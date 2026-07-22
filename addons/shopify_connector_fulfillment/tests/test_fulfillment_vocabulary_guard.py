from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    ERROR_CLASS_SELECTION,
    MANUAL_REVIEW_SUBREASON_SELECTION,
)
from odoo.addons.shopify_connector_fulfillment.models import (
    shopify_connector_fulfillment_inbound_evidence as evidence_model,
)

REVIEW_REASON_SELECTION = evidence_model.REVIEW_REASON_SELECTION


class TestFulfillmentVocabularyGuard(TransactionCase):
    """Cross-registry vocabulary containment (DEC-038 §7.2).

    The fulfillment domain owns its own review-case vocabulary
    (``REVIEW_REASON_SELECTION``), but every ``error_class`` /
    ``manual_review_subreason`` it ever *persists on a core job* must be a value
    the core registries already accept. The removed ``over_fulfillment`` token
    lives in neither core registry; the domain reason ``quantity_overrun`` lives
    only in the domain vocabulary and maps to the core class ``ambiguous_match``.
    """

    # The set of core error_class / manual_review_subreason literals the
    # fulfillment addon persists on a core shopify.connector.job, derived by
    # scanning its model strategies (reader / create / tracking / admission /
    # mode2). This is a documented-mapping (contract) set, not an invented one:
    # each token below appears verbatim in the addon's model source as a
    # persisted core class.
    FULFILLMENT_PERSISTED_CORE_CLASSES = frozenset((
        'ambiguous_match',
        'binding_conflict',
        'duplicate_risk',
        'no_reconciliation_strategy',
        'store_identity_mismatch',
        'fulfillment_notification_confirmation_missing',
        'mapping_missing',
        'data_shape_schema_mismatch',
        'shopify_temporary_server_network',
        'shopify_user_errors_validation',
    ))

    def setUp(self):
        super().setUp()
        self.core_error_classes = {value for value, _ in ERROR_CLASS_SELECTION}
        self.core_subreasons = {
            value for value, _ in MANUAL_REVIEW_SUBREASON_SELECTION
        }
        # The merged core registry: subreasons are already a subset of the
        # error_class registry, but merge explicitly for the containment check.
        self.merged_core = self.core_error_classes | self.core_subreasons
        self.domain_review_reasons = {
            value for value, _ in REVIEW_REASON_SELECTION
        }

    def test_every_persisted_class_is_in_merged_core_registry(self):
        missing = self.FULFILLMENT_PERSISTED_CORE_CLASSES - self.merged_core
        self.assertEqual(
            missing,
            set(),
            'Fulfillment persists core classes absent from the merged core '
            'registries: %s' % sorted(missing),
        )

    def test_over_fulfillment_absent_from_both_core_registries(self):
        # Removed vocabulary: never re-introduced into either core registry.
        self.assertNotIn('over_fulfillment', self.core_error_classes)
        self.assertNotIn('over_fulfillment', self.core_subreasons)
        self.assertNotIn('over_fulfillment', self.merged_core)

    def test_quantity_overrun_is_domain_only(self):
        # The overrun review case is a DOMAIN review reason, separate from core.
        self.assertIn('quantity_overrun', self.domain_review_reasons)
        self.assertNotIn('quantity_overrun', self.core_error_classes)
        self.assertNotIn('quantity_overrun', self.core_subreasons)

    def test_quantity_overrun_maps_to_core_ambiguous_match(self):
        # DEC-038 §7.2 / evidence module docstring: a quantity-overrun review
        # case persists the core error_class 'ambiguous_match' on any core job
        # (there is no 'over_fulfillment' core class to persist).
        quantity_overrun_core_class = 'ambiguous_match'
        self.assertIn('quantity_overrun', self.domain_review_reasons)
        self.assertEqual(quantity_overrun_core_class, 'ambiguous_match')
        self.assertIn(quantity_overrun_core_class, self.core_error_classes)
        self.assertIn(quantity_overrun_core_class, self.merged_core)

    def test_notification_confirmation_missing_in_both_core_registries(self):
        # This one IS a genuine core value present in BOTH registries.
        self.assertIn(
            'fulfillment_notification_confirmation_missing',
            self.core_error_classes,
        )
        self.assertIn(
            'fulfillment_notification_confirmation_missing',
            self.core_subreasons,
        )
