"""P04 recovery command authorization, stale-state and quiescence tests."""

from datetime import datetime, timezone
from uuid import uuid4

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "shopify_connector_p04")
class TestV2RecoveryCommands(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env["shopify.connector.store"].sudo()
        cls.Settings = cls.env["shopify.connector.store.settings"].sudo()
        cls.Run = cls.env["shopify.connector.run"]
        cls.Job = cls.env["shopify.connector.job"]
        cls.App = cls.env["shopify.connector.application.facade"]
        cls.Runtime = cls.env["shopify.connector.v2.runtime"]
        cls.Log = cls.env["shopify.connector.job.log"].sudo()
        cls.admin = new_test_user(
            cls.env,
            login="p04_recovery_admin",
            groups=(
                "base.group_user,"
                "shopify_connector_core.group_shopify_connector_admin"
            ),
        )
        cls.operator = new_test_user(
            cls.env,
            login="p04_recovery_operator",
            groups=(
                "base.group_user,"
                "shopify_connector_core.group_shopify_connector_operator"
            ),
        )
        cls.reviewer = new_test_user(
            cls.env,
            login="p04_recovery_reviewer",
            groups=(
                "base.group_user,"
                "shopify_connector_core.group_shopify_connector_reviewer"
            ),
        )
        cls._sequence = 0

    @classmethod
    def _store(cls, *, v2=False):
        cls._sequence += 1
        store = cls.Store.create({
            "name": "P04 Recovery %d" % cls._sequence,
            "shop_domain": "p04-recovery-%d.myshopify.com" % cls._sequence,
            "api_version": "2026-07",
            "state": "connected",
            "credential_present": True,
            "last_readiness_result": "pass",
        })
        settings = cls.Settings._settings_service_create(
            "_canonical_settings", {"store_id": store.id},
        )
        if v2:
            settings.with_user(cls.admin)._set_v2_modes_service(
                {"v2_runtime_mode": "read_only"},
                reason="P04 recovery test mode",
                expected_configuration_generation=0,
            )
        return store

    def _run(self, store):
        run = self.Run.with_user(self.admin)._create_service({
            "store_id": store.id,
            "workflow": "core",
            "operation": "core_dispatch_selftest",
            "trigger": "user",
            "actor_uid": self.admin.id,
            "scope_summary": "P04 recovery test",
            "configuration_snapshot": {},
        })
        run.with_user(self.admin)._admit_service()
        return run

    def _v2_job(self, run, state="queued"):
        job = self.Runtime.with_user(self.admin).enqueue_read_only_job(
            run,
            {
                "job_type": "core_dispatch_selftest",
                "job_source": "manual_sync",
                "payload_hash": str(uuid4()),
            },
        )
        if state != "queued":
            values = {"state": state}
            if state in ("succeeded", "failed_final", "skipped", "cancelled"):
                values["finished_at"] = fields.Datetime.now()
            job.sudo().write(values)
            job.invalidate_recordset()
        return job

    @staticmethod
    def _command(user, store, name, payload, *, config=None, command_id=None):
        result = {
            "contract_version": 1,
            "command_id": str(command_id or uuid4()),
            "command_name": name,
            "store_id": store.id,
            "company_id": store.company_id.id,
            "expected_generation": int(store.connection_generation or 0),
            "actor_uid": user.id,
            "trigger": "user",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        if config is not None:
            result["expected_configuration_generation"] = config
        return result

    def test_attention_retry_delegates_and_records_command_identity(self):
        store = self._store()
        job = self.Job.sudo().create({
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_manual_maintenance",
            "state": "failed_retryable",
            "payload_hash": str(uuid4()),
        })
        facade = self.env["shopify.connector.ui.facade"].with_user(self.operator)
        rows = facade.search_attention_v1(store.id, limit=10)
        item = next(
            row for row in rows["data"]["items"]
            if row["provider"] == "manual_review_job" and row["run_ref"] == "job:%d" % job.id
        )
        command = self._command(
            self.operator,
            store,
            "resolve_attention_v1",
            {
                "item_ref": item["item_ref"],
                "state_version": item["state_version"],
                "action_key": "retry_job",
                "inputs": {},
            },
            config=0,
        )
        result = self.App.with_user(self.operator).resolve_attention_v1(command)
        self.assertEqual(result["status"], "accepted")
        job.invalidate_recordset()
        self.assertEqual(job.state, "queued")
        audit = self.Log.search([
            ("job_id", "=", job.id),
            ("event_type", "=", "note"),
            ("payload_snapshot", "ilike", command["command_id"]),
        ], limit=1)
        self.assertTrue(audit)

    def test_reused_attention_command_id_cannot_cross_a_connection_generation(self):
        store = self._store()
        store._store_service_write(
            "_lifecycle", {"connection_generation": 4},
        )
        job = self.Job.sudo().create({
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_manual_maintenance",
            "state": "failed_retryable",
            "payload_hash": str(uuid4()),
        })
        facade = self.env["shopify.connector.ui.facade"].with_user(self.operator)
        item = next(
            row for row in facade.search_attention_v1(store.id, limit=10)["data"]["items"]
            if row["run_ref"] == "job:%d" % job.id
        )
        command = self._command(
            self.operator,
            store,
            "resolve_attention_v1",
            {
                "item_ref": item["item_ref"],
                "state_version": item["state_version"],
                "action_key": "retry_job",
                "inputs": {},
            },
            config=0,
            command_id=uuid4(),
        )
        first = self.App.with_user(self.operator).resolve_attention_v1(command)
        self.assertEqual(first["status"], "accepted")
        replay = self.App.with_user(self.operator).resolve_attention_v1(dict(command))
        self.assertEqual(replay["status"], "duplicate")
        self.assertEqual(replay["original_status"], "accepted")

        store._store_service_write(
            "_lifecycle", {"connection_generation": 5},
        )
        later = dict(command)
        later["expected_generation"] = 5
        with self.assertRaises(ValidationError):
            self.App.with_user(self.operator).resolve_attention_v1(later)
        job.invalidate_recordset()
        self.assertEqual(job.state, "queued")

    def test_attention_stale_version_is_conflict_and_does_not_write(self):
        store = self._store()
        job = self.Job.sudo().create({
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_manual_maintenance",
            "state": "failed_retryable",
            "payload_hash": str(uuid4()),
        })
        facade = self.env["shopify.connector.ui.facade"].with_user(self.operator)
        item = next(
            row for row in facade.search_attention_v1(store.id, limit=10)["data"]["items"]
            if row["run_ref"] == "job:%d" % job.id
        )
        job.sudo().write({"error_class": "mapping_missing"})
        result = self.App.with_user(self.operator).resolve_attention_v1(
            self._command(
                self.operator,
                store,
                "resolve_attention_v1",
                {
                    "item_ref": item["item_ref"],
                    "state_version": item["state_version"],
                    "action_key": "retry_job",
                    "inputs": {},
                },
                config=0,
            )
        )
        self.assertEqual(result["status"], "conflict")
        job.invalidate_recordset()
        self.assertEqual(job.state, "failed_retryable")

    def test_uncertain_mutation_cannot_use_retry_command(self):
        store = self._store()
        job = self.Job.sudo().create({
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_manual_maintenance",
            "state": "failed_retryable",
            "payload_hash": str(uuid4()),
        })
        from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
            ATTEMPT_WRITE_CONTEXT,
            C2_SENTINEL_CONTEXT,
            C2_SIDE_CURSOR_SENTINEL,
            CREATE_SURFACE,
        )
        attempt = self.env[
            "shopify.connector.mutation.attempt"
        ].sudo().with_context(
            **{
                ATTEMPT_WRITE_CONTEXT: CREATE_SURFACE,
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            }
        ).create({
            "job_id": job.id,
            "attempt_token": str(uuid4()),
            "mutation_domain": "mutation_dispatch_selftest",
            "observed_outcome": "uncertain",
        })
        state_version = self.env["shopify.connector.ui.facade"]._state_version(
            job,
            ("state", "error_class", "manual_review_subreason", "write_date"),
        )
        result = self.App.with_user(self.admin).retry_job_v1(
            self._command(
                self.admin,
                store,
                "retry_job_v1",
                {
                    "target_ref": "job:%d" % job.id,
                    "state_version": state_version,
                    "reason": "do not resend",
                },
            )
        )
        self.assertEqual(result["status"], "blocked")
        job.invalidate_recordset()
        attempt.invalidate_recordset()
        self.assertEqual(job.state, "failed_retryable")
        self.assertEqual(attempt.observed_outcome, "uncertain")

    def test_cancel_is_administrator_only_and_rejects_actor_spoof(self):
        store = self._store(v2=True)
        run = self._run(store)
        job = self._v2_job(run)
        version = self.env["shopify.connector.ui.facade"]._state_version(
            run,
            ("state", "cancel_requested_at", "cancel_reason", "write_date"),
        )
        with self.assertRaises(AccessError):
            self.App.with_user(self.operator).cancel_job_v1(
                self._command(
                    self.operator,
                    store,
                    "cancel_job_v1",
                    {
                        "target_ref": "run:%d" % run.id,
                        "state_version": version,
                        "reason": "operator cannot cancel a run",
                    },
                    config=1,
                )
            )
        command = self._command(
            self.operator,
            store,
            "cancel_job_v1",
            {
                "target_ref": "run:%d" % run.id,
                "state_version": version,
                "reason": "spoof",
            },
            config=1,
        )
        with self.assertRaises(AccessError):
            self.App.with_user(self.admin).cancel_job_v1(command)
        run.invalidate_recordset()
        job.invalidate_recordset()
        self.assertFalse(run.cancel_requested_at)
        self.assertEqual(job.state, "queued")

    def test_cancel_v2_run_settles_queued_but_not_running_or_uncertain(self):
        store = self._store(v2=True)
        run = self._run(store)
        queued = self._v2_job(run)
        running = self._v2_job(run, "running")
        uncertain = self._v2_job(run)
        from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
            ATTEMPT_WRITE_CONTEXT,
            C2_SENTINEL_CONTEXT,
            C2_SIDE_CURSOR_SENTINEL,
            CREATE_SURFACE,
        )
        self.env[
            "shopify.connector.mutation.attempt"
        ].sudo().with_context(
            **{
                ATTEMPT_WRITE_CONTEXT: CREATE_SURFACE,
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            }
        ).create({
            "job_id": uncertain.id,
            "attempt_token": str(uuid4()),
            "mutation_domain": "mutation_dispatch_selftest",
            "observed_outcome": "uncertain",
        })
        version = self.env["shopify.connector.ui.facade"]._state_version(
            run,
            ("state", "cancel_requested_at", "cancel_reason", "write_date"),
        )
        result = self.App.with_user(self.admin).cancel_job_v1(
            self._command(
                self.admin,
                store,
                "cancel_job_v1",
                {
                    "target_ref": "run:%d" % run.id,
                    "state_version": version,
                    "reason": "administrator requested quiescence",
                },
                config=1,
            )
        )
        self.assertEqual(result["status"], "accepted")
        self.assertGreaterEqual(result["pending"]["running"], 1)
        self.assertGreaterEqual(result["pending"]["protected"], 1)
        run.invalidate_recordset()
        queued.invalidate_recordset()
        running.invalidate_recordset()
        uncertain.invalidate_recordset()
        self.assertTrue(run.cancel_requested_at)
        self.assertEqual(queued.state, "cancelled")
        self.assertEqual(running.state, "running")
        self.assertEqual(uncertain.state, "queued")

    def test_cancel_state_version_prevents_second_concurrent_submit(self):
        store = self._store(v2=True)
        run = self._run(store)
        self._v2_job(run)
        version = self.env["shopify.connector.ui.facade"]._state_version(
            run,
            ("state", "cancel_requested_at", "cancel_reason", "write_date"),
        )
        command_id = uuid4()
        command = self._command(
            self.admin,
            store,
            "cancel_job_v1",
            {
                "target_ref": "run:%d" % run.id,
                "state_version": version,
                "reason": "one request",
            },
            config=1,
            command_id=command_id,
        )
        first = self.App.with_user(self.admin).cancel_job_v1(command)
        self.assertEqual(first["status"], "accepted")
        second = self.App.with_user(self.admin).cancel_job_v1(command)
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(second["original_status"], "accepted")

        run.invalidate_recordset()
        fresh_version = self.env["shopify.connector.ui.facade"]._state_version(
            run,
            ("state", "cancel_requested_at", "cancel_reason", "write_date"),
        )
        business_duplicate = self._command(
            self.admin,
            store,
            "cancel_job_v1",
            {
                "target_ref": "run:%d" % run.id,
                "state_version": fresh_version,
                "reason": "second distinct request",
            },
            config=1,
        )
        third = self.App.with_user(self.admin).cancel_job_v1(business_duplicate)
        self.assertEqual(third["status"], "duplicate")
        replayed_third = self.App.with_user(self.admin).cancel_job_v1(
            dict(business_duplicate)
        )
        self.assertEqual(replayed_third["status"], "duplicate")
        self.assertEqual(replayed_third["original_status"], "duplicate")


__all__ = ["TestV2RecoveryCommands"]
