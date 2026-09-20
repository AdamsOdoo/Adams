"""Real Odoo browser acceptance with disposable finance fixtures."""
import json

from odoo import Command, fields
from odoo.tests import tagged
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
                    const profitability = root.querySelector('#adams-group-profitability > .adams_grid');
                    if (profitability.children.length !== 4) throw new Error('Reference requires four primary profitability cards');
                    if (root.querySelectorAll('.adams_nav button').length !== 6) throw new Error('Reference requires six department tabs');
                    const columns = getComputedStyle(profitability).gridTemplateColumns.split(' ').length;
                    if ((WIDTH === 390 && columns !== 2) || (WIDTH === 320 && columns !== 1) || (WIDTH >= 1440 && columns !== 4)) throw new Error('Incorrect reference KPI column count');
                    if (!root.querySelector('.adams_profit_grid .adams_performance')) throw new Error('Missing reference performance-context panel');
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
                    console.log('test successful');
                })().catch(error => console.error(error));
                '''.replace('HEADING', json.dumps(heading)).replace('DIRECTION', json.dumps(direction)).replace('WIDTH', str(width))
                self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=90)
