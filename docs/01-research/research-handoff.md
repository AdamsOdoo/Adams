# Research Sprint A Handoff

> Continuity record for **Research Sprint A — Governance, Research Workspace,
> Source Inventory, and Research Backlog.** The final, complete handoff is
> assembled in Stage 6; the running **Sprint checkpoint log** below is appended
> after each stage.

<!-- The sections below are populated in Stage 6 (Final self-review and handoff). -->

## Session summary

_(Filled in Stage 6.)_

## Branch and commits

_(Filled in Stage 6.)_

## Files created or updated

_(Filled in Stage 6.)_

## What changed

_(Filled in Stage 6.)_

## Evidence and citations added

_(Filled in Stage 6.)_

## Assumptions

_(Filled in Stage 6.)_

## Open questions

_(Filled in Stage 6.)_

## Risks

_(Filled in Stage 6.)_

## Learning feedback loop

_(Filled in Stage 6.)_

## What ChatGPT should review

_(Filled in Stage 6.)_

## Recommended next session

_(Filled in Stage 6.)_

## Stop confirmation

_(Filled in Stage 6.)_

## Sprint self-review

_(Filled in Stage 6.)_

---

## Sprint checkpoint log

> One short note per stage as the sprint progresses (most recent last).

- **Stage 1 — Repo inspection & safe setup (2026-06-30):** Confirmed remote
  default branch is `main` at `68007a9` (clean Odoo scaffold:
  `addons/adams_base`, `README.md`, `.gitignore`; no `docs/`, no `CLAUDE.md`).
  Created the clean branch `docs/research-sprint-a-governance-inventory` from
  `origin/main` (deliberately not from the prior research branch, so this PR
  contains exactly this governance foundation). Created the `/docs/00..08` and
  `/.claude/{skills,agents}` directory structure. No code touched. Next: Stage 2
  governance files.
- **Stage 2 — Governance files (2026-06-30):** Created `CLAUDE.md` (roles:
  Claude=execution/research/docs worker, ChatGPT=strategy/control-room/reviewer;
  GitHub source-of-truth; research-first; no-code-until-approved; small scoped
  sessions; mandatory handoff; citation rules; the fact/competitor-claim/
  inference/recommendation/decision/open-question classification; future
  implementation-task requirements incl. allowed/forbidden files, acceptance
  criteria, tests, rollback, definition of done; and the hard do-not-repeat-
  rejected-approaches rule). Created `AGENTS.md` listing six **proposed** agents
  (competitor-research, shopify-api-research, odoo-architecture-research,
  ux-benchmark, qa-review, prompt-control) — none active. Updated `README.md`
  (preserved existing title/description; added the project workspace map).
  Added `decision-record-template.md`, `pr-review-checklist.md`,
  `implementation-task-template.md`, `pr-review-template.md`, and
  `session-handoff-template.md`. Docs only; no forbidden files. Next: Stage 3
  learning feedback loop.
- **Stage 3 — Learning feedback loop (2026-06-30):** Created
  `quality-feedback-loop.md` (review-decision categories; 17-type issue
  taxonomy; 2×→update-rule / 3×→pause-implementation escalation; concrete-lesson
  rule; end-of-session review; quality + acceptance gates; routing table) and
  the four logs with the exact required columns — `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md` (all initialized empty with instructions). Created
  `claude-learning-rules.md` with the mandatory 7-item pre-session checklist
  (previous handoff, defect log, rejected log, architecture-review log, decision
  records, current phase, allowed/forbidden files). Next: Stage 4 research
  workspace + source inventory.
