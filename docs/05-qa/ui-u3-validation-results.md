# UI U3 — Validation Results

> **Status: Evidence record. Docs. NOT an acceptance, NOT a review, NOT a
> runtime or UAT claim.** Produced on `fable/wave-5-completion` by the
> implementing session. Per CLAUDE.md §13 that session may not review or
> accept its own work, and this file accepts nothing.
>
> Required by `ui-implementation-phases-packet.md` §8.2 (`ALLOWED FILES:
> … docs/05-qa/ui-u3-validation-results.md`).

---

## 1. What was executed, and in what

`[Fact — this environment, this session]`

| Item | Value |
| --- | --- |
| Odoo source | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (`tools/odoo-pin.txt`), verified on checkout |
| PostgreSQL | 16 (local cluster) |
| Python | 3.12 |
| Browser | Chromium (`ODOO_BROWSER_BIN=/opt/pw-browsers/chromium`) |
| Shopify | **none** — no store, no credential, no request, no mutation, no webhook |

**Evidence class: local pre-freeze evidence.** This is *not* Odoo.sh
acceptance, *not* independent review, and *not* UAT. See §6.

---

## 2. The environment finding that came first

`[Fact]` Before any U3 result below could be trusted, one thing had to be
fixed: **`websocket-client` was not installed, so every `HttpCase` browser
test SKIPPED** while the suite still reported `0 failed, 0 error(s)`.

That is the most dangerous shape a test result can take — a green run that
proves nothing. Any tour "result" recorded in an environment without
`websocket-client` is a skip, and must never be quoted as browser evidence.

---

## 3. Defects the browser evidence found

`[Fact]` Four defects were found by *executing* the surfaces. None of them is
visible to a server-side view test.

| # | Defect | Owner | Disposition |
| --- | --- | --- | --- |
| 1 | `ir.actions.client` has no `group_ids` field in Odoo 19 (`ir_actions.py::IrActionsClient`, read at the pin). Declaring one is a hard `ParseError` at install. | **Candidate** | Fixed. Access enforced on the menu, the button, the projection service (`AccessError` below the auditor floor) and `action_confirm_export_preview`. Reason recorded in the XML so it is not "fixed" back. |
| 2 | `--` inside an XML comment in the Owl template made the entire `web.assets_web` bundle fail to build (`OwlError: Missing template "web.WebClient"`). | **Candidate** | Fixed. Only a browser could see this; the Python install parsed the file without complaint because static templates are not parsed at install. |
| 3 | **Every tour in the repository timed out on its first step.** In Odoo 19 the `.o_app` tiles live inside the apps-menu sidebar and do not exist in the DOM until it is opened (`web/static/src/webclient/navbar/navbar.xml`). `shopify_connector_u0_nav_tour`, merged with U0, **could never have passed**. | **Inherited** | Fixed with the standard `stepUtils.showAppsMenuItem()` step. The U0 tour now passes — see §4. |
| 4 | `shopify_connector_dashboard.test.js` has shipped since U0 and **nothing ever ran it**: no Python runner opened `/web/tests`. It is also broken — `mockService` at module scope, which HOOT rejects during suite registration. | **Inherited** | Module-scope `mockService` corrected. The suite still fails to register for a **further, unidentified reason**; see §5. |
| 5 | **The canonical runner's warm and non-standard databases had no filestore.** `createdb -T` copies the database but not `<data_dir>/filestore/<dbname>/`, so the clone came up with a complete `ir_attachment` table pointing at files that were not there (76 MB in the template, 1.1 MB in the clone). Invisible to every test that does not read an attachment's bytes — and fatal to every browser test, because the web asset bundles **are** attachments: they failed to load, `odoo.isTourReady(...)` never became true, and all five tour tests failed in the warm pass while the fresh pass was green. | **Inherited (runner)** | Fixed. `clone_db()` now copies the filestore with the database. **The warm database was not reproducing a warm upgrade; it was reproducing a broken installation.** |

`[Fact]` Finding #5 is the reason the first definitive exact-head run was
discarded rather than reported: fresh passed **1728/1728** and warm failed
**3 failed, 2 error(s) of 1728** — every failure a tour, none of them a
product defect. Reporting that as a product result would have been wrong; so
would tagging the tours out of the warm pass to make it green. The instrument
was broken, and the instrument was fixed.

`[Inference — high confidence, from #3 and #4 together]` No browser evidence
for any connector UI surface has ever actually executed in this repository.
That is consistent with `wave-5-completion-gate-state.md` §5e, which records
browser evidence as absent — but the reason is stronger than "not yet run":
the harness could not have produced a pass.

---

## 4. Executed results

### 4.1 Browser tours — `HttpCase`, real Chromium

`[Fact — verbatim]`

```
odoo-bin ... --test-enable --test-tags /shopify_connector_product_export:TestU3ExportTours,/shopify_connector_core:TestUiTours
0 failed, 0 error(s) of 5 tests
```

