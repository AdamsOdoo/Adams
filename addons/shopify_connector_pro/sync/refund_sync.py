# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

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
                # One savepoint per refund (AUD-021): the posted credit
                # note and its binding are atomic — a failure between
                # them must not leave an orphaned credit note that
                # duplicates on the next sync.
                with self.env.cr.savepoint():
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
            tax_amount, _ = self._money(node.get('totalTaxSet'))

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
                'tax_amount': tax_amount,
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
            line_vals = dict(line)
            line_vals['refund_binding_id'] = refund_binding.id
            # tax_amount is used by _create_refund_credit_note but is
            # not a field on shopify.refund.line
            line_vals.pop('tax_amount', None)
            self.env['shopify.refund.line'].create(line_vals)

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
        # ── Refund-GID recovery guard (AUD-021) ────────────────
        # The binding-existence check is the primary dedup; this stamp
        # search is the recovery net (mirrors the payment memo
        # pattern): if a credit note for this exact Shopify refund
        # already exists — e.g. the binding was lost — reuse it,
        # never book the refund twice.
        refund_gid = refund_data.get('id')
        if refund_gid:
            existing_cn = self.env['account.move'].search([
                ('shopify_refund_gid', '=', refund_gid),
                ('move_type', '=', 'out_refund'),
                ('state', '!=', 'cancel'),
                ('company_id', '=', self.backend.company_id.id),
            ], limit=1)
            if existing_cn:
                _logger.info(
                    "Refund %s already booked as credit note %s — "
                    "reusing it (recovery guard).",
                    refund_gid, existing_cn.name,
                )
                return existing_cn

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

        # ── Build credit-note lines from refund line items ─────────
        invoice_line_ids = []
        tax_fallback_activities = []

        # Cache the posted invoice for tax mapping
        posted_invoices = order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
        )

        for rl in refund_lines:
            qty = rl.get('quantity') or 0
            amt = rl.get('amount') or 0
            tax_amt = rl.get('tax_amount') or 0
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

                    # Tax strategy (a): carry tax_ids from original invoice line
                    original_tax_ids = self._find_original_tax_ids(
                        posted_invoices, product, order,
                    )
                    if original_tax_ids is not None:
                        line_vals['tax_ids'] = [(6, 0, original_tax_ids.ids)]
                    elif tax_amt:
                        # Fallback (b): include tax in amount, flag for review
                        line_vals['price_unit'] = (amt + tax_amt) / qty
                        line_vals['tax_ids'] = [(5,)]  # clear auto-detected taxes
                        tax_fallback_activities.append(
                            product.display_name
                        )
                else:
                    line_vals['name'] = 'Shopify Refund Item'
                    if journal_default_account:
                        line_vals['account_id'] = journal_default_account.id
                    else:
                        # Dropped line is recovered untaxed by the
                        # auto-balance delta below — log it so the gross
                        # adjustment is explainable (AUD-023).
                        _logger.warning(
                            "Refund %s on order %s: non-product line "
                            "(%.2f) dropped — no journal default "
                            "account; amount recovered via the "
                            "balancing adjustment line.",
                            refund_data.get('id'), order.name, amt,
                        )
                        continue
                    # Non-product line: include tax in amount if present
                    if tax_amt:
                        line_vals['price_unit'] = (amt + tax_amt) / qty
                        line_vals['tax_ids'] = [(5,)]
                invoice_line_ids.append((0, 0, line_vals))

        # ── Shipping refund lines ─────────────────────────────
        shipping_product = (
            self.backend.shipping_product_id
            or self.env['product.product'].search(
                [('default_code', '=', 'SHOPIFY-SHIPPING')], limit=1,
            )
        )
        for edge in (refund_data.get('refundShippingLines') or {}).get('edges', []):
            node = edge.get('node') or {}
            ship_subtotal, _ = self._money(node.get('subtotalAmountSet'))
            ship_tax, _ = self._money(node.get('taxAmountSet'))
            if ship_subtotal or ship_tax:
                ship_line = {
                    'quantity': 1,
                    'price_unit': ship_subtotal,
                    'name': 'Shipping Refund',
                }
                ship_account = journal_default_account
                if shipping_product:
                    ship_line['product_id'] = shipping_product.id
                    # Resolve income account like product lines
                    # (AUD-023): product → category → journal default
                    ship_accounts = (
                        shipping_product.product_tmpl_id
                        .get_product_accounts(
                            fiscal_pos=order.fiscal_position_id,
                        )
                    )
                    ship_account = (
                        ship_accounts.get('income') or ship_account
                    )
                    # Tax from original invoice shipping line
                    ship_tax_ids = self._find_original_tax_ids(
                        posted_invoices, shipping_product, order,
                    )
                    if ship_tax_ids is not None:
                        ship_line['tax_ids'] = [(6, 0, ship_tax_ids.ids)]
                    elif ship_tax:
                        ship_line['price_unit'] = ship_subtotal + ship_tax
                        ship_line['tax_ids'] = [(5,)]
                        tax_fallback_activities.append('Shipping')
                if ship_account:
                    ship_line['account_id'] = ship_account.id
                invoice_line_ids.append((0, 0, ship_line))

        # ── Order adjustments (rounding / discrepancies) ──────
        for adj in refund_data.get('orderAdjustments') or []:
            adj_amount, _ = self._money(adj.get('amountSet'))
            adj_tax, _ = self._money(adj.get('taxAmountSet'))
            total_adj = adj_amount + adj_tax
            if abs(total_adj) > 0.001:
                reason = adj.get('reason') or 'rounding'
                adj_line = {
                    'name': 'Shopify refund adjustment (%s)' % reason,
                    'quantity': 1,
                    'price_unit': total_adj,
                    'tax_ids': [(5,)],
                }
                if journal_default_account:
                    adj_line['account_id'] = journal_default_account.id
                invoice_line_ids.append((0, 0, adj_line))

        # ── Fallback: single line when no itemised lines exist ─
        if not invoice_line_ids and refund_amount:
            if not journal_default_account:
                msg = (
                    "Refund credit note skipped: no income account could be "
                    "resolved (journal has no default account, no posted "
                    "invoice lines, and no income account in the chart of "
                    "accounts). Refund %s on order %s." % (
                        refund_data.get('id'), order.name,
                    )
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
                'tax_ids': [(5,)],
            }
            invoice_line_ids.append((0, 0, fallback_vals))
            tax_fallback_activities.append('(lump-sum refund)')

        if not invoice_line_ids:
            _logger.warning(
                "No refund lines and zero amount — skipping credit note "
                "for refund %s", refund_data.get('id'),
            )
            return None

        # ── Credit-note currency (AUD-019) ─────────────────────
        # The credit note must reconcile against the original invoice, so
        # it carries the invoice currency (order currency when no invoice
        # was posted) — never the company currency by default. A refund
        # reported in a different currency is not converted here: it is
        # degraded visibly and left retryable after review.
        cn_currency = (
            posted_invoices[0].currency_id if posted_invoices
            else order.currency_id
        )
        _, refund_ccy = self._money(refund_data.get('totalRefundedSet'))
        if refund_ccy and refund_ccy != cn_currency.name:
            msg = (
                "Shopify refund %s is in %s but the order/invoice is in %s. "
                "The credit note was NOT created. Review the refund in "
                "Shopify and the invoice currency in Odoo, then use Retry "
                "Sync on the refund binding to create it." % (
                    refund_data.get('id'), refund_ccy, cn_currency.name,
                )
            )
            _logger.warning("Order %s: %s", order.name, msg)
            order.activity_schedule(
                'mail.mail_activity_data_warning',
                summary="Shopify refund credit note failed",
                note=msg,
            )
            return None

        # ── Cumulative over-refund guard (AUD-022) ─────────────
        # Shopify itself caps refunds at the captured amount, so a
        # breach here means an Odoo-side mismatch (partial/edited
        # invoice, duplicate payloads). Never post credit notes beyond
        # the posted invoice total: degrade visibly, leave retryable.
        if posted_invoices:
            tolerance = 2 * (cn_currency.rounding or 0.01)
            invoiced_total = sum(posted_invoices.mapped('amount_total'))
            prior_credit_notes = self.env['account.move'].search([
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('company_id', '=', self.backend.company_id.id),
                ('shopify_refund_gid', '!=', False),
                ('invoice_origin', '=', order.name),
            ])
            cumulative = (
                sum(prior_credit_notes.mapped('amount_total'))
                + refund_amount
            )
            if cumulative > invoiced_total + tolerance:
                msg = (
                    "Shopify refund %s of %s %.2f would bring the total "
                    "refunded for order %s to %.2f, exceeding the "
                    "invoiced total of %.2f. The credit note was NOT "
                    "created. Compare the Shopify refunds with the "
                    "posted invoice(s) and credit note(s); after "
                    "correcting the records, use Retry Sync on the "
                    "refund binding." % (
                        refund_data.get('id'), cn_currency.name,
                        refund_amount, order.name, cumulative,
                        invoiced_total,
                    )
                )
                _logger.warning("Order %s: %s", order.name, msg)
                order.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary="Shopify refund exceeds invoiced amount",
                    note=msg,
                )
                return None

        try:
            with self.env.cr.savepoint():
                credit_note = self.env['account.move'].with_context(**ctx).create({
                    'move_type': 'out_refund',
                    'partner_id': order.partner_id.id,
                    'journal_id': journal.id,
                    'currency_id': cn_currency.id,
                    'invoice_origin': order.name,
                    'ref': refund_data.get('note') or 'Shopify Refund',
                    'shopify_refund_gid': refund_gid,
                    'invoice_line_ids': invoice_line_ids,
                })

                # ── Auto-balance to totalRefundedSet ──────────
                # Shopify is the source of truth for the actual money
                # refunded.  Odoo's tax recomputation may differ by a
                # cent or two due to per-unit rounding.  Force an exact
                # match so the receivable always reconciles.
                delta = refund_amount - credit_note.amount_total
                if abs(delta) > 0.001:
                    credit_note.write({
                        'invoice_line_ids': [(0, 0, {
                            'name': 'Shopify refund rounding adjustment',
                            'quantity': 1,
                            'price_unit': delta,
                            'account_id': (
                                journal_default_account.id
                                if journal_default_account
                                else journal.default_account_id.id
                            ),
                            'tax_ids': [(5,)],
                        })],
                    })
                    if abs(delta) > 0.05:
                        order.activity_schedule(
                            'mail.mail_activity_data_todo',
                            summary="Shopify refund rounding adjustment",
                            note=(
                                "Credit note for refund %s on order %s "
                                "includes a %s %.2f rounding adjustment to "
                                "match the actual amount refunded on Shopify. "
                                "This exceeds normal rounding — verify against "
                                "the original invoice." % (
                                    refund_data.get('id'), order.name,
                                    credit_note.currency_id.symbol, abs(delta),
                                )
                            ),
                        )

                credit_note.with_context(**ctx).action_post()

                # Schedule activity for any tax-fallback lines
                if tax_fallback_activities:
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary="Shopify refund — verify tax reversal",
                        note=(
                            "Credit note %s for refund %s on order %s: tax "
                            "reversal could not be determined from the original "
                            "invoice for: %s. Tax amount was included in the "
                            "line total instead. Verify tax treatment against "
                            "the original invoice." % (
                                credit_note.name, refund_data.get('id'),
                                order.name,
                                ', '.join(tax_fallback_activities),
                            )
                        ),
                    )

                return credit_note
        except Exception as e:
            _logger.warning(
                "Could not create credit note for refund %s on order %s "
                "(products: %s): %s. Check income account, fiscal "
                "position, and company chart of accounts.",
                refund_data.get('id'), order.name,
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
                note="Credit note creation failed for refund %s on "
                     "order %s: %s" % (
                         refund_data.get('id'), order.name, e,
                     ),
            )
            return None

    def _find_original_tax_ids(self, posted_invoices, product, order):
        """Find tax_ids from the original posted invoice line for a product.

        Returns:
            - recordset of account.tax if a confident match is found
            - None if no match or conflicting taxes (caller should fallback)
        """
        for inv in posted_invoices:
            matching = inv.line_ids.filtered(
                lambda l: l.product_id.id == product.id
                and l.display_type == 'product'
                and l.sale_line_ids.order_id == order
            )
            if matching:
                # Check all matching lines have the same tax_ids
                tax_sets = [frozenset(l.tax_ids.ids) for l in matching]
                if len(set(tax_sets)) == 1:
                    return matching[0].tax_ids
                else:
                    # Conflicting taxes on the same product — can't
                    # determine which to reverse
                    _logger.warning(
                        "Order %s: product %s has conflicting tax "
                        "treatments on invoice %s — falling back to "
                        "tax-inclusive amount",
                        order.name, product.display_name, inv.name,
                    )
                    return None
        return None


