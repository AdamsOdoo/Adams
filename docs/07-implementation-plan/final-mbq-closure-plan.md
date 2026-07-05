# Final MBQ Closure Plan — Proposed

> Final planning-closure package for the premium **Odoo 19 ↔ Shopify
> Connector**. Prepared after PR #85 (core naming/schema planning, AR-019)
> merged into `Shopify-connector` at merge commit
> `2e6842b` on **2026-07-05**. Companion documents:
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (the MBQ register this plan closes or scopes — **not edited by this PR**),
> [`../05-qa/implementation-gate-readiness-audit.md`](../05-qa/implementation-gate-readiness-audit.md)
> (AR-018, accepted), [`core-naming-schema-planning.md`](./core-naming-schema-planning.md)
> (AR-019, accepted),
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
> (Part E). Companion review-log entry: **AR-020**
> ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)),
> **Proposed for ChatGPT review**.

## Status

- **Proposed for ChatGPT review.** Nothing in this document is decided
  until ChatGPT accepts it.
- **Documentation-only.**
- **Planning-closure only.**
- **Does not create code.** No Python, XML, manifest, security CSV, test,
  CI, or Odoo module file is created or modified.
- **Does not create implementation tasks.** No file matching `CLAUDE.md`
  §9 / `../06-prompts/implementation-task-template.md` is written.
- **Does not open the implementation gate.** Opening the gate remains a
  separate, explicit ChatGPT act (`master-blueprint.md`, "Criteria for
  when implementation may later be opened", criterion 3).
- **Does not edit the MBQ register.**
  `master-blueprint-open-questions.md` is untouched by this PR; §7 below
  provides the proposed replacement wording only, to be applied by a
  future acceptance patch if and when ChatGPT accepts.
- **Implementation remains blocked** until ChatGPT accepts this closure
  package **and then separately opens the implementation gate.** Accepting
  this package is necessary but not sufficient — it is not the gate act.
- Every proposed decision below is a **[Recommendation]** per `CLAUDE.md`
  §8 until accepted; verified platform facts are labelled **[Fact]** with
  source and access date; deductions are labelled **[Inference]**.
- **Research conducted this session (high-power mode, authorized by the
  session prompt):** five parallel evidence agents — two repo-extraction
  passes (Master Blueprint Parts B/C; DEC-003/004/005/008, decisions
  README, rejected-approaches log, quality-feedback-loop §10/§11) and
  three official-doc verification passes (Shopify compliance/protected
  customer data for MBQ-09; Shopify `productSet` media + `@idempotent`
  scope for MBQ-24/MBQ-14; Odoo 19 tax mechanism for MBQ-27). All
  external claims below carry exact URLs, access dates (2026-07-05), and
  access status. Stop condition: one verification pass; anything the
  official docs do not state is logged as unconfirmed and closed by a
  conservative default, never asserted. **Follow-up item:** full-page
  source captures belong under `/docs/00-source-materials` per
  `CLAUDE.md` §7.4; that directory is outside this session's
  allowed-files list, so the high-value excerpts are embedded verbatim
  below and the full-page capture is logged as a documentation-maintenance
  follow-up (§10, risk 10).

## 1. Purpose

This document closes — or safely and explicitly scopes — **every MBQ row
that is not already fully resolved** in
`master-blueprint-open-questions.md`, so the project can move from
planning into implementation. After PR #85, the register's remaining open
material falls into exactly four shapes: (1) rows closable now with
official-doc evidence or an accepted conservative default; (2) residuals
that are, by their own wording, task-spec detail belonging inside a future
gated implementation task (`CLAUDE.md` §9 requires every task to fix its
own allowed files, acceptance criteria, and tests — that template is where
these residuals land); (3) rows that block only a specific later domain
slice, never the first core-only slice; (4) rows that are genuinely
non-MVP. This plan assigns every remaining row to one of those shapes with
an explicit final status, so the register stops being a diffuse planning
blocker and becomes an implementation-ready control document. **The target
is zero rows still blocking a limited, core-only, zero-UI first
implementation gate — and that target is met (§6).**

## 2. Current accepted baseline

- **DEC-003 through DEC-020 — all Accepted by ChatGPT.** Verified this
  session against each file's own Status line; no DEC file carries any
  status other than Accepted (the decisions README narrative lags at
  DEC-017 — a known documentation-currency item, not a status conflict).
- **AR-002 through AR-019 — all Accepted**
  ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
- **PR #85 merged into `Shopify-connector`** (merge commit `2e6842b`,
  2026-07-05); **core naming/schema planning accepted** at
  implementation-planning level (AR-019): six core models, field schemas,
  feature-flag/settings shape, job+log split, `idempotency_key` +
  `operation_scope_key`, retry/backoff planning defaults, four group XML
  IDs, planned core access-CSV row shapes, `odoo_event`/`trigger_origin`
  mechanics.
- **Core model/schema planning accepted** — MBQ-01/02/07/16/19/20/21
  resolved; MBQ-45 and MBQ-62 residuals resolved; MBQ-44 partially
  resolved (planned CSV row shapes only).
- **MBQ-04 explicitly NOT resolved** — fully descoped from the first
  core-only slice (Option A, AR-019): no credential model, credential
  metadata model, or secret/token field of any kind.
- **Implementation gate still closed.** AR-018 (accepted) found criteria
  2/3/4 unmet and criterion 5 ambiguous as of 2026-07-05 pre-PR-#85;
  criterion 2's eleven core blockers were then resolved by AR-019. No
  gate-opening act has occurred.

## 3. Remaining MBQ inventory before this closure

All 50 rows below are the complete set not fully closed before this
session (rows fully resolved with no residual — MBQ-01/02/07/11/16/19/20/
21/26/31/37/39/45/47/62 — are excluded and **not reopened**; MBQ-37's and
MBQ-39's residuals live in MBQ-63 and MBQ-60 respectively, which are
included). Key: **Core?** = blocks first core-only zero-UI slice;
**Domain?** = blocks an MVP domain slice (which one); **Release?** =
blocks release readiness. Closure routes: **RES** resolve now; **TASK**
residual becomes named task-spec detail inside the gated slice (contained
by `CLAUDE.md` §9); **SLICE** blocks a named later slice only; **REL**
release-readiness residual with a concrete later gate; **DESCOPE**
explicitly out of MVP / first gate; **DEFAULT** conservative default
proposed for ChatGPT acceptance; **AO** accepted-open risk with
containment.

