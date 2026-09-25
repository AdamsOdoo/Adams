"""Server side of the Executive Dashboard: one call per section, drawers on demand, search."""
import re
import threading
import time
from collections import OrderedDict
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

# Section key -> models it reads. A section is shown only when every model is
# installed (runtime detection: the module depends on web + account only) and readable.
# ``groups``: the user needs one of them as well (financial statements are accounting
# data; an Invoicing-only database gives its administrators ``group_account_manager``
# without the read-only accounting group).
SECTIONS = {
    'finance': {'models': ('account.move.line',), 'period': True,
                'groups': ('account.group_account_readonly', 'account.group_account_manager')},
    'sales': {'models': ('sale.order',), 'period': True},
    'crm': {'models': ('crm.lead',), 'period': True},
    'procurement': {'models': ('purchase.order',), 'period': True},
    'inventory': {'models': ('stock.picking', 'stock.quant'), 'period': False},
    'people': {'models': ('hr.employee',), 'period': False},
}
PERIODS = ('month', 'last_month', 'quarter', 'ytd', 'custom')
MAX_CUSTOM_DAYS = 3 * 366

# Search: models looked up when installed and readable, 5 results each, record rules apply.
SEARCH_MODELS = (
    'res.partner', 'account.move', 'sale.order', 'purchase.order', 'stock.picking',
    'product.template', 'crm.lead', 'hr.employee',
)
SEARCH_LIMIT = 5

KEY_RE = re.compile(r'^[a-z_]+\.[a-z_]+$')

# Per-process section cache. The key holds everything the result depends on
# (database, user and groups, companies, section, dates, language), so users never
# share an entry and record rules that depend on the user stay correct.
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
        user = self.env.user
        if not (user.has_group('executive_dashboard.group_user') or self.env.is_system()):
            raise AccessError(self.env._('You do not have access to the Executive Dashboard.'))

    def _section_status(self, section):
        """'ok', 'hidden' (disabled or app not installed) or 'restricted' (no read access)."""
        if not self.env.company[f'executive_dashboard_{section}']:
            return 'hidden'
        names = SECTIONS[section]['models']
        if any(name not in self.env for name in names):
            return 'hidden'
        if not all(self.env[name].has_access('read') for name in names):
            return 'restricted'
        groups = SECTIONS[section].get('groups')
        if groups and not any(self.env.user.has_group(group) for group in groups):
            return 'restricted'
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
        return {'period': period, 'date_from': start, 'date_to': end, 'today': today,
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
                for key, spec in SECTIONS.items() if self._section_status(key) == 'ok'
            ],
            'can_configure': self.env.is_system(),
        }

    @api.model
    def get_section(self, section, period='month', date_from=None, date_to=None, refresh=False):
        """Every widget of one section in a single call, cached for 60 seconds."""
        self._authorize()
        if section not in SECTIONS:
            raise ValidationError(self.env._('Unknown section.'))
        status = self._section_status(section)
        if status != 'ok':
            return {'section': section, 'status': status, 'widgets': {}}
        scope = self._period_scope(section, period, date_from, date_to)
        key = (
            self.env.cr.dbname, self.env.uid, tuple(self.env.user.all_group_ids.ids),
            tuple(scope['companies'].ids), scope['company'].id, self.env.lang,
            section, scope['date_from'], scope['date_to'],
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

    @api.model
    def get_drawer(self, key, args=None):
        """Side-panel content for ``<section>.<name>``, fetched when the panel opens."""
        self._authorize()
        return self._dispatch('drawer', key, args)

    @api.model
    def open_action(self, key, args=None):
        """The native Odoo action behind a figure, resolved at click time."""
        self._authorize()
        return self._dispatch('action', key, args)

    @api.model
    def global_search(self, query):
        """Up to 5 readable records per model whose name matches ``query``."""
        self._authorize()
        query = (query or '').strip()
        if len(query) < 2:
            return []
        query = query[:100]
        groups = []
        for name in SEARCH_MODELS:
            if name not in self.env or not self.env[name].has_access('read'):
                continue
            Model = self.env[name]
            records = Model.search([('display_name', 'ilike', query)], limit=SEARCH_LIMIT)
            if records:
                groups.append({
                    'model': name,
                    'label': self.env['ir.model']._get(name).name,
                    'records': [{'id': r.id, 'name': r.display_name} for r in records],
                })
        return groups
