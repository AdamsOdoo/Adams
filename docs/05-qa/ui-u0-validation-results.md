# U0 — First Usable Shopify Connector Operator UI — Validation Results

> **Status: implementation candidate — Stage R1 Odoo.sh runtime campaign EXECUTED
> on the corrected working tree (`EXECUTED — PASS — ODOO.SH CONTAINER,
> PRE-REBUILD`); a Stage R2 correction is now IMPLEMENTED — EXACT-SHA ODOO.SH
> VERIFICATION PENDING; a corrected-SHA rebuild remains.** The original
> `RUNTIME PENDING` claims below are superseded for everything Stage R1 actually
> ran — see **§1a**. Browser execution (tours + HOOT) and absolute-timing budgets
> remain pending Stage R2 (container thread limit; §1a).
>
> **Stage R2 correction (2026-07-22) — see §12.** The independent review of the
> exact Stage R1 head `0fa512d2ecec028f6e6bc4198de441c9f50224c1` (PR #192
> comment `5049668193`) returned **REVISE**: one confirmed P1
> (`action_mark_reconnect_needed` lacked the Administrator boundary) plus five
> accepted test/evidence corrections. The control room accepted that verdict
> (comment `5049734472`). This session applied the one authorized consolidated
> correction. **No final independent `ACCEPT` exists yet** for this PR; §12
> below is the accurate, current review-status record — do not rely on
> anything below it that predates this note.
>
> This document records the honest evidence for the U0 operator-UI batch on
> branch `claude/u0-operator-ui-foundation`. It follows the program's
> established evidence-classification discipline (see PR #189 for the same
> `IMPLEMENTED — RUNTIME PENDING` pattern used when no Odoo runtime exists in
> the build workspace).

- **Batch:** U0 — first usable operator UI (navigation, dashboard, stores,
  Sync Center, Error & Review Center, logs, mutation evidence, safe actions).
- **Base identity:** `mvp/program-integration@1e2e5c258922b93e11f6bf6f5d4828517d12c917`
  (authoritative U0 base amendment; PR #191 merge `ba4ccc2` + tracker-only
  closure commit above it).
- **Builder authority:** DEC-039 + DEC-040 (Claude default builder; no
  self-review / self-accept / self-merge; independent review is the gate).
- **Reviewer model:** DEC-040 independent-review mechanism (fresh memoryless
  reviewer). This session does **not** self-accept, ready-mark, or merge.

---

## 1. Evidence classification key

| Class | Meaning |
| --- | --- |
| `EXECUTED — PASS` | Ran in this workspace and passed. |
| `STATIC — PASS` | Verified by static analysis / parsing / source inspection in this workspace (no Odoo runtime). |
| `RUNTIME PENDING` | Correctly implemented and self-consistent, but requires a genuine Odoo runtime (Odoo.sh) to execute; not run here. |
| `NOT PROVEN` | Not executed and not fabricated. |

**The build workspace has no Odoo runtime and no Odoo.sh access** (`odoo` is
not importable, no `odoo`/`odoo-bin` on PATH, no `/opt/odoo`). Consequently the
mandatory Odoo.sh runtime campaign (§24 of the U0 prompt), the driven browser
walkthrough + screenshots (§23), and actual execution of the Python / HOOT /
tour suites are `RUNTIME PENDING`. No static-only result is presented as a
runtime pass.

---

## 1a. Stage R1 Odoo.sh runtime campaign — `EXECUTED — PASS — ODOO.SH CONTAINER, PRE-REBUILD`

> This section supersedes the `RUNTIME PENDING` rows below for everything it
> ran. Evidence is genuine Odoo 19 runtime inside the Odoo.sh dev container, on
> the **corrected working tree**. It is **pre-rebuild**: the corrected SHA
> requires a fresh Odoo.sh build for exact-build (Stage R2) confirmation.

