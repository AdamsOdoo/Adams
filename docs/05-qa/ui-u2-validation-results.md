# UI U2 — Validation Results

> **Status: Evidence record. Docs. NOT an acceptance, NOT a review, NOT a
> runtime or UAT claim.** Produced on `fable/wave-5-completion` by the
> implementing session. Per CLAUDE.md §13 that session may not review or
> accept its own work, and this file accepts nothing.
>
> Required by
> [`ui-implementation-phases-packet.md`](../07-implementation-plan/ui-implementation-phases-packet.md)
> §8.1 (`ALLOWED FILES: … docs/05-qa/ui-u2-validation-results.md`). U2 shipped
> without it; this closes that gap and records what driving the U2 controls in
> a browser actually found.

---

## 1. What was executed, and in what

`[Fact — this environment, this session]`

| Item | Value |
| --- | --- |
| Odoo source | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (`tools/odoo-pin.txt`), verified on checkout |
| PostgreSQL | 16.13 |
| Python | 3.12.3 |
| Browser | Chromium 141.0.7390.37 (`ODOO_BROWSER_BIN=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`) |
| `websocket-client` | 1.9.0 — **installed**, so no `HttpCase` skipped |
| Shopify | **none** — no store, no credential, no request, no mutation, no webhook |

**Evidence class: local pre-freeze browser evidence.** This is *not* Odoo.sh
acceptance, *not* independent review, and *not* UAT. See §7.

---

## 2. The gap this closes

`[Fact]` U2 shipped with server-side visibility and wiring tests, and later
with a **navigation** tour that is read-only by construction. Its own
acceptance matrix requires browser evidence for the operator **controls**, and
there was none: every control that writes was deferred to "the driven runtime
campaign". [`ui-u3-validation-results.md`](./ui-u3-validation-results.md) §5.8
recorded that as an open gap.

`[Fact]` U2 ships **exactly four** controls that reach a server method. All
four are now driven in a real browser, by an allowed role and by a refused
role, with the resulting database state asserted:

| # | Control | Sanctioned action | Effect |
| --- | --- | --- | --- |
| 1 | `Approve Payment` | `action_approve_manual_gateway_order` | writes + enqueues |
| 2 | `Confirm First Push` | `action_confirm_first_push` | writes |
| 3 | `Verify Now` | `action_recheck_inventory_pair` | writes + enqueues |
| 4 | `Change Push` | `action_set_push_enabled` | writes |

`[Fact]` The customer, product and variant matching surfaces carry **no action
control at all**, by design — `grep '<button'` over all three view files
returns zero hits. That boundary is now pinned by test rather than left to a
comment (§4.3).

---

## 3. Defects the browser evidence found

`[Fact]` **Five.** Three are UI/server disagreements that no server-side test
could see, because a server-side test calls the method directly and never asks
whether an operator can reach it.

| # | Defect | Severity | Owner | Disposition |
| --- | --- | --- | --- | --- |
| 1 | **`Confirm First Push` was unreachable.** The control was rendered `invisible="first_push_state != 'pending'"` while `action_confirm_first_push` refuses anything that is not `previewed` — shown in the only state that fails, hidden in the only state that works. The First-Push Guard queue compounded it: its domain was `[('first_push_state','=','pending')]`, so the queue listed only rows whose control is unavailable. **The sanctioned first-push confirmation could not be completed from the shipped UI, and the only click it allowed could only ever raise `UserError`.** | **P1** | **Candidate** (introduced by `1d3e06f`) | Fixed. Button gated on `previewed`; queue lists both waiting states; the two states carry two different sentences. |
| 2 | **`Verify Now` was offered to a role the server refuses.** Button `groups="…group_shopify_connector_operator"`; `_recheck_inventory_pair` admits Reviewer or Administrator only. | P2 | Candidate | Fixed. Button gated on Reviewer; the wizard ACL moved from Operator to Reviewer to match. |
| 3 | **`Change Push` was refused at the dialog, not at the control.** Button `groups="…operator"`, but the transient wizard behind it was ACL'd to Administrator alone, so a Connector User pressed a control they were offered and was refused on `create()`. | P2 | Candidate | Fixed. Operator ACL row added for the toggle wizard. |
| 4 | **The scope-quarantine banner is unreachable.** Six U2 forms carry an `alert-danger` "Excluded from synchronisation" banner for `sec3_scope_quarantined` rows. The SEC-3 store rule is a *global* `ir.rule` filtering `sec3_scope_quarantined = True` out of **every non-superuser read**, so the row the banner sits on is invisible to every operator. | P3 | Inherited (SEC-3) | **Not fixed, deliberately.** The rule is stricter than the banner and is the correct fail-closed posture; weakening a security rule to make a banner appear would be the wrong trade. Recorded as dead UI. Test asserts the absence instead. |
| 5 | **Five list views carry a decoration for a state that does not exist.** `decoration-muted="status == 'inactive'"`, and `'inactive'` is not a value of the `status` selection anywhere in the codebase. The decoration can never fire. | P3 | Candidate | **Not fixed.** Harmless; recorded so the copy deck does not describe it as a real state. |

