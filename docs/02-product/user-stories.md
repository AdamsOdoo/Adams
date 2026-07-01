# User Stories

> The **MVP experience** for the Odoo 19 ↔ Shopify Connector, expressed as
> persona-driven, testable user stories grouped into epics. Companion to
> [`./mvp-scope.md`](./mvp-scope.md) (scope) and
> [`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md) (boundaries).
> These are **product stories, not implementation tasks** — no code-level acceptance
> criteria, no screens, no modules.

## Status

> **Proposed for ChatGPT review — not final until accepted.**

- **Sprint:** Product Sprint F (RB-13). **Phase:** MVP synthesis — **no-code gate in
  force** (`CLAUDE.md` §4–§5). **Decides nothing.**
- **Governance:** every story's MVP relevance is **proposed MVP / later / open** — an
  **input**, not a decision. No architecture, ADR, module, data model, queue
  framework, API strategy, or distribution model is decided.
- **Evidence discipline (DP-003/DP-004/DP-006):** stories trace to demonstrated
  evidence or Tier-1 facts; competitor claims stay claims; conditional items stay
  conditional; improvement inferences (command center, recovery-first, freshness,
  auto-apply) are labelled inference.
- **Dates:** competitor evidence access **2026-06-30**; session **2026-07-01**.

## Purpose

Turn the MVP scope proposal into the **lived experience** of the four personas, so
ChatGPT can sanity-check scope from the user's point of view and so later UI design +
(gated) implementation inherit a shared, testable definition of "what the user can do."
Stories are deliberately **practical and testable at the product level** and are traced
to capability IDs and their architecture gates.

## Evidence base

Same already-merged evidence as [`./mvp-scope.md`](./mvp-scope.md): the capability
evidence map + feature taxonomy (`C-…` IDs, strengths, AR gates), the product vision
(personas, non-negotiables) and setup/UX principles (north star + 12 principles), the
Sprint C research (`O-…`/`A-…`), and Tier-1 facts.

## Persona assumptions

> **[Inference]** — personas are deduced from the evidence (the UX benchmark's admin
> vs functional split; SH's access-gated setup; modularity/trust findings). Not
> validated buyer research; **which persona is the primary MVP target is open (RB-13)**.

- **P1 — Operations / e-commerce user (primary daily user).** Runs and monitors syncs,
  reads logs, recovers from failures; often not a developer.
- **P2 — Odoo administrator / implementation consultant (setup & config owner).**
  Installs, connects, maps fields, sets permissions, tunes sync behaviour.
- **P3 — Business owner / finance stakeholder (economic buyer).** Cares about
  correctness (no double refunds/oversell), trust/evaluability, total cost.
- **P4 — Odoo partner / integrator (deployer & reseller).** Deploys for many clients;
  cares about modularity, isolation, upgrade-safety.

## Story format

Each story uses:

```
### Story ID
- Persona:
- Story: As a <persona>, I want <capability>, so that <outcome>.
- Capability IDs:
- MVP relevance: proposed MVP / later / open
- Evidence strength:
- Acceptance notes:        (observable, product-level — not code)
- Failure/recovery notes:
- Architecture dependency:
- Open questions:
```

> All "proposed MVP" stories are **Proposed MVP inclusion — pending ChatGPT
> acceptance.** Stories whose mechanism is gated are **Architecture-dependent — must
> be resolved in RB-14 before implementation.**

---

## Epic 1 — Store setup and readiness

### US-E1-01
- Persona: P2
- Story: As an Odoo administrator, I want a guided in-product setup that connects my
  Shopify store securely, so that I reach a working connection without hand-editing
  server config or pasting long scope strings.
- Capability IDs: C-CONN-01, C-CONN-03
- MVP relevance: proposed MVP
- Evidence strength: B / A-if-public (VT [Demonstrated]; Shopify public-app rule)
- Acceptance notes: a step-by-step flow ends in a confirmed connection; no manual
  scope-string paste is the only path; the getting-started guide is never gated.
- Failure/recovery notes: a failed connection shows a clear reason and a retry, not a
  stack trace.
- Architecture dependency: **AR-002** (auth style OAuth vs token) — **Architecture-
  dependent**; step content follows the distribution decision.
- Open questions: distribution model (AR-002) fixes OAuth-mandatory.

### US-E1-02
- Persona: P2
- Story: As an Odoo administrator, I want my Shopify credentials stored masked, so that
  secrets are never exposed in the UI or logs.
- Capability IDs: C-CONN-02
- MVP relevance: proposed MVP
- Evidence strength: B (VT [Demonstrated])
- Acceptance notes: credentials display masked; secrets do not appear in logs or
  exports.
- Failure/recovery notes: rotating a credential is possible via reconnect (US-E1-05).
- Architecture dependency: none.
- Open questions: none.

### US-E1-03
- Persona: P1, P2
- Story: As an operator, I want a one-click "test connection", so that I get an
  unambiguous pass/fail before I rely on the store.
- Capability IDs: C-CONN-04
- MVP relevance: proposed MVP
- Evidence strength: B (WK/SH [Demonstrated])
- Acceptance notes: a discrete action returns pass/fail with a reason on failure.
- Failure/recovery notes: failure names the cause (bad token, wrong URL) and links to
  reconnect.
- Architecture dependency: none.
- Open questions: none.

### US-E1-04
- Persona: P2, P3
- Story: As an administrator (and reassured buyer), I want a readiness/self-test that
  checks known failure modes before the first sync, so that predictable problems are
  caught up front, not mid-sync.
- Capability IDs: C-CONN-05, C-FUL-03, C-DOCS-03 (self-test)
- MVP relevance: proposed MVP (MVP version)
- Evidence strength: C (VT scope-check + EM gotcha + [Inference]; partial whitespace)
- Acceptance notes: a pass/fail readiness panel covers (candidate) scopes, HTTPS/
  `web.base.url`, webhook reachability, worker/queue presence, credential validity, and
  fulfilment scope; each check states how to fix a failure.
- Failure/recovery notes: any failing check blocks/warns before first sync with a fix
  hint.
- Architecture dependency: **AR-003** (which prerequisites exist depends on the queue/
  API choice) — **Architecture-dependent**.
- Open questions: which checks are MVP-essential vs later.

### US-E1-05
- Persona: P1, P2
- Story: As an operator, I want to reconnect, re-authorise, or disconnect a store, so
  that I can recover from a store-URL migration or a rotated credential.
- Capability IDs: C-CONN-06
- MVP relevance: proposed MVP
- Evidence strength: B (VT store-URL fix, dated [Demonstrated])
- Acceptance notes: reconnect/disconnect actions exist and restore/clear a working
  connection.
- Failure/recovery notes: a broken connection has an explicit recovery path (never a
  dead end).
- Architecture dependency: none (auth style follows AR-002).
- Open questions: none.

---

## Epic 2 — Product and catalog sync

### US-E2-01
- Persona: P1
- Story: As an operator, I want to import products from Shopify into Odoo, so that my
  catalog exists in Odoo for orders and inventory.
- Capability IDs: C-PROD-01
- MVP relevance: proposed MVP
- Evidence strength: B (EM/VT/SH [Demonstrated]) + Tier-1 API [Fact]
- Acceptance notes: products import incrementally and can be filtered; re-running does
  not create duplicates (idempotent upsert).
- Failure/recovery notes: a failed product is isolated with a reason; the batch
  continues; the failure is retryable.
- Architecture dependency: **AR-002** (API), **AR-005** (binding) — **Architecture-
  dependent**.
- Open questions: confirm import as the MVP product direction.

### US-E2-02
- Persona: P1
- Story: As an operator, I want variants and their options synced, so that real
  multi-variant products are represented correctly.
- Capability IDs: C-VAR-01
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] variant model + EM/VT [Demonstrated])
- Acceptance notes: variants sync within the current Shopify variant model (no 250-cap
  regression); options map correctly.
- Failure/recovery notes: variant-level errors are isolated and reason-coded.
- Architecture dependency: AR-002 — **Architecture-dependent**.
- Open questions: none.

### US-E2-03
- Persona: P1, P3
- Story: As an operator, I want product images and base price/compare-at synced, so
  that product records are complete and order values are correct.
- Capability IDs: C-VAR-02, C-PRICE-01
- MVP relevance: proposed MVP (basic image + base price; pHash dedup excluded)
- Evidence strength: B (EM/VT [Demonstrated]); pHash is [Competitor claim] (excluded)
- Acceptance notes: basic images and base price/compare-at travel with the product;
  advanced media dedup (pHash) is out of MVP.
- Failure/recovery notes: image/media fetch failures are isolated and retryable.
- Architecture dependency: none (basic); scale handling ties to AR-002.
- Open questions: confirm basic image + base price only.

### US-E2-04
- Persona: P1, P2
- Story: As an operator, I want to exclude selected products from sync, so that I can
  scope out discontinued or irrelevant items.
- Capability IDs: C-PROD-04
- MVP relevance: proposed MVP (basic)
- Evidence strength: B (SH/EM [Demonstrated])
- Acceptance notes: an exclude flag keeps items out of sync; the exclusion reason is
  logged.
- Failure/recovery notes: n/a (control, not a sync action).
- Architecture dependency: none.
- Open questions: none.

### US-E2-05
- Persona: P2
- Story: As an administrator, I want to publish Odoo-authored products to Shopify as
  drafts with a preview before any destructive apply, so that I can build catalogs in
  Odoo without risking data loss.
- Capability IDs: C-PROD-02, C-PROD-03, C-PROD-05
- MVP relevance: open (lean defer — Phase 2 "bidirectional catalog")
- Evidence strength: B (VT/EM/SH/WK draft-export); C-PROD-05 safety A [Fact]
- Acceptance notes (if in scope): export creates drafts; a dry-run/preview precedes any
  full-state write (**[Fact]** `productSet` delete-on-omit); channel control available.
- Failure/recovery notes: partial lists are never sent to full-state mutations.
- Architecture dependency: **AR-002, AR-005** — **Architecture-dependent**.
- Open questions: is product export in MVP? (decides C-PROD-05 as mandatory).

---

## Epic 3 — Customer import and matching

### US-E3-01
- Persona: P1
- Story: As an operator, I want customers imported from Shopify, so that orders link to
  the right customer records.
- Capability IDs: C-CUST-01
- MVP relevance: proposed MVP
- Evidence strength: B (EM/VT/SH [Demonstrated]) + Shopify PII rules [Fact]
- Acceptance notes: customers import; on no-PII plans a default-customer fallback
  applies; protected-data rules respected.
- Failure/recovery notes: a failed customer is isolated + reason-coded; the order still
  reconciles via matching (US-E3-02).
- Architecture dependency: none (light); PII handling platform-conditional.
- Open questions: confirm default-customer fallback for no-PII plans.

### US-E3-02
- Persona: P1, P3
- Story: As an operator, I want incoming customers matched to existing Odoo records by
  email (and optionally name/phone), so that I do not create duplicate customers.
- Capability IDs: C-CUST-03, C-MAP-02
- MVP relevance: proposed MVP
- Evidence strength: B (VT normalized matching [Demonstrated])
- Acceptance notes: a customer already in Odoo is matched, not duplicated; match keys
  are documented and explicit.
- Failure/recovery notes: ambiguous matches are surfaced for review, not silently
  merged.
- Architecture dependency: **AR-005** (keys/binding model) — **Architecture-dependent**.
- Open questions: MVP match-key set (email-only vs multi-key).

### US-E3-03
- Persona: P1
- Story: As an operator, I want billing and shipping addresses mapped onto the
  customer/order, so that orders are complete and shippable.
- Capability IDs: C-CUST-04
- MVP relevance: proposed MVP (basic address); deep multi-address/company later
- Evidence strength: C (EM/VT partial [Demonstrated])
- Acceptance notes: basic billing/shipping addresses appear on the order; deep
  multi-address and company mapping are out of MVP.
- Failure/recovery notes: address-mapping issues are logged with a reason.
- Architecture dependency: company mapping ties to multi-company (later, AR-004).
- Open questions: confirm basic-address-only.

### US-E3-04
- Persona: P2
- Story: As an administrator, I want to export/link Odoo customers to Shopify, so that
  Odoo-authored customers exist in the store.
- Capability IDs: C-CUST-02
- MVP relevance: open (lean defer — Phase 2)
- Evidence strength: B (EM link-by-email [Demonstrated])
- Acceptance notes (if in scope): customers are linked by email; no duplicate creation.
- Failure/recovery notes: ownership conflicts are surfaced, not silently overwritten.
- Architecture dependency: **AR-005** — **Architecture-dependent**.
- Open questions: is customer export in MVP?

---

## Epic 4 — Order import and order lifecycle

### US-E4-01
- Persona: P1, P3
- Story: As an operator, I want new Shopify orders imported into Odoo automatically, so
  that fulfilment and accounting can proceed in Odoo.
- Capability IDs: C-ORD-01
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] reconcile required + VT/EM/SH/WK [Demonstrated])
- Acceptance notes: orders arrive via a layered path (webhook + scheduled +
  reconciliation + manual); the same order is never imported twice (idempotent).
- Failure/recovery notes: a missed webhook is caught by reconciliation (US-E7-05); a
  failed order is isolated and retryable.
- Architecture dependency: **AR-003** (orchestration) — **Architecture-dependent**.
- Open questions: none on inclusion; mechanism → RB-14.

### US-E4-02
- Persona: P1, P2
- Story: As an operator, I want to backfill recent historical orders on first connect,
  so that Odoo is not empty on day one.
- Capability IDs: C-ORD-02
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] 60-day `read_all_orders` gate + EM/VT [Demonstrated])
- Acceptance notes: a backfill imports recent orders; the 60-day approval gate is
  surfaced honestly (not hidden); backfill is resumable.
- Failure/recovery notes: an interrupted backfill resumes without duplicating (US-E7-04).
- Architecture dependency: **AR-002** (scope/API); large volumes may need bulk
  (C-JOB-06, open) — **Architecture-dependent**.
- Open questions: backfill window/limits; bulk-ops need.

### US-E4-03
- Persona: P1
- Story: As an operator, I want order, financial, and fulfilment status mapped into
  Odoo, so that imported orders carry a correct, meaningful state.
- Capability IDs: C-ORD-03
- MVP relevance: proposed MVP
- Evidence strength: B (SH matrix + VT [Demonstrated])
- Acceptance notes: Shopify statuses map to a documented Odoo state baseline.
- Failure/recovery notes: unmapped/unknown statuses are logged, not silently dropped.
- Architecture dependency: none (light).
- Open questions: none.

### US-E4-04
- Persona: P1
- Story: As an operator, I want imported orders to move through a sensible Odoo order
  lifecycle, so that they become actionable (confirm, deliver) without manual re-keying.
- Capability IDs: C-ORD-04
- MVP relevance: proposed MVP (basic default; full configurability later)
- Evidence strength: B (VT pipeline + SH [Demonstrated])
- Acceptance notes: a basic, sane default workflow advances orders; each step is an
  isolated, retryable, idempotent job.
- Failure/recovery notes: a failed workflow step is isolated and retryable; it does not
  block other orders.
- Architecture dependency: **AR-003** — **Architecture-dependent**.
- Open questions: how configurable the MVP workflow is.

### US-E4-05
- Persona: P3
- Story: As a finance stakeholder, I want the minimal payment/journal/invoice
  representation the Odoo order flow needs, so that orders are financially actionable
  without a full accounting integration.
- Capability IDs: C-PAY-01, C-PAY-02, C-PAY-03
- MVP relevance: open (lean: minimal representation only; full accounting deferred)
- Evidence strength: B (VT/SH/EM [Demonstrated]); `OrderTransaction` [Fact]
- Acceptance notes (if in scope): the minimal representation is idempotent (no
  double-invoice on retry); full gateway/journal breadth is deferred.
- Failure/recovery notes: retries never create duplicate invoices/payments.
- Architecture dependency: none decided; idempotency required (C-JOB-04).
- Open questions: what is the **minimal** representation the order flow needs?

### US-E4-06
- Persona: P1, P3
- Story: As an operator, I want Shopify refunds and cancellations reflected in Odoo
  safely, so that finance stays consistent without double-refunding.
- Capability IDs: C-RET-01, C-RET-03
- MVP relevance: open (lean defer; **idempotency + irreversible-action warnings
  mandatory if included**)
- Evidence strength: A ([Fact] `@idempotent` refunds 2026-04) / B (VT/EM [Demonstrated])
- Acceptance notes (if in scope): a refund is never applied twice; a cancellation warns
  before irreversible effects and never silently creates a cancel order.
- Failure/recovery notes: refund/cancel retries are idempotent.
- Architecture dependency: **AR-006** — **Architecture-dependent**.
- Open questions: is basic refund/cancellation reflection in MVP? (ties Domain 9).

---

## Epic 5 — Inventory sync and freshness

### US-E5-01
- Persona: P1, P3
- Story: As an operator, I want Odoo stock levels written back to Shopify, so that the
  storefront does not oversell or undersell.
- Capability IDs: C-INV-01
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] `committed` read-only, `@idempotent` set/adjust + EM/VT)
- Acceptance notes: only `available`/`on_hand` are written (never `committed`), and
  writes are idempotent (a repeated sync does not double-apply).
- Failure/recovery notes: a failed quantity write is isolated, reason-coded, retryable.
- Architecture dependency: **AR-007** — **Architecture-dependent**.
- Open questions: confirm write-back direction.

### US-E5-02
- Persona: P2
- Story: As an administrator, I want a clear default for which quantity field is pushed
  (with inline help), so that I ship the right number without deciphering jargon.
- Capability IDs: C-INV-02
- MVP relevance: proposed MVP (sensible default + inline help)
- Evidence strength: B (EM formulas [Demonstrated])
- Acceptance notes: a default quantity field applies; inline help explains
  Forecast vs Free-to-Use.
- Failure/recovery notes: a misconfiguration is visible before it ships wrong numbers.
- Architecture dependency: AR-007.
- Open questions: which default quantity field for MVP.

### US-E5-03
- Persona: P1, P3
- Story: As an operator, I want inventory mapped per location, so that multi-location
  stock is correct and never double-decremented.
- Capability IDs: C-INV-03
- MVP relevance: proposed MVP (location-aware; avoid a wrong single-location design)
- Evidence strength: A ([Fact] InventoryLevel per-location + EM/VT [Demonstrated])
- Acceptance notes: stock maps to ≥1 Shopify location safely; SKU-only writes do not
  double-decrement across locations (A-INV-2).
- Failure/recovery notes: location-mapping gaps are surfaced, not silently guessed.
- Architecture dependency: **AR-007** — **Architecture-dependent**.
- Open questions: minimum multi-location support at MVP.

### US-E5-04
- Persona: P1
- Story: As an operator, I want to import initial/Shopify stock into Odoo with a
  controlled apply, so that I can establish a correct starting stock position.
- Capability IDs: C-INV-04
- MVP relevance: proposed MVP (controlled apply); auto-apply **open**
- Evidence strength: C (EM [Demonstrated]); **auto-apply is [Inference]** (DP-006)
- Acceptance notes: stock imports with a controlled apply/review; **whether apply is
  automatic or reviewed is open** (auto-apply is an improvement inference, not a decided
  behaviour).
- Failure/recovery notes: an apply can be reviewed/reverted before it affects live sync.
- Architecture dependency: **AR-007** — **Architecture-dependent**.
- Open questions: auto-apply vs review-then-apply (do not promote the inference).

### US-E5-05
- Persona: P1, P3
- Story: As an operator, I want honest "last synced / last reconciled" freshness labels
  per data type, so that I trust what I see instead of assuming "real-time".
- Capability IDs: C-SYNC-07
- MVP relevance: proposed MVP
- Evidence strength: E ([Inference] + latency-honesty; competitors overstate real-time)
- Acceptance notes: each data type shows a truthful freshness/latency label; no
  "real-time" claim over a scheduled path.
- Failure/recovery notes: staleness beyond an expected window is visible.
- Architecture dependency: none.
- Open questions: per-object vs global freshness.

---

## Epic 6 — Fulfillment and tracking

### US-E6-01
- Persona: P1
- Story: As an operator, when I fulfil an order in Odoo, I want the fulfilment and
  tracking pushed back to Shopify, so that the storefront and customer see accurate
  shipping status.
- Capability IDs: C-FUL-01
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] FulfillmentOrder + EM/VT/SH [Demonstrated])
- Acceptance notes: fulfilment uses FulfillmentOrder-based mutations (not legacy
  endpoints); tracking number/URL is written back.
- Failure/recovery notes: a failed write-back is isolated, reason-coded, retryable
  (idempotent — no duplicate fulfilment).
- Architecture dependency: **AR-008** — **Architecture-dependent**.
- Open questions: none on inclusion; design → RB-14.

### US-E6-02
- Persona: P2
- Story: As an administrator, I want the connector to verify it has the fulfilment
  scope, so that fulfilment does not fail silently from a missing permission.
- Capability IDs: C-FUL-03
- MVP relevance: proposed MVP (folds into readiness, US-E1-04)
- Evidence strength: A ([Fact] scopes + EM walkthrough [Demonstrated])
- Acceptance notes: a missing fulfilment scope is flagged in the readiness check with a
  fix hint.
- Failure/recovery notes: no silent fulfilment failures from missing scope.
- Architecture dependency: none.
- Open questions: none.

### US-E6-03
- Persona: P1
- Story: As an operator, I want multi-package / multi-location fulfilment, so that split
  shipments report correctly.
- Capability IDs: C-FUL-02
- MVP relevance: later (single-package tracking write-back is MVP)
- Evidence strength: B (EM Put-in-Pack + VT [Demonstrated])
- Acceptance notes (later): split shipments map to per-package/location fulfilments.
- Failure/recovery notes: n/a (later).
- Architecture dependency: AR-008.
- Open questions: none (later).

---

## Epic 7 — Logs, errors, retries, and recovery

### US-E7-01
- Persona: P1
- Story: As an operator, I want reason-coded, per-record, in-app logs, so that I can see
  what synced and exactly why something failed — without reading a stack trace or an
  email.
- Capability IDs: C-OBS-01, C-OBS-02
- MVP relevance: proposed MVP
- Evidence strength: B (EM Log Book / Mismatch Log [Demonstrated])
- Acceptance notes: each failure has a human-readable reason (e.g. "SKU not found");
  successes and failures are distinguishable; an audit trail records sync actions.
- Failure/recovery notes: one bad record never blocks the batch (isolation, A-LOG-2).
- Architecture dependency: none (light).
- Open questions: audit retention policy (minor).

### US-E7-02
- Persona: P1
- Story: As an operator, I want each failure to show the record, the reason, a suggested
  fix, and a retry, so that errors are a recovery surface, not a dead end.
- Capability IDs: C-OBS-03, C-DASH-04
- MVP relevance: proposed MVP (MVP version of the error center)
- Evidence strength: C (synthesis EM+VT+SH; unified by none — [Inference])
- Acceptance notes: an error entry links to its record, states a named cause + fix hint,
  and offers a retry.
- Failure/recovery notes: retrying a fixed error succeeds without side effects
  (idempotent).
- Architecture dependency: **AR-006** (cause/retry taxonomy) — **Architecture-dependent**.
- Open questions: how much of the error center is MVP (basic vs full).

### US-E7-03
- Persona: P1
- Story: As an operator, I want safe manual retry always available, and automatic retry
  for operations that are safe to repeat, so that transient failures recover without
  data loss.
- Capability IDs: C-JOB-02, C-JOB-03, C-JOB-04
- MVP relevance: proposed MVP (safe manual retry always; auto-retry conditional on
  idempotency)
- Evidence strength: A (idempotency [Fact]) / B (VT auto-retry [Demonstrated]) / C
  (classification [Inference])
- Acceptance notes: a manual retry is always available; auto-retry applies only where
  idempotency makes repeating safe; naive double-acting is prevented.
- Failure/recovery notes: retries never double-decrement or double-refund (idempotency).
- Architecture dependency: **AR-006** — **Architecture-dependent**.
- Open questions: which ops auto-retry at MVP.

### US-E7-04
- Persona: P1, P3
- Story: As an operator, I want the connector to survive rate limits and long syncs, so
  that large catalogs/order volumes do not cause 429 storms or timeouts.
- Capability IDs: C-JOB-05, C-JOB-07
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] rate limits / worker limits; **no competitor** addresses
  throttling)
- Acceptance notes: syncs pace against live throttle status and back off on 429; long
  syncs run out-of-band and resume rather than timing out.
- Failure/recovery notes: throttling/backpressure is surfaced honestly, not failed
  opaquely.
- Architecture dependency: **AR-002, AR-003, AR-006** — **Architecture-dependent**.
- Open questions: bulk-ops need for large backfills (C-JOB-06).

### US-E7-05
- Persona: P1, P3
- Story: As an operator, I want scheduled and on-demand reconciliation that detects and
  repairs drift, so that missed webhooks or out-of-order events never leave the systems
  silently out of sync.
- Capability IDs: C-SYNC-06, C-SYNC-02, C-SYNC-03
- MVP relevance: proposed MVP (first-class, even if basic)
- Evidence strength: A ([Fact] delivery not guaranteed; HMAC; webhook-id dedup)
- Acceptance notes: a deliberately dropped event is detected and repaired by
  reconciliation; webhooks are HMAC-verified and de-duplicated by id; "last reconciled"
  is visible.
- Failure/recovery notes: reconciliation is idempotent (repair does not double-apply).
- Architecture dependency: **AR-003, AR-006** — **Architecture-dependent**.
- Open questions: reconciliation cadence/scope (per-object vs global).

---

## Epic 8 — Dashboard / command center

### US-E8-01
- Persona: P1
- Story: As an operator, I want one command center that answers "is everything OK, what
  failed, and what do I do", so that I am not hunting through scattered menus.
- Capability IDs: C-DASH-01, C-DASH-02
- MVP relevance: proposed MVP (basic)
- Evidence strength: C (synthesis SH monitoring + VT diagnostics — [Inference])
- Acceptance notes: a single home shows connection health (traffic-light) and the state
  of the sync loop at a glance.
- Failure/recovery notes: an unhealthy state links to the error center (US-E7-02).
- Architecture dependency: **AR-003** (light — actions enqueue).
- Open questions: admin vs functional-user dashboard split.

### US-E8-02
- Persona: P1
- Story: As an operator, I want an activity timeline with queue and failure counts, so
  that I can see what has been happening and what needs attention.
- Capability IDs: C-DASH-03
- MVP relevance: proposed MVP
- Evidence strength: B (SH activity chart [Demonstrated])
- Acceptance notes: recent activity, queued work, and failure counts are visible.
- Failure/recovery notes: failure counts link through to the failing records.
- Architecture dependency: AR-003 (light — reflects the queue model).
- Open questions: none.

### US-E8-03
- Persona: P1
- Story: As an operator, I want quick actions (sync now, reconcile, retry) from the
  command center, so that I can act immediately without navigating away.
- Capability IDs: C-DASH-05
- MVP relevance: proposed MVP
- Evidence strength: B (EM/SH/VT/WK [Demonstrated])
- Acceptance notes: quick actions **enqueue** work (never run heavy sync inline, 5s ack).
- Failure/recovery notes: an enqueued action reports back into the activity timeline.
- Architecture dependency: **AR-003** (must enqueue) — **Architecture-dependent**.
- Open questions: none.

### US-E8-04
- Persona: P1, P2
- Story: As a new user, I want first-run/empty states that guide me to a first sync, so
  that a cold start is not confusing.
- Capability IDs: C-DASH-06
- MVP relevance: proposed MVP
- Evidence strength: E ([Inference] — UX best-practice; no competitor evidence)
- Acceptance notes: empty states point to the next setup step.
- Failure/recovery notes: n/a.
- Architecture dependency: none.
- Open questions: none.

---

## Epic 9 — Mapping and configuration

### US-E9-01
- Persona: P2
- Story: As an administrator, I want to map the essential fields directionally with a
  dry-run/preview, so that I never map blind or apply destructively by accident.
- Capability IDs: C-MAP-03
- MVP relevance: proposed MVP (essential fields only; custom transforms excluded)
- Evidence strength: B (VT direction+transforms+test [Demonstrated])
- Acceptance notes: essential mappings are directional and previewable; custom Python
  transforms are out of MVP (advanced/later).
- Failure/recovery notes: a preview reveals problems before a destructive apply
  (A-CFG-1).
- Architecture dependency: **AR-004, AR-005** — **Architecture-dependent**.
- Open questions: which mappings are "essential".

### US-E9-02
- Persona: P2
- Story: As an administrator, I want documented, explicit dedup/binding keys, so that
  the connector reliably matches records and prevents duplicates.
- Capability IDs: C-MAP-01, C-MAP-02
- MVP relevance: proposed MVP (documented keys; data model gated)
- Evidence strength: A ([Fact] GID binding + EM/SH/VT [Demonstrated])
- Acceptance notes: dedup keys per object are documented and applied; the Shopify-GID ↔
  Odoo binding is stable and multi-store-safe.
- Failure/recovery notes: deleted-binding handling is defined (not silently
  duplicating).
- Architecture dependency: **AR-005** — **Architecture-dependent — must be resolved in
  RB-14** (binding data model).
- Open questions: `ir.model.data` reuse vs dedicated model; deleted-binding handling.

### US-E9-03
- Persona: P2
- Story: As an administrator, I want friendly scheduling language for background sync,
  so that I configure cadence without touching raw Odoo cron internals.
- Capability IDs: C-SYNC-04, C-MAP-04
- MVP relevance: proposed MVP
- Evidence strength: B (EM/VT/SH/WK/EC [Demonstrated])
- Acceptance notes: schedule reads as "every N minutes" (not `nextcall`); deterministic
  location/gateway routing has a clean fallback; raw `ir.cron` internals are hidden
  (A-UX-2).
- Failure/recovery notes: the manual sync path is always available (staging where crons
  are off).
- Architecture dependency: **AR-003** (orchestration), AR-004 (config model) —
  **Architecture-dependent**.
- Open questions: routing scope (location+gateway only) at MVP.

---

## Epic 10 — Permissions and roles

### US-E10-01
- Persona: P2, P4
- Story: As an administrator/integrator, I want connector settings gated to authorised
  users, so that a functional user can operate day-to-day without admin rights.
- Capability IDs: C-MULTI-03
- MVP relevance: proposed MVP
- Evidence strength: A ([Fact] Odoo security + EM/SH [Demonstrated])
- Acceptance notes: an admin surface (setup/creds/mappings/permissions) is separated
  from a functional surface (run/read/fix) by access rights; access is deny-by-default.
- Failure/recovery notes: a functional user is not blocked from routine recovery
  (retry/read).
- Architecture dependency: security (Odoo-native; not a gated design choice).
- Open questions: admin vs functional dashboard split (with US-E8-01).

### US-E10-02
- Persona: P4
- Story: As an integrator, I want the single-store MVP built with multi-store-safe keys,
  so that adding stores later does not require re-architecting identity.
- Capability IDs: C-MULTI-01
- MVP relevance: proposed MVP (single-store; keys stay multi-store-safe) — full
  multi-store later
- Evidence strength: B (VT [Demonstrated])
- Acceptance notes: binding/config keys are per-store-scoped even though MVP runs one
  store; no multi-store UI/logic is built.
- Failure/recovery notes: n/a (design property).
- Architecture dependency: **AR-004, AR-005** — **Architecture-dependent**.
- Open questions: confirm single-store MVP with multi-store-safe keys.

### US-E10-03
- Persona: P3, P4
- Story: As a buyer/integrator, I want open, screenshot-rich docs, a dated honest
  changelog, and a built-in self-test, so that I can evaluate and trust the connector
  without a sales gate.
- Capability IDs: C-DOCS-01, C-DOCS-02, C-DOCS-03 (self-test)
- MVP relevance: proposed MVP (quality requirement) — public demo/marketplace later
- Evidence strength: B (EM honest docs + VT dated release notes [Demonstrated])
- Acceptance notes: docs are open (never gated), screenshot-rich; the changelog is
  dated and cites current platform figures (DP-001); the self-test is available.
- Failure/recovery notes: n/a.
- Architecture dependency: none (public App-Store/demo packaging is distribution-gated,
  AR-002 — later).
- Open questions: self-test scope.

---

## Later-phase epics

Story-level detail deferred; scope in
[`./non-mvp-and-later-phases.md`](./non-mvp-and-later-phases.md):

- **Epic L1 — Bidirectional catalog & customers** (product/customer export, publish/
  channel): C-PROD-02/03/05, C-CUST-02. MVP relevance: later/open.
- **Epic L2 — Financial depth** (full payments/invoicing, refunds, cancellations,
  returns/RMA): C-PAY-01/02/03, C-RET-01/02/03. MVP relevance: later/open.
- **Epic L3 — Payout reconciliation** (Shopify-Payments-gated): C-POUT-01/02. later.
- **Epic L4 — Premium breadth (optional add-ons)** (Markets/B2B/POS/gift cards/
  metafields/extended): C-ADV-01…06, C-PRICE-02/03, C-VAR-03/04. later.
- **Epic L5 — Multi-tenancy** (multi-store, multi-company, isolated config model):
  C-MULTI-01 (full), C-MULTI-02, C-MULTI-04. later.
- **Epic L6 — Scale & analytics** (bulk ops, custom transforms, dedicated analytics/
  reporting): C-JOB-06, C-MAP-03 (transforms), C-RPT-01/02. later/open.

## Acceptance principles

Story acceptance is judged at the **product level** (mirrors
[`./mvp-scope.md`](./mvp-scope.md) "MVP acceptance principles"; **not** code-level
criteria):

1. **Testable behaviour, not implementation.** Each story's acceptance notes describe
   observable behaviour a reviewer can check, not code.
2. **Correct under failure.** Stories that touch inventory/orders/refunds/fulfilment
   must hold under the classic-defect scenarios (A-IMP-4: duplicate orders,
   multi-location double-decrement, missed-webhook reconciliation, idempotent refunds,
   timezone/paging).
3. **Recoverable.** Every failure path names isolation + reason + retry (no dead ends).
4. **Honest & observable.** Freshness is truthful; status answers "OK / what failed /
   what next".
5. **Safe.** Destructive/irreversible actions (if in scope) require preview/warning.
6. **Approachable.** Setup/readiness pass before first sync; jargon carries inline help.
7. **Secure & scoped.** HMAC, masked creds, role gating, protected-data/60-day rules.

## Open questions

1. **Primary MVP persona** (P1 operator vs P2 admin/consultant) to bias UX priority.
2. **Direction** — are the "open" export stories (US-E2-05, US-E3-04) in MVP or Phase 2?
3. **Domain 9 minimum** (US-E4-05) and **refunds/cancellations** (US-E4-06) — in MVP or
   deferred?
4. **Distribution (AR-002)** — fixes OAuth-mandatory (US-E1-01) and App-Store/demo
   packaging (US-E10-03).
5. **Reconciliation cadence & freshness granularity** (US-E7-05, US-E5-05).
6. **Error/retry taxonomy depth & auto-retry set** (US-E7-02/03).
7. **Essential mappings & dedup/match keys** (US-E9-01/02, US-E3-02) → AR-005.
8. **Readiness/self-test check set** (US-E1-04).
9. **Bulk ops for backfill** (US-E4-02/US-E7-04) → C-JOB-06.

## Review notes for ChatGPT

Please inspect carefully:

1. **Experience coverage** — do the 10 MVP epics fully express the "correct, observable,
   recoverable single-store loop, import-first" experience without gaps or over-reach?
2. **Story ≠ implementation task** — confirm stories stay product-level (no code-level
   acceptance criteria, no screens/modules).
3. **MVP relevance tags** — confirm the **open** stories (US-E2-05, US-E3-04, US-E4-05,
   US-E4-06) are the right scope forks left to you, and the **later** tags are correct.
4. **Evidence discipline** — confirm each story traces to demonstrated/Tier-1 evidence;
   inferences (command center, error center, freshness, auto-apply) stay inference; no
   claim is promoted to a fact.
5. **Architecture-dependent tags** — confirm stories commit *intent*, and no story
   hard-codes a gated mechanism (queue, binding model, API, distribution).
6. **Personas** — confirm P1–P4 usage is reasonable and "primary MVP persona" is
   correctly left open.

> **This document decides nothing.** All stories, epics, and MVP-relevance tags are
> **inputs** for the gated RB-13 (MVP) and RB-14 (architecture) reviews, subject to
> ChatGPT approval (`CLAUDE.md` §4–§5, §8–§10). **Proposed for ChatGPT review — not
> final until accepted.**
