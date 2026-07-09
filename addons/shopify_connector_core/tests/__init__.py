# test_api_client / test_job_log_system_append / test_test_connection
# import lines below are Task 003 test-discovery scaffolding: Odoo
# discovers tests only via this package's own imports, so a new test
# file is otherwise dead code. Not named in the Task 003 final
# implementation prompt's allowed-files list; approved as a necessary
# exception by ChatGPT's F1 review of PR #101 (mirrors the
# already-allowed models/__init__.py one-import-line pattern).
from . import test_api_client
from . import test_connection_lifecycle
from . import test_credential_access
from . import test_credential_service
from . import test_job_dispatch
from . import test_job_enqueue
from . import test_job_log_system_append
from . import test_job_retry_scheduling
from . import test_readiness_check
from . import test_redaction
from . import test_test_connection
