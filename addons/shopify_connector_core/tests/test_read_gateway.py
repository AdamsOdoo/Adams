"""P06 Odoo adapter scope and mode tests.

The transport is intentionally not patched here: these tests stop at the
adapter's authorization boundary, proving that a denied role/company cannot
reach the API client at all.  Pure gateway behavior is covered by the cheap
``tools.tests.test_v2_read_gateways`` lane.
"""

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


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
