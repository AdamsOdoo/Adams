# Wave 3 Stage 0 — DEC-031 Layer 2 Core Substrate Implementation Packet

> **Status: PROPOSED — LOCKED PROMPT NOT ISSUED.** Cut from
> [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) (status:
> PROPOSED FOR CONTROL-ROOM ACCEPTANCE — NOT YET ACCEPTED). **This packet
> does not authorize implementation.** Implementation opens only when (a)
> DEC-036 is accepted by the product owner + Claude control room, (b) every
> item DEC-036 marks **BLOCKING** below is resolved or explicitly
> risk-accepted on the record, and (c) the companion locked Sol prompt
> ([`../06-prompts/sol-wave-3-stage-0-locked-prompt.md`](../06-prompts/sol-wave-3-stage-0-locked-prompt.md))
> is separately, explicitly issued to a Sol session.
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
multi-connection concurrency and OS-process-level crash-injection evidence.

## 2. Explicit non-goals

- **No inventory-domain implementation.** No `shopify_connector_inventory`
  addon, no location mapping, no `inventorySetQuantities` call site, no
  Task 013/013B logic of any kind.
- **No Shopify mutation of any kind.** This packet's own tests may issue
  Shopify **reads** only if a genuine dev-store reconciliation-adapter test
  is built to prove the generic registry contract (§13) — never a mutation.
- No fulfillment or product-export scaffolding.
- No UI/screen work.
- No change to the Layer 1 replay-policy registry's existing three-class
  vocabulary or fail-closed default (extended, never modified).
- No change to any currently-shipped read-only handler's observable
  behavior.
- No resolution of DEC-036's **BLOCKING** items by this packet itself —
  those are prerequisites, not in-packet deliverables (see §17 hard stops).

## 3. Allowed files (exhaustive)

- `addons/shopify_connector_core/models/shopify_connector_job.py` —
  additive fields only (D1): `attempt_id`, `owner_worker_ref`,
  `transport_attempted`, `running_since`, `reconciliation_pending_until`
  (D13), `mutation_attempt_id` (D14, on the reconciliation-job side).
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  — the C1/C2/NET/C3 protocol for mutation job types (D19); the widened
  `_recover_after_concurrency_conflict` claimability branch (D25); the
  `ShopifyQuiescedError` handling branch (D28/D29); the
  `_get_reconciliation_strategies()` registry seam (D15) and its runtime
  fail-closed gate (D16) — **only if** its owning-model question (DEC-036
  §5 item 6) is resolved to this file; otherwise the new model file below.
- **New file** `addons/shopify_connector_core/models/shopify_connector_mutation_attempt.py`
  — the `shopify.connector.mutation.attempt` model (D2/D3/D4/D5/D6/D7/D8/D9/D10/D17).
- **New file** `addons/shopify_connector_core/models/shopify_connector_stale_owner_sweep.py`
  (or added to `job_dispatch.py` if smaller — implementer's choice,
  disclosed either way) — `_sweep_stale_running_jobs()` (D26/D27).
- `addons/shopify_connector_core/security/ir.model.access.csv` — four new
  ACL rows for `mutation.attempt` (D30).
- `addons/shopify_connector_core/security/shopify_connector_security.xml`
  — no new group; the Admin-only resolution-override action (D11) uses the
  existing `group_shopify_connector_admin`.
- **New file** `addons/shopify_connector_core/data/shopify_connector_stale_owner_sweep_cron.xml`
  — the new cron record, `noupdate="1"` (D26/D27).
- `addons/shopify_connector_core/models/__init__.py`,
  `addons/shopify_connector_core/__manifest__.py` — version bump, new file
  registration, new data file registration (D33).
- **New test files** under `addons/shopify_connector_core/tests/` — see §14
  for the exact required set.
- `docs/07-implementation-plan/wave-3-stage-0-layer-2-packet.md` (this
  file — validation-record updates only, no scope change).
- A new `docs/05-qa/task-stage0-layer2-validation-results.md` (created at
  implementation time, not by this packet).

## 4. Forbidden files

Everything outside §3. Specifically: `shopify_connector_product/**`,
`shopify_connector_sale/**`, `adams_base/**`; any file under a future
`shopify_connector_inventory/**` (does not yet exist and must not be
created by this packet); `shopify_connector_api_client.py`,
`shopify_connector_store.py`, `shopify_connector_store_settings.py`,
`shopify_connector_binding_mixin.py`, `shopify_connector_job_actions.py`,
`shopify_connector_call_lease.py`, `shopify_connector_job_enqueue.py` (read
and cited extensively by this session's audit; **not modified** by Stage 0
— D29's credential-snapshot field lives on the new attempt model, not on
these files); any Layer 1 replay-policy-registry *behavior* change (only
new domain declarations, via the existing extension seam, are ever
in-scope for a *future* domain, never Stage 0 itself since Stage 0
registers no domain); CI/workflow files; protected references.

