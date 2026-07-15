"""Task 011B -- customer matching scalability (indexed normalized lookup).

Proves the indexed candidate lookup added by Task 011B is recall-
equivalent to the merged O(n) full scan it replaces, that every Task 011
routing outcome is unchanged, that duplicate/ambiguity behaviour is
preserved, and that the source-level guards (indexed domain, identical
`email_normalize(strict=False)` on both sides, no new match key) hold.

Several `-standard`-excluded classes carry the runtime-only work; none run
in the standard CI pass, each is invocable under an explicit test tag on a
runtime host:

  * `TestCustomerMatchingConcurrency` (D-011B-6, a genuine independent-
    transaction binding race through the real dispatcher) and
    `TestCustomerMatchingBenchmark` (D-011B-7, the deterministic 100k
    performance harness) -- tags
    `shopify_connector_customer_matching_concurrency` /
    `shopify_connector_customer_matching_benchmark`.
  * The CORE-R2 Slice 2B genuine independent-connection customer call-site
    lifecycle proofs, all tagged
    `shopify_connector_customer_callsite_lifecycle`:
      - `TestCustomerCallsiteLeaseVisibilityGenuine` -- M1/M2 committed-lease
        visibility (single-threaded M1; threaded paused-reconciliation M2);
      - `TestCustomerCallsiteRaceAGenuine` -- Race A / M8 admission-vs-
        disconnect ordering, both orderings (single-threaded);
      - `TestCustomerCallsiteRaceBGenuine` -- Race B / M18: the PRIMARY
        lease-count proof (the controller genuinely locks the store, observes
        the open lease, transitions to `quiescing` without finalizing, then
        finalizes after release) PLUS the retained binding-key-share
        `FOR UPDATE SKIP LOCKED` lock-skip coverage (both threaded).

All genuine lifecycle classes use real `db_connect` PostgreSQL connections
(bounded, distinct backend PIDs). Only `_send` is the transport seam and a
domain `_apply_import` observe-and-delegate wrapper is the reconciliation
synchronization barrier; production lifecycle/state is never monkeypatched.
"""

import ast
import contextlib
import json
import logging
import os
import queue
import threading
import time
import uuid
from time import perf_counter
from unittest.mock import patch

import psycopg2

from odoo import SUPERUSER_ID, api
import odoo.service.model as service_model
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import email_normalize, mute_logger

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.tools.redaction import redact


# Reserved-TLD, connector-unique domains so corpus/routing fixtures never
# collide with base/demo partners already present in the test database.
CORPUS_DOMAIN = 'corpus011b.example'
ROUTE_DOMAIN = 't011b.example'

# PostgreSQL table backing shopify.connector.customer.binding.
BINDING_TABLE = 'shopify_connector_customer_binding'

# Server-side, case-insensitive, quote-tolerant POSIX regex proving the active
# statement is specifically the customer-binding INSERT -- NOT a SELECT/UPDATE/
# DELETE and NOT an unrelated mention of the table in a comment or a different
# statement. Evaluated entirely inside PostgreSQL via `query ~* <regex>`; only
# the resulting boolean is returned to Python, so the raw active-query text
# (which carries the email VALUES of the row being inserted) never enters
# Python, an assertion message, or the committed documentation.
BINDING_INSERT_QUERY_REGEX = (
    r'insert\s+into\s+"?' + BINDING_TABLE + r'"?'
)

