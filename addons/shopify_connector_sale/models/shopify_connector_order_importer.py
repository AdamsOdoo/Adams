import itertools
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)
from odoo.addons.shopify_connector_core.tools.redaction import redact

from .shopify_connector_tax_mapping import (
    build_tax_fingerprint,
    canonical_tax_rate,
    eligible_sale_tax_domain,
    safe_tax_preview,
    tax_posture_included,
    TAX_SOURCE_PREVIEW_MAX_LEN,
    TAX_TITLE_PREVIEW_MAX_LEN,
)


LINE_ITEMS_PAGE_SIZE = 100
SHIPPING_LINES_PAGE_SIZE = 50
DISCOUNT_APPLICATIONS_PAGE_SIZE = 50
LINE_ITEMS_PAGE_LIMIT = 100
SHIPPING_LINES_PAGE_LIMIT = 100
DISCOUNT_APPLICATIONS_PAGE_LIMIT = 100
SOLVER_K = 2
SOLVER_MAX_DEPENDENT_LINES = 2
SOLVER_MAX_CANDIDATE_VECTORS = 25
PENDING_RECHECK_MINUTES = 15
ORDER_LINE_DESCRIPTION_MAX_LEN = 512
ORDER_CANCELLED_PAYLOAD_PREFIX = 'webhook_cancelled|'
_EMAIL_RE = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')
_RFC3339_RE = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    r'(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$'
)
REDACTION_EXTENSION = frozenset((
    'address', 'address1', 'address2', 'billingAddress', 'city', 'company',
    'display_name', 'displayName', 'email', 'first_name', 'firstName',
    'incoming_email_normalized', 'last_name', 'lastName', 'name', 'phone',
    'shippingAddress', 'street', 'street2', 'zip',
))

# Contract-mandated evidence-only fields are deliberately limited to
# Order.confirmed/closed and Transaction.id/processedAt.  They are retained in
# the accepted query shape for authoritative lifecycle/payment evidence but are
# neither persisted nor used to mutate an Odoo order in this read-only MVP.
# Order.closedAt is separately parsed and shape-validated below.