**Environment / identity.** Odoo.sh dev container. Odoo **19.0**; PostgreSQL
**16.14**. Branch `claude/u0-operator-ui-foundation`, tip = HEAD =
`f80437932cea31190d8cd45ca10f18f4c8245b75` (exact candidate SHA; clean tree at
campaign start). Build **35284077** / DB
`adamsmen-claude-u0-operator-ui-foundation-35284077` — the prompt named build
`35282748`, but the container had been rebuilt from the **same branch at the
same SHA**; the SHA (not the build number) is the candidate freeze, so evidence
is valid. Modules present: `shopify_connector_core` (19.0.1.10.0),
`shopify_connector_product` (19.0.2.1.2), `shopify_connector_sale` (19.0.2.0.0),
`shopify_connector_inventory` (19.0.1.0.0). No Wave-4 fulfillment addon present.
No credential/secret printed.

**Initial install at the exact candidate SHA — FAILED (owned P0, install-blocking).**
`odoo-bin -i` of the four modules failed to load the registry at
`f804379…` with `odoo.tools.convert.ParseError` — Odoo 19 tightened view
validation and five U0 search/form-view constructs are now invalid:

| # | File | Construct | Odoo 19 rule |
| --- | --- | --- | --- |
| 1–4 | store / job / job_log / mutation_attempt search views | `<group expand="0" string="Group By">` | search `<group>` (shared `common.rng`) allows neither `expand` nor `string`; the current idiom is a plain `<group>` wrapping the group-by `<filter>`s |
| 5 | job form view stat button | `context="{'search_default_job_id': active_id}"` | the field-accessibility validator treats `active_id` as a non-existent field on `shopify.connector.job` (Access-Rights-Inconsistency); the current idiom uses `id` |

Fix (owned; `views/*`): plain `<group>` in all four search views + `active_id`→`id`
in the job stat button. After the fix the full stack installs cleanly (**79
modules loaded, registry loaded in 66 s**) — registry, models, U0 XML views,
menus/actions, ACLs, Owl/SCSS/tour/HOOT asset bundles all load; no missing
model/field/external-ID, no duplicate XML ID, no invalid domain/modifier.

**Known Test Connection P1 — reproduced then fixed (mocked transport; no real Shopify call).**
`shopify.connector.store.action_test_connection()` invoked by
Auditor / Operator / Reviewer / plain user (runtime, `registry_enter_test_mode`,
`_send` mocked):

| tree | exc | transport | Δjob | Δlog | store | cred |
| --- | --- | --- | --- | --- | --- | --- |
| **UNFIXED** (`store.py` reverted via `git stash`) | **NONE — not denied** | 0¹ | **+1** | **+2** | unchanged | unchanged |
| **FIXED** (boundary guard) | **AccessError** | 0 | 0 | 0 | unchanged | unchanged |

¹ In `registry_enter_test_mode` the shared `_admit_lifecycle` side-cursor
self-supersedes before `_send`, so transport shows 0 in-test; the code path
proves an admitted probe reaches `_send_lifecycle` (and the sanctioned
`_get_access_token` `sudo()` materialises the token) **before** the late
non-sudo store write — i.e. before any ACL bite. The runtime-proven harm on the
unfixed tree is: **an unauthorized read-only role is not denied at all and
creates a `core_test_connection` job + two `job.log` rows** (`exc=NONE`, Δjob=1,
Δlog=2). The corrected-contract regression test
(`test_test_connection_denies_non_admin_before_side_effects`) **FAILS on the
unfixed tree** (the recorded proof) and **passes on the fixed tree**.

**Correction — one consolidated Administrator boundary (owned; `store.py`).**
New `_ensure_connector_admin_boundary()` enforces the **existing**
`group_shopify_connector_admin` (no new role/group) at the top of the four
public store actions — `action_test_connection`, `action_activate`,
`action_disconnect`, `action_reconnect` — **before** any job/log creation,
credential read, Shopify transport, or store-row lock/write. Mirrors the guard
already present in `action_force_disconnect`. The Odoo framework superuser
(`env.su`: crons, the disconnect controller, the test harness) is exempt as
everywhere in Odoo; a real RPC caller can never be `su`, so this is a strict
**tightening** — nothing is loosened.

