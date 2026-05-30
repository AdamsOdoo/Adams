# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from ..shopify_api.queries.refund import FETCH_REFUNDS
from .accounting import validate_order_income_accounts, schedule_account_activity

_logger = logging.getLogger(__name__)


class RefundImporter:
    """Import refunds from Shopify and create credit notes in Odoo."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.client = backend._make_api_client()

    def import_refunds_for_order(self, order_binding):
        """Fetch and import all refunds for a given order binding."""
        if not order_binding.shopify_id:
            return 0, 0, 0

        try:
            body = self.client.execute(
                FETCH_REFUNDS,
                {'orderId': order_binding.shopify_id},
                estimated_cost=10,
            )
        except Exception as e:
            _logger.warning("Failed to fetch refunds for order %s: %s",
                            order_binding.shopify_id, e)
            return 0, 1, 0

        refunds = body.get('data', {}).get('order', {}).get('refunds', [])
        success = errors = skipped = 0

        for refund_data in refunds:
            shopify_refund_id = refund_data.get('id', '')
            existing = self.env['shopify.refund.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_refund_id),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            try:
                self._import_one_refund(refund_data, order_binding)
                success += 1
            except Exception as e:
                _logger.warning("Failed to import refund %s: %s", shopify_refund_id, e)
                errors += 1

        return success, errors, skipped

    def _money(self, price_set):
        """Extract amount from a priceSet respecting backend import_currency_mode.
        Mirrors order_sync._get_money_amount so refund totals match the order/
        invoice currency when the backend is in 'presentment' mode."""
        if not price_set:
            return 0.0, ''
        if self.backend.import_currency_mode == 'presentment':
            money = price_set.get('presentmentMoney') or price_set.get('shopMoney') or {}
        else:
            money = price_set.get('shopMoney') or {}
        return float(money.get('amount', 0) or 0), money.get('currencyCode', '') or ''

    def _import_one_refund(self, refund_data, order_binding):
        """Create a credit note from a Shopify refund."""
        shopify_refund_id = refund_data.get('id')
        refund_amount, currency_code = self._money(refund_data.get('totalRefundedSet'))

        # Parse refund lines
        refund_lines = []
        for edge in (refund_data.get('refundLineItems') or {}).get('edges', []):
            node = edge.get('node') or {}
            # dict.get(k, {}) returns {} only when k is absent, NOT when the
            # value is explicitly null. Shopify returns null for deleted
            # variants / lineItems, so guard every nested hop with `or {}`.
            line_item = node.get('lineItem') or {}
            variant = line_item.get('variant') or {}
            subtotal_amount, _ = self._money(node.get('subtotalSet'))

            product = None
            variant_id = variant.get('id', '')
            if variant_id:
                vb = self.env['shopify.variant.binding'].search([
                    ('backend_id', '=', self.backend.id),
                    ('shopify_id', '=', variant_id),
                ], limit=1)
                if vb:
                    product = vb.odoo_id

            restock = (node.get('restockType', 'NO_RESTOCK') or 'NO_RESTOCK').lower()
            if restock not in ('no_restock', 'cancel', 'return'):
                restock = 'no_restock'

            refund_lines.append({
                'product_id': product.id if product else False,
                'quantity': node.get('quantity', 0),
                'amount': subtotal_amount,
                'restock_type': restock,
            })

        # Create a credit note for the actual refund amount.  Previous
        # implementation used reverse_moves() which always reversed the FULL
        # invoice — breaking partial refunds and double-crediting when
        # multiple refunds exist on the same order (BUG-R1/R2).
        order = order_binding.odoo_id
        credit_note = None
        ctx = {'shopify_no_auto_export': True}
        if order:
            credit_note = self._create_refund_credit_note(
                order, refund_data, refund_lines, refund_amount, ctx,
            )

        binding_vals = {
            'backend_id': self.backend.id,
            'shopify_id': shopify_refund_id,
            'order_binding_id': order_binding.id,
            'shopify_order_id': order_binding.shopify_id,
            'refund_note': refund_data.get('note') or '',
            'refund_amount': refund_amount,
            'currency_code': currency_code,
            'sync_checksum': shopify_refund_id,
            'last_sync_date': fields.Datetime.now(),
        }
        if credit_note:
            binding_vals['odoo_id'] = credit_note.id
            binding_vals['sync_status'] = 'synced'
        else:
            # Record the binding with error state so it is not retried
            # blindly on the next sync (the existing-binding check at
            # import_refunds_for_order skips it).  The merchant can
            # fix accounting setup and use action_retry_sync.
            binding_vals['sync_status'] = 'error'
            binding_vals['sync_error'] = (
                'Credit note could not be created. Check the scheduled '
                'activity on order %s for details.' % (
                    order_binding.odoo_id.name if order_binding.odoo_id else
                    order_binding.shopify_order_name
                )
            )

        refund_binding = self.env['shopify.refund.binding'].create(binding_vals)

        for line in refund_lines:
            line['refund_binding_id'] = refund_binding.id
            self.env['shopify.refund.line'].create(line)

        return refund_binding

    def _create_refund_credit_note(self, order, refund_data, refund_lines,
                                   refund_amount, ctx):
        """Create a credit note matching the actual Shopify refund amount.

        Creates an ``account.move`` with ``move_type='out_refund'`` directly
        instead of using ``reverse_moves()`` which would always reverse the
        full invoice amount — causing over-crediting on partial refunds and
        when multiple refunds target the same order.

        Mirrors the defensive pattern from ``OrderImporter._auto_create_invoice``:
        - Pre-validates income accounts on products before building lines
        - Wraps create+post in a savepoint to isolate SQL failures
        - Schedules a visible activity on the sale order when creation fails
        """
        # Prefer the journal from an existing posted invoice; fall back to
        # any sales journal in the backend's company.
        posted_invoices = order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
        )
        if posted_invoices:
            journal = posted_invoices[0].journal_id
        else:
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.backend.company_id.id),
            ], limit=1)

        if not journal:
            msg = (
                "No sales journal found — cannot create credit note for "
                "refund %s" % refund_data.get('id')
            )
            _logger.warning("Order %s: %s", order.name, msg)
            order.activity_schedule(
                'mail.mail_activity_data_warning',
                summary="Shopify refund credit note failed",
                note=msg,
            )
            return None

        # ── Account pre-validation (shared helper) ─────────────────
        # Uses the centralised validate_order_income_accounts() which
        # resolves the same fallback chain: journal default → posted
        # invoice lines → any income account in the company.
        missing_accounts, journal_default_account = \
            validate_order_income_accounts(self.env, order, journal=journal)

        if missing_accounts and not journal_default_account:
            schedule_account_activity(
                order,
                summary="Shopify refund credit note skipped",
                products=missing_accounts,
            )
            return None

        # Build credit-note lines from the Shopify refund line items.
        invoice_line_ids = []
        for rl in refund_lines:
            qty = rl.get('quantity') or 0
            amt = rl.get('amount') or 0
            if qty and amt:
                line_vals = {
                    'quantity': qty,
                    'price_unit': amt / qty,
                }
                if rl.get('product_id'):
                    product = self.env['product.product'].browse(rl['product_id'])
                    line_vals['product_id'] = product.id
                    # Resolve income account: product → category → journal default
                    accounts = product.product_tmpl_id.get_product_accounts(
                        fiscal_pos=order.fiscal_position_id,
                    )
                    account = accounts.get('income') or journal_default_account
                    if account:
                        line_vals['account_id'] = account.id
                else:
                    line_vals['name'] = 'Shopify Refund Item'
                    # Non-product lines must always have an explicit account
                    if journal_default_account:
                        line_vals['account_id'] = journal_default_account.id
                    else:
                        # Should not reach here (pre-validation catches it),
                        # but guard defensively.
                        continue
                invoice_line_ids.append((0, 0, line_vals))

        # Fallback: single line for the total when no itemised lines exist
        # (e.g. manual / shipping-only refund).
        if not invoice_line_ids and refund_amount:
            if not journal_default_account:
                msg = (
                    "Refund credit note skipped: no income account could be "
                    "resolved (journal has no default account, no posted "
                    "invoice lines, and no income account in the chart of "
                    "accounts). Refund %s" % refund_data.get('id')
                )
                _logger.warning("Order %s: %s", order.name, msg)
                order.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary="Shopify refund credit note failed",
                    note=msg,
                )
                return None
            fallback_vals = {
                'name': refund_data.get('note') or 'Shopify Refund',
                'quantity': 1,
                'price_unit': refund_amount,
                'account_id': journal_default_account.id,
            }
            invoice_line_ids.append((0, 0, fallback_vals))

        if not invoice_line_ids:
            _logger.warning(
                "No refund lines and zero amount — skipping credit note "
                "for refund %s", refund_data.get('id'),
            )
            return None

        try:
            with self.env.cr.savepoint():
                credit_note = self.env['account.move'].with_context(**ctx).create({
                    'move_type': 'out_refund',
                    'partner_id': order.partner_id.id,
                    'journal_id': journal.id,
                    'invoice_origin': order.name,
                    'ref': refund_data.get('note') or 'Shopify Refund',
                    'invoice_line_ids': invoice_line_ids,
                })
                credit_note.with_context(**ctx).action_post()
                return credit_note
        except Exception as e:
            _logger.warning(
                "Could not create credit note for refund %s "
                "(products: %s): %s. Check income account, fiscal "
                "position, and company chart of accounts.",
                refund_data.get('id'),
                ', '.join(
                    self.env['product.product'].browse(
                        rl['product_id']
                    ).display_name
                    for rl in refund_lines if rl.get('product_id')
                ) or 'none',
                e,
            )
            order.activity_schedule(
                'mail.mail_activity_data_warning',
                summary="Shopify refund credit note failed",
                note="Credit note creation failed for refund %s: %s" % (
                    refund_data.get('id'), e,
                ),
            )
            return None


class RefundSync:
    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = RefundImporter(env, backend)

    def import_refunds(self):
        """Import refunds for orders with refund status."""
        order_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', '=', 'synced'),
            ('shopify_financial_status', 'in', ['refunded', 'partially_refunded']),
        ])
        total_success = total_errors = total_skipped = 0
        for ob in order_bindings:
            s, e, sk = self.importer.import_refunds_for_order(ob)
            total_success += s
            total_errors += e
            total_skipped += sk
        return total_success, total_errors, total_skipped
