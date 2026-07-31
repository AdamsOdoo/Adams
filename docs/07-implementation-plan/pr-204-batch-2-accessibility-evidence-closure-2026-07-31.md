# PR #204 — Batch 2 accessibility and evidence closure

> **2026-07-31. Implementation record only.** NOT an acceptance, NOT a review,
> NOT a ready-mark, NOT a merge, NOT self-accepted, and NOT an Odoo.sh,
> live-Shopify, campaign or UAT claim. PR #204 stays **draft and open**.
>
> Companion to
> [`pr-204-batch-2-p0-merchant-reachability-2026-07-30.md`](pr-204-batch-2-p0-merchant-reachability-2026-07-30.md)
> and to the Batch 2 real-data correction that ends at `fc80cd8`. It does not
> reopen either one's accepted scope: F1–F11 stand exactly as the independent
> review left them, and nothing in this session redesigns, revisits or
> re-argues any of them.

| Item | Value |
| --- | --- |
| Starting head (control-room verified) | `fc80cd8c881180c2c76843683672b1198ee9f0ee` |
| Correction parent (merge base with the previous cycle) | `ccad8bf432868650abb80bfb2103bd8d397be549` |
| Final executable / test / tooling head — the head every result below was measured at | `65cf84a1fe954423db8665896d3bba80c83bea4c` |
| Final repository head | the documentation/evidence tail that follows `65cf84a`. **A commit cannot contain its own SHA**, so this record names the executable head it describes and the PR body names the repository head; the tail changes no executable, test or tooling file, which a changed-path comparison against `65cf84a` shows |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, verified ancestor of the head) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, checked out and verified for every run |
| History operation | **Additive only.** No rebase, reset, amend, squash or force-push |
| Shopify | **`shopify_operations = none`** — no store, credential, request, mutation or webhook |

---

## 1. What this session closes, and what it deliberately does not

The independent review of `fc80cd8` accepted the correction and confirmed
F1–F11, the mutation-quality pass, the 147 focused tests and the before/after
reproduction (13 failures at `ccad8bf`, zero at `fc80cd8`). It left **three
browser/accessibility evidence findings** open. Those three, and the one
low-severity finding it asked to be recorded rather than fixed, are the whole
of this session.

| Finding | Closed by |
| --- | --- |
| **A. Live-region truthfulness** — static instructional bands declared `role="status"`, a live region, on copy that cannot change | §2 — four bands re-ruled to `role="note"`, adjudicated one by one, with a rendered + declared test that fails if any of it is reverted (counterfactual: **6 declarations named, 1 failed of 1**) |
| **B. Connector-owned clipping coverage** — four of the six Batch 2 surfaces produced ZERO connector-owned measurement, and the two that did could not say which dialog they were about | §3 — inert surface markers, a marker-attributed instrument, and a per-surface × per-width coverage test that fails on a zero (**18/18 rows PASS**; counterfactual: **18/18 rows expose the zero**) |
| **C. Per-surface RTL proof** — the matrix accepted a surface on `any(...)` evidence measured somewhere else in the run | §4 — every row now carries its own proof, taken while that exact surface was visible (**99 rows, 0 unproved**) |

**Not touched, by instruction:** fulfillment reconnect catch-up; inventory
scheduling truthfulness; the merchant operating guide; the historical-order
backfill wizard; large-catalog redesign; tax-remapping lifecycle; bulk product
export; refunds/cancellations/accounting expansion. Every one of them remains
exactly where the previous cycle left it, and the deferred post-UAT backlog in
the technical-debt register is **unchanged apart from the one row this session
was told to add** (TD-025). TD-004, TD-005, TD-007, TD-020, TD-023 and TD-024
are retained byte-for-byte.

**Recorded, not fixed:** the privileged job-existence oracle, as **TD-025**
(§6).

**No connector functional workflow changed.** No model, service, importer,
exporter, dispatcher, job, security rule, ACL or transport file is in the diff
(§7).

---

## 2. Finding A — live-region truthfulness

### 2.1 The ruling

