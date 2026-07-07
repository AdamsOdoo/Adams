# Task 003 — Static / Offline Validation Sweep

## Session metadata

| Field | Value |
| --- | --- |
| Date | 2026-07-07 |
| Branch | `claude/task-003-static-validation-cszl88` (branched from `Shopify-connector` at merge commit `76cd74e7cf585e1925c3ac280bd6ca97c55df7ab`, PR #108) |
| Session type | Docs/QA-only, static and offline checks only — **no valid Shopify Admin API token was used, requested, or required** |
| Scope note | This session runs deliberately in parallel with, and does not touch, a separate concurrently-running session performing the Fable/manual OAuth token-acquisition experiment. No file in that session's scope is touched here. |
| Files inspected | `addons/shopify_connector_core/models/*.py`, `addons/shopify_connector_core/security/shopify_connector_security.xml`, `addons/shopify_connector_core/__manifest__.py`, `addons/shopify_connector_core/tests/test_api_client.py`, repository-wide file listing under `addons/`, git history for PR #101 (merge commit `e27f10e55f3504d1a9b8871a207b3d9762a3c783`) |

## Purpose and boundary

This document records what could be confirmed by **reading the repository and
its git history alone**, with no live Odoo instance, no live Shopify
connection, and no server logs available in this execution environment. It
supplements — and does not replace — the live-session record in
[`task-003-validation-results.md`](./task-003-validation-results.md) and the
step definitions in
[`task-003-manual-validation-checklist.md`](./task-003-manual-validation-checklist.md).

**This document does not claim Task 003 validation is complete, and does not
claim Task 004 is unblocked.** Static/repo-level evidence is a narrower,
weaker form of proof than a live runtime/database/API observation, and is
labelled as such throughout.

---

## VAL-A4 — No XML/menu/action/wizard/controller/cron introduced by Task 003

**Result: static repo check passed.**

- PR #101 (Task 003, merge commit `e27f10e55f3504d1a9b8871a207b3d9762a3c783`)
  touched only: `__manifest__.py` (version bump), `models/__init__.py`,
  `models/shopify_connector_api_client.py`, `models/shopify_connector_job.py`,
  `models/shopify_connector_job_log.py`, `models/shopify_connector_store.py`,
  `tests/__init__.py`, `tests/test_api_client.py`,
  `tests/test_credential_service.py`, `tests/test_job_log_system_append.py`,
  `tests/test_test_connection.py`, and `docs/01-research/research-handoff.md`.
  It did **not** touch any XML file.
- The addon's only XML file,
  `addons/shopify_connector_core/security/shopify_connector_security.xml`,
  predates Task 003 (Task 001/002) and defines only `ir.module.category`,
  `res.groups.privilege`, and `res.groups` records — no menu, action, wizard,
  controller, route, cron, or server/scheduled-action record of any kind.
- No `controllers/` or `wizards/` directory exists anywhere under
  `addons/shopify_connector_core/`.
- A repository-wide grep for `ir.cron`, `ir.actions.server`, `ir.ui.menu`, and
  `ir.actions.act_window` inside `addons/shopify_connector_core/` returns
  **zero hits**.
- The manifest's `data` list is unchanged in content by Task 003 (only the
  `version` string was bumped) and lists only
  `security/shopify_connector_security.xml` and `security/ir.model.access.csv`.

**What this does not prove:** an `ir.model.data` / `ir.ui.menu` /
`ir.actions.act_window` / `ir.cron` **database-registry** query against a
live, installed Odoo instance was **not** performed this session — no such
instance is available in this environment. The static repo check strongly
implies (via the closed set of files Task 003 touched, and the closed set of
record types the one pre-existing XML file defines) that the DB-level result
would also be zero rows, but this remains an inference from source, not a
live observation. **The DB/registry-level half of VAL-A4 is still not
tested.**

---

## VAL-C3 — `sudo()` call-site confirmation

**Result: static source check passed — count matches governance expectation.**

Production `sudo()` call sites in `addons/shopify_connector_core/` (tests
excluded):

| # | File | Line | Method |
| --- | --- | --- | --- |
| 1 | `models/shopify_connector_store_credential.py` | 158 | `_get_access_token` (Task 002 — "the only sanctioned `sudo()` in this module," per its own docstring) |
| 2 | `models/shopify_connector_job_log.py` | 85 | `_system_append` (Task 003 — "the only `sudo()` this file contains," per its own docstring) |

**Count: exactly 2**, matching `task-003-manual-validation-checklist.md`'s
VAL-C3 expectation ("exactly two `sudo()` call sites"). No discrepancy found;
no fix needed, none proposed. (One additional `.sudo(` usage was found in
`tests/test_credential_service.py`, which is test-harness code exercising the
production sites above, not a third production call site.)

