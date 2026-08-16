from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ShopifyConnectorUiHealth(models.AbstractModel):
    """Read-only operational projection for the separate Health page."""

    _inherit = 'shopify.connector.ui.dashboard'

    @api.model
    def get_connector_health_data(self, store_id=False):
        """Return health evidence only; never sales or lifecycle figures."""
        self._ensure_dashboard_user()
        stores = self.env['shopify.connector.store'].search([], order='id')
        store = self._store_360_validate_store(store_id, stores)
        ctx = {'store': store, 'stores': stores}
        jobs = self._job_counts_scoped(store)
        attempts_uncertain = self._uncertain_attempt_count_scoped(store)
        store_states = self._store_counts_scoped(store)
        derived = self._derive_state(
            store_states, jobs, attempts_uncertain,
        )
        return {
            'meta': self._connector_health_meta(ctx),
            'health': {
                'state': derived['state'],
                'lead': derived['lead'],
                'jobs': jobs,
                'needs_review':
                    jobs['blocked_manual_review'] + attempts_uncertain,
                'backlog':
                    jobs['queued'] + jobs['running'] + jobs['retry_waiting'],
                'oldest_blocked': self._oldest_blocked(store),
                'week': self._week_counters(store),
                'exceptions': self._store_360_exceptions(
                    store, jobs, attempts_uncertain,
                ),
                'activity': self._recent_activity_scoped(store),
            },
            'flows': self._flow_rows(ctx),
            'stores_region': self._connector_health_store_rows(ctx),
            'throttle': self._connector_health_throttle(ctx),
            'mappings': self._connector_health_mappings(store),
            'reconciliation': self._connector_health_reconciliation(store),
            'mode_switch': self._connector_health_mode_switch(ctx),
            'setup_available': self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            'refresh_interval_seconds': 30,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }

    def _connector_health_meta(self, ctx):
        store = ctx['store']
        return {
            'store_id': store.id if len(store) == 1 else False,
            'stores': [
                {
                    'id': candidate.id,
                    'name': candidate.name,
                    'state': candidate.state,
                }
                for candidate in ctx['stores']
            ],
        }

    def _store_counts_scoped(self, store):
        Store = self.env['shopify.connector.store']
        term = [('id', '=', store.id)] if len(store) == 1 else []
        return {
            'total': Store.search_count(term),
            'connected': Store.search_count(term + [('state', '=', 'connected')]),
            'reconnect_needed': Store.search_count(
                term + [('state', '=', 'reconnect_needed')]
            ),
            'setup_incomplete': Store.search_count(
                term + [('state', '=', 'setup_incomplete')]
            ),
            'disconnecting': Store.search_count(
                term + [('state', '=', 'disconnecting')]
            ),
            'disconnected': Store.search_count(
                term + [('state', '=', 'disconnected')]
            ),
            'api_degraded': Store.search_count(
                term + [('api_health_state', 'in', ('throttled', 'degraded'))]
            ),
        }

    def _connector_health_store_rows(self, ctx):
        stores = ctx['stores']
        selected = ctx['store']
        visible = selected if len(selected) == 1 else stores
        if not visible:
            return {
                'available': False,
                'summary': {
                    'healthy': 0, 'working': 0,
                    'attention': 0, 'unknown': 0,
                },
                'rows': [],
            }
        Job = self.env['shopify.connector.job']
        Attempt = self.env['shopify.connector.mutation.attempt']
        ids = visible.ids
        backlog_rows = dict(Job._read_group(
            [('store_id', 'in', ids),
             ('state', 'in', ('queued', 'running', 'retry_waiting'))],
            groupby=['store_id'], aggregates=['__count'],
        ))
        attention_rows = dict(Job._read_group(
            [('store_id', 'in', ids),
             ('state', 'in', ('failed_retryable', 'failed_final',
                              'blocked_manual_review')),
             ('superseded_by_job_id', '=', False)],
            groupby=['store_id'], aggregates=['__count'],
        ))
        uncertain_rows = dict(Attempt._read_group(
            [('store_id', 'in', ids),
             ('observed_outcome', '=', 'uncertain'),
             ('resolution_disposition', '=', False)],
            groupby=['store_id'], aggregates=['__count'],
        ))
        latest_rows = dict(Job._read_group(
            [('store_id', 'in', ids), ('finished_at', '!=', False)],
            groupby=['store_id'], aggregates=['finished_at:max'],
        ))
        now = fields.Datetime.now()
        rows = []
        summary = {
            'healthy': 0, 'working': 0,
            'attention': 0, 'unknown': 0,
        }
        for candidate in visible:
            attention = (
                attention_rows.get(candidate, 0)
                + uncertain_rows.get(candidate, 0)
            )
            backlog = backlog_rows.get(candidate, 0)
            if (
                attention
                or candidate.state in (
                    'reconnect_needed', 'disconnecting', 'disconnected',
                )
                or candidate.api_health_state in ('throttled', 'degraded')
            ):
                tone = 'attention'
            elif (
                candidate.state != 'connected'
                or not candidate.api_health_state
                or not latest_rows.get(candidate)
            ):
                # A connected lifecycle flag is not proof that any domain has
                # run successfully or that Shopify API health was observed.
                tone = 'unknown'
            elif backlog:
                tone = 'working'
            else:
                tone = 'healthy'
            if tone == 'healthy':
                summary['healthy'] += 1
            elif tone == 'working':
                summary['working'] += 1
            elif tone == 'unknown':
                summary['unknown'] += 1
            elif tone == 'attention':
                summary['attention'] += 1
            latest = latest_rows.get(candidate)
            rows.append({
                'id': candidate.id,
                'name': candidate.name,
                'state': candidate.state,
                'tone': tone,
                'backlog': backlog,
                'attention': attention,
                'ambiguous_mutations': uncertain_rows.get(candidate, 0),
                'api_health': candidate.api_health_state or 'unknown',
                'last_activity': fields.Datetime.to_string(latest)
                    if latest else False,
                'last_activity_relative': self._relative_time(latest, now)
                    if latest else False,
            })
        return {'available': True, 'summary': summary, 'rows': rows}

    def _connector_health_throttle(self, ctx):
        selected = ctx['store']
        visible = selected if len(selected) == 1 else ctx['stores']
        rows = []
        now = fields.Datetime.now()
        for store in visible:
            ratio = store._throttle_headroom_ratio(now=now)
            if ratio is None:
                tone = 'unknown'
            elif ratio <= 0.10:
                tone = 'danger'
            elif ratio <= 0.25:
                tone = 'warning'
            else:
                tone = 'healthy'
            rows.append({
                'store_id': store.id,
                'store': store.name,
                'tone': tone,
                'headroom_ratio': ratio,
                'available': store._projected_throttle_available(now=now),
                'maximum': store.api_throttle_maximum or False,
                'restore_rate': store.api_throttle_restore_rate or False,
                'observed_at': fields.Datetime.to_string(
                    store.api_throttle_observed_at
                ) if store.api_throttle_observed_at else False,
            })
        return {'rows': rows}

    def _connector_health_mappings(self, store):
        term = self._store_term(store)
        specs = (
            ('products', 'shopify.connector.product.template.binding',
             _("Product mappings")),
            ('variants', 'shopify.connector.product.variant.binding',
             _("Variant mappings")),
            ('customers', 'shopify.connector.customer.binding',
             _("Customer mappings")),
            ('locations', 'shopify.connector.location.mapping',
             _("Location mappings")),
        )
        rows = []
        for key, model_name, label in specs:
            if model_name not in self.env:
                rows.append({
                    'id': key, 'label': label, 'state': 'unknown',
                    'count': False, 'reason': 'module_unavailable',
                })
                continue
            try:
                count = self.env[model_name].search_count(term)
            except AccessError:
                rows.append({
                    'id': key, 'label': label, 'state': 'unknown',
                    'count': False, 'reason': 'no_permission',
                })
                continue
            rows.append({
                'id': key,
                'label': label,
                'state': 'observed' if count else 'unknown',
                'count': count,
                'reason': False if count else 'no_evidence',
            })
        return {'rows': rows}

    def _connector_health_reconciliation(self, store):
        term = self._store_term(store)
        Job = self.env['shopify.connector.job']
        Attempt = self.env['shopify.connector.mutation.attempt']
        return {
            'pending_runs': Job.search_count(term + [
                ('job_source', '=', 'reconciliation'),
                ('state', 'in', ('draft', 'queued', 'running',
                                 'retry_waiting')),
            ]),
            'failed_runs': Job.search_count(term + [
                ('job_source', '=', 'reconciliation'),
                ('state', 'in', ('failed_retryable', 'failed_final',
                                 'blocked_manual_review')),
                ('superseded_by_job_id', '=', False),
            ]),
            'ambiguous_mutations': Attempt.search_count(term + [
                ('observed_outcome', '=', 'uncertain'),
                ('resolution_disposition', '=', False),
            ]),
            'verified_mutations': Attempt.search_count(term + [
                ('merchant_write_status', '=', 'verified'),
            ]),
        }

    def _connector_health_mode_switch(self, ctx):
        selected = ctx['store']
        visible = selected if len(selected) == 1 else ctx['stores']
        Settings = self.env['shopify.connector.store.settings']
        readable = Settings.fields_get()
        detailed = all(name in readable for name in (
            'fulfillment_operating_mode',
            'fulfillment_requested_mode',
            'fulfillment_mode_switch_state',
            'fulfillment_mode_switch_is_stale',
        ))
        settings_by_store = {
            row.store_id.id: row
            for row in Settings.search([('store_id', 'in', visible.ids)])
        } if detailed and visible else {}
        Job = self.env['shopify.connector.job']
        active_counts = dict(Job._read_group(
            [('store_id', 'in', visible.ids),
             ('job_type', '=', 'fulfillment_mode_switch_scan'),
             ('state', 'in', ('draft', 'queued', 'running',
                              'retry_waiting'))],
            groupby=['store_id'], aggregates=['__count'],
        )) if visible else {}
        failed_counts = dict(Job._read_group(
            [('store_id', 'in', visible.ids),
             ('job_type', '=', 'fulfillment_mode_switch_scan'),
             ('state', 'in', ('failed_retryable', 'failed_final',
                              'blocked_manual_review')),
             ('superseded_by_job_id', '=', False)],
            groupby=['store_id'], aggregates=['__count'],
        )) if visible else {}
        rows = []
        for store in visible:
            settings = settings_by_store.get(store.id)
            if settings:
                state = settings.fulfillment_mode_switch_state
                tone = 'danger' if (
                    settings.fulfillment_mode_switch_is_stale
                    or state in ('failed_retryable', 'failed_final')
                ) else ('working' if state in (
                    'queued', 'running', 'retry_waiting',
                ) else 'healthy')
                rows.append({
                    'store_id': store.id,
                    'store': store.name,
                    'available': True,
                    'tone': tone,
                    'effective_mode': settings.fulfillment_operating_mode,
                    'requested_mode': settings.fulfillment_requested_mode,
                    'state': state,
                    'stale': settings.fulfillment_mode_switch_is_stale,
                })
            else:
                active = active_counts.get(store, 0)
                failed = failed_counts.get(store, 0)
                rows.append({
                    'store_id': store.id,
                    'store': store.name,
                    'available': False,
                    'tone': 'danger' if failed else (
                        'working' if active else 'unknown'
                    ),
                    'effective_mode': False,
                    'requested_mode': False,
                    'state': 'failed' if failed else (
                        'running' if active else 'unknown'
                    ),
                    'stale': False,
                })
        return {'rows': rows}
