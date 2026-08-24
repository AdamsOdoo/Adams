# Independent Release-Assurance Report (COMPLETE) — Odoo 19 ↔ Shopify Connector

**System under review:** AdamsOdoo/Adams · Pull request **#206** · branch `codex/ui-restructure-implementation`
**Reviewed exact HEAD:** `6bb05c0cb0a91be856d9066451f292d5b1a7c791`
**Reviewer:** Claude (independent release-assurance session, memoryless of implementer reasoning)
**Review date:** 2026-08-23, timezone **UTC**
**Nature:** Read-only review. No repository file, PR, Odoo.sh staging/production, or Shopify production state was changed. All credentials/tokens/PII are redacted throughout.

**Evidence-class legend used in this report:** `[STATIC]` = source/diff inspection at the exact checkout · `[TEST]` = automated-test/CI evidence at the exact head · `[RUNTIME]` = genuine local Odoo 19 runtime I stood up at the exact head · `[LIVE-SHOPIFY]` = live 2026-07 Admin schema/dev-store evidence · `[BLOCKED]` = validation that the environment prevented (explicitly labelled, never fabricated).

---

## 1. EXECUTIVE DECISION

| Axis | Determination |
|---|---|
| **Assurance state** | **NOT ASSURED — material release blockers confirmed** |
| **Release readiness** | **NOT RELEASE READY** |
| **Architecture path** | **A — PRESERVE the current architecture with a bounded correction pass.** Not a rebuild; not a broad refactor; not a partial replacement. |
| **Finding counts (deduplicated, this review)** | **P0: 0 · P1: 15 · P2: 33 · P3: 30+** |
| **Are the supported workflows seamless?** | **No.** Onboarding, order import, fulfillment, product export, and inventory first-push each break or mislead on the first record; three core screens are unreachable or state the opposite of what the code does. |
| **Is public release safe now?** | **No.** |
| **Actual supported distribution model** | **A merchant-installed Odoo module driving a per-merchant Shopify _custom app_** (pasted Admin API access token, or Dev-Dashboard client-credentials grant). It is **not** a public Shopify App Store app: there is no OAuth authorization-code install flow and none of the three mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`) exist. |

**Why NOT ASSURED (evidence, not impression).** The transaction/idempotency/mutation-safety core, the webhook-ingress security, and the multi-company authorization model each survived adversarial attempts to break them (Sections 8, 10). But the connector does not do what it tells the merchant it does, on the very first order, fulfillment, export, or inventory push — independent of scale:

1. **Order import is dead on first live contact** — the order-read GraphQL selects `priceAfterAllDiscountsBeforeTaxesSet` on `LineItem`, a field that **does not exist in Admin API 2026-07** (the version the connector pins). Verified by live schema introspection and 2026-07 docs. `[LIVE-SHOPIFY]`
2. **The entire fulfillment read direction is dead** — `ORDER_FULFILLMENTS_QUERY` treats `Order.fulfillments` as a paginated connection; in 2026-07 it is a plain list. Mode 2 (auto-fulfillment) can never activate. `[LIVE-SHOPIFY]`
3. **The connector will let a warehouse ship cancelled and unpaid orders** — post-import cancellation / payment void refreshes the snapshot but never routes to review or Needs-Attention. `[STATIC]`
4. **A routine "sync a title" export can unpublish a merchant's live products** — imported ACTIVE products default their export status to DRAFT, so the first confirmed update proposes `status: ACTIVE → DRAFT`. `[STATIC]`
5. **Onboarding's inventory consent screen describes a Shopify→Odoo baseline import the code deliberately never implements**, and two first-push admission paths can permanently wedge an inventory pair. `[STATIC]` `[RUNTIME]` (setup-wizard HOOT verified present)

Beneath these first-contact defects sits a genuine **capacity ceiling** (single sequential job drain, unbounded fulfillment reconciliation, non-resumable 10k/20k scan ceilings, no job/log retention) that breaks the connector at the volumes a "best-in-class" connector implies, with **no documented supported limits** to fence a smaller deployment safely.

**Two hard release gates could not be executed here and remain open:** there is **no Odoo.sh build at the exact head** (the DEC-041 D8 Tier-1 acceptance authority; Odoo.sh dev hosts were unreachable — egress proxy 502) `[BLOCKED]`, and **no order/fulfillment workflow has ever been exercised end-to-end** against a live store (the authorized dev store holds 0 orders) `[BLOCKED]`. CI is green at the exact head and the local suite passes, but — as the CI workflow file itself states — that is **supporting evidence, not acceptance**.

**Is the architecture salvageable?** Yes, decisively. Every confirmed blocker is a localized, well-scoped correction against sound machinery. A rebuild would discard proven safety code to re-solve problems already solved here, and is therefore explicitly **not** recommended.

---

## 2. IMMUTABLE REVIEW FINGERPRINT

| Field | Value |
|---|---|
| Repository | `AdamsOdoo/Adams` (genuine checkout verified) |
| Pull request | **#206** — OPEN, DRAFT, `mergeable_state = clean` |
| Branch | `codex/ui-restructure-implementation` |
| Head SHA (reviewed) | `6bb05c0cb0a91be856d9066451f292d5b1a7c791` (= live branch HEAD; the PR body's `271164ce…` is stale and was **not** reviewed) |
| Tree SHA | `a8cc1e7ad6d064f9569ecfa4454e7c2545423532` |
| Base ref / SHA | `fable/wave-5-completion` @ `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` (= merge-base) |
| Diff vs base | **+31,122 / −3,217** across **302 files**, **116 commits** |
| Pinned Odoo source | `odoo/odoo` @ `30bde9ff758834a4912c5ae55843d3a7dad849f1` (`tools/odoo-pin.txt`) |
| Shopify Admin API pinned | **2026-07** (`shopify_connector_core/tools/api_version.py:39`) |
| Connector addons (11; all LGPL-3; all installable) | core `19.0.1.23.0` · product `19.0.2.11.0` · sale `19.0.2.11.0` · inventory `19.0.1.8.0` · fulfillment `19.0.1.6.0` · product_export `19.0.1.2.0` · webhook `19.0.1.1.0` · product_webhook `19.0.0.2.0` · sale_webhook `19.0.0.1.0` · inventory_webhook `19.0.0.3.0` · fulfillment_webhook `19.0.0.1.0` |
| CI workflow | `.github/workflows/connector-tests.yml` (fail-closed; pins Odoo; tests PR head, not merge ref) |
| CI runs at exact head | Actions **32594700478** (push) and **32594702709** (pull_request) — both `success`, 2026-08-22; only these two check runs on the head; suite step ≈ 56 min |
| CI result (first-party, from job log) | fresh **0 failed / 0 err / 2,760** · warm **0/0/2,760** · migration from `50b770a3` **0/0/2,659** (5 scripts) + idempotent repeat · migration from `0a15b176` **0/0/2,659** (4 scripts) + repeat · non-standard/concurrency **0/0/62** · **40/39** required tours · HOOT dashboard + export-diff + **setup-wizard** all verified |
| Odoo.sh build at exact head | **NONE recorded** → DEC-041 Tier-1 gate **NOT satisfied**. Odoo.sh dev hosts unreachable from this environment (egress proxy 502) → Odoo.sh inspection **`[BLOCKED]`** |
| Local replication runtime | Python **3.11.15** (CI uses 3.12 — deviation noted) · PostgreSQL **16.13** · Chromium **141.0.7390.37** · runner `--self-test` **PASS** · fresh-install pass **0/0/2,760** at exact head |
| Authorized Shopify store | `testin-lzhbzhtc.myshopify.com` (Basic App Development plan, AED). 3 active locations. **0 orders.** Seed product `gid://…/Product/8650641047737` @ qty 5 (matches repair-ledger §9's recorded 7→5 push). Forbidden store `mqiu21-yz.myshopify.com` **never touched.** |
| Governance state | DEC-042 one-iteration program armed; latest independent review at this head = **REVISE** (PR comment 5383360935); no implementer READY-FOR-CLAUDE-REVIEW posted since. |

---

## 3. PRODUCT CONTRACT FOUND

Executable behavior per domain. Disposition key: **FS** = fully supported · **MR** = supported with manual review · **UN** = unsupported by design · **AMB** = ambiguous/contradictory (a defect).

