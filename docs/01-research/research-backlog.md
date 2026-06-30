# Research Backlog

> The structured, ordered backlog for the research phase. Each item carries:
> **ID · Objective · Inputs · Output file · Acceptance criteria · Dependencies ·
> Status.** Items are scoped to roughly one session each. **Nothing here
> authorises code, MVP finalization, or architecture decisions** — those remain
> gated (`CLAUDE.md` §5) and subject to ChatGPT review.
>
> **Status legend:** `Not started` · `Blocked (access)` · `In progress` ·
> `Done` · `Deferred`.
> IDs use `RB-NN` (section) and `RB-NN.x` (item within a section).

---

## 1. Source access and resource validation

### RB-01.1 — Validate and unblock initial sources
- **Objective:** Confirm access for all 8 registered resources; establish an
  unblock path for Blocked/Partial ones without bypassing auth.
- **Inputs:** `resource-inventory.md`; access results (2026-06-30).
- **Output file:** `docs/01-research/resource-inventory.md` (updated access +
  unblock notes).
- **Acceptance criteria:** Each source has a current access status; R2 Teqstars
  has a tested alternate-fetch decision (UA/browser/cache, or 16.0 fallback); R5
  Google Doc has an explicit access request/export decision; R4 VentorTech gated
  children identified.
- **Dependencies:** None.
- **Status:** Blocked (access) — R2 and R5 need an unblock step.

## 2. Competitor deep-dives

> One file per competitor, using `research-methodology.md` §11 and the fixed
> feature taxonomy (RB-12). Each is one scoped session.

### RB-02.1 — Webkul deep dive
- **Objective:** Cited feature/sync/UX/pricing profile of the Webkul connector.
- **Inputs:** R1; methodology §5–§11.
- **Output file:** `docs/01-research/02-webkul.md`
- **Acceptance criteria:** Taxonomy covered; every claim cited + classified;
  excerpts captured to `00-source-materials/webkul/`; pricing resolved or logged
  as open question; strengths/weaknesses/gaps marked inference.
- **Dependencies:** RB-01.1; RB-12 (taxonomy) preferred.
- **Status:** Not started.

### RB-02.2 — Teqstars deep dive
- **Objective:** Cited profile of the Teqstars connector across its doc tree.
- **Inputs:** R2; methodology.
- **Output file:** `docs/01-research/03-teqstars.md`
- **Acceptance criteria:** As RB-02.1; doc-tree (setup, product/order/customer)
  covered.
- **Dependencies:** RB-01.1 (must unblock R2 first).
- **Status:** Blocked (access).

### RB-02.3 — Emipro deep dive
- **Objective:** Cited profile of the Emipro connector via its doc hub.
- **Inputs:** R3; methodology.
- **Output file:** `docs/01-research/04-emipro.md`
- **Acceptance criteria:** As RB-02.1; nav-hub sub-pages (webhooks, metafields,
  payouts) covered.
- **Dependencies:** RB-01.1.
- **Status:** Not started.

### RB-02.4 — VentorTech deep dive (docs + website)
- **Objective:** Cited profile of the VentorTech connector.
- **Inputs:** R4 (Confluence) + R7 (website); methodology.
- **Output file:** `docs/01-research/05-ventortech.md`
- **Acceptance criteria:** As RB-02.1; gated Confluence content flagged, not
  bypassed; website pricing (EUR 499) and sync-direction claims captured.
- **Dependencies:** RB-01.1.
- **Status:** Not started (R4 partial).

### RB-02.5 — Odoo Apps listings deep dive (ecommerce_shopify + sh_shopify_connector)
- **Objective:** Cited profiles + pricing/license + provenance check.
- **Inputs:** R6, R8; methodology.
- **Output file:** `docs/01-research/06-odoo-apps.md`
- **Acceptance criteria:** As RB-02.1; pricing/license recorded as on-page facts
  ($195.56 / $168.81, OPL-1); R6 official-vs-partner provenance resolved or
  logged as open question; ratings/version history captured.
- **Dependencies:** RB-01.1.
- **Status:** Not started.