## 5. `shopify.connector.mutation.attempt` — exact schema

Per DEC-036 D2, D3, D5–D9, D10, D17:

| Field | Type | Notes |
|---|---|---|
| `job_id` | **BLOCKED — DEC-036 D20** | Many2one-FK-restrict vs. plain Integer unresolved; resolve before this field is implemented |
| `attempt_id` | Char (UUID), required | matches the job-row token for this attempt |
| `mutation_domain` | Selection | **BLOCKED — DEC-036 D35**: field-ownership model (domain-`selection_add` vs. core-fixed) unresolved |
| `store_id` | Many2one, `related='job_id.store_id'`, stored, indexed, readonly | D3; exact source field name on `job` unconfirmed, verify before implementing |
| `remote_mutation_intent` | Char/JSON | identifiers only, D7 allowlist |
| `preconditions_snapshot` | JSON | allowlisted per domain matrix row, D7 |
| `request_fingerprint` | Char (SHA-256) | D5; `changeFromQuantity` excluded from the hash |
| `shopify_idempotency_key` | Char (UUID), nullable | D6 |
| `idempotency_key_carried_forward` | Boolean | D6, new |
| `transport_attempted` | Boolean, default False | D1/D23 |
| `outcome` | Selection (4): `pending`/`succeeded`/`failed_clean`/`uncertain` | D9/D10 — Layer O |
| `resolution_disposition` | Selection (2), nullable: `applied`/`not_applied` | D10/D11 — Layer R, canonical name pending control-room ratification |
| `resolution_reason` | Text, mandatory when `resolution_disposition` set | D11 |
| `resolution_uid` | Many2one `res.users` | D11 |
| `resolution_at` | Datetime | D11 |
| `inconclusive_reconciliation_count` | Integer, default 0 | D17 — **persistence-scope BLOCKING**, see §17 |
| `remote_evidence_refs` | JSON | D8, exact shape below |
| `created_at`, `transport_at`, `resolved_at` | Datetime | commit-point timestamps |

`remote_evidence_refs` shape (D8): `{remote_gids: [...], user_errors:
[{code, field}], http_status, graphql_error_codes: [...], throttle_status:
{maximumAvailable, currentlyAvailable, restoreRate} | null}`.

Uniqueness: `(job_id, attempt_id)` via `models.UniqueIndex` — **never**
`_sql_constraints` (confirmed silently inert under Odoo 19).

Job-row additive fields (D1): `attempt_id`, `owner_worker_ref`,
`transport_attempted`, `running_since`, `reconciliation_pending_until`
(D13), `mutation_attempt_id` (D14, reconciliation-job side). All join
`PROTECTED_JOB_FIELDS`.

## 6. State and transition tables

Full detail: DEC-036 Part 5. Summary:

- **Layer J (Job):** unchanged 10-value `shopify.connector.job.state`
  machine — zero new states, zero new transitions.
- **Layer O (Outcome):** `mutation.attempt.outcome`, closed 4-value,
  machine-observed only.
- **Layer R (Resolution):** `mutation.attempt.resolution_disposition`,
  closed 2-value nullable, human-asserted only via §9's override action.

11-step transition sequence: attempt creation (`pending`) → direct response
(`succeeded`/`failed_clean`/`uncertain`) → `uncertain` triggers
reconciliation (job-level `reconciliation_pending_until` set, linked
reconciliation job created) → verdict `applied`/`not-applied`/`inconclusive`
→ inconclusive count increments (row-locked) → cap (N=3, **persistence
scope BLOCKING**) trips to `blocked_manual_review`/`duplicate_risk` →
Admin-only override sets `resolution_disposition` and forces `outcome` →
job resumes via the existing sanctioned `blocked_manual_review→queued`
transition. Store-identity mismatch (§10) bypasses the normal flow
entirely. A `failed_clean` DEC-009 retry always creates a **new** attempt
row with a new `attempt_id` — the old row's `outcome`/`resolution_disposition`
are terminal and immutable.

## 7. Transaction/commit protocol

Full detail: DEC-036 Part 6; design-doc §11 (corrected 2026-07-18).

