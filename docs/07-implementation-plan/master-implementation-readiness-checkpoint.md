# Master Implementation Readiness Checkpoint — Task 010 Gate Assessment

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Planning only. Does
> not authorize implementation of any kind.** Prepared after PR #131 (Task 006C
> sync-engine core skeleton), PR #132 (Task 006C closure/validation docs),
> PR #133 (post-Task 006C next-task recommendation checkpoint), and PR #134
> (sync-engine concurrency validation plan) all merged into `Shopify-connector`,
> latest merge commit `51628f77a7da1e47cfdb30d17559b496c4c45a1d`. This document
> consolidates already-recorded facts, decisions, and open items from the cited
> files — it does not itself resolve, narrow, or decide any of them, and it
> does not reopen or reinterpret any accepted decision. Every claim below is
> either a **[Fact]** (cited, verifiable in this repository), a restated
> **[Decision]** / **[Open question]** (cited from its own record), or this
> document's own **[Recommendation]** / **[Inference]**, labelled per
> `CLAUDE.md` §8. Subject to ChatGPT review, revision, or rejection in whole or
> in part.
>
> **This document does not accept, authorize, or open anything.** It is the
> master readiness assessment requested for the post-Task-006C implementation-
> readiness checkpoint. Per its own findings (§1), it functions as a
> **blocker-resolution proposal**, not a Task 010 gate-opening package — no
> Task 010 final implementation prompt or gate-opening proposal is drafted by
> this session (see §10).

## Status

- **Not ready to open a Task 010 gate.** Two explicit, named preconditions in
  Task 010's own accepted proposed-scope document are unmet (§1, §4).
- Confirms PR #131, #132, #133, #134 are merged into `Shopify-connector` (verified
  via `pull_request_read` this session, all four `merged: true`, `state: closed`).
