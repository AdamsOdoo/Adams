# Public Release Closure

## Authority

- Repository: `AdamsOdoo/Adams`
- Baseline merge: `eccc498baaf65252f9febc4efdccfe9307650bf8`
- Corrective branch: `codex/public-release-closure`
- Release status: **PARTIALLY ASSURED — CORRECTIONS REQUIRED**
- Public distribution: **FROZEN**

## Release blockers

1. Guided onboarding does not reliably allow a normal administrator to activate a ready store.
2. Operator UI lacks sufficient hierarchy, clarity, progress feedback, and recovery guidance.
3. Webhook admission was proven, but end-to-end Shopify-event-to-visible-Odoo latency is not qualified.
4. Queue dispatch, concurrency, backlog recovery, rate-limit behavior, database performance, and restart recovery are not fully proven under representative load.
5. Prior release evidence over-weighted automated/backend safety and did not prove the complete user experience.

## Scope lock

This closure covers store connection, credentials, onboarding, activation, dashboard, products/variants, customers, orders, inventory, fulfillment/tracking, webhooks, scheduled reconciliation, manual synchronization, mappings, jobs/recovery, and Administrator/User/no-access roles.

No advanced refunds, payouts, subscriptions, Shopify POS, B2B, Markets, gift cards, metafields, or new feature discovery is admitted.

## Required gates

- G0 — baseline, branch, draft PR, and evidence control
- G1 — exact backend event/ownership/latency architecture map
- G2 — onboarding activation and UI correction
- G3 — webhook-first near-real-time dispatch and visible progress
- G4 — failure injection, concurrency, load, restart, and recovery
- G5 — complete live Shopify <-> Odoo workflow matrix
- G6 — security, privacy, installation, upgrade, and uninstall
- G7 — immutable exact-SHA CI, Odoo.sh, browser UAT, and Shopify read-back
- G8 — bounded independent review and controlled-release verdict

A gate failure returns only to its owning work package. The frozen exact-candidate suite and affected downstream gates must be repeated after code changes.

## Performance acceptance

| Metric | Target |
|---|---:|
| Webhook acknowledgement p95 | <= 1 second |
| Webhook acknowledgement maximum | < 5 seconds |
| Durable delivery/job creation p95 | <= 2 seconds |
| Worker start after admission p95 | <= 5 seconds |
| Shopify event to final Odoo state p95 | <= 15 seconds |
| Shopify event to final Odoo state p99 | <= 60 seconds |
| Manual action visible feedback | <= 1 second |
| UI terminal-state refresh | <= 5 seconds |
| Duplicate business mutation | 0 |
| Unexplained pending job | 0 |

## Release rule

The branch may become release-ready only when every advertised workflow has exact-build automated, backend, live Shopify, browser, latency, recovery, and read-back evidence; all queues are clean; all subscriptions are verified; and zero Critical or High defects remain.

## Evidence ledger

| Gate | Candidate | Status | Evidence |
|---|---|---|---|
| G0 | `eccc498b` baseline | Complete | PR #210 is draft, one-commit baseline, exact base `eccc498b` |
| G1 | Working candidate | In progress | Static event/latency trace recorded in `backend-responsiveness-architecture.md`; exact runtime timing remains open |
| G2 | Working candidate | In progress | Activation follower, reachable Check status, one-minute fallback and upgrade migration implemented locally; exact tests pending |
| G3 | Pending | Not started | Enqueue wake-up exists; priority/backlog and live latency remain unproved |
| G4 | Pending | Not started | |
| G5 | Pending | Not started | |
| G6 | Pending | Not started | |
| G7 | Pending | Not started | |
| G8 | Pending | Not started | |