| Tour | Covers |
| --- | --- |
| `shopify_connector_u0_nav_tour` | **Inherited, now passing.** Dashboard → Stores → Sync Center → Error & Review Center → Logs |
| `shopify_connector_u2_nav_tour` | **New — U2 had no browser evidence at all.** Orders workspace → COD reconciliation → customer matching → product matching → variant matching → inventory workspace → first-push guard → location mapping |
| `shopify_connector_u3_export_nav_tour` | All five U3 export surfaces render: Export Previews, Exported Media, Reconnect and Backfill, Export Settings, Export Diagnostics |
| `shopify_connector_u3_export_review_tour` | Opens the Owl diff on a seeded preview and asserts the **refusal section** and the **enumerated tag removals** are on screen, and the confirm control is present for a reviewer |
| `shopify_connector_u3_export_keyboard_tour` | The export action takes keyboard focus **and matches `:focus-visible`**, so a focus ring that exists only in the stylesheet fails |

`[Fact]` The review tour deliberately **does not click confirm**. Confirming
enqueues a real apply job, and a tour must not leave a queued mutation behind.

`[Fact]` The U2 tour is **read-only by construction**: every step opens a menu
or asserts that a list rendered. No step clicks a control that writes, enqueues
a job or contacts Shopify, so it leaves no residue. It also found a real
navigation fact that a server-side test would not have: **Customer Matching is
parented to the *Catalog* branch, not Orders**, even though the menu is
declared in the sale addon.

### 4.2 HOOT unit suite

`[Fact — verbatim]`

```
[HOOT] "@shopify_connector_product_export/shopify_connector_export_diff" ended (passed: 11 / time: 1252 ms)
[HOOT] Test suite succeeded
```

Eleven assertions on the S7 component, including the ones that carry the
safety property:

- tag removals are enumerated **by name** in a `role="alert"`;
- a tag change that only **adds** raises no removal alert (crying wolf on
  every tag edit is how a real removal stops being read);
- refusals render with their own heading and detail;
- the confirm control is **absent** when the server would refuse;
- an expired preview says so and offers no confirm;
- confirm calls **exactly** `action_confirm_export_preview` — the ORM mock
  throws on any other call, so a future edit that writes a field or enqueues
  a job directly fails here;
- a double click cannot enqueue two applies;
- a failed load renders an error rather than an empty screen;
- the progress bar carries accessible bounds.

### 4.3 Server-side U3 tests

`[Fact]` `TestExportUiProjection` — 13 tests. The projection is proven
read-only **by AST guard** (no `write`, `create`, `unlink`, `sudo`, `commit`,
`enqueue`, `execute` or `_send` call survives), its sudo budget is pinned at
**zero** in the module's frozen sudo inventory, and its `can_confirm` is
asserted to agree with what `action_confirm_export_preview` actually does for
the same user, state and expiry.

---

## 5. Not closed, stated plainly

> **Superseded in part on 2026-07-27 by the consolidated U2/U3 evidence-closure
> batch on this same branch.** Items 1-5, 7 and 8 are CLOSED; item 4's
> underlying claim turned out to be **wrong** and is corrected in §5A. Items 6
> and the Odoo.sh/review/UAT absences in §6 stand. The original wording is kept
> verbatim below rather than rewritten, because a durable record should show
> what was believed at the time.

`[Fact]`

1. **The U0 HOOT suite still fails to register.** `HootError: error while
   registering suite "shopify_connector_dashboard"`. The module-scope
   `mockService` was one cause and is corrected; a second cause remains
   unidentified. The runner added in this batch is therefore scoped to the
   export suite. **This is an inherited defect, it is not fixed, and the U0
   dashboard component consequently still has no executed unit evidence.**
2. **No screenshot set.** The tours assert structure and focus
   programmatically; no image artifact is captured or committed.
3. **No contrast measurement.** The stylesheet uses the accepted
   design-system semantic pairs and `--sc-border-strong` for every control
   edge, and states the intent — but no instrument measured a rendered
   contrast ratio in this session, so no ratio is claimed.
4. **No RTL screenshot.** RTL correctness is implemented structurally
   (`dir="auto"` plus logical properties throughout the stylesheet — no
   physical `left`/`right`/`width` anywhere) and is **not** visually verified.
5. **No reduced-motion visual check.** Every transition is behind
   `prefers-reduced-motion: no-preference`, so the reduced-motion default is
   *no animation*; this is verified by reading the stylesheet, not by
   rendering under the media query.
6. **The HOOT suite imports `mailModels`** from `@mail/../tests/mail_test_helpers`
   to satisfy the mock server, which couples the unit bundle to `mail` being
   installed. The canonical runner always installs `account`+`stock` (hence
   `mail`), so this holds there; a unit run in a DB without `mail` would fail
   to resolve the import.
7. **No `ui-u2-copy-deck.md`.** The U2 surfaces carry their copy inline with
   no deck. A genuine gap in the U2 record; not closed here.
