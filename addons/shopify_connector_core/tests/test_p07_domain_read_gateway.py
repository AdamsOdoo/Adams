"""Odoo-installed scope checks for the P07 domain read adapter."""

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "shopify_connector_p07")
class TestP07DomainReadGateway(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env["shopify.connector.store"].sudo()
        cls.auditor = new_test_user(
            cls.env,
            login="p07_read_auditor",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_auditor",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="p07_read_outsider",
            groups="base.group_user",
        )

    def _store(self, company=None):
        return self.Store.create({
            "name": "P07 read store",
            "shop_domain": "p07-read.myshopify.com",
            "api_version": "2026-07",
            "state": "connected",
            "credential_present": True,
            "company_id": (company or self.env.company).id,
        })

    def test_single_core_model_exposes_all_domain_reads(self):
        gateway = self.env["shopify.connector.read.gateway"]
        for name in (
            "read_inventory_pair",
            "read_inventory_level",
            "read_fulfillment_orders",
            "read_order_fulfillments",
            "read_fulfillment",
            "read_fulfillments_batch",
            "read_webhook_subscriptions",
        ):
            self.assertTrue(callable(getattr(gateway, name)))

    def test_default_mode_is_legacy_and_scope_is_enforced(self):
        store = self._store()
        gateway = self.env["shopify.connector.read.gateway"].with_user(self.auditor)
        self.assertEqual(gateway._store_mode(store.with_user(self.auditor)), "legacy")
        with self.assertRaises(AccessError):
            self.env["shopify.connector.read.gateway"].with_user(self.outsider)._assert_store(
                store.with_user(self.outsider)
            )

    def test_foreign_active_company_is_denied_before_any_domain_read(self):
        company_b = self.env["res.company"].create({"name": "P07 foreign company"})
        store = self._store(company_b)
        gateway = self.env["shopify.connector.read.gateway"].with_user(self.auditor)
        with self.assertRaises(AccessError):
            gateway._assert_store(store.with_user(self.auditor))
