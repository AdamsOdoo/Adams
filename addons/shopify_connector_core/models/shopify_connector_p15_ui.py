"""P15 typed administrator reads over the existing UI facade."""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Mapping

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..domain.dto import ResponseEnvelope, WorkflowSummaryDTO
from ..domain.store_admin import (
    LIFECYCLE_TRANSITIONS,
    ReadinessCheckDTO,
    ReadinessDTO,
    SettingsFieldDTO,
    SettingsGroupDTO,
    StoreAdminSummaryDTO,
    StoreListDTO,
    StoreListItemDTO,
    StoreSettingsDTO,
    StoreSetupDTO,
    MAX_SUPPORTED_STORES,
    canonical_shop_domain,
    require_setup_step_key,
    store_configuration_fingerprint,
)
from ..domain.states import RuntimeHealth, WorkflowReadiness
from .shopify_connector_p15_shared import (
    P15_CURSOR_RE,
    P15_EDITABLE_SETTINGS_GROUP_FIELDS,
    P15_MAX_LIST_LIMIT,
    P15_MAX_SEARCH_LENGTH,
    P15_MAX_TEXT_SETTING_LENGTH,
    P15_SETTINGS_GROUP_FIELDS,
    P15_SETTINGS_GROUP_LABELS,
    P15_SETUP_STEP_PAYLOAD_FIELDS,
    _p15_datetime,
    _p15_positive_id,
)
from .shopify_connector_setup_wizard import setup_step_index