`[Inference — high confidence]` Defects 1–3 share one shape: **the view's
`groups=`/`invisible=` predicate disagreed with the server's own guard.** The
packet's §3 rule already says a UI-visible button whose call is denied
server-side is a test failure. What was missing was an instrument that could
observe it — server tests assert the guard, view tests assert the attribute,
and only a browser asks whether the two agree.

---

## 4. Executed results

### 4.1 U2 action-control tours

`[Fact]` `TestUiU2InventoryActionTours` (13 tests) and
`TestUiU2SaleActionTours` (7 tests) — **20 tests, 0 failed, 0 error(s)**.

| Tour | What it drives | Assertion after |
| --- | --- | --- |
| `…_first_push_confirm_tour` | Guard queue → row → warning banner → focus the control → **activate by keyboard** → consequence dialog → accept | `first_push_state == 'confirmed'`, actor and timestamp recorded |
| `…_first_push_pending_has_no_control_tour` | A `pending` pair | No control offered; state unchanged |
| `…_first_push_denied_tour` | Same row as an **auditor** | Disclosure readable, control absent, nothing written |
| `…_push_toggle_tour` | Mapping → `Change Push` → dialog states the consequence → Confirm | `push_enabled` flipped |
| `…_recheck_tour` | Blocked pair → `Verify Now` → read-only disclosure → reason → queue | Blocked job `cancelled`, **exactly one** successor, **no mutation attempt** |
| `…_recheck_blank_reason_tour` | Same, with no reason | Field marked invalid, dialog stays open, blocked job untouched, nothing enqueued |
| `…_order_approval_tour` | Orders → warning above the control → focus → dialog → reason → Approve | Provenance written, **exactly one** `order_import_sync` job |
| `…_order_approval_denied_tour` | Same order as an **auditor** | Disclosure readable, control absent, nothing written |
| `…_quarantined_is_not_listed_tour` | Workspace with a quarantined pair | The pair is **absent** — see defect 4 |

`[Fact]` **Every tour runs inside its own `HttpCase` transaction and is rolled
back at teardown.** `test_fixtures_leave_no_residue` asserts the property
rather than claiming it, and an AST check asserts no U2 control path calls
`cr.commit()`.

`[Fact]` **No test contacts Shopify.**
`test_no_shopify_transport_is_reachable_from_a_u2_control` asserts structurally
that `action_confirm_first_push` and `action_set_push_enabled` reach no API
client, no GraphQL document and no `_send`. The two enqueueing controls create
a **job row**; job execution is a dispatcher concern no tour starts, and the
re-check test additionally asserts **no mutation attempt** was created.

### 4.2 Roles, company boundary, idempotency

`[Fact]`

- **Allowed role succeeds** — Connector User completes all four controls.
- **Disallowed role is refused** — an auditor is offered no control on either
  the inventory or the order surface, and nothing is written.
- **Company boundary** — a foreign-company Administrator cannot even *see* the
  inventory pair or the location mapping; the SEC-3 store rule refuses the
  read, which is the strongest form of the refusal.
- **Repeated activation** — a second `action_confirm_first_push` raises and
  leaves the original actor and timestamp intact; a second approval enqueues
  **no** second `order_import_sync` job; the re-check requires exactly one
  blocked job and produces exactly one successor.

### 4.3 The disclosure-only boundaries

`[Fact]` Pinned by test, not by comment:

- `test_customer_matching_offers_no_resolution_control` — neither customer view
  contains a `<button>` or references `action_override_binding`.
- `test_cod_surface_offers_no_separate_write_control` — the COD list has no
  `<button>`, and the COD action reuses the order-review model and form, so its
  only control is `Approve Payment`.

`[Open question — scope, for the control room]` The U2 locked prompt names
"collection-event entry, discrepancy review" as COD deliverables. What shipped
is display-only (five-value ledger, three state badges). That is a **scope**
gap, not a missing string, and it is not closed here.

---

## 5. Rendered visual and accessibility evidence

`[Fact]` Produced by `test_ui_visual_evidence.py`, which drives the real
surfaces through the DevTools protocol. Artifacts:
[`evidence/wave-5-u2-u3-2026-07-27/`](./evidence/wave-5-u2-u3-2026-07-27/).

| Check | Instrument | Result |
| --- | --- | --- |
| Responsive, 1366 / 768 / 390 px | full-page screenshots + `documentElement.scrollWidth` vs `innerWidth` | No surface scrolls the page horizontally at any width |
| RTL | real `ar_001` session; rtlcss bundles served; computed `direction` read back | See the finding below |
| Reduced motion | `Emulation.setEmulatedMedia` `prefers-reduced-motion: reduce`; computed `transition-duration`/`animation-duration` read back | No connector element animates |
| Focus visible | `CSS.forcePseudoState('focus-visible')`; computed outline/box-shadow + measured contrast | Every connector control renders an indicator |
| Contrast | rendered `getComputedStyle` colours, backgrounds resolved up the ancestor chain and alpha-composited | See §6 |

