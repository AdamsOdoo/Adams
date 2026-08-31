"""Overview projection for the P02 read-only UI facade."""

from __future__ import annotations

from collections import defaultdict

from odoo import _, api
from odoo.exceptions import AccessError

from ..domain.dto import (
    ActivityDTO,
    AllowedActionDTO,
    HealthDTO,
    OverviewDTO,
    StoreSummaryDTO,
    WorkflowSummaryDTO,
)
from ..domain.states import (
    RuntimeHealth,
    StoreActivationState,
    StoreConfigurationState,
    StoreConnectionState,
    WorkflowReadiness,
)
from ..domain.store_admin import MAX_SUPPORTED_STORES


class ShopifyConnectorUiFacadeOverviewMixin:
    @api.model
    def get_overview_v1(self, store_id):
        """Return one store's bounded Overview read model.

        ``store_id`` is mandatory and is resolved against the caller's exact
        active company.  The selected-store projection also carries the
        bounded store selector and global capabilities so the browser never
        has to invent a second store-list request or action target.
        """
        store = self._require_store(store_id)
        now = self._now_utc()
        settings = self._settings_for(store)
        jobs = self._search_jobs(
            store,
            limit=self.MAX_OVERVIEW_JOBS,
            order="write_date desc, id desc",
        )
        attention_rows = self._collect_attention(
            store,
            limit=self.MAX_ATTENTION_ITEMS,
            now=now,
        )

        workflow_rows = self._workflow_dtos(
            store, settings, jobs, attention_rows, now,
        )
        health = self._overview_health(store, settings, attention_rows, now)
        activity = self._overview_activity(store, jobs, now)
        permissions = self._permissions()
        allowed_stores = self._overview_allowed_stores()
        allowed_actions = self._overview_allowed_actions(allowed_stores)
        attention_items = [
            self._serialize(dto)
            for dto, _meta in attention_rows[:3]
        ]
        overview = OverviewDTO(
            store=self._store_dto(store, settings, attention_rows),
            health=health,
            workflows=tuple(workflow_rows),
            attention={
                "total": len(attention_rows),
                "items": attention_items,
                "has_more": (
                    bool(getattr(attention_rows, "has_more", False))
                    or len(attention_rows) > 3
                ),
                "truncated": bool(getattr(attention_rows, "truncated", False)),
                "partial": bool(getattr(attention_rows, "partial", False)),
                "provider_truncation": getattr(
                    attention_rows, "provider_status", {},
                ),
            },
            activity=activity,
            permissions=permissions,
            allowed_stores=allowed_stores,
            all_stores={
                "allowed": len(allowed_stores) > 1,
                "read_only": True,
                "selected": False,
            },
            allowed_actions=allowed_actions,
        )
        through = self._oldest_observation(
            store,
            settings,
            jobs,
            [meta.get("observed_at") for _dto, meta in attention_rows],
        )
        return self._envelope(store, overview, through=through, now=now)

    @api.model
    def _overview_allowed_stores(self):
        """Return only exact-company store summaries for the selector."""
        Store = self.env["shopify.connector.store"]
        try:
            stores = Store.search(
                [("company_id", "=", self.env.company.id)],
                order="id asc",
                limit=MAX_SUPPORTED_STORES,
            )
        except AccessError:
            return ()
        rows = []
        for candidate in stores:
            settings = self._settings_for(candidate)
            rows.append(self._serialize(self._store_dto(candidate, settings, [])))
        return tuple(rows)

    @api.model
    def _overview_allowed_actions(self, allowed_stores):
        """Advertise only global actions with server-owned capabilities."""
        try:
            role = self._current_role()
        except AccessError:
            return ()
        if role.value != "administrator":
            return ()
        target = self._authorized_store_admin_target()
        if not target:
            target = self._authorized_native_collection_target(
                "shopify.connector.store",
                domain=[("company_id", "=", self.env.company.id)],
                label=_("Manage Shopify stores"),
            )
        actions = []
        if target:
            actions.append(AllowedActionDTO(
                key="manage_stores",
                label=_("Manage stores"),
                required_role="administrator",
                target=target,
            ))
        # V2 does not own the create command.  Its executable manage target
        # opens the subordinate P16 surface, where create_store_v1 is guarded
        # by the store-capacity and generation command contracts.
        return tuple(actions)

    @api.model
    def _settings_for(self, store):
        Settings = self.env["shopify.connector.store.settings"]
        return Settings.search([("store_id", "=", store.id)], limit=1)

    @api.model
    def _store_dto(self, store, settings, attention_rows):
        connection = {
            "setup_incomplete": StoreConnectionState.UNCONFIGURED.value,
            "connected": StoreConnectionState.CONNECTED.value,
            "reconnect_needed": StoreConnectionState.INVALID.value,
            "disconnecting": StoreConnectionState.DISCONNECTED.value,
            "disconnected": StoreConnectionState.DISCONNECTED.value,
        }.get(store.state, StoreConnectionState.INVALID.value)
        configuration = self._configuration_state(store, settings)
        activation = self._activation_state(store, settings)
        runtime = self._runtime_health(store, attention_rows)
        return StoreSummaryDTO(
            id=store.id,
            name=self._safe_text(store.name) or _("Shopify store"),
            shop_domain=self._safe_domain(store.shop_domain),
            company={
                "id": store.company_id.id,
                "name": self._safe_text(store.company_id.name)
                or _("Active company"),
            },
            connection=connection,
            configuration=configuration,
            activation=activation,
            runtime_health=runtime,
        )

    @staticmethod
    def _configuration_state(store, settings):
        if not settings:
            return StoreConfigurationState.INCOMPLETE.value
        if settings.setup_readiness_stale_since:
            return StoreConfigurationState.STALE.value
        if store.last_readiness_result == "pass" and store.state == "connected":
            return StoreConfigurationState.VALID.value
        return StoreConfigurationState.INCOMPLETE.value

    @staticmethod
    def _activation_state(store, settings):
        stored = getattr(store, "activation_state", False)
        if stored in {
            StoreActivationState.DRAFT.value,
            StoreActivationState.ACTIVE.value,
            StoreActivationState.PAUSED.value,
            StoreActivationState.RETIRED.value,
        }:
            return stored
        if store.state == "connected":
            return StoreActivationState.ACTIVE.value
        # A disconnected legacy row does not prove operator retirement.  Keep
        # the state in draft until the additive activation field has durable
        # evidence; inferring retired here would hide a recoverable store.
        return StoreActivationState.DRAFT.value

    @classmethod
    def _runtime_health(cls, store, attention_rows):
        if getattr(store, "activation_state", False) == StoreActivationState.RETIRED.value:
            return RuntimeHealth.UNKNOWN.value
        if store.state in ("setup_incomplete", "disconnected"):
            return RuntimeHealth.UNKNOWN.value
        if store.state in ("reconnect_needed", "disconnecting"):
            return RuntimeHealth.BLOCKED.value
        if getattr(store, "activation_state", False) == StoreActivationState.PAUSED.value:
            return RuntimeHealth.DEGRADED.value
        if store.api_health_state in ("throttled", "degraded"):
            return RuntimeHealth.DEGRADED.value
        if any(dto.severity == "critical" for dto, _meta in attention_rows):
            return RuntimeHealth.ATTENTION_REQUIRED.value
        if attention_rows:
            return RuntimeHealth.ATTENTION_REQUIRED.value
        return RuntimeHealth.HEALTHY.value

    @api.model
    def _overview_health(self, store, settings, attention_rows, now):
        critical = sum(
            1 for dto, _meta in attention_rows if dto.severity == "critical"
        )
        warning = sum(
            1 for dto, _meta in attention_rows if dto.severity == "warning"
        )
        activation_state = self._activation_state(store, settings)
        if activation_state == StoreActivationState.RETIRED.value:
            severity = "warning"
            title = _("The store is retired.")
            reason = _(
                "This store is retained for history and cannot run connector workflows."
            )
        elif store.state in ("setup_incomplete", "disconnected"):
            severity = "warning"
            title = _("Finish the store connection setup.")
            reason = _("The connector has no active synchronization identity.")
        elif store.state in ("reconnect_needed", "disconnecting"):
            severity = "critical"
            title = _("The store is not available for synchronization.")
            reason = _("Connection lifecycle evidence requires administrator action.")
        elif activation_state == StoreActivationState.PAUSED.value:
            severity = "warning"
            title = _("Synchronization is paused.")
            reason = _("The store remains connected for diagnostics, but workflows are paused.")
        elif critical:
            severity = "critical"
            title = _("A connector workflow needs attention.")
            reason = _("Resolve the highest-impact item before starting new work.")
        elif warning or store.api_health_state in ("throttled", "degraded"):
            severity = "warning"
            title = _("Synchronization is operating with a warning.")
            reason = _("The connector has recoverable work or API pressure.")
        else:
            severity = "info"
            title = _("Synchronization is healthy.")
            reason = _("No unresolved connector exception is recorded.")
        score = max(0, 100 - (critical * 30) - (warning * 12))
        action_key = "open_attention" if attention_rows else None
        actions = ()
        if action_key:
            actions = (
                AllowedActionDTO(
                    key=action_key,
                    label=_("Review the highest-impact item"),
                    item_ref=attention_rows[0][0].item_ref
                    if attention_rows else None,
                    required_role=None,
                ),
            )
        return HealthDTO(
            title=title,
            reason=reason,
            severity=severity,
            observed_at=self._as_utc(
                store.last_readiness_at or store.write_date or now,
            ),
            next_check_at=None,
            score=score,
            allowed_actions=actions,
        )

    @api.model
    def _workflow_dtos(self, store, settings, jobs, attention_rows, now):
        specs = (
            ("catalog", _("Products"), "product_domain_enabled"),
            ("orders", _("Orders"), "sale_domain_enabled"),
            ("inventory", _("Inventory"), "inventory_domain_enabled"),
            ("fulfillment", _("Fulfillment"), "fulfillment_domain_enabled"),
        )
        by_workflow = defaultdict(list)
        for dto, _meta in attention_rows:
            by_workflow[dto.workflow].append(dto)
        result = []
        activation_state = self._activation_state(store, settings)
        for key, label, flag in specs:
            enabled = bool(settings and flag in settings._fields and settings[flag])
            related_jobs = [job for job in jobs if self._workflow_for_job(job) == key]
            latest = related_jobs[0] if related_jobs else None
            rows = by_workflow.get(key, ())
            if activation_state == StoreActivationState.RETIRED.value:
                readiness = WorkflowReadiness.DISABLED.value
                health = RuntimeHealth.UNKNOWN.value
            elif activation_state == StoreActivationState.PAUSED.value:
                readiness = WorkflowReadiness.PAUSED.value
                health = RuntimeHealth.DEGRADED.value
            elif not enabled:
                readiness = WorkflowReadiness.DISABLED.value
                health = RuntimeHealth.UNKNOWN.value
            elif rows and any(item.severity == "critical" for item in rows):
                readiness = WorkflowReadiness.NOT_READY.value
                health = RuntimeHealth.BLOCKED.value
            elif rows:
                readiness = WorkflowReadiness.READY.value
                health = RuntimeHealth.ATTENTION_REQUIRED.value
            else:
                readiness = WorkflowReadiness.READY.value
                health = RuntimeHealth.HEALTHY.value
            observed = self._workflow_observed_at(
                settings, key, related_jobs,
            )
            result.append(
                WorkflowSummaryDTO(
                    key=key,
                    label=label,
                    readiness=readiness,
                    health=health,
                    freshness={
                        "observed_at": observed.isoformat()
                        if observed else None,
                        "label": self._freshness_label(observed, now),
                    },
                    attention_count=len(rows),
                    latest_run_ref="job:%d" % latest.id if latest else None,
                )
            )
        return result

    @classmethod
    def _workflow_observed_at(cls, settings, workflow, jobs):
        """Return the newest durable success watermark for one workflow.

        A workflow with no successful run or domain checkpoint is genuinely
        unobserved.  Using request time for that state would make a newly
        enabled or never-run workflow look fresh and would hide a stale-data
        condition from the operator.
        """
        values = []
        field_name = cls._WORKFLOW_ANCHOR_FIELDS.get(workflow)
        if settings and field_name and field_name in settings._fields:
            try:
                value = settings[field_name]
            except AccessError:
                value = False
            if value:
                values.append(cls._as_utc(value))
        for job in jobs or ():
            if job.state != "succeeded":
                continue
            value = job.finished_at or job.write_date or job.create_date
            if value:
                values.append(cls._as_utc(value))
        return max(values) if values else None

    @classmethod
    def _freshness_label(cls, observed, now):
        if not observed:
            return _("Not observed yet")
        age = max(0, int((cls._as_utc(now) - observed).total_seconds()))
        if age < 60:
            return _("Observed just now")
        if age < 3600:
            return _("Observed %d minutes ago") % max(1, age // 60)
        if age < 86400:
            return _("Observed %d hours ago") % max(1, age // 3600)
        return _("Observed %d days ago") % max(1, age // 86400)

    @api.model
    def _overview_activity(self, store, jobs, now):
        start = now.timestamp() - (self.MAX_ACTIVITY_DAYS * 86400)
        recent = [
            job for job in jobs
            if self._as_utc(job.write_date or job.create_date or now).timestamp() >= start
        ]
        succeeded = self._search_count(
            "shopify.connector.job",
            [
                ("store_id", "=", store.id),
                ("state", "=", "succeeded"),
                ("finished_at", ">=", self._odoo_datetime(now, days=7)),
            ],
        )
        held = self._search_count(
            "shopify.connector.job",
            [
                ("store_id", "=", store.id),
                ("state", "in", self._JOB_ATTENTION_STATES),
                ("superseded_by_job_id", "=", False),
            ],
        )
        buckets = defaultdict(int)
        for job in recent:
            if job.state != "succeeded":
                continue
            day = self._as_utc(job.finished_at or job.write_date or now).date().isoformat()
            buckets[day] += 1
        series = tuple(
            {"date": day, "succeeded": buckets[day]}
            for day in sorted(buckets)[-self.MAX_ACTIVITY_DAYS:]
        )
        return ActivityDTO(
            window_days=self.MAX_ACTIVITY_DAYS,
            succeeded=max(0, succeeded),
            held=max(0, held),
            series=series,
        )


__all__ = ["ShopifyConnectorUiFacadeOverviewMixin"]
