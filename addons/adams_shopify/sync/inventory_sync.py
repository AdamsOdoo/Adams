import logging

from odoo import fields

from ..shopify_api.queries.inventory import INVENTORY_SET_QUANTITIES

_logger = logging.getLogger(__name__)


class InventorySync:
    """Exports Odoo stock levels to Shopify.

    Supports multi-location: if shopify.location records with mapped
    warehouses exist, each location/warehouse pair is synced independently.
    Falls back to the legacy single-location mode using
    backend.shopify_location_id / backend.warehouse_id.
    """

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def export_inventory(self, backend):
        """Push current stock levels for all variant bindings."""
        location_mappings = self._get_location_mappings(backend)
        if not location_mappings:
            _logger.warning("No Shopify location configured for backend %s", backend.id)
            return 0, 0, 0

        log = self.env['shopify.sync.log'].create({
            'backend_id': backend.id,
            'entity': 'inventory',
            'operation': 'export',
        })

        variant_bindings = self.env['shopify.variant.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_inventory_item_id', '!=', False),
            ('sync_status', 'in', ['synced', 'pending']),
        ])

        total_success = total_errors = total_skipped = 0
        all_error_details = []
        qty_field = backend.inventory_quantity_field or 'free_qty'

        for shopify_loc_id, warehouse in location_mappings:
            success, errors, skipped, error_details = self._sync_location(
                backend, variant_bindings, shopify_loc_id, warehouse, qty_field,
            )
            total_success += success
            total_errors += errors
            total_skipped += skipped
            all_error_details.extend(error_details)

        log._finalize(
            total_success, total_errors, total_skipped,
            '\n'.join(all_error_details) or None,
        )
        return total_success, total_errors, total_skipped

    def _get_location_mappings(self, backend):
        """Return list of (shopify_location_id, warehouse) tuples.

        Prefers multi-location records. Falls back to legacy single-location.
        """
        locations = self.env['shopify.location'].search([
            ('backend_id', '=', backend.id),
            ('is_active', '=', True),
            ('warehouse_id', '!=', False),
        ])
        if locations:
            return [
                (loc.shopify_location_id, loc.warehouse_id)
                for loc in locations
            ]
        # Fallback: legacy single-location
        if backend.shopify_location_id and backend.warehouse_id:
            return [(backend.shopify_location_id, backend.warehouse_id)]
        return []

    def _sync_location(self, backend, variant_bindings, shopify_loc_id, warehouse, qty_field):
        """Sync inventory for a single Shopify location / Odoo warehouse pair."""
        success = errors = skipped = 0
        error_details = []
        batch = []
        batch_limit = min(backend.batch_size or 50, 100)  # Shopify max is 100

        # Pre-fetch all inventory bindings for this location in one query
        inv_bindings = self.env['shopify.inventory.binding'].search([
            ('backend_id', '=', backend.id),
            ('shopify_location_id', '=', shopify_loc_id),
        ])
        inv_binding_map = {vb.variant_binding_id.id: vb for vb in inv_bindings}

        # Pre-fetch quantities for all variants in a single context
        ctx_env = self.env['product.product'].with_context(warehouse=warehouse.id)

        for vb in variant_bindings:
            product = vb.odoo_id
            if qty_field == 'free_qty':
                qty = ctx_env.browse(product.id).free_qty
            else:
                qty = ctx_env.browse(product.id).qty_available
            qty = int(qty)

            inv_binding = inv_binding_map.get(vb.id)

            if inv_binding and inv_binding.last_pushed_qty == qty:
                skipped += 1
                continue

            batch.append({
                'variant_binding': vb,
                'inv_binding': inv_binding,
                'quantity': qty,
                'inventory_item_id': vb.shopify_inventory_item_id,
            })

            if len(batch) >= batch_limit:
                s, e, details = self._push_batch(batch, shopify_loc_id)
                success += s
                errors += e
                error_details.extend(details)
                batch = []

        if batch:
            s, e, details = self._push_batch(batch, shopify_loc_id)
            success += s
            errors += e
            error_details.extend(details)

        return success, errors, skipped, error_details

    def _push_batch(self, batch, location_id):
        """Push a batch of inventory quantities to Shopify.

        Uses inventorySetQuantities with compareQuantity (required as of
        Shopify 2026-01 — ignoreCompareQuantity was removed). compareQuantity
        is taken from last_pushed_qty which represents our last known
        Shopify state; if Shopify drifted (manual edit), the call will fail
        with compareQuantityStale and we'll retry on the next cron pass.
        """
        success = 0
        errors = 0
        error_details = []

        quantities = []
        for item in batch:
            compare_qty = 0
            if item['inv_binding']:
                compare_qty = int(item['inv_binding'].last_pushed_qty or 0)
            quantities.append({
                'inventoryItemId': item['inventory_item_id'],
                'locationId': location_id,
                'quantity': item['quantity'],
                'compareQuantity': compare_qty,
            })

        try:
            self.client.execute_mutation(
                INVENTORY_SET_QUANTITIES,
                variables={
                    'input': {
                        'reason': 'correction',
                        'name': 'available',
                        'quantities': quantities,
                    },
                },
                result_key='inventorySetQuantities',
                estimated_cost=10,
            )

            for item in batch:
                inv_binding = item['inv_binding']
                if inv_binding:
                    inv_binding.write({'last_pushed_qty': item['quantity']})
                else:
                    self.env['shopify.inventory.binding'].create({
                        'backend_id': self.backend.id,
                        'variant_binding_id': item['variant_binding'].id,
                        'shopify_inventory_item_id': item['inventory_item_id'],
                        'shopify_location_id': location_id,
                        'last_pushed_qty': item['quantity'],
                        'shopify_id': f"{item['inventory_item_id']}:{location_id}",
                        'sync_status': 'synced',
                        'last_sync_date': fields.Datetime.now(),
                    })
            success = len(batch)

        except Exception as e:
            _logger.warning("Inventory batch push failed: %s", e)
            errors = len(batch)
            error_details.append(str(e))

        return success, errors, error_details
