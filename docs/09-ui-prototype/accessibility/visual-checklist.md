# Visual acceptance checklist — V-1 … V-12

> Completed against the design-system §13 checklist for the U0 prototype.
> **Status: U0 self-review evidence. Proposed, not accepted.** Each item is
> marked **Pass / Partial / Fail** with an evidence path and any follow-up.
> No item is marked Pass without evidence. "Prototype" = static HTML/CSS +
> rendered PNGs under `docs/09-ui-prototype/**`; it is **not** Odoo code, so
> items that require a running Odoo runtime (browser timing, HOOT, tours) are
> honestly scoped as **deferred to UI-U1**, not claimed here.

| # | Check | Result | Evidence | Follow-up |
| --- | --- | --- | --- | --- |
| **V-1** | One dominant answer per screen; hierarchy budget respected | **Pass** | Every screen leads with one lead-answer band at 1.75rem/600 and subordinates the rest; dashboard ranks band → ≤3 exceptions → quiet chips → activity → severable trend. See `dashboard/dashboard-*-1366.png`, `setup-readiness/*-1366.png`, `matching-center/*-1366.png`, `product-diff/*-1366.png`. | — |
| **V-2** | All spacing/type values on the accepted scale; no ad-hoc values | **Pass** | `assets/prototype.css` uses only the §4 scale via CSS custom properties (`--sc-space-1…8`, the six type sizes, weights 400/500/600). No off-scale px/rem literals for spacing or type. | — |
| **V-3** | Token-only colors; contrast recorded, all pairs pass | **Pass** | `accessibility/contrast-table.md` — 32 computed pairs, all pass; one proposed token (`--sc-border-strong #79839B`) recorded. Colors come only from the §6 tokens. | ChatGPT to accept the `--sc-border`/`--sc-border-strong` split (contrast-table §5). |
| **V-4** | State never by color alone; all five states designed per surface | **Pass** | Every state carries a **word** (status chips, band sentence, owner chip) plus an icon; color only reinforces. Dashboard ships all five as PNGs; every other spec defines all five (see each `*-spec.md` “States”). Manual-review is visually distinct from error (hand icon + “waiting on a decision” vs triangle + “on hold”): `dashboard-manual-review-1366.png` vs `dashboard-error-1366.png`; `matching-ambiguous-1366.png` vs `matching-error-1366.png`. | — |
| **V-5** | Icon usage within the §7 catalogue and rules | **Pass (with proposal)** | Icons are inline-SVG placeholders standing in for the §7 FontAwesome glyphs, each annotated with its FA name in the specs; monochrome, ≥16px, always paired with text; no emoji, no external icon font. | Structural platform chrome (`magnifying-glass` search, breadcrumb chevron) uses standard Odoo platform glyphs — noted for ChatGPT (not a new semantic icon). |
| **V-6** | One primary action per screen; destructive styling + preview | **Pass** | Exactly one filled-accent primary per state; secondaries outlined; destructive actions are danger-styled and never primary-positioned; high-impact changes are never pre-selected (`product-diff-blocked-1366.png` leads with the fixer action, not a confirm). Matching “Reject suggestion” sits apart from “Link”. | — |
| **V-7** | Motion within §8 durations; reduced-motion verified | **Pass (annotated)** | Only tokenised transitions (100/150/250ms ease-out) are used; the sole animation is the honest platform spinner; `@media (prefers-reduced-motion: reduce)` collapses transitions to instant and freezes the spinner. PNGs are rendered with `reducedMotion:'reduce'`. See `keyboard-and-focus-notes.md` §Motion. | Live timing verified at UI-U1 (runtime). |
| **V-8** | Responsive at 375/768/1366; no horizontal scroll; RTL smoke check | **Pass** | 1366/768/375 renders for the dashboard and each screen’s primary surface (e.g. `dashboard-success-{1366,768,375}.png`, `matching-ambiguous-{1366,768,375}.png`, `product-diff-update-{1366,768,375}.png`, `native-list-{1366,768,375}.png`, `setup-readiness-pass-{1366,768,375}.png`). Order preserved on stack; no page-level horizontal scroll. RTL: `dashboard-rtl-1366.png` mirrors fully via logical properties. | — |
| **V-9** | Keyboard walkthrough recorded; focus visible everywhere | **Pass (annotated)** | `keyboard-and-focus-notes.md` records tab order, the visible `:focus-visible` ring (2px accent, 2px offset, 5.99:1), dialog/radio semantics, and header associations per screen. | Executable keyboard/tour tests are a UI-U1 deliverable (static prototype has no JS). |
| **V-10** | No vanity metric, raw token, bare timestamp, or stack trace on any primary surface | **Pass** | Every metric routes to an action or state; timestamps are always relative + mechanism (“12 minutes ago (scheduled)”); no `retry_waiting`/`nextcall`-style tokens; errors show reason+fix+owner with technical detail behind “View technical detail”, never a stack trace. See `setup-test-fail-1366.png`, `matching-error-1366.png`. | — |
| **V-11** | Performance considerations mapped to accepted budgets | **Partial** | The specs map each surface to PB rows (PB-2/3 dashboard render+interaction, PB-4/5 lists, PB-9/10 pagination/aggregates, PB-13 matching lookup) in each `*-spec.md` “Performance” section and the traceability matrix. | Numbers are **not measured** here (no runtime) — measurement is owned by UI-U1 + UAT 27–28; recorded as deferred, not passed. |
| **V-12** | Copy matches the accepted voice; no “encrypt”/“real-time” claims | **Pass** | Verb-first actions, we/you framing, no exclamation in errors, honest cadence (“checked every 15 minutes”), never “real-time”. Credential copy says “stored with restricted access… never displayed again” and the word **encrypt** appears nowhere. Grep evidence in `README.md` §Validation. Draft copy is labelled draft (RTL Arabic + all strings are MBQ-22 illustrative). | Final copy is MBQ-22 (copy pass). |

## Summary

- **10 Pass**, **2 Partial** (V-11 performance measurement and — within V-5 —
  the platform-chrome icon note; V-9 execution), **0 Fail**.
- The two Partials are **honestly runtime-scoped**: they cannot be *measured*
  or *executed* in a static, JS-free prototype and are owned by **UI-U1**
  (which stays closed). Nothing is claimed as measured that was not measured.
- The one design proposal inside a Pass (V-3 border split, V-5 icon placeholders)
  is surfaced for ChatGPT acceptance in `README.md` and the traceability matrix.
