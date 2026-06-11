# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields


def _parse_shopify_dt(dt_str):
    """Convert Shopify ISO 8601 datetime to Odoo format."""
    if not dt_str:
        return False
    try:
        return fields.Datetime.to_datetime(
            dt_str.replace('T', ' ').replace('Z', '')
        )
    except (ValueError, TypeError):
        return False

from .accounting import (
    check_total_against_shopify,
    schedule_account_activity,
    schedule_total_mismatch_activity,
    validate_order_income_accounts,
)
from .base_exporter import BaseExporter
from .base_importer import BaseImporter
from .checksum import compute_checksum
from ..shopify_api.queries.order import FETCH_ORDERS, ORDER_UPDATE_MUTATION

_logger = logging.getLogger(__name__)


class OrderExporter(BaseExporter):
    entity_name = 'order'
    binding_model = 'shopify.order.binding'

    def _compute_checksum(self, binding):
        order = binding.odoo_id
        return compute_checksum({
            'note': order.note or '',
            'shopify_tags': order.shopify_tags or '',
        })

    def _export_one(self, binding):
        order = binding.odoo_id
        if not binding.shopify_id:
            _logger.warning(
                "Cannot export order %s: no Shopify ID on binding",
                order.name,
            )
            return

        order_input = {
            'id': binding.shopify_id,
            'note': order.note or '',
            'tags': [t.strip() for t in (order.shopify_tags or '').split(',') if t.strip()],
        }
        self.client.execute_mutation(
            ORDER_UPDATE_MUTATION,
            {'input': order_input},
            result_key='orderUpdate',
            estimated_cost=10,
        )


