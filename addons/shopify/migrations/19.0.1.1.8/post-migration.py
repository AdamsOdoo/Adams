import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger("Teqstars:Shopify")

# Old ReturnReason enum -> new ReturnReasonDefinition handle
RETURN_REASON_ENUM_TO_HANDLE = {
    'COLOR': 'color',
    'DEFECTIVE': 'damaged-or-defective',
    'NOT_AS_DESCRIBED': 'item-not-as-described',
    'OTHER': 'other-reason',
    'FLEX': 'flex',
    'UNKNOWN': 'unknown',
    'UNWANTED': 'changed-my-mind',
    'WRONG_ITEM': 'received-the-wrong-item',
}

def migrate(cr, version):

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Create the target records: sync the reason catalog per confirmed Shopify instance.
    instances = env['mk.instance'].search([
        ('marketplace', '=', 'shopify'),
        ('state', '=', 'confirmed'),
    ])
    for instance in instances:
        try:
            env['shopify.return.reason.ts'].import_return_reasons_from_shopify(instance)
        except Exception as e:
            _logger.warning("Migration: return reasons sync failed for %s: %s", instance.name, e)

    # 2. Transfer data: map snapshot enum -> handle -> reason record (per instance).
    #    Skip if the temp column was never created (fresh install / pre-migration skipped).
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shopify_return_line_ts'
          AND column_name = 'return_reason_old'
    """)
    has_temp_column = bool(cr.fetchone())

    for enum, handle in (RETURN_REASON_ENUM_TO_HANDLE.items() if has_temp_column else []):
        cr.execute("""
            UPDATE shopify_return_line_ts line
            SET return_reason_definition_id = reason.id
            FROM shopify_return_reason_ts reason
            WHERE line.return_reason_old = %s
              AND reason.handle = %s
              AND reason.mk_instance_id = line.mk_instance_id
              AND line.return_reason_definition_id IS NULL
        """, (enum, handle))

    # 3. Cleanup temp column
    cr.execute("ALTER TABLE shopify_return_line_ts DROP COLUMN IF EXISTS return_reason_old")