# U0 — First Usable Shopify Connector Operator UI — Validation Results

> **Status: implementation candidate — STATIC VALIDATION GREEN, RUNTIME PENDING (Gate C / Odoo.sh).**
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
- **P1:** none known after the pre-review audit (§5).
- **Material P2 / runtime-verification items:**
  - RPC dispatch to the `AbstractModel` dashboard service (§3.1) — expected to
    work; confirm at Gate C.
  - HOOT test API surface (Odoo 19 `@odoo/hoot` + `web_test_helpers`) — written
    to convention; confirm selectors/mount API at Gate C.
  - Tour selectors (`data-menu-xmlid`, `.o_sc_dashboard`, `.o_list_view`) —
    confirm against the running Odoo 19 web client.
  - Mutation-attempt test fixtures import Layer-2 create-surface constants;
    guarded with `skipTest` if the build shape differs.
