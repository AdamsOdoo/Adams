# Keyboard, focus, and interaction annotations

> **Status: U0 prototype annotations. Proposed, not accepted.** These describe
> the intended keyboard/focus/semantic behavior the static prototype models and
> that UI-U1 must implement and test. The prototype contains **no JavaScript**;
> anything interactive is shown as separate anchored sections or CSS-only state
> panels, never as simulated production behavior. Executable keyboard tests
> (Odoo `web_tour` + HOOT) are a **UI-U1** deliverable — this file is the
> specification they verify against.

## 1. Global rules (all surfaces)

- **Focus visibility (WCAG 2.4.7).** Every operable element shows a 2px
  `:focus-visible` outline in `--sc-focus` (`#175CD3`, 5.99:1 on white) with a
  2px offset and 4px radius. Defined once in `assets/prototype.css`
  (`:focus-visible`); no element removes the outline.
- **Target size (WCAG 2.5.8).** Buttons are ≥ 36px block-size (min 24×24 CSS px
  enforced); chips, radios, and icon controls keep ≥ 24×24 hit area.
- **Tab order follows visual hierarchy.** Reading order = DOM order = visual
  order: app menu → breadcrumb → lead band action → primary region → secondary.
  No positive `tabindex`; logical source order carries it.
- **Icons.** Decorative inline-SVG icons are `aria-hidden="true"`; meaning is in
  adjacent text or an `aria-label`. The 7-day sparkline is a single
  `role="img"` with a text `aria-label` summarising the trend.
- **Status is never color-only (WCAG 1.4.1).** Every state chip, band, and owner
  chip carries a word; color reinforces only.

## 2. Per-surface keyboard walkthrough

### Dashboard (S3 — Owl client action at UI-U1)
1. App-menu items (Dashboard…Configuration) → 2. persistent health indicator
(link to Store Settings connection band) → 3. lead-band action (if present) →
4. each exception entry’s single action, top-to-bottom (max 3) → 5. secondary
metric chips (each links to its filtered S4/S5 view) → 6. recent-activity links.
- **Semantic headings:** one `h1`-equivalent lead answer; section titles
  (“Needs your attention”, “At a glance”, “Recent activity”) are headings so a
  screen-reader user can jump between regions.
- **Auto-refresh (WCAG 2.2.2 / PB-12):** dashboard refresh cadence ≥ 30s and is
  pausable/visibility-aware — never faster, never a moving distraction.
- **Status announcement:** the lead answer is an `aria-live="polite"` region so
  a change from “All systems normal” to “3 items need your attention” is
  announced without stealing focus.

### Setup & readiness (S1)
- **Step indicator** exposes the current step (`aria-current="step"`, and an
  `aria-label` “Setup step N of 6, <name>”).
- **Credential field:** a single labelled input; the helper text is linked via
  `aria-describedby`; the value is masked and never read back on any surface.
- **Test-connection & readiness results** are announced via `aria-live` when a
  run completes; a failed check associates its reason/fix with the row
  (`aria-describedby`) and names the responsible owner.
- **Continue** is disabled (`aria-disabled="true"`) until every must-pass check
  passes; the disabled reason is stated in text, not implied by graying alone.

### Matching center (S6/S8)
- **Automatic outcomes have no radio group.** The single-exact-match (bound
  automatically) and no-candidate (created automatically) screens are completed
  outcomes (merged Task 011): the outcome state is announced in words via the
  green outcome chip, and the controls are plain navigation links (Open contact /
  View audit trail / Back) — there is nothing to select or confirm.
- **Manual review is a radio group.** Only the ambiguous state offers a choice:
  `role="radiogroup"`, each card `role="radio"` + `aria-checked`; arrow keys move
  selection, Space selects; at most one is selected; with none selected, “Link”
  is `aria-disabled`.
- **Evidence tables** use real `<th>` headers (Field / Shopify / Odoo / Result)
  with header associations; each verdict is a word — **“Matched — binding key”**
  (the sole automatic key), **“Same”**, or **“Differs — advisory”** — plus icon,
  never color alone. There is no fuzzy/“Similar” verdict.
- **Ambiguous vs error (both danger family):** ambiguous uses the **hand** icon +
  a **reviewer** owner + “waiting on a decision / not a system failure”; technical
  error uses the **triangle** icon + the **system** owner + “this is a technical
  error, not an ambiguous match” — distinct to AT and to sight **without relying
  on color** (per the accepted `blocked_manual_review → danger` map).

