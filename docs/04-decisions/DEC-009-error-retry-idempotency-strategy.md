# DEC-009 — Error / Retry / Idempotency Strategy (AR-006)

> **Proposed architecture decision record — NOT yet accepted.** This record
> proposes a resolution for **AR-006** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md),
> prepared in the AR-004 + AR-006 Decision Preparation sprint (2026-07-02),
> after DEC-004/005/006/007 acceptance. It requires **explicit ChatGPT
> review and acceptance** before it resolves AR-006, and does **not** by
> itself authorize implementation or change DEC-003/004/005/006/007.

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-
authorizing.

## Date

2026-07-02.

## Scope

**AR-006 only** — Phase 1 **error classification**, **retry behaviour**,
**idempotency layers**, and **user-facing log/audit requirements**, working
within the already-accepted DEC-005 orchestration substrate and DEC-006
binding model. Does **not** design concrete Odoo model/field/constraint
schema, does **not** fix exact retry-count/backoff constants beyond
implementation-planning defaults, does **not** decide AR-007 (inventory) or
AR-008 (fulfilment) internal design beyond naming their related error
classes, and does **not** create any Odoo module, database DDL, Python
class, or code. Assumes DEC-004's custom-app/GraphQL premise, DEC-005's
orchestration substrate, DEC-006's binding model, and DEC-007's Phase 1
guardrails.

## Accepted context

- DEC-003 (MVP scope): reliability spine — layered sync, HMAC, webhook-ID
  dedup, fast ack, idempotency keys, duplicate prevention, per-record
  isolation, reason-coded logs, safe manual retry, retry-classification
  concept, rate-limit awareness, resumable jobs, honest freshness; mandatory
  carried-forward idempotent-refund/no-double-refund regression.
- DEC-004 (distribution/API/auth): GraphQL-first surface that fixes the
  idempotency reality (17 `@idempotent` mutations, 24-hour dedup TTL, no
  general mechanism) this record's idempotency layers build on.
- DEC-005 (sync orchestration): webhook fast-ack + dedup, internal queue/
  job model, `ir.cron` worker(s), manual sync, scheduled reconciliation,
  per-record isolation, retry counters, dead/final-failed state; explicitly
  defers the full retry/error taxonomy to AR-006.
- DEC-006 (binding/dedup/identity): dedicated, store-scoped binding as the
  home for connector-designed idempotency keys beyond the platform
  `@idempotent` surface; explicitly defers the idempotency-key taxonomy to
  AR-006.
- DEC-007 (Phase 1 scope clarifications): first-inventory-push guard,
  fulfilment customer-notification default, conservative financial-artifact
  creation with a total-check guard — the Phase 1 guardrails this record's
  error taxonomy and idempotency layers must account for.

## Decision proposed

