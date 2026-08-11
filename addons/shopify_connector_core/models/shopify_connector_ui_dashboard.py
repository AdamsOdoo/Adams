# Part of the Shopify Connector (U0 operator UI foundation).
#
# Read-only operator dashboard aggregate service.
#
# This is the ONE bounded, read-only aggregate service that backs the U0
# operational dashboard Owl client action (see
# static/src/js/shopify_connector_dashboard.js). It is deliberately an
# ``AbstractModel`` -- it owns no table, no ACL row, and no persistent state.
# It exposes bounded compatibility, sales, and operational-health projections;
# each returns a JSON-serialisable dict and never performs a Shopify call.
#
# Hard guarantees this service upholds (enforced by test_ui_dashboard.py,
# test_ui_performance.py and test_ui_source_guards.py):
#   * It performs ONLY bounded aggregate reads -- ``search_count`` for every
#     headline number and a single explicitly ``limit``-ed ``search_read`` for
#     the recent-activity feed. It never loads an unbounded recordset, never
#     reads a full jobs/logs table, and issues a CONSTANT number of queries
#     regardless of data volume (RD-1 vs RD-2), so it cannot degrade
#     super-linearly (PB-9/PB-10/PB-11).
#   * It issues no Shopify request, reads no credential, and performs no write
#     or other mutation. It is a pure projection of already-stored connector
#     evidence.
#   * It never returns a credential, a credential fragment, a raw request /
#     response payload, a stack trace, a customer name / email / phone /
#     address, or a raw internal state token as merchant-facing copy. Only
#     non-sensitive operational aggregates and plain-language labels cross the
#     RPC boundary.
#
# The single dashboard severity model lives in :meth:`_derive_state`: the lead
# answer's severity is the severity of the most-severe *active* item, so a
# healthy (success) lead can never coexist with an active failed / blocked /
# retry count, and a resolved item is never counted as active.

