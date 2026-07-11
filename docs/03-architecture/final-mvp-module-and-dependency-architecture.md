# Final MVP Module and Dependency Architecture

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-10 by the MVP planning-completion session (AR-042
> candidate). This document consolidates the accepted architecture
> decisions (DEC-005/006/008/009/010/011/013/014/015/018/019/020, the
> AR-019 naming plan, and the merged Tasks 001–011 code) into one
> final, evidence-backed module/dependency/data-ownership/sync-direction/
> reliability reference for the remaining MVP work, and proposes the
> small set of genuinely new architecture points (marked **[Proposed
> decision]**). Accepting this document (with the AR-042 package)
> ratifies those proposed points at planning level only — **it opens no
> gate and authorizes no implementation.** Everything already accepted
> is restated with its source and is not re-decided here.

## 1. Final module map

| # | Module | Exists? | MVP | Edition (per `../02-product/lite-full-packaging-final-proposal.md`) | Odoo depends | Connector depends |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `shopify_connector_core` | **Merged** (v19.0.1.5.0) | Yes | Lite + Full | `base` | — |
| 2 | `shopify_connector_product` | **Merged** (import slice) | Yes | Lite + Full | `product` | core |
| 3 | `shopify_connector_sale` | **Merged** (customer slice) | Yes | Lite + Full | `sale` *(added by Task 012 — see §1.2)* | core; **+ product (added by Task 012)** |
| 4 | `shopify_connector_inventory` | No — created by Task 013 | Yes | **Full only** | `stock` | core + product |
| 5 | `shopify_connector_fulfillment` | No — created by Task 014 | Yes | **Full only** | `stock_delivery`, **`sale_stock`** (red-team-added: `picking.sale_id`, `move.sale_line_id`, and SO-confirmation picking generation all live in the `sale_stock` bridge module — an undeclared hard dependency would leave fulfillment dead code) | core + sale |
| 6 | `shopify_connector_product_export` | No — created by Task 015 | Yes (MVP write-back half of the product domain, DEC-003/PR #55) | **Full only** | — (inherits product's) | core + product — **[Proposed decision PD-1, §1.1]** |
| 7 | `shopify_connector_accounting` / `_refund` / `_payout` / `_multi_store` | No | **No — Phase 2/3** (DEC-003 deferrals) | Future add-ons | t.b.d. | t.b.d. at their own architecture pass |
| 8 | Public-app auth/compliance surfaces (working name `shopify_connector_oauth`) | No | **No — Phase 2+** (DEC-026, RA-003 not lifted) | Distribution layer, not an edition | t.b.d. | core |

**Core's breadth is intentional (red-team-acknowledged):** core is the
deliberate substrate hub — transport, credentials, store lifecycle,
jobs/logs/dispatch, binding mixin, and (via the core-owned tasks) the
shared UI surfaces, job-action services, readiness slots, and the W1
webhook receiver. The accepted "no giant connector module" rule
targets domain capability sprawl, not the substrate; domain logic
never migrates into core, and core never contains domain
mapping/matching/mutation logic — that boundary, not file count, is
the enforced invariant.

**UI ownership [Proposed decision PD-2]:** there is **no separate UI
module**. Views/menus/actions live in the module that owns their
models: core owns the shared surfaces (Dashboard S3, Sync Center S4,
Error Center S5, Store form/settings S2, wizard S1, Roles page S14);
each domain module contributes its own screens/extensions (product:
Matching Center S6; product_export: Preview/Diff S7; sale: Customer
Matching S8 + the two accepted Error-Center order extensions S9;
inventory: S10/S11/S12; fulfillment: S13 sub-surfaces) by inheriting
the shared surfaces — the accepted "domain modules contribute, never
fork" rule (RA-013/DEC-016) made structural. A separate UI module would
invert the DAG (it would need every domain) — rejected here for that
reason. Consequence: each future UI implementation phase touches only
the owning module's `views/` files.

**Webhook ownership (restated, accepted):** core exclusively owns the
future webhook receiver (HMAC verify, fast-ack, `X-Shopify-Webhook-Id`
dedup, enqueue-only — Part A §A.5.7/DEC-005); domain modules register
topics via a seam. No webhook code exists or is authorized; the phased
plan is `../07-implementation-plan/webhook-implementation-packets.md`.

### 1.1 PD-1 — Task 015 as its own module `shopify_connector_product_export`

**[Proposed decision]** Controlled product export/update (Task 015)
ships as its own installable module depending on `core + product`, not
as files inside `shopify_connector_product`.

Reasons: (1) it is the Lite/Full edition boundary for the product
domain — a module boundary enforces it with standard Odoo packaging,
no license code (see the packaging proposal §4); (2) write-risk
isolation — every Shopify **mutation** the connector ever performs on
catalog data lives in one uninstallable unit, and removing it provably
removes all catalog write capability while leaving import bindings and
data intact; (3) it preserves the twice-proven zero-edit seam pattern —
Task 015's allowlist stays disjoint from the merged, runtime-green
import files. Relationship to DEC-008 (which assigned import **and**
controlled export/update responsibility to the product domain): the
domain responsibility is unchanged — this refines the domain into two
modules along the read/write boundary, exactly the split PR #93's
REVISE already made at task level. Checked against
`../05-qa/rejected-approaches-log.md`: this is neither "one giant
module" nor the rejected over-fragmentation pattern (it follows a
capability seam with a real packaging/security payoff); no rejected
approach is being reintroduced.

