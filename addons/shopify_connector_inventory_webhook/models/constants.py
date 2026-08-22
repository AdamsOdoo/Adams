"""Frozen contracts for the inventory webhook observation addon."""

INVENTORY_WEBHOOK_TOPIC = 'inventory_levels/update'
INVENTORY_WEBHOOK_TOPICS = (INVENTORY_WEBHOOK_TOPIC,)
INVENTORY_WEBHOOK_HANDLER = 'inventory_observation_sync'
INVENTORY_OBSERVATION_JOB_TYPE = 'inventory_observation_sync'

# Shopify's inventory_levels/update payload is intentionally narrowed to the
# exact identifiers and observation fields this read-first signal needs. The
# raw snake_case names are the webhook contract; do not replace them with
# GraphQL camelCase names.
INVENTORY_WEBHOOK_INCLUDE_FIELDS = [
    'admin_graphql_api_id',
    'inventory_item_id',
    'location_id',
    'available',
    'updated_at',
]

INVENTORY_OBSERVATION_STATES = [
    ('accepted', 'Accepted'),
    ('stale', 'Stale'),
    ('duplicate', 'Duplicate'),
    ('deferred', 'Deferred'),
    ('manual_review', 'Manual Review'),
]

INVENTORY_OBSERVATION_SOURCES = [
    ('webhook', 'Webhook'),
    ('scheduled_sync', 'Scheduled Observation'),
]

# These are the inventory pair-lineage job types that can be handing off to,
# performing, or reconciling Shopify stock work. Observation code uses this
# closed tuple to defer while that lineage is active; it never invokes or
# enqueues any of them.
OUTBOUND_INVENTORY_JOB_TYPES = (
    'inventory_push_sync',
    'inventory_first_push_preview',
    'inventory_activate',
    'inventory_set_quantities',
    'inventory_mutation_reconcile',
)

OBSERVATION_FALLBACK_BATCH = 20
OBSERVATION_FALLBACK_MAX_BATCH = 100
# A reconciliation pass is intentionally a store scheduler as well as a
# pair scheduler.  Keeping this ceiling separate from the pair batch means a
# database with hundreds of connected stores cannot turn one cron tick into
# an all-store scan.  The store checkpoint is advanced only after the store
# was explicitly accounted for (no eligible pair) or a selected pair was
# admitted/coalesced.
OBSERVATION_FALLBACK_STORE_LIMIT = 10


def fair_rotation(ids, cursor, limit):
    """Return a bounded, wrap-around page after a persisted cursor.

    ``ids`` must already be an ascending list of durable binding IDs. Keeping
    this function pure makes the fairness contract testable without a database
    and avoids relying on backend-specific NULL ordering.
    """
    ordered = [value for value in ids if value > (cursor or 0)]
    ordered.extend(value for value in ids if value <= (cursor or 0))
    return tuple(ordered[:max(0, min(int(limit or 0), len(ordered)))])


def observation_payload_hash(level_gid, source_stamp, payload_digest, generation):
    """Build a reconnect-fenced webhook observation identity."""
    return '|'.join((
        'inventory-observation',
        level_gid or '',
        source_stamp or '',
        payload_digest or '',
        'connection_generation:%d' % int(generation or 0),
    ))


def fallback_payload_hash(level_gid, run_nonce):
    """Make each bounded fallback pass eligible after terminal evidence."""
    return 'inventory-observation-fallback|%s|%s' % (level_gid, run_nonce)
