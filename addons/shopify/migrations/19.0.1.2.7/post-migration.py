import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger("Teqstars:Shopify")

# Condition columns the new model needs; the data file does not add them to an existing database.
CANONICAL_COLUMNS = [
    ('TAG', 'Tag'),
    ('PRODUCT_STATUS', 'Product Status'),
    ('PRODUCT_CATEGORY_ID', 'Product Category'),
    ('EXCLUDE_COLLECTION', 'In Collection'),
]

# Relations the old shared list allowed, and the one the column really takes on Shopify. Export
# translates these on the fly, so storing the translated one keeps the form showing what Shopify holds.
TRANSLATE_RELATION = {
    'TAG': {'EQUALS': 'TAGGED_WITH', 'CONTAINS': 'TAGGED_WITH', 'INCLUDES': 'TAGGED_WITH',
            'NOT_EQUALS': 'NOT_TAGGED_WITH', 'NOT_CONTAINS': 'NOT_TAGGED_WITH', 'DOES_NOT_CONTAIN': 'NOT_TAGGED_WITH'},
    'TITLE': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'TYPE': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'VENDOR': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'VARIANT_TITLE': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'PRODUCT_CATEGORY_ID': {'CONTAINS': 'EQUALS', 'NOT_CONTAINS': 'NOT_EQUALS'},
}

MERGE_INTO = {
    'tag': 'TAG',
    'PRODUCT_TAXONOMY_NODE_ID': 'PRODUCT_CATEGORY_ID',
    'PRODUCT_CATEGORY_ID_WITH_DESCENDANTS': 'PRODUCT_CATEGORY_ID',
    'IS_PRICE_REDUCED': 'VARIANT_COMPARE_AT_PRICE',
}


