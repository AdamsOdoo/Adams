import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools import float_compare

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

# CORE-R2 Slice 2B: the product importer now issues every Shopify Admin page
# call through the core `execute_business` admission-lease context manager
# (`_send` transport seam), not the legacy value-returning `execute()`. The
# transport tests below drive the REAL admission gate; `DUMMY_TOKEN` is a
# non-secret test constant (never a live token) and no live Shopify request
# runs (the absent-product fixtures normalize a null product node).
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeSendResponse:
    """Minimal `requests.Response` stand-in for the `_send` transport seam;
    `_normalize_response` reads `.status_code`, `.json()`, `.headers` and
    `.text` only, and the JSON body is the accepted Task 010B fixture dict."""

    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ''

    def json(self):
        return self._body


class TestProductRefreshAndStale(TransactionCase):
    """D-010B-7 (safe refresh) and D-010B-8 (archived/deleted remote)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Refresh Stale Test Store',
            'shop_domain': 'refresh-stale-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.Job = cls.env['shopify.connector.job']
        # Seed a credential while `setup_incomplete` (no generation bump), so the
        # store stays at generation 0, matching a directly-created job.
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # Enter registry test mode so `execute_business._admit`'s side cursor
        # sees this test's fixture (the sanctioned core-test mechanism); no
        # production behaviour changes and it is auto-left on teardown.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _import_job(self, shopify_target_gid):
        """Connect the store (the business-job create gate requires it) and
        return a product-import job at generation 0 (matching the store), then
        flush so the admission side cursor observes the store/job."""
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

    def _settings(self, **vals):
        return self.Settings.create(dict(vals, store_id=self.store.id))

    def _variant(self, gid, price, selected=None, sku=None):
        selected = selected or []
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': price,
            'compare_at_price': None, 'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': None,
        }

    def _payload(self, gid, variants, options=None, status='active',
                 updated_at=None, image_url=None):
        return {
            'gid': gid, 'title': 'Refreshable Product', 'status': status,
            'updated_at': updated_at, 'image_url': image_url,
            'options': options or [], 'variants': variants,
        }

    # ------------------------------------------------------------------
    # Refresh modes.
    # ------------------------------------------------------------------

    def test_snapshot_only_does_not_overwrite_merchant_price(self):
        self._settings(price_source_of_truth='shopify_authoritative',
                       product_import_refresh_mode='snapshot_only')
        gid = 'gid://shopify/Product/6001'
        result = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 20.0, sku='R1')]),
        )
        template = result['template_binding'].product_template_id
        # First import wrote 20; merchant then edits Odoo to 99.
        template.list_price = 99.0
        self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 30.0, sku='R1')]),
        )
        template.invalidate_recordset(['list_price'])
        self.assertEqual(
            float_compare(template.list_price, 99.0, precision_digits=2), 0,
        )

    def test_shopify_fields_refresh_rewrites_price(self):
        self._settings(price_source_of_truth='shopify_authoritative',
                       product_import_refresh_mode='shopify_fields')
        gid = 'gid://shopify/Product/6002'
        result = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 20.0, sku='R2')]),
        )
        template = result['template_binding'].product_template_id
        self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 35.0, sku='R2')]),
        )
        template.invalidate_recordset(['list_price'])
        self.assertEqual(
            float_compare(template.list_price, 35.0, precision_digits=2), 0,
        )

    def test_snapshot_only_preserves_merchant_name_but_refreshes_snapshot(self):
        self._settings(product_import_refresh_mode='snapshot_only')
        gid = 'gid://shopify/Product/6003'
        result = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 20.0, sku='R3')]),
        )
        template = result['template_binding'].product_template_id
        template.name = 'Merchant Renamed Product'
        payload_2 = self._payload(gid, [self._variant('%s/v' % gid, 20.0, sku='R3')])
        payload_2['title'] = 'Shopify New Title'
        result_2 = self.Importer._apply_import(self.store, payload_2)
        template.invalidate_recordset(['name'])
        # Merchant's Odoo name is preserved; the snapshot reflects Shopify.
        self.assertEqual(template.name, 'Merchant Renamed Product')
        self.assertEqual(
            result_2['template_binding'].shopify_title, 'Shopify New Title',
        )

    def test_structural_additions_apply_in_snapshot_only_mode(self):
        self._settings(product_import_refresh_mode='snapshot_only')
        gid = 'gid://shopify/Product/6004'
        first = self.Importer._apply_import(self.store, self._payload(
            gid,
            options=[{'name': 'SC010B Refresh Color', 'position': 1, 'values': ['Red']}],
            variants=[self._variant('%s/r' % gid, 10.0,
                                    [{'name': 'SC010B Refresh Color', 'value': 'Red'}],
                                    sku='SR')],
        ))
        template = first['template_binding'].product_template_id
        self.assertEqual(len(template.product_variant_ids), 1)
        # A new remote variant appears on refresh -- structural addition
        # applies even in snapshot_only mode.
        second = self.Importer._apply_import(self.store, self._payload(
            gid,
            options=[{'name': 'SC010B Refresh Color', 'position': 1,
                      'values': ['Red', 'Blue']}],
            variants=[
                self._variant('%s/r' % gid, 10.0,
                              [{'name': 'SC010B Refresh Color', 'value': 'Red'}], sku='SR'),
                self._variant('%s/b' % gid, 10.0,
                              [{'name': 'SC010B Refresh Color', 'value': 'Blue'}], sku='SB'),
            ],
        ))
        self.assertEqual(len(second['variant_bindings']), 2)
        self.assertEqual(len(template.product_variant_ids), 2)

    # ------------------------------------------------------------------
    # D-010B-7 real updatedAt short-circuit (review 4950202231 item 2):
    # importer-level, before any media/DB write. The stamp is stored only
    # after a complete success; enqueue-level payload_hash=updatedAt is an
    # Area-6 obligation, not implemented here.
    # ------------------------------------------------------------------

    def test_same_updated_at_short_circuits_before_any_work(self):
        gid = 'gid://shopify/Product/6100'
        first = self.Importer._apply_import(self.store, self._payload(
            gid, [self._variant('%s/v' % gid, 10.0, sku='UA1')],
            updated_at='2026-07-11T10:00:00Z',
        ))
        binding = first['template_binding']
        self.assertEqual(binding.shopify_updated_at, '2026-07-11T10:00:00Z')
        stamped_at = binding.shopify_last_imported_at

        Importer = type(self.Importer)
        with patch.object(Importer, '_prepare_media') as media, \
                patch.object(Importer, '_apply_prices') as prices, \
                patch.object(Importer, '_apply_image') as image:
            result = self.Importer._apply_import(self.store, self._payload(
                gid, [self._variant('%s/v' % gid, 99.0, sku='UA1')],
                updated_at='2026-07-11T10:00:00Z',
            ))
        self.assertTrue(result.get('unchanged'))
        # No media download, no price/image write on the short-circuit.
        media.assert_not_called()
        prices.assert_not_called()
        image.assert_not_called()
        # Snapshots are not rewritten.
        binding.invalidate_recordset(['shopify_last_imported_at'])
        self.assertEqual(binding.shopify_last_imported_at, stamped_at)
        # The returned bindings are the existing ones.
        self.assertEqual(result['template_binding'], binding)
        self.assertEqual(result['variant_bindings'], first['variant_bindings'])

    def test_changed_updated_at_reprocesses_normally(self):
        gid = 'gid://shopify/Product/6101'
        self.Importer._apply_import(self.store, self._payload(
            gid, [self._variant('%s/v' % gid, 10.0, sku='UA2')],
            updated_at='2026-07-11T10:00:00Z',
        ))
        Importer = type(self.Importer)
        with patch.object(
            Importer, '_prepare_media', return_value={},
        ) as media:
            result = self.Importer._apply_import(self.store, self._payload(
                gid, [self._variant('%s/v' % gid, 10.0, sku='UA2')],
                updated_at='2026-07-11T11:30:00Z',  # changed
            ))
        self.assertFalse(result.get('unchanged'))
        media.assert_called()  # normal path ran
        self.assertEqual(
            result['template_binding'].shopify_updated_at, '2026-07-11T11:30:00Z',
        )

    def test_updated_at_stored_only_after_success(self):
        gid = 'gid://shopify/Product/6102'
        # A blind create (no identifier) fails; nothing is stored.
        with self.assertRaises(JobHandlerError):
            self.Importer._apply_import(self.store, self._payload(
                gid, [self._variant('%s/v' % gid, 10.0, sku=None)],
                updated_at='2026-07-11T10:00:00Z',
            ))
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))

    def test_failed_changed_import_does_not_advance_updated_at(self):
        gid = 'gid://shopify/Product/6103'
        first = self.Importer._apply_import(self.store, self._payload(
            gid,
            options=[{'name': 'SC010B Refresh Color', 'position': 1, 'values': ['Red']}],
            variants=[self._variant('%s/r' % gid, 10.0,
                                    [{'name': 'SC010B Refresh Color', 'value': 'Red'}],
                                    sku='CR3')],
            updated_at='t1',
        ))
        binding = first['template_binding']
        self.assertEqual(binding.shopify_updated_at, 't1')
        # A changed import that fails (a phantom-option variant) must roll
        # back and leave shopify_updated_at at t1.
        with self.assertRaises(JobHandlerError):
            self.Importer._apply_import(self.store, self._payload(
                gid,
                options=[{'name': 'SC010B Refresh Color', 'position': 1,
                          'values': ['Red']}],
                variants=[
                    self._variant('%s/r' % gid, 10.0,
                                  [{'name': 'SC010B Refresh Color', 'value': 'Red'}],
                                  sku='CR3'),
                    self._variant('%s/x' % gid, 10.0,
                                  [{'name': 'SC010B Refresh Phantom', 'value': 'Z'}],
                                  sku='CX3'),
                ],
                updated_at='t2',
            ))
        binding.invalidate_recordset(['shopify_updated_at'])
        self.assertEqual(binding.shopify_updated_at, 't1')

    def test_empty_updated_at_never_short_circuits(self):
        gid = 'gid://shopify/Product/6104'
        payload = self._payload(
            gid, [self._variant('%s/v' % gid, 10.0, sku='UA5')], updated_at=None,
        )
        first = self.Importer._apply_import(self.store, payload)
        self.assertFalse(first['template_binding'].shopify_updated_at)
        Importer = type(self.Importer)
        with patch.object(
            Importer, '_prepare_media', return_value={},
        ) as media:
            result = self.Importer._apply_import(self.store, payload)
        self.assertFalse(result.get('unchanged'))
        media.assert_called()

    # ------------------------------------------------------------------
    # D-010B-8: archived / deleted remote products.
    # ------------------------------------------------------------------

    def test_archived_product_marks_binding_stale_without_touching_odoo(self):
        gid = 'gid://shopify/Product/6006'
        result = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='AR1')]),
        )
        template = result['template_binding'].product_template_id
        binding = result['template_binding']

        archived = self.Importer._apply_import(
            self.store,
            self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='AR1')],
                          status='archived'),
        )
        binding.invalidate_recordset(['status'])
        self.assertEqual(binding.status, 'stale')
        self.assertTrue(any(
            code == 'remote_archived' for code, _ in archived['notes']
        ))
        # Odoo product is never deleted or archived.
        self.assertTrue(template.exists())
        self.assertTrue(template.active)

    def test_deleted_bound_product_marks_binding_stale(self):
        gid = 'gid://shopify/Product/6007'
        first = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='DEL1')]),
        )
        template = first['template_binding'].product_template_id

        def fake_execute(self, store, query, variables=None):
            return {'data': {'product': None}}

        with self._patch_send(fake_execute):
            result = self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertTrue(result.get('stale'))
        self.assertEqual(result['template_binding'].status, 'stale')
        self.assertTrue(template.exists())
        self.assertTrue(template.active)

    # ------------------------------------------------------------------
    # D-010B-8 archived path routed BEFORE media (review 4950339305 item 4):
    # a bound archived product marks stale with no media download and no
    # master write; a first-seen unbound archived product creates nothing and
    # raises the existing mapping_missing class.
    # ------------------------------------------------------------------

    def test_bound_archived_product_does_not_call_prepare_media(self):
        gid = 'gid://shopify/Product/6200'
        first = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ARP1')]),
        )
        binding = first['template_binding']
        Importer = type(self.Importer)
        with patch.object(Importer, '_prepare_media') as media:
            result = self.Importer._apply_import(
                self.store,
                self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ARP1')],
                              status='archived',
                              image_url='https://cdn.shopify.com/a.png'),
            )
        media.assert_not_called()  # archived routed before any media staging
        binding.invalidate_recordset(['status'])
        self.assertEqual(binding.status, 'stale')
        self.assertTrue(result.get('stale'))

    def test_archived_broken_image_url_does_not_block_stale_marking(self):
        gid = 'gid://shopify/Product/6201'
        first = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ARP2')]),
        )
        binding = first['template_binding']
        Importer = type(self.Importer)

        def boom(inner, url):
            raise JobHandlerError(
                'shopify_temporary_server_network', 'unreachable image')

        with patch.object(Importer, '_fetch_image', boom):
            result = self.Importer._apply_import(
                self.store,
                self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ARP2')],
                              status='archived',
                              image_url='https://cdn.shopify.com/broken.png'),
            )
        # The broken image URL never blocks the stale marking, because the
        # archived path runs before any media download.
        binding.invalidate_recordset(['status'])
        self.assertEqual(binding.status, 'stale')
        self.assertTrue(result.get('stale'))

    def test_archived_leaves_bound_master_values_unchanged(self):
        self._settings(price_source_of_truth='shopify_authoritative',
                       product_import_refresh_mode='shopify_fields')
        gid = 'gid://shopify/Product/6202'
        first = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 25.0, sku='ARP3')]),
        )
        template = first['template_binding'].product_template_id
        template.invalidate_recordset(['list_price', 'name'])
        price_before = template.list_price
        name_before = template.name
        # An archived payload carries a different price -- it must NOT be
        # written (no master write on the archived path).
        archived = self.Importer._apply_import(
            self.store,
            self._payload(gid, [self._variant('%s/v' % gid, 999.0, sku='ARP3')],
                          status='archived'),
        )
        template.invalidate_recordset(['list_price', 'name'])
        self.assertEqual(
            float_compare(template.list_price, price_before, precision_digits=2), 0,
        )
        self.assertEqual(template.name, name_before)
        self.assertTrue(archived.get('stale'))

    def test_archived_outranks_unchanged_short_circuit(self):
        """Lifecycle status beats the unchanged-updatedAt optimization
        (review 4951145191 item 3): an active binding whose archived payload
        presents the exact same stored updatedAt must still go stale, with no
        media download and no master write -- never returned as `unchanged`."""
        self._settings(price_source_of_truth='shopify_authoritative',
                       product_import_refresh_mode='shopify_fields')
        gid = 'gid://shopify/Product/6210'
        first = self.Importer._apply_import(self.store, self._payload(
            gid, [self._variant('%s/v' % gid, 20.0, sku='AO1')],
            updated_at='2026-07-12T09:00:00Z'))
        binding = first['template_binding']
        template = binding.product_template_id
        self.assertEqual(binding.status, 'active')
        self.assertEqual(binding.shopify_updated_at, '2026-07-12T09:00:00Z')
        template.invalidate_recordset(['list_price'])
        price_before = template.list_price

        Importer = type(self.Importer)
        with patch.object(Importer, '_prepare_media') as media:
            # Archived payload with the EXACT same updatedAt and a decoy price.
            result = self.Importer._apply_import(self.store, self._payload(
                gid, [self._variant('%s/v' % gid, 999.0, sku='AO1')],
                status='archived', updated_at='2026-07-12T09:00:00Z'))
        media.assert_not_called()  # archived outranks media staging
        self.assertFalse(result.get('unchanged'))  # not short-circuited
        self.assertTrue(result.get('stale'))
        binding.invalidate_recordset(['status'])
        self.assertEqual(binding.status, 'stale')
        self.assertTrue(result['variant_bindings'])
        self.assertTrue(all(
            vb.status == 'stale' for vb in result['variant_bindings']))
        # Master data untouched -- the decoy 999 price was never written.
        template.invalidate_recordset(['list_price'])
        self.assertEqual(
            float_compare(template.list_price, price_before, precision_digits=2), 0)

    def test_first_seen_archived_product_raises_mapping_missing(self):
        gid = 'gid://shopify/Product/6203-never-seen'
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(
                self.store,
                self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ARN1')],
                              status='archived'),
            )
        self.assertEqual(ctx.exception.error_class, 'mapping_missing')

    def test_first_seen_archived_creates_no_master_or_binding(self):
        gid = 'gid://shopify/Product/6204-never-seen'
        templates_before = self.env['product.template'].search_count([])
        products_before = self.env['product.product'].search_count([])
        attrs_before = self.env['product.attribute'].search_count([])
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(
                self.store,
                self._payload(
                    gid,
                    options=[{'name': 'Color', 'position': 1, 'values': ['Red']}],
                    variants=[self._variant('%s/r' % gid, 10.0,
                                            [{'name': 'Color', 'value': 'Red'}],
                                            sku='ARN2')],
                    status='archived'),
            )
        self.assertEqual(ctx.exception.error_class, 'mapping_missing')
        # No Odoo master data and no binding created for an archived first-see.
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before)
        self.assertEqual(
            self.env['product.product'].search_count([]), products_before)
        self.assertEqual(
            self.env['product.attribute'].search_count([]), attrs_before)
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid)]))
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', '%s/r' % gid)]))

    def test_deleted_unbound_product_is_data_error(self):
        def fake_execute(self, store, query, variables=None):
            return {'data': {'product': None}}

        gid = 'gid://shopify/Product/6008-never-seen'
        with self._patch_send(fake_execute):
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer.import_product_sync(
                    self.store, gid, job=self._import_job(gid),
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_deletion_does_not_delete_any_odoo_product(self):
        gid = 'gid://shopify/Product/6009'
        first = self.Importer._apply_import(
            self.store, self._payload(gid, [self._variant('%s/v' % gid, 10.0, sku='ND1')]),
        )
        template_id = first['template_binding'].product_template_id.id
        products_before = self.env['product.product'].search_count([])

        def fake_execute(self, store, query, variables=None):
            return {'data': {'product': None}}

        with self._patch_send(fake_execute):
            self.Importer.import_product_sync(
                self.store, gid, job=self._import_job(gid),
            )
        self.assertTrue(self.env['product.template'].browse(template_id).exists())
        self.assertEqual(
            self.env['product.product'].search_count([]), products_before,
        )

    # ------------------------------------------------------------------
    # Source-level declared-write guard.
    # ------------------------------------------------------------------

    def test_source_level_list_price_only_written_in_price_path(self):
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_product_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            lines = source_file.readlines()
        price_writes = [
            (i, line) for i, line in enumerate(lines)
            if 'list_price' in line and '=' in line and 'def ' not in line
        ]
        # Every list_price assignment lives inside _apply_prices.
        apply_prices_start = next(
            i for i, line in enumerate(lines) if 'def _apply_prices(' in line
        )
        should_write_start = next(
            i for i, line in enumerate(lines)
            if 'def _should_write_shopify_owned_fields(' in line
        )
        for index, _line in price_writes:
            self.assertTrue(
                apply_prices_start < index < should_write_start,
                'list_price written outside _apply_prices',
            )