# CORE-R2 Slice 2B: the customer importer now issues its one Shopify Admin
# call through the admission-gated `execute_business` lease, so `_admit`
# reads a credential and checks the connection generation. A non-secret
# placeholder token lets the real admission gate pass; the transport is
# always the injected `_send` seam, so it never reaches a network call.
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _RaceFakeResponse:
    """Minimal stand-in for a `requests.Response` for the `_send()`
    transport-injection seam (no network call). `execute_business`'s
    `_normalize_response` turns this `{'data': ...}` body into the
    normalized dict the importer's `_normalize_payload` consumes."""

    def __init__(self, status_code, json_body=None, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_body = json_body
        self.text = json.dumps(json_body) if json_body is not None else ''

    def json(self):
        return self._json_body


def _sanitized_exception_diagnostic(exc):
    """Type-only, data-free diagnostic for an exception surfaced from a
    benchmark/concurrency helper.

    NEVER includes ``str(exc)``/``repr(exc)``: a psycopg2/DB error routinely
    embeds partner emails, SQL ``VALUES``, connection paths, or access tokens
    in its message. This emits only the exception class name plus a fixed
    generic sentence, then runs the result through the connector redaction
    helper as defence in depth. The harness **catches and suppresses** the
    exception payload -- it fails loudly (the caller records this diagnostic
    and asserts on it) but only the sanitized, type-only diagnostic is
    guaranteed; the harness makes no claim to preserve an unredacted trace
    anywhere."""
    return redact(
        '%s (payload suppressed to avoid leaking partner/SQL/credential '
        'data; only this sanitized, type-only diagnostic is retained)'
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
        # The corrected wording no longer claims an unredacted trace survives.
        self.assertNotIn('runtime host log', diagnostic)

    # ==================================================================
    # Binding-INSERT evidence predicate (standard CI). Evaluates the exact
    # server-side regex the concurrency monitor uses (`query ~* <rx>`)
    # against literal sample statements, proving it matches ONLY an
    # INSERT INTO the binding table -- never a SELECT/UPDATE/DELETE, and
    # never a bare mention of the table in a comment or another statement.
    # ==================================================================

    def test_binding_insert_predicate_matches_only_inserts(self):
        cases = [
            # (sample statement, expected predicate result)
            ('INSERT INTO "shopify_connector_customer_binding" '
             '(store_id, partner_id) VALUES (1, 2)', True),
            ('insert into shopify_connector_customer_binding (a) values (1)',
             True),
            ('INSERT   INTO\n  "shopify_connector_customer_binding" DEFAULT '
             'VALUES', True),
            ('SELECT id FROM shopify_connector_customer_binding WHERE id = 1',
             False),
            ('UPDATE shopify_connector_customer_binding SET partner_id = 2',
             False),
            ('DELETE FROM shopify_connector_customer_binding WHERE id = 1',
             False),
            ('SELECT 1  -- touches shopify_connector_customer_binding in a note',
             False),
            ('INSERT INTO some_other_table (note) VALUES '
             "('shopify_connector_customer_binding')", False),
        ]
        for statement, expected in cases:
            self.env.cr.execute(
                'SELECT %s ~* %s', (statement, BINDING_INSERT_QUERY_REGEX))
            actual = self.env.cr.fetchone()[0]
            # The sample statements are synthetic literals (no real data), so
            # echoing which case failed leaks nothing.
            self.assertEqual(
                actual, expected,
                'binding-INSERT predicate misclassified a %r statement'
                % statement.split()[0])


# `-at_install` is REQUIRED, not cosmetic: Odoo's `tagged` unions onto the
# inherited default `{'standard', 'at_install'}` (odoo/tests/common.py
# `BaseCase.__init_subclass__`, 19.0), so without removing `at_install` this
# class would carry BOTH `at_install` and `post_install` and trip the decorator's
# "should be either at_install or post_install" warning (`not (at_install ^
# post_install)`). Removing it leaves exactly `{post_install, <custom tag>}`:
# post_install-only, `-standard` (never in ordinary CI), deliberately invocable
# by the custom tag.
@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_customer_matching_benchmark')
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


# `-at_install` is REQUIRED (see the note on TestCustomerMatchingBenchmark):
# it removes the inherited default `at_install` so the effective tag set is
# exactly `{post_install, <custom tag>}` — post_install-only, `-standard`
# (excluded from ordinary CI), invocable deliberately by the custom tag, and no
# longer tripping the decorator's at_install-XOR-post_install warning.
@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_customer_matching_concurrency')
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

    Execution-safety design (control-room reviews 4950353232, 4951165587):

      * Worker-owned, daemonized cursor -- the worker thread itself calls
        ``db_connect(dbname).cursor()``, reports its backend PID to the
        parent through a ``queue.Queue``, builds its own ``Environment``,
        runs the real dispatcher, commits on the handled outcome, rolls
        back on an unexpected exception, and closes its cursor in its own
        ``finally``. No Odoo cursor or ``Environment`` ever crosses the
        thread boundary; parent<->worker signalling is
        ``threading.Event``/``queue.Queue`` only. The thread is created
        ``daemon=True`` purely as a last-resort process-liveness guard so a
        wedged worker can never keep the Python/Odoo process alive after the
        test fails -- it is NOT a substitute for the explicit cursor
        rollback/close, the emergency barrier release, or the durable row
        cleanup, all of which still run and are still asserted.
      * Attributed lock-wait proof -- synchronization does not accept "B is
        waiting on some lock", nor even "B's query mentions the binding
        table". It requires ``A_PID IN pg_blocking_pids(B)`` AND that B's
        active statement matches a server-side ``INSERT INTO`` +
        binding-table regex (``query ~* BINDING_INSERT_QUERY_REGEX``, case/
        quote tolerant) -- so a SELECT/UPDATE/DELETE of, or a mere mention
        of, the table cannot satisfy it. Only the resulting boolean crosses
        into Python; the raw query text (which carries the row's email
        VALUES) is never read into Python. It also proves the wait CLEARS
        once A commits.
      * Bounded everything -- worker-start, PID-received, lock-wait and
        join are all bounded; on a stuck worker the test releases the lock
        barrier, waits once more with a bounded emergency timeout, and
        fails closed rather than hanging. Both the cleanup and verification
        connections apply transaction-local PostgreSQL ``lock_timeout`` and
        ``statement_timeout`` (``CLEANUP_*_TIMEOUT_MS``) before any ORM work,
        so a leaked/competing lock cannot hang cleanup either.
      * Durable cleanup + verification -- all independent cursors are
        rolled back/closed BEFORE a fresh cleanup connection deletes every
        synthetic row (FK-safe order); cleanup never swallows a failure and
        re-raises it (the caller records a sanitized, type-only diagnostic
        and asserts it is absent); best-effort emergency cursor rollback/
        close failures are likewise captured (sanitized) and asserted empty;
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
    # Transaction-local PostgreSQL bounds (milliseconds) applied to the fresh
    # cleanup + verification connections before any ORM work, so a leaked or
    # competing lock can never hang cleanup. Finite and conservative.
    CLEANUP_LOCK_TIMEOUT_MS = 5000
    CLEANUP_STATEMENT_TIMEOUT_MS = 15000

    def setUp(self):
        super().setUp()
        # Per-run marker so repeated runs never collide on the shared email,
        # the target GIDs, or the cleanup-verification predicate.
        marker = uuid.uuid4().hex[:12]
        self.run_marker = marker
        self.shared_email = 'race-%s@concurrency011b.example' % marker
        self.gid_a = 'gid://shopify/Customer/race-A-%s' % marker
        self.gid_b = 'gid://shopify/Customer/race-B-%s' % marker

    def _fake_send(self):
        """CORE-R2 Slice 2B: replace the `_send` transport seam (not the
        removed `execute`) so the REAL admission-gated `execute_business`
        context manager, `_admit`, and the committed lease all run through
        the race. Returns a 200 `_RaceFakeResponse` whose body
        `_normalize_response` turns into the Race-B customer payload the
        importer then reconciles (the colliding binding INSERT)."""
        email = self.shared_email

        def fake_send(client_self, store, body, token=None):
            gid = ((body or {}).get('variables') or {}).get('id')
            return _RaceFakeResponse(200, json_body={'data': {'customer': {
                'id': gid,
                'firstName': 'Race', 'lastName': 'B', 'displayName': 'Race B',
                'defaultEmailAddress': {'emailAddress': email},
                'defaultPhoneNumber': None, 'defaultAddress': None,
                'updatedAt': '2026-07-12T00:00:00Z',
            }}})
        return fake_send

    # ------------------------------------------------------------------
    # Deterministic, ATTRIBUTED lock-wait synchronization. Evidence is
    # computed server-side and returned as booleans only -- the raw
    # pg_stat_activity.query (which carries the email VALUES of the row
    # being inserted) is never read into Python or an assertion message.
    # ------------------------------------------------------------------

    def _blocking_evidence(self, monitor_cr, waiter_pid, blocker_pid):
        """Return (blocked_by_blocker, query_is_binding_insert) as booleans
        computed ENTIRELY inside PostgreSQL. `query_is_binding_insert` is
        ``query ~* BINDING_INSERT_QUERY_REGEX`` -- true only for an
        ``INSERT INTO`` of the binding table, never a SELECT/UPDATE/DELETE
        or a bare mention. The raw ``query`` text is never selected out, so
        the row's email VALUES never reach Python."""
        monitor_cr.execute(
            'SELECT '
            '  %(blocker)s = ANY(pg_blocking_pids(%(waiter)s)) AS blocked_by, '
            '  COALESCE(query ~* %(rx)s, FALSE) AS is_binding_insert '
            'FROM pg_stat_activity WHERE pid = %(waiter)s',
            {'blocker': blocker_pid, 'waiter': waiter_pid,
             'rx': BINDING_INSERT_QUERY_REGEX})
        row = monitor_cr.fetchone()
        monitor_cr.rollback()
        if not row:
            return False, False
        return bool(row[0]), bool(row[1])

    def _wait_until_blocked_by(self, monitor_cr, waiter_pid, blocker_pid, timeout):
        """Poll until `waiter_pid` is lock-blocked SPECIFICALLY BY
        `blocker_pid` AND its active statement is the binding ``INSERT``.
        Returns (blocked_by_blocker, query_is_binding_insert): the success
        condition requires BOTH -- a bare lock wait, a block that is not the
        INSERT, or a non-INSERT statement referencing the table are all
        rejected. On timeout the last-observed booleans are returned so the
        caller's assertions fail with the specific unmet condition."""
        deadline = time.monotonic() + timeout
        last_blocked = last_insert = False
        while time.monotonic() < deadline:
            blocked_by, is_binding_insert = self._blocking_evidence(
                monitor_cr, waiter_pid, blocker_pid)
            last_blocked, last_insert = blocked_by, is_binding_insert
            if blocked_by and is_binding_insert:
                return True, True
            time.sleep(0.05)
        return last_blocked, last_insert

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

    def _apply_cleanup_bounds(self, cr):
        """Apply transaction-local PostgreSQL ``lock_timeout`` and
        ``statement_timeout`` to `cr` BEFORE any ORM work.

        ``set_config(..., is_local => true)`` scopes both bounds to the
        current transaction only (never leaking to another user of a pooled
        connection). With these set, a delete/search that blocks on a leaked
        or competing lock is cancelled by PostgreSQL (``LockNotAvailable`` /
        ``QueryCanceled``) instead of hanging forever -- the caller's
        ``except`` then rolls back, closes, records a sanitized diagnostic,
        and fails the test."""
        cr.execute(
            "SELECT set_config('lock_timeout', %s, true), "
            "set_config('statement_timeout', %s, true)",
            (str(self.CLEANUP_LOCK_TIMEOUT_MS),
             str(self.CLEANUP_STATEMENT_TIMEOUT_MS)))

    def _durable_cleanup(self, dbname, store_id, partner_id, job_id):
        """Delete every committed synthetic row in FK-safe order on a FRESH,
        time-bounded connection. Re-raises on any failure (incl. a lock/
        statement timeout) -- the caller records and asserts the outcome; a
        cleanup failure must never pass silently."""
        cr = db_connect(dbname).cursor()
        try:
            self._apply_cleanup_bounds(cr)
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.job.log'].search(
                [('job_id', '=', job_id)]).unlink()
            # CORE-R2 Slice 2B: execute_business releases its lease on both the
            # collision (exception) and forced-retry paths, so none should
            # remain -- but sweep any residue (e.g. a killed worker) before the
            # job/store FK targets are removed, since the lease references both.
            env['shopify.connector.call.lease'].search(
                [('store_id', '=', store_id)]).unlink()
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
        """On a second FRESH, time-bounded connection, count every synthetic
        row that should now be gone. Returns a dict of remaining counts (all
        must be zero). Re-raises on any failure (incl. a lock/statement
        timeout) so verification can never hang or pass silently."""
        cr = db_connect(dbname).cursor()
        try:
            self._apply_cleanup_bounds(cr)
            env = api.Environment(cr, SUPERUSER_ID, {})
            remaining = {
                'logs': env['shopify.connector.job.log'].search_count(
                    [('job_id', '=', job_id)]),
                'jobs': len(env['shopify.connector.job'].browse(job_id).exists()),
                # CORE-R2 review 4695664662 #4: the verification map now counts
                # leases too, so a lease that outlived its context (a release
                # regression) is a verified nonzero rather than an unchecked gap.
                'leases': env['shopify.connector.call.lease'].search_count(
                    [('store_id', '=', store_id)]),
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
        except Exception:
            cr.rollback()
            raise
        finally:
            cr.close()

    def _independent_lease_count(self, dbname, store_id):
        """Count committed leases for the store on a FRESH, time-bounded
        connection BEFORE any cleanup runs (CORE-R2 review 4695664662 #4).

        This is the fail-loud release-regression check: it captures the lease
        residue as evidence *before* `_durable_cleanup` sweeps leases, so the
        cleanup's own lease deletion can never turn a context that failed to
        release its lease into a passing test. Re-raises on any failure so it
        cannot silently pass."""
        cr = db_connect(dbname).cursor()
        try:
            self._apply_cleanup_bounds(cr)
            env = api.Environment(cr, SUPERUSER_ID, {})
            count = env['shopify.connector.call.lease'].search_count(
                [('store_id', '=', store_id)])
            cr.rollback()
            return count
        except Exception:
            cr.rollback()
            raise
        finally:
            cr.close()

    @mute_logger('odoo.sql_db', 'odoo.addons.shopify_connector_core')
    def test_genuine_independent_transaction_binding_race(self):
        dbname = self.env.cr.dbname
        client_cls = type(self.env['shopify.connector.api.client'])
        fake_send = self._fake_send()

        obs = {}
        setup_cr = cr_a = monitor_cr = None
        store_id = partner_id = job_b_id = None
        worker = None
        # Thread-safe comms only -- no Odoo cursor/Environment crosses over.
        started_evt = threading.Event()
        done_evt = threading.Event()
        pid_queue = queue.Queue()
        # Bounded, sanitized worker phase evidence: phase identifiers and
        # exception CLASS names ONLY -- never raw SQL/email/payload/token/exc
        # text. Lets a future failure pinpoint exactly how far the worker got
        # (e.g. a stall at `before_api_environment` = the Registry._lock
        # post_install deadlock, CORE-R2 §4.2 / review 4687443143).
        phase_queue = queue.Queue()
        obs['worker_phases'] = []

        def _drain_phases():
            while True:
                try:
                    obs['worker_phases'].append(phase_queue.get_nowait())
                except queue.Empty:
                    break

        result = {}
        # --- Framework-lock decoupling for the SPAWNED worker (CORE-R2 §4.2 /
        #     review 4687443143). Odoo's ThreadedServer.run() holds the reentrant
        #     Registry._lock across the ENTIRE preload/post_install phase
        #     (service/server.py), so the worker's api.Environment(cr_w, ...) ->
        #     Registry(cr.dbname) -> Registry.__new__ -> `with cls._lock:` blocks
        #     forever on a lock a different thread can never acquire (proven by the
        #     diagnostic: the worker stalls at `before_api_environment`). A fresh
        #     RLock for the bounded worker window lets the worker build its
        #     Environment while PRESERVING (a) real mutual exclusion -- the registry
        #     is fully built and only READ here (a cached registries[db] lookup,
        #     never a rebuild), the same decoupling Odoo's own
        #     _registry_test_mode_patches performs -- and (b) real INDEPENDENT
        #     PostgreSQL connections (every cursor stays an unchanged
        #     db_connect(dbname).cursor(); no TestCursor, no shared connection). The
        #     `with cls._lock:` in Registry.__new__ releases the SAME object it
        #     acquired, so restoring the class attribute below is safe even if the
        #     worker is mid-Environment. Restored in `finally` once the worker has
        #     terminated and closed its own cursor.
        registry_cls = type(self.registry)
        saved_registry_lock = registry_cls._lock
        registry_cls._lock = threading.RLock()
        try:
            # --- committed setup on an independent connection ---
            setup_cr = db_connect(dbname).cursor()
            setup_env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = setup_env['shopify.connector.store'].create({
                'name': 'Race Store %s' % self.run_marker,
                'shop_domain': 'race-%s.myshopify.com' % self.run_marker,
                'api_version': '2026-07',
                'state': 'connected',
            })
            # CORE-R2 Slice 2B: the importer now issues its Shopify call
            # through the admission-gated execute_business lease, so worker B's
            # _admit reads a credential and checks the connection generation.
            # Provision a (non-secret placeholder) credential and re-assert
            # connected (action_set_token demotes + bumps the generation), and
            # capture the job's expected generation from the committed store so
            # admission matches.
            setup_env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
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
                'expected_connection_generation': store.connection_generation,
            })
            store_id, partner_id, job_b_id = store.id, partner.id, job_b.id
            setup_cr.commit()

            # --- Transaction A: create the first binding, hold uncommitted;
            #     record A's backend PID for the blocker-attribution proof ---
            cr_a = db_connect(dbname).cursor()
            cr_a.execute('SELECT pg_backend_pid()')
            a_pid = cr_a.fetchone()[0]
            obs['a_backend_pid'] = a_pid
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
                phase_queue.put('worker_thread_entered')
                started_evt.set()
                cr_w = None
                try:
                    cr_w = db_connect(dbname).cursor()
                    phase_queue.put('cursor_opened')
                    cr_w.execute('SELECT pg_backend_pid()')
                    pid_queue.put(cr_w.fetchone()[0])
                    phase_queue.put('backend_pid_obtained')
                    # The spawned worker builds its OWN Environment here. Without
                    # the parent's bounded-window Registry._lock decoupling this
                    # call blocks forever on the main-thread-held reentrant
                    # Registry._lock (CORE-R2 §4.2): a stall whose LAST phase is
                    # `before_api_environment` is exactly that framework deadlock.
                    phase_queue.put('before_api_environment')
                    env_w = api.Environment(cr_w, SUPERUSER_ID, {})
                    phase_queue.put('after_api_environment')
                    try:
                        with patch.object(client_cls, '_send', fake_send):
                            phase_queue.put('before_dispatch')
                            env_w['shopify.connector.job.dispatch']._dispatch_one(
                                env_w['shopify.connector.job'].browse(job_b_id))
                            phase_queue.put('after_dispatch')
                        phase_queue.put('before_commit')
                        cr_w.commit()          # commit the handled outcome
                        phase_queue.put('after_commit')
                        result['committed'] = True
                    except BaseException as exc:  # unexpected -> roll back
                        phase_queue.put('worker_body_exc:%s' % type(exc).__name__)
                        try:
                            cr_w.rollback()
                        except Exception:
                            pass
                        result['error'] = _sanitized_exception_diagnostic(exc)
                except BaseException as exc:   # cursor/setup failure
                    phase_queue.put('worker_setup_exc:%s' % type(exc).__name__)
                    result['setup_error'] = _sanitized_exception_diagnostic(exc)
                finally:
                    phase_queue.put('worker_finally_entered')
                    if cr_w is not None:
                        try:
                            cr_w.close()
                        except Exception:
                            pass
                    phase_queue.put('cursor_closed')
                    # Put the terminal phase BEFORE signalling done, so the parent
                    # observes a complete trail the moment done_evt fires.
                    phase_queue.put('worker_done')
                    done_evt.set()

            # daemon=True is a LAST-RESORT process-liveness guard only: if the
            # emergency rollback + bounded joins below cannot stop a wedged
            # worker, daemonization stops it from keeping the Python/Odoo
            # process alive after the test fails. It never substitutes for the
            # worker's own cursor rollback/close or the durable row cleanup,
            # which still run and are still asserted.
            worker = threading.Thread(
                target=run_b, name='race-B-%s' % self.run_marker, daemon=True)
            worker.start()

            # Bounded: worker reached its body.
            obs['worker_started'] = started_evt.wait(timeout=self.START_TIMEOUT)
            # Bounded: worker reported its backend PID.
            try:
                pid_b = pid_queue.get(timeout=self.PID_TIMEOUT)
            except queue.Empty:
                pid_b = None
            obs['pid_received'] = pid_b is not None
            obs['b_backend_pid'] = pid_b
            obs['distinct_backend_pids'] = bool(
                pid_b is not None and pid_b != a_pid)

            # Bounded: B is blocked SPECIFICALLY BY A AND its active statement
            # is the binding INSERT (both required by _wait_until_blocked_by).
            monitor_cr = db_connect(dbname).cursor()
            if pid_b is not None:
                blocked_by_a, is_binding_insert = self._wait_until_blocked_by(
                    monitor_cr, pid_b, a_pid, self.LOCK_WAIT_TIMEOUT)
            else:
                blocked_by_a, is_binding_insert = False, False
            obs['b_blocked_by_a'] = blocked_by_a
            obs['b_query_is_binding_insert'] = is_binding_insert

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
            _drain_phases()
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
            with patch.object(client_cls, '_send', fake_send):
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
            # Best-effort emergency teardown must not silently swallow a
            # failure that would invalidate the cleanup claim: capture a
            # sanitized, type-only diagnostic for each and assert the list is
            # empty after cleanup (never str(exc)/repr(exc)).
            teardown_errors = []

            # 1. Ensure the worker has exited before touching cleanup. If it
            #    is still alive, release the lock barrier so its INSERT fails
            #    out (it then rolls back & closes its OWN cursor), then wait
            #    once more with a bounded emergency timeout -- never unbounded.
            if worker is not None and worker.is_alive():
                if cr_a is not None:
                    try:
                        cr_a.rollback()
                    except Exception as exc:  # noqa: BLE001 - recorded, asserted
                        teardown_errors.append(_sanitized_exception_diagnostic(exc))
                done_evt.wait(timeout=self.EMERGENCY_TIMEOUT)
                worker.join(timeout=self.EMERGENCY_TIMEOUT)
            obs['worker_alive_final'] = bool(
                worker is not None and worker.is_alive())
            _drain_phases()
            obs['last_worker_phase'] = (
                obs['worker_phases'][-1] if obs['worker_phases'] else None)

            # 2. Roll back / close every parent-owned cursor BEFORE cleanup so
            #    no held lock can block the cleanup transaction.
            for cr in (cr_a, monitor_cr, setup_cr):
                if cr is not None:
                    try:
                        cr.rollback()
                    except Exception as exc:  # noqa: BLE001 - recorded, asserted
                        teardown_errors.append(_sanitized_exception_diagnostic(exc))
                    try:
                        cr.close()
                    except Exception as exc:  # noqa: BLE001 - recorded, asserted
                        teardown_errors.append(_sanitized_exception_diagnostic(exc))
            obs['cursor_teardown_errors'] = teardown_errors

            # Restore the framework Registry._lock now that the worker has
            # terminated (steps 1-2) and every worker-owned cursor is closed. The
            # durable cleanup below runs on the MAIN thread, which reacquires the
            # original reentrant lock it already holds -- so restoring before
            # cleanup keeps the patched window as narrow as possible and is safe.
            registry_cls._lock = saved_registry_lock

            # 3. Durable cleanup + verification on FRESH connections -- only
            #    when the worker is confirmed gone (a lingering lock could
            #    otherwise block cleanup; fail closed instead). Cleanup never
            #    swallows a failure.
            obs['cleanup_error'] = None
            obs['cleanup_remaining'] = None
            obs['precleanup_lease_count'] = None
            if store_id is not None and not obs['worker_alive_final']:
                try:
                    # CORE-R2 review 4695664662 #4: capture the committed lease
                    # residue on an INDEPENDENT connection BEFORE the durable
                    # cleanup deletes anything, so a release regression is recorded
                    # as fail-loud evidence (asserted below) and the cleanup's own
                    # lease sweep can never convert it into a pass. Emergency
                    # deletion then runs only after this evidence is captured.
                    obs['precleanup_lease_count'] = self._independent_lease_count(
                        dbname, store_id)
                    self._durable_cleanup(dbname, store_id, partner_id, job_b_id)
                    obs['cleanup_remaining'] = self._verify_cleanup(
                        dbname, store_id, partner_id, job_b_id)
                except Exception as exc:  # noqa: BLE001 - recorded & asserted
                    obs['cleanup_error'] = _sanitized_exception_diagnostic(exc)

        # ------------------------------------------------------------------
        # Assertions run AFTER cleanup so a failing assert never leaks rows.
        # ------------------------------------------------------------------
        # Concise, sanitized phase trail -- phase identifiers + exception class
        # names only. Retained (not debug noise) because it pinpoints how far the
        # worker got on any future regression (e.g. a `before_api_environment`
        # tail = the Registry._lock post_install deadlock).
        phases = obs.get('worker_phases', [])
        print('[TASK-011B-CONCURRENCY] worker_phases=%s last=%s' % (
            phases, obs.get('last_worker_phase')))
        # Sanitized race evidence (booleans, backend PIDs as ints, routing states,
        # counts -- never any email/payload/token/SQL text).
        print('[TASK-011B-CONCURRENCY] race_evidence '
              'distinct_pids=%s a_pid=%s b_pid=%s blocked_by_a=%s '
              'binding_insert=%s wait_cleared=%s first=%s/%s/retry=%s '
              'retry=%s/%s bindings=%s partners=%s survivor_is_gid_a=%s '
              'cleanup=%s' % (
                  obs.get('distinct_backend_pids'), obs.get('a_backend_pid'),
                  obs.get('b_backend_pid'), obs.get('b_blocked_by_a'),
                  obs.get('b_query_is_binding_insert'), obs.get('b_wait_cleared'),
                  obs.get('first_state'), obs.get('first_error_class'),
                  obs.get('first_retry_count'), obs.get('retry_state'),
                  obs.get('retry_subreason'), obs.get('binding_count'),
                  obs.get('partner_count'),
                  obs.get('surviving_gid') == self.gid_a,
                  obs.get('cleanup_remaining')))
        # Thread-safety / liveness.
        self.assertTrue(obs.get('worker_started'),
                        'worker thread never started; phases=%s' % phases)
        self.assertTrue(obs.get('pid_received'),
                        'worker never reported its PID; phases=%s' % phases)
        # The worker must build its OWN Environment on the spawned thread and
        # reach the real dispatcher -- proving the Registry._lock post_install
        # deadlock (CORE-R2 §4.2) is decoupled for the bounded window.
        self.assertIn(
            'after_api_environment', phases,
            'worker never built its Environment on the spawned thread -- '
            'Registry._lock post_install deadlock (CORE-R2 §4.2) not decoupled; '
            'phases=%s' % phases)
        self.assertIn(
            'before_dispatch', phases,
            'worker never entered the real dispatcher; phases=%s' % phases)
        self.assertTrue(
            obs.get('worker_done'),
            'worker did not finish within the bounded join timeout; phases=%s'
            % phases)
        self.assertFalse(
            obs.get('worker_alive_final'),
            'worker still alive after the emergency join -- inconclusive, '
            'not passing; phases=%s' % phases)
        self.assertIsNone(
            obs.get('worker_error'),
            'the racing worker raised unexpectedly: %s' % obs.get('worker_error'))
        # Attributed lock-wait proof (not a bare "some lock" wait).
        self.assertTrue(
            obs.get('distinct_backend_pids'),
            'A and B must use distinct PostgreSQL backends (a_pid=%s b_pid=%s)'
            % (obs.get('a_backend_pid'), obs.get('b_backend_pid')))
        self.assertTrue(
            obs.get('b_blocked_by_a'),
            'B was never blocked specifically by A (pg_blocking_pids(B) never '
            'contained A) -- the intended uniqueness race did not occur; '
            'inconclusive')
        self.assertTrue(
            obs.get('b_query_is_binding_insert'),
            "B's blocked statement did not match the binding INSERT predicate "
            '-- a table mention / SELECT / UPDATE is not the intended race')
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
        # No emergency cursor teardown failure was silently swallowed.
        self.assertEqual(
            obs.get('cursor_teardown_errors'), [],
            'a parent-cursor rollback/close failed during teardown: %s'
            % (obs.get('cursor_teardown_errors'),))
        # Fail-loud release-regression check (CORE-R2 review 4695664662 #4):
        # every execute_business context in this race (the worker's collision
        # path and the forced-retry path) must release its lease, so an
        # INDEPENDENT connection must observe zero committed leases BEFORE the
        # durable cleanup runs. This is asserted from the pre-cleanup capture, so
        # the cleanup's own lease sweep cannot mask a lease that never released.
        self.assertEqual(
            obs.get('precleanup_lease_count'), 0,
            'a committed lease survived the admitted call before cleanup -- a '
            'release regression (independent pre-cleanup count: %s)'
            % (obs.get('precleanup_lease_count'),))
        # Cleanup actually ran (bounded) and verifiably removed every row.
        self.assertIsNone(
            obs['cleanup_error'],
            'durable cleanup failed (bounded lock/statement timeout or other): '
            '%s' % obs['cleanup_error'])
        self.assertEqual(
            obs['cleanup_remaining'],
            {'logs': 0, 'jobs': 0, 'leases': 0, 'bindings': 0, 'settings': 0,
             'partner': 0, 'store': 0},
            'synthetic rows remained after cleanup: %s'
            % (obs['cleanup_remaining'],))


