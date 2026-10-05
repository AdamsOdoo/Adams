import pprint
from datetime import datetime, timezone

import pytz

from odoo import fields, models, tools, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import GET_CUSTOMERS_BY_IDS, GET_MULTIPLE_CUSTOMERS, GET_REMAINING_CUSTOMER_METAFIELD
from odoo.addons.shopify.models.misc import extract_numeric_id
from odoo.addons.shopify.shopify.pyactiveresource.connection import ResourceNotFound


class Partner(models.Model):
    _inherit = "res.partner"

    def shopify_customer_query_filter(self, last_customer_import_date):
        """
        Generate and return the filter string for fetching Shopify customers based on their last update date.

        Args:
            last_customer_import_date (datetime or None): The timestamp of the last imported customer record. If provided,
            only customers updated after this date (until now) will be fetched.

        Returns:
            str: A formatted GraphQL filter string for the query.
        """
        filters = []
        # Set default to_date to current date if not provided
        to_date = fields.Datetime.now()
        if last_customer_import_date:
            from_date = pytz.UTC.localize(last_customer_import_date)
            to_date = pytz.UTC.localize(to_date)

            # Convert dates to ISO 8601 format (YYYY-MM-DD) as required by the GraphQL query.
            iso_from = from_date.isoformat().replace('+00:00', 'Z')
            iso_to = to_date.isoformat().replace('+00:00', 'Z')

            filters.append(f"updated_at:>='{iso_from}' updated_at:<='{iso_to}'")
        return "".join(filters)

    def fetch_all_shopify_customers(self, instance_id, mk_customer_id=False):
        """
        Fetches customer details from Shopify using GraphQL, either by specific customer IDs or by date range (default behavior).

        Args:
            instance_id (recordset): Recordset of mk.instance model.
            mk_customer_id (str or bool): A comma-separated string of Shopify Customer IDs (e.g., "12345,67890"). If provided, only these customers will be fetched. Defaults to False.

        Returns:
            list: A list of dictionaries containing Shopify customer data.

        """
        if mk_customer_id:
            # Task: T8975 - Fetch the given customers 250 at a time instead of one call per customer.
            shopify_customer_ids = []
            for customer_id in mk_customer_id.split(','):
                customer_id = customer_id.strip()
                shopify_customer_id = f"gid://shopify/Customer/{customer_id}"
                if customer_id and shopify_customer_id not in shopify_customer_ids:
                    shopify_customer_ids.append(shopify_customer_id)

            customer_list = []
            for batch_customer_ids in tools.split_every(250, shopify_customer_ids, piece_maker=list):
                variables = {"ids": batch_customer_ids}
                res = instance_id.execute_graphql_query(GET_CUSTOMERS_BY_IDS, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Customers: %(errors)s") % {'errors': joined_errors})

                batch_customer_list = res.get('data', {}).get('nodes', []) if res.get('data', {}) else []
                for customer_vals in batch_customer_list:
                    if customer_vals:
                        customer_list.append(customer_vals)
            return customer_list

        return self.fetch_all_shopify_customers_by_date(instance_id)

    def fetch_all_shopify_customers_by_date(self, instance_id):
        """
        Fetches all Shopify customers updated since the last import date using pagination via GraphQL.

        This method retrieves multiple customers from Shopify by repeatedly calling the
        GraphQL endpoint with pagination until all available customers are fetched.

        Args:
            instance_id (recordset): Recordset of mk.instance model.

        Returns:
            list:
                A list of dictionaries, each representing a Shopify customer record.

        Raises:
            MarketplaceException: If the GraphQL query fails or an unexpected error occurs during data fetching.

        """

        cursor = None
        shopify_customer_list = []

        # Generate GraphQL query filter based on last import date
        query_filter = self.shopify_customer_query_filter(instance_id.last_customer_import_date)

        while True:
            try:
                variables = {"customersCursor": cursor, "query": query_filter}
                res = instance_id.execute_graphql_query(GET_MULTIPLE_CUSTOMERS, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify customers: %(errors)s") % {'errors': joined_errors})

                customer_list = res and res.get('data', {}) and res.get('data', {}).get('customers', [])
                if not customer_list:
                    break

                if customer_list:
                    shopify_customer_list.extend(customer_list[:len(customer_list) - 1])
                    page_info = customer_list[-1].get('pageInfo', {})
                    if not page_info.get('hasNextPage', False):
                        instance_id.last_customer_import_date = fields.Datetime.now()
                        break

                    cursor = page_info.get('endCursor', None)

            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify customers: {str(e)}")

        return shopify_customer_list

    def shopify_get_find_partner_where_clause(self, type):
        """
        Task T7419 - Use Shipping Address as Delivery
        Included 'type' in the where_clause.
        Determines the fields used to match or find an existing partner (contact) record in Odoo based on the partner type — such as 'invoice' or 'delivery'.

        Args:
            type (str):
                The type of partner being processed. Common values include:
                - 'invoice': For billing address partners.
                - 'delivery': For shipping address partners.
                - Any other type will use a default matching set without 'parent_id'.

        Returns:
            list[str]: A list of field names to be used in the search domain for matching an existing partner.

        """
        where_clause = ['name', 'state_id', 'city', 'zip', 'street', 'street2', 'country_id', 'email', 'phone']

        # Include parent_id for child-type partners such as invoice or delivery addresses
        if type in ('invoice', 'delivery'):
            where_clause.extend(['parent_id', 'type'])

        return where_clause

    def _extract_customer_data_from_shopify_dict(self, customer_dict, mk_instance_id, type='contact', parent_id=False):
        """
        Task T7419 - Use Shipping Address as Delivery
        Add parent_id to the partner values so the system can find partner records correctly based on it.
        Extracts and maps Shopify customer information into an Odoo-compatible dictionary for customer or address record creation.

        Args:
            customer_dict (dict): Dictionary representing a Shopify customer, typically obtained from the Shopify GraphQL API response.
            mk_instance_id (recordset): The Shopify instance record, used for configuration values like `is_create_company_contact`.
            parent_id (int or bool, optional): ID of the parent partner (used when creating child addresses). Defaults to False.

        Returns:
            dict or bool: A dictionary of values to create or update an Odoo `res.partner` record. Returns False if the required address data is missing.

        """
        if not customer_dict:
            return False

        default_address_dict = customer_dict.get('defaultAddress') if customer_dict and customer_dict.get('defaultAddress', False) else customer_dict
        if not default_address_dict:
            return False

        # Determine name and company type
        name = default_address_dict.get('name', False)
        company_type = 'person'

        email_from_default = (default_address_dict.get('defaultEmailAddress') or {}).get('emailAddress') or ''
        email_from_customer = (customer_dict.get('defaultEmailAddress') or {}).get('emailAddress') or ''

        if mk_instance_id.is_create_company_contact and type == 'contact':
            name = customer_dict.get('company', False) if customer_dict.get('company', False) else default_address_dict.get('name', False)
            company_type = 'company' if customer_dict.get('company', False) else 'person'

        # Build name if missing
        if not name:
            first_name = customer_dict.get('firstName', '')
            last_name = customer_dict.get('lastName', '')

            if first_name or last_name:
                name = f"{first_name} {last_name}"
            else:
                name = email_from_default or email_from_customer or "Untitled"

        name = name.strip()

        # Country and state resolution
        country = self.env['res.country']
        if default_address_dict.get('countryCodeV2') or default_address_dict.get('country'):
            country = self.env['res.country'].search(['|', ('code', '=', default_address_dict.get('countryCodeV2')), ('name', '=', default_address_dict.get('country'))], limit=1)

        state = self.env['res.country.state'].search(
            [('country_id', '=', country.id), '|', ('code', '=', default_address_dict.get('provinceCode')), ('name', '=', default_address_dict.get('province'))], limit=1)

        if not state and default_address_dict.get('province') and default_address_dict.get('provinceCode'):
            state = self.env['res.country.state'].sudo().with_context(tracking_disable=True).create(
                {'country_id': country.id, 'name': default_address_dict.get('province'), 'code': default_address_dict.get('provinceCode')})

        # Prepare tags
        tag_list = []
        if customer_dict.get('tags', False):
            tag_list = self.shopify_prepare_tag_vals(customer_dict.get('tags'))
        # Task: T7545 -  Updated for Shopify API 2026-07 and deprecated phone fields.
        partner_vals = {
            'name': name,
            'email': email_from_default or email_from_customer,
            'street': default_address_dict.get('address1'),
            'street2': default_address_dict.get('address2'),
            'city': default_address_dict.get('city'),
            'state_id': state.id,
            'country_id': country.id,
            'zip': default_address_dict.get('zip'),
            'phone': default_address_dict.get('phone') or customer_dict.get('defaultPhoneNumber') and customer_dict.get('defaultPhoneNumber').get('phoneNumber', ''),
            'type': type,
            'comment': customer_dict.get('note', ''),
            'company_type': company_type,
            'category_id': tag_list,
        }
        if parent_id:
            partner_vals['parent_id'] = parent_id.id
        return partner_vals

    def create_update_shopify_customers(self, customer_dict, mk_instance_id, type='contact', parent_id=False):
        """
        Task T7419 - Use Shipping Address as Delivery
        Included parent_id in _extract_customer_data_from_shopify_dict method.
        """
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        partner = self.env['res.partner']

        try:
            partner_vals = self._extract_customer_data_from_shopify_dict(customer_dict, mk_instance_id, type=type, parent_id=parent_id)
            if partner_vals:
                partner = self.get_marketplace_partners(partner_vals, mk_instance_id, type=type, parent_id=parent_id)
                shopify_category_id = self.env.ref('shopify.res_partner_category_shopify', raise_if_not_found=False)
                if shopify_category_id:
                    partner.sudo().category_id = [(4, shopify_category_id.id)]

        except Exception as err:
            log_message = 'IMPORT CUSTOMER: TECHNICAL EXCEPTION : %s' % err
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})

        return partner

    def create_shopify_customer_queue_job(self, instance_id):
        shopify_customer_list = self.fetch_all_shopify_customers_by_date(instance_id)
        res_id_list, action = [], False
        if shopify_customer_list:
            batch_size = instance_id.queue_batch_limit or 100
            for shopify_customers in tools.split_every(batch_size, shopify_customer_list):
                queue_id = instance_id.action_create_queue(type='customer')
                for customer in shopify_customers:
                    name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}"
                    line_vals = {
                        'mk_id': extract_numeric_id(customer.get('id')),
                        'state': 'draft',
                        'name': name.strip(),
                        'data_to_process': pprint.pformat(customer),
                        'mk_instance_id': instance_id.id,
                    }

                    queue_id.action_create_queue_lines(line_vals)
                res_id_list.append(queue_id.id)
        if res_id_list:
            action = instance_id.action_open_model_view(res_id_list, 'mk.queue.job', 'Shopify Customers Queue')
        return action

    def import_shopify_customer_records(self, customer_dict, instance_id):
        """
        Task: T6294 - Added the functionality to import customer metafield.
        Create or update customers in Odoo based on Shopify customer information.
        :param customer_dict: Dictionary containing Shopify Customer information.
        :param instance_id: ID of the Shopify instance in Odoo.
        :return: Odoo customer ID.
        """
        company_customer_id = False
        default_address = customer_dict.get('defaultAddress', {})
        if instance_id.is_create_company_contact and customer_dict.get('defaultAddress', False):
            default_address_dict = default_address if default_address else customer_dict

            email_from_default = (default_address_dict.get('defaultEmailAddress') or {}).get('emailAddress') or ''
            email_from_customer = (customer_dict.get('defaultEmailAddress') or {}).get('emailAddress') or ''

            if not email_from_default and email_from_customer:
                default_address_dict.update({'defaultEmailAddress': {'emailAddress': email_from_customer}})

            # Check if the default address indicates a company
            is_company = True if default_address_dict.get('company', False) else False
            # If it's a company, create or update the company customer in Odoo
            if is_company:
                company_customer_id = self.create_update_shopify_customers(default_address_dict, instance_id)
        # Create or update the regular customer in Odoo based on the Shopify customer information
        if company_customer_id:
            first_name = default_address.get('firstName', '')
            last_name = default_address.get('lastName', '')
            name = '' or 'Untitled'
            if first_name or last_name:
                name = f"{first_name} {last_name}"

            vals = {'name': name, 'phone': default_address.get('phone', '')}
            customer_id = self.create_update_shopify_customers(vals, instance_id, parent_id=company_customer_id)
        else:
            customer_id = self.create_update_shopify_customers(customer_dict, instance_id, parent_id=company_customer_id)

        if customer_id:
            mk_id = str(extract_numeric_id(customer_dict.get('id')))
            if mk_id:
                customer_id.import_customer_metafield_from_shopify(instance_id, customer_dict, mk_id, mk_log_id=self.env.context.get('mk_log_id') or False,
                                                                   queue_line_id=self.env.context.get('queue_line_id') or False)
        return customer_id

    def _fetch_all_shopify_customer_remaining_metafields(self, mk_instance_id, customer_mk_id, page_info, mk_log_line_dict, queue_line_id=False):
        """
        Task: T6294 - Fetches remaining customer metafields from Shopify using pagination.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            customer_mk_id (str): Shopify customer ID.
            page_info (dict): Pagination info containing cursor and next page details.
            mk_log_line_dict (dict): Dictionary contains log details.
            queue_line_id (recordset): Recordset of mk.queue.job.line.
        Returns:
            tuple: (list of remaining metafields, bool indicating whether pagination completed without errors)
        """
        remaining_metafields = []
        is_complete = True

        while page_info.get('hasNextPage', False):
            variables = {'id': f"gid://shopify/Customer/{customer_mk_id}", 'cursor': page_info.get('endCursor', ''), 'first': 250}
            try:
                response = mk_instance_id.execute_graphql_query(GET_REMAINING_CUSTOMER_METAFIELD, variables=variables)
                if response and response.get('errors'):
                    log_message = _("IMPORT CUSTOMER: Error while fetching remaining metafield for customer %s (%s): %s") % (self.name, customer_mk_id, response.get('errors'))
                    mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                    is_complete = False
                    break
                metafield_data = (((response or {}).get('data') or {}).get('customer') or {}).get('metafields') or {}
                remaining_metafields.extend(metafield_data.get('nodes') or [])
                page_info = metafield_data.get('pageInfo') or {}
            except Exception as e:
                log_message = f"IMPORT CUSTOMER: Exception occurred during remaining metafield fetch for customer {self.name} ({customer_mk_id}): {str(e)}"
                mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                is_complete = False
                break
        return remaining_metafields, is_complete

    def import_customer_metafield_from_shopify(self, mk_instance_id, customer_dict, mk_id, mk_log_id=False, queue_line_id=False):
        """
        Task: T6294 - Imports Shopify customer metafields into the Odoo.

        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            customer_dict (dict): Shopify customer response data.
            mk_id (str): Shopify customer ID.
            mk_log_id (recordset): Recordset of mk.log.
            queue_line_id (recordset): Recordset of mk.queue.job.line.

        Returns:
            bool: True after processing.
        """
        self.ensure_one()
        if not (mk_instance_id.enable_metafield and mk_instance_id.metafield_resource_ids.filtered(lambda r: r.active_sync and r.shopify_owner_type == 'CUSTOMER')):
            return True

        mk_instance_id.connection_to_shopify()

        new_log = False
        if not mk_log_id:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
            new_log = True
        mk_log_line_dict = {'error': [], 'success': []}

        metafield_res = (customer_dict.get('metafields') or {}).get('nodes') or []
        page_info = (customer_dict.get('metafields') or {}).get('pageInfo') or {}

        remaining_metafields, is_complete = self._fetch_all_shopify_customer_remaining_metafields(
            mk_instance_id=mk_instance_id,
            customer_mk_id=mk_id,
            page_info=page_info,
            mk_log_line_dict=mk_log_line_dict,
            queue_line_id=queue_line_id,
        )
        if remaining_metafields:
            metafield_res.extend(remaining_metafields)

        try:
            mk_instance_id.import_specific_type_metafield_from_shopify(
                target_odoo_record=self,
                shopify_owner_type='CUSTOMER',
                metafields_list=metafield_res,
                reference_handler_func=mk_instance_id.set_shopify_reference_metafield_value,
                mk_log_line_dict=mk_log_line_dict,
                wipe_unmatched=is_complete,
                queue_line_id=queue_line_id,
                mk_log_id=mk_log_id,
                mk_id=mk_id,
            )
        except Exception as e:
            mk_log_line_dict['error'].append({
                'log_message': f"IMPORT CUSTOMER: Failed to update metafields for Customer {self.name} ({mk_id}): {e}",
                'queue_job_line_id': queue_line_id.id if queue_line_id else False,
            })
        finally:
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=mk_instance_id, operation_type='import', mk_log_line_dict=mk_log_line_dict)
            if new_log and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
        return True

    def shopify_import_customers(self, instance_id, mk_customer_id=False):
        res_id_list, action = [], False
        instance_id.connection_to_shopify()
        if mk_customer_id:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=instance_id, operation_type='import')
            try:
                shopify_customer_list = self.fetch_all_shopify_customers(instance_id, mk_customer_id=mk_customer_id)
            except ResourceNotFound as e:
                raise MarketplaceException(e.args, f'{e.response.code} - {e.response.msg}')
            for shopify_customer in shopify_customer_list:
                partner_id = self.with_context(mk_log_id=mk_log_id).import_shopify_customer_records(shopify_customer, instance_id)
                partner_id and res_id_list.append(partner_id.id)

            if not mk_log_id.log_line_ids:
                mk_log_id.unlink()
            if res_id_list:
                return instance_id.action_open_model_view(res_id_list, 'res.partner', 'Shopify Customers')
            if mk_log_id.exists():
                return instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
        if not mk_customer_id:
            return self.create_shopify_customer_queue_job(instance_id)

    def shopify_prepare_tag_vals(self, shopify_tags):
        shopify_tag_list, shopify_tag_obj = [], self.env['res.partner.category']
        for tag in shopify_tags:
            if not tag.strip():
                continue
            tag_name = tag.strip()
            shopify_tag_id = shopify_tag_obj.search([('name', '=', tag_name)], limit=1)
            if not shopify_tag_id:
                shopify_tag_id = shopify_tag_obj.sudo().create({'name': tag_name})
            shopify_tag_list.append(shopify_tag_id.id)

        return [(6, 0, shopify_tag_list)]

    def transform_customer_webhook_response_to_graphql(self, webhook_response, mk_instance_id=False):
        """Transforms a Shopify customer webhook response into a dictionary
        that follows the structure of Shopify GraphQL API customer response.

        Args:
            webhook_response (dict): Dictionary containing the Shopify customer data received via webhook.

        Returns:
            dict: A dictionary formatted similarly to Shopify GraphQL customer response.
        """
        if not webhook_response:
            return None

        # Helper to used to convert webhook timestamp to UTC ISO format.(format accepted by graphql)
        def shopify_utc_iso_format(timestamp_str):
            if not timestamp_str:
                return None
            dt_object = datetime.fromisoformat(timestamp_str)
            return dt_object.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        default_address = webhook_response.get("default_address", {})
        return {
            "id": webhook_response.get("admin_graphql_api_id", ""),
            "firstName": webhook_response.get("first_name", ""),
            "lastName": webhook_response.get("last_name", ""),
            "createdAt": shopify_utc_iso_format(webhook_response.get("created_at", "")),
            "updatedAt": shopify_utc_iso_format(webhook_response.get("updated_at", "")),
            "defaultEmailAddress": {
                "emailAddress": webhook_response.get("email", "")
            },
            # Task: T7545 -  Updated for Shopify API 2026-07 and deprecated phone fields.
            "defaultPhoneNumber": {
                "phoneNumber": webhook_response.get("phone", "")
            },
            "state": webhook_response.get("state", ""),  # state is not used
            "note": webhook_response.get("note", ""),
            "tags": None,  # doesn't get from webhook
            "defaultAddress": {
                "phone": default_address.get("phone", ""),
                "address1": default_address.get("address1", ""),
                "address2": default_address.get("address2", ""),
                "firstName": default_address.get("first_name", ""),
                "lastName": default_address.get("last_name", ""),
                "company": default_address.get("company", ""),
                "country": default_address.get("country", ""),
                "countryCodeV2": default_address.get("country_code", ""),
                "province": default_address.get("province", ""),
                "provinceCode": default_address.get("province_code", ""),
                "zip": default_address.get("zip", ""),
            }
        }
