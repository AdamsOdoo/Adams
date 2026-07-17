# Rendered visual-review evidence — 2026-07-16 correction

Browser-rendered evidence for the twelve Fable gap-closure prototype surfaces (plus
the accepted U0 dashboard and the prototype index), produced during the PR #173
consolidated correction. **Documentation-only evidence; no production UI code.**

- **Renderer:** headless **Chromium 1194** driven by **Playwright 1.56.1** (deterministic;
  no OCR). Harness: `scratchpad/render-prototypes.mjs` (loads each `file://` surface,
  full-page screenshot per viewport, then on-page link/overflow/accessibility probes).
- **Rendered:** 2026-07-16, against the corrected prototype HTML at PR #173 head.
- **Viewports:** desktop **1440×900** (every surface); tablet **768×1024** and mobile
  **390×844** (the seven representative surfaces: dashboard, orders, cod-reconciliation,
  external-fulfillment-review, reconnect-backfill, settings-permissions, jobs-diagnostics).
- **Totals:** 28 screenshots · **0 horizontal-overflow** hits · **0 broken links**
  (21 internal links checked) · **0 accessibility flags** · **0 page errors**.

## Contents

| File | What it is |
|---|---|
| `desktop/`, `tablet/`, `mobile/` | full-page PNG screenshots (one per surface per viewport) |
| `screenshot-index.md` | the full screenshot inventory + viewport coverage |
| `visual-review-report.md` | per-surface visual review against the premium checklist |
| `link-check-report.md` | internal-link resolution results |
| `overflow-report.md` | horizontal-overflow / responsive-reflow results |
| `accessibility-observations.md` | static accessibility observations + the one fix applied |
| `results.json` | raw machine output from the harness |

**Scope caveat.** This proves *static* visual quality, structure, link integrity,
responsive reflow, and static accessibility markup. It does not exercise live
interaction, focus-trap behavior in real assistive tech, or production Owl rendering —
those remain Wave-5 UI-implementation acceptance criteria (see the visual-review report).