from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ShopifyConnectorUiDashboard(models.AbstractModel):
    _name = 'shopify.connector.ui.dashboard'
    _description = 'Shopify Connector Operator Dashboard (read-only aggregate service)'

    # --- bounds (every query below is capped by one of these) ---------------
    RECENT_ACTIVITY_LIMIT = 8
    MAX_EXCEPTIONS = 3
    SPARKLINE_DAYS = 7

    # Job states that read as "attention required" on the operator surfaces.
    _DANGER_JOB_STATES = ('blocked_manual_review', 'failed_final', 'failed_retryable')
    _WARNING_JOB_STATES = ('retry_waiting',)
    _IN_PROGRESS_JOB_STATES = ('queued', 'running')
    _TERMINAL_JOB_STATES = ('succeeded', 'failed_final', 'skipped', 'cancelled')

    # ------------------------------------------------------------------ #
    #  Public RPC entrypoint
    # ------------------------------------------------------------------ #
    @api.model
    def get_dashboard_data(self):
        """Return the full, bounded, read-only dashboard projection.

        The result is a JSON-serialisable dict. Called once per render and
        once per (>=30s, visibility-aware) auto-refresh by the Owl client
        action. Runs entirely as the *current* user, so per-user ACLs on the
        underlying records apply -- a user who cannot read jobs cannot leak
        them through this service.
        """
        # Defence in depth: the menu/action is already group-gated, but refuse
        # the data to any non-connector user so the aggregate can never leak to
        # a caller outside the connector groups.
        if not self.env.user.has_group('shopify_connector_core.group_shopify_connector_auditor'):
            raise AccessError(_("The Shopify Connector dashboard is only available to connector users."))

        stores = self._store_counts()
        jobs = self._job_counts()
        attempts_uncertain = self._uncertain_attempt_count()

        derived = self._derive_state(stores, jobs, attempts_uncertain)
        exceptions = self._build_exceptions(stores, jobs, attempts_uncertain)
        chips = self._build_chips(stores, jobs, attempts_uncertain)
        activity = self._recent_activity()
        sparkline = self._sparkline()

        return {
            'state': derived['state'],
            'lead': derived['lead'],
            'exceptions': exceptions,
            'affirmative': _("All clear — nothing needs your attention right now."),
            'chips': chips,
            'activity': activity,
            'cadence': self._cadence_line(activity),
            'sparkline': sparkline,
            'stores': stores,
            # S1 entry route 1 of 3: the first-run empty state offers setup.
            # A flag rather than an action payload, and gated on the same
            # Administrator group the setup service enforces server-side --
            # the dashboard is visible to every connector role, and offering
            # a control the setup service would refuse is how a surface
            # teaches operators to distrust it.
            'setup_available': self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            'refresh_interval_seconds': 30,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }

    # ------------------------------------------------------------------ #
    #  Store 360 (spec docs/02-product/ui-operations-360-dashboard-spec-
    #  2026-08-01.md) — second RPC entrypoint, same read-only contract
    # ------------------------------------------------------------------ #

    # The one server-side period registry. The client sends a KEY, never a
    # domain, a model name, a context or a date expression (task §7).
    STORE_360_PERIODS = ('24h', '7d', '30d', '90d')
    _PERIOD_DAYS = {'7d': 7, '30d': 30, '90d': 90}

    @api.model
    def get_store_360_data(self, store_id=False, period='30d'):
        """Return the Store 360 projection: sales performance + connector
        health for the selected store and period.

        Same hard guarantees as :meth:`get_dashboard_data` — bounded
        constant-count reads, current user only, no Shopify request, no
        credential, no write, no hidden-record identifiers or labels in the
        payload. Commercial and lifecycle regions are contributed by the
        owning modules through :meth:`_store_360_extra_sections`, each
        aggregating ON the model whose record rules govern it and drilling
        down to a native list of that SAME model with the identical
        server-built domain (spec §6.1).
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_auditor'
        ):
            raise AccessError(_(
                "The Shopify Connector dashboard is only available to "
                "connector users."
            ))
        period = self._store_360_validate_period(period)
        stores = self.env['shopify.connector.store'].search([], order='id')
        store = self._store_360_validate_store(store_id, stores)
        window = self._store_360_window(period)
        ctx = {
            'store': store,
            'stores': stores,
            'period': period,
            'window': window,
        }

        jobs = self._job_counts_scoped(store)
        attempts_uncertain = self._uncertain_attempt_count_scoped(store)
        store_states = self._store_counts()
        derived = self._derive_state(store_states, jobs, attempts_uncertain)
        payload = {
            'meta': self._store_360_meta(ctx),
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
            'stores_region': self._store_360_stores_region(ctx),
            'setup_available': self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            'refresh_interval_seconds': 30,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }
        payload.update(self._store_360_extra_sections(ctx))
        payload['critical'] = self._store_360_critical(ctx, payload)
        return payload

    @api.model
    def get_sales_dashboard_data(self, store_id=False, period='30d'):
        """Return only the merchant sales projection.

        C7 deliberately separates sales reporting from connector health. The
        owning sale module still contributes the bounded, rule-faithful
        commercial/lifecycle reads through ``_store_360_extra_sections``;
        this method selects only those sales sections and never computes or
        returns queue, attempt, throttle, mapping, or mode-switch aggregates.
        """
        self._ensure_dashboard_user()
        period = self._store_360_validate_period(period)
        stores = self.env['shopify.connector.store'].search([], order='id')
        store = self._store_360_validate_store(store_id, stores)
        ctx = {
            'store': store,
            'stores': stores,
            'period': period,
            'window': self._store_360_window(period),
        }
        contributed = self._store_360_extra_sections(ctx)
        sales_keys = ('commercial', 'bridge', 'lifecycle', 'dispatch')
        payload = {
            'meta': self._store_360_meta(ctx),
            # The app root is the sales dashboard, including on a true first
            # run. Preserve the setup entry route here as well as on Connector
            # Health; otherwise an administrator with no visible stores lands
            # on an honest "sales unavailable" screen with no way to begin.
            'setup_available': self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            'refresh_interval_seconds': 30,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }
        payload.update({
            key: contributed[key]
            for key in sales_keys
            if key in contributed
        })
        payload.setdefault(
            'commercial', {'available': False, 'reason': 'module_unavailable'}
        )
        payload.setdefault(
            'lifecycle', {'available': False, 'reason': 'module_unavailable'}
        )
        payload['critical'] = self._store_360_critical(ctx, payload)
        return payload

    @api.model
    def _ensure_dashboard_user(self):
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_auditor'
        ):
            raise AccessError(_(
                "The Shopify Connector dashboard is only available to "
                "connector users."
            ))

    # -- validation (server-side, fixed registries only) ------------------
    @api.model
    def _store_360_validate_period(self, period):
        if period not in self.STORE_360_PERIODS:
            raise UserError(_(
                "Unknown reporting period. Choose one of the offered "
                "periods."
            ))
        return period

    @api.model
    def _store_360_validate_store(self, store_id, stores):
        """Resolve the store filter against the caller's own visible set.

        `stores` was searched as the current user, so a store another
        company owns is simply not in it — an out-of-set id gets the same
        refusal as a nonsense id, and no probe can distinguish "exists but
        hidden" from "does not exist".
        """
        if not store_id:
            return stores if len(stores) == 1 else stores.browse()
        if not isinstance(store_id, int) or store_id not in set(stores.ids):
            raise UserError(_("Unknown store."))
        return stores.browse(store_id)

    @api.model
    def _store_360_window(self, period):
        """Current + previous window bounds, user-timezone boundaries.

        Returns naive-UTC datetimes for domains plus the timezone name for
        the caption. The previous window is the current one shifted back by
        its own length (spec C∆).
        """
        tzname = self.env.user.tz or 'UTC'
        try:
            tz = pytz.timezone(tzname)
        except pytz.UnknownTimeZoneError:
            tzname, tz = 'UTC', pytz.utc
        now_utc = fields.Datetime.now()
        now_local = pytz.utc.localize(now_utc).astimezone(tz)
        if period == '24h':
            end_local = now_local
            start_local = end_local - timedelta(hours=24)
        else:
            days = self._PERIOD_DAYS[period]
            end_local = now_local
            start_local = (
                now_local - timedelta(days=days - 1)
            ).replace(hour=0, minute=0, second=0, microsecond=0)
        duration = end_local - start_local
        prev_end_local = start_local
        prev_start_local = start_local - duration

        def _utc(value):
            return value.astimezone(pytz.utc).replace(tzinfo=None)

        return {
            'tz': tzname,
            'start': _utc(start_local),
            'end': _utc(end_local),
            'prev_start': _utc(prev_start_local),
            'prev_end': _utc(prev_end_local),
        }

    def _store_360_meta(self, ctx):
        store = ctx['store']
        window = ctx['window']
        return {
            'period': ctx['period'],
            'periods': list(self.STORE_360_PERIODS),
            'tz': window['tz'],
            'window_start': fields.Datetime.to_string(window['start']),
            'window_end': fields.Datetime.to_string(window['end']),
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

    # -- extension seam ----------------------------------------------------
    def _store_360_extra_sections(self, ctx):
        """Sections contributed by the owning modules.

        Core owns connector health only. The sale module adds `commercial`,
        `bridge`, `trend`, `products` and `lifecycle`; the fulfillment
        module adds `dispatch` and its lifecycle exception sources. Each
        override calls ``super()`` and updates the dict, and each section
        aggregates on the model whose rules govern it (spec §6.1) — this
        seam mirrors `_get_handlers` in the job dispatcher.
        """
        return {}

    # -- store-scoped bounded reads ----------------------------------------
    def _store_term(self, store):
        return [('store_id', '=', store.id)] if len(store) == 1 else []

    def _job_counts_scoped(self, store):
        Job = self.env['shopify.connector.job']
        term = self._store_term(store)
        return {
            state: Job.search_count(term + [('state', '=', state)])
            for state in (
                'queued', 'running', 'retry_waiting', 'failed_retryable',
                'failed_final', 'blocked_manual_review',
            )
        }

    def _uncertain_attempt_count_scoped(self, store):
        return self.env['shopify.connector.mutation.attempt'].search_count(
            self._store_term(store) + [
                ('observed_outcome', '=', 'uncertain'),
                ('resolution_disposition', '=', False),
            ]
        )

    def _oldest_blocked(self, store):
        domain = self._store_term(store) + [
            ('state', '=', 'blocked_manual_review'),
        ]
        oldest = self.env['shopify.connector.job'].search(
            domain,
            order='create_date asc', limit=1,
        )
        if not oldest:
            return False
        return {
            'age': self._relative_time(
                oldest.create_date, fields.Datetime.now(),
            ),
            'target': {
                'res_model': 'shopify.connector.job',
                'domain': self._serialize_domain(domain),
                'name': _('Blocked connector cases'),
            },
        }

    def _week_counters(self, store):
        Job = self.env['shopify.connector.job']
        term = self._store_term(store)
        window_start = fields.Datetime.now() - timedelta(days=7)
        base = term + [('finished_at', '>=', window_start)]
        return {
            'succeeded': Job.search_count(base + [('state', '=', 'succeeded')]),
            'failed': Job.search_count(
                base + [('state', 'in', ('failed_final', 'failed_retryable'))]
            ),
        }

    def _recent_activity_scoped(self, store):
        rows = self.env['shopify.connector.job'].search_read(
            domain=self._store_term(store) + [
                ('state', 'in', list(self._TERMINAL_JOB_STATES)),
            ],
            fields=['state', 'job_type', 'job_source', 'store_id',
                    'finished_at'],
            limit=self.RECENT_ACTIVITY_LIMIT,
            order='finished_at desc, id desc',
        )
        now = fields.Datetime.now()
        return [
            {
                'id': row['id'],
                'state': row['state'],
                'state_label': self._job_state_label(row['state']),
                'tone': self._job_state_tone(row['state']),
                'job_label': self._job_type_label(row['job_type']),
                'source_label': self._job_source_label(row['job_source']),
                'store': (row['store_id'] or [0, ''])[1]
                    if row.get('store_id') else '',
                'relative': self._relative_time(row.get('finished_at'), now),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [['id', '=', row['id']]],
                    'name': _("Run"),
                },
            }
            for row in rows
        ]

    def _store_360_exceptions(self, store, jobs, attempts_uncertain):
        """The existing exception builder, store-scoped, plus the two
        registry-guarded decision sources (F7). Count == target-domain count
        stays the load-bearing invariant."""
        term = self._store_term(store)
        term_json = [list(t) for t in term]
        candidates = [
            {
                'id': 'blocked_manual_review',
                'severity': 'danger',
                'icon': 'fa-hand-paper-o',
                'title': _("Runs waiting on a review decision"),
                'count': jobs['blocked_manual_review'],
                'why': _("A reviewer needs to decide how these proceed."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': term_json + [
                        ['state', '=', 'blocked_manual_review']],
                    'name': _("Runs waiting on a review decision"),
                },
            },
            {
                'id': 'uncertain_mutation',
                'severity': 'danger',
                'icon': 'fa-hand-paper-o',
                'title': _("Changes waiting on an administrator decision"),
                'count': attempts_uncertain,
                'why': _("An outcome could not be confirmed and needs an "
                         "administrator judgement."),
                'owner': _("Administrator"),
                'target': {
                    'res_model': 'shopify.connector.mutation.attempt',
                    'domain': term_json + [
                        ['observed_outcome', '=', 'uncertain'],
                        ['resolution_disposition', '=', False]],
                    'name': _("Changes waiting on a decision"),
                },
            },
            {
                'id': 'failed_final',
                'severity': 'danger',
                'icon': 'fa-exclamation-triangle',
                'title': _("Runs that stopped after repeated failures"),
                'count': jobs['failed_final'],
                'why': _("These stopped retrying — review the reason to get "
                         "them moving again."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': term_json + [['state', '=', 'failed_final']],
                    'name': _("Runs that stopped after repeated failures"),
                },
            },
            {
                'id': 'failed_retryable',
                'severity': 'danger',
                'icon': 'fa-exclamation-triangle',
                'title': _("Runs that need a fix before retrying"),
                'count': jobs['failed_retryable'],
                'why': _("These are paused for a manual fix, then a retry."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': term_json + [['state', '=', 'failed_retryable']],
                    'name': _("Runs that need a fix before retrying"),
                },
            },
        ]
        if not len(store) == 1:
            reconnect_count = self.env[
                'shopify.connector.store'
            ].search_count([('state', '=', 'reconnect_needed')])
            candidates.append({
                'id': 'reconnect_needed',
                'severity': 'warning',
                'icon': 'fa-plug',
                'title': _("Stores that need reconnecting"),
                'count': reconnect_count,
                'why': _("Shopify no longer accepts the saved credentials — "
                         "reconnect to resume."),
                'owner': _("Administrator"),
                'target': {
                    'res_model': 'shopify.connector.store',
                    'domain': [['state', '=', 'reconnect_needed']],
                    'name': _("Stores that need reconnecting"),
                },
            })
        elif store.state == 'reconnect_needed':
            candidates.append({
                'id': 'reconnect_needed',
                'severity': 'warning',
                'icon': 'fa-plug',
                'title': _("This store needs reconnecting"),
                'count': 1,
                'why': _("Shopify no longer accepts the saved credentials — "
                         "reconnect to resume."),
                'owner': _("Administrator"),
                'target': {
                    'res_model': 'shopify.connector.store',
                    'domain': [['id', '=', store.id]],
                    'name': _("Store"),
                },
            })
        # Registry-guarded decision source: product match decisions. Core
        # does not depend on the product module; reading it only when its
        # model is genuinely in the registry keeps core installable alone
        # while F4/F7 stay complete on a full install (the product module's
        # files are outside this batch's write-set by the frozen manifest).
        if 'shopify.connector.product.match.decision' in self.env:
            pending = self.env[
                'shopify.connector.product.match.decision'
            ].search_count(term + [('state', '=', 'pending')])
            candidates.append({
                'id': 'match_decisions',
                'severity': 'danger',
                'icon': 'fa-hand-paper-o',
                'title': _("Product matches waiting on a decision"),
                'count': pending,
                'why': _("A reviewer must choose the matching product "
                         "before these products sync."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.product.match.decision',
                    'domain': term_json + [['state', '=', 'pending']],
                    'name': _("Product matches waiting on a decision"),
                },
            })
        active = [c for c in candidates if c['count'] > 0]
        severity_rank = {'danger': 0, 'warning': 1, 'info': 2}
        active.sort(key=lambda c: (severity_rank.get(c['severity'], 3),
                                   -c['count']))
        return active[:self.MAX_EXCEPTIONS]

    # -- flow rows (F6) ------------------------------------------------------
    _FLOW_FAMILIES = (
        ('orders', ('order_import_scan', 'order_import_sync',
                    'customer_import_sync')),
        ('catalog', ('product_import_scan', 'product_import_sync')),
        ('inventory', ('inventory_push_sync', 'inventory_push_scan',
                       'inventory_first_push_preview',
                       'inventory_location_sync', 'inventory_activate',
                       'inventory_set_quantities',
                       'inventory_mutation_reconcile')),
        ('export', ()),      # filled by prefix below
        ('fulfillment', ()),  # filled by prefix below
    )

    def _flow_family_of(self, job_type):
        if not job_type:
            return False
        if job_type.startswith('product_export_'):
            return 'export'
        if job_type.startswith('fulfillment_'):
            return 'fulfillment'
        for family, types in self._FLOW_FAMILIES:
            if job_type in types:
                return family
        return False

    def _flow_rows(self, ctx):
        """Five flow rows from two grouped reads (constant query count).

        Last-success anchors are the per-domain settings watermarks, read
        only when the owning module actually contributes the field —
        field-presence guarded for the same reason as the registry guard
        above."""
        Job = self.env['shopify.connector.job']
        store = ctx['store']
        term = self._store_term(store)
        backlog_rows = Job._read_group(
            term + [('state', 'in', ('queued', 'running', 'retry_waiting'))],
            groupby=['job_type'], aggregates=['__count'],
        )
        failure_rows = Job._read_group(
            term + [('state', 'in', ('failed_retryable', 'failed_final',
                                     'blocked_manual_review'))],
            groupby=['job_type'], aggregates=['__count'],
        )
        success_rows = Job._read_group(
            term + [('state', '=', 'succeeded'),
                    ('finished_at', '!=', False)],
            groupby=['job_type'], aggregates=['finished_at:max'],
        )
        backlog = {}
        failures = {}
        successes = {}
        for job_type, count in backlog_rows:
            family = self._flow_family_of(job_type)
            if family:
                backlog[family] = backlog.get(family, 0) + count
        for job_type, count in failure_rows:
            family = self._flow_family_of(job_type)
            if family:
                failures[family] = failures.get(family, 0) + count
        for job_type, finished_at in success_rows:
            family = self._flow_family_of(job_type)
            if family and (
                not successes.get(family)
                or finished_at > successes[family]
            ):
                successes[family] = finished_at

        settings = self.env['shopify.connector.store.settings']
        row = settings.search(
            [('store_id', '=', store.id)], limit=1,
        ) if len(store) == 1 else settings.browse()
        anchors = {}
        anchor_fields = {
            'orders': 'sale_order_catchup_synced_through_at',
            'catalog': 'product_last_import_success_at',
            'inventory': 'inventory_last_push_scan_at',
            'fulfillment': 'fulfillment_catchup_observed_through_at',
        }
        for family, field_name in anchor_fields.items():
            if row and field_name in settings._fields:
                anchors[family] = fields.Datetime.to_string(
                    row[field_name]
                ) if row[field_name] else False
            else:
                anchors[family] = False
        labels = {
            'orders': _("Orders"),
            'catalog': _("Catalog"),
            'inventory': _("Inventory"),
            'export': _("Product export"),
            'fulfillment': _("Fulfillment"),
        }
        now = fields.Datetime.now()
        rows = []
        for family in ('orders', 'catalog', 'inventory', 'export',
                       'fulfillment'):
            anchor = anchors.get(family)
            success = successes.get(family)
            if success and (
                not anchor
                or success > fields.Datetime.from_string(anchor)
            ):
                anchor = fields.Datetime.to_string(success)
            failures_count = failures.get(family, 0)
            backlog_count = backlog.get(family, 0)
            rows.append({
                'id': family,
                'label': labels[family],
                'backlog': backlog_count,
                'failures': failures_count,
                'last_success': anchor,
                'last_success_relative': self._relative_time(
                    fields.Datetime.from_string(anchor), now,
                ) if anchor else False,
                'tone': 'danger' if failures_count
                        else ('info' if backlog_count
                              else ('healthy' if anchor else 'unknown')),
            })
        return rows

    # -- multi-store region (H1) ---------------------------------------------
    def _store_360_stores_region(self, ctx):
        """Per-store operational cells from grouped reads (no per-store
        loop queries; the sale module adds the per-store sales cell in its
        own section)."""
        stores = ctx['stores']
        if len(stores) <= 1:
            return {'available': False, 'rows': []}
        Job = self.env['shopify.connector.job']
        backlog_rows = dict(Job._read_group(
            [('store_id', 'in', stores.ids),
             ('state', 'in', ('queued', 'running', 'retry_waiting'))],
            groupby=['store_id'], aggregates=['__count'],
        ))
        attention_rows = dict(Job._read_group(
            [('store_id', 'in', stores.ids),
             ('state', 'in', ('failed_retryable', 'failed_final',
                              'blocked_manual_review'))],
            groupby=['store_id'], aggregates=['__count'],
        ))
        latest_rows = {
            group: value
            for group, value in Job._read_group(
                [('store_id', 'in', stores.ids),
                 ('finished_at', '!=', False)],
                groupby=['store_id'], aggregates=['finished_at:max'],
            )
        }
        now = fields.Datetime.now()
        rows = []
        for store in stores:
            latest = latest_rows.get(store)
            rows.append({
                'id': store.id,
                'name': store.name,
                'state': store.state,
                'backlog': backlog_rows.get(store, 0),
                'attention': attention_rows.get(store, 0),
                'last_activity_relative':
                    self._relative_time(latest, now) if latest else False,
            })
        return {'available': True, 'rows': rows}

    # -- critical band (B1) ----------------------------------------------------
    def _store_360_critical(self, ctx, payload):
        """Derived after every section: does a connector problem make the
        money numbers wrong right now? Renders only when true, and names
        the worst cause with a direct route."""
        store = ctx['store']
        causes = []
        bridge = payload.get('bridge') or {}
        if len(store) == 1 and store.state in (
            'reconnect_needed', 'disconnected', 'disconnecting',
        ):
            causes.append({
                'id': 'store_state',
                'text': _("Shopify connection unavailable — figures are "
                          "last known and may be incomplete."),
                'target': {
                    'res_model': 'shopify.connector.store',
                    'domain': [['id', '=', store.id]],
                    'name': _("Store"),
                },
            })
        if bridge.get('state') in ('stale', 'incomplete'):
            causes.append({
                'id': 'bridge_%s' % bridge['state'],
                'text': bridge.get('critical_text') or _(
                    "Order import completeness cannot be proven — the "
                    "figures below may be missing recent orders."),
                'target': bridge.get('critical_target') or {
                    'res_model': 'shopify.connector.job',
                    'domain': [['state', 'in',
                                ['failed_retryable', 'failed_final',
                                 'blocked_manual_review']]],
                    'name': _("Needs Attention"),
                },
            })
        return {
            'active': bool(causes),
            'causes': causes,
        }

    # ------------------------------------------------------------------ #
    #  Bounded aggregate reads
    # ------------------------------------------------------------------ #
    def _store_counts(self):
        Store = self.env['shopify.connector.store']
        return {
            'total': Store.search_count([]),
            'connected': Store.search_count([('state', '=', 'connected')]),
            'reconnect_needed': Store.search_count([('state', '=', 'reconnect_needed')]),
            'setup_incomplete': Store.search_count([('state', '=', 'setup_incomplete')]),
            'disconnecting': Store.search_count([('state', '=', 'disconnecting')]),
            'disconnected': Store.search_count([('state', '=', 'disconnected')]),
            'api_degraded': Store.search_count([('api_health_state', 'in', ('throttled', 'degraded'))]),
        }

    def _job_counts(self):
        Job = self.env['shopify.connector.job']
        # One indexed count per state we surface. Constant query count.
        return {
            'queued': Job.search_count([('state', '=', 'queued')]),
            'running': Job.search_count([('state', '=', 'running')]),
            'retry_waiting': Job.search_count([('state', '=', 'retry_waiting')]),
            'failed_retryable': Job.search_count([('state', '=', 'failed_retryable')]),
            'failed_final': Job.search_count([('state', '=', 'failed_final')]),
            'blocked_manual_review': Job.search_count([('state', '=', 'blocked_manual_review')]),
            'skipped': Job.search_count([('state', '=', 'skipped')]),
        }

    def _uncertain_attempt_count(self):
        # "Active" needs-a-decision attempts = observed uncertain AND not yet
        # resolved. A resolved attempt carries resolution_disposition and is
        # therefore excluded here -- the "resolved excluded from active" rule.
        return self.env['shopify.connector.mutation.attempt'].search_count([
            ('observed_outcome', '=', 'uncertain'),
            ('resolution_disposition', '=', False),
        ])

    # ------------------------------------------------------------------ #
    #  The single dashboard severity model
    # ------------------------------------------------------------------ #
    def _derive_state(self, stores, jobs, attempts_uncertain):
        """Derive the one lead answer + its severity from the aggregates.

        Guarantees, all asserted by test_ui_dashboard.py:
          * a ``success`` (healthy) lead requires ZERO danger AND ZERO warning
            active items -- it can never coexist with an active failed /
            blocked / retry count;
          * ``manual_review`` is used only when every active danger item is a
            decision item (blocked_manual_review job or uncertain attempt) and
            there is no technical failure or reconnect;
          * every non-empty, non-loading band colour equals the severity of the
            most-severe active item.
        """
        manual_review = jobs['blocked_manual_review'] + attempts_uncertain
        technical_fail = jobs['failed_final'] + jobs['failed_retryable']
        reconnect = stores['reconnect_needed']
        warning_active = jobs['retry_waiting'] + reconnect + stores['api_degraded']
        danger_active = manual_review + technical_fail

        # First-run / empty: nothing operational to report yet.
        if stores['total'] == 0 or (stores['connected'] == 0 and stores['setup_incomplete'] > 0
                                    and danger_active == 0 and jobs['retry_waiting'] == 0):
            return {
                'state': 'empty',
                'lead': {
                    'severity': 'info',
                    'icon': 'fa-plug',
                    'text': _("Store setup is incomplete"),
                    'hint': _("Connect your store to begin syncing."),
                },
            }

        if danger_active == 0 and warning_active == 0:
            return {
                'state': 'healthy',
                'lead': {
                    'severity': 'success',
                    'icon': 'fa-check-circle',
                    'text': _("All systems normal"),
                    'hint': _("Everything that ran recently succeeded."),
                },
            }

        if danger_active > 0 and technical_fail == 0 and reconnect == 0:
            # All active danger is a human decision, no technical failure.
            return {
                'state': 'manual_review',
                'lead': {
                    'severity': 'danger',
                    'icon': 'fa-hand-paper-o',
                    'text': _("%s waiting on a decision", self._count_phrase(manual_review)),
                    'hint': _("These are decisions for a reviewer — not a system failure."),
                },
            }

        if danger_active > 0:
            total_attention = danger_active + warning_active
            return {
                'state': 'degraded',
                'lead': {
                    'severity': 'danger',
                    'icon': 'fa-exclamation-triangle',
                    'text': _("%s need your attention", self._count_phrase(total_attention)),
                    'hint': _("Review the items below to get things moving again."),
                },
            }

        # Warning-only: nothing failed, but work is retrying / a store needs a
        # reconnect / the API is throttled. Not green, not red.
        return {
            'state': 'warning',
            'lead': {
                'severity': 'warning',
                'icon': 'fa-clock-o',
                'text': _("%s need your attention", self._count_phrase(warning_active)),
                'hint': _("Nothing has failed — these are working through on their own or need a quick check."),
            },
        }

    # ------------------------------------------------------------------ #
    #  Exceptions (at most three, ranked danger-first)
    # ------------------------------------------------------------------ #
    def _build_exceptions(self, stores, jobs, attempts_uncertain):
        """Return at most three active exceptions, most-severe first.

        Each carries a plain-language title, a count, why it matters, the
        owning role, and a ``target`` (res_model + a static domain + name) the
        client turns into a native filtered list. The count always equals the
        number of records matching ``target.domain`` -- asserted by
        test_ui_dashboard.py so the number the operator sees and the list they
        land on can never disagree.
        """
        candidates = [
            {
                'id': 'blocked_manual_review',
                'severity': 'danger',
                'icon': 'fa-hand-paper-o',
                'title': _("Runs waiting on a review decision"),
                'count': jobs['blocked_manual_review'],
                'why': _("A reviewer needs to decide how these proceed."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'blocked_manual_review')],
                    'name': _("Runs waiting on a review decision"),
                },
            },
            {
                'id': 'uncertain_mutation',
                'severity': 'danger',
                'icon': 'fa-hand-paper-o',
                'title': _("Changes waiting on an administrator decision"),
                'count': attempts_uncertain,
                'why': _("An outcome could not be confirmed and needs an administrator judgement."),
                'owner': _("Administrator"),
                'target': {
                    'res_model': 'shopify.connector.mutation.attempt',
                    'domain': [('observed_outcome', '=', 'uncertain'), ('resolution_disposition', '=', False)],
                    'name': _("Changes waiting on a decision"),
                },
            },
            {
                'id': 'failed_final',
                'severity': 'danger',
                'icon': 'fa-exclamation-triangle',
                'title': _("Runs that stopped after repeated failures"),
                'count': jobs['failed_final'],
                'why': _("These stopped retrying — review the reason to get them moving again."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'failed_final')],
                    'name': _("Runs that stopped after repeated failures"),
                },
            },
            {
                'id': 'failed_retryable',
                'severity': 'danger',
                'icon': 'fa-exclamation-triangle',
                'title': _("Runs that need a fix before retrying"),
                'count': jobs['failed_retryable'],
                'why': _("These are paused for a manual fix, then a retry."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'failed_retryable')],
                    'name': _("Runs that need a fix before retrying"),
                },
            },
            {
                'id': 'reconnect_needed',
                'severity': 'warning',
                'icon': 'fa-plug',
                'title': _("Stores that need reconnecting"),
                'count': stores['reconnect_needed'],
                'why': _("Shopify no longer accepts the saved credentials — reconnect to resume."),
                'owner': _("Administrator"),
                'target': {
                    'res_model': 'shopify.connector.store',
                    'domain': [('state', '=', 'reconnect_needed')],
                    'name': _("Stores that need reconnecting"),
                },
            },
        ]
        active = [c for c in candidates if c['count'] > 0]
        # Domains are serialised as lists-of-lists so they survive JSON to the
        # browser and back into an act_window domain.
        for c in active:
            c['target']['domain'] = [list(term) for term in c['target']['domain']]
        return active[:self.MAX_EXCEPTIONS]

    # ------------------------------------------------------------------ #
    #  Secondary metric chips (quiet; loud only when non-zero + non-nominal)
    # ------------------------------------------------------------------ #
    def _build_chips(self, stores, jobs, attempts_uncertain):
        def chip(cid, label, value, tone='neutral', loud=False):
            return {'id': cid, 'label': label, 'value': value, 'tone': tone, 'loud': bool(loud)}

        connected_label = _("%(connected)s of %(total)s connected", connected=stores['connected'], total=stores['total'])
        return [
            chip('stores', _("Stores"), connected_label,
                 tone='success' if stores['total'] and stores['connected'] == stores['total'] else 'neutral',
                 loud=bool(stores['reconnect_needed'] or stores['disconnected'])),
            chip('queued', _("Queued"), jobs['queued'], tone='info', loud=False),
            chip('running', _("Running"), jobs['running'], tone='info', loud=False),
            chip('retry_waiting', _("Waiting to retry"), jobs['retry_waiting'],
                 tone='warning', loud=bool(jobs['retry_waiting'])),
            chip('needs_review', _("To review"), jobs['blocked_manual_review'] + attempts_uncertain,
                 tone='danger', loud=bool(jobs['blocked_manual_review'] + attempts_uncertain)),
        ]

    # ------------------------------------------------------------------ #
    #  Recent activity (single bounded, safe-field read)
    # ------------------------------------------------------------------ #
    def _recent_activity(self):
        """The N most recent finished jobs, safe fields only.

        One ``search_read`` with an explicit ``limit`` -- never the full table.
        Only enum/label/timestamp/reference fields are read; no message,
        payload, technical detail, credential or PII field is touched.
        """
        rows = self.env['shopify.connector.job'].search_read(
            domain=[('state', 'in', list(self._TERMINAL_JOB_STATES))],
            fields=['state', 'job_type', 'job_source', 'store_id', 'finished_at'],
            limit=self.RECENT_ACTIVITY_LIMIT,
            order='finished_at desc, id desc',
        )
        now = fields.Datetime.now()
        activity = []
        for row in rows:
            finished = row.get('finished_at')
            activity.append({
                'id': row['id'],
                'state': row['state'],
                'state_label': self._job_state_label(row['state']),
                'tone': self._job_state_tone(row['state']),
                'job_label': self._job_type_label(row['job_type']),
                'source_label': self._job_source_label(row['job_source']),
                'store': (row['store_id'] or [0, ''])[1] if row.get('store_id') else '',
                'relative': self._relative_time(finished, now),
            })
        return activity

    # ------------------------------------------------------------------ #
    #  Optional 7-day sparkline (severable; only when enough history)
    # ------------------------------------------------------------------ #
    def _sparkline(self):
        Job = self.env['shopify.connector.job']
        now = fields.Datetime.now()
        window_start = now - timedelta(days=self.SPARKLINE_DAYS)

        # Only render when there is at least SPARKLINE_DAYS of history: the
        # oldest terminal job must be older than the window.
        oldest = Job.search(
            [('finished_at', '!=', False)], order='finished_at asc', limit=1,
        )
        if not oldest or not oldest.finished_at or oldest.finished_at > window_start:
            return {'available': False, 'days': [], 'summary': ''}

        days = []
        total_success = 0
        total_failure = 0
        for offset in range(self.SPARKLINE_DAYS - 1, -1, -1):
            day_start = (now - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            base = [('finished_at', '>=', fields.Datetime.to_string(day_start)),
                    ('finished_at', '<', fields.Datetime.to_string(day_end))]
            success = Job.search_count(base + [('state', '=', 'succeeded')])
            failure = Job.search_count(base + [('state', 'in', ('failed_final', 'failed_retryable'))])
            total_success += success
            total_failure += failure
            days.append({
                'label': day_start.strftime('%a'),
                'date': day_start.strftime('%Y-%m-%d'),
                'success': success,
                'failure': failure,
            })
        summary = _("Last 7 days: %(ok)s succeeded, %(bad)s failed.", ok=total_success, bad=total_failure)
        return {'available': True, 'days': days, 'summary': summary}

    # ------------------------------------------------------------------ #
    #  Label helpers -- plain language only, never a raw internal token
    # ------------------------------------------------------------------ #
    def _job_state_label(self, state):
        return {
            'draft': _("Draft"),
            'queued': _("Queued"),
            'running': _("Running"),
            'succeeded': _("Done"),
            'failed_final': _("Failed"),
            'failed_retryable': _("Needs a fix"),
            'skipped': _("Skipped"),
            'cancelled': _("Cancelled"),
            'retry_waiting': _("Waiting to retry"),
            'blocked_manual_review': _("Waiting on a decision"),
        }.get(state, _("Unknown"))

    def _job_state_tone(self, state):
        return {
            'succeeded': 'success',
            'failed_final': 'danger',
            'failed_retryable': 'danger',
            'blocked_manual_review': 'danger',
            'retry_waiting': 'warning',
            'queued': 'info',
            'running': 'info',
            'skipped': 'neutral',
            'cancelled': 'neutral',
            'draft': 'neutral',
        }.get(state, 'neutral')

    def _job_type_label(self, job_type):
        return {
            'core_readiness_check': _("Readiness check"),
            'core_manual_maintenance': _("Maintenance"),
            'core_test_connection': _("Connection test"),
            'historic_domain_job': _("Sync run"),
            'core_dispatch_selftest': _("Dispatch self-test"),
            'mutation_dispatch_selftest': _("Change self-test"),
            'mutation_dispatch_selftest_reconcile': _("Change reconciliation"),
        }.get(job_type, _("Sync run"))

    def _job_source_label(self, job_source):
        return {
            'webhook': _("Webhook"),
            'manual_sync': _("Manual sync"),
            'scheduled_sync': _("Scheduled sync"),
            'reconciliation': _("Reconciliation"),
            'setup_readiness_check': _("Readiness check"),
            'export_preview_dry_run': _("Preview"),
            'odoo_event': _("Odoo event"),
        }.get(job_source, _("Activity"))

    def _count_phrase(self, n):
        if n == 1:
            return _("1 item")
        return _("%s items", n)

    def _relative_time(self, when, now):
        if not when:
            return _("just now")
        delta = now - when
        seconds = int(delta.total_seconds())
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return _("just now")
        minutes = seconds // 60
        if minutes < 60:
            return _("%s min ago", minutes)
        hours = minutes // 60
        if hours < 24:
            return _("%s h ago", hours)
        days = hours // 24
        if days < 7:
            return _("%s d ago", days)
        weeks = days // 7
        return _("%s w ago", weeks)

    def _cadence_line(self, activity):
        if activity and activity[0].get('relative'):
            return _("Automatic checks run on a schedule — last activity %s.", activity[0]['relative'])
        return _("Automatic checks run on a schedule.")
