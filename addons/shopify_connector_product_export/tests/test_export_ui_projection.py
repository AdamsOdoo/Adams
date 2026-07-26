"""The U3 export projection is read-only, role-gated, and tells the truth.

The Owl surface trusts this service completely — it renders what it is given
and computes nothing. So the guarantees have to hold here: no write, no
Shopify request, no credential, no bypass of the confirmation rules, and a
`can_confirm` that agrees with what the server would actually do.
"""

import ast
import pathlib

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user, tagged

from ..models.shopify_connector_product_export_service import JOB_TYPE_UPDATE
from .common import ExportCase


@tagged('post_install', '-at_install')
class TestExportUiProjection(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template(variant_gid=None)
        self.Ui = self.env['shopify.connector.product.export.ui']
        self.reviewer = new_test_user(
            self.env, login='u3-projection-reviewer',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_reviewer',
        )

    def _preview(self, **overrides):
        diff = {
            'scalars': [{'field': 'tags',
                         'from': ['keep-me', 'merchant-added'],
                         'to': ['keep-me']}],
            'tag_replacement': {
                'applies': True,
                'removed': ['merchant-added'],
                'resulting': ['keep-me'],
                'note': 'Replaces the complete tag list.',
            },
            'untouched': {'collections': True, 'metafields': False,
                          'existing_media': True, 'note': 'Untouched.'},
            'media': {'exported': False, 'reason': 'Off.', 'appends': []},
        }
        diff.update(overrides.pop('diff', {}))
        return self.make_preview(
            binding=self.binding, diff=diff,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['tags']}],
            blocked=[{'kind': 'unowned_remote_variant',
                      'detail': 'Left exactly as it is.'}],
            **overrides,
        )

    # ------------------------------------------------------------------
    # It says what will be removed
    # ------------------------------------------------------------------

    def test_tag_removals_survive_the_projection_by_name(self):
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            self._preview().id
        )
        self.assertTrue(data['tag_replacement']['applies'])
        self.assertTrue(data['tag_replacement']['removes'])
        self.assertEqual(data['tag_replacement']['removed'], ['merchant-added'])

    def test_an_additive_tag_change_is_not_reported_as_a_removal(self):
        """`removes` is keyed on an actual removal, not on any tag edit.

        A surface that raises a removal alert every time a tag changes is a
        surface whose removal alert nobody reads by the third time.
        """
        preview = self._preview(diff={'tag_replacement': {
            'applies': True, 'removed': [], 'resulting': ['a', 'b'],
            'note': 'n/a',
        }})
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertTrue(data['tag_replacement']['applies'])
        self.assertFalse(data['tag_replacement']['removes'])

    def test_refusals_are_projected_with_a_plain_language_label(self):
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            self._preview().id
        )
        self.assertEqual(len(data['refusals']), 1)
        self.assertEqual(
            data['refusals'][0]['label'],
            'Shopify variant this connector does not own',
        )

    def test_an_unknown_refusal_kind_still_renders_visibly(self):
        """An unrecognised refusal must never become a blank row."""
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['tags']}],
            blocked=[{'kind': 'a_kind_from_the_future', 'detail': 'detail'}],
        )
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertEqual(
            data['refusals'][0]['label'], 'a_kind_from_the_future',
        )

    def test_an_empty_value_reads_as_empty_not_as_false(self):
        preview = self.make_preview(
            binding=self.binding,
            diff={'scalars': [{'field': 'vendor', 'from': False, 'to': ''}]},
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['vendor']}],
        )
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        row = data['sections'][0]['rows'][0]
        self.assertEqual(row['from'], '(empty)')
        self.assertEqual(row['to'], '(empty)')

    # ------------------------------------------------------------------
    # can_confirm agrees with the server
    # ------------------------------------------------------------------

    def test_can_confirm_is_false_for_a_role_the_server_would_refuse(self):
        operator = new_test_user(
            self.env, login='u3-projection-operator',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_operator',
        )
        preview = self._preview()
        data = self.Ui.with_user(operator).get_export_preview_data(preview.id)
        self.assertFalse(data['can_confirm'])
        # And the server genuinely refuses that same user.
        with self.assertRaises(AccessError):
            preview.with_user(operator).action_confirm_export_preview()

    def test_can_confirm_is_false_for_an_expired_preview(self):
        preview = self._preview()
        self.env.cr.execute(
            'UPDATE shopify_connector_product_export_preview '
            'SET expires_at = %s WHERE id = %s',
            (fields.Datetime.subtract(fields.Datetime.now(), hours=1),
             preview.id),
        )
        preview.invalidate_recordset()
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertTrue(data['is_expired'])
        self.assertFalse(data['can_confirm'])

    def test_can_confirm_is_false_when_the_plan_is_empty(self):
        preview = self.make_preview(binding=self.binding, steps=[])
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertFalse(data['can_confirm'])

    def test_a_non_connector_user_is_refused_outright(self):
        outsider = new_test_user(
            self.env, login='u3-projection-outsider', groups='base.group_user',
        )
        preview = self._preview()
        with self.assertRaises(AccessError):
            self.Ui.with_user(outsider).get_export_preview_data(preview.id)

    # ------------------------------------------------------------------
    # Progress arithmetic lives here, so the bar cannot disagree with the count
    # ------------------------------------------------------------------

    def test_plan_progress_percent_matches_the_step_counts(self):
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'done'},
                   {'step': 'product_export_media_stage', 'state': 'pending'}],
        )
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertEqual(data['plan']['total'], 2)
        self.assertEqual(data['plan']['done'], 1)
        self.assertEqual(data['plan']['percent'], 50)

    def test_an_empty_plan_does_not_divide_by_zero(self):
        preview = self.make_preview(binding=self.binding, steps=[])
        data = self.Ui.with_user(self.reviewer).get_export_preview_data(
            preview.id
        )
        self.assertEqual(data['plan']['percent'], 0)

    # ------------------------------------------------------------------
    # It is a projection, and the AST proves it
    # ------------------------------------------------------------------

    def test_the_projection_service_performs_no_write_of_any_kind(self):
        """Read-only by construction, asserted mechanically.

        The same standing guard the repository applies to `_check_*` readiness
        checks: a projection that can write is one refactor away from becoming
        a second, ungoverned mutation path.
        """
        path = (
            pathlib.Path(__file__).resolve().parent.parent
            / 'models' / 'shopify_connector_product_export_ui.py'
        )
        tree = ast.parse(path.read_text())
        forbidden = {
            'write', 'create', 'unlink', 'sudo', 'commit', 'enqueue',
            'flush', 'execute', '_send', 'action_confirm_export_preview',
        }
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden:
                    offenders.append(node.func.attr)
        self.assertEqual(
            offenders, [],
            'the export UI projection called a mutating or transport method',
        )
