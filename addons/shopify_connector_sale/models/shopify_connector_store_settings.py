from odoo import fields, models


class ShopifyConnectorStoreSettingsCustomerExtension(models.Model):
    """Adds the inert fallback-partner configuration field (D5, Posture A).

    Task 011 defines this field as supporting substrate only -- zero
    order-resolution behaviour, zero consumption within Task 011's own
    import/matching flow (see shopify_connector_customer_importer.py,
    which never reads this field), and zero coupling to order import.
    When and how an order routes to this partner, and the order-level
    audit marker that decision requires, are entirely Task 012's own
    future, separately-authorized scope. No default, no auto-creation of
    any partner record, no constraint requiring it, no compute/onchange,
    ordinary write path -- contributed via the core settings extension
    seam, no shopify_connector_core file edit.
    """

    _inherit = 'shopify.connector.store.settings'

    customer_fallback_partner_id = fields.Many2one(
        comodel_name='res.partner',
        ondelete='restrict',
    )
