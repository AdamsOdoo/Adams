# Screen spec — Jobs, retry & diagnostics (+ global state gallery)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline; design artifact only — **no
> implementation is authorized**, UI-U1/U2/U3 stay CLOSED. Source:
> `jobs-diagnostics.html` (+ `../assets/prototype.css` + a small
> screen-local `<style>` block, token values only). Copy is illustrative
> (MBQ-22). Two-role model (Connector User / Connector Administrator) —
> itself Proposed.

## Purpose

Answer "what is the sync engine doing, what needs me, and is the machinery
itself healthy?" — the job list with per-row recovery actions, the honest
diagnostics panel, and the canonical eleven-state gallery every other
surface must express consistently.

## Primary role

**Connector User.** Jobs/logs viewing, retrying eligible jobs, cancelling
non-terminal jobs, and resolving manual-review cases are User capabilities
(roles doc §1.1); eligibility is always server-side error-class-gated
(DEC-003/DEC-009) — the UI only surfaces what the server permits.
Administrator additionally reaches raw-payload diagnostics (noted in the
log drawer, not rendered).

## Data shown

- **Jobs table** — type + subject, store, state badge, attempts (n of max),
  next-retry countdown, truncated idempotency key, connection generation,
  one action. All **10 job states** appear across the rows, as words
  (internal tokens live only in this spec):

  | Internal token | UI word | Family |
  | --- | --- | --- |
  | `draft` | Draft | neutral |
  | `queued` | Queued | neutral |
  | `running` | Running | info |
  | `succeeded` | Succeeded | success |
  | `failed_final` | Failed — final | danger |
  | `skipped` | Skipped (policy) | neutral |
  | `cancelled` | Cancelled | neutral |
  | `retry_waiting` | Retrying soon | warning |
  | `failed_retryable` | Failed — will retry | warning |
  | `blocked_manual_review` | Needs review | **danger** (accepted token map; hand icon + reviewer owner + decision language distinguish it from `failed_*` without color — U0 P12 posture) |

- **Diagnostics panel** — cron health with the honesty card ([Fact] Odoo
  `ir.cron` auto-deactivates a job only after **5 failures across ≥7 days**
  — too coarse to be the user's safety net, so the connector watches every
  run: DEC-005/DEC-009, Area-6 packet), queue depth (waiting/running/oldest),
  throttle status (cost-based leaky bucket, paced wording), API version
  (pinned 2026-07) with the **falls-forward** warning ([Fact] Shopify
  responds with the oldest accessible stable version when the pinned one is
  retired — source captures / rb14 refresh).
- **Log drawer** — append-only entries (read-only for all roles —
  [Fact — repo] job logs are read-only in the shipped ACLs), plain-language
  lines, redaction note (PII redacted at write time; raw payload
  Administrator-only).

## Actions per role

| Action | Connector User | Connector Administrator |
| --- | --- | --- |
| View jobs, logs, diagnostics | Yes | Yes |
| Retry | Yes — only rows the server marks retry-eligible (`failed_final` after review, `failed_retryable` "Retry now") | Yes |
| Cancel | Yes — non-terminal rows only (`queued`/`running`/`retry_waiting`), via the reason drawer; reason audited | Yes |
| Resolve manual review | Yes — via the resolve drawer routing to the matching/review screen; decision audited who/when/what | Yes |
| Edit/delete a log entry | Never (append-only for every role) | Never |
| Raw payload / connection tooling | No | Yes (diagnostics, not rendered here) |

**Resolve drawer — the six manual-review sub-reasons** (accepted vocabulary;
UI words with internal tokens spec-only): Ambiguous match
(`ambiguous_match`), Binding conflict (`binding_conflict`), Duplicate risk
(`duplicate_risk`), Destructive write blocked
(`destructive_write_guard_blocked`), Inventory location missing
(`inventory_location_missing`), Notification confirmation missing
(`fulfillment_notification_confirmation_missing`).

## States rendered

1. **Normal** — 10-row table covering all ten job states + healthy
   diagnostics trio.
2. **Cancel reason drawer** — consequences stated (stops before next
   attempt; nothing undone; rescannable), reason field, danger-styled
   confirm.
