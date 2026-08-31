"""Run projection for the P02 read-only UI facade."""

from __future__ import annotations

from odoo import _, api
from odoo.exceptions import AccessError, UserError

from ..domain.authorization import capability_for
from ..domain.dto import AllowedActionDTO, RunDTO, TimelineEventDTO
from ..domain.identifiers import require_run_ref
from ..domain.states import Role, RunState


class ShopifyConnectorUiFacadeRunMixin:
    @api.model
    def get_run_v1(self, store_id, run_ref):
        """Return one bounded legacy-job or aggregate-run projection.

        The prefix is an opaque route discriminator, never a model name.  A
        ``job:`` reference projects one legacy job; a ``run:`` reference
        resolves the additive run row and only its same-store/company jobs.
        Both paths therefore retain the exact active-company and record-rule
        boundary used by the rest of the facade.
        """
        store = self._require_store(store_id)
        if not isinstance(run_ref, str):
            raise UserError(_("The run reference must be a string."))
        try:
            require_run_ref(run_ref)
        except (TypeError, ValueError) as exc:
            raise UserError(_("The run reference is invalid.")) from exc
        try:
            reference_id = int(run_ref.split(":", 1)[1])
        except (TypeError, ValueError) as exc:  # defensive after validator
            raise UserError(_("The run reference is invalid.")) from exc
        if run_ref.startswith("run:"):
            return self._get_run_aggregate(store, reference_id, run_ref)
        if not run_ref.startswith("job:"):
            raise UserError(_("This run reference is not available yet."))
        Job = self.env["shopify.connector.job"]
        job = Job.search(
            [
                ("id", "=", reference_id),
                ("store_id", "=", store.id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not job:
            raise AccessError(
                _("The requested run is not available in the active store.")
            )
        job.ensure_one()
        now = self._now_utc()
        raw_logs = self._search_job_logs(
            job,
            limit=self.MAX_TIMELINE_EVENTS,
            include_sentinel=True,
        )
        logs = raw_logs[: self.MAX_TIMELINE_EVENTS]
        attempt = self._mutation_for_job(job)
        run = RunDTO(
            run_ref=run_ref,
            display_name="RUN-%06d" % job.id,
            state=self._run_state(job.state),
            workflow=self._workflow_for_job(job),
            operation=self._operation_for_job(job),
            store={"id": store.id, "name": self._safe_text(store.name)},
            trigger=self._trigger_for_job(job),
            scope={
                "label": self._safe_text(job.operation_scope_key)
                or _("Connector operation"),
                "operation_scope_key": self._safe_text(
                    job.operation_scope_key,
                ),
            },
            configuration_generation=max(
                0, int(job.expected_connection_generation or 0),
            ),
            result=self._run_result(job, attempt),
            jobs=(self._job_dto(job, attempt),),
            timeline=tuple(self._timeline_dto(log) for log in logs),
            affected_records=tuple(self._affected_record(job)),
            allowed_actions=tuple(self._run_actions(job, attempt)),
            truncation={
                "jobs": False,
                "timeline": len(raw_logs) > self.MAX_TIMELINE_EVENTS,
                "logs": len(raw_logs) > self.MAX_TIMELINE_EVENTS,
                "affected_records": False,
                "allowed_actions": False,
                "limits": {
                    "jobs": 1,
                    "timeline": self.MAX_TIMELINE_EVENTS,
                    "logs": self.MAX_TIMELINE_EVENTS,
                    "affected_records": self.MAX_AFFECTED_RECORDS,
                    "allowed_actions": self.MAX_RUN_ACTIONS,
                },
            },
        )
        through = self._oldest_observation(
            store,
            None,
            (job,),
            [log.occurred_at for log in logs],
        )
        return self._envelope(store, run, through=through, now=now)

    @api.model
    def _get_run_aggregate(self, store, run_id, run_ref):
        """Project one additive run and a bounded set of child jobs."""
        if "shopify.connector.run" not in self.env:
            raise UserError(_("Aggregate run records are not available yet."))
        Run = self.env["shopify.connector.run"]
        durable_run = Run.search(
            [
                ("id", "=", run_id),
                ("store_id", "=", store.id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not durable_run:
            raise AccessError(
                _("The requested run is not available in the active store.")
            )
        durable_run.ensure_one()

        Job = self.env["shopify.connector.job"]
        raw_jobs = Job.search(
            [
                ("run_id", "=", durable_run.id),
                ("store_id", "=", store.id),
                ("company_id", "=", self.env.company.id),
            ],
            order="sequence asc, id asc",
            limit=self.MAX_TIMELINE_EVENTS + 1,
        )
        jobs = raw_jobs[: self.MAX_TIMELINE_EVENTS]
        jobs_truncated = len(raw_jobs) > self.MAX_TIMELINE_EVENTS
        attempts_by_job = self._mutations_for_jobs(jobs)
        Log = self.env["shopify.connector.job.log"]
        logs = Log.search(
            [
                ("job_id", "in", jobs.ids),
                ("store_id", "=", store.id),
                ("company_id", "=", self.env.company.id),
            ],
            order="occurred_at asc, id asc",
            limit=self.MAX_TIMELINE_EVENTS + 1,
        ) if jobs else Log.browse()
        job_attempts = [
            (job, attempts_by_job.get(job.id)) for job in jobs
        ]
        actions = []
        action_keys = set()
        actions_truncated = jobs_truncated
        affected = []
        affected_keys = set()
        affected_truncated = False
        for job, attempt in job_attempts:
            for action in self._run_actions(job, attempt):
                key = (action.key, action.item_ref)
                if key not in action_keys:
                    action_keys.add(key)
                    if len(actions) >= self.MAX_RUN_ACTIONS:
                        actions_truncated = True
                    else:
                        actions.append(action)
            for record in self._affected_record(job):
                key = (record.get("model"), record.get("id"))
                if key not in affected_keys:
                    if len(affected) >= self.MAX_AFFECTED_RECORDS:
                        affected_truncated = True
                        break
                    affected_keys.add(key)
                    affected.append(record)

        all_logs = [log for log in logs[: self.MAX_TIMELINE_EVENTS]]
        state = self._aggregate_run_state(durable_run, jobs)
        result = self._aggregate_run_result(
            durable_run, state, job_attempts,
        )
        workflow = self._safe_text(
            getattr(durable_run, "workflow", False),
        ).lower() or "connector"
        operation = self._safe_text(
            getattr(durable_run, "operation", False),
        ).lower() or "connector_operation"
        generation = getattr(
            durable_run, "expected_configuration_generation", None,
        )
        if generation is None:
            generation = getattr(
                durable_run, "expected_connection_generation", 0,
            )
        try:
            generation = max(0, int(generation or 0))
        except (TypeError, ValueError):
            generation = 0
        scope_summary = self._safe_text(
            getattr(durable_run, "scope_summary", False),
        ) or _("Connector operation")
        scope_fingerprint = self._safe_text(
            getattr(durable_run, "scope_fingerprint", False),
        )
        run = RunDTO(
            run_ref=run_ref,
            display_name=self._safe_text(
                getattr(durable_run, "name", False),
            ) or "RUN-%06d" % durable_run.id,
            state=state,
            workflow=workflow,
            operation=operation,
            store={"id": store.id, "name": self._safe_text(store.name)},
            trigger=self._trigger_for_run(durable_run),
            scope={
                "label": scope_summary,
                "operation_scope_key": scope_fingerprint,
            },
            configuration_generation=generation,
            result=result,
            jobs=tuple(
                self._job_dto(job, attempt)
                for job, attempt in job_attempts
            ),
            timeline=tuple(self._timeline_dto(log) for log in all_logs),
            affected_records=tuple(affected),
            allowed_actions=tuple(actions),
            truncation={
                "jobs": jobs_truncated,
                # Logs and affected records are queried only for the bounded
                # child-job projection.  If a child was omitted, those
                # projections are necessarily partial even when their own
                # visible query did not reach 201 rows.
                "timeline": (
                    jobs_truncated or len(logs) > self.MAX_TIMELINE_EVENTS
                ),
                "logs": (
                    jobs_truncated or len(logs) > self.MAX_TIMELINE_EVENTS
                ),
                "affected_records": affected_truncated or jobs_truncated,
                "allowed_actions": actions_truncated,
                "limits": {
                    "jobs": self.MAX_TIMELINE_EVENTS,
                    "timeline": self.MAX_TIMELINE_EVENTS,
                    "logs": self.MAX_TIMELINE_EVENTS,
                    "affected_records": self.MAX_AFFECTED_RECORDS,
                    "allowed_actions": self.MAX_RUN_ACTIONS,
                },
            },
        )
        observations = [
            getattr(durable_run, name, None)
            for name in ("requested_at", "admitted_at", "finished_at")
        ]
        through = self._oldest_observation(
            store, None, tuple(jobs), observations + [
                log.occurred_at for log in all_logs
            ],
        )
        now = self._now_utc()
        return self._envelope(store, run, through=through, now=now)

    @api.model
    def _mutations_for_jobs(self, jobs):
        """Load latest optional mutation evidence in one bounded query."""
        if not jobs:
            return {}
        Attempt = self._optional_model("shopify.connector.mutation.attempt")
        if Attempt is None:
            return {}
        attempts = self._safe_search(
            Attempt,
            [("job_id", "in", jobs.ids)],
            order="id desc",
            # The mutation-attempt model has a database unique index on
            # job_id.  One sentinel still turns pre-existing/corrupt duplicate
            # evidence into a visible failure instead of hiding another job.
            limit=max(1, len(jobs) + 1),
        )
        result = {}
        for attempt in attempts:
            job_id = attempt.job_id.id
            if job_id in result:
                raise UserError(_(
                    "Duplicate mutation evidence prevents a complete run projection."
                ))
            result[job_id] = attempt
        return result

    @classmethod
    def _aggregate_run_state(cls, durable_run, jobs):
        value = getattr(durable_run, "state", False)
        valid = {item.value for item in RunState}
        if value in valid:
            return value
        child_states = [cls._run_state(job.state) for job in jobs]
        if not child_states:
            return RunState.REQUESTED.value
        if any(item == RunState.BLOCKED_MANUAL_REVIEW.value for item in child_states):
            return RunState.BLOCKED_MANUAL_REVIEW.value
        if any(item == RunState.FAILED_TERMINAL.value for item in child_states):
            return RunState.FAILED_TERMINAL.value
        if any(item == RunState.FAILED_RETRYABLE.value for item in child_states):
            return RunState.FAILED_RETRYABLE.value
        if any(item == RunState.RUNNING.value for item in child_states):
            return RunState.RUNNING.value
        if any(item == RunState.WAITING.value for item in child_states):
            return RunState.WAITING.value
        if all(item == RunState.SUCCEEDED.value for item in child_states):
            return RunState.SUCCEEDED.value
        return RunState.PARTIALLY_SUCCEEDED.value

    @api.model
    def _aggregate_run_result(self, durable_run, state, job_attempts):
        uncertain = next(
            (
                (job, attempt) for job, attempt in job_attempts
                if attempt and attempt.observed_outcome == "uncertain"
            ),
            None,
        )
        if uncertain:
            return self._run_result(uncertain[0], uncertain[1])
        summary = self._safe_text(
            getattr(durable_run, "result_summary", False),
        )
        titles = {
            RunState.SUCCEEDED.value: (
                _("Run completed"),
                _("The stored operation completed."),
            ),
            RunState.PARTIALLY_SUCCEEDED.value: (
                _("Run partially completed"),
                _("Some parts completed and some require review."),
            ),
            RunState.FAILED_RETRYABLE.value: (
                _("Retry available"),
                _("A bounded retry is available."),
            ),
            RunState.BLOCKED_MANUAL_REVIEW.value: (
                _("Decision required"),
                _("An administrator must resolve the review."),
            ),
            RunState.FAILED_TERMINAL.value: (
                _("Investigation required"),
                _("The run ended without a safe automatic completion."),
            ),
            RunState.CANCELLED.value: (
                _("Run cancelled"),
                _("The connector recorded a local cancellation."),
            ),
        }
        title, message = titles.get(
            state,
            (_("Run in progress"), _("The connector has not reached a terminal state.")),
        )
        if summary:
            message = summary
        return {"title": title, "message": message, "safe_next_action": None}

    @api.model
    def _trigger_for_run(self, durable_run):
        trigger = getattr(durable_run, "trigger", False) or "system"
        return {
            "type": trigger,
            "label": self._selection_label(durable_run, "trigger") or trigger,
            "actor": None,
        }

    @api.model
    def _job_dto(self, job, attempt):
        return {
            "id": job.id,
            "state": job.state,
            "state_label": self._selection_label(job, "state"),
            "workflow": self._workflow_for_job(job),
            "operation": self._operation_for_job(job),
            "source": self._selection_label(job, "job_source"),
            "retry_count": max(0, int(job.retry_count or 0)),
            "error_class": self._selection_label(job, "error_class") or None,
            "merchant_write_status": self._selection_label(job, "merchant_write_status") or None,
            "attempt_id": attempt.id if attempt else None,
        }

    @api.model
    def _run_result(self, job, attempt):
        if attempt and attempt.observed_outcome == "uncertain":
            return {
                "title": _("Remote outcome uncertain"),
                "message": _(
                    "The connector is reading Shopify before deciding whether "
                    "another attempt is safe."
                ),
                "safe_next_action": None,
            }
        messages = {
            "succeeded": (_("Run completed"), _("The stored operation completed.")),
            "failed_retryable": (_("Retry available"), _("A bounded retry is available.")),
            "failed_final": (
                _("Investigation required"),
                _("The run ended without a safe automatic completion."),
            ),
            "blocked_manual_review": (
                _("Decision required"),
                _("An administrator must resolve the review."),
            ),
            "cancelled": (_("Run cancelled"), _("The connector recorded a local cancellation.")),
        }
        title, message = messages.get(
            job.state,
            (_("Run in progress"), _("The connector has not reached a terminal state.")),
        )
        return {"title": title, "message": message, "safe_next_action": None}

    @api.model
    def _run_actions(self, job, attempt):
        capability = capability_for(self._current_role())
        result = []
        if job.state == "failed_retryable" and capability.can_operate:
            result.append(
                AllowedActionDTO(
                    key="retry_job",
                    label=_("Retry safely"),
                    item_ref="job:%d" % job.id,
                    required_role=Role.OPERATOR.value,
                )
            )
        if job.state == "blocked_manual_review" and capability.can_configure:
            result.append(
                AllowedActionDTO(
                    key="resolve_manual_review",
                    label=_("Resolve review"),
                    item_ref="job:%d" % job.id,
                    required_role=Role.ADMINISTRATOR.value,
                    requires_reason=True,
                )
            )
        if attempt and attempt.observed_outcome == "uncertain" and capability.can_configure:
            result.append(
                AllowedActionDTO(
                    key="resolve_mutation",
                    label=_("Resolve remote outcome"),
                    item_ref="job:%d" % job.id,
                    required_role=Role.ADMINISTRATOR.value,
                    requires_reason=True,
                )
            )
        # A run's affected-record projection is deliberately read-only, but
        # its native target must also be present in the run authority set.  A
        # browser record link is executable only after the controller finds
        # this exact key/ref/target tuple in ``allowed_actions``.  Reuse the
        # bounded, store/company-authorized projection so no model, domain, or
        # action target is inferred from job metadata in the browser.
        for record in self._affected_record(job):
            action_key = record.get("action_key")
            item_ref = record.get("item_ref")
            target = record.get("target")
            if (
                isinstance(action_key, str)
                and action_key
                and isinstance(item_ref, str)
                and item_ref
                and isinstance(target, dict)
            ):
                result.append(
                    AllowedActionDTO(
                        key=action_key,
                        label=_("Open affected record"),
                        item_ref=item_ref,
                        target=target,
                    )
                )
            # ``_affected_record`` is itself bounded to one record today.  A
            # break keeps this action projection bounded if that provider is
            # extended later without silently growing one job's action set.
            break
        return result

    @api.model
    def _timeline_dto(self, log):
        occurred = self._as_utc(log.occurred_at or log.create_date or self._now_utc())
        return TimelineEventDTO(
            event_id=log.id,
            occurred_at=occurred,
            kind=log.event_type or "note",
            tone=self._timeline_tone(log),
            title=self._selection_label(log, "event_type") or _("Connector event"),
            detail=self._safe_text(log.message) or _("No operator message recorded."),
            technical_detail_available=bool(log.technical_detail),
        )

    @api.model
    def _history_row(self, log):
        return self._serialize(self._timeline_dto(log))

    @staticmethod
    def _timeline_tone(log):
        if log.to_state in ("failed_final", "blocked_manual_review"):
            return "warning"
        if log.to_state == "succeeded":
            return "positive"
        return "neutral"

    @api.model
    def _trigger_for_job(self, job):
        return {
            "type": job.job_source or "system",
            "label": self._selection_label(job, "job_source") or _("System"),
            "actor": None,
        }

    @api.model
    def _affected_record(self, job):
        model_name = job.res_model
        record_id = job.res_id
        allowlisted = {
            "shopify.connector.store",
            "shopify.connector.product.template.binding",
            "shopify.connector.product.variant.binding",
            "shopify.connector.order.binding",
            "shopify.connector.inventory.level.binding",
            "shopify.connector.fulfillment.binding",
            "stock.picking",
        }
        if (
            not isinstance(model_name, str)
            or model_name not in allowlisted
            or isinstance(record_id, bool)
            or not isinstance(record_id, int)
            or record_id <= 0
            or model_name not in self.env
        ):
            return []
        Model = self.env[model_name]
        if model_name != "shopify.connector.store" and "store_id" not in Model._fields:
            return []
        domain = [("id", "=", record_id)]
        if model_name == "shopify.connector.store":
            domain.append(("company_id", "=", job.company_id.id))
        else:
            domain.append(("store_id", "=", job.store_id.id))
            if "company_id" in Model._fields and job.company_id:
                domain.append(("company_id", "=", job.company_id.id))
        try:
            record = Model.search(domain, limit=1)
        except AccessError:
            return []
        if not record:
            return []
        target = self._authorized_native_record_target(
            record,
            job.store_id,
            action_key="open_native_record",
        )
        if not target:
            return []
        return [{
            "model": model_name,
            "id": record.id,
            "item_ref": "%s:%d" % (model_name, record.id),
            "action_key": "open_native_record",
            "target": target,
        }]

    @api.model
    def _mutation_for_job(self, job):
        Attempt = self._optional_model("shopify.connector.mutation.attempt")
        if Attempt is None:
            return None
        attempts = self._safe_search(
            Attempt,
            [("job_id", "=", job.id)],
            order="id desc",
            limit=1,
        )
        return attempts[0] if attempts else None


__all__ = ["ShopifyConnectorUiFacadeRunMixin"]
