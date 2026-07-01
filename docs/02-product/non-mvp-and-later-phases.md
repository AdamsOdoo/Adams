# Non-MVP and Later-Phase Candidates

> The **strict boundary** companion to [`./mvp-scope.md`](./mvp-scope.md). It records
> what is **deliberately kept out of the first release**, why, and what must be true
> before each item is reconsidered — so the MVP stays *small but excellent* and does
> not silently bloat. Every item here is an **input**, not a decision.

## Status

> **Proposed for ChatGPT review — not final until accepted.**

- **Sprint:** Product Sprint F (RB-13). **Phase:** MVP synthesis — **no-code gate in
  force** (`CLAUDE.md` §4–§5). **Decides nothing.**
- **Governance:** exclusions here are **recommendations against MVP inclusion only**,
  **not** rejected-approach decisions (`CLAUDE.md` §10 — formal rejection routes
  through architecture review). No architecture, ADR, module boundary, data model,
  queue framework, API strategy, or distribution model is decided.
- **Evidence discipline (DP-003/DP-004/DP-006):** competitor claims stay claims; a
  config field is not demonstrated support; a market promise is not demonstrated
  bidirectionality; improvement opportunities are inference; conditional items stay
  conditional.
- **Dates:** competitor evidence access **2026-06-30**; session **2026-07-01**. No new
  sources crawled.

## Purpose

Make the MVP boundary **explicit and defensible**. A premium MVP fails not only by
missing correctness, but by **over-scoping** — pulling in second sync directions,
financial depth, premium breadth, and multi-tenancy that each multiply complexity and
fragility. This document names those items, ties each to its evidence and its
architecture/distribution/edition gate, and states the **revisit condition** so later
phases inherit a clean backlog instead of re-litigating scope.

## Evidence base

Same already-merged evidence as [`./mvp-scope.md`](./mvp-scope.md): the capability
evidence map ([`./capability-evidence-map.md`](./capability-evidence-map.md)) and
feature taxonomy ([`./feature-taxonomy.md`](./feature-taxonomy.md)) for `C-…` IDs and
strengths; the product vision ([`./product-vision.md`](./product-vision.md)) "later/
advanced inputs" and setup/UX principles; the Sprint C research (`O-…`/`A-…` IDs) and
Tier-1 facts; and the QA logs (DP-001…006, AR-002…008).

## Non-MVP rule

An item is **kept out of MVP** if **any** of:

1. **It is a second sync direction or a breadth surface** the correctness core does
   not need (export, publish/channel, pricelists, Markets/B2B/POS/gift cards/
   metafields, extended breadth).
2. **It rests on weak or single-vendor evidence** (D/claim-only, or one-vendor B) and
   is not platform-required.
3. **It is gated by an unresolved decision** — architecture (AR-002…008), distribution
   (AR-002), or Odoo edition/hosting — such that including it forces the decision.
4. **It adds financial or multi-tenancy depth** (payouts, full accounting, refunds/
   returns lifecycle, multi-store/company) beyond what a single-store correctness loop
   requires.

Categories used below: **later** (a named later phase), **optional add-on** (premium,
feature-flagged), **blocked (weak evidence)**, **blocked (distribution)**, **blocked
(edition/hosting)**, **architecture-dependent**.

## Explicitly non-MVP for first release

**Product export (draft-first) + publish/channel control**
- Capability ID(s): C-PROD-02, C-PROD-03, C-PROD-05 (safety, conditional)
- Category: architecture-dependent / later (open — direction call for ChatGPT)
- Why not MVP: a **second sync direction** doubles conflict/direction complexity and
  **forces** the destructive-apply guardrail (**[Fact]** `productSet` delete-on-omit,
  A-IMP-1) plus AR-002/AR-005 decisions.
- Evidence: VT/EM/SH/WK draft-export [Demonstrated] (B); C-PROD-05 safety is A [Fact].
- Risk of including too early: silent data loss on full-state writes; larger, more
  fragile surface; premature architecture commitment.
