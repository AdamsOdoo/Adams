# CORE-R2 — Durable Job Execution Ownership & Remote Replay Safety

> **Status: PROPOSED — PENDING CONTROL-ROOM ACCEPTANCE.** This is an
> architecture-decision **package**, not an accepted decision. Nothing in
> this file authorizes implementation. The no-code gate (`CLAUDE.md` §4–§5)
> remains in force. Companion decision record:
> [`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)
> (also **Proposed**). Architecture-review-log row:
> [`AR-048`](../05-qa/architecture-review-log.md).
>
> **Revised 2026-07-15 (control-room review `4701015790`).** The original
> draft made the full durable-ownership protocol (Option A) an immediate
> requirement. This revision splits the architecture into **Layer 1** (a
> minimal replay-policy registry — the immediate MVP/UAT decision, §0.1) and
> **Layer 2** (Option A and mutation hardening — deferred until the first
> Shopify-mutation domain, §0.1/§8). Evidence and option analysis (§2–§4)
> are unchanged; the recommendation and implementation slicing (§8–§9) are
> narrowed.

**Session type:** normal Claude Code session (not Odoo.sh runtime). Docs-only.
No production code, test code, or PR #163 changes were made by this session.
**Date:** 2026-07-15 (revised same day — control-room review `4701015790`).

---

## 0. Why this document exists

PR #163 (`claude/core-r2-slice-2b-runtime-correction-review` @
`655e1cd744c9a9c9d82d65a926369168e0429de0`, base
`claude/core-r2-slice-2b-integration` @
`63d10fb465a26189fa463f9c7ac580da6a931c5c`) fixed three real defects in the
CORE-R2 Slice 2B scheduled-dispatch path (concurrency exceptions re-raised
instead of poisoning the transaction; failure routing re-locks and revalidates
after rollback; customer/product lifecycle test corrections) but, by its own
PR body, could **not** close the underlying gap:

> "The current implementation prevents Worker A from immediately re-invoking
> the handler in the same `_drain_one()` call. It does not prove or guarantee
> that the Shopify operation is executed only once after the database
> transaction rolls back." — PR #163 body, "Remaining blocking issue" section.

Control-room review (`4700703933`) requires a **decided, documented,
production contract** for durable job-execution ownership and remote replay
safety **before** any further implementation code is authorized. This
document is that decision package. PR #163 is **not** modified, merged, or
used as a base by this package (§1).

---

## 0.1 Two-layer decision structure (revision — control-room review `4701015790`)

> **This revision narrows scope; it does not redo the research.** Control-room
> review `4701015790` found the original package's immediate requirement —
> the full Option-A durable-ownership protocol (`attempt_id`/
> `owner_worker_ref`/`transport_attempted`, two commits per job, a new
> stale-owner cron) — disproportionate to current UAT scope, where every
> implemented Shopify handler is read-only. The evidence and option analysis
> below (§2–§4) are unchanged and still support both layers; only the
> recommendation and implementation slicing (§8–§9) are narrowed.

**Layer 1 — MVP/UAT contract, decided now, implement next.** A minimal,
fail-closed replay-policy registry (§5) with three declared classes
(`local_only`, `remote_read_replay_safe`, `remote_effect_not_replay_safe`),
explicit declarations for the three current handlers, and a fail-closed
default for everything else. **No new model, field, migration, or cron.**
PR #163's rollback/reset/re-lock/revalidate/bounded-retry behavior
(Option D, §4) is **accepted as-is** for the current read-only scope: a
replayed Shopify query has no side effect to duplicate, the failed Odoo
transaction is rolled back, and importer duplicate prevention/bindings/
uniqueness constraints remain the local data-integrity protection. The new
registry's job is to make that acceptance **safe by construction** — never
to let a future mutation handler silently inherit it.

**Layer 2 — mutation hardening, deferred.** Durable execution ownership
(Option A, §4), persisted attempt identity, transport-ambiguity tracking,
stale-owner recovery, Shopify idempotency-key persistence, and
reconciliation-before-retry remain the correct future architecture — **not
required, and not a blocker, for current read-only product/customer/order
UAT.** Layer 2 is reopened by name (§8) the moment any Shopify **mutation**
domain is authorized for implementation: inventory export,
fulfillment/tracking update, product export, refund creation, or any other
Shopify write.

See §8 for the full Layer 1/Layer 2 recommendation and §9 for the narrowed
implementation slicing.

---

## 1. Verified starting state (Phase 1)

Verified directly against the repository and GitHub at session start
(2026-07-15):

| Item | Required | Verified |
| --- | --- | --- |
| Integration branch tip | `claude/core-r2-slice-2b-integration` @ `63d10fb465a26189fa463f9c7ac580da6a931c5c` | **Match** — `git rev-parse origin/claude/core-r2-slice-2b-integration` = `63d10fb465a26189fa463f9c7ac580da6a931c5c` |
| PR #163 | draft, unmerged, head `655e1cd744c9a9c9d82d65a926369168e0429de0` | **Match** — `state: open, draft: true, merged: false`, head SHA exact |
| `Shopify-connector` | unchanged, `dd6ecb8` | **Match** — tip `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`, confirmed to be the exact merge-base of `Shopify-connector` and the integration branch (i.e. the integration branch is `Shopify-connector` plus additive product/customer completeness work only — `shopify_connector_job.py`/`shopify_connector_job_dispatch.py` are byte-identical between the two) |
| PR #150 | open, draft, unmerged, head `10d0034e` | **Match** — head `10d0034e8e666684daa36f517788223976d74035`, `state: open, draft: true, merged: false` |
| PR #151 | open, draft, unmerged, head `e4669aaf` | **Match** — head `e4669aaf206fe8436a6d8a524b083f48d56ac9df`, `state: open, draft: true, merged: false` |
| Existing replay-safety decision PR | none | **Confirmed none** — `search_pull_requests` for `head:core-r2-replay-safety-decision` and for `replay-safety` in title/body returned only PR #163 itself (which discusses the gap, but is not a decision PR) |
| Working tree | clean | **Confirmed clean** at session start and after branch reset |

**Branch note.** This session's harness-assigned development branch,
`claude/core-r2-replay-safety-decision-3f7pjs`, initially pointed at the
`Shopify-connector` tip (`dd6ecb8`) rather than the required
`63d10fb`. It carried no unique commits (its tip was an exact ancestor of
`origin/Shopify-connector`), so it was safely reset
(`git checkout -B claude/core-r2-replay-safety-decision-3f7pjs 63d10fb…`) to
start exactly at the accepted integration SHA before any file was written.
No history was lost — the discarded tip is `Shopify-connector`'s own
already-preserved history.

**Revision verification (2026-07-15, control-room review `4701015790`).**
Re-checked before this revision was written: PR #164 head still
`3cefc42346f48a339fdaec0ddad5035625ff7751`, base still
`claude/core-r2-slice-2b-integration` @ `63d10fb465a26189fa463f9c7ac580da6a931c5c`;
PR #163 still open/draft/unmerged at `655e1cd744c9a9c9d82d65a926369168e0429de0`,
untouched. Nothing in this revision required re-verifying §2's evidence — it
is unchanged and still current.

---

## 2. Evidence reviewed (Phase 2)

Claims below are labelled **[Fact]** (verifiable from a primary source, cited),
**[Inference]** (this session's reasoning from cited facts), or
**[Open question]**. No claim in this section is a **Decision** — proposed
decisions are in §3–§9 and are separately labelled **[Recommendation]** or
routed to the DEC-031 file for control-room acceptance.

### 2.1 Repository evidence — current job-dispatch mechanism

All citations are to the exact accepted integration base,
`63d10fb465a26189fa463f9c7ac580da6a931c5c`, read directly (`git show
63d10fb:<path>`), except where a PR #163 diff is explicitly named.

**[Fact] Job states and retry taxonomy.**
`addons/shopify_connector_core/models/shopify_connector_job.py:6-59` defines
`JOB_STATE_SELECTION` (`draft`, `queued`, `running`, `succeeded`,
`failed_final`, `skipped`, `cancelled`, `retry_waiting`, `failed_retryable`,
`blocked_manual_review`), `TERMINAL_JOB_STATES`, the fixed 16-value
`ERROR_CLASS_SELECTION`, and the six-value `MANUAL_REVIEW_SUBREASON_SELECTION`
(`ambiguous_match`, `binding_conflict`, **`duplicate_risk`**,
`destructive_write_guard_blocked`, `inventory_location_missing`,
`fulfillment_notification_confirmation_missing`). `duplicate_risk` already
exists in the accepted vocabulary — this matters directly for §7.

**[Fact] `_claim_for_dispatch`** (`shopify_connector_job.py:319-363`) claims
up to `limit` claimable (`queued`, or due `retry_waiting`) jobs via
`try_lock_for_update()` (Odoo 19's non-blocking `FOR UPDATE SKIP LOCKED`
primitive), re-checks each row's state under the lock, and returns only
still-claimable rows. Its own docstring states plainly: *"This is a
code-level claim guard only... this method's behavior under actual
multi-worker/multi-server execution is NOT proven by any unit test in this
repository."*

**[Fact] `_drain_one` / `_recover_after_concurrency_conflict` (PR #163 diff,
`63d10fb` → `655e1cd`, `shopify_connector_job_dispatch.py`).** PR #163 adds a
per-job transaction boundary: claim → dispatch → `env.cr.flush()`; on a
genuine PostgreSQL concurrency exception
(`PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` = 40001/40P01/55P03), roll back, reset
the environment, **reacquire the exact job** under a fresh
`try_lock_for_update`, revalidate its claimable state under that lock, and —
**only if still owned and claimable** — route it once to
`concurrency_race_conflict` (bounded auto-retry) **without replaying the
handler**. `_invoke_handler` now re-raises `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY`
instead of routing it through an ORM write inside an already-aborted
transaction.

**[Fact] The mechanism's own documented limits.**
`_recover_after_concurrency_conflict`'s docstring states its ownership
contract explicitly includes: *"Another worker winning the post-rollback
claim, or having already transitioned the job, is a valid outcome — never an
error."* This is not a bug the docstring is hiding; it is the design's
stated behavior. Between step 1 (rollback+reset) and step 2 (reacquire the
lock) in `_recover_after_concurrency_conflict`, the job row is **fully
unlocked and back in a claimable state** (`queued`/due `retry_waiting`) —
this is the exact window in which a second worker's own `_claim_for_dispatch`
can legitimately win the row and invoke the **real** handler a second time.
**[Inference]** Because `concurrency_race_conflict` is unconditionally in
`AUTO_RETRY_ERROR_CLASSES` (`shopify_connector_job_dispatch.py:55-59`,
unchanged by PR #163), a job routed to `retry_waiting` by
`_recover_after_concurrency_conflict` is *also* eligible for a **second,
scheduled** automatic replay by a future drain, independent of the Worker-B
race — i.e., PR #163 leaves two independent replay paths open, exactly as
its own PR body states (worker-B replay, and scheduled future replay).

**[Fact] `operation_scope_key` / `idempotency_key`**
(`shopify_connector_job.py:141-538`). `idempotency_key` answers "is this the
same operation, same target, same payload, already known" and is a
`(store_id, idempotency_key)`-unique, stored, computed field — it prevents a
**second job row** for an identical operation from being created, but is
computed once at job-creation time and says nothing about whether a given
job's **handler** has already produced an external effect.
`operation_scope_key` is a DB-backed serialization guard
(`(store_id, res_model, res_id, shopify_target_gid)`-unique while
non-terminal) that prevents two **concurrent non-terminal jobs** against the
same target, not two **attempts of the same job**. **[Inference]** Neither
key records attempt-level transport/outcome state; both are silent on the
exact ambiguity PR #163 identifies.

**[Fact] Call-lease behavior — `shopify.connector.call.lease` /
`execute_business`** (`shopify_connector_call_lease.py`,
`shopify_connector_api_client.py:345-538`, both at `63d10fb`).
`execute_business(job, store, query, variables)` is a `@contextmanager`:
`__enter__` performs `_admit` (an **independent, owned side-cursor
transaction**: `SELECT … FOR SHARE` on the store row, fresh
state/`connection_generation` gate check, single token read, insert +
**commit** an opaque-keyed `call.lease` row) then issues the HTTP call via
`_send`; the lease is held **through** `yield result` — i.e., through the
caller's local reconciliation code inside the `with` block — and is deleted
on a **second independent side-cursor transaction** (`_release_lease`) in
`__exit__`, on both normal and exception exit.

**[Fact — directly answering the task's Option-B instruction] The
call-lease's lifecycle does *not* cover the whole job, and does *not* cover
the post-transport database window this gap concerns.** The lease is
released (row deleted, committed) the moment the handler's local
reconciliation code inside the `with execute_business(...)` block finishes —
**this happens strictly *before* `_invoke_handler` returns control to
`_dispatch_one`/`_drain_one`, which still has to write the job's own terminal
state (`succeeded`, or route via `_route_failure`) and commit the *outer*
job-dispatch transaction.** If that *outer* commit itself hits a genuine
PostgreSQL concurrency failure — the exact scenario `_recover_after_
concurrency_conflict` exists to handle — the lease has **already been
deleted** by the time the rollback occurs. No committed record of "a
transport occurred" survives that rollback. The call-lease's actual designed
purpose (per its own docstring and
`disconnect-quiescence-remediation-analysis.md`) is a **disconnect-quiescence
signal** — "is anyone currently talking to Shopify for this store" — not a
per-job attempt/outcome ledger. Reusing it as a replay-safety mechanism would
require extending its lifecycle to span claim→terminal-commit (not
admit→reconciliation) and giving it outcome/ambiguity semantics it does not
have today — effectively building a different thing under the same name. See
§4 (Option B) for the full evaluation.

**[Fact] The call-lease is dormant — not wired into any live call site.**
`shopify_connector_api_client.py:136` ("Foundation-slice dormancy... no
production call site uses them yet; the legacy `execute()` path is unchanged
and still the only live caller") is independently confirmed by direct
inspection of the current product and customer importers: both call
`self.env['shopify.connector.api.client'].execute(...)` (plain, legacy,
un-leased) — `shopify_connector_product_importer.py:213`,
`shopify_connector_customer_importer.py:113`. **[Inference]** The replay-safety
gap is therefore live-relevant *today* even though every shipped handler is
currently read-only: the dispatcher-level ownership mechanism (§2.1 above) is
domain-neutral and already governs these handlers' execution, independent of
whether they use `execute()` or the (unused) `execute_business()`.

**[Fact] `connection_generation` / epoch gate is a different mechanism for a
different race.** `shopify_connector_store.py` (`connection_generation`
field, `_admit`'s generation-equality check) prevents an **old-generation**
job (enqueued before a disconnect/reconnect cycle) from being admitted after
reconnect. **[Inference]** It provides no protection against two workers
racing within the **same** generation/session — the exact PR #163 scenario —
because both Worker A and Worker B hold the *same* `expected_connection_
generation` captured at enqueue.

**[Fact] Disconnect controller is further along than "Slice 1" implied.**
At `63d10fb`, `shopify_connector_store.py` already implements the
`disconnecting` state, `action_disconnect`'s generation bump +
`_lock_store_for_lifecycle` (blocking `FOR NO KEY UPDATE`), and
`_sweep_quiescing_business_jobs` (non-blocking `try_lock_for_update` sweep of
only `queued`/`retry_waiting` business jobs — a `running`/claimed row is
**never** touched, by design). This is CORE-R2 Slice 2A work, already merged
into `Shopify-connector` (and hence present at `63d10fb`). **[Inference]**
None of this machinery inspects or interacts with a job already claimed and
`running` inside another worker's transaction — consistent with SRR-03's
"OPEN" status (§2.2) and with the fact that this machinery solves
disconnect/reconnect-boundary safety, not intra-session worker-replay safety.

### 2.2 Repository evidence — prior accepted architecture & risk tracking

**[Fact] DEC-009 (`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`,
Accepted 2026-07-02) already established an "ambiguous-outcome rule" for a
structurally analogous problem:** *"a Shopify temporary/server/network
failure on a write outside Shopify's `@idempotent` surface, where the outcome
is unknown after dispatch... is not auto-retried. The job either performs a
safe verification read of Shopify's current state before any re-attempt,
where one exists, or routes to `blocked_manual_review` if the outcome cannot
be safely verified. A connector-internal job idempotency key prevents
connector-side duplicate processing but does not make it safe to re-send the
mutation to Shopify"* (DEC-009 §"Retry taxonomy"). **[Inference — load-bearing
for this package's recommendation]** DEC-009 anticipated *ambiguous Shopify
response* as a source of unsafe replay, but explicitly scoped its rule to
"Shopify temporary/server/network failure." It did **not** contemplate a
**local PostgreSQL concurrency failure occurring after a successful
transport** as a second source of the identical ambiguity — and, in the
same record, placed `concurrency_race_conflict` unconditionally in the
blanket "Automatic retry (reads and `@idempotent` writes)" class (DEC-009
§"Retry taxonomy", bullet 1), evidently written with a *pre-transport*
lock-contention scenario in mind (e.g. two workers racing to claim a row, or
racing on a binding insert). **PR #163 exposes that this single error class
now conflates two semantically different situations: a concurrency conflict
that aborted the transaction *before* any external effect (safe to blindly
retry) and one that aborted it *after* a handler already attempted a
transport (unsafe to blindly retry).** This is the precise, narrow crack this
package must close — not a wholesale re-litigation of DEC-009, which remains
otherwise correct and unchanged. See §7.

**[Fact] DEC-025 (`sync-engine-architecture-gate.md`, Accepted 2026-07-08)
explicitly left this exact question open**, not merely silent: *"No
job-claiming concurrency mechanism is selected (`SKIP LOCKED` vs.
`lock_for_update()` vs. advisory locks vs. a combination) — named as an open
architecture question, not decided"* and *"leaving the job-claiming-time
concurrency guard as an explicitly undesigned candidate"* (DEC-025
§"Explicit non-decisions", §"Accepted architecture decisions" item 4). This
package is the direct, expected continuation of that named-open item — not a
reopening of anything DEC-025 settled.

**[Fact] Task 006C** (`task-006c-sync-engine-skeleton-implementation-scope.md`,
`task-006c-sync-engine-gate-opening-proposal.md`) chose `try_lock_for_update`
over a raw `SKIP LOCKED` reimplementation or a PostgreSQL advisory lock
(Decision A) specifically as "a code-level claim guard," and its own
gate-opening proposal §4/§8 states this is **not** proven under genuine
multi-worker/multi-server execution by any unit test — consistent with
`_claim_for_dispatch`'s own docstring (§2.1) and with SRR-04/SRR-09 below.

**[Fact] `sync-engine-risk-register.md` SRR-03** is the direct, pre-existing
tracking row for this entire problem family, and is already marked **OPEN**
with a detailed history: runtime-confirmed as `DEF-PB-1` by PR #153;
remediated in *design* by the CORE-R2 disconnect-quiescence analysis (the
committed admission-lease, epoch gate, context-manager admission); the
Foundation Slice explicitly noted as **"dormant... the admission-vs-disconnect
linearization is not yet closed end to end."** SRR-03's own text already
anticipates that "becomes a live-write defect the moment a domain handler
performs a real Shopify mutation" — i.e., the risk register already correctly
scoped this as latent-but-real, not hypothetical.

**[Fact] SRR-04** documents that whether Odoo's own RPC-layer
`retrying()` protects a cron job's *own* record-processing code is an
open, source-backed inference, not a proven fact, and separately confirms
(source-cited) that `retrying()` retries the **entire wrapped function**,
which is exactly why PR #163 does **not** wrap the handler in `retrying()` —
re-invoking the whole function after a rollback would blindly replay a
transport that may have already occurred (PR #163's own `run_drain`
docstring states this explicitly, `655e1cd`, and is consistent with SRR-04's
finding).

**[Fact] SRR-09** documents that the disconnect-quiescence design already
**evaluated and rejected** a `pg_advisory_xact_lock`-based quiescence barrier
in favor of the committed admission-lease, for reasons (independent
cross-transaction visibility, real holder count/timestamps, avoiding a
held-open connection for the call's whole duration) that generalize directly
to this package's Option B/C evaluation in §4 — an advisory lock is **not**
re-proposed here, for the same reasons.

**[Fact] `rejected-approaches-log.md` (RA-001…RA-024) contains no entry**
that would block any option evaluated in §4. RA-014/RA-015/RA-017 (retry-
everything automatically; never-retry-automatically; binding-alone
idempotency) are the closest prior rejections and are **consistent with**,
not contradicted by, this package's direction (§3, §7). No rejected approach
is re-proposed by this package.

**[Fact] Future mutation domains are not yet implemented and are explicitly
scoped as writes.** `DEC-010` (inventory) states both inventory-adjacent
mutations *"require `@idempotent` as of API 2026-04 and are within the
17-mutation fixed list"* — i.e., **remote-idempotency-capable in principle**,
conditioned on the connector actually persisting and reusing a stable
Shopify idempotency key per operation, which is not yet implemented.
`DEC-011` (fulfillment) is built on `FulfillmentOrder`-based **mutations**
(`fulfillmentCreate` et al.) with no equivalent blanket `@idempotent`
statement recorded. Product export
(`task-015-product-export-implementation-packet.md`) is a Shopify **write**
domain. **None of these domains is implemented; all remain gated.**

**[Fact] Task 012 (order import) is confirmed read-only, with certain
numeric bounds separately "frozen."** `task-012-order-import-decision-
closure.md` repeatedly and structurally confirms zero mutations: *"the order
read is expressed as **four** module-level constants, all **read-only, zero
mutations**"* (§4); *"**No mutation** ever occurs on any path"* (§4.3);
*"before any Shopify mutation or SO write (there are none — the importer is
read-only)"*; *"**Live-Shopify: none required** (read-only; VAL-B2
independent)"* (§15). Separately, and precisely — **the literal phrase
"frozen read-only design" does not appear in the source documents**; "frozen"
in these documents refers specifically to the tax/total-check solver's
**locked numeric bounds** (`K=2`, `M=2`, `C_max=25`, "round-10"), not to the
document's overall approval status, which remains explicitly "Proposed for
ChatGPT control-room review. NOT accepted." Task 012 must be classified on
its own confirmed read-only behavior alone (§5), never by name, by
domain-adjacency to order data, or by its "frozen" solver bounds (a
different, unrelated property).

### 2.3 Official Odoo 19 evidence

This session independently re-verified Odoo's official behavior directly
against the `19.0` branch source (`raw.githubusercontent.com`/
`github.com/odoo/odoo`, HTTP 200, full files fetched) and the official
`odoo.com/documentation/19.0` pages, superseding (while confirming) AR-047's
earlier citation set. Access date for all citations below: 2026-07-15.

**[Fact] Each cron job runs in its own dedicated transaction, committed
after each job — and manual `commit()`/`rollback()` is an official,
explicitly sanctioned exception for cron code.**
`odoo/addons/base/models/ir_cron.py` (19.0):
`_process_jobs_loop` (lines 215-238) — *"The `cron_cr` is used to lock the
currently processed job and relased by committing after each job."*
`_run_job` (lines 457-568) opens a **brand-new cursor per job**
(`with cls.pool.cursor() as job_cr:`, line 480) and commits after each
progress checkpoint (lines 500, 557). `_callback` (lines 671-695) commits
(`env.cr.commit()`, line 691) on success or rolls back + `pool.
reset_changes()` (line 693) on any exception, then re-raises. Official docs
(`odoo.com/documentation/19.0/contributing/development/coding_guidelines.html
#never-commit-the-transaction`, Accessible): *"For scheduled actions, you
should rollback the changes if you catch errors and wish to continue.
**Scheduled actions run in a separate transaction**, so you can rollback or
commit directly when you signal progress."* — one of the few places Odoo
officially sanctions manual commit/rollback, precisely because each cron job
has its own transaction.

**[Fact — directly supports this package's "never replay in place"
direction] Odoo's own cron acquisition step already treats a concurrency
conflict as "move to the next job," never as "retry this job in place."**
`_acquire_one_job` (`ir_cron.py:308-386`) locks via `FOR NO KEY UPDATE SKIP
LOCKED` (line 365) and its docstring states: *"it is possible that this
function raises a `psycopg2.errors.SerializationFailure` in case the job has
been processed in another worker. In such case it is advised to roll back
the transaction and to go on with the other jobs"* — and
`_process_jobs_loop` does exactly that (catches
`TransactionRollbackError`, rolls back, logs, `continue`s to the next job;
lines 224-229). **[Inference]** Odoo's own framework precedent for a
concurrency conflict during batch job processing is "abandon this attempt,
move on, let a future pass pick it up cleanly" — not "blindly retry in
place." This is independent corroboration, from Odoo's own source, for
Option A's recovery direction (§4/§8): recovery must re-validate ownership
fresh, never simply resume.

**[Fact] `try_lock_for_update()` exact semantics, source-verified.**
`odoo/orm/models.py:5591-5622` (19.0; raw fetch, 7130 lines, Accessible):
issues `SELECT ... FOR UPDATE SKIP LOCKED` (or `FOR NO KEY UPDATE SKIP
LOCKED` if `allow_referencing=True`), returns **only the subset of rows that
could actually be locked** — no exception on a partial/empty result. Its
sibling `lock_for_update()` (lines 5563-5589) is the raising variant:
*"If all records couldn't be locked, a `LockError` exception is raised."*
Odoo's own "Writing cron functions" official example
(`odoo.com/documentation/19.0/developer/reference/backend/actions.html
#writing-cron-functions`, Accessible) uses exactly `_claim_for_dispatch`'s
pattern: `record.try_lock_for_update().filtered_domain(domain)` — lock, then
re-check nothing changed underneath. **[Inference, avoiding overclaim]**
neither method has a dedicated entry on the formal ORM API-reference page
(checked directly, zero matches) — its status as "the sanctioned pattern" is
an inference from the official worked example + docstring, not a formally
guaranteed API contract; this does not weaken Task 006C's choice (§2.2), it
only means the "documented pattern" claim should be held at that precision.

**[Fact] The official rollback-recovery trio, source-verified.**
`odoo/orm/environments.py` (19.0, Accessible): `Environment.reset()` is now a
**deprecated** thin wrapper (line 59-62, `DeprecationWarning`) — the
canonical 19.0 call is **`env.transaction.reset()`**.
`Transaction.reset()` (lines 610-618): *"Reset the transaction. This clears
the transaction, and reassigns the registry on all its environments. This
operation is strongly recommended after reloading the registry."`
`Registry.reset_changes()` (`odoo/orm/registry.py:1142-1152`, Accessible)
resets model setup and cancels cache invalidations. This exact trio
(`cr.rollback()` + `env.transaction.reset()` + `env.registry.
reset_changes()`) is what Odoo's own `retrying()` uses (next finding) and is
consistent with `_recover_after_concurrency_conflict`'s own
`self.env.cr.rollback(); self.env.transaction.reset()` sequence (§2.1).
**[Inference]** Reset restores ORM-cache/registry consistency — it does not
and cannot "recover" the rolled-back writes themselves, which Postgres has
already permanently discarded.

**[Fact — directly explains why PR #163 does not use `retrying()`, and why
it should not] `retrying()` re-invokes the entire wrapped function on every
retry, including any side effect already performed — and it is not even
part of the cron path.** `odoo/service/model.py:28-30` (19.0, Accessible):
`PG_CONCURRENCY_EXCEPTIONS_TO_RETRY = (LockNotAvailable, SerializationFailure,
DeadlockDetected)` (SQLSTATE `55P03`/`40001`/`40P01`, cross-checked against
`postgresql.org/docs/current/errcodes-appendix.html`, Accessible),
`MAX_TRIES_ON_CONCURRENCY_FAILURE = 5`. `retrying()` (lines 160-241): `result
= func()` sits **inside** the retry loop, called again after each `rollback()`
+`transaction.reset()`+`registry.reset_changes()`+jittered backoff
(`time.sleep`). **[Inference]** any non-database side effect `func` performs
before hitting the DB error (e.g. an outbound HTTP call) **is re-executed**
on every retry — Odoo's own source contains no side-effect suppression for
this. **[Fact, scope-limiting]** `retrying()` is used only by the
synchronous RPC dispatch path (`dispatch()` → `execute_cr()` →
`retrying(partial(call_kw, ...), env)`, lines 109-157) — a grep of the full
`ir_cron.py` source for `retrying`/`odoo.service.model` returns **zero
matches**. Cron execution never goes through `retrying()` at all; it has its
own separate, simpler mechanism (previous finding). This directly confirms
PR #163's own `run_drain` docstring reasoning (§2.1) is correct, not merely
plausible: wrapping a Shopify-calling handler in `retrying()`-style
whole-function replay would be actively dangerous, and is not even how
Odoo's own cron framework behaves today.

**[Open question, confirmed by direct negative search, not merely
un-investigated]** Odoo has **no documented official position** on
idempotency/duplicate-prevention for cron-driven external API calls.
Checked directly (all Accessible, HTTP 200, full-text searched for
"idempot"): the cron/actions reference page, the coding-guidelines page, the
ORM reference page, the Studio "Automated Actions" pages, and every fetched
source file — zero matches anywhere. This is a genuine, confirmed
documentation gap, not an unresearched point, and is exactly why this
package (§3) establishes the connector's *own* contract rather than
deferring to an Odoo-provided one that does not exist.

### 2.4 Official Shopify evidence

This session independently re-verified current Shopify Admin GraphQL API
documentation directly (`shopify.dev`, WebFetch, access date 2026-07-15),
superseding and sharpening the DEC-009/DEC-010-era citations with
mutation-specific detail.

**[Fact] Idempotency is not universal — it is opt-in, via two distinct,
narrow mechanisms.** `shopify.dev/docs/api/usage/implementing-idempotency`
and `.../idempotent-requests` (both Accessible): an `@idempotent(key: "...")`
directive on a **named, specific list** of mutations (inventory/location
mutations and `refundCreate`), and a separate plain `idempotencyKey` input
**field** on certain payment/billing mutations (e.g.
`subscriptionBillingAttemptCreate`). **Most mutations have neither** —
confirmed by direct spot-check: `orderCreate`
(`shopify.dev/docs/api/admin-graphql/latest/mutations/orderCreate`,
Accessible) has **no** `idempotencyKey` input and **no** `@idempotent`
support.

**[Fact — sharpens DEC-010's inventory claim and extends it to refunds]**
As of **API version 2026-04**, `@idempotent` becomes **mandatory** (not
merely available) for `refundCreate` and the inventory/location mutation
family (`inventorySetQuantities`, `inventoryAdjustQuantities`,
`inventoryMoveQuantities`, and others in the same named list) —
`shopify.dev/changelog/making-idempotency-mandatory-for-inventory-
adjustments-and-refund-mutations` (Accessible, posted 2025-12-12). **[Recommendation-
relevant]** This directly confirms DEC-010's inventory posture (§2.2) is
correct and shows the *same* platform guarantee will cover a future refund
domain's core mutation — **if and only if** the connector actually persists
and reuses a stable key per operation, which is not yet implemented
anywhere in this codebase.

**[Fact — directly relevant to DEC-011/fulfillment default classification]**
Fulfillment's core mutations (`fulfillmentCreate`,
`fulfillmentTrackingInfoUpdate`) are confirmed **not** on the `@idempotent`
list found at `implementing-idempotency` — consistent with, and now
independently confirming, DEC-011's own already-recorded statement that
these mutations are "not on Shopify's 17-mutation `@idempotent` list" (§2.2).
Product export's `productSet` mutation is likewise not natively
`@idempotent`; the Task 015 packet's own design compensates via
upsert-by-custom-id (§2.2) — an unproven, connector-side mitigation, not a
platform guarantee.

**[Fact] Reconciliation identifiers exist, but only usefully so for bulk
operations.** `BulkOperation` objects (`.../objects/bulkoperation`,
Accessible) expose `id`/`status`/`url`/`errorCode`/`completedAt`, queryable
after the fact via `bulkOperations`; Shopify's own docs caution *"webhook
delivery isn't always guaranteed, so you might still need to poll for the
operation's status."* For an ordinary (non-bulk) mutation with no
idempotency support, Shopify's docs describe **no** generic "look up by
request/correlation ID" recovery mechanism — a client would have to search
by a domain-natural key it controls (e.g. order `name`, product `handle`),
which is this session's own **[Inference]**, not a documented Shopify
mechanism.

**[Open question, confirmed by direct check, not an unresearched gap]** A
`requestId` in GraphQL error `extensions` is referenced only in
secondary/community sources, not on a canonical `shopify.dev` reference page
this session could locate and verify directly (`response-codes` was checked
directly and is silent on it). For the general Admin API outside the
specific idempotent-mutation list, Shopify's documentation gives **no**
way to determine after a dropped connection whether a mutation executed,
beyond re-querying application state — a genuine, confirmed documentation
gap, consistent with why this package's default (§3.3) never assumes
recoverability.

**[Fact] Rate-limit/throttle guidance is generic, not mutation-specific.**
Cost-based leaky-bucket; mutations carry a flat 10-point minimum cost
(`shopify.dev/docs/api/usage/limits`, Accessible); GraphQL throttling
surfaces as HTTP 200 with `THROTTLED` in `extensions` (confirms the
already-tracked SRR-08). Shopify's own retry guidance (back off, read
`throttleStatus`) does **not** distinguish mutations from queries for retry
*safety* — the idempotency mechanism (above) is the only documented answer to
"is it safe to retry this specific mutation," and it covers only the named
list.

