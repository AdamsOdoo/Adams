# MVP Domain Pre-Implementation Checklist

> Gate checklist for reviewing any future product/customer/order/inventory/
> fulfillment domain task spec or implementation PR (documentation now;
> code when the relevant domain task is separately authorized). Derived
> from the house style of
> [`pr-review-checklist.md`](./pr-review-checklist.md),
> [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md),
> and [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md),
> and from the proposed task specs in
> [`../07-implementation-plan/mvp-domain-implementation-sequence.md`](../07-implementation-plan/mvp-domain-implementation-sequence.md)
> and its companion Task 010–014 documents. A "No" on any **[Gate]** item
> blocks acceptance of the domain task/PR under review. Complements —
> does not replace — `pr-review-checklist.md` §C (Implementation phase),
> the credential-security-redaction checklist, and the UI/UX design
> review checklist, each of which still applies in full wherever a domain
> task also touches those areas.

## Status

**Planning-level, docs-only.** This document itself creates no task,
authorizes no code, and opens no gate. It applies once a domain
implementation gate (product/sale/inventory/fulfillment) is separately
opened by ChatGPT for the specific task under review. Accepting this
checklist does not itself open any gate or authorize Task 010–014 or any
other domain task.

## A. Foundation dependencies met

- [ ] **[Gate]** Task 002 (credential storage/redaction) is merged and
      ChatGPT-reviewed, if the domain task under review makes any
      Shopify call.
- [ ] **[Gate]** Task 003 (API client/test connection) is merged,
      ChatGPT-reviewed, and its own gate-opening act has occurred, if the
      domain task makes any Shopify call.
- [ ] Task 004 (readiness substrate) status confirmed and, if the domain
      task depends on readiness gating, merged.
- [ ] Task 005 (connection lifecycle) status confirmed and, if the
      domain task depends on store-state gating (`setup_incomplete` /
      `reconnect_needed` / `disconnected`), merged.
- [ ] Task 006 (setup wizard UI) status confirmed if the domain task
      ships any UI dependent on the wizard having run.
- [ ] **[Gate]** The domain task's own separately-named "domain gate"
      (product/sale/inventory/fulfillment, per
      `../07-implementation-plan/ui-ux-implementation-task-map.md`) has
      been explicitly opened by ChatGPT — not assumed from this checklist
      or from any other task's acceptance.

## B. Domain boundaries respected

- [ ] **[Gate]** The task changed only files inside its own accepted
      module (`shopify_connector_product` / `_sale` / `_inventory` /
      `_fulfillment`) plus only the accepted extension seams inside
      `shopify_connector_core` (job-type `selection_add`, error-class
      mapping, settings `_inherit`).
- [ ] **[Gate]** The accepted dependency DAG is respected: `product`
      depends only on `core`; `sale` and `inventory` depend on `core` +
      `product` and are siblings (neither depends on the other);
      `fulfillment` depends on `core` + `sale` only and never on
      `inventory`.
- [ ] No product task touches order/customer/inventory/fulfillment
      logic; no order task touches inventory/fulfillment write logic; no
      inventory task touches fulfillment logic or vice versa.
- [ ] No new domain module was invented beyond the four accepted names
      (`shopify_connector_customer` is explicitly not part of the
      accepted Phase 1 module set — customer logic belongs inside
      `shopify_connector_sale`).
