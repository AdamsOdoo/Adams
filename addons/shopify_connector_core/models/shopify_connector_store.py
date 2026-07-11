import json
import uuid

from odoo import fields, models
from odoo.exceptions import UserError

from ..tools.redaction import redact
from .shopify_connector_api_client import ERROR_AUTH, ShopifyClientError
from .shopify_connector_job import BUSINESS_JOB_SOURCES, TERMINAL_JOB_STATES

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
            ('disconnected', 'Disconnected'),
        ],
        required=True,
        index=True,
        default='setup_incomplete',
        readonly=True,
    )
    api_version = fields.Char(required=True)
    api_health_state = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('throttled', 'Throttled'),
            ('degraded', 'Degraded'),
        ],
        readonly=True,
    )
    api_health_reason = fields.Char(readonly=True)
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

    _shop_domain_uniq = models.Constraint(
        'UNIQUE(shop_domain)',
        'A store already exists for this Shopify shop domain.',
    )

    def action_test_connection(self):
        """Run one read-only Shopify test-connection check (Task 003).

        Admin-invoked (store write access is Admin-only per the merged
        ACL, so this is enforced by the existing ACL, not a new guard).
        Creates exactly one `job_type='core_test_connection'` job per
        run, with a fresh UUID4 `payload_hash` nonce so repeat runs never
        collide on `store_idempotency_key_uniq` --
        `core_readiness_check`'s identical latent exposure is untouched
        (TD-001). Writes only the store mirrors, the credential's
        `credential_state` (only for a genuine token-invalid signal), and
        the job/job.log rows -- never the token, never a raw response
        body outside the client's already-redacted `technical_detail`.
        """
        self.ensure_one()
        if not self.credential_present:
            raise UserError(
                'Enter a credential before testing the connection.'
            )
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Test connection attempt started.',
        )

        try:
            result = self.env['shopify.connector.api.client'].execute(
                self, TEST_CONNECTION_QUERY
            )
        except ShopifyClientError as exc:
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
                    credential.write({'credential_state': 'invalid'})
            if exc.credential_invalid or exc.error_class == ERROR_AUTH:
                # Task 005 / DEC-022 §4.7: any auth/permission/scope
                # invalidation signal -- not only a genuine token-invalid
                # one -- moves the store to reconnect_needed. Human/admin
                # action (reconnect/disconnect) is the only way out; this
                # never auto-reconnects.
                self.action_mark_reconnect_needed(reason=exc.reason)
            job.write({
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
            job.write({
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
        if result.get('version_fallforward'):
            self.write({
                'api_health_state': 'degraded',
                'api_health_reason': redact(
                    'Shopify served API version %s instead of the '
                    'configured %s.' % (
                        result.get('served_version'), self.api_version,
                    )
                ),
            })
        else:
            # D-R1-5 (Task CORE-R1): a fully successful test connection
            # with no API-version fall-forward is the healthy API state --
            # record 'normal' so the unchanged _check_api_version_health
            # readiness check can pass on real evidence (no merged path
            # wrote 'normal' before this, leaving the field NULL and
            # readiness permanently fail-closed). The 'degraded'
            # fall-forward path above is untouched.
            self.write({'api_health_state': 'normal'})
        job.write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt',
            'Connection verified with %s.' % shop.get('name'),
            from_state='running', to_state='succeeded',
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
        job type, no second log-creation path, no `sudo()`.
        """
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_manual_maintenance',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'manual_action', message,
            from_state='running', to_state='succeeded',
        )
        job.write({
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
        self.write({'state': 'connected'})
        self._create_lifecycle_audit_job(
            'Store activated (test-connection: %s, readiness: %s).' % (
                self.last_test_connection_result, self.last_readiness_result,
            )
        )
        return None

    def action_disconnect(self):
        """Clear the credential, cancel non-terminal business jobs, disconnect.

        Reuses the existing Task 002 credential-clear service -- no
        second credential-clear path -- which preserves the credential
        row and its history. Cancels every non-terminal business job for
        this store (never deletes a job); core setup/test/readiness/
        maintenance jobs and already-terminal jobs are left untouched.
        Idempotent: a second call finds nothing left to cancel and simply
        re-records an audited no-op (DEC-022 §4.1/§4.5).
        """
        self.ensure_one()
        self.env['shopify.connector.store.credential'].action_clear_token(
            self
        )
        self.write({'state': 'disconnected'})
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        jobs_to_cancel = Job.search([
            ('store_id', '=', self.id),
            ('job_source', 'in', list(BUSINESS_JOB_SOURCES)),
            ('state', 'not in', list(TERMINAL_JOB_STATES)),
        ])
        for job in jobs_to_cancel:
            from_state = job.state
            job.write({
                'state': 'cancelled',
                'cancel_reason': 'Store disconnected.',
                'finished_at': fields.Datetime.now(),
                # A job coming from blocked_manual_review carries a
                # manual_review_subreason (required by that state's own
                # constraint) -- clearing it here is required so the
                # same job's move to 'cancelled' doesn't violate
                # _check_manual_review_subreason_required, which forbids
                # a non-blocked_manual_review state from carrying one.
                'manual_review_subreason': False,
            })
            JobLog._system_append(
                job, 'state_change', 'Job cancelled: store disconnected.',
                from_state=from_state, to_state='cancelled',
            )
        self._create_lifecycle_audit_job(
            'Store disconnected (%d non-terminal business job(s) '
            'cancelled).' % len(jobs_to_cancel)
        )
        return None

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
        if not self.credential_present:
            self.write({'state': 'reconnect_needed'})
            self._create_lifecycle_audit_job(
                'Reconnect attempted with no stored credential; remains '
                'reconnect_needed.'
            )
            return None
        self.action_test_connection()
        self.invalidate_recordset()
        # If test-connection just failed with an auth/permission/scope
        # signal, action_test_connection()'s own exception handler
        # already called action_mark_reconnect_needed() -- its state
        # write and audit job are already recorded. Re-running that same
        # write/audit below would double the audit trail for one logical
        # reconnect attempt, so detect it via the fresh job's error_class
        # (the same condition action_test_connection() itself used) and
        # skip the redundant re-write. Every other failure path (identity
        # mismatch, temporary/throttle/unknown errors, or a readiness
        # failure with a passing test-connection) still falls through to
        # this method's own reconnect_needed write/audit below, since
        # action_test_connection() does not handle those itself.
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
        if (
            self.last_test_connection_result == 'pass'
            and self.last_readiness_result in ('pass', 'warning')
        ):
            self.write({'state': 'connected'})
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
        """
        self.ensure_one()
        self.write({'state': 'reconnect_needed'})
        message = 'Store marked reconnect_needed.'
        if reason:
            message = 'Store marked reconnect_needed: %s' % redact(reason)
        self._create_lifecycle_audit_job(message)
        return None
