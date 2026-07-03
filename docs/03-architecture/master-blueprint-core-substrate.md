# Master Blueprint — Part A: Core / Common Substrate

> **Master Blueprint Sprint A deliverable** for the premium **Odoo 19 ↔ Shopify
> Connector**. Detailed, implementation-ready **blueprint** for the
> `shopify_connector_core` common substrate — still **documentation only, no
> code**. Companion index:
> [`master-blueprint.md`](./master-blueprint.md). Companion open-questions
> register:
> [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).
> Companion decision record:
> [`../04-decisions/DEC-013-master-blueprint-core-substrate.md`](../04-decisions/DEC-013-master-blueprint-core-substrate.md)
> (Status: **Accepted by ChatGPT**, 2026-07-03).

## Status

**Accepted through DEC-013.** Acceptance date: **2026-07-03.**
Documentation only — the no-code gate (`CLAUDE.md` §4–§5) is in force.
**This blueprint does not authorize implementation**, and its acceptance
does not open the implementation gate (that remains a separate ChatGPT
approval per `../05-qa/quality-feedback-loop.md` §10). Blueprint
proposals accepted by DEC-013 are now **[Accepted — DEC-013]**; open
questions this record raised remain open per
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
(notably MBQ-04, MBQ-08, MBQ-53, MBQ-54).

## Claim labels used throughout

- **[Accepted — DEC-0XX]** — restates an already-accepted decision, cited.
  Not re-litigated here.
- **[Blueprint proposal]** — a blueprint-level design detail introduced by
  this sprint, converting accepted decisions into implementable shape.
  Binding only if ChatGPT accepts DEC-013.
