"""Authoritative read path and durable evidence for inventory webhooks.

The webhook handler is deliberately split from this model.  W1 verifies and
persists the delivery, then the registry admits ``inventory_observation_sync``.
This child job performs one exact InventoryLevel read under the core business
read lease and records only connector evidence.  It never writes stock and it
never enters the outbound inventory service.
"""

from datetime import datetime, timedelta, timezone
import logging
import re

from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    RETRY_MAX_ATTEMPTS,
    RETRY_WINDOW_HOURS,
)
from odoo.addons.shopify_connector_inventory.models.shopify_connector_inventory_service import (
    ERROR_CLASS_CONCURRENCY,
    ERROR_CLASS_DATA_SHAPE,
    ERROR_CLASS_LOCATION_MISSING,
    ERROR_CLASS_STORE_IDENTITY,
    ERROR_CLASS_TEMPORARY,
    ERROR_CLASS_VALIDATION,
    SUBREASON_BINDING_CONFLICT,
)

from .constants import (
    INVENTORY_OBSERVATION_JOB_TYPE,
    INVENTORY_OBSERVATION_SOURCES,
    INVENTORY_OBSERVATION_STATES,
    OBSERVATION_FALLBACK_BATCH,
    OBSERVATION_FALLBACK_MAX_BATCH,
    OBSERVATION_FALLBACK_STORE_LIMIT,
    OUTBOUND_INVENTORY_JOB_TYPES,
    fallback_payload_hash,
    observation_payload_hash,
)


_logger = logging.getLogger(__name__)

_OBSERVATION_SERVICE_CONTEXT = 'shopify_connector_inventory_observation_service'
_OBSERVATION_SERVICE_SENTINEL = object()
_CRON_CONTEXT_SENTINEL = object()


# RFC3339 is deliberately narrower than ``fields.Datetime.to_datetime``.
# Shopify's timestamps are remote authority; accepting a naive value here
# would make the comparison depend on the Odoo/server timezone.  The
# authoritative quantity timestamp is therefore required to contain an
# explicit ``Z`` or numeric offset and is normalized to Odoo's naive-UTC
# convention only after that requirement has been proven.
_RFC3339_TIMESTAMP = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    # W1 admits Shopify's documented nanosecond precision. Python/Odoo
    # retain the representable first six digits, while the shape still
    # rejects arbitrary precision and every timezone-less value.
    r'(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$'
)

_POSITIVE_DECIMAL = r'[1-9]\d*'
_INVENTORY_LEVEL_GID = re.compile(
    r'^gid://shopify/InventoryLevel/'
    r'(?P<level_id>%s)\?inventory_item_id=(?P<item_id>%s)$'
    % (_POSITIVE_DECIMAL, _POSITIVE_DECIMAL)
)


def _parse_inventory_level_gid(value):
    """Return the canonical InventoryLevel composite, or ``False``.

    Shopify's InventoryLevel GID is a parameterized GID.  The only accepted
    query component is the documented ``inventory_item_id`` component.  A
    location id is authoritative response data (``location { id }``), not a
    value that this service is allowed to synthesize into a GID.  Requiring
    the exact grammar rejects fragments, extra query parameters, path
    suffixes, encoded/nonnumeric guesses, and the bare numeric REST ids that
    are unsafe to use as GraphQL identity.
    """
    if not isinstance(value, str) or value.strip() != value:
        return False
    match = _INVENTORY_LEVEL_GID.fullmatch(value)
    if not match:
        return False
    return {
        'level_id': match.group('level_id'),
        'inventory_item_id': match.group('item_id'),
    }


def _canonical_simple_gid(value, prefix):
    """Accept one exact, unparameterized Shopify object GID."""
    if not isinstance(value, str) or value.strip() != value:
        return False
    if not value.startswith(prefix) or len(value) > 512:
        return False
    suffix = value[len(prefix):]
    if not re.fullmatch(_POSITIVE_DECIMAL, suffix):
        return False
    return suffix