A band that is **on screen when the surface receives focus** and **cannot
change while it is on screen** is document structure, not a live region —
whatever visual class it uses. WAI-ARIA 1.2 §5.3.2 lists the live-region roles
as `alert`, `log`, `marquee`, `status` and `timer`; `note` is deliberately not
among them, and that is the recorded answer for every one of these bands.

The bands carried `role="status"` because they use an `alert-*` **visual**
class and Odoo's view validator asks for a live role when it sees one
(`ir_ui_view.py::_validate_classes` at the pin: *"An alert (class alert-\*)
must have an alert, alertdialog or status role or an alert-link class"*). That
is a presentational heuristic standing in for a semantic decision. It is
**accepted rather than obeyed**: obeying it means declaring a region that
promises to announce a change and has none to announce. The same answer was
already recorded for the withdrawal dialog's note band in Batch 1, and the
repository already carried one such band before this session
(`shopify_connector_inventory_wizard_views.xml`, `alert alert-info` +
`role="note"`), so the validator emits a warning per band and no error. The
count moves from **1 to 5**; nothing else about module loading changes.

The `alert-*` classes are **kept**. They are why the leading band reads as the
reason the dialog opened rather than as one more paragraph, and rule 5 requires
the note to remain readable. Only the role changed.

### 2.2 The adjudication table

Every `role="status"`, `role="alert"`, `role="note"` and explicit `aria-live`
declared on the six Batch 2 surfaces, read from the **combined view arch**
(`get_view`, inherited views included — so bands hidden by `invisible` for the
fixture's record, and notebook pages the browser has not rendered, are in the
inventory too). **16 declarations. Zero `aria-live` anywhere. Zero `alert-*`
bands without a role.**

| Surface | Band | Was | Now | Ruling |
| --- | --- | --- | --- | --- |
| `b2-tax-decision-dialog` | *"This order stopped because Shopify charged a tax…"* (`alert alert-info`) | `status` | **`note`** | **Corrected.** On screen the instant the dialog opens; the same sentence for every stopped order; nothing an administrator does in this dialog changes a word of it. A live region with nothing to announce. |
| `b2-tax-decision-dialog` | *"Only active sale taxes of this store's order company…"* (`text-muted`) | `note` | `note` | Retained. Static explanatory copy; measured identical before and after a real refusal. |
| `b2-product-match-decision-dialog` | *"This import stopped because more than one Odoo record…"* (`alert alert-info`) | `status` | **`note`** | **Corrected.** Same shape and same reasoning as the tax dialog. |
| `b2-product-match-decision-dialog` | *"Only records of this store's company that still carry…"* (`text-muted`) | `note` | `note` | Retained. Static; measured identical across the refusal. |
| `b2-product-match-decision-pending` / `-resolved` | *"This import is waiting for a decision."* (`alert alert-warning`, `invisible="state != 'pending'"`) | `status` | **`note`** | **Corrected.** `invisible` on a record form is evaluated against the record that was LOADED, not a live update. The band is already on screen when the form receives focus, and `pending` becomes `confirmed` only through a modal that moves focus and a re-read afterwards. |
| `b2-product-match-decision-pending` / `-resolved` | *"Superseded."* (`alert alert-secondary`, `invisible="state != 'superseded'"`) | `status` | **`note`** | **Corrected.** Same reasoning. Proved by genuinely superseding a decision through `_supersede_stale_siblings` and rendering the result. |
| `b2-product-match-decision-pending` / `-resolved` | *"A decision belongs to one exact version of one Shopify record…"* (`text-muted`) | `note` | `note` | Retained. Static. |
| `b2-store-settings-canonical` | four `text-muted` bands (core onboarding, product import, inventory schedule, order schedule) | `note` | `note` | Retained. Static explanatory copy; measured identical across a real field edit on the same form. |
| `b2-store-form-controls` | *"This store's API health is degraded."* (`alert alert-warning`, `invisible="api_health_state != 'degraded'"`) | `alert` | `alert` | **Adjudicated, not edited.** A standing-condition banner owned by `shopify_connector_product_export` (S25) — not an instruction, and `alert` is the role its own view records as deliberate. Outside this correction's allowed files. Not rendered in this fixture (healthy connected store), which the rendered half asserts. |
| `b2-store-form-controls` | *"This store is not connected."* (`alert alert-info`, `invisible="state == 'connected'"`) | `alert` | `alert` | **Adjudicated, not edited.** Same ruling. |

**No connector-owned live region remains on any of the six surfaces**, and the
rendered half asserts that directly: zero regions with a live-region role or
`aria-live` inside any connector-owned Batch 2 root, in every state measured.

### 2.3 The test

`TestUiVisualEvidence.test_batch2_live_regions_are_truthful` asserts in two
halves, and neither can pass vacuously.

**Declared** (the arch of all six surfaces):

* no band claims a live-region role or `aria-live` unless it is adjudicated by
  name — and every adjudication must still match something, so the list cannot
  rot into exemptions for bands that no longer exist;
* every `alert-*` band carries some role;
* no `role="note"` carries `aria-live`;
* the four re-ruled bands are present, as `note`, pinned by a fragment of the
  sentence each one actually says — so restoring the role, or keeping the role
  and rewriting the band, fails here.

**Rendered** (real headless Chromium, the real surfaces):

* every surface renders its adjudicated bands **visible and non-empty** — a
  static note nobody can see is not readable;
* **no live region is rendered** inside any connector-owned Batch 2 root;
* the notes survive a **real production state change on the same visible
  surface**: both dialogs are submitted with their mandatory choice empty, and
  the note text must be byte-identical before and after;
* the **refusal** is still announced assertively and attributed to exactly one
  field — the one the arch declared required (SC 3.3.1 / SC 4.1.3);
* the pending and superseded bands are proved to be a function of the **loaded
  record** rather than of a live update: the pending band renders on a pending
  decision and is absent from a resolved one, and the superseded band appears
  only after the model's own `_supersede_stale_siblings` has genuinely retired
  the decision — driven by raising a second, newer ambiguity for the same
  Shopify product through the production `_route_failure` seam, never by
  writing the state the test wanted to photograph.

**What was deliberately NOT done.** The earlier reviewer's suggestion — make
the static dialog instructions differ between fixture values so a `status`
region could be shown to change — is not implemented. It would prove the wrong
contract: the band's whole defect is that it *cannot* change, and manufacturing
a difference would preserve the false semantics and test the manufacture.

**One host-framework limitation is disclosed rather than asserted around.**
Odoo 19 at the pin announces a refused save as the bare string *"Missing
required fields"* (`Record._displayInvalidFieldNotification`,
`web/static/src/model/relational_model/record.js`), which no form controller
overrides. The announcement names no field. The refusal **is** announced —
`role="alert" aria-live="assertive"` — and the **attribution** is carried in
the DOM instead: exactly one field is marked invalid, and it is the one the
connector's arch declared required. The test asserts only those two facts, and
the artifact records the measured notification text.

