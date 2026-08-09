import json
import logging
import uuid

from odoo import api, fields, models

from .shopify_connector_fulfillment_create_strategy import (
    FulfillmentPreC2FailClosedError,
)
from .shopify_connector_fulfillment_reader import FulfillmentReadError

_logger = logging.getLogger(__name__)

# Anonymous fulfillmentTrackingInfoUpdate document (module constant, guarded by
# this addon's source-guard test). RA-022: never the legacy V2 path. No
# @idempotent directive. Updates tracking IN PLACE — never a second fulfillment.
FULFILLMENT_TRACKING_UPDATE_DOCUMENT = (
    'mutation ($fulfillmentId: ID!, $trackingInfoInput: FulfillmentTrackingInput!, '
    '$notifyCustomer: Boolean) {\n'
    '  fulfillmentTrackingInfoUpdate(fulfillmentId: $fulfillmentId, '
    'trackingInfoInput: $trackingInfoInput, notifyCustomer: $notifyCustomer) {\n'
    '    fulfillment {\n'
    '      id\n'
    '      status\n'
    '      trackingInfo { number url company }\n'
    '    }\n'
    '    userErrors { field message }\n'
    '  }\n'
    '}'
)

FULFILLMENT_NODE_QUERY = (
    'query($id: ID!) {\n'
    '  fulfillment(id: $id) {\n'
    '    id\n'
    '    status\n'
    '    displayStatus\n'
    '    trackingInfo { number url company }\n'
    '  }\n'
    '}'
)


