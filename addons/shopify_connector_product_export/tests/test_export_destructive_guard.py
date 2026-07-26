"""Every difference that would need a remote deletion fails closed.

These are the tests the whole module exists for. Each names a specific thing a
naive export would delete, and asserts that this one does not.
"""

from odoo.tests.common import tagged

from ..models.shopify_connector_product_export_service import (
    JOB_TYPE_VARIANTS_CREATE,
    JOB_TYPE_VARIANTS_UPDATE,
)
from .common import ExportCase, PRODUCT_GID, VARIANT_GID


@tagged('post_install', '-at_install')
class TestExportDestructiveGuard(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template()

    def _remote(self, variants=None, options=None):
        return {
            'id': PRODUCT_GID,
            'title': 'Exportable Widget',
            'descriptionHtml': '<p>A widget.</p>',
            'vendor': 'Adams',
            'productType': 'Widgets',
            'tags': ['alpha', 'beta'],
            'status': 'DRAFT',
            'updatedAt': '2026-07-26T00:00:00Z',
            'options': options if options is not None else [],
            'variants': {'nodes': variants or []},
        }

    def _read(
        self, variants=None, options=None, has_collections=False,
        has_metafields=False, has_media=False,
    ):
        """The shape `_read_remote_product` returns, built locally."""
        return {
            'store_identity': self.store.shop_domain,
            'exists': True,
            'product': self._remote(variants=variants, options=options),
            'variants': variants or [],
            'updated_at': '2026-07-26T00:00:00Z',
            'has_collections': has_collections,
            'has_metafields': has_metafields,
            'has_media': has_media,
        }

    def _bound_remote_variant(self):
        return {
            'id': VARIANT_GID,
            'barcode': '0001',
            'price': '12.50',
            'compareAtPrice': None,
            'inventoryItem': {'id': 'gid://shopify/InventoryItem/1',
                              'sku': 'WIDGET-1'},
            'selectedOptions': [],
        }

    # ------------------------------------------------------------------
    # A remote variant the connector does not own is never deleted
    # ------------------------------------------------------------------

    def test_an_unowned_remote_variant_is_disclosed_and_left_alone(self):
        foreign = {
            'id': 'gid://shopify/ProductVariant/999',
            'barcode': 'FOREIGN',
            'price': '99.00',
            'compareAtPrice': None,
            'inventoryItem': {'id': 'gid://shopify/InventoryItem/9',
                              'sku': 'MERCHANT-SKU'},
            'selectedOptions': [],
        }
        plan = self.Service._diff_variants(
            self.store, self.binding, self._remote(),
            [self._bound_remote_variant(), foreign],
            self.template.product_variant_ids, True,
        )
        kinds = [item['kind'] for item in plan['blocked']]
        self.assertIn('unowned_remote_variant', kinds)
        blocked = next(
            item for item in plan['blocked']
            if item['kind'] == 'unowned_remote_variant'
        )
        self.assertEqual(
            blocked['remote_variant_gid'], 'gid://shopify/ProductVariant/999',
        )
        self.assertEqual(blocked['remote_sku'], 'MERCHANT-SKU')
        # It is not in any executable list.
        self.assertNotIn(
            'gid://shopify/ProductVariant/999',
            [entry['id'] for entry in plan['update']],
        )

    def test_a_bound_variant_missing_remotely_routes_to_review(self):
        """Creating a replacement would duplicate; deleting the binding would
        erase evidence. Neither is available, so it is a review case."""
        plan = self.Service._diff_variants(
            self.store, self.binding, self._remote(), [],
            self.template.product_variant_ids, True,
        )
        kinds = [item['kind'] for item in plan['blocked']]
        self.assertIn('bound_variant_missing_remotely', kinds)
        self.assertFalse(plan['update'])

    # ------------------------------------------------------------------
    # Option divergence is refused, never reshaped
    # ------------------------------------------------------------------

    def test_option_divergence_is_detected_in_both_directions(self):
        self.assertTrue(self.Service._options_diverge(
            [{'name': 'Size', 'values': ['S', 'M']}],
            [{'name': 'Size', 'values': ['S']}],
        ))
        self.assertTrue(self.Service._options_diverge(
            [{'name': 'Size', 'values': ['S']}],
            [{'name': 'Colour', 'values': ['S']}],
        ))
        self.assertTrue(self.Service._options_diverge(
            [], [{'name': 'Size', 'values': ['S']}],
        ))
        self.assertFalse(self.Service._options_diverge(
            [{'name': 'Size', 'values': ['S', 'M']}],
            [{'name': 'Size', 'values': ['M', 'S']}],
        ))

    def test_variant_writes_are_withheld_while_options_diverge(self):
        """`optionValues` are positional against the remote option set, so
        writing them against a different structure is how a variant ends up
        describing the wrong thing."""
        remote_options = [{
            'id': 'gid://shopify/ProductOption/1',
            'name': 'Size',
            'position': 1,
            'optionValues': [{'id': 'x', 'name': 'S'},
                             {'id': 'y', 'name': 'M'}],
        }]
        diff, steps, blocked = self.Service._preview_update_path(
            self.store, self.template, self.binding,
            self.Service._desired_scalars(self.template),
            [],  # Odoo has no attribute lines -> divergence
            self.template.product_variant_ids, True,
            self._read(
                variants=[self._bound_remote_variant()],
                options=remote_options,
            ),
        )
        kinds = [item['kind'] for item in blocked]
        self.assertIn('remote_option_divergence', kinds)
        self.assertNotIn(
            JOB_TYPE_VARIANTS_UPDATE, [step['step'] for step in steps],
        )
        self.assertNotIn(
            JOB_TYPE_VARIANTS_CREATE, [step['step'] for step in steps],
        )

    # ------------------------------------------------------------------
    # Merchant-owned surfaces are disclosed as untouched, never targeted
    # ------------------------------------------------------------------

    def test_merchant_surfaces_are_reported_untouched_not_omitted(self):
        diff, steps, blocked = self.Service._preview_update_path(
            self.store, self.template, self.binding,
            self.Service._desired_scalars(self.template), [],
            self.template.product_variant_ids, True,
            self._read(
                variants=[self._bound_remote_variant()],
                has_collections=True, has_metafields=True, has_media=True,
            ),
        )
        untouched = diff['untouched']
        self.assertTrue(untouched['collections'])
        self.assertTrue(untouched['metafields'])
        self.assertTrue(untouched['existing_media'])
        self.assertIn('never included', untouched['note'])

    # ------------------------------------------------------------------
    # No delete mutation exists anywhere in this module
    # ------------------------------------------------------------------

    def test_no_forbidden_mutation_appears_in_any_graphql_document(self):
        """Scan the GraphQL documents this module builds, not its prose.

        A plain string search over the source would flag the guard constant
        that lists forbidden field names and every comment explaining WHY a
        mutation is not used, so it would fail for exactly the right
        intentions. This inspects string literals that are GraphQL documents
        (they contain a `mutation ` or `query ` keyword) and asserts that no
        destructive operation appears in one.
        """
        import ast
        import pathlib
        import re

        # A GraphQL DOCUMENT, not a sentence that happens to say "mutation".
        # `mutation Name(` / `query Name(` / `query Name {` anchored at the
        # start is what this module's operation strings actually look like, and
        # what no docstring or manifest description looks like.
        document_re = re.compile(r'^\s*(mutation|query)\s+\w+\s*[({]')
        forbidden = (
            'productDelete', 'productVariantsBulkDelete', 'fileDelete',
            'productDeleteMedia', 'productCreateMedia', 'productUpdateMedia',
            'productVariantDetachMedia', 'productReorderMedia',
            'collectionRemoveProducts', 'metafieldsDelete',
            'metafieldDefinitionDelete', 'productOptionsDelete',
            'productOptionUpdate', 'publishablePublish',
            'inventoryQuantities', 'referencesToRemove',
            'collectionsToLeave',
        )
        root = pathlib.Path(__file__).resolve().parent.parent
        offenders = []
        for path in sorted(root.rglob('*.py')):
            if 'tests' in path.parts:
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                if not isinstance(node.value, str):
                    continue
                document = node.value
                if not document_re.match(document):
                    continue
                for token in forbidden:
                    if token in document:
                        offenders.append((path.name, token))
        self.assertEqual(
            offenders, [],
            'a destructive operation appears in a GraphQL document',
        )

    def test_the_forbidden_key_guard_covers_every_merchant_list_field(self):
        """The guard list is the mechanical form of the ownership matrix, so
        it must actually name every merchant-owned list surface."""
        from ..models.shopify_connector_product_export_service import (
            FORBIDDEN_UPDATE_KEYS,
        )
        for key in (
            'collections', 'collectionsToJoin', 'collectionsToLeave',
            'metafields', 'files', 'media', 'variants', 'productOptions',
            'inventoryQuantities',
        ):
            self.assertIn(key, FORBIDDEN_UPDATE_KEYS)
