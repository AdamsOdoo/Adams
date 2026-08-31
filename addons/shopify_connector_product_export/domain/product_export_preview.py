"""Freshness and immutable-preview guards for product export apply."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping
from typing import Any

from ._support import PREVIEW_VALIDITY_HOURS, StalePreviewError, fail, gid, parse_datetime, text, utc


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        fail("invalid_fingerprint", f"{name} must be a lowercase SHA-256 digest.")
    return value


@dataclass(frozen=True)
class PreviewSnapshot:
    store_id: str
    connection_generation: int
    fingerprint: str
    created_at: datetime
    expires_at: datetime
    state: str = "previewed"
    source_write_date: datetime | None = None
    remote_updated_at: datetime | None = None
    product_gid: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "store_id", text(self.store_id, "store_id", max_length=256))
        if isinstance(self.connection_generation, bool) or not isinstance(self.connection_generation, int) or self.connection_generation < 0:
            fail("invalid_generation", "connection_generation must be a non-negative integer.")
        object.__setattr__(self, "fingerprint", _digest(self.fingerprint, "fingerprint"))
        object.__setattr__(self, "created_at", utc(self.created_at, "created_at"))
        object.__setattr__(self, "expires_at", utc(self.expires_at, "expires_at"))
        if self.expires_at > self.created_at + timedelta(hours=PREVIEW_VALIDITY_HOURS):
            fail("invalid_preview", "preview expiry cannot exceed the V1 validity window.")
        state = text(self.state, "state", max_length=32)
        if state not in {"previewed", "confirmed", "applying", "applied", "expired", "blocked", "failed"}:
            fail("invalid_preview", "preview state is not supported.")
        object.__setattr__(self, "state", state)
        if self.source_write_date is not None:
            object.__setattr__(self, "source_write_date", utc(self.source_write_date, "source_write_date"))
        if self.remote_updated_at is not None:
            object.__setattr__(self, "remote_updated_at", utc(self.remote_updated_at, "remote_updated_at"))
        if self.product_gid is not None:
            object.__setattr__(self, "product_gid", gid(self.product_gid, "product_gid", kind="Product"))
        if self.scope is not None:
            object.__setattr__(self, "scope", text(self.scope, "scope", max_length=1024))

    @classmethod
    def create(
        cls,
        *,
        store_id: str,
        connection_generation: int,
        fingerprint: str,
        created_at: datetime,
        state: str = "previewed",
        source_write_date: datetime | None = None,
        remote_updated_at: datetime | None = None,
        product_gid: str | None = None,
        scope: str | None = None,
    ) -> "PreviewSnapshot":
        created = utc(created_at, "created_at")
        return cls(store_id, connection_generation, fingerprint, created, created + timedelta(hours=PREVIEW_VALIDITY_HOURS), state, source_write_date, remote_updated_at, product_gid, scope)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreviewSnapshot":
        if not isinstance(value, Mapping):
            fail("invalid_preview", "preview snapshot must be an object.")
        created = parse_datetime(value.get("created_at") or value.get("previewed_at"))
        expires = parse_datetime(value.get("expires_at"))
        if created is None:
            fail("invalid_preview", "Preview created_at is required.")
        if expires is None:
            expires = created + timedelta(hours=PREVIEW_VALIDITY_HOURS)
        return cls(
            store_id=value.get("store_id", ""),
            connection_generation=value.get("connection_generation", value.get("generation", -1)),
            fingerprint=value.get("fingerprint", ""),
            created_at=created,
            expires_at=expires,
            state=value.get("state", "previewed"),
            source_write_date=parse_datetime(value.get("source_write_date")),
            remote_updated_at=parse_datetime(value.get("remote_updated_at") or value.get("remote_updated_at_snapshot")),
            product_gid=value.get("product_gid"),
            scope=value.get("scope"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "connection_generation": self.connection_generation,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "state": self.state,
            "source_write_date": self.source_write_date.isoformat() if self.source_write_date else None,
            "remote_updated_at": self.remote_updated_at.isoformat() if self.remote_updated_at else None,
            "product_gid": self.product_gid,
            "scope": self.scope,
        }


def _stale(reason: str, **details: Any) -> None:
    raise StalePreviewError("stale_preview", "The reviewed product export preview is no longer current.", details={"reason": reason, **details})


def _same_time(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is right
    return left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def reject_stale_preview(
    snapshot: PreviewSnapshot,
    *,
    now: datetime,
    expected_fingerprint: str | None = None,
    current_generation: int | None = None,
    current_source_write_date: datetime | None = None,
    current_remote_updated_at: datetime | None = None,
    current_store_id: str | None = None,
    current_scope: str | None = None,
    require_confirmed: bool = True,
) -> PreviewSnapshot:
    """Raise a typed stale-preview reason; return the same immutable snapshot if fresh."""

    if not isinstance(require_confirmed, bool):
        fail("invalid_boolean", "require_confirmed must be a strict boolean.")
    if not isinstance(snapshot, PreviewSnapshot):
        snapshot = PreviewSnapshot.from_mapping(snapshot)  # type: ignore[arg-type]
    current = utc(now, "now")
    if require_confirmed and snapshot.state not in {"confirmed", "applying"}:
        _stale("not_confirmed", state=snapshot.state)
    if snapshot.state in {"expired", "blocked", "applied", "failed"}:
        _stale("invalid_state", state=snapshot.state)
    if current >= snapshot.expires_at or current >= snapshot.created_at + timedelta(hours=PREVIEW_VALIDITY_HOURS):
        _stale("expired", expires_at=snapshot.expires_at.isoformat())
    if expected_fingerprint is not None and expected_fingerprint != snapshot.fingerprint:
        _stale("fingerprint_mismatch")
    if current_generation is not None and current_generation != snapshot.connection_generation:
        _stale("connection_generation_changed", expected=snapshot.connection_generation, observed=current_generation)
    if current_store_id is not None and current_store_id != snapshot.store_id:
        _stale("store_changed")
    if current_scope is not None and snapshot.scope != current_scope:
        _stale("scope_changed")
    if current_source_write_date is not None:
        source_date = utc(current_source_write_date, "current_source_write_date")
        if snapshot.source_write_date is None or not _same_time(source_date, snapshot.source_write_date):
            _stale("source_changed", source_write_date=source_date.isoformat())
    if current_remote_updated_at is not None:
        remote_date = utc(current_remote_updated_at, "current_remote_updated_at")
        if snapshot.remote_updated_at is None or not _same_time(remote_date, snapshot.remote_updated_at):
            _stale("remote_changed", remote_updated_at=remote_date.isoformat())
    return snapshot


def assert_preview_current(*args: Any, **kwargs: Any) -> PreviewSnapshot:
    return reject_stale_preview(*args, **kwargs)


def stale_preview_guard(*args: Any, **kwargs: Any) -> PreviewSnapshot:
    return reject_stale_preview(*args, **kwargs)


__all__ = ["PreviewSnapshot", "assert_preview_current", "reject_stale_preview", "stale_preview_guard"]
