# Competitor Gap Analysis Against the Accepted Blueprint

> **Purpose.** Reconcile the captured competitor evidence
> ([`competitor-evidence-reconciliation.md`](./competitor-evidence-reconciliation.md),
> [`competitor-feature-screen-map.md`](./competitor-feature-screen-map.md))
> against the **accepted** blueprint work (DEC-003, DEC-010–DEC-015; AR-002–AR-012;
> RA-001–RA-023; the four master-blueprint files; the MBQ register) and answer:
> **what have we already covered, what have we missed, what can we do better,
> what should we avoid, and does any accepted decision need an amendment
> candidate?** This is an **evidence and gap-analysis** deliverable, not a UX
> sprint and not Part D. It **draws no new decisions**; it does not modify any
> accepted decision; the no-code / research-first gate (`CLAUDE.md` §4–§5) is in
> force. Amendment *candidates* (never amendments) are collected separately in
> [`../03-architecture/blueprint-amendment-candidates.md`](../03-architecture/blueprint-amendment-candidates.md).
>
> **Reconciliation date:** 2026-07-03. **Evidence access dates:** 2026-06-30
> (all), **Teqstars 2026-07-01**. **Extends, does not duplicate,** the existing
> [`gaps-opportunities.md`](./gaps-opportunities.md) (opportunity IDs `O-*`) and
> [`avoid-list.md`](./avoid-list.md) (anti-pattern IDs `A-*`); this file maps
> those items onto the **now-accepted** blueprint and states, for each, whether
> the blueprint has already absorbed it.

---

## 0. Headline reconciliation finding (inference)

**The accepted blueprint has already absorbed the substance of the competitor
evidence at the *behaviour and architecture* level.** Nearly every competitor
strength and market whitespace that the research surfaced already has an
accepted home:

- Command-center dashboard fusing SH-style monitoring + VT-style diagnostics →
  **DEC-013 §F** (resolves the `O-DASH-1` whitespace at behaviour level).
- Recovery-first, reason-coded error center (EM Log Book bar) → **DEC-013 §D.11/§H,
  DEC-012 flow 5** (`O-LOG-1`, `A-LOG-1/2/3`).
- Automatic retry/backoff (VT-only in the market) → **DEC-009 / DEC-013 §D.5**
  (`O-REL-3`, `A-RET-1`).
- `@idempotent` writes + persistent keys (VT-only) → **DEC-009 / DEC-013 §D.6**
  (`O-REL-1`, `A-RET-3`, `A-IMP-2`).
- First-class reconciliation (market whitespace — nobody demonstrates it) →
  **DEC-005 / DEC-013 §D.1** (`O-REL-1`, `A-SYNC-2`).
- Rate-limit / GraphQL-cost-aware throttling (market whitespace) → **DEC-004 /
  DEC-013 §B.3 + §D pacing** (`O-REL-2`, `A-SYNC-5`; exact params open = MBQ-51).
- Multi-location per-`(inventory_item_id, location_id)` mapping (EM/VT/TQ) →
  **DEC-010** (`A-INV-2`, RA-019).
- Dry-run / preview before destructive write (VT Preview/Report) → **DEC-004
  productSet preview + DEC-012 flows 6/7/8** (`O-CFG-1`, `A-CFG-1`, `A-IMP-1`).
- FulfillmentOrder-based fulfillment, never legacy (Tier-1) → **DEC-011**
  (`A-FUL-1`, RA-022).
- Honest freshness / no "real-time" overstatement (WK/EC/SH anti-pattern) →
  **DEC-013 §D.11** (`A-UX-1`).
- HMAC verification + webhook-ID dedup + fast ack → **DEC-005 / DEC-013 §D.1**
  (`A-SYNC-6`).

