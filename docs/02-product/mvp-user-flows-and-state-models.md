# MVP User Flows and State Models

> Companion to
> [`ui-ux-final-design-spec.md`](./ui-ux-final-design-spec.md) — the nine
> MVP operator flows with start conditions, happy/exception paths, terminal
> states, decision points, system actions, safety guards, audit events,
> premium UX treatment, and unresolved detail. Docs-only; authorizes
> nothing. Every flow renders the accepted behaviour of DEC-003 through
> DEC-020 and Master Blueprint Parts A–E; state vocabulary is the accepted
> set and is **never extended here**.

## Fixed vocabularies (accepted; reused verbatim)

- **Job sources (7):** `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`
  **[Accepted — DEC-009]** + `odoo_event` (with a required trigger-origin
  sub-classification: inventory stock-change / fulfillment
  picking-validation) **[Decided — DEC-019]**.
- **Job states (10):** `draft`, `queued`, `running` (non-terminal);
  `succeeded`, `failed_final`, `skipped`, `cancelled` (terminal);
  `retry_waiting`, `failed_retryable`, `blocked_manual_review` (recovery
  loop). **[Accepted — DEC-009]**
- **Error classes (16, fixed):** per Part A §D.4; no 17th class; only
  `ambiguous match` is widened (deterministic fulfillment-location
  mismatch — DEC-015 point J).
- **Manual-review sub-reasons (6):** ambiguous match; binding conflict;
  duplicate risk; destructive-write guard blocked; inventory location
  missing; fulfillment notification confirmation missing.
- **Retry UI cases (4):** auto-retry in progress / safe to retry now /
  fix first / verify before retry. **[Accepted — DEC-009; Part D §4.1]**
- On-screen state words are plain language; internal tokens never render
  as primary labels (**MBQ-22** governs final strings).

Store connection states (Part D §6 proposal): `Connected / Setup
incomplete / Disconnected / Reconnect needed` — a store-level status
vocabulary, distinct from job states.

---

## Flow 1 — Setup flow

- **Start condition.** Module installed; no store configured (or wizard
  re-entered from `Configuration`); user is a Connector Administrator.
- **Happy path.** Wizard steps 1→11 (accepted 11-step set): welcome/
  prerequisites → store identity → credential entry (masked; never read
  back) → scope presentation → Test Connection (pass, with reason) →
  readiness checks (all "must pass" green — DEC-018 MBQ-06 split) →
  per-domain direction choices (DEC-003-supported only) → source-of-truth
  choices (explicit, both required) → notification default (off; explicit
  opt-in only) → inventory first-push **scheduling** → final readiness
  summary (plain-language confidence statement) → Activate → store =
  `Connected`; Dashboard shows "first sync not started" guidance.
- **Exception paths.**
  - Test Connection fails → stay on step; named cause + fix; retry in
    place. No store state change.
  - Essential readiness check fails → Activate blocked; failing checks
    listed with fix links; warnings ("good to fix") never block.
  - Operator exits early → store = `Setup incomplete`; the exact remaining
    steps are listed; **no business sync/write job runs**;
    `setup_readiness_check` / `export_preview_dry_run` jobs may run
    read-only. **[Accepted — DEC-012 §1]**
  - Incomplete first-push scheduling blocks **inventory** writes only —
    product/order sync proceeds if otherwise ready.
- **Terminal states.** `Connected` (active); `Setup incomplete`
  (safe-idle). The wizard itself has no failed terminal state — it is
  always resumable.
- **User decision points.** Domain directions; source of truth (matching +
  price); notification opt-in; first-push now/later.
- **System actions.** Credential save (masked); test/readiness jobs
  (`setup_readiness_check`, read-only); persistence of every choice on
  durable records so re-running resumes.
- **Safety guards.** No business sync before completion; no silent
  defaults for direction/source-of-truth/notification; first-push never
  auto-completed; credential never read back; no encryption claims in
  copy (MBQ-04 posture).
- **Logs/audit events.** Each readiness/test run logged as a job; each
  wizard completion records the choices; activation timestamped.
- **Premium UX treatment.** One decision per step; per-step verified
  moments; the closing confidence statement in merchant language; calm
  failure handling that never ejects the user from the flow.
- **Unresolved implementation details.** Credential internals (MBQ-04
  task); token-acquisition walkthrough (MBQ-05); readiness thresholds/copy
  (MBQ-06 residual, MBQ-22); wizard XML (MBQ-03).

---

## Flow 2 — Connect / test / activate flow (re-run and reconnect)

