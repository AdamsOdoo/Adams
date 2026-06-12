# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tier 2: webhook dedup scoping (AUD-024) and GDPR child-contact
redaction (AUD-025)."""
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from .common import mute_case_loggers


class Tier2Fixture:

    def _backend(self, name, url):
        return self.env['shopify.backend'].create({
            'name': name,
            'shop_url': url,
            'access_token': 'shpat_%s' % name.lower().replace(' ', ''),
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })


class TestWebhookDedupScope(Tier2Fixture, TransactionCase):
    """AUD-024: webhook dedup must be scoped per backend — the same
    webhook id arriving for two backends is two distinct deliveries."""

    @mute_logger('odoo.sql_db')
    def test_same_webhook_id_allowed_across_backends(self):
        b1 = self._backend('Dedup Store One', 'dedup-one.myshopify.com')
        b2 = self._backend('Dedup Store Two', 'dedup-two.myshopify.com')
        Log = self.env['shopify.webhook.log']
        Log.create({
            'backend_id': b1.id,
            'topic': 'orders/create',
            'webhook_id': 'wh_shared_id_1',
            'state': 'pending',
        })
        # Same webhook id, DIFFERENT backend: must be accepted — losing
        # it silently drops a legitimate inbound event for store two.
        log2 = Log.create({
            'backend_id': b2.id,
            'topic': 'orders/create',
            'webhook_id': 'wh_shared_id_1',
            'state': 'pending',
        })
        self.assertTrue(
            log2,
            "AUD-024: dedup must be per backend, not global",
        )


class TestGdprChildRedaction(Tier2Fixture, TransactionCase):
    """AUD-025: customers/redact must clear PII from delivery/invoice
    child contacts (created by order import) and from the parent's
    city/zip — not only the parent's street/email/phone."""

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.models.shopify_webhook_log')

    def test_redaction_covers_child_contacts_and_city(self):
        backend = self._backend('GDPR Store', 'gdpr-test.myshopify.com')
        partner = self.env['res.partner'].create({
            'name': 'Erase Me',
            'email': 'erase.me@example.com',
            'phone': '+4912345678',
            'street': 'Geheimstr. 1',
            'city': 'Berlin',
            'zip': '10115',
        })
        child = self.env['res.partner'].create({
            'parent_id': partner.id,
            'type': 'delivery',
            'name': 'Erase Me Delivery',
            'street': 'Lieferweg 2',
            'city': 'Hamburg',
            'zip': '20095',
            'phone': '+4987654321',
            'email': 'erase.me.delivery@example.com',
        })
        self.env['shopify.customer.binding'].create({
            'backend_id': backend.id,
            'odoo_id': partner.id,
            'shopify_id': 'gid://shopify/Customer/777001',
            'sync_status': 'synced',
        })
        log = self.env['shopify.webhook.log'].create({
            'backend_id': backend.id,
            'topic': 'customers/redact',
            'webhook_id': 'wh_gdpr_redact_1',
            'state': 'pending',
        })
        log._handle_gdpr_customer_redact({
            'customer': {'id': 777001, 'email': 'erase.me@example.com'},
        })
        self.assertFalse(partner.email, "Parent email must be cleared")
        self.assertFalse(partner.city,
                         "AUD-025: parent city must be cleared")
        self.assertFalse(partner.zip,
                         "AUD-025: parent zip must be cleared")
        for field in ('street', 'street2', 'email', 'phone', 'city',
                      'zip'):
            self.assertFalse(
                child[field],
                "AUD-025: child contact %s must be cleared (delivery/"
                "invoice addresses carry the customer's PII)" % field,
            )
        self.assertNotIn(
            'Erase Me', child.name,
            "AUD-025: child contact name must be anonymized",
        )
