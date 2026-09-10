"""Needs-Attention projection for the P02 read-only UI facade."""

from __future__ import annotations

from collections.abc import Mapping

from odoo import _, api
from odoo.exceptions import UserError

from ..domain.authorization import capability_for
from ..domain.dto import (
    AllowedActionDTO,
    AttentionDetailDTO,
    AttentionItemDTO,
    EvidenceGroupDTO,
)
from ..domain.states import Role


class ShopifyConnectorUiFacadeAttentionMixin:
    __slots__ = ()

    @api.model
    def search_attention_v1(
        self,
        store_id,
        limit=80,
        offset=0,
        filters=None,
        cursor=None,
    ):
        """Return one bounded page of normalized attention summaries.

        ``filters`` is a small, closed vocabulary.  The browser cannot submit
        an arbitrary Odoo domain, model, field or method.  ``cursor`` is an
        opaque base64 position and is only a presentation aid; all records are
        still re-resolved under the current user and store scope.
        """
        store = self._require_store(store_id)
        limit = self._bounded_limit(limit, self.MAX_ATTENTION_ITEMS)
        if cursor not in (None, False, ""):
            offset = self._decode_cursor(cursor)
        else:
            offset = self._bounded_offset(offset)
        normalized_filters = self._validate_attention_filters(filters)
        now = self._now_utc()
        rows = self._collect_attention(
            store,
            limit=self.MAX_ATTENTION_ITEMS,
            now=now,
            filters=normalized_filters,
            include_sentinel=True,
        )
        # The provider read is deliberately capped at MAX+1.  The last row is
        # a sentinel used only to tell the client that the bounded projection
        # was truncated; it is never exposed as a page item.  This avoids both
        # an unbounded aggregate and an exact count of rows the caller cannot
        # inspect through this contract.
        visible_total = min(len(rows), self.MAX_ATTENTION_ITEMS)
        page_start = min(offset, visible_total)
        page_end = min(page_start + limit, visible_total)
        page = rows[page_start:page_end]
        truncated = bool(getattr(rows, "truncated", False))
        partial = bool(getattr(rows, "partial", False))
        has_more = bool(getattr(rows, "has_more", False)) or page_end < visible_total
        # Once the hard 80-item projection is reached, the caller must narrow
        # filters rather than walk an unbounded cursor.  Cursors are still
        # useful for pages within the safe projection.
        next_cursor = (
            self._encode_cursor(page_end)
            if page_end < visible_total else None
        )
        data = {
            "total": visible_total,
            "items": [self._serialize(dto) for dto, _meta in page],
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "truncated": truncated,
            "partial": partial,
            "provider_truncation": getattr(rows, "provider_status", {}),
            "configuration_generation": int(
                getattr(self._settings_for(store), "configuration_generation", 0)
                or 0
            ),
        }
        through = self._oldest_observation(
            store,
            None,
            (),
            [meta.get("observed_at") for _dto, meta in rows],
        )
        return self._envelope(store, data, through=through, now=now)

    @api.model
    def get_attention_v1(self, store_id, item_ref):
        """Return one attention detail, rechecking its opaque source ref."""
        store = self._require_store(store_id)
        provider, source_id, requested_version = self._parse_attention_ref(
            item_ref,
        )
        now = self._now_utc()
        row = self._load_attention_source(store, provider, source_id, now)
        if row is None:
            raise UserError(_("That attention item is no longer available."))
        dto, meta = row
        if dto.item_ref != item_ref or dto.state_version != requested_version:
            raise UserError(
                _("That attention item changed. Refresh the list before acting.")
            )
        detail = self._serialize(self._attention_detail(dto, meta, now))
        detail["configuration_generation"] = int(
            getattr(self._settings_for(store), "configuration_generation", 0)
            or 0
        )
        through = self._oldest_observation(store, None, (), [meta.get("observed_at")])
        return self._envelope(store, detail, through=through, now=now)

    @api.model
    def get_attention_detail_v1(self, store_id, item_ref):
        """Exact P02 compatibility method; authorization stays in the alias."""

        return self.get_attention_v1(store_id, item_ref)

    @api.model
    def _collect_attention(
        self,
        store,
        job_records=None,
        limit=80,
        now=None,
        filters=None,
        include_sentinel=False,
    ):
        now = now or self._now_utc()
        filters = filters or {}
        capability = capability_for(self._current_role())
        rows = []
        jobs = job_records
        if jobs is None:
            jobs = self._search_jobs(
                store,
                domain=[
                    ("state", "in", self._JOB_ATTENTION_STATES),
                    ("superseded_by_job_id", "=", False),
                ],
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
        else:
            jobs = jobs.filtered(
                lambda job: job.state in self._JOB_ATTENTION_STATES
                and not job.superseded_by_job_id
            )
        for job in jobs[: self.MAX_ATTENTION_ITEMS + 1]:
            rows.append(self._job_attention(job, now, capability))

        Attempt = self._optional_model("shopify.connector.mutation.attempt")
        if Attempt is not None:
            attempts = self._safe_search(
                Attempt,
                [
                    ("store_id", "=", store.id),
                    ("observed_outcome", "=", "uncertain"),
                    ("resolution_disposition", "=", False),
                ],
                order="created_at desc, id desc",
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
            for attempt in attempts:
                rows.append(self._mutation_attention(attempt, now, capability))

        Decision = self._optional_model(
            "shopify.connector.product.match.decision",
        )
        if Decision is not None:
            decisions = self._safe_search(
                Decision,
                [("store_id", "=", store.id), ("state", "=", "pending")],
                order="id desc",
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
            for decision in decisions:
                rows.append(self._product_attention(decision, now, capability))

        rows.extend(self._inventory_attentions(store, now, capability))

        Fulfillment = self._optional_model(
            "shopify.connector.fulfillment.inbound.evidence",
        )
        if Fulfillment is not None:
            reviews = self._safe_search(
                Fulfillment,
                [("store_id", "=", store.id), ("reconciled_state", "=", "review")],
                order="last_observed_at desc, id desc",
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
            for review in reviews:
                rows.append(self._fulfillment_attention(review, now, capability))

        if store.last_readiness_result == "fail":
            rows.append(self._readiness_attention(store, now, capability))

        filtered = [
            row for row in rows
            if row and self._matches_attention_filter(row, filters)
        ]
        filtered.sort(key=self._attention_sort_key)
        # Every provider is individually bounded and the final projection is
        # bounded too.  Search may request one extra row as a has-more
        # sentinel; that row is never sent to the browser.  A detail read
        # re-fetches its exact id and is not dependent on this first-page cap.
        result_limit = self.MAX_ATTENTION_ITEMS + (1 if include_sentinel else 0)
        return filtered[:result_limit]

    @api.model
    def _load_attention_source(self, store, provider, source_id, now):
        capability = capability_for(self._current_role())
        if provider == "manual_review_job":
            Job = self.env["shopify.connector.job"]
            job = Job.search(
                [
                    ("id", "=", source_id),
                    ("store_id", "=", store.id),
                    ("state", "in", self._JOB_ATTENTION_STATES),
                    ("superseded_by_job_id", "=", False),
                ],
                limit=1,
            )
            return self._job_attention(job, now, capability) if job else None
        model_by_provider = {
            "mutation_uncertainty": "shopify.connector.mutation.attempt",
            "product_match": "shopify.connector.product.match.decision",
            "fulfillment_review": "shopify.connector.fulfillment.inbound.evidence",
        }
        model_name = model_by_provider.get(provider)
        if model_name:
            Model = self._optional_model(model_name)
            if Model is None:
                return None
            if provider == "mutation_uncertainty":
                field, value = "observed_outcome", "uncertain"
            elif provider == "product_match":
                field, value = "state", "pending"
            else:
                field, value = "reconciled_state", "review"
            domain = [("id", "=", source_id), ("store_id", "=", store.id), (field, "=", value)]
            if provider == "mutation_uncertainty":
                domain.append(("resolution_disposition", "=", False))
            record = self._safe_search(Model, domain, limit=1)
            if not record:
                return None
            builder = {
                "mutation_uncertainty": self._mutation_attention,
                "product_match": self._product_attention,
                "fulfillment_review": self._fulfillment_attention,
            }[provider]
            return builder(record, now, capability)
        if provider == "inventory_mapping":
            Location = self._optional_model("shopify.connector.location")
            if Location is None:
                return None
            location = self._safe_search(
                Location,
                [("id", "=", source_id), ("store_id", "=", store.id)],
                limit=1,
            )
            if not location:
                return None
            MappingModel = self._optional_model("shopify.connector.location.mapping")
            mappings = self._safe_search(
                MappingModel,
                [("store_id", "=", store.id), ("shopify_gid", "=", location.shopify_location_gid)],
                limit=1,
            ) if MappingModel is not None else ()
            if mappings:
                return None
            return self._inventory_location_attention(location, now, capability)
        if provider == "readiness_failure":
            return self._readiness_attention(store, now, capability)
        return None

    @api.model
    def _job_attention(self, job, now, capability=None):
        if not job:
            return None
        capability = capability or capability_for(self._current_role())
        if job.state == "blocked_manual_review":
            severity = "critical"
            title = _("A sync job is waiting for an administrator decision.")
            impact = _("Work is held until the safety decision is recorded.")
            owner = Role.ADMINISTRATOR.value
        elif job.state == "failed_retryable":
            severity = "warning"
            title = _("A sync job is ready for a safe retry.")
            impact = _("The connector has not completed this operation yet.")
            owner = Role.OPERATOR.value
        else:
            severity = "warning"
            title = _("A sync job needs investigation.")
            impact = _("The operation ended without a successful terminal result.")
            owner = Role.ADMINISTRATOR.value
        actions = [
            AllowedActionDTO(
                key="open_run",
                label=_("Open run evidence"),
                item_ref="job:%d" % job.id,
            )
        ]
        if job.state == "failed_retryable" and capability.can_operate:
            actions.append(
                AllowedActionDTO(
                    key="retry_job",
                    label=_("Retry safely"),
                    item_ref="job:%d" % job.id,
                    required_role=Role.OPERATOR.value,
                )
            )
        if job.state == "blocked_manual_review" and capability.can_configure:
            actions.append(
                AllowedActionDTO(
                    key="resolve_manual_review",
                    label=_("Resolve review"),
                    item_ref="job:%d" % job.id,
                    required_role=Role.ADMINISTRATOR.value,
                    requires_reason=True,
                )
            )
        observed = job.write_date or job.finished_at or job.create_date or now
        state_version = self._state_version(
            job,
            ("state", "error_class", "manual_review_subreason", "write_date"),
        )
        dto = AttentionItemDTO(
            item_ref="attn:manual_review_job:%d:%d" % (job.id, state_version),
            state_version=state_version,
            provider="manual_review_job",
            workflow=self._workflow_for_job(job),
            severity=severity,
            title=title,
            impact_summary=impact,
            age_seconds=self._age_seconds(observed, now),
            owner_role=owner,
            store_id=job.store_id.id,
            run_ref="job:%d" % job.id,
            allowed_actions=tuple(actions),
        )
        return dto, {
            "kind": "job",
            "record": job,
            "observed_at": observed,
            "what_happened": self._job_what_happened(job),
        }

    @api.model
    def _mutation_attention(self, attempt, now, capability=None):
        capability = capability or capability_for(self._current_role())
        job = attempt.job_id
        actions = [
            AllowedActionDTO(
                key="open_run",
                label=_("Open run evidence"),
                item_ref="job:%d" % job.id if job else None,
            )
        ]
        if capability.can_configure:
            actions.append(
                AllowedActionDTO(
                    key="resolve_mutation",
                    label=_("Resolve remote outcome"),
                    item_ref="job:%d" % job.id if job else None,
                    required_role=Role.ADMINISTRATOR.value,
                    requires_reason=True,
                )
            )
        observed = attempt.created_at or now
        version = self._state_version(
            attempt,
            (
                "observed_outcome",
                "merchant_write_status",
                "resolution_disposition",
                "write_date",
            ),
        )
        dto = AttentionItemDTO(
            item_ref="attn:mutation_uncertainty:%d:%d" % (attempt.id, version),
            state_version=version,
            provider="mutation_uncertainty",
            workflow=self._workflow_from_mutation(attempt),
            severity="critical",
            title=_("Shopify's remote outcome still needs verification."),
            impact_summary=_(
                "The connector will not blindly resend an uncertain mutation."
            ),
            age_seconds=self._age_seconds(observed, now),
            owner_role=Role.ADMINISTRATOR.value,
            store_id=attempt.store_id.id,
            run_ref="job:%d" % job.id if job else None,
            allowed_actions=tuple(actions),
        )
        return dto, {
            "kind": "mutation",
            "record": attempt,
            "observed_at": observed,
            "what_happened": _(
                "The request may have reached Shopify, so independent readback "
                "is required before another write."
            ),
        }

    @api.model
    def _product_attention(self, decision, now, capability=None):
        capability = capability or capability_for(self._current_role())
        job = decision.job_id
        actions = []
        if capability.can_configure:
            actions.append(
                AllowedActionDTO(
                    key="open_match_decision",
                    label=_("Review product match"),
                    item_ref="attn:product_match:%d:%d"
                    % (decision.id, self._state_version(decision, ("state", "write_date"))),
                    required_role=Role.ADMINISTRATOR.value,
                )
            )
        observed = decision.write_date or decision.create_date or now
        version = self._state_version(decision, ("state", "write_date"))
        dto = AttentionItemDTO(
            item_ref="attn:product_match:%d:%d" % (decision.id, version),
            state_version=version,
            provider="product_match",
            workflow="catalog",
            severity="critical",
            title=_("A product match needs a decision."),
            impact_summary=_(
                "Product import is held until an exact Odoo match is selected."
            ),
            age_seconds=self._age_seconds(observed, now),
            owner_role=Role.ADMINISTRATOR.value,
            store_id=decision.store_id.id,
            run_ref="job:%d" % job.id if job else None,
            allowed_actions=tuple(actions),
        )
        return dto, {
            "kind": "product_match",
            "record": decision,
            "observed_at": observed,
            "what_happened": _(
                "The importer found more than one eligible product candidate."
            ),
        }

    @api.model
    def _inventory_attentions(self, store, now, capability=None):
        capability = capability or capability_for(self._current_role())
        Location = self._optional_model("shopify.connector.location")
        MappingModel = self._optional_model("shopify.connector.location.mapping")
        if Location is None or MappingModel is None:
            return []
        locations = self._safe_search(
            Location,
            [("store_id", "=", store.id), ("shopify_location_active", "=", True)],
            order="id asc",
            limit=self.MAX_ATTENTION_ITEMS + 1,
        )
        mappings = self._safe_search(
            MappingModel,
            [("store_id", "=", store.id)],
            order="id asc",
            limit=self.MAX_ATTENTION_ITEMS + 1,
        )
        mapped = {
            mapping.shopify_gid
            for mapping in mappings
            if "shopify_gid" in mapping._fields and mapping.shopify_gid
        }
        # Preserve one unmatched sentinel after the provider post-filter.  If
        # the first bounded location page is fully mapped, no false
        # ``has_more`` signal is emitted; if it contains more unresolved
        # mappings, the sentinel survives to the aggregate cap.
        return [
            self._inventory_location_attention(location, now, capability)
            for location in locations
            if location.shopify_location_gid not in mapped
        ][: self.MAX_ATTENTION_ITEMS + 1]

    @api.model
    def _inventory_location_attention(self, location, now, capability=None):
        capability = capability or capability_for(self._current_role())
        version = self._state_version(
            location,
            ("shopify_location_active", "name", "write_date"),
        )
        dto = AttentionItemDTO(
            item_ref="attn:inventory_mapping:%d:%d" % (location.id, version),
            state_version=version,
            provider="inventory_mapping",
            workflow="inventory",
            severity="critical",
            title=_("A Shopify location needs an Odoo mapping."),
            impact_summary=_(
                "Inventory work for this location is held until mapping is explicit."
            ),
            age_seconds=self._age_seconds(location.last_synced_at or location.write_date, now),
            owner_role=Role.ADMINISTRATOR.value,
            store_id=location.store_id.id,
            run_ref=None,
            allowed_actions=(
                AllowedActionDTO(
                    key="map_location_and_preview",
                    label=_("Map location and preview"),
                    item_ref="attn:inventory_mapping:%d:%d" % (location.id, version),
                    required_role=Role.ADMINISTRATOR.value,
                ),
            ) if capability.can_configure else (),
        )
        observed = location.last_synced_at or location.write_date or now
        return dto, {
            "kind": "inventory_location",
            "record": location,
            "observed_at": observed,
            "what_happened": _(
                "Shopify reported an active location for which no explicit "
                "Odoo mapping is recorded."
            ),
        }

    @api.model
    def _fulfillment_attention(self, review, now, capability=None):
        version = self._state_version(review, ("reconciled_state", "review_reason", "write_date"))
        observed = review.last_observed_at or review.write_date or now
        dto = AttentionItemDTO(
            item_ref="attn:fulfillment_review:%d:%d" % (review.id, version),
            state_version=version,
            provider="fulfillment_review",
            workflow="fulfillment",
            severity="critical",
            title=_("A fulfillment observation needs review."),
            impact_summary=_("Fulfillment evidence is held until an operator resolves it."),
            age_seconds=self._age_seconds(observed, now),
            owner_role=Role.ADMINISTRATOR.value,
            store_id=review.store_id.id,
            run_ref=None,
            allowed_actions=(
                AllowedActionDTO(
                    key="open_fulfillment_review",
                    label=_("Open fulfillment review"),
                    item_ref="attn:fulfillment_review:%d:%d" % (review.id, version),
                ),
            ),
        )
        return dto, {
            "kind": "fulfillment_review",
            "record": review,
            "observed_at": observed,
            "what_happened": _(
                "The fulfillment observation could not be reconciled safely."
            ),
        }

    @api.model
    def _readiness_attention(self, store, now, capability=None):
        capability = capability or capability_for(self._current_role())
        version = self._state_version(
            store,
            ("last_readiness_result", "last_readiness_at", "write_date"),
        )
        dto = AttentionItemDTO(
            item_ref="attn:readiness_failure:%d:%d" % (store.id, version),
            state_version=version,
            provider="readiness_failure",
            workflow="setup",
            severity="critical",
            title=_("Store readiness checks did not pass."),
            impact_summary=_("Activation or a workflow change is blocked until repaired."),
            age_seconds=self._age_seconds(store.last_readiness_at or store.write_date, now),
            owner_role=Role.ADMINISTRATOR.value,
            store_id=store.id,
            run_ref=None,
            allowed_actions=(
                AllowedActionDTO(
                    key="repair_setup",
                    label=_("Repair setup"),
                    item_ref="attn:readiness_failure:%d:%d" % (store.id, version),
                    required_role=Role.ADMINISTRATOR.value,
                ),
            ) if capability.can_configure else (),
        )
        observed = store.last_readiness_at or store.write_date or now
        return dto, {
            "kind": "readiness",
            "record": store,
            "observed_at": observed,
            "what_happened": _(
                "The last stored readiness evaluation reported a failure."
            ),
        }

    @classmethod
    def _matches_attention_filter(cls, row, filters):
        dto, _meta = row
        if filters.get("severity") and dto.severity != filters["severity"]:
            return False
        if filters.get("workflow") and dto.workflow != filters["workflow"]:
            return False
        if filters.get("owner_role") and dto.owner_role != filters["owner_role"]:
            return False
        if filters.get("action_key") and not any(
            action.key == filters["action_key"] for action in dto.allowed_actions
        ):
            return False
        query = filters.get("q", "").strip().lower()
        if query and query not in (dto.title + " " + dto.impact_summary).lower():
            return False
        return True

    @classmethod
    def _attention_sort_key(cls, row):
        dto, _meta = row
        return (
            -cls._SEVERITY_RANK.get(dto.severity, 0),
            -dto.age_seconds,
            cls._PROVIDER_RANK.get(dto.provider, 99),
            dto.item_ref,
        )

    @api.model
    def _attention_detail(self, dto, meta, now):
        record = meta.get("record")
        groups = []
        history = []
        if meta.get("kind") == "job":
            groups.append(
                EvidenceGroupDTO(
                    key="safety_decision",
                    label=_("Safety decision"),
                    rows=(
                        {"label": _("Job state"), "value": self._selection_label(record, "state")},
                        {"label": _("Workflow"), "value": self._workflow_for_job(record)},
                        {"label": _("Error class"), "value": self._selection_label(record, "error_class") or _("Not classified")},
                    ),
                )
            )
            history = [
                self._history_row(log)
                for log in self._search_job_logs(record, self.MAX_HISTORY_EVENTS)
            ]
        elif meta.get("kind") == "mutation":
            groups.append(
                EvidenceGroupDTO(
                    key="safety_decision",
                    label=_("Safety decision"),
                    rows=(
                        {"label": _("Observed outcome"), "value": self._selection_label(record, "observed_outcome")},
                        {"label": _("Merchant status"), "value": self._selection_label(record, "merchant_write_status")},
                        {"label": _("Transport attempted"), "value": _("Yes") if record.transport_attempted else _("No")},
                    ),
                )
            )
        elif meta.get("kind") == "product_match":
            groups.append(
                EvidenceGroupDTO(
                    key="incoming",
                    label=_("Incoming evidence"),
                    rows=(
                        {"label": _("Decision level"), "value": self._selection_label(record, "decision_level")},
                        {"label": _("Match key"), "value": self._selection_label(record, "match_key")},
                        {"label": _("Candidates"), "value": int(record.candidate_total or 0)},
                    ),
                )
            )
        elif meta.get("kind") == "inventory_location":
            groups.append(
                EvidenceGroupDTO(
                    key="incoming",
                    label=_("Incoming evidence"),
                    rows=(
                        {"label": _("Shopify location"), "value": self._safe_text(record.name)},
                        {"label": _("Mapping"), "value": _("Not mapped")},
                    ),
                )
            )
        elif meta.get("kind") == "fulfillment_review":
            groups.append(
                EvidenceGroupDTO(
                    key="incoming",
                    label=_("Incoming evidence"),
                    rows=(
                        {"label": _("Review reason"), "value": self._selection_label(record, "review_reason") or _("Not classified")},
                        {"label": _("Observation state"), "value": self._selection_label(record, "reconciled_state")},
                    ),
                )
            )
        elif meta.get("kind") == "readiness":
            groups.append(
                EvidenceGroupDTO(
                    key="current_state",
                    label=_("Current Odoo state"),
                    rows=(
                        {"label": _("Readiness result"), "value": _("Failed")},
                        {"label": _("Connection"), "value": self._selection_label(record, "state")},
                    ),
                )
            )
        return AttentionDetailDTO(
            item_ref=dto.item_ref,
            state_version=dto.state_version,
            provider=dto.provider,
            workflow=dto.workflow,
            severity=dto.severity,
            title=dto.title,
            impact_summary=dto.impact_summary,
            age_seconds=dto.age_seconds,
            owner_role=dto.owner_role,
            store_id=dto.store_id,
            run_ref=dto.run_ref,
            allowed_actions=dto.allowed_actions,
            what_happened=meta.get("what_happened") or _("Review the evidence before acting."),
            impact={"held_records": 1, "unit": _("connector case")},
            evidence_groups=tuple(groups),
            history=tuple(history),
        )


__all__ = ["ShopifyConnectorUiFacadeAttentionMixin"]
