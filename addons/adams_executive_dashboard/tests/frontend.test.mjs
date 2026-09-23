// Focused controller tests; this does not replace Odoo browser/asset acceptance.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';
import assert from 'node:assert/strict';

function fixture() {
    const pending = [];
    const notifications = [];
    let destroy;
    const storage = new Map();
    const companyEvents = {};
    const nativeUser = {};
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
        window: { localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) } },
        Component: class {}, onWillStart() {}, onWillUnmount(fn) { destroy = fn; },
        useRef: () => ({ el: { scrollTop: 140 } }), useEffect() {}, useSetupAction() {},
        useState: value => value, useService: key => { if (!services[key]) throw new Error(`Service ${key} is not available`); return services[key]; },
        useBus(bus, event, callback) { companyEvents[event] = callback; }, user: nativeUser, userBus: {}, _t: value => value,
        getComputedStyle: element => ({direction: element.direction || 'ltr'}),
        requestAnimationFrame() {}, registry: { category: () => ({ add() {} }) }, Intl, document: { documentElement: { lang: 'en' } },
    });
    const controller = new Controller();
    controller.setup();
    controller.state.draft = { company_id: 1, date_from: '2026-08-01', date_to: '2026-08-31', as_of: '2026-08-31' };
    return { controller, pending, notifications, storage, companyEvents, nativeUser, destroy: () => destroy() };
}

const data = value => ({ items: [{ key: 'invoiced_sales', value }], digits: 2 });