| MBQ | Status before this closure | Area | Core? | Domain? | Release? | Route | Evidence/source used | Proposed final status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 03 | Open | View/menu/action XML IDs | No (zero-UI slice) | Yes — every UI-bearing task | No | TASK/SLICE | AR-018 §4 (zero-UI first slice); AR-019 naming conventions | Descoped from first gate; exact IDs fixed per UI-bearing task spec |
| 04 | Not resolved; descoped slice 1 | Credential storage | No (descoped) | Yes — credential/setup slice | No | SLICE | AR-019 §11 (accepted descope); DEC-004 | Unchanged: descoped from first gate; blocks credential slice pending Odoo evidence + ChatGPT decision |
| 05 | Open | Custom-app surface / token mechanics | No | Yes — setup wizard | No | SLICE | DEC-004 "remains blocked"; shopify.dev distribution docs (partial, 2026-07-05) | Descoped from first gate; blocks setup-wizard slice; official-doc verification at step 6 (§9) |
| 06 | Resolved (posture); residual copy/thresholds | Readiness checks | No | Yes — wizard task detail | No | TASK | DEC-018 | Partially resolved; residual = wizard task-spec detail |
| 08 | Resolved (posture); residual mechanics | Disconnect retention | No | Yes — store-lifecycle task detail | No | TASK | DEC-018 | Partially resolved; residual = store-lifecycle task-spec detail |
| 09 | Open (conservative posture) | Compliance webhooks / protected data | No | Only compliance-relevant code | No | RES(part)+DEFAULT | Official shopify.dev pages fetched 2026-07-05 (§4.9) | Partially resolved at fact level; compliance-webhook feature stays non-MVP; conservative posture stands |
| 10 | Open | Turnkey install prerequisites | No | No | Docs only | REL | Register row (Blocks: No) | Descoped from gate; install-docs item at release readiness |
| 12 | Open (may never resolve) | GID permanence | No | No | No | AO | Register row; DEC-006 defensive design | Accepted-open risk; containment = existing stale/review, no-silent-recreate design |
| 13 | Open | Stale-binding review flow detail | No | Error-center task detail | No | TASK | Register row (behaviour fixed) | Descoped from gate; detail per error-center/matching task spec |
| 14 | Open | `@idempotent` uniqueness scope | No | Yes — inventory write task | No | RES(part)+DEFAULT | Official shopify.dev idempotency pages, 2026-07-05 (§4.14) | Partially resolved (facts verified); scope residual contained by UUID-per-operation default |
| 15 | Open (conditional) | Bulk Operation idempotency | No | Only if bulk adopted | No | DESCOPE | DEC-003 (bulk not user-facing MVP); §4.14 bulk-key fact | Descoped: internal bulk not used in MVP slices; verification precondition if ever proposed |
| 17 | Resolved (posture); residual constants | Reconciliation cadence | No | Per-domain task detail | No | TASK | DEC-018 | Partially resolved; residual = per-domain reconciliation task-spec constants |
| 18 | Open (constants before code; validation → release) | Cron cadence/throughput | Only if slice 1 codes the cron loop | Yes — queue-drain code | Yes (validation) | TASK+REL | AR-018 §6; MBQ-16 precedent (AR-019 §9) | Partially resolved by scope split: constants in the task spec that first codes the cron loop; validation = MBQ-49 release gate |
| 22 | Open | User-facing copy | No | No | Yes (copy pass) | DESCOPE+REL | Register row (Blocks: No); DEC-012 | Descoped from gate; controlled placeholder-copy rule; copy pass blocks release, not implementation |
| 23 | Partially resolved (direction) | Variant-write mutation choice | No | Yes — product export | No | TASK | DEC-014 | Partially resolved; residual = product-export task-spec detail |
| 24 | Open | `productSet` media delete-on-omit | No | Yes — media export only | No | DEFAULT | Official productSet/ProductSetInput/sync-data pages, 2026-07-05 (§4.24) | Partially resolved (facts verified; media behaviour still unconfirmed); MVP disables automated media replace/remove |
| 25 | Partially resolved (mechanism) | Draft/publish channel UX | No | Yes — product export | No | TASK | DEC-014 | Partially resolved; residual = product-export task-spec detail |
| 27 | Open (inconclusive) | Shopify-computed tax in Odoo | No | Yes — order import | No | SLICE+DEFAULT | Official Odoo 19 docs + 19.0 source, 2026-07-05 (§4.27) | Not resolved; descoped from first gate; blocks order-import task only; contained by mandatory total-check guard + manual review |
| 28 | Open (guard, not triggered) | Domain 9 draft-artifact guard | No | Only if triggered | No | AO | Register row; DEC-003 | Accepted-open; containment = the guard itself (returns to ChatGPT if triggered) |
| 29 | Partially resolved (direction) | Default-customer fallback granularity | No | Yes — customer/order import | No | DEFAULT | Part B §B.7 (DEC-014-accepted direction) | Proposed Resolved: single flagged fallback partner per store; per-order anonymous identity non-MVP |
| 30 | Partially resolved (concept) | Gateway→journal mapping schema | No | No | No | TASK | DEC-014 | Partially resolved; residual = sale-slice task-spec schema |
| 32 | Partially resolved (facts) | Free-to-Use source selection | No | Yes — inventory write-back | No | DEFAULT+TASK | DEC-015/Part C §A.4 (verified, non-equivalent sources) | Partially resolved + proposed default: `free_qty` semantics as the single Phase 1 source; mechanics per task |
| 33 | Resolved (granularity); residual schema/UI | First-push guard | No | Yes — inventory task detail | No | TASK | DEC-018 | Partially resolved; residual = inventory task-spec detail (with MBQ-38) |
| 34 | Resolved (default); residual UX | Ongoing apply-mode | No | Yes — inventory task detail | No | TASK | DEC-018 | Partially resolved; residual = inventory task-spec detail |
| 35 | Open (conditional) | `on_hand` UI exposure | No | No | No | DEFAULT | DEC-010/012; RA-018 context | Proposed Resolved: no `on_hand` UI choice in Phase 1; `available` only |
| 36 | Partially resolved (direction) | Mutation per trigger type | No | Yes — inventory task detail | No | TASK | DEC-015; §4.14 idempotency facts | Partially resolved; residual = inventory task-spec detail |
| 38 | Partially resolved (concept) | First-push confirmation schema | No | Yes — inventory task detail | No | TASK | DEC-015 | Partially resolved; residual = inventory task-spec schema |
| 40 | Partially resolved | Backorder wizard-UX nuance | No | Yes — fulfillment task detail | No | TASK | DEC-015 | Partially resolved; residual = fulfillment task-spec detail (verify wizard copy in-task) |
| 41 | Resolved (default); residual check | Notification granularity | No | Implementation-time check | No | TASK | DEC-018 | Partially resolved; residual = one implementation-time check in the fulfillment task |
| 42 | Partially resolved (mechanism) | Location-confirmation detail | No | Yes — fulfillment task detail | No | TASK | DEC-015 | Partially resolved; residual = sub-reason tagging in fulfillment task spec |
| 43 | Partially resolved (precedence) | Location cache refresh cadence | No | Yes — fulfillment/inventory task detail | No | TASK | DEC-015 | Partially resolved; residual = refresh cadence/mechanism in task spec |
| 44 | Partially resolved (row shapes) | Access CSVs / record rules | The residual IS the gated slice-1 artifact | No | No | TASK | AR-019 §10 | Partially resolved (unchanged); residual = the gated CSV/record-rule code itself, written to the accepted shapes — nothing left to decide pre-gate |
| 46 | Open (later phase) | Multi-company/multi-store isolation | No | No | No | DESCOPE | DEC-003 (single-store MVP); AR-019 §10 store-scoping | Descoped from MVP; containment = Phase 1 keys/record rules must not preclude it (already accepted) |
| 48 | Open | Packaging/install convenience | No | No | Docs only | REL | Register row (Blocks: No) | Descoped from gate; release-readiness install-docs item |
| 49 | Open | MVP-scale throughput validation | No | No | **Yes** | REL | Register row; DEC-005 revisit trigger 2 | Descoped from gate; concrete release-readiness gate (validate under `--max-cron-threads=2` before release) |
| 50 | Open (trigger-gated) | OCA `queue_job` adoption | No | No | No | AO | DEC-005 revisit triggers; RA-004 | Accepted-open; containment = DEC-005's three explicit revisit triggers |
| 51 | Open | GraphQL pacing parameters | No (no API calls in slice 1) | Yes — transport-client task | No | SLICE+TASK | AR-018 §4/§5 | Descoped from first gate; constants fixed in transport-client task spec (MBQ-16-style adjustable defaults) |
| 52 | Resolved (policy); residual mechanics | API-version upgrade mechanics | No | Yes — transport task detail | Partly (runbook) | TASK+REL | DEC-018; §4.14 (2026-04 `@idempotent` requirement shows version pinning is load-bearing) | Partially resolved; residual = transport task-spec detail + release-readiness upgrade runbook |
| 53 | Partially resolved (screen-design level) | Screen-level UI/UX | No (zero-UI slice) | Yes — every UI-bearing task | No | TASK | DEC-016; MBQ-03/22 routes above | Partially resolved (unchanged level); residual closes per UI-bearing task via accepted Part D + MBQ-03/22 routes |
| 54 | Resolved (posture); residual guard/copy | Uninstall/disable lifecycle | No | No | **Yes** | REL | DEC-018 | Partially resolved; residual = guard mechanism + disclosure copy before first release |
| 55 | Open | Domain binding model/field names | No | **Yes — product/sale/inventory/fulfillment slices** | No | SLICE | Register row; AR-019 precedent | Descoped from first gate; blocks domain slices; route = a domain naming/schema planning pass (PR #85 pattern) before step 8 (§9) |
| 56 | Open | Total-check tolerance mechanism | No | Yes — order import | No | SLICE+TASK | Part B §C.8 (guard fixed; tolerance open) | Descoped from first gate; blocks order-import task authoring; must be fixed in that task spec |
| 57 | Open (future only) | Whole-order-hold alternative | No | No | No | DESCOPE | Register row | Descoped: future-phase reconsideration only; current rule stands |
| 58 | Open (refinement) | Order-identity nuances | No | No | No | AO | Register row; Part A §C.6 | Accepted-open; containment = binding-based defensive design already accepted |
| 59 | Resolved (policy); residual detail | Automated create/bind mechanics | No | Yes — domain-automation task detail | No | TASK | DEC-014 | Partially resolved; residual = eligibility/match-confidence detail in domain-automation task specs |
| 60 | Resolved (posture); residual manifest/wording | `stock_delivery` dependency | No | Yes — fulfillment task detail | No | TASK | DEC-018 | Partially resolved; residual = manifest `depends` + readiness wording in fulfillment task spec |
| 61 | Open | FulfillmentOrder lifecycle events | No | No (existing manual review contains) | No | DESCOPE+AO | Part C §B.11 (no lifecycle-family subscription proposed) | Descoped from MVP: no `FULFILLMENT_ORDERS_*` lifecycle subscription in Phase 1; containment = manual-review on rejected calls + reconciliation |
| 63 | Open | Inventory webhook payload/scope | No | Only webhook-driven inventory import | No | DESCOPE | Part C §A.7/§A.9 ("candidate… never the sole mechanism") | Proposed: webhook-driven inventory import descoped from Phase 1; payload verification precondition if ever proposed |
| 64 | Resolved (posture); residual mapping | Currency divergence mechanics | No | Yes — order-import task detail | No | TASK | DEC-020 | Partially resolved; residual = error-class/sub-reason mapping + enforcement mechanism in order-import task spec |
| 65 | Resolved (posture); residual mechanics | Product webhook mechanics | No | Yes — product-webhook task detail | No | TASK | DEC-020 | Partially resolved; residual = controller/job/query/subscription mechanics in product-webhook task spec; truncation claim verified in-task |

## 4. Proposed final MBQ decisions

Decision blocks for every row above. Blocks are grouped: §4.A gives the
full blocks for rows where this plan proposes **new substance** (evidence
or a conservative default); §4.B gives compact blocks for rows whose
closure is a **scope/routing classification** of already-accepted content
(nothing is reopened; no accepted DEC/AR/blueprint content is changed).

### §4.A Rows with new substance

#### MBQ-09 — Compliance webhooks / protected customer data

- **Question:** whether custom apps must implement Shopify's compliance
  webhooks / are bound by Level 1/2 protected-data obligations regardless
  of distribution.
- **Proposed final status:** Partially resolved at fact-verification
  level; compliance-webhook implementation confirmed non-MVP; conservative
  posture stands. Residual = two narrow open questions (below) that block
  only a future compliance-webhook feature, never MVP.
- **Decision (proposed for ChatGPT acceptance):** Phase 1 keeps DEC-004's
  accepted conservative posture (treat data-subject obligations as
  conservatively applicable; masking, least-privilege scopes, data
  minimization). Compliance-webhook endpoints remain out of MVP scope,
  consistent with DEC-003's existing non-goal ("app billing/compliance
  webhook work — unless distribution is later decided") and with the newly
  verified fact that Shopify documents the mandate as an App-Store
  requirement. The admin-created-custom-app Level 2 plan dependence
  becomes a named setup-wizard readiness-check item (MBQ-06 list) when
  that slice is built.
- **Rationale:** the mandate's scoping is now verified; the conservative
  posture already accepted by DEC-004 contains the residual risk without
  blocking core scaffolding or PII import under custom distribution.
- **Evidence/source (all accessed 2026-07-05, Accessible):**
  - **[Fact]** "Mandatory compliance webhooks are callback methods that
    Shopify requires for apps listed on the Shopify App Store." and
    "Every app that's distributed through the Shopify App Store must
    subscribe to the following compliance webhook topics:"
    (`customers/data_request`, `customers/redact`, `shop/redact`) —
    https://shopify.dev/docs/apps/build/privacy-law-compliance (direct
    quotes; the page never mentions custom apps — verified by text grep).
  - **[Fact]** The `compliance_topics` webhook property in the official
    app-configuration reference is marked Required? = "No", described as
    "required topics to subscribe to for all apps distributed in the
    Shopify App Store" —
    https://shopify.dev/docs/apps/build/cli-for-apps/app-configuration
    (direct quote).
  - **[Fact]** The protected-customer-data page explicitly tables custom
    apps: review applies to public apps; Partner-Dashboard custom apps:
    Level 1 and Level 2 "Always available"; admin-created custom apps:
    Level 1 "Always available", Level 2 "Varies by plan"; "While we
    encourage all apps to meet protected customer data requirements,
    access to the different levels can vary based on app types." —
    https://shopify.dev/docs/apps/launch/protected-customer-data (direct
    quotes).
  - **[Fact]** The distribution capabilities table shows "Approval
    required: No" for custom distribution and admin-created apps —
    https://shopify.dev/docs/apps/launch/distribution (direct quote).
  - **[Inference — labelled, not asserted as fact]** because every
    official scoping sentence ties the compliance-webhook mandate to App
    Store distribution and enforcement is App-Store review, the mandate is
    not enforced on custom apps. Underlying privacy law (GDPR/CPRA)
    still applies to any developer handling personal data.
  - **[Open question — residual]** (a) whether Shopify delivers
    compliance topics to custom apps that voluntarily subscribe; (b) the
    exact plan matrix behind "Varies by plan" for admin-created apps.
    Neither is stated in the fetched official pages.