**Analogous public-action audit (§10).** `action_reconnect` shares
`_run_connection_probe` → same job/log/credential/transport-before-denial
defect. `action_disconnect`'s already-`disconnecting` **audited-no-op** branch
creates a `sudo()` audit job with **no** denial at all. `action_activate`
acquires the store-row lifecycle lock before denial. All three are closed by
the uniform boundary guard. No lifecycle behaviour is redesigned; Administrator
outcomes are unchanged.

**Corrected-tree U0 test campaign — `EXECUTED — PASS`.** 63 post-tests
(`TestTestConnection` [post_install; see below] + all seven
`shopify_connector_u0` classes except the browser tour): **0 failed, 0 errors**.
The four-role Administrator-only direct-call matrix
(`test_store_lifecycle_actions_admin_only_direct_call`) passes.

**U0 defects surfaced by genuine runtime and fixed (owned; test-level, no
production access-control loosened).**

| id | test | root cause | fix |
| --- | --- | --- | --- |
| RC1 | `test_ui_dashboard` (12), `test_ui_performance` (4), `test_ui_installation` (1) | ran the connector-users-only dashboard aggregate as the **framework superuser** (not a connector-group member) → `AccessError` | run the aggregate as a connector **Auditor** (the realistic caller) |
| RC2 | `test_ui_installation.test_menus_resolve_and_are_gated` | `ir.ui.menu.groups_id` removed in Odoo 19 | → `group_ids` |
| RC3 | `test_ui_source_guards.test_no_controller_or_webhook_or_oauth` | the guard inspected **itself** and matched the literal `'http.Controller'` it searches for | skip the guard's own file |
| RC6 | `test_ui_actions.test_mutation_resolution_applies` | fixture used a non-existent `mutation_domain='inventory'` (registry has `inventory_set_quantities` / `inventory_activate` / `mutation_dispatch_selftest`) | use the always-registered `mutation_dispatch_selftest` |

`test_test_connection.py` was retagged `post_install` (see the environmental
note) to run the added security regression; its eight pre-existing assertions
are unchanged and pass.

**Core regression (`shopify_connector_core`) — `EXECUTED`.** 368 tests:
**0 failed, 11 errors** — all 11 are the **environmental** `autopost_bills`
`setUpClass` blocker (below), never a connector-logic failure. The genuine
cross-connection lifecycle/concurrency classes that ran passed (no
`can't start new thread`). **No regression from the correction** — consistent
with the `env.su` exemption (every superuser-driven lifecycle test passes the
guard unchanged). Product / Sale / Inventory install cleanly (fresh-install
smoke ✓, full 4-module registry load); their own at_install user-creating
suites share the same environmental blocker.

**Leak / redaction scan — PASS.** Odoo logs + test output contain no real
`shpat_` token (only the dummy `shpat_DUMMYDUMMYDUMMY…`), no
`Authorization`/`X-Shopify-Access-Token` header, no secret/password, and no
customer PII (only test-domain `@example.com` addresses). The P1 regression
also asserts no token persists to store/job/log.

**Environmental blockers (evidence-backed; not owned; pending Stage R2).**

- **`autopost_bills` at_install setUpClass NOT-NULL.** `account`'s
  `res.partner.autopost_bills` (required, default `'ask'`) is NOT-NULL in the
  DB. `shopify_connector_core` loads **before** `account`, so an at_install test
  that creates a `res.users` in `setUpClass` inserts a partner while the field
  is not yet on the in-registry model → NOT-NULL violation. Proven environmental:
  a normal `odoo-bin shell` creates users/partners fine (default applied); only
  the at_install phase is affected. Not introduced by U0 or this correction;
  production is unaffected. It blocks 11 core at_install user-creating classes
  (connection_lifecycle, credential_access/service, job_actions,
  job_log_system_append, mutation_attempt/reconciliation/retention/security,
  readiness_slot_closure, security_hardening). Post_install U0 tests are
  unaffected (account is fully loaded by then), which is why
  `test_test_connection` was retagged `post_install`.
