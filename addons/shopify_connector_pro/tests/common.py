# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Shared test helpers and mixins for the Shopify Connector test suite.

The ShopifyAccountingMixin sets up the accounting prerequisites (receivable,
payable, income accounts, sales journal) that Odoo 19 requires before any
invoice / payment operation can succeed.  Without these, the SQL-level
``account_move_line_check_accountable_required_fields`` constraint will reject
INSERT statements on ``account.move.line``.

Usage — just inherit the mixin *before* TransactionCase::

    from .common import ShopifyAccountingMixin

    class TestMyFeature(ShopifyAccountingMixin, TransactionCase):
        def setUp(self):
            super().setUp()
            # self.receivable_account, self.payable_account,
            # self.income_account are ready to use.
            # Helper methods are also available:
            #   self._create_partner(name, email)
            #   self._set_product_income_account(product)
"""


class ShopifyAccountingMixin:
    """Mixin that provides accounting setup for Shopify connector tests.

    Sets up:
    - Receivable account (``self.receivable_account``)
    - Payable account (``self.payable_account``)
    - Income account (``self.income_account``)
    - Sales journal (created if missing)

    And exposes helper methods to apply these to partners and products.
    """

    def setUp(self):
        super().setUp()
        self._setup_accounting()

    # ------------------------------------------------------------------
    # Core setup
    # ------------------------------------------------------------------

    def _setup_accounting(self):
        """Ensure all required accounting objects exist for the test company."""
        company = self.env.company

        # Sales journal
        if not self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1,
        ):
            self.env['account.journal'].create({
                'name': 'Test Sales Journal',
                'type': 'sale',
                'code': 'TSHP',
                'company_id': company.id,
            })

        # Receivable
        self.receivable_account = self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.receivable_account:
            self.receivable_account = self.env['account.account'].create({
                'name': 'Test Receivable',
                'code': 'TREC',
                'account_type': 'asset_receivable',
                'reconcile': True,
                'company_ids': [(6, 0, [company.id])],
            })

        # Payable
        self.payable_account = self.env['account.account'].search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.payable_account:
            self.payable_account = self.env['account.account'].create({
                'name': 'Test Payable',
                'code': 'TPAY',
                'account_type': 'liability_payable',
                'reconcile': True,
                'company_ids': [(6, 0, [company.id])],
            })

        # Income
        self.income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.income_account:
            self.income_account = self.env['account.account'].create({
                'name': 'Test Income Account',
                'code': 'TINC',
                'account_type': 'income',
                'company_ids': [(6, 0, [company.id])],
            })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_accounting_partner(self, name, email=None):
        """Create a partner with receivable and payable accounts set."""
        vals = {
            'name': name,
            'property_account_receivable_id': self.receivable_account.id,
            'property_account_payable_id': self.payable_account.id,
        }
        if email:
            vals['email'] = email
        return self.env['res.partner'].create(vals)

    def _set_product_income_account(self, product):
        """Set the income account on both the product category and template."""
        product.categ_id.property_account_income_categ_id = self.income_account
        product.product_tmpl_id.property_account_income_id = self.income_account
