# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    collection = env["shopify.collection.ts"].search([])
    for collection in collection:
        condition_type = 'any' if collection.is_disjunctive else 'all'
        collection.condition_type = condition_type
