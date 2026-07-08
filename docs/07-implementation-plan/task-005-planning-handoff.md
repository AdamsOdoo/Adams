# Task 005 Planning Handoff

> Session-specific handoff for the Task 005 gate-proposal package. This is a
> **standalone** handoff document, separate from the rolling
> `../01-research/research-handoff.md`, because that file is currently owned
> by the parallel, not-yet-merged PR #117 (`claude/token-acquisition-val-b2-5zi8bg`)
> and is out of scope for this session by explicit instruction.

## Branch name

`claude/task-005-gate-proposal-daa49e`, branched from `origin/Shopify-connector`.

## Base commit confirmed

`f4a6ace519bed1073d9b76e0fd91823e03ab7a59` ("Merge pull request #116: Task
004 acceptance and TD-001 closure docs") — confirmed as the current
`Shopify-connector` HEAD via `git fetch origin Shopify-connector` and
`git merge-base --is-ancestor f4a6ace... origin/Shopify-connector` before
branching.

## Files changed

Exactly 3, all newly created, all docs-only:

- `docs/07-implementation-plan/task-005-gate-proposal.md` (new)
- `docs/04-decisions/DEC-022-task-005-scope.md` (new)
- `docs/07-implementation-plan/task-005-planning-handoff.md` (new, this file)

No other file touched.

## Recommended Task 005 scope

**Connection lifecycle actions** — `activate`, `disconnect`, `reconnect`,
`reconnect_needed` auto-transition, and the `perm_create` store/settings ACL
decision. Service/model layer only; no UI. Full comparison against five
other candidates (token acquisition/VAL-B2 closure, setup wizard/connection
UX, queue/job runner execution layer, store configuration/readiness
display, product sync foundation) in `task-005-gate-proposal.md` §3–§6;
formal proposal in `../04-decisions/DEC-022-task-005-scope.md`.

## Why it was chosen

1. It is the only compared candidate whose named prerequisites (Tasks 002,
   003, 004) are already merged and reviewed.
2. It already carries an existing, implementation-planning-level ChatGPT
   acceptance under this exact name and number
   (`credential-connection-foundation-task-plan.md`, AR-024, PR #92,
   accepted 2026-07-06) — this proposal reconciles with that prior
   acceptance rather than silently deviating from it.
3. `mvp-domain-implementation-sequence.md`'s own accepted dependency
   analysis names Task 005 as the specific mechanism (store-state gating)
   that determines whether any domain sync job may be enqueued at all — the
   direction every other still-blocked candidate cites as its own remaining
   dependency.
4. It requires neither the (still-closed) UI implementation gate nor MBQ-05's
   resolution nor VAL-B2 passing.

Full reasoning, dependency diagram, and risk table: `task-005-gate-proposal.md`
§4–§7.

## Known dependencies on PR #117 / DEC-023

**None that block Task 005.** Analyzed in full in `task-005-gate-proposal.md`
§16:

- If PR #117/DEC-023 is accepted: no change to Task 005's recommended
  scope — `reconnect`'s test/readiness steps call the existing Task 003/004
  substrate regardless of which token-acquisition mechanism is eventually
  chosen. Acceptance would primarily affect the later Task 006 (wizard).
- If PR #117/DEC-023 is revised or rejected: Task 005 is **not blocked** —
  nothing in this proposal assumes a particular token-acquisition mechanism.
- This session did not read, cite as decided, or modify any of PR #117's
  four files beyond the read-only verification needed to describe its
  current (draft, unaccepted) state accurately.

## VAL-B2 status

**Deferred, not passed.** Unchanged by this session. No live Shopify
connection was attempted or claimed. Per
`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`, VAL-B2 remains
"not passed, not failed, and not waived."

## MBQ-05 status

**Open, not resolved.** Unchanged by this session. This proposal's
recommended Task 005 scope does not require MBQ-05's resolution (see
"Why it was chosen," point 4).

## No code changed

Confirmed: no `addons/` file, no Python, no XML, no CSV, no manifest/
security/migration/CI file created or modified. No OAuth, setup wizard, UI,
or sync code of any kind exists in this branch beyond what was already
merged into `Shopify-connector`.

## Task 005 not implemented

Confirmed: this package is a proposal only. No Task 005 gate has been
opened; no Task 005 implementation task prompt has been issued or accepted;
no Task 005 code exists anywhere in this repository.

## Validation performed before commit

1. Confirmed only the 3 allowed docs files changed (`git status` /
   `git diff --name-only` against the allow-list).
2. Confirmed no `addons/` file changed.
3. Confirmed no code file (Python/XML/CSV/manifest/security/migration/CI)
   changed.
4. Confirmed no PR #117 file
   (`docs/01-research/research-handoff.md`,
   `docs/01-research/shopify-token-acquisition-notes.md`,
   `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md`,
   `docs/05-qa/val-b2-closure-plan.md`) was touched.
5. Confirmed no OAuth/setup wizard/UI/sync implementation was created
   anywhere in this branch.
6. Confirmed VAL-B2 is not marked passed anywhere in this package (grepped
   every mention across all 3 new files).
7. Confirmed MBQ-05 is not marked resolved anywhere in this package.
8. Confirmed `DEC-022-task-005-scope.md`'s Status line reads "Proposed, not
   accepted."
9. Confirmed Task 005 is not implemented — no code file of any kind exists
   in this branch beyond the 3 new docs files.

## Next step

**ChatGPT review.** This PR must not be merged, and must not be marked
ready for review, except by later ChatGPT/control-room instruction. If
accepted, the next act is a separate, explicit Task 005 gate-opening
document (mirroring `task-004-readiness-check-substrate-gate.md`), followed
by a final `CLAUDE.md` §9 implementation task prompt — neither exists yet.
