# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from .base_importer import BaseImporter
from .checksum import compute_checksum
from ..shopify_api.queries.collection import FETCH_COLLECTIONS

_logger = logging.getLogger(__name__)


class CollectionImporter(BaseImporter):
    entity_name = 'collection'
    binding_model = 'shopify.collection.binding'

    def _compute_shopify_checksum(self, node):
        return compute_checksum({
            'title': node.get('title', ''),
            'handle': node.get('handle', ''),
        })

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id')
        title = node.get('title', 'Untitled')
        checksum = self._compute_shopify_checksum(node)
        product_count = node.get('productsCount', {}).get('count', 0)

        if existing_binding:
            existing_binding.odoo_id.write({'name': title})
            existing_binding.write({
                'shopify_title': title,
                'shopify_handle': node.get('handle', ''),
                'product_count': product_count,
            })
            existing_binding._mark_synced(checksum=checksum)
        else:
            category = self.env['product.category'].search([
                ('name', '=', title),
            ], limit=1)
            if not category:
                category = self.env['product.category'].create({'name': title})

            self.env['shopify.collection.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': category.id,
                'shopify_id': shopify_id,
                'shopify_title': title,
                'shopify_handle': node.get('handle', ''),
                'product_count': product_count,
                'sync_status': 'synced',
                'sync_checksum': checksum,
                'last_sync_date': fields.Datetime.now(),
            })


class CollectionSync:
    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = CollectionImporter(env, backend)

    def import_collections(self):
        nodes = self.importer.client.fetch_paginated(
            FETCH_COLLECTIONS, 'collections',
            page_size=self.backend.batch_size,
            estimated_cost_per_page=10,
        )
        return self.importer.import_batch(nodes)
