"""Read-first Shopify fulfillment webhook acceleration.

The generic webhook addon owns ingress and durable delivery evidence.  This
module only admits a resolver job keyed by Shopify's explicit Fulfillment GID;
the resolver performs one authoritative GraphQL read and hands the existing
fulfillment inbound-observation path an exact order binding.
"""

from psycopg2 import IntegrityError

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (
    FulfillmentReadError,
)


FULFILLMENT_WEBHOOK_TOPICS = (
    'fulfillments/create',
    'fulfillments/update',
)
FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE = 'fulfillment_webhook_resolve'
FULFILLMENT_INBOUND_JOB_TYPE = 'fulfillment_inbound_observation'
TERMINAL_JOB_STATES = (
    'succeeded', 'failed_final', 'skipped', 'cancelled',
)
SAFE_ACTIVE_JOB_STATES = ('queued', 'running', 'retry_waiting')


def canonical_shopify_gid(value, resource_type):
    """Return a canonical, unparameterized Shopify GID or ``False``."""
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


class ShopifyConnectorFulfillmentWebhookRegistry(models.AbstractModel):
    """Activate the assessed fulfillment topics through W1."""

    _inherit = 'shopify.connector.webhook.registry'

    @api.model
    def _extend_fulfillment_topic_registry(self, registry):
        catalog = self._get_topic_catalog()
        for topic in FULFILLMENT_WEBHOOK_TOPICS:
            spec = catalog.get(topic)
            if not spec:
                raise ValidationError(
                    'The fulfillment webhook topic %s is absent from the '
                    'assessed Shopify topic catalog; refusing activation.'
                    % topic
                )
            if topic in registry:
                raise ValidationError(
                    'The fulfillment webhook topic %s is already registered '
                    'by another domain; refusing a colliding handler.' % topic
                )
            registry[topic] = dict(
                spec,
                domain='fulfillment',
                handler=FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
                inline_expand_safe=True,
                # `order_id` is deliberately not requested or trusted.  The
                # resolver obtains the exact Order GID from Shopify's node.
                include_fields=['admin_graphql_api_id'],
            )
        return registry

    @api.model
    def _get_topic_registry(self):
        return self._extend_fulfillment_topic_registry(
            super()._get_topic_registry(),
        )

    @api.model
    def _extend_fulfillment_topic_handlers(self, handlers):
        for topic in FULFILLMENT_WEBHOOK_TOPICS:
            if topic in handlers:
                raise ValidationError(
                    'The fulfillment webhook topic %s already has a handler; '
                    'refusing a colliding handler.' % topic
                )
            handlers[topic] = self._handle_fulfillment_webhook
        return handlers

    @api.model
    def _get_topic_handlers(self):
        return self._extend_fulfillment_topic_handlers(
            dict(super()._get_topic_handlers()),
        )

    @api.model
    def _fulfillment_gid_from_delivery(self, delivery):
        """Return only the explicit Fulfillment GID; never use `order_id`."""
        identity = delivery.resource_identity
        if not isinstance(identity, dict):
            return False
        gid = canonical_shopify_gid(
            identity.get('admin_graphql_api_id'), 'Fulfillment',
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
    def _fulfillment_settings(self, store):
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if not settings or not settings.fulfillment_domain_enabled:
            return False, (
                'Fulfillment webhook retained as an acceleration signal: '
                'the fulfillment domain is not enabled. Scheduled fulfillment '
                'reconciliation remains the recovery path.'
            )
        if settings.company_id.id != store.company_id.id:
            return False, (
                'Fulfillment webhook was held because store/settings company '
                'ownership could not be proven.'
            )
        return settings, False

    @api.model
    def _find_existing_resolver_job(self, store, gid, payload_hash):
        Job = self.env['shopify.connector.job'].sudo()
        Job.flush_model()
        generation = int(store.connection_generation or 0)
        domain = [
            ('store_id', '=', store.id),
            ('job_type', '=', FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE),
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
    def _enqueue_resolver(self, store, delivery, gid, generation):
        # Delivery IDs are already deduplicated by W1.  Keeping the ID in the
        # child identity means a later update of the same fulfillment creates
        # a new terminal-safe observation while an in-flight one coalesces.
        payload_hash = (
            'fulfillment_webhook:%s:%s|connection_generation:%s'
            % (gid, delivery.delivery_id, int(generation or 0))
        )
        existing, disposition = self._find_existing_resolver_job(
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
                    job_type=FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
                    payload_hash=payload_hash,
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=gid,
                    trigger_origin_event_ref=delivery.delivery_id,
                    trigger_origin_event_at=delivery.triggered_at,
                )
            return job, 'enqueued'
        except IntegrityError:
            job, disposition = self._find_existing_resolver_job(
                store, gid, payload_hash,
            )
            if job:
                return job, disposition
            return self.env['shopify.connector.job'].browse(), 'unresolved_conflict'

    @api.model
    def _handle_fulfillment_webhook(self, delivery):
        """Validate the W1 envelope and enqueue a read-first resolver only."""
        if delivery.topic not in FULFILLMENT_WEBHOOK_TOPICS:
            return {
                'state': 'manual_review',
                'message': (
                    'Unsupported fulfillment webhook topic; no resolver job '
                    'was admitted.'
                ),
            }
        store = delivery.store_id.sudo()
        parent_job = delivery.job_id.sudo()
        if not store or not parent_job:
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook evidence has no delivery-resolved '
                    'store or processing job; no resolver job was admitted.'
                ),
            }
        try:
            locked_state, locked_generation = store._lock_store_for_lifecycle()
            store.invalidate_recordset()
        except Exception as exc:
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook could not acquire the store lifecycle '
                    'fence (%s); no resolver job was admitted.'
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
            or delivery.resource_type != 'fulfillments'
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook store/company/API ownership did not '
                    'match the verified delivery; no resolver job was admitted.'
                ),
            }
        if (
            locked_state != 'connected'
            or parent_job.expected_connection_generation != locked_generation
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook generation is stale or the store is '
                    'not connected. Reconcile after reconnect.'
                ),
            }
        settings, reason = self._fulfillment_settings(store)
        if not settings:
            return {'state': 'ignored', 'message': reason}
        gid = self._fulfillment_gid_from_delivery(delivery)
        if not gid:
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook did not contain the exact allowlisted '
                    'admin_graphql_api_id Fulfillment GID; numeric order_id '
                    'was not trusted and no resolver job was admitted.'
                ),
            }
        job, disposition = self._enqueue_resolver(
            store, delivery, gid, locked_generation,
        )
        if not job:
            if disposition == 'stale_generation':
                message = (
                    'Fulfillment webhook generation changed before resolver '
                    'admission; scheduled reconciliation remains the recovery '
                    'path.'
                )
            else:
                message = (
                    'Fulfillment webhook resolver admission hit an unresolved '
                    'uniqueness conflict; inspect preserved evidence.'
                )
            return {'state': 'manual_review', 'message': message}
        if disposition in (
            'stale_active', 'distinct_active_signal', 'unsafe_existing',
            'unsafe_terminal',
        ):
            reasons = {
                'stale_active': (
                    'a resolver from an older connection generation is '
                    'still active'
                ),
                'distinct_active_signal': (
                    'a different same-fulfillment signal arrived while '
                    'resolver job %s is active' % job.id
                ),
                'unsafe_existing': (
                    'the exact resolver job %s is retrying or blocked' % job.id
                ),
                'unsafe_terminal': (
                    'the exact prior resolver job %s ended in unsafe state %s'
                    % (job.id, job.state)
                ),
            }
            return {
                'state': 'manual_review',
                'message': (
                    'Fulfillment webhook retained for manual review because '
                    '%s. No successful duplicate was claimed; scheduled '
                    'fulfillment reconciliation remains the repair path.'
                    % reasons[disposition]
                ),
            }
        if disposition == 'enqueued':
            action = 'enqueued'
        elif disposition == 'duplicate_succeeded':
            action = 'matched the existing succeeded resolver'
        else:
            action = 'coalesced with the exact active resolver'
        return {
            'state': 'processed',
            'message': (
                'Fulfillment webhook accepted: %s resolver job %s for '
                'Fulfillment %s. The resolver performs a read-only exact-GID '
                'lookup; no webhook body application or remote mutation ran.'
                % (action, job.id, gid)
            ),
        }


