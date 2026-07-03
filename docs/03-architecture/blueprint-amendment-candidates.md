# Blueprint Amendment Candidates (non-binding)

> **This file amends nothing.** It is a **candidate register only**, produced by
> the Competitor Evidence & Blueprint Reconciliation Sprint. It records where the
> competitor evidence *might* imply a future change to accepted work, so ChatGPT
> can decide — **after reviewing the evidence pack** — whether any accepted work
> needs revision before Part D, or whether it is safe to proceed. Per
> `CLAUDE.md` §5/§8/§10 and the sprint's hard rules:
>
> - **No accepted decision is modified.** DEC-003 through DEC-015 are untouched.
> - **Nothing here is marked accepted.** Every row is a *candidate*, class
>   `[Recommendation / Open question]`, never `[Decision]`.
> - **No DEC-016, no AR-013, no MBQ resolution, no new master-blueprint file** is
>   created by this sprint.
> - **No rejected approach (RA-001…RA-023) is re-proposed.** Each candidate was
>   checked against
>   [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md);
>   see the guardrail note at the end.
> - The no-code / research-first gate (`CLAUDE.md` §4–§5) is in force;
>   implementation stays blocked.
>
> **Source evidence:**
> [`../01-research/competitor-gap-analysis-against-blueprint.md`](../01-research/competitor-gap-analysis-against-blueprint.md),
> [`../01-research/competitor-feature-screen-map.md`](../01-research/competitor-feature-screen-map.md),
> [`../01-research/competitor-evidence-reconciliation.md`](../01-research/competitor-evidence-reconciliation.md).
> **Date:** 2026-07-03.

## How to read a candidate

Each `BAC-###` records: **related accepted DEC/blueprint · competitor evidence or
gap that triggered it · why it may matter · suggested action · risk if ignored ·
recommendation.** The **suggested-action** vocabulary is fixed:

- **No amendment needed** — the blueprint already covers it; recorded for
  traceability only.
- **Part D input only** — feeds the (gated) Part D UI/UX Screen Design Blueprint;
  no change to any accepted decision.
- **Future MBQ** — a candidate new open question for a later sprint to register
  (this sprint does **not** register it).
- **Future DEC amendment** — would require a future ChatGPT-reviewed decision
  record (none is created here).
- **Future implementation-planning item** — belongs to the later gated
  implementation-planning bridge (Part E).

---

## Candidate register

