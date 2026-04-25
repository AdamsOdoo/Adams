# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Payment status transition handler for Shopify → Odoo.

Handles financial status changes received via webhooks or periodic imports
and applies the corresponding accounting actions in Odoo.
"""

import logging

from odoo import _

_logger = logging.getLogger(__name__)


# ── Transition map ────────────────────────────────────────────
# (old_status, new_status) → method name
# Methods return True on success, False if manual intervention needed.
TRANSITION_MAP = {
    ('authorized', 'paid'): '_transition_to_paid',
    ('pending', 'paid'): '_transition_to_paid',
    ('partially_paid', 'paid'): '_transition_to_paid',
    ('pending', 'partially_paid'): '_transition_to_partially_paid',
    ('authorized', 'partially_paid'): '_transition_to_partially_paid',
    ('pending', 'voided'): '_transition_to_voided',
    ('authorized', 'voided'): '_transition_to_voided',
    ('pending', 'expired'): '_transition_to_voided',
    ('authorized', 'expired'): '_transition_to_voided',
    # Refund transitions are handled by refund_sync — we just update status
    ('paid', 'partially_refunded'): '_transition_refund_status_only',
    ('paid', 'refunded'): '_transition_refund_status_only',
    ('partially_refunded', 'refunded'): '_transition_refund_status_only',
}


class PaymentStatusHandler:
    """Handles payment status transitions from Shopify to Odoo."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend

    def handle_status_change(self, order_binding, old_status, new_status):
        """Process a financial status change on a Shopify order binding.

        Args:
            order_binding: shopify.order.binding record
            old_status: previous financial status (lowercase)
            new_status: new financial status (lowercase)

        Returns:
            True if handled automatically, False if manual action needed.
        """
        if old_status == new_status:
            return True

        if not self.backend.auto_handle_payment_transitions:
            _logger.info(
                "Payment transition handling disabled for backend %s. "
                "Skipping %s → %s for order %s",
                self.backend.id, old_status, new_status,
                order_binding.shopify_order_name,
            )
            # Still update the status field
            self._update_status_fields(order_binding, new_status)
            return True

        transition_key = (old_status, new_status)
        method_name = TRANSITION_MAP.get(transition_key)

        if method_name:
            _logger.info(
                "Processing payment transition %s → %s for order %s",
                old_status, new_status, order_binding.shopify_order_name,
            )
            handler = getattr(self, method_name)
            result = handler(order_binding, old_status, new_status)
            self._update_status_fields(order_binding, new_status)
            return result
        else:
            _logger.warning(
                "Unknown payment transition %s → %s for order %s",
                old_status, new_status, order_binding.shopify_order_name,
            )
            self._update_status_fields(order_binding, new_status)
            return True

    def _update_status_fields(self, order_binding, new_status):
        """Update the financial status on binding and sale order."""
        order_binding.write({'shopify_financial_status': new_status})
        if order_binding.odoo_id:
            order_binding.odoo_id.with_context(
                shopify_no_auto_export=True,
            ).write({'shopify_financial_status': new_status})

    # ── Transition handlers ────────────────────────────────

    def _transition_to_paid(self, binding, old_status, new_status):
        """Handle transition to 'paid' — post invoice and register payment."""
        order = binding.odoo_id
        if not order:
            return False

        # All accounting actions must suppress reverse-sync to avoid a loop:
        # Shopify→paid → post invoice → action_post override → orderMarkAsPaid → loop
        ctx = {'shopify_no_auto_export': True}

        # Find draft invoice → post it
        draft_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'draft'
        )
        posted_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )

        if draft_invoices:
            try:
                draft_invoices[0].with_context(**ctx).action_post()
                _logger.info(
                    "Posted draft invoice %s for order %s (Shopify payment captured)",
                    draft_invoices[0].name, order.name,
                )
                return True
            except Exception as e:
                _logger.warning(
                    "Failed to post invoice for order %s: %s", order.name, e,
                )
                self._schedule_activity(
                    order,
                    _("Payment captured on Shopify but invoice could not be posted: %s") % e,
                )
                return False

        if posted_invoices:
            _logger.info(
                "Invoice already posted for order %s — no action needed", order.name,
            )
            return True

        # No invoice exists — try to create one
        if order.state == 'draft':
            try:
                order.with_context(**ctx).action_confirm()
            except Exception as e:
                _logger.warning("Could not confirm order %s: %s", order.name, e)
                self._schedule_activity(
                    order,
                    _("Payment received on Shopify but order could not be confirmed: %s") % e,
                )
                return False

        if order.state in ('sale', 'done'):
            try:
                with self.env.cr.savepoint():
                    invoice = order.with_context(**ctx)._create_invoices()
                    if not invoice:
                        _logger.warning(
                            "No invoiceable lines for order %s — "
                            "invoice not created",
                            order.name,
                        )
                        return False
                    invoice.with_context(**ctx).action_post()
                _logger.info(
                    "Created and posted invoice %s for order %s",
                    invoice.name, order.name,
                )
                return True
            except Exception as e:
                _logger.warning(
                    "Failed to create invoice for order %s: %s", order.name, e,
                )
                self._schedule_activity(
                    order,
                    _("Payment received on Shopify but invoice creation failed: %s") % e,
                )
                return False

        self._schedule_activity(
            order,
            _("Payment captured on Shopify (status: %s) but order is in state '%s'. "
              "Manual invoice creation may be required.") % (new_status, order.state),
        )
        return False

    def _transition_to_partially_paid(self, binding, old_status, new_status):
        """Handle transition to 'partially_paid'.

        Post the invoice if in draft (so partial payment can be registered),
        but don't auto-register the payment — the amount is unknown from
        the status change alone.
        """
        order = binding.odoo_id
        if not order:
            return False

        # Suppress reverse-sync to avoid a loop (same as _transition_to_paid)
        ctx = {'shopify_no_auto_export': True}

        draft_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'draft'
        )

        if draft_invoices:
            try:
                draft_invoices[0].with_context(**ctx).action_post()
                _logger.info(
                    "Posted invoice %s for partially paid order %s",
                    draft_invoices[0].name, order.name,
                )
            except Exception as e:
                _logger.warning(
                    "Failed to post invoice for partially paid order %s: %s",
                    order.name, e,
                )

        self._schedule_activity(
            order,
            _("Order partially paid on Shopify. Please register the partial "
              "payment on the invoice."),
        )
        return True

    def _transition_to_voided(self, binding, old_status, new_status):
        """Handle transition to 'voided' or 'expired'."""
        order = binding.odoo_id
        if not order:
            return False

        # Suppress reverse-sync for all accounting operations
        ctx = {'shopify_no_auto_export': True}

        # Cancel draft invoices safely
        draft_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'draft'
        )
        if draft_invoices:
            try:
                draft_invoices.with_context(**ctx).button_cancel()
                _logger.info(
                    "Cancelled draft invoice(s) for voided order %s", order.name,
                )
            except Exception as e:
                _logger.warning(
                    "Failed to cancel draft invoice for order %s: %s", order.name, e,
                )

        # If there's a posted invoice, we CANNOT auto-cancel — need manual credit note
        posted_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )
        if posted_invoices:
            self._schedule_activity(
                order,
                _("Payment voided/expired on Shopify but invoice %s is already posted. "
                  "A manual credit note is required.") % posted_invoices[0].name,
            )
            return False

        # Cancel the SO if not yet delivered
        if order.state in ('draft', 'sent'):
            try:
                order.action_cancel()
                _logger.info("Cancelled order %s after Shopify void", order.name)
            except Exception as e:
                _logger.warning("Failed to cancel order %s after Shopify void: %s", order.name, e)
        elif order.state == 'sale':
            # Check if anything shipped
            done_pickings = order.picking_ids.filtered(lambda p: p.state == 'done')
            if not done_pickings:
                try:
                    order.with_context(disable_cancel_warning=True).action_cancel()
                    _logger.info("Cancelled unshipped order %s after Shopify void", order.name)
                except Exception as e:
                    _logger.warning("Failed to cancel order %s: %s", order.name, e)
                    self._schedule_activity(
                        order,
                        _("Payment voided on Shopify. Order could not be auto-cancelled. "
                          "Please review."),
                    )

        return True

    def _transition_refund_status_only(self, binding, old_status, new_status):
        """Refund transitions — just update status. Actual credit notes
        are handled by RefundSync which has line-level detail."""
        _logger.info(
            "Refund status transition %s → %s for order %s (handled by RefundSync)",
            old_status, new_status, binding.shopify_order_name,
        )
        return True

    def _schedule_activity(self, order, note):
        """Schedule a to-do activity on the sale order for manual review."""
        try:
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("Shopify Payment Status Change"),
                note=note,
            )
        except Exception as e:
            _logger.warning("Could not schedule activity on order %s: %s", order.name, e)
