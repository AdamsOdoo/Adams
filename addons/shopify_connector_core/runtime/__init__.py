"""Pure runtime contracts and explicit registries; no execution behavior."""

from .contracts import (
    HandlerResult,
    NeedsReview,
    NeedsVerification,
    Retryable,
    Skipped,
    Succeeded,
    TerminalFailure,
)
from .registries import (
    AttentionProviderSpec,
    AttentionRegistry,
    HandlerRegistry,
    JobHandlerSpec,
)

__all__ = [
    "AttentionProviderSpec",
    "AttentionRegistry",
    "HandlerRegistry",
    "HandlerResult",
    "JobHandlerSpec",
    "NeedsReview",
    "NeedsVerification",
    "Retryable",
    "Skipped",
    "Succeeded",
    "TerminalFailure",
]
