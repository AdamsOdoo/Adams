"""Pure exact-pair readback evaluation for P12 inventory mutations.

The evaluator is intentionally conservative.  ``applied`` requires the
requested quantity/zero baseline.  ``not_applied`` is returned only when the
absence of the write is proven (or the V1 location/item safety branch requires
manual review).  Every other observation is ``inconclusive`` and therefore
cannot authorize a blind replay.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from shopify_connector_core.domain.immutability import freeze_value, to_plain

from .inventory_mutation import (
    INVENTORY_ACTIVATE_OPERATION,
    InventoryMutationOperation,
    InventoryMutationPayload,
    InventoryPairObservation,
    _timestamp as _strict_timestamp,
)


class ReadbackOutcome(str, Enum):
    """Remote certainty dispositions from one independent pair read."""

    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    INCONCLUSIVE = "inconclusive"


def _operation(value: Any) -> str:
    try:
        return value.value if isinstance(value, InventoryMutationOperation) else InventoryMutationOperation(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unsupported inventory mutation operation: {value!r}") from exc


def _timestamp(value: Any, field_name: str) -> datetime | None:
    """Parse evidence timestamps; malformed values make proof unavailable."""
    try:
        # Readback proof is stricter than merely being parseable: a naive or
        # non-UTC clock cannot establish ordering with transport_at and must
        # therefore leave the outcome inconclusive.
        return _strict_timestamp(value, field_name, strict=True)
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass(frozen=True, slots=True)
class ReadbackDecision:
    """Result of evaluating an exact item/location pair readback."""

    operation: str | InventoryMutationOperation
    outcome: str | ReadbackOutcome
    operation_scope_key: str
    exact_pair: bool
    safe_to_replay: bool
    reason: str
    message: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", _operation(self.operation))
        try:
            outcome = self.outcome.value if isinstance(self.outcome, ReadbackOutcome) else ReadbackOutcome(self.outcome).value
        except (TypeError, ValueError) as exc:
            raise ValueError("unsupported readback outcome") from exc
        object.__setattr__(self, "outcome", outcome)
        if not isinstance(self.operation_scope_key, str) or not self.operation_scope_key.strip():
            raise ValueError("operation_scope_key must be non-empty")
        if not isinstance(self.exact_pair, bool) or not isinstance(self.safe_to_replay, bool):
            raise TypeError("readback booleans must be bool")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("readback.reason must be non-empty")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("readback.message must be non-empty")
        if not isinstance(self.evidence, Mapping):
            raise TypeError("readback.evidence must be an object")
        object.__setattr__(self, "evidence", freeze_value(dict(self.evidence)))

    @property
    def verdict(self) -> str:
        return self.outcome

    @property
    def replay_allowed(self) -> bool:
        return self.safe_to_replay

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "operation": self.operation,
            "outcome": self.outcome,
            "verdict": self.outcome,
            "operation_scope_key": self.operation_scope_key,
            "exact_pair": self.exact_pair,
            "safe_to_replay": self.safe_to_replay,
            "reason": self.reason,
            "message": self.message,
            "evidence": self.evidence,
        })


class ReadbackEvaluator:
    """Apply V1's applied/not-applied/inconclusive pair-read matrix."""

    @staticmethod
    def _decision(
        payload: InventoryMutationPayload,
        outcome: ReadbackOutcome,
        reason: str,
        message: str,
        *,
        exact_pair: bool,
        safe_to_replay: bool,
        **evidence: Any,
    ) -> ReadbackDecision:
        return ReadbackDecision(
            payload.operation, outcome, payload.operation_scope_key,
            exact_pair, safe_to_replay, reason, message, evidence,
        )

    def evaluate(
        self,
        payload: InventoryMutationPayload,
        observation: InventoryPairObservation | Mapping[str, Any] | None,
        *,
        transport_at: datetime | str | None = None,
    ) -> ReadbackDecision:
        if not isinstance(payload, InventoryMutationPayload):
            raise TypeError("payload must be InventoryMutationPayload")
        if observation is not None and not isinstance(observation, InventoryPairObservation):
            observation = InventoryPairObservation.from_mapping(observation)
        if observation is None:
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "observation_missing",
                "No exact pair readback was returned; no replay is safe.",
                exact_pair=False, safe_to_replay=False,
            )
        exact_pair = (
            observation.store_identity == payload.expected_store_identity
            and observation.inventory_item_gid == payload.inventory_item_gid
            and observation.location_gid == payload.location_gid
        )
        if not exact_pair:
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "identity_mismatch",
                "Readback did not prove the requested store/item/location pair; no replay is safe.",
                exact_pair=False, safe_to_replay=False,
                observed_store_identity=observation.store_identity,
                observed_inventory_item_gid=observation.inventory_item_gid,
                observed_location_gid=observation.location_gid,
            )
        if not observation.fresh:
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "observation_stale",
                "The exact pair readback is stale; no remote outcome or replay is safe.",
                exact_pair=True, safe_to_replay=False,
            )
        if not observation.item_exists:
            return self._decision(
                payload, ReadbackOutcome.NOT_APPLIED, "inventory_item_missing",
                "The exact Shopify InventoryItem is absent; route to review instead of replaying.",
                exact_pair=True, safe_to_replay=False,
            )
        if observation.tracked is not True:
            return self._decision(
                payload, ReadbackOutcome.NOT_APPLIED, "inventory_item_untracked",
                "The exact Shopify InventoryItem is not tracked; route to review.",
                exact_pair=True, safe_to_replay=False,
            )
        if not observation.level_exists:
            replay = payload.operation == INVENTORY_ACTIVATE_OPERATION
            return self._decision(
                payload, ReadbackOutcome.NOT_APPLIED, "inventory_level_missing",
                "The exact Shopify InventoryLevel is absent; activation is required before quantity set." if not replay else "The exact activation effect is not present; a bounded activation successor may be considered.",
                exact_pair=True, safe_to_replay=replay,
            )

        current = observation.available
        if payload.operation == INVENTORY_ACTIVATE_OPERATION:
            if current == 0:
                return self._decision(
                    payload, ReadbackOutcome.APPLIED, "activation_observed",
                    "The exact pair readback proves the accepted zero activation baseline.",
                    exact_pair=True, safe_to_replay=False,
                    current=current, inventory_level_gid=observation.inventory_level_gid,
                )
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "activation_quantity_unexplained",
                "The exact pair exists with a nonzero quantity after activation; no automatic correction is safe.",
                exact_pair=True, safe_to_replay=False, current=current,
            )

        target = payload.normalized_target_quantity
        pre_attempt = payload.change_from_quantity
        if target is None:
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "invalid_quantity",
                "The mutation target is not an integral V1 quantity; no replay is safe.",
                exact_pair=True, safe_to_replay=False,
            )
        if target is not None and current == target:
            return self._decision(
                payload, ReadbackOutcome.APPLIED, "target_observed",
                "The exact pair readback equals the requested target quantity.",
                exact_pair=True, safe_to_replay=False,
                current=current, target=target, inventory_level_gid=observation.inventory_level_gid,
            )
        updated_at = _timestamp(observation.updated_at, "observation.updated_at")
        sent_at = _timestamp(transport_at, "transport_at")
        if pre_attempt is not None and current == pre_attempt and updated_at is not None and sent_at is not None:
            if updated_at <= sent_at:
                return self._decision(
                    payload, ReadbackOutcome.NOT_APPLIED, "pre_attempt_value_unchanged",
                    "The exact pair remains at the pre-attempt quantity with affirmative no-change freshness evidence.",
                    exact_pair=True, safe_to_replay=True,
                    current=current, pre_attempt=pre_attempt,
                )
            return self._decision(
                payload, ReadbackOutcome.INCONCLUSIVE, "aba_or_newer_change",
                "The pair equals the pre-attempt value but changed after transport; this may be an ABA update.",
                exact_pair=True, safe_to_replay=False,
                current=current, pre_attempt=pre_attempt,
            )
        return self._decision(
            payload, ReadbackOutcome.INCONCLUSIVE, "quantity_ambiguous",
            "The exact pair readback neither proves the target nor proves absence of the write; no replay is safe.",
            exact_pair=True, safe_to_replay=False,
            current=current, target=target, pre_attempt=pre_attempt,
        )


def evaluate_inventory_readback(
    payload: InventoryMutationPayload,
    observation: InventoryPairObservation | Mapping[str, Any] | None,
    *,
    transport_at: datetime | str | None = None,
) -> ReadbackDecision:
    """Convenience function for verification adapters and pure tests."""

    return ReadbackEvaluator().evaluate(payload, observation, transport_at=transport_at)


# Descriptive aliases keep the contract discoverable for later runtime wiring.
MutationReadbackDecision = ReadbackDecision


__all__ = [
    "MutationReadbackDecision",
    "ReadbackDecision",
    "ReadbackEvaluator",
    "ReadbackOutcome",
    "evaluate_inventory_readback",
]
