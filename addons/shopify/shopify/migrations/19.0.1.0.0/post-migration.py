import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger("Qamah:Shopify")


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    payout_transaction_type_obj = env['shopify.payout.transaction.type']

    # Search for the TRANSFER transaction type ID
    transfer_type_rec = env.ref('shopify.transaction_type_code_transfer', raise_if_not_found=False)
    transfer_type_id = transfer_type_rec.id if transfer_type_rec else False

    # Build mapping from transaction_type_code -> id
    transaction_type_map = {}
    transaction_types = payout_transaction_type_obj.search([])

    for rec in transaction_types:
        if rec.transaction_type_code:
            transaction_type_map[rec.transaction_type_code.upper()] = rec.id

    # Fetch old values stored in pre-migration
    cr.execute("""
        SELECT id, transaction_type_old
        FROM shopify_payout_account_config
        WHERE transaction_type_old IS NOT NULL
    """)

    records = cr.fetchall()
    payout_account_config_model = env['shopify.payout.account.config']

    for rec_id, old_transaction_type in records:

        if not old_transaction_type:
            continue      

        old_type = old_transaction_type.upper()
        new_type_id = False
        # Existing logic for other types
        if old_transaction_type == 'payout' and transfer_type_id:
            new_type_id = transfer_type_id

        elif old_type in transaction_type_map:
            new_type_id = transaction_type_map[old_type]

        if new_type_id:
            payout_account_config_model.browse(rec_id).write({
                'transaction_type_id': new_type_id
            })

    cr.execute("""
        ALTER TABLE shopify_payout_account_config
        DROP COLUMN IF EXISTS transaction_type_old
        """)

    cr.execute("""
        UPDATE mk_listing_item
        SET continue_selling = UPPER(continue_selling)
        WHERE continue_selling IN ('continue', 'deny');
    """)

    cr.execute("""
        DELETE FROM ir_model_fields_selection s
        USING ir_model_fields f
        WHERE s.field_id = f.id
        AND f.model = 'mk.listing.item'
        AND f.name = 'continue_selling'
        AND s.value IN ('continue', 'deny');
    """)

    cr.execute("""
        UPDATE shopify_fraud_analysis
        SET recommendation = UPPER(recommendation)
        WHERE recommendation IN ('cancel', 'investigate', 'accept');
    """)

    cr.execute("""
           DELETE FROM ir_model_fields_selection s
           USING ir_model_fields f
           WHERE s.field_id = f.id
           AND f.model = 'shopify.fraud.analysis'
           AND f.name = 'recommendation'
           AND s.value IN ('cancel', 'investigate', 'accept');
       """)

    cr.execute("""
        UPDATE sale_order
        SET shopify_financial_status = CASE
            WHEN shopify_financial_status = 'pending' THEN 'PENDING'
            WHEN shopify_financial_status = 'authorized' THEN 'AUTHORIZED'
            WHEN shopify_financial_status = 'partially_paid' THEN 'PARTIALLY_PAID'
            WHEN shopify_financial_status = 'paid' THEN 'PAID'
            WHEN shopify_financial_status = 'partially_refunded' THEN 'PARTIALLY_REFUNDED'
            WHEN shopify_financial_status = 'refunded' THEN 'REFUNDED'
            WHEN shopify_financial_status = 'voided' THEN 'VOIDED'
            ELSE shopify_financial_status
        END
        WHERE shopify_financial_status IN ('pending', 'authorized', 'partially_paid', 'paid', 'partially_refunded', 'refunded', 'voided')
          OR shopify_financial_status IS NULL;
    """)

    cr.execute("""
        DELETE FROM ir_model_fields_selection s
        USING ir_model_fields f
        WHERE s.field_id = f.id
        AND f.model = 'sale.order'
        AND f.name = 'shopify_financial_status'
        AND s.value IN ('pending', 'authorized', 'partially_paid', 'paid', 'partially_refunded', 'refunded', 'voided');
    """)

    cr.execute("""
        UPDATE shopify_financial_workflow_config
        SET financial_status = CASE
            WHEN financial_status = 'pending' THEN 'PENDING'
            WHEN financial_status = 'authorized' THEN 'AUTHORIZED'
            WHEN financial_status = 'partially_paid' THEN 'PARTIALLY_PAID'
            WHEN financial_status = 'paid' THEN 'PAID'
            WHEN financial_status = 'partially_refunded' THEN 'PARTIALLY_REFUNDED'
            WHEN financial_status = 'refunded' THEN 'REFUNDED'
            WHEN financial_status = 'voided' THEN 'VOIDED'
            WHEN financial_status = 'any' THEN 'ANY'
            WHEN financial_status = 'unpaid' THEN 'UNPAID'
            ELSE financial_status
        END
        WHERE financial_status IN ('pending', 'authorized', 'partially_paid', 'paid', 'partially_refunded', 'refunded', 'voided', 'any', 'unpaid')
          OR financial_status IS NULL;
    """)

    cr.execute("""
        DELETE FROM ir_model_fields_selection s
        USING ir_model_fields f
        WHERE s.field_id = f.id
        AND f.model = 'shopify.financial.workflow.config'
        AND f.name = 'financial_status'
        AND s.value IN ('pending', 'authorized', 'partially_paid', 'paid', 'partially_refunded', 'refunded', 'voided', 'any', 'unpaid');
    """)

    cr.execute("""
        UPDATE sale_order
        SET fulfillment_status = CASE
            WHEN fulfillment_status = 'partial' THEN 'PARTIALLY_FULFILLED'
            WHEN fulfillment_status = 'fulfilled' THEN 'FULFILLED'
            WHEN fulfillment_status = 'unfulfilled' THEN 'UNFULFILLED'
            WHEN fulfillment_status = 'restocked' THEN 'UNFULFILLED'
            ELSE fulfillment_status
        END
        WHERE fulfillment_status IN ('fulfilled', 'unfulfilled', 'partial', 'restocked')
          OR fulfillment_status IS NULL;
    """)

    cr.execute("""
        DELETE FROM ir_model_fields_selection s
        USING ir_model_fields f
        WHERE s.field_id = f.id
          AND f.model = 'sale.order'
          AND f.name = 'fulfillment_status'
          AND s.value IN ('fulfilled', 'unfulfilled', 'partial', 'restocked');
    """)

    # Task T7221 - Fetch and import product categories from Shopify.
    # Do not call any Shopify API during migration. If any listing is missingq

    # Updates the script to automatically set the sales channel when the number of listings is less than 500 for instance.
    shopify_instances = env['mk.instance'].search([('marketplace', '=', 'shopify')])    
    # Task: T8254 -  set product type & category during sales-channel migration.
    for instance in shopify_instances:
        cr.execute("""
                    SELECT EXISTS (
                        SELECT 1
                    FROM mk_listing l
                    WHERE l.mk_instance_id = %s
                      AND l.is_listed = TRUE
                          AND l.mk_id IS NOT NULL
                          AND (
                              NOT EXISTS (
                          SELECT 1
                          FROM mk_listing_sales_channels_rel rel
                          WHERE rel.mk_listing_id = l.id
                              )
                              OR l.shopify_product_type_id IS NULL
                              OR l.shopify_product_category_id IS NULL
                          )
                      )
                """, (instance.id,))

        has_missing = cr.fetchone()[0]
        # Leave for the user to trigger manually from the UI
        if has_missing:
            instance.write({'need_sync_shopify_sales_channels': True})
