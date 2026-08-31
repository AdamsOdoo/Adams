"""Pure V2 application contracts; intentionally not wired into Odoo."""

from .command_contracts import CommandEnvelope, CommandResult
from .registry import (
    DuplicateRegistryKey,
    Registry,
    RegistryError,
    RegistryFrozen,
    UnknownRegistryKey,
)

__all__ = [
    "CommandEnvelope",
    "CommandResult",
    "DuplicateRegistryKey",
    "Registry",
    "RegistryError",
    "RegistryFrozen",
    "UnknownRegistryKey",
]