- What must be true before including: ChatGPT prioritises Odoo-first catalogs; AR-002
  (API) + AR-005 (binding) resolved; C-PROD-05 dry-run/preview built as mandatory.

**Customer export (email dedup, link)**
- Capability ID(s): C-CUST-02
- Category: architecture-dependent / later (open — direction call)
- Why not MVP: second direction; WK/EC are import-only (DP-004) — not demonstrated
  export.
- Evidence: EM link-by-email [Demonstrated] (B).
- Risk of including too early: duplicate/ownership conflicts across systems; binding
  model pulled forward.
- What must be true before including: AR-005 binding + dedup keys resolved; ChatGPT
  wants Odoo-authored customers pushed to Shopify.

**Full payment / invoice / gateway breadth (beyond the minimal order-flow representation)**
- Capability ID(s): C-PAY-01, C-PAY-02, C-PAY-03
- Category: later (open — MVP keeps only the minimal representation the order flow needs)
- Why not MVP: full accounting/gateway integration is a large, edition-sensitive
  surface beyond a correct order import.
- Evidence: VT/SH invoice, EM multi-payment, SH+VT gateway→journal [Demonstrated] (B);
  `OrderTransaction` ledger [Fact].
- Risk of including too early: heavy accounting surface, edition gating, double-invoice
  if not idempotent.
- What must be true before including: ChatGPT defines the MVP order-flow minimum; the
  remainder becomes a Phase-2 accounting module; all of it idempotent (C-JOB-04).

**Refund sync / returns lifecycle / cancellations**
- Capability ID(s): C-RET-01 (open), C-RET-02 (later), C-RET-03 (open)
- Category: later / architecture-dependent (AR-006) — some open
- Why not MVP: "advanced refunds/returns lifecycle" is explicitly non-MVP; refunds tie
  to the deferred Domain 9 minimum; RMA (C-RET-02) is scarce even among competitors.
- Evidence: **[Fact]** `@idempotent` refunds 2026-04 + EM/VT/SH [Demonstrated] (A/B);
  returns API [Fact]; `returnRefund` deprecated → `returnProcess`.
- Risk of including too early: **double-refund** if not idempotent (A-PAY-2);
  irreversible-action footguns (A-RET-2) without strong guards.
- What must be true before including: Domain 9 minimum decided; **idempotency
  mandatory**; AR-006 taxonomy resolved; irreversible-action warnings (C-RET-03).

**Payout import + bank reconciliation**
- Capability ID(s): C-POUT-01, C-POUT-02
- Category: optional add-on / blocked (distribution-agnostic but Shopify-Payments-gated)
- Why not MVP: payouts exist **only for Shopify-Payments stores** (**[Fact]**, A-PAY-1);
  a premium finance surface, not core sync.
- Evidence: EM [Demonstrated] (A SP-only / B reconciliation).
- Risk of including too early: assuming payouts for all gateways (A-PAY-1); finance
  complexity without core value.
- What must be true before including: core loop shipped; store uses Shopify Payments;
  packaged as an optional finance add-on.

**Multi-package / multi-location fulfilment**
- Capability ID(s): C-FUL-02
- Category: later (AR-008)
- Why not MVP: MVP ships single-package tracking write-back (C-FUL-01); split shipments
  add complexity beyond the common case.
- Evidence: EM Put-in-Pack + VT [Demonstrated] (B).
- Risk of including too early: fulfilment-split edge cases before the base loop is solid.
- What must be true before including: C-FUL-01 shipped; AR-008 design resolved.

**Order fraud / risk import**
- Capability ID(s): C-ORD-05
- Category: later (weak — single vendor)
- Why not MVP: single-vendor (VT) demonstrated; not core to the sync loop.
- Evidence: VT [Demonstrated] (B); others 🟨.
- Risk of including too early: surface area without demonstrated broad need.
- What must be true before including: demonstrated customer demand; core loop shipped.

**SEO/taxonomy, BoM/kit stock, pricelists, per-market pricing**
- Capability ID(s): C-VAR-03, C-VAR-04, C-PRICE-02, C-PRICE-03
- Category: later
- Why not MVP: enrichment/pricing breadth, not core correctness; per-market ties to
  Markets (non-MVP).
