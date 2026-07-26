"""Browser-tour coverage for the U3 export operator surfaces.

These are `HttpCase` tests: they boot the real web client in a real browser and
drive it. That is the point — server-side "the view renders" assertions cannot
catch a template that throws in Owl, an asset bundle that fails to build, a
menu whose action id does not resolve, or a focus ring that exists only in a
stylesheet nobody loaded.

The navigation tour needs no Shopify state and runs in the ordinary suite. The
review and keyboard tours need one seeded preview carrying a refusal and a tag
removal, which is built here in Odoo rows only: no store credential is used, no
Shopify request is made, and nothing is enqueued.
"""

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from ..models.shopify_connector_product_export_service import JOB_TYPE_UPDATE


@tagged('post_install', '-at_install', 'shopify_connector_u3')
class TestU3ExportTours(HttpCase):

    def _connector_user(self, login, extra_group):
        return new_test_user(
            self.env,
            login=login,
            password=login,
            groups='base.group_user,%s' % extra_group,
        )

    def test_export_navigation_tour(self):
        """Every U3 export surface renders for a connector user."""
        self._connector_user(
            'u3_tour_user',
            'shopify_connector_core.group_shopify_connector_user',
        )
        self.start_tour(
            '/odoo', 'shopify_connector_u3_export_nav_tour',
            login='u3_tour_user',
        )

    # ------------------------------------------------------------------
    # Seeded review fixture
    # ------------------------------------------------------------------

    def _seed_preview(self):
        """One preview with a refusal AND a tag removal, in Odoo rows only."""
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'U3 Tour Store',
            'shop_domain': 'u3-tour.myshopify.com',
            'api_version': SHOPIFY_API_VERSION,
        })
        store.sudo().write({'state': 'connected'})
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'product_export_domain_enabled': True,
            'price_source_of_truth': 'odoo_authoritative',
        })
        template = self.env['product.template'].sudo().create({
            'name': 'U3 Tour Widget',
            'shopify_export_enabled': True,
            'shopify_export_tags': 'keep-me',
        })
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().create({
            'store_id': store.id,
            'product_template_id': template.id,
            'shopify_gid': 'gid://shopify/Product/9001',
        })
        now = fields.Datetime.now()
        return self.env[
            'shopify.connector.product.export.preview'
        ]._preview_surface('_create_preview').create({
            'store_id': store.id,
            'product_template_id': template.id,
            'product_template_binding_id': binding.id,
            'export_path': 'update',
            'state': 'previewed',
            'diff': {
                'scalars': [{'field': 'tags',
                             'from': ['keep-me', 'merchant-added'],
                             'to': ['keep-me']}],
                # The removal the surface must enumerate by name.
                'tag_replacement': {
                    'applies': True,
                    'removed': ['merchant-added'],
                    'resulting': ['keep-me'],
                    'note': 'Confirming this export replaces the product\'s '
                            'COMPLETE Shopify tag list with the Odoo list.',
                },
                'untouched': {'collections': True, 'metafields': False,
                              'existing_media': True,
                              'note': 'Never included in this export.'},
                'media': {'exported': False, 'reason': 'Media export is off.',
                          'appends': []},
            },
            'apply_plan': {'steps': [{'step': JOB_TYPE_UPDATE,
                                      'state': 'pending',
                                      'fields': ['tags']}], 'cursor': 0},
            # The refusal the surface must disclose above the confirm control.
            'blocked_differences': {'items': [{
                'kind': 'unowned_remote_variant',
                'detail': 'A Shopify variant is not bound to any Odoo variant. '
                          'It is left exactly as it is.',
            }]},
            'has_blocked_differences': True,
            'remote_product_gid': binding.shopify_gid,
            'remote_updated_at': '2026-07-26T00:00:00Z',
            'source_write_date': self.env[
                'shopify.connector.product.export.preview'
            ]._source_write_date(template),
            'previewed_at': now,
            'expires_at': fields.Datetime.add(now, hours=24),
        })

    def test_export_review_tour_discloses_before_it_offers(self):
        """The refusals and the tag removals are on screen with the confirm."""
        user = self._connector_user(
            'u3_tour_reviewer',
            'shopify_connector_core.group_shopify_connector_user',
        )
        preview = self._seed_preview()
        # Prove the fixture is READABLE by the tour user before driving a
        # browser at it. A tour that fails because the row was invisible looks
        # identical to a tour that fails because the button is missing, and
        # the two need completely different fixes.
        visible = self.env['shopify.connector.product.export.preview'].with_user(
            user
        ).search([('id', '=', preview.id)])
        self.assertEqual(
            visible, preview,
            'the seeded preview is not readable by the tour user, so the tour '
            'would fail on visibility rather than on the surface under test',
        )
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_u3_export_review_tour',
            login='u3_tour_reviewer',
        )

    def test_export_review_surface_is_keyboard_reachable(self):
        """Tab-reachable, and the focused control matches :focus-visible."""
        self._connector_user(
            'u3_tour_keyboard',
            'shopify_connector_core.group_shopify_connector_user',
        )
        self._seed_preview()
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_u3_export_keyboard_tour',
            login='u3_tour_keyboard',
        )
