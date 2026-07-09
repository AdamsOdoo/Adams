# Task 006C — Sync Engine Skeleton Implementation Gate

> **Status: Accepted by ChatGPT (2026-07-09). Gate opens only after this
> PR merges into `Shopify-connector` and the final implementation prompt
> is separately issued.** This document is the explicit gate-opening act
> for Task 006C, modeled on the
> [`task-002-credential-storage-gate.md`](./task-002-credential-storage-gate.md)
> and
> [`task-003-api-client-test-connection-gate.md`](./task-003-api-client-test-connection-gate.md)
> precedent (both accepted-and-merged acts that authorized exactly one
> future coding session apiece). ChatGPT accepted this gate document via
> control-room review (GitHub review artifact/comment ID `4658949628`,
> PR #130) — **but the gate is not yet effective**: it has not merged
> into `Shopify-connector`. The gate this document describes **becomes
> effective only once this document (already accepted) is merged into
> `Shopify-connector`** — not on draft, not on review approval alone, and
> not on any earlier commit. **Even after that merge, implementation
> still does not start automatically** — a new Claude Code session must
> separately receive ChatGPT's pasted, finalized
> [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
> as its own chat turn, per `CLAUDE.md` §5/§9. **The future implementation
> PR this gate authorizes must itself remain draft for ChatGPT's own
> review.** Companion documents:
> [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
> (the proposal this act enacts — also accepted by this same review) and
> [`../05-qa/task-006d-gate-opening-review-checklist.md`](../05-qa/task-006d-gate-opening-review-checklist.md)
> (the checklist recording this acceptance decision).

## Acceptance note (2026-07-09)

- **ChatGPT accepted this gate document** via control-room review (GitHub
  review artifact/comment ID `4658949628`, PR #130).
- **The gate is accepted, but implementation does not start
  automatically.** Acceptance of this document is one of the four
  conditions §K names — not all four.
- **The gate becomes effective only after this PR merges into
  `Shopify-connector`** — PR #130 remains open/draft/unmerged as of this
  acceptance patch.
- **Even after merge, implementation requires ChatGPT to issue the
  finalized prompt in a new Claude Code session** — with the actual
  merge-commit SHA filled in, replacing the `<TASK_006D_GATE_MERGE_COMMIT_SHA>`
  placeholder still carried by
  [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
  (status: Accepted final prompt / Not issued).
- **The future implementation PR must remain draft for ChatGPT review** —
  unchanged by this acceptance; restated in §L.

---

## A. Gate purpose

This gate, **if and when accepted and merged**, would open a narrow,
one-time authorization for exactly one future coding session — **Task
006C: Sync Engine Skeleton Implementation** — building the core
job-enqueue/claim/dispatch/retry skeleton inside `shopify_connector_core`
that the accepted DEC-025 architecture gate and the accepted (as a
planning/scope package) Task 006C implementation-scope document (PR #129)
both describe. It exists because the accepted scope package's own §F left
six concrete implementation choices as candidates requiring ChatGPT's
explicit approval — this document is the vehicle for that approval,
paired with the six recommendations proposed in
[`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
§6. **This document does not itself decide any of the six choices** — it
proposes to adopt the gate-opening proposal's recommendations, subject to
ChatGPT's acceptance, revision, or rejection of each.

## B. Accepted inputs

This gate proposal rests on the following already-accepted state,
confirmed by direct inspection this session (2026-07-09):

- **DEC-025** — Task 006 sync-engine architecture gate. **Accepted by
  ChatGPT, 2026-07-08.** `AR-030` — **Accepted**.
- **Task 006C implementation-scope package**
  ([`task-006c-sync-engine-skeleton-implementation-scope.md`](./task-006c-sync-engine-skeleton-implementation-scope.md),
  PR #129) — **Accepted by ChatGPT, 2026-07-08, as a planning/scope
  package only.** This acceptance did **not** authorize code, did not
  open any implementation gate, and did not select any of the six §F
  candidates — confirmed by that document's own Acceptance note.
- **PR #129 merge commit `241871b70f8151d8b796dbb4fb7bcb69cc3b2db3`** —
  confirmed present on `origin/Shopify-connector` (the tip of that branch
  as of this session; this branch is based on it).
- **`task-006c-sync-engine-skeleton-final-prompt.md`** — status **Final
  draft / Pending gate acceptance / Not issued** (revised this session,
  Task 006D, incorporating the six recommendations below; still not
  issued; still carries an unresolved merge-commit-SHA placeholder).
- **`task-006c-sync-engine-gate-opening-proposal.md`** — status
  **Proposed for ChatGPT gate-opening review / Does not open the gate
  yet** (revised this session, Task 006D, adding the six concrete
  recommendations this gate proposes to adopt).
- **Existing accepted substrate**, confirmed unchanged by direct
  inspection of `addons/shopify_connector_core/models/` this session:
  `shopify.connector.job`'s full state machine (`JOB_STATE_SELECTION`,
  `ERROR_CLASS_SELECTION`, `MANUAL_REVIEW_SUBREASON_SELECTION`, exactly
  three `job_type` values, `idempotency_key`/`operation_scope_key` with
  their DB-level unique constraints, `BUSINESS_JOB_SOURCES`-gated
  `create()`/`write()`); `shopify.connector.job.log._system_append()`'s
  single sanctioned, redaction-enforcing write path;
  `shopify.connector.readiness.check._get_checks()`'s inheritance-append
  extension-seam precedent. **No enqueue, dispatch, registry, or drain-
  loop code exists anywhere in the repository.**

## C. Gate-opening decisions — Accepted 2026-07-09

**ChatGPT accepted each of the six recommendations in
[`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
§6** (2026-07-09, review artifact/comment ID `4658949628`, PR #130) — as
the accepted basis for the future Task 006C implementation prompt.
Restated here in summary form (full detail, evidence, and caveats live in
that document, not duplicated verbatim here, per this repo's existing
gate-document convention of referencing rather than restating):

| # | Choice | Proposed decision |
| --- | --- | --- |
| A | Execution-time claim/concurrency mechanism | `try_lock_for_update()` per candidate job row; skip locked/unavailable rows in the same drain pass; never raw SQL `SKIP LOCKED`; never a PostgreSQL advisory lock in this phase |
| B | Handler-registry seam shape | New `shopify.connector.job.dispatch` `AbstractModel` with a `_get_handlers()` registry seam, returning a `job_type → handler` mapping, adapting (not copying) the `_get_checks()` inheritance-append precedent; fails safely for a missing handler |
| C | Retry-default constants | 12 max attempts; 30-second base delay; ×2 exponential multiplier; 30-minute cap; ±20% jitter; 24-hour retry window — named, tunable constants |
| D | Enqueue/dispatch file split | `shopify_connector_job_enqueue.py` + `shopify_connector_job_dispatch.py`, both `AbstractModel`s under `models/`; no `services/` package; no concrete model/table; no ACL/security file |
| E | Cron batch size / interval | Batch size 20 (named constant); cron interval 5 minutes — both conservative defaults pending runtime validation |
| F | Core diagnostic `job_type` | `core_dispatch_selftest` — core/diagnostic-only, used only to exercise dispatcher/registry tests, never calls Shopify, never represents domain sync, does not alter existing `job_type` values' meaning |

**Each of the six is now an accepted decision, not a bare recommendation
— but acceptance of the choice is not the same act as opening the gate or
authorizing code.** The gate itself still requires this document to merge
into `Shopify-connector` and the final prompt to be separately issued
(§K).

## D. Final implementation prompt reference

- **The only implementation prompt this gate would authorize, if
  accepted and merged, is:**
  [`docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
  (status: Final draft / Pending gate acceptance / Not issued).
- **This gate document does not restate that prompt's contracts** — it
  references it by exact path, mirroring the Task 002/003 gate
  precedent, so the two documents cannot silently drift apart.
- **Any deviation from that final prompt requires a new ChatGPT
  decision** — a future implementing session may not improvise a
  different field shape, file split, constant set, or test list.
- **The prompt is issued only after** this gate document is accepted and
  merged, **and** ChatGPT separately pastes the prompt's exact text into
  a **new** Claude Code session, as its own chat turn, with the
  merge-commit-SHA placeholder filled in from this document's actual
  post-merge commit.

## E. Exact future coding scope

Restated from the accepted implementation-scope document's §A/§C and the
gate-opening proposal's §3 — **if and when this gate opens**, it would
authorize implementing, inside `shopify_connector_core` only:

- A job **enqueue** service wrapping the existing `Job.create()`.
- An `ir.cron`-driven **claim/drain loop** using Decision A's concurrency
  mechanism.
- A **handler-registry dispatch seam** per Decision B, plus the one new
  diagnostic `job_type` per Decision F.
- A **retry scheduler** using Decision C's constants, honoring the
  existing DEC-009 error-class taxonomy.
- **Duplicate-running guards** at creation (existing
  `operation_scope_key`, unchanged) and execution (Decision A).
- **Permanent-failure/blocked-manual-review transition helpers**
  implementing already-accepted DEC-009 state semantics.
- **Job-log integration** exclusively through the existing
  `_system_append()` path.
- **Store-state gating** (unchanged) plus a new **domain-enabled
  execution-time-only gating hook** (fail-safe only, no domain module).
- **Lifecycle handling** building on the existing `action_disconnect()`
  sweep, plus an execution-time-immediately-before-dispatch store-state
  re-check (narrows, does not close, SRR-03).
- **Unit tests for every implemented behavior** (§H below).

**No domain sync logic, no live Shopify call, no webhook controller, no
setup wizard/UI/view/menu/action beyond one `ir.cron` data record, and no
OAuth/token-acquisition code** — restated identically from the
implementation-scope document's §A "What it explicitly does not
implement" and §D "Future forbidden scope."

## F. Exact future allowed files

Restated verbatim from
[`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)'s
"Allowed files (exact)" list (that document is the binding source; this
is a scope summary, not a re-specification):

- `addons/shopify_connector_core/models/shopify_connector_job.py` (MODIFY
  only)
- `addons/shopify_connector_core/models/shopify_connector_job_enqueue.py`
  (NEW, per Decision D)
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (NEW, per Decision D)
- `addons/shopify_connector_core/models/shopify_connector_job_log.py`
  (MODIFY, only if a new `event_type` value is genuinely required)
- `addons/shopify_connector_core/data/shopify_connector_cron_drain.xml`
  (NEW — exactly one `ir.cron` record; no view/menu/action)
- `addons/shopify_connector_core/models/__init__.py` (new import lines
  only)
- `addons/shopify_connector_core/tests/test_job_enqueue.py` (NEW)
- `addons/shopify_connector_core/tests/test_job_dispatch.py` (NEW)
- `addons/shopify_connector_core/tests/test_job_retry_scheduling.py`
  (NEW, or folded into `test_job_dispatch.py`)
- `addons/shopify_connector_core/tests/__init__.py` (new import lines
  only)
- `addons/shopify_connector_core/__manifest__.py` (version bump + one new
  `data` entry only)
- `docs/01-research/research-handoff.md` (mandatory handoff update)
- `docs/05-qa/technical-debt-register.md` (only if a genuine new shortcut
  is discovered)

## G. Exact future forbidden files

Restated verbatim from the final prompt's "Forbidden files (exact)" list
and the implementation-scope document's §D:

- Any view/menu/action/wizard/controller/XML file other than the one
  cron data file named above.
- Any webhook receiver/controller file of any kind.
- Any file under a domain module
  (`shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment`),
  including any such module's creation.
- Any OAuth or token-acquisition file.
- Any CI/workflow file, Dockerfile, or `requirements*.txt`.
- Any migration file.
- Any security/`*.csv` or `*_security.xml` file — both new model files
  are `AbstractModel`s; if implementation-time inspection finds a
  concrete model is genuinely required, the implementing session must
  stop and report back before writing any code.
- `shopify_connector_store.py`, `shopify_connector_store_credential.py`,
  `shopify_connector_store_settings.py`, `shopify_connector_location.py`,
  `shopify_connector_binding_mixin.py`, `shopify_connector_api_client.py`,
  `tools/redaction.py` — read/called, never modified.
- Any file not explicitly named in §F above.
- **`main`, plain `dev`, and `dev/Shopify-connector`** — forbidden as
  targets or bases, unchanged.

## H. Tests required

Restated from the implementation-scope document's §H and the final
prompt's "Tests" section — every behavior implemented under §E must ship
with a unit test; no behavior implemented untested:

- Enqueue allowed/blocked by store state.
- Enqueue idempotency (existing `idempotency_key` constraint).
- Operation-scope duplicate prevention (existing `operation_scope_key`
  constraint).
- Execution claim guard (Decision A's mechanism; code-level proof only,
  **not** a claim of real concurrent-worker safety).
- Handler registry dispatch (fake handler via `_get_handlers()`,
  exercised only via `core_dispatch_selftest`, per Decision F).
- Missing handler behavior (fails safely, never hangs or silently
  drops).
- Retryable error schedules retry (Decision C's constants).
- Terminal error routes to `failed_final`/`blocked_manual_review` as
  applicable.
- Logs appended through the sanctioned `_system_append()` path only.
- Secrets redacted (mirrors `test_no_secret_leakage_in_job_or_log`).
- Disconnect cancels/blocks relevant jobs (extends
  `test_disconnect_cancels_non_terminal_business_jobs`).
- Execution-time store-state recheck (extends
  `test_business_job_running_blocked_when_not_connected`).
- Execution-time domain-enabled recheck.
- No live Shopify call in unit tests (source-level test).
- No domain modules required (full new suite passes with zero domain
  modules installed).

## I. Runtime validation required after implementation PR

**None of the following may be marked passed by the future implementation
PR's own description without genuine live Odoo.sh evidence** — restated
from the implementation-scope document's §I and the gate-opening
proposal's §8:

- Cron drain runs in Odoo runtime.
- Concurrency behavior under multiple workers (Decision A's mechanism —
  not proven safe by unit tests or by this gate's acceptance).
- Disconnect during an active job (live SRR-03 reproduction — narrowed,
  not closed, by the execution-time re-check).
- Retry scheduling works over real time.
- Failed jobs visible/queryable in a live registry.
- No token leakage in logs (live server-log grep).
- Savepoint/batch behavior acceptable at realistic volumes (Decision E's
  defaults validated live).

## J. Open blockers preserved

**None of the following is resolved, narrowed, or silently decided by
this gate document, by adopting the six §C recommendations, or by the
future Task 006C implementation this gate would authorize:**

- VAL-B2 (deferred / not passed), MBQ-05 (Partially routed / Open),
  TD-002 (Open), the fulfillment API model (unresolved), product
  first-sync deduplication (domain design), token acquisition for many
  unrelated customers (unresolved), Lite/Full packaging (not finalized),
  the 16-vs-17 `@idempotent` mutation-count discrepancy (open,
  immaterial), the OCA `queue_job` worker-count wording discrepancy
  (open, non-blocking), checkpoint/resume ownership (undecided), and the
  multi-server/Odoo.sh runtime concurrency proof requirement (still
  required before any implementation relies on a concurrency
  assumption) — every one carried forward unchanged from DEC-025 and the
  accepted implementation-scope document's §G.

## K. Gate opening condition

**This gate is not yet open — it is accepted but not yet effective.** It
opens only once **all** of the following are true:

1. ~~ChatGPT accepts this gate document (including any revision ChatGPT
   requires).~~ **Satisfied 2026-07-09** — accepted via control-room
   review (GitHub review artifact/comment ID `4658949628`, PR #130).
2. ~~ChatGPT accepts the companion
   [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md).~~
   **Satisfied 2026-07-09** — accepted by the same review.
3. **This PR (or its accepted revision) is merged into
   `Shopify-connector`.** **Not yet satisfied** — PR #130 remains
   open/draft/unmerged as of this acceptance patch.
4. **Even then**, implementation does not start until ChatGPT separately
   pastes the finalized
   [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
   text, with the merge-commit-SHA placeholder resolved to this
   document's actual merge commit, into a **new** Claude Code session, as
   its own chat turn. **Not yet satisfied.**

**Acceptance of this document — even now — does not itself start
implementation, and does not itself open the gate.** Conditions 3 and 4
are distinct, later, separate acts, neither of which this acceptance
patch performs.

## L. Gate closing condition

The gate, once opened, closes again the moment the future Task 006C
implementation PR this gate authorizes is **opened as a draft** for
ChatGPT's own review. No follow-on coding beyond that one PR is
authorized by this gate — any further sync-engine work (a second slice, a
domain module registering into the handler seam, etc.) requires its own
separate, later, explicit ChatGPT gate-opening act, mirroring the
AR-021 → AR-026 → AR-029 precedent chain.

## M. Rollback and safety notes

Restated from the implementation-scope document's §J:

- **Single-PR revert.** The future implementation PR is expected to be a
  single, self-contained PR — reverting it removes the enqueue/dispatch/
  registry code, the new `ir.cron` record, and the new tests, with no
  destructive schema change (no column drop, no table drop).
- **Protecting existing data.** Any `job`/`job.log` rows created before a
  rollback remain in the database as valid audit history
  (`ondelete='restrict'`, unchanged) — a rollback must not attempt to
  delete them.
- **Avoiding destructive schema changes.** Any change to
  `shopify_connector_job.py` must be additive (new methods) or, if a new
  field proves necessary, nullable/optional only — never a rename or
  removal of an existing column.
- **Preserving job history.** Removing the new `ir.cron` record on
  rollback stops future drain runs but does not touch any already-
  processed job row.

## N. No implementation yet

**No Odoo module, model, view, XML, security file, migration, CI/
workflow file, controller, wizard, OAuth code, or domain-sync code is
created or modified by this document or by this acceptance patch.** No
addon file was modified this session or the prior one — every addon file
named in this package was read for decision accuracy only. **This
acceptance patch does not, by itself, open the Task 006C implementation
gate.** It does not authorize any code. This document now carries
ChatGPT's acceptance (2026-07-09), but it does **not** claim this PR has
merged, or that the final prompt has been issued — neither is true yet.
The gate it describes opens only per §K above, closes per §L, and
**implementation starts only when a new Claude Code session separately
receives ChatGPT's pasted final prompt as its own chat turn, after this
PR merges** — never automatically, never as a continuation of this
session, and never as a consequence of this document's acceptance alone.
