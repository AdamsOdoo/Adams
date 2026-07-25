# Exhaustive frozen test list (locked prompt §5). No additional test file may be
# added without a control-room allowlist amendment. The Wave 5 U1 locked prompt
# is such an amendment: it authorises exactly the six `test_ui_*` modules at the
# end of this list, and no others. The runtime concurrency
# harness (runtime_layer2_fulfillment_concurrency_harness.py) is deliberately
# NOT imported here — it is an out-of-band multiprocessing script, never an
# Odoo test.
from . import test_fulfillment_binding
from . import test_fulfillment_inbound_evidence
from . import test_fulfillment_trigger
from . import test_fulfillment_admission
from . import test_fulfillment_reader_pagination
from . import test_fulfillment_matching
from . import test_fulfillment_location_resolution
from . import test_fulfillment_create_strategy
from . import test_fulfillment_tracking_strategy
from . import test_fulfillment_idempotency
from . import test_fulfillment_inbound_classification
from . import test_fulfillment_mode2_engine
from . import test_fulfillment_mode_switch
from . import test_fulfillment_scans
from . import test_fulfillment_review_release
from . import test_fulfillment_cod_interplay
from . import test_fulfillment_state_model
from . import test_fulfillment_lifecycle
from . import test_fulfillment_readiness
from . import test_fulfillment_vocabulary_guard
from . import test_fulfillment_source_guards
from . import test_fulfillment_concurrency
# --- Wave 5 U1 operator UI (authorised by u1-locked-implementation-prompt.md) ---
from . import test_ui_import_structure
from . import test_ui_source_guards
from . import test_ui_visibility_matrix
from . import test_ui_actions
from . import test_ui_sec3_scope
from . import test_ui_tours
