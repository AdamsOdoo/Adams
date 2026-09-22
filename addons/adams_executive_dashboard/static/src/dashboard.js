/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useState, useRef, useEffect } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { useSetupAction } from '@web/search/action_hook';
import { _t } from '@web/core/l10n/translation';

export class ExecutiveDashboard extends Component {
    static template = 'adams_executive_dashboard.Dashboard';
    static props = ['*'];

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');
        this.notification = useService('notification');
        this.companyService = useService('company');
        this.hrDepartments = [];
        this.generation = 0;
        this.alive = true;
        this.sections = [
            { key: 'finance', name: _t('Accounting & Finance'), short: _t('Finance'), icon: 'bank', number: '01', description: _t('Your financial position, explained and traceable.') },
            { key: 'sales', name: _t('Sales'), short: _t('Sales'), icon: 'sales', number: '02', description: _t('Commercial performance and fulfillment.') },
            { key: 'crm', name: _t('CRM'), short: _t('CRM'), icon: 'target', number: '03', description: _t('Your pipeline at a glance.') },
            { key: 'inventory', name: _t('Inventory'), short: _t('Inventory'), icon: 'box', number: '04', description: _t('Stock, value and availability.') },
            { key: 'procurement', name: _t('Procurement'), short: _t('Procurement'), icon: 'truck', number: '05', description: _t('Commitments and supplier follow-up.') },
            { key: 'hr', name: _t('Human Resources'), short: _t('HR'), icon: 'people', number: '06', description: _t('Workforce and approved leave.') },
        ];
        this.sections.sort((a, b) => ['finance', 'sales', 'inventory', 'procurement', 'crm', 'hr'].indexOf(a.key) - ['finance', 'sales', 'inventory', 'procurement', 'crm', 'hr'].indexOf(b.key));
        this.labels = {
            revenue: _t('Accounting revenue'), profit: _t('Net profit'), cash: _t('Bank and cash'), cash_flow: _t('Net cash movement'),
            receivables: _t('Receivables'), payables: _t('Payables'), receivables_overdue: _t('Overdue receivables'), payables_overdue: _t('Overdue payables'),
            gross_profit: _t('Gross profit'), operating_expenses: _t('Operating expenses'),
            gross_margin: _t('Gross margin'), net_margin: _t('Net margin'),
            assets: _t('Assets'), liabilities: _t('Liabilities'), equity: _t('Equity'),
            standard_forecast: _t('short-term cash forecast'),
            invoiced_sales: _t('Net invoiced sales'), invoiced_margin: _t('invoiced commercial margin'), confirmed_sales: _t('Confirmed sales'),
            orders: _t('Distinct sales orders'), quotations: _t('Draft and sent quotations'), purchases: _t('Confirmed purchases'),
            inventory: _t('Inventory valuation'), crm: _t('Weighted open pipeline'), hr: _t('Approved leave hours (signed)'),
        };
        this.groupHeadings = { revenue: _t('Profitability'), cash: _t('Liquidity'), receivables: _t('Working capital'), invoiced_sales: _t('Commercial performance') };
        this.statusLabels = {
            not_configured: _t('Not configured'), not_installed: _t('App not installed'),
            restricted: _t('Access restricted'), empty: _t('No matching records'),
            source_only: _t('Open the source report'), unsupported_scope: _t('Unsupported report scope'), error: _t('Report unavailable'),
            undefined_ratio: _t('Undefined ratio: zero denominator'),
        };
        this.dimensionLabels = { customer: _t('Customer'), salesperson: _t('Salesperson'), product: _t('Product'),
            vendor: _t('Vendor'), buyer: _t('Buyer'), stage: _t('Stage'), department: _t('Department') };
        this.dimensions = { invoiced_margin: ['salesperson', 'customer', 'product'], invoiced_sales: ['customer', 'salesperson', 'product'], confirmed_sales: ['customer', 'salesperson', 'product'],
            quotations: ['customer', 'salesperson', 'product'], orders: ['customer', 'salesperson'], purchases: ['vendor', 'buyer', 'product'], crm: ['stage', 'salesperson'], hr: ['department'] };
        this.root = useRef('root');
        this.sourceDialog = useRef('sourceDialog');
        this.analysisDialog = useRef('analysisDialog');
        this.searchDialog = useRef('searchDialog');
        this.printDialog = useRef('printDialog');
        this.searchInput = useRef('searchInput');
        this.employeeDialog = useRef('employeeDialog');
        this.cashDialog = useRef('cashDialog');
        useEffect(() => { const dialog = this.cashDialog.el; if (!dialog) return; if (this.state.cashOpen && !dialog.open) dialog.showModal(); if (!this.state.cashOpen && dialog.open) dialog.close(); }, () => [this.state.cashOpen]);
        useEffect(() => { const dialog = this.employeeDialog.el; if (!dialog) return; if (this.state.employeeProfile && !dialog.open) dialog.showModal(); if (!this.state.employeeProfile && dialog.open) dialog.close(); }, () => [this.state.employeeProfile]);
        this.searchKinds = { all: _t('All documents'), invoices: _t('Customer invoices'), bills: _t('Vendor bills'), orders: _t('Sales orders'), quotations: _t('Quotations') };
        this.workspaceMenu = useRef('workspaceMenu');
        this.workspaceToggle = useRef('workspaceToggle');
        this.detailGeneration = 0;
        this.state = useState({ workspaceDetails: {}, cashOpen: false, periodPreset: 'month', cutoffOpen: false, searchOpen: false, moreOpen: false, logoFailed: false, stockMode: 'current', stockError: '', hrTab: 'overview', hrFilters: {search: '', department_id: '', employee_id: '', status: '', assignment: '', view: 'week'}, hrData: null, employeeProfile: null, sectionOrder: [], layoutOpen: false, rankLimit: 5, productMeasure: 'value', productUnit: '', orderRanking: null, stockFilters: {warehouse_id: '', category_id: '', search: '', hide_zero: true, hide_negative: false, at_date: ''}, printSummary: null, searchQuery: '', searchKind: 'all', search: null, companies: [], draft: {}, applied: null, sections: {}, error: '', opening: false,
            collapsed: { crm: true, inventory: true, procurement: true, hr: true }, activeSection: 'finance', sidebarOpen: false, detail: null, directory: null, cashSearch: '', inventory: null, workforce: null, procurement: null, ranking: null, customers: null, products: null, canConfigure: false, source: null, financialTrends: {}, fulfillment: null, recent: null, exporting: false, restored: false, savedView: false, attentionExpanded: false });
        useEffect(() => {
            const dialog = this.printDialog.el;
            if (!dialog) return;
            if (this.state.printSummary && !dialog.open) dialog.showModal();
            if (!this.state.printSummary && dialog.open) dialog.close();
        }, () => [this.state.printSummary]);
        useEffect(() => {
            const dialog = this.searchDialog.el;
            if (!dialog) return;
            if (this.state.search && !dialog.open) dialog.showModal();
            if (!this.state.search && dialog.open) dialog.close();
        }, () => [this.state.search]);
        useEffect(() => {
            const dialog = this.sourceDialog.el;
            if (!dialog) return;
            if (this.state.source && !dialog.open) dialog.showModal();
            if (!this.state.source && dialog.open) dialog.close();
        }, () => [this.state.source]);
        useEffect(() => {
            if (this.state.sidebarOpen) this.workspaceMenu.el?.querySelector('button')?.focus();
        }, () => [this.state.sidebarOpen]);
        useEffect(() => {
            const dialog = this.analysisDialog.el;
            if (!dialog) return;
            if (this.state.detail && !dialog.open) dialog.showModal();
            if (!this.state.detail && dialog.open) dialog.close();
        }, () => [this.state.detail]);
        useEffect(() => {
            const root = this.root.el;
            if (!root) return;
            let frame;
            const schedule = () => {
                if (frame) return;
                frame = requestAnimationFrame(() => {
                    frame = null;
                    if (this.alive) this.syncActiveSection();
                });
            };
            const manual = event => {
                if (event.type !== 'keydown' || ['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) {
                    this.scrollTarget = null;
                    schedule();
                }
            };
            root.addEventListener('scroll', schedule, { passive: true });
            for (const event of ['wheel', 'touchstart', 'pointerdown', 'keydown']) root.addEventListener(event, manual, { passive: true });
            const observer = new ResizeObserver(schedule);
            observer.observe(root);
            for (const node of root.querySelectorAll('.adams_section, .adams_nav')) observer.observe(node);
            schedule();
            return () => {
                if (frame) cancelAnimationFrame(frame);
                root.removeEventListener('scroll', schedule);
                for (const event of ['wheel', 'touchstart', 'pointerdown', 'keydown']) root.removeEventListener(event, manual);
                observer.disconnect();
            };
        }, () => [this.visibleSections.map(section => section.key).join(',')]);
        useSetupAction({ getLocalState: () => ({ dashboard: this.navigationState() }) });
        useEffect(() => {
            if (this.state.restored && this.restoreScroll !== null && this.root.el) {
                this.root.el.scrollTop = this.restoreScroll;
                this.restoreScroll = null;
            }
        }, () => [this.state.restored]);
        onWillStart(async () => {
            try {
                const data = await this.orm.call('adams.executive.dashboard', 'get_bootstrap', []);
                if (!this.alive) { return; }
                this.state.companies = data.companies;
                this.state.canConfigure = data.can_configure;
                this.userId = data.user_id;
                this.defaultOptions = { ...data.options };
                const savedNavigation = this.props.state?.dashboard;
                const restore = savedNavigation?.userId === data.user_id && savedNavigation.applied?.company_id === data.options.company_id &&
                    data.companies.some(company => company.id === savedNavigation.applied?.company_id)
                    ? savedNavigation : null;
                this.state.draft = restore ? { ...restore.applied } : data.options;
                this.preferenceKey = `adams-dashboard-v1-${data.user_id}`;
                try { this.state.sectionOrder = JSON.parse(window.localStorage.getItem(this.preferenceKey + '-order') || '[]'); if (!Array.isArray(this.state.sectionOrder)) this.state.sectionOrder = []; } catch { this.state.sectionOrder = []; }
                this.viewKey = `adams-dashboard-view-v1-${data.user_id}`;
                this.state.savedView = Boolean(this.readSavedView());
                try {
                    const saved = JSON.parse(window.localStorage.getItem(this.preferenceKey) || '{}');
                    for (const section of this.sections) {
                        if (typeof saved[section.key] === 'boolean') { this.state.collapsed[section.key] = saved[section.key]; }
                    }
                } catch { /* Storage may be unavailable; dashboard remains usable. */ }
                // Render the shell while each section completes independently.
                void this.restoreNavigation(restore);
            } catch {
                this.state.error = _t('The dashboard could not be loaded. Check your access and try again.');
            }
        });
        onWillUnmount(() => { this.alive = false; this.generation++; });
    }

