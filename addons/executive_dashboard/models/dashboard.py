"""Server side of the Executive Dashboard: one call per section, drawers on demand, search."""
import re
from ast import literal_eval
import threading
import time
from collections import OrderedDict
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain

# Section key -> models it reads. A section is shown when it is enabled for the company
# and every model is installed (runtime detection: the module depends on web + account only).
#
# Access (owner decision): the dashboard has one level, Administrator, or no access. An
# Administrator sees every section and figure whatever their rights in the other apps: the
# data is read with elevated rights (``_elevated``), limited to the companies the user may
# use. Buttons to Odoo's own screens are shown only when the user may open them (``_open_info``).
SECTIONS = {
    'finance': {'models': ('account.move.line',), 'period': True},
    'sales': {'models': ('sale.order',), 'period': True},
    'crm': {'models': ('crm.lead',), 'period': True},
    'procurement': {'models': ('purchase.order',), 'period': True},
    'inventory': {'models': ('stock.picking', 'stock.quant'), 'period': False},
    'people': {'models': ('hr.employee',), 'period': False},
}
PERIODS = ('month', 'last_month', 'quarter', 'ytd', 'custom')
MAX_CUSTOM_DAYS = 3 * 366

# Search: models looked up when installed, 5 results each, in the user's current companies.
SEARCH_MODELS = (
    'res.partner', 'account.move', 'sale.order', 'purchase.order', 'stock.picking',
    'product.template', 'crm.lead', 'hr.employee',
)
SEARCH_LIMIT = 5

KEY_RE = re.compile(r'^[a-z_]+\.[a-z_]+$')

# Per-process section cache. The key holds everything the result depends on
# (database, user and groups, companies, section, dates, language), so users never
# share an entry.
CACHE_TTL = 60
CACHE_SIZE = 512
_cache = OrderedDict()
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            _cache.move_to_end(key)
            return hit[1]
        _cache.pop(key, None)
    return None


def _cache_put(key, value):
    with _cache_lock:
        _cache[key] = (time.monotonic() + CACHE_TTL, value)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def cache_clear():
    with _cache_lock:
        _cache.clear()


