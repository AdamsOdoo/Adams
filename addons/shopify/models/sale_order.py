import logging
import pprint
import re
from datetime import timedelta, datetime, timezone
from random import randint

from markupsafe import Markup
from odoo.addons.shopify.models.shopify_return import SHOPIFY_RETURN_STATUS_SEARCH_GROUP

from odoo import models, fields, tools, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import (GET_ORDERS_BY_IDS, GET_PRODUCT_VARIANT, GET_SPECIFIC_PRODUCT_DATA,
                                                        FETCH_FULFILLMENT, GET_TRANSACTION_BY_ORDER_ID, GET_ORDERS_BY_DATE,
                                                        GET_ORDER_LINE_AFTER_CURSOR, GET_FULFILLMENT_LINE_ITEMS_AFTER_CURSOR,
                                                        GET_SHIPPING_LINES_AFTER_CURSOR, GET_REFUND_LINE_ITEMS_AFTER_CURSOR,
                                                        GET_REFUND_SHIPPING_LINES_AFTER_CURSOR, GET_ORDER_ADJUSTMENTS_AFTER_CURSOR, MARK_ORDER_AS_PAID,
                                                        GET_REMAINING_ORDER_METAFIELD, GET_MARK_AS_PAID_AUTHORIZE_CAPTURE_PAYMENT, ORDER_RISK, GET_ORDER_RETURNS_WITH_LINES_BY_DATE,
                                                        GET_ORDER_RETURNS_AFTER_CURSOR,
                                                        GET_RETURN_LINE_ITEMS_AFTER_CURSOR,
                                                        GET_RETURN_REVERSE_FULFILLMENT_ORDERS_AFTER_CURSOR,
                                                        GET_RFO_LINE_ITEMS_AFTER_CURSOR)
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc, log_traceback_for_exception, extract_numeric_id
from odoo.addons.shopify.shopify.pyactiveresource.connection import ResourceNotFound

_logger = logging.getLogger("Teqstars:Shopify")

FINANCIAL_STATUS = [('PENDING', 'Pending'),
                    ('AUTHORIZED', 'Authorized'),
                    ('PARTIALLY_PAID', 'Partially Paid'),
                    ('PAID', 'Paid'),
                    ('PARTIALLY_REFUNDED', 'Partially Refunded'),
                    ('REFUNDED', 'Refunded'),
                    ('VOIDED', 'Voided')]

FULFILLMENT_STATUS = [('FULFILLED', 'Fulfilled'),
                      ('UNFULFILLED', 'Unfulfilled'),
                      ('PARTIALLY_FULFILLED', 'Partially Fulfilled'),
                      ('IN_PROGRESS', 'In Progress'),
                      ('SCHEDULED', 'Scheduled'),
                      ('ON_HOLD', 'On Hold'),
                      ('RESTOCKED', 'Restocked'),
                      ('REQUEST_DECLINED', 'Request Declined')]

PICKUP_STATUS = [('ready_to_pickup', 'Ready for pickup'), ('already_pickup', 'Already pickup')]

# Shopify FulfillmentOrder.status that means "Ready for Pickup" in the Shopify admin.
SHOPIFY_FO_STATUS_IN_PROGRESS = 'IN_PROGRESS'
# Shopify deliveryMethod.methodType for Click & Collect / local-pickup orders.
SHOPIFY_DELIVERY_METHOD_PICKUP = 'PICK_UP'

