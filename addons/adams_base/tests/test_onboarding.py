"""Disposable installation smoke; not acceptance of future business features."""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAdamsOnboarding(TransactionCase):
    def test_application_installed(self):
        module = self.env['ir.module.module'].search([('name', '=', 'adams_base')])
        self.assertEqual(len(module), 1)
        self.assertEqual(module.state, 'installed')

    def test_english_active_and_arabic_available(self):
        # This module does not load languages: Arabic is active only where it was installed
        # (a fresh Odoo.sh development database has English only).
        self.assertEqual(self.env['res.lang'].search_count([('code', '=', 'en_US'), ('active', '=', True)]), 1)
        self.assertEqual(self.env['res.lang'].with_context(active_test=False).search_count([('code', '=', 'ar_001')]), 1)

    def test_disposable_orm_roundtrip(self):
        record = self.env['res.partner'].create({'name': 'Adams isolated onboarding smoke'})
        self.env.flush_all()
        record.invalidate_recordset()
        self.assertEqual(record.name, 'Adams isolated onboarding smoke')
        self.assertTrue(record.exists())
