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
| RA-002 | 2026-07-02 | REST-heavy Shopify API strategy for Phase 1 (AR-002 Option D) | `[Official fact]` REST is legacy as of 2024-10-01; `[Official limitation]` GraphQL is signalled the sole long-term API; the 2,048-variant product model degrades off the GraphQL product APIs; no current evidence supports it | Evaluated as an AR-002 candidate in `ar-002-distribution-api-framing.md`; the only real-world precedent (VentorTech) migrated **away** from REST (v2.0.0, 2026-01-23) | A Shopify reversal of the GraphQL-primary direction, or a documented REST-only requirement for a needed resource with no GraphQL equivalent | [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-003 | 2026-07-02 | Public Shopify App Store distribution / OAuth public-app flow / Billing API as a Phase 1 architecture requirement (AR-002 Option A as Phase 1) | Carries the full App-Store burden (3 mandatory compliance webhooks, protected-data "Requires review," Billing API, Built-for-Shopify performance thresholds) that DEC-003 already defers as product scope; this is the matching architecture-mechanism deferral, not a duplicate of the product-scope one | Evaluated as an AR-002 candidate in `ar-002-distribution-api-framing.md`; DEC-003 non-goals already exclude public App-Store packaging "unless distribution is later decided" | A future, ChatGPT-approved decision to pursue public App Store distribution for Phase 2+ | [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-004 | 2026-07-02 | OCA `queue_job` as the Phase 1 DEFAULT sync-orchestration substrate (AR-003 Option 3 as default; `queue_job` itself is NOT rejected, only its default-substrate role) | Non-core community dependency; Odoo.sh `server_wide_modules`/external-Jobrunner support is **not confirmed** by official docs (2026-07-02 refresh — silence, not a documented denial); competitor evidence (VentorTech) shows real `odoo.conf`-edit install friction; DEC-003's effortless-onboarding intent argues against depending on an unconfirmed hosting capability as the *default* | Evaluated as an AR-003 candidate in `ar-003-sync-orchestration-framing.md` and the 2026-07-02 evidence refresh (`../03-architecture/ar002-ar003-ar005-evidence-refresh.md`) | Odoo.sh (or on-prem) officially documents/demonstrates `server_wide_modules` + turnkey Jobrunner support, or MVP-scale throughput proves insufficient under the internal cron-queue | [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-005 | 2026-07-02 | Reuse of `ir.model.data` as the PRIMARY per-store binding/dedup mechanism (AR-005 Option C as primary; `ir.model.data` itself is not rejected for all uses) | `[Official source-code fact]` has `UniqueIndex('(module, name)')` and is designed for third-party data sync in principle, but has **no per-store column, no binding-status/audit fields**, and its `module`/`noupdate` semantics are tied to module-data lifecycle — a poor fit for a multi-store-safe, auditable runtime binding store | Evaluated as an AR-005 candidate in `ar-005-binding-dedup-framing.md` and the RB-14 Part 2 source-code resolution (`../03-architecture/rb14-part2-open-question-resolution.md`, RQ-005-3) | Official evidence that `ir.model.data` gains a per-store/audit-capable shape (no realistic path known; would need core changes) | [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-006 | 2026-07-02 | Name-only automatic product/customer matching (AR-005) | No evidence supports it as safe; directly contradicts the DEC-003 mandatory "no automatic name-only matching" + duplicate-prevention-preview rules; the classic root cause of connector duplicate-record defects | Evaluated as an AR-005 matching-priority question in `ar-005-binding-dedup-framing.md`; DEC-003 already requires SKU/barcode-first matching with ambiguous → manual review | None anticipated — would need a demonstrated, safe disambiguation method that does not exist today | [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |
| RA-007 | 2026-07-02 | External worker / out-of-Odoo processor as the Phase 1 sync-orchestration substrate (AR-003 Option 4) | Heaviest operational/deployment/security/monitoring surface; no competitor demonstrates it; contradicts DEC-003 install-and-go / Early Access simplicity | Evaluated as AR-003 Option 4 in `../04-decisions/DEC-005-sync-orchestration-strategy.md`; Phase 1 already has the Odoo.sh/on-prem internal cron-queue direction proposed; no evidence justifies a separate worker for single-store MVP | Serious throughput/hosting limitation proven after MVP-scale testing, or a later enterprise deployment explicitly accepts external infrastructure | [`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md) (Status: Accepted by ChatGPT, 2026-07-02) |

_No approaches rejected yet, **as of Research Sprints A–C** — historical for
that period only; **superseded for the log overall by RA-001** (added
2026-07-02, Control-Room Reset Sprint 1, from DEC-003's Option C rejection;
see the Log table above). Entries begin once design options are evaluated and
ChatGPT/architecture review formally rejects one._

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
it is evaluated for **our** design and ChatGPT/architecture review rejects it — which had
**not** happened *at Sprint G authoring time* (no AR row is decided). The weak/blocked
competitor evidence kept out of scope (pHash, EC/SH breadth, WK config-field-only multi-company)
are **evidence down-weights under DP-003/DP-004, not rejected approaches**. ~~(TeqStars docs
were 403-blocked in Sprint C but re-checked accessible 2026-07-01; a full rebaseline is
pending.)~~ **Superseded:** the full TeqStars rebaseline was completed the same day
(Research Sprint C2, PR #56, 2026-07-01) — see `../01-research/competitor-feature-matrix.md`.
No entry was added in Sprint G itself, but **DEC-003 — recorded in this same Sprint G —
did explicitly reject an MVP-scope option ("Option C — Thin import-only pilot"); that
rejection was later logged here as RA-001** in Control-Room Reset Sprint 1 (2026-07-02),
after being found missing from this log during a residue sweep._

_**Product Sprint G revision note (2026-07-01, PR #55): still none.** ChatGPT's PR #55
correction moved **controlled product export/update INTO MVP** (product export is **not**
deferred) and kept **unrestricted autonomous bidirectional catalog ownership** and **customer
export** later. This is a **product-scope correction** — **no approach was rejected**, so no
entry is added here._

_**Evidence Refresh + Combined AR-002/003/005 Decision Preparation (2026-07-02) — RA-002 through
RA-006 originally added, marked PROPOSED (history).** Unlike RA-001 (added only **after** ChatGPT
accepted DEC-003), RA-002–RA-006 were added **alongside** their DEC-004/005/006 proposals, per
that sprint's explicit instruction to log rejected/deferred approaches "if the proposed decisions
explicitly reject them." Each row was tagged **PROPOSED** at the time, citing the DEC file's own
then-current `Status: Proposed for ChatGPT review` — **at that time none of these was a final
rejection.** No approach outside the five tied to DEC-004/005/006 was evaluated to rejection in
that sprint; DEC-003's non-MVP deferrals were not re-logged there (see the Sprint G note above).
**Superseded by the acceptance note below** — all six rows (plus RA-007) are now final._

_**PR #60 minor revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES) —
RA-007 added (history).** Fable flagged a dangling pointer: DEC-005's rejected-options table
cited this log for AR-003 Option 4 (external worker) with no corresponding row. Added **RA-007**
(external worker as the Phase 1 sync-orchestration substrate), tagged **PROPOSED** at the time,
same pattern as RA-002–RA-006. **Superseded by the acceptance note below.**_

_**DEC-004/005/006 Acceptance Patch (2026-07-02) — RA-002 through RA-007 are now binding final
rejected approaches.** ChatGPT formally accepted
[`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md),
[`../04-decisions/DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md),
and [`../04-decisions/DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md)
on **2026-07-02** (after PR #60 merged into `Shopify-connector`, merge commit
`7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`, and Fable's minor-change review was applied). The
**`PROPOSED:` prefix has been removed** from RA-002 through RA-007's titles and their "Related
decision record" cells now cite each DEC file's `Status: Accepted by ChatGPT, 2026-07-02`. Per
`CLAUDE.md` §10, **the do-not-re-propose bar now applies in full** to these six rows — they are no
longer "candidate rejections under review" but **binding final rejections**, on the same footing
as RA-001, and may only be revisited via their stated **Future revisit condition**, routed through
`architecture-review-log.md`. This acceptance does **not** authorize implementation; DEC-003 and
MVP scope remain unchanged; AR-004/AR-006/AR-007/AR-008 remain not decided._
