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
import queue
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
from odoo.addons.shopify_connector_core.tools.redaction import redact


# Reserved-TLD, connector-unique domains so corpus/routing fixtures never
# collide with base/demo partners already present in the test database.
CORPUS_DOMAIN = 'corpus011b.example'
ROUTE_DOMAIN = 't011b.example'

# PostgreSQL table backing shopify.connector.customer.binding. Used only to
# RECOGNISE the colliding binding INSERT in pg_stat_activity (a server-side
# boolean), never to read or expose the raw active-query text (which carries
# the email VALUES of the row being inserted).
BINDING_TABLE = 'shopify_connector_customer_binding'


def _sanitized_exception_diagnostic(exc):
    """Type-only, data-free diagnostic for an exception surfaced from a
    benchmark/concurrency helper.

    NEVER includes ``str(exc)``/``repr(exc)``: a psycopg2/DB error routinely
    embeds partner emails, SQL ``VALUES``, connection paths, or access tokens
    in its message. This emits only the exception class name plus a fixed
    generic sentence, then runs the result through the connector redaction
    helper as defence in depth. The harness still fails loudly on the
    exception -- it simply never leaks the payload into an assertion message
    or the committed documentation. The full unredacted trace remains in the
    runtime host logs."""
    return redact(
        '%s (details suppressed to avoid leaking partner/SQL/credential '
        'data; the full unredacted trace is only in the runtime host logs)'
        % type(exc).__name__
    )


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

    # ==================================================================
    # Sanitized-diagnostic guard (standard CI -- pure Python, no DB).
    # Proves the benchmark backfill-failure path (and the concurrency
    # worker error path) can never leak partner/SQL/credential data even
    # when the underlying exception message carries it.
    # ==================================================================

    def test_helper_diagnostic_strips_sensitive_sentinels(self):
        sentinel_email = 'secret.person@leaked-pii.example'
        sentinel_token = 'shpat_LEAKEDLEAKEDLEAKED000000000000000'
        sentinel_sql = "Key (email)=(%s) already exists" % sentinel_email
        exc = ValueError(
            'duplicate key value violates unique constraint '
            '"res_partner_uniq"; DETAIL: %s; token=%s'
            % (sentinel_sql, sentinel_token)
        )
        diagnostic = _sanitized_exception_diagnostic(exc)
        # The exception TYPE may be identified...
        self.assertIn('ValueError', diagnostic)
        # ...but no fragment of the sensitive payload may appear.
        self.assertNotIn(sentinel_email, diagnostic)
        self.assertNotIn(sentinel_token, diagnostic)
        self.assertNotIn('Key (email)=', diagnostic)
        self.assertNotIn(str(exc), diagnostic)


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
    # Every count below is EXACT by construction and asserted both in-Python
    # and against the DB (isolated to this run's marker, never a whole-DB or
    # id-range count).
    TARGET_PARTNERS = 100000
    SHARED_COUNT = 1500          # exactly 1.5% shared-normalized email (>= 1%)
    WRAPPED_COUNT = 10500        # exactly 10.5% wrapped/display-name (>= 10%)
    ORDINARY_COUNT = 88000       # remainder
    ORDINARY_START = SHARED_COUNT + WRAPPED_COUNT  # 12000
    # active = (idx % 10) >= 3 -> exactly 70% active / 30% archived
    # (idx % 10 in {0,1,2} archived).
    EXPECTED_ACTIVE = 70000
    EXPECTED_ARCHIVED = 30000
    BATCH = 5000
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
        """Deterministic, run-marker-scoped stored email for a corpus index.

        Every generated address ends with this run's unique marker domain,
        and the three categories carry distinct local-part prefixes
        (``shared``, ``wrapped.``, ``user.``) so each category is countable
        in the DB by an exact marker pattern -- never by a fragile id range
        that a concurrent insert could contaminate."""
        if idx < self.SHARED_COUNT:
            return self._shared_email
        if idx < self.ORDINARY_START:
            # Wrapped/display-name form -> normalizes to
            # 'wrapped.<idx>@<marker_domain>'.
            return '"Wrapped %d" <wrapped.%d@%s>' % (
                idx, idx, self._marker_domain)
        return 'user.%d@%s' % (idx, self._marker_domain)

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
        index-based allocation and return (counters, seconds).

        `counters` are exact by construction. Every row also carries this
        run's unique marker (in both its email domain and its name), so the
        DB cross-check counts only rows this run created -- corpus identity
        is the marker, NEVER a min_id..max_id interval a concurrent insert
        could fall inside."""
        Partner = self.env['res.partner']
        counters = {
            'total': 0, 'active': 0, 'archived': 0,
            'shared': 0, 'wrapped': 0, 'ordinary': 0,
        }
        idx = 0
        start = perf_counter()
        while idx < self.TARGET_PARTNERS:
            chunk = []
            batch_size = min(self.BATCH, self.TARGET_PARTNERS - idx)
            for _ in range(batch_size):
                active = self._is_active_idx(idx)
                chunk.append({
                    'name': 'Bench %s %d' % (self._run_marker, idx),
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
            Partner.create(chunk)
        self.env.flush_all()
        return counters, perf_counter() - start

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
            # Type-only, redacted diagnostic -- never str(exc), which for a
            # DB error can embed partner emails / SQL VALUES / credentials.
            return None, _sanitized_exception_diagnostic(exc)
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
        subset -- all scoped to this run's marker domain. Ordinary
        active/archived indices are disjoint (by the active rule) and each
        ordinary email is unique, so every probe's category is
        deterministic."""
        probes = []
        # Active unique hits: ordinary, active, unique email -> 1 candidate.
        idx, collected = self.ORDINARY_START, 0
        while collected < self.PROBE_ACTIVE_HITS:
            if self._is_active_idx(idx):
                probes.append('user.%d@%s' % (idx, self._marker_domain))
                collected += 1
            idx += 1
        # Archived-only hits: ordinary, archived, unique email -> 0 active,
        # 1 archived.
        idx, collected = self.ORDINARY_START, 0
        while collected < self.PROBE_ARCHIVED_HITS:
            if not self._is_active_idx(idx):
                probes.append('user.%d@%s' % (idx, self._marker_domain))
                collected += 1
            idx += 1
        # Clean misses: marker-scoped emails absent from the dataset.
        for n in range(self.PROBE_MISSES):
            probes.append('nobody.%d@%s' % (n, self._marker_domain))
        # Ambiguous: the shared normalized email (many active candidates).
        for _ in range(self.PROBE_AMBIGUOUS):
            probes.append(self._shared_email)
        return probes

    def test_benchmark_100k_customer_matching(self):
        # Per-run marker: a unique domain suffix stamped on every generated
        # row. Corpus identity is this marker -- never a min_id..max_id range
        # a concurrent insert could fall inside (control-room item 6).
        self._run_marker = 'r%s' % uuid.uuid4().hex[:12]
        self._marker_domain = 'b011b-%s.example' % self._run_marker
        self._shared_email = 'shared@%s' % self._marker_domain
        marker_like = '%%@%s' % self._marker_domain
        wrapped_like = 'wrapped.%%@%s' % self._marker_domain
        ordinary_like = 'user.%%@%s' % self._marker_domain

        counters, generation_seconds = self._generate_dataset()
        Partner = self.env['res.partner']
        generated = Partner.with_context(active_test=False)
        self._emit('dataset.run_marker', self._run_marker)

        # Exact in-Python generated-category counters.
        for key in ('total', 'active', 'archived', 'shared', 'wrapped', 'ordinary'):
            self._emit('dataset.generated_%s' % key, counters[key])

        # DB cross-check counts, isolated to THIS run's marker only.
        db_total = generated.search_count(
            [('shopify_connector_email_normalized', '=like', marker_like)])
        db_active = generated.search_count([
            ('shopify_connector_email_normalized', '=like', marker_like),
            ('active', '=', True)])
        db_archived = generated.search_count([
            ('shopify_connector_email_normalized', '=like', marker_like),
            ('active', '=', False)])
        db_shared = generated.search_count(
            [('shopify_connector_email_normalized', '=', self._shared_email)])
        db_wrapped = generated.search_count(
            [('shopify_connector_email_normalized', '=like', wrapped_like)])
        db_ordinary = generated.search_count(
            [('shopify_connector_email_normalized', '=like', ordinary_like)])
        db_non_null = generated.search_count([
            ('shopify_connector_email_normalized', '=like', marker_like),
            ('shopify_connector_email_normalized', '!=', False)])
        self._emit('dataset.marker_total', db_total)
        self._emit('dataset.marker_active', db_active)
        self._emit('dataset.marker_archived', db_archived)
        self._emit('dataset.marker_shared', db_shared)
        self._emit('dataset.marker_wrapped', db_wrapped)
        self._emit('dataset.marker_ordinary', db_ordinary)
        self._emit('dataset.marker_non_null_normalized', db_non_null)
        self._emit('dataset.generation_seconds', round(generation_seconds, 3))

        # Exact in-Python composition (every count exact by construction).
        self.assertEqual(counters['total'], self.TARGET_PARTNERS)
        self.assertEqual(counters['active'], self.EXPECTED_ACTIVE)
        self.assertEqual(counters['archived'], self.EXPECTED_ARCHIVED)
        self.assertEqual(counters['shared'], self.SHARED_COUNT)
        self.assertEqual(counters['wrapped'], self.WRAPPED_COUNT)
        self.assertEqual(counters['ordinary'], self.ORDINARY_COUNT)
        # Exact DB composition, counting ONLY this run's marker rows -- proves
        # the stored index populated and grouped every generated partner and
        # that no unrelated row is being counted.
        self.assertEqual(db_total, self.TARGET_PARTNERS)
        self.assertEqual(db_active, self.EXPECTED_ACTIVE)
        self.assertEqual(db_archived, self.EXPECTED_ARCHIVED)
        self.assertEqual(db_shared, self.SHARED_COUNT)
        self.assertEqual(db_wrapped, self.WRAPPED_COUNT)
        self.assertEqual(db_ordinary, self.ORDINARY_COUNT)
        self.assertEqual(db_non_null, self.TARGET_PARTNERS)

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
    thread that OWNS its own cursor, synchronizes on a real, ATTRIBUTED
    lock-wait, and durably cleans up + verifies -- none of which fits
    ``TransactionCase``'s single rolled-back transaction. It does NOT
    resolve the standing multi-server claim/dispatch concurrency caveat
    (SRR-03/04/09); it proves only the binding-layer duplicate-prevention
    route under a real two-transaction race.

    Execution-safety design (control-room review 4950353232):

      * Worker-owned cursor -- the worker thread itself calls
        ``db_connect(dbname).cursor()``, reports its backend PID to the
        parent through a ``queue.Queue``, builds its own ``Environment``,
        runs the real dispatcher, commits on the handled outcome, rolls
        back on an unexpected exception, and closes its cursor in its own
        ``finally``. No Odoo cursor or ``Environment`` ever crosses the
        thread boundary; parent<->worker signalling is
        ``threading.Event``/``queue.Queue`` only.
      * Attributed lock-wait proof -- synchronization does not accept "B is
        waiting on some lock". It requires ``A_PID IN pg_blocking_pids(B)``
        AND that B's active statement is the customer-binding ``INSERT`` (a
        server-side boolean; the raw query text, which carries the row's
        email VALUES, is never read into Python), and it proves the wait
        CLEARS once A commits.
      * Bounded everything -- worker-start, PID-received, lock-wait and
        join are all bounded; on a stuck worker the test releases the lock
        barrier, waits once more with a bounded emergency timeout, and
        fails closed rather than hanging.
      * Durable cleanup + verification -- all independent cursors are
        rolled back/closed BEFORE a fresh cleanup connection deletes every
        synthetic row (FK-safe order); cleanup never swallows a failure,
        and a second fresh connection asserts zero synthetic rows remain.

    Expected two-stage outcome (asserted below; NOT YET OBSERVED at runtime
    -- there is no Odoo runtime in the authoring session):

      1. First collision -- B passes its pre-create checks (it cannot see
         A's uncommitted binding), attempts the colliding ``INSERT``, blocks
         on ``UNIQUE(store_id, partner_id)`` and -- once A commits -- fails
         with a uniqueness violation. The importer savepoint rolls back and
         the dispatcher's fail-safe boundary routes the job to
         ``unknown_system_error`` -> ``retry_waiting`` (``retry_count == 1``,
         ``next_retry_at`` populated), NOT directly to ``binding_conflict``.
      2. Forced clean-transaction retry -- a deliberate, direct
         ``_dispatch_one`` re-invocation (NOT the scheduler's due-time
         selection) with A's binding now committed & visible: the importer's
         app-level conflict guard raises ``binding_conflict`` ->
         ``blocked_manual_review``.
      3. Exactly one binding survives (A's, first GID); no duplicate
         partner or binding.
    """

    # Bounded timeouts (seconds) -- no unbounded join/poll/cleanup anywhere.
    START_TIMEOUT = 15.0
    PID_TIMEOUT = 15.0
    LOCK_WAIT_TIMEOUT = 30.0
    JOIN_TIMEOUT = 60.0
    EMERGENCY_TIMEOUT = 15.0

    def setUp(self):
        super().setUp()
        # Per-run marker so repeated runs never collide on the shared email,
        # the target GIDs, or the cleanup-verification predicate.
        marker = uuid.uuid4().hex[:12]
        self.run_marker = marker
        self.shared_email = 'race-%s@concurrency011b.example' % marker
        self.gid_a = 'gid://shopify/Customer/race-A-%s' % marker
        self.gid_b = 'gid://shopify/Customer/race-B-%s' % marker

    def _fake_execute(self):
        email = self.shared_email

        def fake_execute(client_self, store, query, variables=None):
            return {'data': {'customer': {
                'id': (variables or {}).get('id'),
                'firstName': 'Race', 'lastName': 'B', 'displayName': 'Race B',
                'defaultEmailAddress': {'emailAddress': email},
                'defaultPhoneNumber': None, 'defaultAddress': None,
                'updatedAt': '2026-07-12T00:00:00Z',
            }}}
        return fake_execute

    # ------------------------------------------------------------------
    # Deterministic, ATTRIBUTED lock-wait synchronization. Evidence is
    # computed server-side and returned as booleans only -- the raw
    # pg_stat_activity.query (which carries the email VALUES of the row
    # being inserted) is never read into Python or an assertion message.
    # ------------------------------------------------------------------

    def _blocking_evidence(self, monitor_cr, waiter_pid, blocker_pid):
        monitor_cr.execute(
            'SELECT '
            '  %(blocker)s = ANY(pg_blocking_pids(%(waiter)s)) AS blocked_by, '
            '  COALESCE(position(%(tbl)s IN query) > 0, FALSE) AS is_binding '
            'FROM pg_stat_activity WHERE pid = %(waiter)s',
            {'blocker': blocker_pid, 'waiter': waiter_pid,
             'tbl': BINDING_TABLE})
        row = monitor_cr.fetchone()
        monitor_cr.rollback()
        if not row:
            return False, False
        return bool(row[0]), bool(row[1])

    def _wait_until_blocked_by(self, monitor_cr, waiter_pid, blocker_pid, timeout):
        """Poll until `waiter_pid` is lock-blocked SPECIFICALLY BY
        `blocker_pid`. Returns (blocked_by_blocker, query_is_binding_path):
        both booleans, captured the moment the block is first observed. A
        bare ``wait_event_type='Lock'`` is NOT accepted as proof."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            blocked_by, is_binding = self._blocking_evidence(
                monitor_cr, waiter_pid, blocker_pid)
            if blocked_by:
                return True, is_binding
            time.sleep(0.05)
        return False, False

    def _wait_until_unblocked(self, monitor_cr, waiter_pid, blocker_pid, timeout):
        """Poll until `blocker_pid` no longer blocks `waiter_pid` (the wait
        cleared after the blocker committed). Returns True once observed."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            blocked_by, _is_binding = self._blocking_evidence(
                monitor_cr, waiter_pid, blocker_pid)
            if not blocked_by:
                return True
            time.sleep(0.05)
        return False

    # ------------------------------------------------------------------
    # Durable cleanup + independent verification (fresh connections).
    # ------------------------------------------------------------------

    def _durable_cleanup(self, dbname, store_id, partner_id, job_id):
        """Delete every committed synthetic row in FK-safe order on a FRESH
        connection. Re-raises on any failure -- the caller records and
        asserts the outcome; a cleanup failure must never pass silently."""
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
            env['shopify.connector.store.settings'].search(
                [('store_id', '=', store_id)]).unlink()
            partner = env['res.partner'].with_context(
                active_test=False).browse(partner_id).exists()
            if partner:
                partner.unlink()
            store = env['shopify.connector.store'].browse(store_id).exists()
            if store:
                store.unlink()
            cr.commit()
        except Exception:
            cr.rollback()
            raise
        finally:
            cr.close()

    def _verify_cleanup(self, dbname, store_id, partner_id, job_id):
        """On a fresh connection, count every synthetic row that should now
        be gone. Returns a dict of remaining counts (all must be zero)."""
        cr = db_connect(dbname).cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            remaining = {
                'logs': env['shopify.connector.job.log'].search_count(
                    [('job_id', '=', job_id)]),
                'jobs': len(env['shopify.connector.job'].browse(job_id).exists()),
                'bindings': env['shopify.connector.customer.binding'].search_count(
                    [('store_id', '=', store_id)]),
                'settings': env['shopify.connector.store.settings'].search_count(
                    [('store_id', '=', store_id)]),
                'partner': len(env['res.partner'].with_context(
                    active_test=False).browse(partner_id).exists()),
                'store': len(env['shopify.connector.store'].browse(
                    store_id).exists()),
            }
            cr.rollback()
            return remaining
        finally:
            cr.close()

    @mute_logger('odoo.sql_db', 'odoo.addons.shopify_connector_core')
    def test_genuine_independent_transaction_binding_race(self):
        dbname = self.env.cr.dbname
        client_cls = type(self.env['shopify.connector.api.client'])
        fake_execute = self._fake_execute()

        obs = {}
        setup_cr = cr_a = monitor_cr = None
        store_id = partner_id = job_b_id = None
        worker = None
        # Thread-safe comms only -- no Odoo cursor/Environment crosses over.
        started_evt = threading.Event()
        done_evt = threading.Event()
        pid_queue = queue.Queue()
        result = {}
        try:
            # --- committed setup on an independent connection ---
            setup_cr = db_connect(dbname).cursor()
            setup_env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = setup_env['shopify.connector.store'].create({
                'name': 'Race Store %s' % self.run_marker,
                'shop_domain': 'race-%s.myshopify.com' % self.run_marker,
                'api_version': '2026-07',
            })
            store.write({'state': 'connected'})
            setup_env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'sale_domain_enabled': True,
            })
            partner = setup_env['res.partner'].create({
                'name': 'Race Partner %s' % self.run_marker,
                'email': self.shared_email,
            })
            job_b = setup_env['shopify.connector.job'].create({
                'store_id': store.id, 'job_source': 'scheduled_sync',
                'job_type': 'customer_import_sync', 'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
                'shopify_target_gid': self.gid_b,
            })
            store_id, partner_id, job_b_id = store.id, partner.id, job_b.id
            setup_cr.commit()

            # --- Transaction A: create the first binding, hold uncommitted;
            #     record A's backend PID for the blocker-attribution proof ---
            cr_a = db_connect(dbname).cursor()
            cr_a.execute('SELECT pg_backend_pid()')
            a_pid = cr_a.fetchone()[0]
            env_a = api.Environment(cr_a, SUPERUSER_ID, {})
            payload_a = {
                'gid': self.gid_a, 'first_name': None, 'last_name': None,
                'display_name': 'Race A', 'email': self.shared_email,
                'phone': None, 'address': None,
            }
            env_a['shopify.connector.customer.importer']._apply_import(
                env_a['shopify.connector.store'].browse(store_id), payload_a)
            env_a.flush_all()  # force the INSERT so the unique row is held

            # --- Transaction B: the worker OWNS its cursor start-to-finish ---
            def run_b():
                started_evt.set()
                cr_w = None
                try:
                    cr_w = db_connect(dbname).cursor()
                    cr_w.execute('SELECT pg_backend_pid()')
                    pid_queue.put(cr_w.fetchone()[0])
                    env_w = api.Environment(cr_w, SUPERUSER_ID, {})
                    try:
                        with patch.object(client_cls, 'execute', fake_execute):
                            env_w['shopify.connector.job.dispatch']._dispatch_one(
                                env_w['shopify.connector.job'].browse(job_b_id))
                        cr_w.commit()          # commit the handled outcome
                        result['committed'] = True
                    except BaseException as exc:  # unexpected -> roll back
                        try:
                            cr_w.rollback()
                        except Exception:
                            pass
                        result['error'] = _sanitized_exception_diagnostic(exc)
                except BaseException as exc:   # cursor/setup failure
                    result['setup_error'] = _sanitized_exception_diagnostic(exc)
                finally:
                    if cr_w is not None:
                        try:
                            cr_w.close()
                        except Exception:
                            pass
                    done_evt.set()

            worker = threading.Thread(
                target=run_b, name='race-B-%s' % self.run_marker)
            worker.start()

            # Bounded: worker reached its body.
            obs['worker_started'] = started_evt.wait(timeout=self.START_TIMEOUT)
            # Bounded: worker reported its backend PID.
            try:
                pid_b = pid_queue.get(timeout=self.PID_TIMEOUT)
            except queue.Empty:
                pid_b = None
            obs['pid_received'] = pid_b is not None

            # Bounded: B is blocked SPECIFICALLY BY A on the binding INSERT.
            monitor_cr = db_connect(dbname).cursor()
            if pid_b is not None:
                blocked_by_a, is_binding = self._wait_until_blocked_by(
                    monitor_cr, pid_b, a_pid, self.LOCK_WAIT_TIMEOUT)
            else:
                blocked_by_a, is_binding = False, False
            obs['b_blocked_by_a'] = blocked_by_a
            obs['b_query_is_binding_path'] = is_binding

            # Release the barrier: commit A -> B's INSERT fails on uniqueness.
            cr_a.commit()

            # Bounded: prove the wait CLEARED after A committed.
            if pid_b is not None:
                obs['b_wait_cleared'] = self._wait_until_unblocked(
                    monitor_cr, pid_b, a_pid, self.LOCK_WAIT_TIMEOUT)
            else:
                obs['b_wait_cleared'] = False

            # Bounded join: the worker finishes and closes its own cursor.
            obs['worker_done'] = done_evt.wait(timeout=self.JOIN_TIMEOUT)
            worker.join(timeout=self.JOIN_TIMEOUT)
            obs['worker_alive_after_join'] = worker.is_alive()
            obs['worker_error'] = result.get('error') or result.get('setup_error')

            # --- first-collision route (fresh committed read) ---
            setup_cr.rollback()
            job_first = setup_env['shopify.connector.job'].browse(job_b_id)
            job_first.invalidate_recordset()
            obs['first_state'] = job_first.state
            obs['first_error_class'] = job_first.error_class
            obs['first_retry_count'] = job_first.retry_count
            obs['first_next_retry_at'] = bool(job_first.next_retry_at)
            JobLog = setup_env['shopify.connector.job.log']
            obs['first_attempt_logs'] = JobLog.search_count([
                ('job_id', '=', job_b_id), ('event_type', '=', 'attempt'),
                ('to_state', '=', 'running')])
            obs['first_retry_logs'] = JobLog.search_count([
                ('job_id', '=', job_b_id), ('event_type', '=', 'state_change'),
                ('to_state', '=', 'retry_waiting')])

            # --- forced clean-transaction retry (direct _dispatch_one, NOT
            #     the scheduler's due-time selection): A's binding is now
            #     committed & visible on cr_a ---
            env_r = api.Environment(cr_a, SUPERUSER_ID, {})
            job_r = env_r['shopify.connector.job'].browse(job_b_id)
            job_r.invalidate_recordset()
            with patch.object(client_cls, 'execute', fake_execute):
                env_r['shopify.connector.job.dispatch']._dispatch_one(job_r)
            cr_a.commit()
            setup_cr.rollback()
            job_retry = setup_env['shopify.connector.job'].browse(job_b_id)
            job_retry.invalidate_recordset()
            obs['retry_state'] = job_retry.state
            obs['retry_subreason'] = job_retry.manual_review_subreason
            obs['retry_manual_logs'] = JobLog.search_count([
                ('job_id', '=', job_b_id), ('event_type', '=', 'state_change'),
                ('to_state', '=', 'blocked_manual_review')])

            # --- final invariants ---
            bindings = setup_env['shopify.connector.customer.binding'].search(
                [('store_id', '=', store_id), ('partner_id', '=', partner_id)])
            obs['binding_count'] = len(bindings)
            obs['surviving_gid'] = bindings.shopify_gid if len(bindings) == 1 else None
            obs['partner_count'] = setup_env['res.partner'].with_context(
                active_test=False).search_count(
                [('shopify_connector_email_normalized', '=', self.shared_email)])
        finally:
            # 1. Ensure the worker has exited before touching cleanup. If it
            #    is still alive, release the lock barrier so its INSERT fails
            #    out (it then rolls back & closes its OWN cursor), then wait
            #    once more with a bounded emergency timeout -- never unbounded.
            if worker is not None and worker.is_alive():
                if cr_a is not None:
                    try:
                        cr_a.rollback()
                    except Exception:
                        pass
                done_evt.wait(timeout=self.EMERGENCY_TIMEOUT)
                worker.join(timeout=self.EMERGENCY_TIMEOUT)
            obs['worker_alive_final'] = bool(
                worker is not None and worker.is_alive())

            # 2. Roll back / close every parent-owned cursor BEFORE cleanup so
            #    no held lock can block the cleanup transaction.
            for cr in (cr_a, monitor_cr, setup_cr):
                if cr is not None:
                    try:
                        cr.rollback()
                    except Exception:
                        pass
                    try:
                        cr.close()
                    except Exception:
                        pass

            # 3. Durable cleanup + verification on FRESH connections -- only
            #    when the worker is confirmed gone (a lingering lock could
            #    otherwise block cleanup; fail closed instead). Cleanup never
            #    swallows a failure.
            obs['cleanup_error'] = None
            obs['cleanup_remaining'] = None
            if store_id is not None and not obs['worker_alive_final']:
                try:
                    self._durable_cleanup(dbname, store_id, partner_id, job_b_id)
                    obs['cleanup_remaining'] = self._verify_cleanup(
                        dbname, store_id, partner_id, job_b_id)
                except Exception as exc:  # noqa: BLE001 - recorded & asserted
                    obs['cleanup_error'] = _sanitized_exception_diagnostic(exc)

        # ------------------------------------------------------------------
        # Assertions run AFTER cleanup so a failing assert never leaks rows.
        # ------------------------------------------------------------------
        # Thread-safety / liveness.
        self.assertTrue(obs.get('worker_started'), 'worker thread never started')
        self.assertTrue(obs.get('pid_received'), 'worker never reported its PID')
        self.assertTrue(
            obs.get('worker_done'),
            'worker did not finish within the bounded join timeout')
        self.assertFalse(
            obs.get('worker_alive_final'),
            'worker still alive after the emergency join -- inconclusive, '
            'not passing')
        self.assertIsNone(
            obs.get('worker_error'),
            'the racing worker raised unexpectedly: %s' % obs.get('worker_error'))
        # Attributed lock-wait proof (not a bare "some lock" wait).
        self.assertTrue(
            obs.get('b_blocked_by_a'),
            'B was never blocked specifically by A (pg_blocking_pids(B) never '
            'contained A) -- the intended uniqueness race did not occur; '
            'inconclusive')
        self.assertTrue(
            obs.get('b_query_is_binding_path'),
            "B's blocked statement was not the customer-binding INSERT -- the "
            'observed wait is not the intended race')
        self.assertTrue(
            obs.get('b_wait_cleared'),
            "B's lock wait did not clear after A committed")
        # First collision -> safety-net retry (complete route), NOT a direct
        # binding_conflict.
        self.assertEqual(obs['first_state'], 'retry_waiting')
        self.assertEqual(obs['first_error_class'], 'unknown_system_error')
        self.assertEqual(obs['first_retry_count'], 1)
        self.assertTrue(
            obs['first_next_retry_at'],
            'next_retry_at must be populated on the retry schedule')
        self.assertGreaterEqual(
            obs['first_attempt_logs'], 1, 'a dispatch-attempt log must exist')
        self.assertGreaterEqual(
            obs['first_retry_logs'], 1,
            'a retry_waiting state-change log must exist')
        # Forced clean-transaction retry -> stable manual-review outcome.
        self.assertEqual(obs['retry_state'], 'blocked_manual_review')
        self.assertEqual(obs['retry_subreason'], 'binding_conflict')
        self.assertGreaterEqual(
            obs['retry_manual_logs'], 1,
            'a blocked_manual_review state-change log must exist')
        # Exactly one binding survives (first GID); no duplicate partner.
        self.assertEqual(obs['binding_count'], 1)
        self.assertEqual(obs['surviving_gid'], self.gid_a)
        self.assertEqual(obs['partner_count'], 1)
        # Cleanup actually ran and verifiably removed every synthetic row.
        self.assertIsNone(
            obs['cleanup_error'],
            'durable cleanup failed: %s' % obs['cleanup_error'])
        self.assertEqual(
            obs['cleanup_remaining'],
            {'logs': 0, 'jobs': 0, 'bindings': 0, 'settings': 0,
             'partner': 0, 'store': 0},
            'synthetic rows remained after cleanup: %s'
            % (obs['cleanup_remaining'],))
