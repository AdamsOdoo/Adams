# Wave 5 — bounded onboarding batch: rendered browser evidence

**Captured 2026-07-29 at exact executable head `75ebb1560335390edc564854d473fc26699f2dcf`**
(`fable/wave-5-completion`, draft PR #204), from the last production commit
of this batch. Every artifact below was produced by
`test_ui_visual_evidence.py` running the real surfaces in a real headless
Chromium through the DevTools protocol.

> **NOT an acceptance, NOT Odoo.sh runtime, NOT a Shopify or UAT claim.**
> No Shopify store, credential, request or mutation was involved: every
> fixture is an Odoo row.

## Environment

| Item | Value |
| --- | --- |
| Connector head | `75ebb1560335390edc564854d473fc26699f2dcf` |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (19.0) |
| Browser | Chromium 141.0.7390.37, headless |
| PostgreSQL | 16.10 |
| Python | 3.11.15 |
| Result | **11 of 11 visual-evidence tests passed, 0 failed, 0 errors** |
| Artifacts | 174 (167 screenshots + 7 measurement records) |

## What each record holds

| File | What it measures | Criterion |
| --- | --- | --- |
| `responsive.json` | per-surface horizontal overflow, silent clipping, escaped descendants, **and vertical reachability**, at 1366 / 768 / 390 px | DESIGN SYSTEM §10, §14; TD-016 |
| `rtl.json` | the same, in a real `ar_001` locale at every width, with the connector root's computed `direction` read back | §10 RTL (V-8) |
| `reduced-motion.json` | computed transition and animation durations under `prefers-reduced-motion: reduce` | §8; WCAG 2.2 SC 2.3.3 |
| `focus-visible.json` | every actionable control's rendered focus indicator, with `:focus-visible` forced via `CSS.forcePseudoState` | SC 2.4.7, SC 2.5.8 |
| `contrast.json` | ratios computed from rendered colour, backgrounds resolved up the ancestor chain and alpha-composited | SC 1.4.3, SC 1.4.11 |
| `sticky-action-row.json` | **Wave 5.** The setup action row at 1366 / 1440 / 768 / 390 px on the three longest steps: what scrolled, how far, the bar's `position`, and its bottom edge against the scrollport's pin target | Wave 5 §11; §10 |
| `sticky-focus-clearance.json` | **Wave 5.** The last focusable control in the scrolling panel, focused and scrolled into view, measured for overlap with the bar | WCAG 2.2 SC 2.4.11 |

## The two findings this capture produced

Both were found by measuring, not by reading the stylesheet, and both are
fixed in the head this evidence was captured at.

1. **The setup surface's content was clipped and unreachable.** A client
   action renders inside `.o_action_manager`, which is `overflow: hidden`
   and scrolls nothing of its own. With `min-height: 100%` on
   `.o_sc_setup` the instrument measured **328–1774 px** of setup content
   overflowing that ancestor, with `doc_extent: 0` and no scrollable
   element anywhere in the chain, at all four widths. The surface now owns
   its own scrolling; `responsive.json` records
   `unreachable_vertical: 0` for every connector surface at every width,
   and `sticky-action-row.json` records real mid-scroll positions on
   `.o_sc_setup`.

2. **The sticky bar's negative inline margin was a real horizontal
   overflow.** It bled the bar 16 px past `.o_sc_setup__inner` on each
   side; `scroll_width 896` against `client_width 880` at every width in
   both directions. Removed.

## Screenshots

`screenshots/` holds 167 PNGs. The naming is
`<surface>-<variant>-<width>px.png`, where variant is one of the
responsive labels (`desktop`/`tablet`/`mobile`), `rtl`,
`reduced-motion`, `focus`, `sticky`, or `focus-bottom`. The Wave 5
setup captures are the `s1-setup-*` files, covering the Welcome, long
Permissions, Location mapping and Final readiness steps.

**No credential, token, customer name, email, address or raw Shopify
response appears in any capture.** The fixtures are connector-owned rows
with synthetic names, the credential step is not among the captured
surfaces, and the token input is a password field that is removed from the
DOM once submitted.