test('populated Owl views keep global constructors out of template expressions', () => {
    const template = readFileSync(new URL('../static/src/dashboard.xml', import.meta.url), 'utf8');
    assert.doesNotMatch(template, /(?:String\(|Object\.keys\(|Math\.)/);
    const { controller } = fixture();
    assert.deepEqual(Array.from(controller.searchKindKeys), ['all', 'invoices', 'bills', 'orders', 'quotations']);
    assert.equal(controller.currentPage({ offset: 25 }), 2);
    assert.equal(controller.visibleRowEnd({ offset: 25, rows: [{ id: 26 }], total: 26 }), 26);
    assert.equal(controller.chartHitHeight({ height: 0 }), 16);
});

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

test('source drawer and customer values are cleared on a company change', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    controller.openSource({ key: 'revenue', value: 99 }, { currency: 'USD' });
    const old = controller.loadCustomers();
    controller.state.draft.company_id = 2;
    const current = controller.refresh();
    assert.equal(controller.state.source, null);
    assert.equal(controller.state.customers, null);
    pending[0].resolve({ status: 'ready', rows: [{ id: 1, value: 999 }] });
    await old;
    assert.equal(controller.state.customers, null);
    for (const request of pending.slice(1)) request.resolve(data(100));
    await current;
});

test('large headline abbreviation retains exact detail formatting and native signs', () => {
    const { controller } = fixture();
    assert.equal(controller.headline({value: -2330000}, {digits: 2}), '-2.33M');
    assert.equal(controller.formatted({value: -2330000}, {digits: 2}), '-2,330,000.00');
    assert.equal(controller.headline({value: 0}, {digits: 2}), '0.00');
    assert.equal(controller.headline({value: -2330000}, {digits: 2}, true), '-2,330,000');
    assert.equal(controller.headline({value: 129.45}, {digits: 2}, true), '129.45');
    assert.equal(controller.headline({value: 0}, {digits: 2}, true), '0');
    assert.equal(controller.headline({value: null, status: 'restricted'}, {digits: 2}), 'Access restricted');
});

test('cash search rejects stale results and retains applied query on pagination', async () => {
    const { controller, pending } = fixture();
    controller.state.applied = { ...controller.state.draft };
    const old = controller.loadDirectory('cash', 0, null, 'Old bank');
    const fresh = controller.loadDirectory('cash', 0, null, 'New bank');
    pending[1].resolve({status: 'ready', search: 'New bank', rows: [{id: 2}], total_count: 27, has_more: true});
    await fresh;
    pending[0].resolve({status: 'ready', search: 'Old bank', rows: [{id: 1}]});
    await old;
    assert.equal(controller.state.directory.search, 'New bank');
    controller.state.cashSearch = 'Unapplied edit';
    const page = controller.loadDirectory('cash', 25);
    assert.equal(pending[2].args[2], 'New bank');
    pending[2].resolve({status: 'ready', search: 'New bank', rows: [{id: 27}], total_count: 27});
    await page;
    assert.equal(controller.navigationState().directory.search, 'New bank');
});


test('saved views contain selections only and are rejected for another user or revoked company', () => {
    const { controller, storage } = fixture();
    controller.userId = 7;
    controller.viewKey = 'view-7';
    controller.state.companies = [{ id: 1 }];
    controller.state.applied = { ...controller.state.draft, privateResult: 123456 };
    controller.state.sections.finance = { items: [{ value: 999 }] };
    controller.state.recent = { kind: 'quotations', offset: 25, rows: [{ name: 'private quotation' }] };
    controller.state.ranking = { key: 'invoiced_margin', rows: [{ label: 'private salesperson' }] };
    controller.saveView();
    const raw = storage.get('view-7');
    assert.ok(!raw.includes('123456') && !raw.includes('999'));
    assert.ok(!raw.includes('private quotation') && !raw.includes('private salesperson'));
    assert.equal(controller.readSavedView().applied.company_id, 1);
    assert.equal(controller.readSavedView().recent.kind, 'quotations');
    assert.equal(controller.readSavedView().recent.offset, 0);
    assert.equal(controller.readSavedView().ranking.key, 'invoiced_margin');
    controller.userId = 8;
    assert.equal(controller.readSavedView(), null);
    controller.userId = 7;
    controller.state.companies = [{ id: 2 }];
    assert.equal(controller.readSavedView(), null);
});

test('restoring a view reloads authorized values and clears former results immediately', async () => {
    const { controller, pending } = fixture();
    controller.userId = 7;
    controller.viewKey = 'view-7';
    controller.state.companies = [{ id: 1 }];
    controller.state.applied = { ...controller.state.draft };
    controller.saveView();
    controller.state.sections.finance = { items: [{ value: 999 }] };
    controller.state.draft.date_from = '2026-07-01';
    const restore = controller.restoreView();
    assert.equal(controller.state.applied.date_from, '2026-08-01');
    assert.equal(controller.state.sections.finance.items.length, 0);
    for (const request of pending) request.resolve(data(20));
    await restore;
    assert.equal(controller.state.sections.finance.items[0].value, 20);
});


test('reference chart preserves negative values and distinguishes missing observations from zero', () => {
    const { controller } = fixture();
    controller.state.financialTrends = {
        revenue: { status: 'ready', rows: [{ label: '2026-08', value: 100 }, { label: '2026-09', value: 0 }] },
        gross_profit: { status: 'ready', rows: [{ label: '2026-08', value: 30 }] },
        profit: { status: 'ready', rows: [{ label: '2026-08', value: -20 }] },
    };
    const chart = controller.profitabilityChart();
    const positive = chart.rows[0].series[0];
    const negative = chart.rows[0].series[2];
    assert.equal(negative.value, -20);
    assert.equal(negative.y, chart.zero);
    assert.ok(positive.y < chart.zero);
    assert.equal(chart.rows[1].series[0].value, 0);
    assert.equal(chart.rows[1].series[1].value, null);
    assert.equal(chart.rows[1].series[1].height, 0);
});

test('saved Sales tabs reload their selected measures and suppress earlier default loads', async () => {
    const { controller, pending } = fixture();
    controller.userId = 7;
    controller.viewKey = 'view-7';
    controller.state.companies = [{ id: 1 }];
    controller.state.applied = { ...controller.state.draft };
    controller.state.recent = { kind: 'quotations', offset: 25 };
    controller.state.ranking = { key: 'invoiced_margin' };
    controller.saveView();
    const restoring = controller.restoreView();
    pending[0].resolve({ items: [] });
    pending[1].resolve({ items: [{ key: 'invoiced_sales', status: 'ready', value: 20 }] });
    pending[2].resolve({ items: [] });
    // Let section completion schedule default loads and then saved selections.
    for (let i = 0; i < 8; i++) await Promise.resolve();
    const quotes = pending.find(request => request.method === 'get_recent_sales' && request.args[0] === 'quotations');
    const margin = pending.find(request => request.method === 'get_breakdown' && request.args[0] === 'invoiced_margin');
    assert.ok(quotes && margin);
    assert.equal(quotes.args[2], 0);
    quotes.resolve({ status: 'ready', rows: [{ id: 22 }] });
    margin.resolve({ status: 'ready', rows: [{ id: 7, value: 30 }] });
    await restoring;
    for (const request of pending.filter(request => request !== quotes && request !== margin)) {
        request.resolve({ status: 'ready', rows: [{ id: 999, value: 999 }] });
    }
    await Promise.resolve();
    assert.equal(controller.state.recent.kind, 'quotations');
    assert.equal(controller.state.recent.rows[0].id, 22);
    assert.equal(controller.state.ranking.key, 'invoiced_margin');
    assert.equal(controller.state.ranking.rows[0].value, 30);
    assert.equal(controller.navigationState().ranking.key, 'invoiced_margin');
});


test('closed or refreshed search cannot receive old results', async () => {
    const {controller, pending} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.searchQuery = 'invoice';
    const first = controller.searchRecords();
    controller.closeSearch();
    pending[0].resolve({groups: [{rows: [{name: 'private'}]}]});
    await first;
    assert.equal(controller.state.search, null);
    const second = controller.searchRecords();
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[1].resolve({groups: [{rows: [{name: 'old company'}]}]});
    await second;
    for (const request of pending.slice(2)) request.resolve(data(0));
    await refresh;
    assert.equal(controller.state.search, null);
});

test('summary export is suppressed after company changes', async () => {
    const {controller, pending, notifications} = fixture();
    controller.state.applied = {...controller.state.draft};
    const exporting = controller.exportSummary();
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[0].resolve({filename: 'private.csv', content: 'old values'});
    await exporting;
    for (const request of pending.slice(1)) request.resolve(data(0));
    await refresh;
    assert.equal(notifications.length, 0);
    assert.equal(controller.state.exporting, false);
});

test('restricted finance is labelled restricted in attention', () => {
    const {controller} = fixture();
    controller.state.sections.finance = {status:'ready',items:[{key:'payables',status:'restricted',value:null}]};
    assert.equal(controller.supplierStatus, 'Access restricted');
});


test('print preparation rejects an old company response', async () => {
    const {controller, pending, notifications} = fixture();
    controller.state.applied = {...controller.state.draft};
    const printing = controller.printDashboard();
    controller.state.draft.company_id = 2;
    const refresh = controller.refresh();
    pending[0].resolve({print_rows: [{value: 999}]});
    await printing;
    for (const request of pending.slice(1)) request.resolve(data(0));
    await refresh;
    assert.equal(controller.state.printSummary, null);
    assert.equal(notifications.length, 0);
});


test('product ranking suppresses stale responses and retains signed top-five native values', async () => {
    const {controller, pending} = fixture();
    controller.state.applied = {...controller.state.draft};
    const old = controller.loadProducts();
    const current = controller.loadProducts();
    pending[1].resolve({status:'ready', rows:[{id:1,value:75},{id:2,value:-10}]});
    await current;
    pending[0].resolve({status:'ready', rows:[{id:9,value:999}]});
    await old;
    assert.equal(pending[0].args[1], 'product');
    assert.equal(controller.state.products.rows[1].value, -10);
    const third = controller.loadProducts();
    const refresh = controller.refresh();
    pending[2].resolve({status:'ready', rows:[{id:9,value:999}]});
    await third;
    for (const request of pending.slice(3)) request.resolve(data(0));
    await refresh;
    assert.equal(controller.state.products, null);
});

test('company section settings filter navigation and skip hidden source requests', async () => {
    const {controller,pending} = fixture();
    controller.state.companies = [{id:1, enabled_sections:['sales']},{id:2,enabled_sections:[]}];
    const refresh = controller.refresh();
    assert.equal(controller.visibleSections.length,1);
    assert.equal(controller.state.activeSection,'sales');
    assert.equal(pending.length,1);
    assert.equal(pending[0].args[0],'sales');
    pending[0].resolve({items:[{key:'invoiced_sales',status:'empty'}]});
    await refresh;
    // A successful Sales response also requests its native product ranking.
    pending[1].resolve({status:'empty',rows:[]});
    controller.state.draft.company_id=2;
    await controller.refresh();
    assert.equal(controller.visibleSections.length,0);
    assert.equal(controller.state.activeSection,'');
    assert.equal(controller.state.products,null);
});

test('explicit department navigation persists through scrolling and rejects disabled departments', () => {
    const {controller} = fixture();
    controller.state.companies = [{id: 1, enabled_sections: ['finance', 'sales']}];
    controller.state.applied = {company_id: 1};
    let scroll;
    controller.root.el.scrollTo = options => { scroll = options.top; };
    controller.navigateSection('sales');
    assert.equal(controller.state.activeSection, 'sales');
    assert.equal(scroll, 0);
    controller.root.el.scrollTop = 1400;
    controller.syncActiveSection();
    assert.equal(controller.state.activeSection, 'sales');
    controller.navigateSection('hr');
    assert.equal(controller.state.activeSection, 'sales');
    controller.navigateSection('finance');
    assert.equal(controller.state.activeSection, 'finance');
});

test('numbered pagination exposes known pages without inventing an unknown last page', () => {
    const {controller} = fixture();
    assert.deepEqual([...controller.pageNumbers({offset: 0, total_count: 126})], [1, 2, 3, 4, 5, 6]);
    assert.deepEqual([...controller.pageNumbers({offset: 0, has_more: true})], [1, 2]);
    assert.deepEqual([...controller.pageNumbers({offset: 25, has_more: false})], [1, 2]);
    assert.deepEqual([...controller.pageNumbers({offset: 0, total_count: 0})], [1]);
});

test('dirty filters normalize company IDs and do not change applied scope', () => {
    const {controller} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.draft.company_id = '1';
    assert.equal(controller.filtersDirty, false);
    controller.state.draft.as_of = '2026-07-31';
    assert.equal(controller.filtersDirty, true);
    assert.equal(controller.state.applied.as_of, '2026-08-31');
});

test('personal section ordering and collapse do not change company visibility', () => {
    const {controller, storage} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.companies = [{id: 1, enabled_sections: ['finance', 'sales', 'inventory']}];
    controller.moveSection('inventory', -1);
    assert.deepEqual([...controller.visibleSections.map(s=>s.key)], ['finance', 'inventory', 'sales']);
    controller.setAllSections(true);
    assert.equal(controller.state.collapsed.sales, true);
    assert.equal(controller.visibleSections.length, 3);
    assert.ok(storage.size);
});

test('inventory sends an immutable filter snapshot and retains selectors during pagination', async () => {
    const {controller, pending} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.stockFilters.warehouse_id = '7';
    controller.state.stockFilters.category_id = '8';
    controller.state.stockFilters.at_date = '2026-07-31';
    controller.state.inventory = {warehouses: [{id: 7, name: 'Main'}], categories: [{id: 8, name: 'Clothes'}]};
    const load = controller.loadDirectory('inventory', 25, 'historical');
    controller.state.stockFilters.warehouse_id = '9';
    assert.equal(pending[0].args[3].warehouse_id, 7);
    assert.equal(pending[0].args[3].at_date, '2026-07-31');
    assert.equal(controller.state.inventory.warehouses[0].id, 7);
    pending[0].resolve({status: 'ready', rows: [], filters: pending[0].args[3]});
    await load;
    assert.equal(controller.state.inventory.filters.warehouse_id, 7);
});

test('sales-order and quantity rankings ignore an old company response', async () => {
    const {controller, pending} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.productMeasure = 'quantity';
    const orders = controller.loadOrderRanking();
    const products = controller.loadProducts();
    assert.equal(pending[1].method, 'get_product_quantity_ranking');
    controller.generation++;
    pending[0].resolve({status: 'ready', rows: [{id: 1, value: 10}]});
    pending[1].resolve({status: 'ready', rows: [{id: 1, value: 20}], unit_id: 3});
    await Promise.all([orders, products]);
    assert.equal(controller.state.orderRanking.status, 'loading');
    assert.equal(controller.state.products.status, 'loading');
});

test('return from quantity source restores its selected unit and ranking limit', async () => {
    const {controller, pending} = fixture();
    const restore = controller.restoreNavigation({rankLimit:10, productMeasure:'quantity', productUnit:'7'});
    for (const request of pending.slice(0,3)) request.resolve(data(100));
    await new Promise(resolve=>setImmediate(resolve));
    const quantity = pending.find(request=>request.method==='get_product_quantity_ranking');
    assert.equal(quantity.args[1], 7);
    quantity.resolve({status:'ready', rows:[], units:[], unit_id:7});
    await restore;
    assert.equal(controller.state.productUnit, '7');
    assert.equal(controller.state.rankLimit, 10);
});

test('paging stock keeps applied filters even when the draft controls have changed', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={mode:'current',filters:{warehouse_id:3,hide_zero:true},rows:[],offset:0};
    controller.state.stockFilters.warehouse_id='8';
    const next=controller.loadDirectory('inventory',25);
    assert.equal(pending[0].args[3].warehouse_id,3);
    pending[0].resolve({status:'ready',rows:[]});await next;
});