- **Start condition.** An existing store in `Reconnect needed` or
  `Disconnected` (auth failure, revoked token, deliberate disconnect), or
  an Admin re-validating a live store.
- **Happy path.** Health indicator / settings band → Reconnect → re-enter
  credential (masked) → Test Connection pass → readiness re-run (required
  on reconnect — **[Decided — DEC-018 MBQ-08]**) → store = `Connected` →
  paused enqueue resumes.
- **Exception paths.** Invalid credential → named failure, stay in flow;
  readiness regression (e.g. scope removed) → blocked with the specific
  check + fix; user abandons → store remains `Disconnected`/`Reconnect
  needed`, clearly labelled; no partial resumption.
- **Terminal states.** `Connected`; or unchanged disconnected state.
- **User decision points.** Proceed with reconnect; re-confirm nothing
  else (settings persist — reconnect is not a re-setup).
- **System actions.** While disconnected: no new business job is enqueued
  or executed; webhooks not processed for the store; existing history
  untouched. On reconnect: readiness jobs, then resume.
- **Safety guards.** Disconnect revokes/removes credentials and disables
  sync/webhook enqueue but **preserves store, bindings, jobs, logs, audit,
  mapping/error history**; reconnect is explicit and audited — never
  automatic. **[Decided — DEC-018 MBQ-08]**
- **Logs/audit events.** Disconnect (who/when), reconnect (who/when),
  readiness results, resumption.
- **Premium UX treatment.** Reconnect copy leads with reassurance
  ("everything is safe and waiting"); the flow is three moments, not a
  second setup.
- **Unresolved details.** Exact disconnect/reconnect state-machine fields
  (MBQ-01/02 residuals); credential replacement mechanics (MBQ-04 task).

---

## Flow 3 — Product import flow (Shopify → Odoo)

- **Start condition.** Store `Connected`; product domain enabled; trigger
  = operator (`manual_sync`), timer (`scheduled_sync`), webhook
  (enqueue-only, follow-up authoritative read — **[Decided — DEC-020
  MBQ-65]**), or `reconciliation`.
- **Happy path (automated trigger).** Job `queued` → `running` →
  pre-create gate: eligibility conditions (setup complete; domain enabled;
  source strategy permits) + duplicate check + match-quality conditions →
  confident match → bind/update; confident no-match → create + bind →
  `succeeded`; fully logged (audit visibility, never presented as a
  preview). **[Accepted — DEC-014 point H (MBQ-59)]**
- **Happy path (interactive/batch).** Operator stages an import → blocking
  preview "will create N, link M, N ambiguous" → confirm → `succeeded`.
- **Exception paths.**
  - Eligibility fails → job not enqueued, or cancelled with audit reason
    (never a review item). **[Accepted — DEC-014 point H]**
  - Ambiguous match / binding conflict / duplicate risk →
    `blocked_manual_review` with the specific sub-reason → Reviewer
    resolves in the matching center.
  - Data-shape mismatch → `failed_retryable` (fix then retry).
  - Throttle/temporary → `retry_waiting` (auto-retry with backoff).
  - `PRODUCTS_DELETE` webhook → enqueue-only, follow-up authoritative
    read; never **directly** deletes/archives the bound Odoo product;
    exact post-read handling of a confirmed deletion remains
    implementation mechanics. **[Decided — DEC-020 MBQ-65]**
- **Terminal states.** `succeeded`, `failed_final`, `skipped` (with
  reason), `cancelled`.
- **User decision points.** Interactive preview confirmation; manual match
  choices; skip decisions.
- **System actions.** Follow-up authoritative read after webhook enqueue;
  binding creation with audit fields; reconciliation backstop.
- **Safety guards.** No blind create (gate/preview); match-key priority
  (binding → SKU → barcode → manual; name advisory only — RA-006); no
  autonomous bidirectional conflict ownership (DEC-003).
- **Logs/audit events.** Per-record log lines; binding audit
  (matched-by/at/strategy/key); gate outcomes.
- **Premium UX treatment.** Preview as the centre of gravity; skips always
  carry reasons; automated activity reads as a calm timeline, not a
  surprise.
- **Unresolved details.** Webhook payload/subscription mechanics (MBQ-63
  descoped); domain binding model names (MBQ-55).

---

## Flow 4 — Customer matching flow

- **Start condition.** Customer data arrives via order import or customer
  import; sale domain enabled.
- **Happy path.** Binding exists → reuse. Else email match (sole automatic
  key — **[Accepted — DEC-014 point E (MBQ-31)]**) → exactly one confident
  candidate → bind (audited); no candidate → create via the pre-create
  gate → bind.
