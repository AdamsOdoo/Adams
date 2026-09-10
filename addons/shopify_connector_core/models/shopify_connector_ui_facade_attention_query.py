"""Bounded provider queries for the Needs-Attention projection.

The presentation DTO builder remains in ``shopify_connector_ui_facade_attention``.
This inherited query extension owns the harder completeness rule: predicates
that can be represented by a provider's ORM domain are pushed before the
provider cap, while a capped post-filter is reported as partial instead of
pretending that the first page is complete.
"""

from __future__ import annotations

from odoo import api
from odoo.exceptions import AccessError


class AttentionCollection(list):
    """List-compatible attention rows carrying bounded-read evidence."""

    __slots__ = ("truncated", "partial", "has_more", "provider_status")

    def __init__(
        self,
        rows=(),
        *,
        truncated=False,
        partial=False,
        has_more=False,
        provider_status=None,
    ):
        super().__init__(rows)
        self.truncated = bool(truncated)
        self.partial = bool(partial)
        self.has_more = bool(has_more)
        self.provider_status = dict(provider_status or {})


class ShopifyConnectorUiFacadeAttentionQueryMixin:
    """Push closed attention predicates before bounded provider searches."""

    __slots__ = ()

    _ATTENTION_WORKFLOW_TOKENS = {
        "catalog": ("product", "catalog", "export"),
        "orders": ("order", "customer", "sale"),
        "inventory": ("inventory", "stock", "location"),
        "fulfillment": ("fulfillment", "tracking"),
        "setup": ("readiness", "connection"),
    }

    @staticmethod
    def _attention_or_domain(fields, tokens):
        terms = [
            (field_name, "ilike", token)
            for field_name in fields
            for token in tokens
        ]
        if not terms:
            return []
        return ["|"] * (len(terms) - 1) + terms

    @classmethod
    def _attention_workflow_domain(cls, fields, workflow):
        tokens = cls._ATTENTION_WORKFLOW_TOKENS.get(workflow)
        if not tokens:
            return None
        return cls._attention_or_domain(fields, tokens)

    @classmethod
    def _attention_provider_filter(cls, provider, filters, capability):
        """Return ``(domain, exact, skip)`` for one closed provider.

        ``exact`` means every non-search predicate is represented by the ORM
        domain.  ``q`` is deliberately left as a presentation post-filter;
        if the provider cap is reached, the caller reports a partial result.
        """

        domain = []
        exact = True
        skip = False
        severity = filters.get("severity")
        owner_role = filters.get("owner_role")
        action_key = filters.get("action_key")
        workflow = filters.get("workflow")

        if provider == "manual_review_job":
            states = set(cls._JOB_ATTENTION_STATES)
            if severity:
                states &= {
                    "critical": {"blocked_manual_review"},
                    "warning": {"failed_retryable", "failed_final"},
                    "info": set(),
                }.get(severity, set())
            if owner_role:
                states &= {
                    "administrator": {"blocked_manual_review", "failed_final"},
                    "operator": {"failed_retryable"},
                    "auditor": set(),
                    "reviewer": set(),
                }.get(owner_role, set())
            if action_key == "retry_job":
                states &= {"failed_retryable"} if capability.can_operate else set()
            elif action_key == "resolve_manual_review":
                states &= {"blocked_manual_review"} if capability.can_configure else set()
            elif action_key not in (None, "open_run"):
                skip = True
            if not states:
                skip = True
            else:
                domain.append(("state", "in", sorted(states)))
            if workflow:
                workflow_domain = cls._attention_workflow_domain(
                    ("job_type", "original_job_type"), workflow,
                )
                if workflow == "connector":
                    exact = False
                elif workflow_domain is None:
                    skip = True
                else:
                    domain.extend(workflow_domain)
        elif provider == "mutation_uncertainty":
            if severity and severity != "critical":
                skip = True
            if owner_role and owner_role != "administrator":
                skip = True
            if action_key == "resolve_mutation" and not capability.can_configure:
                skip = True
            elif action_key not in (None, "open_run", "resolve_mutation"):
                skip = True
            if workflow:
                workflow_domain = cls._attention_workflow_domain(
                    ("job_id.job_type", "job_id.original_job_type"), workflow,
                )
                if workflow == "connector":
                    exact = False
                elif workflow_domain is None:
                    skip = True
                else:
                    domain.extend(workflow_domain)
        else:
            expected = {
                "product_match": ("critical", "administrator", "catalog", "open_match_decision"),
                "inventory_mapping": ("critical", "administrator", "inventory", "map_location_and_preview"),
                "fulfillment_review": ("critical", "administrator", "fulfillment", "open_fulfillment_review"),
                "readiness_failure": ("critical", "administrator", "setup", "repair_setup"),
            }.get(provider)
            if expected is None:
                return domain, exact, True
            expected_severity, expected_owner, expected_workflow, expected_action = expected
            if severity and severity != expected_severity:
                skip = True
            if owner_role and owner_role != expected_owner:
                skip = True
            if workflow and workflow != expected_workflow:
                skip = True
            if action_key and action_key != expected_action:
                # ``open_run`` is intentionally not advertised by these
                # providers; it is only a job-linked navigation action.
                skip = True
            if expected_action in {"map_location_and_preview", "repair_setup"} and not capability.can_configure:
                if action_key == expected_action:
                    skip = True

        # Search text is formed from translated/provider-generated copy and is
        # not a database field.  It is therefore always a safe post-filter.
        if filters.get("q"):
            exact = False
        return domain, exact, skip

    @api.model
    def _attention_provider_records(
        self, provider, model, store, base_domain, order, filters, capability,
    ):
        domain_extra, exact, skip = self._attention_provider_filter(
            provider, filters, capability,
        )
        status = {
            "truncated": False,
            "partial": False,
            "has_more": False,
            "filter_pushed": bool(exact),
        }
        if skip:
            return (), status
        if model is None or "store_id" not in model._fields:
            return (), status
        try:
            records = model.search(
                [*base_domain, *domain_extra],
                order=order,
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
        except AccessError:
            # An installed provider whose rows cannot be read is not an empty
            # provider.  Surface the unknown portion explicitly so a caller
            # cannot mistake an ACL failure for a complete clean result.
            status.update(
                partial=True,
                has_more=True,
                access_denied=True,
            )
            return (), status
        capped = len(records) > self.MAX_ATTENTION_ITEMS
        status.update(
            truncated=capped,
            partial=capped,
            has_more=capped,
        )
        return records, status

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
        capability = self._attention_capability()
        rows = []
        provider_status = {}

        # A supplied job recordset is already bounded by its caller (overview
        # uses the 200-job cap).  Filtered searches query the provider afresh so
        # a match after 81 nonmatching rows is not silently lost.
        Job = self.env["shopify.connector.job"]
        if job_records is not None and not filters:
            jobs = job_records.filtered(
                lambda job: job.state in self._JOB_ATTENTION_STATES
                and not job.superseded_by_job_id
            )[: self.MAX_ATTENTION_ITEMS + 1]
            provider_status["manual_review_job"] = {
                "truncated": len(job_records) > self.MAX_ATTENTION_ITEMS,
                "partial": len(job_records) > self.MAX_ATTENTION_ITEMS,
                "has_more": len(job_records) > self.MAX_ATTENTION_ITEMS,
                "filter_pushed": True,
            }
        else:
            jobs, status = self._attention_provider_records(
                "manual_review_job",
                Job,
                store,
                [
                    ("store_id", "=", store.id),
                    ("state", "in", self._JOB_ATTENTION_STATES),
                    ("superseded_by_job_id", "=", False),
                ],
                "write_date desc, id desc",
                filters,
                capability,
            )
            provider_status["manual_review_job"] = status
        rows.extend(
            self._job_attention(job, now, capability)
            for job in jobs
        )

        Attempt = self._optional_model("shopify.connector.mutation.attempt")
        if Attempt is not None:
            attempts, status = self._attention_provider_records(
                "mutation_uncertainty",
                Attempt,
                store,
                [
                    ("store_id", "=", store.id),
                    ("observed_outcome", "=", "uncertain"),
                    ("resolution_disposition", "=", False),
                ],
                "created_at desc, id desc",
                filters,
                capability,
            )
            provider_status["mutation_uncertainty"] = status
            rows.extend(
                self._mutation_attention(attempt, now, capability)
                for attempt in attempts
            )

        Decision = self._optional_model("shopify.connector.product.match.decision")
        if Decision is not None:
            decisions, status = self._attention_provider_records(
                "product_match",
                Decision,
                store,
                [("store_id", "=", store.id), ("state", "=", "pending")],
                "id desc",
                filters,
                capability,
            )
            provider_status["product_match"] = status
            rows.extend(
                self._product_attention(decision, now, capability)
                for decision in decisions
            )

        inventory = self._inventory_attentions(
            store, now, capability, filters=filters,
        )
        provider_status["inventory_mapping"] = inventory.provider_status.get(
            "inventory_mapping", {}
        )
        rows.extend(inventory)

        Fulfillment = self._optional_model(
            "shopify.connector.fulfillment.inbound.evidence",
        )
        if Fulfillment is not None:
            reviews, status = self._attention_provider_records(
                "fulfillment_review",
                Fulfillment,
                store,
                [("store_id", "=", store.id), ("reconciled_state", "=", "review")],
                "last_observed_at desc, id desc",
                filters,
                capability,
            )
            provider_status["fulfillment_review"] = status
            rows.extend(
                self._fulfillment_attention(review, now, capability)
                for review in reviews
            )

        readiness_status = {
            "truncated": False,
            "partial": False,
            "has_more": False,
            "filter_pushed": True,
        }
        if store.last_readiness_result == "fail":
            _domain, _exact, skip = self._attention_provider_filter(
                "readiness_failure", filters, capability,
            )
            if not skip:
                rows.append(self._readiness_attention(store, now, capability))
        provider_status["readiness_failure"] = readiness_status

        filtered = [
            row for row in rows
            if row and self._matches_attention_filter(row, filters)
        ]
        filtered.sort(key=self._attention_sort_key)
        result_limit = self.MAX_ATTENTION_ITEMS + (1 if include_sentinel else 0)
        truncated = any(item.get("truncated") for item in provider_status.values())
        partial = any(item.get("partial") for item in provider_status.values())
        has_more = any(item.get("has_more") for item in provider_status.values())
        # The public projection exposes at most MAX rows.  With a sentinel
        # request, exactly MAX+1 aggregate matches already proves omission;
        # comparing against result_limit would falsely report that boundary
        # as complete.
        if len(filtered) > self.MAX_ATTENTION_ITEMS:
            has_more = True
            truncated = True
        return AttentionCollection(
            filtered[:result_limit],
            truncated=truncated,
            partial=partial,
            has_more=has_more,
            provider_status=provider_status,
        )

    @api.model
    def _attention_capability(self):
        from ..domain.authorization import capability_for

        return capability_for(self._current_role())

    @api.model
    def _inventory_attentions(
        self, store, now, capability=None, *, filters=None,
    ):
        capability = capability or self._attention_capability()
        filters = filters or {}
        Location = self._optional_model("shopify.connector.location")
        MappingModel = self._optional_model("shopify.connector.location.mapping")
        status = {
            "truncated": False,
            "partial": False,
            "has_more": False,
            "filter_pushed": True,
        }
        _domain, exact_filter, skip = self._attention_provider_filter(
            "inventory_mapping", filters, capability,
        )
        status["filter_pushed"] = bool(exact_filter)
        if Location is None or MappingModel is None or skip:
            return AttentionCollection(provider_status={"inventory_mapping": status})

        try:
            locations = Location.search(
                [("store_id", "=", store.id), ("shopify_location_active", "=", True)],
                order="id asc",
                limit=self.MAX_ATTENTION_ITEMS + 1,
            )
        except AccessError:
            status.update(partial=True, has_more=True, access_denied=True)
            return AttentionCollection(
                provider_status={"inventory_mapping": status},
                partial=True,
                has_more=True,
            )
        status["truncated"] = len(locations) > self.MAX_ATTENTION_ITEMS
        status["has_more"] = status["truncated"]
        rows = []
        mapping_access_unknown = False
        for location in locations[: self.MAX_ATTENTION_ITEMS + 1]:
            try:
                mapped = MappingModel.search(
                    [
                        ("store_id", "=", store.id),
                        ("shopify_gid", "=", location.shopify_location_gid),
                    ],
                    limit=1,
                )
            except AccessError:
                # A denied mapping read cannot be interpreted as unmapped.
                mapping_access_unknown = True
                continue
            if not mapped:
                row = self._inventory_location_attention(
                    location, now, capability,
                )
                if row and self._matches_attention_filter(row, filters):
                    rows.append(row)
        if mapping_access_unknown:
            status["partial"] = True
            status["has_more"] = True
        # The per-location existence checks make the mapping set complete for
        # every inspected location, including mappings whose ids are beyond 81.
        # If the location scan itself hit its cap, later locations remain
        # unknown and the response says so explicitly instead of returning a
        # false empty projection.
        if status["truncated"]:
            status["partial"] = True
            status["has_more"] = True
        rows.sort(key=self._attention_sort_key)
        if len(rows) > self.MAX_ATTENTION_ITEMS + 1:
            status["truncated"] = True
            status["has_more"] = True
        return AttentionCollection(
            rows[: self.MAX_ATTENTION_ITEMS + 1],
            truncated=status["truncated"],
            partial=status["partial"],
            has_more=status["has_more"],
            provider_status={"inventory_mapping": status},
        )


__all__ = ["AttentionCollection", "ShopifyConnectorUiFacadeAttentionQueryMixin"]