### RB-02.6 — Project Google Doc review (conditional)
- **Objective:** If access is granted, extract relevant content; else keep
  blocked and document the gap.
- **Inputs:** R5.
- **Output file:** `docs/01-research/07-google-doc.md`
- **Acceptance criteria:** Either a cited extraction, or an explicit "still
  blocked" record with the access action needed.
- **Dependencies:** RB-01.1 (owner-granted access/export).
- **Status:** Blocked (access).

## 3. Competitor feature matrix

### RB-03.1 — Build cross-competitor feature matrix
- **Objective:** Single matrix (rows = taxonomy features, columns = competitors)
  with presence/depth and a source citation per cell.
- **Inputs:** All RB-02 deep dives; RB-12 taxonomy.
- **Output file:** `docs/01-research/competitor-feature-matrix.md`
- **Acceptance criteria:** Every cell cites its source deep-dive; claim vs
  demonstrated distinguished; gaps visible; no MVP conclusions drawn here.
- **Dependencies:** RB-02.*, RB-12.
- **Status:** Not started.

## 4. UX/UI benchmark

### RB-04.1 — UX/UI benchmark across competitors
- **Objective:** Compare onboarding/config and operational UX; identify
  best-in-class patterns and friction.
- **Inputs:** RB-02 deep dives; screenshots in `00-source-materials/`.
- **Output file:** `docs/01-research/ux-benchmark.md`
- **Acceptance criteria:** Flows documented per methodology §8; observation vs
  UX judgement separated; screenshot sources cited.
- **Dependencies:** RB-02.* (enough deep dives with captured UX).
- **Status:** Not started.

## 5. Shopify official API notes

### RB-05.1 — Official Shopify API & app-requirement notes
- **Objective:** Tier-1 facts: Admin REST vs GraphQL, webhooks, OAuth scopes,
  versioning/deprecation, rate limits, bulk ops, idempotency, app review.
- **Inputs:** Official Shopify developer documentation.
- **Output file:** `docs/01-research/shopify-api-notes.md`
- **Acceptance criteria:** Every claim cites an official doc + the API version
  it applies to; an explicit "architecture constraints/implications" section
  (marked inference); open questions listed.
- **Dependencies:** None (can run in parallel with deep dives).
- **Status:** Not started.

## 6. Odoo official architecture notes

### RB-06.1 — Official Odoo 19 architecture notes
- **Objective:** Tier-1 facts on extension points/modularity: sale/stock/
  product/account/delivery, ir.cron & queue/async patterns, external IDs/
  mapping, ORM/performance, security/access rules, addon structure.
- **Inputs:** Official Odoo 19 developer documentation.
- **Output file:** `docs/01-research/odoo-architecture-notes.md`
- **Acceptance criteria:** Every claim cites an official doc + Odoo version;
  recommended extension points & modularity boundaries (marked inference); open
  questions listed.
- **Dependencies:** None.
- **Status:** Not started.

## 7. Common patterns

### RB-07.1 — Common patterns across competitors
- **Objective:** Identify recurring approaches (sync models, mapping, scheduling,
  error handling) shared across the market.
- **Inputs:** RB-03 matrix; RB-05/RB-06 notes.
- **Output file:** `docs/01-research/common-patterns.md`
- **Acceptance criteria:** Patterns evidenced by ≥2 competitors and cited;
  classified (fact/claim/inference).
- **Dependencies:** RB-03, RB-05, RB-06.
- **Status:** Not started.

## 8. Best-in-class observations

### RB-08.1 — Best-in-class observations
- **Objective:** Identify the strongest approaches worth emulating and why.
- **Inputs:** RB-03 matrix; RB-04 UX benchmark; RB-07 patterns.
- **Output file:** `docs/01-research/best-in-class.md`
- **Acceptance criteria:** Each "best-in-class" claim cites the source and
  states the quality bar it sets; marked as inference/recommendation.
- **Dependencies:** RB-03, RB-04, RB-07.
- **Status:** Not started.

## 9. Gaps and opportunities