test('changing stock results suppresses an in-flight source action', async () => {
    const {controller,pending}=fixture();let opened=0;
    controller.action.doAction=()=>opened++;
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={mode:'historical',filters:{at_date:'2026-07-31'}};
    const open=controller.openStockRow({product_id:2,location_id:3});
    assert.equal(pending[0].args[4].at_date,'2026-07-31');
    controller.state.inventory={mode:'current',rows:[]};
    pending[0].resolve({res_model:'product.product'});await open;
    assert.equal(opened,0);assert.equal(controller.state.opening,false);
});

test('company settings open for the applied dashboard company', () => {
    const {controller}=fixture();
    controller.state.applied={...controller.state.draft,company_id:2};
    let options;controller.action.doAction=(action, settings)=>{options=settings;};
    controller.openSettings();
    assert.equal(options.additionalContext.default_company_id,2);
    assert.deepEqual([...options.additionalContext.allowed_company_ids],[2]);
});

// Drain RPCs issued by awaited restoration and its auxiliary loaders. This
// avoids coupling regressions to a fixed number of microtask turns or calls.
async function settleRequests(pending, operation, response = () => ({items: [], rows: [], status: 'ready'})) {
    let finished = false;
    operation.finally(() => { finished = true; });
    let cursor = 0;
    for (let wave = 0; wave < 40; wave++) {
        while (cursor < pending.length) {
            const request = pending[cursor++];
            request.resolve(response(request));
        }
        await new Promise(resolve => setImmediate(resolve));
        if (finished && cursor === pending.length) return operation;
    }
    assert.fail('Restoration did not settle after draining its RPCs');
}