ORDER_HEADER_QUERY = """
query ConnectorOrderHeader($id: ID!) {
  order(id: $id) {
    id name legacyResourceId createdAt processedAt updatedAt edited test
    currencyCode presentmentCurrencyCode taxesIncluded confirmed closed closedAt
    cancelledAt cancelReason displayFinancialStatus displayFulfillmentStatus email
    paymentGatewayNames
    transactions {
      id gateway kind status manualPaymentGateway processedAt
      amountSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    }
    customer {
      id firstName lastName
      defaultEmailAddress { emailAddress }
      defaultPhoneNumber { phoneNumber }
    }
    billingAddress {
      firstName lastName name address1 address2 city zip provinceCode
      countryCodeV2 phone
    }
    shippingAddress {
      firstName lastName name address1 address2 city zip provinceCode
      countryCodeV2 phone
    }
    totalPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    subtotalPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    totalTaxSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    totalDiscountsSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    totalShippingPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    totalTipReceivedSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    currentTotalPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    currentTotalTaxSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    currentShippingPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    currentTotalAdditionalFeesSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    currentTotalDutiesSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    totalCashRoundingAdjustment {
      paymentSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
      refundSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
    }
    taxLines {
      title source rate ratePercentage channelLiable
      priceSet { shopMoney { amount } presentmentMoney { amount } }
    }
    lineItems(first: 100) {
      edges { cursor node {
        id name title variantTitle quantity currentQuantity sku isGiftCard
        requiresShipping taxable variant { id } product { id }
        originalUnitPriceSet { shopMoney { amount } }
        originalTotalSet { shopMoney { amount } }
        discountedUnitPriceSet { shopMoney { amount } }
        discountedTotalSet { shopMoney { amount } }
        priceAfterAllDiscountsBeforeTaxesSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        discountAllocations {
          allocatedAmountSet {
            shopMoney { amount } presentmentMoney { amount }
          }
          discountApplication {
            __typename index allocationMethod targetType targetSelection
          }
        }
        taxLines {
          title source rate ratePercentage channelLiable
          priceSet { shopMoney { amount } }
        }
      } }
      pageInfo { hasNextPage endCursor }
    }
    shippingLines(first: 50) {
      edges { cursor node {
        id isRemoved title
        discountedPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
        currentDiscountedPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
        taxLines {
          title source rate ratePercentage channelLiable
          priceSet { shopMoney { amount } presentmentMoney { amount } }
        }
      } }
      pageInfo { hasNextPage endCursor }
    }
    discountApplications(first: 50) {
      edges { cursor node {
        __typename index allocationMethod targetSelection targetType
      } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

ORDER_LINE_ITEMS_PAGE_QUERY = """
query ConnectorOrderLineItemsPage($id: ID!, $after: String!) {
  order(id: $id) {
    id updatedAt
    lineItems(first: 100, after: $after) {
      edges { cursor node {
        id name title variantTitle quantity currentQuantity sku isGiftCard
        requiresShipping taxable variant { id } product { id }
        originalUnitPriceSet { shopMoney { amount } }
        originalTotalSet { shopMoney { amount } }
        discountedUnitPriceSet { shopMoney { amount } }
        discountedTotalSet { shopMoney { amount } }
        priceAfterAllDiscountsBeforeTaxesSet {
          shopMoney { amount currencyCode }
          presentmentMoney { amount currencyCode }
        }
        discountAllocations {
          allocatedAmountSet {
            shopMoney { amount } presentmentMoney { amount }
          }
          discountApplication {
            __typename index allocationMethod targetType targetSelection
          }
        }
        taxLines {
          title source rate ratePercentage channelLiable
          priceSet { shopMoney { amount } }
        }
      } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

ORDER_SHIPPING_LINES_PAGE_QUERY = """
query ConnectorOrderShippingLinesPage($id: ID!, $after: String!) {
  order(id: $id) {
    id updatedAt
    shippingLines(first: 50, after: $after) {
      edges { cursor node {
        id isRemoved title
        discountedPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
        currentDiscountedPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
        taxLines {
          title source rate ratePercentage channelLiable
          priceSet { shopMoney { amount } presentmentMoney { amount } }
        }
      } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY = """
query ConnectorOrderDiscountApplicationsPage($id: ID!, $after: String!) {
  order(id: $id) {
    id updatedAt
    discountApplications(first: 50, after: $after) {
      edges { cursor node {
        __typename index allocationMethod targetSelection targetType
      } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


class OrderPolicySkip(Exception):
    def __init__(self, skip_reason, message, technical_detail=False):
        super().__init__(message)
        self.skip_reason = skip_reason
        self.message = message
        self.technical_detail = technical_detail


class OrderPendingWait(Exception):
    def __init__(self, expiry_hours):
        super().__init__('Pending non-manual payment is waiting for fresh evidence.')
        self.expiry_hours = expiry_hours


class OrderFatalSchemaError(Exception):
    """A source defect that cannot change through blind automatic retry."""

    def __init__(self, message, technical_detail=False):
        super().__init__(message)
        self.message = message
        self.technical_detail = technical_detail


class _RejectedCandidate(Exception):
    pass


class ShopifyConnectorOrderImporter(models.AbstractModel):
    """Read-only Shopify Order importer; every local import is atomic."""

    _name = 'shopify.connector.order.importer'
    _description = 'Shopify Connector Order Importer Service'

    @api.model
    def import_order_sync(self, store, shopify_order_gid, job=False):
        client = self.env['shopify.connector.api.client']
        try:
            with client.execute_business(
                job, store, ORDER_HEADER_QUERY,
                variables={'id': shopify_order_gid},
            ) as result:
                order = self._extract_order(result, shopify_order_gid)
                initial_updated_at = order.get('updatedAt')
                self._validate_connection_shape(order, 'lineItems')
                self._validate_connection_shape(order, 'shippingLines')
                self._validate_connection_shape(order, 'discountApplications')

            line_items = self._collect_connection(
                client, job, store, shopify_order_gid, initial_updated_at,
                order['lineItems'], 'lineItems', ORDER_LINE_ITEMS_PAGE_QUERY,
                LINE_ITEMS_PAGE_LIMIT,
            )
            shipping_lines = self._collect_connection(
                client, job, store, shopify_order_gid, initial_updated_at,
                order['shippingLines'], 'shippingLines',
                ORDER_SHIPPING_LINES_PAGE_QUERY, SHIPPING_LINES_PAGE_LIMIT,
            )
            discount_applications = self._collect_connection(
                client, job, store, shopify_order_gid, initial_updated_at,
                order['discountApplications'], 'discountApplications',
                ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY,
                DISCOUNT_APPLICATIONS_PAGE_LIMIT,
            )
            payload = dict(order)
            payload.pop('lineItems', None)
            payload.pop('shippingLines', None)
            payload.pop('discountApplications', None)
            payload.update({
                'line_items': line_items,
                'shipping_lines': shipping_lines,
                'discount_applications': discount_applications,
            })
            outcome = self._apply_import(store, payload, job=job)
            self.env.flush_all()
            return outcome
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class, exc.reason, exc.technical_detail,
            ) from exc

    @api.model
    def _extract_order(self, result, expected_gid):
        if not isinstance(result, dict) or not isinstance(result.get('data'), dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence had an invalid response envelope.',
            )
        order = result['data'].get('order')
        if not order or order.get('id') != expected_gid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence was missing or had the wrong identity.',
            )
        if not order.get('updatedAt'):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted updatedAt.',
            )
        return order

    @api.model
    def _validate_connection_shape(self, order, name):
        connection = order.get(name)
        if not isinstance(connection, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted the %s connection.' % name,
            )
        if not isinstance(connection.get('edges'), list):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'The %s connection omitted edges.' % name,
            )
        if not isinstance(connection.get('pageInfo'), dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'The %s connection omitted pageInfo.' % name,
            )
        page_info = connection['pageInfo']
        has_next = page_info.get('hasNextPage')
        if (
            not isinstance(has_next, bool)
            or (
                has_next
                and (
                    not isinstance(page_info.get('endCursor'), str)
                    or not page_info.get('endCursor')
                )
            )
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'The %s connection had invalid pagination metadata.' % name,
            )

    @api.model
    def _collect_connection(
        self, client, job, store, order_gid, initial_updated_at,
        first_connection, name, page_query, page_limit,
    ):
        edges = []
        seen_edge_cursors = set()
        seen_page_cursors = set()
        seen_secondary = set()
        page_count = 1
        connection = first_connection
        while True:
            self._append_page_edges(
                name, connection.get('edges') or [], edges,
                seen_edge_cursors, seen_secondary,
            )
            page_info = connection.get('pageInfo') or {}
            if not page_info.get('hasNextPage'):
                return [edge['node'] for edge in edges]
            cursor = page_info.get('endCursor')
            if not cursor or cursor in seen_page_cursors:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The %s cursor did not make progress.' % name,
                )
            seen_page_cursors.add(cursor)
            if page_count >= page_limit:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The %s page ceiling (%d) was exceeded.' % (
                        name, page_limit,
                    ),
                )
            with client.execute_business(
                job, store, page_query,
                variables={'id': order_gid, 'after': cursor},
            ) as result:
                page_order = self._extract_order(result, order_gid)
                if page_order.get('updatedAt') != initial_updated_at:
                    raise JobHandlerError(
                        'concurrency_race_conflict',
                        'Shopify order evidence changed during pagination.',
                    )
                self._validate_connection_shape(page_order, name)
                connection = page_order[name]
            page_count += 1

    @api.model
    def _append_page_edges(
        self, name, page_edges, collected, seen_cursors, seen_secondary,
    ):
        for edge in page_edges:
            cursor = edge.get('cursor') if isinstance(edge, dict) else False
            node = edge.get('node') if isinstance(edge, dict) else False
            if not cursor or not isinstance(node, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The %s connection contained a malformed edge.' % name,
                )
            if cursor in seen_cursors:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The %s connection repeated an edge cursor.' % name,
                )
            secondary = self._secondary_identity(name, node)
            if secondary and secondary in seen_secondary:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The %s connection repeated a node identity.' % name,
                )
            seen_cursors.add(cursor)
            if secondary:
                seen_secondary.add(secondary)
            collected.append({'cursor': cursor, 'node': node})

    @api.model
    def _secondary_identity(self, name, node):
        if name == 'lineItems':
            if not node.get('id'):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify line item omitted its required identity.',
                )
            return ('line', node['id'])
        if name == 'shippingLines':
            return ('shipping', node['id']) if node.get('id') else False
        typename = node.get('__typename')
        index = node.get('index')
        if (
            not typename
            or isinstance(index, bool)
            or not isinstance(index, int)
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A discount application omitted its typed index identity.',
            )
        return (
            'discount', typename, index,
        )

    @api.model
    def _apply_import(self, store, payload, job=False):
        settings = self._settings_for_store(store)
        company = settings.order_company_id
        if self.env.company != company:
            service = self.with_company(company)
            return service._apply_import(
                store.with_env(service.env), payload,
                job=job.with_env(service.env) if job else False,
            )
        Binding = self.env['shopify.connector.order.binding']
        existing = Binding.search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', payload['id']),
        ], limit=1)
        if existing:
            return self._refresh_existing(existing, payload, settings, job)
        self._precreation_gates(payload, settings)

        with self.env.cr.savepoint():
            partner, resolution = self._resolve_customer(
                store, payload, settings, job,
            )
            if partner.company_id and partner.company_id != company:
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'The resolved order customer belongs to another '
                    'Odoo company.',
                )
            invoice_partner, shipping_partner = self._resolve_order_addresses(
                partner, payload, resolution,
            )
            pricelist = self._resolve_pricelist(settings, payload)
            self._validate_payment_term(settings.order_payment_term_id)
            order_vals = {
                'partner_id': partner.id,
                'partner_invoice_id': invoice_partner.id,
                'partner_shipping_id': shipping_partner.id,
                'company_id': company.id,
                'pricelist_id': pricelist.id,
                'payment_term_id': settings.order_payment_term_id.id,
                'date_order': self._to_odoo_datetime(
                    payload.get('processedAt') or payload.get('createdAt')
                ) or fields.Datetime.now(),
                'origin': payload.get('name') or payload['id'],
                'client_order_ref': payload.get('name') or payload['id'],
            }
            if settings.order_sales_team_id:
                order_vals['team_id'] = settings.order_sales_team_id.id
            order = self.env['sale.order'].create(order_vals)
            line_plans = self._create_order_lines(
                order, store, payload, settings, job=job,
            )
            self._solve_and_assert_totals(order, line_plans, payload)

            gateway = self._classify_manual_gateway(payload)
            confirmation = self._confirmation_outcome(
                payload, settings, gateway,
            )
            if confirmation['confirm']:
                order.action_confirm()

            binding_vals = self._binding_snapshot_vals(
                payload, resolution, gateway, confirmation,
            )
            binding_vals.update({
                'store_id': store.id,
                'shopify_gid': payload['id'],
                'sale_order_id': order.id,
                'match_key': 'existing_binding',
                'matched_by_uid': self.env.uid,
                'matched_at': fields.Datetime.now(),
            })
            try:
                with self.env.cr.savepoint():
                    binding = Binding.sudo().create(binding_vals)
            except IntegrityError as exc:
                # The outer savepoint rolls the new order and lines back.
                # Do not attempt an in-transaction handler replay or rely on
                # seeing the winner in a REPEATABLE READ snapshot.
                raise JobHandlerError(
                    'concurrency_race_conflict',
                    'A concurrent order import won the permanent binding '
                    'race.',
                    json.dumps({
                        'shopify_order_gid': payload['id'],
                    }, sort_keys=True),
                ) from exc
            binding = Binding.browse(binding.id)
            if gateway['state'] == 'mixed' and job:
                self.env['shopify.connector.job.log']._system_append(
                    job,
                    'note',
                    'Order imported as a draft for payment-evidence review.',
                    technical_detail=self._safe_gateway_evidence(payload),
                )
            return binding

    @api.model
    def _settings_for_store(self, store):
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', store.id),
        ], limit=1)
        if (
            not settings
            or not settings.sale_domain_enabled
            or not settings.order_company_id
            or not settings.order_payment_term_id
        ):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'Order import requires enabled sale-domain settings, an '
                'order company, and an explicit payment term.',
            )
        return settings

    @api.model
    def _precreation_gates(self, payload, settings):
        status = payload.get('displayFinancialStatus')
        if not status:
            raise OrderFatalSchemaError(
                'Shopify order evidence omitted displayFinancialStatus.',
                json.dumps({
                    'shopify_order_gid': payload.get('id'),
                    'display_financial_status': None,
                }, sort_keys=True),
            )
        if payload.get('totalTaxSet') is None:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted totalTaxSet.',
            )
        self._validate_refresh_evidence(payload)
        if not isinstance(payload.get('taxesIncluded'), bool):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted a Boolean taxesIncluded value.',
            )
        if payload.get('edited'):
            raise OrderPolicySkip(
                'unsupported_order_edit',
                'Automatic import skipped: edited Shopify orders are not '
                'supported in the MVP.',
                self._safe_evidence(payload, ('id', 'updatedAt', 'edited')),
            )
        if payload.get('test') and not settings.order_import_include_test:
            raise OrderPolicySkip(
                'test_order_excluded',
                'Automatic import skipped: test orders are excluded.',
                self._safe_evidence(payload, ('id', 'updatedAt', 'test')),
            )
        if payload.get('cancelledAt'):
            raise OrderPolicySkip(
                'order_pre_cancelled',
                'Automatic import skipped: the Shopify order was already '
                'cancelled.',
                self._safe_evidence(payload, ('id', 'updatedAt', 'cancelReason')),
            )
        currency = payload.get('currencyCode')
        presentment = payload.get('presentmentCurrencyCode')
        if not currency or not presentment:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted a currency code.',
            )
        if currency != presentment:
            raise OrderPolicySkip(
                'divergent_presentment_currency',
                'Automatic import not supported: divergent presentment '
                'currency (DEC-020).',
                self._safe_evidence(payload, (
                    'id', 'currencyCode', 'presentmentCurrencyCode',
                    'totalPriceSet',
                )),
            )
        currency_record = self.env['res.currency'].search([
            ('name', '=', currency),
        ], limit=1)
        if (
            currency_record
            and Decimal(str(currency_record.rounding)) < Decimal('0.01')
        ):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'Currencies finer than two decimal places require a named '
                'Shopify dev-store rounding verification before onboarding.',
                json.dumps({
                    'currency': currency,
                    'rounding': str(currency_record.rounding),
                    'verification_state': 'required',
                }, sort_keys=True),
            )
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'totalTaxSet',
            'totalDiscountsSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalPriceSet',
            'currentTotalTaxSet', 'currentShippingPriceSet',
            'currentTotalDutiesSet', 'currentTotalAdditionalFeesSet',
        ):
            bag = payload.get(field_name)
            if bag is not None:
                self._validate_money_bag_shape(
                    bag, currency, presentment, field_name,
                )
        rounding = payload.get('totalCashRoundingAdjustment') or {}
        for field_name in ('paymentSet', 'refundSet'):
            bag = rounding.get(field_name)
            if bag is not None:
                self._validate_money_bag_currency(
                    bag, currency,
                    'totalCashRoundingAdjustment.%s' % field_name,
                )
        if not payload.get('line_items'):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify order must contain at least one line item.',
            )
        self._validate_discount_evidence(payload)
        self._validate_order_tax_evidence(payload)
        upper = status.upper()
        supported_states = {
            'PAID', 'AUTHORIZED', 'PENDING', 'PARTIALLY_PAID',
            'PARTIALLY_REFUNDED', 'REFUNDED', 'VOIDED', 'EXPIRED',
        }
        if upper not in supported_states:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify returned an unknown financial-status value.',
                json.dumps({'financial_status': upper}, sort_keys=True),
            )
        if upper in ('REFUNDED', 'VOIDED', 'EXPIRED'):
            raise OrderPolicySkip(
                'unsupported_financial_state',
                'Automatic import skipped: the Shopify financial state is '
                'terminal and outside the MVP import posture.',
                json.dumps({'financial_status': upper}, sort_keys=True),
            )
        if upper == 'PARTIALLY_REFUNDED':
            raise JobHandlerError(
                'financial_total_mismatch',
                'Partially refunded orders require operator review.',
            )
        if (
            upper == 'PARTIALLY_PAID'
            and settings.order_confirmation_policy != 'quotations_only'
        ):
            raise JobHandlerError(
                'financial_total_mismatch',
                'Partially paid orders require operator review under this '
                'confirmation policy.',
            )
        if not self._money_equal(
            payload.get('totalPriceSet'), payload.get('currentTotalPriceSet'),
        ):
            raise OrderPolicySkip(
                'refunded_or_removed_quantity',
                'Automatic import skipped: current product totals differ '
                'from original order evidence.',
            )
        if not self._money_equal(
            payload.get('totalTaxSet'), payload.get('currentTotalTaxSet'),
        ):
            raise OrderPolicySkip(
                'refunded_or_removed_quantity',
                'Automatic import skipped: current tax differs from original '
                'order evidence.',
            )
        for line in payload.get('line_items') or []:
            self._validate_money_bag_currency(
                line.get('priceAfterAllDiscountsBeforeTaxesSet'),
                currency,
                'lineItems.priceAfterAllDiscountsBeforeTaxesSet',
            )
            if line.get('quantity') != line.get('currentQuantity'):
                raise OrderPolicySkip(
                    'refunded_or_removed_quantity',
                    'Automatic import skipped: a product quantity was refunded '
                    'or removed.',
                    json.dumps({
                        'line_item_gid': line.get('id'),
                        'quantity': line.get('quantity'),
                        'current_quantity': line.get('currentQuantity'),
                    }, sort_keys=True),
                )
        shipping_total = self._money_decimal(
            payload.get('currentShippingPriceSet'),
        )
        shipping_sum = Decimal('0')
        for shipping in payload.get('shipping_lines') or []:
            if not isinstance(shipping, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify shipping line had an invalid shape.',
                )
            self._validate_money_bag_currency(
                shipping.get('discountedPriceSet'),
                currency,
                'shippingLines.discountedPriceSet',
            )
            self._validate_money_bag_currency(
                shipping.get('currentDiscountedPriceSet'),
                currency,
                'shippingLines.currentDiscountedPriceSet',
            )
            if (
                shipping.get('isRemoved')
                or not self._money_equal(
                    shipping.get('discountedPriceSet'),
                    shipping.get('currentDiscountedPriceSet'),
                )
            ):
                raise OrderPolicySkip(
                    'refunded_or_removed_shipping',
                    'Automatic import skipped: shipping evidence was removed '
                    'or changed.',
                )
            shipping_sum += self._money_decimal(
                shipping.get('currentDiscountedPriceSet'),
            )
        for transaction in payload.get('transactions') or []:
            if isinstance(transaction, dict) and transaction.get('amountSet'):
                self._validate_money_bag_currency(
                    transaction['amountSet'], currency,
                    'transactions.amountSet',
                )
        if shipping_sum != shipping_total:
            raise OrderPolicySkip(
                'refunded_or_removed_shipping',
                'Automatic import skipped: shipping totals are inconsistent.',
            )
        if not self._money_is_zero(payload.get('currentTotalDutiesSet')):
            raise OrderPolicySkip(
                'unsupported_duties',
                'Automatic import skipped: duties are not supported.',
                json.dumps({
                    'duties': self._safe_money_dict(
                        payload.get('currentTotalDutiesSet')
                    ),
                    'additional_fees_nonzero': not self._money_is_zero(
                        payload.get('currentTotalAdditionalFeesSet')
                    ),
                    'remaining_fee_composition_inferred': False,
                }, sort_keys=True),
            )
        if not self._money_is_zero(payload.get('currentTotalAdditionalFeesSet')):
            raise OrderPolicySkip(
                'unsupported_additional_fees',
                'Automatic import skipped: additional fees are not supported.',
                self._safe_money_evidence(
                    payload.get('currentTotalAdditionalFeesSet'),
                ),
            )
        if (
            not self._money_is_zero(rounding.get('paymentSet'))
            or not self._money_is_zero(rounding.get('refundSet'))
        ):
            raise OrderPolicySkip(
                'unsupported_cash_rounding',
                'Automatic import skipped: cash rounding is not supported.',
                json.dumps({
                    'payment': self._safe_money_dict(rounding.get('paymentSet')),
                    'refund': self._safe_money_dict(rounding.get('refundSet')),
                }, sort_keys=True),
            )
        if not self._money_is_zero(payload.get('totalTipReceivedSet')):
            raise OrderPolicySkip(
                'unsupported_tip_tax_treatment',
                'Automatic import skipped: tip tax treatment is unsupported.',
                self._safe_money_evidence(payload.get('totalTipReceivedSet')),
            )

    @api.model
    def _validate_refresh_evidence(self, payload):
        """Validate snapshot shapes without applying new-order policy gates."""
        status = payload.get('displayFinancialStatus')
        if status is not None and (
            not isinstance(status, str)
            or status.upper() not in {
                'PAID', 'AUTHORIZED', 'PENDING', 'PARTIALLY_PAID',
                'PARTIALLY_REFUNDED', 'REFUNDED', 'VOIDED', 'EXPIRED',
            }
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify returned an unknown financial-status value.',
            )
        if not isinstance(payload.get('taxesIncluded'), bool):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted a Boolean taxesIncluded value.',
            )
        currency = payload.get('currencyCode')
        presentment = payload.get('presentmentCurrencyCode')
        if not currency or not presentment:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted a currency code.',
            )
        for field_name in (
            'totalPriceSet', 'totalTaxSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalPriceSet',
            'currentTotalTaxSet', 'currentShippingPriceSet',
        ):
            if payload.get(field_name) is None:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order evidence omitted %s.' % field_name,
                )
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'totalTaxSet',
            'totalDiscountsSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalPriceSet',
            'currentTotalTaxSet', 'currentShippingPriceSet',
            'currentTotalDutiesSet', 'currentTotalAdditionalFeesSet',
        ):
            bag = payload.get(field_name)
            if bag is not None:
                self._validate_money_bag_shape(
                    bag, currency, presentment, field_name,
                )
        rounding = payload.get('totalCashRoundingAdjustment')
        if not isinstance(rounding, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order evidence omitted cash-rounding evidence.',
            )
        for field_name in ('paymentSet', 'refundSet'):
            if rounding.get(field_name) is None:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify cash-rounding evidence omitted %s.' % field_name,
                )
            self._validate_money_bag_shape(
                rounding[field_name], currency, presentment,
                'totalCashRoundingAdjustment.%s' % field_name,
            )
        for field_name in (
            'createdAt', 'processedAt', 'updatedAt', 'closedAt', 'cancelledAt',
        ):
            value = payload.get(field_name)
            if field_name in ('createdAt', 'updatedAt') and not value:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order evidence omitted %s.' % field_name,
                )
            if value:
                try:
                    self._to_odoo_datetime(value)
                except (TypeError, ValueError) as exc:
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'Shopify order evidence contained an invalid %s.'
                        % field_name,
                    ) from exc

    @api.model
    def _validate_discount_evidence(self, payload):
        applications = {}
        for application in payload.get('discount_applications') or []:
            if not isinstance(application, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A discount application had an invalid shape.',
                )
            identity = self._discount_application_identity(application)
            if identity in applications:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A discount application identity was repeated.',
                )
            applications[identity] = self._discount_application_shape(
                application,
            )
        for line in payload.get('line_items') or []:
            if not isinstance(line, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify line item had an invalid shape.',
                )
            if not isinstance(line.get('requiresShipping'), bool) or not isinstance(
                line.get('taxable'), bool
            ):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify line item omitted Boolean classification flags.',
                )
            if not line['taxable'] and (line.get('taxLines') or []):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A non-taxable Shopify line carried tax evidence.',
                )
            for field_name in (
                'originalUnitPriceSet', 'originalTotalSet',
                'discountedUnitPriceSet', 'discountedTotalSet',
            ):
                self._money_decimal(line.get(field_name))
            for allocation in line.get('discountAllocations') or []:
                if not isinstance(allocation, dict):
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'A discount allocation had an invalid shape.',
                    )
                amount = allocation.get('allocatedAmountSet')
                shop = self._money_side_decimal(amount, 'shopMoney')
                presentment = self._money_side_decimal(
                    amount, 'presentmentMoney',
                )
                if shop < 0 or shop != presentment:
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'A discount allocation had inconsistent money evidence.',
                    )
                reference = allocation.get('discountApplication')
                if not isinstance(reference, dict):
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'A discount allocation omitted its application.',
                    )
                identity = self._discount_application_identity(reference)
                shape = self._discount_application_shape(reference)
                if identity not in applications or applications[identity] != shape:
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'Discount allocation/application evidence disagreed.',
                    )
                if shape[1] != 'LINE_ITEM':
                    raise JobHandlerError(
                        'data_shape_schema_mismatch',
                        'A product-line discount targeted a different domain.',
                    )

    @api.model
    def _discount_application_identity(self, application):
        typename = application.get('__typename')
        index = application.get('index')
        if (
            not isinstance(typename, str)
            or not typename
            or isinstance(index, bool)
            or not isinstance(index, int)
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A discount application omitted its typed index identity.',
            )
        return typename, index

    @api.model
    def _discount_application_shape(self, application):
        shape = tuple(application.get(field_name) for field_name in (
            'allocationMethod', 'targetType', 'targetSelection',
        ))
        if any(not isinstance(value, str) or not value for value in shape):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A discount application omitted classification evidence.',
            )
        return shape

    @api.model
    def _validate_order_tax_evidence(self, payload):
        order_tax_lines = payload.get('taxLines') or []
        order_by_fingerprint = self._tax_fingerprint_amounts(
            order_tax_lines, payload.get('taxesIncluded'),
            require_presentment=True,
        )
        if self._tax_source_total(order_tax_lines) != self._money_decimal(
            payload.get('totalTaxSet')
        ):
            raise JobHandlerError(
                'financial_total_mismatch',
                'Order-level tax lines do not reconcile with totalTaxSet.',
            )
        source_tax_lines = []
        for line in payload.get('line_items') or []:
            source_tax_lines.extend(line.get('taxLines') or [])
        for shipping in payload.get('shipping_lines') or []:
            source_tax_lines.extend(shipping.get('taxLines') or [])
        source_by_fingerprint = self._tax_fingerprint_amounts(
            source_tax_lines, payload.get('taxesIncluded'),
            require_presentment=False,
        )
        if source_by_fingerprint != order_by_fingerprint:
            raise JobHandlerError(
                'financial_total_mismatch',
                'Order-level and source-line tax fingerprints do not '
                'reconcile.',
            )

    @api.model
    def _tax_fingerprint_amounts(
        self, tax_lines, price_included, require_presentment,
    ):
        totals = {}
        for evidence in tax_lines:
            if not isinstance(evidence, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify tax line had an invalid shape.',
                )
            try:
                fingerprint = build_tax_fingerprint(
                    evidence.get('rate'), evidence.get('ratePercentage'),
                    evidence.get('title'), evidence.get('source'),
                    evidence.get('channelLiable'), price_included,
                )
                price = evidence.get('priceSet')
                shop = self._money_side_decimal(price, 'shopMoney')
                presentment_node = (
                    price.get('presentmentMoney')
                    if isinstance(price, dict) else None
                )
                if require_presentment or presentment_node is not None:
                    presentment = self._money_side_decimal(
                        price, 'presentmentMoney',
                    )
                    if shop != presentment:
                        raise ValidationError(
                            'Tax evidence disagrees across equal currencies.'
                        )
            except (InvalidOperation, ValidationError, JobHandlerError) as exc:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify tax evidence was malformed.',
                ) from exc
            totals[fingerprint] = totals.get(fingerprint, Decimal('0')) + shop
        return totals

    @api.model
    def _resolve_customer(self, store, payload, settings, job):
        CustomerBinding = self.env['shopify.connector.customer.binding']
        CustomerImporter = self.env['shopify.connector.customer.importer']
        customer = payload.get('customer') or False
        if customer and customer.get('id'):
            binding = CustomerBinding.search([
                ('store_id', '=', store.id),
                ('shopify_gid', '=', customer['id']),
            ], limit=1)
            if binding:
                return binding.partner_id, 'existing_binding'
            email_node = customer.get('defaultEmailAddress') or {}
            email = email_node.get('emailAddress')
            if email:
                name = ' '.join(filter(None, (
                    customer.get('firstName'), customer.get('lastName'),
                ))) or customer['id']
                customer_payload = {
                    'gid': customer['id'],
                    'first_name': customer.get('firstName'),
                    'last_name': customer.get('lastName'),
                    'display_name': name,
                    'email': email,
                    'phone': (
                        (customer.get('defaultPhoneNumber') or {}).get(
                            'phoneNumber'
                        )
                    ),
                    'address': None,
                }
                normalized = CustomerImporter._normalize_incoming_email(email)
                active_before = (
                    CustomerImporter._find_active_candidates(normalized)
                    if normalized else self.env['res.partner'].browse()
                )
                try:
                    created_binding = CustomerImporter._apply_import(
                        store, customer_payload, job=job,
                    )
                except JobHandlerError as exc:
                    raise JobHandlerError(
                        exc.error_class,
                        exc.reason,
                        self._redact_evidence(exc.technical_detail),
                    ) from exc
                resolution = 'email_match' if active_before else 'created'
                return created_binding.partner_id, resolution

        email = payload.get('email')
        normalized = email_normalize(email, strict=False) if email else False
        if normalized:
            active = CustomerImporter._find_active_candidates(normalized)
            if len(active) > 1:
                raise JobHandlerError(
                    'ambiguous_match',
                    'Ambiguous guest-order customer match.',
                    self._redact_evidence(
                        CustomerImporter._build_candidate_payload(
                            payload['id'], normalized, active,
                        )
                    ),
                )
            if len(active) == 1:
                return active, 'guest_email_match'
            archived = CustomerImporter._find_archived_candidates(normalized)
            if archived:
                raise JobHandlerError(
                    'duplicate_risk',
                    'Archived customer matches require operator review.',
                    self._redact_evidence(
                        CustomerImporter._build_candidate_payload(
                            payload['id'], normalized, archived,
                        )
                    ),
                )
            partner = self.env['res.partner'].create({
                'name': self._order_contact_name(payload),
                'email': email,
            })
            return partner, 'guest_created'
        if settings.customer_fallback_partner_id:
            return settings.customer_fallback_partner_id, 'fallback'
        raise JobHandlerError(
            'odoo_validation_configuration',
            'A customer fallback partner is required for an order with no '
            'usable customer email.',
        )

    @api.model
    def _order_contact_name(self, payload):
        address = payload.get('billingAddress') or payload.get('shippingAddress') or {}
        return (
            address.get('name')
            or ' '.join(filter(None, (
                address.get('firstName'), address.get('lastName'),
            )))
            or 'Shopify Guest'
        )

    @api.model
    def _resolve_order_addresses(self, partner, payload, resolution):
        invoice = self._resolve_address_child(
            partner, payload.get('billingAddress'), 'invoice',
            payload.get('name') if resolution == 'fallback' else False,
        )
        shipping = self._resolve_address_child(
            partner, payload.get('shippingAddress'), 'delivery',
            payload.get('name') if resolution == 'fallback' else False,
        )
        defaults = partner.address_get(['invoice', 'delivery'])
        return (
            invoice or self.env['res.partner'].browse(
                defaults.get('invoice') or partner.id
            ),
            shipping or self.env['res.partner'].browse(
                defaults.get('delivery') or partner.id
            ),
        )

    @api.model
    def _resolve_address_child(self, partner, address, address_type, fallback_name):
        if not address:
            return self.env['res.partner'].browse()
        CustomerImporter = self.env['shopify.connector.customer.importer']
        country = CustomerImporter._resolve_country(address.get('countryCodeV2'))
        state = (
            CustomerImporter._resolve_state(country, address.get('provinceCode'))
            if country else self.env['res.country.state'].browse()
        )
        name = fallback_name or address.get('name') or ' '.join(filter(None, (
            address.get('firstName'), address.get('lastName'),
        ))) or partner.name
        values = {
            'parent_id': partner.id,
            'type': address_type,
            'name': name,
            'street': address.get('address1') or False,
            'street2': address.get('address2') or False,
            'city': address.get('city') or False,
            'zip': address.get('zip') or False,
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
            'phone': address.get('phone') or False,
        }
        identity_fields = (
            'name', 'street', 'street2', 'city', 'zip',
            'country_id', 'state_id',
        )
        if all(
            (partner[field_name].id if field_name in ('country_id', 'state_id')
             else partner[field_name]) == values[field_name]
            for field_name in identity_fields
        ):
            return partner
        domain = [
            ('parent_id', '=', partner.id),
            ('type', '=', address_type),
        ] + [
            (field_name, '=', values[field_name])
            for field_name in identity_fields
        ]
        existing = self.env['res.partner'].search(domain, limit=1)
        return existing or self.env['res.partner'].create(values)

    @api.model
    def _resolve_pricelist(self, settings, payload):
        currency = payload['currencyCode']
        if settings.order_pricelist_id:
            pricelist = settings.order_pricelist_id
            if not pricelist.active or pricelist.currency_id.name != currency:
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'The configured order pricelist is inactive or has the '
                    'wrong currency.',
                )
            return pricelist
        pricelist = self.env['product.pricelist'].search([
            ('active', '=', True),
            ('currency_id.name', '=', currency),
            '|', ('company_id', '=', False),
            ('company_id', '=', settings.order_company_id.id),
        ], order='company_id desc, id', limit=1)
        if not pricelist:
            raise JobHandlerError(
                'odoo_validation_configuration',
                'No active pricelist matches the Shopify shop currency.',
            )
        return pricelist

    @api.model
    def _validate_payment_term(self, term):
        if (
            getattr(term, 'early_discount', False)
            and getattr(term, 'early_pay_discount_computation', False) == 'mixed'
            and getattr(term, 'discount_percentage', 0)
        ):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The configured payment term has an unsupported early-payment '
                'discount structure.',
                'unsupported_early_payment_discount_payment_term',
            )

    @api.model
    def _create_order_lines(self, order, store, payload, settings, job=False):
        plans = []
        Line = self.env['sale.order.line']
        adjustment_product = False
        discount_product = False
        discount_precision = self.env[
            'decimal.precision'
        ].precision_get('Discount')
        discount_step = Decimal(1).scaleb(-discount_precision)
        gift_card_gids = []
        for item in payload.get('line_items') or []:
            quantity = item.get('quantity')
            if not isinstance(quantity, int) or quantity <= 0:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify line item had an invalid quantity.',
                )
            product = self._resolve_product(store, item, settings)
            source_target = self._money_decimal(
                item.get('priceAfterAllDiscountsBeforeTaxesSet'),
            )
            taxes, rate_total, signature = self._resolve_taxes(
                order, store, item.get('taxLines') or [],
                payload.get('taxesIncluded'), settings,
            )
            original_unit = self._money_decimal(item.get('originalUnitPriceSet'))
            original_base = self._raw_excluded_for_values(
                order, product, taxes, original_unit, quantity,
            )
            if source_target < 0 or source_target > original_base:
                raise JobHandlerError(
                    'financial_total_mismatch',
                    'A Shopify line net could not be attributed to a '
                    'non-negative discount on its source line.',
                )
            discount = Decimal('0')
            if original_base:
                discount = (
                    Decimal('1') - (source_target / original_base)
                ) * Decimal('100')
                discount = discount.quantize(
                    discount_step, rounding=ROUND_HALF_UP,
                )
            line = Line.create({
                'order_id': order.id,
                'product_id': product.id,
                'name': self._line_name(item),
                'product_uom_qty': quantity,
                'price_unit': float(original_unit),
                'discount': float(discount),
                'tax_ids': [(6, 0, taxes.ids)],
                'shopify_line_item_gid': item.get('id'),
            })
            represented = self._line_raw_excluded(line)
            if represented < source_target and discount >= discount_step:
                # Keep an order-discount remainder negative. Odoo's native
                # discount precision can round the percentage upward, which
                # would otherwise require a positive balancing line.
                discount -= discount_step
                line.write({'discount': float(discount)})
                represented = self._line_raw_excluded(line)
            residual = source_target - represented
            source_evidence = self._product_source_evidence(
                item, original_unit, source_target, discount, signature,
            )
            plans.append({
                'line': line,
                'gid': 'product:%s:base' % item.get('id'),
                'source_base': represented,
                'source_tax': self._tax_source_total(item.get('taxLines') or []),
                'shopify_tax_events': len(item.get('taxLines') or []),
                'shipping_tax_events': 0,
                'tax_rate_total': rate_total,
                'signature': signature,
                'source_evidence': source_evidence,
            })
            if residual:
                if residual > 0:
                    raise JobHandlerError(
                        'financial_total_mismatch',
                        'A Shopify discount remainder was not representable as '
                        'a tax-preserving negative adjustment.',
                    )
                discount_product = discount_product or self._service_product(
                    'SHOPIFY-ORDER-DISCOUNT', 'Shopify Order Discount',
                    settings, store,
                )
                plans.append(self._create_residual_line(
                    Line, order, discount_product, taxes, residual,
                    rate_total, signature,
                    'product:%s:residual' % item.get('id'),
                    name='Shopify Order Discount',
                    source_evidence=dict(
                        source_evidence,
                        representation='tax_preserving_discount_residual',
                        residual_amount=format(residual, 'f'),
                    ),
                ))
            if item.get('isGiftCard'):
                gift_card_gids.append(item.get('id'))
        shipping_product = False
        for index, shipping in enumerate(payload.get('shipping_lines') or []):
            if not isinstance(shipping, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify shipping line had an invalid shape.',
                )
            if not shipping_product:
                shipping_product = self._service_product(
                    'SHOPIFY-SHIPPING', 'Shopify Shipping', settings, store,
                )
            gross_amount = self._money_decimal(
                shipping.get('discountedPriceSet')
            )
            source_target = gross_amount
            taxes, rate_total, signature = self._resolve_taxes(
                order, store, shipping.get('taxLines') or [],
                payload.get('taxesIncluded'), settings,
            )
            if payload.get('taxesIncluded'):
                source_target -= sum(
                    self._decimal_value(
                        ((tax_line.get('priceSet') or {}).get('shopMoney') or {}).get(
                            'amount'
                        )
                    )
                    for tax_line in shipping.get('taxLines') or []
                )
            shipping_key = shipping.get('id') or str(index)
            line = Line.create({
                'order_id': order.id,
                'product_id': shipping_product.id,
                'name': self._bounded_line_text(
                    shipping.get('title'), 'Shopify Shipping',
                ),
                'product_uom_qty': 1,
                'price_unit': float(gross_amount),
                'tax_ids': [(6, 0, taxes.ids)],
            })
            represented = self._line_raw_excluded(line)
            residual = source_target - represented
            plans.append({
                'line': line,
                'gid': 'shipping:%s:base' % shipping_key,
                'source_base': represented,
                'source_tax': self._tax_source_total(
                    shipping.get('taxLines') or []
                ),
                'shopify_tax_events': len(shipping.get('taxLines') or []),
                'shipping_tax_events': (
                    len(shipping.get('taxLines') or [])
                    if payload.get('taxesIncluded') else 0
                ),
                'tax_rate_total': rate_total,
                'signature': signature,
                'source_evidence': {
                    'representation': 'shipping_base',
                    'shipping_identity': shipping_key,
                    'source_gross_amount': format(gross_amount, 'f'),
                    'source_target_amount': format(source_target, 'f'),
                    'tax_signature': list(signature),
                },
            })
            if residual:
                adjustment_product = adjustment_product or self._service_product(
                    'SHOPIFY-ADJUSTMENT', 'Shopify Rounding Adjustment',
                    settings, store,
                )
                plans.append(self._create_residual_line(
                    Line, order, adjustment_product, taxes, residual,
                    rate_total, signature,
                    'shipping:%s:residual' % shipping_key,
                    source_evidence={
                        'representation': 'shipping_residual',
                        'shipping_identity': shipping_key,
                        'residual_amount': format(residual, 'f'),
                        'tax_signature': list(signature),
                    },
                ))
        if gift_card_gids and job:
            self.env['shopify.connector.job.log']._system_append(
                job,
                'note',
                'Gift-card line items were imported as ordinary sale lines; '
                'no gift-card accounting behavior was applied.',
                technical_detail=json.dumps({
                    'line_item_gids': sorted(gift_card_gids),
                }, sort_keys=True),
            )
        return plans

    @api.model
    def _create_residual_line(
        self, Line, order, product, taxes, residual, rate_total, signature, gid,
        name='Shopify attributable rounding adjustment',
        source_evidence=None,
    ):
        quantity = Decimal('-1') if residual < 0 else Decimal('1')
        target = abs(residual)
        seed = self._analytic_unit_for_excluded(order, taxes, target)
        line = Line.create({
            'order_id': order.id,
            'product_id': product.id,
            'name': name,
            'product_uom_qty': float(quantity),
            'price_unit': float(seed),
            'tax_ids': [(6, 0, taxes.ids)],
        })
        return {
            'line': line,
            'gid': gid,
            'source_base': residual,
            'source_tax': Decimal('0'),
            'shopify_tax_events': 0,
            'shipping_tax_events': 0,
            'tax_rate_total': rate_total,
            'signature': signature,
            'source_evidence': source_evidence or {},
        }

    @api.model
    def _analytic_unit_for_excluded(self, order, taxes, target):
        # EFFECTIVE posture, for the same reason as the two eligibility
        # authorities: an included tax on a company whose default is
        # `tax_included` carries no override, and reading the override would
        # skip this conversion and seed the line from a tax-inclusive figure as
        # though it were exclusive. Left uncorrected, admitting such a tax
        # through the corrected dialog would have produced wrong order totals.
        if not taxes or not all(tax_posture_included(tax) for tax in taxes):
            return target
        result = taxes._get_tax_details(
            price_unit=float(target),
            quantity=1,
            precision_rounding=order.currency_id.rounding,
            rounding_method=order.company_id.tax_calculation_rounding_method,
            special_mode='total_excluded',
        )
        return Decimal(str(result['total_included']))

    @api.model
    def _raw_excluded_for_values(
        self, order, product, taxes, price_unit, quantity, discount=Decimal('0'),
    ):
        result = taxes._get_tax_details(
            price_unit=float(price_unit) * (1 - float(discount) / 100),
            quantity=float(quantity),
            precision_rounding=order.currency_id.rounding,
            rounding_method=order.company_id.tax_calculation_rounding_method,
            product=product,
            product_uom=product.uom_id,
        ) if taxes else {
            'total_excluded': float(price_unit) * float(quantity)
            * (1 - float(discount) / 100),
        }
        return Decimal(str(result['total_excluded']))

    @api.model
    def _line_raw_excluded(self, line):
        base_line = line._prepare_base_line_for_taxes_computation()
        self.env['account.tax']._add_tax_details_in_base_line(
            base_line, line.order_id.company_id,
        )
        return Decimal(str(
            base_line['tax_details']['raw_total_excluded_currency']
        ))

    @api.model
    def _tax_source_total(self, tax_lines):
        try:
            if any(not isinstance(evidence, dict) for evidence in tax_lines):
                raise TypeError('invalid tax-line shape')
            return sum((
                self._decimal_value(
                    ((evidence.get('priceSet') or {}).get('shopMoney') or {}).get(
                        'amount'
                    )
                ) for evidence in tax_lines
            ), Decimal('0'))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify tax line omitted a finite money amount.',
            ) from exc

    @api.model
    def _resolve_product(self, store, item, settings):
        variant_gid = (item.get('variant') or {}).get('id')
        if variant_gid:
            binding = self.env[
                'shopify.connector.product.variant.binding'
            ].search([
                ('store_id', '=', store.id),
                ('shopify_gid', '=', variant_gid),
                ('status', 'in', ('active', 'manually_overridden')),
            ], limit=1)
            if not binding:
                raise JobHandlerError(
                    'mapping_missing',
                    'A Shopify product variant has no active Odoo binding.',
                    json.dumps({'variant_gid': variant_gid}),
                )
            product_gid = (item.get('product') or {}).get('id')
            template_binding = binding.product_template_binding_id
            if (
                not product_gid
                or template_binding.shopify_gid != product_gid
                or template_binding.status
                not in ('active', 'manually_overridden')
            ):
                raise JobHandlerError(
                    'mapping_missing',
                    'The Shopify product/variant identity chain is incomplete.',
                    json.dumps({
                        'product_gid': product_gid,
                        'variant_gid': variant_gid,
                    }, sort_keys=True),
                )
            product = binding.product_variant_id
        else:
            sku = (item.get('sku') or '').strip()
            candidates = self.env['product.product'].search([
                ('default_code', '=', sku),
                '|', ('company_id', '=', False),
                ('company_id', '=', settings.order_company_id.id),
            ], limit=2) if sku else self.env['product.product'].browse()
            if len(candidates) > 1:
                raise JobHandlerError(
                    'ambiguous_match',
                    'A custom Shopify line SKU matches multiple Odoo products.',
                )
            product = candidates or self._service_product(
                'SHOPIFY-CUSTOM', 'Shopify Custom Item', settings, store,
            )
        if (
            product.company_id
            and product.company_id != settings.order_company_id
        ):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The resolved product belongs to another Odoo company.',
            )
        return product

    @api.model
    def _service_product(self, default_code, name, settings, store):
        # Task 012 requires these connector-owned products to remain
        # store-scoped even when stores share an Odoo company.  Wave 2 adds no
        # product field, so a bounded non-PII store-id suffix supplies the local
        # discriminator while preserving the accepted default code.
        store_name = '%s [Shopify store %d]' % (name, store.id)
        product = self.env['product.product'].search([
            ('default_code', '=', default_code),
            ('name', '=', store_name),
            '|', ('company_id', '=', False),
            ('company_id', '=', settings.order_company_id.id),
        ], limit=1)
        if product:
            if product.type != 'service':
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'A reserved Shopify connector product code is assigned '
                    'to a non-service product.',
                )
            return product
        return self.env['product.product'].create({
            'name': store_name,
            'default_code': default_code,
            'type': 'service',
            'company_id': settings.order_company_id.id,
        })

    @api.model
    def _line_name(self, item):
        parts = [item.get('title') or item.get('name') or 'Shopify item']
        if item.get('variantTitle'):
            parts.append(item['variantTitle'])
        return self._bounded_line_text(' - '.join(parts), 'Shopify item')

    @api.model
    def _bounded_line_text(self, value, fallback):
        return (value or fallback)[:ORDER_LINE_DESCRIPTION_MAX_LEN]

    @api.model
    def _product_source_evidence(
        self, item, original_unit, source_target, discount, signature,
    ):
        """Return the bounded, PII-free line-allocation audit evidence."""
        allocations = []
        for allocation in item.get('discountAllocations') or []:
            application = allocation.get('discountApplication') or {}
            amount = allocation.get('allocatedAmountSet')
            allocations.append({
                'shop_amount': self._money_amount(amount, 'shopMoney'),
                'presentment_amount': self._money_amount(
                    amount, 'presentmentMoney',
                ),
                'application_type': application.get('__typename'),
                'application_index': application.get('index'),
                'allocation_method': application.get('allocationMethod'),
                'target_type': application.get('targetType'),
                'target_selection': application.get('targetSelection'),
            })
        return {
            'representation': 'product_base',
            'source_line_gid': item.get('id'),
            'original_unit_amount': format(original_unit, 'f'),
            'original_total_amount': self._money_amount(
                item.get('originalTotalSet'), 'shopMoney',
            ),
            'discounted_unit_amount': self._money_amount(
                item.get('discountedUnitPriceSet'), 'shopMoney',
            ),
            'discounted_total_amount': self._money_amount(
                item.get('discountedTotalSet'), 'shopMoney',
            ),
            'source_target_amount': format(source_target, 'f'),
            'native_discount_percent': format(discount, 'f'),
            'discount_allocations': allocations,
            'tax_signature': list(signature),
        }

    @api.model
    def _resolve_taxes(
        self, order, store, tax_lines, price_included, settings,
    ):
        taxes = self.env['account.tax'].browse()
        rate_total = Decimal('0')
        fingerprints = []
        for evidence in tax_lines:
            if not isinstance(evidence, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'A Shopify tax line had an invalid shape.',
                )
            try:
                shop_tax_amount = self._money_side_decimal(
                    evidence.get('priceSet'), 'shopMoney',
                )
                presentment_node = (
                    (evidence.get('priceSet') or {}).get('presentmentMoney')
                )
                if presentment_node is not None:
                    presentment_tax_amount = self._money_side_decimal(
                        evidence.get('priceSet'), 'presentmentMoney',
                    )
                    if shop_tax_amount != presentment_tax_amount:
                        raise ValidationError(
                            'TaxLine priceSet disagrees across equal currencies.'
                        )
                rate_key = canonical_tax_rate(
                    evidence.get('rate'), evidence.get('ratePercentage'),
                )
                fingerprint = build_tax_fingerprint(
                    evidence.get('rate'), evidence.get('ratePercentage'),
                    evidence.get('title'), evidence.get('source'),
                    evidence.get('channelLiable'), price_included,
                )
            except (JobHandlerError, ValidationError) as exc:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify tax evidence had inconsistent rate or money units.',
                ) from exc
            mapping = self.env['shopify.connector.tax.mapping'].search([
                ('store_id', '=', store.id),
                ('shopify_tax_evidence_key', '=', fingerprint),
            ], limit=1)
            if not mapping:
                preview = {
                    'rate_percentage': rate_key,
                    'included': bool(price_included),
                    'title_preview': safe_tax_preview(
                        evidence.get('title'), TAX_TITLE_PREVIEW_MAX_LEN,
                    ),
                    'source_preview': safe_tax_preview(
                        evidence.get('source'), TAX_SOURCE_PREVIEW_MAX_LEN,
                    ),
                    'fingerprint': fingerprint,
                    'suggested_account_tax_ids': self._tax_suggestions(
                        settings, rate_key, price_included,
                    ),
                    'suggestion_basis': 'rate_and_inclusion_only_non_binding',
                }
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'A Shopify tax fingerprint needs an explicit Odoo mapping.',
                    json.dumps(preview, sort_keys=True),
                )
            tax = mapping.account_tax_id
            self._validate_resolved_tax(tax, settings, price_included, rate_key)
            mapped = (
                order.fiscal_position_id.map_tax(
                    tax, product=False, partner=order.partner_id,
                ) if order.fiscal_position_id else tax
            )
            if len(mapped) != 1:
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'Fiscal-position tax mapping is ambiguous or empty.',
                )
            self._validate_resolved_tax(
                mapped, settings, price_included, rate_key,
            )
            if mapped & taxes:
                raise JobHandlerError(
                    'odoo_validation_configuration',
                    'Two distinct Shopify tax fingerprints resolve to the '
                    'same Odoo tax on one source line.',
                )
            taxes |= mapped
            rate_total += Decimal(rate_key)
            fingerprints.append(fingerprint)
        return taxes, rate_total, tuple(sorted(fingerprints))

    @api.model
    def _tax_suggestions(self, settings, rate_key, price_included):
        # The SHARED eligibility rule, so the non-binding suggestions the
        # merchant sees on the blocked job are the same set the decision dialog
        # will offer and the mapping constraint will accept.
        candidates = self.env['account.tax'].search(
            eligible_sale_tax_domain(
                settings.order_company_id, price_included,
                float(Decimal(rate_key)),
            ),
            order='id', limit=20,
        )
        return candidates.ids

    @api.model
    def _validate_resolved_tax(self, tax, settings, price_included, rate_key):
        # `tax_posture_included` reads Odoo's EFFECTIVE posture. Reading the
        # raw `price_include_override` here was the third copy of F4, and the
        # one that mattered most: a mapping created through the corrected
        # dialog would have been refused by this check on the very next import,
        # so the merchant would have mapped the tax and the order would still
        # not have moved.
        if (
            tax.company_id != settings.order_company_id
            or not tax.active
            or tax.type_tax_use != 'sale'
            or tax.amount_type != 'percent'
            or tax.include_base_amount
            or tax_posture_included(tax) != bool(price_included)
        ):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The mapped Odoo tax has an unsupported structure.',
                'unsupported_tax_structure',
            )
        if abs(Decimal(str(tax.amount)) - Decimal(rate_key)) > Decimal('0.000001'):
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The mapped Odoo tax rate no longer matches the fingerprint.',
            )

    @api.model
    def _solve_and_assert_totals(self, order, plans, payload):
        plans.sort(key=lambda value: value['gid'])
        precision = self.env['decimal.precision'].precision_get('Product Price')
        step = Decimal(1).scaleb(-precision)
        for plan in plans:
            seed = Decimal(str(plan['line'].price_unit)).quantize(
                step, rounding=ROUND_HALF_UP,
            )
            if seed < 0:
                raise JobHandlerError(
                    'financial_total_mismatch',
                    'A source price is outside the non-negative solver lattice.',
                )
            plan['seed'] = seed
            plan['line'].write({'price_unit': float(seed)})

        initial = self._financial_evidence(order, plans, payload)
        if initial['accepted']:
            return initial
        dependent = [
            plan for plan in plans if not initial['line_checks'][plan['line'].id]
        ]
        if len(dependent) > SOLVER_MAX_DEPENDENT_LINES:
            raise JobHandlerError(
                'financial_total_mismatch',
                'More than two lines require bounded price reconciliation.',
                self._financial_failure_detail(initial),
            )
        if not dependent:
            raise JobHandlerError(
                'financial_total_mismatch',
                'Odoo order totals do not reconcile with Shopify evidence.',
                self._financial_failure_detail(initial),
            )
        windows = []
        for plan in dependent:
            seed = plan['seed']
            candidates = [seed]
            for distance in range(1, SOLVER_K + 1):
                lower = seed - step * distance
                if lower >= 0:
                    candidates.append(lower)
                candidates.append(seed + step * distance)
            windows.append(candidates)
        vectors = list(itertools.product(*windows))
        vectors.sort(key=lambda vector: sum(
            abs(vector[index] - Decimal(str(dependent[index]['line'].price_unit)))
            for index in range(len(vector))
        ))
        if len(vectors) > SOLVER_MAX_CANDIDATE_VECTORS:
            raise JobHandlerError(
                'financial_total_mismatch',
                'The bounded whole-order solver budget was exceeded.',
            )
        seed_vector = tuple(plan['seed'] for plan in dependent)
        for vector in vectors:
            # The seed vector was already evaluated above to derive D. It is
            # vector 1 of the frozen C_max=25 budget and is never recomputed.
            if vector == seed_vector:
                continue
            try:
                with self.env.cr.savepoint():
                    for plan, candidate in zip(dependent, vector):
                        plan['line'].write({'price_unit': float(candidate)})
                    evidence = self._financial_evidence(order, plans, payload)
                    if not evidence['accepted']:
                        raise _RejectedCandidate()
                    return evidence
            except _RejectedCandidate:
                order.invalidate_recordset()
                order.order_line.invalidate_recordset()
        raise JobHandlerError(
            'financial_total_mismatch',
            'No bounded whole-order price vector reconciled the evidence.',
            self._financial_failure_detail(initial),
        )

    @api.model
    def _totals_match(self, order, plans, payload):
        return self._financial_evidence(order, plans, payload)['accepted']

    @api.model
    def _financial_evidence(self, order, plans, payload):
        self.env.flush_all()
        order._compute_amounts()
        if order._add_base_lines_for_early_payment_discount():
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The payment term introduced unsupported early-payment '
                'discount base lines.',
                'unsupported_early_payment_discount_payment_term',
            )

        AccountTax = self.env['account.tax']
        priced_lines = order._get_priced_lines()
        base_lines = [
            line._prepare_base_line_for_taxes_computation()
            for line in priced_lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
        summary = AccountTax._get_tax_totals_summary(
            base_lines=base_lines,
            currency=order.currency_id,
            company=order.company_id,
        )
        by_line_id = {
            line.id: base_line
            for line, base_line in zip(priced_lines, base_lines)
        }
        currency = order.currency_id
        rounding = Decimal(str(currency.rounding))
        expected_untaxed = sum(
            (plan['source_base'] for plan in plans), Decimal('0')
        )
        expected_tax = self._money_decimal(payload.get('totalTaxSet'))
        expected_total = self._money_decimal(payload.get('totalPriceSet'))
        actual_untaxed = Decimal(str(summary['base_amount_currency']))
        actual_tax = Decimal(str(summary['tax_amount_currency']))
        actual_total = Decimal(str(summary['total_amount_currency']))
        shipping_events = sum(
            plan['shipping_tax_events'] for plan in plans
        )
        line_tolerance = rounding * Decimal(
            len(plans) + shipping_events
        ) / Decimal('2')
        grouped = {}
        line_checks = {}
        line_evidence = {}
        for plan in plans:
            base_line = by_line_id[plan['line'].id]
            details = base_line['tax_details']
            line_base_raw = Decimal(str(
                details['raw_total_excluded_currency']
            ))
            line_checks[plan['line'].id] = (
                self._currency_quantize(currency, line_base_raw)
                == self._currency_quantize(currency, plan['source_base'])
            )
            line_evidence[plan['gid']] = dict(
                plan.get('source_evidence') or {},
                sale_order_line_id=plan['line'].id,
                chosen_price_unit=str(plan['line'].price_unit),
                chosen_quantity=str(plan['line'].product_uom_qty),
                chosen_discount=str(plan['line'].discount),
                source_base=format(plan['source_base'], 'f'),
                odoo_raw_base=format(line_base_raw, 'f'),
                line_base_check=bool(line_checks[plan['line'].id]),
            )
            key = plan['signature']
            bucket = grouped.setdefault(key, {
                'source_base': Decimal('0'),
                'odoo_raw_base': Decimal('0'),
                'source_tax': Decimal('0'),
                'odoo_tax': Decimal('0'),
                'rate_total': plan['tax_rate_total'],
                'shopify_events': 0,
                'odoo_tax_ids': set(),
                'odoo_events': 0,
            })
            bucket['source_base'] += plan['source_base']
            bucket['odoo_raw_base'] += line_base_raw
            bucket['source_tax'] += plan['source_tax']
            bucket['shopify_events'] += plan['shopify_tax_events']
            for tax_data in details['taxes_data']:
                bucket['odoo_tax'] += Decimal(str(
                    tax_data['tax_amount_currency']
                ))
                bucket['odoo_tax_ids'].add(tax_data['tax'].id)
                bucket['odoo_events'] += 1

        signature_checks = {}
        base_delta_total = Decimal('0')
        tax_tolerance = Decimal('0')
        global_rounding = (
            order.company_id.tax_calculation_rounding_method
            == 'round_globally'
        )
        for key, bucket in grouped.items():
            base_delta = abs(
                bucket['odoo_raw_base'] - bucket['source_base']
            )
            tax_delta = (
                base_delta * bucket['rate_total'] / Decimal('100')
            )
            o_events = (
                len(bucket['odoo_tax_ids'])
                if global_rounding else bucket['odoo_events']
            )
            signature_tax_tolerance = tax_delta + rounding * Decimal(
                bucket['shopify_events'] + o_events
            ) / Decimal('2')
            base_ok = (
                self._currency_quantize(currency, bucket['source_base'])
                == self._currency_quantize(currency, bucket['odoo_raw_base'])
            )
            tax_ok = (
                abs(bucket['odoo_tax'] - bucket['source_tax'])
                <= signature_tax_tolerance
            )
            signature_checks['|'.join(key) if key else 'untaxed'] = {
                'base_ok': base_ok,
                'tax_ok': tax_ok,
                'source_base': format(bucket['source_base'], 'f'),
                'odoo_raw_base': format(bucket['odoo_raw_base'], 'f'),
                'source_tax': format(bucket['source_tax'], 'f'),
                'odoo_tax': format(bucket['odoo_tax'], 'f'),
                'base_delta': format(base_delta, 'f'),
                'tax_tolerance': format(signature_tax_tolerance, 'f'),
            }
            base_delta_total += tax_delta
            tax_tolerance += signature_tax_tolerance

        total_tolerance = line_tolerance + tax_tolerance
        ledger_ok = (
            abs(expected_untaxed + expected_tax - expected_total)
            <= total_tolerance
        )
        accepted = (
            all(line_checks.values())
            and all(
                check['base_ok'] and check['tax_ok']
                for check in signature_checks.values()
            )
            and abs(actual_untaxed - expected_untaxed) <= line_tolerance
            and abs(actual_tax - expected_tax) <= tax_tolerance
            and abs(actual_total - expected_total) <= total_tolerance
            and ledger_ok
        )
        return {
            'accepted': accepted,
            'line_checks': line_checks,
            'line_evidence': line_evidence,
            'signature_checks': signature_checks,
            'expected_untaxed': format(expected_untaxed, 'f'),
            'actual_untaxed': format(actual_untaxed, 'f'),
            'expected_tax': format(expected_tax, 'f'),
            'actual_tax': format(actual_tax, 'f'),
            'expected_total': format(expected_total, 'f'),
            'actual_total': format(actual_total, 'f'),
            'line_tolerance': format(line_tolerance, 'f'),
            'tax_delta_total': format(base_delta_total, 'f'),
            'tax_tolerance': format(tax_tolerance, 'f'),
            'total_tolerance': format(total_tolerance, 'f'),
            'ledger_ok': ledger_ok,
        }

    @api.model
    def _currency_quantize(self, currency, amount):
        return Decimal(str(currency.round(float(amount))))

    @api.model
    def _financial_failure_detail(self, evidence):
        safe = dict(evidence)
        safe.pop('line_checks', None)
        return json.dumps(safe, sort_keys=True)

    @api.model
    def _classify_manual_gateway(self, payload):
        raw_transactions = payload.get('transactions')
        raw_names = payload.get('paymentGatewayNames')
        transactions_well_formed = (
            isinstance(raw_transactions, list)
            and all(
                isinstance(item, dict)
                and isinstance(item.get('id'), str)
                and isinstance(item.get('gateway'), str)
                and isinstance(item.get('kind'), str)
                and isinstance(item.get('status'), str)
                and isinstance(item.get('manualPaymentGateway'), bool)
                and isinstance(item.get('amountSet'), dict)
                for item in raw_transactions
            )
        )
        malformed = (
            not isinstance(raw_transactions, list)
            or not isinstance(raw_names, list)
            or not transactions_well_formed
            or any(not isinstance(item, str) for item in raw_names)
        )
        transactions = (
            raw_transactions
            if transactions_well_formed
            else []
        )
        relevant = [
            transaction for transaction in transactions
            if (transaction.get('kind') or '').upper()
            in ('SALE', 'CAPTURE', 'AUTHORIZATION')
        ]
        active = [
            transaction for transaction in relevant
            if (transaction.get('status') or '').upper() in ('SUCCESS', 'PENDING')
        ]
        unclassifiable = [
            transaction for transaction in relevant
            if (transaction.get('status') or '').upper()
            not in ('SUCCESS', 'PENDING', 'FAILURE', 'ERROR')
        ]
        manual = [transaction for transaction in active if transaction.get(
            'manualPaymentGateway'
        )]
        non_manual = [transaction for transaction in active if not transaction.get(
            'manualPaymentGateway'
        )]
        gateways = {
            (transaction.get('gateway') or '').strip()
            for transaction in manual if (transaction.get('gateway') or '').strip()
        }
        order_gateways = {
            value.strip().casefold()
            for value in (raw_names or []) if isinstance(raw_names, list)
            if isinstance(value, str) and value.strip()
        }
        manual_gateway_keys = {value.casefold() for value in gateways}
        mixed_names = bool(
            len(order_gateways) > 1
            or (manual and order_gateways - manual_gateway_keys)
        )
        if malformed or unclassifiable or mixed_names:
            state = 'mixed'
            name = False
        elif not manual:
            state = 'not_manual'
            name = False
        elif len(gateways) == 1 and not non_manual and len(manual) == len(active):
            state = 'unambiguous'
            name = next(iter(gateways))
        else:
            state = 'mixed'
            name = False
        return {'state': state, 'name': name, 'transactions': transactions}

    @api.model
    def _confirmation_outcome(self, payload, settings, gateway):
        status = payload['displayFinancialStatus'].upper()
        if gateway['state'] == 'mixed':
            return {
                'confirm': False, 'binding_status': 'review',
                'approval_state': 'not_required', 'commercial_state': 'review',
                'is_cod': False,
            }
        if status == 'PARTIALLY_PAID':
            return {
                'confirm': False, 'binding_status': 'review',
                'approval_state': 'not_required', 'commercial_state': 'review',
                'is_cod': False,
            }
        approved = False
        if status == 'PAID':
            confirm = settings.order_confirmation_policy in (
                'paid_only', 'paid_or_authorized',
            )
        elif status == 'AUTHORIZED':
            confirm = settings.order_confirmation_policy == 'paid_or_authorized'
        elif status == 'PENDING':
            approved = (
                gateway['state'] == 'unambiguous'
                and gateway['name'].casefold()
                in settings._approved_manual_gateway_set()
            )
            if approved:
                if settings.manual_gateway_policy == 'confirm_auto':
                    confirm = True
                elif settings.manual_gateway_policy == 'quotation':
                    confirm = False
                else:
                    return {
                        'confirm': False, 'binding_status': 'active',
                        'approval_state': 'pending',
                        'commercial_state': 'quotation',
                        'is_cod': True,
                    }
            elif settings.order_confirmation_policy == 'quotations_only':
                confirm = False
            else:
                raise OrderPendingWait(settings.pending_wait_expiry)
        else:
            confirm = False
        return {
            'confirm': confirm,
            'binding_status': 'active',
            'approval_state': 'not_required',
            'commercial_state': 'confirmed' if confirm else 'quotation',
            'is_cod': bool(status == 'PENDING' and approved),
        }

    @api.model
    def _binding_snapshot_vals(
        self, payload, resolution, gateway, confirmation,
    ):
        total = self._money_amount(payload.get('totalPriceSet'), 'shopMoney')
        presentment_total = self._money_amount(
            payload.get('totalPriceSet'), 'presentmentMoney',
        )
        collected = self._manual_collected_amount(gateway['transactions'])
        collection_state = 'nothing_collected'
        if collected > 0:
            collection_state = (
                'fully_collected'
                if collected >= self._decimal_value(total)
                else 'partially_collected'
            )
        return {
            'status': confirmation['binding_status'],
            'shopify_order_name': payload.get('name') or False,
            'shopify_legacy_resource_id': payload.get('legacyResourceId') or False,
            'shopify_processed_at': self._to_odoo_datetime(payload.get('processedAt')),
            'shopify_updated_at_snapshot': self._strict_updated_at(
                payload.get('updatedAt'),
            ),
            'shopify_created_at': self._to_odoo_datetime(payload.get('createdAt')),
            'shopify_currency_code': payload.get('currencyCode'),
            'shopify_presentment_currency_code': payload.get(
                'presentmentCurrencyCode'
            ),
            'shopify_taxes_included': bool(payload.get('taxesIncluded')),
            'shopify_financial_status_snapshot': payload.get(
                'displayFinancialStatus'
            ),
            'shopify_fulfillment_status_snapshot': payload.get(
                'displayFulfillmentStatus'
            ),
            'shopify_cancelled_at': self._to_odoo_datetime(payload.get('cancelledAt')),
            'shopify_cancel_reason': payload.get('cancelReason') or False,
            'shopify_order_total_amount': total,
            'shopify_order_total_presentment': presentment_total,
            'shopify_subtotal_amount': self._money_amount(
                payload.get('subtotalPriceSet'), 'shopMoney',
            ),
            'shopify_total_tax_amount': self._money_amount(
                payload.get('totalTaxSet'), 'shopMoney',
            ),
            'shopify_total_discounts_amount': self._money_amount(
                payload.get('totalDiscountsSet'), 'shopMoney',
            ),
            'shopify_total_shipping_amount': self._money_amount(
                payload.get('totalShippingPriceSet'), 'shopMoney',
            ),
            'shopify_total_tip_amount': self._money_amount(
                payload.get('totalTipReceivedSet'), 'shopMoney',
            ),
            'customer_resolution': resolution,
            'shopify_last_imported_at': fields.Datetime.now(),
            'shopify_last_evidence_refresh_at': fields.Datetime.now(),
            'financial_status_changed_at': fields.Datetime.now(),
            'financial_status_trigger_source': 'initial_import',
            'manual_gateway_name': gateway['name'] or False,
            'manual_gateway_evidence_state': gateway['state'],
            'manual_gateway_approval_state': confirmation['approval_state'],
            'is_cod': confirmation['is_cod'],
            'cod_commercial_state': confirmation['commercial_state'],
            'cod_fulfillment_state': 'not_dispatched',
            'cod_collection_state': collection_state,
            'cod_order_value_amount': total,
            'cod_fulfilled_value_amount': '0',
            'cod_collected_value_amount': format(collected, 'f'),
            'cod_refunded_value_amount': '0',
            'cod_cancelled_value_amount': '0',
        }

    @api.model
    def _refresh_existing(self, binding, payload, settings, job):
        self._validate_refresh_evidence(payload)
        # Scheduled scans and webhook-triggered reads can complete out of
        # order.  Serialize the final snapshot comparison with a database row
        # lock so an older Shopify read can never overwrite a newer one.  The
        # non-blocking ORM lock is intentional: a genuine race is classified
        # for the durable job retry path instead of waiting while a sibling
        # importer holds the binding transaction.
        binding = binding.sudo().try_lock_for_update()
        if not binding:
            raise JobHandlerError(
                'concurrency_race_conflict',
                'The Shopify order binding is being refreshed by another '
                'importer; retry the durable order job.',
            )
        binding.invalidate_recordset()
        if not binding.exists():
            raise JobHandlerError(
                'concurrency_race_conflict',
                'The Shopify order binding was deleted while its refresh was '
                'being serialized; no snapshot update was claimed.',
            )
        refreshed_at = self._strict_updated_at(payload.get('updatedAt'))
        if (
            binding.shopify_updated_at_snapshot
            and refreshed_at
            and refreshed_at < binding.shopify_updated_at_snapshot
        ):
            if job:
                self.env['shopify.connector.job.log']._system_append(
                    job,
                    'note',
                    'Ignored stale Shopify order snapshot; no commercial or '
                    'binding evidence was overwritten.',
                    technical_detail=json.dumps({
                        'order_binding_id': binding.id,
                        'shopify_order_gid': binding.shopify_gid,
                        'incoming_updated_at': fields.Datetime.to_string(
                            refreshed_at,
                        ),
                        'stored_updated_at': fields.Datetime.to_string(
                            binding.shopify_updated_at_snapshot,
                        ),
                    }, sort_keys=True),
                )
            return binding
        if (
            job
            and job.job_source == 'webhook'
            and binding.shopify_updated_at_snapshot
            and refreshed_at == binding.shopify_updated_at_snapshot
        ):
            same_snapshot = bool(
                binding.shopify_financial_status_snapshot
                == payload.get('displayFinancialStatus')
                and binding.shopify_fulfillment_status_snapshot
                == payload.get('displayFulfillmentStatus')
                and binding.shopify_cancelled_at
                == self._to_odoo_datetime(payload.get('cancelledAt'))
                and (binding.shopify_cancel_reason or False)
                == (payload.get('cancelReason') or False)
                and self._binding_financial_evidence_matches(binding, payload)
            )
            if not same_snapshot:
                # Two changed webhook bodies can carry the same source second.
                # Refuse to overwrite committed evidence without an ordering
                # proof.  The delivery and blocked child remain durable, while
                # the overlapping scheduled scan/manual refresh can perform a
                # fresh read outside the webhook equal-timestamp ambiguity.
                raise JobHandlerError(
                    'ambiguous_match',
                    'Shopify returned changed order evidence at the same '
                    'updatedAt already stored on the binding. The webhook '
                    'refresh was held for manual review; run scheduled order '
                    'reconciliation to obtain a fresh ordering signal.',
                    json.dumps({
                        'order_binding_id': binding.id,
                        'shopify_order_gid': binding.shopify_gid,
                        'incoming_job_payload_hash': job.payload_hash,
                        'updated_at': fields.Datetime.to_string(refreshed_at),
                    }, sort_keys=True),
                )
            self.env['shopify.connector.job.log']._system_append(
                job,
                'note',
                'Equal-timestamp Shopify order evidence matched the stored '
                'snapshot exactly; treated as an idempotent no-op.',
                technical_detail=json.dumps({
                    'order_binding_id': binding.id,
                    'shopify_order_gid': binding.shopify_gid,
                    'updated_at': fields.Datetime.to_string(refreshed_at),
                }, sort_keys=True),
            )
            return binding
        previous = binding.shopify_financial_status_snapshot
        previous_fulfillment = binding.shopify_fulfillment_status_snapshot
        previous_cancelled = bool(binding.shopify_cancelled_at)
        gateway = self._classify_manual_gateway(payload)
        financial_evidence_matches = self._binding_financial_evidence_matches(
            binding, payload,
        )
        values = self._binding_snapshot_vals(
            payload,
            binding.customer_resolution,
            gateway,
            {
                'binding_status': binding.status,
                'approval_state': binding.manual_gateway_approval_state,
                'commercial_state': binding.cod_commercial_state or 'imported',
                'is_cod': binding.is_cod,
            },
        )
        values.pop('shopify_last_imported_at', None)
        values.pop('financial_status_changed_at', None)
        values['shopify_previous_financial_status_snapshot'] = previous or False
        current = payload.get('displayFinancialStatus')
        if previous != current:
            values.update({
                'financial_status_changed_at': fields.Datetime.now(),
                'financial_status_trigger_source': (
                    job.job_source if job else 'direct_refresh'
                ),
            })
        if gateway['state'] == 'mixed':
            values.update({
                'status': 'review',
                'cod_commercial_state': 'review',
            })
        if not financial_evidence_matches or not current:
            values.update({
                'status': 'review',
                'cod_commercial_state': 'review',
            })
        approved_at_evidence = binding.manual_gateway_approved_shopify_updated_at
        if binding.manual_gateway_approval_state == 'pending':
            cancellation_signal = bool(
                job
                and isinstance(job.payload_hash, str)
                and job.payload_hash.startswith(ORDER_CANCELLED_PAYLOAD_PREFIX)
            )
            eligible = (
                binding.sale_order_id.state == 'draft'
                and settings.manual_gateway_policy == 'require_approval'
                and gateway['state'] == 'unambiguous'
                and gateway['name'].casefold()
                in settings._approved_manual_gateway_set()
                and (payload.get('displayFinancialStatus') or '').upper()
                == 'PENDING'
                and not payload.get('cancelledAt')
                and financial_evidence_matches
            )
            approval_was_recorded = bool(binding.manual_gateway_approved_at)
            if (
                approval_was_recorded
                and eligible
                and refreshed_at == approved_at_evidence
                and not cancellation_signal
            ):
                binding.sale_order_id.action_confirm()
                values.update({
                    'manual_gateway_approval_state': 'approved',
                    'cod_commercial_state': 'confirmed',
                })
            elif not approval_was_recorded and current == 'PAID':
                # Fresh paid evidence makes a still-unapproved manual-gateway
                # intent unnecessary. The permanent binding is retained and
                # the ordinary store confirmation policy decides below.
                values.update({
                    'status': 'active',
                    'manual_gateway_approval_state': 'not_required',
                })
            elif approval_was_recorded or not eligible:
                values.update({
                    'status': 'review',
                    'manual_gateway_approval_state': 'superseded',
                    'cod_commercial_state': 'review',
                })

        transition_to_paid = (
            previous in ('PENDING', 'AUTHORIZED')
            and current == 'PAID'
            and binding.sale_order_id.state == 'draft'
            and settings.order_confirmation_policy in (
                'paid_only', 'paid_or_authorized',
            )
            and values.get(
                'manual_gateway_approval_state',
                binding.manual_gateway_approval_state,
            ) != 'pending'
            and values.get('status', binding.status) != 'review'
            and financial_evidence_matches
            and not payload.get('cancelledAt')
            and not (
                job
                and isinstance(job.payload_hash, str)
                and job.payload_hash.startswith(ORDER_CANCELLED_PAYLOAD_PREFIX)
            )
        )
        if transition_to_paid:
            binding.sale_order_id.action_confirm()
            values['cod_commercial_state'] = 'confirmed'
        binding.sudo().write(values)
        if job:
            diverged = bool(
                previous != current
                or previous_fulfillment
                != payload.get('displayFulfillmentStatus')
                or previous_cancelled != bool(payload.get('cancelledAt'))
                or not financial_evidence_matches
                or gateway['state'] == 'mixed'
            )
            self.env['shopify.connector.job.log']._system_append(
                job,
                'note',
                'Order evidence refreshed%s; existing commercial lines were '
                'left unchanged.' % (
                    ' and routed for review' if diverged else '',
                ),
                technical_detail=json.dumps({
                    'order_binding_id': binding.id,
                    'shopify_order_gid': binding.shopify_gid,
                    'previous_financial_status': previous,
                    'current_financial_status': current,
                    'financial_evidence_matches': financial_evidence_matches,
                    'mixed_gateway_evidence': gateway['state'] == 'mixed',
                }, sort_keys=True),
            )
        return binding

    @api.model
    def _binding_financial_evidence_matches(self, binding, payload):
        pairs = (
            ('shopify_order_total_amount', 'totalPriceSet', 'shopMoney'),
            (
                'shopify_order_total_presentment', 'totalPriceSet',
                'presentmentMoney',
            ),
            ('shopify_subtotal_amount', 'subtotalPriceSet', 'shopMoney'),
            ('shopify_total_tax_amount', 'totalTaxSet', 'shopMoney'),
            (
                'shopify_total_discounts_amount', 'totalDiscountsSet',
                'shopMoney',
            ),
            (
                'shopify_total_shipping_amount', 'totalShippingPriceSet',
                'shopMoney',
            ),
            ('shopify_total_tip_amount', 'totalTipReceivedSet', 'shopMoney'),
        )
        for binding_field, payload_field, side in pairs:
            stored = binding[binding_field]
            amount = self._money_amount(payload.get(payload_field), side)
            if stored is False and amount is False:
                continue
            try:
                if self._decimal_value(stored) != self._decimal_value(amount):
                    return False
            except (InvalidOperation, TypeError, ValueError):
                return False
        return bool(
            binding.shopify_currency_code == payload.get('currencyCode')
            and binding.shopify_presentment_currency_code
            == payload.get('presentmentCurrencyCode')
            and binding.shopify_taxes_included == payload.get('taxesIncluded')
            and self._money_equal(
                payload.get('totalPriceSet'),
                payload.get('currentTotalPriceSet'),
            )
            and self._money_equal(
                payload.get('totalTaxSet'),
                payload.get('currentTotalTaxSet'),
            )
            and self._money_equal(
                payload.get('totalShippingPriceSet'),
                payload.get('currentShippingPriceSet'),
            )
        )

    @api.model
    def _manual_collected_amount(self, transactions):
        total = Decimal('0')
        for transaction in transactions:
            if (
                transaction.get('manualPaymentGateway')
                and (transaction.get('status') or '').upper() == 'SUCCESS'
                and (transaction.get('kind') or '').upper() in ('SALE', 'CAPTURE')
            ):
                total += self._money_decimal(transaction.get('amountSet'))
        return total

    @api.model
    def _money_equal(self, left, right):
        return all(
            self._money_currency(left, side)
            == self._money_currency(right, side)
            and self._money_side_decimal(left, side)
            == self._money_side_decimal(right, side)
            for side in ('shopMoney', 'presentmentMoney')
        )

    @api.model
    def _money_is_zero(self, bag):
        if bag is None:
            return True
        return all(
            self._money_side_decimal(bag, side) == 0
            for side in ('shopMoney', 'presentmentMoney')
        )

    @api.model
    def _money_decimal(self, bag):
        amount = self._money_amount(bag, 'shopMoney')
        if amount is False:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A required Shopify money amount was missing.',
            )
        try:
            return self._decimal_value(amount)
        except (InvalidOperation, ValueError) as exc:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify money amount was not a finite decimal.',
            ) from exc

    @api.model
    def _decimal_value(self, value):
        result = Decimal(str(value))
        if not result.is_finite():
            raise InvalidOperation()
        return result

    @api.model
    def _money_amount(self, bag, side):
        if not isinstance(bag, dict):
            return False
        node = bag.get(side)
        if not isinstance(node, dict):
            return False
        return node.get('amount', False)

    @api.model
    def _money_side_decimal(self, bag, side):
        amount = self._money_amount(bag, side)
        if amount is False:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A required Shopify money amount was missing.',
            )
        try:
            return self._decimal_value(amount)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify money amount was not a finite decimal.',
            ) from exc

    @api.model
    def _money_currency(self, bag, side='shopMoney'):
        if not isinstance(bag, dict):
            return False
        node = bag.get(side)
        return node.get('currencyCode') if isinstance(node, dict) else False

    @api.model
    def _validate_money_bag_currency(self, bag, currency, field_name):
        try:
            valid = bool(bag) and all(
                self._money_currency(bag, side) == currency
                and self._decimal_value(self._money_amount(bag, side))
                == self._decimal_value(
                    self._money_amount(bag, 'shopMoney')
                )
                for side in ('shopMoney', 'presentmentMoney')
            )
        except (InvalidOperation, TypeError, ValueError):
            valid = False
        if not valid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify money bag omitted, changed, or disagreed on '
                'the order currency.',
                json.dumps({'field': field_name}, sort_keys=True),
            )

    @api.model
    def _validate_money_bag_shape(
        self, bag, shop_currency, presentment_currency, field_name,
    ):
        try:
            shop = self._money_side_decimal(bag, 'shopMoney')
            presentment = self._money_side_decimal(bag, 'presentmentMoney')
            valid = bool(bag) and (
                self._money_currency(bag, 'shopMoney') == shop_currency
                and self._money_currency(bag, 'presentmentMoney')
                == presentment_currency
                and (
                    shop_currency != presentment_currency
                    or shop == presentment
                )
            )
        except (InvalidOperation, TypeError, ValueError, JobHandlerError):
            valid = False
        if not valid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A Shopify money bag omitted, changed, or disagreed on '
                'its declared currency.',
                json.dumps({'field': field_name}, sort_keys=True),
            )

    @api.model
    def _safe_money_evidence(self, bag):
        return json.dumps(self._safe_money_dict(bag), sort_keys=True)

    @api.model
    def _safe_money_dict(self, bag):
        return {
            side: {
                'amount': self._money_amount(bag, side),
                'currency': self._money_currency(bag, side),
            }
            for side in ('shopMoney', 'presentmentMoney')
        }

    @api.model
    def _safe_evidence(self, payload, keys):
        return json.dumps({key: payload.get(key) for key in keys}, sort_keys=True)

    @api.model
    def _safe_gateway_evidence(self, payload):
        transactions = payload.get('transactions')
        transactions = transactions if isinstance(transactions, list) else []
        names = payload.get('paymentGatewayNames')
        names = names if isinstance(names, list) else []
        return json.dumps({
            'payment_gateway_names': [
                self._safe_log_text(value)
                for value in names
                if isinstance(value, str)
            ],
            'transactions': [{
                'gateway': self._safe_log_text(transaction.get('gateway')),
                'kind': self._safe_log_text(transaction.get('kind')),
                'manual_payment_gateway': bool(
                    transaction.get('manualPaymentGateway')
                ),
                'status': self._safe_log_text(transaction.get('status')),
            } for transaction in transactions if isinstance(transaction, dict)],
        }, sort_keys=True)

    @api.model
    def _safe_log_text(self, value):
        value = redact(value or '')
        value = _EMAIL_RE.sub('[redacted-email]', value)
        value = _PHONE_RE.sub('[redacted-phone]', value)
        return value[:160]

    @api.model
    def _redact_evidence(self, value):
        if not value:
            return value
        parsed = value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                return self._safe_log_text(value)

        def scrub(item, key=False):
            if key in REDACTION_EXTENSION:
                return '***'
            if isinstance(item, dict):
                return {
                    item_key: scrub(item_value, item_key)
                    for item_key, item_value in item.items()
                }
            if isinstance(item, list):
                return [scrub(entry) for entry in item]
            if isinstance(item, str):
                return self._safe_log_text(item)
            return item

        result = scrub(parsed)
        return json.dumps(result, sort_keys=True) if isinstance(value, str) else result

    @api.model
    def _to_odoo_datetime(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @api.model
    def _strict_updated_at(self, value):
        """Parse Shopify Order.updatedAt only when it is strict RFC3339.

        A timezone-less value is not orderable across workers or stores and
        therefore cannot participate in the binding's monotonic watermark.
        Other evidence timestamps retain the connector's existing tolerant
        parser because they do not fence snapshot replacement.
        """
        if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify Order.updatedAt must be a timezone-qualified RFC3339 '
                'timestamp; the order snapshot was not applied.',
            )
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify Order.updatedAt is not a valid RFC3339 timestamp; '
                'the order snapshot was not applied.',
                type(exc).__name__,
            ) from exc
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)


