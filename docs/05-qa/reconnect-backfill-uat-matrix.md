# Reconnect / Catch-Up / Backfill UAT Matrix

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** Companion QA deliverable of
> [`../02-product/reconnect-catchup-backfill-policy.md`](../02-product/reconnect-catchup-backfill-policy.md)
> (the RB policy; PD-RB-1..9). Each per-domain "must NOT happen" in RB §4 has
> at least one negative case here, per RB §9. Order catch-up/backfill cases
> execute with Wave 2; inventory Wave 3; fulfillment Wave 4; product-export
> Wave 5; the consolidated live run is Wave 6.
>
> **[Product-direction update — 2026-07-16] Dev-store evidence rule.** Odoo.sh
> evidence is mandatory for every wave. The **read-only** order catch-up /
> backfill dev-store UAT (Wave 2) is strongly preferred but is **not a Wave 2
> merge blocker** — if read-only Shopify credentials are unavailable it defers
> to the Wave 6 consolidated run (VAL-B2 not presented as completed). The
> mutation domains (inventory Wave 3, fulfillment Wave 4, product-export
> Wave 5) and the Wave 6 run keep their genuine dev-store mutation-evidence
> requirement.

## Shared conventions

- **Environment:** Odoo.sh build + dev store; a store that can be
  disconnected (credential clear) and reconnected; seeded per-domain
  watermarks; test data changed **while disconnected** per case.
- **Roles:** reconnect initiation and backfill are Administrator-only;
  Users observe progress and work review queues.
- **Universal pass criteria:** no historic job is replayed (PD-RB-1/2);
  no store lifecycle state beyond the shipped five appears (PD-RB-3);
  every count shown to the operator reconciles against seeded data.

## 1. Reconnect sequence (the eight steps)

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-RB-1.1 | Eight-step verification | Disconnect; reconnect with valid credentials; observe the sequence | All eight RB §2 steps observable in order: credential probe → scope diff → API-version check → readiness re-run → new `connection_generation` → historic jobs preserved as evidence → stale-generation refusal armed → fresh per-domain catch-up scans enqueued (the only source of post-reconnect work) |
| UAT-RB-1.2 | Scope-loss surfacing | Reconnect with a token missing a previously granted scope (e.g. `read_all_orders`) | The scope diff surfaces the loss before the store is declared `connected`; affected domain flagged; no silent degradation |
| UAT-RB-1.3 | API-version mismatch | Reconnect against a store mirroring a version ≠ pinned 2026-07 (falls-forward condition) | Readiness compares mirrored vs pinned and raises a warning; no mutation domain resumes on an unverified version |
| UAT-RB-1.4 | Stale-generation fencing | Leave jobs enqueued under the old generation; reconnect; attempt to run them | Admission refuses every stale-generation job; they route to the historic sink, never execute; `action_reconnect` itself refuses to complete if the epoch changed mid-flight |
| UAT-RB-1.5 | Historic preservation | After reconnect, inspect prior-generation jobs/logs/bindings/settings | Everything preserved unmodified (audit trail, never an execution queue); only new disconnect/reconnect audit entries added |

## 2. Per-domain catch-up correctness (with overlap dedup)

Setup per case: record the domain watermark; disconnect; make the listed
remote changes; reconnect; observe the domain scan.

| ID | Domain | Disconnected-period changes | Pass criteria |
| --- | --- | --- | --- |
| UAT-RB-2.1 | Products | 1 new product, 1 edited bound product, 1 touch-only change (unmapped field), 1 variant-set restructure | Scan filters `updated_at:>{watermark−overlap}`; counts new=1 / changed=1 / skipped≥1 (hash short-circuit for touch-only) / needs-review=1 (restructured variants); catch-up never mutates Shopify |
| UAT-RB-2.2 | Customers | 1 new customer, 1 bound customer edited remotely AND locally, 1 remote merge event | New imports; both-sides-changed → review; merge → review, **no automatic partner merge**; PII redaction posture holds in the review queue |
| UAT-RB-2.3 | Orders | 1 new eligible order, 1 bound order edited (`orders/edited`), 1 bound order cancelled, 1 COD order collected remotely | New order imports once; edited/cancelled/COD-diverged orders arrive as *changed* and route per the order/COD policies (review where Odoo progressed); **no automatic full-history import; no confirmation-policy bypass for caught-up orders** |
| UAT-RB-2.4 | Overlap dedup (all domains) | Run a second scan immediately after the first (records inside the overlap window) | Records with `updatedAt ≤` last-synced version skip; equal-hash records skip with binding timestamp refresh; **zero duplicate records and zero duplicate jobs** for the same observed version (PD-RB-5/6); one active scan per store×domain (scope-key no-op on re-trigger) |
| UAT-RB-2.5 | Watermark advance/hold-back | Force a scan to fail mid-run (fault injection); then complete a clean scan | Failed/partial scan **never advances** the watermark; the retried scan re-covers the window; dedup absorbs re-reads; clean completion advances the watermark |
| UAT-RB-2.6 | Inventory — no blind push | Pre-disconnect pending push targets exist; remote quantities changed while disconnected | First post-reconnect inventory action is a reconciliation **read** of all mapped pairs; pushes resume only with fresh `compareQuantity` bases; no pre-disconnect computed quantity is pushed |
| UAT-RB-2.7 | Fulfillment — no blind create replay | Queued outbound fulfillment interrupted by disconnect; external fulfillment created during the gap | Queued outbound re-verifies FO remaining quantities before executing (skip/shrink); the gap-period external fulfillment lands as a review case in both modes (see [`fulfillment-mode-uat-matrix.md`](./fulfillment-mode-uat-matrix.md) UAT-FM-3.5) |
| UAT-RB-2.8 | Product export — no resumed write before verification | Bound exported product edited in Shopify while disconnected | Export reconciliation pass re-reads each exported binding before any export resumes; divergence → review (ownership policy), deletion → review, identical → resume; exports blocked for the store until the pass completes |
| UAT-RB-2.9 | Disconnected-period external changes (integration) | Combine: one order edited+fulfilled externally+COD-collected while disconnected | The order arrives as one *changed* record; the fulfillment classifies per operating mode; the COD divergence follows COD scenario 16 — one coherent review picture, no duplicate effects |

