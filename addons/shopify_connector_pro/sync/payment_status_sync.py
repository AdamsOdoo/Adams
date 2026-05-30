# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Payment status transition handler for Shopify → Odoo.

Handles financial status changes received via webhooks or periodic imports
and applies the corresponding accounting actions in Odoo.
"""

import logging

from odoo import _, fields

from .accounting import validate_order_income_accounts, schedule_account_activity

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

        invoice = False

        if draft_invoices:
            try:
                draft_invoices[0].with_context(**ctx).action_post()
                invoice = draft_invoices[0]
                _logger.info(
                    "Posted draft invoice %s for order %s (Shopify payment captured)",
                    invoice.name, order.name,
                )
            except Exception as e:
                _logger.warning(
                    "Failed to post invoice for order %s: %s", order.name, e,
                )
                self._schedule_activity(
                    order,
                    _("Payment captured on Shopify but invoice could not be posted: %s") % e,
                )
                return False

        elif posted_invoices:
            invoice = posted_invoices[0]
            _logger.info(
                "Invoice already posted for order %s — proceeding to payment registration",
                order.name,
            )

        else:
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
                # Pre-validate income accounts before attempting invoice
                # creation.  Uses the shared helper so every path that
                # builds account.move.line records applies the same check.
                missing, _fallback = validate_order_income_accounts(
                    self.env, order,
                )
                if missing:
                    schedule_account_activity(
                        order,
                        summary="Shopify payment received — invoice skipped",
                        products=missing,
                    )
                    return False
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
                except Exception as e:
                    _logger.warning(
                        "Failed to create invoice for order %s: %s", order.name, e,
                    )
                    self._schedule_activity(
                        order,
                        _("Payment received on Shopify but invoice creation failed: %s") % e,
                    )
                    return False
            else:
                self._schedule_activity(
                    order,
                    _("Payment captured on Shopify (status: %s) but order is in state '%s'. "
                      "Manual invoice creation may be required.") % (new_status, order.state),
                )
                return False

        # Register payment on the posted invoice
        if invoice and invoice.state == 'posted' and invoice.amount_residual > 0:
            self._register_payment(invoice, binding)

        return True

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

    # ── Payment registration ─────────────────────────────

    def _register_payment(self, invoice, order_binding):
        """Register a payment on the invoice using gateway journal mapping.

        Idempotent: skips if a payment with the same reference already exists.
        Uses shopify.payment.gateway to resolve the journal, falling back to
        the company's default bank journal.
        """
        ctx = {'shopify_no_auto_export': True}
        # Key the memo on the Shopify GID (globally unique across all
        # stores) rather than the human-readable order name (#1001)
        # which is only sequential within a single store.
        shopify_gid = order_binding.shopify_id
        if not shopify_gid:
            _logger.error(
                "Cannot register payment: binding %s has no shopify_id",
                order_binding.id,
            )
            return False
        memo = "SHOPIFY-%s" % shopify_gid

        # ── Primary idempotency: structural link on the binding ──
        # Each binding tracks its own payment_id, so two backends in
        # the same company with the same order name (#1001) never collide.
        if order_binding.payment_id and order_binding.payment_id.state != 'cancelled':
            _logger.info(
                "Payment already registered for binding %s (payment %s)",
                order_binding.shopify_order_name, order_binding.payment_id.name,
            )
            return True

        # ── Secondary idempotency: memo-based guard (crash recovery) ──
        # Catches edge cases where payment exists but the payment_id
        # write-back was lost (e.g. crash between payment creation and
        # binding update).  Because the memo now contains the Shopify
        # GID — globally unique across all stores — company_id is the
        # only additional scope needed; no partner or journal scoping.
        existing = self.env['account.payment'].search([
            ('memo', '=', memo),
            ('state', '!=', 'cancelled'),
            ('company_id', '=', self.backend.company_id.id),
        ], limit=1)
        if existing:
            # Repair the structural link while we're here.
            # Wrapped in a savepoint so a DB-level failure cannot
            # poison the cursor — the dedup result is still valid.
            try:
                with self.env.cr.savepoint():
                    order_binding.payment_id = existing
            except Exception:
                _logger.warning(
                    "Could not repair payment_id link on binding %s",
                    order_binding.id, exc_info=True,
                )
            _logger.info(
                "Payment already registered for order %s (memo=%s, "
                "repaired binding link)",
                order_binding.shopify_order_name, memo,
            )
            return True

        journal = self._resolve_payment_journal(order_binding)
        if not journal:
            self._schedule_activity(
                order_binding.odoo_id,
                _("Payment captured on Shopify but no payment journal "
                  "could be determined. Please register payment manually "
                  "or configure a Shopify Payment Gateway mapping."),
            )
            return False

        amount = invoice.amount_residual
        if amount <= 0:
            _logger.info("Invoice %s already fully paid", invoice.name)
            return True

        # Step 1: Create and post the payment in a savepoint.
        # Kept separate from reconciliation so that a reconciliation
        # failure does not roll back the payment itself.
        try:
            with self.env.cr.savepoint():
                payment = self.env['account.payment'].with_context(**ctx).create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice.partner_id.id,
                    'amount': amount,
                    'journal_id': journal.id,
                    'memo': memo,
                    'date': invoice.date or fields.Date.today(),
                    'currency_id': invoice.currency_id.id,
                })
                payment.with_context(**ctx).action_post()
                # Write-back INSIDE the savepoint so that if the
                # savepoint rolls back, the binding link is also undone.
                order_binding.payment_id = payment
        except Exception as e:
            _logger.warning(
                "Failed to create/post payment for order %s: %s",
                order_binding.shopify_order_name, e,
            )
            self._schedule_activity(
                order_binding.odoo_id,
                _("Payment captured on Shopify but auto-registration "
                  "failed: %s. Please register payment manually.") % e,
            )
            return False

        # Step 2: Reconcile payment with invoice (best-effort).
        # If reconciliation fails the payment still exists; the user
        # can reconcile manually from the invoice.
        try:
            if payment.move_id:
                receivable_lines = (
                    payment.move_id.line_ids + invoice.line_ids
                ).filtered(
                    lambda l: l.account_type == 'asset_receivable'
                    and not l.reconciled
                )
                if receivable_lines:
                    receivable_lines.reconcile()
        except Exception as e:
            _logger.warning(
                "Payment created for order %s but reconciliation "
                "failed: %s — manual reconciliation required.",
                order_binding.shopify_order_name, e,
            )

        _logger.info(
            "Payment registered for order %s: %s %s (journal: %s)",
            order_binding.shopify_order_name, amount,
            invoice.currency_id.name, journal.name,
        )
        return True

    def _resolve_payment_journal(self, order_binding):
        """Find the payment journal via gateway mapping or fallback.

        Resolution order:
        1. Fetch gateway name from Shopify transactions
        2. Match shopify.payment.gateway by name or code → journal_id
        3. Fallback: company's default bank journal
        """
        company = self.backend.company_id
        gateway_name = self._get_transaction_gateway(order_binding)

        if gateway_name:
            gateway = self.env['shopify.payment.gateway'].search([
                '|', ('name', '=ilike', gateway_name),
                ('code', '=ilike', gateway_name),
                '|', ('company_id', '=', company.id),
                ('company_id', '=', False),
                ('active', '=', True),
            ], limit=1)
            if gateway and gateway.journal_id:
                return gateway.journal_id

        # Fallback: default bank journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', company.id),
        ], limit=1)
        if journal:
            _logger.info(
                "No gateway mapping for '%s' — using default bank journal %s",
                gateway_name or 'unknown', journal.name,
            )
        return journal

    def _get_transaction_gateway(self, order_binding):
        """Fetch the payment gateway name from Shopify order transactions.

        Also records transactions in shopify.order.transaction for audit.
        Returns the gateway name of the first successful sale/capture, or None.
        """
        if not order_binding.shopify_id:
            return None
        try:
            client = self.backend._make_api_client()
            query = """
            query GetOrderTransactions($id: ID!) {
              order(id: $id) {
                transactions(first: 20) {
                  id
                  gateway
                  kind
                  status
                  amountSet {
                    shopMoney { amount currencyCode }
                  }
                  processedAt
                }
              }
            }
            """
            body = client.execute(
                query, {'id': order_binding.shopify_id}, estimated_cost=5,
            )
            transactions = (
                body.get('data', {}).get('order', {}).get('transactions', [])
            )

            gateway_name = None
            for txn in transactions:
                kind = (txn.get('kind') or '').lower()
                status = (txn.get('status') or '').lower()
                txn_id = txn.get('id', '')

                # Record every transaction for audit (idempotent)
                if txn_id:
                    existing_txn = self.env['shopify.order.transaction'].search([
                        ('shopify_transaction_id', '=', txn_id),
                        ('order_binding_id', '=', order_binding.id),
                    ], limit=1)
                    if not existing_txn:
                        money = txn.get('amountSet', {}).get('shopMoney', {})
                        self.env['shopify.order.transaction'].create({
                            'order_binding_id': order_binding.id,
                            'shopify_transaction_id': txn_id,
                            'gateway': txn.get('gateway', ''),
                            'kind': kind if kind in ('sale', 'capture', 'authorization', 'refund', 'void') else False,
                            'status': status if status in ('success', 'pending', 'failure', 'error') else False,
                            'amount': float(money.get('amount', 0)),
                            'currency_code': money.get('currencyCode', ''),
                            'processed_at': txn.get('processedAt'),
                        })

                # Use the first successful sale/capture for gateway
                if not gateway_name and kind in ('sale', 'capture') and status == 'success':
                    gateway_name = txn.get('gateway', '')

            return gateway_name
        except Exception as e:
            _logger.warning(
                "Could not fetch transactions for order %s: %s",
                order_binding.shopify_order_name, e,
            )
            return None

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