---

## 3. Finding B — connector-owned clipping coverage

### 3.1 What was wrong

`OVERFLOW_JS` names its measured roots explicitly, and knew three Owl surfaces
plus a generic `.modal-body`. Four of the six Batch 2 surfaces are ordinary
Odoo form views and matched none of them, so they produced **no connector-owned
measurement at any width, in either direction**, while the campaign counted
them as covered. The two that did match matched only through Odoo's modal
chrome — the same string for every dialog — so their rows could not say which
screen they were about, and any dialog at all would have satisfied either row.

### 3.2 The markers, and why they are shaped the way they are

Five inert classes, declared in the connector's own view arch, carrying no
styling anywhere and selected by no stylesheet:

| Marker | Declared on | Why there |
| --- | --- | --- |
| `o_sc_store_settings` | `<sheet>` of the canonical Store Settings form | a `class` on `<sheet>` lands on Odoo's `.o_form_sheet_bg` — the box the form's content is actually laid out in. **No element is added.** |
| `o_sc_store_form` | `<sheet>` of the store form | same |
| `o_sc_match_decision` | `<sheet>` of the match decision record form | same |
| `o_sc_tax_decision` | the tax dialog's leading band | a wizard form has no `<sheet>` — see below |
| `o_sc_match_decision_wizard` | the match dialog's leading band | same |

