# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for inventory mutations."""
import logging

from .base_handler import build_mutation_response

_logger = logging.getLogger(__name__)


def handle_inventory_set_quantities(env, config, variables):
    """INVENTORY_SET_QUANTITIES mutation — batch set inventory levels."""
    inp = variables.get('input', {})
    reason = inp.get('reason', 'correction')
    quantities = inp.get('quantities', [])

    for q in quantities:
        inventory_item_id = q.get('inventoryItemId', '')
        location_id = q.get('locationId', '')
        qty = q.get('quantity', 0)

        # Find variant by inventory item GID
        variant = env['sim.shopify.variant'].search([
            ('inventory_item_gid', '=', inventory_item_id),
            ('product_id.config_id', '=', config.id),
        ], limit=1)

        location = env['sim.shopify.location'].search([
            ('shopify_gid', '=', location_id),
            ('config_id', '=', config.id),
        ], limit=1)

        if variant and location:
            # Upsert inventory level
            level = env['sim.shopify.inventory.level'].search([
                ('variant_id', '=', variant.id),
                ('location_id', '=', location.id),
            ], limit=1)
            if level:
                level.write({'available': qty})
            else:
                env['sim.shopify.inventory.level'].create({
                    'config_id': config.id,
                    'variant_id': variant.id,
                    'location_id': location.id,
                    'available': qty,
                })

            # Also update variant quantity
            variant.write({'inventory_quantity': qty})

    return build_mutation_response('inventorySetQuantities', {
        'inventoryAdjustmentGroup': {
            'reason': reason,
        },
    })


def handle_inventory_adjust_quantities(env, config, variables):
    """INVENTORY_ADJUST_QUANTITIES mutation — adjust inventory by delta."""
    inp = variables.get('input', {})
    reason = inp.get('reason', 'correction')
    changes = inp.get('changes', [])

    result_changes = []
    for change in changes:
        inventory_item_id = change.get('inventoryItemId', '')
        location_id = change.get('locationId', '')
        delta = change.get('delta', 0)

        variant = env['sim.shopify.variant'].search([
            ('inventory_item_gid', '=', inventory_item_id),
            ('product_id.config_id', '=', config.id),
        ], limit=1)

        location = env['sim.shopify.location'].search([
            ('shopify_gid', '=', location_id),
            ('config_id', '=', config.id),
        ], limit=1)

        if variant and location:
            level = env['sim.shopify.inventory.level'].search([
                ('variant_id', '=', variant.id),
                ('location_id', '=', location.id),
            ], limit=1)
            old_qty = level.available if level else 0
            new_qty = old_qty + delta

            if level:
                level.write({'available': new_qty})
            else:
                env['sim.shopify.inventory.level'].create({
                    'config_id': config.id,
                    'variant_id': variant.id,
                    'location_id': location.id,
                    'available': new_qty,
                })

            variant.write({'inventory_quantity': new_qty})
            result_changes.append({
                'name': variant.sku or variant.shopify_gid,
                'delta': delta,
            })

    return build_mutation_response('inventoryAdjustQuantities', {
        'inventoryAdjustmentGroup': {
            'reason': reason,
            'changes': result_changes,
        },
    })