### RB-09.1 — Gaps and opportunities analysis
- **Objective:** Identify market gaps, weaknesses, and differentiation
  opportunities for a premium connector.
- **Inputs:** RB-03, RB-04, RB-07, RB-08; RB-05/RB-06 constraints.
- **Output file:** `docs/01-research/gaps-and-opportunities.md`
- **Acceptance criteria:** Each gap tied to evidence; opportunities marked as
  recommendations; feasibility flagged against Tier-1 constraints.
- **Dependencies:** RB-03, RB-04, RB-07, RB-08.
- **Status:** Not started.

## 10. Avoid-list

### RB-10.1 — Avoid-list (anti-patterns)
- **Objective:** Patterns/approaches we deliberately will not copy.
- **Inputs:** RB-07, RB-08, RB-09; reliability/technical-risk findings.
- **Output file:** `docs/01-research/avoid-list.md` (and seed
  `docs/05-qa/rejected-approaches-log.md`).
- **Acceptance criteria:** Each avoid item has a reason + evidence + a revisit
  condition; mirrored into the rejected-approaches log.
- **Dependencies:** RB-07, RB-08, RB-09.
- **Status:** Not started.

## 11. Product vision

### RB-11.1 — Product vision draft
- **Objective:** Articulate the product's premium positioning, target users, and
  value proposition.
- **Inputs:** RB-08, RB-09, RB-10.
- **Output file:** `docs/02-product/product-vision.md`
- **Acceptance criteria:** Vision is evidence-grounded; explicitly labelled as a
  draft recommendation pending ChatGPT review; no scope lock-in.
- **Dependencies:** RB-08, RB-09, RB-10.
- **Status:** Not started.

## 12. Feature taxonomy

### RB-12.1 — Canonical feature taxonomy
- **Objective:** A stable, shared taxonomy of connector capabilities used by
  deep dives and the matrix.
- **Inputs:** Methodology §7; first 1–2 deep dives for grounding.
- **Output file:** `docs/02-product/feature-taxonomy.md`
- **Acceptance criteria:** Mutually exclusive, exhaustive categories; stable IDs
  for matrix columns/rows; reviewed before the matrix is built.
- **Dependencies:** A first deep dive (RB-02.x) for grounding.
- **Status:** Not started.

## 13. MVP scope

### RB-13.1 — MVP scope implications (not finalized)
- **Objective:** Translate findings into MVP **implications and candidates** —
  not a locked scope.
- **Inputs:** RB-09, RB-11, RB-12, RB-03; dispositions (methodology §12).
- **Output file:** `docs/02-product/mvp-scope.md`
- **Acceptance criteria:** Each candidate tied to evidence + disposition;
  explicitly marked "not finalized — pending ChatGPT review"; open questions
  listed.
- **Dependencies:** RB-03, RB-09, RB-11, RB-12.
- **Status:** Not started.

## 14. Architecture preparation

### RB-14.1 — Architecture preparation (pre-decision)
- **Objective:** Frame the first architecture questions and candidate approaches
  (sync orchestration, mapping/idempotency, scheduling/queueing, modularity) —
  **no decisions**.
- **Inputs:** RB-05, RB-06, RB-13; reliability/technical-risk findings.
- **Output file:** `docs/03-architecture/architecture-preparation.md`
- **Acceptance criteria:** Questions and candidate approaches logged in
  `docs/05-qa/architecture-review-log.md` as Proposed; no ADRs created;
  evidence-required noted per candidate.
- **Dependencies:** RB-05, RB-06, RB-13.
- **Status:** Not started.

---

## Suggested sequencing

`RB-01` → competitor deep-dives `RB-02.*` (+ `RB-12` taxonomy early, and
`RB-05`/`RB-06` official notes in parallel) → `RB-03` matrix → `RB-04` UX →
`RB-07` patterns → `RB-08` best-in-class → `RB-09` gaps → `RB-10` avoid-list →
`RB-11` vision → `RB-13` MVP implications → `RB-14` architecture preparation.
Blocked items (R2 Teqstars, R5 Google Doc) are revisited once unblocked and do
not stall the rest.