test('stock page one uses applied filters until explicit Apply commits the draft', async () => {
    const {controller, pending} = fixture();
    controller.state.applied = {...controller.state.draft};
    controller.state.inventory = {status:'ready',offset:25,mode:'current',total_count:345,
        filters:{search:'',warehouse_id:3,hide_zero:true},rows:[{id:'old'}]};
    controller.state.stockFilters.search = 'ZZ';
    const first = controller.pageStock(0);
    assert.equal(pending[0].args[3].search, '');
    pending[0].resolve({status:'ready',mode:'current',filters:pending[0].args[3],total_count:345,rows:[{id:'page1'}]});
    await first;
    assert.equal(controller.state.inventory.total_count,345);
    const apply = controller.applyStockFilters();
    assert.equal(pending[1].args[3].search,'ZZ');
    pending[1].resolve({status:'empty',mode:'current',filters:pending[1].args[3],total_count:0,rows:[]});
    await apply;
    assert.equal(controller.state.inventory.total_count,0);
});

test('stock cutoff intent overrides a previously entered manual date', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.defaultOptions={date_to:'2026-09-22'};
    controller.state.stockFilters.at_date='2026-08-20';
    controller.state.inventory={mode:'historical',filters:{at_date:'2026-08-20'},rows:[]};
    const cutoff=controller.changeStockMode('cutoff');
    assert.equal(pending[0].args[2],'historical');
    assert.equal(pending[0].args[3].at_date,'2026-08-31');
    pending[0].resolve({status:'ready',rows:[],mode:'historical',as_of:'2026-08-31',filters:pending[0].args[3]});
    await cutoff;
    assert.equal(controller.state.inventory.as_of,'2026-08-31');
});

test('invalid global dates retain the applied scope and successful values without RPCs', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.sections.sales=data(75);
    const good=controller.state.sections.sales;
    controller.state.draft.date_from='2026-09-01';
    await controller.refresh();
    assert.equal(pending.length,0);
    assert.equal(controller.state.sections.sales,good);
    assert.equal(controller.state.applied.date_from,'2026-08-01');
    assert.ok(controller.state.error);
});

test('stock request failure clears prior count and date and retry recovers locally', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.sections.sales=data(75);
    controller.state.inventory={status:'ready',total_count:6,as_of:'2026-08-20',mode:'historical',
        filters:{at_date:'2026-08-20'},rows:[{id:1}]};
    const failure=controller.pageStock(25);
    pending[0].reject(new Error('temporary failure'));
    await failure;
    assert.equal(controller.state.inventory.status,'error');
    assert.equal(controller.state.inventory.total_count,undefined);
    assert.equal(controller.state.inventory.as_of,undefined);
    assert.equal(controller.state.inventory.rows.length,0);
    assert.equal(controller.state.sections.sales.items[0].value,75);
    const retry=controller.pageStock(0);
    assert.equal(pending[1].args[3].at_date,'2026-08-20');
    pending[1].resolve({status:'ready',total_count:1,as_of:'2026-08-20',rows:[{id:2}]});
    await retry;
    assert.equal(controller.state.inventory.rows[0].id,2);
});

test('same-company refresh retains Sales selections and reloads the selected sources', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.recent={kind:'quotations',offset:25,rows:[]};
    controller.state.ranking={key:'invoiced_margin',rows:[]};
    controller.state.productMeasure='quantity'; controller.state.productUnit='7';
    controller.state.rankLimit=10;
    await settleRequests(pending,controller.refresh(), request => request.method==='get_section'
        ? {items:[{key:'invoiced_sales',status:'ready',value:55}]}
        : {status:'ready',rows:[],unit_id:7});
    assert.equal(pending.find(r=>r.method==='get_recent_sales').args[0],'quotations');
    assert.ok(pending.some(r=>r.method==='get_breakdown' && r.args[0]==='invoiced_margin'));
    assert.equal(pending.find(r=>r.method==='get_product_quantity_ranking').args[1],7);
    assert.equal(controller.state.productUnit,'7');
    assert.equal(controller.state.rankLimit,10);
});

test('saved selection restoration reloads stock, search and layout without stored records', async () => {
    const {controller,pending,storage}=fixture();
    controller.userId=12; controller.viewKey='selection-test';
    controller.state.companies=[{id:1}];
    controller.state.applied={...controller.state.draft};
    controller.state.sectionOrder=['sales','inventory','finance'];
    controller.state.inventory={offset:25,mode:'historical',filters:{warehouse_id:3,at_date:'2026-08-20',search:'Shampoo'},rows:[{name:'PRIVATE_STOCK'}]};
    controller.state.search={query:'Invoice',kind:'invoices',offset:50,groups:[{rows:[{name:'PRIVATE_INVOICE'}]}]};
    controller.state.employeeProfile={name:'PRIVATE_EMPLOYEE'};
    controller.state.hrData={filters:{search:'Work'},offset:0,rows:[{name:'PRIVATE_HR'}]};
    controller.saveView();
    const encoded=storage.get('selection-test');
    assert.equal(encoded.includes('PRIVATE_'),false);
    controller.state.inventory=null; controller.state.search=null; controller.state.sectionOrder=[];
    await settleRequests(pending,controller.restoreView(), request => request.method==='get_inventory'
        ? {status:'ready',rows:[],mode:request.args[2],filters:request.args[3]}
        : request.method==='search_records' ? {groups:[],has_more:false} : {items:[],rows:[],status:'ready'});
    const stock=pending.find(r=>r.method==='get_inventory');
    assert.equal(stock.args[1],25); assert.equal(stock.args[3].warehouse_id,3);
    assert.equal(stock.args[3].at_date,'2026-08-20');
    assert.equal(controller.state.search.query,'Invoice');
    assert.equal(controller.state.search.offset,50);
    assert.deepEqual([...controller.state.sectionOrder],['sales','inventory','finance']);
});

