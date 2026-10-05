import logging
from urllib.parse import urlparse

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import CREATE_SHOPIFY_WEBHOOK, DELETE_SHOPIFY_SUBSCRIPTION, GRAPHQL_QUERY_FIND_WEBHOOKS, GET_WEHBOOK_SUBSCRIPTION, \
    GET_WEBHOOK_SUBSCRIPTION_USING_URI_AND_TOPIC
from odoo.addons.shopify.models.misc import extract_numeric_id

_logger = logging.getLogger("Qamah:Shopify")

WEBHOOK_EVENTS = [('customers/create', 'Create Customer'),
                  ('orders/create', 'Create Orders'),
                  ('orders/updated', 'Update Orders'),
                  ('products/create', 'Create Product'),
                  ('products/update', 'Update Product'),
                  ('products/delete', 'Delete Product'),
                  ('returns/request', 'Return Requested'),
                  ('returns/approve', 'Return Approved'),
                  ('returns/decline', 'Return Declined'),
                  ('returns/close', 'Return Closed'),
                  ('returns/reopen', 'Return Reopened'),
                  ('returns/cancel', 'Return Canceled')]


class ShopifyWebhook(models.Model):
    _name = "shopify.webhook.ts"
    _description = "Shopify Webhook"
    _rec_name = "webhook_event"

    webhook_event = fields.Selection(WEBHOOK_EVENTS, "Webhook Event Type")
    webhook_id = fields.Char("Webhook ID", copy=False)
    active_webhook = fields.Boolean("Active", default=False)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade')

    _check_unique_webhook_event = models.Constraint("UNIQUE (webhook_event, mk_instance_id)", "You cannot create duplicate Webhook Events.")

    def fetch_all_webhook_from_shopify(self, mk_instance_id):
        """
        TASK T6079 : Fetches all existing webhook subscriptions from Shopify via GraphQL and synchronizes their status locally.
        Args: mk_instance_id (recordset)- Recordset of the marketplace instance model (e.g., mk.instance).
        Returns:
            bool: True upon successful completion of the synchronization process.

        """
        mk_instance_id.connection_to_shopify()
        variables = {
            "count": 250
        }
        webhooks = self.mk_instance_id.execute_graphql_query(GRAPHQL_QUERY_FIND_WEBHOOKS, variables)
        webhooks_response_dict = webhooks.get('data', {}).get('webhookSubscriptions', {})
        for webhook in webhooks_response_dict:
            webhook_id = extract_numeric_id(webhook.get('id'))
            webhook_event = webhook.get('topic')
            webhook_url = mk_instance_id.webhook_url
            if webhook.get('uri', '') != webhook_url:
                continue
            webhook_event = webhook_event.strip().lower().replace("_", "/")
            existing_webhook_id = self.search([('mk_instance_id', '=', mk_instance_id.id), '|', ('webhook_id', '=', webhook_id), ('webhook_event', '=', webhook_event)])
            if existing_webhook_id and not existing_webhook_id.active_webhook:
                existing_webhook_id.with_context(skip_create=True).write({'active_webhook': True, 'webhook_id': webhook_id})
            if not existing_webhook_id:
                create_vals = {'webhook_event': webhook_event.strip().lower().replace("_", "/"),
                               'webhook_id': webhook_id,
                               'active_webhook': True,
                               'mk_instance_id': mk_instance_id.id}
                self.with_context(skip_create=True).create(create_vals)
        webhook_id = self.env['shopify.webhook.ts'].search([('active_webhook', '=', 'True')])
        mapped_webhook_id = webhook_id.mapped('webhook_id')
        if mapped_webhook_id and webhooks_response_dict:
            response = []
            response_id = [webhook['id'] for webhook in webhooks_response_dict if 'id' in webhook]
            for webhook_response in response_id:
                response.append(extract_numeric_id(webhook_response))
            response = [str(response_id) for response_id in response]
            webhook_id_not_in_response = list(set(mapped_webhook_id) - set(response))
            if webhook_id_not_in_response:
                for webhook_not_in_res in webhook_id_not_in_response:
                    if webhook_not_in_res:
                        webhook_not_in_res = int(webhook_not_in_res)
                        webhook = self.env['shopify.webhook.ts'].search([('webhook_id', '=', webhook_not_in_res)])
                        webhook.with_context(skip_create=True).write({'active_webhook': False, 'webhook_id': ''})

        return True

    def _get_existing_shopify_webhook_id(self):
        """
        TASK T6079: Get url and topic from create a webhook for the "Address for this topic has already been taken" and get the id.
        Returns:
            int: webhook_id
        """
        webhook_id = False
        data_vals = {
            'uri': self.mk_instance_id.webhook_url,
            'topic': [self.webhook_event.strip().upper().replace('/', '_')]
        }
        response = self.mk_instance_id.execute_graphql_query(GET_WEBHOOK_SUBSCRIPTION_USING_URI_AND_TOPIC, data_vals)
        user_errors = response.get('errors', []) if isinstance(response, dict) else {}
        if user_errors and isinstance(user_errors, list):
            err_messages = [e.get('message', str(e)) for e in user_errors]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Webhook: %(errors)s") % {'errors': joined_errors})

        webhook_subscriptions = response.get('data', {}).get('webhookSubscriptions', [])
        if webhook_subscriptions:
            for webhook_subscription in webhook_subscriptions:
                webhook_id = webhook_subscription.get('id', '')
            if not webhook_id:
                return False
            return extract_numeric_id(webhook_id)

    def create_webhook_in_shopify(self):
        """
        Task : T6079 - Create a webhook Subscription.
                       Migrate the rest api to the Graphql.

        Returns: response data.
        bool: True upon successful completion of the synchronization process.
        """
        # Task: T7432 - Raise an error when attempting to activate a webhook while the instance is not in the confirmed state.
        if not self.mk_instance_id.state == 'confirmed':
            raise MarketplaceException(_("You must confirm the instance before activating the webhook."))
        if not self.mk_instance_id:
            raise MarketplaceException(_("You have to create/save Instance first to active webhook"))
        if not self.mk_instance_id.webhook_url:
            self.mk_instance_id.webhook_url = self.mk_instance_id._get_shopify_webhook_url()
        if not self.mk_instance_id.webhook_url.startswith('https://'):
            raise MarketplaceException(_("You can only create Webhook with secure URL (https)."))
        self.mk_instance_id.connection_to_shopify()
        data_vals = self._prepare_webhook_data()
        response = self.mk_instance_id.execute_graphql_query(CREATE_SHOPIFY_WEBHOOK, data_vals)
        user_errors = response.get('data', {}).get('webhookSubscriptionCreate', {}).get('userErrors')
        if user_errors:
            errors = response.get('data', {}).get('webhookSubscriptionCreate', {}).get('userErrors', {})
            error_message = [error.get('message') for error in errors]
            if 'Address for this topic has already been taken' in error_message:
                existing_webhook_id = self._get_existing_shopify_webhook_id()
                if existing_webhook_id:
                    self.webhook_id = existing_webhook_id
                    return True
            error = _("Create Webhook STATUS: Errors Generate When Webhook Create: %s") % ', '.join(e.get('message') for e in errors)
            raise MarketplaceException(error)
        else:
            response_data = response.get('data', {}).get('webhookSubscriptionCreate', {})
            response_webhook_id = response_data.get('webhookSubscription', {}).get('id', '')
            self.webhook_id = extract_numeric_id(response_webhook_id or '')
        return response

    def _prepare_webhook_data(self):
        data = {
                "topic": self.webhook_event.strip().upper().replace("/", "_"),
                "webhookSubscription": {
                    "uri": self.mk_instance_id.webhook_url,
                    "format": "JSON"
                }
            }
        return data

    @api.model_create_multi
    def create(self, vals):
        res = super(ShopifyWebhook, self).create(vals)
        for webhook_id in res:
            if webhook_id.active_webhook and not self.env.context.get('skip_create', False):
                webhook_id.create_webhook_in_shopify()
        return res

    def write(self, vals):
        """
        Task: T6079 - Migrate the Rest api to the Graphql.
        """
        if vals.get('active_webhook') and not self.env.context.get('skip_create', False):
            self.create_webhook_in_shopify()
        if 'active_webhook' in vals and not vals.get("active_webhook") and not self.env.context.get('skip_write', False):
            self.delete_subscription()
        res = super(ShopifyWebhook, self).write(vals)
        return res

    def delete_subscription(self):
        """
        Task: T6079 - Delete the Shopify Subscription when click (active_webhook) boolean True to False.
        """
        for record in self:
            if record.active_webhook:
                record.mk_instance_id.connection_to_shopify()
                variables = {
                    "id": f"gid://shopify/WebhookSubscription/{record.webhook_id}"
                }
                webhooks = self.mk_instance_id.execute_graphql_query(GET_WEHBOOK_SUBSCRIPTION, variables)
                user_errors = webhooks.get('errors', []) if isinstance(webhooks, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Webhook: %(errors)s") % {'errors': joined_errors})

                webhooks = webhooks.get('data', {}).get('webhookSubscription', {})
                webhooks_url = webhooks.get('uri', '') if webhooks else ''
                if webhooks_url == record.mk_instance_id.webhook_url:
                    try:
                        webhooks_id = webhooks.get('id', '')
                        webhooks_id = extract_numeric_id(webhooks_id)
                        variables = {"id": f"gid://shopify/WebhookSubscription/{webhooks_id}"}
                        self.mk_instance_id.execute_graphql_query(DELETE_SHOPIFY_SUBSCRIPTION, variables)
                        self.write({'webhook_id': ''})

                    except Exception as err:
                        _logger.error(f"SHOPIFY WEBHOOK DELETE SUBSCRIPTION : Cannot found webhook in Shopify. ERROR: {err}")
        return True

    def unlink(self):
        """
        Task: T6079 - Migrate the Rest api to the Graphql.
        Delete the Shopify Subscription and unlink the record from the erp.
        """
        for record in self:
            if record.active_webhook:
                record.mk_instance_id.connection_to_shopify()
                variables = {
                     "id": f"gid://shopify/WebhookSubscription/{record.webhook_id}"
                }
                webhooks = self.mk_instance_id.execute_graphql_query(GET_WEHBOOK_SUBSCRIPTION, variables)
                user_errors = webhooks.get('errors', []) if isinstance(webhooks, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Webhook: %(errors)s") % {'errors': joined_errors})

                webhooks = webhooks.get('data', {}).get('webhookSubscription', {})
                webhooks_url = webhooks.get('uri', '') if webhooks else ''
                if webhooks_url == record.mk_instance_id.webhook_url:
                    try:
                        webhooks_id = webhooks.get('id', '')
                        webhooks_id = extract_numeric_id(webhooks_id)
                        variables = {"id": f"gid://shopify/WebhookSubscription/{webhooks_id}"}
                        self.mk_instance_id.execute_graphql_query(DELETE_SHOPIFY_SUBSCRIPTION, variables)
                    except Exception as err:
                        _logger.error(f"SHOPIFY WEBHOOK UNLINK: Cannot found webhook in Shopify. ERROR: {err}")
        res = super(ShopifyWebhook, self).unlink()
        return res

    def shopify_delete_webhook(self):
        """
        Task: T6079 -  Migrate the Rest api to the Graphql.
        Delete the shopify Subscription for this and False the active webhook type and deleted the webhook_id and set None.
        """
        self.mk_instance_id.connection_to_shopify()
        try:
            variables = {
                "id": f"gid://shopify/WebhookSubscription/{self.webhook_id}"
            }
            webhooks = self.mk_instance_id.execute_graphql_query(GET_WEHBOOK_SUBSCRIPTION, variables)
            user_errors = webhooks.get('errors', []) if isinstance(webhooks, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Webhook: %(errors)s") % {'errors': joined_errors})

            webhooks_response_dict = webhooks.get('data', {}).get('webhookSubscription', {})
            instance_webhook_url = urlparse(self.mk_instance_id.webhook_url).hostname
            webhook_uri = webhooks_response_dict.get('uri', {})
            webhook_address = urlparse(webhook_uri).hostname
            if webhook_address == instance_webhook_url:
                variables = {"id": webhooks_response_dict.get('id', {})}
                self.mk_instance_id.execute_graphql_query(DELETE_SHOPIFY_SUBSCRIPTION, variables)
                self.write({
                    'active_webhook': False,
                    'webhook_id': ''
                })
        except MarketplaceException:
            raise
        except Exception as err:
            _logger.error(f"SHOPIFY WEBHOOK DEACTIVATE: Cannot found webhook in Shopify. ERROR: {err}")
        return True
