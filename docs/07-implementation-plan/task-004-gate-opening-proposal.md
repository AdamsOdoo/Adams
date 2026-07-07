# Task 004 Gate-Opening Proposal

> **Proposal only. Does not open the Task 004 gate. Does not authorize
> implementation.** This document proposes the scope and conditions for a
> future, separate Task 004 gate-opening act — mirroring the
> `task-002-gate-opening-proposal.md` → `task-002-credential-storage-gate.md`
> and `task-003-gate-opening-proposal.md` →
> `task-003-api-client-test-connection-gate.md` precedent. The gate opens
> only when a document analogous to those two (this package's companion,
> [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md))
> is itself explicitly accepted and merged by ChatGPT — not by this
> proposal being drafted, reviewed, or discussed.

## 1. Status

**Proposed for ChatGPT review; not implementation authorization.** Prepared
2026-07-07 on branch `claude/task-004-gate-opening-w3f1zg`, following
ChatGPT's control-room decision recorded in
[`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
to defer VAL-B2 from the Task 003 → Task 004 gate.

## 2. Gate context

- **VAL-B2 deferred by DEC-021.** ChatGPT has formally deferred VAL-B2 (the
  Task 003 valid-token positive-connection test) from the Task 003 → Task
  004 gate. VAL-B2 is **not passed, not failed, and not waived**.
- **MBQ-05 deferred for Task 004 only.** The token-acquisition direction
  (Option A/B/C) remains open at the product/architecture level — see
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)'s
  MBQ-05 row. This deferral is scoped to unblocking Task 004 gate-opening
  review specifically.
- **Task 004 is allowed to move to gate-opening *review*.** DEC-021 exists
  precisely to permit this proposal and its companion documents to be
  prepared and reviewed.
- **Task 004 implementation is not yet authorized.** This proposal, its
  companion gate document, and the draft final implementation prompt
  prepared alongside it do not, by themselves or together, open the gate
  or authorize any code. The gate opens only when
  [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
  is itself merged into `Shopify-connector`, per the AR-021/AR-026/AR-028
  precedent.
- **Task 003 is conditionally accepted for this purpose only.** Per the
  updated Go/No-Go section in
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  §5: conditional acceptance for Task 004 gate-opening review, not a full
  Go, not a claim of full completion, and not a claim that a live valid
  Shopify connection has ever been established.
- **TD-001 remains open and is routed, not fixed, by this session.** See
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)'s
  routing note and §4 below.

## 3. Proposed Task 004 objective

**Readiness check substrate only** — the smallest next foundation step
already named in
[`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md):
a readiness-check engine (check registry, essential/warning tiers per the
already-accepted DEC-018/MBQ-06 split) running as `setup_readiness_check`-
sourced `core_readiness_check` jobs, with per-check JSON results written to
`job.log.payload_snapshot` and a summary mirrored onto
`store.last_readiness_result`/`store.last_readiness_at`.

## 4. Proposed included scope

- Readiness check registry/service (core-owned checks plus a domain
  extension seam).
- Essential/warning tier semantics per the accepted DEC-018/MBQ-06 split.
- Fail-closed aggregation: an unknown/uncomputed check state must never be
  treated as "passed" in the overall summary; a single failed essential
  check must always yield an overall fail regardless of warnings.
- Per-check JSON result persistence to `job.log.payload_snapshot`.
- A readiness summary mirror on `store` fields
  (`last_readiness_result`/`last_readiness_at`), if already planned/
  accepted in prior architecture material (see
  `credential-connection-foundation-task-plan.md`'s Task 004 entry).
- A domain-extension registration seam (a check can be registered from
  outside `shopify_connector_core` without modifying core files).
- **No customer-facing live-connection "pass" claim if VAL-B2 evidence is
  absent.** The credential-validity/test-connection essential check must
  read only the existing, already-stored `last_test_connection_result`
  mirror from Task 003 — it must never assert a live "connected" state
  from inference, and must report unknown/not-proven when that mirror has
  never recorded a pass.
- **TD-001 route explicitly included or separated** — the eventual Task
  004 implementation task prompt must name, exactly, whether TD-001's fix
  is in-scope for Task 004 or is a separate pre-Task-004 patch. Neither
  choice is pre-decided by this proposal.

## 5. Proposed excluded scope

- OAuth implementation of any kind.
- Token acquisition of any kind.
- Setup wizard implementation of any kind.
- Activation/disconnect/reconnect (lifecycle) implementation of any kind.
- Product/customer/order/inventory/fulfillment sync of any kind.
- Dashboards/UI of any kind.
- Webhooks/cron — registered as pending check slots only (per the existing
  candidate scope), never implemented.
- Any change to credential storage or security files
  (`shopify_connector_store_credential.py`,
  `security/ir.model.access.csv`, `security/shopify_connector_security.xml`)
  unless explicitly authorized later, by name, in a separate gate act.

## 6. Gate conditions

1. **DEC-021 must be merged** into `Shopify-connector` before this
   proposal or its companion gate document may be considered accepted.
2. **TD-001 routing must be explicit** — named in the accepted gate
   document and in the eventual final implementation prompt, not silently
   inherited.
3. **A final implementation prompt must be accepted by ChatGPT**, naming
   an exact, exhaustive allowed-files list and an exact, exhaustive
   forbidden-files list, per `CLAUDE.md` §9, before any code is written.
   The draft prepared alongside this proposal
   ([`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md))
   is explicitly marked not runnable until that acceptance.
4. **All allowed/forbidden files must be exact** in the accepted gate
   document — no open-ended or illustrative file lists.
5. **No broad build.** This proposal authorizes, at most, a narrow,
   small-PR implementation slice (mirroring the Task 002/003 precedent of
   splitting scaffold from checks) — not a single large PR implementing
   the entire readiness engine at once.
6. **No customer-facing readiness, activation, setup wizard, or domain
   sync dependency on the unproven VAL-B2**, per DEC-021 §4, applies to
   every stage of Task 004.

## 7. Recommendation

**ChatGPT may approve moving to Task 004 final implementation prompt
review** — reviewing and, if acceptable, merging
[`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
as the actual gate-opening act, and separately reviewing
[`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
before it is issued to any implementation session. **This proposal does
not itself authorize code.** No Task 004 implementation PR may be opened
on the basis of this proposal alone.