- **Browser tour + HOOT — container thread limit.** With HTTP enabled, Chrome
  141 launches and connects via the devtools websocket, but
  `HttpCase.browser_js`/`start_tour` fails with
  `RuntimeError: can't start new thread` — a container process/thread cap, not a
  connector defect. Server-side Python tests are unaffected. Browser execution
  (registered tours + the HOOT JS suite) and absolute browser render/timing
  budgets (PB-1/2/3/7/8/12 absolutes) are **pending Stage R2** on the
  corrected-SHA build. Asset *registration* is proven by the clean install.

**Not exact-build proof.** Every result above is on the corrected working tree
inside the existing build; it is genuine runtime but **pre-rebuild**. Final
exact-build confirmation, browser tours/HOOT, upgrade/uninstall-reinstall
zero-residue, and RD-1/RD-2 absolute timings belong to Stage R2 on the
corrected-SHA Odoo.sh build.

---

## 2. What was built (scope delivered)

- **Navigation** — one root app menu `Shopify Connector` gated to the connector
  Auditor group, with five first-level destinations (Dashboard, Stores, Sync
  Center, Error & Review Center, Logs) and a nested Mutation Evidence entry
  under Error & Review Center. No empty placeholders for later waves.
- **Dashboard** — one bounded Owl client action over a read-only aggregate
  service (`shopify.connector.ui.dashboard`, an `AbstractModel`). Ranked
  hierarchy: lead answer band → ≤3 exceptions → secondary chips → recent
  activity → optional severable 7-day sparkline. Five real states
  (loading/empty/healthy/warning/degraded/manual-review) driven by one
  severity model.
- **Stores** — native list/form/search over `shopify.connector.store`,
  read-only for all roles; Administrator-only lifecycle/test buttons targeting
  existing sanctioned methods; credential value never displayed; no encryption
  claim.
- **Sync Center** — server-paginated native job list/form/search with saved
  filters and group-bys over the real state/error/source vocabularies.
- **Error & Manual Review Center** — a dedicated action over the job model
  defaulting to attention-required states; manual review distinguished from
  technical failure by icon/owner/copy, not colour.
- **Logs & mutation evidence** — read-only native views; raw JSON evidence
  fields never displayed; payload snapshot confined to a labelled redacted
  audit-evidence section, never in a list.
- **Safe actions** — retry (`action_manual_retry`), cancel (transient wizard →
  `action_cancel(reason)`), review resolve (`action_resolve_manual_review`),
  mutation resolution (admin-only transient wizard →
  `action_resolve_mutation_attempt(disposition, reason)`), and store
  lifecycle/test buttons. No UI-owned business logic.

Files: 3 modified + 15 new production; 1 modified + 8 new test; this doc + the
copy deck + focused tracker updates. All 27 code/test changes are within the
§8–§9 allowlist (proof in §4).

---

## 3. Architecture decisions of record (this batch)

1. **Dashboard aggregate service = `AbstractModel`, no ACL row.** Chosen so the
   only ACL additions are the two transient wizards (§19). The service exposes
   one public `@api.model get_dashboard_data`, called from the Owl action via
   `orm.call`. It gates on the Auditor group at the data layer for defence in
   depth. *Runtime verification item:* confirm RPC dispatch to an
   `AbstractModel` public method under Odoo 19 (expected to work; standard
   dashboard pattern). Fallback if ever needed: a thin authorised model — not
   used here to keep ACL additions to the wizards only.
