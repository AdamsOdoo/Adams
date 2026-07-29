import json
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..tools.redaction import redact
from ..tools.api_version import SHOPIFY_API_VERSION
from .shopify_connector_api_client import (
    ERROR_AUTH,
    LIFECYCLE_PURPOSE_STATES,
    ShopifyClientError,
)
from .shopify_connector_job import BUSINESS_JOB_SOURCES
from .shopify_connector_job_dispatch import (
    DISCONNECT_QUIESCE_TIMEOUT,
    POLL_DELAY,
)

_logger = logging.getLogger(__name__)

# TD-014 (PERF-1 / D-PERF1-4). Head-room thresholds as a fraction of the
# store's own `maximumAvailable`, so they hold for any plan size rather
# than encoding a bucket the connector does not control (MBQ-51 stays
# untouched: no bucket size is hard-coded anywhere).
#
# Two thresholds rather than one, deliberately: with a single line the
# state flaps across it, rewriting the store row and changing the next
# pass's candidate set on every call. The gap is the hysteresis that lets
# the bucket actually refill before work resumes.
THROTTLE_DEFER_RATIO = 0.2
THROTTLE_RECOVER_RATIO = 0.5

# CORE-R2 Slice 2A: the disconnect controller's `timed_out` escalation snapshot
# records at most this many outstanding holders (opaque lease_key + Integer
# job_id only -- never a token/credential/payload) into the audited
# `disconnect_status_reason`, keeping the operator-facing escalation bounded
# (analysis §16). Named, not an inlined magic number.
_ESCALATION_SNAPSHOT_LIMIT = 20

# The controller cron xml-id (`data/shopify_connector_cron_disconnect.xml`),
# resolved when Phase 1 wakes the controller and when a still-quiescing store
# schedules its delayed re-poll.
_DISCONNECT_CRON_XMLID = (
    'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce'
)

# The read-only test-connection query (Task 003) -- confirmed in the
# 2026-07 official reference (Facts #7/#8,
# credential-connection-api-client-planning.md); no mutation, no
# variables needed.
TEST_CONNECTION_QUERY = """
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
"""


