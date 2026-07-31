# PR #204 — Batch 2 P0 merchant reachability

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

> **This record supersedes its own earlier text and says so explicitly.** The
> version written at `9af8b23` stated that the commits were *"local only"* and
> that *"the branch `fable/wave-5-completion` remains at `b0dbba2a`"*. Both
> were true when they were written and became stale the moment the control
> room ruled that the durability recovery is accepted as preservation of
> provisional work. They are corrected below rather than deleted: the
> historical fact that the chain was unpushed at `9af8b23` is part of this
> campaign's record, and rewriting it away would be the same kind of quiet
> revision this project exists to avoid.
>
> **Nothing here is acceptance.** Every push described below is a preservation
> checkpoint. The work remains provisional until independent review.

## 1. Heads and history

| | |
| --- | --- |
| Batch 2 starting baseline | `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e` |
| Durability-recovery head (control-room verified) | `cb4efcde13792920275f0fd8edc0c06226b94fe9` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run |
| History | **additive only** — no amend, rebase, squash, reset or force-push |

### The additive chain

| Commit | What it is |
| --- | --- |
| `9a70682` | checkpoint 1 — canonical Store Settings |
| `f5f3668` | checkpoint 1 — the guards the new surface had to answer to |
| `39e5113` | checkpoint 2 — order controls and tax decisions |
| `2c5d190` | checkpoint 3 §8.1 — product enumeration producer |
| `9af8b23` | Batch 2 records (the ones this section corrects) |
| `cb4efcd` | restore the research handoff a prepend had truncated |
| `be7cc43` | §8.2 durable match decisions, §8.3 tests, §9 journeys |
| `68410fb` | §10 browser/accessibility campaign, records, TD-021/TD-022, handoff |
| `153be2b` | the tour-instrument correction the definitive run's migration pass found — **final executable/test/tooling head** |
| *(final)* | this validation record — documentation only, zero executable/test/tooling delta against `153be2b` |

### The handoff truncation, and the fix-forward

`cb4efcd` exists because a prepend to `docs/01-research/research-handoff.md`
replaced the file instead of extending it. The correction is **additive**: the
truncated content was restored forward as a new commit rather than by amending
the commit that lost it. The net delta of that file against `b0dbba2` is
**+104 / −0**, which is the check that the restoration put back exactly what
was lost and nothing else.

### Commit signing

Unavailable in this environment: the configured signing key is empty. Unsigned
additive commits are the accepted implementation deviation for this campaign,
per the control-room ruling. **No commit was amended, rebased or recreated to
obtain a signature** — doing so would have destroyed the additive history the
same ruling protects.

## 2. What Batch 2 set out to close, and where each part stands

| § | Deliverable | State |
| --- | --- | --- |
| Checkpoint 1 | Canonical Store Settings | Implemented (`9a70682`, `f5f3668`) |
| Checkpoint 2 | Order controls and the tax decision route | Implemented (`39e5113`) |
| §8.1 | Product enumeration producer | Implemented (`2c5d190`) |
| **§8.2** | **Durable product/variant match decisions** | **Implemented (`be7cc43`)** |
| **§8.3** | **Load-bearing product matching tests** | **Implemented (`be7cc43`)** |
| **§9** | **Consolidated vertical journeys C, D-P0, I, J-P0, K-P0** | **Implemented (`be7cc43`)** |
| **§10** | **Consolidated browser/responsive/accessibility campaign** | **Implemented (final head)** |
| §15.2 | Definitive seven-pass validation | **All seven passes green at `153be2b`** (§9 below) |

Checkpoints 1, 2 and §8.1 are described in §§3–5 of the retained record below.
This section covers what the continuation added.

## 3. §8.2 — the decision an ambiguous match never recorded

### The defect

When two Odoo products carry the SKU a Shopify product claims, the importer
refuses. That is correct: silently picking one binds a store's catalog to the
wrong master data. But refusing was the whole of it.

* `ambiguous_match` is a `MANUAL_REVIEW` class, so the dispatcher routes the
  job to `blocked_manual_review` — asserted against the dispatcher's real
  taxonomy, not against the phrase "blocked work".
* Both raise sites carried a human sentence and **no structured
  `technical_detail`**, so nothing downstream could tell which product, which
  variant, or which candidates the importer had seen.
* The only offered control was the generic `action_resolve_manual_review`,
  which re-queues the identical job so the identical search finds the identical
  two candidates and stops again. A merchant could press it forever.

### Why the decision cannot be written where the ambiguity is found

Both raise sites (`_resolve_template`, `_match_variant_candidate`) run inside
`import_product_sync`'s single `self.env.cr.savepoint()` block — the block that
exists so a failure half-way through a product leaves no partial product
behind. A decision created there is discarded by the same `ROLLBACK TO
SAVEPOINT` that discards the partial writes.

That is **measured, not assumed**:
`test_a_decision_written_inside_the_importer_savepoint_would_not_survive`
patches `_resolve_template` to create a decision immediately before the raise,
drives the real drain, and asserts the row is gone — while the production seam
records its own in the same run. If that ever stops being true the seam can be
simplified; while it is true, the seam is the only correct place.

So the evidence travels out on the exception — structured, sanitized and
size-bounded on `JobHandlerError.technical_detail` — and the decision is
written by a **product-owned override of `_route_failure`**, in the same
transaction that durably records the blocked job. `super()` is called first, so
the job is transitioned before anything is linked to it and a failure to record
can never leave the job un-routed. No second queue, no second dispatcher, no
side channel.

### The invariants, and what enforces each