# ======================================================================
# CORE-R2 Slice 2B -- GENUINE independent-connection customer call-site
# lifecycle proofs (control-room review 4695664662).
#
# These replace the earlier pre-admission-refusal tests that were
# mislabelled Race A. They use REAL `db_connect` PostgreSQL connections
# (never registry test mode), the REAL `execute_business`/`_admit`/
# `_release_lease` path, the REAL `action_disconnect` + admission lock
# protocol, and the REAL `_run_disconnect_quiesce` controller. Only `_send`
# is the transport injection seam; production lifecycle/state is never
# monkeypatched. Committed leases are observed cross-connection; the
# reconciliation pause is a genuine UNIQUE(store,partner) index wait (a
# second connection holds an uncommitted binding, then ROLLS BACK so the
# admitted call succeeds). Every connection is bounded (statement_timeout +
# lock_timeout), backends are proven distinct, worker threads are bounded +
# fail-loud, and teardown is durable with a zero-residue (incl. lease)
# verification.
#
# Tagged `-standard` (opt-in, runtime host) exactly like
# `TestCustomerMatchingConcurrency`: they require a genuine multi-connection
# PostgreSQL runtime and are authored here but executed on the runtime host,
# never in the standard unit pass (this session claims no runtime-green).
# ======================================================================
class _CustomerGenuineHelpers:
    """Shared genuine independent-connection helpers (mixin), mirroring the
    accepted core `_GenuineRaceHelpers`/`TestGenuineRealAdmission` pattern but
    for the customer domain. Raw SQL is used ONLY to commit fixtures, OBSERVE
    committed state, and clean up -- never to create the lease/binding under
    test."""

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    # --- bounded genuine connections -----------------------------------

    def _open_bounded(self, dbname, read_committed=False, lock_timeout_ms=None):
        cr = db_connect(dbname).cursor()
        try:
            if read_committed:
                cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            lt = self.LOCK_TIMEOUT_MS if lock_timeout_ms is None else lock_timeout_ms
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(lt)))
        except BaseException:
            cr.close()
            raise
        return cr

    def _backend_pid(self, cr):
        cr.execute("SELECT pg_backend_pid()")
        return cr.fetchone()[0]

    def _real_registry_cursor(self, dbname):
        """registry.cursor() replacement handing out bounded real pooled cursors,
        so the production `_admit`/`_release_lease` side transactions are
        genuinely independent AND time-bounded (never unbounded/hangable)."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    @staticmethod
    @contextlib.contextmanager
    def _instant_retry_backoff():
        """Make the REAL `odoo.service.model.retrying` loop's inter-try backoff
        instantaneous WITHOUT touching its retry decision or exception
        classification -- patch only the jitter (`random.uniform` -> 0.0) and the
        wait (`time.sleep` -> no-op), tolerant of the module's import form. If a
        hook is absent the only effect is one short real sleep -- still correct."""
        patches = []
        if hasattr(service_model, 'time') and hasattr(service_model.time, 'sleep'):
            patches.append(patch.object(service_model.time, 'sleep',
                                        lambda *a, **k: None))
        if hasattr(service_model, 'random') and hasattr(
                service_model.random, 'uniform'):
            patches.append(patch.object(service_model.random, 'uniform',
                                        lambda *a, **k: 0.0))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            yield

    @contextlib.contextmanager
    def _capture_service_retry(self):
        """Capture the dispatcher's concurrency-recovery log (and the legacy
        `odoo.service.model` retry log) so a genuine SQLSTATE 40001 -- never an
        injected exception -- that drove the corrected no-replay recovery can be
        evidenced. Process-global logging, so a record emitted from a worker
        thread is captured too. (The dispatcher no longer wraps the handler in
        `odoo.service.model.retrying`; the corrected per-job boundary logs the
        SQLSTATE itself from `shopify_connector_job_dispatch` before rolling back
        and reacquiring the job under a fresh row lock -- runtime correction,
        review `4699752673`.)"""
        records = []

        class _Capture(logging.Handler):
            def emit(self_handler, record):
                try:
                    records.append(record.getMessage())
                except Exception:
                    pass

        handler = _Capture()
        loggers = [logging.getLogger(name) for name in (
            'odoo.addons.shopify_connector_core.models.'
            'shopify_connector_job_dispatch',
            'odoo.service.model',
        )]
        prior = [(lg, lg.level) for lg in loggers]
        for lg in loggers:
            lg.setLevel(logging.DEBUG)
            lg.addHandler(handler)
        try:
            yield records
        finally:
            for lg, level in prior:
                lg.removeHandler(handler)
                lg.setLevel(level)

    def _sanitize(self, exc, phase):
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _drain(self, q):
        findings = []
        while True:
            try:
                findings.append(q.get_nowait())
            except queue.Empty:
                break
        return findings

    def _assert_workers_dead(self, threads):
        alive = sum(1 for t in threads if t is not None and t.is_alive())
        self.assertEqual(
            alive, 0, 'worker thread still alive at the cleanup boundary')

    # --- committed fixtures + a fake transport -------------------------

    def _fixture(self, dbname, marker):
        """Commit (independent bounded connection) a connected+credentialed
        store, its sale settings, a partner P carrying the incoming email (the
        single active match candidate), and one generation-matched
        customer_import_sync job. Returns an ids dict."""
        email = 'genuine-%s@callsitegenuine.example' % marker
        gid = 'gid://shopify/Customer/genuine-%s' % marker
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Callsite Store %s' % marker,
                'shop_domain': 'genuine-callsite-%s.myshopify.com' % marker,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed and bumps the
            # generation; re-assert connected so the business admission passes.
            store.write({'state': 'connected'})
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'sale_domain_enabled': True})
            partner = env['res.partner'].create({
                'name': 'Genuine Partner %s' % marker, 'email': email})
            job = env['shopify.connector.job'].create({
                'store_id': store.id, 'job_source': 'scheduled_sync',
                'job_type': 'customer_import_sync', 'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
                'shopify_target_gid': gid,
                'expected_connection_generation': store.connection_generation,
            })
            ids = {
                'store_id': store.id, 'partner_id': partner.id,
                'job_id': job.id, 'gid': gid, 'email': email,
            }
            setup.commit()
            return ids
        finally:
            setup.close()

    def _payload_body(self, ids):
        return {'data': {'customer': {
            'id': ids['gid'], 'firstName': 'Gen', 'lastName': 'Uine',
            'displayName': 'Genuine Customer',
            'defaultEmailAddress': {'emailAddress': ids['email']},
            'defaultPhoneNumber': None, 'defaultAddress': None,
            'updatedAt': '2026-07-12T00:00:00Z'}}}

    # --- committed-state observers (fresh connections) -----------------

    def _lease_count(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            n = obs.fetchone()[0]
            obs.rollback()
            return n
        finally:
            obs.close()

    def _lease_rows(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT lease_key, job_id FROM shopify_connector_call_lease "
                "WHERE store_id = %s ORDER BY lease_key", (store_id,))
            rows = obs.fetchall()
            obs.rollback()
            return rows
        finally:
            obs.close()

    def _observe_store(self, dbname, store_id):
        """(state, connection_generation, disconnect_status, credential_present)."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, connection_generation, disconnect_status, "
                "credential_present FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _observe_credential_token(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT access_token FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _observe_job_state(self, dbname, job_id):
        """The committed `state` of a job, observed on a fresh connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state FROM shopify_connector_job WHERE id = %s", (job_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _store_open_lease_count(self, dbname, store_id):
        """The controller-written `disconnect_open_lease_count` snapshot field on
        the store (distinct from the live COUNT(*) of lease rows): proves the
        controller reached the lease-count path and recorded the count it saw."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT disconnect_open_lease_count "
                "FROM shopify_connector_store WHERE id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _binding_count(self, dbname, store_id, gid=None):
        obs = self._open_bounded(dbname)
        try:
            if gid is None:
                obs.execute(
                    "SELECT count(*) FROM shopify_connector_customer_binding "
                    "WHERE store_id = %s", (store_id,))
            else:
                obs.execute(
                    "SELECT count(*) FROM shopify_connector_customer_binding "
                    "WHERE store_id = %s AND shopify_gid = %s", (store_id, gid))
            n = obs.fetchone()[0]
            obs.rollback()
            return n
        finally:
            obs.close()

    def _partner_count(self, dbname, normalized_email):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT count(*) FROM res_partner "
                "WHERE shopify_connector_email_normalized = %s",
                (normalized_email,))
            n = obs.fetchone()[0]
            obs.rollback()
            return n
        finally:
            obs.close()

    # --- attributed reconciliation-pause detection ---------------------

    def _blocked_by(self, monitor_cr, waiter_pid, blocker_pid):
        """(blocked_by_blocker, waiter_stmt_is_binding_insert) as booleans
        computed ENTIRELY inside PostgreSQL. Reuses the customer
        BINDING_INSERT_QUERY_REGEX so the waiter's parked statement is proven to
        be the binding INSERT (never a SELECT/UPDATE/DELETE); the raw query text
        (which carries the row's email VALUES) never enters Python."""
        monitor_cr.execute(
            'SELECT %(b)s = ANY(pg_blocking_pids(%(w)s)) AS blocked_by, '
            'COALESCE(query ~* %(rx)s, FALSE) AS is_binding_insert '
            'FROM pg_stat_activity WHERE pid = %(w)s',
            {'b': blocker_pid, 'w': waiter_pid,
             'rx': BINDING_INSERT_QUERY_REGEX})
        row = monitor_cr.fetchone()
        monitor_cr.rollback()
        if not row:
            return False, False
        return bool(row[0]), bool(row[1])

    def _wait_blocked(self, monitor_cr, waiter_pid, blocker_pid, timeout):
        deadline = time.monotonic() + timeout
        last = (False, False)
        while time.monotonic() < deadline:
            blk, ins = self._blocked_by(monitor_cr, waiter_pid, blocker_pid)
            last = (blk, ins)
            if blk and ins:
                return True, True
            time.sleep(0.05)
        return last

    def _hold_uncommitted_binding(self, dbname, ids, gid):
        """Open a bounded connection and hold an UNCOMMITTED binding for
        (store, partner) under a distinct GID, so the admitted worker's binding
        INSERT for the same (store, partner) blocks on UNIQUE(store, partner) --
        a genuine reconciliation pause. The caller rolls back + closes this
        cursor to release the pause so the worker's INSERT succeeds."""
        cr = self._open_bounded(dbname)
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.customer.binding'].create({
                'store_id': ids['store_id'], 'shopify_gid': gid,
                'partner_id': ids['partner_id'], 'match_key': 'manual',
            })
            # Materialize the INSERT (holds the unique-index entry) WITHOUT
            # committing -- the row is invisible to the worker's REPEATABLE READ
            # snapshot but its index entry still blocks the worker's INSERT.
            env.flush_all()
            return cr
        except BaseException:
            cr.rollback()
            cr.close()
            raise

    # --- test-owned cron-trigger ownership (review 4696393942 #2) ------
    #
    # `action_disconnect` and every quiescing controller pass schedule
    # `ir_cron_trigger` rows on the connector's disconnect-quiesce cron (and the
    # job path may schedule the drain cron). Those trigger rows carry no store_id,
    # so they cannot be scoped by store -- which is why the earlier cleanup
    # deleted EVERY trigger for those crons. That is globally destructive: a
    # pre-existing trigger from the base DB or a concurrent process would be
    # deleted too. Ownership is instead established by a per-test BASELINE:
    # `_trigger_baseline` snapshots the connector-cron trigger ids that exist
    # BEFORE the test; cleanup deletes ONLY the ids that appeared AFTER that
    # snapshot (`current - baseline`) -- exactly the rows this test created --
    # and `_assert_zero_residue` recomputes the same delta to prove none remain.
    # No baseline (pre-existing) id is ever in the delete set.

    _CONNECTOR_CRON_XMLIDS = (
        'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce',
        'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
    )

    def _connector_cron_ids(self, cr):
        """Resolve the connector cron record ids (`ir_cron.id`) from their xmlids
        on `cr`. A missing xmlid (stripped registry) is tolerated and omitted, so
        the trigger cleanup degrades to a no-op rather than failing."""
        env = api.Environment(cr, SUPERUSER_ID, {})
        ids = []
        for xmlid in self._CONNECTOR_CRON_XMLIDS:
            cron = env.ref(xmlid, raise_if_not_found=False)
            if cron:
                ids.append(cron.id)
        return ids

    def _trigger_baseline(self, dbname):
        """Snapshot (frozenset) the connector-cron `ir_cron_trigger` ids that
        exist BEFORE the test, establishing test ownership: any id NOT in this
        baseline is a trigger THIS test created and is the only kind cleanup may
        delete. Captured on a bounded, read-only (rolled-back) connection."""
        cr = self._open_bounded(dbname)
        try:
            cron_ids = self._connector_cron_ids(cr)
            if not cron_ids:
                cr.rollback()
                return frozenset()
            cr.execute(
                "SELECT id FROM ir_cron_trigger WHERE cron_id = ANY(%s)",
                (cron_ids,))
            baseline = frozenset(row[0] for row in cr.fetchall())
            cr.rollback()
            return baseline
        finally:
            cr.close()

    def _trigger_delta_ids(self, cr, baseline):
        """The connector-cron trigger ids created since `baseline` (the test-owned
        delta) on `cr` -- `sorted(current - baseline)`. By construction this never
        contains a baseline/pre-existing id, so a pre-existing trigger can never be
        deleted or reported as residue."""
        cron_ids = self._connector_cron_ids(cr)
        if not cron_ids:
            return []
        cr.execute(
            "SELECT id FROM ir_cron_trigger WHERE cron_id = ANY(%s)",
            (cron_ids,))
        current = frozenset(row[0] for row in cr.fetchall())
        return sorted(current - baseline)

    # --- durable, fail-loud teardown + zero-residue --------------------

    def _cleanup(self, dbname, ids, trigger_baseline):
        """Delete every committed row this test created, on a bounded connection,
        then assert zero residue. `trigger_baseline` is the pre-test connector-cron
        trigger snapshot: only the trigger ids created AFTER it (the test-owned
        delta) are deleted, so no pre-existing trigger is ever removed."""
        store_id = ids.get('store_id') if ids else None
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            # Scoped, test-owned cron-trigger cleanup: delete ONLY the connector-
            # cron trigger ids that appeared after the pre-test baseline -- never a
            # pre-existing trigger, never a whole-cron wipe.
            delta_ids = self._trigger_delta_ids(cr, trigger_baseline)
            if delta_ids:
                cr.execute(
                    "DELETE FROM ir_cron_trigger WHERE id = ANY(%s)", (delta_ids,))
            cr.execute(
                "DELETE FROM shopify_connector_job_log WHERE job_id IN "
                "(SELECT id FROM shopify_connector_job WHERE store_id = %s)",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_customer_binding "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_job WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_settings "
                "WHERE store_id = %s", (store_id,))
            if ids.get('partner_id'):
                cr.execute(
                    "DELETE FROM res_partner WHERE id = %s", (ids['partner_id'],))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        self._assert_zero_residue(dbname, ids, trigger_baseline)

    def _assert_zero_residue(self, dbname, ids, trigger_baseline):
        store_id = ids['store_id']
        v = self._open_bounded(dbname)
        try:
            for table, col, val, label in (
                ('shopify_connector_call_lease', 'store_id', store_id, 'lease'),
                ('shopify_connector_customer_binding', 'store_id', store_id,
                 'binding'),
                ('shopify_connector_job', 'store_id', store_id, 'job'),
                ('shopify_connector_store_settings', 'store_id', store_id,
                 'settings'),
                ('shopify_connector_store_credential', 'store_id', store_id,
                 'credential'),
                ('shopify_connector_store', 'id', store_id, 'store'),
            ):
                v.execute(
                    "SELECT count(*) FROM %s WHERE %s = %%s" % (table, col),
                    (val,))
                self.assertEqual(
                    v.fetchone()[0], 0, '%s residue after cleanup' % label)
            if ids.get('partner_id'):
                v.execute(
                    "SELECT count(*) FROM res_partner WHERE id = %s",
                    (ids['partner_id'],))
                self.assertEqual(
                    v.fetchone()[0], 0, 'partner residue after cleanup')
            # No test-created cron-trigger delta may remain (and, by construction,
            # every baseline/pre-existing trigger is untouched).
            self.assertEqual(
                self._trigger_delta_ids(v, trigger_baseline), [],
                'cron-trigger delta residue after cleanup')
            v.rollback()
        finally:
            v.close()


