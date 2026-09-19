/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
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
            invoiced_sales: _t('Net invoiced sales'), confirmed_sales: _t('Confirmed sales'),
            orders: _t('Distinct sales orders'), purchases: _t('Confirmed purchases'),
            inventory: _t('Inventory'), crm: _t('CRM'), hr: _t('People'),
        };
        this.statusLabels = {
            not_configured: _t('Not configured'), not_installed: _t('App not installed'),
            restricted: _t('Access restricted'), empty: _t('No matching records'),
        };
        this.state = useState({ companies: [], draft: {}, applied: null, sections: {}, error: '', opening: false });
        onWillStart(async () => {
            try {
                const data = await this.orm.call('adams.executive.dashboard', 'get_bootstrap', []);
                if (!this.alive) { return; }
                this.state.companies = data.companies;
                this.state.draft = data.options;
                // Render the shell while each section completes independently.
                void this.refresh();
            } catch {
                this.state.error = _t('The dashboard could not be loaded. Check your access and try again.');
            }
        });
        onWillUnmount(() => { this.alive = false; this.generation++; });
    }

    async refresh() {
        const generation = ++this.generation;
        const options = { ...this.state.draft, company_id: Number(this.state.draft.company_id) };
        this.state.applied = options;
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

    async openReport(key) {
        if (this.state.opening) { return; }
        const generation = this.generation;
        this.state.opening = true;
        try {
            const action = await this.orm.call('adams.executive.dashboard', 'open_report', [key, { ...this.state.applied }]);
            if (this.alive && generation === this.generation) { await this.action.doAction(action); }
        } catch {
            if (this.alive) { this.notification.add(_t('The native report could not be opened. Check your access.'), { type: 'warning' }); }
        } finally {
            if (this.alive) { this.state.opening = false; }
        }
    }
}

registry.category('actions').add('adams_executive_dashboard.dashboard', ExecutiveDashboard);