test('company switching clears identity-bound drawers and ignores late HR/profile results', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.companies=[{id:1,name:'First',logo_url:'/first'},{id:2,name:'Second',logo_url:'/second'}];
    const hr=controller.loadHR('employees');
    const profile=controller.openEmployeeProfile(11);
    controller.state.draft.company_id=2;
    const refresh=controller.refresh();
    assert.equal(controller.companyIdentity.name,'Second');
    assert.equal(controller.state.employeeProfile,null);
    assert.equal(controller.state.hrData,null);
    pending[0].resolve({status:'ready',rows:[{name:'First company employee'}]});
    pending[1].resolve({status:'ready',id:11,name:'First company employee'});
    for(const request of pending.slice(2))request.resolve({items:[]});
    await Promise.all([hr,profile,refresh]);
    assert.equal(controller.state.employeeProfile,null);
    assert.equal(controller.state.hrData,null);
    assert.equal(controller.companyIdentity.logoUrl,'/second');
});

test('closed and superseded employee profiles reject their late responses', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    const old=controller.openEmployeeProfile(11);
    const current=controller.openEmployeeProfile(22);
    pending[1].resolve({status:'ready',id:22}); await current;
    pending[0].resolve({status:'ready',id:11}); await old;
    assert.equal(controller.state.employeeProfile.id,22);
    const closing=controller.openEmployeeProfile(33);
    controller.closeEmployeeProfile();
    pending[2].resolve({status:'ready',id:33}); await closing;
    assert.equal(controller.state.employeeProfile,null);
});

test('HR optional-source statuses remain distinct and local errors recover', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    for(const status of ['not_installed','restricted','empty']) {
        const load=controller.loadHR('attendance');
        pending.at(-1).resolve({status,rows:[],total:0}); await load;
        assert.equal(controller.state.hrData.status,status);
    }
    const failure=controller.loadHR('attendance');
    pending.at(-1).reject(new Error('backend unavailable')); await failure;
    assert.equal(controller.state.hrData.status,'error');
    const recovery=controller.loadHR('attendance');
    pending.at(-1).resolve({status:'ready',rows:[{id:7}],total:1}); await recovery;
    assert.equal(controller.state.hrData.status,'ready');
    assert.equal(controller.state.hrData.rows[0].id,7);
});

test('HR department selection replaces the unassigned drilldown scope', () => {
    const {controller}=fixture();
    controller.state.hrFilters={department_unassigned:true,search:'Engineer'};
    assert.equal(controller.hrDepartmentSelection,'unassigned');
    controller.changeHRDepartment({target:{value:'7'}});
    assert.equal(controller.hrDepartmentSelection,'7');
    assert.equal(controller.state.hrFilters.department_unassigned,undefined);
    assert.equal(controller.state.hrFilters.search,'Engineer');
    controller.changeHRDepartment({target:{value:'unassigned'}});
    assert.equal(controller.state.hrFilters.department_id,undefined);
    controller.changeHRDepartment({target:{value:''}});
    assert.equal(controller.hrDepartmentSelection,'');
    assert.equal(controller.state.hrFilters.department_unassigned,undefined);
});

test('native active-company event clears old data even with an invalid draft date', async () => {
    const {controller,pending,nativeUser,companyEvents}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.draft.date_from='invalid';
    controller.state.sections.finance=data(999);
    controller.state.employeeProfile={employee:{id:11}};
    nativeUser.activeCompany={id:2};
    companyEvents.ACTIVE_COMPANIES_CHANGED();
    assert.equal(controller.state.applied.company_id,2);
    assert.equal(controller.state.draft.date_from,'2026-08-01');
    assert.equal(controller.state.employeeProfile,null);
    assert.equal(controller.state.sections.finance.items.length,0);
    for(const request of pending)request.resolve(request.method==='get_bootstrap'
        ? {options:{company_id:2},companies:[{id:2,name:'Second'}]} : {items:[]});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(controller.companyIdentity.name,'Second');
});

test('stock sort changes the whole applied query without applying unsent search drafts', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={status:'ready',offset:25,mode:'current',filters:{sort:'name',search:'Applied',warehouse_id:3},rows:[]};
    controller.state.stockFilters.search='Unsent';
    const sort=controller.changeStockSort({target:{value:'qty'}});
    assert.equal(pending[0].args[1],0);
    assert.equal(pending[0].args[3].sort,'qty');
    assert.equal(pending[0].args[3].search,'Applied');
    pending[0].resolve({status:'ready',rows:[],offset:0,filters:pending[0].args[3]});
    await sort;
    assert.equal(controller.navigationState().inventory.filters.sort,'qty');
    assert.equal(controller.state.stockFilters.search,'Unsent');
});

test('stock page recovery accepts the server clamped offset and truthful valuation labels', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={status:'ready',offset:25,mode:'current',filters:{sort:'name'},rows:[]};
    assert.equal(controller.stockValuationLabel({warehouse_id:false}),'Company valuation →');
    assert.equal(controller.stockValuationLabel({warehouse_id:3}),'Warehouse valuation →');
    const page=controller.pageStock(25);
    pending[0].resolve({status:'ready',offset:0,total_count:2,rows:[{id:1},{id:2}]});
    await page;
    assert.equal(controller.state.inventory.offset,0);
    assert.deepEqual([...controller.pageNumbers(controller.state.inventory)],[1]);
});

