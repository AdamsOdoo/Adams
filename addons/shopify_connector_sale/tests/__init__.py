from . import test_customer_binding
from . import test_customer_import_matching
from . import test_customer_duplicate_prevention
from . import test_customer_fallback_partner
from . import test_customer_matching_scalability
from . import test_pii_least_privilege
from . import test_order_binding
from . import test_order_import_mapping
from . import test_order_totals_guard
from . import test_order_tax_resolution
from . import test_order_duplicate_prevention
from . import test_order_customer_resolution
from . import test_order_confirmation_policy
from . import test_order_manual_gateway_overlay
from . import test_order_watermark_backfill
from . import test_order_cod_import_readmodel
from . import test_order_scan_triggers
# SEC-3 (issue #197) two-company isolation matrix.
from . import test_sec3_company_isolation
from . import test_ui_u2_sale
from . import test_ui_u2_action_tours
from . import test_setup_order_defaults

# Batch 2 checkpoint 1: canonical Store Settings classification.
from . import test_canonical_store_settings_sale
from . import test_tax_decision_route
from . import test_tax_mapping_race
from . import test_batch2_correction_at_any_head
from . import test_batch2_journeys_sale
from . import test_ui_b2_sale_tours

# Store 360 slice 1 (final pre-UAT implementation session, 2026-08-01):
# the protected sale-order projection, the rule-respecting aggregate
# sections, the adversarial record-rule suite and the generation-bound
# order catch-up.
from . import test_sale_order_projection
from . import test_store360_aggregates
from . import test_store360_security
from . import test_order_reconnect_catchup