class ShopifyConnectorP15UiFacade(models.AbstractModel):
    """Typed P15 reads over the existing exact-store V2 read facade."""

    _inherit = "shopify.connector.ui.facade"

    # ------------------------------------------------------------------
    # Shared authorization / envelope helpers
    # ------------------------------------------------------------------

    @api.model
    def _p15_require_admin(self):
        if not self.env.su and not self.env.user.has_group(
            "shopify_connector_core.group_shopify_connector_admin"
        ):
            raise AccessError(_(
                "Only a Shopify Connector Administrator may use this control."
            ))

    @api.model
    def _p15_require_store(self, store_id):
        # `_require_store` already resolves through normal ACLs and the exact
        # active-company predicate.  Keep the check in one place so every P15
        # read/write has identical foreign-store behavior.
        return self._require_store(store_id)

    @api.model
    def _p15_settings_for_read(self, store):
        """Resolve at most one effective row without creating on a read."""

        Settings = self.env["shopify.connector.store.settings"]
        rows = Settings.search(
            [("store_id", "=", store.id)], order="id asc", limit=2,
        )
        if len(rows) > 1:
            raise ValidationError(_(
                "More than one settings row exists for this store; resolve "
                "the duplicate before continuing."
            ))
        return rows

    @api.model
    def _p15_envelope(self, store_generation, data, *, through=None):
        now = self._now_utc()
        observed = self._as_utc(through or now)
        if observed > now:
            observed = now
        envelope = ResponseEnvelope(
            contract_version=1,
            generated_at=now,
            data_through=observed,
            store_generation=max(0, int(store_generation or 0)),
            correlation_id="sc_" + uuid.uuid4().hex[:24],
            data=self._serialize(data),
        )
        return self._serialize(envelope)

    # ------------------------------------------------------------------
    # Store-list projection
    # ------------------------------------------------------------------

    @api.model
    def _p15_cursor_decode(self, value):
        if value in (None, False, ""):
            return 0
        if not isinstance(value, str):
            raise UserError(_("The store cursor is invalid."))
        # The cursor carries no store/company data; it is only an opaque
        # bounded position.  Prefixing and base64 keep clients from treating
        # it as a public ORM id while retaining deterministic keyset paging.
        try:
            padded = value + "=" * (-len(value) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        except (UnicodeError, ValueError, binascii.Error) as exc:
            raise UserError(_("The store cursor is invalid.")) from exc
        if not P15_CURSOR_RE.fullmatch(decoded):
            raise UserError(_("The store cursor is invalid."))
        return _p15_positive_id(int(decoded.split(":", 1)[1]), "cursor")

    @api.model
    def _p15_cursor_encode(self, store_id):
        raw = ("s:%d" % int(store_id)).encode("ascii")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @api.model
    def _p15_company_filter(self, company_ids):
        active = self.env.company.id
        if company_ids in (None, False, ""):
            return active
        if isinstance(company_ids, bool) or not isinstance(company_ids, (list, tuple)):
            raise UserError(_("Company scope must be a list."))
        parsed = []
        for value in company_ids:
            parsed.append(_p15_positive_id(value, "company_id"))
        if set(parsed) != {active}:
            raise AccessError(_(
                "Store administration is scoped to the exact active company."
            ))
        return active

    @api.model
    def _p15_state_filter(self, value):
        if value in (None, False, ""):
            return ()
        if isinstance(value, str):
            values = (value,)
        elif isinstance(value, (list, tuple)) and not isinstance(value, bool):
            values = tuple(value)
        else:
            raise UserError(_("The lifecycle state filter is invalid."))
        allowed = set(LIFECYCLE_TRANSITIONS)
        if any(not isinstance(item, str) or item not in allowed for item in values):
            raise UserError(_("The lifecycle state filter is invalid."))
        return tuple(dict.fromkeys(values))

    @api.model
    def _p15_store_list_workflows(
        self, store, settings, now, attention_rows=None,
    ):
        """Cheap bounded workflow summaries for the <=10-store list."""

        specs = (
            ("catalog", _("Products"), "product_domain_enabled"),
            ("orders", _("Orders"), "sale_domain_enabled"),
            ("inventory", _("Inventory"), "inventory_domain_enabled"),
            ("fulfillment", _("Fulfillment"), "fulfillment_domain_enabled"),
        )
        jobs = self._search_jobs(store, limit=30, order="write_date desc, id desc")
        if attention_rows is None:
            attention_rows = self._collect_attention(
                store,
                limit=self.MAX_ATTENTION_ITEMS,
                now=now,
                include_sentinel=True,
            )
        result = []
        activation_state = getattr(store, "activation_state", "draft")
        for key, label, field_name in specs:
            enabled = bool(
                settings and field_name in settings._fields and settings[field_name]
            )
            workflow_jobs = [job for job in jobs if self._workflow_for_job(job) == key]
            attention = [
                row for row in attention_rows
                if row and row[0].workflow == key
            ]
            # Operator activation dominates workflow flags.  A paused store
            # remains connected for diagnostics but cannot present a ready or
            # healthy workflow; a retired store is no longer operational.
            if activation_state == "retired":
                readiness = WorkflowReadiness.DISABLED.value
                health = RuntimeHealth.UNKNOWN.value
            elif activation_state == "paused":
                readiness = WorkflowReadiness.PAUSED.value
                health = RuntimeHealth.DEGRADED.value
            elif not enabled:
                readiness = WorkflowReadiness.DISABLED.value
                health = RuntimeHealth.UNKNOWN.value
            elif attention:
                readiness = WorkflowReadiness.NOT_READY.value
                health = RuntimeHealth.ATTENTION_REQUIRED.value
            else:
                readiness = WorkflowReadiness.READY.value
                health = RuntimeHealth.HEALTHY.value
            observed = self._workflow_observed_at(settings, key, workflow_jobs)
            result.append(WorkflowSummaryDTO(
                key=key,
                label=label,
                readiness=readiness,
                health=health,
                freshness={
                    "observed_at": observed.isoformat() if observed else None,
                    "label": self._freshness_label(observed, now),
                },
                attention_count=min(len(attention), self.MAX_ATTENTION_ITEMS),
                latest_run_ref=("job:%d" % workflow_jobs[0].id)
                if workflow_jobs else None,
            ))
        return tuple(result)

    @api.model
    def get_store_list_v1(
        self, company_ids=None, state_filter=None, search=None, limit=10, cursor=None,
    ):
        """Return a bounded list limited to the exact active company."""

        self._current_role()
        active_company = self._p15_company_filter(company_ids)
        states = self._p15_state_filter(state_filter)
        if search in (None, False, ""):
            search = ""
        elif not isinstance(search, str) or len(search) > P15_MAX_SEARCH_LENGTH:
            raise UserError(_("The store search is invalid."))
        if limit in (None, False, ""):
            limit = P15_MAX_LIST_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise UserError(_("The page size must be a positive integer."))
        limit = min(limit, P15_MAX_LIST_LIMIT)
        after_id = self._p15_cursor_decode(cursor)
        domain = [("company_id", "=", active_company)]
        if states:
            domain.append(("state", "in", list(states)))
        if search:
            domain += ["|", ("name", "ilike", search), ("shop_domain", "ilike", search)]
        if after_id:
            domain.append(("id", ">", after_id))
        Store = self.env["shopify.connector.store"]
        stores = Store.search(domain, order="id asc", limit=limit + 1)
        has_more = len(stores) > limit
        visible = stores[:limit]
        now = self._now_utc()
        global_actions = self._p15_admin_actions()
        items = []
        through = None
        for store in visible:
            settings = self._p15_settings_for_read(store)
            attention_rows = self._collect_attention(
                store,
                limit=self.MAX_ATTENTION_ITEMS,
                now=now,
                include_sentinel=True,
            )
            visible_attention_rows = attention_rows[:self.MAX_ATTENTION_ITEMS]
            summary = self._store_dto(store, settings, [(
                # `_runtime_health` only needs the DTO severity; the metadata
                # is intentionally discarded from this compact projection.
                row[0], row[1]
            ) for row in visible_attention_rows if row])
            workflows = self._p15_store_list_workflows(
                store, settings, now, attention_rows=visible_attention_rows,
            )
            continuation = self._p15_setup_continuation(settings)
            item = StoreListItemDTO(
                store=summary,
                connection_generation=max(0, int(store.connection_generation or 0)),
                workflows=workflows,
                setup_continuation=continuation,
                freshness={
                    "last_readiness_at": (
                        self._as_utc(store.last_readiness_at).isoformat()
                        if store.last_readiness_at else None
                    ),
                    "last_test_connection_at": (
                        self._as_utc(store.last_test_connection_at).isoformat()
                        if store.last_test_connection_at else None
                    ),
                },
                attention_count=len(visible_attention_rows),
                allowed_actions=self._p15_admin_actions(store, settings),
                attention_truncated=(
                    bool(getattr(attention_rows, "truncated", False))
                    or bool(getattr(attention_rows, "partial", False))
                ),
                attention_partial=bool(getattr(attention_rows, "partial", False)),
            )
            items.append(item)
            timestamps = [store.write_date, store.last_readiness_at]
            if settings:
                timestamps.append(settings.write_date)
            timestamps = [self._as_utc(value) for value in timestamps if value]
            if timestamps:
                through = min((through, *timestamps)) if through else min(timestamps)
        next_cursor = self._p15_cursor_encode(visible[-1].id) if has_more and visible else None
        payload = StoreListDTO(
            stores=tuple(items),
            limit=limit,
            next_cursor=next_cursor,
            has_more=has_more,
            capacity={
                "maximum": MAX_SUPPORTED_STORES,
                "database_limit_enforced": True,
                "visible_count": len(visible),
            },
            allowed_actions=global_actions,
            can_create_store=any(item.key == "create_store" for item in global_actions),
        )
        generation = max((item.connection_generation for item in items), default=0)
        return self._p15_envelope(generation, payload, through=through)

    @api.model
    def _p15_setup_continuation(self, settings):
        if not settings:
            return {"step_key": "welcome", "step": 1, "completed": False}
        Wizard = self.env["shopify.connector.setup.wizard"]
        key = Wizard._resume_key(settings)
        return {
            "step_key": key,
            "step": setup_step_index(key),
            "completed": bool(settings.setup_completed_at),
        }

    # ------------------------------------------------------------------
    # Settings projection / fragments
    # ------------------------------------------------------------------

    @api.model
    def _p15_field_value(self, settings, field_name):
        if field_name not in settings._fields:
            return None, None
        if any(secret in field_name.casefold() for secret in (
            "token", "secret", "password", "credential",
        )):
            raise AccessError(_("Credential values are not settings values."))
        field = settings._fields[field_name]
        try:
            value = settings[field_name]
        except AccessError:
            return None, None
        field_type = field.type
        if field_type == "many2one":
            return (value.id if value else False), "reference"
        if field_type in ("datetime", "date"):
            return (
                fields.Date.to_string(value) if field_type == "date"
                else fields.Datetime.to_string(value)
            ) if value else None, "text"
        if field_type == "boolean":
            return bool(value), "boolean"
        if field_type == "integer":
            return int(value or 0), "integer"
        if field_type in ("float", "monetary"):
            return float(value or 0.0), "number"
        if field_type == "selection":
            return value or None, "selection"
        # Text settings are bounded and redacted.  No arbitrary record or
        # exception object is allowed to reach the DTO.
        text = "" if value in (None, False) else str(value)
        return text[:P15_MAX_TEXT_SETTING_LENGTH], "text"

    @api.model
    def _p15_field_schema(self, settings, field_name):
        field = settings._fields[field_name]
        if field.type != "selection":
            return {"type": field.type}
        selection = field.selection
        if callable(selection):
            try:
                selection = selection(settings.env)
            except Exception:
                selection = ()
        try:
            return {
                "type": "selection",
                "choices": [
                    {"value": key, "label": str(label)}
                    for key, label in (selection or ())
                ],
            }
        except (TypeError, ValueError):
            return {"type": "selection", "choices": []}

    @api.model
    def _p15_settings_groups(self, store, settings):
        readiness_fields = set()
        try:
            readiness_fields = set(settings._readiness_relevant_fields())
        except (AttributeError, AccessError):
            pass
        groups = []
        effective = {}
        for group_key, fields_list in P15_SETTINGS_GROUP_FIELDS.items():
            fields_out = []
            values = {}
            for field_name in fields_list:
                if field_name not in settings._fields:
                    continue
                value, value_type = self._p15_field_value(settings, field_name)
                if value_type is None:
                    continue
                values[field_name] = value
                effective[field_name] = value
                fields_out.append(SettingsFieldDTO(
                    key=field_name,
                    value=value,
                    value_type=value_type,
                    source="store_settings",
                    schema=self._p15_field_schema(settings, field_name),
                    readiness_impact=field_name in readiness_fields,
                    last_changed_at=_p15_datetime(settings.write_date),
                ))
            # A fragment remains registered even when an optional addon is not
            # installed, but an empty fragment is not rendered as a fake
            # control.  This is the typed seam optional domains populate by
            # adding their existing settings fields.
            if not fields_out:
                continue
            fingerprint = store_configuration_fingerprint(
                store_id=store.id,
                company_id=store.company_id.id,
                generation=int(getattr(settings, "configuration_generation", 0) or 0),
                operation="settings_group:%s" % group_key,
                values=values,
                preconditions={"readiness_fields": sorted(readiness_fields.intersection(values))},
            )
            editable = set(P15_EDITABLE_SETTINGS_GROUP_FIELDS[group_key]).intersection(values)
            actions = self._p15_admin_actions(store, settings) if editable else ()
            groups.append(SettingsGroupDTO(
                key=group_key,
                label=_(P15_SETTINGS_GROUP_LABELS[group_key]),
                revision=int(getattr(settings, "configuration_generation", 0) or 0),
                fingerprint=fingerprint,
                fields=tuple(fields_out),
                readiness_impact=bool(readiness_fields.intersection(values)),
                allowed_actions=actions,
            ))
        return tuple(groups), effective

    @api.model
    def get_store_settings_v1(self, store_id):
        self._p15_require_admin()
        store = self._p15_require_store(store_id)
        settings = self._p15_settings_for_read(store)
        if not settings:
            # The structural row is created only through its private service;
            # reads never call ordinary create.  A missing row is represented
            # as an empty effective settings projection with generation zero.
            groups = ()
            effective = {}
            generation = 0
            fingerprint = store_configuration_fingerprint(
                store_id=store.id,
                company_id=store.company_id.id,
                generation=0,
                operation="settings",
                values={},
            )
        else:
            groups, effective = self._p15_settings_groups(store, settings)
            generation = int(getattr(settings, "configuration_generation", 0) or 0)
            fingerprint = store_configuration_fingerprint(
                store_id=store.id,
                company_id=store.company_id.id,
                generation=generation,
                operation="settings",
                values=effective,
            )
        dto = StoreSettingsDTO(
            store_id=store.id,
            company_id=store.company_id.id,
            configuration_generation=generation,
            groups=groups,
            effective_values=effective,
            fingerprint=fingerprint,
            allowed_actions=self._p15_admin_actions(store, settings),
        )
        through = settings.write_date if settings else store.write_date
        return self._p15_envelope(store.connection_generation, dto, through=through)

    # ------------------------------------------------------------------
    # Readiness and setup projections
    # ------------------------------------------------------------------

    @api.model
    def _p15_readiness_dto(self, store, settings=None):
        Readiness = self.env["shopify.connector.readiness.check"]
        raw_checks = Readiness._get_checks(store)
        checks = []
        for raw in raw_checks:
            if not isinstance(raw, Mapping):
                continue
            code = str(raw.get("code") or "unknown")
            reason = self._safe_text(raw.get("reason"), _("No reason recorded."))
            checks.append(ReadinessCheckDTO(
                code=code,
                tier=str(raw.get("tier") or "essential"),
                result=str(raw.get("result") or "not_proven"),
                reason=reason,
                not_applicable=bool(raw.get("not_applicable")),
                owner=(code.split("_", 1)[0] if "_" in code else "core"),
            ))
        overall = store.last_readiness_result or "not_run"
        stale = bool(settings and settings.setup_readiness_stale_since)
        fingerprint = store_configuration_fingerprint(
            store_id=store.id,
            company_id=store.company_id.id,
            generation=int(getattr(settings, "configuration_generation", 0) or 0),
            operation="readiness",
            values={
                "overall_result": overall,
                "checks": [
                    {
                        "code": item.code,
                        "tier": item.tier,
                        "result": item.result,
                        "not_applicable": item.not_applicable,
                    }
                    for item in checks
                ],
            },
            preconditions={
                "connection_generation": int(store.connection_generation or 0),
                "stale": stale,
            },
        )
        return ReadinessDTO(
            store_id=store.id,
            overall_result=overall,
            checked_at=_p15_datetime(store.last_readiness_at),
            stale=stale,
            checks=tuple(checks),
            fingerprint=fingerprint,
            allowed_actions=self._p15_admin_actions(store, settings),
        )

    @api.model
    def get_store_readiness_v1(self, store_id):
        store = self._p15_require_store(store_id)
        settings = self._p15_settings_for_read(store)
        readiness = self._p15_readiness_dto(store, settings)
        return self._p15_envelope(
            store.connection_generation,
            readiness,
            through=store.last_readiness_at or store.write_date,
        )

    @api.model
    def get_setup_v1(self, store_id):
        self._p15_require_admin()
        store = self._p15_require_store(store_id)
        # Detect a historic duplicate before the wizard's compatibility
        # helper searches with ``limit=1`` or creates any missing row.
        self._p15_settings_for_read(store)
        state = self.env["shopify.connector.setup.wizard"].get_setup_state(
            store_id=store.id,
        )
        settings = self._p15_settings_for_read(store)
        readiness = self._p15_readiness_dto(store, settings)
        resume_key = state.get("resume_step_key") or "welcome"
        try:
            resume_key = require_setup_step_key(resume_key)
        except (TypeError, ValueError) as exc:
            raise UserError(_("The stored setup progress is invalid.")) from exc
        resume_ordinal = int(state.get("resume_step") or 1)
        steps = []
        for item in state.get("steps") or ():
            key = item.get("key")
            if not isinstance(key, str):
                continue
            applicable = bool(item.get("applicable", True))
            ordinal = int(item.get("index") or 0)
            if not applicable:
                step_state = "not_required"
            elif ordinal <= resume_ordinal:
                step_state = "completed"
            else:
                step_state = "pending"
            steps.append({
                "step_key": key,
                "label": self._safe_text(item.get("label"), key),
                "state": step_state,
                "display_ordinal": ordinal,
                "applicable": applicable,
                "skipped_reason": self._safe_text(item.get("skipped_reason"), "")
                if item.get("skipped_reason") else "",
            })
        config_generation = int(getattr(settings, "configuration_generation", 0) or 0)
        step_values = {}
        if settings and "setup_step_payloads" in settings._fields:
            raw_step_values = settings.setup_step_payloads or {}
            if isinstance(raw_step_values, Mapping):
                # The command service is the writer; this projection only
                # returns the already-sanitized scalar evidence for the exact
                # store.  Never expose a malformed row as arbitrary JSON.
                step_values = {
                    str(key): dict(value)
                    for key, value in raw_step_values.items()
                    if isinstance(key, str) and isinstance(value, Mapping)
                }
        # The setup screen needs an initial value for every installed semantic
        # control, not only for steps that were already submitted.  Project
        # those values from the owning settings row; the command remains the
        # only writer and this map still contains scalar, non-secret fields.
        if settings:
            for step_key, field_names in P15_SETUP_STEP_PAYLOAD_FIELDS.items():
                current = dict(step_values.get(step_key) or {})
                for field_name in field_names:
                    if field_name == "acknowledged" or field_name not in settings._fields:
                        continue
                    value, value_type = self._p15_field_value(settings, field_name)
                    if value_type is not None:
                        current.setdefault(field_name, value)
                if current:
                    step_values[step_key] = current
        dto = StoreSetupDTO(
            store_id=store.id,
            resume_step_key=resume_key,
            resume_step=resume_ordinal,
            steps=tuple(steps),
            readiness=readiness,
            configuration_generation=config_generation,
            activation_preview={
                "state": store.state,
                "activation_state": getattr(store, "activation_state", "draft"),
                "credential_present": bool(store.credential_present),
                "credential_verified": bool(store.credential_last_verified_at),
                "readiness_fingerprint": readiness.fingerprint,
            },
            allowed_actions=self._p15_admin_actions(store, settings),
            step_values=step_values,
        )
        return self._p15_envelope(store.connection_generation, dto, through=store.write_date)

    # ------------------------------------------------------------------
    # Administrator summary
    # ------------------------------------------------------------------

    @api.model
    def get_store_admin_summary_v1(self, store_id):
        self._p15_require_admin()
        store = self._p15_require_store(store_id)
        settings = self._p15_settings_for_read(store)
        generation = int(getattr(settings, "configuration_generation", 0) or 0)
        readiness = self._p15_readiness_dto(store, settings)
        admin_actions = self._p15_admin_actions(store, settings)
        capabilities = {
            "product_import": bool(settings and "product_domain_enabled" in settings._fields),
            "product_export": bool(settings and "product_export_domain_enabled" in settings._fields),
            "orders": bool(settings and "sale_domain_enabled" in settings._fields),
            "inventory": bool(settings and "inventory_domain_enabled" in settings._fields),
            "fulfillment": bool(settings and "fulfillment_domain_enabled" in settings._fields),
            "webhook_intake": "shopify.connector.webhook.subscription" in self.env,
        }
        summary = StoreAdminSummaryDTO(
            store=self._store_dto(store, settings, []),
            connection_generation=int(store.connection_generation or 0),
            configuration_generation=generation,
            lifecycle={
                "state": store.state,
                "activation_state": getattr(store, "activation_state", "draft"),
                "disconnect_status": store.disconnect_status,
                "disconnect_reason": self._safe_text(store.disconnect_status_reason, "")
                if store.disconnect_status_reason else "",
                "one_way_disconnect": True,
                "pause_supported": (
                    store.state == "connected"
                    and getattr(store, "activation_state", "draft") == "active"
                ),
                "resume_supported": (
                    store.state == "connected"
                    and getattr(store, "activation_state", "draft") == "paused"
                ),
                "retire_representation": "durable_activation_state",
                "retire_requires": "disconnected_quiesced",
                "allowed_actions": admin_actions,
            },
            credentials={
                # Presence/verification only.  No credential search/read is
                # needed and no raw field is representable in this DTO.
                "present": bool(store.credential_present),
                "verified": bool(store.credential_last_verified_at),
                "last_verified_at": (
                    self._as_utc(store.credential_last_verified_at).isoformat()
                    if store.credential_last_verified_at else None
                ),
                "last_replaced_at": (
                    self._as_utc(store.credential_last_replaced_at).isoformat()
                    if store.credential_last_replaced_at else None
                ),
            },
            capabilities=capabilities,
            webhooks={
                "desired": bool(capabilities["webhook_intake"]),
                "actual": bool(store.webhook_ready),
            },
            readiness=readiness,
            identity_immutability={
                "shop_domain": {
                    "value": self._safe_domain(store.shop_domain),
                    "immutable": True,
                    "reason": "Shopify shop identity is canonical and cannot be re-homed.",
                },
                "company_id": {
                    "value": store.company_id.id,
                    "immutable": True,
                    "reason": "A store belongs to exactly one owning company.",
                },
            },
            allowed_actions=admin_actions,
        )
        return self._p15_envelope(store.connection_generation, summary, through=store.write_date)