test('global replenishment opens a real scoped action and rejects a late stock response', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={status:'ready',mode:'current',filters:{warehouse_id:3},rows:[]};
    let opened=0; controller.action.doAction=()=>{opened++;};
    const action=controller.openStockSource('replenishment');
    assert.equal(pending[0].method,'open_inventory_source');
    assert.equal(pending[0].args[1],'replenishment');
    assert.equal(pending[0].args[2].warehouse_id,3);
    controller.state.inventory={status:'loading',rows:[]};
    pending[0].resolve({type:'ir.actions.act_window'}); await action;
    assert.equal(opened,0);
    const current=controller.openStockSource('forecast');
    assert.equal(pending[1].args[1],'forecast');
    pending[1].resolve({type:'ir.actions.act_window'}); await current;
    assert.equal(opened,1);
});

test('reservation source retains the exact row scope and ignores a superseded stock page', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.inventory={status:'ready',mode:'current',filters:{warehouse_id:3},rows:[]};
    let opened=0; controller.action.doAction=()=>{opened++;};
    const action=controller.openStockReservations({product_id:12,location_id:8});
    assert.equal(pending[0].method,'open_inventory_reservations');
    assert.equal(pending[0].args[1],12);
    assert.equal(pending[0].args[2],8);
    assert.equal(pending[0].args[3].warehouse_id,3);
    controller.state.inventory={status:'ready',mode:'historical',rows:[]};
    pending[0].resolve({type:'ir.actions.act_window'}); await action;
    assert.equal(opened,0);
    await controller.openStockReservations({product_id:12,location_id:8});
    assert.equal(pending.length,1);
});

test('compact card dates distinguish the applied period from its balance cutoff', () => {
    const {controller}=fixture();
    controller.state.applied={company_id:1,date_from:'2026-09-01',date_to:'2026-09-22',as_of:'2026-08-31'};
    assert.match(controller.metricPeriodLabel({key:'revenue'}), /1.*22.*Sept.*2026/);
    assert.equal(controller.metricPeriodLabel({key:'cash'}), '31 Aug 2026');
    assert.equal(controller.metricPeriodLabel({key:'custom',date_field:'as_of'}), '31 Aug 2026');
});

test('invalid independent HR dates preserve successful rows and issue no RPC', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.hrPeriodApplied={date_from:'2026-07-01',date_to:'2026-07-31'};
    const retained={status:'ready',rows:[{id:11}],total:1};
    controller.state.hrData=retained;
    for(const period of [
        {date_from:'2026-02-30',date_to:'2026-03-01'},
        {date_from:'2026-07-31',date_to:'2026-07-01'},
        {date_from:'2020-01-01',date_to:'2026-07-31'},
    ]) {
        controller.state.hrPeriodDraft=period;
        await controller.applyHRPeriod();
        assert.ok(controller.state.hrPeriodError);
        assert.equal(controller.state.hrData,retained);
        assert.equal(controller.state.hrPeriodApplied.date_from,'2026-07-01');
        assert.equal(pending.length,0);
    }
});

test('HR overview worklists profiles and sources use applied independent dates, never unsent drafts', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.hrPeriodApplied={date_from:'2026-07-01',date_to:'2026-07-31'};
    controller.state.hrPeriodDraft={date_from:'2026-06-01',date_to:'2026-06-30'};
    const hidden={employee_id:11,department_id:3,status:'open',scope:'current',search:'Private'};
    const overview=controller.loadHR('overview',0,hidden);
    assert.deepEqual(Object.keys(pending[0].args[2]),[]);
    pending[0].resolve({status:'ready',metrics:[],rows:[]}); await overview;
    const list=controller.loadHR('attendance',25,{employee_id:11});
    assert.equal(pending[1].args[2].employee_id,11);
    assert.equal(pending[1].args[3],25);
    pending[1].resolve({status:'ready',rows:[],total:0}); await list;
    const profile=controller.openEmployeeProfile(11);
    pending[2].resolve({status:'ready',employee:{id:11}}); await profile;
    const source=controller.openHRSource(null,true,'attendance',{employee_id:11});
    pending[3].resolve({type:'ir.actions.act_window'}); await source;
    for(const request of pending) {
        assert.equal(request.args[0].date_from,'2026-07-01',request.method);
        assert.equal(request.args[0].date_to,'2026-07-31',request.method);
        assert.equal(request.args[0].company_id,1);
        assert.equal(request.args[0].as_of,'2026-08-31');
    }
    assert.equal(controller.state.hrPeriodDraft.date_from,'2026-06-01');
});

test('global refresh preserves same-company HR period and saved navigation restores selections without records', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.hrPeriodApplied={date_from:'2026-07-01',date_to:'2026-07-31'};
    controller.state.hrPeriodDraft={...controller.state.hrPeriodApplied};
    controller.state.hrTab='attendance';
    controller.state.hrData={status:'ready',filters:{employee_id:11},offset:25,rows:[{name:'PRIVATE_HR_RECORD'}]};
    controller.state.employeeProfile={employee:{name:'PRIVATE_PROFILE'}};
    const saved=controller.navigationState();
    assert.equal(JSON.stringify(saved).includes('PRIVATE_'),false);
    controller.state.draft.date_from='2026-09-01';
    controller.state.draft.date_to='2026-09-30';
    await settleRequests(pending,controller.refresh());
    assert.equal(controller.hrOptions.date_from,'2026-07-01');
    assert.equal(controller.state.applied.date_from,'2026-09-01');
    controller.state.hrPeriodApplied={date_from:'2026-06-01',date_to:'2026-06-30'};
    await settleRequests(pending,controller.restoreNavigation(saved));
    const request=pending.findLast(request=>request.method==='get_hr_workspace');
    assert.equal(request.args[0].date_from,'2026-07-01');
    assert.equal(request.args[1],'attendance');
    assert.equal(request.args[2].employee_id,11);
    assert.equal(request.args[3],25);
    assert.equal(controller.state.hrPeriodDraft.date_to,'2026-07-31');
    assert.equal(controller.state.employeeProfile,null);
});