### 1.2 Task 012 manifest deltas (sale module)

**[Proposed decision PD-3]** Task 012 changes
`shopify_connector_sale`'s manifest depends from
`['shopify_connector_core']` to
`['shopify_connector_core', 'shopify_connector_product', 'sale']` —
exactly the deferred half of Task 011's D6 ("Task 012 adds both").
`sale` is required for `sale.order`; `shopify_connector_product` is
required because order-line resolution consumes the product-variant
binding (sibling reuse, Part A §K.9).

## 2. Dependency DAG

```
Odoo apps:        base      product       sale        stock     stock_delivery
                    │           │           │            │            │
MVP Lite:   shopify_connector_core ──► shopify_connector_product ──► shopify_connector_sale
                    ▲                        ▲                            (customer + order)
                    │                        │
MVP Full adds:      ├── shopify_connector_inventory  (core + product + stock)
                    ├── shopify_connector_fulfillment (core + sale + stock_delivery + sale_stock)
                    └── shopify_connector_product_export (core + product)
Phase 2/3 add-ons: accounting / refund / payout / multi_store  (own future pass)
Phase 2+ distribution: oauth/compliance surfaces (core)         (RA-003-gated)
```

Rules (all restated from DEC-008, binding): strict one-directional
DAG; `sale` and `inventory` are siblings (neither depends on the
other); **`fulfillment` never depends on `inventory`** and must not
read inventory's location-mapping table; nothing depends on
`adams_base`; no module other than core touches transport, credential,
job, log, or readiness code. New edges introduced here: `sale → product`
(Task 012, PD-3) and `product_export → product` (PD-1). There are no
cycles: core ← product ← {sale, inventory, product_export}; sale ←
fulfillment. Verified by inspection — every edge points strictly toward
core.

## 3. Data ownership and binding map (final)

One concrete binding model per synchronized root entity, on the merged
abstract `shopify.connector.binding.mixin` (DEC-013 §C.8). Merged
models are [Verified repository state]; planned models are
**[Proposed decision PD-4]** at exact-name level (the MBQ-55
order/inventory/fulfillment portions), following the accepted naming
precedent (`shopify.connector.<entity>.binding`, explicit
`_name`+`_inherit`, required indexed `ondelete='restrict'` link to the
Odoo record, dual `models.Constraint` uniqueness, readonly snapshots,
no shadow copies, ambiguous matches never create rows).

