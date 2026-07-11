# Screen spec — Command-center dashboard (S3)

> **Status: U0 prototype spec. Proposed, not accepted.** Implements the
> ranked §9 hierarchy of `../../03-architecture/premium-ui-ux-design-system.md`
> (which supersedes the accepted nine-equal-card grid *at ChatGPT’s review
> direction* — flagged, not silent). Inherits S3 / DEC-012 §3 / Part A §F.1
> from `../../02-product/ui-ux-final-design-spec.md`. Source:
> `dashboard.html` (+ `../assets/prototype.css`). Copy is illustrative
> (MBQ-22).

## Purpose
Answer “Is everything OK, and where do I click?” in ~10 seconds, on one
screenful, without a chart to interpret.

## Hierarchy (top → bottom) — the design-system §9 order
1. **Lead answer band** — the single dominant element. `--sc-fs-dominant`
   (1.75rem) / weight 600. Examples: *All systems normal* · *3 items need your
   attention* · *Store setup is incomplete* · *2 items are waiting on a
   decision*. Tinted per status; text always, color reinforces.
2. **Primary exception region** — **at most three** entries. Each entry:
   plain-language issue + count/affected scope + **why it matters** + **one**
   next action routing to the filtered S4/S5 view + an owner chip. When empty,
   it **collapses to one affirmative line** (`.sc-affirm`) — never three zeros.
3. **Secondary metric chips** (`.sc-chip`, not cards) — last-sync per domain,
   queued, retry-waiting, first-push-pending, inventory/fulfillment/matching
   exceptions. `--sc-fs-secondary`; quiet; loud (warning tint) only when a value
   is non-zero in a warning/danger state.
4. **Recent activity** — human-readable timeline with relative freshness +
   an honest cadence line (“checked every 15 minutes… last reconciled 22
   minutes ago”). No raw logs, no bare timestamps.
5. **Restrained trend (optional, severable)** — one monochrome 7-day
   activity/failure sparkline with a danger accent on failure days. Rendered
   only when ≥ 7 days of data exist. **This is the §9.5 sparkline decision** —
   see recommendation below; it is built so ChatGPT can remove it without
   touching regions 1–4.

## Tokens used
- Type: `--sc-fs-dominant` (band answer), `--sc-fs-lead` (section titles),
  `--sc-fs-cardtitle` (exception title), `--sc-fs-secondary` (chips/meta),
  `--sc-fs-caption` (owner chip, activity meta).
- Color: band/exception/chip semantic families (`success/warning/danger/info/
  neutral` text+bg); `--sc-border` on cards/chips; exception left-rule in the
  status text token; `--sc-accent` on the primary action.
- Spacing: sections `--sc-space-6` apart; card padding `--sc-space-5`; exception
  gap `--sc-space-3`. Card radius 8px, 1px border, no resting shadow.

## Five states (all rendered at 1366px)
| State | File | Behavior |
| --- | --- | --- |
| Loading | `dashboard-loading-1366.png` | Skeleton band + skeleton exception lines + honest line “Loading your dashboard…”. Never blank, never fake-instant. |
| First-run / empty | `dashboard-empty-1366.png` | Info band “Store setup is incomplete”; a guided empty card names the **one** next action (“Connect your store”) + a 3-step what-happens-next. |
| Healthy / success | `dashboard-success-1366.png` | Success band; exception region collapsed to one affirmative line; quiet chips; activity + severable trend. |
| Degraded / error | `dashboard-error-1366.png` | Warning band “3 items need your attention”; three ranked exceptions (financial hold → unmatched product → first-push); chips go loud where non-zero. |
| Manual review | `dashboard-manual-review-1366.png` | Warning band + **hand** icon “waiting on a decision”; reviewer-owned entries. **Visually distinct from error** (hand + decision language vs triangle + on-hold). |

## Responsive & RTL
- `dashboard-success-768.png`, `dashboard-success-375.png`: the region order
  (band → exceptions → chips → activity → trend) is preserved on stack; the
  two-column activity/trend collapses to one column; no horizontal page scroll;
  the lead answer and each row’s primary identifier stay visible.
- `dashboard-rtl-1366.png`: full mirror via logical properties; Arabic draft
  copy (MBQ-22).

## Actions
One primary action per state at most (e.g. “Connect your store” on first-run).
Exception entries each carry exactly one action; quick actions are
enqueue-only by design (PB-1) — nothing runs inline.

## Accessibility
`aria-live="polite"` lead answer; section headings; sparkline is a single
`role="img"` with a text summary; auto-refresh ≥ 30s and pausable (PB-12 /
WCAG 2.2.2). Full walkthrough in `../accessibility/keyboard-and-focus-notes.md`.

## Performance (mapped, not measured — UI-U1/UAT owns numbers)
PB-2 first useful render (band + exception region) ≤ 1.5s p75; PB-3 interaction
(card → filtered list) ≤ 200ms; PB-10 all counts via `read_group`/count
aggregates, never full recordsets; PB-8 ≤ 1,500 DOM nodes.

## Proposed vs inherited
- **Inherited (accepted):** S3 surface; lead-answer-first; nine cards’
  *information*; no-vanity-metrics; honest freshness; five states.
- **Proposed (needs acceptance):** the ranked §9 layout replacing the
  nine-equal-tile grid (design-system §9, ChatGPT-directed); the **optional
  sparkline** (§9.5); secondary metrics as *chips* rather than cards.

## Sparkline recommendation (the §9.5 severable call)
**Recommendation: keep the sparkline, in its restrained form.** Failure *trend*
(“is recovery working?”) is a genuine operator decision input the accepted copy
already implies (“failures cleared after 2 days”), and the restrained monochrome
form adds no vanity — it answers a question the numeric chips cannot. It is
built severable: removing it leaves regions 1–4 untouched. If ChatGPT judges it
vanity, remove it; the dashboard remains complete without it.
