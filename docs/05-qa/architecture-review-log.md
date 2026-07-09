# Architecture Review Log

> Tracks architecture discussions **before** they become finalized decision
> records. An entry here is a proposal under review (typically reviewed by
> ChatGPT), not a commitment. Accepted proposals are promoted to an ADR in
> [`../04-decisions/`](../04-decisions/) and linked back here.

## How to use

1. Add a row when an architectural approach is proposed or debated.
2. **Review decision** vocabulary: `accepted` / `accepted with minor
   corrections` / `revise` / `reject`.
   - `reject` → also log in
     [`rejected-approaches-log.md`](./rejected-approaches-log.md).
   - `accepted` → create an ADR (`../04-decisions/`) and put the link in
     **Follow-up action**.
3. **Evidence required** must name concrete proof needed (a Shopify/Odoo
   capability, a competitor behaviour, a benchmark) before acceptance. Do not
   accept while required evidence is missing.
4. **Status** values: `Proposed`, `Under review`, `Evidence pending`,
   `Accepted → ADR`, `Rejected`, `Deferred`.

> Read this log **before finalizing any design** so prior outcomes are not
> re-litigated or contradicted.

---

## Log

| ID | Date | Topic | Proposed approach | Review decision | Reason | Evidence required | Risks | Follow-up action | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _AR-000_ | _YYYY-MM-DD_ | _e.g. Sync orchestration model_ | _Short description_ | _accepted/revise/reject_ | _Why_ | _Proof needed_ | _Key risks_ | _ADR link / next step_ | _Proposed_ |
| AR-001 | 2026-06-30 | Governance foundation branch | Use the Research Sprint A branch (`docs/research-sprint-a-governance-inventory`) as the canonical governance foundation | Accepted after revision patch | It defers active skills/agents and preserves the no-code, research-first gate | n/a — governance/process decision | Branch divergence if the earlier `claude/odoo-shopify-research-setup-fs4wzi` branch is reused | Do not continue from the old branch; treat it as non-canonical unless ChatGPT explicitly reopens it | Accepted |
| AR-002 | 2026-06-30 | API strategy: REST vs GraphQL vs hybrid | To be researched / evidence pending — candidates: GraphQL-Admin-only; a REST-where-simpler hybrid; GraphQL + Bulk Operations for backfill | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: REST is legacy (2024-10-01) and new public apps are GraphQL-only (2025-04-01), but the custom/non-public scope is open (`../01-research/shopify-official-api-notes.md`) | Confirm target distribution (public App Store vs custom app); any REST sunset date; GraphQL coverage gaps for needed resources | REST = dead end for public apps; GraphQL calculated-cost model adds throttling complexity | RB-14 → **accepted** [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-003 | 2026-06-30 | Sync orchestration model | To be researched / evidence pending — candidates: `ir.cron`-only; webhooks + cron reconciliation; OCA `queue_job`-based | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: Shopify webhook delivery is not guaranteed (reconciliation required); Odoo core has **no** official job queue (only `ir.cron`); `queue_job` is community | Whether to adopt OCA `queue_job` (Jobrunner/dependency cost); cron throughput (`--max-cron-threads`); 5s webhook-ack constraint; competitor patterns (RB-07) | Webhook-only → silent data drift; cron-only → latency/throughput limits; `queue_job` → non-core dependency | RB-14 → **accepted** [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-004 | 2026-06-30 | Module boundaries (addon family) | **Accepted by ChatGPT** (2026-07-02, via DEC-008) — layered domain-aligned addon family (`shopify_connector_core`/`product`/`sale`/`inventory`/`fulfillment` for Phase 1), strict dependency DAG, cross-cutting substrate concentrated in `core` | **Accepted by ChatGPT** (2026-07-02 — see note below) | Odoo docs favour link modules; exact boundaries decided against the accepted AR-002/003/005 baseline | See [`../03-architecture/ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md) for options considered and evidence | One-giant-module (A-MOD-1) and over-fragmentation (A-MOD-2) both evaluated and avoided; dependency coupling | RB-14 → **accepted** [`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-005 | 2026-06-30 | Mapping & duplicate prevention | To be researched / evidence pending — candidates: reuse `ir.model.data` external IDs vs a dedicated per-store binding model (Shopify GID ↔ Odoo `res_id`) | **Accepted by ChatGPT** (2026-07-02 — see note below) | External IDs give an idempotent, db-id-independent handle, but users can delete them and multi-store needs per-store keys (`../01-research/odoo-official-architecture-notes.md`) | `ir.model.data` `(module,name)` uniqueness (open question); Shopify GID stability; competitor dedup approaches | Duplicate records / double-decrement if keys are wrong (cf. `quality-feedback-loop.md` §5); bound-record deletion | RB-14 → **accepted** [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-006 | 2026-06-30 | Error handling & retries | **Accepted by ChatGPT** (2026-07-02, via DEC-009) — classified retry policy (auto-retry only safe/transient classes), job-source/state/error-class taxonomy, layered idempotency (platform + connector-designed keys), recovery-first logs/audit | **Accepted by ChatGPT** (2026-07-02 — see note below) | `ir.cron` auto-deactivates after repeated failures; Shopify returns 429/throttle and requires `@idempotent` on some mutations (2026-04) | See [`../03-architecture/ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md) for taxonomy tables and evidence | Missing retry → lost syncs; naive retry → duplicates / rate-limit storms — both evaluated and avoided via error-class taxonomy | RB-14 → **accepted** [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-007 | 2026-06-30 | Inventory architecture | **Accepted by ChatGPT** (2026-07-02, via DEC-010) — Odoo as ongoing source of truth for Shopify inventory write-back; controlled first-sync import; inventory identity keyed on `(store, inventory_item_id, location_id)`; explicit non-inferred location mapping; DEC-007 first-push guard honored in full; layered sync trigger; write only Shopify `available` (Phase 1 default target; `on_hand` allowed but not default without explicit Master Blueprint justification; `committed` never written) | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: Shopify `committed` is API-read-only (order-driven), `on_hand` is a sum, set/adjust need `@idempotent` (2026-04), multi-location mapping required; Odoo 19.0 official "On Hand"/"Free to Use"/"Forecasted" report concepts newly verified 2026-07-02 | Exact Odoo implementation source/field/formula behind "Free to Use" (`stock.quant` or another mechanism, not verified); exact quantity-field default; exact cron cadence; exact fulfillment-location-confirmation mechanism (ownership clarified: `core` may hold a Shopify Location reference, `inventory` keeps the mapping, `fulfillment` never depends on `inventory`) | Double-decrement of multi-location SKUs; attempting to write `committed`; over/under-sell on drift | RB-14 → **accepted** [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-008 | 2026-06-30 | Fulfillment architecture | **Accepted by ChatGPT** (2026-07-02, via DEC-011) — validated `stock.picking` as trigger; FulfillmentOrder-based mutations only; matched order/FulfillmentOrder/line/quantity via `lineItemsByFulfillmentOrder`; DEC-007 no-notification-by-default guard honored in full; single-fulfillment-location Phase 1 posture, multi-package/multi-location deferred | **Accepted by ChatGPT** (2026-07-02 — see note below) | Tier-1: legacy Order/Fulfillment workflow unsupported since 2022-07; one fulfillment per order + location; tracking via `fulfillmentTrackingInfoUpdate`; neither fulfillment mutation is on Shopify's 17-mutation `@idempotent` list | Exact tracking-reference field name; exact backorder-to-picking linkage; exact notification-UI granularity; exact operation-level idempotency key schema (operation type + Shopify target ID + payload/version hash, conceptually set); exact fulfillment-location-confirmation mechanism (ownership clarified, mirrors AR-007) | Using legacy fulfillment endpoints; multi-location mismatch; double fulfillment on ambiguous retry; hidden customer notification | RB-14 → **accepted** [`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (Accepted by ChatGPT, 2026-07-02) | **Accepted** |
| AR-009 | 2026-07-02 | UX/operator-flow strategy | **Accepted by ChatGPT** (2026-07-03, via DEC-012) — ten operator flows (initial setup wizard, store settings, dashboard/command center, sync center/job monitor, error center/recovery, matching/duplicate-prevention, product import/export/update, inventory, fulfillment, conceptual permissions/roles), each built directly on the already-accepted DEC-003 through DEC-011 "UX implications" sections and the accepted `setup-ux-principles.md`/`product-vision.md` product inputs | **Accepted by ChatGPT** (2026-07-03 — see note below) | Builds on Tier-1-grounded, already-accepted DEC-003 through DEC-011 architecture; no new Tier-1 evidence required — this is a UX-structure synthesis of already-accepted decisions, not a new platform-fact claim | Whether the ten-flow structure fully covers the operator experience without pre-deciding Odoo-level implementation; ChatGPT/Fable review of `ux-operator-flow.md` and the architecture bridge — reviewed, Fable returned ACCEPT WITH MINOR CHANGES, fix-up applied | A UX proposal drifting from or contradicting an accepted DEC-003–011 "UX implications" section or a binding RA row; a UX proposal implicitly deciding the DEC-008 feature-flag mechanism instead of only its operator-facing experience | RB-14 → **accepted** [`../04-decisions/DEC-012-ux-operator-flow-strategy.md`](../04-decisions/DEC-012-ux-operator-flow-strategy.md) (Accepted by ChatGPT, 2026-07-03) | **Accepted** |
| AR-010 | 2026-07-03 | Master Blueprint core/common substrate | **Accepted via [`DEC-013`](../04-decisions/DEC-013-master-blueprint-core-substrate.md)** — Master Blueprint index + Part A core/common substrate blueprint: `shopify_connector_core` boundary/extension seams; store/credential/API-health/Location-reference/settings concepts; binding abstraction with the accepted per-domain-concrete-on-core-contract schema-shape direction (the fork DEC-006/DEC-008 routed here; resolves MBQ-11); job/log/error/retry abstraction (6 sources / 10 states / 16-class registry, generalized operation-level idempotency key + serialization guard); setup-wizard/dashboard/sync-center/error-center blueprints per DEC-012; the DEC-008-routed feature-flag mechanism direction (store-scoped core settings record, domain-extended; no flag bypasses a safety guard; resolves MBQ-07 at blueprint-direction level); a blueprint-level four-role access matrix (no CSVs, proposed names only; role hierarchy accepted, resolving MBQ-45 partially and MBQ-47 fully); ten cross-module extension rules; open-questions register MBQ-01–MBQ-54 | **Accepted by ChatGPT** (2026-07-03 — see acceptance note below) | Synthesizes only already-accepted DEC-003 through DEC-012 content plus explicitly-routed blueprint forks; no new Tier-1 platform-fact claim introduced; no web research performed | ChatGPT/Fable review of the three blueprint documents against DEC-003–012 and RA-001–023 — reviewed, Fable returned ACCEPT WITH MINOR CHANGES, fix-up + tiny consistency fix applied before merge; headline review items MBQ-04/07/08/11/45/47, plus MBQ-53 (UI/UX Screen Design Blueprint) and MBQ-54 (domain-module uninstall/disable data lifecycle), added per Fable's PR #70 review | Blueprint detail being read as code-level commitment (mitigated: proposed-names-only discipline, MBQ-01/02/03/44); a blueprint proposal silently exceeding an accepted DEC (mitigated: every extension labelled [Blueprint proposal]/[Accepted — DEC-013] with its accepted source cited) | RB-14 → **accepted** [`../04-decisions/DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md) (Accepted by ChatGPT, 2026-07-03); next → Master Blueprint Sprint B (product/customer/sale-order domain blueprint), not started | **Accepted** |
| AR-011 | 2026-07-03 | Master Blueprint Product, Customer, and Sale/Order Domain Blueprint | **Accepted via [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)**, revised twice on 2026-07-03 (PR #72 ChatGPT review, then PR #72 Fable review) before acceptance — Master Blueprint Part B: product-template/product-variant binding under `shopify_connector_product`; customer/order binding under `shopify_connector_sale`; product import/export/update flow (variant-mutation-strategy direction citing both `productVariantsBulkCreate` and `productVariantsBulkUpdate` official docs, draft/publish mechanism via `Product.status`+`publishablePublish`, media/price handling per DEC-007 §2/§3, corrected §A.4 wording so an update job requires an explicit operator action, never an ordinary Odoo write alone); customer import/matching (default-customer-fallback direction, **accepted at blueprint level** email-only match-key recommendation, MBQ-31); order import (whole-order-hold rule for unmatched product lines, **three-path** customer-resolution rule reconciled with the domain-brief "one bad customer record does not block order import" posture, total-check guard definition, **narrowed** §C.12 order-edit/`ORDERS_UPDATED` posture — evidence-refresh only, no silent sale-order-line writes, divergence routed to the total-check guard, webhook/reconciliation consistency (**Fable B2 route, accepted**), **accepted at blueprint level** order-import operator-touchpoint recommendation with inline financial-evidence breakdown and direct matching-flow links (MBQ-26), gateway→journal mapping concept, generalized order-scope wording in the error-class table); the **automated import create/bind policy, accepted at blueprint-policy level** (MBQ-59 — pre-create duplicate check + two-tier eligibility/match-quality gate, routed via **accepted Part A per-class mechanisms** — not a single collapsed `blocked_manual_review` state — replacing both the withdrawn "retrospective visibility satisfies preview" reading and the withdrawn "every gate failure is `blocked_manual_review`" reading); manual-review triggers (§C.13) and §G/§I corrected to distinguish `failed_retryable`/"manual fix then retry" from `blocked_manual_review`'s six confirmation-required sub-classes from `financial total mismatch`'s own "conservative, never silent" posture, without widening Part A §D.8's vocabulary (**Fable B1 route, accepted**); cross-domain sequencing; consolidated error/retry-class mapping (no new class added to the fixed 16-class registry); open-questions register updates — **MBQ-23/25/29/30 partially resolved; MBQ-26/31/59 accepted at blueprint(-policy) level; MBQ-04/08/24/27/28/53/54/55/56/57/58 remain open** — with original question text restored for MBQ-23–27/29–31/59 | **Accepted by ChatGPT** (2026-07-03 — see acceptance note below) | Synthesizes already-accepted DEC-003/006/007/012/013 content; three small, targeted official-doc checks performed (Shopify `productSet`/`productVariantsBulkCreate`/`productVariantsBulkUpdate`/`Product.status`/`publishablePublish` reference pages, accessed 2026-07-03; Odoo 19 accounting/taxes documentation, accessed 2026-07-03, inconclusive) — no broad research performed, per the sprint's "targeted checks only" instruction | ChatGPT review of the Part B blueprint document, then **Fable review, which returned REVISE** — governance was clean and Sprint B's substance did not require redesign, but three findings (B1 routing/state semantics, B2 order-edit/`ORDERS_UPDATED` scope, B3 MBQ-59 acceptance-status labels) plus twelve minor issues required a focused fix, applied before this row's acceptance; **ChatGPT then accepted DEC-014 on 2026-07-03** | Blueprint detail being read as code-level commitment (mitigated: proposed-names-only discipline continued from Part A, MBQ-01/02/55 unresolved); **the ChatGPT-revision draft silently amended accepted DEC-013 state semantics by routing `mapping missing`, `financial total mismatch`, `data shape/schema mismatch`, and every MBQ-59 gate failure into `blocked_manual_review` as if all were among Part A §D.8's six confirmation-required sub-classes — Fable flagged this as B1; mitigated by correcting §A.2/§B.2/§C.5/§C.8/§C.13/§G/§I to accepted Part A per-class routing (`failed_retryable` for "manual fix then retry" classes, `financial total mismatch`'s own §D.5.5 posture, `blocked_manual_review` only for its four Sprint-B-relevant confirmation-required classes), without widening §D.8's vocabulary — this corrected routing is now accepted as final (DEC-014 point I)**; **§C.12 silently un-deferred order-edit handling by letting an `ORDERS_UPDATED` webhook update existing sale-order line quantities/evidence through the normal update path — Fable flagged this as B2; mitigated by narrowing §C.12 to evidence-refresh only, with any divergence routed through the total-check guard and webhook/reconciliation paths behaving identically — this narrowed posture is now accepted as final (DEC-014 point J)**; **§A.2's Flow bullet and heading presented the MBQ-59-gated automated create/bind mechanism as already `[Accepted — DEC-003; DEC-006]` — Fable flagged this as B3; mitigated by separating the accepted import capability from the then-pending automated mechanism throughout §A.2/§C.6.2 — MBQ-59's policy is now itself accepted at blueprint-policy level by DEC-014 (point H), exact implementation detail remains open**; an unverified `read_all_orders` scope claim in the error-class table (mitigated: generalized to "missing required order read scope / protected-customer-data approval," already covered by MBQ-06/MBQ-09); MBQ-26/MBQ-31 recommendations being mistaken for already-decided outcomes (mitigated: both explicitly labelled "recommendation to ChatGPT" throughout, both name their register decision owner as ChatGPT (Sprint B); **ChatGPT has now made both decisions via DEC-014**) | RB-14 → **accepted** [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) (Accepted by ChatGPT, 2026-07-03; revised twice on 2026-07-03 per PR #72 ChatGPT review and PR #72 Fable review before acceptance); next → Master Blueprint Sprint C (inventory/fulfillment domain blueprint), not started | **Accepted** |
| AR-012 | 2026-07-03 | Master Blueprint Inventory and Fulfillment Domain Blueprint | **Accepted via [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)** — Master Blueprint Part C: inventory-level binding under `shopify_connector_inventory` keyed `(store, inventory_item_id, location_id)`; Shopify Location reference/Odoo location-mapping posture restated from DEC-010; the ongoing Odoo-source-of-truth posture with a controlled one-time baseline import; a **proposed quantity-source direction** (`product.product.free_qty` / `stock.quant.available_quantity`, both newly cited against official Odoo 19.0 source but **corrected as non-equivalent per Fable finding C1** — they diverge whenever expired unreserved stock exists, so the source choice is substantive, not decided here — proposing to partially resolve MBQ-32); a first-push-guard granularity **recommendation** (MBQ-33) and confirmation-record concept (MBQ-38) for ChatGPT's review; update-direction, sync-posture, idempotency/retry, mapping-failure, multi-location, product/variant-binding-dependency, and safety-guard sections; inventory job types and error/retry mapping; FulfillmentOrder/Fulfillment binding under `shopify_connector_fulfillment`, never depending on `inventory`; the FulfillmentOrder-exclusive and validated-`stock.picking`-trigger postures restated from DEC-011; order/FulfillmentOrder/line/quantity matching via `lineItemsByFulfillmentOrder`; a **proposed tracking-field resolution** (`stock.picking.carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id`, newly cited against official Odoo 19.0 source, proposing to resolve MBQ-39, surfacing new question MBQ-60 on the `stock_delivery` module dependency); customer-notification posture with a **recommendation** for MBQ-41; partial/backorder/cancellation/return/refund/multi-package posture, with an official `backorder_id`/`backorder_ids` citation partially resolving MBQ-40; a **proposed location-mismatch-guard mechanism** partially resolving MBQ-42/MBQ-43 — **including an explicit, named proposal to widen the accepted `ambiguous match` class (AR-006/DEC-009: multiple candidates) to also cover a deterministic location mismatch, per Fable minor finding 2 — now accepted at blueprint level only by this acceptance, not an already-settled reading of AR-006/DEC-009**; idempotency/retry/webhook/reconciliation posture, including newly cited Shopify `INVENTORY_LEVELS_UPDATE` and `FULFILLMENT_ORDERS_*`/`FULFILLMENTS_*` webhook topics (proposing to resolve MBQ-37; surfacing new question MBQ-61 on FulfillmentOrder lifecycle events); fulfillment job types and error/retry mapping — **with the Odoo-event-triggered job-source classification for both inventory push and fulfillment creation left undecided per Fable finding C2, routed to new MBQ-62 rather than silently treating "event-driven enqueue" as a Part A job-source value**; cross-domain sequencing; consolidated error/retry-class mapping (no new class added to the fixed 16-class registry, and the two Part A/B-only-named classes — "inventory location missing," "fulfillment notification confirmation missing" — are instantiated for the first time); open-questions register updates — **MBQ-37/39 resolved at fact-verification level; MBQ-32/36/38/40/42/43 partially resolved; MBQ-33/34/41 remain open, carried forward with a recommendation each, not decided by this acceptance; MBQ-35 carried forward unchanged; MBQ-60 through MBQ-63 remain new and open (MBQ-62/63 added in a Fable-review revision on PR #74, covering job-source classification and the inventory-webhook payload/subscription residual respectively)** | **Accepted by ChatGPT** (2026-07-03 — see acceptance note below) | Synthesizes already-accepted DEC-003/006/007/008/009/010/011/013/014 content; six small, targeted official-doc checks performed this sprint (Shopify `WebhookSubscriptionTopic` enum, accessed 2026-07-03; Odoo 19.0 `odoo/odoo` GitHub source for `stock.quant`, `product.product.free_qty`, `stock.picking.backorder_id`, and `stock_delivery`'s `stock.picking.carrier_tracking_ref`/`carrier_tracking_url`, all accessed 2026-07-03) — no broad research performed, per the sprint's "targeted checks only" instruction; no fact was found inconclusive, no source was inaccessible | Reviewed — Fable returned **REVISE** (findings C1/C2 plus seven minor findings, all fixed on PR #74), followed by a same-PR consistency patch aligning new-MBQ summary wording; **ChatGPT then accepted DEC-015 on 2026-07-03** | Blueprint detail being read as code-level commitment (mitigated: proposed-names-only discipline continued from Part A/B; the Odoo field names cited this sprint — `free_qty`, `carrier_tracking_ref`, `backorder_id`, etc. — are existing Odoo-core/Odoo-module fields being read/written, not connector-proposed names, MBQ-01/02 unresolved); the `stock_delivery` module-dependency question and the FulfillmentOrder-lifecycle-webhook question being silently absorbed rather than surfaced (mitigated: both explicitly logged as new, open MBQ rows — MBQ-60, MBQ-61 — not asserted as settled); MBQ-33/34/41 recommendations being mistaken for already-decided outcomes (mitigated: all three explicitly labelled "recommendation to ChatGPT" throughout, naming ChatGPT as the register decision owner); **an initial draft over-claimed `product.product.free_qty` and `stock.quant.available_quantity` were equivalent — Fable flagged this as finding C1; mitigated by correcting §A.4/§G/the register/DEC-015 point A to state the exact, non-equivalent relationship (UoM rounding, the `expired_unreserved_qty` term) and that the source choice is substantive**; **an initial draft silently listed "event-driven enqueue" as a Part A job-source enum value and left fulfillment creation's own source classification unstated — Fable flagged this as finding C2; mitigated by distinguishing the sync-trigger layer from Part A §D.2's fixed job-source vocabulary throughout §A.7/§A.13/§B.12/§C item 7 and routing the classification question to new MBQ-62**; **§B.8's reuse of `ambiguous match` for a deterministic location mismatch was not framed as a widening of an accepted class — Fable minor finding 2; mitigated by stating AR-006/DEC-009's original "multiple candidates" definition explicitly and naming the reuse as a widening — this widening is now accepted as final, at blueprint level only (DEC-015 point J)**; **MBQ-37/39's register cells read as overly optimistic before acceptance — Fable minor finding 3; mitigated by restoring conservative, Yes-leading wording, and MBQ-37's payload/subscription residual was routed to new MBQ-63 per Fable minor finding 4 — both cells now resolve to "No" for the verified facts themselves, with the MBQ-37 residual still routed to, and still blocking, only MBQ-63** | RB-14 → **accepted** [`../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md) (Accepted by ChatGPT, 2026-07-03); next → Master Blueprint Part D (UI/UX Screen Design Blueprint) or Part E (implementation-planning bridge), neither started | **Accepted** |
| AR-013 | 2026-07-03 | Master Blueprint UI/UX Screen Design Blueprint | **Accepted via [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)** — Master Blueprint Part D ([`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md)): converts the ten accepted DEC-012 operator flows + accepted Part A/B/C blueprints into a single-shared-surface screen inventory (one role-gated dashboard/sync-center/error-center/manual-review queue; domains contribute, never fork — RA-013); a navigation/information-architecture proposal (menu tree + inter-screen routing + role-gated visibility); Odoo-native interaction patterns (reused vs custom, blueprint level); a global empty/loading/success/error/manual-review state model; blueprint-level screen specs for setup wizard, store settings, dashboard, sync center, error center + manual-review queue, matching/duplicate-prevention center, product diff, customer review, order-import touchpoints (no dedicated screen, delivering the two DEC-014/MBQ-26 error-center extensions), inventory location-mapping/first-push/settings, fulfillment log/notification/mismatch, and conceptual permissions/roles; a UX-copy/error-message **style guide** (not final copy); cross-screen consistency rules; and a premium UI/UX acceptance checklist. Reuses the fixed 6 job sources / 10 job states / 16 error classes / 6 manual-review sub-reasons / 4 roles verbatim; invents no identifier. **Partially resolves MBQ-53 at screen-design blueprint level only (marked Partially resolved by DEC-016); blueprint refined pre-review by a capability audit + six-lens expert-review pass, then by a competitor screenshot UX benchmark traceability audit + Fable Sprint D review fixes (F1–F7) (all docs-only, no architecture change).** | **Accepted by ChatGPT** (2026-07-04 — see acceptance note below) | Synthesizes already-accepted DEC-003 through DEC-015 + DEC-012 flows + Part A/B/C content plus `product-vision.md`/`setup-ux-principles.md` **recommendation-level** UX inputs; no new Tier-1 platform-fact claim introduced; no web research performed (screen-design synthesis of already-accepted decisions) | Reviewed — ChatGPT/Fable review of the Part D document against DEC-012, Part A/B/C, and RA-001–023, following duplicate-PR reconciliation (PR #75 closed as superseded) and the competitor screenshot UX benchmark traceability audit; confirmed that (a) the single-shared-surface rule and the two order-import error-center extensions (MBQ-26) are correctly carried, (b) no open recommendation (MBQ-33/34/41/45/35/06) is written as decided, and (c) MBQ-53 is only partially (not fully) resolved; **ChatGPT then accepted DEC-016 on 2026-07-04, at screen-design blueprint level only** | Screen spec read as code-level commitment (mitigated: proposed-names-only discipline continued from Part A/B/C; every model/field/menu/group/label/copy name flagged proposed-only, MBQ-01/02/03/22/44 unresolved); an open recommendation mistaken for a decision (mitigated: MBQ-33/34/41/45/35/06 each labelled open, screens designed to accommodate either resolution); over-claiming MBQ-53's resolution (mitigated: register row marked **Partially resolved by DEC-016 at screen-design blueprint level**, sibling open rows explicitly flagged); a differentiation/vision item cited as an accepted Decision (mitigated: product-vision/setup-ux-principles cited as recommendation-level inputs that "decide nothing", reconciled against DEC-003); this acceptance being mistaken for a pixel-level visual-design or implementation-authorizing approval (mitigated: DEC-016 and this row both state explicitly that pixel-level visual design/final wireframe polish, including the `sh_shopify_connector` "Daily Queue Activity Tracking" chart idea, remain deferred and not adopted, and that implementation remains blocked) | RB-14 → **accepted** [`../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md) (Accepted by ChatGPT, 2026-07-04); next → Master Blueprint Part E (implementation-planning bridge), not started | **Accepted** |
| AR-014 | 2026-07-04 | Master Blueprint Part E — Implementation-Planning Bridge | **Accepted via [`DEC-017`](../04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md)** — Master Blueprint Part E ([`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)): a documentation-only planning bridge, opened after PR #79 merged into `Shopify-connector` and directly executing the PR #78 Master Blueprint Integrity & Competitor Advantage Audit's own §10 "Required Part E focus areas" as its scoped work — an MBQ decision plan routing ~45 implementation-blocking open questions (MBQ-01–63) to a decision owner, decision type, and recommended timing, **accepted as a routing/sequencing plan only, none resolved or closed by this table**; two new open-questions-register rows, **MBQ-64** (Shopify `MoneyBag`/presentment-currency order-money model vs. Odoo's single computed `sale.order.currency_id`, both verified against official sources 2026-07-04 — **accepted at fact-verification level by DEC-017; the design/selection question itself is not decided**) and **MBQ-65** (Shopify product-domain webhook topic strings `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`, **resolved at fact-verification level only by DEC-017**; the payload/subscription/scope residual remains open); a proposed module-by-module implementation sequence following the already-accepted DEC-008 dependency DAG (`core` → `product` → `sale`/`inventory` → `fulfillment`), **accepted as planning guidance only, not locked**; a first-safe-implementation-slice **recommendation** (the job/log/error abstraction skeleton, MBQ-19/20/21 — **accepted as a recommendation only, not thereby authorized to start**); test-strategy and rollback-strategy notes at planning level only; and a restated no-code-to-code gate checklist (2 of 5 criteria satisfied, **unchanged by this acceptance**). **Does not authorize implementation; does not open the implementation gate; does not change any accepted DEC-003–016/Part A–D status; resolves no existing MBQ row beyond MBQ-64/MBQ-65's own fact-verification-level status; decides no ChatGPT-batch MBQ item.** | **Accepted** | Synthesizes already-accepted DEC-003 through DEC-016 + Part A–D content plus the PR #78 audit's own findings/recommendations (§4/§8/§10) as its work plan; two small, targeted official-doc checks performed this session (Shopify `MoneyBag`/`Order` money fields + `WebhookSubscriptionTopic` product topics, accessed 2026-07-04; Odoo `sale.order.currency_id` + `res.currency.rounding`/`round()`/`compare_amounts()` against official 19.0 source, accessed 2026-07-04) — no broad research performed, per the PR #78 audit's own recommended scope; no fact was found inconclusive on the pages/source actually fetched, though two narrower sub-questions (Markets-independence of presentment-currency divergence; product-webhook payload/scope) remain explicitly open, not asserted, and **not resolved by this acceptance** | Reviewed by ChatGPT — confirmed that no MBQ row is silently resolved beyond MBQ-64/MBQ-65's own stated fact-verification-level status, and that every "Proposed Part E action" cell in the MBQ decision plan reads as a recommendation, not a decision; **ChatGPT then accepted DEC-017 on 2026-07-04**; the MBQ decision plan's own ChatGPT-batch items (MBQ-06/08/17/33/34/41/45/52/54/60/62, roughly) still need ChatGPT's actual decision — accepting this plan is not the same act as deciding those items | A recommendation being mistaken for a decision (mitigated: every "Proposed Part E action" cell in §4 explicitly labelled as a recommendation; DEC-017's own "MBQ impact" and "What this acceptance does NOT authorize" sections restate that no ChatGPT-batch item is decided); MBQ-64/MBQ-65 being read as fully resolved (mitigated: DEC-017 explicitly labels each **fact-verification level only**, with each row's own design/selection or residual question named as still open); this record or its document being mistaken for a gate-opening act (mitigated: §3 of the Part E document restates the five gate criteria, confirms only 2 of 5 are satisfied, and now explicitly states DEC-017's acceptance does not change that count; DEC-017's own "Implementation gate status" section restates the gate is still closed) | **Accepted**; next → the MBQ decision plan's own ChatGPT-batch decisions (§4 of the Part E document), then a separate, explicit ChatGPT implementation-gate-opening act — neither performed by this record | **Accepted** |
| AR-015 | 2026-07-04 | MBQ Decision Batch 1 | **Accepted via [`DEC-018`](../04-decisions/DEC-018-mbq-decision-batch-1.md)** — a controlled first decision batch executing Part E's own "ChatGPT batch" (§4): decisions, with evidence/options/risk/register-impact wording now applied, for **MBQ-06** (readiness-check essential-vs-nice-to-have split), **MBQ-08** (store-disconnect data-retention posture), **MBQ-17** (reconciliation cadence/scope posture only), **MBQ-33** (first-push guard granularity), **MBQ-34** (ongoing inventory apply mode), **MBQ-41** (fulfillment notification-UI granularity), **MBQ-45** (roles→groups mapping / admin-vs-functional surface split), **MBQ-52** (Shopify API-version pinning/upgrade policy only), **MBQ-54** (domain-module uninstall/disable lifecycle posture only), and **MBQ-60** (`stock_delivery`/`delivery` dependency for fulfillment tracking) — each adopting a direction an already-accepted Master Blueprint part (mostly DEC-013/DEC-015) already carried as a ChatGPT-owned recommendation, none new architecture. **MBQ-62** (Odoo-event-triggered job-source classification) is **not decided** — DEC-018 §4 checked it against all six fixed Part A §D.2 job-source values, found none a defensible fit, and recommended splitting it into its own dedicated follow-up decision record rather than repeating the exact unauthorized-vocabulary-extension failure mode Fable's finding C2 already caught during DEC-015's review; **ChatGPT accepted that split recommendation**. **MBQ-64 and MBQ-65 remain explicitly out of scope**, routed to a separate currency/webhook residual decision sprint. **No MBQ row other than the ten named above (plus MBQ-62's own split-note) is resolved, marked accepted, or silently changed by this acceptance — every other row in the register remains exactly as open as before.** | **Accepted by ChatGPT** (2026-07-04 — see acceptance note below) | Synthesizes already-accepted DEC-013/DEC-015 recommendations (as quoted in this log's AR-010/AR-012 rows and in the open-questions register's own acceptance-patch notes) plus Part A/C blueprint sections (§B.1/§B.3/§D.2/§E.1–E.6/§I.3–I.4/§J.1–J.2; §A.5/§A.7/§B.5/§B.6) read directly the proposing session; no new Tier-1 platform-fact claim introduced; no external Shopify/Odoo research performed — every accepted decision rests on evidence Parts A/C and DEC-013/015 already established and cited | Reviewed by ChatGPT — checked against `rejected-approaches-log.md` (RA-008 blind first-push, RA-009 hidden/default-on notification, and the full RA-001–023 list) before proposing; none of the ten accepted decisions reintroduces a binding rejected approach; MBQ-62 checked with special strictness per the task's own instruction and found not to have a defensible existing-vocabulary mapping — split recommendation accepted rather than forced | A posture recommendation being mistaken for a decision (mitigated: now moot — the ten rows are genuine Decisions per this acceptance, each still carrying its own named implementation-planning residual); MBQ-62 being forced into a weak mapping under batch-review time pressure (mitigated: explicitly declined, with a named split recommendation ChatGPT accepted, rather than forcing a sixth-value guess); this batch being mistaken for an implementation-gate-opening act (mitigated: DEC-018 §7 restates the gate stays closed regardless of this batch's outcome, and that ~35 other blocking MBQ rows remain untouched even after this acceptance) | RB-14 → **accepted** [`../04-decisions/DEC-018-mbq-decision-batch-1.md`](../04-decisions/DEC-018-mbq-decision-batch-1.md) (Accepted by ChatGPT, 2026-07-04); next → a dedicated follow-up DEC for MBQ-62, then the separate MBQ-64/MBQ-65 currency/webhook residual decision sprint — neither is implementation | **Accepted** |
| AR-016 | 2026-07-04 | MBQ-62 Odoo-side event job-source classification | **Accepted via [`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md)** — a dedicated follow-up decision record for the one row DEC-018 declined to force a same-batch answer for: whether Part A §D.2's fixed six-value job-source vocabulary should be extended with a seventh value for Odoo-side event triggers (an inventory push enqueued by a relevant Odoo stock change; a fulfillment creation triggered by a validated `stock.picking`), or classified another way. Evaluated four options (add a seventh value; existing source + trigger-origin metadata; a separate trigger-origin dimension with no seventh value; defer Odoo-side event triggers from Phase 1) against dashboard and retry-policy impact, and **accepted** extending the vocabulary with a seventh accepted semantic value, `odoo_event`, paired with a required (accepted, conceptual) trigger-origin sub-classification naming the specific Odoo event ("inventory stock-change trigger" / "fulfillment picking-validation trigger") — combining the useful parts of the first and third options while rejecting the second and fourth. **This resolves MBQ-62 at decision/semantic-classification level only — exact Odoo implementation mechanics (model/field names, Python constants, XML IDs, storage/Selection-field mechanics, trigger-origin field/model implementation, MBQ-16 retry constants) remain implementation planning; no implementation authorization or gate-opening act is performed.** | **Accepted by ChatGPT** (2026-07-04 — see acceptance note below) | Synthesizes already-accepted DEC-009/DEC-010/DEC-011/DEC-013 content plus DEC-018's own strict per-value analysis (§4, independently re-confirmed, not re-derived from scratch) and Part A §D.2/§D.5/§D.8/§D.10/§F.1/§G.1/§G.7 and Part C §A.7/§A.13/§B.3/§B.12; no new Tier-1 platform-fact claim introduced; no external Shopify/Odoo research performed, per this session's scope instruction — every claim rests on evidence already established and cited in Parts A/C and DEC-009/010/011/018 | Reviewed by ChatGPT — checked against `rejected-approaches-log.md` in full before drafting; no row addresses job-source vocabulary, so nothing is reintroduced; the four options were evaluated with the same strictness DEC-018 applied, explicitly declining a weak mapping onto an existing value in favor of either a genuine seventh value or an honest deferral (deferral itself found unavailable for fulfillment, per DEC-011); **ChatGPT then accepted DEC-019 on 2026-07-04** | A decision being mistaken for full implementation authorization (mitigated: DEC-019's Status/Acceptance sections and this row both state the acceptance is at decision/semantic-classification level only, implementation remains blocked, and the implementation gate remains closed); the accepted semantic value `odoo_event` being read as itself unresolved because its implementation mechanics are open (mitigated: DEC-019 §5/§6/Acceptance state plainly that `odoo_event` is the accepted seventh Part A §D.2 job-source value and the trigger-origin requirement is accepted conceptually — only implementation mechanics and exact field/model/constant placement (Odoo model names, field names, Python constants, XML IDs, storage/Selection-field mechanics, trigger-origin field/model implementation, MBQ-16 constants) remain implementation planning); this acceptance being mistaken for a gate-opening or implementation-authorizing act (mitigated: DEC-019 §7 restates the gate remains closed and no implementation task is created under any outcome) | RB-14 → **accepted** [`../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) (Accepted by ChatGPT, 2026-07-04); next → the separate MBQ-64/MBQ-65 currency/webhook residual decision sprint — not implementation | **Accepted** |
| AR-017 | 2026-07-04 | MBQ-64/MBQ-65 currency and product-webhook residual decisions | **Accepted via [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)**, **revised** after ChatGPT's first review returned REVISE for MBQ-64 — the dedicated currency/webhook residual decision sprint that DEC-017 anticipated and DEC-018 explicitly routed MBQ-64/MBQ-65 to. Proposes, for **MBQ-64** (revised posture): Phase 1 **automatic order import is same-currency only** — for orders where `Order.presentmentCurrencyCode == Order.currencyCode`, Odoo `sale.order.currency_id` follows the connector's normal configured pricelist/company currency, aligned to Shopify's shop currency; for orders where the two differ, the connector **never** silently creates a normal Odoo sale order in shop currency, regardless of whether a numeric total-check would otherwise reconcile — the job is blocked from automatic SO creation and routed to manual review / treated as an explicit unsupported-scope case **before** SO creation, independent of the total-check guard's outcome. Both `shopMoney`/`presentmentMoney` amounts and `presentmentCurrencyCode` are captured as audit/reconciliation evidence in every case. `financial total mismatch` is evaluated explicitly as a candidate classification for the blocked case, not forced onto it — the exact final error-class/sub-reason mapping remains implementation planning; MBQ-56's own tolerance mechanics remain open and are not relied upon as the mechanism that catches the currency-model divergence. Presentment-currency-denominated Odoo orders are explicitly non-MVP, consistent with DEC-007 §3's existing Markets/currency-specific-pricing exclusion. Proposes, for **MBQ-65** (unchanged by the revision): `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE` are implemented in Phase 1 as **enqueue-only triggers** — never a direct write — each job performing a follow-up authoritative read before any create/update/delete is applied, with DEC-005 reconciliation as the required backstop; a `PRODUCTS_DELETE` webhook never directly deletes/archives the bound Odoo product. Both proposals are grounded in fresh official-doc research this session: Shopify's "About Shopify Markets" page (presentment currency as checkout/refund "source of truth," shop currency as a back-converted analytics reference that "might not sum perfectly to totals"); the `Order` object's `presentmentCurrencyCode` field description, re-verified to include "This may differ from the shop's base currency when serving international customers or using multi-currency pricing"; the official `odoo/odoo` 19.0 `sale_order.py` source, newly confirming `currency_id` is compute-only (not directly settable, unlike `pricelist_id`) and that `amount_untaxed`/`amount_tax`/`amount_total` are computed via `AccountTax._get_tax_totals_summary` in exactly the order's one currency; and Shopify's "About webhooks" page (delivery not guaranteed, ordering not guaranteed, "your app shouldn't rely on receiving data from Shopify webhooks," reconciliation jobs recommended, `X-Shopify-Webhook-Id` dedup). **MBQ-64 Option B (presentment currency as Odoo order currency) and MBQ-65 Option D (direct webhook-driven product mutation) are both evaluated and not adopted**, for the same root reason DEC-018/DEC-019 already applied elsewhere in this register: prefer the option that does not silently risk a financial or data-safety defect, even where a more feature-rich option exists. **MBQ-64 and MBQ-65 are both resolved at decision/posture level by this acceptance; exact implementation mechanics for both (MBQ-56's tolerance, the exact error-class/sub-reason mapping for a blocked MBQ-64 order, and MBQ-65's exact controller/job/query/subscription mechanics) remain implementation planning; no other MBQ row is touched.** | **Accepted by ChatGPT** (2026-07-04 — see acceptance note below) | Synthesizes already-accepted DEC-007 §3, DEC-009 (`financial total mismatch` class), DEC-005/DEC-006 (layered sync, binding/dedup), and DEC-017's own fact-verification-level MBQ-64/MBQ-65 facts; five official Shopify pages and one official Odoo source file fetched and cited this session (2026-07-04) — see DEC-020 §2 for the full source table; one claimed Shopify fact (per-product variant-count webhook payload truncation) could **not** be confirmed against a primary `shopify.dev` page this session and is logged as inconclusive, not asserted | Checked against `rejected-approaches-log.md` in full — no existing rejected approach is reintroduced; MBQ-65 Option D and MBQ-64 Option B are both rejected in DEC-020 itself for the same root failure mode RA-008/RA-020 already reject in the inventory domain (writing/committing without a confirming read or guard), though neither option is itself logged as a new RA row by this record (`rejected-approaches-log.md` is outside this sprint's allowed-files scope) | A decision being mistaken for full implementation authorization (mitigated: DEC-020's Status/Acceptance sections and this row both state the acceptance is at decision/posture level only, implementation remains blocked, and the implementation gate remains closed); MBQ-64/MBQ-65 being read as fully resolved down to implementation detail (mitigated: DEC-020 §9's applied register wording and this row both name MBQ-56, the exact error-class mapping, and the exact webhook-controller mechanics as remaining implementation planning); the unconfirmed variant-truncation claim being silently asserted as fact (mitigated: DEC-020 §2 logs it as inconclusive and states it does not change either accepted posture); this acceptance being mistaken for a gate-opening or implementation-authorizing act (mitigated: DEC-020 §10 restates the gate remains closed and no implementation task is created under any outcome) | RB-14 → **accepted** [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md) (Accepted by ChatGPT, 2026-07-04); next → a gate-readiness audit against `master-blueprint.md`'s five gate-opening criteria before any implementation — not implementation itself | **Accepted** |
| AR-018 | 2026-07-05 | Implementation gate readiness audit after DEC-020 | **Accepted via [`implementation-gate-readiness-audit.md`](../05-qa/implementation-gate-readiness-audit.md)** — a strict, row-by-row audit of `master-blueprint.md`'s five gate-opening criteria against the current, post-DEC-020 state of the open-questions register (all 65 rows classified), performed after DEC-003 through DEC-020 and AR-002 through AR-017 were confirmed accepted. Extracts the five gate criteria verbatim and finds: **criterion 1** (blueprint parts accepted) passes only for a scope with zero operator-facing UI; **criterion 2** (implementation-blocking questions resolved/accepted) fails — eleven rows (MBQ-01/02/04/07/16/19/20/21/44/45/62) block even the narrowest possible first slice (`shopify_connector_core` substrate alone); **criterion 3** (explicit ChatGPT gate-opening act) fails — the act has not occurred; **criterion 4** (tasks written to the CLAUDE.md §9 template) is vacuously unmet — no implementation task exists; **criterion 5** (no open quality-gate escalation without a prevention rule) is ambiguous — `defect-pattern-log.md`'s "unsupported assumption/weak research" category sits at 3rd-occurrence `ESCALATED` status with a recorded evidence-consistency-gate prevention mechanism, but the row's own Status field has never been updated to `Mitigated`/`Closed`. Also flags, as an evidence-based documentation-currency finding (not corrected by this audit — out of its allowed-files scope), that `master-blueprint.md` and `master-blueprint-core-substrate.md` §D.2 are stale (read "Accepted through DEC-017"/"AR-002 through AR-014" and list only six job sources, not reflecting DEC-018/019/020 or the accepted seventh `odoo_event` value). Recommends the next session resolve the eleven core-blocking rows via a single naming/schema implementation-planning pass — **not code**. **No implementation authorized by this audit. No implementation task created. No MBQ row status changed. The implementation gate remains closed; implementation remains blocked.** **Verdict: READY ONLY FOR A VERY LIMITED IMPLEMENTATION-PLANNING SPRINT, NOT CODE.** **Audit verdict accepted by ChatGPT on 2026-07-05 — gate remains closed, implementation remains blocked, no implementation authorized, no implementation task created; next recommended session is a documentation-only naming/core-schema implementation-planning pass, not code and not a gate-opening act.** | **Accepted by ChatGPT** (2026-07-05 — see acceptance note below) | Synthesizes already-accepted DEC-003 through DEC-020, AR-002 through AR-017, Master Blueprint Parts A–E (read via their own acceptance records plus targeted section reads of `master-blueprint-core-substrate.md` §D.2/§I.3/§J.1 for this audit's core-substrate classification), `quality-feedback-loop.md` §8/§10/§11, and `defect-pattern-log.md`'s occurrence-counter table; no new Tier-1 Shopify/Odoo platform-fact claim introduced — this is an internal-readiness synthesis, not new external research | Checked against `rejected-approaches-log.md` — no new architecture proposed, so nothing to reintroduce; §8's risk list explicitly cites RA-008/011/012/014/017/020 as the concrete failure modes premature coding would risk repeating | An audit being mistaken for the gate-opening act itself (mitigated: Status section and this row both state "Proposed for ChatGPT review," "does not open the implementation gate," throughout); the criterion-5 ambiguity being silently resolved either way (mitigated: the audit states the ambiguity explicitly and recommends ChatGPT confirm the reading rather than assuming either answer); the documentation-currency finding being read as already fixed (mitigated: explicitly stated as not corrected by this audit, out of allowed-files scope) | RB-14 → **accepted** [`implementation-gate-readiness-audit.md`](../05-qa/implementation-gate-readiness-audit.md) (Accepted by ChatGPT, 2026-07-05); next → a documentation-only naming/core-schema implementation-planning pass for MBQ-01/02/04/07/16/19/20/21/44/45(residual)/62(residual) — not code, not a gate-opening act | **Accepted** |
| AR-019 | 2026-07-05 | Core naming and schema implementation-planning pass | **Accepted via [`../07-implementation-plan/core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md)** — revised 2026-07-05 after ChatGPT's REVISE review, then **accepted by ChatGPT on 2026-07-05, at implementation-planning level only** — the documentation-only naming/core-schema implementation-planning artifact the accepted implementation gate readiness audit (AR-018) named as the next session, prepared after PR #84 merged into `Shopify-connector` at merge commit `4bf692dceec4190705f522bc2d32851af4c79e37`. Proposes exact Odoo model names for a first core-only slice — **six models**: `shopify.connector.store`, `.store.settings`, `.location`, `.binding.mixin` (abstract), `.job`, `.job.log` — and their field schemas; a store-scoped `store.settings` model as the feature-flag/settings shape (with `store` carrying no reverse settings field — `store.settings.store_id` is the sole link); a **job+log split** with error/manual-review fields folded onto the job model (no separate error or idempotency-guard model), `job.log.job_id` using `ondelete='restrict'` (not `cascade`) to protect log history; a `job_type` Selection carrying two core-owned starting values (`core_readiness_check`, `core_manual_maintenance`) so the required field is never contradictorily empty before any domain module installs; the operation-level idempotency key schema (`idempotency_key`, persists for the job's life) and a **DB-backed, race-safe serialization guard** (`operation_scope_key`, populated only while non-terminal, cleared on reaching a terminal state, under a unique constraint on `(store_id, operation_scope_key)`), both owned by the job model and kept distinct from each other; retry-count ceilings and a backoff schedule by error-class family; four proposed group XML IDs (`group_shopify_connector_admin`/`_operator`/`_reviewer`/`_auditor`) plus planned (not created) `ir.model.access.csv` row shapes; and the `odoo_event` job-source/`trigger_origin` field mechanics (model: `shopify.connector.job`; field: `trigger_origin`; values `inventory_stock_change`/`fulfillment_picking_validation`; required only when `job_source = odoo_event`). For **MBQ-04**, explicitly adopts **Option A (full slice-1 descope, not a partial resolution)** — no official Odoo encryption-at-rest evidence was reviewed this session, so **no credential model of any kind is proposed** (removed entirely on revision); real credential persistence and any credential-lifecycle schema both remain fully open. **This document does not authorize implementation, does not open the implementation gate, and does not create any implementation task or code, module, view, controller, security file, manifest, test, or CI file.** MBQ register-impact wording (§14 of the document) is now **applied** to `master-blueprint-open-questions.md`, for exactly **MBQ-01, MBQ-02, MBQ-07, MBQ-16, MBQ-19, MBQ-20, MBQ-21, and the MBQ-45/MBQ-62 residuals — each now Resolved**; **MBQ-44 — Partially resolved** (planned CSV row shapes only, no CSV file created); **MBQ-04 — Not resolved, explicitly and fully descoped for slice 1**, not partially resolved. **No other MBQ row in `master-blueprint-open-questions.md` is touched by this acceptance.** | **Accepted by ChatGPT** (2026-07-05 — see acceptance note below) | Converts the already-accepted Part A core-substrate blueprint (DEC-013) — which deliberately left every model/field name a "proposed direction, not a committed identifier" — into the exact names/schema the accepted audit found blocking even a core-only first slice; no new architecture decision is introduced, only naming/schema detail inside boundaries DEC-003 through DEC-020 already fixed; the revision corrects five schema defects ChatGPT's REVISE identified (credential-model/MBQ-04 mislabeling, a One2many field named singular, a destructive cascade FK, a required Selection with no valid pre-domain-module value, and a race-prone query-time-only serialization guard) without introducing any new architecture | ChatGPT review/acceptance of this revised planning document; no external Shopify/Odoo research was performed or is required for this internal naming/schema synthesis | This acceptance being mistaken for full implementation authorization (mitigated: Status/Acceptance sections in the document and this row both state accepted at implementation-planning level only, gate remains closed, implementation remains blocked, no implementation task created); the job+log split and the generic `enqueue_decisions` JSON field being read as unreviewed rather than explicitly accepted (mitigated: §16 of the document records both as accepted — the latter "for now," subject to future implementation review); this acceptance being mistaken for a gate-opening act (mitigated: Status/Acceptance sections and §16 both state explicitly that no gate criterion is satisfied by this acceptance and that opening the gate is not recommended) | Applied the §14 register-impact wording to `master-blueprint-open-questions.md` for MBQ-01/02/04/07/16/19/20/21/44/45(residual)/62(residual) (MBQ-04 recorded as explicitly descoped, not resolved); recorded this acceptance in this log and in `research-handoff.md`; **not implementation** — a separate, explicit ChatGPT gate-opening act, and the domain-scope MBQ rows this pass does not touch (MBQ-03/05/09/14/23–43/46/48–61/63–65), remain for a later session | **Accepted** |
| AR-020 | 2026-07-05 | Final MBQ closure plan | **Proposed via [`../07-implementation-plan/final-mbq-closure-plan.md`](../07-implementation-plan/final-mbq-closure-plan.md)** — the planning-closure package prepared after AR-019's acceptance and PR #85's merge, reviewing **all 50 MBQ rows not yet fully closed** and proposing for each exactly one final status: **2 proposed resolved** (MBQ-29 single fallback partner per store; MBQ-35 no `on_hand` UI in Phase 1), **27 proposed partially resolved** with each residual named and reclassified as task-spec detail enforced by the `CLAUDE.md` §9 implementation-task template (MBQ-06/08/09/14/17/18/23/24/25/30/32/33/34/36/38/40/41/42/43/44/52/53/54/59/60/64/65), **17 explicitly descoped from MVP / the first gate** with named routes or containment (MBQ-03/04/05/10/13/15/22/27/46/48/49/51/55/56/57/61/63 — including webhook-driven inventory import out of Phase 1, no `FULFILLMENT_ORDERS_*` lifecycle subscription, automated product-media overwrite disabled, and the MBQ-27 tax mechanism decision gated before the order-import task), and **4 accepted-open risks with containment rules** (MBQ-12/28/50/58). Backed by fresh official-doc verification (2026-07-05, cited with URLs/quotes in the plan): Shopify's compliance-webhook mandate is documented as App-Store-distribution-scoped and protected-customer-data levels for custom apps are officially tabled (MBQ-09); `@idempotent` is required as of API 2026-04 with a 24-hour retention window and an undocumented uniqueness scope, closed by a scope-independent UUID-per-operation default (MBQ-14); `productSet` media omission behavior remains officially unconfirmed with a documented reference-vs-guide tension (MBQ-24); Odoo 19 documents **no** supported externally-computed-tax mechanism on `sale.order`, and Odoo's own Amazon connector documents recompute-plus-write-off (MBQ-27). **Zero rows remain in the plan's "still blocks implementation gate" class (§6).** **No code. No implementation task. The MBQ register's closure wording (plan §7) — originally held for a future acceptance patch — is now applied by the 2026-07-05 acceptance patch (see acceptance note below). The implementation gate remains closed; implementation remains blocked.** Plan §8/§11 recommend: ready for a **separate, limited, core-only, zero-UI** implementation-gate opening **after** ChatGPT accepts the package, plus two named pre-gate confirmations (criterion 5's DP-003/004/006 prevention-rule reading; the explicit gate act itself, criterion 3). | **Accepted by ChatGPT** (2026-07-05 — see acceptance note below) | Synthesizes the accepted AR-018 audit classification, AR-019's resolved core rows, DEC-003 through DEC-020, and Master Blueprint Parts A–E; adds four targeted official-doc verification passes (Shopify privacy-law-compliance / protected-customer-data / app-configuration / distribution pages; Shopify productSet / ProductSetInput / sync-data / idempotency pages; Odoo 19 taxes docs, Amazon-connector docs, and 19.0 source for sale_order/account_move/account_tax), every claim cited with URL, access date 2026-07-05, and access status; unverifiable points logged as open, never asserted | ChatGPT review of this closure package; checked against `rejected-approaches-log.md` in full — no rejected approach reintroduced; every proposed default is stricter than the accepted baseline | The package being mistaken for a gate-opening act (mitigated: Status section, §8, and this row all state the gate remains closed and the opening is a separate, later, explicit ChatGPT act); a proposed conservative default being mistaken for an accepted decision before ChatGPT review (mitigated: every §4 block is labelled proposed/[Recommendation]; the register is untouched until an acceptance patch); descoped rows being silently forgotten (mitigated: §7 wording routes every descope back into the register rows themselves upon acceptance); the embedded source excerpts substituting for `/docs/00-source-materials` captures (mitigated: logged explicitly as plan §10 risk 10, a named follow-up) | Accepted 2026-07-05; the acceptance patch applied plan §7 to `master-blueprint-open-questions.md` (50 rows + top note) and flipped this row to Accepted; next → criterion-5 confirmation and the separate, explicit, limited core gate-opening act — **neither performed by this acceptance; the gate remains closed** | **Accepted** |
| AR-021 | 2026-07-05 | Limited core implementation gate | Proposes, via [`../07-implementation-plan/limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md), the two separate ChatGPT acts the accepted Final MBQ Closure Plan (AR-020 §8/§11) and the accepted Implementation Gate Readiness Audit (AR-018 criteria 3/5) named as the only remaining preconditions: **(1)** confirms AR-018's criterion-5 ambiguity — the `defect-pattern-log.md` DP-003/004/006 "unsupported assumption / weak research" occurrence-counter row, still literally reading `ESCALATED`, is confirmed to satisfy the prevention-rule requirement **for this limited core gate only**, because its recorded evidence-consistency gate prevents implementation from proceeding when evidence conflicts remain unresolved; **(2)** opens a **limited, core-only, zero-UI** implementation gate scoped to `shopify_connector_core` only — module scaffold, manifest/init, the six AR-019-accepted core models, groups/access CSV for those models, AR-019-accepted constraints/indexes, and scaffold/core-model/security/constraint tests; explicitly excludes any credential/token/secret field, external API call, webhook, controller, setup wizard, test connection, product/customer/order/inventory/fulfillment domain logic, dashboard, sync center, or error-center UI; **(3)** authorizes exactly **one** implementation task, [`../07-implementation-plan/task-001-core-module-scaffold.md`](../07-implementation-plan/task-001-core-module-scaffold.md) (Core Module Scaffold), written to the `CLAUDE.md` §9 template. **No implementation PR may start until this act is accepted; no second task may start until Task 001's own coding PR is reviewed.** | **Accepted by ChatGPT** (2026-07-05 — see acceptance note below) | Executes the separate, explicit gate-opening act (criterion 3) and criterion-5 confirmation that AR-020's acceptance patch and AR-018's own criterion table named the only remaining preconditions for a core-only first slice; introduces no new architecture and decides no new MBQ row | n/a — governance/gate-opening act, not a new Shopify/Odoo platform-fact claim; the criterion-5 confirmation rests on the already-recorded DP-003/004/006 evidence-consistency gate (`defect-pattern-log.md`) and the already-accepted AR-019 (core naming/schema) and AR-020 (MBQ closure) | The criterion-5 confirmation being read as a project-wide waiver rather than limited to this gate (mitigated: gate document §2/Acceptance state the scope explicitly — does not waive evidence requirements for credential/API/UI/domain/release-readiness tasks, and every later gate requires its own separate ChatGPT act); the gate being read as authorizing more than Task 001 (mitigated: gate document §6 and §5 state exactly one task is authorized and no second task may start before ChatGPT reviews the first); this acceptance being mistaken for the gate being genuinely open before merge (mitigated: gate document Status/Acceptance sections state the gate opens only once this PR is merged into `Shopify-connector`, and no code is created by this PR) | **Accepted 2026-07-05; the limited core-only zero-UI gate opens and Task 001 is authorized once this PR merges** → Task 001's own coding PR (the core module scaffold implementation) becomes the next session, not performed by this entry | **Accepted** |
| AR-023 | 2026-07-06 | UI/UX final design specification | Accept PR #91's UI/UX design package — [`ui-ux-final-design-spec.md`](../02-product/ui-ux-final-design-spec.md), [`screen-inventory-and-navigation-map.md`](../02-product/screen-inventory-and-navigation-map.md), [`mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md), [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md), and [`ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md) — as design-specification guidance: the Premium Simplicity Standard as the project's UI/UX quality bar, the screen inventory/navigation map as the design-level screen map, the MVP user flows/state models as the design-level flow map, the review checklist as the checklist for future UI implementation review, and the task map as planning guidance only. **No implementation gate opened; no code authorized by this acceptance.** | **Accepted by ChatGPT** (2026-07-06 — see acceptance note below) | Converts the accepted DEC-012 through DEC-020 UX/architecture decisions and the accepted PR #90 MBQ-04 credential posture (AR-022) into implementation-ready UI/UX design detail without authorizing code; every new design-level statement is labelled **[Design proposal — this spec]** / **[Illustrative copy — MBQ-22 open]** / **[Open item]**, never asserted as decided | None remaining for design-specification-level acceptance; future implementation tasks must still satisfy every still-open MBQ item (MBQ-03 XML IDs, MBQ-22 final copy, MBQ-44 residual access rows, the MBQ-04 credential implementation-planning task, and the rest of the design spec's open-items register) as their own task-spec detail | Proposal-level design disciplines (7±2 field budget, one-primary-action, 10-second dashboard rule) being misread as hard code-level gates; the UI implementation task map being misread as task authorization; a future UI implementation adding clutter, generic-connector feel, or complexity the Premium Simplicity Standard rejects | A future, separate, explicit ChatGPT UI-implementation-gate-opening act, each area's own `CLAUDE.md` §9 task spec — neither performed by this acceptance | **Accepted** |
| AR-022 | 2026-07-05 | MBQ-04 credential persistence research and decision proposal | **Accepted via** [`../01-research/odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md) and [`../03-architecture/mbq-04-credential-persistence-decision-proposal.md`](../03-architecture/mbq-04-credential-persistence-decision-proposal.md) — the official-evidence answer AR-019/AR-020 identified as missing before MBQ-04 could move past a full descope, **revised once (2026-07-05) per ChatGPT's first REVISE review** to narrow two absolute claims to their evidence-scoped form, then **accepted by ChatGPT (2026-07-06)**: adversarially-verified research against official Odoo 19.0 Community/core docs and source establishes that **no official Odoo 19 Community/core field-level or ORM encryption-at-rest mechanism was found in the official docs/source reviewed**; `password=True`/the view-arch `password` attribute is UI-display masking only (not an ORM read-restriction, not encryption); `ir.config_parameter` is plain, unencrypted key-value storage under a single `group_system`-only ACL, with no official documentation calling it secure secret storage; field-level `groups`/`ir.model.access`/`ir.rule` are access control only and are explicitly bypassed by `sudo()`/superuser mode even at the field-`groups` level; five real official Odoo credential-field examples (`ir.mail_server.smtp_pass`, Stripe/Adyen/Authorize.Net payment-provider keys, `iap.account.account_token`) all use the identical plain-`Char` + `groups='base.group_system'` pattern with no encryption; and the only encryption-at-rest claim found anywhere (`odoo.com/security`, AES-256) is infrastructure/platform-level, scoped by Odoo's own corporate page to "Odoo Cloud (the platform)" — its exact Odoo Online/Odoo.sh/on-premise applicability is a **hosting-scope question, not separately confirmed**, and it is not a field-level ORM mechanism. Enterprise-only modules, third-party modules, custom application-side encryption, and external secret managers remain outside this evidence base unless separately researched. The decision proposal evaluates five options (A full descope, B standard Odoo field/`groups`, C `ir.config_parameter`, D external secret manager, E hybrid metadata-in-Odoo/secret-outside), and **ChatGPT accepts Option B at posture level only** — a dedicated Odoo-managed credential field (or tightly coupled field set), plain storage using standard Odoo field/access controls, restricted with a connector admin-equivalent `groups=`, view-level password masking wherever exposed, and a mandatory no-logging/redaction rule; consistent with DEC-004's already-accepted "masked storage/field-level `groups`/least-privilege" posture, no DEC-004 amendment needed. Options D/E are **not rejected forever** — deferred as a possible future stronger-posture research/design path, routed as their own follow-up architecture-review row if pursued. **No code or implementation is authorized by this acceptance — no credential model, field, API client, setup wizard, test-connection mechanism, webhook, controller, cron, UI, or domain module is created.** Exact model name, field name/type, access group XML ID, audit metadata, rotation/revocation behavior, test-connection behavior, redaction implementation, and rollback behavior all remain open, future implementation-planning items, each requiring its own separate task written to the `CLAUDE.md` §9 template before any code starts. This acceptance's register-impact wording has been applied to `master-blueprint-open-questions.md` (MBQ-04 only, now **Partially resolved** — evidence blocker resolved for the official Community/core Odoo 19 sources reviewed; Option B accepted at posture level; implementation detail open). | **Accepted by ChatGPT** (2026-07-06 — see acceptance note below) | Synthesizes already-accepted DEC-004 (auth/token-model posture) and the AR-019/AR-020 record of MBQ-04's exact evidence gap; five parallel official-source research passes plus an independent adversarial verification pass on every risk-flagged claim (encryption/security/password-related), all performed and cited 2026-07-05, then narrowed once per ChatGPT's REVISE review before this acceptance — see the research notes' "Sources searched" section for the full list; no fact asserted without a direct official-doc or official-source-code citation, and every unconfirmed point is logged as an open question rather than inferred | Checked against `rejected-approaches-log.md` — no existing rejected approach is reintroduced; the accepted documents explicitly decline to assert `password=True` or `ir.config_parameter` provide encryption/security beyond access control, per this task's hard rules, and do not claim Option B constitutes "encryption at rest" or confirmed Odoo.sh/Odoo Cloud coverage anywhere in their wording | A masking/access-control mechanism being mistaken for encryption (mitigated: both documents state repeatedly and explicitly that UI masking and `groups=` access control are not encryption, and that `sudo()`/superuser bypasses field-level `groups`); this acceptance being mistaken for an implementation-authorizing or gate-opening act (mitigated: Status/Acceptance sections in the decision proposal and this row both state "Accepted... at posture level only," "Not implemented," and name every implementation-planning item still required); MBQ-04 being marked fully resolved prematurely (mitigated: this row, the register, and the proposal's own classification section all state "Partially resolved," not "Resolved"); Option B's posture-level acceptance being read as also deciding implementation detail (mitigated: the Acceptance section explicitly lists model/field/access/audit/rotation/test-connection/redaction/rollback as separate, still-open, future implementation-planning items) | **Accepted 2026-07-06.** Register-impact wording applied to `master-blueprint-open-questions.md` (MBQ-04 only). Next → a separate future implementation-planning task naming the exact credential model/field/access-group/redaction/rotation/test-connection/rollback details, written to the `CLAUDE.md` §9 template — not performed by this entry, and not implementation. | **Accepted** |
| AR-024 | 2026-07-06 | Credential, connection, and API-client foundation planning | **Accepted via** [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md), [`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md), [`../07-implementation-plan/task-002-credential-storage-redaction-proposed.md`](../07-implementation-plan/task-002-credential-storage-redaction-proposed.md), [`../07-implementation-plan/task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md), and [`./credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md) — the proposed implementation-planning package for credential storage (recommended: a dedicated Admin-only `shopify.connector.store.credential` model within the accepted MBQ-04 Option B posture, with non-secret status mirrors on `shopify.connector.store`), the redaction/no-logging contract (`SENSITIVE_KEYS` + `shpat_`/`shprt_` value patterns, belt-and-braces enforcement), connection lifecycle semantics for the four accepted store states, the read-only test-connection contract (`shop` + `currentAppInstallation.accessScopes` GraphQL query, officially cited), the readiness-check mechanics for the accepted DEC-018 MBQ-06 essential set, the API-client boundary (single `core`-owned GraphQL transport, dual-path error normalization into the fixed 16 classes, throttle-signal surfacing without pacing policy), and the proposed Task 002 (credential storage/redaction) and Task 003 (API client shell/test connection) specs — both **proposed only, not authorized**. Docs-only; no code, no fields, no models, no views, no gate opened; Task 002 not started. Backed by fresh official-source verification (2026-07-06, cited with URLs/quotes/access status in the planning document): Shopify auth header/endpoint/versioning/scopes-query/shop-query/error-code/cost facts confirmed; Shopify's deprecation of new admin-created custom apps and the Dev Dashboard client-credentials 24-hour-token model recorded as a material MBQ-05 development; Odoo 19 field-`groups` enforcement and `sudo()` bypass re-confirmed at source level; every unconfirmed platform behavior (THROTTLED body shape, invalid-token HTTP status, missing-scope shape, `shop`/`currentAppInstallation` scope requirements) logged as an open question, never asserted. | **Accepted by ChatGPT** (2026-07-06 — see acceptance note below) | Closes the detailed planning gap left by AR-022 / MBQ-04 posture-level acceptance before coding starts — AR-022 and the accepted UI/UX task map (AR-023, Group 4) both name exactly this planning task as the required precursor to any credential code | ChatGPT review; official Shopify/Odoo citations checked (access date 2026-07-06 for the new pass; prior repo research reused with its original dates); the exact model/field/access/redaction/test plan reviewed, including the named decision points (compute-blank no-read-back variant; `token_variant` vocabulary vs the MBQ-05 development; scope-snapshot placement; `core_test_connection` job-type value; `SHOP_INACTIVE`/402/423 class mapping) | Credential leakage (contained: Admin-only model, two access layers, mandatory redaction contract + tests, honest residual-exposure statements); premature implementation (contained: both task specs are Proposed-not-authorized, each requiring its own explicit ChatGPT gate act and final §9 prompt — Task 003 additionally requires the first conscious widening of the no-external-API-call rule); unsupported API assumptions (contained: undocumented Shopify behaviors carried as labelled-unofficial fixtures + empirical verification steps, never asserted); UI gate confusion (contained: zero views/UI in every foundation task; the UI implementation gate remains a separate, explicit ChatGPT act per AR-023) | **Accepted 2026-07-06.** Register-impact wording applied to `master-blueprint-open-questions.md` (MBQ-04 upgraded to implementation-planning level, still Partially resolved; MBQ-05/06/44/51/52/08 planning notes added, no status change on those six); recorded in this log and in `research-handoff.md`. Task 002/003 remain proposed only, not authorized; no implementation gate opened. Next → a separate, explicit ChatGPT gate-opening act and final `CLAUDE.md` §9 task prompt for Task 002 — not performed by this acceptance | **Accepted** |
| AR-025 | 2026-07-06 | Task 002 decision closure and gate-preparation pack | Close the three Task 002-specific decision points AR-024 left open and produce the gate-ready package, via [`../07-implementation-plan/task-002-decision-closure.md`](../07-implementation-plan/task-002-decision-closure.md) (compute-blank no-read-back hardening: **reject for Task 002** — stored Char behind the two accepted access layers, honest residual stated, `res.users`-style full variant recorded with a revisit condition; `token_variant`/MBQ-05: **Option 2C** — Task 002 stores exactly one secret value with the single Selection value `offline_custom_app`, the dedicated credential model is the seam, Dev Dashboard client-credentials mechanics explicitly deferred pending ChatGPT's MBQ-05 direction; scope snapshot: **on `shopify.connector.store`** — `granted_scopes` + `granted_scopes_checked_at` created in Task 002 as readonly mirrors with no writer until Task 003), plus the complete copy-paste final `CLAUDE.md` §9 implementation prompt ([`../07-implementation-plan/task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md), marked not issued/not authorized), a proposal to open a narrow credential-storage-only gate ([`../07-implementation-plan/task-002-gate-opening-proposal.md`](../07-implementation-plan/task-002-gate-opening-proposal.md) — external API calls, setup wizard, UI, test connection, webhooks, controllers, cron, and domain logic all stay forbidden; the proposal itself opens nothing), and the review gate ([`./task-002-pre-implementation-review-checklist.md`](./task-002-pre-implementation-review-checklist.md)). Official Shopify/Odoo facts re-verified 2026-07-06 (incl. the now-dated January 1, 2026 legacy custom-app creation cutoff and the 19.0 `res.users.password` compute-blank source mechanics) | **Accepted by ChatGPT (2026-07-07 — see acceptance note below), at decision/gate-preparation level only:** the three Task 002 decisions accepted (compute-blank rejected for Task 002; `token_variant` = `offline_custom_app` only; scope snapshot on `store`); the final Task 002 prompt accepted as gate-ready and binding **but not issued**; the gate proposal accepted as the proposed scope **but the gate is not opened**; Task 002/003 not started; no implementation or code authorized | AR-024 accepted the credential foundation plan but left three Task 002-specific decisions open before coding | ChatGPT review of the compute-blank decision, the token_variant/MBQ-05 direction, the scope-snapshot placement, and the final implementation prompt — performed 2026-07-07 | Accidentally opening the gate; overbuilding Dev Dashboard credential mechanics; false no-read-back claims; weak tests; Task 003 scope leakage | Acceptance patch applied (2026-07-07). Next → the separate, explicit Task 002 gate-opening act per [`../07-implementation-plan/task-002-gate-opening-proposal.md`](../07-implementation-plan/task-002-gate-opening-proposal.md) — **not performed by this acceptance** | **Accepted** |
| AR-026 | 2026-07-07 | Task 002 credential-storage implementation gate | Open a narrow Task 002 implementation gate for credential storage, masking, and redaction only, using the accepted AR-025 final prompt, via [`../07-implementation-plan/task-002-credential-storage-gate.md`](../07-implementation-plan/task-002-credential-storage-gate.md) — authorizes exactly one future coding session (Task 002) after this document merges; the gate references [`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md) by exact path rather than restating its contracts; API client, test connection, setup wizard, UI/views/menus/actions/wizards, webhooks/controllers/cron, domain modules, external network calls, and Task 003 all remain forbidden; the gate closes again once the future Task 002 implementation PR is opened as draft | **Accepted by ChatGPT — gate opens only once this PR merges** | PR #94 / AR-025 accepted the Task 002 decisions and final prompt; the project now needs the separate explicit gate-opening act before code can start | PR #94 merge commit `03ffcb4dc949cd5137b589a6cdc33da9105de31d`; the accepted AR-025 documents (`task-002-decision-closure.md`, `task-002-final-implementation-prompt.md`, `task-002-gate-opening-proposal.md`, `task-002-pre-implementation-review-checklist.md`); the final Task 002 prompt itself | Credential leakage; false security claims; accidental API call; UI/scope leakage; Task 003 leakage; unexecuted runtime tests (no Odoo runtime in this repository) | After merge, issue the final Task 002 implementation prompt verbatim as a separate coding session; the resulting PR must remain draft until ChatGPT reviews it | **Accepted** |
| AR-027 | 2026-07-07 | Task 003 decision closure | Close the four Task 003-specific decision points AR-024 left open, via [`../07-implementation-plan/task-003-decision-closure.md`](../07-implementation-plan/task-003-decision-closure.md) (job-type value: `core_test_connection`, added directly to the base selection, amending AR-019's fixed-at-two-values statement to three; `SHOP_INACTIVE`/402/423/403-fraudulent error-class mapping: `shopify_permission_scope_auth` for all four — the underlying HTTP-status/error-code facts are already cited in `credential-connection-api-client-planning.md`, but the mapping choice and several named behavioral shapes remain flagged `[Requires external validation before implementation]` — with `credential_state` flipped to `invalid` only for a genuine token-invalid signal, not a shop-account-state condition, and a distinct, mandatory plain-language reason per condition; job-log write path: a single sanctioned internal `sudo()`-wrapped system-append method, no ACL widening, no security-file change; per-run `payload_hash` nonce: a UUID4 for **`core_test_connection` job creation only** — the identical latent idempotency-collision defect in the already-merged `core_readiness_check` job type is explicitly **excluded** from Task 003's scope and tracked separately), plus a companion review checklist ([`./task-003-pre-implementation-review-checklist.md`](./task-003-pre-implementation-review-checklist.md)) and a dated amendment note on [`../07-implementation-plan/task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md). **No final Task 003 implementation prompt and no gate-opening proposal are included** — unlike the AR-025 round, this package is decisions-only, deferring the final prompt/gate pairing to a later, separate session. Session constraint: no external network access; every platform statement reuses an already-cited repo document or is explicitly labelled as requiring future external validation — no new official-source research was performed or claimed. | **Accepted by ChatGPT — with an F1 revision to Decision 4** (2026-07-07 — see acceptance note below) | AR-024 accepted the credential/API-client foundation plan but left these four Task-003-specific decision points open; AR-025 closed only the three Task-002-specific points and explicitly deferred these four | Direct inspection of `shopify_connector_job.py`/`shopify_connector_job_log.py`/`ir.model.access.csv` (confirmed current schema/ACL state, no Task 003 code exists yet); reused citations from `credential-connection-api-client-planning.md` (accessed 2026-07-06) and `DEC-009`; `rejected-approaches-log.md` (RA-001–RA-023) checked — no conflict; `shopify_user_errors_validation` now logged as rejected (RA-024) | A mapping that later official verification contradicts (mitigated: the mapping choice and named behavioral shapes are labelled `[Requires external validation before implementation]`, not asserted as fact); the `core_readiness_check` collision defect being silently folded into Task 003 or lost (mitigated: F1 revision explicitly excludes it from Task 003's scope and logs it as `TD-001`, cross-referenced from the decision-closure document, the QA checklist, this row, and the handoff); a future session mistaking this acceptance for gate authorization (mitigated: Status sections in all three documents state no gate is opened and no final prompt exists) | A separate future session prepares the final Task 003 `CLAUDE.md` §9 prompt and a narrow gate-opening proposal (mirroring AR-025 → AR-026), stating explicitly whether `core_readiness_check` (`TD-001`) is folded in by name or left for its own follow-up patch — **not performed by this entry** | **Accepted** |
| AR-028 | 2026-07-07 | Task 003 final implementation prompt and gate-opening proposal | Prepare the final Task 003 `CLAUDE.md` §9 implementation prompt applying the four AR-027-accepted decisions, via [`../07-implementation-plan/task-003-final-implementation-prompt.md`](../07-implementation-plan/task-003-final-implementation-prompt.md) (marked not issued/not authorized), and a narrow gate-opening proposal for the **first** authorization of outbound, read-only Shopify Admin API calls, via [`../07-implementation-plan/task-003-gate-opening-proposal.md`](../07-implementation-plan/task-003-gate-opening-proposal.md) — the proposal itself opens nothing. Mirrors the AR-025 → AR-026 pattern, but scoped to gate-preparation only, since AR-027 already closed the four Task 003 decision points in a prior, separate PR (#98). No new decision is made and none of AR-027's four decisions is re-litigated; `core_readiness_check` (`TD-001`) is explicitly excluded from the proposed gate scope, named only as a possible future explicitly-authorized inclusion; API client, test connection, setup wizard, UI/XML, webhooks/controllers/cron, and domain logic all stay forbidden by this proposal. Docs-only; no code, no external network call | **Accepted by ChatGPT** (2026-07-07 — applied by the AR-029 gate-opening act itself, see the AR-029 row and acceptance note below) | AR-027 closed the four Task 003-specific decision points but explicitly deferred the final-prompt/gate-proposal pairing to a later, separate session (per AR-027's own "Recommended next session" and "Final Task 003 implementation-boundary note") | n/a — a packaging/gate-preparation act, not new research; every technical contract restated in the final prompt reuses the already-authoritative [`task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md) and the AR-027-accepted decisions; no new external research performed or claimed this session (no network access) | This proposal being mistaken for authorization (mitigated: both documents' Status sections state the gate is not opened and the prompt is not issued); `core_readiness_check` being silently folded into the gate scope (mitigated: explicitly excluded, named only as a future by-name option); `sudo()` proliferation beyond the two sanctioned sites named in the final prompt; premature mutation/UI/domain-logic scope creep; false official-behavior claims for Shopify error shapes not yet empirically observed (mitigated: `[Requires external validation before implementation]` labelling carried through from AR-027) | **Superseded by AR-029:** the separate, explicit Task 003 gate-opening act is performed in [`task-003-api-client-test-connection-gate.md`](../07-implementation-plan/task-003-api-client-test-connection-gate.md) — the final prompt is issued only after that document merges into `Shopify-connector` | **Accepted** |
| AR-029 | 2026-07-07 | Task 003 API-client / test-connection implementation gate | Open a narrow Task 003 implementation gate for the read-only API client and test-connection service only, using the accepted AR-028 final prompt, via [`../07-implementation-plan/task-003-api-client-test-connection-gate.md`](../07-implementation-plan/task-003-api-client-test-connection-gate.md) — authorizes exactly one future coding session (Task 003) after this document merges; the gate references [`task-003-final-implementation-prompt.md`](../07-implementation-plan/task-003-final-implementation-prompt.md) by exact path rather than restating its contracts; applies the AR-028 acceptance patch in the same document (AR-028 row → Accepted); this is the **first** conscious widening of the AR-021 no-external-API-call rule — read-only outbound GraphQL calls only, no mutation, no Bulk Operations, no REST; `core_readiness_check`/`TD-001`, setup wizard, UI/views/menus/actions/wizards, webhooks/controllers/cron, domain modules, credential-model changes, and ACL/security-file changes all remain forbidden; the gate closes again once the future Task 003 implementation PR is opened as draft | **Accepted by ChatGPT — gate opens only once this PR merges** | PR #98 / AR-027 accepted the four Task 003 decisions; PR #99 / AR-028 packaged the final prompt and gate-opening proposal (merged before its own acceptance patch, per this document's §AR-028 acceptance); the project now needs the separate explicit gate-opening act before code can start | PR #98 merge commit `2e51cf02cd54527ff9dc817b6be1e1189f001a83`; PR #99 merge commit `756b88eca79f2ef56ff752b6ba82ab266a782724`; the accepted AR-027/AR-028 documents (`task-003-decision-closure.md`, `task-003-final-implementation-prompt.md`, `task-003-gate-opening-proposal.md`, `task-003-pre-implementation-review-checklist.md`); the final Task 003 prompt itself | Accidental mutation capability; `sudo()` proliferation beyond the two sanctioned sites; `core_readiness_check`/`TD-001` silently folded in; false official-behavior claims for unconfirmed Shopify error shapes; credential/token leakage via new transport code; unexecuted runtime tests (no Odoo runtime in this repository) | After merge, issue the final Task 003 implementation prompt verbatim as a separate coding session; the resulting PR must remain draft until ChatGPT reviews it | **Accepted** |
| AR-030 | 2026-07-08 | Task 006B sync engine architecture gate | Proposed domain-neutral sync-engine architecture gate / [`DEC-025`](../04-decisions/DEC-025-task-006-sync-engine-gate.md), synthesizing the accepted Task 006A research package (PR #123–#127) into architecture principles, a proposed core-engine shape, a job-trigger model, a retry/failure policy, an idempotency/duplicate-prevention layering, the Odoo execution substrate, Shopify API implications, and a core-vs-domain responsibility table — built directly on already-accepted [`DEC-005`](../04-decisions/DEC-005-sync-orchestration-strategy.md), [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md), [`DEC-013`](../04-decisions/DEC-013-master-blueprint-core-substrate.md), and [`DEC-024`](../04-decisions/DEC-024-task-005-closure.md); full detail in [`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md) | **Accepted by ChatGPT (2026-07-08)** | Consolidates already-accepted Task 006A evidence into a single accepted architecture gate so a future implementation-scope session has a synthesized shape to draft against; **no implementation authorization of any kind is granted or implied by this acceptance** | ChatGPT review of PR #128 against [`../05-qa/task-006b-architecture-gate-review-checklist.md`](../05-qa/task-006b-architecture-gate-review-checklist.md) — completed; confirmed that every Task 006A open item (VAL-B2, MBQ-05, TD-002, fulfillment API model, product first-sync dedup thresholds, Lite/Full packaging) remains preserved, not silently resolved; confirmed that the named concurrency claims (job-acquisition locking, disconnect race, multi-server coordination) remain flagged as requiring live Odoo.sh/multi-server runtime proof before any implementation relies on them | Premature implementation starting before a separate implementation gate is opened; the unresolved job-claiming-concurrency and multi-server-coordination questions being silently assumed safe; token-acquisition (MBQ-05), fulfillment-API-model, product-dedup-threshold, and Lite/Full-packaging assumptions being treated as settled when none is decided by this acceptance | Future Task 006C implementation-scope drafting may be proposed in a separate session, but no implementation is authorized by AR-030/DEC-025 itself | **Accepted** |
| AR-031 | 2026-07-09 | Task 006C sync-engine skeleton implementation gate | Proposes opening a narrow Task 006C implementation gate for the core job-enqueue/claim/dispatch/retry skeleton only, via a revised [`task-006c-sync-engine-gate-opening-proposal.md`](../07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md) and a new [`task-006c-sync-engine-skeleton-gate.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-gate.md), proposing, and via this row's acceptance now ChatGPT-adopting, concrete decisions for the six open implementation choices the accepted Task 006C implementation-scope package (PR #129, accepted as a planning/scope package only) left as candidates requiring ChatGPT approval: (A) execution-time claim/concurrency mechanism — `try_lock_for_update()` per candidate job row, skip locked/unavailable rows, never raw SQL `SKIP LOCKED`, never a PostgreSQL advisory lock; (B) handler-registry seam shape — a new `_get_handlers()` registry seam on a `shopify.connector.job.dispatch` `AbstractModel`, adapting (not copying) the `_get_checks()` precedent, with safe missing-handler failure; (C) retry-default constants — 12 attempts / 30s base delay / ×2 multiplier / 30-minute cap / ±20% jitter / 24-hour window, named and tunable; (D) enqueue/dispatch file split — `shopify_connector_job_enqueue.py` + `shopify_connector_job_dispatch.py`, both `AbstractModel`s, no services package, no concrete model, no ACL file; (E) cron batch size/interval — batch size 20, interval 5 minutes, conservative defaults pending runtime validation; (F) core diagnostic `job_type` — `core_dispatch_selftest`, core/diagnostic-only, never calling Shopify, never a domain-sync template. The companion final prompt ([`task-006c-sync-engine-skeleton-final-prompt.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md)) is now **Accepted final prompt / Not issued**, incorporating all six accepted values, leaving only the merge-commit-SHA placeholder unresolved (deliberately — PR #130 has not merged) | **Accepted by ChatGPT (2026-07-09)** — via control-room review, GitHub review artifact/comment ID `4658949628`, PR #130; acceptance of the six choices and of the gate-opening proposal/gate document does not by itself open the gate or authorize code — PR #130 must still merge, and the final prompt must still be separately issued | This session (Task 006D) prepared the concrete gate-opening decision package the accepted implementation-scope document's §F and the prior gate-opening proposal's own §6 both left for a future, separate ChatGPT act — mirroring the AR-025→AR-026 (Task 002) and AR-027/AR-028→AR-029 (Task 003) two-step decision-closure-then-gate-opening-act pattern this log already establishes; ChatGPT's acceptance completes the decision-closure step, mirroring AR-025/AR-027 | ChatGPT review of this package against [`../05-qa/task-006d-gate-opening-review-checklist.md`](./task-006d-gate-opening-review-checklist.md) — completed; every accepted value confirmed consistent across the gate-opening proposal, the final prompt, the new gate document, and that checklist | Premature coding before PR #130 actually merges; the `try_lock_for_update()` mechanism (Decision A) or the execution-time-immediately-before-dispatch re-check (SRR-03 narrowing) being overclaimed as proven safe under real concurrent workers or a multi-server deployment before live Odoo.sh proof; domain-sync/UI-setup-wizard/webhook-controller/OAuth-token-acquisition/live-Shopify-call scope creep during any future implementation this gate would authorize | After this PR merges, ChatGPT may issue the finalized Task 006C implementation prompt in a new Claude Code session with the merge commit SHA filled in; the resulting implementation PR must remain **draft** until ChatGPT reviews it — not performed by this entry | **Accepted** |
| AR-032 | 2026-07-09 | Task 006C sync-engine skeleton implementation closure | PR #131 ("Task 006C: sync-engine core skeleton (enqueue, dispatch, retry)") merged into `Shopify-connector`, merge commit `152b1553fe10c6efcbad75b4eba9cfcd2f101385` (head before merge `e68a5319bb7a7602bb8cc72568ef0c022551f542`); implements the core job-enqueue/claim/dispatch/retry skeleton authorized by AR-031/the issued Task 006C final prompt — full detail in [`task-006c-sync-engine-skeleton-validation-results.md`](./task-006c-sync-engine-skeleton-validation-results.md) | **Accepted / merged** | Accepted with user-provided green Odoo.sh build confirmation; a real Odoo.sh runtime validation surfaced two genuine defects (a test-only fake-handler-signature bug, fixed directly; a real pre-existing `action_disconnect()`/`manual_review_subreason` production bug, fixed only after an explicit, scoped, control-room-approved one-file exception to `shopify_connector_store.py` — review artifact `4923059289`) — both fixed before merge, full failure/fix timeline documented in the validation-results doc | Runtime failure/fix timeline documented (see validation-results doc §C); GitHub combined status/check-runs for the merged head remain `pending`/empty via this repo's API — merge rests on user-provided confirmation, not independently observed build evidence | Multi-server/concurrent-worker runtime concurrency proof for `try_lock_for_update()` remains open, not proven by this merge; VAL-B2, MBQ-05, TD-002, the fulfillment API model, product first-sync dedup thresholds, token acquisition, Lite/Full packaging, and checkpoint/resume ownership all remain open and unchanged; no domain sync of any kind is authorized or implemented by this PR | This closure record does not authorize further implementation; next controlled task requires a separate ChatGPT implementation prompt — see [`research-handoff.md`](../01-research/research-handoff.md) | **Accepted** |
| AR-033 | 2026-07-09 | Task 010 product-import implementation readiness — master checkpoint and gate-proposal assessment | After PR #131–#134 all merged into `Shopify-connector` (latest merge commit `51628f77a7da1e47cfdb30d17559b496c4c45a1d`), consolidates the full post-Task-006C evidence base into [`../07-implementation-plan/master-implementation-readiness-checkpoint.md`](../07-implementation-plan/master-implementation-readiness-checkpoint.md): a full blocker classification table (A/B/C/D) covering VAL-B2, MBQ-05, MBQ-55, TD-002, the fulfillment API model, product first-sync dedup thresholds, token acquisition, Lite/Full packaging, checkpoint/resume ownership, the multi-server concurrency proof requirement, and every proposed domain task (010–014); concludes **Option 2 — not ready** to open a Task 010 gate, because two explicit preconditions named in [`task-010-product-import-proposed.md`](../07-implementation-plan/task-010-product-import-proposed.md) itself remain unmet (the "product domain gate" named in `ui-ux-implementation-task-map.md` Group 10 has never been opened and its own trigger conditions are undefined anywhere in the repo; MBQ-55, the product-template/variant binding model/field naming pass, remains open). Per this conclusion, **no Task 010 final implementation prompt and no Task 010 gate-opening proposal are drafted this session** — the checkpoint document itself functions as the required blocker-resolution proposal | **Accepted by ChatGPT** — via control-room review, GitHub comment ID `4924290291`, on PR #135's merge; accepts the checkpoint's Option 2 ("not ready") conclusion and its recommended blocker-resolution track (a documentation-only MBQ-55 naming/schema pass for the product-template/variant binding models); does not itself authorize Task 010, open the Task 010 gate, open the product-domain gate, or authorize any implementation | This is a readiness assessment, not a new research finding; every blocker cited is restated exactly as its own already-recorded source states it, none newly discovered or newly resolved by this entry | ChatGPT review of the checkpoint's blocker classification table and its recommended blocker-resolution track (a documentation-only MBQ-55 domain-naming/schema planning pass for the product-template/variant binding models, with MBQ-05 branch B auth-distribution planning as a non-competing parallel candidate) | This entry, and the checkpoint it records, must not be read as authorizing Task 010, any other domain-sync task, a setup wizard, OAuth/token-acquisition code, or any Lite/Full packaging implementation; no implementation gate is opened, extended, or reinterpreted by this entry | Recommended next: ChatGPT decides whether to authorize the MBQ-55 naming pass, MBQ-05 branch B planning, both, or a different priority, and separately whether/how to define the product domain gate's own opening criteria — only after both of Task 010's named preconditions close should a future session be asked to prepare a Task 010 gate-opening proposal and final implementation prompt | **Accepted** |
| AR-034 | 2026-07-09 | MBQ-55 product-template/product-variant binding naming/schema proposal, and product-domain gate criteria proposal | After PR #135 (master implementation-readiness checkpoint) merged into `Shopify-connector` (merge commit `308e9cb96b71861f774f1904aeb40f489cff867f`), proposes closure for the product-template/product-variant portion of MBQ-55 via [`../07-implementation-plan/mbq-55-product-binding-naming-schema-proposal.md`](../07-implementation-plan/mbq-55-product-binding-naming-schema-proposal.md) — exact proposed model names (`shopify.connector.product.template.binding`, `shopify.connector.product.variant.binding`), future module/file/class names, and a full field proposal (inherited-mixin, new relational, identity, imported-snapshot, out-of-scope, and deferred buckets), grounded directly in the merged core code (binding mixin, store, store.settings, location) and the already-accepted DEC-006/DEC-008/DEC-013/DEC-014 architecture; also proposes product-domain implementation-gate opening criteria via [`../07-implementation-plan/product-domain-gate-criteria-proposal.md`](../07-implementation-plan/product-domain-gate-criteria-proposal.md); adds a clearly-marked, non-rewriting linkage section to [`../07-implementation-plan/task-010-product-import-proposed.md`](../07-implementation-plan/task-010-product-import-proposed.md) | **Accepted by ChatGPT** — via control-room review, GitHub comment ID `4924917266`, on PR #136; accepts (a) the product-template/product-variant portion of the MBQ-55 naming/schema proposal — model names `shopify.connector.product.template.binding`/`shopify.connector.product.variant.binding`, the proposed module/file/class names, and the field proposal — closing **only** that portion of MBQ-55 (the customer-binding and order-binding portions remain separately open, unaddressed); and (b) the product-domain gate criteria proposal, **as criteria only** — the product-domain implementation gate itself remains closed, and Task 010 remains unauthorized, until a distinct, future, explicit ChatGPT gate-opening act confirms every criterion satisfied | This is a naming/schema and gate-criteria proposal, not a new architecture decision; every accepted constraint cited (module boundary, one-binding-model-per-root-entity, separate GIDs, no-polymorphic-table direction, match-key priority, no-blind-create policy) is restated exactly as its own already-accepted source states it, none newly decided or newly resolved by this entry | ChatGPT review of both proposals against the accepted DEC-006/DEC-008/DEC-013/DEC-014 sources cited, and against the merged core code's own existing conventions | MBQ-55's product-template/product-variant portion is now Accepted/closed by this acceptance; MBQ-55's customer-binding and order-binding portions remain Open, unaddressed. This entry, and the two proposals it records, still must not be read as authorizing Task 010 or any other domain-sync task, opening the Task 010 gate, opening the product-domain gate, or authorizing any code, module, UI/wizard/webhook/OAuth file | Recommended next: with both proposals now accepted (the MBQ-55 product portion; the gate criteria as criteria), a future session may draft Task 010's file-exact final implementation prompt and a product-domain gate-opening proposal referencing the accepted names/criteria — the product-domain gate itself still requires its own distinct, explicit ChatGPT gate-opening act confirming every criterion in the gate-criteria document satisfied before it opens or Task 010 is authorized | **Accepted** |
| AR-035 | 2026-07-09 | Task 010 product import final prompt and product-domain gate-opening proposal | After PR #136 merged into `Shopify-connector` (merge commit `c171d8f9b404f0b9bc066ee6fbef811086f5d0fc`), drafts the file-exact Task 010 final implementation prompt via [`../07-implementation-plan/task-010-product-import-final-implementation-prompt.md`](../07-implementation-plan/task-010-product-import-final-implementation-prompt.md) (marked "DO NOT USE THIS PROMPT UNTIL CHATGPT ACCEPTS THE TASK 010 GATE-OPENING PROPOSAL AND EXPLICITLY ISSUES THIS PROMPT IN CHAT" — not issued), converting the accepted MBQ-55 names into exact allowed/forbidden files, exact schema, an exact MVP dedup-threshold conversion of the already-accepted DEC-014 point H two-tier gate, and an exact job/sync-engine usage recommendation (one `product_import_sync` job type via the existing, already-proven `selection_add`/`_get_handlers()` extension seams, zero core edits); and a product-domain gate-opening proposal via [`../07-implementation-plan/task-010-product-import-gate-opening-proposal.md`](../07-implementation-plan/task-010-product-import-gate-opening-proposal.md), auditing all twelve gate criteria and presenting evidence that criteria 3, 4, 5, 9, and 12 (previously not yet satisfied) are now satisfied by this session's own drafting act, with an explicit, non-overclaiming reconciliation of the checkpoint/resume-ownership blocker (readiness-checkpoint Class A, resolved here per its own named in-task-decision resolution path, not asserted as having already been non-blocking) | **Accepted by ChatGPT** — via control-room review, GitHub comment ID `4926437491`, PR #137. Accepts the final implementation prompt's content (fixing it as binding — **still not issued**) and accepts the gate-opening proposal, which **opens the product-domain implementation gate for exactly one future implementation session — Task 010 only** — effective once PR #137 merges into `Shopify-connector`. **The gate closes again once the future Task 010 implementation PR is opened as draft; that future PR must remain draft until ChatGPT separately reviews it.** This acceptance does not authorize Task 011/012/013/014, Task 015, any UI, webhook, OAuth, or Lite/Full packaging work, and does not, by itself, authorize any Task 010 code — code remains unauthorized until ChatGPT explicitly issues the final prompt, verbatim, in a new Claude Code session, after this PR merges | This session's own governing instructions required stopping before drafting a gate-opening proposal if any of criteria 3/4/5/9/12 proved unsatisfiable by documentation work alone; none did — see the gate-opening proposal's own §3 evidence table | ChatGPT review of [`../07-implementation-plan/task-010-product-import-gate-opening-proposal.md`](../07-implementation-plan/task-010-product-import-gate-opening-proposal.md) against [`../07-implementation-plan/product-domain-gate-criteria-proposal.md`](../07-implementation-plan/product-domain-gate-criteria-proposal.md) §3, and of the final prompt against the accepted MBQ-55 schema — completed, comment ID `4926437491` | Premature use of the final prompt before ChatGPT issues it (mitigated: the prompt's own top warning is unweakened by this acceptance); the acceptance being mistaken for authorization to start Task 010 coding now (mitigated: explicit language above); VAL-B2, MBQ-05, TD-002, the fulfillment API model, Lite/Full packaging, and the multi-server concurrency proof requirement being mistaken as resolved (none is; all remain exactly as open as their own cited sources state, per the gate-opening proposal's own §7) | This entry does not authorize implementation. Next step: this status patch requires ChatGPT's final review, then merge of PR #137; after merge, ChatGPT separately and explicitly issues the final prompt, verbatim, in a new Claude Code session; the resulting implementation PR must remain draft until ChatGPT reviews it, and the gate closes the moment that PR is opened as draft | **Accepted** |
| AR-036 | 2026-07-09 | Task 010 product import implementation — draft PR opened, not yet reviewed | After PR #137 merged into `Shopify-connector` (merge commit `431b4bf`) and ChatGPT issued the final implementation prompt verbatim in a new Claude Code session, this session implements the `shopify_connector_product` addon per that prompt (PR #138, branch `claude/task-010-product-import-gate-0uh7g4`, opened as draft): two concrete binding models (`shopify.connector.product.template.binding`, `shopify.connector.product.variant.binding`), both declaring explicit `_name`/`_inherit` per the accepted MBQ-55 schema; a read-only `shopify.connector.product.importer` `AbstractModel` implementing the final prompt §8 match-key/dedup-threshold sequence (existing binding → SKU → barcode → confident no-match create, gated → ambiguous/blind never create, routed to `blocked_manual_review` via the existing, unmodified `JobHandlerError`/`_route_failure()` mechanism); the three required extension seams (`job_type` `selection_add`, a `_domain_flag_for_job_type()` override mapping `product_import_sync` → `product_domain_enabled`, a `_get_handlers()` override), all declared inside `shopify_connector_product_importer.py` only — zero edits to any `shopify_connector_core` file (confirmed by `git diff --stat`); `ir.model.access.csv` only, reusing the four existing groups, no new group/XML; four required test files (~35 test methods) covering every case named in final prompt §10. Three narrow in-task decisions were made and are recorded in [`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md) §C: (1) a future `res_model`/`res_id` targeting choice — the binding model, not the underlying `product.template`, per final prompt §9's own "pick one of the two already-named candidates" allowance; (2) ambiguous/blind matches never create a binding row (both binding models' `product_template_id`/`product_variant_id` are `required=True`, so a "pending review" binding with no confirmed candidate is structurally impossible without an automatic guess, which DEC-006 forbids) — the outcome is represented entirely at the job level instead, which is what every required §10 test actually asserts; (3) new `product.product` creation is scoped to a brand-new template's own Odoo-generated first/singleton variant only — every other new-variant-under-an-existing-template case routes to `blocked_manual_review`/`duplicate_risk` rather than synthesizing Odoo variant-attribute structure from Shopify option data, which no accepted document specifies | **REVISE** (ChatGPT control-room review of a *second* actual Odoo.sh red build, GitHub comment ID `4927455927`, following two earlier REVISE decisions at comment IDs `4927037139` and `4927278355`) — not marked ready, not merged, Task 010 still not accepted. User-provided Odoo.sh evidence: module `shopify_connector_product` 2 failures / 0 errors of 53 tests; full database load 2 failed / 0 error(s) of 220 tests; the same docutils/RST build-log warning, unchanged. The prior revision's own singleton-variant-matching fix (comment `4927278355`) turned out to be too broad — it also suppressed SKU/barcode variant match-key search for templates resolved via candidate match, not just existing bindings. One production-logic fix applied in the same PR #138: `_resolve_template_binding()` now returns a three-way `template_resolution_source` (`existing_binding`/`candidate_match`/`created`), and `_resolve_deterministic_variant()` now only takes its singleton shortcut for `existing_binding`/`created` sources, never `candidate_match` — restoring correct `sku_reference`/`barcode` variant match-keys while keeping every fix from the prior revision intact. The docutils/RST warning was re-investigated: it recurred at the identical build-log line numbers despite the prior revision's own plain-prose rewrite of the two suspected files, which is evidence the warning does not originate from PR #138's files at all — not proven either way, but no longer chased further, per this revision's own instruction. See the AR-036 Revision Note 3 footnote below and [`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md) §J for full detail. Per final prompt §14, the resulting PR remains **DRAFT** and this session stops again for the next Odoo.sh validation cycle — still not itself an acceptance | This is an implementation-closure-style entry recording what was built, mirroring AR-032's Task-006C-closure pattern, but for a **draft, not-yet-accepted** PR rather than a merged one — no review decision beyond REVISE is asserted | No live Odoo/PostgreSQL runtime was reachable in this session (no `odoo` package installed, no Odoo.sh/CI access) — every check is static only (`py_compile`, `pyflakes`, source-level greps for zero-mutation/zero-bypass/zero-forbidden-model), full detail in the validation-results doc §D; the four new test files are written and statically valid but **not execution-proven**; ChatGPT's own review of the PR diff and of the three in-task decisions above is still required | Runtime execution proof for the four new test files remains outstanding; the three in-task scope decisions in this row could be found too conservative, or otherwise in need of revision, on ChatGPT's review; VAL-B2, MBQ-05, TD-002, the fulfillment API model, Lite/Full packaging, and the multi-server concurrency proof requirement (SRR-03/04/09) all remain exactly as open as before this task — none is touched, resolved, or narrowed; no Task 011/012/013/014, Task 015, UI, webhook, OAuth, or Lite/Full packaging work is authorized or started by this task | ChatGPT reviews the draft PR against final prompt §3–§14 and this row's own evidence; the PR must not be marked ready for review or merged without that review, per final prompt §14 — the product-domain implementation gate closes the moment this PR was opened as draft (product-domain-gate-criteria-proposal.md §4; task-010-product-import-gate-opening-proposal.md §9), so no further product-domain work may start regardless of this PR's own outcome | **Accepted** |
| AR-037 | 2026-07-09 | MBQ-55 customer-binding naming/schema proposal, customer-domain gate criteria proposal, and Task 011 readiness assessment | After PR #138 (Task 010 implementation) and PR #139 (Task 010 post-merge closure docs) both merged into `Shopify-connector` (latest merge commit `297f398da96d11d1f8f9e25a9d15570a66aed80a`), proposes closure for the customer-binding portion of MBQ-55 via [`../07-implementation-plan/mbq-55-customer-binding-naming-schema-proposal.md`](../07-implementation-plan/mbq-55-customer-binding-naming-schema-proposal.md) — exact proposed model name (`shopify.connector.customer.binding`), future module/file/class names, a full field proposal (inherited-mixin, new relational, imported-snapshot, out-of-scope, and deferred buckets), and a proposed store-settings home (`customer_fallback_partner_id`) for the MBQ-29-resolved single fallback-partner-per-store concept, grounded directly in the merged core code and the already-accepted DEC-006/DEC-008/DEC-013/DEC-014 architecture, mirroring the AR-034/PR #136 pattern used for the product portion; also proposes customer-domain (Task-011-scoped only, explicitly not order-import) implementation-gate opening criteria via [`../07-implementation-plan/customer-domain-gate-criteria-proposal.md`](../07-implementation-plan/customer-domain-gate-criteria-proposal.md); adds a non-rewriting scope/readiness refresh, [`../07-implementation-plan/task-011-customer-import-proposed.md`](../07-implementation-plan/task-011-customer-import-proposed.md), citing rather than editing the existing [`task-011-customer-import-matching-proposed.md`](../07-implementation-plan/task-011-customer-import-matching-proposed.md); and a full Task-011-scoped blocker-classification readiness assessment mirroring `master-implementation-readiness-checkpoint.md`, via [`../07-implementation-plan/task-011-customer-import-gate-readiness.md`](../07-implementation-plan/task-011-customer-import-gate-readiness.md), concluding **not ready** — the customer-domain gate has never been opened and its trigger conditions were undefined until this session's own proposal, and MBQ-55's customer-binding portion remains open pending this session's proposal's own acceptance. This session also confirms, by direct read of the open-questions register, that **MBQ-29 (default-customer fallback) is now Resolved** (not merely partially resolved as DEC-014 alone stated) via the Final MBQ closure pass (AR-020, 2026-07-05) — a genuine narrowing recorded in all four documents above, correcting an unreconciled discrepancy the original Task 011 draft had flagged | **REVISE** (ChatGPT control-room review, GitHub comment ID `4928244425`) — not accepted, PR #140 kept **draft**, not merged. ChatGPT found the naming proposal's ambiguous-customer-match behavior unsafe and structurally inconsistent: it proposed creating a `shopify.connector.customer.binding` row in `status = 'review'` with no `match_key` for an ambiguous match, but `partner_id` is `required=True` — an ambiguous match has no single confirmed candidate, so creating a row would force an automatic guess among several `res.partner` candidates, contradicting DEC-006/RA-006 and the Task 010 precedent (ambiguous/blind product matches never create a binding row). ChatGPT also required an explicit Task 011/Task 012 boundary for the fallback-partner concept, so it does not drag order-import behavior into Task 011. **Revision applied in the same PR:** `mbq-55-customer-binding-naming-schema-proposal.md` §3/§7.1.A/§9/§10/§11 revised so an ambiguous match creates no binding row — the job routes to `blocked_manual_review` with candidate `res.partner` detail stored at job/log level only, never in a binding row; `status = 'review'` is now explicitly scoped to lifecycle review of an already-real binding only. §7.3/§9/§10 revised to adopt **Posture A**: Task 011 proposes only the `customer_fallback_partner_id` store-settings field as inert config substrate, with zero order-resolution behavior and zero consumption within Task 011's own flow — order-level routing/audit-marker logic remains entirely Task 012's future scope. `customer-domain-gate-criteria-proposal.md` gained a new criterion 15 (ambiguous-match handling) and a revised criterion 13 (fallback-partner boundary); `task-011-customer-import-gate-readiness.md` §5/§9 and `task-011-customer-import-proposed.md` §1/§2 updated for consistency. **Conclusion unchanged: Task 011 still not ready to gate; no implementation authorized** | This is a correction to a naming/schema proposal after control-room review, not a new architecture decision; the corrected posture reuses only already-accepted DEC-006/RA-006 (no automatic guessing) and the already-established Task 010 precedent (ambiguous/blind matches never create a binding row), extending both to the customer domain rather than inventing new rules | ChatGPT review of comment `4928244425` against the original naming proposal; this revision's own self-audit confirms `partner_id` remains required, no placeholder binding row is created for an ambiguous match, candidate detail is stored at job/log level only, and the fallback-partner boundary is stated consistently across all four Task-011 documents | The exact job/log field(s) used to store ambiguous-match candidate detail remain open, named as new criterion 15/blocker row for a future final implementation prompt to fix; MBQ-55's customer-binding portion remains Open, now revised but still not accepted; the order-binding portion of MBQ-55 remains fully Open and untouched. This entry, and the four documents it records, must not be read as authorizing Task 011, Task 012, or any other domain-sync task, opening the Task 011 gate, opening the customer-domain gate, or authorizing any code, module, UI/wizard/webhook/OAuth file | Recommended next: ChatGPT re-reviews the revised customer-binding naming/schema proposal and the revised customer-domain gate-criteria proposal together against comment `4928244425`'s own concerns; if accepted, a future session may draft Task 011's file-exact final implementation prompt and a customer-domain gate-opening proposal referencing the accepted names/criteria — the customer-domain gate itself would still require its own distinct, explicit ChatGPT gate-opening act confirming every criterion in the gate-criteria document satisfied before it opens or Task 011 is authorized | **Proposed** |

_**AR-036 Acceptance Note (2026-07-09, post-merge) — PR #138 merged into
`Shopify-connector`, merge commit
`1f478032d8581a949fa7820847e5c1ab419586b4`; Odoo.sh runtime build green.**
Following the three REVISE cycles addressed by AR-036 Revision Note,
Revision Note 2, and Revision Note 3 below (comment IDs `4927037139`,
`4927278355`, `4927455927`), PR #138 was merged. A subsequent Odoo.sh
runtime build reports: `shopify_connector_core` 187 tests,
`shopify_connector_product` 61 tests, **0 failed, 0 error(s) of 220
tests**; database/build `adamsmen-shopify-connector-34704468`;
timestamps `2026-07-09 17:18:02`–`17:18:12`. The build log's SQL `ERROR`
lines and ACL `denied` lines are expected negative-test noise from this
addon's own required-field-constraint and access-matrix tests (not
failures — see
[`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
§K.3 for the full explanation). **Task 010's runtime validation is
accepted; this row's Status is updated from Proposed to Accepted.**
Full evidence record:
[`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
§K. **The following risks remain explicitly open, unresolved, and
untouched by this acceptance:** VAL-B2, MBQ-05, TD-002, the fulfillment
API model decision, Lite/Full packaging, and the multi-server/
concurrent-worker safety proof (SRR-03/04/09). This acceptance does not
authorize Task 011 (customer import/matching), Task 012 (order import),
Task 013 (inventory sync), Task 014 (fulfillment/tracking), Task 015
(product write/export), any UI, webhook, OAuth, or Lite/Full packaging
work — the next step is a separate, explicit planning/gate proposal for
whichever task ChatGPT selects next, not direct implementation._

_**AR-036 Revision Note 3 (2026-07-09, PR #138 control-room review of a
second Odoo.sh red build, GitHub comment ID `4927455927`) — REVISE,
addressed in this revision.** After AR-036 Revision Note 2's own fix was
pushed, a second Odoo.sh build ran (evidence provided by the user) and
was still red: module `shopify_connector_product` reported 2 failures /
0 errors of 53 tests; the full database load reported 2 failed / 0
error(s) of 220 tests; the same docutils/RST build-log warning recurred
at the identical `<string>:38`/`<string>:43` location. ChatGPT reviewed
this evidence and returned **REVISE** again. **Root cause:** Revision
Note 2's own `_resolve_deterministic_variant()` fix was too broad — it
took the singleton-variant shortcut whenever the *resolved* template had
exactly one Odoo variant and the payload carried exactly one variant,
regardless of *how* that template was resolved. This correctly covered
the intended existing-binding case, but also incorrectly covered the
SKU/barcode candidate-match case: `TestProductImportMatching.
test_sku_match_when_no_existing_binding` and `..._test_barcode_match_
when_no_sku_match` both failed with the variant binding's own
`match_key` left `False` instead of `sku_reference`/`barcode`, because
the shortcut skipped `_find_variant_candidates()` entirely for those
templates too. **Fix (production logic, not a test-only change):**
`_resolve_template_binding()` now returns a three-way
`template_resolution_source` string (`'existing_binding'`,
`'candidate_match'`, or `'created'`) instead of a `just_created`
boolean; `_resolve_deterministic_variant()` now gates its singleton
shortcut strictly on `template_resolution_source`, so a template
resolved via SKU/barcode candidate match always runs its variant(s)
through the ordinary match-key search, while the existing-binding
singleton case, its already-bound-singleton guard, and the
multi-variant conservative/atomic case (all from Revision Note 2) are
completely unchanged. No new test method was added -- the two
previously-failing tests already exercise the exact regression shape and
now pass by production-code fix alone; both received a docstring
annotation recording this as the regression scenario, and all five
Revision Note 2 tests were re-traced by hand and confirmed unaffected.
The docutils/RST warning was re-investigated: it recurred at the exact
same line numbers even though Revision Note 2's own plain-prose rewrite
of the manifest description and the importer's class docstring had
already substantially changed both files' content by the time this
second build ran (commit `636493e`) — since neither file's content
change shifted the reported line, this is evidence against those two
files being the true source, and the warning is not proven to be
introduced by PR #138 at all. A fresh local `docutils` scan across all
twelve files this PR has ever touched found zero warnings. Test count
unchanged at 53. Validation remains: `py_compile`/`pyflakes` clean; the
same source-level guards re-run clean; **no Odoo runtime was available
in this session's own sandbox to re-execute the fixed tests** -- the fix
is traced by hand against the real Odoo.sh failure evidence, but this
session does not, and cannot, claim a new green Odoo.sh build. PR #138
remains **draft, unmerged**. Full detail:
[`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
§J._

_**AR-036 Revision Note 2 (2026-07-09, PR #138 control-room review of an
Odoo.sh red build, GitHub comment ID `4927278355`) — REVISE, addressed
in this revision.** After the static-content-accepted PR #138 was run
through an actual Odoo 19 runtime on Odoo.sh (evidence provided by the
user), the build was red: module `shopify_connector_product` reported 0
failures / 2 errors of 51 tests; the full database load reported 0
failed / 2 error(s) of 218 tests; the build log also carried a docutils/
RST warning (`<string>:38` ERROR/3 unexpected indentation,
`<string>:43` WARNING/2 block quote ends without a blank line).
ChatGPT reviewed this evidence and returned **REVISE**. Three fixes
applied, all inside the existing Task 010 allowed-file envelope, no
`shopify_connector_core` file touched, no file added outside that
envelope: (1) **existing-template-binding singleton-variant matching**
— a real production-logic gap, not a test-only defect:
`_apply_import()` previously had no path to bind a single incoming
Shopify variant to an *already-resolved* (not newly created) template's
own single, unbound Odoo variant, so it always fell through to
SKU/barcode candidate search and raised `duplicate_risk` whenever that
search found nothing, even when exactly one Odoo record could possibly
be correct; fixed via a new `_resolve_deterministic_variant()` method,
applied when the resolved template already has exactly one Odoo variant
and the incoming Shopify payload carries exactly one variant, still
guarded against binding an Odoo variant already claimed by a
*different* Shopify variant (blocked with a classified
`JobHandlerError('duplicate_risk', ...)` naming the conflicting GID);
multi-variant payloads under an existing template are completely
unaffected -- the shortcut never applies when there is more than one
incoming Shopify variant. Two new tests added, one existing test
strengthened. (2) **`TestProductVariantBinding.test_access_matrix_
across_four_groups`** — a test-fixture-only bug: its supporting
`product.template` record was created via
`.with_user(self.user_admin)`, forcing the connector admin test user's
own non-superuser Odoo access context, and the connector admin group is
correctly *not* a member of Odoo's own Products/Create group; fixed by
creating that record via the normal test environment/setup user
instead, matching the pattern this same test file's own
`_make_template_binding()` helper already used -- **no connector group
ACL was touched**, `ir.model.access.csv` is unchanged. (3) **docutils/
RST build-log warning** — investigated with a locally-installed
`docutils` (0.23) systematic parse of every docstring and manifest
field in `shopify_connector_product` (and, for completeness,
`shopify_connector_core`, which this task must not edit regardless); no
exact reproduction of `<string>:38`/`<string>:43` was found, honestly
reported as inconclusive; applied the final prompt's own explicit
fallback instruction anyway and rewrote both the manifest `description`
and the importer class's docstring (the two files control-room comment
`4927278355` named as most likely) as plain prose, removing every RST/
Markdown-sensitive construct (double-backtick literals, bulleted/
numbered lists, bold markers, a section-title underline) while
preserving every substantive fact the original content recorded; no
functional behaviour changed. Test count grew from 51 to **53**
methods. Validation remains: `py_compile`/`pyflakes` clean; the same
source-level guards re-run clean; the local `docutils` scan re-run
clean on both rewritten strings; **no Odoo runtime was available in
this session's own sandbox to re-execute the fixed tests** -- the fixes
are traced by hand against the real Odoo.sh failure evidence, but this
session does not, and cannot, claim a new green Odoo.sh build. PR #138
remains **draft, unmerged**. Full detail:
[`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
§I._

_**AR-036 Revision Note (2026-07-09, PR #138 control-room review, GitHub
comment ID `4927037139`) — REVISE before merge, addressed in this
revision.** ChatGPT reviewed PR #138 and returned **REVISE before
merge**: not marked ready, not merged, Task 010 still not accepted.
Four required fixes were identified and applied, all inside
`shopify_connector_product_importer.py` only (no other production file
touched; no file added outside the existing Task 010 allowed-file
envelope; no `shopify_connector_core` file touched): (1) **Shopify API
client error taxonomy preservation** — `import_product_sync()` now
catches `ShopifyClientError` (imported read-only from
`shopify_connector_core`'s own API-client module, not an edit to it)
and re-raises it as `JobHandlerError(exc.error_class, exc.reason,
exc.technical_detail)`, so throttling/temporary-network/permission-
scope-auth failures keep their accepted DEC-009 error class through
`_route_failure()` instead of being reclassified as
`unknown_system_error` by the dispatcher's generic exception boundary;
`exc.credential_invalid`-triggered store-lifecycle side effects (e.g.
marking the store `reconnect_needed`, as `shopify_connector_store.py`'s
`action_test_connection()` does) are deliberately not replicated here —
out of this task's own scope. Four new tests confirm throttling and
temporary-network each route to `retry_waiting` and permission/scope/
auth routes to `failed_retryable`, none becoming `unknown_system_error`,
plus a test confirming the importer itself never retries. (2) **Atomic
one-product import** — `_apply_import()`'s entire write sequence now
runs inside one `self.env.cr.savepoint()` block (the same mechanism
this addon's own binding-model tests already used to probe a constraint
violation), so a later-variant classified failure rolls back every
write the call made. A regression test proves a two-variant payload
where variant 2 always fails `duplicate_risk` leaves zero residue — no
template, no product, no template binding, no variant binding for
either GID — and a companion test proves the savepoint does not affect
a separate, already-successful import. (3) **Malformed-payload
validation** — a new `_validate_payload()` method runs before any write
and raises `JobHandlerError('data_shape_schema_mismatch', ...)` for a
missing product node/GID, a missing variant GID, or an unexpected
product status; six new tests cover each case plus a regression guard
that the four accepted statuses remain allowed. (4)
**Variant-pagination-truncation guard** — `PRODUCT_IMPORT_QUERY` now
requests `variants.pageInfo.hasNextPage`/`endCursor`; `_validate_
payload()` blocks the import with `data_shape_schema_mismatch` when
`hasNextPage` is true rather than silently importing only the first 100
variants (full pagination remains out of Task 010's scope — this is a
block, not an implementation); four new tests cover the blocked case
(unit + end-to-end) and a regression guard that a normal, single-page
response is not blocked. Test count grew from 4 files/~35 methods to 4
files/**51 methods**. Validation remains static only (no `odoo`
package/Odoo.sh/CI reachable in this session) — `py_compile`/`pyflakes`
clean on every changed file; the same source-level mutation/bypass/
forbidden-model guards re-run clean; all 51 test methods, including the
17 new ones, are written and statically valid but **not
execution-proven**. PR #138 remains **draft, unmerged** — not marked
ready, not merged. Full detail:
[`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
§H._

_**AR-035 Acceptance Note (2026-07-09) — PR #137 control-room review,
GitHub comment ID `4926437491`: content accepted, final status patch
applied.** ChatGPT confirmed every precision fix from the prior REVISE
(comment `4925370944`, see the AR-035 Revision Note immediately below)
and accepted PR #137's content. **This note records the gate-opening act
[`product-domain-gate-criteria-proposal.md`](../07-implementation-plan/product-domain-gate-criteria-proposal.md)
§4 required: the product-domain implementation gate now opens for
exactly one future implementation session — Task 010 only — effective
once PR #137 merges into `Shopify-connector`**, mirroring the AR-029
(Task 003) and AR-031 (Task 006C) gate-opening pattern exactly. **The
gate closes again the moment the future Task 010 implementation PR is
opened as draft; that future PR must remain draft until ChatGPT
separately reviews it.** This acceptance also fixes
[`../07-implementation-plan/task-010-product-import-final-implementation-prompt.md`](../07-implementation-plan/task-010-product-import-final-implementation-prompt.md)'s
content as binding — its status is now **Accepted final prompt / Not
issued** — but **does not issue it**: the prompt's own top warning ("DO
NOT USE THIS PROMPT UNTIL CHATGPT ACCEPTS THE TASK 010 GATE-OPENING
PROPOSAL AND EXPLICITLY ISSUES THIS PROMPT IN CHAT") remains unweakened,
and Claude must not use it until ChatGPT explicitly pastes/issues it,
verbatim, into a **new** Claude Code session, as its own later chat turn,
after PR #137 merges. **This note does not merge PR #137, does not mark
it ready, does not implement Task 010, and does not authorize any other
product-domain task, Task 011/012/013/014, Task 015, any UI, webhook,
OAuth, or Lite/Full packaging work.** No addon/code/test/manifest/XML/
security/migration/CI file was touched by this patch — docs only. Next →
ChatGPT's final review of this status patch, then merge; after merge,
ChatGPT separately and explicitly issues the final prompt as a new
Claude Code session's opening turn; that session's resulting PR must
remain draft until ChatGPT reviews it._

_**AR-035 Revision Note (2026-07-09) — PR #137 control-room review,
GitHub comment ID `4925370944`: REVISE before merge.** Decision: PR #137
requires revision before merge; not marked ready; not merged; Task 010
not authorized; product-domain gate not opened. Five precision gaps were
identified in the final implementation prompt and fixed in this revision:
(1) the future manifest's `depends` now explicitly includes Odoo's own
`product` module, not just `shopify_connector_core`, and the "two
security files" wording is corrected to name the one actually-allowed
file; (2) `shopify_option_values`/`shopify_price_snapshot`/
`shopify_compare_at_price_snapshot` now name exact Odoo field types
(`fields.Text`/`fields.Float`) instead of "Char or Text"/"Monetary or
Float", with no currency field authorized; (3) both concrete binding
models now explicitly declare `_name` alongside `_inherit`, not implied;
(4) a required third seam extension was added — a
`_domain_flag_for_job_type()` override on `shopify.connector.job`,
declared inside the one already-allowed importer file, mapping
`product_import_sync` to the already-existing `product_domain_enabled`
flag on `shopify.connector.store.settings` (confirmed directly this
revision) and preserving `super()` for every other `job_type` — so the
new job type is gated by the same product-domain-enablement mechanism
`shopify.connector.job.write()` already implements, instead of silently
bypassing it; (5) tests proving that gating (disabled / missing-settings
/ enabled cases) and `core_dispatch_selftest` preservation were added to
the already-allowed `test_product_import_matching.py` — no new test file.
The product-domain gate-opening proposal's §3 evidence table and §6/§8
were updated to reflect the revised final prompt; its own Status remains
**Proposed / Under review, not accepted**. AR-035's own Status remains
**Proposed / Under review, not accepted** — this note records a revision
to the same proposed package, not a new acceptance or a new gate act. No
addon/code/test/manifest/XML/security/migration/CI file was touched by
this revision — docs only._

_**AR-029 Gate-Opening Note (2026-07-07) — the Task 003 API-client/
test-connection implementation gate is opened by this act, effective
once
[`task-003-api-client-test-connection-gate.md`](../07-implementation-plan/task-003-api-client-test-connection-gate.md)
is merged into `Shopify-connector`.** This is a gate-opening act in the
AR-021/AR-026 pattern, not a research or planning acceptance: it
authorizes **exactly one** future coding session — Task 003 (API Client
Shell and Test Connection) — using the exact contracts already accepted
in
[`task-003-final-implementation-prompt.md`](../07-implementation-plan/task-003-final-implementation-prompt.md).
**This act also applies the AR-028 acceptance patch** (see the AR-028
row above, now Accepted) — PR #99 merged AR-028's package
(`task-003-final-implementation-prompt.md`,
`task-003-gate-opening-proposal.md`) while it was still marked Proposed
in its own text, so this document is the first point at which ChatGPT's
acceptance of that package is formally recorded, immediately followed
by the gate-opening act itself, mirroring the combined effect of the
separate AR-025-then-AR-026 sequence. **Preconditions confirmed before
this act:** PR #97 merged (`7498ba181a01e571204e471d6880ea0c2068fd87`,
Task 002 implementation); PR #98 merged
(`2e51cf02cd54527ff9dc817b6be1e1189f001a83`, AR-027 accepted with the
F1 revision); PR #99 merged
(`756b88eca79f2ef56ff752b6ba82ab266a782724`, AR-028 package); all three
confirmed ancestors of the branch this act was authored from; Task 003
not started (no API client, no `action_test_connection`, no
`core_test_connection` value, no job-log system-append method exists in
the repository). **This act does not implement Task 003, does not
create the API client or any model/field, and does not create any
code, and makes no external network call** — it is docs-only, and the
final prompt is not issued inside this PR. Setup wizard,
UI/views/menus/actions/wizards, webhooks/controllers/cron,
product/customer/order/inventory/fulfillment, domain modules,
credential-model changes, ACL/security-file changes, mutations, Bulk
Operations, REST calls, and any fix to `core_readiness_check`/`TD-001`
remain forbidden and unauthorized; DEC-003 through DEC-020,
`docs/04-decisions/README.md`, and `docs/05-qa/defect-pattern-log.md`
are unchanged. **The gate closes once the future Task 003
implementation PR is opened as draft** — no follow-on coding beyond
that PR is authorized by this act. Next → after this PR merges, issue
[`task-003-final-implementation-prompt.md`](../07-implementation-plan/task-003-final-implementation-prompt.md)
verbatim as a separate Task 003 coding session; that session's PR must
remain draft until ChatGPT reviews it._

_**AR-028 (2026-07-07) — Task 003 final implementation prompt and
gate-opening proposal, proposed only, NOT accepted.** Prepared on branch
`claude/task-003-gate-opening-no0tw4`, from `Shopify-connector` at PR
#98's merge commit `2e51cf02cd54527ff9dc817b6be1e1189f001a83` (confirmed
the tip of `Shopify-connector` before starting). This is a **docs-only
gate-preparation session** — it closes no new decision (AR-027 already
closed all four Task 003-specific points) and opens no implementation
gate. It packages (1) the complete, copy-paste final Task 003
`CLAUDE.md` §9 prompt
([`../07-implementation-plan/task-003-final-implementation-prompt.md`](../07-implementation-plan/task-003-final-implementation-prompt.md),
applying `core_test_connection`; the `SHOP_INACTIVE`/402/423/
403-fraudulent → `shopify_permission_scope_auth` mapping with
`credential_state` gating and five mandatory distinct plain-language
reasons; the `_system_append` job-log system-append method as the
single new sanctioned `sudo()` site; and the per-run UUID4
`payload_hash` nonce for `core_test_connection` job creation only —
marked **not issued, not authorized**), and (2) a narrow gate-opening
proposal
([`../07-implementation-plan/task-003-gate-opening-proposal.md`](../07-implementation-plan/task-003-gate-opening-proposal.md))
scoping the **first** conscious widening of the AR-021 no-external-API
rule to exactly the read-only API-client shell and test-connection
service — **the proposal itself opens nothing**. `core_readiness_check`
(`TD-001`) is explicitly excluded from the proposed gate scope, per
AR-027's F1 revision; it is named only as a possible future
explicitly-authorized inclusion, not folded in here. No `main`/plain
`dev` touched; no external network call; no Shopify API call; no addon
code, Python, XML, CSV, manifest, test, or CI file created or modified.
**Next: ChatGPT reviews AR-028; if accepted, a separate, explicit Task
003 gate-opening act (mirroring
[`task-002-credential-storage-gate.md`](../07-implementation-plan/task-002-credential-storage-gate.md)
for AR-026) must still be prepared and merged before the final prompt
may be issued — not performed by this entry.**_

_**AR-027 Acceptance Patch (2026-07-07) — AR-027 is now Accepted by
ChatGPT, with an F1 revision to Decision 4.** Prepared on PR #98
(branch `claude/task-003-decisions-xx7u85`), proposed the same day this
patch was applied — the proposal and its acceptance both land in this
same PR/branch, before merge, per the AR-025/PR #94 convention. ChatGPT
accepted Decisions 1–3 exactly as proposed: `core_test_connection`
confirmed as the `job_type` value (amending AR-019's fixed-at-two-values
statement to three, effective once this PR merges — see the AR-019
amendment note below); `SHOP_INACTIVE`/402/423/403-fraudulent confirmed
mapped to `shopify_permission_scope_auth`, with the `credential_state`-
gating refinement and a distinct, **mandatory** plain-language reason
per condition; the sanctioned internal `sudo()`-wrapped job-log
system-append method confirmed over ACL widening, no security-file
change. **ChatGPT's F1 revision on Decision 4:** the per-run UUID4
`payload_hash` nonce is accepted **for `core_test_connection` job
creation only** — the original proposal's implication that Task 003
should also populate the nonce for the already-merged
`core_readiness_check` job type is **rejected as written**, since that
would silently pull a fix to already-accepted Task 001 schema into Task
003's implementation boundary without a named authorization.
`core_readiness_check`'s identical latent collision exposure is instead
recorded as **`TD-001`** in
[`technical-debt-register.md`](./technical-debt-register.md) (the
register's first real entry) and routed to either a future,
explicitly-named inclusion in a later gate, or its own separate, tiny
follow-up patch (candidate name: "Task 001B — job-framework target-less
idempotency patch"). `shopify_user_errors_validation` — the named
alternative to the accepted error-class mapping — is logged as
**`RA-024`** in
[`rejected-approaches-log.md`](./rejected-approaches-log.md), per the
ADR template convention that rejected alternatives are recorded at
acceptance time. A short amendment note is added to AR-019's row (below)
and to `master-blueprint-open-questions.md`'s MBQ-44 row; no other
MBQ/DEC/AR row is touched. **This acceptance does not open the Task 003
implementation gate** — no API client, test connection, setup wizard,
UI, webhook/controller/cron, or domain logic is authorized; a separate,
explicit gate-opening act and final `CLAUDE.md` §9 prompt remain
required, in a later, separate session (mirroring AR-025 → AR-026 for
Task 002)._

_**AR-019 amendment note (2026-07-07, via AR-027):** AR-019's accepted
`shopify.connector.job` schema fixed `job_type` at exactly two
core-owned values (`core_readiness_check`, `core_manual_maintenance`).
AR-027's acceptance adds a third, `core_test_connection`, as a one-line
addition to the base Selection (not via the domain-module
`selection_add` seam). AR-019's six-model schema and every other detail
are otherwise unchanged by this amendment._

_**AR-026 Gate-Opening Note (2026-07-07) — the Task 002 credential-storage
implementation gate is opened by this act, effective once
[`task-002-credential-storage-gate.md`](../07-implementation-plan/task-002-credential-storage-gate.md)
is merged into `Shopify-connector`.** This is a gate-opening act in the
AR-021 pattern (`limited-core-implementation-gate.md`), not a research
or planning acceptance: it authorizes **exactly one** future coding
session — Task 002 (Credential Storage, Masking, and Redaction
Foundation) — using the exact contracts already accepted via AR-025 in
[`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md).
**Preconditions confirmed before this act:** PR #94 merged into
`Shopify-connector` (merge commit `03ffcb4dc949cd5137b589a6cdc33da9105de31d`,
confirmed an ancestor of the branch this act was authored from); AR-025
Accepted (2026-07-07); compute-blank rejected for Task 002;
`token_variant = offline_custom_app` accepted; scope snapshot on
`shopify.connector.store` accepted; the final prompt accepted as
gate-ready and binding; the gate proposal accepted as the proposed
scope; Task 002 not started; Task 003 not started. **This act does
not implement Task 002, does not create the credential model or any
token field, and does not create any code** — it is docs-only, and the
final prompt is not issued inside this PR. API client, test
connection, setup wizard, UI/views/menus/actions/wizards,
webhooks/controllers/cron, product/customer/order/inventory/
fulfillment, domain modules, external network calls, and Task 003
remain forbidden and unauthorized; DEC-003 through DEC-020,
`docs/04-decisions/README.md`, and `docs/05-qa/defect-pattern-log.md`
are unchanged. **The gate closes once the future Task 002
implementation PR is opened as draft** — no follow-on coding beyond
that PR is authorized by this act, and Task 003 requires its own
separate decision/gate act. Next → after this PR merges, issue
[`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md)
verbatim as a separate Task 002 coding session; that session's PR must
remain draft until ChatGPT reviews it._

_**AR-025 Acceptance Patch (2026-07-07) — AR-025 is now Accepted by
ChatGPT.** ChatGPT reviewed PR #94
([`task-002-decision-closure.md`](../07-implementation-plan/task-002-decision-closure.md),
[`task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md),
[`task-002-gate-opening-proposal.md`](../07-implementation-plan/task-002-gate-opening-proposal.md),
[`task-002-pre-implementation-review-checklist.md`](./task-002-pre-implementation-review-checklist.md))
and **accepted it on 2026-07-07, at decision/gate-preparation level
only.** AR-025's table row above moves from "Proposed" to
**"Accepted."** **Decision 1:** the compute-blank no-read-back
hardening variant is **rejected for Task 002** — `access_token`
remains a plain stored `fields.Char` with `copy=False` and Admin-only
`groups=`, the model ACL remains Admin-only/default-deny for the other
roles, and no compute/inverse/raw-SQL/hand-managed-column/companion
stored field exists; the honest residual must be documented
(Admin-group ORM/RPC read technically possible outside connector
surfaces; `sudo()`/database/backup access reads the plaintext; no
encryption claim). **Decision 2:** Task 002 uses exactly one
`token_variant` value (`offline_custom_app`) and stores exactly one
secret value (`access_token`) — no `client_id`/`client_secret`/token
cache/expiry field/refresh machinery/client-credentials
implementation; **MBQ-05 remains open** for the MVP acquisition-path
decision and setup-wizard copy. **Decision 3:** `granted_scopes` and
`granted_scopes_checked_at` belong on `shopify.connector.store` as
readonly status mirrors; Task 002 creates the fields with no writer;
Task 003 writes them after test connection. **The final Task 002
implementation boundary is accepted** (credential model; six store
mirrors; redaction utility; four service methods; one Admin-only ACL
row; tests; manifest version bump; handoff update). **The final
implementation prompt is accepted as gate-ready and binding but is not
issued.** **The gate-opening proposal is accepted as the proposed gate
scope but the gate is not opened by this acceptance.** API client,
test connection, setup wizard, UI/views/menus/actions/wizards,
webhooks/controllers/cron, product/customer/order/inventory/
fulfillment, domain modules, external network calls, and Task 003 all
remain forbidden and unauthorized; the four Task 003-only decision
points (`core_test_connection` job-type value; `SHOP_INACTIVE`/402/
423/403-fraudulent error-class mapping; job-log system-append write
path vs. ACL widening; per-run `payload_hash` nonce) remain open.
Register impact applied: MBQ-04 remains **Partially resolved** (not
fully resolved); MBQ-05 remains **open**; MBQ-44 status unchanged.
**No implementation gate is opened. Task 002 is not started. Task 003
is not started. No code is authorized by this acceptance.** Next → the
separate, explicit Task 002 gate-opening act, then the final prompt is
issued verbatim._

_**AR-024 Acceptance Patch (2026-07-06) — AR-024 is now Accepted by
ChatGPT.** ChatGPT reviewed PR #92
([`credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md),
[`credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md),
[`task-002-credential-storage-redaction-proposed.md`](../07-implementation-plan/task-002-credential-storage-redaction-proposed.md),
[`task-003-api-client-test-connection-proposed.md`](../07-implementation-plan/task-003-api-client-test-connection-proposed.md),
[`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md))
and **accepted it on 2026-07-06, at implementation-planning level only.**
AR-024's table row above moves from "Proposed for ChatGPT review" to
**"Accepted."** **The credential/connection/API-client foundation
planning package is accepted at implementation-planning level**: the
recommended **Option C** — a dedicated Admin-only
`shopify.connector.store.credential` model, one row per store, secret
value held on the credential model (not on `store`/`store.settings`),
non-secret status mirrors on `shopify.connector.store`, Admin-only ACL
with no rows for auditor/operator/reviewer, field-level `groups=` on the
secret value as a second layer, no unlink, no connector-surface
read-back for any role including Admin — **is accepted at planning
level, explicitly as a justified post-AR-022 / MBQ-04 addition to the
previously accepted AR-019 six-core-model plan** (AR-019 §11 named
exactly this revisit condition: "a future MBQ-04 decision may add a
credential model later" — met by AR-022). **The redaction/no-logging
contract (shared `redact()` utility, `SENSITIVE_KEYS`, `shpat_`/`shprt_`
value patterns, exact-value scrub, source-side and sink-side
enforcement, no token in job logs/technical detail/exceptions/chatter/
Python logs/store mirrors/failure summaries) is accepted at planning
level.** **Task 002 (credential storage, masking, redaction foundation)
is accepted as the recommended next coding task — not authorized by this
acceptance.** **Task 003 (API client shell / test connection) is
accepted as the proposed follow-up task — not authorized by this
acceptance**, including its planning-level constraints (one core-owned
GraphQL client boundary; read-only test-connection query; no mutations;
no domain sync; no webhooks; no cron; no setup wizard UI). **No
implementation gate is opened. No code is authorized.** The following
seven decision points remain explicitly **open** and are not decided by
this acceptance: the compute-blank no-read-back hardening variant;
`token_variant` vocabulary and the MBQ-05 acquisition-path direction;
scope-snapshot placement; the `core_test_connection` job-type value; the
`SHOP_INACTIVE`/402/423/403-fraudulent error-class mapping; the job-log
system-append write path vs. ACL widening; the per-run `payload_hash`
nonce for repeat target-less jobs. Also accepted as current planning
facts: new custom apps can no longer be created in the Shopify admin;
existing admin-created apps continue to work; admin-created custom-app
token rotation requires uninstall/reinstall; Dev Dashboard
client-credentials flow returns 24-hour tokens; the GraphQL Admin API
uses a versioned endpoint + `X-Shopify-Access-Token`; GraphQL may return
HTTP 200 with `errors[]`. The following remain unsupported and require
empirical verification in Task 003: THROTTLED body shape; invalid-token
HTTP status; missing-scope error shape; `shop`/`currentAppInstallation`
scope requirements. **MBQ-04 register-impact wording is now applied to
`master-blueprint-open-questions.md`** — MBQ-04 upgraded from posture
level to **implementation-planning level**, remaining **Partially
resolved** (not fully resolved; full closure requires Task 002's
implementation to be reviewed and accepted); MBQ-05 records the official
Shopify findings above without being prematurely resolved; MBQ-06,
MBQ-44, MBQ-51, MBQ-52, and MBQ-08 receive the planning-note updates
named in the planning document's §Proposed register impact. DEC-003
through DEC-020 remain unchanged; `../04-decisions/README.md` remains
unchanged; `defect-pattern-log.md` remains unchanged. **No credential
model/field, API client, setup wizard, test-connection, webhook,
controller, cron, or domain-module implementation is created or
authorized by this acceptance.** **The next step is a separate, explicit
ChatGPT gate-opening act and final `CLAUDE.md` §9 task prompt for Task
002 — not performed by this acceptance; PR #92 remains open/draft/not
merged until ChatGPT or the repository owner merges it.**_

_**AR-021 Acceptance Patch (2026-07-05) — AR-021 is now Accepted by
ChatGPT.** ChatGPT reviewed PR #87
([`limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md),
[`task-001-core-module-scaffold.md`](../07-implementation-plan/task-001-core-module-scaffold.md))
and **accepted it on 2026-07-05.** AR-021's table row above moves from
"Proposed for ChatGPT review — NOT YET ACCEPTED" to **"Accepted."**
**The limited, core-only, zero-UI implementation gate is accepted and
opens once PR #87 is merged into `Shopify-connector`; it does not open
before that merge.** **AR-018's criterion 5 is confirmed for this
limited core gate only** — the `defect-pattern-log.md` DP-003/004/006
"unsupported assumption / weak research" occurrence-counter row's
recorded evidence-consistency gate satisfies the prevention-rule
requirement for this gate; this confirmation does not apply
project-wide and does not waive future evidence requirements for later
gates (product/customer/sale, inventory, fulfillment, UI,
credentials/API). **Task 001 — Core Module Scaffold — is authorized as
the only implementation task, starting only after PR #87 is merged.**
**No second task is authorized.** **No code, module, Python, XML,
manifest, security CSV, test, or CI file is created by this acceptance
or by PR #87.** **Implementation itself has not started in this PR.**
No credentials, external API calls, operator-facing UI, or
product/customer/order/inventory/fulfillment domain logic is authorized
by this acceptance. DEC-003 through DEC-020 remain unchanged;
`../04-decisions/README.md` remains unchanged; `defect-pattern-log.md`
is not edited by this acceptance — the criterion-5 confirmation remains
scoped to the limited core gate only, as recorded here and in the gate
document. **The next step is Task 001's own coding PR (the
`shopify_connector_core` module scaffold implementation) — not
performed by this acceptance; PR #87 remains open/draft/not merged
until ChatGPT or the repository owner merges it.**_

_**AR-022 Acceptance Patch (2026-07-06) — AR-022 is now Accepted by
ChatGPT.** ChatGPT reviewed PR #90
([`odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md),
[`mbq-04-credential-persistence-decision-proposal.md`](../03-architecture/mbq-04-credential-persistence-decision-proposal.md))
and, after one REVISE round (2026-07-05, narrowing two absolute
evidence claims to their Community/core-scoped form — see the row
above), **accepted it on 2026-07-06.** AR-022's table row above moves
from "Proposed for ChatGPT review" to **"Accepted."** **The accepted
evidence conclusion:** no official Odoo 19 Community/core field-level
or ORM encryption-at-rest mechanism was found in the official
docs/source reviewed; every real official Odoo credential-field
example uses plain `Char`/`Text` storage with `groups=` access control
and no field-level encryption; UI masking (`password` view attribute)
is not encryption; access control (`groups=`/`ir.model.access`/
`ir.rule`) is not encryption; `sudo()`/superuser mode bypasses
field-level `groups`; Odoo's corporate "Odoo Cloud" AES-256 statement
is infrastructure/platform-level, not field-level ORM encryption, and
its exact Odoo Online/Odoo.sh/on-premise applicability remains a
hosting-scope question unless separately sourced. **Option B is
accepted as the Phase 1/MVP credential-persistence posture** — a
dedicated Odoo-managed credential field or tightly coupled field set,
plain storage using standard Odoo field/access controls, restricted
with a connector admin-equivalent `groups=`, view-level password
masking wherever exposed, and a mandatory no-logging/redaction rule;
no claim of field-level encryption; no claim that Odoo.sh/on-premise
shares the same infrastructure-encryption posture unless separately
sourced. **Options D/E are deferred, not rejected forever**, as a
possible future stronger-posture research/design path. **MBQ-04 is now
Partially resolved** in
[`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
(register-impact wording applied by this same acceptance patch, MBQ-04
row only — no other row touched): evidence blocker resolved for the
official Community/core Odoo 19 sources reviewed; Option B accepted at
posture level; exact model name, field name/type, access group, audit
metadata, rotation/revocation behavior, test-connection behavior,
redaction implementation, and rollback behavior remain open
implementation-planning details. **No code, module, Python, XML,
manifest, security CSV, test, or CI file is created by this
acceptance or by PR #90. No credential model, field, API client, setup
wizard, test-connection mechanism, webhook, controller, cron, UI, or
domain module is created.** DEC-003 through DEC-020 remain unchanged;
`../04-decisions/README.md` remains unchanged; `defect-pattern-log.md`
remains unchanged. **The next step is a separate, future
implementation-planning task naming the exact credential
model/field/access-group/redaction/rotation/test-connection/rollback
details, written to the `CLAUDE.md` §9 template — not performed by
this acceptance, and not implementation; PR #90 remains open/draft/not
merged until ChatGPT or the repository owner merges it.**_

_**AR-023 Acceptance Patch (2026-07-06) — AR-023 is now Accepted by
ChatGPT.** ChatGPT reviewed PR #91
([`ui-ux-final-design-spec.md`](../02-product/ui-ux-final-design-spec.md),
[`screen-inventory-and-navigation-map.md`](../02-product/screen-inventory-and-navigation-map.md),
[`mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md),
[`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md),
[`ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md))
and **accepted it on 2026-07-06, at design-specification level.**
AR-023's table row above moves from (not yet logged) to **"Accepted."**
**The UI/UX Final Design Specification package is accepted at
design-specification level; the Premium Simplicity Standard is accepted
as the project's UI/UX quality bar (clarity, confidence, polish,
guidance, recovery — never more screens/colors/charts/complexity); the
screen inventory/navigation map is accepted as the design-level screen
map; the MVP user flows/state models are accepted as the design-level
flow map; the UI/UX design-review checklist is accepted as the review
checklist for future UI implementation review; the UI/UX implementation
task map is accepted as planning guidance only, not task authorization.**
**The 7±2 visible field budget, the one-primary-action discipline, and
the 10-second dashboard rule remain proposal-level design disciplines,
not hard implementation gates, unless a later, separate ChatGPT act
promotes them.** **No UI implementation gate is opened by this
acceptance. No code, XML, view, menu, action, wizard, field, model,
credential, API client, test-connection, webhook, controller, cron, or
domain module is authorized. Task 002 is not started.** DEC-003 through
DEC-020 remain unchanged; `../04-decisions/README.md` remains unchanged;
`defect-pattern-log.md` remains unchanged; `master-blueprint-open-questions.md`
remains untouched. Exact XML IDs remain MBQ-03; exact final copy remains
MBQ-22; exact access rows remain MBQ-44 residual; credential
implementation detail remains the future MBQ-04 implementation-planning
task. **The next step remains the MBQ-04 credential
implementation-planning task or a separate, explicit ChatGPT UI
implementation-gate-opening decision — neither performed by this
acceptance; PR #91 remains open/draft/not merged until ChatGPT or the
repository owner merges it.**_

_**AR-021 proposed (2026-07-05) — Limited core implementation gate.**
Prepared after AR-020's acceptance patch (below) named the separate,
explicit ChatGPT acts still outstanding: criterion-5 confirmation, the
limited core-only gate-opening act, and authorizing the first
`CLAUDE.md` §9 task — the same acts AR-018's own criterion table
(criteria 3 and 5) left unmet. This entry, together with
[`limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md)
and
[`task-001-core-module-scaffold.md`](../07-implementation-plan/task-001-core-module-scaffold.md),
proposes all three in one package: **(1)** confirms AR-018's criterion-5
ambiguity — the `defect-pattern-log.md` DP-003/004/006 "unsupported
assumption / weak research" occurrence-counter row's recorded
evidence-consistency gate is confirmed to satisfy the prevention-rule
requirement, **for this limited core gate only, not project-wide**;
**(2)** opens only the limited, core-only, zero-UI implementation gate if
accepted — `shopify_connector_core` scaffold, the six AR-019-accepted
core models, groups/access CSV, core constraints/indexes, core tests;
explicitly excludes credentials, external API calls, webhooks, setup
wizard, test connection, domain logic, dashboard, sync center, and
error-center UI; **(3)** authorizes exactly one implementation task, Task
001. **No code, module, Python, XML, manifest, security CSV, test, or CI
file is created by this entry or its companion documents. Implementation
itself has not started.** AR-002 through AR-020 are unchanged by this
entry._

_**AR-020 Acceptance Patch (2026-07-05) — AR-020 is now Accepted by
ChatGPT, at planning-closure level only.** ChatGPT reviewed the proposed
[`final-mbq-closure-plan.md`](../07-implementation-plan/final-mbq-closure-plan.md)
and **accepted it on 2026-07-05.** AR-020's table row above moves from
"Proposed for ChatGPT review — NOT YET ACCEPTED" to **"Accepted."** **The
Final MBQ Closure Plan is accepted at planning-closure level:** all 50
remaining MBQ rows are closed or explicitly scoped (2 resolved — MBQ-29,
MBQ-35; 27 partially resolved with named task-spec residuals; 17 descoped
from MVP / the first gate; 4 accepted-open risks with containment), and
**zero MBQ rows remain blocking the limited, core-only, zero-UI
implementation gate.** This acceptance applies the plan's §7 register
wording to
[`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
(exactly the 50 reviewed rows, plus a top acceptance-patch note; no other
row touched). Per `CLAUDE.md` §10, this acceptance **does not authorize
implementation**; **the implementation gate remains closed;
implementation remains blocked; no implementation task is created; no
code, module, view, controller, security file, manifest, test, or CI file
is created**; DEC-003 through DEC-020 remain unchanged;
`../04-decisions/README.md` remains unchanged. **The next step is a
separate, explicit ChatGPT gate-opening act — not automatic
implementation**: (1) confirm AR-018's criterion-5 reading
(DP-003/004/006 prevention-rule status), (2) open the limited core gate
(`shopify_connector_core` only, zero operator-facing UI, no webhooks, no
external API calls, no credential persistence), (3) authorize the first
implementation task written to the `CLAUDE.md` §9 template — none
performed by this acceptance._

_**AR-020 proposed (2026-07-05) — Final MBQ closure plan, history,
superseded by the acceptance patch above.** After PR #85 merged into
`Shopify-connector` (merge commit `2e6842b`), the final MBQ closure plan
([`../07-implementation-plan/final-mbq-closure-plan.md`](../07-implementation-plan/final-mbq-closure-plan.md))
was prepared and proposed via a draft PR. It reviews **all 50 MBQ rows
not fully closed after AR-019** and proposes, for each, one explicit
final status (resolved / partially resolved with named residual /
descoped from MVP or first gate / accepted-open with containment), with
official-doc verification performed this session for MBQ-09, MBQ-14,
MBQ-24, and MBQ-27 (Shopify/Odoo official sources, accessed 2026-07-05,
cited in the plan). **Zero rows remain classified as blocking a limited,
core-only, zero-UI implementation gate** (plan §6); rows that could not
be honestly resolved (MBQ-27 mechanism, MBQ-04, MBQ-05, MBQ-55, MBQ-56)
block their affected later slice only. **No code is created. No
implementation task is created. The MBQ register
(`../03-architecture/master-blueprint-open-questions.md`) is NOT edited —
plan §7 carries the proposed register wording, to be applied only by a
future acceptance patch. The implementation gate remains closed;
implementation remains blocked; this proposal is not a gate-opening act
and does not pre-empt one.** Fable's recommendation in the plan (§8/§11):
**ready for a separate, limited, core-only implementation-gate opening
after ChatGPT accepts this closure package**, with two named pre-gate
ChatGPT confirmations (criterion 5's DP-003/004/006 reading; the explicit
gate act itself). AR-002 through AR-019 are unchanged by this entry._

_**AR-019 Acceptance Patch (2026-07-05) — AR-019 is now Accepted by
ChatGPT, at implementation-planning level only.** After the revision below
corrected the five schema defects ChatGPT's REVISE identified, **ChatGPT
accepted the revised
[`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md)
on 2026-07-05.** AR-019's table row above moves from "Proposed for ChatGPT
review — NOT YET ACCEPTED" to **"Accepted."** **Core naming/schema planning
is accepted at implementation-planning level.** This acceptance applies the
document's own §14 register-impact wording to
[`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
for exactly **MBQ-01, MBQ-02, MBQ-07, MBQ-16, MBQ-19, MBQ-20, MBQ-21, and
the MBQ-45/MBQ-62 residuals (each now Resolved)** and **MBQ-44 (Partially
resolved, planned CSV row shapes only)** — **MBQ-04 is recorded as Not
resolved, explicitly and fully descoped for slice 1**, not partially
resolved. **No other MBQ row is changed.** Per `CLAUDE.md` §10, this
acceptance **does not authorize implementation**; **does not open the
implementation gate**; **implementation remains blocked**; **no
implementation task is created**; **no code, module, view, controller,
security file, manifest, test, or CI file is created**; DEC-003 through
DEC-020 remain unchanged; `../04-decisions/README.md` remains unchanged.
Recommended next: a separate, explicit ChatGPT implementation-gate-opening
act, and the domain-scope MBQ rows this pass does not touch — neither is
performed by this acceptance._

_**AR-019 revision (2026-07-05) — corrected after ChatGPT REVISE, still not
accepted.** ChatGPT reviewed the proposed core naming/schema planning
document (PR #85) and returned **REVISE**: direction accepted, but the
schema needed correction before acceptance. Applied: **removed
`shopify.connector.store.credential` entirely** — no credential model,
credential metadata model, or secret field of any kind is proposed for the
first slice; MBQ-04 is now **"proposed not resolved / explicitly, fully
descoped for slice 1,"** not "partially resolved"; **fixed the
`store.settings_id`/One2many-named-singular contradiction** by removing the
reverse field from `store` and relying on `store.settings.store_id` as the
sole link; **changed `job.log.job_id` from `ondelete='cascade'` to
`ondelete='restrict'`** so a job's log/audit history can never be silently
cascade-deleted through its parent; **gave `job_type` two core-owned
starting values** (`core_readiness_check`, `core_manual_maintenance`) so the
required Selection is never contradictorily empty before any domain module
installs; **made the serialization guard DB-backed and race-safe** — a new
`operation_scope_key` field, populated only while a job is non-terminal and
cleared to `NULL` on reaching a terminal state, under a unique constraint on
`(store_id, operation_scope_key)`, kept explicitly distinct from
`idempotency_key`; and **removed the `mail.thread`/tracking commitment**
for settings-change history, leaving that choice to a future implementation
task's own manifest dependency decision. The proposed model count moves
from seven to **six**. **AR-019 remains Proposed for ChatGPT review — NOT
YET ACCEPTED.** No DEC-003 through DEC-020 file changed; no MBQ row in
`master-blueprint-open-questions.md` changed; `../04-decisions/README.md`
unchanged; no code, module, or implementation task created; the
implementation gate remains closed; implementation remains blocked._

_**DEC-015 Acceptance Patch (2026-07-03) — AR-012 is now Accepted by
ChatGPT.** After Fable reviewed PR #74 and returned **REVISE** (finding
C1 — corrected the earlier over-claim that `product.product.free_qty`
and `stock.quant.available_quantity` are equivalent; finding C2 —
corrected the earlier silent treatment of "event-driven enqueue" as a
Part A job-source value, routing the classification question to new
MBQ-62; plus seven minor findings, all fixed on the same PR) and a
same-PR consistency patch aligning the new-MBQ summary wording, **ChatGPT
formally accepted**
[`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
on **2026-07-03**. AR-012's table row above moves from "Proposed for
ChatGPT review" to **"Accepted by ChatGPT"** / **"Accepted."** This
acceptance accepts, at blueprint level: **Master Blueprint Part C**
(inventory and fulfillment domain blueprints, in full); the **corrected
C1 posture** — `product.product.free_qty` and
`stock.quant.available_quantity` are verified candidate sources but not
equivalent, **MBQ-32 stays partially resolved**, final source-selection/
aggregation mechanism remains open; the **corrected C2 posture** —
"event-driven enqueue" is not a Part A job-source enum value, **MBQ-62
remains open**; **MBQ-37 and MBQ-39 resolved at fact-verification
level**; **MBQ-32, MBQ-36, MBQ-38, MBQ-40, MBQ-42, and MBQ-43 partially
resolved**; **MBQ-42's accepted widening of `ambiguous match`** (AR-006/
DEC-009: multiple candidates) to also cover a deterministic fulfillment-
location mismatch — accepted at blueprint level only, not implementation
detail. **MBQ-33, MBQ-34, and MBQ-41 remain open** — their recommendations
are noted, not adopted as decisions, by this acceptance. **MBQ-35 remains
carried forward, open, unchanged. MBQ-60 through MBQ-63 remain new and
open** — none resolved by this acceptance. Per `CLAUDE.md` §10, this
acceptance **does not authorize implementation**; DEC-003 through DEC-014
remain unchanged; no code, Odoo module, or implementation plan was
produced; **implementation remains blocked**; **Part D — UI/UX Screen
Design Blueprint — remains not started and remains required before
implementation of any operator-facing screen**; **Part E —
implementation-planning bridge — remains not started.** Recommended
next: **Master Blueprint Part D (UI/UX Screen Design Blueprint)** or
**Part E (implementation-planning bridge)**, per ChatGPT's preference
(neither started)._

_**DEC-016 Acceptance Patch (2026-07-04) — AR-013 is now Accepted by
ChatGPT.** After duplicate-PR reconciliation (a duplicate Sprint D
proposal, PR #75, was confirmed to exist, salvaged for four safe,
additive completeness items, and closed as superseded, not merged), a
competitor screenshot UX benchmark traceability audit (resolving a
ChatGPT concern that Part D's grounding in competitor screenshot evidence
was only transitive, not directly cited), and the Fable Sprint D review
fixes (F1–F7, all documentation-only) were applied on PR #77, **ChatGPT
formally accepted**
[`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)
on **2026-07-04**, confirming PR #77 head commit
`b1f1ac9da3893b0d62fb803f0e588f889f8c1ab5`. AR-013's table row above
moves from "Proposed for ChatGPT review" to **"Accepted by ChatGPT"** /
**"Accepted."** This acceptance accepts, **at screen-design blueprint
level only**: **Master Blueprint Part D** (the UI/UX Screen Design
Blueprint, in full, as a screen-design contract — explicitly **not** a
pixel-level visual-design or final-wireframe-polish approval); **MBQ-53
partially resolved at screen-design blueprint level** — its sibling rows
**MBQ-03, MBQ-22, MBQ-44, MBQ-45, and MBQ-06 remain open**; **MBQ-33,
MBQ-34, MBQ-41, MBQ-35, and MBQ-32 remain open recommendations**, not
decided by this acceptance; **MBQ-60 through MBQ-63 remain open**; **no
new MBQ row is added**. **The competitor screenshot audit is accepted as
sufficient traceability for this blueprint-level acceptance** — the
`sh_shopify_connector` "Daily Queue Activity Tracking" chart idea it
surfaced **remains a deferred premium visualization candidate for a
later pixel-design pass, not adopted into the accepted dashboard card
set**. Per `CLAUDE.md` §10, this acceptance **does not authorize
implementation**; DEC-003 through DEC-015 remain unchanged; no code,
Odoo module, or implementation plan was produced; **implementation
remains blocked**; **Part E — implementation-planning bridge — remains
not started.** PR #75 remains **closed, not merged**; PR #77 remains
**open, draft, not merged**. Recommended next: **Master Blueprint Part
E (implementation-planning bridge)**, or a separate, explicit ChatGPT
decision on the open recommendations MBQ-33/34/41/45/06/35, then
**implementation only after a separate ChatGPT gate**._

_**DEC-017 Acceptance Patch (2026-07-04) — AR-014 is now Accepted by
ChatGPT.** After ChatGPT reviewed PR #80 ("Propose Master Blueprint Part E
implementation-planning bridge," head commit
`e4e1fd5b2d2c4fafdaa57c4b025d5234611b44b6`), **ChatGPT formally accepted**
[`DEC-017`](../04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md)
on **2026-07-04**. AR-014's table row above moves from "Not yet reviewed"
to **"Accepted"** / **"Accepted."** This acceptance accepts, as
**documentation-only planning guidance**: **Master Blueprint Part E**
(the implementation-planning bridge, in full — MBQ decision plan,
proposed implementation sequence, first-safe-slice recommendation,
test/rollback strategy, no-code-to-code gate checklist); **MBQ-64
partially resolved at fact-verification level** (Shopify `MoneyBag`/
`shopMoney`/`presentmentMoney` and Odoo's single `sale.order.currency_id`
accepted as verified facts; the design/selection mechanism remains open);
**MBQ-65 resolved at fact-verification level only** (`PRODUCTS_CREATE`/
`PRODUCTS_UPDATE`/`PRODUCTS_DELETE` accepted as verified; the payload/
subscription/scope residual remains open). **No ChatGPT-batch MBQ item
(MBQ-06/08/17/33/34/41/45/52/54/60/62) is decided by this acceptance** —
accepting the plan to decide them is not the same act as deciding them.
**No other MBQ row is touched.** Per `CLAUDE.md` §10, this acceptance
**does not authorize implementation**; DEC-003 through DEC-016 remain
unchanged; no code, Odoo module, or implementation plan was produced;
**implementation remains blocked; the implementation gate remains
closed.** Recommended next: the MBQ decision plan's own ChatGPT-batch
decisions, then a separate, explicit ChatGPT implementation-gate-opening
act._

_**Proposed MBQ Decision Batch 1 (2026-07-04) — AR-015 added, Proposed for
ChatGPT review; NOT accepted (history).** Prepared after DEC-017 was
confirmed accepted (2026-07-04) and PR #80 confirmed merged into
`Shopify-connector` (merge commit
`403d17fc16c6854b0bd9f3ce3161ff61cc0e1570`). This session proposed
[`DEC-018`](../04-decisions/DEC-018-mbq-decision-batch-1.md) — a controlled
first batch of the Part E MBQ decision plan's own "ChatGPT batch" (§4),
covering MBQ-06/08/17/33/34/41/45/52/54/60 with evidence, options,
recommended decisions, risk, and drafted (not applied) register-impact
wording, and explicitly declining to force MBQ-62 into that same batch
(recommended split into its own follow-up DEC instead). **Superseded by the
acceptance note below.**_

_**DEC-018 Acceptance Patch (2026-07-04) — AR-015 is now Accepted by
ChatGPT.** ChatGPT reviewed the proposed
[`DEC-018`](../04-decisions/DEC-018-mbq-decision-batch-1.md) packet and
**formally accepted DEC-018 on 2026-07-04 — Batch 1 except MBQ-62.**
AR-015's table row above moves from "Proposed for ChatGPT review" to
**"Accepted by ChatGPT"** / **"Accepted."** This acceptance accepts, as
**documentation-only decisions**: **MBQ-06** (readiness-check
essential-vs-nice-to-have split), **MBQ-08** (disconnect data-retention
posture), **MBQ-17** (reconciliation posture only, constants remain
implementation planning), **MBQ-33** (first-push guard granularity),
**MBQ-34** (review-then-apply as the Phase 1 ongoing-apply-mode default),
**MBQ-41** (global/per-store notification-UI default), **MBQ-45**
(roles→groups 1:1 mapping and one shared role-gated surface), **MBQ-52**
(API-version pinning/upgrade policy only), **MBQ-54** (disable-not-uninstall
posture only), and **MBQ-60** (`stock_delivery`/`delivery` dependency
required for fulfillment tracking write-back). Each of these ten rows'
register-impact wording (DEC-018 §5) has been **applied** to
`master-blueprint-open-questions.md`, dated **2026-07-04**; each still
carries its own named implementation-planning residual (exact copy, XML
IDs, schemas, constants, mechanics — see each row). **MBQ-62 is explicitly
NOT decided** — ChatGPT accepted DEC-018's recommendation to split it into
its own dedicated follow-up decision record instead of forcing a mapping
onto any of the six fixed Part A §D.2 job-source values; only a short
split-note citation was added to its register row, its substance is
unchanged. **MBQ-64 and MBQ-65 remain untouched**, reserved for a separate
currency/webhook residual decision sprint. **No other MBQ row is resolved,
re-routed, or silently changed by this acceptance.** Per `CLAUDE.md` §10,
this acceptance **does not authorize implementation**; DEC-003 through
DEC-017 remain unchanged; no code, Odoo module, or implementation plan was
produced; **implementation remains blocked; the implementation gate remains
closed.** Recommended next: a dedicated follow-up DEC for MBQ-62, then the
separate MBQ-64/MBQ-65 currency/webhook residual decision sprint — neither
is implementation._

_**MBQ-62 Decision Proposal (2026-07-04) — AR-016 added, Proposed for
ChatGPT review; NOT accepted.** Prepared after DEC-018 was confirmed
accepted (2026-07-04) and the current branch confirmed based on
`Shopify-connector` at PR #81 merge commit
`31d6732c9558c04bac49f4c84feba3bd5f90dec8`. This session prepared
[`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) — a
dedicated, strict evaluation of MBQ-62's own four candidate answers (add a
seventh job-source value; existing source + trigger-origin metadata; a
separate trigger-origin dimension with no seventh value; defer Odoo-side
event triggers from Phase 1), recommending a seventh value (`odoo_event`)
paired with a required trigger-origin sub-classification, and explicitly
declining a weak mapping onto any of the six existing values. **No MBQ row
is resolved. No implementation started. Implementation gate remains
closed.** DEC-019 and AR-016 are both **Proposed for ChatGPT review — NOT
accepted.**_ **Superseded by the acceptance note below.**

_**DEC-019 Acceptance Patch (2026-07-04) — AR-016 is now Accepted by
ChatGPT.** ChatGPT reviewed
[`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) and
**formally accepted it on 2026-07-04, at decision/semantic-classification
level.** AR-016's table row above moves from "Proposed for ChatGPT review"
to **"Accepted by ChatGPT"** / **"Accepted."** This acceptance accepts, as a
**documentation-only decision**: **Part A §D.2's job-source vocabulary is
extended with a seventh accepted semantic value, `odoo_event`** (a job
enqueued because an Odoo-side business event occurred — not a webhook, not
manual sync, not scheduled sync, not reconciliation, not setup readiness,
not export preview dry run); **every `odoo_event` job must conceptually
carry a trigger-origin sub-classification**, with the accepted
trigger-origin concepts for MBQ-62 being **"inventory stock-change
trigger"** and **"fulfillment picking-validation trigger."** MBQ-62's
register-impact wording (DEC-019 §6) has been **applied** to
`master-blueprint-open-questions.md`, dated **2026-07-04**; it still
carries its own named implementation-planning residual (exact Odoo model
names, field names, Python constants, XML IDs, storage/Selection-field
mechanics, trigger-origin field/model implementation, and MBQ-16
retry-count/backoff constants — see MBQ-62's row). **MBQ-64 and MBQ-65
remain untouched**, reserved for a separate currency/webhook residual
decision sprint. **No other MBQ row is resolved, re-routed, or silently
changed by this acceptance.** Per `CLAUDE.md` §10, this acceptance **does
not authorize implementation**; DEC-003 through DEC-018 remain unchanged;
no code, Odoo module, or implementation plan was produced;
**implementation remains blocked; the implementation gate remains
closed.** Recommended next: the separate MBQ-64/MBQ-65 currency/webhook
residual decision sprint — not implementation._

_**Proposed MBQ-64/MBQ-65 Residual Decisions (2026-07-04) — AR-017 added,
Proposed for ChatGPT review; NOT accepted.** Prepared after DEC-019 was
confirmed accepted (2026-07-04) and PR #82 confirmed merged into
`Shopify-connector` (merge commit
`94e3458e9ff6511f34f9abfe8944b4e0660c02b2`). This session proposed
[`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
— the dedicated currency/webhook residual decision sprint DEC-018 §6
explicitly routed MBQ-64/MBQ-65 to, since DEC-017 had accepted only their
underlying platform facts, not a design/selection decision. Grounded in
fresh official-doc research (Shopify's "About Shopify Markets" and "About
webhooks" pages, a re-verified `Order.presentmentCurrencyCode` field
description, and the official `odoo/odoo` 19.0 `sale_order.py` source),
DEC-020 proposes: for **MBQ-64**, shop currency drives
`sale.order.currency_id` in Phase 1, with presentment-currency evidence
captured for audit only and any shop/presentment divergence routed through
the existing `financial total mismatch` class, never silently accepted;
for **MBQ-65**, `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE` are
implemented in Phase 1 as enqueue-only triggers with a mandatory follow-up
authoritative read before any write, never a direct mutation from the
webhook payload. **No MBQ row is resolved by this proposal. No
implementation started. Implementation gate remains closed.** DEC-020 and
AR-017 are both **Proposed for ChatGPT review — NOT accepted.**_
**Superseded in part by the revision note below (MBQ-64 only; MBQ-65
unaffected).**

_**DEC-020 Revision (2026-07-04) — MBQ-64 corrected after ChatGPT REVISE;
AR-017 remains Proposed for ChatGPT review, NOT accepted.** ChatGPT
reviewed the proposed
[`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
and returned **REVISE for MBQ-64** — the original posture above (shop
currency for every Phase 1 order; a shop/presentment divergence caught
only if the numeric total-check guard happened to fail) was found **not
safe enough**, since a divergent order's shop-currency total is itself a
back-converted approximation that could reconcile within tolerance while
still misrepresenting the customer-facing order currency. **MBQ-65 was
found directionally acceptable and was not redesigned.** DEC-020 §4/§5 are
corrected: **Phase 1 automatic order import is now same-currency only** —
for orders where `Order.presentmentCurrencyCode == Order.currencyCode`,
`sale.order.currency_id` follows the connector's normal configured
pricelist/company currency, aligned to Shopify shop currency; for orders
where the two differ, the connector **never** silently creates a normal
Odoo sale order in shop currency, regardless of the total-check guard's
outcome — the job is blocked from automatic SO creation and routed to
manual review / treated as an explicit unsupported-scope case **before**
SO creation. Both `shopMoney`/`presentmentMoney` and
`presentmentCurrencyCode` remain captured as audit evidence in every case.
`financial total mismatch` is now evaluated explicitly as a candidate
classification for the blocked case rather than forced onto it — DEC-020
§5 explains why forcing it without a named, deliberate broadening would
risk the same loose-routing pattern DEC-014's Fable review (finding B1)
already flagged once; the **exact final error-class/sub-reason mapping**
for a blocked divergent-currency order **remains implementation
planning**, while the **decision posture itself — no silent SO creation
for divergent currencies — is fixed now**. MBQ-56's own tolerance
mechanics remain open, unchanged, and are explicitly not relied upon as
the mechanism that catches a currency-model divergence. **No MBQ row is
resolved by this revision. No implementation started. Implementation gate
remains closed.** DEC-020 and AR-017 remain **Proposed for ChatGPT
review — NOT accepted.**_ **Superseded by the acceptance note below.**

_**DEC-020 Acceptance Patch (2026-07-04) — AR-017 is now Accepted by
ChatGPT.** ChatGPT reviewed the revised
[`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
and **formally accepted it on 2026-07-04, at decision/posture level for
both MBQ-64 and MBQ-65.** AR-017's table row above moves from "Proposed
for ChatGPT review" to **"Accepted by ChatGPT"** / **"Accepted."** This
acceptance accepts, as **documentation-only decisions**: for **MBQ-64**,
Phase 1 automatic order import is same-currency only
(`Order.presentmentCurrencyCode == Order.currencyCode`); for a divergent
order, the connector never silently creates a normal Odoo sale order in
shop currency — the job is blocked from automatic SO creation and routed
to manual review / treated as an explicit unsupported-scope case before SO
creation, independent of the total-check guard's outcome; both
`shopMoney`/`presentmentMoney` and `presentmentCurrencyCode` are captured
as audit evidence in every case; presentment-currency Odoo orders remain
non-MVP. For **MBQ-65**, `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/
`PRODUCTS_DELETE` are implemented in Phase 1 as enqueue-only triggers,
never a direct write, each job performing a follow-up authoritative read
before any create/update/delete, with DEC-005 reconciliation as the
required backstop; `PRODUCTS_DELETE` never directly deletes/archives the
bound Odoo product. Both rows' register-impact wording (DEC-020 §9) has
been **applied** to `master-blueprint-open-questions.md`, dated
**2026-07-04**; each still carries its own named implementation-planning
residual — **MBQ-56's own tolerance mechanics** (unaffected, still open),
**the exact final error-class/sub-reason mapping and enforcement
mechanism** for a blocked MBQ-64 divergent-currency order, and **MBQ-65's
exact controller/job/query/subscription mechanics** and the still-
unconfirmed variant-count payload-truncation claim. **No other MBQ row is
resolved, re-routed, or silently changed by this acceptance; MBQ-62's
accepted state (DEC-019) is not reopened or weakened.** Per `CLAUDE.md`
§10, this acceptance **does not authorize implementation**; DEC-003
through DEC-019 remain unchanged; no code, Odoo module, or implementation
plan was produced; **implementation remains blocked; the implementation
gate remains closed.** Recommended next: a gate-readiness audit against
`master-blueprint.md`'s five gate-opening criteria before any
implementation — not implementation itself._

_**Implementation Gate Readiness Audit (2026-07-05) — AR-018 added,
Proposed for ChatGPT review.** Prepared after DEC-020 was confirmed
accepted (2026-07-04) and PR #83 confirmed merged into `Shopify-connector`
(merge commit `b27f842425043e6320d8e168a1208345f6fcab12`). This session
prepared
[`implementation-gate-readiness-audit.md`](./implementation-gate-readiness-audit.md)
— a strict, row-by-row readiness check against `master-blueprint.md`'s
five gate-opening criteria, classifying all 65 rows of
`master-blueprint-open-questions.md` into whether each blocks a first
`shopify_connector_core`-only implementation slice, a later domain slice,
release readiness only, or nothing at all. Found **zero of five gate
criteria unambiguously satisfied project-wide**, and eleven rows
(MBQ-01/02/04/07/16/19/20/21/44/45/62) that would block even the narrowest
possible first slice. **This is an audit only — it resolves no MBQ row, it
does not open the implementation gate, it creates no implementation task,
and it authorizes no code.** Verdict: **READY ONLY FOR A VERY LIMITED
IMPLEMENTATION-PLANNING SPRINT, NOT CODE.** AR-018 is **Proposed for
ChatGPT review**, not accepted._ **Superseded by the acceptance note below.**

_**Implementation Gate Readiness Audit Acceptance Patch (2026-07-05) —
AR-018 is now Accepted by ChatGPT.** ChatGPT reviewed
[`implementation-gate-readiness-audit.md`](./implementation-gate-readiness-audit.md)
and **formally accepted it on 2026-07-05.** AR-018's table row above moves
from "Proposed for ChatGPT review" to **"Accepted by ChatGPT"** /
**"Accepted."** This acceptance accepts, as a **documentation-only
finding**: the audit's verdict, **READY ONLY FOR A VERY LIMITED
IMPLEMENTATION-PLANNING SPRINT, NOT CODE**, unchanged; the audit's
Criterion-2/3/4 findings (eleven rows — MBQ-01/02/04/07/16/19/20/21/44/45/
62 — still block even the narrowest core-substrate-only first slice; the
explicit gate-opening act has not occurred; no implementation task has
been written to the CLAUDE.md §9 template); and the audit's own strict,
conservative reading of **Criterion 1 as non-blocking** for this scope —
ChatGPT confirms Criterion 1 passes for the core-substrate-only scope this
audit and its recommended next session both target, and that the
**decisive** blockers remain Criteria 2, 3, and 4, not Criterion 1.
**Accepted next session:** a single, documentation-only naming/
core-schema implementation-planning artifact addressing MBQ-01/02/04/07/
16/19/20/21/44/45(residual)/62(residual), exactly as the audit's own §6/§7
recommended — **not code, and not the gate-opening act.** **No MBQ row
status is changed by this acceptance. No implementation task is created.
No DEC-003 through DEC-020 is changed.** Per `CLAUDE.md` §10, this
acceptance **does not authorize implementation**; **implementation remains
blocked; the implementation gate remains closed.** Recommended next: the
documentation-only naming/core-schema implementation-planning pass named
above — not implementation, not a gate-opening act._

_AR-001 is a governance/process decision (not a product-architecture choice);
it is recorded here because it concerns the canonical foundation all later
architecture work builds on._

_**UX / Operator-Flow Decision Preparation sprint (2026-07-02) — AR-009 added, Proposed
for ChatGPT review (history).** Prepared after PR #67 merged into `Shopify-connector`
(merge commit `8798a2454924fd241c8052e2556ea8bca21a7c20`) and after all of AR-002
through AR-008 were confirmed accepted. AR-009 is **not** a new platform-fact/
architecture-option question in the AR-002…AR-008 sense — it is the UX/operator-flow
synthesis of those already-accepted decisions, proposed via
[`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md). **Superseded by the
acceptance note below.**_

_**DEC-012 Acceptance Patch (2026-07-03) — AR-009 is now Accepted by ChatGPT.**
ChatGPT formally accepted
[`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md) on **2026-07-03**
(after PR #68 merged into `Shopify-connector`, merge commit
`7d01617fdd0fd70d6a1d83d57918b045296550ac`, following Fable's review — **ACCEPT WITH
MINOR CHANGES** — and the Fable fix-up applied before merge). AR-009's table row moved
from "Proposed for ChatGPT review" to "Accepted by ChatGPT." Per `CLAUDE.md` §10, this
does not authorize implementation; DEC-003 through DEC-011 are unchanged; the
**Master Blueprint** is the next step, and a separate ChatGPT implementation-gate
approval remains required before any implementation._

_**AR-002 … AR-008** were seeded in **Research Sprint B** as **evidence-pending
research questions only** — every one has Review decision **"Not decided"** and
Status **"Evidence pending."** They are **not proposals under active review and
not decisions**; they exist so the open architecture questions implied by the
Tier-1 Shopify/Odoo baselines are tracked and not forgotten. No design may be
accepted while its **Evidence required** is missing, and any acceptance must
route through this log and (when accepted) an ADR in `../04-decisions/`. All
architecture work remains gated until research is sufficient and ChatGPT
approves (see `CLAUDE.md` §4–§5; backlog item RB-14)._

_**Research Sprint C competitor-evidence note (2026-06-30) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** The Sprint C competitor deep
dives, feature matrix, patterns, gaps, and avoid-list now supply **competitor
evidence** that informs (does not resolve) several AR rows. For the record only:
**AR-002 (API)** — every studied connector adopts/positions on **GraphQL**
(VentorTech migrated REST→GraphQL in v2.0.0, Jan 2026), consistent with Tier-1;
the custom-app/distribution choice stays open. **AR-003 (sync orchestration)** —
the market pattern is **webhooks + cron/scheduled + manual** with staging/queues
common; **VentorTech runs on the OCA `queue_job` async queue** (a real-world data
point for the queue dependency question), while cron-only/webhook-less
(ecommerce_shopify) and webhook-only designs risk drift. **AR-005 (mapping/dedup)**
— competitors bind via **SKU/barcode (products) + email (customers) + Shopify-ID
write-back**; none clearly documents bound-record-deletion handling. **AR-006
(error/retry/idempotency)** — **VentorTech ships GraphQL `@idempotent` directives
(Shopify 2026-04) + automatic retry**; others recover manually — corroborating the
idempotency+retry direction; **no competitor describes rate-limit/cost-aware
throttling** (whitespace). **AR-007 (inventory)** — multi-location mapping is
demonstrated (Emipro/VentorTech); single-location (Webkul) and manual
stock-adjustment-on-import (Emipro) are anti-patterns to avoid. **AR-008
(fulfillment)** — FulfillmentOrder-era flows + tracking write-back + multi-package
(Emipro Put-in-Pack) are the norm. **No AR row is decided, accepted, or
re-litigated here.** Avoid-list items tagged "Arch review: YES" are seeded against
these rows and become formal `rejected-approaches-log.md` entries **only after
ChatGPT review**. Evidence: `../01-research/competitor-deep-dives.md`,
`../01-research/gaps-opportunities.md`, `../01-research/avoid-list.md`._

_**Research/Product Sprint D non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** The Sprint D canonical feature
taxonomy (`../02-product/feature-taxonomy.md`) and capability evidence map
(`../02-product/capability-evidence-map.md`) now provide **capability-level
inputs** to the open architecture questions. For the record only, each AR row has
named dependent capabilities: **AR-002 (API/distribution/bulk)** — connection
auth, product/variant/backfill sync, bulk ops, App-Store readiness (distribution
public-vs-custom still open); **AR-003 (sync orchestration/queue)** — webhooks +
reconciliation + scheduled + manual, queue with per-record isolation, auto-workflow,
resumable jobs (`ir.cron` vs OCA `queue_job` still open); **AR-004 (module
boundaries)** — domain-isolated config, mapping/metafield extensibility, feature
flags, transport abstraction (**no module names/boundaries defined**); **AR-005
(binding/dedup)** — Shopify-GID binding model, documented dedup keys, per-store
keys, multi-key customer matching (`ir.model.data` reuse vs dedicated model, and
deleted-binding handling, still open); **AR-006 (error/retry/idempotency)** — retry
classification, automatic retry, idempotency keys, recovery-first error center,
reconciliation; **AR-007 (inventory)** — quantity sync (write `available`/`on_hand`
only), quantity-field choice, multi-location, auto-apply, BoM stock; **AR-008
(fulfillment)** — FulfillmentOrder-based fulfillment, multi-package/location. The
taxonomy classifies these as **inputs/candidates only** and routes them here; **no
AR row is decided, accepted, proposed for active review, or re-litigated.** All
remain "Not decided / Evidence pending" pending sufficient research + ChatGPT
approval (`CLAUDE.md` §4–§5; RB-14). See also DP-005 (`defect-pattern-log.md`) — the
prevention rule that a taxonomy classification is an input, not a decision._

_**Product Sprint E non-decision note (2026-07-01) — NOT decisions; AR rows remain
"Not decided / Evidence pending".** The Sprint E product vision
(`../02-product/product-vision.md`) and setup/UX principles
(`../02-product/setup-ux-principles.md`) now provide **product-intent inputs** to the
open architecture questions — product direction only, never a design choice. For the
record only: **AR-002 (API/distribution)** — the vision states OAuth-first as a strong
but **conditional** direction (mandatory only if public/App-Store distribution is
chosen) and keeps **distribution (public vs custom) and REST/GraphQL/hybrid OPEN**;
**AR-003 (sync orchestration/queue)** — product intent requires webhooks + first-class
reconciliation + scheduled + manual together with out-of-band, resumable processing,
but the **`ir.cron` vs OCA `queue_job` choice and Odoo-Online feasibility stay OPEN**;
**AR-004 (module boundaries)** — a layered, isolated addon family with feature flags
is the direction, **no boundaries/names defined**; **AR-005 (binding/dedup)** —
documented binding + dedup keys and deleted-binding handling are required, **the data
model (`ir.model.data` reuse vs dedicated) stays OPEN**; **AR-006
(error/retry/idempotency)** — idempotency-by-default + recovery-first error center +
retry classification are product non-negotiables, **the error/retry taxonomy and
mechanism stay OPEN**; **AR-007 (inventory)** — multi-location, write
`available`/`on_hand` only, controlled apply (auto-apply is an improvement inference,
DP-006), **design OPEN**; **AR-008 (fulfilment)** — FulfillmentOrder-based +
multi-package/location, **design OPEN**. The vision routes these here as **inputs
only** and re-litigates nothing; **no AR row is decided, accepted, proposed for active
review, or re-litigated.** All remain "Not decided / Evidence pending" pending
sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). See DP-006's
evidence-consistency gate in `defect-pattern-log.md`._

_**Product Sprint F non-decision note (2026-07-01) — NOT decisions; AR rows remain "Not
decided / Evidence pending".** The Sprint F MVP scope proposal (`../02-product/mvp-scope.md`),
non-MVP boundaries (`../02-product/non-mvp-and-later-phases.md`), and user stories
(`../02-product/user-stories.md`) now provide **capability-scope inputs** to the open
architecture questions — MVP *intent/requirements* only, never a design choice. The MVP
proposal commits the **what**, not the **how**, and explicitly maps each
architecture-sensitive capability to its AR row as *Architecture-dependent — must be
resolved in RB-14 before implementation* (`mvp-scope.md` "Architecture-dependent MVP
items"). For the record only: **AR-002 (API/distribution/bulk/App-Store)** — depends
C-CONN-01 (auth style), C-PROD-01/02, C-VAR-01, C-ORD-02, C-JOB-05/06, C-DOCS-04
(distribution public-vs-custom still open; REST/GraphQL/hybrid open); **AR-003 (sync
orchestration/queue)** — depends C-SYNC-01/03/04/06, C-JOB-01/07, C-ORD-01/04, C-DASH
enqueue (`ir.cron` vs OCA `queue_job` still open; Odoo-Online feasibility open); **AR-004
(module boundaries/config/feature flags)** — depends C-MAP-03, C-MULTI-04, feature-flag
visibility (**no module names/boundaries defined**); **AR-005 (binding/dedup)** — depends
C-MAP-01/02, C-CUST-03, C-PROD-01, C-MULTI-01 multi-store-safe keys (`ir.model.data`
reuse vs dedicated model, and deleted-binding handling, still open); **AR-006
(error/retry/idempotency)** — depends C-JOB-02/03/04, C-OBS-03, C-DASH-04, C-SYNC-06
(taxonomy, idempotency mechanism, reconciliation cadence open); **AR-007 (inventory)** —
depends C-INV-01/02/03/04 (fields, multi-location, **auto-apply-vs-review** open — DP-006);
**AR-008 (fulfilment)** — depends C-FUL-01/02 (FulfillmentOrder, multi-package/location
open). The proposal routes these here as **inputs only** and re-litigates nothing; **no
AR row is decided, accepted, proposed for active review, or re-litigated.** All remain
"Not decided / Evidence pending" pending sufficient research + ChatGPT approval
(`CLAUDE.md` §4–§5; RB-14). See DP-006's evidence-consistency gate in
`defect-pattern-log.md`._

_**Product Sprint G non-decision note (2026-07-01) — NOT an architecture decision; AR rows
remain "Not decided / Evidence pending".** ChatGPT accepted the **MVP product scope**
baseline in [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md)
(RB-13). **DEC-003 is a product-scope decision, not an architecture decision:** it fixes the
MVP *what* (Option A correctness-core **with controlled bidirectional product onboarding**
— product import **and** controlled export/update; import + inventory/fulfilment write-back;
Domain 9 minimal financial **evidence** only, no accounting automation; refunds/cancellations
deferred; bulk ops **not a user-facing feature**; single-store/single-company with
multi-store-safe keys; P1-primary/P2-secondary) and **feeds AR-002…AR-008 as scope inputs**,
but **decides, accepts, proposes-for-active-review, and re-litigates no AR row.** Specifically
still open: **AR-002** distribution/API strategy — and whether Shopify **Bulk Operations are
required internally** for safe/resumable backfills (an architecture mechanism, not a
product-scope expansion); **AR-003** orchestration/queue framework + Odoo-Online feasibility;
**AR-004** module boundaries/config model; **AR-005** binding/dedup data model + per-store keys
+ deleted-binding handling; **AR-006** error/retry taxonomy + idempotency mechanism +
reconciliation cadence; **AR-007** inventory design incl. **apply mode (auto-apply vs
review)**; **AR-008** fulfilment design. Additionally, the **Domain 9 draft-artifact
exception** (whether a draft invoice/payment artifact is absolutely required for a valid Odoo
order flow) is **architecture-dependent** and must **return to ChatGPT before
implementation** — no silent automatic invoice/payment creation. All rows remain "Not decided
/ Evidence pending" pending sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14).
See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**Product Sprint G revision non-decision note (2026-07-01, PR #55 review) — NOT an
architecture decision; AR rows remain "Not decided / Evidence pending".** ChatGPT corrected
DEC-003 to include **controlled bidirectional product onboarding** in MVP (controlled product
export/update, with matching, binding, preview/dry-run, and draft/unpublished/channel-controlled
safety). This adds **product-scope inputs** to two AR rows without deciding them: **AR-002**
now also carries the **destructive-apply / full-state-write mechanics** (`productSet`
delete-on-omit) that the controlled export path must guard, plus the API-strategy dependency;
**AR-005** now also carries **product export/import matching + binding + the first-sync source
strategy** (Shopify-source / Odoo-source / both-match-first) and the **product match-key set**
(SKU/internal-reference, barcode). **Full autonomous bidirectional catalog management** —
automatic all-field two-way conflict resolution, a complex field-ownership matrix, and advanced
publish/channel campaign management — **remains later and architecture-gated** (a future
field-ownership + conflict-resolution design must be reviewed and accepted before inclusion).
**No AR row is decided, accepted, proposed for active review, or re-litigated.** All remain
"Not decided / Evidence pending" (`CLAUDE.md` §4–§5; RB-14). NB: **TeqStars** documentation,
recorded 403-blocked in Sprint C, was **re-checked accessible on 2026-07-01**; a **full
TeqStars rebaseline is pending a later research sprint** — it does not change any AR row here._

_**Research Sprint C2 non-decision note (2026-07-01) — NOT decisions; AR rows remain "Not
decided / Evidence pending".** The Sprint C2 TeqStars rebaseline (docs now accessible;
`../01-research/competitor-deep-dives.md`, `competitor-feature-matrix.md`) upgraded TeqStars
from listing-claim-only to **page-classified demonstrated evidence**, which now supplies
**additional competitor inputs** (not resolutions) to several AR rows. For the record only:
**AR-002 (API/distribution)** — the TeqStars docs **state the Shopify GraphQL Admin API** for
sync/webhooks/refunds/cancel/payouts (a vendor doc statement corroborating GraphQL
convergence), and demonstrate a **controlled, draft-safe product export** (Add-to-Listings →
Export Listings with sales-channels-optional = unpublished, Publish/Unpublish, per-listing
Skip-Sync) — a concrete competitor pattern for the DEC-003 controlled-onboarding path, but
**REST/GraphQL/hybrid, distribution (public vs custom), and the `productSet` delete-on-omit /
full-state-write mechanics stay OPEN**. **AR-003 (orchestration/queue)** — TeqStars runs
**webhooks (background-thread fast-ack) + scheduled Automatic Jobs + manual + per-operation
queues** (Product/Customer/Order/Return, Queue Batch Limit 100, **cron-processed — framework
not named**) with a collection background job that "retries in the next run" — a real-world
data point that a **cron-processed per-op queue** (not necessarily OCA `queue_job`) is viable,
alongside VentorTech's `queue_job`; the **`ir.cron` vs `queue_job` choice and Odoo-Online
feasibility stay OPEN**. **AR-005 (binding/dedup)** — TeqStars binds via **Listing / Listing
Item** entities to Odoo products/variants, matches on **"Sync Listings Based On" = SKU /
Barcode / both**, dedups customers on a **multi-field search**, and guards product creation
(Create-Odoo-Products) — corroborating a **dedicated binding model + SKU/barcode match keys +
first-sync guard**, but the `ir.model.data`-reuse-vs-dedicated model, per-store keys, and
deleted-binding handling **stay OPEN**. **AR-006 (error/retry/idempotency)** — TeqStars shows
**adjacent guards only** (refund amount-match, already-cancelled) + typed logs +
Activity-on-failure, but **no explicit `@idempotent` directive, no automatic-retry/backoff
taxonomy, no first-class cross-object reconciliation, and no rate-limit/GraphQL-cost
throttling** (adversarially verified ⬜) — **reinforcing** (not closing) the idempotency +
reconciliation + retry + throttle whitespace that AR-006 must resolve. **AR-007 (inventory)** —
TeqStars demonstrates **multi-location** (export combines multiple locations; third-party
location excluded), **quantity-field choice** (Free-to-Use / On-Hand / Forecasted), and
**controlled apply** (Validate Inventory Adjustment; lot/serial skipped) — corroborating the
AR-007 direction; design **stays OPEN**. **AR-008 (fulfilment)** — TeqStars demonstrates
deliver → **Update in Marketplace** (status + tracking), **click & collect** pickup lifecycle,
and shipped-order import → stock moves — corroborating FulfillmentOrder-era + tracking
write-back; design **stays OPEN**. The rebaseline routes these here as **competitor inputs
only** and re-litigates nothing; **no AR row is decided, accepted, proposed for active review,
or re-litigated.** All remain "Not decided / Evidence pending" pending sufficient research +
ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). No architecture doc, ADR, or implementation plan
was produced. See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**RB-14 Architecture Preparation — Part 1 non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** This sprint produced the **first architecture
framing documents** under `../03-architecture/` — an
[`architecture-decision-framing.md`](../03-architecture/architecture-decision-framing.md) map
plus **deep framing** for **AR-002** (distribution/API), **AR-003** (sync orchestration/queue),
and **AR-005** (binding/dedup/identity), backed by a current **official-source refresh**
([`rb14-official-source-refresh.md`](../03-architecture/rb14-official-source-refresh.md), access
date 2026-07-01, ~40 Tier-1 Shopify/Odoo pages re-verified). **These documents FRAME the
decisions and DECIDE none of them.** Explicitly: **no** REST/GraphQL/hybrid choice, **no**
public-vs-custom distribution choice, **no** OAuth-vs-token choice, **no** `ir.cron`-vs-`queue_job`-
vs-external-worker choice, **no** binding data model, **no** module boundaries, **no** data model
— every candidate option is labelled `[Not decided]` with evidence-for/against, risks, UX
implications, and required-evidence-before-decision. **AR-002, AR-003, AR-005 are now FRAMED
(not decided); AR-004, AR-006, AR-007, AR-008 remain NOT framed and NOT decided** (AR-006/007/008
depend on AR-002/003/005; AR-004 module boundaries are recommended to wait until enough data-flow
decisions are framed — a **recommendation, not a decision**). **Official-source refresh completed**
and dated; the load-bearing facts were re-confirmed current with a few **version-sensitive deltas
flagged** (GraphQL `latest` alias now `2026-07`; `@idempotent` on inventory set/adjust
**required as of 2026-04**, optional from 2026-01; `productSet` delete-on-omit is **list-fields-
only**; dual offline-token model). The **Odoo async-queue absence is classified as an [Inference
from official fact]** — the official docs document **only `ir.cron`** for scheduled/background
work and do **not** document a general-purpose async job queue (absence of documentation, not a
positive Official fact; OCA `queue_job` is **community, not core**; confirm against 19.0 source if
load-bearing). **New/sharpened open questions** surfaced for ChatGPT
(custom-vs-public GraphQL mandate; **GID permanence not asserted**; **no general mutation
idempotency** beyond `@idempotent`; `ir.model.data` `(module,name)` uniqueness unconfirmed;
`sudo()` bypass not literally on `security.rst`; **Odoo Online feasibility open**). **DEC-003 and
MVP scope are unchanged; competitor evidence was not promoted to official fact; implementation
remains blocked.** The framing routes everything back here as **inputs**; **no AR row is decided,
accepted, proposed for active review, or re-litigated.** All rows stay "Not decided / Evidence
pending" pending sufficient research + ChatGPT approval (`CLAUDE.md` §4–§5; RB-14). Recommended
decision order (a **recommendation**): decide **AR-002, AR-003, AR-005 before implementation
planning**; **AR-006/007/008 depend on them**; **AR-004 waits**. See DP-006's evidence-
consistency gate in `defect-pattern-log.md`._

_**RB-14 Architecture Preparation — Part 2 non-decision note (2026-07-01) — NOT decisions; AR
rows remain "Not decided / Evidence pending".** This sprint re-checked **only** the high-risk
open questions surfaced by RB-14 Part 1 against **official Shopify docs**, **official Odoo 19.0
docs**, and **official Odoo 19.0 source code** (`odoo/odoo` 19.0), then **narrowed** AR-002/AR-003/
AR-005 into **decision candidates** for ChatGPT — producing
[`rb14-part2-open-question-resolution.md`](../03-architecture/rb14-part2-open-question-resolution.md)
and [`rb14-decision-candidate-brief.md`](../03-architecture/rb14-decision-candidate-brief.md) and
adding RB-14 Part 2 notes to the AR-002/003/005 framing docs + the framing map. **These documents
RESOLVE/NARROW EVIDENCE and DECIDE nothing.** Explicitly: **no** REST/GraphQL/hybrid choice,
**no** public-vs-custom distribution choice, **no** OAuth-vs-token choice, **no** `ir.cron`-vs-
`queue_job`-vs-external-worker choice, **no** binding data model, **no** module boundaries — every
narrowing is labelled `[Recommendation]` / `[Decision candidate]`; **AR-002, AR-003, AR-005 stay
"Not decided / Evidence pending"; AR-004/006/007/008 remain later and not framed.** Evidence
outcomes (facts, not decisions): **resolved from source** — `ir.cron` signatures + failure
constants 3/5/7d (RQ-003-3), `ir.model.data` fields + **`UniqueIndex('(module, name)')`** with no
per-store/audit fields (RQ-005-3), **`sudo()` bypasses access rights AND record rules** (RQ-005-4);
**materially narrowed** — **24-hour** idempotency dedup TTL + fixed **17-mutation** `@idempotent`
set + **no general mutation idempotency/`clientMutationId`** (RQ-005-2), **"Odoo Online is
incompatible with custom modules"** → substrate is Odoo.sh/on-prem (RQ-003-1), custom apps **not
categorically forbidden from REST** with GraphQL the sole long-term API and no REST EOL (RQ-002-1),
protected-data access **"Always available"** for custom apps vs **"Requires review"** for public
with compliance webhooks App-Store-scoped (RQ-002-2), offline token model + 90-day rotating refresh
(RQ-002-3); **re-confirmed open** — **GID permanence not asserted** (RQ-005-1); and for RQ-003-2
the reviewed source confirms `ir.cron` (`[Official source-code fact]`) and that `with_delay` is
absent, while a general async queue was **not found** in the reviewed docs/source (`[Inference]`;
whole-repo absence `[Open question]`; OCA `queue_job` community). **Still-open items
kept open** (custom-app compliance obligations — **not assumed absent**; `@idempotent` key
uniqueness scope; bulk-op idempotency; Odoo.sh/on-prem jobrunner/`server_wide_modules` support;
whole-repo async-queue absence). Candidate carry-forwards (inputs only): **AR-002** custom +
GraphQL-first + offline token; **AR-003** internal cron-queue or `queue_job` (turnkey); **AR-005**
dedicated per-domain or hybrid binding model. **Weak/avoid-candidates were noted but NOT entered in
`rejected-approaches-log.md`** (formal rejection needs ChatGPT, `CLAUDE.md` §10). **DEC-003 and MVP
scope unchanged; competitor evidence was excluded from this official-only pass; implementation
remains blocked.** Recommended next: **RB-14 Part 3 — AR-002 decision sprint, only if ChatGPT
accepts Part 2.** All rows stay "Not decided / Evidence pending" pending ChatGPT approval
(`CLAUDE.md` §4–§5; RB-14). See DP-006's evidence-consistency gate in `defect-pattern-log.md`._

_**Control-Room Reset Sprint 1 note (2026-07-02): no AR-row change; non-decision confirmed.** A
mechanical documentation-residue sweep (`../05-qa/documentation-residue-sweep.md`) ran after PR #58
(RB-14 Part 2) merged — **no research, no fan-out, no new evidence gathered.** It corrected stale
current-truth statements (MVP-not-finalized wording superseded by DEC-003; TeqStars/TQ 403-blocked
wording superseded by the Sprint C2 rebaseline; "Empty" claims in the `04-decisions/` and
`03-architecture/` READMEs) and logged DEC-003's already-decided Option C rejection into
`rejected-approaches-log.md` (RA-001) — **it did not evaluate or reject any new approach.** It also
added (as `[Recommendation — becomes binding when merged by ChatGPT]`) phase-exit criteria and a
documentation-maintenance rule to `quality-feedback-loop.md` §10–§11. **AR-002, AR-003, AR-005 stay
"Not decided / Evidence pending"; AR-004/006/007/008 remain not framed. No AR row changed status.
DEC-003 body untouched; MVP scope unchanged; implementation remains blocked.** Recommended next
(unchanged from the RB-14 Part 2 note above, pending ChatGPT/Fable review of this sweep): **RB-14
Part 3 / Evidence Refresh + Combined AR-002/003/005 Decision Preparation.**_

_**Evidence Refresh + Combined AR-002/003/005 Decision Preparation (2026-07-02) — AR-002, AR-003,
AR-005 move from "Not decided / Evidence pending" to "Proposed for ChatGPT review"; still NOT
accepted.** A small, targeted official-source refresh (Odoo.sh `server_wide_modules`/Jobrunner
silence; Odoo.sh production-cron "best effort" behavior, both new 2026-07-02 facts; OCA
`queue_job` 19.0 community evidence — full record in
[`../03-architecture/ar002-ar003-ar005-evidence-refresh.md`](../03-architecture/ar002-ar003-ar005-evidence-refresh.md))
plus the already-strong RB-14 Part 1/2 evidence base (2026-07-01) produced three **proposed**
decision records: [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md)
(AR-002 — custom/Admin-created app, GraphQL-first, offline token; public App Store/OAuth/Billing
deferred), [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md)
(AR-003 — webhook + `ir.cron` + internal queue model as the Phase 1 default substrate on
Odoo.sh/on-prem; OCA `queue_job` deferred/optional, not default), and
[`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
(AR-005 — a dedicated/hybrid per-store binding model as the source of truth; `ir.model.data`
rejected as the *primary* mechanism; no name-only matching). **Each DEC file is explicitly
`Status: Proposed for ChatGPT review`, not `Accepted` — this sprint does not self-accept any
decision.** The Status cells for AR-002/AR-003/AR-005 above are updated to **"Proposed for
ChatGPT review"** accordingly; **AR-004/AR-006/AR-007/AR-008 are untouched** (still not framed /
not decided). A small number of options were explicitly proposed-rejected as part of these DEC
files (REST-heavy API, public App Store as a Phase 1 requirement, OCA `queue_job` as the Phase 1
*default*, `ir.model.data` as the *primary* binding mechanism, name-only automatic matching) —
logged in `rejected-approaches-log.md` as **proposed**, pending the same ChatGPT review as the DEC
files themselves (not yet final rejections). **DEC-003 and MVP scope are unchanged; no
implementation is authorized.** Recommended next (pending this review): **ChatGPT/Fable review of
DEC-004/005/006, then a Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint if accepted.**_

_**DEC-004/005/006 Acceptance Patch (2026-07-02) — AR-002, AR-003, AR-005 move from "Proposed for
ChatGPT review" to "Accepted."** After PR #60 merged into `Shopify-connector` (merge commit
`7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`) and Fable's minor-change review was applied, **ChatGPT
formally accepted** all three proposed decision records:
[`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md)
(AR-002), [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md)
(AR-003), and [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
(AR-005), each now **`Status: Accepted by ChatGPT`, acceptance date 2026-07-02**. The Review
decision and Status cells for AR-002/AR-003/AR-005 above are updated to **"Accepted by ChatGPT"** /
**"Accepted"** accordingly. The five (now six, with RA-007) proposed-rejection rows tied to these
DEC files (`rejected-approaches-log.md` RA-002–RA-007) **became binding final rejected approaches**
on this same acceptance — see that log's own acceptance note. **AR-004/AR-006/AR-007/AR-008 are
untouched** (still "Not decided / Evidence pending," not framed). **This acceptance decides the
architecture direction for AR-002/003/005 only — it does not by itself authorize implementation.**
DEC-003 and MVP scope remain unchanged; no code, Odoo module, or implementation plan was produced.
Per `../05-qa/quality-feedback-loop.md` §10, AR-002/AR-003/AR-005 acceptance is **one of several**
Phase 1 research-phase-exit criteria (alongside Phase 1 domain-model briefs, a DEC-003 scope-hole
amendment, and a UX/operator-flow sprint) — the implementation gate itself opens only after ChatGPT
separately approves that full exit. Recommended next: **Phase 1 Domain Model + DEC-003 Scope-Hole
Closure sprint.**_

_**Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint (2026-07-02) — NOT an architecture
decision; AR-006, AR-007, AR-008 remain "Not decided / Evidence pending."** This sprint produced
[`../03-architecture/phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md)
(a documentation-level Phase 1 domain-model brief covering store/connection, binding/identity,
product, customer, order/sale, inventory, fulfilment, and queue/log/error concepts) and proposed
[`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
(`Status: Proposed for ChatGPT review`) closing five DEC-003 scope-hole wordings (variant
export/update; image/media and price "where feasible" wording; a first-inventory-push guard;
fulfilment customer-notification default; tax/shipping/discount/payment/order-accounting
treatment). **For the record only, this sprint feeds — and explicitly does not decide — three AR
rows:** **AR-006** (error/retry/idempotency taxonomy) — the domain-model brief names a minimum
job/log concept (source, state, retry count, error class placeholder) per the already-accepted
DEC-005 substrate, but the **full taxonomy stays AR-006, not decided here**; **AR-007** (inventory
architecture) — the proposed first-inventory-push guard is a **scope-level guardrail statement**
(preview + confirmation + mapped location + recorded source-of-truth before the first
Odoo→Shopify write), **not** a quantity-field default, multi-location mechanism, or apply-mode
decision, all of which **stay AR-007, not decided here**; **AR-008** (fulfilment architecture) —
the proposed fulfilment customer-notification default (no notification unless explicitly enabled,
grounded in Shopify's own `FulfillmentInput.notifyCustomer`/`fulfillmentTrackingInfoUpdate`
defaults) is a **scope-level default statement**, **not** a FulfillmentOrder-orchestration or
multi-package/location design, which **stay AR-008, not decided here**. **AR-004** module
boundaries are untouched by this sprint. **No AR row changes status; AR-006/AR-007/AR-008 remain
"Not decided / Evidence pending"; AR-002/AR-003/AR-005 remain "Accepted."** DEC-003 body was not
edited; DEC-004/005/006 were not edited; implementation remains blocked. Recommended next (pending
ChatGPT/Fable review of DEC-007 and the domain-model brief): **Master Blueprint sprint**, and/or a
dedicated **AR-006/AR-007/AR-008 architecture-decision sprint**._

_**DEC-007 Acceptance Patch (2026-07-02) — NOT an architecture decision; AR-004/AR-006/AR-007/
AR-008 remain "Not decided / Evidence pending."** DEC-007 accepted by ChatGPT on 2026-07-02 after
PR #62 merged into `Shopify-connector` and Fable's review (**ACCEPT WITH MINOR CHANGES**) was
applied. DEC-007 is a **scope-clarification addendum** to DEC-003, not an AR-004/006/007/008
architecture decision — it **feeds AR-006, AR-007, and AR-008** (the retry/error taxonomy, the
inventory first-push-guard scope statement, and the fulfilment notification-default scope
statement, respectively) **but does not decide any of them**. **AR-004 remains untouched** by this
patch. **AR-004/AR-006/AR-007/AR-008 remain "Not decided / Evidence pending"; AR-002/AR-003/AR-005
remain "Accepted."** This acceptance makes RA-008/RA-009/RA-010 (`rejected-approaches-log.md`)
binding final rejected approaches — see that log's own acceptance note. DEC-003/004/005/006 remain
unchanged; no code, Odoo module, or implementation plan was produced; implementation remains
blocked. Recommended next work:
- **AR-004 + AR-006 decision sprint.**
- **AR-007 + AR-008 decision sprint.**
- **UX/operator-flow sprint.**
- **Master Blueprint**, after those gates._

_**AR-004 + AR-006 Decision Preparation (2026-07-02) — AR-004 and AR-006 move from
"Not decided / Evidence pending" to "Proposed for ChatGPT review"; still NOT accepted.**
After PR #63 merged into `Shopify-connector` and DEC-003/004/005/006/007 acceptance
confirmed, this sprint produced two evidence-backed decision briefs —
[`../03-architecture/ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md)
and
[`../03-architecture/ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md)
— and two proposed decision records:
[`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md)
(**AR-004** — a layered, domain-aligned addon family: `shopify_connector_core`/
`product`/`sale`/`inventory`/`fulfillment` for Phase 1, strict dependency DAG, no
`adams_base` dependency found justified. **DEC-008 resolves module boundaries only —
the feature-flag / per-store capability-configuration mechanism that AR-004's DEC-003
scope also names is routed onward to the UX/operator-flow sprint and Master Blueprint /
implementation planning, not decided here.** DEC-008 also does not choose between
DEC-006's polymorphic-vs-per-domain binding-schema options — it places binding
responsibility with modules, not table shape.) and
[`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)
(**AR-006** — a classified retry policy with a 6-job-source/10-state/16-error-class
taxonomy, layered idempotency spanning Shopify's `@idempotent` surface and
connector-designed keys, and recovery-first log/audit requirements). **Each DEC file is
explicitly `Status: Proposed for ChatGPT review`, not `Accepted` — this sprint does not
self-accept any decision.** The Review decision and Status cells for AR-004/AR-006 above
are updated to **"Proposed for ChatGPT review"** accordingly. A small number of options
were explicitly proposed-rejected as part of these DEC files (one giant
`shopify_connector` module, per-feature micro-module explosion, duplicating queue/job/
log/binding abstractions per domain, retry-everything automatically, never-retry-
automatically/manual-only recovery, user-facing stack traces as the primary error UX, no
connector-designed idempotency key beyond binding identity) — logged in
`rejected-approaches-log.md` as **PROPOSED**, pending the same ChatGPT review as the DEC
files themselves (not yet final rejections). **AR-007 and AR-008 are untouched** (still
"Not decided / Evidence pending"); no AR-007/AR-008 internal design (inventory quantity
fields, multi-location mechanism, FulfillmentOrder orchestration) was decided — the new
briefs explicitly keep those rows open. No fresh external research was performed; every
citation reuses already-verified facts from `../01-research/shopify-official-api-notes.md`
and `../01-research/odoo-official-architecture-notes.md`. **DEC-003 through DEC-007 were
not edited; no code, Odoo module, or implementation plan was produced; implementation
remains blocked.** Recommended next (pending this review): **ChatGPT/Fable review of
DEC-008/009, then an AR-007 + AR-008 decision sprint and/or a UX/operator-flow sprint.**_

_**DEC-008/DEC-009 Acceptance Patch (2026-07-02) — AR-004 and AR-006 move from "Proposed
for ChatGPT review" to "Accepted."** After PR #64 merged into `Shopify-connector` (merge
commit `e4c74abf0e3b4ad32e66413d27b40287ed4c5822`) and Fable's minor-change review
(**ACCEPT WITH MINOR CHANGES**) was applied, **ChatGPT formally accepted** both proposed
decision records:
[`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md)
(AR-004) and
[`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)
(AR-006), each now **`Status: Accepted by ChatGPT`, acceptance date 2026-07-02**. The
Review decision and Status cells for AR-004/AR-006 above are updated to **"Accepted by
ChatGPT"** / **"Accepted"** accordingly. **AR-004 is accepted as the module-boundary
strategy; DEC-008 does not decide the feature-flag / per-store capability-configuration
mechanism (still routed to the UX/operator-flow sprint and Master Blueprint /
implementation planning) and does not choose between DEC-006's polymorphic-vs-per-domain
binding-schema options.** **AR-006 is accepted as the error/retry/idempotency strategy;
DEC-009 does not decide exact retry/backoff constants or exact reconciliation
cadence/scope (both remain implementation-planning items).** The seven proposed-rejection
rows tied to these DEC files (`rejected-approaches-log.md` RA-011–RA-017) **became binding
final rejected approaches** on this same acceptance — see that log's own acceptance note.
**AR-007 and AR-008 remain "Not decided / Evidence pending"** — untouched by this
acceptance; no inventory or fulfilment internal design was decided. **This acceptance
decides the architecture direction for AR-004/AR-006 only — it does not by itself
authorize implementation.** DEC-003/004/005/006/007 remain unchanged; no code, Odoo
module, or implementation plan was produced; implementation remains blocked. Recommended
next work:
- **AR-007 + AR-008 decision sprint.**
- **UX/operator-flow sprint.**
- **Master Blueprint.**
- **Implementation only after a separate ChatGPT gate.**_

_**AR-007 + AR-008 Decision Preparation (2026-07-02) — AR-007 and AR-008 move from
"Not decided / Evidence pending" to "Proposed for ChatGPT review"; still NOT accepted.**
After PR #65 merged into `Shopify-connector` (merge commit
`dfb0199c9588ae600216ef549d160d0ced15034f`) and DEC-003/004/005/006/007/008/009 acceptance
confirmed, this sprint produced two evidence-backed decision briefs —
[`../03-architecture/ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md)
and
[`../03-architecture/ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md)
— plus a small, targeted Odoo-side official-source check
([`../03-architecture/ar007-ar008-evidence-refresh.md`](../03-architecture/ar007-ar008-evidence-refresh.md),
access date 2026-07-02, since the existing Odoo research notes had zero coverage of
`stock.quant`/`stock.picking`/delivery-carrier models) — and two proposed decision
records:
[`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md)
(**AR-007** — Odoo as ongoing source of truth for Shopify inventory write-back, a
controlled first-sync import, inventory identity keyed on `(store, inventory_item_id,
location_id)`, an explicit non-inferred location mapping, the DEC-007 first-push guard
honored in full, layered sync, and the DEC-009 ambiguous-outcome retry rule applied to
inventory writes) and
[`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md)
(**AR-008** — validated `stock.picking` as the fulfillment trigger, FulfillmentOrder-based
mutations only, matched order/FulfillmentOrder/line/quantity, the DEC-007
no-notification-by-default guard honored in full, single-fulfillment-location Phase 1
posture with multi-package/multi-location deferred, and the DEC-009 ambiguous-outcome
retry rule applied to fulfillment writes). **Each DEC file is explicitly `Status:
Proposed for ChatGPT review`, not `Accepted` — this sprint does not self-accept any
decision.** The Review decision and Status cells for AR-007/AR-008 above are updated to
**"Proposed for ChatGPT review"** accordingly. A small number of options were explicitly
proposed-rejected as part of these DEC files (writing Shopify's read-only `committed`
quantity; single-location-only/SKU-only inventory writes without per-location binding
identity; autonomous bidirectional inventory conflict resolution in Phase 1; treating
Shopify/Odoo inventory quantities as equivalent without an explicit source-of-truth;
legacy fulfillment API flow instead of FulfillmentOrder-based flow; fulfillment creation
without FulfillmentOrder/line/quantity/location matching) — logged in
`rejected-approaches-log.md` as **PROPOSED** (RA-018 through RA-023), pending the same
ChatGPT review as the DEC files themselves (not yet final rejections); blind first
inventory push, hidden/default-on notification, blind retry-everything, and binding-alone
idempotency were **not** re-logged (already covered by the binding RA-008, RA-009,
RA-014, and RA-017 respectively). **DEC-010/DEC-011 do not authorize implementation** —
implementation remains blocked pending ChatGPT acceptance of these proposals **and** a
separate implementation-gate opening (`../05-qa/quality-feedback-loop.md` §10; `CLAUDE.md`
§5). **UX/operator-flow and the Master Blueprint remain future steps**, not started by
this sprint. DEC-003/004/005/006/007/008/009 were not edited; no code, Odoo module, or
implementation plan was produced. Recommended next (pending this review):
**ChatGPT/Fable review of DEC-010/DEC-011, then a UX/operator-flow sprint and/or the
Master Blueprint sprint if accepted.**_

_**PR #66 Fable review — DEC-008 clarification note (2026-07-02) — NOT an architecture
decision; AR-007/AR-008 remain "Proposed for ChatGPT review," not accepted.** Fable
reviewed PR #66 and returned **ACCEPT WITH MINOR CHANGES**, including a correction to how
DEC-010/DEC-011 attribute the proposed shared Shopify-Location reference to DEC-008. For
the record: **DEC-010/DEC-011 propose a clarification/extension of DEC-008's `core`-owns
list** — a minimal Shopify Location reference/cache/list may live in
`shopify_connector_core`; `shopify_connector_inventory` keeps sole ownership of the
Odoo↔Shopify location **mapping**; `shopify_connector_fulfillment` never depends on
`shopify_connector_inventory`. This is **not** something DEC-008 already explicitly
decided — DEC-008 names `core`'s cross-cutting substrate (transport, queue, binding
abstraction, error registry, setup wizard, dashboard/log center), not Shopify-object
reference data — so the prior wording (attributing the reference to `core` "already
owning cross-cutting reference data" under DEC-008) has been corrected in DEC-010,
DEC-011, and the AR-007/AR-008 briefs to read as a **proposed** clarification. This
clarification **dissolves the potential DEC-008 link-module question for Phase 1**
(a possible future glue module letting `fulfillment` reuse `inventory`'s location
mapping) **without changing DEC-008's dependency direction** and without creating a new
module. **If DEC-010/DEC-011 are later accepted, the acceptance patch must explicitly
record this clarification against DEC-008** (mirroring how the DEC-008/DEC-009
acceptance patch above records its own caveats) — it is not silently folded into DEC-008
by this note. **DEC-010/DEC-011 remain "Proposed for ChatGPT review," not accepted; AR-007
and AR-008 remain "Proposed for ChatGPT review," not accepted.** This PR also corrected a
false repo-evidence claim (the literal 17-mutation `@idempotent` list, already itemized in
`rb14-part2-open-question-resolution.md`, was previously described as "not itemized in
repo docs"), added a dated official verification for `FulfillmentInput.lineItemsByFulfillmentOrder`
and FulfillmentOrder `assignedLocation` (`ar007-ar008-evidence-refresh.md`, access date
2026-07-02), added a fulfillment operation-serialization guard for unresolved ambiguous
operations, and added core-Location-reference invariants (no Odoo-location IDs, no mapping
decisions in the core reference). DEC-003/004/005/006/007/008/009 were not edited; no
code files changed; implementation remains blocked._

_**DEC-010/DEC-011 Acceptance Patch (2026-07-02) — AR-007 and AR-008 move from "Proposed
for ChatGPT review" to "Accepted."** ChatGPT formally accepted
[`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md)
(AR-007) and
[`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md)
(AR-008) on **2026-07-02** (after PR #66 merged into `Shopify-connector` and Fable's
minor-change review — **ACCEPT WITH MINOR CHANGES** — was applied). **DEC-010 is the
accepted inventory architecture strategy; DEC-011 is the accepted fulfillment
architecture strategy.** The Review decision and Status cells for AR-007/AR-008 above are
updated to **"Accepted by ChatGPT"** / **"Accepted"** accordingly. **The shared Shopify
Location reference clarification (proposed in DEC-010/DEC-011 as an extension of DEC-008's
`core`-owns list) is now ratified against DEC-008** through this same DEC-010/DEC-011
acceptance: `shopify_connector_core` may hold a minimal Shopify-side Location
reference/cache/list (never Odoo-location IDs or Odoo↔Shopify mapping decisions);
`shopify_connector_inventory` remains the sole owner of the Odoo↔Shopify location mapping;
`shopify_connector_fulfillment` still must not depend on `shopify_connector_inventory`;
DEC-008's dependency direction is unchanged and no new module is created. The six
proposed-rejection rows tied to these DEC files (`rejected-approaches-log.md` RA-018
through RA-023) **became binding final rejected approaches** on this same acceptance —
see that log's own acceptance note. **This acceptance decides the architecture direction
for AR-007/AR-008 only — it does not by itself authorize implementation.**
DEC-003/004/005/006/007/008/009 remain unchanged; no code, Odoo module, or implementation
plan was produced; implementation remains blocked. **All architecture decisions AR-002
through AR-008 are now accepted.** Recommended next work:
- **UX/operator-flow sprint.**
- **Master Blueprint.**
- **Implementation only after a separate ChatGPT gate.**_

_**Master Blueprint Sprint A (2026-07-03) — AR-010 added, Proposed for ChatGPT review;
NOT accepted.** Prepared after PR #69 merged into `Shopify-connector` (merge commit
`305f396bcbd2656a4282ed18c5983540503b5502`), with DEC-003 through DEC-012 confirmed
accepted, AR-002 through AR-009 confirmed accepted, and all five Phase 1
research-phase-exit criteria (`quality-feedback-loop.md` §10) confirmed satisfied. This
sprint created the first Master Blueprint package —
[`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md) (index),
[`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
(Part A, core/common substrate), and
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
(MBQ-01–MBQ-52) — and proposed
[`../04-decisions/DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md)
(`Status: Proposed for ChatGPT review`). **AR-010 is not a new platform-fact/architecture-
option question in the AR-002…AR-008 sense** — it is the blueprint-level conversion of the
already-accepted DEC-003 through DEC-012 substrate decisions, plus the two forks those
decisions explicitly routed to the Master Blueprint (binding schema shape per
DEC-006/DEC-008; the feature-flag mechanism per DEC-008), each proposed with a preferred
direction and routed through DEC-013's review (MBQ-11, MBQ-07). **No AR-002…AR-009 row is
changed, re-litigated, or contradicted; no RA-001…RA-023 row is reintroduced; no new Tier-1
claim is introduced; no web research was performed.** Product/customer/sale/inventory/
fulfillment detailed domain blueprints are **not started** (routed to Master Blueprint
Sprints B/C). DEC-003 through DEC-012 were not edited; no code files changed;
**implementation remains blocked** — DEC-013 does not authorize implementation under any
outcome, and the implementation gate remains a separate ChatGPT approval. Recommended next
(pending this review): **ChatGPT/Fable review of DEC-013/AR-010, then Master Blueprint
Sprint B — Product, Customer, and Sale/Order Domain Blueprint.**_

_**DEC-013 Acceptance Patch (2026-07-03) — AR-010 is now Accepted by ChatGPT.** After
Fable reviewed PR #70 and returned **ACCEPT WITH MINOR CHANGES** (Part D — UI/UX Screen
Design Blueprint added to the Master Blueprint sequence and gate criteria; MBQ-53/MBQ-54
added; the §I.3 feature-flag execution-time re-check scoped to fail-safe enablement gating
only; a cross-domain binding-enumeration seam and binding-granularity bound added to §C.8;
several claim-label corrections; a webhook-topic registration seam added to §A.5) and a
tiny consistency fix (AR-010's MBQ range corrected to MBQ-01–MBQ-54) were applied, **PR #70
merged into `Shopify-connector`** (merge commit
`5c44971d1df84d5657da0164bf874b1125aee64f`). **ChatGPT formally accepted**
[`DEC-013`](../04-decisions/DEC-013-master-blueprint-core-substrate.md) on **2026-07-03**.
AR-010's table row above moves from "Proposed for ChatGPT review" to **"Accepted by
ChatGPT"** / **"Accepted."** This acceptance resolves, at blueprint level: **MBQ-11**
(binding schema shape — per-domain concrete models on a core abstract contract, with a
cross-domain enumeration/registration seam and a binding-granularity bound); **MBQ-07**
(feature-flag mechanism direction — store-scoped core settings record, domain-extended;
exact technical implementation detail remains open for implementation planning); **MBQ-47**
(Reviewer role boundary — approval/manual-review focused, not a general retry/trigger
role); and **partially** resolves **MBQ-45** (the proposed role hierarchy — Administrator
⊃ Operator/Reviewer ⊃ Auditor — is accepted; exact roles→groups mapping and the
admin-vs-functional-user screen split remain open). **MBQ-04** (credential storage/
encryption mechanism), **MBQ-08** (store-disconnect data-retention posture), **MBQ-53**
(screen-level UI/UX design blueprint), and **MBQ-54** (domain-module uninstall/disable data
lifecycle) **remain open** — not resolved by this acceptance. Per `CLAUDE.md` §10, this
acceptance **does not authorize implementation**; DEC-003 through DEC-012 remain unchanged;
no code, Odoo module, or implementation plan was produced; **implementation remains
blocked**; **Part D — UI/UX Screen Design Blueprint — remains required before
implementation of any operator-facing screen.** Recommended next: **Master Blueprint
Sprint B — Product, Customer, and Sale/Order Domain Blueprint** (not started)._

_**DEC-014 Acceptance Patch (2026-07-03) — AR-011 is now Accepted by ChatGPT.** After
Fable reviewed PR #72 and returned **REVISE** (B1 routing/state-semantics correction, B2
`ORDERS_UPDATED` narrowing, B3 MBQ-59 acceptance-status label separation, plus twelve minor
issues, all applied on the same branch/PR) and **PR #72 merged into `Shopify-connector`**
(merge commit `e27c21f328436bc734539dd9169a95d79deaadd1`), **ChatGPT formally accepted**
[`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) on
**2026-07-03**. AR-011's table row above moves from "Proposed for ChatGPT review" to
**"Accepted by ChatGPT"** / **"Accepted."** This acceptance accepts, at blueprint level:
**Master Blueprint Part B** (product, customer, and sale/order domain blueprints, in full);
**the Fable B1 route** — `mapping missing`/`data shape mismatch` in `failed_retryable`,
`financial total mismatch` in its own §D.5.5 posture, only the four Sprint-B-relevant
confirmation-required classes in `blocked_manual_review`, **Part A §D.8's vocabulary not
widened**; **the Fable B2 route** — `ORDERS_UPDATED`/order-edit handling is
**evidence-refresh only**, no silent Odoo sale-order line/price/tax/shipping/discount/
payment/refund/fulfillment update under any trigger; **MBQ-59** (automated import
create/bind policy) **accepted at blueprint-policy level** — the pre-create duplicate check
plus two-tier eligibility/match-quality gate, routed via accepted Part A per-class
mechanisms, exact implementation detail remains open; **MBQ-26** (order-import operator
touchpoints) **accepted at blueprint level** — existing sync-center/error-center surfaces
are sufficient, conditioned on the inline financial-evidence breakdown and direct
matching-flow links already specified in Part B §C.14; **MBQ-31** (customer match-key set)
**accepted at blueprint level** — email is the sole automatic match key. **MBQ-23, MBQ-25,
MBQ-29, and MBQ-30** are **partially resolved** by this acceptance (direction accepted,
exact detail open). **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53, MBQ-54, MBQ-55,
MBQ-56, MBQ-57, and MBQ-58 remain open** — not resolved by this acceptance. Per
`CLAUDE.md` §10, this acceptance **does not authorize implementation**; DEC-003 through
DEC-013 remain unchanged; no code, Odoo module, or implementation plan was produced;
**implementation remains blocked**; **Master Blueprint Sprint C** (Inventory and
Fulfillment Domain Blueprint) **remains not started**; **Part D — UI/UX Screen Design
Blueprint — remains not started and remains required before implementation of any
operator-facing screen.** Recommended next: **Master Blueprint Sprint C — Inventory and
Fulfillment Domain Blueprint** (not started)._
