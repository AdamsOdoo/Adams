"""TD-003: the vocabulary reconciliation cannot drift from the code.

`docs/06-prompts/connector-vocabulary-reconciliation.md` is the authoritative
code→label mapping. A reference document is only worth having if it is
provably current, and the failure mode TD-003 records is exactly a document
that quietly stopped matching the implementation: the product docs named
`external_service`, `over_fulfillment`, `under_review`, `auto_matched` and
`rejected`, none of which is a selection value anywhere.

So this reads the document's tables and the shipped selections and requires
them to agree, in both directions:

* every value the document lists must exist in the code — otherwise the
  document invents a value, which is the original defect;
* every value the code defines must appear in the document — otherwise a
  real code value has no operator-facing label and renders as a raw string,
  which is the specific gap TD-003 flags for `external_fulfillment_observed`.

No Shopify contact, no fixtures: this reads source and Markdown.
"""

import pathlib
import re

from odoo.tests.common import TransactionCase, tagged

DOC = (
    pathlib.Path(__file__).resolve().parents[3]
    / 'docs' / '06-prompts' / 'connector-vocabulary-reconciliation.md'
)


def _documented_values(section_heading, doc_text):
    """The left-hand column of the table under one `##` heading."""
    body = doc_text.split('\n## ')
    section = next(
        (part for part in body if part.startswith(section_heading)), None,
    )
    if section is None:
        return None
    values = set()
    for line in section.splitlines():
        match = re.match(r'^\|\s*`([a-z_0-9]+)`\s*\|', line)
        if match:
            values.add(match.group(1))
    return values