class ShopifyConnectorFulfillmentWebhookResolver(models.AbstractModel):
    """Resolve a Fulfillment GID to an exact bound Order GID."""

    _inherit = 'shopify.connector.fulfillment.service'

    FULFILLMENT_NODE_QUERY = """
query ConnectorFulfillmentWebhookNode($fulfillmentId: ID!) {
  node(id: $fulfillmentId) {
    id
    __typename
    ... on Fulfillment {
      order { id }
    }
  }
}
"""

    @api.model
    def _resolve_order_gid(self, job, store, fulfillment_gid):
        fulfillment_gid = canonical_shopify_gid(
            fulfillment_gid, 'Fulfillment',
        )
        if not fulfillment_gid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'The fulfillment resolver job did not carry a canonical '
                'Fulfillment GID.',
            )
        data = self._read_data(
            job, store, self.FULFILLMENT_NODE_QUERY,
            {'fulfillmentId': fulfillment_gid},
        )
        node = data.get('node')
        if not isinstance(node, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify returned no Fulfillment node for the webhook GID.',
            )
        if (
            node.get('__typename') != 'Fulfillment'
            or node.get('id') != fulfillment_gid
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify Fulfillment read returned a mismatched node identity.',
            )
        order = node.get('order')
        order_gid = (
            isinstance(order, dict) and order.get('id')
        )
        order_gid = canonical_shopify_gid(order_gid, 'Order')
        if not order_gid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify Fulfillment read omitted a canonical Order GID; the '
                'numeric webhook order_id was not used as a fallback.',
            )
        return order_gid

    @api.model
    def _handle_fulfillment_webhook_resolve(self, job):
        store = job.store_id
        fulfillment_gid = canonical_shopify_gid(
            job.shopify_target_gid, 'Fulfillment',
        )
        if not fulfillment_gid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Fulfillment webhook resolver has no canonical target GID.',
            )
        try:
            order_gid = self._resolve_order_gid(
                job, store, fulfillment_gid,
            )
        except JobHandlerError:
            raise
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class, exc.reason, exc.technical_detail,
            ) from exc
        except ShopifyQuiescedError as exc:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'The fulfillment webhook resolver was fenced by a store '
                'lifecycle change; retry after reconnect.',
                type(exc).__name__,
            ) from exc
        except FulfillmentReadError as exc:
            raise JobHandlerError(
                exc.error_class, exc.message,
            ) from exc
        except Exception as exc:
            # Keep an unknown implementation failure classified without ever
            # treating an incomplete remote read as successful evidence.
            raise JobHandlerError(
                'unknown_system_error',
                'The fulfillment webhook resolver read could not complete; '
                'scheduled reconciliation remains the recovery path.',
                type(exc).__name__,
            ) from exc
        # Re-read and fence the lifecycle row after the network read.  A
        # disconnect/reconnect may have raced the resolver while its committed
        # call lease was active; do not admit a child observation into an old
        # generation or claim that a stale read was current.
        locked_state, locked_generation = store._lock_store_for_lifecycle()
        store.invalidate_recordset()
        if (
            locked_state != 'connected'
            or locked_generation != job.expected_connection_generation
        ):
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'The fulfillment webhook resolver became stale during its '
                'read; reconnect and scheduled reconciliation are required.',
            )
        order_binding = self.env[
            'shopify.connector.order.binding'
        ].sudo().search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', order_gid),
        ], limit=1)
        if not order_binding:
            raise JobHandlerError(
                'fulfillment_notification_confirmation_missing',
                'Fulfillment %s resolved to Order %s, but no exact order '
                'binding exists for this store. The resolver created no '
                'fulfillment or tracking mutation; import/bind the order and '
                'run scheduled fulfillment reconciliation.'
                % (fulfillment_gid, order_gid),
            )
        order_binding = order_binding.sudo().try_lock_for_update()
        if not order_binding:
            raise JobHandlerError(
                'concurrency_race_conflict',
                'The exact order binding disappeared or changed while the '
                'fulfillment webhook was being resolved. No child job was '
                'admitted; scheduled reconciliation remains the repair path.',
            )
        order_binding.invalidate_recordset()
        if (
            not order_binding.exists()
            or order_binding.store_id != store
            or order_binding.shopify_gid != order_gid
        ):
            raise JobHandlerError(
                'concurrency_race_conflict',
                'The exact order binding no longer matches the resolved '
                'Shopify Order. No child job was admitted.',
            )
        Service = self.env['shopify.connector.fulfillment.service']
        payload_hash = (
            'webhook:%s:%s' % (
                fulfillment_gid,
                job.trigger_origin_event_ref or job.id,
            )
        )
        observation = Service._enqueue_once(
            store,
            'webhook',
            FULFILLMENT_INBOUND_JOB_TYPE,
            payload_hash,
            'shopify.connector.order.binding',
            order_binding.id,
        )
        if not observation:
            raise JobHandlerError(
                'mapping_missing',
                'Fulfillment %s resolved to Order %s, but the inbound '
                'observation job could not be admitted. Reconcile manually.'
                % (fulfillment_gid, order_gid),
            )
        expected_hash = payload_hash
        safe_active_states = ('queued', 'running', 'retry_waiting')
        if (
            observation.store_id != store
            or observation.job_type != FULFILLMENT_INBOUND_JOB_TYPE
            or observation.res_model != 'shopify.connector.order.binding'
            or observation.res_id != order_binding.id
            or observation.payload_hash != expected_hash
            or observation.expected_connection_generation
            != job.expected_connection_generation
            or observation.state not in safe_active_states + ('succeeded',)
        ):
            raise JobHandlerError(
                'fulfillment_notification_confirmation_missing',
                'Fulfillment %s resolved to Order %s, but downstream '
                'observation admission returned non-identical, stale, failed, '
                'blocked or cancelled work (job %s, state %s). No successful '
                'observation was claimed; reconcile manually.'
                % (
                    fulfillment_gid, order_gid,
                    observation.id, observation.state,
                ),
            )
        # The existing observation handler performs the authoritative read of
        # every fulfillment for the exact order binding and only records
        # evidence/review.  It never invokes fulfillment_create or tracking.
        return observation
