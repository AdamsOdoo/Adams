# Store 360 slice 1: backfill the eleven protected sale-order projection
# columns from each order's binding.
#
# Runs after the ORM has created the columns for 19.0.2.9.0. Bounded and
# idempotent: the WHERE clause updates only rows whose projection actually
# disagrees with their binding, so a re-run (or a re-install over orphaned
# columns after a code revert) touches zero rows once converged. SQL is the
# right tool here — this is the install/upgrade maintenance path, the exact
# scope the runtime dashboard's no-raw-SQL guard excludes — and the join is
# the binding's own (store_id, sale_order_id) identity, whose company
# consistency the binding constraints already enforce.
#
# Rollback posture (handoff §12): reverting the module code leaves these
# columns and their backfilled values harmlessly orphaned; structural
# removal is a separate forward cleanup migration, never automatic.

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('shopify_connector_order_binding')")
    if not cr.fetchone()[0]:
        # Fresh chain without the binding table: nothing to backfill.
        return
    cr.execute(
        """
        UPDATE sale_order AS o
           SET shopify_connector_store_id = b.store_id,
               shopify_connector_cancelled_at = b.shopify_cancelled_at,
               shopify_connector_quarantined =
                   COALESCE(b.sec3_scope_quarantined, FALSE),
               shopify_connector_financial_status =
                   b.shopify_financial_status_snapshot,
               shopify_connector_is_cod = COALESCE(b.is_cod, FALSE),
               shopify_connector_approval_state =
                   b.manual_gateway_approval_state,
               shopify_connector_cod_commercial_state =
                   b.cod_commercial_state,
               shopify_connector_cod_collection_state =
                   b.cod_collection_state,
               shopify_connector_fulfillment_status =
                   b.shopify_fulfillment_status_snapshot,
               shopify_connector_review = (b.status = 'review'),
               shopify_connector_evidence_refreshed_at =
                   b.shopify_last_evidence_refresh_at
          FROM shopify_connector_order_binding AS b
         WHERE b.sale_order_id = o.id
           AND (
               o.shopify_connector_store_id IS DISTINCT FROM b.store_id
            OR o.shopify_connector_cancelled_at
                   IS DISTINCT FROM b.shopify_cancelled_at
            OR o.shopify_connector_quarantined
                   IS DISTINCT FROM COALESCE(b.sec3_scope_quarantined, FALSE)
            OR o.shopify_connector_financial_status
                   IS DISTINCT FROM b.shopify_financial_status_snapshot
            OR o.shopify_connector_is_cod
                   IS DISTINCT FROM COALESCE(b.is_cod, FALSE)
            OR o.shopify_connector_approval_state
                   IS DISTINCT FROM b.manual_gateway_approval_state
            OR o.shopify_connector_cod_commercial_state
                   IS DISTINCT FROM b.cod_commercial_state
            OR o.shopify_connector_cod_collection_state
                   IS DISTINCT FROM b.cod_collection_state
            OR o.shopify_connector_fulfillment_status
                   IS DISTINCT FROM b.shopify_fulfillment_status_snapshot
            OR o.shopify_connector_review
                   IS DISTINCT FROM (b.status = 'review')
            OR o.shopify_connector_evidence_refreshed_at
                   IS DISTINCT FROM b.shopify_last_evidence_refresh_at
           )
        """
    )
    _logger.info(
        'Store 360 slice 1: backfilled the sale-order projection for %d '
        'bound order(s).', cr.rowcount,
    )
