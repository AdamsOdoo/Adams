import logging

from ..shopify_api.queries.inventory import INVENTORY_SET_QUANTITIES

_logger = logging.getLogger(__name__)


class InventorySync:
    """Exports Odoo stock levels to Shopify."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def export_inventory(self, backend):
        """Push current stock levels for all variant bindings."""
        location_id = backend.shopify_location_id
        if not location_id:
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

        success = errors = skipped = 0
        error_details = []
        qty_field = backend.inventory_quantity_field or 'free_qty'

        # Batch inventory updates (max 100 per API call)
        batch = []
        for vb in variant_bindings:
            product = vb.odoo_id
            warehouse = backend.warehouse_id

            if qty_field == 'free_qty':
                qty = product.with_context(warehouse=warehouse.id).free_qty
            else:
                qty = product.with_context(warehouse=warehouse.id).qty_available

            qty = int(qty)

            # Check if inventory binding exists; create if needed
            inv_binding = self.env['shopify.inventory.binding'].search([
                ('backend_id', '=', backend.id),
                ('variant_binding_id', '=', vb.id),
            ], limit=1)

            if inv_binding and inv_binding.last_pushed_qty == qty:
                skipped += 1
                continue

            batch.append({
                'variant_binding': vb,
                'inv_binding': inv_binding,
                'quantity': qty,
                'inventory_item_id': vb.shopify_inventory_item_id,
            })

            if len(batch) >= 100:
                s, e, details = self._push_batch(batch, location_id)
                success += s
                errors += e
                error_details.extend(details)
                batch = []

        if batch:
            s, e, details = self._push_batch(batch, location_id)
            success += s
            errors += e
            error_details.extend(details)

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped

    def _push_batch(self, batch, location_id):
        """Push a batch of inventory quantities to Shopify."""
        success = 0
        errors = 0
        error_details = []

        quantities = []
        for item in batch:
            quantities.append({
                'inventoryItemId': item['inventory_item_id'],
                'locationId': location_id,
                'quantity': item['quantity'],
            })

        try:
            self.client.execute_mutation(
                INVENTORY_SET_QUANTITIES,
                variables={
                    'input': {
                        'reason': 'correction',
                        'name': 'Odoo inventory sync',
                        'ignoreCompareQuantity': True,
                        'quantities': quantities,
                    },
                },
                result_key='inventorySetQuantities',
                estimated_cost=10,
            )

            # Update bindings
            for item in batch:
                inv_binding = item['inv_binding']
                if inv_binding:
                    inv_binding.write({'last_pushed_qty': item['quantity']})
                else:
                    self.env['shopify.inventory.binding'].create({
                        'backend_id': self.env.context.get('active_backend_id', batch[0]['variant_binding'].backend_id.id),
                        'variant_binding_id': item['variant_binding'].id,
                        'shopify_inventory_item_id': item['inventory_item_id'],
                        'shopify_location_id': location_id,
                        'last_pushed_qty': item['quantity'],
                        'shopify_id': f"{item['inventory_item_id']}:{location_id}",
                        'sync_status': 'synced',
                        'last_sync_date': self.env.cr.now(),
                    })
            success = len(batch)

        except Exception as e:
            _logger.warning("Inventory batch push failed: %s", e)
            errors = len(batch)
            error_details.append(str(e))

        return success, errors, error_details
