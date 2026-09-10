"""Read-only W2 installation prerequisite (approved compatibility decision 19).

Owner modules must be upgraded using their versioned migrations. W2 never
creates or seeds another owner's schema to disguise an old installation.
"""


def check_owner_versions(cr, manifest_loader):
    """Use only stable module metadata; an old connector registry is unsafe."""
    cr.execute(
        "SELECT name, latest_version, state FROM ir_module_module "
        "WHERE name LIKE %s AND name != %s "
        "AND state IN ('installed', 'to upgrade', 'to remove') ORDER BY name",
        ('shopify\\_connector\\_%', 'shopify_connector_product_webhook'),
    )
    problems = []
    for name, installed, state in cr.fetchall():
        manifest = manifest_loader(name) or {}
        expected = manifest.get('version')
        if not expected:
            problems.append('%s: installed %s, source unavailable' % (name, installed))
        elif installed != expected or state != 'installed':
            problems.append('%s: installed %s, source %s, state %s' % (
                name, installed, expected, state,
            ))
    if problems:
        raise RuntimeError(
            'W2 installation requires matching, fully upgraded connector owners. '
            'Back up the database and matching source, complete the normal '
            'versioned upgrade of the listed installed modules, then install W2. '
            'If the installed version is newer, restore matching source; do not '
            'downgrade the database. No owner schema was changed by this check. '
            + '; '.join(problems)
        )


def pre_init_hook(env):
    """Refuse mixed source/schema versions before installing W2."""
    from odoo.modules.module import get_manifest

    check_owner_versions(env.cr, get_manifest)