- Confirms this session's branch (`claude/task-010-readiness-checkpoint-jrx96i`)
  sits exactly at `Shopify-connector` tip `51628f77a7da1e47cfdb30d17559b496c4c45a1d`
  (PR #134's merge commit) — no drift.
- Confirms `main` is untouched (recorded SHA `a5d4543` — Research Sprint A
  governance foundation merge — unrelated to and unaffected by this session).
- Confirms no plain `dev` branch exists on the remote (`git ls-remote --heads
  origin` returns no `dev` ref) — nothing to avoid touching beyond `main` itself.
- Does not open, extend, or reinterpret any implementation gate. The only gate
  ever opened remains the limited core-only, zero-UI gate
  ([`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md)),
  scoped to Task 001 only and explicitly stated not to "apply project-wide to
  future gates."
- Does not authorize Task 010, any other domain-sync task, a setup wizard,
  OAuth/token-acquisition code, or any Lite/Full packaging implementation.

---

## 1. Executive conclusion

**Not ready because specific blockers must be closed first.**

Two explicit, named preconditions in Task 010's own accepted proposed-scope
document — [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md)
§"Preconditions" — remain unmet, and neither is resolved by PR #131–#134 or by
anything else read for this checkpoint:

1. **[Fact]** *"The product domain gate named in
   `ui-ux-implementation-task-map.md` Group 10 explicitly opened by ChatGPT."*
   — **Not opened.** [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
   Group 10 itself lists "Product domain gate" as a **prerequisite decision**,
   not a decided/opened one. [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md)
   Area 1 independently confirms: *"a not-yet-defined 'product domain gate'
   referenced as a prerequisite in `ui-ux-implementation-task-map.md` Group 10,
   whose own triggering conditions are not specified in any research note read
   for this pass."* No document anywhere in this repository defines what would
   need to be true to open this gate, and no document opens it.
2. **[Fact]** *"MBQ-55 (exact Odoo model/field names for the product-template
   and product-variant binding models) resolved via the dedicated
   documentation-only domain naming/schema planning pass that
   `master-blueprint-open-questions.md`'s own MBQ-55 row calls for 'before the
   product/customer/order slice starts.'"* — **Not resolved.** Every citation
   found across `docs/03-architecture/`, `docs/04-decisions/`, and
   `docs/07-implementation-plan/` (dozens of cross-references, including the
   DEC-014 acceptance patch, which explicitly lists MBQ-55 among the rows that
   "remain open — not resolved by this acceptance") confirms MBQ-55 is still
   open. No naming/schema planning pass for the product domain has been run.

Because Task 010's own proposed spec is explicit that these two items are
required before the task "may start," and because neither is a runtime/live-
access item (both are docs-only-resolvable), this checkpoint cannot honestly
conclude Task 010 is the smallest safe next **build** step. It is not yet a
safe step at all, because two of its own named starting conditions are absent.

This finding is also fully consistent with, not a reversal of, the
already-merged planning trail: PR #133's own recommendation document
([`next-task-recommendation-after-task-006c.md`](./next-task-recommendation-after-task-006c.md)
§D) explicitly named "Product MVP Task 010 preparation" as **"not recommended
as the immediate next task,"** citing the same rework-risk category this
checkpoint independently re-confirms (§7 below). PR #134's own concurrency
validation plan ([`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md)
§12) restates that, absent a live runtime (still true — see §7), the
recommended parallel track is MBQ-05 auth-distribution planning, **not**
Task 010. Nothing found in this session's research contradicts or reopens
either of those conclusions.

**Conclusion label, per the task's required phrasing:** *Not ready because
specific blockers must be closed first.*

---

## 2. Current accepted foundation

What is complete and merged into `Shopify-connector` as of
`51628f77a7da1e47cfdb30d17559b496c4c45a1d`:

- **Research baseline** — Research Sprints A–G (competitor research, feature
  taxonomy, capability evidence map, product vision, MVP scope, UX principles)
  and the Master Blueprint program (Parts A–D: core substrate, product/
  customer/sale, inventory/fulfillment, UI/UX screen design), all accepted via
  DEC-013 through DEC-020.
- **Architecture decisions** — DEC-003 through DEC-025 accepted (MVP scope,
  distribution/auth strategy, sync orchestration, binding/dedup identity,
  Phase 1 scope clarifications, module boundaries, error/retry/idempotency,
  inventory architecture, fulfillment architecture, UX operator flow, the four
  master-blueprint decision packages, MBQ decision batches, VAL-B2 deferral,
  Task 005 scope/closure, token-acquisition/VAL-B2 routing, and the Task 006
  sync-engine gate).
- **Core substrate (merged code, `shopify_connector_core`)** — six accepted
  core models (`shopify.connector.store`, `.store.settings`, `.location`,
  `.binding.mixin`, `.job`, `.job.log`); credential storage/masking/redaction
  foundation (Task 002); read-only API client + test-connection service
  (Task 003); readiness-check substrate (Task 004, TD-001 fixed inside it);
  connection lifecycle actions — activate/disconnect/reconnect (Task 005).
  Confirmed present via direct, read-only inspection of
  `addons/shopify_connector_core/models/` and `/tests/` this session — no
  product/customer/order/inventory/fulfillment model, no webhook controller,
  no OAuth file, no setup-wizard view/menu/action exists anywhere in the addon
  tree.
- **Sync-engine skeleton (Task 006C, PR #131, merged)** — job-enqueue service;
  `ir.cron`-driven claim/drain dispatch loop using per-row
  `try_lock_for_update()`; handler-registry dispatch seam; named/tunable retry
  scheduler; state-transition helpers; diagnostic `core_dispatch_selftest`
  job type. Makes no Shopify API call itself and implements no domain sync.
- **Validation/closure records** — Task 006C closure and validation-results
  record ([`task-006c-sync-engine-skeleton-validation-results.md`](../05-qa/task-006c-sync-engine-skeleton-validation-results.md),
  AR-032) documents two real-runtime defects found and fixed (a test-only
  fake-handler-signature bug; a real production `action_disconnect()`/
  `manual_review_subreason` bug, fixed via an approved one-file exception) and
  explicitly states the runtime-validation acceptance rests on a
  **user-provided** Odoo.sh green-build report, not independently observed CI
  evidence (`pull_request_read get_status`/`get_check_runs` still return
  `pending`/empty via this repository's GitHub API).
- **Concurrency validation plan (PR #134, merged, not executed)** —
  [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md)
  defines nine scenarios, three runtime topologies, and pass/fail criteria for
  SRR-03/SRR-04/SRR-09 against the Task 006C claim/dispatch mechanism. **No
  Odoo/Odoo.sh runtime is reachable from this or any prior session's
  environment**, so the plan remains unexecuted.

---

## 3. Accepted vs proposed vs open

**Accepted (decisions, not implementation authorizations unless noted):**

- DEC-003 through DEC-025 (architecture/scope decisions).
- Task 001 core-only zero-UI gate — **the only implementation gate ever
  opened** ([`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md),
  accepted 2026-07-05, scope exhausted by Task 001).
- Task 002, 003, 004, 005, 006C implementation gates — each separately opened
  and each already exhausted by its own merged PR (accepted per their own
  AR rows AR-026, AR-029, and the Task 004/005/006C gate documents).
- MBQ-59 (automated product/customer/order import create/bind policy) —
  accepted **at blueprint-policy level only**; exact eligibility/match-
  confidence thresholds remain open (see §4).
- DEC-023 — Custom Distribution accepted **only** for one-store/VAL-B2-
  evidence-gathering purposes (branch A); the scalable many-customer
  architecture (branch B) is explicitly **not** accepted.

**Proposed (not yet accepted as a decision, not authorized):**

- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) —
  scope/boundary/approach only; does not reach `CLAUDE.md` §9 file-exact
  precision because MBQ-55 is open (by the document's own stated limitation).
- [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md) —
  a proposed domain ordering (product → customer → order → inventory →
  fulfillment); explicitly "does not open any implementation gate."
- [`next-task-recommendation-after-task-006c.md`](./next-task-recommendation-after-task-006c.md) —
  a recommendation, not a decision; ranked concurrency-plan drafting (done,
  PR #134) and MBQ-05 planning above Task 010 preparation.
- [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md) —
  a plan, not evidence; "even a fully green future execution would not mean
  concurrency is proven for all time or all conditions" (its own §9).

**Open questions / recommendations / runtime-only unknowns:** see the full
classification table in §4.

---

## 4. Blocker classification table

Classification key (per this session's required scheme):
**A** = blocks Product Task 010 implementation ·
**B** = does not block Task 010 but blocks later MVP implementation ·
**C** = does not block coding but must remain tracked ·
**D** = requires live/runtime/human access, cannot be solved by docs-only work.

| Item | Class | Source evidence | Blocks Task 010? | Why / why not | Resolves via |
| --- | --- | --- | --- | --- | --- |
| **Product domain gate (not opened; trigger conditions undefined)** | **A** | [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) §Preconditions; [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md) Group 10; [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md) Area 1 | **Yes — hard blocker** | Named as an explicit precondition in Task 010's own proposed scope; no document defines what would open it, and it has never been opened | A ChatGPT act defining and opening this gate (docs-only) |
| **MBQ-55 (product-template/variant binding model/field names)** | **A** | [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md); DEC-014 acceptance patch (lists MBQ-55 as still open); [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) §Preconditions | **Yes — hard blocker** | Task 010's own document states MBQ-55 must be resolved "before the product/customer/order slice starts"; not resolved anywhere in the repo | A dedicated, documentation-only domain naming/schema planning pass |
| **Product first-sync dedup thresholds (MBQ-59 residual)** | **A** | [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) §"Duplicate prevention approach"; [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q37 | Yes — blocks a §9-precision final prompt, not the docs-only prep track | Deferred by design to "Task 010's own future final implementation prompt"; policy direction (two-tier gate, blocking preview) is accepted, exact thresholds are not | Task 010's own final implementation prompt (once the gate opens) — a narrow, named design decision, not a new architecture question |
| **Checkpoint/resume ownership (pagination-cursor ownership: core vs domain)** | **A** | [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q7; [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md) Scenario 9 | Yes — affects how Task 010 would implement multi-page product import | Core engine implements no checkpoint/resume primitive today (confirmed: no reclaim/resume code exists in `shopify_connector_job_dispatch.py`) | A narrow, in-task design decision inside Task 010's own final prompt (domain-owned cursor state), or a future core-engine primitive if the naming pass recommends one |
| **Product binding model details (product-template binding)** | **A** | Same as MBQ-55 row | Yes | Subset of MBQ-55 | Domain naming/schema planning pass |
| **Variant binding model details (product-variant binding)** | **A** | Same as MBQ-55 row | Yes | Subset of MBQ-55 | Domain naming/schema planning pass |
| **Product import pagination/checkpointing (GraphQL query/field list, cursor durability)** | **A** | [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) §"API calls required" ("Open — not yet confirmed... for this task's own final §9 prompt to fix"); [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q10, Q11, Q39 | Yes | Exact GraphQL shape and cursor-reuse behavior explicitly left to the final prompt | Task 010's own final implementation prompt |
| **Product media/image handling** | **A** | Silence in [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) — neither included nor excluded by name | Yes — an unaddressed scope gap, must not be assumed either way | No accepted decision anywhere states whether Task 010 imports media; must be explicitly scoped (recommend: excluded) before a final prompt is issued | Task 010's own final implementation prompt, as an explicit narrow scope decision |
| **Product price handling** | **A** | Same silence as above | Yes | Same reasoning | Task 010's own final implementation prompt, as an explicit narrow scope decision |
| **Product status/draft/archive/delete behavior** | **A** | Same silence as above | Yes | Same reasoning; Task 010 is import-only and issues no delete/write, but what to do with a non-`ACTIVE` Shopify product on import is undecided | Task 010's own final implementation prompt, as an explicit narrow scope decision |
| **Multi-server/concurrent-worker concurrency proof (SRR-03/04/09)** | **D** | [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md); [`sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md) SRR-03/04/09 | Not a named Task 010 precondition, but a material cross-cutting risk every future domain job (including Task 010's) would run through | `_claim_for_dispatch()`/`try_lock_for_update()` is proven only via `TransactionCase`; live proof requires a runtime this environment does not have | Future live Odoo.sh/multi-server execution of the existing validation plan |
| **VAL-B2 (no live Shopify Admin API connection ever made)** | **D** | [`val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) §Status | No — Task 010 uses only the existing Task 003 API client and fake/stub tests; VAL-B2 gates live/production claims, not Task 010's backend code | Requires a human operator with real Shopify Partner/Dev Dashboard access | Execution of `val-b2-closure-plan.md` by a session/operator with that access |
| **MBQ-05 (scalable many-unrelated-customer token-acquisition/distribution)** | **B** | [`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) §3.2 branch B | No — Task 010 consumes an already-established store connection; it performs no OAuth/token-acquisition | Blocks the setup wizard's OAuth-connect step and any many-customer distribution claim, not product-import backend logic | A dedicated MBQ-05 branch B research/decision task (docs-only, available now) |
| **Token acquisition for many unrelated customers** | **B** | Same as MBQ-05 row | No | Same underlying question as MBQ-05 branch B | Same as MBQ-05 row |
| **OAuth/token acquisition (implementation)** | **B** | [`DEC-023`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md); no OAuth code exists anywhere in the repo | No | Not required for Task 010's read-only import scope against an already-connected store | Future setup-wizard/OAuth implementation task, after MBQ-05 branch B is decided |
| **TD-002 (`read_fulfillments` scope-naming correctness)** | **B** | [`technical-debt-register.md`](../05-qa/technical-debt-register.md) TD-002 row | No — unrelated to product import | Depends on the fulfillment API model decision (below) | Fulfillment-domain task, or its own small correction task |
| **Fulfillment API model (legacy `Fulfillment` vs. `FulfillmentOrder`)** | **B** | [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q36; DEC-011/MBQ-42/MBQ-60 | No — unrelated to product import | Needed only for the future fulfillment-domain task (Task 014) | Fulfillment-domain task's own architecture decision |
| **Lite/Full packaging** | **B** | [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Blocking Question 6, Q21, Q27 | No — does not affect product-import backend model code | Affects install/licensing shape, not Task 010's own models/logic | A dedicated Lite/Full packaging research/decision task |
| **Setup wizard / operator-facing UI** | **B** | [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md); UI implementation gate remains closed | No, for a backend-only Task 010 — per the Task 001 core-only-zero-UI precedent (repo states this precedent exists but "no document states a general policy on this either way," an explicit open item, not a settled rule) | Task 010's own doc requires the UI gate only for its Matching Center (S6) screen, not its import/binding backend | A separate UI-implementation-gate opening act |
| **Product export/update (Task 015, future)** | **C** | [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) — explicitly out of scope, ChatGPT REVISE on PR #93 | No — explicitly excluded from Task 010 by name | Deferred to a separate, not-yet-authorized future candidate task | Future Task 015, its own separate gate |
| **Customer import (Task 011)** | **B** | [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md) | No — sequenced after product per the proposed domain order | Depends on MBQ-55 (same naming pass) and its own gate | Task 011, after Task 010 and its own gate |
| **Order import (Task 012)** | **B** | [`task-012-order-import-proposed.md`](./task-012-order-import-proposed.md) | No | Depends on product + customer bindings existing first | Task 012, after Tasks 010–011 |
| **Inventory sync (Task 013)** | **B** | [`task-013-inventory-sync-proposed.md`](./task-013-inventory-sync-proposed.md); DEC-010 | No | Depends on product binding only, sequenced later by risk profile | Task 013, its own gate |
| **Fulfillment/tracking sync (Task 014)** | **B** | [`task-014-fulfillment-tracking-proposed.md`](./task-014-fulfillment-tracking-proposed.md); DEC-011 | No | Depends on product + order bindings; fulfillment API model open | Task 014, its own gate |
| **Webhooks** | **C** | DEC-005 (layered sync, "never webhook-only"); DEC-020/MBQ-65 (product-webhook posture accepted at blueprint level, not implemented) | No — every proposed domain task explicitly excludes webhooks unless separately authorized | Standing, whole-MVP-sequence posture, not specific to any one task | Separate, explicit authorization per domain task if/when needed |
| **Live Shopify API validation** | **D** | Same as VAL-B2 row | No | Duplicate framing of VAL-B2 | Same as VAL-B2 row |

This table adds no new blocker beyond what its cited sources already record,
and closes none of them. Every "Open" status above is restated exactly as its
own cited source states it.

---

## 5. Recommendation

**Not Product MVP Task 010.** The smallest safe next steps, in order of how
directly they unblock Task 010 specifically, are docs-only and available now:

1. **[Recommendation] Primary: a dedicated, documentation-only domain
   naming/schema planning pass resolving MBQ-55** for the product-template and
   product-variant binding models (Area 1 only — not customer/order/inventory/
   fulfillment binding names, which can follow in their own pass per the
   proposed domain sequence). This is the more direct predecessor to a future
   Task 010 gate proposal, because it closes one of Task 010's own two named
   preconditions outright, and materially informs the second (defining exactly
   what the product domain gate would need to authorize).
2. **[Recommendation] Parallel candidate: MBQ-05 branch B (scalable
   many-unrelated-customer token-acquisition/distribution architecture)
   research/decision task**, per PR #134's own stated fallback when no runtime
   is available (still the case). This does not block Task 010 directly (§4),
   but remains open across multiple sessions and does not compete for the same
   evidence/access constraints as the naming pass — it can run alongside it.
3. **Not recommended now: concurrency validation execution** (Candidate 1 from
   PR #133) — still blocked on a live Odoo/Odoo.sh runtime this environment does
   not have. No change since PR #134.
4. **A ChatGPT act defining the product domain gate's own opening criteria** —
   distinct from (1)/(2), this is a standing gap: no document anywhere states
   what would need to be true to open the "product domain gate" named in
   `ui-ux-implementation-task-map.md` Group 10. Resolving (1) does not by
   itself open this gate; a separate, explicit act is still required per
   `CLAUDE.md` §5/§6.

This document does not rank (1) above (2) on authority — only on directness to
Task 010's own stated blockers. Both are fully docs-only-executable now, and
ChatGPT may choose either, both in parallel, or a different priority entirely.

---

## 6. First build task boundary

**Not applicable under this session's Option 2 conclusion — Product Task 010
is not recommended to start, and no build task is authorized by this
document.**

For forward reference only, once (and only once) §1's two named preconditions
are actually closed by explicit ChatGPT acts, Task 010's own already-proposed
scope (`task-010-product-import-proposed.md`, unchanged by this document)
would carry the following boundary:

- Product import only (Shopify → Odoo, read-only against Shopify).
- Variant binding only.
- Duplicate prevention / binding creation only.
- No product export/update of any kind.
- No order/customer/inventory/fulfillment logic of any kind.
- No setup wizard.
- No webhook.
- No OAuth.
- No Lite/Full packaging implementation.
- No live-Shopify dependency beyond the existing Task 003 API client/test-
  connection foundation, unless explicitly and separately controlled.
- Fake/stub client tests allowed in the absence of a live runtime.
- No broad refactor.

Restating this boundary here does **not** authorize it, start it, or imply the
preconditions in §1 are close to closed — it exists only so a future readiness
checkpoint does not have to re-derive it from scratch once the blockers move.

---

## 7. Why Task 010 cannot start yet

This section addresses each item this checkpoint was specifically required to
address:

- **Concurrency proof (SRR-03/SRR-04/SRR-09) still open.** [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md)
  remains unexecuted — no Odoo/Odoo.sh runtime is reachable from this
  environment. This is not one of Task 010's own named preconditions, but it
  is the specific, cited reason ([`next-task-recommendation-after-task-006c.md`](./next-task-recommendation-after-task-006c.md)
  §E) the already-merged planning trail gave for not starting *any* domain
  implementation yet: every future domain job, including a future Task 010's,
  would dispatch through the same unproven `_claim_for_dispatch()`/
  `try_lock_for_update()` mechanism, and this project has direct precedent
  (PR #121, SRR-06) of a concurrency-timing defect that passed every static
  review and was only caught live.
- **VAL-B2 still open.** No live Shopify Admin API connection has ever been
  made. This does not block Task 010's own backend logic (which would use
  fakes/stubs per its own proposed scope), but it means no domain sync code
  written anywhere in this project, including a future Task 010's, has ever
  been exercised against real Shopify response shapes — the same category of
  defect (test double vs. real behavior mismatch) Task 006C itself already
  hit once during real-runtime validation.
- **MBQ-05 still open.** Branch A (one-store/VAL-B2-evidence use of Custom
  Distribution) is accepted in narrow scope only; branch B (the scalable
  many-unrelated-customer architecture) remains a separate, unevaluated,
  gated research/decision task. Does not block Task 010's own import/binding
  scope (no OAuth involved), but blocks the setup wizard and any claim about
  how the connector would be distributed to real customers.
- **Lite/Full packaging still open.** No accepted decision states whether
  "Lite/Full" maps onto the existing per-store domain-enablement-flag
  mechanism or is a separate packaging concept. Does not block Task 010's own
  model/logic code, but remains a standing gap for the project's eventual
  commercial shape.
- **Product first-sync dedup thresholds still open.** Accepted at
  blueprint-policy level (MBQ-59: two-tier gate, blocking preview) but exact
  eligibility/match-confidence thresholds are explicitly deferred to Task
  010's own future final implementation prompt — which does not exist yet,
  because that prompt cannot be responsibly issued while §1's two
  preconditions remain unmet.
- **Checkpoint/resume ownership still open.** Whether pagination-cursor
  ownership belongs to the core engine or each domain module is undecided;
  the core engine today implements no reclaim/resume primitive for a job
  stuck mid-processing (confirmed by direct, read-only inspection of
  `shopify_connector_job_dispatch.py` and by
  [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md)
  Scenario 9's own framing). This is a real design input Task 010's own
  final prompt would need to fix, one more reason that prompt cannot yet be
  written responsibly.
- **The product domain gate is unopened, with undefined trigger conditions
  (§1).** This is the more fundamental blocker of the two named in Task 010's
  own preconditions: even if every item above were resolved, Task 010 still
  could not start without a distinct, explicit ChatGPT act opening this gate
  — and no document in this repository specifies what evidence or decision
  would need to precede that act.
- **MBQ-55 is unresolved (§1).** The second named precondition. Task 010's
  own document states plainly that it "does not reach the exact file/field
  precision of the `CLAUDE.md` §9 template because MBQ-55 ... is still open."
  A final implementation prompt written without this resolved would either
  invent model/field names not backed by any accepted decision, or leave them
  as a "narrow design decision" so broad (binding-model shape for a whole
  domain) that it would exceed what `CLAUDE.md` §9 intends by that phrase.

**Net effect:** even setting aside every cross-cutting risk (concurrency,
VAL-B2, MBQ-05, Lite/Full) as *not* formally blocking Task 010's own narrow
scope, the two items that Task 010's own proposed document names as hard
preconditions are both still open. That is sufficient, on its own, for the
strict/practical conclusion in §1.

---

## 8. Risks accepted for starting Task 010

**None.** No implementation of any kind is being started, recommended, or
authorized by this document. This section is intentionally empty of accepted
risk because Option 2 (not ready) was selected in §1/§3 of this session's
required decision process — there is no "starting Task 010 now" to accept
risk against.

---

## 9. Risks not accepted

Unchanged, standing prohibitions — none of the following is authorized by
this document, regardless of which blocker-resolution track (§5) ChatGPT
chooses next:

- Any real Shopify write of any kind.
- Any product/variant export or update code path.
- Any order/customer/inventory/fulfillment coupling or implementation.
- Any hidden or incidental setup-wizard work.
- Any silent assumption about the auth/distribution architecture (MBQ-05
  branch B) baked into code, tests, or a task spec.
- Any silent assumption about Lite/Full packaging/licensing baked into code,
  tests, or a task spec.
- Any implementation gate being treated as opened, extended, or reinterpreted
  by this document.

---

## 10. Decision

- **Recommended next step:** a documentation-only domain naming/schema
  planning pass resolving MBQ-55 for the product-template and product-variant
  binding models (§5, item 1), with MBQ-05 branch B auth-distribution planning
  as an available, non-competing parallel track (§5, item 2). Concurrency
  validation execution remains blocked on runtime access (§5, item 3).
- **Task 010 final implementation prompt:** **not drafted.** Per this
  session's Phase 3 gating rule, the prompt is drafted only if Option 1
  (ready) is selected; this checkpoint selected Option 2 (not ready).
- **Task 010 gate-opening proposal:** **not drafted**, for the same reason.
- **What ChatGPT must review before issuing any implementation prompt:**
  1. This checkpoint's blocker-classification table (§4), specifically the
     "A"-classified items, which are the ones that actually stand between the
     current state and a safe Task 010 gate proposal.
  2. Whether to authorize the MBQ-55 domain-naming/schema planning pass, the
     MBQ-05 branch B planning task, both, or a different priority.
  3. Whether and how to define the "product domain gate" named in
     `ui-ux-implementation-task-map.md` Group 10 — this checkpoint found no
     existing document that specifies its opening criteria, and closing that
     gap is itself a distinct, required ChatGPT act separate from resolving
     MBQ-55.
  4. Only after both §1 preconditions are closed by explicit ChatGPT acts
     should a future session be asked to prepare a Task 010 gate-opening
     proposal and final implementation prompt — mirroring the two-step
     decision-closure-then-gate-opening pattern already used for Tasks 002,
     003, and 006C (AR-025→AR-026, AR-027/028→AR-029, AR-030→AR-031).

**Next step:** ChatGPT review of this checkpoint.

---

## Explicit non-authorizations

This document does not:

- Authorize Task 010, any other domain-sync task, a setup wizard, OAuth/
  token-acquisition code, or any Lite/Full packaging implementation.
- Resolve VAL-B2, MBQ-05, MBQ-55, TD-002, the fulfillment API model, product
  first-sync dedup thresholds, Lite/Full packaging, checkpoint/resume
  ownership, or SRR-03/SRR-04/SRR-09 — every one remains exactly as open as
  its own cited source states.
- Open, define, extend, or reinterpret the "product domain gate" named in
  `ui-ux-implementation-task-map.md` Group 10, or any other implementation
  gate. The only gate ever opened remains the limited core-only, zero-UI gate,
  whose scope Task 006C's own already-merged skeleton already exhausted for
  the core sync-engine.
- Create, modify, or imply authorization for any addon/code, test, manifest,
  XML/security/ACL, migration, CI/workflow, domain module, UI/view/menu/
  action/wizard/controller, webhook, or OAuth file.
- Claim ChatGPT accepted anything in this session. Every "Accepted" reference
  above cites a prior, already-merged acceptance recorded in
  `architecture-review-log.md` or `docs/04-decisions/` — none is a new
  acceptance made by this document.

---

## Evidence / references

- GitHub PR #131, #132, #133, #134 (`AdamsOdoo/Adams`) — retrieved via
  `pull_request_read` this session, 2026-07-09; all four confirmed
  `merged: true`, `state: closed`.
- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
  Group 10 — access: Accessible, this repository, observed 2026-07-09.
- [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`next-task-recommendation-after-task-006c.md`](./next-task-recommendation-after-task-006c.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/task-006c-sync-engine-skeleton-validation-results.md`](../05-qa/task-006c-sync-engine-skeleton-validation-results.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md),
  [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md),
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md),
  [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md),
  [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  (MBQ-55 row and cross-references) — access: Accessible, this repository,
  observed 2026-07-09.
- `addons/shopify_connector_core/models/`, `addons/shopify_connector_core/tests/`,
  `addons/shopify_connector_core/__manifest__.py` — read directly (not
  modified) this session to confirm current module state — access:
  Accessible, this repository, observed 2026-07-09.
- `git log`, `git ls-remote --heads origin` — run directly this session to
  confirm branch state, `main` SHA, and the absence of a plain `dev` branch —
  observed 2026-07-09.

**Next step:** ChatGPT review of this checkpoint and its recommended
blocker-resolution track (§5, §10).
