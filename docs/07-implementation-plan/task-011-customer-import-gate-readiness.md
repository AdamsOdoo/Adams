# Task 011 Customer Import — Gate Readiness Assessment

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Planning only.
> Does not authorize implementation of any kind.** Prepared after PR #138
> (Task 010 product import/variant binding) and PR #139 (Task 010 post-merge
> closure docs) both merged into `Shopify-connector`, latest merge commit
> `297f398da96d11d1f8f9e25a9d15570a66aed80a`, mirroring the structural
> pattern of
> [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md)
> (the Task 010 equivalent), scoped to Task 011 (customer import/matching)
> only. This document consolidates already-recorded facts, decisions, and
> open items from the cited files — it does not itself resolve, narrow, or
> decide any of them, and it does not reopen or reinterpret any accepted
> decision.
>
> **This document does not accept, authorize, or open anything.** Per its
> own findings (§1), it functions as a **blocker-resolution proposal**, not
> a Task 011 gate-opening package — no Task 011 final implementation prompt
> or gate-opening proposal is drafted by this session (see §8).

## Status

- **Not ready to open a Task 011 gate.** Two explicit, named preconditions
  in Task 011's own proposed-scope documents are unmet (§1, §4).
- Confirms PR #138 and PR #139 are merged into `Shopify-connector` (merge
  commits `1f478032d8581a949fa7820847e5c1ab419586b4` and
  `297f398da96d11d1f8f9e25a9d15570a66aed80a` respectively, per this
  session's task instructions).
- Confirms this session's branch (`claude/task-011-customer-readiness-5xunqw`)
  sits exactly at `Shopify-connector` tip
  `297f398da96d11d1f8f9e25a9d15570a66aed80a` (verified via `git merge-base`
  this session) — no drift.
- Confirms `main` is untouched and no plain `dev` branch exists on the
  remote — this session made no commits to either.
- Does not open, extend, or reinterpret any implementation gate. The
  product-domain gate opened for exactly one session (Task 010) and closed
  again the moment PR #138 was opened as draft
  (`product-domain-gate-criteria-proposal.md` §7–§8); it remains closed for
  further product-domain work. No customer-domain or sale-domain gate has
  ever been opened.
- Does not authorize Task 011, Task 012, or any other domain-sync task, a
  setup wizard, OAuth/token-acquisition code, or any Lite/Full packaging
  implementation.

---

## 1. Executive conclusion

**Not ready because specific blockers must be closed first.**

