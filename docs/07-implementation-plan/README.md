# 07 — Implementation Plan

**Purpose:** the phased implementation plan for the connector.

> **Re-baseline note (2026-07-16, Fable gap-closure mission):** parts of this
> README predate the 2026-07-15 checkpoint and the merged Waves 0/1. Live wave
> status: `mvp-program-state.md`; wave contract: `mvp-completion-program.md`;
> Waves 2–6 Definitions of Ready and the dependency/gate map are the
> `wave-*-definition-of-ready.md` / `waves-2-6-dependency-and-gate-map.md`
> files added by the gap-closure mission.

**What belongs here:** phased plans broken into small, reviewable, independently
testable tasks, each referencing the ADR(s) it implements and the
`../06-prompts/implementation-task-template.md` (allowed/forbidden files,
acceptance criteria, tests, rollback, definition of done).

**What does not belong here yet:** **anything that authorises coding.** Plans
here are **drafts only** until ChatGPT approves the implementation transition
(`CLAUDE.md` §5, §9). No code, no module scaffolding.

**Current status (refreshed 2026-07-10, OP-25 docs-maintenance — the
previous "Empty" status was stale):** Populated. This directory holds the
project's gate corpus: per-task gate documents, gate-opening proposals,
decision closures, and final implementation prompts for Tasks 001–006C and
010 (all of whose gates are now exhausted/closed by their own merged PRs),
the accepted MBQ-55 product- and customer-binding naming proposals, the
customer-domain gate-criteria proposal (accepted as criteria only), the
Task 011/012/013/014 proposed-scope documents, and this session's Task 011
final-prompt/gate-opening package (Proposed, AR-039). **Nothing in this
directory authorizes coding by itself** — every implementation still
requires its own explicit ChatGPT gate-opening act and an explicitly issued
final prompt (`CLAUDE.md` §5, §9). Authoritative per-task statuses live in
each file's own Status section and `../05-qa/architecture-review-log.md`;
this note refreshes the stale index text only and decides nothing.
