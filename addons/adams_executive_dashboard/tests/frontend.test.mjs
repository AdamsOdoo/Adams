// Focused controller tests; this does not replace Odoo browser/asset acceptance.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';
import assert from 'node:assert/strict';

function fixture() {
    const pending = [];
    let destroy;
    const services = {
        orm: { call(model, method, args) {
            return new Promise((resolve, reject) => pending.push({ method, args, resolve, reject }));
        } },
        action: { doAction() {} },
        notification: { add() {} },
    };
    const source = readFileSync(new URL('../static/src/dashboard.js', import.meta.url), 'utf8')
        .replace(/^import .*;$/gm, '').replace('export class', 'class');
    const Controller = runInNewContext(source + '\nExecutiveDashboard;', {
        Component: class {}, onWillStart() {}, onWillUnmount(fn) { destroy = fn; },
        useState: value => value, useService: key => services[key], _t: value => value,
        registry: { category: () => ({ add() {} }) }, Intl, document: { documentElement: { lang: 'en' } },
    });
    const controller = new Controller();
    controller.setup();
    controller.state.draft = { company_id: 1, date_from: '2026-08-01', date_to: '2026-08-31', as_of: '2026-08-31' };
    return { controller, pending, destroy: () => destroy() };
}

const data = value => ({ items: [{ key: 'invoiced_sales', value }], digits: 2 });

test('late old-company responses cannot replace current-company results', async () => {
    const { controller, pending } = fixture();
    const old = controller.refresh();
    controller.state.draft.company_id = 2;
    const current = controller.refresh();
    for (const request of pending.slice(3)) { request.resolve(data(200)); }
    await current;
    for (const request of pending.slice(0, 3)) { request.resolve(data(100)); }
    await old;
    assert.equal(controller.state.sections.sales.items[0].value, 200);
    assert.equal(controller.state.applied.company_id, 2);
});

test('refresh clears previous data immediately and a failed section does not erase successful sections', async () => {
    const { controller, pending } = fixture();
    controller.state.sections.sales = data(999);
    const loading = controller.refresh();
    assert.equal(controller.state.sections.sales.items.length, 0);
    pending[0].reject(new Error('restricted'));
    pending[1].resolve(data(75));
    pending[2].resolve(data(50));
    await loading;
    assert.equal(controller.state.sections.finance.status, 'error');
    assert.equal(controller.state.sections.sales.items[0].value, 75);
});

test('unmounted dashboard ignores pending results', async () => {
    const { controller, pending, destroy } = fixture();
    const loading = controller.refresh();
    destroy();
    for (const request of pending) { request.resolve(data(999)); }
    await loading;
    assert.equal(controller.state.sections.sales.status, 'loading');
    assert.equal(controller.state.sections.sales.items.length, 0);
});
