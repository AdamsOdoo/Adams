"""Shared fixtures for the product-export suite.

No Shopify store, credential or request exists anywhere in this package. The
transport is replaced at the `_send` seam so the REAL admission gate, the real
Layer 2 attempt machinery and the real `_normalize_response` taxonomy all run
exactly as they do in production — only the socket is absent.
"""

import json
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
SHOP_DOMAIN = 'export-test.myshopify.com'
PRODUCT_GID = 'gid://shopify/Product/111'
VARIANT_GID = 'gid://shopify/ProductVariant/222'
FILE_GID = 'gid://shopify/MediaImage/333'


class FakeSendResponse:
    """A `requests.Response` stand-in for the `_send` transport seam."""

    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers if headers is not None else {
            API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
        }
        self.text = json.dumps(body) if body is not None else ''

    def json(self):
        return self._body


class ExportCase(TransactionCase):
    """Fixtures for a connected store with the export domain enabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env['shopify.connector.store']
        cls.Service = cls.env['shopify.connector.product.export.service']
        cls.Media = cls.env['shopify.connector.media.export.service']
        cls.Preview = cls.env['shopify.connector.product.export.preview']
        cls.TemplateBinding = cls.env[
            'shopify.connector.product.template.binding'
        ]
        cls.VariantBinding = cls.env[
            'shopify.connector.product.variant.binding'
        ]
        cls.MediaBinding = cls.env['shopify.connector.product.media.binding']

        cls.store = cls.Store.sudo().create({
            'name': 'Export Test Store',
            'shop_domain': SHOP_DOMAIN,
            'api_version': SHOPIFY_API_VERSION,
        })
        cls.store.sudo().write({'state': 'connected'})
        # Batch 1 correction (§9.1): `create()` on the credential model is
        # refused outside the credential service's own write surface, so this
        # fixture mints through that surface. Mechanical, test-only, and
        # deliberately NOT `action_set_token`, which takes the store lifecycle
        # lock and would demote this `connected` store to `reconnect_needed` --
        # the opposite of what the fixture is building.
        cls.env['shopify.connector.store.credential'].sudo()._credential_surface(
            '_mutate_token',
        ).create({
            'store_id': cls.store.id,
            'access_token': DUMMY_TOKEN,
            'credential_epoch': 1,
        })
        cls.settings = cls.env['shopify.connector.store.settings'].sudo().create({
            'store_id': cls.store.id,
            'product_export_domain_enabled': True,
            'price_source_of_truth': 'odoo_authoritative',
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Exportable Widget',
            'description_sale': '<p>A widget.</p>',
            'list_price': 12.5,
            'shopify_export_enabled': True,
            'shopify_export_status': 'draft',
            'shopify_export_vendor': 'Adams',
            'shopify_export_product_type': 'Widgets',
            'shopify_export_tags': 'alpha, beta',
        })
        cls.variant = cls.template.product_variant_ids[:1]
        cls.variant.write({'default_code': 'WIDGET-1', 'barcode': '0001'})

    def setUp(self):
        super().setUp()
        # `_admit` opens its gate/lease insert on an independent
        # `registry.cursor()` side transaction. Registry test mode makes that a
        # TestCursor sharing the single test connection, so the uncommitted
        # fixtures and the committed lease are visible cross-cursor -- the
        # sanctioned CORE-R2 mechanism the existing admission tests use.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def bind_template(self, gid=PRODUCT_GID, variant_gid=VARIANT_GID):
        binding = self.TemplateBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_id': self.template.id,
            'shopify_gid': gid,
        })
        if variant_gid:
            self.VariantBinding.sudo().create({
                'store_id': self.store.id,
                'product_variant_id': self.variant.id,
                'product_template_binding_id': binding.id,
                'shopify_gid': variant_gid,
            })
        return binding

    def add_template_variant(self, default_code, barcode=False):
        """Create a genuine attribute-backed sibling variant.

        Odoo 19 enforces one empty ``combination_indices`` row per template,
        so directly creating a second ``product.product`` row is not a valid
        fixture. Adding an always-generated attribute line exercises the same
        business shape as the UI and preserves the original standalone row as
        one of the two combinations.
        """
        attribute = self.env['product.attribute'].create({
            'name': 'Export test option',
            'create_variant': 'always',
        })
        values = self.env['product.attribute.value'].create([
            {'name': 'Original', 'attribute_id': attribute.id},
            {'name': 'Added', 'attribute_id': attribute.id},
        ])
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.template.id,
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, values.ids)],
        })
        self.template.invalidate_recordset(['product_variant_ids'])
        extra = self.template.product_variant_ids.filtered(
            lambda variant: variant.id != self.variant.id
        )[:1]
        extra.ensure_one()
        extra.write({
            'default_code': default_code or False,
            'barcode': barcode or False,
        })
        return extra

    def make_job(self, job_type, res_model, res_id, gid=False):
        return self.env['shopify.connector.job.enqueue'].enqueue(
            self.store,
            'manual_sync' if job_type != 'product_export_preview'
            else 'export_preview_dry_run',
            job_type,
            payload_hash='test-%s-%s' % (job_type, res_id),
            res_model=res_model,
            res_id=res_id,
            shopify_target_gid=gid,
        )

    def send_patch(self, responder):
        """Patch the ONE transport method, nothing above it."""
        Client = type(self.env['shopify.connector.api.client'])
        return patch.object(Client, '_send', responder)

    def make_preview(
        self, export_path='update', steps=None, state='previewed',
        binding=None, diff=None, blocked=None,
        remote_updated_at='2026-07-26T00:00:00Z', expires_at=None,
        source_write_date=None,
    ):
        """Create a preview through the sanctioned surface.

        Tests build previews directly rather than by running the preview
        handler when the behaviour under test is downstream of it; the preview
        handler has its own tests.
        """
        now = fields.Datetime.now()
        values = {
            'store_id': self.store.id,
            'product_template_id': self.template.id,
            'product_template_binding_id': binding.id if binding else False,
            'export_path': export_path,
            'state': state,
            'diff': diff or {'scalars': [], 'untouched': {}},
            'apply_plan': {'steps': steps or [], 'cursor': 0},
            'blocked_differences': {'items': blocked or []},
            'has_blocked_differences': bool(blocked),
            'remote_product_gid': binding.shopify_gid if binding else False,
            'remote_updated_at': remote_updated_at,
            # Overridable so a test can express "the product was edited
            # after this preview was taken". It cannot be expressed by
            # actually writing to the template mid-test: Odoo stamps
            # `write_date` from `cr.now()`, which is the TRANSACTION's
            # timestamp and is cached on the cursor for its whole life
            # (`odoo/sql_db.py::BaseCursor.now`). Every write inside one
            # `TransactionCase` therefore carries the identical
            # `write_date`, and `_is_expired`'s strictly-greater comparison
            # can never flip. In production each job is its own
            # transaction, so the clock does advance -- the mechanism is
            # sound; only this fixture has to reach it another way.
            'source_write_date': (
                source_write_date if source_write_date is not None
                else self.Preview._source_write_date(self.template)
            ),
            'previewed_at': now,
            # `expires_at` is settable only here: `_create_preview` is the
            # CREATE surface and expiry is deliberately not in
            # `WRITE_SURFACES`, so nothing may move a preview's deadline
            # after the fact -- not even a test. A TD-013 case that needs an
            # already-stale confirmation therefore has to be BORN stale.
            'expires_at': (
                expires_at if expires_at is not None
                else fields.Datetime.add(now, hours=24)
            ),
        }
        return self.Preview._preview_surface('_create_preview').create(values)
