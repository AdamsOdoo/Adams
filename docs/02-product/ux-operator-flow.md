# UX / Operator-Flow Proposal

> **Phase 1 UX/operator-flow strategy evidence base**, for the premium
> **Odoo 19 ↔ Shopify Connector**, prepared after all of **AR-002 through
> AR-008** were accepted (via DEC-004 through DEC-011) and **DEC-003 through
> DEC-011** were accepted by ChatGPT. This document remains the
> evidence-backed UX/operator-flow proposal behind the companion decision
> record:
> [`../04-decisions/DEC-012-ux-operator-flow-strategy.md`](../04-decisions/DEC-012-ux-operator-flow-strategy.md)
> (status: **Accepted by ChatGPT, 2026-07-03**, after PR #68 merged into
> `Shopify-connector` — see DEC-012's *Acceptance note*). Companion
> architecture bridge:
> [`../03-architecture/ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md).

## Status

- **Sprint:** UX / Operator-Flow Decision Preparation (2026-07-02), after the
  AR-007 + AR-008 Decision Preparation sprint (PR #66, merge commit
  `14af2fb3becb47ba7c32a50715d85f6eaab0d855`) and its follow-up README
  cleanup (PR #67, merge commit
  `8798a2454924fd241c8052e2556ea8bca21a7c20`).
- **Phase:** documentation-only, **no-code gate in force** (`CLAUDE.md` §4–§5).
  **This document decides nothing by itself** — it is the evidence base for
  [`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md), which is
  now **Accepted by ChatGPT** (acceptance date 2026-07-03, after PR #68
  merged into `Shopify-connector` and Fable's **ACCEPT WITH MINOR CHANGES**
  review was applied). This document itself still does not authorize
  implementation — the **Master Blueprint** remains the next step, gated by
  a separate ChatGPT implementation-gate approval.
- **Governance:** every statement below is labelled exactly one of:
  - **[Accepted]** — restates an already-accepted DEC-003 through DEC-011 (or
    `CLAUDE.md`/`quality-feedback-loop.md`) decision, cited by file. Not
    re-litigated here.
  - **[Proposed UX decision]** — the label used during PR #68 decision
    preparation for a new operator-flow proposal this document introduces,
    rather than a direct restatement of DEC-003 through DEC-011. It is
    retained as-is to show provenance; now that DEC-012 is **Accepted by
    ChatGPT**, statements carrying this label are accepted through DEC-012
    like the rest of this document — the label no longer means "not yet
    binding," only "introduced by this sprint."
  - **[Inference]** — reasoning drawn from cited evidence (the accepted
    architecture decisions, `setup-ux-principles.md`, `product-vision.md`,
    the domain-model brief, or competitor evidence already in the repo), not
    itself a decision.
  - **[Open question / must be verified before implementation]** — unresolved;
    routed to the Master Blueprint / implementation planning, per
    `CLAUDE.md` §7.
- **Does not decide:** exact Odoo views/menus/widgets, exact field names,
  exact model/schema, exact copy text, exact security groups/access CSVs, or
  any implementation mechanism. Those remain Master Blueprint /
  implementation-planning items, gated by a separate ChatGPT-approved
  implementation gate (`CLAUDE.md` §5; `../05-qa/quality-feedback-loop.md`
  §10).

## Purpose

Define **how a non-technical Odoo operator safely configures, runs, monitors,
recovers, and audits** the Shopify connector, so that the Master Blueprint (the
next gated sprint) can design concrete screens/menus/models against a
settled, evidence-grounded operator-experience direction instead of
re-deriving UX judgement calls per domain. This closes the last Phase
1 research-phase-exit criterion named in
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10
("a UX/operator-flow sprint accepted, or explicitly parallelized").

## Evidence base

- **Product UX principles (accepted evidence input):**
  [`./setup-ux-principles.md`](./setup-ux-principles.md) (12 principles: guided
  setup, prove readiness, progressive disclosure, honest freshness, command
  center, recovery-first errors, safe-by-default actions, human-readable logs,
  guided mappings, role-aware UX, modular feature visibility, docs mirror the
  product).
- **Product vision (accepted evidence input):**
  [`./product-vision.md`](./product-vision.md) — personas P1 (operations/
  e-commerce user), P2 (Odoo administrator/implementation consultant), P3
  (business owner/finance stakeholder), P4 (Odoo partner/integrator); the
  "correctness + operator experience" differentiation thesis.
- **Accepted architecture/product decisions:**
  [`DEC-003`](../04-decisions/DEC-003-mvp-scope.md),
  [`DEC-004`](../04-decisions/DEC-004-distribution-api-auth-strategy.md),
  [`DEC-005`](../04-decisions/DEC-005-sync-orchestration-strategy.md),
  [`DEC-006`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md),
  [`DEC-007`](../04-decisions/DEC-007-phase1-scope-clarifications.md),
  [`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md),
  [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md),
  [`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md),
  [`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) —
  each already carries a **"UX implications"** section that this document
  expands into concrete operator flows.
- **Phase 1 domain model:**
  [`../03-architecture/phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md)
  (Domains 1–8: store/connection, binding/identity, product, customer,
  order/sale, inventory, fulfillment, queue/log/error).
- **Rejected approaches this document must not reintroduce:** RA-006
  (name-only auto-match), RA-008 (blind first inventory push), RA-009 (hidden/
  default-on fulfilment notification), RA-014 (retry-everything
  automatically), RA-015 (never-retry/manual-only), RA-016 (raw stack trace as
  primary error UX), RA-017 (binding-alone idempotency), RA-018 (writing
  `committed`), RA-019 (SKU-only inventory writes), RA-020 (autonomous
  bidirectional inventory conflict resolution), RA-021 (assumed quantity
  equivalence), RA-022 (legacy fulfillment API), RA-023 (fulfillment without
  FulfillmentOrder/line/quantity/location matching) — see
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md).

## No implementation authorized

