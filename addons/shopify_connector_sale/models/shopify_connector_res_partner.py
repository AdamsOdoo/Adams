from odoo import api, fields, models
from odoo.tools import email_normalize


class ShopifyConnectorResPartner(models.Model):
    """Connector-owned indexed normalized-email lookup column on
    ``res.partner`` (Task 011B, D-011B-1).

    This is a **performance index only, not a matching-policy change.**
    It stores, per partner, the exact same normalized form the customer
    importer already computes for an incoming Shopify email --
    ``odoo.tools.email_normalize(value, strict=False)`` -- so that
    candidate discovery can run a single btree-indexed equality search
    instead of loading every partner carrying an email and normalizing
    each one in Python (the merged O(n) full scan the importer used
    before Task 011B). Because the stored value is byte-for-byte what the
    removed Python filter compared against, the indexed lookup is
    provably recall-equivalent to the full scan across the pathological
    email corpus (see ``test_customer_matching_scalability.py``).

    Exactly one field is added, via classic ``_inherit`` with no
    behaviour change to ``res.partner``: no ``create``/``write``
    override, no inverse, no search method, no uniqueness constraint, no
    ``sudo()``, no company-dependent behaviour, and no data mutation
    beyond the computed column itself. Email remains the sole automatic
    customer match key -- this field introduces no new key.
    """

    _inherit = 'res.partner'

    shopify_connector_email_normalized = fields.Char(
        string='Shopify Connector Normalized Email',
        compute='_compute_shopify_connector_email_normalized',
        store=True,
        index=True,
        readonly=True,
        help="Connector-owned lookup index: email_normalize(strict=False) "
             "applied to this partner's email, kept identical to the value "
             "the Shopify customer importer normalizes an incoming email to, "
             "so candidate matching uses an indexed equality search instead "
             "of a full partner scan. Performance index only -- not a "
             "matching-policy change.",
    )

    @api.depends('email')
    def _compute_shopify_connector_email_normalized(self):
        """Store the same normalized form the importer computes for an
        incoming Shopify email (``email_normalize(email, strict=False)``),
        recomputed by Odoo on every ``email`` create / write / clear.

        ``email_normalize`` returns ``False`` for a missing, empty, or
        unnormalizable address (``odoo.tools.mail.email_split_tuples``
        guards falsy input with ``if not text: return []``), so an
        email-less or garbage-email partner stores ``False`` (a SQL NULL)
        and is correctly excluded from the importer's truthy-value
        equality search -- exactly as the removed full scan excluded it.
        Applied identically to active and archived partners; the compute
        is independent of ``active``.
        """
        for partner in self:
            partner.shopify_connector_email_normalized = email_normalize(
                partner.email, strict=False,
            ) or False
