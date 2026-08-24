"""Keep pre-1.9 preview rows confirmable while new previews gain freshness proof."""

import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # The new timestamp is deliberately left NULL on historical previewed
    # rows. They predate the quantity-freshness evidence and retain their
    # previous confirmation behavior; the next preview refresh writes both
    # quantity and timestamp and enables the strict stale check.
    cr.execute(
        "SELECT to_regclass('shopify_connector_inventory_level_binding')"
    )
    if not cr.fetchone()[0]:
        return
    cr.execute(
        """
        SELECT COUNT(*)
          FROM shopify_connector_inventory_level_binding
         WHERE first_push_state = 'previewed'
           AND first_push_previewed_at IS NULL
        """
    )
    legacy_count = cr.fetchone()[0]
    _logger.info(
        'Inventory first-push migration retained %d legacy preview(s); '
        'fresh previews will enforce quantity freshness.',
        legacy_count,
    )
