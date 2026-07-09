# Task 006C — Sync Engine Skeleton Implementation-Scope Package

> **Status: Accepted by ChatGPT as planning/scope package.** Acceptance
> date: **2026-07-08** (control-room review, GitHub review artifact/comment
> ID `4920363287`, PR #129). This document remains a
> **future-implementation-planning package only**. It authorizes **no
> code**. It creates no Odoo module, model, view, XML, security file,
> migration, CI/workflow file, or dependency. The `CLAUDE.md` §4–§5 no-code
> gate remains in full force. Nothing in this document opens the Task 006C
> implementation gate — that is a separate, later ChatGPT act, gated on
> this document, its companion
> [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
> (Status: **Draft only / Not issued** — unchanged by this acceptance), and
> [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
> (Status: **Proposed only / Does not open the gate** — unchanged by this
> acceptance) all being separately accepted, per §L below. See the
> Acceptance note immediately below for the full scope of what this
> acceptance does, and explicitly does not, do.

## Acceptance note (2026-07-08)

- **Accepted by ChatGPT** for PR #129, per control-room review (GitHub
  review artifact/comment ID `4920363287`) — **content-wise, as a
  planning/scope package only**.
- **This accepts the Task 006C implementation-scope package only** — the
  document you are reading. It does not accept, modify, or extend the
  status of any other document.
- **This does not authorize code.** No addon file, Python, XML, CSV,
  manifest, security, migration, CI/workflow, controller, view, wizard,
  OAuth, or domain-sync code is created, modified, or implied by this
  acceptance.
- **This does not open the Task 006C implementation gate.**
- **This does not issue or accept the final prompt.**
  [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
  is unmodified by this acceptance and remains **Draft only / Not
  issued**.
- **This does not accept the gate-opening proposal.**
  [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
  is unmodified by this acceptance and remains **Proposed only / Does not
  open the gate**.
- **This does not fill any placeholder** in the final-prompt draft (the
  concurrency mechanism, the handler-registry shape, the retry-default
  constants, the merge-commit SHA, or the file-split note) — every one
  remains exactly as unresolved as before this acceptance.
- **This does not select the execution-time claim/concurrency mechanism**
  (§F item 1) — remains a candidate requiring ChatGPT approval in a
  future, separate gate-opening act.
- **This does not select the handler-registry seam shape** (§F item 4) —
  remains a candidate requiring ChatGPT approval in a future, separate
  gate-opening act.
- **Task 006C implementation remains blocked** until a future, separately
  authorized gate-opening act and a separately issued final prompt —
  neither is created, started, or implied by this acceptance. Every open
  item preserved by §G below (VAL-B2, MBQ-05, TD-002, the fulfillment API
  model, product first-sync dedup, token acquisition, Lite/Full
  packaging, the 16-vs-17 discrepancy, the OCA `queue_job` wording
  discrepancy, and the multi-server/Odoo.sh runtime concurrency proof
  requirement) remains exactly as open as it was before this acceptance.

- **Session date:** 2026-07-08.
- **Branch:** `claude/task-006c-sync-engine-scope-pmj6ta` (harness-designated
  session branch; based on `origin/Shopify-connector` HEAD `a45e0a6`, the
  PR #128 merge commit, confirmed an ancestor of this branch before any
  edit).
- **Primary accepted inputs:** the accepted Task 006B architecture gate
  ([`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md))
  and its companion decision record
  ([`DEC-025`](../04-decisions/DEC-025-task-006-sync-engine-gate.md), Status:
  **Accepted by ChatGPT, 2026-07-08**), plus
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  (`AR-030`, Accepted), the accepted Task 001–005 substrate cited throughout,
  and the still-open items registered in
  [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md),
  [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md),
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
  and
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  — all read in full this session, all checked before any proposal below,
  per `CLAUDE.md` §10. Claims below are labelled per `CLAUDE.md` §8
  (**Fact** / **Inference** / **Recommendation** / **Decision** /
  **Open question**); nothing here is a **Decision** and nothing upgrades an
  open item's status.

---

## A. Scope summary

**[Recommendation]** This document proposes the scope of a **future,
separately authorized** coding session ("Task 006C implementation") that
would build a **controlled core sync-engine skeleton** inside
`shopify_connector_core`, directly implementing the architecture-level
shape DEC-025 already accepted (enqueue → claim/drain → dispatch → retry/
failure routing → logging/redaction → gating → lifecycle handling), without
implementing any domain sync logic.

**This document itself is future-implementation planning only.** It does
not write code, does not create a module, model, view, security file,
migration, or CI file, and does not authorize a coding session to start.
Per `CLAUDE.md` §5, only ChatGPT — through the gate-opening act named in
§L — can lift the no-code gate for the future task this document scopes.

**Exact future coding objective (if and when authorized):** implement the
core job-processing engine — a job **enqueue** service, an `ir.cron`-driven
**drain/claim** loop, a **handler-registry** dispatch seam, a **retry**
scheduler honoring the accepted DEC-009 taxonomy, **duplicate-running**
guards at both creation and execution time, **permanent-failure**/
**blocked-manual-review** transitions, job-log integration through the
existing sanctioned `_system_append()` path with redaction preserved,
**store-state** and **domain-enabled** gating at both enqueue and execution
time, and lifecycle handling for disconnected/reconnect-needed stores — all
with unit tests, no Shopify live calls, and no domain sync logic of any
kind.

**What business value this unlocks:** today, `shopify.connector.job` is a
fully-gated, fully-tested **state-machine schema** with no engine that
actually moves a job through it — no code path creates a business job, no
code path claims/dispatches one, and no code path executes a retry. A
domain module (product/customer/order/inventory/fulfillment) cannot safely
enqueue or process a single real sync operation until this engine exists,
because every domain job would otherwise need to reinvent claiming,
retry, and failure-routing itself — exactly the duplicated-substrate
anti-pattern **RA-013** already rejects. Building this skeleton is the
single largest unblocking step between the accepted architecture (DEC-025)
and any future domain-sync implementation task.

**What it explicitly does not implement (restated from the task's own
instruction, binding on any future coding session this document scopes):**

- No product, customer, order, inventory, or fulfillment domain sync logic
  of any kind — no field mapping, no matching rule, no Shopify write.
- No live Shopify API call of any kind (no domain job type ever actually
  dispatches to a handler that calls Shopify — the skeleton's own tests use
  no-op/fake handlers only).
- No webhook HTTP controller/receiver. (See §F for the explicit scoping of
  this exclusion.)
- No setup wizard, view, menu, action, or any other UI/XML surface beyond
  the one `ir.cron` data record named in §C.
- No OAuth or token-acquisition implementation.
- No resolution of any open item named in §G — every one of them is
  preserved, unchanged, by this document and by the future task it scopes.

---

## B. Existing substrate inventory

### B.1 Existing accepted models (confirmed by direct code inspection this
session — **Fact**, not inference)

| Model | File | What exists today |
| --- | --- | --- |
| `shopify.connector.job` | `models/shopify_connector_job.py` | Full state-machine schema: `job_source` (7 values incl. the 5 business sources + 2 core/diagnostic sources), `trigger_origin`, `job_type` (3 core/diagnostic values only — **no domain job type is registered anywhere**), `state` (10-value `JOB_STATE_SELECTION`), `error_class` (16-class `ERROR_CLASS_SELECTION`), `manual_review_subreason` (6-value, DEC-009 §D.5.4), `retry_count`, `next_retry_at`, `res_model`/`res_id`/`shopify_target_gid` (target triple), `payload_hash`, computed+stored `idempotency_key` (`UNIQUE(store_id, idempotency_key)`) and `operation_scope_key` (`UNIQUE(store_id, operation_scope_key)`, cleared on terminal/superseded state), `superseded_by_job_id`, `cancel_reason`, `started_at`/`finished_at`. `create()`/`write()` already gate the 5 business `job_source` values on `store.state == 'connected'`, using effective post-write values, at both enqueue and the `state → 'running'` transition (Task 005/DEC-022 §4.2). **No code path anywhere creates a job with any business `job_source` value** — every existing caller (`action_test_connection`, `_create_lifecycle_audit_job`, `run_for_store`) uses only the two core/diagnostic sources. **No claim/dispatch/retry-scheduling code exists.** |
| `shopify.connector.job.log` | `models/shopify_connector_job_log.py` | Append-only child model; `_system_append()` is the single sanctioned write path (the model's only `sudo()`), redacting `message`/`technical_detail`/`payload_snapshot` via `tools/redaction.py`'s `redact()` before every write. No group holds `perm_create` — rows are system-appended only. |
| `shopify.connector.store` | `models/shopify_connector_store.py` | Full connection lifecycle (`setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`), `action_activate()`/`action_disconnect()`/`action_reconnect()`/`action_mark_reconnect_needed()` (Task 005/DEC-024, live-validated on Odoo.sh). `action_disconnect()` already cancels every non-terminal business job for the store (via `Job.search(... job_source in BUSINESS_JOB_SOURCES, state not in TERMINAL_JOB_STATES)`), preserving history, and calls the existing credential-clear service. Also owns `action_test_connection()` (Task 003), the sole existing caller of the GraphQL API client. |
| `shopify.connector.store.credential` | `models/shopify_connector_store_credential.py` | Admin-only credential storage (masked, plain — no encryption claim, AR-022/024/025 accepted residual); `_get_access_token()` is the sole sanctioned read path (its module's only `sudo()`). Any credential mutation already moves a `connected` store to `reconnect_needed`. |
| `shopify.connector.store.settings` | `models/shopify_connector_store_settings.py` | Per-store domain-enablement flags (`product_domain_enabled`, `sale_domain_enabled`, `inventory_domain_enabled`, `fulfillment_domain_enabled` — all default `False`), plus `product_first_sync_source`/`price_source_of_truth`/`notification_default_enabled`. **No code anywhere reads these flags to gate a job** — the readiness check's `_check_domain_flag_enablement` only checks that *at least one* is `True` for readiness-summary purposes; it does not gate enqueue/execution. |
| `shopify.connector.readiness.check` (`AbstractModel`) | `models/shopify_connector_readiness_check.py` | The one existing, tested extension-seam precedent: `_get_checks()` is overridden via classic `_inherit` + `super()` + append. Registers **checks**, not sync **operations** — the gate document (§B principle 7, §C) is explicit that this pattern requires adaptation, not verbatim reuse, for a future job-type/handler registry. |
| `shopify.connector.binding.mixin` (`AbstractModel`) | `models/shopify_connector_binding_mixin.py` | The accepted (DEC-013) core binding contract shape — `store_id`/`shopify_gid`/`status`/`match_key`/audit fields — inherited by future domain concrete binding models. Out of scope for a core-only skeleton (no domain binding is created by this scope). |
| `shopify.connector.location` | `models/shopify_connector_location.py` | Shopify-side-only Location cache (`shopify_location_gid`, `name`, `active`, `last_synced_at`), no write ACL for any role — system-populated only. Not touched by this scope. |
| `shopify.connector.api.client` (`AbstractModel`) | `models/shopify_connector_api_client.py` | **Read-only** GraphQL transport boundary (Task 003). `execute()`/`_send()` cannot construct a `mutation` body; no retry loop (retry policy is explicitly deferred to the job layer, matching this scope). Raises `ShopifyClientError` with one of exactly four `error_class` values (`shopify_temporary_server_network`, `shopify_permission_scope_auth`, `shopify_throttling_rate_limit`, `unknown_system_error`). **This scope's skeleton never calls this client** — no live Shopify call exists anywhere in Task 006C's proposed tests. |
| `tools/redaction.py` | `redact()` | Key- and value-pattern-based recursive redaction, already used by both sanctioned write paths (`job.log._system_append`, `api_client`'s error path). The skeleton's log-integration work (§F) reuses this — it does not add a second redaction mechanism. |

### B.2 Existing test substrate (confirmed by direct inspection — **Fact**)

Eight test files, 2,410 lines total, `TransactionCase`-based (per-method
savepoint — the established convention, consistent with `sync-engine-open-
questions.md` open question 24's still-unresolved note that a *drain-loop
concurrency* test would need a heavier harness `TransactionCase` cannot
provide). Coverage today: credential service, redaction, job-log
`_system_append`, readiness-check registry/aggregation/extension-seam,
test-connection, and the full connection-lifecycle/store-state-gating
matrix (`test_connection_lifecycle.py`, 759 lines — the largest file,
covering `action_activate`/`action_disconnect`/`action_reconnect`/
`action_mark_reconnect_needed` and both enqueue-time and execution-time
business-job gating). **No test exists for claiming, dispatch, a handler
registry, retry scheduling, or domain-enabled gating** — because no code
implementing any of those exists yet.

### B.3 Exact existing code files future coding will likely modify

- `addons/shopify_connector_core/models/shopify_connector_job.py` — to add
  claim/transition helper methods (see §C, §F). **Modification, not
  rewrite**: the existing schema, constraints, `create()`/`write()` gating,
  and computed-key logic are already accepted (Task 001/003/005) and must
  not be altered beyond what §C names.
- `addons/shopify_connector_core/models/__init__.py` — exactly one new
  import line per new model file (the existing one-line-per-file
  precedent, e.g. Task 004's addition of `shopify_connector_readiness_check`).
- `addons/shopify_connector_core/tests/__init__.py` — exactly one new
  import line per new test file (same precedent).
- `addons/shopify_connector_core/__manifest__.py` — version bump (current
  `19.0.1.4.0`) plus one new entry in `data` for the `ir.cron` data file
  named in §C. No other manifest change.

### B.4 Exact new files future coding may create

See §C for the full grouped list. **Candidate names below are this
document's best-evidenced proposal, not implementation-final** — the
future task's own final prompt (§ of
[`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md))
fixes the exact names ChatGPT actually issues.

### B.5 Confirmed existing facts vs. candidate future changes

Every row in §B.1/§B.2 is a **confirmed existing fact** (direct code
inspection, this session, 2026-07-08). Every file/method named in §B.3/§B.4
and everywhere in §C–§F below is a **candidate future change** — none of it
exists in the repository today, and nothing in this document creates it.

---

## C. Proposed future allowed files

**[Recommendation — conservative, subject to ChatGPT revision in the
gate-opening act]**

### Models

- `addons/shopify_connector_core/models/shopify_connector_job.py`
  (**modify only** — add: an execution-time claim/lock helper; state-
  transition helper methods for `retry_waiting`/`failed_retryable`/
  `failed_final`/`blocked_manual_review`/`skipped`; a domain-enabled
  execution-time re-check alongside the existing store-state re-check in
  `write()`; **exactly one new `job_type` Selection value**, reserved for
  the dispatcher's own internal self-test/diagnostic use (candidate name:
  `core_dispatch_selftest`), added the same way the three existing values
  already are (an inline addition to the existing static `selection=[...]`
  list — `job_type` has no `selection_add` caller anywhere yet, since no
  domain module exists). This is a **necessary** addition, not optional:
  with zero domain job types registered (§B.1), the §H "Handler registry
  dispatch"/"Retryable error"/"Terminal error" tests have no other
  allowed-files-compliant way to construct a `shopify.connector.job` row
  whose `job_type` actually routes through the new registry to a
  registered fake handler — Odoo's ORM rejects a `Selection` value outside
  its declared list, so a test cannot simply pass an arbitrary string.
  This value is core/diagnostic-only, mirroring the existing three (it is
  never dispatched to a live Shopify call, exactly like
  `core_test_connection`/`core_readiness_check`). Do not remove or weaken
  any existing field, constraint, or gating check.)
- `addons/shopify_connector_core/models/shopify_connector_job_enqueue.py`
  (**new**, `AbstractModel`, no table — the core enqueue service/API named
  in the task's core-slice list; the single call surface a future domain
  module would use to create a business job.)
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (**new**, `AbstractModel`, no table — the drain-loop entry point, the
  handler-registry seam (`_get_handlers()`, mirroring the readiness-check
  `_get_checks()` precedent per §F), the dispatcher, and the retry-
  scheduling sweep.)
- `addons/shopify_connector_core/models/shopify_connector_job_log.py`
  (**modify only, conditionally** — add a new `event_type` Selection value,
  e.g. `retry_scheduled`, only if the dispatcher's own logging needs one
  the existing five values do not cover; if the existing values suffice,
  this file is **not** touched. No change to `_system_append()`'s
  signature or its redaction behavior either way.)

*(Exact file count/split above — one enqueue file plus one dispatch file,
versus folding both into `shopify_connector_job.py` itself — is itself a
**[candidate requiring ChatGPT approval]**, not fixed by this document; see
§F.)*

### Services

No separate `services/` package exists in this addon today (compare: the
Shopify transport boundary is itself modeled as an `AbstractModel` under
`models/`, not a `services/` package). This scope follows that existing
convention rather than introducing a new package layout.

### Tests

- `addons/shopify_connector_core/tests/test_job_enqueue.py` (**new**)
- `addons/shopify_connector_core/tests/test_job_dispatch.py` (**new**)
- `addons/shopify_connector_core/tests/test_job_retry_scheduling.py`
  (**new** — or folded into `test_job_dispatch.py`; exact split is
  implementation-planning detail, not fixed here.)

### Data / cron XML — needed, scoped narrowly

- `addons/shopify_connector_core/data/shopify_connector_cron_drain.xml`
  (**new** — exactly one `ir.cron` record registering the drain-loop
  skeleton at a conservative interval, e.g. matching the accepted
  Odoo.sh "best effort," never-more-often-than-~5-minutes guidance
  (DEC-005 evidence, `O7`/`OD-2`). **This is data, not UI** — no view,
  menu, or action of any kind accompanies it.)

### Init files

- `addons/shopify_connector_core/models/__init__.py` (modify — new import
  lines only, per §B.3).
- `addons/shopify_connector_core/tests/__init__.py` (modify — new import
  lines only, per §B.3).

### Manifest

- `addons/shopify_connector_core/__manifest__.py` (modify — version bump;
  add the one new `data/` file above to the `data` list; no other change).

### Documentation

- `docs/01-research/research-handoff.md` (modify — the mandatory
  `CLAUDE.md` §12 handoff update; every future task carries this, not
  specific to this scope).
- `docs/05-qa/technical-debt-register.md` (modify — **only if** a genuine
  new shortcut is taken during the future coding session; not touched
  otherwise).

### Explicitly forbidden files (conservative — if in doubt, forbidden)

- Any `security/*.csv` or `*_security.xml` file — the two new model files
  proposed above are `AbstractModel`s (no table), mirroring
  `shopify_connector_readiness_check.py`/`shopify_connector_api_client.py`,
  so no new ACL row should be needed. **If implementation-time inspection
  finds a concrete (non-abstract) model is genuinely required, the future
  task must stop and report back before adding any security file**,
  exactly mirroring the Task 004 final-prompt precedent for an
  unanticipated file-boundary conflict.
- `shopify_connector_store.py`, `shopify_connector_store_credential.py`,
  `shopify_connector_store_settings.py`, `shopify_connector_location.py`,
  `shopify_connector_binding_mixin.py`, `shopify_connector_api_client.py`,
  `tools/redaction.py` — all **read/called, never modified** by this
  scope.
- Any view, menu, action, wizard, or controller file of any kind.
- Any domain module directory
  (`shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment`),
  including its creation.

---

## D. Future forbidden scope

Explicitly forbidden for the future Task 006C coding session, restated
from the task's own instruction and binding on
[`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md):

- **Any product/customer/order/inventory/fulfillment domain module or
  domain-sync logic** — no field mapping, no matching rule, no domain
  binding model, no Shopify write of any kind.
- **Any OAuth/token-acquisition implementation** — MBQ-05 remains open
  (§G); the skeleton continues to use only the existing, already-accepted
  `token_variant='offline_custom_app'` credential seam, unmodified.
- **Any setup wizard, view, menu, action, or other UI surface** — the one
  `ir.cron` data record in §C is the sole XML artifact; it is data, not
  UI.
- **Any webhook controller implementation.** The gate document names a
  webhook-topic registration seam (blueprint §A.5 seam 7) as a *future*
  extension point, but building it now — with no domain module ever to
  register a topic, and no HTTP receiver to enqueue from — would be
  unused, untestable placeholder code. **This scope forbids it entirely**;
  it is not proposed even as a "placeholder-free internal registry," since
  a registry with zero real registrants and zero real callers is
  indistinguishable from a placeholder in practice. If ChatGPT judges
  otherwise, that judgment belongs in the gate-opening act (§L), not
  assumed here.
- **Any live Shopify API call.** No test, fixture, or code path in this
  scope may call `shopify.connector.api.client.execute()` against a real
  endpoint. Handlers registered for skeleton tests are no-op/fake only.
- **Any accounting/refund/payout logic** — out of Phase 1 scope entirely
  (RA-010; DEC-025 §I "Future accounting / refund / payout" row).
- **Any Lite/Full packaging implementation** — MBQ concept remains
  unresolved (§G); no packaging-tier code, flag, or gate is added.
- **Any unrelated refactor** of already-accepted Task 001–005 behavior
  beyond the narrow, named modifications in §C. In particular: no change
  to `action_activate`/`action_disconnect`/`action_reconnect`/
  `action_mark_reconnect_needed`'s existing accepted semantics; no change
  to the credential service; no change to the readiness-check registry's
  existing checks.
- **`main`, plain `dev`, and `dev/Shopify-connector`** — all forbidden as
  targets or bases, per `CLAUDE.md`'s branch governance, unchanged.

---

## E. Architecture-to-code mapping

Every row maps an accepted DEC-025 responsibility (cited) to the future
coding work this scope proposes. No row here decides anything DEC-025
itself left open — see the "Candidate" labels, cross-referenced to §F.

| DEC-025 responsibility | Accepted source | Proposed future implementation |
| --- | --- | --- |
| **Enqueue** | DEC-025 point 1 (core owns orchestration); gate §C "Job creation/enqueue API" (candidate, not yet built) | New `shopify_connector_job_enqueue.py` service wrapping `Job.create()` — inherits the existing store-state gate automatically (no gate duplicated), computes an operation-appropriate `idempotency_key`/`operation_scope_key` via the existing computed fields (no new key scheme). |
| **Claim/drain** | DEC-025 point 5 (`ir.cron` substrate); gate §C "Job claiming/drain loop" (candidate, concurrency mechanism explicitly undesigned at architecture level) | New `ir.cron` record (§C) invoking `shopify_connector_job_dispatch.py`'s drain entry point, which claims batched `queued`/`retry_waiting` rows using the concrete mechanism proposed in §F item 1 — **candidate requiring ChatGPT approval**, not selected by this document alone. |
| **Dispatch** | DEC-025 point 1 (domain modules register handlers); gate §C "Execution dispatcher" (candidate) | `shopify_connector_job_dispatch.py` dispatches a claimed job by `job_type` to a registered handler via the registry (below); with zero domain job types registered today, the skeleton's own tests use fake/no-op handlers only. |
| **Registry** | DEC-025 point 1; blueprint §A.5 seam 2 (accepted direction — job-type registration); gate §C (precedented but requiring adaptation); gate §K / DEC-025 "Open questions" (this exact question — whether the `_get_checks()` seam literally extends to job-type dispatch, or needs a materially different shape — is one of the three new architecture-level open questions this gate itself explicitly surfaces, alongside the concurrency mechanism and checkpoint/resume ownership) | `_get_handlers()` on the dispatch model, following the `_get_checks()` inheritance-append precedent as this document's proposed shape — **candidate requiring ChatGPT approval**, per §F item 4, not selected here, since DEC-025 explicitly left this exact question open rather than answering it. |
| **Retry** | DEC-025 point 3 (classified DEC-009 taxonomy); gate §E | Dispatcher reads the job's `error_class` on failure and routes per the existing `ERROR_CLASS_SELECTION`/retry-taxonomy already encoded in `shopify_connector_job.py`'s constants; scheduling constants (attempts/backoff) per §F item 2 — implementation-planning defaults, not new architecture. |
| **Idempotency** | DEC-025 point 4 (layered idempotency, core owns job key + serialization guard) | No new mechanism — the future enqueue service reuses the existing `idempotency_key`/`operation_scope_key` computed fields and their DB-level unique constraints verbatim. |
| **Duplicate-running prevention** | DEC-025 point 4 (creation-time guard accepted, implemented; **execution-time/claiming guard explicitly an undesigned candidate**, DEC-025 "Explicit non-decisions") | Creation-time: already fully accepted/implemented (`operation_scope_key`), reused as-is. Execution-time: a concrete claim mechanism proposed in §F item 1 — **candidate requiring ChatGPT approval**, since DEC-025 explicitly states no job-claiming concurrency mechanism is selected. |
| **Failure visibility** | DEC-025 point 3; gate §E ("must never disappear into raw `ir.cron` logs," SRR-05) | `failed_final`/`blocked_manual_review` transitions (§F item 6) surfaced through the existing `job`/`job.log` model — no reliance on `ir.cron`'s own `_notify_admin()`. |
| **Logs** | DEC-025 point 3; gate §C ("no parallel logging mechanism") | Every dispatcher/enqueue write path calls the existing `job.log._system_append()` exclusively — no second log-write path is introduced. |
| **Redaction** | DEC-025 point 3; gate §C (accepted, implemented) | No new redaction mechanism — `_system_append()` already redacts every free-text argument via the existing `tools/redaction.py:redact()`; the skeleton's own log messages/technical details/payload snapshots pass through unchanged. |
| **Gating** | DEC-025 point 1; gate §C (store-state accepted/implemented; domain-enablement accepted at blueprint level, DEC-013 §I.3) | Store-state: already fully accepted/implemented in `job.py`'s `create()`/`write()`, untouched. Domain-enablement: a new, analogous execution-time-only re-check added to `job.py`'s `write()` (fail-safe gating only — never alters an enqueue-time decision, per DEC-013 §I.3's own accepted constraint) — **selected for Task 006C future implementation**, §F item 5. |
| **Lifecycle handling** | DEC-025 point 1; gate §C ("Lifecycle behavior on disconnect/reconnect/credential mutation," accepted/implemented, with an open risk — SRR-03) | No new mechanism for the already-accepted disconnect-time cancellation sweep (`action_disconnect()`, unchanged). The dispatcher must **re-check store state immediately before executing a claimed job** (not only at claim time), narrowing — but per DEC-025's own explicit framing, **not provably closing** — the SRR-03 in-flight race; this re-check is **selected for Task 006C future implementation**, §F item 9, as a direct extension of the already-accepted two-checkpoint store-state defense-in-depth pattern (gate §C) — not a claim that the race is closed, and not itself a new architecture decision requiring separate approval. |
| **Tests** | Task's own §H requirement | See §H below — a dedicated new test file per major behavior, no behavior implemented without an accompanying unit test. |

---

## F. Concrete future design candidates

Each open implementation choice is labelled exactly as required: **selected
for Task 006C future implementation**, **candidate requiring ChatGPT
approval**, or **deferred**.

1. **Job claiming / execution concurrency guard** — **candidate requiring
   ChatGPT approval.** DEC-025's own "Explicit non-decisions" section
   states plainly: "No job-claiming concurrency mechanism is selected." The
   gate document (§C, §G) names `lock_for_update()`/`try_lock_for_update()`
   (Odoo's official row-locking primitives, `O9`/`OD-3`, whose only
   official documented use case is exactly this cron-batch-processing
   pattern) as the most directly evidence-backed candidate, ahead of a raw
   `SKIP LOCKED` reimplementation or PostgreSQL advisory locks (which carry
   their own documented hazards — `LIMIT`-ordering interaction,
   rollback-non-release — per SRR-09). **This document's recommendation**
   (not a decision): a non-blocking claim using `try_lock_for_update()` per
   candidate row, skipping any row that cannot be locked in the same drain
   pass (functionally mirroring `SKIP LOCKED` semantics using an officially
   documented Odoo 19 primitive) — but this remains explicitly **not
   selected** here, because doing so would pre-empt DEC-025's own withheld
   decision. The future task's final prompt (§L) must not proceed to code
   this without ChatGPT explicitly approving a specific mechanism in the
   gate-opening act. **Whichever mechanism is approved, its concurrency
   safety under real multi-worker/multi-server load is explicitly NOT
   provable by this scope's own unit tests** (`TransactionCase`'s
   single-transaction model cannot exercise real concurrent workers, per
   open question 24) — DEC-025 Risks #2/#3 (SRR-04/SRR-09) require live
   Odoo.sh (and, where relevant, multi-server) runtime proof **after**
   implementation, per §I.
2. **Retry due-date and attempt handling** — **selected for Task 006C
   future implementation**, as an adjustable implementation-planning
   default, not a new architecture decision. DEC-009's own acceptance note
   already labels MBQ-16's constants (12 attempts, 30s exponential base
   ×2, capped at 30 minutes, ±20% jitter, 24-hour window) as
   "implementation-planning defaults, not final production-tuned
   constants" — coding a skeleton retry scheduler necessarily needs *some*
   concrete numbers to exist and be tested; these are the only
   evidence-cited candidates in the accepted corpus. The future task must
   keep them named as adjustable defaults (e.g. named constants, not
   inlined magic numbers) so a later session can retune them without an
   architecture change.
3. **Checkpoint/resume placeholder vs. actual model** — **deferred.**
   DEC-025's "Explicit non-decisions" states "No checkpoint/resume
   ownership (core vs. domain) is decided" (open question 7). Task 006C's
   own scope excludes all domain sync logic, and checkpoint/resume is
   meaningful only for a paginated/bulk-import job — a domain concern with
   no core skeleton consumer yet. Building even a placeholder model risks
   silently pre-deciding the core-vs-domain ownership question. **No
   checkpoint/resume file, field, or model is proposed anywhere in §C.**
4. **Handler registry shape** — **candidate requiring ChatGPT approval.**
   DEC-025's own "Open questions" section names, as one of exactly three
   *new*, architecture-level open questions this gate itself surfaces
   (alongside the concurrency mechanism, item 1, and checkpoint/resume
   ownership, item 3): "whether the readiness-check extension-seam pattern
   literally extends to job-type dispatch" (gate §K restates the identical
   framing: "Whether the readiness-check `_get_checks()` seam pattern can
   be literally extended to job-type/handler dispatch, or needs a
   materially different shape"). This document's earlier draft mislabeled
   this "selected," which this revision corrects — DEC-025 explicitly left
   the question open, so this document must not answer it either. **This
   document's recommendation** (not a decision): adapt the `_get_checks()`
   inheritance-append pattern (an existing, tested precedent, gate §B
   principle 7) to `job_type → handler` dispatch via a new `_get_handlers()`
   method, since blueprint §A.5 seam 2 (job-type registration) is already
   an accepted extension-seam *direction* (DEC-013) even though its exact
   *shape* is not. The future task's final prompt must not proceed to code
   this shape without ChatGPT explicitly approving it in the gate-opening
   act, exactly as for item 1. **Exercising this seam in unit tests
   requires exactly one new `job_type` Selection value** (candidate name
   `core_dispatch_selftest`, core/diagnostic-only, added to
   `shopify_connector_job.py`'s existing static selection list per §C) —
   with zero domain job types registered, no existing value can stand in
   for a registered, dispatchable test target without repurposing one of
   the three existing values' already-committed meaning. Whichever
   registry shape ChatGPT approves, this one new diagnostic `job_type`
   value remains necessary to test it.
5. **Domain-enabled gating hook** — **selected for Task 006C future
   implementation**, hook shape only, no domain module. DEC-013 already
   accepts the direction at blueprint level (§I.3: flags read at enqueue
   time **and** re-checked at execution time, scoped to **fail-safe
   gating only** — may stop/hold/cancel/block, never alter an enqueue-time
   decision or bypass a safety guard). The future task implements exactly
   this shape against the existing `shopify.connector.store.settings`
   flags, with zero domain flags ever actually driving real behavior
   (since no domain module exists to set them meaningfully yet) — the hook
   is tested with a synthetic/test-only flag value, not a live domain
   flag.
6. **Permanent-failure/manual-review actions** — **selected for Task 006C
   future implementation.** `failed_final` and `blocked_manual_review` are
   already-accepted terminal/loop-back states (DEC-009) with an existing,
   already-accepted six-value `manual_review_subreason` vocabulary and a
   `_check_manual_review_subreason_required()` constraint already enforcing
   it. The future task adds transition helper methods (mirroring the
   existing `_create_lifecycle_audit_job`/lifecycle-action pattern in
   `shopify_connector_store.py`) that move a job into these states with
   the correct sub-reason and an audited `job.log` entry — implementing
   already-accepted state semantics, not deciding new ones.
7. **Cron batching and savepoint strategy** — **selected for Task 006C
   future implementation**, as a conservative implementation-planning
   default requiring post-implementation runtime validation. DEC-005/§D.1
   already accepts per-record-isolation batching via `ir.cron`; the
   >64-savepoint performance ceiling (SRR-01, DEC-025 Risk #4) is a
   documented, not-yet-validated-at-realistic-volume constraint. This
   document recommends the future task cap the drain loop's per-run batch
   size well below 64 (e.g. a small, named constant such as 20), explicitly
   flagged in code/tests as a tunable default pending the runtime
   validation named in §I — not a proof the number is correct at scale.
8. **Webhook-topic registration seam** — **deferred**, per §D. No consumer
   exists; building it now would be unused scaffolding.
9. **Execution-time-immediately-before-dispatch store-state re-check
   (SRR-03 narrowing)** — **selected for Task 006C future implementation.**
   Gate §C already accepts, as implemented, a two-checkpoint store-state
   defense-in-depth pattern (enqueue time; the `state → 'running'`
   transition). Adding a third checkpoint — a re-check immediately before
   the dispatcher actually invokes a claimed job's handler — is a direct
   extension of that already-accepted pattern using the same store-state
   field and the same fail-closed logic, not a new architecture decision,
   so it does not require the separate ChatGPT approval items 1 and 4
   require. **This selection narrows, but per DEC-025's own explicit
   framing does not provably close, SRR-03** (the disconnect/in-flight-job
   race, DEC-025 Risk #1) — the future task must not claim the race is
   closed in its PR description, tests, or docstrings; §I still requires
   live proof.

---

## G. Open items preserved

**None of the following is resolved, narrowed, advanced, or silently
decided by this document.** Every item below remains exactly as open as it
was before this session, and the future Task 006C coding session this
document scopes — if and when authorized — must not resolve any of them
either unless a named, separate ChatGPT decision does so first:

- **VAL-B2** — remains deferred / not passed. No live Shopify Admin API
  connection has been made or attempted by this session or any prior one.
- **MBQ-05** — remains Partially routed / Open (token acquisition for many
  unrelated customers unresolved).
- **TD-002** — remains Open (`read_fulfillments` readiness-scope
  correctness concern).
- **Fulfillment API model** — remains unresolved (legacy `Fulfillment` vs.
  `FulfillmentOrder`-based).
- **Product first-sync deduplication** — remains domain-design work,
  deferred to a future product-domain task (MBQ-59).
- **Token acquisition for many unrelated customers** — remains unresolved
  (MBQ-05 branch B, DEC-023 §3.2).
- **Lite/Full packaging** — remains not finalized; still treated as
  product strategy, not an architecture or implementation decision.
- **16-vs-17 `@idempotent` mutation-count discrepancy** — remains open,
  unresolved, immaterial to this core-engine-level scope (no mutation list
  is hard-coded anywhere in §C/§F).
- **OCA `queue_job` worker-count wording discrepancy** (`--workers > 0` vs.
  `> 1`) — remains open, still explicitly non-blocking; `queue_job` remains
  reference-only (RA-004 unchanged, not revisited by this scope).
- **Multi-server/Odoo.sh runtime concurrency proof** — remains explicitly
  required (DEC-025 Risks #1–#3) before any future implementation may rely
  on a claim about the job-claiming mechanism selected in §F item 1, the
  disconnect/in-flight-job race (SRR-03), or cross-server coordination.
  This document does not claim such proof exists; §I restates the
  validation this scope's future coding PR would still owe.

---

## H. Tests required for future coding PR

Every behavior implemented under §C must ship with a unit test; no behavior
is implemented untested. At minimum:

- **Enqueue allowed/blocked by store state** — a business-job enqueue via
  the new enqueue service succeeds only when `store.state == 'connected'`,
  reusing (not duplicating) the existing `job.py` `create()` gate test
  matrix in `test_connection_lifecycle.py`.
- **Enqueue idempotency** — two enqueue calls with the same operation
  identity collide on the existing `idempotency_key` unique constraint,
  not a new mechanism.
- **Operation-scope duplicate prevention** — two enqueue calls targeting
  the same `(store, res_model, res_id, shopify_target_gid)` while the
  first is non-terminal collide on `operation_scope_key`.
- **Execution claim guard** — two simulated concurrent claim attempts
  against the same job row: only one claim succeeds; the mechanism
  selected per §F item 1 is exercised, with the test file's own
  docstring/comment explicitly stating this proves the mechanism's
  *code-level* behavior under `TransactionCase`, not real concurrent-worker
  safety (see §I).
- **Handler registry dispatch** — a fake/no-op handler registered via the
  `_get_handlers()` seam (from outside `shopify_connector_core`, mirroring
  the existing `test_extension_seam_registers_check_without_modifying_core`
  precedent) is actually invoked by the dispatcher for the new
  `core_dispatch_selftest` `job_type` value (§C, §F item 4) — the only
  `job_type` this scope's own tests may use to exercise the registry,
  since the three pre-existing values remain reserved for their own
  already-committed synchronous flows.
- **Missing handler behavior** — a job whose `job_type` has no registered
  handler fails safely (e.g. routes to `unknown_system_error` /
  `failed_final`), never silently drops or hangs.
- **Retryable error schedules retry** — a fake handler raising a
  retryable-class error causes the dispatcher to set `retry_waiting` +
  `next_retry_at`, honoring the §F item 2 defaults.
- **Terminal error goes `failed_final`/`blocked_manual_review` as
  applicable** — a fake handler raising a manual-fix-class error reaches
  `failed_final`; one raising a confirmation-required class reaches
  `blocked_manual_review` with the correct `manual_review_subreason`.
- **Logs appended through sanctioned path** — every dispatcher/enqueue
  write path is proven to call `job.log._system_append()` and never
  `job.log.create()` directly (mirroring the existing
  `test_source_level_two_sudo_sites_total`-style source-level guard
  pattern already used elsewhere in this test suite).
- **Secrets redacted** — a dummy-token string threaded through a fake
  handler's failure path never appears unredacted in any `job`/`job.log`
  field (mirroring the existing `test_no_secret_leakage_in_job_or_log`
  pattern).
- **Disconnect cancels/blocks relevant jobs** — reuses/extends the existing
  `test_disconnect_cancels_non_terminal_business_jobs` coverage against a
  job that is `queued`/`retry_waiting` under the new dispatcher, confirming
  no new business-job state introduced by §C escapes that sweep.
- **Execution-time store-state recheck** — a job whose store disconnects
  between claim and dispatch is not executed (extends the existing
  `test_business_job_running_blocked_when_not_connected` pattern to the new
  dispatcher code path).
- **Execution-time domain-enabled recheck** — a job whose domain flag is
  disabled between enqueue and claim is stopped/held/cancelled (per §F item
  5), never silently executed and never silently altering its enqueue-time
  decisions.
- **No live Shopify call in unit tests** — a source-level test (mirroring
  `test_readiness_check_never_calls_shopify_api_client`) proves no test in
  the new files calls `shopify.connector.api.client.execute()`.
- **No domain modules required** — the full new test suite passes with
  zero domain modules installed, proving the skeleton has no domain
  dependency.

---

## I. Runtime validation required after future coding PR

**None of the following is claimed as already passed by this document.**
Per DEC-025's own risk register, live Odoo.sh (and, where named,
multi-server) proof remains required before any future implementation may
rely on a concurrency assumption:

- **Cron drain runs in Odoo runtime.** The new `ir.cron` record actually
  fires and drains queued jobs on a live Odoo 19/PostgreSQL instance —
  `TransactionCase` alone cannot prove a real scheduled action executes.
- **Concurrency behavior under multiple workers.** The job-claiming
  mechanism selected per §F item 1 must be exercised with `--max-cron-
  threads` > 1 (or an equivalent concurrent-execution harness) against a
  real database, per DEC-025 Risk #2 (SRR-04) — not provable by this
  scope's own unit tests.
- **Disconnect during an active job.** A live test reproducing the SRR-03
  scenario (a business job `running` inside an in-flight `ir.cron` batch
  at the exact instant of disconnect) — this scope's own execution-time
  re-check (§F item 9) narrows but does not, by itself, prove the race is
  closed.
- **Retry scheduling works over time.** A `retry_waiting` job's
  `next_retry_at` is honored by a subsequent real cron firing, not merely
  by a unit test manipulating the clock in-process.
- **Failed jobs visible in UI/model search.** `failed_final`/
  `blocked_manual_review` rows are queryable against a live registry
  (no UI is built by this scope, but the underlying model/search behavior
  must be confirmed live, not merely asserted by ORM-level unit tests).
- **No token leakage in logs.** A live Odoo server-log grep (mirroring the
  Task 004 manual-validation-checklist §E precedent) for a dummy-token
  string across every persisted surface this scope's dispatcher touches.
- **Savepoint/batch behavior acceptable.** The §F item 7 batch-size default
  validated against realistic catalog/order volumes on a live instance, per
  SRR-01/DEC-025 Risk #4 — not merely the documentation warning restated.

None of these runtime checks may be marked passed by the future coding
session's own PR description without an actual live Odoo.sh run producing
the evidence, mirroring the Task 004/Task 005 validation-results precedent
(`../05-qa/task-004-validation-results.md`,
`../05-qa/task-005-validation-results.md`).

---

## J. Rollback notes

- **Single-PR revert.** The future Task 006C coding PR is expected to be a
  single, self-contained PR (new files + the narrow modifications named in
  §C) — reverting it removes the enqueue/dispatch/registry code, the new
  `ir.cron` record, and the new tests, with no destructive schema change
  (no column drop, no table drop) since no existing field is removed or
  retyped.
- **Protecting existing data.** Any `shopify.connector.job`/`job.log` rows
  created by the new enqueue/dispatch code before a rollback remain in the
  database (Odoo migrations do not delete data on a code-only revert); a
  rollback must not attempt to delete them — they remain valid audit
  history under the existing `job.log` "audit history, not disposable
  children" design (`ondelete='restrict'`, unchanged).
- **Avoiding destructive schema changes.** §C's proposed model changes to
  `shopify_connector_job.py` are additive (new methods) or, if a new field
  proves necessary at implementation time, must be nullable/optional and
  never a rename or removal of an existing column — mirroring this
  project's existing "no NOT NULL surprise on stored-computed fields"
  lesson already encoded in the current file's own comments.
- **Preserving job history.** The new `ir.cron` record's removal on
  rollback stops future drain runs but does not touch any job row already
  processed; `job.log`'s append-only, `ondelete='restrict'` design already
  guarantees history survives a code-only rollback.

---

## K. Definition of done for future coding PR

- All unit tests named in §H pass.
- No live Shopify API call exists in any unit test (proven by the
  source-level test named in §H).
- Documentation updated: the mandatory `research-handoff.md` entry
  (`CLAUDE.md` §12), plus any new technical debt logged in
  `../05-qa/technical-debt-register.md` if a genuine shortcut is taken.
- A runtime-validation plan (mirroring §I above, filled in with the actual
  future PR's specifics) is created and attached to the PR — **not**
  claimed as already executed inside the same PR unless it genuinely was,
  with evidence, mirroring the Task 004/005 precedent.
- No domain sync logic of any kind exists anywhere in the diff.
- No UI file of any kind exists in the diff, unless a future,
  separately-authorized session explicitly reopens that boundary.
- No implementation beyond the core skeleton named in §C — any file not on
  the allowed list is treated as scope creep and must be dropped or
  separately re-authorized, not silently included.

---

## L. Gate-opening conditions

Before any Task 006C coding session may start, **all** of the following
must be true — none is satisfied by this document alone:

1. **This implementation-scope document is accepted** (not merely
   proposed) by ChatGPT, including any revision ChatGPT requires.
2. **The companion final prompt**
   ([`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md))
   **is accepted** by ChatGPT, with any `<PLACEHOLDER>` (e.g. a merge-
   commit SHA) filled in — mirroring the Task 004 final-prompt precedent
   of a draft-then-finalized two-stage document.
3. **The companion gate-opening proposal**
   ([`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md))
   **is accepted** by ChatGPT.
4. **This PR (or its accepted revision) is merged** into
   `Shopify-connector`.
5. **The next coding session is separately issued** — ChatGPT pastes the
   finalized prompt text, in chat, as its own turn, per `CLAUDE.md` §5/§9.
   Acceptance of documents 1–4 above does not, by itself, constitute
   issuing that prompt.

**No implementation is authorized by this document.** No Task 006C
implementation gate is opened by this document. This document does not
claim any of the five conditions above is satisfied.
