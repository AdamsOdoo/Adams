"""Odoo service/model seams for the bounded V2 read-only runtime.

The repository implementation is kept in
shopify_connector_v2_runtime_repository.py.  This module remains the stable
import surface for the Odoo service and legacy dispatcher extensions.
"""

from datetime import datetime
import os

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..runtime.p10_capacity import reserve_capacity_after_v2
from ..runtime.p10_coordinator import (
    ReadOnlyCoordinator,
    ReadOnlyHandlerRegistry,
    ReadOnlyHandlerSpec,
    RuntimeBoundaryError,
)
from ..runtime.contracts import Succeeded
from .shopify_connector_job_dispatch import (
    DRAIN_BATCH_SIZE_MAX,
    DRAIN_BATCH_SIZE_MIN,
)
from .shopify_connector_v2_runtime_common import (
    V2_MAX_CLAIM_BATCH,
    V2_RUNTIME_MODE,
    _ACTIVE_RUN_STATES,
    _UTC,
    _TRANSITION_MESSAGE_LIMIT,
    _positive_limit,
    _safe_transition_message,
    _utc,
    _worker,
    V2RuntimeClaimLost,
    V2_READ_ONLY_RUNTIME_MODES,
    runtime_mode_includes,
)
from .shopify_connector_v2_runtime_repository import (
    OdooReadOnlyRuntimeRepository,
)


# Caller-owned fields for the public read-only admission seam.  Runtime
# identity, lifecycle, and generation fields are always derived below before
# the sudoed ORM create; accepting an arbitrary ``dict`` here would turn that
# sudo into a protected-field bypass.
_READ_ONLY_ENQUEUE_FIELDS = frozenset((
    'job_type', 'job_source', 'payload_hash',
    'res_model', 'res_id', 'shopify_target_gid',
    'parent_job_id', 'sequence',
    'lane', 'lane_priority', 'available_at',
))