class RefundSync:
    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = RefundImporter(env, backend)

    def import_refunds(self):
        """Import refunds for orders with refund status.

        Two-layer pruning to avoid unbounded API fan-out:

        Layer 1 — ``refunded`` (terminal state): skip orders that
        already have at least one refund binding.  ``refunded`` means
        the full amount has been refunded; Shopify will not add further
        refunds.  ``import_refunds_for_order`` fetches ALL refunds for
        the order in one call and creates bindings for each, so if any
        binding exists we have seen all of them.

        Layer 2 — ``partially_refunded`` (open-ended): new refunds can
        appear at any time.  We bound the scan to orders whose
        ``write_date`` falls within ``reconciliation_order_days``.  The
        ``orders/updated`` webhook advances ``write_date`` on the order
        binding whenever a refund changes the financial status (via
        ``_update_status_fields`` and ``_mark_synced``), so recently-
        refunded orders stay inside the window.  The cron acts as a
        catch-all for missed webhooks.
        """
        # ── Layer 1: fully-refunded orders ──
        fully_refunded = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', '=', 'synced'),
            ('shopify_financial_status', '=', 'refunded'),
        ])
        if fully_refunded:
            already_imported_ids = set(
                self.env['shopify.refund.binding'].search([
                    ('order_binding_id', 'in', fully_refunded.ids),
                ]).mapped('order_binding_id').ids
            )
            unchecked_refunded = fully_refunded.filtered(
                lambda b: b.id not in already_imported_ids
            )
        else:
            unchecked_refunded = self.env['shopify.order.binding']

        # ── Layer 2: partially-refunded orders (date-bounded) ──
        days = self.backend.reconciliation_order_days or 30
        cutoff = fields.Datetime.now() - timedelta(days=days)
        partially_refunded = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', '=', 'synced'),
            ('shopify_financial_status', '=', 'partially_refunded'),
            ('write_date', '>=', cutoff),
        ])

        order_bindings = unchecked_refunded | partially_refunded

        total_success = total_errors = total_skipped = 0
        for ob in order_bindings:
            s, e, sk = self.importer.import_refunds_for_order(ob)
            total_success += s
            total_errors += e
            total_skipped += sk
        return total_success, total_errors, total_skipped
