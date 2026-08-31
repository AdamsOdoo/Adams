"""Pure inventory-domain contracts used by the P12 vertical slice.

The package is deliberately not imported by the Odoo model package yet.  This
keeps the vertical slice safe to exercise while the P10 runtime integration is
still being qualified.
"""

from .inventory_mutation import (
    CoalescingAction,
    DEFAULT_MAX_OBSERVATION_AGE_SECONDS,
    INVENTORY_ACTIVATE_OPERATION,
    INVENTORY_PAIR_SCOPE_PREFIX,
    INVENTORY_SET_QUANTITIES_OPERATION,
    InventoryMappingSnapshot,
    InventoryMutationOperation,
    InventoryMutationPayload,
    InventoryObservation,
    InventoryPairScope,
    InventoryPairObservation,
    InventoryPreview,
    FirstPushConfirmation,
    canonical_preview_fingerprint,
    derive_inventory_operation_scope,
    integral_quantity,
)
from .inventory_admission import (
    AdmissionDecision,
    AdmissionReason,
    InventoryAdmissionPolicy,
    evaluate_inventory_admission,
)
from .inventory_coalescing import (
    CoalesceDecision,
    CoalescingDecision,
    decide_inventory_coalescing,
)
from .inventory_readback import (
    MutationReadbackDecision,
    ReadbackDecision,
    ReadbackEvaluator,
    ReadbackOutcome,
    evaluate_inventory_readback,
)

__all__ = [
    "AdmissionDecision",
    "AdmissionReason",
    "CoalescingAction",
    "CoalesceDecision",
    "CoalescingDecision",
    "DEFAULT_MAX_OBSERVATION_AGE_SECONDS",
    "INVENTORY_ACTIVATE_OPERATION",
    "INVENTORY_PAIR_SCOPE_PREFIX",
    "INVENTORY_SET_QUANTITIES_OPERATION",
    "InventoryAdmissionPolicy",
    "InventoryMappingSnapshot",
    "InventoryMutationOperation",
    "InventoryMutationPayload",
    "InventoryObservation",
    "InventoryPairScope",
    "InventoryPairObservation",
    "InventoryPreview",
    "FirstPushConfirmation",
    "MutationReadbackDecision",
    "ReadbackDecision",
    "ReadbackEvaluator",
    "ReadbackOutcome",
    "canonical_preview_fingerprint",
    "derive_inventory_operation_scope",
    "decide_inventory_coalescing",
    "evaluate_inventory_admission",
    "evaluate_inventory_readback",
    "integral_quantity",
]
