"""Production-entry coverage for the inventory first-pair bootstrap.

The pair rows in this file are created only by product-binding and
location-mapping transitions, or by the scheduled scan's legacy repair.  The
one direct row removal is deliberately scoped to the legacy-reconciliation
test: it represents a pre-existing installation whose derived pair is
missing, not a normal fixture shortcut.
"""

import copy
import uuid
from unittest.mock import patch

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeSendResponse:

    def __init__(self, body):
        self._body = body
        self.status_code = 200
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install')
class TestInventoryPairBootstrap(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.inventory.service']
        cls.Store = cls.env['shopify.connector.store']
        cls.Mapping = cls.env['shopify.connector.location.mapping']
        cls.VariantBinding = cls.env[
            'shopify.connector.product.variant.binding'
        ]
        cls.LevelBinding = cls.env[
            'shopify.connector.inventory.level.binding'
        ]
        cls.Job = cls.env['shopify.connector.job']

        cls.store = cls.Store.create({
            'name': 'Inventory Pair Bootstrap Store',
            'shop_domain': 'inventory-pair-bootstrap.myshopify.com',
            'api_version': '2026-07',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'Inventory Pair Bootstrap Location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })

    def _new_chain(
        self, tag, gid=None, mapping_first=False, push_enabled=True,
        variant_status='active', mapping_status='active', location=None,
    ):
        """Create a real binding/mapping chain in either arrival order."""
        location = location or self.location
        template = self.env['product.template'].sudo().create({
            'name': 'Inventory Pair Bootstrap Product %s' % tag,
        })
        template_binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/%s' % tag,
            'product_template_id': template.id,
        })
        mapping = False
        if mapping_first:
            mapping = self.Mapping.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Location/%s' % tag,
                'odoo_location_id': location.id,
                'match_key': 'manual',
                'push_enabled': push_enabled,
                'status': mapping_status,
            })
        values = {
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/%s' % tag,
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        }
        if gid is not None:
            values.update({
                'shopify_inventory_item_gid': gid,
                'status': variant_status,
            })
        variant_binding = self.VariantBinding.sudo().create(values)
        if not mapping:
            mapping = self.Mapping.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Location/%s' % tag,
                'odoo_location_id': location.id,
                'match_key': 'manual',
                'push_enabled': push_enabled,
                'status': mapping_status,
            })
        return template, variant_binding, mapping

    def _pair(self, variant_binding, mapping):
        return self.LevelBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('product_variant_binding_id', '=', variant_binding.id),
            ('location_mapping_id', '=', mapping.id),
        ], limit=1)

    def test_variant_identity_then_mapping_creates_pair(self):
        gid = 'gid://shopify/InventoryItem/BOOTSTRAP-FIRST'
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-FIRST', gid=gid,
        )
        pair = self._pair(variant, mapping)
        self.assertTrue(pair)
        self.assertEqual(pair.shopify_inventory_item_gid, gid)
        self.assertEqual(pair.first_push_state, 'pending')

    def test_active_other_company_bootstraps_store_company_pair(self):
        """A real variant/mapping hook creates the pair for store company.

        This deliberately supplies both sides while a different allowed
        company is active, so the production loop and level-binding create
        cannot pass vacuously.
        """
        other_company = self.env['res.company'].sudo().create({
            'name': 'Pair Bootstrap Active Other Company',
        })
        OtherService = self.Service.sudo().with_context(
            allowed_company_ids=[
                other_company.id, self.store.company_id.id,
            ],
        ).with_company(other_company)
        self.assertEqual(OtherService.env.company, other_company)

        template = self.env['product.template'].sudo().create({
            'name': 'Pair Bootstrap Store Company Product',
            'company_id': self.store.company_id.id,
        })
        template_binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().with_context(
            allowed_company_ids=[
                other_company.id, self.store.company_id.id,
            ],
        ).with_company(other_company).create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/ACTIVE-OTHER-PAIR',
            'product_template_id': template.id,
        })
        gid = 'gid://shopify/InventoryItem/ACTIVE-OTHER-PAIR'
        variant = self.VariantBinding.sudo().with_context(
            allowed_company_ids=[
                other_company.id, self.store.company_id.id,
            ],
        ).with_company(other_company).create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/ACTIVE-OTHER-PAIR',
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
            'shopify_inventory_item_gid': gid,
        })
        mapping = self.Mapping.sudo().with_context(
            allowed_company_ids=[
                other_company.id, self.store.company_id.id,
            ],
        ).with_company(other_company).create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Location/ACTIVE-OTHER-PAIR',
            'odoo_location_id': self.location.id,
            'match_key': 'manual',
        })

        pair = self._pair(variant, mapping)
        self.assertTrue(pair)
        self.assertEqual(pair.shopify_inventory_item_gid, gid)
        self.assertEqual(
            pair.product_variant_binding_id.product_variant_id.company_id,
            self.store.company_id,
        )
        self.assertEqual(
            pair.location_mapping_id.odoo_location_id.company_id,
            self.store.company_id,
        )

    def test_foreign_location_is_skipped_and_level_binding_refused(self):
        """Bootstrap and its persistence constraint both fail closed."""
        other_company = self.env['res.company'].sudo().create({
            'name': 'Pair Bootstrap Truly Foreign Company',
        })
        OtherService = self.Service.sudo().with_context(
            allowed_company_ids=[
                other_company.id, self.store.company_id.id,
            ],
        ).with_company(other_company)
        self.assertEqual(OtherService.env.company, other_company)

        _template, variant, valid_mapping = self._new_chain(
            'FOREIGN-PAIR-GUARD',
            gid='gid://shopify/InventoryItem/FOREIGN-PAIR-GUARD',
            push_enabled=False,
        )
        self.assertFalse(self._pair(variant, valid_mapping))
        foreign = self.env['stock.location'].sudo().create({
            'name': 'Pair Bootstrap Truly Foreign Location',
            'usage': 'internal',
            'company_id': other_company.id,
        })
        # Plant a historical corrupt mapping and enable it without invoking
        # the ORM constraint. The production bootstrap must inspect this real
        # pair and skip it based on the owning store's company.
        self.env.cr.execute(
            'UPDATE shopify_connector_location_mapping '
            'SET odoo_location_id = %s, push_enabled = TRUE WHERE id = %s',
            (foreign.id, valid_mapping.id),
        )
        valid_mapping.invalidate_recordset([
            'odoo_location_id', 'push_enabled',
        ])
        self.assertEqual(valid_mapping.odoo_location_id, foreign)
        ensured = OtherService._bootstrap_inventory_level_bindings(
            variant_bindings=variant,
            location_mappings=valid_mapping,
        )
        self.assertFalse(ensured)
        self.assertFalse(self._pair(variant, valid_mapping))

        # Defense in depth: even a direct elevated create cannot persist the
        # invalid pair. This invokes the level-binding company constraint,
        # not merely the bootstrap's pre-check.
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                self.LevelBinding.sudo().with_context(
                    allowed_company_ids=[
                        other_company.id, self.store.company_id.id,
                    ],
                ).with_company(other_company).create({
                    'store_id': self.store.id,
                    'product_variant_binding_id': variant.id,
                    'location_mapping_id': valid_mapping.id,
                    'shopify_inventory_item_gid': (
                        variant.shopify_inventory_item_gid
                    ),
                })
        self.assertFalse(self._pair(variant, valid_mapping))

    def test_mapping_then_variant_identity_write_creates_pair(self):
        gid = 'gid://shopify/InventoryItem/BOOTSTRAP-REVERSE'
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-REVERSE', mapping_first=True,
        )
        self.assertFalse(self._pair(variant, mapping))
        variant.sudo().write({'shopify_inventory_item_gid': gid})
        pair = self._pair(variant, mapping)
        self.assertTrue(pair)
        self.assertEqual(pair.shopify_inventory_item_gid, gid)

    def test_repeated_transitions_are_idempotent(self):
        gid = 'gid://shopify/InventoryItem/BOOTSTRAP-REPEAT'
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-REPEAT', gid=gid,
        )
        first = self._pair(variant, mapping)
        mapping.sudo().write({'push_enabled': True})
        variant.sudo().write({'shopify_inventory_item_gid': gid})
        self.Service._bootstrap_inventory_level_bindings(
            variant_bindings=variant,
            location_mappings=mapping,
        )
        pairs = self.LevelBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('product_variant_binding_id', '=', variant.id),
            ('location_mapping_id', '=', mapping.id),
        ])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs.id, first.id)

    def test_store_scope_never_crosses_to_another_store(self):
        other_store = self.Store.create({
            'name': 'Inventory Pair Bootstrap Other Store',
            'shop_domain': 'inventory-pair-bootstrap-other.myshopify.com',
            'api_version': '2026-07',
        })
        _template, variant, _mapping = self._new_chain(
            'BOOTSTRAP-SCOPE-A',
            gid='gid://shopify/InventoryItem/BOOTSTRAP-SCOPE-A',
        )
        other_mapping = self.Mapping.sudo().create({
            'store_id': other_store.id,
            'shopify_gid': 'gid://shopify/Location/BOOTSTRAP-SCOPE-B',
            'odoo_location_id': self.location.id,
            'match_key': 'manual',
        })
        self.Service._bootstrap_inventory_level_bindings(
            variant_bindings=variant,
            location_mappings=other_mapping,
        )
        self.assertFalse(self.LevelBinding.sudo().search([
            ('product_variant_binding_id', '=', variant.id),
            ('location_mapping_id', '=', other_mapping.id),
        ]))

    def test_legacy_missing_pair_is_recreated_by_reconciliation_helper(self):
        gid = 'gid://shopify/InventoryItem/BOOTSTRAP-LEGACY'
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-LEGACY', gid=gid,
        )
        pair = self._pair(variant, mapping)
        self.assertTrue(pair)
        # This is the only manufactured intermediate state in the suite: a
        # legacy database upgraded with the derived row missing.
        self.env.cr.execute(
            'DELETE FROM shopify_connector_inventory_level_binding '
            'WHERE id = %s', (pair.id,),
        )
        self.env.invalidate_all()
        self.assertFalse(self._pair(variant, mapping))
        self.Service._bootstrap_inventory_level_bindings(
            store=self.store,
        )
        repaired = self._pair(variant, mapping)
        self.assertTrue(repaired)
        self.assertEqual(repaired.shopify_inventory_item_gid, gid)

    def test_scan_repairs_missing_pair_and_admits_first_preview(self):
        gid = 'gid://shopify/InventoryItem/BOOTSTRAP-SCAN'
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-SCAN', gid=gid,
        )
        pair = self._pair(variant, mapping)
        self.assertTrue(pair)
        self.env.cr.execute(
            'DELETE FROM shopify_connector_inventory_level_binding '
            'WHERE id = %s', (pair.id,),
        )
        self.env.invalidate_all()

        scan_jobs = self.Service.run_inventory_push_scan().filtered(
            lambda job: job.store_id == self.store,
        )
        self.assertTrue(scan_jobs)
        for scan_job in scan_jobs:
            scan_job.sudo().write({'state': 'running'})
            self.Service._handle_inventory_push_scan(scan_job)

        repaired = self._pair(variant, mapping)
        self.assertTrue(repaired)
        self.assertTrue(self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_first_push_preview'),
            ('res_id', '=', repaired.id),
        ]))

    def test_missing_inventory_item_identity_never_creates_pair(self):
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-NO-ID', mapping_first=True,
        )
        self.assertFalse(variant.shopify_inventory_item_gid)
        self.Service._bootstrap_inventory_level_bindings(
            variant_bindings=variant,
            location_mappings=mapping,
        )
        self.assertFalse(self._pair(variant, mapping))

    def test_disabled_mapping_waits_until_push_is_enabled(self):
        _template, variant, mapping = self._new_chain(
            'BOOTSTRAP-DISABLED',
            gid='gid://shopify/InventoryItem/BOOTSTRAP-DISABLED',
            mapping_first=True,
            push_enabled=False,
        )
        self.assertFalse(self._pair(variant, mapping))
        mapping.sudo().write({'push_enabled': True})
        self.assertTrue(self._pair(variant, mapping))

    def test_stale_variant_or_mapping_is_not_bootstrapped(self):
        _template, stale_variant, mapping = self._new_chain(
            'BOOTSTRAP-STALE-VARIANT',
            gid='gid://shopify/InventoryItem/BOOTSTRAP-STALE-VARIANT',
            variant_status='stale',
        )
        self.assertFalse(self._pair(stale_variant, mapping))
        stale_variant.sudo().write({'status': 'active'})
        self.assertTrue(self._pair(stale_variant, mapping))

        _template, variant, stale_mapping = self._new_chain(
            'BOOTSTRAP-STALE-MAPPING',
            gid='gid://shopify/InventoryItem/BOOTSTRAP-STALE-MAPPING',
            mapping_first=True,
            mapping_status='stale',
            location=self.env['stock.location'].create({
                'name': 'Inventory Pair Bootstrap Stale Mapping Location',
                'usage': 'internal',
                'location_id': self.location.location_id.id,
            }),
        )
        self.assertFalse(self._pair(variant, stale_mapping))
        stale_mapping.sudo().write({'status': 'active'})
        self.assertTrue(self._pair(variant, stale_mapping))

    def test_tracked_false_is_evidence_only_and_does_not_change_odoo_product(self):
        template, variant, mapping = self._new_chain(
            'BOOTSTRAP-UNTRACKED',
            gid='gid://shopify/InventoryItem/BOOTSTRAP-UNTRACKED',
            mapping_first=True,
        )
        before = template.product_variant_id.is_storable
        variant.sudo().write({
            'shopify_inventory_tracked': False,
            'shopify_inventory_tracked_known': True,
        })
        self.assertTrue(self._pair(variant, mapping))
        self.assertEqual(template.product_variant_id.is_storable, before)


