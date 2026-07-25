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
