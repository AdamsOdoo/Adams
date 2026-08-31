"""P10 product-scan admission and runtime finalization seams."""

import hashlib
import uuid

from psycopg2 import IntegrityError

from odoo import api, models
from odoo.exceptions import UserError

from odoo.addons.shopify_connector_core.domain.runtime_modes import (
    runtime_mode_includes,
)
from odoo.addons.shopify_connector_core.runtime.p10_coordinator import (
    ReadOnlyHandlerSpec,
    RuntimeBoundaryError,
)
from odoo.addons.shopify_connector_core.runtime.contracts import Succeeded

from .shopify_connector_product_scan import PRODUCT_SCAN_TARGET
from .shopify_connector_product_scan_p10 import (
    _PRODUCT_SCAN_HANDLER,
    _TERMINAL_JOB_STATES,
    _cursor,
    _db_utc,
    _is_unique_violation,
    _job_matches_expected,
    _record_id,
)


def _continuation_job_matches(
    winner, *, job, run, claim, sequence, payload_hash, lane, lane_priority,
):
    """Prove that a duplicate row is this exact continuation.

    A run/parent/sequence hit alone is not enough: a malformed or unrelated
    row must never turn a failed continuation insert into apparent progress.
    Keep the checks explicit because this is the recovery path after a rolled
    back unique-violation savepoint.
    """
    store_id = _record_id(getattr(run, 'store_id', None))
    claim_store_id = getattr(claim, 'store_id', None)
    expected_generation = getattr(claim, 'expected_generation', None)
    expected_configuration_generation = getattr(
        claim, 'expected_configuration_generation', None,
    )
    claim_payload = getattr(claim, 'payload', None)
    if not hasattr(claim_payload, 'get'):
        return False
    claim_job_type = claim_payload.get('job_type')
    claim_operation = claim_payload.get('operation')
    claim_res_model = claim_payload.get('res_model')
    claim_res_id = claim_payload.get('res_id')
    claim_target_gid = claim_payload.get('shopify_target_gid')
    if store_id != claim_store_id:
        return False
    if (
        getattr(claim, 'job_id', None) != _record_id(job)
        or getattr(claim, 'run_id', None) != _record_id(run)
        or getattr(claim, 'handler_key', None) != _PRODUCT_SCAN_HANDLER
        or claim_job_type != _PRODUCT_SCAN_HANDLER
        or claim_operation != 'product.import.scan'
    ):
        return False
    if not _job_matches_expected(
        job,
        store_id=claim_store_id,
        job_type=claim_job_type,
        res_model=claim_res_model,
        res_id=claim_res_id,
        target_gid=claim_target_gid,
        check_payload=False,
    ):
        return False
    if not _job_matches_expected(
        winner,
        store_id=claim_store_id,
        job_type=claim_job_type,
        res_model=claim_res_model,
        res_id=claim_res_id,
        target_gid=claim_target_gid,
        payload_hash=payload_hash,
    ):
        return False
    return bool(
        # Run and parent lineage must be exact, not merely same sequence.
        _record_id(getattr(job, 'run_id', None)) == _record_id(run)
        and _record_id(getattr(winner, 'run_id', None)) == _record_id(run)
        and _record_id(getattr(winner, 'parent_job_id', None))
        == _record_id(job)
        and getattr(winner, 'sequence', None) == sequence
        and getattr(job, 'job_type', None) == _PRODUCT_SCAN_HANDLER
        # The run itself must still describe this product scan operation.
        and getattr(run, 'workflow', None) == 'product'
        and getattr(run, 'operation', None) == 'product.import.scan'
        and claim_operation == getattr(run, 'operation', None)
        # All rows must remain in the claimed company/store scope.
        and _record_id(getattr(run, 'company_id', None))
        == getattr(claim, 'company_id', None)
        and _record_id(getattr(job, 'company_id', None))
        == getattr(claim, 'company_id', None)
        and _record_id(getattr(winner, 'company_id', None))
        == getattr(claim, 'company_id', None)
        and _record_id(getattr(job, 'store_id', None)) == claim_store_id
        and _record_id(getattr(winner, 'store_id', None)) == claim_store_id
        # Connection and configuration generations are both part of the
        # admitted identity and must match the immutable claim snapshot.
        and getattr(run, 'expected_connection_generation', None)
        == expected_generation
        and getattr(job, 'expected_connection_generation', None)
        == expected_generation
        and getattr(winner, 'expected_connection_generation', None)
        == expected_generation
        and getattr(run, 'expected_configuration_generation', None)
        == expected_configuration_generation
        and getattr(job, 'expected_configuration_generation', None)
        == expected_configuration_generation
        and getattr(winner, 'expected_configuration_generation', None)
        == expected_configuration_generation
        # Scheduling lineage is copied exactly from the parent.
        and getattr(winner, 'lane', None) == lane
        and getattr(winner, 'lane_priority', None) == lane_priority
    )