@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_customer_callsite_lifecycle')
class TestCustomerCallsiteLeaseVisibilityGenuine(
        _CustomerGenuineHelpers, TransactionCase):
    """M1/M2 -- genuine committed-lease visibility (review 4695664662 #3)."""

    # M1: the committed lease is visible on an INDEPENDENT connection BEFORE
    # `_send` runs, the admitted call uses the exact captured token, and the
    # lease is released on context exit -- all observed cross-connection, no
    # thread required (single admitted call).
    def test_m1_committed_lease_visible_before_send_and_released(self):
        dbname = self.env.cr.dbname
        ids = None
        worker_cr = None
        # Pre-test connector-cron trigger baseline (test ownership): cleanup
        # deletes only trigger ids created after this snapshot.
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'm1-%s' % uuid.uuid4().hex[:10])
            worker_cr = self._open_bounded(dbname)
            wenv = api.Environment(worker_cr, SUPERUSER_ID, {})
            Importer = wenv['shopify.connector.customer.importer']
            Client = wenv['shopify.connector.api.client']
            store = wenv['shopify.connector.store'].browse(ids['store_id'])
            job = wenv['shopify.connector.job'].browse(ids['job_id'])
            observed = {}

            def observing_send(client_self, s, body, token=None):
                # The committed lease is observable on an INDEPENDENT connection
                # BEFORE the transport call returns (M1).
                observed['during_send'] = self._lease_rows(dbname, ids['store_id'])
                observed['token'] = token
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', observing_send):
                    binding = Importer.import_customer_sync(
                        store, ids['gid'], job=job)
                worker_cr.commit()
            observed['after'] = self._lease_count(dbname, ids['store_id'])

            # M1: exactly one committed lease, keyed to the job, opaque, with the
            # real captured token, visible cross-connection before transport.
            self.assertEqual(len(observed['during_send']), 1)
            key, jid = observed['during_send'][0]
            self.assertEqual(jid, ids['job_id'])
            self.assertRegex(key, r'^[0-9a-f]{32}$')
            self.assertEqual(observed['token'], DUMMY_TOKEN)
            # Reconciliation completed (the binding is committed) and the lease
            # released on context exit.
            self.assertEqual(binding.shopify_gid, ids['gid'])
            self.assertEqual(observed['after'], 0)
            self.assertEqual(
                self._binding_count(dbname, ids['store_id'], ids['gid']), 1)
        finally:
            if worker_cr is not None:
                try:
                    worker_cr.rollback()
                except Exception:
                    pass
                worker_cr.close()
            self._cleanup(dbname, ids, trigger_baseline)

    # M2: the SAME committed lease remains held (exactly one) while
    # `_apply_import` is genuinely paused mid-reconciliation on a real
    # UNIQUE(store,partner) index wait; it is released only after reconciliation
    # completes and the context exits.
    def test_m2_lease_held_through_paused_reconciliation_then_released(self):
        dbname = self.env.cr.dbname
        ids = None
        locker_cr = monitor_cr = None
        worker_thread = None
        registry_cls = type(self.registry)
        saved_lock = registry_cls._lock
        pid_q = queue.Queue()
        token_q = queue.Queue()
        phase_q = queue.Queue()
        diag_q = queue.Queue()
        done_evt = threading.Event()
        result = {}
        obs = {'phases': []}
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'm2-%s' % uuid.uuid4().hex[:10])
            locker_gid = 'gid://shopify/Customer/locker-%s' % uuid.uuid4().hex[:8]
            # Genuine reconciliation pause: hold an uncommitted (store,partner)
            # binding so the worker's admitted binding INSERT blocks on the
            # unique index.
            locker_cr = self._hold_uncommitted_binding(dbname, ids, locker_gid)
            locker_pid = self._backend_pid(locker_cr)

            Client = self.env['shopify.connector.api.client']

            def fake_send(client_self, s, body, token=None):
                token_q.put(token)
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            def worker():
                phase_q.put('entered')
                wcr = None
                try:
                    wcr = self._open_bounded(dbname)
                    pid_q.put(self._backend_pid(wcr))
                    phase_q.put('cursor')
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    phase_q.put('env')
                    job = wenv['shopify.connector.job'].browse(ids['job_id'])
                    phase_q.put('before_dispatch')
                    wenv['shopify.connector.job.dispatch']._dispatch_one(job)
                    phase_q.put('after_dispatch')
                    wcr.commit()
                    phase_q.put('committed')
                    result['ok'] = True
                except BaseException as exc:
                    phase_q.put('exc:%s' % type(exc).__name__)
                    if wcr is not None:
                        try:
                            wcr.rollback()
                        except Exception:
                            pass
                    diag_q.put(self._sanitize(exc, 'worker'))
                finally:
                    if wcr is not None:
                        try:
                            wcr.close()
                        except Exception:
                            pass
                    phase_q.put('done')
                    done_evt.set()

            monitor_cr = self._open_bounded(dbname)
            with patch.object(registry_cls, '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)), \
                    patch.object(type(Client), '_send', fake_send):
                worker_thread = threading.Thread(
                    target=worker, name='m2-worker', daemon=True)
                worker_thread.start()
                pid_b = None
                try:
                    pid_b = pid_q.get(timeout=self.BOUND_SECONDS)
                except queue.Empty:
                    pid_b = None
                obs['pid_received'] = pid_b is not None
                obs['distinct_pids'] = bool(pid_b is not None and pid_b != locker_pid)
                if pid_b is not None:
                    blocked, is_insert = self._wait_blocked(
                        monitor_cr, pid_b, locker_pid, self.BOUND_SECONDS)
                else:
                    blocked, is_insert = False, False
                obs['blocked'] = blocked
                obs['is_binding_insert'] = is_insert
                # M2: while the worker is parked mid-reconciliation, exactly one
                # committed lease is observable, and the admitted token was the
                # real snapshot.
                obs['lease_during_reconciliation'] = self._lease_count(
                    dbname, ids['store_id'])
                try:
                    obs['token'] = token_q.get_nowait()
                except queue.Empty:
                    obs['token'] = None
                # Release the pause -> the worker's INSERT proceeds and binds.
                locker_cr.rollback()
                locker_cr.close()
                locker_cr = None
                obs['worker_done'] = done_evt.wait(timeout=self.BOUND_SECONDS)
                worker_thread.join(timeout=self.BOUND_SECONDS)
            registry_cls._lock = saved_lock
            obs['findings'] = self._drain(diag_q)
            obs['lease_after'] = self._lease_count(dbname, ids['store_id'])
            obs['binding_after'] = self._binding_count(
                dbname, ids['store_id'], ids['gid'])
        finally:
            registry_cls._lock = saved_lock
            # Cleanup-first teardown (review 4696393942 #3): release the barrier
            # and roll back the locker so a parked worker can exit, bounded-join
            # (normal then emergency), and capture worker liveness as EVIDENCE --
            # never an assertion here, which could abort the cleanup path.
            done_evt.set()
            if locker_cr is not None:
                try:
                    locker_cr.rollback()
                except Exception:
                    pass
                try:
                    locker_cr.close()
                except Exception:
                    pass
                locker_cr = None
            if worker_thread is not None:
                worker_thread.join(timeout=self.BOUND_SECONDS)
                if worker_thread.is_alive():
                    worker_thread.join(timeout=self.BOUND_SECONDS)  # emergency
            obs['worker_alive_final'] = bool(
                worker_thread is not None and worker_thread.is_alive())
            if monitor_cr is not None:
                try:
                    monitor_cr.rollback()
                except Exception:
                    pass
                monitor_cr.close()
            # Durable, zero-residue cleanup runs ONLY when no worker still owns DB
            # locks; a still-alive worker skips cleanup (recorded) and fails loud
            # below rather than acting against still-owned locks.
            if not obs['worker_alive_final']:
                self._cleanup(dbname, ids, trigger_baseline)
            else:
                obs['cleanup_skipped_worker_alive'] = True

        print('[SLICE2B-CUSTOMER-M2] %s' % obs)
        # Fail loud if a worker survived bounded recovery (cleanup was skipped to
        # avoid acting against still-owned locks) -- inconclusive, never passing.
        self.assertFalse(
            obs.get('worker_alive_final'),
            'worker still alive after bounded recovery; cleanup skipped')
        self.assertTrue(obs.get('pid_received'), 'worker never reported its PID')
        self.assertTrue(obs.get('distinct_pids'), 'backends must be distinct')
        self.assertTrue(
            obs.get('blocked'),
            'worker never parked on the (store,partner) unique index')
        self.assertTrue(
            obs.get('is_binding_insert'),
            "worker's parked statement was not the binding INSERT")
        # M2: exactly ONE lease held through the paused reconciliation.
        self.assertEqual(obs.get('lease_during_reconciliation'), 1)
        self.assertEqual(obs.get('token'), DUMMY_TOKEN)
        self.assertEqual(obs.get('findings'), [],
                         'worker findings: %s' % obs.get('findings'))
        self.assertTrue(obs.get('worker_done'), 'worker did not finish in bound')
        # Released only after reconciliation completed; the binding is committed.
        self.assertEqual(obs.get('lease_after'), 0)
        self.assertEqual(obs.get('binding_after'), 1)


@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_customer_callsite_lifecycle')
class TestCustomerCallsiteRaceAGenuine(_CustomerGenuineHelpers, TransactionCase):
    """Race A / M8 -- genuine admission-vs-disconnect ordering around the lease
    commit (review 4695664662 #1). Both orders are driven by the REAL
    `action_disconnect` + admission lock protocol on genuine independent
    connections -- never a pre-set state or a hand-written generation."""

    # A. Disconnect wins BEFORE admission: the real action_disconnect commits
    # first (distinct backend); the later `_admit` FOR SHARE reads the fresh
    # committed disconnecting/new-generation row and fails closed -> zero
    # transport, no lease, no partner or binding.
    def test_race_a_disconnect_first_fails_closed_zero_transport(self):
        dbname = self.env.cr.dbname
        ids = None
        worker_cr = None
        disc = None
        send_calls = []
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'raa-%s' % uuid.uuid4().hex[:10])
            # Real one-way disconnect commits FIRST on an independent backend --
            # and that connection is kept CHECKED OUT AND OPEN while the worker
            # connection is opened, so the backend PIDs are genuinely distinct by
            # construction, not by pool timing. (An earlier version closed the
            # disconnect connection before opening the worker; Odoo's LIFO
            # connection pool may then legitimately hand the worker the same
            # backend, which invalidated the distinct-PID proof under pooled
            # reuse -- runtime finding #1.)
            disc = self._open_bounded(dbname)
            denv = api.Environment(disc, SUPERUSER_ID, {})
            disc_pid = self._backend_pid(disc)
            denv['shopify.connector.store'].browse(
                ids['store_id']).action_disconnect()
            disc.commit()

            # Worker connection opened WHILE the disconnect connection is still
            # open -> a genuinely distinct backend.
            worker_cr = self._open_bounded(dbname)
            worker_pid = self._backend_pid(worker_cr)
            self.assertNotEqual(
                worker_pid, disc_pid,
                'the worker and the committed disconnect must run on distinct '
                'PostgreSQL backends (genuine independent connections)')
            wenv = api.Environment(worker_cr, SUPERUSER_ID, {})
            Importer = wenv['shopify.connector.customer.importer']
            Client = wenv['shopify.connector.api.client']
            store = wenv['shopify.connector.store'].browse(ids['store_id'])
            job = wenv['shopify.connector.job'].browse(ids['job_id'])

            def spy_send(client_self, s, body, token=None):
                send_calls.append(1)
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', spy_send):
                    # Fail-closed at admission: ShopifyQuiescedError propagates
                    # uncaught (never remapped to a ShopifyClientError/
                    # JobHandlerError).
                    with self.assertRaises(ShopifyQuiescedError):
                        Importer.import_customer_sync(store, ids['gid'], job=job)
                worker_cr.rollback()

            # Zero transport, no lease, no binding; the fixture partner is the
            # only partner (no confident-create partner was made).
            self.assertEqual(send_calls, [], 'no transport on a fail-closed admit')
            self.assertEqual(self._lease_count(dbname, ids['store_id']), 0)
            self.assertEqual(self._binding_count(dbname, ids['store_id']), 0)
            self.assertEqual(
                self._partner_count(dbname, ids['email']), 1)  # only the fixture P
        finally:
            # Cleanup-first, fail-loud: close both genuine connections safely,
            # then delete every committed fixture row and assert zero residue.
            if worker_cr is not None:
                try:
                    worker_cr.rollback()
                except Exception:
                    pass
                worker_cr.close()
            if disc is not None:
                try:
                    disc.rollback()
                except Exception:
                    pass
                disc.close()
            self._cleanup(dbname, ids, trigger_baseline)

    # B. Admission wins FIRST: `_admit` commits the lease + token snapshot; a real
    # action_disconnect then commits on a distinct backend DURING the call
    # (inside the transport seam) and returns; the already-admitted call
    # continues with its captured in-memory token and completes. Exactly one
    # transport, one lease (released), no untracked call.
    def test_race_a_admission_first_call_proceeds_with_snapshot(self):
        dbname = self.env.cr.dbname
        ids = None
        worker_cr = None
        send_calls = []
        captured = {}
        pids = []
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'rab-%s' % uuid.uuid4().hex[:10])
            worker_cr = self._open_bounded(dbname, read_committed=True)
            worker_pid = self._backend_pid(worker_cr)
            wenv = api.Environment(worker_cr, SUPERUSER_ID, {})
            Importer = wenv['shopify.connector.customer.importer']
            Client = wenv['shopify.connector.api.client']
            store = wenv['shopify.connector.store'].browse(ids['store_id'])
            job = wenv['shopify.connector.job'].browse(ids['job_id'])

            def racing_send(client_self, s, body, token=None):
                # Admission already committed the lease + token snapshot. A real
                # one-way disconnect wins NOW on an independent backend; it does
                # not block (the admission FOR SHARE released at commit) and
                # returns without waiting for this call.
                send_calls.append(1)
                captured['token'] = token
                captured['lease_during'] = self._lease_count(
                    dbname, ids['store_id'])
                disc = self._open_bounded(dbname)
                try:
                    denv = api.Environment(disc, SUPERUSER_ID, {})
                    pids.append(self._backend_pid(disc))
                    denv['shopify.connector.store'].browse(
                        ids['store_id']).action_disconnect()
                    disc.commit()
                finally:
                    disc.close()
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', racing_send):
                    binding = Importer.import_customer_sync(
                        store, ids['gid'], job=job)
                worker_cr.commit()

            # Exactly one transport with the captured OLD token; the lease was
            # committed (visible) before the disconnect; the admitted call
            # completed its binding; the lease released on exit.
            self.assertEqual(send_calls, [1])              # one call, no untracked
            self.assertEqual(captured['token'], DUMMY_TOKEN)
            self.assertEqual(captured['lease_during'], 1)  # tracked before disconnect
            self.assertEqual(binding.shopify_gid, ids['gid'])
            self.assertEqual(
                self._binding_count(dbname, ids['store_id'], ids['gid']), 1)
            self.assertEqual(self._lease_count(dbname, ids['store_id']), 0)
            # The disconnect won and returned; the credential is NOT cleared until
            # the controller finalizes (still present here).
            state, _gen, _status, cred_present = self._observe_store(
                dbname, ids['store_id'])
            self.assertEqual(state, 'disconnecting')
            self.assertTrue(cred_present)
            self.assertEqual(
                self._observe_credential_token(dbname, ids['store_id']), DUMMY_TOKEN)
            self.assertGreaterEqual(len(set(pids + [worker_pid])), 2)
        finally:
            if worker_cr is not None:
                try:
                    worker_cr.rollback()
                except Exception:
                    pass
                worker_cr.close()
            self._cleanup(dbname, ids, trigger_baseline)


