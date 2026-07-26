import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

# CORE-R2 Slice 2B: the product importer now issues every Shopify Admin page
# call through the core `execute_business` admission-lease context manager
# (`_send` transport seam), not the legacy value-returning `execute()`. The
# transport test below drives the REAL admission gate: it seeds a store
# credential, connects the store, and converts the accepted Task 010B
# normalized-response fixture into a `_send` transport stub. `DUMMY_TOKEN` is a
# non-secret test constant (never a live token); no live Shopify request runs.
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeSendResponse:
    """Minimal `requests.Response` stand-in for the `_send` transport seam.
    `_normalize_response` reads `.status_code`, `.json()`, `.headers` and
    `.text` only; the JSON body is the accepted Task 010B fixture dict,
    consumed unchanged (so `{'data': {...}}` normalizes to the same result the
    legacy `execute()` returned)."""

    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        # The API-version ruling (2026-07-26) makes `_normalize_response`
        # fail closed when the response carries no `X-Shopify-API-Version`
        # header, so a fake transport response has to state the version it
        # is pretending to have been served by -- exactly as a real one
        # does. An explicit `headers` argument still overrides this.
        self.headers = headers or {
            API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
        }
        self.text = ''

    def json(self):
        return self._body


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestProductVariantGeneration(TransactionCase):
    """D-010B-3: deterministic creation of exactly the Shopify variants
    (sparse sets, no cartesian phantoms, idempotent re-import)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Variant Generation Test Store',
            'shop_domain': 'variant-generation-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Job = cls.env['shopify.connector.job']
        # Seed a credential while the store is still `setup_incomplete`, so no
        # `connection_generation` bump occurs (a `connected` `action_set_token`
        # would bump it); the store therefore stays at generation 0, matching a
        # directly-created job's default `expected_connection_generation`.
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # `execute_business._admit` runs its gate/lease on a `registry.cursor()`
        # side transaction; under a plain TransactionCase that cursor cannot see
        # this test's uncommitted fixture, so admission would fail closed. Entering
        # registry test mode makes every `registry.cursor()` reuse the single test
        # connection as a TestCursor (the sanctioned core-test mechanism); it
        # changes no production behaviour and is auto-left on teardown.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _import_job(self, shopify_target_gid):
        """Connect the store (the business-job create gate requires it) and
        return a product-import job whose captured generation matches the store
        (both 0), so `execute_business._admit` admits it. Flush so the admission
        side cursor observes the store/job."""
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': shopify_target_gid,
        })
        self.env.flush_all()
        return job

    def _patch_send(self, fake_execute):
        """Route an accepted normalized-response `fake_execute(self, store,
        query, variables=None)` fixture through the real `execute_business`
        gate by patching only the `_send` transport seam."""
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            outcome = fake_execute(
                client_self, store, body.get('query'), body.get('variables'),
            )
            return _FakeSendResponse(outcome)

        return patch.object(type(Client), '_send', fake_send)

    def _variant(self, gid, selected, sku=None, price=None):
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': price,
            'compare_at_price': None,
            'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': None,
        }

    def _payload(self, gid, options, variants):
        return {
            'gid': gid, 'title': 'Variant Product', 'status': 'active',
            'updated_at': None, 'image_url': None,
            'options': options, 'variants': variants,
        }

    def _option(self, name, values, position=1):
        return {'name': name, 'position': position, 'values': list(values)}

    def _combo_names(self, product):
        return {
            (ptav.attribute_id.name, ptav.product_attribute_value_id.name)
            for ptav in product.product_template_attribute_value_ids
        }

    # ------------------------------------------------------------------
    # Sparse two-option set: 2 of 4 possible combinations.
    # ------------------------------------------------------------------

    def test_sparse_two_option_set_no_cartesian_extras(self):
        payload = self._payload(
            'gid://shopify/Product/3001',
            options=[
                self._option('SC010B VG Color', ['Red', 'Blue'], position=1),
                self._option('SC010B VG Size', ['S', 'M'], position=2),
            ],
            variants=[
                self._variant('gid://shopify/ProductVariant/3001a', [
                    {'name': 'SC010B VG Color', 'value': 'Red'},
                    {'name': 'SC010B VG Size', 'value': 'S'},
                ], sku='RS'),
                self._variant('gid://shopify/ProductVariant/3001b', [
                    {'name': 'SC010B VG Color', 'value': 'Blue'},
                    {'name': 'SC010B VG Size', 'value': 'M'},
                ], sku='BM'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        # Cartesian product is 4; Shopify has exactly 2 -> Odoo has 2.
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(len(result['variant_bindings']), 2)
        combos = {
            frozenset(self._combo_names(product))
            for product in template.product_variant_ids
        }
        self.assertEqual(combos, {
            frozenset({('SC010B VG Color', 'Red'), ('SC010B VG Size', 'S')}),
            frozenset({('SC010B VG Color', 'Blue'), ('SC010B VG Size', 'M')}),
        })

    def test_sparse_three_option_set_exact_equality(self):
        payload = self._payload(
            'gid://shopify/Product/3002',
            options=[
                self._option('SC010B VG Color', ['Red', 'Blue'], position=1),
                self._option('SC010B VG Size', ['S', 'M'], position=2),
                self._option('SC010B VG Fit', ['Slim', 'Loose'], position=3),
            ],
            variants=[
                self._variant('gid://shopify/ProductVariant/3002a', [
                    {'name': 'SC010B VG Color', 'value': 'Red'},
                    {'name': 'SC010B VG Size', 'value': 'S'},
                    {'name': 'SC010B VG Fit', 'value': 'Slim'},
                ], sku='RSS'),
                self._variant('gid://shopify/ProductVariant/3002b', [
                    {'name': 'SC010B VG Color', 'value': 'Blue'},
                    {'name': 'SC010B VG Size', 'value': 'M'},
                    {'name': 'SC010B VG Fit', 'value': 'Loose'},
                ], sku='BML'),
                self._variant('gid://shopify/ProductVariant/3002c', [
                    {'name': 'SC010B VG Color', 'value': 'Red'},
                    {'name': 'SC010B VG Size', 'value': 'M'},
                    {'name': 'SC010B VG Fit', 'value': 'Slim'},
                ], sku='RMS'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        # Cartesian is 8; Shopify has exactly 3.
        self.assertEqual(len(template.product_variant_ids), 3)
        self.assertEqual(len(result['variant_bindings']), 3)

    def test_variant_bindings_map_to_correct_products(self):
        payload = self._payload(
            'gid://shopify/Product/3003',
            options=[self._option('SC010B VG Color', ['Red', 'Blue'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/3003a',
                              [{'name': 'SC010B VG Color', 'value': 'Red'}], sku='R'),
                self._variant('gid://shopify/ProductVariant/3003b',
                              [{'name': 'SC010B VG Color', 'value': 'Blue'}], sku='B'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        for binding in result['variant_bindings']:
            combo = self._combo_names(binding.product_variant_id)
            self.assertEqual(len(combo), 1)

    # ------------------------------------------------------------------
    # Deterministic re-import idempotency.
    # ------------------------------------------------------------------

    def test_reimport_is_idempotent_no_duplicate_variants(self):
        payload = self._payload(
            'gid://shopify/Product/3004',
            options=[
                self._option('SC010B VG Color', ['Red', 'Blue'], position=1),
                self._option('SC010B VG Size', ['S', 'M'], position=2),
            ],
            variants=[
                self._variant('gid://shopify/ProductVariant/3004a', [
                    {'name': 'SC010B VG Color', 'value': 'Red'},
                    {'name': 'SC010B VG Size', 'value': 'S'},
                ], sku='RS4'),
                self._variant('gid://shopify/ProductVariant/3004b', [
                    {'name': 'SC010B VG Color', 'value': 'Blue'},
                    {'name': 'SC010B VG Size', 'value': 'M'},
                ], sku='BM4'),
            ],
        )
        first = self.Importer._apply_import(self.store, payload)
        template = first['template_binding'].product_template_id
        second = self.Importer._apply_import(self.store, payload)
        self.assertEqual(first['template_binding'], second['template_binding'])
        self.assertEqual(len(second['variant_bindings']), 2)
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            self.VariantBinding.search_count([
                ('product_template_binding_id', '=', first['template_binding'].id),
            ]), 2,
        )

    # ------------------------------------------------------------------
    # New remote variant on refresh -> instantiated additively (structural
    # addition applies in both refresh modes).
    # ------------------------------------------------------------------

    def test_refresh_adds_new_remote_variant(self):
        gid = 'gid://shopify/Product/3005'
        payload_1 = self._payload(
            gid,
            options=[self._option('SC010B VG Color', ['Red'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/3005a',
                              [{'name': 'SC010B VG Color', 'value': 'Red'}], sku='R5'),
            ],
        )
        first = self.Importer._apply_import(self.store, payload_1)
        template = first['template_binding'].product_template_id
        self.assertEqual(len(template.product_variant_ids), 1)

        payload_2 = self._payload(
            gid,
            options=[self._option('SC010B VG Color', ['Red', 'Green'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/3005a',
                              [{'name': 'SC010B VG Color', 'value': 'Red'}], sku='R5'),
                self._variant('gid://shopify/ProductVariant/3005b',
                              [{'name': 'SC010B VG Color', 'value': 'Green'}], sku='G5'),
            ],
        )
        second = self.Importer._apply_import(self.store, payload_2)
        self.assertEqual(len(second['variant_bindings']), 2)
        self.assertEqual(len(template.product_variant_ids), 2)

    # ------------------------------------------------------------------
    # Structural mismatch on a merchant's bound product -> binding_conflict.
    # ------------------------------------------------------------------

    def test_structural_mismatch_routes_to_binding_conflict(self):
        # A merchant template bound to this GID uses an 'always' attribute
        # that cannot represent the incoming sparse variant combination.
        attribute = self.env['product.attribute'].create({
            'name': 'SC010B VG Grade', 'create_variant': 'always',
        })
        template = self.env['product.template'].create({
            'name': 'Merchant Graded Product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(0, 0, {'name': 'A', 'attribute_id': attribute.id})],
            })],
        })
        binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/3006',
            'product_template_id': template.id,
            'match_key': 'manual',
        })
        payload = self._payload(
            'gid://shopify/Product/3006',
            options=[self._option('SC010B VG Grade', ['A', 'B'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/3006b',
                              [{'name': 'SC010B VG Grade', 'value': 'B'}], sku='GB'),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertTrue(binding.exists())

    # ------------------------------------------------------------------
    # Later-variant failure rolls back the whole structured import.
    # ------------------------------------------------------------------

    def test_later_variant_failure_rolls_back_everything(self):
        # Variant b references an option value that is not in the product's
        # declared options and is not used by any earlier variant, so it
        # cannot be represented -> binding_conflict rolls back variant a too.
        templates_before = self.env['product.template'].search_count([])
        payload = self._payload(
            'gid://shopify/Product/3007',
            options=[self._option('SC010B VG Color', ['Red'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/3007a',
                              [{'name': 'SC010B VG Color', 'value': 'Red'}], sku='OK7'),
                self._variant('gid://shopify/ProductVariant/3007b',
                              [{'name': 'SC010B VG Finish', 'value': 'Matte'}], sku='BAD7'),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/3007'),
        ]))
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/ProductVariant/3007a'),
        ]))

    # ------------------------------------------------------------------
    # 150-variant paginated fixture imports completely (D-010B-1/§5).
    # ------------------------------------------------------------------

    def test_one_hundred_fifty_variant_paginated_fixture(self):
        gid = 'gid://shopify/Product/3150'
        total = 150
        option_values = [{'id': 'ov%d' % i, 'name': 'V%d' % i} for i in range(total)]
        nodes = [
            {
                'id': '%s/v/%d' % (gid, i), 'sku': 'F150-%d' % i, 'barcode': None,
                'price': '5.00', 'compareAtPrice': None,
                'selectedOptions': [{'name': 'SC010B VG Paginated', 'value': 'V%d' % i}],
                'image': None, 'inventoryItem': None,
            }
            for i in range(total)
        ]

        def fake_execute(client_self, store, query, variables=None):
            cursor = (variables or {}).get('cursor')
            if cursor is None:
                page_nodes, has_next, end = nodes[:100], True, 'c-0'
            else:
                page_nodes, has_next, end = nodes[100:], False, None
            return {
                'data': {
                    'product': {
                        'id': gid, 'title': '150 Variant', 'status': 'ACTIVE',
                        'featuredImage': None,
                        'options': [{
                            'id': 'opt', 'name': 'SC010B VG Paginated', 'position': 1,
                            'optionValues': option_values,
                        }],
                        'variants': {
                            'nodes': page_nodes,
                            'pageInfo': {'hasNextPage': has_next, 'endCursor': end},
                        },
                    },
                },
            }

        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertEqual(len(result['variant_bindings']), 150)
        self.assertEqual(
            len(result['template_binding'].product_template_id.product_variant_ids),
            150,
        )
