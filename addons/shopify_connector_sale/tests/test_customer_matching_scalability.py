"""Task 011B -- customer matching scalability (indexed normalized lookup).

Proves the indexed candidate lookup added by Task 011B is recall-
equivalent to the merged O(n) full scan it replaces, that every Task 011
routing outcome is unchanged, that duplicate/ambiguity behaviour is
preserved, and that the source-level guards (indexed domain, identical
`email_normalize(strict=False)` on both sides, no new match key) hold.

Two `-standard`-excluded classes carry the runtime-only work:
`TestCustomerMatchingConcurrency` (D-011B-6, a genuine independent-
transaction binding race through the real dispatcher) and
`TestCustomerMatchingBenchmark` (D-011B-7, the deterministic 100k
performance harness). Both are authored to run under an explicit test-tag
invocation on a runtime host; neither runs in the standard CI pass.
"""

import ast
import json
import os
import threading
import time
import uuid
from time import perf_counter
from unittest.mock import patch

import psycopg2

from odoo import SUPERUSER_ID, api
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import email_normalize, mute_logger

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


# Reserved-TLD, connector-unique domains so corpus/routing fixtures never
# collide with base/demo partners already present in the test database.
CORPUS_DOMAIN = 'corpus011b.example'
ROUTE_DOMAIN = 't011b.example'


