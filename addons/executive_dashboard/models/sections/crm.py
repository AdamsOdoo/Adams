"""CRM: open and weighted pipeline, new leads, won, pipeline by stage and salesperson.

Open pipeline = active opportunities whose ``won_status`` is ``pending`` (Odoo 19: won =
won stage at 100 %, lost = archived at 0 %), as of today. Won = ``won_status = 'won'`` with
``date_closed`` in the period. New leads = leads and opportunities created in the period.
Amounts are ``expected_revenue`` / ``prorated_revenue`` in each company's currency,
converted to the dashboard company's currency.
"""
from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

TOP_ROWS = 5
SOON_ROWS = 10
DRAWER_ROWS = 25


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_crm(self, scope):
        """CRM widgets: ``currency``, ``kpis``, ``stages``, ``salespeople``, ``closing``."""
        currency = scope['company'].currency_id
        Lead = self.env['crm.lead']
        today = scope['today']
        open_domain = self._crm_open_domain(scope)
        pipeline = Lead._read_group(open_domain, ['company_id'],
                                    ['expected_revenue:sum', 'prorated_revenue:sum', '__count'])
        won = Lead._read_group(self._crm_won_domain(scope), ['company_id'], ['expected_revenue:sum', '__count'])
        stages = []
        for stage, company, amount, count in Lead._read_group(
                open_domain, ['stage_id', 'company_id'], ['expected_revenue:sum', '__count'], order='stage_id'):
            if not stages or stages[-1]['id'] != (stage.id or False):
                stages.append({'id': stage.id or False, 'name': stage.name or self.env._('No stage'),
                               'amount': 0.0, 'count': 0})
            stages[-1]['amount'] += self._fin_convert(scope, amount, company or scope['company'], today)
            stages[-1]['count'] += count
        people = self._ranked(scope, 'crm.lead', open_domain, 'user_id', 'expected_revenue', TOP_ROWS, today)
        closing = Lead.search(open_domain, order='date_deadline asc nulls last, id', limit=SOON_ROWS)
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'kpis': {
                'pipeline': sum(self._fin_convert(scope, a, c or scope['company'], today) for c, a, _p, _n in pipeline),
                'weighted': sum(self._fin_convert(scope, p, c or scope['company'], today) for c, _a, p, _n in pipeline),
                'opportunities': sum(n for *_r, n in pipeline),
                'new_leads': Lead.search_count(self._crm_new_domain(scope)),
                'won': sum(self._fin_convert(scope, a, c or scope['company'], scope['date_to']) for c, a, _n in won),
                'won_count': sum(n for *_r, n in won),
            },
            'stages': stages,
            'salespeople': [{'id': user.id or False, 'name': user.name or self.env._('No salesperson'),
                             'amount': amount, 'count': count} for user, amount, count in people],
            'closing': [self._crm_row(scope, lead) for lead in closing],
        }

    # ------------------------------------------------------------------ helpers

    def _crm_open_domain(self, scope):
        return Domain([('type', '=', 'opportunity'), ('active', '=', True), ('won_status', '=', 'pending'),
                       ('company_id', 'in', [False, *scope['companies'].ids])])

    def _crm_won_domain(self, scope):
        return Domain([('type', '=', 'opportunity'), ('won_status', '=', 'won'),
                       ('company_id', 'in', [False, *scope['companies'].ids]),
                       *self._in_period('date_closed', scope)])

    def _crm_new_domain(self, scope):
        return Domain([('company_id', 'in', [False, *scope['companies'].ids]),
                       *self._in_period('create_date', scope)])

    def _crm_amount(self, scope, lead):
        company = lead.company_id or scope['company']
        return self._fin_convert(scope, lead.expected_revenue, company, scope['today'])

    def _crm_row(self, scope, lead):
        return {
            'id': lead.id, 'name': lead.name, 'customer': lead.partner_id.display_name or '',
            'amount': self._crm_amount(scope, lead), 'probability': lead.probability,
            'closing': fields.Date.to_string(lead.date_deadline) if lead.date_deadline else False,
            'salesperson': lead.user_id.name or '',
        }

    def _crm_scope(self, args):
        return self._period_scope('crm', args.get('period') or 'month', args.get('date_from'), args.get('date_to'))

    def _crm_format(self, amount):
        return formatLang(self.env, amount, digits=0)

    def _crm_lead_rows(self, scope, leads, crumb):
        return [{'label': lead.name,
                 'sub': ' · '.join(filter(None, [lead.partner_id.display_name, lead.user_id.name])),
                 'value': self._crm_format(self._crm_amount(scope, lead)),
                 'open': {'key': 'crm.opportunity', 'args': {'lead_id': lead.id}, 'crumb': crumb}}
                for lead in leads]

    def _crm_list(self, args):
        """Lists behind the figures: ``(title, sub, domain, order, action xmlid)``."""
        kind = args.get('kind')
        _ = self.env._
        scope = self._crm_scope(args)
        domain = self._crm_open_domain(scope)
        if kind == 'stage':
            stage_id = self._positive_id(args, 'stage_id', optional=True)
            name = self.env['crm.stage'].browse(stage_id).name if stage_id else _('No stage')
            return (name, _('Pipeline by stage'), domain & Domain('stage_id', '=', stage_id),
                    'expected_revenue desc, id', 'crm.crm_lead_action_pipeline')
        if kind == 'salesperson':
            user_id = self._positive_id(args, 'user_id', optional=True)
            name = self.env['res.users'].browse(user_id).name if user_id else _('No salesperson')
            return (name, _('Pipeline by salesperson'), domain & Domain('user_id', '=', user_id),
                    'expected_revenue desc, id', 'crm.crm_lead_action_pipeline')
        if kind == 'closing':
            return (_('Closing soonest'), _('By expected closing date'), domain,
                    'date_deadline asc nulls last, id', 'crm.crm_lead_action_pipeline')
        if kind == 'leads':
            return (_('New leads'), _('Leads and opportunities created in the period'),
                    self._crm_new_domain(scope), 'create_date desc, id desc', 'crm.crm_lead_all_leads')
        if kind == 'won':
            return (_('Won'), _('Opportunities marked won in the period'), self._crm_won_domain(scope),
                    'date_closed desc, id desc', 'crm.crm_lead_action_pipeline')
        raise ValidationError(_('Unknown detail.'))

    # ------------------------------------------------------------------ drawers

    def _drawer_crm_pipeline(self, args):
        """Open pipeline by stage; each stage opens its opportunities."""
        scope = self._crm_scope(args)
        widgets = self._section_crm(scope)
        _ = self.env._
        crumb = _('Open pipeline')
        rows = [{'label': stage['name'], 'sub': _('%s opportunities', stage['count']),
                 'value': self._crm_format(stage['amount']),
                 'open': {'key': 'crm.list', 'args': dict(args, kind='stage', stage_id=stage['id']), 'crumb': crumb}}
                for stage in widgets['stages']]
        return {'title': crumb, 'sub': _('Open opportunities · as of today'), 'rows': rows,
                'total': {'label': _('Total'), 'value': '%s %s' % (
                    self._crm_format(widgets['kpis']['pipeline']), scope['company'].currency_id.name)},
                'action': {'key': 'crm.pipeline', 'args': {}}, 'dest': _('Pipeline')}

    def _action_crm_pipeline(self, args):
        return self._window('crm.crm_lead_action_pipeline', self.env._('Pipeline'), 'crm.lead',
                            self._crm_open_domain(self._crm_scope({})))

    def _drawer_crm_list(self, args):
        title, sub, domain, order, _xmlid = self._crm_list(args)
        scope = self._crm_scope(args)
        Lead = self.env['crm.lead']
        leads = Lead.search(domain, order=order, limit=DRAWER_ROWS)
        count = Lead.search_count(domain)
        return {'title': title, 'sub': '%s · %s' % (sub, self.env._('%s records', count)),
                'rows': self._crm_lead_rows(scope, leads, title),
                'action': {'key': 'crm.list', 'args': args},
                'dest': self.env._('Leads') if args.get('kind') == 'leads' else self.env._('Pipeline')}

    def _action_crm_list(self, args):
        title, _sub, domain, _order, xmlid = self._crm_list(args)
        return self._window(xmlid, title, 'crm.lead', domain)

    def _crm_lead(self, args):
        lead = self.env['crm.lead'].browse(self._positive_id(args, 'lead_id')).exists()
        if not lead:
            raise ValidationError(self.env._('Unknown detail.'))
        lead.check_access('read')
        return lead

    def _drawer_crm_opportunity(self, args):
        lead = self._crm_lead(args)
        scope = self._crm_scope({})
        _ = self.env._
        rows = [
            {'label': _('Expected revenue'), 'value': self._crm_format(self._crm_amount(scope, lead))},
            {'label': _('Probability'), 'value': '%s%%' % formatLang(self.env, lead.probability, digits=0)},
            {'label': _('Closing'), 'value': format_date(self.env, lead.date_deadline) if lead.date_deadline else '—'},
            {'label': _('Stage'), 'value': lead.stage_id.name or '—'},
            {'label': _('Salesperson'), 'value': lead.user_id.name or '—'},
        ]
        return {'title': lead.name, 'sub': lead.partner_id.display_name or '', 'rows': rows,
                'action': {'key': 'crm.opportunity', 'args': {'lead_id': lead.id}},
                'dest': _('Opportunity') if lead.type == 'opportunity' else _('Lead')}

    def _action_crm_opportunity(self, args):
        lead = self._crm_lead(args)
        return self._window('crm.crm_lead_action_pipeline', lead.name, 'crm.lead', [('id', '=', lead.id)],
                            res_id=lead.id)
