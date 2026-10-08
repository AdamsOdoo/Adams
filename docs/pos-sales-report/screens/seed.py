# Seed for the POS Sales Report screenshots (run by `oh test --keep --seed`; sees `env`).
from datetime import timedelta

from odoo import fields

env.ref('base.user_admin').group_ids |= env.ref('point_of_sale.group_pos_manager')
employees = env['hr.employee'].create([{'name': 'Sara Ahmed'}, {'name': 'Omar Khalil'}])
orders = env['pos.order'].search([('state', 'in', ('paid', 'done'))], order='id')
start = fields.Datetime.now().replace(day=1, hour=9, minute=0, second=0)
for index, order in enumerate(orders):
    order.employee_id = employees[index % 2] if index % 3 else False
    order.date_order = start + timedelta(days=index % 6, hours=index % 9)
env.cr.commit()
print(f"seeded {len(orders)} orders")