class ShopifyConnectorStore(models.Model):
    """The DEC-006 store-scoping anchor every other core model references.

    Holds connection lifecycle, API version/health, and readiness
    metadata, plus non-secret credential status mirrors only. This
    model stores no secret value itself: the credential presence flag,
    replacement/verification timestamps, failure reason, and
    granted-scope snapshot below are all non-secret status mirrors,
    written only by the credential service (Task 002). The actual
    secret credential value is persisted exclusively on the dedicated
    Admin-only `shopify.connector.store.credential` model.
    """

    _name = 'shopify.connector.store'
    _description = 'Shopify Connector Store'

    name = fields.Char(required=True)
    shop_domain = fields.Char(required=True, index=True, readonly=True)
    state = fields.Selection(
        selection=[
            ('setup_incomplete', 'Setup Incomplete'),
            ('connected', 'Connected'),
            ('reconnect_needed', 'Reconnect Needed'),
            # CORE-R2 (AR-047): the two-phase disconnect intermediate state. A
            # store enters `disconnecting` at Phase-1 `action_disconnect` and is
            # finalized to `disconnected` by the quiescence controller once its
            # committed admission-lease count reaches zero (`completed`) or the
            # bounded timeout fires (`timed_out`). Non-startable and
            # non-enqueueable for business jobs, and lifecycle-mutation-refusing,
            # exactly like the never-connected states (analysis §8/§13).
            ('disconnecting', 'Disconnecting'),
            ('disconnected', 'Disconnected'),
        ],
        required=True,
        index=True,
        default='setup_incomplete',
        readonly=True,
    )
    # TD-008. The value is still stored -- the column is not removed and no
    # schema migration is performed -- but it is no longer a value anyone
    # may CHOOSE. `SHOPIFY_API_VERSION` remains the single authority: the
    # endpoint is built from the constant, never from this column, and
    # `_check_api_version_is_the_connector_constant` below refuses any row
    # that disagrees with it.
    #
    # The default is what makes ordinary store creation correct without
    # anybody passing anything, and the constraint is what makes the
    # RPC/import/superuser paths safe -- the form was already
    # `readonly="1"`, which is a client-side courtesy and not a boundary.
    api_version = fields.Char(
        required=True,
        default=lambda self: SHOPIFY_API_VERSION,
    )
    api_health_state = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('throttled', 'Throttled'),
            ('degraded', 'Degraded'),
        ],
        readonly=True,
    )
    api_health_reason = fields.Char(readonly=True)
    # TD-014 (PERF-1, D-PERF1-4). The minimum safe numeric state from
    # Shopify's own `extensions.cost.throttleStatus`, which
    # `_parse_throttle_status` has extracted from every response since
    # PERF-1 shipped and which nothing consumed. Three numbers and a
    # timestamp: no request payload, no header, no credential, nothing
    # that could carry merchant data.
    #
    # Official reference: https://shopify.dev/docs/api/usage/limits
    # (read 2026-07-27). The bucket refills continuously at
    # `restoreRate` points per second up to `maximumAvailable`, which is
    # what lets `_projected_throttle_available` below recompute head-room
    # without issuing a call -- and that, in turn, is what stops a
    # deferred store from starving.
    api_throttle_available = fields.Float(readonly=True)
    api_throttle_maximum = fields.Float(readonly=True)
    api_throttle_restore_rate = fields.Float(readonly=True)
    api_throttle_observed_at = fields.Datetime(readonly=True)
    webhook_ready = fields.Boolean(default=False, readonly=True)
    last_test_connection_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail')],
        readonly=True,
    )
    last_test_connection_at = fields.Datetime(readonly=True)
    last_test_connection_reason = fields.Char(readonly=True)
    last_readiness_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail'), ('warning', 'Warning')],
        readonly=True,
    )
    last_readiness_at = fields.Datetime(readonly=True)
    credential_present = fields.Boolean(default=False, readonly=True)
    credential_last_verified_at = fields.Datetime(readonly=True)
    credential_last_replaced_at = fields.Datetime(readonly=True)
    credential_last_failure_reason = fields.Char(readonly=True)
    granted_scopes = fields.Text(readonly=True)
    granted_scopes_checked_at = fields.Datetime(readonly=True)
    # CORE-R2 (AR-047) persisted connection epoch. Monotonic per store; a
    # business job captures it at enqueue (`expected_connection_generation`) and
    # `execute_business` admission refuses any call whose captured epoch no longer
    # matches this value. Additive and inert in this foundation slice: it is read
    # by admission and captured at enqueue, but NO lifecycle transition bumps it
    # yet and NO state change is introduced here — the disconnect/reconnect
    # generation-bump protocol is a later CORE-R2 slice. Existing rows backfill to
    # 0 (matching a never-cycled store, analysis §22).
    connection_generation = fields.Integer(
        default=0,
        required=True,
        readonly=True,
    )
    # CORE-R2 (AR-047; analysis §11) two-phase disconnect status + escalation
    # snapshot fields. All additive and non-secret. `disconnect_status` is the
    # controller-observable lifecycle sub-state; the `*_lease_count` /
    # `*_oldest_admitted_at` pair is the escalation snapshot the controller
    # writes each pass; the `*_requested_at`/`*_by` pair records the Phase-1
    # request; `*_completed_at` stamps the `completed`/`timed_out` finalize.
    # Existing rows backfill to `disconnect_status='none'` (a never-disconnected
    # store) and the rest empty/zero.
    disconnect_status = fields.Selection(
        selection=[
            ('none', 'None'),
            ('requested', 'Requested'),
            ('quiescing', 'Quiescing'),
            ('completed', 'Completed'),
            ('timed_out', 'Timed Out'),
        ],
        default='none',
        required=True,
        readonly=True,
    )
    disconnect_status_reason = fields.Char(readonly=True)
    disconnect_open_lease_count = fields.Integer(default=0, readonly=True)
    disconnect_oldest_admitted_at = fields.Datetime(readonly=True)
    disconnect_requested_at = fields.Datetime(readonly=True)
    disconnect_requested_by = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='set null',
    )
    disconnect_completed_at = fields.Datetime(readonly=True)

    # SEC-3 (#197) ownership root. Every durable connector record derives its
    # company from the store it belongs to, so this one field is the single
    # place company ownership is decided for the whole connector.
    #
    # MVP ownership contract (control-room decision, 2026-07-25):
    #   * a store belongs to exactly ONE company;
    #   * a company may own many stores;
    #   * sharing one store across companies is OUT of the MVP and must not
    #     become possible by accident -- hence Many2one, not Many2many.
    #
    # Deliberately NOT `required=True`. A required field would make the warm
    # `-u` update of a database that already holds stores fail outright, and
    # Odoo would silently leave the column nullable anyway. Ownership is
    # instead enforced at two places that cannot be bypassed by an upgrade:
    # `_check_company_assigned` below (create-time) and the fail-closed record
    # rule in `security/shopify_connector_company_rules.xml` (read-time). An
    # un-backfilled historic store is therefore invisible to every interactive
    # user rather than visible to the wrong one.
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        index=True,
        ondelete='restrict',
        default=lambda self: self.env.company,
        help='The Odoo company that owns this Shopify store. Every job, '
             'credential, binding and log derived from this store inherits '
             'this company.',
    )

    _shop_domain_uniq = models.Constraint(
        'UNIQUE(shop_domain)',
        'A store already exists for this Shopify shop domain.',
    )

    @api.constrains('api_version')
    def _check_api_version_is_the_connector_constant(self):
        """TD-008: the stored version may only ever be the constant.

        `api_version` was a plain writable `Char`. The form marked it
        `readonly="1"`, which stops a person typing in it and stops nothing
        else: an RPC call, a data import, a server action or any `sudo()`
        write could set it to anything, and the field would then sit on
        the store looking authoritative while every request went to the
        version in `SHOPIFY_API_VERSION` regardless. The stored value
        could not change WHERE requests went -- it could only lie about
        it, which is worse than a value that does nothing.

        `@api.constrains` is the right guard here rather than a
        `models.Constraint`, because the acceptable value is a Python
        constant rather than a database-expressible one, and because it
        fires on every ORM path including `sudo()`, `load()` and RPC --
        the three the readonly attribute does not cover.

        Existing rows that already hold the constant are unaffected: they
        satisfy this. A row that does not is a genuine configuration
        defect and is refused rather than silently tolerated.
        """
        for store in self:
            if store.api_version and store.api_version != SHOPIFY_API_VERSION:
                raise ValidationError(
                    'This connector speaks Shopify Admin API %s, and that '
                    'version is a verified property of its code -- every '
                    'query and mutation in it was checked field-by-field '
                    'against that schema. It cannot be reconfigured per '
                    'store, so %r was refused. Requests are sent to %s '
                    'whatever this field says; a store row claiming a '
                    'different version would only misreport where they '
                    'go.' % (
                        SHOPIFY_API_VERSION, store.api_version,
                        SHOPIFY_API_VERSION,
                    )
                )

    @api.constrains('company_id')
    def _check_company_assigned(self):
        """Refuse a store with no owning company.

        Fires on create and on any write that clears `company_id`, so a new
        store can never be created unowned and an owned store can never be
        un-owned. It deliberately does NOT fire when other fields are written,
        which is what lets an administrator keep operating on a historic
        un-backfilled store long enough to assign it (see `_backfill_company`).

        `@api.constrains` also fires under `sudo()`, so this is a genuine
        write-side guard and not merely a UI convenience.
        """
        for store in self:
            if not store.company_id:
                raise ValidationError(
                    'A Shopify store must belong to a company. Assign the '
                    'owning company before saving this store.'
                )

    # ------------------------------------------------------------------
    # TD-014 (PERF-1 / D-PERF1-4): backpressure from real throttle data
    # ------------------------------------------------------------------

    def _record_throttle_status(self, throttle_status):
        """Fold one response's `throttleStatus` into this store's health.

        Called from the single client choke point, so every Shopify
        response this connector receives contributes -- reads and
        mutations alike, for every domain.

        **Fail-safe on absent or malformed data.** Shopify omits
        `extensions.cost` on some responses, and a partial or
        non-numeric payload must never be read as "no head-room". When
        the three values are not all usable numbers this returns without
        touching anything, so throughput is preserved exactly as it was
        before TD-014. Backpressure is only ever applied on evidence.

        **Only ever defers work.** Nothing here raises a rate, shortens
        a delay, or admits anything: the strongest effect available is
        setting `api_health_state` to `throttled`, which the existing
        `_backpressured_store_ids` lever already drops from the claim
        candidate search for the rest of a pass.

        **Isolated per store.** State lives on the store row, so one
        merchant's exhausted bucket cannot defer another's work.
        """
        self.ensure_one()
        values = self._normalized_throttle_values(throttle_status)
        if not values:
            return False
        available, maximum, restore_rate = values
        self.sudo().write({
            'api_throttle_available': available,
            'api_throttle_maximum': maximum,
            'api_throttle_restore_rate': restore_rate,
            'api_throttle_observed_at': fields.Datetime.now(),
        })
        self.invalidate_recordset()
        return self._apply_throttle_backpressure()

    @api.model
    def _normalized_throttle_values(self, throttle_status):
        """`(available, maximum, restore_rate)`, or False if unusable.

        `maximumAvailable` must be positive because it is the divisor for
        head-room; a zero or absent bucket size makes the ratio undefined
        and is treated as no evidence rather than as zero head-room.
        """
        if not isinstance(throttle_status, dict):
            return False
        try:
            available = float(throttle_status.get('currentlyAvailable'))
            maximum = float(throttle_status.get('maximumAvailable'))
            restore_rate = float(throttle_status.get('restoreRate') or 0.0)
        except (TypeError, ValueError):
            return False
        if maximum <= 0 or available < 0 or restore_rate < 0:
            return False
        return min(available, maximum), maximum, restore_rate

    def _projected_throttle_available(self, now=None):
        """Head-room now, projecting the documented continuous refill.

        This is what prevents the starvation the naive design has. A
        store deferred for low head-room issues no calls, so it receives
        no new `throttleStatus`, so a purely observation-driven state
        could never recover -- the store would be deferred forever on the
        strength of one bad moment.

        Shopify's bucket refills continuously at `restoreRate` points per
        second up to `maximumAvailable`, so the head-room a store would
        have *right now* is arithmetic on the last observation and the
        clock. No Shopify call, fully deterministic, and testable by
        passing `now`.
        """
        self.ensure_one()
        if not self.api_throttle_maximum or not self.api_throttle_observed_at:
            return None
        now = now or fields.Datetime.now()
        elapsed = (now - self.api_throttle_observed_at).total_seconds()
        if elapsed < 0:
            elapsed = 0.0
        return min(
            self.api_throttle_maximum,
            self.api_throttle_available
            + (self.api_throttle_restore_rate * elapsed),
        )

    def _throttle_headroom_ratio(self, now=None):
        """Projected head-room as a fraction of the bucket, or None."""
        self.ensure_one()
        projected = self._projected_throttle_available(now=now)
        if projected is None or not self.api_throttle_maximum:
            return None
        return projected / self.api_throttle_maximum

    def _apply_throttle_backpressure(self, now=None):
        """Move `api_health_state` between `normal` and `throttled`.

        Two thresholds, not one, on purpose. A single threshold makes the
        state flap around it: every call that nudged head-room across the
        line would rewrite the store row and change the next pass's
        candidate set. Deferring below `THROTTLE_DEFER_RATIO` and only
        recovering above the higher `THROTTLE_RECOVER_RATIO` gives the
        bucket room to actually refill before work resumes.

        `degraded` is left alone entirely. It means something else --
        the store lifecycle sets it for API health problems that are not
        rate pressure -- and this must not clear a degradation it did not
        cause.
        """
        self.ensure_one()
        ratio = self._throttle_headroom_ratio(now=now)
        if ratio is None:
            return False
        if ratio < THROTTLE_DEFER_RATIO:
            if self.api_health_state != 'throttled':
                self.sudo().write({
                    'api_health_state': 'throttled',
                    'api_health_reason': (
                        'Shopify API head-room is %.0f%% of this store\'s '
                        'bucket; new work is deferred until it recovers.'
                        % (ratio * 100)
                    ),
                })
                _logger.info(
                    'Store %d deferred on Shopify rate head-room %.2f.',
                    self.id, ratio,
                )
            return True
        if (
            self.api_health_state == 'throttled'
            and ratio >= THROTTLE_RECOVER_RATIO
        ):
            self.sudo().write({
                'api_health_state': 'normal',
                'api_health_reason': False,
            })
            _logger.info(
                'Store %d resumed on Shopify rate head-room %.2f.',
                self.id, ratio,
            )
        return False

    @api.model
    def _recover_throttled_stores(self, now=None):
        """Re-evaluate every rate-deferred store against the clock.

        The other half of the anti-starvation guarantee. A store deferred
        by `_apply_throttle_backpressure` makes no calls, so nothing
        would re-evaluate it from the response path. This runs at the
        start of each drain pass and lets the projected refill lift the
        deferral on its own, with no Shopify contact of any kind.
        """
        recovered = self.sudo().search([
            ('api_health_state', '=', 'throttled'),
            ('api_throttle_observed_at', '!=', False),
        ])
        for store in recovered:
            store._apply_throttle_backpressure(now=now)
        return recovered

    @api.model
    def _backfill_company(self):
        """Deterministically assign a company to historic stores, or fail closed.

        Called from `init()` on every install/update. Two rules, both of which
        require the answer to be *provable* from the database:

        1. If the database has exactly one company, that company is the only
           possible owner, so assign it.
        2. Otherwise ownership is ambiguous. Do NOT guess. The store keeps a
           NULL company and the fail-closed record rule makes it invisible to
           every interactive user until an administrator assigns it through
           `action_assign_company` (the durable remediation path).

        A downstream module may supply further *provable* evidence for rule 2
        -- `shopify_connector_sale` backfills from a store's already-configured
        `order_company_id` -- but no module may guess.
        """
        self.env.cr.execute(
            'SELECT id FROM shopify_connector_store WHERE company_id IS NULL'
        )
        unassigned = [row[0] for row in self.env.cr.fetchall()]
        if not unassigned:
            return
        companies = self.env['res.company'].sudo().search([])
        if len(companies) == 1:
            self.env.cr.execute(
                'UPDATE shopify_connector_store SET company_id = %s '
                'WHERE company_id IS NULL',
                (companies.id,),
            )
            _logger.info(
                'SEC-3: assigned the single company %s to %d historic '
                'Shopify store(s).', companies.display_name, len(unassigned),
            )
            return
        _logger.warning(
            'SEC-3: %d Shopify store(s) have no owning company and ownership '
            'is not provable in a %d-company database. They are HIDDEN from '
            'every interactive user until an administrator assigns a company '
            '(Settings > Technical > Shopify > unassigned stores). Store ids: '
            '%s', len(unassigned), len(companies), unassigned,
        )

    def init(self):
        """Run the ownership backfill on every install and update."""
        super().init()
        self._backfill_company()

    def action_assign_company(self, company):
        """Administrative remediation path for an un-backfilled historic store.

        The fail-closed record rule hides a company-less store from ordinary
        reads, which is the point -- but it must still be *fixable*. This
        method is the sanctioned way: it is Administrator-gated, it resolves
        the store by explicit id under `sudo()` (the row is invisible to a
        normal read by construction), and it refuses to move a store that
        already has an owner, so it can never be used to re-home a live store
        into another company.
        """
        self._ensure_connector_admin_boundary()
        company = self.env['res.company'].browse(int(company))
        if not company.exists():
            raise UserError('The company to assign does not exist.')
        if company not in self.env.user.company_ids:
            raise AccessError(
                'You may only assign a Shopify store to a company you belong '
                'to.'
            )
        for store in self.sudo():
            if store.company_id:
                raise UserError(
                    'This Shopify store already belongs to %s. Re-homing a '
                    'store to another company is not supported.'
                    % (store.company_id.display_name,)
                )
            store.company_id = company

    def _ensure_connector_admin_boundary(self):
        """Refuse a non-Administrator caller at a public action boundary
        BEFORE any side effect (Stage R1 SEC; sibling of the guard already in
        ``action_force_disconnect``).

        ``action_test_connection``, ``action_activate``, ``action_disconnect``
        and ``action_reconnect`` funnel privileged work -- audit ``Job`` /
        ``job.log`` creation, the one sanctioned credential-token ``sudo()``
        read, the Shopify transport call, and the store-row lifecycle
        lock/write -- through ``_run_connection_probe`` /
        ``_create_lifecycle_audit_job``, several sites via ``sudo()``. The store
        write ACL is Administrator-only, but it only bites at the LATE non-sudo
        mirror write, so an unauthorized direct-RPC caller (Auditor / Operator /
        Reviewer, who all hold store *read*) could otherwise reach the Shopify
        transport, materialise the credential, and create audit rows before
        being denied. Enforcing the existing
        ``group_shopify_connector_admin`` here -- no new role or group -- closes
        that gap so denial happens before every side effect. The framework
        superuser (``env.su``: crons, the disconnect controller, and the test
        harness) is exempt exactly as elsewhere in Odoo; a real RPC caller can
        never be ``su``.
        """
        if not self.env.su and not self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'):
            raise AccessError(
                'Only a Shopify Connector Administrator may run connection '
                'and lifecycle actions on a store.'
            )

    def action_test_connection(self):
        """Run one read-only Shopify test-connection check (Task 003).

        Admin-invoked (store write access is Admin-only per the merged
        ACL, so this is enforced by the existing ACL, not a new guard).
        Thin public wrapper over the shared `_run_connection_probe` with the
        INTERNAL purpose `'test_connection'` -- never a caller/RPC-controlled
        purpose. The frozen matrix refuses it while the store is `disconnecting`
        **or** `disconnected` (analysis §8/§9.1); `reconnect_probe` is the sibling
        purpose used by `action_reconnect` for the finalized `disconnected` state.
        """
        self.ensure_one()
        # SEC (Stage R1): enforce the Administrator boundary BEFORE
        # `_run_connection_probe` creates any job/log, reads the credential, or
        # reaches the Shopify transport (the known direct-RPC P1).
        self._ensure_connector_admin_boundary()
        # `_run_connection_probe` returns `'superseded'` when a concurrent
        # lifecycle/credential change discarded the result; Test Connection has no
        # further step, so return None (the accepted RPC contract) either way.
        self._run_connection_probe('test_connection')
        return None

    def _run_connection_probe(self, purpose):
        """Shared read-only connection probe (Task 003 + CORE-R2; reviews
        4690639375 #2 + 4690804619 #1).

        The single implementation behind `action_test_connection`
        (`purpose='test_connection'`) and `action_reconnect`
        (`purpose='reconnect_probe'`). `purpose` is a fixed INTERNAL enum chosen
        by those two trusted callers -- it is **not** a caller/RPC-controlled
        value. Identical transport, normalization, mirror, and audit behavior for
        both purposes; only the allowed-state matrix differs
        (`LIFECYCLE_PURPOSE_STATES`): `test_connection` excludes `disconnected`,
        `reconnect_probe` permits it (reconnect after completed disconnect,
        matrix §8), and neither permits `disconnecting`.

        **One atomic credential snapshot per probe (reviews 4690804619 #1 +
        4691182306 #1).** The probe binds to exactly one credential snapshot via
        `_admit_lifecycle`, which captures it in a **short independent side
        transaction** whose store-row ``FOR SHARE`` linearizes the probe against
        any concurrent generation-changing lifecycle transition and is
        **committed/released before** the network call (no lease, no lock across
        the network). It then issues the request through
        `_send_lifecycle(store, query, token)` with that exact token -- the
        transport re-reads **no** credential. A disconnect that wins **before** the
        admission ``FOR SHARE`` is refused under the lock (no network issued); a
        disconnect that wins **after** is caught by the post-network revalidation:
        `_lifecycle_probe_superseded` acquires the store->credential locks and
        revalidates state, generation, and credential version/value; if a lifecycle
        or credential change won the response is **discarded** and the probe is
        audited as **superseded** (job cancelled, **no** verification/failure mirror
        and **no** credential state written). No lock spans the network call.
        Returns `'superseded'` in either case (so `action_reconnect` aborts),
        else `None`.

        The matrix is pre-checked here **before** any audit job is created (so a
        refused probe never leaves a dangling `running` job) and re-enforced in
        `_admit_lifecycle` as defense in depth. Creates exactly one
        `job_type='core_test_connection'` job per run with a fresh UUID4
        `payload_hash` nonce; writes only the store mirrors, the credential's
        `credential_state` (only for a genuine token-invalid signal), and the
        job/job.log rows -- never the token.
        """
        self.ensure_one()
        allowed_states = LIFECYCLE_PURPOSE_STATES.get(purpose)
        if allowed_states is None:
            raise UserError(
                'An unknown connection-probe purpose was requested.'
            )
        if self.state not in allowed_states:
            raise UserError(
                'A connection check is not available while the store is '
                '"%s".' % self.state
            )
        if not self.credential_present:
            raise UserError(
                'Enter a credential before testing the connection.'
            )
        Client = self.env['shopify.connector.api.client']
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        # Wave 5: a client-credentials store obtains/refreshes its 24-hour token
        # before ANY lock exists -- before the audit job, before
        # `_admit_lifecycle`'s `FOR SHARE`, and therefore certainly before the
        # network call this probe makes. A no-op for the offline mode. A failure
        # here is the accepted `ShopifyClientError` taxonomy and is recorded by
        # the same `_apply_probe_failure` path an unusable credential already
        # took, so Test Connection reports "we could not authenticate" rather
        # than an unhandled error.
        try:
            self.env[
                'shopify.connector.store.credential'
            ]._ensure_access_token(self)
        except ShopifyClientError as exc:
            probe_job = Job.sudo().create({
                'store_id': self.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'core_test_connection',
                'state': 'running',
                'payload_hash': str(uuid.uuid4()),
                'started_at': fields.Datetime.now(),
            })
            self._apply_probe_failure(Job.browse(probe_job.id), exc)
            return None
        job = Job.sudo().create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        job = Job.browse(job.id)
        JobLog._system_append(
            job, 'attempt', 'Test connection attempt started.',
        )

        # CORE-R2 (reviews 4690804619 #1 + 4691182306 #1): bind the probe to ONE
        # credential snapshot captured in an atomic side transaction, and send
        # with exactly that token (no second credential read on the transport).
        # `_admit_lifecycle`'s store-row FOR SHARE linearizes this probe against a
        # concurrent generation-changing lifecycle transition:
        #   * a matrix refusal under the lock (`UserError`) means a disconnect (or
        #     other transition) WON between this probe's pre-check and the
        #     admission FOR SHARE -> the probe is superseded and NO network is
        #     issued (the exact "disconnect wins before _send" hole review
        #     4691182306 #1 named);
        #   * a missing/empty credential at admission (`ShopifyClientError`, e.g. a
        #     raced direct clear) is an auth failure recorded without any network;
        #   * otherwise the request is sent with the snapshot token, and the
        #     result goes through the post-network revalidation below.
        try:
            snapshot = Client._admit_lifecycle(self, purpose)
        except UserError:
            self._audit_probe_superseded(job)
            return 'superseded'
        except ShopifyClientError as exc:
            self._apply_probe_failure(job, exc)
            return None

        try:
            result = Client._send_lifecycle(
                self, TEST_CONNECTION_QUERY, snapshot['token'],
            )
            probe_error = None
        except ShopifyClientError as exc:
            result = None
            probe_error = exc

        # Post-network revalidation: discard a result the snapshot no longer
        # backs (state/generation/credential changed during the call), audit it as
        # superseded, and write NO mirror/credential state. No lock spans the call.
        if self._lifecycle_probe_superseded(snapshot):
            self._audit_probe_superseded(job)
            return 'superseded'

        if probe_error is not None:
            self._apply_probe_failure(job, probe_error)
            return None

        data = result.get('data') or {}
        shop = data.get('shop') or {}
        if shop.get('myshopifyDomain') != self.shop_domain:
            reason = (
                "The connected Shopify store does not match this "
                "store's configured domain — check the domain and "
                "reconnect."
            )
            self.write({
                'last_test_connection_result': 'fail',
                'last_test_connection_at': fields.Datetime.now(),
                'last_test_connection_reason': redact(reason),
            })
            job.sudo().write({
                'error_class': 'odoo_validation_configuration',
                'state': 'failed_final',
                'finished_at': fields.Datetime.now(),
            })
            JobLog._system_append(
                job, 'attempt', redact(reason),
                from_state='running', to_state='failed_final',
            )
            return None

        access_scopes = (
            data.get('currentAppInstallation') or {}
        ).get('accessScopes') or []
        self.write({
            'last_test_connection_result': 'pass',
            'last_test_connection_at': fields.Datetime.now(),
            'last_test_connection_reason': False,
            'credential_last_verified_at': fields.Datetime.now(),
            'granted_scopes': json.dumps(
                [scope['handle'] for scope in access_scopes]
            ),
            'granted_scopes_checked_at': fields.Datetime.now(),
        })
        # D-R1-5 (Task CORE-R1): a fully successful test connection is the
        # healthy API state -- record 'normal' so the unchanged
        # _check_api_version_health readiness check can pass on real
        # evidence, and clear any stale api_health_reason an earlier
        # 'degraded' write left behind, so a recovered store never keeps
        # contradictory operator-facing degradation evidence.
        #
        # There is no longer a fall-forward branch here. Under the
        # 2026-07-26 API-version ruling a served version that differs from
        # the connector constant no longer produces a *successful* result
        # marked degraded: `_normalize_response` fails closed, so control
        # reaches `_apply_probe_failure` with the configuration error class
        # instead of arriving here. Recording "degraded but verified" was
        # the softer disposition this ruling deliberately removes.
        self.write({
            'api_health_state': 'normal',
            'api_health_reason': False,
        })
        job.sudo().write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt',
            'Connection verified with %s.' % shop.get('name'),
            from_state='running', to_state='succeeded',
        )
        return None

    def _apply_probe_failure(self, job, exc):
        """Write the shared probe-failure mirrors + job/log for a
        `ShopifyClientError` (CORE-R2; extracted from `_run_connection_probe`).

        Runs only after the post-network revalidation confirmed the snapshot still
        holds (never from a superseded result). Writes the fail mirrors, flips the
        credential's `credential_state` to `invalid` **only** on a genuine
        token-invalid signal, and -- for any auth/permission/scope class (Task 005 /
        DEC-022 §4.7), not only a token-invalid one -- moves the store to
        `reconnect_needed` via the TOCTOU-safe `action_mark_reconnect_needed`
        (which itself refuses to overwrite a one-way disconnect). Never logs the
        token.
        """
        self.ensure_one()
        JobLog = self.env['shopify.connector.job.log']
        self.write({
            'last_test_connection_result': 'fail',
            'last_test_connection_at': fields.Datetime.now(),
            'last_test_connection_reason': redact(exc.reason),
        })
        if exc.credential_invalid:
            credential = self.env[
                'shopify.connector.store.credential'
            ].search([('store_id', '=', self.id)], limit=1)
            if credential:
                # Wave 5: the non-secret failure hint lives beside the state
                # flip, and is written HERE -- in the caller's own transaction
                # -- rather than by the token-refresh side transaction, whose
                # write to this row would collide with this same request's
                # later revalidation lock under REPEATABLE READ.
                credential.write({
                    'credential_state': 'invalid',
                    'token_last_failure_reason': redact(exc.reason or ''),
                })
        if exc.credential_invalid or exc.error_class == ERROR_AUTH:
            self.action_mark_reconnect_needed(reason=exc.reason)
        job.sudo().write({
            'error_class': exc.error_class,
            'state': 'failed_final',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', redact(exc.reason),
            technical_detail=exc.technical_detail,
            from_state='running', to_state='failed_final',
        )
        return None

    def _lifecycle_probe_superseded(self, snapshot):
        """Return True if a lifecycle/credential change superseded the probe
        (CORE-R2, AR-047; review 4690804619 #1).

        Runs **after** the network result. Acquires the store-row lifecycle lock
        first (`_lock_store_for_lifecycle`, `FOR NO KEY UPDATE`), then the
        credential-row lock (`_lifecycle_credential_version(lock=True)`) -- the
        global `store -> credential` order -- and compares the freshly-locked
        values against the pre-network `snapshot`:

        - the locked state left the `purpose`'s allowed matrix (e.g. a disconnect
          moved it to `disconnecting`);
        - the `connection_generation` changed (an activation/reconnect/disconnect
          or a connected credential replace won the race);
        - the credential row vanished, or its identity/version (`id`,
          `write_date`) changed (a set/replace/clear happened);
        - the credential **value** changed from the snapshot token -- the
          definitive signal for a same-row replace whose `write_date` PostgreSQL
          may fix to the transaction timestamp (so an equal-value or same-txn
          replacement is still caught).

        Any of these means the network response no longer describes the current
        credential/store, so the caller discards it. The lock is taken only here
        (after the network), never across the network call, and -- once acquired --
        is held to the request-boundary commit so the subsequent mirror write is
        TOCTOU-safe. The token compared here is the in-memory snapshot value; it is
        never logged or persisted.
        """
        self.ensure_one()
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state not in snapshot['allowed_states']:
            return True
        if locked_generation != snapshot['generation']:
            return True
        Credential = self.env['shopify.connector.store.credential']
        current = Credential._lifecycle_credential_version(self, lock=True)
        if not current:
            return True
        if current[0] != snapshot['credential_id']:
            return True
        if current[1] != snapshot['credential_version']:
            return True
        # Value revalidation under the held credential-row lock: any set/replace
        # changes the stored value even when its write_date is transaction-fixed.
        #
        # Wave 5: the compared value is the credential IDENTITY, not whatever
        # token happens to be current. Under the offline mode those are the same
        # thing and this is byte-for-byte the previous check. Under the
        # client-credentials mode the access token rotates on a 24-hour schedule
        # that no merchant initiated, so comparing tokens would discard a
        # perfectly valid probe result once a day and report it as a credential
        # change that never happened; the app's own client id and secret are
        # what actually change when a merchant replaces the credential.
        if (
            Credential._lifecycle_credential_identity(self)
            != snapshot.get('identity')
        ):
            return True
        return False

    def _audit_probe_superseded(self, job):
        """Cancel a superseded probe job; write NO store/credential mirror
        (CORE-R2, AR-047; review 4690804619 #1).

        Uses the existing terminal `cancelled` state + `cancel_reason` taxonomy
        (writes to `cancelled` are never store-state-gated) with the required
        empty `manual_review_subreason`, and appends the audit log row. Deliberately
        writes **no** verification/failure mirror and **no** credential state -- the
        whole point of a superseded probe is that its result must not touch the
        store's connection evidence.
        """
        self.ensure_one()
        JobLog = self.env['shopify.connector.job.log']
        reason = (
            'Connection probe superseded by a lifecycle or credential '
            'change; rerun it.'
        )
        job.sudo().write({
            'state': 'cancelled',
            'cancel_reason': reason,
            'finished_at': fields.Datetime.now(),
            'manual_review_subreason': False,
        })
        JobLog._system_append(
            job, 'state_change', reason,
            from_state='running', to_state='cancelled',
        )
        return None

    # ------------------------------------------------------------------
    # Task 005: connection lifecycle actions (DEC-022 / gate document)
    # ------------------------------------------------------------------

    def _create_lifecycle_audit_job(self, message):
        """Create + close one audited `core_manual_maintenance` job.

        The single sanctioned audit-trail path every lifecycle action
        below funnels through. `job_source='setup_readiness_check'` keeps
        this on the existing core/diagnostic source vocabulary (so it is
        never itself business-job-gated); a fresh UUID4 `payload_hash`
        nonce mirrors the already-accepted `action_test_connection`/
        `run_for_store` pattern so repeat lifecycle actions never collide
        on `store_idempotency_key_uniq` (the TD-001 class of issue); every
        log row goes through the existing `_system_append` path -- no new
        job type and no second log-creation path. SEC-1 narrowly elevates
        only the protected job create/final-write sites; the Store and log
        appender retain the original caller environment and actor.
        """
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.sudo().create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_manual_maintenance',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        job = Job.browse(job.id)
        JobLog._system_append(
            job, 'manual_action', message,
            from_state='running', to_state='succeeded',
        )
        job.sudo().write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        return job

    def action_activate(self):
        """Transition to `connected` -- only on real Task 003/004 evidence.

        Never infers success: requires a credential currently on record
        (not merely a stale pass mirror left over from before a
        disconnect -- `action_disconnect` clears `credential_present`
        but does not reset `last_test_connection_result`/
        `last_readiness_result`, so this check is the guard against
        re-activating a credential-less store on old evidence) and that
        the current credential has actually been verified
        (`credential_last_verified_at` truthy). `action_set_token` and
        `action_replace_token` both clear this stamp on every token
        set/update, closing the stale-evidence path at the credential-
        service source. This method deliberately does **not** compare
        the credential row's own `write_date` -- an earlier revision did,
        but real DB write timing on Odoo.sh proved that guard brittle,
        rejecting valid activations. It also requires the stored
        readiness result to be at least as fresh as that verification
        (`last_readiness_at` truthy and not older than
        `credential_last_verified_at`) -- otherwise a readiness pass
        recorded *before* the current credential was verified could
        incorrectly count as evidence for it. Neither the credential-row
        search nor anything else here reads or logs `access_token`, nor
        uses `sudo()` -- the search runs as the calling (Admin) user,
        exactly as the rest of this model's credential-adjacent reads
        already do. If any check fails, raises `UserError` and leaves
        the state untouched -- never calls Shopify, never runs OAuth,
        and never claims VAL-B2 has passed or that MBQ-05 is resolved
        (DEC-022 §4.4).
        """
        self.ensure_one()
        # SEC (Stage R1): Administrator boundary before the store-row lifecycle
        # lock and any audit-job side effect (analogous to Test Connection).
        self._ensure_connector_admin_boundary()
        # CORE-R2 (AR-047; review 4690639375 #1): take the conflicting store-row
        # update lock FIRST, then validate every state-dependent precondition
        # against the fresh state read UNDER that lock (TOCTOU-safe). A disconnect
        # that won the race is observed here and refused -- disconnect is one-way,
        # activation must never overwrite `disconnecting`/`disconnected`. No
        # Shopify call is made while the lock is held (only stored evidence is
        # read); `connection_generation` is bumped exactly once, only on success.
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            raise UserError(
                'Cannot activate: a disconnect is in progress or has completed '
                'for this store.'
            )
        if not self.credential_present:
            raise UserError(
                'Cannot activate: no credential is present for this '
                'store -- enter a credential first.'
            )
        credential = self.env['shopify.connector.store.credential'].search(
            [('store_id', '=', self.id)], limit=1
        )
        if not credential:
            raise UserError(
                'Cannot activate: no credential record exists for this '
                'store -- enter a credential first.'
            )
        if not self.credential_last_verified_at:
            raise UserError(
                'Cannot activate: the current credential has not been '
                'verified yet — run Test Connection first.'
            )
        if self.last_test_connection_result != 'pass':
            raise UserError(
                'Cannot activate: no passing test-connection result is '
                'recorded for this store yet -- run Test Connection first.'
            )
        if self.last_readiness_result not in ('pass', 'warning'):
            raise UserError(
                'Cannot activate: no passing or warning-tier readiness '
                'result is recorded for this store yet -- run the '
                'readiness check first.'
            )
        if (
            not self.last_readiness_at
            or self.last_readiness_at < self.credential_last_verified_at
        ):
            raise UserError(
                'Cannot activate: readiness has not been checked after '
                'the current credential was verified — run the '
                'readiness check first.'
            )
        # Consume the generation read under the held lock and bump it exactly
        # once -- the single successful-activation transition (analysis §8/§9.2).
        self.write({
            'state': 'connected',
            'connection_generation': locked_generation + 1,
        })
        self._create_lifecycle_audit_job(
            'Store activated (test-connection: %s, readiness: %s).' % (
                self.last_test_connection_result, self.last_readiness_result,
            )
        )
        return None

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047): generation-changing lifecycle store-row lock
    # ------------------------------------------------------------------

    def _lock_store_for_lifecycle(self):
        """Acquire the conflicting store-row update lock and fresh-read under it.

        The lifecycle half of the CORE-R2 store-row lock protocol (analysis
        §9.2 / INV-2L). Every generation-changing lifecycle transition
        (disconnect request, activation, reconnect) runs this first, on the
        **request/main cursor**, to take a **blocking** ``SELECT … FOR NO KEY
        UPDATE`` on this store row: it conflicts with -- and therefore waits for
        -- any in-flight admission's brief ``FOR SHARE`` (`_admit`), and
        conflicts with any other lifecycle/finalize update lock, so admission and
        every generation-changing transition **linearize** on the row. Unlike
        Odoo's ``lock_for_update`` (which issues ``FOR UPDATE SKIP LOCKED`` and
        would silently skip a locked row) this waits, because a lifecycle
        transition must not be skipped. A prior ``flush_recordset`` guarantees the
        raw ``SELECT`` observes this transaction's own pending state/generation
        writes; ``invalidate_recordset`` afterwards forces the subsequent field
        reads to come from the freshly-locked row. The lock is released by the
        natural RPC/cron-boundary commit -- **never** an explicit main-cursor
        ``commit`` -- and is never held across a Shopify network call. Only the
        store row is locked here; a path that also touches the credential row
        locks **store first, then credential** (one global order -> deadlock-free,
        §9.2). Returns the fresh ``(state, connection_generation)`` read under the
        lock.
        """
        self.ensure_one()
        # Flush this store's pending ORM writes so the raw locking SELECT below
        # observes the current transaction's own state/generation, then
        # invalidate afterwards so subsequent field reads come from the freshly
        # locked row (the sanctioned Odoo raw-SQL discipline).
        self.flush_recordset()
        self.env.cr.execute(
            "SELECT state, connection_generation "
            "FROM shopify_connector_store WHERE id = %s FOR NO KEY UPDATE",
            (self.id,),
        )
        row = self.env.cr.fetchone()
        self.invalidate_recordset()
        return row

    def _sweep_quiescing_business_jobs(self, reason):
        """Non-blocking A/B sweep of this store's cancellable business jobs.

        Cancels only the **queued** / **retry_waiting** business jobs (the A/B
        rows of the in-flight taxonomy, analysis §3) that can be row-locked
        **without blocking**, via ``try_lock_for_update`` (``FOR UPDATE SKIP
        LOCKED``). A job a concurrent drain holds (row C -- claimed/running) is
        **skipped**, never blocked and never written, so the sweep issues **no**
        write to a locked running/claimed job row (INV-9, packet §6/§14). All job
        history is preserved (cancel, never delete); a job leaving
        ``blocked_manual_review`` -- not swept here, but guarded regardless -- has
        its ``manual_review_subreason`` cleared so the terminal transition never
        violates ``_check_manual_review_subreason_required``. Runs in Phase 1 and
        again in each controller pass; both are non-blocking and idempotent.
        """
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        candidates = Job.search([
            ('store_id', '=', self.id),
            ('job_source', 'in', list(BUSINESS_JOB_SOURCES)),
            ('state', 'in', ('queued', 'retry_waiting')),
            ('mutation_attempt_id', '=', False),
        ])
        if not candidates:
            return
        locked = candidates.try_lock_for_update()
        if not locked:
            return
        locked.invalidate_recordset()
        for job in locked:
            if job.state not in ('queued', 'retry_waiting'):
                continue
            from_state = job.state
            job.sudo().write({
                'state': 'cancelled',
                'cancel_reason': reason,
                'finished_at': fields.Datetime.now(),
                'manual_review_subreason': False,
            })
            JobLog._system_append(
                job, 'state_change', 'Job cancelled: %s' % reason,
                from_state=from_state, to_state='cancelled',
            )

    def _trigger_disconnect_controller(self, at=None):
        """Wake the disconnect quiescence controller cron.

        A one-shot wake after a Phase-1 request (``at=None`` -> immediate) or a
        **delayed** re-poll for a still-quiescing store (``at=now+POLL_DELAY``,
        analysis §14). Never an immediate same-store re-trigger from within a
        quiescing pass (that would busy-loop); duplicate triggers are harmless
        (each controller pass re-selects under SKIP LOCKED and finalize is
        idempotent). Missing-cron tolerant so a lifecycle action never hard-fails
        if the cron record is absent (e.g. in a stripped test registry).
        """
        self.ensure_one()
        cron = self.env.ref(_DISCONNECT_CRON_XMLID, raise_if_not_found=False)
        if not cron:
            return
        if at is None:
            cron._trigger()
        else:
            cron._trigger(at=at)

    def action_disconnect(self):
        """Phase 1 of the two-phase CORE-R2 disconnect (AR-047; analysis §4/§6/§8).

        Requests quiescence -- it does **not** complete the disconnect. On a
        store that is not already `disconnecting`/`disconnected`:

        1. take the conflicting store-row update lock and fresh-read under it
           (`_lock_store_for_lifecycle`);
        2. bump `connection_generation` exactly once -- so **no new business
           Shopify call can be admitted** (the `execute_business` epoch gate
           refuses any job whose captured epoch no longer matches) and no
           business job can start;
        3. transition `state` -> `disconnecting`, `disconnect_status` ->
           `requested`, and stamp `disconnect_requested_at`/`_by`;
        4. run **one** non-blocking A/B (queued/retry_waiting) business-job sweep;
        5. wake the quiescence controller and return "request accepted".

        It deliberately does **not** clear the credential, does **not** wait for
        lease holders, does **not** write a locked running job row, and issues no
        explicit main-cursor commit. The controller (`_run_disconnect_quiesce`)
        later finalizes to `completed` (zero committed leases) or `timed_out`
        (leases still present at the deadline) and clears the credential **then**
        (analysis §15). A repeated disconnect while already
        `disconnecting`/`disconnected` is an **audited idempotent no-op**
        (matrix §8). Disconnect is one-way.
        """
        self.ensure_one()
        # SEC (Stage R1): Administrator boundary before the store-row lock and
        # any audit-job side effect. Without it the already-disconnecting
        # "audited no-op" branch below would create a `Job`/`job.log` via
        # `sudo()` for an unauthorized caller with NO denial at all.
        self._ensure_connector_admin_boundary()
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            self._create_lifecycle_audit_job(
                'Disconnect requested; store already %s -- audited no-op.'
                % locked_state
            )
            return None
        self._request_disconnect_locked(locked_state, locked_generation)
        return None

    def _request_disconnect_locked(self, locked_state, locked_generation):
        """Phase-1 disconnect request body, run UNDER the held store lifecycle
        lock (CORE-R2, AR-047; reviews 4690804619 §11 + 4690807427).

        The caller must already hold `_lock_store_for_lifecycle` and pass the
        `(state, generation)` it read under that lock; this consumes them directly
        -- bumping `connection_generation` to **`locked_generation + 1`** (the
        value returned under the lock, never an indirect re-read of the field) --
        so **no new business Shopify call can be admitted** and no business job can
        start. It then transitions to `disconnecting`/`requested`, stamps the
        request, runs **one** non-blocking A/B (queued/retry_waiting) business-job
        sweep, records the audit, and wakes the quiescence controller. It clears
        **no** credential and issues no explicit commit; the controller finalizes.

        Shared by `action_disconnect` (the direct request) and the public
        `action_clear_token` when it routes a `connected`/`reconnect_needed` store
        through the accepted two-phase disconnect instead of clearing immediately
        (review 4690807427) -- both take the lock, then call this once.
        """
        self.ensure_one()
        new_generation = locked_generation + 1
        self.write({
            'state': 'disconnecting',
            'connection_generation': new_generation,
            'disconnect_status': 'requested',
            'disconnect_status_reason': False,
            'disconnect_requested_at': fields.Datetime.now(),
            'disconnect_requested_by': self.env.uid,
            'disconnect_completed_at': False,
            'disconnect_open_lease_count': 0,
            'disconnect_oldest_admitted_at': False,
        })
        self._sweep_quiescing_business_jobs('Store disconnecting.')
        self._create_lifecycle_audit_job(
            'Store disconnect requested (state=disconnecting; connection '
            'generation bumped to %d).' % new_generation
        )
        self._trigger_disconnect_controller()
        return None

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047): disconnect quiescence controller (analysis §14/§16)
    # ------------------------------------------------------------------

    @api.model
    def _run_disconnect_quiesce(self):
        """The disconnect quiescence controller cron entry point.

        Processes **exactly one** `disconnecting` store per invocation/transaction
        (analysis §14, packet §13). Selects the next **unlocked** store with the
        corrected ``search(order=…).try_lock_for_update(limit=1)`` idiom (``FOR
        UPDATE SKIP LOCKED LIMIT 1``): a locked first row does **not** block later
        ones, and an all-locked set is a **documented no-op** for this pass (a
        later pass handles them). The held ``FOR UPDATE`` conflicts with
        admission's ``FOR SHARE``, so no new lease can commit for this store while
        it is checked and finalized -- both the duplicate-finalization guard and
        the count-stability guarantee. No explicit main-cursor commit: the natural
        cron-boundary commit persists the finalize and releases the lock together.
        """
        stores = self.search(
            [('state', '=', 'disconnecting')],
            order='disconnect_requested_at, id',
        )
        if not stores:
            return
        store = stores.try_lock_for_update(limit=1)
        if not store:
            # Every eligible row is locked by a concurrent controller -> safe
            # no-op this pass (analysis §14); a later pass handles them.
            return
        store._process_disconnect_quiesce()

    def _layer2_disconnect_blockers(self):
        self.ensure_one()
        Attempt = self.env['shopify.connector.mutation.attempt']
        attempts = Attempt.search([
            ('store_id', '=', self.id),
            '|',
            ('observed_outcome', '=', 'pending'),
            '&',
            ('observed_outcome', '=', 'uncertain'),
            ('resolution_disposition', '=', False),
        ])
        reconciliations = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.id),
            ('mutation_attempt_id', '!=', False),
            ('state', 'in', ('queued', 'running', 'retry_waiting')),
        ])
        return attempts, reconciliations

    def _process_disconnect_quiesce(self):
        """One quiescence pass for a single locked `disconnecting` store.

        Runs under the controller's held store ``FOR UPDATE`` (no new ``FOR
        SHARE`` admission can commit a lease meanwhile, so the count is stable
        through finalize). Re-checks the state under the lock, runs the
        non-blocking A/B sweep, then applies **direction C** (analysis §10/§16):
        count **all** committed lease rows (an expired-but-unreleased lease still
        counts -- it is unknown/live, never reaped into `completed`); write the
        escalation snapshot; then **zero rows -> `completed`**, **rows within the
        timeout -> `quiescing`** (schedule a delayed re-poll), **rows at/past
        `DISCONNECT_QUIESCE_TIMEOUT` -> `timed_out`**.
        """
        self.ensure_one()
        if self.state != 'disconnecting':
            # Re-checked under the lock: a concurrent pass already finalized it.
            return
        self._sweep_quiescing_business_jobs('Store disconnecting.')
        Lease = self.env['shopify.connector.call.lease']
        leases = Lease.search([('store_id', '=', self.id)])
        count = len(leases)
        oldest = min(leases.mapped('admitted_at')) if leases else False
        self.write({
            'disconnect_open_lease_count': count,
            'disconnect_oldest_admitted_at': oldest,
        })
        attempts, reconciliations = self._layer2_disconnect_blockers()
        if count == 0 and not attempts and not reconciliations:
            # Completion requires both call-lease quiescence and Layer 2
            # mutation/reconciliation quiescence.
            self._finalize_disconnect_completed()
            return
        requested_at = self.disconnect_requested_at or fields.Datetime.now()
        elapsed = fields.Datetime.now() - requested_at
        if elapsed >= DISCONNECT_QUIESCE_TIMEOUT:
            if attempts or reconciliations:
                self._block_disconnect_for_layer2_evidence(
                    attempts, reconciliations, count,
                )
            else:
                self._finalize_disconnect_timed_out(leases)
        else:
            self.write({
                'disconnect_status': 'quiescing',
                'disconnect_status_reason': (
                    '%d call lease(s), %d unresolved mutation attempt(s), '
                    'and %d reconciliation job(s) remain; waiting for '
                    'quiescence.' % (
                        count, len(attempts), len(reconciliations),
                    )
                ),
            })
            self._trigger_disconnect_controller(
                at=fields.Datetime.now() + POLL_DELAY
            )

    def _block_disconnect_for_layer2_evidence(
        self, attempts, reconciliations, lease_count,
    ):
        self.ensure_one()
        reason = (
            'Disconnect blocked at the quiescence deadline: %d call lease(s), '
            '%d unresolved mutation attempt(s), and %d reconciliation job(s) '
            'remain. Credentials were preserved.'
            % (lease_count, len(attempts), len(reconciliations))
        )
        self.write({
            'disconnect_status': 'timed_out',
            'disconnect_status_reason': reason,
            'disconnect_open_lease_count': lease_count,
        })
        self._create_lifecycle_audit_job(reason)
        return False

    def action_force_disconnect(self, reason):
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may force disconnect.'
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError('A non-empty force-disconnect reason is required.')
        safe_reason = redact(reason.strip())
        self._lock_store_for_lifecycle()
        attempts, reconciliations = self._layer2_disconnect_blockers()
        leases = self.env['shopify.connector.call.lease'].search([
            ('store_id', '=', self.id),
        ])
        for attempt in attempts:
            job = attempt.job_id
            if job.state != 'blocked_manual_review':
                from_state = job.state
                job.sudo().write({
                    'state': 'blocked_manual_review',
                    'error_class': 'duplicate_risk',
                    'manual_review_subreason': 'duplicate_risk',
                    'finished_at': fields.Datetime.now(),
                    'reconciliation_pending_until': False,
                    'current_attempt_token': False,
                    'owner_worker_ref': False,
                    'running_since': False,
                })
                job._log_transition(
                    'manual_action',
                    'Force-disconnect routed unresolved mutation evidence to '
                    'Administrator review; no outcome was inferred.',
                    from_state=from_state,
                    to_state='blocked_manual_review',
                )
        audit = (
            'Force disconnect requested by actor_uid=%d; reason=%s; '
            'unresolved_attempt_count=%d reconciliation_job_count=%d. '
            'Credentials preserved pending explicit attempt resolution.'
            % (
                self.env.uid, safe_reason, len(attempts),
                len(reconciliations),
            )
        )
        if attempts or reconciliations or leases:
            self.write({
                'state': 'disconnecting',
                'disconnect_status': 'timed_out',
                'disconnect_status_reason': audit,
            })
            self._create_lifecycle_audit_job(audit)
            return False
        self._create_lifecycle_audit_job(audit)
        self._finalize_disconnect_completed()
        return True

    def _finalize_disconnect_completed(self):
        """Finalize a fully-quiesced disconnect (zero committed lease rows).

        Reachable **only** at zero lease rows (INV-3, direction C). Clears the
        credential via the controller-only `_clear_token_under_store_lock`
        primitive **under the controller's held store ``FOR UPDATE``**
        (store->credential global lock order, §9.2/§15) -- never the public
        `action_clear_token`, which refuses a `disconnecting` store (review
        4690804619 #2). No admission can slip in during the clear; this finalize
        then sets `disconnected` / `disconnect_status='completed'` and stamps
        completion. All job/log history is preserved. `completed` is provably
        distinct from `timed_out` (this path is the zero-rows condition only).
        """
        self.ensure_one()
        self.env[
            'shopify.connector.store.credential'
        ]._clear_token_under_store_lock(self)
        self.write({
            'state': 'disconnected',
            'disconnect_status': 'completed',
            'disconnect_status_reason': (
                'Disconnect completed: all in-flight call leases released.'
            ),
            'disconnect_open_lease_count': 0,
            'disconnect_oldest_admitted_at': False,
            'disconnect_completed_at': fields.Datetime.now(),
        })
        self._create_lifecycle_audit_job(
            'Store disconnect completed (0 outstanding call leases).'
        )

    def _finalize_disconnect_timed_out(self, leases):
        """Finalize a disconnect that reached the timeout with lease rows present.

        Direction C (analysis §16): with **any** lease rows still present (expired
        or live) at `DISCONNECT_QUIESCE_TIMEOUT`, record a **bounded, secret-free**
        escalation snapshot (count, oldest-admitted age, and at most
        ``_ESCALATION_SNAPSHOT_LIMIT`` opaque `lease_key`s / Integer `job_id`s --
        never a token/credential/payload), clear the credential (the bounded set
        of already-admitted holders may finish with their **already-captured
        in-memory token**; clearing the row does not invalidate sent bytes), and
        set `disconnected` / `disconnect_status='timed_out'` -- a status **distinct
        from `completed`**. Job/log history is preserved. The residual lease rows
        are cleaned up **only after** this `timed_out` finalization (never before,
        never on the `completed` path) -- the only sanctioned cleanup point.
        """
        self.ensure_one()
        count = len(leases)
        oldest = min(leases.mapped('admitted_at')) if leases else False
        snapshot = [
            {'lease_key': lease.lease_key, 'job_id': lease.job_id}
            for lease in leases[:_ESCALATION_SNAPSHOT_LIMIT]
        ]
        reason = (
            'Disconnect timed out with %d outstanding call lease(s) at the '
            'quiescence deadline; credential cleared. Outstanding holders '
            '(bounded to %d): %s'
            % (count, _ESCALATION_SNAPSHOT_LIMIT, json.dumps(snapshot))
        )
        # Controller-only clear primitive under the held store FOR UPDATE (review
        # 4690804619 #2); this finalize sets `disconnected`/`timed_out` itself.
        self.env[
            'shopify.connector.store.credential'
        ]._clear_token_under_store_lock(self)
        self.write({
            'state': 'disconnected',
            'disconnect_status': 'timed_out',
            'disconnect_status_reason': reason,
            'disconnect_open_lease_count': count,
            'disconnect_oldest_admitted_at': oldest,
            'disconnect_completed_at': fields.Datetime.now(),
        })
        self._create_lifecycle_audit_job(
            'Store disconnect timed out (%d outstanding call lease(s); '
            'credential cleared; distinct from completed).' % count
        )
        # Direction C: residual lease rows are cleaned up ONLY AFTER the
        # `timed_out` finalization -- never before, never on the `completed`
        # path -- since the store is now `timed_out`, not `completed`.
        leases.unlink()

    def action_reconnect(self):
        """Re-run the existing Task 003/004 substrate; connect only on evidence.

        Service/model layer only -- no OAuth, no setup wizard, no new
        credential-input mechanism; token re-entry goes through the
        existing Task 002 credential service exactly as `activate`/
        initial setup already do. Never infers `connected` from
        credential presence alone: transitions to `connected` only if the
        freshly re-run test-connection and readiness substrate both
        actually support it, otherwise remains/transitions to
        `reconnect_needed` (DEC-022 §4.6).

        With no credential present: this method does not call Shopify,
        does not run readiness, does not clear the credential, and does
        not auto-reconnect -- it only persists the reconnect_needed
        state and its audit job, then returns `None`. It deliberately
        does not raise afterward: in normal Odoo RPC/service execution a
        raised exception can roll back the ORM writes made earlier in
        the same call, which would silently discard the very
        state/audit write this branch exists to guarantee. A caller
        that needs to distinguish "reconnect actually connected" from
        "reconnect left the store in reconnect_needed" should check
        `self.state` after calling, not rely on an exception.
        """
        self.ensure_one()
        # SEC (Stage R1): Administrator boundary before `_run_connection_probe`
        # (reconnect shares Test Connection's job/log/credential/transport path)
        # or any reconnect_needed audit-job side effect.
        self._ensure_connector_admin_boundary()
        # CORE-R2 (AR-047; analysis §8): reconnect is refused while the store is
        # `disconnecting` (disconnect is one-way; reconnect is only from the
        # finalized `disconnected` state). No credential/state/audit is written.
        if self.state == 'disconnecting':
            raise UserError(
                'Cannot reconnect: a disconnect is in progress for this '
                'store.'
            )
        if not self.credential_present:
            self.write({'state': 'reconnect_needed'})
            self._create_lifecycle_audit_job(
                'Reconnect attempted with no stored credential; remains '
                'reconnect_needed.'
            )
            return None
        # CORE-R2 (AR-047; review 4690639375 #1): capture the connection epoch at
        # reconnect start. The probe/readiness below run UNLOCKED, so a disconnect
        # (or any other generation-changing transition) winning the race during
        # them will change this epoch; the finalize then refuses rather than
        # overwriting it. Capturing the epoch -- not a blanket `disconnected`
        # refusal -- is what lets a *legitimate* reconnect from the finalized
        # `disconnected` state (its epoch unchanged during the probe) still
        # succeed, while a disconnect that WON during the probe is refused.
        initial_generation = self.connection_generation
        # CORE-R2 (AR-047; review 4690639375 #2): reconnect probes via the shared
        # `_run_connection_probe` with the INTERNAL purpose `'reconnect_probe'`,
        # which the frozen matrix permits from the finalized `disconnected` state
        # (reconnect after completed disconnect) -- unlike `'test_connection'`,
        # which excludes `disconnected`. The probe issues the Shopify call, then
        # revalidates its one credential snapshot under the store->credential locks.
        probe_status = self._run_connection_probe('reconnect_probe')
        if probe_status == 'superseded':
            # A lifecycle/credential change won during the probe; it was already
            # audited as superseded and wrote no mirrors. Do not run readiness or
            # finalize on a store that has moved on -- abort the reconnect.
            return None
        self.invalidate_recordset()
        # If the probe just failed with an auth/permission/scope signal,
        # `_run_connection_probe`'s own handler already called
        # action_mark_reconnect_needed() (which is itself TOCTOU-safe and refuses
        # to overwrite a one-way disconnect). Detect it via the fresh job's
        # error_class to avoid doubling the audit trail for one logical attempt.
        already_marked_reconnect_needed = False
        if self.last_test_connection_result != 'pass':
            last_test_job = self.env['shopify.connector.job'].search([
                ('store_id', '=', self.id),
                ('job_type', '=', 'core_test_connection'),
            ], order='id desc', limit=1)
            already_marked_reconnect_needed = (
                last_test_job.error_class == ERROR_AUTH
            )
        self.env['shopify.connector.readiness.check'].run_for_store(self)
        self.invalidate_recordset()
        reconnect_ok = (
            self.last_test_connection_result == 'pass'
            and self.last_readiness_result in ('pass', 'warning')
        )
        # CORE-R2 (AR-047; review 4690639375 #1): finalize the reconnect state
        # transition UNDER the conflicting update lock, revalidating the fresh
        # state read under it. Refuse -- never overwriting -- if a disconnect is
        # in progress (`disconnecting`) OR if the connection epoch changed since
        # reconnect start (a disconnect, activation, or credential change won the
        # race during the unlocked probe/readiness). A store that was already
        # `disconnected` at reconnect start with an unchanged epoch is a
        # legitimate reconnect and proceeds.
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if (
            locked_state == 'disconnecting'
            or locked_generation != initial_generation
        ):
            self._create_lifecycle_audit_job(
                'Reconnect aborted: a concurrent lifecycle transition won '
                'during the probe; store remains %s.' % locked_state
            )
            return None
        if reconnect_ok:
            # A successful reconnect is a generation-changing transition -- bump
            # the epoch exactly once, consuming the generation read under the lock.
            self.write({
                'state': 'connected',
                'connection_generation': locked_generation + 1,
            })
            self._create_lifecycle_audit_job(
                'Store reconnected (test-connection: %s, readiness: '
                '%s).' % (
                    self.last_test_connection_result,
                    self.last_readiness_result,
                )
            )
        elif not already_marked_reconnect_needed:
            self.write({'state': 'reconnect_needed'})
            self._create_lifecycle_audit_job(
                'Reconnect evidence insufficient; remains reconnect_needed '
                '(test-connection: %s, readiness: %s).' % (
                    self.last_test_connection_result,
                    self.last_readiness_result,
                )
            )
        return None

    def action_mark_reconnect_needed(self, reason=False):
        """Move to `reconnect_needed`; never auto-clears the credential or reconnects.

        Only an explicit `action_reconnect`/`action_disconnect`, taken by
        an operator, may move the store away from this state -- no
        automatic reconnect is ever attempted here or anywhere else
        (DEC-022 §4.7). Idempotent: calling this on a store already in
        `reconnect_needed` is a safe, audited no-op re-record, never an
        error.

        CORE-R2 (AR-047; review 4690639375 #1): this is called both directly and
        from `_run_connection_probe`'s auth-failure handler, so it takes the
        conflicting store-row update lock and fresh-reads the state first; it
        **never overwrites a one-way disconnect** (`disconnecting`/`disconnected`
        -> audited no-op). Moving to `reconnect_needed` is an auth-failure
        degradation, not a generation-changing reconnect, so it does **not** bump
        the epoch.

        SEC (Stage R2 correction; independent review 5049668193 P1): this public
        method had no `_ensure_connector_admin_boundary()` call at all -- on a
        store already `disconnecting`/`disconnected` the audited-no-op branch
        below creates a `sudo()`-backed audit Job/JobLog with **no** denial
        whatsoever (the one ACL-gated write in this method sits only in the
        *other* branch). Enforcing the boundary here, first, mirrors the other
        four privileged public store actions. The sole internal caller
        (`_apply_probe_failure`, via `_run_connection_probe`) only ever reaches
        this method after its own caller -- `action_test_connection` or
        `action_reconnect` -- already passed this identical check earlier in the
        same request, so this is a no-op re-check for every legitimate internal
        path, never a behavior change for it.
        """
        self.ensure_one()
        self._ensure_connector_admin_boundary()
        locked_state, _generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            self._create_lifecycle_audit_job(
                'Reconnect-needed signal ignored: store is %s (disconnect is '
                'one-way).' % locked_state
            )
            return None
        self.write({'state': 'reconnect_needed'})
        message = 'Store marked reconnect_needed.'
        if reason:
            message = 'Store marked reconnect_needed: %s' % redact(reason)
        self._create_lifecycle_audit_job(message)
        return None