2. **Navigation menu = the prompt's five U0 destinations, not the eventual
   seven-entry map.** The accepted `screen-inventory-and-navigation-map.md`
   describes a seven-entry *end-state* menu (Dashboard, Sync Center, Error
   Center, Catalog & Matching, Inventory, Fulfillment, Configuration→Store
   Settings). U0's prompt (§12) deliberately scopes a five-item first level and
   forbids empty placeholders for later waves. This is an intentional,
   self-consistent U0 subset, recorded in `architecture-review-log.md`. Stores
   is surfaced top-level for U0 (rather than under Configuration, which is not
   built); Logs is surfaced top-level (and also reachable from the job form).
   Reconcile with the seven-entry map when U1–U3 land.
3. **Mutation-evidence indicator in the job list uses the existing
   `mutation_attempt_id`.** The job model cannot be edited (not in the
   allowlist), so no computed `has_mutation_evidence` field was added. Button
   visibility hides generic retry/cancel when `mutation_attempt_id` is set; the
   server's `_has_mutation_attempt_evidence` guard (which also covers the
   reverse `attempt.job_id` link) remains the authoritative control, so a rare
   reverse-linked job that still shows a button is refused server-side with a
   clear error. Documented as an accepted, honest UX approximation.

---

## 4. Static validation performed in this workspace — `STATIC — PASS`

| Check | Tooling | Result |
| --- | --- | --- |
| Python compiles (all models + all tests) | `python3 -m py_compile` | PASS (0 errors) |
| XML well-formedness (7 view files + Owl template) | `xml.dom.minidom` | PASS (all well-formed) |
| JS/ESM syntax (dashboard.js, tour.js, HOOT test) | `node --check` (ESM) | PASS |
| Manifest parses; `depends` includes `web`; assets bundles present | `ast` / eval | PASS |
| Allowlist conformance (all 27 code/test changes) | git-status diff vs §8–§9 | PASS (0 violations) |
| XML-ID uniqueness (29 records/menus) | regex scan | PASS (0 duplicates) |
| Cross-reference resolution (`ref=`, `%(...)d`, `action=`, `parent=`, `groups=`) | regex scan | PASS (0 unresolved) |
| Field-existence: every `<field>` in every view exists on its model | model-source grep | PASS (0 missing; `web_ribbon` is a widget) |
| ACL CSV structure (8 columns; wizard rows gated correctly) | `csv` | PASS |
| Source guards (single Owl surface; no controller; no external dep; no credential/payload read; wizards call sanctioned methods) | `test_ui_source_guards` logic, verified statically | PASS |

---

## 5. Pre-review adversarial audit — findings caught and fixed here

All fixed before freezing the candidate (no known P1/P2 deferred into a later
micro-correction):

| # | Severity | Finding | Fix |
| --- | --- | --- | --- |
| A1 | P1 (would break install) | Job views referenced a non-existent `created_at` field (the job model has no `created_at` and does not disable `_log_access`, so only `create_date` exists). | Replaced with `create_date`; verified by field-existence sweep. |
| A2 | P1 (would break asset load) | Owl template had XML comments containing `--` (illegal in XML). | Rewrote the two comments. |
| A3 | P2 (would break dashboard render) | Owl `t-if` used Python `and`; Owl compiles JS. | Changed to `&&` (XML-escaped). |
| A4 | P2 (would crash sparkline) | A placeholder line (`fields.datetime.min.__class__`) survived in `_sparkline`. | Replaced with a clean `timedelta` import + window computation. |
| A5 | Tier-3 | Brittle tour selector (`%(cancel)s`) in the operator tour. | Simplified to a `.o_form_view` presence check. |
| A6 | Governance flag (not a defect) | Prompt's five-item U0 menu diverges from the accepted seven-entry end-state map. | Implemented the prompt's U0 subset; recorded in `architecture-review-log.md` + §3.2 above. |

---

## 6. Automated test suites — authored, `RUNTIME PENDING`

