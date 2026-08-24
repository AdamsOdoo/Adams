import json
import logging
import uuid

from odoo import api, fields, models

from .shopify_connector_fulfillment_reader import FulfillmentReadError

_logger = logging.getLogger(__name__)

# The fulfillmentCreate mutation document (RA-022: FulfillmentOrder-based, never
# the legacy V2/REST path). Written as an ANONYMOUS GraphQL operation and held
# as a module constant referenced by name from prepare/transport — fulfillment
# mutation documents are guarded by this addon's own source-guard test, which
# proves they are only ever reachable through the guarded
# client.execute_business(mutation_context=...) transport surface. There is NO
# @idempotent directive (fulfillmentCreate is not on Shopify's 17-mutation
# @idempotent list); dedup is business_intent_fingerprint + operation-scope
# serialization + the reconcile read.
FULFILLMENT_CREATE_DOCUMENT = (
    'mutation ($fulfillment: FulfillmentInput!) {\n'
    '  fulfillmentCreate(fulfillment: $fulfillment) {\n'
    '    fulfillment {\n'
    '      id\n'
    '      status\n'
    '      trackingInfo { number url company }\n'
    '    }\n'
    '    userErrors { field message }\n'
    '  }\n'
    '}'
)

# FulfillmentOrder statuses that are eligible for a create attempt.
FO_ELIGIBLE_STATUSES = ('OPEN', 'IN_PROGRESS')
FO_BLOCKING_STATUSES = ('ON_HOLD', 'SCHEDULED', 'INCOMPLETE')
CREATE_FULFILLMENT_ACTION = 'CREATE_FULFILLMENT'


class FulfillmentPreC2FailClosedError(Exception):
    """Raised from a fulfillment prepare/precondition callback to fail closed
    BEFORE C2: no mutation-attempt row is created and no transport occurs. The
    dispatcher's `_recover_pre_c2_failure` seam routes the still-owned job by
    the carried `error_class` after core's own rollback/reset."""

    def __init__(self, error_class, message):
        super().__init__(message)
        self.error_class = error_class
        self.message = message