class ShopifyConnectorStoreProductScanP10(models.Model):
    """Route only cumulative read-only stores into P10 admission."""

    _inherit = 'shopify.connector.store'

    @api.model
    def _p10_product_settings(self, store):
        return self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)

    @api.model
    def _p10_runtime_enabled(self, store):
        settings = self._p10_product_settings(store)
        return bool(
            settings
            and 'v2_runtime_mode' in settings._fields
            and runtime_mode_includes(settings.v2_runtime_mode, 'read_only')
        )

    @api.model
    def _exact_active_product_scan(self):
        """Return only a matching active scan, never an arbitrary job row."""
        self.ensure_one()
        expected = {
            'store_id': self.id,
            'job_type': _PRODUCT_SCAN_HANDLER,
            'res_model': self._name,
            'res_id': self.id,
            'target_gid': PRODUCT_SCAN_TARGET,
        }
        winner = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.id),
            ('job_type', '=', _PRODUCT_SCAN_HANDLER),
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('shopify_target_gid', '=', PRODUCT_SCAN_TARGET),
            ('state', 'not in', tuple(_TERMINAL_JOB_STATES)),
        ], order='id asc', limit=1)
        if not winner or not _job_matches_expected(winner, **expected):
            return False
        if getattr(winner, 'state', None) in _TERMINAL_JOB_STATES:
            return False
        return winner

    @api.model
    def _enqueue_v2_product_scan(self, source, settings):
        self.ensure_one()
        if self.state != 'connected':
            raise UserError('Only a connected store can start a product import.')
        if not settings or not settings.product_domain_enabled:
            raise UserError('The product domain is not enabled for this store.')
        if settings.product_first_sync_source == 'odoo_source':
            raise UserError(
                'This store imports no products: its first sync direction is '
                'Odoo as the source.',
            )
        active = self._exact_active_product_scan()
        if active:
            return active

        request_key = 'v2-product-scan:%s:%s' % (self.id, uuid.uuid4())
        trigger = 'user' if source == 'manual_sync' else 'cron'
        Run = self.env['shopify.connector.run']
        try:
            with self.env.cr.savepoint():
                run = Run._create_service({
                    'store_id': self.id,
                    'request_key': request_key,
                    'workflow': 'product',
                    'operation': 'product.import.scan',
                    'trigger': trigger,
                    # Run evidence requires an actor for both interactive and
                    # scheduled requests.  The cron caller is the actor for
                    # the scheduled admission; it is not a reason to bypass
                    # the run service's caller-identity check.
                    'actor_uid': self.env.uid,
                    'scope_summary': 'Shopify product catalog scan',
                    'configuration_snapshot': {
                        'runtime_mode': settings.v2_runtime_mode,
                        'configuration_generation': settings.configuration_generation,
                        'product_first_sync_source': settings.product_first_sync_source,
                    },
                    'expected_connection_generation': self.connection_generation,
                    'expected_configuration_generation': settings.configuration_generation,
                })
                run._admit_service()
                return self.env[
                    'shopify.connector.v2.runtime'
                ].sudo().enqueue_read_only_job(run, {
                    'job_type': _PRODUCT_SCAN_HANDLER,
                    'job_source': source,
                    'payload_hash': request_key,
                    'res_model': self._name,
                    'res_id': self.id,
                    'shopify_target_gid': PRODUCT_SCAN_TARGET,
                    'sequence': 0,
                    'lane': 'interactive' if source == 'manual_sync' else 'scheduled',
                    'lane_priority': 100,
                })
        except IntegrityError as exc:
            # The unique operation scope can race another opener.  Only
            # return an exact active scan after proving SQLSTATE 23505;
            # check/FK/not-null and other integrity failures stay failures.
            if not _is_unique_violation(exc):
                raise
            active = self._exact_active_product_scan()
            if active:
                return active
            raise

    def _enqueue_product_scan(self, job_source):
        self.ensure_one()
        settings = self._p10_product_settings(self)
        if self._p10_runtime_enabled(self):
            return self._enqueue_v2_product_scan(job_source, settings)
        return super()._enqueue_product_scan(job_source)


