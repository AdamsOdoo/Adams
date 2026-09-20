"""Real Odoo browser acceptance with disposable finance fixtures."""
import json
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import ChromeBrowser
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDashboardFinanceBrowser(AccountTestInvoicingHttpCommon):
    def test_bilingual_finance_reflow_and_native_drilldown(self):
        today = fields.Date.today()
        self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner_a.id,
            'invoice_date': today, 'date': today,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'name': 'Browser native revenue fixture', 'quantity': 1, 'price_unit': 100,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()],
            })],
        }).action_post()
        mapping = self.env['adams.dashboard.finance.mapping'].create({
            'company_id': self.env.company.id, 'metric': 'revenue',
            'report_id': self.env.ref('account_reports.profit_and_loss').id,
            'expression_id': self.env.ref('account_reports.account_financial_report_revenue0_balance').id,
            'definition_note': 'Disposable browser fixture approval; not customer accounting policy.',
        })
        mapping.action_approve()
        mapping_model = self.env['adams.dashboard.finance.mapping']
        cash_line = self.env.ref('account_reports.account_financial_report_bank_view0')
        cash_mapping = mapping_model.create({
            'company_id': self.env.company.id, 'metric': 'cash',
            'report_id': self.env.ref('account_reports.balance_sheet').id,
            'expression_id': cash_line.expression_ids.filtered(lambda expr: expr.label == 'balance').id,
            'cash_detail_report_id': self.env.ref('account_reports.general_ledger_report').id,
            'cash_detail_expression_id': self.env.ref('account_reports.general_ledger_line_balance').id,
            'cash_flow_report_id': self.env.ref('account_reports.cash_flow_report').id,
            'definition_note': 'Disposable browser cash fixture; not customer accounting policy.',
        })
        cash_mapping.action_approve()
        for metric, prefix in [('receivables', 'aged_receivable'), ('payables', 'aged_payable')]:
            aging_mapping = mapping_model.create({
                'company_id': self.env.company.id, 'metric': metric,
                'report_id': self.env.ref(f'account_reports.{prefix}_report').id,
                'expression_id': self.env.ref(f'account_reports.{prefix}_line_total').id,
                'definition_note': 'Disposable browser aging fixture; not customer accounting policy.',
            })
            aging_mapping.action_approve()
        language = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'ar_001')])
        if not language.active:
            self.env['base.language.install'].create({'lang_ids': [Command.set(language.ids)]}).lang_install()
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        for lang, heading, direction in [('en_US', 'Accounting revenue', 'ltr'), ('ar_001', 'الإيرادات المحاسبية', 'rtl')]:
            self.env.user.lang = lang
            for width in (320, 390, 768, 1024, 1440, 1920):
                self.browser_size = f'{width}x900'
                # No mocked reports or browser RPCs: interact with rendered Odoo UI.
                code = '''
                (async () => {
                    const wait = async (test, message) => {
                        for (let i = 0; i < 250; i++) {
                            const result = test(); if (result) return result;
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }
                        throw new Error(message);
                    };
                    const heading = HEADING;
                    const expected = new Intl.NumberFormat(document.documentElement.lang || 'en', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(100);
                    const card = await wait(() => [...document.querySelectorAll('.adams_card')]
                        .find(node => node.querySelector('h3')?.textContent.trim() === heading &&
                            node.querySelector('.adams_value')?.textContent.trim() === expected),
                        'Native revenue fixture must render 100.00 in the selected language');
                    const root = document.querySelector('.o_adams_dashboard');
                    if (getComputedStyle(root).direction !== DIRECTION) throw new Error('Incorrect text direction');
                    if (root.scrollWidth > root.clientWidth + 2) throw new Error('Dashboard has horizontal page overflow');
                    if (WIDTH < 760) {
                        const toggle = root.querySelector('.adams_mobile_menu');
                        toggle.click();
                        const menu = await wait(() => root.querySelector('.adams_sidebar.is-open'), 'Mobile navigation must open');
                        await wait(() => menu.contains(document.activeElement), 'Mobile navigation must receive focus');
                        document.activeElement.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
                        await wait(() => !root.querySelector('.adams_sidebar.is-open'), 'Escape must dismiss mobile navigation');
                        if (document.activeElement !== toggle) throw new Error('Mobile navigation must return focus');
                        toggle.click();
                        await wait(() => root.querySelector('.adams_sidebar.is-open'), 'Mobile navigation must reopen');
                        root.querySelector('.adams_workspace_close').click();
                        await wait(() => !root.querySelector('.adams_sidebar.is-open'), 'Close control must dismiss mobile navigation');
                    }
                    const profitability = root.querySelector('#adams-group-profitability > .adams_grid');
                    if (profitability.children.length !== 4) throw new Error('Reference requires four primary profitability cards');
                    if (root.querySelectorAll('.adams_nav button').length !== 6) throw new Error('Reference requires six department tabs');
                    const columns = getComputedStyle(profitability).gridTemplateColumns.split(' ').length;
                    if ((WIDTH === 390 && columns !== 2) || (WIDTH === 320 && columns !== 1) || (WIDTH >= 1440 && columns !== 4)) throw new Error('Incorrect reference KPI column count');
                    if (!root.querySelector('.adams_profit_grid .adams_performance')) throw new Error('Missing reference performance-context panel');
                    const liquidity = root.querySelector('#adams-group-liquidity');
                    if (liquidity.querySelector('.adams_grid').children.length !== 3) throw new Error('Reference requires three liquidity cards');
                    await wait(() => liquidity.querySelector('.adams_bank_row button'), 'Native cash account balances must load automatically');
                    if (liquidity.querySelectorAll('.adams_cash_bridge strong').length !== 3) throw new Error('Native cash bridge must show opening, movement and closing');
                    const aging = root.querySelector('#adams-group-working-capital');
                    if (aging.querySelectorAll('.adams_aging_list').length !== 2) throw new Error('Both native aging panels must be visible');
                    if (!aging.querySelector('.adams_aging_list').innerText.includes(expected)) throw new Error('Native receivable bucket must contain the invoice value');
                    for (const date of root.querySelectorAll('.adams_card_date')) {
                        if (getComputedStyle(date).direction !== 'ltr') throw new Error('ISO date ranges must preserve order in RTL');
                    }
                    const source = card.querySelector('.adams_source_button');
                    source.click();
                    const drawer = await wait(() => root.querySelector('dialog[open]'), 'Source drawer must open');
                    if (!drawer.innerText.includes(expected)) throw new Error('Source drawer must retain precise native value');
                    if (!drawer.contains(document.activeElement)) throw new Error('Source drawer must receive focus');
                    if (drawer.getBoundingClientRect().width > WIDTH + 2) throw new Error('Source drawer exceeds viewport');
                    drawer.querySelector('header button').click();
                    await wait(() => !root.querySelector('dialog[open]'), 'Source drawer must close');
                    const filter = root.querySelector('.adams_filters button');
                    filter.focus();
                    if (document.activeElement !== filter) throw new Error('Filter button is not focusable');
                    if (WIDTH === 1440 && DIRECTION === 'ltr') {
                        const open = card.querySelector('button[aria-label="Open native report"]');
                        open.click();
                        await wait(() => !document.querySelector('.o_adams_dashboard') &&
                            document.body.innerText.includes('100.00'), 'Native report must display independently rendered fixture value');
                    }
                    if (WIDTH === 768 || WIDTH === 1024) liquidity.scrollIntoView({block: 'start'});
                    console.log('test successful');
                })().catch(error => console.error(error));
                '''.replace('HEADING', json.dumps(heading)).replace('DIRECTION', json.dumps(direction)).replace('WIDTH', str(width))
                original_wait = ChromeBrowser._wait_code_ok

                def capture_success(browser, *args, **kwargs):
                    result = original_wait(browser, *args, **kwargs)
                    # Instrument only evidence capture after the real browser assertions.
                    # Business data, rendering and test success are never mocked.
                    browser.take_screenshot(prefix=f'dashboard_{lang}_{width}_').result(timeout=20)
                    return result

                with patch.object(ChromeBrowser, '_wait_code_ok', capture_success):
                    self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=90)
