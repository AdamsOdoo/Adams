# PR #204 — description as it stood before the 2026-07-29 merchant-operability closure batch

> **Verbatim archive. Not a new claim.** This file preserves the complete
> description of draft PR #204 (`fable/wave-5-completion` →
> `mvp/program-integration`) exactly as it stood at head
> `50b770a315b53f0c05f0b8867bb801d75c6476ef`, immediately before the
> merchant-operability closure batch replaced the live body.
>
> **Why it exists.** The new current section plus this record exceed GitHub's
> 65,536-character pull-request body limit. Rather than truncate any of the
> historical record, the whole pre-edit live body is kept here, in the
> repository, which CLAUDE.md §3 makes the single source of truth. The live
> PR body carries the new current section, a link to this archive, and the
> unambiguous statement that the rejected single-package experiment remains
> rejected and reverted.
>
> **Nothing below the marker is edited, corrected, re-dated or re-scoped** —
> including the handful of pre-existing HTML-entity artefacts (`&gt;`,
> `&#34;`, `&#39;`) in its older sections, which are preserved exactly as
> they stood on GitHub. Statements in it were true of the heads they
> describe and are superseded — not retracted — by the live body's current
> section. In particular, the single-package dependency-recovery experiment
> it documents **remains rejected and reverted**; nothing in this archive
> revives it.

---

## The pre-edit live body, verbatim, from here to the end of the file

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

# BOUNDED UAT-CRITICAL ONBOARDING, LOCATION MAPPING AND FINAL READINESS

&gt; **2026-07-29. This section is current and supersedes every head-SHA, scope
&gt; and evidence statement below it.** Everything below it is retained verbatim
&gt; as the historical record — including the reversion record, which is
&gt; unchanged and still accurate about what it describes.
&gt;
&gt; **Status: implementation only.** NOT an acceptance, NOT a review, NOT a
&gt; ready-mark, NOT a merge, NOT self-accepted, and NOT an Odoo.sh, Shopify,
&gt; campaign or UAT claim.

