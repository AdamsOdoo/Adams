# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    conditions = env["shopify.collection.condition.ts"].search([])
    for condition in conditions:
        condition.column_id = env["shopify.collection.condition.column.ts"].search([('shopify_name', '=', condition.column)])