Adopt a **classified retry policy** (Option C in the decision brief):
every job failure is assigned an error class at the point of failure; only
classes that are both likely transient and safe to repeat are
auto-retried with backoff; every other class surfaces to an operator with a
clear next action (retry, manual fix then retry, skip, or confirmation
required). Idempotency is layered — platform-level (`@idempotent`,
webhook-ID dedup) where Shopify provides it, and connector-designed
(binding-scoped keys, guard-confirmation records) everywhere it does not.
Full rationale, taxonomy tables, and evidence:
[`ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md).

## Error taxonomy

**Job sources:** `webhook`, `manual_sync`, `scheduled_sync`,
`reconciliation`, `setup_readiness_check`, `export_preview_dry_run`.

**Job states:** `draft`, `queued`, and `running` are non-terminal entry
states; `succeeded`, `failed_final`, `skipped`, and `cancelled` are
terminal; `retry_waiting`, `failed_retryable`, and `blocked_manual_review`
loop back to `queued` once their condition is resolved rather than
terminating (full transition table, including the `cancelled` exit
available from `draft`/`queued`/`retry_waiting`, in the brief §2).

**Error classes (16):** Shopify throttling/rate-limit; Shopify temporary/
server/network; Shopify permission/scope/auth; Shopify userErrors/
validation; Odoo validation/configuration; mapping missing; ambiguous
match; binding conflict; duplicate risk; destructive-write guard blocked;
inventory location missing; fulfillment notification confirmation missing;
financial total mismatch; data shape/schema mismatch; concurrency/race
conflict; unknown/system error (full mapping to grounding + default
behaviour in the brief §3–4).

## Retry taxonomy

- **Automatic retry (reads and `@idempotent` writes):** Shopify throttling/
  rate-limit; concurrency/race conflict; Shopify temporary/server/network
  failures on **reads**, or on **writes using a Shopify `@idempotent`
  mutation** (retried using the same persisted idempotency key within the
  platform's 24-hour window).
- **Ambiguous-outcome rule (no blind retry):** a Shopify temporary/server/
  network failure on a **write outside Shopify's `@idempotent` surface**,
  where the outcome is unknown after dispatch (e.g. a timeout or connection
  loss after the request left the connector), is **not** auto-retried. The
  job either performs a safe verification read of Shopify's current state
  before any re-attempt, where one exists, or routes to
  `blocked_manual_review` if the outcome cannot be safely verified. A
  connector-internal job idempotency key prevents connector-side duplicate
  *processing* but does **not** make it safe to re-send the mutation to
  Shopify — see the brief §4a for the full rule.
- **No automatic retry (manual fix then retry):** Shopify permission/
  scope/auth; Shopify userErrors/validation; Odoo validation/configuration;
  mapping missing; data shape/schema mismatch.
- **Operator confirmation required (`blocked_manual_review`):** ambiguous
  match; binding conflict; duplicate risk; destructive-write guard blocked;
  inventory location missing; fulfillment notification confirmation
  missing.
- **No automatic retry, conservative-by-default:** financial total
  mismatch — requires operator review or a configuration/data correction
  before any retry is attempted; must never proceed silently (DEC-007 §6).
- **Single safety-net auto-retry, then human** `[Implementation-planning
  default]`: unknown/system error.
- **Skip and dead/final-failed are outcomes available from any class**, not
  per-class defaults — reached by operator choice (`skipped`) or exhausted
  attempts/manual retries (`failed_final`).
- **Retry limits/backoff:** conceptual only —
  `[Implementation-planning default]`; no fixed constants asserted.
  `ir.cron`'s own deactivation math (5 failures/≥7 days) is explicitly
  **not** reused as the connector's own retry-count logic (reaffirms
  DEC-005).

## Idempotency layers

Webhook dedup (`X-Shopify-Webhook-Id`); Shopify object identity/GID (never
assumed permanent); store-scoped binding key (`(store, GID)` /
`(store, Odoo model, Odoo record)`); internal job idempotency key
(connector-designed, for crash-safe re-runs); Shopify `@idempotent`
mutation key (the 17-mutation fixed list, 24-hour TTL); reconciliation
safety (convergent by construction); manual retry safety (same code path
as automatic retry); preview/dry-run no-write safety (structurally
write-incapable); total-check guard (financial artifacts); first-
inventory-push confirmation record; fulfillment notification setting
record. Full mechanism-to-evidence mapping in the brief §5.

## User-facing log requirements

Readable error reason (no stack trace as the primary message); related
store/Shopify object/Odoo record/binding/job source shown together;
suggested fix; a retry action where retry is the correct next step; a
skip/manual-match action for `blocked_manual_review` states; technical
details available but secondary; per-record isolation reflected honestly;
honest freshness (real 24-hour dedup window, not implied infinite dedup).

## Audit requirements

What was attempted; what was written (never assume attempted implies
written); what was skipped and by whom/what rule; who confirmed
destructive/first-push/notification actions; the source-of-truth record
for first-sync/first-push decisions; before/after values for destructive
operations.

## What remains open

- AR-007 full inventory architecture; AR-008 full fulfilment architecture —
  untouched.
- Exact retry-count ceilings and backoff constants —
  `[Implementation-planning default]` only.
- Exact job/log/binding Odoo model, field, and constraint design — deferred
  to a domain-model/implementation sprint.
- `@idempotent` key uniqueness scope and bulk-operation idempotency —
  `[Open question]`, unresolved since RB-14 Part 2.
- **Reconciliation cadence and scope** — DEC-005 originally routed detailed
  reconciliation cadence to AR-006
  (`../04-decisions/DEC-005-sync-orchestration-strategy.md` §"Performance
  implications"). This record resolves the error/retry/idempotency
  taxonomy but does not choose an exact cadence — cadence and scope remain
  `[Open question]`, routed onward to Master Blueprint / implementation
  planning before code, not silently dropped.
- Exact user-facing copy/wording for error reasons and suggested fixes — a
  UX/operator-flow sprint concern.

## Risks and mitigations

1. **Risk:** a per-error-class taxonomy this detailed could be
   over-engineered relative to Phase 1's actual failure surface.
   **Mitigation:** every class in the taxonomy maps directly to a named
   DEC-003/005/006/007 requirement or a cited Shopify/Odoo fact — none is
   speculative; classes with no Phase 1 evidence were not added.
2. **Risk:** classifying an error as auto-retryable when it is not actually
   safe would reproduce the double-acting failure mode this record exists
   to prevent. **Mitigation:** throttling/rate-limit and concurrency/race
   conflict are auto-retryable and are grounded directly in cited Shopify
   facts about their transient, retry-intended nature; temporary/server/
   network auto-retry is grounded in general API-client resilience
   practice (`[Inference]`, not a specific Shopify fact) and, per the
   ambiguous-outcome rule above, is restricted to reads and `@idempotent`
   writes — non-`@idempotent` writes are routed to a verification read or
   `blocked_manual_review` instead of a blind retry; every class touching
   a write with platform or connector-level correctness risk (userErrors,
   validation, guards, financial totals) defaults to no automatic retry.
3. **Risk:** without fixed backoff/retry-limit constants, implementation
   could under- or over-retry in practice. **Mitigation:** explicitly
   flagged `[Implementation-planning default]` rather than silently
   omitted, so the implementation-planning sprint knows a decision is still
   needed and is not tempted to invent an unverified constant here.
4. **Risk:** the `retry_waiting` / `failed_retryable` / `blocked_manual_review`
   three-way split could confuse operators if the UI does not clearly
   differentiate "system will retry" from "you need to act." **Mitigation:**
   the user-facing log requirements section makes the retry/skip/manual-
   match actions state-conditional, not a single generic "retry" button
   shown everywhere.
5. **Risk:** idempotency layers span both Shopify-provided and
   connector-designed mechanisms; a gap between them (an operation outside
   the 17-mutation list with no connector-designed key) would be a
   correctness hole. **Mitigation:** the "internal job idempotency key"
   layer prevents *connector-side* duplicate processing (re-running the
   same job twice), but it does **not**, by itself, make it safe to
   re-send a non-`@idempotent` mutation to Shopify after an
   ambiguous-outcome failure — the ambiguous-outcome rule (verification
   read before retry, or `blocked_manual_review` when the outcome cannot
   be safely verified) closes the part of the gap the internal key alone
   cannot, since Shopify does not treat those mutations as safe to replay.

## No implementation authorized

**Proposing (and any future acceptance of) this architecture decision does
not by itself authorize implementation.** This record creates no code, no
database DDL, no Python class, no Odoo module, and no file outside
`docs/03-architecture/**` and `docs/04-decisions/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force until ChatGPT accepts this record
**and** separately opens a dedicated implementation gate per
`../05-qa/quality-feedback-loop.md` §10.