3. **Resolve manual-review drawer** — six sub-reasons table with the active
   case highlighted; primary action routes to the matching screen.
4. **Log drawer** — append-only timeline + redaction note.
5. **Backlog-heavy** — warning band ("nothing is lost"), queue 312 waiting,
   throttle "Paced", cron explicitly healthy ("backlog is demand, not a
   scheduler fault"); reconnect catch-up priority explained (live first,
   backfill lower priority — reconnect policy §5.5).
6. **Offline banner** — danger band, hold-don't-fail posture, next
   automatic attempt countdown, last-known-data freshness label.
7. **Unknown-schema banner** — pinned 2026-07 vs responding 2026-10;
   fail-closed: unverified shapes route to review, never guessed.
8. **Global state gallery** — the 11 canonical states as compact labeled
   reference cards: empty, loading, warning, success, failure, offline,
   reconnecting, stale, delayed, partial, unknown-schema — each with the
   badge treatment and a one-line behavioral contract.

## Tokens used

Table = `.sc-list` (exception rows `has-exception` → danger tint); state
badges = `.sc-status--{success|warning|danger|info|neutral}`; countdowns and
keys are tabular-numeric (`.sc-mono`, `.jd-key` caption size); drawers =
`.sc-dialog` (single elevated surface); bands per family; gallery cards are
1px-border tokens-only (`.jd-state`). Truncated idempotency keys use an
ellipsis — full keys are never needed on screen. Manual review uses the
danger family with the hand icon per the accepted §6 token map.

## Accessibility

- Every state is a word + icon, never color alone (WCAG 1.4.1); manual
  review vs technical failure are distinguished by icon/owner/language.
- Drawers: `role="dialog"` `aria-modal="true"`, labelled headings;
  destructive confirm last in focus order.
- The jobs table scrolls inside its own `overflow-x:auto` container; ≤ 640px
  the shared stylesheet hides optional columns (`col-ref`, `col-source`)
  keeping subject + state + action visible.
- Log drawer content is plain language (no raw HTTP codes as primary copy);
  skeletons/spinners respect `prefers-reduced-motion`.
- Gallery grid reflows 4 → 2 → 1 columns; RTL via logical properties.

## Traceability

- 10-state job vocabulary + retry/cancel backend: JOB-ACTIONS packet
  (capability map row 16, Merged-Wave-1 backend / UI not started) and
  DEC-009 error/retry taxonomy; retry eligibility server-side
  error-class-gated per roles doc §1.1 [Fact — repo posture].
- Six manual-review sub-reasons: accepted review vocabulary (roles doc
  §1.1 "the six accepted manual-review sub-reasons"; DEC-009 audit
  posture who/when/what).
- Idempotency key / operation-scope enqueue dedup + generation fencing:
  [Fact — repo] via
  [`reconnect-catchup-backfill-policy.md`](../../02-product/reconnect-catchup-backfill-policy.md)
  §3.3 and §2 step 7 (stale-generation refusal).
- Cron honesty card: [Fact] `ir.cron` deactivation math (5 failures/≥7
  days) — DEC-005 §, DEC-009 §, Area-6 packet; recovery-first posture.
- Throttle: [Fact] cost-based rate limit with `throttleStatus` backoff
  (source captures §11, cited by the reconnect policy §5.5).
- API version falls-forward: [Fact] Shopify falls forward when a pinned
  version is inaccessible (rb14-official-source-refresh; shopify-official
  capture). Fail-closed unknown-schema handling is [Recommendation]
  consistent with the accepted nine-element error contract.
- Append-only, redacted logs: [Fact — repo] read-only job-log ACLs;
  `_system_append` redaction posture (Task 014 §4 reference in the
  fulfillment modes doc §8).
- 11-state global vocabulary: the U0 five-state model (loading / empty /
  success / degraded / manual-review) extended per the accepted honesty
  laws (stale/delayed/partial/offline/reconnecting/unknown-schema);
  the extension is **[Recommendation]** for control-room acceptance, not
  a silent change to the accepted five-state contract.