**Why the two dialog markers are on a band and not on a wrapper, measured
rather than argued.** Marking a dialog body *as a box* meant interposing a
plain block `<div>`, and `<group>` compiles to a Bootstrap `.row`, whose
negative gutter margins put its children 8px outside any intermediate block box
on each side. Measured, that wrapper reported a **16px
`unhandled_self_overflow` at every width** (962/946 at 1366px, 632/616 at
768px, 374/358 at 390px) with `overflow-x: visible` — on content that is not
clipped and never was: the form's own horizontal padding absorbs the gutters
exactly as it did before the wrapper existed, page overflow stayed 0,
`escaped_descendants` stayed empty, and both `.modal-body` and the wizard's own
form root reported zero self-overflow throughout. That is an artefact of
introducing a box, not a connector defect. **No production CSS was written to
make a green number appear, and no box is added**: the markers are declared on
a band that is already there, the dialogs keep the roots Batch 1 measured (the
modal **body** and the wizard's own form root), and attribution is carried by a
new `markers` field instead.

### 3.3 `markers`, and why `cls` was not enough

`copyAttributes` **appends** an arch `class`, so a
`<sheet class="o_sc_store_settings">` renders as
`class="o_form_sheet_bg o_sc_store_settings"` — and the instrument's `cls` is
the element's *first* class. Four different screens all report
`o_form_sheet_bg`. Every measured root now also reports `classes` and
`markers` (every `o_sc_*` on the root or anywhere inside it), and the
per-surface matrix is keyed on markers.

### 3.4 The test

`TestUiVisualEvidence.test_every_batch2_surface_yields_a_connector_owned_measurement`
opens each of the six surfaces at all three required widths and requires, per
row: at least one **visible** measured root carrying that surface's marker; the
**intended** surface visible under a surface-specific selector; the page not
scrolling horizontally; for the two dialogs, the modal **body** still measured;
the final actionable control — which for a dialog lives in the **footer**,
outside the body — still reachable; and no clipping defect. A named surface
producing zero measurements is a failing row, not a missing one.

`test_the_overflow_instrument_covers_every_connector_surface` now reads
`views/**` and `wizards/**` as well as `static/src/**`, so a marker class
declared in a form arch and left out of the instrument fails rather than going
unmeasured — which is exactly the omission that guard exists to prevent, and
which it could not previously see.

---

## 4. Finding C — per-surface RTL proof

`test_rtl_renders_mirrored_without_overflow` used to accept the campaign on
`any(...)`: one row anywhere in the run showing Odoo's flipped bundle, and one
row anywhere showing `.o_rtl`, satisfied the whole matrix. Every individual
surface could have been photographed in a session that was not in RTL at all.

Each row now carries its own proof, taken while that exact surface was on
screen:

* the **intended** surface is present and visible — not `.o_form_view`, which
  is true of every form in the product. Where a surface is reached by pressing
  a control, the post-open action's own wait selector is used: the S7 export
  diff **replaces** the form it was opened from, so `wait` named a screen that
  is deliberately no longer there, and that row was the first thing the
  stricter assertion caught;
* Odoo's own `.o_rtl` class is applied to **this** page;
* Odoo served at least one rtlcss bundle for **this** page;
* where the connector owns a root with its own stylesheet, that root computes
  `direction: rtl`;
* the surface clips or displaces nothing when mirrored, and the page does not
  scroll sideways;
* and every Batch 2 surface produces one row per required width, with at least
  one visible connector-owned root in it — a row that silently stopped being
  produced would otherwise pass by being absent.

**What is asserted for a plain Odoo form, honestly.** Odoo 19's backend sets no
`dir` on `<html>`/`<body>`; its RTL mechanism is rtlcss bundle flipping. The
connector's Owl surfaces bind `direction` because their stylesheets are written
in logical properties, which resolve against it. The Batch 2 surfaces are
ordinary form views: the connector owns their arch and not their chrome, and no
layer of this repository sets `direction` on them. Their marked roots are
measured for direction and **recorded**; what is **asserted** for those rows is
the signal that actually carries RTL for them. Promoting them into the
Owl-root direction probe would assert a property nothing sets, and would have
made the matrix read better while proving less.

**Counterfactual, recorded honestly:** see §9.3. The stricter per-row RTL
assertions were **not** forced to fail on `fc80cd8` to manufacture a
before/after: the parts of the strengthening that are pure evidence
adjudication (per-row `.o_rtl`, per-row rtlcss bundle, per-row Owl-root
direction, per-row intended-surface visibility once the instrument stopped
naming a screen the post-open action had replaced) already hold at `fc80cd8`,
and that is recorded as an **evidence-adjudication closure** rather than dressed
up as a defect. What does not hold at `fc80cd8` is the Batch 2 half — no
connector-owned root is on screen for four of the six surfaces, so there is
nothing for an RTL row about them to be about. That is finding B seen through
the RTL lens, and it is where the RTL counterfactual actually bites.

---

## 5. Validation

**Bounded to this correction, exactly as instructed.** No seven-pass suite, no
GitHub Actions, no Odoo.sh, no live Shopify, no UAT.

| Pass | Command shape | Result |
| --- | --- | --- |
| The complete rendered UI/accessibility class (contains every changed instrument) | `-u <6 modules> --test-enable --test-tags shopify_connector_visual` | **0 failed, 0 error(s) of 16 tests** (14 at `fc80cd8` → **+2**) |
| Focused Batch 2 browser/tour coverage for the six surfaces | `--test-tags shopify_connector_b2_tours` | **0 failed, 0 error(s) of 10 tests**, **8/8 `tour succeeded` markers** |
| Focused affected core / product / sale tests (dialog and action regression) | `--test-tags /shopify_connector_core,/shopify_connector_product,/shopify_connector_sale` | **0 failed, 0 error(s) of 1404 tests** |
| View installation and validation, from scratch, for every touched module | fresh `-i` of all six connector modules + `account`, `stock` | **`Modules loaded.`**, exit 0, no view error, no new error line against the `fc80cd8` baseline install |
| Genuine version-to-version update `fc80cd8` → candidate | every run above is `-u` against a database installed at `fc80cd8` | `ir_module_module.latest_version` moved **`core 19.0.1.19.0 → 19.0.1.20.0`**, **`product 19.0.2.8.0 → 19.0.2.9.0`**, **`sale 19.0.2.7.0 → 19.0.2.8.0`** — read back from the upgraded database, not asserted from the manifest |

Environment: Odoo pinned and verified `30bde9ff758834a4912c5ae55843d3a7dad849f1`,
Chromium 141.0.7390.37 headless, PostgreSQL 16.13, Python 3.12.3.

**Odoo view-validator warnings: 1 → 5.** The four new ones are the four
re-ruled bands, and they are the deliberate cost of §2.1: Odoo warns on an
`alert-*` class whose role is not `alert`/`alertdialog`/`status`. The
repository already carried one such band before this session
(`shopify_connector_inventory_wizard_views.xml`). They are warnings, not
errors; module loading is unaffected; and they are recorded here rather than
silenced by declaring a live region that has nothing to announce.

**`shopify_operations = none`.** Every transport seam stays patched; no
credential exists in the repository or the environment.

---

## 6. TD-025 — recorded, not fixed

The independently confirmed **privileged job-existence oracle** is recorded as
**TD-025** in [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md):
`_authorized_job` refuses an absent job with `UserError('That job no longer
exists.')` and an inaccessible or cross-company one with the deliberately
opaque `AccessError`, and the match decision route does the same with `'That
match decision no longer exists.'` — so the two outcomes are distinguishable
and iterating ids maps which ids are taken.

No store, company, order, tax, candidate or evidence content is disclosed;
reaching either route at all requires an already-privileged connector role,
re-asserted server-side. Classification **Low / P3, not release-blocking**,
disposition **post-UAT hardening**. **No production code was changed for it in
this session** — model and service behaviour is outside the allowed files.

The reviewer's two speculative sub-P1 observations (a transaction/savepoint
shape and an optimistic-lock shape) are **not** promoted to accepted defects.
Neither has an independently reproduced consequence, and inventing one to
justify a change would be the opposite of what this session is for.

