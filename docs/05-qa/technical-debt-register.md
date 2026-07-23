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
| TD-001 | 2026-07-07 | Core job framework (`shopify_connector_job.py`) | The already-merged `core_readiness_check` `job_type` (AR-019, Task 001) is target-less (`res_model`/`res_id`/`shopify_target_gid` empty) with no per-run `payload_hash` value, so its `idempotency_key` is identical across every run for a given store; since `(store_id, idempotency_key)` is uniquely constrained and never cleared on terminal state (unlike `operation_scope_key`), a **second** `core_readiness_check` job for the same store would collide with the first, forever. Task 003 (AR-027, accepted with F1 revision) fixes the identical defect for the new `core_test_connection` job type only, by design — `core_readiness_check` is explicitly excluded from Task 003's scope so as not to silently touch already-accepted Task 001 schema/behavior without a named authorization. Separately, `payload_hash` is being repurposed from its originally-planned semantics ("a hash of the normalized outbound payload," `core-naming-schema-planning.md:476-481`) into a per-run nonce for target-less job types — a naming/schema-cleanliness overload, not just a `core_readiness_check`-specific issue. Re-confirmed still reproducing via VAL-F1 in the 2026-07-07 live validation session (`../05-qa/task-003-validation-results.md`). | Medium | Task 003's own scope (AR-027, F1 revision) deliberately excludes fixing already-merged Task 001 schema; fixing it requires its own named authorization, not an incidental Task 003 side-effect | If `core_readiness_check` jobs are ever created more than once per store before this is fixed, the second attempt fails on `store_idempotency_key_uniq` instead of succeeding | Control room (ChatGPT) to route: fold into a future Task 003 (or later) gate by explicit name, or schedule as its own tiny follow-up patch (candidate name: "Task 001B — job-framework target-less idempotency patch"). **Task 004 gate routing note (2026-07-07, per [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)): TD-001 must be explicitly handled in the Task 004 gate-opening act — either named as a mandatory first Task 004 implementation acceptance criterion, or split out as its own separate pre-Task-004 patch.** **ROUTE SELECTED (2026-07-07), by ChatGPT's Task 004 gate-acceptance decision (see [`task-004-readiness-check-substrate-gate.md`](../07-implementation-plan/task-004-readiness-check-substrate-gate.md) §TD-001 route): fix TD-001 INSIDE Task 004, as the first mandatory Task 004 implementation acceptance criterion.** The "Task 001B" separate-patch candidate is retired — no longer the chosen route. This is still a routing decision, not a fix — **TD-001 is NOT fixed, NOT closed, and NOT resolved by this note**; it stays `Open` until the future Task 004 implementation PR actually merges the fix and it is validated (mandatory regression test: two `core_readiness_check` runs for the same store must not collide). **RESOLVED (2026-07-08), by PR #115 (merge commit `4145faf69ae6c1d541006890fc2b997fe4c07238`, merged into `Shopify-connector`) — the Task 004 readiness-check substrate now gives `core_readiness_check` job creation its own fresh UUID4 `payload_hash` nonce (inside the new `shopify_connector_readiness_check.py` service's own `run_for_store`, mirroring the accepted `core_test_connection` pattern; `shopify_connector_job.py` and `shopify_connector_store.py` were not touched), so a second `core_readiness_check` job for the same store no longer collides on `store_idempotency_key_uniq`. Regression evidence: `test_td001_repeated_readiness_job_does_not_collide` proves two `core_readiness_check` job-creation attempts for the same store both succeed with distinct `payload_hash`/`idempotency_key` values. This regression test, and the full `shopify_connector_core` suite, were both run live against a real Odoo 19/PostgreSQL registry on Odoo.sh (branch database `adamsmen-claude-task-004-readiness-substrate-me21qg-34601850`) before merge — full module: `0 failed, 0 error(s) of 78 tests`; focused `TestReadinessCheck`: `0 failed, 0 error(s) of 31 tests` — see [`task-004-validation-results.md`](./task-004-validation-results.md) for the full evidence record.** | **Task 004 implementation** — fixed inside Task 004's own scope, as its first mandatory acceptance criterion, per the gate-acceptance decision above; no separate follow-up patch is planned. **Resolved by PR #115 (2026-07-08).** | Resolved |
| TD-002 | 2026-07-08 | Readiness scopes / Shopify access scopes (`shopify_connector_readiness_check.py`) | The already-shipped `REQUIRED_MVP_SCOPES` constant includes `read_fulfillments`, but current official Shopify Admin API access-scopes documentation (re-verified 2026-07-08, see [`../01-research/shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md) §3 and [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) §5) indicates that `read_fulfillments` governs only the `FulfillmentService` resource, not read access to an order's `Fulfillment`/`FulfillmentOrder` data — fulfillment-object access is actually covered by `read_orders` (already in the required set) and/or the `FulfillmentOrder`-family scopes, depending on which fulfillment API model the connector's fulfillment domain ultimately adopts. This is a least-privilege/readiness correctness concern, not merely a naming nitpick: requiring a scope that does not grant the access its name implies is exactly the kind of over-broad/mis-scoped grant DEC-004's least-privilege posture exists to avoid, and it must be resolved before any customer-facing setup/readiness claim relies on this check. **Clarification note (2026-07-09, AR-038 audit session — status unchanged, still Open, no fix authorized):** this row's original wording ("depends on which fulfillment API model … the connector ultimately adopts … which is not yet decided") is imprecise as written — the **write-side** fulfillment model was already decided before this row was logged: [`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (Accepted 2026-07-02) fixes FulfillmentOrder-based mutations exclusively, and RA-022 makes the legacy flow a binding rejection. The genuinely open dependency is narrower: the **exact scope set** the fulfillment domain needs. Per Shopify's official access-scopes page (re-verified 2026-07-09, Accessible, https://shopify.dev/docs/api/usage/access-scopes): `read_fulfillments`/`write_fulfillments` govern the `FulfillmentService` resource only, while the `FulfillmentOrder` resource is governed by the `read/write_assigned_fulfillment_orders`, `read/write_merchant_managed_fulfillment_orders`, `read/write_third_party_fulfillment_orders` (+ `read_marketplace_fulfillment_orders`) family, with `write_merchant_managed_fulfillment_orders` governing fulfillment creation for merchant-managed FulfillmentOrders (the connector's DEC-011 target case). The fix therefore waits only on the fulfillment domain's own naming/final-prompt pass picking its exact scope list (see `../08-release-readiness/open-points-closure-register.md` OP-20/OP-03) — not on any undecided architecture. Routing options unchanged. **Wave 0 research closure (2026-07-15; code status still Open):** official Shopify evidence and Task 014 D-014-2 now fix the exact narrow route: replace `read_fulfillments` with `read_merchant_managed_fulfillment_orders`, and require `write_merchant_managed_fulfillment_orders` only when the fulfillment domain is enabled for the merchant-managed write flow. See `../01-research/wave-0-roles-permissions-and-fulfillment-scope-refresh.md`. DEC-033 proposes control-room acceptance; no addon fix is authorized by this note. | Medium | The exact correction is now researched and routed, but Wave 0 is docs-only and DEC-033 remains Proposed; addon implementation belongs to the accepted Task 014/Wave 4 allowlist | The readiness-check's required-scopes gate may ask for or validate a misleading scope, and may imply fulfillment-readiness assurance that is not actually proven by the granted scope set | Claude control room to accept/revise DEC-033; Sol to implement Task 014 D-014-2 in Wave 4 after Layer 2, with focused readiness-scope tests | Before customer-facing setup/readiness UI or fulfillment domain implementation, whichever comes first | Open |
| TD-003 | 2026-07-23 | Fulfillment UI vocabulary (product docs vs shipped Wave 4 code) | The pre-implementation product docs use several review-case/status vocabulary values that **differ from the shipped Wave 4 `shopify_connector_fulfillment` code** (verified against exact head `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`): `fulfillment-operating-modes.md` §3 uses origin classes `external_service`/`carrier_event_only`, but the code `ORIGIN_CLASS_SELECTION` is `connector`/`external_merchant`/`external_app`/`external_unknown`; §4 uses review reason `over_fulfillment`, but the evidence `REVIEW_REASON_SELECTION` uses `quantity_overrun` (and the core job persists `ambiguous_match` as `manual_review_subreason`); §5 uses reconciled states `under_review`/`auto_matched`/`rejected`, but the code `RECONCILED_STATE_SELECTION` is `observed`/`review`/`acknowledged`/`applied`/`superseded`. This is a documentation/consistency debt, not a code defect — the code is authoritative and internally consistent. Recorded so the Wave 5 U1 UI binds to the **code** values and the product docs are annotated as carrying superseded vocabulary. Detail: `docs/07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md` §10. | Low | Scope boundary — surfaced during docs-only U1 Gate A; the U1 copy deck (a U1-implementation deliverable) is the correct place to fix the code→label mapping, and the product docs' superseded-vocabulary annotations are a light-touch doc pass not authorized in this Gate A session | If a future U1 UI or test author copies a product-doc value (e.g. `over_fulfillment`, `external_service`) into a view/selection/test instead of the code value, it will reference a non-existent selection and fail at runtime — exactly the invented-value trap the Gate A static-validation rule guards against | Wave 5 U1 implementation (copy deck) + a light product-doc annotation pass | Wave 5 U1 implementation | Open |

_This register is active. TD-001 was its first real entry (logged via
AR-027's F1 acceptance patch, 2026-07-07) and is now **Resolved** (fixed by
PR #115, 2026-07-08 — see the TD-001 row above). TD-002 (readiness
scope-naming concern) remains **Open for code**; Wave 0 closed the exact-scope
research/routing question, pending DEC-033 acceptance and Wave 4 implementation. Research-only gaps and gated
architecture/MVP questions from earlier research and product sprints
(Sprints A–G, summarized below) remain tracked in their own research/product
docs, the handoffs, and `architecture-review-log.md` — they are **not**
technical debt unless a compromise is explicitly logged here as its own
row._

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
