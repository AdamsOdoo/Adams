"""Batch 2 checkpoint 1 -- the order section of canonical Store Settings.

The sale module contributes the largest block of previously unreachable
configuration, including `order_scheduled_sync_enabled`, which had no
production writer anywhere before this surface existed.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    CANONICAL_EDITABLE,
    CANONICAL_READONLY,
    SETTINGS_MODEL,
    assert_module_classification,
    canonical_form_field_nodes,
)

MODULE = 'shopify_connector_sale'

SALE_CLASSIFICATION = {
    'order_scheduled_sync_enabled': (CANONICAL_EDITABLE, ''),
    'order_confirmation_policy': (CANONICAL_EDITABLE, ''),
    'manual_gateway_policy': (CANONICAL_EDITABLE, ''),
    'approved_manual_gateways': (CANONICAL_EDITABLE, ''),
    'order_import_window': (CANONICAL_EDITABLE, ''),
    'pending_wait_expiry': (CANONICAL_EDITABLE, ''),
    'order_import_include_test': (CANONICAL_EDITABLE, ''),
    'customer_fallback_partner_id': (CANONICAL_EDITABLE, ''),
    'order_pricelist_id': (CANONICAL_EDITABLE, ''),
    'order_sales_team_id': (CANONICAL_EDITABLE, ''),
    'order_payment_term_id': (CANONICAL_EDITABLE, ''),
    'order_company_id': (
        CANONICAL_READONLY,
        'A store belongs to exactly one company and its orders are created '
        'there; re-homing a store is not a settings edit (SEC-3).',
    ),
    'sale_order_last_import_checkpoint_at': (
        CANONICAL_READONLY,
        'Discovery watermark written by the order scan; an observation, not '
        'a decision.',
    ),
}


@tagged('post_install', '-at_install')
class TestCanonicalStoreSettingsSale(TransactionCase):

    def test_every_sale_settings_field_is_classified(self):
        assert_module_classification(self, MODULE, SALE_CLASSIFICATION)

    def test_the_order_section_reaches_the_canonical_form(self):
        nodes = canonical_form_field_nodes(self.env)
        for name in SALE_CLASSIFICATION:
            self.assertIn(name, nodes)

    def test_the_fallback_customer_is_a_real_setting_not_a_false_capability(self):
        """§6.4 demands proof before this is presented as supported.

        The proof is a production call site, not a comment: the order
        importer's customer resolution returns this partner with resolution
        `fallback`. Asserting it here means the day that call site is removed,
        this fails and the form stops claiming the capability.
        """
        importer = self.env['shopify.connector.order.importer']
        source = importer._resolve_customer.__doc__ or ''
        self.assertTrue(hasattr(importer, '_resolve_customer'), source)

        import inspect
        body = inspect.getsource(type(importer)._resolve_customer)
        self.assertIn(
            'customer_fallback_partner_id', body,
            'The canonical form presents the fallback customer as supported; '
            'the production order importer must actually consume it.',
        )
        self.assertIn("'fallback'", body)

    def test_scheduled_order_sync_is_reachable_and_drives_the_real_cron(self):
        """§7.1's prerequisite, proved at the settings layer.

        The canonical form writes `order_scheduled_sync_enabled` through the
        ordinary model path, and the existing cron selects stores on exactly
        that field plus `sale_domain_enabled`. This asserts the field the form
        writes is the field the cron reads -- the two had never been connected
        by anything a merchant could reach.
        """
        nodes = canonical_form_field_nodes(self.env)
        self.assertIn('order_scheduled_sync_enabled', nodes)
        self.assertFalse(
            self.env[SETTINGS_MODEL]._fields[
                'order_scheduled_sync_enabled'
            ].readonly,
        )
        import inspect
        cron_body = inspect.getsource(
            type(self.env['shopify.connector.store'])._cron_enqueue_order_scans
        )
        self.assertIn('order_scheduled_sync_enabled', cron_body)
        self.assertIn('sale_domain_enabled', cron_body)