class OrderImporter(BaseImporter):
    entity_name = 'order'
    binding_model = 'shopify.order.binding'

    def __init__(self, env, backend):
        super().__init__(env, backend)
        # Caches to avoid repeated DB lookups during batch import
        self._currency_cache = {}  # currency_code → res.currency
        self._pricelist_cache = {}  # currency_id → product.pricelist
        self._shipping_product = None  # cached shipping product
        self._country_cache = {}  # country_code → res.country
        self._state_cache = {}  # (state_code, country_id) → res.country.state

    def _compute_shopify_checksum(self, node):
        return compute_checksum({
            'name': node.get('name', ''),
            'displayFinancialStatus': node.get('displayFinancialStatus', ''),
            'displayFulfillmentStatus': node.get('displayFulfillmentStatus', ''),
            'updatedAt': node.get('updatedAt', ''),
        })

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id')
        checksum = self._compute_shopify_checksum(node)
        financial_status = (node.get('displayFinancialStatus', '') or '').lower()
        fulfillment_status = (node.get('displayFulfillmentStatus', '') or '').lower()
        refund_count = len(node.get('refunds') or [])

        if (existing_binding and not existing_binding.odoo_id
                and existing_binding.sync_status == 'pending'):
            # Retryable binding without a sale order (action_retry_sync
            # resets an AUD-020 currency failure to 'pending'): retry the
            # creation path so the retry can actually complete the import.
            # Other no-order bindings keep the status-update path below —
            # webhook status changes must still advance write_date on them
            # (refund-window invariant, test_refund_scan_pruning).
            order = self._create_sale_order(node)
            if order:
                existing_binding.write({
                    'odoo_id': order.id,
                    'shopify_total_amount': self._get_money_amount(
                        node.get('totalPriceSet')),
                    'sync_status': 'synced',
                    'sync_error': False,
                    'shopify_financial_status': financial_status,
                    'shopify_fulfillment_status': fulfillment_status,
                    'shopify_refund_count': refund_count,
                    'shopify_created_at': _parse_shopify_dt(node.get('createdAt')),
                    'sync_checksum': checksum,
                    'last_sync_date': fields.Datetime.now(),
                })
                self._track_discount_usage(existing_binding, node)
                if (self.backend.auto_create_invoice
                        and financial_status == 'paid'):
                    self._auto_register_payment(order, existing_binding)
            return

        if existing_binding:
            # Detect financial status change → trigger transition handler
            old_financial = existing_binding.shopify_financial_status or ''
            if financial_status and financial_status != old_financial:
                try:
                    from .payment_status_sync import PaymentStatusHandler
                    handler = PaymentStatusHandler(self.env, self.backend)
                    handler.handle_status_change(
                        existing_binding, old_financial, financial_status,
                    )
                except Exception as e:
                    _logger.warning(
                        "Payment transition failed for order %s: %s",
                        existing_binding.shopify_order_name, e,
                    )

            # Update fulfillment status and refund count
            old_fulfillment = existing_binding.shopify_fulfillment_status or ''
            update_vals = {}
            if fulfillment_status != old_fulfillment:
                update_vals['shopify_fulfillment_status'] = fulfillment_status
            if refund_count != existing_binding.shopify_refund_count:
                update_vals['shopify_refund_count'] = refund_count
            if update_vals:
                # Only propagate fulfillment_status to the sale order —
                # shopify_refund_count is binding-only metadata.
                so_vals = {k: v for k, v in update_vals.items()
                           if k != 'shopify_refund_count'}
                existing_binding.write(update_vals)
                if existing_binding.odoo_id and so_vals:
                    existing_binding.odoo_id.with_context(
                        shopify_no_auto_export=True,
                    ).write(so_vals)
            existing_binding._mark_synced(checksum=checksum)
            self._track_discount_usage(existing_binding, node)
        else:
            order = self._create_sale_order(node)
            if order:
                order_binding = self.env['shopify.order.binding'].create({
                    'backend_id': self.backend.id,
                    'odoo_id': order.id,
                    'shopify_total_amount': self._get_money_amount(
                        node.get('totalPriceSet')),
                    'shopify_id': shopify_id,
                    'shopify_order_name': node.get('name', ''),
                    'shopify_financial_status': financial_status,
                    'shopify_fulfillment_status': fulfillment_status,
                    'shopify_refund_count': refund_count,
                    'shopify_created_at': _parse_shopify_dt(node.get('createdAt')),
                    'sync_status': 'synced',
                    'sync_checksum': checksum,
                    'last_sync_date': fields.Datetime.now(),
                })
                self._track_discount_usage(order_binding, node)
                # Register payment for fully paid orders with posted invoices
                if (self.backend.auto_create_invoice
                        and financial_status == 'paid'):
                    self._auto_register_payment(order, order_binding)

    def _create_sale_order(self, node):
        """Create an Odoo sale.order from Shopify order data."""
        partner = self._resolve_customer(node)
        if not partner:
            _logger.warning("Could not resolve customer for order %s", node.get('name'))
            return None

        # Skip cancelled orders — they should not create an Odoo draft/SO.
        cancelled_at = node.get('cancelledAt')
        is_cancelled = bool(cancelled_at) or node.get('displayFinancialStatus', '').lower() == 'voided'

        order_vals = {
            'partner_id': partner.id,
            'sales_channel': 'shopify',
            'shopify_order_name': node.get('name', ''),
            'shopify_financial_status': (node.get('displayFinancialStatus', '') or '').lower(),
            'shopify_fulfillment_status': (node.get('displayFulfillmentStatus', '') or '').lower(),
            'note': node.get('note') or '',
            'company_id': self.backend.company_id.id,
            'warehouse_id': self.backend.warehouse_id.id,
        }

        # Multi-currency support (AUD-020). Policy (Ahmed, 2026-06-11):
        # never book foreign amounts as company currency; auto-activate
        # currencies visibly; require a usable exchange rate (order
        # money-pair preferred, Odoo rates fallback); otherwise error-state
        # the order binding with an actionable message.
        currency_mode = self.backend.import_currency_mode
        company_currency = self.backend.company_id.currency_id
        self._company_take_presentment = False
        self._company_convert = None
        if currency_mode == 'presentment':
            currency_code = node.get('presentmentCurrencyCode', '')
            if not currency_code:
                currency_code = (
                    node.get('totalPriceSet', {}).get('presentmentMoney', {}).get('currencyCode', '')
                )
        else:
            # 'shopify' and 'company' modes both source shopMoney amounts
            currency_code = (
                node.get('currencyCode', '')
                or node.get('totalPriceSet', {}).get('shopMoney', {}).get('currencyCode', '')
            )
        if currency_code and currency_code != company_currency.name:
            if currency_mode == 'company':
                # Convert to TRUE company-currency amounts (decision
                # 2026-06-11: convert, do not refuse). _get_money_amount
                # applies the per-order conversion prepared here.
                if not self._prepare_company_conversion(node):
                    self._order_import_error(node, (
                        "Shopify order %s is in %s but this backend books "
                        "in %s (company currency mode) and no usable "
                        "exchange rate was found — none derivable from the "
                        "order and no %s rate configured in Odoo. The "
                        "order was NOT imported. Add an exchange rate "
                        "(Accounting > Configuration > Currencies), then "
                        "use Retry Sync on this order."
                        % (node.get('name', ''), currency_code,
                           company_currency.name, currency_code)
                    ))
                    return None
            else:
                currency = self._resolve_currency(
                    currency_code, node.get('name', ''),
                )
                if not currency:
                    self._order_import_error(node, (
                        "Shopify order %s uses currency %s, which does not "
                        "exist in this Odoo database. The order was NOT "
                        "imported. Create or activate the currency "
                        "(Accounting > Configuration > Currencies), then "
                        "use Retry Sync on this order."
                        % (node.get('name', ''), currency_code)
                    ))
                    return None
                if not self._ensure_usable_rate(currency, node):
                    self._order_import_error(node, (
                        "Shopify order %s is in %s but no usable exchange "
                        "rate exists — none derivable from the order and "
                        "no %s rate configured in Odoo. The order was NOT "
                        "imported. Add an exchange rate (Accounting > "
                        "Configuration > Currencies), then use Retry Sync "
                        "on this order."
                        % (node.get('name', ''), currency_code,
                           currency_code)
                    ))
                    return None
                order_vals['currency_id'] = currency.id
                pricelist = self._resolve_pricelist(currency)
                if pricelist:
                    order_vals['pricelist_id'] = pricelist.id

        # Resolve shipping address
        shipping = node.get('shippingAddress')
        if shipping:
            ship_partner = self._get_or_create_address(partner, shipping, 'delivery')
            order_vals['partner_shipping_id'] = ship_partner.id

        # Resolve billing address
        billing = node.get('billingAddress')
        if billing:
            bill_partner = self._get_or_create_address(partner, billing, 'invoice')
            order_vals['partner_invoice_id'] = bill_partner.id

        # All sale.order operations must run in the backend's company
        # context and suppress the reverse-export trigger that fires on
        # sale.order writes/creates.
        SaleOrder = self.env['sale.order'].with_company(
            self.backend.company_id,
        ).with_context(shopify_no_auto_export=True)
        order = SaleOrder.create(order_vals)

        # Create order lines
        line_items_conn = node.get('lineItems', {})
        line_items = line_items_conn.get('edges', [])
        if line_items_conn.get('pageInfo', {}).get('hasNextPage'):
            _logger.warning(
                "Order %s has more than %d line items — some may be "
                "truncated. Review manually on Shopify.",
                node.get('name'), len(line_items),
            )
        for edge in line_items:
            li = edge.get('node', {})
            self._create_order_line(order, li)

        # Create shipping line
        shipping_lines = node.get('shippingLines', {}).get('edges', [])
        for edge in shipping_lines:
            sl = edge.get('node', {})
            self._create_shipping_line(order, sl)

        if is_cancelled:
            # Record as cancelled in Odoo — do NOT confirm or invoice.
            try:
                order.with_context(
                    shopify_no_auto_export=True,
                    disable_cancel_warning=True,
                ).action_cancel()
            except Exception as e:
                _logger.warning(
                    "Failed to auto-cancel Shopify-cancelled order %s: %s",
                    node.get('name'), e,
                )
            return order

        # Confirm order if paid
        if order_vals['shopify_financial_status'] in ('paid', 'partially_paid', 'authorized'):
            order.with_context(
                shopify_no_auto_export=True,
            ).action_confirm()
            # Auto-create invoice if configured
            if self.backend.auto_create_invoice:
                fin_status = order_vals['shopify_financial_status']
                if fin_status in ('paid', 'partially_paid'):
                    self._auto_create_invoice(
                        order,
                        self._get_money_amount(node.get('totalPriceSet')),
                    )
                    if fin_status == 'partially_paid':
                        order.activity_schedule(
                            'mail.mail_activity_data_todo',
                            summary="Shopify Partial Payment",
                            note="Order imported as partially paid on Shopify. "
                                 "Please register the partial payment on the invoice.",
                        )

        return order

    def _auto_create_invoice(self, order, expected_total=0.0):
        """Create and post an invoice inside a savepoint.

        A savepoint isolates accounting failures (missing income account,
        fiscal position gaps, etc.) so the surrounding order import
        transaction is never poisoned.

        Idempotent: skips if the order already has a non-cancelled invoice.
        """
        # Idempotency guard: skip if invoice already exists
        existing_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state != 'cancel'
        )
        if existing_invoices:
            _logger.info(
                "Order %s already has invoice(s) — skipping auto-create",
                order.name,
            )
            return

        missing, _fallback = validate_order_income_accounts(
            self.env, order,
        )
        if missing:
            schedule_account_activity(
                order,
                summary="Shopify auto-invoice skipped",
                products=missing,
            )
            return

        try:
            with self.env.cr.savepoint():
                invoice = order.with_company(
                    self.backend.company_id,
                ).with_context(
                    shopify_no_auto_export=True,
                )._create_invoices()
                if invoice:
                    # Permanent total-check guard (DEC-011): never post
                    # an invoice whose total differs from what Shopify
                    # actually charged. The invoice stays in draft with
                    # a visible activity.
                    ok, tol = check_total_against_shopify(
                        invoice, expected_total,
                    )
                    if not ok:
                        schedule_total_mismatch_activity(
                            order, invoice, expected_total, tol,
                        )
                        return
                    invoice.with_context(
                        shopify_no_auto_export=True,
                    ).action_post()
        except Exception as e:
            _logger.warning(
                "Auto-invoice failed for order %s (products: %s): %s. "
                "Check income account, fiscal position, and company "
                "chart of accounts.",
                order.name,
                ', '.join(order.order_line.product_id.mapped('display_name')),
                e,
            )
            order.activity_schedule(
                'mail.mail_activity_data_warning',
                summary="Shopify auto-invoice failed",
                note="Invoice creation failed: %s" % e,
            )

    def _auto_register_payment(self, order, order_binding):
        """Register payment on posted invoices for fully paid orders.

        Delegates to PaymentStatusHandler for gateway resolution and
        idempotency. Safe to call multiple times.
        """
        posted_invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
            and i.amount_residual > 0
        )
        if not posted_invoices:
            return
        try:
            from .payment_status_sync import PaymentStatusHandler
            handler = PaymentStatusHandler(self.env, self.backend)
            handler._register_payment(posted_invoices[0], order_binding)
        except Exception as e:
            _logger.warning(
                "Auto payment registration failed for order %s: %s",
                order.name, e,
            )

    def _track_discount_usage(self, order_binding, node):
        """Check for promoter discount codes and record usage."""
        discount_codes = node.get('discountCodes') or []
        if not discount_codes:
            return

        # Get order total from Shopify data (always use shopMoney for commissions)
        total_price = float(
            node.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0)
        )
        total_discounts = float(
            node.get('totalDiscountsSet', {}).get('shopMoney', {}).get('amount', 0)
        )

        for code_str in discount_codes:
            discount_binding = self.env['shopify.discount.code'].search([
                ('backend_id', '=', self.backend.id),
                ('code', '=ilike', code_str),
            ], limit=1)
            if not discount_binding:
                continue

            # Idempotency: skip if this (code, order) pair was already recorded.
            existing_usage = self.env['shopify.discount.usage'].search([
                ('discount_code_id', '=', discount_binding.id),
                ('order_binding_id', '=', order_binding.id),
            ], limit=1)
            if existing_usage:
                continue

            # Compute commission
            promoter = discount_binding.promoter_id
            if promoter.commission_type == 'percentage':
                commission = total_price * (promoter.commission_rate / 100.0)
            else:
                commission = promoter.commission_rate

            self.env['shopify.discount.usage'].create({
                'discount_code_id': discount_binding.id,
                'order_binding_id': order_binding.id,
                'discount_amount': total_discounts,
                'order_total': total_price,
                'commission_amount': commission,
                'date': fields.Datetime.now(),
            })

    def _get_money_amount(self, price_set):
        """Extract the correct amount from a priceSet based on currency mode.

        For 'presentment' mode, use presentmentMoney (customer-facing currency).
        Otherwise, use shopMoney (store base currency).
        """
        if not price_set:
            return 0.0
        if self.backend.import_currency_mode == 'presentment':
            money = price_set.get('presentmentMoney') or price_set.get('shopMoney', {})
        elif getattr(self, '_company_take_presentment', False):
            # Company mode, presentment side IS the company currency:
            # Shopify's own per-line conversion (the order money-pair
            # rate) wins over any Odoo daily rate — policy 2026-06-11.
            money = price_set.get('presentmentMoney') or price_set.get('shopMoney', {})
        else:
            money = price_set.get('shopMoney', {})
        amount = float(money.get('amount', 0))
        conv = getattr(self, '_company_convert', None)
        if conv and amount:
            from_currency, company, conv_date = conv
            amount = from_currency._convert(
                amount, company.currency_id, company, conv_date,
            )
        return amount

    def _prepare_company_conversion(self, node):
        """Company mode with a foreign shop currency: arrange for
        _get_money_amount to return TRUE company-currency amounts.

        Preference (policy 2026-06-11): (1) the order's own money pair —
        when presentmentMoney is in the company currency, take that side
        directly (Shopify's per-line conversion, exact to the cent);
        (2) Odoo rates — convert shopMoney via res.currency rates dated to
        the order; (3) neither usable → False (caller error-states).
        """
        company = self.backend.company_id
        total_set = node.get('totalPriceSet') or {}
        pres = total_set.get('presentmentMoney') or {}
        shop = total_set.get('shopMoney') or {}
        if (pres.get('currencyCode') or '') == company.currency_id.name:
            self._company_take_presentment = True
            return True
        shop_code = shop.get('currencyCode') or ''
        shop_currency = self._resolve_currency(shop_code, node.get('name', ''))
        if not shop_currency:
            return False
        has_rate = self.env['res.currency.rate'].search_count([
            ('currency_id', '=', shop_currency.id),
            ('company_id', 'in', [company.id, False]),
        ])
        if not has_rate:
            return False
        conv_date = fields.Date.to_date(
            (node.get('createdAt') or '')[:10] or fields.Date.today(),
        )
        self._company_convert = (shop_currency, company, conv_date)
        return True

    def _ensure_usable_rate(self, currency, node):
        """Guarantee a usable exchange rate before booking a foreign-
        currency order (policy 2026-06-11: order money-pair preferred,
        Odoo rates fallback, otherwise the caller error-states).

        When the order's money pair (shopMoney vs presentmentMoney with
        the company currency on one side) yields a rate and no rate
        record exists for the order's date, a company-scoped, dated
        res.currency.rate is created VISIBLY (log + backend chatter), so
        it cannot leak into other companies' conversions.
        """
        company = self.backend.company_id
        order_date = fields.Date.to_date(
            (node.get('createdAt') or '')[:10] or fields.Date.today(),
        )
        total_set = node.get('totalPriceSet') or {}
        sides = [total_set.get('shopMoney') or {},
                 total_set.get('presentmentMoney') or {}]
        pair_rate = None
        cur_amt = company_amt = 0.0
        for i, side in enumerate(sides):
            other = sides[1 - i]
            if (side.get('currencyCode') == currency.name
                    and other.get('currencyCode') == company.currency_id.name):
                cur_amt = float(side.get('amount') or 0)
                company_amt = float(other.get('amount') or 0)
                if cur_amt > 0 and company_amt > 0:
                    pair_rate = cur_amt / company_amt
                break
        same_date_rate = self.env['res.currency.rate'].search_count([
            ('currency_id', '=', currency.id),
            ('company_id', 'in', [company.id, False]),
            ('name', '=', order_date),
        ])
        if pair_rate and not same_date_rate:
            self.env['res.currency.rate'].create({
                'currency_id': currency.id,
                'rate': pair_rate,
                'name': order_date,
                'company_id': company.id,
            })
            msg = (
                "Exchange rate %s %.6f per %s created from Shopify order "
                "%s money fields (dated %s, company %s)." % (
                    currency.name, pair_rate, company.currency_id.name,
                    node.get('name', ''), order_date, company.name,
                )
            )
            _logger.info(msg)
            self.backend.message_post(
                body=msg, message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            return True
        return bool(same_date_rate or self.env['res.currency.rate'].search_count([
            ('currency_id', '=', currency.id),
            ('company_id', 'in', [company.id, False]),
        ]))

    def _order_import_error(self, node, message):
        """Record a VISIBLE, retryable import failure for this order
        (rule 5): error-state binding with an actionable message, no
        sale order. Idempotent — re-uses the existing binding on retry."""
        shopify_id = node.get('id')
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', shopify_id),
        ], limit=1)
        vals = {
            'sync_status': 'error',
            'sync_error': message,
            'shopify_order_name': node.get('name', ''),
            'shopify_financial_status': (
                node.get('displayFinancialStatus', '') or ''
            ).lower(),
        }
        if binding:
            binding.write(vals)
        else:
            vals.update({
                'backend_id': self.backend.id,
                'shopify_id': shopify_id,
            })
            binding = self.env['shopify.order.binding'].create(vals)
        _logger.warning(
            "Order %s import error: %s", node.get('name', ''), message,
        )
        return binding

    def _resolve_currency(self, currency_code, order_name=''):
        """Resolve a currency code to a res.currency record, with caching.

        Inactive currencies are activated automatically and VISIBLY
        (policy 2026-06-11): log + backend chatter note. Unknown codes
        return False — the caller degrades visibly.
        """
        if currency_code in self._currency_cache:
            return self._currency_cache[currency_code]

        currency = self.env['res.currency'].search([
            ('name', '=', currency_code),
            ('active', '=', True),
        ], limit=1)
        if not currency:
            currency = self.env['res.currency'].with_context(
                active_test=False,
            ).search([('name', '=', currency_code)], limit=1)
            if currency:
                currency.active = True
                msg = (
                    "Currency %s was activated automatically to import "
                    "Shopify order %s in its original currency." % (
                        currency_code, order_name,
                    )
                )
                _logger.info(msg)
                self.backend.message_post(
                    body=msg, message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
            else:
                _logger.warning(
                    "Currency %s not found for order %s — the order "
                    "cannot be imported until it exists in Odoo.",
                    currency_code, order_name,
                )
                currency = False
        self._currency_cache[currency_code] = currency or False
        return self._currency_cache[currency_code]

    def _resolve_pricelist(self, currency):
        """Find or create a pricelist for the given currency, with caching."""
        if currency.id in self._pricelist_cache:
            return self._pricelist_cache[currency.id]

        pricelist = self.env['product.pricelist'].search([
            ('currency_id', '=', currency.id),
            '|',
            ('company_id', '=', self.backend.company_id.id),
            ('company_id', '=', False),
        ], limit=1)
        if not pricelist:
            # Auto-create a pricelist for this currency
            pricelist = self.env['product.pricelist'].create({
                'name': f'Shopify {currency.name}',
                'currency_id': currency.id,
                'company_id': self.backend.company_id.id,
            })
            _logger.info(
                "Auto-created pricelist '%s' for currency %s",
                pricelist.name, currency.name,
            )
        self._pricelist_cache[currency.id] = pricelist
        return pricelist

    def _resolve_customer(self, node):
        """Find or create the customer for this order.

        Uses the backend's dedup strategy and ensures a binding is created
        when a new partner is linked to a Shopify customer.
        """
        customer_data = node.get('customer')
        if not customer_data:
            # Guest order — dedup by shipping address email/phone
            return self._resolve_guest_customer(node)

        shopify_customer_id = customer_data.get('id', '')

        # Step 1: Check existing binding (fastest, most reliable)
        if shopify_customer_id:
            binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_customer_id),
            ], limit=1)
            if binding:
                return binding.odoo_id

        # Step 2: Dedup by configured strategy
        email = customer_data.get('email')
        phone = customer_data.get('phone')
        partner = self._dedup_partner(email, phone)

        # Step 3: Create new partner if no match
        if not partner:
            first_name = customer_data.get('firstName', '') or ''
            last_name = customer_data.get('lastName', '') or ''
            name = f"{first_name} {last_name}".strip() or email or 'Shopify Customer'
            partner = self.env['res.partner'].create({
                'name': name,
                'email': email or False,
                'phone': phone or False,
                'customer_rank': 1,
                'is_shopify_customer': True,
            })

        # Step 4: Create binding so future lookups use Step 1 (fast path)
        if shopify_customer_id:
            existing_binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_customer_id),
            ], limit=1)
            if not existing_binding:
                self.env['shopify.customer.binding'].create({
                    'backend_id': self.backend.id,
                    'odoo_id': partner.id,
                    'shopify_id': shopify_customer_id,
                    'shopify_email': email or '',
                    'sync_status': 'synced',
                    'sync_checksum': shopify_customer_id,
                    'last_sync_date': fields.Datetime.now(),
                })

        return partner

    def _resolve_guest_customer(self, node):
        """Resolve customer for guest orders (no Shopify customer object).

        Dedup by email from shipping/billing address to avoid creating
        a new partner for every guest order from the same person.
        """
        shipping = node.get('shippingAddress', {})
        billing = node.get('billingAddress', {})

        # Try to find an identifier
        email = node.get('email') or shipping.get('email') or billing.get('email')
        phone = shipping.get('phone') or billing.get('phone')

        partner = self._dedup_partner(email, phone)
        if partner:
            return partner

        # Create new from shipping address
        if shipping:
            name = f"{shipping.get('firstName', '')} {shipping.get('lastName', '')}".strip()
            return self.env['res.partner'].create({
                'name': name or 'Shopify Guest',
                'email': email or False,
                'phone': phone or False,
                'customer_rank': 1,
                'is_shopify_customer': True,
            })
        return None

    def _dedup_partner(self, email, phone):
        """Find existing partner using the backend's dedup strategy."""
        dedup = self.backend.customer_dedup_field or 'email'

        if dedup == 'email' and email:
            return self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('parent_id', '=', False),
            ], limit=1)

        if dedup == 'phone' and phone:
            return self.env['res.partner'].search([
                ('phone', '=', phone),
                ('parent_id', '=', False),
            ], limit=1)

        if dedup == 'email_phone':
            if email:
                partner = self.env['res.partner'].search([
                    ('email', '=ilike', email),
                    ('parent_id', '=', False),
                ], limit=1)
                if partner:
                    return partner
            if phone:
                return self.env['res.partner'].search([
                    ('phone', '=', phone),
                    ('parent_id', '=', False),
                ], limit=1)

        return None

    def _get_or_create_address(self, parent, addr_data, addr_type):
        """Get or create an address partner."""
        country = self._resolve_country(addr_data.get('countryCodeV2'))
        state = self._resolve_state(addr_data.get('provinceCode'), country)

        first_name = addr_data.get('firstName', '') or ''
        last_name = addr_data.get('lastName', '') or ''
        name = f"{first_name} {last_name}".strip() or parent.name

        # Try to find existing child address
        existing = self.env['res.partner'].search([
            ('parent_id', '=', parent.id),
            ('type', '=', addr_type),
            ('street', '=', addr_data.get('address1', '')),
            ('city', '=', addr_data.get('city', '')),
        ], limit=1)
        if existing:
            return existing

        return self.env['res.partner'].create({
            'parent_id': parent.id,
            'type': addr_type,
            'name': name,
            'street': addr_data.get('address1') or False,
            'street2': addr_data.get('address2') or False,
            'city': addr_data.get('city') or False,
            'zip': addr_data.get('zip') or False,
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
            'phone': addr_data.get('phone') or False,
        })

    def _create_order_line(self, order, line_item):
        """Create a sale.order.line from a Shopify line item."""
        product = self._resolve_product(line_item)
        price_unit = self._get_money_amount(line_item.get('originalUnitPriceSet'))

        # Calculate discount using correct currency amounts
        discount_total = 0
        for alloc in line_item.get('discountAllocations', []):
            discount_total += self._get_money_amount(alloc.get('allocatedAmountSet'))
        quantity = line_item.get('quantity', 1)
        discount_pct = 0
        line_subtotal = price_unit * quantity if price_unit and quantity else 0
        if line_subtotal:
            discount_pct = (discount_total / line_subtotal) * 100
        elif discount_total > 0:
            # Zero-price item with a discount allocation (e.g. 100% promo).
            # Represent as full discount so the line stays visible on the
            # order with a crossed-out price (BUG-O2).
            discount_pct = 100.0

        line_vals = {
            'order_id': order.id,
            'product_id': product.id if product else False,
            'name': line_item.get('title', 'Shopify Item'),
            'product_uom_qty': quantity,
            'price_unit': price_unit,
            'discount': min(discount_pct, 100),
        }

        # Apply tax mapping from Shopify taxLines. Shopify is
        # authoritative for line taxes (AUD-016): when nothing resolves
        # (tax-exempt order, or unmapped tax titles/rates) the line
        # carries NO taxes — never the product's default sale tax. Any
        # unmapped remainder is caught visibly by the total-check guard
        # before auto-posting (DEC-011).
        tax_ids = self._resolve_taxes(line_item.get('taxLines', []))
        line_vals['tax_ids'] = [(6, 0, tax_ids)] if tax_ids else [(5,)]

        self.env['sale.order.line'].create(line_vals)

    def _resolve_taxes(self, tax_lines):
        """Map Shopify tax lines to Odoo tax IDs via shopify.tax.mapping.

        Falls back to searching Odoo taxes by rate if no mapping is
        configured for a given tax title.
        """
        if not tax_lines:
            return []

        # Lazy-load tax mapping cache once per importer run
        if not hasattr(self, '_tax_map_cache'):
            mappings = self.env['shopify.tax.mapping'].search([
                ('backend_id', '=', self.backend.id),
                ('active', '=', True),
            ])
            self._tax_map_cache = {
                m.shopify_tax_name.lower(): m.odoo_tax_id
                for m in mappings if m.odoo_tax_id
            }
            self._tax_rate_cache = {}

        tax_ids = []
        for tl in tax_lines:
            title = (tl.get('title') or '').strip()
            rate = tl.get('rate')  # Shopify rate is a decimal, e.g. 0.1 = 10%

            # 1. Try exact mapping by name
            mapped_tax = self._tax_map_cache.get(title.lower())
            if mapped_tax:
                tax_ids.append(mapped_tax.id)
                continue

            # 2. Fallback: find Odoo tax by rate (2 dp is sufficient for tax
            # rates; a ±0.005 tolerance avoids float→SQL precision drift).
            if rate is not None:
                rate_pct = round(float(rate) * 100, 2)
                if rate_pct not in self._tax_rate_cache:
                    odoo_tax = self.env['account.tax'].search([
                        ('type_tax_use', '=', 'sale'),
                        ('amount', '>=', rate_pct - 0.005),
                        ('amount', '<=', rate_pct + 0.005),
                        ('company_id', '=', self.backend.company_id.id),
                    ], limit=1)
                    self._tax_rate_cache[rate_pct] = odoo_tax
                fallback_tax = self._tax_rate_cache[rate_pct]
                if fallback_tax:
                    tax_ids.append(fallback_tax.id)
                else:
                    _logger.warning(
                        "Tax line dropped: no mapping for '%s' and no Odoo tax "
                        "matching rate %.2f%% (backend %s). Create a tax mapping "
                        "or an Odoo tax with this rate.",
                        title, rate_pct, self.backend.id,
                    )
            else:
                _logger.warning(
                    "Tax line dropped: no mapping for '%s' and no rate provided "
                    "(backend %s). Create a tax mapping for this title.",
                    title, self.backend.id,
                )

        return list(set(tax_ids))

    def _create_shipping_line(self, order, shipping_line):
        """Create a shipping line on the order.

        Shipping taxes follow the same rule as product lines
        (AUD-015/016): Shopify ``taxLines`` are authoritative, resolved
        via ``_resolve_taxes()``; when nothing resolves the line carries
        NO taxes — never the shipping product's default sale tax. Any
        unmapped remainder is caught visibly by the total-check guard
        before auto-posting (DEC-011). Refund credit notes mirror taxes
        from the original invoice's shipping line, so they inherit the
        correct treatment from here.
        """
        price = self._get_money_amount(shipping_line.get('originalPriceSet'))
        if not price:
            return

        # Use cached shipping product to avoid repeated lookups
        shipping_product = self._shipping_product
        if not shipping_product:
            shipping_product = self.backend.shipping_product_id
            if not shipping_product:
                shipping_product = self.env['product.product'].search([
                    ('default_code', '=', 'SHOPIFY-SHIPPING'),
                ], limit=1)
            if not shipping_product:
                shipping_product = self.env['product.product'].create({
                    'name': 'Shopify Shipping',
                    'default_code': 'SHOPIFY-SHIPPING',
                    'type': 'service',
                    'list_price': 0,
                    # No default sale tax: shipping tax always comes
                    # from Shopify taxLines, and other consumers of
                    # this product (refund credit notes) must not pick
                    # up a company default through it.
                    'taxes_id': [(5, 0, 0)],
                })
            self._shipping_product = shipping_product

        tax_ids = self._resolve_taxes(shipping_line.get('taxLines', []))
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': shipping_product.id,
            'name': shipping_line.get('title', 'Shipping'),
            'product_uom_qty': 1,
            'price_unit': price,
            'tax_ids': [(6, 0, tax_ids)] if tax_ids else [(5,)],
        })

    def _resolve_product(self, line_item):
        """Try to resolve the Odoo product for a Shopify line item."""
        variant_data = line_item.get('variant') or {}
        shopify_variant_id = variant_data.get('id', '')

        if shopify_variant_id:
            vbinding = self.env['shopify.variant.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_variant_id),
            ], limit=1)
            if vbinding:
                return vbinding.odoo_id

        # Fallback: match by SKU — scoped to the backend's company (and
        # company-agnostic products) to prevent cross-company collisions
        # when multiple Shopify stores share an Odoo instance (BUG-O1).
        sku = variant_data.get('sku', '')
        if sku:
            return self.env['product.product'].search([
                ('default_code', '=', sku),
                ('company_id', 'in', [self.backend.company_id.id, False]),
            ], limit=1)

        return None

    def _resolve_country(self, code):
        if not code:
            return None
        if code in self._country_cache:
            return self._country_cache[code]
        country = self.env['res.country'].search([('code', '=', code)], limit=1)
        self._country_cache[code] = country or None
        return self._country_cache[code]

    def _resolve_state(self, state_code, country):
        if not state_code or not country:
            return None
        cache_key = (state_code, country.id)
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        state = self.env['res.country.state'].search([
            ('code', '=', state_code),
            ('country_id', '=', country.id),
        ], limit=1)
        self._state_cache[cache_key] = state or None
        return self._state_cache[cache_key]


