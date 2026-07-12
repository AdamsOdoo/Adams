# U0 — Premium operator UI visual prototype

> **Design artifacts only. No Odoo implementation. UI-U1 remains CLOSED.**
> Produced by the U0 visual-design session under gate comment **`4948902516`**
> (the B10/U0 authorization act), branched from the verified `Shopify-connector`
> base **`f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`** (PR #149 merged). This
> package is a **proposal** for ChatGPT review; it accepts nothing and
> authorizes no code.
>
> **Revision (control-room review `4950255482`):** this pass corrects six
> load-bearing semantic issues — (1) the **healthy dashboard** now reads from one
> coherent all-clear state model (no active exception/retry/pending/held item; a
> past incident is labelled **resolved**); (2) **customer ambiguity** now shows
> two candidates sharing the **exact normalized email** with advisory-only
> differences (no fuzzy discovery); (3) the **blocked product preview** asserts
> no price authority and computes no result; (4) a **compact Odoo-native mobile
> shell** replaces the clipped tablet/phone nav; (5) **manual review** uses the
> **danger** family per the accepted token map, distinguished from technical
> failure without color; (6) every PNG is regenerated from the final source with
> a **source-to-render consistency check** (§7).

The prototype demonstrates the future operator UI for the premium Odoo 19 ↔
Shopify connector: strong hierarchy, Odoo-native familiarity, restrained color,
clear exception handling, accessibility, responsive + RTL behavior, and Lite/Full
extensibility — implementing the ranked §9 command center and the selective-Owl
surfaces of `../03-architecture/premium-ui-ux-design-system.md` (PD-7), built on
the accepted corpus in `../02-product/ui-ux-final-design-spec.md` and
`../02-product/screen-inventory-and-navigation-map.md`.

---

## 1. How to open the prototype locally

Everything is **self-contained static HTML/CSS** — no server, no build, no
network. Open any `.html` file directly in a browser (`file://`), or start at
the index:

```
open docs/09-ui-prototype/prototype-index.html      # macOS
xdg-open docs/09-ui-prototype/prototype-index.html  # Linux
```

Each screen `.html` is a **gallery**: it stacks every state of that screen as a
full-width “screen” frame with a caption above it. Scroll to see all states.
The shared stylesheet is `assets/prototype.css` (linked relatively). The PNGs
were rendered from these exact files with headless Chromium at a 2× device scale
(so a “1366” PNG is 2732px wide).

## 2. Editable source vs rendered evidence

| Kind | Files | Role |
| --- | --- | --- |
| **Editable HTML source** | `prototype-index.html`, `*/‹screen›.html` (6 files) | The prototype itself — hand-editable static HTML, one per surface. |
| **Editable CSS source** | `assets/prototype.css` | The single token + component stylesheet. Every color/space/type value is a CSS custom property from the accepted design system. |
| **Markdown specs** | `*/‹screen›-spec.md` (5) + `accessibility/*` (3) + `traceability-matrix.md` + this README | The written design contract. |
| **Rendered PNG evidence** | 34 `*.png` | Screenshots rendered *from* the HTML/CSS. Evidence, not source — regenerate them from the HTML, never edit a PNG by hand. |

## 3. Artifact index

### Dashboard — `dashboard/`
- `dashboard.html` · `dashboard-spec.md`
- States @1366: `dashboard-empty-1366.png`, `dashboard-loading-1366.png`,
  `dashboard-success-1366.png`, `dashboard-error-1366.png`,
  `dashboard-manual-review-1366.png`
- Responsive: `dashboard-success-768.png`, `dashboard-success-375.png`
- RTL: `dashboard-rtl-1366.png`

### Setup & readiness — `setup-readiness/`
- `setup-readiness.html` · `setup-readiness-spec.md`
- `setup-connect-1366.png`, `setup-test-success-1366.png`,
  `setup-test-fail-1366.png`, `setup-readiness-loading-1366.png`,
  `setup-readiness-action-1366.png`, `setup-readiness-pass-1366.png`
- Responsive: `setup-readiness-pass-768.png`, `setup-readiness-pass-375.png`

### Matching center — `matching-center/`
- `matching-center.html` · `matching-center-spec.md`
- `matching-single-1366.png`, `matching-ambiguous-1366.png`,
  `matching-none-1366.png`, `matching-loading-1366.png`,
  `matching-error-1366.png`
- Responsive: `matching-ambiguous-768.png`, `matching-ambiguous-375.png`

### Product diff / preview — `product-diff/`
- `product-diff.html` · `product-diff-spec.md`
- `product-diff-update-1366.png`, `product-diff-blocked-1366.png`,
  `product-diff-loading-1366.png`, `product-diff-empty-1366.png`
- Responsive: `product-diff-update-768.png`, `product-diff-update-375.png`

### Odoo-native list & form exemplar — `odoo-native-exemplar/`
- `list-form.html` · `list-form-spec.md`
- `native-list-1366.png`, `native-form-1366.png`, `native-list-empty-1366.png`
- Responsive: `native-list-768.png`, `native-list-375.png`

### Accessibility & cross-cutting
- `accessibility/contrast-table.md` — 32 computed WCAG 2.2 SC 1.4.3/1.4.11 pairs
- `accessibility/visual-checklist.md` — V-1 … V-12
- `accessibility/keyboard-and-focus-notes.md`
- `traceability-matrix.md`
- `prototype-index.html`

## 4. Inherited (accepted) vs proposed

- **Inherited from the accepted corpus** (built upon, never weakened): the
  S1–S14 surface inventory, DEC-012 operator flows, the nine-element error
  contract + 16-class registry, the five states, fixed job-state/error
  vocabularies rendered as words, the credential posture (masked, no read-back,
  no “encrypt”), honest freshness, no-vanity-metrics, and the copy voice rules.
- **Proposed (needs ChatGPT acceptance)** — consolidated in
  `traceability-matrix.md` §3 (P1–P10) and as the decision list in §6 below.
  Chief among them: the ranked §9 dashboard replacing the nine-equal-tile grid
  (a ChatGPT-directed revision of accepted content, flagged, not silent), the
  optional sparkline, and the one contrast token addition.

## 5. Deviations, assumptions, and unresolved questions

- **Nine-card grid superseded.** The dashboard implements the design-system §9
  ranked hierarchy, which supersedes the accepted nine-equal-card grid *at
  ChatGPT’s own review direction*. This is a deviation from
  `ui-ux-final-design-spec.md` §Dashboard and is surfaced as **decision 1**.
- **Icons are inline-SVG placeholders**, not FontAwesome. External assets are
  forbidden this session, so each glyph is a minimal inline-SVG standing in for
  the accepted §7 FontAwesome name (annotated in the specs). Structural platform
  chrome (search magnifier, breadcrumb chevron) uses standard Odoo platform
  glyphs. Production (U1) uses the real platform FontAwesome set — **decision 9 /
  P9**.
- **`--sc-border-strong` proposed.** The accepted design system defines only
  `--sc-border #E4E7EC` (1.24:1). To satisfy SC 1.4.11 for interactive control
  boundaries without heavying every hairline, U0 proposes splitting the role and
  adding `--sc-border-strong #79839B` (contrast-table §3) — **decision 3**.
- **6-chip wizard compression** groups the 11 accepted steps into 6 visible
  chips (no step added/removed/reordered) — **decision 4 / P4**.
- **Arabic RTL copy is draft** (MBQ-22); it exists to prove the layout mirrors,
  not to fix wording. All on-screen strings are illustrative (MBQ-22).
- **No backend invented.** No RPC method, model field, XML ID, ACL, permission,
  or mutation logic is asserted; the diff/matching field names are illustrative
  presentations of accepted contracts only.
- **Manual review = danger family (token-map alignment).** Following review
  `4950255482` §5, `blocked_manual_review` uses the **danger** family per
  design-system §6; the §11 “warning family” prose is flagged as a **proposed
  correction** (P12), not changed unilaterally. The internal token
  `blocked_manual_review` is never shown on a UI surface (specs only).
- **Compact mobile/tablet shell (≤ 900px).** The 7-item app bar collapses to
  ☰ Menu + current section + persistent health — the reviewer’s “collapse the
  nav” option (P11) — replacing the clipped/overlapping full bar at 768/375.
- **Open questions carried, not closed:** final copy (MBQ-22), exact XML IDs
  (MBQ-03), ACL rows (MBQ-44), and every domain packet remain open; U0 closes
  none of them.

## 6. Decisions ChatGPT must make

1. **Dashboard hierarchy & state model** — accept/revise the ranked §9
   implementation (lead band → ≤3 exceptions → quiet chips → activity) replacing
   the nine-equal-card grid, **plus the state-consistency rule** (band color =
   most-severe *active* item; resolved incidents labelled, not counted — P13).
2. **Optional sparkline** — include or remove the 7-day activity/failure
   sparkline (built severable). *U0 recommendation: keep it (restrained;
   answers “is recovery working?”; see `dashboard-spec.md`).* 
3. **Adjusted contrast tokens** — accept the `--sc-border`/`--sc-border-strong`
   split and `#79839B`, or direct an alternative (contrast-table §5).
4. **Setup / readiness composition** — accept/revise the token-paste connect
   step, the test-connection outcome, and the three-group readiness layout
   (Action required / Passed / Not applicable), plus the 6-chip step compression.
5. **Matching-center composition** — accept/revise confidence-in-words, the
   **binding-key vs advisory** evidence marks (exact normalized email is the
   sole automatic key; no fuzzy verdict), the four-decision set, and the
   **manual-review-danger** distinction from technical error (P12).
6. **Product diff/preview composition** — accept/revise the 4-column diff,
   inline source-of-truth, protected-field treatment, and the **blocked-state
   posture** (asserts no authority, computes no result, no Confirm).
7. **Odoo-native token treatment** — accept/revise how restrained the connector
   token layer is on standard Odoo list/form views.
8. **Responsive, mobile shell & RTL** — accept/revise the **compact
   Odoo-native mobile/tablet shell** (P11), the mobile table reflow (stacked
   comparison cards; optional-column hiding), and the RTL mirroring.
9. **Owl scope in later phases** — confirm the PD-7 surfaces that will use Owl
   (dashboard, setup/readiness, matching, diff) vs stay Odoo-native.
10. **Prototype fidelity as the U1 baseline** — accept this prototype as the
    visual baseline U1 must match, or request revisions first.

**UI-U1 remains explicitly BLOCKED** until ChatGPT accepts this prototype in a
recorded act. This README authorizes nothing.

## 7. Validation summary (§24)

All commands run this session; results recorded here (no validation file is
created outside this directory).

| Check | Command / method | Result |
| --- | --- | --- |
| Changed-file scope | `git status --short` | **Only** `docs/09-ui-prototype/**` (new) + one appended `docs/01-research/research-handoff.md` entry. Nothing else. |
| Authorized paths | path filter over `git status` | All changes under the two authorized paths — **0 unauthorized**. |
| HTML validation | Python `html.parser` (strict) over all 6 HTML | **6/6 parse OK.** |
| CSS syntax | brace-balance check on `prototype.css` | **Balanced** (281 `{` / 281 `}`). |
| **Source-to-render consistency** | assert key visible-state text in the committed HTML + no stale PNG (mtime ≥ HTML+CSS) | **All 20 assertions pass** (see §7a). |
| Local-link integrity | resolve every `href`/`src` to disk | **All local links resolve**; no broken references. |
| External URLs | grep `https?://` link targets in HTML/CSS | **None** as link targets (only illustrative `*.myshopify.com`/`example.com` strings inside copy text). |
| Network dependencies | grep `@import`, `url(`, `@font-face`, `cdn`, remote `src` | **None.** Platform system-font stack only. |
| JavaScript | grep `<script`, `on*=`, `javascript:`, `addEventListener` | **None — zero JavaScript.** |
| Addon / code refs | grep `addons/`, `__manifest__`, `import odoo`, `<record` | **None** — no Odoo code created. |
| Secret-like values | grep `shpat_`/`Bearer`/keys/≥32-char | **None.** The only ≥32-char strings are the public base SHA in a CSS header comment and decorative comment rules — no tokens/secrets. |
| PNG evidence | dims + sizes over 34 files | **34 PNGs, ~8.6 MB.** CSS widths 1366 (×24), 768 (×5), 375 (×5); rendered at 2× (2732 / 1536 / 750 physical). All regenerated from the final HTML/CSS this revision. |
| Contrast | WCAG luminance formula, 32 pairs | **All 32 pass** their SC 1.4.3 / 1.4.11 threshold (contrast-table.md). The revision added **no new color pair** (manual-review danger, blocked-row danger, advisory-neutral all reuse verified pairs). |
| V-1…V-12 | honest self-review | **11 Pass · 1 Partial (V-11, runtime-scoped) · 0 Fail** (visual-checklist.md). |
| Viewport rendering | headless Chromium at 1366/768/375 + RTL | No horizontal page scroll; the compact mobile/tablet shell shows Menu + current section + health with no clipped label or nav/health overlap; mobile comparison tables reflow to labelled cards; RTL mirrors. |
| Handoff structure | update the existing top U0 entry only | The existing U0 entry carries a revision note; older entries untouched. |

### 7a. Source-to-render consistency check (review `4950255482` §6/§8)

Because every PNG is rendered from the committed HTML/CSS, consistency is proven
deterministically: (a) **20 assertions** over the committed HTML confirm the key
visible-state text, and (b) a **staleness guard** confirms every PNG’s mtime is
≥ its source HTML **and** `prototype.css`. Verified this revision:

- **Setup:** connect step shows **“Step 2 of 6”** and **Credentials** is the
  current step; the word **“encrypt” appears nowhere** in the prototype.
- **Dashboard success:** “All systems normal”, chips read clear
  (“In sync”/“Complete”), **no** active-exception/“Pending” chip, **no** active
  held order, and the incident is labelled **“resolved”**.
- **Dashboard manual-review & degraded:** **danger** band; manual review carries
  the **hand** icon and shows **no raw `blocked_manual_review` token**.
- **Matching ambiguous:** both candidates carry the **exact** incoming email
  `j.okafor@example.com`; **no** `jane.okafor@…` and **no** “same domain / similar
  name / partial match” wording; “advisory only” + “binding key” framing present.
- **Blocked diff:** “Choose a price authority” / “Held until a price authority”;
  **no** “Odoo is the price authority”; **no** Confirm button.
- **Staleness:** 34/34 PNGs newer than their HTML+CSS source — no stale evidence.

### Confirmations
- **Zero external dependencies** (no CDN, font, image, tracker, or remote asset).
- **Zero JavaScript.**
- **No addon, Python, XML, manifest, security, migration, CI, or `.claude/`
  file changed** — this session produced no Odoo implementation.
- Parallel sessions **Task 010B** and **Task 011B** were **not touched**, not
  branched from, and not depended on.
