# Canonical Feature Taxonomy

> The Sprint D product-synthesis deliverable. It **normalizes the messy Sprint C
> competitor feature matrix into clean, reusable product language** for the
> Odoo 19 ↔ Shopify Connector, organised into canonical **domains** and
> **capabilities**. It is the shared vocabulary that later sprints will reuse for
> MVP scoping, modular architecture, setup UX, menu structure, configuration
> screens, sync-engine design, logs/error/retry UX, permission design, test
> strategy, and implementation task prompts.

## Status

- **Sprint:** Research/Product Sprint D (RB-12). **Phase:** research/synthesis
  only — the **no-code gate is in force** (`CLAUDE.md` §4–§5). No connector code,
  no Odoo module, no CI/Docker, no ADRs.
- **This document decides nothing.** It is a **taxonomy and classification of
  candidates**, not a scope, roadmap, or architecture. Every "candidate",
  "premium", "later", MVP-relevance, and architecture-dependency label is an
  **input for later gated review**, never a decision (`CLAUDE.md` §8). MVP scope
  is **RB-13** (gated); architecture is **RB-14 / AR-002…AR-008** (gated).
- **Access date for all competitor evidence:** **2026-06-30** (Sprint C capture).
  **Session date:** 2026-07-01. No new competitor sources were crawled for this
  sprint — it synthesises **already-merged repo evidence only**.
- **Evidence discipline (DP-003, DP-004) applied throughout:** competitor
  capability statements are **claims**, not facts; a **configuration field alone
  is not demonstrated support**; a **market promise is not demonstrated
  bidirectionality**; `✅` is used only where a **demonstrated workflow / screenshot
  / dated release note / explicit vendor documentation** supports the specific
  capability.

## Purpose

Convert competitor evidence into a normalized product model so that:

1. we have **one canonical name and definition per capability** (competitors use
   inconsistent, often overstated, marketing language);
2. every capability is **traceable to evidence** and **classified by strength**;
3. capabilities are **separated by type** (product-UX, technical-reliability,
   configuration, architecture-dependency) so different later sprints can consume
   the right slice;
4. **MVP candidates, later/advanced candidates, and architecture-review items**
   are visibly tagged **without being decided** now.

The compact traceability companion to this file is
[`capability-evidence-map.md`](./capability-evidence-map.md).

## Evidence base

This taxonomy is built **only** from these already-merged Sprint B/C repo files
(no new sourcing):

