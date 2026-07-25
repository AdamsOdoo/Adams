import uuid

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestFulfillmentInboundEvidence(TransactionCase):
    """Per-fulfillment inbound evidence + per-line reconciled-quantity ledger.

    Covers (Modes §3/§5):
    - a per-fulfillment evidence row carries per-line evidence lines;
    - ``reconciled_quantity_ledger()`` returns
      ``{fo_line_item_gid: sum(reconciled_quantity)}`` and drops lines with no
      FulfillmentOrderLineItem GID;
    - the raw + normalized Layer-A state fields are stored;
    - the ``_check_review_reason`` constraint requires a named ``review_reason``
      when ``reconciled_state == 'review'``;
    - UNIQUE(store_id, shopify_fulfillment_gid) holds.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Evidence = cls.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ]
        cls.Line = cls.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ]
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })

    def _evidence(self, gid, **vals):
        payload = {
            'store_id': self.store.id,
            'shopify_fulfillment_gid': gid,
        }
        payload.update(vals)
        return self.Evidence.sudo().create(payload)

    def test_evidence_and_lines_created(self):
        evidence = self._evidence('gid://shopify/Fulfillment/EV-1')
        line = self.Line.sudo().create({
            'evidence_id': evidence.id,
            'fo_line_item_gid': 'gid://shopify/FulfillmentOrderLineItem/1',
            'line_item_gid': 'gid://shopify/LineItem/111',
            'quantity': 2,
            'reconciled_quantity': 2,
        })
        evidence.invalidate_recordset(['line_ids'])
        self.assertEqual(len(evidence.line_ids), 1)
        self.assertIn(line, evidence.line_ids)
        self.assertEqual(line.evidence_id, evidence)

    def test_reconciled_quantity_ledger_sums_by_fo_line(self):
        evidence = self._evidence('gid://shopify/Fulfillment/EV-2')
        fo_a = 'gid://shopify/FulfillmentOrderLineItem/A'
        fo_b = 'gid://shopify/FulfillmentOrderLineItem/B'
        self.Line.sudo().create([
            {'evidence_id': evidence.id, 'fo_line_item_gid': fo_a,
             'quantity': 1, 'reconciled_quantity': 1},
            {'evidence_id': evidence.id, 'fo_line_item_gid': fo_a,
             'quantity': 2, 'reconciled_quantity': 2},
            {'evidence_id': evidence.id, 'fo_line_item_gid': fo_b,
             'quantity': 3, 'reconciled_quantity': 3},
            # A line with no FulfillmentOrderLineItem GID is excluded.
            {'evidence_id': evidence.id, 'fo_line_item_gid': False,
             'quantity': 5, 'reconciled_quantity': 5},
        ])
        evidence.invalidate_recordset(['line_ids'])
        self.assertEqual(
            evidence.reconciled_quantity_ledger(),
            {fo_a: 3, fo_b: 3},
        )

    def test_raw_and_normalized_state_fields_stored(self):
        evidence = self._evidence(
            'gid://shopify/Fulfillment/EV-3',
            fulfillment_status_raw='SUCCESS',
            fulfillment_status_normalized='success',
            fulfillment_status_is_success=True,
            display_status_raw='FULFILLED',
            display_status_normalized='fulfilled',
            state_snapshot='{"FulfillmentStatus": "SUCCESS"}',
            schema_warning=False,
        )
        evidence.invalidate_recordset()
        self.assertEqual(evidence.fulfillment_status_raw, 'SUCCESS')
        self.assertEqual(evidence.fulfillment_status_normalized, 'success')
        self.assertTrue(evidence.fulfillment_status_is_success)
        self.assertEqual(evidence.display_status_raw, 'FULFILLED')
        self.assertEqual(evidence.display_status_normalized, 'fulfilled')
        self.assertEqual(
            evidence.state_snapshot, '{"FulfillmentStatus": "SUCCESS"}',
        )
        self.assertFalse(evidence.schema_warning)

    def test_review_state_requires_review_reason(self):
        # reconciled_state='review' with no named review_reason is refused by
        # the _check_review_reason constraint.
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self._evidence(
                    'gid://shopify/Fulfillment/EV-4',
                    reconciled_state='review',
                )
        # The same review state WITH a domain review_reason is accepted.
        evidence = self._evidence(
            'gid://shopify/Fulfillment/EV-5',
            reconciled_state='review',
            review_reason='quantity_overrun',
        )
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'quantity_overrun')

    @mute_logger('odoo.sql_db')
    def test_unique_store_fulfillment_gid(self):
        gid = 'gid://shopify/Fulfillment/EV-DUP'
        self._evidence(gid)
        # Same store + same Fulfillment GID collides on
        # UNIQUE(store_id, shopify_fulfillment_gid).
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._evidence(gid)
