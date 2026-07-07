# DEC-021 — VAL-B2 Deferral for Task 004 Gate

## Status

**Accepted by ChatGPT control-room decision; pending PR review/merge.**

## 1. Context

- **Task 003 is partially validated, not fully complete.** Per
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  (PR #107; extended by PR #109; extended by PR #110): eight checklist items
  passed live against a real Odoo 19 + Shopify development-store session
  (VAL-A2, VAL-A3, VAL-B1, VAL-B3, VAL-C2, VAL-E2, VAL-E3, VAL-F1), VAL-A1
  passed only as an installed-module/registry-load observation, static/
  offline evidence closed VAL-A4/VAL-C3/VAL-D1/VAL-D2, VAL-C1 remains
  **PARTIAL** (DB/ORM scan passed, server-log half not testable in any
  session so far), and VAL-B4–B7 and VAL-G1–G4 remain not tested.
- **VAL-B2 (the valid-token positive-connection test) is blocked**, not
  passed and not failed, because no compatible, valid Shopify Admin API
  access token was obtained in any session to date. The Dev Dashboard app
  used did not expose the older admin-created custom-app Admin API
  token-issuance path the connector currently expects
  (`token_variant='offline_custom_app'`).
- **The OAuth/Fable manual token-acquisition experiment did not execute.**
  PR #109 recorded that the attempt was blocked *before* reaching the
  Shopify Dev Dashboard: no Fable-equivalent browser-automation tool/
  connector and no Shopify Dev Dashboard Client ID/Client Secret or
  login/2FA path were available to that session. No authorization request
  was ever sent to Shopify; no claim is made about whether the flow would
  succeed or fail.
- **PR #110 added static/offline evidence but did not solve VAL-B2.** The
  static/offline Task 003 validation sweep closed several checklist items
  by repo/source inspection only (VAL-A4, VAL-C3, VAL-D1, VAL-D2, and
  VAL-C1's server-log half as "not testable in this session's
  environment") — none of that evidence touches VAL-B2, which requires an
  actual live, valid Shopify Admin API connection.
- **PR #111 prepared the Task 004 readiness preflight package but did not
  unblock implementation.** `task-004-readiness-preflight.md`,
  `task-004-dependency-map.md`, `task-004-quality-gates.md`, and
  `task-004-candidate-claude-prompts.md` restated the existing blocked
  state, organized already-existing planning material, and explicitly
  stated Task 004 remains blocked and no code is authorized.
- **ChatGPT has now made a control-room decision:** VAL-B2 is deferred
  from the Task 003 → Task 004 gate, so that Task 004 may proceed to a
  gate-opening *review* stage (not implementation) despite VAL-B2's
  unresolved status, under the strict constraints recorded in §4 below.

## 2. Decision

- **VAL-B2 is deferred from the Task 003 → Task 004 gate.** This is a
  formal deferral, decided by ChatGPT — not a silent re-scope, not an
  informal skip, and not a claim that the underlying validation gap has
  closed.
- **VAL-B2 is not passed, not failed, and not waived.** It remains an
  open, unresolved validation item. This deferral changes only what is
  required *of the Task 003 → Task 004 gate specifically* — it does not
  change VAL-B2's own status in `task-003-validation-results.md`.
- **MBQ-05 / the token-acquisition-direction proof is deferred for Task
  004 only** — it is not resolved as a final token-acquisition strategy.
  Option C remains a Recommendation, not an accepted Decision, and the
  empirical OAuth exchange experiment remains unexecuted.
- **Task 004 may move to gate-opening *review* only**, under the strict
  constraints in §4 — this decision does not authorize Task 004
  implementation.
- **Task 004 implementation still requires a separate gate-opening act and
  a separate final implementation prompt**, both explicitly accepted by
  ChatGPT, before any code is written.
- **TD-001 must be routed explicitly** — either as a mandatory first
  implementation acceptance criterion inside the Task 004 gate, or as a
  separate pre-Task-004 patch — **inside or before the Task 004 gate**.
  This decision does not itself route TD-001; it only requires that the
  gate-opening package route it explicitly rather than silently inheriting
  it (see `technical-debt-register.md`'s routing note, added by this same
  session).

## 3. Explicit non-decisions

This decision does **not**:

- pass VAL-B2;
- resolve OAuth or token acquisition;
- make the connector customer-ready;
- authorize OAuth implementation;
- authorize product/customer/order/inventory/fulfillment sync;
- authorize the setup wizard;
- authorize lifecycle activation/disconnect/reconnect implementation;
- resolve TD-001;
- authorize any code in this PR or in any PR that follows from it, absent
  a separate, explicit Task 004 gate-opening act and final implementation
  prompt.

## 4. Constraints on Task 004

Any Task 004 gate-opening package, and any eventual Task 004
implementation, must observe:

- **Fail-closed readiness behavior** — an unknown/uncomputed check state
  must never be treated as "passed" in any readiness summary.
- **No customer-facing readiness pass based on an unproven live
  connection.** A valid-connection readiness signal must rely only on
  existing stored evidence (e.g., Task 003's `last_test_connection_result`
  mirror) and must show **unknown/not-proven** when VAL-B2 evidence is
  absent — it must never assert "connected"/"pass" from an inference or
  from the mere presence of a stored token.
- **No activation/lifecycle dependency** — no disconnect/reconnect/
  activation implementation is authorized by this decision or by any
  Task 004 gate-opening package that cites it.
- **No domain sync dependency** — no product/customer/order/inventory/
  fulfillment sync code is authorized.
- **No OAuth code** of any kind.
- **No setup wizard** of any kind.
- **No UI** unless separately approved later, by its own named gate.
- **TD-001 routing is a hard pre-start condition** — a Task 004
  gate-opening package that does not name TD-001's routing explicitly is
  not gate-ready.

## 5. Consequences

- **Task 003 may be conditionally accepted only for Task 004 gate-opening
  *review* purposes** — not for customer-facing readiness, not as a claim
  that Task 003 is fully complete. See the corresponding update to
  `task-003-validation-results.md`'s Go/No-Go section.
- **A Task 004 gate-opening proposal may be prepared next** (this
  session's Phase 7 package) — proposal only, not an implementation
  authorization.
- **VAL-B2 remains required** before customer-facing setup, activation, a
  live readiness "pass" claim, or any domain sync that depends on a
  proven live connection.
- **MBQ-05 remains open/deferred, not resolved.** The token-acquisition
  direction (Option A/B/C) is still undecided as a final MVP strategy.
- **Customer-facing onboarding remains not ready.** Nothing in this
  decision changes that.

## 6. Rollback

Revert this docs PR. Task 004 returns to the pre-existing
blocked-on-VAL-B2 state recorded in
`task-004-readiness-preflight.md`/`task-004-dependency-map.md` prior to
this session, with no code, schema, or runtime effect of any kind (this
decision touches Markdown documentation only).
