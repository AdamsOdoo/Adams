# Wave 5 — bounded UAT-critical onboarding batch: validation results

> **Status: implementation evidence record. NOT an acceptance, NOT Odoo.sh
> runtime, NOT independently reviewed, NOT merged, NOT self-accepted.**
> Produced 2026-07-29 on `fable/wave-5-completion` (draft PR #204) under the
> control room's bounded post-reversion onboarding instruction of the same
> date.
>
> **No Shopify store, credential, request, mutation, campaign or UAT is
> involved anywhere in this record.** Every automated test that could reach
> the transport replaces it with a stand-in that FAILS the test if it is
> reached; the two tests that deliberately drive the dispatcher answer
> `execute` locally, so the real handler, the real response validation and the
> real cache upsert all run with only the socket absent.
>
> **Evidence class.** DEC-041 D8 supporting evidence. The exact-SHA Odoo.sh
> run remains the Tier-1 acceptance authority and has not been performed for
> this head.

---

## 1. Scope

The bounded onboarding scope only: the guided setup's step order and
addressing, a customer-operable location-mapping route, the final-readiness
presentation, the credential guidance, and the sticky responsive action row.

**Explicitly not in this batch, and not reintroduced by it:**
`addons/shopify_connector/**` (does not exist), a customer package
controller, reverse module dependencies, component-uninstall protection,
dependency-loss pause, dependency snapshots or restoration, automatic
technical-module installation, DEC-042, TD-017, TD-018 and TD-019. Every part
of the rejected single-package lifecycle architecture stays reverted, and
dependency-uninstall survival stays deferred from the MVP.

## 2. Environment

`[Fact]`

| Item | Value |
| --- | --- |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (19.0), verified on every suite run |
| PostgreSQL | 16.10 |
| Python | 3.11.15 |
| Browser | Chromium 141.0.7390.37 (headless, resolved and proven before any browser-bearing pass) |
| Modules | `shopify_connector_core`, `_product`, `_sale`, `_inventory`, `_fulfillment`, `_product_export`, plus `account` and `stock` |
| Shopify | **none** — no store, credential, request, mutation or webhook at any point |
| Runner | `tools/run_connector_suite.sh` (fresh install, warm `-u` update, non-standard tag pass) |

## 3. What the tests hold, by requirement group

### A — Step order, addressing and persistence

- The exact twelve semantic keys, in the exact accepted order, asserted
  against the literal list rather than a count.
- **The ordering invariant, not just the list:** every step whose value a
  readiness check reads (`directions`, `location_mapping`, `source_of_truth`,
  `notification`, `first_push`) is asserted to come *before*
  `final_readiness`, which is asserted to come before `review`. A future
  reorder that keeps the count fails here.
- The semantic key is what persistence records; the ordinal is derived from
  the key and asserted to equal its position.
- **Numeric navigation is refused, not translated.** `save_and_exit` is driven
  with `1, 5, 8, 11, 12, 0, -1, 99` and every one is refused, with the stored
  resume point asserted unchanged afterwards. A **static source guard**
  additionally forbids any comparison of the current step against a bare
  number anywhere in the client — over the code, with comments stripped,
  because the comments necessarily quote the shape they warn about.
- **Warm migration.** Every legacy position 1–11 is asserted to translate to a
  real step, monotonically; each translation is driven through
  `get_setup_state` on a row seeded exactly as a pre-Wave-5 database holds it
  (a number, no key); a legacy row is asserted to be upgraded in place on the
  next step completion **with every durable choice unchanged**; and a stale
  numeric write is asserted unable to rewind a semantically-recorded point.
- Back, Continue, Save & Exit, resume, Start again, connect-only activation,
  and "setup completion admits no job of any kind" all retained and asserted.
- The conditional location step: present in the list in both configurations,
  never renumbering anything, marked Not required with a reason when inventory
  is disabled, enqueueing nothing and fabricating no mapping on Continue.

### B — Credential guidance

Asserted against the **shipped template**, not a docstring: the Admin API
access token is named, the Client ID and the Client Secret are each named as
*not* the token, the "may be used outside Odoo to obtain an access token"
sentence is present, and no universal 24-hour expiry claim exists. The
write-only credential implementation is unchanged; the existing assertions
that the token never returns in a payload, never enters Owl state, and never
reaches a log or an error are retained and still pass.

### C — Location refresh

- The public guarded action admits a real `inventory_location_sync` job; a
  **spy on `_enqueue_location_sync` proves the delegation**, so a future
  implementation that built its own job row would fail rather than pass.
- A `setup_incomplete` store can refresh at all (the circular gate, closed);
  a `connected` store uses the business-gated `manual_sync`; and
  `reconnect_needed` / `disconnecting` / `disconnected` are **refused
  outright**, with the job count asserted unchanged, so the store-state
  exemption cannot become a way around the business gate.
- An unsanctioned `job_source` is refused.
- Duplicate admission is coalesced onto the same job id, with the total job
  count asserted; a new refresh is admitted once the previous one is terminal.
- Auditor, foreign-company administrator, inventory-disabled, and each of the
  three missing-credential-evidence conditions are refused **before**
  admission, each with the job count asserted unchanged.
- A foreign store id and a nonexistent one produce an identical refusal
  (class and message), so neither is an existence oracle.
- Waiting / Running / Succeeded / Failed are distinguishable, and "no refresh
  ever asked for" is its own state.
- **An empty cache while a refresh is pending is asserted not to be presented
  as zero Shopify locations**, and a failed refresh is asserted never to be
  presented as a success.
- The job reaches the production handler through the ordinary dispatcher
  registry, and the end-to-end test asserts a **database consequence** —
  cached rows that were not there before — not that a method was called.

### D — Mapping

Zero / one / many cached locations; inactive and foreign-store cache rows
never offered; every cached location carrying a visible mapped state; eligible
Odoo locations restricted to internal and company-compatible ones; creation
delegating to the sanctioned service (proven by spy); the name snapshot taken
from the validated cache row; exact repeats idempotent; arbitrary,
foreign-store and inactive GIDs refused; duplicate Shopify identity, duplicate
Odoo identity, non-internal, cross-company and nonexistent Odoo locations all
refused; a direct protected-field create still refused; and a
**deliberately name-identical Odoo and Shopify location pair asserted to
produce no mapping at all**, which is where any surviving name inference
would show.

### E — Remap

Administrator required (Reviewer and Operator both refused, with the mapping
asserted unchanged); the generic mixin's own Reviewer-or-Administrator
admission asserted **unchanged**; explicit confirmation required; a non-empty
reason required; the audited reason sanitized (a merchant email in the reason
is asserted absent from connector history and replaced by the redaction
marker); the exact safe change moving only the Odoo target with the same row
id, the same Shopify GID and no unlink/recreate; same-target, non-internal,
nonexistent, foreign-company and inactive-cache refusals; non-terminal
inventory work refused and a terminal job asserted **not** to block; a
`pending` pair asserted not to block; `previewed` and `confirmed` first-push
state asserted to block.

### F — Readiness presentation

All five states rendered as text; a not-applicable check asserted **Not
required and not `success`**; `Sync features selected` as the label; the
connect-only warning asserted **verbatim**; a readiness-relevant change
asserted to make every earlier row Waiting and `can_activate` false; a re-run
asserted to clear it; entering the step asserted to change a
previously-not-required `mapped_location` into a non-success state once
inventory is enabled; the fix action asserted to carry the semantic step key;
and activation asserted refused, naming the blocking check, with the store
asserted not `connected` afterwards.

A **static AST guard** across every connector module asserts that any
`_check_result` whose reason begins "Not applicable" declares
`not_applicable=True`, so the presentation rule can depend on a key rather
than on translatable prose and cannot drift silently.

### G — UI

**Two defects this batch's own evidence found, both fixed here.**

1. **The setup surface's content was clipped and unreachable.** A client
   action renders inside `.o_action_manager`, which is `overflow: hidden` at
   the pinned Odoo and scrolls nothing of its own — scrolling is a view's job,
   and a bare client action is not a view. With `min-height: 100%` on
   `.o_sc_setup` the instrument measured **328–1774 px** of setup content
   overflowing that ancestor, with `doc_extent: 0` and no scrollable element
   anywhere in the ancestor chain, at all four required widths. The bottom of
   every long step was clipped away with no scrollbar for anyone to notice.
   The surface now owns its own scrolling (`block-size: 100%; overflow-y:
   auto`), which also gives `position: sticky` a real scrollport instead of
   the viewport. `unreachable_vertical_content` is now a measured, asserted
   defect class for **every** connector surface, and is zero everywhere.
2. **The sticky bar's negative inline margin was a real connector-owned
   horizontal overflow** — 16 px past `.o_sc_setup__inner` on each side,
   `scroll_width 896` against `client_width 880` at every width in both
   directions. Removed.

**And three corrections to the instrument itself,** each because the first
version could have produced a green result that meant nothing: it now reports
the whole ancestor chain so "nothing scrolled" is distinguishable from "the
scroll was attempted and the page was already in the middle"; it measures the
bar against the **scrollport's pin target** rather than `innerHeight`, which
reported the surface's own 32 px padding as a defect and would have had a
correct sticky bar "fixed" into a wrong one; and the focus-clearance test
records the cases it skips and asserts a floor on the number actually
measured.

Six browser tours (twelve-step traversal with the sticky bar asserted inside
the viewport on the longest step; dashboard entry; resume from **legacy
numeric progress**; keyboard traversal with focus management and per-control
scroll clearance; the location step with three cached locations, one already
mapped, creating a second through the governed route and asserting the
resulting database row and its cache-derived snapshot; and a blocking
readiness row whose fix control deep-links by `data-step-key`), seventeen HOOT
unit tests, and rendered CDP evidence.

## 3a. Requirement-to-proof matrix

`[Fact]` One row per required behaviour. "Negative test" means a test that
asserts the refusal AND that nothing happened.

| Requirement | Production entry point | Implementation | Positive test | Negative test | Browser / runtime evidence | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Exact 12 semantic steps, in order | `get_setup_state` | `SETUP_STEPS` | `test_the_step_order_is_the_accepted_one`, `test_the_state_payload_names_every_step_in_order` | `test_readiness_runs_after_every_choice_it_reads` (ordering invariant) | `shopify_connector_s1_setup_tour` asserts "Step N of 12" + name at all 12 stops | — |
| Key is authoritative for persistence | `_record_progress` | `setup_wizard_step_key` | `test_the_semantic_key_is_what_persistence_records` | `test_the_resume_point_is_never_rewound_by_a_legacy_translation` | — | — |
| Key authoritative for navigation; no numeric coupling | `save_and_exit`, Owl `goToStep` | semantic switch, `_code_only` guard | `test_progress_is_durable_and_resumes_where_it_stopped` | `test_a_numeric_step_is_refused_rather_than_translated`, `test_the_client_never_navigates_by_a_numeric_step_position` | HOOT `navigation follows the key, not the ordinal` | — |
| Warm migration of numeric progress | `19.0.1.15.0/post-migrate.py` + `_resume_key` | deterministic table | `test_existing_numeric_progress_resumes_without_being_reset`, `test_every_legacy_position_translates_to_a_real_step` | `test_a_legacy_row_is_upgraded_in_place_and_loses_no_choice` (asserts choices intact) | `shopify_connector_s1_resume_tour` resumes a legacy-seeded store | A legacy store past `directions` skips `location_mapping`; `mapped_location` then blocks with a deep link |
| Conditional step explained, never hidden | `_step_applicability` | `applicable` + `skipped_reason` | `test_inventory_disabled_marks_the_step_not_required_and_explains` | `test_the_step_is_never_removed_from_the_list`, `test_inventory_disabled_enqueues_no_location_refresh`, `test_continuing_past_the_step_fabricates_no_mapping` | tour asserts `Not required` on the step | — |
| Readiness runs after the choices it reads | `run_readiness` at `final_readiness` | order + `_onEnterStep` | `test_entering_final_readiness_evaluates_what_is_currently_saved` | — | tour asserts results present on arrival | — |
| Readiness-relevant change marks evidence stale | `save_directions`, `save_location_mapping`, `remap_location_mapping` | `setup_readiness_stale_since` | `test_re_running_the_checks_clears_the_staleness` | `test_a_readiness_relevant_change_makes_earlier_evidence_stale` (asserts no `success` tone, `can_activate` false) | HOOT `stale readiness evidence is never shown as a success` | — |
| Activation re-runs readiness server-side | `activate` | `run_for_store` + refusal | `test_activation_starts_no_sync_and_writes_nothing_to_shopify` | `test_activation_is_refused_while_readiness_is_waiting`, `test_activation_is_refused_while_an_essential_check_fails` | tour reaches the dashboard | — |
| Connect-only activation valid | `activate` | WARNING tier | `test_a_genuine_connect_only_store_can_activate` | `test_the_domain_flag_check_is_non_blocking_not_essential` | — | — |
| Credential guidance (3 values, no 24h claim) | setup template | step copy | `test_the_credential_step_names_the_two_values_that_are_not_a_token` | asserts `24 hours` / `24-hour` absent | tour asserts "not the Client ID" and "Client Secret" | — |
| Governed refresh, one public route | `action_refresh_shopify_locations` | `_enqueue_location_sync` | `test_the_public_action_admits_a_governed_job`, `test_the_action_delegates_to_the_sanctioned_admission_service` | `test_an_unsanctioned_job_source_is_refused` | `test_the_setup_refresh_reaches_the_public_guarded_action` | — |
| Pre-activation refresh without weakening the gate | same | state-derived `job_source` | `test_a_pre_activation_store_can_refresh_at_all`, `test_a_connected_store_uses_the_business_gated_source` | `test_a_disconnecting_store_is_refused_rather_than_routed_around` (job count asserted) | — | — |
| No transport shortcut anywhere | — | — | — | `test_no_wizard_view_or_setup_surface_calls_the_api_client`, `test_the_owl_client_holds_no_shopify_request` | fail-on-contact stand-in in every admission test | — |
| Dispatcher route reaches the handler | `run_drain` registry | `_get_handlers` | `test_the_ordinary_dispatcher_routes_the_admitted_job`, `test_the_admitted_job_populates_the_cache_through_the_handler` (DB consequence) | `test_the_location_sync_job_type_is_domain_gated_at_start` | — | — |
| Duplicate refresh coalesced | `action_refresh_shopify_locations` | non-terminal lookup | `test_a_new_refresh_is_admitted_once_the_previous_one_finished` | `test_duplicate_refresh_is_coalesced_not_queued_twice` | wizard dialog states it before the click | — |
| Four async states distinguishable | `location_refresh_state` | job-state mapping | `test_the_four_states_are_distinguishable` | `test_no_refresh_ever_asked_for_is_its_own_state` | HOOT pending-refresh disclosure | — |
| Empty cache never reported as zero locations | readiness projection | `_readiness_state` waiting | — | `test_an_empty_cache_while_pending_is_not_reported_as_zero_locations`, `test_a_failed_refresh_is_never_presented_as_a_success` | HOOT + rendered capture | — |
| Refresh authorization | `action_refresh_shopify_locations` | role/visibility/company/domain/credential | `test_the_public_action_admits_a_governed_job` | `test_an_auditor_is_refused`, `test_a_foreign_company_administrator_is_refused`, `test_a_foreign_and_a_nonexistent_id_refuse_identically`, `test_inventory_disabled_is_refused`, `test_missing_credential_evidence_is_refused_before_admission` | — | — |
| Mapping creation, cache-validated | `create_or_update_location_mapping` | `_validated_cached_location` | `test_creation_delegates_to_the_sanctioned_service`, `test_the_name_snapshot_comes_from_the_validated_cache`, `test_an_exact_repeat_submission_is_idempotent` | `test_an_arbitrary_gid_typed_by_a_browser_is_refused`, `test_a_foreign_store_gid_is_refused`, `test_an_inactive_gid_is_refused`, `test_a_duplicate_shopify_identity_is_refused`, `test_a_duplicate_odoo_identity_is_refused`, `test_a_non_internal_odoo_location_is_refused`, `test_a_cross_company_odoo_location_is_refused`, `test_a_nonexistent_odoo_location_is_refused`, `test_a_protected_field_create_is_still_refused_directly` | `shopify_connector_s1_location_tour` creates one and the test asserts the row + snapshot | Step lists at most 200 rows; truncation is disclosed and routes to the workspace |
| No name inference anywhere | — | explicit GID only | — | `test_no_mapping_is_ever_inferred_from_a_matching_name` (identical names, no mapping) | — | — |
| Remap safe and Administrator-only | `remap_location_mapping` | mixin behind extra checks | `test_an_exact_safe_change_moves_only_the_odoo_target`, `test_a_pending_pair_does_not_block_a_remap`, `test_a_finished_job_does_not_block_a_remap` | `test_administrator_is_required`, `test_explicit_confirmation_is_required`, `test_a_non_empty_reason_is_required`, `test_non_terminal_inventory_work_blocks_a_remap`, `test_a_previewed_or_confirmed_first_push_blocks_a_remap`, `test_a_foreign_company_target_is_refused`, `test_an_inactive_cached_shopify_location_is_refused`, `test_remapping_to_the_same_location_is_refused`, `test_a_non_internal_target_is_refused`, `test_a_nonexistent_target_is_refused` | — | **TD-020** — a confirmed first push makes the refusal permanent |
| Generic mixin not weakened | `action_override_binding` | untouched | `test_a_reviewer_can_still_use_the_generic_mixin_unchanged` | — | — | — |
| Audited reason sanitized | `remap_location_mapping` | `_audit_safe_reason` | `test_the_audited_reason_is_sanitized` (asserts the email absent and the marker present) | — | — | — |
| Five readiness presentation states | `_readiness_state` | projection | `test_a_not_applicable_check_is_not_required_not_passed`, `test_the_domain_check_reads_as_a_feature_selection` | `test_connect_only_produces_a_non_blocking_warning_in_these_words` (verbatim), `test_a_not_applicable_check_always_declares_itself` (AST guard) | HOOT all-five-states test; tour asserts `Not required` | — |
| Fix action deep-links by key | `_readiness_action` | `action_step_key` | `test_the_mapped_location_fix_action_deep_links_by_step_key` | asserts the value is not an int | `shopify_connector_s1_readiness_tour` clicks it and lands on step 7 | — |
| Fulfillment staff-permission guidance | `_check_fulfillment_staff_permission` | copy only | `test_fulfillment_readiness` (existing, unchanged severity) | — | — | Unprovable from API scopes by design |
| Sticky, responsive, focus-safe action row | setup SCSS/template | `position: sticky` + `scroll-margin` | `test_the_setup_action_row_stays_reachable_while_content_scrolls` (1366/1440/768/390 × 3 long steps) | `test_focus_near_the_bottom_of_long_content_is_not_concealed` | rendered captures + `shopify_connector_s1_keyboard_tour` per-control clearance assertion | — |
| Captures photograph the wizard, not its error branch | evidence harness | Administrator capture user | `test_the_setup_captures_render_the_wizard_not_a_permission_error` | asserts 12 steps + action row present | — | — |

## 4. Results

`[Fact]` Definitive run at the final head, clean worktree, source-head
verification enabled, zero Shopify operations.

| Pass | Result | Tests |
| --- | --- | --- |
| Fresh install + standard suite | **0 failed, 0 error(s)** | 2131 |
| Warm `-u` update + standard suite | **0 failed, 0 error(s)** | 2131 |
| Non-standard tag suite | __NONSTD__ | __NONSTDN__ |
| Required tours | **23 of 23** started and produced a success marker | — |
| HOOT suites | 3 of 3 verified | — |
| Skips | exactly one, the sanctioned `TestMutationRecovery.test_real_process_death_harness` | — |

### 4.0 Browser evidence

`[Fact]` Captured at exact executable head
`75ebb1560335390edc564854d473fc26699f2dcf` — the last production commit of
this batch — into
[`docs/05-qa/evidence/wave-5-onboarding-2026-07-29/`](evidence/wave-5-onboarding-2026-07-29/):
**11 of 11 visual-evidence tests passed**, 174 artifacts, 167 screenshots.

| Required capture | Where |
| --- | --- |
| Long Permissions step with sticky actions | `s1-setup-permissions-long-*`, `sticky-action-row.json` (`scopes@*`) |
| Location mapping with multiple cached locations | `s1-setup-location-mapping-*` (six cached locations seeded) |
| Final readiness with a long result list | `s1-setup-final-readiness-*` |
| A 390px mobile case | every capture set includes 390; sticky measured at 390 on all three steps |
| An RTL case | `*-rtl-*` at all three widths, with the connector root's computed `direction` read back |
| Reduced motion | `*-reduced-motion-1366px`, with computed durations read back |
| Keyboard focus near the bottom of long content | `sticky-focus-clearance.json`, `s1-setup-*-focus-bottom-*` |

Measured connector-owned horizontal overflow: **0 px** on every connector
surface at every width, in both LTR and RTL. Measured unreachable vertical
content: **0 px**, on every connector surface at every width.

### 4.1 Test-count delta, fully accounted

`[Fact]` The recorded historical baseline is **2040** fresh-install and
**2040** warm-upgrade tests. This head runs **2131** in each — a delta of
**+91**, and every one of them is a test added by this batch. Nothing was
removed, renamed away, or silently skipped.

| Where | Tests | What they hold |
| --- | --- | --- |
| `TestSetupWizardSemanticProgress` | 5 | key authority, legacy translation, in-place upgrade, no rewind |
| `TestSetupWizardConditionalLocationStep` | 5 | the conditional step's presence, position, copy, and that it enqueues and fabricates nothing |
| `TestSetupWizardReadinessPresentation` | 9 | the five states, staleness, the connect-only wording, the deep link, activation refusal |
| `TestSetupWizardSourceGuards` | 3 | no numeric navigation, every template branch a real key, every "Not applicable" declared |
| `TestLocationRemap` | 16 | authority, confirmation, reason, sanitisation, the exact safe change, and every safety refusal |
| `TestLocationRefreshAdmission` | 13 | the governed route, the state-derived job source, coalescing, and every refusal |
| `TestLocationRefreshState` | 4 | the four asynchronous states and the pending/failed disclosure |
| `TestLocationRefreshDispatch` | 4 | the dispatcher registry and the database consequence |
| `TestLocationRefreshHasNoTransportShortcut` | 2 | no surface holds a Shopify request |
| `TestSetupLocationStep` | 23 | the payload, creation through the sanctioned service, and every mapping refusal |
| `TestSetupWizardShape` (added) | 1 | the ordering invariant |
| `TestSetupWizardProgress` (added) | 1 | a numeric step is refused, not translated |
| `TestLocationMapping` (added) | 3 | uncached, foreign-store and inactive GIDs refused |
| `TestUiSetupTours` (added) | 2 | the location-step tour and the readiness deep-link tour |
| **Total** | **91** | matches 2131 − 2040 exactly |

### 4.2 Tour delta

`[Fact]` **21 → 23 required tours.** Two added:
`TestUiSetupTours.test_the_location_step_shows_every_cached_location_and_maps_one`
and `TestUiSetupTours.test_a_blocking_readiness_row_deep_links_by_step_key`.
One renamed: `test_setup_wizard_traverses_all_eleven_steps` →
`..._all_twelve_steps`. `tools/run_connector_suite.sh`'s
`REQUIRED_TOUR_TESTS` is updated to match, and
`test_phase_contract.py::test_every_tour_test_is_listed_in_the_suite_runner`
asserts the runner's inventory equals the tours that actually exist, so the
two cannot drift.

### 4.3 HOOT delta

`[Fact]` **9 → 17** tests in the `shopify connector setup wizard` suite; the
other two suites are unchanged at 8 and 11. `EXPECTED_SUITES` in
`test_u3_hoot_suite.py` is an EXACT count by design, so this is declared in
the same change rather than allowed to drift.

## 5. Commands

```
tools/run_connector_suite.sh
```

with `PGHOST`, `PGPORT`, `ODOO_BROWSER_BIN`, `ODOO_SRC` and `SOURCE_HEAD_SHA`
set for the environment. The runner performs the fresh-install pass, the warm
`-u` pass and the non-standard tag pass, verifies the Odoo pin, verifies the
declared source head against the checkout, refuses to run without a working
browser or `websocket-client`, and fails on an unexpected skip, a missing
tour or a missing HOOT marker.

## 6. Not claimed

- **No Odoo.sh run.** This is local supporting evidence.
- **No Shopify validation**, no live campaign, no UAT, no dev-store contact.
- **No acceptance, review, ready-mark or merge.** PR #204 stays draft.
- **No claim about `fulfillment_staff_permission`.** Its wording was corrected
  to name the two axes and the exact Shopify navigation path; its warning
  severity and its not-proven verdict are unchanged, and it remains
  unprovable from API scopes.