```
C1: CLAIM COMMIT           state='running', attempt_id, owner_worker_ref,
                           running_since → COMMIT
C2: ATTEMPT-INTENT COMMIT  cursor placement BLOCKED (D20): attempt row
                           (pending), transport_attempted=true → COMMIT,
                           strictly before NET
NET: network call          bounded window; "nothing on main cursor between
                           C2 and NET" discipline required, unproven (D22)
C3: OUTCOME COMMIT         fresh txn, re-lock + attempt_id CAS-verify;
                           outcome + evidence; if uncertain, sets
                           reconciliation_pending_until + creates linked
                           reconciliation job in the same commit
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
model:** not stated by the original design doc; must be decided (§3 above,
DEC-036 §5 item 6) before this interface is implemented.

## 9. Attempt-wrapper interface

The single point through which every mutation-domain handler must pass:
claim (C1, already exists) → domain-registration gate (§8) → precondition
snapshot capture (read-only, allowlisted per D7) → C2 commit → NET → C3
commit. No mutation call site may exist outside this wrapper — enforced by
the AST/source guard (§15). The Admin-only override action,
`action_resolve_mutation_attempt` (D11), is part of this interface's
manual-resolution surface: Admin-group-only, no Reviewer bypass, mandatory
reason, gated on `outcome=='uncertain'` + `blocked_manual_review`/`duplicate_risk`,
atomic with the job's existing sanctioned transition and one `job.log` row.

## 10. Sweep behavior

Per DEC-036 D26/D27/D28/D29: new `_sweep_stale_running_jobs()` cron, 5-minute
cadence, `state='running'` with `running_since` older than a provisional
30-minute timeout (bounded batch, `try_lock_for_update()`, default 20 per
tick). Evidence-preserving takeover: `transport_attempted=false` → safe
requeue; `transport_attempted=true` → linked reconciliation job, never
re-invokes the handler, never auto-finalizes. Logged distinctly
(`action_type='stale_owner_sweep'`). **BLOCKING interaction:** the
disconnect-quiescence controller clears credentials/deletes the lease at a
fixed 15-minute timeout with no way to distinguish a live vs. orphaned
lease — an orphaned lease is invisible to a 30-minute sweep until after
credentials are already cleared, stranding reconciliation. Requires an
explicit control-room choice between shrinking the sweep timeout below 15
minutes or extending `_finalize_disconnect_timed_out` to check for open
mutation jobs (§17). Regardless of the choice, `ShopifyQuiescedError` must
be wired into an explicit `except` branch in `_invoke_handler` (currently
falls to the generic `unknown_system_error` safety net).

## 11. Retry and manual-review behavior

`failed_clean` → normal DEC-009 class-based bounded retry (new attempt
row, new `attempt_id`). `uncertain` → reconcile-then-retry only, no other
path. Reconciliation `inconclusive` at count 3 (persistence-scope
**BLOCKING**, §17) → `blocked_manual_review`/`duplicate_risk`. Store-identity
mismatch → `blocked_manual_review`/`store_identity_mismatch`, bypassing the
normal flow. Disconnect-mid-attempt → a dedicated `blocked_manual_review`
subreason distinguishing it from ordinary ambiguity (§10). **Unresolved
overlap, not resolved by this packet:** two pre-existing mechanisms
(`action_resolve_manual_review`, `action_manual_retry`) already reach
`blocked_manual_review→queued`; their interaction with the new
`action_resolve_mutation_attempt` (D11) is not reconciled anywhere and
should be reviewed before Stage 0 ships (DEC-036 §5 item 9).

## 12. ACL / security matrix

Per DEC-036 D30/D31 (implements the control-room ruling's point 7 — no
reliance on unresolved `sudo()`/field-`groups=` behavior):

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
(ties to retention, §13). No field relies on `groups=` for write
protection — every guard is an explicit Python `write()`-override check on
`self.env.su`, mirroring the existing `PROTECTED_JOB_FIELDS` pattern
exactly. SEC-2 (future two-role migration) compatibility: no ACL change
needed here, pending empirical confirmation of `implied_ids` inheritance
(non-blocking now, blocking at SEC-2 packet time).

## 13. Redaction rules

Per DEC-036 D7: `preconditions_snapshot`, `remote_mutation_intent`, and
`remote_evidence_refs` are populated **exclusively** from a fixed,
per-mutation-domain allowlist declared alongside each domain's
reconciliation-matrix row — never from an unfiltered dump of handler-local
state (no `**kwargs`/`vars()`/`locals()`-style construction). This is a
**structural, write-time** guarantee, enforced by an AST source-guard test,
and does **not** depend on the (disabled-by-default) PII-retention sweep
ever running. Retention (D32): rows are retained **indefinitely** — no
cron, sweep, or manual action in Stage 0 ever deletes a row, mirroring
`job`/`job.log`'s append-only posture. A future deletion capability, if
ever needed, is explicitly out of scope here.

## 14. Lifecycle and uninstall behavior

Per DEC-036 D34 (corrects a self-contradiction in the original design
doc): core-owned, inherits `job`/`job.log`'s DEC-030 posture. Domain-level
uninstall (e.g. a future inventory-module uninstall) → rows survive
core-side, retyped/queryable via the job's LC-1 mechanism. Core/Lite-substrate
uninstall → lost identically to `job`/`job.log`, unmodified DEC-030 matrix.
**Contingent on D35** (§17) — an incorrectly domain-owned `mutation_domain`
field without an LC-1-style historic-conversion mechanism would reintroduce
the exact failure DEC-030 already fixed once.

## 15. Upgrade behavior

Per DEC-036 D33: purely additive, **no backfill** required for any of the
four job fields (none has a computable historical value, unlike LC-1's
`original_job_type`) — must be **proven**, not merely asserted, by a
negative-migration test (seed a fixture DB with pre-existing job rows,
apply the upgrade, assert zero `IntegrityError`/`ValidationError` and
correct default resolution). Full upgrade surface: 3+ job fields, one new
model, one new ACL block, one new cron XML record.

## 16. Rollback behavior

Per DEC-036 D36: **pre-ship** — clean additive-schema revert, proven by
§15's negative-migration test. **Post-ship** — never deletes evidence
(§13); requires **two coordinated mechanisms together**: (a) the relevant
`store.settings.*_domain_enabled` flag set `False`; **and** (b) the
job_type's replay-policy registry entry set/reverted to
`remote_effect_not_replay_safe`. Neither alone is sufficient — (b) alone
does not stop an already-`queued` job's *first* attempt.

## 17. Hard stops (inherited from DEC-036 — must be resolved or explicitly
risk-accepted by the control room before the corresponding Stage 0 code
path may be implemented)

1. **`mutation_attempt.job_id` field type + C2 cursor placement** (DEC-036
   D20) — Many2one-FK-restrict vs. plain Integer; main vs. side cursor.
2. **Open-transaction-spans-network-call proof** (D22) — requires a new
   coding rule and a new `pg_stat_activity`-based test class.
3. **Disconnect-quiescence/sweep-timeout interaction** (D28) — explicit
   control-room choice between two remediations.
4. **`mutation_domain` field ownership** (D35) — explicit control-room
   choice between domain-`selection_add` and core-fixed.
5. **N=3 inconclusive-cap persistence scope** (D17) — per-`attempt_id` vs.
   cross-retry-chain; a product-owner safety-property decision.
6. **Repo-wide AST/source-guard tooling-maturity contradiction** (D37) —
   resolve by direct inspection before sizing.
7. **Three-layer runtime/concurrency/crash-injection proof** (D38) —
   logical, genuine-concurrency, and genuine OS-process-crash-injection
   layers, all three required, none substitutable by simulation. **If
   genuine OS-level crash injection is infeasible on the target Odoo.sh
   environment, this invokes Wave-3-DoR hard-stop 6/10: stop, escalate for
   an explicit, separately-logged product-owner risk-acceptance decision.**
8. **Out-of-scope document corrections** — `inventory-operating-model.md`
   §4.4 and `task-013-inventory-sync-implementation-packet.md`'s CAS
   heading still reference `compareQuantity`; must be corrected in a
   session with those files in its allowed list before the Stage 1 locked
   prompt (not this Stage 0 prompt) is issued.
9. Every Wave-3-DoR program-level hard stop (1–10) applies verbatim, plus
   the Stage-0-specific ones above.

Plus every hard stop already binding on this whole session: no
implementation until DEC-036 is accepted; no addon file created/modified by
*this packet's authoring* (only by a future, separately-issued
implementation session); no Odoo/Odoo.sh run; no Shopify request/mutation.

## 18. Definition of done

- All non-blocking DEC-036 decisions (D1–D11, D13–D16, D18–D19, D21,
  D23–D27, D29–D34, D36) implemented exactly as specified.
- Every item in §17 explicitly resolved or explicitly risk-accepted on the
  record by the control room — none silently skipped.
- Static tests (§19), unit tests (§20), genuine PostgreSQL concurrency
  tests (§21), and genuine OS-process crash-injection tests (§22) all
  green on a real Odoo.sh multi-worker environment.
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
- AST-based repo-wide network-call-site guard (§17 item 6) — no
  `requests.get/post/request` call outside `_send()` and the disclosed
  allowlist.
- AST-based `preconditions_snapshot`/`remote_mutation_intent`/`remote_evidence_refs`
  allowlist-only construction guard (no `**kwargs`/`vars()`/`locals()`).
- Combined registry-completeness test (`_get_replay_policies()` and
  `_get_reconciliation_strategies()` in lockstep for every declared
  `mutation_domain`).
- `(job_id, attempt_id)` uniqueness via `models.UniqueIndex` (not
  `_sql_constraints`) — confirmed enforced, not silently inert.

## 20. Unit tests

- Full 11-step state-machine transition test (DEC-036 Part 5).
- Fingerprint normalization stability (key-order-independent;
  `changeFromQuantity`-exclusion verified).
- Idempotency-key reuse-within-window / non-reuse-past-window.
- All three idempotency user-error codes correctly classified.
- THROTTLED → `uncertain` classification (never `failed_clean`).
- Store-identity-mismatch detection routes to the correct dedicated
  subreason, bypassing normal reconcile flow.
- Negative-migration test (§15).
- Rollback two-mechanism test (§16) — proving mechanism (b) alone is
  insufficient, both together are sufficient.

## 21. Genuine PostgreSQL concurrency tests

Extending the proven `db_connect`+`registry.cursor`-monkey-patch+
`threading.Thread` technique (currently scoped only to
`call.lease`/disconnect-quiescence) to `job.py`/`dispatch.py`'s claim logic
together with the new C1/C2/NET/C3 commit points:

- At least one genuine-concurrency test per row of the D19/D23/D24
  crash-window recovery table.
- Widened claimability-gate test (D25): the new branch matches only on
  exact `attempt_id`; a non-matching `running` row remains correctly
  excluded.
- Concurrent-increment race test for `inconclusive_reconciliation_count`
  (two racing reconciliation jobs cannot both bypass the cap).
- `(job_id, attempt_id)` uniqueness under genuine concurrent insert.
- Main-cursor write-isolation invariant test (D21): ORM dirty-state
  inspection immediately before the C2 commit, asserting no
  non-connector-model write is pending.
- `pg_stat_activity`-based open-transaction test (D22): asserting no open
  transaction is observed on the connection during the simulated
  network-call window.

## 22. Crash-injection tests

Genuine **OS-process-level** crash injection (real `SIGKILL` or
equivalent, not a same-process exception) against a real hosted-Postgres
target:

- Kill between C1 and C2.
- Kill between C2 and NET (the "transport may have occurred" window).
- Kill during NET (response never received).
- Kill between NET returning and C3 committing.
- Kill during C3's re-lock/CAS/write.

For each: assert the recovery-table disposition (DEC-036 Part 6) is
reached correctly after restart, via the sweep or the widened
`_recover_after_concurrency_conflict` branch as appropriate — never a
blind re-invocation of the handler.

**If infeasible on the target Odoo.sh environment:** stop, do not
substitute simulation, escalate per §17 item 7.

## 23. Odoo.sh runtime plan

Fresh install + focused-class + full regression + residue audit, per the
Wave 1/Wave 2 standard. Multi-worker proof specifically required: Worker B
must not be able to execute a handler Worker A durably owns (C1's
`attempt_id` durability is the property under test); sweep-driven
reconciliation observed on a real killed worker, not simulated.

## 24. Residue/leak audit

Zero idle-in-transaction connections after any C1/C2/NET/C3 sequence
(direct test of D22's currently-unproven invariant); zero orphaned locks;
zero stray workers; zero leaked credentials/tokens/PII in
`preconditions_snapshot`/`remote_mutation_intent`/`remote_evidence_refs`
(structural allowlist guarantee, §13, verified at runtime not just
statically); zero duplicate mutation attempts recorded for a single
successful Shopify mutation across the full crash-injection matrix (§22).

---

**This packet carries no inventory-domain implementation.** Where an
inventory reconciliation test adapter is needed to prove the generic
registry contract (§8), it may be built as a **test-only** fixture
registering a fake `mutation_domain` with a stubbed reconciliation
strategy — it must not call any real Shopify mutation and must not become
the actual inventory domain's implementation (that is Task 013's own,
separately-gated scope, per `wave-3-definition-of-ready.md` §1 Stage 1).
