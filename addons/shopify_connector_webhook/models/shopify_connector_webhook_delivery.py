"""Durable, payload-free Shopify webhook delivery evidence."""

import logging
import re
from datetime import datetime, timedelta, timezone

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from psycopg2 import IntegrityError

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)


DELIVERY_STATES = [
    ('received', 'Received'),
    ('queued', 'Queued'),
    ('processed', 'Processed'),
    ('ignored', 'Ignored'),
    ('failed', 'Failed'),
    ('manual_review', 'Manual Review'),
]
TERMINAL_DELIVERY_STATES = ('processed', 'ignored', 'failed', 'manual_review')
WEBHOOK_RETENTION_DAYS = 30
WEBHOOK_RETENTION_BATCH = 2000

_logger = logging.getLogger(__name__)

_DELIVERY_SERVICE_CONTEXT = 'shopify_connector_webhook_delivery_service'
_DELIVERY_SERVICE_SENTINEL = object()
_DELIVERY_RETENTION_CONTEXT = 'shopify_connector_webhook_delivery_retention'
_DELIVERY_RETENTION_SENTINEL = object()

# Shopify documents ``X-Shopify-Triggered-At`` as an RFC 3339 timestamp and
# currently shows nanosecond precision in its webhook examples.  Odoo's
# ``fields.Datetime`` is a timezone-naive UTC value, so accept the complete
# timestamp shape that can be represented by Python's datetime parser and
# normalize it before handing it to the ORM.  Requiring a timezone prevents a
# locale/server-timezone interpretation of a source watermark.
_SHOPIFY_WEBHOOK_DATETIME = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    r'(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$'
)