def _parse_remote_datetime(value):
    """Parse a timezone-required RFC3339 value into UTC-naive Odoo time.

    This parser intentionally does not use Odoo's permissive datetime helper:
    a value such as ``2026-08-22 08:00:00`` is not a valid remote timestamp
    for observation ordering and must be rejected rather than interpreted in
    a server-local timezone.
    """
    if (
        not isinstance(value, str)
        or value.strip() != value
        or not _RFC3339_TIMESTAMP.fullmatch(value)
    ):
        return False
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + '+00:00' if value.endswith('Z') else value,
        )
    except (TypeError, ValueError, OverflowError):
        return False
    if not parsed.tzinfo or parsed.utcoffset() is None:
        return False
    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _strict_integer(value):
    """Return a real integer, never a boolean or a numeric string."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value


def _valid_shopify_gid(value, prefix):
    """Validate a canonical Shopify GID for a known object type."""
    if prefix == 'gid://shopify/InventoryLevel/':
        return bool(_parse_inventory_level_gid(value))
    return bool(_canonical_simple_gid(value, prefix))


class ShopifyConnectorInventoryObservation(models.Model):
    """One immutable outcome for one claimed observation job.

    The row stores no webhook body.  Delivery identity and correlation remain
    on W1's payload-free delivery envelope; this table stores the authoritative
    read result and the monotonic disposition needed by operators and the
    fallback scanner.
    """

    _name = 'shopify.connector.inventory.observation'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Inventory Observation Evidence'
    _order = 'source_updated_at desc, id desc'

    store_id = fields.Many2one(
        'shopify.connector.store', required=True, index=True, readonly=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company', related='store_id.company_id', store=True, index=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        'shopify.connector.job', required=True, index=True, readonly=True,
        ondelete='restrict',
    )
    binding_id = fields.Many2one(
        'shopify.connector.inventory.level.binding', index=True, readonly=True,
        ondelete='restrict',
    )
    location_mapping_id = fields.Many2one(
        'shopify.connector.location.mapping', index=True, readonly=True,
        ondelete='restrict',
    )
    inventory_level_gid = fields.Char(required=True, index=True, readonly=True)
    inventory_item_gid = fields.Char(required=True, index=True, readonly=True)
    location_gid = fields.Char(required=True, index=True, readonly=True)
    available = fields.Integer(required=True, readonly=True)
    source_updated_at = fields.Datetime(required=True, index=True, readonly=True)
    webhook_source_updated_at = fields.Datetime(readonly=True)
    observed_at = fields.Datetime(
        required=True, default=fields.Datetime.now, index=True, readonly=True,
    )
    source = fields.Selection(
        selection=INVENTORY_OBSERVATION_SOURCES,
        required=True, readonly=True,
    )
    state = fields.Selection(
        selection=INVENTORY_OBSERVATION_STATES,
        required=True, index=True, readonly=True,
    )
    delivery_id = fields.Char(index=True, readonly=True)
    event_id = fields.Char(index=True, readonly=True)
    remote_store_domain = fields.Char(readonly=True)
    previous_observation_id = fields.Many2one(
        'shopify.connector.inventory.observation', index=True, readonly=True,
        ondelete='set null',
    )
    reason = fields.Text(readonly=True)

    _job_unique = models.Constraint(
        'UNIQUE(job_id)',
        'One inventory observation evidence row is allowed per job.',
    )

    @api.model
    def _service_context(self):
        return {_OBSERVATION_SERVICE_CONTEXT: _OBSERVATION_SERVICE_SENTINEL}

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(_OBSERVATION_SERVICE_CONTEXT)
            is not _OBSERVATION_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Inventory observation evidence can only be created by the '
                'verified read service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.su
            or self.env.context.get(_OBSERVATION_SERVICE_CONTEXT)
            is not _OBSERVATION_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Inventory observation evidence can only be changed by the '
                'verified read service.'
            )
        allowed = {
            'binding_id', 'location_mapping_id', 'available',
            'source_updated_at', 'webhook_source_updated_at', 'observed_at',
            'source', 'state', 'delivery_id', 'event_id',
            'remote_store_domain', 'previous_observation_id', 'reason',
            'inventory_level_gid', 'inventory_item_gid', 'location_gid',
        }
        unknown = set(vals) - allowed
        if unknown:
            raise ValidationError(
                'Inventory observation service cannot write fields: %s.'
                % ', '.join(sorted(unknown))
            )
        return super().write(vals)

    def unlink(self):
        raise AccessError(
            'Inventory observation evidence is retained as operator history.'
        )

    @api.model
    def _sec3_parent_scope_relations(self):
        return (
            ('job_id', 'store'),
            ('binding_id', 'store'),
            ('location_mapping_id', 'store'),
            ('previous_observation_id', 'store'),
        )

    @api.constrains(
        'store_id', 'job_id', 'binding_id', 'location_mapping_id',
        'previous_observation_id',
    )
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    @api.constrains(
        'inventory_level_gid', 'inventory_item_gid', 'location_gid',
        'source_updated_at', 'available',
    )
    def _check_identity_shape(self):
        for evidence in self:
            level_identity = _parse_inventory_level_gid(
                evidence.inventory_level_gid,
            )
            item_id = _canonical_simple_gid(
                evidence.inventory_item_gid,
                'gid://shopify/InventoryItem/',
            )
            location_id = _canonical_simple_gid(
                evidence.location_gid, 'gid://shopify/Location/',
            )
            if not level_identity:
                raise ValidationError(
                    'Inventory observation evidence requires an exact '
                    'canonical Shopify InventoryLevel composite GID.'
                )
            if not item_id:
                raise ValidationError(
                    'Inventory observation evidence requires an exact '
                    'Shopify InventoryItem GID.'
                )
            if not location_id:
                raise ValidationError(
                    'Inventory observation evidence requires an exact '
                    'Shopify Location GID.'
                )
            if level_identity['inventory_item_id'] != item_id:
                raise ValidationError(
                    'Inventory observation evidence InventoryLevel composite '
                    'does not match its authoritative InventoryItem GID.'
                )
            if level_identity['level_id'] != location_id:
                raise ValidationError(
                    'Inventory observation evidence InventoryLevel composite '
                    'does not match its authoritative Location GID.'
                )
            if evidence.binding_id:
                if (
                    evidence.binding_id.shopify_inventory_item_gid
                    != evidence.inventory_item_gid
                ):
                    raise ValidationError(
                        'Inventory observation evidence InventoryItem GID '
                        'does not match the bound inventory pair.'
                    )
                if (
                    evidence.binding_id.location_mapping_id
                    != evidence.location_mapping_id
                ):
                    raise ValidationError(
                        'Inventory observation evidence Location mapping '
                        'does not match the bound inventory pair.'
                    )
            if (
                evidence.location_mapping_id
                and evidence.location_mapping_id.shopify_gid
                != evidence.location_gid
            ):
                raise ValidationError(
                    'Inventory observation evidence Location GID does not '
                    'match its authoritative location mapping.'
                )

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()

    @api.model
    def run_scheduled_observation_fallback(self, limit=20):
        """Cron-facing delegate; the service owns selection and enqueue."""
        return self.env[
            'shopify.connector.inventory.observation.service'
        ].run_scheduled_observation_fallback(limit=limit)

    @api.model
    def _run_scheduled_observation_fallback(self, limit=20):
        """Root-only cron entry matching the cron's model_id."""
        if self.env.uid != SUPERUSER_ID:
            raise AccessError('Only the root cron may run inventory observation.')
        return self.env[
            'shopify.connector.inventory.observation.service'
        ]._run_scheduled_observation_fallback(limit=limit)