@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_customer_callsite_lifecycle')
class TestCustomerCallsiteRaceBGenuine(_CustomerGenuineHelpers, TransactionCase):
    """Race B / M18 -- a disconnect landing AFTER a committed admission does not
    wait for the reconciliation body, and the quiescence controller defers
    finalization while an admission lease is open (reviews 4695664662 #2 +
    4696393942). Two complementary genuine proofs, both on real independent
    `db_connect` connections with distinct backend PIDs:

      1. `test_m18_lease_count_...` -- the PRIMARY LEASE-COUNT proof. The admitted
         customer call parks BEFORE any FK/business write (via the allowed
         `_apply_import` observe-and-delegate synchronization barrier), so the
         worker holds NO store-row lock. A concurrent real `action_disconnect`
         returns without waiting; then the real `_run_disconnect_quiesce`
         controller genuinely LOCKS the store (its `FOR UPDATE SKIP LOCKED`
         succeeds), reaches the lease-count branch, records
         `disconnect_open_lease_count = 1`, transitions to `quiescing`, and does
         NOT clear the credential while the lease exists. Only after the call
         releases the lease does a later pass finalize `completed` + clear the
         credential.

      2. `test_race_b_binding_keyshare_controller_skip_locked_coverage` -- retained
         LOCK-SKIP coverage (NOT the primary lease-count proof). Here the call
         parks ON the binding INSERT, whose `FOR KEY SHARE` on the store makes the
         controller's `FOR UPDATE SKIP LOCKED` legitimately SKIP the row and defer
         by skip. This exercises the skip path but never reaches the lease-count
         branch, so it cannot stand in for proof #1.
    """

    # -- PRIMARY M18 lease-count proof (review 4696393942) -----------------
    # Pause the admitted call via the allowed `_apply_import` observe-and-delegate
    # wrapper BEFORE the reconciliation savepoint / any FK write. At that point the
    # lease is already committed (admission ran in `execute_business.__enter__`) but
    # the worker's main transaction holds NO store-row lock -- `_admit`'s FOR SHARE
    # was committed+released together with the lease on its own side cursor
    # (api-client `_admit`, "no lock is ever held across the network call"). So the
    # controller's `FOR UPDATE SKIP LOCKED` on the store SUCCEEDS, it reaches the
    # LEASE-COUNT branch (`_process_disconnect_quiesce`), observes the one open
    # lease, writes `disconnect_open_lease_count`, and moves to the non-finalized
    # `quiescing` posture WITHOUT clearing the credential -- the exact path the
    # binding-key-share/SKIP-LOCKED scenario below can never reach.
    def test_m18_lease_count_then_serialization_retry_refuses_after_disconnect(
            self):
        """Corrected M18 contract (runtime correction, review `4699752673`):
        lease-count observation PLUS a genuine serialization conflict recovered by
        the corrected NO-REPLAY dispatcher, driven through the REAL scheduled
        ``run_drain`` entrypoint.

        The admitted customer call parks pre-FK (allowed ``_apply_import``
        observe-and-delegate barrier) holding one committed lease; a concurrent
        real ``action_disconnect`` returns without waiting; the real controller
        LOCKS the store, records ``disconnect_open_lease_count = 1``, goes
        ``quiescing`` and retains the credential. On release the reconciliation's
        binding INSERT touches the store row the disconnect committed and raises a
        genuine SQLSTATE 40001; the dispatcher's per-job boundary catches it
        WITHOUT replaying the handler -- it rolls back (the lease has already
        released via the ``execute_business`` context exit), resets, REACQUIRES
        the exact job under a real ``FOR UPDATE SKIP LOCKED`` row lock, and routes
        it ONCE to the bounded ``concurrency_race_conflict`` -> ``retry_waiting``
        state. A later controller pass then SWEEPS that (retry_waiting) business
        job to ``cancelled`` under the disconnect and finalizes the store
        (credential cleared only after the lease releases). Net: exactly one
        transport, zero binding from the aborted attempt, NO second transport (no
        replay), no raw concurrency exception as the outcome, and the superseded
        job cancelled by the disconnect. (Was a ``retrying``-boundary proof whose
        reset RE-INVOCATION was gate-refused into ``failed_retryable``; the
        corrected dispatcher no longer replays the handler and routes once under a
        reacquired lock, so the disconnect sweep cancels the retry_waiting job --
        runtime correction, review `4699752673`.)
        """
        dbname = self.env.cr.dbname
        ids = None
        monitor_cr = None
        worker_thread = None
        send_tokens = []
        registry_cls = type(self.registry)
        saved_lock = registry_cls._lock
        ImporterCls = type(self.env['shopify.connector.customer.importer'])
        real_apply = ImporterCls._apply_import
        pid_q = queue.Queue()
        token_q = queue.Queue()
        phase_q = queue.Queue()
        diag_q = queue.Queue()
        parked_evt = threading.Event()
        release_evt = threading.Event()
        done_evt = threading.Event()
        result = {}
        obs = {}
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'm18lc-%s' % uuid.uuid4().hex[:10])
            Client = self.env['shopify.connector.api.client']

            def fake_send(client_self, s, body, token=None):
                # One entry per transport invocation (total across all attempts).
                send_tokens.append(token)
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            def observing_apply(self_imp, store, payload, job=False):
                # SYNCHRONIZATION BARRIER (the allowed observe-and-delegate
                # wrapper): the lease is already committed (admission ran in
                # `__enter__`) and NO business/FK write has happened yet, so the
                # worker holds no store-row lock here. Signal parked, wait for
                # release, then delegate to the REAL reconciliation unchanged
                # (real matching/create/bind behaviour is preserved).
                phase_q.put('apply_entered')
                parked_evt.set()
                release_evt.wait(timeout=self.BOUND_SECONDS)
                phase_q.put('apply_delegating')
                return real_apply(self_imp, store, payload, job=job)

            def worker():
                wcr = None
                try:
                    wcr = self._open_bounded(dbname)
                    pid_q.put(self._backend_pid(wcr))
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    # Drive the REAL scheduled entrypoint so the production
                    # concurrency-retry boundary applies end to end (claims this
                    # job, dispatches it under odoo.service.model.retrying).
                    wenv['shopify.connector.job.dispatch'].run_drain(1)
                    wcr.commit()
                    result['ok'] = True
                except BaseException as exc:
                    if wcr is not None:
                        try:
                            wcr.rollback()
                        except Exception:
                            pass
                    diag_q.put(self._sanitize(exc, 'worker'))
                finally:
                    if wcr is not None:
                        try:
                            wcr.close()
                        except Exception:
                            pass
                    done_evt.set()

            def run_controller_pass():
                cc = self._open_bounded(dbname)
                try:
                    obs.setdefault('controller_pids', []).append(
                        self._backend_pid(cc))
                    cenv = api.Environment(cc, SUPERUSER_ID, {})
                    cenv['shopify.connector.store']._run_disconnect_quiesce()
                    cc.commit()
                finally:
                    cc.close()

            def drive_controller_until(target_status, timeout):
                # The controller processes ONE `disconnecting` store per pass, so
                # in the (unlikely, in sequential test execution) presence of
                # another disconnecting store OUR store may need more than one
                # pass. Loop bounded passes until our store's disconnect_status
                # reaches `target_status`, returning the final observation either
                # way (a miss fails loud in the assertions). Re-processing a store
                # already at the target is idempotent.
                deadline = time.monotonic() + timeout
                last = self._observe_store(dbname, ids['store_id'])
                while time.monotonic() < deadline:
                    if last[2] == target_status:
                        return last
                    run_controller_pass()
                    last = self._observe_store(dbname, ids['store_id'])
                    if last[2] == target_status:
                        return last
                    time.sleep(0.05)
                return last

            with self._capture_service_retry() as retry_log, \
                    self._instant_retry_backoff(), \
                    patch.object(registry_cls, '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)), \
                    patch.object(type(Client), '_send', fake_send), \
                    patch.object(ImporterCls, '_apply_import', observing_apply):
                worker_thread = threading.Thread(
                    target=worker, name='m18lc-worker', daemon=True)
                worker_thread.start()
                try:
                    pid_b = pid_q.get(timeout=self.BOUND_SECONDS)
                except queue.Empty:
                    pid_b = None
                obs['pid_received'] = pid_b is not None
                obs['worker_pid'] = pid_b
                # The worker reached the reconciliation pause BEFORE any FK write.
                obs['worker_parked'] = parked_evt.wait(timeout=self.BOUND_SECONDS)
                # Transport #1 (the admitted send) happened before the pre-FK
                # pause; its token is the first (and, proven below, only) one.
                obs['token'] = send_tokens[0] if send_tokens else None
                # The committed lease is observable; the worker holds no store lock.
                obs['lease_parked'] = self._lease_count(dbname, ids['store_id'])
                pre = self._observe_store(dbname, ids['store_id'])
                obs['state_before_disc'] = pre[0]

                # A concurrent real disconnect lands after the committed admission
                # and must return without waiting for the parked reconciliation.
                disc_start = time.monotonic()
                disc = self._open_bounded(dbname)
                try:
                    denv = api.Environment(disc, SUPERUSER_ID, {})
                    obs['disc_pid'] = self._backend_pid(disc)
                    denv['shopify.connector.store'].browse(
                        ids['store_id']).action_disconnect()
                    disc.commit()
                finally:
                    disc.close()
                obs['disc_returned_within_bound'] = (
                    time.monotonic() - disc_start) < self.BOUND_SECONDS
                after_disc = self._observe_store(dbname, ids['store_id'])
                obs['state_after_disc'] = after_disc[0]
                obs['gen_bumped'] = after_disc[1] > pre[1]
                obs['cred_present_after_disc'] = bool(after_disc[3])
                obs['worker_alive_after_disc'] = worker_thread.is_alive()

                # THE LEASE-COUNT PATH: the worker holds NO store lock at the
                # pre-FK pause, so the controller's FOR UPDATE SKIP LOCKED SUCCEEDS,
                # counts the one open lease, writes disconnect_open_lease_count, and
                # transitions to `quiescing` -- it does NOT finalize/clear while the
                # lease exists.
                q = drive_controller_until('quiescing', self.BOUND_SECONDS)
                obs['state_quiescing'] = q[0]
                obs['status_quiescing'] = q[2]
                obs['open_lease_count_field'] = self._store_open_lease_count(
                    dbname, ids['store_id'])
                obs['lease_quiescing'] = self._lease_count(dbname, ids['store_id'])
                obs['cred_present_quiescing'] = bool(q[3])
                obs['token_quiescing'] = self._observe_credential_token(
                    dbname, ids['store_id'])
                # Controller backends observed WHILE the worker is still parked
                # (holding its backend): these are provably distinct from the
                # worker. Later finalize passes run after the worker releases its
                # backend, which the LIFO pool may legitimately reuse -- so the
                # distinctness claim is scoped to this parked window.
                obs['controller_pids_quiescing'] = list(
                    obs.get('controller_pids') or [])

                # Release the pause -> the admitted call delegates to the REAL
                # `_apply_import`, binds, and releases the lease on context exit.
                release_evt.set()
                obs['worker_done'] = done_evt.wait(timeout=self.BOUND_SECONDS)
                worker_thread.join(timeout=self.BOUND_SECONDS)
                obs['lease_after_release'] = self._lease_count(
                    dbname, ids['store_id'])
                obs['binding_after_release'] = self._binding_count(
                    dbname, ids['store_id'], ids['gid'])

                # A later controller pass now sees zero leases -> finalizes.
                fin = drive_controller_until('completed', self.BOUND_SECONDS)
                obs['state_final'] = fin[0]
                obs['status_final'] = fin[2]
                obs['cred_present_final'] = bool(fin[3])
                obs['token_final'] = self._observe_credential_token(
                    dbname, ids['store_id'])
                obs['transport_count'] = len(send_tokens)
                obs['retry_serialization_logged'] = any(
                    'serial' in m.lower() or '40001' in m for m in retry_log)
                obs['retry_log_sample'] = list(retry_log)[:6]
                obs['job_state_final'] = self._observe_job_state(
                    dbname, ids['job_id'])
            registry_cls._lock = saved_lock
            obs['findings'] = self._drain(diag_q)
            obs['phases'] = self._drain(phase_q)
        finally:
            registry_cls._lock = saved_lock
            # Cleanup-first teardown (review 4696393942 #3): release the barrier so
            # a parked worker can exit, bounded-join (normal then emergency),
            # capture worker liveness as EVIDENCE (never asserted here), and run
            # durable cleanup only when no worker still owns DB locks.
            release_evt.set()
            done_evt.set()
            if worker_thread is not None:
                worker_thread.join(timeout=self.BOUND_SECONDS)
                if worker_thread.is_alive():
                    worker_thread.join(timeout=self.BOUND_SECONDS)  # emergency
            obs['worker_alive_final'] = bool(
                worker_thread is not None and worker_thread.is_alive())
            if monitor_cr is not None:
                try:
                    monitor_cr.rollback()
                except Exception:
                    pass
                monitor_cr.close()
            if not obs['worker_alive_final']:
                self._cleanup(dbname, ids, trigger_baseline)
            else:
                obs['cleanup_skipped_worker_alive'] = True

        print('[SLICE2B-CUSTOMER-M18-LEASECOUNT] %s' % obs)
        # Fail loud if a worker survived bounded recovery (cleanup was skipped).
        self.assertFalse(
            obs.get('worker_alive_final'),
            'worker still alive after bounded recovery; cleanup skipped')
        # Genuine setup: worker admitted + parked BEFORE any FK write, one committed
        # lease observed, real token snapshot, distinct backends.
        self.assertTrue(obs.get('pid_received'), 'worker never reported its PID')
        self.assertTrue(obs.get('worker_parked'),
                        'worker never reached the pre-FK reconciliation pause')
        self.assertEqual(obs.get('findings'), [],
                         'worker findings: %s' % obs.get('findings'))
        self.assertEqual(obs.get('lease_parked'), 1)
        self.assertEqual(obs.get('token'), DUMMY_TOKEN)
        self.assertEqual(obs.get('state_before_disc'), 'connected')
        # Genuine distinct backends: the worker holds its own connection open across
        # the whole race, so its backend PID is provably distinct from the (pooled)
        # disconnect and controller connections the parent opens. (disc/controller
        # connections are opened+closed and MAY share a pooled backend with each
        # other -- only worker-vs-others distinctness is the meaningful claim.)
        self.assertIsNotNone(obs.get('worker_pid'), 'worker backend PID missing')
        self.assertNotEqual(
            obs.get('worker_pid'), obs.get('disc_pid'),
            'the disconnect must run on a distinct backend from the parked worker')
        self.assertNotIn(
            obs.get('worker_pid'), obs.get('controller_pids_quiescing') or [],
            'the controller pass that observed the open lease must run on a '
            'backend distinct from the still-parked worker (a later finalize '
            'pass, after the worker frees its backend, may reuse it via the pool)')
        # The disconnect returned without waiting; worker still parked, lease open.
        self.assertTrue(obs.get('disc_returned_within_bound'))
        self.assertEqual(obs.get('state_after_disc'), 'disconnecting')
        self.assertTrue(obs.get('gen_bumped'))
        self.assertTrue(obs.get('worker_alive_after_disc'),
                        'the disconnect must not have waited for reconciliation')
        self.assertTrue(obs.get('cred_present_after_disc'))
        # THE LEASE-COUNT PATH REACHED: the controller LOCKED the store, counted the
        # open lease, wrote disconnect_open_lease_count=1, set `quiescing`, and did
        # NOT finalize/clear the credential while the lease existed.
        self.assertEqual(obs.get('state_quiescing'), 'disconnecting')
        self.assertEqual(obs.get('status_quiescing'), 'quiescing')
        self.assertEqual(obs.get('open_lease_count_field'), 1)
        self.assertEqual(obs.get('lease_quiescing'), 1)
        self.assertTrue(obs.get('cred_present_quiescing'))
        self.assertEqual(obs.get('token_quiescing'), DUMMY_TOKEN)
        # On release the reconciliation's binding INSERT raised a genuine 40001
        # (the store row was committed-superseded by the disconnect): the real
        # retry boundary rolled the attempt back (no binding), released the lease,
        # and the reset attempt was refused before any second transport.
        self.assertTrue(obs.get('worker_done'), 'worker did not finish in bound')
        self.assertEqual(obs.get('lease_after_release'), 0)
        self.assertEqual(
            obs.get('binding_after_release'), 0,
            'the superseded (retried-then-refused) attempt must leave no binding')
        self.assertEqual(
            obs.get('transport_count'), 1,
            'exactly one transport: the aborted attempt is never replayed')
        self.assertTrue(
            obs.get('retry_serialization_logged'),
            'a genuine SQLSTATE 40001 must have driven the corrected dispatcher '
            'concurrency-recovery boundary; recovery log sample: %s'
            % obs.get('retry_log_sample'))
        self.assertEqual(
            obs.get('job_state_final'), 'cancelled',
            'the superseded job must be routed once (no replay) to retry_waiting '
            'and then cancelled by the disconnect sweep, never a raw concurrency '
            'error; saw %s' % obs.get('job_state_final'))
        # Only AFTER release does the controller finalize: completed + cred cleared.
        self.assertEqual(obs.get('state_final'), 'disconnected')
        self.assertEqual(obs.get('status_final'), 'completed')
        self.assertFalse(obs.get('cred_present_final'))
        self.assertFalse(obs.get('token_final'))

    # -- Retained LOCK-SKIP coverage (NOT the primary lease-count proof) ---
    # Here the admitted call parks ON the binding INSERT, whose FOR KEY SHARE on the
    # store row makes the controller's FOR UPDATE SKIP LOCKED legitimately SKIP the
    # store and defer BY SKIP -- it never reaches the lease-count branch, so it is
    # complementary skip-path coverage, not the primary M18 lease-count proof (which
    # is `test_m18_lease_count_controller_observes_open_lease_then_finalizes`).
    def test_race_b_binding_keyshare_controller_skip_locked_coverage(self):
        dbname = self.env.cr.dbname
        ids = None
        locker_cr = monitor_cr = None
        worker_thread = None
        registry_cls = type(self.registry)
        saved_lock = registry_cls._lock
        pid_q = queue.Queue()
        token_q = queue.Queue()
        phase_q = queue.Queue()
        diag_q = queue.Queue()
        done_evt = threading.Event()
        result = {}
        obs = {}
        trigger_baseline = self._trigger_baseline(dbname)
        try:
            ids = self._fixture(dbname, 'rb-%s' % uuid.uuid4().hex[:10])
            locker_gid = 'gid://shopify/Customer/locker-%s' % uuid.uuid4().hex[:8]
            locker_cr = self._hold_uncommitted_binding(dbname, ids, locker_gid)
            locker_pid = self._backend_pid(locker_cr)
            Client = self.env['shopify.connector.api.client']

            def fake_send(client_self, s, body, token=None):
                token_q.put(token)
                return _RaceFakeResponse(200, json_body=self._payload_body(ids))

            def worker():
                wcr = None
                try:
                    wcr = self._open_bounded(dbname)
                    pid_q.put(self._backend_pid(wcr))
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    job = wenv['shopify.connector.job'].browse(ids['job_id'])
                    wenv['shopify.connector.job.dispatch']._dispatch_one(job)
                    wcr.commit()
                    result['ok'] = True
                except BaseException as exc:
                    if wcr is not None:
                        try:
                            wcr.rollback()
                        except Exception:
                            pass
                    diag_q.put(self._sanitize(exc, 'worker'))
                finally:
                    if wcr is not None:
                        try:
                            wcr.close()
                        except Exception:
                            pass
                    done_evt.set()

            def run_controller_pass():
                cc = self._open_bounded(dbname)
                try:
                    cenv = api.Environment(cc, SUPERUSER_ID, {})
                    cenv['shopify.connector.store']._run_disconnect_quiesce()
                    cc.commit()
                finally:
                    cc.close()

            monitor_cr = self._open_bounded(dbname)
            with patch.object(registry_cls, '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)), \
                    patch.object(type(Client), '_send', fake_send):
                worker_thread = threading.Thread(
                    target=worker, name='rb-worker', daemon=True)
                worker_thread.start()
                try:
                    pid_b = pid_q.get(timeout=self.BOUND_SECONDS)
                except queue.Empty:
                    pid_b = None
                obs['pid_received'] = pid_b is not None
                obs['distinct_pids'] = bool(pid_b is not None and pid_b != locker_pid)
                if pid_b is not None:
                    blocked, is_insert = self._wait_blocked(
                        monitor_cr, pid_b, locker_pid, self.BOUND_SECONDS)
                else:
                    blocked, is_insert = False, False
                obs['blocked'] = blocked
                obs['is_binding_insert'] = is_insert
                # Admission committed + parked mid-reconciliation: one lease held.
                obs['lease_parked'] = self._lease_count(dbname, ids['store_id'])
                try:
                    obs['token'] = token_q.get_nowait()
                except queue.Empty:
                    obs['token'] = None
                pre = self._observe_store(dbname, ids['store_id'])
                obs['state_before_disc'] = pre[0]

                # A concurrent real disconnect lands AFTER the committed
                # admission. It must NOT wait for the parked reconciliation.
                disc_start = time.monotonic()
                disc = self._open_bounded(dbname)
                try:
                    denv = api.Environment(disc, SUPERUSER_ID, {})
                    obs['disc_pid'] = self._backend_pid(disc)
                    denv['shopify.connector.store'].browse(
                        ids['store_id']).action_disconnect()
                    disc.commit()
                finally:
                    disc.close()
                obs['disc_returned_within_bound'] = (
                    time.monotonic() - disc_start) < self.BOUND_SECONDS
                # The disconnect returned while the worker is STILL parked (lease
                # open, no binding yet) -> it did not block on reconciliation.
                after_disc = self._observe_store(dbname, ids['store_id'])
                obs['state_after_disc'] = after_disc[0]
                obs['status_after_disc'] = after_disc[2]
                obs['gen_bumped'] = after_disc[1] > pre[1]
                obs['cred_present_after_disc'] = bool(after_disc[3])
                obs['lease_after_disc'] = self._lease_count(dbname, ids['store_id'])
                obs['binding_after_disc'] = self._binding_count(
                    dbname, ids['store_id'], ids['gid'])
                obs['worker_alive_after_disc'] = worker_thread.is_alive()

                # Controller pass while the admitted call is parked
                # mid-reconciliation: the in-flight binding INSERT holds a
                # FOR KEY SHARE on the store row (a binding's store_id FK), so the
                # controller's FOR UPDATE SKIP LOCKED (`try_lock_for_update`)
                # SAFELY SKIPS the store and defers -- it must NOT finalize while a
                # lease is open (its count-stability guarantee finalizes only under
                # its own held FOR UPDATE, which it cannot take here). This is the
                # genuine deferral: no `completed`, no `disconnected`, lease still
                # open, credential preserved. (The lease-count-based `quiescing`
                # transition needs the store lockable -- no in-flight key-share --
                # and is proven directly by the PRIMARY lease-count test
                # `test_m18_lease_count_controller_observes_open_lease_then_finalizes`
                # above; this method is complementary skip-path coverage only.)
                run_controller_pass()
                d1 = self._observe_store(dbname, ids['store_id'])
                obs['state_deferred'] = d1[0]
                obs['status_deferred'] = d1[2]
                obs['lease_deferred'] = self._lease_count(dbname, ids['store_id'])
                obs['cred_present_deferred'] = bool(d1[3])

                # Release the pause -> the admitted call finishes with its
                # in-memory token and releases the lease.
                locker_cr.rollback()
                locker_cr.close()
                locker_cr = None
                obs['worker_done'] = done_evt.wait(timeout=self.BOUND_SECONDS)
                worker_thread.join(timeout=self.BOUND_SECONDS)
                obs['lease_after_release'] = self._lease_count(
                    dbname, ids['store_id'])
                obs['binding_after_release'] = self._binding_count(
                    dbname, ids['store_id'], ids['gid'])

                # Controller pass 2 now that the lease released: finalizes.
                run_controller_pass()
                fin = self._observe_store(dbname, ids['store_id'])
                obs['state_final'] = fin[0]
                obs['status_final'] = fin[2]
                obs['cred_present_final'] = bool(fin[3])
                obs['token_final'] = self._observe_credential_token(
                    dbname, ids['store_id'])
            registry_cls._lock = saved_lock
            obs['findings'] = self._drain(diag_q)
        finally:
            registry_cls._lock = saved_lock
            # Cleanup-first teardown (review 4696393942 #3): release the barrier
            # and roll back the locker so a parked worker can exit, bounded-join
            # (normal then emergency), capture worker liveness as EVIDENCE (never
            # asserted here), and run durable cleanup only when no worker still
            # owns DB locks.
            done_evt.set()
            if locker_cr is not None:
                try:
                    locker_cr.rollback()
                except Exception:
                    pass
                try:
                    locker_cr.close()
                except Exception:
                    pass
                locker_cr = None
            if worker_thread is not None:
                worker_thread.join(timeout=self.BOUND_SECONDS)
                if worker_thread.is_alive():
                    worker_thread.join(timeout=self.BOUND_SECONDS)  # emergency
            obs['worker_alive_final'] = bool(
                worker_thread is not None and worker_thread.is_alive())
            if monitor_cr is not None:
                try:
                    monitor_cr.rollback()
                except Exception:
                    pass
                monitor_cr.close()
            if not obs['worker_alive_final']:
                self._cleanup(dbname, ids, trigger_baseline)
            else:
                obs['cleanup_skipped_worker_alive'] = True

        print('[SLICE2B-CUSTOMER-M18-LOCKSKIP] %s' % obs)
        # Fail loud if a worker survived bounded recovery (cleanup was skipped).
        self.assertFalse(
            obs.get('worker_alive_final'),
            'worker still alive after bounded recovery; cleanup skipped')
        # Genuine setup.
        self.assertTrue(obs.get('pid_received'), 'worker never reported its PID')
        self.assertTrue(obs.get('distinct_pids'), 'backends must be distinct')
        self.assertTrue(obs.get('blocked'), 'worker never parked mid-reconciliation')
        self.assertTrue(obs.get('is_binding_insert'),
                        "worker's parked statement was not the binding INSERT")
        self.assertEqual(obs.get('findings'), [],
                         'worker findings: %s' % obs.get('findings'))
        # Admission committed before the disconnect (lease held, real token).
        self.assertEqual(obs.get('lease_parked'), 1)
        self.assertEqual(obs.get('token'), DUMMY_TOKEN)
        self.assertEqual(obs.get('state_before_disc'), 'connected')
        # M18: the disconnect returned without waiting for the reconciliation.
        self.assertTrue(obs.get('disc_returned_within_bound'))
        self.assertEqual(obs.get('state_after_disc'), 'disconnecting')
        self.assertTrue(obs.get('gen_bumped'))
        self.assertTrue(obs.get('worker_alive_after_disc'),
                        'the disconnect must not have waited for reconciliation')
        self.assertEqual(obs.get('lease_after_disc'), 1)      # still open
        self.assertEqual(obs.get('binding_after_disc'), 0)    # not yet bound
        self.assertTrue(obs.get('cred_present_after_disc'))   # credential kept
        # Controller defers finalization BY SKIP while the binding key-share is
        # held: it SKIPS the store row (never reaching the lease-count branch), so
        # the store stays `disconnecting` (never `disconnected`/`completed`), the
        # lease is still open, and the credential is preserved. (The lease-count
        # branch -- store lockable, `quiescing`, disconnect_open_lease_count -- is
        # asserted in the primary lease-count test, not here.)
        self.assertEqual(obs.get('state_deferred'), 'disconnecting')
        self.assertNotEqual(obs.get('status_deferred'), 'completed')
        self.assertEqual(obs.get('lease_deferred'), 1)
        self.assertTrue(obs.get('cred_present_deferred'))
        # The admitted call finished and released its lease; the binding committed.
        self.assertTrue(obs.get('worker_done'), 'worker did not finish in bound')
        self.assertEqual(obs.get('lease_after_release'), 0)
        self.assertEqual(obs.get('binding_after_release'), 1)
        # Finalization happens ONLY after release: completed + credential cleared.
        self.assertEqual(obs.get('state_final'), 'disconnected')
        self.assertEqual(obs.get('status_final'), 'completed')
        self.assertFalse(obs.get('cred_present_final'))
        self.assertFalse(obs.get('token_final'))