class ShopifyConnectorFulfillmentTrackingStrategy(models.AbstractModel):
    """The 7-callback Layer 2 strategy for `fulfillment_tracking_update` plus the
    tracking-domain reconcile read invoked by the shared
    `fulfillment_mutation_reconcile`. Post-C2: APPLIED / INCONCLUSIVE only; a
    possible prior `notifyCustomer` is never repeated from read absence
    (RA-009)."""

    _inherit = 'shopify.connector.fulfillment.service'

    @api.model
    def _read_fulfillment(self, job, store, fulfillment_gid):
        data = self._read_data(
            job, store, FULFILLMENT_NODE_QUERY, {'id': fulfillment_gid},
        )
        node = data.get('fulfillment')
        return node if isinstance(node, dict) else None

    # ------------------------------------------------------------------
    # Callback 2: prepare_local
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_fulfillment_tracking_update(self, job):
        binding = self.env['shopify.connector.fulfillment.binding'].browse(job.res_id)
        picking = binding.picking_id
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', job.store_id.id)], limit=1,
        )
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'binding_id': binding.id,
            'fulfillment_gid': binding.shopify_gid,
            'notify_customer': bool(
                settings and settings._fulfillment_notification_allowed()
            ),
            'tracking_numbers': self._picking_tracking_numbers(picking),
            'tracking_company': picking.carrier_id.name or '',
            'tracking_urls': self._picking_tracking_urls(picking),
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    # ------------------------------------------------------------------
    # Callback 3: prepare_preconditions
    # ------------------------------------------------------------------

    @api.model
    def _prepare_preconditions_fulfillment_tracking_update(
        self, local_snapshot, owner_context,
    ):
        read_job = self.env['shopify.connector.job'].browse(
            local_snapshot['job_id']
        )
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        fulfillment_gid = local_snapshot['fulfillment_gid']
        if not fulfillment_gid:
            self._fail_closed_pre_c2(
                'mapping_missing',
                'The fulfillment binding has no Shopify Fulfillment GID.',
            )
        try:
            node = self._read_fulfillment(
                read_job, store, fulfillment_gid,
            )
        except FulfillmentReadError as exc:
            self._fail_closed_pre_c2(exc.error_class, exc.message)
        if not node:
            self._fail_closed_pre_c2(
                'ambiguous_match',
                'The fulfillment to update no longer exists on Shopify.',
            )
        if node.get('status') == 'CANCELLED':
            self._fail_closed_pre_c2(
                'binding_conflict',
                'The Shopify fulfillment is CANCELLED; tracking cannot be '
                'updated.',
            )
        tracking_info = self._build_tracking_info(local_snapshot)
        if tracking_info is None:
            self._fail_closed_pre_c2(
                'mapping_missing',
                'No tracking information is available to update.',
            )
        variables = {
            'fulfillmentId': fulfillment_gid,
            'trackingInfoInput': tracking_info,
            'notifyCustomer': bool(local_snapshot['notify_customer']),
        }
        return {
            'mutation_domain': 'fulfillment_tracking_update',
            'operation': FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
            'variables': variables,
            'business_intent': {
                'mutation_domain': 'fulfillment_tracking_update',
                'store_id': local_snapshot['store_id'],
                'fulfillment_gid': fulfillment_gid,
                'tracking_info': tracking_info,
            },
            'remote_mutation_intent': {
                'operation_name': 'fulfillmentTrackingInfoUpdate',
                'fulfillment_gid': fulfillment_gid,
            },
            'preconditions_snapshot': {
                'fulfillment_gid': fulfillment_gid,
                'sent_tracking_numbers': local_snapshot['tracking_numbers'],
                'sent_tracking_info': tracking_info,
                'notify_customer': bool(local_snapshot['notify_customer']),
                'observed_before': node.get('trackingInfo'),
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()
                ),
            },
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity': local_snapshot['expected_store_identity'],
            # Non-empty to satisfy the merged Layer 2 request contract; the
            # operation document has NO @idempotent directive and never
            # references it, so it is never sent on the wire (see the
            # create-strategy note).
            'shopify_idempotency_key': uuid.uuid4().hex,
        }

    # ------------------------------------------------------------------
    # Callback 4: transport
    # ------------------------------------------------------------------

    @api.model
    def _transport_fulfillment_tracking_update(self, request, attempt_context):
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
                payload = data.get('fulfillmentTrackingInfoUpdate') or {}
                return {
                    'outcome': None,
                    'user_errors': payload.get('userErrors'),
                    'fulfillment': payload.get('fulfillment'),
                    'evidence': {'transport': 'fulfillmentTrackingInfoUpdate'},
                }
        except Exception as exc:  # noqa: BLE001 — never re-raise past C2
            return {
                'outcome': 'uncertain',
                'error_class': 'shopify_temporary_server_network',
                'evidence': {'exception_class': type(exc).__name__},
            }

    # ------------------------------------------------------------------
    # Callback 5: classify_direct_result
    # ------------------------------------------------------------------

    @api.model
    def _classify_direct_fulfillment_tracking_update(self, result):
        result = result or {}
        if result.get('outcome') == 'uncertain':
            return self._uncertain_consequence(
                result.get('error_class', 'shopify_temporary_server_network'),
                'Transport-level uncertainty during fulfillmentTrackingInfoUpdate.',
                result.get('evidence'),
            )
        user_errors = result.get('user_errors')
        evidence = dict(result.get('evidence') or {})
        if not isinstance(user_errors, list):
            return self._uncertain_consequence(
                'data_shape_schema_mismatch',
                'fulfillmentTrackingInfoUpdate returned a malformed userErrors '
                'container.',
                evidence,
            )
        if user_errors:
            evidence['user_errors'] = user_errors
            return {
                'observed_outcome': 'failed_clean',
                'error_class': 'shopify_user_errors_validation',
                'manual_review_subreason': False,
                'action': 'fail_final',
                'message': 'Shopify rejected fulfillmentTrackingInfoUpdate '
                           '(userErrors).',
                'evidence': evidence,
            }
        fulfillment = result.get('fulfillment')
        fulfillment_id = (
            fulfillment.get('id') if isinstance(fulfillment, dict) else None
        )
        if not fulfillment_id:
            return self._uncertain_consequence(
                'data_shape_schema_mismatch',
                'fulfillmentTrackingInfoUpdate returned empty userErrors but no '
                'Fulfillment id; reconciling before trusting this as applied.',
                evidence,
            )
        evidence['fulfillment'] = fulfillment
        return {
            'observed_outcome': 'succeeded',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': 'fulfillmentTrackingInfoUpdate applied.',
            'evidence': evidence,
        }

    # ------------------------------------------------------------------
    # Callback 6: reconcile (post-C2; APPLIED / INCONCLUSIVE only)
    # ------------------------------------------------------------------

    @api.model
    def _reconcile_fulfillment_tracking_update(
        self, attempt, reconciliation_job=None,
    ):
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        observed_identity = store.shop_domain
        if observed_identity != attempt.expected_store_identity:
            return self._inconclusive_reconcile(
                observed_identity,
                'Reconciliation observed a different store identity.',
            )
        fulfillment_gid = snapshot.get('fulfillment_gid')
        if not fulfillment_gid:
            return self._inconclusive_reconcile(
                observed_identity, 'No fulfillment identity to reconcile.',
            )
        try:
            node = self._read_fulfillment(
                reconciliation_job or attempt.job_id,
                store,
                fulfillment_gid,
            )
        except FulfillmentReadError:
            return self._inconclusive_reconcile(
                observed_identity,
                'The reconciliation read did not complete; inconclusive.',
            )
        sent_numbers = set(snapshot.get('sent_tracking_numbers') or [])
        current = {
            (t or {}).get('number')
            for t in ((node or {}).get('trackingInfo') or [])
            if isinstance(t, dict)
        }
        if node and sent_numbers and sent_numbers <= current:
            return {
                'verdict': 'applied',
                'observed_store_identity': observed_identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Reconciliation confirms the tracking update is '
                           'present.',
                'evidence': {'fulfillment_gid': fulfillment_gid},
                'domain_payload': {'fulfillment_gid': fulfillment_gid},
            }
        # Old/unchanged tracking, read absence, or any ambiguity is
        # INCONCLUSIVE. A possible prior notifyCustomer is never repeated.
        return self._inconclusive_reconcile(
            observed_identity,
            'Tracking update not positively confirmed; inconclusive (no '
            'resend, no repeated notification).',
        )

    # ------------------------------------------------------------------
    # Callback 7: apply_consequence
    # ------------------------------------------------------------------

    @api.model
    def _apply_consequence_fulfillment_tracking_update(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        if consequence['action'] != 'succeed':
            return
        binding = self.env['shopify.connector.fulfillment.binding'].sudo().browse(
            job.res_id
        )
        if not binding.exists():
            return
        snapshot = attempt.preconditions_snapshot or {}
        binding.write({
            'tracking_numbers_snapshot': json.dumps(
                snapshot.get('sent_tracking_numbers') or []
            ),
            'notify_customer_sent': bool(snapshot.get('notify_customer')),
            'shopify_last_synced_at': fields.Datetime.now(),
        })
