import base64
import hashlib
import hmac
import json
import logging
import threading

import psycopg2
import requests
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.modules.registry import Registry

from odoo import api, http, SUPERUSER_ID, _
from odoo.addons.shopify.models.misc import log_traceback_for_exception, extract_numeric_id

_logger = logging.getLogger("Teqstars:Shopify")


class ShopifyWebhook(http.Controller):

    @http.route('/external/oauth/callback', type='http', auth="public", csrf=False, methods=['GET'])
    def shopify_oauth_callback(self, **kwargs):
        """
        Task 6480 - Handles the OAuth callback from Shopify.
        Redirects users back to Odoo with visual feedback (Success or Error).
        """
        auth_code = kwargs.get('code')
        received_state = kwargs.get('state')
        shop = kwargs.get('shop')

        try:
            tenant_id = self.parse_and_verify_state(received_state)
        except ValueError as e:
            return f"Security Error: {str(e)}"

        if not all([auth_code, shop]):
            return "Missing required parameters (code, shop) in Shopify callback."

        # Find instance
        if tenant_id:
            instance_id = request.env['mk.instance'].sudo().browse(int(tenant_id))
        else:
            instance_id = request.env['mk.instance'].sudo().search([('shop_url', 'ilike', shop), ('marketplace', '=', 'shopify')], limit=1)

        if not instance_id:
            return f"No Shopify instance found for shop: {shop}"

        secret = instance_id.secret_id
        client_id = instance_id.client_id
        self.verify_shopify_oauth_hmac_decoded(kwargs, secret)
        if not secret:
            return "Shopify Client Secret is not configured in Odoo."
        if not client_id:
            return "Shopify Client ID is not configured in Odoo."

        # Exchange Code for Access Token
        url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            'client_id': client_id,
            'client_secret': secret,
            'code': auth_code}

        try:
            res = requests.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            access_token = data.get('access_token')

            if access_token:
                instance_id.write({'api_token': access_token})
                # Redirect back to the instance form
                return request.redirect(f'/web#id={instance_id.id}&model=mk.instance&view_type=form')
            else:
                return f"No access token received. Response: {data}"

        except requests.exceptions.HTTPError as e:
            error_msg = f"Shopify API Error: {e.response.text}"
            _logger.exception(error_msg)
            return error_msg

        except Exception as e:
            _logger.exception("Shopify OAuth Token Exchange Failed (Unknown Error)")
            return f"Internal Error: {str(e)}"

    @http.route('/shopify/webhook/notification/<string:db_name>/<int:mk_instance_id>/<string:access_token>/', type='jsonrpc', auth="public", csrf=False)
    def shopify_webhook_process(self, db_name, mk_instance_id, access_token, **kwargs):
        """
        TASK T6079 : First, check whether the webhook type in Shopify odoo instance  is active. If it is active, process the webhook and apply Shopify changes in Odoo.
                     If the webhook is inactive in Odoo, skip processing and do not apply any changes in Odoo.
        """
        # Extract webhook type from the request headers
        webhook_type = request.httprequest.headers.get('X-Shopify-Topic', False)
        # Capture the Shopify HMAC header and the RAW request body while we are still in the
        # request context (both are needed to verify the signature inside the worker thread).
        hmac_header = request.httprequest.headers.get('X-Shopify-Hmac-Sha256', '')
        raw_body = request.httprequest.get_data() or b''
        # Extract response data from the request
        response_data = request.get_json_data() or {}

        # Create a new thread to handle the webhook processing
        if webhook_type:
            find_active_webhook_shopify = request.env['shopify.webhook.ts'].sudo().search([('mk_instance_id', '=', mk_instance_id), ('webhook_event', '=', webhook_type), ('active_webhook', '=', True), ])
            if find_active_webhook_shopify:
                order_thread = threading.Thread(target=self.create_and_process_webhook_request, args=(db_name, mk_instance_id, access_token, webhook_type, response_data, raw_body, hmac_header))
                order_thread.start()
                return {'status': 'Successfully processed.'}

    def create_and_process_webhook_request(self, db_name, mk_instance_id, access_token, webhook_type, response_data, raw_body=b'', hmac_header=''):
        try:
            # Access the database registry for the specified database
            db_registry = Registry(db_name)
            with db_registry.cursor() as cr:
                # Create a new Odoo environment
                env = api.Environment(cr, SUPERUSER_ID, {})
                mk_instance_id = env['mk.instance'].browse(int(mk_instance_id))


                # Validate the webhook request
                validated, error_message = self._validate_webhook(mk_instance_id, access_token, webhook_type, raw_body, hmac_header)
                if not validated:
                    return error_message

                response = self.transform_webhook_response(webhook_type, env, mk_instance_id, response_data) or response_data

                mk_log_id = None
                mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
                try:
                    # Create or update the log for the webhook processing
                    mk_log_id = env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='webhook')
                    # Process the webhook response
                    self.process_webhook_response(env, webhook_type, response, mk_instance_id, mk_log_id)
                except Exception as e:
                    # Handle exceptions that occur during webhook processing
                    log_traceback_for_exception()
                    self._handle_exception(env, mk_instance_id, mk_log_id, webhook_type, e)
                finally:
                    # If no log lines were created, remove the log entry
                    env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='webhook', mk_log_line_dict=mk_log_line_dict)
                    if mk_log_id and not mk_log_id.log_line_ids:
                        mk_log_id.unlink()
        except psycopg2.Error as e:
            # Log any database-related errors
            _logger.error(f"SHOPIFY WEBHOOK RECEIVE: Error while Processing webhook request. ERROR: {e}")

    def _validate_webhook(self, mk_instance_id, access_token, webhook_type, raw_body=b'', hmac_header=''):
        # Shopify HMx`AC verification (fail-closed) when the app secret is configured on the instance.
        # Shopify signs every webhook with the app's API secret; we recompute the signature over the
        # RAW body and reject on mismatch. Installs that have no secret configured (API-token only)
        # fall back to the URL token check below so existing setups keep working.
        secret = mk_instance_id.sudo().secret_id
        if secret:
            if not hmac_header:
                error_msg = "SHOPIFY WEBHOOK RECEIVE: Missing Shopify HMAC signature header."
                _logger.error(error_msg)
                return False, error_msg
            computed_hmac = base64.b64encode(hmac.new(secret.encode('utf-8'), raw_body or b'', hashlib.sha256).digest()).decode('utf-8')
            if not hmac.compare_digest(computed_hmac, hmac_header):
                error_msg = "SHOPIFY WEBHOOK RECEIVE: Invalid Shopify HMAC signature."
                _logger.error(error_msg)
                return False, error_msg
        # Validate the access token against the instance's webhook UUID
        if mk_instance_id.webhook_uuid and access_token and mk_instance_id.webhook_uuid != access_token:
            error_msg = "SHOPIFY WEBHOOK RECEIVE: Error while Processing webhook request. ERROR: Invalid Access Token"
            _logger.error(error_msg)
            return False, error_msg
        # Ensure the instance is in a confirmed state before processing
        if mk_instance_id.state != 'confirmed':
            error_msg = f'Instance {mk_instance_id.name} is not in Confirmed State.'
            _logger.warning(error_msg)
            return False, error_msg
        # Ensure the webhook event type is configured for the instance
        if not mk_instance_id.webhook_ids.filtered(lambda webhook: webhook.webhook_event == webhook_type):
            error_msg = f'Webhook Event Type {webhook_type} is not configured in Instance {mk_instance_id.name}.'
            _logger.warning(error_msg)
            return False, error_msg
        return True, "Success"

    def _handle_exception(self, env, mk_instance_id, mk_log_id, webhook_type, exception):
        # Log the exception details for the webhook processing
        log_message = "Error while processing Shopify webhook %s, ERROR: %s." % (webhook_type, exception)
        mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        mk_log_line_dict['error'].append({'log_message': 'WEBHOOK PROCESS: ' + log_message})
        # Update the log with the error information
        env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='webhook', mk_log_line_dict=mk_log_line_dict)

    def shopify_process_fulfillment(self, existing_order_id, response, mk_log_id):
        # Update the fulfillment status of the order
        fulfillment_status = response.get('displayFulfillmentStatus')
        update_order_dict = {'fulfillment_status': fulfillment_status}
        # Confirm the order if it is in draft or sent state
        if existing_order_id.state in ["draft", "sent"]:
            existing_order_id.action_confirm()
        # Automatically validate the delivery order for Shopify
        existing_order_id.with_context(operation_type='webhook', mk_log_id=mk_log_id).auto_validate_shopify_delivery_order(response.get('fulfillments'))
        # Check if all pickings have been updated in the marketplace
        if all(existing_order_id.order_line.mapped('move_ids').mapped('picking_id').mapped('updated_in_marketplace')):
            update_order_dict.update({'updated_in_marketplace': True})
        # Write the updated order information
        existing_order_id.write(update_order_dict)
        return existing_order_id

    def process_webhook_response(self, env, webhook_type, response, mk_instance_id, mk_log_id):
        mk_instance_id.connection_to_shopify()
        mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        # Define the handlers for different webhook types
        webhook_handlers = {
            'customers/create': lambda: env['res.partner'].with_context(operation_type='webhook', mk_log_line_dict=mk_log_line_dict, mk_log_id=mk_log_id).import_shopify_customer_records(response, mk_instance_id),
            'products/create': lambda: env['mk.listing'].with_context(operation_type='webhook', mk_log_line_dict=mk_log_line_dict, mk_log_id=mk_log_id).create_update_shopify_product(response, mk_instance_id, update_product_price=True),
            'products/update': lambda: self._handle_product_update(env, response, mk_instance_id, mk_log_line_dict),
            'products/delete': lambda: self._handle_product_delete(env, response, mk_instance_id, mk_log_line_dict),
            'orders/updated': lambda: self._handle_order_update(env, response, mk_instance_id, mk_log_id),
            'orders/create': lambda: self._handle_order_create(env, response, mk_instance_id, mk_log_id),
            'returns/request': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
            'returns/approve': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
            'returns/decline': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
            'returns/close': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
            'returns/reopen': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
            'returns/cancel': lambda: self._handle_return_event(env, response, mk_instance_id, mk_log_id),
        }
        # Call the appropriate handler for the webhook type
        if webhook_type in webhook_handlers:
            webhook_handlers[webhook_type]()

    def transform_webhook_response(self, webhook_type, env, mk_instance_id, response):
        webhook_handlers = {
            'customers/create': env['res.partner'].transform_customer_webhook_response_to_graphql,
            'products/create': env['mk.listing'].transform_product_webhook_response_to_graphql,
            'products/update': env['mk.listing'].transform_product_webhook_response_to_graphql,
            'orders/updated': env['sale.order'].transform_shopify_order_webhook_response_to_graphql,
            'orders/create': env['sale.order'].transform_shopify_order_webhook_response_to_graphql
        }
        # Call the appropriate handler for the webhook type
        handler = webhook_handlers.get(webhook_type, False)
        return handler(response, mk_instance_id) if handler else False

    def _handle_product_update(self, env, response, mk_instance_id, mk_log_line_dict):
        # Handle product updates by finding the corresponding listing and updating it
        mk_listing_obj = env['mk.listing']
        listing_id = mk_listing_obj.search([('mk_id', '=', response.get('legacyResourceId')), ('mk_instance_id', '=', mk_instance_id.id)])
        if listing_id:
            mk_listing_obj.with_context(operation_type='webhook', mk_log_line_dict=mk_log_line_dict).create_update_shopify_product(response, mk_instance_id, update_product_price=True,
                                                                                                         is_update_existing_products=True)

    def _handle_product_delete(self, env, response, mk_instance_id, mk_log_line_dict):
        # Handle product deletions by finding the listing and unlinking it
        mk_listing_obj = env['mk.listing']
        listing_id = mk_listing_obj.search([('mk_id', '=', response.get('id')), ('mk_instance_id', '=', mk_instance_id.id)])
        listing_name = listing_id.name
        if listing_id:
            listing_id.unlink()
            # Log the successful deletion of the listing
            log_message = _("Successfully Deleted Listing. Listing Name: %s, Listing ID: %s") % (listing_name, response.get('id'))
            mk_log_line_dict['success'].append({'log_message': 'DELETE PRODUCT: ' + log_message})

    def _handle_order_update(self, env, response, mk_instance_id, mk_log_id):
        # Handle order updates by finding the existing order and processing it
        mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        mk_id = extract_numeric_id(response.get('id'))
        existing_order_id = env['sale.order'].search([('mk_id', '=', mk_id), ('mk_instance_id', '=', mk_instance_id.id)])
        if not existing_order_id:
            _logger.warning(f"SHOPIFY WEBHOOK RECEIVE: Existing Order {mk_id} not found while process while Processing webhook request.")
            return False
        env['sale.order'].with_context(operation_type='webhook', mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict).process_import_order_from_shopify_ts(response, mk_instance_id)
        fulfillment_status = response.get('displayFulfillmentStatus')
        if fulfillment_status in ['PARTIAL', 'FULFILLED']:
            try:
                # Validate and process the Shopify order
                existing_order_id._validate_and_process_shopify_order(response)
                # Process fulfillment for the order
                self.shopify_process_fulfillment(existing_order_id, response, mk_log_id)
                # Process any refunds from Shopify
                existing_order_id.with_context(skip_check_transaction=True)._process_shopify_refund_in_odoo(response)
                # Update order tags if provided in the response
                shopify_tag_vals = existing_order_id.prepare_order_tag_vals(response.get('tags'))
                if shopify_tag_vals and response.get('tags'):
                    existing_order_id.write(shopify_tag_vals)
            except Exception as e:
                # Log any exceptions that occur during order update processing
                log_traceback_for_exception()
                self._handle_exception(env, mk_instance_id, mk_log_id, 'orders/updated', e)

    def _handle_return_event(self, env, response, mk_instance_id, mk_log_id):
        """Webhook handler for the RETURNS_* topics.

        Shopify return webhooks carry the return identifier in REST format
        (under ``id`` or ``return.id``, sometimes also ``admin_graphql_api_id``).
        Normalize to a GID then enqueue via the standard
        ``shopify.return.ts`` queue framework — same code path as the cron.
        """
        mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        return_id = response.get('id') or (response.get('return') or {}).get('id') or response.get('admin_graphql_api_id')
        if not return_id:
            mk_log_line_dict['error'].append({'log_message': f"WEBHOOK RETURN: No return id found in payload: {response}"})
            return False
        if isinstance(return_id, str) and return_id.startswith('gid://'):
            return_gid = return_id
        else:
            return_gid = f"gid://shopify/Return/{return_id}"
        try:
            env['shopify.return.ts'].enqueue_return_from_webhook(mk_instance_id, return_gid, mk_log_id=mk_log_id)
            mk_log_line_dict['success'].append({'log_message': f"WEBHOOK RETURN: Enqueued return {return_gid}."})
        except Exception as e:
            log_traceback_for_exception()
            mk_log_line_dict['error'].append({'log_message': f"WEBHOOK RETURN: Failed to enqueue {return_gid}. ERROR: {e}"})
        return True

    def _handle_order_create(self, env, response, mk_instance_id, mk_log_id):
        # Handle order creation by finding and creating the order
        mk_log_line_dict = env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        mk_id = extract_numeric_id(response.get('id'))

        existing_order_id = env['sale.order'].search([('mk_id', '=', mk_id), ('mk_instance_id', '=', mk_instance_id.id)])
        if not existing_order_id:
            existing_order_id = env['sale.order'].with_context(operation_type='webhook', mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict).process_import_order_from_shopify_ts(response, mk_instance_id)
        fulfillment_status = response.get('displayFulfillmentStatus')
        if fulfillment_status in ['PARTIAL', 'FULFILLED'] and existing_order_id:
            try:
                # Process fulfillment for the newly created order
                self.shopify_process_fulfillment(existing_order_id, response, mk_log_id)
            except Exception as e:
                # Log any exceptions that occur during order creation processing
                log_traceback_for_exception()
                self._handle_exception(env, mk_instance_id, mk_log_id, 'orders/create', e)

    def verify_shopify_oauth_hmac_decoded(self, kwargs: dict, client_secret: str):
        """
        Verify Shopify OAuth callback HMAC using DECODED query parameters.
        This avoids the %3D vs '=' issue for base64-padded values like `state`.

        Algorithm:
        - remove 'hmac' and 'signature'
        - sort by key
        - build message: key=value&key=value (NO re-encoding)
        - HMAC-SHA256(secret, message).hexdigest()
        - constant-time compare with received hmac
        """

        if not client_secret or not isinstance(client_secret, str):
            raise AccessDenied("Missing/invalid Shopify client secret (API secret key).")

        received_hmac = (kwargs.get("hmac") or "").strip()
        if not received_hmac:
            raise AccessDenied("Missing hmac parameter.")

        # Prepare items excluding hmac/signature
        items = []
        for k, v in kwargs.items():
            if k in ("hmac", "signature"):
                continue

            # Odoo usually provides scalars; be defensive
            if isinstance(v, (list, tuple)):
                v = v[0] if v else ""
            if v is None:
                v = ""

            # IMPORTANT: use decoded values exactly (no urlencode)
            items.append((str(k), str(v)))

        items.sort(key=lambda kv: kv[0])

        message = "&".join([f"{k}={v}" for k, v in items])

        computed = hmac.new(
            client_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed, received_hmac):
            _logger.warning("Shopify OAuth HMAC mismatch.")
            _logger.warning("MESSAGE (decoded): %s", message)
            _logger.warning("RECEIVED: %s", received_hmac)
            _logger.warning("COMPUTED: %s", computed)
            raise AccessDenied("Invalid HMAC in OAuth callback.")

    def parse_and_verify_state(self, state):
        """
        Task 6480 - Reverse of build_state:
        - Decode base64
        - Split payload and signature
        - Recompute HMAC and compare
        - Return tenant_id if valid
        Raise ValueError if invalid.
        """
        secret = self.env['ir.config_parameter'].sudo().get_param('shopify.oauth_signing_secret')

        try:
            # Decode base64
            combined = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
        except Exception:
            raise ValueError("Invalid state encoding")

        # Split into payload_json and signature
        try:
            payload_json, received_signature = combined.rsplit("|", 1)
        except ValueError:
            raise ValueError("Invalid state format")

        # Recompute HMAC signature
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, received_signature):
            raise ValueError("Invalid state signature")

        # Parse JSON and get tenant_id
        try:
            payload = json.loads(payload_json)
            mk_instance_id = int(payload["mk_instance_id"])
        except Exception:
            raise ValueError("Invalid state payload")

        return mk_instance_id


class ShopifyCollectionImage(http.Controller):

    @http.route(['/shopify/collections/image/<string:db_name>/<string:encodedres>',
                 '/shopify/collections/image/<string:db_name>/<string:encodedres>/<string:filename>'], type='http', auth='public', csrf=False)
    def retrive_marketplace_collection_image_from_url(self, db_name, encodedres='', filename='', **kwargs):
        try:
            if len(encodedres) and db_name:
                db_registry = Registry(db_name)
                if db_name and not request.session.db:
                    request.session.db = db_name
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    decode_data = base64.urlsafe_b64decode(encodedres)
                    res_id = str(decode_data, "utf-8")
                    record = env['shopify.collection.ts'].sudo().browse(int(res_id))
                    stream = request.env['ir.binary']._get_image_stream_from(record, field_name='image', filename=filename).get_response()
                    return stream
        except Exception:
            return request.not_found()
        return request.not_found()