**Therefore the genuine, still-open gaps are overwhelmingly at the *screen-design*
level — exactly the scope of Part D / MBQ-53, which this evidence pack feeds.**
Competitors expose *concrete screens* (VT traffic-light webhook health, EM
queue + reason-coded Log Book, SH dashboard + daily-activity chart, VT
Preview/Report dry-run, TQ click-and-collect status) that our blueprint fixes
only as *behaviour and state*. Part D must turn that accepted behaviour into
premium, Odoo-native screens. **No accepted decision is contradicted by the
competitor evidence.** (See §C for the per-decision detail and §F/amendment-
candidates for the handful of items worth a Part D or future-phase flag.)

---

## C. Gap analysis against accepted decisions

**Gap-type legend:** `Already covered` · `Covered — UX/screen detail needed
(Part D)` · `Covered — open MBQ remains` · `Missing from MVP (candidate)` ·
`Non-MVP / later phase (confirmed deferral)` · `Should avoid` · `Needs amendment
candidate`.
**Severity legend:** `Critical before implementation` · `Important before Part D`
· `Useful later` · `Not relevant`.

### C.1 — vs DEC-003 (MVP scope) & DEC-007 (scope clarifications)

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Controlled bidirectional product onboarding (import + export/update) demonstrated by EM/VT/WK/SH/TQ | **DEC-003 (PR #55 correction) + DEC-007 §1** include controlled product/variant export/update in MVP | Already covered | Not relevant | None — evidence confirms the accepted scope is market-baseline, not luxury. |
| 2 | Payout reconciliation (EM, TQ — both Shopify-Payments-only) | **DEC-003 Domain 9 / Domain 12** defers payout & accounting automation; `A-PAY-1` gates it to Shopify Payments | Non-MVP / later phase (confirmed deferral) | Useful later | Keep deferred; premium add-on candidate (`O-PREM-3`). No amendment. |
| 3 | Full refunds/returns/cancellation lifecycle (EM/VT/SH/TQ) | **DEC-003** defers refunds/returns/cancellations; idempotent-refund regression mandatory if ever added | Non-MVP / later phase | Useful later | Keep deferred; if added later, `A-PAY-2`/RA (double-refund) guard is mandatory. |
| 4 | Shopify Markets/Catalogs, B2B, gift cards, POS, metafields (EM/VT/TQ/SH) | **DEC-003 non-goals** list all as premium add-ons / later | Non-MVP / later phase | Useful later | Keep as feature-flagged add-ons; no MVP or Part D impact. |
| 5 | Customer export with email-dedup (EM) | **DEC-003** defers customer export (C-CUST-02); MVP = import + match | Non-MVP / later phase | Useful later | Keep deferred; competitor import-only norm (WK/EC/TQ) supports it. |
| 6 | Order fraud/risk import (VT order-risk fields) | **DEC-003** defers C-ORD-05 (fraud/risk) | Non-MVP / later phase | Useful later | Keep deferred; note as future add-on. |
| 7 | Bulk operations for large backfills (EM batches; none use Shopify Bulk) | **DEC-003** = not a user-facing feature; internal-need assessment routed to AR-002 | Covered — open MBQ | Useful later | No change; internal-only mechanism question (MBQ-15). |

### C.2 — vs DEC-013 (core substrate: setup, health, jobs, logs, errors, dashboard, permissions)

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Guided setup wizard + explicit **Test Connection** (WK, TQ) | **DEC-013 §E** 11-step wizard; `setup_readiness_check` test-connection with pass/fail + reason | Already covered / screen detail | Important before Part D | Part D designs the wizard screens; behaviour fixed. |
| 2 | Credential masking / no plaintext (all custom-app) | **DEC-013 §B.2** masked, no-read-back, never-logged | Already covered | Not relevant | None; at-rest mechanism stays MBQ-04. |
| 3 | Queue/job monitor with failure counts (EM Data Queues, SH Queue Dashboard) | **DEC-013 §D.1–D.3, §G** internal cron queue, 6 sources, 10 states, sync-center UI | Covered — UX/screen detail needed | Important before Part D | Part D designs the sync-center screen; EM/SH are the visual bar. |
| 4 | Reason-coded Log Book / Mismatch Log (EM); Activity-on-failure (TQ) | **DEC-013 §D.4 (16-class registry), §D.11, §H** error center | Covered — UX/screen detail needed | Important before Part D | Part D designs error-center + log screens; EM Log Book is the reference. |
| 5 | Automatic retry (VT-only); manual re-run/re-export (EM/TQ/SH) | **DEC-013 §D.5** classified retry (auto-with-backoff + verification-read-before-retry + manual-fix classes) | Already covered | Not relevant | Behaviour exceeds market; Part D renders the state-conditional retry controls (§G.4). |
| 6 | Unified dashboard: SH monitoring + VT diagnostics (neither has both) | **DEC-013 §F** recovery-first command center (9 exception-first cards, every count clickable, no vanity metrics) | Covered — UX/screen detail needed | Important before Part D | Part D designs the dashboard. **One nuance → amendment candidate (BAC-001):** SH's daily-activity *time-series* trend vs DEC-013 §F "no vanity-only metrics." |
| 7 | Traffic-light webhook health with named cause (VT: yellow = check `web.base.url`) | **DEC-013 §B.3** health state (normal/throttled/degraded + plain reason) + §H error center | Covered — UX/screen detail needed | Important before Part D | Part D realizes the health indicator + diagnostic colour/fix-hint (BAC-005). Best-in-class pattern to match. |
| 8 | Granular access-rights groups (SH; EM Odoo user rights) | **DEC-013 §J** four-role blueprint + capability matrix (deny-by-default, record rules) | Covered — open MBQ | Critical before implementation | Groups/CSVs stay MBQ-44/45 (implementation). Part D: admin-vs-functional surface split. |
| 9 | Field-mapping "test against live data" (VT) | **DEC-013 §D.2** `export_preview_dry_run` (read-only preview job) | Covered — UX/screen detail needed | Useful later | Part D input (BAC-002): a mapping-test/preview surface beyond dry-run export. |
| 10 | CSV/XLSX mapping fallback for non-SKU catalogs (EM) | **DEC-006/DEC-013 §C.5** match keys binding→SKU→barcode→manual; no CSV-map surface | Missing from MVP (candidate) | Useful later | Future MBQ / non-MVP (BAC-003); do not add to MVP. |

### C.3 — vs DEC-012 (operator flows) & setup-UX principles

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Toggle-dense config screens (EM/TQ/SH — 10+ toggles, dev-mode-gated) | **setup-ux P3 (progressive disclosure) + DEC-012** | Should avoid / screen detail | Important before Part D | Part D must apply progressive disclosure; competitors are the cautionary example (`A-UX-3`, BAC-006). |
| 2 | Preview/dry-run before push (VT Preview/Report) | **DEC-012 flows 6/7/8** mandatory preview before create/bind/destructive write | Already covered | Not relevant | Part D renders the preview screens; behaviour fixed. |
| 3 | Irreversible actions (EM Force Done, TQ Force Restock, VT Force Full Fulfillment) with weak/strong guards | **DEC-012** destructive-write guard + `blocked_manual_review` + audit | Already covered / screen detail | Important before Part D | Part D designs strong-confirmation UX (`A-RET-2`, BAC-011). |
| 4 | Click-and-collect / local pickup order status (TQ Ready-for-Pickup → Picked-Up) | **DEC-011/DEC-012 flow 9** fulfillment via FulfillmentOrder; pickup/local-delivery status not specifically addressed | Needs amendment candidate | Useful later | Future scope note (BAC-004); not MVP. Flag for later, do not add now. |
| 5 | Honest latency labels + "last synced" per domain (market overstates "real-time") | **DEC-012 flow 3 + DEC-013 §F** per-domain honest freshness, mechanism label | Already covered | Not relevant | Part D renders the per-domain freshness display. |
| 6 | Four-role model maps to real personas | **DEC-012 flow 10** four conceptual roles (Admin/Operator/Reviewer/Auditor) → P1–P3 | Already covered — open MBQ | Critical before implementation | Groups = MBQ-44/45. No change. |

### C.4 — vs DEC-010 (inventory) & DEC-015 (inventory/fulfillment blueprint)

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Stock-source choice: Free-to-Use / On-Hand / Forecasted (WK/TQ/EM/VT) | **DEC-010/DEC-015 §A.4** `available` default; `on_hand` justification-gated; `committed` never; Free-to-Use = semantic source | Covered — open MBQ | Critical before implementation | Exact ORM source = MBQ-32; whether `on_hand` is a UI choice = MBQ-35. No change. |
| 2 | Multi-location "External Location" grid with default fallback (VT); combine-locations + third-party exclusion (TQ) | **DEC-010/DEC-015 §A.5/§B** explicit non-inferred mapping, inventory-owned, multi-location-capable | Already covered / screen detail | Important before Part D | Part D designs the location-mapping grid; VT/TQ are the reference. |
| 3 | Import stock → manual Inventory Adjustment (EM friction); Validate-Inventory-Adjustment toggle (TQ) | **DEC-010** one-time controlled reviewed baseline import; ongoing apply-mode = MBQ-34 open | Covered — open MBQ | Important before Part D | Apply-mode (review-then-apply vs auto-apply) stays ChatGPT-owned MBQ-34. Avoid EM's manual-adjustment friction (`A-INV-1`). |
| 4 | No competitor shows a **first-push safety screen** before the first Odoo→Shopify write | **DEC-007 §4 / DEC-010 / DEC-012 flow 8** mandatory unweakened first-push guard | Already covered — premium whitespace | Important before Part D | **Differentiator.** Part D must design the first-push preview/confirm screen (BAC-007); nobody in the market has it. |
| 5 | "Real-time on stock move" optional push (VT/TQ) | **DEC-010** layered sync (scheduled + manual + event-driven enqueue); never webhook-only | Already covered — open MBQ | Useful later | Event-source classification = MBQ-62; webhook payload = MBQ-63. No change. |

### C.5 — vs DEC-011 (fulfillment) & DEC-015

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Fulfillment + tracking write-back (EM/VT/SH/TQ); fulfillment-ID write-back (SH) | **DEC-011/DEC-015 §B** FulfillmentOrder-based `fulfillmentCreate` + `fulfillmentTrackingInfoUpdate`; validated picking trigger | Already covered | Not relevant | Tracking field source verified (MBQ-39); module dep = MBQ-60. |
| 2 | Multi-package (EM Put-in-Pack); per-warehouse transfers (VT) | **DEC-011/DEC-003 C-FUL-02** deferred to Phase 2 (sequential backorder events in MVP) | Non-MVP / later phase | Useful later | Keep deferred; `A-FUL-2` noted. |
| 3 | Customer notification default & control (VT/EM/TQ options) | **DEC-011 §B.6 / DEC-007 §5** default OFF, persisted at enqueue, global/per-store | Already covered — open MBQ | Important before Part D | Per-order override granularity = MBQ-41 (ChatGPT). `A`-consistent (`RA-009`). |
| 4 | Fulfillment scopes (EM documents assigned/merchant/third-party) | **DEC-011** FulfillmentOrder posture; scope list in setup | Already covered | Not relevant | `A-FUL-3` handled via readiness checks. |
| 5 | "Needs Shopify Re-Export" recovery flag (SH) | **DEC-013 §C.6 stale binding + `blocked_manual_review` + reconciliation** | Already covered | Not relevant | Part D surfaces the recovery affordance (BAC-012); concept already covered. |

### C.6 — vs DEC-014 (product / customer / sale-order blueprint)

| # | Competitor evidence | Accepted coverage | Gap type | Severity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Draft-safe export (TQ empty-Sales-Channels; VT draft-for-review) | **DEC-014 §A.10** draft-first: `status:DRAFT` + unpublished-by-default + explicit `publishablePublish` | Already covered | Not relevant | Part D renders channel-selection UX (MBQ-25). |
| 2 | Variant handling (TQ Listing Items; VT 250-variant fix) | **DEC-014 §A.5** variants ≤2,048; bulk-variant vs productSet direction (MBQ-23) | Already covered — open MBQ | Important before Part D | Mutation choice = MBQ-23; media delete-on-omit = MBQ-24. |
| 3 | Customer multi-key matching (VT email/name/phone; TQ multi-field; EM email-link) | **DEC-014 §B.13** email = sole automatic key; phone/name advisory-only | Already covered | Not relevant | Accepted decision (MBQ-31); competitor multi-key is advisory in our design by choice. |
| 4 | No-PII plan handling (VT Basic-plan default-customer) | **DEC-014 §B.7** single flagged fallback partner per store, only for genuine no-PII | Already covered — open MBQ | Important before Part D | Shared-vs-per-order granularity = MBQ-29. Avoid inventing PII. |
| 5 | Payment gateway → journal mapping (TQ/SH matrix) | **DEC-014 §C.10** gateway→journal as classification/routing input only (no posting) | Already covered — open MBQ | Useful later | Schema = MBQ-30; note: our design deliberately does NOT automate accounting (RA-010). |
| 6 | Order totals/tax/shipping/discount capture (EM multi-payment; TQ duties/tips) | **DEC-014 §C** financial-evidence capture + **total-check guard** | Already covered — open MBQ | Critical before implementation | Total-check tolerance = MBQ-56; tax representation = MBQ-27. |
| 7 | Order-import screens (EM Order Config; TQ per-gateway workflow) | **DEC-014 §C.14 (MBQ-26)** no dedicated order-import screen; error-center + inline financial-evidence breakdown | Already covered | Not relevant | ChatGPT-accepted; Part D renders the financial-evidence breakdown in the error/sync center. |

---

## D. What we can do better (premium differentiators)

Each item cross-references the existing `O-*` opportunity and states the accepted
blueprint home + the Part D / implementation implication. **These are
inferences/recommendations, not decisions.**

| Differentiator | Competitor weakness / market gap | Accepted blueprint coverage | Part D design implication | Later implementation implication | Risk |
| --- | --- | --- | --- | --- | --- |
| **Demonstrated correctness core** (`O-PREM-1`, `O-REL-1/2/3`) | Only VT mechanizes `@idempotent`; **nobody** surfaces reconciliation or rate-limit throttling | DEC-009 (idempotency, classified retry), DEC-005/DEC-013 (reconciliation, layered sync), DEC-004 (cost-aware pacing) | Design a **reconciliation status surface** ("last reconciled / drift found") and a **throttle/health indicator** (BAC-008/009) | Persistent idempotency keys, cost-aware client (MBQ-14/20/51) | Over-promising "real-time"; must label freshness honestly (`A-UX-1`) |
| **Best operator experience** (`O-PREM-2`, `O-DASH-1`, `O-LOG-1`) | SH monitoring + VT diagnostics never combined; EC email-only | DEC-013 §F/§H, DEC-012 flows 3/5 | Unified command center + recovery-first error center screens; every count clickable | Dashboard aggregation from job/log abstraction (no parallel store, RA-013) | Vanity metrics (DEC-013 §F.4) — keep exception-first |
| **Effortless install + real reliability** (`O-SET-1/2`) | VT needs `odoo.conf` edits + excludes Odoo Online; EM trailing-slash footgun; EC gated guide | DEC-005 (internal cron queue, no mandatory `queue_job`), DEC-013 §E (guided wizard + readiness) | Design a one-screen readiness check + inline credential validation | Turnkey install; Odoo.sh/on-prem prerequisites (MBQ-10) | `queue_job` default was rejected (RA-004) — keep it optional |
| **Better first-push safety** (unique whitespace) | **No competitor** shows a first-push guard screen | DEC-007 §4 / DEC-010 / DEC-012 flow 8 | Design the first-push preview + confirm + recorded-source-of-truth screen (BAC-007) | First-push confirmation record schema (MBQ-38) | None — pure differentiation; ensure it is not skippable |
| **Better matching UX** (`O-DUP-1`) | Competitor dedup keys mostly implicit | DEC-006/DEC-013 §C (documented keys, preview, stale handling) | Design the matching/duplicate-prevention preview screen ("create N, link M, N ambiguous") | Per-domain binding models (MBQ-55) | Name-only matching (RA-006) — never auto |
| **Better logs / audit trail** (`O-LOG-1`, EM Log Book bar) | EC email-only; retries mostly manual | DEC-013 §D.10–D.12 audit (attempted/written/skipped/who-confirmed) | Design reason-first log rows with expandable technical detail | Job/log model shape (MBQ-19) | Stack-trace-as-primary-UX (RA-016) |
| **Better financial-evidence visibility** (`O-PREM-3` context) | Order financial evidence buried or accounting-automated | DEC-014 §C financial-evidence capture + total-check guard (no accounting automation) | Design the inline financial-evidence breakdown in the error/sync center (MBQ-26) | Total-check tolerance (MBQ-56) | Silent invoice/payment creation (RA-010, DEC-003 guard) |
| **Better location/fulfillment mismatch handling** | Competitors don't surface location-mismatch as a first-class exception | DEC-011/DEC-015 §B.8 live `assignedLocation` authoritative → `ambiguous match` | Design the fulfillment location-mismatch review screen | Location-confirmation mechanism (MBQ-42) | Fulfilling from a mismatched location (RA-023) |
| **Better manual-review flows** | Competitors lack a dedicated review-owner surface | DEC-012 flow 10 Reviewer role + `blocked_manual_review` sub-reasons | Design the manual-review queue with the six specific sub-reasons | Approval audit (who/when) | Collapsing all failures into one generic state |
| **Better modularity & enable/disable clarity** (`O-MOD-1`) | Monolithic vs fragmented both exist in market | DEC-008/DEC-013 §A/§I (layered family + per-store domain enablement) | Design the domain enable/disable settings with history-preservation messaging | Feature-flag mechanism (MBQ-07 direction accepted; detail open) | Giant module (RA-011) / micro-explosion (RA-012) |
| **Better testability / QA readiness** (`O-TEST-1/2`) | Poor evaluability across the field; VT's disclosed CRITICAL bugs | `CLAUDE.md` §9 DoD; built-in self-test in DEC-013 §E readiness | Design a "test sync / self-check" affordance | Regression tests for classic defects (`A-IMP-4`) | Shipping without regression tests |

---

## E. What to avoid (practical avoid-list, reconciled)

Extends [`avoid-list.md`](./avoid-list.md); each maps a competitor anti-pattern to
its accepted guard, so Part D and implementation do not reintroduce it.

| Avoid | Competitor evidence | Accepted guard (already prevents it) | Part D / impl note |
| --- | --- | --- | --- |
| Cluttered / toggle-dense setup (`A-UX-3`, `A-CFG-3`) | EM/TQ/SH 10+ toggles | setup-ux P3 progressive disclosure; DEC-013 §E stepwise wizard | Part D must not replicate the dense single form |
| One giant settings screen | EM/TQ instance form | DEC-012 store-settings flow (7 grouped items); DEC-013 §I | Group by domain; advanced tier |
| Silent sync without clear logs (`A-LOG-1`) | EC email-only | DEC-013 §D.11 in-app reason-coded log = source of truth | Alerts are secondary to the log |
| Weak retry visibility (`A-RET-1`) | WK/EM/SH manual-only | DEC-009/DEC-013 §D.5 classified retry + §G.4 state-conditional controls | Never one generic retry button |
| No first-push guard (`A-INV`-adjacent, RA-008) | No competitor has one | DEC-007 §4 / DEC-010 mandatory guard | Must be non-skippable in Part D |
| No duplicate-prevention explanation (`O-DUP-1`) | Implicit competitor dedup | DEC-006/DEC-013 §C.5 mandatory preview | Show "create N / link M / N ambiguous" |
| Unclear mapping screens (`A-CFG-1`) | Most map blind | DEC-004 preview; DEC-012 dry-run | Dry-run/preview before destructive apply |
| Overloaded dashboards (vanity metrics) | SH activity chart risk | DEC-013 §F.4 no vanity-only metrics | Every count clickable → action |
| Raw technical errors as primary UX (`A-LOG-3`, RA-016) | (counter to EM) | DEC-013 §D.11/§H human-readable primary | Technical detail behind expand |
| Hidden scheduled jobs (`A-UX-2`) | WK exposes raw `ir.cron` | DEC-012/DEC-013 friendly schedule, no raw cron | Hide `ir.cron` plumbing |
| Unsafe auto-apply (RA-008/RA-020) | (inventory conflict) | DEC-003/DEC-010 auto-apply not a default; apply-mode = MBQ-34 | Review-then-apply default recommended, ChatGPT-owned |
| Unclear source of truth (RA-021) | Competitors assume equivalence | DEC-007 §3 explicit price source-of-truth; DEC-010 recorded source-of-truth | Record it on every first push |
| "Real-time" overstatement (`A-UX-1`) | WK/EC/SH | DEC-013 §D.11 honest freshness | Per-domain latency labels |
| Legacy fulfillment API (`A-FUL-1`, RA-022) | Tier-1 unsupported | DEC-011 FulfillmentOrder-only | Never legacy Order/Fulfillment |
| Writing `committed` (`A-INV-3`, RA-018) | Tier-1 read-only | DEC-010 structural exclusion | Never a write target |
| Non-idempotent refunds (`A-PAY-2`) | Tier-1 double-refund risk | DEC-003 mandatory guard if refunds added | Carry forward to any refund sprint |
| Bot-block / gate evaluation docs (`A-DOC-1`) | TQ (resolved), EC gated guide | project doc policy | Public, crawlable, screenshot-rich docs |
| Stale platform figures (`A-DOC-3`) | EM "19 retries/48h" | Tier-1 re-verification rule (DP-001) | Cite current Shopify limits |

---

## Answers to the sprint's ten questions (summary)

1. **What did competitors provide?** 8 resources (R1–R8); see the reconciliation
   file. Richest demonstrated evidence: EM, VT (R4), TQ; weakest: EC (no shots),
   R5 (blocked).
2. **What screens/flows/features do they expose?** See the feature-screen map —
   table-stakes (connect/import/export/orders/inventory/fulfillment/logs) plus
   differentiated (queue monitor, reason-coded logs, dry-run, traffic-light
   health, payout reconciliation, Markets, gift cards, B2B).
3. **What do they do well?** EM queue/log observability; VT diagnostics +
   idempotency + dated changelog; TQ demonstrated breadth; SH breadth + dashboard.
4. **What do they do poorly?** "Real-time" overstatement; toggle-density;
   email-only recovery (EC); no rate-limit strategy; no first-class
   reconciliation; mostly manual retry; implicit dedup keys.
5. **What have we covered?** Essentially all of it, at the **behaviour /
   architecture** level (§0, §C) — DEC-003/010–015, DEC-012/013.
6. **What have we missed?** Very little at the behaviour level. Genuine gaps are
   **screen-level (Part D / MBQ-53)** plus two non-MVP candidates (CSV-map
   fallback; click-and-collect status) and one dashboard nuance (activity trend).
7. **What can we do better?** §D — correctness core, operator UX, effortless
   install, first-push safety, matching UX, audit trail, financial-evidence
   visibility, location-mismatch handling, modularity, testability.
8. **What should we avoid?** §E — the reconciled avoid-list; all already guarded.
9. **Do accepted decisions need amendment candidates?** A small, non-binding set
   — see [`blueprint-amendment-candidates.md`](../03-architecture/blueprint-amendment-candidates.md);
   **none requires amending an accepted decision.**
10. **What evidence must feed Part D?** The competitor screen patterns in the
    feature-screen map (VT traffic-light, EM queue+log, SH dashboard, VT
    dry-run, first-push whitespace, progressive-disclosure lessons) — the
    behaviour is fixed; Part D designs the screens.

> **Reconciliation verdict (inference, for ChatGPT):** the competitor evidence
> **validates** the accepted blueprint and surfaces **no contradiction** with any
> accepted decision. The residual work is Part D screen design plus a few
> future-phase notes. **Recommendation: safe to proceed to Part D after ChatGPT
> reviews this evidence pack; no accepted work needs revision first.**
