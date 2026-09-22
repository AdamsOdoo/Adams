"""Disclosed synthetic load baseline; not a customer-volume qualification."""
import json
import logging
import math
import os
import platform
from time import perf_counter

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDashboardPerformance(AccountTestInvoicingHttpCommon):
    def test_native_finance_synthetic_load_baseline(self):
        partners = self.env['res.partner'].create([
            {'name': f'Dashboard load fixture {index:03d}'} for index in range(100)])
        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice', 'partner_id': partners[index % 100].id,
            'invoice_date': '2026-08-10', 'date': '2026-08-10',
            'invoice_date_due': '2026-08-20', 'invoice_payment_term_id': False,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'name': 'Synthetic load', 'quantity': 1, 'price_unit': 100,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()],
            })],
        } for index in range(1000)])
        invoices.action_post()
        Mapping = self.env['adams.dashboard.finance.mapping']
        for metric, report, expression in [
            ('revenue', 'profit_and_loss', 'account_financial_report_revenue0_balance'),
            ('gross_profit', 'profit_and_loss', 'account_financial_report_gross_profit0_balance'),
            ('receivables', 'aged_receivable_report', 'aged_receivable_line_total'),
            ('payables', 'aged_payable_report', 'aged_payable_line_total'),
        ]:
            Mapping.create({
                'company_id': self.env.company.id, 'metric': metric,
                'report_id': self.env.ref('account_reports.' + report).id,
                'expression_id': self.env.ref('account_reports.' + expression).id,
                'definition_note': 'Rolled-back synthetic performance fixture, not owner policy.',
            }).action_approve()
        self.env.flush_all()
        options = {'company_id': self.env.company.id, 'date_from': '2026-08-01',
                   'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        samples, queries = [], []
        for index in range(21):
            self.env.invalidate_all()
            before_queries = self.cr.sql_log_count
            started = perf_counter()
            result = self.env['adams.executive.dashboard'].get_section(
                'finance', dict(options, date_from='2026-08-01' if index % 2 else '2026-08-02'))
            samples.append(perf_counter() - started)
            queries.append(self.cr.sql_log_count - before_queries)
            items = {item['key']: item for item in result['items']}
            for key in ('revenue', 'gross_profit', 'receivables'):
                self.assertEqual(items[key]['status'], 'ready', items[key])
                self.assertEqual(items[key]['value'], 100000)
            self.assertEqual(items['payables']['value'], 0)
        warm = samples[1:]
        p95 = sorted(warm)[math.ceil(len(warm) * .95) - 1]
        _logger.info('DASHBOARD_PERFORMANCE %s', json.dumps({
            'scope': 'native finance RPC body; excludes HTTP/render/concurrent load',
            'invoices': len(invoices), 'journal_items': len(invoices.line_ids),
            'partners': len(partners), 'company_count': 1,
            'mapped_metrics': ['revenue', 'gross_profit', 'receivables', 'payables'],
            'native_report_count': 3, 'first_seconds': samples[0],
            'refresh_p95_seconds': p95, 'samples_seconds': samples,
            'query_counts': queries, 'python': platform.python_version(),
            'cpu_count': os.cpu_count(), 'machine': platform.machine(),
            'first_target_seconds': 3, 'refresh_target_seconds': 2,
            'representative_customer_volume_qualified': False,
        }, sort_keys=True))
        self.assertLessEqual(samples[0], 3, 'Synthetic first native Finance evaluation exceeds 3s')
        self.assertLessEqual(p95, 2, 'Synthetic native Finance refresh p95 exceeds 2s')
        self.browser_size = '1440x900'
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        self.browser_js(f'/odoo/action-{action.id}', '''
        (async () => {
            const wait = async (test, message) => {
                for (let attempt = 0; attempt < 1000; attempt++) {
                    if (test()) return;
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
                throw new Error(message);
            };
            await wait(() => document.querySelector('#adams-finance .adams_metric_groups'), 'Finance did not become usable');
            const first = performance.now();
            const root = document.querySelector('.o_adams_dashboard');
            const period = root.querySelector('.adams_filters select');
            period.value = 'custom'; period.dispatchEvent(new Event('change', {bubbles:true}));
            root.querySelector('.adams_balance_scope button').click();
            await wait(() => root.querySelectorAll('.adams_filters input[type="date"]').length === 3,
                'Custom period and balance cutoff must expose their native date controls');
            const inputs = [...root.querySelectorAll('.adams_filters input[type="date"]')];
            const dates = ['2026-08-01','2026-08-31','2026-08-31'];
            const expected = new Intl.NumberFormat(document.documentElement.lang || 'en',
                {minimumFractionDigits:2, maximumFractionDigits:2}).format(100000);
            const samples = [];
            for (let index = 0; index < 20; index++) {
                dates[0] = index % 2 ? '2026-08-01' : '2026-08-02';
                inputs.forEach((input, i) => {
                    input.value = dates[i]; input.dispatchEvent(new Event('input', {bubbles:true}));
                    input.dispatchEvent(new Event('change', {bubbles:true}));
                });
                const started = performance.now();
                root.querySelector('.adams_filters button[type="submit"]').click();
                await wait(() => root.querySelector('#adams-finance > .adams_message[role="status"]'), 'Refresh must clear old Finance values');
                await wait(() => root.querySelector('#adams-finance .adams_value')?.title === expected,
                    'Refreshed native revenue must equal 100000');
                samples.push((performance.now() - started) / 1000);
            }
            const p95 = [...samples].sort((a,b) => a-b)[18];
            console.log('DASHBOARD_BROWSER_PERFORMANCE ' + JSON.stringify({
                scope:'1440px native browser, 1000 invoices/100 partners, four configured metrics',
                first_navigation_seconds:first / 1000, refresh_p95_seconds:p95, samples_seconds:samples,
                customer_volume_qualified:false, concurrent_load_qualified:false}));
            if (first > 3000) throw new Error('Synthetic usable Finance navigation exceeds 3s');
            if (p95 > 2) throw new Error('Synthetic rendered Finance refresh p95 exceeds 2s');
            console.log('test successful');
        })().catch(error => console.error(error));
        ''', login=self.env.user.login, timeout=120)