| §8.2 requirement | What enforces it |
| --- | --- |
| 1. linkage (store, company, job, product GID, variant GID, remote identity, level, evidence, candidates, state) | Model fields on `shopify.connector.product.match.decision`, all `readonly=True` |
| 2. no secret or unnecessary PII | `safe_match_preview` — secret patterns, then email/phone, then a length bound, on every merchant-controlled string |
| 3. company-aware candidates, bound records excluded | `eligible_candidates()`; the exclusion set is read under `sudo()` **on purpose** — elevating an exclusion can only ever remove a candidate |
| 4. priority: binding → SKU → barcode → manual | The decision is consulted only where identifier matching has already produced an ambiguity |
| 5. never match by name | Unchanged (RA-006); `MATCH_KEYS` admits only `sku_reference` and `barcode` |
| 6. Reviewer or Administrator resolve; Operator may start, not decide | `_assert_match_decision_reviewer` — the same two groups `action_manual_retry` admits from `blocked_manual_review`, so the dialog cannot offer a consequence its caller would then be refused |
| 7. same-company eligible record only | Odoo's own `_check_company` (`_check_company_auto` + `check_company=True`), which holds under `sudo()` |
| 8. no "create new" | Not added |
| 9. confirm-time revalidation | `_validated_decision` + `_validated_choice` + `_assert_no_conflicting_binding`, all re-run at confirm |
| 10. atomic decision + consequence | The decision write and the resume share one savepoint |
| 11. exact remote identity only | The decision key carries the verbatim `updatedAt`; a changed product supersedes it and raises a fresh one |
| 12. row locks and uniqueness | `SELECT … FOR UPDATE` before the state is read; `UNIQUE(store_id, decision_key)` |
| 13. resume the exact work once | `action_manual_retry` on the source job — never a fresh scan |
| 14. generic Resolve Review refuses | `action_resolve_manual_review` override, naming the route that does work |
| 15. actor, time, evidence, choice, binding, job state | `resolved_uid`, `resolved_at`, the evidence fields, `selected_*`, `resulting_*_binding_id`, `resumed_job_state` + live `job_state` |
| 16. real surfaces expose it | Match Decisions workspace + the control on the blocked job; **no binding field made generically editable** |
| 17. attribute conflicts unchanged | `product_import_attribute_conflict_mode` untouched |

### Three design choices worth reading twice

**The key is hashed and length-prefixed.** `decision_key_for` joins
`(level, product GID, variant GID, updatedAt)` with each component's length in
front of it, then hashes. Without the length prefix, `('ab', 'c')` and
`('a', 'bc')` would collide — a test asserts they do not.