### Product diff / preview (S7)
- **Diff table** has column headers (Field / Odoo value / Shopify value /
  Result) with associations; changed rows are conveyed by struck-through old
  value + new value + a labelled source-of-truth, not color alone; protected
  rows carry a “Kept — merchant-owned” **label** with a lock icon.
- **Confirm dialog behavior (UI-U1):** a destructive/high-impact confirm opens a
  `role="dialog"` with focus trapped, `aria-labelledby` the consequence
  summary, Esc to cancel, and initial focus on the non-destructive control.
- High-impact changes are never pre-selected; the primary action is the fixer
  when the preview is blocked.

### Odoo-native list & form
- Standard Odoo list/search/form keyboard behavior is inherited (native). The
  list’s search facet is a removable token; row exceptions are conveyed by a
  state **word** in the State column plus a tinted row, never tint alone.
- The form statusbar exposes the current stage (`aria-current`); notebook tabs
  follow the ARIA APG tabs pattern; smart buttons are links with text labels.

## 2a. Mobile shell (≤ 900px) — added per review `4950255482` §4

At ≤ 900px (tablet and phone) the 7-item app bar is replaced by a compact
Odoo-native shell so the operator navigation baseline stays usable and nothing
critical scrolls off:

- **`☰ Menu`** — a `<button aria-haspopup="true">` with the label “Open connector
  menu — all sections” (Arabic “القائمة” on the RTL render). It represents the
  overflow of the remaining sections. In production it opens the standard Odoo
  menu; the static prototype does not simulate the open state (no JS).
- **Current section** — carries `aria-current="page"`, is **always fully
  visible** (never truncated/clipped), and names where the operator is.
- **Persistent connection-health** — the dot + a **compact** label (“Connected”
  / “Throttled” / “Reconnect”); the full label shows on desktop, the compact one
  on the mobile shell (`.sc-health__lg` / `.sc-health__sm`). State is carried by
  the **word**, not the dot color alone (WCAG 1.4.1).
- No horizontal page scroll and no clipped labels at 375px, verified on
  `dashboard-success-375`, `matching-ambiguous-375`, `product-diff-update-375`,
  `setup-readiness-pass-375`, and `native-list-375` (plus the tightest case, the
  “Throttled” degraded health, which keeps the section name whole).

## 2b. Manual review is the danger family (token-map aligned)

Per the accepted token map (`blocked_manual_review → danger`), manual-review
surfaces use the **danger** color family, and are distinguished from a technical
failure **without relying on color**: the **hand** icon, a **reviewer** owner
chip, “waiting on a decision / not a system failure” copy, and decision actions
(vs the triangle icon, “system” owner, and “try again” of a technical error).
A screen-reader user hears the owner and the state word regardless of color.

## 3. Motion & reduced motion (WCAG 2.3.3 / design-system §8)

- Durations are tokenised: 100ms state/hover, 150ms reveal/collapse, 250ms
  panel/dialog enter; ease-out; nothing longer; no looping/decorative motion.
- The only animation is the honest platform spinner (conveys state).
- `@media (prefers-reduced-motion: reduce)` sets all transition/animation
  durations to ~0 and freezes the spinner to a static ring. All PNG evidence is
  rendered under reduced-motion, so the screenshots reflect the reduced-motion
  presentation exactly.

## 4. RTL / localization (design-system §10)

- All layout uses CSS **logical properties** (`margin-inline`, `padding-inline`,
  `border-inline-start`, `inset-inline`, `text-align:start`) — no left/right
  rules — so `dir="rtl"` mirrors the entire shell, bands, exceptions, chips,
  timeline, tables, and step indicator without any RTL-specific override.
  Evidence: `dashboard/dashboard-rtl-1366.png`.
- The breadcrumb chevron and any directional glyph mirror with the document
  direction. Numbers/dates render through the locale (Arabic-Indic digits shown
  in the draft RTL copy).
- **Arabic copy in the RTL rendering is draft (MBQ-22)** and is labelled as such;
  it exists to prove the layout mirrors without breakage, not to fix wording.

## 5. What is intentionally NOT simulated

- No fake progress bars, no JS state changes, no simulated async. Loading states
  are shown as skeleton compositions; “after click” states are shown as
  separate rendered states (e.g. test-success vs test-fail), not as live
  transitions. This keeps the prototype honest: it shows **what each state looks
  like**, and defers **behavior** to UI-U1.
