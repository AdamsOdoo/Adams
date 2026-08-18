"""Minimal schema bridge for installing W2 over an older installed W1.

W1 remains the canonical owner of these fields and its versioned migration
verifies them when W1 itself is upgraded.  Odoo does not upgrade an already
installed dependency during ``-i shopify_connector_product_webhook`` though,
so this optional addon must make the two additive columns available before the
current W1 registry is loaded.  The bridge is deliberately SQL-only,
idempotent, and limited to the known W1-owned table/columns.
"""

_TABLE = 'shopify_connector_webhook_subscription'
_COLUMNS = (
    'expected_include_fields',
    'actual_include_fields',
)


def pre_init_hook(env):
    """Create and verify the W1 evidence columns before registry setup."""
    cr = env.cr
    cr.execute(
        'ALTER TABLE IF EXISTS "%s" '
        'ADD COLUMN IF NOT EXISTS expected_include_fields jsonb, '
        'ADD COLUMN IF NOT EXISTS actual_include_fields jsonb' % _TABLE,
    )
    cr.execute(
        "SELECT column_name, udt_name FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = ANY(%s)",
        (_TABLE, list(_COLUMNS)),
    )
    columns = {row[0]: row[1] for row in cr.fetchall()}
    missing = [name for name in _COLUMNS if name not in columns]
    wrong_type = [
        name for name in _COLUMNS
        if name in columns and columns[name] != 'jsonb'
    ]
    if missing or wrong_type:
        details = []
        if missing:
            details.append('missing: %s' % ', '.join(missing))
        if wrong_type:
            details.append('non-jsonb: %s' % ', '.join(wrong_type))
        raise RuntimeError(
            'W2 cannot install safely over the installed W1 schema (%s).'
            % '; '.join(details)
        )
