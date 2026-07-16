# Accessibility observations — 2026-07-16 correction

Static markup probes on each desktop render (not a substitute for an assistive-tech audit).

| Surface | lang | `<h1>` | imgs missing alt | unnamed buttons | unlabeled `<use>` svg |
|---|---|---|---|---|---|
| prototype-index | en | 1 | 0 | 0 | 0 |
| orders | en | 1 | 0 | 0 | 0 |
| order-review | en | 1 | 0 | 0 | 0 |
| cod-reconciliation | en | 1 | 0 | 0 | 0 |
| fulfillment | en | 1 | 0 | 0 | 0 |
| external-fulfillment-review | en | 1 | 0 | 0 | 0 |
| tracking-timeline | en | 1 | 0 | 0 | 0 |
| inventory | en | 1 | 0 | 0 | 0 |
| reconnect-backfill | en | 1 | 0 | 0 | 0 |
| product-export | en | 1 | 0 | 0 | 0 |
| stores | en | 1 | 0 | 0 | 0 |
| settings-permissions | en | 1 | 0 | 0 | 0 |
| jobs-diagnostics | en | 1 | 0 | 0 | 0 |
| dashboard | en | 1 | 0 | 0 | 0 |

**Findings.**
- Every surface declares `lang="en"`, has exactly one `<h1>`, no `<img>` without `alt`, and no button without an accessible name.
- **Fix applied this pass:** the first render flagged 2 decorative `<svg><use>` icons each in `orders.html` and `cod-reconciliation.html` (empty-state `#i-order`, loading `#i-sync`) lacking `aria-hidden`; `aria-hidden="true"` was added (no visual change). Re-render: **0 unlabeled icons**.
- Color is never the only signal — every status badge pairs an icon + text label (design-system rule), and the fulfillment/status taxonomy uses badge+label+icon.

**Carried to Wave-5 UI implementation (not provable in static HTML):** real keyboard focus-order and focus-trap behavior in dialogs/drawers; screen-reader announcement of live status changes; `prefers-reduced-motion` honoring for any animated states; full RTL mirroring beyond the dashboard's `dir` demo; WCAG contrast measured against the final production token values.
