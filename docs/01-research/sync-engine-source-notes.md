# Sync Engine — Source Notes (Task 006A)

> Research phase only. No architecture decision, model design, or
> implementation is authorized by this file. Citations use the source IDs
> defined in [`sync-engine-source-inventory.md`](./sync-engine-source-inventory.md)
> (e.g. `R1`, `S7`, `O8`, `Q3`, `E2`). Classification tags follow `CLAUDE.md`
> §8: **[Fact]** · **[Competitor claim]** · **[Inference]** · **[Open
> question]**. Every claim below states whether it is a **core-engine**
> concern (the domain-neutral job/queue/retry/log substrate) or a
> **domain-module** concern (product/customer/order/inventory/fulfillment
> sync logic), or both.

## Scope of this research

This session (Task 006A) researches the evidence base for a future
domain-neutral **sync engine** — the job/queue/retry/log substrate that will
eventually execute product/customer/order/inventory/fulfillment sync. It does
**not** decide architecture, does **not** propose a schema beyond what
already exists and is accepted (`shopify.connector.job`/`.job.log`), and does
**not** authorize OAuth, a setup wizard, UI, or any domain sync
implementation. The research hierarchy followed, per the task prompt: (1)
existing repo code/accepted docs, (2) official Shopify docs, (3) official
Odoo docs/source, (4) OCA `queue_job` as reference pattern only, (5)
reputable engineering references, (6) competitor docs for externally visible
behavior only.

### Companion Task 006A shards (revision note)

This document was originally drafted before three sibling Task 006A shards
merged into `Shopify-connector`. All three are now **accepted/merged** and
this document (across two revisions) cross-references them rather than
duplicating their content. **Synthesis hierarchy:** `R31` is canonical for
Odoo/repo substrate; `R33` is canonical for queue/idempotency/retry/backoff/
dead-letter reference patterns; `R32` is canonical for competitor/common
sync patterns; this document is the cross-cutting synthesis, not a fourth
independent research pass that replaces any of the three.

