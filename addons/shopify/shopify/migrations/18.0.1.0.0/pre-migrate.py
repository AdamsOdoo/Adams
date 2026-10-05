# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import column_exists, constraint_definition


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if column_exists(env.cr, "shopify_payout_account_config", "account_id"):
        if constraint_definition(cr, "shopify_payout_account_config", "shopify_payout_account_config_account_id_fkey"):
            cr.execute("""ALTER TABLE shopify_payout_account_config DROP CONSTRAINT shopify_payout_account_config_account_id_fkey""")
        cr.execute("""
            ALTER TABLE shopify_payout_account_config 
            ALTER COLUMN account_id TYPE jsonb
            USING jsonb_build_object(company_id::text, account_id);
        """)