- **Scope impact:** removes the last compliance ambiguity blocking
  customer-PII import under custom distribution (with the conservative
  posture); adds one future readiness-check item.
- **Now allowed (after acceptance + gate):** core scaffolding and, at the
  domain slice, customer/order import under the conservative posture.
- **Remains disallowed:** any compliance-webhook endpoint work (non-MVP);
  any assumption that privacy-law duties are absent; any Level 2 field
  reliance on admin-created apps without the readiness check.
- **Blocks first implementation gate:** **No.**

#### MBQ-14 — `@idempotent` key uniqueness scope

- **Question:** `@idempotent` key uniqueness scope (per-shop / per-app /
  global) and any API-version-specific behaviour.
- **Proposed final status:** Partially resolved at fact-verification
  level; the undocumented uniqueness scope is contained by a conservative
  key-generation default; exact mechanics = inventory-task detail.
- **Decision (proposed):** the connector never relies on any assumed
  server-side scope: every logical operation gets a fresh, randomly
  generated UUID idempotency key (collision-safe under *any* scope),
  stored on the job (the accepted MBQ-20 `idempotency_key` schema remains
  the connector-side dedup authority); retries older than Shopify's
  24-hour retention window must not assume server-side dedup — the
  accepted connector-side guards (`idempotency_key`,
  `operation_scope_key`, DEC-005 reconciliation) are the primary
  protection, which is exactly the already-accepted design.
- **Rationale:** closes the row without inventing an undocumented
  platform fact; RA-017 (no connector-designed idempotency key) stays
  rejected — this strengthens, not replaces, the connector-side key.
- **Evidence/source (all accessed 2026-07-05, Accessible):**
  - **[Fact]** `inventorySetQuantities`: "As of 2026-01, this mutation
    supports an optional idempotency key using the `@idempotent`
    directive." … "As of 2026-04, the idempotency key is required" —
    https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities
    (direct quotes; same for `inventoryAdjustQuantities` at
    https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventoryAdjustQuantities).
  - **[Fact]** "Shopify tracks idempotency keys for **24 hours** from the
    original request." "After 24 hours, idempotency keys expire and are no
    longer recognized as duplicates." —
    https://shopify.dev/docs/api/usage/implementing-idempotency (direct
    quotes). Same page documents input-variable fingerprinting and an
    `IDEMPOTENCY_CONCURRENT_REQUEST` error code.
  - **[Fact]** "An idempotency key is a unique string identifier
    generated by your app." — recommend "a randomly generated universally
    unique identifier (UUID) to avoid collisions." —
    https://shopify.dev/docs/api/usage/idempotent-requests (direct quotes).
  - **[Fact — negative]** neither official idempotency page states the
    uniqueness scope (per shop / per app / global) — verified by targeted
    text greps; logged as an open platform fact, not asserted either way.
- **Scope impact:** the inventory/refund write design no longer waits on
  an unobtainable official statement; version pinning (MBQ-52) must land
  on a version where the directive's required/optional status is known
  (2026-04+ requires it) — a task-spec input, already covered by the
  accepted pinning policy.
- **Now allowed:** inventory-write task authoring with UUID-per-operation
  keys.
- **Remains disallowed:** relying on server-side dedup across >24h
  retries or across an assumed scope; dropping the connector-side key.
- **Blocks first implementation gate:** **No.**

#### MBQ-24 — `productSet` delete-on-omit for media

- **Question:** whether `productSet` delete-on-omit applies to
  product/variant media identically to variants/collections/metafields.
- **Proposed final status:** Partially resolved (platform facts verified;
  media behaviour itself still officially unconfirmed); MVP contained by
  disabling automated media replace/remove.
- **Decision (proposed):** Phase 1 product export treats existing Shopify
  media as **write-protected by default**: no automated export path may
  replace or remove existing media; media additions and any
  replace/remove operation are explicit, operator-initiated,
  destructive-write-preview-gated actions only (the already-accepted Part
  B §A.13/§A.11 guard, unweakened). Before any media-list-shaped write
  ships, the product-export implementation task must include a live-API
  verification step for omit behaviour, logged with evidence — until
  then, omit-media writes are neither assumed safe nor assumed
  destructive.
- **Rationale:** the official docs are verifiably silent; the accepted
  belt-and-suspenders preview posture already refuses to depend on this
  fact; disabling automated media overwrite closes the row for MVP
  without waiting on Shopify.
- **Evidence/source (all accessed 2026-07-05, Accessible):**
  - **[Fact]** `productSet` reference: "For list fields: Creates new
    entries, updates existing entries, and deletes existing entries that
    aren't included in the mutation's input. Common examples of list
    fields include `collections`, `metafields`, and `variants`." — files/
    media are not named —
    https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet
    (direct quote, verified in raw page HTML).
  - **[Fact]** `ProductSetInput.files` is a list type (`[FileSetInput!]`),
    description: "The files to associate with the product." — no omission
    semantics stated —
    https://shopify.dev/docs/api/admin-graphql/latest/input-objects/ProductSetInput.
  - **[Fact]** The official sync-data guide narrows complete-state
    replacement to options and variants: "For options and variants, the
    mutation replaces the complete state… For other product fields (like
    description or tags), omitted fields remain unchanged" —
    https://shopify.dev/docs/apps/build/graphql/migrate/new-product-model/sync-data
    (direct quote). **[Fact]** This creates a documented tension with the
    reference page's general list-field rule; media is covered by neither
    statement explicitly.
  - **[Inference — labelled]** `files` being a list type means the
    list-field rule *could* apply; this is not asserted.
- **Scope impact:** product export (non-media) proceeds at its slice;
  media replace/remove is out of automated MVP paths.
- **Now allowed:** product-export task authoring with media
  write-protection; preview-gated manual media operations per the
  accepted guard.
- **Remains disallowed:** any automated media replace/remove; any
  omit-media list write before the in-task live verification.
- **Blocks first implementation gate:** **No.** Blocks only the media
  portion of the product-export slice, which this default disables.

#### MBQ-27 — Representing Shopify-computed tax on an Odoo sale order

- **Question:** exact mechanism for representing Shopify-computed tax on
  an Odoo sale order without Odoo's tax engine recomputing/overriding,
  keeping totals reconcilable.
- **Proposed final status:** **Not resolved — explicitly descoped from
  the first implementation gate; blocks the order-import task only**, with
  a mandatory containment posture and a dedicated pre-task decision step.
