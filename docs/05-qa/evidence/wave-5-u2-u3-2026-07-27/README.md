# Wave 5 U2/U3 — rendered visual and accessibility evidence (2026-07-27)

> **Status: Evidence artifacts. NOT an acceptance, NOT a review, NOT a runtime
> or UAT claim.** Produced on `fable/wave-5-completion` by the implementing
> session, which per CLAUDE.md §13 may not review or accept its own work.
>
> **Evidence class: LOCAL rendered browser evidence.** The design system §14
> asks for the screenshot set "from the Odoo.sh runtime". These are **not**
> from Odoo.sh — this session is explicitly forbidden from running an Odoo.sh
> campaign. That is a genuinely narrower class and is stated here rather than
> blurred: the §14 requirement is **not** satisfied by this package.

---

## 1. Exact identity

| Item | Value |
| --- | --- |
| Frozen head | `SEE PR #204` — the SHA this package corresponds to is recorded in the PR body and in `ui-u2-validation-results.md` §1 |
| Odoo source | `30bde9ff758834a4912c5ae55843d3a7dad849f1` (`tools/odoo-pin.txt`), verified on checkout |
| PostgreSQL | 16.13 |
| Python | 3.12.3 |
| Browser | Chromium 141.0.7390.37 |
| `websocket-client` | 1.9.0 |
| Produced by | `addons/shopify_connector_core/tests/test_ui_visual_evidence.py` |
| Shopify operations | **none** |

**Reproduce:**

```bash
SC_EVIDENCE_DIR=docs/05-qa/evidence/wave-5-u2-u3-2026-07-27 \
  odoo-bin -d <db> --stop-after-init --test-enable \
           --test-tags shopify_connector_visual
```

Without `SC_EVIDENCE_DIR` the same test runs every assertion and writes its
artifacts to a temporary directory instead. That default is deliberate: the
canonical runner records `connector_worktree_dirty`, and a test that rewrote
these PNGs on every run would dirty the worktree and destroy the exact-SHA
property of the definitive run.

**No credential, token, shop name, PII or production data appears in any
artifact.** The only store in the fixtures is `visual-evidence.myshopify.com`,
an Odoo row created by the test and rolled back with it; no Shopify request was
made and no credential exists.

---

## 2. What is here

| Path | Contents |
| --- | --- |
| `screenshots/*.png` | 89 full-page captures, named `<surface>-<variant>-<width>px.png` |
| `contrast.json` | every measured text and non-text pair: selector, sample, foreground, background, font size, required threshold, computed ratio, PASS/FAIL |
| `focus-visible.json` | every focusable control with `:focus-visible` forced: outline style/width/colour/offset, box-shadow, background behind, measured indicator contrast, target size |
| `reduced-motion.json` | whether the media query reached the page, and every element still carrying a non-trivial transition or animation |
| `rtl.json` | per surface: `<html>`/`<body>`/connector-root computed `direction`, whether Odoo served its rtlcss bundles, whether `.o_rtl` was applied, and the overflow measurement |
| `responsive.json` | the widths measured and any surface whose document scrolled horizontally |
| `manifest.json` | every artifact mapped to the acceptance criterion it evidences |

**Surfaces captured (14):** U0 dashboard; U2 orders workspace, COD
reconciliation, customer matching, product matching, inventory workspace,
first-push guard (queue and form), location-mapping form; U3 export previews,
exported media, reconnect/backfill, export diagnostics, export settings, and
the **S7 export diff** carrying a refusal and an enumerated tag removal.

**Variants per surface:** `desktop-1366px`, `tablet-768px`, `mobile-390px`,
`rtl-1366px`, `reduced-motion-1366px`, `focus-1366px`.

---

## 3. Criterion → artifact

