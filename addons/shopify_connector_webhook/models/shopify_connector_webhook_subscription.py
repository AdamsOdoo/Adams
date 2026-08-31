"""Shopify webhook subscription registry and guarded lifecycle service."""

import hashlib
import uuid
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from psycopg2 import IntegrityError

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    canonical_sha256,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
from odoo.addons.shopify_connector_core.tools.redaction import redact
from odoo.addons.shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (
    WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT,
    WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT,
)
from odoo.addons.shopify_connector_webhook.integration.shopify.webhook_subscription_read_gateway import (
    SUBSCRIPTIONS_QUERY as SUBSCRIPTION_LIST_QUERY,
)


SUBSCRIPTION_STATES = [
    ('expected', 'Expected'),
    ('queued', 'Change queued'),
    ('pending_verification', 'Pending verification'),
    ('active', 'Active'),
    ('missing', 'Missing'),
    ('error', 'Error'),
    ('manual_review', 'Manual review'),
]

_SUBSCRIPTION_SERVICE_CONTEXT = 'shopify_connector_webhook_subscription_service'
_SUBSCRIPTION_SERVICE_SENTINEL = object()
CREATE_RETRY_STATES = frozenset(
    ('succeeded', 'failed_final', 'cancelled', 'skipped')
)


def _create_retry_allowed(subscription, store_state, bootstrap):
    """Return whether reconciliation may enqueue a create attempt."""
    if bootstrap or store_state != 'connected':
        return False
    last_job = subscription.last_job_id
    return not last_job or last_job.state in CREATE_RETRY_STATES


def _bounded_sweep_remaining(selected_count, processed):
    """Report only the current bounded cron batch's remaining work."""
    return max(int(selected_count or 0) - int(processed or 0), 0)


def _latest_reconciled_at(values):
    """Return the latest persisted reconciliation timestamp, if any.

    New expected subscription rows legitimately have no reconciliation
    timestamp yet. Filter those falsey placeholders before comparing
    datetimes so a mixed registry remains safely observable while work is
    admitted.
    """
    reconciled = [value for value in (values or ()) if value]
    return max(reconciled) if reconciled else False


def _scheduled_reconciliation_bucket_limits(limit, null_cursor_count):
    """Return the bounded NULL-first selection plan.

    The caller performs two ordinary Odoo searches: never rely on database
    NULL ordering, and spend the remainder of the same bounded batch on the
    oldest timestamped cursors. Keeping this arithmetic pure makes the
    fairness boundary independently testable without a database.
    """
    batch_limit = max(1, min(int(limit or 20), 100))
    null_limit = min(
        batch_limit, max(int(null_cursor_count or 0), 0),
    )
    return batch_limit, null_limit, batch_limit - null_limit


def _scheduled_reconciliation_bucket_ids(null_ids, timestamped_ids, limit):
    """Select NULL-cursor ids first, then the oldest timestamped ids."""
    _batch_limit, null_limit, timestamped_limit = (
        _scheduled_reconciliation_bucket_limits(limit, len(null_ids))
    )
    return tuple(null_ids[:null_limit]) + tuple(
        timestamped_ids[:timestamped_limit]
    )


def _uri_digest(uri):
    if not isinstance(uri, str) or not uri:
        return False
    return hashlib.sha256(uri.encode('utf-8')).hexdigest()


class ShopifyWebhookSchemaError(Exception):
    """Shopify returned a response shape this webhook domain cannot trust."""


def _api_version_handle(value):
    """Validate Shopify's 2026-07 ``ApiVersion`` object and return its handle.

    In the current Admin GraphQL schema ``WebhookSubscription.apiVersion`` is
    an object, not a scalar string.  The handle is the only value used for
    subscription comparison/evidence, but the complete selected object is
    checked so a partial or silently changed schema cannot be treated as a
    healthy subscription.
    """
    if not isinstance(value, dict):
        raise ShopifyWebhookSchemaError(
            'Shopify returned a malformed webhook API version object.'
        )
    handle = value.get('handle')
    display_name = value.get('displayName')
    supported = value.get('supported')
    if not isinstance(handle, str) or not handle.strip():
        raise ShopifyWebhookSchemaError(
            'Shopify returned a webhook API version without a handle.'
        )
    if not isinstance(display_name, str) or not display_name.strip():
        raise ShopifyWebhookSchemaError(
            'Shopify returned a webhook API version without a display name.'
        )
    if not isinstance(supported, bool):
        raise ShopifyWebhookSchemaError(
            'Shopify returned a webhook API version with an invalid support flag.'
        )
    return handle.strip()[:32]


