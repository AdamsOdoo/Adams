# Task 004 — Final Implementation Prompt (Draft)

> **DRAFT — DO NOT RUN UNTIL CHATGPT EXPLICITLY APPROVES AFTER REVIEW.**
>
> This is a **future Claude Code prompt** for Task 004 implementation,
> prepared as part of this session's gate-opening package. It is **not**
> issued, **not** authorized, and **must not be pasted into any Claude Code
> session and run** until: (1)
> [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md) is
> merged, (2)
> [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
> is explicitly reviewed, accepted, and merged by ChatGPT, and (3) every
> `<PLACEHOLDER>` below is filled in with ChatGPT-reviewed specifics. **No
> implementation code is written by this document. This document does not
> execute the prompt it contains.**

## Status

Prepared 2026-07-07, docs-only, as part of the Task 004 gate-opening
package (branch `claude/task-004-gate-opening-w3f1zg`). Companion to
[`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md)
and
[`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md).
Supersedes nothing in
[`../06-prompts/task-004-candidate-claude-prompts.md`](../06-prompts/task-004-candidate-claude-prompts.md)
— this document is a more concrete, single consolidated draft; the
candidate-prompts file's 004A–004D split remains an alternative shaping
ChatGPT may prefer instead.

## How to use this document

1. Confirm the three preconditions in the banner above are actually true —
   do not assume they are because this document exists.
2. Fill in every `<PLACEHOLDER>` below with the exact, ChatGPT-reviewed
   specifics. An unfilled placeholder means the prompt is not ready to
   issue.
3. Have ChatGPT review the filled-in prompt itself, separately from
   reviewing this draft-shape document, before it is issued to any
   implementation session.
4. Issue the prompt as its own session/turn. Stop at its own scoped
   boundary (`CLAUDE.md` §6).

---

## Draft prompt text

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm the Task 004 gate-opening act
(docs/07-implementation-plan/task-004-readiness-check-substrate-gate.md,
merge commit <PLACEHOLDER>) exists, is merged, and carries ChatGPT's
explicit acceptance before writing any code.

Read first: CLAUDE.md; docs/01-research/research-handoff.md (current
entry); docs/06-prompts/claude-learning-rules.md; the Task 004 gate
document named above; docs/04-decisions/DEC-021-val-b2-deferral-for-task-004.md;
docs/05-qa/defect-pattern-log.md; docs/05-qa/rejected-approaches-log.md;
docs/05-qa/architecture-review-log.md; docs/05-qa/technical-debt-register.md
(TD-001 — confirm its routing disposition from the gate document is
followed exactly, not silently reopened or silently fixed if the gate
named it out of scope); docs/06-prompts/pr-review-checklist.md (A–C).

Objective: Implement the readiness-check substrate for
shopify_connector_core: a check registry/service (core-owned checks plus a
domain-extension registration seam), essential/warning tiers exactly per
the accepted DEC-018/MBQ-06 split, running as setup_readiness_check-sourced
core_readiness_check jobs, with per-check JSON results written to
job.log.payload_snapshot via the existing _system_append path, and a
summary mirrored onto <PLACEHOLDER: confirm exact field names —
store.last_readiness_result / store.last_readiness_at, or the accepted
equivalent per the gate document>.

Allowed files (exact — fill in after repo inspection at gate-acceptance
time):
<PLACEHOLDER — expected to be limited to one or two new files under
addons/shopify_connector_core/models/ (e.g. a readiness-check
registry/service model file) and their matching test files under
addons/shopify_connector_core/tests/; a documentation-only manifest
version bump; the mandatory research-handoff update. No other file.>

Forbidden files (exact):
- Any file under addons/shopify_connector_core/security/ or
  addons/shopify_connector_core/models/shopify_connector_store_credential.py
- Any view/menu/action/wizard/controller/XML file of any kind
- Any webhook/cron/scheduled-action implementation
- Any file under a domain module
  (shopify_connector_product/_sale/_inventory/_fulfillment), including any
  such module's creation
- Any CI/workflow file, Dockerfile, or requirements*.txt
- Any migration file
- Any file not explicitly named in the Allowed files list above

Acceptance criteria:
- A failed essential check can never yield an overall "pass"; warnings
  never block.
- Every check returns a named, human-readable reason; no raw exception
  text or stack trace surfaces as the primary message.
- Every check is provably read-only (no mutation-capable call path exists
  in any check implementation).
- The credential-validity/test-connection essential check reads only the
  existing store.last_test_connection_result mirror from Task 003 — it
  performs no new live Shopify call, and reports unknown/not-proven when
  that mirror has never recorded a pass. It must NEVER assert a
  "connected"/"pass" state when VAL-B2 evidence is absent — this is a
  hard, non-negotiable acceptance criterion per DEC-021.
- The webhook-HMAC check and mapped-Location check exist as registered,
  non-implemented pending slots only.
- The domain-extension registration seam is provable: a check can be
  registered from outside shopify_connector_core without modifying core
  files.
- TD-001 disposition: <PLACEHOLDER — state exactly, per the accepted gate
  document: either "fixed in this task's own scope, with a
  fix-verification test" or "explicitly NOT fixed in this task's scope;
  the existing core_readiness_check idempotency-collision behavior is
  unchanged, proven by a non-regression test">.
- No customer-facing readiness "pass", activation trigger, setup-wizard
  step, or domain-sync enablement exists anywhere in this task's scope
  that depends on the unproven VAL-B2.

Tests:
<PLACEHOLDER — expected to include: tier-semantics test (single failed
essential -> overall fail, regardless of warnings); per-check JSON result
persistence test; summary-mirroring test including the "unknown = not
passed" fail-closed aggregation rule; seam-registration test; read-only
guarantee test for every check implemented in this stage; the TD-001 test
matching the disposition named above.>

Rollback notes:
<PLACEHOLDER — expected to state: single-PR revert; no destructive
migration; store.last_readiness_result/_at mirror fields, if populated,
remain harmlessly stale on rollback; confirm whether any later-planning
material already assumes this task's output at rollback time and say so
explicitly if it does.>

Definition of done: code + tests written and pass (or honestly recorded as
py_compile/pyflakes-validated only if no Odoo runtime is available, per
the Task 001A precedent, with docs/05-qa/task-004-manual-validation-checklist.md
prepared as mandatory review evidence); lint/format clean;
pr-review-checklist.md section C satisfied; any shortcut logged in
technical-debt-register.md; only allowed files changed (confirmed by git
diff review); the mandatory research-handoff update
(docs/01-research/research-handoff.md, including the Learning feedback
loop section) is included in the PR; TD-001's disposition matches exactly
what this prompt named, with no silent deviation.

Explicit hard constraints (restate before finishing, in the PR body):
- No OAuth code of any kind.
- No setup wizard of any kind.
- No product/customer/order/inventory/fulfillment sync code of any kind.
- No UI/views/menus/actions/wizards/XML of any kind.
- No webhook/cron implementation — pending slots only.
- Fail-closed readiness behavior: unknown/uncomputed = not passed, always.
- No live-connection "pass" claim anywhere in code, tests, docstrings, or
  the PR body if VAL-B2 evidence is absent from the store's stored
  test-connection mirror.

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate per
docs/05-qa/quality-feedback-loop.md, commit/push to the designated branch,
open the PR as DRAFT, then STOP. Do not start any further Task 004 slice,
Task 005 work, or any other next-feature work in this session.
```

---

## What this document does not do

- Does not execute the prompt above.
- Does not write any implementation code.
- Does not authorize OAuth, setup-wizard, domain-sync, or lifecycle
  (activate/disconnect/reconnect) implementation.
- Does not claim VAL-B2 has passed or that a live Shopify connection has
  been proven.
- Does not decide TD-001's disposition — that placeholder must be filled
  in only after ChatGPT's review of the gate document names the choice
  explicitly.
- Does not supersede or invalidate
  [`../06-prompts/task-004-candidate-claude-prompts.md`](../06-prompts/task-004-candidate-claude-prompts.md) —
  both remain drafts pending ChatGPT's own choice of shaping (single
  consolidated task vs. the 004A–004D split).