| Binding model | Module | Odoo record link | Uniqueness (both per model) | Status |
| --- | --- | --- | --- | --- |
| `shopify.connector.product.template.binding` | product | `product_template_id` | (store_id, shopify_gid) + (store_id, product_template_id) | **Merged** |
| `shopify.connector.product.variant.binding` | product | `product_variant_id` (+ required `product_template_binding_id`) | (store_id, shopify_gid) + (store_id, product_variant_id) | **Merged** |
| `shopify.connector.customer.binding` | sale | `partner_id` | (store_id, shopify_gid) + (store_id, partner_id) | **Merged** |
| `shopify.connector.order.binding` | sale (Task 012) | `sale_order_id` | (store_id, shopify_gid) + (store_id, sale_order_id) | Proposed (packet §7) |
| `shopify.connector.location.mapping` | inventory (Task 013) | `odoo_location_id` ↔ mixin `shopify_gid` (= Shopify Location GID) | (store_id, odoo_location_id) + (store_id, shopify_gid) — one-to-one, non-inferred (DEC-010) | Proposed (packet §7) |
| `shopify.connector.inventory.level.binding` | inventory (Task 013) | `product_variant_binding_id` + `location_mapping_id` | (store_id, shopify_inventory_item_gid, location_mapping_id); `shopify_gid` carries the InventoryLevel GID once known — **deliberate mixin deviation (red-team-confirmed): this one binding overrides `shopify_gid` to `required=False`** (the GID exists only after activation/first read; the mixin declares it required) and relies on the item+location key, not `(store, shopify_gid)`, as its identity | Proposed (packet §7) |
| `shopify.connector.fulfillment.binding` | fulfillment (Task 014) | `picking_id` (`stock.picking`) | (store_id, shopify_gid = Fulfillment GID) + (store_id, picking_id) | Proposed (packet §7) |

Deliberate non-bindings (unchanged): **no order-line binding model**
(DEC-013 granularity bound — order lines resolve through the
product-variant binding; Task 012 adds a plain audit/traceability Char
field `shopify_line_item_gid` on `sale.order.line` via `_inherit`,
which is a reference field, not a binding model — flagged for review
as part of the Task 012 packet, not silently assumed); **no partner
shadow fields**; **no snapshot of authoritative Odoo data** in any
binding. Fulfillment-binding keying note — **this is a proposed revision of
accepted content, not the filling of an open detail**: the accepted
blueprint (Part C, `[Accepted — DEC-006; DEC-011; Part A §C.8]`,
`master-blueprint-inventory-fulfillment.md`) keys the fulfillment
binding on "(store, Shopify FulfillmentOrder GID) (and the Fulfillment
GID once created)". That accepted key breaks on a backorder chain: two
pickings partially fulfilling one FulfillmentOrder would collide on
FO-GID uniqueness, contradicting the equally-accepted rule that each
validated picking (incl. backorder splits) is an independent
fulfillment event (DEC-011). The proposed revision anchors on the
**created Fulfillment GID** plus `(store, picking)` uniqueness, with
FulfillmentOrder GIDs demoted to an audit field. Because this
overrides part of DEC-006/DEC-011/Part-A-§C.8-accepted identity
content, it is routed through architecture review explicitly (the
AR-042 row names it; master plan §1 call 4 asks for the ratification;
detail in the Task 014 packet §2, D-014-1) — ChatGPT is being asked
to revise an acceptance, not merely to confirm a naming.

## 4. Sync-direction matrix (final, MVP)

