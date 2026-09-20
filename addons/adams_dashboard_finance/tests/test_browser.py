"""Real Odoo browser acceptance with disposable finance fixtures."""
import json
from itertools import product
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import new_test_user, tagged
from odoo.tests.common import ChromeBrowser
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDashboardFinanceBrowser(AccountTestInvoicingHttpCommon):
    def test_browser_roles_and_direct_rpc_boundaries(self):
        company = self.env.company
        foreign = self.env['res.company'].create({'name': 'Browser unauthorized company'})
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        roles = [
            ('finance', 'account.group_account_readonly,adams_executive_dashboard.group_dashboard_user'),
            ('sales', 'sales_team.group_sale_salesman,adams_executive_dashboard.group_dashboard_user'),
            ('dashboard_only', 'adams_executive_dashboard.group_dashboard_user'),
            ('no_dashboard', 'account.group_account_readonly'),
        ]
        today = fields.Date.today().isoformat()
        options = {'company_id': company.id, 'date_from': today, 'date_to': today, 'as_of': today}
        for role, groups in roles:
            user = new_test_user(self.env, login='dashboard_browser_' + role,
                groups='base.group_user,' + groups, company_id=company.id,
                company_ids=[Command.set(company.ids)])
            user.group_ids -= self.env.ref('base.group_allow_export')
            code = '''
            (async () => {
                const call = async (method, args) => {
                    const response = await fetch('/web/dataset/call_kw/adams.executive.dashboard/' + method, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({jsonrpc:'2.0', method:'call', id:1,
                            params:{model:'adams.executive.dashboard', method, args,
                                kwargs:{context:{allowed_company_ids:[OPTIONS.company_id]}}}})
                    });
                    return response.json();
                };
                const bootstrap = await call('get_bootstrap', []);
                if (ROLE === 'no_dashboard') {
                    if (!bootstrap.error) throw new Error('Direct dashboard RPC must deny no-dashboard user');
                } else {
                    if (bootstrap.error) throw new Error('Authorized dashboard user must load bootstrap');
                    const finance = await call('get_section', ['finance', OPTIONS]);
                    if (finance.error) throw new Error('Finance must expose an explicit availability state');
                    const expected = ROLE === 'finance' ? 'not_configured' : 'restricted';
                    if (!finance.result.items.every(item => item.value === null && item.status === expected))
                        throw new Error('Role must not receive unauthorized or invented financial values');
                    for (let attempt = 0; attempt < 200; attempt++) {
                        if (document.querySelector('.adams_card .adams_source_button')) break;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    if (!document.querySelector('.adams_card .adams_source_button'))
                        throw new Error('Authorized role dashboard did not render');
                }
                const deniedCompany = await call('get_section', ['finance', {...OPTIONS, company_id:FOREIGN}]);
                if (!deniedCompany.error) throw new Error('Wrong company RPC must be rejected');
                const exported = await call('export_breakdown', ['invoiced_sales','customer',OPTIONS]);
                if (!exported.error) throw new Error('Export-disabled user must be rejected by direct RPC');
                console.log('test successful');
            })().catch(error => console.error(error));
            '''.replace('OPTIONS', json.dumps(options)).replace('ROLE', json.dumps(role)).replace('FOREIGN', str(foreign.id))
            self.browser_js(f'/odoo/action-{action.id}', code, login=user.login, timeout=60)

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
        for amount, days in [(129.45, 1), (999, 31)]:
            self.env['account.move'].create({
                'move_type': 'in_invoice', 'partner_id': self.partner_a.id,
                'invoice_date': today, 'date': today, 'invoice_payment_term_id': False,
                'invoice_date_due': today + timedelta(days=days),
                'journal_id': self.company_data['default_journal_purchase'].id,
                'invoice_line_ids': [Command.create({
                    'name': 'Browser supplier installment fixture', 'quantity': 1,
                    'price_unit': amount, 'account_id': self.company_data['default_account_expense'].id,
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
            for theme, width in product(('light', 'dark'), (320, 390, 768, 1024, 1440, 1920)):
                self.env.user.color_scheme = theme
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
                    if (getComputedStyle(root).colorScheme !== THEME) throw new Error('Dashboard must follow native Odoo theme');
                    const surface = getComputedStyle(card).backgroundColor;
                    if (surface !== (THEME === 'dark' ? 'rgb(38, 42, 54)' : 'rgb(255, 255, 255)')) throw new Error('Card has incorrect theme surface');
                    if (root.querySelectorAll('.adams_header_actions button').length !== 3) throw new Error('Reference view controls are missing');
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
                    const windows = aging.querySelectorAll('.adams_supplier_windows .adams_card');
                    if (windows.length !== 4) throw new Error('Four approved supplier windows must render');
                    const paymentValue = new Intl.NumberFormat(document.documentElement.lang || 'en', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(129.45);
                    if (windows[2].querySelector('.adams_value').textContent.trim() !== paymentValue ||
                        windows[3].querySelector('.adams_value').textContent.trim() !== paymentValue)
                        throw new Error('Native supplier window must show 129.45 excluding day 31');
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
                    // Exercise all department navigation in the rendered client.
                    // Restricted native departments must still reflow correctly.
                    for (const key of ['sales', 'crm', 'inventory', 'procurement', 'hr', 'finance']) {
                        const keys = ['finance', 'sales', 'crm', 'inventory', 'procurement', 'hr'];
                        root.querySelectorAll('.adams_nav button')[keys.indexOf(key)].click();
                        await wait(() => root.querySelector('#adams-' + key)?.querySelector('.adams_section_toggle')?.getAttribute('aria-expanded') === 'true',
                            'Department must expand: ' + key);
                        if (root.scrollWidth > root.clientWidth + 2) throw new Error('Department overflow: ' + key);
                    }
                    if (WIDTH === 1440 && DIRECTION === 'ltr') {
                        const open = card.querySelector('button[aria-label="Open native report"]');
                        open.click();
                        await wait(() => !document.querySelector('.o_adams_dashboard') &&
                            document.body.innerText.includes('100.00'), 'Native report must display independently rendered fixture value');
                        const back = await wait(() => document.querySelector('a[href="/odoo/action-ACTION_ID"]'),
                            'Native financial report must expose dashboard breadcrumb');
                        back.click();
                        const restored = await wait(() => document.querySelector('.o_adams_dashboard .adams_value')?.textContent.trim() === expected
                            && document.querySelector('.o_adams_dashboard'), 'Financial report return must reload the known native value');
                        const restoredDates = [...restored.querySelectorAll('.adams_filters input')].map(input => input.value);
                        if (JSON.stringify(restoredDates) !== JSON.stringify(EXPECTED_DATES))
                            throw new Error('Financial report return changed applied dates');
                        const paymentOpen = await wait(() => document.querySelectorAll('.adams_supplier_windows .adams_card')[2]?.querySelector('button'),
                            'Payment window drilldown must load after financial report return');
                        paymentOpen.click();
                        await wait(() => !document.querySelector('.o_adams_dashboard') &&
                            document.body.innerText.includes('129.45'), 'Scoped native payment report must render 129.45');
                        if (!document.body.innerText.includes('Supplier bills due in 7 days'))
                            throw new Error('Native payment report must identify its restricted window');
                        if (document.body.innerText.includes('1,128.45'))
                            throw new Error('Native payment drilldown lost its due-window filter');
                        const paymentBack = await wait(() => document.querySelector('a[href="/odoo/action-ACTION_ID"]'),
                            'Payment report must expose dashboard breadcrumb');
                        paymentBack.click();
                        await wait(() => document.querySelectorAll('.adams_supplier_windows .adams_card').length === 4,
                            'Payment return must restore the supplier windows');
                    }
                    if (WIDTH === 768 || WIDTH === 1024) liquidity.scrollIntoView({block: 'start'});
                    console.log('test successful');
                })().catch(error => console.error(error));
                '''.replace('THEME', json.dumps(theme)).replace('HEADING', json.dumps(heading)).replace('DIRECTION', json.dumps(direction)).replace('WIDTH', str(width)).replace('ACTION_ID', str(action.id)).replace('EXPECTED_DATES', json.dumps([today.replace(day=1).isoformat(), today.isoformat(), today.isoformat()]))
                original_wait = ChromeBrowser._wait_code_ok

                def capture_success(browser, *args, **kwargs):
                    result = original_wait(browser, *args, **kwargs)
                    # Instrument only evidence capture after the real browser assertions.
                    # Business data, rendering and test success are never mocked.
                    browser.take_screenshot(prefix=f'dashboard_{lang}_{theme}_{width}_').result(timeout=20)
                    return result

                with patch.object(ChromeBrowser, '_wait_code_ok', capture_success):
                    self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=90)
