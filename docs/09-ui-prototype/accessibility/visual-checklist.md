# Visual acceptance checklist — V-1 … V-12

> Completed against the design-system §13 checklist for the U0 prototype, and
> **re-evaluated after control-room review `4950255482`**. **Status: U0
> self-review evidence. Proposed, not accepted.** Result values are strictly
> **Pass / Partial / Fail** (nuances live in the Follow-up column so the totals
> count cleanly). No item is Pass without evidence. A **Partial** means the item
> is partly satisfiable in a static, JS-free prototype and its remainder is
> **runtime-scoped to UI-U1** (which stays closed) — never a hidden failure.

| # | Check | Result | Evidence | Follow-up |
| --- | --- | --- | --- | --- |
| **V-1** | One dominant answer per screen; hierarchy budget respected | **Pass** | Every screen leads with one lead-answer band (1.75rem/600) and subordinates the rest; the dashboard ranks band → ≤3 exceptions → quiet chips → activity → severable trend, and each state is driven from **one coherent data model** (`dashboard/dashboard-spec.md` §State-consistency). See `dashboard/*-1366.png`, `setup-readiness/*-1366.png`, `matching-center/*-1366.png`, `product-diff/*-1366.png`. | — |
| **V-2** | All spacing/type values on the accepted scale; no ad-hoc values | **Pass** | `assets/prototype.css` uses only the §4 scale via CSS custom properties (`--sc-space-1…8`, the six type sizes, weights 400/500/600). | — |
| **V-3** | Token-only colors; contrast recorded, all pairs pass | **Pass** | `accessibility/contrast-table.md` — 32 computed pairs, all pass; the revision introduced **no new color pair** (manual-review danger, blocked-row danger, and the advisory-neutral marker all reuse already-verified pairs). | ChatGPT to accept the `--sc-border`/`--sc-border-strong` split (contrast-table §5). |
| **V-4** | State never by color alone; all five states designed per surface | **Pass** | Every state carries a **word** (band sentence, status/owner chip) + icon; color only reinforces. Manual review and technical error are now **both danger** (per the token map) yet distinguished **without color** — hand icon + reviewer owner + “not a system failure” vs triangle + system owner + “try again”: `dashboard-manual-review-1366.png` & `matching-ambiguous-1366.png` vs `dashboard-error-1366.png` & `matching-error-1366.png`. Dashboard ships all five states; every other spec defines all five. | — |
| **V-5** | Icon usage within the §7 catalogue and rules | **Pass** | Icons are inline-SVG placeholders standing in for the §7 FontAwesome glyphs (annotated with FA names in the specs); monochrome, ≥16px, always paired with text; no emoji, no external icon font. | Placeholders → the real platform FontAwesome set at U1 (P9); structural chrome (search magnifier, breadcrumb chevron, ☰ menu bars) uses standard Odoo platform glyphs — noted, not a new semantic icon. |
| **V-6** | One primary action per screen; destructive styling + preview | **Pass** | Exactly one filled-accent primary per state; secondaries outlined; high-impact changes never pre-selected — `product-diff-blocked-1366.png` leads with the **fixer** (“Set price source of truth”), shows **no computed price and no Confirm**. Matching “Reject suggestion” sits apart from “Link”. | — |
| **V-7** | Motion within §8 durations; reduced-motion verified | **Pass** | Only tokenised transitions (100/150/250ms ease-out); the sole animation is the honest platform spinner; `@media (prefers-reduced-motion: reduce)` collapses transitions and freezes the spinner. All PNGs rendered with `reducedMotion:'reduce'`. | Live timing measured at UI-U1 (runtime). |
| **V-8** | Responsive at 375/768/1366; no horizontal scroll; RTL smoke check | **Pass** | 1366/768/375 renders for the dashboard and each screen’s primary surface. **Compact Odoo-native mobile shell ≤ 900px** (☰ Menu + current section + persistent health) — no clipped labels, no nav/health overlap, no horizontal page scroll; verified incl. the tight “Throttled” case. RTL: `dashboard-rtl-1366.png` mirrors fully via logical properties (Arabic Menu “القائمة”). | — |
| **V-9** | Keyboard walkthrough recorded; focus visible everywhere | **Pass** | `keyboard-and-focus-notes.md` records tab order, the visible `:focus-visible` ring (2px accent, 5.99:1), radiogroup/dialog/tabs semantics, header associations, and the **mobile-shell** menu/current/health behavior. | Executable keyboard/tour tests are a UI-U1 deliverable (static prototype has no JS). |
| **V-10** | No vanity metric, raw token, bare timestamp, or stack trace on any primary surface | **Pass** | Every metric routes to an action or state and reads as words (“In sync” / “2 to review”), not counts-for-their-own-sake; timestamps always relative + mechanism; **the internal token `blocked_manual_review` is NOT shown on any surface** (it lives only in the specs) — verified by the source-to-render check (`README.md` §Validation); errors show reason+fix+owner, technical detail behind a disclosure, never a stack trace. | — |
| **V-11** | Performance considerations mapped to accepted budgets | **Partial** | Each `*-spec.md` “Performance” section maps its surface to the PB rows (PB-2/3/4/5/9/10/13). | **Not measured** here — a static prototype has no runtime; measurement is owned by UI-U1 + UAT 27–28. Mapped, not passed. |
| **V-12** | Copy matches the accepted voice; no “encrypt”/“real-time” claims | **Pass** | Verb-first actions, we/you framing, no exclamation in errors, honest cadence, never “real-time”. Credential copy says “stored with restricted access… never displayed again”; the word **“encrypt” now appears nowhere in the prototype at all** (even meta-text reworded) — verified by the source-to-render check. Draft copy labelled draft (RTL Arabic + all strings MBQ-22). | Final copy is MBQ-22 (copy pass). |

## Summary

- **11 Pass · 1 Partial · 0 Fail.** The single Partial is **V-11**, honestly
  runtime-scoped: performance is **mapped** to the accepted PB budgets but cannot
  be **measured** in a static, JS-free prototype — measurement is a UI-U1/UAT
  deliverable. Nothing is claimed as measured that was not measured.
- The Result column now uses only Pass/Partial/Fail, so **the count matches the
  rows exactly** (the earlier “10 Pass, 2 Partial” mismatch is corrected).
- Design proposals living inside a Pass (V-3 border split; V-5 icon placeholders →
  real FontAwesome at U1; V-8 compact shell; V-4/§6-vs-§11 manual-review danger)
  are surfaced for ChatGPT in `README.md` §6 and `traceability-matrix.md` §3.
