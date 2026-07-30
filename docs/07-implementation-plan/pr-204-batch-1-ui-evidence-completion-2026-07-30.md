# PR #204 — Batch 1 UI and evidence completion

> **2026-07-30. Implementation record only.** NOT an acceptance, NOT a review,
> NOT a ready-mark, NOT a merge, NOT self-accepted, and NOT an Odoo.sh,
> live-Shopify, campaign or UAT claim. PR #204 stays **draft and open**.
>
> Companion to
> [`pr-204-batch-1-consolidated-correction-2026-07-30.md`](pr-204-batch-1-consolidated-correction-2026-07-30.md),
> which this completes. It does not reopen that correction's accepted scope.

| Item | Value |
| --- | --- |
| Starting head (control-room verified) | `2e4f4278dc14a508408b1e8a3900a3c987f12d77` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, verified ancestor) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run |
| History operation | **Additive only.** No rebase, reset, amend, squash or force-push |
| Shopify | **none** — no store, credential, request, mutation or webhook |

---

## 1. What this closes

The implementing report at `2e4f4278` named three proof gaps in its own work.
This session closes all three, and nothing else.

| Gap admitted at `2e4f4278` | Closed by |
| --- | --- |
| No mounted-component HOOT coverage for the location client rework | §2 — ten HOOT tests, each proved against the absence of the property it claims |
| No real-browser journey through the mapping-level bulk-withdrawal wizard | §3 — four tours, five tests, driven through the real action/view/wizard/service chain |
| No fresh responsive / RTL / keyboard / zoom / reduced-motion campaign for the changed surfaces | §4 — six new surfaces, three new measured dimensions, 90-row zoom matrix |

Three defects were reproduced along the way. All three are **production**
defects — two in the client, one that made a security control inert — and each
is fixed with a regression that fails without the fix (§5).

---

## 2. The location client, tested as the protocol it is

`addons/shopify_connector_core/static/tests/shopify_connector_setup_wizard.test.js`
— ten tests, taking the suite from 20 to 30. The HOOT suite inventory in
`test_u3_hoot_suite.py` moves in the same commit, which is what that inventory
is for.

**The fake server enforces the real contract rather than answering whatever it
is asked.** It refuses a continuation that does not belong to the `(side,
query)` being paged, exactly as `search_location_options` does, and it issues a
`next_offset` deliberately skewed away from the number of rows the client is
holding — so a client that derives its position locally asks for the wrong rows
and fails an assertion, instead of passing because the two numbers happened to
agree. Overlap is driven with a held `Deferred`; there is no sleep and no
timing luck anywhere.

| Behaviour proved | How the assertion can fail |
| --- | --- |
| Search obeys `state.busy` | the flag and the `disabled` bindings it drives are read while a response is held open |
| No overlapping search, load-more, clear or mapping is admitted | four overlapping actions against one held response; the request count and the held kwargs are identical afterwards |
| Load more sends the SERVER's `next_offset` | the fixture's position is `real + 100`, so a length-derived offset fetches the wrong slice |
| A new query and a clear invalidate the old continuation | the fixture refuses a mismatched token, so a stale one lands on screen as the refusal |
| Pages accumulate, deduplicated by identity | the set is shifted between pages so one row is served twice |
| A mapping updates its row in place | four accumulated rows survive, one badge moves, and no further page is fetched |
| Selections are revalidated after search, clear and load more | a chosen location is searched away and the `<select>` value is read back |
| A stale, off-screen or foreign identity is refused at submit | three cases, each asserting no `save_location_mapping` was issued |
| The Shopify list's empty states are distinguishable, and a fruitless search keeps its way out | two reasons, two sentences, and the search row/Clear/Map controls asserted present |
| The Odoo list distinguishes no match, no access and no warehouse | three reasons, three distinct sentences |

### 2.1 Mutation proof

Each test was run against a production client with the property it claims
removed. Seven mutations, seven catches, one to one, no collateral:

| Mutation of the production client | Caught by |
| --- | --- |
| busy discipline removed from `_searchLocations` | *the location search obeys the same busy discipline…* |
| busy guard removed from `clearLocationSearch` | *no second search, load-more, clear or mapping is admitted…* |
| `offset: search.items.length` instead of `nextOffset` | *load more sends the server's own next_offset…* |
| clear keeps the continuation it should drop | *a new query and a clear both invalidate the continuation…* |
| deduplication removed | *pages accumulate and are deduplicated by identity…* |
| mapping re-runs the search instead of updating in place | *mapping a location updates that row in place…* |
| revalidation calls removed | *a selection is revalidated after every search, clear and load more* |

---

