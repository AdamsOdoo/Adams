"""Batch 2 correction F1/F2/F3: retire every `v1` product match decision.

WHAT THE `v1` ROWS ARE. Before this version the durable decision recorded its
Shopify Product GID, ProductVariant GID and remote `updatedAt` after passing
them through `safe_match_preview` -- a DISPLAY scrubber whose phone-number
pattern rewrites any run of seven or more digits. Every realistic Shopify GID
carries one, so `gid://shopify/Product/7346299043911` was stored as
`gid://shopify/Product/[redacted-phone]`, and the exact SKU/barcode match values
were flattened the same way.

WHY THE ROWS CANNOT BE REPAIRED. The transformation is not invertible. The
original digits are not in the database, in the job, or anywhere else: the
importer's payload was discarded when the savepoint rolled back. There is no
honest way to reconstruct which product a `v1` row was about, and two different
products could produce the same stored identity, so "pick the plausible one" is
not a repair -- it is a coin toss that could bind a store's catalog to the wrong
master data. This migration therefore SUPERSEDES rather than reinterprets.

WHAT IT TOUCHES, AND WHAT IT DELIBERATELY DOES NOT.

* `pending` and `confirmed` rows keyed under `v1` become `superseded` with a
  stated reason. They could never have been consumed anyway -- `_confirmed_for`
  computes its key from the raw payload and would never match a `v1` key -- so
  this changes no import outcome. It changes what the merchant is shown: an
  actionable-looking decision that cannot act becomes an honest dead one, and
  the next import raises a fresh ambiguity under the corrected identity rules.
* `consumed` rows are left exactly as they are. A consumed decision has already
  produced a binding, that binding is independently valid, and rewriting the
  decision would falsify the audit trail of a correct outcome.
* Already-`superseded` rows are left alone.
* The obsolete `match_values` column is dropped. It held display-sanitized
  identifier copies that the corrected code never reads and that must not
  survive as a second, wrong answer to "what did Shopify send?".

Idempotent: a second run matches no `v1` row and finds no column to drop.

No Shopify request. No binding is created, altered or deleted.
"""

import logging

_logger = logging.getLogger(__name__)

TABLE = 'shopify_connector_product_match_decision'

SUPERSEDED_REASON = (
    'This decision was recorded under the superseded v1 identity rules, which '
    'stored a display-sanitized copy of the Shopify product identity instead '
    'of the identity itself. The original identity cannot be recovered, so the '
    'decision cannot be applied to any import and has been retired. The next '
    'import of this product raises a fresh decision against what Shopify sends '
    'now.'
)


def _table_exists(cr, table):
    cr.execute(
        'SELECT 1 FROM information_schema.tables WHERE table_name = %s',
        (table,),
    )
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        'SELECT 1 FROM information_schema.columns '
        ' WHERE table_name = %s AND column_name = %s',
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not _table_exists(cr, TABLE):
        return

    cr.execute(
        """
        UPDATE %s
           SET state = 'superseded',
               superseded_reason = %%(reason)s
         WHERE state IN ('pending', 'confirmed')
           AND decision_key IS NOT NULL
           AND decision_key NOT LIKE 'v2:%%%%'
        """ % TABLE,
        {'reason': SUPERSEDED_REASON},
    )
    retired = cr.rowcount

    cr.execute(
        """
        SELECT COUNT(*) FROM %s
         WHERE state = 'consumed'
           AND decision_key IS NOT NULL
           AND decision_key NOT LIKE 'v2:%%'
        """ % TABLE
    )
    kept = cr.fetchone()[0]

    if _column_exists(cr, TABLE, 'match_values'):
        cr.execute('ALTER TABLE %s DROP COLUMN match_values' % TABLE)
        dropped = True
    else:
        dropped = False

    _logger.info(
        'Batch 2 correction (product match decision v1 -> v2): %d undecided '
        'or decided-but-unconsumable decision(s) retired as superseded; %d '
        'already-consumed decision(s) left untouched with their bindings '
        'intact; obsolete match_values column dropped: %s.',
        retired, kept, dropped,
    )
