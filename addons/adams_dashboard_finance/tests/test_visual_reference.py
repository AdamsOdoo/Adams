"""Synthetic presentation capture in the real Odoo client.

Runs in the native build test process. These transaction-local
responses are not application fixtures and are never loaded in normal requests.
This records discrepancies; it deliberately does not assert visual acceptance.
"""
import base64
import hashlib
import json
import logging
from pathlib import Path
import tempfile
import time
import subprocess
from unittest.mock import patch

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
        user_id = self.env.uid
        values = {'revenue': 1284000, 'gross_profit': 464800, 'profit': 182400,
                  'operating_expenses': 282400, 'gross_margin': 36.2, 'net_margin': 14.2}
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
                return {x:Math.floor(a.x + window.scrollX),y:Math.floor(a.y + window.scrollY),width:Math.ceil(a.width),
                        height:Math.ceil(b.bottom-a.top),scale:1};
            })()""".replace('SELECTOR', json.dumps(selector)).replace('END', json.dumps(end_selector or selector))
            measured = browser._websocket_request('Runtime.evaluate', params={
                'expression': expression, 'awaitPromise': True, 'returnByValue': True})
            self.assertFalse(measured.get('exceptionDetails'), str(measured))
            clip = measured['result']['value']
            image = browser._websocket_request('Page.captureScreenshot', params={
                'format': 'png', 'clip': clip, 'captureBeyondViewport': True})
            content = base64.b64decode(image['data'])
            path = output / f'{name}.png'
            path.write_bytes(content)
            path.chmod(0o600)
            captures[name] = {'file': path.name, 'sha256': hashlib.sha256(content).hexdigest(), 'clip': clip}

        def after_render(browser, *args, **kwargs):
            result = original_wait(browser, *args, **kwargs)
            capture(browser, 'odoo-profitability', '#adams-group-profitability')
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
                // UI07 only: remove unsupported comparison, preserve the note slot.
                document.querySelector('.kpi-note').textContent='';
                const movement=[...document.querySelectorAll('.focus-row')].find(x=>x.textContent.includes('Revenue movement'));
                if(movement)movement.remove();
                await document.fonts.ready;
                return document.querySelectorAll('.kpis:first-of-type .kpi').length;
            })()"""
            ready = browser._websocket_request('Runtime.evaluate', params={
                'expression': setup, 'awaitPromise': True, 'returnByValue': True})
            self.assertFalse(ready.get('exceptionDetails'), str(ready))
            capture(browser, 'reference-profitability', '#content > .section-heading', '#content > .grid-2')
            return result

        code = r"""(async () => {
            for(let i=0;i<250;i++) {
                const cards=document.querySelectorAll('#adams-group-profitability .adams_value');
                if(cards.length===4 && cards[0].getAttribute('title')?.includes('1,284,000') &&
                   document.querySelectorAll('.adams_chart_column').length===18) {
                    await document.fonts.ready; console.log('test successful'); return;
                }
                await new Promise(r=>setTimeout(r,100));
            }
            throw new Error('Populated Finance fixture failed to render');
        })().catch(e=>console.error(e));"""
        with patch.object(model, 'get_bootstrap', bootstrap), patch.object(model, 'get_section', section), \
                patch.object(model, 'get_financial_trends', trends), patch.object(ChromeBrowser, '_wait_code_ok', after_render):
            self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=60)
        manifest = {'status': 'unreviewed-captures-not-parity', 'html_sha256': hashlib.sha256(raw).hexdigest(),
                    'fixture': 'synthetic Finance values; no source reconciliation claim',
                    'viewport': [1440, 900], 'theme': 'light', 'language': 'en_US',
                    'adjustments': ['UI07: remove comparison note and Revenue movement row'],
                    'captures': captures, 'company': self.env.company.name,
                    'source_sha': subprocess.check_output(['git', '-C', str(reference.parent), 'rev-parse', 'HEAD'], text=True).strip(),
                    'database': self.env.cr.dbname}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        logging.getLogger(__name__).info('ADAMS_REFERENCE_CAPTURE: %s', output)
