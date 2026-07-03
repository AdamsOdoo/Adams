# Master Blueprint — Open Questions Register

> Central register of unresolved **Master Blueprint / implementation-planning
> questions** for the premium **Odoo 19 ↔ Shopify Connector**. Created in
> Master Blueprint Sprint A; **updated by every later blueprint part**.
> Companion index: [`master-blueprint.md`](./master-blueprint.md). Companion
> Part A blueprint:
> [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md).

## Status

**Accepted as the central register through DEC-013**, acceptance date
**2026-07-03**. Documentation only; the no-code gate (`CLAUDE.md` §4–§5)
is in force. **Register acceptance does not resolve every question** —
each MBQ row remains open unless the row itself says **Resolved** or
**Partially resolved**; notably **MBQ-04, MBQ-08, MBQ-53, and MBQ-54
remain open**. Registering (or accepting the register containing) a
question does **not** decide it and does **not** authorize
implementation. Every row follows `CLAUDE.md` §7/§8: unverified items
are **open questions**, never asserted.

> **Master Blueprint Sprint B note (2026-07-03, revised after PR #72
> review).** Sprint B
> ([`master-blueprint-product-customer-sale.md`](./master-blueprint-product-customer-sale.md),
> companion
> [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md))
> has **proposed** updates to the product/customer/order rows below
> (MBQ-23 through MBQ-31) and added MBQ-55 through MBQ-59 (MBQ-59 added
> in the PR #72 revision — see MBQ-59's own row). **These are proposed
> resolutions/partial resolutions only, pending DEC-014 acceptance by
> ChatGPT** — none is final yet; the register's accepted-through-DEC-013
> status is otherwise unchanged, and MBQ-04, MBQ-08, MBQ-53, and MBQ-54
> remain untouched and open.

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
| MBQ-23 | **Proposed partially resolved (Sprint B, pending DEC-014):** direction proposed — prefer `productVariantsBulkCreate`/`Update` for variant-only updates after first export, `productSet` for first-time combined export/full resync (`master-blueprint-product-customer-sale.md` §A.5.2, citing verified `productSet`/`productVariantsBulkCreate` official docs, accessed 2026-07-03). Exact implementation choice remains open. | DEC-007 §1 | Different mutations have different delete-on-omit/partial-failure semantics | Official-doc verification + Implementation planning (Sprint B) | Yes (product export) |
| MBQ-24 | **Carried forward, open (Sprint B checked, not resolved):** official `productSet` docs (accessed 2026-07-03) name `collections`/`metafields`/`variants` as list-field examples but do not name or exclude media — still unconfirmed either way. Safety posture (preview guard) applies regardless (`master-blueprint-product-customer-sale.md` §A.13). | DEC-007 §2 | Determines whether image export needs the same full-state-diff guard | Official-doc verification (Sprint B) | Yes (image export) |
| MBQ-25 | **Proposed partially resolved (Sprint B, pending DEC-014):** mechanism identified and cited — `Product.status` enum (`active`/`archived`/`draft`/`unlisted`) + `productCreate`'s unpublished-by-default behaviour + explicit `publishablePublish` mutation (`master-blueprint-product-customer-sale.md` §A.10, accessed 2026-07-03). Exact channel-selection UX remains open. | DEC-012 §7 | Draft-first export safety depends on the concrete status/channel mechanism | Official-doc verification (Sprint B) | Yes (product export) |
| MBQ-26 | **Proposed resolution (Sprint B, pending DEC-014):** recommend the existing error-center/sync-center surfaces (Part A §G/§H), extended with an inline financial-evidence breakdown and direct matching-flow links, are sufficient — no dedicated order-import screen proposed (`master-blueprint-product-customer-sale.md` §C.14). This is a recommendation for ChatGPT's acceptance, not self-decided. | DEC-012 (Fable, PR #68); DEC-007 §6 | Determines whether Sprint B adds an operator surface beyond the core error center | ChatGPT (Sprint B) | Yes (order domain) |
| MBQ-27 | **Carried forward, open (Sprint B checked, inconclusive):** an official-doc check of Odoo 19 accounting/taxes documentation (accessed 2026-07-03) confirmed a "Tax Included" price mode exists but did not resolve the manual/externally-supplied tax-amount mechanism (`master-blueprint-product-customer-sale.md` §C.17). Mechanism remains unverified. | DEC-007 §6; domain brief Domain 5 | Totals-reconcilability is a correctness requirement; mechanism unverified | Official-doc verification + Implementation planning (Sprint B) | Yes (order import) |
| MBQ-28 | **Domain 9 draft-artifact guard** — whether any draft invoice/payment artifact is absolutely required for a valid Odoo order flow. **Not triggered by Sprint B** (`master-blueprint-product-customer-sale.md` §C.11/§C.17). | DEC-003 (guard); DEC-007 §6 | If triggered, returns to ChatGPT before implementation; no silent invoice/payment creation | ChatGPT (if triggered by Sprint B/implementation planning) | Yes, if triggered |
| MBQ-29 | **Proposed partially resolved (Sprint B, pending DEC-014):** direction proposed — a single, clearly-flagged fallback partner per store, used only for genuine no-PII orders, never for ordinary matching failures (`master-blueprint-product-customer-sale.md` §B.7). Whether one shared fallback partner per store is sufficient, or per-order anonymous identity is needed, remains open. | domain brief Domain 4 | Order import must not fail or invent PII when customer data is unavailable | Implementation planning (Sprint B) | Yes (customer/order import) |
| MBQ-30 | **Proposed partially resolved (Sprint B, pending DEC-014):** concept proposed — a per-store gateway-label → `account.journal` mapping, classification/routing input only, contributed via the core settings-extension seam (`master-blueprint-product-customer-sale.md` §C.10). Exact schema/fields remain open. | DEC-003 Domain 9; domain brief Domain 5 | Config input for evidence routing; no accounting automation implied | Implementation planning (Sprint B) | No |
| MBQ-31 | **Proposed resolution (Sprint B, pending DEC-014):** recommend **email as the sole automatic customer match key** (beyond existing binding); phone/name stay advisory/manual-only (`master-blueprint-product-customer-sale.md` §B.13). This is a recommendation for ChatGPT's acceptance, not self-decided. | DEC-006; domain brief Domain 4 | Wrong keys create duplicate partners; accepted priority stands, exact set refinable | ChatGPT (Sprint B) | Yes (customer matching) |
| MBQ-55 | Exact **Odoo model/field names** for the four Sprint B-defined binding models: product-template binding, product-variant binding, customer binding, order binding | Sprint B (`master-blueprint-product-customer-sale.md` §A.1/§B.1/§C.1) | Domain-specific extension of MBQ-01/02 to the Sprint B binding models — implementation cannot start without committed names | Implementation planning | Yes |
| MBQ-56 | Exact **total-check guard tolerance/comparison mechanism** — the exact Shopify total field(s) used, currency-rounding tolerance, and which evidence components are summed | Sprint B (`master-blueprint-product-customer-sale.md` §C.8) | The total-check guard is mandatory and permanent; its exact comparison logic is not yet fixed | Implementation planning | Yes (order import) |
| MBQ-57 | Whether the **whole-order-hold rule** for an unmatched product line (§C.5) should ever have an alternative (e.g. partial-line placeholder) for a future phase | Sprint B (`master-blueprint-product-customer-sale.md` §C.5) | Recorded for future reconsideration; the current guard-consistent rule is not weakened by leaving this open | ChatGPT (future, only if revisited) | No (current rule stands unless revisited) |
| MBQ-58 | **Shopify order-identity stability nuances** beyond general GID-non-permanence (e.g. test-mode orders, draft orders later converted) | Sprint B (`master-blueprint-product-customer-sale.md` §C.3) | The existing binding-based defensive design (Part A §C.6) already covers the general case; this refines it, not a blocker | Official-doc verification | No (defensive design already stands) |
| MBQ-59 | **Added in PR #72 revision.** **Proposed, pending DEC-014:** exact **automated (webhook/scheduled/reconciliation) import create/bind policy and preview semantics** — a pre-create duplicate check plus a six-condition auto-create gate (setup complete, domain enabled, source strategy permits creation, confident/unambiguous match, no duplicate-risk/binding-conflict/destructive-write-guard condition triggered, fully logged); retrospective sync-center/dashboard visibility is audit only, never a preview substitute (`master-blueprint-product-customer-sale.md` §A.2/§A.9/§B.2/§B.9). Replaces this document's withdrawn earlier reading that retrospective visibility satisfied the preview requirement. | Sprint B revision (§A.2/§B.2); tension between DEC-003/DEC-006 "no blind create" and DEC-005 layered automation | Prevents weakening the accepted no-blind-create rule while still allowing webhook/scheduled import to operate without a synchronous per-record human click for every confident, unambiguous create | ChatGPT (at DEC-014 review) + Implementation planning | Yes (automated product/customer create-bind flows) |

## 5. Inventory (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-32 | Exact **Odoo ORM source/field/formula behind "Free to Use"** (and whether a configurable Forecast/On-Hand/Free-to-Use default is offered) | DEC-010 (semantic concept decided; source unverified) | Pushing the wrong Odoo quantity to Shopify `available` over/under-sells live stock | Official-doc verification (Odoo 19 source) — Sprint C | Yes |
| MBQ-33 | Exact **granularity of "first"** for the first-push guard (per-store / per-binding / per-variant-location), no coarser than per-store | DEC-007 §4; DEC-010 | Fixes where the guard/confirmation record attaches | ChatGPT (Sprint C) | Yes |
| MBQ-34 | **Ongoing apply-mode** — auto-apply vs review-then-apply for post-first-push writes (C-INV-04) | DEC-003; DEC-010 | Auto-apply was explicitly not accepted as default MVP behaviour; must be decided, not assumed | ChatGPT (Sprint C) | Yes |
| MBQ-35 | Whether **`on_hand` is ever exposed as a Phase 1 UI choice** at all (requires explicit justification; `available` is the default; `committed` never) | DEC-010; DEC-012 §8 | Prevents mis-mapping a multi-state sum; structural exclusions already stand | ChatGPT (Sprint C) | No (default path is fixed; exposure decision needed only before any `on_hand` UI) |
| MBQ-36 | Exact **mutation choice per trigger type** (`inventorySetQuantities` preferred default vs `inventoryAdjustQuantities` for deltas) | DEC-010 | Compare-and-set vs delta semantics differ under concurrency | Implementation planning (Sprint C) | Yes |
| MBQ-37 | **Shopify inventory webhook topic string(s)** — unverified in repo docs | DEC-010; ar007-ar008-evidence-refresh | Webhook-driven import can't be built on an unverified topic; layered sync stands regardless | Official-doc verification (Sprint C) | Yes, only for webhook-driven inventory import |
| MBQ-38 | Exact **first-push confirmation record schema** (what is persisted: preview snapshot, confirmer, source-of-truth, scope) | DEC-010 | The guard's audit/idempotency anchor (DEC-009 layer) | Implementation planning (Sprint C) | Yes |

## 6. Fulfillment (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-39 | Exact **Odoo tracking-reference field source** (carrier/tracking fields on `stock.picking`/delivery) | DEC-011; ar007-ar008-evidence-refresh | Tracking write-back needs a verified source field | Official-doc verification (Odoo 19) — Sprint C | Yes |
| MBQ-40 | Exact **backorder-to-picking linkage** fields/rules for sequential partial fulfillments | DEC-011 | Each backorder picking is its own fulfillment event; linkage must be exact | Official-doc verification + Implementation planning (Sprint C) | Yes |
| MBQ-41 | Exact **notification-UI granularity** (global/per-store minimum decided; per-order override open) | DEC-007 §5; DEC-011 | Operator control surface for the notification guard | ChatGPT (Sprint C) | Yes (notification UI beyond the per-store default) |
| MBQ-42 | Exact **fulfillment location-confirmation mechanism** (core Shopify Location reference vs live FulfillmentOrder `assignedLocation` read, or both; live read treated as authoritative unless proven otherwise) | DEC-010/DEC-011 | Prevents fulfilling from a mismatched location without depending on inventory's mapping | ChatGPT (Sprint C) + Implementation planning | Yes |
| MBQ-43 | **Core Location reference cache policy** — stale-cache handling, refresh cadence, precedence vs live reads | DEC-010/DEC-011; Part A §B.4 | A stale cache must never override live Shopify state for a specific operation | Implementation planning (Sprint C) | Yes (fulfillment/inventory location checks) |

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
| MBQ-53 | **Screen-level UI/UX design blueprint** — screen inventory, navigation/information architecture, Odoo-native interaction patterns, screen-level wireframe specs (dashboard, setup wizard, store settings, sync center, error center, matching center, preview/review screens), empty/loading/success/error/manual-review states per screen, UX copy guidelines, error-message style, and a premium UI/UX acceptance checklist | DEC-012 (promised a later UI-design pass; "exact copy/wording... a later UI-design pass" — `ux-operator-flow.md` §5, DEC-012 "What remains open"); standing user/ChatGPT rule that premium UI/UX is a product pillar; Master Blueprint Sprint A review | The ten accepted operator flows (DEC-012) fix *behaviour*, not *screens* — premium UI/UX is a named differentiation pillar (`../02-product/product-vision.md`) and is not achieved by behavioural rules alone; without screen-level design, wireframes/specs, Odoo-native interaction rules, and explicit screen states, implementation would have to invent screen design ad hoc, risking an inconsistent or non-premium operator experience | ChatGPT + a later **UI/UX Screen Design Blueprint sprint** (Master Blueprint Part D, see `master-blueprint.md`) | Yes, for implementation of any operator-facing screen/view/UI flow; No for Part B/C domain-blueprint authoring (concept/contract level, not screen design) |

---

## Maintenance rule

Every later blueprint part (B/C/D/E) must: (1) resolve or re-route its
assigned rows, marking resolved rows **Resolved (date, by, where)** rather
than deleting them; (2) add newly discovered questions here with the next
free ID; (3) never let a "Blocks implementation: Yes" row be silently
dropped — per `../05-qa/quality-feedback-loop.md` §11 and `CLAUDE.md` §7.
