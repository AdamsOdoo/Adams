# Batch 2 accessibility and evidence closure — rendered campaign

**Captured 2026-07-31**, on `fable/wave-5-completion` (draft PR #204), by
`addons/shopify_connector_core/tests/test_ui_visual_evidence.py` driving the
real surfaces in a real headless Chromium through the DevTools protocol.

> **NOT an acceptance, NOT a review, NOT Odoo.sh runtime, NOT a live-Shopify or
> UAT claim.** No Shopify store, credential, request or mutation was involved:
> every fixture is an Odoo row, and every transport seam is patched.

## Why this campaign exists

The independent review of `fc80cd8` accepted the Batch 2 correction (F1–F11)
and left three browser/accessibility **evidence** findings open. This directory
is those three closed, and nothing else.

| Finding | What was wrong | What the records here show |
| --- | --- | --- |
| **A. Live-region truthfulness** | Four static instructional bands declared `role="status"` — a polite ARIA live region — on copy that is on screen the moment the surface receives focus and that nothing on that surface can change. They had the role because they use an `alert-*` **visual** class and Odoo's view validator asks for a live role when it sees one | `batch2-live-region-semantics.json` — the complete declared inventory of all six surfaces read from the real combined arch, the adjudication of every live region, and the rendered proof that the notes are static, visible and non-empty across a real refusal |
| **B. Connector-owned clipping coverage** | Four of the six Batch 2 surfaces produced **zero** connector-owned measurement at any width; the two that did matched only Odoo's generic `.modal-body`, so their rows could not say which dialog they were about | `batch2-clipping-coverage.json` — 18 rows (six surfaces × three widths), each naming the marker it measured, the intended surface it proved visible, page overflow, modal-body coverage and final-control reachability |
| **C. Per-surface RTL proof** | The matrix accepted a surface on `any(...)` evidence measured somewhere else in the run | `rtl.json` — `per_surface_rows`, each carrying its own `.o_rtl`, rtlcss-bundle, intended-surface-visible and connector-root-direction measurements taken while that exact surface was on screen |

## Environment

| Item | Value |
| --- | --- |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (19.0), checked out and verified |
| Browser | Chromium 141.0.7390.37, headless |
| PostgreSQL | 16.13 |
| Python | 3.12.3 |
| Tested tree | the working tree of this correction, whose parent is `fc80cd8c881180c2c76843683672b1198ee9f0ee`. A commit SHA cannot appear inside the artifact that commit contains, so the final head is named in the PR body and in [`../../../07-implementation-plan/pr-204-batch-2-accessibility-evidence-closure-2026-07-31.md`](../../../07-implementation-plan/pr-204-batch-2-accessibility-evidence-closure-2026-07-31.md) instead of being asserted here |
| Update path | every run is `-u` against a database installed at `fc80cd8`, so `core 19.0.1.19.0 → 19.0.1.20.0`, `product 19.0.2.8.0 → 19.0.2.9.0` and `sale 19.0.2.7.0 → 19.0.2.8.0` are genuine version-to-version upgrades, read back from `ir_module_module` |
| Result | **0 failed, 0 error(s) of 16 tests** (14 at `fc80cd8` → **+2**) |

## The six Batch 2 surfaces

| Surface | Route | Marker measured |
| --- | --- | --- |
| `b2-store-settings-canonical` | canonical Store Settings form | `o_sc_store_settings` |
| `b2-store-form-controls` | store form, carrying both import control groups | `o_sc_store_form` |
| `b2-tax-decision-dialog` | tax decision dialog, opened from the stopped job | `o_sc_tax_decision` |
| `b2-product-match-decision-pending` | pending match decision record surface | `o_sc_match_decision` |
| `b2-product-match-decision-dialog` | match decision dialog, opened from the stopped job | `o_sc_match_decision_wizard` |
| `b2-product-match-decision-resolved` | resolved match decision record surface | `o_sc_match_decision` |

Every marker is **inert**: no connector stylesheet selects it, none was written
for it, and three of the five are declared on `<sheet>` (which lands on Odoo's
existing `.o_form_sheet_bg`) while the other two are declared on a band that is
already there. **No element is added to any surface.**

## What each record holds

| File | What it measures | Criterion |
| --- | --- | --- |
| `batch2-live-region-semantics.json` | **New.** Declared: every `role`/`aria-live`/`alert-*` on all six surfaces, read from the combined `get_view` arch so bands hidden by `invisible` and un-rendered notebook pages are in it too. Rendered: the same surfaces in a real browser, before and after a real production state change, plus the refusal path on both dialogs | WAI-ARIA 1.2 §5.3.2; WCAG 2.2 SC 4.1.3, SC 3.3.1 |
| `batch2-clipping-coverage.json` | **New.** Six surfaces × three widths. Per row: the intended surface's visibility under a surface-specific selector, every measured root with its full class list and connector markers, the page's own horizontal overflow, whether the modal **body** is still measured for the dialogs, whether the final actionable control is reachable, and a verdict | TD-016; DESIGN SYSTEM §10 |
| `rtl.json` | **Strengthened.** `per_surface_rows` replaces aggregate acceptance: each row records the intended selector and whether it was visible, `.o_rtl`, the rtlcss bundle count, every visible connector root with its computed direction, page overflow and clipping — all taken while that surface was on screen | DESIGN SYSTEM §10 RTL (V-8); TD-016 |
| `responsive.json` | per-surface horizontal overflow, silent clipping, escaped descendants and vertical reachability at 1366 / 768 / 390 px — now including the Batch 2 roots | §10, §14; TD-016 |
| `changed-surfaces-zoom-matrix.json` | Batch 1 + Batch 2 surfaces at 200% zoom, LTR and RTL | SC 1.4.4, SC 1.4.10 |
| `batch1-keyboard-traversal.json` | sequential focus navigation by real `Input.dispatchKeyEvent` Tab presses | SC 2.1.1, SC 2.4.3, SC 2.4.11 |
| `batch1-aria-semantics.json` | the Batch 1 alert/note semantics record, unchanged and re-run | WAI-ARIA 1.2; SC 4.1.3, SC 3.3.1 |
| `contrast.json`, `focus-visible.json`, `reduced-motion.json`, `sticky-action-row.json`, `sticky-focus-clearance.json` | the rest of the campaign, re-run at this head | SC 1.4.3, 1.4.11, 2.4.7, 2.5.8, 2.3.3, 2.4.11 |
| `manifest.json` | every artifact this run wrote, with the criterion each one serves | — |

## Screenshots

The run wrote **394** distinct screenshot files. `screenshots/` retains the
**110** belonging to the **six Batch 2 surfaces** this closure is about — every
width, both directions, 200% zoom, reduced motion, focus and the new
per-surface clipping captures. The other 284 are Batch 1 / U2 / U3 surfaces
whose equivalent pictures are already committed under the earlier evidence
directories; **all of them were still measured in this run**, and the `.json`
records here cover the complete set rather than only the retained pictures.
`retained-screenshots.txt` lists what was kept and says exactly that.

## One host-framework limitation, disclosed rather than asserted around

Odoo 19 at the pin announces a refused save as the bare string **"Missing
required fields"** (`Record._displayInvalidFieldNotification` in
`web/static/src/model/relational_model/record.js`), which no form controller
overrides. The announcement names no field. The refusal **is** announced —
`role="alert" aria-live="assertive"` — and the **attribution** is carried in
the DOM instead: exactly one named field is marked invalid, and it is the one
the connector's arch declared required. Odoo also marks that field's label,
which carries no `name`; that entry is kept in the record rather than filtered
out of it. This is Odoo chrome, not connector arch, and it is measured and
recorded here rather than worked around.