- **Competitor evidence (Tier 2–5 — claims/on-page facts):**
  [`../01-research/competitor-deep-dives.md`](../01-research/competitor-deep-dives.md),
  [`../01-research/competitor-feature-matrix.md`](../01-research/competitor-feature-matrix.md),
  [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md),
  [`../01-research/common-patterns.md`](../01-research/common-patterns.md),
  [`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md),
  [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md),
  [`../01-research/avoid-list.md`](../01-research/avoid-list.md),
  [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md),
  [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md).
- **Official platform baselines (Tier 1 — facts):**
  [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md),
  [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).

**Competitor keys:** **WK** = Webkul (R1) · **TQ** = Teqstars (R2) · **EM** =
Emipro (R3) · **VT** = VentorTech PRO (R4+R7) · **EC** = ecommerce_shopify (R6) ·
**SH** = sh_shopify_connector / Softhealer (R8). **Official-platform key:**
**SHOPIFY-OFFICIAL** = Shopify official docs (Tier-1), **ODOO-OFFICIAL** = Odoo
official docs (Tier-1). **SH always means Softhealer's connector — never Shopify
official docs.**

**Evidence weighting (from Sprint C):** **EM** (≈29 real screenshots) and **VT**
(dated, mechanism-level release notes) carry the most **demonstrated** evidence;
**TQ** docs are **403-blocked** (Apps-listing claims only → weak); **EC** has **no
screenshots** (listing claims only → weak); **SH** ✅ marks rest on a **captioned
walkthrough** with **no ratings/changelog** (medium-for-behaviour, low-for-trust);
**WK** is a single vendor guide (medium).

## Claim and evidence rules

Each capability below carries an **Evidence status** drawn from this controlled
vocabulary:

| Evidence status | Meaning | Typical basis |
| --- | --- | --- |
| **official-platform requirement** | The Shopify/Odoo platform makes this necessary or mandatory. | Tier-1 Shopify/Odoo docs. |
| **competitor demonstrated** | ≥1 competitor **shows** it (screenshot / step flow / dated release note / explicit doc). | EM/VT (strong); SH/WK (medium). |
| **baseline market pattern** | Multiple competitors do it and it is the demonstrated market floor. | ≥2 connectors demonstrate. |
| **competitor claim only** | Stated by a vendor but **not demonstrated** (or from a blocked/screenshot-free source). | TQ listing, EC listing, marketing bullets. |
| **inference** | Our deduction from evidence (labelled), not a competitor or platform statement. | Synthesis. |
| **open question** | Unknown / unverified / blocked. | Blocked docs, whitespace. |

Where a capability is **both** platform-required and market-seen, both are noted.
Per-cell competitor coverage uses the Sprint C symbols: **✅** demonstrated ·
**🟨** claim only · **⬜** not found · **🚫** explicitly absent · **🔒** blocked/unknown.

## Taxonomy principles

1. **Canonical name over marketing name.** "Real-time inventory sync" (WK/EC/SH
   marketing) is normalized to *inventory sync* with an honest **sync-mode**
   attribute; latency claims are not adopted as capability names (A-UX-1).
2. **A capability is what can be demonstrated or platform-required — not what is
   promised.** `✅`/"demonstrated" requires evidence for the **specific**
   capability (DP-004).
3. **Separate the four capability types.** Every capability is tagged as some mix
   of **Product/UX**, **Reliability/performance**, **Configuration**, and
   **Architecture-dependency** (via the four "implications/dependency" fields).
4. **Classify, don't decide.** Candidate classification (baseline / premium /
   advanced-later / optional add-on / unknown) and MVP relevance
   (candidate / later / unknown) are **inputs**, gated for ChatGPT (RB-13/RB-14).
5. **Route architecture-bearing capabilities to review.** Anything whose shape
   depends on an open architecture question is tagged **requires AR review** and
   named against AR-002…AR-008 — **not** resolved here.
6. **Honesty and correctness are first-class capabilities**, not afterthoughts
   (idempotency, reconciliation, rate-limit awareness, latency labelling).

## Domain overview

Twenty canonical domains group the capability set. Domains 1–2 are onboarding/
command-center; 3–12 are commerce-object domains; 13–16 are the sync/reliability/
mapping engine; 17 is multi-tenancy/permissions; 18–20 are advanced breadth,
reporting, and product-surround.

| # | Domain | Canonical scope (one line) | Capability-ID prefix |
| --- | --- | --- | --- |
| 1 | Store connection, authentication, and setup | Connect a Shopify store to Odoo securely and provably. | `C-CONN-*` |
| 2 | Dashboard, health, and command center | One pane for health, activity, queue status, and quick actions. | `C-DASH-*` |
| 3 | Product catalog sync | Move product templates/records both ways. | `C-PROD-*` |
| 4 | Variants, options, images, and media | Variant/option model + media, honouring Shopify limits. | `C-VAR-*` |
| 5 | Pricing, pricelists, compare-at, markets pricing | Price/compare-at/per-market pricing mapping. | `C-PRICE-*` |
| 6 | Inventory, stock quantities, and locations | Quantity + multi-location stock, correct quantity states. | `C-INV-*` |
| 7 | Customers, companies, and addresses | Customer/company/address sync + dedup + PII handling. | `C-CUST-*` |
| 8 | Orders and order lifecycle | Order intake + status + auto-workflow. | `C-ORD-*` |
| 9 | Invoices, payments, gateways, and journals | Invoice creation + gateway→journal + transactions. | `C-PAY-*` |
| 10 | Fulfillment, delivery, tracking, shipment status | FulfillmentOrder-based fulfillment + tracking write-back. | `C-FUL-*` |
| 11 | Refunds, returns, cancellations, restocking | Refund/return/cancel with restock, idempotently. | `C-RET-*` |
| 12 | Payouts and reconciliation | Shopify Payments payout import + bank reconciliation. | `C-POUT-*` |
| 13 | Webhooks, scheduled sync, manual sync, reconciliation | The sync trigger/verify/reconcile layer. | `C-SYNC-*` |
| 14 | Queue, jobs, retries, and recovery | Async processing, retry classes, throttling, isolation. | `C-JOB-*` |
| 15 | Logs, errors, audit trail, and observability | Reason-coded logs + recovery-first error center. | `C-OBS-*` |
| 16 | Mapping, matching, and duplicate prevention | Binding keys, dedup, directional/testable mappings. | `C-MAP-*` |
| 17 | Multi-store, multi-company, and permissions | Per-store/company isolation + role-based access. | `C-MULTI-*` |
| 18 | Shopify Markets, B2B, POS, gift cards, metafields, advanced | Premium breadth capabilities. | `C-ADV-*` |
| 19 | Reporting, analytics, and operational insights | Operational + financial reporting. | `C-RPT-*` |
| 20 | Documentation, support, demo, maintenance transparency | Trust/evaluability surround. | `C-DOCS-*` |

> **Cross-cutting groups** (feature flags, progressive disclosure, dry-run,
> idempotency, extension points, transport abstraction) span multiple domains and
> are consolidated in **Cross-cutting capability groups** after Domain 20.

---

## Domain 1 — Store connection, authentication, and setup

### Definition

Everything required to connect an Odoo instance to a Shopify store and **prove the
connection works before any sync**: authentication, credential handling, the setup
wizard, connection/scope testing, and a pre-flight readiness check. This domain is
the single biggest onboarding drop-off point in the survey.

### Capabilities

- **Capability ID:** C-CONN-01
  - **Capability name:** OAuth-first store connection
  - **Description:** Connect and authorise the app via Shopify OAuth (no manual
    token paste) to obtain an offline access token. A strong UX/security/product
    direction; **competitor-demonstrated by VentorTech**.
  - **User value:** Fewer credential errors; no long token/scope paste; secure by
    default.
  - **Evidence status:** competitor demonstrated + **conditional** official-platform
    requirement **if public/App-Store distribution is chosen** (SHOPIFY-OFFICIAL:
    new public apps must OAuth before any UI). It is **not** an unconditional
    platform requirement — custom/private connector flows may authenticate with an
    Admin API token / custom-app access instead, so this cannot be treated as a
    finalized requirement until **AR-002 (distribution) resolves** (still open).
  - **Evidence references:** best-in-class-observations.md (VT OAuth ✅ — demonstrated); shopify-official-api-notes.md (Auth & scopes: OAuth/token-exchange, offline tokens; App-Store requires OAuth-first — *conditional on public distribution*); architecture-review-log.md (AR-002, open).
  - **Competitor examples:** VT✅ ("OAuth — no manual API tokens"); WK✅/EM✅/SH✅ paste custom-app token (demonstrated non-OAuth path); TQ🟨/EC🟨.
  - **UX implications:** OAuth redirect + consent screen; hide token internals; **if** public/App-Store, apps must OAuth **before** any UI.
  - **Reliability/performance implications:** Offline token doesn't expire by default; token-exchange/refresh handling required if using the expiring variant.
  - **Configuration implications:** App registration (client id/secret, redirect URL); scope declaration in app TOML — **only under the OAuth path**; a custom-app path pastes a token instead.
  - **Architecture dependency:** requires AR review (**AR-002 API/distribution — open**: public-app vs custom-app decides whether OAuth is mandatory or optional).
  - **Candidate classification:** likely baseline (**as a product/UX direction**; the *requirement* status is conditional).
  - **MVP relevance:** candidate.
  - **Notes:** Custom-app token paste is the demonstrated market default; OAuth-first is VT's differentiator and a **strong** UX/security direction — but its official-platform *requirement* is **conditional on the (unresolved) public/App-Store distribution choice (AR-002)**. Do **not** treat OAuth-first as a finalized architecture decision.

- **Capability ID:** C-CONN-02
  - **Capability name:** Credential storage and masking
  - **Description:** Securely store and **mask** client secret / access token in
    the connection record.
  - **User value:** Secrets aren't shoulder-surfed or leaked in views.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (VT v2.1.3 credential masking); ux-ui-benchmark.md (best patterns #7).
  - **Competitor examples:** VT✅ (masking); TQ🟨 ("securely stored" — claim); others ⬜.
  - **UX implications:** Masked field with reveal control; never echo secret in logs.
  - **Reliability/performance implications:** Token rotation/refresh path; avoid logging secrets (ties to C-OBS reason-coded logs).
  - **Configuration implications:** Field-level access; store per-connection.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Cheap, high-trust; pair with C-MULTI role-gating so only admins see credentials.

- **Capability ID:** C-CONN-03
  - **Capability name:** Guided setup wizard
  - **Description:** A step-by-step wizard that walks a user from app creation to a
    working connection.
  - **User value:** Non-experts can connect without reading a manual.
  - **Evidence status:** baseline market pattern (mixed demonstrated/claim).
  - **Evidence references:** ux-ui-benchmark.md (setup/onboarding comparison); competitor-deep-dives.md (WK setup ✅; EM Path A/B ✅; VT "3-step"/"8-step" 🟨).
  - **Competitor examples:** WK✅/EM✅ (demonstrated multi-step); VT🟨 (step-count claim); TQ🟨 ("wizard checks API access"); EC🔒 (guide is the blocked Google Doc).
  - **UX implications:** Progressive disclosure; inline help on jargon; never gate the guide behind sign-in (A-DOC-1).
  - **Reliability/performance implications:** Should end in a verified state, not an unverified "saved".
  - **Configuration implications:** Sequences C-CONN-01/04/05.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EC's setup guide being a blocked Google Doc (R5) is the onboarding anti-pattern to avoid.

- **Capability ID:** C-CONN-04
  - **Capability name:** Test connection (explicit pass/fail)
  - **Description:** A discrete button that verifies the credentials reach Shopify
    and returns an explicit pass/fail.
  - **User value:** Immediate confidence the connection works; failures surface at
    setup, not mid-sync.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (WK Test Connection ✅; VT connection test 🟨; SH Sync-Logs confirm ✅).
  - **Competitor examples:** WK✅; SH✅ (status→Done); VT🟨; EM➖; TQ🟨; EC⬜.
  - **UX implications:** One obvious control; clear success/error text with a named cause (ties to C-DASH-04).
  - **Reliability/performance implications:** Cheap Admin API call; must not leak token in error.
  - **Configuration implications:** None beyond the connection record.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Cheap, high-value guardrail (best-in-class #5).

- **Capability ID:** C-CONN-05
  - **Capability name:** Scope / readiness pre-flight check
  - **Description:** Verify required OAuth scopes are granted and environment is
    ready (HTTPS/`web.base.url`, webhook reachability, worker/queue presence)
    before first sync.
  - **User value:** Predictable failures are caught up front; fewer support tickets.
  - **Evidence status:** competitor demonstrated (partial) + inference + official-platform requirement.
  - **Evidence references:** gaps-opportunities.md (O-SET-2 pre-flight readiness); competitor-deep-dives.md (VT auto scope-check 🟨; EM trailing-slash warning ✅); shopify-official-api-notes.md (least-privilege scopes; protected-customer-data approval).
  - **Competitor examples:** VT🟨 (scope-check); EM✅ (trailing-slash gotcha documented); others ⬜.
  - **UX implications:** One-screen readiness panel with named causes and fix hints (generalized VT yellow-status model).
  - **Reliability/performance implications:** Surfaces missing scopes / unreachable webhook URL / missing workers before they cause silent failures.
  - **Configuration implications:** Depends on chosen scopes; protected-customer-data (orders/customers) needs Shopify approval + Level 1/2 controls.
  - **Architecture dependency:** requires AR review (AR-003: what "queue/worker present" means depends on the sync-orchestration choice).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** No competitor demonstrates a full readiness check — partial whitespace.

- **Capability ID:** C-CONN-06
  - **Capability name:** Reconnect / re-authorise / disconnect lifecycle
  - **Description:** Re-run OAuth, rotate credentials, and cleanly disconnect a
    store (including webhook teardown).
  - **User value:** Recover from revoked tokens or store-URL changes without a
    broken connector.
  - **Evidence status:** inference + competitor demonstrated (partial).
  - **Evidence references:** competitor-deep-dives.md (VT webhook fix after store-URL migration ✅); shopify-official-api-notes.md (compliance webhooks; token model).
  - **Competitor examples:** VT✅ (store-URL-migration webhook fix, dated); others ⬜/➖.
  - **UX implications:** Clear "reconnect" affordance; warn before disconnect (destroys webhooks/bindings).
  - **Reliability/performance implications:** Must re-verify HMAC secret and re-register webhooks; handle bindings on disconnect.
  - **Configuration implications:** Ties to C-SYNC webhook subscription management.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Store-URL migration is a real, evidenced failure mode (VT patched it).

---

## Domain 2 — Dashboard, health, and command center

### Definition

A single operational surface that fuses connection health, sync/queue status,
recent activity, failure counts, freshness indicators, and quick actions. No
competitor combines the best monitoring (SH) with the best diagnostics (VT) — this
is a named differentiation whitespace (O-DASH-1).

### Capabilities

- **Capability ID:** C-DASH-01
  - **Capability name:** Unified command center
  - **Description:** One dashboard fusing connection health + queue status +
    activity timeline + failure counts + reconciliation status + quick actions.
  - **User value:** "Is everything OK, what failed, what do I do" answered in one
    place.
  - **Evidence status:** inference (synthesis of SH + VT) — no competitor demonstrates the full fusion.
  - **Evidence references:** gaps-opportunities.md (O-DASH-1); ux-ui-benchmark.md (dashboard/command-center comparison); best-in-class-observations.md (SH command center ✅).
  - **Competitor examples:** SH✅ (Integration Dashboard + activity chart, best monitoring); EM✅ (Shopify/Smart Dashboard); TQ🟨 (two dashboards claim); VT⬜ (no dedicated dashboard); EC⬜ (none).
  - **UX implications:** Admin vs functional-user views; glanceable health; quick actions (sync now, reconcile now, open error center).
  - **Reliability/performance implications:** Aggregates queue/failure metrics — must read cheaply (batched/`_read_group`, not N+1).
  - **Configuration implications:** Per-store scoping; role-gated widgets.
  - **Architecture dependency:** light (data model depends on queue/log design → AR-003/AR-006).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** Clear differentiator; combines SH monitoring + VT diagnostics that neither does fully.

- **Capability ID:** C-DASH-02
  - **Capability name:** Health indicators (traffic-light status)
  - **Description:** Glanceable green/yellow/red status for connection, webhooks,
    and sync health.
  - **User value:** Instant read of whether the connector is healthy.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** ux-ui-benchmark.md (VT traffic-light webhook health — best status pattern); competitor-deep-dives.md (VT R4 Confluence ✅).
  - **Competitor examples:** VT✅ (traffic-light webhook health); SH✅ (queue counts); others ⬜/binary.
  - **UX implications:** Status encodes state; pair with C-DASH-04 named cause.
  - **Reliability/performance implications:** Reflects real webhook/connection state (not just "configured").
  - **Configuration implications:** None.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT's is the single best status-indicator pattern observed.

- **Capability ID:** C-DASH-03
  - **Capability name:** Activity timeline + queue status + failure counts
  - **Description:** A recent-activity feed with per-entity queue state (draft/
    done/failed) and failure counts, optionally a daily activity chart.
  - **User value:** See what has been syncing and what is failing, over time.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (SH Queue Dashboard + "Daily Queue Activity Tracking" chart ✅; EM queues ✅); ux-ui-benchmark.md (SH best monitoring).
  - **Competitor examples:** SH✅ (activity chart + failure counts); EM✅ (state-coloured queues); VT➖ (status menu/pipeline); EC⬜.
  - **UX implications:** Drill from a count into the failed records (ties to C-OBS error center).
  - **Reliability/performance implications:** Time-series aggregation must be efficient at scale.
  - **Configuration implications:** Per-store; retention window.
  - **Architecture dependency:** light (AR-003 queue model).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** SH's daily activity chart is the best monitoring visual in the survey.

- **Capability ID:** C-DASH-04
  - **Capability name:** Named-cause diagnostics with fix hints
  - **Description:** Every health/error indicator names the **cause** and a
    **suggested fix**, not an opaque state.
  - **User value:** Users self-serve fixes instead of filing tickets.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** ux-ui-benchmark.md (VT yellow="callback URL mismatch — check web.base.url"); gaps-opportunities.md (O-UX-3).
  - **Competitor examples:** VT✅ (named cause); others ⬜ (opaque/binary → A-UX-4).
  - **UX implications:** Requires a **taxonomy of named causes** (open question); fix hints inline.
  - **Reliability/performance implications:** Maps error classes → causes → hints; ties to retry classification (C-JOB-02).
  - **Configuration implications:** None.
  - **Architecture dependency:** light.
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** Generalize VT's yellow-status model to all connection/webhook/sync health.

- **Capability ID:** C-DASH-05
  - **Capability name:** Quick actions
  - **Description:** One-click "sync now", "reconcile now", "retry failed", "open
    error center", "run readiness check" from the command center.
  - **User value:** Common operations are one click, not buried in menus.
  - **Evidence status:** baseline market pattern.
  - **Evidence references:** ux-ui-benchmark.md (EM "Perform Operation" launcher; SH per-tab Sync buttons); gaps-opportunities.md (O-DASH-1).
  - **Competitor examples:** EM✅ (Perform Operation); SH✅ (Sync buttons); VT✅ ("Run Now"); WK✅.
  - **UX implications:** Confirm/guard destructive actions (dry-run/preview first where applicable).
  - **Reliability/performance implications:** Manual triggers must enqueue, not run heavy work inline (5s webhook / worker limits).
  - **Configuration implications:** Role-gated (functional users can run; only admins reconfigure).
  - **Architecture dependency:** light (AR-003).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Pairs with freshness indicator (C-SYNC-07).

- **Capability ID:** C-DASH-06
  - **Capability name:** Empty states and first-run guidance
  - **Description:** Helpful empty states (no store yet, no syncs yet, no errors)
    that guide the next action.
  - **User value:** New users aren't dropped into a blank screen.
  - **Evidence status:** inference (UX best practice; not evidenced in competitors).
  - **Evidence references:** ux-ui-benchmark.md (UX principles — approachable then powerful); (no competitor evidence — EC has no screenshots).
  - **Competitor examples:** none demonstrated (⬜ across the survey / unproven).
  - **UX implications:** Empty-state copy points to setup wizard / first sync / docs.
  - **Reliability/performance implications:** None.
  - **Configuration implications:** None.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Cheap polish; no competitor evidence, so classified by inference only.

---

## Domain 3 — Product catalog sync

### Definition

Bidirectional movement of product **templates/records** (name, description,
category, status) between Odoo and Shopify, with incremental/filterable imports,
draft-first exports, and publish control. (Variants/media in Domain 4; pricing in
Domain 5.)

### Capabilities

- **Capability ID:** C-PROD-01
  - **Capability name:** Product import (Shopify → Odoo)
  - **Description:** Import products with create/update date-range filters and
    "do not update existing" / "import draft" options.
  - **User value:** Bring the Shopify catalog into Odoo controllably and
    incrementally.
  - **Evidence status:** baseline market pattern (demonstrated).
  - **Evidence references:** competitor-feature-matrix.md §2 (EM✅ date ranges + don't-update-existing + draft; WK✅; SH✅); best-in-class-observations.md (EM incremental import).
  - **Competitor examples:** EM✅/WK✅/SH✅/VT✅ demonstrated; TQ🟨; EC🟨.
  - **UX implications:** Import filters (all/ID/date-range); "From" defaults to last run.
  - **Reliability/performance implications:** Incremental by `updated_at`; batch/queue; per-record isolation; idempotent upsert by binding key.
  - **Configuration implications:** Filter defaults; overwrite policy.
  - **Architecture dependency:** requires AR review (AR-002 API; AR-005 binding).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Directionality is object-specific (DP-004) — import is broadly demonstrated.

- **Capability ID:** C-PROD-02
  - **Capability name:** Product export (Odoo → Shopify)
  - **Description:** Push Odoo products to Shopify, ideally **draft-first for
    review** before publish, with Shopify-ID write-back.
  - **User value:** Manage the catalog from Odoo as the source of truth.
  - **Evidence status:** competitor demonstrated (directionality varies — DP-004).
  - **Evidence references:** competitor-feature-matrix.md §2 (VT draft-export ✅; EM✅; SH ID-writeback ✅; **EC export direction not found**); common-patterns.md (directionality varies).
  - **Competitor examples:** VT✅/EM✅/SH✅; WK✅ (category+template); TQ🟨; **EC⬜ (export not found)**.
  - **UX implications:** Draft-first + preview; publish as a separate step.
  - **Reliability/performance implications:** `productSet` **deletes omitted list entries** — never send a partial list (A-IMP-1); idempotent by binding.
  - **Configuration implications:** Draft vs live; which fields are Odoo-authoritative.
  - **Architecture dependency:** requires AR review (AR-002; AR-005).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EC's missing export direction is the DP-004 example — do not assume bidirectionality.

- **Capability ID:** C-PROD-03
  - **Capability name:** Publish / unpublish and sales-channel control
  - **Description:** Control Shopify publication (Web / Web+POS) and channel
    membership from Odoo, including "unpublish" and sell-when-out-of-stock.
  - **User value:** Merchandising control without leaving Odoo.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §2 (EM Web/Web+POS + Shopify Unpublish ✅; SH via sales-channel membership ✅).
  - **Competitor examples:** EM✅/SH✅; VT✅; WK⬜; EC⬜.
  - **UX implications:** Channel toggles; clear published/draft state per product.
  - **Reliability/performance implications:** Publication status is a sync field with its own drift risk.
  - **Configuration implications:** Default publish target; POS channel handling.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Ties to POS (C-ADV-03) and inventory sell-OOS behaviour.

- **Capability ID:** C-PROD-04
  - **Capability name:** Product-level exclude-from-sync
  - **Description:** Mark individual products (or sets) to be excluded from sync.
  - **User value:** Keep internal/non-Shopify products out of the channel.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (SH exclude-from-sync ✅; EM exclude-channel with logged reason ✅).
  - **Competitor examples:** SH✅; EM✅ (analytic-channel exclusion, logged reason); others ⬜.
  - **UX implications:** A visible per-record toggle; excluded items shouldn't clutter queues.
  - **Reliability/performance implications:** Exclusion must be honoured by every sync path (reduces noise/cost).
  - **Configuration implications:** Per-product / per-category / per-channel rules.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Emipro logs the exclusion reason — good observability pattern.

- **Capability ID:** C-PROD-05
  - **Capability name:** Draft/preview before destructive catalog apply
  - **Description:** A dry-run/preview that reports what an export would create/
    update/**delete** before it is sent.
  - **User value:** Prevents pushing bad data to Shopify (hard to reverse).
  - **Evidence status:** competitor demonstrated (for pricing/catalogs) + official-platform requirement (motivated by `productSet` delete-on-omit).
  - **Evidence references:** best-in-class-observations.md (VT Preview/Report dry-run); avoid-list.md (A-CFG-1; A-IMP-1); shopify-official-api-notes.md (`productSet` delete-on-omit footgun).
  - **Competitor examples:** VT✅ (catalogs Preview/Report); others ⬜.
  - **UX implications:** Show adds/updates/**deletes** explicitly; require confirm for deletes.
  - **Reliability/performance implications:** Critical for `productSet`/variant reconciliation (data-loss prevention).
  - **Configuration implications:** Dry-run default before first live export.
  - **Architecture dependency:** requires AR review (AR-002 — mutation strategy).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** Generalizes VT's catalog dry-run to all destructive catalog writes.

---

## Domain 4 — Variants, options, images, and media

### Definition

The variant/option model (up to Shopify's 2,048-variant limit), product images/
media both directions with optional dedup, and SEO/taxonomy fields.

### Capabilities

- **Capability ID:** C-VAR-01
  - **Capability name:** Variant and option sync (2,048-variant model)
  - **Description:** Sync product options and variants honouring the Shopify **new
    product model** (up to 2,048 variants).
  - **User value:** Large catalogs with many variants sync without truncation.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §2 (EM✅/VT✅; **WK not found**); competitor-deep-dives.md (VT fixed 250-variant cap v2.1.4); shopify-official-api-notes.md (2,048-variant model; `productVariantsBulkCreate`).
  - **Competitor examples:** EM✅/VT✅ demonstrated; TQ🟨/EC🟨/SH🟨; **WK⬜**.
  - **UX implications:** Variant grid; option mapping; large-variant products need batching feedback.
  - **Reliability/performance implications:** Apps not on GraphQL product APIs break >100 variants; use bulk variant mutations; `productSet` list-reconciliation risk.
  - **Configuration implications:** Option→attribute mapping.
  - **Architecture dependency:** requires AR review (AR-002 GraphQL product APIs).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT's 250-cap fix (v2.1.4) shows this is a real defect surface.

- **Capability ID:** C-VAR-02
  - **Capability name:** Image and media sync (bidirectional)
  - **Description:** Import and export product/variant images, optionally with
    dedup.
  - **User value:** Consistent media across Odoo and Shopify without duplicates.
  - **Evidence status:** competitor demonstrated (dedup is claim-only).
  - **Evidence references:** competitor-feature-matrix.md §2 (EM import + Odoo-update ✅; VT bidirectional ✅; TQ pHash dedup 🟨; **WK not found**).
  - **Competitor examples:** EM✅/VT✅; TQ🟨 (pHash); SH🟨; **WK⬜**.
  - **UX implications:** Media order preserved; remove-only in some competitor windows (EM).
  - **Reliability/performance implications:** Media is heavy — batch; dedup avoids re-upload cost; media staging via `stagedUploadsCreate` for bulk.
  - **Configuration implications:** Direction; disable media sync (VT can disable images).
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** pHash image dedup (TQ) is a claim only — do not adopt as demonstrated.

- **Capability ID:** C-VAR-03
  - **Capability name:** SEO and standard product taxonomy fields
  - **Description:** Sync SEO fields and Shopify's Standard Product Taxonomy /
    product category.
  - **User value:** SEO and category consistency; correct Shopify taxonomy.
  - **Evidence status:** competitor demonstrated (VT) / claim (others).
  - **Evidence references:** competitor-deep-dives.md (VT v2.1.3 Standard Product Taxonomy ✅; SEO/taxonomy ✅).
  - **Competitor examples:** VT✅ (dated); others ⬜/🟨.
  - **UX implications:** Taxonomy picker; SEO fields on product form.
  - **Reliability/performance implications:** Taxonomy IDs must map to Shopify's controlled vocabulary.
  - **Configuration implications:** Category ↔ taxonomy mapping.
  - **Architecture dependency:** light.
  - **Candidate classification:** advanced-later.
  - **MVP relevance:** later.
  - **Notes:** Only VT demonstrates it (dated release note).

- **Capability ID:** C-VAR-04
  - **Capability name:** BoM / kit stock handling
  - **Description:** Handle bill-of-materials/kit products so available stock
    reflects components (e.g. after a manufacturing order).
  - **User value:** Correct availability for kitted/manufactured goods.
  - **Evidence status:** competitor demonstrated (VT).
  - **Evidence references:** competitor-deep-dives.md (VT v2.1.2 BoM-based real-time stock after MO ✅).
  - **Competitor examples:** VT✅ (dated); others ⬜.
  - **UX implications:** Indicate kit-derived availability.
  - **Reliability/performance implications:** Availability computation from components; recompute on MO events.
  - **Configuration implications:** Which products are kits/BoM.
  - **Architecture dependency:** requires AR review (AR-007 inventory model).
  - **Candidate classification:** advanced-later.
  - **MVP relevance:** later.
  - **Notes:** Manufacturing-aware inventory; niche but demonstrated.

---

## Domain 5 — Pricing, pricelists, compare-at pricing, and markets pricing

### Definition

Mapping of price and compare-at price, Odoo pricelists ↔ Shopify pricing, and
per-market pricing via Shopify Catalogs. (Markets as a domain feature: Domain 18.)

### Capabilities

- **Capability ID:** C-PRICE-01
  - **Capability name:** Price and compare-at price sync
  - **Description:** Sync selling price and **compare-at** (strike-through) price.
  - **User value:** Promotions and reference prices reflected correctly.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §2 (EM Pricelist + Compare-At Pricelist ✅; VT ✅); competitor-deep-dives.md (EM compare-at).
  - **Competitor examples:** EM✅/VT✅; WK🟨 (pricelist stores original price); TQ🟨; EC⬜/SH⬜.
  - **UX implications:** Which Odoo price feeds Shopify price vs compare-at.
  - **Reliability/performance implications:** Price is high-churn — incremental sync; idempotent writes.
  - **Configuration implications:** Pricelist selection; compare-at source.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EM/VT are the demonstrated evidence; EC/SH did not show pricing.

- **Capability ID:** C-PRICE-02
  - **Capability name:** Pricelist mapping
  - **Description:** Map Odoo pricelists to Shopify pricing (base and, per-market,
    via Catalogs).
  - **User value:** Reuse Odoo pricing rules for Shopify.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §2 (EM ✅; VT per-market via Catalogs ✅); competitor-deep-dives.md (VT pricelists→catalogs).
  - **Competitor examples:** EM✅/VT✅; WK🟨; TQ🟨 (volume/B2B pricing); EC⬜/SH⬜.
  - **UX implications:** Pricelist picker; "Odoo as single source of truth for pricing" (VT).
  - **Reliability/performance implications:** Pricelist expansion can be large — batch/bulk.
  - **Configuration implications:** Which pricelist(s) map to which market/catalog.
  - **Architecture dependency:** light (per-market → Domain 18/Markets, AR review).
  - **Candidate classification:** likely baseline (base) / premium (per-market).
  - **MVP relevance:** candidate (base) / later (per-market).
  - **Notes:** Per-market pricing pairs with C-ADV-01 (Markets).

- **Capability ID:** C-PRICE-03
  - **Capability name:** Per-market (Catalogs) pricing with dry-run
  - **Description:** Compute and export per-market prices via Shopify Catalogs,
    with a Preview/Report dry-run before sending.
  - **User value:** Correct localized pricing without accidental bad pushes.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** best-in-class-observations.md (VT Markets & Catalogs Preview/Report dry-run ✅); competitor-deep-dives.md (EM per-market Pricelist ✅).
  - **Competitor examples:** VT✅ (dry-run); EM✅ (per-market pricelist); others ⬜.
  - **UX implications:** Dry-run report before "Send Prices"; manual or daily auto-export.
  - **Reliability/performance implications:** Large price calculations → scheduled job; dry-run reduces error.
  - **Configuration implications:** Market ↔ catalog ↔ pricelist mapping.
  - **Architecture dependency:** requires AR review (Markets/Catalogs modelling).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** later.
  - **Notes:** Dry-run is the reusable UX pattern (A-CFG-1 prevention).

---

## Domain 6 — Inventory, stock quantities, and locations

### Definition

Stock quantity synchronisation across one or more locations, honouring Shopify's
inventory model (InventoryItem → InventoryLevel → Location) and quantity states
(`available`/`on_hand` writable; `committed` read-only). Multi-location is
table-stakes; single-location and manual post-import processing are anti-patterns.

### Capabilities

- **Capability ID:** C-INV-01
  - **Capability name:** Stock quantity sync
  - **Description:** Sync stock quantities Odoo ↔ Shopify, writing only
    `available`/`on_hand` (never `committed`).
  - **User value:** Accurate availability; fewer oversells.
  - **Evidence status:** baseline market pattern + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §3 (EM✅/VT✅/WK✅/SH✅); shopify-official-api-notes.md (`committed` read-only; `inventorySetQuantities`/`inventoryAdjustQuantities`).
  - **Competitor examples:** EM✅/VT✅/WK✅/SH✅ demonstrated; TQ🟨/EC🟨 (cron).
  - **UX implications:** Honest latency label (A-UX-1 — "real-time" is overstated by WK/EC/SH); last-synced timestamp.
  - **Reliability/performance implications:** `inventorySetQuantities`/`inventoryAdjustQuantities` **require `@idempotent` (2026-04)**; compare-and-set to avoid clobber.
  - **Configuration implications:** Direction; sync-mode (event vs scheduled).
  - **Architecture dependency:** requires AR review (AR-007 inventory).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Correctness-critical; ties to idempotency (C-JOB-04).

- **Capability ID:** C-INV-02
  - **Capability name:** Quantity-field / source-quantity choice
  - **Description:** Let the user choose which Odoo quantity feeds Shopify
    (Free-to-Use / On-Hand / Forecasted).
  - **User value:** Match stock policy to business model.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §3 (EM Forecast vs Free-to-Use ✅; VT Free/On-Hand/Forecasted ✅; WK ✅); common-patterns.md (quantity-field choice).
  - **Competitor examples:** EM✅/VT✅/WK✅; TQ⬜/EC⬜/SH⬜.
  - **UX implications:** Clear labels + inline help (jargon: "forecast" vs "free-to-use").
  - **Reliability/performance implications:** Formula-based; consistent across export.
  - **Configuration implications:** Per-store / per-warehouse default.
  - **Architecture dependency:** requires AR review (AR-007).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Emipro documents the exact formulas — good honesty pattern.

- **Capability ID:** C-INV-03
  - **Capability name:** Multi-location inventory mapping
  - **Description:** Map Odoo warehouses/locations to Shopify locations and write
    per-location levels (`inventory_item_id` + `location_id`).
  - **User value:** Correct stock for multi-warehouse merchants; avoids double-
    decrement.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §3 (EM✅/VT✅ demonstrated; **WK single-location only**); quality-feedback-loop.md §5 (double-decrement lesson); shopify-official-api-notes.md (InventoryLevel per location).
  - **Competitor examples:** EM✅/VT✅ (External Location grid + default fallback); TQ🟨/EC🟨/SH🟨; **WK⬜ (single)**.
  - **UX implications:** Location mapping grid with a default fallback (VT).
  - **Reliability/performance implications:** SKU-only writes **double-decrement** multi-location SKUs — must key on item+location (A-INV-2).
  - **Configuration implications:** Location↔warehouse map; default location.
  - **Architecture dependency:** requires AR review (AR-007).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Table-stakes per Sprint C; single-location (WK) is the anti-pattern.

- **Capability ID:** C-INV-04
  - **Capability name:** Stock import with controlled apply/review
  - **Description:** Import Shopify stock into Odoo, with a **controlled
    apply/review** step. **Stock import itself is demonstrated** by several
    competitors (in different forms); **auto-apply** (removing the manual Inventory
    Adjustment step) is a **recommended improvement/inference**, not a demonstrated
    market capability.
  - **User value:** Stock is imported and applied predictably; auto-apply (as an
    improvement) would avoid a hidden manual step and reduce oversell risk.
  - **Evidence status:** competitor demonstrated (stock import, various forms) +
    **inference** (auto-apply is a recommended improvement, **not** demonstrated).
  - **Evidence references:** competitor-feature-matrix.md §3 (Import stock: WK⬜, TQ🟨, **EM✅**, **VT✅**, EC🟨, **SH✅**; EM creates a manual **Inventory Adjustment to process manually** ✅ — a friction point / anti-pattern, A-INV-1); avoid-list.md (A-INV-1 — auto-apply is our do-better, not competitor evidence).
  - **Competitor examples:** EM✅ (demonstrated, but **manual Inventory-Adjustment apply — friction**); VT✅; SH✅; TQ🟨 (claim); EC🟨 (claim); **WK⬜ (import stock not found)**.
  - **UX implications:** Controlled apply with a review option; **auto-apply is the recommended improvement over EM's required manual Inventory Adjustment** (inference, not demonstrated).
  - **Reliability/performance implications:** Imported quantities must post (as an Inventory Adjustment or equivalent) to take effect; stale un-applied stock risks oversell.
  - **Configuration implications:** Apply mode (auto-apply vs review-first) — the auto-apply option is our proposed improvement.
  - **Architecture dependency:** requires AR review (AR-007 inventory).
  - **Candidate classification:** premium differentiator (the **auto-apply improvement** is the differentiator; basic stock import is baseline).
  - **MVP relevance:** candidate (**input, not a decision**).
  - **Notes:** DP-006 fix — "auto-apply" is an **improvement/inference**, not demonstrated competitor evidence; **Webkul is not marked demonstrated for import stock** (matrix §3 = ⬜). Emipro's manual Inventory-Adjustment step is the friction we propose to improve on.

---

## Domain 7 — Customers, companies, and addresses

### Definition

Customer/company sync with dedup-by-key (email/name/phone), address mapping,
customer-as-company handling, and graceful handling of Shopify's protected-
customer-data / PII plan gating.

### Capabilities

- **Capability ID:** C-CUST-01
  - **Capability name:** Customer import
  - **Description:** Import Shopify customers into Odoo (queued, incremental).
  - **User value:** Customer records available in Odoo for orders/CRM.
  - **Evidence status:** baseline market pattern.
  - **Evidence references:** competitor-feature-matrix.md §4 (EM✅/VT✅/SH✅; WK🟨/EC🟨); competitor-deep-dives.md (EM queue, incremental).
  - **Competitor examples:** EM✅/VT✅/SH✅; WK🟨/TQ🟨/EC🟨.
  - **UX implications:** Handle no-PII plans gracefully (default customer fallback).
  - **Reliability/performance implications:** Orders/customers are **protected customer data** — Shopify approval + Level 1/2 controls; 60-day order window.
  - **Configuration implications:** Default customer; PII fallback.
  - **Architecture dependency:** light (compliance) → AR review for data-protection posture.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT's honest "no PII on Basic plan" disclosure is the pattern to copy.

- **Capability ID:** C-CUST-02
  - **Capability name:** Customer export with email dedup (link, not duplicate)
  - **Description:** Export Odoo contacts to Shopify, **linking** an existing
    Shopify customer by email instead of creating a duplicate.
  - **User value:** No duplicate customers; clean contact base.
  - **Evidence status:** competitor demonstrated (directionality varies — DP-004).
  - **Evidence references:** competitor-feature-matrix.md §4 (EM email-dedup link ✅; SH✅; **WK/EC import-only**); best-in-class-observations.md (EM email link).
  - **Competitor examples:** EM✅ (link-by-email); SH✅; VT➖; **WK⬜/EC⬜ (import only)**.
  - **UX implications:** Skip no-email/child/already-linked; show link vs create outcome.
  - **Reliability/performance implications:** GraphQL required (EM); dedup key = normalized email.
  - **Configuration implications:** Dedup key selection.
  - **Architecture dependency:** requires AR review (AR-005 binding/dedup).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** WK/EC import-only is another DP-004 directionality example.

- **Capability ID:** C-CUST-03
  - **Capability name:** Multi-key customer matching (email / name / phone)
  - **Description:** Match customers by normalized email/name/phone before create.
  - **User value:** Fewer duplicates across imperfect data.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §4 (VT match email/name/phone ✅; EM email ✅); competitor-deep-dives.md (VT v1.13.0 normalize email/phone).
  - **Competitor examples:** VT✅ (multi-key normalized); EM✅ (email); WK🟨/TQ🟨/EC🟨/SH🟨.
  - **UX implications:** Show which key matched; manual merge override.
  - **Reliability/performance implications:** Normalization (case/whitespace/format); indexed lookups.
  - **Configuration implications:** Which keys, in what order.
  - **Architecture dependency:** requires AR review (AR-005).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT is the strongest demonstrated multi-key matcher.

- **Capability ID:** C-CUST-04
  - **Capability name:** Address and company (B2B individual/company) mapping
  - **Description:** Map billing/shipping addresses and company-vs-individual
    contacts, with country/state matching.
  - **User value:** Correct addresses and company hierarchy on orders.
  - **Evidence status:** inference (mostly implied) + competitor demonstrated (partial).
  - **Evidence references:** competitor-feature-matrix.md §4 (address handling ➖ across most; EM customer-as-company ✅); competitor-deep-dives.md (VT companies vs individuals ✅ — see B2B, Domain 18).
  - **Competitor examples:** EM✅ (customer-as-company); VT✅ (B2B company detection); address deep-mapping ➖ across survey.
  - **UX implications:** Explicit billing/shipping mapping; country/state resolution.
  - **Reliability/performance implications:** Country/state matching is a classic mismatch source.
  - **Configuration implications:** Address field mapping.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline (address) / premium (B2B company).
  - **MVP relevance:** candidate (address) / later (B2B).
  - **Notes:** Deep multi-address mapping is under-demonstrated across the field.

---

## Domain 8 — Orders and order lifecycle

### Definition

Order intake (webhook + scheduled backfill + manual), order/financial/fulfillment
status mapping, and a configurable auto-workflow (confirm → invoice → deliver →
pay), including historical-order backfill with the 60-day/`read_all_orders` gate.

### Capabilities

- **Capability ID:** C-ORD-01
  - **Capability name:** Order import (webhook + scheduled backfill + manual)
  - **Description:** Import orders in near-real-time via webhook, with a scheduled
    backfill and manual on-demand import.
  - **User value:** Timely orders in Odoo with a safety net against missed events.
  - **Evidence status:** baseline market pattern + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §5 (VT webhook "within seconds" ✅; EM manual/scheduler/webhook ✅; SH✅); shopify-official-api-notes.md (webhook delivery not guaranteed → reconcile; ORDERS_CREATE/UPDATED).
  - **Competitor examples:** VT✅/EM✅/SH✅/WK✅; TQ🟨/EC🟨 (cron 10-min).
  - **UX implications:** Honest latency; filter by status/channel/currency/date.
  - **Reliability/performance implications:** Ack webhook fast (5s), process out-of-band; reconcile missed events; idempotent by order id.
  - **Configuration implications:** Order filters; sequence/prefix; historical cut-off.
  - **Architecture dependency:** requires AR review (AR-003 orchestration).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Webhook-only (drift) and cron-only (latency) are both anti-patterns (A-SYNC-1).

- **Capability ID:** C-ORD-02
  - **Capability name:** Historical / backfill order import (60-day gate)
  - **Description:** Import historical orders from a chosen cut-off date, handling
    the 60-day default window and `read_all_orders` approval.
  - **User value:** Onboard with existing order history.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-deep-dives.md (EM shipped/historical ✅; VT historical from date ✅, REST<1.13.2/GraphQL 2.0.0 mapping); shopify-official-api-notes.md (60-day window; `read_all_orders` + Shopify approval).
  - **Competitor examples:** EM✅/VT✅; EC🟨 (date-range fetch); WK✅ (date filters).
  - **UX implications:** "Orders before cut-off will never be imported" (VT honesty); explain the 60-day gate.
  - **Reliability/performance implications:** Large backfills → Bulk Operations; `read_all_orders` needs approval.
  - **Configuration implications:** Cut-off date; approval status.
  - **Architecture dependency:** requires AR review (AR-002 bulk/backfill).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Protected-customer-data approval is a real onboarding gate.

- **Capability ID:** C-ORD-03
  - **Capability name:** Order / financial / fulfillment status mapping
  - **Description:** Map Shopify `displayFinancialStatus`/`displayFulfillmentStatus`
    to Odoo state, configurable per gateway/financial status.
  - **User value:** Orders land in the correct Odoo state automatically.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §5 (SH Payment Gateway Workflow Matrix ✅; EM per gateway+financial status 🟨; VT ✅); shopify-official-api-notes.md (Order status enums).
  - **Competitor examples:** SH✅/VT✅; EM🟨; WK🟨/TQ🟨/EC🟨.
  - **UX implications:** Status/workflow mapping rows per gateway.
  - **Reliability/performance implications:** Status is a sync field with drift; reconcile.
  - **Configuration implications:** Per-gateway/per-financial-status rules.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Feeds the auto-workflow (C-ORD-04).

- **Capability ID:** C-ORD-04
  - **Capability name:** Configurable order auto-workflow
  - **Description:** Rule-based downstream automation (confirm → ship → invoice →
    send → pay), each step observable and configurable, per gateway/status.
  - **User value:** Hands-off order processing that still shows each step.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** best-in-class-observations.md (VT 5-step auto-workflow visual pipeline; SH Auto Sale Workflow ✅); common-patterns.md (auto-workflow pattern).
  - **Competitor examples:** VT✅ (visual pipeline, each step a job); SH✅ (auto invoice/validate/register/force-transfer); EM🟨/TQ🟨/EC🟨.
  - **UX implications:** Visual pipeline; failed steps shown + restartable.
  - **Reliability/performance implications:** Each step should be a retryable, idempotent job; auto-create missing products/carriers/taxes carefully.
  - **Configuration implications:** Which steps, per gateway/status.
  - **Architecture dependency:** requires AR review (AR-003 jobs/orchestration).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT's per-step-as-a-job + restartable model is the bar.

- **Capability ID:** C-ORD-05
  - **Capability name:** Order fraud / risk import
  - **Description:** Import Shopify order risk/fraud score and flag orders over a
    threshold.
  - **User value:** Flag risky orders before fulfilling.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (VT fraud score + threshold flag ✅; order-risk fields R4 ✅).
  - **Competitor examples:** VT✅; TQ🟨 (fraud/risk); others ⬜.
  - **UX implications:** Risk level/sentiment/recommended action on the order.
  - **Reliability/performance implications:** Score imported with order.
  - **Configuration implications:** Threshold; action on flag.
  - **Architecture dependency:** light.
  - **Candidate classification:** advanced-later.
  - **MVP relevance:** later.
  - **Notes:** Demonstrated only by VT.

---

## Domain 9 — Invoices, payments, gateways, and journals

### Definition

Invoice creation from orders, payment representation (including multi-payment
orders), gateway→Odoo-journal mapping, and modelling Shopify transactions
(gateway-agnostic `OrderTransaction`) as the financial ledger.

### Capabilities

- **Capability ID:** C-PAY-01
  - **Capability name:** Invoice creation from orders
  - **Description:** Create/validate Odoo invoices from Shopify orders, driven by
    the auto-workflow.
  - **User value:** Finance records generated automatically.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §5 (VT ✅ "up to 5 steps"; SH auto-create invoice ✅; EM 🟨/➖).
  - **Competitor examples:** VT✅/SH✅; EM🟨; TQ🟨/EC🟨.
  - **UX implications:** Invoice as an auto-workflow step; visible result.
  - **Reliability/performance implications:** Idempotent (don't double-invoice on retry).
  - **Configuration implications:** When to invoice (per workflow/gateway).
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Tie invoice creation to idempotency (C-JOB-04).

- **Capability ID:** C-PAY-02
  - **Capability name:** Payment representation incl. multi-payment orders
  - **Description:** Represent Shopify payments in Odoo, including orders paid by
    multiple tenders (e.g. gift card + card → two payment lines).
  - **User value:** Faithful financial representation of real Shopify orders.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** best-in-class-observations.md (EM multi-payment lines ✅); competitor-deep-dives.md (VT Shopify payments→invoices, currency conversion ✅).
  - **Competitor examples:** EM✅ (multi-payment lines); VT✅; SH✅; TQ🟨.
  - **UX implications:** Show each tender as a line.
  - **Reliability/performance implications:** Currency conversion (VT v2.1.6); transaction-date accuracy (VT v2.1.3).
  - **Configuration implications:** Payment registration policy.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Multi-payment fidelity is a demonstrated EM/VT strength.

- **Capability ID:** C-PAY-03
  - **Capability name:** Payment-gateway → journal mapping
  - **Description:** Map each Shopify payment gateway to an Odoo journal/account.
  - **User value:** Correct accounting per payment method.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §5 (SH gateway→journal ✅; TQ🟨/EM🟨); common-patterns.md (gateway→journal mapping).
  - **Competitor examples:** SH✅; VT✅ (payments→invoices); TQ🟨/EM🟨.
  - **UX implications:** Mapping rows gateway→journal.
  - **Reliability/performance implications:** Use `OrderTransaction` (gateway-agnostic) as the cross-gateway ledger.
  - **Configuration implications:** Per-gateway journal/account.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** `OrderTransaction` is the platform-correct ledger for non-Shopify-Payments gateways.

---

## Domain 10 — Fulfillment, delivery, tracking, and shipment status

### Definition

FulfillmentOrder-based fulfillment (legacy order-based fulfillment unsupported
since 2022-07), tracking write-back, multi-package/multi-location fulfillment, and
correct Shopify fulfillment scopes.

### Capabilities

- **Capability ID:** C-FUL-01
  - **Capability name:** Fulfillment creation (FulfillmentOrder-based) + tracking write-back
  - **Description:** On Odoo delivery validation, create a Shopify fulfillment via
    FulfillmentOrder mutations and write back carrier/tracking.
  - **User value:** Shipping status and tracking appear in Shopify automatically.
  - **Evidence status:** baseline market pattern + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §5 (EM✅/VT✅/SH✅; WK "shipping-method import not available"); shopify-official-api-notes.md (`fulfillmentCreate`, `fulfillmentTrackingInfoUpdate`; legacy unsupported 2022-07).
  - **Competitor examples:** EM✅ (Export Shipment)/VT✅ (carrier tracking)/SH✅ (fulfillment-ID write-back); TQ🟨/EC🟨.
  - **UX implications:** Fulfillment status + tracking on the order; per-line "internal info" on failures (VT).
  - **Reliability/performance implications:** Must use FulfillmentOrder mutations; one fulfillment per order+location; supported carrier name → auto tracking URL.
  - **Configuration implications:** Carrier mapping; auto vs manual.
  - **Architecture dependency:** requires AR review (AR-008 fulfillment).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Legacy order-based fulfillment endpoints are the anti-pattern (A-FUL-1).

- **Capability ID:** C-FUL-02
  - **Capability name:** Multi-package / multi-location fulfillment
  - **Description:** Support Put-in-Pack multi-package shipments and per-location
    fulfillment splits.
  - **User value:** Correct fulfillments for split/partial orders.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** best-in-class-observations.md (EM Put-in-Pack multi-package ✅; VT per-warehouse transfers ✅); avoid-list.md (A-FUL-2).
  - **Competitor examples:** EM✅ (multi-package); VT✅ (per-warehouse, `sale_sourced_by_line`); SH✅.
  - **UX implications:** Package/line-level fulfillment view.
  - **Reliability/performance implications:** One fulfillment per order+location; multi-location orders → multiple fulfillments.
  - **Configuration implications:** Warehouse↔location; packaging.
  - **Architecture dependency:** requires AR review (AR-008).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Pairs with multi-location inventory (C-INV-03).

- **Capability ID:** C-FUL-03
  - **Capability name:** Fulfillment scope granting / verification
  - **Description:** Request and verify the correct Shopify fulfillment scopes
    (assigned / merchant-managed / third-party).
  - **User value:** Fulfillment export doesn't silently fail on missing scopes.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** best-in-class-observations.md (EM grant-fulfillment-scopes walkthrough ✅); avoid-list.md (A-FUL-3); shopify-official-api-notes.md (fulfillment-order scopes).
  - **Competitor examples:** EM✅ (explicit scope-grant walkthrough); others ➖.
  - **UX implications:** Readiness check flags missing fulfillment scopes (ties to C-CONN-05).
  - **Reliability/performance implications:** Missing scope = fulfillment export failure.
  - **Configuration implications:** Scope selection at connect.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Emipro's explicit scope walkthrough is the bar.

---

## Domain 11 — Refunds, returns, cancellations, and restocking

### Definition

Idempotent refunds (`refundCreate` requires `@idempotent` from 2026-04), the
Shopify return lifecycle (request/approve/process), order cancellation with
restock/notify, and modelling refunds independently of money movement.

### Capabilities

- **Capability ID:** C-RET-01
  - **Capability name:** Refund sync (idempotent)
  - **Description:** Sync refunds between Shopify and Odoo (credit notes),
    idempotently (no double refunds on retry).
  - **User value:** Correct financial state; no accidental double refunds.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §5 (EM✅/VT✅/SH✅; VT GraphQL refund idempotency); shopify-official-api-notes.md (`refundCreate` requires `@idempotent` 2026-04; refund independent of money movement).
  - **Competitor examples:** EM✅ (credit note + conditions); VT✅ (idempotent refunds, dated); SH✅ (full/partial/restock/multi-currency); EC🟨.
  - **UX implications:** Show refund → credit note; restock choice.
  - **Reliability/performance implications:** **Non-idempotent refunds double-refund** (A-PAY-2); refund status is on its transactions.
  - **Configuration implications:** Auto vs manual; conditions (invoice-exists).
  - **Architecture dependency:** requires AR review (AR-006 idempotency).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Idempotency is platform-mandated here — correctness, not polish.

- **Capability ID:** C-RET-02
  - **Capability name:** Returns lifecycle (request → approve → process, restock)
  - **Description:** Handle the Shopify return lifecycle and create Odoo return
    pickings + credit notes, with restock types.
  - **User value:** Proper RMA handling with stock and finance effects.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-deep-dives.md (EM returns via webhook: credit note if invoice exists + return picking, fulfilled-only ✅; SH refunds/returns ✅); shopify-official-api-notes.md (`returnCreate`/`returnRequest`/`returnApproveRequest`; `returnProcess`; `restockType`).
  - **Competitor examples:** EM✅ (conditional returns); SH✅; EC🟨 (returns v19.0.2.0); VT✅ (synced back).
  - **UX implications:** Conditions surfaced (invoice-exists, fulfilled-only); restock choice.
  - **Reliability/performance implications:** `returnRefund` deprecated 2026-04 → `returnProcess`; restock types map to Odoo pickings.
  - **Configuration implications:** Restock rules; return journals.
  - **Architecture dependency:** requires AR review (AR-006/AR-008).
  - **Candidate classification:** premium differentiator (returns-as-distinct-from-refunds is scarce).
  - **MVP relevance:** later.
  - **Notes:** VT/EC treat refunds ≈ returns; distinct RMA lifecycle is scarcer (advanced).

- **Capability ID:** C-RET-03
  - **Capability name:** Order cancellation (restock / notify / two-step)
  - **Description:** Cancel orders with reason/restock/notify, with guards for
    already-fulfilled/paid orders.
  - **User value:** Safe cancellations with correct stock/finance/customer effects.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (VT two-step cancel with restock/refund/notify ✅; EM cancels if quotation/undelivered else log-note ✅; SH ✅).
  - **Competitor examples:** VT✅ (two-step, irreversible warning); EM✅ (never creates a cancel order); SH✅; WK🟨 (cancel-status only).
  - **UX implications:** Irreversible-action warning (VT); reason/restock/notify options.
  - **Reliability/performance implications:** Paid+shipped can't cancel until fulfillments removed (VT).
  - **Configuration implications:** Cancellation policy; restock default.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EM's "never silently create a cancel order" and VT's irreversibility warning are good guards.

---

## Domain 12 — Payouts and reconciliation

### Definition

Shopify Payments payout import and bank-statement reconciliation. Payouts/balance/
disputes are **Shopify Payments only**; non-Shopify-Payments gateways have no
payout data (use `OrderTransaction`). Robust payout reconciliation is rare
whitespace (only EM demonstrates).

### Capabilities

- **Capability ID:** C-POUT-01
  - **Capability name:** Payout import (Shopify Payments)
  - **Description:** Import Shopify Payments payout reports into Odoo.
  - **User value:** Payout data available for finance/reconciliation.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §5 (only EM demonstrates ✅; TQ claims Enterprise auto-reconcile 🟨); shopify-official-api-notes.md (`shopifyPaymentsAccount`, payouts; Shopify-Payments-only).
  - **Competitor examples:** EM✅ (Shopify-Payments-only); TQ🟨; VT⬜/EC⬜/SH⬜.
  - **UX implications:** Gate payout features to Shopify-Payments stores; explain the limitation.
  - **Reliability/performance implications:** Non-Shopify-Payments stores have no payout data (A-PAY-1); needs "access to payouts" merchant permission.
  - **Configuration implications:** Payout journals.
  - **Architecture dependency:** requires AR review (payments/payout modelling).
  - **Candidate classification:** premium differentiator (advanced add-on).
  - **MVP relevance:** later.
  - **Notes:** Rare whitespace — only EM demonstrated; gate to Shopify Payments.

- **Capability ID:** C-POUT-02
  - **Capability name:** Bank-statement generation and reconciliation
  - **Description:** Generate a bank statement from the payout report and reconcile
    against Odoo.
  - **User value:** Finance-grade reconciliation of Shopify settlements.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (EM import payout → Generate Bank Statement → reconcile ✅).
  - **Competitor examples:** EM✅; others ⬜.
  - **UX implications:** Reconciliation workflow; show matched/unmatched.
  - **Reliability/performance implications:** Idempotent statement creation; avoid duplicate statements.
  - **Configuration implications:** Journals; fee handling.
  - **Architecture dependency:** requires AR review.
  - **Candidate classification:** premium differentiator (advanced add-on).
  - **MVP relevance:** later.
  - **Notes:** "Payout reconciliation done robustly and demonstrably" is a premium theme (O-PREM-3).

---

## Domain 13 — Webhooks, scheduled sync, manual sync, and reconciliation

### Definition

The sync trigger/verify/reconcile layer: webhook subscription + **HMAC
verification** + **ID deduplication** + **fast acknowledgement**, scheduled sync,
manual sync, and **first-class scheduled + on-demand reconciliation** (webhook
delivery is not guaranteed → reconciliation is mandatory, not optional).

### Capabilities

- **Capability ID:** C-SYNC-01
  - **Capability name:** Webhook subscription management
  - **Description:** Subscribe to Shopify webhook topics (product/order/customer/
    fulfillment/bulk) and manage them per store.
  - **User value:** Near-real-time events without polling.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §6 (VT 8 events ✅; EM ✅; SH ✅; **EC none 🚫**); shopify-official-api-notes.md (webhooks topics/subscribe).
  - **Competitor examples:** VT✅/EM✅/SH✅; TQ🟨; **EC🚫 (cron-only)**; WK⬜.
  - **UX implications:** Show subscribed topics + health (traffic-light).
  - **Reliability/performance implications:** Admin-API subscriptions **self-delete after 8 consecutive failures**; recreate path needed.
  - **Configuration implications:** Which topics; per-store vs app-level (TOML).
  - **Architecture dependency:** requires AR review (AR-003).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EC's webhook-less cron-only design is the floor (A-SYNC-1).

- **Capability ID:** C-SYNC-02
  - **Capability name:** Webhook HMAC verification (raw body)
  - **Description:** Verify `X-Shopify-Hmac-SHA256` against HMAC-SHA256 of the
    **raw** body using the client secret, **before** processing.
  - **User value:** Rejects spoofed/forged events; security-correct.
  - **Evidence status:** official-platform requirement (only VT even claims it).
  - **Evidence references:** shopify-official-api-notes.md (HMAC on raw body before processing); avoid-list.md (A-SYNC-6); common-patterns.md (HMAC under-addressed — only VT).
  - **Competitor examples:** VT🟨 (HMAC-SHA256 claim); **others ⬜/unstated**.
  - **UX implications:** Invisible when correct; compliance webhooks return 401 on bad HMAC.
  - **Reliability/performance implications:** Must use unparsed body; constant-time compare.
  - **Configuration implications:** Uses the app client secret.
  - **Architecture dependency:** requires AR review (security).
  - **Candidate classification:** likely baseline (mandatory).
  - **MVP relevance:** candidate.
  - **Notes:** Under-addressed across the field — a correctness/security baseline, not optional.

- **Capability ID:** C-SYNC-03
  - **Capability name:** Webhook ID deduplication + fast acknowledgement
  - **Description:** Dedupe on `X-Shopify-Webhook-Id`, return 200 within the 5s
    window, and process out-of-band.
  - **User value:** No duplicate processing; no Shopify auto-delete from timeouts.
  - **Evidence status:** official-platform requirement + inference.
  - **Evidence references:** shopify-official-api-notes.md (dedupe on webhook id; 1s connect/5s total; retries 8×/4h; auto-delete after 8 fails); avoid-list.md (A-SYNC-4).
  - **Competitor examples:** none explicitly demonstrate dedupe/fast-ack; VT hardened webhooks (dated) ✅ (partial).
  - **UX implications:** Invisible; surfaces as reliability.
  - **Reliability/performance implications:** Heavy work in the request → timeout → retries → auto-delete (A-SYNC-4); dedupe prevents double-apply.
  - **Configuration implications:** None user-facing.
  - **Architecture dependency:** requires AR review (AR-003 — ack fast, queue processing).
  - **Candidate classification:** likely baseline (mandatory).
  - **MVP relevance:** candidate.
  - **Notes:** No competitor documents webhook-id dedupe — whitespace + platform requirement.

- **Capability ID:** C-SYNC-04
  - **Capability name:** Scheduled sync
  - **Description:** Time-based sync for each process (import/export/stock) with a
    friendly interval (not raw `ir.cron` internals).
  - **User value:** Reliable periodic sync without manual runs.
  - **Evidence status:** baseline market pattern.
  - **Evidence references:** competitor-feature-matrix.md §6 (EM per-process scheduler ✅; EC fixed 10-min crons; all have cron); avoid-list.md (A-UX-2 don't expose cron internals).
  - **Competitor examples:** EM✅/VT✅/SH✅/WK✅ (exposes raw cron — anti-pattern); EC✅ (fixed 10-min).
  - **UX implications:** "Every N minutes" not `nextcall`/Scheduler User (WK anti-pattern).
  - **Reliability/performance implications:** `ir.cron` is poll-based, `--max-cron-threads` default 2; disabled on Odoo.sh staging/dev (testing footgun).
  - **Configuration implications:** Per-process interval; stagger to avoid overload.
  - **Architecture dependency:** requires AR review (AR-003).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Hide Odoo plumbing (A-UX-2); crons off on Odoo.sh non-prod.

- **Capability ID:** C-SYNC-05
  - **Capability name:** Manual / on-demand sync
  - **Description:** Always-available manual sync triggers with filters.
  - **User value:** Run a sync when needed; test after config changes.
  - **Evidence status:** baseline market pattern.
  - **Evidence references:** competitor-feature-matrix.md §6 (universal); ux-ui-benchmark.md (stage→inspect→process→verify loop).
  - **Competitor examples:** all ✅/🟨 (WK/EM/VT/SH demonstrated; TQ/EC claim).
  - **UX implications:** Manual run → queue → inspect → verify (open record) → log.
  - **Reliability/performance implications:** Manual triggers enqueue (don't run heavy inline); needed to test on Odoo.sh staging where crons are off.
  - **Configuration implications:** Filters (all/ID/date-range).
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Universal; also the Odoo.sh-staging test path.

- **Capability ID:** C-SYNC-06
  - **Capability name:** Scheduled + manual reconciliation (first-class)
  - **Description:** A first-class reconciliation job that periodically (and
    on-demand) fetches Shopify state (`updated_at`) to detect and repair drift,
    with a visible report.
  - **User value:** State stays consistent even when webhooks are missed/duplicated.
  - **Evidence status:** official-platform requirement + inference (whitespace).
  - **Evidence references:** shopify-official-api-notes.md (delivery not guaranteed → reconciliation jobs required); gaps-opportunities.md (O-REL-1 — nobody exposes first-class reconciliation); avoid-list.md (A-SYNC-2).
  - **Competitor examples:** EM✅ (manual import to recover missed webhooks — partial); **no competitor surfaces a first-class "reconcile now / last reconciled / drift found"**.
  - **UX implications:** "Reconcile now" + "last reconciled" + drift report on the command center.
  - **Reliability/performance implications:** Prevents silent drift; must be idempotent; cadence/scope open.
  - **Configuration implications:** Cadence; scope (per object).
  - **Architecture dependency:** requires AR review (AR-003/AR-006).
  - **Candidate classification:** premium differentiator (Tier-1-mandated correctness).
  - **MVP relevance:** candidate.
  - **Notes:** The single clearest correctness whitespace — mandatory per Shopify, absent as a first-class surface across competitors.

- **Capability ID:** C-SYNC-07
  - **Capability name:** Sync freshness indicators (last synced / last reconciled)
  - **Description:** Per-object (or global) timestamps for last successful sync and
    last reconciliation, with honest sync-mode labels.
  - **User value:** Users know how fresh the data is and how it syncs.
  - **Evidence status:** inference (whitespace) + baseline (latency honesty).
  - **Evidence references:** gaps-opportunities.md (O-UX-1 honest latency + last-synced/last-reconciled); avoid-list.md (A-UX-1).
  - **Competitor examples:** none clearly demonstrate freshness indicators; WK/EC/SH overstate "real-time".
  - **UX implications:** "Last synced 3 min ago (scheduled every 15 min)"; no "real-time" overstatement.
  - **Reliability/performance implications:** Cheap timestamp writes on each run.
  - **Configuration implications:** Per-object vs global (open question).
  - **Architecture dependency:** none.
  - **Candidate classification:** premium differentiator (cheap, high-trust).
  - **MVP relevance:** candidate.
  - **Notes:** Honesty-as-a-feature (O-PREM-4).

---

## Domain 14 — Queue, jobs, retries, and recovery

### Definition

The asynchronous processing engine: staged/queued work, per-record failure
isolation, retry classification (auto for safe/transient, manual for
human-fixable), idempotency keys, rate-limit / GraphQL-cost-aware throttling, bulk
operations, and resumable jobs. Odoo core has **no** job queue (only `ir.cron`);
whether to adopt OCA `queue_job` is an open architecture question (AR-003).

### Capabilities

- **Capability ID:** C-JOB-01
  - **Capability name:** Async job / queue processing with per-record isolation
  - **Description:** Process sync work as staged/queued jobs where one bad record
    does not block the batch (isolated Failed/Cancelled/Done states).
  - **User value:** Throughput + resilience; a single error doesn't stop everything.
  - **Evidence status:** baseline market pattern (queue) / competitor demonstrated (isolation).
  - **Evidence references:** competitor-feature-matrix.md §6–7 (VT `queue_job` async ✅; EM Data Queues 125/50 ✅; SH Queue Dashboard ✅; WK Feeds; **EC none**); odoo-official-architecture-notes.md (no core queue; `queue_job` community).
  - **Competitor examples:** VT✅ (real async queue); EM✅ (batch queues, isolated Failed); SH✅ (queue dashboards); WK✅ (Feeds staging); **EC⬜ (none)**.
  - **UX implications:** Queue states + counts + drill-down (ties to C-DASH-03/C-OBS).
  - **Reliability/performance implications:** Batch valid records even if some error (VT); Odoo `ir.cron` is not a queue (A-SYNC-3).
  - **Configuration implications:** Batch sizes; channels.
  - **Architecture dependency:** requires AR review (AR-003 — cron vs `queue_job`).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** The queue framework choice is AR-003, not decided here; `queue_job` is a non-core dependency to decide consciously (A-MOD-3).

- **Capability ID:** C-JOB-02
  - **Capability name:** Retry classification (auto-safe vs manual-fixable)
  - **Description:** Classify failures as **auto-retryable** (transient/idempotent-
    safe, e.g. network/429) vs **human-fixable** (mapping/data errors) and route
    accordingly.
  - **User value:** Transient errors self-heal; real problems get human attention.
  - **Evidence status:** inference + competitor demonstrated (partial).
  - **Evidence references:** gaps-opportunities.md (O-LOG-1/O-REL-3 — which errors auto-retryable vs human); competitor-deep-dives.md (VT auto-retry safe ops ✅).
  - **Competitor examples:** VT✅ (auto-retry safe ops); EM/SH/WK/EC manual-only.
  - **UX implications:** Error shows record + reason + suggested fix + retry (C-OBS-03).
  - **Reliability/performance implications:** Requires an **error taxonomy** (open question); auto-retry must be idempotent.
  - **Configuration implications:** Which classes auto-retry; backoff.
  - **Architecture dependency:** requires AR review (AR-006).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** The auto/manual split is the design core of the recovery-first error center.

- **Capability ID:** C-JOB-03
  - **Capability name:** Automatic retry with backoff (safe operations)
  - **Description:** Automatically retry transient/idempotent-safe operations with
    backoff after network/server errors and 429s.
  - **User value:** Fewer lost syncs; no manual re-run needed for blips.
  - **Evidence status:** competitor demonstrated (VT only).
  - **Evidence references:** competitor-feature-matrix.md §7 (only VT auto-retries ✅); best-in-class-observations.md (VT auto-retry + VIES 3× retry).
  - **Competitor examples:** VT✅ (dated); EM/SH/WK/EC manual (A-RET-1).
  - **UX implications:** Show retry attempts; clear manual override.
  - **Reliability/performance implications:** Naive retry double-acts → needs idempotency (A-RET-3); back off on `Retry-After`.
  - **Configuration implications:** Max attempts; backoff policy.
  - **Architecture dependency:** requires AR review (AR-006).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** Automatic retry is a demonstrated differentiator (VT only).

- **Capability ID:** C-JOB-04
  - **Capability name:** Idempotency key management (idempotent writes)
  - **Description:** Generate and persist idempotency keys for writes and use
    Shopify's `@idempotent` directive where required.
  - **User value:** Retries never double-refund or double-adjust inventory.
  - **Evidence status:** official-platform requirement + competitor demonstrated (VT).
  - **Evidence references:** shopify-official-api-notes.md (`@idempotent` on `inventorySetQuantities`/`inventoryAdjustQuantities`/`refundCreate` from 2026-04); competitor-deep-dives.md (VT idempotency directives, dated ✅); avoid-list.md (A-RET-3/A-IMP-2).
  - **Competitor examples:** VT✅ (GraphQL idempotency directives); TQ🟨 (claim, unverifiable); others ⬜/implicit.
  - **UX implications:** Invisible; surfaces as correctness.
  - **Reliability/performance implications:** Mandatory for inventory set/adjust and refunds (2026-04); persist keys across retries.
  - **Configuration implications:** None user-facing.
  - **Architecture dependency:** requires AR review (AR-006).
  - **Candidate classification:** likely baseline (mandatory for the affected writes).
  - **MVP relevance:** candidate.
  - **Notes:** Only VT mechanizes it; it is Tier-1-mandated, not optional.

- **Capability ID:** C-JOB-05
  - **Capability name:** Rate-limit / GraphQL-cost-aware throttling
  - **Description:** Pace requests off live `throttleStatus` (GraphQL cost) and the
    REST leaky-bucket, back off on 429/`Retry-After`.
  - **User value:** Large syncs don't 429-storm or fail; predictable throughput.
  - **Evidence status:** official-platform requirement + inference (total whitespace).
  - **Evidence references:** shopify-official-api-notes.md (leaky-bucket REST; calculated-cost GraphQL; 429/`Retry-After`); common-patterns.md + gaps-opportunities.md (O-REL-2 — **no competitor describes one**).
  - **Competitor examples:** **none** (VT closest: "avoid unnecessary API requests" 🟨).
  - **UX implications:** Surface throttle state to the user when Shopify throttles (nobody does — A-SYNC-5).
  - **Reliability/performance implications:** REST request-count vs GraphQL point-cost (two strategies); pace off requested cost.
  - **Configuration implications:** Concurrency; batch sizes.
  - **Architecture dependency:** requires AR review (AR-002/AR-006).
  - **Candidate classification:** premium differentiator (clear whitespace).
  - **MVP relevance:** candidate.
  - **Notes:** The market's biggest reliability whitespace and Tier-1-relevant.

- **Capability ID:** C-JOB-06
  - **Capability name:** Bulk operation handling (large reads/writes)
  - **Description:** Route large reads/writes to Shopify Bulk Operations (async
    JSONL), with polling/finish-webhook and Odoo-side batching.
  - **User value:** Big catalogs/backfills complete without hammering rate limits.
  - **Evidence status:** official-platform requirement + inference.
  - **Evidence references:** shopify-official-api-notes.md (Bulk Operations; concurrency 2026-01; JSONL ≤100MB); gaps-opportunities.md (O-PERF-1 — none describes Bulk Operations); odoo-official-architecture-notes.md (batch `create`, `_read_group`).
  - **Competitor examples:** **none describe Bulk Operations**; EM batches (125/50) 🟨/✅ (partial).
  - **UX implications:** Progress feedback for long bulk jobs.
  - **Reliability/performance implications:** Bulk execution doesn't count against normal limits; poll or use `bulk_operations/finish` webhook (delivery not guaranteed → poll backup).
  - **Configuration implications:** When to switch to bulk (thresholds).
  - **Architecture dependency:** requires AR review (AR-002).
  - **Candidate classification:** advanced-later (backfill) / premium (scale).
  - **MVP relevance:** later (candidate for backfill).
  - **Notes:** Concurrency changed at 2026-01 (5 of each) — pin version awareness.

- **Capability ID:** C-JOB-07
  - **Capability name:** Resumable / restartable jobs
  - **Description:** Jobs that resume from progress (chunked, committing progress)
    and failed steps that are restartable.
  - **User value:** Long syncs survive interruptions; failed steps re-run cleanly.
  - **Evidence status:** competitor demonstrated (VT) + official-platform (Odoo).
  - **Evidence references:** competitor-deep-dives.md (VT failed steps restartable + "Run Now" ✅); odoo-official-architecture-notes.md (cron batching + `_commit_progress`; long syncs must not run in one request).
  - **Competitor examples:** VT✅ (restartable steps); EM✅ (re-run queue); SH✅ (re-export flag).
  - **UX implications:** Restart control on failed steps; progress indicator.
  - **Reliability/performance implications:** Worker time/memory limits kill long requests; chunk + commit progress.
  - **Configuration implications:** Chunk size.
  - **Architecture dependency:** requires AR review (AR-003).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Odoo.sh staging disables crons — plan manual triggers for tests.

---

## Domain 15 — Logs, errors, audit trail, and observability

### Definition

In-app, reason-coded, per-record logs (never email-only), an audit trail of sync
actions, and a **recovery-first error center** where each failure shows record,
reason, suggested fix, and a retry control.

### Capabilities

- **Capability ID:** C-OBS-01
  - **Capability name:** Reason-coded, in-app sync/error logs
  - **Description:** In-app log lines with a human-readable **reason** per failure
    ("SKU not found", "tax not found", "customer missing").
  - **User value:** Users see exactly what failed and why — actionable.
  - **Evidence status:** baseline market pattern (demonstrated).
  - **Evidence references:** competitor-feature-matrix.md §7 (EM Log Book/Mismatch Log ✅; SH Sync/Export Logs ✅; VT "every action logged" ✅; **EC email-only**); avoid-list.md (A-LOG-1/A-LOG-3).
  - **Competitor examples:** EM✅ (reason-coded Log Book); SH✅; VT✅; WK✅ (Feeds); **EC⬜ (email-only — dead end)**.
  - **UX implications:** Reasons, not stack traces; per-line drill-down.
  - **Reliability/performance implications:** In-app log is the source of truth; alerts are secondary (A-LOG-1).
  - **Configuration implications:** Log retention.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EM's reason-coded Mismatch Log is the observability bar; EC email-only is the floor.

- **Capability ID:** C-OBS-02
  - **Capability name:** Audit trail of sync actions
  - **Description:** A durable record of every sync action (what/when/by whom/
    result) for traceability.
  - **User value:** Answer "what happened to this record and when".
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-deep-dives.md (VT "every sync action logged" + retention + trace logs ✅; SH audit tables ✅; EM Log Book + chatter ✅).
  - **Competitor examples:** VT✅/SH✅/EM✅; WK✅ (Sync History); EC🟨.
  - **UX implications:** Filterable audit view; per-record history.
  - **Reliability/performance implications:** Retention policy; Odoo `ir.logging`/chatter or a dedicated model.
  - **Configuration implications:** Retention window.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT logging + restartable jobs are praised in reviews.

- **Capability ID:** C-OBS-03
  - **Capability name:** Recovery-first error center
  - **Description:** A dedicated error surface where each failure shows record,
    reason, suggested fix, and a **retry** (auto + one-click manual), with isolated
    failures.
  - **User value:** Errors are a to-do list with fixes, not a dead end.
  - **Evidence status:** inference (synthesis — no competitor has the full combination).
  - **Evidence references:** gaps-opportunities.md (O-LOG-1 — nobody combines reason-coded per-record logs + isolation + auto-retry + one-click retry + next-action); ux-ui-benchmark.md (EM isolation + VT retry + SH re-export).
  - **Competitor examples:** EM✅ (isolation/reasons); VT✅ (auto-retry/diagnostics); SH✅ (re-export flag/counts) — **split across three, unified by none**.
  - **UX implications:** Each failure = record + reason + fix hint + retry; failures isolated from successes.
  - **Reliability/performance implications:** Depends on retry classification (C-JOB-02) and named causes (C-DASH-04).
  - **Configuration implications:** None.
  - **Architecture dependency:** requires AR review (AR-006).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate.
  - **Notes:** The unified error center is a core "best operator UX" differentiator (O-PREM-2).

- **Capability ID:** C-OBS-04
  - **Capability name:** Failed-job notifications to responsible users
  - **Description:** Notify the responsible user when jobs fail (in-app; alerts
    secondary to the in-app log).
  - **User value:** Failures get noticed without watching a dashboard.
  - **Evidence status:** competitor demonstrated (VT).
  - **Evidence references:** competitor-deep-dives.md (VT Failed Job Notifications on user profiles ✅); ux-ui-benchmark.md (best patterns #9).
  - **Competitor examples:** VT✅; EC🟨 (email-only — but email is the *only* surface, an anti-pattern); others ⬜.
  - **UX implications:** Notification links to the error center, not a bare email.
  - **Reliability/performance implications:** Alerts complement, don't replace, the in-app log (A-LOG-1).
  - **Configuration implications:** Who is notified; channel.
  - **Architecture dependency:** light.
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** VT notifies the right user; EC's email-*only* model is the counter-example.

---

## Domain 16 — Mapping, matching, and duplicate prevention

### Definition

The binding/mapping layer: a per-store Shopify-GID ↔ Odoo binding, documented
dedup keys (SKU/barcode/email/ID-write-back), directional + testable field
mappings with a dry-run, and safe handling of deleted bindings.

### Capabilities

- **Capability ID:** C-MAP-01
  - **Capability name:** External-ID / Shopify-GID binding model
  - **Description:** A per-store binding that links each Odoo record to its Shopify
    GID (and back), used as the idempotent upsert/dedup key.
  - **User value:** The same Shopify record always resolves to the same Odoo record
    — no duplicates.
  - **Evidence status:** competitor demonstrated + official-platform requirement + inference.
  - **Evidence references:** common-patterns.md (Shopify-ID write-back: EM/SH/VT ✅); odoo-official-architecture-notes.md (`ir.model.data` external IDs as binding key — inference); gaps-opportunities.md (O-DUP-1); architecture-review-log.md (AR-005).
  - **Competitor examples:** EM✅ (stored reference blocks re-export); SH✅ (Shopify ID write-back); VT✅; others 🟨/implicit.
  - **UX implications:** Show the Shopify link on each record.
  - **Reliability/performance implications:** REST↔GraphQL ID formats differ — store GID; indexed lookups; handle deleted bindings.
  - **Configuration implications:** Per-store keys (multi-store).
  - **Architecture dependency:** requires AR review (AR-005 — `ir.model.data` reuse vs dedicated binding model).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** No competitor clearly documents its dedup keys or deleted-binding handling — whitespace.

- **Capability ID:** C-MAP-02
  - **Capability name:** Duplicate prevention (documented dedup keys)
  - **Description:** Explicit, documented dedup keys per object (SKU/barcode for
    products, email for customers, GID for linking) with uniqueness enforcement.
  - **User value:** No duplicate products/customers/orders.
  - **Evidence status:** baseline market pattern (implicit) + inference (documentation is the gap).
  - **Evidence references:** common-patterns.md (SKU/barcode + email dedup: EM/VT ✅); gaps-opportunities.md (O-DUP-1 — keys mostly implicit); quality-feedback-loop.md §5 (duplicate/double-decrement lesson).
  - **Competitor examples:** EM✅ (email/SKU + re-export block); VT✅ (multi-key); SH🟨/TQ🟨/EC🟨/WK🟨.
  - **UX implications:** Show which key matched; manual override/merge.
  - **Reliability/performance implications:** Binding-table uniqueness + multi-location regression tests (A-IMP-2).
  - **Configuration implications:** Key selection per object.
  - **Architecture dependency:** requires AR review (AR-005).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Duplicates/double-decrement are the classic connector defects — document the keys.

- **Capability ID:** C-MAP-03
  - **Capability name:** Directional, testable field mapping with dry-run
  - **Description:** Per-field mapping with direction control, safe transforms, a
    test-against-live-data option, and a preview/dry-run before destructive apply.
  - **User value:** Controllable, safe mappings; no blind pushes.
  - **Evidence status:** competitor demonstrated (VT strongest).
  - **Evidence references:** best-in-class-observations.md (VT per-field direction + Python transforms + test-against-live-data + Preview/Report; EM CSV fallback); avoid-list.md (A-CFG-1).
  - **Competitor examples:** VT✅ (most advanced); EM✅ (SKU match or CSV/XLSX map); SH✅ (directional metafields); TQ🟨.
  - **UX implications:** Direction per field; dry-run/preview; CSV fallback for non-SKU catalogs.
  - **Reliability/performance implications:** Test-before-apply reduces bad writes; transforms must be sandboxed (custom Python = power-user).
  - **Configuration implications:** Mapping rows; transform expressions (advanced tier).
  - **Architecture dependency:** requires AR review (mapping extensibility → AR-004/AR-005).
  - **Candidate classification:** likely baseline (basic mapping) / premium (transforms+test).
  - **MVP relevance:** candidate (basic) / later (custom Python transforms).
  - **Notes:** VT's testable directional mapping is the mapping-UX bar; custom Python is advanced.

- **Capability ID:** C-MAP-04
  - **Capability name:** Deterministic routing (gateway / location / market)
  - **Description:** Deterministic mapping rows for gateway→journal, location↔
    warehouse, and market→company/warehouse/pricelist (country→currency→fallback).
  - **User value:** Records route to the right journal/warehouse/company reliably.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** common-patterns.md (per-gateway, per-location mapping); competitor-deep-dives.md (EM market routing country→currency→fallback ✅; SH gateway matrix ✅; VT External Location grid ✅).
  - **Competitor examples:** EM✅ (deterministic market routing); SH✅ (gateway matrix); VT✅ (location grid).
  - **UX implications:** Mapping tables with a default fallback.
  - **Reliability/performance implications:** Deterministic fallback avoids ambiguous routing.
  - **Configuration implications:** Mapping tables per dimension.
  - **Architecture dependency:** light (per-market → AR review).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** EM's country→currency→fallback is a clean deterministic pattern.

---

## Domain 17 — Multi-store, multi-company, and permissions

### Definition

Connect multiple Shopify stores with per-store configuration isolation, multi-
company isolation via record rules, and role-based access (admin vs functional
user). Multi-company is widely claimed but rarely demonstrated (EM/VT only).

### Capabilities

- **Capability ID:** C-MULTI-01
  - **Capability name:** Multi-store with per-store configuration isolation
  - **Description:** Connect multiple Shopify stores, each with its own connection,
    config, mappings, and bindings.
  - **User value:** Run several stores from one Odoo without config bleed.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §8 (VT "as many stores as you want" ✅; SH multi-store in one DB 🟨; TQ "unlimited" 🟨); ux-ui-benchmark.md (per-store config isolation).
  - **Competitor examples:** VT✅; SH🟨; TQ🟨; WK➖ (single-store framing); EC⬜.
  - **UX implications:** "Which store does this belong to" on every record.
  - **Reliability/performance implications:** Per-store bindings/keys (multi-store dedup).
  - **Configuration implications:** Per-store connection records.
  - **Architecture dependency:** requires AR review (AR-004/AR-005).
  - **Candidate classification:** likely baseline (single-store first is a common MVP framing).
  - **MVP relevance:** candidate (question: single- vs multi-store at MVP — RB-13).
  - **Notes:** Per-store config isolation is the requirement; MVP may start single-store.

- **Capability ID:** C-MULTI-02
  - **Capability name:** Multi-company isolation (record rules)
  - **Description:** Isolate data per Odoo company using record rules, with
    deterministic company/warehouse/pricelist routing.
  - **User value:** Correct company scoping; no cross-company leakage.
  - **Evidence status:** competitor demonstrated (EM/VT) + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §8 (**EM via Markets per-market company ✅; VT multi-company inventory ✅; WK default-Company field only ➖ (not demonstrated — DP-004); SH unverified**); odoo-official-architecture-notes.md (record rules global=AND/group=OR).
  - **Competitor examples:** EM✅/VT✅ (demonstrated); **WK➖ (config field ≠ support — DP-004)**; SH⬜/TQ⬜/EC⬜.
  - **UX implications:** Company shown on records; company-scoped views.
  - **Reliability/performance implications:** Record-rule semantics (global intersect / group unify) must be correct to avoid over/under-exposure.
  - **Configuration implications:** Company↔store↔warehouse mapping.
  - **Architecture dependency:** requires AR review (AR-004; security).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** later (single-company first?).
  - **Notes:** WK's default Company field is the DP-004 example — a field is not multi-company support.

- **Capability ID:** C-MULTI-03
  - **Capability name:** Role-based access (admin vs functional user)
  - **Description:** Access-rights groups + record rules so only admins see
    credentials/config while functional users run syncs and fix errors.
  - **User value:** Least-privilege; safer operations.
  - **Evidence status:** competitor demonstrated + official-platform requirement.
  - **Evidence references:** competitor-feature-matrix.md §7 (EM Odoo user rights ✅; SH granular access-rights groups ✅); odoo-official-architecture-notes.md (`ir.model.access.csv` deny-by-default; groups; `sudo()` caution).
  - **Competitor examples:** EM✅/SH✅ (access-gated setup); VT➖; others ⬜.
  - **UX implications:** Two audiences (admin vs functional) gated by rights.
  - **Reliability/performance implications:** `ir.model.access.csv` + groups + record rules; `sudo()` only as an audited bypass (A-IMP-5).
  - **Configuration implications:** Group membership.
  - **Architecture dependency:** requires AR review (security).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** SH gates setup behind an access right — a good security default to adopt.

- **Capability ID:** C-MULTI-04
  - **Capability name:** Domain-isolated / per-store configuration model
  - **Description:** Configuration is organised by domain and isolated per store/
    company (no global bleed), enabling feature flags per capability group.
  - **User value:** Clean, scoped config; enable only what's needed.
  - **Evidence status:** inference (architecture input) + competitor demonstrated (partial).
  - **Evidence references:** ux-ui-benchmark.md (per-store config isolation); gaps-opportunities.md (O-MOD-1 layered isolated addon family); avoid-list.md (A-MOD-1/A-MOD-2).
  - **Competitor examples:** VT✅ (tabbed per-instance config); EM/SH per-instance config; others ➖.
  - **UX implications:** Config grouped by domain; per-store scoping.
  - **Reliability/performance implications:** Isolation prevents one store's config affecting another.
  - **Configuration implications:** Config records keyed per store/company.
  - **Architecture dependency:** requires AR review (AR-004 module boundaries — **do not name final modules**).
  - **Candidate classification:** likely baseline.
  - **MVP relevance:** candidate.
  - **Notes:** Architecture input only; module boundaries are RB-14/AR-004, not decided.

---

## Domain 18 — Shopify Markets, B2B, POS, gift cards, metafields, and advanced Shopify features

### Definition

Premium breadth capabilities that only 1–2 competitors demonstrate each; candidates
for **optional add-ons** on a correct, observable core, not MVP baseline.

### Capabilities

- **Capability ID:** C-ADV-01
  - **Capability name:** Shopify Markets & Catalogs
  - **Description:** Per-market configuration (company/warehouse/pricelist/fiscal/
    language/journal) and Catalogs-based per-market pricing.
  - **User value:** Correct localized selling across markets.
  - **Evidence status:** competitor demonstrated (EM/VT).
  - **Evidence references:** competitor-feature-matrix.md §8 (EM/VT demonstrate Markets & Catalogs ✅); competitor-deep-dives.md (EM per-market mapping + country→currency→fallback; VT v2.0.0 Markets).
  - **Competitor examples:** EM✅/VT✅; TQ🟨; WK⬜/EC⬜/SH⬜.
  - **UX implications:** Per-market mapping; "markets sync-only" (EM); no multi-warehouse delivery with Markets (EM limitation).
  - **Reliability/performance implications:** Order routing determinism; pricing dry-run (C-PRICE-03).
  - **Configuration implications:** Market↔company/warehouse/pricelist.
  - **Architecture dependency:** requires AR review.
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** later.
  - **Notes:** Demonstrated by EM/VT; a premium differentiator, not baseline.

- **Capability ID:** C-ADV-02
  - **Capability name:** B2B (company accounts, VAT/VIES)
  - **Description:** Detect companies vs individuals, import VAT with VIES
    validation, and prevent B2B duplicate contacts.
  - **User value:** Correct B2B customer/tax handling.
  - **Evidence status:** competitor demonstrated (VT only).
  - **Evidence references:** competitor-feature-matrix.md §8 (only VT ✅); competitor-deep-dives.md (VT VAT/VIES 3× retry, B2B dedup v2.1.6).
  - **Competitor examples:** VT✅; TQ🟨; others ⬜.
  - **UX implications:** Company vs individual on the contact; VAT validation feedback.
  - **Reliability/performance implications:** VIES retry (external dependency).
  - **Configuration implications:** B2B detection rules.
  - **Architecture dependency:** light.
  - **Candidate classification:** premium differentiator (whitespace — only VT).
  - **MVP relevance:** later.
  - **Notes:** Differentiating whitespace; only VT demonstrates it.

- **Capability ID:** C-ADV-03
  - **Capability name:** POS order import
  - **Description:** Import Shopify POS orders (e.g. via "Closed" status + default
    POS customer).
  - **User value:** Unified online + POS order picture in Odoo.
  - **Evidence status:** competitor claim / demonstrated (partial).
  - **Evidence references:** competitor-feature-matrix.md §8 (TQ/EM claim POS; VT via "Closed" status ✅ partial); competitor-deep-dives.md (VT POS via Closed status).
  - **Competitor examples:** VT✅ (Closed-status path); EM🟨/TQ🟨; others ⬜.
  - **UX implications:** POS channel handling; default POS customer.
  - **Reliability/performance implications:** POS order topics; PII handling.
  - **Configuration implications:** Enable POS import; default customer.
  - **Architecture dependency:** light.
  - **Candidate classification:** advanced-later.
  - **MVP relevance:** later.
  - **Notes:** Partially demonstrated (VT); mostly claimed elsewhere.

- **Capability ID:** C-ADV-04
  - **Capability name:** Gift cards
  - **Description:** Import/export gift cards and disable-in-Shopify, with masked
    code/balance/expiry.
  - **User value:** Gift-card data reflected in Odoo.
  - **Evidence status:** competitor demonstrated (SH only).
  - **Evidence references:** competitor-feature-matrix.md §8 (only SH demonstrates ✅); competitor-deep-dives.md (SH gift cards import/export/disable ✅; EM scopes+auto-fulfil 🟨).
  - **Competitor examples:** SH✅; EM🟨; TQ🟨; others ⬜.
  - **UX implications:** Masked sensitive fields.
  - **Reliability/performance implications:** Gift-card scopes.
  - **Configuration implications:** Enable gift-card sync.
  - **Architecture dependency:** light.
  - **Candidate classification:** optional add-on.
  - **MVP relevance:** later.
  - **Notes:** Niche breadth differentiator; only SH demonstrates.

- **Capability ID:** C-ADV-05
  - **Capability name:** Metafields (directional, per-entity)
  - **Description:** Map Shopify metafields (product/variant/order/customer) with
    fetch scope, sync direction, and type handling.
  - **User value:** Custom data flows both ways.
  - **Evidence status:** competitor demonstrated (EM/VT/SH).
  - **Evidence references:** competitor-feature-matrix.md §8 (EM/VT/SH directional metafields ✅; VT "30+ types"); competitor-deep-dives.md (EM Fetch Scope/Sync Direction ✅).
  - **Competitor examples:** EM✅/VT✅/SH✅; TQ🟨; WK➖/EC⬜.
  - **UX implications:** Directional mapping (Import/Export/Both); type casting.
  - **Reliability/performance implications:** Type handling; custom-namespace activation.
  - **Configuration implications:** Metafield mapping rows.
  - **Architecture dependency:** light (mapping extensibility → AR-004/AR-005).
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** later.
  - **Notes:** Well-demonstrated (EM/VT/SH); still advanced relative to core sync.

- **Capability ID:** C-ADV-06
  - **Capability name:** Extended breadth (abandoned-checkout→CRM, recommendations, Buy-with-Prime)
  - **Description:** SH-unique breadth: abandoned checkouts → CRM leads, product
    recommendations, Buy-with-Prime order import.
  - **User value:** Recovery/merchandising extras beyond core commerce.
  - **Evidence status:** competitor demonstrated (SH only).
  - **Evidence references:** competitor-feature-matrix.md §8 (SH-unique breadth ✅); competitor-deep-dives.md (SH abandoned-checkout→CRM, recommendations, Buy-with-Prime ✅).
  - **Competitor examples:** SH✅; others ⬜.
  - **UX implications:** Separate feature tabs; opt-in.
  - **Reliability/performance implications:** Each has its own queue (SH).
  - **Configuration implications:** Enable per feature.
  - **Architecture dependency:** light.
  - **Candidate classification:** optional add-on.
  - **MVP relevance:** later.
  - **Notes:** Clear "optional add-on" candidates; SH-only evidence.

---

## Domain 19 — Reporting, analytics, and operational insights

### Definition

Operational insight (queue/sync/failure metrics, activity charts) and financial
reporting (sales analysis, net profit, analytic-account-per-channel). Some
reporting is Enterprise-edition-gated in Odoo.

### Capabilities

- **Capability ID:** C-RPT-01
  - **Capability name:** Operational sync analytics
  - **Description:** Metrics/charts on sync volume, queue throughput, and failure
    counts over time.
  - **User value:** Understand connector health and load trends.
  - **Evidence status:** competitor demonstrated.
  - **Evidence references:** competitor-feature-matrix.md §8–9 (SH dashboard + activity chart ✅; EM performance graph ✅; TQ Analytics dashboard 🟨).
  - **Competitor examples:** SH✅ (daily activity chart); EM✅; TQ🟨; VT⬜/EC⬜.
  - **UX implications:** Overlaps the command center (C-DASH-03).
  - **Reliability/performance implications:** Efficient aggregation (`_read_group`).
  - **Configuration implications:** Time window.
  - **Architecture dependency:** light.
  - **Candidate classification:** premium differentiator.
  - **MVP relevance:** candidate (basic counts) / later (rich analytics).
  - **Notes:** SH's activity chart is the best operational visual.

- **Capability ID:** C-RPT-02
  - **Capability name:** Financial / sales reporting (channel analytic, net profit)
  - **Description:** Sales analysis, analytic-account-per-channel, and net-profit
    reporting (Enterprise-gated in Odoo).
  - **User value:** Channel profitability and sales insight.
  - **Evidence status:** competitor demonstrated (EM).
  - **Evidence references:** competitor-feature-matrix.md §8 (EM Sales Analysis + Net Profit Enterprise-only ✅; SH dashboard ✅); competitor-deep-dives.md (EM analytic account per channel ✅).
  - **Competitor examples:** EM✅ (analytic-per-channel, Net-Profit Enterprise); SH✅; TQ🟨.
  - **UX implications:** Report views; disclose Enterprise-only features honestly.
  - **Reliability/performance implications:** Analytic tagging per channel.
  - **Configuration implications:** Channel↔analytic account.
  - **Architecture dependency:** light.
  - **Candidate classification:** advanced-later.
  - **MVP relevance:** later.
  - **Notes:** Net-Profit is Enterprise-only (EM) — disclose edition gating (honesty).

---

## Domain 20 — Documentation, support, demo, and maintenance transparency

### Definition

The trust/evaluability surround: readable screenshot-rich non-gated docs, a dated
honest changelog, ticket/helpdesk support, a public demo, and App-Store/Built-for-
Shopify readiness. Trust signals materially affect evaluability (VT rewarded;
TQ/EC/SH penalized).

### Capabilities

- **Capability ID:** C-DOCS-01
  - **Capability name:** Readable, screenshot-rich, non-gated documentation
  - **Description:** Public, crawlable docs with screenshots and honest limitation
    disclosure — never bot-blocked or sign-in-gated.
  - **User value:** Buyers/users can evaluate and self-serve.
  - **Evidence status:** competitor demonstrated (EM best) + inference.
  - **Evidence references:** gaps-opportunities.md (O-DOC-1); avoid-list.md (A-DOC-1); competitor-deep-dives.md (EM honest docs ✅; **TQ docs 403; EC no screenshots + gated guide; SH no changelog**).
  - **Competitor examples:** EM✅ (rich, honest); VT✅ (Confluence KB); **TQ🔒 (403); EC🚫 (none + gated); SH✅(captions)**.
  - **UX implications:** Docs mirror in-app flows; disclosed limitations.
  - **Reliability/performance implications:** N/A (product surround).
  - **Configuration implications:** N/A.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline (parallel to build).
  - **MVP relevance:** candidate.
  - **Notes:** EC's blocked setup guide (R5) and TQ's 403 docs are the anti-patterns.

- **Capability ID:** C-DOCS-02
  - **Capability name:** Dated, honest changelog (discloses fixes)
  - **Description:** A dated, mechanism-level changelog that discloses bug fixes
    (including CRITICAL ones), like VT's.
  - **User value:** Users can judge currency/maintenance and trust the vendor.
  - **Evidence status:** competitor demonstrated (VT best).
  - **Evidence references:** best-in-class-observations.md (VT dated release notes disclosing CRITICAL fixes ✅); avoid-list.md (A-DOC-2/A-DOC-3); competitor-deep-dives.md (**SH none; EM stale on v19; TQ blocked**).
  - **Competitor examples:** VT✅ (best); EC✅ (recent cadence); **EM stale on v19; SH none; TQ🔒**.
  - **UX implications:** Changelog visible; cite current platform figures (avoid stale — DP-001/A-DOC-3).
  - **Reliability/performance implications:** N/A.
  - **Configuration implications:** N/A.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline (cheap, high-trust).
  - **MVP relevance:** candidate.
  - **Notes:** Trust-and-transparency as a feature (O-PREM-4).

- **Capability ID:** C-DOCS-03
  - **Capability name:** Support, public demo, and self-test
  - **Description:** Ticket/helpdesk support, a public honest demo, and a built-in
    "test sync" / readiness self-check.
  - **User value:** Easy evaluation and support.
  - **Evidence status:** competitor demonstrated (support) / claim (demo) + inference.
  - **Evidence references:** gaps-opportunities.md (O-TEST-1 public demo + self-test); common-patterns.md (ticket/helpdesk support); competitor-deep-dives.md (WK UV Desk ✅; EM Helpdesk ✅; TQ demo sandbox 🟨).
  - **Competitor examples:** WK✅/EM✅/VT✅ (support); TQ🟨 (demo sandbox claim); EC gated.
  - **UX implications:** Built-in readiness self-check (ties to C-CONN-05).
  - **Reliability/performance implications:** Self-test exercises the real sync path.
  - **Configuration implications:** N/A.
  - **Architecture dependency:** none.
  - **Candidate classification:** likely baseline (support) / premium (demo/self-test).
  - **MVP relevance:** candidate (support) / later (public demo).
  - **Notes:** Evaluability is poor across the field — a demo + self-test is differentiating.

- **Capability ID:** C-DOCS-04
  - **Capability name:** App-Store / Built-for-Shopify readiness
  - **Description:** Meet App-Store requirements (OAuth-first, compliance webhooks,
    least-privilege scopes, TLS, billing API) and Built-for-Shopify performance
    thresholds — **if** public distribution is chosen.
  - **User value:** Distributable, compliant app (if public).
  - **Evidence status:** official-platform requirement (future-readiness only).
  - **Evidence references:** shopify-official-api-notes.md (App-Store requirements; compliance webhooks; Built-for-Shopify thresholds); competitor-deep-dives.md (VT Official Odoo partner; TQ App-Store listing).
  - **Competitor examples:** all are Odoo-Apps/marketplace listings; none verified against Shopify App-Store review here.
  - **UX implications:** Mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`).
  - **Reliability/performance implications:** Built-for-Shopify perf thresholds (LCP/CLS/INP); billing via Shopify App Pricing.
  - **Configuration implications:** Distribution model (public vs custom).
  - **Architecture dependency:** requires AR review (AR-002 — distribution decides GraphQL-only + billing).
  - **Candidate classification:** unknown (depends on distribution decision).
  - **MVP relevance:** unknown.
  - **Notes:** Distribution (public App-Store vs custom app) is an **open AR-002 question** — do not decide.

