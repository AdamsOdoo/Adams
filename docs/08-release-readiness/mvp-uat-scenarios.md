# MVP UAT Scenarios

> Business-readable user-acceptance-testing scenarios for the connector
> MVP, part of the
> [MVP QA and Test Strategy](../05-qa/mvp-qa-test-strategy.md) package.
> Baseline: `Shopify-connector` at `f74aaf204745ce0087733870fe56bdda74bfa79a`.
> **These scenarios cannot be executed today** — they require a live Odoo
> 19 + PostgreSQL runtime and, for several scenarios, a Shopify
> development store, neither of which exists in this environment (see
> [`mvp-qa-test-strategy.md`](../05-qa/mvp-qa-test-strategy.md) §Runtime
> limitation strategy) — and they require the underlying tasks (Task 002
> onward) to be implemented, which they are not yet. This document plans
> the scenarios a future UAT pass must execute; it does not claim any of
> them have been run.

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened. No scenario below has been executed.**

## How to use this document

Each scenario names: purpose; preconditions; steps; expected result;
evidence to capture; a pass/fail rule; and the related module/task. A
future UAT reviewer should be able to execute a scenario exactly as
written, without needing to consult any other document to understand what
"pass" means. Every scenario referencing an unauthorized task (Task 002
onward, or the UI/wizard) is written as the target state that task's
future PR must satisfy — it is not a claim that the scenario can be run
against the codebase as it exists at this sprint's baseline.

**Plain-language first.** Each scenario's "Steps" and "Expected result"
are written for a business/operations reviewer — plain product language,
not internal code names. Where a precise internal identifier matters for
someone tracing the result back to a system record (a model name, an
exact field, an exact API method), it appears only in the "Evidence to
capture" line, in parentheses, so a non-technical reviewer can run the
scenario without needing a glossary, while a technical reviewer can still
find the exact record to inspect.

---

## 1. Connect store successfully

- **Purpose.** Confirm a merchant can complete the setup wizard end to end
  and reach an active, connected store.
- **Preconditions.** Module installed; no store configured; user has the
  Connector Administrator role; a Shopify development store and a valid
  (non-production) credential are available.
- **Steps.** (1) Open the setup wizard. (2) Complete Step 1 (welcome/
  prerequisites) through Step 4 (scope presentation). (3) At Step 5, run
  Test Connection. (4) At Step 6, confirm all essential readiness checks
  show green. (5) Complete Steps 7–10 (domain directions, source-of-truth
  choices, notification default, inventory first-push scheduling). (6) At
  Step 11, review the final readiness summary and click Activate.
- **Expected result.** Test Connection reports a named pass with a reason
  (never a silent spinner). All essential readiness checks pass; any
  warnings are visibly non-blocking. Store state becomes `Connected`. The
  dashboard shows a "first sync not started" guidance state, not an error.
- **Evidence to capture.** Screenshot or log excerpt of the Test
  Connection pass result; the readiness summary; the store's `state`
  field value after Activate; the job/log record for the test-connection
  and readiness-check jobs.
- **Pass/fail rule.** Pass only if the store reaches `Connected` with
  every essential check green and no business sync job ran before
  Activate was clicked.
- **Related module/task.** Task 002 (credential), Task 003 (test
  connection), Task 004 (readiness), Task 006 (wizard UI, horizon).

## 2. Failed credential and recovery

- **Purpose.** Confirm an invalid credential fails safely, with a
  business-friendly explanation, and that the operator can correct it
  without losing wizard progress.
- **Preconditions.** Same as Scenario 1, but the credential entered at
  Step 3 is deliberately invalid (e.g. a revoked or malformed token).
- **Steps.** (1) Enter the invalid credential at Step 3. (2) Proceed to
  Step 5 and run Test Connection. (3) Observe the failure. (4) Return to
  Step 3, correct the credential, and re-run Test Connection.
- **Expected result.** Test Connection fails with a named cause (e.g.
  "Shopify didn't accept this credential") and a suggested fix — never a
  raw HTTP status or stack trace as primary copy. The wizard stays on the
  step; no store-state change occurs. After correction, Test Connection
  passes and the wizard proceeds normally.