test('rapid HR period changes reject old rows profiles and source navigation', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.hrPeriodApplied={date_from:'2026-07-01',date_to:'2026-07-31'};
    const old=controller.loadHR('attendance');
    const profile=controller.openEmployeeProfile(11);
    let opened=0; controller.action.doAction=()=>{opened++;};
    const source=controller.openHRSource(5);
    controller.state.hrPeriodDraft={date_from:'2026-06-01',date_to:'2026-06-30'};
    const intermediate=controller.applyHRPeriod();
    controller.state.hrPeriodDraft={date_from:'2026-05-01',date_to:'2026-05-31'};
    const current=controller.applyHRPeriod();
    pending[4].resolve({status:'ready',rows:[{id:55}],total:1}); await current;
    pending[0].resolve({status:'ready',rows:[{id:77}],total:1});
    pending[1].resolve({status:'ready',employee:{id:11}});
    pending[2].resolve({type:'ir.actions.act_window'});
    pending[3].resolve({status:'ready',rows:[{id:66}],total:1});
    await Promise.all([old,profile,source,intermediate]);
    assert.equal(controller.state.hrData.rows[0].id,55);
    assert.equal(controller.state.employeeProfile,null);
    assert.equal(controller.state.hrPeriodApplied.date_from,'2026-05-01');
    assert.equal(opened,0);
    assert.equal(controller.state.opening,false);
});

test('company change resets independent HR dates to the new applied global period', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    controller.state.hrPeriodApplied={date_from:'2026-07-01',date_to:'2026-07-31'};
    controller.state.hrPeriodDraft={date_from:'invalid',date_to:'invalid'};
    controller.state.hrPeriodError='Previous validation error';
    controller.state.draft.company_id=2;
    await settleRequests(pending,controller.refresh());
    assert.equal(controller.hrOptions.company_id,2);
    assert.equal(controller.state.hrPeriodApplied.date_from,'2026-08-01');
    assert.equal(controller.state.hrPeriodDraft.date_to,'2026-08-31');
    assert.equal(controller.state.hrPeriodError,'');
});

test('HR week appends complete bounded batches and retains independent list pagination', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    const first=controller.loadHR('shifts',75,{view:'week'});
    assert.equal(pending[0].args[3],0);
    pending[0].resolve({status:'ready',offset:0,page_size:100,total:203,has_more:true,rows:Array.from({length:100},(_,i)=>({id:i+1}))});await first;
    const more=controller.loadMoreHRShifts();
    assert.equal(controller.state.hrData.rows.length,100);
    assert.equal(pending[1].args[3],100);
    await controller.loadMoreHRShifts();assert.equal(pending.length,2);
    pending[1].resolve({status:'ready',offset:100,page_size:100,total:203,has_more:true,rows:Array.from({length:100},(_,i)=>({id:i+101}))});await more;
    assert.equal(controller.state.hrData.rows.length,200);
    const last=controller.loadMoreHRShifts();assert.equal(pending[2].args[3],200);
    pending[2].resolve({status:'ready',offset:200,page_size:100,total:203,has_more:false,rows:[{id:201},{id:202},{id:203}]});await last;
    assert.equal(controller.state.hrData.rows.length,203);assert.equal(controller.state.hrData.has_more,false);
    const list=controller.loadHR('shifts',25,{view:'list'});assert.equal(pending[3].args[3],25);
    assert.equal(controller.state.hrData.rows.length,0);
    pending[3].resolve({status:'ready',offset:25,page_size:25,total:26,has_more:false,rows:[{id:26}]});await list;
    assert.deepEqual(Array.from(controller.state.hrData.rows,row=>row.id),[26]);
});

test('late HR week append cannot replace new filters, periods, tabs or company scope', async () => {
    for (const change of ['filters','period','tab','company']) {
        const {controller,pending}=fixture();controller.state.applied={...controller.state.draft};
        const initial=controller.loadHR('shifts',0,{view:'week',department_id:2});
        pending[0].resolve({status:'ready',offset:0,total:2,has_more:true,rows:[{id:1}]});await initial;
        const stale=controller.loadMoreHRShifts();
        if(change==='company'){controller.generation++;controller.state.applied.company_id=2;}
        if(change==='period')controller.state.hrPeriodApplied={date_from:'2026-09-01',date_to:'2026-09-07'};
        const fresh=controller.loadHR(change==='tab'?'employees':'shifts',0,{view:'week',department_id:3});
        assert.equal(controller.state.hrData.rows.length,0);
        pending[2].resolve({status:'ready',offset:0,total:1,has_more:false,rows:[{id:99}]});await fresh;
        pending[1].resolve({status:'ready',offset:1,total:2,has_more:false,rows:[{id:2}]});await stale;
        assert.deepEqual(Array.from(controller.state.hrData.rows,row=>row.id),[99],change);
    }
});

test('HR week append failure preserves loaded shifts and retries the same offset', async () => {
    const {controller,pending}=fixture();controller.state.applied={...controller.state.draft};
    const first=controller.loadHR('shifts',0,{view:'week'});
    pending[0].resolve({status:'ready',offset:0,total:2,has_more:true,rows:[{id:1}]});await first;
    const fail=controller.loadMoreHRShifts();pending[1].reject(new Error('temporary'));await fail;
    assert.equal(controller.state.hrData.load_more_error,true);assert.equal(controller.state.hrData.rows[0].id,1);
    const retry=controller.loadMoreHRShifts();assert.equal(pending[2].args[3],1);
    pending[2].resolve({status:'ready',offset:1,total:2,has_more:false,rows:[{id:2}]});await retry;
    assert.equal(controller.state.hrData.load_more_error,false);assert.equal(controller.state.hrData.rows.length,2);
});