`[Fact — P2 finding, and the reason the RTL claim had to change]` **Odoo 19's
backend never establishes `direction: rtl`.** Measured under a genuine
`ar_001` session with both rtlcss bundles served and Odoo's own `.o_rtl` class
present on the main components container:

```
html   dir attribute : null
html   computed      : ltr
body   computed      : ltr
.o_sc_dashboard       : dir="auto" → computed ltr
```

Odoo's backend RTL mechanism is **rtlcss**, which flips *physical* properties
inside the CSS bundle. That works for Odoo's own stylesheets and does nothing
for the connector's, because the connector's are written entirely in **logical**
properties — which resolve against `direction`, and `direction` was never set.
`dir="auto"` made it worse rather than better: it resolves from the first
strong character of the *content*, so an Arabic operator reading English
operational data got `ltr`.

**Reading the SCSS suggested RTL was handled. Rendering it proved it was not.**
[`ui-u3-validation-results.md`](./ui-u3-validation-results.md) §5.4's claim that
RTL is "implemented structurally … and not visually verified" was true about
the implementation and wrong about its effect.

`[Fact]` **Corrected.** Both connector Owl roots (`.o_sc_dashboard`,
`.o_sc_export_diff`) now bind `dir` to the user's locale direction rather than
to `auto`, so the logical properties resolve as intended. The test asserts the
connector surface root — not `documentElement`, which Odoo deliberately leaves
unset and which this repository cannot and should not change.

---

## 6. Measured contrast

`[Fact]` Thresholds applied: **WCAG 2.2 SC 1.4.3** — ≥ 4.5:1 ordinary text,
≥ 3:1 large text (≥ 24 px, or ≥ 18.66 px bold); **WCAG 2.2 SC 1.4.11** — ≥ 3:1
for the boundary of a meaningful UI component. Focus indicators are measured
against SC 1.4.11 as well (**SC 2.4.7** for their presence).

`[Fact]` Method: every visible text node's own `color` and its **effective**
background — resolved up the ancestor chain and alpha-composited, then over
white — read from `getComputedStyle` in the rendered page; relative luminance
per the WCAG 2.2 definition. A ratio taken against `rgba(0,0,0,0)` is
meaningless and always optimistic, which is the usual way a contrast table
lies.

`[Fact]` **185 pairs measured across 14 surfaces; 54 fail; 0 of the failures
are connector-owned.** Every failing pair belongs to Odoo's own backend chrome
(search-facet close buttons, dropdown toggles), which this repository neither
styles nor can fix; they are left in the artifact rather than filtered out,
because a table that silently drops what it cannot fix is not a measurement.

`[Fact]` **All 24 connector-owned pairs pass**, from **3.63:1** (the tightest —
`--sc-border-strong #79839B` as a control boundary on `#F8FAFC`, against a 3:1
requirement) to **21.00:1**. The complete per-selector table is in
[`evidence/wave-5-u2-u3-2026-07-27/README.md`](./evidence/wave-5-u2-u3-2026-07-27/README.md)
§4, with the raw data in
[`contrast.json`](./evidence/wave-5-u2-u3-2026-07-27/contrast.json).
**No value was rounded to produce a pass.**

`[Fact]` **Focus indicators:** 212 controls measured with `:focus-visible`
forced; 11 render no indicator, **0 connector-owned**; all 3 connector controls
render a 2 px solid outline at **5.72:1**, above SC 1.4.11's 3:1.
**Target size:** 35 controls below 24×24 px, **0 connector-owned**.
**Reduced motion:** 19 elements still animate, **0 connector-owned**.

`[Fact]` The design-system token pairs the connector uses, and their published
intent (§6 of the design system): `--sc-text-primary #1F2937` and
`--sc-text-secondary #475467` on `--sc-surface-0 #F8FAFC` / `--sc-surface-1
#FFFFFF`; the five semantic text/tint pairs; `--sc-border-strong #79839B` for
every interactive boundary and `--sc-focus #175CD3` for the focus ring.

`[Fact]` Cited criteria, official W3C sources (Accessible, 2026-07-27):

- SC 1.4.3 Contrast (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- SC 1.4.11 Non-text Contrast — https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- SC 2.4.7 Focus Visible — https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
- SC 2.5.8 Target Size (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- SC 2.3.3 Animation from Interactions — https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html

---

## 7. What this file does not claim

- **No Odoo.sh runtime acceptance.** DEC-041 D8 keeps the exact-SHA Odoo.sh run
  as the Tier-1 authority; nothing here substitutes for it.
- **No independent review.** The implementing session may not review its own
  work (CLAUDE.md §13).
- **No live-Shopify evidence.** `M-EXP-1`..`M-EXP-20` remain outstanding, and
  `X-EXPORT-0` remains an API-version hard stop that is neither PASS nor FAIL.
- **No UAT, no release readiness, no acceptance of any Wave 5 gate.**
- **No translation coverage.** No `.po` file exists in any U2 module.
- **No performance measurement.** PB-1..PB-12 are not measured here.
