#!/usr/bin/env python3
"""Enforce the V2 changed-production-file size contract.

New production files may not exceed 750 lines.  A V1 hotspot that already
exceeded that ceiling may be touched only when it stays the same size or gets
smaller.  The comparison base is the immutable V1 SHA recorded by the journey
baseline, so regenerating V2 evidence cannot silently move the goalposts.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_CHANGED_PRODUCTION_LINES = 750
PRODUCTION_SUFFIXES = frozenset({".py", ".js", ".xml", ".scss"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SizeViolation:
    path: str
    current_lines: int
    baseline_lines: int | None
    message: str

    def format(self) -> str:
        baseline = (
            "new" if self.baseline_lines is None else str(self.baseline_lines)
        )
        return (
            f"{self.path}: change-size: {self.message} "
            f"(current={self.current_lines}, baseline={baseline})"
        )


def _git(root: Path, *args: str, text: bool = True):
    return subprocess.check_output(
        ["git", *args], cwd=root, text=text, stderr=subprocess.PIPE,
    )


def _line_count(data: bytes) -> int:
    return len(data.splitlines())


def _is_production_path(path: str) -> bool:
    candidate = Path(path)
    if not path.startswith("addons/") or candidate.suffix not in PRODUCTION_SUFFIXES:
        return False
    parts = set(candidate.parts)
    return "tests" not in parts and "migrations" not in parts


def _changed_paths(root: Path, base_sha: str) -> tuple[str, ...]:
    tracked = _git(
        root, "diff", "--name-only", "--diff-filter=ACMRT", base_sha, "--", "addons",
    ).splitlines()
    untracked = _git(
        root, "ls-files", "--others", "--exclude-standard", "addons",
    ).splitlines()
    return tuple(sorted(set(tracked + untracked)))


def _baseline_lines(root: Path, base_sha: str, path: str) -> int | None:
    try:
        data = _git(root, "show", f"{base_sha}:{path}", text=False)
    except subprocess.CalledProcessError:
        return None
    return _line_count(data)


def check_change_sizes(root: Path, base_sha: str) -> list[SizeViolation]:
    root = root.resolve()
    if not SHA_RE.fullmatch(base_sha):
        raise ValueError("baseline SHA must be a full lowercase Git SHA")
    try:
        _git(root, "cat-file", "-e", f"{base_sha}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise ValueError("baseline SHA is not available in repository history") from exc

    violations: list[SizeViolation] = []
    for relative in _changed_paths(root, base_sha):
        if not _is_production_path(relative):
            continue
        path = root / relative
        if not path.is_file():
            continue
        current = _line_count(path.read_bytes())
        baseline = _baseline_lines(root, base_sha, relative)
        if baseline is None or baseline <= MAX_CHANGED_PRODUCTION_LINES:
            if current > MAX_CHANGED_PRODUCTION_LINES:
                violations.append(SizeViolation(
                    relative,
                    current,
                    baseline,
                    f"new/extracted production files must be <= "
                    f"{MAX_CHANGED_PRODUCTION_LINES} lines",
                ))
        elif current > baseline:
            violations.append(SizeViolation(
                relative,
                current,
                baseline,
                "a pre-existing hotspot may not grow during V2 extraction",
            ))
    return violations


def _recorded_base(root: Path) -> str:
    path = root / "docs" / "v2" / "evidence" / "journey-baseline.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))["source_v1_sha"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            "journey baseline must contain the immutable source_v1_sha"
        ) from exc
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError("journey baseline source_v1_sha is malformed")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-sha")
    args = parser.parse_args(argv)
    try:
        base_sha = args.base_sha or _recorded_base(args.repo_root.resolve())
        violations = check_change_sizes(args.repo_root, base_sha)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"v2 change-size policy: error: {exc}", file=sys.stderr)
        return 2
    if violations:
        for violation in violations:
            print(violation.format())
        print(f"v2 change-size policy: {len(violations)} violation(s)")
        return 1
    print("v2 change-size policy: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