@tagged('post_install', '-at_install')
class TestVocabularyReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = DOC.read_text() if DOC.exists() else None

    def setUp(self):
        super().setUp()
        self.assertTrue(
            self.doc,
            'the vocabulary reconciliation document is missing at %s; '
            'TD-003 depends on it existing' % DOC,
        )

    def _selection_values(self, model_name, field_name):
        self.assertIn(
            model_name, self.env,
            '%s is not installed, so this guard would be vacuous' % model_name,
        )
        field = self.env[model_name]._fields[field_name]
        return {value for value, _label in field.selection}

    def _assert_agrees(self, heading, model_name, field_name):
        documented = _documented_values(heading, self.doc)
        self.assertIsNotNone(
            documented,
            'the reconciliation document has no "%s" section any more; if it '
            'was renamed, update this guard in the same commit' % heading,
        )
        actual = self._selection_values(model_name, field_name)
        self.assertTrue(actual, 'no selection values were read at all')
        invented = documented - actual
        self.assertFalse(invented, (
            'the reconciliation document lists values that do not exist in '
            '%s.%s: %s. That is the exact defect TD-003 records -- a document '
            'naming a selection nobody can use.' % (
                model_name, field_name, sorted(invented))
        ))
        unmapped = actual - documented
        self.assertFalse(unmapped, (
            'these %s.%s values have no entry in the reconciliation '
            'document, so they have no operator-facing label and would '
            'render as raw strings: %s' % (
                model_name, field_name, sorted(unmapped))
        ))

    # ------------------------------------------------------------------
    # The three fulfillment selections TD-003 names
    # ------------------------------------------------------------------

    def test_origin_classes_agree_with_the_code(self):
        self._assert_agrees(
            '2. Origin classes',
            'shopify.connector.fulfillment.inbound.evidence',
            'origin_class',
        )

    def test_reconciliation_states_agree_with_the_code(self):
        self._assert_agrees(
            '3. Reconciliation states',
            'shopify.connector.fulfillment.inbound.evidence',
            'reconciled_state',
        )

    def test_every_review_reason_is_documented(self):
        """The 21st value is the one TD-003 flags by name."""
        self._assert_agrees(
            '4. Review reasons',
            'shopify.connector.fulfillment.inbound.evidence',
            'review_reason',
        )
        self.assertIn(
            'external_fulfillment_observed',
            _documented_values('4. Review reasons', self.doc),
            'the Wave 4 Theme H addition must be in the copy deck; a deck '
            'built against the historical 20 leaves it unmapped',
        )

    # ------------------------------------------------------------------
    # The superseded tokens must stay out of the mapping tables
    # ------------------------------------------------------------------

    def test_no_superseded_token_is_listed_as_a_real_value(self):
        """`under_review` and friends may be DISCUSSED, never mapped.

        The document names them so a reader who arrives holding one can
        find out what to use instead. What it must never do is put one in
        a value column, which is what a copy-and-paste would then produce.
        """
        superseded = (
            'external_service', 'carrier_event_only', 'over_fulfillment',
            'under_review', 'auto_matched', 'rejected',
        )
        offenders = []
        for line in self.doc.splitlines():
            match = re.match(r'^\|\s*`([a-z_0-9]+)`\s*\|', line)
            if match and match.group(1) in superseded:
                offenders.append(line.strip()[:90])
        self.assertFalse(offenders, (
            'these superseded tokens appear in a VALUE column of the '
            'reconciliation document, where a reader will copy them: %s'
            % offenders
        ))

    def test_the_two_residual_stale_locations_are_corrected(self):
        """TD-003's named residual locations, asserted rather than assumed."""
        root = pathlib.Path(__file__).resolve().parents[3] / 'docs'
        for relative in (
            '05-qa/fulfillment-mode-uat-matrix.md',
            '02-product/premium-ux-master-specification.md',
        ):
            path = root / relative
            with self.subTest(document=relative):
                self.assertTrue(path.exists(), '%s is missing' % relative)
                text = path.read_text()
                for stale in re.findall(r'`under_review`', text):
                    del stale
                # `under_review` may still be MENTIONED, but only alongside
                # the correction that says it was never a value.
                for line in text.splitlines():
                    if '`under_review`' not in line:
                        continue
                    self.assertIn(
                        'connector-vocabulary-reconciliation.md', line,
                        'this line still carries `under_review` without '
                        'pointing at the correction: %s' % line.strip()[:120],
                    )

    # ------------------------------------------------------------------
    # Roles: the concept string is not the group name
    # ------------------------------------------------------------------

    def test_the_documented_group_names_are_the_real_ones(self):
        """A screen must never print a role concept as if it were a label."""
        expected = {
            'group_shopify_connector_user': 'User',
            'group_shopify_connector_admin': 'Administrator',
            'group_shopify_connector_auditor': 'Auditor',
            'group_shopify_connector_operator': 'Operator',
            'group_shopify_connector_reviewer': 'Reviewer',
        }
        for xmlid, name in expected.items():
            with self.subTest(group=xmlid):
                group = self.env.ref('shopify_connector_core.%s' % xmlid)
                self.assertEqual(
                    group.name, name,
                    'the reconciliation document records this group as %r; '
                    'a group is never renamed to match a document, so if '
                    'this changed deliberately, update the document in the '
                    'same commit' % name,
                )
                self.assertIn('`%s`' % name, self.doc)

    def test_the_hidden_roles_are_still_hidden(self):
        """Three of the five carry no privilege and are not on the form.

        The document tells a copy author that "assign the Reviewer role"
        describes a control that is not on screen. That claim has to stay
        true.
        """
        for xmlid in (
            'group_shopify_connector_auditor',
            'group_shopify_connector_operator',
            'group_shopify_connector_reviewer',
        ):
            with self.subTest(group=xmlid):
                group = self.env.ref('shopify_connector_core.%s' % xmlid)
                self.assertFalse(
                    group.privilege_id,
                    '%s now carries a privilege, so it IS on the user form '
                    'and the reconciliation document is wrong about it'
                    % xmlid,
                )
        for xmlid in ('group_shopify_connector_user',
                      'group_shopify_connector_admin'):
            with self.subTest(group=xmlid):
                self.assertTrue(
                    self.env.ref(
                        'shopify_connector_core.%s' % xmlid
                    ).privilege_id,
                    '%s must remain a selectable level of the Shopify '
                    'Connector privilege' % xmlid,
                )
