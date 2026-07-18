import copy
import queue
import threading
import uuid
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, api
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .test_order_import_mapping import OrderImportCase


class TestOrderDuplicatePrevention(OrderImportCase):

    def test_repeat_import_refreshes_one_permanent_binding_and_order(self):
        payload = self._payload('gid://shopify/Order/Repeat')
        orders_before = self.env['sale.order'].search_count([])
        first = self.Importer._apply_import(self.store, payload)
        line_before = first.sale_order_id.order_line.read([
            'product_id', 'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ])
        payload['updatedAt'] = '2026-07-17T12:00:00Z'
        second = self.Importer._apply_import(self.store, payload)
        self.assertEqual(second, first)
        self.assertEqual(
            self.env['sale.order'].search_count([]), orders_before + 1,
        )
        self.assertEqual(self.Binding.search_count([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', payload['id']),
        ]), 1)
        self.assertEqual(first.sale_order_id.order_line.read([
            'product_id', 'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ]), line_before)

    def test_every_discovery_source_collides_on_same_entity_identity(self):
        Scan = self.env['shopify.connector.order.scan']
        node = {
            'id': 'gid://shopify/Order/Discovery',
            'updatedAt': '2026-07-17T12:00:00Z',
        }
        results = [
            Scan._enqueue_order(self.store, node, source)
            for source in (
                'scheduled_sync', 'manual_sync', 'reconciliation',
                'manual_sync',
            )
        ]
        self.assertEqual(results, [True, False, False, False])
        jobs = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', node['id']),
        ])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.job_source, 'scheduled_sync')

    def test_overlapping_windows_and_repeated_pages_do_not_duplicate(self):
        Scan = self.env['shopify.connector.order.scan']
        node = {
            'id': 'gid://shopify/Order/Overlap',
            'updatedAt': '2026-07-17T12:30:00Z',
        }
        self.assertTrue(Scan._enqueue_order(
            self.store, node, 'scheduled_sync',
        ))
        for _index in range(5):
            self.assertFalse(Scan._enqueue_order(
                self.store, dict(node), 'reconciliation',
            ))
        self.assertEqual(self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('shopify_target_gid', '=', node['id']),
        ]), 1)

    def test_database_binding_constraints_are_the_last_race_anchor(self):
        binding = self.Importer._apply_import(
            self.store, self._payload('gid://shopify/Order/BindingAnchor'),
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.Binding.sudo().create({
                    'store_id': self.store.id,
                    'shopify_gid': binding.shopify_gid,
                    'sale_order_id': self.env['sale.order'].create({
                        'partner_id': self.fallback_partner.id,
                        'company_id': self.env.company.id,
                        'pricelist_id': self.pricelist.id,
                        'payment_term_id': self.payment_term.id,
                    }).id,
                })
        self.assertEqual(self.Binding.search_count([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', binding.shopify_gid),
        ]), 1)


@tagged(
    'post_install', '-at_install', '-standard',
    'shopify_connector_order_discovery_concurrency',
)
class TestOrderDiscoveryConcurrencyGenuine(TransactionCase):
    """Independent PostgreSQL connections race the real scan-enqueue seam."""

    BOUND_SECONDS = 20

    def _open(self, dbname):
        cr = db_connect(dbname).cursor()
        cr.execute(
            "SELECT set_config('statement_timeout', %s, true), "
            "set_config('lock_timeout', %s, true)",
            ('10000', '8000'),
        )
        return cr

    def _setup_committed_store(self, dbname):
        cr = self._open(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Order Discovery Race',
                'shop_domain': 'order-race-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            settings = env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'sale_domain_enabled': True,
            })
            result = (store.id, settings.id)
            cr.commit()
            return result
        finally:
            cr.close()

    def _cleanup(self, dbname, store_id, settings_id):
        cr = self._open(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            jobs = env['shopify.connector.job'].search([
                ('store_id', '=', store_id),
            ])
            logs = env['shopify.connector.job.log'].search([
                ('job_id', 'in', jobs.ids),
            ])
            if logs:
                logs.unlink()
            if jobs:
                jobs.unlink()
            env['shopify.connector.store.settings'].browse(settings_id).unlink()
            env['shopify.connector.store'].browse(store_id).unlink()
            cr.commit()
        finally:
            cr.close()

    def _money(self, amount, currency):
        amount = str(amount)
        return {
            'shopMoney': {'amount': amount, 'currencyCode': currency},
            'presentmentMoney': {
                'amount': amount, 'currencyCode': currency,
            },
        }

    def _import_payload(self, currency, template_gid, variant_gid):
        zero = self._money('0.00', currency)
        total = self._money('100.00', currency)
        return {
            'id': 'gid://shopify/Order/GenuineBindingRace',
            'name': '#GENUINE-RACE-%s' % uuid.uuid4().hex,
            'legacyResourceId': '9000001',
            'createdAt': '2026-07-17T09:00:00Z',
            'processedAt': '2026-07-17T10:00:00Z',
            'updatedAt': '2026-07-17T11:00:00Z',
            'edited': False,
            'test': False,
            'confirmed': True,
            'closed': False,
            'closedAt': None,
            'cancelledAt': None,
            'cancelReason': None,
            'currencyCode': currency,
            'presentmentCurrencyCode': currency,
            'taxesIncluded': False,
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'email': None,
            'customer': None,
            'billingAddress': None,
            'shippingAddress': None,
            'paymentGatewayNames': [],
            'transactions': [],
            'totalPriceSet': total,
            'subtotalPriceSet': total,
            'totalTaxSet': zero,
            'totalDiscountsSet': zero,
            'totalShippingPriceSet': zero,
            'totalTipReceivedSet': zero,
            'currentTotalPriceSet': total,
            'currentTotalTaxSet': zero,
            'currentShippingPriceSet': zero,
            'currentTotalAdditionalFeesSet': None,
            'currentTotalDutiesSet': None,
            'totalCashRoundingAdjustment': {
                'paymentSet': zero,
                'refundSet': zero,
            },
            'taxLines': [],
            'line_items': [{
                'id': 'gid://shopify/LineItem/GenuineBindingRace',
                'name': 'Genuine binding race item',
                'title': 'Genuine binding race item',
                'variantTitle': None,
                'quantity': 1,
                'currentQuantity': 1,
                'sku': 'GENUINE-RACE',
                'isGiftCard': False,
                'requiresShipping': False,
                'taxable': False,
                'variant': {'id': variant_gid},
                'product': {'id': template_gid},
                'originalUnitPriceSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'originalTotalSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'discountedUnitPriceSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'discountedTotalSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'priceAfterAllDiscountsBeforeTaxesSet': total,
                'discountAllocations': [],
                'taxLines': [],
            }],
            'shipping_lines': [],
            'discount_applications': [],
        }

    def _setup_committed_import_fixture(self, dbname):
        cr = self._open(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            company = env.company
            currency = company.currency_id
            partner = env['res.partner'].create({
                'name': 'Genuine Order Binding Race Fallback',
            })
            pricelist = env['product.pricelist'].create({
                'name': 'Genuine Order Binding Race Pricelist',
                'currency_id': currency.id,
                'company_id': company.id,
            })
            payment_term = env.ref('account.account_payment_term_immediate')
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Order Binding Race',
                'shop_domain': 'order-binding-race-%s.myshopify.com'
                % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            settings = env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'sale_domain_enabled': True,
                'order_company_id': company.id,
                'order_pricelist_id': pricelist.id,
                'order_payment_term_id': payment_term.id,
                'customer_fallback_partner_id': partner.id,
                'order_confirmation_policy': 'quotations_only',
            })
            template = env['product.template'].create({
                'name': 'Genuine Order Binding Race Product',
                'type': 'service',
                'company_id': company.id,
                'list_price': 100.0,
            })
            product = template.product_variant_id
            template_gid = 'gid://shopify/Product/GenuineBindingRace'
            variant_gid = 'gid://shopify/ProductVariant/GenuineBindingRace'
            template_binding = env[
                'shopify.connector.product.template.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid': template_gid,
                'product_template_id': template.id,
            })
            variant_binding = env[
                'shopify.connector.product.variant.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid': variant_gid,
                'product_variant_id': product.id,
                'product_template_binding_id': template_binding.id,
            })
            fixture = {
                'store_id': store.id,
                'settings_id': settings.id,
                'partner_id': partner.id,
                'pricelist_id': pricelist.id,
                'template_id': template.id,
                'template_binding_id': template_binding.id,
                'variant_binding_id': variant_binding.id,
                'payload': self._import_payload(
                    currency.name, template_gid, variant_gid,
                ),
            }
            cr.commit()
            return fixture
        finally:
            cr.close()

    def _cleanup_import_fixture(self, dbname, fixture):
        cr = self._open(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            bindings = env['shopify.connector.order.binding'].search([
                ('store_id', '=', fixture['store_id']),
            ])
            orders = env['sale.order'].search([
                ('origin', '=', fixture['payload']['name']),
            ]) | bindings.mapped('sale_order_id')
            bindings.unlink()
            orders.unlink()
            env['shopify.connector.product.variant.binding'].browse(
                fixture['variant_binding_id']
            ).unlink()
            env['shopify.connector.product.template.binding'].browse(
                fixture['template_binding_id']
            ).unlink()
            env['shopify.connector.store.settings'].browse(
                fixture['settings_id']
            ).unlink()
            env['shopify.connector.store'].browse(
                fixture['store_id']
            ).unlink()
            env['product.template'].browse(fixture['template_id']).unlink()
            env['product.pricelist'].browse(fixture['pricelist_id']).unlink()
            env['res.partner'].browse(fixture['partner_id']).unlink()
            cr.commit()
        finally:
            cr.close()

    def test_two_connections_return_one_scan_job(self):
        dbname = self.env.cr.dbname
        store_id, settings_id = self._setup_committed_store(dbname)
        start_barrier = threading.Barrier(2)
        enqueue_barrier = threading.Barrier(2)
        results = queue.Queue()
        EnqueueType = type(self.env['shopify.connector.job.enqueue'])
        real_enqueue = EnqueueType.enqueue

        def synchronized_enqueue(service, *args, **kwargs):
            enqueue_barrier.wait(timeout=10)
            return real_enqueue(service, *args, **kwargs)

        def worker():
            cr = None
            try:
                cr = self._open(dbname)
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(store_id)
                start_barrier.wait(timeout=10)
                job = store._enqueue_order_scan('manual_sync')
                job_id = job.id if job else False
                cr.commit()
                results.put(('ok', job_id))
            except BaseException as exc:
                if cr:
                    cr.rollback()
                results.put(('error', type(exc).__name__))
            finally:
                if cr:
                    cr.close()

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
        try:
            # Odoo's post-install runner can hold ``Registry._lock`` around
            # the test phase.  A spawned worker building its own Environment
            # would otherwise block before reaching the production enqueue
            # seam.  Mirror the already-runtime-proven product concurrency
            # harness: replace only that process-local registry lock for the
            # bounded worker window; every database cursor, transaction,
            # unique constraint, and enqueue call remains genuine.
            with patch.object(type(self.registry), '_lock', threading.RLock()):
                with patch.object(
                    EnqueueType, 'enqueue', new=synchronized_enqueue,
                ):
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(timeout=self.BOUND_SECONDS)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            findings = [results.get_nowait() for _ in range(results.qsize())]
            self.assertEqual(len(findings), 2)
            self.assertTrue(all(kind == 'ok' for kind, _value in findings), findings)
            values = [value for _kind, value in findings]
            self.assertEqual(sum(bool(value) for value in values), 1, findings)
            self.assertIn(False, values)
            cr = self._open(dbname)
            try:
                cr.execute(
                    "SELECT count(*) FROM shopify_connector_job "
                    "WHERE store_id = %s AND job_type = 'order_import_scan'",
                    (store_id,),
                )
                self.assertEqual(cr.fetchone()[0], 1)
                cr.rollback()
            finally:
                cr.close()
        finally:
            for thread in threads:
                thread.join(timeout=self.BOUND_SECONDS)
            self._cleanup(dbname, store_id, settings_id)

    def test_two_connections_create_one_permanent_binding_and_sale_order(self):
        dbname = self.env.cr.dbname
        fixture = self._setup_committed_import_fixture(dbname)
        start_barrier = threading.Barrier(2)
        creation_barrier = threading.Barrier(2)
        results = queue.Queue()
        ImporterType = type(
            self.env['shopify.connector.order.importer']
        )
        real_precreation_gates = ImporterType._precreation_gates

        def synchronized_precreation_gates(service, payload, settings):
            result = real_precreation_gates(service, payload, settings)
            creation_barrier.wait(timeout=10)
            return result

        def worker():
            cr = None
            try:
                cr = self._open(dbname)
                env = api.Environment(cr, SUPERUSER_ID, {})
                store = env['shopify.connector.store'].browse(
                    fixture['store_id']
                )
                start_barrier.wait(timeout=10)
                binding = env[
                    'shopify.connector.order.importer'
                ]._apply_import(store, copy.deepcopy(fixture['payload']))
                result = (binding.id, binding.sale_order_id.id)
                cr.commit()
                results.put(('ok', result))
            except JobHandlerError as exc:
                if cr:
                    # The real dispatcher catches JobHandlerError and continues
                    # in the same transaction to record the job outcome.  Prove
                    # the importer's outer savepoint restored transaction
                    # usability and removed the losing quotation before commit.
                    cr.execute('SELECT 1')
                    cr.commit()
                results.put(('conflict', exc.error_class))
            except BaseException as exc:
                if cr:
                    cr.rollback()
                results.put(('error', type(exc).__name__))
            finally:
                if cr:
                    cr.close()

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
        try:
            with patch.object(type(self.registry), '_lock', threading.RLock()):
                with patch.object(
                    ImporterType, '_precreation_gates',
                    new=synchronized_precreation_gates,
                ):
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(timeout=self.BOUND_SECONDS)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            findings = [results.get_nowait() for _ in range(results.qsize())]
            self.assertEqual(len(findings), 2)
            self.assertEqual(
                sorted(kind for kind, _value in findings),
                ['conflict', 'ok'],
                findings,
            )
            self.assertEqual([
                value for kind, value in findings if kind == 'conflict'
            ], ['concurrency_race_conflict'])
            identities = {
                value for kind, value in findings if kind == 'ok'
            }
            self.assertEqual(len(identities), 1, findings)
            cr = self._open(dbname)
            try:
                cr.execute(
                    'SELECT count(*), count(DISTINCT sale_order_id) '
                    'FROM shopify_connector_order_binding WHERE store_id = %s',
                    (fixture['store_id'],),
                )
                self.assertEqual(cr.fetchone(), (1, 1))
                cr.execute(
                    'SELECT count(*) FROM sale_order WHERE origin = %s',
                    (fixture['payload']['name'],),
                )
                self.assertEqual(cr.fetchone()[0], 1)
                cr.rollback()
            finally:
                cr.close()
        finally:
            for thread in threads:
                thread.join(timeout=self.BOUND_SECONDS)
            self._cleanup_import_fixture(dbname, fixture)