- **Decision (proposed):** (1) the verified negative finding below is
  recorded: no documented, supported Odoo 19 mechanism exists for forcing
  externally computed tax amounts on a `sale.order`. (2) Phase 1 order
  import therefore stays in the already-accepted conservative posture:
  Shopify tax amounts are preserved as **evidence only** (DEC-007 §6 /
  Part B §C.9); the mandatory, permanent total-check guard (Part B §C.8)
  runs before finalization; any divergence beyond the (MBQ-56) tolerance
  is `financial total mismatch` — conservative, never silent, never
  auto-retried, manual review. (3) The exact representation mechanism
  (fiscal-position/tax mapping so Odoo's own computation approximates
  Shopify's, Amazon-connector-style; tax-included pricing; or any other
  candidate) is decided in a dedicated MBQ-27 decision step **before the
  order-import task is written** (§9 step 8). (4) Using Odoo's
  internal `manual_tax_amounts`/`extra_tax_data` engine mechanism is
  **not permitted without a dedicated ADR and explicit ChatGPT decision**
  — it is undocumented, technical/private API with deprecated helpers in
  19.0.
- **Rationale:** the row cannot be honestly resolved now — official
  evidence affirmatively shows no supported mechanism; the safest closure
  is explicit scoping plus the guard, exactly matching this session's
  scope-closure strategy rule 2.