---

## 6b. Scope note, named rather than reconciled

Two files outside the obvious "browser and accessibility" reading were touched,
both as the direct and unavoidable consequence of an instructed change. They
are named here explicitly so the control room can reverse either reading if it
disagrees.

* **`addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js`**
  — two tour steps targeted `.alert-info[role='status']` on the tax and match
  dialogs, i.e. they asserted the semantics this correction rules wrong. They
  now target `[role='note']`, so the ruling is pinned by a real browser journey
  and a silent revert fails the tour. Read as "focused UI/tour tests directly
  supporting this correction".
* **`addons/shopify_connector_sale/tests/test_order_import_mapping.py`** — one
  line. `TestOrderImportMappingStatic` is a deliberate frozen-contract guard on
  the sale manifest and pinned `19.0.2.7.0`. The instruction requires the module
  version to move when loaded XML changes, and that guard's own comment says an
  intended change is *recorded there rather than the guard being relaxed* — so
  the pin moves to `19.0.2.8.0` with the reason written beside it. Nothing else
  in that file changed, and the guard is not weakened.

The `test_no_out_of_scope_ui` source guard also caught one of this session's
own comments: the word *"matching"* is a forbidden out-of-scope token in
`shopify_connector_core/views/*.xml`, and an explanatory comment used it in
passing. The comment was reworded. **The guard was not exempted, relaxed or
edited** — it did its job and the prose moved.

