from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import ALL_LOCATIONS, GET_PRIMARY_LOCATION
from odoo.addons.shopify.models.misc import extract_numeric_id


class ShopifyAccount(models.Model):
    _name = "shopify.location.ts"
    _description = 'Shopify Location'

    name = fields.Char('Name', required=True)
    active = fields.Boolean(default=True)
    shopify_location_id = fields.Char("Shopify Location ID", copy=False)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade')
    is_default_location = fields.Boolean("Is Default Location?", copy=False,
                                         help="Location that Shopify and apps will use when no other location is specified. Only locations that fulfill online orders can be used as your default location.", )
    order_warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', copy=False,
                                         help="This warehouse is set in the Order if this location is found. Otherwise set Instance's warehouse.")
    company_id = fields.Many2one('res.company', string='Company', related='mk_instance_id.company_id', store=True)
    location_id = fields.Many2one('stock.location', 'Location', help="This warehouse location is used while import stock.", domain="[('usage','=','internal')]")
    is_import_export_stock = fields.Boolean('Enable Import/Export Stock?', help="If you enable then stock for this location will be use for import/export.", default=True,
                                            copy=False)
    export_location_ids = fields.Many2many(comodel_name='stock.location', relation='shopify_export_location_relation', help="This warehouse location is used while export stock.")
    restock_warehouse_id = fields.Many2one('stock.warehouse', string="Return Restock Warehouse", copy=False,
                                           help="Warehouse where returned items for this Shopify location will be restocked. If not configured, items are restocked back into the warehouse they were fulfilled from.")

    def prepare_vals_for_location(self, location, mk_instance_id):
        """
        Prepare a dictionary of values for a Shopify location record.

        Args:
            location (dict): The location data from Shopify.
            mk_instance_id (obj): The instance of the Shopify integration.

        Returns:
            dict: The dictionary of values for the location record.
        """
        vals = {
            'name': location.get('name'),
            'shopify_location_id': extract_numeric_id(location.get('id')),
            'mk_instance_id': mk_instance_id.id,
        }
        return vals

    def set_default_location(self, mk_instance_id):
        """
        Set the default location for a Shopify instance. If a default location exists, unset it.
        Then, set the primary location as the default.

        Args:
            mk_instance_id (obj): The instance of the Shopify integration.
        """
        shopify_default_location = self.search([('is_default_location', '=', True), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)

        if shopify_default_location:
            shopify_default_location.write({'is_default_location': False})

        response_data = mk_instance_id.execute_graphql_query(GET_PRIMARY_LOCATION)
        user_errors = response_data.get('errors', []) if isinstance(response_data, dict) else {}
        if user_errors and isinstance(user_errors, list):
            err_messages = [e.get('message', str(e)) for e in user_errors]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Location: %(errors)s") % {'errors': joined_errors})

        location_data = response_data and response_data.get('data', {}) and response_data.get('data', {}).get('location', {})
        default_location_id = location_data and location_data.get('id', '') and extract_numeric_id(location_data.get('id', ''))
        default_location = default_location_id and self.search([('shopify_location_id', '=', default_location_id), ('mk_instance_id', '=', mk_instance_id.id)]) or False

        if default_location:
            location_vals = {'is_default_location': True}
            if not default_location.order_warehouse_id:
                location_vals.update({'order_warehouse_id': mk_instance_id.warehouse_id.id})
            if not default_location.location_id:
                location_vals.update({'location_id': mk_instance_id.warehouse_id.lot_stock_id.id})
            if not default_location.export_location_ids:
                location_vals.update({'export_location_ids': [(6, 0, [mk_instance_id.warehouse_id.lot_stock_id.id])]})
            default_location.write(location_vals)

        return True

    def remove_deactivate_shopify_locations(self, active_location_ids, mk_instance_id):
        """
        Deactivate Shopify locations that are not in the list of active locations.

        Args:
            active_location_ids (list): List of active location IDs.
            mk_instance_id (obj): The instance of the Shopify integration.

        Returns:
            list: The list of active location IDs.
        """
        all_shopify_locations = self.search([('mk_instance_id', '=', mk_instance_id.id)])
        to_remove_locations = all_shopify_locations - active_location_ids
        to_remove_locations and to_remove_locations.write({'active': False})
        return active_location_ids

    def fetch_all_shopify_locations(self, mk_instance_id):
        """
        Fetch all active Shopify locations with pagination.

        Args:
            mk_instance_id (obj): The instance of the Shopify integration.

        Returns:
            list: The list of Shopify locations.
        """
        shopify_location_list = []
        cursor = None
        has_next_page = True

        # 2. Loop until there are no more pages
        while has_next_page:
            variables = {"cursor": cursor}

            # Execute the query with the current cursor
            response_data = mk_instance_id.execute_graphql_query(ALL_LOCATIONS, variables)
            user_errors = response_data.get('errors', []) if isinstance(response_data, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Location: %(errors)s") % {'errors': joined_errors})

            # Safely access the data
            locations_data = response_data and response_data.get('data', {}) and response_data.get('data', {}).get('locations', {})
            nodes = locations_data.get('nodes', [])
            page_info = locations_data.get('pageInfo', {})

            shopify_location_list.extend(nodes)

            # 3. Check if there is a next page and update the cursor
            has_next_page = page_info.get('hasNextPage', False)
            if has_next_page:
                cursor = page_info.get('endCursor', None)

        return shopify_location_list

    def import_location_from_shopify(self, mk_instance_id):
        """
        Import locations from Shopify and update the records in the Odoo.

        Args:
            mk_instance_id (obj): The instance of the Shopify.
        """
        self = self.sudo()
        active_location_ids = self
        mk_instance_id.connection_to_shopify()
        shopify_locations = self.fetch_all_shopify_locations(mk_instance_id)

        for location in shopify_locations:

            vals = self.prepare_vals_for_location(location, mk_instance_id)
            location = location.get('id') and extract_numeric_id(location.get('id'))
            shopify_location_id = self.with_context(active_test=False).search([('shopify_location_id', '=', location), ('mk_instance_id', '=', mk_instance_id.id)])

            if shopify_location_id:
                vals.update({'active': True})
                shopify_location_id.write(vals)
            else:
                shopify_location_id = self.create(vals)

            active_location_ids |= shopify_location_id

        self.set_default_location(mk_instance_id)

        self.remove_deactivate_shopify_locations(active_location_ids, mk_instance_id)
        return True

    @api.constrains('export_location_ids')
    def _constrains_export_location_ids(self):
        """
        TASK: T6274 - Validate Shopify location.

        Ensures that a parent location and its child location cannot be active or
        selected in one Shopify Location.
        """
        location_ids = self.export_location_ids

        for location_id in location_ids:
            other_locations = location_ids - location_id
            conflicting_parent_ids = other_locations.filtered(
                lambda l: l.id != location_id.id and location_id.id in l.search([('id', 'child_of', l.id), ('id', '=', location_id.id)]).ids)

            if conflicting_parent_ids:
                parent_name = conflicting_parent_ids[0].display_name
                child_name = location_id.display_name
                raise MarketplaceException(_("You cannot select both the parent '%(parent_name)s' and its child '%(child_name)s'.") % {'parent_name': parent_name, 'child_name': child_name})
