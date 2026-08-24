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
        store_region = self._connector_health_store_rows(ctx)
        derived = self._derive_state(
            store_states, jobs, attempts_uncertain,
        )
        derived = self._operational_health_lead(derived, store_region)
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
            'stores_region': store_region,
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
        settings_model = self.env['shopify.connector.store.settings']
        settings_by_store = {
            row.store_id.id: row
            for row in settings_model.search([('store_id', 'in', ids)])
        }
        mapping_counts = self._operational_group_count(
            'shopify.connector.location.mapping', ids,
            [('status', '=', 'active'), ('push_enabled', '=', True)],
        )
        unconfirmed_counts = self._operational_group_count(
            'shopify.connector.inventory.level.binding', ids,
            [('status', '=', 'active'),
             ('first_push_state', '!=', 'confirmed')],
        )
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
            operational = self._derive_store_operational_state(
                candidate,
                settings_by_store.get(candidate.id),
                backlog,
                attention,
                mapping_counts.get(candidate.id, 0),
                unconfirmed_counts.get(candidate.id, 0),
            )
            tone = operational['tone']
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
                'operational_state': operational['state'],
                'operational_label': operational['label'],
                'operational_reason': operational['reason'],
                'next_action': operational['next_action'],
                'domains_selected': operational['domains_selected'],
                'domains_completed': operational['domains_completed'],
                'initial_child_pending': backlog,
                'initial_child_review': attention,
                'last_activity': fields.Datetime.to_string(latest)
                    if latest else False,
                'last_activity_relative': self._relative_time(latest, now)
                    if latest else False,
            })
        return {'available': True, 'summary': summary, 'rows': rows}

    def _operational_group_count(self, model_name, store_ids, extra_domain):
        """Return one grouped count without depending on optional addons."""
        if model_name not in self.env or not store_ids:
            return {}
        try:
            rows = self.env[model_name]._read_group(
                [('store_id', 'in', store_ids)] + list(extra_domain),
                groupby=['store_id'], aggregates=['__count'],
            )
        except AccessError:
            return {}
        return {store.id: count for store, count in rows}

    def _derive_store_operational_state(
        self, store, settings, backlog, attention, active_mapping_count,
        unconfirmed_inventory_count,
    ):
        """Project one truthful lifecycle from existing durable evidence.

        `connected` is transport identity, never readiness. Required producer
        completion comes from the existing per-domain high-water marks; queue,
        review, mapping, first-push, API-health and connection evidence decide
        whether initial synchronization is pending, running, blocked or ready.
        """
        fixed = {
            'setup_incomplete': (
                'setup_incomplete', 'Setup Incomplete', 'unknown',
                'Complete the guided setup.',
            ),
            'reconnect_needed': (
                'reconnect_required', 'Reconnect Required', 'attention',
                'Reconnect and verify the merchant-managed custom app.',
            ),
            'disconnecting': (
                'disconnected', 'Disconnected', 'attention',
                'Wait for disconnect cleanup to finish.',
            ),
            'disconnected': (
                'disconnected', 'Disconnected', 'attention',
                'Reconnect the store to resume synchronization.',
            ),
        }
        if store.state in fixed:
            state, label, tone, action = fixed[store.state]
            return self._operational_payload(
                state, label, tone, action, 0, 0,
                'The store connection lifecycle is %s.' % label.lower(),
            )

        domains = []
        field_specs = (
            ('product_domain_enabled', 'catalog',
             'product_last_import_success_at'),
            ('sale_domain_enabled', 'orders',
             'sale_order_catchup_synced_through_at'),
            ('inventory_domain_enabled', 'inventory',
             'inventory_last_push_scan_at'),
            ('fulfillment_domain_enabled', 'fulfillment',
             'fulfillment_catchup_observed_through_at'),
        )
        anchors = []
        for enabled_field, family, anchor_field in field_specs:
            if settings and enabled_field in settings._fields and settings[enabled_field]:
                anchor = (
                    settings[anchor_field]
                    if anchor_field in settings._fields else False
                )
                domains.append((family, bool(anchor)))
                if anchor:
                    anchors.append(anchor)
        selected = len(domains)
        completed = sum(1 for _family, done in domains if done)
        inventory_enabled = any(
            family == 'inventory' for family, _done in domains
        )
        mapping_blocked = inventory_enabled and not active_mapping_count
        first_push_blocked = inventory_enabled and bool(
            unconfirmed_inventory_count
        )

        if attention or mapping_blocked or first_push_blocked:
            if mapping_blocked:
                action = 'Map at least one active Shopify location.'
                reason = 'Inventory is enabled but no active push mapping exists.'
            elif first_push_blocked:
                action = 'Review and confirm each current first-push preview.'
                reason = '%d inventory pair(s) still require first-push review.' % (
                    unconfirmed_inventory_count,
                )
            else:
                action = 'Open Needs Attention and resolve the blocking case.'
                reason = '%d initial or current case(s) need a person.' % attention
            return self._operational_payload(
                'initial_sync_needs_attention',
                'Initial Sync Needs Attention', 'attention', action,
                selected, completed, reason,
            )
        if store.api_health_state in ('throttled', 'degraded'):
            return self._operational_payload(
                'degraded', 'Degraded', 'attention',
                'Review Shopify API health and allow recovery before resuming.',
                selected, completed,
                'Shopify API health is %s.' % store.api_health_state,
            )
        if selected == 0 or completed < selected:
            if backlog:
                return self._operational_payload(
                    'initial_sync_running', 'Initial Sync Running', 'working',
                    'Monitor progress; resolve an exception if one appears.',
                    selected, completed,
                    '%d of %d selected domain(s) have completion evidence.' % (
                        completed, selected,
                    ),
                )
            return self._operational_payload(
                'connected_initial_sync_pending',
                'Connected — Initial Sync Pending', 'unknown',
                'Start or wait for the selected initial scans.',
                selected, completed,
                ('No synchronization domain is selected.' if not selected else
                 '%d of %d selected domain(s) have completion evidence.' % (
                     completed, selected,
                 )),
            )
        if backlog:
            return self._operational_payload(
                'initial_sync_running', 'Initial Sync Running', 'working',
                'Monitor progress; resolve an exception if one appears.',
                selected, completed,
                '%d child operation(s) are still pending.' % backlog,
            )
        if store.api_health_state != 'normal':
            return self._operational_payload(
                'connected_initial_sync_pending',
                'Connected — Initial Sync Pending', 'unknown',
                'Run the connection and scope verification again.',
                selected, completed,
                'Synchronization evidence exists, but current Shopify API '
                'identity and scope health is not proven normal.',
            )
        freshness_cutoff = fields.Datetime.subtract(
            fields.Datetime.now(), days=1,
        )
        if any(anchor < freshness_cutoff for anchor in anchors):
            return self._operational_payload(
                'degraded', 'Degraded', 'attention',
                'Run reconciliation and review Connector Health.',
                selected, completed,
                'Required evidence is stale or Shopify API health is degraded.',
            )
        return self._operational_payload(
            'ready', 'Ready', 'healthy', 'No action is required.',
            selected, completed,
            'Every selected domain has fresh completion evidence and no '
            'blocking exception or first-push decision remains.',
        )

    @staticmethod
    def _operational_payload(
        state, label, tone, next_action, selected, completed, reason,
    ):
        return {
            'state': state,
            'label': label,
            'tone': tone,
            'next_action': next_action,
            'domains_selected': selected,
            'domains_completed': completed,
            'reason': reason,
        }

    def _operational_health_lead(self, derived, store_region):
        """Prevent a green lead before operational readiness is proven."""
        if derived['state'] not in ('healthy', 'warning'):
            return derived
        rows = store_region.get('rows') or []
        states = {row.get('operational_state') for row in rows}
        if 'degraded' in states:
            return {
                'state': 'degraded',
                'lead': {
                    'severity': 'danger', 'icon': 'fa-exclamation-triangle',
                    'text': _('Connector operation is degraded'),
                    'hint': _('Review Shopify API health and stale evidence.'),
                },
            }
        if 'initial_sync_needs_attention' in states:
            return {
                'state': 'initial_sync_needs_attention',
                'lead': {
                    'severity': 'danger', 'icon': 'fa-hand-paper-o',
                    'text': _('Initial synchronization needs attention'),
                    'hint': _('Open the affected store row or Needs Attention.'),
                },
            }
        if 'initial_sync_running' in states:
            return {
                'state': 'initial_sync_running',
                'lead': {
                    'severity': 'info', 'icon': 'fa-refresh',
                    'text': _('Initial synchronization is running'),
                    'hint': _('The selected domains are still producing work.'),
                },
            }
        if 'connected_initial_sync_pending' in states:
            return {
                'state': 'connected_initial_sync_pending',
                'lead': {
                    'severity': 'info', 'icon': 'fa-clock-o',
                    'text': _('Connected — initial synchronization pending'),
                    'hint': _('Connected is not Ready; required completion evidence is missing.'),
                },
            }
        return derived

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
        latest = Job._read_group(
            term + [('job_source', '=', 'reconciliation'),
                    ('state', '=', 'succeeded'),
                    ('finished_at', '!=', False)],
            aggregates=['finished_at:max'],
        )
        last_success = latest[0][0] if latest else False
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
            'last_success': fields.Datetime.to_string(last_success)
                if last_success else False,
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
