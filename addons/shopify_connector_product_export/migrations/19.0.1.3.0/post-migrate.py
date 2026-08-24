"""Seed imported status and disable implicit status ownership safely."""

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('shopify_connector_product_template_binding')")
    if not cr.fetchone()[0]:
        return
    # A template can be bound to more than one store. Seed the visible local
    # value only when every supported remote binding agrees; regardless, omit
    # status from future updates until a person explicitly manages it.
    cr.execute(
        """
        WITH imported AS (
            SELECT product_template_id,
                   CASE WHEN COUNT(DISTINCT shopify_status) = 1
                        AND MIN(shopify_status) IN ('active', 'draft', 'archived')
                        THEN MIN(shopify_status)
                        ELSE NULL
                   END AS agreed_status
              FROM shopify_connector_product_template_binding
             GROUP BY product_template_id
        )
        UPDATE product_template AS pt
           SET shopify_export_status = COALESCE(
                   imported.agreed_status, pt.shopify_export_status
               ),
               shopify_export_status_managed = FALSE
          FROM imported
         WHERE pt.id = imported.product_template_id
           AND (
               pt.shopify_export_status_managed IS DISTINCT FROM FALSE
            OR (imported.agreed_status IS NOT NULL
                AND pt.shopify_export_status IS DISTINCT FROM imported.agreed_status)
           )
        """
    )
    _logger.info(
        'Product status ownership migration seeded/disabled implicit status '
        'export for %d imported template(s).', cr.rowcount,
    )