---

## Cross-cutting capability groups

These span multiple domains and are consolidated here (each is realised inside the
domain capabilities above; listed together so later sprints can consume them as
themes). None is a decision.

- **CC-1 — Idempotency & correctness by default.** C-JOB-04 (idempotency keys),
  C-SYNC-06 (reconciliation), C-INV-01/C-RET-01 (idempotent inventory/refunds),
  C-MAP-01/02 (binding + dedup). *Tier-1-mandated; the market's biggest whitespace.*
- **CC-2 — Recovery-first operations.** C-OBS-03 (error center), C-JOB-02/03 (retry
  classification + auto-retry), C-DASH-04 (named causes), C-OBS-04 (failed-job
  notifications).
- **CC-3 — Honesty & transparency.** C-SYNC-07 (freshness/latency labels),
  C-DOCS-01/02 (non-gated docs + dated changelog), disclosed limitations (EM/VT).
- **CC-4 — Safe-by-default destructive actions.** C-PROD-05 / C-PRICE-03 / C-MAP-03
  (dry-run/preview), C-RET-03 (irreversible-action warnings). *Guards `productSet`
  delete-on-omit (A-IMP-1).*
- **CC-5 — Progressive disclosure & inline help.** C-CONN-03 (wizard), C-MULTI-04
  (config model), inline help on jargon (A-UX-3). Sensible defaults + an "advanced"
  tier.