| Item | Value |
| --- | --- |
| **Starting head** | `d6d44fa6d93ac688d6ca6f187f552586e1616461` (the accepted rollback head) |
| **Final head** | `50b770a315b53f0c05f0b8867bb801d75c6476ef` (documentation-only tail) |
| **Final executable head** | `624bf8f25d53e4bdbf219d31d0d899448c7cc4e7` — where the definitive suite ran |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` |
| Previously qualified executable ancestor | `ee23c966a0b214c7974abbade4b384f251c4940f` |
| History operation | **Additive only.** No rebase, reset, amend, squash or force-push. The unsigned rollback commits are untouched |
| Identity gate | local HEAD = `origin/fable/wave-5-completion` = PR #204 head at start; PR open, draft, unmerged; worktree clean; `addons/shopify_connector/**` absent; Actions run `30470359888` on that exact SHA `completed` / `success` |

## Commits

| Commit | Subject |
| --- | --- |
| `ed541e7` | Guided setup: 12 steps, addressed by semantic key |
| `e022655` | Inventory: a customer-operable route to a mapped Shopify location |
| `e91378f` | Setup browser evidence: the location step, the deep link, the sticky bar |
| `75ebb15` | The setup surface&#39;s content was clipped and unreachable |
| `7171f43` | Wave 5 onboarding: rendered browser evidence |
| `624bf8f` | Docs: record the bounded onboarding batch |
| `836aca7` | Record the definitive validation run *(documentation only)* |
| `50b770a` | Archive PR #204&#39;s pre-batch description verbatim *(documentation only)* |

All additive and fast-forward from `d6d44fa6d93ac688d6ca6f187f552586e1616461`.

`624bf8f2` is the **final executable head** — every production, test, tooling
and evidence path is at that commit, and the definitive suite ran there.
`836aca7` records that run&#39;s results and `50b770a` archives this PR&#39;s
pre-batch description; neither changes an executable path. Results cannot be
recorded before the run that produces them exists, so the recording commits
are necessarily the tail.

## Changed paths

**Production — `shopify_connector_core`**
- `models/shopify_connector_setup_wizard.py`, `models/shopify_connector_store_settings.py`, `models/shopify_connector_readiness_check.py`
- `migrations/19.0.1.15.0/post-migrate.py` (new), `__manifest__.py` (19.0.1.14.0 → 19.0.1.15.0)
- `static/src/js/shopify_connector_setup_wizard.js`, `static/src/xml/shopify_connector_setup_wizard.xml`, `static/src/scss/shopify_connector_setup_wizard.scss`
- `static/src/js/tours/shopify_connector_s1_setup_tour.js`

**Production — `shopify_connector_inventory`**
- `models/shopify_connector_inventory_service.py`, `models/shopify_connector_inventory_setup.py` (new), `models/__init__.py`
- `wizards/shopify_connector_inventory_ui_wizards.py`
- `views/shopify_connector_inventory_wizard_views.xml`, `views/shopify_connector_inventory_views.xml`, `views/shopify_connector_inventory_menus.xml`
- `security/ir.model.access.csv`, `__manifest__.py` (19.0.1.3.0 → 19.0.1.4.0)

**Production — outside the two families, and why**
- `shopify_connector_fulfillment/models/shopify_connector_readiness_check.py` — the packet&#39;s §10 fulfillment staff-permission copy, plus three `not_applicable=True` markers. Severity, tier and verdict unchanged.
- `shopify_connector_product_export/models/shopify_connector_product_export_seams.py` — **one keyword argument.** Its `product_export_scopes` check returns &#34;Not applicable&#34; when the export domain is off; without the marker the setup surface would render that as a green **Passed** for a domain the operator deliberately disabled, which §10 forbids. Nothing else in that module&#39;s production code is touched.

**Tests**
- `shopify_connector_core/tests/`: `test_setup_wizard.py`, `test_readiness_check.py`, `test_credential_service.py`, `test_ui_setup_tours.py`, `test_ui_visual_evidence.py`
- `shopify_connector_core/static/tests/shopify_connector_setup_wizard.test.js`
- `shopify_connector_inventory/tests/`: `test_location_mapping.py`, `test_location_refresh_action.py` (new), `test_setup_location_step.py` (new), `__init__.py`
- `shopify_connector_product_export/tests/test_u3_hoot_suite.py` — the exact HOOT count, declared in the same change

**Qualification**
- `tools/run_connector_suite.sh` — `REQUIRED_TOUR_TESTS` only: two added, one renamed

**Documentation**
- `docs/02-product/ui-ux-final-design-spec.md`, `docs/07-implementation-plan/wave-5-completion-gate-state.md` (§5e.9), `docs/05-qa/wave-5-onboarding-completion-validation-results.md` (new), `docs/05-qa/technical-debt-register.md` (TD-020), `docs/01-research/research-handoff.md`, `CHATGPT.md` (§18.16–§18.18)
- `docs/05-qa/evidence/wave-5-onboarding-2026-07-29/` (new) — 174 browser-evidence artifacts, plus `manifest.json` and the runner&#39;s `definitive-suite-summary.json`
- `docs/07-implementation-plan/pr-204-body-archive-2026-07-29.md` (new) — this PR&#39;s pre-batch description, verbatim, because the body exceeds GitHub&#39;s 65,536-character limit

**Executable delta.** Every changed executable path is inside
`shopify_connector_core`, `shopify_connector_inventory`, the two files named
above, and `tools/run_connector_suite.sh`. No workflow, no `requirements*.txt`,
no Dockerfile, no Odoo core, no monkey-patch, no direct SQL for production
state, and no `addons/shopify_connector/**`.

## What this is, and what it deliberately is not

The control room&#39;s bounded post-reversion onboarding scope, and nothing else.
**No part of the rejected single-package dependency-recovery architecture is
reintroduced**: `addons/shopify_connector/**` does not exist, and there is no
customer package controller, no reverse module dependency, no
component-uninstall protection, no dependency-loss pause, no dependency
snapshot or restoration, no automatic technical-module installation, and no
DEC-042 / TD-017 / TD-018 / TD-019 work. Dependency-uninstall survival stays
deferred from the MVP.

No new architecture decision is created. The register was inspected before any
identifier could be assigned; nothing here is a new architectural choice, only
the delivery of scope the existing decisions already describe.

## The five verified starting defects, closed

### 1. Readiness ran before the choices it reads

**Was:** an 11-step flow with readiness at position 6 — before *what to sync*,
*source of truth*, *customer notifications* and *first stock push*.
`domain_flag_enablement` and `mapped_location` read exactly those, so the
screen an operator was asked to act on evaluated a store that did not exist
yet. Activation compensated by re-running readiness server-side, which made
activation correct and left the operator-facing step misleading.

**Now:** the exact 12-step sequence, with `final_readiness` at 11.

| # | Key | Step |
| --- | --- | --- |
| 1 | `welcome` | Welcome |
| 2 | `identity` | Store identity |
| 3 | `credential` | Credentials |
| 4 | `scopes` | Permissions |
| 5 | `test_connection` | Test connection |
| 6 | `directions` | What to sync |
| 7 | `location_mapping` | Location mapping |
| 8 | `source_of_truth` | Source of truth |
| 9 | `notification` | Customer notifications |
| 10 | `first_push` | First stock push |
| 11 | `final_readiness` | Final readiness |
| 12 | `review` | Review and activate |

Entering step 11 evaluates the currently saved configuration; changing
anything a check reads marks the earlier result stale rather than leaving it
on screen as a success; and activation still re-runs the whole set
server-side, because the review step is one an operator can sit on while a
setting changes in another tab.

### 2. Progress was addressed by position

**Was:** `setup_wizard_step`, an integer index into an order that this change
alters. A stored `8` meant *Source of truth* before and would have meant
*Customer notifications* after.

**Now:** `setup_wizard_step_key` is the authority for persistence,
validation, navigation, deep links, conditional skipping and resume; the
ordinal is derived from the accepted tuple for display only. `save_and_exit`
**refuses** an ordinal rather than translating it — quietly reinterpreting it
would resume an operator on a screen they never asked for.

**Existing progress moves and loses nothing.**
`19.0.1.15.0/post-migrate.py` translates each stored number through the OLD
eleven-step order, and `_resume_key` applies the identical translation at read
time for any row the migration did not reach. Legacy 6 (&#34;Readiness checks&#34;)
resumes at `directions` — its readiness evidence is untouched and is
re-evaluated by `final_readiness`. No store is reset; no durable choice is
rewritten; the mapping is monotone, so no two administrators&#39; progress is
shuffled relative to each other.

A legacy store resuming past `directions` skips the new `location_mapping`
step. That is **not** a silent skip: with inventory enabled and nothing
mapped, `mapped_location` reports **Blocking** on step 11 with a *Fix location
mapping* action that deep-links back to step 7 by key.

### 3. `_enqueue_location_sync` had no customer-operable route

**Was:** a correct admission service and a correct handler, reachable by
nothing. The location cache could only be populated by the scheduled cron on
an already-activated store — while `mapped_location` is an essential check
that blocks activation, needs a mapping, which needs a Shopify location, which
needed the store activated first. A circular gate.

**Now:** one public guarded `action_refresh_shopify_locations`, reached from
the setup step and from the Location Mapping workspace, admitting an
`inventory_location_sync` job through the ordinary queue and the ordinary
dispatcher to `_handle_inventory_location_sync`.

**Why the pre-activation path is not a hole in the business gate.** The job
source is derived from the store&#39;s own lifecycle state, and only two states
admit anything:

- `connected` → `manual_sync`, fully business-gated at create and at start;
- `setup_incomplete` → `setup_readiness_check`, one of core&#39;s two sources
  deliberately exempt from store-state gating *because such jobs exist to
  determine connection/readiness state, so gating them on `connected` would be
  circular* — core&#39;s own words, unchanged.

`reconnect_needed`, `disconnecting` and `disconnected` are **refused
outright** rather than routed down the ungated path. That refusal is what
keeps a deliberate exemption from becoming a way around the business gate, and
it is asserted with the job count. No new `job_source` value; no change to
core&#39;s gating; `inventory_domain_enabled` still gates every one of them at
start.

**No surface holds a transport.** Asserted from the sources across every
wizard, controller, setup service and browser asset.

### 4. Any GID string could be mapped

**Was:** `create_or_update_location_mapping` accepted whatever string it was
given, and never wrote `shopify_location_name_snapshot`. Every existing test
passed a fabricated GID and passed — which is the proof nothing checked it.

**Now:** the GID must name a currently-**active** cached
`shopify.connector.location` belonging to **this** store, and the snapshot
comes from that validated row rather than from caller input. Arbitrary,
foreign-store and inactive GIDs are refused with identical non-enumerating
messages.

**And a second defect the work itself surfaced.** The service documented
&#34;resolves and validates `odoo_location` in the caller&#39;s own (non-elevated)
environment&#34; and did not: a recordset carries its own environment, so every
visibility and company question was being answered by whatever environment
the caller built — including `sudo()`. Rebound with `with_env(self.env)`. The
fixtures that had been masking this created users holding only a connector
group, which is not a shape a real backend user takes; they now carry
`base.group_user`, and the caller&#39;s own `stock.location` right is what decides
whether they may map a location.

### 5. The workspace promised a mapping route it did not have

**Was:** `create=&#34;false&#34;` on both the list and the form (correctly — the
binding mixin refuses a generic create of protected identity fields) and copy
saying a mapping &#34;is created&#34;, with nowhere to create one.

**Now:** three governed wizards — **Refresh Shopify locations**, **Map a
Shopify Location**, and **Remap** on the mapping form — each collecting the
arguments the sanctioned service requires and delegating. `create=&#34;false&#34;` is
unchanged.

**Remap does not expose `action_override_binding`.** The mixin admits Reviewer
*or* Administrator and proves nothing about whether an inventory remap is
operationally safe, so it is reached through an Administrator-only
`remap_location_mapping` that additionally requires explicit confirmation and
a non-empty sanitized reason, re-validates the cached Shopify location,
enforces company and store isolation, and refuses while non-terminal inventory
work exists or any pair&#39;s first push is `previewed`/`confirmed`. The mixin is
neither weakened nor bypassed; the Shopify identity is never touched; nothing
is unlinked and recreated.

## Final readiness presentation

Five states — **Passed, Warning, Blocking, Waiting, Not required** — projected
from the readiness service&#39;s own `{tier, result}` verdict plus the three facts
the verdict does not carry: whether the check applies at all, whether a
location refresh is still in flight, and whether the evidence predates the
configuration it describes. **Readiness remains a server-owned decision**;
Owl renders the result and computes nothing.

- No green result for a check that did not run, is stale, is waiting on a
  refresh, is not proven, or covers a disabled domain.
- **Stale outranks Not required**, because &#34;not applicable&#34; is itself a
  conclusion about a configuration that may have changed.
- `not_applicable` is an explicit key on the check result, not a phrase
  matched inside translatable copy — with an AST guard across every connector
  module asserting that every &#34;Not applicable&#34; result declares it.
- *At least one thing is set to sync* → **Sync features selected**.
- Connect-only, verbatim: *No sync features are enabled. This store will
  connect without syncing. You can enable features later from Store Settings.*
- `mapped_location`: label **Inventory location mapping**; Blocking when
  inventory is on and no valid mapping exists; **Not required** when inventory
  is off; **Waiting** while a refresh is pending; never **Passed** for a
  failed refresh; action *Fix location mapping*, deep-linked by step **key**.
- `fulfillment_staff_permission`: states that Shopify API scopes and Shopify
  staff permissions are separate axes, that the connector cannot prove the
  staff role automatically, and gives the exact path *Shopify Admin →
  Settings → Users and permissions → role → Orders → Fulfill and ship*. Its
  warning severity and not-proven verdict are unchanged.

## Credential guidance

The Credentials step now says, in these terms: Odoo requires the **Admin API
access token**; a **Client ID** is not the access token; a **Client Secret**
is not the access token; those two may be used *outside* Odoo to obtain an
access token but neither belongs in the field; and token lifetime **depends on
the authentication method** — with no claim that every Shopify token expires
after 24 hours.

The write-only implementation is unchanged. The token is never returned to the
browser, never held in Owl state, never logged, never in a URL, never in an
error, and never in a screenshot or evidence fixture — the input is a password
field and is removed from the DOM once submitted, both asserted in the browser.

## Sticky, responsive action bar

Back / Continue / Activate / Save &amp; Exit stay reachable while long content
scrolls. A normal-flow sibling after the panel with `position: sticky;
inset-block-end: 0`, so at the bottom of the page it settles into its own
space and covers nothing — a fixed bar would not. Connector design tokens
only, logical properties throughout, no external library, font or CDN, no
transition or animation on it at all, and `env(safe-area-inset-bottom)` so it
clears a phone&#39;s home indicator.

Keyboard focus is kept clear of it by `scroll-margin-block-end` on every
focusable element in the surface — the scroll container is Odoo&#39;s
`.o_content`, which is not this repository&#39;s to restyle, so the clearance is
reserved from the side we own.

One correction worth naming: `.o_sc_setup` carried `overflow-x: hidden`, which
makes the used `overflow-y` compute to `auto` and turns the element into a
scroll container — `position: sticky` would then have resolved against a box
that never scrolls and silently stopped being sticky. It is now `overflow-x:
clip`, which suppresses horizontal overflow without creating a scroll
container.

## Security and data integrity

`[Fact]` Each row is asserted by a named test, and every refusal test also
asserts that **nothing happened** — the job count, the mapping, or the stored
value is checked afterwards.

| Property | How it is held |
| --- | --- |
| Administrator-only guided setup | `_assert_setup_admin` on every entry point including the read; Connector User, plain internal user and wrong-company Administrator all refused |
| Operator/Administrator for refresh and mapping creation | the established role policy, unchanged and not broadened; Auditor refused |
| Administrator-only remap | Reviewer and Operator both refused, with the mapping asserted unchanged |
| Ordinary record visibility before elevation | `check_access` as the calling user in `_resolve_store`, `_resolve_store_for_location_action` and on the Odoo location — **and the recordset rebound into the service&#39;s own environment first**, without which a `sudo()` recordset answered its own visibility question |
| Store-company and `env.companies` consistency | checked before every elevation; evaluated against the switcher selection, not `user.company_ids` |
| No cross-company cache, mapping, stock-location or store access | foreign-store cache rows never listed; foreign-company Odoo locations never offered and refused on submit; foreign store ids refused |
| Non-enumerating refusals | a real-but-foreign store and a nonexistent one produce the identical exception class and message, asserted directly |
| No arbitrary Shopify Location GID can be mapped | must name an active cached row of this store; uncached, foreign-store and inactive all refused |
| No direct protected-field browser write | the binding mixin is unchanged and a direct create is still refused, asserted |
| No name-based inference | asserted with a deliberately name-identical Odoo/Shopify pair that produces no mapping |
| No credential, PII or raw Shopify response in logs, notifications, screenshots or evidence | refusals carry the fixed `error_class` vocabulary only; the remap reason is sanitized through `_audit_safe_reason` (a merchant email is asserted absent and replaced by the redaction marker); evidence scanned |
| No Shopify mutation path added | the only new job type usage is the existing read-only `inventory_location_sync`, whose replay policy is asserted read-safe |
| Location refresh read-only and job-governed | admits a job and returns it; no surface holds a transport, asserted from the sources |
| Setup completion and activation start no synchronisation | job counts asserted unchanged, with a transport stand-in that fails on contact |
| Remap cannot bypass protected-binding invariants | the mixin is called, not replaced; its own Reviewer-or-Administrator admission asserted unchanged |
| A crafted RPC cannot bypass server checks | every guard is server-side and re-run as the calling user; the arbitrary-GID, foreign-id and numeric-step tests are exactly that shape |
| Sudo is narrow and post-check | the core frozen sudo-site inventory is updated with the three new sites and their stated purposes, so a fourth would fail the guard |

The connector role hierarchy is **not broadened**. No group, no implication
and no ACL grant on an existing model changes; the only ACL additions are the
minimum rows for the three new transient wizards.

## Tests

`[Fact]` Definitive run at the final **executable** head
`624bf8f25d53e4bdbf219d31d0d899448c7cc4e7`, clean worktree, source-head
verification enabled, zero Shopify operations. The only later commits,
`836aca7` and `50b770a`, are documentation and change no executable path.

```
tools/run_connector_suite.sh
```

| Pass | Result | Tests |
| --- | --- | --- |
| Fresh install + standard suite | **0 failed, 0 error(s)** | 2131 |
| Warm `-u` update + standard suite | **0 failed, 0 error(s)** | 2131 |
| Non-standard tag suite | **0 failed, 0 error(s)** | 42 |
| Required tours | **23 of 23** started and produced a success marker, in both browser-bearing passes | — |
| HOOT suites | **3 of 3** verified | — |
| Skips | exactly one per pass, the sanctioned `TestMutationRecovery.test_real_process_death_harness` | — |

**Non-standard delta: 39 → 42.** All three are the visual-evidence tests
this batch adds — that file goes from 8 test methods to 11. The HOOT change
below adds no Python test, because a HOOT suite runs as browser JS inside one
existing Python test.

**Environment.** Odoo pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1`,
verified on every run; PostgreSQL 16.13; Python 3.11.15; Chromium
141.0.7390.37, resolved and proven to render before any browser-bearing pass.

### Count deltas, fully accounted

The recorded historical baseline is **2040** fresh and **2040** warm. This
head runs **2131** in each — **+91**, and all 91 are tests this batch adds.
Nothing was removed, renamed away or silently skipped.

| Where | + | What it holds |
| --- | --- | --- |
| `TestSetupWizardSemanticProgress` | 5 | key authority, legacy translation, in-place upgrade, no rewind |
| `TestSetupWizardConditionalLocationStep` | 5 | the conditional step&#39;s presence, position, copy, and that it enqueues and fabricates nothing |
| `TestSetupWizardReadinessPresentation` | 9 | the five states, staleness, the connect-only wording, the deep link, activation refusal |
| `TestSetupWizardSourceGuards` | 3 | no numeric navigation, every template branch a real key, every &#34;Not applicable&#34; declared |
| `TestLocationRemap` | 16 | authority, confirmation, reason, sanitisation, the exact safe change, every safety refusal |
| `TestLocationRefreshAdmission` | 13 | the governed route, the state-derived job source, coalescing, every refusal |
| `TestLocationRefreshState` | 4 | the four asynchronous states and the pending/failed disclosure |
| `TestLocationRefreshDispatch` | 4 | the dispatcher registry and the database consequence |
| `TestLocationRefreshHasNoTransportShortcut` | 2 | no surface holds a Shopify request |
| `TestSetupLocationStep` | 23 | the payload, creation through the sanctioned service, every mapping refusal |
| `TestSetupWizardShape` | 1 | the ordering invariant |
| `TestSetupWizardProgress` | 1 | a numeric step is refused, not translated |
| `TestLocationMapping` | 3 | uncached, foreign-store and inactive GIDs refused |
| `TestUiSetupTours` | 2 | the location-step tour and the readiness deep-link tour |
| **Total** | **91** | = 2131 − 2040, exactly |

**Tours: 21 → 23.** Two added, one renamed
(`..._all_eleven_steps` → `..._all_twelve_steps`). `REQUIRED_TOUR_TESTS` is
updated, and `test_phase_contract.py` asserts that inventory equals the tours
that actually exist, so the two cannot drift.

**HOOT: 9 → 17** in the setup-wizard suite; the other two unchanged at 8 and
11. `EXPECTED_SUITES` is an exact count by design, so it is declared here
rather than allowed to drift.

Tests were written to fail on the starting head for the corresponding defect
where meaningful — the semantic-key field does not exist there, the twelve-step
order is a different order, `action_refresh_shopify_locations` and
`remap_location_mapping` do not exist, and the arbitrary-GID and
caller-environment refusals were the defects. Every refusal test asserts a
database consequence rather than passing because no work was admitted.

## Browser evidence

Captured at exact executable head `75ebb1560335390edc564854d473fc26699f2dcf`
— the last production commit of this batch — into
`docs/05-qa/evidence/wave-5-onboarding-2026-07-29/`. **11 of 11
visual-evidence tests passed**; 174 artifacts, 167 screenshots.

| Required capture | Where |
| --- | --- |
| Long Permissions step with sticky actions | `s1-setup-permissions-long-*`, `sticky-action-row.json` |
| Location mapping with multiple cached locations | `s1-setup-location-mapping-*` (six cached locations) |
| Final readiness with a long result list | `s1-setup-final-readiness-*` |
| A 390px mobile case | every set; sticky measured at 390 on all three long steps |
| An RTL case | `*-rtl-*` at all three widths, connector root `direction` read back |
| Reduced motion | `*-reduced-motion-1366px`, computed durations read back |
| Keyboard focus near the bottom of long content | `sticky-focus-clearance.json`, `s1-setup-*-focus-bottom-*` |

Each capture records the head, the route, the viewport, LTR/RTL, the
reduced-motion state, the expected assertion, the measured horizontal
overflow, the keyboard-focus assertion where applicable, whether the measured
content is connector-owned, and that no secret or PII is visible.

**Measured connector-owned horizontal overflow: 0 px**, every connector
surface, every width, both directions. **Measured unreachable vertical
content: 0 px**, same coverage.

All twelve sticky cases are genuinely mid-scroll on `.o_sc_setup` — scroll
extents 328–1774 px, scrolled to the midpoint — with the bar&#39;s bottom edge
equal to the scrollport&#39;s pin target to the pixel.

Browser evidence is not used as proof of server-side authorization or job
governance anywhere; those are asserted by the server tests listed above.

## Adversarial self-review — findings this session produced and corrected

1. **`create_or_update_location_mapping` never resolved in the caller&#39;s
   environment** despite documenting that it did. Corrected with
   `with_env(self.env)`; the fixtures masking it were users who could not
   exist. *(P0 — a documented security property that was not in force.)*
2. **The rendered-evidence harness ran as a Connector User against an
   Administrator-only screen.** `.o_sc_setup` is present in the component&#39;s
   error branch too, so the S1 capture had been photographing a permission
   error while passing every assertion. Corrected, plus a new test that
   distinguishes the wizard from its own error branch. *(P1 — evidence that
   proved nothing.)*
3. **The first version of the numeric-navigation source guard found its own
   documentation.** The comments necessarily quote `state.step === 8` to warn
   about it. The guard now scans code with comments stripped. *(P2 — a guard
   that fails for the wrong reason gets deleted.)*
4. **An unescaped CSS `max(var(), env())` in SCSS failed the entire asset
   bundle**, and surfaced as an unrelated export tour failing with &#34;Style
   error&#34;. Interpolated. *(P0 — every connector stylesheet was gone.)*
5. **Stale must outrank Not required** in the readiness projection: &#34;not
   applicable&#34; is a conclusion about a configuration that may have changed,
   so ranking it first left the one row an operator most needed to re-read
   looking settled. Reordered. *(P1.)*
6. **The setup surface&#39;s content was clipped and unreachable — at every
   width, before this batch.** A client action renders inside
   `.o_action_manager`, which is `overflow: hidden` and scrolls nothing of
   its own. With `min-height: 100%` on `.o_sc_setup`, the instrument
   measured **328–1774 px** of setup content overflowing that ancestor with
   `doc_extent: 0` and no scrollable element anywhere in the chain: the
   bottom of every long step was clipped away with no scrollbar for anyone
   to notice. The surface now owns its own scrolling, which also gives
   `position: sticky` a real scrollport. *(P0 — and the reason a sticky
   action row mattered at all: it would otherwise have been polish on an
   unusable screen.)*
7. **The sticky bar&#39;s negative inline margin was a real connector-owned
   horizontal overflow.** It bled the bar&#39;s background 16px past
   `.o_sc_setup__inner` on each side so it would span the full surface; the
   TD-016 instrument measured `scroll_width 896` against `client_width 880`
   at every width in both LTR and RTL and failed the run. Removed — the bar
   spans the content column, which is what it should have done. *(P1 — and
   the one finding in this list that was caught by the evidence harness
   rather than by reading the code, which is the harness working.)*
8. **Three corrections to the instrument itself**, each because the first
   version could have returned a green result that meant nothing: it now
   reports the whole ancestor chain, so &#34;nothing scrolled&#34; is
   distinguishable from &#34;the scroll was attempted and the page was already
   in the middle&#34;; it measures the bar against the **scrollport&#39;s pin
   target** rather than `innerHeight`, which reported the surface&#39;s own
   32px padding as a defect and would have had a correct sticky bar &#34;fixed&#34;
   into a wrong one; and the focus-clearance test records the cases it skips
   and asserts a floor on the number actually measured. *(P1 — a measurement
   that cannot fail is not evidence.)*

## Remaining limitations

- **TD-020 (new, Medium).** A Shopify location whose pairs have a
  **confirmed** first push can never be remapped. The refusal is correct —
  re-pointing under a confirmed pair would reuse a human&#39;s explicit
  confirmation for a warehouse nobody reviewed — but `confirmed` is terminal,
  so it is permanent rather than a wait. Unwinding a confirmed first push is a
  first-push-guard decision needing its own governed route and consequence
  disclosure; inventing one inside a bounded onboarding batch would be exactly
  the scope drift the batch forbids. Recorded, with the boundary proven by
  test rather than assumed.
- The Location mapping step lists at most 200 cached Shopify locations and 200
  eligible Odoo locations. Truncation is **disclosed on screen** and routes
  the operator to the searchable workspace list.

## Remaining gates

1. **Independent delta and security review** of this exact head — not this
   session, and not a subagent of it.
2. **Exact-head Odoo.sh qualification.**
3. **A new controlled Shopify validation environment.**
4. **UAT.**
5. **Acceptance and merge authorization** by the control room / product owner.

## Explicit confirmations

- **No Shopify contact.** No store, credential, request, mutation or webhook
  at any point.
- **No credential use.** No Shopify secret was read, held or transmitted.
- **No campaign** issued or resumed.
- **No Odoo.sh run**, and no Odoo.sh claim.
- **No UAT.**
- **No ready-mark, no approval, no merge, no self-acceptance.** PR #204 stays
  draft and open. No issue was closed.

---

**`DRAFT — REJECTED BATCH REVERTED — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

# CONTROL-ROOM REJECTION AND ADDITIVE REVERSION OF THE SINGLE-PACKAGE DEPENDENCY-RECOVERY EXPERIMENT

&gt; **2026-07-29. This section is current and supersedes every head-SHA, scope
&gt; and evidence statement below it. Everything below the horizontal rule is
&gt; retained verbatim as the historical record of the rejected experiment and
&gt; of the cycles that preceded it — it is not rewritten, and it must not be
&gt; read as describing the current head.**
&gt;
&gt; **Status: reversion + governance record only. NOT an acceptance, NOT a
&gt; review, NOT a ready-mark, NOT a merge, NOT a runtime, Shopify or UAT
&gt; claim, and NOT a new architecture decision.**

The control room has **REJECTED** the implementation batch from
`4ac4ce2a5144907673fea1b753764823857916aa` (exclusive) through
`69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` (inclusive). It does **not**
proceed to independent acceptance review, Odoo.sh qualification, Shopify
validation, UAT, ready-mark or merge. The rejected architecture was **not
repaired or redesigned** — it was reverted.

| Item | Value |
| --- | --- |
| **Rejected starting head** | `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` |
| **Final head** | `d6d44fa6d93ac688d6ca6f187f552586e1616461` |
| Restored executable checkpoint | `4ac4ce2a5144907673fea1b753764823857916aa` |
| Previously accepted Odoo.sh-tested executable ancestor | `ee23c966a0b214c7974abbade4b384f251c4940f` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor, 0 behind) |
| History operation | **Additive only.** Fast-forward `69562d3..d6d44fa`. No rebase, reset, amend, squash or force-push; 0 merge commits added |
| Changed paths vs `4ac4ce2a` after reversion | **1** — `docs/07-implementation-plan/wave-5-completion-gate-state.md` (the authorized governance record) |
| Executable delta vs `4ac4ce2a` and vs `ee23c966` | **ZERO** under `addons/**`, `tools/**`, `.github/**` |
| Shopify | **none** — no store, credential, request, mutation or webhook, in this cycle or any commit on this PR |

## Exact revert commits

| Commit | Role |
| --- | --- |
| [`6c6cef38d08cb7e855736164618e19c4791f7fc2`](https://github.com/AdamsOdoo/Adams/commit/6c6cef38d08cb7e855736164618e19c4791f7fc2) | Additive revert of all seven rejected commits, applied newest-first |
| [`d6d44fa6d93ac688d6ca6f187f552586e1616461`](https://github.com/AdamsOdoo/Adams/commit/d6d44fa6d93ac688d6ca6f187f552586e1616461) | Documentation-only governance record (`wave-5-completion-gate-state.md` §5e.8) |

**The seven reverted commits, full SHAs, newest-first:**

1. `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`
2. `105314d1373b0c7f6a9e414d2a5da52cef852d3d`
3. `a208a562f1cf9249c9f7e4f0a30e75131a477058`
4. `ffb769c7a8ed6f0a71390f77b8e993d229430a94`
5. `b44ccce24fae99660e10011c2670f94a270e2a2f`
6. `6e622e1ca72d8ce196d824858bff514f4142cc03`
7. `6e1db1d271fce14676ebede9db340c6ad248d7c2`

All seven remain **reachable and unmodified** in this branch&#39;s history. Nothing
at or before `4ac4ce2a` was reverted or modified. Abbreviated SHAs in the
governing instruction were resolved and range-verified before the revert:
`ffb769c` → `ffb769c7a8ed6f0a71390f77b8e993d229430a94`, `b44ccce` →
`b44ccce24fae99660e10011c2670f94a270e2a2f`, `6e622e1` →
`6e622e1ca72d8ce196d824858bff514f4142cc03`.

## Why it was rejected

1. **TD-019 is a feasibility blocker for the rejected architecture, not
   acceptable technical debt.** A standard-dependency cascade physically
   deletes domain-owned mappings, bindings, jobs, logs and mutation
   evidence.
2. That outcome **violates mandatory feasibility invariant H** and should
   have triggered the governing prompt&#39;s **Section 30 no-edit stop** before
   any file was edited.
3. The global resume implementation does not perform **per-store
   selection**, **production-path readiness**, **explicit store
   confirmation**, **interrupted-job reconciliation**, or **prevention of
   automatic queued-work resumption**.
4. The pause record and workflow **omit mandatory audit and recovery facts**.
5. **Restore does not upgrade every component.**
6. The required **setup, mapping, remap, readiness and browser-evidence
   scope was not implemented** — **Sections 15–20 and 26 were not
   delivered**.
7. Customer-facing copy claiming affected components are *&#34;paused
   automatically, not deleted&#34;* is **false**: Odoo removes the modules and
   their owned tables.

**TD-017 and TD-018 were mandatory gaps, not accepted limitations.** The
rejected batch logged them as scoped-out debt; the control room does not
accept that classification — they are the same defects named in reasons 3
and 5. TD-017, TD-018 and TD-019 were introduced by the reverted commits and
do not exist in the restored tree.

## Exact path result

```
$ git diff --name-status 4ac4ce2a5144907673fea1b753764823857916aa d6d44fa6d93ac688d6ca6f187f552586e1616461
M	docs/07-implementation-plan/wave-5-completion-gate-state.md
```

One path — the authorized governance record — and nothing else. The new
`addons/shopify_connector/**` family no longer exists (`git ls-tree
d6d44fa addons/shopify_connector` → 0 entries). All six pre-existing
connector manifests and production files match `4ac4ce2a` byte-for-byte.

## Zero executable-delta proofs

```
$ git diff --name-only 4ac4ce2a d6d44fa -- addons tools .github     # 0 paths
$ git diff --name-only ee23c966 d6d44fa -- addons tools .github     # 0 paths
```

Subtree object-hash equality — the strongest available proof, identical
across all three references:

| Path | `ee23c966` | `4ac4ce2a` | `d6d44fa` (final) |
| --- | --- | --- | --- |
| `addons/` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` |
| `tools/` | `eede631173b4f9f006ab572b469084cffc0a05bc` | `eede631173b4f9f006ab572b469084cffc0a05bc` | `eede631173b4f9f006ab572b469084cffc0a05bc` |
| `.github/` | `f109452f4bd4caba17df7c207683308a68f69a27` | `f109452f4bd4caba17df7c207683308a68f69a27` | `f109452f4bd4caba17df7c207683308a68f69a27` |

The revert commit `6c6cef38`&#39;s **whole-repository** tree object is
`0790a57545ade4fccade035df88b3f816febc973`, identical to `4ac4ce2a`&#39;s —
i.e. the reversion restored every path in the repository, not only the
executable ones, before the governance record was added on top.

Static validation at the final head: 7 manifests parse, 49 XML files
well-formed, `compileall` clean over `addons/`, `tools/run_connector_suite.sh`
passes `bash -n`, `connector-tests.yml` parses. Worktree clean, zero
untracked files, no database or artifact residue in the tracked tree.

## Restored evidence baseline

The executable tree is byte-for-byte the tree of
`ee23c966a0b214c7974abbade4b384f251c4940f`, the previously accepted
Odoo.sh-tested executable ancestor. **No new runtime evidence is claimed by
this reversion, and none is required — no new executable tree was
produced.** The Odoo.sh standard-runtime-pass disposition recorded for
`ee23c966` ([comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435))
continues to describe the current executable tree.

The rejected batch&#39;s green local regression results (2069 / 2069 / 39) and
its green GitHub Actions runs **remain historical evidence for the rejected
subset only**. They are not evidence for the restored tree, and they never
established the mandatory requirements the batch failed. **No Odoo.sh,
Shopify, UAT or acceptance claim applies to `69562d34…` — none was ever
made, and none may be inferred.**

## Forward disposition and remaining next gate

- **Dependency-uninstall survival is deferred from the MVP** by the control
  room. No MVP work depends on it.
- **The next implementation addresses UAT-critical onboarding separately**,
  as its own bounded task. This session did not begin it.
- **Remaining next gate:** return to the control room for that bounded
  UAT-critical onboarding task. The Wave 5 gate state at this head is the
  `ee23c966` executable baseline plus documentation; the previously recorded
  next gates for that baseline (independent review of the correction delta,
  then exact-head Odoo.sh validation, then controlled live-Shopify
  validation, then UAT, then the release decision) are unchanged by this
  reversion.

## Not done in this session

**No approval · no ready-mark · no merge · no issue closed · no Shopify
contact of any kind · no credential use · no live campaign · no Odoo.sh run
· no replacement onboarding implementation begun · no architecture decision
created or accepted.** PR #204 remains **draft, open and unmerged**. Issues
#185, #186, #197 and #200 remain open.

**Execution deviation, recorded not silently reconciled.** This session&#39;s
harness designated branch `claude/revert-wave-5-lifecycle-8d62z1` while its
instruction authorised pushing **only** `fable/wave-5-completion`. The
instruction was followed — the identity invariant (local head = remote head
= PR head) is unsatisfiable on any other branch, and this PR could not
otherwise be updated. Same reasoning, same choice, as the two prior cycles
recorded further down this body.

---

&gt; **Everything below this line is the historical record of the rejected
&gt; experiment and the cycles that preceded it. It is retained verbatim and
&gt; unrewritten. Its head-SHA, scope, evidence and &#34;recommended next gate&#34;
&gt; statements are superseded by the section above.**

---

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

| Item | Value |
| --- | --- |
| Head SHA | `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor, 0 behind) |
| Commits · changed paths vs base | **82** · **361 changed paths** |
| **Wave 5 pre-campaign onboarding / single-package-lifecycle commits added after `4ac4ce2a5144907673fea1b753764823857916aa`** | **5 implementation commits** (`6e1db1d`, `6e622e1`, `b44ccce`, `ffb769c`, `a208a56`) + **2 documentation-only evidence/lessons commits** (`105314d`, `69562d3`) · **35 changed paths total** — fast-forward, no amend, rebase, squash or force-push. **The 5 implementation commits are an `addons/**` batch, not documentation-only**; the 2 trailing commits have **zero executable-tree delta** (`git diff --name-only 105314d..69562d3` touches only `CHATGPT.md`) — see the new section below |
| Correction commits added after `ef67c8035e7ee2f6cafd564fcbf2e12153a7e817` | **2 commits** · **17 changed paths** — fast-forward, no amend, rebase, squash or force-push; the five prior commits are untouched |
| Provisioning-package correction commits added after `ee23c966a0b214c7974abbade4b384f251c4940f` | **2 commits** (`dd8ab135f494b5c2085662ef68e920fd1339e21e`, `4ac4ce2a5144907673fea1b753764823857916aa`) · **3 changed paths**, identical set both times (`docs/05-qa/shopify-live-validation-package.md`, `docs/05-qa/val-b2-closure-plan.md`, `docs/07-implementation-plan/wave-5-completion-gate-state.md`) — **documentation-only**, fast-forward, no amend, rebase, squash or force-push; **zero delta** under `addons/`, `tools/`, `.github/` |
| Accepted runtime-tested executable head | `ee23c966a0b214c7974abbade4b384f251c4940f` — the Odoo.sh standard-runtime-pass disposition ([PR comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435)) applies to that SHA. **`a208a56` is a later, materially different executable head** (the new `addons/shopify_connector` package family) and is **not** independently Odoo.sh-validated; the current head `69562d3` inherits that exact same executable tree unchanged (only `CHATGPT.md` differs) — see the new section below for what evidence the executable change does have |
| Evidence class | For the executable tree at `a208a56` (unchanged through `69562d3`, this cycle): **source inspection + disposable-database module-lifecycle harness (7/7 stages, real Odoo installs/uninstalls) + local automated regression suite (2069 fresh / 2069 warm / 39 non-standard, 0 failed/0 errors, up from the 2040/2040/39 baseline)**. No Odoo.sh runtime, no independent review, no live-Shopify contact, no UAT. For the executable code at `ee23c966`: source inspection + local automated tests + local rendered browser evidence, as previously recorded |
| Shopify | **none** — no store, credential, request, mutation or webhook, in any commit on this PR |

## Wave 5 pre-campaign onboarding, location mapping, single-package lifecycle, and dependency-recovery — 2026-07-29

&gt; **Status: implementing-session record. NOT an acceptance, NOT a review, NOT a runtime or UAT claim. This session has not reviewed, accepted, ready-marked, or merged its own work — per CLAUDE.md §13/DEC-040/DEC-041 it may not.**

Five implementation commits (`6e1db1d` → `a208a56`) plus two documentation-only evidence/lessons commits (`105314d`, `69562d3`), fast-forward only from `4ac4ce2a5144907673fea1b753764823857916aa`, no amend/rebase/squash/force-push. The two trailing commits have zero executable-tree delta from `a208a56` — `69562d3` only adds two CHATGPT.md lessons about this cycle&#39;s own evidence-integrity process errors (see below) — so every evidence figure in this section, produced at exact head `a208a562f1cf9249c9f7e4f0a30e75131a477058`, applies unchanged to the current head `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`.

**What this cycle implements, in one sentence:** a single customer-facing `Shopify Connector` application (`addons/shopify_connector`) that installs the complete six-module technical suite in one action, survives a standard Odoo-dependency loss by entering a durable, administrator-gated `dependency_paused` state (never partial operation, never auto-resume), refuses any direct uninstall of its own technical components (including a crafted co-selection), and correctly cascades its own removal to the whole suite — via Odoo&#39;s own native `downstream_dependencies()` mechanism, no custom uninstall code — when deliberately uninstalled.

**The crux design move, proven from the pinned Odoo 19 source, not assumed:** the six technical modules now depend on the new umbrella (`shopify_connector` depends only on `base`/`web`), the *reverse* of an ordinary umbrella. This is what makes package survival possible at all: `ir.module.module.downstream_dependencies()` is a transitive, unconditional cascade rooted at whatever lost its dependency, so a package that itself depended on the technical modules would be swept away the instant any one of them lost its own standard Odoo dependency. Full derivation, the manifest-graph tables, and the `post_init_hook` one-action-install proof: [`docs/03-architecture/single-package-lifecycle.md`](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/03-architecture/single-package-lifecycle.md). Decision record: [`DEC-042`](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/04-decisions/DEC-042-single-package-lifecycle.md) (status: Proposed, not self-accepted).

**Global gate instrumentation:** `shopify.connector.package.assert_healthy()` is called at every job-admission/dispatch/transport/store-lifecycle boundary already identified as load-bearing in `shopify_connector_core` (`shopify_connector_job_enqueue.py`, `shopify_connector_job_dispatch.py`, `shopify_connector_api_client.py::execute`/`execute_business`, `shopify_connector_store.py`&#39;s connection-probe/activate/reconnect paths) — proven to fire *before* any transport call is reached, not merely alongside it, via a mock that fails the test if the transport method is ever called.

**Also delivered, narrower in scope — location-mapping hardening (`shopify_connector_inventory`):** `create_or_update_location_mapping` now refuses an arbitrary, foreign-store, or inactive Shopify Location GID (it must correspond to a currently-active, this-store cached `shopify.connector.location` row) and populates `shopify_location_name_snapshot` from that validated cached row rather than from caller input, on both the create and idempotent-update paths.

### Disposable-database proof (Section 6/24C) — exact head `a208a562f1cf9249c9f7e4f0a30e75131a477058`

`tools/shopify_connector_package_lifecycle_check.sh` — a standalone harness driving real `odoo-bin`/`odoo-bin shell` module operations (never `TransactionCase`, since Odoo&#39;s own `_button_immediate_function` forbids module operations inside a test transaction). All 7 stages passed:

| # | Stage | Result |
| --- | --- | --- |
| 1 | Fresh one-action install (`-i shopify_connector` installs the whole suite + every standard app it needs) | **PASS** |
| 2 | Warm adoption of a pre-Wave-5 database (six modules under the OLD manifests, `-u`&#39;d to current code) | **PASS** |
| 3 | Standard-dependency loss (`stock`) + package survival, correctly detected as `dependency_paused` | **PASS** |
| 4 | Restore/explicit resume — three-stage, never automatic (recheck → restore → confirm) | **PASS** |
| 5 | Direct component-uninstall refusal, including a crafted co-selection with a legitimate standard app | **PASS** |
| 6 | Complete package uninstall cascades the whole suite via Odoo&#39;s own mechanism | **PASS** |
| 7 | Wider transitive cascade (`product`, bringing down `sale`/`stock`/`account`/all five domain modules) | **PASS** |

Real Odoo module operations throughout every stage; zero Shopify contact.

### Regression qualification (Section 24/25) — definitive final pass, exact head, clean worktree

`tools/run_connector_suite.sh`, `source_head_verified: true` at `a208a562f1cf9249c9f7e4f0a30e75131a477058`, `connector_worktree_dirty: false`, Odoo pin `30bde9ff758834a4912c5ae55843d3a7dad849f1` verified, PostgreSQL 16.13 / Python 3.12.3, zero Shopify operations in any pass.

| Pass | Result |
| --- | --- |
| **Fresh install** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Warm upgrade** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Non-standard tags** | **0 failed, 0 errors of 39 tests** |

Tours: 21 required, 21 executed, 21 success markers, each standard pass. HOOT suites: all three executed and verified (dashboard, export diff, setup wizard). Skip detection: only the sanctioned skip (`TestMutationRecovery.test_real_process_death_harness`). Standard-suite count moved by exactly the tests this cycle added: **2040 → 2069 (+29)** — 12 in `test_package_lifecycle.py`, 5 in `test_uninstall_guard.py`, 9 in `test_package_pause_gates.py`, 3 in `test_location_mapping.py`; none silently dropped. Non-standard stayed at **39**.

**Process error disclosed rather than hidden:** a first attempt at this run was invalidated mid-run because source files were edited while an earlier pass was still executing against a different code state — caught by this session, discarded, and re-run cleanly only after every edit was committed. A second attempt was flagged `connector_worktree_dirty: true` because a leftover artifact directory from the discarded run had been moved to an untracked path inside the repository; relocated outside the repository and the run repeated cleanly, producing the numbers above. Both mistakes are now logged as their own lessons ([CHATGPT.md §18.28](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/CHATGPT.md)). Full account: [`wave-5-completion-gate-state.md` §5e.8](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/07-implementation-plan/wave-5-completion-gate-state.md).

### HEADLINE finding — TD-019 (High), from this cycle&#39;s own adversarial self-review, disclosed prominently, not narrowed

**Domain-owned data does not survive a standard-dependency cascade.** Only the package controller&#39;s own state (`shopify.connector.package`, which lives in the never-cascaded `shopify_connector` module) survives. Shopify location mappings, product/customer/order bindings, inventory-level bindings, their jobs/job logs, and mutation-attempt evidence all live in the five domain technical modules, and Odoo&#39;s own `module_uninstall()` physically drops those modules&#39; tables the moment a standard-dependency loss cascades them away.

**Verified empirically, not merely reasoned about:** a `shopify.connector.location.mapping` row was created, `stock` was uninstalled (cascading `shopify_connector_inventory` away, exactly as designed), and `SELECT to_regclass(&#39;shopify_connector_location_mapping&#39;)` against the same database returned `NULL` immediately afterward — the table itself no longer exists. Restoring the suite recreates it empty; it cannot restore the deleted rows.

**Why this was not fixed in this cycle:** the two proven-safe patterns (move the data&#39;s ownership into a surviving module, or build a durable versioned snapshot/restore mechanism) both require materially altering the five domain modules&#39; own data ownership/semantics — outside this task&#39;s allowed-file scope for those modules, and a control-room design decision this session may not make unilaterally. Logged as **TD-019 (High)** in the technical-debt register, with the full empirical proof in `single-package-lifecycle.md` §6a and the consequence recorded in DEC-042&#39;s &#34;Negative / trade-offs&#34; section.

### Scoped out of this cycle, explicitly, and logged rather than silently narrowed

- **TD-017** — no dedicated per-store resume-selection UI; the package-level gate is a global circuit breaker layered on the existing per-store readiness/activation machinery (`shopify_connector_core`, unchanged by this cycle).
- **TD-018** — `action_restore_suite` reinstalls missing components but does not also force-upgrade already-installed ones; left to Odoo&#39;s own ordinary Apps &#34;Upgrade&#34; action.
- The full location-mapping setup flow/workspace (Sections 18–19 of the governing task) beyond the GID-validation hardening above — the setup wizard, remap-with-audited-reason flow, and per-location readiness workspace are not built in this cycle.
- The full 29-module standard-dependency closure is not individually cascade-tested; the harness proves the three representative cascades the task specifies (`stock`, `product`, complete package uninstall).
- No browser/viewport evidence was captured for the new package status view (a minimal Odoo-native form with a statusbar and three buttons).

### Not claimed

**No Odoo.sh runtime · no independent review of this head · no live-Shopify contact of any kind · no UAT · no acceptance, ready-mark, or merge.** The implementation worker has not reviewed, accepted, or approved its own work, and per CLAUDE.md §13/DEC-040/DEC-041 may not. PR #204 remains draft, unapproved and unmerged.

### Recommended next gate

A fresh, independent Claude review of this exact head (`69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`) — a separate top-level session or a fresh subagent invocation that adversarially re-verifies rather than summarizes, per DEC-040 — covering in particular: the reverse-dependency architecture and its disposable-database proof, the REPEATABLE READ fix in `_commit_via_side_cursor`/`_apply_detected_state`, the uninstall-guard&#39;s crafted-co-selection refusal, the location-mapping GID-validation hardening, and above all a control-room ruling on TD-019 (accept the domain-data-loss gap as MVP behaviour, or authorize a Pattern A/B follow-up). Then, if accepted, a separate closure session before any ready-mark or merge — never this one.

---

## Provisioning-package correction — 2026-07-28 (post-runtime-disposition)

&gt; **Status: documentation-only correction record. NOT an acceptance, NOT a
&gt; review, NOT a new runtime or UAT claim, NOT provisioning or campaign
&gt; execution.**

After the control room recorded the Odoo.sh standard-runtime-pass disposition
for `ee23c966a0b214c7974abbade4b384f251c4940f`
([PR comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435))
and a provisioning-readiness checklist on issue #200
([comment `5103684847`](https://github.com/AdamsOdoo/Adams/issues/200#issuecomment-5103684847)),
a session-independent source audit found that checklist&#39;s credential-scope
section — carried forward from `docs/05-qa/shopify-live-validation-package.md`
§2.3 — was internally contradictory: it required execution of the M-EXP-*
product/media mutation cases while its own scope table excluded
`write_products` and `write_files` as forbidden. Two documentation-only
commits corrected this and three further consistency gaps found while
finalizing the correction:

1. **`dd8ab135f494b5c2085662ef68e920fd1339e21e`** — re-derived the
   consolidated Shopify scope set directly from the frozen source
   (`shopify_connector_readiness_check.py` in core and fulfillment,
   `shopify_connector_inventory_service.py`,
   `shopify_connector_product_export_seams.py`) and current official Shopify
   2026-07 GraphQL Admin API documentation (`productUpdate`/`productSet`/
   `productVariantsBulkUpdate` → `write_products`; `fileUpdate` → `write_files`
   or `write_themes`; `inventorySetQuantities`/`inventoryActivate` →
   `write_inventory`): the six-scope `REQUIRED_MVP_SCOPES` read baseline
   (`read_products`, `read_customers`, `read_orders`, `read_inventory`,
   `read_locations`, `read_merchant_managed_fulfillment_orders`) plus
   `write_inventory`, `write_merchant_managed_fulfillment_orders`,
   `write_products` and `write_files` — ten scopes total. `write_themes`
   stays explicitly forbidden. `read_assigned_fulfillment_orders` /
   `write_assigned_fulfillment_orders` were removed — neither name appears
   anywhere in `addons/`, and assigned-fulfillment-order scopes govern a
   different mechanism (fulfillment-service-app assignment) from the
   merchant-managed `FulfillmentOrder` model this connector uses exclusively.
   Also corrected: `val-b2-closure-plan.md` §4 still named the pre-TD-002/
   D-014-2 scope `read_fulfillments` instead of the shipped check&#39;s actual
   `read_merchant_managed_fulfillment_orders`; and §7 classified a 24-hour
   client-credentials-only outcome as an unqualified FAIL, contradicting §8&#39;s
   existing PARTIAL/QUALIFIED framing — §7 now separates PASS / PARTIAL /
   FAIL as three distinct outcomes.
2. **`4ac4ce2a5144907673fea1b753764823857916aa`** — a control-room addendum
   found three further documentation-consistency gaps and authorized this one
   additional additive commit (never amending `dd8ab135`): (a)
   `shopify-live-validation-package.md` §1&#39;s entry criteria E2/E3 conflated
   &#34;the connector SHA under test&#34; with the Odoo.sh-validated executable head
   via a single `git rev-parse HEAD` — corrected to record the current
   campaign/package head and the accepted runtime-tested executable head
   separately, with a zero-executable-delta proof requirement and a
   fresh-qualification trigger if that delta is ever non-zero; (b)
   `val-b2-closure-plan.md` §10 point 5 read &#34;if VAL-B2 fails (including the
   qualified/partial case in §8),&#34; folding PARTIAL back into FAIL — corrected
   so FAIL and PARTIAL are named as distinct, independently-escalated
   outcomes; (c) `wave-5-completion-gate-state.md` §5e.6 had pre-claimed the
   PR #204 and issue #200 correction comments as &#34;posted this session&#34; before
   they were posted — corrected to accurate sequencing.

**Zero executable-tree delta, both commits combined:**
`git diff --name-only ee23c966a0b214c7974abbade4b384f251c4940f..4ac4ce2a5144907673fea1b753764823857916aa -- addons tools .github`
is empty. Only the three documentation paths above changed, identically in
both commits. **`EXECUTABLE TREE UNCHANGED FROM THE ACCEPTED ODOO.SH
STANDARD-RUNTIME HEAD.`** GitHub Actions ran green at this final head:
run [`30359073374`](https://github.com/AdamsOdoo/Adams/actions/runs/30359073374)
(`push`) and run [`30359078999`](https://github.com/AdamsOdoo/Adams/actions/runs/30359078999)
(`pull_request`), both `completed`/`success`, head SHA
`4ac4ce2a5144907673fea1b753764823857916aa` — supporting evidence only
(DEC-041 D8), not a new Odoo.sh claim; none was made or required, since a
zero-executable-delta descendant inherits the disposition of the executable
head it descends from.

**No Shopify resource was provisioned or contacted.** Issues #185, #186,
#197 and #200 remain open. This PR remains draft, unapproved and unmerged.
Full record: PR comment `CONTROL-ROOM PROVISIONING-PACKAGE CORRECTION` and
issue #200 comment
`AUTHORITATIVE CORRECTION TO PROVISIONING READINESS COMMENT 5103684847`.

---

## The remainder of this description is archived in the repository

GitHub&#39;s pull-request body limit is 65,536 characters, and this description
plus the section at the top comes to roughly 88,000. Rather than let any of
the historical record fall off the end of an edit, **the complete pre-batch
body — verbatim, unedited — is committed at
[`docs/07-implementation-plan/pr-204-body-archive-2026-07-29.md`](https://github.com/AdamsOdoo/Adams/blob/50b770a315b53f0c05f0b8867bb801d75c6476ef/docs/07-implementation-plan/pr-204-body-archive-2026-07-29.md)**
(commit `50b770a`, documentation only). GitHub&#39;s own body edit history also
retains the previous version.

Nothing above this line was shortened: the bounded-onboarding section, the
complete control-room rejection and reversion record, and the two most recent
superseded cycle records are all present in full. The sections that live only
in the archive are the older superseded record:

- Correction record — independent review `5100097485` (2026-07-28)
- Commits after `98334c7a`
- Correction A — TD-015, one resolvable review and only one
- Correction B — S1, the 11-step guided setup wizard
- Correction C — SEC-3 delta
- Correction D — present-tense trackers
- Three defects found while doing the above, and fixed here
- Retained limitations — NOT resolved
- Not claimed
- Execution deviations recorded rather than reconciled silently
- Recommended next gate (superseded by the 2026-07-29 cycle above)