class ShopifyConnectorV2Runtime(models.AbstractModel):
    """Named, administrator-gated V2 runtime service."""

    _name = 'shopify.connector.v2.runtime'
    _description = 'Shopify Connector V2 Read-only Runtime'

    @api.model
    def _assert_runtime_actor(self):
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may run V2 runtime work.'
            )

    @api.model
    def _worker_ref(self):
        return _worker('worker:odoo:%d:%d' % (os.getpid(), self.env.uid))

    @api.model
    def _extend_v2_read_only_handler_specs(self):
        """Return additive domain-owned read specs.

        A domain addon overrides this method, calls ``super()``, and appends
        explicit ``ReadOnlyHandlerSpec`` values.  Core intentionally does not
        import product/sale/other domain modules.  Until a claim-fenced
        transport adapter is available, extensions must remain local-only;
        the coordinator does not make network calls or hold a database lock
        around one.
        """
        return ()

    @api.model
    def _get_v2_read_only_handler_specs(self):
        """Return the bounded core registry plus additive domain specs."""
        specs = (
            ReadOnlyHandlerSpec(
                'core_dispatch_selftest',
                self._handle_core_dispatch_selftest,
                operation_kind='diagnostic',
                allowed_workflows=('core',),
                allowed_operations=(
                    'core_dispatch_selftest',
                    'runtime.concurrency',
                    'runtime.schema.read',
                ),
            ),
        )
        additions = self._extend_v2_read_only_handler_specs()
        if not isinstance(additions, (tuple, list)):
            raise RuntimeBoundaryError(
                'V2 read-only handler extensions must be a bounded sequence.'
            )
        if len(specs) + len(additions) > V2_MAX_CLAIM_BATCH:
            raise RuntimeBoundaryError(
                'V2 read-only handler registration exceeds its bound.'
            )
        return specs + tuple(additions)

    @api.model
    def _handle_core_dispatch_selftest(self, claim):
        del claim
        return Succeeded({'handler': 'core_dispatch_selftest'})

    @api.model
    def _finalize_v2_read_result(self, *, job, run, claim, result):
        """Domain hook after terminal/scheduled state is flushed.

        Extensions may admit bounded local follow-up work in the same short
        finalization transaction.  They must not perform network I/O or alter
        the finalized parent/attempt evidence.
        """
        del job, run, claim, result
        return None

    @api.model
    def _handler_registry(self):
        specs = self._get_v2_read_only_handler_specs()
        if not isinstance(specs, (tuple, list)):
            raise RuntimeBoundaryError(
                'V2 read-only handler registration must be a bounded sequence.'
            )
        return ReadOnlyHandlerRegistry(tuple(specs))

    @api.model
    def run_v2_read_only(self, *, limit=V2_MAX_CLAIM_BATCH, now=None):
        """Run one bounded V2 pass; handlers execute after committed claims."""
        self._assert_runtime_actor()
        limit = _positive_limit(limit)
        now = _utc(now or datetime.now(_UTC))
        coordinator = ReadOnlyCoordinator(
            repository=OdooReadOnlyRuntimeRepository(self.env),
            handlers=self._handler_registry(),
            worker_ref=self._worker_ref(),
            max_batch=V2_MAX_CLAIM_BATCH,
        )
        return coordinator.run_once(now=now, limit=limit).as_dict()

    @api.model
    def _has_read_only_store(self):
        self._assert_runtime_actor()
        return bool(self.env[
            'shopify.connector.store.settings'
        ].search_count([(
            'v2_runtime_mode', 'in', V2_READ_ONLY_RUNTIME_MODES,
        )]))

    @api.model
    def enqueue_read_only_job(self, run, values):
        """Admit one explicit read-only job with both generation snapshots."""
        self._assert_runtime_actor()
        if not isinstance(values, dict):
            raise ValidationError('Read-only job values must be a mapping.')
        if any(type(key) is not str for key in values):
            raise ValidationError('Read-only job field names must be strings.')
        if not run or not run.exists() or run._name != 'shopify.connector.run':
            raise ValidationError('A valid V2 run is required.')
        run.ensure_one()
        if run.state not in _ACTIVE_RUN_STATES:
            raise ValidationError('A V2 job requires an admitted active run.')
        if run.cancel_requested_at:
            raise ValidationError(
                'A cancelled V2 run cannot admit additional read work.'
            )
        store = run.store_id
        if (
            not store
            or not store.company_id
            or store.company_id.id != self.env.company.id
        ):
            raise AccessError(
                'Read-only admission is restricted to the active company.'
            )
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if (
            not settings
            or not runtime_mode_includes(
                settings.v2_runtime_mode, V2_RUNTIME_MODE,
            )
            or store.state != 'connected'
        ):
            raise ValidationError(
                'Read-only admission requires a connected store in read_only mode.'
            )
        if (
            run.company_id != store.company_id
            or settings.company_id != store.company_id
        ):
            raise ValidationError('The run and store company must match.')
        if (
            run.expected_connection_generation != store.connection_generation
            or run.expected_configuration_generation
            != settings.configuration_generation
        ):
            raise ValidationError(
                'The V2 run snapshot is stale; reload before admitting work.'
            )
        job_type = values.get('job_type')
        registry = self._handler_registry()
        try:
            spec = registry.require(job_type)
        except LookupError as exc:
            raise ValidationError(
                'The read-only handler is not registered.'
            ) from exc
        if not spec.allows(run.workflow, run.operation):
            raise ValidationError(
                'The read-only handler is not authorized for this run operation.'
            )
        unknown = sorted(set(values) - _READ_ONLY_ENQUEUE_FIELDS)
        if unknown:
            raise AccessError(
                'Read-only admission received unsupported fields: %s.'
                % ', '.join(unknown)
            )
        forbidden = {
            'mutation_attempt_id', 'current_attempt_token',
            'owner_worker_ref', 'running_since', 'state', 'run_id',
            'expected_connection_generation',
            'expected_configuration_generation',
        }
        if forbidden.intersection(values):
            raise AccessError(
                'Read-only admission owns runtime identity and lifecycle fields.'
            )
        vals = dict(values)
        parent_id = vals.get('parent_job_id')
        if parent_id:
            parent = self.env['shopify.connector.job'].sudo().browse(
                parent_id,
            ).exists()
            if (
                not parent
                or parent.store_id != store
                or parent.run_id != run
            ):
                raise ValidationError(
                    'A V2 read-only parent must belong to the same run and store.'
                )
        vals.update({
            'run_id': run.id,
            'store_id': store.id,
            'state': 'queued',
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation': settings.configuration_generation,
            'lane': vals.get('lane') or 'interactive',
            'lane_priority': vals.get('lane_priority', 100),
            'available_at': vals.get('available_at') or fields.Datetime.now(),
        })
        if vals.get('mutation_attempt_id'):
            raise AccessError('Mutation work cannot enter the read-only runtime.')
        job = self.env['shopify.connector.job'].sudo().create(vals)
        cron = self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger()
        return job

    @api.model
    def run_stale_owner_sweep(self, *, limit=V2_MAX_CLAIM_BATCH, now=None):
        self._assert_runtime_actor()
        return OdooReadOnlyRuntimeRepository(self.env).sweep_stale_read_only(
            limit=limit, now=now,
        )


