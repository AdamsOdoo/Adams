"""The mutation-split rules from the 2026-07-26 ruling, asserted mechanically.

These are the tests that make the ruling structural rather than aspirational:
each one fails if a future edit routes an existing product through
`productSet`, echoes merchant list state into an update, or lets a variant
batch apply partially.
"""

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from ..models.shopify_connector_product_export_service import (
    ExportPreC2FailClosedError,
    FORBIDDEN_UPDATE_KEYS,
    JOB_TYPE_CREATE,
    JOB_TYPE_UPDATE,
    JOB_TYPE_VARIANTS_CREATE,
    JOB_TYPE_VARIANTS_UPDATE,
    assert_no_forbidden_keys,
)
from .common import ExportCase, PRODUCT_GID, VARIANT_GID


# Issue #193 / #157 -- Odoo 19 test-phase contract. These fixtures insert rows
# into Odoo business tables (product.template/res.partner/res.users) whose NOT
# NULL columns are contributed by modules outside this module's dependency
# closure (stock.tracking, account.autopost_bills). post_install runs after
# every module is loaded, which is the only phase where those fields exist on
# the model.
@tagged('post_install', '-at_install')
class TestExportMutationStrategy(ExportCase):

    # ------------------------------------------------------------------
    # productSet may never target an existing binding
    # ------------------------------------------------------------------

    def test_product_set_refused_for_an_existing_binding(self):
        binding = self.bind_template()
        snapshot = {
            'store_id': self.store.id,
            'preview_id': 0,
            'remote_product_gid': binding.shopify_gid,
            'binding_id': binding.id,
        }
        with self.assertRaises(ExportPreC2FailClosedError) as catcher:
            self.Service._assert_no_product_set_on_existing(
                'mutation X { productSet(input: $i) { product { id } } }',
                snapshot,
            )
        self.assertEqual(
            catcher.exception.error_class, 'destructive_write_guard_blocked',
        )

    def test_product_set_allowed_only_with_no_binding_and_no_gid(self):
        snapshot = {
            'store_id': self.store.id,
            'preview_id': 0,
            'remote_product_gid': '',
            'binding_id': False,
        }
        self.assertTrue(
            self.Service._assert_no_product_set_on_existing(
                'mutation X { productSet(input: $i) { product { id } } }',
                snapshot,
            )
        )

    def test_every_update_path_operation_avoids_product_set(self):
        """The three update mutations must not mention productSet at all."""
        binding = self.bind_template()
        preview = self.make_preview(
            export_path='update', binding=binding, state='applying',
            steps=[
                {'step': JOB_TYPE_UPDATE, 'state': 'pending',
                 'fields': ['title']},
                {'step': JOB_TYPE_VARIANTS_UPDATE, 'state': 'pending',
                 'variant_gids': [VARIANT_GID]},
            ],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        snapshot = self.Service._prepare_local_common(
            self.make_job(
                JOB_TYPE_UPDATE, preview._name, preview.id, PRODUCT_GID,
            )
        )
        request = self.Service._prepare_preconditions_update(snapshot, {})
        self.assertIn('productUpdate', request['operation'])
        self.assertNotIn('productSet', request['operation'])

        variants_snapshot = self.Service._prepare_local_common(
            self.make_job(
                JOB_TYPE_VARIANTS_UPDATE, preview._name, preview.id,
                PRODUCT_GID,
            )
        )
        variants_request = self.Service._prepare_preconditions_variants_update(
            variants_snapshot, {},
        )
        self.assertIn(
            'productVariantsBulkUpdate', variants_request['operation'],
        )
        self.assertNotIn('productSet', variants_request['operation'])
        # allowPartialUpdates must be explicitly false: a half-applied variant
        # batch is the hardest state to reason about afterwards.
        self.assertIs(
            variants_request['variables']['allowPartialUpdates'], False,
        )

    # ------------------------------------------------------------------
    # No merchant-owned list state in an update variable tree
    # ------------------------------------------------------------------

    def test_forbidden_keys_are_refused_at_any_depth(self):
        for key in sorted(FORBIDDEN_UPDATE_KEYS):
            with self.subTest(key=key):
                with self.assertRaises(ValidationError):
                    assert_no_forbidden_keys(
                        {'product': {'title': 'x'},
                         'variants': [{'id': 'v', key: ['anything']}]}
                        if key != 'variants' else {'product': {key: []}}
                    )

    def test_update_variables_carry_no_merchant_list_state(self):
        binding = self.bind_template()
        preview = self.make_preview(
            export_path='update', binding=binding, state='applying',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title', 'tags']}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        snapshot = self.Service._prepare_local_common(
            self.make_job(
                JOB_TYPE_UPDATE, preview._name, preview.id, PRODUCT_GID,
            )
        )
        request = self.Service._prepare_preconditions_update(snapshot, {})
        product_input = request['variables']['product']
        for key in (
            'collections', 'collectionsToJoin', 'collectionsToLeave',
            'metafields', 'files', 'media', 'variants', 'productOptions',
        ):
            self.assertNotIn(key, product_input)
        # Targeting is through `identifier.id`, the preferred form —
        # `ProductSetInput.id` still exists but is deprecated, and
        # `productUpdate` takes its target outside the input object.
        self.assertEqual(
            request['variables']['identifier'], {'id': PRODUCT_GID},
        )

    def test_scalar_update_carries_only_confirmed_fields(self):
        binding = self.bind_template()
        preview = self.make_preview(
            export_path='update', binding=binding, state='applying',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        snapshot = self.Service._prepare_local_common(
            self.make_job(
                JOB_TYPE_UPDATE, preview._name, preview.id, PRODUCT_GID,
            )
        )
        request = self.Service._prepare_preconditions_update(snapshot, {})
        # Only `title` was confirmed, so only `title` is sent — a field that
        # drifted after the preview is never quietly added.
        self.assertEqual(set(request['variables']['product']), {'title'})

    # ------------------------------------------------------------------
    # Variant create never deletes the standalone variant
    # ------------------------------------------------------------------

    def test_variant_create_preserves_the_standalone_variant(self):
        binding = self.bind_template()
        extra = self.env['product.product'].create({
            'product_tmpl_id': self.template.id,
            'default_code': 'WIDGET-2',
        })
        preview = self.make_preview(
            export_path='update', binding=binding, state='applying',
            steps=[{'step': JOB_TYPE_VARIANTS_CREATE, 'state': 'pending',
                    'variant_ids': [extra.id]}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        snapshot = self.Service._prepare_local_common(
            self.make_job(
                JOB_TYPE_VARIANTS_CREATE, preview._name, preview.id,
                PRODUCT_GID,
            )
        )
        request = self.Service._prepare_preconditions_variants_create(
            snapshot, {},
        )
        # `DEFAULT` would delete the standalone "Default Title" variant when
        # it is the only one on the product. A remote deletion is not
        # available to this module, so the strategy that performs one is not
        # available either.
        self.assertEqual(
            request['variables']['strategy'], 'PRESERVE_STANDALONE_VARIANT',
        )
        self.assertNotIn('DEFAULT', str(request['variables']['strategy']))

    # ------------------------------------------------------------------
    # The create path builds a productSet with no merchant-owned lists
    # ------------------------------------------------------------------

    def test_create_input_claims_no_merchant_owned_lists(self):
        self.settings.sudo().write(
            {'product_export_binding_namespace_ready': True}
        )
        preview = self.make_preview(
            export_path='create', state='applying',
            steps=[{'step': JOB_TYPE_CREATE, 'state': 'pending',
                    'variant_ids': self.variant.ids}],
            diff={'variants_create': [
                {'odoo_variant_id': self.variant.id, 'values': {}},
            ], 'untouched': {}},
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        snapshot = self.Service._prepare_local_create(job)
        request = self.Service._prepare_preconditions_create(snapshot, {})
        product_input = request['variables']['input']
        self.assertIn('productSet', request['operation'])
        for merchant_owned in ('collections', 'metafields', 'files'):
            self.assertNotIn(merchant_owned, product_input)
        # The create shape MAY carry the connector's own options/variants —
        # a brand-new product has no merchant state to destroy.
        self.assertIn('variants', product_input)
        self.assertEqual(
            request['variables']['identifier']['customId']['value'],
            str(self.template.id),
        )
        # `namespace` is omitted so Shopify uses the app-reserved namespace.
        self.assertNotIn(
            'namespace', request['variables']['identifier']['customId'],
        )

    def test_create_refused_without_the_binding_metafield_definition(self):
        self.settings.sudo().write(
            {'product_export_binding_namespace_ready': False}
        )
        preview = self.make_preview(
            export_path='create', state='applying',
            steps=[{'step': JOB_TYPE_CREATE, 'state': 'pending',
                    'variant_ids': self.variant.ids}],
            diff={'variants_create': [], 'untouched': {}},
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        snapshot = self.Service._prepare_local_create(job)
        with self.assertRaises(ExportPreC2FailClosedError):
            self.Service._prepare_preconditions_create(snapshot, {})

    def test_create_refused_when_a_binding_appeared_after_the_preview(self):
        """Reconciliation before the mutation, not after a failure."""
        self.settings.sudo().write(
            {'product_export_binding_namespace_ready': True}
        )
        preview = self.make_preview(
            export_path='create', state='applying',
            steps=[{'step': JOB_TYPE_CREATE, 'state': 'pending',
                    'variant_ids': self.variant.ids}],
            diff={'variants_create': [], 'untouched': {}},
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        # A binding appears between preview and apply — a create would
        # duplicate the product.
        self.bind_template()
        job = self.make_job(JOB_TYPE_CREATE, preview._name, preview.id)
        snapshot = self.Service._prepare_local_create(job)
        with self.assertRaises(ExportPreC2FailClosedError) as catcher:
            self.Service._prepare_preconditions_create(snapshot, {})
        self.assertEqual(catcher.exception.error_class, 'duplicate_risk')