**This document does not authorize implementation.** It remains the
evidence-backed operator-flow UX proposal behind
[`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md) (status:
**Accepted by ChatGPT**, acceptance date 2026-07-03). No Odoo module, model,
view, controller, security file, or code of any kind is created by this
document or by DEC-012. Implementation of any part of these flows remains
blocked until ChatGPT separately opens the implementation gate per the
Phase 1 research-phase-exit criteria (`../05-qa/quality-feedback-loop.md`
§10) and `CLAUDE.md` §5. Acceptance of DEC-012 alone did not open that gate
— exact screens, menus, widgets, fields, and security groups remain
**Master Blueprint** work, which is the next step, not started here.

---

## 1. Initial setup wizard

### Purpose

Get a non-technical operator from "module installed" to "connected, tested,
and ready to sync" without editing server config or reading source code
**[Inference — setup-ux-principles.md Principle 1]**.

### Respects

- Non-public custom-app / offline-token model; masked storage; least-privilege
  scopes; inline test-connection/readiness check **[Accepted — DEC-004]**.
- Single-store, single-company Phase 1 MVP; keys stay multi-store-safe
  **[Accepted — DEC-003 / phase1-domain-model-brief.md Domain 1]**.
- Layered sync (webhook + scheduled + manual + reconciliation), never one
  mechanism alone **[Accepted — DEC-005]**.
- Binding-first matching, no name-only auto-match **[Accepted — DEC-006]**.
- First-inventory-push guard and fulfilment-notification default-off guard
  apply from first configuration, not only post-setup **[Accepted — DEC-007]**.

### Proposed flow

1. **Welcome / prerequisites** — states plainly that this is a guided,
   in-product flow with no server-config editing required for the credential
   step itself; separately and honestly discloses that Odoo.sh/on-prem hosting
   is required (Odoo Online is excluded) **[Accepted — DEC-005 §"Decision
   summary"]** — this is disclosed once, up front, not discovered mid-wizard
   **[Proposed UX decision]**.
2. **Store connection** — operator names the store (single store, Phase 1)
   and enters the custom-app credential per the DEC-004 offline-token model;
   the credential field is masked on entry and never displayed in plaintext
   again after save **[Accepted — DEC-004]**.
3. **Credentials / token posture** — the wizard presents this as a **guided
   custom-app credential flow, not one-click OAuth** — it explains, in plain
   language, why (non-public/Early Access distribution, "Always available"
   protected-data access, no App-Store review wait) so the operator
   understands the friction is wizard steps, not approval latency
   **[Accepted — DEC-004 §"UX implications"]**. The wizard presents the
   minimal required scope list, never as arbitrary free-text input, and
   verifies the granted scopes during the test-connection/readiness step —
   the wizard does not itself mechanically grant Shopify scopes; the operator
   still grants them on the Shopify side when creating/authorising the custom
   app. **Exact Shopify custom-app scope-grant mechanics remain a Master
   Blueprint / implementation-planning item** **[Proposed UX decision; Open
   question / must be verified before implementation]**.
4. **Test connection** — a discrete, explicit "Test Connection" action
   (WK-style floor) that reports pass/fail with a reason, not a silent
   spinner **[Accepted — DEC-004 UX implications; setup-ux-principles.md
   Principle 2]**. This action, and the readiness checks in the next step,
   are **not** "sync runs" — see "Readiness/test/preview jobs are not
   business sync runs" below.
5. **Readiness checks** — before the store is marked connected, an explicit
   pass/fail readiness surface checks (candidate list, not final): scope
   grants, HTTPS/`web.base.url` reachability, webhook reachability,
   worker/queue presence, credential validity **[Accepted — DEC-004 UX
   implications]**. **Which checks are essential vs nice-to-have is
   unresolved** **[Open question / must be verified before implementation —
   setup-ux-principles.md Principle 2, "Open questions" #1]**.
6. **Sync direction choices** — for each domain (product, order, inventory,
   fulfillment), the operator is asked which direction(s) are enabled for
   this store, consistent with DEC-003's per-domain scope (product
   import + controlled export/update; order import only; inventory
   import-then-Odoo-write-back; fulfilment write-back only)
   **[Accepted — DEC-003]**. The wizard does not offer a direction DEC-003
   does not support (e.g. autonomous bidirectional catalog ownership, customer
   export) **[Accepted — DEC-003 non-goals]**.
7. **Source-of-truth choices** — the operator makes an **explicit** first-sync
   source-of-truth choice for product matching (Shopify-source /
   Odoo-source / both-match-first) **[Accepted — DEC-006 UX implications]**
   and, separately, for price (Odoo-authoritative vs. Shopify-authoritative)
   **[Accepted — DEC-007 §3]**. Neither choice defaults to an implicit guess —
   the wizard **requires** a selection before the store can be marked ready
   **[Proposed UX decision]**.
8. **Fulfillment notification default** — the wizard sets the Phase 1 safe
   default explicitly: **no customer notification on fulfilment/tracking
   write-back unless the operator explicitly enables or confirms it**,
   grounded in Shopify's own `notifyCustomer` defaults
   **[Accepted — DEC-007 §5; RA-009]**. The wizard states this default in
   plain language and requires an explicit opt-in action to change it — it is
   never pre-checked "on" **[Accepted — DEC-007 §5]**.
9. **Inventory first-push mode** — inventory sync is **not** enabled to write
   Odoo→Shopify until the operator completes the dedicated first-push guard
   (mapped location + preview + confirmation + recorded source-of-truth +
   skip/manual-match option — see §8 below)
   **[Accepted — DEC-007 §4; DEC-010 "First-push guard posture"; RA-008]**.
   The setup wizard may **schedule** this step but must not silently skip or
   auto-complete it **[Proposed UX decision]**.
10. **Final readiness summary** — a single screen restates: connection status,
    enabled domains + directions, source-of-truth choices, notification
    default, and whether inventory first-push is still pending — before the
    operator leaves setup **[Proposed UX decision, synthesising DEC-004 UX
    implications + DEC-007 §4/§5]**.
11. **Safe incomplete setup state** — if the operator exits before completing
    every required step, the connector is left in an explicit **"setup
    incomplete"** state: no sync runs, no writes occur, and the operator is
    shown exactly which steps remain (not a generic "not configured" error)
    **[Proposed UX decision, consistent with DEC-003's safe-by-default and
    setup-ux-principles.md Principle 7]**. An incomplete inventory first-push
    step blocks inventory sync specifically, without blocking product/order
    sync that does not depend on it **[Inference — DEC-007 §4 scopes the
    guard to inventory only]**.

### Readiness/test/preview jobs are not business sync runs

The setup-gate statement below ("no sync of any kind runs before setup is
marked complete") refers to **business sync/write jobs** — it does not block
the wizard's own readiness/test/preview mechanics, which must be able to run
**during** setup for the wizard to function at all:

- **Readiness checks and test-connection actions** (DEC-009 job source
  `setup_readiness_check`) and **preview/dry-run jobs** (DEC-009 job source
  `export_preview_dry_run`) are **not** treated as "sync runs"
  **[Proposed UX decision, clarifying DEC-009's job-source taxonomy for this
  document]**.
- They **may run during setup**, before the store is marked connected/ready.
- They **must not create or update any Shopify or Odoo business record** —
  they are structurally read-only or preview-only, never a write path.
- **Business sync/write jobs** (product/order/inventory/fulfillment sync,
  first-push writes, etc.) remain blocked until setup is marked complete,
  unchanged from the safe default below.

### Safe defaults

- No **business sync/write job** runs before setup is marked complete;
  readiness checks, test-connection actions, and preview/dry-run jobs
  (`setup_readiness_check`, `export_preview_dry_run`) are not business sync
  runs and may run during setup, provided they stay read-only/preview-only
  and never create or update a Shopify or Odoo business record.
- Fulfilment customer notification defaults to **off**.
- Inventory Odoo→Shopify write-back is blocked until the first-push guard is
  satisfied.
- No domain is enabled unless the operator explicitly selects it.

### Open questions

- Exact minimal-vs-full readiness-check list **[Open question —
  setup-ux-principles.md Principle 2]**.
- Exact custom-app creation surface and token-acquisition mechanics
  (Admin-created vs. Partner/Dev-Dashboard) **[Open question — DEC-004,
  routed to implementation planning]**.
- Whether Odoo.sh/on-prem setup can avoid mandatory `odoo.conf`/queue
  prerequisites **[Open question — AR-003/DEC-005 implementation planning]**.

---

## 2. Store settings

### Purpose

Give the operator one place to see and change what the connector is doing for
this store, without exposing internal mechanics or secrets
**[Inference — setup-ux-principles.md Principle 10/11]**.

### Respects

- Credential masking; field-level access control **[Accepted — DEC-004]**.
- The feature-flag/per-store capability-configuration **mechanism** is not
  decided by DEC-008 and is explicitly routed to this sprint for the
  operator-facing experience only — the technical mechanism stays a Master
  Blueprint item **[Accepted — DEC-008 "What remains open"]**.
- Domain-aligned module boundaries (`core`/`product`/`sale`/`inventory`/
  `fulfillment`) **[Accepted — DEC-008]**.

### Proposed flow

1. **Connection status** — a single, glanceable state (Connected / Setup
   incomplete / Disconnected / Reconnect needed), never a raw HTTP code
   **[Proposed UX decision, per setup-ux-principles.md Principle 4]**.
2. **API health display** — honest, named health state (e.g. "Normal" /
   "Throttled — Shopify is rate-limiting requests" / "Degraded"), not a raw
   GraphQL cost number, with a plain-language explanation when not "Normal"
   **[Accepted — DEC-004 §"UX implications" ("honest, named health
   indicator")]**.
3. **Token status without exposing secrets** — shows whether a credential is
   present, when it was last validated, and (if the expiring-token variant is
   ever selected in implementation planning) a rotation/expiry countdown —
   **never** the token value itself, masked at all times
   **[Accepted — DEC-004]**. Reconnect/re-authorise/disconnect is a
   first-class action, not buried **[Accepted — DEC-004 UX implications;
   setup-ux-principles.md "Setup flow principles"]**.
4. **Enabled domains** — product, sale/order, inventory, fulfillment each
   shown with an explicit on/off state matching DEC-008's module boundaries,
   so an operator can reason about "what is this connector doing" per domain
   **[Proposed UX decision, aligned to DEC-008's addon family]**. Disabling a
   domain does not delete its history/logs — it stops new sync activity for
   that domain **[Proposed UX decision]**.
5. **Source-of-truth settings** — the product-matching and price
   source-of-truth choices made at setup (§1) are visible and editable here,
   with a warning that changing source-of-truth after first sync is a
   meaningful behaviour change, not a cosmetic toggle
   **[Proposed UX decision, extending DEC-006/DEC-007]**.
6. **Notification defaults** — the fulfilment customer-notification default
   (§1, DEC-007 §5) is visible and editable here at the global/per-store
   granularity; **per-order override granularity remains an open DEC-007
   fork, not resolved here** **[Accepted — DEC-011 "Customer notification
   posture"]**.
7. **Safe defaults** — store settings never silently widen scope: enabling a
   new domain re-enters that domain's own first-sync/first-push guard rather
   than assuming prior consent carries over **[Proposed UX decision, per
   RA-008's rationale generalised]**.

### Open questions

- The exact feature-flag/per-store capability-configuration **mechanism**
  **[Open question — DEC-008, routed to Master Blueprint]**.
- Admin vs. functional-user settings-visibility split **[Open question —
  setup-ux-principles.md Principle 10, "Open questions" #2]**.

---

## 3. Dashboard / command center

### Purpose

Answer, in one place and at a glance: **"Is everything OK? What failed and
why? What do I do next?"** **[Accepted product principle — setup-ux-principles.md
"UX north star"]**.

### Respects

- Job/log/error concept is uniform across all domains **[Accepted —
  phase1-domain-model-brief.md Domain 8; DEC-005]**.
- Quick actions enqueue work, never run heavy sync inline
  **[Accepted — DEC-005 UX implications]**.
- Honest freshness, no "real-time" overstatement **[Accepted — DEC-005 UX
  implications; setup-ux-principles.md Principle 4]**.

### Proposed flow / contents

1. **Connection health** — mirrors store settings §2 (status + API health),
   surfaced here as the top-level signal **[Proposed UX decision]**.
2. **Last successful sync by domain** — product, order, inventory,
   fulfillment each show their own "last synced / last reconciled" timestamp
   and mechanism label (webhook vs. scheduled vs. manual) — never one global
   "last synced" that hides a stalled domain **[Accepted — DEC-005 UX
   implications; setup-ux-principles.md Principle 4]**.
3. **Failed jobs by severity** — counts split by what they mean to the
   operator (needs manual review vs. system will auto-retry vs.
   permanently failed), not a single undifferentiated "errors: N"
   **[Accepted — DEC-009 "User-facing log requirements"]**.
4. **Manual review count** — jobs in `blocked_manual_review` (ambiguous
   match, binding conflict, duplicate risk, destructive-write guard,
   inventory location missing, fulfillment notification confirmation
   missing) **[Accepted — DEC-009 error taxonomy]**.
5. **Retry-waiting count** — jobs in `retry_waiting`, so the operator can see
   "the system has this, it will retry" distinctly from "you must act"
   **[Accepted — DEC-009 job states]**.
6. **First-push pending count** — how many bindings/units still require the
   inventory first-push guard (§8) before Odoo→Shopify inventory writes can
   begin for them **[Proposed UX decision, extending DEC-007 §4/DEC-010]**.
7. **Inventory exceptions** — location-missing, ambiguous-match, and
   quantity-mismatch counts, distinct from generic failures, since they
   have a distinct safe next action (map a location / resolve ambiguity)
   **[Proposed UX decision, per DEC-010 error classes]**.
8. **Fulfillment exceptions** — unmatched-picking, ambiguous
   FulfillmentOrder/line, and notification-confirmation-missing counts
   **[Proposed UX decision, per DEC-011 error classes]**.
9. **Duplicate/matching exceptions** — ambiguous-match and binding-conflict
   counts across domains, since duplicate prevention is a cross-cutting
   correctness concern **[Accepted — DEC-006; DEC-009]**.
10. **Clear next action** — every count above is clickable and routes
    directly to the filtered job-monitor/error-center view for that
    category — a number alone, with no path to act on it, is not acceptable
    **[Accepted product principle — setup-ux-principles.md Principle 5]**.
11. **Avoid vanity-only metrics** — the dashboard does not show counts that
    have no corresponding operator action (e.g. a raw "API calls made"
    counter with no threshold/action attached) **[Proposed UX decision,
    reflecting the recovery-first / actionable-status principle]**; any
    metric shown must map to either a health signal or a clickable next
    action.

### Open questions

- Admin vs. functional-user dashboard split — one surface with role-gated
  sections, or two **[Open question — setup-ux-principles.md Principle 5,
  "Open questions" #2]**.
- Per-object vs. global freshness indicators **[Open question —
  setup-ux-principles.md Principle 4, "Open questions" #3]**.

---

## 4. Sync center / job monitor

### Purpose

Let the operator see every unit of sync work, in every state, and act on it
safely — without exposing raw `ir.cron` internals **[Accepted — DEC-005 UX
implications; setup-ux-principles.md "Configuration screen principles"]**.

### Respects

- Job source: `webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`,
  `setup_readiness_check`, `export_preview_dry_run` **[Accepted — DEC-009
  "Error taxonomy"]**.
- Job states: `draft`, `queued`, `running` (non-terminal); `succeeded`,
  `failed_final`, `skipped`, `cancelled` (terminal); `retry_waiting`,
  `failed_retryable`, `blocked_manual_review` (loop back to `queued`)
  **[Accepted — DEC-009 "Error taxonomy"]**.
- Ambiguous-outcome rule: no blind retry for a non-`@idempotent` write whose
  outcome is unknown after dispatch **[Accepted — DEC-009 "Retry taxonomy"]**.
- Operation-level idempotency keys distinct from binding identity
  **[Accepted — DEC-009; DEC-011 "Idempotency/retry posture"; RA-017]**.

### Proposed flow / contents

1. **Job list** — one list spanning all domains, sortable/filterable, each row
   showing: domain, source, state, related record, age, retry count
   **[Proposed UX decision]**.
2. **Domain filter** — product / order / inventory / fulfillment
   **[Proposed UX decision, aligned to DEC-008 module boundaries]**.
3. **Trigger filter** — manual, scheduled, webhook, reconciliation
   **[Accepted — DEC-009 job sources, exposed as a filter]**.
4. **Status filter** — queued, running, retry_waiting, blocked_manual_review,
   failed, done, cancelled **[Accepted — DEC-009 job states]**.
5. **Error class** — shown per failed/blocked job, using the DEC-009
   16-class taxonomy translated to a human-readable label (never the raw
   class code alone) **[Accepted — DEC-009 error taxonomy; RA-016]**.
6. **Retry eligibility** — the UI distinguishes, per job, whether a manual
   retry is: automatic already in progress (`retry_waiting` — no button
   needed), safe to retry manually right now, requires a fix first (no retry
   button until the underlying issue is addressed), or requires a
   verification read before any retry is offered (ambiguous-outcome case)
   **[Accepted — DEC-009 "Retry taxonomy"; DEC-011 "Idempotency/retry
   posture"]**.
7. **Operator-safe idempotency/operation key visibility** — the operator sees
   a stable, human-readable reference for "this operation" (e.g. a short
   operation reference derived from the operation-level key: operation type +
   target + attempt) so two attempts at the same thing are visibly the same
   operation — the operator never needs to see or reason about the raw key
   schema itself **[Proposed UX decision, exposing DEC-009/DEC-011's
   idempotency-key concept without exposing implementation detail]**.
8. **Actions:**
   - **Retry when safe** — enabled only when the job's error class and state
     make retry safe per DEC-009 (auto-retry classes are not manually
     re-triggered redundantly; ambiguous-outcome cases offer "verify" before
     "retry" is enabled) **[Accepted — DEC-009]**.
   - **Verify current state** — for ambiguous-outcome jobs, a safe
     verification read against Shopify's current state, shown before any
     retry action is offered **[Accepted — DEC-009 "Ambiguous-outcome rule";
     DEC-011]**.
   - **Open mapping** — jumps to the relevant binding/mapping record
     **[Proposed UX decision, per DEC-006]**.
   - **Open source record** — jumps to the related Odoo record (product,
     order, picking, etc.) **[Accepted — DEC-009 "Audit requirements";
     phase1-domain-model-brief.md Domain 8]**.
   - **Cancel/supersede** — available from `draft`/`queued`/`retry_waiting`
     **[Accepted — DEC-009 "Error taxonomy" job-state transitions]**.
9. **No blind retry for unsafe cases** — retry is never offered as a
   one-size-fits-all button; classes requiring manual fix, confirmation, or
   verification never show a bare "retry" action **[Accepted — DEC-009;
   RA-014]**.

### Open questions

- Reconciliation cadence and scope (per-object vs. global)
  **[Open question — DEC-009 "What remains open"]**.
- Exact retry-count ceilings and backoff constants
  **[Open question — DEC-009 "What remains open"; implementation-planning
  default]**.

---

## 5. Error center / recovery flow

### Purpose

Make every failure a **recovery surface, never a dead end**
**[Accepted product principle — setup-ux-principles.md Principle 6]**.

### Respects

- Human-readable reason as the primary message; technical detail secondary
  **[Accepted — DEC-009 "User-facing log requirements"; RA-016]**.
- Related store/Shopify object/Odoo record/binding/job source shown together
  **[Accepted — DEC-009 "User-facing log requirements"]**.
- Audit requirements: what was attempted, what was written, what was skipped
  and by whom/what rule, who confirmed destructive/first-push/notification
  actions **[Accepted — DEC-009 "Audit requirements"]**.

### Proposed flow / contents

1. **Human-readable reason** — every error's primary display is a plain-
   language sentence (e.g. "Shopify rejected this update: the SKU no longer
   exists on this product"), not an error code or stack trace
   **[Accepted — DEC-009; RA-016]**.
2. **Expandable technical details** — the raw error/response, error class
   code, and job/operation identifiers are available on demand, behind an
   explicit expand action, never shown by default
   **[Accepted — DEC-009 "User-facing log requirements"]**.
3. **Suggested fix** — every blocked/failed entry names a concrete next step
   (e.g. "map a Shopify location for this warehouse," "resolve the ambiguous
   match," "this total does not reconcile — review before retrying")
   **[Accepted — DEC-009; setup-ux-principles.md Principle 6/8]**.
4. **Owner/action state** — whether the entry is waiting on the system
   (auto-retry), waiting on the operator (manual fix/confirm), or resolved
   **[Proposed UX decision, extending DEC-009's state taxonomy into a
   UX-facing owner label]**.
5. **Related Odoo record** — direct link to the product/order/picking/etc.
   the job acted on **[Accepted — DEC-009 "Audit requirements"]**.
6. **Related Shopify record if available** — a direct reference (and, where
   feasible, a link) to the corresponding Shopify object, shown even when the
   operation failed before a Shopify object was confirmed to exist
   **[Proposed UX decision, extending DEC-009's "related store/Shopify
   object" requirement]**.
7. **Retry policy explanation** — the entry states plainly why a class is
   auto-retried, manual-only, or requires verification-before-retry — not
   just that it is one of those, but a one-line why (e.g. "Shopify's response
   was inconclusive, so this needs a quick check before we retry to avoid a
   duplicate")  **[Proposed UX decision, translating DEC-009's ambiguous-
   outcome rule for operators]**.
8. **Manual review reason** — for `blocked_manual_review`, the specific
   sub-reason (ambiguous match / binding conflict / duplicate risk /
   destructive-write guard / inventory location missing / fulfillment
   notification confirmation missing) is shown, not a generic "needs review"
   **[Accepted — DEC-009 error taxonomy]**.
9. **Audit trail** — what was attempted, what was actually written (never
   assumed from "attempted"), what was skipped and by which rule, and who
   confirmed any destructive/first-push/notification action, with
   before/after values for destructive operations
   **[Accepted — DEC-009 "Audit requirements"]**.

### Open questions

- Exact user-facing copy/wording for error reasons and suggested fixes
  **[Open question — DEC-009 "What remains open", explicitly named a
  UX/operator-flow-sprint concern]** — this document sets the **structure**
  (reason + suggested fix + owner + audit), not the final copy.

---

## 6. Matching / duplicate-prevention flow

### Purpose

Prevent duplicate records and silent mis-matches by making every match
**visible, testable, and operator-approved when ambiguous**
**[Accepted product principle — setup-ux-principles.md Principle 9]**.

### Respects

- Match-key priority: existing binding → SKU/internal reference → barcode →
  email/customer keys (customers) → manual match; name is advisory only,
  never automatic **[Accepted — DEC-006 "Decision summary"]**.
- Per-store uniqueness on `(store, Shopify GID)` and
  `(store, Odoo model, Odoo record)` **[Accepted — DEC-006]**.
- No name-only automatic matching, ever **[Accepted — DEC-006; RA-006]**.

### Proposed flow / contents

1. **Binding-first match** — the connector always checks for an existing
   binding before evaluating any other key, for every matchable record type
   (product, variant, customer) **[Accepted — DEC-006 match-key priority]**.
2. **SKU/internal reference** — second-priority automatic match key **for
   product/variant matching** **[Accepted — DEC-006]**.
3. **Barcode** — third-priority automatic match key **for product/variant
   matching** **[Accepted — DEC-006]**.
4. **Customer email / customer-key matching** — **for customer records
   only**, after the binding-first check, the connector matches on
   email/customer keys before falling back to manual match; name is
   advisory only here too, never automatic. Product/variant matching does
   **not** use this step — it follows SKU/internal reference → barcode as
   above. **Customer matching order: binding → email/customer keys →
   manual, name advisory only. Product/variant matching order: binding →
   SKU/internal reference → barcode → manual, name advisory only.** Neither
   order weakens DEC-006 — both are the same accepted match-key priority
   applied to the two record shapes DEC-006 already distinguishes
   **[Accepted — DEC-006 "Decision summary" ("email/customer keys
   (customers)")]**.
5. **Manual match** — available whenever automatic matching cannot resolve
   confidently (either record type); the operator picks the correct
   counterpart record, and the match is recorded with full audit detail
   **[Accepted — DEC-006 UX implications]**.
6. **Name advisory only** — a name/title similarity may be shown as a hint
   during manual match, for both product/variant and customer matching, but
   is never used to auto-bind **[Accepted — DEC-006; RA-006]**.
7. **Preview before create/export** — a duplicate-prevention preview/diff
   ("will create N, link M, N ambiguous") is shown before any create/bind
   action; there is no blind create **[Accepted — DEC-006 UX implications;
   DEC-004 UX implications ("mandatory preview/dry-run diff")]**.
8. **Unmatched / ambiguous / duplicate states** — each is a distinct,
   labelled state (not folded into one generic "needs attention"):
   - **Unmatched** — no candidate found; offer create (subject to the
     relevant domain's own guard, e.g. first-push) or manual match.
   - **Ambiguous** — more than one plausible candidate; routes to manual
     review, never an automatic guess **[Accepted — DEC-006]**.
   - **Duplicate risk** — a create would likely produce a duplicate; blocked
     pending operator confirmation **[Accepted — DEC-009 error taxonomy
     ("duplicate risk")]**.
9. **Operator approval for manual binding** — every manual match is an
   explicit operator action, recorded with who/when/which key
   **[Accepted — DEC-006 UX implications ("manual match override with a
   visible audit trail")]**.
10. **Audit trail** — matched-by, matched-at, source strategy, match key used,
    and status (active/stale/manually-overridden) are visible per binding
    **[Accepted — DEC-006 "Mitigations" #2]**. Stale/recreated bindings surface
    as review items, not silent duplicates **[Accepted — DEC-006 UX
    implications]**.
11. **Store-scoped uniqueness** — the UI reflects that a binding is unique
    per store, so a future multi-store expansion does not silently collide
    with Phase 1's single-store bindings **[Accepted — DEC-006]**.

### Open questions

- Exact schema/fields for binding records (single polymorphic table vs.
  per-domain tables) — does not affect this UX proposal's structure, but
  affects implementation **[Open question — DEC-006/DEC-008, Master
  Blueprint]**.

---

## 7. Product import/export/update flow

### Purpose

Let the operator safely bring Shopify and Odoo catalog data into agreement,
in either direction, without silent data loss
**[Accepted product principle — setup-ux-principles.md Principle 7]**.

### Respects

- Controlled bidirectional product onboarding is MVP; unrestricted autonomous
  bidirectional catalog ownership is explicitly **not** MVP
  **[Accepted — DEC-003]**.
- Variant export/update is included, bounded to the current Shopify
  product/variant model (≤2,048 variants), same controlled-export rules as
  product-level export **[Accepted — DEC-007 §1]**.
- `productSet` reconciles list fields by **deleting omitted entries** — a
  missing/incorrect diff is a data-loss risk **[Accepted — DEC-004
  "Data-safety implications"]**.
- Basic image import/export/update at product/variant level; advanced image
  dedup/alt-text/CDN transforms excluded from Phase 1
  **[Accepted — DEC-007 §2]**.
- Core price + compare-at price sync, both directions; price source-of-truth
  must be explicit before any price export/update
  **[Accepted — DEC-007 §3]**.

### Proposed flow / contents

1. **Shopify → Odoo import** — new/changed Shopify products/variants are
   matched (§6) and either linked to an existing Odoo record or queued as a
   create, per the operator's first-sync source strategy
   **[Accepted — DEC-003; DEC-006]**.
2. **Odoo → Shopify export** — controlled export/update of product, variant,
   image, and price data, gated by the duplicate-prevention preview (§6) and
   a **draft-first** posture (see below) **[Accepted — DEC-003; DEC-007
   §1–§3]**.
3. **Update existing** — updates to an already-bound product/variant show a
   diff of what will change (fields, images, price) before the write, keyed
   off the binding **[Accepted — DEC-004 UX implications]**.
4. **Variants/options** — included in controlled export/update, using the
   same preview/binding/no-name-only-match rules as product-level export;
   the exact mutation choice (`productSet` vs.
   `productVariantsBulkCreate`/`Update`) is not decided here
   **[Accepted — DEC-007 §1]**.
5. **Basic images/media** — included at product/variant level; a preview is
   shown before any destructive replacement or removal of an existing image
   **[Accepted — DEC-007 §2]**.
6. **Price/compare-at** — included, both directions; every price
   export/update requires the price source-of-truth to already be explicit
   (set in §1/§2 store settings) — the flow blocks rather than assumes a
   default when it is not **[Accepted — DEC-007 §3]**.
7. **Source-of-truth selection** — visible per operation, not just at setup;
   an operator can see, for any given product, which system is authoritative
   for this write **[Proposed UX decision, extending DEC-007 §3]**.
8. **Preview of creates/updates/skips** — every export/update run shows,
   before writing: how many records will be created, how many updated
   (with a diff), and how many skipped (with why) — mirroring the
   duplicate-prevention preview in §6 **[Accepted — DEC-004/DEC-006 UX
   implications]**.
9. **Draft-first export** — where Shopify supports a draft/unpublished
   product state, a first-time export defaults to draft/unpublished rather
   than immediately live, so the operator can review on Shopify before the
   product goes live **[Proposed UX decision, per setup-ux-principles.md
   Principle 7 and DEC-003's "channel-controlled safety" language in
   DEC-007 §1]**. **Exact Shopify draft/publish mechanism to key this off is
   an open question** **[Open question / must be verified before
   implementation]**.
10. **Skip/manual-review for ambiguous records** — an ambiguous match or an
    unresolvable diff is skipped with a reason, never guessed
    **[Accepted — DEC-006; DEC-009]**.
11. **No autonomous bidirectional conflict ownership** — the flow never
    silently decides "which side wins" for a field both systems changed;
    that class of conflict is explicitly out of Phase 1 scope
    **[Accepted — DEC-003 non-goals]**.

### Open questions

- Exact `productSet` vs. bulk-variant-mutation choice for variant writes
  **[Open question — DEC-007 §1, implementation planning under DEC-004]**.
- Whether `productSet`'s delete-on-omit behaviour applies identically to
  media as to variants/collections/metafields
  **[Open question — DEC-007 §2]**.
- Exact draft/publish mechanism for draft-first export
  **[Open question — this document]**.

---

## 8. Inventory flow

### Purpose

Let Odoo safely become the ongoing source of truth for Shopify's sellable
stock, without ever risking a blind overwrite of live storefront inventory
**[Accepted — DEC-010]**.

### Respects

- Odoo is the ongoing source of truth for Shopify inventory write-back;
  Shopify's `available` is the Phase 1 **default write target**; `on_hand` is
  allowed but requires explicit Master Blueprint justification before use;
  `committed` is **never** written, under any circumstance
  **[Accepted — DEC-010 "Inventory source-of-truth posture"; RA-018]**.
- Inventory identity keys on `(store, inventory_item_id, location_id)`, not
  SKU alone **[Accepted — DEC-010; RA-019]**.
- The DEC-007 first-push guard applies in full and unweakened: mapped
  location + preview + explicit operator confirmation + recorded
  source-of-truth + skip/manual-match option, before the **first**
  Odoo→Shopify inventory write at the configured granularity
  **[Accepted — DEC-007 §4; DEC-010 "First-push guard posture"; RA-008]**.
- No autonomous bidirectional inventory conflict resolution in Phase 1
  **[Accepted — DEC-010; RA-020]**.

### Proposed flow / contents

1. **Source-of-truth selection** — the operator records, per store (at a
   granularity no coarser than per-store), which system's quantity is
   authoritative for the initial baseline and for ongoing writes
   **[Accepted — DEC-007 §4; DEC-010]**.
2. **Shopify first-sync import preview** — where Shopify is used to establish
   the initial Odoo baseline, a controlled, reviewed one-time import shows
   SKU/variant/location/quantity before applying — not an unreviewed import
   **[Accepted — DEC-003 "initial Shopify stock import is
   controlled/reviewed"]**.
3. **Odoo → Shopify first-push preview** — before the very first Odoo→Shopify
   inventory write for a store/binding, the operator sees a preview of every
   SKU/variant/location/quantity that will be written **[Accepted —
   DEC-007 §4; RA-008]**.
4. **Mapped location requirement** — at least one explicit Odoo
   location ↔ Shopify Location mapping is required before any write; no
   inferred/name-based mapping; a mapping-less location blocks with
   "inventory location missing," never guessed
   **[Accepted — DEC-010 "Location mapping posture"]**.
5. **SKU/variant/location/quantity preview** — the same preview shape is used
   for both the first push and (where the eventual apply-mode requires it)
   ongoing writes, so the operator always sees exactly what will change
   before it changes **[Accepted — DEC-007 §4; DEC-010]**.
6. **Operator confirmation** — the first-push preview requires an explicit
   confirmation action; there is no "skip preview" path for a first write
   **[Accepted — DEC-007 §4; RA-008]**.
7. **Recorded source-of-truth** — the confirmed source-of-truth decision is
   persisted and shown on the binding/audit trail, not just used once and
   forgotten **[Accepted — DEC-007 §4; DEC-009 "Audit requirements"]**.
8. **Skip/manual-review** — an unmapped or ambiguous SKU/variant/location
   combination can be skipped or sent to manual match rather than forcing a
   guess **[Accepted — DEC-007 §4; DEC-010]**.
9. **Shopify `available` as default target** — the UI does not present
   `available` and `on_hand` as equally-weighted, interchangeable choices;
   `available` is pre-selected as the Phase 1 default
   **[Accepted — DEC-010]**.
10. **`on_hand` warning and Master Blueprint justification requirement** — if
    an operator-facing configuration for `on_hand` is ever exposed at all in
    Phase 1, it must carry an explicit warning that `on_hand` is a
    multi-state sum (`available + committed + reserved + damaged +
    safety_stock + quality_control`) with materially different semantics
    than a single sellable-quantity figure, and selecting it requires the
    Master Blueprint's explicit justification — **this document does not
    decide whether `on_hand` is exposed as a UI choice in Phase 1 at all**
    **[Accepted — DEC-010; Open question / must be verified before
    implementation]**.
11. **`committed` never shown as a write target** — `committed` does not
    appear as a selectable inventory-write target anywhere in the UI, under
    any configuration — this is a structural exclusion, not a warned-against
    option **[Accepted — DEC-010; RA-018]**.
12. **Ongoing sync/reconciliation view** — a first-class "reconcile now /
    last reconciled / drift found" surface, since webhook delivery is not
    guaranteed and inventory correctness is high-stakes
    **[Accepted — DEC-005 UX implications; DEC-010 "Sync trigger
    posture"]**.
13. **Inventory mismatch handling** — a detected drift between Odoo's and
    Shopify's last-known quantity is shown as a distinct "inventory
    mismatch" exception (see dashboard §3), not folded into a generic error;
    it never auto-resolves by guessing which side is right
    **[Accepted — DEC-010; RA-020; RA-021]**.

### Open questions

- Exact granularity of "first" for the first-push guard (per-store /
  per-binding / per-variant-location binding)
  **[Open question — DEC-007 §4; DEC-010, Master Blueprint]**.
- Whether ongoing (post-first-push) writes also require preview/confirmation
  on every write, or only the first (apply-mode)
  **[Open question — DEC-010 "What remains open"]**.
- Exact computed-quantity field/formula behind "Free to Use" on the Odoo side
  **[Open question — DEC-010]**.
- Exact feature-flag/configuration UI for inventory settings
  **[Open question — DEC-008/DEC-010, Master Blueprint]**.

---

## 9. Fulfillment flow

### Purpose

Let a validated Odoo delivery safely become the correct, matched Shopify
fulfillment — with no double fulfillment and no surprise customer
notification **[Accepted — DEC-011]**.

### Respects

- Validated `stock.picking` (delivery) is the fulfillment trigger; Shopify
  fulfillment is created exclusively via FulfillmentOrder-based mutations;
  legacy Order/Fulfillment endpoints are never used
  **[Accepted — DEC-011 "Fulfillment source/target posture"; RA-022]**.
- Matching requires the bound Shopify order → its open FulfillmentOrder(s) →
  matched line items/quantities via `lineItemsByFulfillmentOrder`; an
  unmatched picking is never fulfilled by guess
  **[Accepted — DEC-011 "FulfillmentOrder posture"; RA-023]**.
- Customer-notification default is **off** unless explicitly enabled/
  confirmed by the operator, persisted per job at enqueue time
  **[Accepted — DEC-007 §5; DEC-011 "Customer notification posture";
  RA-009]**.
- Multi-package/multi-location fulfillment automation is deferred, not
  rejected **[Accepted — DEC-003 C-FUL-02; DEC-011 "Partial/backorder
  posture"]**.

### Proposed flow / contents

1. **Validated picking trigger** — a validated `stock.picking` (including a
   backorder-split picking, treated as its own fulfillment event) is the only
   trigger; an unvalidated or draft picking never triggers a Shopify write
   **[Accepted — DEC-011 "Fulfillment source/target posture"]**.
2. **Fulfillment candidate preview** — before any Shopify write, the operator
   (or the automated flow, for the non-ambiguous case) can see what will be
   fulfilled: which Shopify order, which FulfillmentOrder, which lines, which
   quantities, which location **[Proposed UX decision, extending the
   DEC-011 matching requirement into a visible preview]**.
3. **Matched Shopify order / FulfillmentOrder / line / quantity / location** —
   shown together as one matched unit, not as separate unlinked facts
   **[Accepted — DEC-011 "User-facing log/audit requirements"]**.
4. **Tracking number/carrier display** — shown per fulfillment, both at
   creation and after any later tracking update; a tracking-only update is
   visibly distinct from a fulfillment-creation event
   **[Accepted — DEC-011 "Tracking update posture"; "User-facing log/audit
   requirements"]**.
5. **Customer notification default off** — every fulfillment/tracking
   write-back defaults to no notification **[Accepted — DEC-007 §5;
   DEC-011; RA-009]**.
6. **Explicit confirmation/enablement for notification** — turning
   notification on is a visible, deliberate action (global/per-store default
   at minimum in Phase 1) — never a pre-checked box
   **[Accepted — DEC-007 §5; DEC-011 "Customer notification posture"]**.
7. **Notification decision persisted per job** — once a job is enqueued, its
   notification decision is fixed for that job and does not silently change
   on retry **[Accepted — DEC-011 "Customer notification posture"]**.
8. **Block if ambiguous/mismatched** — a picking that cannot be cleanly
   matched to exactly one FulfillmentOrder's open line items blocks for
   manual review — it is never auto-guessed
   **[Accepted — DEC-011 "Location/line matching posture"; RA-023]**.
9. **Verification read before retry for ambiguous outcome** — if a
   `fulfillmentCreate` or `fulfillmentTrackingInfoUpdate` call has an unknown
   outcome (timeout/connection loss), the flow performs a safe verification
   read of Shopify's current Fulfillment/FulfillmentOrder state before any
   retry is offered, or blocks for manual review if inconclusive — never a
   blind retry **[Accepted — DEC-009 "Ambiguous-outcome rule"; DEC-011
   "Idempotency/retry posture"; RA-014]**.
10. **No double fulfillment** — the operation-level idempotency key
    (operation type + Shopify target ID + payload version/hash, not just the
    picking ID) distinguishes a tracking update from a fulfillment creation
    and a corrected tracking update from a repeat of the same one; operations
    against the same target are serialized while a prior ambiguous operation
    is unresolved **[Accepted — DEC-011 "Idempotency/retry posture"]**.
11. **Multi-location/multi-package deferred/manual-review posture** — Phase 1
    targets single-fulfillment-location matching; a genuinely multi-location
    spread or a multi-package split routes to manual review rather than
    being auto-split, and true multi-package "Put-in-Pack" automation is
    deferred to a later phase **[Accepted — DEC-003 C-FUL-02; DEC-011
    "Partial/backorder posture"]**.

### Open questions

- Exact notification UI granularity (global/per-store/per-order)
  **[Open question — DEC-007 §5; DEC-011, DEC-007's own unresolved fork]**.
- Exact tracking field source on the Odoo side
  **[Open question — DEC-011 "What remains open"]**.
- Exact mechanism by which fulfillment confirms a picking's source location
  against the Shopify fulfillment location (core Shopify-Location reference
  vs. live `assignedLocation` read, or both)
  **[Open question — DEC-010/DEC-011, Master Blueprint]**.

---

## 10. Permissions / roles concept

### Purpose

Separate who can change connector configuration from who can operate it
day-to-day, and from who can only observe — **conceptually**, not as Odoo
security groups **[Accepted product principle — setup-ux-principles.md
Principle 10]**.

### Respects

- Role-aware UX: an admin surface (install, credentials, mappings,
  permissions) and a functional-user surface (run syncs, read logs, fix
  errors), separated by access rights
  **[Accepted — setup-ux-principles.md Principle 10]**.
- `ir.model.access` is deny-by-default; record rules provide isolation
  **[Accepted — setup-ux-principles.md Principle 10, citing Tier-1 Odoo
  fact]**.
- No credential-handling or store-scoping design may rely on `sudo()` to
  cross record-rule boundaries **[Accepted — DEC-004; DEC-005; DEC-006]**.

### Proposed roles (conceptual only)

1. **Connector Administrator** — can run initial setup, hold/view masked
   credential status, change store settings (§2), enable/disable domains,
   and change source-of-truth/notification defaults. Maps conceptually to
   persona **P2** (Odoo administrator/implementation consultant)
   **[Proposed UX decision, informed by product-vision.md P2 and
   setup-ux-principles.md Principle 10]**.
2. **Connector Operator** — can run manual syncs, view the dashboard/job
   monitor/error center, retry safe jobs, and open source/mapping records —
   cannot change credentials, source-of-truth, or notification defaults.
   Maps conceptually to persona **P1** (operations/e-commerce user)
   **[Proposed UX decision, informed by product-vision.md P1]**.
3. **Connector Reviewer / Manual Review Owner** — can resolve
   `blocked_manual_review` items specifically (approve a manual match,
   confirm a first-push preview, confirm/decline a notification override) —
   a narrower grant than full Operator access, useful where manual-review
   approval should be a distinct, auditable action from routine sync
   operation **[Proposed UX decision, informed by DEC-009's audit
   requirement that confirmations record who acted]**.
4. **Read-only Auditor** — can view the dashboard, job monitor, error center,
   and audit trails, but cannot trigger any sync, retry, or confirmation
   action. Maps conceptually to persona **P3** (business owner/finance
   stakeholder, for correctness/trust visibility)
   **[Proposed UX decision, informed by product-vision.md P3]**.

### Explicitly out of scope here

- Exact Odoo security groups, `ir.model.access` rows, or access-control CSVs
  — Master Blueprint / implementation-planning work
  **[Open question / must be verified before implementation]**.
- Whether these four roles map one-to-one to Odoo groups, or are
  finer-grained combinations of existing Odoo access concepts
  **[Open question]**.
- Multi-company/multi-store permission isolation beyond what DEC-003's
  single-store/single-company MVP already requires
  **[Open question — setup-ux-principles.md "Multi-store and permissions
  principles"]**.

---

## Cross-cutting safe-default and blocked-state summary

For quick reference, the safe defaults and blocked states this document
proposes/reaffirms across all ten flows:

| Situation | Safe default / blocked state | Source |
| --- | --- | --- |
| Setup not fully complete | No **business sync/write job** runs; readiness/test-connection/preview jobs (`setup_readiness_check`, `export_preview_dry_run`) are not business sync runs and may run read-only/preview-only during setup | §1; DEC-003 UX spine; DEC-009 job sources |
| Fulfilment notification | Off, unless explicitly enabled/confirmed | DEC-007 §5; RA-009 |
| First Odoo→Shopify inventory write | Blocked until mapped location + preview + confirmation + recorded source-of-truth | DEC-007 §4; RA-008 |
| Shopify `committed` | Never a write target, structurally | DEC-010; RA-018 |
| Ambiguous product/customer match | Manual review, never auto-guessed | DEC-006; RA-006 |
| Ambiguous/duplicate-risk create | Blocked pending confirmation, preview shown first | DEC-006; DEC-004 |
| Non-`@idempotent` write, unknown outcome | Verification read before retry, or manual review — never blind retry | DEC-009; RA-014 |
| Unmatched fulfillment picking | Blocked for manual review, never auto-guessed | DEC-011; RA-023 |
| Multi-location/multi-package fulfillment | Deferred / manual review in Phase 1 | DEC-003 C-FUL-02; DEC-011 |
| Autonomous bidirectional conflict (catalog or inventory) | Not offered in Phase 1; routes to manual review | DEC-003; DEC-010; RA-020 |

---

## Additional open questions (Fable review, PR #68)

Two open questions surfaced during Fable's review of this document. Neither
is decided here — both are routed to the Master Blueprint:

- **Order-import operator touchpoints** — confirm in the Master Blueprint
  whether order-import operator touchpoints are fully covered by the error
  center/manual-review flow (§5), especially financial evidence mismatch and
  total-check issues (DEC-007 §6), or whether a separate order-import
  operator flow is needed **[Open question / must be verified before
  implementation]**.
- **Store disconnect data-retention posture** — confirm in the Master
  Blueprint what happens to bindings, logs, jobs, and audit records after a
  store is disconnected (§2 "Store settings") **[Open question / must be
  verified before implementation]**.

---

## What this document does not decide

- Exact Odoo views, menus, wizards, widgets, or field names.
- Exact security groups or access-control CSVs (§10 is conceptual only).
- Exact copy/wording for any screen, error message, or confirmation dialog.
- Exact feature-flag/per-store capability-configuration mechanism (DEC-008,
  routed to Master Blueprint).
- Whether order-import operator touchpoints need a dedicated flow beyond the
  error center/manual-review flow (see "Additional open questions" above).
- What happens to bindings/logs/jobs/audit records after store disconnect
  (see "Additional open questions" above).
- Any of the "Open question" items listed under each flow above.

All of the above remain **Master Blueprint / implementation-planning** items,
gated by a separate ChatGPT-approved implementation gate
(`CLAUDE.md` §5; `../05-qa/quality-feedback-loop.md` §10). **No implementation
is authorized by this document.**
