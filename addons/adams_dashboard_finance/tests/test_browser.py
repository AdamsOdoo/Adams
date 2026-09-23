"""Real Odoo browser acceptance with disposable finance fixtures."""
import base64
import hashlib
import io
import json
import logging
import os
import subprocess
from pathlib import Path
import tempfile
import time
from uuid import uuid4
from itertools import product
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, api, fields
from odoo.exceptions import UserError
from odoo.tools import config
from odoo.tools.pdf import PdfReader
from odoo.tests import new_test_user, tagged
from odoo.tests.common import ChromeBrowser
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDashboardFinanceBrowser(AccountTestInvoicingHttpCommon):
    def test_browser_hr_retry_preserves_scope_after_one_rpc_failure(self):
        if 'hr.employee' not in self.env:
            self.skipTest('HR is optional; this browser recovery fixture requires installed HR')
        self.env.company.adams_dashboard_hr = True
        user = new_test_user(self.env, login='dashboard_hr_recovery',
            groups='base.group_user,hr.group_hr_user,account.group_account_readonly,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)],
            lang='en_US', tz='UTC')
        employee = self.env['hr.employee'].with_user(user).create({
            'name': 'Dashboard recovery employee', 'company_id': self.env.company.id})
        today = fields.Date.today()
        period = {'date_from': (today - timedelta(days=3)).isoformat(), 'date_to': today.isoformat()}
        model = type(self.env['adams.executive.dashboard'])
        original = model.get_hr_workspace
        attempts = []

        @api.model
        def fail_once(recordset, options, tab='overview', filters=None, offset=0):
            if (recordset.env.uid == user.id and tab == 'employees'
                    and (filters or {}).get('search')):
                attempts.append({'options': dict(options), 'filters': dict(filters), 'offset': offset})
                if len(attempts) == 1:
                    # UserError is an expected RPC failure, not an unexpected
                    # server ERROR or a customer/staging fault injection.
                    raise UserError('Controlled disposable HR recovery failure')
            return original(recordset, options, tab, filters, offset)

        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        self.browser_size = '1440x900'
        code = r"""(async () => {
            const wait = async (fn, message) => {
                for (let i=0;i<250;i++) { const value=fn(); if(value)return value; await new Promise(r=>setTimeout(r,100)); }
                throw new Error(message);
            };
            const root = await wait(()=>document.querySelector('.o_adams_dashboard .adams_card')?.closest('.o_adams_dashboard'), 'Initial finance must render');
            const initialDocument = document, initialTimeOrigin = performance.timeOrigin;
            const financeValues = () => [...root.querySelectorAll('#adams-finance .adams_card h3, #adams-finance .adams_card .adams_value')].map(node=>node.textContent.trim());
            const financeText = JSON.stringify(financeValues());
            root.querySelector('.adams_side_link[data-section="hr"]').click();
            const hr = await wait(()=>root.querySelector('#adams-hr .adams_hr_tabs')?.closest('#adams-hr'), 'HR navigation must render');
            await wait(()=>!hr.querySelector('[role="status"]'), 'HR overview must settle');
            hr.querySelectorAll('.adams_hr_tabs button')[4].click();
            await wait(()=>hr.querySelector('.adams_hr_filters'), 'Employee filters must render');
            const periodForm = hr.querySelector('.adams_hr_period');
            for (const [name,value] of Object.entries(PERIOD)) {
                const input=periodForm.querySelector('[name="'+name+'"]');
                input.value=value; input.dispatchEvent(new Event('change',{bubbles:true}));
            }
            await new Promise(resolve=>requestAnimationFrame(resolve));
            periodForm.requestSubmit();
            await wait(()=>periodForm.querySelector('button').disabled && hr.querySelector('.adams_hr_filters') && !hr.querySelector('[role="status"]'), 'Selected period must apply');
            const filters=hr.querySelector('.adams_hr_filters'), search=filters.querySelector('input[type="search"]');
            search.value=EMPLOYEE; search.dispatchEvent(new Event('input',{bubbles:true}));
            await new Promise(resolve=>requestAnimationFrame(resolve));
            const liveFilters=await wait(()=>root.querySelector('#adams-hr .adams_hr_filters input[type="search"]')?.value===EMPLOYEE &&
                root.querySelector('#adams-hr .adams_hr_filters'), 'Employee search must remain in the live form');
            liveFilters.requestSubmit();
            const error=await wait(()=>root.querySelector('#adams-hr .adams_message[role="alert"]'), 'One-shot RPC failure must show local HR error');
            if(!error.innerText.includes('other departments remain available'))throw new Error('Failure did not remain local');
            root.querySelector('.adams_side_link[data-section="finance"]').click();
            await wait(()=>root.querySelector('#adams-finance'), 'Finance must remain navigable during HR error');
            if(JSON.stringify(financeValues())!==financeText)throw new Error('HR failure changed successful finance data');
            root.querySelector('.adams_side_link[data-section="hr"]').click();
            const retry=await wait(()=>root.querySelector('#adams-hr .adams_message[role="alert"] button'), 'Returning HR must retain explicit Retry');
            retry.click();
            await wait(()=>[...root.querySelectorAll('#adams-hr .adams_hr_person')].some(node=>node.innerText.includes(EMPLOYEE)), 'Retry must recover native employee row');
            const restored=root.querySelector('#adams-hr');
            if(restored.querySelector('[role="alert"]'))throw new Error('Recovery retained error state');
            if(restored.querySelector('.adams_hr_filters input[type="search"]').value!==EMPLOYEE)throw new Error('Retry lost employee filter');
            for(const [name,value] of Object.entries(PERIOD)) {
                if(restored.querySelector('.adams_hr_period [name="'+name+'"]').value!==value)throw new Error('Retry lost selected period');
            }
            if(document!==initialDocument || performance.timeOrigin!==initialTimeOrigin || document.querySelector('.o_adams_dashboard')!==root)
                throw new Error('Recovery reloaded the document or whole dashboard');
            console.log('test successful');
        })().catch(error=>console.error(error));""".replace('PERIOD', json.dumps(period)).replace('EMPLOYEE', json.dumps(employee.name))
        with patch.object(model, 'get_hr_workspace', fail_once):
            self.browser_js(f'/odoo/action-{action.id}', code, login=user.login, timeout=75)
        self.assertEqual(len(attempts), 2, 'Exactly one failed request followed by its successful Retry')
        self.assertEqual(attempts[0], attempts[1], 'Retry must preserve the exact company, period, filter and page')
        self.assertEqual(attempts[1]['filters']['search'], employee.name)
        self.assertEqual(attempts[1]['options']['company_id'], self.env.company.id)
        for key, value in period.items():
            self.assertEqual(attempts[1]['options'][key], value)

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
                const summary = await call('export_summary', [OPTIONS]);
                if (!summary.error) throw new Error('Export-disabled user must not export a summary');
                console.log('test successful');
            })().catch(error => console.error(error));
            '''.replace('OPTIONS', json.dumps(options)).replace('ROLE', json.dumps(role)).replace('FOREIGN', str(foreign.id))
            self.browser_js(f'/odoo/action-{action.id}', code, login=user.login, timeout=60)

    def test_bilingual_finance_reflow_and_native_drilldown(self):
        self.partner_a.name = 'Dashboard Search Fixture'
        # These native rights and records exist only in this rollback-isolated
        # browser fixture. The independent negative-role test stays unchanged.
        stock_category = False
        if 'sale.order' in self.env:
            self.env.user.group_ids |= self.env.ref('sales_team.group_sale_manager')
        if 'stock.quant' in self.env:
            self.env.user.group_ids |= self.env.ref('stock.group_stock_manager')
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id)], limit=1)
            self.assertTrue(warehouse, 'Installed stock fixture requires its company warehouse')
            location = self.env['stock.location'].create({
                'name': 'Dashboard shelf / رف العرض', 'usage': 'internal',
                'location_id': warehouse.lot_stock_id.id, 'company_id': self.env.company.id,
            })
            stock_category = self.env['product.category'].create({'name': 'Dashboard visual stock'})
            stock_products = self.env['product.product'].create([{
                'name': f'Dashboard stock {index:02} / شامبو العرض',
                'default_code': f'DASH-VIS-{index:02}', 'is_storable': True,
                'company_id': self.env.company.id, 'categ_id': stock_category.id,
            } for index in range(27)])
            for index, stock_product in enumerate(stock_products):
                self.env['stock.quant']._update_available_quantity(stock_product, location, index + 1)
            self.env.flush_all()
        employee = False
        if 'hr.employee' in self.env:
            self.env.user.group_ids |= self.env.ref('hr.group_hr_user')
            department = self.env['hr.department'].create({
                'name': 'Dashboard department / قسم العرض', 'company_id': self.env.company.id})
            employee = self.env['hr.employee'].create({'name': '000 Dashboard work profile fixture',
                                                       'company_id': self.env.company.id,
                                                       'department_id': department.id})
        today = fields.Date.today()
        hr_start = today - timedelta(days=1)
        hr_end = today + timedelta(days=6)
        self.env.user.tz = 'UTC'
        if employee and 'hr.attendance' in self.env:
            self.env.user.group_ids |= self.env.ref('hr_attendance.group_hr_attendance_manager')
            self.env['hr.attendance'].create({'employee_id': employee.id,
                'check_in': fields.Datetime.to_datetime(hr_start) + timedelta(hours=8)})
        if employee and 'hr.leave' in self.env:
            self.env.user.group_ids |= self.env.ref('hr_holidays.group_hr_holidays_manager')
            leave_employee = self.env['hr.employee'].create({
                'name': '001 Dashboard leave fixture', 'company_id': self.env.company.id})
            leave_type = self.env['hr.leave.type'].create({'name': 'Dashboard native leave',
                'requires_allocation': False, 'leave_validation_type': 'no_validation'})
            leave = self.env['hr.leave'].create({'employee_id': leave_employee.id,
                'holiday_status_id': leave_type.id, 'request_date_from': today, 'request_date_to': hr_end})
            if leave.state != 'validate':
                leave.action_validate()
        if employee and 'planning.slot' in self.env:
            self.env.user.group_ids |= self.env.ref('planning.group_planning_manager')
            start = fields.Datetime.to_datetime(hr_start)
            self.env['planning.slot'].create([
                {'company_id': self.env.company.id, 'resource_id': employee.resource_id.id,
                 'state': 'published', 'start_datetime': start + timedelta(hours=22),
                 'end_datetime': start + timedelta(days=1, hours=6)},
                {'company_id': self.env.company.id, 'state': 'draft',
                 'start_datetime': start + timedelta(days=2, hours=8),
                 'end_datetime': start + timedelta(days=2, hours=16)},
                {'company_id': self.env.company.id, 'state': 'published',
                 'start_datetime': start + timedelta(days=3, hours=8),
                 'end_datetime': start + timedelta(days=3, hours=16)},
            ])
        self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner_a.id,
            'invoice_date': today, 'date': today,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'name': 'Browser native revenue fixture', 'product_id': self.product_a.id, 'quantity': 1, 'price_unit': 100,
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
                'partner_ledger_report_id': self.env.ref('account_reports.partner_ledger_report').id,
                'definition_note': 'Disposable browser aging fixture; not customer accounting policy.',
            })
            aging_mapping.action_approve()
        language = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'ar_001')])
        if not language.active:
            self.env['base.language.install'].create({'lang_ids': [Command.set(language.ids)]}).lang_install()
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        screenshot_source = Path(config['screenshots']) / self.env.cr.dbname / 'screenshots'
        existing_screenshots = set(screenshot_source.glob('*.png'))
        capture_prefixes = []
        captured_pdfs = []
        viewports = [(320, 900), (390, 900), (768, 900), (1024, 900), (1366, 768), (1440, 900), (1920, 1080)]
        for lang, heading, direction in [('en_US', 'Accounting revenue', 'ltr'), ('ar_001', 'الإيرادات المحاسبية', 'rtl')]:
            self.env.user.lang = lang
            for theme, (width, height) in product(('light', 'dark'), viewports):
                self.env.user.color_scheme = theme
                self.browser_size = f'{width}x{height}'
                prefixes = ['dashboard', 'polish_sales', 'polish_inventory', 'polish_procurement',
                            'polish_crm', 'polish_product_ranking', 'polish_order_ranking',
                            'polish_recent_orders', 'polish_recent_quotations', 'polish_recent_invoices', 'polish_fulfillment',
                            'hr_overview', 'hr_attendance', 'hr_time_off', 'hr_shifts', 'hr_employees']
                if employee:
                    prefixes += ['hr_profile']
                if stock_category:
                    prefixes += ['polish_inventory_table', 'polish_inventory_page2']
                capture_prefixes.extend(f'{prefix}_{lang}_{theme}_{width}_' for prefix in prefixes)
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
                    // DOM click() ignores covering elements. Test the real browser
                    // hit target before clicking a control inside a card-wide link.
                    const assertHitTarget = async (control, label) => {
                        control.scrollIntoView({block: 'center', inline: 'nearest'});
                        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                        const rect = control.getBoundingClientRect();
                        const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
                        if (!rect.width || !rect.height || !target || (target !== control && !control.contains(target)))
                            throw new Error(label + ' is covered by a different hit target: ' + (target?.className || target?.tagName));
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
                    const paper = getComputedStyle(root).getPropertyValue('--adams-paper').trim();
                    const sample = document.createElement('span'); sample.style.backgroundColor = paper; root.append(sample);
                    if (surface !== getComputedStyle(sample).backgroundColor) throw new Error('Card must use the selected appearance surface');
                    sample.remove();
                    if (root.querySelectorAll('.adams_header > .adams_header_actions button').length !== 3) throw new Error('Reference view/export/print controls are missing');
                    if (getComputedStyle(root).direction !== DIRECTION) throw new Error('Incorrect text direction');
                    if (root.scrollWidth > root.clientWidth + 2) throw new Error('Dashboard has horizontal page overflow');
                    const scopeDates = [...root.querySelectorAll('.adams_applied_period bdi, .adams_balance_scope > bdi')];
                    if (scopeDates.length !== 3) throw new Error('Applied filter summary must show three individual dates');
                    if (scopeDates.some(date => date.getClientRects().length !== 1)) throw new Error('Applied filter summary split an individual date');
                    if (WIDTH <= 900) {
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
                    if ((WIDTH === 390 && columns !== 2) || (WIDTH === 320 && columns !== 2) || (WIDTH >= 1440 && columns !== 4)) throw new Error('Incorrect reference KPI column count');
                    if (!root.querySelector('.adams_profit_grid .adams_performance')) throw new Error('Missing reference performance-context panel');
                    const liquidity = root.querySelector('#adams-group-liquidity');
                    if (liquidity.querySelector('.adams_grid').children.length !== 2) throw new Error('Approved design requires two liquidity cards');
                    const bankLink = root.querySelector('.adams_cash_links button');
                    if (WIDTH === 1440 && DIRECTION === 'ltr' && THEME === 'light')
                        await assertHitTarget(bankLink, 'Bank View accounts');
                    bankLink.click();
                    const cashDrawer = await wait(() => root.querySelector('.adams_cash_dialog[open]'), 'Account directory must open');
                    await wait(() => cashDrawer.querySelector('.adams_bank_row button'), 'Native cash account balances must load');
                    cashDrawer.querySelector('header button').click();
                    await wait(() => !cashDrawer.open, 'Account directory must close');
                    if (liquidity.querySelectorAll('.adams_cash_bridge strong').length !== 3) throw new Error('Native cash bridge must show opening, movement and closing');
                    const aging = root.querySelector('#adams-group-working-capital');
                    if (aging.querySelectorAll('.adams_aging_list').length !== 2) throw new Error('Both native aging panels must be visible');
                    for (const summary of aging.querySelectorAll('.adams_aging_list summary')) {
                        if (WIDTH === 1440 && DIRECTION === 'ltr' && THEME === 'light')
                            await assertHitTarget(summary, 'Aging buckets');
                        summary.click();
                    }
                    if (!aging.querySelector('.adams_aging_list').textContent.includes(expected)) throw new Error('Native receivable bucket must contain the invoice value');
                    const windows = liquidity.querySelectorAll('.adams_supplier_windows .adams_card');
                    if (windows.length !== 4) throw new Error('Four approved supplier windows must render');
                    const paymentValue = new Intl.NumberFormat(document.documentElement.lang || 'en', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(129.45);
                    if (windows[2].querySelector('.adams_value').textContent.trim() !== paymentValue ||
                        windows[3].querySelector('.adams_value').textContent.trim() !== paymentValue)
                        throw new Error('Native supplier window must show 129.45 excluding day 31');
                    for (const date of root.querySelectorAll('.adams_card_date')) {
                        if (getComputedStyle(date).direction !== 'ltr') throw new Error('ISO date ranges must preserve order in RTL');
                    }
                    const source = card.querySelector('.adams_source_button');
                    if (WIDTH === 1440 && DIRECTION === 'ltr' && THEME === 'light')
                        await assertHitTarget(source, 'Source & definition');
                    source.click();
                    const drawer = await wait(() => root.querySelector('dialog[open]'), 'Source drawer must open');
                    if (!drawer.innerText.includes(expected)) throw new Error('Source drawer must retain precise native value');
                    if (!drawer.contains(document.activeElement)) throw new Error('Source drawer must receive focus');
                    if (drawer.getBoundingClientRect().width > WIDTH + 2) throw new Error('Source drawer exceeds viewport');
                    drawer.querySelector('header button').click();
                    await wait(() => !root.querySelector('dialog[open]'), 'Source drawer must close');
                    const filter = root.querySelector('.adams_balance_scope button');
                    filter.focus();
                    if (document.activeElement !== filter) throw new Error('Filter button is not focusable');
                    const navigate = async key => {
                        if (WIDTH <= 900) {
                            root.querySelector('.adams_mobile_menu').click();
                            await wait(() => root.querySelector('.adams_sidebar.is-open'), 'Navigation must open');
                        }
                        root.querySelector('.adams_side_link[data-section="' + key + '"]').click();
                        await wait(() => root.querySelector('#adams-' + key), 'Department must render: ' + key);
                        await wait(() => root.querySelector('.adams_side_link.active')?.dataset.section === key, 'Department must remain active');
                        if (root.querySelectorAll('.adams_section').length !== 1) throw new Error('Only the selected department must own the page');
                    };
                    const more = async action => {
                        if (!root.querySelector('#adams-more-menu')) root.querySelector('[aria-controls="adams-more-menu"]').click();
                        const menu = await wait(() => root.querySelector('#adams-more-menu'), 'More menu must open');
                        const button = menu.querySelector('[data-action="' + action + '"]');
                        if (!button || button.disabled) throw new Error('Requested utility must be available');
                        button.click();
                        await wait(() => !root.querySelector('#adams-more-menu'), 'Utility must close its menu');
                    };
                    const identity = root.querySelector('.adams_company_brand strong');
                    if (identity.textContent.trim() !== COMPANY_NAME) throw new Error('Company branding must match standard company name');
                    const logo = root.querySelector('.adams_company_logo');
                    if (logo && (getComputedStyle(logo).objectFit !== 'contain' || !logo.src.includes('/web/image/res.company/COMPANY_ID/logo'))) throw new Error('Company logo must use its standard record and preserve aspect ratio');
                    for (const key of ['sales', 'crm', 'inventory', 'procurement', 'hr', 'finance']) {
                        await navigate(key);
                        if (root.scrollWidth > root.clientWidth + 2) throw new Error('Department overflow: ' + key);
                    }
                    await navigate('sales');
                    const productRank = await wait(() => root.querySelector('.adams_product_ranking .adams_rank_row'), 'Native product ranking must render');
                    if (!productRank.innerText.includes(expected)) throw new Error('Product ranking must retain signed native invoice value');
                    root.dispatchEvent(new Event('wheel')); root.scrollTop = root.scrollHeight;
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    if (root.querySelector('.adams_side_link.active')?.dataset.section !== 'sales') throw new Error('Scrolling must not change the selected department');
                    root.scrollTop = 0;
                    await navigate('hr');
                    const hrPeriod = await wait(() => root.querySelector('.adams_hr_period'), 'Independent HR dates must render');
                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    const periodControls = [...hrPeriod.querySelectorAll('input[type="date"], button[type="submit"]')];
                    for (let i = 0; i < periodControls.length; i++) {
                        const a = periodControls[i].getBoundingClientRect();
                        const container = hrPeriod.getBoundingClientRect();
                        if (a.left < container.left - 2 || a.right > container.right + 2) throw new Error('HR period control escapes its form at width ' + WIDTH);
                        for (let j = i + 1; j < periodControls.length; j++) {
                            const b = periodControls[j].getBoundingClientRect();
                            if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2) throw new Error('HR date/apply controls overlap at width ' + WIDTH);
                        }
                    }
                    if (WIDTH <= 900) {
                        const nav = root.querySelector('.adams_nav');
                        const active = nav?.querySelector('button.active');
                        if (!active) throw new Error('Active HR department must exist in mobile navigation');
                        const n = nav.getBoundingClientRect(), a = active.getBoundingClientRect();
                        if (a.left < n.left - 2 || a.right > n.right + 2) throw new Error('Active HR department must remain visible in the horizontal navigation');
                    }
                    for (const [name, value] of Object.entries(HR_PERIOD)) {
                        const input = hrPeriod.querySelector('[name="' + name + '"]');
                        input.value = value; input.dispatchEvent(new Event('change', {bubbles:true}));
                    }
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    hrPeriod.requestSubmit();
                    await wait(() => !root.querySelector('#adams-hr [role="status"]') &&
                        hrPeriod.querySelector('button').disabled, 'HR period must apply');
                    const tabs = await wait(() => root.querySelector('.adams_hr_tabs'), 'Five HR views must be available');
                    if (tabs.querySelectorAll('button').length !== 5) throw new Error('HR must expose five tabs');
                    for (let index = 0; index < 5; index++) {
                        tabs.querySelectorAll('button')[index].click();
                        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                        await wait(() => !root.querySelector('#adams-hr [role="status"]'), 'HR tab must leave loading state');
                        if (root.querySelector('#adams-hr [role="alert"]')) throw new Error('HR tab returned a backend error');
                        if (root.scrollWidth > root.clientWidth + 2) throw new Error('HR tab overflows');
                        if (index === 3) {
                            const days = [...root.querySelectorAll('.adams_hr_day > header')];
                            if (!days.length) throw new Error('Shift week must display day headings');
                            for (const day of days) {
                                const weekday = day.querySelector('strong')?.textContent.trim();
                                const date = day.querySelector('bdi')?.textContent.trim();
                                if (!weekday || weekday === date || /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(weekday)) throw new Error('Shift headings must have a localized weekday distinct from the date');
                            }
                        }
                    }
                    if (HAS_EMPLOYEE) {
                        if (![...root.querySelectorAll('.adams_hr_filters select option')].some(node =>
                            node.textContent.includes('Dashboard department / قسم العرض')))
                            throw new Error('Populated HR department must render without template errors');
                        const person = await wait(() => [...root.querySelectorAll('.adams_hr_person')].find(node => node.innerText.includes('000 Dashboard work profile fixture')), 'Authorized employee fixture must appear');
                        person.click();
                        const profile = await wait(() => root.querySelector('.adams_employee_dialog[open]'), 'Employee work profile must open');
                        await wait(() => profile.innerText.includes('000 Dashboard work profile fixture'), 'Profile must show selected employee');
                        if (profile.querySelector('#adams-employee-title')?.textContent !== '000 Dashboard work profile fixture')
                            throw new Error('Employee drawer heading must identify the selected employee');
                        const footer = profile.querySelector('.adams_hr_profile_footer');
                        if (!footer || footer.querySelectorAll('button').length !== 2)
                            throw new Error('Employee drawer must retain separate return and source actions');
                        for (const button of profile.querySelectorAll('.adams_hr_profile_actions button')) {
                            if (!button.querySelector('.adams_directional_arrow'))
                                throw new Error('Employee record actions must expose their navigation direction');
                        }
                        footer.querySelector('button').click();
                        await wait(() => !profile.open, 'Employee profile must close');
                    }
                    await navigate('finance');
                    if (WIDTH <= 900) { root.querySelector('.adams_mobile_menu').click(); await wait(() => root.querySelector('.adams_sidebar.is-open'), 'Search navigation must open'); }
                    root.querySelector('.adams_sidebar button:not([data-section]).adams_side_link').click();
                    if (root.querySelector('.adams_sidebar.is-open')) root.querySelector('.adams_workspace_close').click();
                    const searchInput = await wait(() => root.querySelector('#adams-search'), 'Search input must open');
                    searchInput.value = 'Dashboard Search Fixture';
                    searchInput.dispatchEvent(new Event('input', {bubbles: true}));
                    root.querySelector('.adams_global_search').requestSubmit();
                    const searchDialog = await wait(() => root.querySelector('.adams_search_dialog[open]'), 'Search drawer must open');
                    await wait(() => searchDialog.querySelector('tbody tr'), 'Native search must find fixture records');
                    if (!searchDialog.innerText.includes('Dashboard Search Fixture')) throw new Error('Search lost native partner');
                    if (searchDialog.scrollWidth > searchDialog.clientWidth + 2) throw new Error('Search drawer overflow');
                    searchDialog.querySelector('header button').click();
                    await wait(() => !searchDialog.open, 'Search drawer must close');
                    if (WIDTH === 1440) {
                        await more('print');
                        const printPreview = await wait(() => root.querySelector('.adams_print_summary[open] tbody tr'), 'Native print preview must render');
                        const printDialog = printPreview.closest('dialog');
                        if (!printDialog.innerText.includes(expected)) throw new Error('Print preview lost formatted native revenue');
                        if (!printDialog.innerText.includes(heading)) throw new Error('Print preview lost translated native revenue label');
                        if (printDialog.scrollWidth > printDialog.clientWidth + 2) throw new Error('Print preview overflow');
                        printDialog.querySelectorAll('header button')[1].click();
                        await wait(() => !printDialog.open, 'Print preview must close');
                    }
                    if (WIDTH === 1440 && DIRECTION === 'ltr') {
                        await navigate('sales');
                        // A saved reference view includes both Sales selections.
                        root.querySelectorAll('.adams_recent_tabs button')[1].click();
                        root.querySelectorAll('.adams_rank_tabs button')[1].click();
                        await wait(() => root.querySelectorAll('.adams_recent_tabs button')[1].classList.contains('active') &&
                            root.querySelectorAll('.adams_rank_tabs button')[1].classList.contains('active'), 'Sales selections must activate');
                        root.querySelector('.adams_header [data-action="views"]').click();
                        const views = await wait(() => root.querySelector('.adams_views_dialog[open]'), 'Saved views dialog must open');
                        if (!views.contains(document.activeElement)) throw new Error('Saved views dialog must receive keyboard focus');
                        const viewName = 'Browser Sales selections ' + THEME;
                        const nameInput = views.querySelector('input');
                        nameInput.value = viewName;
                        nameInput.dispatchEvent(new Event('input', {bubbles:true}));
                        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                        views.querySelector('form').requestSubmit();
                        await wait(() => !views.open && root.querySelector('.adams_header [data-action="views"]').textContent.trim() === viewName,
                            'Saving must close the dialog and display the selected view name');
                        const saved = Object.values(localStorage).map(value => {try {return JSON.parse(value);} catch {return null;}})
                            .find(value => value?.viewName === viewName && value?.applied?.company_id === COMPANY_ID);
                        if (!saved || saved.recent?.kind !== 'quotations' || saved.ranking?.key !== 'invoiced_margin')
                            throw new Error('Saved browser selections must retain Sales tabs');
                        if (saved.hr?.rows || saved.recent?.rows || saved.sections || saved.employeeProfile)
                            throw new Error('Saved view must not persist business records');
                        root.querySelectorAll('.adams_recent_tabs button')[0].click();
                        root.querySelectorAll('.adams_rank_tabs button')[0].click();
                        await wait(() => root.querySelectorAll('.adams_recent_tabs button')[0].classList.contains('active') &&
                            root.querySelectorAll('.adams_rank_tabs button')[0].classList.contains('active'), 'Changed Sales selections must activate');
                        await more('restore');
                        await wait(() => root.querySelectorAll('.adams_recent_tabs button')[1]?.classList.contains('active') &&
                            root.querySelectorAll('.adams_rank_tabs button')[1]?.classList.contains('active') &&
                            !root.querySelector('#adams-sales [role="status"]'), 'Saved Sales selections must reload');
                        if (root.querySelector('.adams_header [data-action="views"]').textContent.trim() !== viewName)
                            throw new Error('Restoring must retain its selected view name');
                        await more('views');
                        const resetDialog = await wait(() => root.querySelector('.adams_views_dialog[open]'), 'Saved views must reopen for reset');
                        resetDialog.querySelector('[data-action="reset"]').click();
                        await wait(() => !resetDialog.open && root.querySelector('#adams-finance') &&
                            root.querySelector('.adams_header [data-action="views"]').textContent.trim() !== viewName,
                            'Reset must return to the default Finance view and clear its active name');
                        await more('restore');
                        await wait(() => root.querySelector('#adams-sales') &&
                            root.querySelectorAll('.adams_recent_tabs button')[1]?.classList.contains('active') &&
                            !root.querySelector('#adams-sales [role="status"]'), 'Reset must preserve the stored view for explicit restoration');
                        await navigate('finance');
                        const restoredCard = [...root.querySelectorAll('.adams_card')].find(node => node.querySelector('h3')?.textContent.trim() === heading);
                        const open = restoredCard.querySelector('button[aria-label="Open report"]');
                        open.click();
                        await wait(() => !document.querySelector('.o_adams_dashboard') &&
                            document.body.innerText.includes('100.00'), 'Native report must display independently rendered fixture value');
                        const back = await wait(() => document.querySelector('a[href="/odoo/action-ACTION_ID"]'),
                            'Native financial report must expose dashboard breadcrumb');
                        back.click();
                        const restored = await wait(() => document.querySelector('.o_adams_dashboard .adams_value')?.textContent.trim() === expected
                            && document.querySelector('.o_adams_dashboard'), 'Financial report return must reload the known native value');
                        const restoredDates = [...restored.querySelectorAll('.adams_applied_period bdi, .adams_balance_scope > bdi')].map(input => input.textContent.trim());
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
                        if (THEME === 'light') {
                            const receivableCard = () => [...document.querySelectorAll('#adams-group-working-capital .adams_card')]
                                .find(node => node.querySelector('h3')?.textContent.trim() === 'Receivables');
                            const overdue = await wait(() => receivableCard()?.querySelector('.adams_overdue_total button'),
                                'Approved receivable mapping must expose the overdue action');
                            await assertHitTarget(overdue, 'Overdue receivables');
                            overdue.click();
                            await wait(() => !document.querySelector('.o_adams_dashboard') &&
                                document.body.innerText.includes('Aged Receivable') &&
                                document.body.innerText.includes('Based on Due Date'),
                                'Overdue control must open the native receivables aging report');
                            const overdueBack = await wait(() => document.querySelector('a[href="/odoo/action-ACTION_ID"]'),
                                'Overdue report must expose the dashboard breadcrumb');
                            overdueBack.click();
                            const ledger = await wait(() => [...(receivableCard()?.querySelectorAll('button') || [])]
                                .find(button => button.textContent.includes('Partner Ledger')),
                                'Approved receivable mapping must expose Partner Ledger');
                            await assertHitTarget(ledger, 'Partner Ledger');
                            ledger.click();
                            await wait(() => !document.querySelector('.o_adams_dashboard') &&
                                document.body.innerText.includes('Partner Ledger') &&
                                document.body.innerText.includes('Dashboard Search Fixture'),
                                'Partner Ledger control must show the native report and accounting partner');
                            if (document.body.innerText.includes('Based on Due Date'))
                                throw new Error('Partner Ledger link opened Aged Receivable instead');
                            const ledgerBack = await wait(() => document.querySelector('a[href="/odoo/action-ACTION_ID"]'),
                                'Partner Ledger must expose the dashboard breadcrumb');
                            ledgerBack.click();
                            await wait(() => receivableCard()?.querySelector('.adams_overdue_total button'),
                                'Partner Ledger return must restore Receivables');
                        }
                    }
                    if (WIDTH === 768 || WIDTH === 1024) root.querySelector('#adams-group-liquidity').scrollIntoView({block: 'start'});
                    console.log('test successful');
                })().catch(error => console.error(error));
                '''.replace('COMPANY_NAME', json.dumps(self.env.company.name)).replace('COMPANY_ID', str(self.env.company.id)).replace('HAS_EMPLOYEE', json.dumps(bool(employee))).replace('HR_PERIOD', json.dumps({'date_from': hr_start.isoformat(), 'date_to': hr_end.isoformat()})).replace('THEME', json.dumps(theme)).replace('HEADING', json.dumps(heading)).replace('DIRECTION', json.dumps(direction)).replace('WIDTH', str(width)).replace('ACTION_ID', str(action.id)).replace('EXPECTED_DATES', json.dumps([today.replace(day=1).isoformat(), today.isoformat(), today.isoformat()]))
                original_wait = ChromeBrowser._wait_code_ok

                def capture_success(browser, *args, **kwargs):
                    result = original_wait(browser, *args, **kwargs)
                    # Instrument only evidence capture after the real browser assertions.
                    # Business data, rendering and test success are never mocked.
                    browser.take_screenshot(prefix=f'dashboard_{lang}_{theme}_{width}_').result(timeout=20)
                    # Retain real rendered sections for semantic visual review, not
                    # only the landing screen. This never supplies business values
                    # or changes a test result. Responsive/theme coverage is shared
                    # with the 28-case application journey above.
                    def capture_section(section, target_selector=None, setup=''):
                        expression = r"""(async () => {
                            const wait = async (test, message) => {
                                for (let i = 0; i < 200; i++) {
                                    const value = test(); if (value) return value;
                                    await new Promise(resolve => setTimeout(resolve, 100));
                                }
                                throw new Error(message);
                            };
                            const root = document.querySelector('.o_adams_dashboard');
                            const navigation = root.querySelector('.adams_side_link[data-section="' + SECTION + '"]');
                            if (!navigation) throw new Error('Missing department navigation');
                            if (innerWidth <= 900 && !root.querySelector('.adams_sidebar.is-open')) { root.querySelector('.adams_mobile_menu').click(); await wait(() => root.querySelector('.adams_sidebar.is-open'), 'Evidence navigation must open'); }
                            navigation.click();
                            const section = await wait(() => root.querySelector('#adams-' + SECTION), 'Missing visual evidence section');
                            const toggle = section.querySelector('.adams_section_toggle');
                            if (toggle.getAttribute('aria-expanded') !== 'true') toggle.click();
                            await wait(() => !section.querySelector('.adams_message[role="status"]'),
                                'Visual evidence section did not finish loading');
                            SETUP
                            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                            const target = TARGET ? section.querySelector(TARGET) : section;
                            if (!target) throw new Error('Missing visual evidence target: ' + SECTION + ' / ' + TARGET);
                            const nav = root.querySelector('.adams_nav');
                            root.scrollTop += target.getBoundingClientRect().top - root.getBoundingClientRect().top - nav.getBoundingClientRect().height - 16;
                            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                            if (root.scrollWidth > root.clientWidth + 2) throw new Error('Visual evidence page overflow: ' + SECTION);
                            return {section:SECTION, width:innerWidth, direction:getComputedStyle(root).direction};
                        })()""".replace('SECTION', json.dumps(section)).replace('TARGET', json.dumps(target_selector)).replace('SETUP', setup)
                        observed = browser._websocket_request('Runtime.evaluate', params={
                            'expression': expression, 'awaitPromise': True, 'returnByValue': True,
                        })
                        if observed.get('exceptionDetails'):
                            raise AssertionError(observed['exceptionDetails'])

                    if width == 1440:
                        # Open the actual dashboard summary through its UI. CDP
                        # prints this document with its real @media print rules;
                        # no replacement HTML, report data or mocked window.print.
                        capture_section('finance')
                        observed = browser._websocket_request('Runtime.evaluate', params={
                            'expression': r"""(async () => {
                                const wait = async (test, message) => {
                                    for (let i = 0; i < 250; i++) {
                                        const value = test(); if (value) return value;
                                        await new Promise(resolve => setTimeout(resolve, 100));
                                    }
                                    throw new Error(message);
                                };
                                const root = document.querySelector('.o_adams_dashboard');
                                root.querySelector('.adams_more_wrapper > button').click();
                                const print = await wait(() => root.querySelector('[data-action="print"]'), 'Print menu must open');
                                await wait(() => !print.disabled, 'Print action must be enabled');
                                print.click();
                                const dialog = await wait(() => root.querySelector('.adams_print_summary[open]'), 'Actual print dialog must open');
                                await wait(() => dialog.querySelectorAll('tbody tr').length > 0, 'Actual print rows must render');
                                await document.fonts.ready;
                                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                                return {url: location.href, viewport: [innerWidth, innerHeight],
                                    language: document.documentElement.lang, direction: getComputedStyle(root).direction,
                                    theme: getComputedStyle(root).colorScheme, company: dialog.querySelector(':scope > h2').textContent,
                                    row_count: dialog.querySelectorAll('tbody tr').length,
                                    dates: [...dialog.querySelectorAll(':scope > p bdi')].map(node => node.textContent),
                                    rendered_text: dialog.innerText};
                            })()""", 'awaitPromise': True, 'returnByValue': True,
                        })
                        self.assertFalse(observed.get('exceptionDetails'), observed.get('exceptionDetails'))
                        print_context = observed['result']['value']
                        self.assertEqual(print_context['viewport'], [width, height])
                        self.assertEqual(print_context['company'], self.env.company.name)
                        self.assertIn(heading, print_context['rendered_text'])
                        parameters = {'landscape': False, 'displayHeaderFooter': False,
                            'printBackground': True, 'preferCSSPageSize': True,
                            'paperWidth': 210 / 25.4, 'paperHeight': 297 / 25.4,
                            'marginTop': 10 / 25.4, 'marginBottom': 10 / 25.4,
                            'marginLeft': 10 / 25.4, 'marginRight': 10 / 25.4,
                            'scale': 1, 'transferMode': 'ReturnAsBase64'}
                        try:
                            response = browser._websocket_request('Page.printToPDF', params=parameters)
                            content = base64.b64decode(response['data'], validate=True)
                            self.assertTrue(content.startswith(b'%PDF-') and len(content) > 1000,
                                            'Chrome must return a nonempty actual PDF')
                            document = PdfReader(io.BytesIO(content))
                            self.assertGreater(len(document.pages), 0)
                            # This known compact fixture fits one A4 page at the
                            # unchanged 10pt print size. Nonempty-page checks alone
                            # missed a second page containing only the final note.
                            self.assertEqual(print_context['row_count'], 29,
                                             'Update the PDF fixture acceptance if summary scope changes')
                            self.assertEqual(len(document.pages), 1,
                                             'The 29-row summary must retain its note on the same A4 page')
                            page_text = [page.extract_text() or '' for page in document.pages]
                            self.assertTrue(all(text.strip() for text in page_text),
                                            'Actual dashboard PDF contains a blank page')
                            self.assertGreater(len(''.join(page_text).strip()), 80,
                                               'Actual dashboard PDF is missing its summary text')
                            captured_pdfs.append({'name': f'dashboard_summary_{lang}_{theme}_{width}.pdf',
                                'content': content, 'context': print_context, 'print_parameters': parameters,
                                'page_count': len(document.pages), 'page_text': page_text,
                                'page_sizes_points': [[float(page.mediabox.width), float(page.mediabox.height)]
                                                      for page in document.pages]})
                        finally:
                            closed = browser._websocket_request('Runtime.evaluate', params={
                                'expression': r"""(async () => {
                                    const dialog = document.querySelector('.adams_print_summary[open]');
                                    if (!dialog) throw new Error('Print dialog unexpectedly disappeared');
                                    dialog.querySelectorAll('header button')[1].click();
                                    for (let i = 0; i < 100; i++) {
                                        if (!dialog.open) return true;
                                        await new Promise(resolve => setTimeout(resolve, 50));
                                    }
                                    throw new Error('Print dialog must close through its UI');
                                })()""", 'awaitPromise': True, 'returnByValue': True,
                            })
                            self.assertFalse(closed.get('exceptionDetails'), closed.get('exceptionDetails'))

                    for section in ('sales', 'inventory', 'procurement', 'crm'):
                        setup = ''
                        target = None
                        if section == 'sales':
                            setup = """
                                await wait(() => section.querySelector('.adams_product_ranking .adams_rank_row') &&
                                    section.querySelector('.adams_customers_panel .adams_rank_row') &&
                                    !section.querySelector('[role="status"]'), 'Invoice rankings must settle before capture');
                            """
                        elif section == 'inventory' and stock_category:
                            setup = """
                                const filters = await wait(() => section.querySelector('.adams_stock_filters'), 'Stock filters must render');
                                await wait(() => !filters.querySelector('button[type="submit"]').disabled, 'Initial stock must settle');
                                const category = filters.querySelectorAll('select')[1];
                                category.value = STOCK_CATEGORY;
                                category.dispatchEvent(new Event('change', {bubbles:true}));
                                await new Promise(resolve => requestAnimationFrame(resolve));
                                filters.requestSubmit();
                                await wait(() => !filters.querySelector('button[type="submit"]').disabled &&
                                    section.querySelectorAll('.adams_stock_table tbody tr').length === 25 &&
                                    section.querySelectorAll('.adams_page_number').length === 2 &&
                                    [...section.querySelectorAll('.adams_stock_table tbody tr')].every(row => row.innerText.includes('DASH-VIS-')),
                                    'Filtered native stock must render 25 rows and two numbered pages');
                            """.replace('STOCK_CATEGORY', json.dumps(str(stock_category.id)))
                            target = '.adams_stock_filters'
                        capture_section(section, target, setup)
                        browser.take_screenshot(prefix=f'polish_{section}_{lang}_{theme}_{width}_').result(timeout=20)
                        if section == 'sales':
                            for panel in ('product_ranking', 'order_ranking'):
                                capture_section(section, '.adams_' + panel)
                                browser.take_screenshot(prefix=f'polish_{panel}_{lang}_{theme}_{width}_').result(timeout=20)
                            # These are separate panels in the approved workspace;
                            # the former sales_lower wrapper no longer exists.
                            # Operate both real list tabs before recording them.
                            for index, kind in enumerate(('orders', 'quotations', 'invoices')):
                                capture_section(section, '.adams_recent_panel', """
                                    const tabs = section.querySelectorAll('.adams_recent_tabs button');
                                    if (tabs.length !== 3) throw new Error('Orders, quotations and invoices tabs must exist');
                                    tabs[TAB_INDEX].click();
                                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                                    await wait(() => tabs[TAB_INDEX].classList.contains('active') &&
                                        section.querySelector('.adams_recent_panel .adams_analysis') &&
                                        !section.querySelector('.adams_recent_panel [role="status"]'),
                                        'Selected recent document list must finish loading');
                                    if (section.querySelector('.adams_recent_panel [role="alert"]'))
                                        throw new Error('Recent document list failed during evidence capture');
                                    if (TAB_INDEX === 2 && !section.querySelector('.adams_recent_panel tbody')?.innerText.includes('Dashboard Search Fixture'))
                                        throw new Error('Invoice tab must show the posted customer invoice fixture');
                                """.replace('TAB_INDEX', str(index)))
                                browser.take_screenshot(prefix=f'polish_recent_{kind}_{lang}_{theme}_{width}_').result(timeout=20)
                            capture_section(section, '.adams_fulfillment_panel', """
                                const panel = section.querySelector('.adams_fulfillment_panel');
                                if (!panel) throw new Error('Delivery quantities panel must exist');
                                panel.querySelector('button').click();
                                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                                await wait(() => panel.querySelector('.adams_page_controls') &&
                                    !panel.querySelector('[role="status"]'),
                                    'Delivery quantities must finish loading');
                                if (panel.querySelector('[role="alert"]'))
                                    throw new Error('Delivery quantities failed during evidence capture');
                            """)
                            browser.take_screenshot(prefix=f'polish_fulfillment_{lang}_{theme}_{width}_').result(timeout=20)
                        elif section == 'inventory' and stock_category:
                            # The long first page and its pager cannot fit in one
                            # narrow screenshot; retain both real viewport states.
                            capture_section(section, '.adams_stock_table', r"""
                                const viewport = section.querySelector('.adams_stock_table');
                                const firstRow = viewport.querySelector('tbody tr');
                                const productCell = firstRow.cells[0];
                                const sourceCell = firstRow.cells[firstRow.cells.length - 1];
                                const rtl = getComputedStyle(viewport).direction === 'rtl';
                                const origin = viewport.scrollLeft;
                                const visibleBounds = () => {
                                    const box = viewport.getBoundingClientRect();
                                    const left = box.left + viewport.clientLeft;
                                    return {left, right: left + viewport.clientWidth};
                                };
                                const bounds = visibleBounds();
                                const identity = productCell.getBoundingClientRect();
                                const leading = rtl ? identity.right : identity.left;
                                if (leading < bounds.left - 2 || leading > bounds.right + 2)
                                    throw new Error('Initial stock product edge is clipped by its scrollport');
                                for (const text of productCell.querySelectorAll('span, small')) {
                                    const range = document.createRange();
                                    range.selectNodeContents(text);
                                    for (const box of range.getClientRects()) {
                                        if (box.left < identity.left - 2 || box.right > identity.right + 2)
                                            throw new Error('Stock product text overflows its own cell');
                                    }
                                }
                                try {
                                    viewport.scrollLeft = rtl ? -viewport.scrollWidth : viewport.scrollWidth;
                                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                                    const endBounds = visibleBounds();
                                    const source = sourceCell.getBoundingClientRect();
                                    if (source.left < endBounds.left - 2 || source.right > endBounds.right + 2)
                                        throw new Error('Horizontal stock scrolling cannot reveal the Source data column');
                                    if (root.scrollWidth > root.clientWidth + 2)
                                        throw new Error('Stock horizontal scrolling leaked into page overflow');
                                } finally {
                                    viewport.scrollLeft = origin;
                                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                                }
                            """)
                            browser.take_screenshot(prefix=f'polish_inventory_table_{lang}_{theme}_{width}_').result(timeout=20)
                            capture_section(section, '.adams_page_controls', """
                                const pageTwo = [...section.querySelectorAll('.adams_page_number')].find(button => button.textContent.trim() === '2');
                                if (!pageTwo) throw new Error('Second stock page is missing');
                                pageTwo.click();
                                await wait(() => section.querySelectorAll('.adams_stock_table tbody tr').length === 2 &&
                                    section.querySelector('.adams_page_number[aria-current="page"]')?.textContent.trim() === '2' &&
                                    !section.querySelector('.adams_stock_filters button[type="submit"]').disabled,
                                    'Second stock page must settle with the remaining two fixture rows');
                                if (!section.querySelector('.adams_stock_table tbody').innerText.includes('DASH-VIS-26'))
                                    throw new Error('Second stock page lost its final fixture product');
                            """)
                            browser.take_screenshot(prefix=f'polish_inventory_page2_{lang}_{theme}_{width}_').result(timeout=20)
                    for index, tab in enumerate(('overview', 'attendance', 'time_off', 'shifts', 'employees')):
                        capture_section('hr', None, f"""
                            section.querySelectorAll('.adams_hr_tabs button')[{index}].click();
                            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                            await wait(() => !section.querySelector('[role=\"status\"]'), 'HR screenshot must finish loading');
                        """)
                        browser.take_screenshot(prefix=f'hr_{tab}_{lang}_{theme}_{width}_').result(timeout=20)
                    if employee:
                        capture_section('hr', None, """
                            const person = await wait(() => [...section.querySelectorAll('.adams_hr_person')].find(node => node.innerText.includes('000 Dashboard work profile fixture')), 'Profile capture employee must render');
                            person.click();
                            const profile = await wait(() => root.querySelector('.adams_employee_dialog[open]'), 'Profile capture must open');
                            await wait(() => profile.innerText.includes('000 Dashboard work profile fixture') && !profile.querySelector('[role="status"]'), 'Profile capture must settle');
                            if (profile.querySelector('[role="alert"]')) throw new Error('Profile capture failed');
                        """)
                        browser.take_screenshot(prefix=f'hr_profile_{lang}_{theme}_{width}_').result(timeout=20)
                    return result

                with patch.object(ChromeBrowser, '_wait_code_ok', capture_success):
                    self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=90)

        # Odoo.sh may clean its temporary screenshots after startup. Retain only
        # this successful matrix's PNGs under the configured private data_dir.
        # A pending directory is promoted atomically only after exact coverage,
        # PNG signature and copied-byte hashes are verified. Existing runs survive.
        deadline = time.monotonic() + 5
        while True:
            current = set(screenshot_source.glob(f'*_{self._testMethodName}.png')) - existing_screenshots
            matched = {prefix: [path for path in current if path.name.startswith(prefix)]
                       for prefix in capture_prefixes}
            if all(len(paths) == 1 for paths in matched.values()) or time.monotonic() >= deadline:
                break
            # take_screenshot's file-writing callback may finish just after its Future.
            time.sleep(0.05)
        self.assertEqual(len(capture_prefixes), len(viewports) * 4 * (16 + (2 if stock_category else 0) + (1 if employee else 0)))
        self.assertTrue(all(len(paths) == 1 for paths in matched.values()),
                        'Each matrix view must have exactly one newly saved screenshot')
        retained_root = Path(config['data_dir']) / 'adams_dashboard_ui_evidence' / self.env.cr.dbname
        retained_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        retained_root.parent.chmod(0o700)
        retained_root.chmod(0o700)
        pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=retained_root))
        manifest = {'test': self._testMethodName, 'database': self.env.cr.dbname,
                    'matrix_cases': len(viewports) * 4, 'viewports': viewports, 'screenshots': len(capture_prefixes),
                    'populated_stock': bool(stock_category), 'files': []}
        for prefix, paths in matched.items():
            source = paths[0]
            self.assertFalse(source.is_symlink(), 'Evidence must be a regular screenshot')
            content = source.read_bytes()
            self.assertTrue(content.startswith(b'\x89PNG\r\n\x1a\n') and len(content) > 24,
                            'Screenshot is missing its PNG header')
            expected_width = int(prefix.rstrip('_').rsplit('_', 1)[1])
            expected_height = dict(viewports)[expected_width]
            png_size = (int.from_bytes(content[16:20], 'big'), int.from_bytes(content[20:24], 'big'))
            self.assertEqual(png_size, (expected_width, expected_height),
                             'Evidence must use the requested real browser viewport')
            destination = pending / source.name
            with destination.open('xb') as output:
                output.write(content)
            destination.chmod(0o600)
            digest = hashlib.sha256(content).hexdigest()
            self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(), digest)
            manifest['files'].append({'prefix': prefix, 'name': source.name,
                                      'bytes': len(content), 'sha256': digest, 'viewport': list(png_size)})
        manifest_path = pending / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        manifest_path.chmod(0o600)
        destination = retained_root / ('run-' + uuid4().hex)
        os.replace(pending, destination)
        logging.getLogger(__name__).info('ADAMS_DASHBOARD_UI_EVIDENCE: %s (%s verified PNGs)',
                                         destination, len(capture_prefixes))

        # PDFs have their own manifest and do not change PNG matrix coverage.
        self.assertEqual(len(captured_pdfs), 4, 'Retain English/Arabic × light/dark actual PDFs')
        pdf_root = Path(config['data_dir']) / 'adams_dashboard_pdf_evidence' / self.env.cr.dbname
        pdf_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        pdf_root.parent.chmod(0o700)
        pdf_root.chmod(0o700)
        pdf_pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=pdf_root))
        source_directory = Path(__file__).resolve().parent
        source_sha = subprocess.check_output(
            ['git', '-C', str(source_directory), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(len(source_sha), 40, 'PDF evidence must identify its exact application source')
        pdf_manifest = {'test': self._testMethodName, 'database': self.env.cr.dbname,
                        'application_sha': source_sha, 'test_source': str(Path(__file__).resolve()),
                        'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        'png_evidence_directory': str(destination), 'files': []}
        for captured in captured_pdfs:
            content = captured.pop('content')
            target = pdf_pending / captured['name']
            with target.open('xb') as output:
                output.write(content)
            target.chmod(0o600)
            digest = hashlib.sha256(content).hexdigest()
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), digest)
            pdf_manifest['files'].append(dict(captured, sha256=digest, bytes=len(content)))
        pdf_manifest_path = pdf_pending / 'manifest.json'
        pdf_manifest_path.write_text(json.dumps(pdf_manifest, indent=2, ensure_ascii=False) + '\n')
        pdf_manifest_path.chmod(0o600)
        pdf_destination = pdf_root / ('run-' + uuid4().hex)
        os.replace(pdf_pending, pdf_destination)
        logging.getLogger(__name__).info('ADAMS_DASHBOARD_PDF_EVIDENCE: %s (4 verified actual PDFs)',
                                         pdf_destination)


    def test_hidden_sections_are_absent_from_both_navigation_surfaces(self):
        self.env.company.write({'adams_dashboard_hr': False, 'adams_dashboard_inventory': False})
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        self.browser_js(f'/odoo/action-{action.id}', r"""
            (async () => {
                const wait = async fn => {for(let i=0;i<200;i++){if(fn())return;await new Promise(r=>setTimeout(r,50));}throw new Error('Hidden sections did not settle');};
                await wait(()=>document.querySelector('.adams_nav button'));
                const root=document.querySelector('.o_adams_dashboard');
                if(root.querySelector('#adams-hr') || root.querySelector('#adams-inventory'))throw new Error('Disabled section rendered');
                if(root.querySelector('.adams_side_link[data-section="hr"]') || root.querySelector('.adams_side_link[data-section="inventory"]'))throw new Error('Disabled sidebar item rendered');
                if(root.querySelectorAll('.adams_nav button').length !== 4)throw new Error('Disabled tab rendered');
                console.log('test successful');
            })().catch(error=>console.error(error));
        """, login=self.env.user.login, timeout=60)