- **CC-6 — Feature flags / enable-disable capability groups.** Turn capability
  groups (e.g. gift cards, Markets, B2B, payouts) on/off per store — enables
  "optional advanced add-ons" (C-ADV-*) on a lean core. *Architecture input, not a
  module decision (AR-004).*
- **CC-7 — Modularity & extension points.** Domain-isolated config (C-MULTI-04),
  mapping extensibility (C-MAP-03), transport/API abstraction (isolating REST vs
  GraphQL — AR-002), link modules for `sale`/`stock`/`account`/`delivery` glue
  (AR-004). **No final module names or boundaries are defined here** (RB-14/AR-004).
- **CC-8 — Multi-tenancy & permissions.** Per-store isolation (C-MULTI-01), per-
  company isolation (C-MULTI-02), role-based access (C-MULTI-03).

---

## Capability classification summary

Counts are **inputs for review**, not scope. Full per-capability values are in
[`capability-evidence-map.md`](./capability-evidence-map.md).

| Candidate classification | Example capabilities | Count (approx.) |
| --- | --- | --- |
| **likely baseline** | connection, product/order/inventory/customer sync, fulfillment, refunds, logs, dedup, scheduled+manual+webhook sync, reconciliation, idempotency, role-based access | ~40 |
| **premium differentiator** | unified command center, named-cause diagnostics, recovery-first error center, first-class reconciliation, auto-retry, rate-limit throttling, idempotency-as-default, dry-run everywhere, freshness labels, testable mapping, multi-company, Markets, B2B | ~20 |
| **advanced-later** | SEO/taxonomy, BoM stock, POS, order fraud, financial reporting, bulk backfill, per-market pricing | ~10 |
| **optional add-on** | gift cards, abandoned-checkout→CRM, recommendations, Buy-with-Prime, payout reconciliation | ~6 |
| **unknown** | App-Store/Built-for-Shopify readiness (depends on distribution) | ~1 |