All test files py-compile cleanly and encode the §22 acceptance checks. They
require an Odoo runtime to execute (Gate C):

| File | Covers | Class |
| --- | --- | --- |
| `test_ui_installation.py` | XML IDs resolve; menus gated; models registered; manifest depends web; client-action tag | RUNTIME PENDING |
| `test_ui_dashboard.py` | empty/healthy/warning/degraded/manual-review; ≤3 exceptions; count↔domain agreement; resolved-excluded; bounded activity; no sensitive data; non-connector denied | RUNTIME PENDING |
| `test_ui_visibility_matrix.py` | read surfaces per role; retry/cancel/review matrices; negative direct calls; protected-field write denied; credential read denied to non-admin | RUNTIME PENDING |
| `test_ui_actions.py` | retry valid/invalid states; mutation-evidence retry refusal; cancel reason required/recorded; wizard defers to server; mutation resolution admin-only + validation; test-connection preconditions (no Shopify call) | RUNTIME PENDING |
| `test_ui_performance.py` | bounded query count; constant-across-scale (no super-linearity); explicit limits; source-bounded reads; smoke timing | RUNTIME PENDING |
| `test_ui_tours.py` | HttpCase navigation tour | RUNTIME PENDING |
| `test_ui_source_guards.py` | single Owl surface; no controller/external dep; no credential/payload/business-write; allowlist; no out-of-scope UI | RUNTIME PENDING (logic also statically verified — §4) |
| `static/tests/shopify_connector_dashboard.test.js` (HOOT) | loading/empty/healthy/degraded/manual-review; filtered nav; failed RPC; a11y labels; chips | RUNTIME PENDING |

---

## 7. Performance budgets PB-1 … PB-12 — classification

| PB | Budget | How U0 addresses it | Class |
| --- | --- | --- | --- |
| PB-1 | Enqueue action ≤300ms server / ≤500ms UI | All action buttons are enqueue-only; no inline run | RUNTIME PENDING (measure on RD-1) |
| PB-2 | Dashboard first useful render ≤1.5s p75 RD-1 | Constant handful of indexed count queries + one bounded read | RUNTIME PENDING (smoke-bounded in test) |
| PB-3 | Dashboard interaction ≤200ms p75 | Exception click → native `doAction`; no heavy client work | RUNTIME PENDING |
| PB-4 | Sync Center load ≤1.5s p75 RD-1 | Server-paginated native list | RUNTIME PENDING |
| PB-5 | Error Center load | Same native list pattern, attention-state domain | RUNTIME PENDING |
| PB-6 | Job-log open ≤1s | Read-only native list, server-paginated | RUNTIME PENDING |
| PB-7 | No main-thread block >500ms | No blocking client work; bounded DOM | RUNTIME PENDING |
| PB-8 | Dashboard ≤1500 DOM nodes; heap stable over 10-min refresh | ≤3 exceptions, ≤5 chips, ≤8 activity rows, ≤7 spark days — bounded DOM by construction | RUNTIME PENDING (10-min soak) |
| PB-9 | Server-paginated; explicit limits; no unbounded fetch | Native lists; aggregate service uses `search_count` + one `limit`-ed read | STATIC — PASS (verified in source + `test_ui_performance`) |
| PB-10 | Aggregates only ≤500ms RD-2 | Only `search_count` + one bounded read; no full recordset | STATIC — PASS (design) / RUNTIME PENDING (timing) |
| PB-11 | No super-linear RD-1→RD-2 | Query count is **constant** regardless of volume | STATIC — PASS (asserted in `test_ui_performance`, runs at Gate C) |
| PB-12 | No poll faster than 30s; visibility-aware pause | 30s floor + `visibilitychange` pause in the client action | STATIC — PASS (verified in source) / RUNTIME PENDING (browser) |

No budget is silently waived. Absolute p75 numbers require the Odoo.sh runtime
campaign.

---

## 8. Mandatory Odoo.sh runtime campaign — to run at Gate C (§24)

