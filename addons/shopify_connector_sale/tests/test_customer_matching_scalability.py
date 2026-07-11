"""Task 011B -- customer matching scalability (indexed normalized lookup).

Proves the indexed candidate lookup added by Task 011B is recall-
equivalent to the merged O(n) full scan it replaces, that every Task 011
routing outcome is unchanged, that duplicate/ambiguity/concurrency
behaviour is preserved, and that the source-level guards (indexed domain,
identical `email_normalize(strict=False)` on both sides, no new match
key) hold. A separate `-standard`-excluded benchmark class carries the
D-011B-7 100k performance harness.
"""

import ast
import json
import os
import random
import uuid
from time import perf_counter
from unittest.mock import patch

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
    # Concurrency (tests 22-23) -- D-011B-6.
    # ==================================================================

    @mute_logger('odoo.sql_db')
    def test_existing_binding_uniqueness_prevents_duplicate_binding(self):
        partner_1 = self._make_partner('Uniq A')
        partner_2 = self._make_partner('Uniq B')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/2200',
            'partner_id': partner_1.id,
        })
        # UNIQUE(store_id, shopify_gid).
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/2200',
                    'partner_id': partner_2.id,
                })
        # UNIQUE(store_id, partner_id).
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/2201',
                    'partner_id': partner_1.id,
                })

    @mute_logger('odoo.sql_db')
    def test_colliding_import_attempts_leave_single_binding(self):
        partner = self._make_partner('Collide', email='collide@%s' % ROUTE_DOMAIN)
        first = self.Importer._apply_import(self.store, self._customer_payload(
            'gid://shopify/Customer/2202', email='collide@%s' % ROUTE_DOMAIN,
        ))
        self.assertEqual(first.partner_id, partner)
        # A second, different Shopify customer that matches the same
        # partner routes through the existing binding-conflict taxonomy --
        # no second binding row, no duplicate.
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

    TARGET_PARTNERS = 100000
    ARCHIVED_RATIO = 0.30
    WRAPPED_RATIO = 0.10
    SHARED_RATIO = 0.01
    SEED = 20260711
    BATCH = 5000
    LATENCY_SAMPLES = 500
    THROUGHPUT_CUSTOMERS = 1000
    SHARED_EMAIL = 'shared-benchmark@bench011b.example'

    def _emit(self, label, value):
        print('[TASK-011B-BENCHMARK] %s=%s' % (label, value))

    def _generate_dataset(self):
        """Deterministically create TARGET_PARTNERS partners:
        >=30% archived, >=10% wrapped/display-name, >=1% shared normalized
        email. Returns the wall-clock generation (create + stored-compute)
        duration in seconds."""
        rng = random.Random(self.SEED)
        Partner = self.env['res.partner']
        created = 0
        start = perf_counter()
        while created < self.TARGET_PARTNERS:
            chunk = []
            batch_size = min(self.BATCH, self.TARGET_PARTNERS - created)
            for offset in range(batch_size):
                idx = created + offset
                form = rng.random()
                if form < self.SHARED_RATIO:
                    email = self.SHARED_EMAIL
                elif form < self.SHARED_RATIO + self.WRAPPED_RATIO:
                    # Wrapped/display-name/mixed-case; normalizes to the
                    # same bare address as the normal form for this idx.
                    email = '"User %d" <User.%d@Bench011b.Example>' % (idx, idx)
                else:
                    email = 'user.%d@bench011b.example' % idx
                active = rng.random() >= self.ARCHIVED_RATIO
                chunk.append({
                    'name': 'Bench Partner %d' % idx,
                    'email': email,
                    'active': active,
                })
            Partner.create(chunk)
            created += batch_size
        self.env.flush_all()
        return perf_counter() - start

    def _measure_backfill_proxy(self):
        """Proxy for the stored-compute backfill: force a full recompute
        of the normalized column over every partner and time it. This
        approximates the single-pass cost Odoo's stored-compute
        initialization incurs at module upgrade; the AUTHORITATIVE upgrade
        duration must still be measured by an actual module upgrade on a
        runtime host (recorded separately in the validation record)."""
        Partner = self.env['res.partner']
        field = Partner._fields['shopify_connector_email_normalized']
        everyone = Partner.with_context(active_test=False).search([])
        self.env.invalidate_all()
        start = perf_counter()
        try:
            self.env.add_to_compute(field, everyone)
            everyone._recompute_field(field)
            self.env.flush_all()
        except Exception as exc:  # pragma: no cover - version-guarded proxy
            self._emit('backfill_proxy.error', repr(exc))
            return None
        return perf_counter() - start

    def _percentile(self, sorted_samples, pct):
        if not sorted_samples:
            return None
        rank = max(0, min(
            len(sorted_samples) - 1,
            int(round((pct / 100.0) * (len(sorted_samples) - 1))),
        ))
        return sorted_samples[rank]

    def test_benchmark_100k_customer_matching(self):
        generation_seconds = self._generate_dataset()
        Partner = self.env['res.partner']
        total = Partner.with_context(active_test=False).search_count([])
        archived = Partner.with_context(active_test=False).search_count(
            [('active', '=', False)],
        )
        non_null = Partner.with_context(active_test=False).search_count(
            [('shopify_connector_email_normalized', '!=', False)],
        )
        self._emit('dataset.requested_partners', self.TARGET_PARTNERS)
        self._emit('dataset.total_partners_in_db', total)
        self._emit('dataset.archived_partners_in_db', archived)
        self._emit('dataset.non_null_normalized', non_null)
        self._emit('dataset.generation_seconds', round(generation_seconds, 3))

        # (3) Backfill/recompute-pass duration proxy.
        backfill_seconds = self._measure_backfill_proxy()
        if backfill_seconds is not None:
            self._emit('backfill_proxy.seconds', round(backfill_seconds, 3))

        # (1) Single-customer indexed-match latency (cold cache each probe).
        rng = random.Random(self.SEED + 1)
        latencies = []
        for _ in range(self.LATENCY_SAMPLES):
            idx = rng.randrange(self.TARGET_PARTNERS)
            normalized = 'user.%d@bench011b.example' % idx
            Partner.invalidate_model(['shopify_connector_email_normalized'])
            start = perf_counter()
            self.Importer._find_active_candidates(normalized)
            latencies.append((perf_counter() - start) * 1000.0)
        latencies.sort()
        self._emit('latency.samples', len(latencies))
        self._emit('latency.p50_ms', round(self._percentile(latencies, 50), 3))
        self._emit('latency.p95_ms', round(self._percentile(latencies, 95), 3))
        self._emit('latency.max_ms', round(max(latencies), 3))
        self._emit('latency.budget_p95_ms', 50)

        # (2) Sequential matching throughput.
        rng2 = random.Random(self.SEED + 2)
        start = perf_counter()
        for _ in range(self.THROUGHPUT_CUSTOMERS):
            idx = rng2.randrange(self.TARGET_PARTNERS)
            self.Importer._find_active_candidates(
                'user.%d@bench011b.example' % idx,
            )
        throughput_seconds = perf_counter() - start
        per_second = self.THROUGHPUT_CUSTOMERS / throughput_seconds if throughput_seconds else 0
        self._emit('throughput.customers', self.THROUGHPUT_CUSTOMERS)
        self._emit('throughput.total_seconds', round(throughput_seconds, 3))
        self._emit('throughput.customers_per_second', round(per_second, 2))
        self._emit('throughput.budget_customers_per_second', 20)

        # The harness asserts only that it produced a full, deterministic
        # dataset; budget pass/fail is judged against the emitted numbers
        # in the validation record (never asserted here, so a slow host
        # cannot red the suite).
        self.assertEqual(total >= self.TARGET_PARTNERS, True)
        self.assertGreaterEqual(archived, int(self.TARGET_PARTNERS * self.ARCHIVED_RATIO * 0.9))
        self.assertTrue(latencies)