class ExecutiveDashboard(models.AbstractModel):
    _name = 'executive.dashboard'
    _description = 'Executive Dashboard'

    # ------------------------------------------------------------------ access

    def _authorize(self):
        if not self.env.user.has_group('executive_dashboard.group_admin'):
            raise AccessError(self.env._('You do not have access to the Executive Dashboard.'))

    def _elevated(self):
        """This model with elevated rights, for reading the dashboard's data.

        The companies are validated first with the user's own rights (``env.companies``
        raises for a company the user may not use); every query then filters on them.
        """
        self.env.companies  # noqa: B018 -- raises AccessError for companies the user may not use
        return self.sudo()

    def _user_env(self):
        """The environment with the user's own rights (for deciding which native screens open)."""
        return self.env(su=False)

    def _check_company(self, record):
        """Refuse a record of a company the user may not use (records without a company pass)."""
        companies = self.env.companies
        if 'company_id' in record._fields:
            foreign = record.company_id and record.company_id not in companies
        elif 'company_ids' in record._fields:
            foreign = record.company_ids and not (record.company_ids & companies)
        else:
            foreign = False
        if foreign:
            raise AccessError(self.env._('This record belongs to a company you do not use.'))
        return record

    def _open_info(self, action):
        """``(can_open, kind)`` of a native action for the user with their own rights.

        ``kind`` names the button: ``record`` (one record), ``list`` or ``report``. A list
        opens only when the user may read every record the dashboard shows in it, so the
        native screen never shows less than the side panel.
        """
        env = self._user_env()
        if action.get('type') == 'ir.actions.client':
            context = action.get('context') or {}
            if isinstance(context, str):
                # Actions read from ir.actions.client keep their context as text.
                try:
                    context = literal_eval(context)
                except (ValueError, SyntaxError):
                    context = {}
            report_id = context.get('report_id') if isinstance(context, dict) else None
            model, res_id, kind = 'account.report', report_id, 'report'
        else:
            model, res_id, kind = action.get('res_model'), action.get('res_id'), \
                'record' if action.get('res_id') else 'list'
        if not model or model not in env:
            return False, kind
        if res_id:
            return env[model].browse(res_id).has_access('read'), kind
        domain = action.get('domain')
        if kind == 'list' and isinstance(domain, list):
            return self._can_list(model, domain), kind
        return env[model].has_access('read'), kind

    def _can_list(self, model, domain):
        """Whether the user, with their own rights, sees every record of ``domain``."""
        Model = self._user_env()[model]
        if not Model.has_access('read'):
            return False
        return Model.search_count(domain) == self.env[model].sudo().search_count(domain)

    def _section_status(self, section):
        """'ok' or 'hidden' (disabled for the company or app not installed)."""
        if not self.env.company[f'executive_dashboard_{section}']:
            return 'hidden'
        if any(name not in self.env for name in SECTIONS[section]['models']):
            return 'hidden'
        return 'ok'

    # ------------------------------------------------------------------ periods

    def _period_scope(self, section, period, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        if not SECTIONS[section]['period']:
            period, start, end = 'now', today, today
        elif period == 'month':
            start, end = today.replace(day=1), today
        elif period == 'last_month':
            end = today.replace(day=1) - timedelta(days=1)
            start = end.replace(day=1)
        elif period == 'quarter':
            start, end = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1), today
        elif period == 'ytd':
            start, end = self.env.company.compute_fiscalyear_dates(today)['date_from'], today
        elif period == 'custom':
            try:
                start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
            except (TypeError, ValueError):
                raise ValidationError(self.env._('Enter valid start and end dates.')) from None
            if start > end or (end - start).days > MAX_CUSTOM_DAYS:
                raise ValidationError(self.env._('Choose a period of up to three years, starting before it ends.'))
        else:
            raise ValidationError(self.env._('Unknown period.'))
        # Balances (bank and cash, open items) are taken at the period's end, never after today.
        return {'period': period, 'date_from': start, 'date_to': end, 'today': today, 'as_of': min(end, today),
                'company': self.env.company, 'companies': self.env.companies}

    # ------------------------------------------------------------------ public API

    @api.model
    def get_bootstrap(self):
        """Shell data only. Welcome shows no figures, so nothing here is a figure."""
        self._authorize()
        company = self.env.company
        return {
            'user_name': self.env.user.name,
            'company_name': company.name,
            'company_initials': ''.join(w[0] for w in company.name.split()[:2]).upper(),
            'today': fields.Date.context_today(self).isoformat(),
            'sections': [
                {'key': key, 'period': spec['period']}
                for key, spec in SECTIONS.items() if self._elevated()._section_status(key) == 'ok'
            ],
            'can_configure': self.env.is_system(),
        }

    @api.model
    def get_section(self, section, period='month', date_from=None, date_to=None, refresh=False):
        """Every widget of one section in a single call, cached for 60 seconds."""
        self._authorize()
        if section not in SECTIONS:
            raise ValidationError(self.env._('Unknown section.'))
        return self._elevated()._get_section(section, period, date_from, date_to, refresh)

    def _get_section(self, section, period, date_from, date_to, refresh):
        status = self._section_status(section)
        if status != 'ok':
            return {'section': section, 'status': status, 'widgets': {}}
        scope = self._period_scope(section, period, date_from, date_to)
        key = (
            self.env.cr.dbname, self.env.uid, tuple(self.env.user.all_group_ids.ids),
            tuple(scope['companies'].ids), scope['company'].id, self.env.lang,
            section, scope['date_from'], scope['date_to'], scope['today'],
        )
        if not refresh:
            cached = _cache_get(key)
            if cached is not None:
                return cached
        result = {
            'section': section,
            'status': 'ok',
            'period': {
                'key': scope['period'],
                'date_from': scope['date_from'].isoformat(),
                'date_to': scope['date_to'].isoformat(),
            },
            'widgets': getattr(self, f'_section_{section}')(scope),
            'generated_at': fields.Datetime.now().isoformat(),
        }
        _cache_put(key, result)
        return result

    def _dispatch(self, prefix, key, args):
        if not isinstance(key, str) or not KEY_RE.match(key):
            raise ValidationError(self.env._('Unknown detail.'))
        section, name = key.split('.', 1)
        if section not in SECTIONS or self._section_status(section) != 'ok':
            raise AccessError(self.env._('This section is not available to you.'))
        method = getattr(self, f'_{prefix}_{section}_{name}', None)
        if method is None:
            raise ValidationError(self.env._('Unknown detail.'))
        return method(dict(args or {}))

    def _target(self, target):
        """``{key, args, kind}`` of a drawer's native screen when the user may open it, else None."""
        try:
            action = self._dispatch('action', target['key'], target.get('args'))
        except (AccessError, ValidationError, UserError):
            return None
        can_open, kind = self._open_info(action)
        return dict(target, kind=kind) if can_open else None

    @api.model
    def get_drawer(self, key, args=None):
        """Side-panel content for ``<section>.<name>``, fetched when the panel opens.

        The drawer's ``action`` (and a row's) is kept only when the user may open that
        screen; it then carries ``kind`` (record, list or report) for the button's wording.
        """
        self._authorize()
        dashboard = self._elevated()
        result = dashboard._dispatch('drawer', key, args)
        if isinstance(result, dict):
            if result.get('action'):
                result['action'] = dashboard._target(result['action'])
            # Rows opening the same report (e.g. every account opening the Trial Balance) share
            # one check: the report and the user's rights on it are the same for each row.
            reports = {}
            rows = [row for group in result.get('groups') or () for row in group.get('rows') or ()]
            for row in rows + list(result.get('rows') or ()):
                if isinstance(row, dict) and row.get('action'):
                    key = row['action'].get('key')
                    if key in reports:
                        row['action'] = dict(row['action'], kind='report')
                        continue
                    row['action'] = dashboard._target(row['action'])
                    if row['action'] and row['action']['kind'] == 'report':
                        reports[key] = True
        return result

    @api.model
    def open_action(self, key, args=None):
        """The native Odoo action behind a figure, resolved at click time; only a screen the
        user may open with their own rights."""
        self._authorize()
        dashboard = self._elevated()
        action = dashboard._dispatch('action', key, args)
        if not dashboard._open_info(action)[0]:
            raise AccessError(self.env._('You cannot open this screen.'))
        return action

    @api.model
    def global_search(self, query):
        """Up to 5 records per model whose name matches ``query``, in the user's current
        companies; ``can_open`` says whether the user may open the record itself."""
        self._authorize()
        query = (query or '').strip()
        if len(query) < 2:
            return []
        query = query[:100]
        dashboard = self._elevated()
        env, user_env = dashboard.env, dashboard._user_env()
        companies = [False, *env.companies.ids]
        groups = []
        for name in SEARCH_MODELS:
            if name not in env:
                continue
            Model = env[name]
            domain = Domain('display_name', 'ilike', query)
            if 'company_id' in Model._fields and Model._fields['company_id'].store:
                domain &= Domain('company_id', 'in', companies)
            records = Model.search(domain, limit=SEARCH_LIMIT)
            if records:
                readable = set(records.with_env(user_env)._filtered_access('read').ids)
                groups.append({
                    'model': name,
                    'label': env['ir.model']._get(name).name,
                    'records': [{'id': r.id, 'name': r.display_name, 'can_open': r.id in readable}
                                for r in records],
                })
        return groups