- **Exception paths.**
  - Multiple email candidates → `ambiguous match` →
    `blocked_manual_review` → Reviewer picks (phone/name shown as advisory
    hints only, never auto-bind).
  - Duplicate risk on create → blocked pending Reviewer confirmation.
  - Genuine no-PII order → the single flagged fallback partner per store —
    visibly marked, never used for ordinary match failures. **[Accepted —
    Part B §B.7; DEC-014 point D]**
  - One bad customer record does **not** block order import (three-path
    rule). **[Accepted — Part B §C.6]**
- **Terminal states.** Bound (audited); created + bound; fallback-assigned
  (flagged); review-resolved.
- **User decision points.** Reviewer's match/create/fallback decision on
  ambiguity.
- **System actions.** Email normalization/lookup; gate; audit.
- **Safety guards.** No name-only auto-match (RA-006); no customer export
  (DEC-003); PII minimization — screens show match evidence, not full
  profiles (a design discipline under the accepted conservative
  protected-data posture, Part B §B.10).
- **Logs/audit events.** Match key used; who resolved ambiguity; fallback
  usage counts.
- **Premium UX treatment.** Reviewer sees a clean side-by-side evidence
  card; fallback usage is honest and visible, never cosmetic.
- **Unresolved details.** Fallback partner naming (MBQ-29 Resolved via
  AR-020; only naming is task-spec detail). (MBQ-09's own open residual is
  compliance-webhook-scoped and does not constrain these screens.)

---

## Flow 5 — Order import flow

- **Start condition.** Sale domain enabled; trigger = webhook (enqueue-only
  + authoritative read), scheduled, manual, or reconciliation.
- **Happy path.** Order fetched → identity/duplicate check (no re-import)
  → same-currency check passes (`presentmentCurrencyCode ==
  currencyCode` — **[Decided — DEC-020 MBQ-64]**) → product lines resolve
  via bindings → customer resolves (Flow 4) → financial evidence captured
  (lines/tax/shipping/discount/payment + gateway label → journal
  *classification only*) → total-check guard passes → sale order created →
  `succeeded`.
- **Exception paths.**
  - Unmatched product line → **whole-order hold** = `mapping missing` =
    `failed_retryable` → fix in matching center → retry (two clicks).
    **[Accepted — Part B §C.5; DEC-014 point I]**
  - Total mismatch → `financial total mismatch` (own conservative posture,
    never silent, not a review sub-reason) → inline breakdown in the error
    center → fix → retry.
  - Divergent currency → blocked **before** SO creation → manual review /
    unsupported-scope handling; currency evidence captured in every case.
    **[Decided — DEC-020 MBQ-64]**
  - Ambiguous customer → Flow 4 exception; order proceeds per the
    three-path rule where accepted.
  - `ORDERS_UPDATED` (or reconciliation-detected change) on an imported
    order → **evidence refresh only**; never a silent SO line/price/tax/
    shipping/discount/invoice/payment/refund/fulfillment update;
    divergence routes through the total-check posture. **[Accepted — Part
    B §C.12; DEC-014 point J]**
- **Terminal states.** `succeeded` (SO created); `failed_final`;
  `skipped`; `cancelled`; held states are recovery states, not terminal.
- **User decision points.** Resolving holds (matching, totals); no
  invoice/payment decisions — none are automated (Part B §C.11).
- **System actions.** Evidence capture (always, including on blocks);
  duplicate prevention on order identity; journal *suggestion* only.
- **Safety guards.** Total-check guard mandatory and unbypassable; no
  accounting automation; order edits/refunds/returns deferred (DEC-003).
- **Logs/audit events.** Evidence records; hold reasons; guard outcomes;
  refresh events.
- **Premium UX treatment.** The financial breakdown reads like a receipt
  comparison, not a JSON diff; held orders state plainly *why holding is
  the safe choice*.
- **Unresolved details.** Tolerance + exact total field (MBQ-56,
  descoped); tax representation (MBQ-27, descoped); divergent-currency
  class mapping (DEC-020 residual).

---

## Flow 6 — Inventory sync flow

- **Start condition.** Inventory domain enabled; ≥1 mapped location pair
  (S10); quantity source-of-truth recorded (S12).