- **Evidence to capture.** The failure copy shown to the operator; the
  redacted technical-detail expand contents (confirm no token appears);
  the store's `state` field (must be unchanged, still `setup_incomplete`)
  after the failure.
- **Pass/fail rule.** Pass only if the failure is named and actionable, no
  token or raw error appears in primary copy, and the store's connection
  state does not change on failure.
- **Related module/task.** Task 002 (credential), Task 003 (test
  connection), Task 006 (wizard UI, horizon).

## 3. Import simple product

- **Purpose.** Confirm a single-variant Shopify product imports correctly
  into Odoo with a durable binding.
- **Preconditions.** Store `Connected`; product domain enabled; a simple
  (single-variant) product exists on the Shopify development store with
  no matching Odoo product yet.
- **Steps.** (1) Trigger a product import (manual sync, or wait for
  scheduled sync). (2) Observe the job outcome. (3) Re-trigger the same
  import a second time.
- **Expected result.** First run: the product is created and bound; the
  job reaches `succeeded`; the create/bind action is logged with
  matched-by/matched-at/source-strategy/match-key/status audit fields.
  Second run: the existing binding is matched and the record is updated,
  **not** duplicated.
- **Evidence to capture.** The Odoo product record and its binding; the
  job/log entries for both runs; confirmation that only one Odoo product
  record exists after both runs.
- **Pass/fail rule.** Pass only if exactly one Odoo product exists after
  two import runs, and the second run's job/log shows an update path, not
  a second create.
- **Related module/task.** Product import domain slice (not yet gated or
  scoped as its own task at this sprint's baseline).

## 4. Import variant product

- **Purpose.** Confirm a multi-variant Shopify product imports with all
  variants correctly bound and option/attribute data mapped.
- **Preconditions.** Store `Connected`; product domain enabled; a
  multi-variant product (e.g. size/color combinations) exists on the
  development store.
- **Steps.** (1) Trigger a product import for the multi-variant product.
  (2) Inspect the resulting Odoo product template and its variants.
- **Expected result.** The template and each variant are created with
  independent bindings (separate Shopify GIDs); options/option values map
  to Odoo attribute/attribute values; no variant is missing or merged
  incorrectly.
- **Evidence to capture.** The Odoo product template, its variant list,
  and each variant's binding record; the Shopify-side variant count vs.
  the Odoo-side variant count (must match).
- **Pass/fail rule.** Pass only if every Shopify variant has exactly one
  corresponding Odoo variant with its own binding, and option/attribute
  data is present and correct.
- **Related module/task.** Product import domain slice.

## 5. Import customer and match existing partner

- **Purpose.** Confirm an order's customer data matches an existing Odoo
  partner by email rather than creating a duplicate.
- **Preconditions.** Store connected; sale domain enabled; an existing
  Odoo contact record already has the same email address as a Shopify
  development-store customer who has not yet placed a linked order.
- **Steps.** (1) Import an order from that Shopify customer (see Scenario
  6). (2) Check which Odoo contact the order ends up linked to.
- **Expected result.** The order links to the **existing** contact — no
  duplicate contact is created. The system matches customers by email
  address only; a similar phone number or name is never enough on its
  own to link an order to a contact.
- **Evidence to capture.** The contact record the order is linked to
  (Odoo model `res.partner`), showing email as the recorded match method;
  confirmation only one contact record exists for this customer after the
  import.
- **Pass/fail rule.** Pass only if the existing partner is reused (no
  duplicate created) and the binding's recorded match key is `email`.
- **Related module/task.** Customer matching domain slice.

## 6. Import same-currency order

- **Purpose.** Confirm a same-currency Shopify order imports into a
  correctly-created Odoo sale order with financial evidence captured.
- **Preconditions.** Store connected; sale domain enabled; a Shopify
  order exists that is priced in the store's own currency (not a
  different "customer-facing" currency — see Scenario 7 for that case);
  all ordered products are already imported.
- **Steps.** (1) Trigger order import (webhook, manual, or scheduled).
  (2) Inspect the resulting Odoo sales order.
- **Expected result.** An Odoo sales order is created with lines matching
  the Shopify order's lines. The system's automatic "do the numbers add
  up" check passes — the total it calculates from the imported lines,
  tax, shipping, and discounts matches the total Shopify reports, within
  an accepted tolerance. The order finishes successfully with no hold or
  review needed.
