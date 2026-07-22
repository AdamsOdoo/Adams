# Part of the Shopify Connector (U0 operator UI foundation).
#
# Read-only operator dashboard aggregate service.
#
# This is the ONE bounded, read-only aggregate service that backs the U0
# operational dashboard Owl client action (see
# static/src/js/shopify_connector_dashboard.js). It is deliberately an
# ``AbstractModel`` -- it owns no table, no ACL row, and no persistent state.
# It exposes exactly one public RPC entrypoint, :meth:`get_dashboard_data`,
# which returns a single JSON-serialisable dict describing the current
# operator situation.
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

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


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
            'refresh_interval_seconds': 30,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
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
                'title': _("Jobs waiting on a review decision"),
                'count': jobs['blocked_manual_review'],
                'why': _("A reviewer needs to decide how these proceed."),
                'owner': _("Reviewer"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'blocked_manual_review')],
                    'name': _("Jobs waiting on a review decision"),
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
                'title': _("Jobs that stopped after repeated failures"),
                'count': jobs['failed_final'],
                'why': _("These stopped retrying — review the reason to get them moving again."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'failed_final')],
                    'name': _("Jobs that stopped after repeated failures"),
                },
            },
            {
                'id': 'failed_retryable',
                'severity': 'danger',
                'icon': 'fa-exclamation-triangle',
                'title': _("Jobs that need a fix before retrying"),
                'count': jobs['failed_retryable'],
                'why': _("These are paused for a manual fix, then a retry."),
                'owner': _("Operator"),
                'target': {
                    'res_model': 'shopify.connector.job',
                    'domain': [('state', '=', 'failed_retryable')],
                    'name': _("Jobs that need a fix before retrying"),
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
            'historic_domain_job': _("Sync job"),
            'core_dispatch_selftest': _("Dispatch self-test"),
            'mutation_dispatch_selftest': _("Change self-test"),
            'mutation_dispatch_selftest_reconcile': _("Change reconciliation"),
        }.get(job_type, _("Sync job"))

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
