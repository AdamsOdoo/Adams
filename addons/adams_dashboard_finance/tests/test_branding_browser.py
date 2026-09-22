"""Focused standard-company branding and live company-context browser regression."""
import base64
import io
import json

from PIL import Image, ImageDraw

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDashboardBrandingBrowser(AccountTestInvoicingHttpCommon):
    @staticmethod
    def _logo(width, height):
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle(
            (width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=(210, 40, 70, 255))
        stream = io.BytesIO()
        image.save(stream, format='PNG')
        return base64.b64encode(stream.getvalue()).decode()

    def test_standard_brand_refresh_fallback_and_company_switch(self):
        company = self.env.company
        first_name = 'International Company Branding Qualification With A Long English Name'
        arabic_name = 'شركة اختبار الهوية المؤسسية الدولية ذات الاسم العربي الطويل'
        wide = self._logo(160, 40)
        portrait = self._logo(40, 160)
        company.write({'name': first_name, 'logo': wide})
        other = self.env['res.company'].create({'name': 'Second authorized company', 'logo': portrait})
        user = new_test_user(self.env, login='dashboard_branding_operator',
            groups='base.group_user,base.group_system,account.group_account_readonly,'
                   'adams_executive_dashboard.group_dashboard_user',
            company_id=company.id, company_ids=[Command.set((company | other).ids)])
        action = self.env.ref('adams_executive_dashboard.action_dashboard')
        payload = {'company': company.id, 'other': other.id, 'name': first_name,
                   'arabic': arabic_name, 'wide': wide, 'portrait': portrait,
                   'other_name': other.name}
        code = r"""
        (async () => {
            const cfg = CONFIG;
            const wait = async (predicate, message) => {
                const deadline = performance.now() + 25000;
                while (performance.now() < deadline) {
                    if (predicate()) return;
                    await new Promise(resolve => requestAnimationFrame(resolve));
                }
                throw new Error(message);
            };
            const check = (condition, message) => { if (!condition) throw new Error(message); };
            const brand = () => document.querySelector('.adams_company_brand');
            const name = () => brand()?.querySelector('strong')?.textContent;
            const refresh = () => {
                const button = [...document.querySelectorAll('.o_adams_dashboard button')]
                    .find(el => el.textContent.trim() === 'Refresh');
                check(button && !button.disabled, 'Refresh must be available');
                button.click();
            };
            const write = async values => {
                const response = await fetch('/web/dataset/call_kw/res.company/write', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({jsonrpc:'2.0', method:'call', id:1,
                        params:{model:'res.company',method:'write',args:[[cfg.company],values],
                            kwargs:{context:{allowed_company_ids:[cfg.company]}}}})
                });
                const result = await response.json();
                check(!result.error && result.result, 'Standard company edit must succeed');
                refresh();
            };
            const inspectLogo = async ratio => {
                await wait(() => {
                    const logo = brand()?.querySelector('img');
                    return logo?.complete && logo.naturalWidth > 0 &&
                        Math.abs(logo.naturalWidth / logo.naturalHeight - ratio) < .01;
                }, 'Company logo aspect ratio must reach the browser');
                const logo = brand().querySelector('img');
                const style = getComputedStyle(logo);
                check(style.objectFit === 'contain', 'Company logo must preserve its aspect ratio');
                check(style.filter === 'none', 'Company logo colors must not be filtered');
                check(logo.alt === name(), 'Logo alternative text must follow company name');
                const canvas = document.createElement('canvas');
                canvas.width = logo.naturalWidth; canvas.height = logo.naturalHeight;
                const context = canvas.getContext('2d'); context.drawImage(logo, 0, 0);
                const pixel = context.getImageData(canvas.width >> 1, canvas.height >> 1, 1, 1).data;
                check(pixel[0] === 210 && pixel[1] === 40 && pixel[2] === 70,
                    'Standard logo image must retain fixture colors');
                check(context.getImageData(0, 0, 1, 1).data[3] === 0,
                    'Transparent logo pixels must remain transparent');
            };
            await wait(() => name() === cfg.name, 'Initial company identity');
            await inspectLogo(4);
            check(brand().scrollWidth <= brand().clientWidth + 2, 'Long English company name must not overflow');
            const firstURL = brand().querySelector('img').src;
            await write({name:cfg.arabic,logo:cfg.portrait});
            await wait(() => name() === cfg.arabic, 'Standard name change must refresh');
            await inspectLogo(.25);
            check(brand().querySelector('img').src !== firstURL, 'Logo edit must invalidate image URL');
            check(brand().scrollWidth <= brand().clientWidth + 2, 'Long Arabic company name must not overflow');
            await write({logo:false});
            await wait(() => !!brand()?.querySelector('.adams_company_fallback'), 'Missing logo fallback');
            check(brand().querySelector('.adams_company_fallback').getAttribute('aria-label') === cfg.arabic,
                'Fallback must have company accessible name');
            await write({logo:cfg.wide});
            await inspectLogo(4);
            // A real decoding failure exercises the image error path, not a direct component mutation.
            brand().querySelector('img').src = 'data:image/png;base64,invalid';
            await wait(() => !!brand()?.querySelector('.adams_company_fallback'), 'Failed image fallback');
            refresh();
            await inspectLogo(4);
            await wait(() => !!document.querySelector('.adams_cash_card'), 'Finance cards reload');
            const accounts = [...document.querySelectorAll('.o_adams_dashboard button')]
                .find(el => el.textContent.includes('View accounts'));
            check(accounts, 'Cash drawer entry point'); accounts.click();
            await wait(() => document.querySelector('.adams_cash_dialog[open]'), 'Cash drawer opens');
            const {user: nativeUser} = odoo.loader.modules.get('@web/core/user');
            check(nativeUser.allowedCompanies.some(c => c.id === cfg.other), 'Second company authorized');
            // Supported Odoo API, with reload disabled, exercises the live context event contract.
            await nativeUser.activateCompanies([cfg.other], {includeChildCompanies:false,reload:false});
            await wait(() => name() === cfg.other_name, 'Company switch identity');
            check(!document.querySelector('.adams_cash_dialog[open]'), 'Company switch closes prior drawer');
            await inspectLogo(.25);
            await nativeUser.activateCompanies([cfg.company], {includeChildCompanies:false,reload:false});
            await nativeUser.activateCompanies([cfg.other], {includeChildCompanies:false,reload:false});
            await wait(() => name() === cfg.other_name, 'Rapid company changes keep final identity');
            await inspectLogo(.25);
            await wait(() => !!document.querySelector('.adams_cash_card'), 'Final company data loads');
            check(!document.querySelector('.adams_cash_dialog[open]'), 'Rapid changes do not reopen old drawer');
            check(!document.querySelector('.o_adams_dashboard').textContent.includes(cfg.arabic),
                'Prior company caption must not remain in dashboard');
            await nativeUser.activateCompanies([cfg.company], {includeChildCompanies:false,reload:false});
            await wait(() => name() === cfg.arabic, 'Return to first company');
            await inspectLogo(4);
            console.log('test successful');
        })().catch(error => console.error(error));
        """.replace('CONFIG', json.dumps(payload))
        self.browser_js(f'/odoo/action-{action.id}', code, login=user.login, timeout=150)
