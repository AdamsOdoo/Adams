"""W3 inventory-level webhook registry and enqueue-only parent handler."""

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import (
    INVENTORY_OBSERVATION_HANDLER,
    INVENTORY_OBSERVATION_JOB_TYPE,
    INVENTORY_WEBHOOK_INCLUDE_FIELDS,
    INVENTORY_WEBHOOK_TOPIC,
)


class ShopifyConnectorInventoryWebhookRegistry(models.AbstractModel):
    """Activate exactly one topic through W1's add-only registry seam."""

    _inherit = 'shopify.connector.webhook.registry'

    @api.model
    def _extend_inventory_topic_registry(self, registry):
        catalog = self._get_topic_catalog()
        spec = catalog.get(INVENTORY_WEBHOOK_TOPIC)
        if not spec:
            raise ValidationError(
                'The inventory webhook topic is absent from the assessed '
                'Shopify topic catalog; refusing activation.'
            )
        if INVENTORY_WEBHOOK_TOPIC in registry:
            raise ValidationError(
                'The inventory webhook topic is already registered by '
                'another domain; refusing a colliding handler.'
            )
        registry[INVENTORY_WEBHOOK_TOPIC] = dict(
            spec,
            domain='inventory',
            handler=INVENTORY_OBSERVATION_HANDLER,
            include_fields=list(INVENTORY_WEBHOOK_INCLUDE_FIELDS),
        )
        return registry

    @api.model
    def _get_topic_registry(self):
        return self._extend_inventory_topic_registry(
            super()._get_topic_registry(),
        )

    @api.model
    def _extend_inventory_topic_handlers(self, handlers):
        if INVENTORY_WEBHOOK_TOPIC in handlers:
            raise ValidationError(
                'The inventory webhook topic already has a handler; refusing '
                'a colliding handler.'
            )
        handlers[INVENTORY_WEBHOOK_TOPIC] = self._handle_inventory_webhook
        return handlers

    @api.model
    def _get_topic_handlers(self):
        return self._extend_inventory_topic_handlers(
            dict(super()._get_topic_handlers()),
        )

    @api.model
    def _inventory_level_gid_from_delivery(self, delivery):
        """Use only the explicit Shopify InventoryLevel GID."""
        return self.env[
            'shopify.connector.inventory.observation.service'
        ]._delivery_level_gid(delivery)

    @api.model
    def _inventory_payload_hash(self, delivery, level_gid, generation):
        source_stamp = False
        if delivery.source_updated_at:
            source_stamp = '%sZ' % fields.Datetime.to_string(
                delivery.source_updated_at,
            ).replace(' ', 'T')
        return self.env[
            'shopify.connector.inventory.observation.service'
        ]._observation_payload_hash(
            level_gid, source_stamp, delivery.payload_digest, generation,
        )

    @api.model
    def _find_existing_inventory_observation_job(
        self, store, level_gid, payload_hash,
    ):
        return self.env[
            'shopify.connector.inventory.observation.service'
        ]._find_existing_observation_job(store, level_gid, payload_hash)

    @api.model
    def _enqueue_inventory_observation(
        self, store, delivery, level_gid, generation=None,
    ):
        if generation is None:
            generation = int(store.connection_generation or 0)
        if int(store.connection_generation or 0) != int(generation):
            return self.env['shopify.connector.job'].browse(), 'stale_generation'
        payload_hash = self._inventory_payload_hash(
            delivery, level_gid, generation,
        )
        existing, disposition = self._find_existing_inventory_observation_job(
            store, level_gid, payload_hash,
        )
        if existing:
            return existing, disposition
        Enqueue = self.env['shopify.connector.job.enqueue'].sudo()
        try:
            with self.env.cr.savepoint():
                job = Enqueue.enqueue(
                    store,
                    job_source='webhook',
                    job_type=INVENTORY_OBSERVATION_JOB_TYPE,
                    payload_hash=payload_hash,
                    # Store-scoped parent identity keeps all existing exact
                    # level events on one local operation scope. The child
                    # resolves the exact binding after its authoritative read.
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=level_gid,
                    trigger_origin_event_ref=delivery.delivery_id,
                    trigger_origin_event_at=delivery.triggered_at,
                )
            return job, 'enqueued'
        except (IntegrityError, ValidationError) as exc:
            # The core enqueue service preserves the DB unique constraints;
            # only a visible winner is a benign concurrent coalesce. Any
            # unresolved conflict is surfaced as manual review by the parent
            # delivery and is never retried by creating a second job.
            if not self._is_duplicate_admission_error(exc):
                raise
            existing, disposition = self._find_existing_inventory_observation_job(
                store, level_gid, payload_hash,
            )
            if existing:
                return existing, disposition
            return self.env['shopify.connector.job'].browse(), 'unresolved_conflict'

    @api.model
    def _is_duplicate_admission_error(self, exc):
        text = str(exc)
        return (
            'A non-terminal job already holds this operation scope' in text
            or 'shopify_connector_job_store_operation_scope_key_uniq' in text
            or 'A job with this idempotency key already exists' in text
        )

    @api.model
    def _handle_inventory_webhook(self, delivery):
        """Validate W1 evidence and enqueue exactly one read-only child."""
        if delivery.topic != INVENTORY_WEBHOOK_TOPIC:
            return {
                'state': 'manual_review',
                'message': 'The inventory webhook handler received an unsupported topic.',
            }
        store = delivery.store_id.sudo()
        parent_job = delivery.job_id.sudo()
        if not store or not parent_job:
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook evidence has no delivery-resolved '
                    'store or processing job; no observation was admitted.'
                ),
            }
        try:
            locked_state, locked_generation = store._lock_store_for_lifecycle()
            store.invalidate_recordset()
        except Exception as exc:
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook could not acquire the store lifecycle '
                    'fence (%s); no observation was admitted.' % type(exc).__name__
                ),
            }
        if (
            delivery.company_id.id != store.company_id.id
            or parent_job.store_id != store
            or parent_job.company_id.id != store.company_id.id
            or not self._shop_domains_match(
                delivery.shop_domain, store.shop_domain,
            )
            or delivery.api_version != store.api_version
            or delivery.resource_type != 'inventory_levels'
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook store/company ownership did not match '
                    'the delivery job; no observation was admitted.'
                ),
            }
        if (
            locked_state != 'connected'
            or parent_job.expected_connection_generation != locked_generation
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook was retained without enqueue because '
                    'the delivery generation is stale or the store is not '
                    'connected. Scheduled observation remains the recovery path.'
                ),
            }
        settings = self.env['shopify.connector.store.settings'].sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        if not settings or not settings.inventory_domain_enabled:
            return {
                'state': 'ignored',
                'message': (
                    'Inventory webhook retained as a drift signal because '
                    'the inventory domain is not enabled for this store.'
                ),
            }
        if settings.company_id != store.company_id:
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook was held because store/settings '
                    'company ownership could not be proven.'
                ),
            }
        level_gid = self._inventory_level_gid_from_delivery(delivery)
        if not level_gid:
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook did not contain the exact allowlisted '
                    'admin_graphql_api_id InventoryLevel GID; no identity was '
                    'synthesized and no child was admitted.'
                ),
            }
        job, disposition = self._enqueue_inventory_observation(
            store, delivery, level_gid, generation=locked_generation,
        )
        if not job:
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory observation admission hit an unresolved '
                    'uniqueness conflict; no duplicate child was created.'
                ),
            }
        if disposition == 'stale_generation':
            return {
                'state': 'manual_review',
                'message': (
                    'Inventory webhook generation changed before child '
                    'admission; scheduled observation remains the recovery path.'
                ),
            }
        if disposition == 'stale_active':
            return {
                'state': 'manual_review',
                'message': (
                    'An active inventory observation from an older connection '
                    'generation exists; no duplicate child was created.'
                ),
            }
        if disposition == 'enqueued':
            action = 'enqueued'
        elif disposition == 'duplicate':
            action = 'matched the existing terminal observation job'
        else:
            action = 'coalesced with the active observation job'
        return {
            'state': 'processed',
            'message': (
                'Inventory webhook accepted: %s %s for InventoryLevel %s. '
                'The child inventory_observation_sync job performs the '
                'authoritative Shopify read; no stock or outbound mutation '
                'runs in webhook processing.'
                % (action, job.id, level_gid)
            ),
        }

    @api.model
    def _shop_domains_match(self, left, right):
        return (
            isinstance(left, str)
            and isinstance(right, str)
            and left.lower() == right.lower()
        )