**What this does not prove:** this is a static source-line count against the
current working tree, not a re-verification against a live-installed module
version running in a real Odoo registry, as the checklist item's own wording
("live-confirmed") calls for. That live re-confirmation is still not tested.

---

## VAL-D1 — Shopify-side no-mutation static evidence

See [`task-003-no-side-effect-baseline.md`](./task-003-no-side-effect-baseline.md)
for full detail. Summary: the `TEST_CONNECTION_QUERY` GraphQL string
(`models/shopify_connector_store.py:15-18`) is confirmed read-only and
matches exactly:

```graphql
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
```

A repository-wide grep for the GraphQL `mutation` keyword inside
`addons/shopify_connector_core/` finds no mutation operation string anywhere
in the module — only a docstring note in `shopify_connector_api_client.py`
("there is no mutation-capable method"), a comment in
`shopify_connector_store.py`, and the pre-existing regression test in
`tests/test_api_client.py` that asserts by regex that no `mutation` operation
string appears in the client module's source.

**Marked as: static read-only query evidence only.** This is not a live
Shopify Admin observation of zero new/changed records or zero registered
webhooks — that live check (the actual VAL-D1 step as written in the
checklist) remains not tested this session, and no Fable/browser evidence
from the separate OAuth-experiment session was available to this session
either.

---

## VAL-D2 — Odoo-side no-domain-mutation static evidence

See [`task-003-no-side-effect-baseline.md`](./task-003-no-side-effect-baseline.md)
for full detail. Summary: `action_test_connection()`
(`models/shopify_connector_store.py:86-203`) and every helper it calls
(`_get_access_token`, `_system_append`,
`ShopifyConnectorApiClient.execute`) write only to:

- `shopify.connector.store` (`self`)
- `shopify.connector.store.credential` (`credential_state` field only)
- `shopify.connector.job`
- `shopify.connector.job.log`

No product, customer, order, inventory, stock, accounting, sale, or purchase
model is referenced anywhere in this code path.

**Marked as: static code-path evidence only, not a live-database mutation
proof.** No live Odoo database was inspected this session to confirm zero
rows changed on any domain model during an actual run; that live observation
remains not tested.

---

## VAL-C1 — server-log grep (dummy-token only)

See [`task-003-server-log-redaction-check.md`](./task-003-server-log-redaction-check.md)
for full detail. Summary: **not testable in this session — logs
unavailable.** No live Odoo runtime and no server log file of any kind exists
anywhere in this execution environment. The dummy token
`shpat_INVALID_INVALID_INVALID0000000000000000` (the same dummy token already
used in the prior live VAL-B1 run) was the only token considered — no real
token was used, requested, or is present anywhere in this session's files.
This is recorded as **not testable**, not as a pass or a fail, and does not
change VAL-C1's existing overall **PARTIAL** status recorded in
`task-003-validation-results.md` (DB/ORM half: passed in the prior live
session; server-log half: still not tested, now for a documented reason).

---

## VAL-G1–G4 — empirical open-questions capture

**Result: not tested.** No live API call was made this session (none was
in scope, and none is possible without a valid Shopify Admin API token, which
this session deliberately does not use). No empirical API behavior is
asserted or invented here. VAL-G1 (actual HTTP status for invalid token),
VAL-G2 (`THROTTLED` body shape), VAL-G3 (scopes required), and VAL-G4
(missing-scope error shape) all remain exactly as recorded in
`task-003-validation-results.md` §3 — "not reproduced this session," carried
forward unchanged.

---

## Static evidence vs. live evidence — summary

| Item | Static/offline evidence (this session) | Live evidence still required |
| --- | --- | --- |
| VAL-A4 | Repo-level: passed (zero XML/menu/action/wizard/controller/cron files introduced by Task 003) | `ir.model.data`/registry-level DB query against a live installed instance |
| VAL-C3 | Source-level: passed (exactly 2 `sudo()` sites, as expected) | Live-installed-module re-confirmation |
| VAL-D1 | Source-level: passed (query is read-only; no mutation string exists) | Live Shopify Admin observation of zero new/changed records and zero webhooks |
| VAL-D2 | Source-level: passed (code path touches only core substrate models) | Live Odoo database observation of zero domain-model changes during an actual run |
| VAL-C1 (server-log half) | Not testable — no logs exist in this environment | A live session with server-log access, using only the dummy token |
| VAL-G1–G4 | Not tested — no invented behavior | A live session with a valid token/API access |

## Explicit non-claims

- This session does not claim VAL-B2 passed, failed, or was attempted.
- This session does not claim any OAuth/token-acquisition experiment
  succeeded or failed — that is out of scope and is being handled by a
  separate, concurrently-running session.
- This session does not claim Task 003 manual validation is complete.
- This session does not claim Task 004 is unblocked.
- No code, test, manifest, security, XML, or CSV file was created or
  modified by this session.
