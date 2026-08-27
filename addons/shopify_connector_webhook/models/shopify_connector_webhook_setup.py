"""Setup hand-off for the installed webhook foundation.

The core guided setup service owns the store transition and the completion
transaction.  This small extension only supplies the post-transition policy:
webhook subscription readiness is established by a durable worker and setup
remains incomplete until the worker's stored Shopify read-back evidence makes
the installed webhook readiness check pass.
"""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_store_credential import (
    AUTH_MODE_OFFLINE,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_setup_wizard import (
    SETUP_STEP_COUNT,
)


ACTIVE_SETUP_JOB_STATES = (
    'draft', 'queued', 'running', 'retry_waiting', 'failed_retryable',
)
CHILD_SETUP_JOB_TYPES = (
    'webhook_subscription_create',
    'webhook_subscription_delete',
    'webhook_subscription_mutation_reconcile',
)


class ShopifyConnectorWebhookSetup(models.AbstractModel):
    """Make webhook proof an asynchronous, truthful setup completion gate."""

    _inherit = 'shopify.connector.setup.wizard'

    @api.model
    def _setup_reconciliation_job(self, store):
        """Return the latest setup job for the *current* store generation.

        A queued job from a prior connect/reconnect epoch is evidence, not a
        reusable lease.  Limiting this lookup to the current generation makes
        repeated activation coalesce only with the live job and causes a
        stale active job to receive a fresh bounded replacement.
        """
        return self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'webhook_subscription_reconcile'),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', store.id),
            ('job_source', '=', 'setup_readiness_check'),
            ('expected_connection_generation', '=', store.connection_generation),
        ], order='id desc', limit=1)

    @api.model
    def _webhook_client_secret_gate(self, store):
        """Return a non-secret setup block when HMAC cannot be verified.

        An offline Admin API token is sufficient for Shopify API calls but not
        for validating webhook signatures.  Refuse before activation and
        before any subscription job is admitted when that mode has no stored
        app client secret.  The only secret read is an in-process boolean
        under the existing credential ACL surface; it is never returned.
        """
        if not store or not store.credential_present:
            return False
        credential = self.env[
            'shopify.connector.store.credential'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if not credential or credential.credential_state == 'absent':
            return False
        if credential.client_secret:
            return False
        if credential.auth_mode == AUTH_MODE_OFFLINE:
            message = (
                'Webhook setup needs the Shopify app client secret for HMAC '
                'verification. This offline access-token mode cannot complete '
                'webhook setup without it. Use the Client ID + Client secret '
                'token-exchange mode, then run Test connection and readiness '
                'again.'
            )
        else:
            message = (
                'Webhook setup needs a stored Shopify app client secret for '
                'HMAC verification. Re-enter the Client ID and Client secret, '
                'then run Test connection and readiness again.'
            )
        return {
            'state': 'action_required',
            'code': 'client_secret_required',
            'message': message,
            'job_id': False,
        }

    @api.model
    def _child_setup_work(self, store):
        """Project unresolved work from each subscription's latest lineage.

        Parent reconciliation may have succeeded while its Layer-2 child is
        still queued, retrying, or waiting for verification.  That is a
        truthful pending state, not an operator error and not permission to
        enqueue another parent.  Historical job rows remain immutable audit
        evidence, but they are not setup blockers after a sanctioned retry
        advances the subscription's ``last_job_id`` lineage and a later
        read-back proves the subscription active.

        The subscription pointer is the durable per-topic/action lineage
        selector: scanning every historical child row would let an old
        ``failed_final`` or ``blocked_manual_review`` row poison a later,
        verified attempt.  A pointer from another connection generation is
        likewise evidence for reconciliation, not current setup work.
        """
        Subscription = self.env[
            'shopify.connector.webhook.subscription'
        ].sudo()
        subscriptions = Subscription.search([
            ('store_id', '=', store.id),
            ('expected', '=', True),
        ], order='id asc')
        current_lineage = []
        for subscription in subscriptions:
            job = subscription.last_job_id
            if (
                not job
                or job.store_id != store
                or job.job_source != 'setup_readiness_check'
                or job.job_type not in CHILD_SETUP_JOB_TYPES
                or job.expected_connection_generation
                != store.connection_generation
            ):
                continue
            # A real current-generation read-back that made this topic active
            # is the strongest local proof.  Do not let an older terminal
            # child row override it; the readiness check below still validates
            # callback, API-version, format, epoch and reconciliation time.
            if subscription.state == 'active':
                continue
            current_lineage.append((subscription, job))

        blocked = [
            (subscription, job) for subscription, job in current_lineage
            if job.state == 'blocked_manual_review'
            or subscription.state == 'manual_review'
        ]
        if blocked:
            subscription, job = blocked[0]
            job_id = job.id
            return {
                'state': 'action_required',
                'code': 'child_manual_review',
                'job_id': job_id,
                'message': (
                    'Webhook subscription work for topic %s is blocked for '
                    'manual review in job #%d. Resolve the preserved Shopify '
                    'evidence before retrying.'
                    % (subscription.topic, job_id)
                ),
            }
        failed = [
            (subscription, job) for subscription, job in current_lineage
            if job.state == 'failed_final' or subscription.state == 'error'
        ]
        if failed:
            subscription, job = failed[0]
            return {
                'state': 'action_required',
                'code': 'child_failed_final',
                'job_id': job.id,
                'message': (
                    'Webhook subscription job #%d for topic %s ended in a '
                    'final failure. Resolve it and reconcile again before '
                    'completing setup.' % (job.id, subscription.topic)
                ),
            }
        active = [
            (subscription, job) for subscription, job in current_lineage
            if job.state in ACTIVE_SETUP_JOB_STATES
        ]
        if active:
            subscription, job = active[0]
            return {
                'state': 'pending',
                'code': 'child_work_pending',
                'job_id': job.id,
                'message': (
                    'Webhook subscription job #%d for topic %s is still %s; '
                    'setup remains incomplete until Shopify read-back '
                    'verification finishes.'
                    % (job.id, subscription.topic, job.state)
                ),
            }
        pending = [
            (subscription, job) for subscription, job in current_lineage
            if subscription.state == 'pending_verification'
            or job.state == 'succeeded'
        ]
        if pending:
            subscription, job = pending[0]
            return {
                'state': 'pending',
                'code': 'child_work_pending',
                'job_id': job.id,
                'message': (
                    'Webhook subscription #%d was created but still needs '
                    'Shopify read-back verification.' % subscription.id
                ),
            }
        return False

    @api.model
    def _webhook_setup_status(self, store, settings):
        """Return a non-secret operator projection of the setup hand-off."""
        if not store or not settings:
            return {
                'state': 'not_started',
                'message': '',
                'job_id': False,
            }
        credential_gate = self._webhook_client_secret_gate(store)
        if credential_gate:
            return credential_gate
        if settings.setup_completed_at:
            return {
                'state': 'complete',
                'code': 'complete',
                'message': 'Setup is complete; webhook health is shown separately.',
                'job_id': False,
            }
        if store.state != 'connected':
            return {
                'state': 'not_started',
                'code': 'not_connected',
                'message': 'Complete connection setup before webhook proof is collected.',
                'job_id': False,
            }

        requirement = self._activation_requirement_status(store, settings)
        if requirement.get('state') != 'ready':
            return requirement

        # A bootstrap read may have populated rows while the store was still
        # setup-incomplete.  That evidence is useful, but it is not the
        # connected-state proof required to finish activation.  The
        # setup-owned reconciliation job is therefore part of the gate: it
        # must have succeeded at the current connection generation, and the
        # stored HMAC/subscription projection must pass beside it.
        job = self._setup_reconciliation_job(store)
        child_work = self._child_setup_work(store)
        if child_work and child_work['state'] == 'action_required':
            return child_work
        if child_work and child_work['code'] == 'child_work_pending':
            return child_work
        check = self.env[
            'shopify.connector.readiness.check'
        ]._check_webhook_hmac(store)
        connected_job_proof = bool(
            job
            and job.state == 'succeeded'
            and job.expected_connection_generation
            == store.connection_generation
        )
        if (
            connected_job_proof
            and check.get('result') == self.env[
                'shopify.connector.readiness.check'
            ].RESULT_PASS
            and not check.get('not_applicable')
        ):
            return {
                'state': 'ready_to_complete',
                'code': 'ready_to_complete',
                'message': (
                    'Webhook subscription read-back proof is recorded. Run '
                    'readiness again, then activate to complete setup.'
                ),
                'job_id': False,
            }

        if job and job.state in ACTIVE_SETUP_JOB_STATES:
            return {
                'state': 'pending',
                'code': 'parent_work_pending',
                'message': (
                    'Connected, but setup is waiting for webhook subscription '
                    'read-back. Reconciliation job #%d is %s; setup is not '
                    'complete yet.' % (job.id, dict(
                        job._fields['state']._description_selection(self.env)
                    ).get(job.state, job.state))
                ),
                'job_id': job.id,
            }
        if job and job.state not in TERMINAL_JOB_STATES:
            # ``blocked_manual_review`` is intentionally visible as an
            # operator action rather than treated as a retryable pending job.
            return {
                'state': 'action_required',
                'code': 'parent_manual_review',
                'message': (
                    'Webhook reconciliation job #%d requires operator review '
                    'before setup can be completed.' % job.id
                ),
                'job_id': job.id,
            }
        if job:
            return {
                'state': 'action_required',
                'code': 'parent_finished_without_proof',
                'message': (
                    'Webhook reconciliation job #%d ended in %s. Resolve it, '
                    'run reconciliation again, and rerun readiness before '
                    'completing setup.' % (
                        job.id,
                        dict(
                            job._fields['state']._description_selection(self.env)
                        ).get(job.state, job.state),
                    )
                ),
                'job_id': job.id,
            }
        return {
            'state': 'pending',
            'code': 'parent_missing',
            'message': (
                'Connected; webhook reconciliation has not produced proof yet. '
                'Use Reconcile webhooks, then rerun readiness.'
            ),
            'job_id': False,
        }

    @api.model
    def _activation_completion_policy(self, store, settings):
        """Defer completion once, then allow it only on stored proof."""
        parent = super()._activation_completion_policy(store, settings)
        status = self._webhook_setup_status(store, settings)
        if status['state'] == 'ready_to_complete':
            return parent

        # A missing HMAC secret, a blocked parent, or a failed child is an
        # explicit operator action.  Do not turn any of those states into a
        # fresh subscription/reconcile enqueue from a repeated activation.
        if status['state'] == 'action_required':
            return {
                'complete': False,
                'job_id': status.get('job_id'),
                'message': status['message'],
            }
        if status.get('code') == 'child_work_pending':
            return {
                'complete': False,
                'job_id': status.get('job_id'),
                'message': status['message'],
            }

        # This is a durable enqueue only.  The worker performs the production
        # API read/mutation through the W1 subscription service and Layer 2;
        # no remote operation is allowed in the setup transaction.
        Subscription = self.env['shopify.connector.webhook.subscription']
        job = self._setup_reconciliation_job(store)
        if not job or job.state not in ACTIVE_SETUP_JOB_STATES:
            job = Subscription._enqueue_store_reconcile(
                store, source='setup_readiness_check',
            )
        settings.sudo().write({
            # Keep the operator on the final review step when reopening.  It
            # is a resume point, not completion evidence.
            'setup_wizard_step_key': 'review',
            'setup_wizard_step': SETUP_STEP_COUNT,
        })
        return {
            'complete': False,
            'job_id': job.id,
            'message': (
                'Connection is established. Webhook reconciliation job #%d '
                'was queued; setup remains incomplete until Shopify '
                'subscription read-back proof is recorded.' % job.id
            ),
        }

    @api.model
    def _activation_preflight(self, store, settings):
        """Refuse impossible offline-token webhook setup before activation."""
        gate = self._webhook_client_secret_gate(store)
        if gate:
            settings.sudo().write({
                'setup_wizard_step_key': 'review',
                'setup_wizard_step': SETUP_STEP_COUNT,
            })
            return {
                'allowed': False,
                'code': gate['code'],
                'message': gate['message'],
            }
        return {'allowed': True}

    @api.model
    def _activation_completion_guard(self, store, settings):
        """Revalidate lifecycle, credential and webhook proof under locks."""
        if not super()._activation_completion_guard(store, settings):
            return False
        locked_state, locked_generation = store._lock_store_for_lifecycle()
        Credential = self.env['shopify.connector.store.credential']
        credential_version = Credential._lifecycle_credential_version(
            store, lock=True,
        )
        store.invalidate_recordset()
        settings.invalidate_recordset()
        if locked_state != 'connected' or not credential_version:
            return False
        job = self._setup_reconciliation_job(store)
        if not job or job.state != 'succeeded':
            return False
        if job.expected_connection_generation != locked_generation:
            return False
        # This is a local read of persisted Shopify subscription evidence.  The
        # lifecycle and credential rows remain locked until core writes the
        # completion timestamp, so a disconnect/reconnect or credential
        # replacement cannot invalidate the proof between this check and that
        # write.
        status = self._webhook_setup_status(store, settings)
        return status['state'] == 'ready_to_complete'

    @api.model
    def _store_payload(self, store, settings):
        payload = super()._store_payload(store, settings)
        status = self._webhook_setup_status(store, settings)
        payload.update({
            'setup_completion_state': status['state'],
            'setup_completion_code': status.get('code', False),
            'setup_completion_message': status['message'],
            'setup_completion_job_id': status['job_id'],
        })
        return payload
