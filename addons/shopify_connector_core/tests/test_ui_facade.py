"""P02 read-facade tests.

These tests exercise the query boundary as a caller would: through Odoo
users, active companies and the existing job/log records.  They intentionally
do not patch or invoke Shopify transport; a read facade has no reason to know
that transport exists.
"""

import math
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from ..domain.dto import AllowedActionDTO
from ..models.shopify_connector_ui_facade_run import (
    ShopifyConnectorUiFacadeRunMixin,
)


@tagged("post_install", "-at_install", "shopify_connector_p02")
class TestUiFacade(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env["shopify.connector.store"].sudo()
        cls.Settings = cls.env["shopify.connector.store.settings"].sudo()
        cls.Job = cls.env["shopify.connector.job"].sudo()
        cls.Log = cls.env["shopify.connector.job.log"].sudo()
        cls.admin = new_test_user(
            cls.env,
            login="p02_facade_admin",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_admin",
        )
        cls.operator = new_test_user(
            cls.env,
            login="p02_facade_operator",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_operator",
        )
        cls.auditor = new_test_user(
            cls.env,
            login="p02_facade_auditor",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_auditor",
        )
        cls.reviewer = new_test_user(
            cls.env,
            login="p02_facade_reviewer",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_reviewer",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="p02_facade_outsider",
            groups="base.group_user",
        )
        cls._seq = 0

    @classmethod
    def _store(cls, company=None, state="connected"):
        cls._seq += 1
        return cls.Store.create(
            {
                "name": "P02 Store %d" % cls._seq,
                "shop_domain": "p02-%d.myshopify.com" % cls._seq,
                "api_version": "2026-07",
                "state": state,
                "credential_present": True,
                "last_readiness_result": "pass" if state == "connected" else "fail",
                "company_id": (company or cls.env.company).id,
            }
        )

    @classmethod
    def _job(cls, store, state="failed_retryable", **extra):
        cls._seq += 1
        values = {
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_manual_maintenance",
            "state": state,
            "payload_hash": "p02-job-%d" % cls._seq,
        }
        if state in ("succeeded", "failed_final", "skipped", "cancelled"):
            values["finished_at"] = fields.Datetime.now()
        if state == "blocked_manual_review":
            values["manual_review_subreason"] = "ambiguous_match"
        values.update(extra)
        return cls.Job.create(values)

    def test_overview_golden_shape_is_json_safe_and_store_scoped(self):
        store = self._store()
        self.Settings.create(
            {
                "store_id": store.id,
                "product_domain_enabled": True,
                "sale_domain_enabled": True,
            }
        )
        self._job(store, "succeeded")
        payload = self.env["shopify.connector.ui.facade"].with_user(
            self.auditor
        ).get_overview_v1(store.id)

        self.assertEqual(payload["contract_version"], 1)
        self.assertEqual(payload["data"]["store"]["id"], store.id)
        self.assertEqual(payload["data"]["store"]["company"]["id"], store.company_id.id)
        self.assertIn("health", payload["data"])
        self.assertIn("workflows", payload["data"])
        self.assertIn("activity", payload["data"])
        self.assertIsInstance(payload["data"]["permissions"]["can_configure"], bool)

        def assert_json(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertIsInstance(key, str)
                    assert_json(item)
            elif isinstance(value, list):
                for item in value:
                    assert_json(item)
            else:
                self.assertFalse(hasattr(value, "_name"), value)

        assert_json(payload)

    def test_role_and_active_company_are_enforced_before_projection(self):
        store = self._store()
        facade = self.env["shopify.connector.ui.facade"]
        with self.assertRaises(AccessError):
            facade.with_user(self.outsider).get_overview_v1(store.id)

        company_b = self.env["res.company"].create({"name": "P02 Company B"})
        foreign = self._store(company=company_b)
        company_a_user = self.auditor.with_company(self.env.company)
        with self.assertRaises(AccessError):
            facade.with_user(company_a_user).get_overview_v1(foreign.id)

    def test_attention_is_bounded_and_invalid_payloads_fail_closed(self):
        store = self._store()
        for _index in range(85):
            self._job(store, "failed_retryable")
        facade = self.env["shopify.connector.ui.facade"].with_user(self.auditor)
        payload = facade.search_attention_v1(store.id, limit=500)
        self.assertLessEqual(len(payload["data"]["items"]), 80)
        self.assertLessEqual(payload["data"]["limit"], 80)
        self.assertEqual(payload["data"]["total"], 80)
        self.assertTrue(payload["data"]["has_more"])
        # The hard projection cap is reached in one page; the sentinel tells
        # the UI to narrow filters rather than manufacturing an empty cursor
        # page or leaking an exact count.
        self.assertIsNone(payload["data"]["next_cursor"])

        first_page = facade.search_attention_v1(store.id, limit=20)
        self.assertEqual(len(first_page["data"]["items"]), 20)
        self.assertTrue(first_page["data"]["has_more"])
        self.assertIsNotNone(first_page["data"]["next_cursor"])
        second_page = facade.search_attention_v1(
            store.id,
            limit=20,
            cursor=first_page["data"]["next_cursor"],
        )
        self.assertEqual(len(second_page["data"]["items"]), 20)
        self.assertTrue(
            {
                item["item_ref"] for item in first_page["data"]["items"]
            }.isdisjoint(
                item["item_ref"] for item in second_page["data"]["items"]
            )
        )

        with self.assertRaises(UserError):
            facade.search_attention_v1(store.id, filters=[])
        with self.assertRaises(UserError):
            facade.get_attention_v1(store.id, "attn:job:1")
        with self.assertRaises(UserError):
            facade.get_overview_v1(False)

    def test_attention_exact_aggregate_sentinel_reports_truncation(self):
        store = self._store(state="reconnect_needed")
        for _index in range(80):
            self._job(store, "failed_retryable")
        payload = self.env["shopify.connector.ui.facade"].with_user(
            self.auditor
        ).search_attention_v1(store.id, limit=80)

        self.assertEqual(len(payload["data"]["items"]), 80)
        self.assertEqual(payload["data"]["total"], 80)
        self.assertTrue(payload["data"]["has_more"])
        self.assertTrue(payload["data"]["truncated"])
        self.assertIsNone(payload["data"]["next_cursor"])

    def test_overview_attention_is_not_buried_by_recent_success_history(self):
        store = self._store()
        failed = self._job(store, "failed_retryable")
        for _index in range(205):
            self._job(store, "succeeded")

        payload = self.env["shopify.connector.ui.facade"].with_user(
            self.auditor
        ).get_overview_v1(store.id)

        self.assertIn(
            "job:%d" % failed.id,
            {
                item["run_ref"]
                for item in payload["data"]["attention"]["items"]
            },
        )

    def test_allowed_actions_are_projected_from_the_callers_role(self):
        store = self._store()
        job = self._job(store, "failed_retryable")
        facade = self.env["shopify.connector.ui.facade"]
        operator = facade.with_user(self.operator).search_attention_v1(store.id)
        auditor = facade.with_user(self.auditor).search_attention_v1(store.id)
        operator_item = next(
            item for item in operator["data"]["items"] if item["run_ref"] == "job:%d" % job.id
        )
        auditor_item = next(
            item for item in auditor["data"]["items"] if item["run_ref"] == "job:%d" % job.id
        )
        self.assertIn("retry_job", {item["key"] for item in operator_item["allowed_actions"]})
        self.assertNotIn("retry_job", {item["key"] for item in auditor_item["allowed_actions"]})

    def test_reviewer_does_not_receive_v1_admin_only_resolution_actions(self):
        store = self._store()
        job = self._job(store, "blocked_manual_review")
        facade = self.env["shopify.connector.ui.facade"]
        item = next(
            item for item in facade.with_user(self.reviewer).search_attention_v1(
                store.id,
            )["data"]["items"]
            if item["run_ref"] == "job:%d" % job.id
        )
        self.assertNotIn(
            "resolve_manual_review",
            {action["key"] for action in item["allowed_actions"]},
        )

    def test_workflow_freshness_is_truthful_and_versions_are_javascript_safe(self):
        store = self._store()
        facade = self.env["shopify.connector.ui.facade"].with_user(self.auditor)
        payload = facade.get_overview_v1(store.id)
        orders = next(
            item for item in payload["data"]["workflows"]
            if item["key"] == "orders"
        )
        self.assertIsNone(orders["freshness"]["observed_at"])
        self.assertEqual(orders["freshness"]["label"], "Not observed yet")
        version = facade._state_version(store, ("write_date",))
        self.assertLessEqual(version, (2 ** 53) - 1)

    def test_attention_detail_rechecks_opaque_version_and_redacts_pii(self):
        store = self._store()
        job = self._job(store, "failed_final", error_class="unknown_system_error")
        self.Log.create(
            {
                "job_id": job.id,
                "event_type": "note",
                "message": "Failure for alice@example.com shpat_secretvalue",
                "occurred_at": fields.Datetime.now(),
            }
        )
        facade = self.env["shopify.connector.ui.facade"].with_user(self.admin)
        search = facade.search_attention_v1(store.id)
        item = next(
            item for item in search["data"]["items"] if item["run_ref"] == "job:%d" % job.id
        )
        detail = facade.get_attention_v1(store.id, item["item_ref"])
        serialized = str(detail)
        self.assertNotIn("alice@example.com", serialized)
        self.assertNotIn("shpat_secretvalue", serialized)
        self.assertIn("evidence_groups", detail["data"])

        job.sudo().write({"state": "queued"})
        with self.assertRaises(UserError):
            facade.get_attention_v1(store.id, item["item_ref"])

    def test_run_timeline_is_bounded_and_read_only(self):
        store = self._store()
        job = self._job(store, "succeeded")
        for index in range(205):
            self.Log.create(
                {
                    "job_id": job.id,
                    "event_type": "note",
                    "message": "event %d" % index,
                    "occurred_at": fields.Datetime.now(),
                }
            )
        before = (job.state, job.write_date)
        facade = self.env["shopify.connector.ui.facade"].with_user(self.auditor)
        payload = facade.get_run_v1(store.id, "job:%d" % job.id)
        self.assertLessEqual(len(payload["data"]["timeline"]), 200)
        self.assertEqual(payload["data"]["run_ref"], "job:%d" % job.id)
        self.assertEqual(
            payload["data"]["truncation"]["limits"],
            {
                "jobs": 1,
                "timeline": 200,
                "logs": 200,
                "affected_records": 20,
                "allowed_actions": 200,
            },
        )
        self.assertEqual(
            set(payload["data"]["truncation"]),
            {
                "jobs", "timeline", "logs", "affected_records",
                "allowed_actions", "limits",
            },
        )
        self.assertEqual((job.state, job.write_date), before)

    def test_run_projection_authorizes_affected_record_action(self):
        store = self._store()
        job = self._job(
            store,
            "succeeded",
            res_model=store._name,
            res_id=store.id,
        )
        payload = self.env["shopify.connector.ui.facade"].with_user(
            self.admin
        ).get_run_v1(store.id, "job:%d" % job.id)
        data = payload["data"]
        self.assertEqual(len(data["affected_records"]), 1)
        record = data["affected_records"][0]
        native = next(
            action
            for action in data["allowed_actions"]
            if action["key"] == "open_native_record"
            and action["item_ref"] == record["item_ref"]
        )
        self.assertEqual(native["target"], record["target"])

    def test_run_actions_survive_the_affected_record_cap(self):
        store = self._store()
        run = self.env["shopify.connector.run"].with_user(self.admin)._create_service({
            "store_id": store.id,
            "workflow": "core",
            "operation": "core_dispatch_selftest",
            "trigger": "user",
            "actor_uid": self.admin.id,
            "scope_summary": "P02 bounded run projection",
            "configuration_snapshot": {},
        })
        for sequence in range(1, 22):
            self._job(
                store,
                "succeeded",
                run_id=run.id,
                sequence=sequence,
            )
        actionable = self._job(
            store,
            "failed_retryable",
            run_id=run.id,
            sequence=22,
        )

        def affected_for_job(_facade, job):
            return [{
                "model": "shopify.connector.store",
                "id": job.id,
                "item_ref": "test.record:%d" % job.id,
                "action_key": "open_native_record",
                "target": {"type": "ir.actions.act_window"},
            }]

        facade = self.env["shopify.connector.ui.facade"].with_user(self.admin)
        with patch.object(
            ShopifyConnectorUiFacadeRunMixin,
            "_affected_record",
            affected_for_job,
        ):
            payload = facade.get_run_v1(store.id, "run:%d" % run.id)
        data = payload["data"]
        self.assertEqual(len(data["affected_records"]), 20)
        self.assertTrue(data["truncation"]["affected_records"])
        self.assertFalse(data["truncation"]["allowed_actions"])
        self.assertIn(
            "job:%d" % actionable.id,
            {item["item_ref"] for item in data["allowed_actions"]},
        )

    def test_run_actions_have_an_explicit_aggregate_cap(self):
        store = self._store()
        run = self.env["shopify.connector.run"].with_user(
            self.admin
        )._create_service({
            "store_id": store.id,
            "workflow": "core",
            "operation": "core_dispatch_selftest",
            "trigger": "user",
            "actor_uid": self.admin.id,
            "scope_summary": "P02 action cap",
            "configuration_snapshot": {},
        })
        for sequence in range(1, 102):
            self._job(
                store, "succeeded", run_id=run.id, sequence=sequence,
            )

        def two_actions(_facade, job, _attempt):
            return [
                AllowedActionDTO(
                    key="retry_job",
                    label="First action",
                    item_ref="job:%d:first" % job.id,
                ),
                AllowedActionDTO(
                    key="open_run",
                    label="Second action",
                    item_ref="job:%d:second" % job.id,
                ),
            ]

        facade = self.env["shopify.connector.ui.facade"].with_user(self.admin)
        with patch.object(
            ShopifyConnectorUiFacadeRunMixin,
            "_run_actions",
            two_actions,
        ):
            payload = facade.get_run_v1(store.id, "run:%d" % run.id)
        truncation = payload["data"]["truncation"]
        self.assertEqual(len(payload["data"]["allowed_actions"]), 200)
        self.assertTrue(truncation["allowed_actions"])
        self.assertFalse(truncation["jobs"])
        self.assertEqual(
            truncation["limits"],
            {
                "jobs": 200,
                "timeline": 200,
                "logs": 200,
                "affected_records": 20,
                "allowed_actions": 200,
            },
        )

    def test_read_facade_never_enters_shopify_transport(self):
        store = self._store()
        facade = self.env["shopify.connector.ui.facade"].with_user(self.auditor)
        with patch(
            "odoo.addons.shopify_connector_core.models.shopify_connector_api_client"
            ".ShopifyConnectorApiClient.execute",
            side_effect=AssertionError("P02 read facade called Shopify"),
        ):
            facade.get_overview_v1(store.id)

    def test_application_facade_has_only_named_read_delegates_and_rechecks_role(self):
        store = self._store()
        facade = self.env["shopify.connector.application.facade"]
        result = facade.with_user(self.auditor).get_overview_v1(store.id)
        self.assertEqual(result["data"]["store"]["id"], store.id)
        with self.assertRaises(AccessError):
            facade.with_user(self.outsider).get_overview_v1(store.id)

    def test_rpc_serializer_rejects_non_json_keys_values_numbers_and_cycles(self):
        facade = self.env["shopify.connector.ui.facade"]
        with self.assertRaises(TypeError):
            facade._serialize({1: "integer key"})
        with self.assertRaises(TypeError):
            facade._serialize({"unsupported": object()})
        with self.assertRaises(ValueError):
            facade._serialize({"number": math.inf})
        cyclic = {}
        cyclic["self"] = cyclic
        with self.assertRaises(ValueError):
            facade._serialize(cyclic)
