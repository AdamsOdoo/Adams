# MVP Scope — Accepted Baseline

> The **accepted MVP scope baseline** (ChatGPT RB-13, 2026-07-01, DEC-003) for the
> premium Odoo 19 ↔ Shopify Connector — authored in Sprint F as an evidence-based
> proposal and accepted in Sprint G. It answers *what belongs in the first excellent
> MVP, what stays out,
> which items are MVP-critical for correctness/reliability/UX/trust, which are
> tempting-but-too-risky, and which depend on unresolved architecture decisions* —
> grounded only in already-merged repo evidence. Companion docs:
> [`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md) (boundaries) and
> [`./user-stories.md`](./user-stories.md) (the MVP experience).

## Status

> **Accepted MVP baseline by ChatGPT (RB-13) on 2026-07-01 — architecture still
> gated.** The MVP *product scope* below is now the **accepted baseline**; see
> [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md) and the
> **ChatGPT RB-13 acceptance** section immediately below. The document was authored in
> Sprint F as a proposal; Product Sprint G records ChatGPT's acceptance and resolves the
> open direction forks. **No architecture is decided.**

- **Sprint:** authored Product Sprint F (RB-13 — MVP scope proposal); **accepted**
  Product Sprint G (RB-13 — MVP scope acceptance, DEC-003). **Phase:** product/MVP scope
  only — **no-code gate in force** (`CLAUDE.md` §4–§5). The MVP *scope* is accepted; the
  *mechanism* of every architecture-sensitive item is **not** decided.
- **Governance:** **MVP product scope is finalized** (ChatGPT RB-13, DEC-003), but
  **no architecture is decided** (RB-14 / AR-002…AR-008, all "Not decided / Evidence
  pending"), **no architecture ADRs, no module names/boundaries, no data models, no
  queue framework, no REST-vs-GraphQL choice, no distribution model, no implementation
  plan.** Implementation remains blocked until RB-14 and later planning are approved.
- **Evidence-consistency gate (DP-006, escalated 3rd-occurrence):** every proposed
  inclusion is checked against evidence strength, conditionality, and competitor
  coverage before it enters this proposal (see *Evidence-consistency review*).
  Competitor claims stay **claims**; a configuration field is **not** demonstrated
  support (DP-004); a market promise is **not** demonstrated bidirectionality; an
  improvement opportunity is **inference**, not demonstrated competitor capability;
  conditional platform requirements stay **conditional**.
- **Dates:** competitor evidence access date **2026-06-30** (Sprint C); session date
  **2026-07-01**. **No new sources were crawled** for this sprint.
- **Claim labels:** **[Fact]** (Tier-1 Shopify/Odoo official), **[Demonstrated]**
  (a specific competitor workflow/screenshot/dated release note), **[Competitor
  claim]**, **[Inference]**, **[Recommendation]**, **[Open question]**.

> **Sprint C2 evidence note (2026-07-01) — reinforces the accepted baseline; no scope
> change.** A later research sprint (**Research Sprint C2**) rebaselined the **TeqStars**
> competitor evidence after its docs — 403-blocked in Sprint C — became accessible. The
> now-demonstrated TeqStars docs **reinforce the already-accepted controlled product
> import/export/update MVP baseline**: TeqStars shows **controlled, draft-safe product
> onboarding** (SKU/Barcode/both match key, Create-Odoo-Products guard, export with
> Sales-Channels-optional = unpublished, Publish/Unpublish, a per-listing Allowed/
> Not-Allowed-Sync switch), and — consistent with DEC-003 — **customer export is not
> offered (import-only)**, so the "customer export = later" deferral is corroborated,
> **not** contradicted. This is a **[Demonstrated]** upgrade of a competitor whose
> evidence was previously [Competitor claim]-only; **it changes no MVP inclusion and does
> not amend DEC-003.** TeqStars' asserted-but-unshown reliability items (explicit
> idempotency, automatic retry, first-class reconciliation, rate-limit throttling, HMAC)
> remain **not demonstrated** (➖/⬜) and are **not** treated as MVP evidence. See
> `../01-research/competitor-deep-dives.md` (TeqStars) and `../05-qa/defect-pattern-log.md`
> (Sprint C2 note). **No serious contradiction to DEC-003 was found; no open review note
> for ChatGPT is required.**

## ChatGPT RB-13 acceptance

> **Accepted MVP scope baseline — ChatGPT, 2026-07-01 (DEC-003), revised same day after
> the PR #55 review.** These decisions resolve the Sprint F **open** direction forks and
> are now the accepted **product scope**. Architecture remains gated (RB-14 /
> AR-002…AR-008); every *mechanism* stays **Architecture-dependent** (see
> *Architecture-dependent MVP items*). This section governs where it clarifies a
> per-domain block below.

> **PR #55 revision (2026-07-01) — product direction correction.** The first draft
> over-deferred product export. **Corrected:** MVP includes **controlled bidirectional
> product onboarding and basic product sync** (product import **and** controlled product
> export/update, with matching, binding, preview, and draft/unpublished/channel-controlled
> safety). What stays deferred is **unrestricted autonomous bidirectional catalog
> ownership**. **Customer export remains deferred.** Product import/export/update is a
> **market-baseline** capability (EM/VT/WK/SH demonstrated), not a Phase-2 luxury.

**Accepted MVP option — Option A (correctness core, with controlled bidirectional product
onboarding).** A small but excellent MVP is a **correct, observable, recoverable
single-store sync loop** across the core commerce objects, including **controlled
bidirectional product onboarding** (safe product import **and** export/update) — **not
unrestricted autonomous bidirectional catalog ownership**.

**Accepted primary direction.**
- **Shopify → Odoo (import):** product import; variant/options import; basic image/media
  import; base price / compare-at import; customer import and matching; order import;
  order status / basic lifecycle representation.
- **Odoo → Shopify (controlled product export/update):** product export; product update;
  basic image/media update/export (where feasible); base price / compare-at update/export
  (where feasible) — with matching, binding, preview, and draft/unpublished/channel-
  controlled safety (see *Product onboarding and duplicate-prevention baseline*).
- **Odoo → Shopify (write-back):** inventory write-back (multi-location-aware,
  idempotent); fulfillment and tracking write-back.
- **Deferred from MVP:** **unrestricted autonomous bidirectional catalog ownership**
  (all-field two-way conflict resolution; complex field-ownership matrix; advanced
  publish/channel campaign management; Markets/pricelists/metafields/SEO/custom-transforms/
  full-multi-store catalog breadth); **customer export**.

**Accepted resolutions of the Sprint F open items:**
- **Product export/update (C-PROD-02/03/05)** — **controlled product export/update
  ACCEPTED in MVP** (corrected from the first draft's defer). MVP exports/updates
  **selected** products via a **previewed, draft/unpublished/channel-controlled** flow;
  destructive-apply safety (C-PROD-05) is **mandatory** for this path; matching + binding
  precede any create/update. **Unrestricted autonomous bidirectional catalog ownership**
  stays deferred (Phase 2+).
- **Customer export (C-CUST-02)** — **deferred** (was open). Phase 2.
- **Domain 9 financial/payment (C-PAY-01/02/03)** — **include minimal financial
  representation only** (was open): preserve Shopify financial status, payment status,
  gateway/method label, transaction reference(s), paid/unpaid/refunded flags (as source
  info), totals, taxes, shipping, discounts, currency, and basic gateway/journal mapping
  as configuration input if needed for classification/routing. **Excluded:** automatic
  posted invoices/payments, bank/payout reconciliation, full accounting workflow,
  gateway-specific accounting depth, automatic refund accounting, automatic payment
  posting on retry. **Rule:** *MVP preserves financial evidence and order actionability;
  it does not automate accounting.* If RB-14 finds a draft invoice/payment artifact is
  absolutely required for a valid Odoo order flow, that is **architecture-dependent** and
  returns to ChatGPT before implementation (do not silently add auto invoice/payment).
- **Refund sync (C-RET-01) / cancellation reflection (C-RET-03) / returns-RMA (C-RET-02)**
  — **deferred** (were open/later). **Mandatory future rule:** if refund handling is
  later included, the **idempotent-refund / no-double-refund** regression is mandatory.
- **Bulk operations (C-JOB-06)** — **not a user-facing MVP feature** (was open). RB-14
  (AR-002) may assess whether Bulk Operations are needed **internally** for safe/resumable
  backfills — an **architecture mechanism, not a product-scope expansion**.
- **Store/company scope** — **single-store, single-company MVP accepted**; no multi-store
  UI/logic and no multi-company logic in MVP, but **architecture-safe**: binding keys must
  not block future multi-store, configuration assumptions must not make it impossible, and
  Webkul's default Company field is **not** multi-company evidence (DP-004).
- **Primary MVP persona** — **P1 (operations/e-commerce user) primary; P2 (Odoo admin /
  implementation consultant) secondary.** P3/P4 remain important buyer/deployer personas,
  but MVP UX priority serves P1 daily operation and P2 setup/configuration first.

**Accepted MVP UX/reliability/inventory scope** (unchanged from the proposal, now
accepted): layered sync (webhooks + scheduled + manual + reconciliation); HMAC
verification; webhook-ID dedup; fast webhook ack; idempotency keys / idempotent writes;
duplicate prevention; per-record failure isolation; reason-coded logs; safe manual retry;
retry classification concept; rate-limit/cost awareness; resumable jobs; honest freshness;
guided setup + credential masking + test connection + readiness self-test; basic command
center with health indicators + activity/failure counts; recovery-first error center (MVP
version) with quick actions that enqueue work; essential mappings only; role-based access
(admin vs functional); open docs + dated changelog + built-in self-test; inventory
write-back that is multi-location-aware, **never writes `committed`**, writes only allowed
Shopify quantity fields, imports initial Shopify stock under a **controlled/reviewed**
apply — with **auto-apply NOT accepted as default MVP behaviour** (remains AR-007-dependent,
an [Inference], DP-006).

**Still gated (not decided here):** distribution/API strategy (AR-002), sync
orchestration/queue framework (AR-003), module boundaries/config model (AR-004),
binding/dedup data model (AR-005), error/retry taxonomy (AR-006), inventory design incl.
apply mode (AR-007), fulfilment design (AR-008), and any implementation plan.

## Product onboarding and duplicate-prevention baseline

> **Accepted MVP requirement (ChatGPT RB-13, DEC-003 — PR #55 correction).** Because MVP
> now does **controlled bidirectional product onboarding** (import **and** export/update),
> the product path must be **safe by construction**: it never blindly creates or
> destructively writes. Every mechanism below is **product-level intent**; the *how*
> (binding data model AR-005; API / destructive-apply mechanics AR-002) stays
> **Architecture-dependent — must be resolved in RB-14 before implementation.**

- **First-sync matching wizard** — before creating any records, classify each product/
  variant as one of:
  - **matched by existing binding** (Shopify ID ↔ Odoo record already linked),
  - **matched by SKU / internal reference**,
  - **matched by barcode**,
  - **only in Shopify**,
  - **only in Odoo**,
  - **duplicate SKU/barcode conflict → manual review required**.
- **Explicit first-sync source strategy** — the operator chooses: **Shopify is source**,
  **Odoo is source**, or **both systems already have products → match first**.
- **No blind create** — a **preview** precedes every create/update/export.
- **No name-only automatic matching** — names are never a sole automatic match key;
  ambiguous matches require **manual review**.
- **Binding created after confirmation** — the Shopify product/variant ID ↔ Odoo
  product/template/variant binding is written only once the match is confirmed.
- **Draft / unpublished / channel-controlled export safety** — Odoo→Shopify export can
  create **drafts** / stay unpublished / respect explicit sales-channel selection (export
  without publishing when no sales channel is selected).
- **Preview / dry-run before any destructive or full-state write** (**[Fact]** `productSet`
  delete-on-omit, A-IMP-1) — mandatory guardrail; mechanism architecture-gated (AR-002).

## Purpose

Convert the vision's "MVP inputs, not decisions"
([`./product-vision.md`](./product-vision.md)), the canonical capability model
([`./feature-taxonomy.md`](./feature-taxonomy.md),
[`./capability-evidence-map.md`](./capability-evidence-map.md)), and the setup/UX
principles ([`./setup-ux-principles.md`](./setup-ux-principles.md)) into a **single,
defensible, reviewable MVP scope proposal** — small but excellent — that ChatGPT can
accept, revise, or reject, and that RB-14 (architecture) can build against without
re-deriving scope. It does **not** author screens, modules, or decisions.

## Evidence base

Already-merged repo evidence only (no new research):

- **Canonical capability model (Sprint D):** [`./feature-taxonomy.md`](./feature-taxonomy.md),
  [`./capability-evidence-map.md`](./capability-evidence-map.md) — the source of
  every `C-…` ID, its evidence strength (A–E), competitor coverage, platform
  dependency, and AR mapping used below.
- **Product strategy (Sprint E):** [`./product-vision.md`](./product-vision.md)
  (thesis, personas, non-negotiables, MVP/later/architecture inputs),
  [`./setup-ux-principles.md`](./setup-ux-principles.md) (UX north star + 12
  principles).
- **Research baseline (Sprint C):** [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
  (`O-…` opportunities), [`../01-research/avoid-list.md`](../01-research/avoid-list.md)
  (`A-…` anti-patterns), [`../01-research/common-patterns.md`](../01-research/common-patterns.md),
  [`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md),
  [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md),
  [`../01-research/competitor-feature-matrix.md`](../01-research/competitor-feature-matrix.md).
