"""Read-first Shopify order webhook acceleration.

W1 owns public ingress, HMAC verification, delivery-ID deduplication and the
durable ``webhook_delivery_process`` job.  This module owns only the three
order topic handlers.  A handler consumes the verified evidence envelope,
validates the exact Shopify Order GID and admits the existing order importer;
it never parses the body again and never calls Shopify inline.
"""

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_sale.models.shopify_connector_order_importer import (
    ORDER_CANCELLED_PAYLOAD_PREFIX,
)


ORDER_WEBHOOK_TOPICS = (
    'orders/create',
    'orders/updated',
    'orders/cancelled',
)
ORDER_IMPORT_JOB_TYPE = 'order_import_sync'
TERMINAL_JOB_STATES = (
    'succeeded', 'failed_final', 'skipped', 'cancelled',
)
SAFE_ACTIVE_JOB_STATES = ('queued', 'running', 'retry_waiting')


def canonical_shopify_gid(value, resource_type):
    """Return a canonical, unparameterized Shopify GID or ``False``.

    Order and fulfillment webhook payloads carry both a legacy numeric ID and
    an explicit Admin GraphQL ID.  Only the latter is an identity.  The
    optional numeric ``id`` cross-check is accepted only when both values are
    plainly numeric; it detects a malformed mixed envelope without ever
    synthesizing a GID from the legacy value.
    """
    if not isinstance(value, str) or value.strip() != value:
        return False
    prefix = 'gid://shopify/%s/' % resource_type
    if not value.startswith(prefix) or len(value) > 256:
        return False
    suffix = value[len(prefix):]
    if (
        not suffix
        or '/' in suffix
        or '?' in suffix
        or '#' in suffix
        or any(char.isspace() for char in suffix)
    ):
        return False
    return value


def generation_aware_order_payload_hash(topic, updated_at, digest, generation):
    """Keep source ordering, body identity and generations in job identity.

    Shopify webhook timestamps are second-precision in the filtered payload;
    two different bodies can therefore share one timestamp.  Retaining the
    verified body digest alongside the timestamp prevents a later changed
    event from being mistaken for the earlier terminal import.  W1 already
    deduplicates the same delivery ID, so a repeated identical body remains a
    harmless terminal duplicate.
    """
    source = (
        '%s|body:%s' % (updated_at, digest)
        if updated_at else 'webhook:%s' % digest
    )
    if topic == 'orders/cancelled':
        source = ORDER_CANCELLED_PAYLOAD_PREFIX + source
    return '%s|connection_generation:%s' % (source, int(generation or 0))