    navigationState() {
        const selection = (value, keys) => value ? Object.fromEntries(keys.map(key => [key, value[key]])) : null;
        return { userId: this.userId, applied: this.state.applied ? { ...this.state.applied } : null,
            sectionOrder: [...this.state.sectionOrder], search: selection(this.state.search, ['query', 'kind', 'offset']), hr: this.state.hrData ? {tab: this.state.hrTab, filters: {...this.state.hrData.filters}, offset: this.state.hrData.offset || 0} : null, stockMode: this.state.stockMode,
            collapsed: { ...this.state.collapsed }, activeSection: this.state.activeSection, scroll: this.root.el?.scrollTop || 0,
            detail: selection(this.state.detail, ['key', 'dimension', 'offset']),
            recent: selection(this.state.recent, ['kind', 'offset']),
            ranking: selection(this.state.ranking, ['key']), rankLimit: this.state.rankLimit, productMeasure: this.state.productMeasure, productUnit: this.state.productUnit,
            procurement: selection(this.state.procurement, ['offset', 'mode']), directory: selection(this.state.directory, ['offset', 'search']), inventory: selection(this.state.inventory, ['offset', 'mode', 'filters']), workforce: selection(this.state.workforce, ['offset']), fulfillment: selection(this.state.fulfillment, ['offset']) };
    }

    async restoreNavigation(saved) {
        if (saved?.rankLimit === 5 || saved?.rankLimit === 10) this.state.rankLimit = saved.rankLimit;
        if (['value', 'quantity'].includes(saved?.productMeasure)) this.state.productMeasure = saved.productMeasure;
        const generation = this.generation + 1;
        await this.refresh(Boolean(saved));
        if (!this.alive || generation !== this.generation || !saved) { return; }
        const jobs = [];
        if (Array.isArray(saved.sectionOrder)) this.state.sectionOrder = saved.sectionOrder.filter(key => this.sectionEnabled(key));
        if (saved.search) { this.state.searchQuery = saved.search.query; this.state.searchKind = saved.search.kind; jobs.push(this.searchRecords(null, saved.search.offset)); }
        if (saved.hr && this.sectionEnabled('hr')) { this.state.hrFilters = {...saved.hr.filters}; jobs.push(this.loadHR(saved.hr.tab, saved.hr.offset)); }
        if (this.sectionEnabled('sales') && saved.productMeasure === 'quantity' && Number(saved.productUnit) > 0) {
            this.state.productUnit = String(saved.productUnit);
            jobs.push(this.loadProducts());
        }
        if (this.visibleSections.some(section => section.key === saved.activeSection)) this.state.activeSection = saved.activeSection;
        if (saved.detail && this.sectionEnabled(['invoiced_sales', 'invoiced_margin', 'confirmed_sales', 'quotations', 'orders'].includes(saved.detail.key) ? 'sales' : ({purchases: 'procurement', crm: 'crm', hr: 'hr'}[saved.detail.key] || 'finance')) && this.dimensions[saved.detail.key]?.includes(saved.detail.dimension)) {
            jobs.push(this.inspect(saved.detail.key, saved.detail.dimension, saved.detail.offset));
        }
        if (this.sectionEnabled('sales') && saved.recent && ['orders', 'quotations'].includes(saved.recent.kind)) {
            jobs.push(this.loadRecent(saved.recent.kind, saved.recent.offset));
        }
        if (this.sectionEnabled('sales') && ['invoiced_sales', 'invoiced_margin'].includes(saved.ranking?.key)) {
            jobs.push(this.loadRanking(saved.ranking.key));
        }
        if (this.sectionEnabled('finance') && saved.directory) { this.state.cashSearch = saved.directory.search || ''; jobs.push(this.loadDirectory('cash', saved.directory.offset, null, this.state.cashSearch)); }
        if (this.sectionEnabled('sales') && saved.fulfillment) { jobs.push(this.loadDirectory('fulfillment', saved.fulfillment.offset)); }
        if (this.sectionEnabled('procurement') && saved.procurement) { jobs.push(this.loadDirectory('procurement', saved.procurement.offset, saved.procurement.mode)); }
        if (this.sectionEnabled('hr') && saved.workforce) { jobs.push(this.loadDirectory('workforce', saved.workforce.offset)); }
        if (this.sectionEnabled('inventory') && saved.inventory) { if (saved.inventory.filters) this.state.stockFilters = {...this.state.stockFilters, ...saved.inventory.filters}; jobs.push(this.loadDirectory('inventory', saved.inventory.offset, saved.inventory.mode || 'current')); }
        for (const section of this.sections) {
            if (typeof saved.collapsed?.[section.key] === 'boolean') { this.state.collapsed[section.key] = saved.collapsed[section.key]; }
        }
        await Promise.all(jobs);
        if (this.alive && generation === this.generation) {
            this.restoreScroll = Number.isFinite(saved.scroll) ? Math.max(0, saved.scroll) : 0;
            this.state.restored = true;
        }
    }

