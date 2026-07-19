# Wave 3 Stage 0 — DEC-031 Layer 2 Core Substrate Implementation Packet

> **Status: ACCEPTED — IMPLEMENTATION PROMPT NOT YET ISSUED.** Cut from
> [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) (status:
> ACCEPTED — CONTROL-ROOM GATE A, PR #177 comment
> [`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)).
> **Acceptance of this packet does not itself authorize implementation.**
> Implementation opens only when the companion locked Sol prompt
> ([`../06-prompts/sol-wave-3-stage-0-locked-prompt.md`](../06-prompts/sol-wave-3-stage-0-locked-prompt.md))
> is separately, explicitly issued to a Sol session — ready for that
> separate control-room issuance only after PR #177 merges and the new
> integration SHA is verified.
>
> **2026-07-19 correction notice.** Per the final consolidated
> Sessions-2-and-3 control-room ruling (PR #177 comment
> [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)),
> every architecture item this packet previously carried as a hard stop is
> now resolved — see §17 below and DEC-036 Part 3/5/6. Remaining §17 items
> are Stage 0 **merge-acceptance criteria** (implementation proof, tunable
> constants, or narrow verification steps), not preconditions to beginning
> implementation.
>
> Instantiates the 7-field standard of
> [`implementation-task-template.md`](../06-prompts/implementation-task-template.md)
> for **Wave 3 Stage 0**, per
> [`wave-3-definition-of-ready.md`](wave-3-definition-of-ready.md) §4.

---

## 1. Objective

Implement the durable, core-owned, domain-agnostic mutation-safety
substrate that every future Shopify-mutation domain (inventory — Task 013;
fulfillment — Task 014; product export — Task 015) wraps every mutation
call through: a persisted mutation-attempt record, a stale-owner sweep, a
per-domain reconciliation-strategy registry, and the C1/C2/NET/C3
transaction-boundary protocol — proven with genuine (not simulated)
multi-connection concurrency and OS-process-level crash-injection evidence
across four distinct proof-environment layers (§22).

## 2. Explicit non-goals

- **No inventory-domain implementation.** No `shopify_connector_inventory`
  addon, no location mapping, no `inventorySetQuantities` call site, no
  Task 013/013B logic of any kind.
- **No Shopify mutation of any kind.** This packet's own tests may issue
  Shopify **reads** only if a genuine dev-store reconciliation-adapter test
  is built to prove the generic registry contract (§8) — never a mutation.
- No fulfillment or product-export scaffolding.
- No UI/screen work.
- No change to the Layer 1 replay-policy registry's existing three-class
  vocabulary or fail-closed default (extended, never modified).
- No change to any currently-shipped read-only handler's observable
  behavior.
- **Stage 0 remains domain-neutral** (DEC-036 D2 restated): a synthetic
  core mutation self-test adapter (`mutation_dispatch_selftest`) and a
  synthetic reconciliation handler
  (`mutation_dispatch_selftest_reconcile`) prove the generic wrapper,
  crash windows, and registry — no inventory API object, no Shopify
  mutation, is used to prove Stage 0 itself.

## 3. Allowed files (exhaustive)

- `addons/shopify_connector_core/models/shopify_connector_job.py` —
  additive fields only (DEC-036 D1): `current_attempt_token`,
  `owner_worker_ref`, `running_since`, `reconciliation_pending_until`
  (D13), `mutation_attempt_id` (D14, `Many2one`-restrict, on the
  reconciliation-job side).
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  — the C1/C2/NET/C3 protocol for mutation job types (D19), C2 on a
  dedicated side cursor (D20); the widened
  `_recover_after_concurrency_conflict` claimability branch (D25); the
  `ShopifyQuiescedError` handling branch (D28/D29); the
  `_get_reconciliation_strategies()` registry seam (D15) and its runtime
  fail-closed gate (D16) — **owning model bindingly this file** (D15,
  RESOLVED 2026-07-19, corrected per PR #177 comment 5014806430 item 3): no
  new dedicated registry model file is authorized for Stage 0.
- `addons/shopify_connector_core/models/shopify_connector_job_actions.py`
  — narrow scope only (DEC-036 D11): the `duplicate_risk`-refusal guard
  added to both pre-existing generic actions
  (`action_resolve_manual_review`, `action_manual_retry`) so neither can be
  used to bypass the Administrator-only `action_resolve_mutation_attempt`
  override.
- `addons/shopify_connector_core/models/shopify_connector_api_client.py` —
  **new to the allowed list, 2026-07-19** (DEC-036 D16 extension): the
  runtime fail-closed guard — a GraphQL document containing a `mutation`
  operation cannot be sent without a valid Layer 2 attempt context/token.
- `addons/shopify_connector_core/models/shopify_connector_store.py` —
  **new to the allowed list, 2026-07-19** (DEC-036 D28): the narrow
  disconnect/quiescence awareness change to `_finalize_disconnect_timed_out`
  (check for unresolved mutation attempts / pending reconciliation jobs
  before clearing credentials), and the force-disconnect path's
  Administrator-only/mandatory-reason/audit extension.
- **New file** `addons/shopify_connector_core/models/shopify_connector_mutation_attempt.py`
  — the `shopify.connector.mutation.attempt` model (DEC-036 D2/D3/D4/D5/D6/D7/D8/D9/D10/D17).
- **New file** `addons/shopify_connector_core/models/shopify_connector_stale_owner_sweep.py`
  (or added to `job_dispatch.py` if smaller — implementer's choice,
  disclosed either way) — `_sweep_stale_running_jobs()` (D26/D27).
- `addons/shopify_connector_core/security/ir.model.access.csv` — four new
  ACL rows for `mutation.attempt` (D30), current four-role model.
- `addons/shopify_connector_core/security/shopify_connector_security.xml`
  — no new group; the Admin-only resolution-override action (D11) uses the
  existing `group_shopify_connector_admin`.
- **New file** `addons/shopify_connector_core/data/shopify_connector_stale_owner_sweep_cron.xml`
  — the new cron record, `noupdate="1"` (D26/D27).
- `addons/shopify_connector_core/models/__init__.py`,
  `addons/shopify_connector_core/__manifest__.py` — version bump, new file
  registration, new data file registration (D33).
- **New test files** under `addons/shopify_connector_core/tests/` — see §19
  for the exact required set.
- `docs/07-implementation-plan/wave-3-stage-0-layer-2-packet.md` (this
  file — validation-record updates only, no scope change).
- A new `docs/05-qa/task-stage0-layer2-validation-results.md` (created at
  implementation time, not by this packet).

## 4. Forbidden files

Everything outside §3. Specifically: `shopify_connector_product/**`,
`shopify_connector_sale/**`, `adams_base/**`; any file under a future
`shopify_connector_inventory/**` (does not yet exist and must not be
created by this packet); `shopify_connector_store_settings.py`,
`shopify_connector_binding_mixin.py`, `shopify_connector_call_lease.py`,
`shopify_connector_job_enqueue.py` (read and cited extensively by this
session's audit; **not modified** by Stage 0 — D29's credential-snapshot
field lives on the new attempt model, not on these files); any Layer 1
replay-policy-registry *behavior* change (only new domain declarations, via
the existing extension seam, are ever in-scope for a *future* domain,
never Stage 0 itself since Stage 0 registers no domain); CI/workflow
files; protected references.

## 5. `shopify.connector.mutation.attempt` — exact schema

Per DEC-036 D2 (RESOLVED), D3, D5–D9, D10, D17, D18:

| Field | Type | Notes |
|---|---|---|
| `job_id` | `Many2one('shopify.connector.job', required=True, index=True, ondelete='restrict')` | **RESOLVED** — not Integer; single-sequential-owner write pattern mirrors `job_log.job_id`'s safe FK precedent |
| `attempt_token` | Char (UUID), required, unique | matches the job-row's `current_attempt_token` for this attempt; **renamed from `attempt_id`** |
| `mutation_domain` | Char, required, indexed | **RESOLVED** — registry-validated, fail-closed against the reconciliation/mutation registry; not a Selection of either kind (DEC-036 D35) |
| `store_id` | `Many2one`, `related='job_id.store_id'`, stored, indexed, readonly | D3; exact source field name on `job` unconfirmed, verify before implementing |
| `expected_connection_generation` | Integer | snapshotted at C2 (D18/D29) |
| `expected_store_identity` | Char | `myshopifyDomain` snapshotted at C2 (D18, new) |
| `remote_mutation_intent` | Char/JSON | identifiers only, D7 allowlist |
| `preconditions_snapshot` | JSON | allowlisted per domain matrix row, D7 |
| `business_intent_fingerprint` | Char (SHA-256) | D5 — stable business intent, excludes CAS/idempotency mechanics |
| `exact_request_fingerprint` | Char (SHA-256) | D5 — exact transmitted request, **includes** `changeFromQuantity` and the idempotency key |
| `shopify_idempotency_key` | Char (UUID), nullable | D6 |
| `idempotency_valid_until` | Datetime, nullable | D6 — Shopify's 24h window minus a configurable local safety margin |
| `transport_attempted` | Boolean, default False | D1/D23 — lives on this row only, never duplicated on `job` |
| `observed_outcome` | Selection (4): `pending`/`succeeded`/`failed_clean`/`uncertain` | D9/D10 — machine-observed, **immutable once it leaves `pending`** |
| `resolution_disposition` | Selection (2), nullable: `applied`/`not_applied` | D10/D11 — orthogonal to `observed_outcome`, never overwrites it |
| `resolution_source` | Selection (2), nullable: `reconciliation_read`/`manual_admin` | D10/D11, new field |
| `resolution_reason` | Text, mandatory when `resolution_disposition` set | D11 |
| `resolution_uid` | `Many2one` `res.users` | D11 |
| `resolution_at` | Datetime | D11 |
| `inconclusive_reconciliation_count` | Integer, default 0 | D17 — per-attempt scope, **resolved sufficient** |
| `remote_evidence_refs` | JSON | D8, exact shape below |
| `created_at`, `transport_at`, `resolved_at` | Datetime | commit-point timestamps |

`remote_evidence_refs` shape (D8): `{remote_gids: [...], user_errors:
[{code, field}], http_status, graphql_error_codes: [...], throttle_status:
{maximumAvailable, currentlyAvailable, restoreRate} | null}`.

**Effective-disposition helper (new, D10):** a pure function reading both
`observed_outcome` and `resolution_disposition`, never mutating either:
`succeeded` → applied; `failed_clean` → not_applied; `uncertain` +
`resolution_disposition='applied'` → applied; `uncertain` +
`resolution_disposition='not_applied'` → not_applied; `uncertain` +
`resolution_disposition` null → unresolved. This is the **only** field any
retry-eligibility or job-completion logic may read for that purpose —
never `observed_outcome`/`resolution_disposition` directly.

Uniqueness: `(job_id, attempt_token)` via `models.UniqueIndex` — **never**
`_sql_constraints` (confirmed silently inert under Odoo 19).

Job-row additive fields (D1): `current_attempt_token`, `owner_worker_ref`,
`running_since`, `reconciliation_pending_until` (D13), `mutation_attempt_id`
(D14, `Many2one`-restrict, reconciliation-job side, **required for
reconciliation jobs**). All join `PROTECTED_JOB_FIELDS`.
`transport_attempted` is **not** duplicated on `job` — it lives on
`mutation.attempt` only.

## 6. State and transition tables

Full detail: DEC-036 Part 3 (D10) and Part 5. Summary:

- **Layer J (Job):** unchanged 10-value `shopify.connector.job.state`
  machine — zero new states, zero new transitions.
- **`observed_outcome`:** `mutation.attempt.observed_outcome`, closed
  4-value, machine-observed only, **immutable once it leaves `pending`**.
- **`resolution_disposition`/`resolution_source`:** nullable, orthogonal,
  set only by a reconciliation-read verdict or the Admin-only override —
  **never** by direct assignment elsewhere, and never overwriting
  `observed_outcome`.

Transition sequence: attempt creation (`pending`) → direct response
(`succeeded`/`failed_clean`/`uncertain`, **terminal and immutable**) →
`uncertain` triggers reconciliation (job-level `reconciliation_pending_until`
set, linked reconciliation job created via `mutation_attempt_id`) → verdict
applied/not-applied/inconclusive sets `resolution_disposition`/
`resolution_source='reconciliation_read'` (never touches `observed_outcome`)
→ inconclusive count increments (row-locked) → cap (N=3, per-attempt scope,
resolved sufficient) trips to `blocked_manual_review`/`duplicate_risk` →
Admin-only override sets `resolution_disposition`/`resolution_source=
'manual_admin'` (still never touches `observed_outcome`) → job resumes via
the existing sanctioned `blocked_manual_review→queued` transition, now with
both pre-existing generic actions refusing this job class. Store-identity
mismatch bypasses the normal flow entirely, routing to
`blocked_manual_review`/`store_identity_mismatch`, never retried. A
`failed_clean` DEC-009 retry always creates a **new** attempt row with a
new `attempt_token` — the old row's `observed_outcome`/
`resolution_disposition` are terminal and permanently immutable.

## 7. Transaction/commit protocol

Full detail: DEC-036 Part 3 (D19/D20/D21/D22); design-doc §11 (corrected
2026-07-19).

```
C1: CLAIM COMMIT           main cursor: state='running',
                           current_attempt_token, owner_worker_ref,
                           running_since → COMMIT
C2: ATTEMPT-INTENT COMMIT  RESOLVED: dedicated side cursor (mirrors
                           call_lease._admit). Attempt row (pending),
                           both fingerprints, idempotency key,
                           transport_attempted=true → COMMIT, strictly
                           before NET. All request data materialized
                           into plain immutable Python values first.
NET: network call          bounded window; no main-cursor ORM/SQL
                           operation occurs by construction (main
                           cursor's last statement before NET is C1's
                           own commit)
C3: OUTCOME COMMIT         fresh main-cursor txn, re-lock +
                           current_attempt_token CAS-verify;
                           observed_outcome + evidence; if uncertain,
                           sets reconciliation_pending_until + creates
                           linked reconciliation job (mutation_attempt_id
                           Many2one) in the same commit
```

**Governing fact:** Odoo 19 uses PostgreSQL `REPEATABLE READ` on every
cursor (`odoo/sql_db.py`) — every commit point above is a genuine, separate
transaction; every cross-transaction read (recovery, reconciliation, the
sweep) must force a fresh read via `invalidate_recordset()` +
re-`browse()`/re-`search()`, mirroring `_claim_for_dispatch`'s existing
precedent.

Non-mutation job types (`local_only`, `remote_read_replay_safe`) are
**unaffected** — they retain the existing single-commit `_drain_one` path.

## 8. Reconciliation registry interface

Per DEC-036 D15/D16: a new `@api.model` method,
`_get_reconciliation_strategies()`, structurally identical to
`_get_replay_policies()` — domain `_inherit`+`super()`+add-only merge;
build-time completeness test asserting every `mutation_domain` value has a
matching entry (**combined** with `_get_replay_policies()`'s own
completeness test — the two registries must stay in lockstep); a runtime
fail-closed accessor returning nothing for an undeclared domain; a runtime
gate before every C2 commit that refuses to commit/transport if the
registry returns no entry (routes to
`blocked_manual_review`/`no_reconciliation_strategy` instead). **Owning
model — RESOLVED, bindingly `shopify_connector_job_dispatch.py`** (D15,
corrected 2026-07-19 per PR #177 comment 5014806430 item 3): no new
dedicated registry model file is authorized.

## 9. Attempt-wrapper interface

The single point through which every mutation-domain handler must pass:
claim (C1, already exists) → domain-registration gate (§8) → precondition
snapshot capture (read-only, allowlisted per D7) → C2 commit (side cursor)
→ NET → C3 commit. No mutation call site may exist outside this wrapper —
enforced by two independent layers (DEC-036 D16/D37, corrected 2026-07-19):
(a) a repo-wide AST/source guard (§19) failing the build on any bypass at
merge time, and (b) a **runtime** fail-closed guard in
`shopify_connector_api_client.py` (§3) — the send path raises, never
silently proceeds, when a GraphQL document containing a `mutation`
operation is submitted without a valid Layer 2 attempt context/token. The
Admin-only override action, `action_resolve_mutation_attempt` (D11), is
part of this interface's manual-resolution surface: Admin-group-only, no
Reviewer bypass, mandatory reason, gated on `observed_outcome=='uncertain'`
+ `blocked_manual_review`/`duplicate_risk`, atomic with the job's existing
sanctioned transition and one `job.log` row — **never** writes
`observed_outcome`. The two pre-existing generic actions
(`action_resolve_manual_review`, `action_manual_retry`) refuse any
`duplicate_risk`, mutation-attempt-linked job (D11, closes the
previously-open overlap).

## 10. Sweep behavior

Per DEC-036 D26/D27/D28/D29: new `_sweep_stale_running_jobs()` cron,
5-minute cadence, `state='running'` with `running_since` older than a
provisional 30-minute timeout (bounded batch, `try_lock_for_update()`,
default 20 per tick — **no longer contingent on D28**, an ordinary tunable
constant). Evidence-preserving takeover: `transport_attempted=false` →
safe requeue; `transport_attempted=true` → linked reconciliation job,
never re-invokes the handler, never auto-finalizes. Logged distinctly
(`action_type='stale_owner_sweep'`). **Disconnect-quiescence interaction —
RESOLVED, awareness-based (D28):** `_finalize_disconnect_timed_out` is
extended to check, before clearing credentials or deleting the lease,
whether any unresolved mutation attempt or pending/running linked
reconciliation job exists for the store — if so, credentials are
preserved, disconnect stays pending/blocked, and Administrator-visible
manual-review evidence is created. Any force-disconnect path is
Administrator-only, requires a reason, is audited, and routes unresolved
attempts to manual review rather than silently resolving them.
`ShopifyQuiescedError` is wired into an explicit `except` branch in
`_invoke_handler` (currently falls to the generic `unknown_system_error`
safety net).

## 11. Retry and manual-review behavior

`failed_clean` → normal DEC-009 class-based bounded retry (new attempt
row, new `attempt_token`). `uncertain` unresolved → reconcile-then-retry
only, no other path — read via the effective-disposition helper (D10),
never `observed_outcome` directly. Reconciliation `inconclusive` at count 3
(per-attempt scope, **resolved sufficient**, D17) →
`blocked_manual_review`/`duplicate_risk`. Store-identity mismatch →
`blocked_manual_review`/`store_identity_mismatch`, bypassing the normal
flow, never retried. Disconnect-mid-attempt → a dedicated
`blocked_manual_review` subreason distinguishing it from ordinary
ambiguity (§10). **RESOLVED (was: unresolved overlap):** the two
pre-existing mechanisms (`action_resolve_manual_review`,
`action_manual_retry`) are extended to refuse any `duplicate_risk`,
mutation-attempt-linked job, closing the bypass around the stricter
`action_resolve_mutation_attempt` (D11).

## 12. ACL / security matrix

Per DEC-036 D30/D31 (implements the control-room ruling's security
requirements — current, accepted **four-role** model, not the future SEC-2
two-role model):

| Role | Read | Write | Create | Unlink |
|---|---|---|---|---|
| Auditor | Yes | No | No | No |
| Operator | Yes | No | No | No |
| Reviewer | Yes | No | No | No |
| Admin | Yes | No | No | No |

All creation/write happens exclusively via `sudo()` at exactly three sites:
C2 commit, C3 commit, and the resolution-override action (D11). A **closed
sudo-site inventory** is enforced by an AST test that fails the build on a
fourth site. Unlink is permanently denied to all roles including Admin
(ties to retention, §13 — masking, not deletion). No field relies on
`groups=` for write protection — every guard is an explicit Python
`write()`-override check on `self.env.su`, mirroring the existing
`PROTECTED_JOB_FIELDS` pattern exactly. **SEC-2 (future two-role migration)
— explicit re-key obligation (new, D31):** these four ACL rows are a
named, tracked item on the SEC-2 migration's own scope; that session must
re-key them against whatever the two-role model's actual `implied_ids`
behavior turns out to be, not assume today's rows carry forward
unexamined.

## 13. Redaction rules

Per DEC-036 D7: `preconditions_snapshot`, `remote_mutation_intent`, and
`remote_evidence_refs` are populated **exclusively** from a fixed,
per-mutation-domain allowlist declared alongside each domain's
reconciliation-matrix row — never from an unfiltered dump of handler-local
state (no `**kwargs`/`vars()`/`locals()`-style construction). This is a
**structural, write-time** guarantee, enforced by an AST source-guard test,
and does **not** depend on the (disabled-by-default) PII-retention sweep
ever running.

**Retention — RESOLVED, corrected 2026-07-19 (D32):** two-tier. Unresolved,
uncertain, or manual-review attempts are retained **indefinitely** — no
cron, sweep, or manual action ever touches these rows. Resolved-terminal
attempts (effective disposition applied/not_applied) retain full
allowlisted evidence for a **configurable period** (default candidate 180
days); after that period, a new masking sweep (mirroring the existing
`pii_retention.run_sweep()` mask-in-place pattern) masks bulky evidence
fields while permanently keeping the row, its identifiers, both
fingerprints, `observed_outcome`, and all resolution/timestamp fields. The
row is **never** `.unlink()`d by any Stage 0 mechanism, in either tier.

## 14. Lifecycle and uninstall behavior

Per DEC-036 D34 (corrects a self-contradiction in the original design
doc): core-owned, inherits `job`/`job.log`'s DEC-030 posture. Domain-level
uninstall (e.g. a future inventory-module uninstall) → rows survive
core-side, retyped/queryable via the job's LC-1 mechanism, and remain
queryable by `mutation_domain` (a plain `Char`, no Selection-uninstall
lifecycle to reconcile). Core/Lite-substrate uninstall → lost identically
to `job`/`job.log`, unmodified DEC-030 matrix. **No longer contingent on
D35** — D35 is resolved (registry-validated `Char`, not a Selection),
removing the historic-conversion-mechanism question this section
previously carried.

## 15. Upgrade behavior

Per DEC-036 D33: purely additive, **no backfill** required for any of the
three job fields (none has a computable historical value, unlike LC-1's
`original_job_type`) — must be **proven**, not merely asserted, by a
negative-migration test (seed a fixture DB with pre-existing job rows,
apply the upgrade, assert zero `IntegrityError`/`ValidationError` and
correct default resolution). Full upgrade surface: three job fields, one
new model, one new ACL block, one new cron XML record.

## 16. Rollback behavior

Per DEC-036 D36: **pre-ship** — clean additive-schema revert, proven by
§15's negative-migration test. **Post-ship** — never deletes evidence
(§13, masks only); requires **two coordinated mechanisms together**: (a)
the relevant `store.settings.*_domain_enabled` flag set `False`; **and**
(b) the job_type's replay-policy registry entry set/reverted to
`remote_effect_not_replay_safe`. Neither alone is sufficient — (b) alone
does not stop an already-`queued` job's *first* attempt.

## 17. Remaining items (Stage 0 merge-acceptance criteria — not
pre-implementation blockers)

**Every item this packet previously carried as a hard stop is resolved as
architecture in DEC-036 Part 3, per the consolidated Sessions-2-and-3
ruling (2026-07-19).** No item below prevents Stage 0 implementation from
beginning once DEC-036 itself is accepted. Three categories remain:

**Category I — Stage 0 merge-acceptance criteria (implementation proof):**

1. **Four-layer runtime/concurrency/crash-injection proof** (DEC-036 D38,
   §22) — static/unit; genuine PostgreSQL multi-connection concurrency;
   controlled real process-death harness (outside or alongside Odoo.sh,
   wherever process control is available); exact-head Odoo.sh multi-worker
   validation. Required before Stage 0 **merges**, not before it begins.
2. **Open-transaction-spans-network-call runtime proof** (D22, §21) — a new
   `pg_stat_activity`-based test class. The design itself is resolved by
   construction (C2 on a side cursor); only the runtime proof remains.
3. **AST-tooling-maturity direct-inspection finding** (D37) — determines
   whether the repo-wide transport guard is new infrastructure or an
   extension; resolved by inspection at the start of implementation.

**Category II — tunable constants / empirical-measurement gaps:**

4. Sweep cadence/timeout exact numeric values (D27) — provisional 30
   minutes, pending Odoo.sh worst-case handler-duration measurement.
5. Local idempotency-key safety-margin exact value (D6) — provisional 23h,
   needs control-room ratification of the number.
6. Retention masking-window exact value (D32) — provisional 180 days,
   needs control-room ratification of the number.

**Category III — narrow, non-blocking implementation-time verification:**

7. Literal field name for job→store linkage on `shopify.connector.job`
   (D3) — never confirmed by direct quote; verify before implementing the
   `related=` field.

**Out-of-scope, Gate B (before Task 013, not before Stage 0):**

8. `inventory-operating-model.md` §4.4 and
   `task-013-inventory-sync-implementation-packet.md`'s CAS-heading text
   still reference `compareQuantity`; must be corrected in a Gate B
   session with those files in its allowed list before Task 013
   implementation is authorized. Stage 0 carries no inventory-domain code
   and is unaffected.
9. Every Wave-3-DoR program-level hard stop (1–10) applies verbatim, plus
   the Stage-0-specific items above.

Plus every hard stop already binding on this whole session: no
implementation until DEC-036 is accepted; no addon file created/modified by
*this packet's authoring* (only by a future, separately-issued
implementation session); no Odoo/Odoo.sh run; no Shopify request/mutation.

## 18. Definition of done

- Every DEC-036 decision (D1–D38) implemented exactly as specified in the
  accepted package.
- Every §17 item resolved on the record — Category I proof complete,
  Category II constants ratified, Category III verified — none silently
  skipped.
- Static tests (§19) and unit tests (§20) green in their normal CI/local
  test environment (Layer 1). Genuine PostgreSQL concurrency tests (§21)
  green under real independent PostgreSQL connections (Layer 2). Genuine
  OS-process crash-injection tests (§22) green in whichever environment —
  inside or outside Odoo.sh — actually provides real process-control
  capability (Layer 3). Exact-head Odoo.sh multi-worker validation (§23)
  green on Odoo.sh itself (Layer 4). **Corrected 2026-07-19 (PR #177
  comment 5014806430 item 4): no single statement requires all four layers
  to run inside Odoo.sh, and Odoo.sh is not required to host the Layer 3
  crash-injection harness.**
- Residue/leak audit (§23) clean.
- Validation record (`docs/05-qa/task-stage0-layer2-validation-results.md`)
  complete and control-room reviewed.
- `mvp-program-state.md`, `mvp-acceptance-matrix.md`, and
  `research-handoff.md` updated.
- No inventory-domain code exists anywhere in the repository.
- No Shopify mutation was ever issued during Stage 0's own development or
  testing.

## 19. Static tests

- AST-based closed sudo-site inventory test (exactly 3 sites: C2, C3,
  resolution-override).
- AST-based repo-wide network-call-site guard — no
  `requests.get/post/request` call outside `_send()` and the disclosed
  allowlist, **plus** coverage of the mutation-wrapper-transport case (any
  `mutation` document issued outside the wrapper, D16/D37).
- API-client runtime guard test: a mutation document submitted without a
  valid attempt context/token raises; a valid context permits the call to
  proceed; a non-mutation document is unaffected (D16).
- AST-based `preconditions_snapshot`/`remote_mutation_intent`/`remote_evidence_refs`
  allowlist-only construction guard (no `**kwargs`/`vars()`/`locals()`).
- Combined registry-completeness test (`_get_replay_policies()` and
  `_get_reconciliation_strategies()` in lockstep for every declared
  `mutation_domain`); `mutation_domain` registry-fail-closed test (an
  unregistered value is rejected at write time).
- `(job_id, attempt_token)` uniqueness via `models.UniqueIndex` (not
  `_sql_constraints`) — confirmed enforced, not silently inert.
- `transport_attempted`-lives-on-attempt-only test (not duplicated on
  `job`).

## 20. Unit tests

- Full state-machine transition test (DEC-036 Part 5/§6 above), asserting
  `observed_outcome` is rejected as read-only after it first leaves
  `pending` (including from the override action); the effective-disposition
  helper is the sole code path read for retry-eligibility/job-completion.
- Fingerprint normalization stability for both hashes: `business_intent_fingerprint`
  stable across key order and unaffected by `changeFromQuantity`/idempotency-key
  changes; `exact_request_fingerprint` stable across key order and
  **changes** when `changeFromQuantity` changes.
- Idempotency-key reuse-within-`idempotency_valid_until` /
  non-reuse-past-window (routes to reconciliation, not fresh resend).
- `IDEMPOTENCY_CONCURRENT_REQUEST` → `uncertain`;
  `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/`IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED`
  → `idempotency_contract_violation`, `blocked_manual_review`, no automatic
  retry (D6).
- THROTTLED → `uncertain` classification (never `failed_clean`).
- Store-identity-mismatch detection routes to the correct dedicated
  subreason, bypassing normal reconcile flow, never retries.
- Inconclusive-cap sequencing test: no new attempt row can be created while
  a prior attempt's `inconclusive_reconciliation_count` is below 3 and
  unresolved (D17).
- Both pre-existing generic actions (`action_resolve_manual_review`,
  `action_manual_retry`) raise `UserError` on a `duplicate_risk`
  mutation-attempt-linked job (D11).
- Disconnect-awareness test: `_finalize_disconnect_timed_out` preserves
  credentials while an unresolved attempt/pending reconciliation job
  exists; proceeds normally once none remain (D28).
- Negative-migration test (§15).
- Rollback two-mechanism test (§16) — proving mechanism (b) alone is
  insufficient, both together are sufficient.
- Retention masking test: a resolved-terminal attempt past the window has
  bulky fields masked while identifiers/outcome/resolution/timestamps
  remain intact; an unresolved attempt is never touched regardless of age
  (D32).

## 21. Genuine PostgreSQL concurrency tests

Extending the proven `db_connect`+`registry.cursor`-monkey-patch+
`threading.Thread` technique (currently scoped only to
`call.lease`/disconnect-quiescence) to `job.py`/`dispatch.py`'s claim logic
together with the new C1/C2/NET/C3 commit points:

- At least one genuine-concurrency test per row of the D19/D23/D24
  crash-window recovery table.
- Widened claimability-gate test (D25): the new branch matches only on
  exact `current_attempt_token`; a non-matching `running` row remains
  correctly excluded.
- Concurrent-increment race test for `inconclusive_reconciliation_count`
  (two racing reconciliation jobs cannot both bypass the cap).
- `(job_id, attempt_token)` uniqueness under genuine concurrent insert.
- Main-cursor write-isolation invariant test (D21, scoped to the C1
  claim-commit window): ORM dirty-state inspection immediately before the
  C1 commit, asserting no non-connector-model write is pending.
- `pg_stat_activity`-based open-transaction test (D22): asserting no open
  transaction is observed on the main-cursor connection during the
  simulated network-call window.

## 22. Crash-injection tests — four proof-environment layers

Per DEC-036 D38 (RESOLVED, four layers, not three, 2026-07-19):

1. **Layer 1 — static/unit/logical:** §20 above.
2. **Layer 2 — genuine PostgreSQL multi-connection concurrency:** §21
   above.
3. **Layer 3 — controlled real process-death/crash harness:** genuine
   **OS-process-level** crash injection (real `SIGKILL` or equivalent, not
   a same-process exception) against a real PostgreSQL target, run
   **outside or alongside Odoo.sh, wherever process control is actually
   available** — not conditioned on Odoo.sh itself supporting it:
   - Kill between C1 and C2.
   - Kill between C2 and NET (the "transport may have occurred" window).
   - Kill during NET (response never received).
   - Kill between NET returning and C3 committing.
   - Kill during C3's re-lock/CAS/write.

   For each: assert the recovery-table disposition (DEC-036 Part 3, D23–D25)
   is reached correctly after restart, via the sweep or the widened
   `_recover_after_concurrency_conflict` branch as appropriate — never a
   blind re-invocation of the handler.
4. **Layer 4 — exact-head Odoo.sh multi-worker validation:** residue,
   lock, session, credential, and redaction proof at exact committed head
   (§23). Multi-worker proof: Worker B cannot execute a handler Worker A
   durably owns. **Corrected 2026-07-19 (PR #177 comment 5014806430 item
   4):** Odoo.sh is not required to expose `SIGKILL`/worker-process
   control. Where that platform capability is actually available, Layer 4
   observes sweep-driven reconciliation following a real killed worker
   directly; where it is not, Layer 4 instead cross-references Layer 3's
   accepted crash-injection evidence and independently validates the
   restart/recovery behaviour actually available on-platform — never
   simulated either way.

**No layer substitutes for another** — Layer 4 does not need to reproduce
Layer 3's crash-injection technique internally, and Layer 3 does not need
to run inside Odoo.sh. If no environment anywhere can supply genuine Layer
3 evidence (a narrower, concretely-scoped case than "not inside Odoo.sh"):
stop, do not substitute simulation, escalate per Wave-3-DoR hard-stop
6/10.

## 23. Odoo.sh runtime plan

Fresh install + focused-class + full regression + residue audit, per the
Wave 1/Wave 2 standard. Multi-worker proof specifically required: Worker B
must not be able to execute a handler Worker A durably owns (C1's
`current_attempt_token` durability is the property under test). Where
Odoo.sh's own process-control capability supports it, sweep-driven
reconciliation is observed following a real killed worker directly;
otherwise this plan cross-references Layer 3's accepted crash-injection
evidence (§22) and independently validates the restart/recovery behaviour
actually available on-platform — Odoo.sh is not required to expose
`SIGKILL`/worker-process control, and this plan never substitutes
simulation for whichever of the two routes above applies.

## 24. Residue/leak audit

Zero idle-in-transaction connections after any C1/C2/NET/C3 sequence
(direct test of D22's invariant, resolved by construction and verified at
runtime); zero orphaned locks; zero stray workers; zero leaked
credentials/tokens/PII in `preconditions_snapshot`/`remote_mutation_intent`/
`remote_evidence_refs` (structural allowlist guarantee, §13, verified at
runtime not just statically); zero duplicate mutation attempts recorded
for a single successful Shopify mutation across the full crash-injection
matrix (§22).

---

**This packet carries no inventory-domain implementation.** Where a
reconciliation test adapter is needed to prove the generic registry
contract (§8), it is the synthetic `mutation_dispatch_selftest`/
`mutation_dispatch_selftest_reconcile` adapter (§2) — a test-only fixture
registering a fake `mutation_domain` with a stubbed reconciliation
strategy — it must not call any real Shopify mutation and must not become
the actual inventory domain's implementation (that is Task 013's own,
separately-gated scope, per `wave-3-definition-of-ready.md` §1 Stage 1).
Task 013B is explicitly outside Layer 2 — it performs Shopify reads plus
guarded local Odoo writes, never a Shopify mutation, and therefore does
not consume this substrate.
