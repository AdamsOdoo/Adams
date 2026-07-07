# MVP Release Readiness Checklist

> Docs-only go/no-go release-readiness checklist for the connector MVP,
> part of the [MVP QA and Test Strategy](../05-qa/mvp-qa-test-strategy.md)
> package. **Historical drafting baseline:** `Shopify-connector` at
> `f74aaf204745ce0087733870fe56bdda74bfa79a`. **This checklist plans what
> a future release-readiness review must confirm — it does not itself
> confirm any item.** At original drafting, no implementation existed
> beyond Task 001's core scaffold. **Freshness note (2026-07-07
> revision):** `Shopify-connector` has since also merged PR #93 (MVP
> domain implementation slicing — proposes Tasks 010–014, gates none of
> them, `ac250f7fd2f242df7b69f78dc619b0a71680c664`), PR #94 (Task 002
> decision closure — AR-025, `03ffcb4dc949cd5137b589a6cdc33da9105de31d`),
> and PR #96 (Task 002 credential-storage gate — AR-026,
> `02b159a39c58a3396c1c249e80896a05c97bb757`). **The Task 002
> credential-storage implementation gate is now open**; Task 002
> implementation may proceed only through
> [`../07-implementation-plan/task-002-final-implementation-prompt.md`](../07-implementation-plan/task-002-final-implementation-prompt.md)
> in its own coding session. Task 003 remains not started/not
> authorized. No item on this checklist is satisfied by that gate
> opening alone — every checkbox still represents a future confirmation
> a release-readiness reviewer must perform once the relevant
> implementation PR actually merges and is tested. Complements
> [`../05-qa/pr-review-checklist.md`](../05-qa/pr-review-checklist.md)
> §C and [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
> per this directory's own [`README.md`](./README.md).

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened by this document. No item below is claimed satisfied by this
document** — every checkbox represents a future confirmation a
release-readiness reviewer must perform once the relevant implementation
task has merged. As of the 2026-07-07 freshness revision, the Task 002
credential-storage gate is open (AR-026/PR #96), but Task 002's own
implementation PR has not yet merged, so none of this checklist's Task
002-relevant items (e.g. "security/redaction checks pass," "access
rights verified") may yet be marked satisfied.

## How to use this checklist

Each item names a gate check. At release-readiness review time, mark each
`[ ]` as satisfied only with concrete evidence (a PR link, a test result,
a manual-validation record) — never mark an item satisfied because "it
should work" or "it's designed to." This extends this sprint's own "do
not claim tests exist if they are only planned" rule to release claims
generally.

## Must-pass before MVP release

- [ ] **Architecture decisions accepted.** DEC-003 through DEC-020 (or
      whatever the final decision set is at release time) are all in
      `Accepted` status in
      [`../04-decisions/README.md`](../04-decisions/README.md); no
      decision remains in `Proposed`/`Under review` that a shipped domain
      depends on.
- [ ] **Open MBQs classified.** Every MBQ row in
      [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
      that blocks a shipped domain is either Resolved or has its residual
      explicitly reclassified as task-spec detail that the shipping task's
      own PR closed — no MBQ silently ignored.
- [ ] **All implementation PRs reviewed.** Every PR contributing to the
      MVP release has a recorded ChatGPT review decision (per
      [`../05-qa/pr-review-checklist.md`](../05-qa/pr-review-checklist.md))
      — no PR merged without review.
- [ ] **Runtime install/upgrade passes.** `shopify_connector_core` and
      every domain module install and upgrade cleanly on a real Odoo 19 +
      PostgreSQL instance — closing the gap
      [`../05-qa/task-001-core-runtime-readiness.md`](../05-qa/task-001-core-runtime-readiness.md)
      ("Task 001A") could not close without a runtime.
- [ ] **Security/redaction checks pass.** Every item in
      [`../05-qa/security-redaction-test-plan.md`](../05-qa/security-redaction-test-plan.md)
      passes with recorded evidence (test results and/or the manual grep
      strategy executed against a live instance).
- [ ] **Access rights verified.** The four-role access matrix
      (auditor/operator/reviewer/admin) matches the accepted AR-019 design
      exactly, on every model that exists at release time, verified by
      test and/or manual evidence — see
      [`../05-qa/foundation-test-matrix.md`](../05-qa/foundation-test-matrix.md)
      "Credential access matrix."
- [ ] **No token leakage.** A grep of logs, `job.log` rows, store mirrors,
      and any exported/backed-up data for a real deployment's actual token
      (or, in staging, a dummy token) returns zero hits outside the
      credential field itself.
- [ ] **No real credentials in repo.** A repository-wide search for any
      Shopify token pattern (`shpat_`, `shprt_`) or other credential-
      shaped string in code, docs, tests, fixtures, and commit history
      returns zero real values (dummy test values only).
- [ ] **Shopify API version pinned.** The connector's `api_version` default
      is a specific, stable, currently-supported Shopify API version (not
      `unstable`/`latest`-floating), matching the accepted MBQ-52 pinning
      policy.
- [ ] **Same-currency order guard tested.** A divergent-currency order
      (`presentmentCurrencyCode != currencyCode`) is confirmed, by test or
      manual evidence, to be blocked before sale-order creation, per
      [`../05-qa/domain-e2e-test-matrix.md`](../05-qa/domain-e2e-test-matrix.md)
      §4 "Same-currency-only order import."
- [ ] **Total-check guard tested.** The order-import total-check guard is
      confirmed unbypassable by any flag/setting, and a forced mismatch is
      confirmed to route to `financial total mismatch`, never silently.
- [ ] **Retry/idempotency tested.** Every item in
      [`../05-qa/data-integrity-idempotency-test-plan.md`](../05-qa/data-integrity-idempotency-test-plan.md)
      passes with recorded evidence, including the target-less job
      repeat-run resolution once Task 003 lands.
- [ ] **Duplicate prevention tested.** Every binding-uniqueness and
      pre-create-gate item in
      [`../05-qa/data-integrity-idempotency-test-plan.md`](../05-qa/data-integrity-idempotency-test-plan.md)
      passes with recorded evidence for every domain shipped in the
      release.
- [ ] **Manual review flows tested.** Every one of the six manual-review
      sub-reasons (ambiguous match, binding conflict, duplicate risk,
      destructive-write guard blocked, inventory location missing,
      fulfillment notification confirmation missing) has at least one
      exercised test/manual-validation case per shipped domain, with the
      Reviewer resolution path confirmed to work end-to-end.
- [ ] **Disconnect/reconnect tested.** Disconnect is confirmed to preserve
      all history while clearing the credential; reconnect is confirmed to
      re-run readiness before returning to `connected`; per
      [`../05-qa/foundation-test-matrix.md`](../05-qa/foundation-test-matrix.md)
      Task 005 rows.
- [ ] **Setup wizard tested.** Every one of the 11 accepted wizard steps
      supports exit-and-resume; no business sync/write job runs before
      Activate; per
      [`../02-product/mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md)
      Flow 1. (Requires the UI implementation gate to have opened and
      Task 006 to have shipped — see [Non-MVP deferred items](#non-mvp-deferred-items)
      if it has not.)
- [ ] **Dashboard/error center tested.** The dashboard renders exactly the
      nine accepted cards with honest freshness and no vanity metrics; the
      error center's retry affordance is always exactly one of the four
      accepted retry UI cases; per
      [`../05-qa/domain-e2e-test-matrix.md`](../05-qa/domain-e2e-test-matrix.md)
      §9.
- [ ] **End-to-end UAT passed.** Every scenario in
      [`mvp-uat-scenarios.md`](./mvp-uat-scenarios.md) has a recorded
      pass result with evidence, executed by a reviewer following the
      scenario's own steps (not summarized from memory).
- [ ] **Rollback documented.** Every implementation task contributing to
      the release has its own rollback notes (already a required section
      of every task spec per `CLAUDE.md` §9), and a release-level rollback
      plan (revert order across the module dependency DAG:
      fulfillment → inventory/sale → product → core) exists and is
      reviewed.
- [ ] **Customer documentation drafted.** Merchant-facing setup and
      troubleshooting documentation exists (even in draft form) covering
      at minimum: connecting a store, the credential-security posture in
      honest plain language, disconnect/reconnect, and how to read the
      error center.
- [ ] **Known limitations documented.** The [Acceptable known
      limitations](#acceptable-known-limitations) and [Non-MVP deferred
      items](#non-mvp-deferred-items) sections below are reviewed, kept
      current, and communicated to the merchant-facing documentation
      above — no known limitation is silently omitted from release notes.

## Acceptable known limitations

These are **accepted, honestly-disclosed** limitations at MVP release —
not defects to fix before shipping, but facts that must be stated plainly
in customer-facing documentation and internal release notes:

- **Residual credential exposure.** Field-level `groups=` and model ACLs
  are access control, not encryption; `sudo()`/superuser bypasses them; an
  Admin-group user with generic ORM/RPC access, or anyone with database/
  backup access, can read the stored token outside connector surfaces.
  This is the accepted MBQ-04 Option B posture (AR-022) and must never be
  described as encryption anywhere.
- **No live scope-sufficiency guarantee beyond snapshot freshness.** The
  `granted_scopes` snapshot is captured at each test-connection/readiness
  run, not continuously — the UI must never imply a live scope view
  (`granted_scopes_checked_at` exists specifically to keep this honest).
- **Officially-unconfirmed Shopify behaviors handled defensively, not
  authoritatively.** THROTTLED response body shape, invalid-token HTTP
  status, missing-scope error shape, and whether `shop`/
  `currentAppInstallation` require any scope are all open questions this
  project has chosen to handle via labelled-unofficial fixtures plus
  empirical verification steps, rather than blocking release on Shopify
  publishing official confirmation.
- **Order-currency divergent-order handling mechanism is Task-spec
  detail, not a fixed UX at this planning stage.** The *fact* that a
  divergent-currency order is blocked before SO creation is decided
  (DEC-020); the *exact* manual-review-queue-vs-unsupported-scope
  presentation is fixed by the order-import task's own spec, which may
  land after this checklist is written.
- **First-push guard granularity is per mapped location pair, not
  per-SKU.** An operator confirms an entire mapped pair's preview at
  once, not each SKU individually — accepted as sufficient granularity by
  DEC-018 (MBQ-33), not a defect.

## Non-MVP deferred items

These are **explicitly out of scope** for the MVP release, not limitations
of the current implementation — shipping without them is not a regression:

- Presentment-currency-denominated Odoo orders (Option B of MBQ-64) —
  deferred pending a future, separately authorized scope expansion.
- Order edits, cancellations, refunds, and returns — deferred unchanged
  from DEC-003 for the entire order/fulfillment lifecycle.
- Payout reconciliation, automatic invoice creation, and automatic payment
  posting — never authorized by the accepted gateway → journal
  classification mapping (MBQ-30); no accounting automation exists.
- Webhook-driven inventory import — not implemented in Phase 1 (MBQ-63);
  the Shopify → Odoo inventory direction is limited to the one-time,
  controlled baseline import.
- `FULFILLMENT_ORDERS_*` lifecycle events beyond ordinary creation/
  tracking (holds, cancellation-requests, merges, splits, reschedules) —
  not subscribed to in Phase 1 (MBQ-61).
- Multi-location/multi-package fulfillment automation — deferred, routes
  to manual review instead (DEC-003).
- Multi-store / multi-company permission isolation — descoped from MVP
  (single-store/single-company posture, DEC-003, MBQ-46).
- Markets, metafields, subscriptions, POS, and B2B — confirmed absent from
  the accepted product/customer/sale and inventory/fulfillment decision
  text; no MVP scope exists for any of these five areas.
- Auto-apply ongoing inventory writes — review-then-apply is the accepted
  Phase 1 default (MBQ-34); auto-apply is deferred behind a future,
  explicit decision/feature flag.
- A scheduled/periodic credential health probe — not designed in the
  current credential/connection foundation package; test connection
  remains interactive/on-demand only in this planning horizon.
