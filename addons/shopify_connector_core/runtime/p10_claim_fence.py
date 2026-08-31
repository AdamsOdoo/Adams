"""Dependency-free predicate for exact P10 network-read ownership."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from ..domain.runtime_modes import runtime_mode_includes
from .p10_coordinator import ClaimedWork


_ACTIVE_RUN_STATES = ("admitted", "running", "waiting")
_READ_ONLY_CAPABILITY = "read_only"


@dataclass(frozen=True, slots=True)
class JobClaimState:
    id: int
    store_id: int
    company_id: int
    job_type: str
    job_source: str
    state: str
    claim_token: str | None
    worker_ref: str | None
    connection_generation: int
    configuration_generation: int
    run_id: int
    lane: str
    operation_scope_key: str | None
    mutation_attempt_id: int | None


@dataclass(frozen=True, slots=True)
class AttemptClaimState:
    attempt_no: int
    claim_token: str
    worker_ref: str
    outcome: str
    run_id: int


@dataclass(frozen=True, slots=True)
class RunClaimState:
    store_id: int
    company_id: int
    state: str
    cancel_requested_at: object | None
    connection_generation: int
    configuration_generation: int


@dataclass(frozen=True, slots=True)
class StoreClaimState:
    company_id: int
    state: str
    connection_generation: int
    shop_domain: str | None
    api_version: str | None


@dataclass(frozen=True, slots=True)
class SettingsClaimState:
    company_id: int
    configuration_generation: int
    runtime_mode: str


@dataclass(frozen=True, slots=True)
class ReadClaimSnapshot:
    job: JobClaimState
    attempt: AttemptClaimState
    run: RunClaimState
    store: StoreClaimState
    settings: SettingsClaimState

    @property
    def endpoint(self) -> tuple[str | None, str | None]:
        return self.store.shop_domain, self.store.api_version


def read_claim_matches(
    snapshot: ReadClaimSnapshot,
    claim: ClaimedWork,
    company_ids: Collection[int],
) -> bool:
    """Whether one ordered-lock snapshot still belongs to the claim."""

    if (
        not isinstance(snapshot, ReadClaimSnapshot)
        or not isinstance(claim, ClaimedWork)
        or claim.mutation
        or claim.run_id is None
        or claim.company_id is None
    ):
        return False
    job = snapshot.job
    attempt = snapshot.attempt
    run = snapshot.run
    store = snapshot.store
    settings = snapshot.settings
    try:
        mode_allowed = runtime_mode_includes(
            settings.runtime_mode, _READ_ONLY_CAPABILITY,
        )
    except (TypeError, ValueError):
        return False
    return bool(
        claim.company_id in company_ids
        and job.id == claim.job_id
        and job.store_id == claim.store_id
        and job.company_id == claim.company_id
        and job.job_type == claim.handler_key
        and job.state == "running"
        and job.claim_token == claim.claim_token
        and job.worker_ref == claim.worker_ref
        and job.connection_generation == claim.expected_generation
        and job.configuration_generation
        == claim.expected_configuration_generation
        and job.run_id == claim.run_id
        and job.lane == claim.lane
        and (job.operation_scope_key or None) == claim.operation_scope_key
        and not job.mutation_attempt_id
        and attempt.attempt_no == claim.attempt_no
        and attempt.claim_token == claim.claim_token
        and attempt.worker_ref == claim.worker_ref
        and attempt.outcome == "running"
        and attempt.run_id == claim.run_id
        and run.store_id == claim.store_id
        and run.company_id == claim.company_id
        and run.state in _ACTIVE_RUN_STATES
        and not run.cancel_requested_at
        and run.connection_generation == claim.expected_generation
        and run.configuration_generation
        == claim.expected_configuration_generation
        and store.company_id == claim.company_id
        and store.state == "connected"
        and store.connection_generation == claim.expected_generation
        and bool(store.shop_domain)
        and bool(store.api_version)
        and settings.company_id == claim.company_id
        and settings.configuration_generation
        == claim.expected_configuration_generation
        and mode_allowed
    )


__all__ = [
    "AttemptClaimState",
    "JobClaimState",
    "ReadClaimSnapshot",
    "RunClaimState",
    "SettingsClaimState",
    "StoreClaimState",
    "read_claim_matches",
]
