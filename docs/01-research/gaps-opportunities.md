# Gaps and Opportunities (Research Sprint C)

> Where our Odoo 19 ↔ Shopify Connector can be **better than the market**, grounded
> in the competitor evidence. Each opportunity records: **evidence · competitor
> gap · why it matters · potential direction · MVP relevance (candidate / later /
> unknown) · open questions.** **Opportunities are recommendations/inferences —
> MVP scope and architecture are NOT finalized here** (`CLAUDE.md` §4–§5; MVP =
> RB-13, architecture = RB-14, both gated). Access date 2026-06-30. Connector
> keys WK/TQ/EM/VT/EC/SH per the matrix.

## Setup simplicity opportunities

- **O-SET-1 — One-click/guided OAuth install without hand-edited server config.**
  - *Evidence:* VT has the best connect (OAuth, scope check, connection test) **but**
    requires editing `odoo.conf` (`server_wide_modules`, `queue_job channels`, ≥2
    workers) and is **not installable on Odoo Online**; EM requires pasting a long
    scope string with a trailing-slash footgun; EC gates its setup guide behind a
    sign-in wall (R5).
  - *Competitor gap:* nobody pairs **effortless install** with **real reliability**.
  - *Why it matters:* install friction is the #1 onboarding drop-off; Odoo-Online
    merchants are excluded by VT.
  - *Direction:* OAuth-first; a guided wizard that auto-checks scopes and runs a
    connection test; minimize/automate any server-config prerequisite; never gate
    the getting-started guide.
  - *MVP relevance:* **candidate** (onboarding is core). *Open Q:* can our queue
    layer avoid mandatory `odoo.conf` edits / work on Odoo Online? (ties to AR-003)

- **O-SET-2 — Pre-flight readiness check.** *Evidence:* EM's trailing-slash
  warning + VT's scope check show known failures are predictable. *Gap:* failures
  still surface late for most. *Direction:* a one-screen readiness check (scopes,
  HTTPS/`web.base.url`, webhook reachability, worker/queue presence) before first
  sync. *MVP:* candidate. *Open Q:* which checks are essential vs nice-to-have?

## UX/UI opportunities

- **O-UX-1 — Honest latency labelling + a "last synced / last reconciled"
  indicator.** *Evidence:* WK/EC/SH overstate "real-time" over cron/queue models.
  *Gap:* no connector clearly communicates actual freshness. *Why:* trust + correct
  expectations. *Direction:* per-data-type sync-mode labels + visible timestamps.
  *MVP:* candidate. *Open Q:* per-object or global freshness?
- **O-UX-2 — Progressive disclosure with inline help on jargon.** *Evidence:*
  EM/SH/WK config is toggle-dense with unexplained terms. *Gap:* approachable
  defaults + power features are not balanced. *Direction:* sensible defaults +
  an "advanced" tier + tooltips on every jargon field. *MVP:* candidate.
- **O-UX-3 — Status that encodes the fix (generalized traffic-light).** *Evidence:*
  VT webhook yellow = "check `web.base.url`". *Gap:* others give opaque/binary
  status. *Direction:* every health indicator names the cause + a fix hint.
  *MVP:* candidate. *Open Q:* taxonomy of named causes.

## Dashboard opportunities

- **O-DASH-1 — A unified command center.** *Evidence:* SH has the best monitoring
  (activity chart + failure counts), VT the best diagnostics, but **neither has
  both**; EC/VT lack a real dashboard. *Gap:* no single pane fusing connection
  health + queue status + activity timeline + quick actions + reconciliation
  status. *Why:* operators want one place to see "is everything OK, what failed,
  what do I do". *Direction:* a command center combining SH monitoring + VT
  diagnostics + a reconciliation widget. *MVP:* **candidate (differentiator).**
  *Open Q:* admin vs functional-user dashboard split.

## Logs / error / retry opportunities

- **O-LOG-1 — Recovery-first error center.** *Evidence:* EM Log Book (reason-coded)
  + SH failure counts are good; **EC is email-only** (dead-end); retries are
  mostly manual. *Gap:* no connector combines reason-coded per-record logs +
  isolated failures + **automatic retry** + one-click manual retry + a clear
  next-action. *Direction:* an error center where each failure shows record,
  reason, suggested fix, and retry — with automatic retry/backoff for transient
  errors. *MVP:* **candidate.** *Open Q:* which errors are auto-retryable vs need
  human action (taxonomy).
- **O-LOG-2 — Never email-only.** *Evidence:* EC. *Gap:* email-only recovery.
  *Direction:* in-app log is the source of truth; email/notification is an alert,
  not the only surface. *MVP:* candidate.

## Reliability opportunities