class ShopifyConnectorFulfillmentCreateStrategy(models.AbstractModel):
    """The 7-callback Layer 2 strategy for `fulfillment_create` plus the
    create-domain reconcile read invoked by the shared
    `fulfillment_mutation_reconcile` job. Post-C2 the reconcile read yields only
    APPLIED / INCONCLUSIVE — never `not_applied`, never a resend."""

    _inherit = 'shopify.connector.fulfillment.service'

    @api.model
    def _fail_closed_pre_c2(self, error_class, message):
        raise FulfillmentPreC2FailClosedError(error_class, message)

    # ------------------------------------------------------------------
    # Callback 2: prepare_local (C1 immutable snapshot)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_fulfillment_create(self, job):
        picking = self.env['stock.picking'].browse(job.res_id)
        binding = self.env['shopify.connector.order.binding'].search([
            ('store_id', '=', job.store_id.id),
            ('sale_order_id', '=', picking.sale_id.id),
        ], limit=1)
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', job.store_id.id)], limit=1,
        )
        if binding.status == 'review':
            self._fail_closed_pre_c2(
                'financial_total_mismatch',
                'Fulfillment stopped before mutation because the Shopify '
                'order is in Needs Attention: %s' % (
                    binding.review_reason
                    or 'its post-import commercial evidence changed',
                ),
            )
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'picking_id': picking.id,
            'order_binding_id': binding.id,
            'order_gid': binding.shopify_gid,
            # Each fulfillment_create job targets exactly one FulfillmentOrder
            # (per-FO decomposition; op-scope (store, picking, FO GID)).
            'target_fo_gid': job.shopify_target_gid,
            # RA-009: the notification decision is frozen here (default off) and
            # carried into the immutable attempt snapshot; never re-read at
            # retry, never repeated from read absence.
            'notify_customer': bool(
                settings and settings._fulfillment_notification_allowed()
            ),
            'tracking_numbers': self._picking_tracking_numbers(picking),
            'tracking_company': picking.carrier_id.name or '',
            'tracking_urls': self._picking_tracking_urls(picking),
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    @api.model
    def _picking_tracking_numbers(self, picking):
        ref = picking.carrier_tracking_ref or ''
        return [n.strip() for n in ref.replace(';', ',').split(',') if n.strip()]

    @api.model
    def _picking_tracking_urls(self, picking):
        url = getattr(picking, 'carrier_tracking_url', '') or ''
        return [url] if url else []

    # ------------------------------------------------------------------
    # Callback 3: prepare_preconditions (fresh pre-C2 read + request builder)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_preconditions_fulfillment_create(self, local_snapshot, owner_context):
        read_job = self.env['shopify.connector.job'].browse(
            local_snapshot['job_id']
        )
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        picking = self.env['stock.picking'].browse(local_snapshot['picking_id'])
        order_gid = local_snapshot['order_gid']
        if not order_gid:
            self._fail_closed_pre_c2(
                'mapping_missing',
                'The picking has no resolvable Shopify order binding.',
            )
        try:
            fos = self._read_fulfillment_orders(read_job, store, order_gid)
        except FulfillmentReadError as exc:
            self._fail_closed_pre_c2(exc.error_class, exc.message)

        # Client-side selection of eligible FOs; blocking states fail closed.
        eligible = []
        for fo in fos:
            status = fo.get('status')
            if status in FO_BLOCKING_STATUSES:
                self._fail_closed_pre_c2(
                    'ambiguous_match',
                    'A FulfillmentOrder is %s; the connector never places or '
                    'releases holds.' % status,
                )
            if status in FO_ELIGIBLE_STATUSES:
                actions = {
                    (a or {}).get('action')
                    for a in (fo.get('supportedActions') or [])
                }
                if CREATE_FULFILLMENT_ACTION not in actions:
                    continue
                eligible.append(fo)
        if not eligible:
            self._fail_closed_pre_c2(
                'ambiguous_match',
                'No eligible FulfillmentOrder supports CREATE_FULFILLMENT for '
                'this order.',
            )

        # This picking maps to one Shopify Fulfillment (UNIQUE(store, picking));
        # its shipped lines are decomposed across every FulfillmentOrder that
        # actually ships on this picking, and sent in one fulfillmentCreate. A
        # shipped line that resolves to no FO fails closed (RA-023). All shipped
        # FOs must share one location (D-014-5).
        try:
            line_inputs, _diag = self._match_picking_to_fo_lines(picking, eligible)
            shipped_fos = [fo for fo in eligible if fo.get('id') in line_inputs]
            location_gid = self._resolve_single_location(store, shipped_fos)
        except FulfillmentReadError as exc:
            self._fail_closed_pre_c2(exc.error_class, exc.message)

        line_items_by_fo = [
            {'fulfillmentOrderId': fo_gid, 'fulfillmentOrderLineItems': items}
            for fo_gid, items in sorted(line_inputs.items())
        ]
        fulfillment_input = {
            'lineItemsByFulfillmentOrder': line_items_by_fo,
            'notifyCustomer': bool(local_snapshot['notify_customer']),
        }
        tracking_info = self._build_tracking_info(local_snapshot)
        if tracking_info:
            fulfillment_input['trackingInfo'] = tracking_info

        variables = {'fulfillment': fulfillment_input}
        return {
            'mutation_domain': 'fulfillment_create',
            'operation': FULFILLMENT_CREATE_DOCUMENT,
            'variables': variables,
            'business_intent': {
                'mutation_domain': 'fulfillment_create',
                'store_id': local_snapshot['store_id'],
                'order_gid': order_gid,
                'line_items_by_fo': line_items_by_fo,
                'notify_customer': bool(local_snapshot['notify_customer']),
            },
            'remote_mutation_intent': {
                'operation_name': 'fulfillmentCreate',
                'order_gid': order_gid,
                'location_gid': location_gid,
            },
            'preconditions_snapshot': {
                'order_gid': order_gid,
                'location_gid': location_gid,
                'line_items_by_fo': line_items_by_fo,
                'sent_tracking_numbers': local_snapshot['tracking_numbers'],
                'notify_customer': bool(local_snapshot['notify_customer']),
                'fo_remaining_snapshot': self._fo_remaining_snapshot(eligible),
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()
                ),
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity': local_snapshot['expected_store_identity'],
            # The merged Layer 2 request contract requires a non-empty
            # shopify_idempotency_key on every prepared mutation request. The
            # fulfillment operation document contains NO @idempotent directive
            # and never references this key, so it is persisted on the attempt
            # but never sent on the wire — it has zero Shopify-side effect
            # (fulfillmentCreate is not on the 17-mutation @idempotent list).
            # "Unused" means "no wire idempotency directive", not "absent".
            'shopify_idempotency_key': uuid.uuid4().hex,
        }

    @api.model
    def _build_tracking_info(self, local_snapshot):
        numbers = local_snapshot.get('tracking_numbers') or []
        urls = local_snapshot.get('tracking_urls') or []
        company = local_snapshot.get('tracking_company') or ''
        if not numbers and not urls:
            # D-014-6: goods-shipped is still recorded — the fulfillment is
            # created without trackingInfo.
            return None
        info = {}
        if company:
            info['company'] = company
        if len(numbers) == 1:
            info['number'] = numbers[0]
        elif len(numbers) > 1:
            info['numbers'] = numbers
        # Position-matched urls only when equal length; else omit (never guess).
        if urls and len(urls) == len(numbers):
            info['urls'] = urls if len(urls) > 1 else None
            if len(urls) == 1:
                info['url'] = urls[0]
                info.pop('urls', None)
        elif len(urls) == 1 and not numbers:
            info['url'] = urls[0]
        return info or None

    @api.model
    def _fo_remaining_snapshot(self, fos):
        snapshot = {}
        for fo in fos:
            for line in fo.get('line_items') or []:
                if isinstance(line, dict) and line.get('id') is not None:
                    snapshot[line['id']] = line.get('remainingQuantity')
        return snapshot

    # ------------------------------------------------------------------
    # Callback 4: transport (the single guarded execute_business surface)
    # ------------------------------------------------------------------

    @api.model
    def _transport_fulfillment_create(self, request, attempt_context):
        store = self.env['shopify.connector.store'].browse(
            attempt_context['store_id']
        )
        client = self.env['shopify.connector.api.client']
        try:
            with client.execute_business(
                attempt_context['job_id'], store,
                request['operation'], request['variables'],
                mutation_context={
                    'job_id': attempt_context['job_id'],
                    'attempt_id': attempt_context['attempt_id'],
                    'attempt_token': attempt_context['attempt_token'],
                    'mutation_domain': attempt_context['mutation_domain'],
                },
            ) as result:
                data = (result or {}).get('data') or {}
                payload = data.get('fulfillmentCreate') or {}
                return {
                    'outcome': None,
                    'user_errors': payload.get('userErrors'),
                    'fulfillment': payload.get('fulfillment'),
                    'evidence': {'transport': 'fulfillmentCreate'},
                }
        except Exception as exc:  # noqa: BLE001 — never re-raise past C2
            return {
                'outcome': 'uncertain',
                'error_class': 'shopify_temporary_server_network',
                'evidence': {'exception_class': type(exc).__name__},
            }

    # ------------------------------------------------------------------
    # Callback 5: classify_direct_result (code_required=False; positive id)
    # ------------------------------------------------------------------

    @api.model
    def _classify_direct_fulfillment_create(self, result):
        result = result or {}
        if result.get('outcome') == 'uncertain':
            return self._uncertain_consequence(
                result.get('error_class', 'shopify_temporary_server_network'),
                'Transport-level uncertainty during fulfillmentCreate.',
                result.get('evidence'),
            )
        user_errors = result.get('user_errors')
        evidence = dict(result.get('evidence') or {})
        if not isinstance(user_errors, list):
            return self._uncertain_consequence(
                'data_shape_schema_mismatch',
                'fulfillmentCreate returned a malformed userErrors container.',
                evidence,
            )
        if user_errors:
            # A synchronous structured clean rejection (no code on fulfillment
            # userErrors): a direct clean failure, correctable by a NEW
            # replacement job — never a post-C2 uncertain verdict.
            evidence['user_errors'] = user_errors
            return {
                'observed_outcome': 'failed_clean',
                'error_class': 'shopify_user_errors_validation',
                'manual_review_subreason': False,
                'action': 'fail_final',
                'message': 'Shopify rejected fulfillmentCreate (userErrors).',
                'evidence': evidence,
            }
        fulfillment = result.get('fulfillment')
        fulfillment_id = (
            fulfillment.get('id') if isinstance(fulfillment, dict) else None
        )
        if not fulfillment_id:
            # Empty userErrors but no real Fulfillment id: not positive success
            # evidence — reconcile before trusting it as applied.
            return self._uncertain_consequence(
                'data_shape_schema_mismatch',
                'fulfillmentCreate returned empty userErrors but no Fulfillment '
                'id; reconciling before trusting this as applied.',
                evidence,
            )
        # Theme F: a real Fulfillment id alone is not positive success
        # evidence -- the reconcile path already requires status == 'SUCCESS'
        # twice (a strictly stronger bar); the direct-result path must match
        # it. Shopify's active FulfillmentStatus enum is exactly
        # SUCCESS/CANCELLED/ERROR/FAILURE (OPEN/PENDING deprecated); only
        # SUCCESS is proof the fulfillment actually completed. A non-SUCCESS
        # or missing status is routed through the existing uncertain/
        # reconcile path — never classified as `failed_clean` merely for not
        # being SUCCESS, since the id itself proves Shopify accepted the
        # request.
        evidence['fulfillment'] = fulfillment
        status = fulfillment.get('status')
        if status != 'SUCCESS':
            return self._uncertain_consequence(
                'data_shape_schema_mismatch',
                'fulfillmentCreate returned a real Fulfillment id but status '
                '%r is not SUCCESS; reconciling before trusting this as '
                'applied.' % (status,),
                evidence,
            )
        return {
            'observed_outcome': 'succeeded',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': 'fulfillmentCreate applied (Fulfillment %s).'
            % fulfillment_id,
            'evidence': evidence,
        }

    @api.model
    def _uncertain_consequence(self, error_class, message, evidence):
        return {
            'observed_outcome': 'uncertain',
            'error_class': error_class,
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': message,
            'evidence': dict(evidence or {}),
        }

    # ------------------------------------------------------------------
    # Callback 6: reconcile (post-C2 read-only; APPLIED / INCONCLUSIVE only)
    # ------------------------------------------------------------------

    @api.model
    def _reconcile_fulfillment_create(self, attempt, reconciliation_job=None):
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        order_gid = snapshot.get('order_gid')
        observed_identity = store.shop_domain
        if observed_identity != attempt.expected_store_identity:
            # Store identity changed — routed by the shared reconcile handler.
            return self._inconclusive_reconcile(
                observed_identity,
                'Reconciliation observed a different store identity.',
            )
        if not order_gid:
            return self._inconclusive_reconcile(
                observed_identity, 'No order identity to reconcile against.',
            )
        try:
            fulfillments = self._read_order_fulfillments(
                reconciliation_job or attempt.job_id, store, order_gid,
            )
        except FulfillmentReadError:
            # An incomplete/malformed read is INCONCLUSIVE, never absence.
            return self._inconclusive_reconcile(
                observed_identity,
                'The reconciliation read did not complete; inconclusive.',
            )
        if self._create_is_applied(
            attempt, snapshot, fulfillments, reconciliation_job,
        ):
            adopted_gid = self._adopted_fulfillment_gid(snapshot, fulfillments)
            return {
                'verdict': 'applied',
                'observed_store_identity': observed_identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Reconciliation found positive evidence the '
                           'fulfillment was created.',
                'evidence': {'adopted_fulfillment_gid': adopted_gid},
                'domain_payload': {'adopted_fulfillment_gid': adopted_gid},
            }
        # Everything else — read absence, unchanged quantities, no match,
        # concurrent activity — is INCONCLUSIVE. Post-C2 NOT_APPLIED is never an
        # actionable Wave 4 verdict; no resend is ever authorized.
        return self._inconclusive_reconcile(
            observed_identity,
            'No positive evidence of application; inconclusive (no resend).',
        )

    @api.model
    def _inconclusive_reconcile(self, observed_identity, message):
        return {
            'verdict': 'inconclusive',
            'observed_store_identity': observed_identity or '',
            'action': None,
            'error_class': None,
            'manual_review_subreason': None,
            'message': message,
            'evidence': {},
        }

    @api.model
    def _create_is_applied(
        self, attempt, snapshot, fulfillments, reconciliation_job=None,
    ):
        """Positive APPLIED evidence only: a fulfillment whose trackingInfo
        matches our sent tracking, or (no-tracking case) the FO remaining
        quantities decreased by EXACTLY our sent quantities."""
        sent_numbers = set(snapshot.get('sent_tracking_numbers') or [])
        if sent_numbers:
            for fulfillment in fulfillments:
                if not isinstance(fulfillment, dict):
                    continue
                info = fulfillment.get('trackingInfo') or []
                numbers = {
                    (t or {}).get('number')
                    for t in info if isinstance(t, dict)
                }
                if sent_numbers & numbers and fulfillment.get('status') == 'SUCCESS':
                    return True
            return False
        # No-tracking case (SRR-10): rely solely on FO remaining decreasing by
        # exactly the sent quantities. Any ambiguity -> not applied evidence ->
        # inconclusive (never a second create).
        return self._remaining_matches_exact_decrease(
            attempt, snapshot, reconciliation_job,
        )

    @api.model
    def _remaining_matches_exact_decrease(
        self, attempt, snapshot, reconciliation_job=None,
    ):
        try:
            fos = self._read_fulfillment_orders(
                reconciliation_job or attempt.job_id,
                attempt.store_id,
                snapshot['order_gid'],
            )
        except FulfillmentReadError:
            return False
        current = self._fo_remaining_snapshot(fos)
        before = snapshot.get('fo_remaining_snapshot') or {}
        expected = {}
        for entry in snapshot.get('line_items_by_fo') or []:
            for item in entry.get('fulfillmentOrderLineItems') or []:
                expected[item['id']] = expected.get(item['id'], 0) + item['quantity']
        for fo_line_id, qty in expected.items():
            b = before.get(fo_line_id)
            c = current.get(fo_line_id)
            if not isinstance(b, int) or not isinstance(c, int) or (b - c) != qty:
                return False
        return bool(expected)

    @api.model
    def _adopted_fulfillment_gid(self, snapshot, fulfillments):
        sent_numbers = set(snapshot.get('sent_tracking_numbers') or [])
        for fulfillment in fulfillments:
            if not isinstance(fulfillment, dict):
                continue
            info = fulfillment.get('trackingInfo') or []
            numbers = {
                (t or {}).get('number') for t in info if isinstance(t, dict)
            }
            if (not sent_numbers or (sent_numbers & numbers)) and (
                fulfillment.get('status') == 'SUCCESS'
            ):
                return fulfillment.get('id')
        return False

    # ------------------------------------------------------------------
    # Callback 7: apply_consequence (domain state: create/adopt the binding)
    # ------------------------------------------------------------------

    @api.model
    def _apply_consequence_fulfillment_create(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        if consequence['action'] != 'succeed':
            # fail_final / block_manual_review carry no domain write; the core
            # already set the job state. No resend is ever created here.
            return
        evidence = consequence.get('evidence') or {}
        fulfillment = evidence.get('fulfillment') or {}
        fulfillment_gid = (
            fulfillment.get('id')
            or (consequence.get('domain_payload') or {}).get(
                'adopted_fulfillment_gid'
            )
        )
        if not fulfillment_gid:
            _logger.warning(
                'fulfillment_create succeeded without a Fulfillment GID; '
                'job_id=%s.', job.id,
            )
            return
        self._upsert_fulfillment_binding(job, attempt, fulfillment, fulfillment_gid)

    @api.model
    def _upsert_fulfillment_binding(self, job, attempt, fulfillment, fulfillment_gid):
        Binding = self.env['shopify.connector.fulfillment.binding'].sudo()
        snapshot = attempt.preconditions_snapshot or {}
        picking = self.env['stock.picking'].browse(job.res_id)
        order_binding = self.env['shopify.connector.order.binding'].search([
            ('store_id', '=', job.store_id.id),
            ('sale_order_id', '=', picking.sale_id.id),
        ], limit=1)
        existing = Binding.search([
            ('store_id', '=', job.store_id.id),
            ('shopify_gid', '=', fulfillment_gid),
        ], limit=1)
        tracking = fulfillment.get('trackingInfo') if isinstance(fulfillment, dict) else None
        vals = {
            'shopify_fulfillment_order_gids': json.dumps(sorted({
                entry['fulfillmentOrderId']
                for entry in snapshot.get('line_items_by_fo') or []
            })),
            'tracking_numbers_snapshot': json.dumps(
                snapshot.get('sent_tracking_numbers') or []
            ),
            'notify_customer_sent': bool(snapshot.get('notify_customer')),
            'shopify_status_snapshot': (
                fulfillment.get('status') if isinstance(fulfillment, dict) else False
            ),
            'shopify_last_synced_at': fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
            return existing
        return Binding.create(dict(
            vals,
            store_id=job.store_id.id,
            shopify_gid=fulfillment_gid,
            picking_id=picking.id,
            order_binding_id=order_binding.id,
        ))
