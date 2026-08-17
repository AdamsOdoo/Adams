"""Standing structural guards over this module and its UI layer.

These tests do not exercise behaviour; they hold the shape of the module so a
later edit cannot quietly reintroduce something the ruling forbids. The repo's
existing guards (the frozen sudo inventory, the phase contract, the UI
source guards) exist for the same reason and have each caught a real defect.
"""

import ast
import pathlib

from odoo.tests.common import tagged

from odoo.tests.common import TransactionCase

MODULE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _python_sources(include_tests=False):
    for path in sorted(MODULE_ROOT.rglob('*.py')):
        if not include_tests and 'tests' in path.parts:
            continue
        yield path


@tagged('post_install', '-at_install')
class TestExportSourceGuards(TransactionCase):

    def test_business_reads_use_only_the_job_bound_read_seam(self):
        legacy = []
        read_calls = []
        for path in _python_sources():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                ):
                    continue
                if (
                    node.func.attr == 'execute'
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == 'client'
                ):
                    legacy.append((path.name, node.lineno))
                if node.func.attr == 'execute_business_read':
                    read_calls.append((path.name, node))
        self.assertFalse(legacy, legacy)
        self.assertEqual(len(read_calls), 9)
        for path, call in read_calls:
            purpose = next(
                (kw.value for kw in call.keywords if kw.arg == 'purpose'),
                None,
            )
            self.assertIsInstance(purpose, ast.Constant, path)
            self.assertEqual(purpose.value, 'product_export', path)

    # ------------------------------------------------------------------
    # The UI layer delegates and does nothing else
    # ------------------------------------------------------------------

    def test_wizards_never_write_create_sudo_commit_or_enqueue(self):
        """A display-and-delegate wizard that writes is no longer one.

        The U1/U2 precedent: the wizard collects an argument an object button
        cannot pass and calls a sanctioned server action. Anything else moves
        business logic into the UI layer, where none of the guards live.

        Correction A (independent review, Defect #1) is the one sanctioned
        exception to "never write/create": the TD-015 acknowledgement
        wizard now overrides `create()`/`write()` to validate a
        caller-supplied `binding_id` (access control, read-only) BEFORE
        delegating to `super().create()`/`super().write()` to actually
        persist it -- which every model's create/write override must
        eventually do. `super().create(...)`/`super().write(...)` is
        therefore excluded from `forbidden` matches; a call to `.create()`/
        `.write()`/`.unlink()`/`.sudo()`/`.commit()`/`.enqueue()` on
        anything else -- `self.env[...]`, `preview_id`, `binding_id`, or
        any other record -- is still caught exactly as before.
        """
        wizard_dir = MODULE_ROOT / 'wizards'
        forbidden = {'create', 'write', 'unlink', 'sudo', 'commit', 'enqueue'}
        offenders = []
        for path in sorted(wizard_dir.rglob('*.py')):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in forbidden
                ):
                    continue
                callee = node.func.value
                is_super_call = (
                    node.func.attr in ('create', 'write')
                    and isinstance(callee, ast.Call)
                    and isinstance(callee.func, ast.Name)
                    and callee.func.id == 'super'
                )
                if is_super_call:
                    continue
                offenders.append((path.name, node.func.attr, node.lineno))
        self.assertEqual(offenders, [], 'a wizard performs a write-side call')

    def test_the_only_super_create_or_write_call_is_the_sanctioned_one(self):
        """The exclusion above is narrow by construction, and this proves
        it: exactly one wizard class overrides `create`/`write` at all, and
        it is the one Correction A names."""
        wizard_dir = MODULE_ROOT / 'wizards'
        super_calls = []
        for path in sorted(wizard_dir.rglob('*.py')):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if node.name not in ('create', 'write'):
                    continue
                super_calls.append((path.name, node.name, node.lineno))
        self.assertEqual(
            [name for _, name, _ in super_calls], ['create', 'write'],
        )
        self.assertTrue(
            all(
                path == 'shopify_connector_product_export_wizards.py'
                for path, _, _ in super_calls
            ),
        )

    def test_no_view_file_contains_a_mutation_name(self):
        """Mutation logic never lives in XML.

        A GraphQL operation in a view would mean a screen builds a request,
        which puts a merchant's catalog behind an XML edit with no test and no
        Layer 2 attempt.
        """
        offenders = []
        for path in sorted((MODULE_ROOT / 'views').rglob('*.xml')):
            source = path.read_text()
            for token in (
                'productSet', 'productUpdate', 'productVariantsBulk',
                'fileCreate', 'fileUpdate', 'stagedUploadsCreate',
                'mutation ',
            ):
                if token in source:
                    offenders.append((path.name, token))
        self.assertEqual(offenders, [])

    # ------------------------------------------------------------------
    # Every sudo() in this module is accounted for
    # ------------------------------------------------------------------

    def test_the_sudo_inventory_is_frozen(self):
        """A new `sudo()` has to be added here deliberately.

        The same standing guard the core module carries: an unreviewed
        elevation is how an access boundary erodes one commit at a time. The
        count is per file so a diff shows exactly where a new one appeared.
        """
        expected = {
            # 20 -> 21 (2026-07-27): the apply handler now terminalises its
            # own job before handing off to the first step, because the
            # parent and the child compute a byte-identical
            # `operation_scope_key` and the parent has to release it first.
            # The elevation is the same one the dispatcher applies to the
            # same field on the same record one frame later
            # (`_invoke_handler`'s own `job.sudo().write({'state':
            # 'succeeded'})`), on a job the dispatcher has already claimed
            # and admitted -- it is a state write on connector-owned
            # bookkeeping, reachable only from inside a claimed dispatch,
            # and it exposes no new operator-facing surface. Authorisation
            # and company access were established upstream at enqueue
            # (`enqueue_preview` / `action_confirm_export_preview`).
            # 21 -> 22 (PR #206 product contract repair). Create
            # finalization now writes a fully evidenced pre-existing variant
            # binding when Shopify returns the durable variant identity. The
            # binding fields are connector-protected, the path is reachable
            # only from an admitted create job, and omitting this elevation
            # would leave the create replay boundary incomplete.
            'shopify_connector_product_export_service.py': 22,
            # 20 -> 26 (TD-011, authorised deliberately). Six elevations,
            # each reviewed:
            #   `_admit_media_job`      1 - reads the connector's own job
            #                               table to coalesce a duplicate
            #                               admission.
            #   `_media_resume_blocker` 2 - reads this row's jobs and their
            #                               mutation attempts to establish
            #                               whether the previous outcome is
            #                               still ambiguous.
            #   `_resume_media_export`  3 - writes `resume_attempt` and
            #                               `resume_blocked_reason` on the
            #                               media row, both of which are
            #                               protected binding fields and so
            #                               are unwritable without it.
            # All six touch connector-owned rows only, expose no new
            # operator-facing surface, and add no user-reachable authority:
            # a resume is admitted by the same service that already admits
            # every other media step, under the preview whose authorisation
            # was established upstream at confirmation.
            #
            # 26 -> 28 (TD-011 correction, 2026-07-27). Two more:
            #   `_outstanding_media_job` 1 - reads this row's own jobs to
            #                                find one still queued, so a
            #                                repeated resume coalesces
            #                                instead of admitting a second
            #                                live attempt at one image.
            #   `_resume_media_export`   1 - clears `resume_blocked_reason`
            #                                on the coalesce path; same
            #                                protected field, same reason as
            #                                the three above.
            'shopify_connector_media_export_service.py': 28,
            'shopify_connector_product_export_preview.py': 2,
            # PR #206 product contract repair adds two reviewed elevations:
            #   create recovery preview 1 - after Administrator, company,
            #                               state and definitely-not-applied
            #                               evidence checks, read the protected
            #                               preview that owns the source product;
            #   import finalization      1 - mark the imported product eligible
            #                               for safe preview-based updates. The
            #                               field is connector-owned and this is
            #                               the production importer transition.
            'shopify_connector_product_export_seams.py': 2,
            # PD-PX-7 (TD-015). Eleven elevations, all on connector-owned
            # rows and none reachable by an unauthorised user:
            #   store state           4 - `export_reconcile_*` are readonly
            #                             protected fields on the store.
            #   binding scope + state 4 - reads every exported binding and
            #                             records its verdict; the verdict
            #                             is protected binding evidence, so
            #                             an operator who could write it
            #                             could clear their own block.
            #   variant + media reads 2 - the identity sets the verdict
            #                             compares against.
            #   job terminalisation   1 - the same protected-transition
            #                             elevation every handler in this
            #                             module already uses.
            # The two entry points are gated first: the reconnect hook runs
            # only after core's own Administrator-gated `action_reconnect`
            # succeeded, and the manual re-run checks Reviewer/Administrator
            # authority AND company access before anything elevates.
            #
            # 11 -> 15 (TD-015 correction, 2026-07-27). Four more, each on
            # connector-owned bookkeeping and none adding a surface:
            #   `_outstanding_reconcile_jobs`   1 - reads this store's own
            #                                       reconcile jobs to find
            #                                       what a second reconnect
            #                                       would collide with.
            #   `_retire_superseded_reconcile_jobs` 1 - cancels a job from a
            #                                       superseded generation;
            #                                       `state`/`cancel_reason`
            #                                       are protected job fields
            #                                       and unwritable without it.
            #   `_serialize_reconcile_settlement`   1 - bumps the store's own
            #                                       readonly settle sequence,
            #                                       the serialization row.
            #   `_supersede`                    1 - the same protected job
            #                                       transition every handler
            #                                       in this module uses.
            # All four are reachable only from inside a claimed dispatch or
            # from the two already-gated entry points above.
            #
            # 15 -> 20 (TD-015 operator resolution, 2026-07-27). Five more,
            # all on connector-owned bookkeeping the caller must not be able
            # to write directly, and every one of them behind the
            # Administrator + record-access + company checks in
            # `_assert_export_reconcile_ack_authority`:
            #   `_export_reconcile_media_claim`     1 - reads this binding's
            #                                       OWN media rows to build
            #                                       the claim digest. Elevated
            #                                       so a record rule cannot
            #                                       silently shorten the claim
            #                                       and make a partial digest
            #                                       look like a match.
            #   `_export_reconcile_clear_acknowledgement` 1 - the ack fields
            #                                       are protected binding
            #                                       fields; dropping a
            #                                       superseded ack is exactly
            #                                       what a non-su write is
            #                                       refused for.
            #   `action_shopify_export_acknowledge_checksum` 1 - writes those
            #                                       same protected fields
            #                                       AFTER authority, record
            #                                       access, company and
            #                                       eligibility have all been
            #                                       established.
            #   `_reassert_export_reconcile_acknowledgements` 2 - reads this
            #                                       store's own outstanding
            #                                       reviews and re-applies the
            #                                       block on the store's own
            #                                       readonly verdict fields.
            'shopify_connector_export_reconnect.py': 20,
            # 0 -> 1 (TD-011 correction, 2026-07-27). The public resume
            # action reads its own store's company through `sudo()` to
            # compare it against the acting user's allowed companies. It is
            # a read of one field on the store this row already belongs to,
            # and it happens AFTER the role check and AFTER
            # `check_access('read')` has re-run the model ACL and both
            # company record rules for the acting user on this row. Nothing
            # is written under it, and the elevation exists so the company
            # comparison itself cannot be defeated by a record rule that
            # would hide the store and turn "wrong company" into "no
            # company".
            'shopify_connector_product_media_binding.py': 1,
            'shopify_connector_product_export_wizards.py': 0,
            # U3: the export preview projection reads as the CURRENT user on
            # purpose, so the ordinary ACL and the SEC-3 company record rules
            # apply to it. A budget above zero here would mean the read
            # surface had acquired an elevation, which is exactly the thing
            # this inventory exists to make impossible to add quietly.
            'shopify_connector_product_export_ui.py': 0,
            '__init__.py': 0,
            '__manifest__.py': 0,
        }
        actual = {}
        for path in _python_sources():
            source = path.read_text()
            actual[path.name] = source.count('.sudo(')
        for name, count in actual.items():
            with self.subTest(file=name):
                self.assertIn(
                    name, expected,
                    'a new module file needs a sudo() budget entry',
                )
                self.assertEqual(
                    count, expected[name],
                    'the sudo() count changed in %s: review each elevation '
                    'and update the inventory deliberately' % name,
                )

    # ------------------------------------------------------------------
    # The API version is never hard-coded away from the constant
    # ------------------------------------------------------------------

    def test_no_module_file_hard_codes_an_api_version(self):
        """The version lives in exactly one place.

        A second literal is how a request ends up addressed at a schema
        nobody verified.
        """
        offenders = []
        for path in _python_sources():
            source = path.read_text()
            for token in ('/admin/api/', "'2025-", "'2026-", '"2026-'):
                if token in source:
                    offenders.append((path.name, token))
        self.assertEqual(offenders, [])

    # ------------------------------------------------------------------
    # Test-phase contract (issues #193 / #157)
    # ------------------------------------------------------------------

    def test_every_test_class_declares_its_phase(self):
        """Every connector test class carries `post_install`/`-at_install`.

        Odoo 19 unions `tagged` arguments onto the inherited default
        `{'standard', 'at_install'}`, so omitting `-at_install` leaves a class
        carrying both phases; and an `at_install` class whose fixtures touch a
        table another module extends with a required column fails only on the
        warm update, which is exactly the #193 family.
        """
        offenders = []
        for path in sorted((MODULE_ROOT / 'tests').rglob('test_*.py')):
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                tags = set()
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    for argument in decorator.args:
                        if isinstance(argument, ast.Constant):
                            tags.add(argument.value)
                if not {'post_install'} <= tags or '-at_install' not in tags:
                    offenders.append((path.name, node.name, sorted(tags)))
        self.assertEqual(offenders, [])
