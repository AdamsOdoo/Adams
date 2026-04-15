# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from .base_exporter import BaseExporter
from .base_importer import BaseImporter
from .checksum import customer_checksum, shopify_customer_checksum
from ..shopify_api.queries.customer import (
    FETCH_CUSTOMERS,
    CUSTOMER_CREATE_MUTATION,
    CUSTOMER_UPDATE_MUTATION,
)

_logger = logging.getLogger(__name__)


class CustomerExporter(BaseExporter):
    entity_name = 'customer'
    binding_model = 'shopify.customer.binding'

    def _compute_checksum(self, binding):
        return customer_checksum(binding.odoo_id)

    def _export_one(self, binding):
        partner = binding.odoo_id
        if binding.shopify_id:
            self._update_customer(binding, partner)
        else:
            self._create_customer(binding, partner)

    def _create_customer(self, binding, partner):
        customer_input = self._build_customer_input(partner)
        result = self.client.execute_mutation(
            CUSTOMER_CREATE_MUTATION,
            {'input': customer_input},
            result_key='customerCreate',
            estimated_cost=10,
        )
        shopify_customer = result.get('customer', {})
        binding.shopify_id = shopify_customer.get('id')
        binding.shopify_email = shopify_customer.get('email', '')

    def _update_customer(self, binding, partner):
        customer_input = self._build_customer_input(partner)
        customer_input['id'] = binding.shopify_id
        self.client.execute_mutation(
            CUSTOMER_UPDATE_MUTATION,
            {'input': customer_input},
            result_key='customerUpdate',
            estimated_cost=10,
        )

    def _build_customer_input(self, partner):
        """Build Shopify CustomerInput from res.partner data."""
        name_parts = (partner.name or '').split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        customer_input = {
            'firstName': first_name,
            'lastName': last_name,
            'email': partner.email or None,
            'phone': partner.phone or None,
        }

        # Build addresses from partner
        addresses = []
        if partner.street or partner.city or partner.country_id:
            addresses.append(self._build_address(partner))

        # Include child contact addresses
        for child in partner.child_ids.filtered(lambda c: c.type in ('delivery', 'invoice', 'other')):
            if child.street or child.city or child.country_id:
                addresses.append(self._build_address(child))

        if addresses:
            customer_input['addresses'] = addresses

        return customer_input

    def _build_address(self, partner):
        """Build a Shopify MailingAddressInput from a res.partner."""
        return {
            'address1': partner.street or None,
            'address2': partner.street2 or None,
            'city': partner.city or None,
            'zip': partner.zip or None,
            'provinceCode': partner.state_id.code if partner.state_id else None,
            'countryCode': partner.country_id.code if partner.country_id else None,
            'phone': partner.phone or None,
        }


