import json
import uuid

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_readiness_check import (
    FULFILLMENT_ACCEPTED_API_VERSIONS,
    WRITE_SCOPE,
)


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestFulfillmentReadiness(TransactionCase):
    """Fulfillment readiness seam (D-014-2 / Q7 / Q8).

    `_get_checks` appends three fulfillment checks. When the domain is disabled
    every one is not-applicable (pass). When enabled: the write-scope check is an
    essential gate on `write_merchant_managed_fulfillment_orders` in the granted-
    scopes snapshot; the API-version check gates on the accepted compatibility
    set; the staff-permission check is a WARNING-tier NOT_PROVEN (never inferred
    from scopes). The core required-scopes swap is also asserted (read_merchant_
    managed_fulfillment_orders present, read_fulfillments absent).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Check = cls.env['shopify.connector.readiness.check']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })

    def _checks_by_code(self, store):
        return {c['code']: c for c in self.Check._get_checks(store)}

    # ------------------------------------------------------------------
    # Registration seam
    # ------------------------------------------------------------------

    def test_get_checks_includes_three_fulfillment_checks(self):
        codes = self._checks_by_code(self.store)
        for code in (
            'fulfillment_write_scope',
            'fulfillment_api_version',
            'fulfillment_staff_permission',
        ):
            self.assertIn(code, codes)

    # ------------------------------------------------------------------
    # Disabled -> all three not-applicable (pass)
    # ------------------------------------------------------------------

    def test_all_three_pass_when_fulfillment_disabled(self):
        self.settings.write({'fulfillment_domain_enabled': False})
        write_scope = self.Check._check_fulfillment_write_scope(self.store)
        api_version = self.Check._check_fulfillment_api_version(self.store)
        staff = self.Check._check_fulfillment_staff_permission(self.store)
        self.assertEqual(write_scope['result'], self.Check.RESULT_PASS)
        self.assertEqual(api_version['result'], self.Check.RESULT_PASS)
        self.assertEqual(staff['result'], self.Check.RESULT_PASS)

    # ------------------------------------------------------------------
    # Write-scope essential gate
    # ------------------------------------------------------------------

    def test_write_scope_fails_when_scope_absent(self):
        self.store.write({
            'granted_scopes': json.dumps(['read_products', 'read_orders']),
        })
        result = self.Check._check_fulfillment_write_scope(self.store)
        self.assertEqual(result['tier'], self.Check.ESSENTIAL)
        self.assertEqual(result['result'], self.Check.RESULT_FAIL)

    def test_write_scope_passes_when_scope_present(self):
        self.store.write({
            'granted_scopes': json.dumps(['read_products', WRITE_SCOPE]),
        })
        result = self.Check._check_fulfillment_write_scope(self.store)
        self.assertEqual(result['result'], self.Check.RESULT_PASS)

    # ------------------------------------------------------------------
    # API-version compatibility gate (Q7)
    # ------------------------------------------------------------------

    def test_api_version_fails_when_outside_accepted_set(self):
        # TD-008 made a divergent `api_version` unreachable through the
        # ORM: `_check_api_version_is_the_connector_constant` refuses it on
        # create, write, `sudo()`, RPC and import alike. The readiness
        # check's behaviour on such a row still matters -- a database
        # upgraded from before that constraint can contain one -- so the
        # row is planted in SQL, the way `TestSec3HistoricRows` plants a
        # company-less store. Nothing about what this test asserts has
        # changed; only how the state it asserts on is reached.
        self.env.cr.execute(
            'UPDATE shopify_connector_store SET api_version = %s '
            'WHERE id = %s', ('2025-01', self.store.id),
        )
        self.store.invalidate_recordset()
        result = self.Check._check_fulfillment_api_version(self.store)
        self.assertEqual(result['tier'], self.Check.ESSENTIAL)
        self.assertEqual(result['result'], self.Check.RESULT_FAIL)

    def test_api_version_passes_for_accepted_version(self):
        self.store.write({'api_version': '2026-07'})
        result = self.Check._check_fulfillment_api_version(self.store)
        self.assertEqual(result['result'], self.Check.RESULT_PASS)

    # ------------------------------------------------------------------
    # Staff-permission axis (Q8): warning-tier, never proven from scopes
    # ------------------------------------------------------------------

    def test_staff_permission_is_warning_not_proven_when_enabled(self):
        # Even with the write scope granted, the staff permission is never
        # inferred from API scopes.
        self.store.write({
            'granted_scopes': json.dumps([WRITE_SCOPE]),
        })
        result = self.Check._check_fulfillment_staff_permission(self.store)
        self.assertEqual(result['tier'], self.Check.WARNING)
        self.assertEqual(result['result'], self.Check.RESULT_NOT_PROVEN)

    # ------------------------------------------------------------------
    # Core required-scopes swap + fulfillment module constants
    # ------------------------------------------------------------------

    def test_core_required_scopes_swap(self):
        required = self.Check.REQUIRED_MVP_SCOPES
        self.assertIn('read_merchant_managed_fulfillment_orders', required)
        self.assertNotIn('read_fulfillments', required)

    def test_fulfillment_module_constants(self):
        self.assertEqual(WRITE_SCOPE, 'write_merchant_managed_fulfillment_orders')
        self.assertIn('2026-07', FULFILLMENT_ACCEPTED_API_VERSIONS)
        self.assertNotIn('2025-01', FULFILLMENT_ACCEPTED_API_VERSIONS)