| Entity | Direction | Source of truth | First-sync matching | Ongoing conflict | Deletion/archive (remote) | Retry | Reconciliation | Manual review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Product/variant | Shopify→Odoo (import, merged); Odoo→Shopify (controlled export, Task 015, Full) | Import: Shopify for imported snapshots; Export: per-store `price_source_of_truth` + explicit field allowlist | binding → SKU → barcode → manual (merged) | Import refresh never destroys Odoo edits outside imported fields; export requires preview + confirmation (destructive-write guard) | Shopify archive/delete → binding `stale`/review, never auto-delete Odoo product; `PRODUCTS_DELETE` webhook never deletes (DEC-020) | Class-conditional (DEC-009) | Product reconciliation re-verifies snapshots (Area 6) | ambiguous/blind → no row, review |
| Customer | Shopify→Odoo only (merged) | Shopify for imported identity fields at create; Odoo record otherwise (never overwritten) | binding → normalized email (sole auto key) → manual (merged) | Existing partners never mutated by import (merged behavior) | Shopify delete → binding stale/review | Same | Customer reconciliation (Area 6) | ambiguous/missing-email/archived-only → review paths (merged) |
| Order | Shopify→Odoo only | Shopify is the factual source of the commercial event; the Odoo SO is the operational record | Never auto-matched to pre-existing SOs: existing binding → else create; manual bind possible | `ORDERS_UPDATED`/reconciliation = evidence refresh ONLY; never mutates imported SO lines/amounts (DEC-014 J) | Shopify cancel → status snapshot + note, SO untouched pending operator action; archived/closed → snapshot only | Whole-order-hold on `mapping missing` (failed_retryable); total-check mismatch conservative-never-silent | Order reconciliation re-verifies totals via total-check guard | ambiguous customer (assignment only), duplicate risk, financial mismatch, divergent currency |
| Inventory | Odoo→Shopify standing; one-time reviewed Shopify→Odoo baseline allowed | **Odoo** (DEC-010) | First-push guard: mapped location + preview + confirmation + recorded SoT + skip/manual-match (per mapped pair, MBQ-33/DEC-018) | No autonomous bidirectional resolution (RA-020); CAS mismatch → fresh read + auto-retry | Shopify location deactivated → `inventory location missing` review; never auto-remap | CAS/`@idempotent` retries safe; races auto-retry | Inventory reconciliation compares last-pushed vs current Shopify `available`, flags drift | unmapped/ambiguous location, first-push unconfirmed |
| Fulfillment | Odoo→Shopify only | Odoo picking validation is the triggering fact | n/a (create-only against open FulfillmentOrders) | Tracking updates via `fulfillmentTrackingInfoUpdate` only (never a second fulfillment) | Shopify FO cancelled/closed before create → review | **Never blind-retry** (not `@idempotent`): verification read first (RA-014) | Fulfillment reconciliation re-verifies Fulfillment status/tracking | unmatched picking, location mismatch, notification confirmation, binding conflict |

## 5. Reliability architecture (planning contract, consolidated)

All items below are accepted and merged unless marked otherwise;
sources: DEC-005/009/013, AR-019, merged core code (read 2026-07-10).

1. **Jobs/logs:** every business operation is a
   `shopify.connector.job` (7 `job_source` values incl. `odoo_event` +
   `trigger_origin`; 10 states; fixed 16-class `error_class` registry —
   no 17th class, ever, without a DEC); append-only
   `shopify.connector.job.log` via `_system_append` with redaction.
2. **Retry/backoff:** class-conditional routing (AUTO_RETRY /
   MANUAL_FIX_THEN_RETRY / CONSERVATIVE_NEVER_SILENT /
   MANUAL_REVIEW / SAFETY_NET); constants are merged adjustable
   defaults (12 attempts, 30 s base, ×2, 1800 s cap, 20 % jitter, 24 h
   window); ambiguous-outcome rule for non-`@idempotent` writes:
   verification read or manual review, never blind retry.
3. **Idempotency layers:** binding uniqueness (sole idempotency anchor
   per entity) → job `idempotency_key` + `operation_scope_key`
   serialization guard → Shopify-side `@idempotent(key:)` where it
   exists. **[Fact — 2026-07-10]** `@idempotent` is **required** on
   `inventorySetQuantities`/`inventoryAdjustQuantities` as of API
   2026-04 (UUID key per operation attempt, persisted with the job);
   no product or fulfillment write mutation carries `@idempotent` —
   their idempotency comes from bindings + verification reads.
4. **Atomicity/partial failure:** per-record `env.cr.savepoint()`
   isolation (merged importer pattern); batch size 20 (below the
   64-savepoint ceiling, SRR-01); one entity per job — an order import
   job commits the SO + lines + binding + evidence in one savepoint or
   routes to a failure class, never half-imports.
