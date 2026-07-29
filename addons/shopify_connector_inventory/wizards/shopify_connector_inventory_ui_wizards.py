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

from odoo import api, fields, models
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


# ======================================================================
# Wave 5: the three governed Location Mapping workspace actions.
#
# The workspace told operators that "a mapping is created when a Shopify
# location is paired with an Odoo location" and then offered no way to
# create one -- both its list and its form carry `create="false"`, correctly,
# because the binding mixin refuses a generic create of protected identity
# fields. The route that was missing is a wizard that collects the two
# identities and delegates to the sanctioned server service, which is what
# these three do.
#
# THE SAME RULE AS THE TWO WIZARDS ABOVE: no business logic lives here. Each
# wizard shows what is about to happen, collects the arguments the server
# method requires, and calls it. Every authorization, company check,
# cache validation and safety refusal is the service's, re-run as the
# calling user, so a caller who is not permitted gets an AccessError with
# zero side effects whatever this dialog rendered.
# ======================================================================


class ShopifyConnectorLocationRefreshWizard(models.TransientModel):
    """Ask Shopify for a store's location list, through the job queue."""

    _name = 'shopify.connector.location.refresh.wizard'
    _description = 'Shopify Connector Location Refresh'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        domain="[('state', 'in', ('setup_incomplete', 'connected'))]",
        help='The Shopify store whose location list will be refreshed.',
    )
    # Non-stored computed reads, so the dialog states the CURRENT state of a
    # refresh rather than a copy of it taken when it opened.
    refresh_state = fields.Char(
        compute='_compute_refresh', string='Current refresh',
    )
    refresh_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        compute='_compute_refresh', string='Refresh job',
    )

    @api.depends('store_id')
    def _compute_refresh(self):
        Service = self.env['shopify.connector.inventory.service']
        for wizard in self:
            if not wizard.store_id:
                wizard.refresh_state = ''
                wizard.refresh_job_id = False
                continue
            state = Service.location_refresh_state(wizard.store_id)
            wizard.refresh_state = state['state']
            wizard.refresh_job_id = state['job_id'] or False

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('active_model') == (
            'shopify.connector.location.mapping'
        ):
            active_id = self.env.context.get('active_id')
            if active_id:
                mapping = self.env[
                    'shopify.connector.location.mapping'
                ].browse(active_id)
                result['store_id'] = mapping.store_id.id
        return result

    def action_confirm(self):
        """Admit the refresh and report the job it actually admitted.

        Never reports success for work that was not admitted: the return is
        the real job record, so a coalesced duplicate shows the job already
        in flight rather than a second one nobody created.
        """
        self.ensure_one()
        if not self.store_id:
            raise UserError('Select a Shopify store first.')
        job = self.env[
            'shopify.connector.inventory.service'
        ].action_refresh_shopify_locations(self.store_id.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': (
                    'Refreshing the Shopify location list. This runs in the '
                    'background; job #%d is %s.' % (job.id, job.state)
                ),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class ShopifyConnectorLocationMapWizard(models.TransientModel):
    """Pair one cached Shopify location with one Odoo internal location."""

    _name = 'shopify.connector.location.map.wizard'
    _description = 'Shopify Connector Location Mapping Creation'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
    )
    # The Shopify side is CHOSEN FROM THE CACHE, never typed. That is the
    # whole point of this control existing: a free-text GID field would be
    # the arbitrary-identity hole the creation service now refuses anyway,
    # rendered as if it were a supported way to work.
    shopify_location_id = fields.Many2one(
        comodel_name='shopify.connector.location',
        required=True,
        string='Shopify location',
        domain="[('store_id', '=', store_id),"
               " ('shopify_location_active', '=', True)]",
    )
    odoo_location_id = fields.Many2one(
        comodel_name='stock.location',
        required=True,
        string='Odoo location',
        domain="[('usage', '=', 'internal')]",
    )
    push_enabled = fields.Boolean(
        string='Push stock for this location',
        default=True,
        help='Whether Odoo stock changes for this location are pushed to '
             'Shopify. The first push still waits for its own confirmation.',
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        context_store = self.env.context.get('default_store_id')
        if context_store:
            result['store_id'] = context_store
        elif self.env.context.get('active_model') == (
            'shopify.connector.location.mapping'
        ):
            active_id = self.env.context.get('active_id')
            if active_id:
                result['store_id'] = self.env[
                    'shopify.connector.location.mapping'
                ].browse(active_id).store_id.id
        if not result.get('store_id'):
            # Exactly one store the caller can see is not a guess, it is the
            # only answer. More than one is a choice, and the field stays
            # empty so the operator makes it.
            stores = self.env['shopify.connector.store'].search([], limit=2)
            if len(stores) == 1:
                result['store_id'] = stores.id
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.shopify_location_id or not self.odoo_location_id:
            raise UserError(
                'Choose both a Shopify location and an Odoo location.'
            )
        mapping = self.env[
            'shopify.connector.inventory.service'
        ].create_or_update_location_mapping(
            self.store_id,
            self.odoo_location_id,
            self.shopify_location_id.shopify_location_gid,
            push_enabled=self.push_enabled,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.connector.location.mapping',
            'res_id': mapping.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ShopifyConnectorLocationRemapWizard(models.TransientModel):
    """Change which Odoo location an already-bound Shopify location means."""

    _name = 'shopify.connector.location.remap.wizard'
    _description = 'Shopify Connector Location Remap'

    mapping_id = fields.Many2one(
        comodel_name='shopify.connector.location.mapping',
        required=True,
        readonly=True,
    )
    location_name = fields.Char(
        related='mapping_id.shopify_location_name_snapshot',
        readonly=True,
        string='Shopify location',
    )
    current_location_id = fields.Many2one(
        related='mapping_id.odoo_location_id',
        readonly=True,
        string='Currently mapped to',
    )
    new_location_id = fields.Many2one(
        comodel_name='stock.location',
        required=True,
        string='New Odoo location',
        domain="[('usage', '=', 'internal')]",
    )
    reason = fields.Char(
        required=True,
        help='Why this Shopify location is being pointed at a different '
             'Odoo location. Recorded on the connector audit trail.',
    )
    confirmed = fields.Boolean(
        string='I understand what this changes',
        help='Remapping changes which Odoo location\'s stock this Shopify '
             'location reflects.',
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('active_model') == (
            'shopify.connector.location.mapping'
        ):
            active_id = self.env.context.get('active_id')
            if active_id:
                result['mapping_id'] = active_id
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.mapping_id:
            raise UserError('Select a location mapping first.')
        self.env[
            'shopify.connector.inventory.service'
        ].remap_location_mapping(
            self.mapping_id,
            self.new_location_id,
            self.reason,
            confirmed=self.confirmed,
        )
        return {'type': 'ir.actions.act_window_close'}