RESOURCE_CONFIG = {
    'root': [
        ('lineItems', GET_ORDER_LINE_AFTER_CURSOR, 'id'),
        ('shippingLines', GET_SHIPPING_LINES_AFTER_CURSOR, 'id'),
        ('metafields', GET_REMAINING_ORDER_METAFIELD, 'id'),
    ],
    'fulfillments': [
        ('fulfillmentLineItems', GET_FULFILLMENT_LINE_ITEMS_AFTER_CURSOR, 'id'),
    ],
    'refunds': [
        ('refundLineItems', GET_REFUND_LINE_ITEMS_AFTER_CURSOR, 'id'),
        ('refundShippingLines', GET_REFUND_SHIPPING_LINES_AFTER_CURSOR, 'id'),
        ('orderAdjustments', GET_ORDER_ADJUSTMENTS_AFTER_CURSOR, 'id'),
    ]
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('fraud_analysis_ids')
    def _check_fraud_orders(self):
        for order_id in self:
            if any(fraud_analysis_id['recommendation'] != 'accept' for fraud_analysis_id in order_id.fraud_analysis_ids):
                order_id.is_fraud_order = True
                order_id.shopify_fraud_analysis_status = "investigate"
            else:
                order_id.is_fraud_order = False
                order_id.shopify_fraud_analysis_status = "accept"

    @api.depends('invoice_ids.payment_state', 'mk_instance_id.mark_order_paid_from_odoo')
    def _compute_show_mark_as_paid_button(self):
        """
        Whether the "Mark Order as Paid" button should be visible for a Shopify order.
        """
        for order_id in self:
            show_mark_as_paid_button = False
            if order_id.should_mark_shopify_order_paid() and order_id.mk_instance_id.mark_order_paid_from_odoo:
                show_mark_as_paid_button = True
            order_id.show_mark_as_paid_button = show_mark_as_paid_button

    shopify_mk_id = fields.Char("Shopify Marketplace Identification", copy=False)
    fraud_analysis_ids = fields.One2many("shopify.fraud.analysis", "order_id", string="Fraud Analysis", copy=False,
                                         help="Displays only Medium and High risk assessments from Shopify’s fraud analysis. Low-risk assessments are excluded.")
    is_fraud_order = fields.Boolean('Fraud Order?', default=False, copy=False, compute='_check_fraud_orders', store=True)
    shopify_financial_status = fields.Selection(FINANCIAL_STATUS, "Shopify Financial Status", help="The status of payments associated with the order in marketplace.")
    fulfillment_status = fields.Selection(FULFILLMENT_STATUS, copy=False, help="The order's status in terms of fulfilled line items:\n\n"
                                                                               "Fulfilled: Every line item in the order has been fulfilled.\n"
                                                                               "Unfulfilled: None of the line items in the order have been fulfilled.\n"
                                                                               "Partial: At least one line item in the order has been fulfilled.\n"
                                                                               "Restocked: Every line item in the order has been restocked and the order canceled.")
    shopify_order_source_name = fields.Char("Order Source", copy=False, help="Know source of Order creation.")
    shopify_force_refund = fields.Boolean('Force Refund in Odoo?', default=False, copy=False)
    shopify_payment_gateway_id = fields.Many2one("shopify.payment.gateway.ts", "Shopify Payment Gateway", help="Payment gateway of Shopify Order.", copy=False)
    shopify_currency_conversion_rate = fields.Float("Shopify Currency Conversion Rate", copy=False)
    is_pickup = fields.Boolean('Pickup Order?', default=False, copy=False,
                               help="A delivery that a customer picks up at your retail store, curbside, or any location that you choose.")
    pickup_status = fields.Selection(selection=PICKUP_STATUS, string="Pickup Status", copy=False,
                                     help="Indicates the Shopify order's pickup progress whether it's ready to pick or has already been picked up.")

    shopify_fraud_analysis_status = fields.Selection([('accept', 'Accept'), ('investigate', 'Investigate')], "Fraud Suggestion",
                                                     help="Order risks show the results of fraud checks that have been completed on Shopify orders.", compute="_check_fraud_orders",
                                                     store=True)
    show_mark_as_paid_button = fields.Boolean(compute="_compute_show_mark_as_paid_button", store=True, copy=False)

    # Shopify Returns
    shopify_return_ids = fields.One2many('shopify.return.ts', 'sale_order_id', string="Shopify Returns",
                                         help="All returns recorded against this order in Shopify, in any status.")
    shopify_return_count = fields.Integer(compute='_compute_shopify_return_count')
    is_returned = fields.Boolean("Has Return?", compute='_compute_is_returned', store=True,
                                 help="Set when this order has at least one Shopify return that is not in a terminal status.")

    _check_unique_shopify_mk_id = models.Constraint("UNIQUE (shopify_mk_id, mk_instance_id)", "You cannot create multiple order with same Marketplace ID and Shopify Store.")

    @api.depends('shopify_return_ids', 'shopify_return_ids.status')
    def _compute_is_returned(self):
        for order in self:
            order.is_returned = bool(order.shopify_return_ids.filtered(lambda r: r.status not in ('DECLINED', 'CANCELED')))

    def _compute_shopify_return_count(self):
        for order in self:
            order.shopify_return_count = len(order.shopify_return_ids)

    def action_view_shopify_returns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shopify Returns'),
            'res_model': 'shopify.return.ts',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.shopify_return_ids.ids)],
            'context': {'default_sale_order_id': self.id, 'default_mk_instance_id': self.mk_instance_id.id},
        }

    def transform_shopify_order_webhook_response_to_graphql(self, webhook_response, mk_instance_id=False):
        """
        This method is used when receive a Shopify webhook event (e.g., orders/create, orders/updated) to Transforms a
        Shopify order webhook response into a dictionary that follows the structure of Shopify GraphQL
        API order response.
        Args:
            webhook_response (dict): Dictionary containing the Shopify order data received via webhook.
        Returns:
            graphql_order_dict (dict): A dictionary formatted similarly to Shopify GraphQL order response.
        """

        # Helper function to normalize text (e.g. "refund discrepancy" → "REFUND_DISCREPANCY")
        def transform_text(text):
            converted_text = re.sub(r'\W+', '_', text.strip()).upper()
            return converted_text

        # Helper to transform price_set data to GraphQL format
        def _transform_webhook_price_set_response(price_set_resource):
            return {
                "presentmentMoney": {"amount": str(abs(float(price_set_resource.get("presentment_money", {}).get("amount", "")))) or '0'},
                "shopMoney": {"amount": str(abs(float(price_set_resource.get("shop_money", {}).get("amount", "")))) or '0'}
            }

        # Helper to transform tax_lines data
        def _transform_webhook_tax_lines_response(tax_lines_response):
            graphql_tax_lines_response = []
            if not tax_lines_response:
                return graphql_tax_lines_response
            for tax_line in tax_lines_response:
                graphql_tax_lines_response.append({
                    "title": tax_line.get("title", ""),
                    "rate": tax_line.get("rate", 0.0),
                    "priceSet": _transform_webhook_price_set_response(tax_line.get("price_set", {}))
                })
            return graphql_tax_lines_response

        # Helper to transform discount allocations
        def _transform_webhook_discount_allocation_response(discount_allocations):
            graphql_discount_allocations = []
            if not discount_allocations:
                return graphql_discount_allocations
            for allocation in discount_allocations:
                graphql_discount_allocations.append({
                    "allocatedAmountSet": _transform_webhook_price_set_response(allocation.get("amount_set", {}))
                })
            return graphql_discount_allocations

        # Helper function used to transform a webhook address response to a GraphQL address.
        def _transform_webhook_address_response(address_response):
            if not address_response:
                return None
            return {
                "name": address_response.get("name", ""),
                "firstName": address_response.get("first_name", ""),
                "lastName": address_response.get("last_name", ""),
                "address1": address_response.get("address1", ""),
                "address2": address_response.get("address2", ""),
                "city": address_response.get("city", ""),
                "phone": address_response.get("phone", ""),
                "company": address_response.get("company", ""),
                "country": address_response.get("country", ""),
                "countryCodeV2": address_response.get("country_code", ""),
                "province": address_response.get("province", ""),
                "provinceCode": address_response.get("province_code", ""),
                "zip": address_response.get("zip", ""),
            }

        # Helper to used to convert webhook REST timestamp to UTC ISO format.(format accepted by graphql)
        def shopify_utc_iso_format(timestamp_str):
            if not timestamp_str:
                return None
            dt_object = datetime.fromisoformat(timestamp_str)
            return dt_object.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Map REST fulfillment statuses to GraphQL equivalents
        FULFILLMENT_STATUS_MAP = {
            'fulfilled': 'FULFILLED',
            'partial': 'PARTIALLY_FULFILLED',
            'unfulfilled': 'UNFULFILLED',
            'restocked': 'UNFULFILLED',  # Not in GraphQL
        }

        # Line Items
        line_item_nodes = []
        if webhook_response.get('line_items', []):
            for item in webhook_response['line_items']:
                duties = []
                if item.get('duties'):
                    for duty in item['duties']:
                        duties.append({
                            "id": duty.get('admin_graphql_api_id', ''),
                            "price": _transform_webhook_price_set_response(duty.get('price_set', {})),
                            "taxLines": _transform_webhook_tax_lines_response(duty.get('tax_lines', []))
                        })

                line_item_nodes.append({
                    "id": item.get("admin_graphql_api_id"),
                    "name": item.get("name", ""),
                    "title": item.get("title", ""),
                    "quantity": item.get("quantity", 0),
                    "sku": item.get("sku", ""),
                    "isGiftCard": item.get("gift_card", False),
                    "requiresShipping": item.get("requires_shipping", False),
                    "originalUnitPriceSet": _transform_webhook_price_set_response(item.get("price_set")),
                    "taxLines": _transform_webhook_tax_lines_response(item.get("tax_lines", [])),
                    "duties": duties,
                    "discountAllocations": _transform_webhook_discount_allocation_response(item.get("discount_allocations", [])),
                    "product": {"id": f"gid://shopify/Product/{item.get('product_id')}" if item.get('product_id') else None},
                    "variant": {
                        "id": f"gid://shopify/ProductVariant/{item.get('variant_id')}" if item.get('variant_id') else None,
                        "sku": item.get("sku", ""),
                        "barcode": ""  # Barcode is not available in webhook
                    }
                })

        # Fulfillment
        fulfillments = []
        if webhook_response.get('fulfillments'):
            for fulfillment in webhook_response.get('fulfillments'):
                tracking_info = []
                tracking_numbers = fulfillment.get('tracking_numbers', [])
                # tracking_urls = fulfillment.get('tracking_urls', [])
                tracking_company = fulfillment.get('tracking_company')

                for i in range(len(tracking_numbers)):
                    tracking_info.append({
                        "number": tracking_numbers[i],
                        # "url": tracking_urls[i] if i < len(tracking_urls) else None,
                        "company": tracking_company
                    })

                # Map fulfillment line items
                fulfillment_line_items_nodes = []
                if fulfillment.get('line_items'):
                    for f_item in fulfillment['line_items']:
                        fulfillment_line_items_nodes.append({
                            "quantity": f_item.get('quantity', 0),
                            "lineItem": {
                                "id": f_item.get('admin_graphql_api_id'),
                                "isGiftCard": f_item.get('gift_card', False)
                            }
                        })

                fulfillments.append({
                    "id": fulfillment.get("admin_graphql_api_id"),
                    "status": fulfillment.get("status", "") and fulfillment.get("status", "").upper(),
                    "trackingInfo": tracking_info,
                    "fulfillmentLineItems": {"nodes": fulfillment_line_items_nodes}
                })

        shipping_line_nodes = []
        if webhook_response.get('shipping_lines'):
            for line in webhook_response['shipping_lines']:
                shipping_line_nodes.append({
                    "id": f"gid://shopify/ShippingLine/{line.get('id')}" if line.get('id') else None,
                    "title": line.get('title'),
                    "originalPriceSet": _transform_webhook_price_set_response(line.get('price_set', {})),
                    "discountAllocations": _transform_webhook_discount_allocation_response(line.get('discount_allocations', [])),
                    "taxLines": _transform_webhook_tax_lines_response(line.get('tax_lines', []))
                })

        # Refunds
        refunds = []
        for refund in webhook_response.get("refunds", []):
            refundLineItems = [
                {
                    "id": f"gid://shopify/RefundLineItem/{refund_line.get('id')}" if refund_line.get("id") else None,
                    "quantity": refund_line.get("quantity"),
                    "lineItem": {
                        "id": refund_line.get("line_item").get("admin_graphql_api_id")
                    }
                }
                for refund_line in refund.get("refund_line_items")
            ]
            # Prepared refund shipping lines from adjustment (not directly get)
            refundShippingLines = []
            for adjustment in refund.get("order_adjustments", []):
                if adjustment.get('kind', "") == "shipping_refund":
                    refundShippingLines.append({
                        "taxAmountSet": _transform_webhook_price_set_response(adjustment.get("tax_amount_set", {})),
                        "subtotalAmountSet": _transform_webhook_price_set_response(adjustment.get("amount_set", {})),
                    })
            orderAdjustments = [
                {
                    "reason": transform_text(adjustment.get("reason", "")),
                    "id": f"gid://shopify/OrderAdjustment/{adjustment.get('id')}" if adjustment.get("id") else None,
                    "amountSet": _transform_webhook_price_set_response(adjustment.get("amount_set", {})),
                    "taxAmountSet": _transform_webhook_price_set_response(adjustment.get("tax_amount_set", {})),
                }
                for adjustment in refund.get("order_adjustments", []) if adjustment.get('kind', "") != "shipping_refund"  # Exclude shipping adjustment
            ]
            transactions = [
                {
                    "status": transaction.get("status", "") and transaction.get("status", "").upper(),
                    # Preparing the data using amount field.(due to not directly get).
                    "amountSet": {
                        "presentmentMoney": {
                            "amount": transaction.get("amount", '')
                        },
                        "shopMoney": {
                            "amount": transaction.get("amount", '')
                        }
                    }
                }
                for transaction in refund.get("transactions", [])
            ]
            refunds.append({
                "id": refund.get("admin_graphql_api_id", ""),
                "note": refund.get("note", ""),
                "createdAt": shopify_utc_iso_format(refund.get("created_at", "")),
                "refundLineItems": {"nodes": refundLineItems},
                "refundShippingLines": {"nodes": refundShippingLines},
                "orderAdjustments": {"nodes": orderAdjustments},
                "transactions": {"nodes": transactions},
            })

        # Customer
        customer_response = webhook_response.get('customer', {})
        transformed_customer = {
            "note": customer_response.get('note', ""),
            "tags": [tag.strip() for tag in customer_response.get('tags', '').split(',') if tag.strip()] or [],
            "defaultEmailAddress": {
                "emailAddress": webhook_response.get("email", "")
            },
            # Task: T7545 -  Updated for Shopify API 2026-07 and deprecated phone fields.
            "defaultPhoneNumber": {
                "phoneNumber": webhook_response.get("phone", "")
            },
            "firstName": customer_response.get('first_name', ""),
            "lastName": customer_response.get('last_name', ""),
            "defaultAddress": _transform_webhook_address_response(customer_response.get('default_address'))
        } if customer_response else None

        mk_instance_id.connection_to_shopify()
        # Transactions
        variable = {"orderId": webhook_response.get('admin_graphql_api_id')}
        response = mk_instance_id.execute_graphql_query(GET_TRANSACTION_BY_ORDER_ID, variable)
        transactions_list = response.get('data', {}).get('order', {}).get('transactions', []) if isinstance(response, dict) else {}

        # Assemble the final GraphQL-like structure
        graphql_order_dict = {
            "id": webhook_response.get("admin_graphql_api_id"),
            "name": webhook_response.get("name", ""),
            "note": webhook_response.get("note", ""),
            "processedAt": shopify_utc_iso_format(webhook_response.get("processed_at", "")),
            "cancelledAt": shopify_utc_iso_format(webhook_response.get("cancelled_at", "")),
            "sourceName": webhook_response.get("source_name", ""),
            "tags": [tag.strip() for tag in webhook_response.get("tags", "").split(',') if tag.strip()] or [],
            "cancelReason": webhook_response.get("cancel_reason", "") and webhook_response.get("cancel_reason", "").upper(),
            "displayFinancialStatus": webhook_response.get("financial_status", "") and webhook_response.get("financial_status", "").upper(),
            "displayFulfillmentStatus": FULFILLMENT_STATUS_MAP.get(webhook_response.get("fulfillment_status")) if webhook_response.get("fulfillment_status") else 'UNFULFILLED',
            "paymentGatewayNames": webhook_response.get("payment_gateway_names", []),
            "currencyCode": webhook_response.get("currency", ""),
            "presentmentCurrencyCode": webhook_response.get("presentment_currency"),
            "taxesIncluded": webhook_response.get("taxes_included"),
            "totalPriceSet": _transform_webhook_price_set_response(webhook_response.get("total_price_set")),
            "billingAddress": _transform_webhook_address_response(webhook_response.get("billing_address")),
            "shippingAddress": _transform_webhook_address_response(webhook_response.get("shipping_address")),
            "customer": transformed_customer,
            "taxLines": _transform_webhook_tax_lines_response(webhook_response.get("tax_lines", [])),
            "lineItems": {"nodes": line_item_nodes},
            "fulfillments": fulfillments,
            "shippingLines": {"nodes": shipping_line_nodes},
            "transactions": transactions_list,
            "refunds": refunds
        }
        return graphql_order_dict

    def _fetch_shopify_order_paginated_nodes(self, mk_instance_id, parent_id, graphql_query, initial_nodes_lst, result_key, page_info, first=250):
        """
        Fetches and returns all paginated nodes from a Shopify GraphQL endpoint.
        This helper function handles pagination by repeatedly calling the API until all nodes for a specific resource have been retrieved.

        Args:
            mk_instance_id (recordset): The marketplace instance to use for the API call.
            parent_id (str): The GID of the parent resource (e.g., an order or fulfillment).
            graphql_query (str): The GraphQL query to execute for fetching the data.
            result_key (str): The key in the GraphQL response that contains the paginated resource.
            first (int, optional): The number of items to fetch per page. Defaults to 250.

        Returns:
            list: A list containing all fetched nodes for the specified resource.
                  Returns an empty list if an error occurs or no data is found.
        """
        remaining_nodes_list, cursor = None, []

        variables = {"id": parent_id, "cursor": page_info.get('endCursor', False), "first": first}
        try:
            response = mk_instance_id.execute_graphql_query(graphql_query, variables)
            user_errors = response.get('errors', []) if isinstance(response, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

            data = response.get('data', {})

            # Smarter parent node detection: Instead of hardcoding 'node' or 'order',
            # we find the dictionary that contains our target 'result_key'.
            parent_node = data.get('node') or data.get('order')  # Keep common cases for speed
            if not parent_node or result_key not in parent_node:
                # Fallback to search for the parent in the data dictionary
                for value in data.values():
                    if isinstance(value, dict) and result_key in value:
                        parent_node = value
                        break

            if not parent_node:
                _logger.warning(f"GraphQL response for {result_key} with parent ID {parent_id} did not contain a valid parent node. Data: {data}")

            resource_data = parent_node.get(result_key, {})
            if resource_data:
                remaining_nodes_list = resource_data.get('nodes', {})

        except Exception as e:
            _logger.error(f"An error occurred while fetching paginated {result_key} for parent ID {parent_id}: {e}", exc_info=True)
            # Stop processing on error to avoid returning incomplete data
            return initial_nodes_lst
        return initial_nodes_lst + remaining_nodes_list

    def _process_paginated_resource(self, parent_dict, resource_key, parent_id, graphql_query, mk_instance_id):
        """
        Checks a resource within a dictionary for pagination and fetches all subsequent nodes if necessary, updating the dictionary in place.
        Args:
            parent_dict (dict): The dictionary containing the resource to check (e.g., shopify_order_dict).
            resource_key (str): The key of the potentially paginated resource (e.g., 'lineItems').
            parent_id (str): The GID of the parent object.
            graphql_query (str): The GraphQL query used to fetch more nodes.
            mk_instance_id (recordset): The marketplace instance.
        """
        initial_resource_data = parent_dict.get(resource_key) or {}

        # Ensure we are working with a dictionary
        if not isinstance(initial_resource_data, dict):
            return

        initial_nodes_list = initial_resource_data.get('nodes', [])
        # Check if the resource is a dictionary and has a pageInfo with hasNextPage == True
        page_info = initial_resource_data.get('pageInfo', {})
        if isinstance(initial_nodes_list, list) and page_info.get('hasNextPage', False):
            all_nodes = self._fetch_shopify_order_paginated_nodes(mk_instance_id, parent_id, graphql_query, initial_nodes_list, resource_key, page_info)
            if len(all_nodes) > len(initial_nodes_list):
                parent_dict[resource_key]['nodes'] = all_nodes

    def get_all_remaining_shopify_order_data(self, shopify_order_dict, mk_instance_id, only_resources=None):
        """
        T6293 - Fetches remaining order metafields while fetching Shopify order data by ID. Added logic to fetch only metafields when the order is fetched by ID, while other resources continue using the existing flow.
        Fetches all paginated data for a given Shopify order.
        This version is cleaner, using a dedicated helper for processing and is driven by the RESOURCE_CONFIG dictionary for maintainability.
        Args:
            shopify_order_dict (dict): The initial order dictionary from Shopify.
            mk_instance_id (recordset): Recordset of mk.instance model.
            only_resources (list[str]): When provided, only paginate the listed resource_keys (e.g. ['metafields']). Defaults to None which paginates every entry in RESOURCE_CONFIG.
        Returns:
            dict: The updated shopify_order_dict with all nodes fetched.
        """
        order_id = shopify_order_dict.get('id')
        if not order_id:
            return shopify_order_dict

        def _should_process(resource_key):
            return not only_resources or resource_key in only_resources

        # Top-level paginated resources
        for resource_key, graphql_query, _ in RESOURCE_CONFIG.get('root', []):
            if not _should_process(resource_key):
                continue
            self._process_paginated_resource(shopify_order_dict, resource_key, order_id, graphql_query, mk_instance_id)

        # Process nested paginated resources (e.g., refundLineItems within each refund)
        for parent_resource_key, nested_config in RESOURCE_CONFIG.items():
            if parent_resource_key == 'root':
                continue

            # Ensure the parent resource (e.g., 'refunds', 'fulfillments') exists and has 'nodes'
            parent_resource_nodes = shopify_order_dict.get(parent_resource_key, {})
            if not parent_resource_nodes:
                continue

            for parent_node_dict in parent_resource_nodes:
                parent_id = parent_node_dict.get('id')
                if not parent_id:
                    continue

                for resource_key, graphql_query, _ in nested_config:
                    if not _should_process(resource_key):
                        continue
                    self._process_paginated_resource(parent_node_dict, resource_key, parent_id, graphql_query, mk_instance_id)

        return shopify_order_dict

    def shopify_order_query_filter(self, from_date, to_date, mk_instance_id, shopify_fulfillment_status_ids):
        """
        Task: T6808 - Added this to Generates and returns the filter used in the GraphQL query to import multiple Shopify order.
            if instance in set import_order_after_date set so create_at fetch order  otherwise processed_at fetch the order.
        Args:
            from_date (datetime): From date to import listing from shopify to odoo.
            to_date (datetime): To date to import listing from shopify to odoo.
            mk_instance_id: Recordset of mk.instance
            shopify_fulfillment_status_ids (record): Indicates based on update date or created date.
        Returns:
            String (str): String states query filter.
        """
        filters = []
        # Set default to_date to current date if not provided
        to_date = to_date or fields.Datetime.now()

        if from_date:
            # Format datetime safely directly to Shopify's expected ISO 8601 UTC format
            iso_from = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            iso_to = to_date.strftime('%Y-%m-%dT%H:%M:%SZ')

            from_import_screen = self.env.context.get('from_import_screen', False)
            date_field = "processed_at" if from_import_screen else "updated_at"

            # Note: Space acts as an 'AND' operator in Shopify GraphQL search syntax
            filters.append(f"{date_field}:>='{iso_from}' {date_field}:<='{iso_to}'")
        if shopify_fulfillment_status_ids:
            if 'any' in shopify_fulfillment_status_ids.mapped('status'):
                return "".join(filters)
            status_conditions = [f"fulfillment_status:{status}" for status in shopify_fulfillment_status_ids.mapped('status')]

            # Combine them with OR and wrap in parentheses: "(fulfillment_status:unshipped OR fulfillment_status:shipped)"
            status_query = f"{' OR '.join(status_conditions)}"
            filters.append(status_query)
        return "".join(filters)

    def fetch_orders_from_shopify(self, from_date, to_date, mk_instance_id, shopify_fulfillment_status_ids):
        """
        Args:
            from_date (datetime): From date to import listing from shopify to odoo.
            to_date (datetime): To date to import listing from shopify to odoo.
            mk_instance_id (record): Recordset of mk.instance model.
            shopify_fulfillment_status_ids (record): Indicates based on update date or created date.
        Returns:
            shopify_order_list (list): A list of dictionaries containing Shopify order data.
        Raises:
            MarketplaceException: If the GraphQL query fails or any error occurs during the API request.
        """
        cursor = None
        shopify_order_list = []
        query_filter = self.shopify_order_query_filter(from_date, to_date, mk_instance_id, shopify_fulfillment_status_ids)  # e.g. 'updated_at:>=2025-07-11 updated_at:<=2025-08-05'

        while True:
            try:
                variables = {"ordersCursor": cursor, "queryFilter": query_filter}
                res = mk_instance_id.execute_graphql_query(GET_ORDERS_BY_DATE, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

                # Task: T7725 - Updated default orders value from dict to list for safe order response handling.
                order_list = res and res.get('data', {}) and res.get('data', {}).get('orders', [])
                if not order_list:
                    break

                # Exclude the 'pageInfo' dictionary from the order list, keeping only order entries.
                # Task: T7725 - Added defensive pagination handling for single-page Shopify responses.
                if isinstance(order_list, list) and order_list:
                    last_item = order_list[-1]
                    if isinstance(last_item, dict) and set(last_item.keys()) == {'pageInfo'}:
                        shopify_order_list.extend(order_list[:-1])
                        page_info = last_item.get('pageInfo', {})
                    else:
                        shopify_order_list.extend(order_list)
                        page_info = {}
                    if not page_info.get('hasNextPage', False):
                        break

                    cursor = page_info.get('endCursor', None)

            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify orders: {e}")

        return shopify_order_list

    def _raise_on_shopify_return_errors(self, response):
        """
        Task: T8437 - Raise when a returns GraphQL response carries top-level errors.
        Args:
            response (dict): The GraphQL response.
        Raises:
            MarketplaceException: If any top-level error is present.
        """
        user_errors = response.get('errors', []) if isinstance(response, dict) else []
        if user_errors and isinstance(user_errors, list):
            joined_errors = ", ".join(error.get('message', str(error)) for error in user_errors)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Returns: %(errors)s") % {'errors': joined_errors})

    def _paginate_shopify_return_line_items(self, mk_instance_id, return_node):
        """
        Task: T8437 - Fetch all line items for a return across multiple pages.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_node (dict): A Shopify Return node, updated in place.
        Returns:
            dict: Updated return node with complete line item list.
        """
        line_block = return_node.get('returnLineItems') or {}
        page_info = line_block.get('pageInfo') or {}
        if not page_info.get('hasNextPage'):
            return return_node

        line_nodes = list(line_block.get('nodes') or [])
        cursor = page_info.get('endCursor')
        while cursor:
            variables = {"id": return_node.get('id'), "cursor": cursor}
            response = mk_instance_id.execute_graphql_query(GET_RETURN_LINE_ITEMS_AFTER_CURSOR, variables)
            self._raise_on_shopify_return_errors(response)
            next_block = (((response or {}).get('data') or {}).get('return') or {}).get('returnLineItems') or {}
            line_nodes.extend(next_block.get('nodes') or [])
            next_page_info = next_block.get('pageInfo') or {}
            cursor = next_page_info.get('endCursor') if next_page_info.get('hasNextPage') else None

        return_node['returnLineItems'] = {'nodes': line_nodes, 'pageInfo': {'hasNextPage': False, 'endCursor': False}}
        return return_node

    def _paginate_shopify_rfo_line_items(self, mk_instance_id, rfo_node):
        """
        Task: T8437 - Fetch all line items for a Reverse Fulfillment Order across multiple pages. Ensures complete restock disposition data from Shopify.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            rfo_node (dict): A Shopify ReverseFulfillmentOrder node, updated in place.
        Returns:
            dict: Updated RFO node with complete line item list.
        """
        line_block = rfo_node.get('lineItems') or {}
        page_info = line_block.get('pageInfo') or {}
        if not page_info.get('hasNextPage'):
            return rfo_node

        line_nodes = list(line_block.get('nodes') or [])
        cursor = page_info.get('endCursor')
        while cursor:
            variables = {"id": rfo_node.get('id'), "cursor": cursor}
            response = mk_instance_id.execute_graphql_query(GET_RFO_LINE_ITEMS_AFTER_CURSOR, variables)
            self._raise_on_shopify_return_errors(response)
            next_block = (((response or {}).get('data') or {}).get('reverseFulfillmentOrder') or {}).get('lineItems') or {}
            line_nodes.extend(next_block.get('nodes') or [])
            next_page_info = next_block.get('pageInfo') or {}
            cursor = next_page_info.get('endCursor') if next_page_info.get('hasNextPage') else None

        rfo_node['lineItems'] = {'nodes': line_nodes, 'pageInfo': {'hasNextPage': False, 'endCursor': False}}
        return rfo_node

    def _paginate_shopify_return_reverse_fulfillment_orders(self, mk_instance_id, return_node):
        """
        Task: T8437 - Fetch all Reverse Fulfillment Orders and their line items for a return.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_node (dict): A Shopify Return node, updated in place.
        Returns:
            dict: Updated return node with complete reverseFulfillmentOrders block.
        """
        rfo_block = return_node.get('reverseFulfillmentOrders') or {}
        page_info = rfo_block.get('pageInfo') or {}
        rfo_nodes = list(rfo_block.get('nodes') or [])
        cursor = page_info.get('endCursor') if page_info.get('hasNextPage') else None

        while cursor:
            variables = {"id": return_node.get('id'), "cursor": cursor}
            response = mk_instance_id.execute_graphql_query(GET_RETURN_REVERSE_FULFILLMENT_ORDERS_AFTER_CURSOR, variables)
            self._raise_on_shopify_return_errors(response)
            next_block = (((response or {}).get('data') or {}).get('return') or {}).get('reverseFulfillmentOrders') or {}
            rfo_nodes.extend(next_block.get('nodes') or [])
            next_page_info = next_block.get('pageInfo') or {}
            cursor = next_page_info.get('endCursor') if next_page_info.get('hasNextPage') else None

        for rfo_node in rfo_nodes:
            self._paginate_shopify_rfo_line_items(mk_instance_id, rfo_node)

        return_node['reverseFulfillmentOrders'] = {'nodes': rfo_nodes, 'pageInfo': {'hasNextPage': False, 'endCursor': False}}
        return return_node

    def _paginate_shopify_order_returns(self, mk_instance_id, order_node):
        """
        Task: T8437 - Fetch all returns and their child line items for a Shopify order.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            order_node (dict): A Shopify Order node carrying a ``returns`` block, updated in place.
        Returns:
            dict: Updated order node with complete returns block.
        """
        returns_block = order_node.get('returns') or {}
        page_info = returns_block.get('pageInfo') or {}
        return_nodes = list(returns_block.get('nodes') or [])
        cursor = page_info.get('endCursor') if page_info.get('hasNextPage') else None

        while cursor:
            variables = {"id": order_node.get('id'), "cursor": cursor}
            response = mk_instance_id.execute_graphql_query(GET_ORDER_RETURNS_AFTER_CURSOR, variables)
            self._raise_on_shopify_return_errors(response)
            next_block = (((response or {}).get('data') or {}).get('order') or {}).get('returns') or {}
            return_nodes.extend(next_block.get('nodes') or [])
            next_page_info = next_block.get('pageInfo') or {}
            cursor = next_page_info.get('endCursor') if next_page_info.get('hasNextPage') else None

        for return_node in return_nodes:
            self._paginate_shopify_return_line_items(mk_instance_id, return_node)
            self._paginate_shopify_return_reverse_fulfillment_orders(mk_instance_id, return_node)

        order_node['returns'] = {'nodes': return_nodes, 'pageInfo': {'hasNextPage': False, 'endCursor': None}}
        return order_node

    def _fetch_shopify_order_returns(self, mk_instance_id, search_query):
        """
        Task: T8437 - Fetch all returns and child items for orders carrying a return.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            search_query (str): Shopify search filter scoped to orders with returns.
        Returns:
            dict: Order GID -> the order's complete ``returns`` block.
        Raises:
            MarketplaceException: On a top-level GraphQL error.
        """
        cursor, has_next, returns_by_order_gid = None, True, {}
        while has_next:
            variables = {"searchQuery": search_query, "afterCursor": cursor}
            response = mk_instance_id.execute_graphql_query(GET_ORDER_RETURNS_WITH_LINES_BY_DATE, variables)
            self._raise_on_shopify_return_errors(response)

            orders_block = ((response or {}).get('data', {}) or {}).get('orders', {}) or {}
            for order_node in orders_block.get('nodes', []) or []:
                if not (order_node.get('returns') or {}).get('nodes'):
                    continue
                try:
                    self._paginate_shopify_order_returns(mk_instance_id, order_node)
                except Exception as error:
                    log_traceback_for_exception()
                    _logger.warning(f"IMPORT RETURN: Could not complete returns pagination for order {order_node.get('id')}. ERROR: {error}")
                returns_by_order_gid[order_node.get('id')] = order_node.get('returns') or {}
            page_info = orders_block.get('pageInfo', {}) or {}
            has_next = bool(page_info.get('hasNextPage'))
            cursor = page_info.get('endCursor') if has_next else None
        return returns_by_order_gid

    def _merge_shopify_returns_into_order_list(self, shopify_order_list, mk_instance_id, from_date, to_date, shopify_fulfillment_status_ids, mk_log_id=False):
        """
        Task: T8437 - Merge return payloads into order lists before queue creation.
        Args:
            shopify_order_list (list): Order payloads fetched by fetch_orders_from_shopify.
            mk_instance_id (recordset): Recordset of mk.instance model.
            from_date (datetime): From date used by the order pass.
            to_date (datetime): To date used by the order pass.
            shopify_fulfillment_status_ids (recordset): Fulfillment statuses used by the order pass.
            mk_log_id (recordset): Recordset of mk.log model. Optional.
        Returns:
            bool: Always returns True.
        """
        if not shopify_order_list:
            return True
        try:
            order_filter = self.shopify_order_query_filter(from_date, to_date, mk_instance_id, shopify_fulfillment_status_ids)
            search_query = f"{SHOPIFY_RETURN_STATUS_SEARCH_GROUP} AND ({order_filter})" if order_filter else SHOPIFY_RETURN_STATUS_SEARCH_GROUP
            returns_by_order_gid = self._fetch_shopify_order_returns(mk_instance_id, search_query)
        except Exception as error:
            log_traceback_for_exception()
            log_message = _("IMPORT RETURN: Failed to fetch returns for the imported order window, orders are imported without them. ERROR: %s") % error
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message}]})
            return True

        if not returns_by_order_gid:
            return True
        for shopify_order in shopify_order_list:
            returns_block = returns_by_order_gid.get(shopify_order.get('id'))
            if returns_block:
                shopify_order['returns'] = returns_block
        return True

    def _map_variant_to_odoo(self, shopify_variant, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id=False):
        """
        Map the Shopify variant to an Odoo product variant.
        Args:
            shopify_variant: The Shopify variant dictionary.
            mk_instance_id: The Shopify marketplace instance object.
            order_number (str): The Shopify order number.
            mk_log_id: The log ID for marketplace logs.
            queue_line_id: The queue line ID for logging.
            order_mk_id: The Shopify order marketplace ID.
        Returns:
            bool: True if the mapping was successful, False otherwise.
        """
        mk_listing_obj = self.env['mk.listing']
        sku = shopify_variant.get('sku', '')
        barcode = shopify_variant.get('barcode', '')

        odoo_product_variant_id, listing_item_id = mk_listing_obj.get_odoo_product_variant_and_listing_item(mk_instance_id, str(extract_numeric_id(shopify_variant.get('id', ""))),
                                                                                                            barcode, sku)
        if not odoo_product_variant_id:
            log_message = _("IMPORT ORDER: Marketplace Item SKU %s Not found for Order %s (%s)") % (sku, order_number, order_mk_id)
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False

        return True

    def _create_or_update_shopify_product(self, product_tmpl_id, mk_instance_id):
        """
        Create or update the Shopify product in Odoo.
        Args:
            product_tmpl_id (int): The Shopify product template ID.
            mk_instance_id: The marketplace instance object.
        """
        variables = {"productId": f"gid://shopify/Product/{product_tmpl_id}"}
        product_res = mk_instance_id.execute_graphql_query(GET_SPECIFIC_PRODUCT_DATA, variables)
        user_errors = product_res.get('errors', []) if isinstance(product_res, dict) else {}
        if user_errors and isinstance(user_errors, list):
            err_messages = [e.get('message', str(e)) for e in user_errors]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

        shopify_product_dict = product_res.get('data', {}).get('product', {}) if isinstance(product_res, dict) else {}

        return self.env['mk.listing'].create_update_shopify_product(shopify_product_dict, mk_instance_id, update_product_price=True, is_update_existing_products=True)

    def _find_shopify_product(self, mk_instance_id, order_line, mk_log_id, queue_line_id):
        """
        Finds a product variant in Odoo. If not found, fetches from Shopify and creates/updates it.
        Returns: The Odoo product.product record or None if it cannot be found/created.
        """
        variant = order_line.get('variant', {})
        variant_id = variant and str(extract_numeric_id(variant.get('id')))
        sku = order_line.get('sku')

        # 1. Fetch from Shopify API
        try:
            variables = {"variantId": f"gid://shopify/ProductVariant/{variant_id}"}
            res = mk_instance_id.execute_graphql_query(GET_PRODUCT_VARIANT, variables)
            user_errors = res.get('errors', []) if isinstance(res, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

            # Add robust check for GraphQL errors
            if not res or res.get('errors') or not isinstance(res, dict):
                error_details = res.get('errors', 'Unknown GraphQL error')
                log_message = _("GraphQL error for Variant ID %s: %s") % (variant_id, error_details)
                self.env['mk.log'].create_update_log(mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

                return None
            shopify_variant_dict = res and res.get('data', {}) and res.get('data', {}).get('productVariant', {})
        except Exception:
            log_message = _("IMPORT ORDER: The Shopify product%s was not found in Shopify, associated with Variant ID: %s, and named: %s.") % (
                ' with SKU ' + sku if sku else '', variant_id, variant.get('title', ''))
            if sku:
                log_message += _(" You may create a product in Odoo with SKU %s and re-import this order.") % sku
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return {}

        if not shopify_variant_dict:
            return {}
        elif isinstance(shopify_variant_dict, dict):
            return shopify_variant_dict
        return {}

    def create_fraud_order_activity(self, mk_instance_id):
        """
        Task T6411 - Create an activity for risk order.
        Args:
            mk_instance_id: The marketplace instance record.
        Returns:
            Return bool after the creation an activity.
        """
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        user_id = mk_instance_id.salesperson_user_id.id or self.env.user.id

        self.activity_schedule(
            activity_type_id=activity_type_id,
            user_id=user_id,
            summary=f'Investigate {self.name} Order',
            note='Shopify has identified this order as potentially risky. Kindly review the information under the <b>Fraud Analysis</b> section in the <b>Marketplace Details</b> tab and take the appropriate action (Confirm or Cancel).')
        return True

    def _handle_missing_shopify_variant(self, variant_id, variant_sku, shopify_order_line_dict, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id=False):
        """
        Handle cases where the Shopify variant is missing from Odoo.
        Args:
            variant_id (int): The Shopify variant ID.
            variant_sku (str): The SKU of the variant.
            shopify_order_line_dict (dict): The Shopify order line data.
            mk_instance_id: The marketplace instance object.
            order_number (str): The Shopify order number.
            mk_log_id: The log ID for marketplace logs.
            queue_line_id: The queue line ID for logging.
            order_mk_id: The Shopify order marketplace ID.
        Returns:
            bool: True if the variant is successfully handled, False otherwise.
        """
        shopify_variant_dict = self._find_shopify_product(mk_instance_id, shopify_order_line_dict, mk_log_id, queue_line_id)
        if not shopify_variant_dict:
            return False

        product_tmpl_id = str(extract_numeric_id(shopify_order_line_dict.get('product', {}).get('id')))

        if product_tmpl_id:
            self._create_or_update_shopify_product(product_tmpl_id, mk_instance_id)

        return self._map_variant_to_odoo(shopify_variant_dict, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id)

    def _validate_shopify_order_line(self, shopify_order_line_dict, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id=False):
        """
        Validate a single Shopify order line to ensure it can be imported.
        Args:
            shopify_order_line_dict (dict): The Shopify order line data.
            mk_instance_id: The Shopify marketplace instance object.
            order_number (str): The Shopify order number.
            mk_log_id: The log ID for marketplace logs.
            queue_line_id: The queue line ID for logging.
            order_mk_id: The Shopify order marketplace ID.
        Returns:
            bool: True if the line is valid, False otherwise.
        """
        mk_listing_item_obj = self.env['mk.listing.item']
        mk_listing_obj = self.env['mk.listing']

        tip = True if (shopify_order_line_dict.get('name') or shopify_order_line_dict.get('title')) == 'Tip' else False
        if shopify_order_line_dict.get('isGiftCard') or tip:
            return True

        variant = shopify_order_line_dict.get('variant', {})
        variant_id = variant and extract_numeric_id(variant.get('id'))
        variant_sku = shopify_order_line_dict.get('sku', '')

        if variant_id:
            shopify_variant = mk_listing_item_obj.search([('mk_id', '=', variant_id), ('mk_instance_id', '=', mk_instance_id.id)])
            if shopify_variant or shopify_order_line_dict.get('isGiftCard', False):
                return True

            if mk_listing_obj._product_exists_in_odoo(variant_sku):
                return True

            # Attempt to find the variant in Shopify and handle product creation in Odoo if necessary
            return self._handle_missing_shopify_variant(variant_id, variant_sku, shopify_order_line_dict, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id)

        return True

    def check_validation_for_import_sale_orders(self, shopify_order_line_list, mk_instance_id, shopify_order_dict):
        """
        Validate the Shopify order and its lines to ensure they can be imported into Odoo.
        Args:
            shopify_order_line_list (list): List of Shopify order lines.
            mk_instance_id: The marketplace instance object.
            shopify_order_dict (dict): The full Shopify order data.
        Returns:
            tuple: A boolean indicating whether the order is importable, and the financial workflow configuration ID.
        """
        is_importable = True
        order_number = shopify_order_dict.get('name', '')
        order_mk_id = extract_numeric_id(shopify_order_dict.get('id', ''))
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)

        # Validate financial workflow for the order
        financial_workflow_config_id = self.validate_shopify_financial_workflow(shopify_order_dict, mk_instance_id)
        if not financial_workflow_config_id:
            return False, financial_workflow_config_id

        # Validate each order line
        for shopify_order_line_dict in shopify_order_line_list.get('nodes'):
            if not self._validate_shopify_order_line(shopify_order_line_dict, mk_instance_id, order_number, mk_log_id, queue_line_id, order_mk_id):
                is_importable = False
                break

        return is_importable, financial_workflow_config_id

    def validate_shopify_financial_workflow(self, shopify_order_dict, mk_instance_id):
        """
        Validates and retrieves the financial workflow for a Shopify order.
        Args:
            shopify_order_dict (dict): The dictionary representing the Shopify order.
            mk_instance_id (mk.instance): The marketplace instance record.
        Returns:
            shopify.financial.workflow.config recordset on success, or False on failure.
        """
        main_workflow_config_id, not_found = False, False
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        gateway_list = shopify_order_dict.get('paymentGatewayNames', ['Untitled']) or ['Untitled']
        main_gateway = [transaction.get('gateway') for transaction in shopify_order_dict.get('transactions', []) if
                        transaction.get('gateway', '') != 'gift_card' and transaction.get('kind', '') in ['CAPTURE', 'SALE'] and transaction.get('status') == 'SUCCESS']
        gateway_list = list(set(gateway_list + main_gateway))
        main_gateway = main_gateway and main_gateway[0] or gateway_list and gateway_list[0] or 'Untitled'

        for gateway in gateway_list:
            if not gateway and main_gateway:
                gateway = main_gateway

            shopify_payment_gateway_id = self.env['shopify.payment.gateway.ts'].search([('code', '=', gateway), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
            if not shopify_payment_gateway_id:
                shopify_payment_gateway_id = self.env['shopify.payment.gateway.ts'].sudo().create({'name': gateway, 'code': gateway, 'mk_instance_id': mk_instance_id.id})

            financial_workflow_config_id = self.env['shopify.financial.workflow.config'].search(
                ['|', ('financial_status', '=', shopify_order_dict.get('displayFinancialStatus')), ('financial_status', '=', 'ANY'), ('mk_instance_id', '=', mk_instance_id.id),
                 ('payment_gateway_id', '=', shopify_payment_gateway_id.id)], limit=1)

            marketplace_workflow_id = financial_workflow_config_id.order_workflow_id or False
            if gateway == main_gateway:
                main_workflow_config_id = financial_workflow_config_id
            if not marketplace_workflow_id:
                log_message = _(
                    "IMPORT ORDER: Financial Workflow Configuration not found for Shopify Order %s. Please configure the order workflow under the Workflow tab with Payment Gateway %s and Financial Status %s in Instance Configuration (Marketplaces > Configuration > Instance).") % (
                                  shopify_order_dict.get('name'), shopify_payment_gateway_id.name, shopify_order_dict.get('displayFinancialStatus'))
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={
                    'error': [
                        {'log_message': log_message, 'payment_gateway_id': shopify_payment_gateway_id.id, 'financial_status': shopify_order_dict.get('displayFinancialStatus'),
                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

                not_found = True
        return False if not_found else main_workflow_config_id

    def get_shopify_order_source(self, shopify_order_dict):
        """
        Retrieves a human-readable source name from a Shopify order dictionary
        """
        # A mapping of known source codes to their human-readable names.
        SOURCE_NAME_MAPPING = {
            'web': 'Online Store',
            'pos': 'POS',
            'shopify_draft_order': 'Draft Orders',
            'iphone': 'iPhone',
            'android': 'Android',
        }

        # Get the source name from the order. Default to 'web' if the key is missing, is None, or is an empty string.
        source_name = shopify_order_dict.get('sourceName') or 'web'

        return SOURCE_NAME_MAPPING.get(source_name, source_name)

    def create_shopify_sale_order(self, shopify_order_dict, mk_instance_id, customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id):
        self._set_payment_term_to_shopify_customer(customer_id, financial_workflow_config_id)
        shopify_source_name = self.get_shopify_order_source(shopify_order_dict)
        currency = self._get_shopify_order_currency(shopify_order_dict, mk_instance_id)
        pricelist_id = self._get_shopify_pricelist_id(mk_instance_id, currency)
        fiscal_position_id = self.env['account.fiscal.position'].with_company(mk_instance_id.company_id)._get_fiscal_position(customer_id, shipping_customer_id)
        sale_order_vals = self.prepare_sale_order_values(shopify_order_dict, customer_id, billing_customer_id, shipping_customer_id, mk_instance_id, pricelist_id,
                                                         fiscal_position_id,
                                                         shopify_source_name, financial_workflow_config_id)
        order_id = self.create(sale_order_vals)
        return order_id

    def _set_payment_term_to_shopify_customer(self, customer_id, financial_workflow_config_id):
        if financial_workflow_config_id:
            payment_term_id = financial_workflow_config_id.payment_term_id
            if payment_term_id:
                customer_id.sudo().with_company(financial_workflow_config_id.company_id or self.env.company).write({'property_payment_term_id': payment_term_id.id})

    def _get_shopify_order_currency(self, shopify_order_dict, mk_instance_id):
        if mk_instance_id.use_marketplace_currency:
            currency = shopify_order_dict.get('presentmentCurrencyCode')
        else:
            currency = shopify_order_dict.get('currencyCode')

        order_currency_id = self.env['res.currency'].with_context(active_test=False).search([('name', '=', currency)], limit=1)
        return order_currency_id

    def _get_shopify_pricelist_id(self, mk_instance_id, currency):
        product_pricelist_obj = self.env['product.pricelist']
        if mk_instance_id.pricelist_id and mk_instance_id.pricelist_id.currency_id != currency:
            if not currency.active:
                currency.sudo().active = True
            name = f'Shopify: {mk_instance_id.name}'
            pricelist_id = product_pricelist_obj.search(
                [('name', '=', name), ('currency_id', '=', currency.id), '|', ('company_id', '=', False), ('company_id', '=', mk_instance_id.company_id.id)])
            if not pricelist_id:
                pricelist_id = product_pricelist_obj.sudo().create({'name': name, 'currency_id': currency.id, 'company_id': mk_instance_id.company_id.id})
        else:
            pricelist_id = mk_instance_id.pricelist_id or False
        return pricelist_id

    def prepare_sale_order_values(self, shopify_order_dict, customer_id, billing_customer_id, shipping_customer_id, mk_instance_id, pricelist_id, fiscal_position_id,
                                  shopify_source_name, financial_workflow_config_id):
        processed_at = convert_shopify_datetime_to_utc(shopify_order_dict.get("processedAt", ""))
        sale_order_vals = {
            'state': 'draft',
            'partner_id': customer_id.id,
            'partner_invoice_id': billing_customer_id.ids[0] if billing_customer_id else customer_id.id,
            'partner_shipping_id': shipping_customer_id.ids[0] if shipping_customer_id else customer_id.id,
            'date_order': processed_at,
            'expected_date': processed_at,
            'company_id': mk_instance_id.company_id.id,
            'warehouse_id': mk_instance_id.warehouse_id.id,
            'fiscal_position_id': fiscal_position_id.id,
            'pricelist_id': pricelist_id and pricelist_id.id or False,
            'team_id': mk_instance_id.team_id.id or False,
        }

        if mk_instance_id.use_marketplace_sequence:
            order_prefix = mk_instance_id.order_prefix
            order_name = shopify_order_dict.get("name", '')
            if order_prefix:
                order_name = f"{order_prefix}{order_name}"
            sale_order_vals.update({'name': order_name})

        conversion_rate = 0.0
        if mk_instance_id.use_marketplace_currency and mk_instance_id.company_id.currency_id == mk_instance_id.pricelist_id.currency_id:
            total_price_set = shopify_order_dict.get('totalPriceSet', {}) or {}
            shop_amount = float(total_price_set.get('shopMoney', {}).get('amount', 1)) or 1
            conversion_rate = round(float(total_price_set.get('presentmentMoney', {}).get('amount', 1)) / shop_amount, 5)

        sale_order_vals = self.prepare_sales_order_vals_ts(sale_order_vals, mk_instance_id)
        marketplace_id = extract_numeric_id(shopify_order_dict.get('id'))

        sale_order_vals.update({'note': shopify_order_dict.get('note'),
                                'mk_id': marketplace_id,
                                'shopify_mk_id': marketplace_id,
                                'mk_order_number': shopify_order_dict.get('name'),
                                'shopify_financial_status': shopify_order_dict.get('displayFinancialStatus'),
                                'mk_instance_id': mk_instance_id.id,
                                'fulfillment_status': shopify_order_dict.get('displayFulfillmentStatus', 'UNFULFILLED') or 'UNFULFILLED',
                                'shopify_order_source_name': shopify_source_name or '',
                                'shopify_payment_gateway_id': financial_workflow_config_id.payment_gateway_id.id,
                                'shopify_currency_conversion_rate': conversion_rate,
                                'is_pickup': shopify_order_dict.get('is_pickup', False)})

        if mk_instance_id.salesperson_user_id:
            sale_order_vals['user_id'] = mk_instance_id.salesperson_user_id.id

        shopify_tag_vals = self.prepare_order_tag_vals(shopify_order_dict.get('tags'))
        if shopify_tag_vals and shopify_order_dict.get('tags'):
            sale_order_vals.update(shopify_tag_vals)

        if financial_workflow_config_id:
            marketplace_workflow_id = financial_workflow_config_id.order_workflow_id
            sale_order_vals.update({
                'picking_policy': marketplace_workflow_id.picking_policy,
                'payment_term_id': customer_id.property_payment_term_id and customer_id.property_payment_term_id.id or False,
                'order_workflow_id': marketplace_workflow_id.id})

        return sale_order_vals

    def prepare_order_tag_vals(self, shopify_tags):
        def _get_default_color():
            return randint(1, 11)

        crm_tag_obj, tag_list = self.env['crm.tag'], []
        for tag in shopify_tags:
            if len(tag) < 1:
                continue
            shopify_tag_id = crm_tag_obj.search([('name', '=', tag.strip())], limit=1)
            if not shopify_tag_id:
                shopify_tag_id = crm_tag_obj.create({'name': tag.strip(), 'color': _get_default_color()})
            tag_list.append(shopify_tag_id.id)
        return {'tag_ids': [(6, 0, tag_list)]}

    def get_odoo_shopify_location_from_id(self, shopify_location_id):
        shopify_location_obj = self.env['shopify.location.ts']
        location_id = shopify_location_obj.search(
            [('shopify_location_id', '=', shopify_location_id), ('mk_instance_id', '=', self.mk_instance_id.id)]) if shopify_location_id else False
        if not location_id:
            shopify_location_obj.import_location_from_shopify(self.mk_instance_id)
            location_id = shopify_location_obj.search(
                [('shopify_location_id', '=', shopify_location_id), ('mk_instance_id', '=', self.mk_instance_id.id)]) if shopify_location_id else False
        return location_id

    def get_refunded_quantity_for_line(self, shopify_order, line_item_id):
        """
        Task: T4859 - Check restock inventory while cancel order from Odoo
        This method return removed quantity count of product from order line which is removed due Edit order in shopify.
        Args:
            shopify_order (dictionary): Dictionary holds order data,
            line_item_id (int): shopify product id,
        Returns:
            refunded_qty (float): Returns removed quantity from shopify order.
        """
        refunded_qty = 0
        refunds = shopify_order.get('refunds', [])
        for refund in refunds:
            # Only consider refunds that have no transactions(these refunds are created due to Edit order process in shopify)
            if not refund.get('transactions', []):
                refund_line_items = refund.get('refundLineItems', [])
                for rli in refund_line_items.get('nodes', []):
                    # Get correct refund line item by id
                    rli_id = str(extract_numeric_id(rli.get('lineItem').get('id')))
                    if rli_id == line_item_id:
                        refunded_qty += rli.get('quantity', 0)
        return refunded_qty

    def create_sale_order_line_ts(self, shopify_order_line_dict, tax_ids, odoo_product_id, order_id, is_delivery=False, description='', is_discount=False):
        """
        Task T7767 - Map the Shopify fulfillment location, and store fulfillment split details when the product is fulfilled from multiple locations.
        Task: T4859 - Check restock inventory while cancel order from Odoo
        This method creates a sale order line in Odoo from the Shopify order line
        dictionary. It ensures that quantities removed due to order edits on Shopify
        are excluded when creating the order line in Odoo.
        Args:
            shopify_order_line_dict (dictionary): Dictionary holds order line data,
            tax_ids (recordset): Recordset of account.tax model,
            odoo_product_id (recordset):  Recordset of product.product model,
            order_id (recordset): Recordset of sale.order model,
            is_delivery (boolean): Specifies whether this line is shipping line or not,
            description (str): String that defines  description,
            is_discount (boolean):  Specifies whether this line is discount line or not,
        Returns:
            order_line (recordset): Recordset of sale.order.line model.
        """
        shopify_order_dict = self.env.context.get('shopify_order_dict', False)
        if not shopify_order_dict:
            return False

        original_quantity = shopify_order_line_dict.get('quantity', 1) or 1

        mk_id = str(extract_numeric_id(shopify_order_line_dict.get('id')))
        # Deduct refunded quantity with transactions
        refunded_qty = self.get_refunded_quantity_for_line(shopify_order_dict, mk_id)
        quantity = original_quantity - refunded_qty

        if quantity <= 0.0:
            return False

        sale_order_line_obj = self.env['sale.order.line']

        price = self._get_currency_based_on_instance_configuration(self.mk_instance_id,
                                                                   shopify_order_line_dict.get('originalUnitPriceSet', shopify_order_line_dict.get('originalPriceSet', {})))
        if not price:
            price = shopify_order_line_dict.get('price', 0.0)

        line_vals = {
            'name': description if description else (shopify_order_line_dict.get('name') or odoo_product_id.name),
            'product_id': odoo_product_id.id or False,
            'order_id': order_id.id,
            'company_id': order_id.company_id.id,
            'product_uom': odoo_product_id.uom_id and odoo_product_id.uom_id.id or False,
            'price_unit': price,
            'order_qty': quantity,
        }

        order_line_data = sale_order_line_obj.prepare_sale_order_line_ts(line_vals, self.mk_instance_id)

        discount_amount = sum(self._get_currency_based_on_instance_configuration(self.mk_instance_id, discount_allocation.get("allocatedAmountSet", {})) for discount_allocation in
                              shopify_order_line_dict.get("discountAllocations", []))

        discount_amount = (discount_amount / original_quantity) * quantity

        disc_per = (discount_amount / (float(price) * original_quantity)) * 100 if float(price) else 0.0

        order_line_data.update({
            'name': description if description else (shopify_order_line_dict.get('name') or odoo_product_id.name),
            'is_delivery': is_delivery,
            'is_discount': is_discount,
            'mk_id': mk_id,
            'discount': disc_per,
            'marketplace_discount_amount': discount_amount
        })

        if shopify_order_line_dict.get('location_id', False):
            shopify_location_id = self.get_odoo_shopify_location_from_id(shopify_order_line_dict.get('location_id'))
            if not shopify_location_id or (shopify_location_id and not shopify_location_id.order_warehouse_id or not shopify_location_id.location_id):
                raise MarketplaceException(_("Please set Warehouse and Location in the Shopify Location %(name)s. Marketplaces > Shopify > Configuration > Locations ") % {
                    'name': shopify_location_id.name})
            shopify_location_id and order_line_data.update({'shopify_location_id': shopify_location_id.id})

        if order_id and order_id.mk_instance_id.tax_system == 'according_to_marketplace':
            order_line_data.update({'tax_ids': [(6, 0, tax_ids.ids)]})

        elif order_id and order_id.mk_instance_id.tax_system == 'marketplace_with_fiscal_position':
            order_line_data.update({'tax_ids': self.fiscal_position_id.map_tax(tax_ids)})

        # Task : T6153 Remove the functionality that creates a separate discount order line.
        order_line = sale_order_line_obj.create(order_line_data)

        shopify_splits = shopify_order_line_dict.get('shopify_fulfillment_splits') or []
        if shopify_splits:
            order_line.shopify_fulfillment_locations = self._build_shopify_fulfillment_splits(shopify_order_line_dict)

        return order_line

    def get_shopify_delivery_method(self, carrier_name, mk_instance_id, country_id=False, country_code=''):
        """
        Task:T6806 - For the searching delivery Carrier add a filter of Country.
        When several carriers share the same Shopify code but differ by allowed countries,
        prefer the one that explicitly lists the destination country and fall back to the
        first match so existing behaviour is preserved.
        """
        carrier_obj = self.env['delivery.carrier']
        exact_name_domain = ['|', ('name', '=', carrier_name), ('shopify_code', '=', carrier_name)]
        country_domain = ['|', ('country_ids', '=', country_id), ('country_ids.code', '=', country_code)]

        carrier_id = carrier_obj.search(exact_name_domain + country_domain, limit=1)
        if not carrier_id:
            names_domain = ['|', ('name', 'ilike', carrier_name), ('shopify_code', 'ilike', carrier_name)]
            carrier_id = carrier_obj.search(names_domain + country_domain, limit=1)
        if not carrier_id:
            carrier_id = carrier_obj.search(['|', ('name', '=', carrier_name), ('shopify_code', '=', carrier_name), ('country_ids', '=', False)], limit=1)
        if not carrier_id:
            carrier_id = carrier_obj.sudo().create({'name': carrier_name, 'shopify_code': carrier_name, 'product_id': mk_instance_id.delivery_product_id.id})
        return carrier_id

    def _get_shopify_odoo_taxes(self, mk_instance_id, tax_lines, included=True):
        """
        Convert Shopify tax lines to Odoo taxes.

        Args:
            mk_instance_id (object): The instance of the MK (Marketplace).
            tax_lines (list): List of tax dictionaries from Shopify.
            included (bool): Whether the taxes are included in the price or not.
        Returns:
            list: List of Odoo tax IDs.
        """
        tax_line_list = []

        # Retrieve and split the special tax labels configured in the instance
        special_tax_label = mk_instance_id.special_tax_label
        special_tax_label_list = special_tax_label and special_tax_label.split(',') or []

        for tax_dict in tax_lines:
            title = tax_dict.get('title', '')
            price = self._get_currency_based_on_instance_configuration(self.mk_instance_id, tax_dict.get('priceSet', {}))

            # Check if the tax title matches any special tax labels
            is_special_tax = any(special_tax.strip() == title for special_tax in special_tax_label_list)

            # Only add non-special taxes with a positive price to the list
            if price > 0.0 and not is_special_tax:
                tax_line_list.append({
                    'rate': tax_dict.get('rate', 0.0) * 100,  # Convert rate to percentage
                    'title': title
                })

        # Retrieve Odoo tax IDs based on the tax line list
        tax_ids = self.get_odoo_tax(mk_instance_id, tax_line_list, included)

        return tax_ids

    def create_shopify_shipping_line(self, mk_instance_id, shopify_order_dict, order_id):
        for shopify_shipping_dict in shopify_order_dict.get('shippingLines', {}).get('nodes', []):
            if 'id' not in shopify_shipping_dict:
                continue

            tax_ids = False

            if mk_instance_id.tax_system != 'default':
                taxes_included = shopify_order_dict.get('taxesIncluded', False)
                tax_ids = self._get_shopify_odoo_taxes(mk_instance_id, shopify_shipping_dict.get('taxLines', []), taxes_included)
            carrier_name = shopify_shipping_dict.get('title', 'Shopify Delivery Method')
            # T6806 - Apply country-based filtering for delivery carriers, prioritizing matches by destination country when carrier codes are shared.
            country_id = order_id.partner_shipping_id.country_id.id if order_id else False
            country_code = shopify_order_dict.get('shippingAddress', {}) and shopify_order_dict.get('shippingAddress', {}).get('countryCodeV2', '') if shopify_order_dict else ''
            carrier_id = self.get_shopify_delivery_method(carrier_name, mk_instance_id, country_id, country_code)
            order_id.write({'carrier_id': carrier_id.id})
            shipping_product = carrier_id.product_id
            # Task : T6153 Remove the functionality that creates a separate discount order line.
            order_line = self.create_sale_order_line_ts(shopify_shipping_dict, tax_ids, shipping_product, order_id, is_delivery=True, description=carrier_name)
            return order_line

    def _process_shopify_duties_lines(self, duties, order_line, shopify_order_dict, mk_instance_id):
        duties_desc = f"Duties: {order_line.product_id.name}"
        taxes_included = shopify_order_dict.get('taxesIncluded', False)
        for duty in duties:
            tax_ids = self._get_shopify_odoo_taxes(mk_instance_id, duty.get('taxLines', []), taxes_included)
            amount = self._get_currency_based_on_instance_configuration(self.mk_instance_id, duty.get('price', {}))
            if amount > 0.0:
                self.create_sale_order_line_ts({'price': float(amount), 'id': duty.get('id'), 'quantity': 1}, tax_ids, mk_instance_id.duties_product_id, self,
                                               is_discount=False, description=duties_desc)
        return True

    def create_special_tax_shipping_line(self, mk_instance_id, shopify_order_dict, order_id):
        special_tax_label = mk_instance_id.special_tax_label
        if special_tax_label:
            for tax_label in special_tax_label.split(','):
                for tax_line in shopify_order_dict.get('taxLines', []):
                    if tax_line.get('title', '') == tax_label.strip():
                        price = self._get_currency_based_on_instance_configuration(self.mk_instance_id, tax_line.get('priceSet', {}))
                        if not price:
                            price = tax_line.get('price', 0.0)
                        discount_desc = tax_line.get('title', 'Untitled')
                        # T8286 - Tax[] parameter change to self.env['account.tax']
                        self.create_sale_order_line_ts({'price': float(price), 'quantity': 1}, self.env['account.tax'], mk_instance_id.delivery_product_id, order_id,
                                                       description=discount_desc)
        return True

    def _preload_default_shopify_products(self, mk_instance_id):
        """
        Preload frequently used products to avoid redundant lookups during the order processing.
        Args:
            mk_instance_id: Marketplace instance object
        Returns:
            tuple: Preloaded products (gift_card_product, tip_product, custom_product, custom_storable_product, discount_product)
        """
        gift_card_product = mk_instance_id.gift_card_product_id or self.env.ref('shopify.shopify_gift_card_product', False)
        tip_product = mk_instance_id.tip_product_id or self.env.ref('shopify.shopify_tip_product', False)
        custom_product = mk_instance_id.custom_product_id
        custom_storable_product = mk_instance_id.custom_storable_product_id
        discount_product = mk_instance_id.discount_product_id
        return gift_card_product, tip_product, custom_product, custom_storable_product, discount_product

    def _get_shopify_odoo_product(self, shopify_order_line_dict, shopify_product_variant_id, gift_card_product, tip_product):
        """
        Get the corresponding Odoo product for a Shopify order line.
        """
        variant_sku = shopify_order_line_dict.get('sku', '')
        gift_card = shopify_order_line_dict.get('isGiftCard', False)
        tip = 'tip' in shopify_order_line_dict

        odoo_product_id = None
        if gift_card:
            odoo_product_id = gift_card_product
        elif tip:
            odoo_product_id = tip_product
        elif shopify_product_variant_id:
            odoo_product_id = shopify_product_variant_id.product_id
        elif variant_sku:
            odoo_product_id = self.env['product.product'].search([('default_code', '=ilike', variant_sku)], limit=1)

        return odoo_product_id

    def _process_shopify_sale_order_line(self, mk_instance_id, shopify_order_line_dict, tax_ids, odoo_product_id, shopify_product_variant_id, order_id, shopify_order_dict):
        """
        Process and create sale order line in Odoo for the Shopify order.
        """
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        order_line = self.env['sale.order.line']

        variant = shopify_order_line_dict.get('variant')
        variant_id = variant and extract_numeric_id(shopify_order_line_dict.get('variant', {}).get('id'))

        if shopify_product_variant_id or odoo_product_id:
            order_line = self.create_sale_order_line_ts(shopify_order_line_dict, tax_ids, odoo_product_id, order_id)
        else:
            if not variant_id:
                if not mk_instance_id.custom_product_id or not mk_instance_id.custom_storable_product_id:
                    log_message = _(
                        "IMPORT ORDER: Shopify Custom Product not found for Shopify Order ID %s, Please set Product in Custom Product field in Order tab of Instance configuration.") % order_id.mk_id
                    self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                         mk_log_line_dict={
                                                             'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    return False
                custom_product_id = mk_instance_id.custom_storable_product_id if shopify_order_line_dict.get('requiresShipping', False) else mk_instance_id.custom_product_id
                order_line = self.create_sale_order_line_ts(shopify_order_line_dict, tax_ids, custom_product_id, order_id)

        # Task: T6153 - Remove the functionality that creates a separate discount order line.
        # Handle duties
        duties = shopify_order_line_dict.get('duties')
        if duties:
            self._process_shopify_duties_lines(duties, order_line, shopify_order_dict, mk_instance_id)

    def create_sale_order_line_shopify(self, mk_instance_id, shopify_order_dict, order_id):
        """
        Create sale order lines for a Shopify order.

        Args:
            mk_instance_id: Marketplace instance object (contains Shopify-specific configurations)
            shopify_order_dict: Dictionary containing Shopify order details
            order_id: ID of the Odoo order where lines need to be added

        Returns:
            bool: True if successful, False if any product is missing or cannot be processed

        The method processes line items from a Shopify order and creates corresponding sale order lines in Odoo.
        If a product is missing or not found, it logs an error and exits. It handles gift cards, tips, taxes, discounts,
        and custom products based on the Shopify order information and instance configuration.
        """
        shopify_order_line_list = shopify_order_dict.get('lineItems', [])
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)

        # Preload products for performance optimization
        gift_card_product, tip_product, custom_product, custom_storable_product, discount_product = self._preload_default_shopify_products(mk_instance_id)

        # Avoid redundant lookup for instance-level tax system and tax inclusion
        taxes_included = shopify_order_dict.get('taxesIncluded', False)
        tax_system_marketplace = mk_instance_id.tax_system != 'default'

        # Loop through each line item in the Shopify order
        for shopify_order_line_dict in shopify_order_line_list.get('nodes', []):
            if 'id' not in shopify_order_line_dict:
                continue

            variant = shopify_order_line_dict.get('variant')
            variant_id = variant and extract_numeric_id(shopify_order_line_dict.get('variant', {}).get('id'))
            shopify_product_variant_id = self.get_mk_listing_item_for_mk_order(variant_id, mk_instance_id)

            odoo_product_id = self._get_shopify_odoo_product(shopify_order_line_dict, shopify_product_variant_id, gift_card_product, tip_product)
            quantity = shopify_order_line_dict.get('currentQuantity', 1)

            # T8942 - Log a message and stop importing the affected order when a normal product is not found in Odoo.
            # Log and return False if no product is found and the variant_id exists
            is_gift_card = shopify_order_line_dict.get('isGiftCard', False)
            is_tip = (shopify_order_line_dict.get('name') or shopify_order_line_dict.get('title')) == 'Tip'

            if quantity and not odoo_product_id and variant_id and not is_gift_card and not is_tip:
                log_message = _(
                    "IMPORT ORDER: The Shopify product with SKU %s was not found in Odoo, associated with Variant ID: %s, named: %s. Please create a product in Odoo with SKU %s and re-import this order.") % (
                                  shopify_order_line_dict.get('sku', False) or '', variant_id, shopify_order_line_dict.get('title', ''),
                                  shopify_order_line_dict.get('sku', False) or '')

                self.env['mk.log'].create_update_log(
                    mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                    mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False}]}
                )
                return False

            # Retrieve tax information if applicable
            tax_ids = None
            if tax_system_marketplace:
                tax_ids = self._get_shopify_odoo_taxes(mk_instance_id, shopify_order_line_dict.get('taxLines', []), taxes_included)

            self.with_context(shopify_order_dict=shopify_order_dict)._process_shopify_sale_order_line(mk_instance_id, shopify_order_line_dict, tax_ids, odoo_product_id,
                                                                                                      shopify_product_variant_id, order_id, shopify_order_dict)

        # Create shipping and special tax lines if applicable
        self.with_context(shopify_order_dict=shopify_order_dict).create_shopify_shipping_line(mk_instance_id, shopify_order_dict, order_id)
        self.with_context(shopify_order_dict=shopify_order_dict).create_special_tax_shipping_line(mk_instance_id, shopify_order_dict, order_id)

        return True

    def _detect_pickup_status_from_shopify(self, shopify_order_dict):
        """
        T6100 - Click & Collect Orders (Pickup Order)
        Determine the correct pickup_status for a pickup sale order by inspecting the Shopify order dictionary already enriched by
        fetch_order_fulfillment_location_from_shopify.

        displayFulfillmentStatus == 'FULFILLED'            → 'already_pickup'
        FulfillmentOrder.status  == 'IN_PROGRESS'
            + deliveryMethod     == 'PICK_UP'              → 'ready_to_pickup'
        Any other state                                    → False  (no change)

        :param dict shopify_order_dict: Shopify order dict enriched by fetch_order_fulfillment_location_from_shopify so that every line
            node carries 'shipping_method' and 'fulfillment_order_status'.
        :return: 'already_pickup', 'ready_to_pickup', or False.
        :rtype: str | bool
        """
        # Priority 1 — fully fulfilled in Shopify → already picked up.
        if shopify_order_dict.get('displayFulfillmentStatus') == 'FULFILLED' and self.is_pickup:
            return 'already_pickup'

        # Collect all FulfillmentOrder statuses for PICK_UP lines only.
        line_items_list = shopify_order_dict.get('lineItems', {}).get('nodes', []) if isinstance(shopify_order_dict.get('lineItems', {}), dict) else []
        pickup_line_statuses = [line.get('fulfillment_order_status') for line in line_items_list if
                                line.get('shipping_method') == SHOPIFY_DELIVERY_METHOD_PICKUP and line.get('fulfillment_order_status')]

        if not pickup_line_statuses:
            return False

        closed_statuses = {'CLOSED', 'SUCCESS'}

        # ALL PICK_UP lines are CLOSED/SUCCESS → all items picked up.
        if all(s in closed_statuses for s in pickup_line_statuses):
            return 'already_pickup'

        # At least one line is IN_PROGRESS → some items ready for pickup.
        # Handles PARTIALLY_FULFILLED orders where some lines are CLOSED (already picked up) and others are IN_PROGRESS (ready for pickup).
        if SHOPIFY_FO_STATUS_IN_PROGRESS in pickup_line_statuses:
            return 'ready_to_pickup'
        return False

    def _build_shopify_fulfillment_splits(self, order_line_dict):
        """
        Task T7767 - Convert Shopify fulfillment split data into JSON-storable values by mapping Shopify locations with Odoo Shopify location records.
        """
        splits_in_payload = order_line_dict.get('shopify_fulfillment_splits') or []
        json_splits = []
        for split in splits_in_payload:
            shopify_location_id = self.get_odoo_shopify_location_from_id(split.get('shopify_location_gid'))
            if not shopify_location_id:
                continue
            json_splits.append({
                'shopify_location_record_id': shopify_location_id.id,
                'qty': split.get('qty', 0),
                'fulfillment_order_status': split.get('fulfillment_order_status', ''),
                'fulfillment_order_id': split.get('fulfillment_order_id'),
                'fulfillment_order_line_item_id': split.get('fulfillment_order_line_item_id'),
            })
        return json_splits

    def fetch_order_fulfillment_location_from_shopify(self, mk_instance_id, shopify_order_dict):
        """
        Task T7767 - Fetch Shopify fulfillment order details and store fulfillment location, quantity, status, and split information in Shopify order lines
        to support multi-location fulfillment handling in Odoo.
        T6100 - Click & Collect Orders(Pickup Order)
        Modify this method to include fulfillment order status in shopify order dictionary.
        This method fetches fulfillment order details from Shopify, extracts fulfillment locations,
        and updates the Shopify order dictionary with location information for each line item.

        :param mk_instance_id: Instance used to execute GraphQL queries
        :param shopify_order_dict: Dictionary containing Shopify order details
        :return: Updated Shopify order dictionary with fulfillment location information
        """

        # GraphQL variables for the orderId
        variables = {"orderId": shopify_order_dict.get('id', "")}
        response = mk_instance_id.execute_graphql_query(FETCH_FULFILLMENT, variables)
        user_errors = response.get('errors', []) if isinstance(response, dict) else {}
        if user_errors and isinstance(user_errors, list):
            err_messages = [e.get('message', str(e)) for e in user_errors]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

        fulfillment_orders = response.get('data', {}).get('order', {}).get('fulfillmentOrders', {}) if isinstance(response, dict) else {}
        for fulfillment in fulfillment_orders:
            # Skip pagination entries by checking for an 'id'
            if 'id' not in fulfillment:
                continue

            delivery_method = fulfillment.get('deliveryMethod', False)
            shipping_method = delivery_method.get('methodType', '') if delivery_method else ""
            if shipping_method == 'PICK_UP':
                pickup_location_id = fulfillment.get('destination', {}).get('location', {}).get('id', '')
                shopify_order_dict.update({'is_pickup': True, 'pickup_location_id': pickup_location_id})  # Include pickup location too.

            fulfillment_id = extract_numeric_id(fulfillment.get('id'))
            fo_status = fulfillment.get('status', '')

            if fo_status in ['SUCCESS', 'OPEN', 'PENDING', 'CLOSED', 'IN_PROGRESS']:
                assigned_location_id = extract_numeric_id(fulfillment.get('assignedLocation', {}).get('location', {}).get('id'))
                for line_item in fulfillment.get('lineItems', []):
                    # Also skip pagination entries in the inner loop
                    if 'id' not in line_item:
                        continue
                    item = line_item.get('lineItem')
                    if item and item.get('id'):
                        line_item_id = extract_numeric_id(line_item.get('id'))
                        item_id = extract_numeric_id(item.get('id'))
                        total_qty = line_item.get('totalQuantity') or 0
                        remaining_qty = line_item.get('remainingQuantity') or 0
                        if fo_status in ('CLOSED', 'SUCCESS'):
                            fulfillment_line_quantity = total_qty - remaining_qty
                        else:
                            fulfillment_line_quantity = remaining_qty
                        shopify_split_entry = {
                            'shopify_location_gid': assigned_location_id,
                            'qty': fulfillment_line_quantity,
                            'fulfillment_order_line_item_id': line_item_id,
                            'fulfillment_order_id': fulfillment_id,
                            'fulfillment_order_status': fo_status,
                            'shipping_method': shipping_method,
                        }
                        for shopify_order_line_item in shopify_order_dict.get('lineItems', {}).get('nodes', []):
                            if extract_numeric_id(shopify_order_line_item.get('id')) == int(item_id):
                                shopify_order_line_item.setdefault('shopify_fulfillment_splits', []).append(shopify_split_entry)
                                shopify_order_line_item.update({
                                    'location_id': assigned_location_id,
                                    'fulfillment_order_line_item_id': line_item_id,
                                    'fulfillment_order_id': fulfillment_id,
                                    'fulfillment_order_status': fo_status,
                                    'shipping_method': shipping_method,
                                })

        return shopify_order_dict

    def _get_customers_for_shopify_order(self, shopify_order_dict, mk_instance_id):
        """
        Create or update customers in Odoo based on Shopify order information.
        :param shopify_order_dict: Dictionary containing Shopify order information.
        :param mk_instance_id: ID of the Shopify instance in Odoo.
        :return: Containing customer IDs for the main, billing, and shipping customers.
        """
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        partner_obj = self.env['res.partner']
        shopify_order_name = shopify_order_dict.get('name', '')
        company_customer_id = False

        # Check if the creation of a company contact is enabled and if there is customer information in the Shopify order
        if mk_instance_id.is_create_company_contact and shopify_order_dict.get('customer', {}):
            default_address_dict = shopify_order_dict.get('customer', {}).get('defaultAddress') if shopify_order_dict.get('customer', {}).get('defaultAddress',
                                                                                                                                              False) else shopify_order_dict.get(
                'customer', {})

            email_from_default = (default_address_dict.get('defaultEmailAddress') or {}).get('emailAddress') or ''
            email_from_customer = ((shopify_order_dict.get('customer') or {}).get('defaultEmailAddress') or {}).get('emailAddress') or ''

            # Update the email in the default address dictionary if it is missing but available in the customer information
            if not email_from_default and email_from_customer:
                default_address_dict.update({'email': email_from_customer})

            # Check if the default address indicates a company
            is_company = True if default_address_dict.get('company', False) else False
            # If it's a company, create or update the company customer in Odoo
            if is_company:
                company_customer_id = partner_obj.create_update_shopify_customers(default_address_dict, mk_instance_id)

        # If there is no customer information in the Shopify order and the source is 'pos', use the default POS customer
        if not shopify_order_dict.get('customer', False) and shopify_order_dict.get('sourceName', '') == 'pos' and mk_instance_id.default_pos_customer_id:
            customer_id = mk_instance_id.default_pos_customer_id
        else:
            # Create or update the regular customer in Odoo based on the Shopify order information
            customer_id = partner_obj.create_update_shopify_customers(shopify_order_dict.get('customer', {}), mk_instance_id, parent_id=company_customer_id)

        # Handle if there is no customer found in the Shopify Order response
        if not customer_id:
            log_message = _("IMPORT ORDER: Customer not found in Shopify Order No: %s(%s)") % (shopify_order_name, extract_numeric_id(shopify_order_dict.get('id')))
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False, False, False

        # Determine the billing customer based on the provided information
        if not shopify_order_dict.get('billingAddress', shopify_order_dict.get('customer', False)):
            billing_customer_id = customer_id
        else:
            billing_company_id = False
            # Check if the creation of a company contact is enabled and if there is billing address information
            if mk_instance_id.is_create_company_contact and shopify_order_dict.get('billingAddress', {}).get('company', '') and (
                    not company_customer_id or company_customer_id.name != shopify_order_dict.get('billingAddress', {}).get('company', '')):
                billing_company_id = partner_obj.create_update_shopify_customers(shopify_order_dict.get('billingAddress', {}), mk_instance_id)

            # Create or update the billing customer in Odoo
            billing_customer_id = partner_obj.create_update_shopify_customers(shopify_order_dict.get('billingAddress', shopify_order_dict.get('customer', {})), mk_instance_id,
                                                                              type='invoice', parent_id=billing_company_id or company_customer_id or customer_id)

        # Determine the shipping customer based on the provided information
        if not shopify_order_dict.get('shippingAddress', shopify_order_dict.get('customer', False)):
            shipping_customer_id = customer_id
        else:
            shipping_company_id = False
            # Check if the creation of a company contact is enabled and if there is shipping address information
            if mk_instance_id.is_create_company_contact and shopify_order_dict.get('shippingAddress', {}).get('company', '') and (
                    not company_customer_id or company_customer_id.name != shopify_order_dict.get('shippingAddress', {}).get('company', '')):
                shipping_company_id = partner_obj.create_update_shopify_customers(shopify_order_dict.get('shippingAddress', {}), mk_instance_id)

            # Create or update the shipping customer in Odoo
            shipping_customer_id = partner_obj.create_update_shopify_customers(shopify_order_dict.get('shippingAddress', shopify_order_dict.get('customer', {})), mk_instance_id,
                                                                               type='delivery', parent_id=shipping_company_id or company_customer_id or customer_id)

        # Return the created or updated customer IDs
        return customer_id, billing_customer_id, shipping_customer_id

    def _update_warehouse_based_on_shopify_location(self):
        # Update order's warehouse based on shopify location.
        shopify_location_id = self.order_line.mapped('shopify_location_id')
        if len(shopify_location_id) > 1:
            shopify_location_id = shopify_location_id[0]
        if shopify_location_id and shopify_location_id.order_warehouse_id:
            self.warehouse_id = shopify_location_id.order_warehouse_id.id

    def _get_shopify_refund_line_ids(self, refund_data_line):
        refund_line_item_dict = {}
        for refund_line_item in refund_data_line.get('refundLineItems', {}).get('nodes', []):
            quantity = refund_line_item.get('quantity')
            line_item_id = extract_numeric_id(refund_line_item.get('lineItem', {}).get('id'))
            if refund_line_item_dict.get(line_item_id):
                refund_line_item_dict.update({line_item_id: (refund_line_item_dict.get(line_item_id) + quantity)})
            else:
                refund_line_item_dict.update({line_item_id: quantity})
        return refund_line_item_dict

    def _update_credit_note_from_shopify_refund_data(self, refund_invoice, refund_line_item_dict):
        """
        Task: T4859 - Check restock inventory while cancel order from Odoo
        Update this method to fix the issue of refund creation.
        Args:
            refund_invoice (recordset): Recordset of account.move model.
            refund_line_item_dict (dictionary): Dictionary that holds refund data. e.g. {13759742541877: 1, 13759742574645: 1}
        Returns:
            boolean: Returns True.
        """
        to_remove_move_lines = self.env['account.move.line']
        previous_mk_id = ''
        for new_move_line in refund_invoice.invoice_line_ids:
            mk_id = int(new_move_line.sale_line_ids.mk_id)
            if mk_id and refund_line_item_dict.get(mk_id):
                new_move_line.quantity = refund_line_item_dict.get(mk_id)
            elif new_move_line.product_id.id == self.mk_instance_id.discount_product_id.id and refund_line_item_dict.get(previous_mk_id):
                new_move_line.price_unit = previous_move_line.sale_line_ids.related_disc_sale_line_id.price_unit
                new_move_line.quantity = previous_move_line.quantity
            elif new_move_line.product_id.id == self.mk_instance_id.discount_product_id.id and not refund_line_item_dict.get(previous_mk_id):
                new_move_line.quantity = 0
            else:
                to_remove_move_lines += new_move_line
            previous_move_line = new_move_line
            previous_mk_id = int(new_move_line.sale_line_ids.mk_id)
        to_remove_move_lines and to_remove_move_lines.with_context(check_move_validity=False).write({'quantity': 0})
        return True

    def _get_currency_based_on_instance_configuration(self, mk_instance_id, amount_dict):
        if mk_instance_id.use_marketplace_currency:
            amount = float(amount_dict.get('presentmentMoney', {}).get('amount', 0.0)) or 0.0
        else:
            amount = float(amount_dict.get('shopMoney', {}).get('amount', 0.0)) or 0.0
        return amount

    def _create_order_adjustment_line_shopify(self, refund_data_line, refund_invoice, taxes_included):
        """
        Task: T4859 - Check restock inventory while cancel order from Odoo
        Update this method to stop creating the new adjustment line for shipping product and update it in existing shipping line in refund.
        Args:
            refund_data_line (dictionary): Dictionary that hold refund details,
            refund_invoice (recordset): Recordset of account.move model,
            taxes_included (boolean): Defines tax included in order or not.
        Returns:
            boolean: Returns true if successfully cancel order in shopify.
        Raises:
            MarketplaceException: If there's an exception during order cancellation process.
        """
        account_move_line_obj = self.env['account.move.line']
        order_adjustments = refund_data_line.get('orderAdjustments', {}).get('nodes', [])

        for adjustment in order_adjustments:
            tax_ids = []

            total_adjustment = self._get_currency_based_on_instance_configuration(self.mk_instance_id, adjustment.get('amountSet'))
            if taxes_included:
                total_adjustment += self._get_currency_based_on_instance_configuration(self.mk_instance_id, adjustment.get('taxAmountSet'))

            adjustment_product_id = self.env.ref('base_marketplace.marketplace_adjustment_product', False)
            adjustment_move_vals = {'name': 'Refund Adjustment', 'product_id': adjustment_product_id.id,
                                    'quantity': 1, 'price_unit': abs(total_adjustment),
                                    'move_id': refund_invoice.id, 'partner_id': refund_invoice.partner_id.id,
                                    'tax_ids': tax_ids}
            account_move_line_obj.with_context(check_move_validity=False).create(adjustment_move_vals)

        shipping_adjustments = refund_data_line.get('refundShippingLines', {}).get('nodes', [])
        for shipping_adjustment in shipping_adjustments:
            total_adjustment = self._get_currency_based_on_instance_configuration(self.mk_instance_id, shipping_adjustment.get('subtotalAmountSet'))
            if taxes_included:
                total_adjustment += self._get_currency_based_on_instance_configuration(self.mk_instance_id, shipping_adjustment.get('taxAmountSet'))

            refund_delivery_line = refund_invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.mk_instance_id.delivery_product_id)
            refund_delivery_line.write({'quantity': 1, 'price_unit': abs(total_adjustment)})

    def _check_shopify_descripency(self, refund_data_line, refund_invoice):
        """
        Check if Shopify refund amount matches Odoo refund invoice amount.
        """
        transactions = refund_data_line.get("transactions", {}).get("nodes", [])

        shopify_refund_amount = sum(self._get_currency_based_on_instance_configuration(self.mk_instance_id, transaction.get("amountSet", {}))
                                    for transaction in transactions if transaction.get("status") == "SUCCESS")
        odoo_refund_amount = round(refund_invoice.amount_total, 2)
        return shopify_refund_amount == odoo_refund_amount

    def _create_shopify_credit_note_and_adjust_amount(self, shopify_order_dict, refund_data_line, invoice_ids):
        """
        Task: T4859 - Check restock inventory while cancel order from Odoo
        Update this method to remove zero qty refund line from odoo's credit note.
        Args:
            shopify_order_dict (list): The data list to populate.
            refund_data_line (list): The results from the SQL query
            invoice_ids ():
        Returns:
            boolean: Returns true if successfully create credit note in odoo.
        """
        self = self.sudo()
        mk_log_id = self.env.context.get('mk_log_id', False)
        log_prefix = self.env.context.get('credit_note_log_prefix') or 'IMPORT ORDER'
        queue_line_id = self.env.context.get('queue_line_id', False)
        refund_line_item_dict = self._get_shopify_refund_line_ids(refund_data_line)
        if not invoice_ids:
            log_message = _("Automatic credit note creation is skipped because no posted customer invoice was found for this order. Please create the credit note in Odoo manually for Shopify Order %s.") % shopify_order_dict.get('name')
            self.env['mk.log'].create_update_log(mk_instance_id=self.mk_instance_id, operation_type='import', mk_log_id=mk_log_id, mk_log_line_dict={
                'error': [{'log_message': f'{log_prefix}: {log_message}', 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False
        if len(invoice_ids) > 1:
            log_message = _("Automatic credit note creation is skipped due to a multiple customer invoices found. Please create the credit note in Odoo manually for Shopify Order %s.") % shopify_order_dict.get('name')
            self.env['mk.log'].create_update_log(mk_instance_id=self.mk_instance_id, operation_type='import', mk_log_id=mk_log_id, mk_log_line_dict={
                'error': [{'log_message': f'{log_prefix}: {log_message}', 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False
        date = self.env.context.get('date', convert_shopify_datetime_to_utc(refund_data_line.get('createdAt')))
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice_ids.ids).create({
            'date': date,
            'reason': refund_data_line.get('note', 'Refunded from Shopify') or 'Refunded from Shopify',
            'journal_id': invoice_ids[0].journal_id.id
        })
        move_reversal.reverse_moves()
        refund_invoice = move_reversal.new_move_ids
        refund_invoice.write({'shopify_refund_id': extract_numeric_id(refund_data_line.get('id'))})
        self._update_credit_note_from_shopify_refund_data(refund_invoice, refund_line_item_dict)
        taxes_included = shopify_order_dict.get('taxesIncluded')
        self._create_order_adjustment_line_shopify(refund_data_line, refund_invoice, taxes_included)
        if not self._check_shopify_descripency(refund_data_line, refund_invoice):
            transactions = refund_data_line.get("transactions", {}).get("nodes", [])

            shopify_refund_amount = sum(self._get_currency_based_on_instance_configuration(self.mk_instance_id, transaction.get("amountSet", {}))
                                        for transaction in transactions if transaction.get("status") == "SUCCESS")

            log_message = _(
                "Automatic credit note creation is skipped due to a discrepancy between the Shopify refund total(%s) and Odoo's credit note total(%s). Please create the credit note in Odoo manually for Shopify Order %s.") % (
                              shopify_refund_amount, refund_invoice.amount_total, shopify_order_dict.get('name'))
            self.env['mk.log'].create_update_log(mk_instance_id=self.mk_instance_id, mk_log_id=mk_log_id, operation_type='import', mk_log_line_dict={
                'error': [{'log_message': f'{log_prefix}: {log_message}', 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.queue_id.create_activity_action(log_message)
            refund_invoice.unlink()
            return False
        container = {'records': refund_invoice}
        # Remove zero qty refund line from the credit note
        zero_qty_refund_line = refund_invoice.invoice_line_ids.filtered(lambda l: not l.quantity and l.display_type not in ['line_note', 'line_section'])
        if zero_qty_refund_line:
            zero_qty_refund_line.unlink()
        refund_invoice.with_context(**{'check_move_validity': False})._sync_dynamic_lines(container)
        if refund_invoice.state == 'draft':
            refund_invoice.action_post()
        if self.env.context.get('refund_journal_id', False):
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=refund_invoice.ids).create(
                {'journal_id': self.env.context.get('refund_journal_id')})._create_payments()
        return True

    def _create_shopify_credit_note(self, shopify_order_dict):
        account_move_obj = self.env['account.move']
        invoice_ids = self.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice' and x.state == 'posted')
        for refund_data_line in shopify_order_dict.get('refunds', []):
            refund_data_line_id = str(extract_numeric_id(refund_data_line.get('id')))
            existing_refund_id = account_move_obj.search([("shopify_refund_id", "=", refund_data_line_id), ("mk_instance_id", "=", self.mk_instance_id.id)])
            if existing_refund_id:
                continue
            self._create_shopify_credit_note_and_adjust_amount(shopify_order_dict, refund_data_line, invoice_ids)
        return True

    def _check_validation_to_process_credit_note(self, shopify_order_dict):
        if not self.order_workflow_id.sudo().is_create_credit_note:
            return False

        if not shopify_order_dict.get('displayFinancialStatus', '') in ['REFUNDED', 'PARTIALLY_REFUNDED']:
            return False

        if not self.invoice_ids:
            _logger.info(f"SHOPIFY CREDIT NOTE: Cannot create Credit note because related invoice not found for Order {self.name}")
            return False

        invoice_ids = self.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice' and x.state == 'posted')
        if not invoice_ids:
            _logger.info(f"SHOPIFY CREDIT NOTE: Cannot create Credit note because related invoice not found for Order {self.name}")
            return False

        if not self._check_invoice_policy_ordered():
            _logger.info(f"SHOPIFY CREDIT NOTE: Cannot create Credit note because some product is not delivered for Order {self.name}")
            return False

        # If there is any manual refund created, then we are not create automatic refund according to Shopify.
        if self.invoice_ids.filtered(lambda x: x.move_type == 'out_refund' and not x.shopify_refund_id):
            _logger.info(f"SHOPIFY CREDIT NOTE: Cannot create Credit note because there is already credit note created for Order {self.name}")
            return False
        return True

    def _process_shopify_refund_in_odoo(self, shopify_order_dict):
        self = self.sudo()
        if not self.env.context.get('skip_check_transaction', False):
            trans_list = [transaction for transaction in shopify_order_dict.get('transactions', []) if
                          transaction and transaction.get('status') == 'SUCCESS' and transaction.get('kind') in ['CAPTURE', 'SALE']]

            if not trans_list:
                return False

        if not self._check_validation_to_process_credit_note(shopify_order_dict):
            return False

        self._create_shopify_credit_note(shopify_order_dict)
        return True

    def _validate_and_process_shopify_order(self, shopify_order_dict):
        shopify_order_line_list = shopify_order_dict.get('lineItems')
        is_importable, financial_workflow_config_id = self.check_validation_for_import_sale_orders(shopify_order_line_list, self.mk_instance_id, shopify_order_dict)
        if not is_importable:
            return False
        self.order_workflow_id = financial_workflow_config_id.order_workflow_id
        self.with_context(create_date=convert_shopify_datetime_to_utc(shopify_order_dict.get("processedAt", "")), order_dict=shopify_order_dict).do_marketplace_workflow_process()
        return f"IMPORT ORDER: Shopify Order {shopify_order_dict.get('name', '')}({extract_numeric_id(shopify_order_dict.get('id'))}) is successfully updated."

    def _get_shopify_order_cancel_reason(self, reason):
        """
        Get the human-readable cancel reason based on the Shopify order cancellation reason.

        :param reason: Shopify order cancellation reason.
        :return: Human-readable cancel reason.
        """
        cancel_msg = "A reason not specified."
        SHOPIFY_CANCEL_REASON_MAPPING = {
            "CUSTOMER": "The customer canceled the order.",
            "FRAUD": "The order was fraudulent.",
            "INVENTORY": "Items in the order were not in inventory.",
            "DECLINED": "The payment was declined.",
            "OTHER": "The order was canceled for other reasons.",
        }
        return SHOPIFY_CANCEL_REASON_MAPPING.get(reason, cancel_msg)

    def cancel_shopify_order_in_odoo(self, shopify_order_dict):
        """
        Cancel the Odoo sale order based on the cancellation information received from Shopify.

        :param shopify_order_dict: Dictionary containing details of Shopify Order.
        :return: True if the order is successfully canceled in Odoo, False otherwise.
        """
        # Check if cancel reason is provided from Shopify and the order is not already canceled in Odoo
        if shopify_order_dict.get('cancelReason') and self.state != 'cancel':
            # Extract the cancel reason from the Shopify order dictionary
            cancel_reason = self._get_shopify_order_cancel_reason(shopify_order_dict.get('cancelReason'))

            cancel_message = _("The order was canceled on Shopify store. Reason: %s") % cancel_reason  # Compose cancel message based on cancel reason

            # filter completed picking orders related to the sale order
            picking_ids = self.picking_ids.filtered(lambda x: x.state == 'done')

            # Post cancel message to each completed picking order
            for picking_id in picking_ids:
                picking_id.message_post(body=cancel_message)
            picking_ids.write({'cancel_in_marketplace': True})  # Mark picking orders as canceled in the marketplace

            # Perform order cancellation in Odoo, disabling cancellation warning
            self.with_context({'disable_cancel_warning': True}).action_cancel()
            self.message_post(body=cancel_message)
            self.write({'canceled_in_marketplace': True})  # Mark the sale order as canceled in the marketplace
            return True
        return False

    def process_import_order_from_shopify_ts(self, shopify_order_dict, mk_instance_id):
        """
        T6293 - Fetches remaining order metafields while fetching Shopify order data by ID.
        T6100 - Click & Collect Orders(Pickup Order)
        Imports an order from Shopify and processes it within Odoo.
        Args:
            shopify_order_dict: Dictionary containing Shopify order details
            mk_instance_id: The Shopify marketplace instance
        Returns:
            order_id: The imported and processed sale order in Odoo, or False if the import failed
        """
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)

        # After executing the main GraphQL query, there's a possibility of receiving partial data
        # For example, if order has 15 lines but the query limit is set to 10, only 10 line will be returned initially.
        # This logic handles such cases by performing an additional query to fetch the remaining data and appending it to the existing order dictionary.
        if queue_line_id:
            shopify_order_dict = self.get_all_remaining_shopify_order_data(shopify_order_dict, mk_instance_id)
        else:
            shopify_order_dict = self.get_all_remaining_shopify_order_data(shopify_order_dict, mk_instance_id, only_resources=['metafields'])

        # Check if the order already exists in Odoo
        mk_id = str(extract_numeric_id(shopify_order_dict.get('id', "")))
        existing_order_id = self._get_existing_order(mk_id, mk_instance_id)

        if existing_order_id:
            if existing_order_id.state == 'cancel':
                return existing_order_id
            process_result = self._process_existing_shopify_order(existing_order_id, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id)
            existing_order_id._sync_shopify_returns_from_order_payload(shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id)
            return process_result

        # Check if the order date is within the allowed range for import
        if not self._is_order_importable(shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id):
            return True

        # Validate order lines and customers
        customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id = self._validate_order_for_import(shopify_order_dict, mk_instance_id, mk_log_id,
                                                                                                                               queue_line_id)
        if not customer_id:
            return False

        # Fetch fulfillment location for order lines from Shopify and set in order dict.
        self.fetch_order_fulfillment_location_from_shopify(mk_instance_id, shopify_order_dict)

        # Create the sale order in Odoo
        order_id = self._create_sale_order_in_odoo(shopify_order_dict, mk_instance_id, customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id)

        # Mark pickup order as already picked up when it fulfilled in shopify.
        # order_id and order_id.fulfillment_status == 'FULFILLED' and order_id.is_pickup and order_id.write({'pickup_status': 'already_pickup'})
        # Detect and set the correct pickup status from Shopify's live state.
        # Covers: FULFILLED → already_pickup and IN_PROGRESS → ready_to_pickup.
        if order_id and order_id.is_pickup:
            detected_pickup_status = order_id._detect_pickup_status_from_shopify(shopify_order_dict)
            detected_pickup_status and order_id.write({'pickup_status': detected_pickup_status})

        if not order_id:
            return False

        # Further processing of the sale order
        finalize_result = self._finalize_order_processing(order_id, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id)
        order_id._sync_shopify_returns_from_order_payload(shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id)
        return finalize_result

    def _sync_shopify_returns_from_order_payload(self, shopify_order_dict, mk_instance_id, mk_log_id=False, queue_line_id=False):
        """
        Task: T8437 - Import Shopify returns embedded directly within the order payload.
        Paginates and imports returns safely without rolling back the order.
        Args:
            shopify_order_dict (dict): The Shopify order payload.
            mk_instance_id (recordset): Recordset of mk.instance model.
            mk_log_id (recordset): Recordset of mk.log model. Optional.
            queue_line_id (recordset): Recordset of mk.queue.job.line model.
        Returns:
            bool: Always True. Errors are logged, never raised.
        """
        self.ensure_one()
        if not (shopify_order_dict.get('returns') or {}).get('nodes'):
            return True
        try:
            with self.env.cr.savepoint():
                self._paginate_shopify_order_returns(mk_instance_id, shopify_order_dict)
                self.env['shopify.return.ts'].import_shopify_returns_from_order_payload(mk_instance_id, shopify_order_dict, mk_log_id=mk_log_id, queue_line_id=queue_line_id)
        except Exception as error:
            log_traceback_for_exception()
            log_message = _("IMPORT RETURN: Failed to import returns received with Shopify order %s. ERROR: %s") % (self.name, error)
            self.env['mk.log'].create_update_log(
                mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]},
            )
        return True

    def _update_pickup_pickings_from_shopify(self, shopify_order_dict):
        """
        T6100 - Click & Collect Orders (Pickup Order)
        Sync picking-level marketplace status fields during order import for
        pickup orders whose FulfillmentOrders are already actioned in Shopify.

        Evaluates each done picking INDEPENDENTLY against its own line item
        statuses so that in a PARTIALLY_FULFILLED order (e.g. one picking CLOSED,
        another IN_PROGRESS) each picking receives only the values matching its
        own Shopify FulfillmentOrder status.

        IN_PROGRESS  -> "Ready for Pickup" in Shopify.
                        Sets: updated_in_marketplace=True
                        Hides the "Ready For Pickup" button on the picking.

        CLOSED / SUCCESS -> Fully picked up / fulfilled.
                            Sets: updated_in_marketplace=True
                                  is_picked_up_in_marketplace=True
                            Hides both "Ready For Pickup" and "Mark as Picked Up".

        Must be called AFTER fetch_order_fulfillment_location_from_shopify has
        enriched line nodes with 'fulfillment_order_status' and 'shipping_method'.

        :param dict shopify_order_dict: Enriched Shopify order dict.
        :return: None
        """
        # Build per-line-mk_id status map for PICK_UP lines only.
        picking_ids, line_status_map = self.env['stock.picking'], {}
        for line in shopify_order_dict.get('lineItems', {}).get('nodes', []):
            if line.get('shipping_method') != SHOPIFY_DELIVERY_METHOD_PICKUP:
                continue
            line_numeric = extract_numeric_id(line.get('id'))
            if line_numeric:
                line_status_map[str(line_numeric)] = line.get('fulfillment_order_status', '')

        if not line_status_map:
            return

        closed_statuses = {'CLOSED', 'SUCCESS'}
        actioned_statuses = closed_statuses | {SHOPIFY_FO_STATUS_IN_PROGRESS}

        domain = [('location_dest_id.usage', '=', 'customer'), ('picking_type_code', '=', 'outgoing'),
                  ('state', 'in', ['confirmed', 'assigned', 'done']), ('cancel_in_marketplace', '=', False),
                  ('is_fbm_order', '=', False), ('updated_in_marketplace', '=', False)]
        # Target done outgoing pickings not yet synced to marketplace.
        picking_ids = self.picking_ids.filtered_domain(domain)

        for picking in picking_ids:
            picking_line_mk_ids = {str(move.sale_line_id.mk_id) for move in picking.move_ids if move.sale_line_id and move.sale_line_id.mk_id}
            # Only consider statuses of lines that belong to THIS picking.
            relevant_statuses = {line_status_map[mk_id] for mk_id in picking_line_mk_ids if mk_id in line_status_map}
            if not relevant_statuses:
                continue
            # All relevant lines must be actioned before syncing this picking.
            if not relevant_statuses.issubset(actioned_statuses):
                continue

            if relevant_statuses.issubset(closed_statuses):
                # All lines for this picking are CLOSED/SUCCESS → already picked up.
                picking_vals = {'updated_in_marketplace': True, 'is_picked_up_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False}
            else:
                # At least one line is IN_PROGRESS → ready for pickup (not yet picked up).
                picking_vals = {'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False}
            picking.write(picking_vals)

    def _process_existing_shopify_order(self, existing_order_id, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id):
        """
        T6293 - Processes an already imported Shopify order in Odoo by updating metafield from Shopify.
        """
        fulfillment_status = shopify_order_dict.get('displayFulfillmentStatus', 'UNFULFILLED') or 'UNFULFILLED'
        mk_id = str(extract_numeric_id(shopify_order_dict.get('id', "")))
        shopify_order_name = shopify_order_dict.get('name', '')

        log_message = existing_order_id._validate_and_process_shopify_order(shopify_order_dict)

        # Fetch fulfillment order details so that each line node in shopify_order_dict carries 'shipping_method' and 'fulfillment_order_status'. This is required for correct pickup status detection (IN_PROGRESS → ready_to_pickup)
        existing_order_id.is_pickup and existing_order_id.fetch_order_fulfillment_location_from_shopify(mk_instance_id, shopify_order_dict)

        existing_order_id.with_context(operation_type='import', mk_log_id=mk_log_id).auto_validate_shopify_delivery_order(shopify_order_dict.get('fulfillments'))
        # Update pickings status for pickup orders at that case where validated from odoo and mark as Ready for Pickup in shopify.
        existing_order_id.is_pickup and existing_order_id._update_pickup_pickings_from_shopify(shopify_order_dict)

        existing_order_id.with_context(skip_check_transaction=True)._process_shopify_refund_in_odoo(shopify_order_dict)  # create refund according to the Shopify.

        shopify_tag_vals = existing_order_id.prepare_order_tag_vals(shopify_order_dict.get('tags'))

        existing_order_id.cancel_shopify_order_in_odoo(shopify_order_dict)

        pickup_status = existing_order_id._detect_pickup_status_from_shopify(shopify_order_dict)
        update_order_vals = {'shopify_financial_status': shopify_order_dict.get('displayFinancialStatus'),
                             'fulfillment_status': fulfillment_status,
                             'updated_in_marketplace': True if fulfillment_status == 'FULFILLED' else False,
                             'pickup_status': pickup_status or existing_order_id.pickup_status}

        # Update tags while update order
        update_order_vals.update(shopify_tag_vals)

        existing_order_id.write(update_order_vals)

        existing_order_id.import_order_metafield_from_shopify(mk_instance_id, shopify_order_dict, mk_id=mk_id, mk_log_id=mk_log_id, queue_line_id=queue_line_id)

        if not log_message:
            log_message = _("IMPORT ORDER: Shopify Order %s(%s) is already imported.") % (shopify_order_name, mk_id)
        self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                             mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
        return existing_order_id

    def _is_order_importable(self, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id):
        """Check if the Shopify order is importable based on its date."""
        order_date = convert_shopify_datetime_to_utc(shopify_order_dict.get("processedAt", ""))
        shopify_order_id = str(extract_numeric_id(shopify_order_dict.get('id', "")))
        if not self.check_marketplace_order_date(order_date, mk_instance_id):
            log_message = _("IMPORT ORDER: Shopify Order %s(%s) is skipped due to being created prior to the allowed date.") % (shopify_order_dict.get('name'), shopify_order_id)
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False
        return True

    def _validate_order_for_import(self, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id):
        """Validate Shopify order lines and customers before importing."""
        shopify_order_line_list = shopify_order_dict.get('lineItems')
        is_importable, financial_workflow_config_id = self.check_validation_for_import_sale_orders(shopify_order_line_list, mk_instance_id, shopify_order_dict)

        if not is_importable:
            return False, None, None, None

        customer_id, billing_customer_id, shipping_customer_id = self.with_context(mk_log_id=mk_log_id, queue_line_id=queue_line_id)._get_customers_for_shopify_order(
            shopify_order_dict, mk_instance_id)
        return customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id

    def _create_sale_order_in_odoo(self, shopify_order_dict, mk_instance_id, customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id):
        """Create the sale order in Odoo based on Shopify order data."""
        order_id = self.create_shopify_sale_order(shopify_order_dict, mk_instance_id, customer_id, billing_customer_id, shipping_customer_id, financial_workflow_config_id)
        if not order_id:
            return False

        if not order_id.create_sale_order_line_shopify(mk_instance_id, shopify_order_dict, order_id):
            order_id.sudo().unlink()
            return False

        order_id._update_warehouse_based_on_shopify_location()
        return order_id

    def shopify_get_product_quantity_and_lot(self):
        """
        Task:T6366 - Validate stock availability and lot/serial readiness for Shopify orders.

        For each storable product tracked by lot or serial number, the method:
            - Retrieves available inventory from the Shopify-linked warehouse location.
            - Verifies that at least one lot/serial quant exists.
            - Ensures reservable stock is available.

        If any tracked product lacks available stock or does not have an
        associated lot/serial number, fulfillment is deferred and the delivery
        order remains available for manual lot assignment and validation.

        Returns:
            tuple(bool, bool):
                - (True, True): All tracked products have reservable stock and
                  at least one valid lot/serial number.
                - (False, False): At least one tracked product is missing
                  reservable stock or a valid lot/serial number.
        """
        company_id = self.mk_instance_id.company_id
        quant_obj = self.env['stock.quant'].with_company(company_id)
        for order_line_id in self.order_line.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and l.product_id.is_storable):
            product_id = order_line_id.product_id
            location_id = order_line_id.shopify_location_id.location_id
            available_quantity = quant_obj._get_available_quantity(product_id, location_id, strict=True)
            lot_quant_ids = quant_obj.search(
                [('product_id', '=', product_id.id), ('location_id', '=', location_id.id), ('company_id', '=', company_id.id), ('lot_id', '!=', False)])
            if not (lot_quant_ids and available_quantity > 0.0):  # Defer unless a usable lot exists AND reservable stock is available.
                return False, False
        return True, True

    def fetch_shopify_order_risk(self, mk_id, mk_instance_id, mk_log_id=False, queue_line_id=False):
        """
        T8578 - Fetch only the risk block of a Shopify order.
        Used when the order payload carries no risk data, which is the case for orders received through the
        orders/create and orders/updated webhooks. The query asks for the risk block alone, so it also works
        for stores whose app has no protected customer data access.
        Args:
            mk_id: The Shopify order ID.
            mk_instance_id: The marketplace instance record.
            mk_log_id: The log record to attach a failure message to.
            queue_line_id: The queue line record being processed, if any.
        Returns:
            Return the risk dictionary of the Shopify order, or an empty dictionary when it can not be fetched.
        """
        try:
            variables = {"id": f"gid://shopify/Order/{mk_id}"}
            res = mk_instance_id.execute_graphql_query(ORDER_RISK, variables)
            user_errors = res.get('errors', []) if isinstance(res, dict) else []
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order Risk: %(errors)s") % {'errors': ", ".join(err_messages)})
            order_dict = res.get('data', {}).get('order', {}) if isinstance(res, dict) else {}
            return order_dict and order_dict.get('risk', {}) or {}
        except Exception as e:
            # A missing fraud analysis must never block the order import, so only log the failure.
            log_message = _("IMPORT ORDER: Unable to fetch the fraud analysis of the Shopify order with ID (%s). ERROR: %s") % (mk_id, e)
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return {}

    def _finalize_order_processing(self, order_id, shopify_order_dict, mk_instance_id, mk_log_id, queue_line_id):
        """
        T6293 - Processes an already imported Shopify order in Odoo by updating metafields from Shopify.
        Finalize the processing of the imported Shopify sale order.
        """
        mk_id = str(extract_numeric_id(shopify_order_dict.get('id')))
        if order_id.check_shopify_order_cancellation_state(shopify_order_dict):
            order_id.cancel_shopify_order_in_odoo(shopify_order_dict)
            log_message = _("IMPORT ORDER: The Shopify order %s with ID (%s) has already been canceled and is imported as a canceled order.") % (
                shopify_order_dict.get('name'), mk_id)
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return order_id

        if mk_instance_id.is_fetch_fraud_analysis_data:
            # T857 - The webhook payload has no risk data, so fetch it with a dedicated query that asks for the risk block only.
            order_risk = shopify_order_dict.get('risk', []) or self.fetch_shopify_order_risk(mk_id, mk_instance_id, mk_log_id, queue_line_id)
            self.env['shopify.fraud.analysis'].create_fraud_analysis(mk_id, order_id, order_risk)
            # TASK T6411- Reminder Activity for Shopify Risk Orders.
            if order_id.fraud_analysis_ids:
                order_id.create_fraud_order_activity(mk_instance_id)

        if not order_id.is_fraud_order:
            order_id.with_context(create_date=convert_shopify_datetime_to_utc(shopify_order_dict.get("processedAt", "")),
                                  order_dict=shopify_order_dict).do_marketplace_workflow_process()

            # Sync pickup statuses to newly generated pickings
            if order_id.is_pickup and order_id.fulfillment_status != 'FULFILLED':
                order_id._update_pickup_pickings_from_shopify(shopify_order_dict)
            if order_id.fulfillment_status == 'FULFILLED' and not order_id.invoice_ids:
                order_id.with_context(order_dict=shopify_order_dict).process_invoice(order_id.order_workflow_id)

            order_id.order_workflow_id.sudo().is_validate_invoice and order_id._process_shopify_refund_in_odoo(shopify_order_dict)

        order_id.import_order_metafield_from_shopify(mk_instance_id, shopify_order_dict, mk_id=mk_id, mk_log_id=mk_log_id, queue_line_id=queue_line_id)

        log_message = _('IMPORT ORDER: Successfully imported marketplace order %s(%s)') % (order_id.name, order_id.mk_id)
        self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                             mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
        return order_id

    def check_shopify_order_cancellation_state(self, shopify_order_dict):
        return bool(shopify_order_dict.get('cancelReason'))

    def import_shopify_order_by_id(self, shopify_order_list, mk_instance_id):
        res_id_list = []
        mk_log_id = self.env.context.get('mk_log_id', False)
        for shopify_order in shopify_order_list:
            mk_id = extract_numeric_id(shopify_order.get('id', ""))

            try:
                with self.env.cr.savepoint():
                    order_id = self.with_context(mk_log_id=mk_log_id, skip_inventory_sync_commit=True).process_import_order_from_shopify_ts(shopify_order, mk_instance_id)
                    if not isinstance(order_id, bool):
                        res_id_list.append(order_id.id)
            except Exception as e:
                log_traceback_for_exception()
                self.env.cr.rollback()
                log_message = f"PROCESS ORDER: Error while processing Marketplace Order {shopify_order.get('name')} ({mk_id}), ERROR: {e}"
                if not mk_log_id.exists():
                    mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
                self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
            self.env.cr.commit()
        return res_id_list

    def create_shopify_order_queue_job(self, mk_instance_id, shopify_order_list):
        res_id_list = []
        batch_size = mk_instance_id.queue_batch_limit or 100
        for shopify_orders in tools.split_every(batch_size, shopify_order_list):
            queue_id = mk_instance_id.action_create_queue(type='order')
            for order in shopify_orders:
                name = order.get('name', '') or ''
                line_vals = {
                    'mk_id': str(extract_numeric_id(order.get('id'))) or '',
                    'state': 'draft',
                    'name': name.strip(),
                    'data_to_process': pprint.pformat(order),
                    'mk_instance_id': mk_instance_id.id,
                }
                queue_id.action_create_queue_lines(line_vals)
            res_id_list.append(queue_id.id)
        return res_id_list

    def shopify_import_orders(self, mk_instance_ids, from_date=False, to_date=False, mk_order_id=False):
        res_id_list, action = [], False
        if not isinstance(mk_instance_ids, list):
            mk_instance_ids = [mk_instance_ids]
        for mk_instance_id in mk_instance_ids:
            shopify_order_list = []
            mk_instance_id.connection_to_shopify()
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
            if not from_date:
                from_date = mk_instance_id.last_order_sync_date if mk_instance_id.last_order_sync_date else fields.Datetime.now() - timedelta(3)
            if not to_date:
                to_date = fields.Datetime.now()
            from_date = from_date - timedelta(minutes=10)
            shopify_fulfillment_status_ids = mk_instance_id.fulfillment_status_ids
            if mk_order_id:
                try:
                    # Task: T8975 - Fetch the given orders 250 at a time instead of one call per order.
                    shopify_order_ids = []
                    for order_id in ''.join(mk_order_id.split()).split(','):
                        shopify_order_id = f"gid://shopify/Order/{order_id}"
                        if order_id and shopify_order_id not in shopify_order_ids:
                            shopify_order_ids.append(shopify_order_id)

                    for batch_order_ids in tools.split_every(250, shopify_order_ids, piece_maker=list):
                        variables = {"ids": batch_order_ids}
                        res = mk_instance_id.execute_graphql_query(GET_ORDERS_BY_IDS, variables)
                        user_errors = res.get('errors', [])
                        if user_errors and isinstance(user_errors, list):
                            err_messages = [e.get('message', str(e)) for e in user_errors]
                            joined_errors = ", ".join(err_messages)
                            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

                        batch_order_list = res.get('data', {}).get('nodes', []) if res.get('data', {}) else []
                        for order_vals in batch_order_list:
                            if order_vals:
                                shopify_order_list.append(order_vals)
                except ResourceNotFound as e:
                    raise MarketplaceException(e.args, f'{e.response.code} - {e.response.msg}')
                except MarketplaceException:
                    raise
                except Exception as e:
                    log_message = f"IMPORT ORDER: Error while import order to Odoo. ERROR: {e}"
                    raise MarketplaceException(log_message, e, additional_context={'show_traceback': True})
                res_id_list = self.with_context(mk_log_id=mk_log_id).import_shopify_order_by_id(shopify_order_list, mk_instance_id)
                if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
                    mk_log_id.unlink()
                self.env.cr.commit()
                if res_id_list:
                    return mk_instance_id.action_open_model_view(res_id_list, 'sale.order', 'Shopify Order')
                if mk_log_id.exists():
                    return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
                return True
            shopify_order_list = self.fetch_orders_from_shopify(from_date, to_date, mk_instance_id, shopify_fulfillment_status_ids)
            if shopify_order_list:
                # Task: T8437 - Merge returns into order payloads so each queue line processes its order and returns together.
                self._merge_shopify_returns_into_order_list(shopify_order_list, mk_instance_id, from_date, to_date, shopify_fulfillment_status_ids, mk_log_id)
                res_id_list = self.create_shopify_order_queue_job(mk_instance_id, shopify_order_list)
            if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
                mk_log_id.unlink()
            mk_instance_id.last_order_sync_date = to_date
        if res_id_list:
            action = mk_instance_id.action_open_model_view(res_id_list, 'mk.queue.job', 'Shopify Order Queue')
        return action

    def update_shopify_order_line_location(self, shopify_order_dict):
        """
        Task T7767 - Update Shopify fulfillment location details on Odoo order lines.
        Maps the Shopify fulfillment location to the related sale order line and stores fulfillment split details when the same product is fulfilled
        from multiple Shopify locations.
        """
        for order_line_dict in shopify_order_dict.get('lineItems').get('nodes', {}):
            location_id = order_line_dict.get('location_id')
            mk_id = str(extract_numeric_id(order_line_dict.get('id')))
            order_line_id = self.order_line.search([('mk_id', '=', mk_id)])
            if order_line_id and location_id:
                shopify_location_id = self.get_odoo_shopify_location_from_id(location_id)
                if shopify_location_id:
                    order_line_id.shopify_location_id = shopify_location_id.id
                shopify_splits = order_line_dict.get('shopify_fulfillment_splits') or []
                if shopify_splits:
                    order_line_id.shopify_fulfillment_locations = self._build_shopify_fulfillment_splits(order_line_dict)
        return True

    def get_shopify_pickings(self, mk_instance_id):
        picking_ids = self.env["stock.picking"].search([('updated_in_marketplace', '=', False),
                                                        ('location_dest_id.usage', '=', 'customer'),
                                                        '|',
                                                        ('mk_instance_id', '=', mk_instance_id.id),
                                                        ('backorder_id.mk_instance_id', '=', mk_instance_id.id),
                                                        ('cancel_in_marketplace', '=', False),
                                                        ('state', '=', 'done'),
                                                        ('is_marketplace_exception', '=', False)], order='create_date')
        return picking_ids

    def shopify_update_order_status(self, mk_instance_ids, manual_process=True):
        if not isinstance(mk_instance_ids, list):
            mk_instance_ids = [mk_instance_ids]
        for mk_instance_id in mk_instance_ids:
            mk_instance_id.connection_to_shopify()
            if self.env.context.get('active_model', '') == 'mk.instance':
                manual_process = False
            picking_ids = self.get_shopify_pickings(mk_instance_id)
            for picking in picking_ids:
                # Updating instance in a case if we have backorder and backorder doesn't have instance set.
                if not picking.mk_instance_id:
                    picking.write({'mk_instance_id': mk_instance_id.id})
                picking.process_update_order_status_shopify(manual_process)
        return True

    def cancel_in_shopify(self):
        view = self.env.ref('shopify.cancel_in_shopify_form_view').sudo()
        context = dict(self._context)
        context.update({'active_model': 'sale.order', 'active_id': self.id, 'active_ids': self.ids})
        return {
            'name': _('Cancel Order In Shopify'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mk.cancel.order',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }

    def refund_in_shopify(self):
        # This method is no-longer in use.
        cancel_order_wizard_obj = self.env['mk.cancel.order']
        view = self.env.ref('shopify.refund_in_shopify_form_view').sudo()
        context = dict(self._context)
        context.update({'active_model': 'sale.order', 'active_id': self.id, 'active_ids': self.ids})
        wizard_vals = cancel_order_wizard_obj.shopify_refund_wizard_default_get(self)
        res_id = cancel_order_wizard_obj.create(wizard_vals)
        return {
            'name': _('Refund Order In Shopify'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mk.cancel.order',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': res_id.id,
            'context': context
        }

    def cron_auto_import_shopify_orders(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self.shopify_import_orders(mk_instance_id)
        return True

    def cron_auto_update_order_status(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
            mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
            self.with_context(mk_log_line_dict=mk_log_line_dict, mk_log_id=mk_log_id).shopify_update_order_status(mk_instance_id, manual_process=False)
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
            if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
                mk_log_id.unlink()
        return True

    def shopify_open_sale_order_in_marketplace(self):
        marketplace_url = self.mk_instance_id.shop_url + '/admin/orders/' + self.mk_id
        return marketplace_url

    def shopify_reconcile_invoice(self, order_workflow_id, invoice_id, transaction):
        """
        Task: T6660 - Add the Shopify Payment ID to the Payment Description.
        """
        amount = 0.0
        if transaction and isinstance(transaction, dict):
            amount = self._get_currency_based_on_instance_configuration(self.mk_instance_id, transaction.get('amountSet'))
        if invoice_id.amount_residual < amount:
            amount = invoice_id.amount_residual
        payment_vals = self.with_context(transaction=transaction)._prepare_payment_vals(order_workflow_id, invoice_id, amount=amount)
        payment_id = transaction and transaction.get('paymentId', '')
        payment = self.env['account.payment'].create(payment_vals)
        payment_reference = payment.memo
        if payment_id and payment:
            if payment_reference:
                payment_id = payment_reference + f' - {payment_id}'
            payment.write({'memo': payment_id})
        payment.action_post()
        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        lines = (counterpart_lines + invoice_id.line_ids.filtered(lambda line: line.account_type == 'asset_receivable'))
        source_balance = abs(sum(lines.mapped('amount_residual')))
        payment_balance = abs(sum(counterpart_lines.mapped('balance')))
        delta_balance = source_balance - payment_balance

        # Balance are already the same.
        if not invoice_id.company_currency_id.is_zero(delta_balance):
            lines.reconcile()

    def shopify_pay_and_reconcile(self, order_workflow_id, invoice_id):
        shopify_order_dict = self.env.context.get('order_dict', {})
        transactions = shopify_order_dict.get('transactions', {})

        if not transactions:
            self.mk_instance_id.connection_to_shopify()
            variable = {"orderId": f"gid://shopify/Order/{self.mk_id}"}
            response = self.mk_instance_id.execute_graphql_query(GET_TRANSACTION_BY_ORDER_ID, variable)
            transactions = response.get('data', {}).get('order', {}).get('transactions', []) if isinstance(response, dict) else {}

        if transactions:
            for transaction in transactions:
                kind = transaction.get('kind', '')
                if kind in ['CAPTURE', 'SALE'] and transaction.get('status') == 'SUCCESS':
                    financial_status = shopify_order_dict.get('displayFinancialStatus', self.shopify_financial_status)
                    payment_gateway = transaction.get('gateway', 'Untitled') or 'Untitled'
                    shopify_payment_gateway_id = self.env['shopify.payment.gateway.ts'].search([('code', '=', payment_gateway), ('mk_instance_id', '=', self.mk_instance_id.id)],
                                                                                               limit=1)
                    financial_workflow_config_id = self.env['shopify.financial.workflow.config'].search(
                        ['|', ('financial_status', '=', financial_status), ('financial_status', '=', 'ANY'), ('mk_instance_id', '=', self.mk_instance_id.id),
                         ('payment_gateway_id', '=', shopify_payment_gateway_id.id)], limit=1)

                    if not financial_workflow_config_id:
                        mk_log_id = self.env.context.get('mk_log_id', False)
                        queue_line_id = self.env.context.get('queue_line_id', False)
                        log_message = _(
                            "IMPORT ORDER: Financial Workflow Configuration not found for Shopify Order %s (%s). Please configure the order workflow under the Workflow tab with Payment "
                            "Gateway %s and Financial Status %s in Instance Configuration (Marketplaces > Configuration > Instance).") % (
                                          shopify_order_dict.get('name'), str(extract_numeric_id(shopify_order_dict.get('id'))),
                                          shopify_payment_gateway_id.name, financial_status
                                      )

                        if mk_log_id:
                            self.env['mk.log'].create_update_log(mk_instance_id=self.mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [
                                {'log_message': log_message, 'payment_gateway_id': shopify_payment_gateway_id.id, 'financial_status': financial_status,
                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                            raise MarketplaceException(log_message)
                    self.shopify_reconcile_invoice(financial_workflow_config_id.order_workflow_id, invoice_id, transaction)
        else:
            self.shopify_reconcile_invoice(order_workflow_id, invoice_id, {})
        return True

    def shopify_get_order_fulfillment_status(self):
        return True if self.fulfillment_status == 'FULFILLED' else False

    def _force_set_quantity_done(self, fulfillment, picking):
        if not picking:
            return False
        process, processed_stock_move = False, self.env['stock.move']
        queue_line_id = self.env.context.get('queue_line_id', False)
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        for fulfillment_line in fulfillment.get('fulfillmentLineItems', {}).get('nodes', []):
            item_id = fulfillment_line.get('lineItem', {}) and str(extract_numeric_id(fulfillment_line.get('lineItem', {}).get('id', '')))
            order_line = self.order_line.filtered(lambda x: x.mk_id == item_id)
            if order_line.product_uom_qty == order_line.qty_delivered:
                continue
            mrp_installed = self.mk_instance_id._is_module_installed('mrp')
            product_id = order_line.product_id
            bom_lines = False
            to_fulfill_quantity = float(fulfillment_line.get('quantity'))
            if mrp_installed:
                bom = self.env['mrp.bom'].sudo()._bom_find(product_id, company_id=self.company_id.id, bom_type='phantom')[product_id]
                if bom:
                    factor = product_id.uom_id._compute_quantity(to_fulfill_quantity, bom.product_uom_id) / bom.product_qty
                    boms, bom_lines = bom.sudo().explode(product_id, factor, picking_type=bom.picking_type_id)
            if bom_lines:
                for bom_line, line_data in bom_lines:
                    stock_move = picking.move_ids.filtered(lambda x: x.sale_line_id.id == order_line.id and x.product_id == bom_line.product_id)
                    if stock_move:
                        stock_move._action_assign()
                        stock_move._set_quantity_done(line_data['qty'])
                        process = True
                        processed_stock_move |= stock_move
            else:
                stock_move = picking.move_ids.filtered(lambda x: x.sale_line_id.id == order_line.id)
                if stock_move:
                    stock_move._action_assign()
                    stock_move._set_quantity_done(min(to_fulfill_quantity, stock_move.product_uom_qty))
                    process = True
                    processed_stock_move |= stock_move
            if process:
                log_message = _("UPDATE ORDER STATUS IN ODOO: Product %s with %s Quantity successfully shipped in Odoo for Sale Order %s and Delivery Order %s.") % (
                    product_id.display_name, to_fulfill_quantity, self.name, picking.name)
                mk_log_line_dict['success'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False})

        remaining_stock_moves = picking.move_ids - processed_stock_move
        remaining_stock_moves.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).quantity = 0
        return process

    def _update_delivery_order_detail_shopify(self, fulfillment, picking_id):
        tracking_ref_list = []
        shopify_fulfillment_id = str(extract_numeric_id(fulfillment.get('id', '')))
        carrier_id = None
        for tracking_info in fulfillment.get('trackingInfo', []):
            if tracking_info.get('number'):
                tracking_ref_list.append(tracking_info.get('number'))
            if not carrier_id and tracking_info.get('company'):
                # T6806 - Apply country-based filtering for delivery carriers, prioritizing matches by destination country when carrier codes are shared.
                country_id = self.partner_shipping_id.country_id
                carrier_id = self.get_shopify_delivery_method(tracking_info.get('company'), self.mk_instance_id, country_id.id, country_id.code or '')

        tracking_ref = tracking_ref_list and ','.join(tracking_ref_list) or False

        picking_vals = {'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False}
        if picking_id and picking_id.sale_id_is_pickup_order:
            picking_vals.update({'is_picked_up_in_marketplace': True})
        if carrier_id:
            picking_vals.update({'carrier_id': carrier_id.id})

        if not picking_id.carrier_tracking_ref and tracking_ref:
            picking_vals.update({
                'carrier_tracking_ref': tracking_ref,
                'shopify_fulfillment_id': shopify_fulfillment_id
            })
        picking_id.write(picking_vals)
        return picking_id

    def _get_fulfillment_line_item_mk_ids(self, fulfillment):
        """
        Return the set of Shopify line item numeric IDs present in a fulfillment.
        Used to match a fulfillment against an existing done picking by inspecting
        which order lines the picking's stock moves belong to.

        :param dict fulfillment: Single fulfillment dict from Shopify order data.
        :return: Set of string Shopify line item IDs.
        :rtype: set
        """
        mk_ids = set()
        for fulfillment_line in fulfillment.get('fulfillmentLineItems', {}).get('nodes', []):
            item_id = fulfillment_line.get('lineItem', {}) and fulfillment_line.get('lineItem', {}).get('id', '')
            numeric = item_id and extract_numeric_id(item_id)
            if numeric:
                mk_ids.add(str(numeric))
        return mk_ids

    def _match_and_update_done_picking_from_fulfillment(self, fulfillment):
        """
        Find an already-validated (done) outgoing picking that corresponds to the
        given Shopify fulfillment, based on matching order line mk_ids.

        This covers the case where the user validated the picking in Odoo first,
        then fulfilled the order in Shopify and re-imported it. In that scenario
        the picking is in state 'done' but has no shopify_fulfillment_id yet and
        updated_in_marketplace is still False — so the 'Update In Marketplace'
        button is incorrectly visible.

        :param dict fulfillment: Single fulfillment dict from Shopify order data.
        :return: Matching done picking recordset, or empty recordset.
        :rtype: stock.picking
        """
        stock_picking_obj = self.env['stock.picking']
        fulfillment_mk_ids = self._get_fulfillment_line_item_mk_ids(fulfillment)
        if not fulfillment_mk_ids:
            return self.env['stock.picking']

        done_outgoing_picking_ids = self.picking_ids.filtered(
            lambda p: p.location_dest_id.usage == 'customer' and p.state == 'done' and (not p.updated_in_marketplace or not p.is_picked_up_in_marketplace))
        for picking_id in done_outgoing_picking_ids:
            picking_mk_ids = {move.sale_line_id.mk_id for move in picking_id.move_ids if move.sale_line_id and move.sale_line_id.mk_id}
            if fulfillment_mk_ids & picking_mk_ids:
                # return picking_id
                self._update_delivery_order_detail_shopify(fulfillment, picking_id)
        return stock_picking_obj

    def auto_validate_shopify_delivery_order(self, fulfillments):
        """
        Auto validate Shopify delivery orders.
        :param fulfillments: List of Shopify fulfillments.
        """
        # Get the context variables.
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})

        # Validate each fulfillment.
        for fulfillment in fulfillments:
            shopify_fulfillment_id = str(extract_numeric_id(fulfillment.get('id', '')))
            if shopify_fulfillment_id in self.picking_ids.mapped('shopify_fulfillment_id'):
                continue

            self._match_and_update_done_picking_from_fulfillment(fulfillment)

            # Get the pickings for the fulfillment.
            picking_ids = self.picking_ids.filtered(lambda p: p.location_dest_id.usage == "customer" and p.state in ['confirmed', 'assigned'])
            for picking_id in picking_ids:
                picking_id = picking_id.sudo()

                # Quality check validation.
                if hasattr(picking_id, "quality_check_todo"):
                    if getattr(picking_id, "quality_check_todo") or getattr(picking_id, "check_ids"):
                        log_message = _(
                            "UPDATE ORDER STATUS IN ODOO: Cannot auto fulfill Shopify Order %s, ERROR: %s Failed Due To Open Quality Checks For Delivery Order. Please check quality manually.") % (
                                          self.name, picking_id.name)
                        self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_log_line_dict={
                            'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                        continue

                # Force the quantity done for the fulfillment.
                process = self.with_context(mk_log_line_dict=mk_log_line_dict, queue_line_id=queue_line_id, mk_log_id=mk_log_id)._force_set_quantity_done(fulfillment, picking_id)
                if not process:
                    continue

                # Validate the picking.
                self._update_delivery_order_detail_shopify(fulfillment, picking_id)
                res = picking_id.sudo().with_context(skip_sms=True, fulfillment_status=fulfillment.get('status', '')).button_validate()
                if isinstance(res, dict):
                    if res.get('res_model', False):
                        record = self.env[res.get('res_model')].sudo().with_context(res.get("context")).create({})
                        record.process()
        return True

    def _get_move_raw_values_ts(self, product, quantity, product_uom, location_id, location_dest_id, order_line, bom_line):
        """
        Task T7767 - Override stock move values to assign the source location based on the Shopify fulfillment split location.
        When processing Shopify orders fulfilled from multiple locations, use the split-specific stock location from context so stock moves
        are created from the correct warehouse/location in Odoo. Otherwise, fallback to the order line's mapped Shopify location.
        """
        res = super(SaleOrder, self)._get_move_raw_values_ts(product, quantity, product_uom, location_id, location_dest_id, order_line, bom_line)
        shopify_split_loc_id = self.env.context.get('shopify_split_location_id')
        if shopify_split_loc_id:
            shopify_location_id = self.env['shopify.location.ts'].browse(shopify_split_loc_id)
            if shopify_location_id.exists() and shopify_location_id.location_id:
                res.update({'location_id': shopify_location_id.location_id.id})
        elif order_line.shopify_location_id.location_id:
            res.update({'location_id': order_line.shopify_location_id.location_id.id})
        return res

    def _process_stock_moves(self, sale_line, quantity, location_dest_id, location_id, bom_lines):
        """
        Task T7767 - Override orphan stock-move creation for Shopify fulfilled orders
        where the same product is fulfilled from multiple locations.

        Creates separate stock moves per Shopify fulfillment split so stock
        movements in Odoo reflect the actual fulfillment warehouse/location
        used in Shopify. Single-location fulfillments follow the standard flow.
        """
        fulfilled_splits = sale_line._get_shopify_fulfillment_splits('fulfilled')
        all_splits = sale_line._get_shopify_fulfillment_splits()
        if not fulfilled_splits or not sale_line._has_shopify_multi_warehouse_splits(all_splits):
            return super()._process_stock_moves(sale_line, quantity, location_dest_id, location_id, bom_lines)
        for split in fulfilled_splits:
            split_qty = split.get('qty', 0)
            shopify_location_record_id = split.get('shopify_location_record_id')
            if split_qty <= 0 or not shopify_location_record_id:
                continue
            super(SaleOrder, self.with_context(shopify_split_location_id=shopify_location_record_id))._process_stock_moves(sale_line, split_qty, location_dest_id, location_id,
                                                                                                                           bom_lines)
        return True

    def _get_invoiceable_lines(self, final=False):
        invoiceable_lines = super()._get_invoiceable_lines(final=final)

        # Filter and get the valid invoiceable lines
        return self._filter_valid_invoiceable_lines(invoiceable_lines)

    def _filter_valid_invoiceable_lines(self, invoiceable_lines):
        """
        Filters out invoiceable lines based on certain conditions:
        - Excludes lines with the 'adjustment' product.
        - Excludes discount product lines not in the related discount sale lines.

        :param invoiceable_lines: Recordset of invoiceable lines to filter.
        :return: Recordset of valid invoiceable lines.
        """
        if not self.mk_instance_id:
            return invoiceable_lines

        if self.mk_instance_id.is_create_single_invoice:
            return invoiceable_lines

        valid_invoiceable_lines = self.env['sale.order.line']
        adjustment_product_id = self.env.ref('base_marketplace.marketplace_adjustment_product', False)
        related_disc_line_ids = invoiceable_lines.mapped('related_disc_sale_line_id')
        discount_product_id = invoiceable_lines.order_id.mk_instance_id.discount_product_id

        for invoiceable_line in invoiceable_lines:
            if invoiceable_line.product_id == adjustment_product_id:
                continue
            if invoiceable_line.product_id == discount_product_id:
                if not invoiceable_line in related_disc_line_ids:
                    continue
            valid_invoiceable_lines |= invoiceable_line

        return valid_invoiceable_lines

    def _update_remaining_amount(self, payment_detail_ids, parent_transaction_id, refunded_amount, refund_move_amount):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        To update the refund and remaining amounts correctly, use the parent transaction ID to identify the corresponding payment transaction.

        Update the remaining amount on successful refund transactions.
        :param payment_detail_ids: Recordset of existing payment details.
        :param gateway_id: Record of the payment gateway used.
        :param refunded_amount: Amount refunded in the transaction.
        """
        for payment in payment_detail_ids:
            if payment.parent_transaction_id == parent_transaction_id:
                remaining_amount = (payment.remaining_amount or payment.total_amount) - float(refunded_amount)
                payment.write({'remaining_amount': remaining_amount,
                               'refund_amount': min(refund_move_amount, remaining_amount)})
                break  # Stop the loop once we find and update the correct payment_gateway_id
        return payment_detail_ids

    def fetch_shopify_transactions_details(self, refund_move_amount):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        To update the refund and remaining amounts correctly, use the parent transaction ID to identify the corresponding payment transaction.

        Fetch Shopify transactions for the given order and create payment details in Odoo.
        :return: Recordset of created or updated payment details.
        """
        # Fetch transactions from Shopify and initialize an empty recordset
        odoo_order_currency_name = self.env.context.get('currency_name', '')
        variables = {"orderId": f"gid://shopify/Order/{self.mk_id}"}
        response = self.mk_instance_id.execute_graphql_query(GET_TRANSACTION_BY_ORDER_ID, variables)
        order_data = response and response.get('data', {}) and response.get('data', {}).get('order', {})
        transactions = order_data and order_data.get('transactions', {}) or []
        payment_detail_ids = self.env["shopify.order.payment"]

        # Process each transaction and update/create payment details
        for transaction in transactions:
            transaction_type = transaction.get('transaction', {}).get('kind') or transaction.get('kind')
            transaction_status = transaction.get('transaction', {}).get('status', '') or transaction.get('status', '')
            gateway_name = transaction.get('gateway', 'Untitled') or 'Untitled'
            payment_gateway_id = self.env['shopify.payment.gateway.ts'].search([('code', '=', gateway_name), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
            shopify_order_currency = transaction.get('amountSet', {}).get('presentmentMoney', {}).get('currencyCode', '')
            if transaction_status == 'SUCCESS':

                if transaction_type in ['SALE', 'CAPTURE', 'REFUND'] and shopify_order_currency != odoo_order_currency_name:
                    raise MarketplaceException(
                        f"- Refund cannot be processed because the Odoo order currency does not match the Shopify transaction currency.\n"
                        f"- Odoo order Currency: {odoo_order_currency_name} | Shopify order Currency: {shopify_order_currency}\n"
                        f"- Please process this refund manually from your Shopify store."
                    )
                if transaction_type in ['SALE', 'CAPTURE']:
                    payment_detail_ids |= self._create_sale_transaction(payment_detail_ids, payment_gateway_id, transaction, refund_move_amount)
                elif transaction_type == 'REFUND':
                    parent_transaction = transaction.get('parentTransaction')
                    if not parent_transaction:
                        continue
                    parent_transaction_id = str(extract_numeric_id(parent_transaction.get('id'))) if parent_transaction.get('id') else ''
                    refunded_amount = self._get_currency_based_on_instance_configuration(self.mk_instance_id, transaction.get('amountSet', {}))
                    self._update_remaining_amount(payment_detail_ids, parent_transaction_id, refunded_amount, refund_move_amount)

        return payment_detail_ids

    def _create_sale_transaction(self, payment_detail_ids, payment_gateway, transaction_data, refund_move_amount):
        """Create a sale transaction entry in payment details.

        :param payment_detail_ids: Recordset of existing payment details.
        :param payment_gateway: Record of the payment gateway used.
        :param transaction_data: Transaction data dictionary.
        :return: Newly created payment detail record.
        """
        total_amount = self._get_currency_based_on_instance_configuration(self.mk_instance_id, transaction_data.get('amountSet', {})) or 0.0
        refund_amount = min(round(refund_move_amount, 2), round(total_amount, 2))
        return payment_detail_ids.create({
            'payment_gateway_id': payment_gateway.id,
            'total_amount': total_amount,
            'parent_transaction_id': extract_numeric_id(transaction_data.get('id')),
            'remaining_amount': total_amount,
            'refund_amount': refund_amount,
        })

    def prepare_shopify_refund_data(self, credit_note_id, shopify_order_payment_ids, is_notify_customer, refund_description):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        Prepare the refund payload for Shopify using transaction-based logic (no line items).
        """
        transaction_list = []
        order_ID = f"gid://shopify/Order/{self.mk_id}"
        for shopify_payment in shopify_order_payment_ids:
            numeric_id = shopify_payment.parent_transaction_id
            transaction_list.append({
                'parentId': f'gid://shopify/OrderTransaction/{numeric_id}' if numeric_id else None,
                'amount': shopify_payment.refund_amount,
                'kind': 'REFUND',
                'orderId': order_ID,
                'gateway': shopify_payment.payment_gateway_id.code
            })
        return {
            'notify': is_notify_customer,
            'note': refund_description or '',
            'currency': self.currency_id.name,
            'orderId': f"gid://shopify/Order/{self.mk_id}",
            'transactions': transaction_list,
        }

    def post_shopify_refund_update(self, total_refund_amount, response):
        shopify_order = response.get('data', {}).get('refundCreate', {}).get('order', {})
        financial_status = shopify_order.get('displayFinancialStatus')

        self.write({'shopify_financial_status': financial_status})
        body = Markup(_("This order has been refunded in Shopify for an amount of <b>%s</b>") % total_refund_amount)
        self.message_post(body=body)

    def pay_and_reconcile(self, order_workflow_id, invoice_id):
        """
        Add context for not mark as paid order in shopify if we are processing invoice from order workflow.
        Args:
            order_workflow_id (recordset): Recordset of the workflow triggering the payment.
            invoice_id (recordset): Recordset of the invoice being paid and reconciled.
        """
        res = super(SaleOrder, self.with_context(is_register_from_order_workflow=True)).pay_and_reconcile(order_workflow_id=order_workflow_id, invoice_id=invoice_id)
        return res

    def mark_order_as_paid(self):
        """
        Marks a Shopify order as paid.

        Returns:
            Returns true if not any error Otherwise print error.
        """
        self.mk_instance_id.connection_to_shopify()
        variables = {"input": {"id": f"gid://shopify/Order/{self.mk_id}"}}

        response = self.mk_instance_id.execute_graphql_query(MARK_ORDER_AS_PAID, variables)
        error = response and response.get('errors', [])
        if error and isinstance(error, list):
            err_messages = [e.get('message', str(e)) for e in error]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to Mark the order as paid.: %(errors)s") % {'errors': joined_errors})

        user_data = response and response.get('data', {})
        order_mark_as_paid = user_data and user_data.get('orderMarkAsPaid', {})
        user_error = order_mark_as_paid and order_mark_as_paid.get('userErrors', {})
        if response and not user_error:
            self.write({'shopify_financial_status': 'PAID'})
            body = Markup(_("✅ The order has been marked as paid in Shopify."))
            self.message_post(body=body)
        elif response and user_error:
            financial_status = response.get("data", {}).get("orderMarkAsPaid", {}).get("order", {}).get("displayFinancialStatus", "")
            if financial_status == "PAID": self.write({'shopify_financial_status': 'PAID'})
            body = Markup(_("⚠️ There was a error while marking the order as paid.<br><b>ERROR:</b> %s") % user_error[0].get('message'))
            self.message_post(body=body)
        return True

    def should_mark_shopify_order_paid(self):
        """
        Determines whether the Shopify order should be marked as paid.

        Returns:
            bool: True if the order should be marked as paid on Shopify, False otherwise.
        """
        PAYMENT_STATE = ('paid', 'in_payment')
        SHOPIFY_PAYMENT_STATE = ('PAID', 'REFUNDED', 'PARTIALLY_REFUNDED', 'VOIDED')

        incomplete_payment_invoice_ids = self.invoice_ids.filtered(lambda x: x.payment_state not in PAYMENT_STATE and x.move_type == 'out_invoice')
        is_fully_invoiced = self.invoice_status == 'invoiced'
        return (
                not incomplete_payment_invoice_ids
                and is_fully_invoiced
                and self.mk_id
                and self.shopify_financial_status not in SHOPIFY_PAYMENT_STATE
                and self.mk_instance_id.marketplace == 'shopify'
        )

    def shopify_authorized_order_mark_as_paid(self):
        """
        Task: T7487 - This method marks a Shopify order as paid by capturing an existing authorized transaction.
        Returns:
                - True: If the order is successfully marked as paid.
                - False: If no valid transaction is found to process.
        Raises:
            MarketplaceException: If the GraphQL request fails or returns errors during payment capture.
        """
        order_id = self.mk_id
        transactions = self.transaction_ids
        if not transactions:
            self.mk_instance_id.connection_to_shopify()
            variable = {"orderId": f"gid://shopify/Order/{order_id}"}
            response = self.mk_instance_id.execute_graphql_query(GET_TRANSACTION_BY_ORDER_ID, variable)
            transactions = response and response.get('data', {}) and response.get('data', {}).get('order', {}) and response.get('data', {}).get('order', {}).get('transactions',
                                                                                                                                                                 []) if isinstance(
                response, dict) else {}
            if transactions:
                for transaction in transactions:
                    kind = transaction.get('kind', '')
                    if kind in ['AUTHORIZATION'] and transaction.get('status') == 'SUCCESS':
                        transaction_id = transaction.get('id', '')
                        amount_dict = transaction.get('amountSet', {})
                        if amount_dict and transaction_id:
                            amount = float(amount_dict.get('presentmentMoney', {}).get('amount', 0.0)) or 0.0
                            currency = amount_dict.get('presentmentMoney', {}).get('currencyCode', '')
                            variables = {"input": {"id": f"gid://shopify/Order/{order_id}", "parentTransactionId": transaction_id, "amount": f"{amount}", "currency": currency}}
                            res = self.mk_instance_id.execute_graphql_query(GET_MARK_AS_PAID_AUTHORIZE_CAPTURE_PAYMENT, variables)
                            error = res and res.get('errors', [])
                            if error and isinstance(error, list):
                                err_messages = [e.get('message', str(e)) for e in error]
                                joined_errors = ", ".join(err_messages)
                                raise MarketplaceException(f"⚠️ Failed to Mark the order as paid.: {joined_errors}")
                            user_data = res and res.get('data', {})
                            order_mark_as_paid = user_data and user_data.get('orderCapture', {})
                            user_error = order_mark_as_paid and order_mark_as_paid.get('userErrors', {})
                            if res and not user_error:
                                financial_status = order_mark_as_paid.get('transaction', {}) and order_mark_as_paid.get('transaction', {}).get('order',
                                                                                                                                               {}) and order_mark_as_paid.get(
                                    'transaction', {}).get('order', {}).get('displayFinancialStatus', '')
                                self.write({'shopify_financial_status': financial_status})
                                body = Markup(_(f"✅ The order has been marked as paid in Shopify."))
                                self.message_post(body=body)
                            elif res and user_error:
                                body = Markup(_(f"⚠️ There was a error while marking the order as paid.<br><b>ERROR:</b> {user_error[0].get('message')}"))
                                self.message_post(body=body)
                return True
            if not transactions:
                return False

    def process_shopify_order_payment_status(self):
        """
        Checks whether the Shopify order should be marked as paid, and if so, triggers the mark order as paid process.
        Task: T7487 - This method marks a Shopify order as paid by capturing an existing authorized transaction.
        Returns:
            bool: Always returns True, regardless of whether the order was marked as paid.
        """
        self = self.sudo()
        if self.should_mark_shopify_order_paid():
            if self.shopify_financial_status == 'AUTHORIZED':
                self.shopify_authorized_order_mark_as_paid()
            else:
                self.mark_order_as_paid()
        return True

    def import_order_metafield_from_shopify(self, mk_instance_id, shopify_order_dict, mk_id, mk_log_id=False, queue_line_id=False):
        """
        T6293 - This method imports Shopify order metafields into Odoo.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            shopify_order_dict (dict): Shopify order response data.
            mk_id (str): Shopify order ID.
            mk_log_id (recordset):  Recordset of mk.log.
            queue_line_id (recordset):  Recordset of mk.queue.job.line.
        Returns:
            bool: Returns True after processing the order metafields.
        """
        self.ensure_one()
        if not (mk_instance_id.enable_metafield and mk_instance_id.metafield_resource_ids.filtered(lambda r: r.active_sync and r.shopify_owner_type == 'ORDER')):
            return True

        metafield_res = (shopify_order_dict.get('metafields') or {}).get('nodes') or []

        new_log = False
        if not mk_log_id:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
            new_log = True
        mk_log_line_dict = {'error': [], 'success': []}

        try:
            mk_instance_id.import_specific_type_metafield_from_shopify(
                target_odoo_record=self,
                shopify_owner_type='ORDER',
                metafields_list=metafield_res,
                reference_handler_func=mk_instance_id.set_shopify_reference_metafield_value,
                mk_log_line_dict=mk_log_line_dict,
                wipe_unmatched=True,
                queue_line_id=queue_line_id,
                mk_log_id=mk_log_id,
                mk_id=mk_id
            )
        except Exception as e:
            mk_log_line_dict['error'].append({
                'log_message': f"IMPORT ORDER: Failed to update metafields for Order {self.name} ({mk_id}): {e}",
                'queue_job_line_id': queue_line_id.id if queue_line_id else False,
            })
        finally:
            self.env['mk.log'].create_update_log(
                mk_log_id=mk_log_id, mk_instance_id=mk_instance_id,
                operation_type='import', mk_log_line_dict=mk_log_line_dict,
            )
            if new_log and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    SHOPIFY_FULFILLMENT_ORDER_DONE_STATES = ('SUCCESS', 'CLOSED')
    SHOPIFY_FULFILLMENT_ORDER_PENDING_STATES = ('OPEN', 'PENDING', 'IN_PROGRESS')

    shopify_location_id = fields.Many2one("shopify.location.ts", "Shopify Location", copy=False)
    shopify_fulfillment_locations = fields.Json("Shopify Fulfillment Splits", copy=False)

    def _get_shopify_fulfillment_splits(self, status_group=None):
        """
        Task T7767 - Override procurement values to assign the warehouse based on the Shopify fulfillment location.
        When a Shopify order line is linked with a mapped Shopify location, use the related warehouse so the delivery order and stock operations
        are created from the correct warehouse in Odoo.
        """
        self.ensure_one()
        splits = self.shopify_fulfillment_locations or []
        if status_group == 'fulfilled':
            return [s for s in splits if s.get('fulfillment_order_status') in self.SHOPIFY_FULFILLMENT_ORDER_DONE_STATES]
        if status_group == 'unfulfilled':
            return [s for s in splits if s.get('fulfillment_order_status') in self.SHOPIFY_FULFILLMENT_ORDER_PENDING_STATES]
        return splits

    def _prepare_procurement_values(self):
        """
        Override the base method to customize procurement values. Set warehouse according to the Shopify Order to create a delivery order based on the warehouse.
        """
        values = super()._prepare_procurement_values()
        if self.shopify_location_id and self.shopify_location_id.order_warehouse_id:
            values.update({
                'warehouse_id': self.shopify_location_id.order_warehouse_id,
            })
        return values

    def _get_shopify_active_fulfillment_splits(self):
        """
        Task T7767 - Get the active Shopify fulfillment splits to use for stock operations by preferring unfulfilled splits and falling back
        to fulfilled splits when required.
        """
        self.ensure_one()
        unfulfilled_splits = self._get_shopify_fulfillment_splits('unfulfilled')
        fulfilled_splits = self._get_shopify_fulfillment_splits('fulfilled')
        if unfulfilled_splits and fulfilled_splits:
            return unfulfilled_splits + fulfilled_splits
        return unfulfilled_splits or fulfilled_splits

    def _has_shopify_multi_warehouse_splits(self, splits):
        """
        Task T7767 - Check whether Shopify fulfillment splits belong to multiple warehouses so separate delivery operations are required.
        """
        self.ensure_one()
        if len(splits) <= 1:
            return False
        warehouse_ids = set()
        for split in splits:
            shopify_location_id = self.env['shopify.location.ts'].browse(split.get('shopify_location_record_id'))
            if shopify_location_id.exists() and shopify_location_id.order_warehouse_id:
                warehouse_ids.add(shopify_location_id.order_warehouse_id.id)
        return len(warehouse_ids) > 1

    def _build_shopify_split_procurements(self, active_splits):
        """
        Task T7767 - Create procurement values for each Shopify fulfillment split to generate stock operations from the correct warehouse.
        """
        self.ensure_one()
        procurements = []
        for split in active_splits:
            location = self.env['shopify.location.ts'].browse(split.get('shopify_location_record_id'))
            split_qty = split.get('qty', 0)
            if split_qty <= 0 or not location.exists() or not location.order_warehouse_id:
                continue
            values = self._prepare_procurement_values()
            values['warehouse_id'] = location.order_warehouse_id
            product_qty, procurement_uom = self.product_uom_id._adjust_uom_quantities(split_qty, self.product_id.uom_id)
            procurements += self._create_procurements(product_qty, procurement_uom, values)
        return procurements

    def _action_launch_stock_rule(self, *, previous_product_uom_qty=False):
        """
        Task T7767 - Override procurement creation for Shopify orders fulfilled from multiple locations.
        When an unfulfilled Shopify order contains fulfillment splits for the same product across different locations, create separate procurements
        per split warehouse so Odoo generates stock operations correctly. All other lines follow the standard Odoo procurement flow.
        """
        standard_lines = self.env['sale.order.line']
        shopify_split_procurements = []
        for line in self:
            active_splits = line._get_shopify_active_fulfillment_splits()
            if line._has_shopify_multi_warehouse_splits(active_splits):
                if not line.order_id.stock_reference_ids:
                    self.env['stock.reference'].create(line._prepare_reference_vals())
                shopify_split_procurements += line._build_shopify_split_procurements(active_splits)
            else:
                standard_lines |= line
        if shopify_split_procurements:
            self.env['stock.rule'].run(shopify_split_procurements)
        if standard_lines:
            return super(SaleOrderLine, standard_lines)._action_launch_stock_rule(previous_product_uom_qty=previous_product_uom_qty)
        return True
