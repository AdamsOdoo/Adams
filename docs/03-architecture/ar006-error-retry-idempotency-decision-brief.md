# AR-006 Error / Retry / Idempotency Decision Brief

> **AR-004 + AR-006 Decision Preparation sprint.** This brief prepared the
> proposal for **AR-006** (error handling, retry, idempotency, and failure
> taxonomy) in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md),
> which fed [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md).
> **DEC-009 is now `Status: Accepted by ChatGPT` (2026-07-02, after PR #64
> merged into `Shopify-connector` and Fable's minor-change review was
> applied), and AR-006 is now accepted through DEC-009.** This brief
> remains the evidence-backed decision brief behind DEC-009 — **it does not
> itself decide anything or authorize implementation**; acceptance flows
> through DEC-009. AR-007 (inventory) and AR-008 (fulfillment) internal
> design **remain not decided**. Exact retry/backoff constants and
> reconciliation cadence/scope remain implementation-planning items, not
> decided by this brief or by DEC-009. This brief creates no Odoo module,
> no database DDL, no Python class, and authorizes no implementation
> (`CLAUDE.md` §4–§5).

## Claim classification used in this document

Per `CLAUDE.md` §8: `[Accepted decision]` · `[Official fact]` (Shopify
`shopify.dev` or Odoo 19.0 official docs/source, cited with URL + access
date) · `[Official limitation]` · `[Competitor claim]` · `[Inference]` ·
`[Recommendation]` (this brief's proposal — not yet a decision) ·
`[Implementation-planning default]` (a conceptual number/behaviour proposed
for later implementation planning, explicitly **not** a verified constant)
· `[Open question]`.

## Purpose

Prepare a decision-ready, evidence-backed proposal for AR-006 that works
with the already-accepted DEC-005 (sync orchestration) and DEC-006
(binding/dedup/identity), and with DEC-007's Phase 1 guardrails
(first-inventory-push, fulfilment-notification, financial total-check).
`architecture-decision-framing.md` records that AR-006 depends on AR-003
(queue/orchestration substrate — now decided) and AR-005 (binding/identity
— now decided), so both prerequisite inputs are now fixed and AR-006 can be
framed against a settled substrate instead of an open fork.

## Inputs used (repo-local; no external fetch needed — see *External
research performed*)

- `[Accepted decision]` DEC-005 — webhook fast-ack + HMAC + dedup on
  `X-Shopify-Webhook-Id`; internal queue/job model; `ir.cron` worker(s)
  honoring `--max-cron-threads`; manual sync; scheduled reconciliation;
  per-record isolation (savepoints); every job carries a retry counter and
  ends in a visible state including dead/final-failed; `ir.cron`'s own
  coarse deactivation is explicitly **not** the connector's retry
  mechanism.
- `[Accepted decision]` DEC-006 — dedicated, store-scoped binding is the
  home for connector-designed idempotency keys beyond the Shopify
  17-mutation `@idempotent` surface; deleted/recreated Shopify records
  marked stale, not silently dropped/recreated; every binding carries audit
  fields (matched-by, matched-at, source strategy, match key, status).
- `[Accepted decision]` DEC-007 — first Odoo→Shopify inventory-push guard
  (mapped location + preview + operator confirmation + recorded
  source-of-truth + skip/manual-match option); fulfilment
  customer-notification default (no notification unless explicitly
  enabled/confirmed); conservative-by-default invoice/payment creation with
  a total-check guard before creation.
- `[Accepted decision]` [`phase1-domain-model-brief.md`](./phase1-domain-model-brief.md)
  Domain 8 (queue/log/error) — the minimum job concept (source, state,
  retry count, error class/message placeholder, related store/binding/
  record, user-visible log/error-center) that this brief expands into a
  full taxonomy.
- `[Accepted decision]` DEC-003 reliability spine — layered sync, HMAC,
  webhook-ID dedup, fast ack, idempotency keys, duplicate prevention,
  per-record isolation, reason-coded logs, safe manual retry, retry
  classification concept, rate-limit awareness, resumable jobs, honest
  freshness; and the mandatory carried-forward regression: idempotent-
  refund/no-double-refund even though refunds are deferred.