## 3. Order backfill (Administrator wizard, preview-first)

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-RB-3.1 | Preview count accuracy | Seed a date range with known composition (e.g. 10 new, 3 changed, 5 already-bound duplicates, 2 ineligible-skip, 1 ambiguous-customer); run the preview | Read-only scan reports exactly new=10 / changed=3 / duplicate=5 / skipped=2 / needs-review=1 using the §3.4 skip logic; **no job and no record created** by the preview; samples shown; enqueue only on explicit confirm |
| UAT-RB-3.2 | 60-day boundary, `read_all_orders` absent | Request a range extending beyond 60 days on a token without `read_all_orders` | Wizard states the limitation **before scanning**, shows the reachable sub-range, links the Partner-Dashboard approval path; never silently truncates ([Fact] 60-day rule — RB §4.3/§5.2) |
| UAT-RB-3.3 | 60-day boundary, `read_all_orders` present | Same range with the approved scope | Full range scans; preview covers the whole window |
| UAT-RB-3.4 | Duplicate-safe re-run | Confirm and complete a backfill; re-run the identical range | Second run's preview shows the prior imports as duplicates; confirming it creates **zero** duplicate sale orders (binding dedup + per-record idempotency keys) |
| UAT-RB-3.5 | Resumability | Interrupt a running backfill (worker kill / disconnect) mid-range | Progress tracked per page-window; resume starts from the last completed window; re-scanned records absorbed by dedup; a disconnect-interrupted backfill is generation-fenced and requires a **fresh preview + re-confirmation** after reconnect |
| UAT-RB-3.6 | Policy parity | Backfill COD and pending-payment orders | Backfilled orders obey the same confirmation policy and COD rules as live imports — no policy bypass (RB §5.7); throttle-aware paging observed (`throttleStatus` backoff, lower priority than live sync) |
| UAT-RB-3.7 | Role gate | As Connector User, attempt to open/confirm the backfill wizard | Refused server-side; Administrator-only (PD-RB-8) |

## 4. Onboarding initial-import windows

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-RB-4.1 | Defaults | Activate a fresh store with default choices | Products: full catalog; orders: recent 30 days; inventory: baseline reconciliation read; abandoned checkouts: none (feature off) — per PD-RB-9 table |
| UAT-RB-4.2 | Order-window cap | Select a custom order window >60 days without `read_all_orders` | Same honesty behavior as UAT-RB-3.2 at onboarding time; ≤60-day windows import normally |
| UAT-RB-4.3 | Watermark seeding | Complete initial import; observe subsequent incremental scans | Each domain's watermark is seeded from the completed scan; the first incremental scan picks up only post-import changes (plus overlap re-reads absorbed by dedup) |
| UAT-RB-4.4 | "None" options | Choose products=none (export-first store) and orders=none | Nothing imports for the opted-out domains; no error states; domains can be back-filled later via the controlled paths |

## Evidence to capture

Per case: the reconnect/catch-up progress UI (per-domain scanned / new /
changed / skipped / needs-review counts); the backfill preview screen with
counts and access-window notice; job lists showing generation tags and
idempotency keys; watermark records before/after; review-queue contents;
proof-of-absence queries for duplicates (order count per Shopify GID = 1).

## Open items

- [Open question — OQ-RB-1] The 30-minute overlap default is engineering
  judgment; UAT-RB-2.4/2.5 evidence feeds its validation.
- [Open question — OQ-RB-5] If `read_all_orders` approval is unobtainable
  for the custom-app posture, UAT-RB-3.3 is recorded as not-executable and
  the >60-day path's honest degradation (UAT-RB-3.2) becomes the release
  behavior.
- [Open question — OQ-RB-2] Remote-deletion detection is out of these
  cases' scope (no `updated_at` signal); its cadence is undefined by the RB
  policy and must not be asserted in any pass criterion.