- **Happy paths.**
  - **Baseline import (one-time, controlled):** Shopify → Odoo preview
    (SKU/variant/location/quantity) → review → apply → baseline recorded.
    **[Accepted — DEC-003; Part C §A.3]**
  - **First push (per store + mapped pair + product/variant binding —
    [Decided — DEC-018 MBQ-33]):** preview rows → skip/manual-match
    ambiguous rows → explicit confirmation → confirmation record persisted
    (snapshot/confirmer/timestamp/source-of-truth/scope) → push enqueued →
    `succeeded`.
  - **Ongoing writes (review-then-apply default — [Decided — DEC-018
    MBQ-34]):** change detected (`odoo_event` stock-change trigger origin,
    or scheduled/manual) → apply queue entry → operator reviews the same
    preview shape → apply → verify.
- **Exception paths.**
  - Unmapped location → `inventory location missing`
    (confirmation-required) → fix link to S10; never guessed.
  - Ambiguous item mapping → `ambiguous match` review.
  - Drift found by reconciliation → distinct mismatch exception; never
    auto-resolved (RA-020/RA-021).
  - Throttle → `retry_waiting` with compare-and-set semantics (accepted
    `inventorySetQuantities` direction — MBQ-36 partial).
- **Terminal states.** Per job: the accepted terminal set. Per pair: the
  first-push confirmation record is the durable "guard satisfied" state.
- **User decision points.** Baseline apply; first-push confirmation;
  each ongoing apply; drift resolutions.
- **System actions.** Preview computation; enqueue; reconciliation
  backstop; per-pair guard tracking.
- **Safety guards.** `committed` never a write target anywhere,
  structurally (RA-018); `available` is the **sole** Phase 1 write target
  (`on_hand` not exposed in Phase 1 UI — MBQ-35 resolved by conservative
  exclusion, AR-020); first-push guard unbypassable by any flag (Part A
  §I.5); auto-apply does not exist in Phase 1 UI.
- **Logs/audit events.** Confirmation records; every apply logged
  who/when; drift reports retained.
- **Premium UX treatment.** The first push feels like signing a document
  you actually read; the ongoing queue is a two-minute morning routine,
  not a chore.
- **Unresolved details.** Quantity-source mechanism (MBQ-32 residual);
  confirmation-record schema (MBQ-38 residual); batched-review UI
  composition (open design detail); inventory webhook import scope
  (MBQ-63, descoped).

---

## Flow 7 — Fulfillment / tracking flow

- **Start condition.** Fulfillment domain enabled; imported, bound order;
  a validated `stock.picking` (the only trigger — RA-023);
  `stock_delivery`/`delivery` present (else tracking write-back is
  readiness-blocked, never silently degraded — **[Decided — DEC-018
  MBQ-60]**).
- **Happy path.** Picking validated (`odoo_event`, picking-validation
  trigger origin) → match order → its open FulfillmentOrder(s) → lines/
  quantities/location matched as one unit → notification decision read
  from the store default (off unless opted in) and **persisted on the job
  at enqueue** → fulfillment created → tracking
  (`carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id`) written →
  `succeeded`; entry shows the matched sentence + notification
  requested/suppressed.
- **Exception paths.**
  - Picking doesn't match exactly one FulfillmentOrder's open lines →
    `blocked_manual_review` — never auto-guessed (RA-023).
  - Location mismatch (live `assignedLocation` read disagrees) → widened
    `ambiguous match` → Reviewer confirms. **[Accepted — Part C §B.8]**
  - Ambiguous outcome (timeout on create/tracking call) → **verification
    read before any retry**; inconclusive → manual review (RA-014).
  - Backorder split → the backorder picking is its own fulfillment event.
  - Multi-location/multi-package spread → manual review (deferred
    automation — DEC-003).
  - Tracking-only update → visibly distinct event; never a second
    fulfillment (operation-level idempotency key — RA-017 avoided).
- **Terminal states.** `succeeded` (fulfillment + tracking recorded);
  `failed_final`; review states as recovery loop.
- **User decision points.** Reviewer confirmations (mismatch,
  notification-confirmation-missing); Admin notification default.
- **System actions.** FulfillmentOrder-exclusive mutations (RA-022);
  serialization against the same target while an ambiguous op is
  unresolved.
- **Safety guards.** Notification default off, never re-read on retry
  (RA-009); no double fulfillment; no fulfillment without the full match.
- **Logs/audit events.** Matched unit; notification requested/suppressed
  per entry; verification-read outcomes.
- **Premium UX treatment.** "No surprise emails" is a visible product
  promise: the notification decision is legible on every single entry.
- **Unresolved details.** FO hold/lifecycle handling (MBQ-61, descoped);
  backorder wizard copy nuance (MBQ-40 residual).

---

## Flow 8 — Error retry / recovery flow

- **Start condition.** Any job in `failed_retryable`, `retry_waiting`, or
  `blocked_manual_review`; or a terminal `failed_final` needing
  re-trigger.