| Criterion | Artifact |
| --- | --- |
| DESIGN SYSTEM §10 responsive, §14 screenshot set (V-8) | `screenshots/*-{desktop,tablet,mobile}-*.png`, `responsive.json` |
| DESIGN SYSTEM §10 RTL smoke check (V-8) | `screenshots/*-rtl-1366px.png`, `rtl.json` |
| DESIGN SYSTEM §8 reduced motion (V-7) · WCAG 2.2 **SC 2.3.3** | `screenshots/*-reduced-motion-1366px.png`, `reduced-motion.json` |
| WCAG 2.2 **SC 2.4.7** Focus Visible (V-9) | `screenshots/*-focus-1366px.png`, `focus-visible.json` |
| WCAG 2.2 **SC 1.4.3** Contrast (Minimum) (V-3) | `contrast.json` |
| WCAG 2.2 **SC 1.4.11** Non-text Contrast (V-3) | `contrast.json` (`kind: "non_text"`), `focus-visible.json` (`indicator_contrast`) |
| WCAG 2.2 **SC 2.5.8** Target Size (Minimum) | `focus-visible.json` (`below_24px_target`) |

Official W3C sources, Accessible 2026-07-27:

- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html

---

## 4. Measured contrast — the connector's own surfaces

`[Fact]` **185 pairs measured across all 14 surfaces; 54 fail; 0 of the
failures are connector-owned.** Every failing pair belongs to Odoo's own
backend chrome — search-facet close buttons, dropdown toggles and the like —
which this repository neither styles nor can fix. They are left in
`contrast.json` rather than filtered out, because a table that silently drops
what it cannot fix is not a measurement.

`[Fact]` **All 24 connector-owned pairs pass.** Method: rendered
`getComputedStyle` colours; the background resolved up the ancestor chain and
alpha-composited, then over white; relative luminance per the WCAG 2.2
definition. A ratio taken against `rgba(0,0,0,0)` is meaningless and always
optimistic. **No value was rounded to produce a pass.**

| Ratio | Required | Kind | Foreground | Background | Selector |
| ---: | ---: | --- | --- | --- | --- |
| 3.63 | 3.0 | non-text | `#79839B` | `#F8FAFC` | `button.sc-x-btn` (control boundary) |
| 5.20 | 4.5 | text | `#B54708` | `#FFFAEB` | `span.sc-x-badge--warning` |
| 5.20 | 4.5 | text | `#B54708` | `#FFFAEB` | `div.sc-x-band__text` |
| 5.40 | 3.0 | text | `#067647` | `#ECFDF3` | `div.sc-band__text` (large) |
| 5.40 | 4.5 | text | `#067647` | `#ECFDF3` | `div.sc-band__hint` |
| 5.72 | 3.0 | non-text | `#175CD3` | `#F8FAFC` | `button.sc-x-btn--primary` (fill) |
| 6.57 | 4.5 | text | `#B42318` | `#FFFFFF` | `span.sc-x-tag__mark` |
| 6.57 | 4.5 | text | `#B42318` | `#FFFFFF` | `h2.sc-x-section__title--danger` |
| 6.98 | 4.5 | text | `#475467` | `#F2F4F7` | `span.sc-x-muted` |
| 7.35 | 4.5 | text | `#475467` | `#F8FAFC` | `p.sc-cadence` |
| 7.37 | 4.5 | text | `#475467` | `#FFFAEB` | `div.sc-x-band__hint` |
| 7.69 | 4.5 | text | `#475467` | `#FFFFFF` | `span.sc-chip__label` |
| 7.69 | 4.5 | text | `#475467` | `#FFFFFF` | `td.sc-x-cell--from` |
| 7.69 | 4.5 | text | `#475467` | `#FFFFFF` | `p.sc-x-note` |
| 7.69 | 4.5 | text | `#475467` | `#FFFFFF` | `div.sc-x-muted` |
| 7.69 | 4.5 | text | `#475467` | `#FFFFFF` | `span.sc-x-step__state` |
| 14.68 | 4.5 | text | `#1F2937` | `#FFFFFF` | `span.sc-chip__value` |
| 14.68 | 4.5 | text | `#1F2937` | `#FFFFFF` | `td.sc-x-cell--to` |
| 14.68 | 4.5 | text | `#1F2937` | `#FFFFFF` | `div.sc-x-list__name` |
| 14.68 | 4.5 | text | `#1F2937` | `#FFFFFF` | `span.sc-x-step__label` |
| 14.68 | 4.5 | text | `#1F2937` | `#FFFFFF` | `button.sc-x-btn` (label) |
| 20.07 | 4.5 | text | `#000000` | `#F8FAFC` | `h2.sc-section__title` |
| 20.07 | 4.5 | text | `#000000` | `#F8FAFC` | `h1.sc-x-head__title` |
| 21.00 | 4.5 | text | `#000000` | `#FFFFFF` | `h2.sc-x-section__title` |

