"""Wave 5: translate numeric setup progress onto the semantic step key.

WHY THIS EXISTS

Before this version the guided setup's durable resume point was an integer
position in an eleven-step order. Wave 5 inserts `location_mapping` and moves
readiness to the end, so every position from 6 onward now names a different
step than it did -- a stored `8` meant "Source of truth" and would otherwise
silently mean "Customer notifications" after the upgrade.

The fix is not to renumber. It is to stop addressing steps by number at all:
`setup_wizard_step_key` is the authority from this version on, and the integer
beside it is a rendering of that key's position.

WHAT THIS DOES, AND WHAT IT REFUSES TO DO

It writes `setup_wizard_step_key` for every settings row that has no key yet,
translating the stored number through the OLD eleven-step order. It rewrites
`setup_wizard_step` to that key's position in the NEW order, so the two never
disagree.

It does not reset a store. It does not touch a single durable choice: the
domain flags, the source-of-truth pair, the notification pair, the
first-push schedule, the completion stamps and the re-run stamps are all
left exactly as they are -- this migration moves a resume POINTER and nothing
else. It writes no row that already carries a key, so a re-run is a no-op and
a partially-migrated database converges.

THE TWO TRANSLATIONS THAT ARE NOT ONE-TO-ONE

Legacy 6 was "Readiness checks", which no longer exists at that position.
Its evidence is not discarded -- the `core_readiness_check` job rows and the
store's `last_readiness_*` mirrors are untouched, and the new
`final_readiness` step re-evaluates them against the current configuration.
What moves is the resume point, to `directions`, the first step of the new
order that store has not answered. Legacy 7 was already `directions`, so both
land in the same place and the mapping stays monotonic.

Legacy 8 and above resume past the new `location_mapping` step, which those
stores never had. That is not a silent skip: a store with the inventory
domain enabled and no mapping gets `mapped_location` reported as Blocking on
the final-readiness step, with a "Fix location mapping" action that
deep-links back to the step by key.

`shopify.connector.setup.wizard._resume_key` performs the identical
translation at READ time, so a row this migration never reached -- an older
dump restored afterwards, a fixture that wrote the number directly -- resumes
in the same place rather than being treated as brand new.
"""

import logging

_logger = logging.getLogger(__name__)

#: The pre-Wave-5 eleven-step order -> the semantic key it becomes. Kept
#: literal here rather than imported: a migration must describe the schema it
#: is migrating FROM, and importing the live constant would make this script
#: silently follow any future reordering instead of the one it was written for.
LEGACY_NUMERIC_STEP_KEYS = {
    1: 'welcome',
    2: 'identity',
    3: 'credential',
    4: 'scopes',
    5: 'test_connection',
    6: 'directions',
    7: 'directions',
    8: 'source_of_truth',
    9: 'notification',
    10: 'first_push',
    11: 'review',
}

#: The Wave 5 order. Position is derived from this list, never hard-coded.
SETUP_STEP_KEYS = (
    'welcome', 'identity', 'credential', 'scopes', 'test_connection',
    'directions', 'location_mapping', 'source_of_truth', 'notification',
    'first_push', 'final_readiness', 'review',
)
STEP_ORDER = {key: index for index, key in enumerate(SETUP_STEP_KEYS, start=1)}


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'shopify_connector_store_settings' "
        "AND column_name IN ('setup_wizard_step', 'setup_wizard_step_key')"
    )
    present = {row[0] for row in cr.fetchall()}
    if {'setup_wizard_step', 'setup_wizard_step_key'} - present:
        # The ORM creates both columns before post-migrate runs; if either is
        # absent something is wrong enough that guessing would be worse than
        # doing nothing.
        _logger.warning(
            'Shopify connector: setup-progress columns are not both present '
            '(%s); the semantic step-key translation was skipped.',
            sorted(present),
        )
        return

    cr.execute(
        "SELECT id, setup_wizard_step FROM shopify_connector_store_settings "
        "WHERE setup_wizard_step_key IS NULL OR setup_wizard_step_key = ''"
    )
    rows = cr.fetchall()
    if not rows:
        return

    translated = 0
    for settings_id, legacy_step in rows:
        try:
            legacy = int(legacy_step or 1)
        except (TypeError, ValueError):
            legacy = 1
        key = LEGACY_NUMERIC_STEP_KEYS.get(legacy)
        if key is None:
            # Above the legacy range: the number can only have come from a
            # build already using this order, so clamp into it rather than
            # invent a step. Below it (0 or negative) is the first step.
            index = min(max(legacy, 1), len(SETUP_STEP_KEYS))
            key = SETUP_STEP_KEYS[index - 1]
        cr.execute(
            "UPDATE shopify_connector_store_settings "
            "SET setup_wizard_step_key = %s, setup_wizard_step = %s "
            "WHERE id = %s",
            (key, STEP_ORDER[key], settings_id),
        )
        translated += 1

    _logger.info(
        'Shopify connector: translated numeric setup progress to the '
        'semantic step key for %d store settings row(s).', translated,
    )
