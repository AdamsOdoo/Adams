"""Shared support for the P02 read-only UI facade.

This module owns the authorization boundary, bounded inputs, legacy record
search helpers, strict JSON sanitation, and common state labels.  It is a
plain Python mixin so the registered Odoo model remains one exact facade while
Overview, Attention, and Run projections can evolve independently.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import fields as dataclass_fields, is_dataclass
from datetime import datetime, timezone

from odoo import _, api, fields
from odoo.exceptions import AccessError, UserError

from ..domain.authorization import capability_for
from ..domain.dto import ResponseEnvelope
from ..domain.immutability import to_plain
from ..domain.states import Role, RunState
from ..tools.redaction import redact


_ATTENTION_REF_RE = re.compile(
    r"^attn:(?P<provider>[a-z][a-z0-9_.:-]*):(?P<source>[1-9][0-9]*):"
    r"(?P<version>[1-9][0-9]*)$"
)
_CURSOR_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)")


class ShopifyConnectorUiFacadeSupportMixin:
    # Odoo 19 replaces registry ``__bases__`` during model setup.  Keep this
    # plain-Python mixin layout-compatible with ``BaseModel`` so later
    # ``_inherit = 'shopify.connector.ui.facade'`` extensions install safely.
    __slots__ = ()

    @api.model
    def _current_role(self):
        """Resolve one stable public role from Odoo's implied groups."""
        group_base = "shopify_connector_core.group_shopify_connector_"
        checks = (
            ("admin", Role.ADMINISTRATOR),
            ("reviewer", Role.REVIEWER),
            ("operator", Role.OPERATOR),
            ("auditor", Role.AUDITOR),
        )
        for suffix, role in checks:
            if self.env.user.has_group(group_base + suffix):
                return role
        raise AccessError(_("This read surface is limited to connector users."))

    @api.model
    def _permissions(self):
        capability = capability_for(self._current_role())
        return {
            "role": capability.role.value,
            "can_start_operation": capability.can_operate,
            "can_configure": capability.can_configure,
            "can_resolve": capability.can_resolve,
        }

    @api.model
    def _require_store(self, store_id):
        self._current_role()
        if (
            isinstance(store_id, bool)
            or not isinstance(store_id, int)
            or store_id <= 0
        ):
            raise UserError(_("Choose one valid Shopify store."))
        Store = self.env["shopify.connector.store"]
        # Search under the caller's environment first.  The company predicate
        # is repeated even though the global rule also enforces it, because the
        # facade's contract is exact active-company, not merely allowed-company.
        store = Store.search(
            [
                ("id", "=", store_id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not store:
            raise AccessError(
                _("The requested store is not available in the active company.")
            )
        store.ensure_one()
        return store

    @classmethod
    def _bounded_limit(cls, value, maximum):
        if value in (None, False, ""):
            return maximum
        if isinstance(value, bool) or not isinstance(value, int):
            raise UserError(_("The page size must be an integer."))
        if value <= 0:
            raise UserError(_("The page size must be positive."))
        return min(value, maximum)

    @staticmethod
    def _bounded_offset(value):
        if value in (None, False, ""):
            return 0
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise UserError(_("The page offset is invalid."))
        return min(value, 10_000)

    @classmethod
    def _encode_cursor(cls, offset):
        raw = str(int(offset)).encode("ascii")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @classmethod
    def _decode_cursor(cls, value):
        if not isinstance(value, str) or not _CURSOR_RE.fullmatch(value):
            raise UserError(_("The attention cursor is invalid."))
        padded = value + "=" * (-len(value) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
            offset = int(raw)
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise UserError(_("The attention cursor is invalid.")) from exc
        return cls._bounded_offset(offset)

    @classmethod
    def _validate_attention_filters(cls, filters):
        if filters in (None, False, ""):
            return {}
        if not isinstance(filters, Mapping):
            raise UserError(_("Attention filters must be a mapping."))
        allowed = {"severity", "workflow", "owner_role", "action_key", "q"}
        unknown = set(filters) - allowed
        if unknown or any(not isinstance(key, str) for key in filters):
            raise UserError(_("Attention filters contain an unsupported key."))
        result = {}
        for key, value in filters.items():
            if not isinstance(value, str) or len(value) > 120:
                raise UserError(_("Attention filter values are invalid."))
            if key == "severity" and value not in cls._SEVERITY_RANK:
                raise UserError(_("The severity filter is invalid."))
            result[key] = value
        return result

    @classmethod
    def _parse_attention_ref(cls, item_ref):
        if not isinstance(item_ref, str):
            raise UserError(_("The attention reference must be a string."))
        match = _ATTENTION_REF_RE.fullmatch(item_ref)
        if not match:
            raise UserError(_("The attention reference is invalid."))
        provider = match.group("provider")
        if provider not in cls._PROVIDER_RANK:
            raise UserError(_("The attention provider is not supported."))
        return provider, int(match.group("source")), int(match.group("version"))

    @api.model
    def _search_jobs(self, store, domain=None, limit=200, order="id desc"):
        Job = self.env["shopify.connector.job"]
        term = [("store_id", "=", store.id)]
        if domain:
            term.extend(domain)
        return Job.search(term, order=order, limit=limit)

    @api.model
    def _search_job_logs(self, job, limit=200, include_sentinel=False):
        Log = self.env["shopify.connector.job.log"]
        bounded = min(max(1, int(limit)), self.MAX_TIMELINE_EVENTS)
        return Log.search(
            [("job_id", "=", job.id)],
            order="occurred_at asc, id asc",
            limit=bounded + (1 if include_sentinel else 0),
        )

    @api.model
    def _optional_model(self, name):
        if name not in self._OPTIONAL_MODELS or name not in self.env:
            return None
        return self.env[name]

    @api.model
    def _safe_search(self, model, domain, order="id desc", limit=80):
        if model is None or "store_id" not in model._fields:
            return ()
        try:
            return model.search(domain, order=order, limit=limit)
        except AccessError:
            # An installed optional addon may intentionally not grant a role
            # access to its details.  Failing closed means it contributes no
            # aggregate, never a privileged count.
            return ()

    @api.model
    def _search_count(self, model_name, domain):
        if model_name not in self.env:
            return 0
        try:
            return self.env[model_name].search_count(domain)
        except AccessError:
            return 0

    @api.model
    def _authorized_native_record_target(
        self, record, store, *, action_key="open_native_record", label=None,
    ):
        """Build one complete native action after the UI read checks.

        The browser receives this already-authorized ``ir.actions.act_window``
        shape.  It is deliberately assembled from a code-owned model
        allowlist and an exact store/company recordset; no RPC argument can
        select a model, domain, or arbitrary action service.
        """
        allowed_models = frozenset({
            "shopify.connector.store",
            "shopify.connector.store.settings",
            "shopify.connector.product.template.binding",
            "shopify.connector.product.variant.binding",
            "shopify.connector.order.binding",
            "shopify.connector.inventory.level.binding",
            "shopify.connector.fulfillment.binding",
            "stock.picking",
        })
        if not record or not store:
            return None
        model_name = getattr(record, "_name", False)
        if model_name not in allowed_models:
            return None
        if not getattr(record, "id", 0) or not getattr(store, "id", 0):
            return None
        try:
            record.ensure_one()
            if hasattr(record, "exists") and not record.exists():
                return None
            # A store is its own scope anchor.  Every other target must carry
            # the exact store relation so a leaked job reference cannot open
            # a same-company record from another connector store.
            if model_name == "shopify.connector.store":
                if record.id != store.id:
                    return None
            elif "store_id" not in record._fields:
                return None
            elif record.store_id.id != store.id:
                return None
            if "company_id" in record._fields and (
                not record.company_id or record.company_id.id != self.env.company.id
            ):
                return None
            record.check_access_rights("read")
            record.check_access_rule("read")
        except (AccessError, UserError, ValueError, AttributeError):
            return None
        action_name = self._safe_text(label) or _("Open connector record")
        return {
            "type": "ir.actions.act_window",
            "name": action_name,
            "res_model": model_name,
            "res_id": record.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "domain": [["id", "=", record.id]],
            "context": {
                "active_model": model_name,
                "active_id": record.id,
                "active_ids": [record.id],
                "default_store_id": store.id,
                "default_company_id": self.env.company.id,
            },
            "target": "current",
            "action_key": action_key,
        }

    @api.model
    def _authorized_native_collection_target(
        self, model_name, *, domain, label, context=None,
    ):
        """Build a bounded native list action for one fixed collection."""
        if model_name != "shopify.connector.store" or model_name not in self.env:
            return None
        Model = self.env[model_name]
        try:
            Model.check_access_rights("read")
            # Execute the exact scoped search under the caller's record rules
            # before advertising the action.  An empty list is valid (the
            # administrator may still create a first store), while denied
            # access fails closed.
            Model.search(list(domain), limit=1)
        except (AccessError, UserError, ValueError, AttributeError):
            return None
        safe_domain = []
        for term in domain:
            if not isinstance(term, (list, tuple)) or len(term) != 3:
                return None
            field_name, operator, value = term
            if field_name != "company_id" or operator != "=" or value != self.env.company.id:
                return None
            safe_domain.append([field_name, operator, value])
        safe_context = {
            "active_model": model_name,
            "default_company_id": self.env.company.id,
        }
        if isinstance(context, Mapping):
            for key, value in context.items():
                if key in {"active_model", "default_company_id", "active_company_id"}:
                    safe_context[key] = value
        return {
            "type": "ir.actions.act_window",
            "name": self._safe_text(label) or _("Manage connector stores"),
            "res_model": model_name,
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "domain": safe_domain,
            "context": safe_context,
            "target": "current",
            "action_key": "manage_stores",
        }

    @api.model
    def _authorized_store_admin_target(self):
        """Return the one known P16 store-admin action when it is installed.

        The target is built by server code and is deliberately limited to one
        registered client-action tag.  Looking up the XML id first prevents a
        pre-activation backend from advertising a client action whose assets
        and action record are not installed yet.
        """

        if not (
            self.env.su
            or self.env.user.has_group(
                "shopify_connector_core.group_shopify_connector_admin"
            )
        ):
            return None
        action = self.env.ref(
            "shopify_connector_core.action_shopify_connector_p16_admin",
            raise_if_not_found=False,
        )
        if not action or action._name != "ir.actions.client":
            return None
        return {
            "type": "ir.actions.client",
            "name": _("Manage Shopify stores"),
            "tag": "shopify_connector_p16_admin",
            "target": "current",
            "context": {
                "p16_surface": "list",
                "active_company_id": self.env.company.id,
            },
        }

    @staticmethod
    def _safe_text(value, fallback=""):
        if value in (None, False):
            return fallback
        try:
            text = redact(str(value))
        except Exception:  # defensive at a presentation boundary
            return fallback
        text = _EMAIL_RE.sub("***", text)
        text = _PHONE_RE.sub("***", text)
        return text[:512]

    @classmethod
    def _safe_domain(cls, value):
        value = cls._safe_text(value)
        if not value or len(value) > 253 or any(char.isspace() for char in value):
            return "unknown.myshopify.com"
        return value.lower()

    @staticmethod
    def _as_utc(value):
        if not value:
            return datetime.now(timezone.utc)
        if not isinstance(value, datetime):
            value = fields.Datetime.to_datetime(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _now_utc(cls):
        return datetime.now(timezone.utc)

    @classmethod
    def _age_seconds(cls, value, now):
        return max(0, int((now - cls._as_utc(value)).total_seconds()))

    @classmethod
    def _odoo_datetime(cls, now, days=0):
        from datetime import timedelta

        value = now - timedelta(days=days)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @classmethod
    def _state_version(cls, record, names):
        values = {"model": record._name, "id": record.id}
        for name in names:
            if name not in record._fields:
                continue
            value = record[name]
            if hasattr(value, "ids"):
                value = tuple(value.ids)
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, (dict, list, tuple)):
                value = str(value)
            values[name] = value
        digest = hashlib.sha256(
            json.dumps(values, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        # References are sent to browser code and may be echoed by JavaScript
        # clients.  Keep the optimistic-concurrency version below
        # Number.MAX_SAFE_INTEGER so a client cannot round it and submit a
        # false stale-state conflict.
        return max(1, int(digest[:12], 16))

    @classmethod
    def _serialize(cls, value):
        """Convert DTOs to strict JSON without coercing unsafe objects.

        Mapping keys are never stringified: doing so can collapse ``1`` and
        ``"1"`` into one browser key.  Unsupported objects, non-finite
        numbers and cycles fail at this RPC boundary instead of becoming a
        record/exception string in a response.
        """

        def contract_tree(item, ancestors):
            if is_dataclass(item):
                identity = id(item)
                if identity in ancestors:
                    raise ValueError('DTO serialization contains a cycle.')
                ancestors.add(identity)
                try:
                    return {
                        field.name: contract_tree(
                            getattr(item, field.name), ancestors,
                        )
                        for field in dataclass_fields(item)
                    }
                finally:
                    ancestors.remove(identity)
            if isinstance(item, Mapping):
                identity = id(item)
                if identity in ancestors:
                    raise ValueError('DTO serialization contains a cycle.')
                ancestors.add(identity)
                try:
                    result = {}
                    for key, nested in item.items():
                        if not isinstance(key, str) or not key:
                            raise TypeError(
                                'DTO mappings require non-empty string keys.'
                            )
                        result[key] = contract_tree(nested, ancestors)
                    return result
                finally:
                    ancestors.remove(identity)
            if isinstance(item, (list, tuple)):
                identity = id(item)
                if identity in ancestors:
                    raise ValueError('DTO serialization contains a cycle.')
                ancestors.add(identity)
                try:
                    return [
                        contract_tree(nested, ancestors) for nested in item
                    ]
                finally:
                    ancestors.remove(identity)
            # Enum and aware-UTC datetime remain typed until the shared strict
            # serializer converts them. Unsupported values are intentionally
            # left for that serializer to reject.
            return item

        return to_plain(contract_tree(value, set()))

    @classmethod
    def _envelope(cls, store, data, through=None, now=None):
        now = now or cls._now_utc()
        generated = cls._as_utc(now)
        data_through = cls._as_utc(through or now)
        if data_through > generated:
            data_through = generated
        envelope = ResponseEnvelope(
            contract_version=1,
            generated_at=generated,
            data_through=data_through,
            store_generation=max(0, int(store.connection_generation or 0)),
            correlation_id="sc_" + uuid.uuid4().hex[:24],
            data=cls._serialize(data),
        )
        return cls._serialize(envelope)

    @classmethod
    def _oldest_observation(cls, store, settings, records, observations):
        values = []
        for value in observations or ():
            if value:
                values.append(cls._as_utc(value))
        for record in records or ():
            for name in ("write_date", "create_date", "finished_at", "occurred_at"):
                if name in record._fields and record[name]:
                    values.append(cls._as_utc(record[name]))
                    break
        if settings:
            for name in ("write_date", "create_date"):
                if name in settings._fields and settings[name]:
                    values.append(cls._as_utc(settings[name]))
                    break
        for name in ("last_readiness_at", "last_test_connection_at", "write_date"):
            if name in store._fields and store[name]:
                values.append(cls._as_utc(store[name]))
        return min(values) if values else cls._now_utc()

    @staticmethod
    def _selection_label(record, field_name):
        if not record or field_name not in record._fields:
            return ""
        value = record[field_name]
        if not value:
            return ""
        field = record._fields[field_name]
        selection = field.selection
        if callable(selection):
            try:
                selection = selection(record.env)
            except Exception:
                selection = ()
        try:
            return dict(selection or ()).get(value, str(value))
        except (TypeError, ValueError):
            return str(value)

    @classmethod
    def _workflow_for_job(cls, job):
        value = (job.job_type or job.original_job_type or "").lower()
        if "fulfillment" in value or "tracking" in value:
            return "fulfillment"
        if "inventory" in value or "stock" in value or "location" in value:
            return "inventory"
        if "order" in value or "customer" in value or "sale" in value:
            return "orders"
        if "product" in value or "catalog" in value or "export" in value:
            return "catalog"
        if "readiness" in value or "connection" in value:
            return "setup"
        return "connector"

    @classmethod
    def _workflow_from_mutation(cls, attempt):
        return cls._workflow_for_job(attempt.job_id) if attempt.job_id else "connector"

    @classmethod
    def _operation_for_job(cls, job):
        return (job.job_type or job.original_job_type or "connector_operation")

    @classmethod
    def _run_state(cls, value):
        return {
            "draft": RunState.REQUESTED.value,
            "queued": RunState.ADMITTED.value,
            "running": RunState.RUNNING.value,
            "succeeded": RunState.SUCCEEDED.value,
            "failed_final": RunState.FAILED_TERMINAL.value,
            "failed_retryable": RunState.FAILED_RETRYABLE.value,
            "retry_waiting": RunState.WAITING.value,
            "blocked_manual_review": RunState.BLOCKED_MANUAL_REVIEW.value,
            "cancelled": RunState.CANCELLED.value,
            "skipped": RunState.SUCCEEDED.value,
        }.get(value, RunState.WAITING.value)

    @classmethod
    def _job_what_happened(cls, job):
        state = job.state
        if state == "blocked_manual_review":
            return _("The connector stopped before it could safely complete the operation.")
        if state == "failed_retryable":
            return _("The operation failed in a state where a bounded retry is safe.")
        return _("The operation reached a terminal failure and needs investigation.")


__all__ = ["ShopifyConnectorUiFacadeSupportMixin"]
