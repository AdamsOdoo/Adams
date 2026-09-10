"""Dependency-free checks for strict legacy evidence comparison."""
import copy
import unittest
from tools.w2_upgrade_preservation_fixture import TABLES, snapshot, verify_snapshot


class Cursor:
    def __init__(self, missing=False):
        self.missing = missing
    def execute(self, query, params):
        self.columns = query.split(' FROM ')[0].removeprefix('SELECT ').split(', ')
        self.ids = params[0]
    def fetchall(self):
        return [] if self.missing else [tuple(i if c == 'id' else None for c in self.columns) for i in self.ids]


class PreservationTests(unittest.TestCase):
    def test_snapshot_requires_every_seeded_row(self):
        with self.assertRaisesRegex(AssertionError, 'missing rows'):
            snapshot(Cursor(missing=True), {table: [1] for table in TABLES})

    def test_each_history_or_identity_change_fails(self):
        before = snapshot(Cursor(), {table: [1] for table in TABLES})
        for table in TABLES:
            with self.subTest(table=table):
                after = copy.deepcopy(before)
                after[table][0]['id'] = 2
                with self.assertRaisesRegex(AssertionError, table):
                    verify_snapshot(before, after)

    def test_uncertainty_resolution_and_evidence_cannot_change(self):
        before = snapshot(Cursor(), {table: [1] for table in TABLES})
        for field in ('observed_outcome', 'resolution_disposition', 'remote_evidence_refs', 'exact_request_fingerprint'):
            after = copy.deepcopy(before)
            after['shopify_connector_mutation_attempt'][0][field] = 'changed'
            with self.assertRaises(AssertionError):
                verify_snapshot(before, after)

    def test_identical_rows_pass(self):
        before = snapshot(Cursor(), {table: [1] for table in TABLES})
        verify_snapshot(before, copy.deepcopy(before))