@tagged('post_install', '-at_install')
class TestInventoryPairBootstrapFromProductImport(TransactionCase):
    """The real GraphQL import path must drive the same production hook."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Inventory Pair Import Store',
            'shop_domain': 'inventory-pair-import.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'product_domain_enabled': True,
        })
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        location = cls.env['stock.location'].create({
            'name': 'Inventory Pair Import Location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/IMPORT',
            'odoo_location_id': location.id,
            'match_key': 'manual',
            'push_enabled': True,
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.Job = cls.env['shopify.connector.job']

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _import_job(self, product_gid):
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': product_gid,
        })
        self.env.flush_all()
        return job

    def _patch_import_transport(self):
        product_gid = 'gid://shopify/Product/BOOTSTRAP-IMPORT'
        variant_gid = 'gid://shopify/ProductVariant/BOOTSTRAP-IMPORT'
        response = {
            'data': {
                'product': {
                    'id': product_gid,
                    'title': 'Bootstrap Import Product',
                    'status': 'ACTIVE',
                    'descriptionHtml': '',
                    'vendor': 'Bootstrap Vendor',
                    'productType': 'Goods',
                    'tags': [],
                    'featuredImage': None,
                    'variants': {
                        'nodes': [{
                            'id': variant_gid,
                            'sku': 'BOOTSTRAP-IMPORT-SKU',
                            'barcode': None,
                            'price': 19.95,
                            'compareAtPrice': None,
                            'selectedOptions': [{
                                'name': 'Title',
                                'value': 'Default Title',
                            }],
                            'image': None,
                            'inventoryItem': {
                                'id': (
                                    'gid://shopify/InventoryItem/'
                                    'BOOTSTRAP-IMPORT'
                                ),
                                'tracked': False,
                            },
                        }],
                        'pageInfo': {
                            'hasNextPage': False,
                            'endCursor': None,
                        },
                    },
                },
            },
        }

        def fake_send(client_self, store, body, token=None):
            # A real HTTP response is decoded into a fresh object per request.
            # The importer deliberately consumes/replaces pagination state,
            # so replaying the same mutable test dictionary would manufacture
            # a malformed second response with no ``variants.pageInfo``.
            return _FakeSendResponse(copy.deepcopy(response))

        return patch.object(
            type(self.env['shopify.connector.api.client']),
            '_send', fake_send,
        ), product_gid

    def test_raw_import_response_creates_one_pair_and_replay_is_idempotent(self):
        transport, product_gid = self._patch_import_transport()
        with transport:
            first = self.Importer.import_product_sync(
                self.store, product_gid,
                job=self._import_job(product_gid),
            )
            second = self.Importer.import_product_sync(
                self.store, product_gid,
                job=self._import_job(product_gid),
            )

        self.assertEqual(
            first['variant_bindings'].shopify_inventory_item_gid,
            'gid://shopify/InventoryItem/BOOTSTRAP-IMPORT',
        )
        self.assertEqual(
            second['variant_bindings'].shopify_inventory_item_gid,
            'gid://shopify/InventoryItem/BOOTSTRAP-IMPORT',
        )
        pairs = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().search([
            ('store_id', '=', self.store.id),
            ('product_variant_binding_id', '=',
             first['variant_bindings'].id),
        ])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(
            pairs.shopify_inventory_item_gid,
            'gid://shopify/InventoryItem/BOOTSTRAP-IMPORT',
        )