class ShopifyConnectorInventoryBindingObservationFields(models.Model):
    """Monotonic current watermark projected onto the pair binding."""

    _inherit = 'shopify.connector.inventory.level.binding'

    last_observed_updated_at = fields.Datetime(
        string='Last Shopify observation', index=True, readonly=True,
    )
    last_observed_available = fields.Integer(readonly=True)
    last_observation_delivery_id = fields.Char(index=True, readonly=True)
    last_observation_event_id = fields.Char(readonly=True)
    last_observation_state = fields.Selection(
        selection=INVENTORY_OBSERVATION_STATES, readonly=True,
    )
    last_observed_at = fields.Datetime(readonly=True)

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'last_observed_updated_at',
            'last_observed_available',
            'last_observation_delivery_id',
            'last_observation_event_id',
            'last_observation_state',
            'last_observed_at',
        ))


class ShopifyConnectorInventoryObservationService(models.AbstractModel):
    """Read-only child handler and bounded fallback scheduler."""

    _name = 'shopify.connector.inventory.observation.service'
    _description = 'Shopify Inventory Observation Service'

    _CRON_CONTEXT_KEY = '_inventory_observation_cron'

    @api.model
    def _run_scheduled_observation_fallback(self, limit=OBSERVATION_FALLBACK_BATCH):
        """Private cron entry; public callers cannot self-select all companies."""
        if self.env.uid != SUPERUSER_ID:
            raise AccessError('Only the root cron may run inventory observation.')
        context = {self._CRON_CONTEXT_KEY: _CRON_CONTEXT_SENTINEL}
        return self.with_context(**context).run_scheduled_observation_fallback(
            limit=limit,
        )

    INVENTORY_OBSERVATION_QUERY = (
        'query InventoryObservation($levelId: ID!) { '
        # The child is intentionally read by the exact InventoryLevel GID
        # admitted from W1.  ``quantities(names: ["available"])`` is the
        # authoritative quantity surface; only that quantity's updatedAt is
        # requested and used for ordering.  InventoryLevel.updatedAt is not a
        # substitute because it describes the level object, not necessarily
        # the available quantity that was observed.
        'inventoryLevel(id: $levelId) { id '
        'item { id tracked } location { id } '
        'quantities(names: ["available"]) { name quantity updatedAt } '
        '} shop { myshopifyDomain } }'
    )

    @api.model
    def _observation_payload_hash(
        self, level_gid, source_stamp, payload_digest, generation,
    ):
        return observation_payload_hash(
            level_gid, source_stamp, payload_digest, generation,
        )

    @api.model
    def _observation_service(self):
        return self.env['shopify.connector.inventory.observation'].sudo().with_context(
            **self.env['shopify.connector.inventory.observation']._service_context()
        )

    @api.model
    def _valid_level_gid(self, value):
        """Accept only Shopify's explicit InventoryLevel GID value."""
        return value if _parse_inventory_level_gid(value) else False

    @api.model
    def _level_gid_matches_authoritative_identity(
        self, level_gid, item_gid, location_gid,
    ):
        """Cross-check a composite level GID with exact read identities.

        ``location_gid`` is not guessed from a webhook numeric field and is
        not interpolated into the level GID. It must be the exact canonical
        ``Location`` GID returned by Shopify. The parameterized level GID's
        embedded inventory-item component must equal the authoritative
        ``InventoryItem`` suffix. The InventoryLevel object's own numeric
        suffix is an independent resource identity and must not be equated to
        the Location suffix.
        """
        composite = _parse_inventory_level_gid(level_gid)
        item_id = _canonical_simple_gid(
            item_gid, 'gid://shopify/InventoryItem/',
        )
        location_id = _canonical_simple_gid(
            location_gid, 'gid://shopify/Location/',
        )
        return bool(
            composite
            and item_id
            and location_id
            and composite['inventory_item_id'] == item_id
        )

    @api.model
    def _delivery_level_gid(self, delivery):
        identity = delivery.resource_identity
        if not isinstance(identity, dict):
            return False
        gid = identity.get('admin_graphql_api_id')
        if not self._valid_level_gid(gid):
            return False
        if delivery.resource_gid != gid:
            return False
        return gid

    @api.model
    def _find_binding_by_level_gid(self, store, level_gid):
        Binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo()
        bindings = Binding.search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', level_gid),
        ])
        if len(bindings) != 1:
            return Binding.browse()
        return bindings

    @api.model
    def _resolve_exact_binding(
        self, store, level_gid, item_gid, location_gid,
    ):
        """Resolve the already-recorded pair; never synthesize a binding."""
        if not self._level_gid_matches_authoritative_identity(
            level_gid, item_gid, location_gid,
        ):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The authoritative InventoryLevel composite GID did not '
                'match exact InventoryItem and Location GIDs; no binding '
                'was created or re-homed.',
            )
        binding = self._find_binding_by_level_gid(store, level_gid)
        if len(binding) != 1:
            raise JobHandlerError(
                ERROR_CLASS_VALIDATION,
                'No unique existing inventory-level binding records the '
                'exact Shopify InventoryLevel GID; no binding was created.',
            )
        mapping = self.env['shopify.connector.location.mapping'].sudo().search([
            ('id', '=', binding.location_mapping_id.id),
            ('store_id', '=', store.id),
            ('shopify_gid', '=', location_gid),
        ])
        if len(mapping) != 1:
            raise JobHandlerError(
                ERROR_CLASS_LOCATION_MISSING,
                'No unique existing Shopify Location mapping matches the '
                'authoritative InventoryLevel location; no Odoo stock was '
                'changed.',
            )
        if (
            binding.shopify_inventory_item_gid != item_gid
            or binding.location_mapping_id != mapping
            or mapping.store_id != store
            or binding.product_variant_binding_id.store_id != store
        ):
            raise JobHandlerError(
                ERROR_CLASS_VALIDATION,
                'The authoritative InventoryLevel item/location identity '
                'does not match the existing store-scoped binding.',
            )
        if (
            binding.company_id != store.company_id
            or mapping.company_id != store.company_id
        ):
            raise JobHandlerError(
                ERROR_CLASS_VALIDATION,
                'Inventory observation binding and mapping company scope '
                'could not be proven.',
            )
        return binding, mapping

    @api.model
    def _delivery_for_job(self, job):
        # Scheduled fallback jobs keep a local cursor/run reference for
        # operator correlation, but that reference is not a W1 delivery ID.
        # Only webhook-origin children require a persisted verified envelope.
        if job.job_source != 'webhook':
            return self.env['shopify.connector.webhook.delivery'].sudo().browse()
        ref = job.trigger_origin_event_ref
        if not ref:
            return self.env['shopify.connector.webhook.delivery'].sudo().browse()
        delivery = self.env['shopify.connector.webhook.delivery'].sudo().search([
            ('store_id', '=', job.store_id.id),
            ('delivery_id', '=', ref),
            ('topic', '=', 'inventory_levels/update'),
        ], limit=1)
        if not delivery:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The inventory observation delivery evidence is missing; '
                'scheduled reconciliation remains the recovery path.',
            )
        if delivery.state not in ('queued', 'processed', 'received'):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The inventory observation delivery evidence is not '
                'processable.',
            )
        return delivery

    @api.model
    def _validate_delivery_for_job(self, delivery, job, level_gid):
        if not delivery:
            return False
        if (
            delivery.store_id != job.store_id
            or delivery.resource_type != 'inventory_levels'
            or delivery.api_version != job.store_id.api_version
            or not (
                isinstance(delivery.shop_domain, str)
                and isinstance(job.store_id.shop_domain, str)
                and delivery.shop_domain.lower()
                == job.store_id.shop_domain.lower()
            )
        ):
            raise JobHandlerError(
                ERROR_CLASS_STORE_IDENTITY,
                'Inventory webhook delivery store or API identity did not '
                'match the claimed observation job.',
            )
        if delivery.source_updated_at is False:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The inventory webhook did not contain its required '
                'updated_at evidence.',
            )
        if self._delivery_level_gid(delivery) != level_gid:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The inventory webhook delivery did not contain the exact '
                'InventoryLevel GID admitted by its child job.',
            )
        return True

    @api.model
    def _outbound_lineage(self, store, binding, current_job=None):
        """Return the one unresolved outbound owner for this pair.

        The query intentionally includes every non-terminal state, including
        ``failed_retryable`` and ``blocked_manual_review``.  Those states are
        unresolved ownership evidence, not permission to keep an observation
        job retrying forever; ``_defer_for_outbound_lineage`` applies the
        bounded core retry/age contract and freezes persistent cases.
        """
        domain = [
            ('store_id', '=', store.id),
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('res_id', '=', binding.id),
            ('job_type', 'in', OUTBOUND_INVENTORY_JOB_TYPES),
            ('state', 'not in', TERMINAL_JOB_STATES),
        ]
        if current_job:
            domain.insert(0, ('id', '!=', current_job.id))
        return self.env['shopify.connector.job'].sudo().search(
            domain, order='id asc', limit=1,
        )

    @api.model
    def _freeze_for_outbound_lineage(self, job, lineage, binding=False):
        """Freeze the pair when outbound ownership is persistently unresolved."""
        reason = (
            'Inventory observation was frozen because outbound inventory '
            'job %s remains unresolved in state %s. The pair requires '
            'scheduled repair or operator review; no remote observation, '
            'stock write, or outbound mutation was performed.' % (
                lineage.id, lineage.state,
            )
        )
        if binding:
            binding.sudo().write({'status': 'review'})
        job._transition_blocked_manual_review(
            ERROR_CLASS_CONCURRENCY,
            SUBREASON_BINDING_CONFLICT,
            reason,
        )
        return False

    @api.model
    def _read_inventory_level(self, job, store, level_gid):
        client = self.env['shopify.connector.api.client']
        variables = {'levelId': level_gid}
        with client.execute_business_read(
            job,
            store,
            self.INVENTORY_OBSERVATION_QUERY,
            variables,
            purpose='inventory',
        ) as result:
            data = (result or {}).get('data')
            if not isinstance(data, dict):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned no inventory observation data.',
                )
            shop = data.get('shop')
            identity = shop.get('myshopifyDomain') if isinstance(shop, dict) else False
            if (
                not isinstance(identity, str)
                or not isinstance(store.shop_domain, str)
                or (
                    identity.lower() != store.shop_domain.lower()
                )
            ):
                raise JobHandlerError(
                    ERROR_CLASS_STORE_IDENTITY,
                    'The inventory observation read returned a different '
                    'Shopify shop identity.',
                )
            level = data.get('inventoryLevel')
            if (
                not isinstance(level, dict)
                or level.get('id') != level_gid
                or not _parse_inventory_level_gid(level.get('id'))
            ):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned a different or malformed '
                    'InventoryLevel identity.',
                )
            item = level.get('item')
            location = level.get('location')
            if (
                not isinstance(item, dict)
                or not isinstance(item.get('id'), str)
                or not _valid_shopify_gid(
                    item.get('id'), 'gid://shopify/InventoryItem/',
                )
                or not isinstance(item.get('tracked'), bool)
            ):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned a malformed InventoryItem identity.',
                )
            if (
                not isinstance(location, dict)
                or not isinstance(location.get('id'), str)
                or not _valid_shopify_gid(
                    location.get('id'), 'gid://shopify/Location/',
                )
            ):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned a malformed Location identity.',
                )
            quantities = level.get('quantities')
            if not isinstance(quantities, list) or len(quantities) != 1:
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned an ambiguous available quantity list.',
                )
            quantity = quantities[0]
            if not isinstance(quantity, dict) or quantity.get('name') != 'available':
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned no uniquely identified available '
                    'quantity.',
                )
            available = _strict_integer(quantity.get('quantity'))
            quantity_updated_at = _parse_remote_datetime(
                quantity.get('updatedAt'),
            )
            # Missing/malformed quantity.updatedAt is not recoverable by
            # looking at InventoryLevel.updatedAt.  The latter is not in the
            # query above by design; fail closed with the exact authoritative
            # timestamp requirement instead of inventing an ordering value.
            if available is False or quantity_updated_at is False:
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned a non-integral available quantity or '
                    'a missing/malformed authoritative quantity.updatedAt '
                    'timestamp; InventoryLevel.updatedAt is not a valid '
                    'substitute.',
                )
            if not self._level_gid_matches_authoritative_identity(
                level_gid, item['id'], location['id'],
            ):
                raise JobHandlerError(
                    ERROR_CLASS_DATA_SHAPE,
                    'Shopify returned an InventoryLevel composite GID whose '
                    'embedded item or authoritative location identity does '
                    'not match the exact read identities.',
                )
            return {
                'store_domain': identity,
                'inventory_level_gid': level_gid,
                'inventory_item_gid': item['id'],
                'location_gid': location['id'],
                'tracked': item['tracked'],
                'available': available,
                'source_updated_at': quantity_updated_at,
            }

    @api.model
    def _latest_observation(self, binding):
        return self.env[
            'shopify.connector.inventory.observation'
        ].sudo().search([
            ('binding_id', '=', binding.id),
            ('state', 'in', ('accepted', 'manual_review')),
        ], order='source_updated_at desc, id desc', limit=1)

    @api.model
    def _record_observation(
        self, job, snapshot, binding, mapping, state, reason,
        previous=False, delivery=False,
    ):
        delivery = delivery or self.env[
            'shopify.connector.webhook.delivery'
        ].sudo().browse()
        values = {
            'store_id': job.store_id.id,
            'job_id': job.id,
            'binding_id': binding.id if binding else False,
            'location_mapping_id': mapping.id if mapping else False,
            'inventory_level_gid': snapshot['inventory_level_gid'],
            'inventory_item_gid': snapshot['inventory_item_gid'],
            'location_gid': snapshot['location_gid'],
            'available': snapshot['available'],
            'source_updated_at': snapshot['source_updated_at'],
            'webhook_source_updated_at': (
                delivery.source_updated_at if delivery else False
            ),
            'source': 'webhook' if delivery else 'scheduled_sync',
            'state': state,
            'delivery_id': delivery.delivery_id if delivery else False,
            'event_id': delivery.event_id if delivery else False,
            'remote_store_domain': snapshot['store_domain'],
            'previous_observation_id': previous.id if previous else False,
            'reason': reason or False,
        }
        Evidence = self._observation_service()
        existing = Evidence.search([('job_id', '=', job.id)], limit=1)
        if existing:
            existing.write(values)
            return existing
        try:
            with self.env.cr.savepoint():
                return Evidence.create(values)
        except IntegrityError:
            existing = Evidence.search([('job_id', '=', job.id)], limit=1)
            if existing:
                return existing
            raise

    @api.model
    def _defer_for_outbound_lineage(self, job, lineage, binding=False):
        """Apply the core retry ceiling/age contract to lineage deferral.

        A blocked/manual-fix outbound job cannot be made healthy by retrying
        the observation, and a retry-waiting observation cannot outlive the
        core's 12-attempt/24-hour contract.  Both cases deterministically
        freeze the pair instead of creating a forever-retry loop.  Ordinary
        active lineage uses the core scheduler itself, preserving the shared
        backoff, jitter, retry count, and age semantics.
        """
        now = fields.Datetime.now()
        started_at = getattr(job, 'started_at', False) or now
        retry_count = int(getattr(job, 'retry_count', 0) or 0)
        lineage_started_at = getattr(lineage, 'started_at', False) or now
        lineage_retry_count = int(
            getattr(lineage, 'retry_count', 0) or 0
        )
        persistent_lineage = lineage.state in (
            'failed_retryable', 'blocked_manual_review',
        ) or (
            lineage_retry_count >= RETRY_MAX_ATTEMPTS
            or now - lineage_started_at >= timedelta(hours=RETRY_WINDOW_HOURS)
        )
        persistent_observation = (
            retry_count >= RETRY_MAX_ATTEMPTS
            or now - started_at >= timedelta(hours=RETRY_WINDOW_HOURS)
        )
        if persistent_lineage or persistent_observation:
            return self._freeze_for_outbound_lineage(
                job, lineage, binding=binding,
            )

        reason = (
            'Inventory observation deferred while outbound inventory job '
            '%s holds the pair lineage; no remote observation or stock '
            'write was performed.' % lineage.id
        )
        self.env['shopify.connector.job.dispatch']._schedule_retry_or_fail(
            job,
            ERROR_CLASS_CONCURRENCY,
            reason,
            False,
            max_attempts=RETRY_MAX_ATTEMPTS,
        )
        return True

    @api.model
    def _is_authoritative_timestamp_failure(self, error):
        return (
            isinstance(error, JobHandlerError)
            and error.error_class == ERROR_CLASS_DATA_SHAPE
            and 'quantity.updatedAt' in error.reason
        )

    @api.model
    def _freeze_for_authoritative_timestamp_failure(
        self, job, binding, error,
    ):
        """Keep unusable remote time as durable manual-review evidence.

        No observation row is manufactured with a local timestamp: doing so
        would corrupt the ordering watermark.  The claimed job's audited
        blocked transition is the reconciliation evidence, and the pair is
        frozen until a later scheduled/manual repair obtains a valid
        quantity.updatedAt.
        """
        locked = binding.try_lock_for_update()
        if not locked:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The inventory pair is held while its authoritative '
                'quantity timestamp is being reviewed; retry later.',
            )
        locked.invalidate_recordset()
        locked.sudo().write({'status': 'review'})
        job._transition_blocked_manual_review(
            ERROR_CLASS_DATA_SHAPE,
            SUBREASON_BINDING_CONFLICT,
            error.reason,
            error.technical_detail,
        )
        return False

    @api.model
    def _apply_snapshot(
        self, job, binding, mapping, snapshot, delivery=False,
    ):
        locked = binding.try_lock_for_update()
        if not locked:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The inventory pair is held by another worker; the '
                'observation job will retry without changing stock.',
            )
        locked.invalidate_recordset()
        lineage = self._outbound_lineage(job.store_id, locked, job)
        if lineage:
            self._defer_for_outbound_lineage(job, lineage, binding=locked)
            return
        latest = self._latest_observation(locked)
        incoming_at = snapshot['source_updated_at']
        if latest and incoming_at < latest.source_updated_at:
            self._record_observation(
                job, snapshot, locked, mapping, 'stale',
                'An older Shopify observation was retained without moving '
                'the pair watermark.', latest, delivery,
            )
            return
        if latest and incoming_at == latest.source_updated_at:
            if snapshot['available'] == latest.available:
                self._record_observation(
                    job, snapshot, locked, mapping, 'duplicate',
                    'The Shopify observation matched the current timestamp '
                    'and available quantity; no state changed.', latest,
                    delivery,
                )
                return
            # Same timestamp with two different quantities is not safely
            # orderable. Treat it as a review case, never choose a winner.
            reason = (
                'Two Shopify inventory observations share the same updatedAt '
                'but report different available quantities; manual review is '
                'required and no Odoo stock or Shopify mutation was issued.'
            )
            self._record_observation(
                job, snapshot, locked, mapping, 'manual_review', reason,
                latest, delivery,
            )
            locked.sudo().write({
                'status': 'review',
                'last_observed_updated_at': incoming_at,
                'last_observed_available': snapshot['available'],
                'last_observation_delivery_id': (
                    delivery.delivery_id if delivery else False
                ),
                'last_observation_event_id': (
                    delivery.event_id if delivery else False
                ),
                'last_observation_state': 'manual_review',
                'last_observed_at': fields.Datetime.now(),
                'last_known_shopify_available': snapshot['available'],
            })
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION,
                SUBREASON_BINDING_CONFLICT,
                reason,
            )
            return

        if locked.status in ('review', 'stale'):
            reason = (
                'The inventory pair is already frozen as %s; the Shopify '
                'observation was retained for review and no stock or '
                'mutation action was taken.' % locked.status
            )
            self._record_observation(
                job, snapshot, locked, mapping, 'manual_review', reason,
                latest, delivery,
            )
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION,
                SUBREASON_BINDING_CONFLICT,
                reason,
            )
            return

        # ``_refresh_pending_target`` is a connector metadata refresh only.
        # It reads Odoo's free_qty under the existing narrow sudo and writes
        # the coalesced target on the binding; it never writes stock.quant or
        # any Odoo stock quantity.  The inbound observation never calls the
        # outbound service's enqueue or mutation paths.
        target, _free_qty = self.env[
            'shopify.connector.inventory.service'
        ]._refresh_pending_target(locked)
        last_pushed_known = bool(locked.last_pushed_at)
        remote_available = snapshot['available']
        unexplained = (
            last_pushed_known
            and remote_available != locked.last_pushed_available
            and remote_available != target
        )
        if unexplained:
            reason = (
                'Shopify inventory differs from both the last pushed Odoo '
                'quantity and the current Odoo target. The pair is frozen '
                'for manual review; no Odoo stock was written and no '
                'outbound mutation was enqueued.'
            )
            self._record_observation(
                job, snapshot, locked, mapping, 'manual_review', reason,
                latest, delivery,
            )
            locked.sudo().write({
                'status': 'review',
                'last_observed_updated_at': incoming_at,
                'last_observed_available': remote_available,
                'last_observation_delivery_id': (
                    delivery.delivery_id if delivery else False
                ),
                'last_observation_event_id': (
                    delivery.event_id if delivery else False
                ),
                'last_observation_state': 'manual_review',
                'last_observed_at': fields.Datetime.now(),
                'last_known_shopify_available': remote_available,
            })
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION,
                SUBREASON_BINDING_CONFLICT,
                reason,
            )
            return

        reason = (
            'Authoritative Shopify InventoryLevel observation recorded '
            'without writing Odoo stock or enqueuing an outbound mutation.'
        )
        self._record_observation(
            job, snapshot, locked, mapping, 'accepted', reason,
            latest, delivery,
        )
        locked.sudo().write({
            'last_observed_updated_at': incoming_at,
            'last_observed_available': remote_available,
            'last_observation_delivery_id': (
                delivery.delivery_id if delivery else False
            ),
            'last_observation_event_id': (
                delivery.event_id if delivery else False
            ),
            'last_observation_state': 'accepted',
            'last_observed_at': fields.Datetime.now(),
            'last_known_shopify_available': remote_available,
        })

    @api.model
    def _handle_inventory_observation_sync(self, job):
        """Guarded read-first child entry point."""
        store = job.store_id.sudo()
        level_gid = self._valid_level_gid(job.shopify_target_gid)
        if not level_gid:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Inventory observation job has no exact InventoryLevel GID.',
            )
        delivery = self._delivery_for_job(job)
        self._validate_delivery_for_job(delivery, job, level_gid)
        binding = self._find_binding_by_level_gid(store, level_gid)
        if len(binding) != 1:
            raise JobHandlerError(
                ERROR_CLASS_VALIDATION,
                'Inventory observation requires an existing exact level '
                'binding; no binding or mapping was created.',
            )
        if binding.status in ('review', 'stale'):
            reason = (
                'Inventory observation was held because the existing pair is '
                'already frozen as %s.' % binding.status
            )
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION,
                SUBREASON_BINDING_CONFLICT,
                reason,
            )
            return
        lineage = self._outbound_lineage(store, binding, job)
        if lineage:
            self._defer_for_outbound_lineage(job, lineage, binding=binding)
            return
        try:
            snapshot = self._read_inventory_level(job, store, level_gid)
            resolved_binding, mapping = self._resolve_exact_binding(
                store,
                level_gid,
                snapshot['inventory_item_gid'],
                snapshot['location_gid'],
            )
            self._apply_snapshot(job, resolved_binding, mapping, snapshot, delivery)
        except JobHandlerError as exc:
            if self._is_authoritative_timestamp_failure(exc):
                self._freeze_for_authoritative_timestamp_failure(
                    job, binding, exc,
                )
                return
            raise
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class,
                exc.reason,
                exc.technical_detail,
            ) from exc
        except ShopifyQuiescedError as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'Inventory observation read was refused by store '
                'quiescence; the durable job will retry.',
                type(exc).__name__,
            ) from exc

    @api.model
    def _observation_candidates(self, store, limit, cursor=0):
        Binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo()
        base = [
            ('store_id', '=', store.id),
            ('shopify_gid', '!=', False),
            ('last_pushed_at', '!=', False),
            ('status', '=', 'active'),
            ('product_variant_binding_id.status', '=', 'active'),
            ('location_mapping_id.status', '=', 'active'),
        ]
        # Query the page after the persisted cursor first. Only wrap to the
        # beginning when that page is exhausted; fetching merely the first N
        # rows and rotating them in Python would starve every binding after N.
        after = Binding.search(
            base + [('id', '>', int(cursor or 0))],
            order='id asc', limit=limit,
        )
        remaining = max(0, int(limit or 0) - len(after))
        if not remaining:
            return after
        before = Binding.search(
            base + [('id', '<=', int(cursor or 0))],
            order='id asc', limit=remaining,
        )
        # Recordset union may normalize IDs into ascending order and thereby
        # erase the after-cursor-first ordering. Concatenation preserves the
        # two bounded pages' order for the fair round-robin selector.
        return after + before

    @api.model
    def _scheduled_observation_stores(self, limit):
        """Select one bounded, fair page without touching the settings row.

        The scheduler checkpoint belongs to the store.  A formerly stored
        related mirror on the one-row settings relation made every checkpoint
        advance update that shared configuration row.  Product/order scan
        windows use the same row, so independently scheduled domains could
        deterministically abort each other with PostgreSQL 40001.

        Join the eligibility flags to their owning store instead.  The LIMIT is
        applied in SQL, NULL checkpoints remain first, and interactive calls
        retain the explicit active-company boundary while the root cron may
        service every company.
        """
        store_limit = max(
            1,
            min(int(limit or OBSERVATION_FALLBACK_STORE_LIMIT),
                OBSERVATION_FALLBACK_STORE_LIMIT),
        )
        is_cron = (
            self.env.context.get(self._CRON_CONTEXT_KEY)
            is _CRON_CONTEXT_SENTINEL
        )
        company_sql = ''
        params = []
        if not is_cron:
            company_sql = 'AND store.company_id = ANY(%s)'
            params.append(self.env.companies.ids)

        Store = self.env['shopify.connector.store'].sudo()
        Settings = self.env['shopify.connector.store.settings'].sudo()
        Store.flush_model([
            'state', 'company_id', 'inventory_observation_scheduled_at',
        ])
        Settings.flush_model([
            'store_id', 'inventory_domain_enabled',
            'inventory_scheduled_sync_enabled',
        ])
        params.append(store_limit)
        self.env.cr.execute(
            """
                SELECT store.id
                  FROM shopify_connector_store AS store
                  JOIN shopify_connector_store_settings AS settings
                    ON settings.store_id = store.id
                 WHERE settings.inventory_domain_enabled IS TRUE
                   AND settings.inventory_scheduled_sync_enabled IS TRUE
                   AND store.state = 'connected'
                   %s
                 ORDER BY
                       store.inventory_observation_scheduled_at ASC NULLS FIRST,
                       store.id ASC
                 LIMIT %%s
            """ % company_sql,
            params,
        )
        # Preserve SQL fairness order; browse() keeps the supplied id order.
        return tuple(Store.browse([row[0] for row in self.env.cr.fetchall()]))

    @api.model
    def _cron_has_time(self, cron, remaining):
        """Probe the Odoo cron budget before doing another bounded query."""
        if not cron:
            return True
        return cron._commit_progress(0, remaining=max(int(remaining), 0)) > 0

    @api.model
    def _admit_fallback_pair(self, store, binding, run_nonce):
        """Admit/coalesce one pair and say whether its cursor is safe."""
        existing, disposition = self._find_existing_observation_job(
            store, binding.shopify_gid, False,
        )
        if existing:
            # A same-generation active job is already accountable.  A stale
            # generation owner is not: leaving the cursor unchanged lets the
            # next scheduled repair revisit it after lifecycle recovery.
            return disposition in (
                'coalesced', 'duplicate_succeeded',
            ), disposition
        Enqueue = self.env['shopify.connector.job.enqueue'].sudo()
        try:
            # Keep a racing unique-key failure inside a savepoint.  Without
            # it the subsequent winner re-read would run on an aborted
            # PostgreSQL transaction and the cursor could neither coalesce
            # nor remain safely unadvanced.
            with self.env.cr.savepoint():
                Enqueue.enqueue(
                    store,
                    'scheduled_sync',
                    INVENTORY_OBSERVATION_JOB_TYPE,
                    payload_hash=fallback_payload_hash(
                        binding.shopify_gid, run_nonce,
                    ),
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=binding.shopify_gid,
                    trigger_origin_event_ref=(
                        'scheduled_observation:%s:%s' % (store.id, run_nonce)
                    ),
                    trigger_origin_event_at=fields.Datetime.now(),
                )
            return True, 'enqueued'
        except (IntegrityError, ValidationError) as exc:
            # A visible same-generation winner is a safe coalesce.  An
            # unresolved conflict remains at the old cursor for repair.
            if not self._is_duplicate_admission_error(exc):
                raise
            existing, disposition = self._find_existing_observation_job(
                store, binding.shopify_gid, False,
            )
            if existing and disposition in (
                'coalesced', 'duplicate_succeeded',
            ):
                return True, disposition
            _logger.warning(
                'Inventory observation fallback could not resolve a '
                'concurrent admission for store=%s level=%s (%s); cursor '
                'was not advanced.',
                store.id, binding.shopify_gid, disposition,
            )
            return False, 'unresolved_conflict'

    @api.model
    def run_scheduled_observation_fallback(self, limit=OBSERVATION_FALLBACK_BATCH):
        """Run a bounded, fair read-only observation pass.

        Pair selection happens immediately before admission.  The pair cursor
        is written only after enqueue/coalesce/explicit no-work accounting,
        so an expiring cron budget cannot skip selected but unattempted work.
        """
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may schedule '
                'inventory observation reconciliation.'
            )
        batch_limit = max(
            1,
            min(int(limit or OBSERVATION_FALLBACK_BATCH),
                OBSERVATION_FALLBACK_MAX_BATCH),
        )
        cron = (
            self.env['ir.cron'].sudo().browse(
                self.env.context.get('cron_id'),
            )
            if (
                self.env.context.get(self._CRON_CONTEXT_KEY)
                is _CRON_CONTEXT_SENTINEL
            ) else False
        )
        # Do not even perform the bounded store-page reads after Odoo has
        # declared the cron budget exhausted.  The store ceiling is included
        # in the estimate because selecting that page is real database work.
        if not self._cron_has_time(
            cron,
            batch_limit + OBSERVATION_FALLBACK_STORE_LIMIT,
        ):
            return 0
        stores = list(self._scheduled_observation_stores(
            OBSERVATION_FALLBACK_STORE_LIMIT,
        ))
        if not stores:
            if cron:
                cron._commit_progress(0, remaining=0)
            return 0
        if not self._cron_has_time(cron, batch_limit + len(stores)):
            return 0

        run_nonce = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
        active_stores = list(stores)
        enqueued = 0
        accounted_pairs = 0
        while active_stores and accounted_pairs < batch_limit:
            made_progress = False
            for store in list(active_stores):
                if accounted_pairs >= batch_limit:
                    break
                if not self._cron_has_time(
                    cron,
                    batch_limit - accounted_pairs + len(active_stores),
                ):
                    return enqueued
                candidates = self._observation_candidates(
                    store,
                    1,
                    cursor=int(store.inventory_observation_cursor_id or 0),
                )
                if not candidates:
                    # The bounded wrapped query explicitly accounted for this
                    # store having no eligible pair.  No pair cursor moves.
                    store.sudo().write({
                        'inventory_observation_scheduled_at': fields.Datetime.now(),
                    })
                    active_stores.remove(store)
                    made_progress = True
                    if cron and cron._commit_progress(
                        1,
                        remaining=max(
                            batch_limit - accounted_pairs + len(active_stores),
                            0,
                        ),
                    ) <= 0:
                        return enqueued
                    continue
                binding = candidates[0]
                accounted, disposition = self._admit_fallback_pair(
                    store, binding, run_nonce,
                )
                if not accounted:
                    # Do not spin on a pair that was not safely accounted for;
                    # the pair cursor remains unchanged for scheduled repair.
                    # The store checkpoint may still move: the attempted
                    # stale-generation/uniqueness outcome is explicitly
                    # accounted, and retaining it in the oldest-store slot
                    # would let one unresolved store starve every other
                    # store.  The unchanged pair cursor guarantees that the
                    # pair itself is revisited after the next fair rotation.
                    store.sudo().write({
                        'inventory_observation_scheduled_at': (
                            fields.Datetime.now()
                        ),
                    })
                    active_stores.remove(store)
                    made_progress = True
                    continue
                store.sudo().write({
                    'inventory_observation_cursor_id': binding.id,
                    'inventory_observation_scheduled_at': fields.Datetime.now(),
                })
                if disposition == 'enqueued':
                    enqueued += 1
                accounted_pairs += 1
                made_progress = True
                if cron and cron._commit_progress(
                    1,
                    remaining=max(
                        batch_limit - accounted_pairs + len(active_stores),
                        0,
                    ),
                ) <= 0:
                    return enqueued
            if not made_progress:
                break
        return enqueued

    @api.model
    def _is_duplicate_admission_error(self, exc):
        text = str(exc)
        return (
            'A non-terminal job already holds this operation scope' in text
            or 'shopify_connector_job_store_operation_scope_key_uniq' in text
            or 'A job with this idempotency key already exists' in text
        )

    @api.model
    def _find_existing_observation_job(self, store, level_gid, payload_hash):
        Job = self.env['shopify.connector.job'].sudo()
        Job.flush_model()
        generation = int(store.connection_generation or 0)
        domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', INVENTORY_OBSERVATION_JOB_TYPE),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', store.id),
            ('shopify_target_gid', '=', level_gid),
        ]
        active = Job.search(
            domain + [
                ('expected_connection_generation', '=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ], order='id asc', limit=1,
        )
        if active:
            if active.state in ('queued', 'running', 'retry_waiting'):
                return active, 'coalesced'
            return active, 'unsafe_existing'
        stale = Job.search(
            domain + [
                ('expected_connection_generation', '!=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ], order='id asc', limit=1,
        )
        if stale:
            return stale, 'stale_active'
        if payload_hash:
            duplicate = Job.search(
                domain + [
                    ('expected_connection_generation', '=', generation),
                    ('payload_hash', '=', payload_hash),
                ], order='id desc', limit=1,
            )
            if duplicate:
                if duplicate.state == 'succeeded':
                    return duplicate, 'duplicate_succeeded'
                return duplicate, 'unsafe_terminal'
        return Job.browse(), False