The following must be executed on the exact candidate SHA before the
independent gate can be closed. This session cannot run them (no runtime):

1. Fresh install of the connector stack (core + product + sale + inventory +
   required bridges).
2. Focused U0 Python tests (`--test-tags shopify_connector_u0`).
3. Browser tours (nav tour + the three role-action tours with seeded fixtures).
4. HOOT tests (`web.assets_unit_tests`).
5. Existing core / product / sale / inventory regressions + the security matrix.
6. Upgrade from the exact base; uninstall/reinstall through the supported
   full-stack sequence; zero-residue check.
7. No-secret / no-PII leak scan.
8. RD-1 performance measurements (PB-1..PB-12); RD-2 where supported.
9. Driven browser walkthrough + the screenshot inventory (§9 below).
   No Shopify request or mutation is performed for U0 validation; use safe
   local fixtures.

Record: build ID, database, Odoo version, PostgreSQL version, exact tested SHA,
module versions, test counts, pass/fail/error counts, screenshot paths,
performance numbers, and any unavailable evidence.

---

## 9. Screenshot inventory — `RUNTIME PENDING`

To capture in the driven walkthrough: dashboard empty / healthy / error /
manual-review; store summary; Sync Center; Error Center; mutation-attempt
evidence; desktop (1366) / tablet (768) / mobile (375) dashboard; one RTL
dashboard/list example. The accepted static baseline for these already exists
under `docs/09-ui-prototype/dashboard/*.png` and is the visual reference.

---

## 10. Rollback

One normal revert of the U0 PR removes all UI XML/menus/actions/assets, the
dashboard service, the two transient wizards, the three wizard ACL rows, and
the U0 tests. No connector operational data is migrated or changed; existing
store/job/log/attempt records remain valid without the UI. The batch is one
atomic, cleanly revertable unit.

---

## 11. Remaining risk register

- **P0:** none known.
- **P1:** none known after the pre-review audit (§5) **at `526ad63`/`f804379`**.
  The independent review of the later, exact Stage R1 head `0fa512d` (PR #192
  comment `5049668193`) confirmed one new P1 — `action_mark_reconnect_needed`
  (`store.py:1237`) had no `_ensure_connector_admin_boundary()` call at all, so
  a non-admin direct ORM/RPC caller could reach a `sudo()`-backed lifecycle
  audit Job/JobLog write with zero denial on a `disconnecting`/`disconnected`
  store. **Corrected in this Stage R2 batch** (§12): the guard is now the
  first statement in that method, mirroring the other four privileged public
  store actions. `IMPLEMENTED — EXACT-SHA ODOO.SH VERIFICATION PENDING`; no
  independent re-review has run against the corrected SHA yet.
- **Material P2 / runtime-verification items:**
  - RPC dispatch to the `AbstractModel` dashboard service (§3.1) — expected to
    work; confirm at Gate C.
  - HOOT test API surface (Odoo 19 `@odoo/hoot` + `web_test_helpers`) — written
    to convention; confirm selectors/mount API at Gate C.
  - Tour selectors (`data-menu-xmlid`, `.o_sc_dashboard`, `.o_list_view`) —
    confirm against the running Odoo 19 web client.
  - Mutation-attempt test fixtures import Layer-2 create-surface constants;
    guarded with `skipTest` if the build shape differs.

---

## 12. Independent review outcome (DEC-040)

**This section's scope is layered across three distinct reviewed heads. Do
not read any one paragraph below as describing the current PR state — only
the final paragraph does.**

