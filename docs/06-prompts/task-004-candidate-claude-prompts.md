# Task 004 — Candidate Claude Prompts (Draft Set)

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.
>
> Every prompt below is a **draft candidate only**. None of them is
> authorized. None of them may be pasted into a Claude Code session and run
> as-is. Each one requires, at minimum: (1) Task 003 validation accepted by
> ChatGPT, (2) the MBQ-05 token-acquisition direction accepted or explicitly
> deferred, (3) a separate, explicit Task 004 gate-opening act merged into
> `Shopify-connector` (following the `task-002-credential-storage-gate.md` /
> `task-003-api-client-test-connection-gate.md` precedent), and (4) every
> placeholder below filled in with ChatGPT-reviewed specifics before the
> prompt is issued. See
> [`../07-implementation-plan/task-004-readiness-preflight.md`](../07-implementation-plan/task-004-readiness-preflight.md)
> and
> [`../07-implementation-plan/task-004-dependency-map.md`](../07-implementation-plan/task-004-dependency-map.md)
> for the full gating context.

## Status

Prepared 2026-07-07, docs-only, as part of the Task 004 readiness preflight
package. Branch `claude/task-004-readiness-preflight-vgbkt3`; revised
2026-07-07 on branch `claude/task-004-gate-opening-w3f1zg` to add the
DEC-021 warning banner above each candidate. This document does not open
any gate and does not itself constitute a §9 implementation task per
`CLAUDE.md` §9 — it is a set of **shaped drafts** for whatever future
session actually writes the binding prompt. **No code is authorized by
this file, by DEC-021, or by the Task 004 gate-opening package prepared
alongside it — this document remains draft-only and not runnable.**

None of these prompts says "build the connector," and none authorizes broad
implementation. Each is deliberately narrow, mirroring the small-PR
discipline already used for Tasks 002 and 003
(`task-002-final-implementation-prompt.md`,
`task-003-final-implementation-prompt.md`).

---

## How to use this document (for the future session that eventually does)

1. Confirm all four preconditions in the banner above are actually true —
   do not assume they are because this document exists.
2. Pick the single next candidate prompt in sequence (004A before 004B,
   004B before 004C, etc.) — do not skip ahead.
3. Fill in every `<PLACEHOLDER>` below with the exact, ChatGPT-reviewed
   specifics for that slice — allowed files, forbidden files, acceptance
   criteria, tests, rollback notes, definition of done. An unfilled
   placeholder means the prompt is not ready to issue.
4. Have ChatGPT review the filled-in prompt itself, separately from
   reviewing this draft-shape document, before it is issued to any
   implementation session.
5. Issue prompts one at a time. Each stops at its own scoped boundary
   (`CLAUDE.md` §6) — do not chain 004A directly into 004B in the same
   session.

---

## Candidate 004A — Finalize accepted scope and allowed files only

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.

> **Purpose:** a docs-only session that converts the candidate scope in
> `task-004-readiness-preflight.md` §4 into a binding, ChatGPT-accepted Task
> 004 scope document and gate-opening act — mirroring
> `task-003-gate-opening-proposal.md` → `task-003-api-client-test-connection-gate.md`.
> **This candidate does not write any code.**