    async loadRecent(kind, offset = 0) {
        const generation = this.generation;
        const request = (this.recentRequest || 0) + 1;
        this.recentRequest = request;
        this.state.recent = { kind, offset, status: 'loading', rows: [] };
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_recent_sales', [kind, { ...this.state.applied }, offset]);
            if (this.alive && generation === this.generation && request === this.recentRequest) {
                this.state.recent = { ...data, kind, offset };
            }
        } catch {
            if (this.alive && generation === this.generation && request === this.recentRequest) {
                this.state.recent = { kind, offset, status: 'error', rows: [] };
            }
        }
    }

    async openRecent(recordId = null) {
        if (this.state.opening || !this.state.recent) { return; }
        const generation = this.generation;
        const recent = this.state.recent;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_recent_sale', [recent.kind, { ...this.state.applied }, recordId]);
            if (this.alive && generation === this.generation && recent === this.state.recent) { await this.action.doAction(action); }
        } catch {
            if (this.alive) { this.notification.add(_t('The sales record could not be opened. Check your access and filters.'), { type: 'warning' }); }
        } finally { if (this.alive) { this.state.opening = false; } }
    }

    async refresh(resetAux = false) {
        resetAux = resetAux === true;
        const options = { ...this.state.draft, company_id: this.companyService?.currentCompany?.id || Number(this.state.draft.company_id) };
        const validation = this.validateScope(options);
        if (validation) { this.state.error = validation; return; }
        const generation = ++this.generation;
        const sameCompany = this.state.applied?.company_id === options.company_id;
        const previousRecent = sameCompany && !resetAux ? this.state.recent?.kind : 'orders';
        const previousRanking = sameCompany && !resetAux ? this.state.ranking?.key : 'invoiced_sales';
        const previousInventory = sameCompany ? this.state.inventory : null;
        const previousHR = sameCompany ? this.state.hrTab : 'overview';
        this.state.employeeProfile = null;
        this.state.cashOpen = false;
        this.state.hrData = null;
        this.hrDepartments = [];
        this.state.workspaceDetails = {};
        this.state.logoFailed = false;
        this.analysisTrends = {};
        if (!sameCompany) { this.state.hrFilters = {search: '', department_id: '', employee_id: '', status: '', assignment: '', view: 'week'}; this.state.productUnit = ''; }

        if (this.state.applied?.company_id !== options.company_id) {
            this.state.stockFilters = {...this.state.stockFilters, warehouse_id: '', category_id: ''};
        }
        this.state.applied = options;
        if (this.companyService) void this.refreshCompanyIdentity(generation);
        this.closeSearch();
        this.state.printSummary = null;
        this.state.detail = null;
        this.state.directory = null;
        this.state.cashSearch = '';
        this.state.inventory = null;
        this.state.workforce = null;
        this.state.procurement = null;
        this.state.ranking = null;
        this.state.customers = null;
        this.state.products = null;
        this.state.orderRanking = null;
        this.scrollTarget = null;
        this.closeSource();
        this.state.financialTrends = {};
        this.state.fulfillment = null;
        this.state.recent = null;
        this.detailGeneration++;
        this.state.error = '';
        // Immediately remove previous-company values, including during failures.
        const enabled = this.visibleSections.map(section => section.key);
        if (!enabled.includes(this.state.activeSection)) this.state.activeSection = enabled[0] || '';
        const sources = ['finance', 'sales', 'operations'].filter(key => key === 'operations' ? enabled.some(entry => !['finance', 'sales'].includes(entry)) : enabled.includes(key));
        this.state.sections = Object.fromEntries(sources.map(key => [key, { status: 'loading', items: [] }]));
        await Promise.all(sources.map(async key => {
            try {
                const data = await this.orm.call('adams.executive.dashboard', 'get_section', [key, options]);
                if (this.alive && generation === this.generation) {
                    this.state.sections[key] = { ...data, status: 'ready' };
                    if (key === 'sales' && data.items.some(item => item.key === 'invoiced_sales' && item.status === 'ready')) { if (!this.state.recent) void this.loadRecent(previousRecent || 'orders'); if (!this.state.ranking) void this.loadRanking(previousRanking || 'invoiced_sales'); void this.loadCustomers(); }
                    if (key === 'sales' && data.items.some(item => item.key === 'invoiced_sales' && item.status)) { void this.loadProducts(); void this.loadOrderRanking(); }
                    if (key === 'finance' && data.items.some(item => item.key === 'cash' && item.status === 'ready')) { void this.loadDirectory('cash'); }
                    if (key === 'finance' && ['revenue', 'gross_profit', 'profit'].every(metric => data.items.some(item => item.key === metric && item.status === 'ready'))) { void this.loadProfitabilityChart(); }
                }
            } catch {
                if (this.alive && generation === this.generation) {
                    this.state.sections[key] = { status: 'error', items: [] };
                }
            }
        }));
        if (this.alive && generation === this.generation) {
            if (previousInventory && this.sectionEnabled('inventory')) {
                this.state.inventory = {filters: {...previousInventory.filters}, mode: previousInventory.mode};
                void this.pageStock(0);
            }
            if (['crm','procurement'].includes(this.state.activeSection)) void this.loadWorkspaceDetails(this.state.activeSection);
            if (this.state.activeSection === 'hr' && this.sectionEnabled('hr')) void this.loadHR(previousHR);
        }
    }

    sectionResult(section) {
        const source = this.state.sections[['finance', 'sales'].includes(section.key) ? section.key : 'operations'];
        if (!source || ['finance', 'sales'].includes(section.key)) { return source; }
        const key = section.key === 'procurement' ? 'purchases' : section.key;
        return { ...source, items: source.items.filter(item => item.key === key) };
    }

    metricGroups(section, result) {
        // Native stock quantities and valuation live in the product workspace below.
        // There is no separate accounting valuation mapping in the agreed scope.
        if (section.key === 'inventory') { return []; }
        const select = keys => keys.map(key => result.items.find(item => item.key === key)).filter(Boolean);
        if (section.key === 'finance') {
            return [
                { key: 'profitability', name: _t('Profitability'), description: _t('Performance during the selected financial period.'), items: select(['revenue', 'gross_profit', 'profit', 'operating_expenses']) },
                { key: 'working-capital', name: _t('Cash and working capital'), description: _t('Balances at the selected cutoff.'), items: select(['cash', 'receivables', 'payables']) },
                { key: 'liquidity', name: _t('Money movement'), description: _t('Recorded cash movement and a separately labelled forecast.'), items: [this.cashMovement(result), ...select(['standard_forecast'])] },
                { key: 'financial-position', name: _t('Financial position'), description: _t('Balance Sheet at the selected cutoff.'), items: select(['assets', 'liabilities', 'equity']) },
            ];
        }
        if (section.key === 'sales') { return [{ key: 'commercial', name: _t('Commercial performance'), description: _t('Invoiced sales, order intake and quotations are different measures.'), items: select(['invoiced_sales', 'confirmed_sales', 'quotations']) }]; }
        return [{ key: section.key, name: '', description: '', items: result.items }];
    }

    metricIcon(key) {
        return { revenue: 'chart', gross_profit: 'trend', profit: 'coins', operating_expenses: 'wallet',
            cash: 'bank', cash_flow: 'trend', standard_forecast: 'calendar', receivables: 'invoice', payables: 'invoice',
            invoiced_sales: 'invoice', invoiced_margin: 'trend', confirmed_sales: 'sales', orders: 'box',
            quotations: 'invoice', purchases: 'truck', inventory: 'box', crm: 'target', hr: 'people' }[key] || 'chart';
    }

    cashMovement(result) {
        const flow = result.cash_flow;
        return { key: 'cash_flow', status: flow?.status || 'not_installed',
            value: flow?.bridge?.net_increase?.value ?? null, unit: 'currency', date_field: 'period',
            source: flow?.source, measure: 'net_increase', drilldown: flow?.status === 'ready',
            definition: _t('Net cash movement recorded during the selected period.'),
            has_warnings: flow?.has_warnings };
    }

    financeMetric(key) {
        return this.state.sections.finance?.items.find(item => item.key === key);
    }

    get filtersDirty() {
        return this.state.applied && ['company_id', 'date_from', 'date_to', 'as_of'].some(key => String(this.state.draft[key]) !== String(this.state.applied[key]));
    }

    pageNumbers(data) {
        const current = Math.floor((data?.offset || 0) / 25) + 1;
        const total = Number.isInteger(data?.total_count) ? Math.max(1, Math.ceil(data.total_count / 25)) : current + (data?.has_more ? 1 : 0);
        const start = Math.max(1, Math.min(current - 2, total - 4));
        return [...new Set([1, ...Array.from({length: Math.min(5, total - start + 1)}, (_, i) => start + i), ...(data?.total_count !== undefined ? [total] : [])])];
    }

    setAllSections(collapsed) {
        for (const section of this.visibleSections) this.state.collapsed[section.key] = collapsed;
        try { window.localStorage.setItem(this.preferenceKey, JSON.stringify(this.state.collapsed)); } catch { /* Optional storage. */ }
    }

    moveSection(key, direction) {
        const keys = this.visibleSections.map(section => section.key);
        const index = keys.indexOf(key), target = index + direction;
        if (target < 0 || target >= keys.length) return;
        [keys[index], keys[target]] = [keys[target], keys[index]];
        this.state.sectionOrder = [...keys, ...this.sections.map(s => s.key).filter(k => !keys.includes(k))];
        try { window.localStorage.setItem(this.preferenceKey + '-order', JSON.stringify(this.state.sectionOrder)); } catch { /* Optional storage. */ }
    }

    async retrySection(section) {
        const key = ['finance', 'sales'].includes(section) ? section : 'operations';
        const generation = this.generation;
        const marker = {};
        this.sectionRetries ||= {};
        this.sectionRetries[key] = marker;
        this.state.sections[key] = {status: 'loading', items: []};
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_section', [key, {...this.state.applied}]);
            if (this.alive && generation === this.generation && this.sectionRetries[key] === marker) {
                this.state.sections[key] = {...data, status: 'ready'};
                if (key === 'sales') void this.refreshRankings();
                if (key === 'finance') { void this.loadDirectory('cash'); void this.loadProfitabilityChart(); }
            }
        } catch {
            if (this.alive && generation === this.generation && this.sectionRetries[key] === marker) this.state.sections[key] = {status: 'error', items: []};
        }
    }

    async refreshRankings() {
        return Promise.all([this.loadRanking(this.state.ranking?.key || 'invoiced_sales'), this.loadCustomers(), this.loadProducts(), this.loadOrderRanking()]);
    }

    async loadOrderRanking() {
        const generation = this.generation, marker = {};
        this.orderRankingRequest = marker;
        this.state.orderRanking = {status: 'loading', rows: []};
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_breakdown', ['confirmed_sales', 'salesperson', {...this.state.applied}]);
            if (this.alive && generation === this.generation && this.orderRankingRequest === marker) this.state.orderRanking = {...data, rows: data.rows.slice(0, this.state.rankLimit || 5)};
        } catch {
            if (this.alive && generation === this.generation && this.orderRankingRequest === marker) this.state.orderRanking = {status: 'error', rows: []};
        }
    }

    async openStockRow(row) {
        if (this.state.opening || !this.state.inventory) return;
        const generation = this.generation;
        const data = this.state.inventory;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_inventory_location', [{...this.state.applied}, row.product_id, row.location_id, data.mode, data.filters]);
            if (this.alive && generation === this.generation && this.state.inventory === data) await this.action.doAction(action);
        } catch {
            if (this.alive && generation === this.generation) this.notification.add(_t('This stock report could not be opened. Check your access and try again.'), {type: 'warning'});
        } finally { if (this.alive) this.state.opening = false; }
    }

    get visibleSections() {
        const company = this.state.companies.find(entry => entry.id === this.state.applied?.company_id);
        const enabled = company?.enabled_sections;
        const sections = enabled ? this.sections.filter(section => enabled.includes(section.key)) : [...this.sections];
        const order = this.state.sectionOrder || [];
        return sections.sort((a, b) => (order.includes(a.key) ? order.indexOf(a.key) : 99) - (order.includes(b.key) ? order.indexOf(b.key) : 99));
    }

    sectionEnabled(key) { return this.visibleSections.some(section => section.key === key); }

    openSettings() {
        return this.action.doAction('adams_executive_dashboard.action_dashboard_settings', {
            additionalContext: {allowed_company_ids: [this.state.applied.company_id], default_company_id: this.state.applied.company_id},
        });
    }

    scrollOffset() {
        return (this.root.el?.querySelector('.adams_nav')?.getBoundingClientRect().height || 0) + 16;
    }

    syncActiveSection() { /* Explicit department navigation owns the active state. */ }

    navigateSection(key) {
        if (!this.sectionEnabled(key)) return;
        this.state.activeSection = key;
        this.state.collapsed[key] = false;
        this.state.sidebarOpen = false;
        this.root.el?.scrollTo?.({top: 0});
        if (key === 'inventory' && !this.state.inventory) void this.applyStockFilters();
        if (key === 'procurement' && !this.state.procurement) void this.loadDirectory('procurement');
        if (key === 'hr' && !this.state.hrData) void this.loadHR();
        if (['crm','procurement'].includes(key) && !this.state.workspaceDetails[key]) void this.loadWorkspaceDetails(key);
    }

    supplierWindow(key) {
        return this.state.sections.finance?.supplier_windows?.find(item => item.key === key);
    }

    get supplierStatus() {
        return this.statusLabels[this.financeMetric('payables')?.status] ||
            this.statusLabels[this.state.sections.finance?.status] || this.statusLabels.not_configured;
    }

    navigateWorkspace(event, id) {
        event.preventDefault();
        this.state.sidebarOpen = false;
        if (id === 'adams-attention') this.state.attentionExpanded = true;
        requestAnimationFrame(() => { const node = this.root.el?.querySelector('#' + id); if (node?.tagName === 'DETAILS') node.open = true; node?.scrollIntoView({ block: 'start' }); node?.querySelector('button, summary')?.focus(); });
    }

    closeSearch() { this.state.search = null; }

    async searchRecords(event = null, offset = 0) {
        event?.preventDefault();
        const query = (this.state.searchQuery || '').trim();
        if (query.length < 2 || query.length > 100 || !this.state.applied) { this.notification.add(_t('Enter between 2 and 100 characters to search.'), {type: 'warning'}); return; }
        const generation = this.generation;
        this.state.search = { query, kind: this.state.searchKind || 'all', offset, status: 'loading', groups: [] };
        const search = this.state.search;
        try {
            const result = await this.orm.call('adams.executive.dashboard', 'search_records', [query, { ...this.state.applied }, search.kind, offset]);
            if (this.alive && generation === this.generation && this.state.search === search) Object.assign(search, result, { status: 'ready' });
        } catch {
            if (this.alive && generation === this.generation && this.state.search === search) search.status = 'error';
        }
    }

    async openSearchRecord(kind, id) {
        if (this.state.opening || !this.state.search) return;
        const generation = this.generation;
        const search = this.state.search;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_search_record', [search.query, { ...this.state.applied }, kind, id]);
            if (this.alive && generation === this.generation && search === this.state.search) {
                await this.action.doAction(action);
            }
        } catch {
            if (this.alive) this.notification.add(_t('The record is unavailable in the selected scope.'), { type: 'warning' });
        } finally { if (this.alive) this.state.opening = false; }
    }

    closePrint() { this.state.printSummary = null; }
    printNow() { window.print(); }

    printValue(row) {
        return row.value === null ? '—' : new Intl.NumberFormat(document.documentElement.lang || 'en', {
            minimumFractionDigits: row.digits ?? this.state.printSummary.currency_digits,
            maximumFractionDigits: row.digits ?? this.state.printSummary.currency_digits,
        }).format(row.value);
    }

    async printDashboard() {
        this.state.moreOpen = false;
        if (!this.state.applied || this.state.exporting) return;
        const generation = this.generation;
        this.state.exporting = true;
        this.state.printSummary = null;
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'export_summary', [{ ...this.state.applied }]);
            if (!this.alive || generation !== this.generation) return;
            this.state.printSummary = data;

        } catch {
            if (this.alive && generation === this.generation) this.notification.add(_t('Export unavailable. Check your export permissions or use the report for large exports.'), { type: 'warning' });
        } finally { if (this.alive) this.state.exporting = false; }
    }

    async exportSummary() {
        this.state.moreOpen = false;
        if (!this.state.applied || this.state.exporting) return;
        const generation = this.generation;
        this.state.exporting = true;
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'export_summary', [{ ...this.state.applied }]);
            if (!this.alive || generation !== this.generation) return;
            const url = URL.createObjectURL(new Blob([data.content], { type: 'text/csv;charset=utf-8' }));
            const anchor = document.createElement('a');
            anchor.href = url; anchor.download = data.filename; anchor.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch {
            if (this.alive && generation === this.generation) this.notification.add(_t('Export unavailable. Check your export permissions or use the report for large exports.'), { type: 'warning' });
        } finally { if (this.alive) this.state.exporting = false; }
    }

    switchTabs(event) {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        const buttons = [...event.currentTarget.querySelectorAll('button')];
        const current = buttons.indexOf(event.target);
        if (current < 0) return;
        event.preventDefault();
        const rtl = document.documentElement.dir === 'rtl';
        const delta = (event.key === 'ArrowRight' ? 1 : -1) * (rtl ? -1 : 1);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 :
            (current + delta + buttons.length) % buttons.length;
        buttons[next].focus();
        buttons[next].click();
    }

    navigateGroup(key) {
        this.root.el?.querySelector(`#adams-group-${key}`)?.scrollIntoView({ block: 'start',
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    }

    get hasFinanceWarnings() {
        const finance = this.state.sections.finance;
        return Boolean(finance?.items?.some(item => item.has_warnings) ||
            finance?.cash_flow?.has_warnings || finance?.supplier_windows?.some(item => item.has_warnings));
    }

    readSavedView() {
        try {
            const saved = JSON.parse(window.localStorage.getItem(this.viewKey) || 'null');
            const dates = ['date_from', 'date_to', 'as_of'];
            if (saved?.userId !== this.userId || (this.companyService?.currentCompany && saved.applied?.company_id !== this.companyService.currentCompany.id) || !this.state.companies.some(company => company.id === saved.applied?.company_id) ||
                !dates.every(key => /^\d{4}-\d{2}-\d{2}$/.test(saved.applied?.[key] || '')) ||
                saved.applied.date_from > saved.applied.date_to) return null;
            return saved;
        } catch { return null; }
    }

    saveView() {
        if (!this.state.applied) return;
        // Store selections only, never amounts, records, permissions or theme.
        const applied = Object.fromEntries(['company_id', 'date_from', 'date_to', 'as_of']
            .map(key => [key, this.state.applied[key]]));
        try {
            window.localStorage.setItem(this.viewKey, JSON.stringify({...this.navigationState(), applied, recent: this.state.recent ? {kind: this.state.recent.kind, offset: 0} : null, detail: null, scroll: 0}));
            this.state.savedView = true;
            this.notification.add(_t('View saved in this browser.'), { type: 'success' });
        } catch {
            this.notification.add(_t('Browser storage is unavailable. The view could not be saved.'), { type: 'warning' });
        }
    }

    async restoreView() {
        this.state.moreOpen = false;
        const saved = this.readSavedView();
        if (!saved) {
            this.state.savedView = false;
            this.notification.add(_t('The saved view is unavailable for your current access.'), { type: 'warning' });
            return;
        }
        this.state.draft = { ...saved.applied };
        await this.restoreNavigation(saved);
    }

    async resetView() {
        this.state.moreOpen = false;
        if (!this.defaultOptions) return;
        this.state.draft = { ...this.defaultOptions };
        this.state.sectionOrder = [];
        this.state.rankLimit = 5;
        this.state.productMeasure = 'value';
        this.state.stockFilters = {warehouse_id: '', category_id: '', search: '', hide_zero: true, hide_negative: false, at_date: ''};
        try { window.localStorage.setItem(this.preferenceKey + '-order', '[]'); } catch { /* Optional. */ }
        this.state.collapsed = { crm: true, inventory: true, procurement: true, hr: true };
        try { window.localStorage.setItem(this.preferenceKey, JSON.stringify(this.state.collapsed)); } catch { /* Optional. */ }
        this.state.activeSection = 'finance';
        this.state.sidebarOpen = false;
        await this.refresh();
        this.root.el?.scrollTo({ top: 0 });
    }

    openCashDirectory() { this.state.cashOpen = true; if (!this.state.directory) void this.loadDirectory('cash'); }
    closeCashDirectory() { this.state.cashOpen = false; }
    toggleMore() { this.state.moreOpen = !this.state.moreOpen; }
    closeMore() { this.state.moreOpen = false; }

    closeWorkspace() {
        this.state.sidebarOpen = false;
        this.workspaceToggle.el?.focus();
    }

    workspaceKeydown(event) {
        if (event.key === 'Escape') this.closeMore();
        if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName) &&
                !event.target.isContentEditable && !this.state.search && !this.state.printSummary && !this.state.source && !this.state.detail) {
            event.preventDefault();
            this.searchInput.el?.focus();
        }
        if (event.key === 'Escape' && this.state.sidebarOpen) {
            event.preventDefault();
            this.closeWorkspace();
        }
    }

    openSource(item, result) {
        this.state.source = { item, result };
    }

    closeSource() { this.state.source = null; }

    headline(item, section) {
        if (typeof item.value !== 'number' || Math.abs(item.value) < 1000000) return this.formatted(item, section);
        return new Intl.NumberFormat(document.documentElement.lang || 'en', {
            notation: 'compact', maximumFractionDigits: 2,
        }).format(item.value);
    }

    async loadCustomers() {
        const generation = this.generation;
        const marker = {};
        this.customerRequest = marker;
        this.state.customers = { status: 'loading', rows: [] };
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_breakdown', ['invoiced_sales', 'customer', { ...this.state.applied }]);
            if (this.alive && generation === this.generation && marker === this.customerRequest) {
                this.state.customers = { ...data, rows: data.rows.slice(0, this.state.rankLimit || 5) };
            }
        } catch {
            if (this.alive && generation === this.generation && marker === this.customerRequest) {
                this.state.customers = { status: 'error', rows: [] };
            }
        }
    }

    async loadProducts() {
        const generation = this.generation;
        const marker = {};
        this.productRequest = marker;
        this.state.products = { status: 'loading', rows: [] };
        try {
            const data = this.state.productMeasure === 'quantity'
                ? await this.orm.call('adams.executive.dashboard', 'get_product_quantity_ranking', [{...this.state.applied}, Number(this.state.productUnit) || false])
                : await this.orm.call('adams.executive.dashboard', 'get_breakdown', ['invoiced_sales', 'product', { ...this.state.applied }]);
            if (this.alive && generation === this.generation && marker === this.productRequest) {
                if (data.unit_id) this.state.productUnit = String(data.unit_id);
                this.state.products = { ...data, rows: data.rows.slice(0, this.state.rankLimit || 5) };
            }
        } catch {
            if (this.alive && generation === this.generation && marker === this.productRequest) {
                this.state.products = { status: 'error', rows: [] };
            }
        }
    }

    async loadProfitabilityChart() {
        const generation = this.generation, marker = {};
        this.profitabilityRequest = marker;
        const keys = ['revenue', 'gross_profit', 'profit'];
        for (const key of keys) this.state.financialTrends[key] = {status: 'loading', rows: []};
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_financial_trends', [keys, {...this.state.applied}]);
            if (this.alive && generation === this.generation && marker === this.profitabilityRequest) for (const key of keys) this.state.financialTrends[key] = data.series[key];
        } catch { if (this.alive && generation === this.generation && marker === this.profitabilityRequest) for (const key of keys) this.state.financialTrends[key] = {status: 'error', rows: []}; }
    }

    profitabilityChart() {
        const keys = ['revenue', 'gross_profit', 'profit'];
        const data = keys.map(key => this.state.financialTrends[key]);
        if (data.some(value => value?.status === 'loading')) { return { status: 'loading', rows: [] }; }
        if (!data.some(Boolean)) { return { status: 'idle', rows: [] }; }
        if (data.some(value => value?.status !== 'ready')) { return { status: 'unavailable', rows: [] }; }
        const labels = [...new Set(data.flatMap(value => value.rows.map(row => row.label)))];
        const values = data.flatMap(value => value.rows.map(row => row.value)).filter(Number.isFinite);
        const peak = Math.max(1, ...values.map(Math.abs));
        const step = 10 ** Math.floor(Math.log10(peak)) / 2;
        const maximum = Math.ceil(Math.max(0, ...values) * 1.1 / step) * step || 1;
        const minimum = Math.floor(Math.min(0, ...values) * 1.1 / step) * step;
        const scale = value => 19 + (maximum - value) / (maximum - minimum) * 174;
        const zero = scale(0);
        const width = Math.max(680, labels.length * 104);
        const number = value => new Intl.NumberFormat(document.documentElement.lang || 'en', {
            notation: 'compact', maximumFractionDigits: 1 }).format(value);
        return { status: 'ready', zero, width, ticks: Array.from({ length: 5 }, (_, index) => {
            const value = minimum + (maximum - minimum) * index / 4;
            return { label: number(value), y: scale(value) };
        }), rows: labels.sort().map((label, monthIndex) => ({ label,
            x: 67 + (width - 82) / labels.length * (monthIndex + 0.5),
            series: keys.map((key, index) => {
                const row = data[index].rows.find(value => value.label === label);
                const value = Number.isFinite(row?.value) ? row.value : null;
                return { ...row, key, value,
                    x: 67 + (width - 82) / labels.length * (monthIndex + 0.5) + (index - 1) * 29 - 12,
                    y: value === null ? zero : Math.min(scale(value), zero),
                    height: value === null ? 0 : Math.max(1, Math.abs(scale(value) - zero)) };
            }) })) };
    }

    chartKeydown(event, key, month) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            void this.openFinancialPeriod(key, month);
        }
    }

    guidance(text) {
        return typeof text === 'string' ? text.replace(/\bnative\s+/gi, '') : text;
    }

    formatted(item, section) {
        if (item.value === null) { return this.statusLabels[item.status] || '—'; }
        return new Intl.NumberFormat(document.documentElement.lang || 'en', {
            maximumFractionDigits: item.key === 'orders' ? 0 : section.digits,
            minimumFractionDigits: item.key === 'orders' ? 0 : section.digits,
        }).format(item.value);
    }

    toggleSection(key) {
        this.state.collapsed[key] = !this.state.collapsed[key];
        try { window.localStorage.setItem(this.preferenceKey, JSON.stringify(this.state.collapsed)); } catch { /* Optional. */ }
    }

    async inspect(key, dimension = null, offset = 0) {
        const generation = this.generation;
        const request = ++this.detailGeneration;
        dimension ||= this.dimensions[key][0];
        this.closeSource();
        const trendKey = JSON.stringify([this.state.applied, key]);
        const cachedTrend = this.analysisTrends?.[trendKey];
        this.state.detail = { key, dimension, offset, status: 'loading', rows: [], trend: cachedTrend?.rows || [] };
        try {
            const [groups, trend] = await Promise.all([
                this.orm.call('adams.executive.dashboard', 'get_breakdown', [key, dimension, { ...this.state.applied }, offset]),
                cachedTrend || this.orm.call('adams.executive.dashboard', 'get_trend', [key, { ...this.state.applied }]),
            ]);
            if (this.alive && generation === this.generation && request === this.detailGeneration) {
                if (trend.status === 'ready' || !trend.status) { this.analysisTrends ||= {}; this.analysisTrends[trendKey] = trend; }
                this.state.detail = { ...groups, key, dimension, offset, trend: trend.rows || [], status: groups.status };
            }
        } catch {
            if (this.alive && generation === this.generation && request === this.detailGeneration) {
                this.state.detail = { key, dimension, offset, status: 'error', rows: [], trend: [] };
            }
        }
    }

    closeDetail() { this.detailGeneration++; this.state.detail = null; }

    barWidth(value, rows) {
        const maximum = Math.max(...rows.map(row => Math.abs(row.value)), 1);
        return `${Math.abs(value) / maximum * 100}%`;
    }

    async loadRanking(key) {
        const generation = this.generation;
        const request = (this.rankingRequest || 0) + 1;
        this.rankingRequest = request;
        this.state.ranking = { key, status: 'loading', rows: [] };
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_breakdown', [key, 'salesperson', { ...this.state.applied }]);
            if (this.alive && generation === this.generation && request === this.rankingRequest) {
                this.state.ranking = { ...data, key, rows: data.rows.slice(0, this.state.rankLimit || 5) };
            }
        } catch {
            if (this.alive && generation === this.generation && request === this.rankingRequest) {
                this.state.ranking = { key, status: 'error', rows: [] };
            }
        }
    }

    async loadFinancialTrend(key) {
        const generation = this.generation;
        const marker = {};
        this.financialTrendRequests ||= {};
        this.financialTrendRequests[key] = marker;
        this.state.financialTrends[key] = { status: 'loading', rows: [] };
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_financial_trend', [key, { ...this.state.applied }]);
            if (this.alive && generation === this.generation && this.financialTrendRequests[key] === marker) {
                this.state.financialTrends[key] = data;
            }
        } catch {
            if (this.alive && generation === this.generation && this.financialTrendRequests[key] === marker) {
                this.state.financialTrends[key] = { status: 'error', rows: [] };
            }
        }
    }

    async openFinancialPeriod(key, period) {
        if (this.state.opening) { return; }
        const generation = this.generation;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_financial_period', [key, { ...this.state.applied }, period]);
            if (this.alive && generation === this.generation) { await this.action.doAction(action); }
        } catch {
            if (this.alive) { this.notification.add(_t('The report could not be opened. Check your access.'), { type: 'warning' }); }
        } finally { if (this.alive) { this.state.opening = false; } }
    }

    async loadDirectory(kind, offset = 0, mode = null, search = null) {
        const generation = this.generation;
        const stateKey = kind === 'cash' ? 'directory' : kind;
        const method = { cash: 'get_cash_directory', inventory: 'get_inventory', fulfillment: 'get_fulfillment', workforce: 'get_workforce', procurement: 'get_procurement' }[kind];
        const request = (this[`${stateKey}Request`] || 0) + 1;
        this[`${stateKey}Request`] = request;
        mode = mode || this.state[stateKey]?.mode || (kind === 'procurement' ? 'late' : 'current');
        search = kind === 'cash' ? (search ?? this.state.directory?.search ?? '') : null;
        const previous = this.state[stateKey];
        const stockFilters = kind === 'inventory' && previous?.filters ? {...previous.filters} : kind === 'inventory' ? {...this.state.stockFilters, warehouse_id: Number(this.state.stockFilters.warehouse_id) || false, category_id: Number(this.state.stockFilters.category_id) || false} : null;
        if (kind === 'inventory' && !previous?.filters && mode === 'historical' && !stockFilters.at_date) stockFilters.at_date = this.state.applied.as_of;
        if (kind === 'inventory' && mode === 'current') stockFilters.at_date = '';
        this.state[stateKey] = { status: 'loading', rows: [], offset, mode, search, filters: stockFilters, warehouses: previous?.warehouses || [], categories: previous?.categories || [] };
        try {
            const args = [{ ...this.state.applied }, offset];
            if (kind === 'cash') { args.push(search); }
            if (['inventory', 'procurement'].includes(kind)) { args.push(mode); }
            if (kind === 'inventory') args.push(stockFilters);
            const data = await this.orm.call('adams.executive.dashboard', method, args);
            if (this.alive && generation === this.generation && this[`${stateKey}Request`] === request) {
                this.state[stateKey] = { ...data, offset: Number.isInteger(data.offset) ? data.offset : offset };
            }
        } catch {
            if (this.alive && generation === this.generation && this[`${stateKey}Request`] === request) {
                this.state[stateKey] = { status: 'error', rows: [], offset, mode, search, filters: stockFilters, warehouses: previous?.warehouses || [], categories: previous?.categories || [] };
            }
        }
    }

    async exportDetail() {
        if (!this.state.detail || this.state.exporting) { return; }
        const generation = this.generation;
        const detail = this.state.detail;
        this.state.exporting = true;
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'export_breakdown', [detail.key, detail.dimension, { ...this.state.applied }]);
            if (!this.alive || generation !== this.generation || this.state.detail !== detail) { return; }
            const url = URL.createObjectURL(new Blob([data.content], { type: 'text/csv;charset=utf-8' }));
            const anchor = document.createElement('a');
            anchor.href = url; anchor.download = data.filename; anchor.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch {
            if (this.alive) { this.notification.add(_t('Export unavailable. Check your export permissions or use the report for large exports.'), { type: 'warning' }); }
        } finally { if (this.alive) { this.state.exporting = false; } }
    }

    async loadWorkspaceDetails(section, offset = 0) {
        if (!['crm','procurement'].includes(section) || !this.sectionEnabled(section)) return;
        const generation=this.generation, marker={};
        this.workspaceRequests ||= {}; this.workspaceRequests[section]=marker;
        this.state.workspaceDetails[section]={status:'loading',rows:[],offset};
        try {
            const data=await this.orm.call('adams.executive.dashboard','get_workspace_details',[{...this.state.applied},section,offset]);
            if(this.alive && generation===this.generation && this.workspaceRequests[section]===marker) this.state.workspaceDetails[section]=data;
        } catch {if(this.alive && generation===this.generation && this.workspaceRequests[section]===marker) this.state.workspaceDetails[section]={status:'error',rows:[],offset};}
    }
    async openWorkspaceRecord(section, id = null) {
        if(this.state.opening)return;
        const generation=this.generation; this.state.opening=true;
        try {
            const action=await this.orm.call('adams.executive.dashboard','open_workspace_record',[{...this.state.applied},section,id]);
            if(this.alive && generation===this.generation)await this.action.doAction(action);
        } catch {if(this.alive && generation===this.generation)this.notification.add(_t('The record is unavailable in the selected scope.'),{type:'warning'});}
        finally {if(this.alive)this.state.opening=false;}
    }

    async refreshCompanyIdentity(generation) {
        try {
            const data = await this.orm.call('adams.executive.dashboard', 'get_bootstrap', []);
            if (this.alive && generation === this.generation && data.options.company_id === this.state.applied.company_id) { this.state.companies = data.companies; this.state.logoFailed = false; }
        } catch { /* Source widgets retain their own permission/error status. */ }
    }
    loadHRDepartment(id) { this.state.hrFilters = id ? {department_id:id} : {department_unassigned:true}; return this.loadHR('employees',0,this.state.hrFilters); }
    setHRView(view) { this.state.hrFilters.view = view; return this.applyHRFilters(); }
    clearHRFilters() { this.state.hrFilters = {view:'week'}; return this.applyHRFilters(); }
    openEmployeeRecord() { const id=this.state.employeeProfile?.employee?.id; if (id) return this.openHRSource(id,false,'employees',{status:'all'}); }
    loadHROverviewMetric(metric) { this.state.hrFilters = {...metric.filters}; return this.loadHR(metric.tab, 0, metric.filters); }
    hrMetricLabel(key) { return {employees:_t('Active employees'), checked_in:_t('Checked in now'), time_off:_t('Approved time off today'), unassigned_shifts:_t('Unassigned published shifts')}[key] || key; }
    employeeInitials(name) { return (name || '').split(/\s+/).slice(0,2).map(part=>part[0]).join(''); }
    get hrStatusOptions() {
        const options = {employees:[['active',_t('Active')],['archived',_t('Archived')],['all',_t('All')]], attendance:[['all',_t('All')],['open',_t('Open')],['closed',_t('Closed')]], time_off:[['all',_t('All')],['confirm',_t('To approve')],['validate1',_t('Second approval')],['validate',_t('Approved')],['refuse',_t('Refused')],['cancel',_t('Cancelled')]], shifts:[['published',_t('Published')],['draft',_t('Draft')],['all',_t('All')]]};
        return (options[this.state.hrTab] || []).map(([value,label])=>({value,label}));
    }
    get hrWeekDays() {
        const start = this.state.hrData?.date_from || this.state.applied?.date_from;
        if (!start) return [];
        const end=this.state.hrData?.date_to || this.state.applied?.date_to || start;
        const length=Math.min(7,Math.max(1,Math.floor((Date.parse(end)-Date.parse(start))/86400000)+1));
        return Array.from({length}, (_,index)=>{const value=new Date(start+'T12:00:00Z'); value.setUTCDate(value.getUTCDate()+index); const date=value.toISOString().slice(0,10); return {date,label:date, rows:(this.state.hrData?.rows || []).filter(row => row.start_datetime_label?.slice(0,10)<=date && (row.end_datetime_label?.slice(0,10)>date || (row.end_datetime_label?.slice(0,10)===date && row.end_datetime_label?.slice(11,16)!=='00:00'))).map(row=>({...row,continuation:row.start_datetime_label.slice(0,10)<date}))};});
    }
    openEmployeeRecords(tab) { const id=this.state.employeeProfile?.employee?.id; if (!id) return; this.closeEmployeeProfile(); this.state.hrFilters={employee_id:id}; return this.loadHR(tab,0,this.state.hrFilters); }

    validateScope(options) {
        const dates = ['date_from', 'date_to', 'as_of'].map(key => options[key]);
        if (dates.some(value => !/^\d{4}-\d{2}-\d{2}$/.test(value || '') || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value)) return _t('Enter valid dates.');
        if (dates[0] > dates[1] || (Date.parse(dates[1]) - Date.parse(dates[0])) / 86400000 > 1095) return _t('Select a period of up to three years with the start before the end.');
        return '';
    }

    get activeDepartment() { return this.sections.find(section => section.key === this.state.activeSection) || this.sections[0]; }
    get companyIdentity() {
        const company = this.state.companies.find(entry => entry.id === this.state.applied?.company_id) || {};
        return {id: company.id, name: company.name || '', logoUrl: company.logo_url || '', initials: company.initials || (company.name || '').split(/\s+/).slice(0, 2).map(word => word[0]).join('')};
    }
    logoError() { this.state.logoFailed = true; }
    focusSearch() { this.state.sidebarOpen = false; this.state.moreOpen = false; this.state.searchOpen = true; requestAnimationFrame(() => this.searchInput.el?.focus()); }
    changePeriod(event) {
        const value = event.target.value;
        this.state.periodPreset = value;
        if (value === 'custom') return;
        const today = this.defaultOptions?.date_to || new Date().toISOString().slice(0, 10);
        const current = new Date(today + 'T12:00:00Z');
        let start = today.slice(0, 7) + '-01', end = today;
        if (value === 'ytd') start = today.slice(0, 4) + '-01-01';
        if (value === 'previous') { current.setUTCDate(0); end = current.toISOString().slice(0, 10); start = end.slice(0, 7) + '-01'; }
        this.state.draft = {...this.state.draft, date_from: start, date_to: end};
        return this.refresh();
    }
    formatStockQuantity(value, row) { return this.quantity(value, row?.digits ?? 2); }
    get stockFiltersDirty() { const applied = this.state.inventory?.filters; return Boolean(applied && Object.keys(this.state.stockFilters).some(key=>String(this.state.stockFilters[key] || '') !== String(applied[key] || ''))); }
    clearStockFilters() { this.state.stockFilters={warehouse_id:'',category_id:'',search:'',hide_zero:true,hide_negative:false,at_date:''}; this.state.stockMode='current'; return this.applyStockFilters(); }
    changeStockMode(mode) {
        this.state.stockMode = mode;
        if (mode === 'current') this.state.stockFilters.at_date = '';
        if (mode === 'cutoff') this.state.stockFilters.at_date = this.state.applied.as_of;
        if (mode !== 'custom') return this.applyStockFilters();
    }
    applyStockFilters() {
        const atDate = this.state.stockFilters.at_date;
        const today = this.defaultOptions?.date_to || new Date().toISOString().slice(0, 10);
        if (atDate && (!/^\d{4}-\d{2}-\d{2}$/.test(atDate) || !Number.isFinite(Date.parse(atDate)) || new Date(atDate).toISOString().slice(0,10) !== atDate || atDate > today)) {
            this.state.stockError = _t('Choose a valid stock date no later than today.'); return;
        }
        this.state.stockError = '';
        const previous = this.state.inventory;
        this.state.inventory = {warehouses: previous?.warehouses || [], categories: previous?.categories || []};
        return this.loadDirectory('inventory', 0, atDate ? 'historical' : 'current');
    }
    pageStock(offset) { return this.loadDirectory('inventory', offset); }
    async openStockValuation(row = null) {
        const data = this.state.inventory;
        if (!data || this.state.opening) return;
        const generation = this.generation;
        this.state.opening = true;
        try {
            const filters = {...data.filters};
            if (row?.warehouse_id) filters.warehouse_id = row.warehouse_id;
            const action = await this.orm.call('adams.executive.dashboard', 'open_inventory_valuation', [{...this.state.applied}, data.mode, filters, row?.product_id || null]);
            if (this.alive && generation === this.generation && data === this.state.inventory) await this.action.doAction(action);
        } catch { if (this.alive && generation === this.generation) this.notification.add(_t('The valuation report could not be opened. Check your access.'), {type:'warning'}); }
        finally { if (this.alive) this.state.opening = false; }
    }
    openStockSource(kind, row) {
        if (!row?.product_id) { this.notification.add(_t('Select a product to open its stock details.'), {type:'info'}); return; }
        return this.openReport('inventory_product', kind, row.product_id);
    }
    async openProductRanking(productId = null) {
        if (this.state.productMeasure !== 'quantity') return this.openReport('invoiced_sales', productId ? 'product' : null, productId);
        if (this.state.opening) return;
        const generation = this.generation;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_product_quantity_report', [{...this.state.applied}, productId, Number(this.state.productUnit) || null]);
            if (this.alive && generation === this.generation) await this.action.doAction(action);
        } catch { if (this.alive && generation === this.generation) this.notification.add(_t('The quantity report could not be opened. Check the selected unit and your access.'), {type:'warning'}); }
        finally { if (this.alive) this.state.opening = false; }
    }
    quantity(value, digits = 2) { return Number.isFinite(value) ? new Intl.NumberFormat(document.documentElement.lang || 'en', {maximumFractionDigits: digits}).format(value) : '—'; }
    async loadHR(tab = this.state.hrTab, offset = 0, filters = null) {
        if (!['overview','attendance','time_off','shifts','employees'].includes(tab) || !this.sectionEnabled('hr')) return;
        const generation = this.generation, marker = {};
        this.hrRequest = marker;
        const changedTab = tab !== this.state.hrTab;
        if (changedTab && !filters) this.state.hrFilters = {search: '', view: 'week'};
        const appliedFilters = this.normalizedHRFilters(filters || (changedTab ? this.state.hrFilters : this.state.hrData?.filters) || this.state.hrFilters);
        if (tab === 'overview') for (const key of Object.keys(appliedFilters)) delete appliedFilters[key];
        this.state.hrTab = tab;
        this.state.hrData = {status:'loading', rows:[], filters: appliedFilters, offset};
        try {
            const data = await this.orm.call('adams.executive.dashboard','get_hr_workspace',[{...this.state.applied},tab,appliedFilters,offset]);
            if (this.alive && generation === this.generation && this.hrRequest === marker) { this.state.hrData = {...data, filters: appliedFilters, total_count: data.total}; if (data.departments) this.hrDepartments = data.departments; }
        } catch { if (this.alive && generation === this.generation && this.hrRequest === marker) this.state.hrData = {status:'error',rows:[],filters:appliedFilters,offset}; }
    }
    normalizedHRFilters(filters) { const result = Object.fromEntries(Object.entries(filters || {}).filter(([, value]) => value !== '' && value !== undefined && value !== null)); if ('include_archived' in result) { result.status = result.include_archived ? 'all' : 'active'; delete result.include_archived; } for (const key of ['department_id','employee_id','leave_type_id']) if (key in result) result[key] = Number(result[key]); return result; }
    applyHRFilters() { return this.loadHR(this.state.hrTab,0,{...this.state.hrFilters}); }
    async openEmployeeProfile(id) {
        const generation = this.generation, marker = {};
        this.employeeRequest = marker;
        this.state.employeeProfile = {status:'loading',id};
        try {
            const data = await this.orm.call('adams.executive.dashboard','get_employee_profile',[{...this.state.applied},id]);
            if (this.alive && generation === this.generation && this.employeeRequest === marker) this.state.employeeProfile = data;
        } catch { if (this.alive && generation === this.generation && this.employeeRequest === marker) this.state.employeeProfile = {status:'error',id}; }
    }
    closeEmployeeProfile() { this.employeeRequest = null; this.state.employeeProfile = null; }
    async openHRSource(recordId = null, report = false, tab = this.state.hrTab, filters = null) {
        const generation = this.generation;
        if (this.state.opening) return;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard','open_hr_source',[{...this.state.applied},tab,this.normalizedHRFilters(filters || this.state.hrData?.filters || this.state.hrFilters),recordId,report]);
            if (this.alive && generation === this.generation) await this.action.doAction(action);
        } catch { if (this.alive && generation === this.generation) this.notification.add(_t('The HR record or report could not be opened. Check your access.'),{type:'warning'}); }
        finally { if (this.alive) this.state.opening = false; }
    }

    async openReport(key, dimension = null, groupId = null) {
        if (this.state.opening) { return; }
        const generation = this.generation;
        this.closeSource();
        this.state.opening = true;
        try {
            const isDirectory = ['inventory', 'fulfillment', 'workforce', 'inventory_product', 'procurement'].includes(key);
            const args = isDirectory ? [{ ...this.state.applied }] : [key, { ...this.state.applied }, dimension, groupId];
            if (key === 'inventory') { args.push(this.state.inventory?.mode || 'current'); }
            if (key === 'procurement') { args.push(this.state.procurement?.mode || 'late', groupId); }
            if (key === 'workforce') { args.push(groupId); }
            if (key === 'inventory_product') { args.push(groupId, dimension); }
            const action = await this.orm.call('adams.executive.dashboard', isDirectory ? `open_${key}` : 'open_report', args);
            if (this.alive && generation === this.generation) { await this.action.doAction(action); }
        } catch {
            if (this.alive) { this.notification.add(_t('The report could not be opened. Check your access.'), { type: 'warning' }); }
        } finally {
            if (this.alive) { this.state.opening = false; }
        }
    }
}

registry.category('actions').add('adams_executive_dashboard.dashboard', ExecutiveDashboard);
