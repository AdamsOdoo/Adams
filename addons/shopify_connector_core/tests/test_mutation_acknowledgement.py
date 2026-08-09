from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMutationAcknowledgementLadder(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Attempt = self.env['shopify.connector.mutation.attempt']

    def _status(self, outcome, disposition=False, source=False):
        return self.Attempt._merchant_write_status_from_evidence(
            outcome, disposition, source,
        )

    def test_direct_attempt_evidence_uses_honest_ladder(self):
        self.assertEqual(self._status('pending'), 'sending')
        self.assertEqual(self._status('succeeded'), 'accepted')
        self.assertEqual(self._status('failed_clean'), 'rejected')
        self.assertEqual(self._status('uncertain'), 'needs_attention')

    def test_only_positive_reconciliation_is_verified(self):
        self.assertEqual(
            self._status('uncertain', 'applied', 'reconciliation_read'),
            'verified',
        )
        self.assertEqual(
            self._status('uncertain', 'not_applied', 'reconciliation_read'),
            'rejected',
        )

    def test_manual_resolution_never_claims_machine_verification(self):
        self.assertEqual(
            self._status('uncertain', 'applied', 'manual_admin'),
            'needs_attention',
        )
        self.assertEqual(
            self._status('uncertain', 'not_applied', 'manual_admin'),
            'needs_attention',
        )