- **Evidence/source (all accessed 2026-07-05, Accessible):**
  - **[Fact — negative]** Odoo 19 taxes documentation
    (https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes.html
    and …/taxes/tax_computation.html) documents no mechanism for
    setting/importing an externally computed tax amount and no way to
    prevent recomputation.
  - **[Fact]** Odoo's official Amazon Connector docs: "the taxes applied
    to the sales order items are those set on the product, or determined
    by the fiscal position" and order totals "differ by a few cents"
    from Amazon, resolved "with a write-off" at reconciliation —
    https://www.odoo.com/documentation/19.0/applications/sales/sales/amazon_connector/setup.html
    (direct quotes). This is the officially documented pattern for
    marketplace order import: Odoo recomputes; differences are tolerated
    and written off.
  - **[Fact]** Odoo 19.0 source: `sale.order.line.price_tax` and order
    totals are engine-computed with no writable manual-tax field
    (`tax_totals = fields.Binary(compute='_compute_tax_totals',
    exportable=False)`, no inverse on `sale.order`) —
    https://github.com/odoo/odoo/blob/19.0/addons/sale/models/sale_order.py,
    …/sale_order_line.py (direct quotes).
  - **[Fact]** `account.move.tax_totals` has an inverse ("Edit Tax
    amounts if you encounter rounding issues.") on invoices/receipts
    only, not sale orders —
    https://github.com/odoo/odoo/blob/19.0/addons/account/models/account_move.py.
  - **[Fact]** An internal engine mechanism (`manual_tax_amounts` /
    `extra_tax_data` JSON on `sale.order.line` and `account.move.line`)
    can force tax amounts but is commented as a technical field, is
    absent from official documentation, and two related helpers are
    marked deprecated in 19.0 —
    https://github.com/odoo/odoo/blob/19.0/addons/account/models/account_tax.py
    (direct quotes in the research record).
  - **[Fact]** Tax-included pricing is documented ("tax amount = sales
    price × tax rate / (1 + tax rate)") but computes, not accepts, the
    tax split —
    https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes/tax_computation.html.
  - **[Fact]** AvaTax is the only documented externally computed tax path
    (Avalara-specific modules) —
    https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes/avatax.html.
- **Scope impact:** order-import task authoring is blocked until the
  dedicated MBQ-27 mechanism decision; nothing earlier in the sequence is
  blocked.
- **Now allowed:** everything up to and including customer import;
  order-import *planning*.
- **Remains disallowed:** writing the order-import task before the
  MBQ-27 mechanism decision; any silent tax divergence; any
  `extra_tax_data` use without ADR + ChatGPT decision.
- **Blocks first implementation gate:** **No.** Blocks the order-import
  slice (§6 class C).

#### MBQ-29 — Default-customer fallback granularity

- **Question:** whether one shared fallback partner per store is
  sufficient, or per-order anonymous identity is needed.
- **Proposed final status:** **Resolved (decision level, on package
  acceptance).**
- **Decision (proposed):** one single, deliberately created, clearly
  flagged fallback partner per store (the DEC-014-accepted direction) is
  the Phase 1 answer, used only for genuine no-PII orders, never for
  ordinary matching failures, every fallback-bound order carrying the
  accepted visible audit marker. Per-order anonymous identity is
  explicitly **non-MVP** (revisitable only via a documented privacy
  requirement).
- **Rationale:** the accepted direction already contains all the safety
  properties (flagged, audited, never-for-matching-failures); the finer
  granularity adds no Phase 1 safety and real complexity.
- **Evidence/source:** Part B §B.7 (DEC-014-accepted): "a single,
  deliberately-created, clearly-flagged **fallback partner per store**…
  used **only** when Shopify genuinely withholds all customer PII" (repo
  doc, accessed 2026-07-05).
- **Scope impact:** customer/order import task authoring unblocked on
  this point; exact partner naming is task-spec detail.
- **Now allowed:** customer-import task authoring with the single
  fallback partner.
- **Remains disallowed:** per-order anonymous partners in Phase 1;
  fallback use for ordinary matching failures.
- **Blocks first implementation gate:** **No.**

#### MBQ-32 — Free-to-Use quantity source selection (residual)

- **Question:** which verified Odoo source drives the Shopify `available`
  push (`product.product.free_qty` vs per-location
  `stock.quant.available_quantity`), and whether a configurable default
  is offered.
- **Proposed final status:** Partially resolved (unchanged facts) plus a
  proposed conservative default; exact mechanics = inventory task detail.
- **Decision (proposed):** Phase 1 uses **`free_qty` semantics** (nets
  out expired unreserved stock) as the single quantity definition, read
  per mapped location via location context; **no configurable
  Forecast/On-Hand/Free-to-Use source choice is offered in Phase 1 UI**
  (consistent with the MBQ-35 closure below). If the implementation
  mechanically aggregates `stock.quant.available_quantity`, the task must
  reconcile it to `free_qty` semantics and carry an acceptance test for
  the documented divergence case (expired unreserved stock) — the DEC-015
  finding that the two sources are not equivalent is preserved, not
  papered over.
- **Rationale:** `free_qty` is the source whose verified formula matches
  the accepted "Free to Use" semantic concept (DEC-010); choosing the
  stricter (lower-or-equal) definition is the conservative side against
  overselling; RA-021's demand for an explicit quantity-field decision is
  satisfied rather than deferred.
- **Evidence/source:** Part C §A.4 (DEC-015-accepted, official Odoo 19.0
  source cited there, accessed 2026-07-03): `free_qty =
  uom.round(qty_available − reserved_quantity − expired_unreserved_qty)`;
  `available_quantity = quantity − reserved_quantity`; "verified but are
  NOT equivalent… diverge whenever expired unreserved stock exists."
- **Scope impact:** inventory write-back task authoring unblocked on the
  source question; mechanics land in the task spec.
- **Now allowed:** inventory task authoring against `free_qty` semantics.
- **Remains disallowed:** writing `on_hand`-style multi-state sums as
  `available`; `committed` writes (RA-018, permanent); a Phase 1
  source-choice UI.
- **Blocks first implementation gate:** **No.**

#### MBQ-35 — `on_hand` UI exposure

- **Question:** whether `on_hand` is ever exposed as a Phase 1 UI choice.
- **Proposed final status:** **Resolved by explicit conservative scope
  exclusion (on package acceptance).**
- **Decision (proposed):** `on_hand` is **not** exposed as a Phase 1 UI
  choice. `available` is the sole Phase 1 write target; `committed` is
  never written (RA-018, unchanged). Any future `on_hand` exposure
  requires the register row's own bar: explicit justification and a
  ChatGPT decision, via the architecture-review log.
- **Rationale:** the row's own text says exposure needs explicit
  justification and none has emerged across Sprints C/D; closing by
  exclusion removes a standing ambiguity at zero cost.
- **Evidence/source:** register row MBQ-35; DEC-010/DEC-012 §8; Part C
  §A.4 (repo docs, accessed 2026-07-05).
- **Scope impact:** inventory UI simplifies to the accepted default path.
- **Now allowed:** inventory task authoring with `available` only.
- **Remains disallowed:** any `on_hand` UI without a new ChatGPT
  decision; `committed` writes, permanently.
- **Blocks first implementation gate:** **No.**

#### MBQ-61 — FulfillmentOrder lifecycle events beyond creation

- **Question:** whether/how the connector must react to holds,
  cancellation-request lifecycle, merges, splits, moves, reschedules.
- **Proposed final status:** **Not resolved but explicitly descoped from
  MVP**, with an accepted-open containment rule.
- **Decision (proposed):** Phase 1 does **not** subscribe to the
  `FULFILLMENT_ORDERS_*` lifecycle webhook family (formalizing Part C
  §B.11's own posture). Containment: a hold/rejection surfaces as a
  failed/ambiguous `fulfillmentCreate` outcome and routes to the existing
  accepted manual-review/ambiguous-outcome handling; the DEC-005
  reconciliation backstop covers drift. A dedicated hold-aware UX is a
  named non-MVP candidate, revisitable via the architecture-review log.
- **Rationale:** the register row itself records "No for MVP
  correctness-core"; making the descope explicit ends the ambiguity
  without new architecture.
- **Evidence/source:** Part C §B.11 (DEC-015-accepted): "this sprint does
  **not** propose subscribing to the full `FULFILLMENT_ORDERS_*`
  lifecycle family — Phase 1's reconciliation backstop… already co[vers]"
  (repo doc, accessed 2026-07-05); register row MBQ-61.
- **Scope impact:** fulfillment slice proceeds without lifecycle-family
  work.
- **Now allowed:** fulfillment task authoring per the accepted design.
- **Remains disallowed:** silent retry of a hold-rejected fulfillment;
  lifecycle-family subscription without a new decision.
- **Blocks first implementation gate:** **No.**

#### MBQ-63 — Inventory webhook payload/subscription/Phase-1 scope

- **Question:** exact `INVENTORY_LEVELS_*` payload shape/subscription
  mechanics, and whether webhook-driven inventory import is implemented
  in Phase 1 at all.
- **Proposed final status:** **Not resolved but explicitly descoped from
  MVP / first gate**: webhook-driven inventory import is **not
  implemented in Phase 1**.
- **Decision (proposed):** the Phase-1-scope half of the row is decided
  by conservative exclusion — `INVENTORY_LEVELS_UPDATE`/`_CONNECT`/
  `_DISCONNECT` remain drift-detection candidates only, exactly as Part C
  §A.7/§A.9 already frame them ("candidate… never the sole mechanism");
  the accepted layered scheduled/manual/`odoo_event`/reconciliation
  mechanisms are Phase 1's only inventory-sync paths. The
  payload-shape/subscription-mechanics half becomes a named
  official-doc-verification precondition of any future decision to
  implement webhook-driven inventory import (post-MVP), routed via the
  architecture-review log.
- **Rationale:** removes a "Blocks implementation: Yes" row from the MVP
  path without weakening anything — no accepted mechanism depends on this
  webhook; building on an unverified payload is exactly what MBQ-65's
  accepted enqueue-only posture exists to avoid.
- **Evidence/source:** Part C §A.7/§A.9 and §G MBQ-63 row (repo doc,
  accessed 2026-07-05); DEC-015/DEC-005.
- **Scope impact:** inventory slice ships without a webhook import path.
- **Now allowed:** inventory task authoring (scheduled/manual/event/
  reconciliation triggers only).
- **Remains disallowed:** any Phase 1 webhook-driven inventory import;
  any future implementation without payload/subscription verification.
- **Blocks first implementation gate:** **No.**

### §4.B Rows closed by scope/routing classification

Common format; nothing here reopens an accepted decision. "Task-spec
detail" means: the residual must be fixed inside the affected future
implementation task's own `CLAUDE.md` §9 specification (allowed files,
acceptance criteria, tests) **before that task's code is written** — the
template is the enforcement mechanism, so the register no longer needs to
hold the gate hostage for it.

- **MBQ-03** — exact view/menu/action XML IDs. **Proposed:** descoped
  from the first gate (the accepted first slice is zero-UI, AR-018 §5);
  every UI-bearing task spec must commit its exact XML IDs (following the
  AR-019 naming conventions) before its code. Blocks UI-bearing tasks
  only. **Gate: No.**
- **MBQ-04** — credential storage. **Proposed: no change** — the
  AR-019-accepted full slice-1 descope stands; blocks the
  credential/setup/test-connection slice pending official Odoo
  encryption-at-rest evidence + a separate ChatGPT decision (§9 step 6).
  **Gate: No** (descoped). Not re-decided here.
- **MBQ-05** — custom-app creation surface / token mechanics. **Proposed:**
  descoped from the first gate; official-doc verification + design inside
  the setup-wizard slice (§9 step 6–7), within DEC-004's fixed
  offline/unattended model. Partial supporting facts (distribution table,
  auth methods) verified 2026-07-05 (§4.9 sources). **Gate: No.**
- **MBQ-06 residual** — exact readiness-check copy/XML IDs/thresholds:
  wizard task-spec detail. **Gate: No.**
- **MBQ-08 residual** — disconnect/reconnect field/state mechanics:
  store-lifecycle task-spec detail. **Gate: No.**
- **MBQ-10** — turnkey install prerequisites: release-readiness
  install-docs item; never a design blocker. **Gate: No.**
- **MBQ-12** — GID permanence. **Accepted-open risk.** Containment: the
  accepted defensive design (stale/review, never silent recreate) does
  not depend on the answer; may remain permanently unresolved. **Gate:
  No.**
- **MBQ-13** — stale-binding review flow detail: error-center/matching
  task-spec detail (behavioural rules already fixed). **Gate: No.**
- **MBQ-15** — Bulk Operation idempotency/resumability. **Proposed:**
  descoped — internal bulk is not used by any MVP slice (DEC-003: not a
  user-facing feature; no accepted mechanism adopts it internally). If a
  future task proposes internal bulk, official verification of
  resumability + per-row idempotency keys is a precondition (**[Fact]**,
  captured 2026-07-05: "each row in the JSONL file… needs its own unique
  idempotency key" —
  https://shopify.dev/docs/api/usage/implementing-idempotency). **Gate:
  No.**
- **MBQ-17 residual** — exact reconciliation interval/batch constants:
  per-domain task-spec detail (posture accepted by DEC-018). **Gate:
  No.**
- **MBQ-18** — cron cadence/throughput. **Proposed split:** (a) the
  constants sub-part is task-spec detail: the first task that codes the
  queue-drain cron loop must commit batch-size/interval constants as
  adjustable planning defaults, mirroring MBQ-16's accepted treatment
  (AR-019 §9) — if the first core task excludes the cron loop, nothing is
  needed at the gate; (b) the throughput-validation sub-part is the
  MBQ-49 release-readiness gate. **Gate: No.**
- **MBQ-22** — user-facing copy. **Proposed:** descoped from the gate
  under a controlled-placeholder rule: any UI-bearing task may ship
  explicitly marked placeholder copy, inventoried in the task spec; a
  dedicated copy/UX-writing pass is a named release-readiness gate item.
  Exact copy never blocks backend model implementation. **Gate: No.**
- **MBQ-23 residual** — exact variant-mutation choice/batching: product-
  export task-spec detail (direction accepted by DEC-014). **Gate: No.**
- **MBQ-25 residual** — channel-selection UX: product-export task-spec
  detail (mechanism accepted by DEC-014). **Gate: No.**
- **MBQ-28** — Domain 9 draft-artifact guard. **Accepted-open risk.**
  Containment is the guard itself: if any implementation-planning step
  finds a draft invoice/payment artifact required, the question returns
  to ChatGPT before that code is written. Not triggered by any accepted
  blueprint. **Gate: No.**
- **MBQ-30 residual** — gateway→journal mapping schema: sale-slice
  task-spec detail (concept accepted; classification/routing input only).
  **Gate: No.**
- **MBQ-33 residual** — first-push confirmation-record schema and
  batched-review UI: inventory task-spec detail (granularity accepted by
  DEC-018; jointly with MBQ-38). **Gate: No.**
- **MBQ-34 residual** — review-queue UX/copy; any future auto-apply flag
  design: inventory task-spec detail (default accepted by DEC-018).
  **Gate: No.**
- **MBQ-36 residual** — exact per-trigger mutation choice, batching,
  error handling: inventory task-spec detail (direction accepted by
  DEC-015); the task spec must include the `@idempotent` key wiring per
  the MBQ-14 facts above. **Gate: No.**
- **MBQ-38 residual** — exact confirmation-record field names/schema:
  inventory task-spec detail (concept accepted by DEC-015). **Gate: No.**
- **MBQ-40 residual** — delivery-specific backorder wizard UX/copy
  nuance: fulfillment task-spec detail, including an in-task verification
  of the Odoo 19 delivery backorder wizard behaviour against official
  source. **Gate: No.**
- **MBQ-41 residual** — whether standard Odoo already exposes a per-order
  notification toggle: a single named implementation-time check in the
  fulfillment task spec (default accepted by DEC-018; per-order override
  remains deferred, not rejected). **Gate: No.**
- **MBQ-42 residual** — mismatch sub-reason tagging detail: fulfillment
  task-spec detail (mechanism accepted by DEC-015 at blueprint level).
  **Gate: No.**
- **MBQ-43 residual** — cache refresh cadence/mechanism: fulfillment/
  inventory task-spec detail (precedence rule accepted: live read always
  wins). **Gate: No.**
- **MBQ-44 residual** — the actual `ir.model.access.csv` file and record
  rules. **Proposed reading:** the residual **is the gated slice-1 code
  artifact itself**, to be written exactly to the accepted §10 row shapes
  (AR-019); there is no planning decision left. It cannot close before
  the gate by definition and therefore does not block opening it. **Gate:
  No.**
- **MBQ-46** — multi-company/multi-store isolation. **Proposed:**
  descoped from MVP (single-store, single-company, DEC-003). Containment:
  Phase 1 keys and the store-scoped record-rule planning (AR-019 §10)
  must not preclude later isolation — already the accepted design.
  **Gate: No.**
- **MBQ-48** — Odoo.sh vs on-prem packaging convenience:
  release-readiness install-docs item. **Gate: No.**
- **MBQ-49** — MVP-scale throughput validation. **Proposed:** confirmed
  as a **concrete release-readiness gate**: before first release, the
  internal cron-queue must be validated at realistic single-store
  volumes under `--max-cron-threads=2`; failure triggers DEC-005's
  `queue_job` revisit trigger 2. Never blocks code start. **Gate: No.**
- **MBQ-50** — OCA `queue_job` adoption. **Accepted-open risk.**
  Containment: adoption only via DEC-005's three explicit revisit
  triggers (RA-004 unchanged). **Gate: No.**
- **MBQ-51** — GraphQL cost/throttle pacing parameters. **Proposed:**
  descoped from the first gate (slice 1 makes no external API calls,
  AR-018 §5); the transport-client task spec must commit pacing/
  backpressure constants as adjustable planning defaults (MBQ-16-style).
  **Gate: No.**
- **MBQ-52 residual** — upgrade-execution mechanics and deprecation-
  warning copy/thresholds: transport task-spec detail plus a
  release-readiness upgrade-runbook item (policy accepted by DEC-018;
  the 2026-04 `@idempotent` requirement verified above is a concrete
  example of why the pinning policy is load-bearing). **Gate: No.**
- **MBQ-53 residual** — full screen-level closure. **Proposed:** the
  screen-design blueprint level stands (DEC-016); the residual closes
  per UI-bearing task: each such task spec commits its exact XML IDs
  (MBQ-03 route), uses controlled placeholder copy (MBQ-22 route), and
  the accepted groups (MBQ-45); pixel-level polish remains a
  release-readiness concern. Blocks operator-facing UI tasks only —
  never the zero-UI core slice. **Gate: No.**
- **MBQ-54 residual** — exact uninstall-guard mechanism / disclosure
  copy: must exist **before first release** (posture accepted by
  DEC-018); a release-readiness gate item, not an initial-coding blocker.
  **Gate: No.**
- **MBQ-55** — domain binding model/field names. **Proposed:** descoped
  from the first gate; **blocks every domain slice** (product/sale/
  inventory/fulfillment). Route: a dedicated, documentation-only **domain
  naming/schema planning pass** (exact PR #85 pattern, extending the
  accepted `shopify.connector.*` conventions and the binding-mixin
  contract) must be accepted before §9 step 8. **Gate: No.**
- **MBQ-56** — total-check tolerance/comparison mechanism. **Proposed:**
  descoped from the first gate; blocks the order-import task: its task
  spec must fix the exact Shopify total field(s), the currency-rounding
  tolerance, and the summed evidence components before code (the guard
  itself is accepted, mandatory, permanent). Jointly sequenced with the
  MBQ-27 mechanism decision and MBQ-64's residual. **Gate: No.**
- **MBQ-57** — whole-order-hold alternative: future-phase reconsideration
  only; the accepted rule stands unweakened. Descoped from MVP. **Gate:
  No.**
- **MBQ-58** — order-identity stability nuances. **Accepted-open risk.**
  Containment: the accepted binding-based defensive design covers the
  general case; nuances (test-mode orders, converted draft orders) are
  refinements verified opportunistically at the order-import task. **Gate:
  No.**
- **MBQ-59 residual** — exact eligibility-check/match-confidence
  implementation detail: domain-automation task-spec detail (policy
  accepted by DEC-014). **Gate: No.**
- **MBQ-60 residual** — manifest `depends` mechanics and exact
  readiness-check wording: fulfillment task-spec detail (dependency
  posture accepted by DEC-018). **Gate: No.**
- **MBQ-64 residual** — exact error-class/sub-reason mapping and
  enforcement mechanism for a blocked divergent-currency order:
  order-import task-spec detail (posture accepted by DEC-020; the task
  spec must carry it with the same rigor DEC-018/019 applied to MBQ-62).
  **Gate: No.**
- **MBQ-65 residual** — exact controller/job/query/subscription
  mechanics; the unconfirmed variant-count payload-truncation claim:
  product-webhook task-spec detail (posture accepted by DEC-020). The
  truncation claim needs no pre-verification **because** the accepted
  enqueue-only + mandatory-follow-up-authoritative-read posture makes
  payload completeness non-load-bearing by design; it is verified
  in-task. **Gate: No.**

## 5. Conservative default decisions for speed

The defaults actually used above, each checked against the register text,
the accepted decisions, and `rejected-approaches-log.md` (RA-001–RA-023
reviewed in full this session; none reintroduced — every default below is
*more* restrictive than the accepted baseline, never less):

1. **Advanced/uncertain features descoped from MVP:** MBQ-61 (lifecycle
   family), MBQ-63 (webhook-driven inventory import), MBQ-15 (internal
   bulk), MBQ-57 (hold-rule alternative), MBQ-46 (multi-company), per-order
   anonymous identity (MBQ-29), `on_hand` UI (MBQ-35).
2. **Compliance/security uncertainty blocks only affected functionality:**
   MBQ-09 residuals block a future compliance-webhook feature, not core
   scaffolding; MBQ-04 blocks only credential-touching code (unchanged).
3. **Markets/multi-currency stays non-MVP:** unchanged — DEC-020's
   same-currency-only posture and DEC-007 §3's exclusion are simply not
   reopened.
4. **Credential storage stays blocked** pending official Odoo evidence
   and a ChatGPT decision: unchanged (MBQ-04).
5. **Media delete-on-omit uncertainty → automated media overwrite
   disabled in MVP** (MBQ-24), on top of the accepted preview guard,
   with in-task live verification before any media-list write ships.
6. **Tax mechanism uncertainty → conservative import posture** (MBQ-27):
   evidence-only tax capture + mandatory total-check guard + manual
   review on divergence; mechanism decided before the order-import task;
   no undocumented API without ADR.
7. **Exact UI copy does not block backend implementation** (MBQ-22):
   explicitly controlled placeholder copy, inventoried per task,
   reviewed at a named release-readiness copy pass.
8. **Advanced lifecycle webhook topics monitored/reconciled later**
   (MBQ-61/63): reconciliation is the accepted backstop; nothing about
   safe basic fulfillment depends on them.
9. **Undocumented platform facts closed by scope-independent design, not
   assumption:** UUID-per-operation idempotency keys (MBQ-14);
   payload-non-authoritative webhook handling (MBQ-65 residual).

## 6. MVP implementation gate impact

Classification of all 50 rows after the proposed closure:

| Class | Meaning | Rows | Count |
| --- | --- | --- | --- |
| A | Does not block first core code | MBQ-12, 13, 17, 18, 22, 28, 29, 30, 35, 44, 46, 53, 57, 58 | 14 |
| B | Blocks only credential/setup/test-connection (incl. transport) | MBQ-03, 04, 05, 06, 08, 51, 52 | 7 |
| C | Blocks product/customer/order slice | MBQ-23, 24, 25, 27, 55*, 56, 59, 64, 65 | 9 |
| D | Blocks inventory/fulfillment slice | MBQ-14, 32, 33, 34, 36, 38, 40, 41, 42, 43, 60 | 11 |
| E | Blocks release readiness only | MBQ-10, 48, 49, 54 | 4 |
| F | Explicitly non-MVP / future | MBQ-09 (residuals), 15, 50, 61, 63 | 5 |
| G | **Still blocks implementation gate** | — | **0** |

\* MBQ-55 also gates class-D slices (domain naming pass covers all four
domain modules). MBQ-03/53 recur per UI-bearing task in classes B–D; they
are counted once at their first occurrence (class B, setup wizard).

**Zero rows remain in class G.** For honesty: the *gate itself* still has
non-MBQ preconditions that only ChatGPT can satisfy — criterion 3 (the
explicit gate-opening act), criterion 4 (the first task written to the
`CLAUDE.md` §9 template, which happens at/after opening), and criterion
5's recorded ambiguity (the DP-003/004/006 `ESCALATED` row needs an
explicit ChatGPT confirmation that the recorded evidence-consistency gate
satisfies "a prevention rule in place", per AR-018 §3). Those are acts,
not open questions — no MBQ row requires further research or decision to
open a **limited, core-only, zero-UI** gate.

## 7. Proposed MBQ register updates

**Not applied by this PR.** Exact wording to be applied to
`master-blueprint-open-questions.md` by a future acceptance patch, if and
when ChatGPT accepts this package. Two forms are used, following the
register's own acceptance-patch pattern (append to the row's question
cell; update Decision-owner / Blocks-implementation cells where stated).

