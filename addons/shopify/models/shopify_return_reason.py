from odoo import models, fields, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import RETURN_REASON_DEFINITIONS
from odoo.addons.shopify.models.misc import extract_numeric_id

RETURN_REASON_HANDLES = [
    "too-short",
    "too-long",
    "color",
    "flex",
    "changed-my-mind",
    "item-not-as-described",
    "received-the-wrong-item",
    "damaged-or-defective",
    "unknown",
    "other-reason"
]

class ShopifyReturnReason(models.Model):
    _name = "shopify.return.reason.ts"
    _description = "Shopify Return Reason Definition"
    _rec_name = "name"

    name = fields.Char("Reason", required=True, help="Name of the return reason from Shopify.")
    handle = fields.Char("Handle", copy=False, index=True, help="Unique Shopify handle  (e.g. 'too-small') used to identify the return reason.")
    shopify_reason_definition_id = fields.Char("Shopify Reason Definition ID", copy=False, index=True, help="Numeric ReturnReasonDefinition id")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade', required=True)

    def import_return_reasons_from_shopify(self, mk_instance_id):
        """
        Fetch the return reason definitions configured in Shopify, create or update the corresponding records in Odoo, and remove any obsolete reasons
        that are no longer available in Shopify.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
        Returns:
            bool: Returns True.
        Raises:
            MarketplaceException: If Shopify returns an error while fetching the reasons.
        """
        self = self.sudo()
        mk_instance_id.connection_to_shopify()
        response = mk_instance_id.execute_graphql_query(RETURN_REASON_DEFINITIONS, {"handles": RETURN_REASON_HANDLES})
        errors = (response or {}).get('errors') or []
        if errors:
            messages = ", ".join(err.get('message', str(err)) for err in errors)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify return reasons: %s") % messages)
        nodes = ((response or {}).get('data') or {}).get('returnReasonDefinitions') or []
        synced_reasons = self
        for node in nodes:
            numeric = extract_numeric_id(node.get('id'))
            if not numeric:
                continue
            vals = {
                'name': node.get('name') or '',
                'handle': node.get('handle') or False,
                'mk_instance_id': mk_instance_id.id,
            }
            reason = self.search([
                ('shopify_reason_definition_id', '=', str(numeric)),
                ('mk_instance_id', '=', mk_instance_id.id),
            ], limit=1)
            if not reason:
                reason = self.create(dict(vals, shopify_reason_definition_id=str(numeric)))
            synced_reasons |= reason
        stale = self.search([('mk_instance_id', '=', mk_instance_id.id), ('handle', 'in', RETURN_REASON_HANDLES), ]) - synced_reasons
        if stale:
            stale.unlink()
        return True