- `[Official fact]` Shopify rate-limit, webhook-delivery, and idempotency
  facts, cited individually below
  (`../01-research/shopify-official-api-notes.md`, access dates
  2026-06-30/2026-07-01/2026-07-02).
- `[Official fact]` Odoo `ir.cron` failure/batch facts and Odoo.sh
  best-effort cron behaviour, cited individually below
  (`../01-research/odoo-official-architecture-notes.md`, access dates
  2026-06-30/2026-07-01/2026-07-02).
- `[Competitor claim]`
  [`../01-research/avoid-list.md`](../01-research/avoid-list.md) A-SYNC-1
  through A-SYNC-6, A-RET-1 through A-RET-3, A-PAY-2, A-LOG-1 through
  A-LOG-3, A-IMP-2; `[Competitor claim]`
  [`../01-research/common-patterns.md`](../01-research/common-patterns.md)
  and [`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md)
  (VentorTech automatic retry + `@idempotent`; TeqStars typed logs +
  Activity-on-failure, explicitly **not** demonstrated for automatic
  retry/idempotency/reconciliation/rate-limit handling).

### External research performed

None beyond re-reading already-cited repo docs. Every Shopify/Odoo fact
this brief needs (rate limits, webhook retry/dedup, the `@idempotent` set
and its 24-hour TTL, `ir.cron` failure constants, Odoo.sh best-effort cron
behaviour) is already Tier-1-cited in
`../01-research/shopify-official-api-notes.md` and
`../01-research/odoo-official-architecture-notes.md` with URL + access
date. No `docs/03-architecture/ar004-ar006-evidence-refresh.md` file was
created.

## Official facts governing error/retry/idempotency behaviour

**Shopify** (`../01-research/shopify-official-api-notes.md`):

1. `[Official fact]` REST rate limits: leaky bucket, Standard **40-request
   bucket / 2 req/s** restore, Shopify Plus **400-request bucket / 20
   req/s**; exceeding returns **HTTP 429** with a `Retry-After` header.
   (https://shopify.dev/docs/api/admin-rest/usage/rate-limits)
2. `[Official fact]` GraphQL cost-based throttling: points restored per
   second by plan (Standard 100, Advanced 200, Plus 1000, Enterprise 2000);
   single query capped at 1,000 points; response carries
   `extensions.cost.throttleStatus` (`maximumAvailable`,
   `currentlyAvailable`, `restoreRate`).
   (https://shopify.dev/docs/api/usage/limits)
3. `[Official fact]` Webhooks: Shopify expects a 200 response within a
   **1-second connection / 5-second total** timeout; on failure, **retries
   8 times over the next 4 hours**; after **8 consecutive failures**, an
   Admin-API-created subscription is **automatically deleted**.
   (https://shopify.dev/docs/apps/build/webhooks/subscribe/https)
4. `[Official fact]` Webhook delivery **is not guaranteed** — "apps
   shouldn't rely on receiving webhook data" and should use reconciliation
   jobs; duplicate deliveries are possible, so handlers must be idempotent.
   (https://shopify.dev/docs/apps/build/webhooks/best-practices)
5. `[Official fact]` Webhook integrity/dedup: verify
   `X-Shopify-Hmac-SHA256` (HMAC-SHA256 of the **raw** request body) before
   processing; deduplicate using **`X-Shopify-Webhook-Id`**.
   (https://shopify.dev/docs/apps/build/webhooks/verify-deliveries)
6. `[Official fact]` "Shopify tracks idempotency keys for **24 hours** from
   the original request" — the server-side idempotency dedup TTL.
   (https://shopify.dev/docs/api/usage/implementing-idempotency)
7. `[Official limitation]` `@idempotent` "only applies to mutations that
   support the `@idempotent` directive" — a **fixed list of 17 mutations**
   (inventory/location mutations + `refundCreate`); **no general/
   all-mutation idempotency and no `clientMutationId`**.
   (https://shopify.dev/docs/api/usage/idempotent-requests;
   https://shopify.dev/docs/api/usage/implementing-idempotency)
8. `[Official fact]` Concurrent duplicate requests while the first is still
   processing return **`IDEMPOTENCY_CONCURRENT_REQUEST`** instead of being
   processed.
   (https://shopify.dev/docs/api/usage/implementing-idempotency)
9. `[Official fact]` As of API version **2026-04**, `inventorySetQuantities`
   and `inventoryAdjustQuantities` **require** an `@idempotent` key
   (optional since 2026-01); `refundCreate` also requires `@idempotent` as
   of 2026-04.
   (https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities;
   https://shopify.dev/docs/api/usage/idempotent-requests)
10. `[Official fact]` An idempotency key is "a unique string identifier
    generated by your app"; "each distinct request should have its own
    unique idempotency key" (UUID recommended).
    (https://shopify.dev/docs/api/usage/idempotent-requests)

**Odoo 19.0** (`../01-research/odoo-official-architecture-notes.md`):

11. `[Official source-code fact]` `ir.cron` (19.0) failure constants:
    `CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`;
    `MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5`;
    `MIN_DELTA_BEFORE_DEACTIVATION = 7 days`; deactivation fires only when
    `failure_count >= 5` **and** `first_failure_date + 7 days < now`.
    (`github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py`)
12. `[Official fact]` Cron functions should batch; the framework commits
    after each batch and re-calls until done ("do not reschedule
    yourself"); `_commit_progress(processed=0, *, remaining=None,
    deactivate=False)` commits/logs progress.
    (https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html)
13. `[Official fact]` `--max-cron-threads` defaults to **2**.
    (https://www.odoo.com/documentation/19.0/developer/reference/cli.html)
14. `[Official fact]` (2026-07-02 evidence-refresh fact, already cited in
    DEC-005) On Odoo.sh, scheduled actions run **"best effort"** even in
    production — "we cannot guarantee an exact running time," "do not
    expect any scheduled action to be run more often than every 5 min,"
    and execution time is limited; Odoo.sh's own guidance is to batch,
    commit per batch, and be idempotent.
    (https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html)
15. `[Official source-code fact]` `sudo()` bypasses access rights **and**
    can cross record-rule boundaries — job execution and binding access
    must not rely on `sudo()` to cross store isolation (already load-bearing
    for DEC-005/DEC-006; the same constraint governs job-worker code in
    this taxonomy).
    (`github.com/odoo/odoo/blob/19.0/odoo/orm/models.py`)

`[Inference]` Together, facts 6–10 establish a **hard platform ceiling**:
Shopify's own idempotency mechanism covers only 17 mutations with a 24-hour
window and no general concurrency-safe replay — everything else needs a
**connector-designed idempotency key**, which is why DEC-006 places that
responsibility on the binding record. Facts 11–14 establish that **no
substrate choice removes the need for connector-owned retry/backoff** —
`ir.cron`'s failure model is coarse and Odoo.sh crons are best-effort, so
the job model itself (not the scheduler) must own retry state.

## Options considered (retry-policy posture)

### Option A — Retry everything automatically

Every job failure is retried automatically with backoff, regardless of
error class, until a fixed attempt ceiling.

**Disposition: rejected (proposed).** `[Inference]` Violates DEC-003's
explicit "retry classification concept" requirement and directly risks
double-acting on non-idempotent operations — `[Official limitation]` most
Shopify mutations have **no** platform idempotency guarantee (fact 7), so
blind automatic retry of e.g. a `userErrors`-rejected mutation or a
config/mapping error would either repeat the same failure forever (wasting
throttle budget, fact 1–2) or, worse, retry an operation whose first
attempt may have partially succeeded. Matches avoid-list **A-RET-3**
(`[Competitor claim]`: "naive retry that double-acts").

### Option B — Never retry automatically / manual-only recovery

Every failure requires a human to explicitly re-trigger it; no automatic
retry ever.

**Disposition: rejected (proposed).** `[Inference]` Contradicts DEC-003's
"safe manual retry" **and** "retry classification concept" (which implies
some classes *are* auto-retryable); makes the connector strictly worse than
the one competitor (`[Competitor claim]` VentorTech) that demonstrates
automatic retry of safe operations, and directly reproduces avoid-list
**A-RET-1** ("manual-only recovery... WK/EM/EC/SH recover manually; only
VT auto-retries"). Also ignores that transient errors (throttling,
temporary network/server errors) are, by definition, likely to succeed on
their own on a later attempt — forcing a human to babysit every rate-limit
429 is poor UX and contradicts the "recovery-first" principle in
`../02-product/setup-ux-principles.md`.

### Option C — Classify errors; auto-retry only what is safe (recommended)

Every error is classified at the point of failure; only error classes that
are both (a) likely to be transient/self-healing and (b) safe to repeat
without risk of double-acting are auto-retried with backoff; everything
else surfaces to a human with a clear next action.

**Disposition: recommended (proposed).** See *Recommended proposed
approach* below.

## Recommended proposed approach

### 1. Job sources

| Source | Description | Grounding |
| --- | --- | --- |
| `webhook` | Enqueued from a fast-acknowledged, HMAC-verified webhook delivery, deduplicated by `X-Shopify-Webhook-Id` | DEC-005; fact 5 |
| `manual_sync` | Operator explicitly triggers a sync for a record or a batch | DEC-005; DEC-003 |
| `scheduled_sync` | Periodic `ir.cron`-driven sync unrelated to a specific incoming event (e.g. a routine catalog pull) | DEC-005 |
| `reconciliation` | Scheduled or on-demand `updated_at`-filtered comparison pass, the correctness backstop for missed/undelivered webhooks | DEC-005; fact 4 |
| `setup_readiness_check` | The connection/setup wizard's inline test-connection and readiness validation | DEC-004; brief §"setup/readiness wizard" (AR-004) |
| `export_preview_dry_run` | A read-only diff/preview job that computes what a write *would* do without writing (e.g. the `productSet` dry-run diff) | DEC-003 controlled-export requirement; DEC-004 `productSet` delete-on-omit risk |

### 2. Job states

`[Recommendation]` (adjusted from the sprint prompt's candidate list for
clarity; every state is either terminal or has a defined next-state set)

| State | Meaning | Terminal? |
| --- | --- | --- |
| `draft` | Created (e.g. by a preview action or a not-yet-validated webhook) but not yet eligible to run | No — → `queued`, or `cancelled` if discarded before enqueue |
| `queued` | Validated, waiting for the next available `ir.cron` batch/worker slot | No — → `running` or `cancelled` |
| `running` | Currently being processed inside a batch, under per-record isolation (savepoint) | No — → `succeeded`, `retry_waiting`, `failed_retryable`, `failed_final`, `skipped`, or `blocked_manual_review` |
| `succeeded` | The write (or a deduped/already-applied no-op) completed | Yes |
| `retry_waiting` | Failed with an auto-retryable error class; scheduled for a future attempt after a backoff interval | No — → `queued` (after backoff), `failed_retryable`/`failed_final` (attempts exhausted), or `cancelled` (if a newer job for the same record supersedes it and this attempt is no longer needed) |
| `failed_retryable` | Automatic attempts exhausted, or the error class needs a human fix first; visible in the error center with a "Retry" action | No — → `queued` (operator retries) or `skipped`/`cancelled`/`failed_final` |
| `failed_final` | Dead-letter state; reached after `failed_retryable` exhausts a bounded number of manual retries, or the error class is non-retryable by nature | Yes (an operator may still start a **fresh** job — never a silent auto-requeue of this one) |
| `skipped` | Intentionally not processed (e.g. operator chose "skip" on an ambiguous match, or reconciliation found no action needed) | Yes — not a failure |
| `cancelled` | Withdrawn before completion (e.g. superseded by a newer webhook for the same record, or an operator cancelled a queued job) | Yes — not a failure |
| `blocked_manual_review` | Cannot proceed without a human **decision** (not a simple retry) — e.g. ambiguous match, or a destructive-write guard not yet satisfied | No — → `queued` (after the decision is made) or `skipped`/`cancelled` |

`[Inference]` `retry_waiting` and `failed_retryable` are kept distinct
because the UX and the required action differ: `retry_waiting` is a system-
owned countdown (no user action needed, matches DEC-003's "resumable
jobs"), while `failed_retryable` is user-actionable (matches DEC-003's
"safe manual retry"). `blocked_manual_review` is kept distinct from both
because the fix is a **decision** (e.g. resolve an ambiguous match, confirm
a destructive-write guard), not a **retry** of the same operation.

### 3. Error classes

| Error class | Example trigger | Grounding |
| --- | --- | --- |
| Shopify throttling/rate-limit | HTTP 429 / GraphQL cost throttle (`throttleStatus`) | facts 1–2 |
| Shopify temporary/server/network | 5xx, timeout, connection error | `[Inference]` general API-client resilience practice |
| Shopify permission/scope/auth | 401/403, missing OAuth/token scope | DEC-004 credential model |
| Shopify userErrors/validation | GraphQL mutation returns a populated `userErrors` array | `[Inference]` GraphQL mutation contract (Shopify Admin GraphQL error shape) |
| Odoo validation/configuration | ORM `ValidationError`, missing required field, misconfigured connector setting | `[Inference]` Odoo ORM validation practice |
| Mapping missing | No field-mapping configured for an incoming value (e.g. an unmapped tax code) | brief §"mapping configuration" (AR-004); DEC-003 essential-mapping requirement |
| Ambiguous match | Binding/dedup resolution returned multiple candidates | DEC-006 "ambiguous → manual review, never an automatic guess" |
| Binding conflict | Two Shopify records both resolve to the same Odoo record, or the binding disagrees with the current value | DEC-006 |
| Duplicate risk | Duplicate-prevention preview flags a would-be duplicate create | DEC-003 duplicate-prevention preview |
| Destructive-write guard blocked | First-inventory-push guard, or `productSet` dry-run shows unexpected list-field deletions, not yet confirmed | DEC-007; DEC-004 `productSet` delete-on-omit |
| Inventory location missing | Shopify location not mapped to an Odoo warehouse/location | DEC-007 first-push guard; ties AR-007 |
| Fulfillment notification confirmation missing | Notification setting is ambiguous/unconfirmed for a store/order where DEC-007's safe default needs an explicit decision | DEC-007; ties AR-008 |
| Financial total mismatch | The DEC-007 total-check guard fails — a would-be invoice/payment artifact's total does not reconcile against the imported order total | DEC-007 §6 |
| Data shape/schema mismatch | Fetched payload does not match the expected structure (e.g. API-version drift, unexpected null) | `[Inference]` defensive parsing practice |
| Concurrency/race conflict | `IDEMPOTENCY_CONCURRENT_REQUEST`, or an Odoo write conflict on the same binding | fact 8 |
| Unknown/system error | Uncaught exception; catch-all | `[Inference]` safety net, must not be retried indefinitely |

### 4. Retry behaviour

| Error class | Default behaviour | Rationale |
| --- | --- | --- |
| Shopify throttling/rate-limit | Automatic retry, backoff paced off `throttleStatus`/`Retry-After` | Transient by definition; retrying is the platform-intended response (facts 1–2) |
| Shopify temporary/server/network | Operation-type-dependent — see §4a below | Transient by nature, but retry safety depends on whether the failed operation was a read, an `@idempotent` write, or a non-`@idempotent` write with an ambiguous outcome |
| Concurrency/race conflict | Automatic retry, short backoff | Safe once the concurrent operation clears (fact 8) |
| Shopify permission/scope/auth | No automatic retry | Will not self-heal; needs an operator to fix scopes/reconnect |
| Shopify userErrors/validation | No automatic retry → manual fix then retry | Same input produces the same rejection; needs a data/mapping fix |
| Odoo validation/configuration | No automatic retry → manual fix then retry | Same as above, Odoo-side |
| Mapping missing | Skip until mapped → manual fix then retry | Nothing meaningful to retry until a mapping exists |
| Ambiguous match | Operator confirmation required (`blocked_manual_review`) | DEC-006 mandates manual resolution, never an automatic guess |
| Binding conflict | Operator confirmation required | Same rationale as ambiguous match |
| Duplicate risk | Operator confirmation required | DEC-003 duplicate-prevention preview — no blind create |
| Destructive-write guard blocked | Operator confirmation required | DEC-007 guard is a decision gate, not a retryable error |
| Inventory location missing | Operator confirmation required (mapping) | DEC-007 first-push guard |
| Fulfillment notification confirmation missing | Operator confirmation required, or falls back to the DEC-007 safe default (no notification) | DEC-007 |
| Financial total mismatch | Conservative — no automatic retry; requires operator review or a configuration/data correction (e.g. a tax/shipping/discount mapping fix) before any retry is attempted; must never proceed silently | DEC-007 §6 conservative-by-default rule; never silently create a mismatched artifact |
| Data shape/schema mismatch | No automatic retry | Same payload → same failure; likely needs a connector fix, not a retry |
| Unknown/system error | No automatic retry (single safety-net auto-retry `[Implementation-planning default]`, then human) | Avoid retry storms on an unclassified failure; a human should see technical details before deciding |

`skip` and `dead/final-failed` are **outcomes**, not per-error-class
defaults — any class can end in `skipped` (operator choice) or
`failed_final` (attempts/manual-retries exhausted), per the state machine
in §2.

### 4a. Ambiguous-outcome rule for non-idempotent writes

A Shopify temporary/server/network failure means something different
depending on what was being attempted when it happened — this is a
correctness-critical distinction, not just a retry-tuning detail:

1. **Reads.** Automatic retry is always safe — a failed read has no side
   effect to duplicate.
2. **Writes using a Shopify `@idempotent` mutation.** Automatic retry is
   safe **using the same persisted idempotency key**, within Shopify's
   24-hour dedup window (facts 6, 7, 9) — a retried request with the same
   key is deduplicated server-side, not double-applied.
3. **Writes outside Shopify's `@idempotent` surface, where the outcome is
   unknown after dispatch** (a timeout or connection loss *after* the
   request left the connector, before a confirmed response). **No blind
   retry.** Shopify may already have applied the mutation. The job must
   either:
   - perform a **safe verification read** of the current Shopify state
     before any re-attempt, where one exists (e.g. re-fetch the target
     object and compare it against the intended write), or
   - route to **`blocked_manual_review`** if the outcome cannot be safely
     verified this way.

A connector-internal job idempotency key (§5) prevents the *connector* from
re-processing the same job twice, but it does **not** make it safe to
re-send the mutation to *Shopify* — Shopify only treats the fixed
17-mutation `@idempotent` list as safe to replay with a reused key (fact
7); every other mutation is only as safe to retry as the verification step
above makes it.

### 5. Idempotency layers

| Layer | Mechanism | Grounding |
| --- | --- | --- |
| Webhook dedup | `X-Shopify-Webhook-Id` deduplication before enqueue | fact 5; DEC-005 |
| Shopify object identity (GID) | Used as the external key, but **never assumed permanent** — deleted/recreated records are handled defensively | DEC-006; `[Open question]` GID permanence not asserted |
| Store-scoped binding key | Per-store uniqueness on `(store, Shopify GID)` and `(store, Odoo model, Odoo record)` | DEC-006 |
| Internal job idempotency key | A connector-designed key (e.g. derived from store + operation + target + payload version) so re-running the same job after a crash mid-batch does not double-process it **on the connector side**. This key alone does **not** make it safe to re-send a non-`@idempotent` Shopify mutation after an ambiguous-outcome failure — see §4a | `[Recommendation]`, grounded in DEC-006 "binding is the natural home for connector-designed idempotency keys... feeds AR-006" |
| Shopify `@idempotent` mutation key | A generated, persisted key attached to each of the 17 applicable mutations, reused on retry within the platform's 24-hour window | facts 6, 7, 9, 10 |
| Reconciliation safety | Reconciliation reads, compares, and writes only on detected drift — safe by construction (convergent, not blindly re-applied) | DEC-005; fact 4 |
| Manual retry safety | Operator-triggered retry reuses the same idempotency-key/binding path as automatic retry — no separate "manual" code path that skips guards | `[Recommendation]` |
| Preview/dry-run no-write safety | The `export_preview_dry_run` job source is structurally incapable of calling a write mutation | DEC-003; DEC-004 `productSet` risk |
| Total-check guard | Financial artifact creation is blocked unless its total reconciles against the imported order total | DEC-007 §6 |
| First-inventory-push confirmation record | The operator confirmation + preview + source-of-truth decision is persisted per binding, so a later re-run cannot silently repeat a "first push" | DEC-007 |
| Fulfillment notification setting record | The notification decision (explicit enable, or the DEC-007 default of none) is persisted per binding/job, so retries do not re-ask or silently flip the default | DEC-007 |

### 6. Retry limits and backoff

`[Implementation-planning default]` — conceptual behaviour only, no fixed
constants asserted here:

- Auto-retryable classes (throttling, temporary/network, concurrency) use
  **exponential backoff** conceptually appropriate to their cause (pacing
  off the live `throttleStatus`/`Retry-After` for throttling; a short fixed
  or lightly-increasing delay for concurrency conflicts).
- Every job carries a **bounded** attempt count before moving from
  `retry_waiting` to `failed_retryable`; the exact ceiling is an
  **implementation-planning default**, not fixed by this brief.
- `failed_retryable` allows a **bounded** number of manual retries before
  becoming `failed_final`; the exact ceiling is likewise an
  implementation-planning default.
- `[Official fact]` Shopify's own webhook retry cadence (8 attempts over
  ~4 hours, fact 3) is cited here as **context for the order of magnitude
  the platform itself considers reasonable for transient recovery**, not as
  a constant this connector copies — the connector's own job retries are a
  **separate** mechanism from Shopify's webhook-delivery retries.
- `[Official source-code fact]` `ir.cron`'s own deactivation math (5
  failures over ≥7 days, fact 11) is **not** reused as the connector's
  job-level retry-count logic — already decided in DEC-005; this brief
  reaffirms it. The connector's job model tracks its **own** `retry_count`
  per job, independent of `ir.cron`'s scheduled-action-level failure count.

### 7. User-facing log requirements

`[Recommendation]`, grounded in DEC-003's UX spine,
`../02-product/setup-ux-principles.md`, `phase1-domain-model-brief.md`
Domain 8, and avoid-list A-LOG-1/2/3:

- Readable error reason (never a raw stack trace as the primary message —
  avoid-list A-LOG-3).
- Related store / Shopify object / Odoo record / binding / job source
  shown together, so a failure can be traced and retried in context
  (DEC-005/006).
- Suggested fix, phrased for the error class (e.g. "map this tax code,"
  "confirm the Shopify location mapping").
- A retry action, shown only for states where retry is the correct next
  step (`failed_retryable`).
- A skip/manual-match action, shown for `blocked_manual_review` states
  (ambiguous match, binding conflict).
- Technical details (raw error, request ID) available on demand, but never
  the primary user-facing message (avoid-list A-LOG-1, A-LOG-3).
- Per-record isolation reflected honestly in the log — one failure never
  silently blocks or hides sibling records (avoid-list A-LOG-2; DEC-005).
- Honest freshness — the log should reflect the real 24-hour idempotency
  window and the real webhook-dedup behaviour rather than implying
  infinite/instant dedup (`rb14-decision-candidate-brief.md` UX
  implications).

### 8. Audit requirements

`[Recommendation]`, grounded in DEC-006's binding audit fields and DEC-007's
guardrail-confirmation requirements:

- What was attempted — the job's source, target record, and operation.
- What was written — the actual mutation/write performed, if any (never
  assume "attempted" implies "written").
- What was skipped — explicit record of skip decisions and who/what made
  them (operator vs. system rule).
- Who confirmed destructive/first-push/notification actions — DEC-007's
  first-inventory-push guard and fulfilment-notification guard both require
  a recorded confirmation, not just a UI prompt that leaves no trace.
- Source-of-truth record — which system was treated as authoritative for a
  given first-sync or first-push decision (DEC-003, DEC-007).
- Before/after values for destructive operations — where a write can
  overwrite or delete existing state (e.g. `productSet` delete-on-omit,
  inventory quantity overwrite), the prior value is recorded alongside the
  new one.

## Rejected or weakened alternatives

| Alternative | Disposition | Why |
| --- | --- | --- |
| **Retry everything automatically** (Option A) | Rejected (proposed) | Violates DEC-003's retry-classification requirement; risks double-acting on non-idempotent operations (A-RET-3) |
| **Never retry automatically / manual-only recovery** (Option B) | Rejected (proposed) | Contradicts DEC-003's "safe manual retry" + retry-classification concept; reproduces avoid-list A-RET-1 |
| **User-facing stack traces as the primary error message** | Rejected (proposed) | Avoid-list A-LOG-1/A-LOG-3; contradicts the DEC-003 recovery-first UX spine |
| **No idempotency key / binding-first retry only (rely solely on the binding to prevent duplicates, with no per-operation idempotency key)** | Rejected (proposed) | The binding prevents *identity* duplication but not *operation* duplication (e.g. two retries of the same mutation against an already-correctly-bound record); DEC-006 explicitly names the binding as the home for idempotency keys, not a substitute for them |
| **Treating a single global retry policy as sufficient (no per-error-class taxonomy)** | Weakened, not formally rejected | Collapses into either Option A or Option B's failure modes depending on how the single policy is tuned; the taxonomy in §3–4 is this brief's proposed alternative |

## What remains open

- **AR-007 full inventory architecture** and **AR-008 full fulfilment
  architecture** — untouched; the inventory-location-missing and
  fulfilment-notification-confirmation-missing error classes here are
  taxonomy entries only, not a quantity-field, multi-location, or
  FulfillmentOrder-orchestration design.
- **Exact retry-count ceilings and backoff constants** — flagged
  `[Implementation-planning default]` throughout; no verified Shopify or
  Odoo constant fixes a Phase 1 number, so none is asserted here.
- **Exact job/log/binding Odoo model, field, and constraint design** —
  conceptual taxonomy only; schema deferred to a domain-model/
  implementation sprint (same deferral pattern as DEC-005/006).
- **`@idempotent` key uniqueness scope** (per-shop/app/global) and
  **bulk-operation idempotency** — `[Open question]`, unresolved since
  RB-14 Part 2, unchanged by this brief.
- **Reconciliation cadence and scope** (per-object vs. global, exact
  schedule) — `[Accepted decision — handoff]` DEC-005 explicitly routed
  detailed reconciliation cadence to AR-006
  (`../04-decisions/DEC-005-sync-orchestration-strategy.md` §"Performance
  implications": "detailed cadence is AR-006, not decided here"). This
  brief resolves the error/retry/idempotency taxonomy but does not choose
  an exact cadence — cadence and scope remain `[Open question]`, routed
  onward to Master Blueprint / implementation planning before code, not
  silently dropped.
- **Exact user-facing copy/wording for error reasons and suggested fixes**
  — a UX/operator-flow sprint concern, not decided here.

## No implementation authorized

This brief documents a conceptual taxonomy only. It creates no database
DDL, no Python class, no Odoo module, and no code. Now that ChatGPT has
accepted [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)
(2026-07-02), the no-code gate (`CLAUDE.md` §4–§5) still remains in force
until ChatGPT separately opens a dedicated implementation gate per
`../05-qa/quality-feedback-loop.md` §10.
