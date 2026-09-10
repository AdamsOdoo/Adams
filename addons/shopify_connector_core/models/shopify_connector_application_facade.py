"""Explicit application-boundary compatibility facade.

The application facade is intentionally narrow in this foundation slice.  It
does not expose a generic model/method dispatcher and it does not implement
commands before their owning runtime contracts exist.  The four read methods
are named delegates to the UI query facade so a caller cannot bypass its role,
active-company and exact-store checks by selecting a different entry point.
"""

from odoo import api, models


class ShopifyConnectorApplicationFacade(models.AbstractModel):
    """Named V2 application RPC seam; read methods only for P02."""

    _name = "shopify.connector.application.facade"
    _description = "Shopify Connector V2 Application Facade"

    @api.model
    def _ui(self):
        return self.env["shopify.connector.ui.facade"]

    @api.model
    def get_overview_v1(self, store_id):
        return self._ui().get_overview_v1(store_id)

    @api.model
    def search_attention_v1(
        self,
        store_id,
        limit=80,
        offset=0,
        filters=None,
        cursor=None,
    ):
        return self._ui().search_attention_v1(
            store_id,
            limit=limit,
            offset=offset,
            filters=filters,
            cursor=cursor,
        )

    @api.model
    def get_attention_v1(self, store_id, item_ref):
        return self._ui().get_attention_v1(store_id, item_ref)

    @api.model
    def get_attention_detail_v1(self, store_id, item_ref):
        """Compatibility spelling for the canonical attention detail read."""

        return self._ui().get_attention_detail_v1(store_id, item_ref)

    @api.model
    def get_run_v1(self, store_id, run_ref):
        return self._ui().get_run_v1(store_id, run_ref)


__all__ = ["ShopifyConnectorApplicationFacade"]