class ShopifyConnectorJobDispatchV2(models.AbstractModel):
    """Route the existing drain seam while excluding V2 rows from legacy."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _claimable_domain(self, now=False, exclude_store_ids=()):
        domain = super()._claimable_domain(
            now=now, exclude_store_ids=exclude_store_ids,
        )
        # V2 read-only work uses the side-cursor repository above.  V2
        # mutation work uses the established Layer-2 dispatcher, but only
        # after a domain addon explicitly registers its job type.  Keep the
        # legacy branch in the same predicate so unregistered/legacy rows can
        # never fall through to a V2 handler.
        v2_types = tuple(sorted(self._get_v2_job_types()))
        if not v2_types:
            return domain + [('run_id', '=', False)]
        return domain + [
            '|',
            ('run_id', '=', False),
            '&',
            ('run_id', '!=', False),
            ('job_type', 'in', v2_types),
        ]

    @api.model
    def run_drain(self, limit=None):
        if limit is None:
            cap = self._resolve_drain_batch_size()
        elif (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < DRAIN_BATCH_SIZE_MIN
            or limit > DRAIN_BATCH_SIZE_MAX
        ):
            return super().run_drain(limit=limit)
        else:
            cap = limit
        Runtime = self.env['shopify.connector.v2.runtime']
        v2_processed = 0
        remaining = cap
        if Runtime._has_read_only_store():
            v2_report = Runtime.run_v2_read_only(
                limit=min(cap, V2_MAX_CLAIM_BATCH),
            )
            # Capacity is consumed when a handler is admitted/executed, not
            # only when its finalization succeeds.  If a finalization boundary
            # is delayed or fails, handing the whole unused ``finalized``
            # count to legacy work would exceed the configured per-pass
            # request/work budget and could starve V2 evidence recovery.
            remaining, v2_processed = reserve_capacity_after_v2(cap, v2_report)
        if remaining <= 0:
            return v2_processed
        return v2_processed + super().run_drain(limit=remaining)


class ShopifyConnectorStaleOwnerSweepV2(models.AbstractModel):
    """Use the existing stale-owner cron for both runtime generations."""

    _inherit = 'shopify.connector.stale.owner.sweep'

    @api.model
    def run_sweep(self):
        v2_count = self.env[
            'shopify.connector.v2.runtime'
        ].run_stale_owner_sweep()
        # The legacy sweep is guarded to run_id IS NULL by the additive
        # compatibility clause in its existing model, so it cannot rewrite a
        # V2 attempt as a Layer-2 mutation result.
        return v2_count + super().run_sweep()


__all__ = [
    'OdooReadOnlyRuntimeRepository',
    'ShopifyConnectorV2Runtime',
    'V2RuntimeClaimLost',
]
