# Master Blueprint — Open Questions Register

> Central register of unresolved **Master Blueprint / implementation-planning
> questions** for the premium **Odoo 19 ↔ Shopify Connector**. Created in
> Master Blueprint Sprint A; **updated by every later blueprint part**.
> Companion index: [`master-blueprint.md`](./master-blueprint.md). Companion
> Part A blueprint:
> [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md).

## Status

**Accepted as the central register through DEC-015**, latest acceptance
date **2026-07-03**. Documentation only; the no-code gate (`CLAUDE.md`
§4–§5) is in force. **Register acceptance does not resolve every
question** — each MBQ row remains open unless the row itself says
**Resolved**, **Partially resolved**, or **Accepted at blueprint(-policy)
level**; notably **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-33,
MBQ-34, MBQ-41, MBQ-53, MBQ-54, MBQ-55, MBQ-56, MBQ-57, MBQ-58, and
MBQ-60 through MBQ-63 remain open**. Registering (or
accepting the register containing) a question does **not** decide it and
does **not** authorize implementation. Every row follows `CLAUDE.md`
§7/§8: unverified items are **open questions**, never asserted.
**Vocabulary note:** an unqualified **Resolved**/**Partially resolved**
label reflects a sprint whose companion decision record ChatGPT has
already **accepted**. A row from a sprint whose companion decision record
is still **Proposed for ChatGPT review** (not yet accepted) is labelled
**Proposed resolved** / **Proposed partially resolved** instead — these
rows remain **open** until that decision record is accepted; see the
Sprint C / DEC-015 acceptance note immediately below — DEC-015 is now
**accepted**, so its rows use the unqualified **Resolved**/**Partially
resolved** labels.