- [ ] **[Gate]** A product-import task must not smuggle in
      product-export/update/write scope: no `productSet` call, no
      `productVariantsBulkUpdate`/`productVariantsBulkCreate` call, no
      other Shopify catalog-write mutation, and no destructive-write
      guard implementation appears in a task scoped as import/binding
      only (added per the ChatGPT REVISE narrowing Task 010, PR #93).
- [ ] **[Gate]** Any Shopify catalog write (product export/update or
      otherwise) requires its own separate, explicitly-named
      product-write gate and its own final `CLAUDE.md` §9 task prompt —
      it is never bundled into an import/binding task's scope or
      acceptance criteria.

## C. API client used, never bypassed

- [ ] **[Gate]** No domain module constructs an HTTP/GraphQL request,
      reads a credential, or parses a raw Shopify error itself — every
      Shopify call goes through `shopify.connector.api.client` in
      `shopify_connector_core`, called only from job handlers registered
      through the accepted job-type seam.
- [ ] **[Gate]** No REST call, no bulk-operation shortcut, and no
      duplicate transport/queue/log/binding abstraction was introduced in
      the domain module (RA-013).

## D. No direct credentials access from domain code

- [ ] **[Gate]** The domain module never reads
      `shopify.connector.store.credential` (or its status mirrors)
      directly; it never logs, exceptions, or persists a token value
      anywhere.
- [ ] **[Gate]** No `sudo()` call in the domain module reads or exposes
      credential data.

## E. Idempotency defined

- [ ] **[Gate]** The task names its idempotency anchor (the relevant
      binding model) and states, concretely, that a repeated
      webhook/scheduled/reconciliation pass updates the existing binding
      rather than re-creating it.
- [ ] Where a Shopify mutation is not documented as idempotent (e.g.
      fulfillment mutations), the task defines an operation-level
      idempotency key and a verification-read-before-retry rule together
      — neither alone is treated as sufficient.

## F. Duplicate prevention defined

- [ ] **[Gate]** The task defines both the interactive/batch
      blocking-preview path and the automated pre-create two-tier gate
      (eligibility conditions, then match-quality conditions) —
      retrospective dashboard/sync-center visibility is not accepted as a
      substitute for either.
- [ ] No feature flag/setting/config exists anywhere in the diff that
      could skip either duplicate-prevention path (Part A §I.5 no-bypass
      rule).

## G. Logs/audit defined

- [ ] Every state transition the task introduces writes a corresponding
      `shopify.connector.job.log` row (append-only, `ondelete='restrict'`).
- [ ] Binding records carry the accepted audit fields (matched-by,
      matched-at, source strategy, match key, override history) — no
      parallel logging/audit mechanism was invented.

## H. Retry/recovery defined

- [ ] **[Gate]** Retry is class-conditional, not blanket:
      transient/network errors and `@idempotent`-eligible operations
      auto-retry; ambiguous-outcome failures require a safe verification
      read before any retry, never a blind retry; conservative classes
      (e.g. `financial total mismatch`) are never auto-retried.
- [ ] No "force" retry bypass exists anywhere in the diff.

## I. Manual review cases defined

- [ ] The task enumerates its specific manual-review-triggering
      scenarios and maps each to one of the six accepted manual-review
      sub-reasons (ambiguous match; binding conflict; duplicate risk;
      destructive-write guard blocked; inventory location missing;
      fulfillment notification confirmation missing) — no new, seventh
      sub-reason or generic catch-all was invented.
- [ ] The task correctly distinguishes `blocked_manual_review`
      (confirmation required) from `failed_retryable` (e.g. `mapping
      missing` — manual fix then retry) rather than collapsing every
      failure into one bucket.

## J. UI dependencies separated from backend logic

- [ ] The task states explicitly which of its screens (if any) require
      the UI implementation gate, and does not assume that gate is open.
- [ ] Backend/domain logic in the task does not silently assume any UI
      screen exists or has run (e.g. does not assume a wizard step, a
      mapping screen, or a settings screen has already collected input
      that has not, in fact, been separately authorized and built).

## K. Premium UX standards respected (where UI is in scope)

- [ ] Where the task includes any UI, it satisfies the twelve accepted
      UX principles and the "Premium Simplicity Standard" (clarity,
      confidence, polish, guidance, recovery — not more screens/colors/
      charts/complexity).
- [ ] Universal must-not-dos respected: no fork of a per-domain
      dashboard/queue (RA-013); no internal token or raw stack trace
      rendered as a primary label (RA-016); no guard bypass; no
      encryption claim; no MVP-scope widening.

## L. MVP vs later separation explicit

- [ ] **[Gate]** The task spec states plainly which of its elements are
      MVP (per `mvp-domain-implementation-sequence.md`, "MVP vs later")
      and confirms it introduces nothing from the Later list (payouts,
      advanced refunds, Shopify Markets, multi-store/multi-company
      complexity, metafields, subscriptions, gift cards, POS, B2B,
      advanced analytics, App Store packaging).
- [ ] Deferred-but-related items already decided elsewhere (order
      edits/cancellations/refunds/returns; per-order notification
      override; FulfillmentOrder advanced lifecycle events;
      presentment-currency Odoo orders) are not silently reintroduced.

## M. Tests defined

- [ ] **[Gate]** Unit/integration tests are written (and executed where
      a runtime exists) covering the task's own edge cases and any
      relevant prior defect pattern from `defect-pattern-log.md`.
- [ ] Access-control matrix (four existing groups) is covered for every
      new model the task introduces.
- [ ] Where no runtime exists at coding time, tests are still written
      and syntax-validated, and the manual-validation checklist becomes
      mandatory review evidence (per the Task 001A precedent) —
      inventing a non-Odoo test harness is not acceptable.

## N. Rollback defined

- [ ] The task states a single-PR revert path and what happens to
      already-created Odoo/Shopify data on revert (e.g. bindings
      dropped, business records remain as ordinary unbound data, no
      automatic corrective Shopify write is triggered).

## O. No unrelated module touched

- [ ] **[Gate]** `docs/04-decisions/*` (DEC-003 through DEC-020),
      `docs/04-decisions/README.md`, `docs/05-qa/defect-pattern-log.md`,
      `docs/05-qa/architecture-review-log.md`, and
      `docs/03-architecture/master-blueprint-open-questions.md` are
      unchanged unless the task explicitly carries its own authorized
      acceptance patch.
- [ ] `addons/adams_base` and any file outside the task's own
      allowed-files list (fixed by its own final §9 prompt) are
      untouched.

## P. No overreach into later scope

- [ ] **[Gate]** No payouts, advanced refunds, Shopify Markets,
      multi-store/multi-company complexity, metafields, subscriptions,
      gift cards, POS, B2B, advanced analytics, or App Store packaging
      logic appears anywhere in the diff.

---

**Result recording.** Review outcomes for any domain task evaluated
against this checklist are recorded in
[`architecture-review-log.md`](./architecture-review-log.md), per the
pattern established by the credential and UI/UX checklists.
Implementation-era reviews must additionally satisfy
[`pr-review-checklist.md`](./pr-review-checklist.md) §C in full.
