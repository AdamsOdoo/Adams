"""Verify the W1 subscription evidence schema during its version upgrade.

The expected/actual ``includeFields`` evidence belongs to the generic webhook
subscription model because the base reconciliation service owns the remote
read-back contract.  The manifest bump makes an existing W1 installation run
this upgrade before an optional domain addon relies on those fields.  Odoo's
registry/schema phase creates the JSONB columns from the model declarations;
this post-migrate check fails loudly if that phase did not do so rather than
allowing a W2 install to mask a partial dependency upgrade.
"""

import logging


_logger = logging.getLogger(__name__)
_TABLE = 'shopify_connector_webhook_subscription'
_COLUMNS = frozenset(('expected_include_fields', 'actual_include_fields'))


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = ANY(%s)",
        (_TABLE, list(_COLUMNS)),
    )
    present = {row[0] for row in cr.fetchall()}
    missing = sorted(_COLUMNS - present)
    if missing:
        raise RuntimeError(
            'Shopify webhook schema upgrade did not create required '
            'includeFields evidence column(s): %s' % ', '.join(missing)
        )
    _logger.info(
        'Shopify webhook W1 upgrade verified includeFields evidence columns '
        'on %s.', _TABLE,
    )