> **Master Blueprint Sprint B note (2026-07-03, revised after PR #72
> ChatGPT review and again after PR #72 Fable review; superseded by the
> DEC-014 acceptance note below).** Sprint B
> ([`master-blueprint-product-customer-sale.md`](./master-blueprint-product-customer-sale.md),
> companion
> [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md))
> proposed updates to the product/customer/order rows below (MBQ-23
> through MBQ-31) and added MBQ-55 through MBQ-59 (MBQ-59 added in the
> PR #72 ChatGPT-requested revision, revised again in the PR #72
> Fable-requested revision to fix its routing description — see MBQ-59's
> own row).
>
> **DEC-014 Acceptance Patch (2026-07-03) — accepted as the register's
> update through Sprint B.** After PR #72 merged into `Shopify-connector`
> (merge commit `e27c21f328436bc734539dd9169a95d79deaadd1`), ChatGPT
> accepted [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
> on **2026-07-03**. MBQ-23, MBQ-25, MBQ-29, and MBQ-30 are now
> **partially resolved** (direction accepted, exact detail still open);
> MBQ-26 (order-import operator touchpoints), MBQ-31 (customer match-key
> set), and MBQ-59 (automated import create/bind policy) are now
> **accepted at blueprint(-policy) level** (see each row below). The
> register's accepted-through-DEC-014 status is otherwise unchanged, and
> **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53, MBQ-54, MBQ-55,
> MBQ-56, MBQ-57, and MBQ-58 remain untouched and open.**

> **Master Blueprint Sprint C note (2026-07-03, revised after PR #74
> Fable review and a same-PR consistency patch; superseded by the
> DEC-015 acceptance note below).** Sprint C
> ([`master-blueprint-inventory-fulfillment.md`](./master-blueprint-inventory-fulfillment.md),
> companion
> [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md))
> proposed updates to the inventory/fulfillment rows below (MBQ-32
> through MBQ-43) and added four new rows, MBQ-60 through MBQ-63 (MBQ-62
> and MBQ-63 added in a Fable-review revision on the same PR — see their
> own rows for what each covers and why).
>
> **DEC-015 Acceptance Patch (2026-07-03) — accepted as the register's
> update through Sprint C.** After Fable reviewed PR #74 (**REVISE** —
> findings C1/C2 plus seven minor findings, fixed on the same PR) and a
> same-PR consistency patch was applied, ChatGPT accepted
> [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
> on **2026-07-03**. MBQ-37 and MBQ-39 are now **resolved** at
> fact-verification level; MBQ-32, MBQ-36, MBQ-38, MBQ-40, MBQ-42, and
> MBQ-43 are now **partially resolved** (direction/fact accepted, exact
> residual detail still open — MBQ-32 stays partially resolved per
> Fable finding C1's correction that the two candidate quantity sources
> are verified but not equivalent; MBQ-42's partial resolution includes
> an accepted widening of `ambiguous match` to also cover a deterministic
> fulfillment-location mismatch, accepted at blueprint level only).
> **MBQ-33, MBQ-34, and MBQ-41 remain open** — each carries a
> recommendation, **not decided by this acceptance** (all three stay
> explicitly ChatGPT-decision-owner rows). **MBQ-35 remains carried
> forward, open, unchanged. MBQ-60 through MBQ-63 remain new and open**
> — none resolved by this acceptance (MBQ-62 — Odoo-event-triggered
> job-source classification, Fable finding C2 — and MBQ-63 — the
> broader inventory-webhook payload/subscription/Phase-1-scope residual
> — both added in the Fable-review revision). The register's
> accepted-through-DEC-015 status is otherwise unchanged, and
> **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53, MBQ-54, MBQ-55,
> MBQ-56, MBQ-57, and MBQ-58 remain untouched and open.**

> **Master Blueprint Sprint D note (2026-07-03) — Part D proposed, not
> accepted.** Sprint D
> ([`master-blueprint-ui-ux-screen-design.md`](./master-blueprint-ui-ux-screen-design.md),
> companion
> [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md))
> drafted the **UI/UX Screen Design Blueprint (Part D)** on the base commit
> `b6199f78064ae4e1934bccee630a14b3d7eef438` (PR #74 / DEC-015 merge). It
> **proposes to partially resolve MBQ-53 only** — the screen-design layer
> (screen inventory, navigation/information architecture, Odoo-native
> interaction patterns, per-screen specs, per-screen states, microcopy
> patterns, and a premium UI/UX acceptance checklist) is proposed complete,
> while exact user-facing copy (**MBQ-22**), exact Odoo identifiers
> (**MBQ-01/02/03/44**), and the admin-vs-functional-user surface split
> (**MBQ-45**) remain open. Because DEC-016 is still **Proposed for ChatGPT
> review** (not accepted), MBQ-53's row below uses the **Proposed partially
> resolved** label and **remains open** until DEC-016 is accepted. **No other
> row is changed by this sprint** — all remain as DEC-015 left them; in
> particular **MBQ-33, MBQ-34, MBQ-41, MBQ-60 through MBQ-63** stay open (each
> is at most *shown* in the screen blueprint as a recommendation or a residual,
> **not decided**), and the implementation-level rows **MBQ-01/02/03/44** and
> all other open rows are carried forward untouched. Part D is
> documentation-only; it authorizes no implementation, and Part E remains not
> started.

## How to read

- **Decision owner:** **ChatGPT** (a control-room decision), **Implementation
  planning** (resolved when the gated implementation-planning sprint writes
  the affected task), or **Official-doc verification** (a Tier-1
  Shopify/Odoo fact that must be verified and cited before use). Combined
  owners mean both are needed.
- **Blocks implementation:** **Yes** = the affected implementation task must
  not be written/coded until this row is resolved or ChatGPT explicitly
  accepts it as an open risk. **No** = can be resolved in parallel without
  blocking the first affected code. Blocking is scoped to the affected
  domain/feature, not the whole project.
- Rows route to the sprint that should resolve them (Part B/C/D per the
  index) where applicable.

---

## 1. Core / setup / config

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-01 | Exact Odoo **model names** for every core concept (store/connection, credential posture, settings/flags, Location reference, job, log, binding contract) | DEC-008; Part A §B–§D | Implementation cannot start without committed names; blueprint names are directions only | Implementation planning | Yes |
| MBQ-02 | Exact **field names/types** for every core concept | Part A §B–§D; phase1-domain-model-brief | Same as MBQ-01; also fixes constraint/index design | Implementation planning | Yes |
| MBQ-03 | Exact **view/menu/action XML IDs** for wizard, dashboard, sync center, error center, settings | DEC-012; Part A §E–§H | UI code needs committed IDs; DEC-012 explicitly left these open | Implementation planning | Yes |
| MBQ-04 | Exact **credential encryption/storage-at-rest mechanism** (Odoo field-level `groups` protection alone vs additional encryption; storage location) | DEC-004; Part A §B.2 | A long-lived offline token is a credential-leak risk if storage is wrong; DEC-004 fixed masking/least-privilege but not the storage mechanism | ChatGPT + Official-doc verification (Odoo capability check) | Yes |
| MBQ-05 | Exact **custom-app creation surface** (merchant Admin-created vs Partner/Dev-Dashboard custom-distribution) and its **token-acquisition mechanics** (incl. non-expiring vs 90-day-rotation variant) | DEC-004 "What remains blocked" | Determines wizard step content and reconnect/rotation flow | Implementation planning (within DEC-004's fixed offline/unattended model) | Yes (setup wizard) |
| MBQ-06 | **Readiness-check list**: which checks are essential vs nice-to-have (scopes, HTTPS/`web.base.url`, webhook reachability, worker/queue presence, credential validity) | setup-ux-principles P2; DEC-012 §1; Part A §E.6 | Fixes the wizard's pass/fail gate and the "connected" definition | ChatGPT (at Part A/B review) or Implementation planning | Yes (setup wizard) |
| MBQ-07 | **Resolved at blueprint-direction level by DEC-013 acceptance (2026-07-03):** store-scoped core settings record, domain-extended (Part A §I.3) — not `ir.config_parameter`, not `res.config.settings`-as-storage, not per-domain ad hoc settings models. Exact **technical feature-flag implementation** (field names, model shape) remains open | DEC-008 "What remains open"; Part A §I; DEC-013 | DEC-008 routed the mechanism to the Master Blueprint; flags gate every domain's behaviour | Implementation planning (direction confirmed; detail remains) | Yes |
| MBQ-08 | **Store-disconnect data-retention posture** — what happens to bindings, jobs, logs, audit records after disconnect | DEC-012 (Fable, PR #68); Part A §B.1 | Wrong posture destroys audit history or leaks stale credentials; affects disconnect UX and re-connect matching | ChatGPT | Yes (disconnect flow) |
| MBQ-09 | Whether **custom apps must implement Shopify's compliance webhooks / are bound by Level 1/2 protected-data obligations** regardless of distribution | DEC-004 (open since RB-14 Part 2) | If yes, compliance endpoints/duties enter Phase 1 scope; DEC-004 mandates conservative handling until resolved | Official-doc verification | Yes (any compliance-relevant code); conservative posture applies meanwhile |
| MBQ-10 | Whether Odoo.sh/on-prem setup can avoid mandatory **`odoo.conf`/queue prerequisites** (turnkey install path) | DEC-005; DEC-012 §1 open questions | Affects install docs and wizard prerequisites step; not a design blocker | Implementation planning + Official-doc verification | No |
| MBQ-54 | **Domain-module uninstall / disable data lifecycle** — if domain modules extend core settings (§I) or own concrete binding tables (§C.8), uninstall/disable behaviour must not silently lose bindings, logs, flags, or audit history | Part A §I feature-flag mechanism; Part A §C binding shape | A merchant disabling or uninstalling a domain module must not silently destroy binding/audit/log history — this is the module-lifecycle counterpart to the already-accepted "disabling must not delete history" rule (DEC-012 store settings §4; Part A §I.4), extended to the harder case of a full module **uninstall** | ChatGPT + Implementation planning | Yes for uninstall/disable lifecycle; No for normal MVP sync if uninstall is explicitly unsupported/guarded in Phase 1 |

## 2. Binding / dedup

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-11 | **Resolved by DEC-013 acceptance (2026-07-03):** per-domain concrete binding models extending a core abstract contract, with a cross-domain enumeration/registration seam and a binding-model granularity bound (Part A §C.8); the single polymorphic table option is not chosen | DEC-006 (fork left open); DEC-008 (binding-schema note); Part A §C.8; DEC-013 | Fixes where tables live, index/constraint design, and reconciliation-scale query shape | Resolved — ChatGPT via DEC-013 | No |
| MBQ-12 | **Shopify GID permanence/non-reuse** — not asserted by Shopify | DEC-006; RB-14 Part 2 (RQ-005-1) | Already handled defensively (stale/review, no silent recreate); official assertion would simplify, not change, the design | Official-doc verification (may remain unresolved) | No (defensive design stands) |
| MBQ-13 | Exact **stale/recreated-binding review flow detail** (fields shown, resolution actions, re-bind semantics) | DEC-006; Part A §C.6 | Operator resolution of stale/hijack cases must be auditable and safe | Implementation planning | No (behavioural rules fixed; detail refinable) |
| MBQ-14 | **`@idempotent` key uniqueness scope** (per-shop / per-app / global) and any API-version-specific behaviour | RB-14 Part 2 (RQ-005-2); DEC-009/DEC-010 | Determines how persisted idempotency keys are namespaced for safe retry | Official-doc verification | Yes (inventory/refund write code) |
| MBQ-15 | **Bulk Operation idempotency/resumability semantics** (if bulk is used internally for backfills) | DEC-004 (internal-mechanism note); DEC-003 | Bulk backfills must be resumable/safe for partial failure | Official-doc verification + Implementation planning | Yes, only if/when internal bulk is used |

## 3. Job / log / error / retry

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-16 | Exact **retry-count ceilings and backoff constants** per auto-retryable class | DEC-009 (`[Implementation-planning default]`) | Under-retry loses syncs; over-retry storms the rate limit | Implementation planning | Yes |
| MBQ-17 | **Reconciliation cadence and scope** (per-object vs global; interval) | DEC-005 → DEC-009 "What remains open" | Reconciliation is the mandatory correctness backstop; cadence trades freshness vs GraphQL cost | ChatGPT (posture) + Implementation planning (constants) | Yes |
| MBQ-18 | Exact **cron cadence and throughput limits** — batch sizes, drain interval, validation under `--max-cron-threads=2` and Odoo.sh best-effort cron | DEC-005; DEC-010 | The queue must provably drain at MVP scale within hosting constraints | Implementation planning (incl. MVP-scale testing) | Yes (constants before code); throughput validation blocks release readiness, not code start |
| MBQ-19 | Exact **job/log model shape** (single job model vs job+log split; payload storage) | phase1-domain-model-brief Domain 8; Part A §D | The substrate every domain depends on; must be fixed once, early | Implementation planning | Yes |
| MBQ-20 | Exact **operation-level idempotency key schema** (field names/types for operation type, Shopify target ID, payload version/hash) | DEC-011 (conceptual shape set); Part A §D.6 | Prevents connector-side duplicate processing across all domains | Implementation planning | Yes |
| MBQ-21 | Exact **serialization-guard mechanism** for unresolved ambiguous operations (queue-level lock vs DB constraint vs job-state check) | DEC-011; Part A §D.7 | Prevents a corrected operation dispatching while a prior ambiguous one is unresolved | Implementation planning | Yes |
| MBQ-22 | Exact **user-facing copy/wording** for error reasons, suggested fixes, wizard steps, dashboard labels | DEC-009/DEC-012 (structure fixed, copy open) | Copy quality is an operator-experience differentiator; structure already fixed | Later UI-design pass | No |

## 4. Product / customer / order (routed to Sprint B)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-23 | Exact **variant-write mutation strategy** (`productSet` vs `productVariantsBulkCreate`/`productVariantsBulkUpdate` vs combination). **Partially resolved by DEC-014 acceptance (2026-07-03):** direction accepted — prefer `productVariantsBulkCreate`/`productVariantsBulkUpdate` for variant-only updates after first export, `productSet` for first-time combined export/full resync (`master-blueprint-product-customer-sale.md` §A.5.2, citing verified `productSet`/`productVariantsBulkCreate`/`productVariantsBulkUpdate` official docs, accessed 2026-07-03). Exact implementation choice remains open. | DEC-007 §1; DEC-014 | Different mutations have different delete-on-omit/partial-failure semantics | Official-doc verification + Implementation planning (direction accepted; detail remains) | Yes (product export) |
| MBQ-24 | Whether **`productSet` delete-on-omit applies to product/variant media** identically to variants/collections/metafields. **Carried forward, open (Sprint B checked, not resolved):** official `productSet` docs (accessed 2026-07-03) name `collections`/`metafields`/`variants` as list-field examples but do not name or exclude media — still unconfirmed either way. Safety posture (preview guard) applies regardless (`master-blueprint-product-customer-sale.md` §A.13). | DEC-007 §2 | Determines whether image export needs the same full-state-diff guard | Official-doc verification (Sprint B) | Yes (image export) |
| MBQ-25 | Exact **Shopify draft/publish mechanism** to key draft-first export off. **Partially resolved by DEC-014 acceptance (2026-07-03):** mechanism accepted — `Product.status` enum (`active`/`archived`/`draft`/`unlisted`) + `productCreate`'s unpublished-by-default behaviour + explicit `publishablePublish` mutation (`master-blueprint-product-customer-sale.md` §A.10, accessed 2026-07-03). Exact channel-selection UX remains open. | DEC-012 §7; DEC-014 | Draft-first export safety depends on the concrete status/channel mechanism | Official-doc verification + Implementation planning (direction accepted; detail remains) | Yes (product export) |
| MBQ-26 | **Order-import operator touchpoints** — fully covered by the error center/manual-review flow, or a dedicated order-import flow needed. **Accepted at blueprint level by DEC-014 (2026-07-03):** the existing error-center/sync-center surfaces (Part A §G/§H), extended with an inline financial-evidence breakdown and direct matching-flow links, are accepted as sufficient — **no dedicated order-import screen is authorized or required** (`master-blueprint-product-customer-sale.md` §C.14). This was ChatGPT's direct decision as MBQ-26's named decision owner. | DEC-012 (Fable, PR #68); DEC-007 §6; DEC-014 | Determines whether Sprint B adds an operator surface beyond the core error center | Resolved at blueprint level — ChatGPT via DEC-014 | No |
| MBQ-27 | Exact **mechanism for representing Shopify-computed tax** on an Odoo sale order without Odoo's tax engine recomputing/overriding, keeping totals reconcilable. **Carried forward, open (Sprint B checked, inconclusive):** an official-doc check of Odoo 19 accounting/taxes documentation (accessed 2026-07-03) confirmed a "Tax Included" price mode exists but did not resolve the manual/externally-supplied tax-amount mechanism (`master-blueprint-product-customer-sale.md` §C.17). Mechanism remains unverified. | DEC-007 §6; domain brief Domain 5 | Totals-reconcilability is a correctness requirement; mechanism unverified | Official-doc verification + Implementation planning (Sprint B) | Yes (order import) |
| MBQ-28 | **Domain 9 draft-artifact guard** — whether any draft invoice/payment artifact is absolutely required for a valid Odoo order flow. **Not triggered by Sprint B** (`master-blueprint-product-customer-sale.md` §C.11/§C.17). | DEC-003 (guard); DEC-007 §6 | If triggered, returns to ChatGPT before implementation; no silent invoice/payment creation | ChatGPT (if triggered by Sprint B/implementation planning) | Yes, if triggered |
| MBQ-29 | **Default-customer fallback** behaviour for no-PII Shopify plans. **Partially resolved by DEC-014 acceptance (2026-07-03):** direction accepted — a single, clearly-flagged fallback partner per store, used only for genuine no-PII orders, never for ordinary matching failures (`master-blueprint-product-customer-sale.md` §B.7). Whether one shared fallback partner per store is sufficient, or per-order anonymous identity is needed, remains open. | domain brief Domain 4; DEC-014 | Order import must not fail or invent PII when customer data is unavailable | Implementation planning (direction accepted; granularity remains) | Yes (customer/order import) |
| MBQ-30 | **Gateway → Odoo journal mapping** configuration surface (classification/routing input only). **Partially resolved by DEC-014 acceptance (2026-07-03):** concept accepted — a per-store gateway-label → `account.journal` mapping, classification/routing input only, contributed via the core settings-extension seam (`master-blueprint-product-customer-sale.md` §C.10). Exact schema/fields remain open. | DEC-003 Domain 9; domain brief Domain 5; DEC-014 | Config input for evidence routing; no accounting automation implied | Implementation planning (concept accepted; schema remains) | No |
| MBQ-31 | Final **customer match-key set** (email-only vs multi-key) beyond the accepted binding→email→manual order. **Accepted at blueprint level by DEC-014 (2026-07-03):** **email is the sole automatic customer match key** (beyond existing binding); phone/name stay advisory/manual-only (`master-blueprint-product-customer-sale.md` §B.13). This was ChatGPT's direct decision as MBQ-31's named decision owner. | DEC-006; domain brief Domain 4; DEC-014 | Wrong keys create duplicate partners; accepted priority stands, exact set refinable | Resolved at blueprint level — ChatGPT via DEC-014 | No |
| MBQ-55 | Exact **Odoo model/field names** for the four Sprint B-defined binding models: product-template binding, product-variant binding, customer binding, order binding | Sprint B (`master-blueprint-product-customer-sale.md` §A.1/§B.1/§C.1) | Domain-specific extension of MBQ-01/02 to the Sprint B binding models — implementation cannot start without committed names | Implementation planning | Yes |
| MBQ-56 | Exact **total-check guard tolerance/comparison mechanism** — the exact Shopify total field(s) used, currency-rounding tolerance, and which evidence components are summed | Sprint B (`master-blueprint-product-customer-sale.md` §C.8) | The total-check guard is mandatory and permanent; its exact comparison logic is not yet fixed | Implementation planning | Yes (order import) |
| MBQ-57 | Whether the **whole-order-hold rule** for an unmatched product line (§C.5) should ever have an alternative (e.g. partial-line placeholder) for a future phase | Sprint B (`master-blueprint-product-customer-sale.md` §C.5) | Recorded for future reconsideration; the current guard-consistent rule is not weakened by leaving this open | ChatGPT (future, only if revisited) | No (current rule stands unless revisited) |
| MBQ-58 | **Shopify order-identity stability nuances** beyond general GID-non-permanence (e.g. test-mode orders, draft orders later converted) | Sprint B (`master-blueprint-product-customer-sale.md` §C.3) | The existing binding-based defensive design (Part A §C.6) already covers the general case; this refines it, not a blocker | Official-doc verification | No (defensive design already stands) |
| MBQ-59 | Exact **automated (webhook/scheduled/reconciliation) import create/bind policy and preview semantics** — whether/how an automated product/customer create satisfies the accepted "no blind create" rule. **Added in PR #72 revision; revised again in the Fable-review revision; accepted at blueprint-policy level by DEC-014 (2026-07-03):** a pre-create duplicate check plus a two-tier gate — eligibility conditions (setup complete, domain enabled, source strategy permits creation) routed via Part A's accepted enqueue/cancel mechanisms (§E.5/§I.3/§I.4, never `blocked_manual_review`), and match-quality conditions (confident match or confident no-match-creation candidate; no ambiguous-match/binding-conflict/duplicate-risk/destructive-write-guard condition) routed via Part A's accepted confirmation-required `blocked_manual_review` classes (§D.5.4/§D.8) when failed — fully logged (§D.10/§C.4); retrospective sync-center/dashboard visibility is audit only, never a preview substitute (`master-blueprint-product-customer-sale.md` §A.2/§A.9/§B.2/§B.9/§C.6). Replaces this document's withdrawn earlier reading that retrospective visibility satisfied the preview requirement, and the earlier reading that every gate failure collapsed into `blocked_manual_review`. **The policy is accepted; exact eligibility-check/match-confidence implementation detail remains open for implementation planning.** | Sprint B revision (§A.2/§B.2); DEC-014; tension between DEC-003/DEC-006 "no blind create" and DEC-005 layered automation, resolved via the accepted Part A/DEC-013 per-class routing | Prevents weakening the accepted no-blind-create rule while still allowing webhook/scheduled import to operate without a synchronous per-record human click for every confident, unambiguous create, without misusing Part A's accepted state/class vocabulary | Resolved at blueprint-policy level — ChatGPT via DEC-014; exact implementation detail remains Implementation planning | Yes (exact eligibility-check/match-confidence implementation detail; policy itself no longer blocks) |

## 5. Inventory (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-32 | Exact **Odoo ORM source/field/formula behind "Free to Use"** (and whether a configurable Forecast/On-Hand/Free-to-Use default is offered). **Partially resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** two candidate sources cited against official Odoo 19.0 source (`master-blueprint-inventory-fulfillment.md` §A.4, accessed 2026-07-03) — `product.product.free_qty` (compute `product.uom_id.round(qty_available − reserved_quantity − expired_unreserved_qty)`, UoM-rounded) and per-location `stock.quant.available_quantity` (`quantity − reserved_quantity`, no UoM-rounding shown). **Fable finding C1 (corrected):** these two sources are verified but **not equivalent** — they diverge whenever expired unreserved stock exists, since only `free_qty` nets that term out; the source choice is substantive, not cosmetic, and this acceptance does not choose a final implementation source. Whether the connector reads `free_qty` via location context, aggregates `stock.quant.available_quantity` directly (and if so, how it would also net out expired-unreserved stock to match `free_qty`'s semantics), or uses a third reconciling mechanism, and whether a configurable default is offered, remain implementation planning. This row stays **open** for that residual. | DEC-010 (semantic concept decided; source unverified) | Pushing the wrong Odoo quantity to Shopify `available` over/under-sells live stock | Official-doc verification (Odoo 19 source) — **Partially resolved by DEC-015 acceptance** | Yes for the residual source-selection/aggregation-mechanism/configurable-default detail; the two candidate sources' field/formula facts are accepted as verified |
| MBQ-33 | Exact **granularity of "first"** for the first-push guard (per-store / per-binding / per-variant-location), no coarser than per-store. **Carried forward, open — DEC-015 (accepted 2026-07-03) carries a recommendation, not decided by that acceptance:** guard fires per **mapped Odoo-location ↔ Shopify-Location pair** (`master-blueprint-inventory-fulfillment.md` §A.5) — a recommendation for ChatGPT's direct decision; DEC-015's acceptance does not itself decide this row. | DEC-007 §4; DEC-010 | Fixes where the guard/confirmation record attaches | ChatGPT (Sprint C) | Yes |
| MBQ-34 | **Ongoing apply-mode** — auto-apply vs review-then-apply for post-first-push writes (C-INV-04). **Carried forward, open — DEC-015 (accepted 2026-07-03) carries a recommendation, not decided by that acceptance:** review-then-apply as the Phase 1 default, consistent with DEC-003's "auto-apply not accepted as default" (`master-blueprint-inventory-fulfillment.md` §A.7/§G) — a recommendation for ChatGPT's direct decision; DEC-015's acceptance does not itself decide this row. | DEC-003; DEC-010 | Auto-apply was explicitly not accepted as default MVP behaviour; must be decided, not assumed | ChatGPT (Sprint C) | Yes |
| MBQ-35 | Whether **`on_hand` is ever exposed as a Phase 1 UI choice** at all (requires explicit justification; `available` is the default; `committed` never). **Carried forward, open, unchanged — Sprint C introduces no new evidence** on this row (`master-blueprint-inventory-fulfillment.md` §A.4/§A.12). | DEC-010; DEC-012 §8 | Prevents mis-mapping a multi-state sum; structural exclusions already stand | ChatGPT (Sprint C) | No (default path is fixed; exposure decision needed only before any `on_hand` UI) |
| MBQ-36 | Exact **mutation choice per trigger type** (`inventorySetQuantities` preferred default vs `inventoryAdjustQuantities` for deltas). **Partially resolved by DEC-015 acceptance (2026-07-03):** direction accepted — `inventorySetQuantities` (compare-and-set) as the default for all trigger types; `inventoryAdjustQuantities` a candidate for narrower single-delta event-driven pushes only (`master-blueprint-inventory-fulfillment.md` §A.13/§G). Exact per-trigger choice, batching, and error handling remain open for implementation planning. | DEC-010 | Compare-and-set vs delta semantics differ under concurrency | Implementation planning — direction accepted by DEC-015; exact per-trigger/batching/error-handling detail remains | Yes |
| MBQ-37 | **Shopify inventory webhook topic string(s)** — unverified in repo docs. **Resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** `INVENTORY_LEVELS_UPDATE` (plus `INVENTORY_LEVELS_CONNECT`/`INVENTORY_LEVELS_DISCONNECT`), confirmed against the official Shopify `WebhookSubscriptionTopic` enum (`master-blueprint-inventory-fulfillment.md` §A.9, accessed 2026-07-03). The underlying fact is accepted as verified; this row is resolved at fact-verification level. | DEC-010; ar007-ar008-evidence-refresh | Webhook-driven import can't be built on an unverified topic; layered sync stands regardless | Official-doc verification — **Resolved by DEC-015 acceptance** | No for the topic-string fact itself; the broader payload-shape/subscription-mechanics/Phase-1-implementation-scope residual still blocks webhook-driven inventory import specifically — see MBQ-63 |
| MBQ-38 | Exact **first-push confirmation record schema** (what is persisted: preview snapshot, confirmer, source-of-truth, scope). **Partially resolved by DEC-015 acceptance (2026-07-03):** blueprint-level concept accepted — extends the Part A guard/audit record shape with a preview snapshot, confirming operator + timestamp, recorded source-of-truth, and scope (`master-blueprint-inventory-fulfillment.md` §A.5). Exact field names/schema remain open for implementation planning. | DEC-010 | The guard's audit/idempotency anchor (DEC-009 layer) | Implementation planning — concept accepted by DEC-015; exact schema/field names remain open | Yes |

## 6. Fulfillment (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-39 | Exact **Odoo tracking-reference field source** (carrier/tracking fields on `stock.picking`/delivery). **Resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** `stock.picking.carrier_tracking_ref` (Char), `carrier_tracking_url` (computed Char, via `carrier_id.get_tracking_link(picking)`), and `carrier_id` (Many2one to `delivery.carrier`), all defined in Odoo 19.0's `stock_delivery` module, cited against official Odoo source (`master-blueprint-inventory-fulfillment.md` §B.5, accessed 2026-07-03). **Surfaces new open question MBQ-60**, which remains open (whether `stock_delivery`/`delivery` is a required Odoo dependency). This row is resolved at fact-verification level. | DEC-011; ar007-ar008-evidence-refresh | Tracking write-back needs a verified source field | Official-doc verification (Odoo 19) — **Resolved by DEC-015 acceptance** | No for the tracking-field fact itself; see MBQ-60, which remains open, for the module-dependency question |
| MBQ-40 | Exact **backorder-to-picking linkage** fields/rules for sequential partial fulfillments. **Partially resolved by DEC-015 acceptance (2026-07-03):** `stock.picking.backorder_id` (Many2one, "Back Order of") and reverse `backorder_ids` (One2many) cited against official Odoo 19.0 source (`master-blueprint-inventory-fulfillment.md` §B.7, accessed 2026-07-03). The delivery-specific backorder-wizard UX/copy nuance flagged by `ar007-ar008-evidence-refresh.md` was not independently re-verified this sprint and remains open. | DEC-011 | Each backorder picking is its own fulfillment event; linkage must be exact | Official-doc verification + Implementation planning — finding accepted by DEC-015 | Yes, for the residual wizard-UX/copy detail |
| MBQ-41 | Exact **notification-UI granularity** (global/per-store minimum decided; per-order override open). **Carried forward, open — DEC-015 (accepted 2026-07-03) carries a recommendation, not decided by that acceptance:** a global/per-store default is sufficient for Phase 1 MVP; per-order override deferred to a later phase (`master-blueprint-inventory-fulfillment.md` §B.6) — a recommendation for ChatGPT's direct decision; DEC-015's acceptance does not itself decide this row. | DEC-007 §5; DEC-011 | Operator control surface for the notification guard | ChatGPT (Sprint C) | Yes (notification UI beyond the per-store default) |
| MBQ-42 | Exact **fulfillment location-confirmation mechanism** (core Shopify Location reference vs live FulfillmentOrder `assignedLocation` read, or both; live read treated as authoritative unless proven otherwise). **Partially resolved by DEC-015 acceptance (2026-07-03):** mechanism accepted — a live `assignedLocation` read is authoritative for a specific operation; the core Location reference is used only for naming/display and mismatch-detection, never as an override authority; a mismatch routes to the existing `ambiguous match` class, **its applicability widened to also cover this deterministic scenario, accepted at blueprint level only** (`master-blueprint-inventory-fulfillment.md` §B.8). Exact implementation-level detail (e.g. sub-reason tagging) remains open for implementation planning. | DEC-010/DEC-011 | Prevents fulfilling from a mismatched location without depending on inventory's mapping | Resolved at blueprint level — ChatGPT via DEC-015; exact implementation detail remains Implementation planning | Yes (exact implementation-level detail; mechanism itself no longer blocks) |
| MBQ-43 | **Core Location reference cache policy** — stale-cache handling, refresh cadence, precedence vs live reads. **Partially resolved by DEC-015 acceptance (2026-07-03):** precedence rule accepted — a live read always wins over the cache for a specific operation, cache refreshed on setup-readiness checks and the shared reconciliation cadence (`master-blueprint-inventory-fulfillment.md` §B.8). Exact refresh cadence/mechanism remains open for implementation planning. | DEC-010/DEC-011; Part A §B.4 | A stale cache must never override live Shopify state for a specific operation | Implementation planning — rule accepted by DEC-015; exact refresh cadence/mechanism remains open | Yes (fulfillment/inventory location checks) |
| MBQ-60 | Whether `shopify_connector_fulfillment` requires the Odoo **`stock_delivery`** (or `delivery`) module as a dependency for the `carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id` fields identified this sprint (§B.5), and what tracking write-back does if a merchant's database does not have that module installed | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.5), newly surfaced by this sprint's official-doc verification — not previously discussed by DEC-008's module family or DEC-011 | These fields live in an installable Odoo module distinct from core `stock`; if not installed, tracking write-back has no field to write to, and DEC-008's module family did not previously name any standard Odoo module dependency beyond core/base | ChatGPT (whether to require it) + Implementation planning (manifest dependency mechanics) | Yes (fulfillment tracking write-back) |
| MBQ-61 | Whether/how the connector must react to Shopify-side **FulfillmentOrder lifecycle events beyond simple creation** — holds (`FULFILLMENT_ORDERS_PLACED_ON_HOLD`/`HOLD_RELEASED`), cancellation-request lifecycle, merges, splits, moves, reschedules — newly confirmed as real Shopify webhook topics this sprint (§B.11) but not discussed by DEC-011 at all | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.11), newly surfaced by this sprint's official-doc verification of the full `WebhookSubscriptionTopic` enum | A FulfillmentOrder placed on hold by Shopify could silently reject or delay an Odoo-triggered `fulfillmentCreate` call if the connector has no visibility into hold state before attempting fulfillment; DEC-011 did not consider these lifecycle events at all | ChatGPT (whether/how to react) + Implementation planning | No for MVP correctness-core fulfillment creation (the existing ambiguous-outcome/manual-review handling already catches a rejected call); Yes if a dedicated hold-aware UX is later required |
| MBQ-62 | **New, Fable finding C2.** Exact **Part A §D.2 job-source classification for Odoo-side event-triggered jobs** — specifically (a) an inventory push enqueued by a relevant Odoo stock change (§A.7), and (b) a fulfillment creation triggered by a validated `stock.picking` (§B.3/§B.12). DEC-010 accepted the Odoo-side event trigger as a **sync-trigger layer**, not as an addition to Part A §D.2's fixed job-source enum (`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`); this sprint's own first draft silently listed `event-driven enqueue` as if it were one of those six values, which Fable flagged as unauthorized vocabulary extension | Sprint C (`master-blueprint-inventory-fulfillment.md` §A.7/§A.13/§B.12/§C item 7), Fable review of PR #74 — not previously decided by DEC-010, DEC-011, or Part A (DEC-013) | Every job must record a Part A job source for dashboard/sync-center display and retry-policy lookup (Part A §D.2/§F/§G); an undecided or silently-invented source value would leave these two genuinely common triggers (an Odoo stock change; a picking validation) without a defined, accepted classification | ChatGPT (whether to map to an existing source with a documented rule, or accept a DEC-level vocabulary extension) + Implementation planning | Yes for Odoo-event-triggered inventory push and fulfillment creation specifically; No for manual/scheduled/reconciliation-triggered inventory pushes or fulfillment reconciliation checks, which already have an accepted Part A source |
| MBQ-63 | **New, Fable minor finding 4.** Exact **Shopify inventory webhook payload shape and subscription mechanics** for `INVENTORY_LEVELS_UPDATE`/`INVENTORY_LEVELS_CONNECT`/`INVENTORY_LEVELS_DISCONNECT` (payload fields, required subscription scopes beyond `read_inventory`, delivery/registration mechanics), and **whether webhook-driven inventory import is implemented in Phase 1 at all** or left purely as a drift-detection candidate (§A.7/§A.9 already treat it as "candidate... never the sole mechanism," but do not decide implementation-vs-candidate-only status) | Sprint C (`master-blueprint-inventory-fulfillment.md` §A.7/§A.9), Fable review of PR #74 — MBQ-37 verified only the topic **string**, not the payload/subscription/implementation-scope residual | Building a webhook-driven import path on an unverified payload shape or unconfirmed subscription mechanics risks silent breakage; whether Phase 1 implements it at all changes what implementation planning must design for this trigger | Implementation planning, with official-doc verification | Yes, only for webhook-driven inventory import specifically; No for the layered scheduled/manual/event-driven/reconciliation inventory-sync mechanisms, which do not depend on this row |

## 7. Permissions / security

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-44 | Exact **Odoo security groups, `ir.model.access` rows, access CSVs, and record rules** for the four roles | DEC-012 §10; Part A §J | `ir.model.access` is deny-by-default; nothing works without these — but they are code artifacts, gated | Implementation planning (from the accepted §J matrix) | Yes |
| MBQ-45 | **Partially resolved by DEC-013 acceptance (2026-07-03):** the proposed role hierarchy is accepted (Admin ⊃ Operator/Reviewer ⊃ Auditor). Still open: exact **roles→groups mapping** — 1:1 vs finer-grained composition; admin-vs-functional-user dashboard/settings surface split (one role-gated surface or two) | DEC-012 §10; setup-ux-principles P10; Part A §J.1/§F.5; DEC-013 | Fixes group design before CSVs are written | Implementation planning (hierarchy confirmed; group/surface detail remains) | Yes |
| MBQ-46 | **Multi-company / multi-store permission isolation** beyond the single-store MVP's record-rule scoping | setup-ux-principles; DEC-003 | Later-phase concern; Phase 1 keys/rules must merely not preclude it | ChatGPT (later phase) | No |
| MBQ-47 | **Resolved by DEC-013 acceptance (2026-07-03):** Reviewer remains approval/manual-review focused — not a general retry/trigger role | Part A §J.2; DEC-013 | Keeps manual-review approval a distinct, auditable act | Resolved — ChatGPT via DEC-013 | No |

## 8. Deployment / operations

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-48 | **Odoo.sh vs on-prem packaging/installation** convenience details | DEC-005/DEC-008 | Install experience; not a design blocker | Implementation planning | No |
| MBQ-49 | **MVP-scale throughput validation** under `--max-cron-threads=2` (realistic catalog/order volumes) | DEC-005 | Proves the internal cron-queue suffices before release; triggers the `queue_job` revisit if not | Implementation planning (testing) | No for code start; **Yes for release readiness** |
| MBQ-50 | **OCA `queue_job` optional-accelerator adoption** — only via DEC-005's revisit triggers | DEC-005; RA-004 | Kept ready-to-adopt-later; not a Phase 1 default | ChatGPT (only if a revisit trigger fires) | No |
| MBQ-51 | Exact **GraphQL cost/throttle-aware pacing parameters** (cost budgeting, backpressure thresholds feeding the health state) | DEC-004; Part A §B.3 | Rate-limit awareness is DEC-003-mandatory; parameters unfixed | Implementation planning | Yes (transport client) |
| MBQ-52 | **Shopify API-version pinning/upgrade policy** (which version pinned per store; upgrade cadence; deprecation watch) | DEC-004; Part A §B.3 | Version drift silently changes mutation semantics (e.g. `@idempotent` requirements are version-dated) | ChatGPT (policy) + Implementation planning | Yes (transport client) |

## 9. UI/UX design

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-53 | **Screen-level UI/UX design blueprint** — screen inventory, navigation/information architecture, Odoo-native interaction patterns, screen-level wireframe specs (dashboard, setup wizard, store settings, sync center, error center, matching center, preview/review screens), empty/loading/success/error/manual-review states per screen, UX copy guidelines, error-message style, and a premium UI/UX acceptance checklist. **Proposed partially resolved by Master Blueprint Sprint D (Part D, 2026-07-03) — DEC-016 is Proposed for ChatGPT review, so this row REMAINS OPEN until DEC-016 is accepted.** Part D (`master-blueprint-ui-ux-screen-design.md`) proposes the screen-design layer in full (screen inventory §0; navigation/information architecture §1/§15; Odoo-native interaction patterns; per-screen specs for dashboard/setup-wizard/store-settings/sync-center/error-center/matching-center/preview-review screens §2–§13; empty/loading/success/error/manual-review states per screen §14; UX copy **guidelines** and error-message **style** §14; and a premium UI/UX acceptance checklist). Proposed **partially** (not fully) because MBQ-53's "UX copy guidelines" span the separate open **MBQ-22** (exact copy strings), screen implementation still needs exact identifiers (**MBQ-01/02/03/44**), the admin-vs-functional-user surface split is **MBQ-45**, and pixel wireframe artwork is out of screen-blueprint scope — none decided here. | DEC-012 (promised a later UI-design pass; "exact copy/wording... a later UI-design pass" — `ux-operator-flow.md` §5, DEC-012 "What remains open"); standing user/ChatGPT rule that premium UI/UX is a product pillar; Master Blueprint Sprint A review; **Master Blueprint Sprint D / DEC-016 (Proposed)** | The ten accepted operator flows (DEC-012) fix *behaviour*, not *screens* — premium UI/UX is a named differentiation pillar (`../02-product/product-vision.md`) and is not achieved by behavioural rules alone; without screen-level design, wireframes/specs, Odoo-native interaction rules, and explicit screen states, implementation would have to invent screen design ad hoc, risking an inconsistent or non-premium operator experience | ChatGPT + the **UI/UX Screen Design Blueprint sprint** (Master Blueprint Part D, `master-blueprint-ui-ux-screen-design.md` / DEC-016, now Proposed) | Yes, for implementation of any operator-facing screen/view/UI flow; No for Part B/C domain-blueprint authoring (concept/contract level, not screen design) |

---

## Maintenance rule

Every later blueprint part (B/C/D/E) must: (1) resolve or re-route its
assigned rows, marking resolved rows **Resolved (date, by, where)** rather
than deleting them; (2) add newly discovered questions here with the next
free ID; (3) never let a "Blocks implementation: Yes" row be silently
dropped — per `../05-qa/quality-feedback-loop.md` §11 and `CLAUDE.md` §7.
