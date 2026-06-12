# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests for import_batch error visibility (ITEM A — swallow visibility).

Test 1: When import_batch encounters a non-Integrity error in production
mode, a warning activity is scheduled on the backend record so the
merchant sees it in the Odoo UI.

Test 2: When import_batch encounters a non-Integrity error under test
mode (config['test_enable'] is True), the exception propagates instead
of being silently counted.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools import config
from .common import mute_case_loggers


class _FakeImporter:
    """Minimal BaseImporter subclass whose _import_one always raises."""

    entity_name = 'order'
    binding_model = 'shopify.order.binding'

    def __init__(self, env, backend):
        from odoo.addons.shopify_connector_pro.sync.base_importer import (
            BaseImporter,
        )
        # Bind BaseImporter methods onto this instance so we get
        # import_batch, _find_binding, etc. without needing a real
        # API client (which __init__ would create).
        self.env = env
        self.backend = backend
        self.import_batch = BaseImporter.import_batch.__get__(self)
        self._find_binding = BaseImporter._find_binding.__get__(self)
        self._create_log = BaseImporter._create_log.__get__(self)

    def _compute_shopify_checksum(self, node):
        return 'fake-checksum'

    def _import_one(self, node, existing_binding=None):
        raise ValueError("Invalid field 'tax_id' in 'sale.order.line'")


class TestImportBatchActivity(TransactionCase):
    """Test 1: production-mode error surfaces a warning activity."""

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.sync.base_importer')
        self.backend = self.env['shopify.backend'].create({
            'name': 'Activity Test Backend',
            'shop_url': 'activity-test.myshopify.com',
            'access_token': 'shpat_activity',
            'company_id': self.env.company.id,
        })

    def test_import_batch_schedules_activity_on_error(self):
        """When import_batch ends with errors > 0, a warning activity
        must be scheduled on the backend record with the error details.

        RED before the fix: no activity is scheduled — the error is
        only logged to the server log.

        GREEN after: backend has a warning activity with the entity
        type and error count in the summary.
        """
        importer = _FakeImporter(self.env, self.backend)
        node = {'id': 'gid://shopify/Order/FAIL001'}

        # Force production mode so the exception is caught, not re-raised.
        # config.options is a ChainMap with _runtime_options first, so we
        # must patch _runtime_options directly.
        orig = config._runtime_options.get('test_enable')
        config._runtime_options['test_enable'] = False
        try:
            success, errors, skipped = importer.import_batch([node])
        finally:
            if orig is None:
                config._runtime_options.pop('test_enable', None)
            else:
                config._runtime_options['test_enable'] = orig

        self.assertEqual(errors, 1, "One error expected")
        self.assertEqual(success, 0)

        # Assert a warning activity was scheduled on the backend
        # mail.mail_activity_data_warning has name='Exception' in Odoo 19
        warning_type = self.env.ref('mail.mail_activity_data_warning')
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'shopify.backend'),
            ('res_id', '=', self.backend.id),
            ('activity_type_id', '=', warning_type.id),
        ])
        self.assertTrue(
            activities,
            "A warning activity must be scheduled on the backend "
            "when import_batch encounters errors",
        )
        activity = activities[0]
        self.assertIn('order', activity.summary.lower(),
                       "Activity summary must name the entity type")
        self.assertIn('1', activity.summary,
                       "Activity summary must include the error count")
        self.assertIn("tax_id", activity.note,
                       "Activity note must include the error detail")


class TestImportBatchTestModeReraise(TransactionCase):
    """Test 2: test-mode re-raise for non-Integrity errors."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Reraise Test Backend',
            'shop_url': 'reraise-test.myshopify.com',
            'access_token': 'shpat_reraise',
            'company_id': self.env.company.id,
        })

    def test_import_batch_reraises_under_test_mode(self):
        """Under test mode, non-Integrity exceptions from _import_one
        must propagate instead of being silently counted.

        This ensures field-name bugs (like the tax_id→tax_ids fix)
        fail CI immediately rather than being swallowed.
        """
        importer = _FakeImporter(self.env, self.backend)
        node = {'id': 'gid://shopify/Order/FAIL002'}

        # config['test_enable'] is True during test runs — verify it
        # causes re-raise
        self.assertTrue(
            config['test_enable'],
            "test_enable must be True during --test-enable runs",
        )
        with self.assertRaises(ValueError) as ctx:
            importer.import_batch([node])

        self.assertIn("tax_id", str(ctx.exception))