def migrate(cr, version):
    """Task: T8887 - Carry collection conditions over to the 2026-07 model.

    Conditions used to hold a single value in `condition`; a Shopify condition now carries a
    list of values plus its own match type. Existing lines are copied into one value each and
    `match_type` inherits the collection's `condition_type`, so the meaning of every collection
    already imported is preserved:

        any: (b OR d OR Nike)   ->  Tag[b,d] any  OR  Vendor[Nike]  ->  unchanged
        all: (b AND d AND Nike) ->  Tag[b,d] all  AND Vendor[Nike]  ->  unchanged

    Nothing is dropped or renamed: `condition` stays populated, so a line this script cannot
    convert keeps its data and the export path reports it later.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    column_obj = env['shopify.collection.condition.column.ts']
    condition_obj = env['shopify.collection.condition.ts']

    # 1. Every existing condition is an include condition; an empty kind would hide it.
    cr.execute("UPDATE shopify_collection_condition_ts SET kind = 'inclusion' WHERE kind IS NULL")
    _logger.info("tagged %s existing conditions as inclusion.", cr.rowcount)

    # Existing sources are Conditions sources; an empty value would break the required field.
    cr.execute("UPDATE shopify_collection_source_ts SET source_kind = 'conditions' WHERE source_kind IS NULL")
    if cr.rowcount:
        _logger.info("tagged %s existing sources as conditions sources.", cr.rowcount)

    # 2. Point the columns at their canonical record before the values are validated against them.
    for shopify_name, label in CANONICAL_COLUMNS:
        column_id = column_obj.search([('shopify_name', '=', shopify_name)], limit=1)
        if not column_id:
            column_obj.create({'name': label, 'shopify_name': shopify_name})
        elif column_id.name == shopify_name:
            column_id.name = label  # created on the fly by an import, so it kept the raw enum name

    descendant_column_ids = column_obj.search([('shopify_name', '=', 'PRODUCT_CATEGORY_ID_WITH_DESCENDANTS')])
    descendant_condition_ids = condition_obj.search([('column_id', 'in', descendant_column_ids.ids)]).ids if descendant_column_ids else []

    for old_name, new_name in MERGE_INTO.items():
        old_column_ids = column_obj.search([('shopify_name', '=', old_name)])
        target_id = column_obj.search([('shopify_name', '=', new_name)], limit=1)
        if not old_column_ids or not target_id:
            continue
        for condition_id in condition_obj.search([('column_id', 'in', old_column_ids.ids)]):
            # Per line, so one condition the new column cannot accept does not abort the update.
            try:
                with cr.savepoint():
                    condition_id.column_id = target_id
            except Exception as error:
                _logger.warning("left condition %s on %s - %s", condition_id.id, old_name, error)

    # 2b. Relations are canonical now that the columns are, so "tag equals X" becomes "tag is tagged with X".
    translate_legacy_relations(env)

    # 3. Seed the values. Only lines not converted yet, so a re-run cannot duplicate them.
    condition_ids = condition_obj.search([('condition', '!=', False), ('value_ids', '=', False)])
    migrated = skipped = 0
    for condition_id in condition_ids:
        try:
            with cr.savepoint():
                condition_id.match_type = condition_id.shopify_collection_id.condition_type or 'any'
                condition_id.sync_values_from_condition()
            migrated += 1
        except Exception as error:
            skipped += 1
            _logger.warning("left condition %s (%s) untouched - %s", condition_id.id, condition_id.column_id.shopify_name, error)
    _logger.info("seeded values for %s conditions, %s left for review.", migrated, skipped)

    # 3b. The old "with descendants" column is a flag now, and only its own lines carry it.
    restore_include_descendants(env, descendant_condition_ids)

    # 4. Conditions and hand-picked products now belong to a source: give every collection one.
    source_obj = env['shopify.collection.source.ts']
    collection_obj = env['shopify.collection.ts']
    created = 0
    for collection_id in collection_obj.search([]):
        if collection_id.source_ids:
            continue
        source_id = source_obj.create({
            'collection_id': collection_id.id,
            'target_type': 'PRODUCTS',
            'source_kind': 'conditions',
            'inclusion_match_type': collection_id.condition_type or 'any',
        })
        condition_ids = condition_obj.search([('shopify_collection_id', '=', collection_id.id), ('source_id', '=', False)])
        if condition_ids:
            condition_ids.write({'source_id': source_id.id})
        created += 1
    _logger.info("created %s collection sources from the pre-source layout.", created)

    # 5. Hand-picks used to sit in two flat lists; each is now one line carrying both.
    move_selections_onto_their_own_lines(env)

    # 6. Collections were rebuilt from what Odoo already held, which the old model could not
    # fully express, so the form asks for an import until someone does it or closes the strip.
    config_obj = env['ir.config_parameter'].sudo()
    for instance in env['mk.instance'].search([('marketplace', '=', 'shopify')]):
        config_obj.set_param('shopify.collection_import_notice.%s' % instance.id, '1')


def translate_legacy_relations(env):
    """Task: T8887 - Store the relation each column really uses on Shopify.

    The old model kept one relation list for every column, so a tag rule was saved as
    "tag equals X" while Shopify calls it "tag is tagged with X". The export translates it on
    every call, which left the form showing one thing and Shopify holding another until the next
    import overwrote it. Translating once here keeps both reading the same from the upgrade on.

    Args:
        env (Environment): Environment of the migration.
    """
    translated = 0
    for condition_id in env['shopify.collection.condition.ts'].search([('relation', '!=', False)]):
        wanted = TRANSLATE_RELATION.get(condition_id.column_id.shopify_name, {}).get(condition_id.relation)
        if not wanted:
            continue
        # Per line, so one condition the new model refuses does not abort the update.
        try:
            with env.cr.savepoint():
                condition_id.relation = wanted
            translated += 1
        except Exception as error:
            _logger.warning("left condition %s on relation %s - %s", condition_id.id, condition_id.relation, error)
    _logger.info("translated the relation of %s condition(s) to the one Shopify uses.", translated)


def restore_include_descendants(env, condition_ids):
    """Task: T8887 - Keep the meaning of the old PRODUCT_CATEGORY_ID_WITH_DESCENDANTS column.

    That column matched a category and everything under it. It is now PRODUCT_CATEGORY_ID with
    `include_descendants` set on each value, so without this the rule would quietly narrow to the
    exact category: the collection loses the products of every sub-category, and the next export
    writes that narrower rule back to Shopify.

    Args:
        env (Environment): Environment of the migration.
        condition_ids (list): Conditions that sat on the old column before the merge.
    """
    if not condition_ids:
        return
    kept, left_ids = 0, []
    for condition_id in env['shopify.collection.condition.ts'].browse(condition_ids).exists():
        value_ids = condition_id.value_ids.filtered('category_id')
        if not value_ids:
            left_ids.append(condition_id.id)
            continue
        try:
            with env.cr.savepoint():
                value_ids.include_descendants = True
            kept += 1
        except Exception as error:
            left_ids.append(condition_id.id)
            _logger.warning("left condition %s without 'include sub-categories' - %s", condition_id.id, error)
    _logger.info("kept 'include sub-categories' on %s conditions carried over from " "PRODUCT_CATEGORY_ID_WITH_DESCENDANTS.", kept)
    if left_ids:
        _logger.warning("conditions %s came from PRODUCT_CATEGORY_ID_WITH_DESCENDANTS but hold no category " "value, so 'Sub-categories' has to be ticked by hand.", left_ids)


def move_selections_onto_their_own_lines(env):
    """Task: T8887 - Turn the two flat hand-pick lists into one line per product.

    Shopify keeps a hand-pick as a product with the variants of it that were picked, so the two
    many2many tables that used to hold products and variants apart become rows of
    shopify.collection.source.selection.ts, each carrying both.
    """
    cr = env.cr
    cr.execute("SELECT to_regclass('shopify_collection_source_selection_rel')")
    if not cr.fetchone()[0]:
        return  # nothing was ever stored in the old shape

    cr.execute("""
        INSERT INTO shopify_collection_source_selection_ts (source_id, mk_listing_id, mk_instance_id)
        SELECT rel.source_id, rel.listing_id, src.mk_instance_id
          FROM shopify_collection_source_selection_rel rel
          JOIN shopify_collection_source_ts src ON src.id = rel.source_id
         ON CONFLICT (source_id, mk_listing_id) DO NOTHING
    """)
    moved = cr.rowcount

    cr.execute("SELECT to_regclass('shopify_collection_source_selection_item_rel')")
    if cr.fetchone()[0]:
        # A variant only belongs on the line of its own product; anything else was never valid.
        cr.execute("""
            INSERT INTO shopify_source_selection_item_rel (selection_id, item_id)
            SELECT line.id, rel.item_id
              FROM shopify_collection_source_selection_item_rel rel
              JOIN mk_listing_item item ON item.id = rel.item_id
              JOIN shopify_collection_source_selection_ts line
                ON line.source_id = rel.source_id AND line.mk_listing_id = item.mk_listing_id
             ON CONFLICT DO NOTHING
        """)
        _logger.info("moved %s variant hand-pick(s) onto their product lines.", cr.rowcount)
    _logger.info("moved %s product hand-pick(s) onto selection lines.", moved)