- **Tier-1 platform facts:** [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md),
  [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).
- **Quality memory:** [`../05-qa/defect-pattern-log.md`](../05-qa/defect-pattern-log.md)
  (DP-001…DP-006), [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  (AR-002…AR-008), [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md).

**Evidence weighting (unchanged):** most robustly demonstrated evidence is **Emipro
(EM, ~29 screenshots)** and **VentorTech (VT, dated release notes)**; **SH** is
caption-level, **WK** guide-level, **EC** has no screenshots. Demonstrated (EM/VT)
weighted over SH/WK/EC/TQ claims; Tier-1 platform facts outrank all vendor evidence.

> **TeqStars (TQ) source-availability correction (2026-07-01).** Sprint C recorded the
> TeqStars docs as **403-blocked on 2026-06-30** (claims only). ChatGPT **re-checked on
> 2026-07-01 and found them accessible**
> ([docs.teqstars.com](https://docs.teqstars.com/19.0/applications/shopify/overview.html)) —
> the tree documents product import/export/update, price/inventory import/export,
> collection/catalog, order import/status, refunds/cancellations/returns, mark-as-paid,
> payouts, and metafields. A **full TeqStars evidence rebaseline is pending a later
> research sprint** and is **not** performed here. The PR #55 product-direction correction
> (controlled product export/update in MVP) is **already supported by existing EM/VT/WK/SH
> product-export evidence** and only **reinforced** by this TQ re-check.

## Scope decision rule

A capability is **proposed for MVP** only if it passes **all** of:

1. **Core-loop essential or platform-required.** It is necessary to make the
   *correct, observable, recoverable single-store sync loop* work, **or** Tier-1
   Shopify/Odoo makes it mandatory for that loop (evidence strength **A**, or **B**
   demonstrated), **or** it is a cheap, correctness-neutral trust/UX inference (**E**)
   that materially raises trust.
2. **Deliverable without forcing a gated decision.** Its *intent* can be committed to
   MVP while its *mechanism* stays isolatable behind the layered design — i.e. it does
   not require choosing distribution, API strategy, queue framework, binding data
   model, error/retry taxonomy, or module boundaries **now**. If it forces such a
   choice, it is marked **Architecture-dependent** (RB-14), not excluded.
3. **Keeps MVP small but excellent.** It does not add object-direction, financial,
   or breadth surface that the correctness core does not need. Breadth, second sync
   directions, and premium surfaces are **deferred**, not because they are unworthy,
   but because MVP wins on *depth of correctness*, not *breadth of coverage*.

Otherwise the capability is **exclude** (out of first release), **defer** (a named
later phase), or **open** (ChatGPT must decide direction/necessity). Every item below
carries one of: `include` / `exclude` / `defer` / `open`.

> **Direction (RB-13 accepted, PR #55-corrected).** Primary direction: **Shopify → Odoo
> for catalog, customers, and orders (import)** and **Odoo → Shopify for inventory and
> fulfilment/tracking (write-back)** — Shopify as the sales channel, Odoo as the back
> office. **In addition, the product catalog is controlled two-way:** Odoo → Shopify
> **product export/update** is **in MVP** (controlled — matching, binding, preview,
> draft/unpublished/channel-controlled), per the PR #55 correction. **Customer export**
> is deferred; **unrestricted autonomous bidirectional catalog ownership** is deferred.

## MVP thesis

**Small but excellent = a correct, observable, recoverable single-store sync loop
across the core commerce objects — proven, not just claimed — wrapped in an operator
experience a non-developer can run.** We win the first release on **demonstrated
correctness** (idempotency + first-class reconciliation + rate-limit awareness) and
the **operator experience** (command center + recovery-first error center + honest
freshness), delivered at the **demonstrated object baseline** for one store — **not**
on object-direction breadth, financial depth, or premium surfaces. Breadth ships
later as clean, optional add-ons on this core (vision differentiation theme 5).

## MVP quality bar

An MVP capability is "done to bar" (adapted from the vision's premium quality bar;
**[Recommendation]**, gated) when it is:

- **Correct under failure** — behaves correctly when webhooks are missed, retried,
  duplicated, or delivered out of order, because **idempotency + reconciliation** are
  in place (**[Fact]** `@idempotent` on inventory/refund writes from 2026-04; webhook
  delivery not guaranteed; O-REL-1).
- **Recoverable** — every failure is **isolated, reason-coded, and retryable** (auto
  where safe, one-click where manual) with a named next action (O-LOG-1).
- **Observable & honest** — status and data freshness are visible and truthfully
  labelled; no "real-time" overstatement (O-UX-1, A-UX-1).
- **Safe** — destructive/irreversible actions require a dry-run/preview or strong
  confirmation; never silently loses data (A-IMP-1 `productSet` delete-on-omit).
- **Approachable then powerful** — sensible defaults + inline help; advanced power
  opt-in (O-UX-2).
- **Evidenced & documented** — traces to demonstrated need or a Tier-1 requirement;
  ships with open, screenshot-rich docs and a built-in self-test (O-DOC-1, O-TEST-1).
- **Modular & upgrade-safe** — isolated from `adams_base`; survives Odoo upgrades
  (O-MOD-1; boundaries **not decided** — AR-004).

## Recommended MVP scope — accepted baseline

> **Accepted MVP baseline (ChatGPT RB-13, DEC-003 — PR #55-corrected).** The scope below
> is the accepted product baseline; the Sprint F **open** direction forks are resolved in
> the **ChatGPT RB-13 acceptance** section above (**controlled product export/update →
> accepted in MVP**; customer export → deferred; Domain 9 → minimal financial evidence
> only; refunds/cancellations → deferred; bulk ops → not user-facing, internal-only
> assessment; single-store/single-company accepted; P1 primary / P2 secondary). Items whose
> *mechanism* is gated remain **Architecture-dependent — must be resolved in RB-14 before
> implementation.** Per-domain blocks below retain their evidence and their original
> recommendation label for traceability; where a block still reads `open`, the acceptance
> section above is authoritative.

**In one paragraph:** a **single-store** connector that **imports** products (with
variants + basic images and price), customers (deduplicated), and orders (with a
basic order lifecycle and the minimal payment/journal representation the Odoo order
flow needs); does **controlled product export/update back to Shopify** (selected
products, previewed, matched + bound, draft/unpublished/channel-controlled); and
**writes back** inventory (multi-location-aware, idempotent) and fulfilment/tracking —
driven by a **layered sync model** (webhooks + scheduled + first-class reconciliation +
manual) on a **correctness engine** (idempotency keys, GID↔Odoo binding + documented
dedup keys, per-record failure isolation, retry classification with safe manual retry,
rate-limit awareness, resumable jobs) — all surfaced through an **operator experience**
(guided setup + readiness self-test, credential masking, a basic command center, a
recovery-first error center with reason-coded logs, honest freshness labels) with
**role-based access** and **open, honest docs**. It **excludes** customer export,
**unrestricted autonomous bidirectional catalog ownership**, refunds/returns lifecycle,
payouts, Markets/B2B/POS/gift cards/metafields, multi-store & multi-company, pricelist
& per-market pricing, custom transforms, bulk-ops-as-a-feature, and advanced
analytics (see [`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md)).

## MVP scope by domain

> **Accepted MVP baseline (ChatGPT RB-13, DEC-003).** Each per-domain block keeps its
> evidence and original recommendation label for traceability; where a block reads
> `open`, the **ChatGPT RB-13 acceptance** section above is authoritative (the resolved
> value is noted inline as **RB-13 accepted:** …). Evidence strength (A–E) and competitor
> coverage are taken verbatim from
> [`./capability-evidence-map.md`](./capability-evidence-map.md). Excluded/later items
> are given a compact block here and treated in full in
> [`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md).

### Domain 1 — Store connection, authentication, and setup

**C-CONN-01 — Store connection (OAuth-first, conditional)**
- Capability ID(s): C-CONN-01
- Recommendation: include (a working, secure store connection) — auth *style* open
- Evidence strength: B / A-if-public (VT [Demonstrated] + Shopify public-app rule)
- Evidence source: VT OAuth connect; Shopify public-app/App-Store requirement
- User value: a store cannot be connected at all without this; it is the front door.
- Risk if included: hard-coding OAuth-first pre-empts the distribution decision.
- Risk if excluded: no product.
- Architecture dependency: **AR-002 (open)** — **Architecture-dependent — must be
  resolved in RB-14 before implementation.** OAuth is mandatory *only if*
  public/App-Store distribution is chosen; custom/private may use token/custom-app.
- MVP rationale: the *capability* (connect a store securely + guided) is MVP-critical;
  the *mechanism* stays conditional (DP-006).
- ChatGPT decision needed: distribution model (AR-002), which fixes OAuth-mandatory.

**C-CONN-02 — Credential storage & masking**
- Capability ID(s): C-CONN-02
- Recommendation: include
- Evidence strength: B (VT v2.1.3 [Demonstrated])
- Evidence source: VT credential masking; vision security strategy.
- User value: protects secrets; a baseline trust signal for P3.
- Risk if included: negligible.
- Risk if excluded: secret leakage in UI/logs; fails non-negotiable #6.
- Architecture dependency: none.
- MVP rationale: cheap, high-trust, correctness-neutral.
- ChatGPT decision needed: none (endorse).

**C-CONN-03 — Guided setup wizard**
- Capability ID(s): C-CONN-03
- Recommendation: include
- Evidence strength: B (WK/EM screenshots [Demonstrated])
- Evidence source: WK/EM setup screens; O-SET-1; UX Principle 1.
- User value: onboarding friction is the #1 drop-off (O-SET-1); a guided flow is the
  difference between first-sync-success and a support ticket.
- Risk if included: low; must avoid gating the guide behind a wall (A-DOC-1).
- Risk if excluded: fragile, doc-dependent setup — a demonstrated competitor failure.
- Architecture dependency: none (flow content depends on AR-002 auth style — kept
  generic).
- MVP rationale: core to the "easy + reliable onboarding" differentiator.
- ChatGPT decision needed: none (endorse); step content follows AR-002.

**C-CONN-04 — Test connection (pass/fail)**
- Capability ID(s): C-CONN-04
- Recommendation: include
- Evidence strength: B (WK/SH [Demonstrated])
- Evidence source: WK discrete Test Connection; UX Principle 2 floor.
- User value: instant, unambiguous "am I connected?" — cheap, high value.
- Risk if included: none.
- Risk if excluded: failures discovered mid-sync instead of up front.
- Architecture dependency: none.
- MVP rationale: the cheap floor of readiness; near-zero cost.
- ChatGPT decision needed: none (endorse).

**C-CONN-05 — Scope / readiness pre-flight check**
- Capability ID(s): C-CONN-05
- Recommendation: include (MVP version)
- Evidence strength: C (VT scope-check + EM gotcha + [Inference] — partial whitespace)
- Evidence source: VT scope check; EM trailing-slash gotcha; O-SET-2; UX Principle 2.
- User value: surfaces known failure modes (scopes, HTTPS/`web.base.url`, webhook
  reachability, worker/queue presence, credential validity) **before** first sync.
- Risk if included: over-scoping the check list; *which checks are essential* is open.
- Risk if excluded: predictable failures surface late (support tickets) — the
  demonstrated competitor weakness.
- Architecture dependency: AR-003 (queue/worker presence check) — light; **partly
  Architecture-dependent** (which prerequisites exist depends on the queue/API choice).
- MVP rationale: ties readiness + docs self-test (O-TEST-1) into one trust surface;
  no competitor does it fully — a differentiator.
- ChatGPT decision needed: which checks are MVP-essential vs later (Open question).

**C-CONN-06 — Reconnect / re-authorise / disconnect**
- Capability ID(s): C-CONN-06
- Recommendation: include
- Evidence strength: B (VT store-URL migration fix, dated [Demonstrated])
- Evidence source: VT store-URL fix; setup-flow principles.
- User value: a real, evidenced failure mode (store-URL migration, rotated creds).
- Risk if included: low.
- Risk if excluded: a stuck connection with no recovery path.
- Architecture dependency: none (auth style follows AR-002).
- MVP rationale: reconnection is part of a trustworthy connection lifecycle.
- ChatGPT decision needed: none (endorse).

### Domain 2 — Dashboard, health, and command center

**C-DASH-01 — Unified command center (basic)**
- Capability ID(s): C-DASH-01
- Recommendation: include (basic)
- Evidence strength: C (synthesis of SH monitoring + VT diagnostics — [Inference] on
  [Demonstrated] halves; no competitor combines them)
- Evidence source: SH Integration Dashboard; VT traffic-light; O-DASH-1; UX Principle 5.
- User value: one home answering "is everything OK / what failed / what to do."
- Risk if included: scope creep into a heavy analytics surface; keep it *basic*.
- Risk if excluded: scattered menus — the demonstrated competitor weakness.
- Architecture dependency: AR-003 (light — quick actions must enqueue, not run inline).
- MVP rationale: the operator-UX differentiator; a basic version is MVP, breadth later.
- ChatGPT decision needed: admin vs functional-user dashboard split (Open question).

**C-DASH-02 — Health indicators (traffic-light)**
- Capability ID(s): C-DASH-02
- Recommendation: include
- Evidence strength: B (VT Confluence + SH [Demonstrated])
- Evidence source: VT traffic-light health; C-DASH-02.
- User value: glanceable "is everything OK?"
- Risk if included: low.
- Risk if excluded: no at-a-glance health.
- Architecture dependency: none.
- MVP rationale: cheap, high-signal; pairs with the error center.
- ChatGPT decision needed: none (endorse).

**C-DASH-03 — Activity timeline / queue / failure counts**
- Capability ID(s): C-DASH-03
- Recommendation: include
- Evidence strength: B (SH activity chart [Demonstrated])
- Evidence source: SH daily activity chart; O-DASH-1.
- User value: "what has been happening, what is queued, what failed."
- Risk if included: low.
- Risk if excluded: no operational visibility; blind operation.
- Architecture dependency: AR-003 (light — reflects the queue model).
- MVP rationale: covers the operational-insight need without a separate analytics
  module (see C-RPT-01 deferral).
- ChatGPT decision needed: none (endorse basic counts/timeline).

**C-DASH-04 — Named-cause diagnostics + fix hints (basic)**
- Capability ID(s): C-DASH-04
- Recommendation: include (basic)
- Evidence strength: B (VT yellow-status [Demonstrated])
- Evidence source: VT named-cause status; O-UX-3.
- User value: status that encodes the *cause* and a *fix hint*, not just red/green.
- Risk if included: a full named-cause taxonomy is open (AR-006) — ship a basic set.
- Risk if excluded: opaque status (an anti-pattern, A-UX-4).
- Architecture dependency: AR-006 (error/cause taxonomy) — basic set in MVP.
- MVP rationale: glanceable+actionable health is the differentiator; keep the taxonomy
  minimal for MVP.
- ChatGPT decision needed: how rich the cause taxonomy is at MVP (ties AR-006).

**C-DASH-05 — Quick actions**
- Capability ID(s): C-DASH-05
- Recommendation: include
- Evidence strength: B (EM/SH/VT/WK [Demonstrated])
- Evidence source: C-DASH-05; UX Principle 5 (actions **enqueue**).
- User value: run a sync / reconcile / retry from one place.
- Risk if included: must enqueue, never run heavy work inline (5s-ack; A-SYNC-4).
- Risk if excluded: operator must hunt through menus to act.
- Architecture dependency: AR-003 (must enqueue) — light.
- MVP rationale: completes the command-center loop.
- ChatGPT decision needed: none (endorse; enqueue-only).

**C-DASH-06 — Empty states / first-run guidance**
- Capability ID(s): C-DASH-06
- Recommendation: include
- Evidence strength: E ([Inference] — UX best-practice; no competitor evidence)
- Evidence source: UX best-practice; dashboard principles.
- User value: guides the new user from zero to first sync.
- Risk if included: none (correctness-neutral).
- Risk if excluded: a cold, confusing first run.
- Architecture dependency: none.
- MVP rationale: cheap trust/UX; classified **[Inference]** only (not a competitor
  capability) — passes the gate as a correctness-neutral E-item.
- ChatGPT decision needed: none (endorse as low-cost UX).

### Domain 3 — Product catalog sync

**C-PROD-01 — Product import**
- Capability ID(s): C-PROD-01
- Recommendation: include
- Evidence strength: B (EM/VT/SH screenshots [Demonstrated]); Tier-1 API [Fact]
- Evidence source: EM/VT/SH import screens; common-patterns baseline.
- User value: the catalog is the substrate for orders/inventory; import is baseline.
- Risk if included: idempotency required to avoid duplicates (ties C-JOB-04/C-MAP-01).
- Risk if excluded: no catalog → no meaningful order/inventory sync.
- Architecture dependency: AR-002 (API), AR-005 (binding) — **Architecture-dependent**
  for *how*; the *capability* is MVP.
- MVP rationale: core object baseline, import direction (see direction assumption).
- ChatGPT decision needed: confirm import as the MVP product direction.

**C-PROD-02 — Product export/update (controlled, draft-first)**
- Capability ID(s): C-PROD-02 (export), C-PROD-05 (safety, mandatory)
- Recommendation: open (lean defer) — **RB-13 accepted (PR #55 correction): CONTROLLED
  product export/update IN MVP** (previewed, matched, bound, draft/unpublished/channel-
  controlled; C-PROD-05 safety mandatory)
- Evidence strength: B (VT/EM/SH/WK [Demonstrated]); C-PROD-05 safety is A [Fact]
- Evidence source: VT/EM/WK/SH draft-export [Demonstrated]; **[Fact]** `productSet`
  delete-on-omit (A-IMP-1); TeqStars docs re-checked accessible 2026-07-01 (reinforcing).
- User value: launch/maintain Odoo-authored products on Shopify without duplicates or
  unsafe publishes — a **market-baseline** capability, not a luxury.
- Risk if included: adds the controlled export/update path; **requires** matching +
  binding + preview + destructive-apply safety (C-PROD-05) — bounded by "controlled".
- Risk if excluded: MVP could not create/update Shopify products from Odoo — below the
  demonstrated market baseline (EM/VT/WK/SH).
- Architecture dependency: AR-002 (API/destructive-apply), AR-005 (binding/match) —
  **Architecture-dependent.**
- MVP rationale: product import/export/update is demonstrated by four competitors; MVP
  includes it in a **controlled, safe** form (matching/binding/preview/draft) and defers
  only **unrestricted autonomous bidirectional catalog ownership**.
- ChatGPT decision needed: resolved — controlled export/update accepted.
- **RB-13 decision (DEC-003, PR #55):** **CONTROLLED product export/update ACCEPTED in
  MVP.** Selected products only; preview before create/update/export; draft/unpublished or
  explicit sales-channel control; binding after confirmation; ambiguous matches → manual
  review; no name-only automatic matching; no destructive/full-state write without
  preview/dry-run. **Unrestricted autonomous bidirectional catalog ownership** stays
  deferred. See *Product onboarding and duplicate-prevention baseline*.

**C-PROD-03 — Publish / unpublish & channel control**
- Capability ID(s): C-PROD-03
- Recommendation: defer — **RB-13 accepted (PR #55): BASIC draft/unpublished/sales-channel
  export control IN MVP (as export safety); ADVANCED publish/channel campaign management
  DEFERRED**
- Evidence strength: B (EM/SH [Demonstrated])
- Evidence source: C-PROD-03; ties to POS/sell-OOS; TeqStars export-without-publishing
  (accessible 2026-07-01).
- User value: export safely without publishing (draft / no-sales-channel), and control
  which products go live — the safe minimum for controlled export.
- Risk if included (basic): low — it is the safety layer for the controlled export path.
- Risk if excluded: unsafe publishes on export; below the demonstrated baseline.
- Architecture dependency: none directly (follows the controlled-export path).
- MVP rationale: **basic** draft/unpublished/channel-controlled export safety is **in MVP**
  (part of controlled export); **advanced publish/channel campaign management is deferred**
  (unrestricted catalog ownership).
- ChatGPT decision needed: resolved — basic export safety in MVP; advanced deferred.

**C-PROD-04 — Exclude-from-sync**
- Capability ID(s): C-PROD-04
- Recommendation: include (basic)
- Evidence strength: B (SH/EM [Demonstrated])
- Evidence source: EM logs exclusion reason; C-PROD-04.
- User value: lets an operator scope what syncs (skip discontinued/irrelevant items).
- Risk if included: low.
- Risk if excluded: all-or-nothing sync; no operator control over noise.
- Architecture dependency: none.
- MVP rationale: cheap control that improves correctness and trust; useful either
  direction.
- ChatGPT decision needed: none (endorse basic exclude flag + logged reason).

**C-PROD-05 — Draft/preview before destructive apply**
- Capability ID(s): C-PROD-05
- Recommendation: open (mandatory **if** export/destructive apply is in MVP) — **RB-13
  accepted (PR #55): MANDATORY in MVP** (the controlled product export/update path is in
  MVP, so its destructive-write safety is mandatory)
- Evidence strength: A ([Fact] `productSet` delete-on-omit + VT dry-run [Demonstrated])
- Evidence source: **[Fact]** A-IMP-1; VT Preview/Report; UX Principle 7.
- User value: prevents silent data loss on full-state mutations.
- Risk if included: adds a preview surface (required by the controlled export path).
- Risk if excluded (while doing destructive writes): **data loss** — non-negotiable #1.
- Architecture dependency: AR-002 — **Architecture-dependent.**
- MVP rationale: it is the **mandatory guardrail** for the controlled export/update path
  (C-PROD-02) that MVP now includes — no full-state write without preview/dry-run.
- ChatGPT decision needed: resolved — mandatory in MVP with controlled export.

### Domain 4 — Variants, options, images, and media

**C-VAR-01 — Variant / option sync (2,048 model)**
- Capability ID(s): C-VAR-01
- Recommendation: include
- Evidence strength: A ([Fact] Shopify 2,048 variant model + EM/VT [Demonstrated])
- Evidence source: **[Fact]** product/variant model; VT 250-cap fix (v2.1.4).
- User value: real catalogs have variants; ignoring them breaks orders/inventory.
- Risk if included: must respect the current variant model (avoid the 250 cap).
- Risk if excluded: a products-only MVP that mishandles real stores.
- Architecture dependency: AR-002 — **Architecture-dependent** for *how*.
- MVP rationale: variants are inseparable from product/inventory correctness.
- ChatGPT decision needed: none (endorse as part of product sync).

**C-VAR-02 — Image / media sync (basic)**
- Capability ID(s): C-VAR-02
- Recommendation: include (basic)
- Evidence strength: B (EM/VT [Demonstrated]); pHash dedup (TQ) is [Competitor claim]
- Evidence source: EM/VT image sync; C-VAR-02.
- User value: product pages need images; basic image sync is expected baseline.
- Risk if included: advanced media dedup (pHash) is claim-only — **exclude** that.
- Risk if excluded: incomplete product records.
- Architecture dependency: none (basic); scale handling ties to performance (AR-002).
- MVP rationale: **feasibility supported** for basic image/media; advanced dedup is
  a claim, not demonstrated — excluded (DP-003/DP-004).
- ChatGPT decision needed: confirm basic image sync in MVP; pHash dedup stays out.

**C-VAR-03 — SEO / standard product taxonomy**
- Capability ID(s): C-VAR-03
- Recommendation: defer
- Evidence strength: B (VT only [Demonstrated])
- Evidence source: C-VAR-03.
- User value: SEO/taxonomy enrichment.
- Risk if excluded: none for MVP correctness.
- Architecture dependency: none.
- MVP rationale: single-vendor evidence; enrichment, not core — later.
- ChatGPT decision needed: none (later).

**C-VAR-04 — BoM / kit stock handling**
- Capability ID(s): C-VAR-04
- Recommendation: exclude (later)
- Evidence strength: B (VT only [Demonstrated])
- Evidence source: C-VAR-04; AR-007.
- User value: manufacturing-aware stock — niche.
- Risk if excluded: none for typical MVP stores.
- Architecture dependency: AR-007.
- MVP rationale: niche, single-vendor; keep MVP small.
- ChatGPT decision needed: none (later).

### Domain 5 — Pricing, pricelists, compare-at, markets

**C-PRICE-01 — Price & compare-at sync (basic, with product sync)**
- Capability ID(s): C-PRICE-01
- Recommendation: include (basic — the product's own price/compare-at)
- Evidence strength: B (EM compare-at + VT [Demonstrated])
- Evidence source: C-PRICE-01.
- User value: a product without a price is incomplete; compare-at is expected.
- Risk if included: multi-currency/market pricing is out of scope — keep to base price.
- Risk if excluded: incomplete product/order value data.
- Architecture dependency: none for base price (follows product direction).
- MVP rationale: base price/compare-at travels with the product record; pricelists and
  per-market pricing are **deferred** (C-PRICE-02/03).
- ChatGPT decision needed: confirm base price only in MVP.

**C-PRICE-02 — Pricelist mapping**
- Capability ID(s): C-PRICE-02
- Recommendation: defer
- Evidence strength: B (EM/VT [Demonstrated])
- Evidence source: C-PRICE-02.
- User value: multiple price lists per segment/market.
- Risk if included: config complexity; not needed for a correct single-price MVP.
- Risk if excluded: none for MVP.
- Architecture dependency: none (light).
- MVP rationale: adds configuration surface without core-correctness value — later.
- ChatGPT decision needed: none (later).

**C-PRICE-03 — Per-market (Catalogs) pricing + dry-run**
- Capability ID(s): C-PRICE-03
- Recommendation: exclude (later — ties to Shopify Markets)
- Evidence strength: B (VT Preview/Report + EM [Demonstrated])
- Evidence source: C-PRICE-03; C-ADV-01 (Markets).
- User value: market-specific pricing.
- Risk if excluded: none for MVP.
- Architecture dependency: Markets review.
- MVP rationale: premium differentiator, not baseline; Markets is explicitly non-MVP.
- ChatGPT decision needed: none (later).

### Domain 6 — Inventory, stock quantities, and locations

**C-INV-01 — Stock quantity sync (write-back)**
- Capability ID(s): C-INV-01
- Recommendation: include
- Evidence strength: A ([Fact] `committed` read-only, `@idempotent` set/adjust + EM/VT)
- Evidence source: **[Fact]** inventory model; EM/VT [Demonstrated]; O-REL-1.
- User value: correct stock on the storefront prevents oversell/undersell.
- Risk if included: must write only `available`/`on_hand`, never `committed`, and
  idempotently (A-INV-2, C-JOB-04).
- Risk if excluded: the connector cannot keep stock honest — a core purpose.
- Architecture dependency: AR-007 — **Architecture-dependent** for design.
- MVP rationale: inventory write-back (Odoo→Shopify) is the back-office core value.
- ChatGPT decision needed: confirm write-back direction; AR-007 design at RB-14.

**C-INV-02 — Quantity-field / source-quantity choice**
- Capability ID(s): C-INV-02
- Recommendation: include (a sensible default + inline help)
- Evidence strength: B (EM formulas [Demonstrated])
- Evidence source: C-INV-02; UX Principle 3 (inline help on jargon).
- User value: choosing Forecast vs Free-to-Use decides what number ships to Shopify.
- Risk if included: jargon overwhelm — mitigate with a default + inline help.
- Risk if excluded: wrong quantities pushed (oversell/undersell).
- Architecture dependency: AR-007.
- MVP rationale: MVP ships one **correct default** with inline help; the full choice
  matrix can stay minimal.
- ChatGPT decision needed: which default quantity field for MVP.

**C-INV-03 — Multi-location inventory mapping (awareness)**
- Capability ID(s): C-INV-03
- Recommendation: include (awareness — avoid a wrong single-location design)
- Evidence strength: A ([Fact] InventoryLevel per-location + EM/VT [Demonstrated])
- Evidence source: **[Fact]** per-location model; A-INV-2 (SKU-only double-decrement).
- User value: correct per-location stock; prevents multi-location double-decrement.
- Risk if included: adds a location-mapping surface.
- Risk if excluded: **a single-location design is a demonstrated anti-pattern (WK)**
  and would need re-architecting; MVP must at least be *location-aware*.
- Architecture dependency: AR-007 — **Architecture-dependent.**
- MVP rationale: even if a store uses one location, the **model must map locations**
  so it is not wrong-by-design (correctness, not breadth).
- ChatGPT decision needed: minimum multi-location support at MVP (map ≥1 location
  safely) — design at RB-14/AR-007.

**C-INV-04 — Stock import with controlled apply/review**
- Capability ID(s): C-INV-04
- Recommendation: include (controlled apply) — auto-apply **open**
- Evidence strength: C (EM [Demonstrated] with manual-apply friction)
- Evidence source: C-INV-04; **auto-apply is an [Inference] improvement, not
  demonstrated** (DP-006); A-INV-1.
- User value: bring Shopify/initial stock into Odoo with a controlled apply.
- Risk if included: **auto-apply is not demonstrated evidence** — must stay labelled
  inference; manual post-import processing is an anti-pattern to *improve on*, not to
  copy.
- Risk if excluded: no clean initial stock reconciliation path.
- Architecture dependency: AR-007 — **Architecture-dependent** (auto vs review apply).
- MVP rationale: include the **controlled apply/review** capability; whether apply is
  automatic (the improvement) or reviewed is **open** and routed to AR-007 (DP-006).
- ChatGPT decision needed: auto-apply vs review-then-apply at MVP (do not promote the
  auto-apply inference to a decision).

### Domain 7 — Customers, companies, and addresses

**C-CUST-01 — Customer import**
- Capability ID(s): C-CUST-01
- Recommendation: include
- Evidence strength: B (EM/VT/SH [Demonstrated]) + Shopify PII rules [Fact]
- Evidence source: C-CUST-01; **[Fact]** protected customer data + 60-day/PII rules.
- User value: orders need customers; import is baseline.
- Risk if included: must handle no-PII plans (VT default-customer) + protected-data.
- Risk if excluded: orders without customers — broken order flow.
- Architecture dependency: none (light); PII handling is platform-conditional.
- MVP rationale: core object baseline; import direction.
- ChatGPT decision needed: confirm no-PII fallback (default customer) in MVP.

**C-CUST-02 — Customer export (email dedup, link)**
- Capability ID(s): C-CUST-02
- Recommendation: open (lean defer) — **RB-13 accepted: DEFERRED** (Phase 2)
- Evidence strength: B (EM link-by-email [Demonstrated])
- Evidence source: C-CUST-02; AR-005.
- User value: push Odoo-authored customers to Shopify (second direction).
- Risk if included: second-direction complexity; WK/EC are import-only (DP-004).
- Risk if excluded: MVP is customer-import-only.
- Architecture dependency: AR-005 — **Architecture-dependent.**
- MVP rationale: mirrors the product-direction question; **recommend defer** unless
  ChatGPT wants Odoo-first customers.
- ChatGPT decision needed: is customer **export** in MVP?
- **RB-13 decision (DEC-003):** **DEFERRED from MVP.** Customer export is Phase 2; MVP
  is customer-import + matching only.

**C-CUST-03 — Multi-key matching (email / name / phone)**
- Capability ID(s): C-CUST-03
- Recommendation: include
- Evidence strength: B (VT normalized matching [Demonstrated])
- Evidence source: C-CUST-03; O-DUP-1.
- User value: prevents duplicate customers — a core correctness property.
- Risk if included: match keys tie to the binding model (AR-005).
- Risk if excluded: duplicate customers proliferate (a classic defect).
- Architecture dependency: AR-005 — **Architecture-dependent** (keys/model).
- MVP rationale: dedup/matching is MVP-critical for correctness (email primary,
  multi-key); the *model* is gated, the *requirement* is not.
- ChatGPT decision needed: MVP match-key set (email-only vs multi-key) → AR-005.

**C-CUST-04 — Address & company mapping (basic address)**
- Capability ID(s): C-CUST-04
- Recommendation: include (basic billing/shipping address); company mapping defer
- Evidence strength: C (EM/VT partial [Demonstrated]; mostly implied elsewhere)
- Evidence source: C-CUST-04.
- User value: orders need billing/shipping addresses.
- Risk if included: deep multi-address/company is under-demonstrated — keep basic.
- Risk if excluded: incomplete orders.
- Architecture dependency: company mapping ties to multi-company (later, AR-004).
- MVP rationale: include the **basic address** needed for orders; **defer** deep
  multi-address and company mapping (multi-company is later).
- ChatGPT decision needed: confirm basic-address-only in MVP.

### Domain 8 — Orders and order lifecycle

**C-ORD-01 — Order import (webhook + backfill + manual)**
- Capability ID(s): C-ORD-01
- Recommendation: include
- Evidence strength: A ([Fact] reconcile required + VT/EM/SH/WK [Demonstrated])
- Evidence source: **[Fact]** delivery-not-guaranteed; A-SYNC-1 (webhook/cron-only
  both anti-patterns).
- User value: importing orders into Odoo is the connector's headline job.
- Risk if included: must be layered (webhook + reconcile + manual) — never one alone.
- Risk if excluded: no order sync — no product.
- Architecture dependency: AR-003 — **Architecture-dependent** (orchestration).
- MVP rationale: the central MVP capability; layered by design.
- ChatGPT decision needed: none on inclusion; orchestration mechanism → RB-14.

**C-ORD-02 — Historical / backfill import (60-day gate)**
- Capability ID(s): C-ORD-02
- Recommendation: include
- Evidence strength: A ([Fact] 60-day `read_all_orders` gate + EM/VT [Demonstrated])
- Evidence source: **[Fact]** 60-day approval gate; C-ORD-02.
- User value: a new connection must backfill recent order history to be useful.
- Risk if included: the `read_all_orders` approval gate is real and must be handled
  honestly; large backfills may need bulk (C-JOB-06, open).
- Risk if excluded: an empty Odoo on day one.
- Architecture dependency: AR-002 (scope/API) — **Architecture-dependent.**
- MVP rationale: backfill is part of a credible first sync; the 60-day gate is a
  platform fact to surface, not hide.
- ChatGPT decision needed: backfill window/limits at MVP; bulk-ops need (C-JOB-06).

**C-ORD-03 — Order / financial / fulfillment status mapping**
- Capability ID(s): C-ORD-03
- Recommendation: include
- Evidence strength: B (SH matrix + VT [Demonstrated])
- Evidence source: C-ORD-03.
- User value: correct order/financial/fulfilment status in Odoo.
- Risk if included: low; feeds the order workflow.
- Risk if excluded: orders land with meaningless/incorrect status.
- Architecture dependency: none (light).
- MVP rationale: required to represent imported orders correctly.
- ChatGPT decision needed: none (endorse a baseline status map).

**C-ORD-04 — Order workflow (basic)**
- Capability ID(s): C-ORD-04
- Recommendation: include (basic; full configurable auto-workflow later)
- Evidence strength: B (VT pipeline + SH [Demonstrated])
- Evidence source: C-ORD-04; UX Principle 5 (each step an enqueued idempotent job).
- User value: imported orders move through a sensible Odoo lifecycle.
- Risk if included: a fully *configurable* auto-workflow is advanced — ship a basic,
  sane default.
- Risk if excluded: orders sit inert with no lifecycle.
- Architecture dependency: AR-003 — **Architecture-dependent** (each step idempotent).
- MVP rationale: "order status/workflow basics" is MVP; deep configurability is later.
- ChatGPT decision needed: how configurable the MVP workflow is (basic default vs
  configurable).

**C-ORD-05 — Order fraud / risk import**
- Capability ID(s): C-ORD-05
- Recommendation: exclude (later)
- Evidence strength: B (VT only [Demonstrated])
- Evidence source: C-ORD-05.
- User value: surface Shopify risk signals in Odoo.
- Risk if excluded: none for MVP.
- Architecture dependency: none.
- MVP rationale: single-vendor; not core to the sync loop.
- ChatGPT decision needed: none (later).

### Domain 9 — Invoices, payments, gateways, and journals

**C-PAY-01 / C-PAY-02 / C-PAY-03 — Payment & invoice representation (minimal)**
- Capability ID(s): C-PAY-01, C-PAY-02, C-PAY-03
- Recommendation: open (lean: minimal representation only if the Odoo order flow needs
  it; full accounting deferred) — **RB-13 accepted: INCLUDE minimal financial
  representation only; no accounting automation**
- Evidence strength: B (VT/SH invoice, EM multi-payment, SH+VT gateway→journal
  [Demonstrated]); `OrderTransaction` ledger is [Fact]
- Evidence source: C-PAY-01/02/03; **[Fact]** `OrderTransaction`.
- User value: for many Odoo flows an order needs a payment/journal/invoice
  representation to be actionable.
- Risk if included (fully): pulls a full accounting integration into MVP — large,
  edition-sensitive surface.
- Risk if excluded (entirely): imported orders may be non-actionable in Odoo.
- Architecture dependency: none decided; must be **idempotent** (no double-invoice on
  retry — C-JOB-04).
- MVP rationale: per the vision, include **only the minimal payment/journal/invoice
  representation the Odoo order flow requires**; defer the full accounting/gateway
  breadth. Exact minimum is a ChatGPT call.
- ChatGPT decision needed: what is the **minimal** payment/invoice representation
  required for the MVP order flow (vs deferring all of Domain 9)?
- **RB-13 decision (DEC-003):** **INCLUDE minimal financial/payment representation
  only.** MVP preserves, on the imported Odoo order, enough Shopify financial
  information to make the order understandable and operationally useful: **Shopify
  financial status, payment status, gateway/payment-method label, transaction
  reference(s) where available, paid/unpaid/refunded flags (as source info only), order
  totals, taxes, shipping, discounts, currency,** and **basic gateway/journal mapping as
  configuration input only if needed for classification/routing.** **Excluded from MVP:**
  automatic posted invoices, automatic posted payments, bank reconciliation, payout
  reconciliation, full accounting workflow, gateway-specific accounting depth, automatic
  refund accounting, automatic payment posting on retry. **Rule:** *MVP preserves
  financial evidence and order actionability; it does not automate accounting.* If RB-14
  finds a draft invoice/payment artifact is absolutely required for a valid Odoo order
  flow, it is **architecture-dependent** and returns to ChatGPT before implementation —
  do **not** silently add automatic invoice/payment creation. Any representation must be
  **idempotent** (no double-invoice/payment on retry — C-JOB-04).

### Domain 10 — Fulfillment, delivery, tracking, and shipment status

**C-FUL-01 — Fulfillment (FulfillmentOrder) + tracking write-back**
- Capability ID(s): C-FUL-01
- Recommendation: include
- Evidence strength: A ([Fact] FulfillmentOrder + EM/VT/SH [Demonstrated])
- Evidence source: **[Fact]** FulfillmentOrder; A-FUL-1 (legacy endpoints anti-pattern).
- User value: when Odoo ships, Shopify (and the customer) get tracking — closes the
  order loop back to the storefront.
- Risk if included: must use FulfillmentOrder-based mutations, not legacy endpoints.
- Risk if excluded: orders import but never report fulfilment — a half loop.
- Architecture dependency: AR-008 — **Architecture-dependent.**
- MVP rationale: fulfilment/tracking write-back (Odoo→Shopify) is explicit MVP value.
- ChatGPT decision needed: none on inclusion; design → RB-14/AR-008.

**C-FUL-02 — Multi-package / multi-location fulfillment**
- Capability ID(s): C-FUL-02
- Recommendation: defer (single-package tracking write-back in MVP)
- Evidence strength: B (EM Put-in-Pack + VT [Demonstrated])
- Evidence source: C-FUL-02.
- User value: split shipments / multi-package tracking.
- Risk if included: added complexity beyond the core write-back.
- Risk if excluded: MVP handles the common single-package case only.
- Architecture dependency: AR-008.
- MVP rationale: keep MVP to the common case; multi-package later.
- ChatGPT decision needed: confirm single-package MVP scope.

**C-FUL-03 — Fulfillment scope granting / verification**
- Capability ID(s): C-FUL-03
- Recommendation: include
- Evidence strength: A ([Fact] scopes + EM walkthrough [Demonstrated])
- Evidence source: **[Fact]** missing scope = silent failure; C-FUL-03.
- User value: prevents silent fulfilment failures from a missing scope.
- Risk if included: low.
- Risk if excluded: silent fulfilment failures — poor trust.
- Architecture dependency: none (ties to readiness check C-CONN-05).
- MVP rationale: cheap guardrail that folds into the readiness self-test.
- ChatGPT decision needed: none (endorse; fold into readiness).

### Domain 11 — Refunds, returns, cancellations, and restocking

**C-RET-01 — Refund sync (idempotent)**
- Capability ID(s): C-RET-01
- Recommendation: open (lean defer; **if included, idempotency is mandatory**) —
  **RB-13 accepted: DEFERRED** (mandatory idempotent-refund regression carried forward)
- Evidence strength: A ([Fact] `@idempotent` refunds 2026-04 + EM/VT/SH [Demonstrated])
- Evidence source: **[Fact]** A-PAY-2 (non-idempotent → double-refund); C-RET-01.
- User value: represent Shopify refunds in Odoo without double-refunding.
- Risk if included: ties to the payment/invoice representation (Domain 9, open) and
  demands idempotency.
- Risk if excluded: MVP does not reflect refunds (acceptable for a first release).
- Architecture dependency: AR-006 — **Architecture-dependent.**
- MVP rationale: **basic** refund reflection could be MVP, but it depends on the
  Domain 9 decision; **recommend defer** to keep MVP small — with the hard rule that
  **any refund handling must be idempotent** (non-negotiable). *Advanced* refund
  lifecycle is explicitly non-MVP.
- ChatGPT decision needed: is basic refund sync in MVP (tied to Domain 9)?
- **RB-13 decision (DEC-003):** **DEFERRED from MVP** (refund sync is deferred). **Mandatory
  future rule:** if refund handling is later included, the **idempotent-refund /
  no-double-refund** regression scenario is **mandatory** — carried forward, never dropped.

**C-RET-02 — Returns lifecycle (request→approve→process)**
- Capability ID(s): C-RET-02
- Recommendation: exclude (later)
- Evidence strength: A ([Fact] returns API + EM [Demonstrated]); RMA scarce
- Evidence source: C-RET-02; `returnProcess` (returnRefund deprecated).
- User value: full RMA lifecycle.
- Risk if excluded: none for MVP.
- Architecture dependency: AR-006, AR-008.
- MVP rationale: "advanced refunds/returns lifecycle" is explicitly non-MVP.
- ChatGPT decision needed: none (later).

**C-RET-03 — Order cancellation (restock / notify)**
- Capability ID(s): C-RET-03
- Recommendation: open (lean defer; irreversible-action warning mandatory if included) —
  **RB-13 accepted: DEFERRED** (cancellation reflection deferred)
- Evidence strength: B (VT two-step + EM [Demonstrated])
- Evidence source: C-RET-03; UX Principle 7 (irreversible-action warning).
- User value: reflect cancellations with restock/notify.
- Risk if included: irreversible actions need strong guards (A-RET-2).
- Risk if excluded: MVP does not reflect cancellations (acceptable first release).
- Architecture dependency: none directly.
- MVP rationale: **recommend defer** to keep MVP small; if included, EM's
  "never silently create a cancel order" + a warning are required.
- ChatGPT decision needed: is basic cancellation reflection in MVP?
- **RB-13 decision (DEC-003):** **DEFERRED from MVP** (cancellation reflection deferred,
  with returns/RMA C-RET-02). If later included, irreversible-action warnings + "never
  silently create a cancel order" are mandatory.

### Domain 12 — Payouts and reconciliation

**C-POUT-01 / C-POUT-02 — Payout import & bank reconciliation**
- Capability ID(s): C-POUT-01, C-POUT-02
- Recommendation: exclude (later / premium add-on)
- Evidence strength: A (SP-only, [Fact] + EM [Demonstrated]) / B (EM only)
- Evidence source: **[Fact]** payouts Shopify-Payments-only (A-PAY-1); C-POUT-01/02.
- User value: payout reconciliation (finance).
- Risk if excluded: none for MVP.
- Architecture dependency: AR review.
- MVP rationale: gated to Shopify-Payments stores; premium finance add-on — explicitly
  non-MVP.
- ChatGPT decision needed: none (later).

### Domain 13 — Webhooks, scheduled, manual, and reconciliation

**C-SYNC-01 — Webhook subscription management**
- Capability ID(s): C-SYNC-01
- Recommendation: include
- Evidence strength: A ([Fact] webhooks + VT/EM/SH [Demonstrated])
- Evidence source: **[Fact]** Admin-API subs auto-delete after 8 fails; A-SYNC-1.
- User value: near-real-time triggers for the sync loop.
- Risk if included: subscription lifecycle must be managed (auto-delete on failures).
- Risk if excluded: cron-only — a demonstrated anti-pattern (EC).
- Architecture dependency: AR-003 — **Architecture-dependent.**
- MVP rationale: one leg of the layered sync model.
- ChatGPT decision needed: none on inclusion; mechanism → RB-14.

**C-SYNC-02 — Webhook HMAC verification (raw body)**
- Capability ID(s): C-SYNC-02
- Recommendation: include (mandatory)
- Evidence strength: A ([Fact] HMAC before processing)
- Evidence source: **[Fact]** security; A-SYNC-6.
- User value: rejects forged/again-delivered payloads — security correctness.
- Risk if included: none.
- Risk if excluded: a security hole; violates non-negotiable #6.
- Architecture dependency: security (not a design choice).
- MVP rationale: mandatory; under-addressed across the field — a differentiator.
- ChatGPT decision needed: none (endorse as mandatory).

**C-SYNC-03 — Webhook ID dedup + fast acknowledgement**
- Capability ID(s): C-SYNC-03
- Recommendation: include
- Evidence strength: A ([Fact] 5s ack, dedupe on webhook-id)
- Evidence source: **[Fact]**; A-SYNC-4; whitespace (no competitor documents it).
- User value: no duplicate processing; no dropped subscriptions from slow acks.
- Risk if included: heavy work must move out-of-band (ties C-JOB-01/07).
- Risk if excluded: duplicate records + auto-deleted subscriptions.
- Architecture dependency: AR-003 — **Architecture-dependent.**
- MVP rationale: correctness whitespace we can own; mandatory for a webhook leg.
- ChatGPT decision needed: none (endorse).

**C-SYNC-04 — Scheduled sync**
- Capability ID(s): C-SYNC-04
- Recommendation: include
- Evidence strength: B (EM/VT/SH/WK/EC [Demonstrated])
- Evidence source: C-SYNC-04; UX (friendly scheduling language, hide `ir.cron`, A-UX-2).
- User value: steady background sync + the basis for reconciliation.
- Risk if included: crons are off on Odoo.sh staging (surface manual path).
- Risk if excluded: only event-driven — brittle.
- Architecture dependency: AR-003 — **Architecture-dependent.**
- MVP rationale: one leg of the layered model; hide platform internals.
- ChatGPT decision needed: none on inclusion; mechanism → RB-14.

**C-SYNC-05 — Manual / on-demand sync**
- Capability ID(s): C-SYNC-05
- Recommendation: include
- Evidence strength: B (universal WK/EM/VT/SH [Demonstrated])
- Evidence source: C-SYNC-05; also the Odoo.sh-staging test path (A-IMP-3 [Fact]).
- User value: run a sync now; test on staging where crons are disabled.
- Risk if included: none.
- Risk if excluded: no operator agency; no staging test path.
- Architecture dependency: none (light).
- MVP rationale: one leg of the layered model; cheap and essential.
- ChatGPT decision needed: none (endorse).

**C-SYNC-06 — Scheduled + manual reconciliation (first-class)**
- Capability ID(s): C-SYNC-06
- Recommendation: include (MVP-critical)
- Evidence strength: A ([Fact] delivery not guaranteed + EM partial [Demonstrated])
- Evidence source: **[Fact]** O-REL-1; A-SYNC-2; no competitor owns it fully.
- User value: detects and repairs drift/missed events — the clearest correctness
  whitespace and headline differentiator.
- Risk if included: cadence/scope is open (AR-003/006) — ship a basic reconcile.
- Risk if excluded: **silent data drift** — the most damaging, least-owned problem.
- Architecture dependency: AR-003, AR-006 — **Architecture-dependent.**
- MVP rationale: reconciliation is the spine of "demonstrated correctness"; a
  first-class (even if basic) reconcile is **non-negotiable** for an excellent MVP.
- ChatGPT decision needed: reconciliation cadence/scope at MVP (per-object vs global).

**C-SYNC-07 — Sync freshness indicators (last synced / reconciled)**
- Capability ID(s): C-SYNC-07
- Recommendation: include
- Evidence strength: E ([Inference] + latency-honesty; competitors overstate real-time)
- Evidence source: C-SYNC-07; A-UX-1; O-UX-1.
- User value: honest "how fresh is this?" — cheap, high-trust.
- Risk if included: none (correctness-neutral).
- Risk if excluded: opacity / "real-time" temptation (an anti-pattern).
- Architecture dependency: none.
- MVP rationale: honesty-as-a-feature; **[Inference]**-classified (not a competitor
  capability) — passes the gate as a correctness-neutral E-item.
- ChatGPT decision needed: per-object vs global freshness (Open question).

### Domain 14 — Queue, jobs, retries, and recovery

**C-JOB-01 — Async job / queue with per-record isolation (concept)**
- Capability ID(s): C-JOB-01
- Recommendation: include (concept) — framework **open**
- Evidence strength: B (VT `queue_job` + EM queues [Demonstrated])
- Evidence source: C-JOB-01; **[Fact]** Odoo has no core queue; A-MOD-3.
- User value: one bad record never blocks the batch (isolation) — a correctness need.
- Risk if included: choosing `queue_job` vs `ir.cron` is a **gated** decision.
- Risk if excluded: batch-blocking failures; the whole design falls over.
- Architecture dependency: AR-003 — **Architecture-dependent — must be resolved in
  RB-14 before implementation** (queue framework).
- MVP rationale: per-record failure isolation is MVP-critical; the **framework is
  explicitly not chosen here** (task + DP-006).
- ChatGPT decision needed: queue framework (AR-003) — *not* to be decided in this doc.

**C-JOB-02 — Retry classification (auto-safe vs manual) (concept)**
- Capability ID(s): C-JOB-02
- Recommendation: include (concept) — taxonomy **open**
- Evidence strength: C (VT partial [Demonstrated] + [Inference])
- Evidence source: C-JOB-02; AR-006.
- User value: routes failures to auto-retry vs human — the basis of recovery.
- Risk if included: the full taxonomy is open (AR-006).
- Risk if excluded: undifferentiated retries → double-acting or dead ends.
- Architecture dependency: AR-006 — **Architecture-dependent.**
- MVP rationale: include the **concept** with a minimal classification; the taxonomy
  is gated.
- ChatGPT decision needed: MVP error/retry taxonomy scope (AR-006).

**C-JOB-03 — Retry with backoff / safe manual retry**
- Capability ID(s): C-JOB-03
- Recommendation: include (safe manual retry always; auto-retry for safe ops
  conditional on idempotency)
- Evidence strength: B (VT [Demonstrated]; others manual)
- Evidence source: C-JOB-03; **[Fact]** naive retry double-acts without idempotency
  (A-RET-3).
- User value: recover from transient failures without data loss.
- Risk if included: **auto-retry depends on idempotency** (C-JOB-04) — must not
  double-act.
- Risk if excluded: manual-only recovery (an anti-pattern, A-RET-1).
- Architecture dependency: AR-006 — **Architecture-dependent** (auto-retry policy).
- MVP rationale: **safe manual retry** is MVP-critical; auto-retry for safe ops is
  included **only** where idempotency guarantees safety.
- ChatGPT decision needed: which ops auto-retry at MVP (AR-006).

**C-JOB-04 — Idempotency key management**
- Capability ID(s): C-JOB-04
- Recommendation: include (mandatory)
- Evidence strength: A ([Fact] `@idempotent` 2026-04 + VT [Demonstrated])
- Evidence source: **[Fact]** mandatory on inventory set/adjust + refunds; O-REL-1.
- User value: retries and duplicate webhooks do not double-act — core correctness.
- Risk if included: none (it is the safety substrate).
- Risk if excluded: double-decrement / double-refund / duplicate records.
- Architecture dependency: AR-006 — **Architecture-dependent** (key mechanism).
- MVP rationale: the substrate that makes reconciliation + auto-retry safe; mandatory.
- ChatGPT decision needed: none on inclusion; key mechanism → RB-14.

**C-JOB-05 — Rate-limit / GraphQL-cost-aware throttling**
- Capability ID(s): C-JOB-05
- Recommendation: include (MVP-critical)
- Evidence strength: A ([Fact] Shopify limits; **no competitor** addresses it)
- Evidence source: **[Fact]** rate limits; O-REL-2; A-SYNC-5; the biggest reliability
  whitespace.
- User value: avoids 429 storms; survives real catalog/order volumes.
- Risk if included: pacing ties to the API strategy (AR-002).
- Risk if excluded: **failure at scale** — 429 storms, stalled syncs.
- Architecture dependency: AR-002, AR-006 — **Architecture-dependent.**
- MVP rationale: a headline differentiator and a scale-survival requirement; the
  *approach* is gated, the *requirement* is not.
- ChatGPT decision needed: none on inclusion; approach → RB-14/AR-002.

**C-JOB-06 — Bulk operation handling**
- Capability ID(s): C-JOB-06
- Recommendation: open (lean defer; may be needed for large backfills) — **RB-13
  accepted: NOT a user-facing MVP feature; RB-14 (AR-002) internal assessment only**
- Evidence strength: A ([Fact] Bulk Ops; **no competitor** describes it)
- Evidence source: **[Fact]** Bulk Operations (concurrency changed 2026-01); C-JOB-06.
- User value: efficient large reads/writes (e.g. big backfills).
- Risk if included: adds significant machinery.
- Risk if excluded: large backfills (C-ORD-02) may be slow / hit limits.
- Architecture dependency: AR-002 — **Architecture-dependent.**
- MVP rationale: **recommend defer** for small-store MVP; **open** because large
  backfills may force it — flag rather than silently drop (no-silent-caps).
- ChatGPT decision needed: is bulk handling needed for MVP backfill volumes?
- **RB-13 decision (DEC-003):** **NOT a user-facing MVP feature** — do not expose "bulk
  operation management" as an MVP feature. RB-14 (AR-002) must assess whether Bulk
  Operations are required **internally** for safe/resumable large backfills; if so, that
  is an **architecture mechanism, not a product-scope expansion.**

**C-JOB-07 — Resumable / restartable jobs**
- Capability ID(s): C-JOB-07
- Recommendation: include
- Evidence strength: A ([Fact] Odoo worker/cron limits + VT/EM/SH [Demonstrated])
- Evidence source: **[Fact]** no long syncs in one HTTP request; O-PERF-2.
- User value: long syncs complete reliably instead of timing out.
- Risk if included: ties to the queue/orchestration model (AR-003).
- Risk if excluded: timeouts on real volumes; half-finished syncs.
- Architecture dependency: AR-003 — **Architecture-dependent.**
- MVP rationale: correctness/performance requirement for real data sizes.
- ChatGPT decision needed: none on inclusion; mechanism → RB-14.

### Domain 15 — Logs, errors, audit trail, and observability

**C-OBS-01 — Reason-coded, in-app logs**
- Capability ID(s): C-OBS-01
- Recommendation: include (MVP-critical)
- Evidence strength: B (EM Log Book / Mismatch Log [Demonstrated])
- Evidence source: C-OBS-01; A-LOG-1 (EC email-only floor); UX Principle 8.
- User value: the in-app source of truth for what synced and what failed and why.
- Risk if included: low.
- Risk if excluded: email-only/opaque errors — a dead end (anti-pattern).
- Architecture dependency: none (light).
- MVP rationale: reason-coded logs are the substrate of the recovery-first experience.
- ChatGPT decision needed: none (endorse).

**C-OBS-02 — Audit trail of sync actions**
- Capability ID(s): C-OBS-02
- Recommendation: include (basic)
- Evidence strength: B (VT/SH/EM/WK [Demonstrated])
- Evidence source: C-OBS-02.
- User value: "who/what changed" for trust and debugging.
- Risk if included: retention policy needed — keep basic.
- Risk if excluded: no traceability of sync actions.
- Architecture dependency: none.
- MVP rationale: cheap trust; a basic audit trail with a retention note.
- ChatGPT decision needed: retention policy (minor).

**C-OBS-03 — Recovery-first error center (MVP version)**
- Capability ID(s): C-OBS-03
- Recommendation: include (MVP version)
- Evidence strength: C (synthesis EM+VT+SH; unified by none — [Inference])
- Evidence source: C-OBS-03; O-LOG-1; UX Principle 6.
- User value: each failure shows record + reason + fix hint + retry — never a dead end.
- Risk if included: the full auto/human taxonomy is open (AR-006) — ship a basic center.
- Risk if excluded: failures without a recovery surface (the operator is stuck).
- Architecture dependency: AR-006 — **Architecture-dependent.**
- MVP rationale: the second differentiator (operator UX); an MVP version is explicitly
  in scope, full taxonomy later.
- ChatGPT decision needed: how much of the error center is MVP (basic vs full).

**C-OBS-04 — Failed-job notifications to users (basic)**
- Capability ID(s): C-OBS-04
- Recommendation: include (basic)
- Evidence strength: B (VT Failed Job Notifications [Demonstrated])
- Evidence source: C-OBS-04; alerts **complement** the in-app log (A-LOG-1).
- User value: the responsible user hears about failures without watching the screen.
- Risk if included: must not become email-only recovery (anti-pattern).
- Risk if excluded: silent failures until someone checks.
- Architecture dependency: none.
- MVP rationale: a basic notification that complements (never replaces) the log.
- ChatGPT decision needed: none (endorse basic notify).

### Domain 16 — Mapping, matching, and duplicate prevention

**C-MAP-01 — External-ID / Shopify-GID binding model (concept)**
- Capability ID(s): C-MAP-01
- Recommendation: include (concept) — data model **open**
- Evidence strength: A ([Fact] `ir.model.data` + Shopify GID + EM/SH/VT [Demonstrated])
- Evidence source: **[Fact]** GID/ID formats; O-DUP-1.
- User value: the binding is the spine of idempotency + dedup across every object.
- Risk if included: choosing `ir.model.data` reuse vs a dedicated per-store model is
  **gated**; deleted-binding handling is undocumented across the field.
- Risk if excluded: no stable identity → duplicates / double-decrement.
- Architecture dependency: AR-005 — **Architecture-dependent — must be resolved in
  RB-14 before implementation.**
- MVP rationale: the **requirement** (a documented binding) is MVP-critical; the
  **data model is not chosen here** (task + DP-006), and must be multi-store-safe.
- ChatGPT decision needed: binding data model + deleted-binding handling (AR-005).

**C-MAP-02 — Duplicate prevention (documented keys)**
- Capability ID(s): C-MAP-02
- Recommendation: include (MVP-critical)
- Evidence strength: B (EM/VT keys [Demonstrated])
- Evidence source: C-MAP-02; O-DUP-1.
- User value: no duplicate products/customers/orders — core correctness.
- Risk if included: keys tie to the binding model (AR-005).
- Risk if excluded: duplicate records — a classic, damaging defect.
- Architecture dependency: AR-005 — **Architecture-dependent.**
- MVP rationale: dedup keys must be **documented and explicit** (not implicit) at MVP.
- ChatGPT decision needed: the MVP dedup key set per object (AR-005).

**C-MAP-03 — Directional field mapping + dry-run (essential fields only)**
- Capability ID(s): C-MAP-03
- Recommendation: include (essential mappings only); custom transforms **exclude**
- Evidence strength: B (VT direction+transforms+test [Demonstrated])
- Evidence source: C-MAP-03; UX Principle 9; **custom Python transforms = advanced**.
- User value: map the essential fields correctly, previewably.
- Risk if included: full transform engine is advanced — **exclude** for MVP.
- Risk if excluded: blind mapping (an anti-pattern, A-CFG-1).
- Architecture dependency: AR-004, AR-005 — **Architecture-dependent.**
- MVP rationale: "mapping screens for essential mappings only"; custom Python
  transforms are explicitly non-MVP.
- ChatGPT decision needed: which mappings are "essential" at MVP.

**C-MAP-04 — Deterministic routing (location / gateway) (basic)**
- Capability ID(s): C-MAP-04
- Recommendation: include (basic — location + gateway/journal routing); market routing
  defer
- Evidence strength: B (EM country→currency→fallback [Demonstrated])
- Evidence source: C-MAP-04.
- User value: deterministic routing of stock to locations and payments to journals.
- Risk if included: keep to location + gateway; market routing is later (Markets).
- Risk if excluded: ambiguous routing → wrong location/journal.
- Architecture dependency: none (light).
- MVP rationale: needed to support multi-location inventory + payment representation
  cleanly; market routing deferred with Markets.
- ChatGPT decision needed: routing scope (location+gateway only) at MVP.

### Domain 17 — Multi-store, multi-company, and permissions

**C-MULTI-01 — Multi-store + per-store config isolation**
- Capability ID(s): C-MULTI-01
- Recommendation: defer (MVP = single-store) — but MVP **must be multi-store-safe**
- Evidence strength: B (VT [Demonstrated])
- Evidence source: C-MULTI-01; vision "MVP may start single-store (RB-13)".
- User value: connect many stores.
- Risk if including full multi-store: large surface, premature.
- Risk if excluded **carelessly**: a single-store design that **blocks** multi-store
  later (binding keys without per-store scoping) — an architecture trap.
- Architecture dependency: AR-004, AR-005 — **Architecture-dependent.**
- MVP rationale: **single-store MVP**, but the binding/config model must carry
  **per-store keys** so multi-store is not designed out (architecture-safe preparation
  only — not a multi-store feature).
- ChatGPT decision needed: confirm single-store MVP with multi-store-safe keys.
- **RB-13 decision (DEC-003):** **CONFIRMED — single-store, single-company MVP;** no
  multi-store UI/logic and no multi-company logic. Binding keys must stay
  **multi-store-safe** and configuration assumptions must not make future multi-store
  impossible (architecture-safe only). Webkul's default Company field is **not**
  multi-company evidence (DP-004).

**C-MULTI-02 — Multi-company isolation (record rules)**
- Capability ID(s): C-MULTI-02
- Recommendation: exclude (later)
- Evidence strength: B (EM/VT + Odoo record rules [Fact]); WK config-field-only (➖,
  DP-004)
- Evidence source: C-MULTI-02; **WK default-Company field ≠ support (DP-004)**.
- User value: isolate data across Odoo companies.
- Risk if excluded: none for a single-company MVP.
- Architecture dependency: AR-004, security.
- MVP rationale: multi-company complexity is explicitly non-MVP; WK evidence is a
  config field, **not** demonstrated support (DP-004) — do not overweight.
- ChatGPT decision needed: none (later).

**C-MULTI-03 — Role-based access (admin vs functional)**
- Capability ID(s): C-MULTI-03
- Recommendation: include (MVP-critical)
- Evidence strength: A ([Fact] Odoo security + EM/SH [Demonstrated])
- Evidence source: **[Fact]** `ir.model.access` deny-by-default; SH gates setup; UX
  Principle 10.
- User value: an admin surface (setup/creds/mappings) vs a functional-user surface
  (run/read/fix), gated by access rights.
- Risk if included: low (Odoo-native mechanism).
- Risk if excluded: over-privileged operation; violates non-negotiable #4/#6 posture.
- Architecture dependency: security (Odoo-native; not a gated design choice).
- MVP rationale: "basic permissions / admin vs functional user separation" is MVP.
- ChatGPT decision needed: none (endorse admin/functional split).

**C-MULTI-04 — Domain-isolated / per-store config model**
- Capability ID(s): C-MULTI-04
- Recommendation: open (single-store: a per-instance config suffices at MVP) — **RB-13
  accepted: single-store per-instance config at MVP; isolated config *model* stays
  gated (AR-004)**
- Evidence strength: C (VT tabbed config + [Inference])
- Evidence source: C-MULTI-04; **no final module names** (AR-004).
- User value: clean per-store configuration.
- Risk if included (fully): pulls the config data-model decision forward (AR-004).
- Risk if excluded: none if single-store config is used.
- Architecture dependency: AR-004 — **Architecture-dependent.**
- MVP rationale: a single-store MVP needs only a per-instance config; the isolated
  config **model** is gated (no module names/boundaries here).
- ChatGPT decision needed: none for MVP (config model → RB-14/AR-004).
- **RB-13 decision (DEC-003):** single-store MVP uses a **per-instance config**; the
  isolated per-store config **model** remains **architecture-dependent (AR-004)** and out
  of MVP.

### Domain 18 — Markets, B2B, POS, gift cards, metafields, advanced

**C-ADV-01…06 — Advanced Shopify surfaces**
- Capability ID(s): C-ADV-01 (Markets/Catalogs), C-ADV-02 (B2B), C-ADV-03 (POS),
  C-ADV-04 (gift cards), C-ADV-05 (metafields), C-ADV-06 (extended breadth)
- Recommendation: exclude (later / optional add-ons)
- Evidence strength: B mostly single-vendor (VT-only B2B; SH-only gift cards/extended)
- Evidence source: Domain 18 rows; vision differentiation theme 5 (breadth as add-ons).
- User value: premium breadth.
- Risk if excluded: none for MVP.
- Architecture dependency: AR-004/AR-005 (metafields) / various.
- MVP rationale: all explicitly non-MVP; ship as clean, feature-flagged add-ons later
  (premium, not bloated).
- ChatGPT decision needed: none (later).

### Domain 19 — Reporting, analytics, and operational insights

**C-RPT-01 — Operational sync analytics**
- Capability ID(s): C-RPT-01
- Recommendation: defer (basic operational counts covered by the command center)
- Evidence strength: B (SH activity chart + EM graph [Demonstrated])
- Evidence source: C-RPT-01; overlaps C-DASH-03.
- User value: operational insight into sync volumes/failures.
- Risk if excluded: none — the command center's activity/failure counts cover the
  MVP need.
- Architecture dependency: none.
- MVP rationale: avoid a separate analytics surface at MVP; the command center gives
  the basics.
- ChatGPT decision needed: none (defer dedicated analytics).

**C-RPT-02 — Financial / sales reporting**
- Capability ID(s): C-RPT-02
- Recommendation: exclude (later)
- Evidence strength: B (EM [Demonstrated]); Net-Profit Enterprise-only (disclose)
- Evidence source: C-RPT-02.
- User value: financial/sales reporting.
- Risk if excluded: none for MVP.
- Architecture dependency: none; Odoo-edition-gated (disclose).
- MVP rationale: advanced analytics is explicitly non-MVP; edition-gated.
- ChatGPT decision needed: none (later).

### Domain 20 — Documentation, support, demo, and maintenance transparency

**C-DOCS-01 — Readable, screenshot-rich, non-gated docs**
- Capability ID(s): C-DOCS-01
- Recommendation: include (product-quality requirement)
- Evidence strength: B (EM honest docs + VT KB [Demonstrated])
- Evidence source: C-DOCS-01; O-DOC-1; A-DOC-1 (never gate).
- User value: evaluable, self-serve onboarding; a trust signal (P3).
- Risk if included: docs effort — but it is part of the quality bar, not polish.
- Risk if excluded: opacity — a demonstrated competitor weakness.
- Architecture dependency: none.
- MVP rationale: open docs are an MVP **quality requirement**, not later polish.
- ChatGPT decision needed: none (endorse as a quality gate).

**C-DOCS-02 — Dated, honest changelog**
- Capability ID(s): C-DOCS-02
- Recommendation: include (product-quality requirement)
- Evidence strength: B (VT dated release notes [Demonstrated])
- Evidence source: C-DOCS-02; cite **current** platform figures (DP-001).
- User value: transparency about fixes/limitations; trust.
- Risk if included: low.
- Risk if excluded: no-changelog opacity (SH weakness).
- Architecture dependency: none.
- MVP rationale: cheap trust; must cite current figures (DP-001).
- ChatGPT decision needed: none (endorse).

**C-DOCS-03 — Built-in self-test (MVP); public demo (later)**
- Capability ID(s): C-DOCS-03
- Recommendation: include (built-in self-test) / defer (public demo marketplace)
- Evidence strength: C (WK/EM support + TQ demo [Competitor claim])
- Evidence source: C-DOCS-03; self-test ties to C-CONN-05; O-TEST-1.
- User value: buyers/operators can verify readiness without a sales gate.
- Risk if included: keep the self-test scoped to readiness (C-CONN-05).
- Risk if excluded: readiness left to support tickets.
- Architecture dependency: none.
- MVP rationale: the **self-test** folds into readiness and is MVP; **public
  demo/marketplace packaging is explicitly non-MVP** (task).
- ChatGPT decision needed: self-test scope (Open question).

**C-DOCS-04 — App-Store / Built-for-Shopify readiness**
- Capability ID(s): C-DOCS-04
- Recommendation: open (defer unless distribution is decided) — **RB-13 accepted:
  OUT of MVP** (distribution undecided; public App-Store packaging + app
  billing/compliance webhooks excluded unless distribution is later decided — AR-002)
- Evidence strength: A ([Fact] App-Store requirements; none verified across field)
- Evidence source: C-DOCS-04; AR-002.
- User value: public-App-Store distribution compliance.
- Risk if included: depends entirely on the **distribution decision** (AR-002).
- Risk if excluded: none if distribution is custom/private.
- Architecture dependency: AR-002 — **Architecture-dependent.**
- MVP rationale: "full App-Store compliance unless distribution is decided" is
  non-MVP; gated on AR-002.
- ChatGPT decision needed: distribution model (AR-002).
- **RB-13 decision (DEC-003):** **OUT of MVP.** Public App-Store packaging, public
  marketplace demo packaging, and app billing/compliance webhook work are excluded unless
  distribution is later decided (AR-002). MVP ships the built-in self-test, not
  marketplace packaging.

## MVP-critical reliability capabilities

The **non-negotiable correctness spine** of the MVP (mostly platform-required — A).
These make "small but excellent" mean *correct under failure*, not *thin*:

- **Idempotency by default** — C-JOB-04 (**[Fact]** `@idempotent` 2026-04). Substrate
  for safe retries + reconciliation.
- **First-class reconciliation** — C-SYNC-06 (**[Fact]** delivery not guaranteed).
  Detect + repair drift; the clearest whitespace (O-REL-1).
- **Layered sync** — C-SYNC-01/04/05 together (never webhook-only or cron-only;
  A-SYNC-1).
- **Webhook integrity** — C-SYNC-02 (HMAC), C-SYNC-03 (id-dedup + fast ack).
- **Duplicate prevention** — C-MAP-01 (binding, model gated AR-005), C-MAP-02 (keys).
- **Per-record failure isolation + safe retry** — C-JOB-01 (framework gated AR-003),
  C-JOB-02/03 (taxonomy gated AR-006; safe manual retry always).
- **Rate-limit / cost awareness** — C-JOB-05 (**[Fact]**; O-REL-2 whitespace).
- **Resumable jobs** — C-JOB-07 (no long syncs in a request; **[Fact]**).
- **Inventory correctness** — C-INV-01 (write `available`/`on_hand` only), C-INV-03
  (multi-location, avoid double-decrement).
- **Fulfilment correctness** — C-FUL-01 (FulfillmentOrder, not legacy).

> All correctness items above are **Proposed MVP inclusion — pending ChatGPT
> acceptance**; the ones tagged with an AR row are **Architecture-dependent — must be
> resolved in RB-14 before implementation** (mechanism only; the requirement stands).

## MVP-critical UX capabilities

The **operator-experience spine** (the second differentiator; combine SH monitoring +
VT diagnostics that neither does fully):

- **Guided setup + credential masking + test connection** — C-CONN-03/02/04.
- **Readiness self-test before first sync** — C-CONN-05 (+ C-FUL-03 scope check).
- **Basic command center** — C-DASH-01, with health (C-DASH-02), activity/failure
  counts (C-DASH-03), named-cause+fix-hint (C-DASH-04, basic), quick actions that
  enqueue (C-DASH-05), first-run/empty states (C-DASH-06).
- **Recovery-first error center (MVP version)** — C-OBS-03, on reason-coded logs
  (C-OBS-01), audit trail (C-OBS-02), failed-job notifications (C-OBS-04).
- **Honest freshness labels** — C-SYNC-07 (no "real-time" overstatement).
- **Guided, essential-only mappings with dry-run** — C-MAP-03 (custom transforms out).

## MVP-critical configuration capabilities

Kept **minimal and safe** (progressive disclosure; inline help on jargon):

- **Essential field mappings only** — C-MAP-03 (custom Python transforms excluded).
- **Quantity-field default + inline help** — C-INV-02.
- **Deterministic location/gateway routing** — C-MAP-04 (market routing deferred).
- **Exclude-from-sync control** — C-PROD-04.
- **Friendly scheduling language** — C-SYNC-04 (hide raw `ir.cron` internals; A-UX-2).
- **Per-instance (single-store) config** — C-MULTI-04 (isolated config **model** gated
  AR-004; MVP needs only a per-instance config, with multi-store-safe keys per
  C-MULTI-01).

## MVP-critical security and permissions capabilities

- **Role-based access (admin vs functional)** — C-MULTI-03 (**[Fact]** deny-by-default).
- **Credential safety / masking** — C-CONN-02.
- **Webhook HMAC verification** — C-SYNC-02 (security correctness).
- **Protected-data compliance** — C-CUST-01 + C-ORD-02 (**[Fact]** protected customer
  data + 60-day order window / approval gate).
- **Multi-store-safe isolation keys** — C-MULTI-01 (per-store keys so single-store MVP
  is not a multi-store trap). **Multi-company isolation (C-MULTI-02) is later** and
  must not be implied by a config field (DP-004).
- **No casual privilege escalation** — **[Fact]** `sudo()` bypasses access rules
  (A-IMP-5) — a design guardrail, not a feature.

## MVP scope options considered

Three coherent options were weighed against the scope decision rule:

**Option A — Correctness core, with controlled bidirectional product onboarding
(ACCEPTED, PR #55-corrected).**
Single-store. Import products (variants + basic images + base price), customers
(deduped), orders (basic lifecycle + minimal payment/journal representation as needed);
**controlled product export/update back to Shopify** (selected products, previewed,
matched + bound, draft/unpublished/channel-controlled); write back inventory
(multi-location-aware, idempotent) and fulfilment/tracking. Full correctness engine
(layered sync + reconciliation + idempotency + binding/dedup + isolation + safe retry +
rate-limit awareness + resumable jobs). Operator UX (guided setup + readiness self-test +
command center + recovery-first error center + honest freshness). Role-based access. Open
docs + self-test. Excludes **customer export**, **unrestricted autonomous bidirectional
catalog ownership**, refunds/returns lifecycle, payouts, Markets/B2B/POS/gift cards/
metafields, multi-store/company, pricelists/per-market, custom transforms,
bulk-ops-as-a-feature, advanced analytics.
- *Why:* maximises **demonstrated correctness + operator UX** on a bounded surface while
  including the **market-baseline** product path (import + controlled export/update,
  EM/VT/WK/SH-demonstrated); every included item is A/B evidenced or a correctness-neutral
  E; unrestricted catalog ownership and other breadth defer cleanly.
- *Note (PR #55):* the first draft over-deferred product export; ChatGPT corrected it to
  **controlled product export/update in MVP** (safe by construction).

**Option B — Unrestricted autonomous bidirectional catalog (BROADER).**
Option A **plus** automatic all-field two-way conflict resolution, a complex
field-ownership matrix, advanced publish/channel campaign management, customer export, and
catalog breadth (Markets/pricelists/metafields/SEO).
- *Why not (for MVP):* it multiplies conflict/ownership complexity well beyond the
  controlled onboarding MVP needs and enlarges/fragilises the surface — trading MVP
  *correctness depth* for *coverage breadth*, against the thesis. Kept as the natural
  **Phase-2+** direction. (Controlled product export/update — with matching/binding/
  preview/draft — **is** in MVP under Option A.)

**Option C — Thin import-only pilot (NARROWER).**
Products + orders import + manual sync only; no webhooks, no reconciliation, no
write-back.
- *Why not:* it **violates the correctness non-negotiables** — webhook-less/cron-only
  with no reconciliation is a demonstrated anti-pattern (A-SYNC-1/2) causing silent
  drift; no inventory/fulfilment write-back removes the back-office value; it would
  need re-architecting to become excellent. It is *small but not excellent.*

## Recommended MVP option

**Option A — Correctness core, with controlled bidirectional product onboarding.** It is
the only option that satisfies all three scope-rule tests: it is built from
core-loop-essential/platform-required and **market-baseline** (product import/export/
update) capabilities, keeps every gated decision behind the layered design (marked
Architecture-dependent, not decided), and stays small while meeting the excellence bar
(correct under failure, recoverable, observable, honest, safe). **Accepted by ChatGPT
(RB-13, DEC-003) on 2026-07-01, corrected the same day after the PR #55 review to include
controlled product export/update in MVP — architecture still gated.**

## Capabilities excluded from MVP

Summarised here; treated in full in
[`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md):

- **Catalog second direction (RB-13, PR #55-corrected):** **controlled product
  export/update (C-PROD-02) + mandatory safety (C-PROD-05) + basic draft/channel export
  control (C-PROD-03) are IN MVP.** Deferred: **customer export C-CUST-02** and
  **unrestricted autonomous bidirectional catalog ownership** (all-field two-way conflict
  resolution, complex field-ownership matrix, advanced publish/channel campaign
  management) — Phase 2+.
- **Financial depth (RB-13 resolved):** Domain 9 keeps **only the minimal financial
  representation** (C-PAY-01/02/03 — status/labels/references/totals/tax/shipping/
  discount/currency as source info; no accounting automation); **deferred:** refund sync
  C-RET-01, cancellations C-RET-03, returns lifecycle C-RET-02, payouts C-POUT-01/02,
  and all posted invoices/payments/bank/payout reconciliation.
- **Breadth (later):** SEO/taxonomy C-VAR-03, BoM/kit C-VAR-04, pricelists C-PRICE-02,
  per-market pricing C-PRICE-03, order risk C-ORD-05, Markets/B2B/POS/gift cards/
  metafields/extended C-ADV-01…06, multi-package fulfilment C-FUL-02.
- **Scale/config surface (later):** bulk ops C-JOB-06 (**RB-13: not a user-facing MVP
  feature; internal-only assessment at RB-14/AR-002**), dedicated analytics C-RPT-01,
  financial reporting C-RPT-02, custom transforms (within C-MAP-03), pricelist/market
  routing (within C-MAP-04).
- **Multi-tenancy (later):** multi-store C-MULTI-01 (defer; keys must stay
  multi-store-safe), multi-company C-MULTI-02, isolated config model C-MULTI-04
  (single-store config suffices at MVP).
- **Distribution-gated (RB-13 out of MVP; unblock via AR-002):** App-Store/Built-for-
  Shopify readiness C-DOCS-04; public demo/marketplace packaging (within C-DOCS-03); app
  billing/compliance webhooks — excluded unless distribution is later decided.

## Architecture-dependent MVP items

> **Architecture-dependent — must be resolved in RB-14 before implementation.** These
> capabilities are **proposed for MVP as intent/requirements**, but their *mechanism*
> is a gated decision (AR-002…AR-008, all "Not decided / Evidence pending"). MVP scope
> commits the **what**, not the **how**.

| AR row | Open decision (not made here) | MVP capabilities that depend on it |
| --- | --- | --- |
| **AR-002** | Distribution (public vs custom); REST/GraphQL/hybrid; bulk; App-Store; **destructive-apply (`productSet`) mechanics** | C-CONN-01 (auth style), C-PROD-01/02/03/05 (**controlled export/update + destructive-write safety**), C-VAR-01, C-ORD-02, C-JOB-05/06, C-DOCS-04 |
| **AR-003** | Sync orchestration + **queue framework** (`ir.cron` vs `queue_job`) | C-SYNC-01/03/04/06, C-JOB-01/07, C-ORD-01/04, C-DASH-01/03/05 (enqueue) |
| **AR-004** | Module boundaries/names; feature-flag + config model | C-MAP-03, C-MULTI-04, (feature-flag visibility) |
| **AR-005** | Binding/dedup **data model**; per-store keys; deleted-binding handling; **product match keys (SKU/barcode) + first-sync source strategy** | C-MAP-01/02, C-CUST-03, C-PROD-01/02 (**export/import matching + binding**), C-MULTI-01 (safe keys) |
| **AR-006** | Error/retry **taxonomy**; idempotency mechanism; reconciliation cadence | C-JOB-02/03/04, C-OBS-03, C-DASH-04, C-SYNC-06 |
| **AR-007** | Inventory design (fields, multi-location, apply mode) | C-INV-01/02/03/04 |
| **AR-008** | Fulfilment design (FulfillmentOrder, multi-package/location) | C-FUL-01/02 |

No AR row is decided, proposed for active review, or re-litigated here (`CLAUDE.md`
§10; DP-005/DP-006).

## Evidence-consistency review

Applying the **DP-006 evidence-consistency gate** (8 checks) to this proposal:

1. **Official Shopify/Odoo docs?** The correctness spine (C-JOB-04, C-SYNC-02/03/06,
   C-INV-01/03, C-FUL-01, C-ORD-01/02, C-MULTI-03) rests on **[Fact]** Tier-1 rules —
   labelled as facts, not vendor claims.
2. **Demonstrated competitor evidence?** Object/UX baselines (C-PROD-01, C-CUST-01/03,
   C-DASH-*, C-OBS-01) rest on **EM/VT-demonstrated** evidence, weighted over
   SH/WK/EC/TQ claims. **Controlled product export/update (C-PROD-02/03/05)** is a
   **market-baseline** capability **demonstrated by EM/VT/WK/SH** — its MVP inclusion rests
   on that demonstrated evidence, not on a claim.
3. **Competitor claim-only?** Kept **out of MVP** or clearly flagged: pHash image
   dedup (TQ claim → excluded), SH-only/VT-only breadth (Domain 18 → later). **TeqStars
   breadth:** docs were 403-blocked in Sprint C but **re-checked accessible on 2026-07-01**;
   a **full TQ rebaseline is pending a later sprint** and is **not adopted here** (the
   product-export correction stands on EM/VT/WK/SH-demonstrated evidence; TQ only
   reinforces).
4. **Inference / recommendation?** Improvement opportunities are labelled
   **[Inference]**, never demonstrated capability: unified command center (C-DASH-01),
   recovery-first error center (C-OBS-03), freshness indicators (C-SYNC-07),
   empty-states (C-DASH-06), and **auto-apply stock (C-INV-04)** — auto-apply stays an
   inference routed to AR-007, not a decision (DP-006).
5. **Conditional on architecture/distribution?** All such items are marked
   **Architecture-dependent** and routed to AR-002…AR-008; OAuth-first (C-CONN-01)
   stays conditional on distribution; the queue framework, binding model, error/retry
   taxonomy, inventory/fulfilment design, and module boundaries are **not chosen**.
6. **Essential for correctness/UX/reliability/trust?** Each `include` names its
   user value + risk-if-excluded; breadth without correctness value is deferred.
7. **Includable without forcing an architecture decision?** Yes — MVP commits
   *requirements/intent*; mechanisms remain gated (the table above).
8. **Could wording be misread as a *final architecture* decision?** Guarded: the
   document now records the **accepted MVP *product* scope** (ChatGPT RB-13, DEC-003),
   but it is banner-marked **architecture still gated**; **no architecture ADR, module
   name, data model, queue framework, API strategy, or distribution model is decided**;
   every architecture-sensitive item stays **Architecture-dependent (RB-14)**. Scope
   acceptance ≠ mechanism decision.

**DP-003/DP-004 specifics honoured:** WK multi-company stays a config field (➖, not
support); WK import-stock stays ⬜ (not found) — not promoted; "real-time" is never
asserted (C-SYNC-07 honesty); a market promise is not treated as demonstrated
bidirectionality (export directions left open, not assumed).

## MVP acceptance principles

Observable conditions that would define **"MVP-ready"** (principles, **not** code-level
acceptance criteria — those come at implementation with tests):

1. **Correct under failure.** In the seeded regression scenarios (A-IMP-4: duplicate
   orders, multi-location double-decrement, missed-webhook reconciliation,
   timezone/paging), the connector produces **no duplicates, no double-decrement, no
   missed orders** — via idempotency + reconciliation. **Refund scope note (RB-13):**
   refund sync is **DEFERRED from MVP** (C-RET-01, Domain 11), so the **idempotent-refund
   / no-double-refund regression scenario is carried forward as a mandatory acceptance
   principle for the first refund/refund-sync sprint** — never dropped. (Were refunds
   ever pulled into MVP, that scenario would become mandatory in the MVP itself.)
2. **Layered sync proven.** Webhook, scheduled, and manual paths each work, and
   reconciliation detects+repairs a deliberately dropped event (never one mechanism
   alone).
3. **Recoverable.** Every induced failure is isolated, reason-coded, and retryable
   (auto where safe, one-click where manual) with a named next action; no email-only
   dead ends.
4. **Honest & observable.** The command center answers "OK / what failed / what next";
   freshness labels are truthful; no "real-time" claim over a scheduled path.
5. **Safe.** Any destructive/full-state write (if in scope) is preceded by a
   dry-run/preview; no silent data loss.
6. **Onboardable by a non-developer.** Guided setup + readiness self-test pass before
   first sync; jargon fields carry inline help; raw `ir.cron` internals are hidden.
7. **Secure & scoped.** HMAC verified; credentials masked; admin/functional roles
   enforced; protected-data + 60-day rules respected.
8. **Scale-safe.** Rate-limit-aware pacing and resumable jobs prevent 429 storms and
   request-timeout failures at realistic volumes.
9. **Evaluable.** Open, screenshot-rich docs + a dated changelog (current figures) +
   the built-in self-test exist.
10. **Modular & upgrade-safe.** Isolated from `adams_base`; single-store but
    multi-store-safe keys; no gated decision silently hard-coded.

## Open questions for ChatGPT

**Resolved at RB-13 (DEC-003, 2026-07-01):**

1. ~~**Direction**~~ — **RESOLVED (PR #55-corrected): controlled bidirectional product
   onboarding** — product import **and** controlled product export/update (matched, bound,
   previewed, draft/unpublished/channel-controlled), plus inventory + fulfilment
   write-back. **Customer export deferred** (Phase 2); **unrestricted autonomous
   bidirectional catalog ownership deferred**.
2. ~~**Domain 9 minimum**~~ — **RESOLVED: minimal financial evidence/representation
   only** (status/labels/references/totals/tax/shipping/discount/currency as source info;
   basic gateway/journal mapping as config input if needed); **no accounting automation.**
3. ~~**Refunds/cancellations**~~ — **RESOLVED: deferred** (refund sync, cancellation
   reflection, returns/RMA); idempotent-refund regression mandatory if later included.
4. ~~**Single- vs multi-store / multi-company**~~ — **RESOLVED: single-store,
   single-company MVP** with multi-store-safe keys; multi-tenancy later.
5. ~~**Bulk operations (C-JOB-06)**~~ — **RESOLVED: not a user-facing MVP feature;**
   RB-14/AR-002 internal-only assessment.
6. ~~**Primary MVP persona**~~ — **RESOLVED: P1 (operator) primary; P2 (admin/consultant)
   secondary.**

**Still open — routed to RB-14 architecture (all Not decided / Evidence pending):**

7. **Distribution model (AR-002)** — decides OAuth-mandatory / GraphQL-only /
   App-Store readiness (C-CONN-01, C-DOCS-04) and any **internal** bulk-ops need (C-JOB-06).
8. **Reconciliation cadence/scope** and **per-object vs global freshness** (AR-003/006).
9. **Error/retry taxonomy depth** at MVP and **which ops auto-retry** (AR-006).
10. **Which mappings are "essential"** (C-MAP-03) and the MVP **dedup key set**
    (C-MAP-02) / **match keys** (C-CUST-03) → AR-005.
11. **Readiness/self-test scope** (C-CONN-05) — which checks are essential.
12. **Inventory apply mode** — auto-apply vs review-then-apply (C-INV-04) → AR-007
    (auto-apply not accepted as default MVP behaviour; stays an [Inference]).
13. **Domain 9 draft-artifact exception** — whether any draft invoice/payment artifact is
    absolutely required for a valid Odoo order flow (architecture-dependent; returns to
    ChatGPT before implementation — no silent auto invoice/payment).

## Review notes for ChatGPT

Please inspect carefully:

1. **Thesis & option choice** — is "small but excellent = a correct, observable,
   recoverable single-store loop with **controlled bidirectional product onboarding**" the
   right MVP thesis, and is **Option A** the right choice over B (unrestricted autonomous
   bidirectional catalog) and C (thin pilot)? *(PR #55: product export corrected into MVP,
   controlled.)*
2. **Evidence-consistency gate (DP-006)** — confirm the 8-check review holds: no
   claim→fact (controlled product export/update rests on EM/VT/WK/SH-demonstrated
   evidence; TQ re-check only reinforces, rebaseline pending), config-field≠support (WK
   multi-company/import-stock), auto-apply stays inference (C-INV-04), conditional items
   stay conditional (OAuth/distribution/queue/binding/taxonomy/inventory/fulfilment/
   module-boundaries), and nothing reads as a final architecture decision.
3. **The include/exclude/defer calls** — especially **controlled product export/update in
   MVP** vs **unrestricted autonomous bidirectional catalog ownership deferred**, customer
   export deferred, Domain 9 minimal-evidence-only, refunds/cancellations deferred, bulk
   ops not user-facing.
4. **Architecture-dependent table** — confirm MVP commits *intent* only and no AR row
   is decided; flag any wording that hardens a mechanism.
5. **MVP-critical spine** — endorse or amend the reliability/UX/config/security
   "critical" lists as the non-negotiable core of an excellent MVP.
6. **Acceptance principles** — confirm they are principles (not code-level criteria)
   and cover the classic defects (A-IMP-4).

> **This document records the accepted MVP *product scope* only.** ChatGPT has accepted
> the scope baseline (RB-13, DEC-003, 2026-07-01). All *mechanism* calls remain **inputs**
> for the gated RB-14 (architecture) review, subject to ChatGPT approval (`CLAUDE.md`
> §4–§5, §8–§10). **MVP scope accepted; architecture still gated; implementation
> blocked.**