### BAC-001 — Dashboard activity trend vs "no vanity-only metrics"
- **Related accepted work:** DEC-013 §F (recovery-first dashboard, §F.4 "no
  vanity-only metrics"); DEC-012 flow 3.
- **Trigger evidence:** SH exposes a **"Daily Queue Activity Tracking" time-series
  chart** (caption-only); it is the one competitor dashboard element that goes
  slightly beyond DEC-013 §F's exception-first, action-only card set.
- **Why it may matter:** a bounded throughput/activity trend *can* be a genuine
  health signal (spotting a stalled queue or a drop in sync volume), but it could
  also read as a "vanity metric" that DEC-013 §F.4 deliberately excludes.
- **Suggested action:** **Part D input only** — Part D should decide whether a
  *bounded, health-bearing* activity trend is admissible under §F.4, without
  amending §F.4's principle.
- **Risk if ignored:** Part D either omits a useful signal or contradicts §F.4 ad
  hoc.
- **Recommendation:** treat as a Part D design question; no amendment.

### BAC-002 — Mapping "test against live data" surface
- **Related accepted work:** DEC-013 §D.2 (`export_preview_dry_run` read-only job);
  DEC-012 flows 6/7 (matching/product preview).
- **Trigger evidence:** VT offers **"test field mappings against live data before
  applying"** — a mapping-validation surface distinct from a per-export dry-run.
- **Why it may matter:** premium mapping UX (`O-CFG-1`) may want to *test a mapping
  configuration* against live data, not only preview a specific export.
- **Suggested action:** **Part D input only** (screen), with a possible
  **future implementation-planning item** for the read path.
- **Risk if ignored:** mapping errors surface only at export time, not at config
  time.
- **Recommendation:** Part D input; no amendment (the dry-run behaviour already
  exists).

### BAC-003 — CSV/XLSX matching fallback for non-SKU catalogs
- **Related accepted work:** DEC-006 / DEC-013 §C.5 (match keys binding→SKU→
  barcode→manual); DEC-014 §A.6.
- **Trigger evidence:** EM offers a **CSV/XLSX product-map fallback** for catalogs
  that cannot be matched on SKU/barcode.
- **Why it may matter:** merchants with poor SKU hygiene cannot be auto-matched;
  a manual bulk-map file is a pragmatic escape hatch.
- **Suggested action:** **Future MBQ** (non-MVP) — candidate later-phase capability,
  not part of the accepted MVP match-key set.
- **Risk if ignored:** a real onboarding edge case (no clean keys) is unaddressed
  — but only for later phases; MVP manual matching still covers it per-record.
- **Recommendation:** do **not** add to MVP; note as a future MBQ for a later
  sprint to register. **Must not** weaken RA-006 (name-only matching stays
  rejected) — a CSV map is an explicit operator-provided mapping, not name
  inference.

### BAC-004 — Local pickup / click-and-collect order-status handling
- **Related accepted work:** DEC-011 / DEC-012 flow 9 (fulfillment via
  FulfillmentOrder); DEC-003 (fulfillment scope).
- **Trigger evidence:** TQ demonstrates a **click-and-collect lifecycle**
  (Ready-for-Pickup → Picked-Up) as first-class order status.
- **Why it may matter:** local-pickup/local-delivery FulfillmentOrders have a
  distinct status lifecycle the current fulfillment blueprint does not call out.
- **Suggested action:** **Future MBQ** / future scope note — not MVP.
- **Risk if ignored:** pickup orders may route to manual review as "unexpected"
  rather than being handled as a known lifecycle; acceptable for MVP.
- **Recommendation:** record as a future-phase consideration; no MVP or Part D
  obligation. Does not conflict with RA-022/RA-023 (still FulfillmentOrder-based).

### BAC-005 — Traffic-light health indicator with named diagnostic + fix hint
- **Related accepted work:** DEC-013 §B.3 (API/connection health state + plain
  reason), §H (error center); DEC-012 flow 3.
- **Trigger evidence:** VT's **webhook traffic-light** (yellow = "callback-URL
  mismatch, check `web.base.url`") — the best status-indicator pattern of the
  survey (`O-UX-3`).
- **Why it may matter:** DEC-013 fixes the health *state and reason* as behaviour;
  the premium *visual* realization (colour + named cause + fix hint) is a Part D
  screen decision.
- **Suggested action:** **Part D input only.**
- **Risk if ignored:** a generic health badge underdelivers vs the market's best.
- **Recommendation:** Part D should match/exceed VT's diagnostic-specific pattern;
  no amendment.

### BAC-006 — Progressive-disclosure requirement for dense config
- **Related accepted work:** setup-ux P3 (progressive disclosure); DEC-012 store-
  settings flow; DEC-013 §I.
- **Trigger evidence:** EM/TQ/SH config is **toggle-dense** (10+ toggles,
  dev-mode-gated) — the survey's clearest UX cautionary example (`A-UX-3`).
- **Why it may matter:** premium UX is a product pillar; Part D must not reproduce
  the dense single form.
- **Suggested action:** **Part D input only.**
- **Risk if ignored:** onboarding drop-off; non-premium feel.
- **Recommendation:** Part D applies progressive disclosure + defaults + inline
  help; no amendment.

### BAC-007 — First-push safety screen (market whitespace)
- **Related accepted work:** DEC-007 §4 / DEC-010 / DEC-012 flow 8 (mandatory
  first-push guard); MBQ-38 (confirmation-record schema, open).
- **Trigger evidence:** **No competitor** exposes a first-push safety screen; our
  blueprint mandates the guard behaviour but has no screen design.
- **Why it may matter:** the first-push guard is a **named differentiator**; its
  premium screen realization is the visible proof of the correctness core.
- **Suggested action:** **Part D input only** (screen), with the confirmation-
  record schema as a **future implementation-planning item** (MBQ-38).
- **Risk if ignored:** the differentiator ships as a bare confirmation dialog and
  loses its premium impact.
- **Recommendation:** Part D must design the first-push preview + confirm +
  recorded-source-of-truth screen as a flagship surface; no amendment.

### BAC-008 — Reconciliation status surface ("last reconciled / drift found")
- **Related accepted work:** DEC-005 / DEC-013 §D.1 (first-class reconciliation),
  §F (dashboard); MBQ-17 (cadence/scope, open).
- **Trigger evidence:** **No competitor** surfaces first-class reconciliation
  (`O-REL-1`); TQ has cursors + per-return resync only; EM manual re-import.
- **Why it may matter:** reconciliation is the mandatory correctness backstop;
  making it *visible* ("last reconciled at X; N drifts found") is premium
  whitespace.
- **Suggested action:** **Part D input only.**
- **Risk if ignored:** the correctness backstop runs invisibly and the
  differentiation is lost.
- **Recommendation:** Part D adds a reconciliation status widget; cadence stays
  MBQ-17; no amendment.

### BAC-009 — Rate-limit / throttle status visibility
- **Related accepted work:** DEC-004 / DEC-013 §B.3 (health state incl.
  throttled/degraded); MBQ-51 (pacing params, open).
- **Trigger evidence:** **No competitor** exposes rate-limit/cost handling
  (`O-REL-2`); DEC-013 §B.3 explicitly keeps *raw* GraphQL cost numbers out of the
  UI, surfacing only a health state.
- **Why it may matter:** showing an honest "throttled — syncs are pacing" state
  (not raw cost) builds trust during large syncs; the exact user-facing surface is
  undecided.
- **Suggested action:** **Part D input only** (what to show), with pacing params as
  a **future implementation-planning item** (MBQ-51).
- **Risk if ignored:** large-sync throttling looks like a stall with no explanation.
- **Recommendation:** Part D designs an honest throttle state; keep raw cost hidden
  per §B.3; no amendment.

### BAC-010 — Premium breadth as later add-ons (payouts / Markets / B2B / gift cards)
- **Related accepted work:** DEC-003 non-goals (all as premium add-ons / later);
  `O-PREM-3`.
- **Trigger evidence:** EM/TQ demonstrate **payout reconciliation** (Shopify-
  Payments-only); EM/VT/TQ Markets; VT B2B; SH gift cards.
- **Why it may matter:** these are demonstrated market capabilities and future
  differentiators, but each is already a **confirmed DEC-003 deferral**.
- **Suggested action:** **No amendment needed** — recorded to confirm the
  deferrals are evidence-backed, not oversights.
- **Risk if ignored:** none for MVP; loss only if later phases forget the demand
  signal (captured here and in `O-PREM-3`).
- **Recommendation:** keep deferred; revisit as feature-flagged add-ons post-MVP.
  Payout features must stay gated to Shopify Payments (`A-PAY-1`).

### BAC-011 — Strong-confirmation UX for irreversible actions
- **Related accepted work:** DEC-012 (destructive-write guard, `blocked_manual_
  review`, audit); DEC-013 §D.10.
- **Trigger evidence:** EM **Force Done** (irreversible), TQ **Force Restock**,
  VT **Force Full Fulfillment** — powerful footguns with uneven guarding
  (`A-RET-2`).
- **Why it may matter:** the blueprint guards destructive writes at the *behaviour*
  level; the *confirmation UX* (warning copy, reversibility, before/after) is a
  Part D screen concern.
- **Suggested action:** **Part D input only.**
- **Risk if ignored:** accidental data loss / stuck queues from weak confirmation.
- **Recommendation:** Part D designs strong-confirmation dialogs with before/after
  and clear reversibility; no amendment.

### BAC-012 — "Needs re-export" / stale-recovery affordance
- **Related accepted work:** DEC-013 §C.6 (stale binding), §D.8 (`blocked_manual_
  review`), reconciliation.
- **Trigger evidence:** SH's **"Needs Shopify Re-Export"** recovery flag
  (auto-cleared after sync) is a clean recovery affordance.
- **Why it may matter:** our blueprint covers the *state* (stale binding +
  manual-review + reconciliation) but not a dedicated one-glance recovery
  affordance.
- **Suggested action:** **Part D input only** — Part D decides whether the sync/
  error center surfaces an explicit "needs re-sync" affordance derived from the
  existing states.
- **Risk if ignored:** recovery is available but less discoverable than SH's flag.
- **Recommendation:** Part D surfaces it from existing states; no new state, no
  amendment (avoids RA-013 parallel-substrate).

---

## Summary

| Candidate | Suggested action | Amends an accepted decision? |
| --- | --- | :--: |
| BAC-001 dashboard activity trend | Part D input only | No |
| BAC-002 mapping test-against-live-data | Part D input only | No |
| BAC-003 CSV/XLSX match fallback | Future MBQ (non-MVP) | No |
| BAC-004 click-and-collect status | Future MBQ / scope note | No |
| BAC-005 traffic-light health indicator | Part D input only | No |
| BAC-006 progressive disclosure | Part D input only | No |
| BAC-007 first-push safety screen | Part D input only | No |
| BAC-008 reconciliation status surface | Part D input only | No |
| BAC-009 throttle status visibility | Part D input only | No |
| BAC-010 premium breadth add-ons | No amendment needed | No |
| BAC-011 irreversible-action confirmation UX | Part D input only | No |
| BAC-012 needs-re-export affordance | Part D input only | No |

**Total candidates: 12.** **Requiring a DEC amendment: 0.** **Requiring an AR
change: 0.** **Requiring an MBQ resolution: 0** (BAC-003/004 propose *future* MBQ
rows for a later sprint to register, not resolved here). **Predominant action:
Part D input only.**

> **Net signal for ChatGPT (inference):** the competitor evidence **validates**
> the accepted blueprint and requires **no revision of any accepted decision**
> before Part D. The candidates are almost entirely Part D screen-design inputs,
> with two future-phase notes (BAC-003, BAC-004) and one confirmed-deferral
> record (BAC-010). **It appears safe to proceed to Part D after ChatGPT reviews
> this evidence pack.**

## Guardrail note — no rejected approach re-proposed

Every candidate was checked against RA-001…RA-023 (all binding-final). None
re-proposes a rejected approach:

- **BAC-003** (CSV/XLSX map) is an **explicit operator-provided** mapping, **not**
  name-only automatic matching — RA-006 stays rejected and untouched.
- **BAC-004** (pickup status) stays **FulfillmentOrder-based** — RA-022 (legacy
  API) and RA-023 (fulfill-by-order-ID-alone) stay rejected and untouched.
- **BAC-008/009** (reconciliation/throttle surfaces) are **read-only status
  displays** over existing accepted mechanisms — they do not touch RA-014/RA-015
  (retry posture) or RA-020 (autonomous conflict resolution).
- **BAC-010** (breadth add-ons) are **DEC-003 deferrals**, not the rejected
  accounting-automation default (RA-010) — payout stays Shopify-Payments-gated.
- **BAC-012** (needs-re-export) reuses existing states, adding **no parallel
  substrate** — RA-013 stays honoured.

No `DEC-016`, no `AR-013`, no MBQ status change, and no accepted-decision edit is
made by this file.
