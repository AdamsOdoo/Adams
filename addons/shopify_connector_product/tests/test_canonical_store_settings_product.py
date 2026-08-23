"""Batch 2 checkpoint 1 -- the product section of canonical Store Settings.

§6.6 requires every module contributing a settings field to classify all of
them. This is the product module's answer.

UPDATED BY CHECKPOINT 3. Checkpoint 1 asserted that no scheduled-product-import
setting existed, because nothing in production enumerated a catalog and a
switch with no producer behind it is a control that silently does nothing.
Checkpoint 3 built the producer, so the three fields it configures are now
classified and rendered, and the guard is replaced by its opposite: the
schedule must be wired to the cron that reads it.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    CANONICAL_EDITABLE,
    CANONICAL_READONLY,
    SETTINGS_MODEL,
    assert_module_classification,
    canonical_form_field_nodes,
)

MODULE = 'shopify_connector_product'

PRODUCT_CLASSIFICATION = {
    'product_import_media_enabled': (CANONICAL_EDITABLE, ''),
    'product_import_refresh_mode': (CANONICAL_EDITABLE, ''),
    'product_import_attribute_conflict_mode': (CANONICAL_EDITABLE, ''),
    'product_scheduled_sync_enabled': (CANONICAL_EDITABLE, ''),
    'product_last_import_checkpoint_at': (
        CANONICAL_READONLY,
        'Enumeration watermark written by the product scan service; an '
        'observation, not a decision.',
    ),
    'product_last_import_success_at': (
        CANONICAL_READONLY,
        'When a product scan last completed; written by the scan service.',
    ),
    'product_scan_window_start_at': (
        CANONICAL_READONLY,
        'Durable lower boundary of the active resumable scan window.',
    ),
    'product_scan_window_end_at': (
        CANONICAL_READONLY,
        'Durable upper boundary of the active resumable scan window.',
    ),
    'product_scan_cursor': (
        CANONICAL_READONLY,
        'Opaque Shopify cursor for the active resumable scan window.',
    ),
    'product_scan_generation': (
        CANONICAL_READONLY,
        'Connection generation fencing the active scan checkpoint.',
    ),
    'product_scan_page_count': (
        CANONICAL_READONLY,
        'Bounded progress evidence for the active scan window.',
    ),
    'product_scan_latest_at': (
        CANONICAL_READONLY,
        'Latest observed record timestamp inside the active scan window.',
    ),
}


@tagged('post_install', '-at_install')
class TestCanonicalStoreSettingsProduct(TransactionCase):

    def test_every_product_settings_field_is_classified(self):
        assert_module_classification(self, MODULE, PRODUCT_CLASSIFICATION)

    def test_the_product_section_reaches_the_canonical_form(self):
        nodes = canonical_form_field_nodes(self.env)
        for name in PRODUCT_CLASSIFICATION:
            self.assertIn(
                name, nodes,
                'The product-import section must be contributed to the '
                'canonical Store Settings form by inheritance.',
            )

    def test_the_scheduled_setting_is_the_field_the_cron_selects_on(self):
        """The inverse of checkpoint 1's guard, now that the producer exists.

        A rendered schedule switch is only honest if something reads it. This
        asserts the cron's own selection is over exactly this field plus the
        domain flag -- so if the producer is ever removed, the control stops
        being decoration by failing here rather than by quietly doing nothing.
        """
        import inspect
        store = self.env['shopify.connector.store']
        source = inspect.getsource(
            type(store)._cron_enqueue_product_scans
        )
        self.assertIn('product_scheduled_sync_enabled', source)
        self.assertIn('product_domain_enabled', source)
        self.assertFalse(
            self.env[SETTINGS_MODEL]._fields[
                'product_scheduled_sync_enabled'
            ].readonly,
        )

    def test_the_scheduled_cron_record_exists_and_calls_the_producer(self):
        cron = self.env.ref(
            'shopify_connector_product.'
            'ir_cron_shopify_connector_product_scan',
        )
        self.assertIn('_cron_enqueue_product_scans', cron.code)
        self.assertEqual(cron.model_id.model, 'shopify.connector.store')
