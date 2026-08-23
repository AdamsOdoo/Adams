"""Seed the new composition evidence without inventing historical truth.

Existing orders have no immutable Shopify line snapshot from which the new
fingerprint can be reconstructed. Leave it NULL: the next complete Shopify
read seeds it, and only later reads may compare it. Review states and uncertain
mutation evidence are never reinterpreted by this migration.
"""

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('shopify_connector_order_binding')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        """
        UPDATE shopify_connector_order_binding
           SET shopify_line_composition_fingerprint = NULL
         WHERE shopify_line_composition_fingerprint = ''
        """
    )
    _logger.info(
        'Order composition evidence migration normalized %d empty legacy '
        'fingerprint(s); the next complete read will seed them.', cr.rowcount,
    )
