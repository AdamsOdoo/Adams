# Task 004 — Final Implementation Prompt (Finalized)

> **DO NOT RUN UNTIL THIS GATE-ACCEPTANCE PR IS MERGED AND CHATGPT ISSUES
> THIS PROMPT IN CHAT.**
>
> This is the **finalized Claude Code prompt** for Task 004 implementation.
> ChatGPT has accepted
> [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
> and decided TD-001's route (fix inside Task 004). This prompt is filled
> in and ready for later use, but it is **still not issued and must not be
> pasted into any Claude Code session and run** until: (1) this
> gate-acceptance PR is merged into `Shopify-connector`, and (2) ChatGPT
> explicitly issues this exact prompt text in chat as its own turn. **No
> implementation code is written by this document. This document does not
> execute the prompt it contains.**

## Status

Finalized 2026-07-07, docs-only, as part of the Task 004 gate-acceptance
package (branch `claude/task-004-gate-acceptance-338b3a`). Supersedes the
prior draft version of this same file (prepared on branch
`claude/task-004-gate-opening-w3f1zg`, merged via PR #113), which carried
unfilled `<PLACEHOLDER>`s pending ChatGPT's gate acceptance and TD-001
routing decision — both are now recorded here. Companion to
[`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md)
and
[`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md).
Supersedes nothing in
[`../06-prompts/task-004-candidate-claude-prompts.md`](../06-prompts/task-004-candidate-claude-prompts.md)
— this document remains a more concrete, single consolidated alternative;
the candidate-prompts file's 004A–004D split remains an alternative
shaping ChatGPT may prefer instead.

## How to use this document

1. Confirm the gate-acceptance PR (this one) is actually merged into
   `Shopify-connector` — do not assume it is because this document exists.
2. Confirm the merge commit SHA below is filled in with the actual,
   post-merge value (it is left as `<MERGE_COMMIT_SHA>` in this PR, since
   the SHA cannot be known before this PR itself merges) before this
   prompt is issued.
3. ChatGPT issues this exact prompt text in chat, as its own session/turn.
4. Stop at its own scoped boundary (`CLAUDE.md` §6) — do not chain
   straight into Task 005 or any other next-feature work.

---

## Finalized prompt text

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm the Task 004 gate-opening act
(docs/07-implementation-plan/task-004-readiness-check-substrate-gate.md,
merge commit <MERGE_COMMIT_SHA>) exists, is merged, and carries ChatGPT's
explicit acceptance before writing any code.

Read first: CLAUDE.md; docs/01-research/research-handoff.md (current
entry); docs/06-prompts/claude-learning-rules.md; the Task 004 gate
document named above; docs/04-decisions/DEC-021-val-b2-deferral-for-task-004.md;
docs/05-qa/defect-pattern-log.md; docs/05-qa/rejected-approaches-log.md;
docs/05-qa/architecture-review-log.md; docs/05-qa/technical-debt-register.md
(TD-001 — its route is decided: fixed inside this task, as the first
mandatory acceptance criterion below — do not silently skip it, and do
not silently broaden the fix beyond target-less readiness jobs);
docs/06-prompts/pr-review-checklist.md (A–C).

Objective: Implement the readiness-check substrate for
shopify_connector_core: a check registry/service (core-owned checks plus a
domain-extension registration seam), essential/warning tiers exactly per
the accepted DEC-018/MBQ-06 split, running as setup_readiness_check-sourced
core_readiness_check jobs, with per-check JSON results written to
job.log.payload_snapshot via the existing _system_append path, and a
summary mirrored onto store.last_readiness_result / store.last_readiness_at
(confirm these two fields' exact presence/shape on
shopify.connector.store before writing to them; if either does not yet
exist, add it as a plain readonly mirror field only — no view, no
onchange, no computed dependency beyond this task's own write path).

Allowed files (exact):
- addons/shopify_connector_core/models/shopify_connector_readiness_check.py
  (new) — the readiness-check registry/service model: check registration
  seam, essential/warning tier semantics, fail-closed aggregation, the
  core_readiness_check job-creation path (with its own fresh UUID4
  payload_hash nonce — this is the TD-001 fix; see Acceptance criteria
  below), and the summary mirror write to shopify.connector.store.
- addons/shopify_connector_core/models/__init__.py — exactly one import
  line added for the new file above (mirrors the Task 003 precedent
  already used for shopify_connector_job_log; no other change to this
  file).
- addons/shopify_connector_core/tests/test_readiness_check.py (new) — all
  tests for this task.
- addons/shopify_connector_core/tests/__init__.py — exactly one import
  line added for the new test file above (mirrors the existing
  Task-003-approved one-import-line pattern; no other change to this
  file).
- addons/shopify_connector_core/__manifest__.py — version bump only (from
  19.0.1.2.3 to 19.0.1.3.0, following the Task 002 -> 19.0.1.1.0 / Task
  003 -> 19.0.1.2.0 precedent). No other change to this file.
- docs/01-research/research-handoff.md — the mandatory handoff update.

No other file may be created or modified. In particular, do NOT modify
addons/shopify_connector_core/models/shopify_connector_job.py or
addons/shopify_connector_core/models/shopify_connector_store.py — the
TD-001 fix belongs entirely inside the new readiness-check file's own
job-creation call (mirroring, not editing, the existing
action_test_connection pattern in shopify_connector_store.py), per the
"minimal and scoped to target-less readiness jobs" constraint below. If
repo inspection at execution time shows this is not achievable without
touching shopify_connector_job.py or shopify_connector_store.py, STOP and
report back before writing any code — do not improvise a broader change.

Forbidden files (exact):
- Any file under addons/shopify_connector_core/security/, or
  addons/shopify_connector_core/models/shopify_connector_store_credential.py
- Any view/menu/action/wizard/controller/XML file of any kind
- Any webhook/cron/scheduled-action implementation
- Any file under a domain module
  (shopify_connector_product/_sale/_inventory/_fulfillment), including any
  such module's creation
- Any CI/workflow file, Dockerfile, or requirements*.txt
- Any migration file
- Any file not explicitly named in the Allowed files list above

Acceptance criteria (in priority order):
1. TD-001 IS FIXED, as the first mandatory acceptance criterion. Repeated
   core_readiness_check job creation for the same store must be safe: a
   second core_readiness_check job for the same store must NOT collide on
   store_idempotency_key_uniq. The fix must be MINIMAL and scoped
   EXCLUSIVELY to target-less readiness jobs (i.e., give
   core_readiness_check job creation its own fresh UUID4 payload_hash
   nonce, mirroring the existing core_test_connection pattern in
   action_test_connection). It must NOT alter the already-accepted
   core_test_connection behavior unless strictly necessary — and if it
   turns out to be necessary, that must be explicitly justified in the PR
   description, not silently done. A regression test proving two
   core_readiness_check job-creation attempts for the same store do not
   collide is MANDATORY (see Tests below).
2. A failed essential check can never yield an overall "pass"; warnings
   never block.
3. Every check returns a named, human-readable reason; no raw exception
   text or stack trace surfaces as the primary message.
4. Every check is provably read-only (no mutation-capable call path
   exists in any check implementation).
5. The credential-validity/test-connection essential check reads ONLY the
   existing store.last_test_connection_result mirror from Task 003 — it
   performs no new live Shopify call, and reports unknown/not-proven when
   that mirror has never recorded a pass. It must NEVER assert a
   "connected"/"pass" state when VAL-B2 evidence is absent — this is a
   hard, non-negotiable acceptance criterion per DEC-021.
6. The webhook-HMAC check and mapped-Location check exist as registered,
   non-implemented pending slots only.
7. The domain-extension registration seam is provable: a check can be
   registered from outside shopify_connector_core without modifying core
   files.
8. No customer-facing readiness "pass", activation trigger, setup-wizard
   step, or domain-sync enablement exists anywhere in this task's scope
   that depends on the unproven VAL-B2.

Tests (all mandatory):
- The TD-001 regression test: two core_readiness_check job-creation
  attempts for the same store both succeed, with no
  store_idempotency_key_uniq collision.
- A test proving core_test_connection's own repeat-run behavior (Task
  003's VAL-B3 property) is unchanged by this task's change, unless the
  PR description explicitly justifies and documents a deviation.
- Tier-semantics test: a single failed essential check always yields an
  overall fail, regardless of any passing/warning checks; a warning-only
  result never yields an overall fail.
- Per-check JSON result persistence into job.log.payload_snapshot.
- Summary-mirroring test, including the "unknown = not passed" fail-closed
  aggregation rule.
- Seam-registration test proving a check can be registered from outside
  shopify_connector_core without modifying core files.
- Read-only guarantee test for every check implemented in this stage.
- If the repository still has no Odoo runtime/CI at execution time, tests
  are honestly recorded as written and py_compile/pyflakes-validated
  only, per the Task 001A precedent, and
  docs/05-qa/task-004-manual-validation-checklist.md is prepared as
  mandatory review evidence — never silently skipped or silently claimed
  as executed.

Rollback notes: single-PR revert; no destructive migration.
store.last_readiness_result/_at mirror fields, if populated, remain
harmlessly stale on rollback — no downstream code may assume they are
always current. Reverting this PR also reverts the TD-001 fix — confirm
in the PR description whether any later-planning material (Task 005/006)
already assumes core_readiness_check's collision-free behavior at
rollback time, and say so explicitly if it does, rather than assuming it
away.

Definition of done: code + tests written and pass (or honestly recorded as
py_compile/pyflakes-validated only if no Odoo runtime is available, per
the Task 001A precedent, with docs/05-qa/task-004-manual-validation-checklist.md
prepared as mandatory review evidence); lint/format clean;
pr-review-checklist.md section C satisfied; any shortcut logged in
technical-debt-register.md; only the allowed files above changed
(confirmed by git diff review); the mandatory research-handoff update
(docs/01-research/research-handoff.md, including the Learning feedback
loop section) is included in the PR; TD-001 is confirmed fixed by its
regression test, and the technical-debt-register.md TD-001 row's Status
column is updated to Resolved only once this PR is reviewed and accepted
by ChatGPT (do not mark it Resolved unilaterally in this same PR without
that review having occurred — record it as "fix implemented, pending
ChatGPT review" instead).

Explicit hard constraints (restate before finishing, in the PR body):
- No OAuth code of any kind.
- No setup wizard of any kind.
- No product/customer/order/inventory/fulfillment sync code of any kind.
- No UI/views/menus/actions/wizards/XML of any kind.
- No webhook/cron implementation — pending slots only.
- No lifecycle (activate/disconnect/reconnect) implementation of any kind.
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
- Does not itself open the Task 004 implementation gate — that happens
  only when
  [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
  is merged into `Shopify-connector` carrying ChatGPT's acceptance.
- Does not start the Task 004 implementation session — that requires
  ChatGPT to explicitly issue this exact prompt text in chat, as its own
  turn, after the gate-acceptance PR merges.
- Does not supersede or invalidate
  [`../06-prompts/task-004-candidate-claude-prompts.md`](../06-prompts/task-004-candidate-claude-prompts.md) —
  both remain drafts pending ChatGPT's own choice of shaping (single
  consolidated task vs. the 004A–004D split).
