# Technical Debt Register

> **No technical debt should be silently accepted.** Every shortcut, compromise,
> deferred hardening, or "good enough for now" decision is recorded here with
> its risk and a target resolution phase.

## How to use

1. Add a row whenever a compromise is knowingly accepted.
2. **Severity** values: `Low`, `Medium`, `High`, `Critical`.
3. **Reason accepted temporarily** must be honest (deadline, missing evidence,
   scope boundary) — not a justification that hides risk.
4. **Target resolution phase** ties the debt to a phase in
   [`../07-implementation-plan/`](../07-implementation-plan/) or a future
   session, so it cannot be forgotten.
5. **Status** values: `Open`, `Scheduled`, `In progress`, `Resolved`,
   `Accepted (won't fix)` — the last requires a linked decision record.

---

## Register

| ID | Date added | Area | Description | Severity | Reason accepted temporarily | Risk | Owner | Target resolution phase | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _TD-000_ | _YYYY-MM-DD_ | _e.g. Sync engine_ | _What the debt is_ | _Low/Med/High_ | _Why now_ | _What could go wrong_ | _Who owns it_ | _Phase / session_ | _Open_ |
| TD-001 | 2026-07-07 | Core job framework (`shopify_connector_job.py`) | The already-merged `core_readiness_check` `job_type` (AR-019, Task 001) is target-less (`res_model`/`res_id`/`shopify_target_gid` empty) with no per-run `payload_hash` value, so its `idempotency_key` is identical across every run for a given store; since `(store_id, idempotency_key)` is uniquely constrained and never cleared on terminal state (unlike `operation_scope_key`), a **second** `core_readiness_check` job for the same store would collide with the first, forever. Task 003 (AR-027, accepted with F1 revision) fixes the identical defect for the new `core_test_connection` job type only, by design — `core_readiness_check` is explicitly excluded from Task 003's scope so as not to silently touch already-accepted Task 001 schema/behavior without a named authorization. Separately, `payload_hash` is being repurposed from its originally-planned semantics ("a hash of the normalized outbound payload," `core-naming-schema-planning.md:476-481`) into a per-run nonce for target-less job types — a naming/schema-cleanliness overload, not just a `core_readiness_check`-specific issue. | Medium | Task 003's own scope (AR-027, F1 revision) deliberately excludes fixing already-merged Task 001 schema; fixing it requires its own named authorization, not an incidental Task 003 side-effect | If `core_readiness_check` jobs are ever created more than once per store before this is fixed, the second attempt fails on `store_idempotency_key_uniq` instead of succeeding | Control room (ChatGPT) to route: fold into a future Task 003 (or later) gate by explicit name, or schedule as its own tiny follow-up patch (candidate name: "Task 001B — job-framework target-less idempotency patch") | A future gate naming `core_readiness_check` explicitly, or its own follow-up patch | Open |

_No other technical debt recorded yet (Research Sprints A–C, and the
docs-only sprints since — no code written until Task 001/002). This
register becomes active as design and implementation introduce
trade-offs; TD-001 (above) is its first real entry, logged via AR-027's
F1 acceptance patch (2026-07-07)._

_**Research Sprint C note (2026-06-30):** none. Sprint C was research-only
(competitor deep dives, matrix, UX benchmark, patterns, gaps, avoid-list) — no
code, no module, no shortcuts. The blocked sources (R2 Teqstars docs 403, R5
Google Doc) are **research gaps**, tracked in
[`../01-research/resource-inventory.md`](../01-research/resource-inventory.md) and
the handoff, **not** technical debt._

_**Research/Product Sprint D note (2026-07-01):** none. Sprint D was
synthesis-only (canonical feature taxonomy + capability evidence map + product
handoff) — no code, no module, no implementation shortcuts. The weak/blocked
competitor evidence (Teqstars docs 403, EC/R5 setup guide, 17 unread VT Confluence
articles) and the open architecture/MVP questions are **research gaps / gated
decisions**, tracked in the taxonomy's "Open questions", the handoffs, and
`architecture-review-log.md` — **not** technical debt._

_**Product Sprint E note (2026-07-01): none.** Sprint E was product-strategy /
synthesis-only (product vision + setup/UX principles + handoffs) — no code, no module,
no implementation shortcuts. The open MVP/architecture questions (distribution, queue
framework, binding model, module boundaries, multi-company, error/retry taxonomy) and
the weak/blocked competitor evidence (Teqstars 403, EC/R5 setup guide, 17 unread VT
Confluence articles) are **gated decisions / research gaps**, tracked in the product
vision's "Open questions", the handoffs, and `architecture-review-log.md` — **not**
technical debt._

_**Product Sprint F note (2026-07-01): none.** Sprint F was an MVP-proposal /
synthesis-only sprint (MVP scope proposal + non-MVP boundaries + user stories + handoffs)
— **no code, no module, no implementation shortcuts.** The open MVP/architecture questions
(direction/export, Domain 9 minimum, refunds/cancellations, distribution AR-002, queue
framework AR-003, binding model AR-005, error/retry taxonomy AR-006, inventory/fulfilment
AR-007/008, module boundaries AR-004, bulk ops, multi-store/company) and the weak/blocked
competitor evidence (Teqstars 403, EC/R5 setup guide, 17 unread VT Confluence articles)
are **gated decisions / research gaps**, tracked in `mvp-scope.md` "Open questions", the
handoffs, and `architecture-review-log.md` — **not** technical debt._

_**Product Sprint G note (2026-07-01, incl. PR #55 revision): none.** Sprint G was a
decision-recording / documentation sprint (accepted MVP scope in
`../04-decisions/DEC-003-mvp-scope.md` + product doc alignment + handoffs; PR #55 corrected
**controlled product export/update into MVP**) — **no code, no module, no implementation
shortcuts.** Scope **deferred** from MVP (**unrestricted autonomous bidirectional catalog
ownership**, customer export, refunds/cancellations, full Domain 9 accounting automation,
payouts, multi-store/company, bulk-ops-as-a-feature, etc. — **note: controlled product
export/update is in MVP, not deferred**) is a **planned product-scope boundary with revisit
conditions**, **not** deferred hardening or a compromise — so it is **not** technical debt.
The still-open MVP/architecture questions (AR-002…AR-008, the destructive-apply mechanics +
product match/binding model, the Domain 9 draft-artifact exception, internal bulk-ops need)
are **gated decisions**, tracked in DEC-003, the handoffs, and `architecture-review-log.md` —
**not** technical debt._
