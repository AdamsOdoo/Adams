"""Batch 2 checkpoint 1 -- the inventory section of canonical Store Settings."""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    CANONICAL_EDITABLE,
    CANONICAL_READONLY,
    SETTINGS_MODEL,
    assert_module_classification,
    canonical_form_field_nodes,
)

MODULE = 'shopify_connector_inventory'

INVENTORY_CLASSIFICATION = {
    'inventory_scheduled_sync_enabled': (CANONICAL_EDITABLE, ''),
    'inventory_last_push_scan_at': (
        CANONICAL_READONLY,
        'Scan watermark written by the inventory service; an observation, '
        'not a decision.',
    ),
}


@tagged('post_install', '-at_install')
class TestCanonicalStoreSettingsInventory(TransactionCase):

    def test_every_inventory_settings_field_is_classified(self):
        assert_module_classification(self, MODULE, INVENTORY_CLASSIFICATION)

    def test_the_inventory_section_reaches_the_canonical_form(self):
        nodes = canonical_form_field_nodes(self.env)
        for name in INVENTORY_CLASSIFICATION:
            self.assertIn(name, nodes)

    def test_scheduled_stock_sync_is_the_field_the_service_selects_on(self):
        """Rendered as a decision because it genuinely is one.

        The inventory service's scheduled scan searches settings on this exact
        field. If that ever stops being true the control becomes decoration,
        and this fails rather than leaving it on screen.
        """
        import inspect
        service = self.env['shopify.connector.inventory.service']
        # The concrete method, not `type(service)`: Odoo composes the registry
        # class at runtime, so it has no source file to read.
        source = inspect.getsource(type(service).run_inventory_push_scan)
        self.assertIn('inventory_scheduled_sync_enabled', source)
        self.assertIn('inventory_domain_enabled', source)
        self.assertFalse(
            self.env[SETTINGS_MODEL]._fields[
                'inventory_scheduled_sync_enabled'
            ].readonly,
        )

    def test_first_push_and_location_routes_are_not_duplicated_here(self):
        """This surface is per-store configuration, not a record workspace.

        The first-push guard and location mapping are decisions about specific
        records and already have their own governed surfaces; pulling them
        onto the settings form would be a second route to a guarded action.
        """
        nodes = canonical_form_field_nodes(self.env)
        for leaked in (
            'first_push_state', 'odoo_location_id', 'shopify_location_id',
        ):
            self.assertNotIn(leaked, nodes)
