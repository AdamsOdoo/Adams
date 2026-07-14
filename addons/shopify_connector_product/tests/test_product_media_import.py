import base64
import contextlib
import io
import os
import tempfile
from unittest.mock import patch

import requests

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from ..models import shopify_connector_product_importer as importer_mod


def _png(color):
    """A small, valid PNG of a solid colour (distinct bytes per colour)."""
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (2, 2), color).save(buffer, format='PNG')
    return buffer.getvalue()


class _FakeResponse:
    """A stand-in for a streamed `requests` response. `raise_exc`, when set,
    is raised AFTER the chunks are yielded, to simulate a mid-stream network
    failure while the importer iterates `iter_content()`."""

    def __init__(self, status_code=200, headers=None, chunks=None, raise_exc=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks if chunks is not None else [b'imagebytes']
        self._raise_exc = raise_exc
        self.closed = False

    def iter_content(self, size):
        for chunk in self._chunks:
            yield chunk
        if self._raise_exc is not None:
            raise self._raise_exc

    def close(self):
        self.closed = True


class TestProductMediaImport(TransactionCase):
    """D-010B-6 + reviews 4950202231 items 3-6 and 4950339305 items 2-3:
    primary + variant image import with checksum-verified ownership,
    SVG/raster validation, mid-stream network classification, and O(1)
    closed-path staging with deterministic unlink on every exit path."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Media Import Test Store',
            'shop_domain': 'media-import-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.ImporterType = type(cls.Importer)
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Settings = cls.env['shopify.connector.store.settings']

    def _settings(self, **vals):
        return self.Settings.create(dict(vals, store_id=self.store.id))

    def _variant(self, gid, sku=None, image_url=None, selected=None):
        selected = selected or []
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': None,
            'compare_at_price': None, 'selected_options': selected,
            'option_values': None, 'image_url': image_url,
        }

    def _payload(self, gid, variants, image_url=None, options=None):
        return {
            'gid': gid, 'title': 'Media Product', 'status': 'active',
            'updated_at': None, 'image_url': image_url,
            'options': options or [], 'variants': variants,
        }

    # ------------------------------------------------------------------
    # Staging helpers: the new contract stages each image to a CLOSED temp
    # file and passes only its path. These helpers create real temp paths so
    # the production `_stage_image`/`ExitStack` cleanup runs for real.
    # ------------------------------------------------------------------

    def _write_temp(self, data, prefix='shopify_test_media_'):
        fd, path = tempfile.mkstemp(prefix=prefix)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        return path

    def _fetch_returns(self, png):
        """Patch `_fetch_image` to stage `png` to a fresh closed temp path
        per call (mirroring the production return type: a path string)."""
        def fake_fetch(inner_self, url):
            return self._write_temp(png)
        return patch.object(self.ImporterType, '_fetch_image', fake_fetch)

    def _tracking_fetch(self, png):
        """Like `_fetch_returns`, but records every staged path so a test can
        assert deterministic unlink. Returns `(patch, paths)`."""
        paths = []

        def fake_fetch(inner_self, url):
            path = self._write_temp(png)
            paths.append(path)
            return path
        return patch.object(self.ImporterType, '_fetch_image', fake_fetch), paths

    # ------------------------------------------------------------------
    # Successful primary + variant image write.
    # ------------------------------------------------------------------

    def test_primary_product_image_written(self):
        png = _png((10, 20, 30))
        payload = self._payload(
            'gid://shopify/Product/5001',
            image_url='https://cdn.shopify.com/primary.png',
            variants=[self._variant('gid://shopify/ProductVariant/5001', sku='M1')],
        )
        with self._fetch_returns(png):
            result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertTrue(template.image_1920)
        self.assertTrue(result['template_binding'].shopify_image_checksum)

    def test_variant_image_written(self):
        png = _png((40, 50, 60))
        payload = self._payload(
            'gid://shopify/Product/5002',
            variants=[self._variant('gid://shopify/ProductVariant/5002', sku='M2',
                                    image_url='https://cdn.shopify.com/v.png')],
        )
        with self._fetch_returns(png):
            result = self.Importer._apply_import(self.store, payload)
        binding = result['variant_bindings']
        self.assertTrue(binding.product_variant_id.image_variant_1920)
        self.assertTrue(binding.shopify_image_checksum)

    def test_unchanged_connector_image_skipped_on_reimport(self):
        png = _png((70, 80, 90))
        payload = self._payload(
            'gid://shopify/Product/5003',
            image_url='https://cdn.shopify.com/same.png',
            variants=[self._variant('gid://shopify/ProductVariant/5003', sku='M3')],
        )
        calls = []

        def counting_fetch(inner_self, url):
            calls.append(url)
            return self._write_temp(png)

        with patch.object(self.ImporterType, '_fetch_image', counting_fetch):
            self.Importer._apply_import(self.store, payload)
            self.assertEqual(len(calls), 1)
            # Re-import, same URL, connector still owns -> skip (no download).
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(len(calls), 1)

    # ------------------------------------------------------------------
    # Ownership (review item 3): same URL must compare the CURRENT Odoo
    # checksum, not only the recorded checksum.
    # ------------------------------------------------------------------

    def _import_template_image(self, gid, url, png, **settings):
        if settings:
            self._settings(**settings)
        payload = self._payload(
            gid, image_url=url,
            variants=[self._variant('%s/v' % gid, sku='%s-sku' % gid[-4:])],
        )
        with self._fetch_returns(png):
            return self.Importer._apply_import(self.store, payload)

    def test_same_url_merchant_replaced_template_image_protected(self):
        gid = 'gid://shopify/Product/5010'
        url = 'https://cdn.shopify.com/t.png'
        result = self._import_template_image(
            gid, url, _png((1, 2, 3)),
            product_import_refresh_mode='shopify_fields',
        )
        template = result['template_binding'].product_template_id
        merchant = _png((222, 111, 55))
        template.write({'image_1920': base64.b64encode(merchant)})
        template.flush_recordset(['image_1920'])
        template.invalidate_recordset(['image_1920'])
        merchant_stored = template.image_1920

        calls = []
        payload = self._payload(
            gid, image_url=url,  # SAME url
            variants=[self._variant('%s/v' % gid, sku='%s-sku' % gid[-4:])],
        )
        with patch.object(self.ImporterType, '_fetch_image',
                          lambda inner, u: calls.append(u) or '/should/not/be/read'):
            result_2 = self.Importer._apply_import(self.store, payload)
        template.invalidate_recordset(['image_1920'])
        self.assertEqual(template.image_1920, merchant_stored)  # not overwritten
        self.assertFalse(calls)  # not even downloaded
        self.assertTrue(any(
            code == 'merchant_image_protected' for code, _ in result_2['notes']
        ))

    def test_same_url_merchant_replaced_variant_image_protected(self):
        gid = 'gid://shopify/Product/5011'
        url = 'https://cdn.shopify.com/vimg.png'
        self._settings(product_import_refresh_mode='shopify_fields')
        payload = self._payload(
            gid, variants=[self._variant('%s/v' % gid, sku='VI1', image_url=url)],
        )
        with self._fetch_returns(_png((3, 6, 9))):
            result = self.Importer._apply_import(self.store, payload)
        product = result['variant_bindings'].product_variant_id
        merchant = _png((90, 180, 200))
        product.write({'image_variant_1920': base64.b64encode(merchant)})
        product.flush_recordset(['image_variant_1920'])
        product.invalidate_recordset(['image_variant_1920'])
        merchant_stored = product.image_variant_1920

        with self._fetch_returns(_png((3, 6, 9))):
            result_2 = self.Importer._apply_import(self.store, payload)
        product.invalidate_recordset(['image_variant_1920'])
        self.assertEqual(product.image_variant_1920, merchant_stored)
        self.assertTrue(any(
            code == 'merchant_image_protected' for code, _ in result_2['notes']
        ))

    def test_same_url_cleared_image_snapshot_only_preserved(self):
        gid = 'gid://shopify/Product/5012'
        url = 'https://cdn.shopify.com/c.png'
        result = self._import_template_image(
            gid, url, _png((5, 10, 15)),
            product_import_refresh_mode='snapshot_only',
        )
        template = result['template_binding'].product_template_id
        template.write({'image_1920': False})  # merchant clears it
        template.flush_recordset(['image_1920'])
        template.invalidate_recordset(['image_1920'])

        payload = self._payload(
            gid, image_url=url,
            variants=[self._variant('%s/v' % gid, sku='%s-sku' % gid[-4:])],
        )
        with self._fetch_returns(_png((5, 10, 15))):
            result_2 = self.Importer._apply_import(self.store, payload)
        template.invalidate_recordset(['image_1920'])
        self.assertFalse(template.image_1920)  # clearing preserved
        self.assertTrue(any(
            code == 'merchant_image_protected' for code, _ in result_2['notes']
        ))

    def test_same_url_cleared_image_shopify_fields_restored(self):
        gid = 'gid://shopify/Product/5013'
        url = 'https://cdn.shopify.com/r.png'
        result = self._import_template_image(
            gid, url, _png((7, 14, 21)),
            product_import_refresh_mode='shopify_fields',
        )
        template = result['template_binding'].product_template_id
        template.write({'image_1920': False})  # merchant clears it
        template.flush_recordset(['image_1920'])
        template.invalidate_recordset(['image_1920'])

        payload = self._payload(
            gid, image_url=url,
            variants=[self._variant('%s/v' % gid, sku='%s-sku' % gid[-4:])],
        )
        with self._fetch_returns(_png((7, 14, 21))):
            self.Importer._apply_import(self.store, payload)
        template.invalidate_recordset(['image_1920'])
        self.assertTrue(template.image_1920)  # restored under shopify_fields

    def test_changed_url_merchant_modification_not_overwritten(self):
        gid = 'gid://shopify/Product/5014'
        result = self._import_template_image(
            gid, 'https://cdn.shopify.com/a.png', _png((1, 1, 1)),
            product_import_refresh_mode='shopify_fields',
        )
        template = result['template_binding'].product_template_id
        merchant = _png((200, 100, 50))
        template.write({'image_1920': base64.b64encode(merchant)})
        template.flush_recordset(['image_1920'])
        template.invalidate_recordset(['image_1920'])
        merchant_stored = template.image_1920

        payload = self._payload(
            gid, image_url='https://cdn.shopify.com/b.png',  # changed url
            variants=[self._variant('%s/v' % gid, sku='%s-sku' % gid[-4:])],
        )
        with self._fetch_returns(_png((1, 1, 1))):
            result_2 = self.Importer._apply_import(self.store, payload)
        template.invalidate_recordset(['image_1920'])
        self.assertEqual(template.image_1920, merchant_stored)
        self.assertTrue(any(
            code == 'merchant_image_protected' for code, _ in result_2['notes']
        ))

    def test_media_switch_off_writes_no_image(self):
        png = _png((11, 22, 33))
        self._settings(product_import_media_enabled=False)
        payload = self._payload(
            'gid://shopify/Product/5005',
            image_url='https://cdn.shopify.com/off.png',
            variants=[self._variant('gid://shopify/ProductVariant/5005', sku='M5')],
        )
        calls = []
        with patch.object(self.ImporterType, '_fetch_image',
                          lambda inner, url: calls.append(url) or self._write_temp(png)):
            result = self.Importer._apply_import(self.store, payload)
        self.assertFalse(calls)
        self.assertFalse(result['template_binding'].product_template_id.image_1920)
        self.assertFalse(result['template_binding'].shopify_image_checksum)

    # ------------------------------------------------------------------
    # Network safety + SVG/raster validation (review items 4-5) + mid-stream
    # network classification (review 4950339305 item 3).
    # ------------------------------------------------------------------

    def _track_mkstemp(self):
        """Patch the importer's `mkstemp` to record every path it creates, so
        a test can assert the partial file is unlinked. Returns `(patch,
        paths)`."""
        created = []
        real_mkstemp = tempfile.mkstemp

        def tracking_mkstemp(*args, **kwargs):
            fd, path = real_mkstemp(*args, **kwargs)
            created.append(path)
            return fd, path
        return patch.object(importer_mod.tempfile, 'mkstemp', tracking_mkstemp), created

    def test_non_https_url_rejected(self):
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._fetch_image('http://cdn.shopify.com/x.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_redirect_to_non_https_rejected(self):
        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=301,
                headers={'Location': 'http://insecure.example.com/x.png'},
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._fetch_image('https://cdn.shopify.com/x.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_wrong_content_type_rejected(self):
        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'text/html'},
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._fetch_image('https://cdn.shopify.com/x.html')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_svg_content_type_rejected(self):
        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/svg+xml'},
                chunks=[b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'],
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._fetch_image('https://cdn.shopify.com/x.svg')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_invalid_bytes_labelled_png_rejected(self):
        junk = b'this-is-not-an-image-body'

        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[junk],
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._fetch_image('https://cdn.shopify.com/fake.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')
        # The downloaded body must never appear in the error text.
        self.assertNotIn('this-is-not-an-image-body', str(ctx.exception))
        self.assertNotIn(
            'this-is-not-an-image-body', ctx.exception.technical_detail or '',
        )

    def test_oversized_response_rejected(self):
        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[b'x' * 50],
            )

        with patch.object(importer_mod, 'MAX_IMAGE_BYTES', 10):
            with patch.object(importer_mod.requests, 'get', fake_get):
                with self.assertRaises(JobHandlerError) as ctx:
                    self.Importer._fetch_image('https://cdn.shopify.com/big.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_network_failure_rejected(self):
        def fake_get(url, **kwargs):
            raise requests.exceptions.Timeout()

        with patch.object(importer_mod.requests, 'get', fake_get):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._fetch_image('https://cdn.shopify.com/x.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')

    def test_mid_stream_network_failure_classified(self):
        """The response's `iter_content()` yields one valid chunk, then raises
        a `ChunkedEncodingError` (review 4950339305 item 3). The importer
        must classify it as `shopify_temporary_server_network`, close the
        response, unlink the partial staged file, and never leak the body or
        the temporary path into the error."""
        valid = _png((3, 3, 3))
        holder = {}

        def fake_get(url, **kwargs):
            response = _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[valid],
                raise_exc=requests.exceptions.ChunkedEncodingError('boom'),
            )
            holder['response'] = response
            return response

        track_patch, created = self._track_mkstemp()
        with track_patch:
            with patch.object(importer_mod.requests, 'get', fake_get):
                with self.assertRaises(JobHandlerError) as ctx:
                    self.Importer._fetch_image('https://cdn.shopify.com/x.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')
        self.assertTrue(holder['response'].closed)  # response closed
        self.assertTrue(created)
        for path in created:
            self.assertFalse(os.path.exists(path))  # partial file removed
            self.assertNotIn(path, str(ctx.exception))
            self.assertNotIn(path, ctx.exception.technical_detail or '')
        self.assertNotIn('boom', str(ctx.exception))

    def test_valid_https_png_downloaded(self):
        png = _png((5, 5, 5))

        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[png],
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            path = self.Importer._fetch_image('https://cdn.shopify.com/ok.png')
        try:
            # `_fetch_image` returns a CLOSED path, not an open handle.
            self.assertIsInstance(path, str)
            self.assertTrue(os.path.exists(path))
            with open(path, 'rb') as handle:
                self.assertEqual(handle.read(), png)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_secret_in_media_request(self):
        captured = {}
        png = _png((9, 9, 9))

        def fake_get(url, **kwargs):
            captured['url'] = url
            captured['kwargs'] = kwargs
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[png],
            )

        with patch.object(importer_mod.requests, 'get', fake_get):
            path = self.Importer._fetch_image('https://cdn.shopify.com/ok.png')
        if os.path.exists(path):
            os.unlink(path)
        self.assertNotIn('headers', captured['kwargs'])
        self.assertNotIn('auth', captured['kwargs'])

    def test_source_level_media_carries_no_token(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_product_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        self.assertNotIn('X-Shopify-Access-Token', content)
        self.assertNotIn('_get_access_token', content)

    # ------------------------------------------------------------------
    # O(1) closed-path staging + deterministic cleanup (review 4950339305
    # item 2). Staged images are paths to CLOSED temp files -- not open
    # handles -- so open FDs stay O(1) regardless of variant count, exactly
    # one path is opened at a time for the write, and every path is unlinked
    # on success and on failure.
    # ------------------------------------------------------------------

    def test_source_level_media_is_staged_not_retained_as_bytes(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_product_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        # Secure temp creation, one-open-at-a-time read, deterministic unlink.
        self.assertIn('mkstemp', content)
        self.assertIn('_read_staged', content)
        self.assertIn('_unlink_quietly', content)
        self.assertNotIn('return bytes(data)', content)
        # The old many-open-handle design is gone (no per-image open handle
        # retained across the transaction).
        self.assertNotIn('SpooledTemporaryFile', content)

    def test_media_plan_retains_closed_paths_not_open_handles(self):
        """`_prepare_media` returns only paths (or None), never open file
        handles -- so open FDs stay O(1) -- and each staged path is a closed
        file on disk that the ExitStack unlinks when it exits."""
        png = _png((8, 8, 8))
        notes = []
        payload = self._payload(
            'gid://shopify/Product/5040',
            image_url='https://cdn.shopify.com/p.png',
            variants=[
                self._variant('gid://shopify/ProductVariant/5040a', sku='PL1',
                              image_url='https://cdn.shopify.com/a.png'),
                self._variant('gid://shopify/ProductVariant/5040b', sku='PL2',
                              image_url='https://cdn.shopify.com/b.png'),
            ],
        )
        with patch.object(self.ImporterType, '_fetch_image',
                          lambda inner, url: self._write_temp(png)):
            with contextlib.ExitStack() as stack:
                media = self.Importer._prepare_media(
                    self.store, payload,
                    self.Importer._store_settings(self.store), notes, stack,
                )
                paths = [value for value in media.values() if value is not None]
                self.assertEqual(len(paths), 3)  # 1 template + 2 variants
                for value in media.values():
                    self.assertTrue(value is None or isinstance(value, str))
                for staged_path in paths:
                    self.assertTrue(os.path.exists(staged_path))
            # After the stack exits, every staged path is unlinked.
            for staged_path in paths:
                self.assertFalse(os.path.exists(staged_path))

    def test_only_one_staged_image_open_at_a_time(self):
        """Across a multi-image import, `_read_staged` is only ever entered
        one call at a time -- never more than one staged file open for
        reading simultaneously."""
        png = _png((4, 4, 4))
        concurrency = {'now': 0, 'max': 0}

        def tracking_read(inner, staged_path):
            concurrency['now'] += 1
            concurrency['max'] = max(concurrency['max'], concurrency['now'])
            try:
                with open(staged_path, 'rb') as handle:
                    return handle.read()
            finally:
                concurrency['now'] -= 1

        gid = 'gid://shopify/Product/5041'
        payload = self._payload(
            gid, image_url='https://cdn.shopify.com/p.png',
            options=[{'name': 'SC010B Media Color', 'position': 1,
                      'values': ['Red', 'Blue']}],
            variants=[
                self._variant('%s/red' % gid, sku='OO-R',
                              image_url='https://cdn.shopify.com/a.png',
                              selected=[{'name': 'SC010B Media Color', 'value': 'Red'}]),
                self._variant('%s/blue' % gid, sku='OO-B',
                              image_url='https://cdn.shopify.com/b.png',
                              selected=[{'name': 'SC010B Media Color', 'value': 'Blue'}]),
            ],
        )
        with patch.object(self.ImporterType, '_read_staged', tracking_read):
            with patch.object(self.ImporterType, '_fetch_image',
                              lambda inner, url: self._write_temp(png)):
                self.Importer._apply_import(self.store, payload)
        self.assertEqual(concurrency['max'], 1)  # 1 template + 2 variant reads

    def test_staged_media_paths_removed_after_successful_import(self):
        png = _png((12, 34, 56))
        fetch_patch, paths = self._tracking_fetch(png)
        payload = self._payload(
            'gid://shopify/Product/5030',
            image_url='https://cdn.shopify.com/s.png',
            variants=[self._variant('gid://shopify/ProductVariant/5030', sku='ST1')],
        )
        with fetch_patch:
            self.Importer._apply_import(self.store, payload)
        self.assertTrue(paths)
        for staged_path in paths:
            self.assertFalse(os.path.exists(staged_path))

    def test_staged_media_paths_removed_after_database_failure(self):
        png = _png((21, 43, 65))
        fetch_patch, paths = self._tracking_fetch(png)
        gid = 'gid://shopify/Product/5031'
        # A structured product whose second variant references a phantom
        # option -> binding_conflict inside the savepoint, after every image
        # (primary + both variants) has been staged over the network.
        payload = self._payload(
            gid, image_url='https://cdn.shopify.com/db.png',
            options=[{'name': 'SC010B Media Color', 'position': 1, 'values': ['Red']}],
            variants=[
                self._variant('%s/r' % gid, sku='DBR',
                              image_url='https://cdn.shopify.com/r.png',
                              selected=[{'name': 'SC010B Media Color', 'value': 'Red'}]),
                self._variant('%s/x' % gid, sku='DBX',
                              image_url='https://cdn.shopify.com/x.png',
                              selected=[{'name': 'SC010B Media Phantom', 'value': 'Z'}]),
            ],
        )
        with fetch_patch:
            with self.assertRaises(JobHandlerError):
                self.Importer._apply_import(self.store, payload)
        self.assertTrue(paths)
        for staged_path in paths:
            self.assertFalse(os.path.exists(staged_path))

    def test_validation_failure_removes_temporary_path(self):
        """A raster-validation failure unlinks its own partial temp file and
        never surfaces the path in the operator-facing error."""
        junk = b'still-not-an-image'

        def fake_get(url, **kwargs):
            return _FakeResponse(
                status_code=200, headers={'Content-Type': 'image/png'},
                chunks=[junk],
            )

        track_patch, created = self._track_mkstemp()
        with track_patch:
            with patch.object(importer_mod.requests, 'get', fake_get):
                with self.assertRaises(JobHandlerError) as ctx:
                    self.Importer._fetch_image('https://cdn.shopify.com/bad.png')
        self.assertEqual(ctx.exception.error_class, 'shopify_temporary_server_network')
        self.assertTrue(created)
        for path in created:
            self.assertFalse(os.path.exists(path))
            self.assertNotIn(path, str(ctx.exception))
            self.assertNotIn(path, ctx.exception.technical_detail or '')
