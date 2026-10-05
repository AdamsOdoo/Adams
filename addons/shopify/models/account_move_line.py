from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _reconcile_plan_with_sync(self, plan_list, all_amls):
        """
        Reconciles payments and mark order as paid when a full payment is registered of an order.

        Args:
            plan_list (list): Reconciliation plans,
            all_amls (recordset): Account move lines,

        Returns:
            result: Super call result
        """
        res = super(AccountMoveLine, self)._reconcile_plan_with_sync(plan_list, all_amls)

        if not plan_list or self.env.context.get('is_register_from_order_workflow'):
            return res

        PAYMENT_STATE = ('paid', 'in_payment')

        for plan in plan_list:
            amls = plan.get('amls')

            move_id = amls.move_id
            order_ids = move_id.line_ids.sale_line_ids.order_id.filtered(lambda o: o.marketplace == 'shopify' and o.mk_instance_id.mark_order_paid_from_odoo)
            invoice_ids = move_id.filtered(lambda m: m.is_invoice(include_receipts=True) and m.payment_state in PAYMENT_STATE and m.line_ids.sale_line_ids.order_id)

            for invoice_id in invoice_ids:
                related_order_ids = order_ids.filtered(lambda o: invoice_id.id in o.invoice_ids.ids)
                if not related_order_ids:
                    continue

                for related_order_id in related_order_ids:
                    related_order_id.process_shopify_order_payment_status()

        return res