| Domain | Supported direction | Source of truth | Initial sync | Incremental sync | Webhook | Reconciliation | Conflict | Deletion | Recovery | Required role | Supported limit | Disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Authentication | Odoo→Shopify (write-only creds) | Odoo store record | test-connection identity check | token reused | — | — | dual-secret rotation grace | store undeletable (S-3) | re-enter token | Admin | 1 app/store | **FS** |
| Products | S→O import; O→S export (managed) | Shopify (birth), Odoo (managed fields) | scan ≤20k/window | webhook + scan | products/create,update | scheduled scan | snapshot divergence by design | products/delete not subscribed (PR-4) | failed_final no auto-recover (W-3) | Operator+ | 20k/window (non-resumable, W-2) | **MR/AMB** |
| Variants | S→O; O→S with product | Shopify birth | with product | with product | via product topic | with product | SKU never overwritten | remote delete silent (PR-5) | wedge on SKU gap (PR-2/3) | Operator+ | ≤2048/product | **AMB** |
| Prices | S→O birth/gated; O→S only odoo-authoritative | Shopify birth / Odoo authoritative | with product | gated refresh | via product | scan | disclosed snapshot | — | — | Operator+ | — | **FS** (1.00 bug fixed) |
| Inventory | **O→S only** (push, CAS) | **Odoo** | **NO baseline import** (I-3 copy claims otherwise) | first-push confirm + push scan | inventory_levels (drift detect) | push scan (unbounded, P-4) | drift → review/freeze | — | pair wedge (I-1/I-2) | Operator+ | push scan unbounded | **AMB** |
| Locations | S→O evidence; mapped | Shopify | mapping preview | mapping | — | scan | unmapped → block | — | remap governance | Admin | — | **FS** |
| Customers | S→O import (order path) | Shopify | on order | on order | via order | — | >1 match → ambiguous block | — | manual match | Operator+ | — | **FS** (O-3 latent PII on unwired job path) |
| Orders | **S→O read-first import** | Shopify | scan ≤10k/window | webhook + scan | orders/create,updated | scan | totals-change → review | — | **A-1 import dead** | Operator+ | 10k/window (non-resumable, W-2) | **AMB/blocked** |
| Payments | S→O evidence | Shopify | with order | with order | via order | — | **reversal after import NOT surfaced (O-2)** | — | — | Operator+ | — | **AMB** |
| Taxes | explicit per-store mapping | Odoo mapping | fingerprint→mapping | with order | — | — | unmapped → fail-closed | — | mapping suggestions | Admin | — | **FS** |
| Discounts | S→O tax-preserving residual | Shopify | with order | with order | — | — | positive residual → fail | — | — | Operator+ | — | **FS** |
| Shipping | S→O service line | Shopify | with order | with order | — | — | changed pre-import → skip | — | — | Operator+ | — | **FS** |
| Fulfillment | Mode 1 evidence / Mode 2 auto-validate | Shopify | **A-2 reads dead** | reader (dead) | fulfillment topics | hourly O(all) reconcile (P-1) | — | — | review cases **unreachable (U-1)** | Operator+ | ≤50k local scan | **AMB/blocked** |
| Cancellation | S→O evidence | Shopify | — | refresh only | orders/cancelled | scan | **not surfaced (O-2)** | — | — | Operator+ | — | **AMB** |
| Refunds | UN (no credit note) | Shopify | — | evidence-only | refunds/create not subscribed | — | — | — | manual | Operator+ | — | **UN** |
| Returns | UN | Shopify | — | — | — | — | — | — | manual | Operator+ | — | **UN** |
| Webhooks | inbound, HMAC, payload-free | Shopify | subscribe on activate | dedup+dispatch | 11 topics registered; gaps noted | delivery GC 500/day (P-3) | dedup on delivery_id | retired-topic readiness stuck (W-5) | reconnect fence | Admin | body ≤10MB | **FS** (topic gaps) |
| Reconciliation | scheduled discovery | Shopify | — | scans | — | fulfillment unbounded (P-1) | — | — | "eventual discovery" false for A-2/W-3 | system | — | **AMB** |
| Reporting | Odoo-side dashboards | Odoo | — | aggregates | — | over non-GC'd tables (P-10) | — | — | — | User+ | — | **FS** |
| Recovery | operator review/retry/resolve | Odoo | — | — | — | — | — | — | best surface unreachable (U-1) | Operator+ | — | **MR** |
| Multiple stores | parallel stores | per-store | per-store | single sequential drain (P-2) | per-store secrets | per-store | isolated | — | — | Admin | **no stated cap** | **MR** |
| Multi-company | fail-closed company rules | Odoo company | — | — | — | — | global rule refuses NULL-company | — | — | Admin | — | **FS** |
| Installation | fresh install 11 modules | — | 0/0/2,760 green | — | — | — | — | — | — | Admin | — | **FS** |
| Upgrade | warm + version-to-version migrations | — | migration scripts run + idempotent | — | — | — | — | — | — | Admin | — | **FS** |
| Uninstall | job retype sink + table drop | — | — | — | — | — | — | **no uninstall_hook → dangling subs+token (S-2)** | — | Admin | — | **AMB** |

---

## 4. PRIOR-HYPOTHESIS ADJUDICATION (HYP-001 … HYP-018)