class ShopifyConnectorV2RuntimeProductScan(models.AbstractModel):
    """Register product scan and admit same-run bounded successors."""

    _inherit = 'shopify.connector.v2.runtime'

    @api.model
    def _extend_v2_read_only_handler_specs(self):
        specs = tuple(super()._extend_v2_read_only_handler_specs())
        return specs + (ReadOnlyHandlerSpec(
            _PRODUCT_SCAN_HANDLER,
            self.env['shopify.connector.product.scan.p10'].handle_claim,
            operation_kind='scan',
            allowed_workflows=('product',),
            allowed_operations=('product.import.scan',),
        ),)

    @api.model
    def _finalize_v2_read_result(self, *, job, run, claim, result):
        super()._finalize_v2_read_result(
            job=job, run=run, claim=claim, result=result,
        )
        if (
            job.job_type != _PRODUCT_SCAN_HANDLER
            or not isinstance(result, Succeeded)
            or not result.observations.get('continuation')
        ):
            return None
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', job.store_id.id)], limit=1)
        if not settings:
            raise RuntimeBoundaryError(
                'The product scan continuation has no settings owner.',
            )
        window_end = _db_utc(
            settings.product_scan_window_end_at,
            'continuation window end',
        )
        cursor = _cursor(
            settings.product_scan_cursor,
            'continuation cursor',
            allow_none=False,
        )
        if settings.product_scan_generation != claim.expected_generation:
            raise RuntimeBoundaryError(
                'The product scan continuation generation is stale.',
            )
        sequence = int(job.sequence or 0) + 1
        continuation_hash = hashlib.sha256(
            ('%s|%s|%s|%s' % (
                run.id, sequence, window_end.isoformat(), cursor,
            )).encode('utf-8')
        ).hexdigest()
        lane_priority = job.lane_priority
        if lane_priority is None or lane_priority is False:
            lane_priority = 100
        values = {
            'job_type': _PRODUCT_SCAN_HANDLER,
            'job_source': job.job_source,
            'payload_hash': continuation_hash,
            'res_model': job.res_model,
            'res_id': job.res_id,
            'shopify_target_gid': job.shopify_target_gid,
            'parent_job_id': job.id,
            'sequence': sequence,
            'lane': job.lane or 'scheduled',
            'lane_priority': lane_priority,
        }
        try:
            with self.env.cr.savepoint():
                self.sudo().enqueue_read_only_job(run, values)
        except IntegrityError as exc:
            # The continuation savepoint has already rolled back.  Only a
            # unique violation may indicate a competing admission; every
            # other IntegrityError must retain its original failure semantics.
            if not _is_unique_violation(exc):
                raise
            existing = self.env['shopify.connector.job'].sudo().search([
                ('run_id', '=', run.id),
                ('parent_job_id', '=', job.id),
                ('sequence', '=', sequence),
                ('job_type', '=', _PRODUCT_SCAN_HANDLER),
                ('store_id', '=', run.store_id.id),
                ('res_model', '=', job.res_model),
                ('res_id', '=', job.res_id),
                ('shopify_target_gid', '=', job.shopify_target_gid),
                ('payload_hash', '=', continuation_hash),
                (
                    'expected_connection_generation', '=',
                    claim.expected_generation,
                ),
                (
                    'expected_configuration_generation', '=',
                    claim.expected_configuration_generation,
                ),
            ], limit=1)
            if existing and _continuation_job_matches(
                existing,
                job=job,
                run=run,
                claim=claim,
                sequence=sequence,
                payload_hash=continuation_hash,
                lane=values['lane'],
                lane_priority=values['lane_priority'],
            ):
                return None
            # Do not report progress for an arbitrary row that happens to
            # share only part of the continuation's identity.
            raise
        return None


__all__ = [
    'ShopifyConnectorStoreProductScanP10',
    'ShopifyConnectorV2RuntimeProductScan',
]