class ShopifyConnectorJobOrderExtension(models.Model):
    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[('order_import_sync', 'Order Import Sync')],
        ondelete={
            'order_import_sync': lambda recs: recs._reassign_to_historic_job_type(),
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type == 'order_import_sync':
            return 'sale_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


class ShopifyConnectorJobDispatchOrderExtension(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        handlers['order_import_sync'] = self._handle_order_import_sync
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies['order_import_sync'] = REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        return policies

    @api.model
    def _handle_order_import_sync(self, job):
        try:
            self.env['shopify.connector.order.importer'].import_order_sync(
                job.store_id, job.shopify_target_gid, job=job,
            )
        except OrderPolicySkip as exc:
            detail = json.dumps({
                'skip_reason': exc.skip_reason,
                'evidence': exc.technical_detail or False,
            }, sort_keys=True)
            job._transition_skipped(exc.message, technical_detail=detail)
        except OrderPendingWait as exc:
            now = fields.Datetime.now()
            started = job.started_at or now
            expires_at = started + timedelta(hours=exc.expiry_hours)
            if now >= expires_at:
                job._transition_skipped(
                    'Pending payment wait expired without eligible payment '
                    'evidence.',
                    technical_detail=json.dumps({
                        'skip_reason': 'payment_pending_expired',
                        'expiry_hours': exc.expiry_hours,
                    }, sort_keys=True),
                )
            else:
                job._transition_retry_waiting(
                    next_retry_at=min(
                        now + timedelta(minutes=PENDING_RECHECK_MINUTES),
                        expires_at,
                    ),
                    retry_count=job.retry_count,
                    error_class=False,
                    message=(
                        'Pending non-manual payment is waiting for fresh '
                        'Shopify evidence.'
                    ),
                    technical_detail=json.dumps({
                        'expiry_hours': exc.expiry_hours,
                    }, sort_keys=True),
                )
        except OrderFatalSchemaError as exc:
            job._transition_failed_final(
                error_class='data_shape_schema_mismatch',
                message=exc.message,
                technical_detail=exc.technical_detail,
            )

    @api.model
    def _invoke_handler(self, job):
        """Compatibility shim for the pre-terminal-respect core dispatcher.

        The accepted Task-012 packet permits a minimal terminal-state-respect
        seam. Core is forbidden in Wave 2, so this extension swallows only the
        precise illegal-success ValidationError raised after the order handler
        has already moved itself to skipped, retry_waiting, or failed_final.
        Every other core dispatch, recovery, locking, and replay-policy path
        remains untouched.
        """
        try:
            return super()._invoke_handler(job)
        except ValidationError as exc:
            if (
                job.job_type == 'order_import_sync'
                and job.state in ('skipped', 'retry_waiting', 'failed_final')
                and str(exc) == (
                    'Illegal Shopify job transition: %s -> succeeded.'
                    % job.state
                )
            ):
                return None
            raise