- Evidence: mostly single-vendor VT [Demonstrated] (B); C-PRICE-03 VT Preview/Report.
- Risk of including too early: config/complexity growth; Markets coupling.
- What must be true before including: core catalog + base pricing shipped; Markets
  decision (for C-PRICE-03).

**Dedicated analytics / financial reporting**
- Capability ID(s): C-RPT-01 (defer), C-RPT-02 (later)
- Category: later
- Why not MVP: the command center covers basic operational counts (C-DASH-03);
  financial reporting is advanced and Odoo-edition-sensitive (Net-Profit
  Enterprise-only).
- Evidence: SH activity chart + EM graph/analytic [Demonstrated] (B).
- Risk of including too early: a reporting surface competing with the command center.
- What must be true before including: command center shipped; edition gating disclosed
  (see edition/hosting section).

## Later-phase candidates

Natural **Phase-2+** work once the correctness core is shipped and accepted:

- **Phase 2 — Bidirectional catalog & customers:** C-PROD-02/03/05, C-CUST-02 (the
  "Option B" surface from [`./mvp-scope.md`](./mvp-scope.md)).
- **Phase 2/3 — Financial depth:** full Domain 9 (C-PAY-01/02/03), refunds
  (C-RET-01), cancellations (C-RET-03), returns/RMA (C-RET-02).
- **Phase 3 — Scale & config depth:** bulk operations (C-JOB-06), pricelists
  (C-PRICE-02), custom transforms (within C-MAP-03), dedicated analytics (C-RPT-01).
- **Phase 3 — Multi-tenancy:** multi-store (C-MULTI-01), multi-company (C-MULTI-02),
  isolated config model (C-MULTI-04).
- **Phase 4 — Premium breadth (optional add-ons):** see below.

*(Phase labels are sequencing **inputs**, not a committed roadmap.)*

## Optional premium add-ons

Feature-flagged premium modules on the correct core (vision differentiation theme 5 —
*premium, not bloated*). Each still meets the full quality bar:

- **Payout reconciliation** (C-POUT-01/02) — EM-grade, Shopify-Payments-gated.
- **B2B (company accounts, VAT/VIES)** (C-ADV-02) — VT-demonstrated only.
- **Shopify Markets & Catalogs + per-market pricing** (C-ADV-01, C-PRICE-03).
- **POS order import** (C-ADV-03) — partly demonstrated (VT).
- **Gift cards** (C-ADV-04) — SH-only evidence.
- **Metafields (directional, per-entity)** (C-ADV-05) — EM/VT/SH-demonstrated; advanced.
- **Extended breadth** (abandoned-checkout→CRM, recommendations, Buy-with-Prime)
  (C-ADV-06) — SH-only evidence.

For each add-on:
- Category: optional add-on
- Why not MVP: premium breadth beyond the correctness core; several single-vendor.
- Evidence: mostly single-vendor B (VT-only B2B/POS-partial; SH-only gift cards/
  extended; EM/VT Markets; EM/VT/SH metafields).
- Risk of including too early: surface bloat; onboarding harm (A-UX-3); single-vendor
  overweighting (DP-003).
- What must be true before including: core shipped; feature-flag mechanism (AR-004)
  resolved; demonstrated demand; metafields also need AR-004/AR-005.

## Architecture-dependent later items

