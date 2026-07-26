"""U2 display-and-delegate wizards for the inventory operator surfaces.

Why these exist. Two sanctioned Wave 3 actions take a REQUIRED argument:
``action_set_push_enabled(enabled)`` and
``action_recheck_inventory_pair(reason)``. An Odoo ``type="object"`` button
calls a method with no arguments, so neither can be wired to a button
directly. The alternative -- teaching the server methods to read their
argument out of the context -- would be a `models/**` change that moves an
input from an explicit parameter into ambient state, which is exactly the
kind of quiet coupling a UI phase must not introduce.

So each wizard does three things and nothing else: show the operator what
they are about to do, collect the one argument the server method requires,
and delegate. **No business logic lives here.** No wizard writes a binding
field, decides a quantity, or interprets a state -- the server method it
calls owns all of that, including its own access checks, and a caller who is
not permitted still gets an AccessError with zero side effects.

This follows the precedent U1 set with the fulfillment review-release wizard.
"""

from odoo import fields, models
from odoo.exceptions import UserError


class ShopifyConnectorLocationPushToggleWizard(models.TransientModel):
    _name = 'shopify.connector.location.push.toggle.wizard'
    _description = 'Shopify Connector Location Push Toggle'

    mapping_id = fields.Many2one(
        comodel_name='shopify.connector.location.mapping',
        required=True,
        readonly=True,
    )
    # Non-stored related reads: the wizard shows current truth rather than a
    # copy of it, so it can never display a stale value if the mapping
    # changed between opening the dialog and confirming.
    location_name = fields.Char(
        related='mapping_id.shopify_location_name_snapshot',
        readonly=True,
    )
    currently_enabled = fields.Boolean(
        related='mapping_id.push_enabled',
        readonly=True,
    )
    odoo_location_id = fields.Many2one(
        related='mapping_id.odoo_location_id',
        readonly=True,
    )
    target_enabled = fields.Boolean(
        string='Enable Push',
        help='The state this mapping will be set to.',
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        mapping_id = result.get('mapping_id') or self.env.context.get(
            'active_id'
        )
        if mapping_id and self.env.context.get(
            'active_model'
        ) == 'shopify.connector.location.mapping':
            result['mapping_id'] = mapping_id
        if result.get('mapping_id'):
            mapping = self.env[
                'shopify.connector.location.mapping'
            ].browse(result['mapping_id'])
            # Default to the opposite of the current state: the operator
            # opened this dialog to change something.
            result['target_enabled'] = not mapping.push_enabled
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.mapping_id:
            raise UserError('Select a location mapping first.')
        return self.mapping_id.action_set_push_enabled(self.target_enabled)


class ShopifyConnectorInventoryRecheckWizard(models.TransientModel):
    _name = 'shopify.connector.inventory.recheck.wizard'
    _description = 'Shopify Connector Inventory Pair Re-check'

    binding_id = fields.Many2one(
        comodel_name='shopify.connector.inventory.level.binding',
        required=True,
        readonly=True,
    )
    variant_binding_id = fields.Many2one(
        related='binding_id.product_variant_binding_id',
        readonly=True,
    )
    location_mapping_id = fields.Many2one(
        related='binding_id.location_mapping_id',
        readonly=True,
    )
    pending_target_available = fields.Float(
        related='binding_id.pending_target_available',
        readonly=True,
    )
    last_known_shopify_available = fields.Float(
        related='binding_id.last_known_shopify_available',
        readonly=True,
    )
    reason = fields.Char(
        required=True,
        help=(
            'Why this pair is being re-checked. Recorded on the resulting '
            'verification job so the decision is auditable later.'
        ),
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get(
            'active_model'
        ) == 'shopify.connector.inventory.level.binding':
            active_id = self.env.context.get('active_id')
            if active_id:
                result['binding_id'] = active_id
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.binding_id:
            raise UserError('Select an inventory level first.')
        reason = (self.reason or '').strip()
        if not reason:
            raise UserError('Describe why this pair is being re-checked.')
        return self.binding_id.action_recheck_inventory_pair(reason)