Two explicit, named preconditions in Task 011's own proposed-scope documents
— [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
§"Preconditions", restated in this session's
[`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md)
§4 — remain unmet:

1. **[Fact]** *"The 'sale domain gate' (`ui-ux-implementation-task-map.md`
   Group 11's named prerequisite) explicitly opened."* — **Not opened.**
   `ui-ux-implementation-task-map.md` Group 11 lists "Sale domain gate" as a
   **prerequisite decision**, not a decided/opened one, mirroring exactly
   how Group 10 named the "product domain gate" as a prerequisite before
   `product-domain-gate-criteria-proposal.md` closed that gap for the
   product domain. No document anywhere in this repository defines what
   would need to be true to open the customer-import portion of this gate,
   and no document opens it. This session's
   [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
   proposes such criteria — **proposed only, not yet accepted.**
2. **[Fact]** *"MBQ-55 (exact Odoo partner/binding field mapping) resolved
   via the dedicated documentation-only domain naming/schema planning
   pass."* — **Not resolved.** `master-blueprint-open-questions.md`'s
   MBQ-55 row confirms only the product-template/product-variant portion is
   Accepted (via `mbq-55-product-binding-naming-schema-proposal.md`, PR
   #136); the customer-binding and order-binding portions remain open. This
   session's
   [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
   proposes closure for the customer-binding portion — **proposed only, not
   yet accepted.**

Because Task 011's own proposed documents are explicit that both items are
required before the task "may start," and because neither is a runtime/
live-access item (both are docs-only-resolvable — this session in fact
drafted proposals for both), this assessment cannot honestly conclude Task
011 is ready to gate. It is closer than it was before this session (both
named preconditions now have a drafted, awaiting-review closure proposal),
but neither is yet **accepted**.

**Conclusion label, mirroring the required phrasing used for Task 010:**
*Not ready because specific blockers must be closed first — but both
blockers now have a docs-only closure proposal awaiting ChatGPT review,
mirroring exactly the state Task 010 was in immediately after
`master-implementation-readiness-checkpoint.md` and before
`mbq-55-product-binding-naming-schema-proposal.md`/`product-domain-gate-criteria-proposal.md`
were accepted in PR #136.*

---

## 2. Current accepted foundation

What is complete and merged into `Shopify-connector` as of
`297f398da96d11d1f8f9e25a9d15570a66aed80a` (updates
`master-implementation-readiness-checkpoint.md` §2 with everything that has
merged since):

- **Research baseline and architecture decisions** — unchanged from
  `master-implementation-readiness-checkpoint.md` §2: Research Sprints A–G,
  the Master Blueprint program (Parts A–D), DEC-003 through DEC-025.
- **Core substrate (merged code, `shopify_connector_core`)** — unchanged:
  six accepted core models; credential storage/masking/redaction; read-only
  API client + test-connection service; readiness-check substrate;
  connection lifecycle actions; sync-engine skeleton (job-enqueue/claim/
  dispatch/retry).
- **Product domain (merged code, `shopify_connector_product`) — new since
  the last checkpoint.** PR #138 merged: two concrete binding models
  (`shopify.connector.product.template.binding`,
  `shopify.connector.product.variant.binding`); a read-only
  `shopify.connector.product.importer` service implementing the match-key/
  dedup-threshold sequence; three extension seams, all inside
  `shopify_connector_product_importer.py` only, zero
  `shopify_connector_core` edits. Post-merge Odoo.sh runtime evidence:
  `shopify_connector_core` 187 tests, `shopify_connector_product` 61 tests,
  **0 failed, 0 error(s) of 220 tests**
  (`../05-qa/task-010-product-import-validation-results.md` §K). This is a
  **read-only, backend-only, not-yet-UAT-ready domain slice** — no operator
  can trigger it yet (no enqueue-trigger call site exists).
- **Product-domain gate lifecycle — fully closed, exhausted.** Opened for
  exactly one session (Task 010) via PR #137's acceptance
  (`product-domain-gate-criteria-proposal.md` §7); closed again the moment
  PR #138 was opened as draft (§4/§8 of that same document); this closure is
  unaffected by Task 010's subsequent merge (§8 of that document, "gate
  stays closed" post-merge status note). **No product-domain, customer-
  domain, or sale-domain work is authorized by any of this.**
- **MBQ-55 — product-template/product-variant portion Accepted; customer-
  binding and order-binding portions remain open** (unchanged status, now
  with this session's own customer-binding proposal awaiting review — §1
  above).
- **MBQ-29 — Resolved** (not merely partially resolved), confirmed by this
  session's direct read of the register: one shared fallback partner per
  store is the Phase 1 answer; per-order anonymous identity is explicitly
  non-MVP (AR-020 / `final-mbq-closure-plan.md`, 2026-07-05). This narrows
  what Task 011's future final implementation prompt still needs to decide
  (only exact partner naming/creation mechanics, not the underlying
  granularity question).
- **MBQ-31 — Resolved at blueprint level, unchanged** — email is the sole
  automatic customer match key (DEC-014 point E).
- **Concurrency validation plan (PR #134, merged, still not executed)** —
  unchanged: nine scenarios, three runtime topologies, SRR-03/SRR-04/SRR-09
  pass/fail criteria against the Task 006C claim/dispatch mechanism. **No
  Odoo/Odoo.sh runtime is reachable from this or any prior session's
  environment**, so the plan remains unexecuted. Task 010's own merge and
  green runtime build did not execute this plan — Task 010 reused the
  existing, unmodified dispatch mechanism without adding new concurrency
  scenarios of its own.

---

## 3. Accepted vs proposed vs open

**Accepted (decisions, not implementation authorizations unless noted):**

- DEC-003 through DEC-025 (architecture/scope decisions) — unchanged.
- Task 001–006C, and now **Task 010**, implementation gates — each
  separately opened and each already exhausted by its own merged PR.
- MBQ-55 (product-template/product-variant portion) — Accepted (PR #136).
- MBQ-29, MBQ-31 (customer domain) — Resolved (AR-020) / Resolved at
  blueprint level (DEC-014), both unchanged by this session, only newly
  confirmed/clarified.
- MBQ-59 (automated product/customer/order import create/bind policy) —
  accepted **at blueprint-policy level only**; exact eligibility/match-
  confidence thresholds remain open, for both the product domain (already
  Task 010's own residual, now moot post-merge) and the customer domain
  (Task 011's own future residual — see §5).

**Proposed (not yet accepted as a decision, not authorized) — new this
session:**

- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md) —
  customer-binding portion of MBQ-55; not yet accepted.
- [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md) —
  Task-011-scoped gate criteria; not yet accepted.
- [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md) —
  scope/readiness refresh; not yet accepted (the original
  [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
  it refreshes was itself never formally "Accepted" as a standalone
  decision — it is a proposed-scope document, same status class as
  `task-010-product-import-proposed.md` was before Task 010's own naming/
  gate-criteria acceptance).

**Open questions / recommendations / runtime-only unknowns:** see the full
classification table in §5.

---

## 4. Preconditions — carried forward from the proposed-scope documents

See [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md)
§4 for the full precondition-by-precondition table. Summary: 2 of 4
preconditions satisfied (foundation Tasks 002/003; DEC-014 baseline), 2 of 4
not yet satisfied (sale/customer-domain gate; MBQ-55 customer portion) —
both of the unsatisfied ones now have a docs-only closure proposal drafted
this session, awaiting ChatGPT review.

---

## 5. Blocker classification table (Task 011 scope)

Classification key (mirrors `master-implementation-readiness-checkpoint.md`
§4 exactly):
**A** = blocks Task 011 implementation ·
**B** = does not block Task 011 but blocks later MVP implementation ·
**C** = does not block coding but must remain tracked ·
**D** = requires live/runtime/human access, cannot be solved by docs-only
work.

| Item | Class | Source evidence | Blocks Task 011? | Why / why not | Resolves via |
| --- | --- | --- | --- | --- | --- |
| **Customer-domain gate (not opened; trigger conditions undefined until this session)** | **A** | [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md) §Preconditions; [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md) Group 11 | **Yes — hard blocker** | Named as an explicit precondition; this session drafts criteria (`customer-domain-gate-criteria-proposal.md`) but they are not yet accepted, and even acceptance would not itself open the gate | ChatGPT review/acceptance of the criteria proposal, then a distinct future gate-opening act once every criterion is satisfied |
| **MBQ-55 (customer-binding model/field names)** | **A** | [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md) MBQ-55 row; [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md) §4 | **Yes — hard blocker** | Task 011's own documents state MBQ-55 must be resolved before the task starts; this session drafts a naming/schema proposal but it is not yet accepted | ChatGPT review/acceptance of `mbq-55-customer-binding-naming-schema-proposal.md` |
| **Customer first-sync dedup/match-confidence thresholds (MBQ-59 residual, customer-domain instance)** | **A** | `mbq-55-customer-binding-naming-schema-proposal.md` §12; `master-blueprint-product-customer-sale.md` §B.2/§B.9 | Yes — blocks a §9-precision final prompt, not the docs-only prep track | Deferred by design to Task 011's own future final implementation prompt; policy direction (two-tier gate, blocking preview) is accepted, exact thresholds are not | Task 011's own final implementation prompt (once the gate opens) |
| **Customer fallback-partner store-settings field exact schema** | **A** | `mbq-55-customer-binding-naming-schema-proposal.md` §7.3 | Yes | Field name/home model proposed this session, not yet accepted or confirmed by a final prompt; exact type/default/creation mechanics remain open | Task 011's own final implementation prompt |
| **Address handling** | **A** | `task-011-customer-import-matching-proposed.md` §"Address handling" ("Open — not yet decided in the repo") | Yes — an unaddressed scope gap, must not be assumed either way | No accepted decision anywhere states whether/how Task 011 imports address data; must be explicitly scoped (recommend: excluded from first cut) before a final prompt is issued | Task 011's own final implementation prompt, as an explicit narrow scope decision |
| **Company/person (`is_company`) classification** | **A** | `task-011-customer-import-matching-proposed.md` §"Company/person handling" ("Open — not yet decided in the repo") | Yes | Same reasoning as address handling | Task 011's own final implementation prompt, as an explicit narrow scope decision |
| **Manifest product-dependency question (`shopify_connector_sale` depends on `shopify_connector_product` at Task 011 time or later)** | **A** | `mbq-55-customer-binding-naming-schema-proposal.md` §4 | Yes — affects how Task 011's own manifest is written | Both options are structurally safe; genuinely undecided, narrow, in-task | Task 011's own final implementation prompt, as a named in-task decision (mirrors Task 010's own `res_model`/`res_id` precedent) |
| **Customer import pagination/checkpointing and exact GraphQL query/field list** | **A** | `mbq-55-customer-binding-naming-schema-proposal.md` §10; `task-011-customer-import-matching-proposed.md` §"API needs" ("Open") | Yes | Exact GraphQL shape explicitly left to the final prompt, mirroring Task 010's own identical residual | Task 011's own final implementation prompt |
| **Multi-server/concurrent-worker concurrency proof (SRR-03/04/09)** | **D** | [`../05-qa/sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md); [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md) SRR-03/04/09 | Not a named Task 011 precondition, but a material cross-cutting risk every future domain job (including Task 011's) runs through | `_claim_for_dispatch()`/`try_lock_for_update()` is proven only via `TransactionCase`; live proof requires a runtime this environment does not have; Task 010's own merge did not add new concurrency proof | Future live Odoo.sh/multi-server execution of the existing validation plan |
| **VAL-B2 (no live Shopify Admin API connection ever made)** | **D** | [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) §Status | No — Task 011 would use only the existing Task 003 API client and fake/stub tests; VAL-B2 gates live/production claims, not Task 011's backend code | Requires a human operator with real Shopify Partner/Dev Dashboard access | Execution of `val-b2-closure-plan.md` by a session/operator with that access |
| **MBQ-05 (scalable many-unrelated-customer token-acquisition/distribution)** | **B** | [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) §3.2 branch B | No — Task 011 would consume an already-established store connection; it performs no OAuth/token-acquisition | Blocks the setup wizard's OAuth-connect step and any many-customer distribution claim, not customer-import backend logic | A dedicated MBQ-05 branch B research/decision task (docs-only, available now) |
| **TD-002 (`read_fulfillments` scope-naming correctness)** | **B** | [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md) TD-002 row | No — unrelated to customer import | Depends on the fulfillment API model decision (below) | Fulfillment-domain task, or its own small correction task |
| **Fulfillment API model (legacy `Fulfillment` vs. `FulfillmentOrder`)** | **B** | [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q36; DEC-011/MBQ-42/MBQ-60 | No — unrelated to customer import | Needed only for the future fulfillment-domain task (Task 014) | Fulfillment-domain task's own architecture decision |
| **Lite/Full packaging** | **B** | [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Blocking Question 6, Q21, Q27 | No — does not affect customer-import backend model code | Affects install/licensing shape, not Task 011's own models/logic | A dedicated Lite/Full packaging research/decision task |
| **Setup wizard / operator-facing UI (Customer mapping screen S8)** | **B** | [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md) Group 11; UI implementation gate remains closed | No, for a backend-only Task 011 | Task 011's own documents require the UI gate only for the Customer mapping screen (S8), not its import/binding backend | A separate UI-implementation-gate opening act |
| **Order import (Task 012)** | **B** | [`task-012-order-import-proposed.md`](./task-012-order-import-proposed.md) | No — sequenced after Task 011 per the proposed domain order | Depends on product + customer bindings existing first; its own MBQ-55 order-binding portion and its own gate remain fully open, untouched by this session | Task 012, after Task 011 and its own separate gate |
| **Inventory sync (Task 013), fulfillment/tracking (Task 014)** | **B** | [`task-013-inventory-sync-proposed.md`](./task-013-inventory-sync-proposed.md), [`task-014-fulfillment-tracking-proposed.md`](./task-014-fulfillment-tracking-proposed.md) | No | Sequenced later; each has its own gate | Their own future gates |
| **Product export/update (Task 015, future)** | **C** | `task-010-product-import-proposed.md` — explicitly out of scope | No — unrelated to customer import | Deferred to a separate, not-yet-authorized future candidate task | Future Task 015, its own separate gate |
| **Webhooks** | **C** | DEC-005 (layered sync, "never webhook-only"); DEC-020/MBQ-65 (product-webhook posture accepted, not implemented) | No — Task 011's own documents explicitly exclude webhooks unless separately authorized | Standing, whole-MVP-sequence posture, not specific to Task 011 | Separate, explicit authorization per domain task if/when needed |
| **Live Shopify API validation** | **D** | Same as VAL-B2 row | No | Duplicate framing of VAL-B2 | Same as VAL-B2 row |

This table adds no new blocker beyond what its cited sources already
record, and closes none of them. Every "Open"/"Not yet satisfied" status
above is restated exactly as its own cited source states it, or, for the
new customer-domain-specific rows (fallback-partner schema, address
handling, company/person classification, manifest dependency), restated
exactly as `mbq-55-customer-binding-naming-schema-proposal.md`/
`task-011-customer-import-matching-proposed.md` themselves already state it.

---

## 6. Recommendation

**Not yet Task 011.** The smallest safe next step, available now and
docs-only, mirrors exactly the path that unblocked Task 010:

1. **[Recommendation] Primary: ChatGPT review of
   [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
   and
   [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
   together**, mirroring exactly how the product-template/product-variant
   naming proposal and the product-domain gate-criteria proposal were
   reviewed and accepted together in PR #136 (AR-034). This closes one of
   Task 011's own two named preconditions outright (MBQ-55 customer
   portion) and materially informs the second (defining exactly what the
   customer-domain gate would need to authorize).
2. **[Recommendation] Parallel candidate, unchanged from the Task 010
   checkpoint: MBQ-05 branch B** (scalable many-unrelated-customer
   token-acquisition/distribution architecture) research/decision task —
   still available, still non-competing, still not evaluated.
3. **Not recommended now: concurrency validation execution** — still
   blocked on a live Odoo/Odoo.sh runtime this environment does not have.
   No change since the Task 010 checkpoint.
4. **A ChatGPT act defining the customer-domain gate's own opening
   criteria** — distinct from (1), if ChatGPT does not simply accept this
   session's proposed criteria as-is, a revised or freshly-authored
   criteria act is still required per `CLAUDE.md` §5/§6.

---

## 7. First build task boundary

**Not applicable under this document's conclusion — Task 011 is not
recommended to start, and no build task is authorized by this document.**

For forward reference only, once (and only once) §1's two named
preconditions are actually closed by explicit ChatGPT acts, Task 011's own
already-proposed scope
([`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md),
[`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md),
unchanged by this document) would carry the following boundary:

- Customer import/matching only (Shopify → Odoo, read-only against
  Shopify).
- Email-only automatic matching; phone/name advisory-hint-only, never
  automatic.
- Single, clearly-flagged fallback partner per store for genuine no-PII
  orders only.
- No customer export of any kind.
- No order/product/inventory/fulfillment logic of any kind.
- No setup wizard.
- No webhook.
- No OAuth.
- No Lite/Full packaging implementation.
- No live-Shopify dependency beyond the existing Task 003 API client/
  test-connection foundation, unless explicitly and separately controlled.
- Fake/stub client tests allowed in the absence of a live runtime.
- No broad refactor.

Restating this boundary here does **not** authorize it, start it, or imply
the preconditions in §1 are close to closed.

---

## 8. Risks accepted for starting Task 011

**None.** No implementation of any kind is being started, recommended, or
authorized by this document.

---

## 9. Risks not accepted

Unchanged, standing prohibitions — none of the following is authorized by
this document, regardless of which blocker-resolution track (§6) ChatGPT
chooses next:

- Any real Shopify write of any kind.
- Any customer export code path.
- Any order/product/inventory/fulfillment coupling or implementation.
- Any hidden or incidental setup-wizard work.
- Any silent assumption about the auth/distribution architecture (MBQ-05
  branch B) baked into code, tests, or a task spec.
- Any silent assumption about Lite/Full packaging/licensing baked into
  code, tests, or a task spec.
- Any silent assumption about address handling or company/person
  classification baked into code, tests, or a task spec.
- Any implementation gate being treated as opened, extended, or
  reinterpreted by this document.

---

## 10. Decision

- **Recommended next step:** ChatGPT review of the customer-binding naming/
  schema proposal and the customer-domain gate-criteria proposal together
  (§6, item 1), with MBQ-05 branch B planning as an available, non-competing
  parallel track (§6, item 2). Concurrency validation execution remains
  blocked on runtime access (§6, item 3).
- **Task 011 final implementation prompt:** **not drafted.** Per this
  session's own gating rule, the prompt is drafted only if both named
  preconditions are actually closed; this assessment finds neither is yet.
- **Task 011 gate-opening proposal:** **not drafted**, for the same reason.
- **What ChatGPT must review before issuing any implementation prompt:**
  1. This assessment's blocker-classification table (§5), specifically the
     "A"-classified items.
  2. Whether to accept the customer-binding naming/schema proposal, the
     customer-domain gate-criteria proposal, both, or request revision to
     either.
  3. Whether to authorize the MBQ-05 branch B planning task as a parallel,
     non-competing track.
  4. Only after both §1 preconditions are closed by explicit ChatGPT acts
     should a future session be asked to prepare a Task 011 gate-opening
     proposal and final implementation prompt — mirroring the two-step
     decision-closure-then-gate-opening pattern already used for Tasks 002,
     003, 006C, and 010.

**Next step:** ChatGPT review of this assessment and its recommended
blocker-resolution track (§6, §10).

---

## Explicit non-authorizations

This document does not:

- Authorize Task 011, Task 012, any other domain-sync task, a setup wizard,
  OAuth/token-acquisition code, or any Lite/Full packaging implementation.
- Resolve VAL-B2, MBQ-05, MBQ-55 (customer or order portion), TD-002, the
  fulfillment API model, address handling, company/person classification,
  Lite/Full packaging, or SRR-03/SRR-04/SRR-09 — every one remains exactly
  as open as its own cited source states.
- Open, define, extend, or reinterpret the customer-domain gate, the "sale
  domain gate" named in `ui-ux-implementation-task-map.md` Group 11, or any
  other implementation gate.
- Create, modify, or imply authorization for any addon/code, test, manifest,
  XML/security/ACL, migration, CI/workflow, domain module, UI/view/menu/
  action/wizard/controller, webhook, or OAuth file.
- Claim ChatGPT accepted anything in this session. Every "Accepted"/
  "Resolved" reference above cites a prior, already-merged acceptance
  recorded in `architecture-review-log.md` or `docs/04-decisions/` — none is
  a new acceptance made by this document.

---

## Evidence / references

- GitHub PR #138, PR #139 (`AdamsOdoo/Adams`) — merge commits
  `1f478032d8581a949fa7820847e5c1ab419586b4` and
  `297f398da96d11d1f8f9e25a9d15570a66aed80a` — per this session's task
  instructions.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md),
  [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
  [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md) —
  companion documents drafted this session — access: Accessible, this
  repository, observed 2026-07-09.
- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  (MBQ-05, MBQ-29, MBQ-31, MBQ-55, MBQ-59 rows) — access: Accessible, this
  repository, observed 2026-07-09.
- [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
  [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md),
  [`../05-qa/sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md),
  [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md),
  [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) —
  access: Accessible, this repository, observed 2026-07-09.
- `git log`, `git merge-base` — run directly this session to confirm branch
  state and the absence of drift from `Shopify-connector` tip — observed
  2026-07-09.

**Next step:** ChatGPT review of this assessment and its recommended
blocker-resolution track (§6, §10).
