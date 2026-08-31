"""Application-facing import location for the shared explicit registry."""

from ..domain.registry import (
    DuplicateRegistryKey,
    Registry,
    RegistryError,
    RegistryFrozen,
    UnknownRegistryKey,
)

__all__ = [
    "DuplicateRegistryKey",
    "Registry",
    "RegistryError",
    "RegistryFrozen",
    "UnknownRegistryKey",
]
