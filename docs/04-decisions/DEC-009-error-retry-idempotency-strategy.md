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

**Job states:** `draft` → `queued` → `running` → one of `succeeded`,
`retry_waiting`, `failed_retryable`, `failed_final`, `skipped`,
`cancelled`, `blocked_manual_review` (full transition table in the brief
§2).

**Error classes (16):** Shopify throttling/rate-limit; Shopify temporary/
server/network; Shopify permission/scope/auth; Shopify userErrors/
validation; Odoo validation/configuration; mapping missing; ambiguous
match; binding conflict; duplicate risk; destructive-write guard blocked;
inventory location missing; fulfillment notification confirmation missing;
financial total mismatch; data shape/schema mismatch; concurrency/race
conflict; unknown/system error (full mapping to grounding + default
behaviour in the brief §3–4).

## Retry taxonomy

- **Automatic retry:** Shopify throttling/rate-limit; Shopify temporary/
  server/network; concurrency/race conflict.
- **No automatic retry (manual fix then retry):** Shopify permission/
  scope/auth; Shopify userErrors/validation; Odoo validation/configuration;
  mapping missing; data shape/schema mismatch.
- **Operator confirmation required (`blocked_manual_review`):** ambiguous
  match; binding conflict; duplicate risk; destructive-write guard blocked;
  inventory location missing; fulfillment notification confirmation
  missing.
- **No automatic retry, conservative-by-default:** financial total
  mismatch (DEC-007 §6 — never silently create a mismatched artifact).
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
- Reconciliation cadence and scope — `[Open question]`, deferred to
  implementation planning.
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
   to prevent. **Mitigation:** only three classes (throttling, temporary/
   network, concurrency) are auto-retryable, all three grounded in cited
   Shopify facts about their transient, retry-intended nature; every class
   touching a write with platform or connector-level correctness risk
   (userErrors, validation, guards, financial totals) defaults to no
   automatic retry.
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
   layer is explicitly proposed to cover every operation, not just the
   17-mutation list, closing that gap by design.

## No implementation authorized

**Proposing (and any future acceptance of) this architecture decision does
not by itself authorize implementation.** This record creates no code, no
database DDL, no Python class, no Odoo module, and no file outside
`docs/03-architecture/**` and `docs/04-decisions/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force until ChatGPT accepts this record
**and** separately opens a dedicated implementation gate per
`../05-qa/quality-feedback-loop.md` §10.