5. **Checkpoints/pagination [Proposed decision PD-5 — closes Q7]:**
   checkpoint state is **domain-owned**, stored as per-domain fields on
   the store settings extension (`<domain>_last_import_checkpoint_at`,
   Datetime, UTC), written only after a fully-committed page batch.
   Enumeration follows the accepted Task 011 D7 posture generalized:
   query `sortKey: UPDATED_AT`, filter `updated_at:>checkpoint −
   overlap`, pages of ≤100 (`first:100`), cursors used **within one
   enumeration run only — never persisted** (GraphQL cursor durability
   is officially undocumented, Q10); a fixed overlap window (default
   10 minutes, constant, adjustable) absorbs timestamp-granularity and
   clock-skew risk; re-reads are harmless by idempotency (bindings).
   Core provides no generic checkpoint primitive in MVP — revisit if a
   third domain duplicates >30 lines of checkpoint logic.
6. **Rate limiting:** the merged client already surfaces
   `throttleStatus` verbatim; THROTTLED/429 → `ERROR_THROTTLE` →
   AUTO_RETRY with backoff (merged). **[Fact]** bucket maxima are
   unpublished by design — pacing reads `maximumAvailable` at runtime;
   single-query cap 1,000 points; input arrays ≤250. No per-domain
   pacing constants are fixed in MVP (MBQ-51 stays
   implementation-planning; the dashboard shows the client's
   `api_health_state`).
7. **Replay/dead-letter/manual review:** `failed_final` after
   retry-budget exhaustion; `blocked_manual_review` with the six fixed
   sub-reasons; operator retry/requeue is Area 6 + UI scope; no force
   bypass exists anywhere (merged invariant).
8. **Duplicate prevention:** two accepted paths (interactive preview;
   automated two-tier MBQ-59 gate) + binding/idempotency constraints +
   webhook `X-Shopify-Webhook-Id` dedup when webhooks arrive (the W1
   slice — MVP tail per the webhook packet).
   **Dual-hook note (red-team-added):** validating one outgoing
   delivery fires both the Task-013 stock-change push hook and the
   Task-014 fulfillment hook — two independent jobs on one event with
   no ordering contract; eventual consistency is by design
   (absolute-set CAS pushes + each domain's reconciliation), and the
   two domains share no state (the structural isolation holds).
9. **Observability/audit:** job/log surface is the operator signal
   (`ir.cron._notify_admin` is a no-op by default — Q19 closed by
   confirming the documented assumption: the connector does not
   override it in MVP; the Error/Sync Centers are the alarm surface);
   every state transition logged; binding audit fields; OP-43 rule:
   quote runtime logs verbatim.
10. **PII redaction:** merged `redact()` on every log write; Task 012
    extends the redaction field list for order payloads (packet §7);
    webhook payload PII list is proposed in the webhook packet
    (closes Q23 at planning level).
11. **Performance budgets:** MVP explicitly defers hard budgets;
    the concurrency plan's §13.2 performance captures (added this
    session) establish the baseline; release hardening (Area 8) owns
    budget-setting against real volumes.
12. **Concurrency caveat (standing, verbatim requirement):** the
    claim/dispatch mechanism is **not proven under real
    concurrent-worker/multi-server execution** (SRR-03/04/09;
    OP-22 external validation). Every packet carries this caveat until
    the concurrency plan is executed.

## 6. API version posture (all remaining tasks)

**[Proposed decision PD-6]** All Task 012–015/Area-6 planning pins
**API version 2026-07** (latest stable, supported until 2027-07-16;
store records already exercise `2026-07`). Consequences baked into the
packets: `changeFromQuantity` CAS shape (not `compareQuantity`);
mandatory `@idempotent(key:)` on inventory set/adjust;
`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` (never V2/legacy);
`productSet` list-field delete-on-omit semantics; forward-watch items
for 2026-10 recorded in the release plan
(`FULFILLMENT_NOT_REQUIRED` enum value; `ITEM_NOT_STOCKED_AT_LOCATION`
removal). Per MBQ-52 (accepted), the version is pinned per release and
re-checked quarterly.