**Tightest margin:** `--sc-border-strong` (`#79839B`) as a control boundary on
the page surface, at **3.63:1** against a 3.0 requirement. It passes, and it is
the value to watch if the surface token is ever lightened.

---

## 5. Focus, motion, RTL, responsive — measured results

`[Fact]` **Focus (SC 2.4.7 / 1.4.11).** 212 focusable controls measured with
`:focus-visible` forced through `CSS.forcePseudoState` — which removes the
browser's input-modality heuristic from the question entirely. **11 render no
indicator; 0 of them are connector-owned.** All 3 connector controls render a
**2 px solid outline at 5.72:1** against the surface behind them, comfortably
above SC 1.4.11's 3:1.

`[Fact]` **Target size (SC 2.5.8).** 35 controls measure below 24×24 CSS px;
**0 are connector-owned.**

`[Fact]` **Reduced motion (SC 2.3.3).** The media query reached the page on
every surface (`Emulation.setEmulatedMedia`). 19 elements still carry a
non-trivial duration; **0 are connector-owned.** The threshold is 10 ms rather
than 0: the conventional reduced-motion override — Odoo's own included — is
`0.001ms !important` rather than `0s`, so `transitionend` still fires. That
computes to 1e-6 s, which is not motion.

`[Fact]` **RTL.** A real `ar_001` session. Odoo served both rtlcss bundles and
applied its own `.o_rtl` class. Both connector Owl roots computed
`direction: rtl`. **No surface overflows horizontally in RTL.**

`[Fact]` **Responsive.** No surface scrolls the page horizontally at 1366, 768
or 390 CSS px.

---

## 6. The finding this package exists to have caught

`[Fact]` **`<html>` and `<body>` compute `direction: ltr` in the Odoo 19
backend even under a fully RTL locale.** Measured, with both rtlcss bundles
served and `.o_rtl` present:

```
html   dir attribute : null
html   computed      : ltr
body   computed      : ltr
```

Odoo's backend RTL mechanism is **rtlcss**, which flips *physical* properties
inside the CSS bundle. The connector's stylesheets are written entirely in
**logical** properties, which have nothing for rtlcss to flip and instead
resolve against `direction` — so before the correction in this batch, nothing
in the connector mirrored. `dir="auto"` on the surface roots made it worse
rather than better: it resolves from the first strong character of the
*content*, so an Arabic operator reading English operational data got `ltr`.

Both connector Owl roots now bind `dir` to the user's locale direction.
`u3-export-diff-refusal-and-tag-removal-rtl-1366px.png` is the rendered proof:
headings, table column order, the alert's accent rail and the refusal's border
all mirror.

**Reading the stylesheet said RTL was handled. Rendering it said otherwise.**
That is the whole argument for this package.

---

## 7. What this package does not establish

- **Not the design system §14 screenshot set.** That requires the Odoo.sh
  runtime; this is local.
- **No Odoo.sh runtime acceptance, no independent review, no UAT.**
- **No live-Shopify evidence.** `M-EXP-1`..`M-EXP-20` remain outstanding.
- **No performance measurement.** PB-1..PB-12 are not measured here.
- **No claim about Odoo's own chrome.** The 54 contrast failures, 11 missing
  focus indicators, 35 small targets and 19 animating elements that belong to
  Odoo are recorded, not fixed, and not this repository's to fix.
