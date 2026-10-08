import logging
from datetime import timedelta, datetime

from odoo.modules.registry import Registry

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import GET_PAYOUTS_BY_DATE_RANGE, GET_TRANSACTIONS_FOR_PAYOUT
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc, extract_numeric_id

_logger = logging.getLogger("Qamah:Shopify-Payout")

INVOICE_AND_PAYMENT_TYPES = {
    'CHARGE': {'invoice_type': 'out_invoice', 'payment_type': 'inbound'},
    'REFUND': {'invoice_type': 'out_refund', 'payment_type': 'outbound'},
    'PAYMENT_REFUND': {'invoice_type': 'out_refund', 'payment_type': 'outbound'}}


class ShopifyPayout(models.Model):
    _name = "shopify.payout"
    _description = "Shopify Payout"
    _order = 'payout_date desc'

    @api.depends('bank_statement_id', 'payout_line_ids.is_reconciled')
    def _compute_payout_state(self):
        for record in self:
            if not record.bank_statement_id:
                record.state = 'draft'
            else:
                all_line_reconciled = all([line.is_reconciled for line in record.bank_statement_id.line_ids])
                record.state = 'confirm' if all_line_reconciled else 'posted'

    @api.depends('payout_line_ids.is_reconciled')
    def _compute_all_lines_reconciled(self):
        for payout in self:
            payout.all_lines_reconciled = all(payout_line.is_reconciled for payout_line in payout.payout_line_ids)

    name = fields.Char('Name', required=True, copy=False, index=True, default=lambda self: _('New'))
    report_id = fields.Char("Shopify Payout ID", copy=False)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", copy=False)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Processing'), ('confirm', 'Validated')], string="Status", default="draft", compute="_compute_payout_state", store=True)
    currency_id = fields.Many2one('res.currency', string="Currency", copy=False)
    payout_date = fields.Date("Payout Date", help="The date when the payout was issued.")
    payout_line_ids = fields.One2many('shopify.payout.line', 'payout_id')
    amount = fields.Float("Amount", help="The total amount of the payout.")
    bank_statement_id = fields.Many2one('account.bank.statement', string="Statement")
    all_lines_reconciled = fields.Boolean(compute='_compute_all_lines_reconciled', help="Technical field indicating if all payout lines are fully reconciled.")

    # For to search payout based on order number or order ID.
    order_id = fields.Many2one(related="payout_line_ids.order_id")
    source_order_id = fields.Char(related="payout_line_ids.source_order_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('shopify.payout') or _('New')
        return super().create(vals_list)

    def convert_str_to_float(self, str_amount):
        """
        Safely converts a value to a float, defaulting to 0.0.
        This method is designed to handle inputs from API data, which could be None, an empty string, an int, or a float.

        Args:
            str_amount (any): The value to convert to a float.

        Returns:
            float: The converted amount, or 0.0 if conversion fails.
        """
        # Handles None, empty string, 0
        if not str_amount:
            return 0.0
        try:
            # Attempt to convert the value to a float
            return float(str_amount)
        except (ValueError, TypeError):
            # Log the error if it's not a parsable string
            _logger.warning(f"⚠️ Could not convert value to float: '{str_amount}'", exc_info=True)
            return 0.0

    def shopify_payout_query_filter(self, from_date, to_date):
        """
        Builds a Shopify GraphQL query filter string for Payouts.

        Args:
            from_date (datetime): From date to import payout from shopify to odoo.
            to_date (datetime): To date to import payout from shopify to odoo.

        Returns:
            payout_list (list): A list of dictionaries containing Shopify payout data.
        """
        filters = []
        # Set default to_date to current date if not provided
        # Convert to date if date object
        to_date = to_date or fields.Datetime.now().date()

        if from_date:
            # Convert dates to ISO 8601 format (YYYY-MM-DD) as required by the GraphQL query.
            iso_from = from_date.isoformat()
            iso_to = to_date.isoformat()
            filters.append(f"issued_at:>='{iso_from}' issued_at:<='{iso_to}'")
        filters.append("status:paid")
        return " ".join(filters)

    def fetch_payout_from_shopify(self, mk_instance_id, from_date=False, to_date=False):
        """
        Fetches a list of Shopify Payouts via GraphQL for a date range.

        Args:
            mk_instance_id (record): The marketplace instance record.
            from_date: The start date for the query.
            to_date: The end date for the query.

        Returns:
            tuple: A tuple containing:
                - payout_list (list): A list of payout data dictionaries.
                - from_date (datetime.date): The start date used for the query.
                - to_date (datetime.date): The end date used for the query.

        Raises:
            MarketplaceException: If the GraphQL query fails.
        """
        if not from_date:
            from_date = mk_instance_id.payout_report_last_sync_date if mk_instance_id.payout_report_last_sync_date else fields.Date.today() - timedelta(days=30)
        if not to_date:
            to_date = fields.Date.today()

        query_filter = self.shopify_payout_query_filter(from_date, to_date)  # e.g. 'issued_at:>=2025-07-11 issued_at:<=2025-08-05'

        mk_instance_id.connection_to_shopify()

        payout_list, page_info, cursor = [], False, None
        while True:
            try:
                variables = {"payoutCursor": cursor, "queryFilter": query_filter}
                res = mk_instance_id.execute_graphql_query(GET_PAYOUTS_BY_DATE_RANGE, variables)
                user_errors = res and res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Payouts: %(errors)s") % {'errors': joined_errors})

                payout_raw_list = res and res.get('data', {}) and res.get('data', {}).get('shopifyPaymentsAccount', {}) and res.get('data', {}).get('shopifyPaymentsAccount', {}).get('payouts', {})

                # Exclude the 'pageInfo' dictionary from the payout list, keeping only payout entries.
                if payout_raw_list:
                    payout_list.extend(payout_raw_list[:len(payout_raw_list) - 1])
                    page_info = payout_raw_list[-1].get('pageInfo', {})
                    if not page_info.get('hasNextPage', False):
                        break

                    cursor = page_info.get('endCursor', None)
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"⚠️ Failed to fetch Shopify Payouts: {e}")

        return payout_list, from_date, to_date

    def fetch_transaction_of_payout(self, payout_id, mk_instance_id):
        """
        Fetches all transactions associated with a single Shopify Payout ID.
        Args:
            mk_instance_id (record): The marketplace instance record.
            payout_id (str): The numeric Shopify Payout ID.
        Returns:
            list: A list of transaction data dictionaries.
        Raises:
            MarketplaceException: If the GraphQL query fails.
        """
        payout_transaction_list, page_info, limit, cursor = [], False, 250, None
        while 1:
            try:
                variables = {"cursor": cursor, "payoutQuery": f"payments_transfer_id:{payout_id}"}

                res = mk_instance_id.execute_graphql_query(GET_TRANSACTIONS_FOR_PAYOUT, variables)
                payout_trans_list = res and res.get('data', {}) and res.get('data', {}).get('shopifyPaymentsAccount', {}).get('balanceTransactions', {})

                # Exclude the 'pageInfo' dictionary from the payout list, keeping only payout entries.
                if payout_trans_list:
                    payout_transaction_list.extend(payout_trans_list[:len(payout_trans_list) - 1])
                    page_info = payout_trans_list[-1].get('pageInfo', {})
                    if not page_info.get('hasNextPage', False):
                        break

                    cursor = page_info.get('endCursor', None)

            except Exception as e:
                raise MarketplaceException(f"⚠️ Failed to fetch Shopify Payouts Transactions: {e}")

        return payout_transaction_list

    def prepare_bank_statement_line_vals(self, payout_line_id, order_id):
        self.ensure_one()
        partner_id = self.env['res.partner']
        payout_currency = self.currency_id
        journal_currency = self.mk_instance_id.payout_journal_id.currency_id or self.mk_instance_id.payout_journal_id.company_id.currency_id
        if order_id:
            partner_id = self.env['res.partner']._find_accounting_partner(order_id.partner_id)
        vals = {
            'name': payout_line_id.transaction_label or payout_line_id.transaction_id,
            'payment_ref': payout_line_id.transaction_label,
            'ref': payout_line_id.transaction_id,
            'amount': payout_currency._convert(payout_line_id.amount, journal_currency, self.mk_instance_id.payout_journal_id.company_id, self.payout_date),
            'date': self.payout_date,
            'partner_id': partner_id.id or False,
            'currency_id': self.mk_instance_id.payout_journal_id.currency_id.id or self.mk_instance_id.payout_journal_id.company_id.currency_id.id,
            'shopify_payout_line_id': payout_line_id.id,
            'sequence': 1000,
            'journal_id': self.mk_instance_id.payout_journal_id.id,
        }
        if payout_currency != journal_currency:
            vals.update({'foreign_currency_id': self.currency_id.id, 'amount_currency': payout_line_id.amount, })
        return vals

    def prepare_bank_statement_line(self, statement_id=False):
        self.ensure_one()
        bank_statement_line_list = []
        for payout_line_id in self.payout_line_ids.filtered(lambda x: not x.bank_statement_line_id):
            order_id = payout_line_id.order_id
            existing_statement_line = False
            if not order_id and payout_line_id.source_order_id:
                order_id = self.env['sale.order'].search([('mk_id', '=', payout_line_id.source_order_id), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
                if order_id:
                    payout_line_id.write({'source_order_id': order_id.id})
            if statement_id and payout_line_id.transaction_id:
                existing_statement_line = statement_id.line_ids.filtered(lambda x: x.ref == payout_line_id.transaction_id)
            if payout_line_id.transaction_type_id.transaction_type_code in ['CHARGE', 'REFUND', 'PAYMENT_REFUND'] and not order_id:
                payout_line_id.write({'warn_message': _("Order not found : Transaction won't reconcile automatically.")})
            elif payout_line_id.transaction_type_id.transaction_type_code in ['CHARGE', 'REFUND', 'PAYMENT_REFUND']:
                transaction_amount = payout_line_id.amount if payout_line_id.transaction_type_id.transaction_type_code == 'CHARGE' else -payout_line_id.amount
                invoice_ids = order_id.invoice_ids.filtered(lambda x: x.state == 'posted' and x.move_type == INVOICE_AND_PAYMENT_TYPES[payout_line_id.transaction_type_id.transaction_type_code]['invoice_type'])

                if invoice_ids and sum(invoice_ids.mapped('amount_total')) != transaction_amount:
                    payout_line_id.write({'warn_message': _("Invoice amount mismatch. Please try to reconcile manually.")})

                if not invoice_ids:
                    payout_line_id.write(
                        {'warn_message': _("Invoice not found: Invoice isn't created for order %s for transaction type %s.") % (order_id.name, payout_line_id.transaction_type_id.transaction_type_code)})
            if statement_id and payout_line_id.transaction_type_id.transaction_type_code == 'FEES':
                existing_statement_line = statement_id.line_ids.filtered(lambda x: x.payment_ref == payout_line_id.transaction_label)
            if existing_statement_line:
                existing_statement_line.write({'shopify_payout_line_id': payout_line_id.id, 'payment_ref': payout_line_id.transaction_label, 'name': payout_line_id.transaction_label or payout_line_id.transaction_id})
                continue
            bank_statement_line_list.append((0, 0, self.prepare_bank_statement_line_vals(payout_line_id, order_id)))
        return bank_statement_line_list

    def create_bank_statement(self):
        self.ensure_one()
        self = self.sudo()
        mk_instance_id = self.mk_instance_id
        bank_statement_obj = self.env['account.bank.statement']
        statement_id = bank_statement_obj.search([('shopify_ref', '=', self.report_id)], limit=1)
        if statement_id:
            statement_id.write({'shopify_payout_id': self.id, 'line_ids': self.prepare_bank_statement_line(statement_id=statement_id)})
            return statement_id
        name = f'{mk_instance_id.name} [{self.payout_date}] [{self.report_id}]'
        statement_line_list = self.prepare_bank_statement_line()
        vals = {'name': name,
                'shopify_ref': self.report_id,
                'shopify_payout_id': self.id,
                'journal_id': mk_instance_id.payout_journal_id.id,
                'date': self.payout_date,
                'currency_id': self.currency_id.id,
                'line_ids': statement_line_list,
                'balance_start': 0.0,
                'balance_end_real': 0.0}
        statement_id = bank_statement_obj.create(vals)
        return statement_id

    def prepare_payout_line_dict(self, transaction_dict, transaction_currency_id, mk_instance_id):
        order_id = self.env['sale.order']

        order_gid = (transaction_dict.get('associatedOrder') or {}).get('id')
        source_order_id = str(extract_numeric_id(order_gid)) if order_gid else False

        # Extract the numeric transaction ID
        transaction_gid = transaction_dict.get('id')
        transaction_id = str(extract_numeric_id(transaction_gid)) if transaction_gid else ''

        # Find the related Odoo Sale Order if it exists
        if source_order_id:
            order_id = self.env['sale.order'].search([('mk_id', '=', source_order_id), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)

        transaction_label = f'{order_id.name}-{transaction_id}' if order_id.name else f'{transaction_dict.get("type")}-{transaction_id or self.report_id}'

        amount = self.convert_str_to_float(transaction_dict.get('amount').get('amount'))
        fee = self.convert_str_to_float(transaction_dict.get('fee').get('amount'))
        net_amount = self.convert_str_to_float(transaction_dict.get('net').get('amount'))
        transaction_type_id = self.env['shopify.payout.transaction.type'].search(['|', ('transaction_type_code', '=', transaction_dict.get('type')), ('name', '=', transaction_dict.get('type'))])
        return {
            'transaction_id': transaction_id,
            'transaction_type_id': transaction_type_id.id or False,
            'currency_id': transaction_currency_id.id,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'source_order_id': source_order_id,
            'source_type': transaction_dict.get('source_type'),
            'processed_at': convert_shopify_datetime_to_utc(transaction_dict.get('transactionDate')),
            'order_id': order_id.id or False,
            'transaction_label': transaction_label,
        }

    def prepare_fee_line_dict(self, payout_dict, payout_currency_id):
        """
        Prepares a values dictionary for a 'fees' payout line.
        Args:
            payout_dict (dict): The main Shopify Payout object dictionary.
            payout_currency_id (Odoo record): The 'res.currency' record matching the payout's currency.

        Returns:
            dict: A dictionary of values ready for creating a 'fees' payout line.
            False: If the total calculated fee amount is zero.
        """
        summary = payout_dict.get('summary') or {}

        # Safely get each fee's data, then its amount
        charges_fee = self.convert_str_to_float(summary.get('chargesFee').get('amount'))
        refunds_fee = self.convert_str_to_float(summary.get('refundsFee').get('amount'))
        adjustments_fee = self.convert_str_to_float(summary.get('adjustmentsFee').get('amount'))
        fees_amount = charges_fee + refunds_fee + adjustments_fee

        if not fees_amount:
            return False

        payout_id = str(extract_numeric_id(payout_dict.get('id', "")))
        transaction_label = f'fees-{payout_id}'
        transaction_type_id = self.env['shopify.payout.transaction.type'].search(['|', ('transaction_type_code', '=', 'FEES'), ('name', '=', 'FEES')])
        return {
            'transaction_type_id': transaction_type_id.id,
            'currency_id': payout_currency_id.id,
            'amount': -fees_amount,
            'fee': 0.0,
            'net_amount': fees_amount,
            'transaction_label': transaction_label,
        }

    def shopify_import_payout_report(self, mk_instance_id, from_date=False, to_date=False):
        """
        Processes a single payout, creating the Odoo record and its lines.
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.

        Args:
            mk_instance_id (record): The marketplace instance record.
            from_date: The start date for the query.
            to_date: The end date for the query.

        1. Fetches all payouts within the date range.
        2. Loops through each payout and calls _process_single_payout to create records.
        3. After all records are created, calls _process_payout_statements to create and reconcile bank statements (if configured).
        4. Updates the last sync date on the instance.
        """
        currency_obj = self.env['res.currency']
        if not mk_instance_id.payout_journal_id:
            error_msg = "⚠️ Please define Payout Journal."
            mk_instance_id.with_context(active_tab_payout='payout').show_shopify_instance_redirect_warning(error_msg)
        payout_list, start_date, end_date = self.fetch_payout_from_shopify(mk_instance_id, from_date, to_date)
        payout_id_list = []
        for payout in payout_list:
            payout_id = str(extract_numeric_id(payout.get('id', "")))

            if not payout_id:
                _logger.warning(f"⚠️ Could not extract numeric ID from payout GID: {payout.get('id')}")
                return None

            existing_payout_id = self.search([('report_id', '=', payout_id), ('mk_instance_id', '=', mk_instance_id.id)])
            if existing_payout_id:
                continue

            currency_code = payout.get('net', {}).get('currencyCode', '')
            payout_currency_id = currency_obj.search([('name', '=', currency_code)], limit=1)
            if not payout_currency_id:
                break

            amount = self.convert_str_to_float(payout.get('net', {}).get('amount'))
            payout_vals = {'report_id': payout_id,
                           'currency_id': payout_currency_id.id,
                           'payout_date': convert_shopify_datetime_to_utc(payout.get('issuedAt')),
                           'amount': amount,
                           'mk_instance_id': mk_instance_id.id}

            transaction_list = self.fetch_transaction_of_payout(payout_id, mk_instance_id)
            transaction_vals_list = []
            for transaction in transaction_list:
                transaction_currency_code = transaction.get('amount', {}).get('currencyCode')
                transaction_currency_id = currency_obj.search([('name', '=', transaction_currency_code)], limit=1)
                transaction_vals_list.append((0, 0, self.prepare_payout_line_dict(transaction, transaction_currency_id, mk_instance_id)))

            fees_line_vals = self.prepare_fee_line_dict(payout, payout_currency_id)

            if fees_line_vals:
                transaction_vals_list.append((0, 0, fees_line_vals))
            payout_vals['payout_line_ids'] = transaction_vals_list
            payout_id = self.create(payout_vals)
            payout_id_list.append(payout_id.id)
            statement_id = payout_id.create_bank_statement()
            payout_id.bank_statement_id = statement_id.id
            # Task: T7715 - Auto payout reconciliation for Enterprise users.
            if mk_instance_id.is_payout_auto_process and mk_instance_id._is_module_installed('account_accountant'):
                payout_id.button_reconcile()
            elif mk_instance_id.is_payout_auto_process:
                _logger.warning(f"⚠️ Auto Reconcile is not supported in Community Edition.")
            self.env.cr.commit()
        if not to_date:
            mk_instance_id.payout_report_last_sync_date = end_date
        self.env.cr.commit()
        if payout_id_list:
            return mk_instance_id.action_open_model_view(payout_id_list, 'shopify.payout', 'Shopify Payout')
        return True

    def cron_auto_import_shopify_payout_report(self, mk_instance_id):
        try:
            cr = Registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))
            mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
            if mk_instance_id.state == 'confirmed':
                self.shopify_import_payout_report(mk_instance_id)
                _logger.info("import shopify payout process is finished and committed")
        except Exception:
            _logger.error("Error during import shopify payout report", exc_info=True)
            raise
        finally:
            try:
                self._cr.close()
            except Exception:
                pass
        return True

    def shopify_process_payout_report(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].sudo().browse(mk_instance_id)
        payout_ids = self.search([('mk_instance_id', '=', mk_instance_id.id), ('report_id', '!=', False), ('state', 'in', ['draft', 'posted', 'confirm'])])
        for payout_id in payout_ids:
            if payout_id.bank_statement_id.state != 'open':
                return True
            payout_id.reconcile_transactions(payout_id.bank_statement_id)
        return True

    def _convert_amount_currency(self, statement_line_id, aml_id):
        amount_currency = 0.0
        statement_currency = statement_line_id.currency_id or statement_line_id.statement_id.currency_id
        statement_company = statement_line_id.statement_id.company_id
        if aml_id.company_id.currency_id.id != statement_currency.id:
            amount_currency = aml_id.currency_id._convert(aml_id.amount_currency, statement_currency, statement_company, statement_line_id.date)
        elif aml_id.move_id.currency_id.id != statement_currency.id:
            amount_currency = aml_id.move_id.currency_id._convert(aml_id.balance, statement_currency, statement_company, statement_line_id.date)
        currency = aml_id.currency_id or aml_id.move_id.currency_id
        return currency, amount_currency

    def reconcile_invoices(self, statement_line_id, invoice_ids):
        paid_invoices = invoice_ids.filtered(lambda x: x.payment_state in ['paid', 'in_payment'])
        unpaid_invoices = invoice_ids.filtered(lambda x: x.payment_state == 'not_paid')
        reconciled_move_lines = unreconciled_move_lines = self.env['account.move.line']
        if paid_invoices:
            for invoice in paid_invoices:
                reconciled_payments = invoice._get_reconciled_payments()
                # Access line_ids via the move_id of the payment
                payment_lines = reconciled_payments.move_id.line_ids
                reconciled_move_lines |= payment_lines.filtered(lambda x: getattr(x, 'debit' if invoice.move_type == 'out_invoice' else 'credit', 0.0) != 0.0)
        total_amount = 0.0
        currency_ids = set([])
        for u_line in unpaid_invoices.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled):
            amount = u_line.balance
            if u_line.currency_id != statement_line_id.currency_id:
                amount = statement_line_id.amount
            total_amount += amount
            unreconciled_move_lines |= u_line

        for r_line in reconciled_move_lines:
            amount = r_line.balance
            if r_line.currency_id != statement_line_id.currency_id:
                amount = statement_line_id.amount
            elif r_line.amount_currency:
                currency, amount_currency = self._convert_amount_currency(statement_line_id, r_line)
                currency_ids.add(currency)
                if amount_currency:
                    amount = amount_currency
            total_amount += amount

        currency_ids = list(currency_ids)
        if round(statement_line_id.amount, 10) == round(total_amount, 10) and (not statement_line_id.currency_id or statement_line_id.currency_id.id == self.bank_statement_id.currency_id.id):
            if len(currency_ids) == 1 and not statement_line_id.currency_id:
                if currency_ids != statement_line_id.statement_id.currency_id:
                    statement_line_id.write({'currency_id': currency_ids.id})
            try:
                if reconciled_move_lines or unreconciled_move_lines:
                    statement_line_id.set_line_bank_statement_line(reconciled_move_lines.ids or unreconciled_move_lines.ids)
                    statement_line_id.move_id.message_post(body=_("This bank transaction has been automatically validated using the shopify payout auto reconcile process"))
            except Exception as e:
                statement_line_id.shopify_payout_line_id.write({'error_message': f'A error encountered while reconciling statement line : {e} '})
                statement_line_id.action_undo_reconciliation()

        if statement_line_id.is_reconciled:
            statement_line_id.shopify_payout_line_id.write({'error_message': False, 'warn_message': False})
        return True

    def reconcile_statement_line(self, st_line_id, payout_account_config_id):
        account_id = payout_account_config_id.account_id
        st_line_id.set_account_bank_statement_line(st_line_id.line_ids[-1].id, account_id.id)
        st_line_id.move_id.message_post(body=_("This bank transaction has been automatically validated using the shopify payout auto reconcile process"))

    def reconcile_transactions(self):
        statement_id = self.bank_statement_id
        for line_id in statement_id.line_ids.filtered(lambda x: not x.is_reconciled and x.shopify_payout_line_id):
            payout_line_id = line_id.shopify_payout_line_id
            if payout_line_id.transaction_type_id.transaction_type_code in ["CHARGE", "REFUND"]:
                order_id = payout_line_id.order_id
                if not order_id:
                    order_id = self.env['sale.order'].search([('mk_id', '=', payout_line_id.source_order_id), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
                invoice_ids = order_id.invoice_ids.filtered(
                    lambda x: x.state == 'posted' and x.move_type == INVOICE_AND_PAYMENT_TYPES[payout_line_id.transaction_type_id.transaction_type_code]['invoice_type'])
                if not invoice_ids:
                    continue
                self.reconcile_invoices(line_id, invoice_ids)
            else:
                payout_account_config_id = self.mk_instance_id.payout_account_config_ids.filtered(lambda x: x.transaction_type_id == payout_line_id.transaction_type_id)
                if not payout_account_config_id:
                    continue
                self.reconcile_statement_line(line_id, payout_account_config_id)
            self.env.cr.commit()
        return True

    def button_reconcile(self):
        """
        Task: T7715 - Ensure Auto Reconcile is available only for Enterprise users.
        """
        self.ensure_one()
        self = self.sudo()
        if not self.mk_instance_id._is_module_installed('account_accountant'):
            raise MarketplaceException(_("⚠️ Auto Reconcile is not supported in Community."))
        if self.state == 'draft':
            self.button_post()
        self.reconcile_transactions()
        return True

    def button_manual_reconcile(self):
        if hasattr(self.bank_statement_id, 'action_open_bank_reconcile_widget'):
            return getattr(self.bank_statement_id, 'action_open_bank_reconcile_widget')()
        raise MarketplaceException(_("⚠️ Reconciliation function not found to do manual reconciliation! Try auto reconciliation instead."))

    def button_post(self):
        self = self.sudo()
        for payout in self:
            if not payout.bank_statement_id:
                payout.bank_statement_id = self.create_bank_statement()
            payout.bank_statement_id.write({'line_ids': payout.prepare_bank_statement_line(statement_id=payout.bank_statement_id)})

    def button_reopen(self):
        self = self.sudo()
        self.payout_line_ids.filtered(lambda x: x.is_reconciled).button_undo_reconciliation()
        self.bank_statement_id.line_ids.unlink()
        self.bank_statement_id.unlink()

    def unlink(self):
        for payout in self:
            if payout.state != 'draft':
                raise MarketplaceException(_('⚠️ You cannot delete a processing or validated payout.'))
        return super().unlink()


class ShopifyPayoutLine(models.Model):
    _name = "shopify.payout.line"
    _description = "Shopify Payout Line"

    @api.depends('payout_id.bank_statement_id', 'payout_id.bank_statement_id.line_ids')
    def _compute_bank_statement_line(self):
        for record in self:
            record.bank_statement_line_id = record.payout_id.bank_statement_id.line_ids.filtered(lambda x: x.shopify_payout_line_id == record)

    @api.depends('source_order_id')
    def _compute_order_id(self):
        for record in self:
            record.order_id = self.env['sale.order'].search([('mk_id', '=', record.source_order_id), ('mk_instance_id', '=', record.payout_id.mk_instance_id.id)], limit=1)
            if record.order_id:
                record.warn_message = False

    payout_id = fields.Many2one("shopify.payout", "Payout", ondelete='cascade')
    transaction_id = fields.Char("Transaction ID")
    # transaction_type = fields.Selection(PAYOUT_TRANSACTION_TYPE, help="The type of the balance transaction", string="Transaction Type")
    transaction_type_id = fields.Many2one('shopify.payout.transaction.type', help="The type of the resource leading to the transaction.", string="Transaction Type")
    currency_id = fields.Many2one('res.currency', string="Currency")
    amount = fields.Float("Amount")
    fee = fields.Float("Fees")
    net_amount = fields.Float("Net Amount")
    source_order_id = fields.Char("Source Order ID", help="The id of the Order that this transaction ultimately originated from.")
    source_type = fields.Char("Source Type", help="The type of the resource leading to the transaction.")
    processed_at = fields.Datetime("Processed Date", help="The time the transaction was processed.")
    order_id = fields.Many2one("sale.order", string="Order Reference", compute="_compute_order_id")
    bank_statement_line_id = fields.Many2one("account.bank.statement.line", compute="_compute_bank_statement_line", store=True, string="Bank Statement Line")
    transaction_label = fields.Char(string="Label", help="Technical field that will use on label field while creating bank statement line.")

    # == Display purpose fields ==
    is_reconciled = fields.Boolean(string='Is Reconciled', related="bank_statement_line_id.is_reconciled")
    warn_message = fields.Text(string="Warning Message", copy=False)
    error_message = fields.Text(string="Error Message", copy=False)

    def button_undo_reconciliation(self):
        self = self.sudo()
        for record in self:
            record.bank_statement_line_id.action_undo_reconciliation()

    def action_open_recon_payout_line(self):
        self.ensure_one()
        self = self.sudo()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            name=self.bank_statement_line_id.name,
            default_context={
                'default_statement_id': self.bank_statement_line_id.id,
                'default_journal_id': self.bank_statement_line_id.journal_id.id,
                'default_st_line_id': self.bank_statement_line_id.id,
                'search_default_id ': self.bank_statement_line_id.id,
            },
        )
