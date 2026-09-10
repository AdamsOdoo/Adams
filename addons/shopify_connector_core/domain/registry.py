"""Explicit duplicate-safe registries used by V2 extension seams."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import Generic, TypeVar

from .identifiers import require_key


T = TypeVar("T")


class RegistryError(Exception):
    """Base class for fail-closed registration errors."""


class DuplicateRegistryKey(RegistryError, ValueError):
    """Raised when registration would silently replace an existing contract."""


class UnknownRegistryKey(RegistryError, KeyError):
    """Raised when a caller asks for an unregistered contract."""


class RegistryFrozen(RegistryError, RuntimeError):
    """Raised when registration is attempted after a registry is frozen."""


class Registry(Generic[T]):
    """A deliberately small explicit key-to-contract registry.

    There is no import discovery, reflection, fallback handler or arbitrary
    model lookup.  A key must be registered exactly once and lookup callers
    that require a value use :meth:`require`, which fails closed.
    """

    def __init__(self, entries: Iterable[tuple[str, T]] = ()) -> None:
        self._entries: dict[str, T] = {}
        self._frozen = False
        # Use the base bulk primitive rather than dynamic dispatch. A typed
        # registry may expose ``register_many(specs)`` with a different shape.
        Registry.register_many(self, entries)

    def _register_pair(self, key: str, value: T) -> T:
        if self._frozen:
            raise RegistryFrozen("registry is frozen")
        require_key(key)
        if key in self._entries:
            raise DuplicateRegistryKey(f"registry key already registered: {key}")
        self._entries[key] = value
        return value

    def register(self, key: str, value: T) -> T:
        return self._register_pair(key, value)

    def register_many(self, entries: Iterable[tuple[str, T]]) -> None:
        if self._frozen:
            raise RegistryFrozen("registry is frozen")
        staged = list(entries)
        staged_keys = []
        for pair in staged:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise TypeError("registry entries must be key/value pairs")
            key, _value = pair
            require_key(key)
            staged_keys.append(key)
        if len(set(staged_keys)) != len(staged_keys):
            raise DuplicateRegistryKey(
                "bulk registration contains a duplicate registry key"
            )
        conflicts = sorted(set(staged_keys).intersection(self._entries))
        if conflicts:
            raise DuplicateRegistryKey(
                "registry key already registered: %s" % conflicts[0]
            )
        # Mutate only after the full iterable has been materialized and every
        # key validated, so a generator error or late duplicate is atomic.
        self._entries.update((key, value) for key, value in staged)

    def freeze(self) -> None:
        self._frozen = True

    @property
    def frozen(self) -> bool:
        return self._frozen

    def get(self, key: str, default: T | None = None) -> T | None:
        return self._entries.get(key, default)

    def require(self, key: str) -> T:
        try:
            return self._entries[key]
        except KeyError as exc:
            raise UnknownRegistryKey(f"unknown registry key: {key}") from exc

    def __getitem__(self, key: str) -> T:
        return self.require(key)

    def __contains__(self, key: object) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[str]:
        return iter(self._entries)

    def keys(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def values(self) -> tuple[T, ...]:
        return tuple(self._entries.values())

    def items(self) -> tuple[tuple[str, T], ...]:
        return tuple(self._entries.items())

    def snapshot(self) -> Mapping[str, T]:
        return MappingProxyType(dict(self._entries))


__all__ = [
    "DuplicateRegistryKey",
    "Registry",
    "RegistryError",
    "RegistryFrozen",
    "UnknownRegistryKey",
]