**By capability type (four-way tag):**

- **Product/UX-heavy:** Domains 1, 2, 15 (UX side), 20, plus dry-run/progressive-
  disclosure cross-cutting.
- **Reliability/performance-heavy:** Domains 13, 14, 16 (binding), plus CC-1/CC-2.
- **Configuration-heavy:** Domains 5, 8 (workflow), 16 (mapping), 17 (per-store).
- **Architecture-dependency-heavy (requires AR review):** Domains 6 (AR-007), 10
  (AR-008), 13/14 (AR-003), 16 (AR-005), plus API strategy (AR-002) and module
  boundaries (AR-004) throughout.

---

## MVP-candidate inputs, not decisions

> **These are candidates for later MVP review (RB-13), not an MVP scope.** Nothing
> here is selected, sequenced, or committed. MVP finalization is **gated**.

Capabilities most frequently tagged **MVP relevance: candidate** cluster around a
**correct, observable core**:

- **Connect + prove:** C-CONN-01…05 (OAuth-first, masking, wizard, test connection,
  readiness check).
- **Core object sync:** C-PROD-01/02/03, C-VAR-01/02, C-PRICE-01, C-INV-01/02/03,
  C-CUST-01/02/03, C-ORD-01/03/04, C-PAY-01/02/03, C-FUL-01/03, C-RET-01/03.
