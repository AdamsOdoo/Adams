# Batch 1 UI completion — fresh browser and accessibility campaign

**Captured 2026-07-30**, on `fable/wave-5-completion` (draft PR #204), by
`addons/shopify_connector_core/tests/test_ui_visual_evidence.py` driving the
real surfaces in a real headless Chromium through the DevTools protocol.

> **NOT an acceptance, NOT Odoo.sh runtime, NOT a Shopify or UAT claim.**
> No Shopify store, credential, request or mutation was involved: every
> fixture is an Odoo row.

## Why this campaign exists

The implementing report at `2e4f4278` admitted three proof gaps, and this
directory closes the third: *no fresh responsive / RTL / keyboard / zoom /
reduced-motion campaign for the surfaces the Batch 1 correction changed.*

The previous campaign was not wrong; it was aimed at a different set. Four of
the surfaces the correction rebuilt **do not exist until an operator acts** —
a location search result set, a set with a second page loaded, a search that
matched nothing, and each of the two withdrawal dialogs — so photographing the
step they live on measured the screen before the thing under test was on it.
Two more, the credential chooser's two paths, were never in the set at all.

## Environment

| Item | Value |
| --- | --- |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (19.0) |
| Browser | Chromium 141.0.7390.37, headless |
| PostgreSQL | 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1) |
| Python | 3.12.3 |
| Result | **14 of 14 visual-evidence tests passed, 0 failed, 0 errors** |
| Artifacts | 323 manifest entries: 313 screenshot captures under 283 distinct names (a surface photographed by two tests under one name is written twice) plus 10 measurement records. **146 screenshots retained here** — see `retained-screenshots.txt` |

## The ten surfaces this campaign is about

| Surface | Why it is in the set |
| --- | --- |
| `s1-setup-credential-dev-dashboard` | the two-path authentication chooser, default path |
| `s1-setup-credential-offline-token` | the same chooser with the offline path selected |
| `s1-setup-location-mapping` | the location step, now against 60 cached locations rather than 6 |
| `s1-setup-location-search-results` | a search with results, its counter and its Clear control |
| `s1-setup-location-loaded-more` | a full 50-row page plus a second page accumulated |
| `s1-setup-location-no-result` | the zero-result state that must keep its way out |
| `u2-first-push-form-awaiting-confirmation` | the pair form whose waiting-state copy was split |
| `u2-first-push-withdraw-dialog` | the single-pair withdrawal dialog |
| `u2-location-mapping-form` | the mapping form carrying the new control |
| `u2-location-withdraw-all-dialog` | the mapping-level withdrawal dialog |

## What each record holds

| File | What it measures | Criterion |
| --- | --- | --- |
| `batch1-zoom-matrix.json` | **New.** 90 rows: every surface above × desktop/tablet/mobile × LTR/RTL × {200% zoom, 200% zoom under `prefers-reduced-motion: reduce`}. Each row carries the exact selector, device width, resulting CSS viewport width, direction, zoom, motion preference, every connector surface's `scrollWidth`/`clientWidth`/overflow/clipping, the page's own horizontal overflow, whether the **final actionable control** is reachable after being scrolled into view, and a verdict | WCAG 2.2 SC 1.4.4, SC 1.4.10; §10 |
| `batch1-keyboard-traversal.json` | **New.** Sequential focus navigation driven by real `Input.dispatchKeyEvent` Tab presses — not a DOM-order walk — from a blurred document to the final actionable control of each surface, recording the full focus path, any focus lost to `<body>` before the target, and anything focus landed on that was not visible | SC 2.1.1, SC 2.4.3, SC 2.4.11 |
| `batch1-aria-semantics.json` | **New.** Alert/note semantics and announced validation states: whether the credential guidance is a live region *and earns it* (its text really changes when the path is switched), whether the withdrawal dialog's `role="note"` band is genuinely static, whether any `alert-*` band carries no role, and how a refused submission is announced and attributed | WAI-ARIA 1.2; SC 4.1.3, SC 3.3.1 |
| `responsive.json` | per-surface horizontal overflow, silent clipping, escaped descendants and vertical reachability at 1366 / 768 / 390 px | §10, §14; TD-016 |
| `rtl.json` | the same in a real `ar_001` locale at every width | §10 RTL (V-8) |
| `reduced-motion.json` | computed transition and animation durations under `prefers-reduced-motion: reduce` | §8; SC 2.3.3 |
| `focus-visible.json` | every actionable control's rendered focus indicator, `:focus-visible` forced via `CSS.forcePseudoState` | SC 2.4.7, SC 2.5.8 |
| `contrast.json` | ratios from rendered colour, backgrounds resolved up the ancestor chain and alpha-composited | SC 1.4.3, SC 1.4.11 |
| `sticky-action-row.json`, `sticky-focus-clearance.json` | the setup action row's pinning and focus clearance | SC 2.4.11 |

## Results

**No connector-owned defect was reproduced.** Specifically:

- **200% zoom: 90 of 90 rows PASS.** No page scrolls horizontally, no
  connector surface overflows its own box unhandled, nothing is silently
  clipped, and the final actionable control is reachable in every
  combination. The mobile row is measured at **320 CSS px** — SC 1.4.10's
  reflow width — rather than at 195px, which is what halving 390 produces and
  which no success criterion requires and no browser lays out for. Desktop and
  tablet are measured at 683px and 384px.
- **RTL is proved, not asserted.** All 30 RTL rows carry a measurement showing
  the page really rendered right-to-left (the connector root's computed
  `direction` where there is a connector root, and Odoo's own `.o_rtl` class
  and flipped stylesheet count everywhere else). A row labelled RTL with
  nothing behind it fails the test.
- **Keyboard alone reaches the final control on all 10 surfaces**, in 4 to 28
  Tab presses, with no focus landing on anything invisible.
- **Live regions earn their roles.** The credential guidance is `role="status"`
  and its text is measurably different between the two authentication paths;
  the withdrawal dialog's `role="note"` band is measurably identical before and
  after the operator fills the dialog in, which is why it is document structure
  and not a live region.

## One disclosed host-framework limitation

Odoo 19 at the pinned commit marks an invalid field with the class
`o_field_invalid` and **emits no `aria-invalid` anywhere in
`web/static/src`**. That is Odoo's form chrome, not connector arch, and it is
not fixable from this repository without patching core.

It is recorded in `batch1-aria-semantics.json` under
`host_framework_limitation` rather than asserted away. What the connector's
own arch decides *is* asserted: the reason field is `required`, so Odoo
refuses before the request is sent, marks the field, and announces the refusal
through its notification — which is `role="alert" aria-live="assertive"` and
names the field ("Missing required fields … Reason").

## Reproducing

```
SC_EVIDENCE_DIR=docs/05-qa/evidence/batch-1-ui-completion-2026-07-30 \
  tools/run_connector_suite.sh --tags shopify_connector_visual
```

Without `SC_EVIDENCE_DIR` the artifacts go to a temporary directory and are
discarded — deliberately, so a routine run cannot dirty the worktree and
destroy the exact-SHA property of the definitive validation. Every assertion
runs either way; this is a test, not a capture script wearing a test's
clothes.