## 7. Extension seams (merged, the only sanctioned integration points)

1. `job_type` `selection_add` (+ `ondelete='cascade'`);
2. `_domain_flag_for_job_type()` override → domain-enable flag;
3. `_get_handlers()` dict-update override (one handler per job type);
4. store-settings `_inherit` field extension;
5. readiness `_get_checks()` append seam (first consumed by Task 013's
   mapped-location check — filling the merged pending slot);
6. `shopify.connector.job.enqueue.enqueue()` (first consumed by
   Area 6 trigger call sites);
7. the binding mixin.

No new seam is proposed beyond the two named below. Core-touchpoint
rule, stated precisely (red-team-corrected — the earlier
"single sanctioned exception" wording undercounted): **domain-module
tasks never edit existing core/product files**, with exactly **two**
named exceptions in this package — Task 014's TD-002
`REQUIRED_MVP_SCOPES` constant swap, and Task 012's additive
`JobPolicySkip` dispatcher seam (new exception class + one
except-branch; needed because the merged dispatcher marks any
normally-returning handler `succeeded`, so no handler-reachable
`skipped` path exists without it). **Core-owned tasks** (Area 6 /
"Task 016" — job-action services + readiness-slot closure; W1 —
webhook receiver; U1 — core views) add or edit core files **by
design**, each with an exhaustive named allowlist in its packet; they
are core work, not domain work.

## 8. Install / uninstall / data-survival contract

- Editions install module sets (packaging proposal §4); **operational
  disablement is always the domain flags** (merged
  `*_domain_enabled`), never uninstall (MBQ-54/DEC-018 accepted
  posture, restated).
- **Uninstall reality (red-team-corrected — the earlier "graceful
  cascade" claim was mechanically false):** the merged domain modules
  extend `job_type` with `selection_add … ondelete='cascade'`, and
  Odoo's selection-unlink cascade tries to `unlink()` every job of
  that type — but every executed job has append-only
  `shopify.connector.job.log` children with **`ondelete='restrict'`**
  (deliberate audit-history design). Uninstalling a domain module
  that has ever executed a job therefore **fails on the FK
  restriction**; it succeeds only on a database where that domain
  never ran. Consequence, aligned with the already-accepted MBQ-54
  posture: **disable-not-uninstall is the only supported removal path
  once a domain has run.** Business data (partners, products, sale
  orders, pickings, stock) is never at risk either way
  (`ondelete='restrict'` links). A future core decision could relax
  the `job_type` `ondelete` to a soft-degrade form to make uninstall
  possible; that is a named non-MVP candidate, not assumed. The
  packaging proposal §5/§6 and the release plan's uninstall section
  carry this corrected posture.
- Core is never uninstalled while a domain module is installed (Odoo
  dependency mechanics enforce this).
- Job/log history lives in core and is preserved under the
  disable-path (nothing is deleted; jobs of a disabled domain simply
  stop being enqueued — merged flag enforcement).

## 9. Proposed decisions in this document (summary for ChatGPT)

| ID | Decision | Where used |
| --- | --- | --- |
| PD-1 | Task 015 ships as `shopify_connector_product_export` (own module, core+product) | §1.1, packaging proposal, Task 015 packet |
| PD-2 | No separate UI module — views live in owning modules | §1, UI packet |
| PD-3 | Task 012 sets sale depends = core, product, `sale` | §1.2, Task 012 packet |
| PD-4 | Exact binding-model names/keys for order / location-mapping / inventory-level / fulfillment (MBQ-55 remaining portions) | §3, packets §7 |
| PD-5 | Domain-owned checkpoints; cursors never persisted; overlap-window re-read (closes Q7) | §5.5, Area 6 packet |
| PD-6 | Pin API 2026-07 for Tasks 012–015 planning | §6, all packets |

Each is **Proposed for ChatGPT review — NOT accepted**; the task
packets carry them as their planning basis and are unusable until this
package is accepted.
