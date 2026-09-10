"""Immutable V2 vocabularies.

This module deliberately contains no Odoo imports and no execution logic.  The
values are the public vocabulary that adapters and DTOs will use while the
legacy models remain authoritative during the staged migration.
"""

from __future__ import annotations

from enum import Enum


class _ValueEnum(str, Enum):
    """String enum whose values are safe to place in a JSON contract."""

    def __str__(self) -> str:
        return self.value


class CommandStatus(_ValueEnum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CONFLICT = "conflict"
    DUPLICATE = "duplicate"


class TriggerType(_ValueEnum):
    USER = "user"
    CRON = "cron"
    WEBHOOK = "webhook"
    ODOO_EVENT = "odoo_event"
    RECONCILIATION = "reconciliation"
    SYSTEM = "system"


class ExecutionMode(_ValueEnum):
    EXECUTE = "execute"
    PREVIEW = "preview"


class OperationMode(_ValueEnum):
    READ = "read"
    PREVIEW = "preview"
    MUTATION = "mutation"
    RECONCILIATION = "reconciliation"


class OperationType(_ValueEnum):
    QUERY = "query"
    MUTATION = "mutation"


class StoreConnectionState(_ValueEnum):
    UNCONFIGURED = "unconfigured"
    TESTING = "testing"
    CONNECTED = "connected"
    INVALID = "invalid"
    DISCONNECTED = "disconnected"


class StoreConfigurationState(_ValueEnum):
    INCOMPLETE = "incomplete"
    VALID = "valid"
    STALE = "stale"


class StoreActivationState(_ValueEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class RuntimeHealth(_ValueEnum):
    HEALTHY = "healthy"
    ATTENTION_REQUIRED = "attention_required"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class WorkflowReadiness(_ValueEnum):
    DISABLED = "disabled"
    NOT_READY = "not_ready"
    READY = "ready"
    PAUSED = "paused"


class RunState(_ValueEnum):
    REQUESTED = "requested"
    ADMITTED = "admitted"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED_RETRYABLE = "failed_retryable"
    BLOCKED_MANUAL_REVIEW = "blocked_manual_review"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"


class JobState(_ValueEnum):
    """The existing physical job values, preserved during migration."""

    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED_FINAL = "failed_final"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRY_WAITING = "retry_waiting"
    FAILED_RETRYABLE = "failed_retryable"
    BLOCKED_MANUAL_REVIEW = "blocked_manual_review"


class AttemptOutcome(_ValueEnum):
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_SCHEDULED = "retry_scheduled"
    VERIFICATION_REQUIRED = "verification_required"
    MANUAL_REVIEW = "manual_review"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"
    OWNER_LOST = "owner_lost"


class RetryDecision(_ValueEnum):
    RETRY = "retry"
    VERIFY = "verify"
    REVIEW = "review"
    TERMINAL = "terminal"
    NONE = "none"


class MutationObservedOutcome(_ValueEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED_CLEAN = "failed_clean"
    UNCERTAIN = "uncertain"


class MerchantWriteStatus(_ValueEnum):
    QUEUED = "queued"
    SENDING = "sending"
    ACCEPTED = "accepted"
    VERIFIED = "verified"
    NEEDS_ATTENTION = "needs_attention"
    REJECTED = "rejected"


class MutationResolutionDisposition(_ValueEnum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"


class MutationResolutionSource(_ValueEnum):
    RECONCILIATION_READ = "reconciliation_read"
    MANUAL_ADMIN = "manual_admin"


class PriorityLane(_ValueEnum):
    SAFETY_VERIFICATION = "safety_verification"
    INTERACTIVE = "interactive"
    WEBHOOK = "webhook"
    ODOO_EVENT = "odoo_event"
    SCHEDULED = "scheduled"
    RECONCILIATION = "reconciliation"


class Role(_ValueEnum):
    ADMINISTRATOR = "administrator"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


ROLE_ORDER = (
    Role.ADMINISTRATOR,
    Role.OPERATOR,
    Role.REVIEWER,
    Role.AUDITOR,
)


class SetupStepKey(_ValueEnum):
    """Semantic durable setup identifiers; display ordinals are not addresses."""

    WELCOME = "welcome"
    IDENTITY = "identity"
    CREDENTIAL = "credential"
    SCOPES = "scopes"
    TEST_CONNECTION = "test_connection"
    DIRECTIONS = "directions"
    LOCATION_MAPPING = "location_mapping"
    SOURCE_OF_TRUTH = "source_of_truth"
    NOTIFICATION = "notification"
    FIRST_PUSH = "first_push"
    FINAL_READINESS = "final_readiness"
    REVIEW = "review"


SETUP_STEP_KEYS = tuple(item.value for item in SetupStepKey)
SETUP_STEP_ENUMS = tuple(SetupStepKey)
SETUP_STEP_ORDINALS = {
    key: ordinal for ordinal, key in enumerate(SETUP_STEP_KEYS, start=1)
}
SETUP_PHASES = (
    (SetupStepKey.WELCOME.value, SetupStepKey.IDENTITY.value, SetupStepKey.CREDENTIAL.value),
    (SetupStepKey.SCOPES.value, SetupStepKey.TEST_CONNECTION.value),
    (SetupStepKey.DIRECTIONS.value,),
    (SetupStepKey.LOCATION_MAPPING.value,),
    (
        SetupStepKey.SOURCE_OF_TRUTH.value,
        SetupStepKey.NOTIFICATION.value,
        SetupStepKey.FIRST_PUSH.value,
    ),
    (SetupStepKey.FINAL_READINESS.value, SetupStepKey.REVIEW.value),
)


# This is an interim supported-capacity contract, not an unlimited-capacity
# claim.  A measured capacity decision may raise or lower it in a later ADR.
SUPPORTED_STORE_CAPACITY = 10
MAX_SUPPORTED_STORES = SUPPORTED_STORE_CAPACITY


__all__ = [
    "AttemptOutcome",
    "CommandStatus",
    "ExecutionMode",
    "JobState",
    "MerchantWriteStatus",
    "MutationObservedOutcome",
    "MutationResolutionDisposition",
    "MutationResolutionSource",
    "OperationMode",
    "OperationType",
    "PriorityLane",
    "RetryDecision",
    "Role",
    "ROLE_ORDER",
    "RunState",
    "RuntimeHealth",
    "SETUP_PHASES",
    "SETUP_STEP_KEYS",
    "SETUP_STEP_ENUMS",
    "SETUP_STEP_ORDINALS",
    "SetupStepKey",
    "StoreActivationState",
    "StoreConfigurationState",
    "StoreConnectionState",
    "SUPPORTED_STORE_CAPACITY",
    "MAX_SUPPORTED_STORES",
    "TriggerType",
    "WorkflowReadiness",
]
