"""P15 canonical store identity and capacity admission."""

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from ..domain.store_admin import (
    MAX_SUPPORTED_STORES,
    StoreCapacityExceeded,
    canonical_shop_domain,
    ensure_store_capacity,
)
from .shopify_connector_p15_shared import P15_CAPACITY_ADVISORY_CLASSID


class ShopifyConnectorP15Store(models.Model):
    """Canonical identity and serialized admission for service creates."""

    _inherit = "shopify.connector.store"

    @api.constrains("shop_domain")
    def _p15_check_canonical_shop_domain(self):
        for store in self:
            try:
                canonical_shop_domain(store.shop_domain)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_(
                    "The Shopify store domain must be a canonical lowercase "
                    "*.myshopify.com host without a scheme or path."
                )) from exc

    @api.model
    def _p15_lock_capacity(self):
        """Serialize all P15 service creates before counting database stores.

        A process-local counter or a row search is not enough: two workers can
        both see nine committed stores and admit a tenth-plus create.  A
        transaction-scoped advisory lock gives every service create one
        database-wide admission point without holding a broad table lock.
        """

        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (P15_CAPACITY_ADVISORY_CLASSID,),
        )
        self.env.cr.execute("SELECT COUNT(*) FROM shopify_connector_store")
        count = int(self.env.cr.fetchone()[0] or 0)
        try:
            ensure_store_capacity(count)
        except StoreCapacityExceeded as exc:
            raise UserError(_(
                "This database supports at most %(limit)d Shopify stores. "
                "Remove an existing store before adding another.",
                limit=MAX_SUPPORTED_STORES,
            )) from exc
        return count

    @api.model
    def _store_service_create(self, surface, vals):
        # Keep the existing closed service shape and root/migration behavior;
        # only P15's explicit service admission receives the capacity fence.
        self._p15_lock_capacity()
        return super()._store_service_create(surface, vals)