- **Sync engine + correctness:** C-SYNC-01…07 (webhooks+HMAC+dedup+scheduled+manual+
  **reconciliation**+freshness), C-JOB-01…05/07 (queue, retry classes, auto-retry,
  idempotency, throttling, resumable), C-MAP-01…04 (binding, dedup, mapping, routing).
- **Operator UX:** C-DASH-01…05, C-OBS-01…04 (command center + recovery-first errors).
- **Permissions:** C-MULTI-03 (role-based access); C-MULTI-01 (single-store first is
  a plausible MVP framing — open).

**Explicitly NOT asserted as MVP:** advanced breadth (Domain 18), payouts (Domain
12), financial reporting (C-RPT-02), per-market pricing (C-PRICE-03), custom-Python
transforms (C-MAP-03 advanced), multi-company (C-MULTI-02). These are **later**
inputs.

---

## Later-phase / advanced inputs, not decisions

Tagged **MVP relevance: later** (candidates for post-MVP phases / optional add-ons,
**not** prioritised):

- **Payouts & reconciliation:** C-POUT-01/02 (Shopify-Payments-only; EM-grade).
- **Advanced refunds/returns:** C-RET-02 (distinct RMA lifecycle).
- **Shopify Markets & per-market pricing:** C-ADV-01, C-PRICE-03.
- **B2B / VAT-VIES:** C-ADV-02.
- **POS:** C-ADV-03.
- **Gift cards:** C-ADV-04.
- **Metafields:** C-ADV-05.
- **Abandoned-checkout→CRM, recommendations, Buy-with-Prime:** C-ADV-06.
- **Advanced analytics / financial reporting:** C-RPT-01 (rich) / C-RPT-02.
- **App-Store packaging / public demo / changelog surround:** C-DOCS-03/04.
- **SEO/taxonomy, BoM stock, bulk backfill:** C-VAR-03/04, C-JOB-06.