```text
You are Claude Code preparing (NOT implementing) Task 004 for the Odoo 19
Shopify Connector. This is a DOCS-ONLY session. Do not write any addon
code, test, manifest, security, or migration file.

Preconditions (confirm all before starting; stop and report if any is
false):
- Task 003 manual validation has been reviewed and accepted by ChatGPT
  (not merely "partial results recorded").
- MBQ-05 (token-acquisition direction) has been accepted or explicitly
  deferred by ChatGPT.
- TD-001's routing decision (folded into this gate by name, or a separate
  follow-up patch) has been made by ChatGPT — <PLACEHOLDER: state which>.
- MBQ-06's residual thresholds/copy/XML-ID decisions are ready to be fixed
  in this task's own scope document — <PLACEHOLDER: cite the ChatGPT
  guidance or decision to use>.

Task: Finalize the Task 004 ("Readiness check substrate") scope document
and prepare (but do not merge without ChatGPT's own explicit act) a gate-
opening document mirroring
`docs/07-implementation-plan/task-003-api-client-test-connection-gate.md`.

Allowed files: <PLACEHOLDER — expected to be limited to
docs/07-implementation-plan/task-004-gate-opening-proposal.md,
docs/07-implementation-plan/task-004-*-gate.md,
docs/07-implementation-plan/task-004-final-implementation-prompt.md,
docs/03-architecture/master-blueprint-open-questions.md (MBQ-06 residual
closure only), docs/01-research/research-handoff.md>

Forbidden files: everything under addons/; every *.py/*.xml/*.csv/manifest/
security/test/migration file; any CI/workflow file; any file not listed
above.

Acceptance criteria: <PLACEHOLDER — e.g., "the gate-opening proposal
restates the seven gate-condition pattern used by Task 002/003; the final
task prompt names an exact, exhaustive allowed-files list; MBQ-06's
residual is closed with exact thresholds/copy, not left open">

Tests: N/A (docs-only). State explicitly that no test file is created or
modified.

Rollback notes: <PLACEHOLDER — e.g., revert the single docs commit; no
code or schema is touched, so rollback has no runtime effect>

Definition of done: <PLACEHOLDER — e.g., gate-opening proposal + final
implementation prompt drafted; ChatGPT reviews and either performs the
explicit gate-opening act or returns for revision; handoff updated>

Do NOT run this prompt unless ChatGPT has explicitly approved starting
Task 004 gate-preparation work. Stop at the scoped boundary; do not draft
004B's skeleton in the same session.
```

---

## Candidate 004B — Create skeleton only, if authorized

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.

> **Purpose:** once 004A's gate-opening act is merged, create the minimal
> readiness-service model/registry skeleton — no check logic, no tests
> beyond import/registration smoke tests. Mirrors how Task 001 shipped
> models before any behavior.

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm the Task 004 gate-opening act (<PLACEHOLDER: cite the merged
gate document and its merge commit>) exists and is merged before writing
any code.

Read first: CLAUDE.md; research-handoff.md (current entry);
claude-learning-rules.md; <PLACEHOLDER: the Task 004 gate-opening
document>; defect-pattern-log.md; rejected-approaches-log.md;
architecture-review-log.md; technical-debt-register.md (TD-001);
pr-review-checklist.md (A–C).

Task: Create the readiness-check registry/service model skeleton only —
<PLACEHOLDER: exact model name, e.g. shopify.connector.readiness.check,
per whatever MBQ-55-adjacent naming decision applies> — with the
essential/warning tier field, the domain-extension registration seam, and
no check implementations beyond <PLACEHOLDER: name the one or two
already-accepted essential checks this skeleton stage is allowed to
implement, if any — otherwise state "zero checks implemented, registry
only">.

Allowed files: <PLACEHOLDER — exact list, expected to be limited to one
or two new files under addons/shopify_connector_core/models/ and their
matching test files; no changes to shopify_connector_store_credential.py
or any security file>

