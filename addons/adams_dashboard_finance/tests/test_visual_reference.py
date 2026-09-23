"""Synthetic presentation capture in the real Odoo client.

Runs in the native build test process. These transaction-local
responses are not application fixtures and are never loaded in normal requests.
This records discrepancies; it deliberately does not assert visual acceptance.
"""
import base64
import hashlib
import io
import json
import logging
from pathlib import Path
import tempfile
import time
import subprocess
from unittest.mock import patch

from PIL import Image

from odoo import api
from odoo.tests import tagged
from odoo.tests.common import ChromeBrowser
from odoo.tools import config
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install', 'dashboard_visual_reference')
class TestDashboardVisualReference(AccountTestInvoicingHttpCommon):
    def test_finance_populated_reference_capture(self):
        reference = Path(__file__).resolve().parents[3] / 'docs/executive-dashboard/reference/Adams_Dashboard_UI_Proposal.html'
        raw = reference.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a')
        self.env.user.group_ids |= self.env.ref('adams_executive_dashboard.group_dashboard_user')
        self.env.user.write({'lang': 'en_US', 'tz': 'UTC'})
        self.env.company.currency_id = self.env.ref('base.EGP')
        model = type(self.env['adams.executive.dashboard'])
        original_section, original_bootstrap = model.get_section, model.get_bootstrap
        original_trends = model.get_financial_trends
        original_directory = model.get_cash_directory
        user_id = self.env.uid
        values = {'revenue': 1284000, 'gross_profit': 464800, 'profit': 182400,
                  'operating_expenses': 282400, 'gross_margin': 36.2, 'net_margin': 14.2,
                  'cash': 640000, 'receivables': 286400, 'payables': 198600,
                  'receivables_overdue': 68400, 'payables_overdue': 41200,
                  'assets': 3850000, 'liabilities': 1200000, 'equity': 2650000, 'standard_forecast': 87500}
        series = {'revenue': [1020000, 1150000, 1070000, 1350000, 1142360, 1284000],
                  'gross_profit': [340000, 370000, 350000, 490000, 413672, 464800],
                  'profit': [125000, 148000, 131000, 199000, 162160, 182400]}

        @api.model
        def bootstrap(records):
            result = original_bootstrap(records)  # Keep authorization and standard company identity.
            if records.env.uid == user_id:
                result['options'].update(date_from='2026-09-01', date_to='2026-09-22', as_of='2026-09-22')
            return result

        @api.model
        def section(records, key, options):
            result = original_section(records, key, options)
            if records.env.uid == user_id and key == 'finance':
                for item in result['items']:
                    if item['key'] in values:
                        item.update(status='ready', value=values[item['key']], drilldown=True,
                                    unit='percentage' if 'margin' in item['key'] else 'currency',
                                    has_warnings=False, date_field='period', budget={'status': 'not_configured'})
                for item in result['items']:
                    if item['key'] in ('receivables', 'payables'):
                        buckets = ([218000,31000,12000,7400,9000,9000] if item['key'] == 'receivables'
                                   else [157400,18000,9000,6200,4000,4000])
                        names = ['Not overdue','1–30 days','31–60 days','61–90 days','91–120 days','Over 120 days']
                        item['aging_buckets'] = [{'key': f'period{i}', 'label': name, 'value': value}
                                                 for i, (name, value) in enumerate(zip(names, buckets))]
                        item['partner_ledger'] = True
                result['cash_breakdown'] = {'status': 'ready', 'bank': 600000, 'cash': 40000}
                result['cash_flow'] = {'status': 'ready', 'source': 'Cash Flow Statement',
                                       'bridge': {key: {'value': value} for key, value in zip(
                                           ['opening_balance', 'net_increase', 'closing_balance'],
                                           [518000, 122000, 640000])}}
                for item in result['items']:
                    if item['key'] == 'standard_forecast': item['source'] = 'Executive Summary'
                for item, value in zip(result['supplier_windows'], [36300,12500,64700,159400]):
                    item.update(status='ready', value=value, drilldown=True, has_warnings=False)
                result['currency'], result['digits'] = 'EGP', 2
            return result

        @api.model
        def trends(records, keys, options):
            if records.env.uid != user_id:
                return original_trends(records, keys, options)
            records._scope(options)  # The test still uses an authorized company scope.
            return {'series': {key: {'status': 'ready', 'rows': [
                {'label': f'2026-{index + 4:02}', 'value': value}
                for index, value in enumerate(series[key])]} for key in keys}}

        @api.model
        def directory(records, options, offset=0, search=''):
            if records.env.uid != user_id:
                return original_directory(records, options, offset, search)
            records._scope(options)
            return {'status': 'ready', 'total_count': 4, 'has_more': False, 'search': '',
                    'as_of': '2026-09-22', 'rows': [
                        {'id': i+1, 'name': name, 'code': str(1010+i), 'active': True,
                         'currency': 'EGP', 'journals': [name], 'balance': value,
                         'balance_status': 'ready', 'balance_currency': 'EGP', 'balance_digits': 2}
                        for i, (name, value) in enumerate(zip(
                            ['Operating bank','Reserve bank','Bank overdraft','Cash on hand'],
                            [450000,200000,-50000,40000]))]}

        target = Path(config['data_dir']) / 'adams_dashboard_reference_evidence'
        target.mkdir(mode=0o700, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='finance-', dir=target))
        self.browser_size = '1440x900'
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        original_wait = ChromeBrowser._wait_code_ok
        captures = {}

        def capture(browser, name, selector, end_selector=None):
            expression = r"""(async () => {
                const start=document.querySelector(SELECTOR), end=document.querySelector(END);
                if(!start || !end)throw new Error('Missing capture region');
                start.scrollIntoView({block:'start'});
                await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                const a=start.getBoundingClientRect(), b=end.getBoundingClientRect();
                return {x:Math.floor(a.x),y:Math.floor(a.y),width:Math.ceil(a.width),
                        height:Math.ceil(b.bottom-a.top),scale:1};
            })()""".replace('SELECTOR', json.dumps(selector)).replace('END', json.dumps(end_selector or selector))
            measured = browser._websocket_request('Runtime.evaluate', params={
                'expression': expression, 'awaitPromise': True, 'returnByValue': True})
            self.assertFalse(measured.get('exceptionDetails'), str(measured))
            clip = measured['result']['value']
            # Capture the existing viewport without asking Chrome to resize its
            # document surface (which can remove a scrollbar and reflow the grid).
            image = browser._websocket_request('Page.captureScreenshot', params={
                'format': 'png', 'captureBeyondViewport': False})
            viewport = Image.open(io.BytesIO(base64.b64decode(image['data'])))
            x, y, width, height = (clip[key] for key in ('x', 'y', 'width', 'height'))
            self.assertTrue(0 <= x < x + width <= viewport.width and
                            0 <= y < y + height <= viewport.height,
                            'Capture region must fit the unchanged viewport; never trim overflow')
            cropped = io.BytesIO()
            viewport.crop((x, y, x + width, y + height)).save(cropped, format='PNG')
            content = cropped.getvalue()
            path = output / f'{name}.png'
            path.write_bytes(content)
            path.chmod(0o600)
            captures[name] = {'file': path.name, 'sha256': hashlib.sha256(content).hexdigest(), 'clip': clip}

        def after_render(browser, *args, **kwargs):
            result = original_wait(browser, *args, **kwargs)
            capture(browser, 'odoo-profitability', '#adams-group-profitability')
            capture(browser, 'odoo-working-capital', '#adams-group-working-capital')
            capture(browser, 'odoo-liquidity', '#adams-group-liquidity')
            capture(browser, 'odoo-balance-sheet', '#adams-group-financial-position')
            # Navigate only this disposable test browser to the immutable reference.
            # No iframe, mock route, production asset, or global dashboard patch.
            browser._websocket_request('Page.navigate', params={
                'url': 'data:text/html;base64,' + base64.b64encode(raw).decode()})
            for attempt in range(100):
                try:
                    loaded = browser._websocket_request('Runtime.evaluate', params={
                        'expression': "Boolean(document.querySelector('.kpis'))", 'returnByValue': True})
                    if loaded.get('result', {}).get('value'):
                        break
                except Exception:
                    # Navigation destroys the previous execution context.
                    pass
                time.sleep(.05)
            else:
                self.fail('Immutable reference document did not load')
            setup = r"""(async () => {
                for(let i=0;i<200 && !document.querySelector('.kpis');i++)await new Promise(r=>setTimeout(r,50));
                if(!document.querySelector('.kpis'))throw new Error('Reference did not render');
                // UI/company data normalization uses the authorized disposable test company.
                COMPANY_FIXTURES[0].name=COMPANY_NAME;
                COMPANY_FIXTURES[0].logo=COMPANY_LOGO;
                state.companyKey=COMPANY_FIXTURES[0].key;
                render();
                // Match dashboard content width; keep the approved component CSS unchanged.
                document.querySelector('#content').style.width=CONTENT_WIDTH+'px';
                // UI07 only: remove unsupported comparison, preserve the note slot.
                document.querySelector('.kpi-note').textContent='';
                const movement=[...document.querySelectorAll('.focus-row')].find(x=>x.textContent.includes('Revenue movement'));
                if(movement)movement.remove();
                // Same source state, not a layout waiver: this fixture has no report warnings.
                const warning=document.querySelector('.focus-row:last-child .pill');
                warning.textContent='No report warnings'; warning.classList.remove('amber');
                document.querySelector('#content > .grid-3').previousElementSibling.id='reference-working-capital';
                document.querySelector('#content > .grid-2.equal').previousElementSibling.id='reference-liquidity';
                document.querySelector('#content > .grid-2.equal').nextElementSibling.nextElementSibling.nextElementSibling.id='reference-supplier-note';
                document.querySelector('#content > .grid-3:last-child').previousElementSibling.id='reference-balance-sheet';
                await document.fonts.ready;
                return document.querySelectorAll('.kpis:first-of-type .kpi').length;
            })()"""
            logo = self.env.company.logo
            if isinstance(logo, bytes): logo = logo.decode()
            setup = setup.replace('COMPANY_NAME', json.dumps(self.env.company.name)).replace(
                'COMPANY_LOGO', json.dumps('data:image/png;base64,' + logo if logo else ''))
            setup = setup.replace('CONTENT_WIDTH', str(captures['odoo-profitability']['clip']['width']))
            ready = browser._websocket_request('Runtime.evaluate', params={
                'expression': setup, 'awaitPromise': True, 'returnByValue': True})
            self.assertFalse(ready.get('exceptionDetails'), str(ready))
            capture(browser, 'reference-profitability', '#content > .section-heading', '#content > .grid-2')
            capture(browser, 'reference-working-capital', '#reference-working-capital', '#content > .grid-3')
            capture(browser, 'reference-liquidity', '#reference-liquidity', '#reference-supplier-note')
            capture(browser, 'reference-balance-sheet', '#reference-balance-sheet', '#content > .grid-3:last-child')
            return result

        code = r"""(async () => {
            for(let i=0;i<250;i++) {
                const cards=document.querySelectorAll('#adams-group-profitability .adams_value');
                if(cards.length===4 && cards[0].getAttribute('title')?.includes('1,284,000') &&
                   document.querySelectorAll('.adams_chart_column').length===18 &&
                   document.querySelector('.adams_cash_links')?.textContent.includes('4')) {
                    await document.fonts.ready; console.log('test successful'); return;
                }
                await new Promise(r=>setTimeout(r,100));
            }
            throw new Error('Populated Finance fixture failed to render');
        })().catch(e=>console.error(e));"""
        with patch.object(model, 'get_bootstrap', bootstrap), patch.object(model, 'get_section', section), \
                patch.object(model, 'get_financial_trends', trends), patch.object(model, 'get_cash_directory', directory), patch.object(ChromeBrowser, '_wait_code_ok', after_render):
            self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=60)
        manifest = {'status': 'unreviewed-captures-not-parity', 'html_sha256': hashlib.sha256(raw).hexdigest(),
                    'fixture': 'synthetic Finance values; no source reconciliation claim',
                    'viewport': [1440, 900], 'theme': 'light', 'language': 'en_US',
                    'adjustments': ['UI07: remove comparison note and Revenue movement row'],
                    'state_normalization': ['authorized test company/logo', 'synthetic Finance values', 'no report warnings'],
                    'content_width': captures['odoo-profitability']['clip']['width'],
                    'captures': captures, 'company': self.env.company.name,
                    'source_sha': subprocess.check_output(['git', '-C', str(reference.parent), 'rev-parse', 'HEAD'], text=True).strip(),
                    'database': self.env.cr.dbname}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        logging.getLogger(__name__).info('ADAMS_REFERENCE_CAPTURE: %s', output)