## 3. The bulk withdrawal, driven end to end

`shopify_connector_u2_action_tour.js` (four tours) and
`test_ui_u2_action_tours.py` (five tests). Service-level tests cannot see any
of what goes wrong here, because all of it is on the way **in**.

* **The full journey.** The control is opened by keyboard from the mapping
  form. Every count is read from its own labelled field — a bare
  `:contains('3')` would be satisfied by any 3 anywhere on screen — so
  `total_pairs=4`, `affected_pairs=3`, `previewed_pairs=1`,
  `confirmed_pairs=2` and `pairs_live_on_shopify=2` are each asserted
  individually, and the fixture's own preview is cross-checked in Python so a
  drift breaks the test rather than making the tour assert the wrong numbers
  quietly. The storefront consequence is asserted as **words and a number**,
  and the copy is asserted to say the quantities STAY rather than implying
  they were reverted. Both refusals are driven: an empty reason (refused
  before the request is sent) and a reason without the consequence
  confirmation (refused by the service, with the refusal on screen).
* **The database consequence**, which the screen cannot show: three pairs to
  `pending` with preview quantity, confirmation stamp and confirming user
  cleared; the fourth untouched; `last_pushed_at` preserved, because the
  dialog says those quantities stay; audit entries at **both** levels — one
  stating 3 of 4 and how many are live, one per withdrawn pair, and none for
  the pair that was not withdrawn.
* **Staleness, at both routes.** The interference is a real concurrent
  operator action issued from the browser through the same RPC endpoint the
  web client uses — the pair form's own `action_confirm_first_push` — and the
  step re-reads the pair and throws if it did not move, so the refusal can
  never pass because nothing happened.
* **Absence for a Connector User**, asserted by reading every button in the
  form header rather than by a CSS selector that cannot express it
  (`:contains()` is a hoot-dom extension and is not valid CSS, so it cannot
  appear inside `:not(:has())`). The server's refusal at all three layers
  beneath — preview, service and wizard `create` — is proved alongside.
* **No Shopify request**, structurally against the source of all four service
  methods and behaviourally: the only jobs created are lifecycle audit rows,
  and no mutation attempt exists.

---

## 4. The campaign, aimed at the surfaces the correction changed

`test_ui_visual_evidence.py`. Artifacts:
[`docs/05-qa/evidence/batch-1-ui-completion-2026-07-30/`](../05-qa/evidence/batch-1-ui-completion-2026-07-30/README.md).

Six surfaces added, each reached by **doing** what produces it, with a
post-open action that waits for its own completion and fails loudly rather than
leaving the previous screen to be photographed under the new name. The location
fixture goes from 6 rows to 60 — the smallest set that renders a full 50-row
page, offers Load more, and then exhausts. With six, the paged surface the
correction rebuilt was never on screen at all.

| New surface | What it puts on screen |
| --- | --- |
| `s1-setup-credential-dev-dashboard` | the two-path authentication chooser, default path |
| `s1-setup-credential-offline-token` | the same chooser, offline path selected |
| `s1-setup-location-search-results` | a search with results, its counter and Clear |
| `s1-setup-location-loaded-more` | a full page plus a second page accumulated |
| `s1-setup-location-no-result` | the zero-result state that must keep its way out |
| `u2-first-push-withdraw-dialog`, `u2-location-withdraw-all-dialog` | both withdrawal dialogs, opened by pressing the control |

Three dimensions that had **no** measurement before:

* **200% zoom — 90 rows, all PASS.** Not a fourth width: the viewport narrows
  *and* the type grows, so 683px at 200% holds the content of a 341px column
  at normal size. 10 surfaces × 3 device widths × LTR/RTL × {zoom, zoom under
  reduced motion}. Each row records the selector, device width, resulting CSS
  width, direction, zoom, motion preference, every connector surface's
  `scrollWidth`/`clientWidth`/overflow/clipping, the page's own horizontal
  overflow, whether the **final actionable control** is reachable after being
  scrolled into view, and a verdict. The mobile row is measured at **320 CSS
  px** — SC 1.4.10's reflow width — not at the 195 that halving 390 produces
  and that no criterion requires and no browser lays out for.
* **Keyboard-only traversal — 10 of 10 reached**, in 4 to 28 real
  `Input.dispatchKeyEvent` Tab presses. A dispatched `KeyboardEvent` does not
  move focus at all: sequential navigation is the browser's own behaviour, so
  a test built on one would pass on a surface with no tab order.