These map to the "premium breadth as clean add-ons" theme (O-PREM-3) — **candidate
add-ons on a correct core**, sequenced later and gated.

---

## Capabilities requiring architecture review

Routed to the architecture-review log (AR-002…AR-008, all **evidence-pending / not
decided**). Listed as **inputs**; **no architecture is decided or re-litigated here**.

| AR row | Topic | Capabilities that depend on it |
| --- | --- | --- |
| **AR-002** | API strategy (REST/GraphQL/hybrid), distribution, bulk | C-CONN-01, C-PROD-01/02/05, C-VAR-01, C-ORD-02, C-JOB-05/06, C-DOCS-04 |
| **AR-003** | Sync orchestration (cron / webhooks+reconcile / `queue_job`) | C-SYNC-01/03/04/06, C-JOB-01/02/07, C-ORD-01/04, C-CONN-05, C-DASH-* |
| **AR-004** | Module boundaries (addon family, link modules) | C-MULTI-04, C-MAP-03, C-ADV-05, CC-6, CC-7 (no final names) |
| **AR-005** | Mapping & duplicate prevention (binding model) | C-MAP-01/02, C-CUST-02/03, C-PROD-01/02, C-MULTI-01 |
| **AR-006** | Error handling & retries, idempotency | C-JOB-02/03/04, C-RET-01, C-INV-01, C-SYNC-06, C-OBS-03 |
| **AR-007** | Inventory architecture (item/level/location, quantity states) | C-INV-01/02/03/04, C-VAR-04 |
| **AR-008** | Fulfillment architecture (FulfillmentOrder-based) | C-FUL-01/02 |