class CustomerImporter(BaseImporter):
    entity_name = 'customer'
    binding_model = 'shopify.customer.binding'

    def _compute_shopify_checksum(self, node):
        return shopify_customer_checksum(node)

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id')
        vals = self._map_to_odoo(node)
        checksum = self._compute_shopify_checksum(node)

        if existing_binding:
            existing_binding.odoo_id.write(vals)
            existing_binding._mark_synced(checksum=checksum)
        else:
            # Acquire a PostgreSQL advisory lock keyed on the Shopify GID
            # hash to prevent concurrent imports from creating duplicate
            # partner records for the same customer.
            lock_key = hash(f"shopify_customer_{self.backend.id}_{shopify_id}") & 0x7FFFFFFF
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s)", (lock_key,),
            )

            # Re-check binding after lock in case another worker just created it.
            existing_binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_id),
            ], limit=1)
            if existing_binding:
                existing_binding.odoo_id.write(vals)
                existing_binding._mark_synced(checksum=checksum)
                return

            partner = self._find_odoo_partner(node)
            if not partner:
                vals['is_shopify_customer'] = True
                partner = self.env['res.partner'].create(vals)
            else:
                partner.write(vals)

            self.env['shopify.customer.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': partner.id,
                'shopify_id': shopify_id,
                'shopify_email': node.get('email', ''),
                'shopify_tags': ', '.join(node.get('tags', [])) if isinstance(node.get('tags'), list) else node.get('tags', ''),
                'sync_status': 'synced',
                'sync_checksum': checksum,
                'last_sync_date': fields.Datetime.now(),
            })

            # Import addresses
            self._import_addresses(partner, node)

    def _map_to_odoo(self, node):
        first_name = node.get('firstName', '') or ''
        last_name = node.get('lastName', '') or ''
        name = f"{first_name} {last_name}".strip() or node.get('email', 'Unknown')

        vals = {
            'name': name,
            'email': node.get('email') or False,
            'phone': node.get('phone') or False,
            'customer_rank': 1,
        }

        default_addr = node.get('defaultAddress') or {}
        if default_addr:
            country = self._resolve_country(default_addr.get('countryCodeV2'))
            state = self._resolve_state(
                default_addr.get('provinceCode'),
                country,
            )
            vals.update({
                'street': default_addr.get('address1') or False,
                'street2': default_addr.get('address2') or False,
                'city': default_addr.get('city') or False,
                'zip': default_addr.get('zip') or False,
                'country_id': country.id if country else False,
                'state_id': state.id if state else False,
            })

        return vals

    def _find_odoo_partner(self, node):
        """Deduplicate partner based on backend's configured dedup strategy."""
        dedup = self.backend.customer_dedup_field or 'email'
        email = node.get('email')
        phone = node.get('phone')

        # Strategy 1: first check if a binding already exists for this Shopify GID
        shopify_id = node.get('id', '')
        if shopify_id:
            existing_binding = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_id),
            ], limit=1)
            if existing_binding:
                return existing_binding.odoo_id

        # Strategy 2: dedup by configured field
        if dedup == 'email' and email:
            return self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('parent_id', '=', False),
            ], limit=1)

        if dedup == 'phone' and phone:
            # Normalize phone for matching
            return self.env['res.partner'].search([
                ('phone', '=', phone),
                ('parent_id', '=', False),
            ], limit=1) or self.env['res.partner'].search([
                ('mobile', '=', phone),
                ('parent_id', '=', False),
            ], limit=1)

        if dedup == 'email_phone':
            # Try email first (more reliable), then phone
            if email:
                partner = self.env['res.partner'].search([
                    ('email', '=ilike', email),
                    ('parent_id', '=', False),
                ], limit=1)
                if partner:
                    return partner
            if phone:
                partner = self.env['res.partner'].search([
                    ('phone', '=', phone),
                    ('parent_id', '=', False),
                ], limit=1) or self.env['res.partner'].search([
                    ('mobile', '=', phone),
                    ('parent_id', '=', False),
                ], limit=1)
                if partner:
                    return partner

        return None

    def _import_addresses(self, partner, node):
        """Import additional Shopify addresses as child contacts (with dedup)."""
        addresses = node.get('addresses', [])
        # Skip first address (already set on main partner from defaultAddress)
        for addr in addresses[1:]:
            street = addr.get('address1') or ''
            city = addr.get('city') or ''
            if not street and not city:
                continue

            # Check for existing child address to avoid duplicates
            existing = self.env['res.partner'].search([
                ('parent_id', '=', partner.id),
                ('street', '=', street),
                ('city', '=', city),
            ], limit=1)
            if existing:
                continue

            country = self._resolve_country(addr.get('countryCodeV2'))
            state = self._resolve_state(addr.get('provinceCode'), country)
            self.env['res.partner'].create({
                'parent_id': partner.id,
                'type': 'other',
                'name': partner.name,
                'street': street or False,
                'street2': addr.get('address2') or False,
                'city': city or False,
                'zip': addr.get('zip') or False,
                'country_id': country.id if country else False,
                'state_id': state.id if state else False,
                'phone': addr.get('phone') or False,
            })

    def _resolve_country(self, country_code):
        if not country_code:
            return None
        return self.env['res.country'].search([
            ('code', '=', country_code),
        ], limit=1)

    def _resolve_state(self, state_code, country):
        if not state_code or not country:
            return None
        return self.env['res.country.state'].search([
            ('code', '=', state_code),
            ('country_id', '=', country.id),
        ], limit=1)


class CustomerSync:
    """Orchestrates customer sync."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = CustomerImporter(env, backend)
        self.exporter = CustomerExporter(env, backend)

    def export_customers(self):
        return self.exporter.export_batch()

    def import_customers(self):
        nodes = self.importer.client.fetch_paginated(
            FETCH_CUSTOMERS, 'customers',
            page_size=self.backend.batch_size,
            estimated_cost_per_page=12,
        )
        return self.importer.import_batch(nodes)

    def import_single_customer(self, webhook_data):
        """Import from webhook (REST payload)."""
        shopify_id = f"gid://shopify/Customer/{webhook_data.get('id', '')}"
        try:
            from ..shopify_api.client import ShopifyClient
            client = ShopifyClient(self.backend)
            query = """
            query GetCustomer($id: ID!) {
              customer(id: $id) {
                id firstName lastName email phone tags state
                defaultAddress {
                  address1 address2 city province provinceCode
                  country countryCodeV2 zip phone
                }
                addresses {
                  address1 address2 city province provinceCode
                  country countryCodeV2 zip phone
                }
              }
            }
            """
            body = client.execute(query, {'id': shopify_id}, estimated_cost=5)
            node = body.get('data', {}).get('customer')
            if node:
                binding = self.importer._find_binding(shopify_id)
                self.importer._import_one(node, binding)
        except Exception:
            _logger.exception("Failed to import customer from webhook: %s", shopify_id)
