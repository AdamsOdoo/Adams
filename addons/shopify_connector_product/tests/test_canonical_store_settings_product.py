"""Batch 2 checkpoint 1 -- the product section of canonical Store Settings.

§6.6 requires every module contributing a settings field to classify all of
them. This is the product module's answer.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    CANONICAL_EDITABLE,
    assert_module_classification,
    canonical_form_field_nodes,
)

MODULE = 'shopify_connector_product'

PRODUCT_CLASSIFICATION = {
    'product_import_media_enabled': (CANONICAL_EDITABLE, ''),
    'product_import_refresh_mode': (CANONICAL_EDITABLE, ''),
    'product_import_attribute_conflict_mode': (CANONICAL_EDITABLE, ''),
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

    def test_no_scheduled_product_import_control_is_offered_yet(self):
        """§6.4's anti-false-capability rule, applied to this module.

        Nothing in production enqueues product enumeration at this head, so a
        scheduled-product-import switch would be a control that silently does
        nothing. This asserts the surface does not grow one before the
        producer it configures exists -- and it is written to FAIL the moment
        such a field is added without also being classified and wired.
        """
        settings_fields = self.env['shopify.connector.store.settings']._fields
        scheduled = {
            name for name in settings_fields
            if name.startswith('product_import_')
            and ('schedul' in name or 'cron' in name)
        }
        self.assertFalse(
            scheduled,
            'A scheduled product-import setting exists (%s) but the product '
            'scan producer does not. Either wire the producer and classify '
            'the field, or do not render the control.' % sorted(scheduled),
        )