- **`docs/01-research/sync-engine-odoo-repo-source-notes.md`** (`R31`, PR
  #124, "Task 006A-2 — Odoo and repository substrate research for the sync
  engine") is the **canonical Odoo/repo-substrate shard** for this task
  family — a dedicated, line-cited inspection of the same job/log/store/
  credential/readiness substrate this document also covers, plus
  substantially deeper Odoo source-code research (constraints/DDL timing,
  `@api.constrains` propagation, `cr.savepoint()` usage patterns) than this
  document independently performed. Where this document's own independent
  Odoo research (fetched the same day, 2026-07-08, via a separate research
  workflow) reaches the same conclusion, that is noted below as
  **corroboration between two independently produced shards**, not restated
  as if discovered only once. Where `R31` goes further (e.g. the
  constraint-DDL-timing/`DEFERRABLE` inference, the `@api.constrains`
  propagation mechanics), this document defers to `R31` and does not restate
  that detail.
- **`docs/01-research/sync-engine-queue-idempotency-source-notes.md`**
  (`R33`, PR #126, "Task 006A-3 — queue/idempotency/retry/backoff/dead-letter
  source notes") is the **canonical queue/idempotency/retry/backoff/
  dead-letter reference-pattern shard** for this task family — a
  52-source, 9-topic, adversarially-verified treatment covering OCA
  `queue_job`, idempotency-key design, retry/backoff/jitter, dead-letter
  visibility, duplicate-running prevention (including PostgreSQL advisory
  locks, not previously researched by this document), checkpoint/resume, and
  observability/redaction — substantially deeper than this document's own
  `E1`–`E9` engineering-reference pass on the same topics. Where this
  document's own research and `R33` converge, both are cited as
  corroboration below. Where `R33` is new, deeper, or corrects something
  this document stated less precisely, this document now defers to and
  cross-references it — see "Wording alignment against R33" callouts
  throughout the sections below.
- **`docs/01-research/sync-engine-competitor-pattern-notes.md`** (`R32`, PR
  #123, "Task 006A-4 — sync engine competitor pattern research") is the
  **canonical competitor/common-pattern shard**. It is mentioned here for
  completeness; this document's own "Competitor/common-pattern notes"
  section below was not rewritten against it, since no revision has scoped
  that specifically.

## Current repo substrate notes

The core job/log/store/credential/readiness substrate is **already
implemented and merged** (Tasks 001–005; PR #121 merged into
`Shopify-connector`, merge commit `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82`;
PR #122 docs-closure merged, merge commit
`9247fea3c36afdb761a82678f3e5e66e8ef42e87`). **This document's branch was
initially created from that PR #122 base; it has since been updated against
latest `Shopify-connector`, which now also includes PR #123 and PR #124**
(merge commit `3735ae2292d1fcf926c83034ac8513906c9f5020`). This is not a
research finding to weigh against alternatives; it is ground truth this
research must build on, not re-derive. `R31` (PR #124) independently
inspected this same substrate at the source-code level with additional
line-number citations — see the companion-shards note above.

- **[Fact]** `shopify.connector.job` (`R1`) already has: a 10-state machine
  (`draft/queued/running/succeeded/failed_final/skipped/cancelled/
  retry_waiting/failed_retryable/blocked_manual_review`), a 16-value
  `ERROR_CLASS_SELECTION` (matching DEC-009's accepted taxonomy, `R8`), a
  computed+stored `idempotency_key` (composed from `store_id`+`job_type`+
  `res_model`+`res_id`+`shopify_target_gid`+`payload_hash`), a computed+stored
  `operation_scope_key` (the DB-backed serialization guard, populated only
  while non-terminal and target-bearing, cleared on terminal/superseded), and
  enqueue-time (`create()`) + execution-time (`write()` to `running`)
  store-state gating restricted to `BUSINESS_JOB_SOURCES = ('webhook',
  'manual_sync', 'scheduled_sync', 'reconciliation', 'odoo_event')`. *Why it
  matters:* this is the exact schema any future sync-engine work must reuse,
  not redesign. *Scope:* **core engine**.
- **[Fact]** `shopify.connector.job.log` (`R2`) is an append-only child model
  with a single sanctioned write path, `_system_append()` — `sudo()`-scoped
  (no group holds `perm_create`), every free-text argument redacted via
  `redact()` before the row is created. *Why it matters:* directly answers
  the "secrets must never be logged" mandatory claim at the mechanism level —
  redaction already happens at the one write path, not as an afterthought.
  *Scope:* **core engine**.
- **[Fact]** `shopify_connector_readiness_check.py` (`R4`) implements a
  working domain-extension seam today: `_get_checks(store)` is the override
  point, domain modules extend via classic Odoo inheritance
  (`_inherit = 'shopify.connector.readiness.check'`), calling
  `super()._get_checks(store)` and appending — never removing/mutating a
  core-owned entry. *Why it matters:* this is a live, tested precedent for
  the "core dispatches, domain registers/extends" shape the job-type
  registration seam (`R12` §A.5) is expected to take. No doc in the repo
  explicitly names this as the template for job-type registration — that
  cross-reference is this session's own **[Inference]**, not an existing
  repo claim. *Scope:* **core engine** (pattern), informs how **domain
  modules** will extend it.
- **[Fact]** `shopify_connector_store.py` (`R3`) already implements
  disconnect-time cancellation of non-terminal business jobs
  (`action_disconnect()` cancels every job with `job_source in
  BUSINESS_JOB_SOURCES` and `state not in TERMINAL_JOB_STATES`, preserving
  history, never deleting). *Why it matters:* directly answers Analysis Area
  I ("what happens if a store disconnects while jobs are queued/running") —
  see the dedicated section below. *Scope:* **core engine**.

## Shopify GraphQL API notes

- **[Fact]** GraphQL is Shopify's primary, and for new public apps the
  exclusive, Admin API surface; REST is legacy as of 2024-10-01 (`R24`,
  pre-006A baseline, not re-verified this session — no new evidence
  contradicts it). *Scope:* both (this is the transport premise the whole
  connector, not just the sync engine, already assumes per DEC-004).
- **[Fact]** Connections require an explicit `first`/`last` argument — there
  is no default page size (`S3`). *Why it matters:* a sync-engine batch-size
  parameter is not optional; every paginated query the engine issues must
  carry one. *Scope:* **core engine** (the client/pagination-loop mechanism
  is core; the specific field selections per object are **domain**).

## Shopify rate-limit / cost / throttling notes

*(Re-verification not separately re-run this session for the numeric
constants themselves — R24's baseline, dated 2026-06-30/07-01/07-02, is
carried forward unchanged; no fresh fetch in this session's workflow
contradicted it. `R33`/PR #126 independently re-fetched and adversarially
verified this exact topic on 2026-07-08 — see the alignment note below.)*

- **[Fact]** REST leaky-bucket: Standard 40-request bucket / 2 req/s restore;
  Shopify Plus 400-request bucket / 20 req/s restore; HTTP 429 +
  `Retry-After` on exceed (`R24`; independently corroborated by `R33`'s
  `SH-1`, which additionally confirms the exact figure via the REST Admin
  API rate-limits page specifically, not the general limits page).
- **[Fact]** GraphQL calculated-cost throttling: points restored per second
  by plan (Standard 100, Advanced 200, Plus 1000, Enterprise 2000); a single
  query capped at 1,000 points; `extensions.cost.throttleStatus` returned on
  every response (`R24`). **`R33` flags a staleness caveat this package did
  not previously carry**: a 2023-06-07 Shopify changelog states the
  Advanced-plan GraphQL figure as 100 points/second, but the current
  "Shopify API limits" page states 200 points/second for the same tier —
  the changelog figure is superseded (`R33`'s `SH-8` vs `SH-2`). This
  package's own `R24`-carried "Advanced 200" figure already matches the
  *current* number, so no correction is needed here, but the changelog
  discrepancy is worth knowing if a future session encounters the older
  page.
- **[Fact — new this revision, from `R33`]** A throttled Shopify **GraphQL**
  call can return **HTTP 200** with a `THROTTLED` error code in the response
  body, rather than a 4xx status (`R33`'s `SH-4`). This package's own
  pre-006A rate-limit baseline (`R24`) did not independently verify GraphQL
  throttle response-status behavior — this is a genuine gap `R33` fills, not
  a correction of an existing claim. *Why it matters:* a sync-engine client
  that only branches on HTTP status code (the common pattern for REST-style
  429 handling) would **silently treat a throttled GraphQL call as
  successful** unless it also inspects the response body for a `THROTTLED`
  error code. No fetched source (by this package or `R33`) documents a
  `Retry-After`-equivalent signal for GraphQL `THROTTLED` responses
  specifically — `R33` logs this as an explicit open question, and this
  package now carries the same open question (see the companion
  open-questions document). *Scope:* **core engine** (the client/response-
  parsing logic must check the response body, not just HTTP status, for any
  GraphQL call).
- **[Inference]** Because cost/throttle status is returned on every GraphQL
  response, a sync-engine client can pace itself reactively (read
  `throttleStatus.currentlyAvailable`/`restoreRate` and back off before
  hitting 429) rather than only reactively retrying after a throttle error.
  This is this session's own inference from `R24`'s already-cited facts, not
  a new fetch; `R33` independently confirms Shopify's own general guidance
  points the same direction — "Your code should stop making additional API
  requests until enough time has passed to retry. The recommended backoff
  time is one second" and "you could implement a request queue with an
  exponential backoff algorithm" (`R33`'s `SH-2`). *Scope:* **core engine**
  (the client/backoff mechanism; which queries to run is **domain**).

## Shopify pagination notes

- **[Fact]** Cursor pagination uses `edges`/`node`/`cursor`, with `pageInfo`
  exposing `startCursor`, `endCursor`, `hasNextPage`, `hasPreviousPage`;
  Shopify recommends querying `nodes` + `pageInfo` over `edges` unless
  edge-level cursor data is specifically needed (`S1`, `S2`, `S3`). Forward
  paging: pass the previous page's `endCursor` as the next request's `after`.
  Backward paging: pass the previous page's `startCursor` as `before`.
  Maximum page size is **250** resources per request (`S1`), corroborated by
  a Shopify staff community reply as applying uniformly across Shopify
  GraphQL APIs (`C1`, reference-only tier).
- **[Fact]** The general `api/usage/limits` page's "Pagination limits"
  section states a 25,000-object cap on paginating arrays (`S4`) — but a
  dedicated changelog entry (`S5`) **explicitly scopes this cap to the Liquid
  and Storefront GraphQL API only**, stating "The Admin GraphQL API continues
  to support higher limits for merchant facing workflows." *Why it matters:*
  this **corrects** an ambiguity the pre-006A baseline (`R24`) had logged as
  an open question ("The exact API-scoping... not stated"). A sync engine
  designed against the Admin API should not assume a 25,000-record ceiling
  per query/connection the way a Liquid-theme developer would. *Scope:*
  **core engine** (pagination-loop design), **domain-module-relevant**
  (large-catalog imports).
- **[Open question — independently corroborated by `R33`]** Neither `S1` nor
  `S2` states whether a saved GraphQL cursor remains valid if pagination is
  paused and resumed hours or days later (no documented expiry policy), nor
  whether ordering is stable if the underlying dataset mutates between page
  requests. `R33` (PR #126) independently searched for this and reached the
  identical conclusion: "No equivalent explicit statement was found for
  GraphQL `after` cursors specifically — their reuse-safety after a
  long-delayed resume is an Open question, not a documented guarantee either
  way" (`R33`'s Checkpoint/resume notes). This is now a **two-shard-
  corroborated open question**, not a single package's finding. *Why it
  matters:* directly affects whether "store `endCursor`, resume later" is a
  *safe* resumable-import design or merely a *technically possible* one —
  Shopify does not confirm either way for GraphQL. *Scope:* **core engine**
  design constraint; **domain-module** first-sync/reconciliation design
  consequence.
- **[Fact — new this revision, from `R33`]** For the **REST** Admin API
  (not GraphQL), Shopify explicitly documents that `page_info`/Link-header
  cursor URLs are **temporary**: "The link header URLs are temporary and we
  don't recommend saving them to use later. Use link header URLs only while
  working with the request that generated them" (`R33`'s `SH-16`, direct
  quote); a request using `page_info` also cannot combine with any parameter
  other than `limit`/`fields`. This package's own research is GraphQL/Admin-
  API-focused and had not independently checked the REST pagination page for
  this specific caveat. *Why it matters:* this is a documented, explicit
  "don't do this" for the REST cursor equivalent of the open question above
  — while no equivalent statement exists for GraphQL specifically, the REST
  precedent is a reasonable signal (not proof) that GraphQL cursors may
  carry a similar informal expectation. Treat as suggestive context, not a
  substitute for the still-open GraphQL question. *Scope:* **core engine**.

## Shopify bulk-operation notes

- **[Fact]** Bulk operations are the sanctioned mechanism for large-dataset
  extraction beyond normal cursor paging: async JSONL result files, nested
  child connections flattened onto separate lines with a `__parentId`
  back-reference, connection order and parent-before-child ordering
  preserved, download URL expires 7 days after completion (`S7`).
- **[Fact]** Bulk **query** operations: 10-day hard execution ceiling, then
  force-stopped and marked `FAILED`; recovery from a cancelled or timed-out
  operation is **resubmission as a brand-new operation** — Shopify's own
  wording is "submitting the query again" both for cancellation-recovery and
  timeout-recovery, with no partial-resume mechanism described anywhere
  (`S7`). Concurrency: 1 of each type per shop before API version 2026-01; up
  to 5 concurrent bulk **query** operations per shop from 2026-01 onward
  (`S7`).
- **[Fact]** Bulk **mutation** operations: 24-hour hard ceiling; per-line
  error handling — each JSONL row validated/executed independently, errors
  reported **in the same output file alongside successes**, categorized as
  JSON-parse / GraphQL-validation / execution / access-denied errors, each
  tagged with the failing input line number (`S8`). The bulk operation as a
  whole only reaches `FAILED` for a small set of **operation-level** system
  errors (`ACCESS_DENIED`, `INTERNAL_SERVER_ERROR`, `TIMEOUT` — `S11`); a
  large number of individual row failures does **not** fail the whole
  operation (`S8`).
- **[Fact]** `bulkOperationCancel` starts an **asynchronous** cancellation
  (`CANCELING` → `CANCELED`, a short undocumented delay); the reference page
  does not state whether repeat cancel calls on the same operation are safe
  (`S9`, `S10`). Whether `partialDataUrl` populates for a `CANCELED` (as
  opposed to `FAILED`) operation is **undocumented** — the field description
  ties it to "a failed operation" specifically (`S12`).
- **[Fact]** `@idempotent` **can** be used inside bulk mutations, but
  idempotency is scoped **per JSONL row**, not to the bulk operation as a
  whole — each row needs its own unique key; reusing one key across rows
  causes rows after the first to be treated as duplicates. Shopify explicitly
  endorses retrying an entire bulk mutation operation by resubmitting the
  same JSONL with the same per-row keys, and offers deterministic UUID v5
  generation so keys need not be persisted (`S8`, `S16`).
- **[Open question]** No official page states whether the `bulkOperationRunQuery`/
  `bulkOperationRunMutation` **start call itself** is safe to blindly retry
  on an ambiguous outcome (e.g. a network timeout after the start request
  left the connector, before a confirmed response) — only per-row mutation
  idempotency and post-failure query-resubmission guidance are addressed
  (`S7`, `S8`).
- **[Open question]** No official page explicitly recommends bulk operations
  only for large one-off exports and discourages them for routine/incremental
  sync; the framing found is purely efficiency-based ("bulk operations are a
  very efficient way to query data compared to standard pagination," `S7`).
  *Why it matters:* Mandatory Claim "Bulk operations may be useful for large
  imports but are not automatically MVP" is **this project's own
  design stance** (consistent with the accepted DEC-005 substrate, which does
  not adopt bulk operations as a Phase-1 mechanism), not a documented Shopify
  recommendation against routine use — the two should not be conflated.
  *Scope:* **domain-module** decision (first-sync product import is the
  concrete candidate), informed by **core-engine** resumability limits above.
- **[Fact — independently corroborated by `R33`]** `R33` (PR #126)
  independently researched this exact topic and reached the same
  not-resumable-at-the-API-level conclusion: "you can retry canceled bulk
  operations by submitting the query again," and a failed operation's
  documented remedy is likewise "these errors might be intermittent, so you
  can try submitting the query again" — with only a separate,
  one-week-expiring `partialDataUrl` recovering rows already produced before
  a failure (`R33`'s Checkpoint/resume notes, citing `SH-14`). This
  package's own `S7`/`S8` findings and `R33`'s independent findings converge
  exactly — cited here as two-shard corroboration, not a new fact. `R33`
  also demonstrates good adversarial-verification practice worth noting: an
  earlier draft of its own research attributed a specific SQL `WHERE`-clause
  string to a Shopify Engineering blog post about cursor mechanics, but two
  independent re-fetches found no such code block on the live page, and the
  unverifiable quote was removed rather than retained (`R33`'s "Unsupported
  claims removed" §Checkpoint/resume). No equivalent fabricated-quote issue
  was found in this package's own bulk-operations research.

## Shopify webhook delivery/retry/HMAC notes

- **[Fact]** Webhook delivery is explicitly **not guaranteed** — "Your app
  shouldn't rely on receiving data from Shopify webhooks... For redundancy,
  use reconciliation jobs to periodically fetch data from Shopify" (`S13`).
  Shopify does **not** guarantee delivery ordering, including the specific
  example "a `products/update` webhook might be delivered before a
  `products/create` webhook" (`S13`) — recommends sequencing by
  `X-Shopify-Triggered-At` header or the payload's `updated_at` field rather
  than arrival order.
- **[Fact]** HMAC verification: base64 HMAC-SHA256 of the **raw** request
  body in `X-Shopify-Hmac-SHA256`, computed from the app's client secret;
  applies to HTTPS delivery only (not Pub/Sub or EventBridge) (`S14`).
  Duplicate-delivery defense: primary recommendation is **idempotent
  processing**; `X-Shopify-Webhook-Id` dedup is offered as a fallback for
  non-idempotent handlers. Multiple subscriptions to the same topic each
  produce a separate delivery with its own `Webhook-Id` but a shared
  `X-Shopify-Event-Id` for correlating deliveries from one merchant action
  (`S14`).
- **[Fact]** Timeouts and retry schedule: 1-second connection / 5-second
  total timeout; any non-2xx (including 3xx) is an error; on failure, 8
  retries over the next 4 hours; after 8 consecutive failures an
  Admin-API-created subscription is auto-deleted and a warning email sent
  (`S14`).
- **[Open question]** The 8-retries/4-hours schedule bounds *failure-triggered*
  retries; Shopify does not separately quantify a maximum window for
  *success-path* duplicates (a delivery Shopify's own systems duplicate
  despite receiving a timely 200) — "Shopify minimizes duplicate deliveries,
  but your app might receive the same webhook more than once" (`S14`), with
  no stated upper bound. *Why it matters:* a webhook-dedup design cannot
  assume all duplicates fall inside a known time window; the dedup record
  must be durable, not merely a short-TTL cache. *Scope:* **core engine**.
- **[Fact]** The URL prior repo research cited as
  `.../webhooks/best-practices` now redirects to a consolidated "About
  webhooks" page (`S13`); this is a documentation-structure change worth
  recording so future sessions don't cite a dead path.

## Shopify idempotency notes

- **[Fact]** Idempotency keys are client-generated unique strings; Shopify
  tracks them for **24 hours from the original request** (reconfirmed
  unchanged this session, `S16`). Concurrent duplicate requests while the
  first is still processing return `IDEMPOTENCY_CONCURRENT_REQUEST` instead
  of being processed (`S16`) — the documented remedy is exponential backoff
  + retry with the *same* key. After the original succeeds, duplicates with
  the same key get the **cached response**, which the docs note "may not be
  the same as the original" if underlying data changed since (worked example
  given: `locationActivate`/`locationDeactivate`) (`S16`).
- **[Fact]** Two distinct idempotency mechanisms exist on Shopify's platform:
  (a) an **argument-style** idempotency key on specific mutations processing
  payments/subscriptions/revenue capture, and (b) a directive-style
  `@idempotent` on a fixed, per-mutation-declared list, mostly inventory and
  location mutations plus `refundCreate` (`S15`, `S16`). Most update/delete
  mutations are "idempotent by definition" and need no key at all; some
  (example given: `inventoryTransferSetItems`) are **not** naturally
  idempotent because of side effects beyond the main operation, and
  therefore require a key (`S15`).
- **[Open question / discrepancy — flagged, not resolved]** Prior repo
  research (`R8`, `R10`) — and the accepted DEC-009 decision record itself —
  states the `@idempotent` directive applies to "a fixed list of **17**
  mutations." This session's fresh fetch of the authoritative list (`S16`,
  self-dated by Shopify "last updated 2 February 2026") counts **16** named
  mutations: `inventoryActivate, inventoryAdjustQuantities,
  inventoryMoveQuantities, inventorySetOnHandQuantities,
  inventorySetQuantities, inventorySetScheduledChanges,
  inventoryShipmentAddItems, inventoryShipmentCreate,
  inventoryShipmentCreateInTransit, inventoryShipmentReceive,
  inventoryTransferCreate, inventoryTransferCreateAsReadyToShip,
  inventoryTransferDuplicate, inventoryTransferSetItems, locationActivate,
  locationDeactivate, refundCreate`. This is a genuine, unresolved numeric
  discrepancy — **not** silently reconciled here. Possible explanations
  (unverified): the list changed between whichever access date "17" was
  originally sourced from and 2026-07-08; a miscount in one of the two
  passes; or a mutation was added/removed by Shopify in the interim. *Why it
  matters:* DEC-009's error/retry taxonomy references this list only at the
  concept level (the ambiguous-outcome rule applies to "writes outside
  Shopify's `@idempotent` surface"), so the exact count does not invalidate
  DEC-009 — but a future domain-module implementation must re-count against
  the live page at build time per Shopify's own instruction on that page,
  not hard-code either "16" or "17." *Scope:* **domain-module** concern
  primarily (inventory/fulfillment mutations); **core-engine** concern only
  insofar as the engine's idempotency-layer design must treat "is this
  specific mutation `@idempotent`" as a per-call lookup, never a hard-coded
  assumption. Logged in full in the companion open-questions document.
- **[Fact]** For bulk mutations, `@idempotent` is scoped per JSONL row (see
  Bulk-operation notes above) — this is the same fact, cross-referenced here
  because it is simultaneously an idempotency-notes and bulk-operation-notes
  finding.
- **[Fact — cross-referenced from `R33`]** Shopify's `IDEMPOTENCY_CONCURRENT_REQUEST`
  behavior (above) is one specific vendor's answer to a question the
  broader idempotency-key literature does **not** answer uniformly. `R33`
  (PR #126) independently researched how a concurrent, still-in-flight
  duplicate request should be handled across vendors and found genuine
  disagreement: the IETF idempotency-key draft recommends HTTP 409 for this
  case, while Stripe's own documented behavior is to **not** cache a result
  for the conflicting concurrent request and tell the client to retry,
  because no endpoint has yet completed the execution that would produce a
  result to cache (`R33`'s Idempotency notes, citing `GEN-1`/`GEN-3`). Shopify's
  own `IDEMPOTENCY_CONCURRENT_REQUEST` response is a third documented shape
  (a distinct error code rather than either a 409 or silent non-caching).
  *Why it matters:* a sync engine's own idempotency-layer design (if it ever
  needs to define behavior for its own concurrent-duplicate case, as opposed
  to relying on Shopify's) should not assume any one vendor's shape is
  "the" standard — three platforms researched across this package and `R33`
  document three different shapes. *Scope:* **core engine**.
- **[Recommendation-candidate, cross-referenced from `R33`, not a decision]**
  `R33` independently offers a candidate idempotency-key composition for a
  *future* architecture review: scoping a key to (a) which two systems'
  records are involved, (b) which kind of operation is being performed, and
  (c) a caller-or-event-supplied unique token — explicitly noting Shopify's
  own `X-Shopify-Webhook-Id` as a candidate for component (c) (`R33`'s
  Idempotency notes). This is offered by `R33` only as candidate/inference
  material for later architecture review, not a decision, and is restated
  here only as a pointer — this package does not adopt, evaluate, or decide
  on it.

## Odoo scheduled-action notes

- **[Fact]** `ir.cron` is confirmed (again, source-level, this session) as
  the only background/deferred-execution primitive in Odoo 19 core; no
  general-purpose async job queue exists in the reviewed source or docs
  (`O7`, `O14`, `R25` baseline). `--max-cron-threads` defaults to 2 (`R25`,
  not re-verified this session, no contradicting evidence found).
- **[Fact]** Failure thresholds, confirmed at both doc and source level: 3
  consecutive errors/timeouts → skip current run, considered failed for that
  run (`CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`); 5 consecutive failures over
  **at least** 7 days → deactivate (`active=False`) and notify the DB admin
  (`MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5`,
  `MIN_DELTA_BEFORE_DEACTIVATION = timedelta(days=7)`, **both** conditions
  required simultaneously) (`O7`, `O14`).
- **[Fact — new this session]** `ir.cron`'s "notify the DB admin" step has
  **no actual delivery mechanism in base Odoo** — `_notify_admin()`'s base
  implementation is a bare `_logger.warning(message)` call, explicitly
  documented as "supposed to be overridden with some actual communication
  mechanism" (`O7`). *Why it matters:* a sync engine cannot assume an
  operator will actually be notified of a deactivated scheduled action unless
  something (Odoo.sh/Enterprise infrastructure, or the connector's own code)
  overrides this — it is a server-log line only, by default. *Scope:* **core
  engine** (observability design).
- **[Fact — new this session]** Odoo 19 introduced a formal **progress API**:
  `ir.cron.progress` (a persisted model with `remaining`, `done`,
  `timed_out_counter`, `deactivate` fields) plus
  `IrCron._commit_progress(processed, *, remaining=None, deactivate=False)`,
  which writes the progress record **and hard-commits the transaction**
  immediately, then returns the remaining time budget. A cron run's
  `CompletionStatus` (`FULLY_DONE`/`PARTIALLY_DONE`/`FAILED`) determines
  whether it is rescheduled at its normal interval, rescheduled ASAP, or
  routed toward the failure-count/deactivation logic above (`O7`). *Why it
  matters:* this is the accepted mechanism DEC-005 already names
  (`_commit_progress`) for batch-and-commit cron processing — confirmed here
  at the exact field/method level. *Scope:* **core engine**.
- **[Fact — new this session]** `ir.cron.progress` stores **no error
  message, exception, traceback, or failed-payload field** — only integer
  counters and a boolean. No documented or reviewed Odoo `ir.cron`
  dead-letter/redrive mechanism was found in the sources inspected — no
  "dead letter"/"DLQ" terminology appears anywhere in `ir_cron.py` or the
  official Scheduled Actions documentation section (`O7`, `O14`, verified by
  full-text search of the files actually reviewed, not a whole-codebase
  claim). What Odoo's failure handling *does* provide, within the sources
  inspected, is: failure counters + eventual deactivation + a log-only
  notification — no persisted record of what failed or why, and no
  redrive/replay mechanism was found in what was reviewed. *Why it matters:*
  directly informs Mandatory Claim "Permanent failure/dead-letter must be
  visible" — the connector must not rely on `ir.cron` for permanent-failure
  visibility; a sync engine wanting a dead-letter surface must build it
  itself (this repo's own `shopify.connector.job`/`.job.log`
  `failed_final`/`blocked_manual_review` states plus the audit log **already
  are** that self-built surface — see "Existing job/log substrate
  implications" below). *Scope:* **core engine**.
- **[Fact — new this session]** Official guidance for writing cron functions
  (`O13`) shows a worked example using `record.try_lock_for_update()` inside
  a batch loop ("lock record (also checks existence)... prefetch: break
  prefetch... filtered_domain: record may have changed"), and an exception
  pattern that rolls back the cursor **first**, before logging, with a
  comment explicitly calling this the "default strategy." *Scope:* **core
  engine**.

## Odoo transaction/error/rollback notes

- **[Fact]** The Odoo framework — not application code — owns the
  transactional context of every RPC call: "a new database cursor is opened
  at the beginning of each RPC call, and committed when the call has
  returned... If any error occurs during the execution of the RPC call, the
  transaction is rolled back atomically" (`O8`). The same dedicated-per-call
  transaction pattern applies to **tests and scheduled actions** (`O8`).
  Application code must **never** call `cr.commit()`/`cr.rollback()` itself
  unless it opened its own cursor (`O8`).
- **[Fact — new this session, source-level confirmation]** The mechanism
  behind this is `odoo.service.model.retrying()` — a function that "call[s]
  `func` in a loop until the SQL transaction commits with no serialisation
  error," rolling back and retrying (random exponential backoff,
  `random.uniform(0.0, 2**i)`) up to `MAX_TRIES_ON_CONCURRENCY_FAILURE = 5`
  times for exactly three PostgreSQL error classes
  (`LOCK_NOT_AVAILABLE`/`SERIALIZATION_FAILURE`/`DEADLOCK_DETECTED`); on
  success it commits (`env.cr.commit()`); on any other/final exception it
  resets transaction/registry state and **re-raises** (never swallows)
  (`O5`). This same `retrying()` wrapper governs both XML-RPC/JSON-RPC
  dispatch (`O5`) and HTTP controller dispatch (`O6`). *Why it matters:*
  confirms, at the source level, both that an uncaught exception rolls back
  the whole in-flight transaction, and that Odoo *already* has a bounded,
  jittered, automatic retry mechanism for concurrency conflicts specifically
  — which the sync engine's own retry design should be aware of (and not
  duplicate at the RPC layer). **Whether this mechanism extends to a cron
  job's own record-processing code is a separate, source-backed inference,
  not a settled fact** — see "Odoo concurrency/locking notes" below for the
  full framing (now corroborated by three independent shards: this package,
  `R31`, and `R33`). *Scope:* **core engine**.
- **[Fact — new this session, source-level confirmation]** `ir.cron`'s own
  `_callback()` method independently implements the identical
  commit-on-success / rollback-and-reraise-on-exception pattern
  (`self.env.cr.commit()` on success; `except Exception:
  self.pool.reset_changes(); self.env.cr.rollback(); raise` on failure)
  (`O7`). Because `_commit_progress()` performs its own hard commit mid-run,
  work committed before an exception is durably persisted; only work since
  the last commit point is rolled back (`O7`, this session's synthesis of
  two source blocks, marked **[Inference]** in the raw research but treated
  here as a well-grounded reading of the two quoted code blocks).
- **[Fact — new this session, independently corroborated by `R31`]** Odoo's
  official coding guidelines warn that PostgreSQL performance degrades when
  a transaction uses more than 64 savepoints: *"After you start more than 64
  savepoints during a single transaction, PostgreSQL will slow down. In all
  cases, if the server runs replicas, savepoints have a huge overhead. If
  you process records and savepoint in a loop... limit the size of the
  batch. If you have more records, the function should maybe become a
  scheduled job or you have to accept the performance penalty"* (`O8`,
  direct quote; `R31` independently fetched and quotes the same passage).
  **This is a performance constraint to design against, not a hard
  functional cap** — nothing enforces it at the code level, and `R31`
  additionally found that core `create()`/`write()` do **not** wrap
  themselves in a savepoint by default: savepoints are used **selectively**
  by higher-level code (e.g. `Model.load()`'s per-record retry-on-batch-
  failure) and in business-logic `try`/`except` blocks across addons, not as
  an automatic per-record mechanism. *Why it matters:* future
  per-record-savepoint loops (as DEC-005's "per-record isolation
  (savepoints)" language contemplates) must treat this as a batch-sizing
  input to weigh, not an automatic ceiling the framework itself enforces —
  no prior repo research had surfaced this warning before this session and
  `R31`. *Scope:* **core engine** (the batch-size / savepoint-per-item
  cron-loop design).
- **[Fact]** `TransactionCase` runs all test methods in one shared
  transaction, but **each test method in its own savepoint sub-transaction**,
  with the cursor always closed without committing; the source additionally
  **actively forbids** calling `commit()`/`rollback()`/`close()` from inside
  a test (monkey-patched to raise, "Cannot commit or rollback a cursor from
  inside a test... Please rollback to a specific savepoint instead") (`O2`,
  `O3`). *Scope:* **core engine** (testing strategy, Analysis Area K).

## Odoo concurrency/locking notes (source-backed)

- **[Fact — genuine gap this session fills]** Odoo deliberately chose
  **`REPEATABLE READ`** (PostgreSQL snapshot isolation) as the default cursor
  isolation level, **not** `SERIALIZABLE` — by explicit design, because
  "OpenERP implements its own level of locking protection for transactions
  that are highly likely to provoke concurrent updates... we don't really
  need additional heuristics to trigger transaction rollbacks, as we are
  taking care of triggering instant rollbacks ourselves when it matters"
  (`O4`, direct quote from the `Cursor` class docstring). *Why it matters:* a
  sync engine cannot rely on PostgreSQL's own `SERIALIZABLE`-level conflict
  detection to catch every race; Odoo's own philosophy is that
  concurrency-sensitive code must **explicitly** lock (see below), not
  assume the database will catch it. *Scope:* **core engine**.
- **[Fact]** Odoo's ORM exposes an explicit row-locking primitive:
  `BaseModel.lock_for_update()` (raises `LockError` if any target row can't
  be locked) and a non-raising variant `try_lock_for_update()` (silently
  drops rows it couldn't lock). Both use PostgreSQL `FOR UPDATE SKIP LOCKED`
  (or `FOR NO KEY UPDATE SKIP LOCKED` with `allow_referencing=True`),
  deliberately choosing `SKIP LOCKED` over `NOWAIT` "because the later
  aborts the transaction and we do not want to use SAVEPOINTS" (`O9`, direct
  quote). Both methods are decorated `@api.private` — **not callable over
  external RPC** (`O9`, `O12`); a purpose-built server-side method would be
  needed for an external caller to use them. *Why it matters:* this is the
  primary answer to Analysis Area C's "what could create-time/execution-time
  checks mean" — Odoo already has the primitive DEC-005's per-record
  isolation could build on for record-level locking, distinct from (and
  complementary to) the DB-backed `operation_scope_key` unique-constraint
  guard already implemented (`R1`). *Scope:* **core engine**.
- **[Fact]** `ir.cron` itself uses this exact SKIP LOCKED pattern for
  **job-queue acquisition** — concurrent cron workers acquire jobs via `FOR
  NO KEY UPDATE SKIP LOCKED` on the `ir_cron` row, explicitly chosen over the
  stronger plain `UPDATE` lock "so [it] doesn't conflict with implicit KEY
  SHARE locks taken by foreign-key references to cron jobs" (`O7`). If job
  acquisition itself races into a PostgreSQL `SerializationFailure`, Odoo's
  own guidance and the actual `_process_jobs_loop()` code **roll back and
  move on to other jobs** rather than retrying that specific job acquisition
  in a loop (`O7`, direct quote of both the docstring and the `except
  psycopg2.extensions.TransactionRollbackError: ... continue` code).
- **[Inference, source-backed — relabeled this revision, was previously
  overstated as a "Fact — important negative finding"]** Source-level review
  indicates this as a synthesis/inference, not a directly-quoted
  single-source conclusion: Odoo's RPC-layer `retrying()` behavior is
  source-confirmed for RPC/HTTP dispatch (`O5`, `O6`), while the reviewed
  `ir.cron` job-processing path did not show an equivalent automatic retry
  around each domain record-processing step — `_callback()` (the method that
  actually runs a cron's server action) does not call `retrying()` and has
  no special handling for serialization/deadlock error codes in the code
  reviewed, only a generic rollback-and-reraise on any exception (`O7`,
  confirmed by grep: the string `retrying` does not occur anywhere in
  `ir_cron.py`). `R31` (PR #124) independently examined a related but
  **distinct** layer — `ir.cron`'s own job-*acquisition* query
  (`_acquire_one_job`, `FOR NO KEY UPDATE SKIP LOCKED`) and its
  `SerializationFailure`-triggers-rollback-and-continue behavior in
  `_process_jobs_loop` — which corroborates that job *acquisition* is
  conflict-aware, but does not itself examine whether a domain record write
  *inside* a cron job's own business logic gets equivalent protection. **This
  remains a source-backed inference requiring runtime proof before
  implementation relies on it**, not a settled fact: if the connector's own
  scheduled-action code needs conflict-safety on the business records it
  writes, explicitly calling `lock_for_update()`/`try_lock_for_update()`
  and/or implementing its own catch-rollback-retry logic is a plausible
  design response to this inference, not a confirmed requirement. *Scope:*
  **core engine**.
- **[Fact]** `LockError` (raised by `lock_for_update()`) is a `UserError`
  subclass mapped to HTTP 409; the lower-level `ConcurrencyError`'s own
  docstring explicitly cross-references `retrying()` as "the intended
  remediation" (`O11`). *Scope:* **core engine**.
- **[Fact]** A real in-core example of raw (non-ORM-helper) row locking
  exists: `ir.sequence._update_nogap()` issues `SELECT ... FOR UPDATE
  NOWAIT` directly via `cr.execute()` for strictly no-gap sequence
  generation — a hard-fail-on-conflict idiom, contrasted with the
  skip-and-continue idiom of `lock_for_update()` (`O10`). Two distinct
  locking idioms coexist in Odoo 19 core.
- **[Open question]** No formal ORM API reference page documents
  `lock_for_update()`/`try_lock_for_update()` at all — a direct string search
  of the official ORM reference page found zero matches; the only official
  documentation location demonstrating the primitive is the "Writing cron
  functions" guide (`O13` vs `O1`, confirmed absence). *Why it matters: a*
  future implementer must know to look at the cron-writing guide, not the
  general ORM reference, to find this primitive documented at all.
- **[Open question — now corroborated by three independent shards]** Whether
  Odoo 19's `FOR NO KEY UPDATE SKIP LOCKED` cron-acquisition mechanism
  *actually* prevents duplicate execution under a real multi-worker,
  multi-process, or multi-server (load-balanced) deployment has, in every
  research pass performed on this topic, been confirmed only by **reading
  source and documentation comments** — never by an observed concurrency
  test. This package's own research (above) and `R31` (PR #124) both reached
  this conclusion independently; `R33` (PR #126) now makes it a **third**
  independent shard reaching the identical conclusion, and states it more
  starkly: "it has not been observed running, and would need an actual
  concurrency test (fire the same cron from two processes/threads
  simultaneously and confirm exactly one executes) to verify the documented
  intent matches real runtime behavior" (`R33`'s Duplicate-running
  prevention notes). `R33` also names a **more specific** open question this
  package had not previously surfaced: whether the row-lock-only approach is
  sufficient with **no additional cross-server coordination** when multiple
  Odoo application servers share one PostgreSQL database — flagged by `R33`
  as a real operational pain point worth an explicit runtime test, citing a
  historical GitHub issue about load-balanced cron scheduling as
  circumstantial (not conclusive) evidence this has been a problem in
  practice elsewhere. *Scope:* **core engine**. Restated in full in the
  companion open-questions and risk-register documents.
- **[Fact — new this revision, from `R33`, genuine gap this package had not
  researched]** PostgreSQL's own advisory-lock mechanism (`pg_advisory_lock`
  and related functions) is a documented alternative/complementary locking
  primitive this package had not previously examined. Two caveats `R33`
  surfaces are directly relevant to any future connector-level locking
  design: (a) calling an advisory-lock function inside a `SELECT ... ORDER
  BY ... LIMIT` query can lock rows **before** the `LIMIT` is applied,
  leaving "dangling" locks the application never intended to acquire, held
  until session end — PostgreSQL's own documentation frames this as a
  "danger!" worked example (`R33`'s Duplicate-running prevention notes,
  citing `GEN-30`); (b) **session-scoped** advisory locks are **not**
  released by a transaction rollback and persist "until explicitly released
  or the session ends" — a design reusing pooled DB connections across
  unrelated units of work would need an explicit release step or the
  transaction-scoped variant (`pg_advisory_xact_lock`) to avoid a lock
  surviving past its intended scope (`R33`, same source). *Why it matters:*
  advisory locks are a plausible alternative to row-level `SKIP LOCKED`
  locking for a future job-claiming design, but carry their own,
  non-obvious hazards not present in the `lock_for_update()`/`ir.cron`
  pattern already documented above — worth weighing at the future
  architecture gate, not decided here. *Scope:* **core engine**.
- **[Cross-reference, from `R33`]** Odoo's job-acquisition deadlock
  avoidance (above) is one instance of a general pattern: election/
  acquisition mechanisms are not automatically proof of a hard
  mutual-exclusion guarantee. `R33` cites Kubernetes' own `client-go`
  leader-election package as a structurally similar admission for a
  different mechanism: "This implementation does not guarantee that only
  one client is acting as a leader (a.k.a. fencing)" (`R33`'s Duplicate-
  running prevention notes, citing `GEN-34`, contrasted with `etcd`'s
  documented single-leader guarantee, `GEN-35`). Offered as corroborating
  context for treating Odoo's own locking claims with the same "verify, don't
  assume" discipline, not as a claim about Odoo's mechanism specifically.

## Existing Task 005 state-gating implications

- **[Fact]** Business-job enqueue-time gating (`create()`) and
  execution-time gating (`write()` to `running`) are **already implemented
  and live-validated** (`R1`, `R3`, `R18`) — restricted to
  `BUSINESS_JOB_SOURCES = ('webhook', 'manual_sync', 'scheduled_sync',
  'reconciliation', 'odoo_event')`; core diagnostic sources
  (`setup_readiness_check`, `export_preview_dry_run`) are exempt by design
  (gating them on `connected` would be circular, since they exist to
  determine connection/readiness state). Any future sync engine's job
  creation/execution paths **must** route through this existing gate, not
  reimplement or bypass it. *Scope:* **core engine**.
- **[Fact]** `action_disconnect()` already cancels every non-terminal
  business job for a store on disconnect (`state='cancelled'`,
  `cancel_reason='Store disconnected.'`, `finished_at` stamped, one
  `state_change` log row per cancelled job via `_system_append`), leaving
  core/diagnostic and already-terminal jobs untouched, and is idempotent (a
  second call finds nothing to cancel and records an audited no-op) (`R3`).
  *Why it matters:* directly and fully answers Analysis Area I's "what
  happens if a store disconnects while jobs are queued/running" — the answer
  already exists in merged code, live-validated (`R18`), not a hypothetical
  a sync-engine design needs to invent. *Scope:* **core engine**.
- **[Open question — not addressed by existing gating]** The existing
  cancellation sweep runs **synchronously inside `action_disconnect()`**, at
  the moment of disconnect. It does not address the narrower race of a job
  that is *already mid-execution* (state `running`) inside an `ir.cron`
  batch at the exact instant `action_disconnect()` runs — `write()`'s
  execution-time gate only blocks a transition *into* `running`, it does not
  interrupt a job already past that check. Whether this narrow window is a
  real, exploitable race, or is closed in practice by savepoint/transaction
  boundaries, is **not** proven by any source in this package — it would
  require live Odoo-runtime evidence (per-record savepoint timing under
  concurrent cron workers) to resolve. Logged in the companion open-questions
  document, not resolved here. *Scope:* **core engine**.

## Existing job/log substrate implications

- **[Fact — corrected wording this revision]** The existing Tasks 001–005
  substrate already provides implemented **primitives** for several
  mandatory sync-engine claims — the job/log split (`R1`, `R2`) gives
  "duplicate-running prevention is mandatory" → `operation_scope_key` unique
  constraint; "logs must be inspectable" → append-only `job.log` rows with
  `event_type` (`attempt`/`state_change`/`verification_read`/`manual_action`/
  `note`); "secrets must never be logged" → redaction at the single write
  path — **but this does not mean the full sync-engine requirements are
  complete.** `R31` (PR #124)'s "Current gaps" section independently and
  more thoroughly confirms this same boundary by direct code inspection:
  actual sync **operation execution** (`job.job_type` has exactly three
  values, all core/diagnostic — no domain job type exists), **retry
  scheduling** (no `ir.cron` reference exists anywhere under `addons/`),
  **checkpoint/resume** (`operation_scope_key` is a single-active-operation
  lock, not a pagination cursor or resume token), **domain deduplication**
  (the binding mixin is shape-only, no concrete binding table exists), and
  **handler dispatch** (no domain-neutral operation registry exists,
  distinct from the readiness-check pattern) **all remain unbuilt**. A sync
  engine built on top of this substrate inherits the primitives listed above
  **if and only if** it uses the existing
  `Job.create()`/`.write()`/`JobLog._system_append()` paths and does not
  invent a parallel path. *Scope:* **core engine**.
- **[Fact]** `payload_hash` currently serves a dual role — a hash of the
  normalized outbound payload for target-bearing domain jobs, and a per-run
  UUID4 nonce for target-less core job types (`core_test_connection`,
  `core_readiness_check`, `core_manual_maintenance`) so repeat runs don't
  collide on the `(store_id, idempotency_key)` unique constraint (`R1`,
  comment in source). *Why it matters:* this is an accepted but
  self-acknowledged "naming/schema overload" (per TD-001's own resolution
  note) that a future domain job type must be aware of when computing its
  own `payload_hash` semantics — it is not simply "a payload hash" in every
  case. *Scope:* **core engine**.

## OCA `queue_job` / reference-pattern notes

RA-004 (`R21`) already rejects OCA `queue_job` as the Phase 1 **default**
substrate; this section documents it purely as read-and-cited reference
material, per the task's explicit instruction — nothing here argues for
adoption.

- **[Fact]** `queue_job`'s job state machine has 7 states
  (`wait_dependencies/pending/enqueued/started/done/cancelled/failed`),
  versus this repo's already-accepted 10-state machine (`R1`) — the two are
  not directly comparable one-to-one; `queue_job` has no analog to
  `retry_waiting` vs `failed_retryable` as *distinct* states (its single
  `failed` state covers both "will auto-retry later" and "exhausted,"
  differentiated only by whether `retry < max_retries` internally) (`Q3`).
- **[Fact]** `queue_job` retries by **exception type**: raising
  `RetryableJobError` signals "retry me" (with optional per-raise `seconds`/
  `ignore_retry` overrides); any other exception (including its own
  `FailedJobError`, raised automatically once `max_retries` — default 5, 0 =
  infinite — is exhausted) is terminal (`Q3`, `Q7`, `Q8`). A **retry
  pattern** (`{retry_count: postpone_seconds}`) can be configured per job
  function; default with no pattern is a flat 10-minute delay (`Q2`).
  PostgreSQL concurrency errors are automatically converted into
  `RetryableJobError` with a short fixed delay (`Q7`) — i.e. `queue_job`
  *does* fold DB-serialization conflicts into its generic retry machinery,
  where core Odoo's own `ir.cron` (`O7`) explicitly does not for a cron's
  own record-processing code. *Why it matters (reference only):* this is a
  concrete existence proof that a job engine *can* auto-convert DB
  concurrency errors into its own retry vocabulary — useful context for
  Analysis Area D, not an endorsement to adopt `queue_job`'s exact mechanism.
- **[Fact]** `identity_key` (queue_job's idempotency/dedup mechanism) is
  content-derived by default (SHA1 of model+method+sorted-ids+args+sorted-
  kwargs, `Q3`) and its dedup check **only matches jobs currently in
  `wait_dependencies`/`pending`/`enqueued`** — explicitly **not**
  `started`/`done`/`cancelled`/`failed` (`Q3`, direct quote of the search
  domain). *Why it matters:* this is a narrower guarantee than it sounds —
  `identity_key` only prevents *piling up redundant queued* work, it does
  **not** prevent re-creating a job with the same key once a prior one has
  started, finished, or failed. `queue_job`'s own README compensates by
  mandating the job *body* itself be idempotent (`Q2`) — i.e. `queue_job`
  relies on the same two-layer strategy (a narrow-window dedup key + a
  broader idempotent-body requirement) this repo's own accepted design
  already uses (`idempotency_key` for the life of the job vs.
  `operation_scope_key` for the non-terminal serialization window, `R11`
  §8). This is a genuine point of structural convergence between an
  independently-designed reference system and this repo's own accepted
  schema — worth noting as corroboration, not as a reason to change
  anything.
- **[Fact]** `queue_job` surfaces failures via Odoo's generic `needaction`
  mechanism and `mail.thread` chatter (auto-subscribing users in a "Queue Job
  Manager" group), rather than a bespoke dashboard (`Q4`). Failed (or
  done/cancelled) jobs can be manually **requeued** by a human, resetting
  state to `pending` (`Q4`). Old done/cancelled jobs are periodically purged
  by a cron-driven autovacuum keyed off a per-channel `removal_interval`
  (`Q4`).
- **[Fact]** "Channels" are a capacity-limited execution lane concept; the
  DB-side `queue.job.channel` model stores only the segregation hierarchy and
  a data-retention interval — **no capacity field** — actual concurrency
  numbers (e.g. `root:4`) are supplied purely as jobrunner **runtime**
  configuration (env var or config file), not an editable business record
  (`Q5`). *Why it matters (reference only):* if a future core-engine design
  ever wants a "don't run more than N of this job type at once" concept, the
  channel *idea* (declarative lane name + external capacity config) is a
  cleaner separation-of-concerns than baking a concurrency limit into the job
  record itself — offered as a pattern to be aware of, not a proposal.
- **[Fact]** `identity_key` dedup at *graph*-delay time is documented by the
  module's own authors as an acknowledged rough edge: it is all-or-nothing
  across the whole dependency graph being delayed, with the authors'
  in-source comment "Maybe we should check that the found jobs are part of
  the same graph, but not sure it's really required..." (`Q6`, direct quote).
  *Why it matters (reference only):* a caution against assuming any
  dependency-graph dedup design is automatically correct just because it
  exists in a mature module — even `queue_job`'s own maintainers flag this
  as unresolved.

**Wording alignment against `R33`.** `R33` (PR #126) independently researched
OCA `queue_job` via a separate 18.0-branch source read (`OCA-1`–`OCA-10`,
this package's own `Q1`–`Q8` read the 19.0 branch directly). Points of
agreement, corroboration, and one unreconciled discrepancy:

- **Reference-only posture**: identical — `R33` explicitly frames its entire
  OCA section as "reference pattern only," reaffirms RA-004/DEC-005, and
  states it "does not recommend installing, depending on, or adopting
  `queue_job`" (`R33`'s OCA queue_job notes). No conflict.
- **Retry constants**: `R33` independently confirms `DEFAULT_MAX_RETRIES = 5`
  and `RETRY_INTERVAL = 10 * 60` (600 seconds) (`R33`'s `OCA-6`) — an exact
  match to this package's own `Q2`/`Q3` findings. Corroboration.
- **`identity_key` non-terminal-only dedup scope**: `R33` independently
  confirms the identical narrow-window finding — the dedup check "only
  searches for existing jobs whose state is `in [wait_dependencies, pending,
  enqueued]` — **not** `started`" (`R33`'s Idempotency notes, citing
  `OCA-6`) — an exact match to this package's own `Q3` finding. Corroboration.
- **`FailedJobError` docstring vs. inference**: `R33` explicitly separates
  the verbatim docstring ("A job had an error having to be resolved.") from
  its own interpretive gloss ("terminal failure needing manual
  intervention"), flagging the blend as a defect its own adversarial-
  verification pass caught and fixed (`R33`'s OCA queue_job notes,
  "Corrected on verification"). This package's own `Q3`/`Q8` treatment
  already kept the two separate; no correction needed here, but `R33`'s
  explicit self-correction is a useful demonstration of the same discipline.
- **Discrepancy, not resolved**: `R33` states the standard Jobrunner requires
  "multiple workers (`--workers > 1`)" (`R33`'s OCA queue_job notes, citing
  `OCA-4`); this package's pre-006A baseline (`R25`) cites `--workers > 0`
  for the same requirement. Neither shard resolves this — recorded as an
  open, unreconciled discrepancy between two independently-produced source
  passes (see the source inventory's "Version / API caveats" §9). Immaterial
  to RA-004 either way.

## Engineering pattern notes

Cited only where Shopify/Odoo official docs are silent, per `CLAUDE.md`
§7.6 and this task's explicit instruction not to treat these as
authoritative for Shopify/Odoo facts.

- **[Inference, grounded in `E2`/`E3`]** Retries compound multiplicatively
  across a call stack — a worked AWS example shows a 5-layer stack with 3
  retries per layer amplifying load on the deepest dependency **243x**
  under failure (`E2`); Google's SRE book gives an independent worked
  example of retried QPS compounding turn-over-turn (100→200→300 QPS)
  (`E3`). **`R33` (PR #126) independently cites the same Google SRE chapter
  with a different worked example** — "if the database can't service
  requests because it's overloaded, and the backend, frontend, and
  JavaScript layers all issue 3 retries (4 attempts), then a single user
  action may create 64 attempts (4³) on the database" (`R33`'s Retry and
  backoff notes, citing `GEN-10`) — a different passage from the same
  source, not a conflict with this package's own `E3` citation; both
  illustrate the identical multiplicative-amplification principle with
  different numbers. `R33` also independently confirms AWS Well-Architected
  rates the risk of unbounded/uncoordinated retries as explicitly **"High"**
  and separately names "retrying at multiple layers... in a manner which
  compounds retry attempts" as a documented anti-pattern (`R33`, citing
  `GEN-15`). *Why it matters:* a sync engine that retries at multiple levels
  (e.g. the GraphQL client retries a request, *and* the cron batch loop
  retries the whole batch, *and* an operator manually retries the same job)
  risks exactly this amplification against Shopify's own rate limits. All
  sources recommend **concentrating retry logic at one layer** and bounding
  it with either a fixed per-request cap or a shared retry budget (`E2`,
  `E3`, `R33`). *Scope:* **core engine**.
- **[Inference, grounded in `E2`/`E3`]** Non-jittered backoff is undermined
  by correlation — "If all the failed calls back off to the same time, they
  cause contention or overload again when they are retried" (`E2`, direct
  quote) — jitter (randomizing the backoff delay) exists specifically to
  break this correlation. Google SRE guidance: "Always use randomized
  exponential backoff when scheduling retries" (`E3`, direct quote). **`R33`
  adds a specific, corrected formula this package did not previously have**:
  the canonical AWS Architecture Blog "Equal Jitter" formula is `temp =
  min(cap, base * 2^attempt); sleep = temp/2 + random(0, temp/2)` — `R33`'s
  own adversarial-verification pass explicitly flags that an earlier draft
  of its own research recorded an inaccurate formula for this and corrected
  it after two independent re-fetches (`R33`'s Retry and backoff notes,
  citing `GEN-8`); Equal Jitter is documented as strictly worse than Full
  Jitter ("the loser... doing slightly more work... and tak[ing] much
  longer"), not merely "similar" as an earlier draft of `R33`'s own research
  had it. *Why it matters:* the already-accepted planning-default retry
  schedule (`R11` §9: 30s base, ×2 multiplier, capped at 30 min, **±20%
  jitter**) already incorporates jitter — this engineering-reference
  research (this package's own `E2`/`E3`, independently corroborated and
  extended by `R33`) **corroborates** that design choice as consistent with
  recognized practice; the exact jitter *formula* the planning default uses
  (a fixed ±20% band, not Full/Equal/Decorrelated Jitter specifically) is a
  distinct implementation-planning detail neither this package nor `R33`
  decides. *Scope:* **core engine**.
- **[Inference, grounded in `E2`]** "APIs with side effects aren't safe to
  retry unless they provide idempotency" (`E2`, direct quote) —
  general-practice restatement of exactly the principle DEC-009's
  ambiguous-outcome rule already encodes for non-`@idempotent` Shopify
  writes (`R8`). Corroboration, not a new requirement.
- **[Inference, grounded in `E1`]** Stripe's own idempotency-key design
  guidance (client-generated UUID v4 or high-entropy random string; never
  embed PII/sensitive data in the key itself; cache the *first* response,
  including error responses, and replay it verbatim on key reuse) (`E1`) is
  a close structural match to Shopify's own documented idempotency-key
  mechanics (`S16`) — cited here only as confirmation this is a converged
  industry pattern, not as a Stripe-specific requirement on this connector.
  *Scope:* **domain-module** (if/when the connector ever generates its own
  idempotency keys for Shopify `@idempotent` calls — already anticipated by
  the existing `idempotency_key` field, `R1`).
- **[Inference, grounded in `E4`, substantially deepened by `R33`]** A
  dead-letter queue's *purpose* — isolate messages/jobs that failed
  processing into a separate, inspectable holding area rather than silently
  dropping or endlessly retrying them, with routing typically keyed to
  "received/attempted N times without success" (`E4`) — is structurally
  identical to what `blocked_manual_review` and `failed_final` already do in
  this repo's accepted job state machine (`R1`). `R33` (PR #126) researched
  this exact topic far more deeply (SQS, Azure Service Bus, RabbitMQ, EIP —
  `GEN-18` through `GEN-29`) and surfaces two nuances this package's own
  lighter `E4` pass did not carry: **(a) visibility is everywhere an opt-in,
  separately-wired alarm/metric, not a default push notification** — "Set up
  a CloudWatch alarm to monitor messages in a dead-letter queue using the
  `ApproximateNumberOfMessagesVisible` metric... [o]nly then can you poll the
  queue to review and retrieve them," with an equivalent named
  `DeadletteredMessages` metric in Azure Monitor (`R33`'s Dead-letter notes,
  citing `GEN-19`/`GEN-25`) — "a bare DLQ with no alarm/monitor wired up
  therefore provides no visibility guarantee by itself" (`R33`, its own
  inference); **(b) dead-lettering is not exclusively a multi-attempt
  phenomenon** — AWS's own SQS docs note "if the `maxReceiveCount` is set to
  a low value such as 1, one failure to receive a message would cause the
  message to move to the dead-letter queue," and RabbitMQ dead-letters on a
  single negative acknowledgment as one of its documented triggers (`R33`,
  citing `GEN-18`/`GEN-27`). *Why it matters:* this package's own Mandatory
  Claim 9 evidence ("Permanent failure/dead-letter must be visible") already
  concluded Odoo core provides no ready-made dead-letter surface and this
  repo's own job states fill that gap — `R33`'s finding (a) sharpens that
  conclusion: *visibility* is a separate design concern from *state
  capture*, and this repo's job/log substrate captures state but has not yet
  been evaluated (out of scope for this research-only package) against
  whether an alarm/dashboard is wired to it. *Scope:* **core engine**.
- **[Inference, grounded in `E6`/`E7`, independently deepened by `R33`]** The
  general checkpoint/resume pattern for long-running jobs — periodically
  persist progress externally, resume from last-saved state on restart,
  design for idempotent re-processing of the last (possibly-repeated) unit
  of work (`E6`, `E7`) — maps cleanly onto Shopify's own `endCursor`-based
  pagination (`S1`) *if* the sync engine persists the last-seen cursor as
  part of a job's own state. Neither Shopify nor Odoo officially documents
  this combination (cursor-as-checkpoint) as a named pattern — it is this
  session's own synthesis of two independently-documented mechanisms
  (Shopify's cursor API + the general checkpoint pattern), not a source's
  own claim. `R33` (PR #126) independently researched general
  checkpoint/resume patterns via a different, deeper source set (AWS
  Glue workflow-resume, AWS Step Functions redrive, Azure Data Factory
  rerun) and surfaces a sharper framing of the same underlying risk this
  package's synthesis gestures at: **double-processing** an
  already-committed record (if the mutating side effect commits before the
  checkpoint/cursor is persisted, a crash between the two causes
  reprocessing on resume) versus **silently skipping** a record (if the
  checkpoint advances before the mutation is durably committed, a crash
  after the checkpoint-advance but before the commit causes that record to
  be missed on resume) (`R33`'s Checkpoint/resume notes, citing `GEN-36`,
  `GEN-37`). *Scope:* **core engine** (if the engine owns checkpoint
  persistence) or **domain-module** (if each domain's import job owns its
  own cursor state) — **genuinely undecided**, logged as an open question.
- **[Inference, grounded in `E9`, independently deepened by `R33`]** OWASP's
  canonical "never log" list (access tokens, session identifiers, passwords,
  connection strings, encryption keys, payment-card data, sensitive PII)
  (`E9`) matches, at the category level, what this repo's existing
  `redact()`-at-write-path design already guards against for job logs
  (`R2`). `R33` (PR #126) independently researched observability/redaction
  via a substantially larger source set (OWASP Top 10 A09 2021/2025, OWASP
  Secrets Management Cheat Sheet, MITRE CWE-532, NIST SP 800-122, GDPR
  Art. 5, the Twelve-Factor App) and surfaces two facts directly relevant to
  this project's own two platforms that this package's lighter `E9` pass did
  not carry: Shopify's own docs recommend regular client-credential
  rotation, citing "employees leave, client credentials can be accidentally
  committed to version control" (`R33`'s Observability/redaction notes,
  citing `SH-18`); and Odoo's own 19.0 developer documentation states an API
  key "should [be] store[d]... as carefully as the password as they
  essentially provide the same access to your user account" (`R33`, citing
  `OD-10` — `R33` itself flags this exact sentence as needing a citation
  correction during its own adversarial-verification pass, tracing it to the
  "External RPC API" page rather than the page an earlier draft attributed
  it to). *Why it matters:* both platforms this connector integrates with
  independently treat their own credentials as password-equivalent in their
  own official documentation — directly relevant to `store_credential.py`'s
  `access_token` field (`R5`), which this repo's own docstrings already
  treat the same way. No gap found against the existing `redact()` design;
  corroboration
  only. *Scope:* **core engine**.

## Competitor/common-pattern notes (externally sourced only)

Per the research hierarchy, competitor evidence is used only for externally
visible behavior, drawn entirely from **existing repo research** (`R27`–`R30`)
— no fresh competitor fetch was performed this session (not requested, and the
existing competitor corpus already covers sync/queue/retry patterns
specifically).

- **[Competitor claim]** TeqStars and Emipro both run a cron-processed
  per-operation queue (batch limits, per-object isolation, incremental
  cursors) without OCA `queue_job`; VentorTech runs on OCA `queue_job` with
  documented install friction (`odoo.conf` edits) (`R9`, citing `R28`/`R29`
  originally). *Why it matters:* already fully absorbed into the accepted
  DEC-005 decision (Option 2 chosen partly on this evidence) — not a new
  finding, restated here only because the task requires competitor notes be
  present if externally sourced. *Scope:* informs **core engine** substrate
  choice (already decided).
- **[Competitor claim]** ecommerce_shopify is cron-only (10-minute interval),
  no webhooks, email-only errors — logged in the existing avoid-list (`R27`)
  as the reliability *floor*, an anti-pattern (A-SYNC-1, A-LOG-1). No
  competitor in the existing corpus demonstrates named GraphQL
  rate-limit/cost-throttling handling (`R9`, citing prior research) — a
  market whitespace, not a new finding this session.
- **[Competitor claim]** No competitor in the existing corpus is documented
  exposing raw `ir.cron` fields to end users except Webkul (anti-pattern
  A-UX-2, `R27`) — restated here as context for the "logs/observability"
  analysis area, not independently re-verified this session.

---

## Facts

The great majority of claims above are labeled **[Fact]** inline, each with
its own citation. This section exists to state, in aggregate, which facts
are **new to this project's research corpus** as of this session (i.e. gaps
the pre-006A repo research did not cover) versus **re-confirmations**:

**New this session (genuine research gaps filled):**
- Odoo's `REPEATABLE READ` isolation-level choice and its stated rationale
  (`O4`).
- `lock_for_update()`/`try_lock_for_update()` as Odoo's explicit ORM
  row-locking primitive, `@api.private` (not RPC-reachable), documented only
  in the cron-writing guide (`O9`, `O12`, `O13`).
- `odoo.service.model.retrying()` as Odoo's automatic, bounded,
  jittered-backoff retry-on-serialization-conflict mechanism for RPC/HTTP
  dispatch (`O5`, `O6`) — **fact**. Whether this extends to a cron job's own
  record-processing code does **not**, per the code reviewed (`O7`) — this
  narrower point is a **source-backed inference**, not independently proven
  either way, and is stated as such in the "Inferences" section below and in
  the Odoo concurrency/locking notes above (relabeled this revision from an
  earlier, overstated "Fact — important negative finding").
- Odoo's official coding guidelines' warning that PostgreSQL performance
  degrades past 64 savepoints in one transaction (`O8`, independently
  corroborated by `R31`) — a performance constraint to design against, not a
  hard functional cap (see the fuller wording in "Odoo transaction/error/
  rollback notes" above).
- `ir.cron.progress`'s field shape, and that no dead-letter/DLQ terminology
  or mechanism was found in the specific files/pages reviewed (`O7`, `O14`)
  — not asserted as an absolute claim about the entire Odoo codebase.
- The **Liquid/Storefront-only scope of the 25,000-object pagination cap**
  (`S5`), correcting an ambiguity the pre-006A baseline had left open.
- Full cursor-pagination mechanics (`S1`, `S2`, `S3`) — not previously
  researched in this repo.
- Bulk-operation cancellation, per-line error handling, and operation-level
  error-code detail (`S7`–`S12`) — the pre-006A baseline covered only basic
  mechanics.
- The **16-vs-17 `@idempotent` mutation count discrepancy** (`S16` vs `R8`/
  `R10`) — flagged, not resolved.
- The full OCA `queue_job` source-level read (`Q1`–`Q8`) — the pre-006A
  baseline only confirmed a PyPI release existed, never read the actual
  design.
- All engineering-reference material (`E1`–`E9`) — no prior research in this
  project cited general distributed-systems/API-client engineering
  references.

**Re-confirmed unchanged this session:** Shopify webhook HMAC/retry/dedup
mechanics (`S13`, `S14` vs `R24`), the 24-hour idempotency-key TTL (`S16` vs
`R24`), and `ir.cron`'s 3-consecutive/5-over-7-days failure thresholds (`O14`
vs `R25`) — all match the pre-006A baseline with no material change found.

**New this revision, from `R33` (PR #126):**
- A throttled Shopify **GraphQL** call can return HTTP 200 with a
  `THROTTLED` body code rather than a 4xx status — this package's rate-limit
  research had not independently verified GraphQL throttle response-status
  behavior before this revision.
- Dead-letter-queue visibility, across every vendor `R33` examined, is an
  **opt-in alarm/metric**, not a default push notification; dead-lettering
  can also trigger on a single failed attempt, not only after exhausted
  retries.
- PostgreSQL advisory locks (session- vs. transaction-scoped, and the
  documented `LIMIT`+advisory-lock hazard) — not previously researched by
  this package.
- The exact AWS Architecture Blog Equal Jitter formula, corrected by `R33`'s
  own adversarial-verification pass.
- Three independent shards (this package, `R31`, `R33`) now converge on the
  identical "requires actual Odoo 19 runtime proof, not source-reading
  alone" conclusion for whether `ir.cron`'s locking prevents duplicate
  execution — previously a single package's finding, now a
  three-shard-corroborated open question.
- REST Admin API `page_info` cursor URLs are explicitly documented as
  temporary/not-for-saving — the GraphQL equivalent remains an open
  question, now corroborated by an independent shard reaching the same
  "undocumented for GraphQL" conclusion.
- Vendor disagreement on how to handle a concurrent, still-in-flight
  duplicate request (IETF: HTTP 409; Stripe: don't cache, tell client to
  retry) — Shopify's own `IDEMPOTENCY_CONCURRENT_REQUEST` is a third
  documented shape.

## Inferences

Every claim tagged **[Inference]** above is this session's own reasoned
synthesis of two or more cited facts, never presented as a directly-stated
source claim. The highest-stakes inferences, restated for visibility:

1. A future sync-engine cron job writing its own domain records may **not**
   be automatically protected by Odoo's RPC-layer serialization-retry, based
   on the code reviewed (`O5`+`O6`+`O7` synthesis; `R31` independently
   confirms the RPC/HTTP-dispatch half of this synthesis and separately
   documents `ir.cron`'s job-*acquisition*-level locking, without itself
   settling the domain-record-processing question). **This is a
   source-backed inference, not a proven fact — it requires live Odoo
   runtime evidence before any implementation relies on it** (see "Questions
   that require live Odoo.sh proof" in the companion open-questions
   document). If confirmed, explicit locking or catch-and-retry inside the
   job handler would be a plausible response, not a settled requirement.
2. Cursor-based pagination *could* serve as a resumable-import checkpoint,
   but neither Shopify nor Odoo documents this combination as a named
   pattern, and Shopify does not confirm cursor durability across a paused
   sync (`S1`+`E6`/`E7` synthesis) — genuinely open, not decided by this
   research.
3. The existing accepted job/log substrate (`R1`, `R2`) already structurally
   satisfies the *purpose* a dead-letter queue and a redaction/PII-safe
   logging layer exist to serve (`E4`+`E9` synthesis) — this research found
   no gap requiring new core-engine mechanism, only confirmation the
   existing design is sound against these external patterns.

## Unsupported claims removed

No claim was drafted and then removed for lack of support during this
session's research — the fan-out research design (source-first, structured
citation output per agent) meant unsupported claims were filtered at
collection time rather than after drafting. Two claims were **downgraded**
rather than removed outright:

- An initial expectation that Shopify would explicitly recommend "bulk
  operations for large one-off exports only, not routine sync" was **not**
  found in either bulk-operations page after a targeted full-text search
  (`S7`, `S8`) — restated above as an explicit open question rather than
  asserted as fact.
- An initial expectation that the readiness-check `_get_checks()` extension
  seam would be explicitly named in the core-substrate blueprint as the
  template for job-type registration was **not** found — the repo deep-read
  found the two seams described independently, structurally similar but never
  cross-referenced by name. Restated above as this session's own
  **[Inference]**, not a repo claim.

## Open questions

See the dedicated companion document,
[`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md),
for the full, categorized list. Summary of the questions raised for the
first time by this session's research (as opposed to already-known open
items like VAL-B2/MBQ-05/TD-002):

1. Cursor durability/reuse across a paused-and-resumed sync — undocumented.
2. `partialDataUrl`/`url` population behavior for a `CANCELED` (vs `FAILED`)
   bulk operation — undocumented.
3. Retry-safety of the `bulkOperationRunQuery`/`bulkOperationRunMutation`
   **start call** itself under an ambiguous (timeout) outcome — undocumented.
4. The 16-vs-17 `@idempotent` mutation count discrepancy — unresolved,
   flagged for re-verification at build time.
5. Whether the Task-005 disconnect-cancellation sweep fully closes the race
   against a job already `running` inside an in-flight `ir.cron` batch at the
   instant of disconnect — requires live Odoo-runtime proof, not resolved by
   any source in this package.
6. Whether cursor-based checkpointing should be a core-engine-owned or
   domain-module-owned responsibility — genuinely undecided, no source
   settles it either way.

## Source list

See [`sync-engine-source-inventory.md`](./sync-engine-source-inventory.md)
for the full graded list (63 sources: 6 repo-code, 17 repo-docs/decisions, 10
repo-research-synthesis — including `R31`/PR #124 and `R32`/PR #123 (added
revision 1) and `R33`/PR #126 (added this revision) — 16 official-Shopify, 1
community, 14 official-Odoo, 8 OCA, 9 engineering-reference; `R33` itself
separately catalogs 52 additional sources within its own document, not
double-counted here). See the source inventory's "Synthesis hierarchy" note
for how this package, `R31`, `R32`, and `R33` relate to one another.
