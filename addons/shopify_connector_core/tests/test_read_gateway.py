"""P06 Odoo adapter scope and mode tests.

The transport is intentionally not patched here: these tests stop at the
adapter's authorization boundary, proving that a denied role/company cannot
reach the API client at all.  Pure gateway behavior is covered by the cheap
``tools.tests.test_v2_read_gateways`` lane.
"""

from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from ..models.shopify_connector_read_gateway import (
    READ_WORKER_CAPABILITY_CONTEXT,
    READ_WORKER_OWNER_CONTEXT,
    _READ_WORKER_CAPABILITY,
)


@tagged("post_install", "-at_install", "shopify_connector_p06")
class TestReadGatewayScope(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env["shopify.connector.store"].sudo()
        cls.auditor = new_test_user(
            cls.env,
            login="p06_read_auditor",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_auditor",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="p06_read_outsider",
            groups="base.group_user",
        )

    def _store(self, company=None):
        return self.Store.create({
            "name": "P06 read store",
            "shop_domain": "p06-read.myshopify.com",
            "api_version": "2026-07",
            "state": "connected",
            "credential_present": True,
            "company_id": (company or self.env.company).id,
        })

    def _job(self, store, state="running"):
        return self.env["shopify.connector.job"].sudo().create({
            "store_id": store.id,
            "job_source": "setup_readiness_check",
            "job_type": "core_dispatch_selftest",
            "state": state,
        })

    def _worker_gateway(self, job, store, *, actor=None, cursor=None):
        actor = actor or self.env.user
        gateway = self.env["shopify.connector.read.gateway"].with_user(actor).sudo()
        gateway = gateway.with_company(store.company_id)
        return gateway.with_context(**{
            READ_WORKER_CAPABILITY_CONTEXT: _READ_WORKER_CAPABILITY,
            READ_WORKER_OWNER_CONTEXT: (
                cursor or gateway.env.cr,
                job.id,
                store.id,
                store.company_id.id,
            ),
        })

    def test_connector_role_is_required_before_store_access(self):
        store = self._store()
        gateway = self.env["shopify.connector.read.gateway"].with_user(self.outsider)
        with self.assertRaises(AccessError):
            gateway._assert_store(store.with_user(self.outsider))

    def test_active_company_and_record_access_are_exact(self):
        company_b = self.env["res.company"].create({"name": "P06 foreign company"})
        store = self._store(company_b)
        gateway = self.env["shopify.connector.read.gateway"].with_user(self.auditor)
        with self.assertRaises(AccessError):
            gateway._assert_store(store.with_user(self.auditor))

    def test_adapter_uses_odoo19_combined_record_access_api(self):
        # Keep the assertion independent of a network response or a settings
        # mutation; the adapter calls these Odoo 19 recordset APIs directly.
        self.assertTrue(hasattr(self.env["shopify.connector.store"], "check_access"))
        self.assertTrue(hasattr(self.env["shopify.connector.store"], "has_access"))

    def test_root_without_claimed_worker_capability_is_denied(self):
        store = self._store()
        job = self._job(store)
        self.assertEqual(self.env.uid, SUPERUSER_ID)
        with self.assertRaises(AccessError):
            self.env["shopify.connector.read.gateway"]._assert_store(
                store, job=job,
            )

    def test_nonroot_sudo_cannot_borrow_worker_capability(self):
        store = self._store()
        job = self._job(store)
        gateway = self._worker_gateway(job, store, actor=self.outsider)
        self.assertTrue(gateway.env.su)
        self.assertNotEqual(gateway.env.uid, SUPERUSER_ID)
        with self.assertRaises(AccessError):
            gateway._assert_store(
                store.with_env(gateway.env), job=job.with_env(gateway.env),
            )

    def test_worker_capability_rejects_forged_state_scope_and_cursor(self):
        store = self._store()
        queued = self._job(store, state="queued")
        running = self._job(store)
        company_b = self.env["res.company"].sudo().create({
            "name": "P06 worker foreign company",
        })
        foreign_store = self.Store.create({
            "name": "P06 worker foreign store",
            "shop_domain": "p06-worker-foreign.myshopify.com",
            "api_version": "2026-07",
            "state": "connected",
            "credential_present": True,
            "company_id": company_b.id,
        })
        foreign_job = self._job(foreign_store)
        foreign_gateway = self.env["shopify.connector.read.gateway"].with_context(**{
            READ_WORKER_CAPABILITY_CONTEXT: _READ_WORKER_CAPABILITY,
            READ_WORKER_OWNER_CONTEXT: (
                self.env.cr,
                foreign_job.id,
                foreign_store.id,
                company_b.id,
            ),
        })
        other_store = self.Store.create({
            "name": "P06 other read store",
            "shop_domain": "p06-other-read.myshopify.com",
            "api_version": "2026-07",
            "state": "connected",
            "credential_present": True,
            "company_id": self.env.company.id,
        })
        cases = (
            (self._worker_gateway(queued, store), queued, store),
            (self._worker_gateway(running, store), running, other_store),
            (self._worker_gateway(running, store, cursor=object()), running, store),
            (foreign_gateway, foreign_job, foreign_store),
        )
        for gateway, job, candidate_store in cases:
            with self.subTest(job=job.id, store=candidate_store.id):
                with self.assertRaises(AccessError):
                    gateway._assert_store(
                        candidate_store.with_env(gateway.env),
                        job=job.with_env(gateway.env),
                    )

        copied = self.env["shopify.connector.read.gateway"].with_context(**{
            READ_WORKER_CAPABILITY_CONTEXT: True,
            READ_WORKER_OWNER_CONTEXT: (
                self.env.cr, running.id, store.id, store.company_id.id,
            ),
        })
        with self.assertRaises(AccessError):
            copied._assert_store(store, job=running)