Items whose *later* inclusion is additionally gated on an AR decision (all "Not
decided / Evidence pending"):

- **Custom Python transforms** (within C-MAP-03) — Category: architecture-dependent
  (AR-004). Why not MVP: advanced power-user surface; MVP maps essential fields only.
  Evidence: VT [Demonstrated] (B). Risk early: unsafe/opaque transforms; support load.
  Before including: AR-004 extension model + a safe/sandboxed transform approach.
- **Isolated per-store config model** (C-MULTI-04) — Category: architecture-dependent
  (AR-004). Why not MVP: single-store MVP needs only a per-instance config. Evidence:
  VT tabbed config (C). Risk early: pulls the config data-model decision forward.
  Before including: AR-004 module/config boundaries.
- **Multi-store keys → full multi-store** (C-MULTI-01) — Category: architecture-
  dependent (AR-004/005). Why not MVP: MVP is single-store (keys stay multi-store-safe).
  Evidence: VT (B). Risk early: multi-store surface before the core is solid. Before
  including: AR-005 per-store binding keys proven at MVP; AR-004 boundaries.
- **Bulk operations** (C-JOB-06) — Category: architecture-dependent (AR-002). Why not
  MVP (open): may be needed for large backfills; otherwise machinery without value.
  Evidence: **[Fact]** Bulk Ops (no competitor describes it). Risk early: complexity for
  small stores. Before including: AR-002 API strategy + evidence that MVP backfill
  volumes need it (flagged, not silently dropped).

## Items blocked by weak evidence

Kept out (or down-weighted) because the evidence is **claim-only / single-vendor /
blocked** — not because the capability is unworthy (DP-003/DP-004):

- **pHash image dedup** (within C-VAR-02) — TQ **[Competitor claim]** only (403 docs).
  Blocked (weak evidence). Before including: a demonstrated, verifiable approach; MVP
  ships basic image sync without it.
- **Teqstars breadth** (idempotency/queue-retry/Markets/B2B/payouts as *claims*) —
  TQ docs 403 → **claims only**. Blocked (weak evidence). Before including: docs
  unblocked (R2) and capability demonstrated.
- **ecommerce_shopify capabilities** — no screenshots; export **not found**; webhooks
  **explicitly absent**; errors email-only. Blocked (weak evidence). Before including:
  demonstrated evidence (currently a floor/anti-pattern reference only).
- **sh_shopify_connector breadth** — captions only; multi-company **not-found**;
  idempotency/HMAC unstated. Weak evidence. Before including: demonstrated workflows.
- **Webkul multi-company** (within C-MULTI-02) — a **configuration field only** (➖,
  DP-004), **not** demonstrated support. Weak evidence. Before including: demonstrated
  record-rule isolation (the [Fact]-based mechanism) — and a multi-company decision.

## Items blocked by distribution decision

Gated on **AR-002 distribution (public App-Store vs custom/private)** — unresolved:

- **App-Store / Built-for-Shopify readiness & compliance** (C-DOCS-04) — Category:
  blocked (distribution). Why not MVP: only required (and only definable) if public/
  App-Store distribution is chosen. Evidence: **[Fact]** App-Store requirements (none
  verified across field). Risk early: building compliance for a distribution model
  that may not be chosen. Before including: AR-002 resolved to public/App-Store.
- **Public demo / marketplace packaging** (within C-DOCS-03) — Category: blocked
  (distribution). Why not MVP: packaging/demo hosting depends on distribution + the
  self-test scope. Evidence: TQ demo **[Competitor claim]**; O-TEST-1. Risk early:
  packaging churn. Before including: distribution + demo/docs hosting decided (MVP
  ships the **built-in self-test**, not a public marketplace demo).
- **OAuth-mandatory / GraphQL-only / billing & compliance webhooks** (mechanism within
  C-CONN-01) — Category: blocked (distribution). Why conditional: these become
  *mandatory* only under public/App-Store distribution. Before deciding: AR-002.

## Items blocked by Odoo edition / hosting constraints

- **Enterprise-only reporting** (within C-RPT-02, e.g. Net-Profit) — Category: blocked
  (edition). Why not MVP: features that require Odoo Enterprise must be **disclosed and
  gated**, not assumed (honesty non-negotiable). Before including: edition-gating
  strategy + disclosure.
- **Odoo Online / Odoo.sh feasibility of the queue/setup layer** (affects C-CONN-01/03,
  C-SYNC-*, C-JOB-*) — Category: blocked (hosting) / architecture-dependent (AR-003).
  Why relevant: VT's reliable stack requires `odoo.conf` edits (`server_wide_modules`,
  `queue_job` channels, ≥2 workers) and is **not installable on Odoo Online**; crons
  are **disabled on Odoo.sh staging** (**[Fact]**). Risk: an MVP setup that silently
  excludes Odoo Online, or relies on staging crons. Before including a mandatory
  server-config prerequisite: AR-003 confirms whether the queue/setup layer can avoid
  it (the manual-sync path C-SYNC-05 covers staging). *MVP intent: minimise/automate
  server-config prerequisites; keep the manual path always available.*

