# Data Integrity and Idempotency Test Plan

> Docs-only test-planning package covering duplicate prevention, binding
> uniqueness, and idempotency, part of the
> [MVP QA and Test Strategy](./mvp-qa-test-strategy.md). **Historical
> drafting baseline:** `Shopify-connector` at
> `f74aaf204745ce0087733870fe56bdda74bfa79a`. Built from the accepted
> core naming/schema
> ([`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md),
> AR-019) and the domain architecture documents
> ([`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md),
> [`master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)).
> **Docs-only. No implementation. No gate opened by this document.**
> **Freshness note (2026-07-07 revision):** `Shopify-connector` has since
> also merged PR #93 (`ac250f7fd2f242df7b69f78dc619b0a71680c664`), PR #94
> (Task 002 decision closure — AR-025,
> `03ffcb4dc949cd5137b589a6cdc33da9105de31d`), and PR #96 (Task 002
> credential-storage gate — AR-026,
> `02b159a39c58a3396c1c249e80896a05c97bb757`). **The Task 002
> credential-storage gate is now open**; the credential-binding-adjacent
> content below (e.g. the "target-less job repeat-run risk" section)
> remains QA planning for whichever task actually resolves it — this
> document neither opened that gate nor implements against it. Task 003
> remains not started/not authorized.

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened by this document. Does not create tests.** As of the 2026-07-07
freshness revision, the Task 002 credential-storage gate is open
(AR-026/PR #96); this document's own content and status are otherwise
unchanged.

## Store uniqueness

- The `shopify.connector.store` model is the DEC-006 store-scoping anchor
  every other core model references. A future test must confirm
  `store_id` is `required` on every scoped model (`store.settings`,
  `location`, `job`, and, once it exists, `store.credential`) and that no
  record of any of these models can exist without a valid store
  reference.
- `shopify.connector.store.settings` is a one-row-per-store model
  (mirroring the accepted pattern the future credential model also
  follows) — a future test must assert a duplicate settings row for the
  same store raises a uniqueness violation (per the Task 001A manual
  checklist item 8, not yet executed against a runtime).

## Binding uniqueness

- Each domain owns its own concrete binding model extending the shared
  abstract `shopify.connector.binding.mixin` contract (no table on the
  abstract model itself): product-template binding, product-variant
  binding, customer binding, and order binding (product/customer/sale
  domains — MBQ-55, exact model/field names still open); inventory-level
  binding keyed `(store, inventory_item_id, location_id)`; FulfillmentOrder/
  Fulfillment binding keyed `(store, Shopify FulfillmentOrder GID)`
  (inventory/fulfillment domains).
- **Store-scoped uniqueness** is the accepted cross-cutting rule (Part A
  §C.2) — every binding model's uniqueness constraint is scoped per store,
  never globally, since the same Shopify GID format could theoretically
  collide across two independent stores' data.
- A future test suite must assert, per binding model: (a) a duplicate
  binding for the same `(store, Shopify-side identifier)` tuple cannot be
  created (unique constraint or equivalent guard); (b) two different
  stores may each hold a binding referencing what looks like the "same"
  Shopify-side identifier value without conflict (proving the scoping is
  genuinely per-store, not accidentally global).
- Product-template and product-variant bindings are held as **two
  separate** binding records (independent Shopify GIDs) — a future test
  must confirm a template binding is never treated as standing in for its
  variants' own bindings, and vice versa.

## Shopify GID uniqueness

- No formal "Shopify GID uniqueness" constraint independent of the
  store-scoped binding uniqueness above is documented in either
  architecture document read for this sprint — **this plan does not
  assert one exists as a separate mechanism.** The uniqueness guarantee a
  future test suite should verify is exactly the store-scoped binding
  uniqueness above (per-domain binding model, per-store), not a
  standalone global-GID-registry mechanism.
- Shopify GID **permanence** (whether a GID is ever reused after
  deletion) is an explicitly **open, unresolved fact** in the register
  (MBQ-12, "accepted-open risk," containment: the accepted binding-based
  defensive design covers the general case). A future test suite must not
  assume GID permanence — it should specifically test the stale/
  recreated-binding path (below) rather than assuming a GID, once seen,
  is stable forever.

## Odoo record matching

- Match-key priority is uniform across the product, variant, and customer
  domains: **existing binding → SKU/internal reference (product) or email
  (customer, the sole automatic key) → barcode (product only) → manual**;
  name is advisory-only, **never** an automatic match key for any domain
  (RA-006).
- A future test suite must assert this exact priority order is respected —
  e.g. a record with both a stale binding and a valid SKU match must
  route through the binding-staleness handling (below), not silently fall
  through to the SKU match as if no binding existed.

## Idempotency key behavior

- `idempotency_key` (on `shopify.connector.job`, computed + stored, unique
  with `store_id`) is composed from `store_id` + `job_type` +
  `res_model`/`res_id` + `shopify_target_gid` + `payload_hash`. It answers
  "is this the same operation, same target, same payload, already known?"
  and persists for the life of the job.
- This is **distinct** from `operation_scope_key` (below) — a future test
  suite must exercise both keys independently, not treat them as
  interchangeable, since they answer different questions (identity vs.
  serialization).
- **Known latent collision risk (explicitly flagged, not yet resolved):**
  a target-less job (e.g. `setup_readiness_check`/the proposed
  `core_test_connection`) leaves the `res_model`/`res_id`/
  `shopify_target_gid`/`payload_hash` components empty, so a **second run
  of the same job type on the same store would collide** with the
  `(store_id, idempotency_key)` unique constraint as currently merged.
  The proposed resolution (a per-run `payload_hash` nonce, e.g. a UUID,
  for target-less interactive check jobs) is a **named ChatGPT decision
  point for Task 003**, not decided by this plan. A future test suite
  must include a test that runs the same target-less job type twice on
  the same store and asserts the second run succeeds — this test will
  fail against the current merged key semantics until Task 003's
  resolution lands, which is the point of writing it now: it documents
  the exact acceptance bar Task 003 must clear.

## Operation scope serialization

- `operation_scope_key` (nullable, unique with `store_id`) is the
  DB-backed serialization guard, computed from the coarser tuple
  `store_id` + `res_model` + `res_id` + `shopify_target_gid` —
  deliberately **excluding** `job_type`/`payload_hash` — so any concurrent
  operation against the same target is blocked regardless of what kind of
  operation it is. It is populated while a job is non-terminal and set to
  `NULL` on reaching a terminal state or being superseded.
- A future test suite must assert: (a) two non-terminal jobs targeting the
  same `(store, res_model, res_id, shopify_target_gid)` cannot coexist
  (unique-constraint collision); (b) a job reaching any terminal state
  clears its `operation_scope_key` to `NULL`, freeing the target for a new
  operation; (c) a superseded job also clears its `operation_scope_key`
  (this is the F1 fix already merged in PR #88 per Task 001A — a future
  test should re-confirm it still holds, not merely assume it).

## Duplicate prevention

- **Pre-create gate (MBQ-59), uniform across product/customer/order-
  triggered-customer creation:** every automated create/bind action must
  pass (1) eligibility conditions (store setup complete; domain enabled;
  first-sync source strategy permits import-side creation) and then (2)
  match-quality conditions (a confident, unambiguous match or a confident
  no-match creation candidate; no `ambiguous match`/`binding conflict`/
  `duplicate risk`/`destructive-write guard blocked` triggered). Failure
  of (1) means the job is never enqueued, or is cancelled with an audit
  reason — **never** presented as a `blocked_manual_review` confirmation
  case. Failure of (2) routes to `blocked_manual_review` with the specific
  sub-reason.
- **No bypass, structurally enforced:** no feature flag, setting, or
  configuration combination may allow an automated import to skip either
  gate stage. A future test suite should include a negative test that
  attempts every plausible bypass vector (a setting toggle, a batch-size
  parameter, a "force" flag if one is ever proposed) and asserts each one
  fails to skip the gate.
- **Interactive/batch creates are unaffected and additionally gated:** a
  blocking, synchronous preview ("will create N, link M, N ambiguous")
  is required before the operator confirms, independent of the automated
  pre-create gate above. Retrospective sync-center/dashboard visibility
  of an automated action is **never** a substitute for this preview on an
  interactive/batch action.

## Safe retry

- Mutation-level idempotency: for inventory, both `inventorySetQuantities`
  and `inventoryAdjustQuantities` are on Shopify's 17-mutation
  `@idempotent`-eligible list and require `@idempotent` as of API version
  2026-04 — a persisted, reused idempotency key within the 24-hour dedup
  window makes a retry of these specific mutations safe.
- Neither `fulfillmentCreate` nor `fulfillmentTrackingInfoUpdate` is on
  that `@idempotent`-eligible list — a future test suite must confirm
  that any ambiguous-outcome failure (timeout/connection loss with
  unknown result) on these two mutations triggers a **safe verification
  read** (re-query the order's Fulfillments/FulfillmentOrder status)
  **before** any retry attempt, never a blind retry (DEC-009's
  ambiguous-outcome rule, RA-014).
- A compare-and-set write (`inventorySetQuantities`) whose
  `compareQuantity` no longer matches Shopify's current value is a
  `concurrency/race conflict` — auto-retried with backoff **after a fresh
  read**, never blindly resubmitted with the stale comparison value.

## Failed job recovery

- `failed_retryable` is the recovery state for "manual fix then retry"
  classes (`mapping missing`, `data shape/schema mismatch`,
  Odoo/Shopify validation classes, Shopify permission/scope/auth) — a
  future test must confirm a job in this state returns to `queued`
  automatically once its named blocking condition resolves (e.g. the
  previously-unmatched product becomes bound), without requiring a manual
  "retry" click for that specific resolution path where the architecture
  says so (the whole-order-hold example: "at which point the job returns
  to `queued` and the order import resumes/retries through the normal job
  path").
- `retry_waiting` is the auto-retry-with-backoff state for transient
  classes (throttling/rate-limit, temporary/server/network,
  concurrency/race conflict) — a future test must confirm the backoff
  actually elapses before the next attempt (no busy-retry loop) and that
  the UI shows "next attempt ~…" with **no** retry button for this case
  specifically (retry UI case (a), "auto-retry in progress").

## Terminal/superseded job behavior

- Terminal states (`succeeded`, `failed_final`, `skipped`, `cancelled`)
  each clear `operation_scope_key` to `NULL` (see §Operation scope
  serialization above).
- A superseded job (cancelled because a newer job now covers the same
  scope) also clears `operation_scope_key`, and — per the accepted
  `job.log` design — is never destroyed; its log rows survive
  (`job.log.job_id` uses `ondelete='restrict'`, not cascade), so a
  superseded job's history remains queryable.
- A future test suite must assert a `failed_final` job carries **no**
  retry control in the UI (only an explicit re-trigger path that creates
  a **new** job, clearly labelled as such — never a UI action that
  resurrects the terminal job itself).

## Target-less job repeat-run risk

- See §Idempotency key behavior above — this is the same latent
  `(store_id, idempotency_key)` collision risk, restated here under its
  own required heading per this sprint's structure. It affects
  `setup_readiness_check` jobs today (both the existing
  `core_readiness_check` job type and the proposed `core_test_connection`
  job type) and is a **named ChatGPT decision point for Task 003**
  (per-run `payload_hash` nonce), not resolved by this plan. A future test
  suite's job-accounting test ("a second run on the same store succeeds")
  is the acceptance bar Task 003 must clear before this risk is closed.

## Manual retry behavior

- A manual retry (retry UI case (b), "safe to retry now") transitions a
  job from `failed_retryable` (once its blocking condition is
  independently resolved, e.g. via the "fix first" case (c)) back to
  `queued` on an explicit operator click. A future test must confirm this
  transition does not re-run any already-succeeded sub-step of the
  operation (no double-application of a partially-completed write) —
  exact partial-completion semantics are this sprint's own open item,
  flagged for the relevant domain's future task spec rather than invented
  here.
- Bulk retry (operating on multiple jobs at once) applies the same
  per-item classified-retry logic as a single retry — a future test
  should confirm ineligible items in a bulk retry are individually
  reported, not silently skipped or silently force-retried.

## No silent overwrite

- Disconnect clears the credential value but **never** unlinks the store,
  credential row, settings, bindings, jobs, logs, audit, or mapping/error
  history (MBQ-08) — a future test must assert every one of these record
  types survives a disconnect with its content unmodified (only new
  disconnect-audit entries are added).
- An `ORDERS_UPDATED` webhook or reconciliation-detected change never
  silently overwrites an existing sale order's lines/prices/taxes/
  shipping/discounts/invoices/payments/refunds/fulfillment state — any
  divergence routes through the total-check guard / human-review posture
  instead of an automatic write (DEC-014 point J).
- A `PRODUCTS_DELETE` webhook never directly overwrites (deletes/archives)
  the bound Odoo product without a follow-up authoritative read first
  (DEC-020 / MBQ-65).

---

## Specific future checks by binding type

### Product binding

- Duplicate binding for the same `(store, Shopify Product GID)` blocked
  by a uniqueness constraint.
- A stale/recreated Shopify product ID (the Shopify-side product was
  deleted and a new one created with a new GID) is marked stale/routed to
  review — never silently re-created or hijacked onto the old binding.
- Match-key priority (binding → SKU → barcode → manual, name advisory
  only) exercised in a test with a record that could match on more than
  one key, asserting the binding takes precedence.

### Variant binding

- Duplicate binding for the same `(store, Shopify ProductVariant GID)`
  blocked, independently of its parent template's binding state.
- A `productSet` write omitting a variant is asserted (fixture-level) to
  delete that variant Shopify-side per the official `productSet`
  reconciliation behavior — a future test must confirm the
  destructive-write guard blocks this write path until a rendered,
  confirmed preview exists, rather than allowing a silent variant
  deletion.

### Customer binding

- Duplicate binding for the same `(store, Shopify Customer GID)` blocked.
- Email-only automatic matching (MBQ-31) exercised with a fixture
  containing a phone/name match but no email match, asserting no
  automatic bind occurs (routes to manual review or creation instead,
  per the accepted rule that phone/name are advisory-only).
- The single fallback partner per store is exercised only via a genuine
  no-PII fixture — a future test must assert a fixture with *some* PII
  present, even if it fails to match, does **not** route to the fallback
  partner (it routes through the ordinary creation/matching path
  instead).

### Order binding

- Duplicate binding for the same `(store, Shopify Order GID)` blocked —
  the order binding is the **sole** idempotency anchor for order
  creation; a repeated webhook or reconciliation pass must match the
  existing binding and update, never re-create.
- A whole-order-hold fixture (an order with one resolvable and one
  unresolvable product line) asserts the **entire** order holds
  (`mapping missing` → `failed_retryable`), not just the unresolvable
  line.
- A divergent-currency order fixture asserts the order is blocked before
  SO creation regardless of whether its shop-currency total happens to
  reconcile against the total-check guard.

### Inventory export jobs

- Identity anchor `(store, inventory_item_id, location_id)` is the sole
  idempotency anchor — a future test must assert a re-processed inventory
  event updates the existing binding, never creates a duplicate.
- Operation-level idempotency (conceptually `(store, inventory_write,
  inventory_item_id, location_id, payload_hash)`) distinguishes a retried
  write of the *same* intended quantity (safe to dedupe) from a *new*
  intended quantity such as a superseding stock move (must not be
  conflated with the prior operation) — a future test must exercise both
  cases distinctly.
- The first-push guard's confirmation record is itself a durable,
  per-mapped-pair uniqueness concept — a future test must assert a
  mapped pair's first write cannot occur twice without two independent
  confirmation records (i.e. confirming once does not silently authorize
  unlimited future "first pushes" for a different pair).

### Fulfillment update jobs

- Identity anchor `(store, Shopify FulfillmentOrder GID)` (and the
  Fulfillment GID once created) — a future test must assert a
  re-processed fulfillment event matches the existing binding.
- A tracking-only update is asserted, by a dedicated test, to **never**
  create a second fulfillment (distinguishing it from a fulfillment
  creation via the operation-level idempotency key).
- A backorder-split picking is asserted to be its **own** fulfillment
  event (a distinct binding), never merged into the original picking's
  fulfillment record.

### Webhook enqueue-only behavior

- Every product webhook topic (`PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/
  `PRODUCTS_DELETE`) is asserted, by a dedicated test, to perform **only**
  an enqueue on receipt — no direct Odoo write occurs inside the webhook
  receiver itself. The enqueued job's own execution then performs the
  mandatory follow-up authoritative read before any create/update/delete
  is applied.
- An ambiguous or unconfirmable webhook-driven case (e.g. the follow-up
  read cannot resolve the product's current state) routes to manual
  review using the existing vocabulary — a future test must assert no
  new, invented error class or manual-review sub-reason is introduced for
  this path.

### Reconciliation backstop

- The same DEC-005 layered-sync reconciliation mechanism covers every
  domain (product/customer/order per DEC-014; inventory/fulfillment per
  DEC-015) — a future test suite should confirm a reconciliation pass
  uses the **same** binding/idempotency/error-class machinery as every
  other trigger, not a parallel or divergent mechanism.
- Reconciliation is the **mandatory correctness backstop** — a future
  integration test should simulate a drift scenario (Shopify-side state
  diverges from the last-known-pushed/imported state) and assert the
  reconciliation pass detects and flags it via the existing error-class
  registry, never silently self-correcting a financial or inventory
  discrepancy without an audit trail.
- Reconciliation cadence/scope is per-store/per-domain with a
  configurable conservative default (MBQ-17) — never one global
  cross-domain job; a future test should confirm two different stores
  (or two different domains on the same store) can run reconciliation on
  independent schedules without interfering with each other's job
  accounting.