Forbidden files: UI/views/menus/actions of any kind; webhooks; cron;
domain modules (shopify_connector_product/_sale/_inventory/_fulfillment);
shopify_connector_store_credential.py; any security/*.csv or *.xml file;
any file not listed above.

Acceptance criteria: <PLACEHOLDER — e.g., "registry model loads with no
schema error; tier field enforces exactly two values; domain seam accepts
a registered check without modifying core; zero checks silently marked
essential without an explicit tier assignment">

Tests: <PLACEHOLDER — e.g., "model-registration smoke test; tier-field
validation test; registration-seam test proving a domain module could
register without touching core">

Rollback notes: <PLACEHOLDER — e.g., "single-PR revert; no other model
depends on this one yet; store.last_readiness_result/_at mirror fields
(if added this stage) remain harmlessly unused on rollback">

Definition of done: code + tests written; tests pass (or are honestly
recorded as py_compile/pyflakes-validated-only if no Odoo runtime is
available, per the Task 001A precedent); lint/format clean;
pr-review-checklist.md section C satisfied; any shortcut logged in
technical-debt-register.md; only allowed files changed; handoff updated;
quality gate confirmed.

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate, commit/push to the
designated branch, then STOP. Do not start 004C in this session.
```

---

## Candidate 004C — Add tests only, if authorized

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.

> **Purpose:** once 004B's skeleton is merged and reviewed, add the actual
> essential/warning check implementations and their tests — one session,
> not folded into 004B, so each PR stays small and independently
> reviewable.

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm 004B is merged and reviewed, and confirm <PLACEHOLDER: the exact
list of essential/warning checks this stage is authorized to implement,
per DEC-018/MBQ-06> before writing any code.

Read first: CLAUDE.md; research-handoff.md (current entry);
claude-learning-rules.md; the Task 004 gate-opening document;
defect-pattern-log.md; rejected-approaches-log.md;
architecture-review-log.md; technical-debt-register.md (TD-001 — confirm
its routing decision from 004A is respected, not silently reopened or
silently fixed here); pr-review-checklist.md (A–C).

Task: Implement <PLACEHOLDER: exact check list, e.g. "credential
validity/test-connection result; required scopes present; API-version
health; store identity" — essential tier — plus <PLACEHOLDER: warning-tier
checks for this stage, if any>>, each returning a named reason, each
read-only, writing per-check JSON results to job.log.payload_snapshot and
mirroring the summary to store.last_readiness_result/_at.

Allowed files: <PLACEHOLDER — exact list, expected to be limited to the
readiness-service model file(s) from 004B plus their test files; no new
model files beyond what 004B already created unless explicitly named
here>

Forbidden files: UI/views/menus/actions of any kind; webhooks; cron;
domain modules; shopify_connector_store_credential.py; any security file;
the webhook-HMAC check and mapped-Location check implementations
(these remain pending slots per the accepted candidate scope — registered,
not implemented, unless a future stage explicitly authorizes them by
name).

Acceptance criteria: a failed essential check can never yield an overall
"pass"; warnings never block; every check returns a named, redacted
reason; every check is provably read-only (no mutation-capable call
exists in the check implementations); the webhook-HMAC and mapped-Location
checks remain registered pending slots, not implemented, unless this
prompt names them explicitly above.

Tests: <PLACEHOLDER — e.g., "tier-semantics test (one failed essential →
overall fail, regardless of warnings); per-check result persistence test;
summary-mirroring test; redaction test on payload_snapshot content;
seam-registration test; TD-001 non-regression test proving
core_readiness_check's routing decision from 004A is respected">

Rollback notes: <PLACEHOLDER — e.g., "single-PR revert; store.last_readiness_result/_at
mirrors remain harmlessly stale, per the already-accepted risk mitigation
in credential-connection-foundation-task-plan.md">

Definition of done: code + tests written and pass; lint/format clean;
pr-review-checklist.md section C satisfied; any shortcut logged in
technical-debt-register.md; only allowed files changed; handoff updated;
quality gate confirmed; manual validation checklist item(s) added if this
project's live-validation precedent (Task 003) applies here too —
<PLACEHOLDER: confirm with ChatGPT whether a Task-004-specific manual
validation checklist, mirroring task-003-manual-validation-checklist.md,
is required before this task's PR can be accepted>.

End: run the learning review, update the handoff, confirm the quality
gate, commit/push to the designated branch, then STOP. Do not start 004D
in this session.
```

---

## Candidate 004D — UI/config only, if authorized

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.

> **Purpose:** placeholder for any UI/config surface Task 004 might
> eventually need (e.g., surfacing readiness results on a future
> dashboard). Per `task-004-readiness-preflight.md` §3, **Task 004's
> current candidate scope explicitly excludes all UI** — this candidate
> exists only so the four-prompt shape (per this session's assignment) is
> complete, and must not be read as implying UI work is expected soon.
> **This candidate is the least likely of the five to ever be needed as
> written** — Task 004's own accepted scope is "no views." If UI is ever
> wanted for readiness results, it almost certainly belongs to Task 006
> (setup wizard UI) or the Dashboard (MVP domain sequence Area 7), each
> already separately gated behind the UI implementation gate (still closed
> per AR-023) — not to Task 004 itself.

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only.

STOP FIRST: confirm this UI/config work is actually scoped to Task 004
and not to Task 006 (setup wizard) or the Dashboard/Sync Center (MVP
domain sequence Area 7) — per task-004-readiness-preflight.md §3, Task
004's accepted candidate scope has "no views." Do not proceed if this
work more properly belongs to Task 006 or the Dashboard; redirect to the
correct task instead.

Preconditions: the UI implementation gate is open (it is explicitly
closed today per AR-023); <PLACEHOLDER: MBQ-03 XML IDs and MBQ-22 copy
decisions relevant to this specific surface are fixed>; Tasks 004's
backend (004B/004C) is merged and reviewed.

Task: <PLACEHOLDER — to be defined only if/when ChatGPT decides Task 004
needs a UI surface; do not assume one is needed>

Allowed files: <PLACEHOLDER>
Forbidden files: <PLACEHOLDER — restate no-code-elsewhere rule>
Acceptance criteria: <PLACEHOLDER>
Tests: <PLACEHOLDER>
Rollback notes: <PLACEHOLDER>
Definition of done: <PLACEHOLDER>

Do NOT run this prompt unless ChatGPT has explicitly named a UI need for
Task 004 specifically (as opposed to Task 006 or the Dashboard) and has
opened the UI implementation gate. Stop at the scoped boundary.
```

---

## Candidate — Rollback/review prompt

> **DRAFT — DO NOT USE UNTIL CHATGPT UNBLOCKS TASK 004.**
>
> **Do not use until [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
> is merged and the Task 004 gate is accepted by ChatGPT.** DEC-021
> (2026-07-07) formally defers VAL-B2 from the Task 003 → Task 004 gate,
> which allows Task 004 to proceed to **gate-opening review only** — it
> does **not** authorize any prompt below to be issued. None of these
> prompts is runnable, and none authorizes code, until a separate Task 004
> gate-opening act (`../07-implementation-plan/task-004-gate-opening-proposal.md`,
> `../07-implementation-plan/task-004-readiness-check-substrate-gate.md`) is
> itself explicitly accepted and merged by ChatGPT.

> **Purpose:** a standing prompt for a dedicated review/rollback session,
> to be used if any Task 004 stage (004B/004C/004D) needs to be reverted or
> re-reviewed after merge — mirroring this project's "small, scoped
> sessions only" discipline (`CLAUDE.md` §6) rather than folding rollback
> into whichever session happens to notice a problem.

```text
You are Claude Code performing a REVIEW/ROLLBACK session for Task 004 on
the Odoo 19 Shopify Connector. This is not a new-feature session.

Read first: CLAUDE.md; research-handoff.md (current entry);
the merged Task 004 stage PR(s) under review; pr-review-checklist.md;
technical-debt-register.md; defect-pattern-log.md.

Task: <PLACEHOLDER — e.g., "review merged PR #<N> (Task 004 stage
<004B/004C/004D>) against its own acceptance criteria and rollback notes;
if a defect is found, do NOT fix it in this session unless explicitly
authorized — record it per the same defect-recording discipline used in
task-003-validation-results.md §4">

Allowed files: <PLACEHOLDER — expected to be limited to the same files
the stage under review touched, if a revert is authorized; otherwise
docs-only (a review-results record) if only recording, not reverting>

Forbidden files: any file not already touched by the PR under review;
any new feature scope.

Acceptance criteria: <PLACEHOLDER — e.g., "review record is honest about
what passed/failed; no defect is silently fixed without its own
authorization; rollback, if performed, follows the rollback notes
recorded in the original stage's task prompt exactly">

Tests: <PLACEHOLDER — e.g., "if rolling back, confirm the rollback notes'
own stated test/verification step (e.g., re-run the seam-registration
test to confirm no orphaned registration remains)">

Rollback notes: this prompt IS a rollback prompt — restate the specific
stage's own previously-recorded rollback notes here rather than inventing
new ones: <PLACEHOLDER>

Definition of done: review record (or rollback) committed; handoff
updated with the review outcome; any newly found defect routed to
technical-debt-register.md or a new, separately-scoped bug-fix task per
this project's standard defect-routing rule (not fixed inline unless
explicitly authorized); quality gate confirmed.

Do NOT run this prompt speculatively — only when an actual Task 004 stage
exists to review, and only with ChatGPT's request or explicit standing
authorization to review it.
```

---

## What none of these prompts do

- None says "build the connector" or authorizes broad implementation.
- None authorizes OAuth implementation.
- None authorizes any domain module (product/customer/order/inventory/
  fulfillment) code.
- None authorizes any UI beyond the explicitly-gated 004D candidate, which
  itself requires a separate, not-yet-open UI gate and most likely belongs
  to a different task entirely (see 004D's own warning above).
- None may be issued to an implementation session without every
  `<PLACEHOLDER>` filled in and ChatGPT's explicit review of the filled-in
  prompt, separate from this draft-shape document.