class ShopifyConnectorSaleWebhookRegistry(models.AbstractModel):
    """Activate the assessed order topics through W1's add-only seam."""

    _inherit = 'shopify.connector.webhook.registry'

    @api.model
    def _extend_order_topic_registry(self, registry):
        catalog = self._get_topic_catalog()
        for topic in ORDER_WEBHOOK_TOPICS:
            spec = catalog.get(topic)
            if not spec:
                raise ValidationError(
                    'The order webhook topic %s is absent from the assessed '
                    'Shopify topic catalog; refusing activation.' % topic
                )
            if topic in registry:
                raise ValidationError(
                    'The order webhook topic %s is already registered by '
                    'another domain; refusing a colliding handler.' % topic
                )
            registry[topic] = dict(
                spec,
                domain='sale',
                handler=ORDER_IMPORT_JOB_TYPE,
                inline_expand_safe=True,
                # These are the only payload fields needed to correlate the
                # envelope.  The child importer performs the full read.
                include_fields=['admin_graphql_api_id', 'updated_at'],
            )
        return registry

    @api.model
    def _get_topic_registry(self):
        return self._extend_order_topic_registry(
            super()._get_topic_registry(),
        )

    @api.model
    def _extend_order_topic_handlers(self, handlers):
        for topic in ORDER_WEBHOOK_TOPICS:
            if topic in handlers:
                raise ValidationError(
                    'The order webhook topic %s already has a handler; '
                    'refusing a colliding handler.' % topic
                )
            handlers[topic] = self._handle_order_webhook
        return handlers

    @api.model
    def _get_topic_handlers(self):
        return self._extend_order_topic_handlers(
            dict(super()._get_topic_handlers()),
        )

    @api.model
    def _order_gid_from_delivery(self, delivery):
        """Return Shopify's explicit Order GID, never a guessed identity."""
        identity = delivery.resource_identity
        if not isinstance(identity, dict):
            return False
        gid = canonical_shopify_gid(
            identity.get('admin_graphql_api_id'), 'Order',
        )
        if not gid or delivery.resource_gid != gid:
            return False
        legacy_id = identity.get('id')
        if legacy_id is not None:
            if isinstance(legacy_id, bool):
                return False
            legacy_text = str(legacy_id).strip()
            suffix = gid.rsplit('/', 1)[-1]
            if legacy_text.isdigit() != suffix.isdigit():
                return False
            if legacy_text.isdigit() and legacy_text != suffix:
                return False
        return gid

    @api.model
    def _sale_settings(self, store):
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if not settings or not settings.sale_domain_enabled:
            return False, (
                'Order webhook retained as an acceleration signal: the sale '
                'domain is not enabled. Scheduled order reconciliation '
                'remains the recovery path.'
            )
        if settings.company_id.id != store.company_id.id:
            return False, (
                'Order webhook was held because store/settings company '
                'ownership could not be proven.'
            )
        return settings, False

    @api.model
    def _find_existing_order_job(self, store, gid, payload_hash):
        Job = self.env['shopify.connector.job'].sudo()
        Job.flush_model()
        generation = int(store.connection_generation or 0)
        domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', ORDER_IMPORT_JOB_TYPE),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', store.id),
            ('shopify_target_gid', '=', gid),
        ]
        exact = Job.search(
            domain + [
                ('expected_connection_generation', '=', generation),
                ('payload_hash', '=', payload_hash),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ], order='id asc', limit=1,
        )
        if exact:
            if exact.state in SAFE_ACTIVE_JOB_STATES:
                return exact, 'coalesced_exact'
            return exact, 'unsafe_existing'
        active = Job.search(
            domain + [
                ('expected_connection_generation', '=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ], order='id asc', limit=1,
        )
        if active:
            if active.state not in SAFE_ACTIVE_JOB_STATES:
                return active, 'unsafe_existing'
            # The operation-scope constraint prevents a successor while this
            # job is active.  Do not silently fold a newer body (especially a
            # cancellation signal) into older work.  W1's delivery row is the
            # durable successor evidence and manual review keeps it visible
            # until the scheduled overlapping scan repairs the watermark.
            return active, 'distinct_active_signal'
        stale_active = Job.search(
            domain + [
                ('expected_connection_generation', '!=', generation),
                ('state', 'not in', TERMINAL_JOB_STATES),
            ], order='id asc', limit=1,
        )
        if stale_active:
            return stale_active, 'stale_active'
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

    @api.model
    def _enqueue_order_import(self, store, delivery, gid, topic, generation):
        payload_hash = generation_aware_order_payload_hash(
            topic,
            fields.Datetime.to_string(delivery.source_updated_at)
            .replace(' ', 'T') + 'Z'
            if delivery.source_updated_at else False,
            delivery.payload_digest,
            generation,
        )
        existing, disposition = self._find_existing_order_job(
            store, gid, payload_hash,
        )
        if existing:
            return existing, disposition
        if int(store.connection_generation or 0) != int(generation):
            return self.env['shopify.connector.job'].browse(), 'stale_generation'
        Enqueue = self.env['shopify.connector.job.enqueue'].sudo()
        try:
            with self.env.cr.savepoint():
                job = Enqueue.enqueue(
                    store,
                    job_source='webhook',
                    job_type=ORDER_IMPORT_JOB_TYPE,
                    payload_hash=payload_hash,
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=gid,
                    trigger_origin_event_ref=delivery.delivery_id,
                    trigger_origin_event_at=delivery.triggered_at,
                )
            return job, 'enqueued'
        except IntegrityError:
            job, disposition = self._find_existing_order_job(
                store, gid, payload_hash,
            )
            if job:
                return job, disposition
            return self.env['shopify.connector.job'].browse(), 'unresolved_conflict'

    @api.model
    def _handle_order_webhook(self, delivery):
        """Validate the W1 envelope and enqueue one read-first order job."""
        if delivery.topic not in ORDER_WEBHOOK_TOPICS:
            return {
                'state': 'manual_review',
                'message': 'Unsupported order webhook topic; no job admitted.',
            }
        store = delivery.store_id.sudo()
        parent_job = delivery.job_id.sudo()
        if not store or not parent_job:
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook evidence has no delivery-resolved store '
                    'or processing job; no importer job was admitted.'
                ),
            }
        try:
            locked_state, locked_generation = store._lock_store_for_lifecycle()
            store.invalidate_recordset()
        except Exception as exc:
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook could not acquire the store lifecycle '
                    'fence (%s); no importer job was admitted.'
                    % type(exc).__name__
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
            or delivery.resource_type != 'orders'
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook store/company/API ownership did not match '
                    'the verified delivery; no importer job was admitted.'
                ),
            }
        if (
            locked_state != 'connected'
            or parent_job.expected_connection_generation != locked_generation
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook generation is stale or the store is not '
                    'connected. Scheduled reconciliation remains the recovery '
                    'path.'
                ),
            }
        settings, reason = self._sale_settings(store)
        if not settings:
            return {'state': 'ignored', 'message': reason}
        gid = self._order_gid_from_delivery(delivery)
        if not gid:
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook did not contain the exact allowlisted '
                    'admin_graphql_api_id Order GID; no numeric ID was '
                    'synthesized and no importer job was admitted.'
                ),
            }
        job, disposition = self._enqueue_order_import(
            store, delivery, gid, delivery.topic, locked_generation,
        )
        if not job:
            if disposition == 'stale_generation':
                message = (
                    'Order webhook generation changed before child admission; '
                    'scheduled reconciliation remains the recovery path.'
                )
            else:
                message = (
                    'Order webhook child-job admission hit an unresolved '
                    'uniqueness conflict; inspect preserved evidence.'
                )
            return {'state': 'manual_review', 'message': message}
        if disposition in (
            'stale_active', 'distinct_active_signal', 'unsafe_existing',
            'unsafe_terminal',
        ):
            reasons = {
                'stale_active': (
                    'an importer from an older connection generation is '
                    'still active'
                ),
                'distinct_active_signal': (
                    'a different same-order signal arrived while importer '
                    'job %s is active' % job.id
                ),
                'unsafe_existing': (
                    'the exact importer job %s is retrying or blocked' % job.id
                ),
                'unsafe_terminal': (
                    'the exact prior importer job %s ended in unsafe state %s'
                    % (job.id, job.state)
                ),
            }
            return {
                'state': 'manual_review',
                'message': (
                    'Order webhook retained for manual review because %s. '
                    'No successful duplicate was claimed; the overlapping '
                    'scheduled order scan remains the repair path.'
                    % reasons[disposition]
                ),
            }
        if disposition == 'enqueued':
            action = 'enqueued'
        elif disposition == 'duplicate_succeeded':
            action = 'matched the existing succeeded job'
        else:
            action = 'coalesced with the exact active job'
        cancellation_note = (
            ' Cancellation is evidence-only: no Odoo cancellation, refund, '
            'stock reversal or Shopify mutation is admitted.'
            if delivery.topic == 'orders/cancelled' else ''
        )
        return {
            'state': 'processed',
            'message': (
                'Order webhook accepted: %s job %s for Order %s. The child '
                'order_import_sync job performs the authoritative Shopify '
                'read; no remote call ran in webhook processing.%s'
                % (action, job.id, gid, cancellation_note)
            ),
        }