* **Alert and note semantics.** Each role has to be **earned**. The credential
  guidance is `role="status"` and its text is measurably different between the
  two authentication paths — a document role would announce nothing at the
  moment the guidance silently became different guidance. The withdrawal
  dialog's `role="note"` band is measurably identical before and after the
  operator fills the dialog in, which is why it is document structure and a
  live region would announce a sentence nothing changed about. This is also
  the recorded answer to Odoo's own view-validator warning about an `alert-*`
  class without a live-region role: the class is presentational and the copy
  is static.

**No connector-owned visual defect was reproduced**, so no production CSS was
changed.

### 4.1 Three defects in the instruments, found by using them

An instrument that lies is worse than no instrument, so these are recorded
rather than quietly fixed:

1. `document.querySelector("a, b")` returns the first match in **document
   order** of either selector, so with a dialog open the surface root resolved
   to the form *behind* the modal — and the "final actionable control" was one
   the modal had made unreachable. Priority order now.
2. That root was `.modal-body`, which excludes the footer, so a dialog's real
   final controls (Confirm, Cancel) were never measured. `.modal-content` now.
3. An RTL row for a surface with no `o_sc_*` root recorded a direction it could
   not show had taken effect. Odoo's `.o_rtl` class and flipped-bundle count
   are carried too, and a row labelled RTL with nothing behind it now fails.

### 4.2 One host-framework limitation, disclosed

Odoo 19 at the pinned commit marks an invalid field with the class
`o_field_invalid` and **emits no `aria-invalid` anywhere in
`web/static/src`**. That is Odoo's form chrome, not connector arch, and is not
fixable from this repository without patching core.

It is recorded in `batch1-aria-semantics.json` under
`host_framework_limitation` rather than asserted away. What the connector's own
arch decides *is* asserted: the reason field is `required`, so the refusal is
raised before the request is sent, attributed to `reason`, and announced
through Odoo's `role="alert" aria-live="assertive"` notification.

---

## 5. Defects reproduced, and the minimal corrections

### 5.1 A clear during an in-flight search was undone by the response

`clearLocationSearch` had no busy guard. Clearing is not a server call, so it
looked safe outside the discipline — but a clear issued while a search is in
flight is **undone** by the response that lands after it: the handler assigns
`search.items` unconditionally, leaving an empty query box, the old query's
results beneath it, and a continuation token belonging to a query no longer on
screen. The next Load more sends that token with an empty query and is refused
by the server, which is a refusal with no visible cause.

**Fix:** the same `state.busy` guard every other call obeys, and
`t-att-disabled="state.busy"` on both Clear buttons so the screen says so.
**Regression:** *no second search, load-more, clear or mapping is admitted
while one is in flight*, which fails when the guard is removed.

### 5.2 A cleared side lost a key its initialiser declares

The same method rebuilt the side's state without `emptyReason`, so a cleared
side and a never-searched side had different shapes. Restored: a state object
that loses a key on a routine operator action is how a reader starts seeing
`undefined`.

### 5.3 The staleness snapshot never reached the server — **security-relevant**

`expected_signature` (mapping-level) and `expected_state` (single-pair) are
`readonly` fields declared in their wizard views. **A readonly field is
excluded from what the web client sends on save** — `_getChanges` in
`web/model/relational_model/record.js` skips it unless `forceSave` — so the
state each dialog was opened against never left the browser. The record is new,
so `create()` filled the gap from `default_get`, recomputing the state **at
save time**: precisely the state the check exists to detect having moved.
`signature == signature` and `state == state` could not fail.

Both staleness refusals were therefore **inert at the only surface that uses
them**, and the Batch 1 correction that made `expected_state` mandatory
protected every caller except the wizard it was written for.

**Fix:** `force_save="1"` on both fields. **Proved load-bearing rather than
asserted:** with it removed, both stale tours fail at the refusal step and the
withdrawal is applied against information that had already changed; with it
restored, both refuse.

---

## 6. What is NOT claimed

* **No Odoo.sh run.** This is local and GitHub-Actions evidence only
  (DEC-041 D8 keeps exact-SHA Odoo.sh as the Tier-1 authority).
* **No live Shopify contact of any kind**; every test patches `_send`,
  `_send_lifecycle` and `_send_token_exchange`, and no real credential exists
  in the repository or the environment.
* **No UAT, no acceptance, no ready-mark, no merge, no approval.**
* **No independent review of this head.** This session implemented; it does not
  review, accept, ready-mark or merge its own work.
* Authentication and TD-020 remain **"implemented, pending independent
  re-review"** — never "resolved".
* Batch 2 is untouched. TD-004, TD-005 and TD-007 are retained byte-for-byte.

## 7. Remaining gate

Independent read-only Batch 1 re-review of the exact final head, then the
gates already recorded in the consolidated correction record §5.