**[Recommendation, unchanged, now on stronger evidence]** This directly
supports §3's central semantic choice: only a small, named, growing subset of
future mutations can ever be `remote_mutation_idempotent` under Shopify's own
platform guarantee (currently: inventory/location mutations and
`refundCreate`, confirmed above); fulfillment and product export are
confirmed **not** in that set today; every other/undeclared write defaults to
non-replay-safe (§3.3) until a connector-designed reconciliation mechanism is
built and proven (§5). **[Open question, recommended follow-up, non-
blocking]** the exact current `@idempotent` mutation list/count should be
independently re-verified against the live docs immediately before any
specific future mutation domain (inventory export, refunds) is designed in
implementation detail — two fetches in this session's research disagreed on
the exact count (17 named vs. "18 total" stated) though the named list
matched; this does not affect any conclusion in this package.

---

## 3. The semantic contract (Phase 3)

### 3.1 Delivery semantics — decided per operation class, not globally

**[Recommendation, routed to DEC-031]** The connector does **not** adopt one
global delivery semantic. It adopts **effectively-once, by construction,
differentiated by declared operation class**:

| Operation class | Delivery semantic | Mechanism |
| --- | --- | --- |
| Local-only (no external effect) | At-least-once, safe | No external effect exists to duplicate; any replay is a no-op risk only for local idempotency (already covered by `idempotency_key`). |
| Shopify read-only query | At-least-once, safe | A repeated read has no side effect; replay is always safe regardless of when/why it happens. |
| Shopify mutation, Shopify-`@idempotent` | Effectively-once | Automatic retry permitted **only** using the same persisted, reused Shopify idempotency key within Shopify's platform TTL (DEC-009, already accepted). |
| Shopify mutation, non-idempotent or unproven | At-most-once for *automatic* system behavior | No automatic replay ever. Ambiguous outcome routes to a human-reconciliation-first path (§3.5, §7) — never a silent auto-retry. A human-authorized retry is always possible, once, deliberately, after reconciliation. |
| Unknown/undeclared handler | At-most-once (fail closed) | Treated identically to "non-idempotent or unproven" by default (§3.3) — never presumed safe. |