**The record-rule escape hatch is load-bearing, not defensive noise.** A domain
leaf across a Many2one compiles to `field IN (SELECT …)`, and a NULL `field`
matches no `IN` subquery. The selection rule's `('selected_template_id', '=',
False)` leaf is what stops it hiding every decision that has not been decided
yet — which is every decision a reviewer needs to see. This was found by the
rule hiding exactly those rows, not by inspection.

**SEC-3 is joined rather than resembled.** The decision points at a job and at
the bindings it produces, and one company may own several stores, so it
inherits `shopify.connector.scope.mixin`, declares all three relations, and is
registered in the SEC-3 ownership matrix. The matrix's own completeness test
(`test_no_durable_store_scoped_model_escapes_this_matrix`) is what caught the
omission — a red suite rather than a quiet gap.

### ACLs

Read-only for **every** connector role — Auditor, Operator, Reviewer,
Administrator. Nothing may create, write or unlink a decision over RPC. Every
production write goes through the dispatcher seam or the revalidated confirm
path, both under `sudo()`. Asserted per role rather than assumed.

## 4. §8.3 — the tests, and what makes them load-bearing

**42 new decision tests**, plus the checkpoint-3 producer tests that already
covered §8.3's enumeration half (routes, pagination, checkpointing, gates,
fail-closed page validation, coalescing). Every end-to-end test drives the real
drain loop with the transport patched at `_send`, and asserts **that work was
admitted** — the transport ran and the job moved — before asserting what the
database holds. A test that only asserts "no binding was created" passes
brilliantly against a run in which the importer was never invoked.

### Proved against their own absence

Each central control was removed or neutered and the test that claims it was
required to fail:

| Mutation | Caught by | Result |
| --- | --- | --- |
| M1 — the `_route_failure` override removed | `test_an_ambiguous_template_persists_a_durable_decision` | **CAUGHT** |
| M2 — the remote-identity check neutered in `_confirmed_for` | `test_the_importer_consumes_only_the_matching_remote_identity` | **CAUGHT** |
| M3 — eligibility recomputation removed at confirm | `test_an_ineligible_candidate_refuses` | **CAUGHT** |
| M4 — the company filter removed from `eligible_candidates` | `test_candidates_never_include_a_foreign_company_record` | **CAUGHT** |
| M5 — the generic-resolve refusal removed | `test_generic_resolve_review_refuses_while_a_decision_is_pending` | **CAUGHT** |
| M6 — the candidate-membership check removed at consumption | `test_a_decision_selecting_a_candidate_that_vanished_is_not_consumed` | **CAUGHT** |
| M7 — the row lock and pending revalidation removed at confirm | `test_a_second_confirmation_of_the_same_decision_refuses` | **CAUGHT** |
| M8 — stale-sibling supersession removed | `test_the_importer_consumes_only_the_matching_remote_identity` | **CAUGHT** |

**8 of 8 caught, 0 missed.** Each mutation was applied to the production file,
the named test run against it, and the file restored byte-for-byte — the
worktree is clean afterwards, so none of this is in the diff. M4 is the one
worth reading twice: the company filter in `eligible_candidates` looks
redundant beside Odoo's own product record rules, and it is not — the test runs
as an administrator with *both* companies active, so the record rule lets the
foreign product through and the connector's own filter is the only thing left.

### Two fixture defects found by writing them

**A variant-ambiguity test that was exercising template matching.**
`_resolve_variant_product` reaches `_match_variant_candidate` only when the
template was resolved by *candidate match*: an `existing_binding` template with
attribute lines is routed to `_instantiate_refresh_variant` and never performs
variant candidate search at all. The first fixture built the obvious shape — a
bound template with two same-SKU variants — and produced no variant ambiguity
whatsoever, so the test failed rather than passing vacuously. The corrected
fixture makes exactly one template carry the SKU (unambiguous template match)
and gives that template two variants that both carry it.

**A shared payload dict that one job's parse corrupted for the next.** A real
transport returns a freshly parsed body every time; the importer normalises in
place. Handing every call the same dict produced a bogus
`data_shape_schema_mismatch` several tests downstream. Every fixture body is
now deep-copied per call.

**A multi-company test that was measuring its own fixture.** A product with no
company is correctly shared by every company, so a "foreign candidate" test
built on company-less products proves nothing. Both sides now carry explicit
companies.

## 5. §9 — the consolidated vertical journeys

Each journey starts from a store an operator has just configured and ends at a
database consequence a merchant could see, with every step performed by the
code the UI invokes. Where a step must fail, it is made to fail **by real
data**, never by an injected exception.

**Journey C — product import.** Configure through Store Settings → press
`Import products now` → scan job → two children → dispatcher → importer. One
product completes unambiguously and binds on `sku_reference`; the other stops
with a durable decision. The scan's checkpoint advances (the *enumeration*
finished; the blocked child is separate work with its own state, which is the
honest reading and the one the store form shows). The decision is opened from
the job, the eligible set is the two candidates and nothing else, the choice is
confirmed, the exact job resumes — **no second scan** — and the final binding
carries `match_key = manual` and the reviewer's uid. The cron route is proved
to reach the same place.

**Journey D-P0 — orders and tax.** Configure sale prerequisites and scheduling
through Store Settings → press `Import orders now` → scan → enqueue →
dispatcher → importer meets a `TaxLine` with no mapping. The job stops at
`failed_retryable` / `odoo_validation_configuration` — the state the dispatcher
really produces for that class — and **no order is created from a payload the
connector could not price**. It is mapped through an explicit same-company
choice, the exact order job resumes without a fresh scan, the order is created,
and the mapped tax is on its line. A second, different fingerprint stops again
rather than being absorbed by the first mapping.

**Journey I — administrator settings.** Reopened through the Configuration
menu's own action, not by URL. A readiness-irrelevant change does not
invalidate readiness; a domain change does; a no-op write does not; unrelated
domain settings survive both. The refusals are stated **precisely**: the one
that genuinely exists on this surface is the ACL, and the two read-only fields
are asserted as what they really are — `readonly` on the model, rendered
readonly or not rendered at all. `readonly=True` on an Odoo field is a UI
contract, not a server refusal, and claiming otherwise would have been a claim
this surface does not support.

**Journey J-P0 — multi-store/company.** Two companies, the same SKU on both
sides, one decision each. Each candidate set is its own company's and nothing
else; each administrator's `search`, `search_count` and direct `read` return
their own and only their own; an action aimed at the other company's job is
refused. Separately, two stores **in the same company** are shown not to share
decisions, so the isolation is proved to be store-scoping rather than a company
check doing the work.

**Journey K-P0 — failure/recovery.** The generic resolution refuses and names
the route that works; a blunt manual retry is permitted and provably cannot
loop (the same block, the same single decision row); stale, ineligible,
concurrent and competing decisions each refuse; a failed enumeration leaves the
checkpoint exactly where it was and admits no children.

## 6. §10 — the browser, responsive and accessibility campaign

### Tours

Seven tour tests over the six Batch 2 surfaces, registered in the runner's
fail-closed inventory (`REQUIRED_TOUR_TESTS`), whose guard test asserts that
inventory equals the set of test methods that actually call `start_tour` — so
adding a tour without listing it, or dropping one, fails a test rather than
silently shrinking browser coverage.

| Surface | Tour test | Database consequence verified in Python |
| --- | --- | --- |
| Canonical Store Settings | `TestUiB2SettingsTours.test_store_settings_tour_changes_a_setting_through_the_menu_route` | the setting is saved **and** the readiness marker moved |
| Product controls | `TestUiB2ProductTours.test_product_controls_tour_starts_a_real_scan` | exactly one `product_import_scan`, `manual_sync`, `queued` |
| Product controls, denied role | `…test_product_controls_are_absent_for_a_role_the_server_refuses` | no scan enqueued at all |
| Pending match decision | `…test_match_decision_tour_records_the_choice_and_resumes` | decision `confirmed`, actor recorded, choice was a real candidate, exact job re-queued |
| Match decision, denied role | `…test_match_decision_control_is_absent_for_an_operator` | decision still `pending`, job still blocked |
| Resolved binding | `…test_resolved_binding_tour_shows_a_human_made_match` | binding still points where the human said |
| Order controls | `TestUiB2SaleTours.test_order_controls_tour_starts_a_real_scan` | exactly one `order_import_scan` |
| Tax decision | `…test_tax_decision_tour_creates_the_mapping_and_resumes` | mapping carries the **importer's** fingerprint; exact job resumed; no fresh scan |

The fixtures are produced by production code: the pending decision comes from
the real importer meeting two same-SKU products and the real dispatcher routing
the failure; the tax block comes from the real `_resolve_taxes` raising its own
structured evidence.

**Selector discipline.** Every value assertion is anchored to the field that
owns it (`div[name='candidate_total']:contains('2')`), because a bare
`:contains('2')` is satisfied by any 2 on screen. Absence is asserted against
real attribute selectors, never `:contains()` inside `:not(:has())` —
`:contains()` is a hoot-dom extension and is not valid CSS.

**Keyboard.** Every actionable control is focused, proved to become
`document.activeElement`, proved to be in the tab order (`tabIndex >= 0`), and
activated by a dispatched `Enter` rather than a bare click. The focus
*indicator* is deliberately not asserted in the tours — in headless Chromium a
script-focused element never matches `:focus-visible` — and is measured instead
in the CDP campaign through `CSS.forcePseudoState`.

### Responsive, RTL, zoom, reduced motion

Six Batch 2 surfaces join the existing changed-surface campaign rather than
forming a second one: `CHANGED_SURFACES = BATCH1 + BATCH2`, and every matrix
that iterated Batch 1 now iterates both — **16 surfaces**, measured, with
`0 failed, 0 error(s) of 14 tests` in the visual/accessibility suite.

| Batch 2 surface | What it is |
| --- | --- |
| `b2-store-settings-canonical` | the canonical Store Settings form |
| `b2-store-form-controls` | the order **and** product controls, with the scheduled-position copy beside each |
| `b2-tax-decision-dialog` | the tax decision dialog, opened by pressing the control |
| `b2-product-match-decision-pending` | a pending decision with its evidence and candidates |
| `b2-product-match-decision-dialog` | the match decision dialog, opened by pressing the control |
| `b2-product-match-decision-resolved` | a resolved decision: actor, choice, resumed job state |

The **Match Decisions list** is captured and measured for responsive layout,
RTL, reduced motion and contrast, and is deliberately **not** in the two
matrices above: they measure a connector-owned surface region and its final
actionable control, and a bare Odoo list view has neither — the instrument
reports `no connector surface on screen` for it, exactly as it does for every
other list in the capture set. It is excluded because those matrices do not
apply to it, not because it failed them, and it is recorded that way rather
than quietly dropped.

Per changed surface the campaign covers:

* desktop / tablet / mobile, with the mobile row measured at **320 CSS px** —
  SC 1.4.10's reflow width;
* LTR and RTL, with an RTL row required to *show* it rendered right-to-left;
* real 200% zoom (the CSS viewport narrows **and** the type grows), and 200%
  zoom under `prefers-reduced-motion: reduce`;
* keyboard-only traversal to the final actionable control, driven by real
  `Input.dispatchKeyEvent` Tab presses;
* connector-owned clipping and horizontal overflow, per surface and for the
  page;
* measured contrast against WCAG 2.2 AA;
* live-region versus static-note semantics.

**One store, and that is measured rather than assumed.** The first version of
this seed created a *second* store so the order controls and the product
controls could be photographed separately. It broke four guided-setup captures
with `no offline path on the credential chooser`: the setup surface is opened
by action with no id and auto-selects a store only while there is exactly one,
so a second store replaced the credential step with a picker. Both control
groups live on the same form anyway, so one capture measures both — and the
regression is recorded here because a seed that quietly disturbs another
batch's evidence is exactly the kind of thing a campaign should not discover
after the fact.

**No production CSS changed.** No connector-owned visual defect was reproduced
on any new Batch 2 surface, so none was "fixed".

### Proved against their own absence, in the browser too

The server-side mutation table above proves the model's controls. These three
prove the *rendered* ones, by mutating the view and requiring the tour that
claims each to fail:

| Mutation | Caught by | Result |
| --- | --- | --- |
| B1 — the role gate removed from the decision control | `test_match_decision_control_is_absent_for_an_operator` | **CAUGHT** |
| B2 — the role gate removed from the catalog-import control | `test_product_controls_are_absent_for_a_role_the_server_refuses` | **CAUGHT** |
| B3 — `role="note"` removed from the dialog's consequence copy | `test_match_decision_tour_records_the_choice_and_resumes` | **CAUGHT** |

**3 of 3 caught, 0 missed**, and the view files are restored byte-for-byte.

## 7. Security and company boundaries

1. **UI visibility is never the control.** Every production action reasserts
   its role on the server: `_assert_product_sync_operator`,
   `_assert_match_decision_reviewer`, `_assert_tax_decision_administrator`,
   `_assert_canonical_settings_administrator`. Each is proved by a denied
   caller with zero side effects.
2. **Store/company scope is established before elevation.** The canonical
   settings seam resolves stores in the caller's ordinary environment and
   **refuses** — never filters — anything outside the caller's active
   companies; only then does it elevate, and only to ensure rows for that fixed
   set.
3. **Elevation is minimal and never used to discover targets.**
   `eligible_candidates()` elevates one exclusion query, which can only remove
   candidates.
4. **No foreign-company record, candidate, count or identity is disclosed.**
   Proved for `search`, `search_count` and direct `read`, per role.
5. **Existing constraints stay load-bearing.** Nothing was weakened to make a
   form save or a decision apply; the binding uniqueness constraints remain the
   final arbiter and the confirm path handles their `IntegrityError` as a
   sentence rather than a traceback.
6. **No protected payload, credential, token, secret or unnecessary PII**
   reaches RPC, DOM, evidence, logs or exception text. Asserted against the
   rendered decision record and against `safe_match_preview` directly.
7. **No generic context flag bypasses protected binding fields.** The decision
   route creates bindings through the importer's existing sanctioned writers
   and adds no editable binding field anywhere.
8. **The new durable model has explicit least-privilege ACLs** (read-only for
   every role) **and two company rules**, one fail-closed on the owning store
   and one on the selection relations.
9. **Stale and concurrent decisions fail closed** at both the confirm boundary
   and the consumption boundary.

## 8. Migrations

**None.** §8.2 adds a new model and new columns, which `_auto_init` creates;
there is no data to move, no existing row to reinterpret, and no behaviour that
changes for a database that already has data. No empty migration script was
created to satisfy a counter, and the genuine-upgrade runner was not weakened.

Module versions moved by coherent patch bumps: `core 19.0.1.18.0 →
19.0.1.19.0` (the tour asset) and `product 19.0.2.6.0 → 19.0.2.7.0` (the
decision model, wizard, views, ACLs and company rules).

## 9. Definitive validation

Run at `153be2baa6b77801f508680bc8da12646a10244f` with
`tools/run_connector_suite.sh` and no arguments. The runner verified the
checkout against the declared source head, verified the Odoo pin, and proved
the browser and `websocket-client` before executing anything — so no browser
test could skip its way to a green result.

| Pass | Result | Tours | Migration scripts |
| --- | --- | --- | --- |
| Fresh install + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | — |
| Warm `-u` (SAME-VERSION) + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **0, asserted** |
| Genuine migration `50b770a3` → candidate + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **2** (`19.0.1.16.0`, `19.0.1.17.0`) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2373 tests** | — | **0, asserted** |
| Genuine migration `0a15b176` → candidate + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **1** (`19.0.1.17.0`) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2373 tests** | — | **0, asserted** |
| Complete non-standard tag suite | **0 failed, 0 error(s) of 59 tests** | — | — |

All three HOOT suites verified (`shopify connector dashboard`, `export diff`,
`setup wizard`). The single sanctioned skip per standard pass remains
`TestMutationRecovery.test_real_process_death_harness`, unchanged.

**Both migration passes were genuine version-to-version upgrades.** The
`50b770a3` tree installed at `core 19.0.1.15.0 / product 19.0.2.4.0 /
sale 19.0.2.4.0 / inventory 19.0.1.4.0` and the `0a15b176` tree at
`core 19.0.1.16.0 / inventory 19.0.1.5.0`; both were upgraded onto the
candidate's `core 19.0.1.19.0 / product 19.0.2.7.0 / sale 19.0.2.6.0 /
inventory 19.0.1.6.0`. Odoo runs an upgrade script only when the installed
version is strictly lower, so those are real upgrades rather than
same-version re-updates — and the runner fails a migration pass that ran no
script.

### Deltas against the Batch 2 baseline

Measured in this same environment against `b0dbba2` (2229 standard / 59
non-standard / 28 tours):

| | Baseline `b0dbba2` | Final `153be2b` | Delta |
| --- | --- | --- | --- |
| Standard suite | 2229 | **2373** | **+144** |
| Tours | 28 | **36** | **+8** |
| Non-standard suite | 59 | 59 | 0 |

### Recorded facts from `summary.json`

`connector_worktree_dirty: false`; `source_head_verified: true`;
`odoo_pin_verified: true` at `30bde9ff758834a4912c5ae55843d3a7dad849f1`;
`browser_evidence: verified`; `required_tour_tests: 36`;
`shopify_operations: none`.

Environment: Python 3.12.3, PostgreSQL 16.13, Chromium 141.0.7390.37,
`websocket-client` 1.9.0.

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

### The defect this validation found, and why it matters

The first definitive attempt, at `68410fb`, **failed its `50b770a3` migration
pass**: `test_tax_decision_tour_creates_the_mapping_and_resumes` asserted
`0 != 1` — no tax mapping existed. Fresh and warm had both been green.

The tour had reported **success**, and had run in three seconds.

Two weaknesses, and the second is why the first was invisible. The Many2one was
chosen by clicking "the first autocomplete suggestion", and
`.o-autocomplete--dropdown-menu li` resolves in document order across the whole
page — so which row is first depends on what the database happens to hold. On a
fresh database it was the tax the fixture created; on a migrated one it was
not, and the confirm was refused for an empty required field. And the tour could
not tell: its closing assertion was `.o_form_view .o_field_widget[name=
'account_tax_id']`, but a refused confirm leaves the **dialog** open and the
dialog contains an `account_tax_id` field too. The step meant to prove the
mapping exists was satisfied by the exact failure it was meant to rule out.

Corrected at `153be2b`: both decision routes type the record's name, click the
row containing that name, and assert the field holds it; both then assert **the
dialog is gone** before asserting anything about the result; the tax route's
final assertion moved to `shopify_tax_evidence_key`, a field the mapping form
has and the dialog does not; and the product route pins the exact candidate by
name rather than accepting either of the two.

Only the Python assertion after the tour caught this. That is the argument for
verifying the database consequence after every tour rather than trusting a green
marker — and it is the second time in this campaign that browser evidence failed
honest-looking, after 8 of 9 tour tests silently **skipped** on an unresolvable
Chromium while reporting `0 failed, 0 error(s)`.

## 10. Deferred, explicitly

**Deferred beyond Batch 2, per §17 and unchanged:** standalone customer import
and refresh; ambiguous-customer matching decisions; bulk `Prepare changed
products`; feature-derived scope narrowing; per-domain operating-mode
declarations; per-store/per-domain dashboard liveness; the consolidated
attention/recovery centre; Fulfillment Settings residuals; reconnect
discoverability; journey families F, G and H; governed tax remap (recorded as
P1 debt when checkpoint 2 declined to offer the unsafe version).

**Not added, by instruction:** a standalone customer import, an ambiguous
customer UI, a tax-remap state machine, webhooks, any Shopify mutation, a
second setup wizard, a second queue or dispatcher, direct UI-to-importer
execution, and generic global optimistic locking.

TD-004, TD-005 and TD-007 are retained byte-for-byte.

## 11. Gates that remain

Independent Claude review of the exact final head (the implementing session
does not review, accept, ready-mark or merge); exact-head Odoo.sh
qualification; controlled live-Shopify validation; business UAT; control-room
acceptance and merge authorization. PR #204 stays draft.

---

> **RETAINED, AND STILL ACCURATE FOR WHAT IT DESCRIBES.** Everything below this
> line is the record written at `9af8b23` for checkpoints 1, 2 and §8.1. Two of
> its statements are corrected above and are named here so no reader takes them
> from the archive by accident:
> 1. *"Nothing has been pushed … the four commits below are local only"* — true
>    at `9af8b23`, superseded by the durability ruling. The chain is pushed.
> 2. *"§8.2 … not implemented"*, and the §5c list of what is not done — all of
>    it is implemented above.
> Its checkpoint-1/2/§8.1 content, its field classification and its own
> mutation table are unchanged and remain the description of those commits.

---

# (retained) Batch 2 record as written at `9af8b23`

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

> **Scope of this record, and its limits.** The unified Batch 2 campaign
> specified three checkpoints plus consolidated journeys, a browser campaign
> and one definitive validation. This record covers what is **implemented and
> focus-validated locally**: checkpoint 1 (canonical Store Settings),
> checkpoint 2 (order controls and the tax decision route), and **§8.1 of
> checkpoint 3** (the product enumeration producer).
>
> **NOT implemented, and not claimed:** §8.2 durable product/variant match
> decisions; §9 consolidated vertical journeys; §10 the consolidated
> browser/accessibility campaign; §15.2 the definitive seven-pass validation
> at a final head. Nothing has been pushed. The branch `fable/wave-5-completion`
> remains at `b0dbba2a` and PR #204 remains draft, unreviewed and unmerged.
>
> Per §5 and §15.2 the additive chain is not pushable until the consolidated
> validation is green, so the four commits below are **local only**.

## 1. Heads

- Starting head (identity-gate verified): `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e`
- Local additive chain (unpushed):
  - `9a70682` checkpoint 1 — canonical Store Settings
  - `f5f3668` checkpoint 1 — the four guards the new surface had to answer to
  - `39e5113` checkpoint 2 — order controls and tax decisions
  - `2c5d190` checkpoint 3 §8.1 — product enumeration producer
- Base: `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, confirmed ancestor)
- Odoo pin: `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run
- History: **additive only** — no amend, rebase, squash, reset or force-push

### Identity gate

All ten items passed before any edit. Repository `AdamsOdoo/Adams`; PR #204
open, draft, unmerged, **zero reviews**; head branch `fable/wave-5-completion`;
PR head, remote branch head and local HEAD all exactly the required starting
head; base unchanged and an ancestor; clean worktree; `tools/odoo-pin.txt`
carrying the required pin; no later unreviewed commit.

One item needed care rather than acceptance at face value. `git merge-base
--is-ancestor` initially reported the base was **not** an ancestor. That was
the clone, not the branch: the working copy was shallow at 50 commits, so the
base commit was simply absent from the object store. After `git fetch
--deepen=200` the ancestry resolves. A shallow clone answering an ancestry
question with silence that reads as "no" is worth recording, because the
honest-looking action there is to stop on a false negative.

## 2. What checkpoint 1 closes

The first of the three §2 defects: **the promised per-store settings surface
did not exist**, and important core, product-import, sale and inventory
settings were not merchant-reachable after onboarding.

`Shopify Connector → Configuration → Store Settings` is that surface. It is
not a second setup wizard — it collects no consent, runs no readiness check,
drives no lifecycle transition and creates no store — and it does not compete
with the two dedicated surfaces that already own their own subjects.

The sharpest single instance: **`order_scheduled_sync_enabled` had no
production writer anywhere in the repository.** The cron
(`_cron_enqueue_order_scans`) and the enqueue producer (`_enqueue_order_scan`)
both already existed and both already selected on that field. The only thing
missing was a control a merchant could reach. That is now on the canonical
form, writing through the ordinary model path.

§7's order controls and tax decision route are §5 below; §8.1's product scan
producer is §5b. §8.2's durable match decisions are **not implemented**.

## 3. Field ownership and classification

Every module contributing a field to `shopify.connector.store.settings`
classifies **all** of them, as §6.6 requires, into exactly one of: canonical
editable, canonical read-only, owned by a named existing dedicated surface, or
internal/protected with a named justification.

**There is no expected field count anywhere in the tests.** A count is
satisfied by any set of the right size — it passes when one field is added and
another removed, and says nothing about the field that was added. The
assertion is set equality against the live registry (`Field._modules`), so
adding a field to the model in any module fails that module's test until it is
classified by name.

### Core (`shopify_connector_core`)

| Field | Classification |
| --- | --- |
| `product_domain_enabled` | canonical editable |
| `sale_domain_enabled` | canonical editable |
| `inventory_domain_enabled` | canonical editable |
| `fulfillment_domain_enabled` | canonical editable |
| `log_redaction_retention_days` | canonical editable |
| `store_id` | canonical read-only |
| `company_id` | canonical read-only |
| `product_first_sync_source` | canonical read-only |
| `notification_default_enabled` | canonical read-only |
| `price_source_of_truth` | owned by **Export Settings** |
| `setup_wizard_step_key`, `setup_wizard_step`, `setup_readiness_stale_since`, `setup_completed_at`, `setup_completed_uid`, `setup_last_rerun_at`, `setup_last_rerun_uid` | internal/protected — setup progress and the readiness marker, written only by the setup service |

`notification_default_enabled` is read-only and says on screen why: opting in
means Shopify emails customers on fulfilment, and that consent stays on the
guided Setup Wizard's notification step, which refuses to enable without an
explicit confirmation (`save_notification`). No second consent path was added.

`product_first_sync_source` is read-only; a post-onboarding direction switch
was not authorized here.

### Product (`shopify_connector_product`)

`product_import_media_enabled`, `product_import_refresh_mode`,
`product_import_attribute_conflict_mode` — all canonical editable.

Plus, **added by checkpoint 3 together with the producer that makes them
real**: `product_scheduled_sync_enabled` (canonical editable),
`product_last_import_checkpoint_at` and `product_last_import_success_at`
(canonical read-only).

**The ordering was deliberate.** Checkpoint 1 declined to render the schedule
switch while nothing in production enumerated a catalog — a control whose
producer does not exist is a control that silently does nothing, the same
false-capability failure §6.4 forbids. Its test asserted the field's absence.
Checkpoint 3 built the producer, so that test is now inverted: the schedule
must be the field the cron actually selects on.

### Sale (`shopify_connector_sale`)

Canonical editable: `order_scheduled_sync_enabled`, `order_confirmation_policy`,
`manual_gateway_policy`, `approved_manual_gateways`, `order_import_window`,
`pending_wait_expiry`, `order_import_include_test`,
`customer_fallback_partner_id`, `order_pricelist_id`, `order_sales_team_id`,
`order_payment_term_id`.
Canonical read-only: `order_company_id`, `sale_order_last_import_checkpoint_at`.

**`customer_fallback_partner_id` — the §6.4 proof.** §6.4 requires the fallback
setting to be proved consumed or else rendered unavailable. It **is** consumed:
`ShopifyConnectorOrderImporter._resolve_customer`
(`shopify_connector_order_importer.py:1164-1165`) returns it with resolution
`fallback` for an order carrying no usable customer email, and raises
`odoo_validation_configuration` when it is unset. It is therefore rendered as
the real setting it is.

The field's own docstring still described it as inert substrate — "zero
order-resolution behaviour", never read. That was true when Task 011
introduced it and stopped being true when Task 012 landed order import. The
docstring is corrected rather than trusted, because the canonical form decides
whether to present a field as supported on exactly that question, and a stale
comment is how it would have been presented wrongly. **This is the one Batch 1
file changed beyond the checkpoint's own additions, and it is named here so the
control room can reverse the reading.** A test asserts the production call site
exists, so the day it is removed the form stops claiming the capability.

### Inventory (`shopify_connector_inventory`)

`inventory_scheduled_sync_enabled` — canonical editable (the inventory
service's `run_inventory_push_scan` selects on it, so it genuinely starts and
stops scheduled scanning). `inventory_last_push_scan_at` — canonical
read-only; the service writes it, so typing into it would only make the report
wrong.

### Not duplicated

Export Settings keeps `price_source_of_truth`, `media_source_of_truth` and
`product_export_domain_enabled`. Fulfillment Settings keeps the operating mode,
`fulfillment_mode_switch_nonce`, the switching state and the notification
confirmation. Setup progress, completion/rerun stamps and
`setup_readiness_stale_since` are rendered nowhere.

## 4. Action, menu and the row-ensure seam

- Canonical list and form on `shopify.connector.store.settings`, both
  `create="false" delete="false"`, list not inline-editable.
- One `ir.actions.act_window` binding both views through `view_ids`. This is
  load-bearing rather than tidy: four surfaces now share this model, and an
  action with no view reference falls back to `default_view()`, which orders by
  `priority,name,id`. Every view sits at the default priority, so the tie
  breaks on **name** — precisely the accident that made "Export Settings"
  render the fulfillment list until it was corrected.
- `group_ids` is the Odoo 19 field on `ir.actions.act_window`, verified at the
  pinned commit (`odoo/addons/base/models/ir_actions.py:329`), not assumed.
- The Administrator-gated **Configuration** menu already existed
  (`menu_shopify_connector_configuration`); Store Settings hangs off it rather
  than creating a second branch.

### The seam, and why the order is the argument

`action_open_canonical_store_settings`:

1. reasserts the Connector Administrator role **on the server** — the menu gate
   and `group_ids` are chrome, and a direct RPC reaches the method regardless;
2. resolves stores in the **caller's ordinary environment**, where the
   fail-closed SEC-3 company rule (`[('company_id', 'in', company_ids)]`) is
   live;
3. re-checks `check_access('read')` and **refuses** if anything outside the
   caller's active companies got through;
4. only then elevates, and only to ensure rows for that fixed set.

`sudo()` does **not** keep record rules running — Odoo bypasses them under
elevation. So the property defended is not "the rules still apply"; it is that
the authorized set is fixed **before** elevation and can only shrink after.
`_ensure_canonical_settings_rows` takes a recordset and never searches for a
store, so discovery cannot happen under elevation by construction.

**A refusal, not a filter.** Step 3 raises rather than quietly dropping
records. The company rule already excluded them, so a silent `filtered()`
would be a no-op that passes every test while absorbing a widened resolution
without a sound. This was found by mutation, not by inspection: with a filter,
replacing the ordinary-environment search with a `sudo()` one broke **nothing**
— the isolation test passed either way, so it was not evidence. With the
refusal, the same mutation breaks four tests.

Row ensure is idempotent, and a concurrent opener is contained: `UNIQUE(store_id)`
is the arbiter, each create sits in its own savepoint, and losing the race is a
no-op because the winner's row is exactly the row the call wanted to exist.

## 5. Write and readiness behaviour

All saves go through the ordinary model write path, so every existing
constraint stays load-bearing — store/company agreement, order-company
agreement, import window and scope, pending expiry, pricelist/team/payment-term
company, fallback-customer company, and the unique-row guard. None was weakened
to make the form save.

The readiness-relevant-field hook is derived from
`shopify.connector.readiness.check._accepted_domain_flags()` — the same
registry the readiness checks are computed over — rather than a second tuple
beside it. The two would drift: Product Export **already** extends that
registry with `product_export_domain_enabled`, so a copied tuple would have
gone on reporting a store as freshly-checked after a merchant enabled catalog
export. It remains overridable, so a domain extends it for fields its own
checks consume.

- A meaningful change marks readiness stale through the existing
  `_mark_setup_readiness_stale()` service.
- A no-op write does not — the comparison is against the stored value, not the
  presence of a key in `vals`.
- An unrelated canonical-editable setting (`log_redaction_retention_days`) does
  not.
- The nested marker write terminates because `setup_readiness_stale_since` is
  not readiness-relevant. That is a property of the **field partition**, not a
  re-entrancy flag somebody has to keep correct — and breaking the partition
  breaks the test that claims it.

## 6. Security and company invariants (checkpoint 1 scope)

1. UI visibility is not authorization — the server role assertion is the control.
2. Store/company scope is established as the original caller, before elevation.
3. Elevation is minimal, record-scoped, and never used for target discovery.
4. No existing settings ACL or company rule was widened. Settings access is
   unchanged: Auditor/Operator/Reviewer read; Administrator read+write, no
   create, no unlink.
5. A company-less historic store — invisible under the fail-closed rule — is
   never adopted.
6. No new durable model, so no new ACL or company rule was required.
7. Zero Shopify contact and zero Shopify mutation: this checkpoint adds no
   transport code path at all.

## 7. Migrations

None. Checkpoint 1 is views, one server seam, and a `write()` override — no
schema change, so no migration script. No empty script was created to satisfy
a counter, and the genuine-upgrade runner was not weakened.

Module versions moved by coherent patch bumps for the four touched modules:
`core 19.0.1.17.0 → 19.0.1.18.0`, `product 19.0.2.4.0 → 19.0.2.5.0`,
`sale 19.0.2.4.0 → 19.0.2.5.0`, `inventory 19.0.1.5.0 → 19.0.1.6.0`.

## 8. Tests, and their load-bearing proof

31 new test methods: **20 core, 3 product, 4 sale, 4 inventory** — counted
from the test files themselves, not from `odoo.tests.stats`, whose per-module
figures include fixtures and do not sum to the selected total.

Each central claim was proved **against its own absence** by mutating the
production code and confirming the specific test that claims it fails:

| Mutation | Result |
| --- | --- |
| Server-side role assertion removed from the seam | `test_non_administrator_direct_call_is_refused` fails (1) |
| Readiness staleness call removed from `write()` | `test_a_meaningful_change_marks_readiness_stale` fails (1) |
| Every written field treated as readiness-relevant | no-op guard, unrelated-setting and **non-recursion** tests fail (3) |
| `readonly="1"` removed from a canonical read-only field | classification test fails (1) |
| `except IntegrityError` no longer catches the unique violation | concurrent-winner test errors (1) |
| Ordinary-environment store search replaced with `sudo()` | 4 tests error — **and 0 before the refusal replaced the filter** |

The last row is the one worth reading twice: it is the case where the first
version of the test proved nothing, and mutation is what said so.

## 9. Definitive validation

Recorded in `docs/05-qa/evidence/batch-2-p0-merchant-reachability-2026-07-30/`.

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

## 10. Deferred, explicitly

**Not started in this session:** checkpoint 2 in full (order manual/scheduled
controls, the tax blocked-work decision route and workspace, their tests) and
checkpoint 3 in full (product scan producer, cron, checkpointing, durable
product/variant match decisions, their tests). Also not started: the
consolidated vertical journeys (C, D-P0, I, J-P0, K-P0), the consolidated
browser/accessibility campaign, and their runner-inventory registration.

**Deferred beyond Batch 2, per §17:** standalone customer import/refresh;
ambiguous customer matching decisions; bulk `Prepare changed products`;
feature-derived scope narrowing; per-domain operating-mode declarations;
per-store/per-domain dashboard liveness; consolidated attention/recovery;
Fulfillment Settings residuals; reconnect discoverability; journey families F,
G and H; governed tax remap. TD-004, TD-005 and TD-007 are retained unchanged.

## 11. Gates that remain

Independent Claude review of this exact head (the implementing session does not
review, accept, ready-mark or merge); checkpoints 2 and 3; the consolidated
journeys and browser campaign; exact-head Odoo.sh qualification; controlled
live-Shopify validation; business UAT; control-room acceptance and merge
authorization. PR #204 stays draft.


## 5. Checkpoint 2 — order controls and tax decisions

**The controls.** `Import orders now` binds `action_sync_orders_now` on the
store form; `Refresh this order` binds `action_sync_selected` on the order
binding. Both methods pre-existed with their own server guards and neither had
a caller in any view. `groups="operator"` matches `_assert_order_sync_operator`
exactly — Administrator and User both imply Operator — and the server refuses a
denied caller regardless. The store form now states the scheduled position, the
discovery watermark and any scan in flight, so a manual button never stands
beside a silent screen that reads as "this is handled".

**The tax route.** The importer already canonicalised a Shopify `TaxLine` into
a version-stamped fingerprint, refused to guess, and raised structured evidence
with bounded candidates explicitly marked
`rate_and_inclusion_only_non_binding`. None of it was reachable: the evidence
sat in a job-log row and the only control was a generic retry that re-ran the
identical import and failed identically.

**The state is `failed_retryable`, not `blocked_manual_review`.**
`odoo_validation_configuration` is a `MANUAL_FIX_THEN_RETRY` class, so a guard
written against the phrase "blocked work" would never match what the dispatcher
produces. It also means the generic `action_resolve_manual_review` already
refuses these jobs (§7.2.13) — asserted rather than rebuilt.

Identity comes from the structured payload after exact-key schema validation,
never from the human sentence; a test rewords the message and asserts nothing
changes. The fingerprint is displayed, never typed. Candidates are recomputed
against the live database at open and again at confirm. Confirmation creates
the mapping with `UNIQUE(store_id, evidence_key)` as arbiter and resumes the
exact job via `action_manual_retry` — never a fresh scan.

**Tax Mapping workspace**: list/form/search, `create="false" delete="false"`,
and `account_tax_id` rendered **read-only** although the model permits writing
it. Changing what a Shopify tax means after it has priced imported orders needs
a preview and an audit; declining to offer the unsafe version is the honest
move. **Governed remap is recorded as P1 debt.**

**A defence that was not being tested.** Removing the candidate query's
`company_id` filter broke nothing — Odoo's own multi-company rule on
`account.tax` already hid the foreign tax from a single-company administrator.
The new test runs the query as an administrator with *both* companies active,
so the record rule lets the tax through and the filter is the only thing left.
That mutation now fails exactly one test.

21 tests. Whole sale module green at **251**.

## 5b. Checkpoint 3 §8.1 — the product enumeration producer

`product_import_sync` was registered, handled and replay-classified, and
nothing in production ever created one. Now: a registered `product_import_scan`
job type, `Import products now`, a module-owned hourly cron, per-store
checkpoint and success stamps, and children admitted through the existing
enqueue service. No second queue, dispatcher or transport.

**Verified against the configured version `2026-07`, not `latest`.**
`ProductSortKeys` carries `UPDATED_AT`; `ProductStatus` carries a fourth value,
`UNLISTED`, which the schema notes is "only visible from 2025-10 and up". A
scan written against the familiar three-value enum would meet it on this
version, so status is carried as an opaque string and a test enumerates all
four. Verification used schema introspection and official documentation only —
**zero Admin API contact, zero credential**.

- First run carries **no time lower bound** and no status clause: a
  recent-changes default silently omits every product nobody edited lately.
- Incremental runs reach one minute **behind** the checkpoint, because
  `updated_at` has second resolution and a same-second write would fall in the
  gap. Re-seeing products is free; the children collide on their idempotency
  key.
- The checkpoint advances once, after every page and child, inside the
  handler's savepoint. A scan failing on page two discards page one's children
  and leaves the checkpoint where it was.
- Child `payload_hash` is the **verbatim** remote `updatedAt`.
- Repeated cursors, non-progressing cursors, duplicate identities, malformed
  shapes and the page ceiling all fail closed and visibly.

25 tests. Whole product module green at **217**.

## 5c. What is NOT done

- **§8.2 durable product/variant match decisions** — not implemented. Ambiguous
  matching still routes to the importer's existing `blocked_manual_review`
  behaviour with no durable decision record, so generic requeue still repeats
  the same failure. This is the one §2 defect left open.
- **§9 consolidated vertical journeys** (C, D-P0, I, J-P0, K-P0) — not written.
- **§10 consolidated browser/accessibility campaign** — not run. No new tour is
  registered, so the runner's fail-closed tour inventory is unchanged.
- **§15.2 definitive seven-pass validation** — not run at a final head.
- **Nothing pushed.** Per §5/§15.2 the chain is not pushable until the
  consolidated validation is green.

An earlier seven-pass run was started after checkpoint 1 and terminated as
premature under §15.1 per the control-room ruling. Its passes 1 and 2 (fresh
and warm, 0 failed of 2260 tests, 28/28 tours) are **intermediate diagnostic
evidence only** and describe `f5f3668`, not any later head.
