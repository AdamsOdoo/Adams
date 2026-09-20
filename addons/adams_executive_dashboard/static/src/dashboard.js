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
        this.generation = 0;
        this.alive = true;
        this.sections = [
            { key: 'finance', name: _t('Finance'), description: _t('Profitability, liquidity and working capital') },
            { key: 'sales', name: _t('Sales'), description: _t('Invoiced sales and confirmed orders') },
            { key: 'operations', name: _t('Operations'), description: _t('Purchasing, inventory, CRM and people') },
        ];
        this.labels = {
            revenue: _t('Accounting revenue'), profit: _t('Net profit'), cash: _t('Bank and cash'),
            receivables: _t('Receivables'), payables: _t('Payables'),
            gross_profit: _t('Gross profit'), operating_expenses: _t('Operating expenses'),
            gross_margin: _t('Gross margin'), net_margin: _t('Net margin'),
            assets: _t('Assets'), liabilities: _t('Liabilities'), equity: _t('Equity'),
            invoiced_sales: _t('Net invoiced sales'), confirmed_sales: _t('Confirmed sales'),
            orders: _t('Distinct sales orders'), quotations: _t('Draft and sent quotations'), purchases: _t('Confirmed purchases'),
            inventory: _t('Inventory valuation'), crm: _t('Weighted open pipeline'), hr: _t('Approved leave hours (native signed)'),
        };
        this.groupHeadings = { revenue: _t('Profitability'), cash: _t('Liquidity'), receivables: _t('Working capital'), invoiced_sales: _t('Commercial performance') };
        this.statusLabels = {
            not_configured: _t('Not configured'), not_installed: _t('App not installed'),
            restricted: _t('Access restricted'), empty: _t('No matching records'),
            unsupported_scope: _t('Unsupported report scope'), error: _t('Report unavailable'),
        };
        this.dimensionLabels = { customer: _t('Customer'), salesperson: _t('Salesperson'), product: _t('Product'),
            vendor: _t('Vendor'), buyer: _t('Buyer'), stage: _t('Stage'), department: _t('Department') };
        this.dimensions = { invoiced_sales: ['customer', 'salesperson', 'product'], confirmed_sales: ['customer', 'salesperson', 'product'],
            quotations: ['customer', 'salesperson', 'product'], orders: ['customer', 'salesperson'], purchases: ['vendor', 'buyer', 'product'], crm: ['stage', 'salesperson'], hr: ['department'] };
        this.root = useRef('root');
        this.detailGeneration = 0;
        this.state = useState({ companies: [], draft: {}, applied: null, sections: {}, error: '', opening: false,
            collapsed: { operations: true }, detail: null, directory: null, inventory: null, fulfillment: null, recent: null, exporting: false, restored: false });
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
                this.userId = data.user_id;
                const savedNavigation = this.props.state?.dashboard;
                const restore = savedNavigation?.userId === data.user_id &&
                    data.companies.some(company => company.id === savedNavigation.applied?.company_id)
                    ? savedNavigation : null;
                this.state.draft = restore ? { ...restore.applied } : data.options;
                this.preferenceKey = `adams-dashboard-v1-${data.user_id}`;
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
            collapsed: { ...this.state.collapsed }, scroll: this.root.el?.scrollTop || 0,
            detail: selection(this.state.detail, ['key', 'dimension', 'offset']),
            recent: selection(this.state.recent, ['kind', 'offset']),
            directory: selection(this.state.directory, ['offset']), inventory: selection(this.state.inventory, ['offset']), fulfillment: selection(this.state.fulfillment, ['offset']) };
    }

    async restoreNavigation(saved) {
        const generation = this.generation + 1;
        await this.refresh();
        if (!this.alive || generation !== this.generation || !saved) { return; }
        const jobs = [];
        if (saved.detail && this.dimensions[saved.detail.key]?.includes(saved.detail.dimension)) {
            jobs.push(this.inspect(saved.detail.key, saved.detail.dimension, saved.detail.offset));
        }
        if (saved.recent && ['orders', 'quotations'].includes(saved.recent.kind)) {
            jobs.push(this.loadRecent(saved.recent.kind, saved.recent.offset));
        }
        if (saved.directory) { jobs.push(this.loadDirectory('cash', saved.directory.offset)); }
        if (saved.fulfillment) { jobs.push(this.loadDirectory('fulfillment', saved.fulfillment.offset)); }
        if (saved.inventory) { jobs.push(this.loadDirectory('inventory', saved.inventory.offset)); }
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

    async refresh() {
        const generation = ++this.generation;
        const options = { ...this.state.draft, company_id: Number(this.state.draft.company_id) };
        this.state.applied = options;
        this.state.detail = null;
        this.state.directory = null;
        this.state.inventory = null;
        this.state.fulfillment = null;
        this.state.recent = null;
        this.detailGeneration++;
        this.state.error = '';
        // Immediately remove previous-company values, including during failures.
        this.state.sections = Object.fromEntries(this.sections.map(s => [s.key, { status: 'loading', items: [] }]));
        await Promise.all(this.sections.map(async ({ key }) => {
            try {
                const data = await this.orm.call('adams.executive.dashboard', 'get_section', [key, options]);
                if (this.alive && generation === this.generation) {
                    this.state.sections[key] = { ...data, status: 'ready' };
                }
            } catch {
                if (this.alive && generation === this.generation) {
                    this.state.sections[key] = { status: 'error', items: [] };
                }
            }
        }));
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
        this.state.detail = { key, dimension, offset, status: 'loading', rows: [], trend: [] };
        try {
            const [groups, trend] = await Promise.all([
                this.orm.call('adams.executive.dashboard', 'get_breakdown', [key, dimension, { ...this.state.applied }, offset]),
                this.orm.call('adams.executive.dashboard', 'get_trend', [key, { ...this.state.applied }]),
            ]);
            if (this.alive && generation === this.generation && request === this.detailGeneration) {
                this.state.detail = { ...groups, key, dimension, offset, trend: trend.rows, status: groups.status };
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

    async loadDirectory(kind, offset = 0) {
        const generation = this.generation;
        const stateKey = kind === 'cash' ? 'directory' : kind;
        const method = { cash: 'get_cash_directory', inventory: 'get_inventory', fulfillment: 'get_fulfillment' }[kind];
        const request = (this[`${stateKey}Request`] || 0) + 1;
        this[`${stateKey}Request`] = request;
        this.state[stateKey] = { status: 'loading', rows: [], offset };
        try {
            const data = await this.orm.call('adams.executive.dashboard', method, [{ ...this.state.applied }, offset]);
            if (this.alive && generation === this.generation && this[`${stateKey}Request`] === request) {
                this.state[stateKey] = { ...data, offset };
            }
        } catch {
            if (this.alive && generation === this.generation && this[`${stateKey}Request`] === request) {
                this.state[stateKey] = { status: 'error', rows: [], offset };
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
            if (this.alive) { this.notification.add(_t('Export unavailable. Check your export permissions or use the native report for large exports.'), { type: 'warning' }); }
        } finally { if (this.alive) { this.state.exporting = false; } }
    }

    async openReport(key, dimension = null, groupId = null) {
        if (this.state.opening) { return; }
        const generation = this.generation;
        this.state.opening = true;
        try {
            const isDirectory = ['inventory', 'fulfillment'].includes(key);
            const args = isDirectory ? [{ ...this.state.applied }] : [key, { ...this.state.applied }, dimension, groupId];
            const action = await this.orm.call('adams.executive.dashboard', isDirectory ? `open_${key}` : 'open_report', args);
            if (this.alive && generation === this.generation) { await this.action.doAction(action); }
        } catch {
            if (this.alive) { this.notification.add(_t('The native report could not be opened. Check your access.'), { type: 'warning' }); }
        } finally {
            if (this.alive) { this.state.opening = false; }
        }
    }
}

registry.category('actions').add('adams_executive_dashboard.dashboard', ExecutiveDashboard);