class _CustomerMatchingScalabilityBase(TransactionCase):
    """Shared fixtures + the test-only old-path reference implementation
    (D-011B-3 backstop) and source-path helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Customer Matching Scalability Test Store',
            'shop_domain': 'customer-matching-scalability-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.customer.importer']
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']
        cls.Partner = cls.env['res.partner']

    # ------------------------------------------------------------------
    # Fixtures.
    # ------------------------------------------------------------------

    def _make_partner(self, name, email=None, active=True):
        vals = {'name': name}
        if email is not None:
            vals['email'] = email
        if not active:
            vals['active'] = False
        return self.env['res.partner'].create(vals)

    def _customer_payload(self, gid, email=None, display_name=None, address=None):
        return {
            'gid': gid, 'first_name': None, 'last_name': None,
            'display_name': display_name or gid, 'email': email,
            'phone': None, 'address': address,
        }

    # ------------------------------------------------------------------
    # D-011B-3 backstop: the exact merged full-scan candidate search,
    # retained here ONLY as a test-time reference implementation (never in
    # production code) to prove candidate-set equivalence.
    # ------------------------------------------------------------------

    def _old_path_active_candidates(self, normalized_incoming):
        Partner = self.env['res.partner']
        candidates = Partner.search([('email', '!=', False)])
        return candidates.filtered(
            lambda partner: email_normalize(
                partner.email, strict=False,
            ) == normalized_incoming
        )

    def _old_path_archived_candidates(self, normalized_incoming):
        Partner = self.env['res.partner']
        candidates = Partner.with_context(active_test=False).search([
            ('email', '!=', False), ('active', '=', False),
        ])
        return candidates.filtered(
            lambda partner: email_normalize(
                partner.email, strict=False,
            ) == normalized_incoming
        )

    # ------------------------------------------------------------------
    # The pathological equivalence corpus (D-011B-3). Every entry is
    # created as BOTH an active and an archived partner so a single build
    # exercises both search dimensions; extra fixtures cover shared
    # normalized emails and mixed active/archived copies.
    # ------------------------------------------------------------------

    def _corpus_stored_emails(self):
        return [
            'alpha@%s' % CORPUS_DOMAIN,                                   # normal lowercase
            'Beta@Corpus011b.Example',                                    # mixed case
            '   gamma@%s   ' % CORPUS_DOMAIN,                             # leading/trailing whitespace
            '"Del Ta" <Del.TA@Corpus011b.Example>',                      # wrapped display-name
            '"Epsilon, Inc." <epsilon@%s>' % CORPUS_DOMAIN,              # quoted display name
            'zeta+shop@%s' % CORPUS_DOMAIN,                              # plus-addressing
            'ünïcödé@%s' % CORPUS_DOMAIN,                                # unicode local part
            'eta@CORPUS011B.EXAMPLE',                                    # uppercase domain
            'not-an-email',                                              # malformed
            '',                                                          # empty string
            'theta@%s, other-theta@%s' % (CORPUS_DOMAIN, CORPUS_DOMAIN),  # multiple-email / comma
            'kappa@%s; other-kappa@%s' % (CORPUS_DOMAIN, CORPUS_DOMAIN),  # semicolon-separated
        ]

    def _build_equivalence_corpus(self):
        """Materialise the corpus and return the probe list to compare
        old-path vs new-path candidate sets against."""
        stored = self._corpus_stored_emails()
        for index, raw in enumerate(stored):
            self._make_partner('Corpus Active %d' % index, email=raw, active=True)
            self._make_partner('Corpus Archived %d' % index, email=raw, active=False)
        # False (no email at all), active and archived.
        self._make_partner('Corpus Active NoEmail', email=None, active=True)
        self._make_partner('Corpus Archived NoEmail', email=None, active=False)
        # Duplicated normalized email across multiple partners (ambiguity).
        self._make_partner('Dup One', email='lambda@%s' % CORPUS_DOMAIN, active=True)
        self._make_partner('Dup Two', email='LAMBDA@Corpus011b.Example', active=True)
        # Active + archived copies of the same normalized email.
        self._make_partner('Copy Active', email='mu@%s' % CORPUS_DOMAIN, active=True)
        self._make_partner('Copy Archived', email='mu@%s' % CORPUS_DOMAIN, active=False)

        probes = list(stored) + [
            'lambda@%s' % CORPUS_DOMAIN,
            'LAMBDA@%s' % CORPUS_DOMAIN,
            'mu@%s' % CORPUS_DOMAIN,
            'ALPHA@%s' % CORPUS_DOMAIN,
            'Del.TA@Corpus011b.Example',
            'nobody-matches@%s' % CORPUS_DOMAIN,
            False,
            None,
        ]
        return probes

    # ------------------------------------------------------------------
    # Source-path / AST helpers for the source guards.
    # ------------------------------------------------------------------

    def _models_dir(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )

    def _read_source(self, filename):
        path = os.path.join(self._models_dir(), filename)
        with open(path, 'r', encoding='utf-8') as source_file:
            return path, source_file.read()

    def _parse(self, filename):
        path, content = self._read_source(filename)
        return path, content, ast.parse(content, filename=path)

    def _find_function(self, tree, name):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def _string_constants(self, node):
        return {
            child.value for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }

    def _email_normalize_calls(self, node):
        calls = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            is_norm = (
                (isinstance(func, ast.Name) and func.id == 'email_normalize')
                or (isinstance(func, ast.Attribute) and func.attr == 'email_normalize')
            )
            if is_norm:
                calls.append(child)
        return calls


class TestCustomerMatchingScalability(_CustomerMatchingScalabilityBase):

    # ==================================================================
    # Field + compute (tests 1-8).
    # ==================================================================

    def test_field_is_stored(self):
        field = self.env['res.partner']._fields['shopify_connector_email_normalized']
        self.assertTrue(field.store, 'the normalized-email field must be stored')
        # A real column exists in the database.
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'res_partner' AND column_name = %s",
            ['shopify_connector_email_normalized'],
        )
        self.assertTrue(
            self.env.cr.fetchall(),
            'a real res_partner column must back the stored field',
        )

    def test_field_is_indexed(self):
        field = self.env['res.partner']._fields['shopify_connector_email_normalized']
        self.assertTrue(field.index, 'the field must declare an index')
        self.assertIn(
            field.index, (True, 'btree'),
            'D-011B-1 mandates a plain btree index (index=True)',
        )
        # A btree index on the column exists in the database.
        self.env.cr.execute(
            "SELECT indexdef FROM pg_indexes WHERE tablename = 'res_partner' "
            "AND indexdef ILIKE %s",
            ['%shopify_connector_email_normalized%'],
        )
        self.assertTrue(
            self.env.cr.fetchall(),
            'a database index on shopify_connector_email_normalized must exist',
        )

    def test_field_is_readonly(self):
        field = self.env['res.partner']._fields['shopify_connector_email_normalized']
        self.assertTrue(field.readonly, 'the field must be readonly')

    def test_compute_uses_email_normalize_strict_false(self):
        raw = '"Jane Doe" <Jane.DOE@Example.COM>'
        partner = self._make_partner('Compute Wrapped', email=raw)
        # The stored value is exactly what the merged normalizer produces
        # (email_normalize with strict=False), not a hand-coded value.
        self.assertEqual(
            partner.shopify_connector_email_normalized,
            email_normalize(raw, strict=False),
        )

    def test_partner_creation_computes_value(self):
        partner = self._make_partner(
            'Create Compute', email='create-compute@%s' % ROUTE_DOMAIN,
        )
        self.assertEqual(
            partner.shopify_connector_email_normalized,
            'create-compute@%s' % ROUTE_DOMAIN,
        )

    def test_email_change_recomputes_value(self):
        partner = self._make_partner('Change', email='before@%s' % ROUTE_DOMAIN)
        partner.write({'email': 'after@%s' % ROUTE_DOMAIN})
        self.assertEqual(
            partner.shopify_connector_email_normalized,
            'after@%s' % ROUTE_DOMAIN,
        )

    def test_email_clear_sets_false(self):
        partner = self._make_partner('Clear', email='clear@%s' % ROUTE_DOMAIN)
        self.assertTrue(partner.shopify_connector_email_normalized)
        partner.write({'email': False})
        self.assertFalse(partner.shopify_connector_email_normalized)

    def test_archived_partner_retains_and_recomputes_value(self):
        partner = self._make_partner('Arch', email='arch-before@%s' % ROUTE_DOMAIN)
        partner.write({'active': False})
        # Retained after archiving.
        self.assertEqual(
            partner.shopify_connector_email_normalized,
            'arch-before@%s' % ROUTE_DOMAIN,
        )
        # Recomputed on an email change while archived.
        partner.write({'email': 'arch-after@%s' % ROUTE_DOMAIN})
        self.assertEqual(
            partner.shopify_connector_email_normalized,
            'arch-after@%s' % ROUTE_DOMAIN,
        )
        # And found through the indexed column with active_test=False.
        found = self.env['res.partner'].with_context(active_test=False).search([
            ('shopify_connector_email_normalized', '=', 'arch-after@%s' % ROUTE_DOMAIN),
        ])
        self.assertIn(partner, found)

    # ==================================================================
    # Equivalence (tests 9-14) -- old path vs new path, D-011B-3.
    # ==================================================================

    def test_equivalence_active_candidates_across_corpus(self):
        probes = self._build_equivalence_corpus()
        for raw in probes:
            normalized = email_normalize(raw, strict=False) if raw else False
            if not normalized:
                # A falsy normalized value never reaches the candidate
                # search in production (guarded upstream) -- covered by
                # test_invalid_and_empty_incoming_behaviour_unchanged.
                continue
            old_ids = set(self._old_path_active_candidates(normalized).ids)
            new_ids = set(self.Importer._find_active_candidates(normalized).ids)
            self.assertEqual(
                old_ids, new_ids,
                'active candidate divergence for probe %r (normalized %r)'
                % (raw, normalized),
            )

    def test_equivalence_archived_candidates_across_corpus(self):
        probes = self._build_equivalence_corpus()
        for raw in probes:
            normalized = email_normalize(raw, strict=False) if raw else False
            if not normalized:
                continue
            old_ids = set(self._old_path_archived_candidates(normalized).ids)
            new_ids = set(self.Importer._find_archived_candidates(normalized).ids)
            self.assertEqual(
                old_ids, new_ids,
                'archived candidate divergence for probe %r (normalized %r)'
                % (raw, normalized),
            )

    def test_wrapped_display_name_recall_unchanged(self):
        partner = self._make_partner(
            'Wrapped Recall', email='"Jane Doe" <Jane.DOE@Example.COM>',
        )
        normalized = email_normalize('jane.doe@example.com', strict=False)
        old_ids = set(self._old_path_active_candidates(normalized).ids)
        new_ids = set(self.Importer._find_active_candidates(normalized).ids)
        self.assertEqual(old_ids, new_ids)
        self.assertIn(partner.id, new_ids)

    def test_mixed_case_behaviour_unchanged(self):
        partner = self._make_partner('Mixed', email='foo@bar.com')
        for probe in ('Foo@BAR.com', 'FOO@BAR.COM', 'foo@bar.com'):
            normalized = email_normalize(probe, strict=False)
            old_ids = set(self._old_path_active_candidates(normalized).ids)
            new_ids = set(self.Importer._find_active_candidates(normalized).ids)
            self.assertEqual(old_ids, new_ids, probe)
            self.assertIn(partner.id, new_ids)

    def test_shared_normalized_ambiguity_unchanged(self):
        p1 = self._make_partner('Shared A', email='shared@%s' % ROUTE_DOMAIN)
        p2 = self._make_partner('Shared B', email='Shared@%s' % ROUTE_DOMAIN)
        normalized = email_normalize('shared@%s' % ROUTE_DOMAIN, strict=False)
        old_ids = set(self._old_path_active_candidates(normalized).ids)
        new_ids = set(self.Importer._find_active_candidates(normalized).ids)
        self.assertEqual(old_ids, new_ids)
        self.assertEqual(new_ids, {p1.id, p2.id})

    def test_invalid_and_empty_incoming_behaviour_unchanged(self):
        # The incoming-normalization guard is identical to the merged
        # code; a falsy normalized value never triggers a candidate
        # search, exactly as before Task 011B.
        for raw in ('not-an-email', '', False, None, '   '):
            self.assertFalse(self.Importer._normalize_incoming_email(raw), raw)

    # ==================================================================
    # Routing regression (tests 15-21) -- Task 011 outcomes on the new
    # indexed path.
    # ==================================================================

    def test_existing_binding_shortcut_unchanged(self):
        partner = self._make_partner('Bound', email='bound@%s' % ROUTE_DOMAIN)
        binding = self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/2100',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        self._make_partner('Decoy', email='decoy@%s' % ROUTE_DOMAIN)
        payload = self._customer_payload(
            'gid://shopify/Customer/2100', email='decoy@%s' % ROUTE_DOMAIN,
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result, binding)
        self.assertEqual(result.partner_id, partner)

    def test_single_active_match_binds_normally(self):
        partner = self._make_partner('Single', email='single@%s' % ROUTE_DOMAIN)
        payload = self._customer_payload(
            'gid://shopify/Customer/2101', email='single@%s' % ROUTE_DOMAIN,
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertEqual(result.partner_id, partner)
        self.assertEqual(result.match_key, 'email')

    def test_multiple_active_matches_route_to_manual_review(self):
        self._make_partner('Amb A', email='amb@%s' % ROUTE_DOMAIN)
        self._make_partner('Amb B', email='amb@%s' % ROUTE_DOMAIN)
        partners_before = self.env['res.partner'].search_count([])
        payload = self._customer_payload(
            'gid://shopify/Customer/2102', email='amb@%s' % ROUTE_DOMAIN,
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/2102'),
        ]))

    def test_candidate_evidence_cap_unchanged(self):
        for index in range(22):
            self._make_partner('Cap %d' % index, email='cap@%s' % ROUTE_DOMAIN)
        payload = self._customer_payload(
            'gid://shopify/Customer/2103', email='cap@%s' % ROUTE_DOMAIN,
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(detail['candidate_count'], 22)
        self.assertEqual(len(detail['candidates']), 20)
        # Deterministic ordering: the first 20 partner ids, ascending.
        shown_ids = [candidate['partner_id'] for candidate in detail['candidates']]
        self.assertEqual(shown_ids, sorted(shown_ids))

    def test_archived_only_result_routes_duplicate_risk(self):
        partner = self._make_partner(
            'Archived Only', email='archived-only@%s' % ROUTE_DOMAIN, active=False,
        )
        payload = self._customer_payload(
            'gid://shopify/Customer/2104', email='archived-only@%s' % ROUTE_DOMAIN,
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        detail = json.loads(ctx.exception.technical_detail)
        self.assertEqual(detail['candidates'][0]['partner_id'], partner.id)
        self.assertEqual(detail['candidates'][0]['active'], False)
        partner.invalidate_recordset()
        self.assertFalse(partner.active)

    def test_no_usable_email_retains_blind_create_block(self):
        partners_before = self.env['res.partner'].search_count([])
        for email in (None, '', 'garbage-no-at'):
            payload = self._customer_payload(
                'gid://shopify/Customer/blind-%s' % (email or 'none'), email=email,
            )
            with self.assertRaises(JobHandlerError) as ctx:
                self.Importer._apply_import(self.store, payload)
            self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['res.partner'].search_count([]), partners_before,
        )

    def test_binding_conflict_behaviour_unchanged(self):
        partner = self._make_partner(
            'Conflict', email='conflict@%s' % ROUTE_DOMAIN,
        )
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/2105',
            'partner_id': partner.id,
            'match_key': 'manual',
        })
        payload = self._customer_payload(
            'gid://shopify/Customer/2106', email='conflict@%s' % ROUTE_DOMAIN,
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertFalse(self.CustomerBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Customer/2106'),
        ]))

    # ==================================================================
    # Binding-uniqueness backstop + sequential stable outcome (D-011B-6
    # supporting evidence). These are single-transaction tests: they prove
    # the DB constraint fires and the post-commit stable route, but they
    # are NOT the concurrency race. The genuine independent-transaction
    # race is `TestCustomerMatchingConcurrency` below (opt-in, runtime).
    # ==================================================================

    @mute_logger('odoo.sql_db')
    def test_binding_uniqueness_constraint_backstop(self):
        """The two binding uniqueness constraints fire at the DB level --
        a specific `psycopg2.IntegrityError`, not a broad Exception. This
        is the constraint backstop the genuine race relies on; it does not
        by itself prove concurrent behaviour."""
        partner_1 = self._make_partner('Uniq A')
        partner_2 = self._make_partner('Uniq B')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/2200',
            'partner_id': partner_1.id,
        })
        # UNIQUE(store_id, shopify_gid).
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/2200',
                    'partner_id': partner_2.id,
                })
        # UNIQUE(store_id, partner_id).
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/2201',
                    'partner_id': partner_1.id,
                })

    def test_sequential_second_import_after_commit_routes_binding_conflict(self):
        """Sequential (NOT concurrent) stable outcome: once the first
        binding is visible, a second Shopify customer that matches the same
        partner is caught by the importer's app-level conflict guard and
        raises `binding_conflict` before any DB write. This is exactly the
        outcome the genuine race reaches only on its *retry* leg (see
        `TestCustomerMatchingConcurrency`); the initial concurrent
        collision is a uniqueness race that routes to
        `unknown_system_error`/`retry_waiting` first, never directly to
        `binding_conflict`."""
        partner = self._make_partner('Collide', email='collide@%s' % ROUTE_DOMAIN)
        first = self.Importer._apply_import(self.store, self._customer_payload(
            'gid://shopify/Customer/2202', email='collide@%s' % ROUTE_DOMAIN,
        ))
        self.assertEqual(first.partner_id, partner)
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, self._customer_payload(
                'gid://shopify/Customer/2203', email='collide@%s' % ROUTE_DOMAIN,
            ))
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertEqual(
            self.CustomerBinding.search_count([
                ('store_id', '=', self.store.id),
                ('partner_id', '=', partner.id),
            ]), 1,
        )

    # ==================================================================
    # Source guards (tests 24-30) -- AST/domain-pattern, D-011B-2 §5.6.
    # ==================================================================

    def test_active_search_does_not_use_full_scan_domain(self):
        _path, _content, tree = self._parse('shopify_connector_customer_importer.py')
        node = self._find_function(tree, '_find_active_candidates')
        self.assertIsNotNone(node)
        constants = self._string_constants(node)
        self.assertNotIn(
            'email', constants,
            "_find_active_candidates must not reference the bare 'email' "
            "field domain of the removed full scan",
        )
        self.assertNotIn(
            '!=', constants,
            "_find_active_candidates must not use the ('email','!=',False) "
            "full-scan domain",
        )

    def test_archived_search_does_not_use_full_scan_domain(self):
        _path, _content, tree = self._parse('shopify_connector_customer_importer.py')
        node = self._find_function(tree, '_find_archived_candidates')
        self.assertIsNotNone(node)
        constants = self._string_constants(node)
        self.assertNotIn('email', constants)
        self.assertNotIn('!=', constants)

    def test_both_searches_use_normalized_indexed_column(self):
        _path, _content, tree = self._parse('shopify_connector_customer_importer.py')
        for name in ('_find_active_candidates', '_find_archived_candidates'):
            node = self._find_function(tree, name)
            constants = self._string_constants(node)
            self.assertIn(
                'shopify_connector_email_normalized', constants,
                '%s must search the indexed normalized-email column' % name,
            )

    def test_compute_and_incoming_paths_use_email_normalize_strict_false(self):
        # Compute side (res.partner field).
        _p, _c, partner_tree = self._parse('shopify_connector_res_partner.py')
        compute = self._find_function(
            partner_tree, '_compute_shopify_connector_email_normalized',
        )
        self.assertIsNotNone(compute)
        # Incoming side (importer).
        _p2, _c2, importer_tree = self._parse(
            'shopify_connector_customer_importer.py',
        )
        incoming = self._find_function(importer_tree, '_normalize_incoming_email')
        self.assertIsNotNone(incoming)

        for label, node in (('compute', compute), ('incoming', incoming)):
            calls = self._email_normalize_calls(node)
            self.assertTrue(
                calls, 'the %s path must call email_normalize' % label,
            )
            for call in calls:
                strict_keywords = [
                    kw for kw in call.keywords if kw.arg == 'strict'
                ]
                self.assertTrue(
                    strict_keywords,
                    'email_normalize in the %s path must pass strict '
                    'explicitly' % label,
                )
                for kw in strict_keywords:
                    self.assertIsInstance(kw.value, ast.Constant)
                    self.assertIs(
                        kw.value.value, False,
                        'the %s path must call email_normalize(strict=False)'
                        % label,
                    )

    def test_no_new_match_key_field_added(self):
        # The two candidate searches reference no name/phone/address key.
        _path, _content, tree = self._parse('shopify_connector_customer_importer.py')
        forbidden_keys = {
            'name', 'display_name', 'complete_name', 'phone', 'mobile',
            'street', 'street2', 'city', 'zip', 'vat', 'commercial_partner_id',
        }
        for name in ('_find_active_candidates', '_find_archived_candidates'):
            node = self._find_function(tree, name)
            constants = self._string_constants(node)
            self.assertFalse(
                constants & forbidden_keys,
                '%s introduced a non-email match key: %r'
                % (name, constants & forbidden_keys),
            )
        # The connector field depends ONLY on email -- no second key.
        _p, _c, partner_tree = self._parse('shopify_connector_res_partner.py')
        compute = self._find_function(
            partner_tree, '_compute_shopify_connector_email_normalized',
        )
        depends_args = set()
        for decorator in compute.decorator_list:
            if isinstance(decorator, ast.Call) and (
                getattr(decorator.func, 'attr', None) == 'depends'
            ):
                depends_args = {
                    arg.value for arg in decorator.args
                    if isinstance(arg, ast.Constant)
                }
        self.assertEqual(
            depends_args, {'email'},
            'the normalized field must depend only on email',
        )

    def test_only_two_importer_methods_changed(self):
        """Only the two candidate-search bodies (and stale docstrings)
        may reference the new indexed column in the importer -- proven by
        the fact that no other importer function mentions it."""
        _path, _content, tree = self._parse(
            'shopify_connector_customer_importer.py',
        )
        touching = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if 'shopify_connector_email_normalized' in self._string_constants(node):
                    touching.add(node.name)
        self.assertEqual(
            touching,
            {'_find_active_candidates', '_find_archived_candidates'},
            'only the two candidate-search methods may reference the '
            'indexed column',
        )

    def test_no_forbidden_mutation_in_new_partner_file(self):
        # D-011B-1 / D-011B-5: the res.partner extension adds one computed
        # column and nothing else -- no override, no constraint, no sudo.
        _path, content = self._read_source('shopify_connector_res_partner.py')
        for forbidden in (
            'def create', 'def write', 'def unlink', '_sql_constraints',
            'models.Constraint', 'api.constrains', 'UNIQUE', '.sudo(',
            'company_dependent',
        ):
            self.assertNotIn(
                forbidden, content,
                'shopify_connector_res_partner.py must not contain %r'
                % forbidden,
            )
        # Exactly one _inherit, and it is res.partner (no other model).
        _p, _c, tree = self._parse('shopify_connector_res_partner.py')
        inherit_targets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if '_inherit' in targets and isinstance(node.value, ast.Constant):
                    inherit_targets.append(node.value.value)
        self.assertEqual(inherit_targets, ['res.partner'])
        # The forbidden customer-binding model was not touched to carry
        # the new index: its (pre-existing, binding-level) uniqueness
        # constraints are unchanged and it never references the column.
        binding_path = os.path.join(
            self._models_dir(), 'shopify_connector_customer_binding.py',
        )
        with open(binding_path, 'r', encoding='utf-8') as source_file:
            binding_content = source_file.read()
        self.assertNotIn('shopify_connector_email_normalized', binding_content)


@tagged('post_install', '-standard', 'shopify_connector_customer_matching_benchmark')
class TestCustomerMatchingBenchmark(_CustomerMatchingScalabilityBase):
    """D-011B-7 performance benchmark harness (tests 31-33).

    Excluded from the standard CI pass via the ``-standard`` tag; invoke
    explicitly, e.g.::

        odoo -d <db> -i shopify_connector_sale \\
            --test-enable --stop-after-init \\
            --test-tags shopify_connector_customer_matching_benchmark

    Every measurement is printed on stdout with the stable prefix
    ``[TASK-011B-BENCHMARK]`` so a runtime host can scrape the numbers
    into ``docs/05-qa/task-011b-validation-results.md``. The dataset is
    deterministically seeded so successive runs are comparable.
    """

    # Deterministic composition (index-based allocation, not probabilistic).
    TARGET_PARTNERS = 100000
    SHARED_COUNT = 1500        # >= 1% shared normalized email
    WRAPPED_COUNT = 10500      # >= 10% wrapped/display-name
    ORDINARY_START = SHARED_COUNT + WRAPPED_COUNT  # 12000
    # active = (idx % 10) >= 3  -> exactly 30% archived (idx%10 in {0,1,2}).
    ARCHIVED_MIN = 30000
    WRAPPED_MIN = 10000
    SHARED_MIN = 1000
    BATCH = 5000
    SHARED_EMAIL = 'shared-benchmark@bench011b.example'
    # Deterministic 1,000-probe matching mix (sums to 1,000).
    PROBE_ACTIVE_HITS = 700
    PROBE_ARCHIVED_HITS = 150
    PROBE_MISSES = 100
    PROBE_AMBIGUOUS = 50
    PROBE_TOTAL = 1000

    def _emit(self, label, value):
        print('[TASK-011B-BENCHMARK] %s=%s' % (label, value))

    # ------------------------------------------------------------------
    # Deterministic index-based allocation (no randomness).
    # ------------------------------------------------------------------

    def _is_active_idx(self, idx):
        return (idx % 10) >= 3

    def _email_for_idx(self, idx):
        if idx < self.SHARED_COUNT:
            return self.SHARED_EMAIL
        if idx < self.ORDINARY_START:
            # Wrapped/display-name/mixed-case; normalizes to the same bare
            # address as the ordinary form would for this idx.
            return '"User %d" <User.%d@Bench011b.Example>' % (idx, idx)
        return 'user.%d@bench011b.example' % idx

    def _matching_probe(self, importer, raw_email):
        """Test-only, non-production customer-matching probe: incoming
        normalization + active lookup + archived fallback. No Shopify call,
        no partner/binding creation. Returns (category, n_active,
        n_archived)."""
        normalized = importer._normalize_incoming_email(raw_email)
        if not normalized:
            return ('miss', 0, 0)
        active = importer._find_active_candidates(normalized)
        n_active = len(active)
        if n_active > 1:
            return ('ambiguous', n_active, 0)
        if n_active == 1:
            return ('active_hit', 1, 0)
        archived = importer._find_archived_candidates(normalized)
        n_archived = len(archived)
        if n_archived:
            return ('archived_hit', 0, n_archived)
        return ('miss', 0, 0)

    def _generate_dataset(self):
        """Deterministically create exactly TARGET_PARTNERS partners via
        index-based allocation and return (counters, id_bounds, seconds).

        `counters` are exact by construction; `id_bounds` is the
        (min_id, max_id) contiguous range of the generated rows, used to
        isolate the generated corpus from any pre-existing DB contacts
        (never the whole-DB partner count)."""
        Partner = self.env['res.partner']
        counters = {
            'total': 0, 'active': 0, 'archived': 0,
            'shared': 0, 'wrapped': 0, 'ordinary': 0,
        }
        min_id = max_id = None
        idx = 0
        start = perf_counter()
        while idx < self.TARGET_PARTNERS:
            chunk = []
            batch_size = min(self.BATCH, self.TARGET_PARTNERS - idx)
            for _ in range(batch_size):
                active = self._is_active_idx(idx)
                chunk.append({
                    'name': 'Bench Partner %d' % idx,
                    'email': self._email_for_idx(idx),
                    'active': active,
                })
                counters['total'] += 1
                counters['active' if active else 'archived'] += 1
                if idx < self.SHARED_COUNT:
                    counters['shared'] += 1
                elif idx < self.ORDINARY_START:
                    counters['wrapped'] += 1
                else:
                    counters['ordinary'] += 1
                idx += 1
            records = Partner.create(chunk)
            batch_ids = records.ids
            min_id = batch_ids[0] if min_id is None else min(min_id, min(batch_ids))
            max_id = max(batch_ids) if max_id is None else max(max_id, max(batch_ids))
        self.env.flush_all()
        return counters, (min_id, max_id), perf_counter() - start

    def _measure_backfill_proxy(self):
        """Proxy for the stored-compute backfill: force a full recompute of
        the normalized column over every partner and time it. This
        APPROXIMATES the single-pass cost of Odoo's stored-compute
        initialization; it does NOT replace the authoritative measure,
        which is an actual 100k module upgrade on a runtime host.

        Returns (seconds, None) on success, or (None, sanitized_error) on
        failure -- the caller must treat a failure as an UNUSABLE benchmark
        result, never as a silent pass."""
        Partner = self.env['res.partner']
        everyone = Partner.with_context(active_test=False).search([])
        try:
            self.env.invalidate_all()
            everyone.modified(['email'])
            start = perf_counter()
            self.env.flush_all()
            # Materialize the recomputed values so the timing includes the
            # full recompute+write pass, not only the flush of pending work.
            everyone.mapped('shopify_connector_email_normalized')
            duration = perf_counter() - start
        except Exception as exc:  # noqa: BLE001 - reported, then fails the test
            return None, '%s: %s' % (type(exc).__name__, exc)
        return duration, None

    def _percentile(self, sorted_samples, pct):
        if not sorted_samples:
            return None
        rank = max(0, min(
            len(sorted_samples) - 1,
            int(round((pct / 100.0) * (len(sorted_samples) - 1))),
        ))
        return sorted_samples[rank]

    def _build_probe_mix(self):
        """Deterministic 1,000-probe matching mix: active-unique hits,
        archived-only hits, clean misses, and a small shared/ambiguous
        subset. Ordinary active/archived indices are disjoint (by the
        active rule) and each ordinary email is unique, so every probe's
        category is deterministic."""
        probes = []
        # Active unique hits: ordinary, active, unique email -> 1 candidate.
        idx, collected = self.ORDINARY_START, 0
        while collected < self.PROBE_ACTIVE_HITS:
            if self._is_active_idx(idx):
                probes.append('user.%d@bench011b.example' % idx)
                collected += 1
            idx += 1
        # Archived-only hits: ordinary, archived, unique email -> 0 active,
        # 1 archived.
        idx, collected = self.ORDINARY_START, 0
        while collected < self.PROBE_ARCHIVED_HITS:
            if not self._is_active_idx(idx):
                probes.append('user.%d@bench011b.example' % idx)
                collected += 1
            idx += 1
        # Clean misses: emails absent from the dataset.
        for n in range(self.PROBE_MISSES):
            probes.append('nobody.%d@bench011b.example' % n)
        # Ambiguous: the shared normalized email (many active candidates).
        for _ in range(self.PROBE_AMBIGUOUS):
            probes.append(self.SHARED_EMAIL)
        return probes

    def test_benchmark_100k_customer_matching(self):
        counters, (min_id, max_id), generation_seconds = self._generate_dataset()
        Partner = self.env['res.partner']
        generated = Partner.with_context(active_test=False)
        in_range = [('id', '>=', min_id), ('id', '<=', max_id)]

        # Exact generated-category counters (isolated to the generated id
        # range -- never the whole-DB partner count).
        for key in ('total', 'active', 'archived', 'shared', 'wrapped', 'ordinary'):
            self._emit('dataset.generated_%s' % key, counters[key])
        archived_in_db = generated.search_count(in_range + [('active', '=', False)])
        non_null_in_db = generated.search_count(
            in_range + [('shopify_connector_email_normalized', '!=', False)])
        shared_in_db = generated.search_count(
            in_range + [('shopify_connector_email_normalized', '=', self.SHARED_EMAIL)])
        self._emit('dataset.archived_in_db', archived_in_db)
        self._emit('dataset.non_null_normalized_in_db', non_null_in_db)
        self._emit('dataset.shared_normalized_in_db', shared_in_db)
        self._emit('dataset.generation_seconds', round(generation_seconds, 3))

        # Enforce the required composition on the ACTUAL generated corpus.
        self.assertEqual(counters['total'], self.TARGET_PARTNERS)
        self.assertGreaterEqual(counters['archived'], self.ARCHIVED_MIN)
        self.assertGreaterEqual(counters['wrapped'], self.WRAPPED_MIN)
        self.assertGreaterEqual(counters['shared'], self.SHARED_MIN)
        # The stored index actually grouped the shared-normalized rows and
        # populated a value for every generated partner.
        self.assertEqual(shared_in_db, counters['shared'])
        self.assertEqual(archived_in_db, counters['archived'])
        self.assertEqual(non_null_in_db, counters['total'])

        # Matching-cost probe (incoming normalize + active + archived
        # fallback), 1,000 deterministic probes, cold model cache each probe.
        probes = self._build_probe_mix()
        self.assertEqual(len(probes), self.PROBE_TOTAL)
        importer = self.Importer
        per_probe_seconds = []
        tally = {'active_hit': 0, 'archived_hit': 0, 'miss': 0, 'ambiguous': 0}
        for raw_email in probes:
            Partner.invalidate_model(['shopify_connector_email_normalized'])
            start = perf_counter()
            category, _n_active, _n_archived = self._matching_probe(importer, raw_email)
            per_probe_seconds.append(perf_counter() - start)
            tally[category] += 1

        latencies_ms = sorted(seconds * 1000.0 for seconds in per_probe_seconds)
        total_matching_seconds = sum(per_probe_seconds)
        per_second = (
            self.PROBE_TOTAL / total_matching_seconds
            if total_matching_seconds else 0
        )
        self._emit('probe.count', len(probes))
        self._emit('probe.active_hit', tally['active_hit'])
        self._emit('probe.archived_hit', tally['archived_hit'])
        self._emit('probe.miss', tally['miss'])
        self._emit('probe.ambiguous', tally['ambiguous'])
        self._emit('latency.p50_ms', round(self._percentile(latencies_ms, 50), 3))
        self._emit('latency.p95_ms', round(self._percentile(latencies_ms, 95), 3))
        self._emit('latency.max_ms', round(max(latencies_ms), 3))
        self._emit('latency.budget_p95_ms', 50)
        self._emit(
            'throughput.total_matching_seconds', round(total_matching_seconds, 3))
        self._emit('throughput.customers_per_second', round(per_second, 2))
        self._emit('throughput.budget_customers_per_second', 20)

        # Backfill/recompute-pass proxy -- must NOT silently pass on failure.
        backfill_seconds, backfill_error = self._measure_backfill_proxy()
        if backfill_seconds is None:
            self._emit('backfill_proxy.status', 'UNUSABLE')
            self._emit('backfill_proxy.error', backfill_error)
        else:
            self._emit('backfill_proxy.status', 'measured')
            self._emit('backfill_proxy.seconds', round(backfill_seconds, 3))
        self._emit('backfill_proxy.budget_seconds', 600)
        self._emit(
            'backfill_authoritative',
            'PENDING -- actual 100k module-upgrade duration must be measured '
            'on a runtime host; the proxy does not replace it')

        # Assertions: the intended probe mix was actually exercised, and the
        # backfill proxy produced a usable measurement. Host-dependent timing
        # budgets are emitted, never asserted, so a slow host cannot red the
        # suite; budget pass/fail is judged from the emitted numbers.
        self.assertEqual(tally['active_hit'], self.PROBE_ACTIVE_HITS)
        self.assertEqual(tally['archived_hit'], self.PROBE_ARCHIVED_HITS)
        self.assertEqual(tally['miss'], self.PROBE_MISSES)
        self.assertEqual(tally['ambiguous'], self.PROBE_AMBIGUOUS)
        self.assertEqual(sum(tally.values()), self.PROBE_TOTAL)
        self.assertIsNotNone(
            backfill_seconds,
            'backfill recompute proxy failed -- benchmark result is UNUSABLE '
            '(see [TASK-011B-BENCHMARK] backfill_proxy.error); the '
            'authoritative 100k module-upgrade/backfill duration must be '
            'measured separately on a runtime host')


@tagged('post_install', '-standard', 'shopify_connector_customer_matching_concurrency')
class TestCustomerMatchingConcurrency(TransactionCase):
    """D-011B-6 -- genuine independent-transaction binding race.

    Authored to run under an explicit tag on a runtime host; excluded from
    the standard CI pass (``-standard``) because it opens independent
    PostgreSQL connections, COMMITs synthetic fixtures, spawns a worker
    thread, synchronizes deterministically on a real lock-wait, and durably
    cleans up -- none of which fits ``TransactionCase``'s single
    rolled-back transaction. It does NOT resolve the standing multi-server
    claim/dispatch concurrency caveat (SRR-03/04/09); it proves only the
    binding-layer duplicate-prevention route under a real two-transaction
    race.

    Expected two-stage outcome (recorded exactly by the assertions below):

      1. First collision -- transaction B passes its pre-create checks
         (it cannot see A's uncommitted binding), attempts the colliding
         ``INSERT``, blocks on the ``UNIQUE(store_id, partner_id)`` index,
         and -- once A commits -- fails with a uniqueness violation. The
         importer savepoint rolls back and the dispatcher's fail-safe
         boundary routes the job to ``unknown_system_error`` ->
         ``retry_waiting`` (NOT directly to ``binding_conflict``).
      2. Retry -- with A's binding now committed and visible, the
         importer's app-level conflict guard raises ``binding_conflict``
         -> ``blocked_manual_review``.
      3. Exactly one binding survives (A's, first GID); no duplicate
         partner or binding.
    """

    SHARED_EMAIL = 'race@concurrency011b.example'
    GID_A = 'gid://shopify/Customer/race-A'
    GID_B = 'gid://shopify/Customer/race-B'

    def _fake_execute(self):
        email = self.SHARED_EMAIL

        def fake_execute(client_self, store, query, variables=None):
            return {'data': {'customer': {
                'id': (variables or {}).get('id'),
                'firstName': 'Race', 'lastName': 'B', 'displayName': 'Race B',
                'defaultEmailAddress': {'emailAddress': email},
                'defaultPhoneNumber': None, 'defaultAddress': None,
                'updatedAt': '2026-07-12T00:00:00Z',
            }}}
        return fake_execute

    def _wait_until_lock_blocked(self, monitor_cr, pid, timeout=30.0):
        """Deterministic synchronization: poll pg_stat_activity until the
        backend `pid` is actually waiting on a lock (its colliding INSERT
        blocked on the uncommitted unique row). Returns True once observed,
        False on timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            monitor_cr.execute(
                'SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s',
                (pid,))
            row = monitor_cr.fetchone()
            monitor_cr.rollback()
            if row and row[0] == 'Lock':
                return True
            time.sleep(0.05)
        return False

    def _durable_cleanup(self, dbname, store_id, partner_id, job_id):
        if store_id is None:
            return
        cr = db_connect(dbname).cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.job.log'].search(
                [('job_id', '=', job_id)]).unlink()
            job = env['shopify.connector.job'].browse(job_id).exists()
            if job:
                job.unlink()
            env['shopify.connector.customer.binding'].search(
                [('store_id', '=', store_id)]).unlink()
            partner = env['res.partner'].browse(partner_id).exists()
            if partner:
                partner.unlink()
            env['shopify.connector.store.settings'].search(
                [('store_id', '=', store_id)]).unlink()
            store = env['shopify.connector.store'].browse(store_id).exists()
            if store:
                store.unlink()
            cr.commit()
        except Exception:  # noqa: BLE001 - best-effort cleanup
            cr.rollback()
        finally:
            cr.close()

    @mute_logger('odoo.sql_db', 'odoo.addons.shopify_connector_core')
    def test_genuine_independent_transaction_binding_race(self):
        dbname = self.env.cr.dbname
        client_cls = type(self.env['shopify.connector.api.client'])
        fake_execute = self._fake_execute()

        obs = {}
        setup_cr = cr_a = cr_b = monitor_cr = None
        store_id = partner_id = job_b_id = None
        try:
            # --- committed setup on an independent connection ---
            setup_cr = db_connect(dbname).cursor()
            setup_env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = setup_env['shopify.connector.store'].create({
                'name': 'Race Store',
                'shop_domain': 'race-concurrency-011b.myshopify.com',
                'api_version': '2026-07',
            })
            store.write({'state': 'connected'})
            setup_env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'sale_domain_enabled': True,
            })
            partner = setup_env['res.partner'].create({
                'name': 'Race Partner', 'email': self.SHARED_EMAIL,
            })
            job_b = setup_env['shopify.connector.job'].create({
                'store_id': store.id, 'job_source': 'scheduled_sync',
                'job_type': 'customer_import_sync', 'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
                'shopify_target_gid': self.GID_B,
            })
            store_id, partner_id, job_b_id = store.id, partner.id, job_b.id
            setup_cr.commit()

            # --- Transaction A: create the first binding, hold uncommitted ---
            cr_a = db_connect(dbname).cursor()
            env_a = api.Environment(cr_a, SUPERUSER_ID, {})
            payload_a = {
                'gid': self.GID_A, 'first_name': None, 'last_name': None,
                'display_name': 'Race A', 'email': self.SHARED_EMAIL,
                'phone': None, 'address': None,
            }
            binding_a = env_a['shopify.connector.customer.importer']._apply_import(
                env_a['shopify.connector.store'].browse(store_id), payload_a)
            obs['binding_a_gid'] = binding_a.shopify_gid
            env_a.flush_all()  # force the INSERT so the unique row is held

            # --- Transaction B: dispatch job B in a worker thread; its
            #     colliding INSERT blocks on the uniqueness index ---
            cr_b = db_connect(dbname).cursor()
            cr_b.execute('SELECT pg_backend_pid()')
            pid_b = cr_b.fetchone()[0]
            b_holder = {}

            def run_b():
                try:
                    env_b = api.Environment(cr_b, SUPERUSER_ID, {})
                    with patch.object(client_cls, 'execute', fake_execute):
                        env_b['shopify.connector.job.dispatch']._dispatch_one(
                            env_b['shopify.connector.job'].browse(job_b_id))
                    cr_b.commit()
                    b_holder['done'] = True
                except Exception as exc:  # noqa: BLE001 - surfaced after join
                    b_holder['error'] = '%s: %s' % (type(exc).__name__, exc)

            worker = threading.Thread(target=run_b, name='race-B')
            worker.start()

            monitor_cr = db_connect(dbname).cursor()
            obs['b_blocked'] = self._wait_until_lock_blocked(monitor_cr, pid_b)

            # release A -> B's INSERT now fails on the uniqueness constraint
            cr_a.commit()
            worker.join(timeout=60)
            obs['worker_alive_after_join'] = worker.is_alive()
            obs['b_thread_error'] = b_holder.get('error')

            # --- observe B's first-collision route (fresh read) ---
            setup_cr.rollback()
            job_b_after = setup_env['shopify.connector.job'].browse(job_b_id)
            job_b_after.invalidate_recordset()
            obs['first_state'] = job_b_after.state
            obs['first_error_class'] = job_b_after.error_class

            # --- retry leg: A's binding is committed & visible now ---
            env_r = api.Environment(cr_a, SUPERUSER_ID, {})
            job_b_r = env_r['shopify.connector.job'].browse(job_b_id)
            job_b_r.invalidate_recordset()
            with patch.object(client_cls, 'execute', fake_execute):
                env_r['shopify.connector.job.dispatch']._dispatch_one(job_b_r)
            cr_a.commit()
            setup_cr.rollback()
            job_b_retry = setup_env['shopify.connector.job'].browse(job_b_id)
            job_b_retry.invalidate_recordset()
            obs['retry_state'] = job_b_retry.state
            obs['retry_subreason'] = job_b_retry.manual_review_subreason

            # --- final invariants ---
            bindings = setup_env['shopify.connector.customer.binding'].search(
                [('store_id', '=', store_id), ('partner_id', '=', partner_id)])
            obs['binding_count'] = len(bindings)
            obs['surviving_gid'] = bindings.shopify_gid if len(bindings) == 1 else None
            obs['partner_count'] = setup_env['res.partner'].with_context(
                active_test=False).search_count(
                [('shopify_connector_email_normalized', '=', self.SHARED_EMAIL)])
        finally:
            self._durable_cleanup(dbname, store_id, partner_id, job_b_id)
            for cr in (cr_a, cr_b, monitor_cr, setup_cr):
                if cr is not None:
                    try:
                        cr.close()
                    except Exception:  # noqa: BLE001
                        pass

        # Assertions run AFTER cleanup so a failure never leaks committed rows.
        self.assertTrue(
            obs.get('b_blocked'),
            'transaction B never blocked on the uniqueness lock -- the race '
            'did not occur; the test is inconclusive, not passing')
        self.assertIsNone(
            obs.get('b_thread_error'),
            'the racing worker raised unexpectedly: %s' % obs.get('b_thread_error'))
        self.assertFalse(obs.get('worker_alive_after_join'))
        # First collision is the uniqueness race -> safety-net retry, NOT a
        # direct binding_conflict.
        self.assertEqual(obs['first_state'], 'retry_waiting')
        self.assertEqual(obs['first_error_class'], 'unknown_system_error')
        # Retry reaches the stable manual-review outcome.
        self.assertEqual(obs['retry_state'], 'blocked_manual_review')
        self.assertEqual(obs['retry_subreason'], 'binding_conflict')
        # Exactly one binding survives (first GID); no duplicate partner.
        self.assertEqual(obs['binding_count'], 1)
        self.assertEqual(obs['surviving_gid'], self.GID_A)
        self.assertEqual(obs['partner_count'], 1)
