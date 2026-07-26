"""SEC-2 section E: audit rows the pre-SEC-2 sweep masked irreversibly.

Masking overwrote the stored value with a sentinel, so the original cannot be
recovered from the database. This migration therefore does exactly two
honest things: it counts the affected rows and records that count. It does
NOT attempt to reconstruct, infer, or fabricate any original value, and it
does not clear the sentinel -- clearing it would erase the only evidence that
the row needs a refresh.

Affected rows surface in the UI through the computed
`pii_snapshot_refresh_required` flag on the binding; refreshing them requires
a Shopify re-import, which this migration does not and must not perform.

The audit records counts only. No snapshot value -- masked or otherwise -- is
written to the log.
"""

import logging

_logger = logging.getLogger(__name__)

MASKED_SENTINEL = '***'


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'shopify_connector_customer_binding'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT COUNT(*)
          FROM shopify_connector_customer_binding
         WHERE shopify_display_name   = %(sentinel)s
            OR shopify_email_snapshot = %(sentinel)s
            OR shopify_phone_snapshot = %(sentinel)s
        """,
        {'sentinel': MASKED_SENTINEL},
    )
    affected = cr.fetchone()[0]
    cr.execute('SELECT COUNT(*) FROM shopify_connector_customer_binding')
    total = cr.fetchone()[0]
    _logger.info(
        'SEC-2 PII simplification: %d of %d customer bindings carry '
        'irreversibly masked snapshots and are flagged for refresh/re-import. '
        'Original values are not recoverable and were not reconstructed.',
        affected,
        total,
    )