This is a direct generalization of DEC-009's already-accepted
ambiguous-outcome rule (§2.2) to a second failure source (local
post-transport concurrency failure) that DEC-009 did not yet contemplate.
**Layer 1 note:** the middle two rows (idempotent mutation, non-idempotent/
unproven mutation) are not yet reachable by any shipped handler; the
registry (§5) collapses them into one declared class,
`remote_effect_not_replay_safe`, until a real mutation domain exists to
design against (§3.2, §0.1).

### 3.2 Operation-class taxonomy

**[Recommendation, revised — Layer 1 minimum]** The registry (§5) declares
every `job_type` into exactly **three** classes for the current scope, not
five. A finer split is real future work (Layer 2) but is not materially
required by any handler that exists today (per the control-room guidance:
do not introduce five policy classes unless they are materially required by
current code):

1. **`local_only`** — no Shopify call is possible for this `job_type`.
2. **`remote_read_replay_safe`** — Shopify query only, no mutation possible;
   replaying it has no Shopify-side side effect.
3. **`remote_effect_not_replay_safe`** — anything else: a Shopify mutation,
   or a `job_type` whose Shopify-call behavior is not (yet) proven
   read-only. This is also the fail-closed default (§3.3) for any
   undeclared `job_type`.

**Layer 2 refinement (deferred, not decided now).** Once a real Shopify
mutation domain is authorized for implementation, `remote_effect_not_
replay_safe` is expected to split into finer sub-classes — distinguishing a
mutation with a persisted, reused Shopify `@idempotent` key
(`remote_mutation_idempotent`) from one that needs a reconciliation read
before retry (`remote_mutation_reconcile_before_retry`) from one that has
neither and must always route to a human
(`remote_mutation_ambiguous_manual_review`, the original package's name for
what Layer 1 now calls `remote_effect_not_replay_safe`). That three-way
split remains a reasonable starting point for the Layer 2 design, but is
**not adopted now** — designing it before a single mutation handler exists
to design it against would be exactly the kind of hypothetical-future-
requirement design `CLAUDE.md` cautions against. Until Layer 2 is
authorized, every non-read, non-local `job_type` is simply
`remote_effect_not_replay_safe` and is handled identically: never
auto-retried; routed to `blocked_manual_review`/`duplicate_risk` if ever
reached (today, it never is — no mutation handler is implemented).