---

## 7. What did not change

* **No model, service, importer, exporter, dispatcher, job or transport file.**
* **No security rule, ACL or group.**
* **No migration script.** The change is view-arch only: no column, no data,
  no schema. Module versions moved because loaded XML changed
  (`core 19.0.1.19.0 → 19.0.1.20.0`, `product 19.0.2.8.0 → 19.0.2.9.0`,
  `sale 19.0.2.7.0 → 19.0.2.8.0`), and the upgrade path was exercised for real.
* **No production CSS.** No connector-owned visual defect was reproduced, so
  none was written — including for the 16px wrapper artefact in §3.2, which was
  removed by not adding the wrapper rather than by styling around it.
* **No Shopify contact of any kind.**

---

## 8. Gates that remain

Independent read-only re-review of the exact final head; exact-head Odoo.sh
qualification; controlled live-Shopify validation; business UAT; control-room
acceptance and merge authorization. This PR stays draft; the implementing
session does not review, accept, ready-mark or merge it.

---

## 9. Recorded results

Artifacts: [`../05-qa/evidence/batch-2-accessibility-closure-2026-07-31/`](../05-qa/evidence/batch-2-accessibility-closure-2026-07-31/).

### 9.1 Six-surface clipping matrix — `batch2-clipping-coverage.json`

**18 rows (six surfaces × three widths), 0 failures.** Every row proved the
intended surface visible under a surface-specific selector, measured at least
one connector-owned root, found zero page horizontal overflow, and reached the
final actionable control.

| Surface | Marker required | Measured root(s) | 1366 | 768 | 390 |
| --- | --- | --- | --- | --- | --- |
| `b2-store-settings-canonical` | `o_sc_store_settings` | `o_form_sheet_bg` | PASS | PASS | PASS |
| `b2-store-form-controls` | `o_sc_store_form` | `o_form_sheet_bg` | PASS | PASS | PASS |
| `b2-tax-decision-dialog` | `o_sc_tax_decision` | `modal-body` + the wizard's own form root | PASS | PASS | PASS |
| `b2-product-match-decision-pending` | `o_sc_match_decision` | `o_form_sheet_bg` | PASS | PASS | PASS |
| `b2-product-match-decision-dialog` | `o_sc_match_decision_wizard` | `modal-body` + the wizard's own form root | PASS | PASS | PASS |
| `b2-product-match-decision-resolved` | `o_sc_match_decision` | `o_form_sheet_bg` | PASS | PASS | PASS |

`o_form_sheet_bg` is where a `<sheet class="…">` lands; the surface each row is
about is carried by `markers`, not by `cls`. The two dialogs keep the modal
**body** in the measured set, and the final control (a dialog's footer button,
outside the body) was reachable on every row.

### 9.2 Six-surface RTL matrix — `rtl.json`

**99 per-surface rows across the whole capture set, 0 unproved.** The 18 Batch 2
rows:

