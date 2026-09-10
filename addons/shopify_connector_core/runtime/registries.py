"""Explicit runtime handler and attention-provider registries."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from ..domain.identifiers import require_key
from ..domain.registry import Registry
from ..domain.states import PriorityLane, Role


@dataclass(frozen=True, slots=True)
class JobHandlerSpec:
    """Typed metadata for one executable job type."""

    job_type: str
    addon: str
    lane: str | PriorityLane
    mutation: bool
    required_role: str | None
    readiness_keys: tuple[str, ...]
    payload_schema: Any
    handler_factory: Callable[..., Any]
    verification_factory: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        require_key(self.job_type, "job_type")
        require_key(self.addon, "addon")
        lane = self.lane.value if isinstance(self.lane, PriorityLane) else self.lane
        if lane not in {item.value for item in PriorityLane}:
            raise ValueError(f"unsupported priority lane: {lane!r}")
        if not isinstance(self.mutation, bool):
            raise TypeError("mutation must be bool")
        if self.required_role is not None:
            try:
                role = self.required_role if isinstance(self.required_role, Role) else Role(self.required_role)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unsupported required_role: {self.required_role!r}") from exc
            object.__setattr__(self, "required_role", role.value)
        if isinstance(self.readiness_keys, (str, bytes)) or not isinstance(
            self.readiness_keys, (list, tuple)
        ):
            raise TypeError("readiness_keys must be a sequence of keys")
        readiness_keys = tuple(self.readiness_keys)
        for key in readiness_keys:
            require_key(key, "readiness key")
        if len(set(readiness_keys)) != len(readiness_keys):
            raise ValueError("readiness_keys must be unique")
        object.__setattr__(self, "readiness_keys", readiness_keys)
        if self.payload_schema is None:
            raise ValueError("payload_schema is required")
        if not callable(self.handler_factory):
            raise TypeError("handler_factory must be callable")
        if self.mutation and self.verification_factory is None:
            raise ValueError("mutation handlers require a verification_factory")
        if self.verification_factory is not None and not callable(self.verification_factory):
            raise TypeError("verification_factory must be callable or None")
        object.__setattr__(self, "lane", lane)


@dataclass(frozen=True, slots=True)
class AttentionProviderSpec:
    """Typed registration metadata for one domain-owned attention provider."""

    provider_key: str
    workflow: str
    provider_factory: Callable[..., Any]
    action_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_key(self.provider_key, "provider_key")
        require_key(self.workflow, "workflow")
        if not callable(self.provider_factory):
            raise TypeError("provider_factory must be callable")
        if isinstance(self.action_keys, (str, bytes)) or not isinstance(
            self.action_keys, (list, tuple)
        ):
            raise TypeError("action_keys must be a sequence of keys")
        action_keys = tuple(self.action_keys)
        for key in action_keys:
            require_key(key, "action key")
        if len(set(action_keys)) != len(action_keys):
            raise ValueError("action_keys must be unique")
        object.__setattr__(self, "action_keys", action_keys)


class HandlerRegistry(Registry[JobHandlerSpec]):
    """No fallback handler: unknown job types fail closed."""

    def __init__(self, specs: Iterable[JobHandlerSpec] = ()) -> None:
        super().__init__()
        self.register_many(specs)

    def register(self, spec: JobHandlerSpec) -> JobHandlerSpec:  # type: ignore[override]
        if not isinstance(spec, JobHandlerSpec):
            raise TypeError("handler registry accepts JobHandlerSpec only")
        return super().register(spec.job_type, spec)

    def register_many(self, specs: Iterable[JobHandlerSpec]) -> None:  # type: ignore[override]
        staged = list(specs)
        if any(not isinstance(spec, JobHandlerSpec) for spec in staged):
            raise TypeError("handler registry accepts JobHandlerSpec only")
        Registry.register_many(
            self, ((spec.job_type, spec) for spec in staged),
        )

    def require_handler(self, job_type: str) -> JobHandlerSpec:
        return self.require(job_type)


class AttentionRegistry(Registry[AttentionProviderSpec]):
    """No implicit provider discovery or arbitrary model lookup."""

    def __init__(self, specs: Iterable[AttentionProviderSpec] = ()) -> None:
        super().__init__()
        self.register_many(specs)

    def register(self, spec: AttentionProviderSpec) -> AttentionProviderSpec:  # type: ignore[override]
        if not isinstance(spec, AttentionProviderSpec):
            raise TypeError("attention registry accepts AttentionProviderSpec only")
        return super().register(spec.provider_key, spec)

    def register_many(self, specs: Iterable[AttentionProviderSpec]) -> None:  # type: ignore[override]
        staged = list(specs)
        if any(not isinstance(spec, AttentionProviderSpec) for spec in staged):
            raise TypeError(
                "attention registry accepts AttentionProviderSpec only"
            )
        Registry.register_many(
            self, ((spec.provider_key, spec) for spec in staged),
        )

    def require_provider(self, provider_key: str) -> AttentionProviderSpec:
        return self.require(provider_key)


__all__ = [
    "AttentionProviderSpec",
    "AttentionRegistry",
    "HandlerRegistry",
    "JobHandlerSpec",
]