Security (HMAC, `sudo()`, record rules) items — C-SYNC-02, C-MULTI-02/03 — also
require review under the security lens noted in the avoid-list (A-SYNC-6, A-IMP-5).

---

## Capabilities with weak or blocked evidence

Per DP-003/DP-004, capabilities resting on **weak** (claim-only / blocked / no-
screenshot) evidence are flagged so they are **not overstated** downstream:

- **Teqstars (TQ) — docs 403-blocked → all TQ support is claim-only (weak):**
  idempotency/queue-retry (C-JOB-03/04), Markets/B2B (C-ADV-01/02), payout auto-
  reconcile (C-POUT), pHash image dedup (C-VAR-02), smart matching (C-MAP-02) — all
  **competitor claim only / unverifiable**.
- **ecommerce_shopify (EC) — no screenshots → weak:** all EC capabilities are
  listing claims (cron-based); **product export direction not found**; webhooks
  **explicitly absent**; error handling **email-only** (anti-pattern).
- **sh_shopify_connector (SH) — captions, no ratings/changelog → medium-behaviour,
  low-trust:** breadth (C-ADV-04/05/06) rests on captions; **multi-company
  not-found** (do not classify as multi-company support); idempotency/HMAC unstated.
- **Webkul (WK) — single vendor guide (medium):** multi-company is a **config field
  only (➖, not demonstrated — DP-004)**; variants/images/refunds/webhooks/multi-
  location **not found**.
- **Blocked source (R5 Google Doc):** = EC's setup guide; content unknown (🔒) — no
  capability is inferred from it.
- **Whitespace (open question, no competitor evidence):** rate-limit throttling
  (C-JOB-05), first-class reconciliation surface (C-SYNC-06), webhook-id dedup
  (C-SYNC-03), empty states (C-DASH-06) — classified by **inference / platform
  requirement**, not competitor demonstration.

---

## Open questions

1. **Distribution model** (public App-Store vs custom app) — decides GraphQL-only,
   billing, compliance-webhook obligations (AR-002; C-DOCS-04). **Unresolved.**
2. **Single-store vs multi-store at MVP** and **single- vs multi-company** (C-MULTI-
   01/02; RB-13). **Not decided.**
3. **Reconciliation cadence/scope** and **per-object vs global freshness** (C-SYNC-
   06/07). **Open.**
4. **Error/retry taxonomy** — which errors are auto-retryable vs human-fixable
   (C-JOB-02, C-OBS-03, C-DASH-04). **Open.**
5. **Binding model** — reuse `ir.model.data` external IDs vs a dedicated per-store
   binding model; deleted-binding handling (C-MAP-01; AR-005). **Open.**
6. **Queue framework** — `ir.cron`-based vs OCA `queue_job` (non-core dependency;
   Odoo-Online implications) (C-JOB-01; AR-003). **Open.**
7. **Which capability groups are core vs optional add-ons** (feature flags, CC-6;
   Domain 18). **Open (RB-13).**
8. **Blocked/weak evidence to firm up:** Teqstars docs (403), EC setup guide (R5),
   17 unread VT Confluence articles — do these change any classification? **Open.**
9. **Payout modelling** for non-Shopify-Payments gateways (`OrderTransaction`
   ledger) (C-POUT; C-PAY-03). **Open.**
10. **Odoo edition gating** (Enterprise-only reports like Net Profit) — how to
    disclose/handle (C-RPT-02). **Open.**

---

## Review notes for ChatGPT

- **Taxonomy completeness & naming:** Are the 20 domains and the capability set the
  right canonical decomposition? Any missing/duplicated/mis-placed capability?
- **Evidence discipline (DP-003/DP-004):** Spot-check that no competitor claim is
  presented as a fact; that `✅`/"demonstrated" is only used with specific evidence;
  that WK multi-company stays a **config field (➖)**, SH multi-company stays
  **not-found**, EC export stays **not-found**, and TQ items stay **claim-only**.
- **Classification calibration:** Are "likely baseline / premium / advanced-later /
  optional add-on" and "MVP candidate / later / unknown" reasonable **as inputs**?
  Flag anything that reads like a premature decision.
- **Architecture routing:** Confirm the AR-002…AR-008 mapping is correct and that
  **no architecture is decided** (no queue framework, no REST/GraphQL choice, no
  module boundaries/names, no data models).
- **Whitespace priorities:** Endorse (or re-rank) the correctness whitespace
  (reconciliation, idempotency, rate-limit throttling, webhook-id dedup) and the
  operator-UX whitespace (command center + recovery-first errors) as the leading
  differentiation inputs for RB-13/RB-14 — **without** locking MVP.
- **Next-sprint sequencing:** Confirm RB-13 (MVP implications) and RB-14
  (architecture prep) as the next gated steps, consuming this taxonomy + the
  evidence map.

> **Nothing in this document is a decision.** MVP scope (RB-13), architecture
> (RB-14 / AR-002…AR-008), and module boundaries remain **gated** pending ChatGPT
> review (`CLAUDE.md` §4–§5, §9–§10).
