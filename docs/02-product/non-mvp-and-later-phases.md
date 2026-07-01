# Non-MVP and Later-Phase Candidates

> The **strict boundary** companion to [`./mvp-scope.md`](./mvp-scope.md). It records
> what is **deliberately kept out of the first release**, why, and what must be true
> before each item is reconsidered — so the MVP stays *small but excellent* and does
> not silently bloat. Every item here is an **input**, not a decision.

## Status

> **Accepted MVP boundary (ChatGPT RB-13, DEC-003, 2026-07-01 — PR #55-corrected) —
> architecture still gated.** The MVP *product scope* is accepted; the items below are the
> **accepted non-MVP boundary** (deferred/excluded from the first release), each with a
> revisit condition. Authored in Sprint F; boundary confirmed in Sprint G. See
> [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md).

> **PR #55 revision (2026-07-01).** Product export is **no longer** in the non-MVP set:
> **controlled product export/update is IN MVP** (matched, bound, previewed,
> draft/unpublished/channel-controlled). What this document keeps out is **unrestricted
> autonomous bidirectional catalog ownership** (all-field two-way conflict resolution,
> field-ownership matrix, advanced publish/channel campaign management) and **customer
> export**. TeqStars docs were re-checked accessible on 2026-07-01 (full rebaseline pending
> a later sprint).

- **Sprint:** authored Product Sprint F (RB-13); **boundary accepted** Product Sprint G
  (RB-13, DEC-003). **Phase:** MVP scope only — **no-code gate in force** (`CLAUDE.md`
  §4–§5).
- **Governance:** deferral/exclusion here is a **product-scope boundary decision**, **not**
  a rejected-approach decision (`CLAUDE.md` §10 — formal architecture rejection still
  routes through architecture review). **No architecture, no architecture ADR, no module
  boundary, no data model, no queue framework, no API strategy, and no distribution model
  is decided.**
- **Evidence discipline (DP-003/DP-004/DP-006):** competitor claims stay claims; a
  config field is not demonstrated support; a market promise is not demonstrated
  bidirectionality; improvement opportunities are inference; conditional items stay
  conditional.
- **Dates:** competitor evidence access **2026-06-30**; session **2026-07-01**. No new
  sources crawled.

## Purpose

Make the MVP boundary **explicit and defensible**. A premium MVP fails not only by
missing correctness, but by **over-scoping** — pulling in **unrestricted autonomous
bidirectional catalog ownership**, financial depth, premium breadth, and multi-tenancy
that each multiply complexity and fragility. (It equally fails by **under-scoping** the
market-baseline product path — so **controlled** product export/update **is in MVP**.)
This document names those items, ties each to its evidence and its
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

1. **It is an unneeded breadth surface or unrestricted second-direction complexity** the
   correctness core does not need — **unrestricted autonomous bidirectional catalog
   ownership** (all-field two-way conflict resolution, field-ownership matrix, advanced
   publish/channel campaign management), customer export, pricelists, Markets/B2B/POS/gift
   cards/metafields, extended breadth. *(**Controlled** product export/update — matched,
   bound, previewed, draft/channel-safe — **is in MVP**, per DEC-003 / PR #55.)*
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

**Full autonomous bidirectional catalog management**
- Capability ID(s): C-PROD-02/03 (beyond controlled export), plus C-PRICE-02/03,
  C-VAR-03, C-ADV-05 (metafields), C-MAP-03 (transforms)
- Category: later / architecture-dependent
- Why not MVP: **unrestricted, autonomous two-way catalog ownership** requires
  **automatic all-field conflict resolution**, a **complex field-ownership matrix**,
  **advanced publish/channel campaign management**, and catalog breadth
  (Markets/pricelist/metafields/SEO) — plus hardened destructive-write safety at scale.
  That multiplies complexity/fragility well beyond what a first excellent MVP needs.
- **In MVP instead (controlled):** MVP includes only **controlled product export/update**
  — **selected** products, **preview** before create/update/export, **matching + binding**
  first, **draft/unpublished/explicit-sales-channel** safe publication, and **no
  destructive/full-state write without preview/dry-run** (**[Fact]** `productSet`
  delete-on-omit, A-IMP-1). See [`./mvp-scope.md`](./mvp-scope.md) *Product onboarding and
  duplicate-prevention baseline*.
- Evidence: product import/export/update is **market-baseline** — VT/EM/WK/SH
  [Demonstrated] (B); TeqStars docs re-checked accessible 2026-07-01 (reinforcing, full
  rebaseline pending).
- Risk of including too early: two-way conflict/ownership edge cases, field-ownership
  ambiguity, and destructive-apply blast radius before the controlled core is proven.
- What must be true before including: controlled export/update shipped and proven; AR-002
  (API/destructive-apply) + AR-005 (binding/conflict model) resolved; a field-ownership +
  conflict-resolution design reviewed and accepted.

**Customer export (Odoo → Shopify)**
- Capability ID(s): C-CUST-02
- Category: later / architecture-dependent — **RB-13: DEFERRED from MVP** (Phase 2)
- Why not MVP: a second-direction customer flow not required by the controlled
  product-onboarding MVP; WK/EC are import-only (DP-004) — not demonstrated export.
- Evidence: EM link-by-email [Demonstrated] (B).
- Risk of including too early: duplicate/ownership conflicts across systems; binding model
  pulled forward.
- What must be true before including: AR-005 binding + dedup keys resolved; ChatGPT wants
  Odoo-authored customers pushed to Shopify.

**Full payment / invoice / gateway accounting automation (beyond the minimal order-flow representation)**
- Capability ID(s): C-PAY-01, C-PAY-02, C-PAY-03 (accounting-automation portion)
- Category: later — **RB-13: MVP keeps ONLY minimal financial evidence; accounting
  automation DEFERRED**
- Why not MVP: MVP preserves financial *evidence* (Shopify financial/payment status,
  gateway/method label, transaction reference(s), paid/unpaid/refunded flags as source
  info, totals/taxes/shipping/discounts/currency, basic gateway/journal mapping as config
  input). **Deferred:** automatic posted invoices, automatic posted payments, bank
  reconciliation, payout reconciliation, full accounting workflow, gateway-specific
  accounting depth, automatic refund accounting, automatic payment posting on retry — a
  large, edition-sensitive surface beyond a correct, actionable order import.
- Evidence: VT/SH invoice, EM multi-payment, SH+VT gateway→journal [Demonstrated] (B);
  `OrderTransaction` ledger [Fact].
- Risk of including too early: heavy accounting surface, edition gating, double-invoice
  if not idempotent.
- What must be true before including: the deferred accounting automation becomes a
  Phase-2/3 accounting module, all of it **idempotent** (C-JOB-04). **Exception:** if RB-14
  finds a **draft** invoice/payment artifact is *absolutely required* for a valid Odoo
  order flow, it is **architecture-dependent** and returns to ChatGPT before implementation
  — no silent automatic invoice/payment creation.

**Refund sync / returns lifecycle / cancellations**
- Capability ID(s): C-RET-01, C-RET-02, C-RET-03
- Category: later / architecture-dependent (AR-006) — **RB-13: DEFERRED from MVP**
  (refund sync, cancellation reflection, and returns/RMA all deferred)
- Why not MVP: "advanced refunds/returns lifecycle" is explicitly non-MVP; refunds tie
  to the deferred Domain 9 minimum; RMA (C-RET-02) is scarce even among competitors.
- Evidence: **[Fact]** `@idempotent` refunds 2026-04 + EM/VT/SH [Demonstrated] (A/B);
  returns API [Fact]; `returnRefund` deprecated → `returnProcess`.
- Risk of including too early: **double-refund** if not idempotent (A-PAY-2);
  irreversible-action footguns (A-RET-2) without strong guards.
- What must be true before including: **idempotency mandatory** — the **idempotent-refund
  / no-double-refund** regression is a **mandatory** acceptance principle for the first
  refund/refund-sync sprint (carried forward from RB-13, never dropped); AR-006 taxonomy
  resolved; irreversible-action warnings + "never silently create a cancel order"
  (C-RET-03).

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

- **Phase 2 — Full autonomous bidirectional catalog + customer export:** unrestricted
  two-way catalog ownership (all-field conflict resolution, field-ownership matrix,
  advanced publish/channel management, beyond controlled C-PROD-02/03), and customer
  export C-CUST-02 (the "Option B" surface from [`./mvp-scope.md`](./mvp-scope.md)).
  *(**Controlled** product export/update C-PROD-02/03/05 is **in MVP**, not Phase 2.)*
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
- **Full multi-store & multi-company** (C-MULTI-01 full multi-store; C-MULTI-02
  multi-company) — Category: architecture-dependent (AR-004/005). **RB-13: OUT of MVP —
  single-store, single-company MVP accepted;** no multi-store UI/logic and no
  multi-company logic. Only the **keys** stay multi-store-safe (architecture-safe
  preparation, not a feature); Webkul's default Company field is **not** multi-company
  evidence (DP-004). Evidence: VT (B) multi-store; EM/VT + Odoo record rules [Fact]
  multi-company. Risk early: multi-tenancy surface before the core is solid. Before
  including: core loop shipped; AR-005 per-store binding keys proven at MVP; AR-004
  boundaries; demonstrated record-rule isolation + a multi-company decision.
- **Bulk operations** (C-JOB-06) — Category: architecture-dependent (AR-002). **RB-13:
  NOT a user-facing MVP feature** — "bulk operation management" is not exposed as an MVP
  feature. Why: machinery without user-facing value for a small-store MVP. Evidence:
  **[Fact]** Bulk Ops (no competitor describes it). Risk early: complexity for small
  stores. **Internal-mechanism note:** RB-14 (AR-002) must assess whether Bulk Operations
  are required **internally** for safe/resumable large backfills; if so, that is an
  **architecture mechanism, not a product-scope expansion** (it does not change the MVP
  boundary).

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
  blocked (distribution) — **RB-13: OUT of MVP** (public App-Store packaging, public
  marketplace demo packaging, and app billing/compliance webhook work are excluded
  unless distribution is later decided). Why not MVP: only required (and only definable)
  if public/App-Store distribution is chosen. Evidence: **[Fact]** App-Store
  requirements (none verified across field). Risk early: building compliance for a
  distribution model that may not be chosen. Before including: AR-002 resolved to
  public/App-Store.
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

1. **Unrestricted two-way catalog ownership "for symmetry."** MVP does **controlled**
   product export/update (matched, bound, previewed, draft/channel-safe); **automatic
   all-field two-way conflict resolution, a field-ownership matrix, and advanced
   publish/channel campaign management are Phase-2+**, not a freebie. **Customer export**
   (C-CUST-02) is also Phase 2.
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

**Resolved at RB-13 (DEC-003, 2026-07-01):**

1. ~~**Direction**~~ — **RESOLVED (PR #55): controlled bidirectional product onboarding
   in MVP** (product import **and** controlled product export/update). **Customer export**
   and **unrestricted autonomous bidirectional catalog ownership** are firmly Phase 2+.
2. ~~**Domain 9 minimum**~~ — **RESOLVED: minimal financial evidence only** on the
   imported order; all accounting automation deferred.
3. ~~**Refunds/cancellations**~~ — **RESOLVED: deferred** (idempotent-refund regression
   mandatory if later included).
4. ~~**Bulk ops (C-JOB-06)**~~ — **RESOLVED: not a user-facing MVP feature;** RB-14/AR-002
   internal-only assessment.

**Still open — routed to RB-14 architecture:**

5. **Distribution (AR-002)** — unblocks C-DOCS-04 + the OAuth/GraphQL/webhook
   conditionals + any **internal** bulk-ops need.
6. **Odoo edition/hosting** — is Odoo Online support an MVP requirement (constrains the
   queue/setup layer, AR-003)? Which reports are edition-gated and how disclosed?
7. **Feature-flag mechanism (AR-004)** — needed before any optional add-on; not an MVP
   decision.

## Review notes for ChatGPT

Please inspect carefully:

1. **Strictness** — is the boundary strict enough? Flag anything that should move from
   MVP (in [`./mvp-scope.md`](./mvp-scope.md)) to here, or vice-versa.
2. **The resolved direction (PR #55)** — confirm **controlled product export/update is IN
   MVP** (matched, bound, previewed, draft/channel-safe) while **unrestricted autonomous
   bidirectional catalog ownership** and **customer export** stay Phase 2+; Domain 9
   minimal-evidence-only; refunds/cancellations deferred.
3. **Evidence discipline** — confirm controlled product export/update rests on **EM/VT/WK/
   SH-demonstrated** evidence (market-baseline); weak/single-vendor/claim-only items
   (pHash, SH/EC breadth, WK multi-company) stay **blocked/down-weighted**; the **TeqStars
   re-check (2026-07-01 accessible)** is noted but the **full rebaseline is pending a later
   sprint** — not rejected-approach decisions (`CLAUDE.md` §10).
4. **Gating** — confirm distribution-blocked (C-DOCS-04) and edition/hosting-blocked
   items are correctly conditional, and that no AR decision is implied.
5. **"Don't pull into MVP" guardrails** — endorse them as the anti-bloat contract for
   the next sprints.

> **The MVP boundary is accepted (ChatGPT RB-13, DEC-003).** Deferrals/exclusions above
> are the accepted **product-scope** boundary with revisit conditions; they are **not**
> rejected-approach decisions and **not** technical debt. Phase labels and add-on
> candidates remain **inputs** for the gated RB-14 (architecture) review, subject to
> ChatGPT approval (`CLAUDE.md` §4–§5, §8–§10). **MVP boundary accepted; architecture
> still gated; implementation blocked.**