### 3.3 The default rule — fail closed, always

**[Recommendation]** An **undeclared** `job_type` (no registry entry, §5)
is treated as **`remote_effect_not_replay_safe`** — the most
conservative class — never as `remote_read_replay_safe`. A mutation handler
**never inherits** a read handler's retry behavior by omission: the registry
lookup that decides retry eligibility is keyed by `job_type`, is populated
only by explicit registration, and has no "if not found, assume safe"
fallback anywhere in the design (§5, §6, §7). This directly satisfies the
control room's stated requirement: *"unknown handlers must never be presumed
replay-safe; mutation handlers must not inherit read-query behavior
accidentally."*

### 3.4 What "ambiguous external effect" means, precisely

**[Recommendation]** An outcome is ambiguous when **all** of the following
hold: (a) a handler's Shopify transport call may have been sent and may have
reached Shopify; (b) the local Odoo transaction that would have recorded the
job's terminal outcome has failed or rolled back **after** that point; and
(c) no committed, durable local record establishes whether Shopify actually
executed the operation. Concretely today: any `PG_CONCURRENCY_EXCEPTIONS_TO_
RETRY` raised **after** a handler has entered a mutation call and **before**
the job-dispatch transaction commits its terminal state. (Today's shipped
handlers are all read-only, so no mutation call exists yet — this class is
currently unreachable in production, but the dispatcher-level mechanism must
not assume that stays true, per §2.1's "live-relevant today" finding.)

### 3.5 Operator outcome for ambiguity

**[Recommendation]** Ambiguity resolves, in order of preference, to the
**cheapest safe option the operation class supports**:

1. If `remote_read_replay_safe` or `local_only`: automatic retry (no
   ambiguity possible by definition).
2. **[Layer 2, deferred, currently unreachable — no `job_type` is declared
   this way]** If a future finer sub-class proves Shopify-side idempotency
   (the original package's `remote_mutation_idempotent` sketch, §3.2):
   automatic retry, reusing the same persisted Shopify idempotency key
   (bounded, per DEC-009).
3. **[Layer 2, deferred, currently unreachable]** If a future finer
   sub-class has a defined safe verification read (the original package's
   `remote_mutation_reconcile_before_retry` sketch, §3.2): schedule a
   reconciliation read; if it proves the operation did not occur, retry; if
   it proves the operation occurred, mark succeeded (no duplicate); if
   reconciliation itself cannot resolve it, fall through to (4).
4. **[Layer 1 — the only case any current or undeclared `job_type` can
   reach]** If `remote_effect_not_replay_safe` (including the default/
   undeclared case): **`blocked_manual_review`** with
   `manual_review_subreason='duplicate_risk'` — an operator confirms the
   real-world state before any further attempt. This reuses the **existing**
   accepted vocabulary (§2.1) — no new state, no new error class, is needed
   for this outcome.

No case in this table results in a silent, unauthorized automatic replay of
a non-idempotent mutation. See §7 for the full state/error mapping and §8 for
why this is the smallest additive change to the existing taxonomy.

---

## 4. Durable ownership options compared (Phase 4)

**Layer framing (revision).** This comparison is unchanged from the
original package. **Layer 1 (decided now) keeps Option D** — PR #163's
mechanism, as-is, gated by the new replay-policy registry (§5) rather than
replaced. **Layer 2 (deferred) recommends Option A** when a mutation domain
is authorized; Options B and C remain evaluated-and-deferred, as before.
Nothing below changes the technical analysis — only §8's recommendation of
*when* to build each option is narrowed.

### Option D — transaction row lock only (PR #163's approach): does not meet the required semantics

**Duplicate prevention:** No — proven, not assumed. `_recover_after_
concurrency_conflict`'s own ownership contract accepts "another worker
winning the post-rollback claim" as a valid outcome (§2.1); the window
between rollback and re-lock is real and the reacquired job is a **plain**
`try_lock_for_update`, indistinguishable from a first attempt. **Scheduled
replay is also unresolved:** the recovered job lands in `retry_waiting` via
`concurrency_race_conflict`, which is unconditionally auto-retried
(§2.1/§2.2), so even *absent* a Worker B, a future drain will re-invoke the
same handler. **Crash recovery:** none — a worker that crashes between
`_start_running`'s write and the outer transaction's commit leaves the row
lock released (process death releases the PostgreSQL session and its locks)
and the job **visible in whatever state was last flushed but not committed**,
i.e. effectively still `queued`/due `retry_waiting` from any other
transaction's point of view — no different from today's un-corrected
behavior for a hard crash (only the PG-concurrency-exception path is
handled; a segfault, OOM-kill, or `SIGKILL` is not). **Stale-running
recovery:** not applicable — the design never durably commits `running`
before invoking the handler, so there is no "stale running job" concept to
recover; a truly hung worker simply leaves the row without any lock, fully
reclaimable, silently. **Owner validation:** none — no attempt/owner token
exists anywhere in the schema. **Additional fields required:** none (this is
its appeal, and its limit). **Interaction with existing constraints:**
none broken, none added. **Compatibility with Odoo cron:** fully compatible
(it's already shipped as PR #163's code). **Verdict:** Option D closes the
*same-worker, same-`_drain_one`-call* replay case correctly and is worth
**keeping** as the first line of defense (§8), but it structurally cannot
close the worker-B race or the scheduled-replay case, because it has no
mechanism that survives a transaction boundary except the job's own
(non-owner-tagged) `state` column, which any worker's claim query treats
identically. **Do not accept it as sufficient merely because today's tests
pass** — the PR #163 body itself identifies exactly why the new tests do not
exercise the dangerous ordering (Test A starts Worker B only after Worker A
has already reacquired the lock; Test C's Worker B handler is a deliberate
no-op).

### Option A — committed running state before handler, owner/attempt token, timeout-based stale recovery

**Design:** split today's single per-job transaction into two: (1) claim
(`try_lock_for_update`, as today) → write `state='running'` **plus** a new
opaque `attempt_id` (e.g. `uuid4`) and `owner_worker_ref` **and commit
immediately**, before the handler runs; (2) run the handler in a fresh
transaction; (3) at finalize, **re-acquire the row lock**, verify
`attempt_id` still matches (nobody else has taken over ownership in the
interim), then write the terminal state and commit. A separate,
timeout-driven sweep (mirroring the existing disconnect-quiescence
controller's cron pattern) finds jobs stuck in `running` past a bound
(`running_since`/heartbeat older than a threshold) and routes them through
the **replay-policy registry** (§5) to a safe disposition — never a blind
requeue.

**Duplicate prevention:** Strong. Once `running` + `attempt_id` is
**committed**, `_claim_for_dispatch`'s own candidate search (`state in
('queued', 'retry_waiting')`) structurally excludes the row — no other
worker's claim query can even select it, with no lock required to enforce
that exclusion (the durable state *is* the exclusion). **Crash recovery:**
Yes — a worker that crashes after commit (1) and before commit (3) leaves
the job durably `running`; the timeout sweep (not a blind requeue) recovers
it. **Stale-running recovery:** Yes, by design (the sweep's entire purpose).
**Owner validation:** Yes — the `attempt_id` compare-and-swap at finalize
(and at sweep-driven recovery) rejects a write from a stale owner whose
`attempt_id` no longer matches, directly satisfying "stale owner finalizing
after takeover" prevention (§6). **Additional fields required:** `attempt_id`
(Char, opaque), `owner_worker_ref` (Char, diagnostic, mirrors
`call.lease.worker_ref`), `running_since`/heartbeat (Datetime, likely
reusable as `started_at`, already present), `transport_attempted` (Boolean or
Datetime — set by the handler/API-client boundary just before the external
call, so recovery knows whether ambiguity is even possible for this attempt).
**Interaction with existing constraints:** `operation_scope_key`'s
"non-terminal" clearing rule is unaffected — `running` is already
non-terminal. No change to `_store_idempotency_key_uniq`/`_store_operation_
scope_key_uniq`. **Compatibility with Odoo cron:** high — `_drain_one`
already establishes the per-job-commit pattern (PR #163); Option A extends it
to **two** commits per job instead of one, which is a small, well-precedented
change to the same function, not a new execution model.

**[Inference]** Option A directly reuses PR #163's own accepted-progress
pieces (the re-raise-and-recover pattern, the re-lock-and-revalidate
discipline) rather than discarding them — it **moves the first commit
earlier** (right after claim, before the handler) and **adds an attempt
token**, which closes exactly the two gaps §"Option D" identifies, without
otherwise changing the mechanism's shape.

### Option B — dedicated execution-attempt/lease model

**Can the existing `shopify.connector.call.lease` be extended?** No — proven
in §2.1, not assumed. Its lifecycle (admit-before-call → release-after-
reconciliation, both on independent side-cursors, deliberately decoupled
from the main job transaction) ends *before* the outer job-dispatch
transaction's terminal-state commit, which is exactly the window this gap
concerns. Its purpose (a disconnect-controller-readable "is Shopify traffic
in flight for this store" signal) is different in kind from "is this job's
attempt still safely owned and what is its outcome." Repurposing it would
require: (a) creating the lease at claim time instead of admission time
(before we even know a Shopify call will happen — most handlers today make
zero or one call, but this couples an unrelated lifecycle to job-claim
timing); (b) releasing it only at the *outer* transaction's commit instead
of at reconciliation (which would make the disconnect controller's "count of
active leases" reflect local-DB-write time, not "actively on the wire with
Shopify" time — degrading the disconnect controller's own accuracy, since
`DISCONNECT_QUIESCE_TIMEOUT` (15 min) is sized against transport+
reconciliation, not against a job's full local-write tail); (c) adding
outcome/ambiguity/owner-token fields the model does not have and was not
designed to carry. **[Recommendation]** Do not extend `call.lease` — keep it
scoped exactly to what it already correctly does. Introduce a **separate**
concept.

**Design (as its own model or as job-row fields — see §8 for the final
choice):** conceptually the fields the control room's prompt names —
`job_id`, `attempt_key`, `worker_ref`, `state`, `acquired_at`,
`heartbeat_at`, `expires_at`, `replay_safety`, `transport_started_at`,
`transport_completed_at`, `outcome_ambiguity`, `recovery_disposition`.

**Durable ownership / expiry / takeover / crash recovery:** equivalent to
Option A's, expressed as a normalized table instead of columns on `job` —
one row per **attempt** (not per job), so a job that is legitimately retried
three times has three attempt rows, giving a complete audit trail without
overloading `job.log` (which today logs transitions, not attempt-scoped
transport timestamps). **Cleanup:** attempt rows for terminal jobs can be
pruned/archived on a retention policy (§8) independent of the job row itself.
**Auditability:** stronger than Option A's (a dedicated per-attempt table is
easier to query/report on than fields overwritten on each retry of the same
job row). **Cost:** a new model, new ACL, a join for every claim/recovery
read, and a second place (besides `job`) that must be kept consistent — real
complexity for a benefit (full multi-attempt history) that `job.log` already
mostly provides today via its existing `_system_append` transition log
(`from_state`/`to_state`/message per attempt).

**Verdict:** Option B is not wrong, but for the **current** scope (all
shipped handlers are `remote_read_replay_safe`; no mutation handler exists
yet) it is more schema than the problem currently requires. It becomes the
right choice the moment a real mutation domain needs full per-attempt replay
forensics beyond what `job.log` already captures. §8 recommends starting
with Option A's job-row fields (reusing `job.log` for the audit trail) and
treating Option B as the natural next step if/when that need is
demonstrated — not a rejected approach, an explicitly deferred one.

### Option C — durable outbox/attempt-state protocol

**Design:** the local transaction that decides "call Shopify" durably
records that *intent* (with a persisted, reusable idempotency key) atomically
with any local pre-conditions; a relay step performs the actual call and
records the outcome back onto the same durable record; retries re-drive the
relay step using the same persisted key, never re-deciding to attempt.

**Local transaction atomicity:** the strongest of the four options — the
decision to attempt and the attempt's own identity are durable from the
first commit, before any network call. **Remote execution / reconciliation /
remote idempotency keys:** this is the pattern's whole purpose — it is the
natural home for a Shopify `@idempotent` key or a reconciliation-read
strategy per operation. **Ambiguity handling:** first-class, not
retrofitted. **Implementation complexity:** high relative to the other three
— requires either a genuinely separate relay loop (new cron/worker
category) or the *same* dispatcher acting as both writer and relay in two
passes, which is architecturally close to Option B with an extra durability
guarantee at the "decide to call" boundary specifically. **Suitability for
future mutation domains:** the best long-term fit, especially once
fulfillment/inventory-export/refund mutations are authorized, because it
gives every future mutation a uniform place to persist and reuse a
Shopify idempotency key and a uniform reconciliation hook.

**Verdict:** right destination, wrong altitude for *this* decision. §8
recommends designing Option A's schema so it is a **strict subset** of what
Option C would eventually need (an `attempt_id` is a de-facto idempotency-key
seed; `transport_started_at`/`transport_completed_at` are outbox-shaped
fields already) — so choosing Option A now does not foreclose Option C
later; it is Option C's first slice, not a competing design.

---

## 5. Replay-safety registry (Phase 5)

**This is the Layer 1 deliverable — the only registry design change this
revision asks to be implemented next (§9, Immediate Slice 1).**

**[Recommendation]** A new, **core-owned**, fail-closed registry, modeled
directly on the two extension seams this exact file already uses
successfully — `_get_handlers()` (job_type → handler) and
`MANUAL_REVIEW_SUBREASON_SELECTION`/`ERROR_CLASS_SELECTION` (fixed,
shared vocabularies) — rather than inventing a new extension pattern.

- **Where registered:** `shopify_connector_job_dispatch.py` gains
  `_get_replay_policies(self)`, an `@api.model` method returning a
  `job_type -> replay_policy` dict, directly beside (and consulted at the
  same points as) `_get_handlers()`.
- **Which module owns each declaration:** the module that owns the
  `job_type`'s **handler** also owns its replay-policy declaration — same
  module boundary DEC-008 already established for handlers, so there is
  never a case where a handler and its replay policy live in different
  modules and can drift apart.
- **Classic Odoo inheritance:** a domain module extends via
  `_inherit = 'shopify.connector.job.dispatch'`, calling `super()._get_
  replay_policies()` and updating the returned dict with its own new
  `job_type` entries — identical mechanics to `_get_handlers()`.
- **Duplicate-key rejection:** **[Recommendation — a real gap this package
  found, not present in the current code]** `_get_handlers()` today has no
  runtime guard against a naive `.update()` silently overwriting a
  core-owned entry — its docstring *says* "never removing or overwriting a
  core-owned entry" but nothing enforces it. The replay-policy registry
  should **not** repeat that gap: `_get_replay_policies()` (and, as a
  follow-up, `_get_handlers()` itself) should be consulted through a small
  aggregating helper that raises (or a static test that fails) if a
  `job_type` key would be silently overwritten by a later `super()` call in
  the MRO — the same property `_store_idempotency_key_uniq`/
  `_store_operation_scope_key_uniq` already give the job model at the DB
  level, applied here at the Python-registry level.
- **No declared policy:** **[Recommendation, restating §3.3]** the lookup
  helper that reads this registry treats a missing `job_type` key as
  `remote_effect_not_replay_safe` — never as "no policy needed" or
  "assume safe." This is enforced at the **single** call site the dispatcher
  and the recovery/finalize paths both use (not duplicated logic in two
  places, which is exactly how such a default could silently drift).
- **Tests preventing accidental read-safe inheritance:** a static
  registry-completeness test (mirroring `test_job_dispatch.py:519`'s
  existing `assertNotIn('.execute(', content, path)` source-level guard
  pattern) asserts: (a) every `job_type` in `JOB_STATE_SELECTION`'s domain
  (i.e. every registered handler) has an explicit replay-policy entry — no
  silent gaps; (b) no domain module's `_get_replay_policies()` override
  removes or reclassifies a core-owned entry; (c) a new test job_type added
  without a replay-policy entry fails the suite, not just the runtime
  default — so a future mutation handler cannot ship *at all* without an
  explicit, reviewed classification, closing the loop the control room
  named: *"how tests prevent a future mutation handler from accidentally
  using read-safe retry behavior."*

**Current classification (proposed, for control-room acceptance in
DEC-031):**

| `job_type` | Policy | Basis |
| --- | --- | --- |
| `core_readiness_check`, `core_manual_maintenance`, `core_test_connection`, `core_dispatch_selftest` (core diagnostic/self-test) | `local_only` | No Shopify call, or (test-connection) a lifecycle-only call outside the business-job dispatch path entirely. |
| **Current** customer import handler (`shopify_connector_sale`) | `remote_read_replay_safe` | **Explicit, not inferred from the module name** — because it issues only `ConnectorCustomerImport`, a read-only GraphQL query (§2.1), never a mutation. |
| **Current** product import handler (`shopify_connector_product`) | `remote_read_replay_safe` | **Explicit, not inferred** — `ConnectorProductImport` is read-only (§2.1). |
| Task 012 order import | **Not pre-registered by this package.** Not yet implemented, so it gets **no entry now** — defaults to `remote_effect_not_replay_safe` (§3.3) until it lands. When implemented, it **must** declare `remote_read_replay_safe` explicitly, classified **separately** from customer/product, based on its own verified read-only design — never assumed, inherited, or pre-registered by this decision. | Per its own confirmed read-only behavior (§2.2) — not grouped by "it's an import," "it touches orders," or its unrelated "frozen" solver-bound constants. |
| Future inventory export/sync (Task 013/DEC-010) | **No entry until designed** — defaults to `remote_effect_not_replay_safe` (§3.3); **potential future `remote_mutation_idempotent` candidate** once implemented | `inventorySetQuantities`/`inventoryAdjustQuantities` are within Shopify's `@idempotent` surface, **mandatory as of API 2026-04** (§2.4) — but the classification requires the connector to actually persist and reuse a stable key, which does not exist yet; defaults conservative until proven. |
| Future refund domain | **Not a scoped domain at all yet** — no DEC/task document exists (§2.2); defaults to `remote_effect_not_replay_safe` (§3.3) if ever introduced without an explicit registration | `refundCreate` is confirmed `@idempotent`-mandatory as of API 2026-04 (§2.4), the same future-candidate caveat as inventory applies once a real domain is designed. |
| Future fulfillment tracking (Task 014/DEC-011) | **No entry until designed** — defaults to `remote_effect_not_replay_safe` (§3.3) | `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` are confirmed **not** on Shopify's `@idempotent` list (§2.4) — likely a `remote_mutation_reconcile_before_retry` candidate (verification read against FulfillmentOrder status) once designed, never assumed idempotent. |
| Future product export (Task 015) | **No entry until designed** — defaults to `remote_effect_not_replay_safe` (§3.3) | `productSet` is not natively `@idempotent` (§2.4); Task 015's own packet proposes an unproven upsert-by-custom-id mitigation — not a platform guarantee, so it cannot pre-qualify for a safer default class before it is implemented and proven. |

---

## 6. Crash and stale-owner recovery (Phase 6) — Layer 2, deferred

> **Not part of this revision's immediate decision.** Everything in this
> section depends on Option A's committed-`running`+`attempt_id` ownership
> model, which Layer 1 does not build (§0.1, §8). It is retained, unchanged
> from the original package, as the design this project commits to building
> when Layer 2 is triggered — not as a current requirement. For Layer 1's
> current read-only scope, crash/stale-owner behavior is exactly what PR
> #163 already provides (a crashed worker's row simply releases its
> transaction-scoped lock; a future drain re-claims it; no permanently-stuck
> state is possible because nothing is durably marked `running` before the
> handler completes) — materially unchanged from today, and accepted as
> sufficient for read-only jobs, whose only failure mode is a safe re-read.

**[Recommendation, deferred to Layer 2]**, built on Option A's
committed-`running`+`attempt_id` model (§4):

| Scenario | Behavior |
| --- | --- |
| Worker crash **before** transport | `running`+`attempt_id` committed, no `transport_attempted` marker set. Stale-owner sweep (timeout past `running_since`) sees no transport occurred → safe to route back to `queued`/`retry_waiting` **regardless of replay policy** (nothing external was ever attempted). |
| Crash **during** transport | `transport_attempted` was set (just before the call) but no outcome recorded. Sweep treats this identically to "ambiguous" (§3.4) — routes per the job's replay policy (§3.5), never a blind requeue for a non-`remote_read_replay_safe`/non-`remote_mutation_idempotent` job. |
| Crash **after** Shopify response but **before** local commit | Same as "during transport" from the recovery sweep's point of view — it cannot distinguish "sent but no response" from "response received but not yet committed" without a reconciliation read, so both collapse to the same ambiguous-outcome handling. This is intentionally conservative, not a gap: the recovery mechanism does not need to distinguish these two sub-cases to behave safely. |
| PostgreSQL serialization failure **after** transport | The exact PR #163 scenario, now closed: `_recover_after_concurrency_conflict`'s existing re-lock-and-revalidate logic (kept, §4/§8) checks `transport_attempted` (new) before deciding `concurrency_race_conflict`'s auto-retry is safe; if transport was attempted, route through the replay-policy path (§3.5/§7) instead of the blanket auto-retry class. |
| Odoo process termination | Equivalent to "worker crash," any phase — the stale-owner sweep is timeout-driven and does not depend on the terminated process doing anything. |
| Expired execution ownership | `running_since`/heartbeat past the configured bound is the sweep's trigger; expiry alone never auto-finalizes as "succeeded" or "failed" — it only ever hands the job to the replay-policy decision (§3.5). |
| Duplicate cron workers | Structurally prevented at the *claim* step exactly as today (`try_lock_for_update`, unchanged) — two workers cannot both win the initial claim. The new protection is what happens *after* a claim is lost to a rollback (§4), not the claim itself. |
| Multi-server workers | Same protection as duplicate cron workers — `try_lock_for_update`/committed `running` state is a database-level guarantee, not a single-process one; this is exactly why Option A's ownership signal is a **committed row state**, not an in-memory flag. **[Open question, inherited from SRR-09/DEC-025]** genuine multi-server proof remains unperformed for the *claim* layer itself — this package inherits that open item, does not resolve it, and does not need to resolve it to be correct (the ownership protocol described here does not depend on single-server assumptions; it depends only on PostgreSQL's own row-lock/commit guarantees, which are multi-server-safe by construction). |
| Manual retry by an operator | An operator-authorized retry from `blocked_manual_review` is the **one** path allowed to re-attempt a `remote_effect_not_replay_safe` job without an automatic system decision — it is a deliberate, audited, single act (existing `job.log` mechanism), not a new automatic behavior. |

**Explicitly prevented by this design (the control room's named
invariants):**

- **Permanently stuck running jobs:** prevented by the timeout-driven sweep
  — no job can stay `running` forever unattended.
- **Silent automatic replay of an ambiguous mutation:** prevented by §3.3's
  fail-closed default plus §3.5's routing table — there is no code path in
  which an ambiguous, non-idempotent mutation reaches automatic retry.
- **Two active owners:** prevented by `attempt_id` compare-and-swap at
  finalize — a second "owner" can only exist if it wins a **fresh** claim
  after the first `attempt_id` is invalidated by the sweep, which is a
  sequential handoff, not concurrent ownership.
- **Ownership takeover without expiry/validation:** the sweep only acts
  after the configured timeout, and only ever transitions via the same
  re-lock-and-revalidate discipline PR #163 already established (§2.1) —
  never a bare `write()` on an unlocked row.
- **Stale owner finalizing after takeover:** the `attempt_id` compare at
  finalize rejects a write from an `attempt_id` the sweep has already
  superseded — a returning stale worker's finalize attempt fails closed
  (routes to the same manual-review path as any other post-hoc ambiguity,
  never silently overwrites the sweep's disposition).
- **Cleanup deleting another worker's active attempt:** cleanup/retention
  (§8) only ever acts on **terminal** job states; a `running` job (with a
  currently-valid `attempt_id`) is never a cleanup candidate, mirroring
  `_sweep_quiescing_business_jobs`'s own existing "never touch a
  claimed/running row" discipline (§2.1).

---

## 7. State and error mapping (Phase 7)

> **Layer 1 result: no new field, no new error class, needed now.** For
> every `job_type` Layer 1 actually declares (`local_only`,
> `remote_read_replay_safe`), the existing vocabulary is fully sufficient —
> see the first four rows below. The one genuinely new vocabulary need
> identified in the original package (`transport_attempted`, discussed
> below) only matters once a mutation handler exists that can reach an
> ambiguous post-transport state; no such handler exists, so it is Layer 2,
> deferred alongside Option A (§0.1, §8) — not proposed for implementation
> now.

**[Recommendation]** Mapped to the **existing** accepted vocabulary
(`JOB_STATE_SELECTION`, `ERROR_CLASS_SELECTION`,
`MANUAL_REVIEW_SUBREASON_SELECTION`) wherever it is sufficient, with the
smallest possible additive change where it is not:

| Outcome | State / error mapping | Vocabulary sufficient? |
| --- | --- | --- |
| Safe read replay | `retry_waiting` / existing auto-retry classes, unchanged | Yes |
| Retryable pre-transport database conflict | `retry_waiting` / `concurrency_race_conflict` (unchanged, matches today's *intended* meaning of the class) | Yes |
| Ambiguous post-transport **read** | `retry_waiting` / `concurrency_race_conflict` — safe, because a read has no side effect to duplicate (§3.1) | Yes |
| Ambiguous post-transport **mutation** | `blocked_manual_review` / `manual_review_subreason='duplicate_risk'` | **Yes — `duplicate_risk` already exists** (§2.1); no new value needed |
| Remote idempotent mutation retry | `retry_waiting` / a **new, narrower** error class or a job-level flag distinguishing "retry using the persisted Shopify key" from generic `concurrency_race_conflict` retry (see below) | **[Open — smallest additive change needed]** |
| Reconciliation-required mutation | **[Open — smallest additive change needed]**, see below | No |
| Duplicate risk | `blocked_manual_review` / `duplicate_risk` | Yes |
| Exhausted retry budget | `failed_final`, unchanged (`_schedule_retry_or_fail`'s existing budget logic) | Yes |
| Stale execution ownership | Routed through the sweep to whichever of the above applies (never its own terminal state) | Yes |
| Operator-authorized retry | Existing manual-retry code path (same as any `blocked_manual_review`/`failed_retryable` recovery today) | Yes |

**[Recommendation — the one genuinely new vocabulary need]** The existing
16-class `ERROR_CLASS_SELECTION` is **insufficient** in exactly one place:
distinguishing, at the point a concurrency failure is caught, whether
`concurrency_race_conflict` means "safe, pre-transport" (today's implicit
assumption) or "unsafe, post-transport, ambiguous mutation" (PR #163's
finding). Two additive options, **smallest first**:

1. **[Preferred]** Do not add a 17th error class. Add a single **job-level
   boolean/timestamp field**, `transport_attempted` (§4/§6), set by the
   API-client boundary immediately before any mutation call. `_recover_
   after_concurrency_conflict` and the stale-owner sweep both consult this
   field — **not** a new `error_class` — to decide whether
   `concurrency_race_conflict` may still auto-retry (transport never
   attempted) or must instead route through `blocked_manual_review`/
   `duplicate_risk` (transport attempted, mutation, no idempotency). This
   changes **behavior**, not **vocabulary** — `error_class` and
   `manual_review_subreason` stay exactly as accepted today.
2. **[Fallback, only if the control room prefers explicit vocabulary]** Add
   one new error class, e.g. `concurrency_race_conflict_post_transport`, as a
   sibling of `concurrency_race_conflict` in the manual-review family. This
   is a strictly larger change (new DB value, new taxonomy row, DEC-009
   amendment) for the same behavioral outcome Option 1 achieves with a
   boolean field — **not recommended** unless reviewers want the ambiguity
   to be independently visible in `error_class` reporting/dashboards without
   inspecting `transport_attempted` alongside it.

`remote_mutation_idempotent` retry and `remote_mutation_reconcile_before_
retry` are **not yet reachable** (no mutation handler exists), so this
package does **not** propose new states/classes for them now — per
CLAUDE.md's "no hypothetical future requirements," the exact reconciliation-
read state machine is correctly deferred to the implementation session that
ships the first real mutation domain (§9, slice 6), which will have a
concrete Shopify operation to design against instead of a hypothetical one.
This is recorded as an explicit future decision, not silently dropped.

---

## 8. Recommendation (Phase 8)

### 8.1 Layer 1 recommendation — implement now

**[Recommendation, routed to DEC-031 for control-room acceptance]**

**Recommended immediate architecture: the Phase-5 replay-safety registry,
and nothing else.** Three declared classes (`local_only`,
`remote_read_replay_safe`, `remote_effect_not_replay_safe`); explicit
declarations for the core diagnostic/self-test handler and the current
customer/product import handlers; a fail-closed default for everything
else; consulted by PR #163's existing `_recover_after_concurrency_conflict`
so a future mutation handler can never silently inherit today's read-safe
retry behavior. **PR #163's mechanism (Option D) is otherwise kept exactly
as shipped** — its rollback/reset/re-lock/revalidate/bounded-retry
discipline is accepted, unmodified, for the current read-only scope (§0.1).

**Why this is sufficient for current UAT scope.** Every handler that exists
today is read-only (§2.1, §5): replaying the underlying Shopify query has no
side effect to duplicate, the failed Odoo transaction is rolled back, and
importer duplicate prevention/bindings/uniqueness constraints remain the
local data-integrity protection — so there is no case where PR #163's
existing worker-B-wins or scheduled-replay behavior (§4, Option D) can
produce a duplicate Shopify write. The only thing genuinely missing is a
**structural guarantee that stays true as new handlers are added** — which
is exactly what the registry's fail-closed default provides, at zero schema
cost.

**Why no schema change, no new model, no new cron, is required now.**
Nothing in Layer 1 needs durable cross-transaction ownership signals
(`attempt_id`/`owner_worker_ref`), transport-ambiguity tracking
(`transport_attempted`), or a stale-owner sweep — those exist to protect a
**mutation** from an ambiguous post-transport replay, and no mutation
handler is implemented. Building them now, before a mutation handler exists
to need them, would be exactly the kind of work-for-a-hypothetical-future-
requirement `CLAUDE.md` cautions against.

**Exact change for the future implementation session (not authorized
here — see §9, Immediate Slice 1):** `shopify_connector_job_dispatch.py`
gains `_get_replay_policies()` (§5) plus a small no-silent-overwrite guard,
and `_recover_after_concurrency_conflict` consults it before routing
`concurrency_race_conflict` to auto-retry.

**Modules affected:** `shopify_connector_core` (the registry seam and the
recovery-path consult), `shopify_connector_product`/`shopify_connector_sale`
(one registry-entry registration each — no call-site behavior change).
No other module. `Shopify-connector`, PR #150, PR #151 are untouched.

**Migration, performance, security implications:** none — no schema change,
no new commit boundary, no new persisted field.

**Test strategy:** see §9, Immediate Slice 2.

**Rollback strategy:** remove the registry seam and its call site; recovery
falls back to today's `AUTO_RETRY_ERROR_CLASSES`-only behavior — a safety
*reduction* for any handler added after the registry ships, not a risk to
anything shipped today (no mutation handler exists to regress).

### 8.2 Layer 2 recommendation — deferred, reopen on first Shopify mutation

**[Recommendation, retained for a future session — not routed to DEC-031 for
acceptance now]**

**Recommended future architecture: Option A** (committed `running` +
`attempt_id` ownership on the `job` row itself, timeout-driven stale-owner
sweep, replay-policy-registry-gated recovery), built on top of — not
replacing — PR #163's mechanism, plus the §7 `transport_attempted` field.
This is unchanged from the original package's full analysis (§4, §6, §7)
and remains the smallest robust solution *for that later scope*. It is
recorded here so a future implementation session does not have to re-derive
it — recording it is not, itself, a current requirement or approval.

**Explicit reopening trigger.** This layer is reopened **by name** — never
silently assumed, never bundled into read-only work — the moment any of the
following is authorized as an implementation domain: inventory export
(Task 013/DEC-010), fulfillment/tracking update (Task 014/DEC-011), product
export (Task 015), refund creation, or any other Shopify mutation. Until
then, Layer 2 does not block current product, customer, or order read-only
UAT.

**Exact models/fields/hooks likely required, when triggered** (unchanged
from the original package):

- `shopify.connector.job`: `attempt_id` (Char, opaque), `owner_worker_ref`
  (Char), `transport_attempted` (Boolean, default False).
- `shopify.connector.job.dispatch`: a new `_sweep_stale_running_jobs()`
  cron-target method; the `_drain_one`/`_recover_after_concurrency_conflict`
  two-commit split described in §4/§6/§7.
- A new scheduled action (`ir.cron`) for the stale-owner sweep, mirroring
  the disconnect-quiescence controller's existing XML pattern.
- API-client/dispatcher boundary: exactly where `transport_attempted` is
  set — open question, §11.

**Migration, performance, security, test, rollback implications when
triggered:** unchanged from the original analysis — additive-only fields,
one extra commit per dispatched job, opaque non-secret diagnostic values,
independent-connection tests proving Worker B cannot execute a real handler
for a job Worker A still durably owns, additive/inert rollback. This detail
is retained in §4/§6 above, not repeated here.

---

## 9. Implementation slicing (Phase 9, revised)

**No implementation prompt is issued by this session.** This revision
replaces the original package's nine-slice future sequence with two
immediate slices (Layer 1) plus one deferred-roadmap paragraph (Layer 2).
The original nine-slice sketch is not reproduced here — its content is
superseded by this section for planning purposes; nothing in it is lost,
since Layer 2 (§8.2) already records the exact models/fields/hooks that
sequence would build, for whenever it is triggered.

### Immediate Slice 1 — Minimal replay-policy correction

*Objective:* implement the fail-closed registry (§5); declare
`local_only`/`remote_read_replay_safe`/`remote_effect_not_replay_safe` for
the core diagnostic/self-test handler and the current product and customer
import handlers; adapt `_recover_after_concurrency_conflict` to consult the
policy before routing `concurrency_race_conflict` to auto-retry; preserve
current read-only bounded retries exactly as PR #163 ships them; prevent any
undeclared or future remote-effect handler from automatic replay by
construction (fail-closed default).

*Allowed files:* `addons/shopify_connector_core/models/shopify_connector_
job_dispatch.py` and its tests; one registration point each in
`shopify_connector_product`/`shopify_connector_sale` and their tests.

*Forbidden files:* any new database field, model, cron, XML, or migration;
`shopify_connector_job.py` schema; `call_lease.py`; `api_client.py`; any
domain-module importer logic (call sites unchanged).

*Prerequisites:* DEC-031 accepted by control room.

*Acceptance criteria:* every declared `job_type` matches §5's table; an
undeclared `job_type` provably routes to `remote_effect_not_replay_safe`
(fail-closed); no observable retry-behavior change for any currently shipped
handler.

*Tests:* a registry-completeness static test (§5); a unit test proving the
fail-closed default for an undeclared `job_type`; existing customer/product/
core lifecycle and concurrency-recovery tests unchanged and green.

*Rollback:* remove the registry seam and its call site; recovery reverts to
today's `AUTO_RETRY_ERROR_CLASSES`-only behavior (a safety reduction for
handlers added after this slice, no risk to anything shipped today).

*Definition of done:* registry exists, is consulted at the one call site
that matters, and the completeness test fails the build for any
undeclared/future remote-effect handler.

### Immediate Slice 2 — Exact-head runtime validation

*Objective:* validate Immediate Slice 1 on a real Odoo.sh build at its exact
committed head.

*Validate:* core suite; product suite; customer suite; three genuine
lifecycle repetitions; read-only concurrency-retry behavior (PR #163's
existing recovery path, now registry-gated); unknown-handler fail-closed
behavior; zero residue; no secret leakage; no live Shopify mutation
performed by any test.

*Prerequisites:* Immediate Slice 1 merged.

*Acceptance criteria:* all listed suites green at the exact validated head;
independent residue audit clean; no behavior change observed for any
currently shipped job type.

*Rollback:* per Immediate Slice 1's rollback (unchanged).

*Definition of done:* exact-head evidence recorded, matching this project's
established evidence bar (e.g. Task 011B's build-to-commit-verified
pattern).

### Deferred roadmap — Layer 2, one future architecture gate

Option A and the full mutation-hardening architecture (§8.2) are recorded as
**one future architecture gate**, required before the **first** Shopify
mutation domain (inventory export, fulfillment/tracking update, product
export, refund creation, or any other Shopify write) is authorized for
implementation. This roadmap is **not** broken into current mandatory
sessions, is not scheduled, and is not a prerequisite for Immediate Slices 1
or 2. It is reopened by name, as a new control-room decision, only when a
specific mutation domain is proposed for implementation.

---

## 10. Self-critique (Phase 11)

> **Layer note.** This self-critique is unchanged from the original
> package. Most of the scenarios below (Worker B winning, lease
> expiry/takeover, duplicate cron workers under a mutation) describe Option A
> — Layer 2, deferred (§0.1, §8.2) — and are not claims about what Layer 1
> closes today. The scenarios that **are** live for Layer 1's current scope
> are marked "[Layer 1]" below; they were already true under PR #163 alone
> and are unaffected by this revision, because replaying a read has no
> duplicate-effect risk to begin with.

Tested against each control-room scenario. **No claim of "exactly once" is
made anywhere in this package** — delivery is **effectively-once by
construction for idempotent-capable classes, and at-most-once for automatic
system behavior on everything else**, with a human required to close the
loop when automation cannot safely do so. That distinction is deliberate,
not a hedge.

- **Worker B winning immediately after rollback:** **Closed** by Option A —
  once `running`+`attempt_id` is committed *before* the handler runs,
  Worker B's claim query structurally cannot select the row. (Under Option
  D/today, this is **open** — restated for contrast, not re-accepted.)
- **Remote request completed but response lost:** **Not closed, by
  design — routed to human reconciliation.** No mechanism in this package
  (or any of the four options) can *know* Shopify's true state without
  either a reconciliation read or an operator checking Shopify directly.
  §3.5/§7 route this to `blocked_manual_review`/`duplicate_risk` rather than
  claiming to resolve it automatically. This is the honest limit of the
  design, stated plainly: **the system cannot achieve "exactly once" against
  an external system with no idempotency guarantee and no reconciliation
  read — it can only guarantee it never silently guesses.**
- **Remote response received but local transaction rolled back:** Same
  limit as above — `transport_attempted=True` with no confirmed local
  outcome is definitionally ambiguous; §6's table intentionally collapses
  this into the same handling as "crash during transport" rather than
  claiming a distinction it cannot actually make.
- **Mutation with no idempotency support:** **Handled** — this is exactly
  `remote_effect_not_replay_safe`'s reason to exist (§3.2, §5).
- **Duplicate cron workers / worker crash:** **Closed** for the ownership
  question (§6); **not** re-closed for the underlying claim-layer
  multi-server question, which remains the pre-existing SRR-04/SRR-09 open
  item this package explicitly does not claim to resolve (§6, §9 slice 7).
- **Lease expiry and takeover / stale owner returning after takeover:**
  **Closed** by the `attempt_id` compare-and-swap (§4/§6) — a returning
  stale owner's finalize fails closed.
- **Retry exhaustion:** **Unchanged, already handled** by
  `_schedule_retry_or_fail`'s existing bounded-attempt/24-hour-window logic
  (§7) — this package does not touch retry-budget accounting.
- **Disconnect during any phase:** **Composes, not yet unified** — the
  disconnect-quiescence controller (§2.1, Slice 2A) and this package's
  ownership sweep are two **independent** timeout-driven mechanisms that
  both consult the same job row but were not designed together. **[Open
  question, honestly flagged]** a job that is simultaneously stale-running
  (this package's concern) *and* the last thing blocking a store's
  disconnect-quiescence (the existing controller's concern) has not been
  jointly analyzed by either design — `_sweep_quiescing_business_jobs`
  already correctly never touches a `running`/claimed row (§2.1), so there
  is no *direct* conflict, but the **interaction** (does the disconnect
  controller's timeout and this package's stale-owner timeout ever need to
  be coordinated, e.g. so a disconnecting store's stuck job is recovered
  *before* `DISCONNECT_QUIESCE_TIMEOUT` fires a `timed_out` escalation
  against it) is not analyzed here and is logged as an open question for
  the implementing session (§9 slice 4/9), not silently assumed fine.
- **Current read-only queries:** **Unaffected in observable behavior**,
  strictly improved in crash-recovery mechanics (§8).
- **Future Shopify mutations:** **Not endangered** — fail-closed default
  (§3.3/§5) is the load-bearing guarantee here, verified structurally (a
  static test, not a promise) rather than by inspection alone (§5, §9
  slice 6).

**Guarantee this design explicitly cannot provide, stated for the record:**
it cannot make a **non-idempotent** Shopify mutation safe to auto-retry
without either (a) Shopify providing a reconciliation mechanism for that
specific operation, or (b) a human confirming real-world state. No schema,
lock, or lease can manufacture idempotency the platform does not offer. This
package's contribution is ensuring the system **never pretends otherwise** —
every ambiguous case reaches a human, precisely once, with a name
(`duplicate_risk`) already in the accepted vocabulary, rather than being
silently replayed.

---

## 11. Open questions (carried into DEC-031 and the handoff)

None of the following blocks acceptance of the Layer 1 semantic
contract/registry (§0.1, §5, §8.1) itself. Items 1–2, 5–6 are Layer 2
questions — they matter only once Layer 2 is reopened (§8.2) and are
recorded now so that future session does not re-derive them. Item 3 (Layer
2) and item 4 (either layer, non-blocking) are noted for the same reason.

1. **[Layer 2]** Whether `transport_attempted` should be set by the
   dispatcher generically or by each handler explicitly (§8.2) —
   recommended generic, not decided here.
2. **[Layer 2]** Whether the smallest-additive-change error-mapping choice
   (§7, a boolean field) or the fallback (a 17th error class) is preferred
   by the control room.
3. **[Layer 2]** Interaction between the disconnect-quiescence controller's
   timeout and the future stale-owner sweep's timeout (§6) — not jointly
   analyzed.
4. **[Either layer, non-blocking]** A full refresh of official Shopify
   mutation-idempotency/reconciliation documentation against the live
   `shopify.dev` docs (§2.4) — recommended before any specific future
   mutation domain is designed in implementation detail.
5. **[Layer 2]** Whether Option B (a dedicated attempt table) should be
   revisited once a real mutation domain is authorized and needs full
   per-attempt audit history beyond `job.log` (§4) — explicitly deferred,
   not rejected.
6. **[Layer 2]** The exact reconciliation-read state machine for a future
   `remote_mutation_reconcile_before_retry` sub-class (§3.2, §7) —
   deliberately deferred until a concrete future mutation handler exists to
   design it against.

---

## References

Repository (all at `63d10fb465a26189fa463f9c7ac580da6a931c5c` unless a PR
diff is named; access: Accessible, local working tree + `git show`,
2026-07-15):

- `addons/shopify_connector_core/models/shopify_connector_job.py`
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (base + PR #163 diff, `63d10fb…655e1cd`)
- `addons/shopify_connector_core/models/shopify_connector_call_lease.py`
- `addons/shopify_connector_core/models/shopify_connector_api_client.py`
- `addons/shopify_connector_core/models/shopify_connector_store.py`
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
- [`../04-decisions/DEC-009-error-retry-idempotency-strategy.md`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)
- [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md)
- [`sync-engine-architecture-gate.md`](./sync-engine-architecture-gate.md)
- [`disconnect-quiescence-remediation-analysis.md`](./disconnect-quiescence-remediation-analysis.md) (AR-047)
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md) (AR-047 entry)
- [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md) (SRR-03, SRR-04, SRR-09)
- [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) (checked, RA-001…RA-024, none blocking)
- [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md)
- [`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md)
- [`task-012-order-import-decision-closure.md`](./task-012-order-import-decision-closure.md)
- [`../07-implementation-plan/task-core-r2-slice-2b-handoff.md`](../07-implementation-plan/task-core-r2-slice-2b-handoff.md)
- PR #163 (`AdamsOdoo/Adams#163`) — body and diff, GitHub, accessed 2026-07-15.
- PR #150 (`AdamsOdoo/Adams#150`), PR #151 (`AdamsOdoo/Adams#151`) — state
  verification only, GitHub, accessed 2026-07-15.

Official Odoo 19 source — independently re-verified by this session
(access: Accessible, `raw.githubusercontent.com`/`github.com/odoo/odoo`
`19.0` branch + `odoo.com/documentation/19.0`, 2026-07-15; see §2.3 for full
excerpts):

- `github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py` —
  `_process_jobs_loop` (215-238), `_run_job` (457-568), `_callback`
  (671-695), `_acquire_one_job` (308-386), `_commit_progress` (845-888).
- `github.com/odoo/odoo/blob/19.0/odoo/orm/models.py` — `try_lock_for_update`
  (5591-5622), `lock_for_update` (5563-5589).
- `github.com/odoo/odoo/blob/19.0/odoo/orm/environments.py` —
  `Environment.reset`/`Transaction.reset`/`Transaction.clear` (59-62,
  600-618).
- `github.com/odoo/odoo/blob/19.0/odoo/orm/registry.py` — `reset_changes`
  (1142-1152).
- `github.com/odoo/odoo/blob/19.0/odoo/service/model.py` — `retrying()`
  (160-241), `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` (28-30).
- `odoo.com/documentation/19.0/developer/reference/backend/actions.html#writing-cron-functions`
- `odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#never-commit-the-transaction`
- `postgresql.org/docs/current/errcodes-appendix.html` (SQLSTATE cross-check)
- Prior in-repo citation set (AR-047,
  `disconnect-quiescence-remediation-analysis.md`) — consistent with, and
  now superseded in precision by, the above independent re-verification.

Official Shopify API facts — independently re-verified by this session
(access: Accessible except where marked Partial, `shopify.dev`, 2026-07-15;
see §2.4 for full excerpts):

- `shopify.dev/docs/api/usage/implementing-idempotency`,
  `.../idempotent-requests` — `@idempotent` directive scope, `idempotencyKey`
  input field.
- `shopify.dev/changelog/making-idempotency-mandatory-for-inventory-adjustments-and-refund-mutations`
  — 2026-04 mandatory-idempotency changelog.
- `shopify.dev/docs/api/admin-graphql/latest/mutations/orderCreate` —
  spot-check confirming no idempotency support.
- `shopify.dev/docs/api/admin-graphql/latest/objects/bulkoperation`,
  `.../usage/bulk-operations/imports` — bulk-operation reconciliation
  identifiers.
- `shopify.dev/docs/api/usage/response-codes` — checked directly, confirmed
  silent on request-ID/post-disconnect recovery.
- `shopify.dev/docs/api/usage/limits`, `.../admin-rest/usage/rate-limits` —
  cost-based throttling, `THROTTLED`-in-200-OK behavior.
- Prior in-repo citation set (`ar006-error-retry-idempotency-decision-brief.md`,
  `shopify-official-api-notes.md`, underlying DEC-004/DEC-009/DEC-010) —
  consistent with, and now sharpened by, the above independent
  re-verification.
