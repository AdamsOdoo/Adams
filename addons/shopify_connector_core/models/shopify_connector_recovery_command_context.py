"""Typed targets shared by the P04 recovery command adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..application.command_contracts import CommandEnvelope


@dataclass(frozen=True)
class _RecoveryContext:
    envelope: CommandEnvelope
    expected_configuration_generation: int | None
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class _Target:
    job: Any
    run: Any = None
    store: Any = None

    @property
    def is_v2(self) -> bool:
        return bool(self.run or getattr(self.job, "run_id", False))

    @property
    def run_ref(self) -> str:
        run = self.run or getattr(self.job, "run_id", False)
        if run:
            return "run:%d" % run.id
        if not self.job:
            raise ValueError("a recovery target must have a job or run")
        return "job:%d" % self.job.id