- **Happy paths (per accepted retry case).**
  - (a) Auto-retry: `retry_waiting` → backoff → `queued` → `succeeded`;
    UI shows "next attempt ~…", no button.
  - (b) Safe manual retry: operator clicks Retry → `queued` →
    `succeeded`.
  - (c) Fix first: operator performs the suggested fix (map location,
    match product) → Retry unlocks → `succeeded`.
  - (d) Verify before retry: Verify current state → "already applied" →
    resolved without a second write; "not applied" → Retry unlocks;
    inconclusive → manual review. **[Accepted — DEC-009 ambiguous-outcome
    rule]**
- **Exception paths.** Retry exhaustion → `failed_final` + error-center
  entry ("we stopped retrying — here's why"); recovery from terminal =
  explicit re-trigger (a new job), clearly labelled as such; bulk retry →
  same per-item logic, ineligible items reported.
- **Terminal states.** `succeeded`; `failed_final` (with re-trigger
  path); `cancelled`.
- **User decision points.** Retry/verify/resolve choices; Reviewer
  confirmations; assignment.
- **System actions.** Classified retry policy per class; backoff
  (accepted adjustable defaults — MBQ-16); serialization guard.
- **Safety guards.** No blanket retry (RA-014); no never-retry
  (RA-015); no flag bypasses classification; blind retry of
  ambiguous-outcome writes structurally impossible.
- **Logs/audit events.** Every attempt/verify/resolve with who/when/
  outcome.
- **Premium UX treatment.** The operator never computes safety in their
  head — the UI states the case and the why, in one line.
- **Unresolved details.** Backoff constants remain adjustable
  implementation defaults (MBQ-16 resolved at that level); retry copy
  (MBQ-22).

---

## Flow 9 — Disconnect / reconnect flow

- **Start condition.** Admin chooses Disconnect (or auth failure forces
  `Reconnect needed`).
- **Happy path (disconnect).** Disconnect action → consequence-stating
  confirmation (sync stops; credentials removed; **history/bindings/logs
  preserved**) → store = `Disconnected`; enqueue disabled; dashboard
  reflects the state calmly.
- **Happy path (reconnect).** Flow 2 (credential → test → readiness →
  resume), explicit and audited.
- **Exception paths.** In-flight jobs at disconnect: no new enqueue; the
  confirmation states what happens to queued/in-flight work — per the
  accepted Part A §I.4 rule it is cancelled with an audit reason **or**
  held in an accepted blocked state, never silently dropped; the exact
  disposition remains implementation planning **[Open item — Part A
  §I.4]**. Abandoned reconnect leaves the labelled disconnected state.
- **Terminal states.** `Disconnected` (stable, safe, reversible);
  `Connected` after reconnect.
- **User decision points.** The confirmation itself; nothing else — no
  data-retention choices (the posture is decided, not optional).
- **System actions.** Credential revocation/removal; enqueue disable;
  audit entries; readiness re-run on reconnect.
- **Safety guards.** History never destroyed (**[Decided — DEC-018
  MBQ-08]**); domain disable ≠ uninstall — uninstall is not a supported
  merchant operation (**[Decided — DEC-018 MBQ-54]**); reconnect never
  implicit.
- **Logs/audit events.** Disconnect/reconnect who/when; job cancellations
  with reasons.
- **Premium UX treatment.** Disconnecting feels safe, not destructive —
  the confirmation reads like a pause, and reconnect copy honours that
  promise.
- **Unresolved details.** Exact state-machine/field mechanics (MBQ-01/02
  residuals); queued-job disposition copy (MBQ-22).

---

## Cross-flow guarantees (summary)

| Guarantee | Flows | Basis |
| --- | --- | --- |
| No business write before setup complete | all | DEC-012 §1 |
| Preview or pre-create gate before every create/bind/destructive write | 3–7 | DEC-006; DEC-014 point H; Part A §I.5 |
| Per-class routing — review queue only for the 6 sub-reasons | 3–8 | DEC-014 point I |
| Verification read before ambiguous-outcome retry | 3, 5–8 | DEC-009 |
| History survives disable/disconnect | 2, 9 | DEC-018 MBQ-08/54; Part A §I.4 |
| Notification off by default, persisted per job | 7 | DEC-007 §5; DEC-018 MBQ-41 |
| `committed` never written | 6 | DEC-010; RA-018 |
| One shared surface; no per-domain forks | all | RA-013 |

## No implementation authorized

Docs-only. These flows authorize no code and open no gate; each maps to
future tasks in
[`../07-implementation-plan/ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md).
