# Rejected Approaches Log

> Captures approaches we **explicitly decided not to use**, so they are not
> reintroduced later. Per `CLAUDE.md` §10, before proposing any architecture or
> implementation approach, **check this log** — do not re-propose a rejected
> approach unless its **Future revisit condition** is met (and say so).

## How to use

1. Add a row whenever an approach is rejected (in design, review, or
   implementation).
2. **Why rejected** + **Evidence / reasoning** must be concrete enough that a
   future session understands the rejection without re-deriving it.
3. **Future revisit condition** states the specific change that would make the
   approach worth reconsidering. If revisiting, route via the
   [architecture-review log](./architecture-review-log.md).
4. Link the accepted alternative's ADR in **Related decision record**, if any.

---

## Log

| ID | Date | Rejected approach | Why rejected | Evidence / reasoning | Future revisit condition | Related decision record |
| --- | --- | --- | --- | --- | --- | --- |
| _RA-000_ | _YYYY-MM-DD_ | _Approach we will not use_ | _Core reason_ | _Concrete evidence/reasoning_ | _What would change our mind_ | _ADR link, if any_ |
| RA-001 | 2026-07-01 | **Option C — Thin import-only pilot** as the MVP scope (import + manual sync only; no webhooks/reconciliation/write-back) | Violates the correctness non-negotiables — a webhook-less/cron-only sync with no reconciliation is a demonstrated market anti-pattern (`../01-research/avoid-list.md`); removes the back-office value; "small but not excellent" | Evaluated as an MVP-scope option alongside Option A (accepted) during RB-13 and explicitly rejected by ChatGPT in the DEC-003 decision record | Would need a documented reason the correctness spine (webhooks + reconciliation + write-back) is infeasible for the MVP substrate — no such evidence exists today | [`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md) ("Accepted MVP option" section) |

_No approaches rejected yet (Research Sprints A–C). Entries begin once design
options are evaluated and ChatGPT/architecture review formally rejects one._

_**Research Sprint C note (2026-06-30):** the competitor research produced an
**avoid-list** of competitor anti-patterns —
[`../01-research/avoid-list.md`](../01-research/avoid-list.md). Those items are
**recommendations/inferences, NOT rejected-approach decisions**: they describe
mistakes **competitors** made (e.g. webhook-only/cron-only sync, `ir.cron`-as-a-
queue, manual-only recovery, email-only errors, single-location inventory,
"real-time" mislabelling, bot-blocked/gated docs). Per `CLAUDE.md` §10 and this
log's rules, an approach is only entered here as **Rejected** after it is
evaluated for **our** design and ChatGPT/architecture review rejects it. The
avoid-list items tagged "Arch review: YES" are seeded against AR-002…AR-008
(evidence-pending) and will route through the architecture-review log first. **No
approach is rejected in this sprint.**_

_**Research/Product Sprint D note (2026-07-01):** **none.** Sprint D was a
product-synthesis sprint (canonical feature taxonomy + capability evidence map). It
**evaluated no design option to rejection** — capability classifications
(baseline / premium / advanced-later / optional add-on / unknown) and MVP-relevance
tags are **inputs** for the gated RB-13 (MVP) and RB-14 (architecture) reviews, not
rejections. The taxonomy's "Capabilities with weak or blocked evidence" section
records competitor claims that are **not adopted as demonstrated** (e.g. Teqstars
docs-403 claims, WK config-field-only multi-company) — these are **evidence
downgrades under DP-003/DP-004, not rejected approaches**. No entry is added here._

_**Product Sprint E note (2026-07-01): none.** Sprint E was a product-strategy /
synthesis sprint (product vision + setup/UX principles). It **evaluated no design
option to rejection** — the product principles, premium quality bar, differentiation
themes, non-negotiables, and UX principles are **inputs** for the gated RB-13 (MVP)
and RB-14 (architecture) reviews, not rejections. The vision's "What we will avoid"
section and the UX doc's "Anti-patterns to avoid" restate the Sprint C **avoid-list**
(competitor anti-patterns) as **recommendations/inferences**, which — per `CLAUDE.md`
§10 and this log's rules — become formal rejections **only after** they are evaluated
for our design and ChatGPT/architecture review rejects them (the "Arch review: YES"
items remain seeded against AR-002…AR-008, evidence-pending). No approach is rejected
in this sprint; no entry is added here._

_**Product Sprint F note (2026-07-01): none.** Sprint F was an MVP-proposal / synthesis
sprint (MVP scope proposal + non-MVP boundaries + user stories). It **evaluated no design
option to rejection.** Items placed outside the MVP in
`../02-product/non-mvp-and-later-phases.md` (export, full payments/refunds/returns/
cancellations, payouts, multi-package fulfilment, order risk, SEO/BoM/pricelists/
per-market, Markets/B2B/POS/gift cards/metafields/extended breadth, multi-store/company,
custom transforms, analytics, App-Store/demo packaging) are **recommendations against
MVP inclusion only** — each carries a "what must be true before including" **revisit
condition** and a later phase. Per `CLAUDE.md` §10 and this log's rules, an approach is
entered here as **Rejected** only after it is evaluated for **our** design and
ChatGPT/architecture review rejects it — which has not happened. The weak/blocked
competitor evidence kept out of scope (pHash image dedup, Teqstars 403 breadth, EC/SH
breadth, WK config-field-only multi-company) are **evidence down-weights under
DP-003/DP-004, not rejected approaches**. No entry is added here._

_**Product Sprint G note (2026-07-01): none.** Sprint G recorded ChatGPT's **accepted MVP
scope** (`../04-decisions/DEC-003-mvp-scope.md`) and aligned the product docs. The items
**deferred/excluded from MVP** (**unrestricted autonomous bidirectional catalog ownership** —
all-field two-way conflict resolution, field-ownership matrix, advanced publish/channel
campaign management; **customer export**; refund sync, cancellation reflection, returns/RMA,
full Domain 9 accounting automation, payout/bank reconciliation, multi-package fulfilment,
complex tax, Markets/B2B/POS/gift cards/metafields/subscriptions/abandoned-checkout/
recommendations/Buy-with-Prime, multi-store/multi-company logic, custom transforms, advanced
analytics, public App-Store/demo packaging, and **bulk operations as a user-facing feature**)
are **product-scope boundary decisions with revisit conditions** in
`../02-product/non-mvp-and-later-phases.md` — **not** rejected architecture approaches. Per
`CLAUDE.md` §10 and this log's rules, an approach is entered here as **Rejected** only after
it is evaluated for **our** design and ChatGPT/architecture review rejects it — which has
**not** happened (no AR row is decided). The weak/blocked competitor evidence kept out of
scope (pHash, EC/SH breadth, WK config-field-only multi-company) are **evidence down-weights
under DP-003/DP-004, not rejected approaches**. (TeqStars docs were 403-blocked in Sprint C
but **re-checked accessible 2026-07-01**; a full rebaseline is pending.) No entry is added
here._

_**Product Sprint G revision note (2026-07-01, PR #55): still none.** ChatGPT's PR #55
correction moved **controlled product export/update INTO MVP** (product export is **not**
deferred) and kept **unrestricted autonomous bidirectional catalog ownership** and **customer
export** later. This is a **product-scope correction** — **no approach was rejected**, so no
entry is added here._
