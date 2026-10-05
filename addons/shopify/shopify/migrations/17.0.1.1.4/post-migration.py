# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute("""
           UPDATE sale_order SET shopify_mk_id = mk_id;
    """)
