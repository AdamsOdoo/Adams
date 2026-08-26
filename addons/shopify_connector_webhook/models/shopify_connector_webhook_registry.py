"""The add-only webhook topic registry seam.

The receiver accepts only topics returned by this registry.  Domain addons can
extend the registry with ``_inherit`` and add a handler for a topic, but the
HTTP route never accepts a caller-supplied job type or callback.  W1 keeps a
catalog of assessed MVP topics separate from the active subscriptions so an
unhandled topic cannot be subscribed and then silently ignored.
"""

from odoo import api, models


MVP_TOPIC_CATALOG = {
    # Product topics are catalogued for a later read-first domain handler.
    'products/create': {
        'enum': 'PRODUCTS_CREATE',
        'label': 'Products created',
    },
    'products/update': {
        'enum': 'PRODUCTS_UPDATE',
        'label': 'Products updated',
    },
    'products/delete': {
        'enum': 'PRODUCTS_DELETE',
        'label': 'Products deleted',
    },
    'inventory_levels/update': {
        'enum': 'INVENTORY_LEVELS_UPDATE',
        'label': 'Inventory levels updated',
    },
    'orders/create': {
        'enum': 'ORDERS_CREATE',
        'label': 'Orders created',
    },
    'orders/updated': {
        'enum': 'ORDERS_UPDATED',
        'label': 'Orders updated',
    },
    'orders/cancelled': {
        'enum': 'ORDERS_CANCELLED',
        'label': 'Orders cancelled',
    },
    'refunds/create': {
        'enum': 'REFUNDS_CREATE',
        'label': 'Refunds created',
    },
    'fulfillments/create': {
        'enum': 'FULFILLMENTS_CREATE',
        'label': 'Fulfillments created',
    },
    'fulfillments/update': {
        'enum': 'FULFILLMENTS_UPDATE',
        'label': 'Fulfillments updated',
    },
    # App uninstall is handled by W1 as a fenced reconnect-needed signal.  It
    # never trusts the payload to mutate an Odoo store record.
    'app/uninstalled': {
        'enum': 'APP_UNINSTALLED',
        'label': 'App uninstalled',
    },
}

# W1 deliberately subscribes only to a topic with a real core handler.  The
# remaining topics are catalogued for later domain addons, but are not
# accepted as active subscriptions or silently marked processed.  Product,
# inventory, order and fulfillment addons extend this active registry when
# they install their read-first handlers.
MVP_ACTIVE_TOPIC_REGISTRY = {
    'app/uninstalled': MVP_TOPIC_CATALOG['app/uninstalled'],
}


class ShopifyConnectorWebhookRegistry(models.AbstractModel):
    """Stateless topic and domain-handler registry."""

    _name = 'shopify.connector.webhook.registry'
    _description = 'Shopify Connector Webhook Topic Registry'

    @api.model
    def _get_topic_registry(self):
        """Return an add-only copy of the allowed topic registry.

        A later domain module must call ``super()`` and update this mapping;
        it may not replace an existing topic with a caller-controlled value.
        The returned dictionaries are copied so a request cannot mutate the
        process-global registry.
        """
        return {
            topic: dict(spec)
            for topic, spec in MVP_ACTIVE_TOPIC_REGISTRY.items()
        }

    @api.model
    def _get_topic_catalog(self):
        """Return known Shopify topics without making them subscribable.

        This is intentionally separate from ``_get_topic_registry``: a domain
        topic may be documented/assessed before its read-first handler exists,
        but W1 must not create a Shopify subscription that would only be
        acknowledged and ignored.
        """
        return {
            topic: dict(spec) for topic, spec in MVP_TOPIC_CATALOG.items()
        }

    @api.model
    def topic_spec(self, topic):
        spec = self._get_topic_registry().get(topic)
        return dict(spec) if spec else False

    @api.model
    def allowed_topics(self):
        return tuple(sorted(self._get_topic_registry()))

    @api.model
    def _get_topic_handlers(self):
        """Return topic -> delivery handler method names.

        The only core-owned active action is the app-uninstall signal;
        product/order/inventory/fulfillment modules extend this map in later
        W2/W3 slices after their authoritative reads are available.
        """
        return {
            'app/uninstalled': self._handle_app_uninstalled,
        }

    @api.model
    def _handle_app_uninstalled(self, delivery):
        """Fence the store into the sanctioned reconnect-needed state."""
        store = delivery.store_id.sudo()
        parent_job = delivery.job_id.sudo()
        try:
            locked_state, locked_generation = store._lock_store_for_lifecycle()
            store.invalidate_recordset()
        except Exception as exc:
            return {
                'state': 'manual_review',
                'message': (
                    'App-uninstalled evidence could not acquire the store '
                    'lifecycle fence (%s); no connection state changed.'
                    % type(exc).__name__
                ),
            }
        if (
            not parent_job
            or parent_job.store_id != store
            or delivery.company_id != store.company_id
            or parent_job.company_id != store.company_id
            or delivery.shop_domain != store.shop_domain
            or delivery.api_version != store.api_version
            or parent_job.expected_connection_generation != locked_generation
        ):
            return {
                'state': 'manual_review',
                'message': (
                    'App-uninstalled evidence belongs to a stale or mismatched '
                    'connection generation; the current connection was not '
                    'fenced. Inspect the delivery and reconcile subscriptions.'
                ),
            }
        if locked_state in ('connected', 'reconnect_needed'):
            # This is the existing lifecycle service, which takes the store
            # row lock, preserves one-way disconnects, and writes an audited
            # lifecycle job.  No payload identity is trusted here.
            store.action_mark_reconnect_needed(
                reason=(
                    'Shopify reported app/uninstalled for connection '
                    'generation %s; reconnect required.' % locked_generation
                ),
            )
            return {
                'state': 'processed',
                'message': (
                    'Shopify reported app uninstallation; the store was '
                    'fenced to reconnect-needed by the lifecycle service.'
                ),
            }
        return {
            'state': 'ignored',
            'message': (
                'Shopify reported app uninstallation while the store was '
                'already outside an active connection state.'
            ),
        }

    @api.model
    def process_delivery(self, delivery):
        """Process only the local W1 outcome for a queued delivery.

        Domain addons may extend ``_get_topic_handlers`` and return their own
        safe, authoritative-read workflow.  The base implementation never
        treats an unhandled topic as a business success.
        """
        handler = self._get_topic_handlers().get(delivery.topic)
        if handler is None:
            return {
                'state': 'ignored',
                'message': (
                    'Delivery retained as an acceleration signal; no domain '
                    'handler is installed for this topic yet. Scheduled '
                    'reconciliation remains authoritative.'
                ),
            }
        return handler(delivery)