| HYP | Subject | Verdict | Evidence / reasoning |
|---|---|---|---|
| 001 | Inventory truthfulness | **Confirmed** | `setup_wizard.py:235-243` promises "Stock levels are read in as a baseline"; no Shopify→Odoo stock write exists; manifest admits baseline import "deferred" (`inventory/__manifest__.py:45-47`). → **I-3**. `[STATIC]` |
| 002 | Connected-vs-ready | **Partially Confirmed** | Genuine "Unknown-not-Healthy" guard (`ui_health.py:148-155`) but defeated by activation audit jobs (**U-4**); activation copy overclaims (**U-3**). No surface literally prints "ready" pre-sync. `[STATIC]` |
| 003 | Intermediate success reported as done | **Partially Confirmed** | Layer-2 attempt honesty genuinely engineered (commit-before-send; empty userErrors never = success). But webhook duplicate branch reports `failed_final` as `processed` (**PR-6**); scan "success" is enumeration-only (honest in log, misleading field name). `[STATIC]` |
| 004 | Product lifecycle | **Confirmed** | `products/delete` not subscribed (**PR-4**); remote variant deletion silent at import (**PR-5**); most destructive directions are safe-stops. `[STATIC]` |
| 005 | Freshness / ordering | **Partially Confirmed** (narrow) | Out-of-order application not reproducible (read-first + per-GID scope lock + monotonic watermark). One same-second swallow: **O-4**. `[STATIC]` |
| 006 | Order lifecycle | **Partially Confirmed** | Most post-import events are honest safe-stops/evidence-only; exceptions **O-2** (cancellation/reversal not surfaced) and **O-1** (false "routed for review" log). `[STATIC]` |
| 007 | Inventory first-push discovery | **Fixed** (empty-preview hypothesis) **+ adjacent Confirmed** | Pair-binding discovery smooth and preview reachability fixed for the scheduled path; but two other admission surfaces wedge pairs (**I-1**, **I-2**) — a worse variant. `[STATIC]` |
| 008 | Historical product defects | **Partially Confirmed** | price-1.00 fixed for created products; empty SKU for variants added after first import (**PR-8**); export status DRAFT trap (**PR-1**). `[STATIC]` |
| 009 | Config-change invalidation | **Partially Confirmed** | Remap/withdrawal governance strong; gaps: stale previews never invalidated (**I-5**), warehouse-tree move unmonitored (**I-7**), domain disable/enable strands jobs (**I-9**). `[STATIC]` |
| 010 | Generation fencing | **Partially Confirmed** | Near-complete at every remote seam and all domain webhook admissions; one unfenced local-only consumer: `_handle_app_uninstalled` (**W-4**). `[STATIC]` |
| 011 | Webhook completeness | **Partially Confirmed** | Foundation release-grade; topic gaps (products/delete, refunds/create, orders/edited, customers/*, inventory_items/*, shop/update); recovery gaps **W-3/W-5**. `[STATIC]` |
| 012 | Resumability / scale | **Confirmed** | Product scan 20k / order scan 10k hard ceilings, restart-from-scratch, watermark frozen (**W-2**); fulfillment reconciliation + inventory push unbounded (**P-1**, **P-4**). `[STATIC]` |
| 013 | Role / company isolation | **Partially Confirmed** | Method-level enforcement unusually consistent (**RPC-probe verified, Section 10**); exceptions **S-1** (unguarded cron RPC — verified live), **S-4** (vestigial Reviewer). No cross-company read path found. `[RUNTIME]` |
| 014 | Recovery UX | **Partially Confirmed** | Decision dialogs & inventory/fulfillment forms answer 8–9/9; the best surface (fulfillment review) is unreachable (**U-1**); core triage & mutation-attempt form answer ~half. `[STATIC]` `[RUNTIME]` |
| 015 | Public-release auth | **Confirmed** | No OAuth install flow; no `customers/data_request`, `customers/redact`, `shop/redact` handlers. Custom-app distribution only. `[STATIC]` |
| 016 | Install / upgrade / uninstall | **Split** | Migrations sound & idempotent (**Confirmed good**); hard-raise-unlink does NOT break uninstall (**Not Reproducible** — runtime rows carry no `ir.model.data`). But no `uninstall_hook`: dangling Shopify subscriptions + token (**S-2**); stores permanently undeletable (**S-3**). `[STATIC]` `[RUNTIME]` |
| 017 | Information architecture | **Partially Confirmed** | Four-pillar structure verified; dead-ends **U-1/U-2**; duplicate Dashboard/Reporting path; orphaned menus. `[RUNTIME]` (live menu tree dumped) |
| 018 | Performance / scale | **Confirmed** | Single sequential drain (**P-2**), unbounded fulfillment reconciliation (**P-1**), no GC/retention (**P-3**), unbounded inventory scan (**P-4**), + N+1 clusters. `[STATIC]` |

No hypothesis is **Superseded**. No hypothesis is fully **Blocked** — every one was adjudicable from static + runtime + live-schema evidence, though HYP-016's live-uninstall path and HYP-018's real-throughput numbers carry residual items that only an Odoo.sh run can fully close (labelled in Sections 11/14).

---

## 5. COMPLETE VERIFIED FINDINGS REGISTER

Severity model (from the mission): **P0** data loss / silent corruption / security breach with no guard · **P1** primary workflow broken, destructive/silent business outcome, or false truthfulness · **P2** material defect with a workaround or bounded blast radius · **P3** improvement/hardening/backlog. Classification per CLAUDE.md §8: **Fact / Inference**. Confidence: **High/Med**. "blocks public release" = Yes/No.

### 5.1 — P1 RELEASE BLOCKERS (full field treatment)

---

**A-1 — Order import selects a non-existent LineItem field → every order import fails closed.**
- **Severity / Confidence / Class:** P1 / High / **Fact** (live-schema verified)
- **Affected capability / role:** Order import (all orders) / Operator+ (system cron)
- **SHA / addon / file / symbol / lines:** `6bb05c0c` / `shopify_connector_sale` / `models/shopify_connector_order_importer.py` / order-header query + line-items page query / **:115, :168** (definitions), consumed **:731-733, :1314**
- **Expected:** the pinned 2026-07 order query returns per-line discounted unit price and imports the order.
- **Actual:** `LineItem.priceAfterAllDiscountsBeforeTaxesSet` **does not exist** in Admin API 2026-07. Shopify returns `errors[].extensions.code='undefinedField'`; the importer maps this to `data_shape_schema_mismatch → failed_retryable`, with no auto-retry and no partial write. **100% of order imports stop on first contact.**
- **Reproduction:** activate a store on 2026-07; create/emit any order; observe the read query rejected with `undefinedField` before any Odoo write.
- **Runtime evidence `[LIVE-SHOPIFY]`:** full introspection of the `LineItem` type on the live 2026-07 endpoint — the field is absent; the correct field `discountedUnitPriceAfterAllDiscountsSet` **is** present. Cross-checked against 2026-07 docs.
- **Automated-test evidence `[TEST]`:** none — the suite performs zero Shopify calls, so the green suite cannot catch this (Section 11). No test executes the pinned query against a schema.
- **Odoo impact:** no sale order created/updated. **Shopify impact:** none (read-only rejection). **Merchant impact:** orders never reach Odoo; the connector's headline capability is inert. **Data-integrity impact:** none (fail-closed). **Security impact:** none.
- **Root cause:** query authored against a field name that is not valid for the pinned version (version-name confusion; an unverified changelog claim does not override live introspection).
- **Minimum safe remediation:** replace with `discountedUnitPriceAfterAllDiscountsSet` (or drop it and derive from `discountedUnitPriceSet`).
- **Acceptance criteria:** a real dev-store order imports green; a new test executes every pinned order query against 2026-07 (schema-validation or live canary) and fails on any undefined field.
- **Regression tests required:** query-schema conformance test for all order queries; one end-to-end order-import test against a canary order.
- **Dependencies:** none (independent).
- **Blocks public release:** **Yes.**
- **Adjudication note:** this **overturns** the order-workstream sub-agent's "not reproducible / field is valid" claim, which rested on an unverified changelog assertion; live introspection is authoritative.

---

**A-2 — Fulfillment reads use a connection shape for a plain-list field → all fulfillment reads fail; Mode 2 unreachable.**
- **Severity / Confidence / Class:** P1 / High / **Fact** (live-schema verified)
- **Affected capability / role:** All fulfillment reads; Mode-2 auto-fulfillment switch / Operator+ (system)
- **SHA / addon / file / symbol / lines:** `6bb05c0c` / `shopify_connector_fulfillment` / `models/shopify_connector_fulfillment_reader.py` / `ORDER_FULFILLMENTS_QUERY` / **:51-70**
- **Expected:** read fulfillments for an order to observe status / capture tracking / drive Mode-2 validation.
- **Actual:** the query uses `fulfillments(first:%d, after:$fCursor){ pageInfo{…} nodes{…} }`. In 2026-07 `Order.fulfillments` is `[Fulfillment!]!` (a plain list; only args `first`/`query`; no `after`/`pageInfo`/`nodes`). Every consumer fails deterministically: inbound observation (→`failed_retryable` per fulfilled order), reconnect catch-up (never completes), Mode-2 switch scan (aborts to "Mode 1 blocked"), fulfillment-create reconciliation (always inconclusive → manual review).
- **Reproduction:** fulfill any order in Shopify; the reader rejects the document with a field-shape error; Mode-2 activation scan aborts.
- **Runtime evidence `[LIVE-SHOPIFY]`:** introspection of `Order.fulfillments` → `[Fulfillment!]!`, args `first`,`query` only.
- **Automated-test evidence `[TEST]`:** none (no Shopify calls in suite).
- **Odoo impact:** fulfillment status never observed; deliveries not validated. **Shopify impact:** none. **Merchant impact:** Mode 2 permanently unavailable; Mode 1 evidence never captured. **Data-integrity impact:** none. **Security impact:** none.
- **Root cause:** query authored to the connection idiom for a field that is a plain list in this version.
- **Minimum safe remediation:** rewrite to `fulfillments(first: N){ … fulfillmentLineItems(first: M){…} }` (list shape) and re-verify against 2026-07.
- **Acceptance / regression:** a real fulfilled dev-store order reads green; schema-conformance test covers the fulfillment document; Mode-2 switch test passes.
- **Dependencies:** unblocks **P-1/W-6** reads once corrected.
- **Blocks public release:** **Yes.**

---

**O-2 — Post-import cancellation / payment reversal never demands attention → cancelled/unpaid orders remain shippable.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Order lifecycle after import; warehouse fulfillment / Operator, warehouse
- **SHA / addon / file / symbol / lines:** `shopify_connector_sale` / `models/shopify_connector_order_importer.py` / review-routing conditions **:2435-2444** (omit cancelled/voided/expired), stamp-only **:2273-2274**; attention filter `views/shopify_connector_order_binding_views.xml:47-52` (excludes cancelled)
- **Expected:** a PAID order later cancelled without refund, or an AUTHORIZED order later VOIDED/EXPIRED, is routed to review / Needs-Attention so it is not shipped.
- **Actual:** the refresh stamps new financial/cancel state but leaves binding `active` and the Odoo SO confirmed and deliverable; no operator signal.
- **Reproduction:** import a paid order; cancel it (or let auth expire) in Shopify; refresh; the SO remains confirmed and absent from Needs-Attention.
- **Evidence:** `[STATIC]` routing + filter inspection. `[TEST]` no coverage of this transition.
- **Odoo impact:** confirmed shippable SO for a dead order. **Shopify impact:** merchant ships goods for a cancelled/unpaid order → chargeback/loss. **Merchant impact:** direct financial loss. **Data-integrity impact:** Odoo state contradicts Shopify truth silently. **Security impact:** none.
- **Root cause:** review-routing whitelist omits cancellation/reversal transitions; attention domain excludes cancelled.
- **Remediation:** on `cancelledAt` false→true, or financial status entering {VOIDED, EXPIRED, REFUNDED, PARTIALLY_REFUNDED}, set `status='review'`; include cancelled in the attention filter.
- **Acceptance / regression:** transition tests for each state → review + appears in Needs-Attention.
- **Dependencies:** none. **Blocks public release:** **Yes.**

---

**PR-1 — Imported ACTIVE products default to a DRAFT-flip on next confirmed update → a title-sync can unpublish a live product.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Product export / Operator, merchant
- **SHA / addon / file / symbol / lines:** `shopify_connector_product_export` / `models/…_seams.py:227-239` (`shopify_export_status` default `'draft'`, never initialized from imported status) + `models/…_service.py:296-299` (`status` always in `_desired_scalars`)
- **Expected:** exporting an unrelated field change (e.g. title) does not alter publish status.
- **Actual:** the first update preview for an imported ACTIVE product contains `status: ACTIVE → DRAFT`; confirming it unpublishes the live product. This is the standing reason **export confirmations must remain FROZEN**.
- **Reproduction:** import an ACTIVE product; edit a managed field; open export preview → `status` diff to DRAFT present.
- **Evidence:** `[STATIC]` default + diff-builder. `[TEST]` HOOT export-diff verifies diff rendering but not this default interaction.
- **Odoo/Shopify/merchant impact:** a routine sync silently unpublishes a live, selling product. **Data-integrity:** publish state corrupted. **Security:** none.
- **Root cause:** export status default not seeded from `binding.shopify_status`; status unconditionally emitted.
- **Remediation:** initialize `shopify_export_status` from imported status, or exclude `status` from the diff unless explicitly managed.
- **Acceptance / regression:** imported ACTIVE product's first export preview contains **no** `status` row unless managed; test named.
- **Dependencies:** gates lifting the export freeze. **Blocks public release:** **Yes.**

---

**PR-2 / PR-3 / PR-8 — Variant-add export finalization broken for the normal case; can wedge after a real remote write; silent SKU gaps feed it.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Product export (adding a variant to an exported product) / Operator
- **SHA / addon / file / symbol / lines:** `product_export/models/…_service.py:3090` (`_bind_created_variants` iterates **all** template variants, not the created ones), reconciliation savepoint **:3282-3303**; `shopify_connector_sale/models/shopify_connector_order_importer.py:944-956` (birth-only SKU write — PR-8)
- **Expected:** adding a variant to a bound product creates and binds exactly the new variant.
- **Actual (PR-2):** iterating all variants means previously-bound variants find no SKU candidate → "could not map … exactly once" raises every time; wedges permanently if any bound variant lacks/drifts an SKU (raise inside the savepoint). **(PR-3):** the variants-create path lacks create-path identity pre-validation → an SKU-less variant is created remotely then can never bind. **(PR-8):** a remote variant added after first import gets empty `default_code`/`barcode` in Odoo (birth-only write), feeding PR-2/PR-3.
- **Reproduction:** export a product; add a variant (with an SKU-less sibling present); confirm → reconciliation raises; the pair cannot finalize.
- **Evidence:** `[STATIC]`. `[TEST]` no test covers `_bind_created_variants` (Section 11).
- **Impact:** export wedges; a variant may exist in Shopify with no Odoo binding (PR-3) → future double-create risk. **Data-integrity:** binding/reality divergence. **Security:** none.
- **Remediation:** iterate the confirmed `variant_ids`; add pre-C2 identity validation to the variants-create path; initialize identity fields for later-created variant bindings.
- **Acceptance / regression:** mixed variants-create with an SKU-less sibling finalizes or safe-stops without a permanent wedge; tests named.
- **Dependencies:** none. **Blocks public release:** **Yes.**

---

**I-1 / I-2 — First-push admission-routing gaps permanently wedge inventory pairs.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Inventory push (first push per pair) / Operator
- **SHA / addon / file / symbol / lines:** `shopify_connector_inventory/models/shopify_connector_inventory_service.py` — I-1: `_enqueue_from_stock_moves:1312-1356` admits a push the handler blocks at `:1462-1470`; I-2: scan `previewed` branch `:1974-1995` admits push for still-unconfirmed pairs
- **Expected:** a pair that has not completed the first-push confirmation is previewed (or nothing is admitted), never a job that blocks and holds the pair scope forever.
- **Actual (I-1):** a stock move for a not-yet-previewed pair admits a `push_sync` the handler blocks; the blocked job holds the pair scope with every sanctioned exit closed → permanent wedge. **(I-2):** the scan's `previewed` branch admits `push_sync` for still-unconfirmed pairs → one `blocked_manual_review` per pair per cycle; after confirmation nothing pushes until each blocked job is manually resolved.
- **Reproduction:** create a stock move for a fresh pair before preview (I-1); or run the scan over a previewed-but-unconfirmed pair (I-2).
- **Evidence:** `[STATIC]` admission/handler paths.
- **Impact:** inventory for the affected pair never syncs; operator must manually clear blocked jobs; at scale a store can accumulate a wall of blocked jobs. **Data-integrity:** Shopify stock stale vs Odoo. **Security:** none.
- **Root cause:** push-admission surfaces other than the scan's `pending` branch ignore `first_push_state`; an attempt-less blocked orchestration job has no terminal exit.
- **Remediation:** route non-confirmed pairs the way the scan's `pending` branch does (preview or admit nothing); make the handler's first-push branch terminal `skipped`, not `blocked`.
- **Acceptance / regression:** stock-move-before-first-scan and second-scan-over-previewed-pair tests → no permanent wedge.
- **Dependencies:** none. **Blocks public release:** **Yes.**

---

**I-3 — Onboarding inventory consent screen describes a Shopify→Odoo baseline import that does not exist.**
- **Severity / Confidence / Class:** P1 / High / **Fact** (truthfulness defect)
- **Affected capability / role:** Onboarding consent / merchant, Admin
- **SHA / addon / file / lines:** `shopify_connector_core/models/shopify_connector_setup_wizard.py:235-243` ("Shopify to Odoo, then Odoo to Shopify"; "Stock levels are read in as a baseline")
- **Expected:** consent copy matches behavior (inventory is one-way Odoo→Shopify; Shopify quantities are read only to detect drift).
- **Actual:** the copy promises a baseline import that no code path implements.
- **Evidence:** `[STATIC]` copy + absence of any S→O stock write; `[RUNTIME]` setup-wizard HOOT present.
- **Impact:** merchant consents to a data flow that will not happen; stock expectations wrong from step one. **Data-integrity/Security:** none.
- **Remediation:** text-only correction to the true contract.
- **Acceptance / regression:** onboarding copy review; wizard tour asserts the corrected text. **Blocks public release:** **Yes.**

---

**U-1 — Fulfillment review cases are unreachable.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Fulfillment exception recovery / Operator
- **SHA / addon / file / lines:** menu inactive `shopify_connector_fulfillment/views/…_menus.xml:13-18`; feed built `…_ui_store360_fulfillment.py:47-51,132-207` but never rendered (no lifecycle/exception renderer in `dashboards_split.xml`; health renders only core exceptions)
- **Expected:** "Shopify cancelled a validated fulfillment" (stock shipped, order cancelled) is visible and actionable.
- **Actual:** no menu and no rendered card → the case is invisible.
- **Evidence:** `[STATIC]` menu + renderer; `[RUNTIME]` live menu tree confirms the menu is inactive.
- **Impact:** the highest-stakes fulfillment exception is silently unhandled. **Security:** none.
- **Remediation:** reactivate the Review Workspace menu (or render the feed on Connector Health) + a review-count smart-link.
- **Acceptance / regression:** browser walk reaches fulfillment review cases; count link present. **Blocks public release:** **Yes.**

---

**U-2 — The canonical Sync Rules settings screen has no navigation route (prior B-4, unfixed).**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Configuration / Admin
- **SHA / addon / file / lines:** `shopify_connector_inventory/views/…_menus.xml:20-25` parents "Inventory Safeguards" under Sync Rules; the codebase's own documented Odoo-19 rule (`…_menus.xml:88-91`) makes a parent-with-children a non-clickable heading, so `action_open_canonical_store_settings` is unreachable — while the wizard tells users to "change it later in Sync Rules."
- **Evidence:** `[STATIC]` menu structure + the code's own documented behavior; `[RUNTIME]` live menu dump (menu 89 → action 113 + child menu 261).
- **Impact:** the main Sync Rules settings screen cannot be opened by any user through the UI. **Security:** none.
- **Remediation:** apply the same self-child mitigation already used for Stores & Onboarding, or re-parent Inventory Safeguards to Configuration.
- **Acceptance / regression:** browser walk opens Sync Rules settings. **Blocks public release:** **Yes.**

---

**U-3 — Activation copy asserts the opposite of what happens.**
- **Severity / Confidence / Class:** P1 / High / **Fact** (truthfulness)
- **Affected capability / role:** Activation / merchant, Admin
- **SHA / addon / file / lines:** `setup_wizard.xml:978-981` + toast `setup_wizard.js:628-631` ("Activating does not start a sync … Nothing is syncing yet") while `setup_wizard.py:1955-1984` immediately `_trigger()`s the read-side scan crons; the promised "dashboard shows the next action" is not rendered for a configured store.
- **Evidence:** `[STATIC]` copy vs trigger call.
- **Impact:** merchant is told nothing is syncing while imports are running → wrong mental model at the moment of activation. **Security:** none.
- **Remediation:** reword to the truth ("Activating starts the imports you selected; nothing is written to Shopify"); implement or drop the next-action promise.
- **Acceptance / regression:** activation tour asserts corrected copy. **Blocks public release:** **Yes.**

---

**W-2 — Non-resumable scan ceilings stall large stores permanently.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Product/order initial + incremental scan / system
- **SHA / addon / file / lines:** `product_scan.py:224-256` (20,000/window), `order_scan.py:246-250` (10,000/window) — hard ceilings that fail closed, discard progress, freeze the watermark, retry into the same wall
- **Expected:** a store above the window ceiling still completes initial sync.
- **Actual:** a >10k-order first window (or a bulk edit above the ceiling) halts sync forever.
- **Evidence:** `[STATIC]`. `[TEST]` no ceiling-behavior test (O-6/W-2).
- **Impact:** any serious store never completes initial sync; no documented cap warns the merchant. **Security:** none.
- **Remediation:** persisted intra-window cursor + time-window bisection, **or** a documented + preflight-enforced supported-scale limit.
- **Acceptance / regression:** a >ceiling dataset completes (cursor) or is refused with a clear supported-limit message. **Blocks public release:** **Yes** (fix or documented+enforced cap).

---

**P-1 / W-6 — Fulfillment hourly reconciliation is O(all fulfillments) remote reads in one job.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Scheduled fulfillment reconciliation / system
- **SHA / addon / file / lines:** `shopify_connector_fulfillment/models/shopify_connector_fulfillment_scans.py:120-181,125-137,147-153`; `tracking_strategy.py:54-59`
- **Expected:** hourly reconciliation bounded per pass.
- **Actual:** full binding population each run; one remote read per binding; one inbound-observation child per order binding. >50k bindings hard-fails and the watermark never advances; ~10k monopolizes the drain 1.5–3 h every hour. (Compounded by **A-2**, which makes every read fail today.)
- **Evidence:** `[STATIC]` (performance workstream annex).
- **Impact:** at real fulfillment volume the queue is monopolized or the pass never completes. **Security:** none.
- **Remediation:** time-window the population; bound per pass with a persisted cursor; batch the remote reads.
- **Acceptance / regression:** load test at the stated ceiling completes within the cron window. **Blocks public release:** **Yes** (fix or documented+enforced cap).

---

**P-2 — Single sequential job drain, no ingestion wakeup, no stated capacity.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Global job dispatch (all stores) / system
- **SHA / addon / file / lines:** `shopify_connector_job_dispatch.py:31,40-42,427-429`; `cron_drain.xml:35-36`
- **Actual:** default ≈20 jobs / 5 min (~4/min), one Shopify call in flight across all stores, nothing triggers the drain on webhook ingestion. 60 webhooks/min ⇒ ~120 jobs/min demand vs 4–100/min capacity → unbounded backlog.
- **Evidence:** `[STATIC]`. Real multi-worker throughput is **not statically verifiable** (needs Odoo.sh).
- **Impact:** multi-store / webhook-heavy deployments fall permanently behind. **Security:** none.
- **Remediation:** per-store round-robin or sharded drain; `_trigger()` on enqueue; document the supported rate.
- **Acceptance / regression:** documented supported throughput + a load test at that rate. **Blocks public release:** **Yes** (fix or documented+enforced cap).

---

**P-3 — No GC for jobs/logs/attempts; delivery GC 500/day vs unbounded inflow.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Retention across job/log/delivery/attempt tables / system
- **SHA / addon / file / lines:** `webhook_delivery.py:24-25,384-404` (single 500-row daily batch, no loop); `job_log.py:25` (`ondelete='restrict'`, never deleted)
- **Actual:** tens of millions of rows/year on a busy store; degrades dashboards, claims, upgrades.
- **Evidence:** `[STATIC]`.
- **Impact:** unbounded table growth → slow dashboards/migrations, storage cost. **Security:** none (though log growth eventually impacts availability).
- **Remediation:** loop the retention sweep under `_commit_progress`; add age-based GC/archival for terminal jobs/logs/attempts with evidence carve-outs.
- **Acceptance / regression:** retention test shows bounded growth at stated inflow. **Blocks public release:** **Yes** (fix or documented+enforced cap).

---

**P-4 — Inventory push scan unbounded, N+1, write-churning, no singleton dedup.**
- **Severity / Confidence / Class:** P1 / High / **Fact**
- **Affected capability / role:** Inventory push scan / system
- **SHA / addon / file / lines:** `inventory_service.py:1404-1407` (uuid payload, no `res_model` → no scope-key dedup), `:1914-2008` + `:3433-3632` (unbounded search, per-pair bootstrap, unconditional per-binding UPDATE)
- **Actual:** latent behind a default-off flag; breaks if enabled for a >1k-pair store.
- **Evidence:** `[STATIC]`.
- **Impact:** if the flag is enabled at scale, write churn + N+1 + no dedup overwhelm the drain. **Security:** none.
- **Remediation:** scope-key singleton; persisted cursor pagination; write-on-change only; move bootstrap out of the hot pass.
- **Acceptance / regression:** enabled-flag load test at stated scale. **Blocks public release:** **Yes** (fix or keep flag off + documented).

---

### 5.2 — P2 MATERIAL FINDINGS

Each carries: ID — title (**class/confidence**) · file:line · expected→actual · impact · remediation · blocks-release.

- **S-1 [RUNTIME-verified]** — Cron entrypoints callable via RPC with no group check (**Fact/High**). Five methods: `run_drain`, `pii.retention.run_sweep`, `stale.owner.sweep.run_sweep`, `inventory.service.run_inventory_push_scan`, `media.export.service.run_media_status_poll`. Live probe: a **read-only Auditor** can invoke all five (initiating Shopify traffic, force-failing running jobs, triggering PII sweeps); **any internal user with no connector group** can invoke `run_media_status_poll`. → authorization gap. Remediation: add the `env.su or admin-group` guard already used on `webhook_delivery.run_retention_sweep`. **Blocks release: Yes** (elevated to the WP-5 gate although rated P2 by blast-radius).
- **O-1** — false "routed for review" job-log claim on refresh (**Fact/High**). Log asserts review routing that did not occur. Impact: misleading audit trail. Remediation: log only real transitions. No.
- **O-4** — same-second second change silently dropped by webhook+scan (**Fact/Med**). Impact: a rapid second edit can be swallowed. Remediation: sub-second tiebreak / version compare. No.
- **O-5** — price-neutral order edit silently absorbed (wrong item shipped) (**Fact/Med**). Impact: item swap with equal total not surfaced. Remediation: diff line composition, not just totals. No (disclose).
- **O-6** — 10k-order scan ceiling mislabeled as schema mismatch (**Fact/High**). Impact: misleading error class hides W-2. Remediation: distinct ceiling error. No.
- **PR-4** — product deletion undiscoverable steady-state (`products/delete` not subscribed) (**Fact/High**). Impact: deleted Shopify products linger in Odoo. Remediation: subscribe + safe-stop, or document. No (disclose).
- **PR-5** — remote variant deletion invisible at import (**Fact/High**). Impact: stale variant bindings. Remediation: detect + safe-stop. No (disclose).
- **PR-6** — webhook duplicate branch reports `failed_final` as `processed` (**Fact/High**). Impact: false success in delivery record. Remediation: preserve terminal disposition. No.
- **I-4** — first-push step/binding form imply a Shopify quantity was read when none was (**Fact/Med**). Truthfulness. Remediation: copy fix. No.
- **I-5** — stale previews never invalidated (confirmed qty ≠ pushed qty) (**Fact/Med**). Impact: operator confirms an outdated number. Remediation: invalidate preview on drift. No.
- **I-7** — post-mapping `stock.location` tree move bypasses double-count guard (oversell) (**Fact/Med**). Impact: possible oversell after warehouse reorg. Remediation: monitor tree moves. No.
- **I-8** — push scan unbounded / no checkpoint (**Fact/High**). (Capacity sibling of P-4.) Remediation: checkpoint. No.
- **W-3** — product `failed_final` import has no automatic recovery (**Fact/High**). Impact: "eventual discovery" claim false for products. Remediation: recovery pass or documented manual retry. No (disclose).
- **W-4** — `_handle_app_uninstalled` unfenced (false forced-reconnect) (**Fact/Med**). Impact: a stale generation can force reconnect. Remediation: fence the local consumer. No.
- **W-5** — retired-then-reinstalled topic never regains `expected=True` (readiness permanently NOT_PROVEN) (**Fact/Med**). Remediation: reset expectation on re-subscribe. No.
- **W-7** — evidence/job growth outpaces retention (**Fact/High**). (Sibling of P-3.) No.
- **W-8** — 240 jobs/hour default ceiling undocumented (**Fact/High**). Remediation: publish. No (disclose).
- **W-10** — product deletion lost end-to-end (**Fact/High**). (PR-4 end-to-end view.) No (disclose).
- **U-4** — health "Healthy" pre-first-sync via activation-audit-job loophole (**Fact/Med**). Truthfulness. Remediation: gate Healthy on real sync evidence. No.
- **U-6** — "Store Settings" named as a place to change things that doesn't exist / is read-only (**Fact/Med**). Remediation: rename/route. No.
- **U-7** — Needs Attention lists superseded (retried) cases forever (**Fact/Med**). Remediation: supersede on retry. No.
- **U-8** — generic order review has no displayed reason/action (**Fact/Med**). Remediation: show reason+action. No.
- **U-9** — degraded-state banner points at an inactive menu (**Fact/Med**). Remediation: route to a live surface. No.
- **U-10** — mutation-attempt decision surface has no business-record link, no uncertainty reason, no downstream-effect text (**Fact/High**). Impact: the highest-stakes "did this land in Shopify?" decision is under-informed. Remediation: add record link + reason + effect text. No (strongly recommended).
- **U-18 [needs backend confirm]** — a blocked inventory mutation with a `failed_clean` attempt may have no UI resolution route (**Inference/Med**). Remediation: confirm + add route. No.
- **S-2** — no `uninstall_hook`: dangling Shopify subscriptions + token after uninstall (**Fact/High**). Remediation: uninstall hook that revokes subscriptions + guidance to rotate the token. No (disclose + fix).
- **S-3** — stores permanently undeletable, no archive path (**Fact/High**). Remediation: archive path + documented permanence contract. No (disclose).
- **P-5** — product-import matching loads whole catalog's bindings per job (**Fact/Med**). Remediation: targeted lookup. No.
- **P-6** — PII/retention sweeps unbounded single-transaction (**Fact/Med**). Remediation: batch. No.
- **P-7** — SEC-3 quarantine sweep full-scans evidence tables on every upgrade (**Fact/Med**). Remediation: bound/scope. No.
- **P-8** — media status poll one job/row/5min forever (**Fact/Med**). Remediation: batch poll. No.
- **P-9** — stock-move hook N+1 inside picking-validation transaction (**Fact/Med**). Remediation: batch. No.

### 5.3 — P3 IMPROVEMENT / BACKLOG (30+; grouped, each with file-area + one-line remediation)

- **O-3** latent PII in customer-import job path — redact `technical_detail` before that job type is ever enabled (**must precede enabling that job**). O-7 dead COD fields reset on refresh. O-8/O-9/O-10 minor lifecycle polish.
- **PR-7, PR-9…PR-15** export/import polish (managed-flag ergonomics, message-string duplication, GID validator duplication, media edge cases).
- **I-6, I-9, I-10, I-11** config-change edge cases (domain disable/enable strands jobs; remap ergonomics; preview lifecycle).
- **W-9, W-11** webhook topic/observability polish.
- **U-5, U-11…U-20** jargon-to-merchant-language pass (mutation, lease/quiescence, idempotency key, fingerprints, HMAC epoch, A4/A7 codes, raw GIDs as titles, "binding"), empty-state copy, smart-link consistency.
- **S-4** vestigial Reviewer group (dead access surface — remove). **S-5** secrets plain at rest — **accepted residual, MUST be documented** in release/privacy docs. S-6, S-8, S-9, S-10 hardening (rotation ergonomics, log-field review, defense-in-depth).
- **P-10…P-15** indexing (finished_at/next_retry_at unindexed), orphan lease expiry, drain COUNT-per-job, store lifecycle lock scope, throttle telemetry last-writer-wins, RR post-IntegrityError re-read winner edge.

> **Register completeness note.** The P1 set above is treated at full field depth because it is the release gate. P2/P3 entries carry the substantive fields (ID, title, class/confidence, file:line, expected→actual, impact, remediation, blocks-release); the exhaustive per-attribute detail for every P2/P3 lives in the per-workstream annexes (`agent-reports/`), of which the performance/architecture annex (`07-performance-architecture.md`, findings P-1…P-15 with exact line ranges) is reproduced verbatim in this session. No finding was dropped to shorten the register; nothing was fabricated where evidence was not separately captured (such fields are marked with the observed basis).

---

## 6. COMPLETE END-TO-END WORKFLOW MATRIX

| Workflow | Supported contract | Code paths reviewed | Automated tests | Live validation | Expected | Actual | Class | Remaining gap | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| Authentication / identity | custom-app token/client-creds; write-only | credential model, test-connection | suite green; RPC probe `[RUNTIME]` | shop identity confirmed on dev store `[LIVE-SHOPIFY]` | identity verified, creds locked | matches | **Pass** | creds plain at rest (documented residual) | OK (custom-app) |
| Onboarding | 12-step wizard, durable resume, readiness gate | setup_wizard.py/.xml/.js | HOOT setup-wizard `[TEST]`; 39 tours | not run end-to-end `[BLOCKED]` | truthful consent + reachable config | false consent (I-3), false activation (U-3), dead-end (U-2) | **Blocked** | I-3/U-2/U-3 | Blocker |
| Initial sync | per-domain evidence, honest Unknown | scan + health | suite green | not run `[BLOCKED]` | truthful progress + terminal readiness | no progress UI; U-4 healthy-pre-sync | **Partial** | U-4 | Fix U-4; document |
| Products (import) | create/update guarded | product_importer | product suites green | seed product imported (ledger §9) `[LIVE-SHOPIFY]` | honest create/update | PR-8 SKU gaps; PR-4/5 deletions | **Partial** | PR-8; deletions | Fix PR-8; disclose |
| Products (export) | review→confirm→apply, Layer-2 safe | export service/seams | export suites green; HOOT export-diff `[TEST]` | **FROZEN** — not exercised `[BLOCKED]` | no unintended publish change | PR-1 DRAFT-flip; PR-2/3 wedge | **Blocked** | PR-1/2/3 | Blocker; freeze stays |
| Inventory | one-way push, CAS, first-push confirm | inventory_service | inventory suites green | push 7→5 recorded `[LIVE-SHOPIFY]` | no pair wedge; truthful copy | I-1/I-2 wedge; I-3 copy; I-5 stale | **Partial** | I-1/2/3 | Blocker |
| Orders / customers | read-first import, evidence-only lifecycle | order_importer | sale suites green | **0 orders — never exercised** `[BLOCKED]` | order imports; reversals surfaced | A-1 import dead; O-2 not surfaced | **Blocked** | A-1/O-2 | Blocker |
| Fulfillment | Mode 1 evidence / Mode 2 auto-validate | fulfillment_reader/scans | fulfillment suites green | not run `[BLOCKED]` | reads succeed; Mode 2 available | A-2 reads dead; Mode 2 unreachable | **Blocked** | A-2 | Blocker |
| Webhooks | HMAC, dedup, payload-free, read-first | webhook base + domain | webhook suites green; base reviewed `[STATIC]` | not run (MCP app ≠ connector app) `[BLOCKED]` | verified ingress, complete topics | topic gaps; W-3/4/5 | **Partial** | W-set | Fix W-set; disclose |
| Scheduled reconciliation | discovery guarantees | scans | suites green | not run `[BLOCKED]` | eventual discovery for all topics | false for A-2 fulfillment, W-3 product | **Partial** | with A-2/W-3 | Fix |
| Failure / recovery | operator review/retry/resolve | recovery surfaces | suites green | role probe `[RUNTIME]` | reachable, informative surfaces | U-1 unreachable; U-10 weak; U-18 possible dead-end | **Partial** | U-1/10/18 | Fix U-1 |
| Material config changes | pause/invalidate/reconcile | config governance | suites green | not run `[BLOCKED]` | invalidate on change | I-5/I-7/I-9 gaps | **Partial** | — | Fix; document |
| Credential rotation | dual-secret grace | secret model | suite green | not run | rotate without downtime | works statically | **Pass** | — | OK |
| Disconnect / reconnect | generation bump + fence + catch-up | reconnect path | suites green | not run `[BLOCKED]` | fenced catch-up | W-4 unfenced uninstall | **Partial** | W-4 | Fix W-4 |
| App uninstall | job retype + table drop | uninstall path | static | not run `[BLOCKED]` | clean external state | S-2 dangling subs/token; S-3 permanence | **Partial** | S-2/3 | Fix S-2; document S-3 |
| Roles | Admin/User visible; Auditor/Operator/Reviewer hidden | ACL/rules | RPC matrix `[RUNTIME]` | pass (creds/secrets admin-only; no-role denied) | method-level enforcement | S-1 cron RPC; S-4 vestigial | **Pass** except S-1 | S-1 | Fix S-1 |
| Multi-company | fail-closed company rules | ir.rule | suites green | probe `[RUNTIME]` | no cross-company read | none found | **Pass** | — | OK |
| Multiple stores | parallel per-store | dispatch | suites green | not run `[BLOCKED]` | fair per-store drain | P-2 single sequential | **Partial** | P-2 | Fix or cap |
| Fresh installation | 11 modules | install | fresh 0/0/2,760 `[TEST]`+`[RUNTIME]` | local install `[RUNTIME]` | clean install | matches | **Pass** | — | OK |
| Upgrade | warm + version-to-version | migrations | migration passes green `[TEST]` | — | idempotent migrations | matches | **Pass** | — | OK |
| Repeated upgrade | idempotent replays | migrations | idempotent-repeat green `[TEST]` | — | no double effect | matches | **Pass** | — | OK |
| Uninstall | (as App uninstall) | uninstall | static | not run `[BLOCKED]` | clean | S-2/S-3 | **Partial** | S-2/3 | Fix/document |

---

## 7. DATA-CONTRACT MATRIX

| Field | Authority | Import rule | Export rule | Conflict rule | Deletion rule | Validation result |
|---|---|---|---|---|---|---|
| Product title | Shopify | birth only | O→S when managed | snapshot diverges by design | never deletes Odoo | OK |
| Description | Shopify/Odoo managed | birth | O→S when managed | managed wins | — | OK |
| Status (publish) | Shopify birth | birth snapshot | **always emitted** | — | — | **PR-1**: DRAFT-flip trap |
| SKU | Shopify (birth) | birth, only-if-empty | O→S via inventoryItem.sku | never overwrites non-empty | no clear path | **PR-8**: empty for later-added variants |
| Barcode | Shopify (birth) | birth, only-if-empty | O→S when set | — | no clear | **PR-8** |
| Vendor | Odoo (`shopify_export_*`) | snapshot only | managed-flag gated | empty+unmanaged omitted | clear only via managed flag | OK |
| Product type | Odoo managed | snapshot | managed-gated | — | — | OK |
| Options | Shopify | with product | with product | — | — | OK |
| Variants | Shopify birth | with product | create/update | SKU never overwritten | remote delete silent | **PR-2/3/5** |
| Price | Shopify birth / Odoo authoritative | additive decomposition or disclosed note | omitted unless odoo-authoritative | disclosed | — | OK (1.00 fixed) |
| Compare-at price | Shopify | snapshot | managed-gated | — | — | OK |
| Currency | Shop currency | presentment must equal shop | — | divergent → skip | — | OK |
| Tax basis | per-store mapping | full-tuple fingerprint → mapping | — | unmapped → blocked+suggestions | — | OK (fail-closed) |
| Inventory tracking | Shopify (evidence)/Odoo is_storable | snapshot | never exported | created-only conversion | — | OK |
| Available quantity | **Odoo → Shopify only** | **NO Shopify→Odoo write** | CAS absolute set, first-push confirm | drift → review/freeze | — | **I-3** false baseline claim |
| Location | Shopify (evidence) | mapping preview | mapped push | unmapped → block | — | OK |
| Customer identity | Shopify | normalized-email match, create-on-confident | — | >1 → ambiguous block | — | OK (**O-3** latent PII on unwired job path) |
| Addresses | Shopify | mapped on import | — | — | — | OK |
| Order quantity | Shopify | on import | — | totals-change → review | — | OK |
| Unit price | Shopify | via `discountedUnitPriceAfterAllDiscountsSet` (currently wrong field) | — | — | — | **A-1** invalid field |
| Discounts | Shopify | line + order-level, tax-preserving residual | — | positive residual → fail | — | OK |
| Taxes | Shopify + mapping | fingerprint → mapping | — | unmapped → blocked | — | OK |
| Shipping lines | Shopify | service line + tax-included conversion | — | changed pre-import → skip | — | OK |
| Payment state | Shopify | rich policy (PAID/AUTHORIZED/PENDING) | — | reversal after import **not surfaced** | — | **O-2** |
| Order lifecycle state | Shopify | evidence-only post-import | — | totals-changing → review | — | **O-2** (cancel not surfaced) |
| Cancellation | Shopify | refresh only | — | **not surfaced** | — | **O-2** |
| Refund | Shopify | evidence-only | — | no credit note (UN) | — | disclose |
| Return | Shopify | — | — | UN | — | disclose |
| Fulfillment state | Shopify | snapshot | Mode-2 auto-validate picking | — | — | **A-2** reads dead |
| Tracking | Shopify/Odoo | — | O→S on delivery | — | — | depends on A-2 |
| Customer notification | Odoo setting | — | fail-closed pair | — | — | OK (**U-6** wrong menu name) |

---

## 8. ARCHITECTURE ASSESSMENT

**Verdict: PRESERVE. Do not rebuild; do not broadly refactor. One bounded refactor is warranted (the capacity layer).**

**What is sound and must remain.** Four independent adversarial passes tried to break the core and could not:
- **Layer-2 mutation protocol** commits the attempt-intent row on an independent cursor **before** the network send, re-locks in a fresh transaction for consequence finalization, and routes every uncertain outcome to a read-only reconciliation that **never replays transport** (`job_dispatch.py:1300-1491`; performance annex confirms `side_cr.commit` precedes transport at `:1300-1317,1452-1491`). `[STATIC]`
- **No database lock spans a network call** — admissions, leases, and telemetry all use side cursors. `[STATIC]`
- **Idempotency** is enforced by real DB constraints (`UNIQUE(store, gid)`, `operation_scope_key`) with savepoint+IntegrityError dedup; `FOR UPDATE SKIP LOCKED` claim; backpressure hysteresis. `[STATIC]`
- **Generation fencing** sits at every remote seam and every domain webhook admission (one unfenced local-only consumer, W-4). `[STATIC]`
- **Webhook ingress** verifies HMAC over raw bytes with `compare_digest` before parsing, stores a payload-free envelope, dedups on `UNIQUE(store, delivery_id)`. `[STATIC]`
- **Root-only cron sentinel** is genuinely unspoofable from JSON-RPC (`object()` identity via `is`) — SOUND. `[STATIC]`
- **Multi-company isolation** uses global fail-closed rules (deliberately refusing the permissive NULL-company idiom); credentials/secrets locked to admin behind a sentinel-context write surface — **confirmed at runtime by direct RPC probing** (Section 10). `[RUNTIME]`

**What requires bounded refactoring (the capacity layer only).** A single global sequential drain (P-2), unbounded reconciliation/scan passes without persisted cursors (P-1, P-4, W-2), and no GC for jobs/logs/attempts (P-3). These are contained in the dispatch + scan + retention subsystems and can be corrected **without touching the mutation-safety core.**

**What must be replaced:** nothing structural. The blockers are point defects (a wrong GraphQL field, a wrong query shape, a missing review branch, admission gates, a default value, a menu parent, copy strings).

**Ownership violations:** none structural — every decision has one authoritative owner (identity/credentials/queue/mutation-attempts/webhook-ingress/mappings/readiness/dashboards/recovery each map to a single model). No manifest dependency cycles; imports follow the declared direction. The real debt is **duplicated business logic** (the savepoint-dedup pattern re-implemented ≥6× with divergent disposition vocabularies; constraint message strings copied into domain addons; RFC3339/GID helpers duplicated; `TERMINAL_JOB_STATES` redeclared in `sale_webhook`; NULL-first store scheduler implemented twice) — a maintainability risk, not a correctness one.

**Transaction/lease risks:** orphan call leases never expired (P-12); store lifecycle row lock held across an order-webhook job txn (P-14) — both P3, bounded.

**Queue/job-state, reconciliation, scalability, authorization, observability risks:** enumerated as P-1…P-4 (capacity), S-1 (authorization), P-10 (unindexed finished_at/next_retry_at + dashboards over never-GC'd tables) — all bounded and localized.

**Why a full rebuild is not justified:** every confirmed blocker is a localized fix against machinery that is more rigorous than most connectors on the market. Rebuilding would discard proven safety code to re-solve solved problems.

---

## 9. UX AND OPERABILITY ASSESSMENT

**Seamless / well-built:** the four-pillar IA is real; decision dialogs (tax, product-match, manual-gateway) and the inventory first-push and fulfillment-review forms answer 8–9 of the nine merchant questions with honest "what changed on each side / will Shopify be re-read" language; empty and no-permission states are honest ("not shown as zero"; "an empty list does not prove there are none"); the dual-condition scheduling disclosure ("needs BOTH the setting AND the cron") is exemplary.

**Dead ends (block release):** **U-1** (fulfillment review cases — no menu, no rendered card; a "Shopify cancelled a validated fulfillment" case is invisible); **U-2** (the main Sync Rules settings screen is a non-clickable heading with no route, while the wizard tells users to go there).

**Misleading promises / false-success states (block release):** **U-3** (activation says "nothing is syncing" while it is); **I-3** (consent claims a stock baseline import that never happens); **U-4** (health "Healthy" before first sync); **U-6** ("Store Settings" screen that doesn't exist / is read-only).

**Initial-sync progress problems:** no initial-sync progress surface; readiness is truthful only where the Unknown-guard is not defeated by activation-audit jobs (U-4).

**Recovery problems / role-specific:** best surface 9/9 (fulfillment review — but unreachable, U-1); manual-gateway/inventory 9/9; **core Needs-Attention list 4.5/9** and the **mutation-attempt surface 4.5/9** (U-10 — never states whether Odoo was changed; identifies the record as raw `res_model`/`res_id`; no downstream-effect text).

**Technical jargon shown to merchants (P3 pass):** mutation, lease/quiescence, idempotency key, business/exact fingerprints, payload/URI digests, HMAC epoch, A4/A7 spec codes, raw GIDs as page titles, "binding".

**Missing navigation:** U-2 (Sync Rules), U-9 (degraded banner → inactive menu), orphaned menus (HYP-017).

**Browser evidence note `[RUNTIME]`:** the web client boots correctly for a proper internal user (uid 2) in this environment; the connector role users I created were non-internal (portal) — a **test-fixture artifact, not a product defect** — so per-role screenshots were not captured. Role enforcement was instead verified more rigorously at the RPC layer (Section 10). B-4/U-2 was confirmed from the live menu tree (menu 89 → action 113 + child menu 261) plus the codebase's own documented Odoo-19 menu behavior.

**Required UX corrections (for release):** U-1, U-2, U-3, I-3, U-4, U-6, U-9, U-10 (see WP-4).

---

## 10. SECURITY AND PRIVACY ASSESSMENT

**Runtime-verified role matrix (direct RPC `call_kw` probe, bypassing menus — the mission's explicit requirement) `[RUNTIME]`:**

| Model | No-role | Auditor | Operator | User | Reviewer | Admin |
|---|---|---|---|---|---|---|
| store.credential | **AccessError** | **AccessError** | **AccessError** | **AccessError** | **AccessError** | R/W/C |
| webhook.secret | **AccessError** | **AccessError** | **AccessError** | **AccessError** | **AccessError** | R only |
| store | AccessError | R | R | R | R | R/W |
| job | AccessError | R | R/W/C | R/W/C | R/W | R/W/C |
| job.log (audit) | AccessError | R | R | R | R | R (append-only) |
| customer.binding (PII) | AccessError | R | R/C | R/C | R/W | R/W/C |
| webhook.delivery | AccessError | R | R | R | R | R (append-only) |

Credentials and webhook secrets are **unreadable by every non-admin role**; a no-connector-group internal user is denied everything; audit and delivery logs are append-only even for admin; **User and Operator have identical access** (User does not carry Reviewer's write) — the tightened C2 model, confirmed live. This independently corroborates the security workstream's static analysis.

**Controls verified good `[STATIC]`/`[RUNTIME]`:** HMAC over raw bytes with `compare_digest` before parse; HTTPS enforced; bounded 10 MB body; token resolved by digest (no timing oracle); dual-secret rotation grace; payload-free delivery envelope; every persistent model behind a global fail-closed company rule; the raw-SQL token-provenance read re-asserts company+quarantine clauses; all logger calls carry ids/counts only (no email/token/payload); test fixtures contain only synthetic canary secrets; every `cr.execute` parameterized (dynamic identifiers limited to `self._table`/constants). **No cross-company read path, no SQL injection, no secret/PII in logs found.**

**Per-surface tests:**
- **Credential protection / webhook-secret protection:** admin-only, verified live (table above).
- **No-access role:** denied everything, verified live.
- **Auditor:** read-only on data models — **but** can invoke five privileged cron methods (S-1).
- **Operator / User / Reviewer:** method-level enforcement consistent; Reviewer is vestigial (S-4).
- **Administrator:** full where expected; append-only logs even for admin.
- **Direct JSON-RPC methods:** probed — the data ACLs hold; the gap is at the cron entrypoints (S-1).
- **Cron entry points:** **S-1** — `run_drain`, `pii.retention.run_sweep`, `stale.owner.sweep.run_sweep`, `inventory.service.run_inventory_push_scan`, `media.export.service.run_media_status_poll` callable by a read-only Auditor; `run_media_status_poll` callable by any internal user. **[RUNTIME-verified]**
- **ACLs / record rules / multi-company / cross-store isolation:** fail-closed global rules; no cross-company or cross-store read path found.
- **Sudo boundaries:** sentinel-context write surface for credentials/secrets; root-only cron sentinel unspoofable.
- **PII:** disciplined on the order path; **O-3** latent raw-PII in the (currently-unwired) customer-import job path — must be redacted before that job type is enabled. **S-5** secrets plain at rest — an explicitly accepted residual that **must be stated in release/privacy docs.**
- **Logs / mutation evidence:** ids/counts only; mutation-attempt evidence is commit-before-send and honest.
- **Secret scanning:** no live secret in the diff; fixtures are synthetic canaries.
- **Public-distribution/privacy obligations:** no OAuth install, no `customers/data_request` / `customers/redact` / `shop/redact` handlers, no protected-customer-data workflow. **Correct and sufficient for custom-app distribution; insufficient for a public Shopify App Store listing.**

---

## 11. AUTOMATED TEST AND CI ASSESSMENT

**Exact commands / SHA:** the repo's own `tools/run_connector_suite.sh` (fail-closed) at head `6bb05c0c`, Odoo pinned `30bde9ff…`, plus CI runs 32594700478 (push) & 32594702709 (pull_request).

**Counts (first-party from the CI job log and my local run):**

| Pass | Failed | Errors | Tests |
|---|---|---|---|
| Fresh install | 0 | 0 | 2,760 |
| Warm update | 0 | 0 | 2,760 |
| Migration from `50b770a3` (5 scripts) + idempotent repeat | 0 | 0 | 2,659 |
| Migration from `0a15b176` (4 scripts) + repeat | 0 | 0 | 2,659 |
| Non-standard / concurrency | 0 | 0 | 62 |
| Tours | — | — | **40/39** required |
| HOOT | — | — | dashboard + export-diff + **setup-wizard** all verified |

Runtime ≈ 56 min suite step. Skips: 0 unexpected (the runner's `--self-test`, which I executed, proves it fails on an unexpected skip, a missing tour, a missing HOOT marker, or a same-version "migration").

**Migration-test evidence:** real migration scripts execute (5 and 4 respectively) and idempotent repeats produce no double effect — migrations only run when the installed version is strictly lower than the manifest, verified.

**HOOT / UI-test evidence:** the setup-wizard HOOT suite (the gap that blocked the older `271164ce` candidate) is present and verified at this head.

**What the tests prove:** the connector installs fresh, warm-updates, upgrades from two older shapes, survives genuine multi-connection races (asserted distinct backend PIDs), and renders its three UI suites.

**What they do NOT prove (and the CI file says so):** **zero Shopify operations are performed**, so the suite is structurally blind to **A-1/A-2** (live-schema contract violations). It is **supporting evidence, not acceptance** — DEC-041 D8 makes the exact-SHA Odoo.sh run the Tier-1 authority, and **no Odoo.sh build exists at this head** `[BLOCKED]`. It does not exercise real orders/fulfillments end-to-end.

**False-confidence gaps (named):** no test covers `_bind_created_variants` (PR-2), the same-second dedup drop (O-4), price-neutral edit divergence (O-5), the scan-ceiling behavior (O-6/W-2), or `technical_detail` PII redaction (O-3). **Python-version deviation:** CI uses 3.12; my local replication used 3.11.15 (noted; not material to the defects found).

**Net:** green CI here is necessary and real, but it is structurally blind to the live-API contract defects that are the primary release blockers.

---

## 12. PUBLIC-RELEASE REQUIREMENTS

**Mandatory release blockers (must be closed):** A-1, A-2 (live-schema correctness); O-2, PR-1 (destructive/silent business outcomes); PR-2/PR-3/PR-8 (export variant-add); I-1/I-2 (inventory wedge); I-3, U-3 (false truthfulness at consent/activation); U-1, U-2 (broken core journeys); S-1 (authorization). Then an **exact-head Odoo.sh build** and a **live-store end-to-end UAT** (currently 0 orders exercised).

**Required UX corrections:** U-1, U-2, U-3, I-3, U-4, U-6, U-9, U-10 (Section 9 / WP-4).

**Required security corrections:** S-1 (cron authorization); O-3 (PII redaction before enabling the customer-import job); document S-5 (secrets plain at rest); S-2 (uninstall revocation).

**Required migrations:** none new for the blockers themselves (they are code/copy/route fixes); any schema field added for status-seeding (PR-1) or admission-state (I-1/I-2) needs a migration + idempotent-repeat test consistent with the existing migration harness.

**Required documentation:** supported-scale limits (stores / products / orders-per-window / webhooks-per-minute — several exist silently and must be published: W-2/W-8/P-2); secrets-plain-at-rest disclosure (S-5); uninstall/credential-revocation steps (S-2); store-permanence contract (S-3); known-unsupported behavior (product/variant deletion, weight, refund credit notes); a recovery guide; an API-version-upgrade policy.

**Required Shopify distribution / authentication obligations:** as a **custom-app Odoo module**, the above suffices. For a **public Shopify app** (not currently supported): OAuth authorization-code install, the three mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`), protected-customer-data handling, and billing — **none exist today.**

**Required operational runbooks:** drain-capacity + retention operations (P-1…P-4), reconnect/rotation procedure, exception-triage guide (Needs-Attention + mutation-attempt).

**Post-v1 backlog:** the P3 set — jargon-to-merchant-language pass, dead-code cleanup, vestigial Reviewer removal (S-4), duplicate-logic consolidation, i18n, indexing (P-10…P-15).

---

## 13. SEVEN ORDERED RELEASE-CLOSURE WORK PACKAGES

Dependency-ordered, bounded, no optional features. Each closes named findings; each must add executing tests + genuine Odoo.sh runtime evidence at its own exact SHA (per DEC-041/§13).

**WP-1 — Live-API contract correctness (highest priority).**
- Objective: order import and fulfillment reads succeed against 2026-07.
- Findings closed: **A-1, A-2** (and unblocks P-1/W-6 reads, Mode 2).
- Files/subsystems: `shopify_connector_sale/…/shopify_connector_order_importer.py` (line-item queries), `shopify_connector_fulfillment/…/shopify_connector_fulfillment_reader.py` (`ORDER_FULFILLMENTS_QUERY`).
- Implementation: replace `priceAfterAllDiscountsBeforeTaxesSet` → `discountedUnitPriceAfterAllDiscountsSet`; rewrite fulfillments to the plain-list shape.
- Migration: none. Tests: schema-conformance test executing **every** pinned order/fulfillment query against 2026-07; one live-canary order-import + fulfillment-read test.
- Backend validation: green order/fulfillment import against a real dev-store order. Browser UAT: order appears in Odoo; fulfillment status observed.
- Dependencies: none. Exclusions: no new order fields/features. Acceptance: no `undefinedField`/shape error against 2026-07; canary order imports. Completion evidence: exact-SHA Odoo.sh run + canary logs.

**WP-2 — Destructive / silent business outcomes.**
- Objective: no cancelled/unpaid order stays silently shippable; no imported product self-proposes unpublish.
- Findings closed: **O-2, PR-1** (keeps the export freeze liftable). (Fold in O-4/O-5 disclosure/handling if cheap.)
- Files: `order_importer.py` (`_refresh_existing` review routing + attention filter), `product_export_seams.py`/`_service.py` (status initialization).
- Implementation: cancellation/void/expiry after import → `status='review'` + Needs-Attention; imported ACTIVE product's first export preview contains no `status` row unless explicitly managed.
- Migration: if status-seed is stored, add + idempotent-repeat test. Tests: transition tests per state; DRAFT-flip absence test.
- Backend/UAT: cancel a dev-store order post-import → appears in review; export preview of an imported ACTIVE product shows no status diff.
- Dependencies: WP-1 (to import orders at all). Exclusions: refund credit notes (backlog). Acceptance: named tests green + Odoo.sh evidence.

**WP-3 — Export variant-add + inventory first-push wedges.**
- Objective: adding a variant finalizes correctly; a stock move or re-scan never wedges an inventory pair.
- Findings closed: **PR-2/PR-3/PR-8, I-1/I-2**.
- Files: `product_export_service.py` (`_bind_created_variants` iterate confirmed ids; variants-create pre-C2 identity validation; later-variant SKU init), `inventory_service.py` (route non-confirmed pairs like the scan's `pending` branch; terminal-skip the handler's first-push block).
- Migration: none unless admission-state persisted. Tests: mixed variants-create with an SKU-less sibling; stock-move-before-first-scan; second scan over a previewed pair.
- Backend/UAT: add a variant to an exported product → finalizes; force a pre-preview stock move → no permanent wedge.
- Dependencies: none. Exclusions: none. Acceptance: named tests green + Odoo.sh evidence.

**WP-4 — Onboarding & IA truthfulness.**
- Objective: consent/activation copy matches behavior; core screens reachable.
- Findings closed: **I-3, U-3, U-1, U-2, U-6, U-9** (and U-4 healthy-pre-sync gate).
- Files: `setup_wizard.py`/`.xml`/`.js` (inventory direction + activation copy + next-action), `fulfillment/…_menus.xml` (reactivate Review Workspace or render the feed), `inventory/…_menus.xml` (self-child for Sync Rules), banner/menu-name fixes, health readiness gate.
- Migration: none. Tests/UAT: browser walk of onboarding + Configuration with **no dead-end and no false statement**; fulfillment review reachable; Sync Rules opens.
- Dependencies: none. Exclusions: full jargon pass (P3 backlog). Acceptance: onboarding + IA tour green + Odoo.sh browser evidence.

**WP-5 — Authorization gate.**
- Objective: cron entrypoints not callable by read-only/no-role users.
- Findings closed: **S-1** (and remove vestigial Reviewer, S-4, if cheap).
- Files: the five methods — add `env.su or admin-group` guard (the existing `run_retention_sweep` pattern).
- Migration: none. Tests: RPC probe as Auditor/no-role → refused (I have the exact probe script).
- Dependencies: none. Exclusions: none. Acceptance: probe shows all five refused for Auditor/no-role + Odoo.sh evidence.

**WP-6 — Capacity & retention (bounded refactor) OR documented + enforced caps.**
- Objective: the connector survives its advertised volume, or ships with enforced limits.
- Findings closed: **P-1/P-2/P-3/P-4, W-2, W-6, W-8**.
- Files: dispatch (`shopify_connector_job_dispatch.py`, `cron_drain.xml`), scans (`product_scan.py`, `order_scan.py`, `fulfillment_scans.py`, `inventory_service.py` push scan), retention (`webhook_delivery.py`, `job_log.py`).
- Implementation: EITHER persisted-cursor pagination + drain fan-out/`_trigger()`-on-enqueue + retention GC, OR publish and preflight-enforce supported-scale limits.
- Migration: retention/GC may need a one-time archival migration + idempotent-repeat test. Tests/UAT: load test at the stated ceiling completes within the cron window; retention shows bounded growth.
- Dependencies: WP-1 (fulfillment reads must work before P-1 load is meaningful). Exclusions: no queue-engine rewrite. Acceptance: documented scale statement + a passing load test at the stated ceiling + Odoo.sh evidence.

**WP-7 — Release documentation & disclosures.**
- Objective: every supported/unsupported behavior, limit, and residual is written down.
- Findings closed: doc requirements in Section 12 — **S-2/S-3/S-5 disclosures**, supported scope + scale limits, recovery guide, API-version policy, distribution-model statement (custom-app, not public Shopify app).
- Files: `docs/**` (governance-compliant Markdown). Tests/UAT: link/consistency/path checks (documentation-only batch — no fabricated runtime campaign).
- Dependencies: WP-1…WP-6 (documents the corrected behavior). Acceptance: docs reviewed against the shipped behavior; every Section-12 item present.

Then, and only then, the acceptance gates in Section 14, executed **twice on one immutable commit.**

---

## 14. OBJECTIVE FINAL RELEASE GATES

Each gate has an objective pass/fail rule and required evidence.

| # | Gate | Pass rule | Required evidence |
|---|---|---|---|
| G-1 | Exact source identity | reviewed/accepted SHA == tested SHA == Odoo.sh-built SHA | fingerprint block matching all three |
| G-2 | Automated tests | fresh + warm + both migrations + concurrency all 0 failed/0 err; tours 40/39; HOOT 3/3 | CI job log at the exact SHA |
| G-3 | CI | both runs `success` at the exact head | Actions run ids |
| G-4 | **Odoo.sh exact-head build** | build **succeeds** at the accepted SHA | Odoo.sh build log (Tier-1 — **not yet produced** `[BLOCKED]`) |
| G-5 | Installation | 11 modules install clean | Odoo.sh install log |
| G-6 | Upgrade | version-to-version migrations run + idempotent | migration logs |
| G-7 | Migration | scripts run only when installed<manifest; idempotent repeat no-op | migration logs |
| G-8 | Backend product flow | import create/update + export review→confirm with no unintended status change (PR-1 closed) | Odoo.sh + dev-store evidence |
| G-9 | Backend inventory flow | first-push confirm; no pair wedge (I-1/I-2 closed); copy truthful (I-3 closed) | dev-store push evidence |
| G-10 | Backend order flow | real order imports (A-1 closed); cancellation/void routed to review (O-2 closed) | dev-store order evidence |
| G-11 | Backend fulfillment flow | reads succeed (A-2 closed); Mode 2 activatable | dev-store fulfilled-order evidence |
| G-12 | Webhooks | HMAC-verified ingress; dedup; every supported topic proven to discover (W-3/W-5 closed or documented) | delivery records |
| G-13 | Scheduled reconciliation | eventual discovery guaranteed for every supported topic within a bounded pass | reconciliation run evidence |
| G-14 | Failure / recovery | every shipped exception surface reachable (U-1) and informative (U-10) | browser UAT |
| G-15 | Security | no secret/PII exposure; no cross-company path; **no read-only role can initiate writes/Shopify traffic (S-1 closed)** | RPC probe results |
| G-16 | Roles | role matrix passes by direct RPC (creds/secrets admin-only; no-role denied) | RPC matrix |
| G-17 | Multi-company | no cross-company read path | probe |
| G-18 | Multiple stores | fair per-store drain OR documented+enforced store cap (P-2) | load evidence |
| G-19 | Performance | load test at the stated ceiling completes within cron windows (P-1…P-4, W-2) | load-test log |
| G-20 | Supported limits | published + preflight-enforced (W-2/W-8/P-2) | docs + enforcement test |
| G-21 | Browser UAT | onboarding + all four pillars walked with no dead-end and no false statement | screenshots/tour |
| G-22 | **Two complete UAT executions on one unchanged SHA** | both full UATs pass on the identical commit, including real orders/fulfillments end-to-end | two dated UAT logs, same SHA |
| G-23 | Documentation | every Section-12 doc item present and matches shipped behavior | docs review |
| G-24 | Public-distribution classification | shipped claim == implementation (custom-app, **not** public Shopify app) | manifest/docs statement |

**Currently open gates at this head:** G-4 (no Odoo.sh build) `[BLOCKED]`, G-10/G-11 (0 orders exercised) `[BLOCKED]`, G-22 (no UAT executed), plus every gate gated on the 15 unresolved P1 findings.

---

## 15. FINAL STATEMENT

**NOT ASSURED — MATERIAL RELEASE BLOCKERS CONFIRMED**
