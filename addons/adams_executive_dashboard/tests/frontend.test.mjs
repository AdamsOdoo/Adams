// Focused controller tests; this does not replace Odoo browser/asset acceptance.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';
import assert from 'node:assert/strict';

function fixture() {
    const pending = [];
    const notifications = [];
    let destroy;
    const services = {
        orm: { call(model, method, args) {
            return new Promise((resolve, reject) => pending.push({ method, args, resolve, reject }));
        } },
        action: { doAction() {} },
        notification: { add(message) { notifications.push(message); } },
    };
    const source = readFileSync(new URL('../static/src/dashboard.js', import.meta.url), 'utf8')
        .replace(/^import .*;$/gm, '').replace('export class', 'class');
    const Controller = runInNewContext(source + '\nExecutiveDashboard;', {
        Component: class {}, onWillStart() {}, onWillUnmount(fn) { destroy = fn; },
        useRef: () => ({ el: { scrollTop: 140 } }), useEffect() {}, useSetupAction() {},
        useState: value => value, useService: key => services[key], _t: value => value,
        registry: { category: () => ({ add() {} }) }, Intl, document: { documentElement: { lang: 'en' } },
    });
    const controller = new Controller();
    controller.setup();
    controller.state.draft = { company_id: 1, date_from: '2026-08-01', date_to: '2026-08-31', as_of: '2026-08-31' };
    return { controller, pending, notifications, destroy: () => destroy() };
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

test('closing analysis suppresses both pending grouped and trend responses', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const loading = controller.inspect('invoiced_sales');
    controller.closeDetail();
    pending[0].resolve({ rows: [{ id: 1, value: 100 }], status: 'ready' });
    pending[1].resolve({ rows: [{ label: '2026-08', value: 100 }] });
    await loading;
    assert.equal(controller.state.detail, null);
});

test('a slower prior dimension cannot replace the selected dimension', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const customers = controller.inspect('invoiced_sales', 'customer');
    const products = controller.inspect('invoiced_sales', 'product');
    pending[2].resolve({ rows: [{ id: 2, value: 25 }], status: 'ready' });
    pending[3].resolve({ rows: [] });
    await products;
    pending[0].resolve({ rows: [{ id: 1, value: 100 }], status: 'ready' });
    pending[1].resolve({ rows: [] });
    await customers;
    assert.equal(controller.state.detail.dimension, 'product');
    assert.equal(controller.state.detail.rows[0].value, 25);
});

test('late cash directory page cannot replace a newer page', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const first = controller.loadDirectory('cash', 0);
    const second = controller.loadDirectory('cash', 25);
    pending[1].resolve({ status: 'ready', rows: [{ id: 26 }] });
    await second;
    pending[0].resolve({ status: 'ready', rows: [{ id: 1 }] });
    await first;
    assert.equal(controller.state.directory.offset, 25);
    assert.equal(controller.state.directory.rows[0].id, 26);
});

test('filter changes suppress exports requested for the previous scope', async () => {
    const { controller, pending, notifications } = fixture();
    controller.state.applied = { ...controller.state.draft };
    controller.state.detail = { key: 'invoiced_sales', dimension: 'customer' };
    const exporting = controller.exportDetail();
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[0].resolve({ filename: 'old.csv', content: 'private old scope' });
    await exporting;
    // The fixture has no Blob/URL download APIs: any attempted stale download fails.
    for (const request of pending.slice(1)) { request.resolve(data(0)); }
    await refresh;
    assert.equal(controller.state.detail, null);
    assert.equal(controller.state.exporting, false);
    assert.equal(notifications.length, 0);
});

test('switching recent lists suppresses slower prior results', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const orders = controller.loadRecent('orders');
    const quotes = controller.loadRecent('quotations');
    pending[1].resolve({ rows: [{ id: 22 }], status: 'ready' });
    await quotes;
    pending[0].resolve({ rows: [{ id: 11 }], status: 'ready' });
    await orders;
    assert.equal(controller.state.recent.kind, 'quotations');
    assert.equal(controller.state.recent.rows[0].id, 22);
});

test('navigation keeps selections and scroll but never caches business values', () => {
    const { controller } = fixture();
    controller.state.applied = { ...controller.state.draft };
    controller.state.detail = { key: 'orders', dimension: 'customer', offset: 25, rows: [{ value: 999 }] };
    controller.state.recent = { kind: 'orders', offset: 25, rows: [{ name: 'private' }] };
    const saved = controller.navigationState();
    assert.equal(saved.scroll, 140);
    assert.equal(saved.detail.offset, 25);
    assert.equal(saved.applied.company_id, 1);
    assert.equal(saved.detail.rows, undefined);
    assert.equal(saved.recent.rows, undefined);
});

test('new filters during return prevent old analysis from reopening', async () => {
    const { controller, pending } = fixture();
    const returning = controller.restoreNavigation({ detail: { key: 'orders', dimension: 'customer', offset: 25 } });
    controller.state.draft.company_id = 2;
    const current = controller.refresh();
    for (const request of pending) { request.resolve(data(1)); }
    await Promise.all([returning, current]);
    assert.equal(pending.length, 6);
    assert.equal(controller.state.detail, null);
    assert.equal(controller.state.applied.company_id, 2);
});


test('historical inventory mode survives paging, navigation and drilldown', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const historical = controller.loadDirectory('inventory', 0, 'historical');
    assert.equal(pending[0].args[2], 'historical');
    pending[0].resolve({ status: 'ready', rows: [], mode: 'historical' });
    await historical;
    const next = controller.loadDirectory('inventory', 25);
    assert.equal(pending[1].args[2], 'historical');
    pending[1].resolve({ status: 'ready', rows: [], mode: 'historical' });
    await next;
    assert.equal(controller.navigationState().inventory.mode, 'historical');
    const open = controller.openReport('inventory');
    assert.equal(pending[2].method, 'open_inventory');
    assert.equal(pending[2].args[1], 'historical');
    pending[2].resolve({});
    await open;
});

test('company changes clear and suppress a pending financial trend', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const loading = controller.loadFinancialTrend('revenue');
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[0].resolve({ status: 'ready', rows: [{ value: 999 }] });
    await loading;
    for (const request of pending.slice(1)) { request.resolve(data(0)); }
    await refresh;
    assert.equal(controller.state.financialTrends.revenue, undefined);
});


test('reference layout separates four finance cards and three sales cards', () => {
    const { controller } = fixture();
    const items = ['revenue', 'gross_profit', 'gross_margin', 'profit', 'net_margin', 'operating_expenses', 'cash', 'standard_forecast', 'receivables', 'payables', 'assets', 'liabilities', 'equity', 'invoiced_sales', 'invoiced_margin', 'confirmed_sales', 'orders', 'quotations'].map(key => ({ key }));
    const finance = controller.metricGroups({ key: 'finance' }, { items });
    assert.equal(finance[0].items.map(item => item.key).join(','), 'revenue,gross_profit,profit,operating_expenses');
    const sales = controller.metricGroups({ key: 'sales' }, { items });
    assert.equal(sales[0].items.map(item => item.key).join(','), 'invoiced_sales,confirmed_sales,quotations');
    assert.equal(controller.sections.length, 6);
});

test('old salesperson ranking cannot survive a company change', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const ranking = controller.loadRanking('invoiced_sales');
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[0].resolve({ rows: [{ id: 1, value: 999 }], status: 'ready' });
    await ranking;
    for (const request of pending.slice(1)) { request.resolve(data(0)); }
    await refresh;
    assert.equal(controller.state.ranking, null);
});