**7.1 Standard closure sentence** — append to the question cell of
MBQ-06, 08, 13, 17, 23, 25, 30, 33, 34, 36, 38, 40, 41, 42, 43, 52, 59,
60, 64, 65 (residual-routing rows), with the bracketed part per row from
§4.B:

> **Final MBQ closure (accepted by ChatGPT via AR-020 /
> [`final-mbq-closure-plan.md`](../07-implementation-plan/final-mbq-closure-plan.md),
> DATE):** the remaining residual — [residual text from §4.B] — is
> reclassified as task-spec detail of the [named task] implementation
> task: it must be fixed in that task's own `CLAUDE.md` §9 specification
> before that task's code is written, and it does not block the limited
> core-only implementation gate.

**7.2 Row-specific wording** (append to question cell; cell changes as
noted):

- **MBQ-03:** "**Final MBQ closure (AR-020, DATE):** descoped from the
  limited core-only gate (zero-UI first slice, AR-018 §5); every
  UI-bearing implementation task must commit its exact view/menu/action
  XML IDs in its own task spec, following the accepted AR-019 naming
  conventions, before its code." Blocks-implementation cell → "Yes for
  each UI-bearing task's authoring only; No for the core-only gate."
- **MBQ-05:** "**Final MBQ closure (AR-020, DATE):** blocks the
  setup-wizard/credential slice only; official-doc verification of the
  custom-app creation surface and token-acquisition mechanics is a named
  precondition of that slice (sequence step 6–7), within DEC-004's fixed
  offline/unattended model. Does not block the core-only gate."
