# 03 — Architecture

**Purpose:** architecture notes, diagrams, data models, and sync-design
**drafts** for the connector.

**What belongs here:** `architecture-preparation.md` and later draft designs
(sync orchestration, mapping/idempotency, scheduling/queueing, modularity
boundaries).

**What does not belong here yet:** finalized decisions (those become ADRs in
`../04-decisions/` after review) and any code. Architecture is **gated** until
research is sufficient and ChatGPT approves the transition (`CLAUDE.md` §4–§5).

**Current status:** Contains RB-14 Part 1 + Part 2 **pre-decision framing and
decision-candidate** documents — `architecture-decision-framing.md`,
`ar-002-distribution-api-framing.md`, `ar-003-sync-orchestration-framing.md`,
`ar-005-binding-dedup-framing.md`, `rb14-official-source-refresh.md`,
`rb14-part2-open-question-resolution.md`, `rb14-decision-candidate-brief.md`.
**AR-002/AR-003/AR-005 are framed and narrowed to candidates — still "Not
decided / Evidence pending."** AR-004/006/007/008 not yet framed. No ADR
exists here yet (ADRs live in `../04-decisions/` only after acceptance);
proposals are tracked in `../05-qa/architecture-review-log.md`.
