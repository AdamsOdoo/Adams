"""Dependency-free contracts for the first P10 product scan slice.

The Odoo registry and a Shopify server are intentionally not required here.
These checks keep the production boundary reviewable while the addon-level
tests exercise the route and registration when Odoo CI is available.
"""

import ast
from pathlib import Path
import textwrap
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "addons" / "shopify_connector_product"
CORE = ROOT / "addons" / "shopify_connector_core"
P10 = PRODUCT / "models" / "shopify_connector_product_scan_p10.py"
ADMISSION = PRODUCT / "models" / "shopify_connector_product_scan_p10_admission.py"
LEGACY = PRODUCT / "models" / "shopify_connector_product_scan.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    source = _source(path)
    return ast.parse(source, filename=str(path))


def _method(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )
    return textwrap.dedent(ast.get_source_segment(source, node))


class TestProductScanP10SourceContracts(unittest.TestCase):
    def test_files_parse_and_are_loaded_after_the_v1_scan(self):
        _tree(P10)
        _tree(ADMISSION)
        init_source = _source(PRODUCT / "models" / "__init__.py")
        self.assertIn("from . import shopify_connector_product_scan", init_source)
        self.assertIn(
            "from . import shopify_connector_product_scan_p10", init_source,
        )
        self.assertIn(
            "from . import shopify_connector_product_scan_p10_admission",
            init_source,
        )
        self.assertLess(
            init_source.index("from . import shopify_connector_product_scan\n"),
            init_source.index("from . import shopify_connector_product_scan_p10\n"),
        )

    def test_v2_handler_never_calls_the_legacy_scan_loop(self):
        source = _source(P10)
        body = _method(source, "handle_claim")
        calls = [
            node for node in ast.walk(ast.parse(body))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        ]
        self.assertNotIn("run_scan", {node.func.attr for node in calls})
        self.assertIn("_read_product_scan_page", body)
        self.assertIn("claim=claim", body)
        self.assertIn("range(PRODUCT_SCAN_SLICE_PAGES)", body)
        self.assertIn("_commit_page", body)

    def test_network_page_read_is_separate_from_each_claimed_local_commit(self):
        source = _source(P10)
        handler = _method(source, "handle_claim")
        commit = _method(source, "_commit_page")
        self.assertLess(
            handler.index("_read_product_scan_page"),
            handler.index("_commit_page"),
        )
        self.assertIn("with self._local_transaction() as side_env", commit)
        self.assertIn("_validate_v2_read_claim_for_update", commit)
        self.assertNotIn("_read_product_scan_page", commit)

    def test_durable_checkpoint_writes_use_the_named_settings_service(self):
        source = _source(P10)
        self.assertGreaterEqual(
            source.count("_settings_service_write('_product_scan'"), 2,
        )
        self.assertIn("product_scan_window_end_at", source)
        self.assertIn("product_scan_cursor", source)
        self.assertIn("product_scan_page_count", source)
        self.assertIn("product_last_import_checkpoint_at", source)
        begin = _method(source, "_initialize_window")
        self.assertIn("end = _max_datetime(observed_now, checkpoint)", begin)
        commit = _method(source, "_commit_page")
        self.assertIn("if observed_exact > window['end']", commit)
        self.assertIn(
            "checkpoint, latest, current['end']",
            commit,
        )

    def test_malformed_remote_identity_cursor_and_time_fail_closed(self):
        source = _source(P10)
        for helper in ("def _aware_utc", "def _cursor", "def _db_utc"):
            self.assertIn(helper, source)
        self.assertIn("_PRODUCT_GID_RE", source)
        self.assertIn("_product_gid(node.get('id'))", source)
        self.assertIn("_shape_failure", source)
        self.assertIn("_aware_utc(node.get('updatedAt')", source)
        self.assertIn("The terminal product scan page carried a cursor.", source)
        self.assertIn("The product scan cursor did not make progress.", source)

    def test_handler_boundary_maps_retry_and_manual_fix_classes(self):
        source = _source(P10)
        repository = _source(
            CORE / "models" / "shopify_connector_v2_runtime_repository.py",
        )
        retry = _method(source, "_retry_or_review")
        handler = _method(source, "handle_claim")
        self.assertIn("decide_retry", retry)
        self.assertIn("_claim_retry_inputs(claim)", retry)
        self.assertNotIn("job.retry_count", retry)
        self.assertIn("error_class=error_class", retry)
        self.assertIn("_MANUAL_FIX_ERROR_CLASSES", retry)
        self.assertIn("_AUTO_RETRY_ERROR_CLASSES", retry)
        self.assertIn("_claim_jitter_fraction(claim)", retry)
        self.assertIn("run_requested_at", source)
        self.assertIn("def _claim_retry_inputs", source)
        self.assertIn("The product scan claim has invalid retry metadata.", source)
        self.assertIn("The product scan claim has invalid run timestamp metadata.", source)
        self.assertIn("'retry_count': int(job.retry_count or 0)", repository)
        self.assertIn("'run_requested_at': _utc(", repository)
        self.assertIn("except (JobHandlerError, ShopifyClientError) as exc", handler)
        self.assertNotIn("except Exception as exc", handler)
        self.assertIn(
            "except (PsycopgError, ShopifyQuiescedError, RuntimeBoundaryError):",
            handler,
        )

    def test_legacy_children_are_explicitly_compatibility_only(self):
        source = _source(P10)
        admission = _method(source, "_admit_legacy_child")
        self.assertIn("product_import_sync", admission)
        self.assertNotIn("run_id", admission)
        self.assertIn("child_runtime': 'legacy_compatibility'", source)
        self.assertIn("duplicate_risk", admission)
        # The V1 producer remains the compatibility fallback and is not
        # rewritten by importing the V2 admission extension.
        legacy_source = _source(LEGACY)
        self.assertIn("def _enqueue_product_scan", legacy_source)
        self.assertIn("def _handle_product_import_scan", legacy_source)

    def test_admission_registers_handler_without_legacy_claim_union(self):
        source = _source(ADMISSION)
        self.assertIn("_extend_v2_read_only_handler_specs", source)
        self.assertIn("ReadOnlyHandlerSpec", source)
        # Read-only jobs are selected by the P10 repository.  Extending the
        # legacy dispatcher union would let the same run-linked row be claimed
        # twice through Layer 2.
        self.assertNotIn("def _get_v2_job_types", source)
        self.assertIn("_PRODUCT_SCAN_HANDLER", source)
        self.assertIn("_PRODUCT_SCAN_HANDLER = 'product_import_scan'", _source(P10))

    def test_v2_route_creates_run_before_admitting_the_job_and_keeps_v1_route(self):
        source = _source(ADMISSION)
        route = _method(source, "_enqueue_v2_product_scan")
        self.assertLess(route.index("_create_service"), route.index("_admit_service"))
        self.assertLess(route.index("_admit_service"), route.index("enqueue_read_only_job"))
        self.assertIn("runtime_mode_includes", source)
        self.assertIn("return super()._enqueue_product_scan(job_source)", source)
        self.assertIn("self.ensure_one()", _method(source, "_enqueue_product_scan"))
        self.assertIn("'actor_uid': self.env.uid", route)
        privileged_enqueue = ".sudo().enqueue_read_only_job"
        self.assertIn(privileged_enqueue, route)
        self.assertLess(route.index("_create_service"), route.index(privileged_enqueue))

    def test_successor_preserves_same_run_lineage_and_is_admitted_in_finalizer(self):
        source = _source(ADMISSION)
        finalizer = _method(source, "_finalize_v2_read_result")
        self.assertIn("super()._finalize_v2_read_result", finalizer)
        self.assertIn("parent_job_id", finalizer)
        self.assertIn("sequence", finalizer)
        self.assertLess(
            finalizer.index("super()._finalize_v2_read_result"),
            finalizer.index("enqueue_read_only_job"),
        )
        self.assertIn("if lane_priority is None or lane_priority is False", finalizer)
        self.assertIn("continuation", finalizer)
        self.assertIn("hashlib.sha256", finalizer)

    def test_integrity_recovery_requires_unique_sqlstate_and_savepoint(self):
        p10_source = _source(P10)
        admission_source = _source(ADMISSION)
        child = _method(p10_source, "_admit_legacy_child")
        initial = _method(admission_source, "_enqueue_v2_product_scan")
        finalizer = _method(admission_source, "_finalize_v2_read_result")

        for body in (child, initial, finalizer):
            self.assertIn("except IntegrityError as exc", body)
            self.assertIn("if not _is_unique_violation(exc):", body)
            self.assertIn("raise", body)
        self.assertIn("with side_env.cr.savepoint()", child)
        self.assertIn("with self.env.cr.savepoint()", initial)
        self.assertIn("with self.env.cr.savepoint()", finalizer)
        self.assertIn("_UNIQUE_VIOLATION_SQLSTATE = '23505'", p10_source)
        self.assertNotIn("except IntegrityError:\n", p10_source + admission_source)

    def test_child_and_initial_winners_are_exact_rows(self):
        p10_source = _source(P10)
        admission_source = _source(ADMISSION)
        child = _method(p10_source, "_admit_legacy_child")
        exact_active = _method(admission_source, "_exact_active_product_scan")
        initial = _method(admission_source, "_enqueue_v2_product_scan")

        for field in (
            "store_id", "job_type", "res_model", "res_id",
            "shopify_target_gid", "payload_hash",
        ):
            self.assertIn(field, child)
        for field in (
            "store_id", "job_type", "res_model", "res_id",
            "shopify_target_gid", "state",
        ):
            self.assertIn(field, exact_active)
        self.assertIn("_exact_active_product_scan()", initial)
        # The recovery branch must not fall back to the broad legacy helper.
        recovery = initial[initial.index("except IntegrityError") :]
        self.assertNotIn("self._active_product_scan()", recovery)

    def test_continuation_winner_checks_full_identity_generation_and_lineage(self):
        source = _source(ADMISSION)
        finalizer = _method(source, "_finalize_v2_read_result")
        matcher = _method(source, "_continuation_job_matches")
        for field in (
            "run_id", "parent_job_id", "sequence", "job_type", "store_id",
            "res_model", "res_id", "shopify_target_gid", "payload_hash",
            "expected_connection_generation",
            "expected_configuration_generation", "lane", "lane_priority",
        ):
            self.assertIn(field, finalizer)
        self.assertIn("_continuation_job_matches", finalizer)
        self.assertIn("expected_connection_generation", matcher)
        self.assertIn("expected_configuration_generation", matcher)
        self.assertIn("run", matcher)
        self.assertIn("parent", matcher)

    def test_sqlstate_and_payload_helpers_reject_unrelated_or_mismatched_rows(self):
        tree = _tree(P10)
        selected = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {
                "_is_unique_violation", "_record_id", "_job_matches_expected",
            }
        ]
        namespace = {"_UNIQUE_VIOLATION_SQLSTATE": "23505"}
        exec(
            compile(ast.Module(body=selected, type_ignores=[]), str(P10), "exec"),
            namespace,
        )

        is_unique = namespace["_is_unique_violation"]
        self.assertTrue(is_unique(SimpleNamespace(pgcode="23505")))
        self.assertFalse(is_unique(SimpleNamespace(pgcode="23514")))
        self.assertFalse(is_unique(SimpleNamespace(pgcode="23503")))
        self.assertFalse(is_unique(SimpleNamespace(pgcode="23502")))
        self.assertTrue(is_unique(SimpleNamespace(
            pgcode=None, diag=SimpleNamespace(sqlstate="23505"),
        )))

        matches = namespace["_job_matches_expected"]
        winner = SimpleNamespace(
            store_id=SimpleNamespace(id=7),
            job_type="product_import_sync",
            res_model="shopify.connector.store",
            res_id=7,
            shopify_target_gid="gid://shopify/Product/7",
            payload_hash="stamp-a",
        )
        expected = dict(
            store_id=7,
            job_type="product_import_sync",
            res_model="shopify.connector.store",
            res_id=7,
            target_gid="gid://shopify/Product/7",
            payload_hash="stamp-a",
        )
        self.assertTrue(matches(winner, **expected))
        self.assertFalse(matches(winner, **dict(expected, payload_hash="stamp-b")))
        self.assertFalse(matches(
            winner,
            **dict(expected, target_gid="gid://shopify/Product/8"),
        ))
        self.assertFalse(matches(winner, **dict(expected, store_id=8)))

    def test_continuation_matcher_rejects_mismatched_parent_claim_payload(self):
        p10_tree = _tree(P10)
        admission_tree = _tree(ADMISSION)
        selected = [
            node for node in p10_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {
                "_record_id", "_job_matches_expected",
            }
        ]
        selected += [
            node for node in admission_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_continuation_job_matches"
        ]
        namespace = {"_PRODUCT_SCAN_HANDLER": "product_import_scan"}
        exec(
            compile(
                ast.Module(body=selected, type_ignores=[]),
                str(ADMISSION),
                "exec",
            ),
            namespace,
        )

        store = SimpleNamespace(id=7)
        company = SimpleNamespace(id=3)
        run = SimpleNamespace(
            id=17,
            store_id=store,
            company_id=company,
            workflow="product",
            operation="product.import.scan",
            expected_connection_generation=4,
            expected_configuration_generation=8,
        )
        job = SimpleNamespace(
            id=31,
            store_id=store,
            company_id=company,
            run_id=run,
            job_type="product_import_scan",
            res_model="shopify.connector.store",
            res_id=7,
            shopify_target_gid="scan:product",
            expected_connection_generation=4,
            expected_configuration_generation=8,
        )
        payload = {
            "job_type": "product_import_scan",
            "operation": "product.import.scan",
            "res_model": "shopify.connector.store",
            "res_id": 7,
            "shopify_target_gid": "scan:product",
        }
        claim = SimpleNamespace(
            job_id=31,
            run_id=17,
            store_id=7,
            company_id=3,
            handler_key="product_import_scan",
            expected_generation=4,
            expected_configuration_generation=8,
            payload=payload,
        )
        winner = SimpleNamespace(
            id=32,
            store_id=store,
            company_id=company,
            run_id=run,
            parent_job_id=job,
            sequence=1,
            job_type="product_import_scan",
            res_model="shopify.connector.store",
            res_id=7,
            shopify_target_gid="scan:product",
            payload_hash="continuation-hash",
            expected_connection_generation=4,
            expected_configuration_generation=8,
            lane="interactive",
            lane_priority=100,
        )
        matcher = namespace["_continuation_job_matches"]
        kwargs = dict(
            job=job,
            run=run,
            claim=claim,
            sequence=1,
            payload_hash="continuation-hash",
            lane="interactive",
            lane_priority=100,
        )
        self.assertTrue(matcher(winner, **kwargs))
        self.assertFalse(matcher(
            winner,
            **dict(kwargs, claim=SimpleNamespace(
                **dict(claim.__dict__, payload=dict(payload, res_id=99)),
            )),
        ))
        self.assertFalse(matcher(
            winner,
            **dict(kwargs, claim=SimpleNamespace(
                **dict(claim.__dict__, job_id=999),
            )),
        ))


if __name__ == "__main__":
    unittest.main()