8. **U2's browser evidence is navigational only.** The new U2 tour proves
   every U2 surface renders and is reachable; it does **not** exercise the
   U2 *action* controls (order review, COD reconcile, matching resolve),
   because those write and a tour that leaves state behind is worse than no
   tour. Those remain for the driven runtime campaign with seeded fixtures.

---

## 5A. Addendum (2026-07-27) — what the consolidated closure batch found

`[Fact]` **Item 1 — the U0 HOOT registration failure is diagnosed and fixed,
and it was never in the dashboard test.** The swallowed cause is:

```
Error while loading "@shopify_connector_core/js/tours/shopify_connector_u0_tour":
TypeError: Cannot destructure property 'stepUtils' of 'require(...)' as it is undefined.
```

`web.assets_unit_tests_setup` does `('include', 'web.assets_backend')`, and
HOOT builds a per-suite module set from the test file's addon plus that addon's
**declared Odoo dependencies**, then starts every module in it
(`web/static/tests/_framework/module_set.hoot.js::defineModuleSet`, read at the
pin). `web_tour` is not a declared dependency of `shopify_connector_core`, so
`@web_tour/tour_utils` was filtered out of the set while the tour importing it
was not — the tour threw, the module set failed, and the suite that merely
shared the bundle could not register. The three connector tours now live in
`web.assets_tests`, Odoo's own home for `HttpCase` tours. **Both suites now
execute: `shopify connector dashboard` 8/8 and `shopify connector export diff`
11/11**, each verified for its success marker AND its exact executed count.

`[Fact]` **Items 2, 3 and 5 are closed by measurement**, not by argument. See
[`ui-u2-validation-results.md`](./ui-u2-validation-results.md) §5-§6 and
[`evidence/wave-5-u2-u3-2026-07-27/`](./evidence/wave-5-u2-u3-2026-07-27/):
89 screenshots at 1366/768/390 px plus RTL, reduced-motion and focus variants;
185 measured contrast pairs with 0 connector-owned failures; the reduced-motion
media query emulated and the computed durations read back.

`[Correction — 2026-07-27, superseding the [Fact — CORRECTION] previously
recorded here.]` The measurement below is real; the root cause recorded
alongside it was false and is withdrawn.

**Measured:** under an `ar_001` session, `<html>`, `<body>` and
`.o_sc_export_diff` all computed `direction: ltr`.

**Recorded cause (false):** "Odoo 19's backend RTL mechanism is rtlcss …
`direction` was never set."

**Actual cause:** `rtlcss` was **not installed in the measuring
environment**. Odoo 19 sets `direction` in `webclient_layout.scss` (lines
22, 73, 84 at the pinned `30bde9ff`) precisely so rtlcss can flip it, and
`run_rtlcss` returns the bundle unflipped when the binary is missing while
still serving it under the `.rtl.` URL. The environment produced a
genuinely LTR render and the conclusion misattributed it to Odoo.
`dir="auto"` made it worse, not better: it resolves from the first strong
character of the *content*, so an Arabic operator reading English operational
data got `ltr`.

Both connector Owl roots now bind `dir` to the user's locale direction, and
`u3-export-diff-refusal-and-tag-removal-rtl-1366px.png` is the rendered proof
that the S7 surface mirrors. **This is the clearest case in the batch for why
rendered evidence was required: the structural implementation was real, and its
effect was nil.**

`[Fact]` **Item 7 — `ui-u2-copy-deck.md` now exists**
([`../06-prompts/ui-u2-copy-deck.md`](../06-prompts/ui-u2-copy-deck.md)), as an
evidence record of shipped copy.

`[Fact]` **Item 8 — U2's action controls are now driven in a browser.** All
four sanctioned controls, by an allowed role and by a refused role, with the
resulting database state asserted, inside a rolled-back transaction and with no
Shopify contact. Three UI/server disagreements were found by doing it — one of
them P1: `Confirm First Push` was visible only in the state the server refuses,
so the sanctioned confirmation was unreachable from the shipped UI. Full record:
[`ui-u2-validation-results.md`](./ui-u2-validation-results.md) §3.

`[Fact]` **Item 6 stands.** The HOOT suite still imports `mailModels` from
`@mail/../tests/mail_test_helpers`, so the unit bundle remains coupled to
`mail` being installed.

`[Fact — record correction]` An earlier report of this branch's work stated
that the session preceding this one added **six** commits. It added **seven**:
`5d6f1f5`, `f21f7bb`, `947096f`, `a9e515f`, `940b890`, `a4a9805`, `e117a2e`.
Recorded here rather than by editing the earlier sentence.

---

## 6. What this file does not claim

- **No Odoo.sh runtime acceptance.** DEC-041 D8 keeps the exact-SHA Odoo.sh
  run as the Tier-1 authority; nothing here substitutes for it.
- **No independent review.** The implementing session may not review its own
  work (CLAUDE.md §13).
- **No live-Shopify evidence.** `M-EXP-1`..`M-EXP-20` remain outstanding, and
  `X-EXPORT-0` remains an API-version hard stop that is neither PASS nor FAIL.
- **No UAT, no release readiness, no acceptance of any Wave 5 gate.**