- **O-REL-1 — Idempotency + reconciliation as first-class, by default.**
  *Evidence:* VT ships GraphQL `@idempotent` (Shopify 2026-04) and webhook
  hardening; EM provides manual missed-webhook import; **Tier-1: webhook delivery
  is not guaranteed → reconciliation required; `@idempotent` required on inventory/
  refund writes from 2026-04.** *Gap:* only VT mechanizes idempotency; **nobody
  exposes a first-class, scheduled, user-visible reconciliation** ("reconcile now /
  last reconciled / drift found"). *Why:* correctness — webhook-only/no-idempotency
  designs silently drift or double-act. *Direction:* persistent idempotency keys
  on all writes + a scheduled + on-demand reconciliation job with a visible report.
  *MVP:* **candidate (core correctness).** *Open Q:* reconciliation cadence/scope;
  AR-006/AR-003.
- **O-REL-2 — Named rate-limit / GraphQL-cost-aware throttling.** *Evidence:*
  **no competitor describes one**; Tier-1: leaky-bucket (REST) + calculated cost
  (GraphQL), 429 + `Retry-After`, bulk-ops for big jobs. *Gap:* total whitespace.
  *Why:* large catalogs/orders hit limits; naive retry causes 429 storms.
  *Direction:* a cost-aware client that paces off live `throttleStatus`, backs off
  on 429/`Retry-After`, and routes big reads/writes to Bulk Operations. *MVP:*
  **candidate (resilience).** *Open Q:* per-plan bucket sizes (Tier-1 open Q).
- **O-REL-3 — Automatic retry of safe operations.** *Evidence:* only VT. *Gap:*
  others manual. *Direction:* classify operations as idempotent-safe → auto-retry
  with backoff; surface non-safe failures for human action. *MVP:* candidate.

## Duplicate-prevention opportunities

- **O-DUP-1 — Explicit, documented binding keys + a dedicated mapping model.**
  *Evidence:* EM (email link, stored-reference re-export block), SH (ID
  write-back), VT (multi-key normalized matching) — but **idempotency/dedup keys
  are mostly implicit**; Tier-1: external IDs/`ir.model.data` give a binding key
  but a per-store binding model may be needed (AR-005). *Gap:* no connector
  clearly documents its dedup keys or handles bound-record deletion. *Why:*
  duplicates / double-decrement are the classic connector defects
  (quality-feedback-loop §5). *Direction:* a per-store Shopify-GID ↔ Odoo binding
  model with documented keys + safe handling of deleted bindings. *MVP:* candidate.
  *Open Q:* `ir.model.data` reuse vs dedicated model (AR-005).

## Performance opportunities

- **O-PERF-1 — Batch + bulk + indexed mapping at scale.** *Evidence:* EM batches
  (125/50 per queue) and warns to stagger crons; **none describes Bulk Operations
  or rate-cost batching**; Tier-1: batch `create`, `_read_group`, selective
  indexes, Bulk Operations (async JSONL). *Gap:* scale strategy is shallow.
  *Direction:* batched ORM writes + indexed binding lookups + Shopify Bulk
  Operations for backfills. *MVP:* later (scale) / candidate for backfill. *Open
  Q:* bulk-op concurrency limits (Tier-1).
- **O-PERF-2 — Don't run long syncs in a request.** *Evidence:* VT uses a job
  queue; Tier-1: worker time/memory limits, Odoo.sh crons disabled on staging.
  *Direction:* chunked, queue/cron-driven sync; testable manual triggers. *MVP:*
  candidate (architecture). *Open Q:* AR-003.

## Modularity opportunities

- **O-MOD-1 — Layered, isolated addon family.** *Evidence:* VT splits into
  Integration Queue Job + E-Commerce Connector Core + the Shopify connector; EM/SH
  depend on a "base integration"/"base marketplace" module. *Gap:* monolithic vs
  fragmented both exist; Tier-1 favours link modules. *Why:* isolation from
  `adams_base`/customer code + clean Shopify/Odoo separation. *Direction:* a
  modular family (transport / mapping / orchestration / domain / UI) with link
  modules for `sale`/`stock`/`account`/`delivery`. *MVP:* unknown (boundaries =
  RB-14/AR-004, **not decided**). *Open Q:* exact module boundaries.

## Configuration / mapping opportunities

- **O-CFG-1 — Directional, testable mappings with a dry-run.** *Evidence:* VT
  (per-field direction + Python transforms + test-against-live-data + Preview/
  Report); EM (CSV fallback). *Gap:* most mappings are blind (no preview/test).
  *Direction:* directional field mapping + safe transforms + a dry-run/preview
  before any destructive apply; CSV fallback for non-SKU catalogs. *MVP:* candidate
  (mapping is core) / advanced for Python transforms.
- **O-CFG-2 — Sensible defaults to cut configuration.** *Evidence:* EM/SH config
  is overwhelming. *Direction:* opinionated defaults + an advanced tier. *MVP:*
  candidate.

## Multi-store / multi-company opportunities

- **O-MS-1 — True multi-store/multi-company with record-rule isolation +
  per-store config + clear routing.** *Evidence:* VT (multi-store + multi-company
  inventory), EM (Markets per-market company; order routing country→currency→
  fallback); **SH multi-company unverified**; Tier-1: record rules
  (global=AND/group=OR) for isolation. *Gap:* multi-company is claimed widely but
  demonstrated rarely; isolation/permissions seldom documented. *Direction:*
  per-store instance config, deterministic company/warehouse/pricelist routing,
  and record-rule-based multi-company isolation. *MVP:* later (single-store first?)
  / candidate. *Open Q:* single- vs multi-store at MVP (RB-13).

## Support / documentation opportunities

- **O-DOC-1 — Readable, screenshot-rich, non-gated docs + a dated, honest
  changelog.** *Evidence:* EM (rich, honest) + VT (dated, discloses CRITICAL
  fixes) lead; **TQ docs bot-blocked, EC no screenshots + gated setup guide, SH no
  changelog/ratings.** *Gap:* documentation/transparency is uneven and sometimes
  an evaluation blocker. *Why:* docs/changelog are trust + evaluability signals.
  *Direction:* public, screenshot-rich docs; a dated changelog that discloses
  fixes; never bot-block or sign-in-gate evaluation docs. *MVP:* candidate
  (parallel to build). *Open Q:* docs platform.

## Testing / demo opportunities

- **O-TEST-1 — A public, honest demo + a built-in self-test.** *Evidence:* TQ
  claims a demo sandbox (unverified); EC's setup is gated; Tier-1: `TransactionCase`
  for mapping, `HttpCase`/tours for webhooks/UI. *Gap:* evaluability is poor
  across the field (blocked docs, no screenshots, gated guides). *Direction:* an
  open demo + a built-in "test sync" / readiness self-check + a real test suite
  (mapping unit tests, webhook/UI tours, multi-location regression). *MVP:*
  candidate (testing is a definition-of-done requirement, `CLAUDE.md` §9). *Open
  Q:* demo hosting.
- **O-TEST-2 — Regression tests for the classic defects.** *Evidence:* VT's
  disclosed CRITICAL silent-skip/timezone bugs; quality-feedback-loop §5
  double-decrement example. *Direction:* tests for duplicate orders, multi-location
  double-decrement, missed-webhook reconciliation, timezone/paging. *MVP:*
  candidate (gates implementation).

## Premium product opportunities (differentiators)

- **O-PREM-1 — Correctness as the headline:** idempotency + reconciliation +
  rate-limit-aware throttling, **demonstrated** (not just claimed). *Evidence:*
  only VT mechanizes idempotency; nobody surfaces reconciliation or rate-limit
  handling. *MVP:* candidate (core differentiator).
- **O-PREM-2 — The best operator experience:** unified command center + recovery-
  first error center + named diagnostics + dry-runs. *Evidence:* split across
  SH/VT/EM. *MVP:* candidate.
- **O-PREM-3 — Premium breadth as optional add-ons:** payout reconciliation
  (EM-grade, demonstrated), gift cards (SH), B2B/VAT (VT), Markets (EM/VT),
  abandoned-checkout→CRM/recommendations (SH). *Evidence:* each exists in only
  1–2 competitors. *MVP:* later / optional add-ons. *Open Q:* which are core vs
  add-on (RB-13).
- **O-PREM-4 — Trust & transparency as a feature:** dated changelog disclosing
  fixes, open docs/demo, honest latency, visible reconciliation/throttle status.
  *Evidence:* VT's transparency is rewarded (300+ installs, 20 reviews); opacity
  (TQ blocked, SH no changelog) is a weakness. *MVP:* candidate (cheap, high-trust).

## Summary — top differentiation themes (inference, gated)

1. **Demonstrated correctness** (idempotency + reconciliation + rate-limit
   throttling) — the market's biggest whitespace, and Tier-1-mandated.
2. **The best operator UX** (unified command center + recovery-first errors +
   named diagnostics + dry-runs).
3. **Effortless install with real reliability** (the combination nobody has).
4. **Honesty & transparency** (latency labels, dated changelog disclosing fixes,
   open docs/demo).
5. **Premium breadth as clean add-ons** (payouts, B2B, gift cards, Markets) on a
   correct, observable core.

> None of the above is an MVP or architecture decision. MVP candidates are tagged
> for **RB-13**; architecture-bearing items route through
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (AR-002…AR-008, all evidence-pending) and **RB-14**, after ChatGPT review.