- **MBQ-09:** "**Partially resolved by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE), at fact-verification level:**
  official Shopify docs (accessed 2026-07-05) scope the mandatory
  compliance webhooks to Shopify-App-Store-distributed apps
  (privacy-law-compliance page; `compliance_topics` marked required only
  for App Store apps), and the protected-customer-data page tables custom
  apps explicitly (Partner-Dashboard custom: Level 1/2 'Always
  available'; admin-created: Level 1 always, Level 2 'Varies by plan').
  **Accepted posture:** DEC-004's conservative posture stands;
  compliance-webhook endpoints remain non-MVP (consistent with DEC-003);
  the admin-created Level 2 plan dependence becomes a readiness-check
  item (MBQ-06 list). **Residual (open):** voluntary-subscription
  delivery behaviour and the 'Varies by plan' matrix — blocks only a
  future compliance-webhook feature." Blocks-implementation cell → "No
  for MVP under the conservative posture; Yes only for a future
  compliance-webhook feature."
- **MBQ-10:** standard sentence with "[residual text] = install-docs
  detail — [named task] = the release-readiness documentation pass."
- **MBQ-12:** "**Final MBQ closure (AR-020, DATE): accepted-open risk.**
  Containment: the accepted defensive design (stale/review, never silent
  recreate) does not depend on the answer; the row may remain permanently
  unresolved without blocking anything."
- **MBQ-14:** "**Partially resolved by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE), at fact-verification level:**
  `@idempotent` is optional as of API 2026-01 and **required as of
  2026-04** on `inventorySetQuantities`/`inventoryAdjustQuantities`; keys
  are app-generated (UUID recommended); retention is **24 hours**;
  Shopify fingerprints input variables (official pages cited in the plan,
  accessed 2026-07-05). The uniqueness scope is **not documented** —
  closed by conservative default: a fresh UUID per logical operation
  (collision-safe under any scope); connector-side `idempotency_key`/
  `operation_scope_key`/reconciliation remain the primary guards; >24h
  retries never assume server-side dedup. Exact key wiring = inventory
  task-spec detail." Blocks-implementation cell → "No — closed by
  scope-independent key design; wiring detail is task-spec only."
- **MBQ-15:** "**Final MBQ closure (AR-020, DATE):** descoped — internal
  Bulk Operations are not used by any MVP slice; any future internal-bulk
  proposal carries an official-doc verification precondition
  (resumability; per-row idempotency keys, official fact captured
  2026-07-05)."
- **MBQ-18:** "**Final MBQ closure (AR-020, DATE), scope split:** (a)
  batch-size/interval constants are task-spec detail of whichever gated
  task first codes the queue-drain cron loop, committed as adjustable
  planning defaults (MBQ-16 pattern, AR-019 §9); (b) throughput
  validation is the MBQ-49 release-readiness gate. Does not block the
  core-only gate." Blocks-implementation cell → "Yes only inside the
  cron-loop task's spec; validation blocks release readiness only."
- **MBQ-22:** "**Final MBQ closure (AR-020, DATE):** controlled
  placeholder copy is permitted in any UI-bearing task (explicitly
  marked, inventoried in the task spec); a dedicated copy pass is a named
  release-readiness gate item. Copy never blocks backend implementation."
- **MBQ-24:** "**Partially resolved by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE):** official docs verified 2026-07-05:
  the `productSet` list-field delete-on-omit rule is confirmed verbatim
  but names only `collections`/`metafields`/`variants`;
  `ProductSetInput.files` is a list type with no omission semantics
  stated; the official sync-data guide narrows complete-state replacement
  to options/variants and says other omitted fields remain unchanged — a
  documented tension; media behaviour remains officially unconfirmed
  either way. **Accepted default:** Phase 1 disables automated media
  replace/remove entirely (media additions and any replace/remove are
  explicit, preview-gated operator actions only, per the accepted §A.13
  guard); a live-API verification step is a named precondition inside the
  product-export task before any media-list write ships."
  Blocks-implementation cell → "No — automated media overwrite is
  disabled in MVP; the residual blocks only a future media-overwrite
  capability."
- **MBQ-27:** "**Final MBQ closure (AR-020, DATE) — not resolved,
  explicitly scoped:** official verification (2026-07-05) found **no
  documented supported Odoo 19 mechanism** for externally computed tax
  amounts on a `sale.order` (taxes/tax_computation docs silent;
  `sale.order` totals engine-computed with no inverse;
  `account.move.tax_totals` inverse exists on invoices only, for
  rounding; the internal `manual_tax_amounts`/`extra_tax_data` mechanism
  is technical/undocumented with deprecated helpers — its use requires a
  dedicated ADR + ChatGPT decision; Odoo's official Amazon connector
  documents recompute-plus-write-off as the sanctioned pattern).
  **Accepted containment:** order import stays evidence-only for tax
  (DEC-007 §6) behind the mandatory total-check guard (§C.8, `financial
  total mismatch`, never silent); the representation mechanism is a
  dedicated decision **before the order-import task** (closure plan §9
  step 8). Blocks the order-import slice only — not the core gate."
- **MBQ-28:** "**Final MBQ closure (AR-020, DATE): accepted-open risk.**
  Containment is the guard itself: if triggered by any implementation
  planning, the question returns to ChatGPT before affected code."
- **MBQ-29:** "**Resolved by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE):** one single, clearly-flagged
  fallback partner per store (the DEC-014-accepted direction) is the
  Phase 1 answer; per-order anonymous identity is explicitly non-MVP.
  Fallback use only for genuine no-PII orders, never matching failures;
  audit marker mandatory. Exact partner naming = task-spec detail."
  Decision-owner cell → "Resolved — ChatGPT via AR-020"; Blocks cell →
  "No."
- **MBQ-32:** "**Residual closed by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE), conservative default:** Phase 1 uses
  `free_qty` semantics (nets out expired unreserved stock) as the single
  quantity definition, per mapped location via location context; no
  source-choice UI in Phase 1; a `stock.quant`-based aggregation, if
  used mechanically, must reconcile to `free_qty` semantics with an
  acceptance test for the expired-unreserved divergence case. Exact
  mechanics = inventory task-spec detail." Blocks cell → "No — source
  decided; mechanics are task-spec detail."
- **MBQ-35:** "**Resolved by ChatGPT via AR-020 /
  final-mbq-closure-plan.md (DATE), by conservative exclusion:**
  `on_hand` is not exposed as a Phase 1 UI choice; `available` is the
  sole Phase 1 write target; `committed` never (RA-018). Future exposure
  requires explicit justification via the architecture-review log."
  Decision-owner cell → "Resolved — ChatGPT via AR-020"; Blocks cell →
  "No."
- **MBQ-44:** "**Final MBQ closure (AR-020, DATE):** the remaining
  residual is the gated slice-1 code artifact itself — the actual
  `ir.model.access.csv` and record rules, written exactly to the accepted
  AR-019 §10 row shapes; no planning decision remains; therefore it does
  not block opening the gate."
- **MBQ-46:** "**Final MBQ closure (AR-020, DATE):** descoped from MVP
  (single-store/single-company, DEC-003). Containment: Phase 1 keys and
  store-scoped record rules (AR-019 §10) must not preclude later
  isolation — unchanged accepted design."
- **MBQ-48:** standard sentence; named task = release-readiness
  documentation pass.
- **MBQ-49:** "**Final MBQ closure (AR-020, DATE):** confirmed as a
  concrete release-readiness gate — validate the internal cron queue at
  realistic single-store volumes under `--max-cron-threads=2` before
  first release; failure fires DEC-005 revisit trigger 2. Never blocks
  code start."
- **MBQ-50:** "**Final MBQ closure (AR-020, DATE): accepted-open risk.**
  Containment: adoption only via DEC-005's three explicit revisit
  triggers (RA-004 unchanged)."
- **MBQ-51:** "**Final MBQ closure (AR-020, DATE):** descoped from the
  core-only gate (slice 1 makes no external API calls); the
  transport-client task spec must commit pacing/backpressure constants
  as adjustable planning defaults (MBQ-16 pattern) before transport
  code."
- **MBQ-53:** "**Final MBQ closure (AR-020, DATE):** the accepted
  screen-design blueprint level stands; full closure is decomposed per
  UI-bearing task (exact XML IDs per MBQ-03's closure; controlled
  placeholder copy per MBQ-22's closure; accepted groups per MBQ-45);
  pixel-level polish is a release-readiness concern. Blocks
  operator-facing UI tasks only, never the zero-UI core slice."
- **MBQ-54:** standard sentence with "[named task] = a pre-release
  task; the guard mechanism and disclosure copy must exist **before
  first release** (release-readiness gate item)."
- **MBQ-55:** "**Final MBQ closure (AR-020, DATE):** blocks every domain
  slice, not the core gate; route = a dedicated, documentation-only
  domain naming/schema planning pass (PR #85 pattern, extending the
  accepted `shopify.connector.*` conventions and binding-mixin
  contract), to be accepted before the product/customer/order slice
  starts."
- **MBQ-56:** "**Final MBQ closure (AR-020, DATE):** blocks the
  order-import task only: its task spec must fix the exact Shopify total
  field(s), rounding tolerance, and summed evidence components before
  code; sequenced with the MBQ-27 mechanism decision and MBQ-64's
  residual. The guard itself remains accepted, mandatory, permanent."
- **MBQ-57:** "**Final MBQ closure (AR-020, DATE):** descoped —
  future-phase reconsideration only; the accepted whole-order-hold rule
  stands unweakened."
- **MBQ-58:** "**Final MBQ closure (AR-020, DATE): accepted-open risk.**
  Containment: the accepted binding-based defensive design covers the
  general case; nuances are verified opportunistically at the
  order-import task."
- **MBQ-61:** "**Final MBQ closure (AR-020, DATE), by conservative
  exclusion:** Phase 1 does not subscribe to the `FULFILLMENT_ORDERS_*`
  lifecycle family (formalizing §B.11). Containment: holds/rejections
  surface via the existing failed/ambiguous `fulfillmentCreate`
  manual-review handling; reconciliation is the backstop; hold-aware UX
  is a named non-MVP candidate." Blocks cell → "No."
- **MBQ-63:** "**Final MBQ closure (AR-020, DATE), by conservative
  exclusion:** webhook-driven inventory import is **not implemented in
  Phase 1** — `INVENTORY_LEVELS_*` remain drift-detection candidates
  only; the accepted layered scheduled/manual/`odoo_event`/reconciliation
  mechanisms are Phase 1's only inventory-sync paths.
  Payload/subscription verification is a named precondition of any
  future implementation decision." Blocks cell → "No for Phase 1."

## 8. Proposed implementation gate posture

**Fable recommends: READY for a first limited core implementation gate
after ChatGPT acceptance of this closure package** — strictly bounded as
follows:

- **Scope of the recommended gate:** `shopify_connector_core` substrate
  only, zero operator-facing UI, no webhooks, no external API calls, no
  credential persistence (MBQ-04 descope), exactly the AR-018 §5 slice —
  module skeleton, the six accepted core models, core access
  CSVs/groups to the accepted shapes, core tests.
- **Why it is now safe:** every MBQ row that blocked this slice was
  resolved by AR-019 (accepted); this plan closes or scopes all 50
  remaining rows with zero left in class G (§6); every proposed default
  is more conservative than the accepted baseline; nothing here weakens
  any accepted guard.
- **What must still happen first (ChatGPT acts, not research):**
  1. Accept (or amend) this closure package.
  2. Resolve AR-018's criterion 5 ambiguity: confirm the recorded
     evidence-consistency gate satisfies "a prevention rule in place"
     for the DP-003/004/006 `ESCALATED` row (or direct its relabeling).
  3. Perform the **separate, explicit gate-opening act** (criterion 3),
     limited to the slice above.
  4. Only then: the first implementation task is written to the
     `CLAUDE.md` §9 template (criterion 4) and reviewed.
- **This document does not perform, request-as-performed, or pre-empt
  any of those acts.** No implementation task is created. The gate
  remains closed. Implementation remains blocked.

## 9. Proposed first implementation sequence after closure

Sequence only — no task files. MBQ dependencies listed per item are the
rows that must be closed (or their task-spec residuals fixed in that
item's own spec) before that item starts.

1. **Limited core gate opening** (ChatGPT act) — deps: this package
   accepted; criterion-5 confirmation; no MBQ rows (all core rows closed
   by AR-019).
2. **Core scaffold** (module skeleton, manifest) — deps: none open
   (DEC-008 module names; AR-019 conventions).
3. **Core models** (the six accepted models) — deps: none open
   (MBQ-01/02/07/16/19/20/21/62 resolved). If this task codes the
   queue-drain cron loop, its spec must commit the MBQ-18 constants.
4. **Security/access** (core CSVs, groups, store-scoped record rules) —
   deps: MBQ-44's accepted row shapes (write exactly those); MBQ-45
   resolved.
5. **Core tests** — deps: none open (test strategy per Part E §9).
6. **Credential research/decision** — deps: **MBQ-04** (official Odoo
   encryption-at-rest evidence + ChatGPT decision), **MBQ-05**
   (official-doc verification of app-creation/token mechanics).
7. **Setup wizard / test connection** (first UI + transport) — deps:
   MBQ-04/05 closed by step 6; MBQ-06 residual, MBQ-03 (wizard XML IDs),
   MBQ-22 (placeholder-copy rule), MBQ-51 (pacing constants), MBQ-52
   residual — all fixed in this item's task specs; MBQ-09's
   Level-2-plan readiness-check item added here.
8. **Product/customer/order slice** — deps: **MBQ-55** (domain
   naming/schema pass accepted first); **MBQ-27** (dedicated mechanism
   decision before the order-import task); MBQ-56 + MBQ-64 residual
   (order-import task spec); MBQ-23/24/25 residuals (product-export task
   spec; media overwrite disabled per MBQ-24); MBQ-29 (closed by this
   package); MBQ-59/65 residuals (automation/webhook task specs).
9. **Inventory/fulfillment slice** — deps: MBQ-55 (same naming pass);
   MBQ-32 default (this package) + MBQ-33/34/36/38 residuals (inventory
   task specs); MBQ-14 (closed by this package; key wiring in spec);
   MBQ-40/41/42/43/60 residuals (fulfillment task specs); MBQ-35/61/63
   (closed/descoped by this package).
10. **Release readiness** — deps: MBQ-49 (throughput validation), MBQ-18
    validation sub-part, MBQ-22 (copy pass), MBQ-54 residual
    (uninstall guard/disclosure), MBQ-10/48 (install docs), MBQ-52
    (upgrade runbook).

## 10. Risks and containment rules

1. **Credential storage (MBQ-04):** contained — slice 1 contains no
   credential model or token field of any kind (AR-019 accepted descope);
   the risk cannot materialize before step 6's explicit decision.
2. **Shopify protected customer data / compliance (MBQ-09):** contained —
   verified App-Store scoping of the mandate; DEC-004 conservative
   posture stands (minimization, masking, least privilege);
   compliance-webhook feature non-MVP; Level-2 plan dependence becomes a
   readiness check.
3. **Product media destructive behaviour (MBQ-24):** contained —
   automated media replace/remove disabled in MVP; preview guard
   mandatory; live-API verification precondition in-task. Same root
   failure mode as RA-008/RA-020 — kept rejected.
4. **Odoo tax mechanism (MBQ-27):** contained — evidence-only capture,
   mandatory total-check guard, `financial total mismatch` never silent/
   auto-retried; mechanism decision gated before the order-import task;
   undocumented API barred without ADR.
5. **Cron throughput (MBQ-18/49):** contained — constants are adjustable
   planning defaults committed in-task; release-readiness validation gate
   under `--max-cron-threads=2`; DEC-005 `queue_job` revisit trigger 2 is
   the escape hatch.
6. **Advanced fulfillment lifecycle events (MBQ-61):** contained — no
   lifecycle-family subscription in Phase 1; rejected/held
   `fulfillmentCreate` routes to the accepted manual-review handling;
   reconciliation backstop.
7. **Multi-currency / presentment currency (MBQ-64):** contained —
   DEC-020's same-currency-only automatic import with pre-SO blocking
   stands; residual is task-spec mapping detail only.
8. **Webhook payload truncation (MBQ-65 residual):** contained — the
   accepted enqueue-only + mandatory follow-up authoritative read makes
   payload completeness non-load-bearing; claim verified in-task.
9. **Multi-store / multi-company isolation (MBQ-46):** contained —
   single-store MVP; store-scoped keys and record rules already in the
   accepted core schema; later phases build on, not against, them.
10. **Source-capture debt (process risk):** the official-doc excerpts
    backing §4 are embedded verbatim above with URLs/dates, but full-page
    captures under `/docs/00-source-materials` (CLAUDE.md §7.4) could not
    be added inside this session's allowed-files list — logged as a
    documentation-maintenance follow-up for the acceptance-patch session.
11. **Register staleness risk:** until the acceptance patch applies §7's
    wording, the register's own rows lag this plan — mitigated by this
    document's explicit not-applied-yet status and the acceptance-patch
    routing; also inherits the known `master-blueprint.md`/Part A §D.2
    staleness items already flagged by AR-018 §2 (not fixed here; out of
    scope).

## 11. Recommendation to ChatGPT

**Accept this closure package, then proceed to a separate, limited,
core-only implementation-gate opening** (§8's bounded scope), in this
order: (1) accept (or amend) this package and direct the acceptance patch
that applies §7 to the register; (2) confirm criterion 5's reading
(DP-003/004/006 prevention rule); (3) perform the explicit gate-opening
act for the core-only slice; (4) direct the first implementation task,
written to the `CLAUDE.md` §9 template.

This is a strict recommendation, not a soft one: zero remaining MBQ rows
block the limited core gate (§6); every closure above is either
evidence-backed (with citations), a reclassification into the
task-template enforcement mechanism the governance contract already
mandates, or a conservative default *stricter* than the accepted
baseline. Where the evidence did not support resolution (MBQ-27 mechanism,
MBQ-04, MBQ-05, MBQ-55, MBQ-56), this plan blocks the affected slice
rather than pretending closure. If ChatGPT prefers different defaults for
any §4.A row, that is an **accept with changes** on that row alone — the
package's structure does not depend on any single default.

---

**Change control:** further changes to this record require ChatGPT
review, mirroring the DEC-013 through DEC-020 pattern. This plan does not
re-litigate DEC-003 through DEC-020, does not reopen accepted Master
Blueprint Parts A–E or AR-002 through AR-019, and reintroduces no row
from `rejected-approaches-log.md` (checked in full, 2026-07-05).
