"""Read-first product webhook acceleration.

The generic webhook addon owns HTTPS verification, delivery deduplication and
the durable ``webhook_delivery_process`` job.  This module owns only the two
product topic handlers.  A handler consumes the already verified delivery
envelope and admits the existing product importer job; it never parses or
re-reads the Shopify payload and never calls Shopify inline.
"""

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import ValidationError


PRODUCT_WEBHOOK_TOPICS = (
    'products/create', 'products/update', 'products/delete',
)
PRODUCT_IMPORT_JOB_TYPE = 'product_import_sync'
TERMINAL_JOB_STATES = (
    'succeeded', 'failed_final', 'skipped', 'cancelled',
)
SAFE_ACTIVE_JOB_STATES = ('queued', 'running', 'retry_waiting')


def generation_aware_product_payload_hash(updated_at, generation):
    """Keep the remote stamp while fencing work across reconnect epochs.

    Generation zero is retained for legacy/import fixtures and for backwards
    compatibility with the original scheduled-scan identity.  Every real
    reconnect has a positive generation, so a terminal row from an earlier
    connection cannot suppress a current-generation import.
    """
    if not generation:
        return updated_at
    return '%s|connection_generation:%s' % (updated_at, int(generation))


class ShopifyConnectorProductWebhookRegistry(models.AbstractModel):
    """Activate product topics through the generic registry seam."""

    _inherit = 'shopify.connector.webhook.registry'

    @api.model
    def _extend_product_topic_registry(self, registry):
        catalog = self._get_topic_catalog()
        for topic in PRODUCT_WEBHOOK_TOPICS:
            spec = catalog.get(topic)
            if not spec:
                raise ValidationError(
                    'The product webhook topic %s is missing from the '
                    'assessed Shopify topic catalog; refusing activation.'
                    % topic
                )
            if topic in registry:
                raise ValidationError(
                    'The product webhook topic %s is already registered by '
                    'another domain; refusing a colliding handler.' % topic
                )
            registry[topic] = dict(
                spec,
                domain='product',
                handler='product_import_sync',
                inline_expand_safe=True,
                # Every product topic requires Shopify's explicit Product GID.
                # Create/update also provide the raw snake_case `updated_at`
                # stamp; delete safely falls back to the verified body digest.
                include_fields=['admin_graphql_api_id', 'updated_at'],
            )
        return registry

    @api.model
    def _get_topic_registry(self):
        return self._extend_product_topic_registry(
            super()._get_topic_registry(),
        )

    @api.model
    def _extend_product_topic_handlers(self, handlers):
        for topic in PRODUCT_WEBHOOK_TOPICS:
            if topic in handlers:
                raise ValidationError(
                    'The product webhook topic %s already has a handler; '
                    'refusing a colliding handler.' % topic
                )
            handlers[topic] = self._handle_product_webhook
        return handlers

    @api.model
    def _get_topic_handlers(self):
        return self._extend_product_topic_handlers(
            dict(super()._get_topic_handlers()),
        )

    @api.model
    def _product_gid_from_delivery(self, delivery):
        """Return only Shopify's explicit Product GID, never a synthesized ID."""
        identity = delivery.resource_identity
        if not isinstance(identity, dict):
            return False
        gid = identity.get('admin_graphql_api_id')
        if not isinstance(gid, str) or not gid or gid.strip() != gid:
            return False
        if not gid.startswith('gid://shopify/Product/'):
            return False
        suffix = gid[len('gid://shopify/Product/'):]
        if not suffix or '/' in suffix or len(gid) > 256:
            return False
        # The generic envelope derives resource_gid from this same allowlisted
        # value.  Disagreement means evidence was corrupted or created by an
        # unsupported producer; fail closed rather than choosing an identity.
        if delivery.resource_gid != gid:
            return False
        return gid

    @api.model
    def _product_import_settings(self, store):
        settings = self.env['shopify.connector.store.settings'].sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        if not settings or not settings.product_domain_enabled:
            return False, (
                'Product webhook retained as an acceleration signal: product '
                'import is not enabled for this store. Scheduled reconciliation '
                'remains the recovery path.'
            )
        if settings.company_id.id != store.company_id.id:
            return False, (
                'Product webhook was held because store/settings company '
                'ownership could not be proven.'
            )
        if settings.product_first_sync_source == 'odoo_source':
            return False, (
                'Product webhook ignored because this store declares Odoo as '
                'the product source of truth.'
            )
        return settings, False

    @api.model
    def _find_existing_product_job(self, store, gid, payload_hash):
        Job = self.env['shopify.connector.job'].sudo()
        # ``operation_scope_key`` is a stored compute.  Flush before the
        # read-side coalescing check so a sibling admitted earlier in this
        # transaction is visible without deliberately executing a statement
        # that the unique index would reject.  The unique constraints and the
        # savepoint/IntegrityError branch below remain the cross-worker race
        # guard when another transaction inserts after this read.
        Job.flush_model()
        generation = int(store.connection_generation or 0)
        domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', PRODUCT_IMPORT_JOB_TYPE),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', store.id),
            ('shopify_target_gid', '=', gid),
        ]
        active = Job.search(
            domain + [
                ('expected_connection_generation', '=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ],
            order='id asc', limit=1,
        )
        if active:
            if active.state in SAFE_ACTIVE_JOB_STATES:
                return active, 'coalesced'
            return active, 'unsafe_existing'
        stale_active = Job.search(
            domain + [
                ('expected_connection_generation', '!=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ],
            order='id asc', limit=1,
        )
        if stale_active:
            return stale_active, 'stale_active'
        duplicate = Job.search(
            domain + [
                ('expected_connection_generation', '=', generation),
                ('payload_hash', '=', payload_hash),
            ],
            order='id desc', limit=1,
        )
        if duplicate:
            if duplicate.state == 'succeeded':
                return duplicate, 'duplicate_succeeded'
            return duplicate, 'unsafe_terminal'
        return self.env['shopify.connector.job'].browse(), False

    @api.model
    def _product_payload_hash(self, delivery, generation=0):
        """Use Shopify's canonical second-resolution updatedAt when present."""
        if delivery.source_updated_at:
            stamp = '%sZ' % fields.Datetime.to_string(
                delivery.source_updated_at,
            ).replace(' ', 'T')
            return generation_aware_product_payload_hash(stamp, generation)
        # A malformed/missing source timestamp is still safely deduplicated by
        # the verified body digest, while the child importer remains the
        # authoritative read path.
        return generation_aware_product_payload_hash(
            'webhook:%s' % delivery.payload_digest, generation,
        )

    @api.model
    def _enqueue_product_import(self, store, delivery, gid, generation=None):
        """Admit one product job, resolving uniqueness conflicts safely."""
        if generation is None:
            generation = int(store.connection_generation or 0)
        if int(store.connection_generation or 0) != int(generation):
            return self.env['shopify.connector.job'].browse(), 'stale_generation'
        payload_hash = self._product_payload_hash(delivery, generation)
        existing, disposition = self._find_existing_product_job(
            store, gid, payload_hash,
        )
        if existing:
            return existing, disposition
        Enqueue = self.env['shopify.connector.job.enqueue'].sudo()
        try:
            with self.env.cr.savepoint():
                job = Enqueue.enqueue(
                    store,
                    job_source='webhook',
                    job_type=PRODUCT_IMPORT_JOB_TYPE,
                    payload_hash=payload_hash,
                    # The store + product GID is the same scope key used by the
                    # scheduled scan, so a newer event coalesces with an
                    # in-flight import instead of creating concurrent readers.
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=gid,
                    # Delivery ID is durable correlation evidence.  The
                    # delivery row retains event_id/topic/digest separately.
                    trigger_origin_event_ref=delivery.delivery_id,
                    trigger_origin_event_at=delivery.triggered_at,
                )
            return job, 'enqueued'
        except IntegrityError:
            job, disposition = self._find_existing_product_job(
                store, gid, payload_hash,
            )
            if job:
                return job, disposition
            # A uniqueness conflict without a visible winner is a database
            # visibility anomaly, not permission to retry and risk duplicate
            # work.  The caller records manual review on the delivery.
            return self.env['shopify.connector.job'].browse(), 'unresolved_conflict'

    @api.model
    def _handle_product_webhook(self, delivery):
        """Validate envelope ownership and enqueue-only product work."""
        if delivery.topic not in PRODUCT_WEBHOOK_TOPICS:
            return {
                'state': 'manual_review',
                'message': (
                    'The product webhook handler received an unsupported '
                    'topic; no importer job was admitted.'
                ),
            }
        store = delivery.store_id.sudo()
        parent_job = delivery.job_id.sudo()
        if not store or not parent_job:
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook evidence has no delivery-resolved store '
                    'or processing job; no importer job was admitted.'
                ),
            }
        # The delivery parent was admitted before this handler ran.  Hold the
        # same sanctioned store lifecycle row lock through the generation
        # check and local child admission, so a disconnect/reconnect cannot
        # slip between validation and enqueue.  No network call occurs while
        # this lock is held.
        try:
            locked_state, locked_generation = store._lock_store_for_lifecycle()
            store.invalidate_recordset()
        except Exception as exc:
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook could not acquire the store lifecycle '
                    'fence (%s); no importer job was admitted.' % type(exc).__name__
                ),
            }
        shop_domain_matches = (
            isinstance(delivery.shop_domain, str)
            and isinstance(store.shop_domain, str)
            and delivery.shop_domain.lower() == store.shop_domain.lower()
        )
        if (
            delivery.company_id.id != store.company_id.id
            or parent_job.store_id != store
            or parent_job.company_id.id != store.company_id.id
            or not shop_domain_matches
            or delivery.api_version != store.api_version
            or delivery.resource_type != 'products'
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook store/company ownership did not match '
                    'the delivery job; no importer job was admitted.'
                ),
            }
        if (
            locked_state != 'connected'
            or parent_job.expected_connection_generation != locked_generation
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook was retained without enqueue because the '
                    'delivery generation is stale or the store is not connected. '
                    'Reconnect and run scheduled product reconciliation.'
                ),
            }
        settings, reason = self._product_import_settings(store)
        if not settings:
            return {
                'state': 'ignored',
                'message': reason,
            }
        gid = self._product_gid_from_delivery(delivery)
        if not gid:
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook did not contain the exact allowlisted '
                    'admin_graphql_api_id Product GID; no numeric ID was '
                    'synthesized and no importer job was admitted.'
                ),
            }
        job, disposition = self._enqueue_product_import(
            store, delivery, gid, generation=locked_generation,
        )
        if not job:
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook job admission hit an unresolved uniqueness '
                    'conflict. No resend or duplicate importer job was created; '
                    'inspect the preserved delivery and job evidence.'
                ),
            }
        if disposition == 'stale_generation':
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook generation changed before child admission; '
                    'the delivery was retained and scheduled reconciliation '
                    'remains the recovery path.'
                ),
            }
        if disposition == 'stale_active':
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook found an active importer job from an older '
                    'connection generation (job %s); no duplicate job was '
                    'created. Reconcile after reconnect.' % job.id
                ),
            }
        if disposition == 'unsafe_existing':
            return {
                'state': 'manual_review',
                'message': (
                    'Product importer job %s is in unsafe active state %s; '
                    'the webhook delivery did not create a replacement or '
                    'claim success.' % (job.id, job.state)
                ),
            }
        if disposition == 'unsafe_terminal':
            return {
                'state': 'manual_review',
                'message': (
                    'Product webhook matched prior importer job %s, which '
                    'ended in unsafe state %s. The delivery remains visible; '
                    'use the product import recovery route or scheduled '
                    'reconciliation rather than claiming success.'
                    % (job.id, job.state)
                ),
            }
        if disposition == 'enqueued':
            action = 'enqueued'
        elif disposition == 'duplicate_succeeded':
            action = 'matched the existing succeeded job in this connection generation'
        else:
            action = 'coalesced with active job'
        return {
            'state': 'processed',
            'message': (
                'Product webhook accepted: %s %s for Product %s. The child '
                'product_import_sync job performs the authoritative Shopify '
                'read; no remote call ran in webhook processing.'
                % (action, job.id, gid)
            ),
        }


class ShopifyConnectorProductScanGenerationFence(models.AbstractModel):
    """Keep the existing scheduled scan as a reconnect-safe fallback."""

    _inherit = 'shopify.connector.product.scan'

    @api.model
    def _enqueue_product(self, store, node, job_source):
        # The base scan deliberately uses the verbatim Shopify updatedAt as
        # its idempotency stamp.  Once W2 is installed, a positive lifecycle
        # generation is part of the local identity so an old terminal scan
        # row cannot suppress a post-reconnect fallback import.  Generation
        # zero keeps existing pre-W2 fixtures/backward-compatible rows stable.
        if store.connection_generation:
            node = dict(node)
            node['updatedAt'] = generation_aware_product_payload_hash(
                node.get('updatedAt'), store.connection_generation,
            )
        return super()._enqueue_product(store, node, job_source)
