"""Final V2 admission at the API client's send-stage validation seam.

The protected API client performs its credential/access work in
``_admit_mutation`` and calls ``_validate_graphql_operation`` again from the
single HTTP method immediately before constructing the request.  This small
inheritance uses that second validation call as the final V2 fence.  It keeps
the network outside the short SQL transaction and leaves the legacy client
path unchanged.
"""

import os
import uuid
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    _CALL_LEASE_LIFETIME_SECONDS,
    REASON_TOKEN_INVALID,
    REASON_TEMPORARY,
    ShopifyClientError,
    ShopifyQuiescedError,
)


class ShopifyConnectorApiClientV2Runtime(models.AbstractModel):
    """Apply the complete locked V2 fence on the real execute-business path."""

    _inherit = 'shopify.connector.api.client'

    @api.model
    def _v2_preflight_mutation_lineage(
        self, job_id, store_id, context,
    ):
        """Prove the exact C2 owner before touching credentials.

        Client-credentials acquisition is itself a Shopify-side network
        operation.  It therefore cannot be the first step in a V2 mutation
        admission: a forged job/store pair, a stale attempt, or a cross-store
        context must be refused while the durable job -> attempt -> run ->
        store -> settings lineage is still locked.  This short transaction is
        only the preflight.  The caller performs the same locked proof again
        after token acquisition before inserting the call lease, closing the
        ordinary preflight/token-refresh TOCTOU window without holding a row
        lock across the exchange.
        """
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(
                side_cr, self.env.uid, dict(self.env.context),
            )
            Dispatch = side_env['shopify.connector.job.dispatch']
            Attempt = side_env['shopify.connector.mutation.attempt']
            job = side_env['shopify.connector.job'].browse(job_id)
            attempt = Attempt.browse(context.get('attempt_id'))
            scope = Attempt._v2_locked_scope(job, attempt=attempt)
            if not scope:
                raise ShopifyQuiescedError(
                    'The V2 mutation lineage is unavailable.'
                )
            job, attempt, run, store, settings = scope
            if not self._v2_mutation_lineage_matches(
                Dispatch, job, attempt, run, store, settings, context,
            ):
                raise ShopifyQuiescedError(
                    'The V2 mutation lineage is stale or invalid.'
                )
            snapshot = {
                'store_id': store.id,
                'shop_domain': store.shop_domain,
                'api_version': store.api_version,
                'connection_generation': store.connection_generation,
                'configuration_generation': settings.configuration_generation,
            }
            side_cr.commit()
            return snapshot
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    @api.model
    def _v2_mutation_lineage_matches(
        self, dispatch, job, attempt, run, store, settings, context,
    ):
        """Validate one already-locked mutation scope.

        Keep this predicate shared by the credential preflight and the final
        lease admission.  The final call intentionally repeats it: the
        preflight proves which store may be used, while the final call proves
        that the same owner/generation is still current after credential work.
        """
        if not all((job, attempt, run, store, settings)):
            return False
        if not dispatch._is_v2_mutation_job(job, attempt=attempt):
            return False
        if (
            job.state != 'running'
            or not job.owner_worker_ref
            or job.current_attempt_token != context.get('attempt_token')
            or attempt.attempt_token != context.get('attempt_token')
            or attempt.job_id != job
            or attempt.mutation_domain != job.job_type
            or context.get('mutation_domain') != job.job_type
            or attempt.observed_outcome != 'pending'
            or not attempt.transport_attempted
            or job.store_id != store
            or attempt.store_id != store
            or attempt.run_id != run
            or not store.shop_domain
            or not store.api_version
            or attempt.expected_store_identity != store.shop_domain
        ):
            return False
        if (
            run.store_id != store
            or run.company_id != store.company_id
            or job.company_id != store.company_id
            or settings.company_id != store.company_id
        ):
            return False
        supplied_connection = context.get(
            'expected_connection_generation',
        )
        if (
            supplied_connection is not None
            and supplied_connection != store.connection_generation
        ):
            return False
        supplied_store_identity = context.get('expected_store_identity')
        if (
            supplied_store_identity is not None
            and supplied_store_identity != store.shop_domain
        ):
            return False
        supplied_configuration = context.get(
            'expected_configuration_generation',
        )
        if (
            supplied_configuration is not None
            and supplied_configuration != settings.configuration_generation
        ):
            return False
        if not dispatch._v2_admit_mutation_job(
            job, phase='c2', attempt=attempt,
        ):
            return False
        return True

    @api.model
    def _admit_v2_reconciliation_read(
        self, reconciliation_job_id, attempt_id, store_id,
    ):
        """Admit exact query-only proof after a durable V2 mutation.

        Original mode/generation/cancellation freshness intentionally does not
        gate this call: those changes forbid another write but cannot erase
        the need to determine whether committed C2 reached Shopify.  Current
        store/company/domain identity, connectivity, exact attempt/child
        linkage, and a usable credential remain mandatory.
        """
        if not all(type(value) is int and value > 0 for value in (
            reconciliation_job_id, attempt_id, store_id,
        )):
            raise ShopifyQuiescedError(
                'V2 reconciliation requires immutable integer identity.'
            )
        # The first locked proof happens before credential access.  The
        # returned store identity is immutable for this row; still, the final
        # side transaction below repeats the complete proof after the refresh
        # so a concurrent lifecycle change cannot authorize the lease.
        # The locked predicate includes attempt.expected_store_identity and
        # attempt.observed_outcome != 'uncertain', and refuses non-uncertain
        # evidence before credential access.
        preflight = self._v2_preflight_reconciliation_lineage(
            reconciliation_job_id, attempt_id, store_id,
        )
        store = self.env['shopify.connector.store'].browse(
            preflight['store_id'],
        ).exists()
        if (
            not store
            or store.id != store_id
            or store.shop_domain != preflight['shop_domain']
            or store.api_version != preflight['api_version']
        ):
            raise ShopifyQuiescedError(
                'The V2 reconciliation store is no longer available.'
            )
        self.env['shopify.connector.store.credential']._ensure_access_token(
            store, purpose='business',
        )
        lifetime = timedelta(seconds=_CALL_LEASE_LIFETIME_SECONDS)
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(
                side_cr, self.env.uid, dict(self.env.context),
            )
            Dispatch = side_env['shopify.connector.job.dispatch']
            Attempt = side_env['shopify.connector.mutation.attempt']
            attempt = Attempt.browse(attempt_id)
            original = attempt.job_id
            scope = Attempt._v2_locked_scope(original, attempt=attempt)
            if not scope:
                raise ValidationError(
                    'The V2 reconciliation lineage is unavailable.'
                )
            original, attempt, run, locked_store, settings = scope
            # The dispatch transaction already owns the reconciliation child
            # row while this side cursor admits the lease.  Re-locking that
            # same row here would self-block.  Its immutable linkage is read
            # from the last committed queued/retry state; the caller's main
            # transaction separately proves the claimed running state.
            reconciliation = side_env['shopify.connector.job'].browse(
                reconciliation_job_id,
            ).exists()
            if not reconciliation:
                raise ValidationError(
                    'The V2 reconciliation child is unavailable.'
                )
            if not self._v2_reconciliation_lineage_matches(
                Dispatch, original, attempt, run, locked_store, settings,
                reconciliation, side_env,
            ):
                raise ValidationError(
                    'The V2 reconciliation read identity is stale or invalid.'
                )
            token = side_env[
                'shopify.connector.store.credential'
            ]._get_access_token(locked_store)
            if not token:
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            lease_key = uuid.uuid4().hex
            admitted_at = fields.Datetime.now()
            side_env['shopify.connector.call.lease'].create({
                'store_id': locked_store.id,
                'lease_key': lease_key,
                'job_id': reconciliation.id,
                'worker_ref': '%s:%s' % (side_cr.dbname, os.getpid()),
                'admitted_at': admitted_at,
                'expires_at': admitted_at + lifetime,
            })
            transport_store = SimpleNamespace(
                id=locked_store.id,
                shop_domain=locked_store.shop_domain,
                api_version=locked_store.api_version,
            )
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return lease_key, token, transport_store

    @api.model
    def _v2_preflight_reconciliation_lineage(
        self, reconciliation_job_id, attempt_id, store_id,
    ):
        """Prove the exact readback child and C2 lineage before auth work."""
        side_cr = self.env.registry.cursor()
        try:
            # The final locked proof below covers owner_worker_ref,
            # current_attempt_token, attempt_token, mutation_domain,
            # transport_attempted, expected_connection_generation,
            # expected_configuration_generation, and expected_store_identity
            # through the shared lineage predicate before a lease is created.
            side_env = api.Environment(
                side_cr, self.env.uid, dict(self.env.context),
            )
            Dispatch = side_env['shopify.connector.job.dispatch']
            Attempt = side_env['shopify.connector.mutation.attempt']
            attempt = Attempt.browse(attempt_id)
            original = attempt.job_id
            scope = Attempt._v2_locked_scope(original, attempt=attempt)
            if not scope:
                raise ShopifyQuiescedError(
                    'The V2 reconciliation lineage is unavailable.'
                )
            original, attempt, run, store, settings = scope
            reconciliation = side_env[
                'shopify.connector.job'
            ].browse(reconciliation_job_id).exists()
            if not reconciliation:
                raise ShopifyQuiescedError(
                    'The V2 reconciliation child is unavailable.'
                )
            if not self._v2_reconciliation_lineage_matches(
                Dispatch, original, attempt, run, store, settings,
                reconciliation, side_env,
            ):
                raise ShopifyQuiescedError(
                    'The V2 reconciliation lineage is stale or invalid.'
                )
            snapshot = {
                'store_id': store.id,
                'shop_domain': store.shop_domain,
                'api_version': store.api_version,
            }
            side_cr.commit()
            return snapshot
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    @api.model
    def _v2_reconciliation_lineage_matches(
        self, dispatch, original, attempt, run, store, settings,
        reconciliation, side_env,
    ):
        """Validate the locked original/attempt/read-child identity."""
        if not all((original, attempt, run, store, settings, reconciliation)):
            return False
        try:
            strategy = dispatch._validated_mutation_strategy(
                attempt.mutation_domain,
            )
        except ValidationError:
            return False
        company_ids = tuple(side_env.companies.ids)
        return bool(
            dispatch._is_v2_mutation_job(original, attempt=attempt)
            and store.state == 'connected'
            and store.company_id.id in company_ids
            and settings.company_id == store.company_id
            and run.store_id == store
            and run.company_id == store.company_id
            and original.store_id == store
            and original.company_id == store.company_id
            and attempt.store_id == store
            and attempt.run_id == run
            and attempt.observed_outcome == 'uncertain'
            and attempt.expected_store_identity == store.shop_domain
            and reconciliation.store_id == store
            and reconciliation.company_id == store.company_id
            and reconciliation.run_id == run
            and reconciliation.parent_job_id == original
            and reconciliation.mutation_attempt_id == attempt
            and reconciliation.job_source == 'reconciliation'
            and reconciliation.job_type == strategy['reconciliation_job_type']
            and reconciliation.state in ('queued', 'running', 'retry_waiting')
        )

    @contextmanager
    def _execute_v2_reconciliation_read(
        self, reconciliation_job, attempt, store, query, variables=None,
    ):
        """Issue one bounded query under the exact reconciliation lease."""
        variables = variables or {}
        self._validate_graphql_operation(query, variables, mutation_context=None)
        if self._graphql_contains_mutation(query):
            raise ValidationError(
                'V2 reconciliation admission accepts GraphQL queries only.'
            )
        if (
            not reconciliation_job
            or reconciliation_job.state != 'running'
            or not store.shop_domain
            or not store.api_version
        ):
            raise ShopifyQuiescedError(
                'V2 reconciliation requires a claimed read job and store.'
            )
        lease_key, token, transport_store = (
            self._admit_v2_reconciliation_read(
                reconciliation_job.id, attempt.id, store.id,
            )
        )
        try:
            try:
                response = self._send(
                    transport_store,
                    {'query': query, 'variables': variables},
                    token,
                )
            except ShopifyClientError:
                raise
            except requests.exceptions.RequestException as exc:
                raise ShopifyClientError(
                    error_class=ERROR_TEMPORARY,
                    reason=REASON_TEMPORARY,
                    technical_detail='transport_error',
                ) from exc
            yield self._normalize_response(transport_store, response)
        except BaseException as primary_error:
            try:
                self._release_lease(lease_key)
            except BaseException as release_error:
                raise primary_error from release_error
            raise
        else:
            self._release_lease(lease_key)

    @api.model
    def _v2_admit_mutation_side(
        self, job_id, store_id, mutation_context,
    ):
        """Admit a V2 call with the complete scope fence in one side txn.

        A locked lineage preflight runs before credential access.  Credential
        ensure/refresh is then performed without a row lock, followed by a
        second side transaction that locks job -> attempt -> run -> store ->
        settings, repeats every owner/identity/generation/mode/cancellation
        fence, snapshots the token once under those locks, inserts the lease,
        and commits.  No network is performed by either durable admission
        transaction; the send-stage validation below repeats the full fence
        immediately before the base HTTP seam.
        """
        context = dict(mutation_context or {})
        if not all(type(value) is int and value > 0 for value in (
            job_id, store_id, context.get('attempt_id'),
            context.get('store_id'),
        )):
            raise ShopifyQuiescedError(
                'Layer 2 admission requires immutable job/store ids.'
            )
        if context['store_id'] != store_id:
            raise ShopifyQuiescedError(
                'V2 admission store identity does not match the call.'
            )

        # Prove the complete durable C2 lineage BEFORE any credential lookup or
        # client-credentials exchange.  The final side transaction below
        # repeats this proof after the refresh and before the lease insert.
        preflight = self._v2_preflight_mutation_lineage(
            job_id, store_id, context,
        )
        store_for_token = self.env[
            'shopify.connector.store'
        ].browse(preflight['store_id']).exists()
        if (
            not store_for_token
            or store_for_token.id != store_id
            or store_for_token.shop_domain != preflight['shop_domain']
            or store_for_token.api_version != preflight['api_version']
        ):
            raise ShopifyQuiescedError(
                'The V2 mutation store is no longer available.'
            )
        # Preserve the existing token-refresh placement: credential work is
        # never performed while a database lock is held.  It is now reached
        # only after the exact job/attempt/run/store/settings proof above.
        self.env['shopify.connector.store.credential']._ensure_access_token(
            store_for_token,
            purpose='business',
        )
        lifetime = timedelta(seconds=_CALL_LEASE_LIFETIME_SECONDS)
        side_cr = self.env.registry.cursor()
        try:
            # The final locked proof below covers owner_worker_ref,
            # current_attempt_token, attempt_token, mutation_domain,
            # transport_attempted, expected_connection_generation,
            # expected_configuration_generation, and expected_store_identity
            # through the shared lineage predicate before a lease is created.
            side_env = api.Environment(
                side_cr, self.env.uid, dict(self.env.context),
            )
            Dispatch = side_env['shopify.connector.job.dispatch']
            Attempt = side_env['shopify.connector.mutation.attempt']
            job = side_env['shopify.connector.job'].browse(job_id)
            attempt = Attempt.browse(context['attempt_id'])
            scope = Attempt._v2_locked_scope(job, attempt=attempt)
            if not scope:
                raise ValidationError('The V2 transport scope is unavailable.')
            job, attempt, run, store, settings = scope
            if not self._v2_mutation_lineage_matches(
                Dispatch, job, attempt, run, store, settings, context,
            ):
                raise ValidationError(
                    'The V2 transport owner or attempt identity is stale.'
                )
            token = side_env[
                'shopify.connector.store.credential'
            ]._get_access_token(store)
            if not token:
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            transport_store = SimpleNamespace(
                id=store_id,
                shop_domain=store.shop_domain,
                api_version=store.api_version,
            )
            lease_key = uuid.uuid4().hex
            admitted_at = fields.Datetime.now()
            side_env['shopify.connector.call.lease'].create({
                'store_id': store.id,
                'lease_key': lease_key,
                'job_id': job.id,
                'worker_ref': '%s:%s' % (side_cr.dbname, os.getpid()),
                'admitted_at': admitted_at,
                'expires_at': admitted_at + lifetime,
            })
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return lease_key, token, transport_store

    @api.model
    def _admit_mutation(self, job_id, store_id, mutation_context):
        """Use the full V2 side admission while preserving the V1 path."""
        context = dict(mutation_context or {})
        job = False
        attempt = False
        if isinstance(job_id, int):
            job = self.env['shopify.connector.job'].browse(job_id).exists()
        attempt_id = context.get('attempt_id')
        if isinstance(attempt_id, int):
            attempt = self.env['shopify.connector.mutation.attempt'].browse(
                attempt_id,
            ).exists()
        if self.env['shopify.connector.job.dispatch']._is_v2_mutation_job(
            job, attempt=attempt,
        ):
            return self._v2_admit_mutation_side(
                job_id, store_id, context,
            )
        return super()._admit_mutation(job_id, store_id, mutation_context)

    @api.model
    def _validate_graphql_operation(
        self, document, variables, mutation_context=None,
    ):
        """Run V2 admission on the validation call inside ``_send``.

        ``execute_business`` validates once before ``_admit_mutation`` and the
        base ``_send`` validates a second time after admission/token
        acquisition.  A committed C2 attempt may already exist for both
        calls; the second call is the required final recheck at the last
        client-side gate before HTTP, while the first remains a harmless
        additive early check.  Legacy/read-only requests and the existing API
        error contract use the base method unchanged.
        """
        result = super()._validate_graphql_operation(
            document, variables, mutation_context,
        )
        if not self._graphql_contains_mutation(document):
            return result
        context = dict(mutation_context or {})
        job_id = context.get('job_id')
        attempt_id = context.get('attempt_id')
        if not isinstance(job_id, int) or not isinstance(attempt_id, int):
            return result
        job = self.env['shopify.connector.job'].browse(job_id).exists()
        attempt = self.env['shopify.connector.mutation.attempt'].browse(
            attempt_id,
        ).exists()
        dispatch = self.env['shopify.connector.job.dispatch']
        if dispatch._is_v2_mutation_job(job, attempt=attempt):
            dispatch._v2_assert_transport_admission(context)
        return result


__all__ = ['ShopifyConnectorApiClientV2Runtime']