- **[Inference]** — reasoning from cited accepted decisions/evidence.
- **[Open question — MBQ-nn]** — unresolved; carried in
  [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
  under the referenced ID. Must be resolved (or consciously accepted as open)
  before the affected implementation task is written.

**Naming discipline:** all model/field/group names in this document are
**proposed naming directions only — not committed Odoo identifiers**. Exact
model names, field names, XML IDs, and access CSV rows remain
**[Open question — MBQ-01/02/03/44]** for implementation planning.

---

## A. Module boundary — `shopify_connector_core`

### A.1 Name and position

- **Proposed module name:** `shopify_connector_core`
  **[Accepted — DEC-008 "Phase 1 addon family"]**. The name itself was fixed
  by DEC-008; this blueprint does not rename it.
- Bottom of the dependency DAG: `core` depends on **no other connector
  module** and **not on `adams_base`** **[Accepted — DEC-008 "Dependency
  rules"]**. It may depend only on Odoo core/base framework modules needed
  for its substrate role (exact Odoo `depends` list is
  **[Open question — MBQ-01]**, implementation planning).

### A.2 Responsibilities (what `core` owns)

Per DEC-008's accepted `core` row, plus the DEC-010/DEC-011 acceptance
ratification, `shopify_connector_core` owns:

1. **Store/connection configuration + credential posture** (§B.1–§B.2)
   **[Accepted — DEC-008]**.
2. **GraphQL transport client + rate-limit/cost-aware pacing** — the single
   place any connector module talks to Shopify **[Accepted — DEC-008;
   DEC-004]**.
3. **Webhook receiver + HMAC verification + `X-Shopify-Webhook-Id` dedup**
   **[Accepted — DEC-008; DEC-005]**.
4. **Queue/job abstraction + `ir.cron` worker(s)** — the internal
   cron-backed queue (§D) **[Accepted — DEC-008; DEC-005]**.
5. **Binding abstraction / shared contract** (§C) — store scoping, audit
   fields, status vocabulary, uniqueness principles **[Accepted — DEC-008]**.
6. **Error-class registry** — the DEC-009 16-class taxonomy as a single
   shared registry (§D.4) **[Accepted — DEC-008; DEC-009]**.
7. **Setup/readiness wizard** (§E) **[Accepted — DEC-008]**.
8. **Recovery-first dashboard / log / error center** (§F–§H)
   **[Accepted — DEC-008]**.
9. **Minimal Shopify Location reference/cache** (§B.4) — Shopify-side
   reference data only, never Odoo-location IDs or mapping decisions
   **[Accepted — DEC-010/DEC-011 acceptance note, ratified against
   DEC-008]**.
10. **Configuration / feature-flag mechanism** (§I) — the per-store
    domain-enablement and capability-flag substrate **[Blueprint proposal —
    DEC-008 routed the mechanism to this blueprint]**.
11. **Connector security groups / role substrate** (§J) — the four
    conceptual DEC-012 roles as connector-wide groups defined once in `core`
    **[Blueprint proposal]**.

### A.3 What `core` must NOT own

- **Any domain business logic or domain sync flow** — product/variant
  import/export, customer matching, order import, inventory writes,
  fulfillment writes all live in their domain modules
  **[Accepted — DEC-008]**.
- **Odoo-location ↔ Shopify-Location mapping** — owned solely by
  `shopify_connector_inventory`; core's Location reference must never store
  Odoo-location IDs or any mapping decision **[Accepted — DEC-010/DEC-011]**.
- **Foreign keys to domain-specific tables** — core stays domain-agnostic;
  it must never reference a product/sale/inventory/fulfillment model
  directly **[Accepted — DEC-008 "Risks and mitigations" #2]**.
- **Domain-specific concrete binding tables** — core owns the binding
  *contract*; concrete per-domain binding models live in domain modules
  (§C.8, the preferred shape proposed by this blueprint).
- **Any dependency on `adams_base` or other customer/base code**
  **[Accepted — DEC-008; CLAUDE.md §9]**.

### A.4 Who depends on `core`

`shopify_connector_product` (directly); `shopify_connector_sale` and
`shopify_connector_inventory` (via `core` + `product`);
`shopify_connector_fulfillment` (via `core` + `sale`). Strict one-directional
DAG; `fulfillment` never depends on `inventory` **[Accepted — DEC-008
"Dependency rules"]**. Cross-module extension rules are in §K.

### A.5 Extension rules (how domain modules extend `core`)

**[Blueprint proposal]** — domain modules extend core only through these
seams, never by patching core internals:

1. **Binding contract extension** — inherit/implement the core binding
   abstract contract with a domain-specific concrete binding model (§C.8).
2. **Job-type registration** — register domain job handlers with the core
   queue (a declared job type + handler entry point); the core worker
   dispatches by job type without importing domain logic.
3. **Error-class mapping** — map domain failures into the fixed DEC-009
   16-class registry; domain modules do **not** add new top-level error
   classes without a DEC-level change (§D.4).
4. **Settings/flag contribution** — contribute per-domain enablement flags
   and capability flags to the core per-store settings concept (§I), rather
   than inventing a per-domain settings mechanism.
5. **Dashboard/error-center contribution** — contribute domain exception
   categories (e.g. inventory mismatch, unmatched picking) as data the core
   surfaces render; domain modules do not build parallel dashboards
   (RA-013 applies).
6. **Setup-wizard step contribution** — contribute domain-specific setup
   steps/guards (e.g. inventory first-push scheduling) into the core wizard
   flow (§E), not separate per-domain wizards.
7. **Webhook-topic registration** — `core` owns the webhook
   receiver/HMAC-verification/dedup/enqueue substrate (§D.1); domain modules
   **register their supported webhook topics** and map each to a domain job
   type (seam 2, above) — `core` does not interpret the domain semantics of
   any webhook payload, and no domain module implements a parallel webhook
   receiver **[Blueprint proposal]**.

---

## B. Core configuration objects

Blueprint-level model **concepts** — not schemas. Exact model/field names:
**[Open question — MBQ-01/02]**.

### B.1 Store / connection

- **Purpose:** represent the one connected Shopify store (Phase 1
  single-store, keys multi-store-safe) and its lifecycle state
  **[Accepted — DEC-003; DEC-004]**.
- **Key fields (conceptual):** store display name; Shopify shop domain
  (`*.myshopify.com` identity); connection state — `setup_incomplete` /
  `connected` / `reconnect_needed` / `disconnected` **[Blueprint proposal,
  from DEC-012 store-settings states]**; targeted Shopify API version
  (§B.3); API health state (§B.3); webhook readiness state; last
  test-connection result (pass/fail + timestamp + reason); enabled-domain
  flags (§I); source-of-truth settings references (§B.6); notification
  default (§B.7); setup-completion markers per wizard step (§E.4).
- **Uniqueness / identity:** one record per connected Shopify store; the
  shop domain is unique per database **[Blueprint proposal]**. Every other
  connector record carries a reference to this store record as its scoping
  dimension **[Accepted — DEC-006]**.
- **Who can view/edit:** Connector Administrator configures; Operator,
  Reviewer, and Auditor view status only (§J). Per-store isolation is
  enforced by explicit store scoping + record rules, never `sudo()`
  **[Accepted — DEC-004/005/006]**.
- **Audit/logging:** connection-state transitions (connected, disconnected,
  reconnect events), setup-step completions, and settings changes are
  logged with who/when **[Accepted — DEC-009 audit requirements, applied]**.
- **Open questions:** store-disconnect data-retention posture
  **[Open question — MBQ-08]**; exact model/field names
  **[MBQ-01/02]**.

### B.2 Credential / secure credential posture

- **Purpose:** hold the DEC-004 offline-token custom-app credential safely.
- **Posture (blueprint level):** the credential is stored **masked**, behind
  **field-level `groups`** restricted to the Connector Administrator role;
  it is **never logged**, never returned in plaintext by any UI after entry,
  and never displayed again after save — the UI shows only *presence +
  last-validated timestamp + rotation state*, not the value
  **[Accepted — DEC-004; DEC-012 store settings §3]**.
- **Key fields (conceptual):** masked token storage; token variant marker
  (non-expiring vs expiring-with-rotation, if the expiring variant is ever
  selected); granted-scopes snapshot (as last verified); last-validated
  timestamp; credential status (present / invalid / revoked).
- **Uniqueness / identity:** one active credential per store connection
  **[Blueprint proposal]**; replacing a credential is a logged
  reconnect/rotation event, not an edit-in-place of history.
- **Who can view/edit:** Administrator can enter/replace/rotate — but
  **cannot read the stored value back**; all other roles see masked status
  only (§J) **[Accepted — DEC-004; Blueprint proposal for the
  no-read-back rule]**.
- **Audit/logging:** credential entry, replacement, rotation, validation
  attempts, and revocation are logged (who/when/outcome) **without ever
  logging the credential value** **[Accepted — DEC-004]**.
- **Open questions:** exact encryption/storage-at-rest mechanism (Odoo
  field-level protection alone vs additional encryption) —
  **[Open question — MBQ-04]**, must be resolved with ChatGPT before any
  credential-handling code; exact custom-app creation surface and
  token-acquisition mechanics **[Open question — MBQ-05, from DEC-004]**.

### B.3 Shopify API version / health status

- **Purpose:** make the targeted Shopify API version explicit and surface an
  honest, named API health state **[Accepted — DEC-004 UX implications]**.
- **Key fields (conceptual):** pinned/targeted Shopify Admin GraphQL API
  version per store; last-seen GraphQL cost/throttle signal; health state —
  `normal` / `throttled` / `degraded` **[Blueprint proposal, from the
  illustrative states in DEC-012 store settings §2; the accepted
  requirement is DEC-004's "honest, named health indicator", not a fixed
  three-state vocabulary]**; health-state reason (plain language, e.g.
  "Shopify is rate-limiting requests").
- **Uniqueness / identity:** attribute of the store connection (§B.1), not
  a standalone entity **[Blueprint proposal]**.
- **Who can view/edit:** health is system-written, read-only for all roles;
  the pinned API version is Administrator-visible; whether operators can
  change it at all is implementation planning **[Blueprint proposal]**.
- **Audit/logging:** health-state transitions logged; throttle events feed
  the job queue's pacing (§D), not user-facing raw cost numbers
  **[Accepted — DEC-004 ("honest, named health indicator, not a raw
  error")]**.
- **Open questions:** API-version pinning/upgrade policy
  **[Open question — MBQ-52]**; exact cost-aware pacing parameters
  **[MBQ-51]**.

### B.4 Shopify Location reference / cache

- **Purpose:** a minimal, shared, Shopify-side Location reference so any
  module (notably `fulfillment`) can name/verify a Shopify Location without
  depending on `inventory`'s mapping table **[Accepted — DEC-010/DEC-011
  acceptance note, ratified against DEC-008]**.
- **Key fields (conceptual):** store reference; Shopify Location GID;
  location name; active/status where available; last-synced/seen metadata
  **[Accepted — DEC-010 "Location mapping posture"]**.
- **Invariants (structural):** never stores Odoo-location IDs; never stores
  any Odoo↔Shopify mapping decision — otherwise it becomes a second,
  competing mapping table; Odoo↔Shopify mapping remains inventory-owned
  **[Accepted — DEC-010/DEC-011]**.
- **Uniqueness / identity:** unique per `(store, Shopify Location GID)`
  **[Blueprint proposal, extending DEC-006's per-store uniqueness
  principle]**.
- **Who can view/edit:** system-maintained (refreshed from Shopify);
  read-only for all roles; no manual edit path **[Blueprint proposal]**.
- **Audit/logging:** refresh runs logged as jobs (§D); newly appearing /
  disappearing Shopify Locations surface as review-worthy log entries, not
  silent cache changes **[Blueprint proposal, consistent with DEC-006
  stale-handling discipline]**.
- **Open questions:** stale-cache handling, refresh cadence, and precedence
  vs a live FulfillmentOrder `assignedLocation` read (live read treated as
  authoritative for a specific fulfillment operation unless proven
  otherwise) **[Open question — MBQ-43, from DEC-010/DEC-011]**.

### B.5 Feature / domain enablement settings

Covered in full in §I (the DEC-008-routed mechanism). Summary concept: a
per-store record of which connector domains are enabled and which
capability flags are set, owned by `core`, extended by domain modules.

### B.6 Source-of-truth settings

- **Purpose:** persist the explicit source-of-truth choices the accepted
  decisions require, so no sync ever runs against an implicit default
  **[Accepted — DEC-006 (product first-sync strategy); DEC-007 §3 (price);
  DEC-007 §4 / DEC-010 (inventory first-push source-of-truth)]**.
- **Key fields (conceptual):** per store — product first-sync source
  strategy (Shopify-source / Odoo-source / both-match-first); price
  source-of-truth (Odoo-authoritative / Shopify-authoritative); inventory
  source-of-truth decision record(s) at the first-push granularity
  eventually chosen (granularity itself **[Open question — MBQ-33]**).
- **Uniqueness / identity:** one current value per store per setting;
  historical values preserved in the audit trail, not overwritten silently
  **[Blueprint proposal]**.
- **Who can view/edit:** Administrator edits; editing after first sync
  carries an explicit warning (a meaningful behaviour change, not a
  cosmetic toggle) **[Accepted — DEC-012 store settings §5]**; all roles
  can view.
- **Audit/logging:** every change logged with who/when/old→new; the
  recorded inventory source-of-truth is shown on the binding/audit trail
  **[Accepted — DEC-007 §4; DEC-009 audit requirements]**.
- **Open questions:** exact configuration surface per setting
  **[MBQ-02/07]**.

### B.7 Notification default settings

- **Purpose:** persist the fulfillment customer-notification default —
  **off unless explicitly enabled/confirmed** **[Accepted — DEC-007 §5;
  DEC-011; RA-009]**.
- **Key fields (conceptual):** per-store notification default (off by
  default, never pre-checked on); note that the decision is **also
  persisted per job at enqueue time** so retries never re-read a changed
  default (§D.9) **[Accepted — DEC-011 "Customer notification posture"]**.
- **Uniqueness / identity:** one current default per store; per-order
  override granularity remains open **[Open question — MBQ-41, DEC-007's
  own fork]**.
- **Who can view/edit:** Administrator edits (an explicit, visible opt-in
  action); Operator/Reviewer/Auditor view **[Accepted — DEC-007 §5;
  DEC-012]**.
- **Audit/logging:** default changes logged; every fulfillment log entry
  records whether notification was requested/suppressed
  **[Accepted — DEC-011]**.

---

## C. Binding / identity abstraction

### C.1 Purpose

One auditable, store-scoped source of truth for cross-system identity,
shared as a **contract** by every domain **[Accepted — DEC-006;
DEC-008]**. The binding is a correctness requirement, not a convenience —
a wrong or missing binding turns `productSet`'s delete-on-omit behaviour
into data loss **[Accepted — DEC-004/DEC-006 evidence]**.

### C.2 Store-scoped uniqueness

Per-store uniqueness on **`(store, Shopify GID)`** and on
**`(store, Odoo model, Odoo record)`** — multi-store-safe even in the
single-store MVP **[Accepted — DEC-006]**. Domain-specific identity shapes
extend, never weaken, this rule (e.g. inventory:
`(store, inventory_item_id, location_id)` **[Accepted — DEC-010]**).

### C.3 Identity fields

Every binding stores explicitly (never inferred, never looked up
indirectly) **[Accepted — DEC-006]**:

- the **Shopify GID** (and domain-specific Shopify identifiers where the
  shape differs — e.g. `inventory_item_id` + `location_id`;
  FulfillmentOrder/Fulfillment GIDs);
- the **Odoo model + record reference**;
- the **store reference** (§B.1).

GID permanence is **not asserted** by Shopify — bindings must handle
deleted/recreated counterparts defensively (§C.6)
**[Accepted — DEC-006, grounded in RB-14 Part 2]**.

### C.4 Binding status and match provenance

- **Status vocabulary (conceptual):** `active` / `stale` /
  `manually_overridden`, plus a `review` state for ambiguous/duplicate-risk
  candidates pending operator resolution **[Accepted — DEC-006 audit/status
  fields; Blueprint proposal for the explicit `review` state]**.
- **Match key used:** recorded per binding — which key produced the match
  (existing binding / SKU-internal reference / barcode / email-customer key
  / manual) **[Accepted — DEC-006]**.
- **Manual override fields:** who overrode and when — an explicit operator
  action with a visible audit trail **[Accepted — DEC-006 UX
  implications]**. Recording **what the automatic candidate was before
  override** is a blueprint extension of that accepted requirement, not
  itself DEC-006 text **[Blueprint proposal]**.
- **Audit fields:** matched-by, matched-at, source strategy (the first-sync
  source-of-truth in force), match key used, status
  **[Accepted — DEC-006 "Mitigations" #2]**.

### C.5 Match-key priority (structural, not configurable)

Existing binding → SKU/internal reference → barcode →
email/customer keys (customers only) → manual match. **Name is advisory
only, never an automatic match key — structurally excluded, not a
configuration default** **[Accepted — DEC-006; RA-006]**. Ambiguous
matches route to manual review, never an automatic guess. Duplicate
prevention preview ("will create N, link M, N ambiguous") precedes every
create/bind — no blind create **[Accepted — DEC-006; DEC-003]**.

### C.6 Stale / deleted / recreated counterpart handling

- A binding whose Shopify counterpart is deleted is marked **stale** —
  never silently dropped, never silently re-created
  **[Accepted — DEC-006]**.
- A new Shopify ID for a "same" SKU/entity must not silently hijack or
  duplicate an existing binding — it surfaces as a **review item**
  (§H manual-review sub-reasons: binding conflict / duplicate risk)
  **[Accepted — DEC-006; DEC-009]**.
- The binding is authoritative over volatile keys: if a SKU/barcode changes
  after binding, the binding remains authoritative and the key change is
  detected/reconciled, not silently re-matched **[Accepted — DEC-006]**.

### C.7 Why not `ir.model.data` as primary

`ir.model.data` has `UniqueIndex('(module, name)')` and no per-store
dimension, no binding-status/audit fields, and module-lifecycle
(`module`/`noupdate`) semantics — rejected as the primary binding/dedup
mechanism (**RA-005**, binding final) **[Accepted — DEC-006]**. This
blueprint does not revisit that rejection; its revisit condition is not
met.

### C.8 How domain modules extend/reuse the binding — accepted shape

**[Accepted — DEC-013, resolving MBQ-11]** — this resolves, at blueprint
level, the schema-shape fork DEC-006/DEC-008 explicitly left to the Master
Blueprint:

- `core` defines an **abstract binding contract** (conceptually an
  abstract model/mixin): store reference, Shopify GID field(s), Odoo
  record reference, status vocabulary, audit fields, uniqueness principles,
  and the stale/review handling behaviours above.
- Each domain module defines its **own concrete binding model** extending
  that contract: product-template binding and product-variant binding in
  `product`; customer binding and order binding in `sale`; inventory-level
  binding (`store, inventory_item_id, location_id`) in `inventory`;
  FulfillmentOrder/Fulfillment binding in `fulfillment`.
- **Rationale [Inference]:** the domain identity shapes are materially
  different (per-location inventory identity; operation-scoped fulfillment
  identity), DEC-006 flagged that a generic polymorphic table must not
  force expensive joins at reconciliation scale, and DEC-008 already places
  binding *responsibility* with each domain module — per-domain concrete
  tables extending one core contract satisfy all three while keeping one
  consistent audit/status shape (RA-013 is not violated: the *abstraction*
  is shared, only the concrete tables are per-domain).
- The **single polymorphic table** option (DEC-006 Option B) is **not
  chosen**, per DEC-013's acceptance, but remains **not entered as a
  rejected approach** — a future architecture review could still revisit
  it if warranted; per-domain concrete tables extending one core
  abstract contract are the accepted direction. **MBQ-11 is resolved by
  DEC-013's acceptance** of this direction.
- **Cross-domain enumeration / registration seam** — because core-level
  operations (e.g. store-disconnect data-retention review, store history
  preservation, a global binding/search view, or a cross-domain audit
  surface) may need to enumerate bindings **across** domains without
  owning their concrete tables, the core binding contract must include an
  **enumeration/registration seam**: each domain binding model registers
  its binding type with `core` and exposes a common minimal read interface
  (at least: count, list-by-store, and status-by-store) that `core` calls
  without importing the domain model directly. This does **not** mean
  `core` owns concrete domain binding tables, and it does **not**
  reintroduce a single polymorphic binding table — it gives `core` a
  read-only, domain-agnostic way to ask "what bindings exist for this
  store," which the per-domain-table shape above would otherwise lack
  **[Blueprint proposal]**.
- **Binding-model granularity bound** — to avoid binding-model explosion,
  the default is **one concrete binding model per synchronized root
  entity** (product template, product variant, customer, order, inventory
  level, FulfillmentOrder/Fulfillment — as listed above). Any **additional
  sub-entity** binding model (a finer-grained identity below one of these
  roots) requires **explicit architecture review** before being added, not
  an ad hoc addition during implementation **[Blueprint proposal]**.
- Convenience reference fields on business records (e.g. a Shopify-ID field
  on the product form) remain **read-only caches updated from the binding,
  never written independently** **[Accepted — DEC-006]**.

---

## D. Job / queue / log / error abstraction

### D.1 Queue posture

Internal, cron-backed queue owned by `core` **[Accepted — DEC-005;
DEC-008]**:

- Webhook receiver verifies HMAC-SHA256 of the raw body, acknowledges
  fast, dedupes on `X-Shopify-Webhook-Id`, and **enqueues** — heavy work
  never runs inline in an HTTP request **[Accepted — DEC-005]**.
- **An `ir.cron` job, or a small number of `ir.cron` jobs**, drains the
  queue in batches with per-record isolation (savepoints) and partial-batch
  commits; `ir.cron`'s own deactivation math is **not** the connector's
  retry mechanism **[Accepted — DEC-005]**. (Wording follows DEC-005's own
  "`ir.cron` job (or a small number of them)" phrasing — this is an Odoo
  scheduled-action drain loop, not an HTTP worker process and not OCA
  `queue_job`'s Jobrunner.)
- Manual sync triggers and scheduled reconciliation are first-class,
  always-on layers — never webhook-only **[Accepted — DEC-005]**.
- OCA `queue_job` remains a documented optional later/on-prem accelerator,
  not the default (RA-004 unchanged) **[Accepted — DEC-005]**.

### D.2 Job sources

`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`,
`setup_readiness_check`, `export_preview_dry_run` — recorded on every job
**[Accepted — DEC-009]**. `setup_readiness_check` and
`export_preview_dry_run` are structurally read-only/preview-only and are
**not business sync runs** (§E.6) **[Accepted — DEC-012]**.

### D.3 Job states

Non-terminal entry: `draft`, `queued`, `running`. Terminal: `succeeded`,
`failed_final`, `skipped`, `cancelled`. Loop-back: `retry_waiting`,
`failed_retryable`, `blocked_manual_review` (return to `queued` once their
condition resolves). `cancelled` is reachable from
`draft`/`queued`/`retry_waiting` **[Accepted — DEC-009]**.

### D.4 Error classes

The fixed 16-class registry **[Accepted — DEC-009]**: Shopify
throttling/rate-limit; Shopify temporary/server/network; Shopify
permission/scope/auth; Shopify userErrors/validation; Odoo
validation/configuration; mapping missing; ambiguous match; binding
conflict; duplicate risk; destructive-write guard blocked; inventory
location missing; fulfillment notification confirmation missing; financial
total mismatch; data shape/schema mismatch; concurrency/race conflict;
unknown/system error. The registry lives once in `core`; domain modules
**map into it**, they do not fork it (§A.5.3) **[Blueprint proposal]**.

### D.5 Retry eligibility concept

Per DEC-009's classified retry policy **[Accepted — DEC-009]**:

1. **Auto-retry with backoff** — throttling/rate-limit; concurrency/race;
   temporary/server/network on **reads** or on **`@idempotent` writes**
   (same persisted key, within the 24-hour window).
2. **Ambiguous-outcome rule** — temporary/network failure on a
   **non-`@idempotent` write** with unknown outcome: **never blind-retried**;
   a safe verification read of Shopify's current state precedes any
   re-attempt, or the job routes to `blocked_manual_review` (RA-014
   applies).
3. **Manual fix then retry** — permission/scope/auth; userErrors/validation;
   Odoo validation/configuration; mapping missing; data shape mismatch.
4. **Operator confirmation required** (`blocked_manual_review`) — ambiguous
   match; binding conflict; duplicate risk; destructive-write guard;
   inventory location missing; fulfillment notification confirmation
   missing.
5. **Conservative, never silent** — financial total mismatch (DEC-007 §6).
6. **Single safety-net auto-retry, then human** — unknown/system error
   `[Implementation-planning default]`.

**`skipped` and `failed_final` are outcomes available from any error
class, not per-class defaults** — `skipped` is reached by operator choice,
`failed_final` by exhausted attempts or manual retries; neither is a
per-class default in the list above **[Accepted — DEC-009 error taxonomy;
DEC-009's job states, restated at D.3]**.

Exact retry ceilings/backoff constants remain
**[Open question — MBQ-16]**.

### D.6 Operation-level idempotency concept

Layered idempotency **[Accepted — DEC-009]**: webhook-ID dedup; store-scoped
binding keys; Shopify `@idempotent` keys (17-mutation fixed list, 24-hour
TTL, persisted and reused on retry); and a **connector-designed
operation-level idempotency key** for everything else. The key concept
generalizes DEC-011's accepted shape to all domains
**[Blueprint proposal]**:

> `(store, operation type, source record, Shopify target ID where known,
> payload version/hash)`

— so two different operations against the same record are never conflated,
and a re-run of the *same* operation is detected connector-side. The
internal key prevents duplicate connector-side *processing*; it never makes
a non-`@idempotent` mutation safe to re-send — the ambiguous-outcome rule
(§D.5.2) closes that gap **[Accepted — DEC-009 "Risks" #5]**. Exact key
schema: **[Open question — MBQ-20]**.

### D.7 Ambiguous outcome handling and serialization

- Verification read before any retry where a safe read exists; otherwise
  `blocked_manual_review` **[Accepted — DEC-009]**.
- **Serialization guard:** operations against the same
  `(store, source record, Shopify target)` are serialized while a prior
  operation against that target is unresolved (ambiguous/manual review) —
  a new or corrected operation must verify current Shopify state or stay
  blocked until the earlier one resolves. Generalized from DEC-011 to a
  core queue behaviour available to all domains **[Accepted — DEC-011;
  Blueprint proposal for the core-level generalization]**. Exact mechanism
  (queue lock / DB constraint / state check):
  **[Open question — MBQ-21]**.

### D.8 Manual review state

`blocked_manual_review` always carries its **specific sub-reason** (one of
the six confirmation-required classes, §D.5.4), the related records, and a
named resolution action; resolving it is a Reviewer-role action recorded
with who/when (§H, §J) **[Accepted — DEC-009; DEC-012]**.

### D.9 Cancellation / supersede concept

- **Cancel** — available from `draft`/`queued`/`retry_waiting`; a cancelled
  job is terminal and logged with who/why **[Accepted — DEC-009 job
  states]**.
- **Supersede** — **[Blueprint proposal]** when a newer operation makes a
  queued/blocked older one obsolete (e.g. a corrected payload), the older
  job is explicitly marked superseded-by (a cancellation variant carrying a
  pointer to the successor), subject to the serialization guard (§D.7) —
  never a silent overwrite. Decisions persisted at enqueue time (e.g. the
  notification flag) are never silently changed on retry
  **[Accepted — DEC-011]**.

### D.10 Audit requirements

What was attempted; **what was actually written** (never assumed from
"attempted"); what was skipped and by whom/what rule; who confirmed
destructive/first-push/notification actions; the recorded source-of-truth
for first-sync/first-push decisions; before/after values for destructive
operations **[Accepted — DEC-009]**.

### D.11 User-facing log shape

Human-readable reason as the primary message (never a stack trace); related
store / Shopify object / Odoo record / binding / job source shown together;
a suggested fix; state-conditional actions (retry / verify / skip /
manual-match — never one generic retry button); honest freshness (the
24-hour dedup window is real, not implied infinite)
**[Accepted — DEC-009; RA-014/RA-015/RA-016]**.

### D.12 Technical detail shape

Raw error/response, error-class code, job/operation identifiers, and the
operator-safe operation reference are available behind an explicit expand
action — secondary, never the primary display
**[Accepted — DEC-009; DEC-012 error center §2]**.

### D.13 Retry safety rules (summary, structural)

- Manual retry uses the **same code path** as automatic retry — no separate
  bypass path **[Accepted — DEC-009 idempotency layers]**.
- Retry never bypasses a guard: a job blocked by the first-push guard,
  notification confirmation, destructive-write guard, or total-check guard
  cannot be retried into execution without the guard being satisfied
  **[Blueprint proposal, from DEC-007/009 guard semantics; see §I.5]**.
- Retry of an `@idempotent` write reuses the **same persisted key** within
  the platform TTL **[Accepted — DEC-009/DEC-010]**.
- Retry preserves the enqueue-time **notification flag** decision — a
  fulfillment job's retry never re-reads a since-changed notification
  default **[Accepted — DEC-011 "Customer notification posture"]**. Retry
  also preserves any **recorded source-of-truth** decision persisted on the
  relevant job/guard record (e.g. the first-push source-of-truth, the price
  source-of-truth) — generalizing this rule beyond fulfillment notification
  to every enqueue-time decision the job/guard record carries
  **[Blueprint proposal, extending DEC-006/DEC-007/DEC-009's
  recorded-decision requirements]**.

---

## E. Setup wizard blueprint

Converts DEC-012 flow §1 into the core wizard blueprint. Owned by `core`
(§A.2.7); domain modules contribute steps (§A.5.6).

### E.1 Steps (blueprint sequence)

1. Welcome / prerequisites — including the up-front Odoo.sh/on-prem hosting
   disclosure (Odoo Online excluded) **[Accepted — DEC-005; DEC-012]**.
2. Store connection — name + shop domain; single store in Phase 1
   **[Accepted — DEC-003/DEC-004]**.
3. Credential entry — guided custom-app credential flow (not one-click
   OAuth); masked entry; plain-language explanation of the custom-app
   model (wizard steps, not approval latency) **[Accepted — DEC-004]**.
4. Scope list presentation — the wizard **presents** the minimal required
   scope list (never free-text) and explains that scopes are granted on the
   Shopify side when creating/authorizing the custom app; the wizard does
   **not** grant scopes itself **[Accepted — DEC-012 §1.3]**.
5. Test connection — a discrete, explicit action reporting pass/fail with a
   reason **[Accepted — DEC-004]**.
6. Readiness checks — pass/fail surface: granted-scope verification,
   HTTPS/`web.base.url` reachability, webhook reachability, worker/queue
   presence, credential validity (candidate list; essential-vs-nice split
   **[Open question — MBQ-06]**) **[Accepted — DEC-004; DEC-012]**.
7. Sync direction choices per domain — bounded to DEC-003's accepted
   directions only; no unsupported direction is offered
   **[Accepted — DEC-003; DEC-012]**.
8. Source-of-truth choices — product first-sync strategy and price
   source-of-truth; a selection is **required**, never defaulted silently
   **[Accepted — DEC-006; DEC-007 §3; DEC-012]**.
9. Notification default — stated in plain language, default **off**, never
   pre-checked on; changing it is an explicit opt-in
   **[Accepted — DEC-007 §5; RA-009]**.
10. Inventory first-push **scheduling** — the wizard may schedule the
    first-push guard for later but must never execute a first push, and
    must never silently skip or auto-complete the guard
    **[Accepted — DEC-007 §4; DEC-010; DEC-012; RA-008]**.
11. Final readiness summary — connection status, enabled domains +
    directions, source-of-truth choices, notification default, and
    first-push-pending state, on one screen before leaving setup
    **[Accepted — DEC-012]**.

### E.2 Test connection

Explicit action; result recorded (pass/fail + timestamp + reason) on the
store record (§B.1) and in the log (§D); job source
`setup_readiness_check` **[Accepted — DEC-004; DEC-009]**.

### E.3 Readiness checks

Run as `setup_readiness_check` jobs through the normal queue — visible,
logged, and re-runnable; results feed the readiness surface and the
dashboard connection-health card **[Accepted — DEC-009; DEC-012]**.

### E.4 Setup-incomplete state

Exiting before completing required steps leaves an explicit
`setup_incomplete` state: the operator sees exactly which steps remain
(never a generic "not configured" error) **[Accepted — DEC-012 §1.11]**.
An incomplete inventory first-push step blocks inventory writes
specifically without blocking product/order sync that does not depend on
it **[Inference — DEC-007 §4 scopes the guard to inventory only; carried
as an Inference in ux-operator-flow.md §1.11, adopted here as a blueprint
rule]**.

### E.5 No business sync/write before setup complete

Structural rule: no business sync/write job is enqueueable-to-run for a
store whose setup is incomplete **[Accepted — DEC-012 safe defaults]**.
Enforced in the queue substrate (not only hidden in the UI) —
**[Blueprint proposal]** the guard is checked at enqueue time and again at
execution time (defense in depth).

### E.6 Readiness/test/preview jobs allowed during setup

`setup_readiness_check` and `export_preview_dry_run` jobs may run during
setup — they are structurally read-only/preview-only and never create or
update any Shopify or Odoo business record **[Accepted — DEC-012 §1
"Readiness/test/preview jobs are not business sync runs"]**.

---

## F. Dashboard / command center blueprint

### F.1 Cards / metrics (conceptual)

Answering "Is everything OK? What failed and why? What do I do next?"
**[Accepted — DEC-012 §3]**:

1. Connection health (state + API health, §B.1/§B.3).
2. Last successful sync **per domain** with mechanism label
   (webhook/scheduled/manual) — never one global timestamp hiding a stalled
   domain; honest freshness **[Accepted — DEC-005; DEC-012]**.
3. Failed jobs **by severity meaning**: needs manual review / system will
   auto-retry / permanently failed **[Accepted — DEC-009; DEC-012]**.
4. Manual-review count (`blocked_manual_review`, with sub-reason
   breakdown).
5. Retry-waiting count (`retry_waiting`) — "the system has this" distinct
   from "you must act".
6. First-push-pending count (inventory guard not yet completed)
   **[Accepted — DEC-012 §3.6]**.
7. Inventory exceptions (location-missing / ambiguous / quantity-mismatch)
   — contributed by the inventory module **[Accepted — DEC-012 §3.7]**.
8. Fulfillment exceptions (unmatched picking / ambiguous
   FulfillmentOrder/line / notification-confirmation-missing) — contributed
   by the fulfillment module **[Accepted — DEC-012 §3.8]**.
9. Duplicate/matching exceptions across domains
   **[Accepted — DEC-006/DEC-009; DEC-012 §3.9]**.

### F.2 Data source

Every metric is computed from the job/log/error abstraction (§D) — job
states, error classes, and guard/confirmation records. **No separate
metrics store and no domain-owned parallel dashboard** (RA-013)
**[Blueprint proposal]**.

### F.3 Exception-first design and next actions

The dashboard leads with what needs attention; **every count is clickable**
and routes to the filtered sync-center/error-center view for that category
— a number with no path to act on it is not acceptable
**[Accepted — DEC-012 §3.10]**.

### F.4 No vanity-only metrics

No metric is shown unless it maps to a health signal or a clickable next
action (e.g. no raw "API calls made" counter without a threshold/action)
**[Accepted — DEC-012 §3.11]**.

### F.5 Role visibility

All four roles (§J) can view the dashboard; action affordances (retry,
confirm, configure) render only for roles holding the corresponding right
— visibility of a problem is never restricted to those who can fix it
**[Blueprint proposal, consistent with DEC-012 §10]**. The
admin-vs-functional-user surface split (one role-gated surface vs two)
remains **[Open question — MBQ-45, carried from DEC-012]**.

---

## G. Sync center / job monitor blueprint

### G.1 Filters

Domain (product/order/inventory/fulfillment); trigger/source (the §D.2
list); state (the §D.3 vocabulary); error class (human-readable labels,
§D.4) **[Accepted — DEC-009; DEC-012 §4]**.

### G.2 List columns (conceptual)

Domain · source · state · related record · age · retry count · error class
(where failed/blocked) · operator-safe operation reference (§G.7)
**[Accepted — DEC-012 §4.1]**.

### G.3 Actions

- **Retry when safe** (§G.4).
- **Verify current state** — for ambiguous-outcome jobs, a safe
  verification read against Shopify, offered **before** any retry
  **[Accepted — DEC-009; DEC-011]**.
- **Open source record** — the related Odoo record
  **[Accepted — DEC-009 audit requirements]**.
- **Open mapping** — the relevant binding/mapping record
  **[Accepted — DEC-006; DEC-012]**.
- **Cancel / supersede** — from `draft`/`queued`/`retry_waiting` (§D.9)
  **[Accepted — DEC-009]**.

### G.4 Retry button rules

Retry is never a single generic button. Per job, the UI distinguishes:
automatic retry already in progress (`retry_waiting` — no button); safe to
retry manually now; requires a fix first (no retry button until resolved);
requires a verification read before retry is offered (ambiguous-outcome).
Classes requiring manual fix, confirmation, or verification never show a
bare retry action **[Accepted — DEC-009; DEC-012 §4.6/§4.9; RA-014]**.

### G.5 Verify-current-state action

Runs the §D.7 verification read as a visible job; its outcome either
unlocks a safe retry or routes to `blocked_manual_review` — the operator
sees which happened and why **[Accepted — DEC-009; DEC-011]**.

### G.6 Cancel/supersede in the UI

Cancellation requires an active role right (§J) and records who/why;
supersession shows the successor operation **[Blueprint proposal, §D.9]**.

### G.7 Operator-safe operation reference

A stable, human-readable reference derived from the operation-level key
(operation type + target + attempt) so two attempts at the same operation
are visibly the same operation — the raw key schema is never exposed
**[Accepted — DEC-012 §4.7]**.

---

## H. Error center / recovery blueprint

1. **Human-readable reason** as the primary display — plain language, never
   an error code or stack trace **[Accepted — DEC-009; RA-016]**.
2. **Technical detail expandable** — raw error/response, class code,
   job/operation identifiers behind an explicit expand
   **[Accepted — DEC-009]**.
3. **Suggested fix** — every blocked/failed entry names a concrete next
   step **[Accepted — DEC-009]**.
4. **Owner/action state** — waiting on system (auto-retry) / waiting on
   operator (fix/confirm) / resolved **[Accepted — DEC-012 §5.4]**.
5. **Related Odoo record** — direct link **[Accepted — DEC-009]**.
6. **Related Shopify record** — reference (and link where feasible), shown
   even when the operation failed before a Shopify object was confirmed
   **[Accepted — DEC-012 §5.6]**.
7. **Retry-policy explanation** — a one-line *why* this entry is
   auto-retried / manual-only / needs verification
   **[Accepted — DEC-012 §5.7]**.
8. **Manual review sub-reasons** — the specific sub-reason shown, never a
   generic "needs review": ambiguous match / binding conflict / duplicate
   risk / destructive-write guard blocked / inventory location missing /
   fulfillment notification confirmation missing
   **[Accepted — DEC-009; DEC-012 §5.8]**.
9. **Audit trail** — attempted / actually written / skipped-by-which-rule /
   confirmed-by-whom, with before/after values for destructive operations
   **[Accepted — DEC-009]**.

Order-import operator touchpoints (financial-evidence mismatch,
total-check issues) are provisionally handled by this error center; whether
a dedicated order-import flow is needed is
**[Open question — MBQ-26, routed to Sprint B]**.

---

## I. Configuration / feature-flag mechanism blueprint

DEC-008 routed the mechanism itself here. **[Accepted — DEC-013,
resolving MBQ-07 at blueprint-direction level]** — the blueprint-level
mechanism below is accepted; the exact technical implementation detail
remains **[Open question — MBQ-07]** for implementation planning.

### I.1 Per-store enabled domains

A per-store record of which domains (product / sale-order / inventory /
fulfillment) are enabled, aligned to the DEC-008 module family. Installing
a module makes its domain *available*, never silently *enabled* — no domain
is enabled unless the operator explicitly selects it
**[Accepted — DEC-012 §1 safe defaults]**.

### I.2 Per-domain capability flags

Within an enabled domain, finer-grained capability flags contributed by the
domain module (e.g. product: image sync on/off, price sync on/off —
bounded by DEC-007 §2/§3; inventory: apply-mode once decided; fulfillment:
notification default, §B.7). Flags configure **within** accepted scope —
a flag can never enable a capability outside DEC-003/DEC-007 scope
**[Blueprint proposal]**.

### I.3 Accepted technical direction

**[Accepted — DEC-013]** — exact implementation detail may remain
**[Open question — MBQ-07]**: a **store-scoped connector settings record
owned by `core`**
(conceptually one settings record per store, referenced from §B.1), with
domain modules **extending** it with their own flag fields — rather than:

- global `ir.config_parameter` keys (not store-scoped, not
  multi-store-safe, no field-level access control) — **[Inference]**
  unsuitable per DEC-003's multi-store-safe-keys rule;
- a `res.config.settings`-only surface (transient, company/global-scoped)
  — **[Inference]** may *present* settings but must not be the storage of
  record;
- per-domain ad hoc settings models (violates the single-substrate rule,
  RA-013-adjacent).

Flags are read at enqueue time **and** re-checked at execution time
(defense in depth, matching §E.5) — **scoped to fail-safe enablement
gating only**: the execution-time re-check may **stop, hold, cancel, or
block** a job from running when the domain/capability it belongs to has
since been disabled, but it must never **alter** any decision persisted at
enqueue time. In particular, the execution-time re-check must **never**
re-read or change the fulfillment notification flag persisted per job
under DEC-011 (§D.13), must **never** re-read or change a source-of-truth
decision persisted for the relevant job/guard (§D.13), and must **not
bypass any safety guard** (§I.5) **[Blueprint proposal]**.

### I.4 Safe enable/disable behaviour

- **Disabling a domain stops new sync activity** for that domain: new jobs
  for it are blocked from enqueue/execution (§I.3). Existing
  `queued`/`retry_waiting` jobs for the disabled domain are either
  **cancelled** (with an audit reason, per the accepted `cancelled` job
  state, §D.3/§D.9) or **kept in an accepted blocked state** such as
  `blocked_manual_review`, depending on implementation planning — **no new
  top-level job state is introduced by this rule**; jobs are never silently
  dropped **[Blueprint proposal, extending DEC-012 store settings §4;
  exact behaviour remains implementation planning / open question]**.
- **Disabling must not delete history** — bindings, jobs, logs, and audit
  records are preserved **[Accepted — DEC-012 store settings §4]**.
- **Re-enabling a domain re-enters that domain's own guard** — e.g.
  inventory re-entry re-enters the first-push guard; prior consent never
  silently carries over **[Accepted — DEC-012 store settings §7]**.

### I.5 No flag bypasses safety guards

Structural rule: **no feature flag, setting, or configuration combination
may bypass** the first-push guard, the notification default-off guard, the
duplicate-prevention preview, the destructive-write preview, the
total-check guard, or the ambiguous-outcome rule. Guards are enforced in
the substrate (queue/guard records), not in the settings UI
**[Blueprint proposal, from DEC-007/009 guard semantics; RA-008/RA-009/
RA-014 reinforced]**.

---

## J. Permissions / access blueprint

Converts DEC-012 §10's four conceptual roles into a blueprint-level access
design. **No access CSVs, no `ir.model.access` rows, no record rules are
created or committed here** — exact artifacts are
**[Open question — MBQ-44]**. Group names below are **proposed names only,
not committed XML IDs**.

### J.1 Roles and proposed group-name directions

| Role (DEC-012) | Proposed group-name direction (proposed name only) | Persona |
| --- | --- | --- |
| Connector Administrator | `group_shopify_connector_admin` | P2 |
| Connector Operator | `group_shopify_connector_operator` | P1 |
| Connector Reviewer / Manual Review Owner | `group_shopify_connector_reviewer` | narrower cut of P1/P2 |
| Read-only Auditor | `group_shopify_connector_auditor` | P3 |

**[Accepted — DEC-013, partially resolving MBQ-45]** — hierarchy:
Administrator implies Operator and Reviewer rights; Operator and Reviewer
are siblings (neither implies the other); Auditor is implied by all
(everyone who can act can also view). The hierarchy above is accepted at
blueprint level; whether the four roles map 1:1 to Odoo groups or to
finer-grained combinations, and the admin-vs-functional-user screen
split, remain **[Open question — MBQ-45]** for implementation planning.

### J.2 Capability matrix (blueprint level)

| Capability | Administrator | Operator | Reviewer | Auditor |
| --- | --- | --- | --- | --- |
| View dashboard / jobs / errors / bindings / audit trails | Yes | Yes | Yes | Yes |
| View store settings & connection status | Yes | Yes (read-only) | Yes (read-only) | Yes (read-only) |
| Configure (settings, domains, source-of-truth, notification default) | Yes | No | No | No |
| Enter/replace/rotate credential | Yes | No | No | No |
| See credential secret value | **No — masked status only, on every connector UI/API surface** | No — masked status only | No — masked status only | No — masked status only |
| Run setup wizard | Yes | No | No | No |
| Trigger manual sync / reconcile-now | Yes | Yes | No | No |
| Retry safe jobs (state/class-conditional, §G.4) | Yes | Yes | No | No |
| Run verify-current-state action | Yes | Yes | Yes (on review items) | No |
| Approve/resolve `blocked_manual_review` (manual match, first-push confirmation, notification confirmation, duplicate-risk confirmation) | Yes | No | **Yes** | No |
| Cancel / supersede jobs | Yes | Yes (own-triggered/queued) | No | No |
| Audit (view who did what, before/after) | Yes | Yes | Yes | Yes |

**[Blueprint proposal throughout; grounded in DEC-012 §10 and DEC-009's
requirement that confirmations record who acted.]** Notes:

- The **no-read-back credential rule is a connector surface guarantee, not
  an absolute database-level claim**: no connector UI or API surface
  exposes the stored secret after entry, for any role including
  Administrator (§B.2) — every role sees masked status only after save
  **[Blueprint proposal, extending DEC-004's masked-storage rule]**. This
  does **not** claim a database superuser or direct database access cannot
  reach raw stored contents — the **at-rest protection and storage
  mechanism** (encryption vs. Odoo field-level `groups` protection alone)
  remain **[Open question — MBQ-04]**, unresolved by this rule.
- Reviewer approvals are the auditable act DEC-009 requires — approving a
  manual-review item records who/when and releases the job through the
  normal queue path, never a side channel **[Accepted — DEC-009]**.
- Per-store isolation for every role is enforced by explicit store scoping
  + record rules, never `sudo()` **[Accepted — DEC-004/005/006]**.
- `ir.model.access` is deny-by-default; the connector's models are
  reachable only through these groups **[Accepted — setup-ux-principles
  Principle 10 (Tier-1 Odoo fact), via DEC-012]**.

---

## K. Cross-module dependency and extension rules

Restated as binding blueprint rules for every later domain blueprint
(Sprint B/C) and for implementation planning:

1. **Dependency direction** — strict one-directional DAG:
   `core` → `product`; `sale` and `inventory` are siblings on
   `core` + `product`; `fulfillment` on `core` + `sale`. No upward or
   same-tier dependencies **[Accepted — DEC-008]**.
2. **No duplicate substrate** — no domain module may implement its own
   job/queue, log, error-class registry, or binding-audit system
   (RA-013 binding) **[Accepted — DEC-008/DEC-009]**.
3. **Domain-specific extensions allowed** — via the §A.5 seams only:
   concrete binding models on the core contract, registered job types,
   error-class mapping, settings/flag contributions, dashboard/error-center
   category contributions, setup-step contributions
   **[Blueprint proposal]**.
4. **Core must not depend on domain modules** — no foreign keys or imports
   from `core` into any domain module **[Accepted — DEC-008]**.
5. **Fulfillment must not depend on inventory** — and must not read
   inventory's location-mapping table; it uses the core Shopify Location
   reference and/or a live FulfillmentOrder `assignedLocation` read
   (mechanism **[Open question — MBQ-42]**)
   **[Accepted — DEC-008/DEC-010/DEC-011]**.
6. **Inventory owns Odoo↔Shopify location mapping** — exclusively
   **[Accepted — DEC-010]**.
7. **Core may own the Shopify Location reference/cache only** — Shopify-side
   data, never Odoo-location IDs or mapping decisions (§B.4)
   **[Accepted — DEC-010/DEC-011]**.
8. **No one giant module** (RA-011) and no per-feature micro-module
   explosion (RA-012) — the Phase 1 family is fixed by DEC-008; later
   modules need their own boundary review **[Accepted — DEC-008]**.
9. **Sibling reuse via `product`** — `sale` and `inventory` both resolve
   product/variant bindings through `product` (the shared owner), never by
   duplicating resolution logic **[Accepted — DEC-008 "Risks" #3]**.
10. **Link modules** — none needed in Phase 1; if a genuine cross-domain
    glue need is discovered, it routes through the DEC-008 link-module
    pattern via a new review, not a silent dependency edit
    **[Accepted — DEC-008]**.

---

## L. Open questions (this blueprint)

Full register with owners and blocking status:
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).
Headline items raised or carried by this Part A blueprint:

- Exact Odoo **model names** (MBQ-01) and **field names** (MBQ-02) for every
  §B–§D concept — implementation planning.
- Exact **access CSV rows / group XML IDs** (MBQ-44) and **view/menu XML
  IDs** (MBQ-03) — implementation planning; §J names are proposed-only.
- Exact **credential encryption/storage mechanism** (MBQ-04) — ChatGPT +
  official-doc verification before any credential code.
- **Reconciliation cadence and scope** (MBQ-17) — ChatGPT (posture) +
  implementation planning (constants); exact **cron cadence and throughput
  limits** (MBQ-18) — implementation planning, with MVP-scale validation
  under `--max-cron-threads=2`.
- Exact **technical feature-flag implementation** (MBQ-07) — §I.3's
  direction is **accepted via DEC-013**; exact implementation detail
  remains for implementation planning.
- **Binding schema-shape confirmation** (MBQ-11) — §C.8's per-domain
  concrete models on a core abstract contract are **accepted via
  DEC-013**.
- **Order-import operator touchpoints** (MBQ-26) — routed to Sprint B.
- **Store-disconnect data-retention posture** (MBQ-08) — ChatGPT decision.
- Operation-level idempotency **key schema** (MBQ-20) and serialization
  guard mechanism (MBQ-21) — implementation planning.
- Readiness-check essential-vs-nice list (MBQ-06); roles→groups mapping
  (MBQ-45); API-version pinning policy (MBQ-52).
- **Screen-level UI/UX design blueprint** (MBQ-53) — routed to a later
  Master Blueprint Part D (UI/UX Screen Design Blueprint); blocks
  implementation of operator-facing screens, not Part B/C domain-blueprint
  authoring.
- **Domain-module uninstall/disable data lifecycle** (MBQ-54) — whether
  disabling or uninstalling a domain module can ever lose bindings, jobs,
  logs, or audit history; ChatGPT + implementation planning.

---

## No implementation authorized

**This blueprint's acceptance via DEC-013 does not authorize
implementation.** It creates no code, no Odoo module, no model, no view,
no security file, and no file outside `docs/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force. Implementation of any part of this
blueprint remains blocked until ChatGPT (1) accepts the remaining Master
Blueprint parts as required (including, for operator-facing screens, the
accepted Part D — UI/UX Screen Design Blueprint), and (2) separately
opens the implementation gate per `../05-qa/quality-feedback-loop.md` §10
and `CLAUDE.md` §5.