test('HR week restarts when Planning inserts or removes shifts between calendar batches', async () => {
    for (const change of ['insert', 'remove', 'changed_during_count', 'same_count_reorder']) {
        const {controller,pending}=fixture();controller.state.applied={...controller.state.draft};
        const initial=controller.loadHR('shifts',0,{view:'week',department_id:2});
        pending[0].resolve({status:'ready',offset:0,page_size:100,total:102,has_more:true,
            rows:Array.from({length:100},(_,i)=>({id:102-i}))});await initial;
        const more=controller.loadMoreHRShifts();assert.equal(pending[1].args[3],100);
        const response = change === 'insert'
            ? {total:103,offset:100,rows:[{id:3},{id:2},{id:1}]}
            : change === 'remove' ? {total:2,offset:0,rows:[{id:2},{id:1}]}
            : change === 'same_count_reorder' ? {total:102,offset:100,rows:[{id:3},{id:1}]}
            : {total:102,offset:100,rows:[{id:1}]};
        pending[1].resolve({status:'ready',page_size:100,has_more:false,...response});
        await new Promise(setImmediate);
        assert.equal(pending[2].args[3],0,change);
        assert.equal(pending[2].args[2].department_id,2,change);
        assert.equal(controller.state.hrData.rows.length,0,change);
        const fresh = change === 'remove' ? [{id:2},{id:1}] : Array.from({length:100},(_,i)=>({id:103-i}));
        pending[2].resolve({status:'ready',offset:0,page_size:100,total:response.total,
            has_more:fresh.length<response.total,rows:fresh});await more;
        assert.deepEqual(Array.from(controller.state.hrData.rows,row=>row.id),fresh.map(row=>row.id),change);
        assert.equal(controller.state.hrData.has_more,fresh.length<response.total,change);
    }
});

test('HR week admission revocation clears loaded sensitive data instead of offering transient retry', async () => {
    const {controller,pending}=fixture();controller.state.applied={...controller.state.draft};
    const first=controller.loadHR('shifts',0,{view:'week'});
    pending[0].resolve({status:'ready',offset:0,total:102,has_more:true,
        rows:Array.from({length:100},(_,i)=>({id:i+1,employee_id:[1,'Previously authorized employee']}))});await first;
    controller.state.employeeProfile={status:'ready',employee:{id:1,name:'Previously authorized employee'}};
    controller.hrDepartments=[{id:1,name:'Previously authorized department'}];
    const denied=controller.loadMoreHRShifts();
    pending[1].reject(Object.assign(new Error('Access denied'),{data:{name:'odoo.exceptions.AccessError'}}));await denied;
    assert.equal(controller.state.hrData.status,'restricted');
    assert.equal(controller.state.hrData.rows.length,0);
    assert.equal(controller.state.employeeProfile,null);
    assert.equal(controller.hrDepartments.length,0);
    assert.equal(controller.state.hrData.load_more_error,undefined);
    await controller.loadMoreHRShifts();assert.equal(pending.length,2);
});


test('native user Arabic language governs week and metric dates even when host HTML stays English', () => {
    const {controller, nativeUser} = fixture();
    nativeUser.context = {lang:'ar_001'};
    controller.state.applied = {date_from:'2026-09-21',date_to:'2026-09-27',as_of:'2026-09-22'};
    controller.state.hrData = {date_from:'2026-09-21',date_to:'2026-09-27',rows:[]};
    const days = controller.hrWeekDays;
    assert.equal(days.length,7);
    assert.equal(days[0].date,'2026-09-21');
    assert.equal(days[0].label,new Intl.DateTimeFormat('ar-001',{weekday:'short',timeZone:'UTC'}).format(new Date('2026-09-21T12:00:00Z')));
    assert.match(days[0].label, /[\u0600-\u06ff]/);
    assert.match(controller.metricPeriodLabel({key:'cash'}), /[\u0600-\u06ff]/);
});


test('stock dashboard pages use the returned size and retain position and totals', async () => {
    const {controller,pending}=fixture();
    controller.state.applied={...controller.state.draft};
    const request=controller.pageStock(8);
    assert.equal(pending[0].args[4],8);
    pending[0].resolve({status:'ready',offset:8,page_size:8,total_count:27,has_more:true,rows:[]});
    await request;
    assert.equal(controller.currentPage(controller.state.inventory),2);
    assert.deepEqual([...controller.pageNumbers(controller.state.inventory)],[1,2,3,4]);
    assert.deepEqual([...controller.stockPageNumbers()].map(row=>row.number),[1,2,3,4]);
    controller.state.inventory.offset=0;
    assert.deepEqual([...controller.stockPageNumbers()].map(row=>row.number),[1,2,null,4]);
});


test('stock date displays today while preserving current versus historical requests', () => {
    const {controller}=fixture();
    controller.defaultOptions={date_to:'2026-09-23'};
    controller.state.stockFilters.at_date='';
    assert.equal(controller.stockDateValue,'2026-09-23');
    controller.changeStockDate({target:{value:'2026-09-20'}});
    assert.equal(controller.state.stockFilters.at_date,'2026-09-20');
    assert.equal(controller.stockDateValue,'2026-09-20');
    controller.changeStockDate({target:{value:'2026-09-23'}});
    assert.equal(controller.state.stockFilters.at_date,'');
});


test('dashboard company selector delegates only authorized choices to the native company API', async () => {
    const {controller,nativeUser}=fixture();
    nativeUser.allowedCompanies=[{id:1,name:'First'},{id:2,name:'Second'}];
    nativeUser.activeCompany={id:1};
    const calls=[];
    nativeUser.activateCompanies=async(ids,options)=>calls.push({ids:[...ids],...options});
    await controller.changeDashboardCompany({target:{value:'999'}});
    await controller.changeDashboardCompany({target:{value:'1'}});
    assert.equal(calls.length,0);
    await controller.changeDashboardCompany({target:{value:'2'}});
    assert.deepEqual(calls,[{ids:[2],includeChildCompanies:false,reload:false}]);
    assert.equal(controller.state.companySwitchPending,false);
    nativeUser.activateCompanies=async()=>{throw new Error('switch failed');};
    await controller.changeDashboardCompany({target:{value:'2'}});
    assert.equal(controller.state.companySwitchPending,false);
});


test('keyboard tabs follow rendered Odoo direction without a DOM dir attribute', () => {
    const { controller } = fixture();
    const selected = [];
    const buttons = [0, 1, 2].map(index => ({focus() {}, click() { selected.push(index); }}));
    const group = {direction: 'rtl', querySelectorAll: () => buttons};
    const press = key => controller.switchTabs({key, target: buttons[1], currentTarget: group, preventDefault() {}});
    press('ArrowRight');
    press('ArrowLeft');
    press('Home');
    press('End');
    assert.deepEqual(selected, [0, 2, 0, 2]);
    group.direction = 'ltr';
    press('ArrowRight');
    assert.equal(selected.at(-1), 2);
});
