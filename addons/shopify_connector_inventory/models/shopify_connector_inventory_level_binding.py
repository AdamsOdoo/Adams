from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


FIRST_PUSH_STATE_SELECTION = [
    ('pending', 'Pending'),
    ('previewed', 'Previewed'),
    ('confirmed', 'Confirmed'),
]


class ShopifyConnectorInventoryLevelBinding(models.Model):
    """Per (product-variant, mapped-location) Shopify InventoryLevel binding.

    D-013-1(b). Identity: one store + one Shopify inventory item + one
    mapped Odoo location. `shopify_gid` (the InventoryLevel GID itself)
    may be empty until the pair's first activation/read -- overriding the
    binding mixin's default `required=True`, the one deliberate deviation
    from the mixin contract on this model (composite identity is
    otherwise non-overridable, see `_odoo_binding_field_name` below).

    Gate B correction (DEC-037 §1 item C5): this binding never stores a
    Shopify transport idempotency key or a request-params hash. Those
    live exclusively, request-level and attempt-owned, on
    `shopify.connector.mutation.attempt` (Stage 0, unchanged). Every
    field below is informational/display/coalescing only, refreshed
    from a reconciliation read or a `succeeded` attempt's evidence --
    never read as transport-replay or idempotency authority.
    """

    _name = 'shopify.connector.inventory.level.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Inventory Level Binding'

    # Deliberate override of the mixin's `required=True` -- the
    # InventoryLevel GID is not known until the pair's first activation
    # or first successful reconciliation read.
    shopify_gid = fields.Char(required=False, readonly=True, index=True)

    product_variant_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.variant.binding',
        required=True,
        index=True,
        ondelete='restrict',
    )
    location_mapping_id = fields.Many2one(
        comodel_name='shopify.connector.location.mapping',
        required=True,
        index=True,
        ondelete='restrict',
    )
    # The 1:1 direction that remains non-null: the Shopify InventoryItem
    # GID for this variant's binding (variant.inventoryItem).
    shopify_inventory_item_gid = fields.Char(
        required=True, index=True, readonly=True,
    )

    # Informational/display/coalescing fields only (Gate B, DEC-037 §1
    # item C5/§10) -- never transport-replay or idempotency authority.
    last_pushed_available = fields.Float(readonly=True)
    last_pushed_at = fields.Datetime(readonly=True)
    last_known_shopify_available = fields.Float(readonly=True)
    # One coalesced pending-update target per pair, last-value-wins
    # (DEC-037 §10). Refreshed by every Odoo-side stock change; consumed
    # (and cleared back to the freshly-derived value) by the next
    # `inventory_push_sync` dispatch.
    pending_target_available = fields.Float(readonly=True)

    # MBQ-38 first-push confirmation record (D-013-4).
    first_push_state = fields.Selection(
        selection=FIRST_PUSH_STATE_SELECTION,
        required=True,
        default='pending',
        readonly=True,
    )
    first_push_preview_qty = fields.Float(readonly=True)
    first_push_confirmed_at = fields.Datetime(readonly=True)
    first_push_confirmed_by_uid = fields.Many2one(
        comodel_name='res.users', readonly=True,
    )

    _store_inventory_item_location_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_inventory_item_gid, location_mapping_id)',
        'An inventory-level binding for this Shopify inventory item and '
        'mapped location already exists for this store.',
    )
    _store_variant_location_uniq = models.Constraint(
        'UNIQUE(store_id, product_variant_binding_id, location_mapping_id)',
        'An inventory-level binding for this product-variant binding and '
        'mapped location already exists for this store.',
    )

    def _odoo_binding_field_name(self):
        # Composite identity (variant x location) -- not a single
        # overridable Odoo-record Many2one. Non-overridable, mixin
        # default `False` (DEC-037 §7 SEC-1 override seam).
        return False

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'product_variant_binding_id',
            'location_mapping_id',
            'shopify_inventory_item_gid',
            'last_pushed_available',
            'last_pushed_at',
            'last_known_shopify_available',
            'pending_target_available',
            'first_push_state',
            'first_push_preview_qty',
            'first_push_confirmed_at',
            'first_push_confirmed_by_uid',
        ))

    @api.constrains('store_id', 'product_variant_binding_id')
    def _check_variant_binding_store_consistency(self):
        for binding in self:
            if (
                binding.product_variant_binding_id
                and binding.product_variant_binding_id.store_id
                != binding.store_id
            ):
                raise UserError(
                    "The product-variant binding must belong to the same "
                    "store as this inventory-level binding."
                )

    @api.constrains('store_id', 'location_mapping_id')
    def _check_location_mapping_store_consistency(self):
        for binding in self:
            if (
                binding.location_mapping_id
                and binding.location_mapping_id.store_id != binding.store_id
            ):
                raise UserError(
                    "The location mapping must belong to the same store as "
                    "this inventory-level binding."
                )

    @api.constrains('product_variant_binding_id', 'location_mapping_id')
    def _check_company_consistency(self):
        """SEC-1 composite-binding company rule (PR #182 comment
        5025803697 item 21): any non-empty company on the product
        variant or the mapped location must equal `env.company`, and
        when both are non-empty they must equal each other.
        Company-neutral product/location records remain valid. Runs on
        every create/write of this binding regardless of caller (the
        sanctioned service included) -- never bypassed by `sudo()`,
        since `@api.constrains` always evaluates on the base record
        visible to the current environment's company context.
        """
        for binding in self:
            product = binding.product_variant_binding_id.product_variant_id
            location = binding.location_mapping_id.odoo_location_id
            product_company = product.company_id if product else False
            location_company = location.company_id if location else False
            for label, company in (
                ('product variant', product_company),
                ('mapped location', location_company),
            ):
                if company and company != self.env.company:
                    raise UserError(
                        "The %s belongs to a different company than the "
                        "current company." % label
                    )
            if (
                product_company and location_company
                and product_company != location_company
            ):
                raise UserError(
                    "The product variant and the mapped location belong "
                    "to different companies."
                )

    def action_confirm_first_push(self):
        """Administrator-only explicit first-push confirmation.

        Records the confirming actor and timestamp and moves
        `first_push_state` from `previewed` to `confirmed`. A row with no
        recorded preview cannot be confirmed -- the preview
        (`inventory_first_push_preview` job, `job_source=
        export_preview_dry_run`) must run first. This is the sole gate
        `inventory_push_sync` checks before it may enqueue either
        mutation job type for this pair (D-013-4).
        """
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                "Only a Shopify Connector Administrator may "
                "confirm a first push."
            )
        if self.first_push_state != 'previewed':
            raise UserError(
                "A first push can only be confirmed after its preview has "
                "run."
            )
        self.sudo().write({
            'first_push_state': 'confirmed',
            'first_push_confirmed_at': fields.Datetime.now(),
            'first_push_confirmed_by_uid': self.env.uid,
        })
        return True

    def action_recheck_inventory_pair(self, reason):
        """The sole public release path for a blocked inventory pair.

        DEC-037 §5.5/§1C item 7: this public RPC/action is owned
        exclusively by this binding model. It may delegate to a private
        helper on `shopify.connector.inventory.service`, but the service
        itself must never expose or own this public method. See that
        private helper for the complete eligibility/atomicity contract.
        """
        self.ensure_one()
        return self.env[
            'shopify.connector.inventory.service'
        ]._recheck_inventory_pair(self, reason)

    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with the connector parent.
    #
    # Company equality is NOT enough here. One Odoo company may own several
    # Shopify stores, so a row in store A pointing at a parent in store B is
    # company-consistent and store-inconsistent -- two different shops' records
    # mixed together, which no company check can see. `init()` additionally
    # quarantines rows written before this constraint existed; it never guesses
    # which half is wrong and never re-homes anything.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (('product_variant_binding_id', 'store'), ('location_mapping_id', 'store'),)

    @api.constrains('store_id', 'product_variant_binding_id', 'location_mapping_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