**Stage R1a — `526ad63` (historical, pre-runtime evidence only).** A fresh,
memoryless independent reviewer (separate `Agent` invocation, no implementer
rationale) adversarially reviewed the frozen candidate `526ad63` against all
ten acceptance dimensions and returned **VERDICT: ACCEPT** — no P0 / P1 /
material-P2 in the production code that existed **at that SHA**. Full report
posted verbatim to [PR #192](https://github.com/AdamsOdoo/Adams/pull/192)
with the reviewed SHA. The reviewer flagged three Tier-3 test/doc items,
folded in as a test/doc-only follow-up commit (production tree unchanged from
`526ad63` at that point — commit `f804379`).

**This `ACCEPT` covers only `526ad63`/`f804379`. It does NOT cover, and was
never presented as covering, the Stage R1 security/view corrections described
in §1a above** — `_ensure_connector_admin_boundary()`, the four view-validity
fixes, and the associated test changes were all written **after** this review
ran, landing at head `0fa512d2ecec028f6e6bc4198de441c9f50224c1`. That new
production code required its own fresh independent review before any
acceptance could extend to it; the paragraph below is that review.

**Stage R1b — `0fa512d` (exact Stage R1 head) — VERDICT: REVISE.** A second
fresh, memoryless independent reviewer read the exact repository checkout at
`0fa512d2ecec028f6e6bc4198de441c9f50224c1` (PR #192 comment
[`5049668193`](https://github.com/AdamsOdoo/Adams/pull/192)) — the complete
base→head diff, every changed file, the governing DECs, and the actual Odoo
19 upstream source for version-specific claims — and returned **VERDICT:
REVISE**. It confirmed the Stage R1 correction genuinely closed the four
actions it targeted, but found **one new P1**:
`shopify.connector.store.action_mark_reconnect_needed()` (`store.py:1237`)
had no `_ensure_connector_admin_boundary()` call at all, so a non-admin
direct ORM/RPC caller could reach a `sudo()`-backed lifecycle audit Job/JobLog
write with zero denial on a `disconnecting`/`disconnected` store — the exact
defect class Stage R1 claimed to have eliminated everywhere. It also
confirmed five accepted material-P2 test/evidence items (the visibility
matrix's missing side-effect-delta counters for three actions, the
mutation-resolution wizard's untested refusal path, the source guard's
hard-coded-prefix gate, the sparkline's colour-only per-day distinction, and
this very §12 being stale/self-contradictory relative to `0fa512d`). The
control room accepted this verdict verbatim in binding ruling
[`5049734472`](https://github.com/AdamsOdoo/Adams/pull/192) and authorized
exactly one consolidated correction batch.

**Stage R2 — this correction (implemented; not yet independently reviewed).**
This session applied the single authorized consolidated correction against
`0fa512d`: `_ensure_connector_admin_boundary()` is now the first statement in
`action_mark_reconnect_needed`; the visibility-matrix direct-call test now
asserts zero lifecycle-lock/transport/Job/JobLog/store/credential deltas for
all five privileged public store actions, including the two dangerous
`action_mark_reconnect_needed` branches (store already
`disconnecting`/`disconnected`); the mutation-resolution wizard's two refusal
branches are now proven through the wizard; the controller/OAuth source guard
now scans the whole production tree via the AST instead of a four-prefix
filename gate, with a synthetic-fixture rejection proof; and the sparkline
now carries a non-colour (textured) distinction plus a per-day accessible
text equivalent. **Classification: `IMPLEMENTED — EXACT-SHA ODOO.SH
VERIFICATION PENDING`.** Static validation (py_compile, AST parse, the
hardened guard run directly, allowlist conformance) passed in this workspace;
no Odoo runtime executed in this session and none is claimed. **No final
independent `ACCEPT` exists yet for this PR.** The remaining sequence is
unchanged in kind from the one recorded in the PR body: (1) one fresh
exact-SHA Odoo.sh build at the corrected head, (2) a narrow exact-build
confirmation covering the new five-action security matrix plus the existing
U0/Test Connection/sale/inventory suites, (3) one fresh independent delta
review limited to this correction, and only then (4) a separate closure
session may ready-mark/merge on `ACCEPT`. This implementing session does not
self-review, self-accept, ready-mark, or merge.