## What not to accidentally pull into MVP

Guardrails against silent scope creep (each would quietly break "small but excellent"):

1. **A second sync direction "for symmetry."** Import-first is deliberate; export
   (C-PROD-02/C-CUST-02) is a Phase-2 decision, not a freebie.
2. **"Just add refunds/payments while we're in orders."** Domain 9/11 depth is gated;
   only the **minimal** order-flow representation is in scope, and refunds must be
   idempotent if ever added.
3. **Auto-apply stock as if demonstrated.** C-INV-04 auto-apply is an **[Inference]**
   (DP-006) routed to AR-007 — do not implement it as a decided MVP behaviour.
4. **Multi-store/company because the model "could".** MVP is single-store; only the
   **keys** stay multi-store-safe (C-MULTI-01) — building multi-store UI/logic is out.
5. **A full mapping/transform engine.** MVP maps **essential fields only**; custom
   Python transforms (within C-MAP-03) are advanced/later.
6. **A reporting/analytics surface.** The command center covers MVP operational
   insight; dedicated analytics (C-RPT-01/02) is later.
7. **App-Store compliance / public demo packaging.** Blocked on distribution (AR-002);
   MVP ships the built-in self-test, not marketplace packaging.
8. **Premium breadth "since a competitor has it."** Markets/B2B/POS/gift cards/
   metafields (C-ADV-01…06) are optional add-ons, several single-vendor — not MVP.
9. **A specific queue framework / binding data model / API strategy.** These are gated
   (AR-002/003/005); MVP commits the requirement, never the mechanism (DP-005/DP-006).

## Open questions

1. **Direction** — is any second direction (product/customer export) in MVP, or firmly
   Phase 2? (mirrors [`./mvp-scope.md`](./mvp-scope.md) Q1)
2. **Domain 9 minimum** — the smallest payment/invoice/journal representation the order
   flow needs (everything else deferred).
3. **Refunds/cancellations** — basic idempotent refund (C-RET-01) / cancellation
   (C-RET-03) in MVP, or fully later?
4. **Distribution (AR-002)** — unblocks C-DOCS-04 + the OAuth/GraphQL/webhook
   conditionals.
5. **Odoo edition/hosting** — is Odoo Online support an MVP requirement (constrains the
   queue/setup layer, AR-003)? Which reports are edition-gated and how disclosed?
6. **Bulk ops (C-JOB-06)** — required for MVP backfill volumes, or defer?
7. **Feature-flag mechanism (AR-004)** — needed before any optional add-on; not an MVP
   decision.

## Review notes for ChatGPT

Please inspect carefully:

1. **Strictness** — is the boundary strict enough? Flag anything that should move from
   MVP (in [`./mvp-scope.md`](./mvp-scope.md)) to here, or vice-versa.
2. **The "open" direction items** — product/customer export, Domain 9 minimum, refunds/
   cancellations: these are the genuine scope forks for your call.
3. **Evidence discipline** — confirm weak/single-vendor/claim-only items (pHash, TQ
   breadth, SH/EC breadth, WK multi-company) are correctly **blocked/down-weighted**,
   not rejected-approach decisions (`CLAUDE.md` §10).
4. **Gating** — confirm distribution-blocked (C-DOCS-04) and edition/hosting-blocked
   items are correctly conditional, and that no AR decision is implied.
5. **"Don't pull into MVP" guardrails** — endorse them as the anti-bloat contract for
   the next sprints.

> **This document decides nothing.** All exclusions, phases, and add-on candidates are
> **inputs** for the gated RB-13 (MVP) and RB-14 (architecture) reviews, subject to
> ChatGPT approval (`CLAUDE.md` §4–§5, §8–§10). **Proposed for ChatGPT review — not
> final until accepted.**