class ShopifyConnectorWebhookDelivery(models.Model):
    """One delivery envelope, never the Shopify payload.

    The model is intentionally an evidence envelope: it stores headers,
    digests, minimal resource identity, timing/order metadata, and processing
    state.  It never stores the request body or a parsed payload snapshot.
    """

    _name = 'shopify.connector.webhook.delivery'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Webhook Delivery'
    _order = 'received_at desc, id desc'

    store_id = fields.Many2one(
        'shopify.connector.store', required=True, index=True, readonly=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company', related='store_id.company_id', store=True, index=True,
        readonly=True,
    )
    delivery_id = fields.Char(required=True, index=True, readonly=True)
    event_id = fields.Char(index=True, readonly=True)
    topic = fields.Char(required=True, index=True, readonly=True)
    shop_domain = fields.Char(required=True, index=True, readonly=True)
    api_version = fields.Char(readonly=True)
    triggered_at = fields.Datetime(readonly=True)
    source_updated_at = fields.Datetime(readonly=True)
    received_at = fields.Datetime(
        required=True, default=fields.Datetime.now, index=True, readonly=True,
    )
    payload_digest = fields.Char(required=True, index=True, readonly=True)
    payload_size = fields.Integer(readonly=True)
    resource_type = fields.Char(readonly=True)
    resource_gid = fields.Char(index=True, readonly=True)
    # This JSON is constructed from a strict allowlist of resource IDs only;
    # it is not the incoming body and is safe to expose to connector roles.
    resource_identity = fields.Json(readonly=True)
    state = fields.Selection(
        selection=DELIVERY_STATES,
        required=True,
        default='received',
        index=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        'shopify.connector.job', index=True, readonly=True,
        ondelete='set null',
    )
    queued_at = fields.Datetime(readonly=True)
    processed_at = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)
    processing_note = fields.Text(readonly=True)

    _store_delivery_unique = models.Constraint(
        'UNIQUE(store_id, delivery_id)',
        'A Shopify webhook delivery may be recorded only once per store.',
    )

    @api.model
    def _service_context(self):
        return {
            _DELIVERY_SERVICE_CONTEXT: _DELIVERY_SERVICE_SENTINEL,
        }

    @api.model
    def _retention_context(self):
        return {
            _DELIVERY_RETENTION_CONTEXT: _DELIVERY_RETENTION_SENTINEL,
        }

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(_DELIVERY_SERVICE_CONTEXT)
            is not _DELIVERY_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook delivery evidence can only be created by the '
                'verified ingestion service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.su
            or self.env.context.get(_DELIVERY_SERVICE_CONTEXT)
            is not _DELIVERY_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook delivery evidence can only be changed by the '
                'verified ingestion or processing service.'
            )
        return super().write(vals)

    def unlink(self):
        if (
            not self.env.su
            or self.env.context.get(_DELIVERY_RETENTION_CONTEXT)
            is not _DELIVERY_RETENTION_SENTINEL
        ):
            raise AccessError(
                'Webhook delivery evidence is retained by the scheduled '
                'retention service.'
            )
        return super().unlink()

    # SEC-3: a delivery's diagnostic job must belong to the same Shopify
    # store.  Company equality is not enough because one company may own
    # several stores; the scope mixin also quarantines historic mismatches.
    @api.model
    def _sec3_parent_scope_relations(self):
        return (('job_id', 'store'),)

    @api.constrains('store_id', 'job_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()

    @api.model
    def _safe_text(self, value, limit=256):
        if not isinstance(value, str):
            return False
        value = value.strip()
        return value[:limit] if value else False

    @api.model
    def _parse_datetime(self, value):
        if not isinstance(value, str) or not value:
            return False
        if not _SHOPIFY_WEBHOOK_DATETIME.fullmatch(value):
            return False
        try:
            # ``datetime.fromisoformat`` on the supported Python runtime
            # accepts the RFC 3339 offset after the terminal ``Z`` is mapped
            # to its explicit UTC spelling.  It truncates any nanoseconds
            # beyond Python's microsecond precision, which is the precision
            # available to Odoo/PostgreSQL datetime values.
            parsed = datetime.fromisoformat(
                value[:-1] + '+00:00' if value.endswith('Z') else value,
            )
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return False
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError, OverflowError):
            return False

    @api.model
    def _minimal_resource_identity(self, payload):
        """Extract only non-PII resource identifiers from a parsed body."""
        if not isinstance(payload, dict):
            return {}
        allowed = (
            'id', 'admin_graphql_api_id', 'admin_graphql_api_gid',
            'product_id', 'variant_id', 'inventory_item_id', 'location_id',
            'order_id', 'fulfillment_id', 'customer_id', 'shop_id',
            'resource_id',
        )
        identity = {}
        for key in allowed:
            value = payload.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                value = str(value).strip()
                if value and len(value) <= 256:
                    identity[key] = value
        # A nested resource ID is common in a few Shopify topic envelopes;
        # only inspect the one fixed ``resource`` object and the same allowlist.
        nested = payload.get('resource')
        if isinstance(nested, dict):
            for key in allowed:
                value = nested.get(key)
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    value = str(value).strip()
                    if value and len(value) <= 256 and key not in identity:
                        identity[key] = value
        return identity

    @api.model
    def _resource_gid(self, identity):
        for key in (
            'admin_graphql_api_id', 'admin_graphql_api_gid', 'resource_id',
            'id', 'product_id', 'variant_id', 'inventory_item_id',
            'location_id', 'order_id', 'fulfillment_id', 'customer_id',
        ):
            value = identity.get(key)
            if isinstance(value, str) and value.startswith('gid://shopify/'):
                return value
        return False

    @api.model
    def _resource_type(self, topic):
        prefix = (topic or '').split('/', 1)[0]
        return self._safe_text(prefix, 64)

    @api.model
    def _ingest(
        self, store, delivery_id, event_id, topic, shop_domain, api_version,
        triggered_at, source_updated_at, payload_digest, payload_size,
        payload_identity,
    ):
        """Persist one verified envelope and enqueue its local job atomically.

        This method is called only after the controller has verified the raw
        body HMAC, exact shop header, API-version path/header, and topic.  It
        never receives or stores the request body.
        """
        store.ensure_one()
        if not delivery_id or not topic or not payload_digest:
            raise ValidationError('Verified webhook metadata is incomplete.')
        if api_version != SHOPIFY_API_VERSION:
            raise ValidationError(
                'Verified webhook metadata used an unsupported API version.'
            )
        identity = dict(payload_identity or {})
        Delivery = self.sudo().with_context(**self._service_context())
        values = {
            'store_id': store.id,
            'delivery_id': self._safe_text(delivery_id, 256),
            'event_id': self._safe_text(event_id, 256),
            'topic': self._safe_text(topic, 128),
            'shop_domain': self._safe_text(shop_domain, 255),
            # The controller has already compared the header to the
            # centralized connector constant; record that verified value, not
            # caller-supplied text that could make evidence disagree with the
            # endpoint actually used.
            'api_version': SHOPIFY_API_VERSION,
            'triggered_at': triggered_at or False,
            'source_updated_at': source_updated_at or False,
            'payload_digest': self._safe_text(payload_digest, 64),
            'payload_size': int(payload_size or 0),
            'resource_type': self._resource_type(topic),
            'resource_gid': self._resource_gid(identity),
            'resource_identity': identity,
            'state': 'received',
        }
        try:
            with self.env.cr.savepoint():
                delivery = Delivery.create(values)
        except IntegrityError:
            delivery = Delivery.search([
                ('store_id', '=', store.id),
                ('delivery_id', '=', values['delivery_id']),
            ], limit=1)
            if not delivery:
                raise
            return delivery, True

        # A delivery received after a local disconnect is retained but is not
        # turned into a business job.  This acknowledges Shopify safely while
        # making the stale/uninstalled condition visible to an operator.
        if store.state != 'connected':
            delivery._service_write({
                'state': 'ignored',
                'processed_at': fields.Datetime.now(),
                'processing_note': (
                    'Delivery retained without enqueue because the store is '
                    'not connected (%s). Reconcile after reconnect.'
                    % store.state
                ),
            })
            return delivery, False

        try:
            job = self.env['shopify.connector.job.enqueue'].sudo().enqueue(
                store,
                'webhook',
                'webhook_delivery_process',
                payload_hash=values['payload_digest'],
                res_model=self._name,
                res_id=delivery.id,
                shopify_target_gid=values['resource_gid'],
                trigger_origin_event_ref=values['event_id'],
                trigger_origin_event_at=values['triggered_at'],
            )
        except ValidationError as exc:
            # A concurrent lifecycle transition may have quiesced the store
            # after the local state check. Keep the verified evidence and make
            # the outcome actionable; do not retry the HTTP request inline.
            delivery._service_write({
                'state': 'manual_review',
                'processed_at': fields.Datetime.now(),
                'last_error': 'Webhook enqueue was refused: %s' % str(exc),
                'processing_note': (
                    'The delivery was verified but no business job was '
                    'created. Reconcile after the store is connected.'
                ),
            })
            return delivery, False

        delivery._service_write({
            'state': 'queued',
            'job_id': job.id,
            'queued_at': fields.Datetime.now(),
        })
        # Remove one full worker cycle from domain webhooks without moving a
        # Shopify read or business write into the HTTP request. Explicitly
        # opted-in registry handlers may only validate this durable envelope
        # and enqueue their read-first child. The parent job remains queued as
        # replay/recovery evidence; when the dispatcher reaches it,
        # `_process_queued()` is an idempotent no-op for a terminal delivery.
        Registry = self.env['shopify.connector.webhook.registry']
        if (
            self.env.context.get('inline_webhook_expansion')
            and Registry.inline_expand_safe(topic)
        ):
            try:
                with self.env.cr.savepoint():
                    delivery._process_queued()
            except Exception as exc:
                # The ordinary parent job is still queued and is the durable
                # recovery path. An optional latency optimization must not
                # become lost evidence or a false acknowledgement.
                delivery.invalidate_recordset()
                _logger.warning(
                    'Inline webhook expansion deferred to parent job %s (%s).',
                    job.id, type(exc).__name__,
                )
        return delivery, False

    def _service_write(self, values):
        self.ensure_one()
        allowed = {
            'state', 'job_id', 'queued_at', 'processed_at', 'last_error',
            'processing_note',
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValidationError(
                'Webhook delivery service cannot write fields: %s.'
                % ', '.join(sorted(unknown))
            )
        return self.sudo().with_context(**self._service_context()).write(values)

    def _process_queued(self):
        """Run the local registry outcome for one durable delivery job."""
        self.ensure_one()
        if self.state in TERMINAL_DELIVERY_STATES:
            return
        if self.state not in ('received', 'queued'):
            raise ValidationError('A webhook delivery is not processable.')
        outcome = self.env['shopify.connector.webhook.registry'].process_delivery(
            self
        )
        if not isinstance(outcome, dict):
            raise ValidationError('The webhook topic handler returned no outcome.')
        state = outcome.get('state')
        if state not in ('processed', 'ignored', 'failed', 'manual_review'):
            raise ValidationError('The webhook topic handler returned an invalid state.')
        note = outcome.get('message') or 'Webhook delivery processing completed.'
        values = {
            'state': state,
            'processed_at': fields.Datetime.now(),
            'processing_note': str(note)[:2000],
        }
        if state in ('failed', 'manual_review'):
            values['last_error'] = str(note)[:2000]
        self._service_write(values)
        return outcome

    @api.model
    def run_retention_sweep(self):
        """Delete terminal delivery envelopes older than 30 days in a batch."""
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may run webhook '
                'retention maintenance.'
            )
        cutoff = fields.Datetime.now() - timedelta(days=WEBHOOK_RETENTION_DAYS)
        deliveries = self.sudo().search([
            ('state', 'in', TERMINAL_DELIVERY_STATES),
            ('received_at', '<', cutoff),
        ], order='id asc', limit=WEBHOOK_RETENTION_BATCH)
        if not deliveries:
            return 0
        deliveries.with_context(
            **self._retention_context()
        ).unlink()
        return len(deliveries)