class OrderSync:
    """Orchestrates order sync."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = OrderImporter(env, backend)
        self.exporter = OrderExporter(env, backend)

    def export_orders(self):
        return self.exporter.export_batch()

    def import_orders(self):
        nodes = self.importer.client.fetch_paginated(
            FETCH_ORDERS, 'orders',
            page_size=min(self.backend.batch_size, 50),
            estimated_cost_per_page=20,
        )
        return self.importer.import_batch(nodes)

    def import_single_order(self, webhook_data):
        """Import from webhook (REST payload)."""
        shopify_id = f"gid://shopify/Order/{webhook_data.get('id', '')}"
        try:
            client = self.backend._make_api_client()
            # Must match FETCH_ORDERS shape: include currencyCode +
            # presentmentCurrencyCode, presentmentMoney on every priceSet,
            # subtotal/shipping/tax totals, and per-line taxLines. Otherwise
            # presentment-mode backends silently fall back to shop currency
            # and imported orders lose tax mappings.
            query = """
            query GetOrder($id: ID!) {
              order(id: $id) {
                id name createdAt updatedAt
                displayFinancialStatus displayFulfillmentStatus
                cancelledAt closed note tags
                currencyCode
                presentmentCurrencyCode
                totalPriceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                subtotalPriceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                totalShippingPriceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                totalTaxSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                totalDiscountsSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                discountCodes
                customer { id email firstName lastName }
                shippingAddress {
                  address1 address2 city province provinceCode
                  country countryCodeV2 zip phone firstName lastName
                }
                billingAddress {
                  address1 address2 city province country countryCodeV2 zip
                }
                lineItems(first: 250) {
                  pageInfo {
                    hasNextPage
                  }
                  edges {
                    node {
                      id title quantity
                      variant { id sku product { id } }
                      originalUnitPriceSet {
                        shopMoney { amount currencyCode }
                        presentmentMoney { amount currencyCode }
                      }
                      discountAllocations {
                        allocatedAmountSet {
                          shopMoney { amount currencyCode }
                          presentmentMoney { amount currencyCode }
                        }
                      }
                      taxLines {
                        title
                        rate
                        priceSet {
                          shopMoney { amount currencyCode }
                          presentmentMoney { amount currencyCode }
                        }
                      }
                    }
                  }
                }
                shippingLines(first: 10) {
                  edges {
                    node {
                      title code
                      originalPriceSet {
                        shopMoney { amount currencyCode }
                        presentmentMoney { amount currencyCode }
                      }
                      taxLines {
                        title
                        rate
                        priceSet {
                          shopMoney { amount currencyCode }
                          presentmentMoney { amount currencyCode }
                        }
                      }
                    }
                  }
                }
                refunds { id }
              }
            }
            """
            body = client.execute(query, {'id': shopify_id}, estimated_cost=15)
            node = body.get('data', {}).get('order')
            if node:
                binding = self.importer._find_binding(shopify_id)
                self.importer._import_one(node, binding)
        except Exception:
            _logger.exception("Failed to import order from webhook: %s", shopify_id)
