from odoo import api, models


class ShopifyConnectorProductVariantBindingInventory(models.Model):
    """Inventory-owned reachability hooks for product-variant identity.

    Product import and product-create finalisation own the durable
    ``shopify_inventory_item_gid`` on the variant binding.  Inventory does not
    duplicate that identity or manufacture one; it only reconciles the
    variant binding against any already-mapped Shopify locations after the
    product binding reaches a durable create/write state.
    """

    _inherit = 'shopify.connector.product.variant.binding'

    @api.model_create_multi
    def create(self, vals_list):
        bindings = super().create(vals_list)
        if bindings:
            self.env[
                'shopify.connector.inventory.service'
            ]._bootstrap_inventory_level_bindings(
                variant_bindings=bindings,
            )
        return bindings

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & {
            'store_id', 'product_variant_id',
            'shopify_inventory_item_gid', 'status',
        }:
            self.env[
                'shopify.connector.inventory.service'
            ]._bootstrap_inventory_level_bindings(
                variant_bindings=self,
            )
        return result
