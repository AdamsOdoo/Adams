"""Shared machinery for the per-module canonical Store Settings
field-classification tests (Batch 2 checkpoint 1, §6.6).

WHY THIS IS SHARED RATHER THAN COPIED FOUR TIMES. Every module that adds a
field to ``shopify.connector.store.settings`` owes the same answer about it:
is it a decision an Administrator takes on the canonical form, an observation
shown there read-only, something a different dedicated surface already owns,
or internal structure that must never be rendered as ordinary configuration?
Four copies of that question would drift, and the one that drifted would be
the one that stopped noticing a newly added field.

WHY THERE IS NO EXPECTED FIELD COUNT ANYWHERE IN HERE. A hard-coded total is
satisfied by any set of the right size, so it passes when a field is added and
another removed, and it says nothing about the field that was added. The
assertion below is set equality against the LIVE registry instead: add a field
to the model in any module and that module's test fails until the field is
classified by name.
"""

from lxml import etree

SETTINGS_MODEL = 'shopify.connector.store.settings'

CANONICAL_FORM_XMLID = (
    'shopify_connector_core.view_shopify_connector_store_settings_canonical_form'
)
CANONICAL_LIST_XMLID = (
    'shopify_connector_core.view_shopify_connector_store_settings_canonical_list'
)
CANONICAL_ACTION_XMLID = (
    'shopify_connector_core.action_shopify_connector_store_settings_canonical'
)

# The four classifications §6.6 allows, and nothing else.
CANONICAL_EDITABLE = 'canonical_editable'
CANONICAL_READONLY = 'canonical_readonly'
OWNED_BY_SURFACE = 'owned_by_dedicated_surface'
INTERNAL_PROTECTED = 'internal_protected'

_CLASSIFICATIONS = (
    CANONICAL_EDITABLE,
    CANONICAL_READONLY,
    OWNED_BY_SURFACE,
    INTERNAL_PROTECTED,
)

# Contributed by ``base`` on every model; never this connector's to classify.
_MAGIC_FIELDS = frozenset({
    'id', 'display_name', 'create_uid', 'create_date', 'write_uid',
    'write_date',
})


def fields_contributed_by(env, module):
    """The settings fields `module` declares, from the live registry.

    ``Field._modules`` is the tuple of modules that define a field (Odoo 19,
    ``odoo/orm/fields.py``). A field declared once appears under exactly one
    module; a field several modules extend appears under each, which is the
    honest answer -- each of them owes a classification for it.
    """
    model = env[SETTINGS_MODEL]
    return {
        name
        for name, field in model._fields.items()
        if name not in _MAGIC_FIELDS and module in (field._modules or ())
    }


def canonical_form_field_nodes(env):
    """``{field_name: node}`` for the COMBINED canonical form.

    Combined, not the raw core arch: the domain sections arrive through
    ``inherit_id`` + xpath, so reading the stored core arch would report every
    domain field as missing. ``get_view`` is what the web client itself calls,
    so this asserts against the form a merchant actually receives.
    """
    view = env.ref(CANONICAL_FORM_XMLID)
    arch = etree.fromstring(
        env[SETTINGS_MODEL].get_view(view.id, 'form')['arch']
    )
    return {
        node.get('name'): node
        for node in arch.iter('field')
        if node.get('name')
    }


def _is_marked_readonly(node):
    return (node.get('readonly') or '').strip() in ('1', 'True', 'true')


def assert_module_classification(case, module, classification):
    """Assert `module` classifies every settings field it contributes.

    `classification` maps field name -> (classification, justification). The
    justification is required for the two "not on the canonical form"
    classifications, because those are the ones that hide something: §6.6 asks
    for a NAMED surface or a NAMED reason, so an empty string fails here
    rather than passing as a shrug.
    """
    env = case.env
    contributed = fields_contributed_by(env, module)
    classified = set(classification)

    unclassified = contributed - classified
    case.assertFalse(
        unclassified,
        '%s contributes these settings fields with no canonical '
        'classification: %s. Every field a module adds to %s must be '
        'classified by name.' % (
            module, sorted(unclassified), SETTINGS_MODEL,
        ),
    )
    stale = classified - contributed
    case.assertFalse(
        stale,
        '%s classifies these settings fields but no longer contributes '
        'them: %s.' % (module, sorted(stale)),
    )

    form_nodes = canonical_form_field_nodes(env)
    model_fields = env[SETTINGS_MODEL]._fields

    for name, (kind, justification) in sorted(classification.items()):
        case.assertIn(
            kind, _CLASSIFICATIONS,
            '%s.%s carries an unknown classification %r.' % (
                module, name, kind,
            ),
        )

        if kind == CANONICAL_EDITABLE:
            case.assertIn(
                name, form_nodes,
                '%s.%s is classified canonical-editable but is not on the '
                'canonical Store Settings form.' % (module, name),
            )
            case.assertFalse(
                _is_marked_readonly(form_nodes[name]),
                '%s.%s is classified canonical-editable but the canonical '
                'form marks it readonly.' % (module, name),
            )
            case.assertFalse(
                model_fields[name].readonly,
                '%s.%s is classified canonical-editable but the field itself '
                'is readonly, so the form cannot save it.' % (module, name),
            )
        elif kind == CANONICAL_READONLY:
            case.assertIn(
                name, form_nodes,
                '%s.%s is classified canonical-readonly but is not on the '
                'canonical Store Settings form.' % (module, name),
            )
            case.assertTrue(
                _is_marked_readonly(form_nodes[name]),
                '%s.%s is classified canonical-readonly but the canonical '
                'form does not mark it readonly, so it renders as an '
                'editable control.' % (module, name),
            )
        else:
            case.assertTrue(
                (justification or '').strip(),
                '%s.%s is classified %s with no named justification.' % (
                    module, name, kind,
                ),
            )
            case.assertNotIn(
                name, form_nodes,
                '%s.%s is classified %s (%s) but is rendered on the '
                'canonical Store Settings form anyway.' % (
                    module, name, kind, justification,
                ),
            )
