# test_api_client / test_job_log_system_append / test_test_connection
# import lines below are Task 003 test-discovery scaffolding: Odoo
# discovers tests only via this package's own imports, so a new test
# file is otherwise dead code. Not named in the Task 003 final
# implementation prompt's allowed-files list; approved as a necessary
# exception by ChatGPT's F1 review of PR #101 (mirrors the
# already-allowed models/__init__.py one-import-line pattern).
from . import test_api_client
from . import test_connection_lifecycle
from . import test_disconnect_quiescence
from . import test_credential_access
from . import test_credential_service
from . import test_client_credentials
from . import test_credential_provenance_race
from . import test_job_dispatch
from . import test_job_enqueue
from . import test_job_log_system_append
from . import test_job_actions
from . import test_lifecycle_uninstall
from . import test_job_retry_scheduling
from . import test_readiness_check
from . import test_readiness_slot_closure
from . import test_redaction
from . import test_security_hardening
from . import test_test_connection
from . import test_mutation_attempt
from . import test_mutation_dispatch
from . import test_mutation_reconciliation
from . import test_mutation_recovery
from . import test_mutation_api_guard
from . import test_mutation_security
from . import test_mutation_retention
from . import test_mutation_concurrency
from . import test_mutation_source_guards
# U0 operator UI foundation tests.
from . import test_ui_installation
from . import test_ui_dashboard
from . import test_ui_visibility_matrix
from . import test_ui_actions
from . import test_ui_performance
from . import test_ui_tours
from . import test_ui_source_guards
# F-4 permanent location-resolution seam (Theme I, Wave 4 closure).
from . import test_shopify_connector_location
# Issue #193/#157 regression guard for the Odoo 19 test-phase contract.
from . import test_phase_contract
from . import test_sec3_store_ownership
# SEC-2 (issue #196) customer-facing connector roles.
from . import test_sec2_roles
# PERF-1 core queue throughput calibration.
from . import test_dispatch_throughput
from . import test_ui_visual_evidence
from . import test_suite_runner_fails_closed
from . import test_throttle_backpressure
from . import test_api_version_binding
from . import test_vocabulary_reconciliation
# S1 guided setup wizard: the server side of the 11-step flow, and the
# browser traversal that proves it is reachable at all.
from . import test_setup_wizard
from . import test_ui_setup_tours
# Batch 2 checkpoint 1: the canonical Store Settings surface. The
# classification helper is imported by the domain modules' own tests, so it
# lives beside the core test that first uses it.
from . import canonical_settings_classification
from . import test_canonical_store_settings
from . import test_batch2_journeys_core
from . import test_ui_b2_settings_tours
