# DEC-021 — VAL-B2 Deferral for the Task 003 → Task 004 Gate

> **Decision record for the premium Odoo 19 ↔ Shopify Connector**, recording a
> ChatGPT control-room decision: **defer** Task 003's blocked VAL-B2
> (valid-token positive-connection test) and the still-unexecuted OAuth/manual
> token-acquisition experiment from the Task 003 → Task 004 gate, so that
> Task 004 gate-opening review may proceed **under explicit constraints**,
> without treating VAL-B2 as passed, failed, or waived. Companion documents:
> [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
> (Go/No-Go section, updated by this same PR),
> [`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md)
> (§10a PR #109 continuation note; new §10b deferral note added by this same
> PR),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (MBQ-05 row, updated by this same PR),
> [`../07-implementation-plan/task-004-readiness-preflight.md`](../07-implementation-plan/task-004-readiness-preflight.md),
> [`../07-implementation-plan/task-004-dependency-map.md`](../07-implementation-plan/task-004-dependency-map.md),
> [`../05-qa/task-004-quality-gates.md`](../05-qa/task-004-quality-gates.md)
> (all three updated by this same PR), and
> [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)
> (TD-001, **not modified** by this PR — referenced only).

## Status

**Accepted by ChatGPT control-room decision, pending PR review/merge.**
Prepared 2026-07-07 on branch `claude/record-val-b2-deferral-5uz9wf`, branched
from `Shopify-connector` at its tip after **PR #111** merged (Task 004
readiness preflight package, merge commit `43f3b2a923a420e523cd2ec2662a46e2a9abed26`).
**Documentation-only.** No code, test, manifest, security, XML, CSV, migration,
or CI/workflow file is created or modified by this record. This record does
**not** authorize Task 004 implementation, does **not** open Task 004's
implementation gate, and does **not** start any Task 004 coding.

## 1. Context

- **Task 003 (API client shell + test connection) is merged, but its manual
  validation is not fully complete.** Per
  [`task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  (originally recorded by **PR #107**): eight checklist items passed live
  against a real Odoo 19 + Shopify development-store session (VAL-A2, VAL-A3,
  VAL-B1, VAL-B3, VAL-C2, VAL-E2, VAL-E3, VAL-F1), VAL-A1 passed only as an
  installed-module/registry-load observation, and **VAL-B2 — the valid-token
  positive-connection test — is BLOCKED, not passed and not failed**, because
  no Shopify Admin API access token compatible with the connector's shipped
  credential shape (`token_variant='offline_custom_app'`) was obtainable from
  the Shopify Dev Dashboard app used during that session. VAL-E1 is blocked as
  a direct consequence of VAL-B2.
- **This is a real Shopify platform change, not a test-environment
  inconvenience.** As of January 1, 2026, Shopify closed the "admin-created
  custom app, reveal a token in the UI" path for any newly created custom app
  — see
  [`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md)
  §2 (evidence, all **[Fact]**, independently re-verified 2026-07-07) and
  [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)'s
  MBQ-05 row for the full official-source detail. This project's own
  research/decision work (**PR #108**) recommends **Option C** (keep the
  existing offline/custom-app storage shape; attempt a manual OAuth
  authorization-code-grant exchange, outside the Odoo codebase, as a
  research-validation step before deciding between Option A and Option B) —
  but Option C is a **[Recommendation]**, not an accepted **[Decision]**, and
  remains unproven either way.
- **The OAuth/Fable experiment did not execute.** **PR #109** ran the
  continuation session Option C's own §5 called for, scoped specifically to
  attempt the manual OAuth authorization-code-grant exchange. That session
  could not proceed past its own prerequisite check: no Fable-equivalent
  browser-automation tool/connector and no Shopify Dev Dashboard Client
  ID/Client Secret or login/2FA path were available to it. **No request was
  ever sent to Shopify; no code was exchanged for a token; no claim is made
  that the flow would have succeeded or failed** against a
  Dev-Dashboard-created custom app. See
  [`task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  §8 and
  [`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md)
  §10a for the full blocked-attempt record.
- **PR #110 added static/offline evidence but did not solve VAL-B2.** A
  docs-only static/offline validation sweep confirmed, by repo/source
  inspection only (no live Odoo instance, no live Shopify connection, no
  valid token), static evidence for VAL-A4, VAL-C3, VAL-D1, and VAL-D2, and
  recorded VAL-C1's server-log-grep half as "not testable in this session's
  environment" (no live Odoo runtime or log files exist in that execution
  environment). None of this touches VAL-B2, which PR #110 explicitly left
  **BLOCKED, not attempted**.
- **PR #111 prepared a Task 004 readiness preflight package but did not
  unblock Task 004.** `task-004-readiness-preflight.md`,
  `task-004-dependency-map.md`, and `task-004-quality-gates.md` were prepared
  to organize already-existing planning material for a future gate-review
  session, restating (not changing) that Task 003 validation is incomplete,
  VAL-B2 is blocked, MBQ-05 is open, and Task 004 remains blocked pending both.
- **TD-001 remains open and unrouted.** Per
  [`technical-debt-register.md`](../05-qa/technical-debt-register.md), the
  already-merged `core_readiness_check` `job_type` (Task 001) collides on a
  second run for the same store (`store_idempotency_key_uniq`). This is
  directly relevant to Task 004's own candidate scope (the readiness engine
  consumes `core_readiness_check`), and Task 003's own live validation session
  (VAL-F1) reconfirmed the collision is still present. Neither this record nor
  any prior PR routes or fixes TD-001 — it is referenced, not resolved, here.
- **No new runtime code defect was observed in any of the tested paths**
  across PR #107, #109, #110, or #111. The blocker is entirely a
  token-acquisition/platform-access question, not a connector code defect.

## 2. Decision

ChatGPT, acting in its control-room/reviewer role per `CLAUDE.md` §2, decides:

1. **VAL-B2 is formally deferred from the Task 003 → Task 004 gate.** VAL-B2
   is **not** passed, **not** failed, and **not** waived. It remains an open,
   named, tracked item — deferred for the specific, limited purpose of
   allowing Task 004 gate-opening *review* (not implementation) to proceed,
   and for no other purpose.
2. **MBQ-05 / the token-acquisition direction is deferred for Task 004 only.**
   This deferral does **not** resolve MBQ-05 as a final token-acquisition
   strategy. Option C remains the standing **[Recommendation]**; Option A and
   Option B remain live alternatives; the empirical OAuth experiment remains
   unexecuted. MBQ-05 continues to block the setup-wizard/credential-
   acquisition slice and any customer-facing setup claim, exactly as it did
   before this record — this deferral narrows only what it takes for **Task
   004's own gate-opening review** to proceed, not what it takes for MBQ-05
   itself to close.
3. **Task 004 may move to gate-opening *review* only**, and only under the
   strict constraints in §4 below. This decision does **not** itself open
   Task 004's implementation gate, does **not** issue a Task 004 `CLAUDE.md`
   §9 final implementation prompt, and does **not** authorize any Task 004
   code. A separate, explicit Task 004 gate-opening act (following the
   `task-002-credential-storage-gate.md` / `task-003-api-client-test-connection-gate.md`
   precedent) is still required before any implementation prompt is written,
   per `task-004-dependency-map.md` §4 items 5–6, which are unchanged by this
   record.

## 3. Explicit non-decisions

This record does **not**:

- Pass VAL-B2. VAL-B2 remains BLOCKED, not passed, not failed, not waived.
- Resolve OAuth/token acquisition. The empirical experiment (decision brief
  §4–§5) remains unexecuted; no direction (Option A, B, or C) is finally
  committed.
- Make the connector customer-ready. No customer-facing setup readiness is
  claimed by this record, before or after Task 004.
- Authorize OAuth implementation of any kind, in Task 004 or any other task.
- Authorize product/customer/order/inventory/fulfillment domain sync, or any
  other domain-module work.
- Authorize a setup wizard, or any UI/view/menu/action/wizard file.
- Authorize connection lifecycle/activation actions (Task 005's scope).
- Resolve TD-001. TD-001 remains **Open** in
  [`technical-debt-register.md`](../05-qa/technical-debt-register.md),
  unmodified by this record, and must be explicitly routed (folded into the
  Task 004 gate by name, or scheduled as its own follow-up patch) before or
  inside the Task 004 gate-opening act — not silently inherited and not
  silently fixed here.
- Change or reopen any prior accepted decision (DEC-003 through DEC-020) or
  any accepted MBQ row other than MBQ-05's own row, which is updated only to
  add this deferral note and a link to this record — not to reclassify it as
  resolved.

## 4. Constraints on Task 004

Task 004 gate-opening review, and any eventual Task 004 implementation, must
observe **all** of the following, each traceable to this record:

- **Fail-closed readiness behavior.** An unknown/uncomputed check state must
  never be treated as "passed" in any readiness summary — consistent with
  `task-004-quality-gates.md` §6's existing fail-closed aggregation
  requirement, which this record does not weaken.
- **No customer-facing readiness-pass claim based on an unproven live
  connection.** Any valid-connection readiness check Task 004 implements must
  remain backed by **existing fields** already produced by Task 002/003
  (`credential_present`, `credential_state`, `granted_scopes`,
  `granted_scopes_checked_at`, and the `core_test_connection` job/job.log
  trail) — it must read what those fields actually record, and must **not**
  claim a live "connected" pass unless the underlying field evidence for that
  pass actually exists. Because VAL-B2 has never been observed to pass, no
  Task 004 check may assert or imply that a real, valid Shopify connection has
  ever been proven.
- **No OAuth implementation.** No client-credentials, authorization-code-grant,
  token-exchange, or redirect-endpoint code of any kind.
- **No setup wizard.** No view, menu, action, or wizard file of any kind (Task
  004's own already-documented candidate scope is core models/tests only, per
  `task-004-readiness-preflight.md` §3 — unchanged by this record).
- **No customer-facing connection flow** of any kind.
- **No product/customer/order/inventory/fulfillment sync** of any kind — no
  domain-module file, no domain-module dependency.
- **No activation/lifecycle actions** — connect/disconnect/reconnect/activate
  remain Task 005's separately-gated scope, unaffected by this record.
- **No claim of a live valid Shopify connection**, anywhere in code, tests,
  documentation, or PR description, until VAL-B2 or an accepted replacement
  validation actually passes.
- **TD-001 must be routed** explicitly — before or inside the Task 004
  gate-opening act, per `task-004-dependency-map.md` §4 item 3 (unchanged) —
  not silently fixed and not silently left unrouted by this record or by any
  future session that cites it.

## 5. Consequences

- **Positive:** Task 003 may be **conditionally accepted for Task 004 gate
  purposes only** — see the corresponding update to
  [`task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  §5 in this same PR. A future session may prepare a Task 004 gate-opening
  proposal (not an implementation prompt) referencing this record, without
  needing to re-litigate whether VAL-B2's absence blocks that specific,
  narrow next step.
- **Negative / trade-offs:** The connector still cannot honestly claim a
  proven, valid Shopify connection. Any Task 004 gate-opening proposal, and
  any eventual implementation, must carry this record's constraints (§4)
  forward explicitly rather than silently assuming Task 003 is "done." If the
  eventual OAuth/token-acquisition experiment fails once it is finally run,
  some Task 004 assumptions about the credential/scope-snapshot seam could
  still require rework — this deferral does not eliminate that risk, it only
  scopes it away from Task 004's own gate-opening review.
- **Follow-ups:**
  - A future Task 004 gate-opening proposal session, including explicit
    TD-001 routing (see §4 and `task-004-dependency-map.md` §4 item 3).
  - The empirical OAuth/manual-token-acquisition experiment remains a
    required future session once a Fable-equivalent browser-automation tool
    and a secure, session-scoped Shopify Dev Dashboard credential/consent
    path are both available — see
    [`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md)
    §10a's "Updated required follow-up."
  - VAL-B2 (or an accepted replacement validation) remains required before
    any customer-facing setup claim, any activation/lifecycle action, or any
    domain sync that depends on a proven live connection — this is not
    satisfied by Task 004's gate-opening review and is not satisfied by this
    record.

## 6. Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Keep Task 004 fully blocked until VAL-B2 passes or MBQ-05 fully resolves | Leaves the project stalled indefinitely on a platform-access blocker (tool/credential availability) unrelated to connector code quality; Task 004's candidate scope (readiness-check substrate) does not itself require a proven live connection to be *designed and gate-reviewed*, only to be *fully validated* | Not rejected outright — remains available; this record chooses the narrower deferral instead because it preserves forward progress without weakening VAL-B2's evidence bar |
| Silently re-scope VAL-B2 away as "close enough" | Explicitly prohibited by the token-acquisition decision brief §8 ("it would not be appropriate to mark Task 003 'complete' by silently re-scoping VAL-B2 away without that decision") and by `CLAUDE.md` §8's claim-classification discipline | Rejected — logged here; not a `rejected-approaches-log.md` entry because it was never proposed as a real option, only named and dismissed |
| Accept Option A or Option B now, without running the empirical experiment | Still available to ChatGPT as a future call (decision brief §10), but not decided by this record — this record only defers VAL-B2/MBQ-05 for Task 004's gate purposes, it does not pick a final token-acquisition direction | Not rejected — remains open per the decision brief |

## 7. Rollback

Revert this record's PR. Effect: Task 004 returns to its pre-existing
**blocked-on-VAL-B2** state exactly as recorded in
`task-004-readiness-preflight.md` (pre-revision) and
`task-004-dependency-map.md` §2 (pre-revision) — no Task 004 gate-opening
review may proceed until either this deferral is re-accepted or VAL-B2/MBQ-05
resolve on their own merits. Reverting this PR does not affect any code,
since none was changed.

## 8. Evidence / references

This is an internal governance/control-room decision, not a claim requiring
external citation under `CLAUDE.md` §7 — its evidentiary basis is the
project's own already-cited, already-merged internal record:

- [`task-003-validation-results.md`](../05-qa/task-003-validation-results.md) —
  PR #107 (original), §8 continuation (PR #109), static/offline addendum (PR
  #110).
- [`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md) —
  PR #108 (original), §10a (PR #109).
- [`shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md) —
  underlying official-source evidence (PR #108).
- [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md) —
  MBQ-05 row.
- [`task-004-readiness-preflight.md`](../07-implementation-plan/task-004-readiness-preflight.md),
  [`task-004-dependency-map.md`](../07-implementation-plan/task-004-dependency-map.md),
  [`task-004-quality-gates.md`](../05-qa/task-004-quality-gates.md) — PR #111.
- [`technical-debt-register.md`](../05-qa/technical-debt-register.md) — TD-001
  (referenced, not modified).