- **Evidence to capture.** The Odoo sales order and its lines (Odoo model
  `sale.order`); the order's link record back to the Shopify order; the
  totals-check breakdown (lines/tax/shipping/discount) recorded on the
  job log.
- **Pass/fail rule.** Pass only if the sales order's total matches
  Shopify's reported total within the accepted tolerance and the import
  finishes successfully with no manual-review or hold state.
- **Related module/task.** Order import domain slice.

## 7. Block divergent-currency order

- **Purpose.** Confirm an order placed in a different currency than the
  store's own currency is **never** silently imported as a normal Odoo
  sales order — the connector should hold it for review instead of
  guessing at a currency conversion.
- **Preconditions.** Store connected; sale domain enabled; a Shopify order
  exists that was priced in a currency different from the store's own
  currency (a "presentment currency" order — e.g. a customer viewing the
  store in a different currency than the shop's base currency).
- **Steps.** (1) Trigger order import for the mismatched-currency order.
  (2) Check the outcome.
- **Expected result.** No Odoo sales order is created in the store's
  currency for this order. The order is held for manual review (or
  flagged as an explicitly unsupported case — the exact presentation is
  still being finalized) **before** any sales order is created. The order's
  amounts in both currencies are recorded as evidence either way, so
  nothing about the order is lost even though it isn't auto-imported.
- **Evidence to capture.** Confirmation no sales order was created for
  this Shopify order; the recorded currency amounts (both the shop's
  currency and the order's own currency, i.e. Shopify's `shopMoney` and
  `presentmentMoney` fields); the job log entry showing why the order was
  held.
- **Pass/fail rule.** Pass only if no sales order in the store's currency
  was created, the order was held **before** any sales-order-creation
  attempt, and both currency amounts were captured as evidence.
- **Related module/task.** Order import domain slice; DEC-020 residual
  (exact error-class/sub-reason mapping remains open).

## 8. Prevent duplicate order import

- **Purpose.** Confirm re-processing the same Shopify order (a repeated
  webhook delivery, or an overlapping reconciliation pass) never creates
  a second sale order.
- **Preconditions.** An order already imported successfully per Scenario
  6.
- **Steps.** (1) Re-deliver the same order webhook (or manually re-trigger
  import for the same order). (2) Inspect the outcome.
- **Expected result.** The existing order binding is matched; the sale
  order is updated (if anything changed) or left as-is — **never**
  re-created.
- **Evidence to capture.** Confirmation exactly one `sale.order` record
  exists for this Shopify order after the re-processing; the job/log entry
  for the second run showing a match-and-update path.
- **Pass/fail rule.** Pass only if exactly one sale order exists after two
  processing attempts.
- **Related module/task.** Order import domain slice;
  [`data-integrity-idempotency-test-plan.md`](../05-qa/data-integrity-idempotency-test-plan.md)
  "Order binding."

## 9. Sync inventory manually

- **Purpose.** Confirm an operator-triggered inventory sync correctly
  previews and applies a quantity change, respecting the review-then-apply
  default.
- **Preconditions.** Store connected; inventory domain enabled; at least
  one Odoo warehouse location has already been matched to its Shopify
  location and has completed its required first-time safety check; a
  stock quantity has changed on the Odoo side for an already-imported
  product at that location.
- **Steps.** (1) Trigger a manual inventory sync. (2) Review the preview
  shown to the operator, listing exactly what will change on Shopify.
  (3) Approve the apply.
- **Expected result.** A preview is shown and must be approved before
  anything is written to Shopify (the system never auto-applies inventory
  changes in MVP). After approval, Shopify's stock level updates safely —
  using Shopify's own "compare current value before changing it"
  mechanism (`inventorySetQuantities`) so a concurrent change elsewhere
  can't be silently overwritten. Shopify's "committed" (already-ordered)
  quantity is never touched by this write. The sync finishes
  successfully.
- **Evidence to capture.** The preview shown to the operator; the job log
  entry recording the applied write; the Shopify-side inventory level
  after the write, confirmed to match the intended value.
- **Pass/fail rule.** Pass only if a preview was shown and explicitly
  approved before the write occurred, and the resulting Shopify inventory
  level matches the intended Odoo quantity.
- **Related module/task.** Inventory sync domain slice.

## 10. Recover failed inventory sync

- **Purpose.** Confirm that if two things try to change the same Shopify
  stock level at once, the system recovers safely instead of overwriting
  one change with stale data or losing a write.
- **Preconditions.** Same as Scenario 9, but the Shopify-side quantity is
  deliberately changed by another process after the preview was shown but
  before the approved write reaches Shopify — creating a conflict.
- **Steps.** (1) Trigger the sync and approve the preview. (2) Force a
  competing Shopify-side change before the write executes. (3) Observe
  the outcome. (4) Allow the automatic retry to proceed.
- **Expected result.** The write is rejected because the stock level
  changed underneath it (a "someone else changed this first" conflict).
  The system automatically retries shortly after — but only after
  re-reading Shopify's current value first, never by blindly resending
  the old comparison. The retry succeeds once it has a fresh value to
  compare against.
- **Evidence to capture.** The job log entries for the failed attempt and
  the successful retry; confirmation the retry used a freshly-read
  comparison value, not the original stale one.
- **Pass/fail rule.** Pass only if the final Shopify-side quantity is
  correct and no duplicate or lost write occurred.
- **Related module/task.** Inventory sync domain slice;
  [`data-integrity-idempotency-test-plan.md`](../05-qa/data-integrity-idempotency-test-plan.md)
  "Safe retry."

## 11. Send fulfillment/tracking update

- **Purpose.** Confirm that marking an Odoo delivery as done automatically
  tells Shopify the order was fulfilled, with tracking info — and that
  nothing else can trigger this besides actually completing the delivery.
- **Preconditions.** Store connected; fulfillment domain enabled; the
  Odoo delivery-carrier/tracking feature (`stock_delivery`, or
  `delivery`) installed; an imported order exists with an associated
  delivery that has not yet been marked done and already has its carrier
  and tracking number filled in.
- **Steps.** (1) Mark the delivery as done ("Validate" the delivery order
  in Odoo). (2) Check the resulting Shopify-side fulfillment.
- **Expected result.** Completing the delivery — and only completing the
  delivery — creates a matching fulfillment record on the Shopify order,
  with the tracking number and carrier attached. The system records that
  this happened because of the delivery being completed, not because of
  a webhook, a manual click, or a schedule. Whether the customer gets a
  shipping-notification email follows the store's saved default, decided
  at the moment the update was queued. The update completes successfully.
- **Evidence to capture.** The job log record showing the update was
  triggered by the delivery-completion event (technically, `job_source =
  'odoo_event'` with trigger-origin `fulfillment_picking_validation`);
  the created Shopify fulfillment and its tracking fields; the
  notification-requested/suppressed flag on the log entry.
- **Pass/fail rule.** Pass only if the fulfillment was created solely as a
  result of the picking validation (no other trigger fired it), tracking
  fields are correct, and the notification decision matches the store
  default.
- **Related module/task.** Fulfillment/tracking domain slice; DEC-019
  (`odoo_event` job source).

## 12. Disconnect store and preserve history

- **Purpose.** Confirm disconnecting a store clears the credential but
  preserves every other record, per DEC-018 (MBQ-08).
- **Preconditions.** Store `Connected` with existing jobs, logs, bindings,
  and at least one prior import of each enabled domain.
- **Steps.** (1) As Admin, choose Disconnect. (2) Read the consequence-
  stating confirmation copy. (3) Confirm the disconnect. (4) Inspect the
  store's records afterward.
- **Expected result.** The confirmation copy states plainly that sync
  stops, credentials are removed, and history/bindings/logs are
  preserved. After confirming: `access_token` is cleared,
  `credential_present=False`, store `state` becomes `Disconnected`; every
  job, log, binding, and mapping/error history record remains queryable
  and unmodified in content; no new business job can be enqueued.
- **Evidence to capture.** The store record before/after disconnect; a
  count of jobs/logs/bindings before and after (must be unchanged except
  for new disconnect-audit entries); confirmation no new business job was
  enqueued after disconnect.
- **Pass/fail rule.** Pass only if all history survives unmodified and the
  credential is provably cleared.
- **Related module/task.** Task 005 (connection lifecycle actions).

## 13. Reconnect store and re-run readiness

- **Purpose.** Confirm reconnecting a disconnected (or `Reconnect
  needed`) store always re-runs readiness before resuming business sync,
  per DEC-018 (MBQ-08).
- **Preconditions.** A store in `Disconnected` or `Reconnect needed`
  state, per Scenario 12 or an auth-failure scenario.
- **Steps.** (1) As Admin, choose Reconnect. (2) Re-enter a valid
  credential. (3) Observe the flow through test connection and readiness.
- **Expected result.** Test Connection runs and passes; readiness checks
  re-run and pass; only then does the store reach `Connected` and paused
  enqueue resume. There is no path that reaches `Connected` without a
  readiness re-run.
- **Evidence to capture.** The job/log entries for the test-connection and
  readiness-check runs during reconnect; the store's `state` transitions
  in order (`Disconnected`/`Reconnect needed` → readiness running →
  `Connected`).
- **Pass/fail rule.** Pass only if readiness demonstrably ran and passed
  before the store state changed to `Connected`.
- **Related module/task.** Task 005 (connection lifecycle actions); Task
  004 (readiness).

## 14. Operator reviews error center and retries safely

- **Purpose.** Confirm the error center clearly explains what went wrong
  and only offers a retry button when it's actually safe to retry.
- **Preconditions.** At least one item is sitting in the error center
  waiting for a person to review and decide (a specific reason is
  attached, not a generic "needs review"); at least one other item has
  failed in a way that just needs a fix before it can be retried.
- **Steps.** (1) Open the error center. (2) Inspect the item waiting for a
  decision. (3) Resolve it as a Reviewer. (4) Inspect the item that needs
  a fix before retrying. (5) Perform the suggested fix, then retry.
- **Expected result.** The review item shows its specific reason (never a
  generic "needs review" label), a plain-language explanation, and a
  "Review & resolve" action; resolving it is recorded with who did it,
  when, and what they chose. The fix-needed item shows a named cause and
  a suggested fix; its Retry button only becomes available once that fix
  has actually been applied — the system never offers a retry button for
  a case where retrying blindly could make things worse.
- **Evidence to capture.** The error-center entries before and after
  resolution; the audit trail for the manual-review resolution; the job
  state transition after retry.
- **Pass/fail rule.** Pass only if the correct retry UI case was shown for
  each entry (never an unconditional retry button on a manual-review
  entry) and both entries reached `succeeded` (or an appropriate terminal
  state) after correct operator action.
- **Related module/task.** Dashboard/error-center domain-agnostic UI
  (Task 006 horizon and beyond).

## 15. Admin verifies logs without seeing credentials

- **Purpose.** Confirm an Admin — even though Admin is the role authorized
  to manage credentials — never sees the actual token value anywhere,
  including in logs and audit trails.
- **Preconditions.** A store with a credential set and at least one
  test-connection or readiness failure logged (to ensure failure-path
  redaction is also exercised, not just the happy path).
- **Steps.** (1) As Admin, open the job/log records related to the
  credential and test-connection history. (2) Inspect every field.
  (3) Attempt to open the credential model directly (there should be no
  view to do so). (4) Search the Odoo server log (if accessible in the
  test environment) for the known dummy token value used in setup.
- **Expected result.** Nowhere Admin looks — activity logs, audit trails,
  or the record itself — ever shows the actual credential value. All
  Admin can see is status information (whether a credential is present,
  and when it was last verified) — never the value. There is no screen
  at all for opening the credential record directly. The dummy token does
  not appear in the server log.
- **Evidence to capture.** The full set of job/log entries and store
  mirror values inspected; confirmation of zero matches for the dummy
  token outside the credential field's own storage; confirmation no
  credential-model view exists.
- **Pass/fail rule.** Pass only if the token is absent from every surface
  Admin can see other than the write-only entry action itself, with zero
  exceptions.
- **Related module/task.** Task 002 (credential storage/redaction);
  [`security-redaction-test-plan.md`](../05-qa/security-redaction-test-plan.md).