| Surface | `intended` visible | `.o_rtl` | rtlcss bundles | connector root measured | clipping | 1366 / 768 / 390 |
| --- | --- | --- | --- | --- | --- | --- |
| `b2-store-settings-canonical` | yes | yes | 2 | `o_form_sheet_bg` (`o_sc_store_settings`), `direction: ltr` | none | PASS / PASS / PASS |
| `b2-store-form-controls` | yes | yes | 2 | `o_form_sheet_bg` (`o_sc_store_form`), `direction: ltr` | none | PASS / PASS / PASS |
| `b2-tax-decision-dialog` | yes | yes | 2 | the marked band (`o_sc_tax_decision`), `direction: ltr` | none | PASS / PASS / PASS |
| `b2-product-match-decision-pending` | yes | yes | 2 | `o_form_sheet_bg` (`o_sc_match_decision`), `direction: ltr` | none | PASS / PASS / PASS |
| `b2-product-match-decision-dialog` | yes | yes | 2 | the marked band (`o_sc_match_decision_wizard`), `direction: ltr` | none | PASS / PASS / PASS |
| `b2-product-match-decision-resolved` | yes | yes | 2 | `o_form_sheet_bg` (`o_sc_match_decision`), `direction: ltr` | none | PASS / PASS / PASS |

**`direction: ltr` on those roots is recorded, not hidden, and it is not a
defect.** Odoo 19's backend sets no `dir` on `<html>`/`<body>`; it mirrors
through the rtlcss bundle, and no layer of this repository sets `direction` on
an ordinary form view. The connector's own Owl surfaces — which DO bind it,
because their stylesheets are written in logical properties — resolve `rtl` on
every row they appear in, and that is asserted. For the Batch 2 rows the
asserted evidence is `.o_rtl` + a served rtlcss bundle + the intended surface
visible + nothing clipped, all measured while that exact surface was on screen.

### 9.3 Counterfactuals

Each was run by moving the production change back and leaving every test change
in place, so the test is the only constant.

| Counterfactual | Setup | Result |
| --- | --- | --- |
| **A — the four `role="status"` bands restored**, markers and tests untouched | `role="note"` → `role="status"` on the four adjudicated bands only | `test_batch2_live_regions_are_truthful` **FAILS**, naming **6 declarations** (the four bands; the two record-form bands are declared on both the pending and resolved surfaces) as *"these Batch 2 bands declare a live region that nobody has ruled on"*. `1 failed, 0 error(s) of 1 test` |
| **B — the four view files exactly as at `fc80cd8`** (no markers, roles back to `status`) | `git checkout fc80cd8 -- <4 view files>` | `test_every_batch2_surface_yields_a_connector_owned_measurement` **FAILS** with **18 of 18 rows** carrying `no_connector_owned_measurement` *and* `intended_surface_not_visible` — every one of the six surfaces, at every width |
| **C — RTL, same `fc80cd8` view tree** | as above | `test_rtl_renders_mirrored_without_overflow` **FAILS on exactly 18 rows**, all Batch 2, all for the single reason *"the intended surface … is not visible"*. **The other 81 rows passed**: `.o_rtl` was true, an rtlcss bundle was served and every Owl root resolved `rtl` on each of them individually |

**C is recorded honestly as an evidence-adjudication closure, not a
manufactured before/after.** The part of the RTL strengthening that replaces
`any(...)` with per-row proof of `.o_rtl`, the rtlcss bundle and the Owl-root
direction **already held at `fc80cd8`** for every surface, and nothing was
invented to make it fail. What did not hold there is the Batch 2 half — no
connector-owned root is on screen for those six surfaces, so an RTL row about
them had nothing to be about. That is finding B seen through the RTL lens, and
it is where the RTL counterfactual actually bites.

### 9.4 Live-region inventory

**16 declarations across the six surfaces. 14 `role="note"`, 2 `role="alert"`
(both foreign, both adjudicated, neither rendered in this fixture). Zero
`aria-live` anywhere. Zero `alert-*` bands without a role. Zero live regions
rendered inside any connector-owned Batch 2 root, in every state measured.**
The full table is §2.2; the machine-readable record is
`batch2-live-region-semantics.json`.

### 9.5 Worktree

Clean at completion. `.odoo-src`, `.connector-venv` and `ci-artifacts-*/` are
gitignored and are not part of the commit.
