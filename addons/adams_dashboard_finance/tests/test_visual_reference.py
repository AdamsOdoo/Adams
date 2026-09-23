"""Synthetic presentation capture in the real Odoo client.

Runs in the native build test process. These transaction-local
responses are not application fixtures and are never loaded in normal requests.
This records discrepancies; it deliberately does not assert visual acceptance.
"""
import base64
import ast
import re
import hashlib
import io
import importlib.util
import json
import logging
from pathlib import Path
import tempfile
import time
import subprocess
from unittest.mock import patch

from PIL import Image

from odoo import api, Command
from odoo.tests import tagged
from odoo.tests.common import ChromeBrowser
from odoo.tools import config
from odoo.tools.translate import code_translations
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install', 'dashboard_visual_reference')
class TestDashboardVisualReference(AccountTestInvoicingHttpCommon):
    def test_finance_populated_reference_capture(self):
        self._capture_reference((1440, 900), 'light', 'en_US')

    def test_finance_inventory_representative_appearances(self):
        # Representative cases, not a full state/viewport/language cross-product.
        for viewport, theme, language in [
                ((1920,1080), 'light', 'en_US'),
                ((1366,768), 'light', 'en_US'),
                ((768,1080), 'dark', 'en_US'),
                ((1440,900), 'dark', 'ar_001')]:
            with self.subTest(viewport=viewport, theme=theme, language=language):
                self._capture_reference(viewport, theme, language)

    def _capture_reference(self, viewport, theme, language):
        reference = Path(__file__).resolve().parents[3] / 'docs/executive-dashboard/reference/Adams_Dashboard_UI_Proposal.html'
        raw = reference.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a')
        self.env.user.group_ids |= self.env.ref('adams_executive_dashboard.group_dashboard_user')
        lang = self.env['res.lang'].with_context(active_test=False).search([('code','=',language)])
        if not lang.active:
            self.env['base.language.install'].create({'lang_ids':[Command.set(lang.ids)]}).lang_install()
        self.env.user.write({'lang':language, 'tz':'UTC', 'color_scheme':theme})
        self.env.company.currency_id = self.env.ref('base.EGP')
        model = type(self.env['adams.executive.dashboard'])
        original_section, original_bootstrap = model.get_section, model.get_bootstrap
        original_trends = model.get_financial_trends
        original_directory = model.get_cash_directory
        original_inventory = model.get_inventory
        user_id = self.env.uid
        messages = code_translations.get_web_translations('adams_executive_dashboard', language)['messages']
        catalog = {message['id']: message['string'] for message in messages if message['string']}
        localized_label = lambda label: catalog.get(label, label)
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
                        item['aging_buckets'] = [{'key': f'period{i}', 'label': localized_label(name), 'value': value}
                                                 for i, (name, value) in enumerate(zip(names, buckets))]
                        item['partner_ledger'] = True
                for item in result['items']:
                    if item['key'] == 'revenue':
                        item.update(source='Profit & Loss', definition='Revenue from posted entries in the selected period.',
                                    source_line='Existing approved Odoo report definition')
                result['cash_breakdown'] = {'status': 'ready', 'bank': 600000, 'cash': 40000}
                result['cash_flow'] = {'status': 'ready', 'source': localized_label('Cash Flow Statement'),
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
                         'balance_status': 'ready', 'balance_currency': 'EGP', 'balance_digits': 2, 'drilldown':True}
                        for i, (name, value) in enumerate(zip(
                            ['Main bank account','Bank overdraft','Retail cash','Office petty cash'],
                            [607200,-7200,28000,12000]))]}

        # Approved sample records exist only inside this native test transaction.
        products = ast.literal_eval(re.search(r"const PRODUCTS=(\[.*?\]);", raw.decode(), re.S).group(1))
        warehouse_names = ['Main warehouse', 'Retail store', 'Online fulfilment']
        category_names = ['Hair Care', 'Body Care', 'Grooming', 'Skin Care', 'Gift Sets']
        stock_rows = []
        for i, product in enumerate(products):
            for j, warehouse in enumerate(warehouse_names):
                index = i * 3 + j
                qty = 0 if index % 11 == 0 else -12 if index % 17 == 0 else (i*43+j*19+37)%217
                reserved = min((i*7+j*3)%19, max(0, qty))
                stock_rows.append({'id': f'{i}-{j}', 'product_id': i+1, 'name': product[1],
                    'display_name': product[1], 'default_code': product[0],
                    'categ_id': [category_names.index(product[2])+1,product[2]],
                    'warehouse_id':j+1, 'warehouse_name':warehouse, 'location_id':index+1,
                    'location_name':f"WH / Stock / {'A' if i<9 else 'B'}-{i%4+1}" if j==0 else 'Retail / Stock' if j==1 else 'Online / Picking',
                    'qty_available':qty, 'reserved_quantity':reserved, 'free_qty':qty-reserved,
                    'incoming_qty':24, 'outgoing_qty':(i*7+j*3)%19, 'virtual_available':qty+24-(i*7+j*3)%19,
                    'uom_id':[1,'PCS'], 'digits':0})

        @api.model
        def inventory(records, options, offset=0, mode='current', filters=None, page_size=25):
            if records.env.uid != user_id:
                return original_inventory(records, options, offset, mode, filters, page_size)
            records._scope(options)
            filters = dict(filters or {})
            rows = [dict(row) for row in stock_rows if
                (not filters.get('hide_zero') or row['qty_available'] != 0) and
                (not filters.get('hide_negative') or row['qty_available'] >= 0) and
                (not filters.get('warehouse_id') or row['warehouse_id'] == filters['warehouse_id']) and
                (not filters.get('category_id') or row['categ_id'][0] == filters['category_id']) and
                filters.get('search','').lower() in (row['name']+' '+row['default_code']+' '+row['location_name']).lower()]
            rows.sort(key=lambda row: (-row['qty_available'],row['name'],row['location_name']) if filters.get('sort')=='qty' else (row['name'],row['location_name']))
            total=len(rows); offset=min(offset,((total-1)//8)*8) if total else 0
            return {'status':'ready' if total else 'empty', 'rows':rows[offset:offset+8],
                'offset':offset,'page_size':8,'total_count':total,'has_more':offset+8<total,
                'mode':mode,'filters':filters,'by_location':True,'as_of':False,
                'warehouses':[{'id':i+1,'name':name} for i,name in enumerate(warehouse_names)],
                'categories':[{'id':i+1,'name':name} for i,name in enumerate(category_names)]}

        target = Path(config['data_dir']) / 'adams_dashboard_reference_evidence'
        target.mkdir(mode=0o700, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='finance-', dir=target))
        self.browser_size = f'{viewport[0]}x{viewport[1]}'
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        original_wait = ChromeBrowser._wait_code_ok
        captures = {}
        environments = {}

        def capture(browser, name, selector, end_selector=None):
            if language == 'ar_001' and name.startswith('reference-'):
                # Contract UI27 requires completed Odoo Arabic, not the partial
                # prototype vocabulary. Normalize content only, never geometry.
                messages = code_translations.get_web_translations('adams_executive_dashboard', language)['messages']
                catalog = {message['id']: message['string'] for message in messages if message['string']}
                localized = browser._websocket_request('Runtime.evaluate', params={
                    'expression': r"""(()=>{
                        const catalog=CATALOG;
                        const escaped=Object.keys(catalog).sort((a,b)=>b.length-a.length).map(key=>key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'));
                        const pattern=new RegExp('(?<![A-Za-z])(?:'+escaped.join('|')+')(?![A-Za-z])','g');
                        const formatter=new Intl.DateTimeFormat('ar-001',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
                        const start=new Date('2026-09-01T12:00:00Z'), end=new Date('2026-09-22T12:00:00Z');
                        const localize=text=>{
                            text=text.replace(/1–22 Sep 2026/g,formatter.formatRange(start,end)).replace(/22 Sept 2026/g,formatter.format(end));
                            // Do not partially translate source definitions or business names.
                            // Translate complete labels and fully covered compound UI captions.
                            const remainder=text.replace(pattern,'').replace(/\b(?:EGP|September|Apr|May|Jun|Jul|Aug|Sept)\b/g,'');
                            if(/[A-Za-z]/.test(remainder))return text;
                            return text.replace(pattern,source=>catalog[source]).replace(/\bSeptember\b/g,new Intl.DateTimeFormat('ar-001',{month:'long',timeZone:'UTC'}).format(end));
                        };
                        for(const label of document.querySelectorAll('.chart .month')) {
                            const index=['Apr','May','Jun','Jul','Aug','Sep*'].indexOf(label.textContent.trim());
                            if(index>=0)label.textContent=new Intl.DateTimeFormat('ar-001',{month:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2026,index+3,1)))+(index===5?'*':'');
                        }
                        document.querySelectorAll('.chart .y-axis span').forEach((label,index)=>{
                            label.textContent=new Intl.NumberFormat('ar-001',{notation:'compact',maximumFractionDigits:1}).format([1500000,1000000,500000,0][index]);
                        });
                        const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
                        let node;while((node=walker.nextNode()))if(!['SCRIPT','STYLE'].includes(node.parentElement?.tagName))node.textContent=localize(node.textContent);
                        for(const element of document.querySelectorAll('[placeholder],[title],[aria-label]'))for(const attribute of ['placeholder','title','aria-label'])if(element.hasAttribute(attribute))element.setAttribute(attribute,localize(element.getAttribute(attribute)));
                    })()""".replace('CATALOG',json.dumps(catalog)), 'returnByValue':True})
                self.assertFalse(localized.get('exceptionDetails'), str(localized))
            expression = r"""(async () => {
                await document.fonts.ready;
                await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                await Promise.all(document.getAnimations().map(animation=>animation.finished.catch(()=>{})));
                const start=document.querySelector(SELECTOR), end=document.querySelector(END);
                if(!start || !end)throw new Error('Missing capture region');
                start.scrollIntoView({block:'start'});
                let scroller=start.parentElement;
                while(scroller && !(scroller.scrollHeight>scroller.clientHeight &&
                    /auto|scroll/.test(getComputedStyle(scroller).overflowY)))scroller=scroller.parentElement;
                scroller=scroller || document.scrollingElement;
                const shellBottom=document.querySelector('.o_main_navbar')?.getBoundingClientRect().bottom || 0;
                const scrollTop=scroller===document.scrollingElement ? 0 : scroller.getBoundingClientRect().top;
                scroller.scrollTop += start.getBoundingClientRect().top - Math.max(shellBottom,scrollTop,0) - 16;
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
                            f'Capture region must fit the unchanged viewport; never trim overflow: {name} {clip} viewport={viewport.size}')
            cropped = io.BytesIO()
            viewport.crop((x, y, x + width, y + height)).save(cropped, format='PNG')
            content = cropped.getvalue()
            path = output / f'{name}.png'
            path.write_bytes(content)
            path.chmod(0o600)
            captures[name] = {'file': path.name, 'sha256': hashlib.sha256(content).hexdigest(), 'clip': clip}
            styles = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(()=>{
                    const box=CAPTURE_BOX, scope=document.querySelector('dialog[open], .drawer') || document.body;
                    return [...scope.querySelectorAll('h1,h2,h3,button,input,select,th,td,small,p,summary')].filter(e=>{
                        const r=e.getBoundingClientRect(); return r.width && r.height && r.top>=box.y-1 && r.bottom<=box.y+box.height+1 && r.left>=box.x-1 && r.right<=box.x+box.width+1;
                    }).slice(0,100).map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {
                        tag:e.tagName,classes:e.className,text:e.textContent.trim().slice(0,100),
                        rect:[r.x-box.x,r.y-box.y,r.width,r.height],
                        styles:Object.fromEntries(['fontFamily','fontSize','fontWeight','lineHeight','color','backgroundColor','padding','margin','borderWidth','borderRadius','verticalAlign','display','direction','textAlign','transform','fontVariantNumeric'].map(k=>[k,s[k]]))};});
                })()""".replace('CAPTURE_BOX',json.dumps(clip)), 'returnByValue':True})
            captures[name]['computed_styles'] = styles['result']['value']

            environments[name] = browser._websocket_request('Runtime.evaluate', params={
                'expression': '''JSON.stringify({browser:navigator.userAgent,
                    fonts:{family:getComputedStyle(document.querySelector('.o_adams_dashboard') || document.body).fontFamily,
                        available:['Inter','Segoe UI','Arial'].map(f=>[f,document.fonts.check('14px '+JSON.stringify(f))])},
                    zoom:visualViewport.scale,device_scale:devicePixelRatio,
                    viewport:[innerWidth,innerHeight]})''', 'returnByValue': True})['result']['value']

        def after_render(browser, *args, **kwargs):
            result = original_wait(browser, *args, **kwargs)
            capture(browser, 'odoo-workspace-header', '.adams_header', '.adams_filters')
            capture(browser, 'odoo-profitability', '#adams-group-profitability')
            opened = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(async()=>{
                    document.querySelector('#adams-group-profitability .adams_source_button').click();
                    for(let i=0;i<100;i++){
                        if(document.querySelector('.adams_finance_source[open]'))return true;
                        await new Promise(r=>setTimeout(r,50));
                    }throw new Error('Source drawer did not open');
                })()""", 'awaitPromise':True,'returnByValue':True})
            self.assertFalse(opened.get('exceptionDetails'),str(opened))
            capture(browser, 'odoo-source-drawer', '.adams_finance_source[open]')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('.adams_finance_source header button').click()"})

            capture(browser, 'odoo-working-capital', '#adams-group-working-capital')
            if viewport == (1440,900) and theme == 'light':
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('.adams_chart_table summary').click(); document.querySelector('.adams_aging_list summary').click()"})
                capture(browser, 'odoo-chart-table', '.adams_chart_table')
                capture(browser, 'odoo-aging-expanded', '.adams_aging_list')
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('.adams_chart_table summary').click(); document.querySelector('.adams_aging_list summary').click()"})

            capture(browser, 'odoo-liquidity', '#adams-group-liquidity')
            capture(browser, 'odoo-balance-sheet', '#adams-group-financial-position')
            opened = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(async()=>{
                    document.querySelector('.adams_cash_links button').click();
                    for(let i=0;i<100;i++){
                        if(document.querySelector('.adams_cash_dialog[open] .adams_bank_row'))return true;
                        await new Promise(r=>setTimeout(r,50));
                    }throw new Error('Cash drawer did not load');
                })()""", 'awaitPromise':True,'returnByValue':True})
            self.assertFalse(opened.get('exceptionDetails'),str(opened))
            capture(browser, 'odoo-cash-drawer', '.adams_cash_dialog[open]')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('.adams_cash_dialog header button').click()"})

            selection = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(async()=>{
                    document.querySelector('.adams_side_link[data-section="inventory"]').click();
                    for(let i=0;i<200;i++){
                        if(document.querySelectorAll('.adams_stock_table tbody tr').length===8)return true;
                        await new Promise(r=>setTimeout(r,50));
                    }throw new Error('Populated Inventory fixture failed to render');
                })()""", 'awaitPromise':True,'returnByValue':True})
            self.assertFalse(selection.get('exceptionDetails'), str(selection))
            capture(browser, 'odoo-stock-filters', '#adams-inventory > .adams_group_heading', '.adams_stock_applied')
            capture(browser, 'odoo-stock-table', '.adams_stock_table', '#adams-inventory .adams_page_controls')
            if viewport[0] <= 900:
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('.adams_stock_detail_toggle').click()"})
                capture(browser, 'odoo-stock-expanded', '.adams_stock_table tbody > tr:first-child', '.adams_stock_detail')
            empty = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(async()=>{
                    const input=document.querySelector('.adams_stock_fields input[type=search]');
                    input.value='NO-MATCH-VISUAL-FIXTURE'; input.dispatchEvent(new Event('input',{bubbles:true}));
                    document.querySelector('.adams_stock_filters').requestSubmit();
                    for(let i=0;i<100;i++){
                        if(document.querySelector('.adams_stock_empty'))return true;
                        await new Promise(r=>setTimeout(r,50));
                    }throw new Error('Empty Inventory state did not render');
                })()""", 'awaitPromise':True,'returnByValue':True})
            self.assertFalse(empty.get('exceptionDetails'),str(empty))
            capture(browser, 'odoo-stock-empty', '.adams_stock_empty')

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
                const profile=COMPANY_FIXTURES[0];
                COMPANY_FIXTURES.splice(0,COMPANY_FIXTURES.length,...REFERENCE_COMPANIES.map(company=>({...profile,key:String(company.id),name:company.name,logo:COMPANY_LOGO})));
                state.companyKey=String(REFERENCE_COMPANY_ID);
                state.theme=REFERENCE_THEME; state.lang=REFERENCE_LANGUAGE;
                render();
                // Match dashboard content width; keep the approved component CSS unchanged.
                document.querySelector('#content').style.width=CONTENT_WIDTH+'px';
                document.querySelector('.main > .heading').style.width=CONTENT_WIDTH+'px';
                document.querySelector('.filterbar').style.width=CONTENT_WIDTH+'px';
                // UI07 only: remove unsupported comparison, preserve the note slot.
                document.querySelector('.kpi-note').textContent='';
                const movement=[...document.querySelectorAll('.focus-row')].find(x=>x.textContent.includes(t('Revenue movement')));
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
            setup = setup.replace('REFERENCE_COMPANIES', json.dumps([{'id':company.id,'name':company.name} for company in self.env.user.company_ids])).replace('REFERENCE_COMPANY_ID', str(self.env.company.id)).replace(
                'COMPANY_LOGO', json.dumps('data:image/png;base64,' + logo if logo else ''))
            setup = setup.replace('CONTENT_WIDTH', str(captures['odoo-profitability']['clip']['width']))
            setup = setup.replace('REFERENCE_THEME',json.dumps(theme)).replace('REFERENCE_LANGUAGE',json.dumps('ar' if language=='ar_001' else 'en'))
            ready = browser._websocket_request('Runtime.evaluate', params={
                'expression': setup, 'awaitPromise': True, 'returnByValue': True})
            self.assertFalse(ready.get('exceptionDetails'), str(ready))
            capture(browser, 'reference-workspace-header', '.main > .heading', '.filterbar')
            capture(browser, 'reference-profitability', '#content > .section-heading', '#content > .grid-2')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('[data-source=revenue]').click(); document.querySelector('.drawer .eyebrow').textContent=companyName(); document.querySelector('.drawer .callout').remove()"})
            capture(browser, 'reference-source-drawer', '.drawer')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('.drawer [data-action=close]').click()"})

            capture(browser, 'reference-working-capital', '#reference-working-capital', '#content > .grid-3')
            if viewport == (1440,900) and theme == 'light':
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('#content > .grid-2 details summary').click(); document.querySelector('#content > .grid-3 details summary').click()"})
                capture(browser, 'reference-chart-table', '#content > .grid-2 details')
                capture(browser, 'reference-aging-expanded', '#content > .grid-3 details')
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('#content > .grid-2 details summary').click(); document.querySelector('#content > .grid-3 details summary').click()"})

            capture(browser, 'reference-liquidity', '#reference-liquidity', '#reference-supplier-note')
            capture(browser, 'reference-balance-sheet', '#reference-balance-sheet', '#content > .grid-3:last-child')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('[data-action=accounts]').click()"})
            # The review-only eyebrow is excluded; the authorized company remains.
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('.drawer .eyebrow').textContent=companyName()"})
            capture(browser, 'reference-cash-drawer', '.drawer')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': "document.querySelector('.drawer [data-action=close]').click()"})

            selected = browser._websocket_request('Runtime.evaluate', params={
                'expression': """(async()=>{
                    document.querySelector('nav button[data-tab=inventory]').click();
                    document.querySelector('#content').style.width=CONTENT_WIDTH+'px';
                    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                    return document.querySelectorAll('.stock-table tbody tr').length;
                })()""".replace('CONTENT_WIDTH', str(captures['odoo-profitability']['clip']['width'])), 'awaitPromise':True,'returnByValue':True})
            self.assertFalse(selected.get('exceptionDetails'),str(selected))
            self.assertEqual(selected['result']['value'],8)
            capture(browser, 'reference-stock-filters', '#content > .section-heading', '.stock-summary')
            capture(browser, 'reference-stock-table', '#content .table-wrap', '#content .table-wrap + div')
            if viewport[0] <= 900:
                browser._websocket_request('Runtime.evaluate', params={
                    'expression': "document.querySelector('[data-stock-detail]').click(); document.querySelector('#content').style.width=CONTENT_WIDTH+'px'".replace('CONTENT_WIDTH',str(captures['odoo-profitability']['clip']['width']))})
                capture(browser, 'reference-stock-expanded', '.stock-table tbody > tr:first-child', '.stock-detail')
            browser._websocket_request('Runtime.evaluate', params={
                'expression': """const input=document.querySelector('#stockSearch');
                    input.value='NO-MATCH-VISUAL-FIXTURE'; input.dispatchEvent(new Event('input',{bubbles:true}));
                    document.querySelector('#stockForm').requestSubmit();
                    document.querySelector('#content').style.width=CONTENT_WIDTH+'px';""".replace('CONTENT_WIDTH',str(captures['odoo-profitability']['clip']['width']))})
            capture(browser, 'reference-stock-empty', '#content .empty')

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
                patch.object(model, 'get_financial_trends', trends), patch.object(model, 'get_cash_directory', directory), patch.object(model, 'get_inventory', inventory), patch.object(ChromeBrowser, '_wait_code_ok', after_render):
            self.browser_js(f'/odoo/action-{action.id}', code, login=self.env.user.login, timeout=60)
        manifest = {'status': 'unreviewed-captures-not-parity', 'html_sha256': hashlib.sha256(raw).hexdigest(),
                    'fixture': 'synthetic Finance values; no source reconciliation claim',
                    'viewport': list(viewport), 'theme': theme, 'language': language,
                    'adjustments': ['UI07: remove comparison note and Revenue movement row',
                                    'UI08: signed bank/cash classification from standard journals; synthetic values retain the approved split',
                                    'UI20: Procurement monetary/count decision deferred; not represented in these captures',
                                    'Company: standard authorized test-company name and logo',
                                    'Exclude prototype review eyebrow and source-destination explanation callout'],
                    'state_normalization': ['authorized test company/logo/menu', 'synthetic Finance values', 'no report warnings'] + (['UI27: completed Arabic catalog and native Arabic period/cutoff content; reference geometry unchanged'] if language == 'ar_001' else []),
                    'arabic_catalog_sha256': hashlib.sha256((reference.parents[3] / 'addons/adams_executive_dashboard/i18n/ar_001.po').read_bytes()).hexdigest() if language == 'ar_001' else None,
                    'content_width': captures['odoo-profitability']['clip']['width'],
                    'captures': captures, 'company': self.env.company.name,
                    'source_sha': subprocess.check_output(['git', '-C', str(reference.parent), 'rev-parse', 'HEAD'], text=True).strip(),
                    'database': self.env.cr.dbname}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # Independent manifests feed the same enforced comparison utility used by review.
        # Visible differences remain review-required; this diagnostic test cannot certify parity.
        refs, acts = [], []
        regions = ['workspace-header','profitability', 'working-capital', 'liquidity', 'balance-sheet', 'cash-drawer', 'source-drawer', 'stock-filters', 'stock-table', 'stock-empty']
        if viewport[0] <= 900: regions.append('stock-expanded')
        if viewport == (1440,900) and theme == 'light': regions.extend(['chart-table','aging-expanded'])
        for region in regions:
            for side, destination in (('reference', refs), ('odoo', acts)):
                name = f'{side}-{region}'
                image = captures[name]
                destination.append(dict(json.loads(environments[name]),
                    id=region, file=image['file'], sha256=image['sha256'],
                    box=[0,0,image['clip']['width'],image['clip']['height']],
                    theme=theme, language=language, content_width=manifest['content_width'],
                    company=manifest['company'], dates={'from':'2026-09-01','to':'2026-09-22','cutoff':'2026-09-22'},
                    controls={'department':'inventory' if region.startswith('stock-') else 'finance','expanded':(region.endswith(('drawer','expanded')) or region=='chart-table'), 'search':'NO-MATCH-VISUAL-FIXTURE' if region=='stock-empty' else ''},
                    data={'fixture':'approved-inventory-synthetic-v1','rows':[] if region=='stock-empty' else stock_rows} if region.startswith('stock-') else {'fixture':'approved-finance-synthetic-v1','values':values,'series':series},
                    state='empty' if region=='stock-empty' else 'expanded' if (region.endswith(('drawer','expanded')) or region=='chart-table') else 'loaded', region=region))
        reference_manifest = output / 'reference.json'
        actual_manifest = output / 'odoo.json'
        reference_manifest.write_text(json.dumps({'role':'approved-reference',
            'html_sha256':manifest['html_sha256'], 'adjustments':manifest['adjustments'],
            'state_normalization':manifest['state_normalization'], 'captures':refs}, indent=2))
        versions = {module.name:module.installed_version for module in self.env['ir.module.module'].search(
            [('name','in',['adams_executive_dashboard','adams_dashboard_finance'])])}
        actual_manifest.write_text(json.dumps({'role':'actual-odoo', 'source_sha':manifest['source_sha'],
            'build':self.env.cr.dbname, 'module_versions':versions, 'captures':acts}, indent=2))
        for path in (output / 'manifest.json', reference_manifest, actual_manifest): path.chmod(0o600)
        tool = reference.parents[3] / 'scripts/dashboard-visual-compare.py'
        spec = importlib.util.spec_from_file_location('dashboard_visual_compare', tool)
        comparator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(comparator)
        try:
            comparator.compare(reference_manifest, actual_manifest, output / 'comparison')
        except ValueError as error:
            # A mismatched environment must stay explicit, never normalized away.
            (output / 'comparison-blocked.txt').write_text(str(error) + '\n')
        logging.getLogger(__name__).info('ADAMS_REFERENCE_CAPTURE: %s', output)
