# Limited Core Implementation Gate — Opened

> **Documentation-only gate-opening act.** This document performs the two
> separate, explicit ChatGPT acts the accepted
> [Final MBQ Closure Plan](./final-mbq-closure-plan.md) (§8, §11) and the
> accepted [Implementation Gate Readiness Audit](../05-qa/implementation-gate-readiness-audit.md)
> (criterion 3, criterion 5) named as still outstanding: (1) confirming
> [AR-018](../05-qa/architecture-review-log.md)'s criterion-5 ambiguity, and
> (2) opening a **limited, core-only, zero-UI** implementation gate. It
> creates **no code, no module, no Python, no XML, no manifest, no security
> CSV, no test, and no CI file.** It authorizes exactly one implementation
> task — [Task 001](./task-001-core-module-scaffold.md) — and nothing
> beyond it. **Accepted by ChatGPT on 2026-07-05** (see [AR-021](../05-qa/architecture-review-log.md));
> **the gate is opened only once this PR is merged into `Shopify-connector`
> — this acceptance does not itself create code or start implementation.**

## Acceptance

- **Accepted by ChatGPT on 2026-07-05.**
- Opens the limited core-only zero-UI gate **after this PR is merged.**
- Confirms [AR-018](../05-qa/architecture-review-log.md) criterion 5
  **only for the limited core gate** — see §2.
- Authorizes exactly **one** implementation task: Task 001 (§6).
- **Does not create code.**
- **Does not start implementation in this PR.**
- **Does not authorize credentials, external API calls, operator-facing
  UI, or product/customer/order/inventory/fulfillment domain logic.**
- **Does not apply project-wide to future gates** — every later gate
  (product/customer/sale, inventory, fulfillment, UI, credentials/API)
  requires its own separate, explicit ChatGPT gate-opening act.
- Future tasks still require their own evidence, allowed files, forbidden
  files, tests, rollback notes, and ChatGPT review — this acceptance
  authorizes Task 001 only, not a standing implementation mandate.

## Status

- **Accepted by ChatGPT on 2026-07-05.** Gate opened only after this PR
  is merged into `Shopify-connector`.
- Gate scope is limited to `shopify_connector_core`.
- Zero operator-facing UI.
- No webhooks.
- No external API calls.
- No credential persistence.
- No setup wizard.
- No test connection.
- No product/customer/order/inventory/fulfillment domain logic.
- No dashboard.
- No sync center.
- No error-center UI.
- No implementation beyond Task 001.

## 1. Basis for opening

- PR #86 merged into `Shopify-connector` (merge commit
  `c9698a70374e5f735f51c1de623c079dc5fd8697`).
- Final MBQ Closure Plan accepted
  ([`AR-020`](../05-qa/architecture-review-log.md),
  [`final-mbq-closure-plan.md`](./final-mbq-closure-plan.md)).
- AR-020 accepted.
- MBQ register updated
  ([`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md),
  applied by the AR-020 acceptance patch).
- Zero MBQ rows remain blocking the limited core-only zero-UI gate.
- AR-019 accepted core naming/schema planning
  ([`core-naming-schema-planning.md`](./core-naming-schema-planning.md)).
- MBQ-04 remains descoped: no credential model, metadata model, or
  token/secret field.

## 2. AR-018 criterion 5 confirmation

[AR-018](../05-qa/architecture-review-log.md)'s
[Implementation Gate Readiness Audit](../05-qa/implementation-gate-readiness-audit.md)
(§3, criterion 5) found criterion 5 ("no quality-gate escalation open
without a prevention rule") **ambiguous**: `defect-pattern-log.md`'s
occurrence-counter row for category "unsupported assumption (#3) / weak
research (#1)" (occurrences **DP-003, DP-004, DP-006**) still literally
reads `ESCALATED`, even though its own text records that an
**evidence-consistency gate** was put in place at the time of escalation
(2026-07-01) and that no new occurrence in that category has been logged
since (each individual DP-003/DP-004/DP-006 log row is itself already
marked `Mitigated`). The audit declined to resolve this ambiguity itself —
out of its allowed-files scope and its own authority — and recommended
ChatGPT confirm the reading directly.

**Decision (accepted by ChatGPT on 2026-07-05):**

ChatGPT confirms that DP-003/004/006 satisfy the prevention-rule
requirement for this limited core gate because their recorded
evidence-consistency gates prevent implementation from proceeding when
evidence conflicts remain unresolved.

**Scope of this confirmation:**

- Applies only to the limited core-only zero-UI gate.
- Does not waive evidence requirements for credential, API, UI, product,
  order, inventory, fulfillment, or release-readiness tasks.
- Does not weaken any rejected approach.
- Does not convert future evidence risks into implementation permission.

Criterion 5 is therefore confirmed **satisfied for this limited gate only**.
This confirmation does not relabel `defect-pattern-log.md`'s occurrence-
counter row (out of this document's allowed-files scope) and does not
apply project-wide.

## 3. Gate scope opened

Within `shopify_connector_core` only, the following is opened:

- create `shopify_connector_core` module scaffold only;
- create manifest/init files needed for installable scaffold;
- create six accepted core models only:
  - `shopify.connector.store`
  - `shopify.connector.store.settings`
  - `shopify.connector.location`
  - `shopify.connector.binding.mixin`
  - `shopify.connector.job`
  - `shopify.connector.job.log`
- create groups/access CSV needed for those core models only;
- create basic constraints/indexes accepted by AR-019;
- create tests for the scaffold/core models/security/constraints only.

## 4. Explicitly forbidden in this gate

- credential model;
- credential metadata model;
- token/secret fields;
- setup wizard;
- test connection;
- Shopify API client;
- webhooks;
- controllers;
- cron execution loop unless explicitly part of Task 001 acceptance
  criteria;
- product/customer/order/inventory/fulfillment domain modules;
- dashboard;
- sync center;
- error center UI;
- accounting/refund/payout/multi-store/Markets logic;
- any destructive migration;
- any production data migration;
- any broad refactor.

## 5. Required implementation governance

- Every implementation PR must be small.
- Every implementation PR must name allowed files and forbidden files.
- Every implementation PR must include tests or explicitly justify why no
  test applies.
- Every implementation PR must update research-handoff.
- Every implementation PR must include rollback notes.
- Every implementation PR must stop after the task objective.
- No second task may start until ChatGPT reviews the first implementation
  PR.

## 6. First task authorized

Exactly one implementation task is authorized by this gate, **starting
only after this PR is merged into `Shopify-connector`**:

[`docs/07-implementation-plan/task-001-core-module-scaffold.md`](./task-001-core-module-scaffold.md)

No other task, and no code, is authorized by this document.