class ShopifyConnectorWebhookSubscription(models.Model):
    """Expected-vs-observed subscription state for one store/topic."""

    _name = 'shopify.connector.webhook.subscription'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Webhook Subscription'
    _order = 'store_id, topic, id'

    store_id = fields.Many2one(
        'shopify.connector.store', required=True, index=True, readonly=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company', related='store_id.company_id', store=True, index=True,
        readonly=True,
    )
    topic = fields.Char(required=True, index=True, readonly=True)
    topic_enum = fields.Char(required=True, readonly=True)
    expected = fields.Boolean(default=True, readonly=True)
    expected_api_version = fields.Char(
        required=True, default=SHOPIFY_API_VERSION, readonly=True,
    )
    # A non-empty value is the minimum field contract required by a domain
    # handler.  NULL/empty observed includeFields means Shopify returned an
    # unfiltered subscription, which contains the full topic payload.
    expected_include_fields = fields.Json(readonly=True)
    expected_callback_url_digest = fields.Char(readonly=True)
    shopify_subscription_gid = fields.Char(index=True, readonly=True)
    actual_topic = fields.Char(readonly=True)
    actual_uri_digest = fields.Char(readonly=True)
    actual_api_version = fields.Char(readonly=True)
    actual_format = fields.Char(readonly=True)
    actual_include_fields = fields.Json(readonly=True)
    state = fields.Selection(
        selection=SUBSCRIPTION_STATES,
        required=True,
        default='expected',
        index=True,
        readonly=True,
    )
    last_reconciled_at = fields.Datetime(readonly=True)
    last_action_at = fields.Datetime(readonly=True)
    hmac_credential_epoch = fields.Integer(readonly=True)
    last_job_id = fields.Many2one(
        'shopify.connector.job', index=True, readonly=True, ondelete='set null',
    )
    last_error = fields.Text(readonly=True)
    operator_note = fields.Text(readonly=True)

    _store_topic_unique = models.Constraint(
        'UNIQUE(store_id, topic)',
        'A webhook topic may be expected only once per Shopify store.',
    )
    _store_gid_unique = models.UniqueIndex(
        '(store_id, shopify_subscription_gid) '
        'WHERE shopify_subscription_gid IS NOT NULL',
        'A Shopify subscription GID may belong to only one topic per store.',
    )

    @api.model
    def _service_context(self):
        return {
            _SUBSCRIPTION_SERVICE_CONTEXT: _SUBSCRIPTION_SERVICE_SENTINEL,
        }

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(_SUBSCRIPTION_SERVICE_CONTEXT)
            is not _SUBSCRIPTION_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook subscription records can only be changed by the '
                'connector subscription service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.su
            or self.env.context.get(_SUBSCRIPTION_SERVICE_CONTEXT)
            is not _SUBSCRIPTION_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook subscription records can only be changed by the '
                'connector subscription service.'
            )
        return super().write(vals)

    def unlink(self):
        raise AccessError(
            'Webhook subscription evidence is retained; use reconciliation '
            'to remove a Shopify subscription.'
        )

    def _service_write(self, values):
        self.ensure_one()
        allowed = {
            'topic_enum', 'expected', 'expected_api_version',
            'expected_include_fields',
            'expected_callback_url_digest', 'shopify_subscription_gid',
            'actual_topic', 'actual_uri_digest', 'actual_api_version',
            'actual_format', 'actual_include_fields', 'state',
            'last_reconciled_at', 'last_action_at',
            'hmac_credential_epoch', 'last_job_id', 'last_error',
            'operator_note',
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValidationError(
                'Webhook subscription service cannot write fields: %s.'
                % ', '.join(sorted(unknown))
            )
        return self.sudo().with_context(**self._service_context()).write(values)

    @api.model
    def _credential_epoch(self, store):
        credential = self.env[
            'shopify.connector.store.credential'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        return credential.credential_epoch if credential else 0

    @api.model
    def _hmac_epoch_for_admitted_job(self, job):
        """Read the current HMAC epoch under the finalization lock fence.

        A mutation reconciliation consequence is the last local write after a
        Shopify read-back.  It must not copy an epoch from a caller payload or
        from the original attempt snapshot: a credential replacement may have
        raced the network call.  Reuse the sanctioned store -> credential
        lifecycle lock order and compare the immutable job generation while
        both rows are held.  If the job no longer describes the connected
        store, refuse the consequence so the dispatcher retries/reroutes the
        full reconciliation rather than recording stale HMAC proof.
        """
        job.ensure_one()
        store = job.store_id
        locked_state, locked_generation = store._lock_store_for_lifecycle()
        if (
            locked_state != 'connected'
            or locked_generation != job.expected_connection_generation
        ):
            raise ShopifyQuiescedError(
                'Webhook mutation evidence was superseded before local '
                'HMAC proof finalization.'
            )
        Credential = self.env[
            'shopify.connector.store.credential'
        ].sudo()
        credential_version = Credential._lifecycle_credential_version(
            store, lock=True,
        )
        if not credential_version:
            raise ShopifyQuiescedError(
                'Webhook mutation evidence has no current credential epoch.'
            )
        credential = Credential.browse(credential_version[0])
        credential.invalidate_recordset()
        if credential.credential_state != 'present':
            raise ShopifyQuiescedError(
                'Webhook mutation evidence has no present credential epoch.'
            )
        return credential.credential_epoch

    @api.model
    def _has_hmac_client_secret(self, store):
        """Return whether this store can verify Shopify webhook signatures."""
        Credential = self.env['shopify.connector.store.credential']
        credential = Credential.sudo().search([('store_id', '=', store.id)], limit=1)
        return bool(
            credential
            and credential.credential_state == 'present'
            and Credential._get_client_secret(store)
        )

    @api.model
    def _require_hmac_client_secret(self, store):
        """Fail closed before any subscription job or remote operation."""
        if not self._has_hmac_client_secret(store):
            raise ValidationError(
                'Webhook subscriptions require a stored Shopify app client '
                'secret for HMAC verification. Offline access-token mode alone '
                'cannot be used for webhook setup; use Client ID + Client '
                'secret token-exchange mode and retry.'
            )
        return True

    @api.model
    def _ensure_expected_for_store(self, store):
        """Materialize the registry rows without contacting Shopify."""
        store.ensure_one()
        Registry = self.env['shopify.connector.webhook.registry']
        Secret = self.env['shopify.connector.webhook.secret']
        callback_digest = Secret._callback_url_digest_for_store(store)
        Subscription = self.sudo().with_context(**self._service_context())
        result = self.browse()
        for topic, spec in Registry._get_topic_registry().items():
            record = Subscription.search([
                ('store_id', '=', store.id), ('topic', '=', topic),
            ], limit=1)
            values = {
                'store_id': store.id,
                'topic': topic,
                'topic_enum': spec['enum'],
                'expected': True,
                'expected_api_version': SHOPIFY_API_VERSION,
                'expected_include_fields': list(
                    spec.get('include_fields') or [],
                ),
                'expected_callback_url_digest': callback_digest,
                'state': 'expected',
            }
            if not record:
                try:
                    with self.env.cr.savepoint():
                        record = Subscription.create(values)
                except IntegrityError:
                    record = Subscription.search([
                        ('store_id', '=', store.id), ('topic', '=', topic),
                    ], limit=1)
                    if not record:
                        raise
            else:
                changed = (
                    not record.expected
                    or record.topic_enum != values['topic_enum']
                    or record.expected_api_version != values['expected_api_version']
                    or (record.expected_include_fields or [])
                    != values['expected_include_fields']
                    or record.expected_callback_url_digest
                    != values['expected_callback_url_digest']
                )
                if changed:
                    # Keep the old GID so a later reconciliation can identify
                    # a stale callback and route it for safe manual review;
                    # never silently delete an unknown remote subscription.
                    record._service_write({
                        'expected': True,
                        'topic_enum': values['topic_enum'],
                        'expected_api_version': values['expected_api_version'],
                        'expected_include_fields':
                            values['expected_include_fields'],
                        'expected_callback_url_digest':
                            values['expected_callback_url_digest'],
                        'state': 'expected',
                        'last_error': False,
                    })
            result |= record
        return result

    @api.model
    def _reconciliation_run_key(self, source):
        """Return a bounded scheduled slot or a coalescing manual slot."""
        if source == 'manual_sync':
            # A stable manual slot coalesces double-clicks while a job is
            # active.  _enqueue_job_with_recovery adds one bounded nonce only
            # after a terminal row, so a later explicit retry is still able
            # to proceed without creating concurrent duplicate work.
            return 'manual'
        now = fields.Datetime.to_datetime(fields.Datetime.now())
        slot_minute = (now.minute // 15) * 15
        return 'slot-%s' % now.replace(
            minute=slot_minute, second=0, microsecond=0,
        ).strftime('%Y%m%d%H%M')

    @api.model
    def _preflight_enqueue_job(
        self, store, job_type, payload_hash, res_model, res_id,
        shopify_target_gid=False,
    ):
        """Find a visible duplicate before asking PostgreSQL to reject it.

        The job table keeps the database unique constraints as the final
        cross-worker guard.  A normal sequential retry, however, should not
        deliberately execute a statement known to violate one of those
        constraints: Odoo logs the rejected SQL at ERROR level even when the
        caller catches the ``IntegrityError`` inside a savepoint.

        The two identities have different meanings and are checked
        separately:

        * an active row with the same job/target operation identity is the
          in-flight work to coalesce with (the operation-scope constraint is
          independent of the payload hash); and
        * a terminal row with the same payload is immutable evidence, so a
          fresh bounded nonce is returned to permit an explicit retry without
          colliding with its lifetime idempotency key.

        The SQL constraints and the savepoint/``IntegrityError`` recovery in
        ``_enqueue_job_with_recovery`` remain mandatory for the narrow window
        in which another transaction inserts after this read.  This method is
        only a read-side fast path for already-visible rows.
        """
        Job = self.env['shopify.connector.job'].sudo()
        # ``operation_scope_key`` and the computed idempotency key are stored
        # computes.  Flush the model so a sibling job admitted earlier in this
        # transaction is visible to this read; the unique indexes remain the
        # authoritative guard for independent workers.
        Job.flush_model()
        identity = [
            ('store_id', '=', store.id),
            ('job_type', '=', job_type),
            ('res_model', '=', res_model or False),
            ('res_id', '=', res_id or False),
            ('shopify_target_gid', '=', shopify_target_gid or False),
        ]
        active = Job.search(
            identity + [
                ('expected_connection_generation', '=',
                 store.connection_generation),
                ('state', 'not in', tuple(CREATE_RETRY_STATES)),
            ],
            order='id asc', limit=1,
        )
        if active:
            return active, payload_hash

        terminal = Job.search(
            identity + [('payload_hash', '=', payload_hash)],
            order='id desc', limit=1,
        )
        if terminal:
            return self.env['shopify.connector.job'].browse(), canonical_sha256({
                'base_payload_hash': payload_hash,
                'terminal_retry_nonce': uuid.uuid4().hex,
            })
        return self.env['shopify.connector.job'].browse(), payload_hash

    @api.model
    def _enqueue_job_with_recovery(
        self, store, source, job_type, payload_hash, res_model, res_id,
        shopify_target_gid=False,
    ):
        """Create one job with savepoint-safe terminal retry semantics.

        Core idempotency is intentionally immutable for a logical attempt, but
        periodic/manual reconciliation must be able to create a new bounded
        attempt after an earlier terminal row.  A unique conflict first
        returns an active job; if only terminal evidence exists, one fresh
        nonce is used.  Every insert is inside a savepoint so a caught
        IntegrityError never poisons the caller transaction.
        """
        Enqueue = self.env['shopify.connector.job.enqueue'].sudo()
        Job = self.env['shopify.connector.job'].sudo()
        candidate = payload_hash
        existing, candidate = self._preflight_enqueue_job(
            store,
            job_type,
            candidate,
            res_model,
            res_id,
            shopify_target_gid,
        )
        if existing:
            return existing
        for retry in range(2):
            try:
                with self.env.cr.savepoint():
                    return Enqueue.enqueue(
                        store,
                        source,
                        job_type,
                        payload_hash=candidate,
                        res_model=res_model,
                        res_id=res_id,
                        shopify_target_gid=shopify_target_gid,
                    )
            except IntegrityError:
                active = Job.search([
                    ('store_id', '=', store.id),
                    ('job_type', '=', job_type),
                    ('res_model', '=', res_model),
                    ('res_id', '=', res_id),
                    ('expected_connection_generation', '=',
                     store.connection_generation),
                    ('state', 'not in', (
                        'succeeded', 'failed_final', 'skipped', 'cancelled',
                    )),
                ], limit=1)
                if active:
                    return active
                # A reconnect makes a setup parent job stale, but its
                # operation-scope key still serializes the old active row.
                # Retire only that read-only parent through the durable job
                # state path, then retry once with a bounded nonce.  Mutation
                # jobs are deliberately not auto-retired: an uncertain remote
                # effect remains a manual-review fence.
                if (
                    job_type == 'webhook_subscription_reconcile'
                    and source == 'setup_readiness_check'
                ):
                    stale = Job.search([
                        ('store_id', '=', store.id),
                        ('job_type', '=', job_type),
                        ('res_model', '=', res_model),
                        ('res_id', '=', res_id),
                        ('expected_connection_generation', '!=',
                         store.connection_generation),
                        ('state', 'not in', (
                            'succeeded', 'failed_final', 'skipped',
                            'cancelled',
                        )),
                    ], order='id asc')
                    for stale_job in stale:
                        if stale_job.state == 'blocked_manual_review':
                            raise ValidationError(
                                'A stale webhook reconciliation job is in '
                                'manual review; resolve it before starting a '
                                'new setup generation.'
                            )
                        if stale_job._has_mutation_attempt_evidence():
                            raise ValidationError(
                                'A stale webhook reconciliation job carries '
                                'mutation evidence; resolve it manually before '
                                'starting a new setup generation.'
                            )
                        from_state = stale_job.state
                        stale_job.sudo().write({
                            'state': 'cancelled',
                            'cancel_reason': (
                                'Superseded by a newer connection generation; '
                                'no remote mutation evidence was attached.'
                            ),
                            'finished_at': fields.Datetime.now(),
                            'manual_review_subreason': False,
                        })
                        stale_job._log_transition(
                            'manual_action',
                            'Stale setup reconciliation retired before a '
                            'fresh current-generation enqueue.',
                            from_state=from_state,
                            to_state='cancelled',
                        )
                if retry:
                    raise
                candidate = canonical_sha256({
                    'base_payload_hash': payload_hash,
                    'terminal_retry_nonce': uuid.uuid4().hex,
                })
        raise ValidationError('Webhook job enqueue did not produce a job.')

    @api.model
    def _read_actual_subscriptions(self, store, job, lifecycle=False):
        """Read Shopify state through a durable business admission lease.

        Connected reconciliation uses the core ``execute_business`` context
        manager, which admits the running job/generation and holds a committed
        call lease for each page. Bootstrap uses one fixed
        ``readiness_probe`` lifecycle snapshot across all pages and applies the
        matching post-network supersession fence before returning evidence.
        There is no unleased ``execute()`` fallback here.
        """
        if not job or not getattr(job, 'id', False):
            raise ValidationError(
                'Webhook subscription reads require a running reconciliation '
                'job and its business admission lease.'
            )
        client = self.env['shopify.connector.api.client']
        after = None
        actual = []
        observed_identity = False
        lifecycle_snapshot = False
        if lifecycle:
            # One lifecycle admission/token must cover the complete paginated
            # read. Re-admitting each page could mix credential generations in
            # one evidence set after a reconnect or secret replacement.
            lifecycle_snapshot = client._admit_lifecycle(
                store, 'readiness_probe',
            )
        # The bounded page cap prevents a malformed cursor loop from turning a
        # reconciliation job into unbounded Shopify cost.
        for _page in range(20):
            variables = {'first': 100, 'after': after}
            if lifecycle:
                result = client._send_lifecycle(
                    store,
                    SUBSCRIPTION_LIST_QUERY,
                    lifecycle_snapshot['token'],
                    variables,
                )
            else:
                with client.execute_business(
                    job, store, SUBSCRIPTION_LIST_QUERY, variables,
                ) as page_result:
                    result = page_result
            data = result.get('data') or {}
            shop = data.get('shop') or {}
            observed_identity = shop.get('myshopifyDomain') or observed_identity
            connection = data.get('webhookSubscriptions') or {}
            nodes = connection.get('nodes') or []
            if not isinstance(nodes, list):
                raise ValidationError('Shopify returned malformed webhook subscriptions.')
            for node in nodes:
                if not isinstance(node, dict) or not node.get('id'):
                    continue
                uri = node.get('uri') or node.get('callbackUrl') or ''
                include_fields = self._normalize_include_fields(
                    node.get('includeFields'),
                )
                actual.append({
                    'id': str(node['id'])[:256],
                    'topic': str(node.get('topic') or '')[:128],
                    'uri_digest': _uri_digest(uri),
                    'observed_api_version': _api_version_handle(
                        node.get('apiVersion')
                    ),
                    'format': str(node.get('format') or '')[:32],
                    # Shopify returns an empty list for an unfiltered
                    # subscription on some API revisions, and a null-like
                    # value on others.  A non-empty list is an explicit
                    # allowlist and must satisfy the domain contract.
                    'include_fields': include_fields,
                })
            page_info = connection.get('pageInfo') or {}
            if not page_info.get('hasNextPage'):
                break
            next_cursor = page_info.get('endCursor')
            if not next_cursor or next_cursor == after:
                raise ValidationError('Shopify returned an invalid webhook cursor.')
            after = next_cursor
        else:
            raise ValidationError('Shopify webhook subscription pagination exceeded its safety cap.')
        if observed_identity != store.shop_domain:
            raise ValidationError(
                'Shopify returned a different shop identity during webhook '
                'subscription reconciliation.'
            )
        if lifecycle and store._lifecycle_probe_superseded(lifecycle_snapshot):
            # The supersession check holds the lifecycle lock until this
            # transaction commits, so no evidence write can follow a stale
            # snapshot. The durable job will retry with a fresh generation.
            raise ShopifyQuiescedError(
                'Webhook bootstrap was superseded by a lifecycle or '
                'credential change; no evidence was written.'
            )
        return actual

    @api.model
    def _validate_subscription_create_preconditions(self, subscription):
        """Let domain addons fence every path that can require a create.

        Stale-callback replacement deletes the preserved remote subscription
        before reconciliation creates its successor.  The same domain
        readiness checks that protect an ordinary create must therefore pass
        both when replacement is requested and again immediately before its
        delete is admitted.
        """
        return True

    @api.model
    def _enqueue_subscription_mutation(self, subscription, action, source):
        self._require_hmac_client_secret(subscription.store_id)
        if action == 'create':
            self._validate_subscription_create_preconditions(subscription)
        job_type = (
            'webhook_subscription_create'
            if action == 'create' else 'webhook_subscription_delete'
        )
        target = subscription.shopify_subscription_gid if action == 'delete' else False
        run_key = self._reconciliation_run_key(source)
        payload_hash = canonical_sha256({
            'action': action,
            'subscription_id': subscription.id,
            'topic': subscription.topic,
            'topic_enum': subscription.topic_enum,
            'callback_url_digest': subscription.expected_callback_url_digest,
            'target': target,
            'run_key': run_key,
        })
        job = self._enqueue_job_with_recovery(
            subscription.store_id,
            source,
            job_type,
            payload_hash,
            self._name,
            subscription.id,
            target,
        )
        subscription._service_write({
            'state': 'queued',
            'last_job_id': job.id,
            'last_action_at': fields.Datetime.now(),
            'last_error': False,
        })
        return job

    @api.model
    def _include_fields_match(self, expected, observed):
        """Return whether a remote field filter satisfies a domain contract.

        Shopify treats a null/empty includeFields value as the unfiltered
        payload, so it contains every ordinary top-level field.  A non-empty
        allowlist must explicitly contain every field required by the active
        domain handler.  This prevents a pre-existing filtered subscription
        that omits ``admin_graphql_api_id`` from being marked healthy.
        """
        expected = {
            str(value) for value in (expected or [])
            if isinstance(value, str) and value
        }
        if not expected:
            return True
        if observed in (False, None, []):
            return True
        if not isinstance(observed, list):
            return False
        return expected.issubset(set(observed))

    @api.model
    def _normalize_include_fields(self, raw):
        """Normalize Shopify's nullable includeFields response safely."""
        if raw is None:
            return []
        if not isinstance(raw, list):
            return ['__malformed_include_fields__']
        return sorted({
            str(value)[:128] for value in raw
            if isinstance(value, str) and value
        })

    @api.model
    def _reconcile_registry_removed_subscriptions(
        self, store, active_topics, actual, source='scheduled_sync',
        epoch=False,
    ):
        """Retire domain rows removed by an optional addon safely.

        Uninstalling a domain addon must not issue a remote delete inside the
        uninstall transaction, and it must not leave the old Shopify
        subscription falsely active.  A normal W1 reconciliation first reads
        Shopify, then marks the row ``expected=False`` and queues a durable
        Layer-2 delete only when the exact previously recorded subscription
        GID is present in that fresh read-back.  Missing/unknown identities
        stay manual-review evidence; no identity is guessed from a topic.
        """
        active_topics = tuple(active_topics or ())
        removed = self.sudo().search([
            ('store_id', '=', store.id),
            ('expected', '=', True),
            ('topic', 'not in', list(active_topics)),
        ], order='id asc')
        if not removed:
            return removed
        actual_by_gid = {
            item.get('id'): item for item in actual
            if isinstance(item, dict) and item.get('id')
        }
        Job = self.env['shopify.connector.job'].sudo()
        terminal = ('succeeded', 'failed_final', 'skipped', 'cancelled')
        now = fields.Datetime.now()
        for subscription in removed:
            gid = subscription.shopify_subscription_gid or False
            base = {
                'expected': False,
                'last_reconciled_at': now,
                'hmac_credential_epoch': epoch,
            }
            if not gid:
                subscription._service_write(dict(
                    base,
                    state='manual_review',
                    last_error=(
                        'The webhook topic %s is no longer provided by an '
                        'installed domain handler, but no stored Shopify '
                        'subscription GID exists. No remote delete was issued; '
                        'resolve the preserved evidence manually.'
                        % subscription.topic
                    ),
                    operator_note=(
                        'Domain capability removal requires an exact remote '
                        'subscription GID before cleanup.'
                    ),
                ))
                continue
            remote = actual_by_gid.get(gid)
            if not remote:
                # A different remote GID for the retired topic is evidence of
                # a second/unknown subscription, not proof that cleanup is
                # complete.  Preserve that read-back for an operator instead
                # of guessing which Shopify object may be deleted.
                same_topic = [
                    item for item in actual
                    if isinstance(item, dict)
                    and item.get('topic') == subscription.topic_enum
                ]
                if same_topic:
                    observed = same_topic[0]
                    subscription._service_write(dict(
                        base,
                        state='manual_review',
                        actual_topic=observed.get('topic') or False,
                        actual_uri_digest=observed.get('uri_digest') or False,
                        actual_api_version=(
                            observed.get('observed_api_version') or False
                        ),
                        actual_format=observed.get('format') or False,
                        actual_include_fields=(
                            observed.get('include_fields') or []
                        ),
                        last_error=(
                            'The webhook topic %s is no longer provided by an '
                            'installed domain handler, but Shopify returned a '
                            'different subscription GID than the preserved '
                            'record. No remote delete was issued; review the '
                            'unknown subscription before cleanup.'
                            % subscription.topic
                        ),
                        operator_note=(
                            'A remote subscription remains under an unknown '
                            'GID; identity must be resolved explicitly before '
                            'any delete.'
                        ),
                    ))
                    continue
                subscription._service_write(dict(
                    base,
                    state='missing',
                    actual_topic=False,
                    actual_uri_digest=False,
                    actual_api_version=False,
                    actual_format=False,
                    actual_include_fields=False,
                    last_error=(
                        'The webhook topic %s is no longer provided by an '
                        'installed domain handler and its recorded Shopify '
                        'subscription GID is absent on read-back; no delete '
                        'was issued.' % subscription.topic
                    ),
                    operator_note=(
                        'Remote cleanup is complete or the recorded GID is '
                        'already absent; the historical row is retained.'
                    ),
                ))
                continue
            active_delete = Job.search([
                ('store_id', '=', store.id),
                ('job_type', '=', 'webhook_subscription_delete'),
                ('res_model', '=', self._name),
                ('res_id', '=', subscription.id),
                ('expected_connection_generation', '=',
                 store.connection_generation),
                ('state', 'not in', terminal),
            ], order='id asc', limit=1)
            evidence = dict(
                base,
                state='manual_review',
                shopify_subscription_gid=gid,
                actual_topic=remote.get('topic') or False,
                actual_uri_digest=remote.get('uri_digest') or False,
                actual_api_version=remote.get('observed_api_version') or False,
                actual_format=remote.get('format') or False,
                actual_include_fields=remote.get('include_fields') or [],
                last_error=(
                    'The webhook topic %s is no longer provided by an '
                    'installed domain handler. The exact Shopify subscription '
                    'was found and is queued for asynchronous cleanup.'
                    % subscription.topic
                ),
                operator_note=(
                    'Cleanup is read-first and durable; no remote mutation ran '
                    'in the uninstall transaction.'
                ),
            )
            if active_delete:
                evidence.update({
                    'state': 'queued',
                    'last_job_id': active_delete.id,
                    'last_error': False,
                })
                subscription._service_write(evidence)
                continue
            subscription._service_write(evidence)
            try:
                self._enqueue_subscription_mutation(
                    subscription, 'delete', source,
                )
            except (IntegrityError, ValidationError) as exc:
                subscription._service_write({
                    'state': 'manual_review',
                    'last_error': (
                        'Retired webhook topic cleanup could not be queued: '
                        '%s. No remote delete was issued.'
                        % str(exc)[:1000]
                    ),
                })
        return removed

    @api.model
    def _reconcile_store(
        self, store, source='scheduled_sync', job=None, bootstrap=False,
    ):
        """Compare expected records with Shopify and enqueue safe mutations."""
        store.ensure_one()
        self._require_hmac_client_secret(store)
        allowed_states = (
            ('setup_incomplete', 'reconnect_needed', 'connected')
            if bootstrap else ('connected',)
        )
        if store.state not in allowed_states:
            raise ValidationError(
                'Webhook subscription reconciliation is not available while '
                'the store is "%s".' % store.state
            )
        Registry = self.env['shopify.connector.webhook.registry']
        active_topics = Registry.allowed_topics()
        expected = self._ensure_expected_for_store(store)
        actual = self._read_actual_subscriptions(
            store, job, lifecycle=bootstrap,
        )
        Secret = self.env['shopify.connector.webhook.secret']
        callback_url = Secret._callback_url_for_store(store)
        callback_digest = _uri_digest(callback_url)
        epoch = self._credential_epoch(store)
        self._reconcile_registry_removed_subscriptions(
            store, active_topics, actual, source=source, epoch=epoch,
        )
        by_topic = {}
        for item in actual:
            by_topic.setdefault(item['topic'], []).append(item)
        for subscription in expected:
            matches = [
                item for item in by_topic.get(subscription.topic_enum, [])
                if item['uri_digest'] == callback_digest
                and item['observed_api_version'] == SHOPIFY_API_VERSION
                and item['format'] == 'JSON'
                and self._include_fields_match(
                    subscription.expected_include_fields,
                    item.get('include_fields'),
                )
            ]
            if matches:
                item = matches[0]
                subscription._service_write({
                    'state': 'active',
                    'shopify_subscription_gid': item['id'],
                    'actual_topic': item['topic'],
                    'actual_uri_digest': item['uri_digest'],
                    'actual_api_version': item['observed_api_version'],
                    'actual_format': item['format'],
                    'actual_include_fields': item.get('include_fields'),
                    'last_reconciled_at': fields.Datetime.now(),
                    'hmac_credential_epoch': epoch,
                    'last_error': False,
                    'operator_note': False,
                })
                continue
            filtered = [
                item for item in by_topic.get(subscription.topic_enum, [])
                if item['uri_digest'] == callback_digest
                and item['observed_api_version'] == SHOPIFY_API_VERSION
                and item['format'] == 'JSON'
                and not self._include_fields_match(
                    subscription.expected_include_fields,
                    item.get('include_fields'),
                )
            ]
            if filtered:
                item = filtered[0]
                required = ', '.join(
                    str(value) for value in (
                        subscription.expected_include_fields or []
                    )
                )
                subscription._service_write({
                    'state': 'manual_review',
                    'shopify_subscription_gid': item['id'],
                    'actual_topic': item['topic'],
                    'actual_uri_digest': item['uri_digest'],
                    'actual_api_version': item['observed_api_version'],
                    'actual_format': item['format'],
                    'actual_include_fields': item.get('include_fields'),
                    'last_reconciled_at': fields.Datetime.now(),
                    'hmac_credential_epoch': epoch,
                    'last_error': (
                        'Shopify has a subscription for this topic and callback '
                        'but its includeFields filter omits the required '
                        'domain field(s): %s. No duplicate subscription was '
                        'created automatically.' % required
                    ),
                })
                continue
            wrong_uri = by_topic.get(subscription.topic_enum, [])
            if wrong_uri:
                item = wrong_uri[0]
                active_delete = self.env[
                    'shopify.connector.job'
                ].sudo().search([
                    ('store_id', '=', store.id),
                    ('job_type', '=', 'webhook_subscription_delete'),
                    ('res_model', '=', self._name),
                    ('res_id', '=', subscription.id),
                    ('shopify_target_gid', '=', item['id']),
                    ('expected_connection_generation', '=',
                     store.connection_generation),
                    ('state', 'not in', tuple(CREATE_RETRY_STATES)),
                ], order='id asc', limit=1)
                values = {
                    'state': 'queued' if active_delete else 'manual_review',
                    'shopify_subscription_gid': item['id'],
                    'actual_topic': item['topic'],
                    'actual_uri_digest': item['uri_digest'],
                    'actual_api_version': item['observed_api_version'],
                    'actual_format': item['format'],
                    'last_reconciled_at': fields.Datetime.now(),
                    'hmac_credential_epoch': epoch,
                    'actual_include_fields': item.get('include_fields'),
                    'last_error': False if active_delete else (
                        'Shopify has a subscription for this topic, but its '
                        'callback endpoint is not this connector endpoint. '
                        'No remote subscription was deleted automatically.'
                    ),
                }
                if active_delete:
                    values['last_job_id'] = active_delete.id
                subscription._service_write(values)
                continue
            subscription._service_write({
                'state': 'missing',
                'last_reconciled_at': fields.Datetime.now(),
                'hmac_credential_epoch': epoch,
                'actual_include_fields': False,
                'last_error': False,
            })
            if _create_retry_allowed(subscription, store.state, bootstrap):
                self._enqueue_subscription_mutation(subscription, 'create', source)
            elif (
                subscription.last_job_id
                and subscription.last_job_id.state == 'blocked_manual_review'
            ):
                # Duplicate-risk/manual-review is a hard no-resend fence.
                # Scans and manual reconciliation never authorize a resend;
                # an administrator must first resolve the preserved evidence
                # through the existing sanctioned operator flow.
                subscription._service_write({
                    'operator_note': (
                        'Create is fenced after duplicate-risk/manual review. '
                        'Resolve the preserved Shopify evidence before any '
                        'operator-authorized retry.'
                    ),
                })
        return expected

    @api.model
    def _enqueue_store_bootstrap(self, store):
        """Queue a read-only lifecycle bootstrap before ordinary connection."""
        store.ensure_one()
        self._require_hmac_client_secret(store)
        if store.state not in (
            'setup_incomplete', 'reconnect_needed', 'connected',
        ):
            raise ValidationError(
                'Webhook bootstrap is unavailable while the store is "%s"; '
                'complete credential setup or reconnect first.' % store.state
            )
        payload_hash = canonical_sha256({
            'store_id': store.id,
            'registry': self.env[
                'shopify.connector.webhook.registry'
            ].allowed_topics(),
            'run_key': self._reconciliation_run_key('scheduled_sync'),
        })
        return self._enqueue_job_with_recovery(
            store,
            'setup_readiness_check',
            'webhook_subscription_bootstrap',
            payload_hash,
            'shopify.connector.store',
            store.id,
        )

    @api.model
    def _enqueue_store_reconcile(self, store, source='manual_sync'):
        store.ensure_one()
        self._require_hmac_client_secret(store)
        if store.state != 'connected':
            raise ValidationError(
                'Webhook subscription reconciliation requires a connected store.'
            )
        run_key = self._reconciliation_run_key(source)
        payload_hash = canonical_sha256({
            'store_id': store.id,
            'registry': self.env[
                'shopify.connector.webhook.registry'
            ].allowed_topics(),
            'run_key': run_key,
        })
        return self._enqueue_job_with_recovery(
            store,
            source,
            'webhook_subscription_reconcile',
            payload_hash,
            'shopify.connector.store',
            store.id,
        )

    @api.model
    def _enqueue_store_retire_all(self, store):
        """Admit one read-first uninstall-preparation parent job."""
        store.ensure_one()
        self._require_hmac_client_secret(store)
        if store.state != 'connected':
            raise ValidationError(
                'Webhook uninstall preparation requires a connected store.'
            )
        return self._enqueue_job_with_recovery(
            store,
            'manual_sync',
            'webhook_subscription_retire_all',
            canonical_sha256({
                'store_id': store.id,
                'action': 'retire_all_for_uninstall',
                'run_key': self._reconciliation_run_key('manual_sync'),
            }),
            'shopify.connector.store',
            store.id,
        )

    def action_reconcile(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may reconcile '
                'Shopify webhook subscriptions.'
            )
        return self._enqueue_store_reconcile(self.store_id, 'manual_sync').id

    def action_replace_stale_callback(self):
        """Queue read-first replacement of one reviewed stale callback.

        This is an explicit administrator remediation, never an automatic
        reconciliation side effect.  A new Shopify read must still contain
        the exact stored GID with the same topic and the wrong callback before
        the durable delete is admitted.  Normal reconciliation creates and
        verifies the replacement only after Shopify proves that GID absent.
        """
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may replace a stale '
                'webhook callback.'
            )
        if (
            self.state != 'manual_review'
            or not self.expected
            or not self.shopify_subscription_gid
            or not self.actual_uri_digest
            or self.actual_uri_digest == self.expected_callback_url_digest
        ):
            raise ValidationError(
                'This subscription does not contain a verified stale callback '
                'identity that can be replaced.'
            )
        self._validate_subscription_create_preconditions(self)
        payload_hash = canonical_sha256({
            'action': 'replace_stale_callback',
            'subscription_id': self.id,
            'target_gid': self.shopify_subscription_gid,
            'actual_uri_digest': self.actual_uri_digest,
            'expected_callback_url_digest':
                self.expected_callback_url_digest,
            'run_key': self._reconciliation_run_key('manual_sync'),
        })
        job = self._enqueue_job_with_recovery(
            self.store_id,
            'manual_sync',
            'webhook_subscription_replace_stale',
            payload_hash,
            self._name,
            self.id,
            self.shopify_subscription_gid,
        )
        self._service_write({
            'state': 'queued',
            'last_job_id': job.id,
            'last_action_at': fields.Datetime.now(),
            'last_error': False,
            'operator_note': (
                'An administrator requested replacement of the preserved '
                'stale callback. A durable worker must fresh-read Shopify '
                'before any delete is admitted.'
            ),
        })
        return job.id

    def _replace_stale_callback_from_read(self, job, actual):
        """Admit the exact delete after the durable parent fresh read."""
        self.ensure_one()
        if (
            job.res_model != self._name
            or job.res_id != self.id
            or job.store_id != self.store_id
            or job.shopify_target_gid != self.shopify_subscription_gid
            or not self.expected
            or not self.shopify_subscription_gid
            or not self.actual_uri_digest
            or self.actual_uri_digest == self.expected_callback_url_digest
        ):
            raise ValidationError(
                'The stale callback replacement target changed before its '
                'fresh Shopify read; no delete was admitted.'
            )
        # Re-check at the action boundary. Domain enablement or governed scope
        # evidence may have changed after the administrator queued the parent;
        # deleting first would otherwise strand the expected topic with a
        # replacement that the create path is required to refuse.
        self._validate_subscription_create_preconditions(self)
        matches = [
            item for item in actual
            if item.get('id') == self.shopify_subscription_gid
            and item.get('topic') == self.topic_enum
        ]
        if len(matches) != 1:
            raise ValidationError(
                'Shopify no longer returns exactly the preserved stale '
                'subscription identity. Reconcile again before cleanup.'
            )
        observed = matches[0]
        if (
            observed.get('uri_digest') != self.actual_uri_digest
            or observed.get('uri_digest') == self.expected_callback_url_digest
        ):
            raise ValidationError(
                'The Shopify callback changed after review. Reconcile again; '
                'no remote delete was queued.'
            )
        self._service_write({
            'operator_note': (
                'An administrator approved replacement of the exact stale '
                'callback identity after a fresh Shopify read. Deletion is '
                'durable and the replacement remains read-back verified.'
            ),
        })
        return self._enqueue_subscription_mutation(
            self, 'delete', 'manual_sync',
        ).id

    @api.model
    def run_scheduled_reconciliation(self, limit=20):
        """Enqueue a bounded number of connected-store reconciliations."""
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may schedule webhook '
                'subscription reconciliation.'
            )
        Store = self.env['shopify.connector.store'].sudo()
        batch_limit = max(1, min(int(limit or 20), 100))
        null_stores = Store.search([
            ('state', '=', 'connected'),
            ('webhook_reconciliation_scheduled_at', '=', False),
        ], order='id asc', limit=batch_limit)
        _batch_limit, _null_limit, timestamped_limit = (
            _scheduled_reconciliation_bucket_limits(
                batch_limit, len(null_stores),
            )
        )
        timestamped_stores = Store.browse()
        if timestamped_limit:
            timestamped_stores = Store.search([
                ('state', '=', 'connected'),
                ('webhook_reconciliation_scheduled_at', '!=', False),
            ], order='webhook_reconciliation_scheduled_at asc, id asc',
                limit=timestamped_limit)
        stores = Store.browse(_scheduled_reconciliation_bucket_ids(
            null_stores.ids, timestamped_stores.ids, batch_limit,
        ))
        count = 0
        processed = 0
        cron = self.env['ir.cron'].sudo() if self.env.context.get('cron_id') else False
        for store in stores:
            if not self._has_hmac_client_secret(store):
                # Keep the bounded fairness cursor moving, but admit no
                # subscription work for an offline-token store without the
                # app secret needed to verify Shopify deliveries.  The health
                # projection explains the remediation to the operator.
                store.sudo().write({
                    'webhook_reconciliation_scheduled_at': fields.Datetime.now(),
                })
                processed += 1
                if cron:
                    remaining = _bounded_sweep_remaining(len(stores), processed)
                    if cron._commit_progress(1, remaining=remaining) <= 0:
                        break
                continue
            try:
                self._enqueue_store_reconcile(store, 'scheduled_sync')
            except IntegrityError:
                pass
            else:
                store.sudo().write({
                    'webhook_reconciliation_scheduled_at': fields.Datetime.now(),
                })
                count += 1
            processed += 1
            if cron:
                # ``remaining`` is the work left in THIS bounded sweep, not
                # every connected store. The final selected row reports zero
                # even when the fair cursor leaves another page for the next
                # normal interval, preventing an ASAP cron loop.
                remaining = _bounded_sweep_remaining(len(stores), processed)
                if cron._commit_progress(1, remaining=remaining) <= 0:
                    break
        if cron and not stores:
            cron._commit_progress(0, remaining=0)
        return count

    # ------------------------------------------------------------------
    # Layer 2 subscription mutations
    # ------------------------------------------------------------------

    @api.model
    def _mutation_subscription(self, job):
        subscription = self.browse(job.res_id).exists()
        if not subscription:
            raise ValidationError(
                'Webhook subscription mutation target is invalid.'
            )
        action = (
            'create' if job.job_type == 'webhook_subscription_create'
            else 'delete'
        )
        active_topics = self.env[
            'shopify.connector.webhook.registry'
        ].allowed_topics()
        removed_topic_cleanup = (
            action == 'delete'
            and not subscription.expected
            and bool(subscription.shopify_subscription_gid)
        )
        stale_callback_cleanup = (
            action == 'delete'
            and subscription.expected
            and subscription.state == 'queued'
            and bool(subscription.shopify_subscription_gid)
            and bool(subscription.actual_uri_digest)
            and subscription.actual_uri_digest
            != subscription.expected_callback_url_digest
        )
        if (
            subscription.store_id != job.store_id
            or (
                subscription.topic not in active_topics
                and not removed_topic_cleanup
            )
            or (action == 'delete' and not (
                removed_topic_cleanup or stale_callback_cleanup
            ))
        ):
            raise ValidationError('Webhook subscription mutation target is invalid.')
        return subscription

    @api.model
    def _prepare_local_subscription_mutation(self, job):
        subscription = self._mutation_subscription(job)
        action = (
            'create' if job.job_type == 'webhook_subscription_create'
            else 'delete'
        )
        if action == 'delete' and not subscription.shopify_subscription_gid:
            raise ValidationError('A delete mutation requires a stored Shopify subscription GID.')
        return {
            'mutation_domain': job.job_type,
            'job_id': job.id,
            'subscription_id': subscription.id,
            'store_id': subscription.store_id.id,
            'expected_connection_generation':
                job.expected_connection_generation,
            'action': action,
            'topic': subscription.topic,
            'topic_enum': subscription.topic_enum,
            'callback_url_digest': subscription.expected_callback_url_digest,
            'expected_api_version': subscription.expected_api_version,
            'expected_include_fields': list(
                subscription.expected_include_fields or [],
            ),
            'shopify_subscription_gid': subscription.shopify_subscription_gid or False,
            'expected_store_identity': subscription.store_id.shop_domain,
        }

    @api.model
    def _prepare_subscription_preconditions(self, local_snapshot, owner_context):
        action = local_snapshot['action']
        if action == 'create':
            callback_url = self.env[
                'shopify.connector.webhook.secret'
            ]._callback_url_for_store(
                self.env['shopify.connector.store'].browse(
                    local_snapshot['store_id']
                )
            )
            if _uri_digest(callback_url) != local_snapshot['callback_url_digest']:
                raise ValidationError(
                    'The callback token changed after the subscription job was '
                    'queued; the remote create was refused.'
                )
            operation = WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT
            variables = {
                'topic': local_snapshot['topic_enum'],
                'webhookSubscription': {
                    # ``uri`` is the current GraphQL Admin API input.  The
                    # deprecated callbackUrl field is intentionally not used.
                    'uri': callback_url,
                    'format': 'JSON',
                    'includeFields': (
                        list(local_snapshot.get('expected_include_fields') or [])
                        or None
                    ),
                },
            }
        else:
            operation = WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT
            variables = {'id': local_snapshot['shopify_subscription_gid']}
        return {
            'mutation_domain': owner_context['mutation_domain'],
            'operation': operation,
            'variables': variables,
            'business_intent': {
                'action': action,
                'subscription_id': local_snapshot['subscription_id'],
                'store_id': local_snapshot['store_id'],
                'topic': local_snapshot['topic'],
                'topic_enum': local_snapshot['topic_enum'],
                'callback_url_digest': local_snapshot['callback_url_digest'],
                'expected_include_fields': list(
                    local_snapshot.get('expected_include_fields') or [],
                ),
                'target_gid': local_snapshot['shopify_subscription_gid'],
            },
            'remote_mutation_intent': {
                'action': action,
                'subscription_id': local_snapshot['subscription_id'],
                'topic_enum': local_snapshot['topic_enum'],
                'callback_url_digest': local_snapshot['callback_url_digest'],
                'expected_include_fields': list(
                    local_snapshot.get('expected_include_fields') or [],
                ),
                'target_gid': local_snapshot['shopify_subscription_gid'],
            },
            'preconditions_snapshot': {
                'expected_connection_generation':
                    local_snapshot['expected_connection_generation'],
                'expected_store_identity': local_snapshot['expected_store_identity'],
                'expected_api_version': local_snapshot['expected_api_version'],
                'expected_include_fields': list(
                    local_snapshot.get('expected_include_fields') or [],
                ),
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity': local_snapshot['expected_store_identity'],
            # Shopify's webhook subscription mutations do not take a generic
            # idempotency argument.  This connector-level key still binds the
            # durable attempt and prevents duplicate local operations.
            'shopify_idempotency_key': 'webhook-subscription:%s:%s:%s' % (
                local_snapshot['subscription_id'], action,
                local_snapshot['callback_url_digest'],
            ),
        }

    @api.model
    def _transport_subscription_mutation(self, request, attempt_context):
        client = self.env['shopify.connector.api.client']
        store = self.env['shopify.connector.store'].browse(
            attempt_context['store_id']
        )
        job = self.env['shopify.connector.job'].browse(
            attempt_context['job_id']
        )
        try:
            with client.execute_business(
                job,
                store,
                request['operation'],
                request['variables'],
                mutation_context=attempt_context,
            ) as result:
                return {'outcome': 'succeeded', 'result': result}
        except ShopifyClientError as exc:
            # The core Layer-2 wrapper intentionally turns post-C2 transport
            # exceptions into an uncertain result. Preserve the client's
            # existing safe error class here so a deterministic GraphQL schema
            # selection error is not demoted to a generic temporary outcome.
            # Never copy technical detail or response bodies into mutation
            # evidence; the exception's redacted reason is sufficient for the
            # operator-facing consequence.
            return {
                'outcome': 'uncertain',
                'error_class': exc.error_class,
                'message': exc.reason,
                'evidence': {
                    'exception_class': type(exc).__name__,
                    'transport': 'exception_after_c2',
                },
            }

    @api.model
    def _classify_subscription_mutation(self, raw_result):
        if not isinstance(raw_result, dict):
            return {
                'observed_outcome': 'uncertain',
                'error_class': 'data_shape_schema_mismatch',
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': 'Shopify returned no subscription mutation result.',
                'evidence': {'response_shape': 'not_a_mapping'},
            }
        if raw_result.get('outcome') != 'succeeded':
            error_class = raw_result.get('error_class') or (
                'shopify_temporary_server_network'
            )
            message = raw_result.get('message') or (
                'The subscription mutation outcome is uncertain; read Shopify '
                'before any retry.'
            )
            return {
                'observed_outcome': 'uncertain',
                'error_class': error_class,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': message,
                'evidence': dict(raw_result.get('evidence') or {}),
            }
        result = raw_result.get('result') or {}
        data = result.get('data') or {}
        if 'webhookSubscriptionCreate' in data:
            payload = data.get('webhookSubscriptionCreate') or {}
            errors = payload.get('userErrors') or []
            if errors:
                return {
                    'observed_outcome': 'failed_clean',
                    'error_class': 'shopify_user_errors_validation',
                    'manual_review_subreason': False,
                    'action': 'fail_final',
                    'message': 'Shopify rejected the webhook subscription create request; review the recorded fields.',
                    'evidence': {
                        'user_error_fields': [
                            str(item.get('field') or '')[:128]
                            for item in errors if isinstance(item, dict)
                        ][:8],
                        'user_error_count': len(errors),
                    },
                }
            node = payload.get('webhookSubscription') or {}
            if not node.get('id'):
                return {
                    'observed_outcome': 'uncertain',
                    'error_class': 'data_shape_schema_mismatch',
                    'manual_review_subreason': False,
                    'action': 'reconcile',
                    'message': 'Shopify did not return a subscription identity; read Shopify before retrying.',
                    'evidence': {'response_shape': 'missing_subscription_id'},
                }
            try:
                actual_api_version = _api_version_handle(
                    node.get('apiVersion')
                )
            except ShopifyWebhookSchemaError:
                return {
                    'observed_outcome': 'uncertain',
                    'error_class': 'data_shape_schema_mismatch',
                    'manual_review_subreason': False,
                    'action': 'reconcile',
                    'message': (
                        'Shopify returned an unsupported webhook API version '
                        'shape; read Shopify before retrying.'
                    ),
                    'evidence': {
                        'response_shape': 'invalid_api_version_object',
                    },
                }
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'Shopify accepted the webhook subscription create request; verification remains required.',
                'evidence': {'remote_subscription_id_present': True},
                'domain_payload': {
                    'shopify_subscription_gid': str(node['id'])[:256],
                    'actual_topic': str(node.get('topic') or '')[:128],
                    'actual_uri_digest': _uri_digest(node.get('uri') or node.get('callbackUrl') or ''),
                    'actual_api_version': actual_api_version,
                    'actual_format': str(node.get('format') or '')[:32],
                    'actual_include_fields': self._normalize_include_fields(
                        node.get('includeFields'),
                    ),
                },
            }
        if 'webhookSubscriptionDelete' in data:
            payload = data.get('webhookSubscriptionDelete') or {}
            errors = payload.get('userErrors') or []
            if errors:
                return {
                    'observed_outcome': 'failed_clean',
                    'error_class': 'shopify_user_errors_validation',
                    'manual_review_subreason': False,
                    'action': 'fail_final',
                    'message': 'Shopify rejected the webhook subscription delete request; review the recorded fields.',
                    'evidence': {
                        'user_error_fields': [
                            str(item.get('field') or '')[:128]
                            for item in errors if isinstance(item, dict)
                        ][:8],
                        'user_error_count': len(errors),
                    },
                }
            if not payload.get('deletedWebhookSubscriptionId'):
                return {
                    'observed_outcome': 'uncertain',
                    'error_class': 'data_shape_schema_mismatch',
                    'manual_review_subreason': False,
                    'action': 'reconcile',
                    'message': 'Shopify returned no deleted subscription identity; read Shopify before retrying.',
                    'evidence': {'response_shape': 'missing_deleted_subscription_id'},
                }
            return {
                'observed_outcome': 'succeeded',
                'error_class': False,
                'manual_review_subreason': False,
                'action': 'succeed',
                'message': 'Shopify accepted the webhook subscription delete request; reconciliation remains required.',
                'evidence': {'remote_subscription_id_present': True},
                'domain_payload': {
                    'deleted_subscription_gid': str(
                        payload['deletedWebhookSubscriptionId']
                    )[:256],
                },
            }
        return {
            'observed_outcome': 'uncertain',
            'error_class': 'data_shape_schema_mismatch',
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': 'Shopify returned an unrecognised webhook subscription mutation result.',
            'evidence': {'response_shape': 'unknown_subscription_mutation'},
        }

    @api.model
    def _reconcile_subscription_mutation(self, attempt, reconciliation_job=None):
        intent = dict(attempt.remote_mutation_intent or {})
        store = attempt.store_id
        try:
            actual = self._read_actual_subscriptions(store, reconciliation_job)
        except ShopifyWebhookSchemaError:
            # Let the core mutation-reconciliation wrapper route this as the
            # existing data-shape/schema error class.  Treating a malformed
            # ApiVersion object as an ordinary inconclusive network read would
            # hide a deterministic schema defect behind repeated retries.
            raise
        except Exception as exc:  # read failure is intentionally inconclusive
            return {
                'verdict': 'inconclusive',
                'observed_store_identity': store.shop_domain,
                'action': 'reconcile',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Shopify subscription reconciliation could not complete; no resend was issued.',
                'evidence': {'read_failure_class': type(exc).__name__},
            }
        action = intent.get('action')
        if action == 'create':
            found = next((
                item for item in actual
                if item['topic'] == intent.get('topic_enum')
                and item['uri_digest'] == intent.get('callback_url_digest')
                and item['observed_api_version'] == SHOPIFY_API_VERSION
                and item['format'] == 'JSON'
                and self._include_fields_match(
                    intent.get('expected_include_fields'),
                    item.get('include_fields'),
                )
            ), False)
            if found:
                return {
                    'verdict': 'applied',
                    'observed_store_identity': store.shop_domain,
                    'action': 'succeed',
                    'error_class': False,
                    'manual_review_subreason': False,
                    'message': 'Read-only Shopify verification found the expected webhook subscription.',
                    'evidence': {
                        'subscription_found': True,
                        'shopify_subscription_gid': found['id'],
                        'actual_topic': found['topic'],
                        'actual_uri_digest': found['uri_digest'],
                        'actual_api_version': found['observed_api_version'],
                        'actual_format': found['format'],
                        'actual_include_fields': found.get('include_fields'),
                    },
                    'domain_payload': {
                        'shopify_subscription_gid': found['id'],
                        'actual_topic': found['topic'],
                        'actual_uri_digest': found['uri_digest'],
                        'actual_api_version': found['observed_api_version'],
                        'actual_format': found['format'],
                        'actual_include_fields': found.get('include_fields'),
                    },
                }
            filtered = next((
                item for item in actual
                if item['topic'] == intent.get('topic_enum')
                and item['uri_digest'] == intent.get('callback_url_digest')
                and item['observed_api_version'] == SHOPIFY_API_VERSION
                and item['format'] == 'JSON'
                and not self._include_fields_match(
                    intent.get('expected_include_fields'),
                    item.get('include_fields'),
                )
            ), False)
            if filtered:
                return {
                    'verdict': 'not_applied',
                    'observed_store_identity': store.shop_domain,
                    'action': 'block_manual_review',
                    'error_class': 'duplicate_risk',
                    'manual_review_subreason': 'duplicate_risk',
                    'message': (
                        'Shopify has the expected callback subscription, but '
                        'its includeFields filter omits a required domain '
                        'field; automatic resend is blocked for review.'
                    ),
                    'evidence': {
                        'subscription_found': True,
                        'subscription_filter_mismatch': True,
                        'shopify_subscription_gid': filtered['id'],
                        'actual_include_fields': filtered.get(
                            'include_fields',
                        ),
                    },
                }
            return {
                'verdict': 'not_applied',
                'observed_store_identity': store.shop_domain,
                'action': 'block_manual_review',
                'error_class': 'duplicate_risk',
                'manual_review_subreason': 'duplicate_risk',
                'message': 'Read-only Shopify verification did not find the expected subscription; automatic resend is blocked for review.',
                'evidence': {'subscription_found': False},
            }
        target = intent.get('target_gid')
        present = any(item['id'] == target for item in actual)
        if not present:
            return {
                'verdict': 'applied',
                'observed_store_identity': store.shop_domain,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Read-only Shopify verification confirmed the subscription is absent.',
                'evidence': {'subscription_present': False},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': store.shop_domain,
            'action': 'block_manual_review',
            'error_class': 'duplicate_risk',
            'manual_review_subreason': 'duplicate_risk',
            'message': 'Read-only Shopify verification still finds the subscription; automatic resend is blocked for review.',
            'evidence': {'subscription_present': True},
        }

    @api.model
    def _apply_subscription_consequence(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        del attempt
        subscription = self.browse(job.res_id).exists()
        if not subscription:
            return True
        action = consequence.get('action')
        payload = dict(consequence.get('domain_payload') or {})
        values = {
            'last_action_at': fields.Datetime.now(),
            'last_job_id': job.id,
            'last_error': False,
        }
        if action == 'succeed':
            if job.job_type == 'webhook_subscription_create':
                values.update(payload)
                values['state'] = (
                    'active' if phase == 'reconciliation'
                    else 'pending_verification'
                )
                if phase == 'reconciliation':
                    # The helper acquires the finalization fence and reads the
                    # epoch from the locked current credential.  Payloads and
                    # attempt snapshots are never trusted for HMAC evidence.
                    values['hmac_credential_epoch'] = (
                        self._hmac_epoch_for_admitted_job(
                            reconciliation_job or job,
                        )
                    )
            else:
                values.update({
                    'state': 'missing',
                    'shopify_subscription_gid': False,
                    'actual_topic': False,
                    'actual_uri_digest': False,
                    'actual_api_version': False,
                    'actual_format': False,
                    'actual_include_fields': False,
                })
            if phase == 'reconciliation':
                values['last_reconciled_at'] = fields.Datetime.now()
        elif action == 'fail_final':
            values.update({
                'state': 'error',
                'last_error': redact(
                    consequence.get('message') or 'Shopify rejected the subscription change.'
                )[:2000],
            })
        elif action == 'block_manual_review':
            values.update({
                'state': 'manual_review',
                'last_error': redact(
                    consequence.get('message') or 'Subscription change requires review.'
                )[:2000],
            })
        subscription._service_write(values)
        return True

    # ------------------------------------------------------------------
    # Operator and scheduled entry points
    # ------------------------------------------------------------------

    def action_open_reconcile(self):
        return self.action_reconcile()

    def _sec3_parent_scope_relations(self):
        return (('last_job_id', 'store'),)

    @api.constrains('store_id', 'last_job_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()


class ShopifyConnectorWebhookSubscriptionStore(models.Model):
    """Store-level operator action and computed health projection."""

    _inherit = 'shopify.connector.store'

    webhook_subscription_ids = fields.One2many(
        'shopify.connector.webhook.subscription', 'store_id', readonly=True,
    )
    webhook_health = fields.Selection(
        selection=[
            ('not_configured', 'Not configured'),
            ('degraded', 'Degraded'),
            ('healthy', 'Healthy'),
        ], compute='_compute_webhook_health', string='Webhook health',
    )
    webhook_health_reason = fields.Char(
        compute='_compute_webhook_health', string='Webhook health detail',
    )
    webhook_callback_path = fields.Char(
        compute='_compute_webhook_health', string='Webhook callback path',
    )
    webhook_last_reconciled_at = fields.Datetime(
        compute='_compute_webhook_health', string='Webhook reconciliation',
    )
    webhook_client_secret_grace_expires_at = fields.Datetime(
        compute='_compute_webhook_health',
        string='Client-secret grace expiry',
    )
    webhook_reconciliation_scheduled_at = fields.Datetime(
        string='Webhook reconciliation scheduling cursor', index=True,
        readonly=True,
    )

    @api.depends(
        'webhook_subscription_ids.state',
        'webhook_subscription_ids.last_reconciled_at',
        'webhook_subscription_ids.last_error',
    )
    def _compute_webhook_health(self):
        for store in self:
            subscriptions = store.webhook_subscription_ids
            store.webhook_callback_path = self.env[
                'shopify.connector.webhook.secret'
            ]._callback_path_label()
            store.webhook_last_reconciled_at = _latest_reconciled_at(
                subscriptions.mapped('last_reconciled_at')
            )
            credential = self.env[
                'shopify.connector.store.credential'
            ].sudo().search([('store_id', '=', store.id)], limit=1)
            store.webhook_client_secret_grace_expires_at = (
                credential.webhook_previous_client_secret_expires_at
                if credential and self.env[
                    'shopify.connector.store.credential'
                ]._hmac_rotation_pending(store) else False
            )
            if store.state != 'connected':
                store.webhook_health = 'not_configured'
                store.webhook_health_reason = (
                    'Webhook proof is not applicable before activation. Use '
                    'Bootstrap / reconcile webhooks, then complete connection.'
                )
            elif not self.env[
                'shopify.connector.webhook.secret'
            ]._client_secret_for_store(store):
                store.webhook_health = 'degraded'
                store.webhook_health_reason = (
                    'A Shopify app client secret is required for webhook HMAC '
                    'verification. Use Client ID + Client secret token-exchange '
                    'mode before reconciling subscriptions.'
                )
            elif self.env[
                'shopify.connector.webhook.secret'
            ]._client_secrets_for_store(store) and self.env[
                'shopify.connector.store.credential'
            ]._hmac_rotation_pending(store):
                store.webhook_health = 'degraded'
                store.webhook_health_reason = (
                    'Shopify app client-secret rotation grace is active; '
                    'readiness remains pending until the recorded expiry.'
                )
            elif not subscriptions:
                store.webhook_health = 'not_configured'
                store.webhook_health_reason = (
                    'No expected webhook subscription evidence is recorded.'
                )
            elif any(sub.state in ('error', 'manual_review') for sub in subscriptions):
                store.webhook_health = 'degraded'
                store.webhook_health_reason = next(
                    (sub.last_error for sub in subscriptions if sub.last_error),
                    'One or more webhook subscriptions require review.',
                )
            elif any(sub.state != 'active' for sub in subscriptions):
                store.webhook_health = 'degraded'
                store.webhook_health_reason = (
                    'Expected webhook subscriptions are not all verified '
                    'active in Shopify.'
                )
            else:
                store.webhook_health = 'healthy'
                store.webhook_health_reason = (
                    'Expected subscriptions have stored read-back evidence. '
                    'Scheduled reconciliation remains mandatory.'
                )

    def action_reconcile_webhooks(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may reconcile '
                'webhook subscriptions.'
            )
        Subscription = self.env['shopify.connector.webhook.subscription']
        if self.state == 'connected':
            job = Subscription._enqueue_store_reconcile(self, 'manual_sync')
        elif self.state in ('setup_incomplete', 'reconnect_needed'):
            job = Subscription._enqueue_store_bootstrap(self)
        else:
            raise ValidationError(
                'Reconnect or complete setup before webhook bootstrap; the '
                'disconnected state has no lifecycle admission for this action.'
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Webhook reconciliation',
            'res_model': 'shopify.connector.job',
            'view_mode': 'form',
            'res_id': job.id,
            'target': 'current',
        }

    def action_prepare_webhook_uninstall(self):
        """Delete exact remote subscriptions through the normal safe queue."""
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may prepare webhook '
                'uninstall.'
            )
        job = self.env[
            'shopify.connector.webhook.subscription'
        ]._enqueue_store_retire_all(self)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Webhook uninstall preparation',
            'res_model': 'shopify.connector.job',
            'view_mode': 'form',
            'res_id': job.id,
            'target': 'current',
        }
