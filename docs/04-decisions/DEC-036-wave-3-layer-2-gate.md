# DEC-036 — Wave 3 Gate A: DEC-031 Layer 2 Acceptance Candidate

- **Status: ACCEPTED — CONTROL-ROOM GATE A.** Acceptance authority: PR #177
  comment
  [`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)
  ("Control-room final Gate A decision — ACCEPTED WITH TWO CLERICAL
  MERGE-CLOSURE CONDITIONS"), 2026-07-19. Claude did not accept its own
  decision package (see this session's governing task, §8); the independent
  control-room review and acceptance act recorded here is that comment's.
- **Package status: CORRECTIONS APPLIED PER THE FINAL CONSOLIDATED
  SESSIONS-2-AND-3 RULING.** Per the control-room's consolidated ruling on
  PR #177 comment
  [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)
  ("Sessions 2 + 3 reconciled; one correction batch authorized"), every
  binding architecture decision in that ruling is applied in this revision.
  **After this correction batch, no genuinely unresolved architecture
  blocker remains preventing Stage 0 implementation from beginning, and
  DEC-036 itself has now been independently accepted** — see Part 0.5 and
  the revised Part 5/Part 6 below. Remaining open items are either (a)
  implementation proof/sizing work correctly classified as Stage 0
  merge-acceptance criteria, not pre-implementation blockers, or (b) Gate B
  prerequisites scoped to Task 013, out of this session's allowed-files
  list. Session A (this record's author) did not accept its own decision
  package — the control room's consolidated ruling supplied the binding
  architecture choices, and the control room's own separate acceptance act
  (PR #177 comment 5015044226) is DEC-036's acceptance authority.
- **Decision owner (candidate author, not acceptor):** Claude control room,
  under DEC-032 / `CLAUDE.md` §13, per the task's explicit "Claude must not
  accept its own decision package" rule (task §8).
- **Scope:** normalizes and closes the DEC-031 Layer 2 decision inventory —
  the source documents inconsistently used `L2-D1..D13` in some places and
  `L2-D14`/`L2-D15` in others; this record replaces that with one complete,
  gap-free numbering set, **L2-D1 through L2-D38**, covering all 35 numbered
  decision/risk items and 15 lettered risk items named in this session's
  governing task, and defines the Wave 3 Stage 0 implementation packet cut
  from it (`../07-implementation-plan/wave-3-stage-0-layer-2-packet.md`).
- **Evidence base:** this session's 27-agent research/audit/adversarial-review
  workflow (18 grounding agents covering
  `addons/shopify_connector_core/models/**`, `security/**`, `data/**`,
  `tests/**` [17 files surveyed], `DEC-031` + its Layer 1 companion doc, the
  Layer 2 design doc in full, `DEC-030` + the lifecycle design doc, the
  Wave 3 DoR + Task 013/013B packets, the inventory operating model +
  reconnect policy, the risk register + acceptance matrix + program
  contract, and a targeted `research-handoff.md` sweep; 4 dedicated
  official-source research agents; 8 thematic adversarial-review clusters
  covering every numbered/lettered item; 1 consolidation pass), plus this
  session's own independent primary-source verification recorded in
  [`../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md).
- **Related:** [`dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
  (updated by this same session to reflect the corrections below — still
  status Proposed), [`DEC-031`](DEC-031-core-r2-job-execution-replay-safety.md)
  (Layer 1 Accepted, unchanged; Layer 2 remains Proposed), the Wave 3 Stage 0
  packet, the locked (not issued) Sol Stage 0 prompt.

---

## 0. Control-room ruling incorporation record

This session received, mid-session, a binding control-room parallel-audit
ruling on PR #177 comment
[`5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989)
("Session 2 source audit accepted with mandatory corrections"). Every
mandatory point is addressed in this package as follows:

| Ruling point | Addressed where |
|---|---|
| 1. Correct isolation-level error: Odoo 19 uses REPEATABLE READ, not Read Committed | [`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md) §5 (independently re-verified against `odoo/sql_db.py`, not merely accepted from the ruling text); this record's Part 6, and the updated design doc §11 |
| 2. Update C1/C2/C3, recovery, snapshot-refresh and cache/re-browse wording | Part 6 below; design doc §11 (rewritten) |
| 3. Replace `compareQuantity`/`ignoreCompareQuantity` with `changeFromQuantity` everywhere current-facing | D12 below; design doc §3/§4.2 (rewritten); source-materials refresh §1. **Residual, out-of-scope correction still needed:** `inventory-operating-model.md` §4.4 and `task-013-inventory-sync-implementation-packet.md` §"CAS via `compareQuantity`" heading also need this correction but are **not** in this session's allowed-files list (task §7) — flagged as a required follow-up in Part 9 and in `research-handoff.md` |
| 4. Treat mutation-side THROTTLED as uncertain/reconcile-first unless pre-execution rejection is positively proven | D9 below; design doc §5.1/§10 (rewritten) |
| 5. Default Task 013 to one pair per mutation request until partial-batch semantics are proven or every entry independently reconciled | D4 below |
| 6. Add the clean-cursor/no-unrelated-dirty-state invariant and tests | D21 below (already independently reached by this session's own transaction-protocol review cluster before the ruling arrived) |
| 7. Do not rely on unresolved sudo/field-group behavior; specify explicit server-side guards | D30 below; source-materials refresh §8 |
| 8. Do not freeze the package yet; Session C's audit still needs reconciliation | This section; every status banner in this record and its siblings says "NOT YET ACCEPTED" / "NOT FROZEN" |

**Independent corroboration, not blind acceptance:** this session did not
simply transcribe the ruling's assertions. Every factual point above was
independently re-verified against primary sources by this session (see the
source-materials refresh's provenance note) before being incorporated, and
in the case of point 1 (isolation level) and point 6 (clean-cursor
invariant), this session's own adversarial-review workflow had **already,
independently, before the ruling was read,** identified the same
underlying risk (see Part 2 item 4 and D21/D22 below) — the ruling and this
session's own research converge, they do not merely defer to each other.

A second, preliminary control-room review followed on PR #177 comment
[`5013028262`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5013028262)
("REVISION REQUIRED; package remains unfrozen"), identifying ten further
mandatory corrections not fully captured by this session's own original
BLOCKING-item list, and instructing that no further commits be made until
an independent "Session 3" adversarial architecture audit was returned and
the control room issued one consolidated correction instruction. That
instruction arrived as PR #177 comment
[`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)
("Sessions 2 + 3 reconciled; one correction batch authorized") and is
applied throughout this revision — see Part 0.5 immediately below for the
full reconciliation record and Part 3 for the corrected per-decision text.

---

## 0.5 Sessions 2 + 3 reconciliation and final consolidated ruling (2026-07-19)

This section records, per the consolidated ruling's explicit requirement,
how the two independent, externally-tracked audit workstreams this session
could not itself perform were each dispositioned by the control room, and
what changed in this document as a result. Neither audit is adopted
wholesale; each finding was independently accepted, rejected, or carried
forward, per the control room's own text.

### Session 2 (official-source audit) reconciliation

- **Accepted with a correction already recorded in Part 0 above:** Session
  2's finding that `changeFromQuantity` is the correct current CAS field,
  that `@idempotent` is mandatory with 24h retention, that `cr.commit()` is
  cursor-wide (clean-cursor invariant needed), that THROTTLED's
  non-execution guarantee is unestablished, and that batch partial-success
  semantics are undocumented — all accepted and already incorporated (Part
  0 table, points 1–7).
- **Session 2's own conclusion that Odoo uses PostgreSQL default Read
  Committed isolation was explicitly REJECTED** by the control room and
  corrected: **Odoo 19 governs the design under PostgreSQL `REPEATABLE
  READ`** (`odoo/sql_db.py`, `ISOLATION_LEVEL_REPEATABLE_READ`, set on
  every cursor). This correction was independently re-verified by this
  session against the primary source, not merely accepted from either the
  ruling or Session 2's own (incorrect) claim — see the source-materials
  refresh §5 and D21 below.

### Session 3 (adversarial architecture audit) reconciliation

- **Accepted as evidence and contradiction discovery.** Session 3's
  contradiction inventory — the D5 fingerprint-safety gap, the D10/D11
  three-layer-model violation, the D6 idempotency-defect mis-routing, the
  D35 missing third `mutation_domain` option, the D32 retain-forever
  over-reach, the D20 combined-decision problem, the D22/D37
  non-architecture-blocker mis-framing, the D38 proof-environment
  conflation, and the D28 timeout-race framing — is accepted and drives
  every corrected decision in Part 3 below.
- **Session 3's proposed single six-value outcome enum is REJECTED.** The
  control room retains the strict two-layer separation: a closed 4-value
  `observed_outcome` (`pending`/`succeeded`/`failed_clean`/`uncertain`,
  immutable once left `pending`) plus an orthogonal, nullable
  `resolution_disposition` (`applied`/`not_applied`). Collapsing these into
  one six-value enum would re-introduce exactly the outcome/resolution
  conflation D10 exists to prevent — see D10 below for the corrected
  design.
- **Session 3's proposal to install Stage 0 ACLs directly against the
  future SEC-2 two-role model is REJECTED.** Stage 0 installs cleanly under
  the **current, accepted four-role model** (Auditor/Operator/Reviewer/
  Administrator) and carries an explicit SEC-2 migration follow-up
  obligation instead — see D30/D31 below. Pre-emptively coding against a
  not-yet-existing role model was already rejected once in D31's original
  text for the same reason (the group does not exist in code yet); this
  ruling extends that same reasoning to the ACL installation shape itself,
  not merely to pre-emptive rows.

### Binding architecture decisions now applied

Every numbered point in the consolidated ruling (attempt granularity/
batching; the orthogonal observed-outcome/resolution model; the two-hash
fingerprint split; the idempotency fail-closed routing; the corrected core
schema; the C1/C2/NET/C3 protocol with C2 as a side-cursor commit; the
reconciliation contract; THROTTLED; disconnect/quiescence
awareness-over-timeout-race; store identity/connection generation; the
retention/lifecycle policy; the four-role security model; the wrapper/API
enforcement guard; the four-layer proof-environment plan; the corrected
Stage 0 allowed-file list; and the Gate B carry-forward list) is applied in
the corresponding Part 3 decision entry below, and reflected in the Part 2
status table, the revised Part 4/5 (no remaining architecture blocker), and
Part 6 (status).

One-pair-per-request removes multi-pair batching from Wave 3 MVP scope
entirely (D4, unchanged in substance, restated precisely as "MVP Stage 1"
per the ruling's own wording).

### Gate B / Task 013 corrections carried forward

Per the consolidated ruling, before Task 013 inventory implementation is
authorized, a Gate B session (with Task 013's own packet and the inventory
operating model in its allowed-files list — neither is in this session's
allowed list) must:

1. Replace all stale `compareQuantity`/`ignoreCompareQuantity` language
   with `changeFromQuantity` (D12's factual correction, already applied
   in-scope everywhere this session's allowed files reach; the two
   out-of-scope documents named in §5 item 11 still need it).
2. Explicitly supersede binding-owned idempotency with attempt-owned
   idempotency (D6, already the binding design in this package — Gate B
   propagates it into Task 013's own text).
3. Adopt review-case-first handling for unexplained Shopify drift, rather
   than automatic overwrite, as the final unexplained-drift posture.
4. State one pair per mutation request for MVP (D4, already binding here
   — Gate B propagates it into Task 013's own text).
5. State that Task 013B does not use Layer 2, because it performs Shopify
   reads plus guarded local Odoo writes, never a Shopify mutation (already
   stated in the Stage 0 packet §2/closing note, out of DEC-036's own
   scope to restate for Task 013B's own packet).
6. Keep Task 013B as a separate Stage 2 packet, unchanged.

These six items must be completed before Task 013 implementation
authorization; none of them blocks Stage 0, which carries no
inventory-domain code.

---

## 1. Numbering-scheme note

Of the 15 lettered risk items (A–O) named in this session's task, five are
merged into the numbered decision they duplicate or complete rather than
kept as separate `L2-D` numbers, because they resolve to the same accepted
content as an adjacent numbered item (full reasoning in Part 3 below): **A**
→ D10; **B** → D23; **E** → D14; **F** (merged with numbered item 23) → D13;
**J** → D34. **O** is not given its own number — it is attached as a
closing validation note on D35. All other lettered items (C, D, G, H, I, K,
L, M, N) get their own number or split across two numbers where they carry
genuinely distinct payloads (H splits into D30/H-security-matrix and D11;
M splits into D9/D16).

---

## 2. Decision Inventory — L2-D1 through L2-D38

| # | Title | Status | Source items |
|---|---|---|---|
| D1 | Job-row durability fields — exactly three (`current_attempt_token`, `owner_worker_ref`, `running_since`) | **RESOLVED** — corrected 2026-07-19, `transport_attempted` removed from the job-field list per PR #177 comment 5014806430 item 5 | 1, 18 |
| D2 | `mutation.attempt` core schema | **RESOLVED** — `job_id` Many2one-restrict, `mutation_domain` Char, two fingerprints, `observed_outcome`/`resolution_*` fields, per consolidated ruling §5/§8 | 2 |
| D3 | `store_id` denormalization + multi-company scope | Candidate, one sub-gap open | 3 |
| D4 | Attempt granularity = exactly one business pair per request; batching excluded from MVP | **RESOLVED** | K, L, 33 |
| D5 | Two-hash fingerprint split (`business_intent_fingerprint` / `exact_request_fingerprint`) | **RESOLVED** — corrected per consolidated ruling §3 | 6 |
| D6 | Idempotency-key lifecycle + fail-closed defect-code routing | **RESOLVED** — corrected per consolidated ruling §4 | 7, N |
| D7 | `preconditions_snapshot` allowlist | Candidate | 8, 28 |
| D8 | `remote_evidence_refs` structured JSON | Candidate | 9 |
| D9 | Outcome taxonomy stays 4-value; THROTTLED→`uncertain` | Candidate | 9, M |
| D10 | Observed-outcome/resolution orthogonal model (immutable `observed_outcome`) | **RESOLVED** — corrected per consolidated ruling §2 | 4, 5, A |
| D11 | Administrator-only resolution-override action | **RESOLVED**, naming ratified as `resolution_disposition`/`action_resolve_mutation_attempt` | 5, 25, H |
| D12 | CAS field-name correction | **RESOLVED** (source conflict), applying it is a Candidate correction | cross-cutting |
| D13 | Job-layer reconciliation-pending gate | Candidate | F, 23 |
| D14 | Reconciliation-job linkage (`mutation_attempt_id` Many2one-restrict, required) | **RESOLVED** — corrected per consolidated ruling §5/§8 | 10, E |
| D15 | Reconciliation-strategy registry | **RESOLVED** — owning model bound to `shopify_connector_job_dispatch.py`, corrected 2026-07-19 per PR #177 comment 5014806430 item 3 | 11, O |
| D16 | Domain-registration fail-closed runtime gate + mutation-wrapper/API-client enforcement | **RESOLVED** — extended per consolidated ruling §14 | 12 |
| D17 | Inconclusive-reconciliation cap (N=3), per-attempt scope | **RESOLVED — not blocking** — per-uncertain-attempt scope is sufficient, per consolidated ruling §7 | 24 |
| D18 | Store-identity + connection-generation snapshot and mismatch routing | **RESOLVED** — corrected per consolidated ruling §10 | 22, G |
| D19 | Transaction/commit-point protocol (C1/C2/NET/C3) | **RESOLVED** | 13 |
| D20 | C2 cursor placement (side cursor) | **RESOLVED — not blocking** — split from `job_id` field type (now D2), per consolidated ruling §6 | 14 |
| D21 | Main-cursor write-isolation invariant | Candidate, needs new tests (runtime acceptance criterion, not a blocker) | C |
| D22 | Open-transaction-spans-network-call discipline | **RESOLVED — not blocking** — implementation invariant + runtime acceptance criterion, per consolidated ruling §6/§9 | D |
| D23 | Crash-window C2→NET recovery | Candidate | 15, B |
| D24 | Crash-window NET→C3 recovery | Candidate, one orphaned question | 16 |
| D25 | Claimability-gate widening for 40001/lock-timeout recovery | Candidate | 17 |
| D26 | Stale-owner sweep mechanism | Candidate | 18 |
| D27 | Sweep cadence & timeout constants | Candidate, values provisional | 19 |
| D28 | Disconnect-quiescence: awareness-based finalization (not a timeout race) | **RESOLVED — not blocking** — per consolidated ruling §9 | 20 |
| D29 | Credential-rotation mid-attempt handling | Candidate | 21 |
| D30 | ACL for `mutation.attempt` (current four-role model) + duplicate-risk bypass guard | **RESOLVED** — extended per consolidated ruling §12 | 26, H |
| D31 | SEC-2 two-role-migration compatibility + explicit re-key follow-up | Candidate, non-blocking-now | 27 |
| D32 | Retention — indefinite for unresolved, configurable pruning for resolved terminal | **RESOLVED** — corrected per consolidated ruling §11 | 29 |
| D33 | Upgrade path | Candidate | 30 |
| D34 | Uninstall behavior | Candidate | 31, J |
| D35 | `mutation_domain` field ownership — registry-validated indexed Char | **RESOLVED — not blocking** — per consolidated ruling §5 | I, O |
| D36 | Rollback procedure (two-phase) | Candidate | 32 |
| D37 | Repo-wide AST/source guard + mutation-wrapper transport guard | **RESOLVED — not blocking** — effort-sizing by direct inspection, per consolidated ruling §14 | 34 |
| D38 | Runtime/concurrency/crash-injection proof requirements — four proof-environment layers | **RESOLVED — Stage 0 merge-acceptance criterion, not a pre-implementation blocker** — per consolidated ruling §15 | 35 |

---

## 3. Full decision detail (L2-D1 – L2-D38)

Each entry gives: **Fact**, **Inference**, **Recommendation**,
**Accepted-candidate wording**, **Alternatives considered**, **Risk**,
**Rollback**, **Exact implementation impact**, **Exact tests**,
**Unresolved question**.

### D1 — Job-row durability fields
*(Items 1, 18)*

- **Fact:** `shopify.connector.job` today has no owner/lease/attempt-identity
  field — ownership is only the transaction-scoped PG row lock
  (`shopify_connector_job.py` `_claim_for_dispatch`, `try_lock_for_update`);
  nothing survives a hard process crash. `started_at`/`finished_at` exist
  and are load-bearing for the retry-window clock and are never reset on
  retry.
- **Inference:** A durable, crash-surviving ownership signal requires new
  fields distinct from `started_at` (which must keep its existing,
  different meaning).
- **Recommendation:** add exactly three core additive fields to
  `shopify.connector.job`. `reconciliation_pending_until` (D13) and
  `mutation_attempt_id` (D14) are separate, D13/D14-owned job-row fields,
  not counted in D1's three.
- **Accepted-candidate wording — RESOLVED (corrected 2026-07-19, per PR #177
  comment 5014806430 item 5, closing an internal inconsistency in this
  entry's own prior wording, which listed a fourth field and then
  contradicted itself about whether it existed):** D1 adds **exactly three**
  job-owned durability fields to `shopify.connector.job`:
  `current_attempt_token` (Char, UUIDv4, regenerated per attempt — the
  CAS/finalize token; **corrected naming, 2026-07-19, per the consolidated
  ruling §5/§8** — previously drafted as `attempt_id`, renamed to avoid
  colliding with `mutation.attempt`'s own per-row `attempt_token` field and
  to read correctly as "the token of the attempt this job currently owns"),
  `owner_worker_ref` (Char, diagnostic, mirrors `call.lease.worker_ref`
  vocabulary), and `running_since` (Datetime, set once per claim at C1,
  **never aliased to `started_at`**). All three join `PROTECTED_JOB_FIELDS`,
  writable only via `env.su`. **`transport_attempted` is not a job field.**
  It exists only on `shopify.connector.mutation.attempt` (D2) and must never
  be duplicated onto the job row or added to job's `PROTECTED_JOB_FIELDS`.
  `reconciliation_pending_until` (D13) and `mutation_attempt_id` (D14,
  `Many2one`-restrict, required for reconciliation jobs) are separate
  job-row fields, each governed by its own decision entry — neither is part
  of D1's three-field count.
- **Alternatives considered:** reuse `started_at` as the staleness clock
  (rejected — proven not-reset-on-retry, already load-bearing for the
  24h retry-window clock; aliasing would make every retried job appear
  instantly stale to the sweep).
- **Risk:** new protected fields widen the sudo-write surface; must be
  covered by the existing AST guard pattern that already inventories sudo
  sites.
- **Rollback:** additive fields, droppable pre-ship; see D33/D36.
- **Exact implementation impact:** `shopify_connector_job.py` field list +
  `PROTECTED_JOB_FIELDS` + `write()` guard; one migration-free upgrade
  (D33).
- **Exact tests:** unit test asserting all three fields reject non-`su`
  writes from every role; unit test asserting `running_since` is set once
  per claim and not mutated by `started_at`'s own logic.
- **Unresolved question:** None.

### D2 — `mutation.attempt` core schema
*(Item 2 — RESOLVED 2026-07-19 per the consolidated Sessions-2-and-3 ruling
§5/§8, superseding this entry's original drafting)*

- **Fact:** No mutation-attempt model exists today. Odoo 19's
  `_sql_constraints` is confirmed silently inert (logs a warning, enforces
  nothing); `models.UniqueIndex` is the current mechanism.
- **Inference:** A dedicated model is required for per-attempt forensics
  beyond what job-row fields alone can carry (real mutation audit trail).
  The two previously-BLOCKED sub-questions this entry deferred to D20
  (`job_id` field type, `mutation_domain` ownership/type) are resolved by
  the consolidated ruling directly, not by this session's own inference —
  recorded here as binding, not re-derived.
- **Recommendation:** new model `shopify.connector.mutation.attempt`, exact
  field list below.
- **Accepted-candidate wording — RESOLVED:**
  - `job_id`: `Many2one('shopify.connector.job', required=True, index=True,
    ondelete='restrict')`. **Resolved, not Integer** — the
    `call_lease.job_id`-style lock-contention concern that motivated the
    non-FK alternative does not apply here: writes to `mutation.attempt`
    come from the single worker that already holds the owning job's claim
    lock (C2/C3), the same sequential-single-writer pattern that already
    makes `job_log.job_id`'s FK+`ondelete='restrict'` safe today.
  - `attempt_token` (Char UUID, required) — the per-row attempt identity,
    unique per job/attempt; matches the job's `current_attempt_token` (D1)
    for the currently-owned attempt.
  - `mutation_domain` (Char, required, indexed) — **resolved, not a
    Selection of either kind.** Validated fail-closed against the
    reconciliation/mutation registry (D15/D16); an unregistered value is
    rejected, never silently accepted. See D35 for the full reasoning —
    this is D35's third option, now the accepted one.
  - `store_id` (Many2one, `related`, stored, indexed, readonly) — D3;
    "derived/stored where supported by the actual job schema" per the
    ruling; verify the exact `job` field name before implementing (D3's own
    disclosed gap).
  - `expected_connection_generation` (Integer, snapshotted at C2) — D18/D29.
  - `expected_store_identity` (Char, `myshopifyDomain` snapshotted at C2) —
    D18, new field this correction adds (previously only compared at
    reconciliation time against the live store record; now also
    snapshotted on the attempt itself for forensic completeness).
  - `remote_mutation_intent` (Char/JSON, identifiers only) — D7 allowlist.
  - `preconditions_snapshot` (JSON, allowlisted) — D7.
  - `business_intent_fingerprint` (Char SHA-256) — D5, new split field.
  - `exact_request_fingerprint` (Char SHA-256) — D5, new split field,
    **includes** `changeFromQuantity` and the idempotency key/directive.
  - `shopify_idempotency_key` (Char UUID, nullable) — D6.
  - `idempotency_valid_until` (Datetime, nullable) — D6, the locally-derived
    boundary (Shopify's 24h window minus the configurable safety margin),
    replacing this entry's earlier unnamed "local staleness window"
    framing with an explicit, queryable field.
  - `transport_attempted` (Boolean, default False) — **lives here only**,
    not duplicated on `job` (corrects D1's earlier drafting).
  - `observed_outcome` (Selection, 4 values, machine-observed only,
    immutable once left `pending`) — **renamed from `outcome`**, D9/D10.
  - `resolution_disposition` (Selection, 2 values, nullable:
    `applied`/`not_applied`) — D10/D11.
  - `resolution_source` (Selection, 2 values, nullable:
    `reconciliation_read`/`manual_admin`) — **new field this correction
    adds**, D10/D11.
  - `resolution_reason` (Text, mandatory when `resolution_disposition` set)
    — D11.
  - `resolution_uid` (Many2one `res.users`) — D11.
  - `resolution_at` (Datetime) — D11.
  - `inconclusive_reconciliation_count` (Integer, default 0) — D17,
    per-attempt scope, resolved sufficient (D17 below).
  - `remote_evidence_refs` (JSON) — D8.
  - `created_at`/`transport_at`/`resolved_at` (Datetime) — commit-point
    timestamps.

  Uniqueness on `(job_id, attempt_token)` via `models.UniqueIndex` (never
  `_sql_constraints`, confirmed silently inert). `transport_attempted` is
  never duplicated independently on both `job` and `mutation.attempt`, per
  the ruling's explicit instruction.
- **Alternatives considered:** fields-on-job only, no dedicated model
  (rejected — insufficient for per-attempt forensics once multiple attempts
  per job exist across retries; weaker audit shape). For `job_id`: plain
  Integer mirroring `call_lease.job_id` (rejected — that field's
  concurrent, multi-worker admission-check access pattern does not apply
  to a single-owner-writes-sequentially model). For `mutation_domain`: both
  a core-fixed Selection and a domain-`selection_add` Selection (both
  rejected — see D35).
- **Risk:** new model = new ACL surface (D30) and new join cost on every
  reconciliation read. `ondelete='restrict'` on `job_id` means a job row
  can never be deleted while any attempt references it — acceptable, since
  neither model is ever deleted under D32's retention policy.
- **Rollback:** pre-ship, drop model cleanly (D36 phase 1); post-ship,
  retained as evidence (D32/D36 phase 2).
- **Exact implementation impact:** new Python model file, new ACL rows
  (D30), new migration-free upgrade entry (D33).
- **Exact tests:** `(job_id, attempt_token)` uniqueness enforcement test
  (concurrent insert attempt); field-type/registry-validation tests
  (`mutation_domain` fail-closed on an unregistered value); a test
  asserting `transport_attempted` exists on `mutation.attempt` only, not on
  `job`.
- **Unresolved question:** None — both sub-questions this entry previously
  deferred to D20 are resolved above.

### D3 — `store_id` denormalization + multi-company scope
*(Item 3)*

- **Fact:** No `company_id` exists anywhere in the store/settings layer
  today (code audit, `shopify_connector_store.py`/`shopify_connector_store_settings.py`).
- **Inference:** Multi-company scoping is out of scope for the MVP by
  construction, not by omission.
- **Recommendation:** add `store_id` as a stored, indexed, readonly
  `related='job_id.store_id'` field for query convenience; explicitly
  declare multi-company out of scope.
- **Accepted-candidate wording:** `store_id` (Many2one, `related`, stored,
  indexed, readonly) on `mutation.attempt`; no `company_id` is added by
  this decision or implied for the future.
- **Alternatives considered:** no denormalization, always join through
  `job_id` (rejected — makes every reconciliation/reporting query more
  expensive for no benefit, since the value is fully derived and stable).
- **Risk:** none beyond normal `related`-field storage cost.
- **Rollback:** drop field, no data loss (derivable from `job_id`).
- **Exact implementation impact:** one `related` field declaration.
- **Exact tests:** assert `store_id` always matches `job_id.store_id` after
  any write path.
- **Unresolved question:** the literal field name for job→store linkage on
  `shopify.connector.job` was not confirmed by direct quote in this
  session's audit (only inferred from `job_enqueue.py`'s generation-capture
  behavior) — must be verified against the actual current field list before
  Stage 0 implementation, not assumed.

### D4 — Attempt granularity = one business pair; batching deferred
*(Items K, L, 33 — directly implements ruling point 5; restated as binding
by the consolidated Sessions-2-and-3 ruling §1, 2026-07-19: "MVP Stage 1
uses exactly one Shopify mutation request per (inventory_item, location)
business pair; one mutation job maps to one mutation-attempt row;
multi-pair batching is excluded from Wave 3 MVP")*

- **Fact:** `InventorySetQuantitiesInput.quantities` is a list — Shopify's
  own schema supports multi-entry batched requests; the CAS field
  (`changeFromQuantity`) lives per-entry, not per-request (source-materials
  refresh §1). No source in this session's research confirms
  `InventorySetQuantitiesPayload`'s `userErrors` carry a per-entry
  field-path index sufficient to build reliable per-entry evidence, and no
  source confirms partial-batch atomicity semantics (does one bad entry
  fail the whole request, or only that entry?).
- **Inference:** Without proof of per-entry evidence shape and partial-batch
  atomicity, an attempt record cannot safely represent more than one
  business pair per row — a batched design today could silently misattribute
  a failure to the wrong pair or infer whole-request success from a
  partially populated response.
- **Recommendation:** **default to one `(inventory_item_id, location_id)`
  pair per mutation request/attempt row**, matching the job layer's
  existing `operation_scope_key` invariant (1 job : 1 pair), until batch
  partial-success semantics are proven or every entry can be independently
  reconciled.
- **Accepted-candidate wording:** one `mutation.attempt` row = exactly one
  `(inventory_item_id, location_id)` pair. Multi-entry `quantities[]`
  batching is **out of scope for Wave 3 Stage 0/Stage 1**. If pursued
  later, it requires a separately-reviewed follow-up decision defining a
  `transport_batch_id` correlation field linking still-independently-tracked
  attempt rows, and Shopify's confirmed per-entry `UserError` field-path
  shape — neither exists today.
- **Alternatives considered:** batch multiple pairs per request per
  attempt (rejected for Stage 0/1 — unproven partial-success semantics);
  batch per request but multiple attempt rows sharing one
  `transport_batch_id` (deferred, not rejected, as the future path once
  per-entry evidence is proven).
- **Risk:** one-pair-per-request has a real throughput cost (more requests,
  more idempotency keys, closer to Shopify's cost-based rate limit) — must
  be weighed against PB-20's ≥300 pushes/hour target at Stage 1 sizing time,
  not at Stage 0.
- **Rollback:** N/A — this is the conservative default, not a feature to
  roll back.
- **Exact implementation impact:** Task 013's push logic must issue one
  `inventorySetQuantities` call per pair, never construct a multi-entry
  `quantities[]` array. **Cross-document correction required:** the Wave 3
  DoR's own text ("batching... where adopted") is superseded by this
  decision and is corrected in this session's update to that file.
- **Exact tests:** a static/AST test asserting no call site constructs a
  `quantities[]` array with length > 1.
- **Unresolved question:** whether Shopify's `UserError` shape carries a
  per-entry field-path index sufficient to ever support batching safely —
  open, non-blocking for Stage 0/1 (batching is simply excluded), blocking
  only for a *future* batching proposal.

### D5 — Two-hash fingerprint split: `business_intent_fingerprint` /
`exact_request_fingerprint`
*(Item 6 — CORRECTED 2026-07-19 per the control-room preliminary review,
PR #177 comment 5013028262 point 1, and bound by the consolidated
Sessions-2-and-3 ruling §3. This entry's original single-fingerprint design
was unsafe as written and is fully superseded below, not merely amended.)*

- **Fact:** No fingerprinting mechanism exists today. `changeFromQuantity`
  is a value this connector actually transmits as a GraphQL variable on
  every `inventorySetQuantities` call (source-materials refresh §1) — it is
  part of "the exact normalized GraphQL operation and exact variables
  transmitted," not a value external to the request.
- **Inference:** **this entry's original design was unsafe.** Excluding
  `changeFromQuantity` from the *only* fingerprint field, as originally
  drafted, meant that field could never be used for forensic replay proof
  or exact-parameter-match verification — a fingerprint that omits a
  transmitted request parameter cannot prove what was actually sent, and
  reusing an idempotency key keyed off such a fingerprint risks masking a
  genuine parameter change. Two genuinely different needs were conflated
  into one field: (a) detecting *stable business intent* across retries
  (which legitimately should not vary with the fresh CAS read), and (b)
  proving *exactly what was transmitted* for forensic/idempotency purposes
  (which must include every transmitted variable, CAS value included).
- **Recommendation:** two distinct SHA-256 hashes, one per need, never
  merged back into one field.
- **Accepted-candidate wording:**
  - `business_intent_fingerprint` = SHA-256 over the stable business intent
    only: `{mutation_domain, inventory_item_id, location_id,
    target_quantity}` for the inventory domain (and the domain's own
    declared equivalent for any future domain) — explicitly **excludes**
    transport and idempotency mechanics (`changeFromQuantity`, the
    idempotency key/directive, any timestamp). Purpose: detect that two
    attempts share the same underlying business goal, for audit/dedup
    reasoning that must not vary with a fresh CAS read.
  - `exact_request_fingerprint` = SHA-256 over the exact normalized
    GraphQL operation document (parsed/re-serialized AST form, not raw
    string) and the exact variables actually transmitted, **including**
    `changeFromQuantity` and the idempotency key/directive. This is the
    field Shopify-parameter-matching and forensic replay proof rely on —
    **never** the business-intent fingerprint. Never reuse an idempotency
    key based on a hash that omits a transmitted request parameter.
- **Alternatives considered:** one merged fingerprint excluding
  `changeFromQuantity` (this entry's original design — **rejected**, unsafe
  per the Inference above); hash the raw request string for either field
  (rejected — whitespace/key-order noise defeats identical-request
  detection).
- **Risk:** low for `business_intent_fingerprint` (forensic-only, not
  safety-load-bearing); `exact_request_fingerprint` is safety-relevant for
  idempotency-key reuse decisions (D6) but is deterministic per attempt, so
  correctly implemented it carries no new risk beyond the hashing itself.
- **Rollback:** both fields inert, droppable.
- **Exact implementation impact:** two normalization helper functions
  (business-intent scope narrower than exact-request scope), unit tested
  for stability across key order.
- **Exact tests:** stability test per fingerprint (same logical request,
  different key orders → same hash); a test asserting
  `exact_request_fingerprint` **changes** when `changeFromQuantity` changes
  (proving it is not excluded); a test asserting
  `business_intent_fingerprint` does **not** change when only
  `changeFromQuantity`/the idempotency key change (proving business intent
  is stable across a fresh CAS read).
- **Unresolved question:** None.

### D6 — Idempotency-key lifecycle + fail-closed defect-code routing
*(Items 7, N — CORRECTED 2026-07-19 per the control-room preliminary
review, PR #177 comment 5013028262 point 3, and bound by the consolidated
Sessions-2-and-3 ruling §4)*

- **Fact:** `@idempotent` is mandatory for `inventorySetQuantities`/
  `inventoryActivate` from API 2026-04; 24-hour retention (source-materials
  refresh §2); `IDEMPOTENCY_CONCURRENT_REQUEST`/`IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/
  `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` exist as user-error codes and are
  absent from the current design's outcome taxonomy.
- **Inference:** the key must be persisted before use (survives crash),
  reused verbatim only within a provably-safe local window, and never
  reused past staleness. `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/
  `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` are **tracking/invariant defect
  signals**, not ordinary transient failures — this entry's original
  routing to `failed_clean`'s normal DEC-009 auto-retry class was wrong:
  auto-retrying a state that indicates the connector's own key/attempt
  bookkeeping is already broken risks compounding the defect rather than
  surfacing it.
- **Recommendation:** `uuid.uuid4().hex`, persisted at C2, request-level and
  attempt-owned (never binding-owned), local staleness window with a
  configurable safety margin below Shopify's 24h; fail-closed routing for
  the two defect-signal codes.
- **Accepted-candidate wording:** `shopify_idempotency_key` validated
  well-formed before interpolation into `@idempotent(key:"...")`, persisted
  at C2. The key is **request-level and attempt-owned** — never
  binding-owned after Layer 2 adoption; a fresh attempt (new CAS cycle)
  always gets a fresh key and a fresh attempt row. Reused verbatim only for
  an **identical exact request** (same `exact_request_fingerprint`, D5) on
  retry of the *same* attempt, within `idempotency_valid_until`
  (Datetime field on `mutation.attempt`, D2 — Shopify's confirmed 24h
  window minus a **configurable** local safety margin; the margin is an
  **implementation choice, not a Shopify fact**, and must be documented as
  such, not hardcoded silently). Past `idempotency_valid_until`:
  reconciliation runs first, **never** a blind fresh-key resend.
  Classification: `IDEMPOTENCY_CONCURRENT_REQUEST` →
  `observed_outcome='uncertain'` (unchanged from this entry's original
  design). `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` and
  `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → **corrected**: both route to a
  new terminal classification, `idempotency_contract_violation`
  (recorded in `remote_evidence_refs`, D8), which sets the job to
  `blocked_manual_review` with a dedicated subreason and is **never
  auto-retried** — these codes should never occur under correct key
  management, and treating them as ordinary `failed_clean` would silently
  mask a real defect behind DEC-009's normal bounded-retry class.
- **Alternatives considered:** always mint a fresh key per HTTP-level retry
  (rejected — defeats the purpose of `@idempotent`). Routing the two defect
  codes through ordinary `failed_clean` auto-retry (this entry's original
  design — **rejected**, per the control-room correction above: a defect
  signal must surface for manual review, not be silently retried).
- **Risk:** a wrongly-sized local margin could either reuse a key Shopify
  has already expired (loses idempotency protection silently) or discard a
  still-valid key too early (unnecessary reconciliation reads) — this risk
  is unchanged by this correction and remains explicitly control-room-owned
  (see Unresolved question).
- **Rollback:** fields inert, droppable pre-ship.
- **Exact implementation impact:** key-generation/validation helper;
  `idempotency_valid_until` computed and persisted at C2;
  `idempotency_contract_violation` added to the manual-review-subreason
  vocabulary (Part 4 item 8's consolidated list).
- **Exact tests:** key reuse within window (same `exact_request_fingerprint`
  only); key non-reuse past `idempotency_valid_until` (routes to
  reconciliation, not fresh resend); `IDEMPOTENCY_CONCURRENT_REQUEST` →
  `uncertain`; both `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` and
  `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → `blocked_manual_review` with
  `idempotency_contract_violation`, asserting no automatic retry occurs.
- **Unresolved question:** the exact numeric safety-margin value (this
  session's original recommendation was 23h) remains this session's own
  Recommendation/inference, with zero source support for the specific
  number — needs explicit control-room ratification and, ideally,
  empirical Shopify round-trip-latency validation before Stage 0 ships
  with a hardcoded default. This is a **tunable-constant question, not an
  architecture blocker** — the mechanism (configurable margin,
  `idempotency_valid_until` field) is fully resolved above.

### D7 — `preconditions_snapshot` allowlist
*(Items 8, 28)*

- **Fact:** No existing PII/payload allowlist mechanism scopes handler-local
  state before persistence; the existing PII-retention sweep
  (`shopify_connector_pii_retention.py`) defaults to disabled per store.
- **Inference:** A write-time allowlist, not a downstream masking sweep, is
  the only guarantee that actually prevents payload/PII leakage into this
  new model, since the sweep cannot be relied upon to ever run.
- **Recommendation:** declare a fixed, per-mutation-domain allowlist
  alongside each domain's reconciliation-matrix row (D15).
- **Accepted-candidate wording:** `preconditions_snapshot`,
  `remote_mutation_intent`, and `remote_evidence_refs` are populated
  **exclusively** from a fixed, per-mutation-domain allowlist of non-PII
  operational identifiers — never from an unfiltered dump of handler-local
  state (no `**kwargs`/`vars()`/`locals()`-style construction). For the
  inventory domain: `{inventory_item_id, location_id, target_quantity,
  change_from_quantity, snapshot_taken_at}`. This is the **sole** redaction
  guarantee at write time (C2) and does **not** depend on the PII-retention
  sweep ever running.
- **Alternatives considered:** rely on the existing PII-retention sweep for
  redaction (rejected — defaults to disabled per store; would leave
  payload-shaped data exposed indefinitely by default).
- **Risk:** an allowlist that is too narrow could omit evidence needed for
  a real reconciliation decision; too broad reintroduces the leakage risk
  it exists to prevent. Balance is a per-domain design choice, reviewed at
  each domain's own matrix-row acceptance.
- **Rollback:** field inert, droppable.
- **Exact implementation impact:** allowlist declared alongside each
  domain's D15 registry entry; enforced by an AST source-guard test, not
  code review alone.
- **Exact tests:** AST test asserting no `**kwargs`/`vars()`/`locals()`
  pattern feeds these three fields; allowlist-completeness test per
  registered domain.
- **Unresolved question:** None (this closes the original design's implied
  "(redacted)" downstream-masking framing, converting it to an explicit
  structural, write-time guarantee).

### D8 — `remote_evidence_refs` structured JSON
*(Item 9)*

- **Fact:** The original design proposed a `Text` field for this evidence.
- **Inference:** Unstructured text is harder to query/audit and easier to
  accidentally overload with payload content than a structured, schema'd
  JSON field.
- **Recommendation:** change to JSON with an explicit shape.
- **Accepted-candidate wording:** `remote_evidence_refs` (JSON):
  `{remote_gids: [...], user_errors: [{code, field}], http_status,
  graphql_error_codes: [...], throttle_status: {maximumAvailable,
  currentlyAvailable, restoreRate} | null}` — identifiers/codes/counts
  only, never payload bodies. Store-identity-mismatch evidence (D18) is
  recorded here too; no separate field needed.
- **Alternatives considered:** free-text log line (rejected — not
  queryable, encourages accidental payload leakage).
- **Risk:** schema drift if a future domain needs a shape this JSON
  structure doesn't anticipate — mitigated by JSON's inherent extensibility
  (additive keys are safe).
- **Rollback:** field inert, droppable.
- **Exact implementation impact:** one field-type change (Text → JSON) plus
  a documented shape.
- **Exact tests:** shape-validation test per outcome path (succeeded,
  failed_clean, uncertain each populate the expected subset of keys).
- **Unresolved question:** None.

### D9 — Outcome taxonomy stays 4-value; THROTTLED→`uncertain`
*(Items 9 partial, M — directly implements ruling point 4)*

- **Fact:** No official Shopify source found in this session's research (or
  the control-room ruling's own cited research) establishes that a
  `THROTTLED` response guarantees the resolver did not execute
  (source-materials refresh §3).
- **Inference:** the original design's `THROTTLED → failed_clean`
  classification was an unlabeled Inference presented as a flat [Fact] —
  a documentation-discipline violation independent of the practical
  question, and practically unsafe if the inference is wrong.
- **Recommendation:** reclassify `THROTTLED` to `uncertain` for every
  mutation domain.
- **Accepted-candidate wording:** `observed_outcome` (**renamed from
  `outcome`, D10 — see below**) remains the closed 4-value Selection
  `pending`/`succeeded`/`failed_clean`/`uncertain`. `THROTTLED`
  (HTTP 429 or GraphQL-body error) is reclassified from `failed_clean` to
  **`uncertain`**, routed through reconciliation like any other ambiguous
  outcome, for every `mutation_domain`, pending an explicit Shopify
  non-execution guarantee (none found as of 2026-07-18). **Re-affirmed by
  the consolidated Sessions-2-and-3 ruling §8:** mutation-side THROTTLED
  remains `uncertain` and reconciliation-first until Shopify provides a
  binding non-execution guarantee; the "recommended backoff time is one
  second" language must never be cited as an established fact without a
  precise official source — it remains a stated recommendation, not a
  documented contractual minimum.
- **Alternatives considered:** keep `failed_clean` (rejected — the ruling
  and this session's independent research agree no such guarantee exists;
  treating an unproven claim as fact risks a real duplicate-mutation
  failure mode); add a 5th/6th outcome value specifically for THROTTLED
  (rejected — `uncertain`'s existing reconcile-first handling already
  covers it correctly; a new value adds complexity without new safety).
- **Risk:** treating THROTTLED as `uncertain` increases reconciliation-read
  volume under sustained rate-limiting — an operational cost, not a
  correctness risk; acceptable trade-off given the alternative is a
  possible silent duplicate mutation.
- **Rollback:** N/A — this is the conservative default.
- **Exact implementation impact:** the response-classification helper's
  THROTTLED branch changes target outcome value; design doc §5.1/§10
  updated (done, this session).
- **Exact tests:** outcome-classification test asserting THROTTLED →
  `uncertain`, not `failed_clean`.
- **Unresolved question:** whether Shopify's THROTTLED response ever has a
  genuine server-side execution effect remains factually open — the
  conservative classification is safe to *ship* without resolving it, but
  the underlying fact is not resolved (source-materials refresh Part 7
  item 8 equivalent).

### D10 — Observed-outcome/resolution orthogonal model (immutable
`observed_outcome`)
*(Items 4, 5, A — CORRECTED 2026-07-19. The control-room preliminary
review, PR #177 comment 5013028262 point 2, found this entry's original
"Layer R forces Layer O" design **contradicted the three-layer model this
same entry itself introduced** — a human/machine resolution must never
rewrite a machine-observed outcome. The consolidated Sessions-2-and-3
ruling §2 makes the corrected design below binding, and explicitly rejects
Session 3's alternative proposal of one merged six-value enum — see Part
0.5.)*

- **Fact:** The current design doc uses `pending`/`succeeded`/`failed_clean`/
  `uncertain` in its outcome taxonomy (§5.1) but separately describes an
  operator override producing `resolved_applied`/`resolved_not_applied`
  (§6) — two vocabularies for what reads like the same concept, never
  reconciled in the source document.
- **Inference:** these are not the same concept — one is a machine-observed
  outcome, the other is a human or reconciliation-derived judgment recorded
  only when the machine path is exhausted. Conflating them into one flat
  enum is the actual defect, not either vocabulary individually. **This
  entry's own first-drafted correction repeated a milder version of the
  same defect**: having a resolution action "atomically force `outcome` to
  `succeeded`/`failed_clean`" still lets a human/machine judgment overwrite
  the machine-observed record, destroying the historical fact of what was
  actually observed. The two must instead stay genuinely orthogonal, with a
  third, derived concept (effective disposition) computed from both without
  mutating either.
- **Recommendation:** two orthogonal fields plus a shared, side-effect-free
  derivation helper — not a hierarchy where one layer overwrites another.
- **Accepted-candidate wording — RESOLVED:**
  - **Layer J (Job)** — `shopify.connector.job.state`: unchanged 10-value
    machine, zero new states/transitions.
  - **`observed_outcome`** (renamed from `outcome`) —
    `mutation.attempt.observed_outcome`: closed 4-value Selection
    (`pending`/`succeeded`/`failed_clean`/`uncertain`, D9), **machine-observed
    only**. **Immutable once it leaves `pending`** — no code path, including
    D11's override action and the reconciliation-read path, may ever write
    to this field again after its first non-`pending` value is committed. It
    remains the *only* field recording what transport evidence actually
    showed.
  - **`resolution_disposition`** — `mutation.attempt.resolution_disposition`:
    new, separate, nullable 2-value Selection (`applied`/`not_applied`),
    set only by (a) a reconciliation-read verdict or (b) D11's Admin-only
    override — **never** by direct assignment elsewhere. Paired with two new
    fields: `resolution_source` (nullable, `reconciliation_read` /
    `manual_admin`) and the existing `resolution_reason`/`resolution_uid`/
    `resolution_at`.
  - **Shared effective-disposition helper** (new, replaces the old
    "atomically force outcome" mechanism): a pure function of both fields,
    computing the disposition any job-consequence logic must read —
    - `observed_outcome == 'succeeded'` → **applied**
    - `observed_outcome == 'failed_clean'` → **not_applied**
    - `observed_outcome == 'uncertain'` and `resolution_disposition ==
      'applied'` → **applied**
    - `observed_outcome == 'uncertain'` and `resolution_disposition ==
      'not_applied'` → **not_applied**
    - `observed_outcome == 'uncertain'` and `resolution_disposition` is
      null → **unresolved**
    Job consequences: effective **applied** → the original mutation job
    completes without resend; effective **not_applied** → the original job
    becomes retry-eligible, and a **new** attempt is created only on its
    next dispatch (never by mutating the resolved attempt row); effective
    **unresolved** → reconciliation or manual review only, no other path.
    `resolved_applied`/`resolved_not_applied` as free-floating string
    values are retired — they exist only as `resolution_disposition`'s two
    values, read exclusively through the helper above, never directly.
  - Manual resolution (D11) requires Administrator, a mandatory reason,
    full actor/time audit, and **never** performs a Shopify mutation itself
    — it only ever sets `resolution_disposition`/`resolution_source=
    'manual_admin'`/`resolution_reason`/`resolution_uid`/`resolution_at`.
  Full transition table: Part 5 below (updated to reflect the immutable
  `observed_outcome`, not the retired force-overwrite mechanism).
- **Alternatives considered:** one flat enum spanning both machine and
  human states (rejected — the original design's own internal
  inconsistency). This entry's own first-drafted "resolution forces
  outcome" correction (rejected on preliminary review — still a form of
  overwrite). Session 3's proposed single six-value outcome enum spanning
  both machine and human/reconciliation dispositions (rejected by the
  consolidated ruling §2 — would re-introduce exactly the same conflation
  this decision exists to prevent, just with more values).
- **Risk:** an orthogonal two-field model is more complex to query than one
  flat enum — mitigated by the shared effective-disposition helper being
  the single, mandatory read path for any consequence logic, so no call
  site needs to reason about the two fields directly.
- **Rollback:** additive fields, droppable pre-ship; post-ship, retained
  per D32.
- **Exact implementation impact:** `observed_outcome`/`resolution_disposition`/
  `resolution_source`/`resolution_reason`/`resolution_uid`/`resolution_at`
  fields; one new shared, pure (no side effects) effective-disposition
  helper method used by every consequence-reading call site (retry
  eligibility, job completion, reporting).
- **Exact tests:** full state-machine unit test covering all transition
  steps in Part 5; a test asserting `observed_outcome` is rejected as
  read-only/immutable by any write attempt after it first leaves `pending`
  (including from D11's override action); a test asserting the
  effective-disposition helper is the *only* code path any
  retry-eligibility or job-completion logic reads (`observed_outcome`/
  `resolution_disposition` are never read directly for that purpose); a
  test covering all five helper branches above.
- **Unresolved question:** None — the canonical names
  (`resolution_disposition`/`resolution_source`/`action_resolve_mutation_attempt`)
  are ratified by the consolidated ruling itself, closing the naming
  question this entry previously carried open.

### D11 — Administrator-only resolution-override action
*(Items 5, 25, H.3 — CORRECTED 2026-07-19: field names updated to match
D10's immutable-`observed_outcome` model, and the overlap this entry left
open against the two pre-existing `blocked_manual_review→queued` actions is
now closed per the consolidated Sessions-2-and-3 ruling §12.)*

- **Fact:** `action_manual_retry` (job_actions.py) and
  `action_resolve_manual_review` (job.py) already exist, both
  Reviewer/Admin-gated, both reaching `blocked_manual_review→queued`,
  neither requiring a mandatory reason.
- **Inference:** D11 adds a **third** mechanism reaching a related job-state
  transition. Left unreconciled, either pre-existing action could be used
  as a bypass around this action's stricter Admin-only/mandatory-reason
  gate for a duplicate-risk, mutation-attempt-linked job — the exact
  higher-stakes case this action's stricter gate exists for.
- **Recommendation:** a single sanctioned action, deliberately stricter
  than the two existing mechanisms, **and** an explicit guard closing the
  bypass the two existing mechanisms would otherwise leave open.
- **Accepted-candidate wording:** `action_resolve_mutation_attempt`,
  restricted to `group_shopify_connector_admin` only, **no Reviewer
  bypass** (matching `action_mask_customer_pii`'s precedent, not
  `action_manual_retry`'s — justified because a wrong call causes silent,
  permanent Odoo/Shopify divergence with no automatic re-check, a
  materially higher-stakes error class). Gated on
  `observed_outcome=='uncertain'` and the job being
  `blocked_manual_review`/`manual_review_subreason='duplicate_risk'`;
  requires a mandatory, redaction-passed reason (`UserError` otherwise).
  One narrow `sudo()` write sets `resolution_disposition`/
  `resolution_source='manual_admin'`/`resolution_reason`/`resolution_uid`/
  `resolution_at` — **`observed_outcome` is never written by this action**
  (D10's immutability rule) — paired atomically with the job's existing
  sanctioned `blocked_manual_review→queued` transition and exactly one
  `job.log` row (`event_type='manual_action'`). The override never edits
  remote Shopify state — any correction is a new, ordinary, fully-wrapped
  mutation job. **Closed bypass (new, per the consolidated ruling §12):**
  both pre-existing generic actions, `action_manual_retry` and
  `action_resolve_manual_review`, are updated to explicitly **refuse** any
  job whose `manual_review_subreason == 'duplicate_risk'` and which is
  linked to a `mutation.attempt` row — raising a `UserError` directing the
  operator to `action_resolve_mutation_attempt` instead. This closes the
  overlap this entry previously left open (Part 4 item 9) by making the
  two older, less-strict actions structurally incapable of touching a
  mutation-attempt-linked duplicate-risk job, rather than merely
  documenting a precedence convention.
- **Alternatives considered:** reuse `action_manual_retry` or
  `action_resolve_manual_review` directly (rejected — neither requires a
  mandatory reason nor is Admin-only). Leaving the two older actions
  untouched and merely documenting precedence (this entry's original
  approach — rejected: a documented convention does not stop a Reviewer
  from calling the less-strict action directly; only an explicit code-level
  refusal does).
- **Risk:** operator error (wrong disposition) causes silent Odoo/Shopify
  divergence — mitigated by mandatory reason + audit row + Admin-only gate
  + the closed bypass, not eliminated.
- **Rollback:** remove the action; underlying jobs remain
  `blocked_manual_review` (no data loss, just no override path); the two
  older actions' refusal guard is a safety addition, not itself rollback
  candidate.
- **Exact implementation impact:** one new server action method, ACL
  restricted to Admin group (D30), one `job.log` write; one guard clause
  added to each of the two pre-existing actions.
- **Exact tests:** Reviewer-denied test; missing-reason `UserError` test;
  atomic-commit test (resolution fields + job transition + log row
  all-or-nothing, `observed_outcome` untouched); a test asserting
  `observed_outcome`'s value is byte-identical before and after the
  override action runs; a test asserting both pre-existing actions raise
  `UserError` on a `duplicate_risk` mutation-attempt-linked job.
- **Unresolved question:** None — the overlap this entry previously left
  open is closed above.

### D12 — CAS field-name correction
*(Cross-cutting — directly implements ruling point 3)*

- **Fact:** `changeFromQuantity` is the correct, current (2026-07) CAS field
  name; `compareQuantity`/`ignoreCompareQuantity` do not exist as input
  fields from API 2026-04 onward (source-materials refresh §1, four
  independent official citations).
- **Inference:** this is a resolved conflict between the project's own
  stale internal documents, not an unresolved conflict between official
  Shopify sources.
- **Recommendation:** correct every current-facing occurrence.
- **Accepted-candidate wording:** every attempt-schema field, matrix row,
  and code comment referencing the CAS mechanism must use
  `changeFromQuantity`. Corrected in this session: `dec-031-layer-2-mutation-safety-design.md`
  §3/§4.2. **Not corrected in this session (out of allowed-files scope,
  flagged as required follow-up):** `inventory-operating-model.md` §4.4;
  `task-013-inventory-sync-implementation-packet.md`'s "CAS via
  `compareQuantity`" heading (its own D-013-3 decision text already says
  `changeFromQuantity` correctly — only the surrounding heading/rationale
  text is stale and reads as self-contradictory).
- **Alternatives considered:** none — this is a factual correction, not a
  design choice.
- **Risk:** a reconciliation-triggered retry built on the wrong field name
  would fail at GraphQL schema-validation, not merely receive an unexpected
  CAS mismatch — i.e. D23–D25's entire recovery path is inert until this
  correction lands in code. This makes the correction a **hard implementation
  prerequisite**, not a cosmetic cleanup.
- **Rollback:** N/A — factual correction.
- **Exact implementation impact:** every place D2/D7 reference the CAS
  value must use the corrected field name from day one of Stage 1
  implementation.
- **Exact tests:** a static test asserting no source file under
  `addons/shopify_connector_inventory/**` (once created) references
  `compareQuantity` or `ignoreCompareQuantity`.
- **Unresolved question:** None for the field name itself. The two
  out-of-scope documents above remain stale until a follow-up session with
  those files in its allowed list corrects them — **this must happen before
  Stage 1 implementation begins**, since Sol would otherwise read
  contradictory source documents.

### D13 — Job-layer reconciliation-pending gate
*(Items F, 23)*

- **Fact:** No job state or gating field exists today for "waiting on a
  reconciliation read."
- **Inference:** overloading `blocked_manual_review` (human-gated exit only
  — defeats the automatic happy path) or `retry_waiting` (reintroduces the
  exact duplicate-execution race Layer 2 exists to prevent) were both
  considered and rejected; a non-state gating field is the correct shape.
- **Recommendation:** a new Datetime gating field, not a new job state.
- **Accepted-candidate wording:** add `reconciliation_pending_until`
  (Datetime, nullable, protected) to `shopify.connector.job`. Set in the
  same transaction as the `observed_outcome='uncertain'` attempt commit and
  reconciliation-job creation (D14). `_claim_for_dispatch`'s WHERE clause
  excludes any job with a non-null, non-expired value. The reconciliation
  job's successful commit clears the field in the same transaction it
  writes the resolved outcome/requeues the job. If the deadline expires
  before reconciliation completes, the stale-owner sweep (D26) treats it as
  a stale-owner case, never a silent re-claim.
- **Alternatives considered:** new job state `awaiting_reconciliation`
  (rejected — violates the design's own "zero new states" commitment for
  no added safety); overload `blocked_manual_review` (rejected — human-gated
  only) or `retry_waiting` (rejected — race risk).
- **Risk:** a gating field that is forgotten in one code path (e.g. a
  future domain's handler) could let `_claim_for_dispatch` re-claim a job
  still awaiting reconciliation — mitigated by the field living in the
  shared, non-domain-specific WHERE clause, not per-domain logic.
- **Rollback:** additive field, droppable pre-ship.
- **Exact implementation impact:** `_claim_for_dispatch`'s WHERE clause
  gains one condition; D14's reconciliation-job creation and this field's
  set/clear are one atomic commit.
- **Exact tests:** test asserting a job with a future
  `reconciliation_pending_until` is never claimed; test asserting expiry
  routes to the sweep, not silent re-claim.
- **Unresolved question:** None — this closes a direct, previously
  unflagged contradiction between the design's "no new state" commitment
  and its "reconcile-then-retry only" requirement, independently discovered
  by two separate review clusters (strong convergent evidence).

### D14 — Reconciliation-job linkage (Many2one-restrict, required)
*(Items 10, E — CORRECTED 2026-07-19 per the consolidated Sessions-2-and-3
ruling §5/§8, which overrides this entry's original non-FK design)*

- **Fact:** `call.lease.job_id` is a deliberate non-FK Integer, specifically
  to avoid `FOR KEY SHARE`/`FOR NO KEY UPDATE` lock contention with
  `_claim_for_dispatch`'s *concurrent, multi-worker admission-check* access
  pattern. A reconciliation job's linkage is a fundamentally different
  access shape: created once, at C3, by the single worker that owns the
  originating attempt, and read once at reconciliation dispatch — never
  concurrently admission-checked the way `call_lease` rows are.
- **Inference:** the lock-contention concern that justified `call_lease`'s
  non-FK Integer does not transfer to this field — this entry's original
  non-FK design over-applied that precedent to an access pattern it does
  not fit, the same correction D2 makes for `mutation_attempt.job_id`.
- **Recommendation:** a required Many2one, matching D2's `job_id`
  correction.
- **Accepted-candidate wording — RESOLVED:** a reconciliation-read job
  links to its target attempt via `mutation_attempt_id`:
  `Many2one('shopify.connector.mutation.attempt', required=True (for
  reconciliation jobs), index=True, ondelete='restrict')` on
  `shopify.connector.job`. **Frozen at creation, never lazily resolved**:
  the same commit that sets `observed_outcome='uncertain'` (C3) creates the
  reconciliation job with `mutation_attempt_id` set to that exact attempt
  record. The reconciliation handler looks up the linked record directly
  (no compound-key lookup needed, since the FK is precise) and fails closed
  to `blocked_manual_review` if the target row's `observed_outcome` is no
  longer `uncertain` at dispatch time. A new `operation_scope_key`
  convention is needed for reconciliation jobs (e.g.
  `reconcile:{store}:{mutation_domain}:{attempt_token}`), since `enqueue()`
  has no idempotency/scope-key mechanism of its own for this job type.
- **Alternatives considered:** non-FK Char storing the attempt token (this
  entry's original design — **rejected**, over-applied the `call_lease`
  lock-contention precedent to a non-concurrent access pattern);
  "most recent attempt for job_id" lookup (rejected — unsafe under
  retries/races, the exact scenario reconciliation exists to handle).
- **Risk:** `ondelete='restrict'` means a `mutation.attempt` row can never
  be deleted while any reconciliation job still references it — acceptable
  under D32's retention policy, since attempt rows are never hard-deleted.
- **Rollback:** additive field, droppable pre-ship.
- **Exact implementation impact:** one new Many2one field + one new
  `operation_scope_key` convention + one dispatch-time consistency check.
- **Exact tests:** test asserting a reconciliation job created for a
  superseded attempt fails closed at dispatch, not silently proceeding;
  test asserting `ondelete='restrict'` prevents deleting a referenced
  attempt row.
- **Unresolved question:** None for the linkage mechanism itself; see D24
  for an orphaned question about reconciliation-verdict evidence priority
  that touches this area but is not resolved here.

### D15 — Reconciliation-strategy registry
*(Items 11, O)*

- **Fact:** `_get_replay_policies()`/`_get_handlers()` are the existing,
  accepted seam pattern (domain `_inherit` + `super()` + add-only merge,
  fail-closed default, build-time completeness test).
- **Inference:** the same pattern should govern reconciliation strategies,
  for consistency and because it is proven.
- **Recommendation:** a structurally identical new seam.
- **Accepted-candidate wording:** a new `@api.model` method,
  `_get_reconciliation_strategies()`, structurally identical to
  `_get_replay_policies()`: domain modules extend via `_inherit`+`super()`+
  add-only merge; a build-time completeness test asserts every
  `mutation_domain` value used anywhere has a matching entry; a runtime
  fail-closed accessor returns nothing for an undeclared domain. The two
  registries must stay in lockstep via a **combined** completeness test.
  Together with D30's ACL posture and D35's `mutation_domain` ownership
  resolution, this is the mechanism keeping core domain-agnostic (O's
  validation note): any PR adding a literal domain-specific value or
  `if mutation_domain == '...'` branch directly inside a core file fails
  review under this decision.
- **Alternatives considered:** inline per-domain `if` branching in core
  dispatch code (rejected — exactly the anti-pattern the existing
  `_get_handlers()`/`_get_replay_policies()` seams were built to avoid).
- **Risk:** two parallel registries (replay-policy, reconciliation-strategy)
  that drift out of lockstep would silently misroute a mutation domain —
  mitigated by the combined completeness test.
- **Rollback:** N/A — registry mechanism, not a feature to disable
  independently of the domains that use it.
- **Exact implementation impact:** one new `@api.model` method + one
  combined build-time completeness test spanning both registries.
- **Exact tests:** completeness test (every `mutation_domain` has both a
  replay-policy and reconciliation-strategy entry); fail-closed runtime
  test (undeclared domain returns nothing, never a default-safe value).
- **Unresolved question: None — RESOLVED 2026-07-19** (per PR #177 comment
  5014806430 item 3). Which model hosts `_get_reconciliation_strategies()`
  was left open by the original design document (a genuine gap in the
  *original* design, not introduced by this review); the control room has
  now bound this bindingly to `shopify_connector_job_dispatch.py`, by
  analogy with `_get_replay_policies()`'s existing home. No new dedicated
  model file is authorized for this purpose.

### D16 — Domain-registration fail-closed runtime gate + mutation-wrapper/
API-client enforcement
*(Item 12 — EXTENDED 2026-07-19 per the consolidated Sessions-2-and-3
ruling §14, which requires an explicit relationship between Layer 2 and
`execute_business` and a runtime API-client-level guard, in addition to
this entry's original C2 registry gate)*

- **Fact:** Layer 1's existing fail-closed mechanism (`_get_replay_policy`)
  is a runtime *default value* (undeclared → conservative default), not an
  *execution prohibition* (it never stops a handler from running).
- **Inference:** the design's Hard Rule 7 ("a mutation without a safe
  reconciliation strategy fails closed — it may not be registered or
  executed") requires more than the weaker default-value mechanism alone
  delivers.
- **Recommendation:** an explicit runtime gate before C2.
- **Accepted-candidate wording:** before any C2 attempt-intent commit, the
  handler must call the D15 registry; if it returns no entry, the handler
  must not commit or transport — it fails the job closed to
  `blocked_manual_review`/`manual_review_subreason='no_reconciliation_strategy'`.
  This is a **runtime** gate, independent of and complementary to D15's
  build-time completeness test.
- **Alternatives considered:** rely on the build-time test alone (rejected
  — a build-time test does not stop a runtime execution path if the test
  itself is ever skipped/broken; defense in depth requires both).
- **Risk:** none beyond the added registry-lookup cost per attempt
  (negligible).
- **Rollback:** N/A — safety gate, not a feature to disable.
- **Exact implementation impact:** one gate check inserted before every
  C2 commit path.
- **Exact tests:** test asserting a domain with no registry entry never
  reaches C2, regardless of build-time test status.
- **Unresolved question:** **directly entangled with D12** — because the
  inventory domain's own matrix entry currently cites the wrong CAS field,
  under this decision's own logic the inventory domain does not currently
  describe an implementable, let alone safe, strategy, and must be treated
  as functionally unregistered until D12's correction lands in the matrix.

**Extension — mutation-wrapper/API-client enforcement (new, 2026-07-19,
consolidated ruling §14):** the C2 registry gate above stops an
*unregistered domain* from reaching transport; a second, independent guard
is required to stop *any* mutation call — registered domain or not — from
reaching transport outside the C1/C2/NET/C3 wrapper entirely. **Accepted-
candidate wording:** `shopify_connector_api_client.py`'s send path must
fail closed — raise, never silently proceed — when a GraphQL document
containing a `mutation` operation is submitted without a valid Layer 2
attempt context/token (the current attempt's `attempt_token`, verified
against the job's `current_attempt_token`). This is a **runtime** check
inside the API client itself, independent of and complementary to (a) this
decision's own C2 registry gate (stops unregistered domains) and (b) D37's
repo-wide AST transport guard (stops call sites bypassing the wrapper
entirely, at build/CI time). The three layers are defense in depth, not
redundant: the AST guard catches a bypass statically before merge; the
API-client runtime guard catches it if the AST guard is ever bypassed or a
call site it doesn't cover is added; the C2 registry gate catches an
unregistered domain even when a valid attempt context exists.
`shopify_connector_api_client.py` is therefore added to the Stage 0 allowed
files (previously absent — corrected in the Stage 0 packet, §18 below).
- **Exact tests (extension):** a test asserting the API client raises when
  a mutation document is submitted with no attempt context; a test
  asserting a valid attempt context permits the call to proceed to
  transport; a test asserting a read-only (non-mutation) document is
  unaffected by this guard.

### D17 — Inconclusive-reconciliation cap (N=3), per-attempt scope
*(Item 24 — RESOLVED 2026-07-19 per the consolidated Sessions-2-and-3
ruling §7, closing this entry's own previously-BLOCKING unresolved
question)*

- **Fact:** the original design's "N=3" language never distinguished
  consecutive-inconclusive-verdicts from total-retry-cycles.
- **Inference:** if the counter resets every time a new `attempt_id` is
  minted (as its natural placement on the attempt row implies), a mutation
  alternating THROTTLED-triggered retries with genuine `uncertain` outcomes
  could accumulate 3 inconclusive verdicts *per attempt row* without ever
  tripping the cap across the full retry chain — silently defeating its
  purpose.
- **Recommendation:** add the counter, per-attempt scope, resolved as
  sufficient rather than left open.
- **Accepted-candidate wording — RESOLVED:** add
  `inconclusive_reconciliation_count` (Integer, default 0, protected) to
  `mutation.attempt`, **scoped per uncertain mutation attempt** (resets on
  each new `attempt_token`, as originally schema'd). Incremented only on a
  literal reconciliation-read verdict of **"inconclusive"** (not
  "not-applied," a different, fully-resolving verdict), under a re-acquired
  row lock (mirroring `_recover_after_concurrency_conflict`'s discipline)
  so two racing reconciliation jobs cannot both silently increment past the
  cap. At exactly 3 inconclusive verdicts on the same attempt row: the
  original job transitions to `blocked_manual_review` with
  `manual_review_subreason='duplicate_risk'`, in the same atomic commit as
  the resolution write and audit log entry — retried on a PostgreSQL
  serialization-conflict failure, never silently dropped. **Why per-attempt
  scope is sufficient, closing this entry's original concern:** the
  original concern was that alternating THROTTLED-triggered retries with
  genuine `uncertain` outcomes across *different* attempt rows could let
  the cap "never fire" if scoped per-attempt. This concern does not hold
  under this design's own retry-eligibility rule (D10): **no new mutation
  attempt may be created until the current `uncertain` attempt reaches a
  resolved effective disposition** (`applied` or `not_applied`) — there is
  no path by which a fresh attempt row's counter resets while the prior
  attempt is still accumulating inconclusive verdicts, because the prior
  attempt must itself resolve (including, if necessary, via this very cap)
  before a new attempt can exist at all. The cap is therefore
  cross-retry-effective without needing cross-attempt persistence.
- **Alternatives considered:** track the count at job level instead
  (surviving `attempt_token` regeneration) — this entry's own earlier
  Recommendation direction, **rejected** by the resolution above: it is
  unnecessary once the retry-eligibility rule's sequencing guarantee is
  applied, and job-level tracking would require reconciling the counter
  against manual interventions and job-level retries for no additional
  safety benefit.
- **Risk:** none beyond the accepted operational cost of routing to manual
  review after 3 inconclusive reads on a single attempt — the scoping
  concern that motivated this entry's original "BLOCKING" framing is
  resolved above, not merely accepted as residual risk.
- **Rollback:** additive field, droppable pre-ship.
- **Exact implementation impact:** one Integer field + one row-locked
  increment path; one atomic-commit routine spanning the resolution write,
  the job transition, and the audit log entry, with retry-on-serialization-
  failure.
- **Exact tests:** concurrent-increment race test (two reconciliation jobs
  racing to increment, cap must not be bypassable); cap-trip test at
  exactly 3; a test proving the sequencing guarantee itself — no new
  attempt row can be created while a prior attempt's
  `inconclusive_reconciliation_count` is still below 3 and unresolved;
  serialization-conflict retry test for the atomic cap-trip commit.
- **Unresolved question:** None — resolved above.

### D18 — Store-identity-change detection
*(Items 22, G)*

- **Fact:** `store.py` (approximately line 295) already has a single-field
  string-equality store-identity check used elsewhere (e.g. the connection
  probe).
- **Inference:** reusing this exact check, rather than inventing a new
  multi-field identity fingerprint, avoids creating two divergent identity
  definitions with no grounding-material evidence justifying the second
  one.
- **Recommendation:** reuse the existing check, apply it as the first step
  of every reconciliation read, and snapshot both identity and generation
  on the attempt itself for forensic completeness.
- **Accepted-candidate wording — EXTENDED 2026-07-19 per the consolidated
  Sessions-2-and-3 ruling §10:** each attempt record snapshots
  `expected_connection_generation` (D2/D29) and `expected_store_identity`
  (D2, new field — the `myshopifyDomain` value in effect when the request
  was sent) at C2. Every reconciliation read begins by verifying the
  **current** `myshopifyDomain` (queried via `shop { myshopifyDomain }`
  alongside domain-specific selection) against the attempt's snapshotted
  `expected_store_identity`, as the **first** evaluation step, before
  interpreting any other response data. Comparison reuses the existing
  single-field string-equality check verbatim. On mismatch: route directly
  to `blocked_manual_review`/`manual_review_subreason='store_identity_mismatch'`
  (new, distinct from `duplicate_risk`), bypassing the normal `uncertain`
  reconcile-then-retry flow entirely, and **never** retry the mutation on a
  store-identity mismatch. No new check is added to `_admit`/ordinary
  mutation-send admission — cost is scoped to reconciliation only.
  **Companion fix:** `_run_connection_probe`'s existing domain-mismatch
  branch must additionally call `action_mark_reconnect_needed` (closing a
  pre-existing asymmetry with the auth-failure path). **Correction to a
  stale claim (ruling §10):** `_mutate_token`'s existing behavior already,
  correctly, bumps `connection_generation` atomically on any credential
  set/replace while `connected` (verified directly against code, D29) —
  any prior document text implying `connection_generation` is *not*
  already bumped by lifecycle actions is stale and is corrected here: the
  bump is confirmed existing, current behavior, not a gap this decision
  needs to close.
- **Alternatives considered:** a new multi-field identity fingerprint
  (rejected — no grounding-material evidence justifies it over the
  existing single-field check; would create two divergent identity
  definitions in the codebase).
- **Risk:** a store-identity change followed by neither an `uncertain`
  outcome nor a manual probe remains **undetected** by this mechanism —
  disclosed, not hidden, as an accepted residual gap (see below).
- **Rollback:** additive check, droppable.
- **Exact implementation impact:** one query-shape addition to
  reconciliation reads; one companion fix to `_run_connection_probe`.
- **Exact tests:** store-identity-mismatch test (mismatched domain routes
  to the new manual-review subreason, not the normal reconcile path).
- **Unresolved question:** **disclosed, accepted residual gap, not fully
  closable within this mechanism** — closing it fully would require either
  a new periodic identity-reverification cron or moving the check into
  `_admit` itself (rejected on cost grounds here). **The control room must
  explicitly accept this residual gap for MVP**, not have it silently
  assumed closed.

### D19 — Transaction/commit-point protocol (C1/C2/NET/C3)
*(Item 13 — RESOLVED 2026-07-19, protocol content bound by the
consolidated Sessions-2-and-3 ruling §6)*

- **Fact:** the original design doc justifies its C2 choice by citing
  Odoo's `_commit_progress()` API as the pattern `_drain_one` "exactly"
  follows. Direct code reading shows `_drain_one` uses a bare, commented
  `cr.commit()`, **not** the `_commit_progress()` helper.
- **Inference:** the design's own citation for this pattern is factually
  wrong and must be corrected in the source document, not merely noted
  here (done in this session's update to the design doc).
- **Recommendation:** replace the single-commit dispatch transaction, for
  mutation-domain job types only, with four discrete, sequential,
  independently-recoverable commits/windows.
- **Accepted-candidate wording — RESOLVED:**
  ```
  C1: main-cursor claim commit — lock job; set state='running';
      set current_attempt_token; set owner_worker_ref;
      set running_since → COMMIT.
  C2: dedicated side-cursor attempt-intent commit — create the
      mutation.attempt row; record allowlisted intent/preconditions
      (D7); record both fingerprints (D5); record the idempotency key
      (D6); conservatively set transport_attempted=True → COMMIT,
      strictly before any network call. All request data needed for
      the mutation body is materialized into plain, immutable Python
      values before this commit — never re-derived after it.
  NET: bounded network call only — no main-cursor ORM or SQL
      operation occurs; no open main-cursor transaction spans this
      window; no PostgreSQL lock is held; the side cursor from C2 is
      already committed and closed.
  C3: fresh main transaction — invalidate/re-browse (Odoo REPEATABLE
      READ requires this, D21); re-lock the job; verify
      current_attempt_token matches the attempt this worker holds;
      write response evidence and observed_outcome (D9/D10); apply the
      corresponding job transition atomically → COMMIT.
  ```
  Non-mutation job types (`local_only`, `remote_read_replay_safe`) retain
  the existing single-commit `_drain_one` path unchanged. **C2's use of a
  dedicated side cursor (not the main cursor) is now the accepted design —
  see D20.**
- **Alternatives considered:** keep the single-commit path for mutation
  types too (rejected — provides no crash-recoverable intermediate state,
  the entire reason Layer 2 exists); C2 on the main cursor (this entry's
  original open alternative — rejected, see D20).
- **Risk:** ~2 extra commits per mutation attempt (C1 already exists in the
  job-claim design; C2 on its own side cursor, and the C3 re-lock, are new)
  — small, bounded, and dwarfed by the network round-trip.
- **Rollback:** scoped to mutation job types only; non-mutation types are
  unaffected and require no rollback consideration.
- **Exact implementation impact:** `_dispatch_one`/`_invoke_handler`
  branch by job-type class (mutation vs. non-mutation), each with its own
  commit-point implementation; C2 opens and uses its own side cursor,
  distinct from `self.env.cr`.
- **Exact tests:** see D38 for the full runtime/concurrency/crash-injection
  test requirements.
- **Unresolved question:** None — C2's cursor placement is resolved (D20).

### D20 — C2 cursor placement (side cursor)
*(Item 14 — RESOLVED, not blocking, 2026-07-19 per the consolidated
Sessions-2-and-3 ruling §6, which also SPLITS this entry: the `job_id`
field-type sub-question this entry originally combined with cursor
placement is now resolved separately under D2, per the control-room
preliminary review's point 6 requiring the split)*

- **Fact:** `call_lease`'s `_admit` pattern already proves a side-cursor
  commit-before-network model works in this codebase: admitted under `FOR
  SHARE`, committed on a dedicated cursor **before** the network call, with
  no dependency on the main cursor's state.
- **Inference:** the design's original justification for main-cursor C2
  rested on the now-corrected false `_commit_progress()` citation (D19)
  and never engaged with the actual isolation property a side cursor
  provides: committing C2 on a side cursor **structurally eliminates** the
  "unrelated main-cursor business changes accidentally co-committed at C2"
  risk, rather than merely requiring a test to catch it after the fact
  (D21's original framing).
- **Recommendation:** adopt the side-cursor design, mirroring `call_lease`'s
  proven `_admit` pattern.
- **Accepted-candidate wording — RESOLVED:** C2 commits on a **dedicated
  side cursor**, not the main cursor, mirroring `call_lease`'s `_admit`
  pattern exactly. This is a structural choice, not merely a
  tested-safe one: because C2 never touches the main cursor at all, D21's
  clean-cursor invariant is only relevant to the **C1→C2 window** (nothing
  unrelated is dirty on the main cursor before C1's own commit, and the
  main cursor performs no writes at all during C2/NET, since C2 lives on
  its own cursor) — the invariant no longer has to guard against C2
  *itself* accidentally co-committing anything, since C2 has no access to
  the main cursor's pending writes by construction. `job_id`'s field type
  is a **separate decision, resolved under D2** (Many2one-FK-restrict) —
  no longer entangled with this decision, per the control-room's explicit
  split instruction.
- **Alternatives considered:** main-cursor pre-network commit (this
  entry's original open alternative — **rejected**: even with D21's
  invariant proven, it only tests for correctness after the fact; the
  side-cursor design removes the risk class structurally, the stronger and
  simpler guarantee, consistent with `call_lease`'s own precedent).
- **Risk:** none beyond the ordinary cost of managing a second cursor
  (already a proven, existing pattern via `call_lease`).
- **Rollback:** N/A — this is a pre-implementation design resolution, not a
  shipped feature; the side cursor itself is simply not opened if Layer 2
  is rolled back.
- **Exact implementation impact:** C2's implementation opens a side cursor
  (mirroring the `call_lease._admit` code path) instead of using
  `self.env.cr`.
- **Exact tests:** a test asserting C2's commit occurs on a distinct
  cursor object from the main cursor; the D21 dirty-state inspection test
  now scoped correctly to the C1→C2 window only.
- **Unresolved question:** None — resolved above; `job_id`'s field type is
  tracked under D2, not here.

### D21 — Main-cursor write-isolation invariant (scoped to the C1→C2
window)
*(Item C — directly implements ruling point 6; scope narrowed 2026-07-19
now that C2 is resolved onto a side cursor, D20)*

- **Fact:** between C1 and C2, today's architecture happens to make "only
  `shopify.connector.job`/`mutation.attempt` writes occur on the main
  cursor" true, but only because of today's narrower one-job-at-a-time
  processing shape — nothing in the code enforces it as an invariant.
- **Inference:** this is currently an unstated, unproven assumption riding
  on accident, not design. Odoo 19's REPEATABLE READ isolation
  (source-materials refresh §5) makes violating this invariant
  particularly dangerous: a stray write between C1 and C1's own commit
  boundary would be silently co-committed, and under REPEATABLE READ, any
  code relying on "freshly committed" visibility after that point could
  observe stale snapshot data unless it explicitly starts a new
  transaction. **Scope correction (D20):** because C2 now commits on its
  own dedicated side cursor rather than the main cursor, this invariant's
  live risk window is narrower than originally framed — it governs the
  **C1 claim-commit itself and any main-cursor activity before it**, not a
  "C1 through C2" main-cursor window, since the main cursor performs no
  writes during C2 at all (C2 has no access to the main cursor's pending
  state by construction, D20).
- **Recommendation:** state the invariant explicitly, scoped correctly, and
  prove it with a new test class.
- **Accepted-candidate wording:** on the main cursor, the only ORM writes
  permitted in the claim-commit (C1) transaction are to
  `shopify.connector.job` and `shopify.connector.mutation.attempt`;
  `preconditions_snapshot` gathering is read-only by contract and occurs
  before C1 commits or on the C2 side cursor, never interleaved with
  uncommitted main-cursor state. This is the **clean-cursor /
  no-unrelated-dirty-state invariant** the control-room ruling requires —
  enforced by a genuinely new test pattern (inspecting ORM dirty-state /
  `env.all.towrite` immediately before the C1 commit), which does not
  exist anywhere in the current 17-file test inventory and must be built,
  not assumed to already exist. Additionally, per the REPEATABLE READ
  consequences recorded in the source-materials refresh §5: any
  recovery/reconciliation code that re-reads a job or attempt row after a
  crash or a sibling worker's commit must force a fresh read via
  `invalidate_recordset()` + re-`browse()`/re-`search()`, mirroring the
  existing `_claim_for_dispatch` precedent, at every point in the
  C1/C2/C3 protocol that depends on cross-transaction visibility
  (including C3's re-lock and re-verification of `current_attempt_token`).
- **Alternatives considered:** trust the current architecture's accidental
  correctness without a new test (rejected — "happens to be true today"
  is not a basis for a safety invariant that must hold as the codebase
  evolves).
- **Risk:** without the new test class, a future handler change could
  silently violate the invariant with no test catching it.
- **Rollback:** N/A — a test requirement, not a feature.
- **Exact implementation impact:** one new test-infrastructure pattern
  (ORM dirty-state inspection before C2 commit) plus explicit
  cache-invalidation/re-browse calls at every cross-transaction read point
  in the C1/C2/C3 protocol.
- **Exact tests:** the dirty-state inspection test itself; a snapshot-refresh
  test proving a reconciliation read genuinely re-reads post-commit state
  rather than a stale REPEATABLE READ snapshot from an earlier transaction
  on the same connection.
- **Unresolved question:** None for the invariant's statement; its **proof**
  is new work required before Stage 0 acceptance (tracked as part of D38).

### D22 — Open-transaction-spans-network-call discipline
*(Item D — RECLASSIFIED 2026-07-19, not an architecture blocker, per the
control-room preliminary review PR #177 comment 5013028262 point 7 and the
consolidated Sessions-2-and-3 ruling §6/§9. This entry's original "BLOCKED"
framing treated an implementation coding-discipline-plus-test requirement
as if it were an undecided design question; the design is not in question
here — only its runtime proof is outstanding, correctly classified as a
Stage 0 merge-acceptance criterion, not a precondition to beginning
implementation.)*

- **Fact:** every documented admission path (`_admit`/`_admit_lifecycle`)
  commits and releases its lock before the network call — "no PostgreSQL
  lock spans the network call" is proven. PostgreSQL auto-opens a new
  transaction on the next statement issued on a connection after any
  commit — there is no "no transaction" idle state on an active cursor
  between statements once any statement has run (confirmed against
  official Odoo source, source-materials refresh §5/§6).
- **Inference:** "no lock spans the network call" and "no open transaction
  spans the network call" are different claims, and only the first is
  actually proven. If a handler does anything on `self.env.cr` between
  C2's commit and `_send()` returning — resolving a GID, re-reading a
  related record — Postgres will silently begin a new transaction on that
  statement, holding a REPEATABLE READ snapshot open for the entire
  network call (up to the 20-second read timeout), a genuine
  idle-in-transaction/vacuum-horizon operational hazard independent of any
  lock question.
- **Recommendation:** split the claim explicitly into two, require an
  explicit coding discipline plus a new runtime test class for the
  unproven half — implementable immediately as a coding rule, verified at
  merge time.
- **Accepted-candidate wording — RESOLVED as an implementation invariant
  and runtime acceptance criterion, not a design blocker.** No PostgreSQL
  row/table lock is held across the network call in any documented
  mutation admission path (proven). Whether a bare open (lock-free)
  transaction on the main cursor spans the network call is closed by
  design, given D20's resolution: the main cursor's last statement before
  NET is C1's own commit (C2 lives entirely on a side cursor, D20), so
  there is no main-cursor statement between C1's commit and C3's re-lock
  to accidentally open a new transaction on. The **coding discipline**
  that guarantees this in practice: (a) all data needed for the mutation
  body must be resolved and captured into plain, immutable Python values
  before C2's commit, never re-derived from the main cursor after it; (b)
  no `self.env.cr` statement of any kind executes between C1's commit and
  C3's re-lock. This discipline is now implementable and enforceable
  immediately — it was never actually undecided, only unproven at runtime.
- **Alternatives considered:** assume the risk away because no lock is
  held (rejected — the operational hazard is at the connection/transaction
  level, invisible to ORM-level lock analysis).
- **Risk:** an idle-in-transaction connection holding a REPEATABLE READ
  snapshot across a 20-second network read timeout is a documented general
  PostgreSQL operational hazard (vacuum/xmin horizon impact) independent of
  correctness — a real production risk if the coding discipline above is
  ever violated; mitigated structurally by D20's side-cursor resolution,
  which removes the main cursor from the NET window entirely by
  construction, not merely by convention.
- **Rollback:** N/A — a coding discipline and its runtime proof, not a
  design choice to roll back.
- **Exact implementation impact:** Stage 0's NET-window handler code must
  be written under the explicit "nothing on `self.env.cr` between C1's
  commit and C3's re-lock" discipline from day one; this is a
  coding-review-enforced rule, not optional guidance, and may begin
  immediately — it does not require D38's runtime proof to exist first.
- **Exact tests:** a new `pg_stat_activity`-based test class asserting no
  open transaction is observed on the connection during the simulated
  network-call window — does not exist anywhere in-repo today; this is a
  **Stage 0 merge-acceptance criterion** (D38), not a precondition to
  beginning implementation of the C1/C2/NET/C3 code path.
- **Unresolved question:** None for the design — resolved above. The
  `pg_stat_activity`-based runtime proof remains outstanding **implementation
  work**, tracked under D38, correctly classified as a merge-acceptance
  requirement rather than an architecture blocker.

### D23 — Crash-window C2→NET recovery
*(Items 15, B — B's accepted wording is identical to 15's per this
session's own cluster review, merged to avoid two drifting copies of one
rule)*

- **Fact:** no crash-recovery table exists today distinguishing this window.
- **Inference:** committing `transport_attempted=true` only after confirmed
  send reopens a false-negative blind-resend hole — strictly worse than
  some unnecessary post-crash reconciliation reads.
- **Recommendation:** commit `transport_attempted=true` strictly before the
  network call, unconditionally treat any post-C2 failure as "transport may
  have occurred."
- **Accepted-candidate wording:** `transport_attempted` is committed `true`
  at C2, strictly before NET. Any failure observed after C2 — process
  death, PG conflict, or anything else — is **unconditionally** treated as
  "transport may have occurred" and is never auto-retried by direct
  re-invocation. Recovery-ownership split: a **plain process kill** (no PG
  exception) is the **sweep's** (D26) exclusive responsibility; a **PG
  40001/lock-timeout** landing in the same window is
  `_recover_after_concurrency_conflict`'s (D25) responsibility. A
  genuinely distinct case — an ordinary, non-crashing Python exception
  raised between C2 and the `execute_business()` call — must route through
  normal `_route_failure` error handling, **not** this crash-recovery
  table.
- **Alternatives considered:** commit `transport_attempted` only after
  confirmed send (rejected — reopens false-negative blind-resend risk,
  strictly worse than the accepted cost).
- **Risk:** conservative-by-design cost: some post-crash reconciliation
  reads will discover the mutation never actually sent — acceptable,
  correctness-preserving overhead.
- **Rollback:** N/A — recovery policy, not a droppable feature.
- **Exact implementation impact:** explicit `except`-vs-crash branching in
  the dispatch/recovery code, distinguishing ordinary exceptions from
  crash/PG-conflict cases.
- **Exact tests:** crash-injection test killing between C2 and NET (D38);
  ordinary-exception test asserting it does NOT route through the
  crash-recovery table.
- **Unresolved question:** None.

### D24 — Crash-window NET→C3 recovery
*(Item 16)*

- **Fact:** distinguishing "crashed during transport" from "crashed after
  response, before commit" would require either extending a lock/transaction
  across the network call (forbidden by D21/D22) or an out-of-band
  completion signal that doesn't exist.
- **Inference:** deliberately collapsing these two cases into one
  conservative branch is the only currently-supportable design.
- **Recommendation:** treat identically to D23's handling.
- **Accepted-candidate wording:** a failure observed after NET returns
  (successfully or not) but before C3 commits — whether process crash or PG
  40001/lock-timeout during C3's re-lock/CAS/write — is handled identically
  to D23: never re-executed, unconditionally routed to a reconciliation
  read.
- **Alternatives considered:** distinguish the two cases via an
  out-of-band signal (rejected — no such mechanism exists or is proposed).
- **Risk:** none beyond D23's accepted conservative-overhead cost.
- **Rollback:** N/A.
- **Exact implementation impact:** shares D23's `except`/crash-branching
  code path.
- **Exact tests:** crash-injection test killing between NET and C3 (D38).
- **Unresolved question:** **orphaned across this session's own review
  clusters** — whether reconciliation should prefer an idempotency-key-replay
  read (strictly more authoritative — returns the *original* mutation's
  actual result) over an independent quantity-comparison read when both are
  available was raised by the transaction-protocol review but never
  engaged with by the reconciliation-framework review that actually owns
  reconciliation-verdict design (D14/D16/D17). Carried to Part 7,
  genuinely unresolved.

### D25 — Claimability-gate widening for 40001/lock-timeout recovery
*(Item 17)*

- **Fact:** `_recover_after_concurrency_conflict`'s current claimability
  filter, verified directly against code, excludes any `running` row —
  correct today, since under Layer-1-only semantics a `running` row during
  recovery is always stale.
- **Inference:** under Layer 2, `running` becomes the expected, durable,
  legitimately-owned state for the entire C2/NET/C3 window — reusing the
  current gate verbatim would cause the function to silently abandon
  exactly the jobs D16's `transport_attempted` routing is written to cover.
  This is a **confirmed, code-verified structural contradiction**, not a
  stylistic gap.
- **Recommendation:** widen the gate additively.
- **Accepted-candidate wording:** for mutation job types only, the
  claimability filter is widened to accept a `running` job whose
  currently-committed `current_attempt_token` matches the value the
  recovering transaction itself holds — in **addition to**, not instead
  of, the existing `queued`/due-`retry_waiting` branch. A `running` row
  with a non-matching or absent locally-held `current_attempt_token`
  remains excluded, exactly as today.
- **Alternatives considered:** leave the gate unmodified and route all
  mutation-type recovery through a separate function (rejected — creates
  two divergent recovery code paths for no benefit; the additive widening
  is simpler and narrower).
- **Risk:** an incorrectly-scoped widening (applying to non-mutation job
  types too) would reintroduce the exact staleness the original gate
  exists to prevent — must be proven, not assumed, scoped correctly.
- **Rollback:** revert the widening; mutation-type recovery reverts to
  full exclusion (fails safe, just less available).
- **Exact implementation impact:** one additive branch in
  `_recover_after_concurrency_conflict`'s claimability filter, scoped by
  job-type class.
- **Exact tests:** **must be proven by a genuine multi-connection
  concurrency test (D38), not accepted by inspection** — a test asserting
  the widened branch only matches on exact `current_attempt_token`, and
  that a non-matching `running` row remains correctly excluded.
- **Unresolved question:** None for the design; proof is required (D38)
  before acceptance.

### D26 — Stale-owner sweep mechanism
*(Item 18)*

- **Fact:** the disconnect-quiescence controller's existing cron pattern
  processes roughly one row per tick — under-scaled for a fleet-crash
  backlog scenario if mirrored literally.
- **Inference:** a bounded-batch design, not a one-row-per-tick mirror, is
  needed for the sweep to actually drain a real crash backlog in
  reasonable time.
- **Recommendation:** a new cron with bounded batching and evidence-preserving
  takeover.
- **Accepted-candidate wording:** new `_sweep_stale_running_jobs()` cron:
  selects `state='running'` with `running_since` (D1) older than the sweep
  timeout (D27), via bounded batch (`limit=SWEEP_BATCH_SIZE`, default 20,
  `try_lock_for_update()`). Evidence-preserving takeover rule:
  `transport_attempted=false`→safe requeue (never re-invokes the handler);
  `transport_attempted=true`→creates a linked reconciliation job (D14),
  leaves the original job in D13's waiting posture — the sweep itself
  never auto-finalizes a job as succeeded/failed. Logged with a distinct
  `action_type='stale_owner_sweep'`, separate from `concurrency_race_conflict`
  recovery entries.
- **Alternatives considered:** literal one-row-per-tick mirror of the
  disconnect-quiescence cron (rejected — under-scaled for backlog
  scenarios).
- **Risk:** an undersized batch limit under a real fleet-crash scenario
  could leave the sweep perpetually behind — `SWEEP_BATCH_SIZE=20` is a
  provisional default (D27), tunable.
- **Rollback:** disable the cron; the four D1 fields remain inert but
  present.
- **Exact implementation impact:** new cron XML record (`noupdate="1"`),
  new Python method, new distinct `action_type` log value.
- **Exact tests:** sweep-batch test (bounded batch, correct
  requeue-vs-reconcile branching by `transport_attempted`); operator-distinguishability
  test (`stale_owner_sweep` entries are logged distinctly from
  `concurrency_race_conflict` entries).
- **Unresolved question:** None for the mechanism; see D27/D28 for
  parameter and interaction gaps.

### D27 — Sweep cadence & timeout constants
*(Item 19)*

- **Fact:** no cadence or timeout value exists anywhere in the original
  design for this cron.
- **Inference:** cadence can be fixed now (matching existing cron cadences);
  timeout cannot be finalized without runtime measurement.
- **Recommendation:** fixed cadence, explicitly provisional timeout.
- **Accepted-candidate wording:** cadence: fixed 5-minute `ir.cron` interval
  (`STALE_RUNNING_SWEEP_CADENCE_MINUTES=5`), matching drain/disconnect
  cadence. Timeout: separately-named, tunable constant, provisional default
  30 minutes, **explicitly provisional pending Odoo.sh runtime measurement**
  of worst-case handler duration — this repository's own already-disclosed
  pattern for this class of constant. **Correction, 2026-07-19:** this
  value is no longer conditioned on D28, since D28's resolved design
  (awareness-based disconnect finalization) removes the timeout-race
  dependency this entry originally flagged — the sweep timeout is now an
  ordinary, independently tunable operational constant.
- **Alternatives considered:** derive cadence from the disconnect-quiescence
  cadence directly (rejected — no coupling requirement exists; matching by
  convention is sufficient and simpler).
- **Risk:** none beyond ordinary tunable-constant risk (too-short risks
  premature takeover of a legitimately slow handler; too-long delays
  crash-backlog recovery) — no longer entangled with D28's disconnect
  interaction.
- **Rollback:** cron interval/timeout are ordinary tunable config, not
  structural.
- **Exact implementation impact:** two named constants in the sweep cron
  implementation.
- **Exact tests:** N/A directly (measurement-driven, not test-driven);
  covered indirectly by D38's runtime proof.
- **Unresolved question:** exact numeric timeout value is an
  **empirical-measurement gap**, not a design gap — provisional 30 minutes
  pending Odoo.sh worst-case handler-duration measurement. No longer
  contingent on D28 (resolved above).

### D28 — Disconnect-quiescence: awareness-based finalization (not a
timeout race)
*(Item 20 — RESOLVED 2026-07-19, not blocking. This entry's original
framing offered a binary choice between two timeout-ordering remediations;
the control-room preliminary review, PR #177 comment 5013028262 point 9,
and the consolidated Sessions-2-and-3 ruling §9 reject that framing
entirely in favor of a safety choice: disconnect finalization must be
*aware* of unresolved mutation attempts, not merely race a shrunk timeout
against them.)*

- **Fact:** `_finalize_disconnect_timed_out()` unconditionally clears the
  store credential and deletes the lease at `DISCONNECT_QUIESCE_TIMEOUT`
  (15 minutes), with no way to distinguish a live vs. orphaned lease.
  `ShopifyQuiescedError` (the error `_admit`'s state gate raises against a
  quiesced store) has **no dedicated handling anywhere in `_invoke_handler`
  today** — it falls to the generic `unknown_system_error` safety net.
- **Inference:** the design's claim that "the sweep defers to quiescence...
  resolved by timeout ordering alone" is **not adequately supported**, and
  this entry's own original remediation (a) (shrink the sweep timeout below
  15 minutes) does not actually fix the underlying problem — it only
  narrows the race window, since a sufficiently slow reconciliation cycle
  or a sufficiently large crash backlog could still lose the race under any
  fixed timeout pairing. The correct fix is for disconnect finalization
  itself to check state, not for the sweep to try to always win a race
  against it.
- **Recommendation:** make `_finalize_disconnect_timed_out` aware of
  unresolved mutation attempts and linked reconciliation jobs — remediation
  (b) from this entry's original framing, now the sole accepted design, not
  one of two options.
- **Accepted-candidate wording — RESOLVED:** new mutation admissions stop
  immediately when disconnect/quiescence begins (existing `_admit` gate
  behavior, unchanged). `_finalize_disconnect_timed_out` is extended to
  check, before clearing credentials or deleting the lease, whether any
  `mutation.attempt` row bound to the store has an unresolved effective
  disposition (D10's helper returns `unresolved`) or any linked
  reconciliation job (D14) is still pending/running. If so: **credentials
  are preserved**, the disconnect is kept **pending/blocked** rather than
  finalized, and Administrator-visible manual-review evidence is created —
  the automatic timeout path never silently finalizes over an unresolved
  mutation attempt. Any **force-disconnect** path remains available but is
  Administrator-only, requires a mandatory reason, is fully audited, and
  routes any still-unresolved attempts to manual review rather than
  pretending they are resolved — it never silently marks an attempt
  applied/not-applied as a side effect of forcing the disconnect. Once no
  unresolved attempt or pending reconciliation job remains, the ordinary
  timeout finalization proceeds unchanged. `ShopifyQuiescedError` is wired
  into an explicit `except` branch in `_invoke_handler` regardless (shared
  fix with D29), routed to a dedicated `blocked_manual_review` subreason
  distinguishing "store disconnected mid-attempt" from genuine outcome
  ambiguity. D27's sweep-timeout value is now an ordinary, independently
  tunable operational constant — it no longer needs to be jointly sized
  against `DISCONNECT_QUIESCE_TIMEOUT`, since disconnect finalization
  itself defers to any unresolved attempt regardless of the sweep's own
  cadence.
- **Alternatives considered:** shrinking the sweep timeout below 15 minutes
  (this entry's original remediation (a) — **rejected**: narrows but does
  not eliminate the race, and re-couples D27's timeout value to
  `DISCONNECT_QUIESCE_TIMEOUT` for no structural safety gain); leaving the
  interaction as originally designed, relying on timeout-ordering alone
  (rejected — proven inadequate by direct code reading).
- **Risk:** none beyond the added cost of one open-attempt/reconciliation
  check inside `_finalize_disconnect_timed_out` — negligible, and strictly
  safer than either of this entry's originally-proposed timeout-race
  remediations.
- **Rollback:** the awareness check is a safety addition; removing it
  reverts to the original (proven-inadequate) timeout-only behavior — not
  recommended, but structurally simple to revert if ever needed.
- **Exact implementation impact:** one new open-attempt/reconciliation-job
  check inside `_finalize_disconnect_timed_out`, gating credential-clearing
  and lease deletion; one new `except ShopifyQuiescedError` branch in
  `_invoke_handler` (shared with D29); the existing force-disconnect action
  extended to require Administrator + mandatory reason + audit + route
  unresolved attempts to manual review.
- **Exact tests:** a test reproducing the exact strand scenario (crash near
  the quiescence boundary) and asserting the awareness check prevents
  credential-clearing while the attempt is unresolved; a test asserting the
  ordinary timeout finalization still proceeds once no unresolved attempt
  remains; a test asserting force-disconnect requires Administrator +
  reason and routes any still-unresolved attempt to manual review, never
  silently resolving it.
- **Unresolved question:** None — resolved above.

### D29 — Credential-rotation mid-attempt handling
*(Item 21)*

- **Fact:** `_mutate_token`'s existing behavior (any credential
  set/replace while `connected` atomically transitions to
  `reconnect_needed` **and** bumps `connection_generation`) is verified
  sufficient as the sole mid-attempt credential-change detection primitive.
  **Correction to this session's own grounding material:** direct code
  reading confirmed a fourth credential-generation-bump site the original
  secondary audit's site-list omitted.
- **Inference:** no new generation-adjacent field is needed; a parallel
  counter would be redundant.
- **Recommendation:** two additive refinements only, no new primitive.
- **Accepted-candidate wording:** the existing `_mutate_token` behavior is
  confirmed **sufficient and unchanged** as Layer 2's sole mid-attempt
  credential-change detection primitive. Two additive refinements: (a) wire
  `ShopifyQuiescedError` into `_invoke_handler` explicitly (shared fix with
  D28), distinguishing "generation mismatch" from "store not connected" in
  the audit message; (b) the attempt record captures the credential
  id/version snapshot at `_admit` time, for audit/forensics only — this
  does not gate admission, which the existing generation+state check
  already handles correctly.
- **Alternatives considered:** a new parallel generation counter dedicated
  to mutation attempts (rejected — redundant with the existing, proven
  `connection_generation` mechanism).
- **Risk:** none beyond D28's shared risk (the `ShopifyQuiescedError`
  wiring gap).
- **Rollback:** the audit-snapshot field (b) is additive/droppable; (a) is
  a bug fix, not a rollback candidate.
- **Exact implementation impact:** one credential id/version snapshot field
  on the attempt record; shares D28's `except` branch addition.
- **Exact tests:** generation-mismatch-vs-not-connected distinguishability
  test in the audit log.
- **Unresolved question:** None.

### D30 — ACL for `mutation.attempt` (current four-role model)
*(Items 26, H.1, H.2, H.4, H.5 — directly implements ruling point 7;
confirmed installing under the current, accepted four-role model per the
consolidated Sessions-2-and-3 ruling §12, which explicitly rejects Session
3's proposal to install Stage 0 ACLs directly against the future SEC-2
two-role model — see Part 0.5)*

- **Fact:** `shopify.connector.job.log`'s existing ACL posture is pure
  audit trail — no role gets write/create/unlink via ACL, all writes are
  `sudo()`-only. This session's own code audit confirms field-level
  `groups=` is **not** relied upon anywhere in the current codebase for
  write protection — protection is enforced by explicit Python `write()`
  overrides checking `self.env.su` (source-materials refresh §8).
- **Inference:** `mutation.attempt` has nothing legitimately human-writable
  outside one sanctioned action (D11) — `job.log`'s posture is the correct
  precedent, not `job`'s blanket-grant-plus-Python-classifier posture.
- **Recommendation:** four read-only ACL rows, all mutation via `sudo()`.
- **Accepted-candidate wording:** four ACL rows, one per **current** role
  (Auditor/Operator/Reviewer/Admin), each `perm_read=1, perm_write=0,
  perm_create=0, perm_unlink=0` — **including Admin**, no role gets
  write/create/unlink via ACL, subject to current connector access rules.
  All creation/write happens exclusively via `sudo()` at C2, C3, and D11's
  override action — a **closed sudo-site inventory** (exactly 3 sites)
  enforced by an AST test that fails the build on a 4th. Unlink is
  permanently denied to all roles including Admin (ties to D32's retention
  policy — masked-in-place after the configurable window, never deleted).
  **SEC-2 follow-up obligation (new, per the consolidated ruling §12):**
  these four ACL rows are explicitly flagged for re-keying during the
  later two-role migration (SEC-2) — installing against the current model
  now does not pre-judge that migration's shape, but does create a named,
  tracked obligation to revisit these exact rows when SEC-2 ships (see
  D31).
- **Alternatives considered:** `job`'s blanket-grant-plus-Python-classifier
  posture (rejected — unnecessary added attack surface for a model with no
  legitimately-mixed editable field set, unlike `job` which has genuine
  operator-editable fields).
- **Risk:** a 4th, unaccounted sudo call site would silently widen the
  write surface — mitigated by the AST test failing the build.
- **Rollback:** ACL rows are declarative config, trivially revertible.
- **Exact implementation impact:** four `ir.model.access.csv` rows; AST
  test enumerating exactly 3 sudo call sites.
- **Exact tests:** ACL-denial test per role (write/create/unlink all
  denied to all four roles); AST sudo-site-count test.
- **Unresolved question:** the resolution-action/field naming
  inconsistency across this session's own review clusters (Part 3 item 2)
  is not a substantive ACL gap, only a naming one — the mechanism (Admin-only
  `sudo()` write via one sanctioned action) is settled.

### D31 — SEC-2 two-role-migration compatibility + explicit re-key
obligation
*(Item 27 — EXTENDED 2026-07-19 per the consolidated Sessions-2-and-3
ruling §12, which rejects Session 3's proposal to install Stage 0 directly
against the future two-role model and instead requires Stage 0 to install
cleanly under the current model with a named SEC-2 follow-up obligation —
see Part 0.5)*

- **Fact:** `mutation.attempt` under D30 is read-only for all four current
  groups; the future `group_shopify_connector_user`'s `implied_ids`
  inheritance mechanic (from the planned two-role migration) is not
  verified against official Odoo 19 docs or runtime behavior anywhere in
  this session's grounding material.
- **Inference:** if the inheritance mechanic works as commonly assumed, no
  ACL changes are needed to this model at SEC-2 time.
- **Recommendation:** state the compatibility conditionally, flag the
  unverified assumption explicitly rather than silently relying on it.
- **Accepted-candidate wording:** no ACL changes are needed to
  `mutation.attempt` at SEC-2 (future two-role migration) time under D30's
  design — it is read-only for all four current groups, automatically
  covered by the future `group_shopify_connector_user`'s `implied_ids`
  inheritance of Operator/Reviewer, **pending empirical confirmation of
  that inheritance mechanic** (non-blocking for Wave 3, blocking for the
  eventual SEC-2 packet). `security-pii-matrix-waves-2-6.md`'s premature
  "User read" framing (referencing a group that does not yet exist in
  code) must be corrected when that document is next in an allowed-files
  scope. SEC-2's planned removal of Wave-1 PII masking for the two new
  roles is explicitly out of scope for this model, since it was never
  PII-masked in the first place (D7 makes it PII-free by construction, a
  stronger guarantee than the masking SEC-2 removes).
- **Alternatives considered:** pre-emptively add explicit ACL rows for the
  not-yet-existing `group_shopify_connector_user` (rejected — the group
  doesn't exist yet; premature rows would be untested and possibly wrong).
  **Session 3's proposal to write Stage 0's ACLs directly against the
  future SEC-2 two-role model** (rejected by the consolidated ruling §12
  — Part 0.5: Stage 0 must install cleanly under the current, accepted
  four-role model; a not-yet-existing role model must not gate what can
  ship now, for the same "the group doesn't exist yet" reasoning this
  entry's own original alternative was already rejected for, now applied
  to the ACL *installation shape* itself, not merely to pre-emptive rows).
- **Risk:** if `implied_ids` inheritance does not work as assumed, SEC-2
  could ship with an accidental ACL gap for the new roles — mitigated by
  flagging this as blocking *for the SEC-2 packet specifically*, not for
  Wave 3, and by the explicit re-key obligation below.
- **Rollback:** N/A.
- **Exact implementation impact:** none for Wave 3; a verification task for
  the future SEC-2 implementation session. **Explicit re-key obligation
  (new):** D30's four ACL rows are a named, tracked item on the SEC-2
  migration's own scope — the SEC-2 session must re-key (not merely
  re-verify) these rows against whatever the two-role model's actual
  `implied_ids` behavior turns out to be, not assume today's rows carry
  forward unexamined.
- **Exact tests:** deferred to the SEC-2 packet's own test requirements.
- **Unresolved question:** the `implied_ids` inheritance mechanic itself is
  unverified — non-blocking now, blocking at SEC-2 time.

### D32 — Retention: indefinite for unresolved, configurable pruning for
resolved terminal
*(Item 29 — CORRECTED 2026-07-19. The control-room preliminary review, PR
#177 comment 5013028262 point 5, rejected this entry's original
retain-forever design as creating unbounded database growth and
contradicting the project's own earlier configurable-retention posture.
The consolidated Sessions-2-and-3 ruling §11 makes the corrected policy
below binding.)*

- **Fact:** the original design's "pruned by existing retention sweep,
  default 180 days, aligned with job retention" claim refers to no
  mechanism verifiable anywhere in the audited codebase: `perm_unlink=0`
  for every role on every model except `call.lease`; the only existing
  sweep (`pii_retention.run_sweep()`) exclusively masks fields in place and
  never `.unlink()`s, and defaults to *disabled* per-store; "aligned with
  job retention" has no referent — no job-retention constant exists
  anywhere.
- **Inference:** the original design's retention claim was aspirational,
  not grounded — a real documentation-accuracy defect, independent of
  retention policy. **This entry's own first-drafted correction
  (retain-forever, no deletion ever) over-corrected**: forensic
  completeness for genuinely unresolved evidence does not require
  unbounded retention of evidence that has *already resolved* and reached
  a terminal state — the two cases carry different retention needs and
  conflating them (as both the original design and this entry's first
  correction did, in opposite directions) is itself the defect.
- **Recommendation:** two-tier policy: indefinite for anything not yet
  resolved, configurable pruning (masking bulky fields, never deleting the
  row) for terminal resolved attempts after an accepted window.
- **Accepted-candidate wording — RESOLVED:** **unresolved, uncertain, or
  manual-review attempts are retained indefinitely** — no cron, sweep, or
  manual action ever deletes or masks these rows while their effective
  disposition (D10's helper) is `unresolved`. **Resolved terminal attempts**
  (effective disposition `applied` or `not_applied`) retain **full,
  allowlisted evidence for a configurable period, default candidate 180
  days**; after that period, a new sweep **masks bulky evidence fields**
  (`preconditions_snapshot`, `remote_mutation_intent`, `remote_evidence_refs`
  payload-shaped content) **in place** — mirroring the existing
  `pii_retention.run_sweep()` mask-not-delete pattern — while permanently
  keeping the row itself, its identifiers (`job_id`, `attempt_token`,
  `mutation_domain`), both fingerprints, `observed_outcome`,
  `resolution_disposition`/`resolution_source`/`resolution_reason`/
  `resolution_uid`/`resolution_at`, and all timestamps — the durable audit
  trail is never lost, only the bulkier forensic payload content. **The
  row is never `.unlink()`d by this or any Stage 0 mechanism**, mirroring
  `job`/`job.log`'s append-only, `ondelete='restrict'`-anchored posture
  (DEC-030) — this part of the original retain-forever framing is retained
  for the row itself, only the *field-masking* dimension is new.
- **Alternatives considered:** the original design's claimed 180-day
  delete-based sweep (rejected — no such mechanism exists to align with or
  extend, and deletion of the single highest-value forensic record is
  unnecessary once masking achieves the storage-bound goal). This entry's
  own first-drafted retain-forever-with-no-masking-either design (rejected
  by the control-room correction above — creates genuinely unbounded
  growth for terminal, already-resolved evidence that no longer needs its
  full bulky payload retained).
- **Risk:** unbounded storage growth for the **unresolved** tier remains an
  accepted, explicit trade-off (forensic completeness while a case is
  still open outweighs storage cost); the **resolved-terminal** tier's
  growth is now bounded by the configurable masking window, closing the
  risk the control room flagged.
- **Rollback:** N/A — retention posture, not a droppable feature; the
  masking sweep itself is a new, separately-tested capability, droppable
  independently of the row-retention guarantee.
- **Exact implementation impact:** `unlink()` permanently denied to all
  roles via ACL (D30) for this model, unconditionally; a new masking sweep
  (mirroring `pii_retention.run_sweep()`'s pattern) scoped to
  resolved-terminal attempt rows older than the configurable window.
- **Exact tests:** test asserting no code path ever calls `.unlink()` on
  this model (AST or runtime assertion); test asserting an unresolved
  attempt is never touched by the masking sweep regardless of age; test
  asserting a resolved-terminal attempt past the window has its bulky
  fields masked while its identifiers/outcome/resolution/timestamps remain
  intact.
- **Unresolved question:** the exact numeric masking-window default (180
  days, mirroring the original design's own aspirational value) is a
  tunable-constant question, not an architecture blocker — control-room
  ratification of the specific number is still open but does not block
  Stage 0 implementation of the mechanism itself.

### D33 — Upgrade path
*(Item 30)*

- **Fact:** none of D1's three new job fields has a computable historical
  value for pre-existing rows (unlike LC-1's `original_job_type`, which
  does).
- **Inference:** no `post-migrate.py` backfill is required — pre-Layer-2
  rows correctly resolve to their declared defaults.
- **Recommendation:** a standard additive upgrade, but with the full
  surface enumerated explicitly, not understated.
- **Accepted-candidate wording:** the three D1 job fields require **no**
  backfill. The upgrade surface must be enumerated in full: it also
  includes one new `ir.model.access.csv` block (D30) and one new `ir.cron`
  XML record (D26/D27, wrapped `noupdate="1"`), not merely "3 fields + 1
  model" as previously understated. This absence-of-backfill claim must be
  **proven, not merely asserted**, by a negative-migration test.
- **Alternatives considered:** a backfill script deriving placeholder
  values for historical rows (rejected — unnecessary, since default
  resolution is already correct and a backfill would add migration risk
  for no benefit).
- **Risk:** an unproven "no backfill needed" claim could hide a real
  upgrade defect if any assumption about default-value correctness is
  wrong — mitigated by the required negative-migration test.
- **Rollback:** standard additive-schema Odoo module downgrade path.
- **Exact implementation impact:** one migration-free module version bump;
  one new ACL block; one new cron XML record.
- **Exact tests:** **negative-migration test**: seed a fixture DB with
  pre-existing, populated job rows of varied states, apply the upgrade,
  assert zero `IntegrityError`/`ValidationError` and correct default
  resolution.
- **Unresolved question:** None.

### D34 — Uninstall behavior
*(Items 31, J — J requires no new mechanism beyond 31's correction)*

- **Fact:** the original design doc contains a genuine, previously-unflagged
  self-contradiction: its own "Uninstall" bullet (§12, "dropped with the
  module's models, offered for export then dropped") describes the wrong
  axis, while its own "Rollback" bullet two lines later already says the
  opposite ("retained as evidence... never deleting attempt history").
  DEC-030's accepted matrix only drops domain-owned binding/mapping tables
  on a *domain* uninstall; core-owned audit tables (`job`, `job.log`)
  survive, retyped via LC-1's `historic_domain_job` mechanism, and are lost
  only on a core/Lite-substrate uninstall (itself unsupported while any
  domain module remains installed).
- **Inference:** `shopify.connector.mutation.attempt` is core-owned (Stage
  0, `addons/shopify_connector_core/models/`) and must inherit
  `job`/`job.log`'s DEC-030 posture, not the domain-owned-binding-table
  posture — the Uninstall bullet must be corrected to match the Rollback
  bullet, not the other way around.
- **Recommendation:** correct the design doc's self-contradiction; state
  the two uninstall scenarios explicitly.
- **Accepted-candidate wording:** **Domain-level uninstall:**
  `mutation.attempt` rows survive core-side, joined to their (LC-1-retyped)
  owning job via `job_id`, remain queryable by `mutation_domain` the same
  way retyped jobs remain queryable by `original_job_type`. **Core/Lite-substrate
  uninstall:** lost "by definition," identically to `job`/`job.log`, under
  DEC-030's existing, unmodified matrix — no new architecture is required
  (this is J's finding: the tension between "pre-mutation removable
  substrate," "post-mutation evidence retained," and "core cannot simply be
  uninstalled independently" is resolved by correct *classification*, not
  a new mechanism).
- **Alternatives considered:** treat `mutation.attempt` as domain-owned,
  dropped on the inventory domain's own uninstall (rejected — would
  reintroduce exactly the failure class DEC-030 already fixed once for
  `job`/`job.log`, since the attempt table's forensic value outlives any
  single domain).
- **Risk:** getting this classification wrong reproduces a documented
  failure pattern DEC-030 was written to prevent — high-stakes if
  mis-implemented.
- **Rollback:** N/A — classification decision, not a feature.
- **Exact implementation impact:** design doc §12's "Uninstall" bullet is
  corrected in this session's update (done); no code change required. **D35
  is now resolved** (registry-validated indexed `Char`, not a Selection of
  either kind) — since `mutation_domain` has no selection-uninstall
  lifecycle at all, this decision's classification is simpler than
  originally framed: `mutation.attempt` rows survive a domain uninstall
  automatically, with no historic-conversion helper needed, because there
  is no enumerated Selection value to become orphaned.
- **Exact tests:** an uninstall-simulation test asserting `mutation.attempt`
  rows survive a domain-only uninstall and remain queryable by
  `mutation_domain` (a plain string comparison, not a retyped Selection
  lookup) afterward.
- **Unresolved question:** None — D35's resolution (Char, not Selection)
  removes the contingency this entry originally carried.

### D35 — `mutation_domain` field ownership — registry-validated indexed
Char
*(Items I, O — RESOLVED, not blocking, 2026-07-19. The control-room
preliminary review, PR #177 comment 5013028262 point 4, found this entry's
original two-option framing omitted a material third option; the
consolidated Sessions-2-and-3 ruling §5 selects that third option as
binding, closing what this entry originally called "genuinely blocking.")*

- **Fact:** two live, precedent-supported options were originally
  presented, pulling in opposite directions. `job_type`'s ownership rule
  (whichever module owns a mutation's handler also owns its
  domain-vocabulary value, via `selection_add`) is DEC-008-consistent,
  proven precedent — call this option (a). DEC-030's Option D (core
  carrying domain vocabulary directly, as a core-fixed Selection) was
  explicitly rejected once already — this entry's original option (b)
  would have reintroduced that same rejected pattern. **A third option
  exists and was omitted from this entry's original framing:** (c) a
  registry-validated, indexed `Char` field — not a Selection of either
  kind. Its values are never enumerated in the field's own type
  declaration; validity is enforced entirely by D15's reconciliation
  registry (fail-closed on an unregistered value) and D16's runtime gate,
  both of which already exist as this design's own mechanism for keeping
  core domain-agnostic.
- **Inference:** option (c) achieves both goals options (a) and (b) each
  achieved only one of: it keeps core domain-agnostic (like (a)) **and**
  avoids any domain-selection uninstall coupling or LC-1-style
  historic-conversion mechanism (like (b) claimed to, without actually
  reintroducing DEC-030's rejected pattern, unlike (b)). A `Char` field has
  no `selection_add` lifecycle to reconcile with LC-1 at all — there is no
  "historic value" problem for D34's uninstall classification to solve,
  because there is no Selection whose enumerated values could become
  orphaned by an uninstalled domain module in the first place.
- **Recommendation:** adopt option (c), closing this entry's original
  either/or framing.
- **Accepted-candidate wording — RESOLVED:** `mutation_domain` is a
  **required, indexed `Char`** field on `mutation.attempt` (per D2's
  schema). It is **not** a core-fixed Selection (rejects original option
  (b)) and **not** a domain-`selection_add` Selection (rejects original
  option (a)) — both alternatives are superseded by option (c). Validity
  is enforced fail-closed against D15's reconciliation-strategy registry
  (and D16's runtime gate before every C2 commit): an unregistered value
  is rejected at write time, never silently accepted. Together with D15's
  registry, D30's read-only ACL, and this field's Char ownership, this is
  the complete mechanism keeping core domain-agnostic (O's original
  validation note, now satisfied by option (c) rather than by whichever of
  (a)/(b) might have been chosen) — a build-time/AST guard (D37) asserts
  zero literal domain-specific branching in core dispatch/job/attempt
  files.
- **Alternatives considered:** option (a), domain-`selection_add`
  (rejected — unnecessary lifecycle complexity once option (c) achieves
  the same domain-agnostic goal without it); option (b), core-fixed
  Selection (rejected — reintroduces DEC-030's Option D pattern, exactly as
  this entry originally found). Both remain documented here as the two
  options this entry originally presented, now both superseded.
- **Risk:** a `Char` field is weaker than a Selection at the database-schema
  level (no enum constraint) — mitigated by the registry-validation
  fail-closed gate being the actual enforcement mechanism in both cases;
  the original Selection options never relied on database-level enum
  enforcement either (Odoo Selections are not database-level enums).
- **Rollback:** N/A — foundational schema decision, resolved above; no
  longer a precondition to beginning Stage 0 implementation of the field.
- **Exact implementation impact:** `mutation_domain` implemented as
  `Char(required=True, index=True)` with a registry-validation write-time
  check (D15/D16) — no historic-conversion helper is needed (unlike option
  (a) would have required), simplifying Stage 0's scope relative to either
  original option.
- **Exact tests:** a registry-fail-closed test (write with an unregistered
  `mutation_domain` value is rejected); an uninstall-simulation test
  proving D34's classification holds — trivially, since a `Char` field has
  no selection-uninstall coupling to test against in the first place.
- **Unresolved question:** None — resolved above.

### D36 — Rollback procedure (two-phase)
*(Item 32)*

- **Fact:** the original design's "Rollback" bullet (§12) names only one
  mechanism (disabling the replay-policy registry entry).
- **Inference:** a rollback performing only that one mechanism would still
  let already-`queued` jobs start a *first* attempt, since the replay-policy
  check never fires for a first attempt, only for retries — an
  under-specification, not a correct-but-incomplete-description.
- **Recommendation:** require two coordinated mechanisms together for a
  post-ship rollback.
- **Accepted-candidate wording:** **Pre-ship** (before any mutation domain
  has executed a job): clean additive-schema revert (drop fields/model/ACL
  rows/cron), proven by D33's negative-migration test. **Post-ship** (after
  at least one mutation attempt has run): never deletes evidence (D32);
  requires **two coordinated, already-existing gating mechanisms together,
  not either alone**: (a) set the relevant `store.settings.*_domain_enabled`
  flag to `False`, blocking any *new* job of that type from reaching
  `running` via the existing `_domain_flag_for_job_type()` gate; **and**
  (b) ensure the job_type's replay-policy registry entry is/reverts to
  `remote_effect_not_replay_safe` or is removed, fail-closing auto-retry
  for anything already in flight.
- **Alternatives considered:** mechanism (b) alone, as the original design
  implies (rejected — proven insufficient, per the Inference above).
- **Risk:** an incomplete rollback (b) alone) would let in-flight *first*
  attempts continue executing during an emergency rollback — a real safety
  gap in the original design's under-specification.
- **Rollback:** this decision is itself about rollback procedure; its own
  "rollback" is simply not adopting the two-phase requirement, which is
  not recommended.
- **Exact implementation impact:** the domain-enable flag and
  replay-policy-registry mechanisms already exist; this decision requires
  documenting and testing their *joint* use for rollback, not new code.
- **Exact tests:** a rollback-simulation test asserting that flag-only or
  registry-only rollback (either alone) fails to stop new first-attempt
  starts, while the joint mechanism succeeds.
- **Unresolved question:** None.

### D37 — Repo-wide AST/source guard + mutation-wrapper transport guard
*(Item 34 — RECLASSIFIED 2026-07-19, not an architecture blocker. The
control-room preliminary review, PR #177 comment 5013028262 point 7, and
the consolidated Sessions-2-and-3 ruling §14 find that whether existing AST
tooling can be extended is implementation sizing, resolvable by direct
inspection at implementation time — not a reason to keep architecture
undecided. This entry's design itself was never in question; only its
effort-sizing was.)*

- **Fact:** existing file-scoped guards (`test_read_only_guarantee`,
  `test_public_surface_adds_only_execute_business`, a hand-maintained
  no-reference file list) exist and are proven; a pre-existing,
  already-tolerated direct-`requests.get` CDN bypass exists at
  `product_importer.py:1958`, proving this class of gap is not
  hypothetical.
- **Inference:** file-scoped guards are insufficient on their own — a
  repo-wide, `ast`-module-based (not regex/`getsource`) scan is needed to
  catch any future bypass anywhere in the connector addon family, not just
  in files a maintainer remembered to add to the guard list.
- **Recommendation:** add a genuine `ast.parse`/`ast.walk`-based repo-wide
  guard, retain the existing file-scoped guards as a second layer.
- **Accepted-candidate wording — RESOLVED as design, sizing deferred to
  implementation time:** a genuine `ast`-module parse across every `.py`
  file under `addons/shopify_connector_*/` must fail the build on any
  `ast.Call` resolving to a raw HTTP-transport call
  (`requests.get/post/request`, etc.) outside `_send()` and an explicit,
  individually justified allowlist (seeded with the existing
  `product_importer.py:1958` CDN bypass). Existing file-scoped guards are
  retained, not replaced. **Extended per D16:** this guard must also cover
  the mutation-wrapper transport requirement — any GraphQL document
  containing a `mutation` operation issued from a call site outside the
  attempt wrapper fails the build, complementing (not duplicating) D16's
  runtime API-client-level guard. **Whether the underlying `ast.parse`/
  `ast.walk` scanning infrastructure already exists repo-wide, or must be
  built new, is determined by direct inspection at implementation time —
  this is implementation sizing, not an architecture blocker**, per the
  consolidated ruling: the guard's required behavior (fail the build on a
  bypass, cover the mutation-wrapper case) is fully specified above
  regardless of which sizing outcome direct inspection finds.
- **Alternatives considered:** rely on code review alone (rejected — proven
  insufficient by the existing tolerated bypass, which presumably passed
  review once already); regex-based scanning (rejected — less reliable
  than genuine AST parsing for detecting call-site patterns robustly);
  treating the tooling-maturity question as a precondition to deciding the
  guard's design (this entry's original framing — rejected: the design
  does not depend on the answer, only the implementation effort does).
- **Risk:** none beyond normal CI-time cost of an additional static-analysis
  pass.
- **Rollback:** N/A — a test/CI addition, not a runtime feature.
- **Exact implementation impact:** one new or extended static-analysis test
  module, scope determined by the direct-inspection finding at
  implementation time (see below).
- **Exact tests:** the guard itself is the test; additionally, a
  negative-control test asserting the guard actually fails the build when
  a deliberately-introduced bypass is present (proves the guard isn't a
  no-op); a test asserting the mutation-wrapper-transport case specifically
  (D16's extension) is caught.
- **Unresolved question:** this session's own grounding material contains a
  direct contradiction between two source audits over whether repo-wide
  `ast.parse`/`ast.walk` tooling **already exists**: one audit found zero
  matches repo-wide; another cited specific `ast.parse`/`ast.walk` usage
  with line numbers across 8 named test files. **Resolved to a sizing task,
  not a blocker**: this is closed by direct file inspection at the start of
  Stage 0 implementation itself — if the tooling already exists, D37 is an
  extension task; if not, it is new infrastructure. Either way, Stage 0
  implementation may begin; this only affects how much of it is spent on
  this guard specifically.

### D38 — Runtime/concurrency/crash-injection proof requirements — four
proof-environment layers
*(Item 35 — RESOLVED as a Stage 0 merge-acceptance criterion, not a
pre-implementation architecture blocker, 2026-07-19. The control-room
preliminary review, PR #177 comment 5013028262 point 8, and the
consolidated Sessions-2-and-3 ruling §15 require distinguishing four
proof-environment layers, not three, and explicitly reject making
Odoo.sh-internal `SIGKILL` the sole acceptable crash-proof route without
first proving that capability exists.)*

- **Fact:** the only genuine-concurrency test pattern proven anywhere
  in-repo (the `db_connect`+`registry.cursor`-monkey-patch+`threading.Thread`
  technique) is currently scoped only to `call.lease`/disconnect-quiescence
  and has never been pointed at `job.py`/`dispatch.py`'s claim logic. No
  genuine OS-process-level crash-injection pattern (real `SIGKILL` or
  equivalent, not a same-process exception) exists anywhere across all 17
  existing test files. Whether genuine OS-process-level crash injection is
  feasible **specifically inside the Odoo.sh multi-worker environment** is
  unestablished by any source in this session's research — but that
  question does not need to gate Stage 0's crash-injection evidence,
  because Odoo.sh feasibility is not the only route to that evidence.
- **Inference:** this entry's original framing conflated two different
  questions — "is genuine process-death evidence required" (yes, settled)
  and "must it come from inside Odoo.sh specifically" (no — a dedicated
  real-Postgres process-kill harness, run outside or alongside Odoo.sh
  where process control is actually available, can supply the
  crash-injection evidence, while Odoo.sh separately supplies
  registry/multi-worker evidence a standalone harness cannot). Treating
  Odoo.sh-internal `SIGKILL` as the *only* acceptable crash-proof route
  was an unproven assumption about environment capability, not a
  requirement of the underlying safety property.
- **Recommendation:** four distinct, separately-evidenced proof layers,
  none substitutable by simulation, with the OS-process-crash layer
  explicitly decoupled from the multi-worker-validation layer.
- **Accepted-candidate wording — RESOLVED:**
  - **Layer 1 — static/unit/logical:** state-machine tests over the
    C1/C2/NET/C3 sequence, proving the design is internally consistent.
  - **Layer 2 — genuine PostgreSQL multi-connection concurrency:**
    extending the proven `db_connect`+monkey-patch+`threading.Thread`
    technique to `job.py`/`dispatch.py`'s claim logic together with the new
    commit points, under genuine Odoo REPEATABLE READ, with at least one
    test per row of D19/D23/D24's crash-window recovery table.
  - **Layer 3 — controlled real process-death/crash harness:** genuine
    OS-process-level crash injection (real `SIGKILL`/equivalent, never a
    same-process exception) against a real PostgreSQL target, run
    **outside or alongside Odoo.sh, wherever process control is actually
    available** — not conditioned on Odoo.sh itself supporting it. Covers
    at minimum a kill between C1→C2, C2→NET, during NET, NET→C3, and
    during C3.
  - **Layer 4 — exact-head Odoo.sh multi-worker validation:** residue,
    lock, session, credential, and redaction proof on the target
    hosting environment, at exact committed head, proving Worker B cannot
    execute a handler Worker A durably owns. **Corrected 2026-07-19 (PR #177
    comment 5014806430 item 4):** Odoo.sh is not required to expose
    `SIGKILL`/worker-process control — Layer 4 does not need "a real killed
    worker" as a hard requirement; where that platform capability is
    actually available, Layer 4 observes sweep-driven reconciliation
    following a real killed worker directly, and where it is not, Layer 4
    instead cross-references Layer 3's accepted crash-injection evidence and
    independently validates the restart/recovery behaviour actually
    available on-platform. This layer supplies multi-worker/environment
    evidence Layer 3's standalone harness cannot, and does not itself need
    to be the source of the
    OS-process-crash evidence.
  All four layers are required; none is substitutable by simulation; **no
  layer may substitute for another** — Layer 4 does not need to reproduce
  Layer 3's crash-injection technique internally, and Layer 3 does not need
  to run inside Odoo.sh. **This is a Stage 0 merge-acceptance criterion,
  not a precondition to beginning Stage 0 implementation** — implementation
  of the C1/C2/NET/C3 code path may begin immediately once DEC-036 itself
  is accepted; these four layers gate the wave's *merge*, not its start.
- **Alternatives considered:** accept simulated/logical proof alone as
  sufficient for acceptance (rejected — simulation is never a substitute
  for genuine crash injection when feasible); requiring OS-level crash
  injection to occur specifically inside Odoo.sh, with no alternative route
  (this entry's original framing — **rejected**: over-conditions a
  provable safety property on one specific environment's unverified
  process-control capability, when a dedicated external harness can supply
  equivalent evidence).
- **Risk:** shipping Stage 0 without all four proof layers risks exactly
  the failure class Layer 2 exists to prevent going unverified in
  production; this risk is unchanged by the four-layer correction — only
  the *routing* of where Layer 3's evidence comes from is corrected.
- **Rollback:** N/A — an acceptance-gate requirement, not a feature.
- **Exact implementation impact:** determines the Stage 0 packet's entire
  test/runtime-plan section (see the Stage 0 packet document, corrected to
  four layers below); Stage 0 implementation itself is not blocked by
  this decision — only its merge is.
- **Exact tests:** enumerated above; see the Stage 0 packet for the full
  test-file-level breakdown.
- **Unresolved question:** whether Odoo.sh itself supports genuine
  OS-process-level crash injection remains factually open, but is **no
  longer blocking** — Layer 3's evidence can be produced by a dedicated
  external harness regardless of that answer, and Layer 4's Odoo.sh
  evidence does not depend on Odoo.sh supporting process-kill internally.
  If, at implementation time, no environment anywhere can supply genuine
  Layer 3 evidence at all (not merely "not inside Odoo.sh"), that remains a
  Wave-3-DoR hard-stop 6/10 escalation — but this is now a narrow,
  concretely-scoped residual case, not the default expectation.

---

## 4. Cross-cluster contradictions, gaps, and inconsistencies

(Full detail in the underlying workflow consolidation; summarized here for
the acceptance record. **Updated 2026-07-19** — items 1 and 9 are now
resolved per the consolidated Sessions-2-and-3 ruling; all others unchanged
from Session A's original consolidation.)

1. **`mutation_attempt.job_id` field type** — three-way conflict
   (Many2one-FK-restrict vs. plain Integer); **RESOLVED under D2** —
   `Many2one('shopify.connector.job', required=True, index=True,
   ondelete='restrict')`, binding per the consolidated ruling §5/§8.
2. **Resolution-field/action naming** — three different names proposed for
   the same settled mechanism (D10/D11); **RESOLVED** — the consolidated
   ruling itself uses and ratifies `resolution_disposition`/
   `action_resolve_mutation_attempt` (plus the new `resolution_source`),
   closing the naming question this item originally left open for
   deliberate ratification.
3. **`attempt_token` regeneration-per-attempt vs. cross-retry tracking** —
   one root cause behind three separately-raised "unresolved question"
   markers (D6, D17, D14); **RESOLVED** — D17's per-attempt scope is
   confirmed sufficient given the retry-eligibility sequencing guarantee
   (no new attempt can exist while the current one is unresolved), closing
   all three markers this item pointed at.
4. **`running_since` vs. `started_at`** — caught by only one review cluster;
   the cluster that designed the commit protocol (D19) never named the
   staleness-clock field the sweep (D26) actually depends on. Resolved at
   D1 (dedicated `running_since` field); recorded as evidence the
   underlying clusters needed a joint read before Stage 0, not just a union
   of outputs — this consolidation record **is** that joint read.
5. **Reconciliation-verdict evidence priority** (idempotency-key replay vs.
   quantity read) — raised by the transaction-protocol review, squarely
   inside the reconciliation-framework review's domain, never connected.
   Orphaned; carried to Part 5 below (D24's unresolved question) — genuinely
   unresolved, narrow-scope, non-blocking for Stage 0 (D24's core recovery
   handling does not depend on the answer).
6. **Batching (K/L vs. 33)** — the two clusters that examined it converge
   cleanly (exclude it, D4); the actual gap is between that converged
   conclusion and the Wave 3 DoR's own still-hedging text ("batching...
   where adopted"), corrected in this session's DoR update.
7. **`preconditions_snapshot` shape: fixed vs. general-allowlist framing** —
   not a true contradiction; resolved at D7 by adopting the general,
   per-domain-declared-allowlist framing with the inventory domain's
   concrete shape as one instance of it.
8. **`manual_review_subreason` new values** — five values now assembled
   into one consolidated list across all review areas
   (`no_reconciliation_strategy` D16, a dedicated "store disconnected
   mid-attempt" value D28/D29, `store_identity_mismatch` D18,
   `idempotency_contract_violation` D6, plus reuse of existing
   `duplicate_risk` D17) — this is the single source for that field's
   extension.
9. **Two pre-existing, overlapping `blocked_manual_review→queued`
   mechanisms** (`action_resolve_manual_review`, `action_manual_retry`) —
   **RESOLVED under D11** — both are extended with an explicit refusal
   guard for any `duplicate_risk`, mutation-attempt-linked job, closing the
   bypass this item originally left open.
10. **AST-tooling-maturity contradiction** — whether repo-wide
    `ast.parse`/`ast.walk` infrastructure already exists is asserted both
    ways within this session's own grounding material; **RECLASSIFIED under
    D37** — this affects D37's effort-sizing only, resolvable by direct
    inspection at implementation time, and does not block Stage 0
    implementation from beginning.

---

## 5. Remaining items after the consolidated Sessions-2-and-3 ruling
(2026-07-19)

**No item below is a pre-implementation architecture blocker.** Every item
that this record originally marked **BLOCKING** is resolved in Part 3
above per the consolidated ruling. What remains falls into three
non-blocking categories: (I) Stage 0 merge-acceptance/implementation-proof
requirements (already correctly scoped as such, not preconditions to
starting); (II) tunable-constant/empirical-measurement gaps; (III) narrow,
genuinely open questions with no bearing on Stage 0's own scope. None
prevents Stage 0 implementation from beginning once DEC-036 is accepted.

**Category I — Stage 0 merge-acceptance criteria (implementation proof,
not architecture):**

1. D38's four-layer runtime/concurrency/crash-injection proof — required
   before Stage 0 **merges**, not before it begins.
2. D22's `pg_stat_activity`-based open-transaction runtime proof — same.
3. D37's AST-tooling-maturity direct-inspection finding — implementation
   sizing, resolved at the start of implementation, not before.

**Category II — tunable constants / empirical-measurement gaps (not design
gaps):**

4. Sweep cadence/timeout exact numeric values (D27) — provisional 30
   minutes, pending Odoo.sh worst-case handler-duration measurement; no
   longer contingent on D28 (resolved).
5. Local idempotency-key safety-margin exact value (D6) — this session's
   own Recommendation (23h), zero source support for the specific number;
   needs explicit control-room ratification of the number, not the
   mechanism (resolved).
6. Retention masking-window exact value (D32) — provisional 180 days;
   needs explicit control-room ratification of the number, not the
   mechanism (resolved).

**Category III — narrow, genuinely open, non-blocking questions:**

7. Reconciliation-verdict evidence priority (idempotency-key-replay read
   vs. independent quantity read) — orphaned between review areas (D24);
   does not block D24's core recovery handling, which does not depend on
   the answer.
8. Whether Shopify's THROTTLED response ever has a genuine server-side
   execution effect — factually open; the conservative `uncertain`
   classification (D9) is safe to *ship* without resolving this.
9. Whether Shopify's `UserError` shape carries a per-entry field-path
   index sufficient for any future batching design — blocking only for
   *future* batching work, never for Stage 0/1 (D4 excludes batching
   entirely).
10. Literal field name for job→store linkage on `shopify.connector.job` —
    never confirmed by direct quote; blocks only D3's `related=` field
    until verified against the actual field list — a narrow,
    implementation-time verification step.

**Out-of-scope document corrections (Gate B, not Stage 0):**

11. `inventory-operating-model.md` §4.4 and
    `task-013-inventory-sync-implementation-packet.md`'s CAS-heading text
    still reference `compareQuantity` as primary and must be corrected to
    `changeFromQuantity` in a Gate B session with those files in its
    allowed list, before Task 013 implementation is authorized — see Part
    0.5's Gate B carry-forward list. This does not block Stage 0, which
    carries no inventory-domain code.

---

## 6. Acceptance authority and status

Acceptance authority for every decision above: **product owner + Claude
control room**, exactly as DEC-031's Layer 2 registration already
specifies. **This record is ACCEPTED.** Disposition: **ACCEPTED — CONTROL-ROOM
GATE A**, per PR #177 comment
[`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)
(2026-07-19), which is this decision set's acceptance authority.

**Status after this correction batch (2026-07-19):** every decision this
record previously marked **BLOCKING** at the individual level (D17, D20,
D22, D28, D35, D37, D38) is now resolved in Part 3, per the binding
consolidated Sessions-2-and-3 ruling (PR #177 comment 5014689445). The
cross-cutting D12 implementation prerequisite (correct the CAS field name
in code from day one) remains a hard implementation prerequisite, not an
architecture blocker — it was never blocking Stage 0's *design*, only
flagging a factual correction that must land in code. The two out-of-scope
document corrections remain a named Gate B prerequisite (Part 5, item 11),
outside this session's allowed-files list, not a Stage 0 blocker.

**Control-room acceptance act (2026-07-19):** the control room has accepted
DEC-036 across its full decision inventory (D1–D38) by PR #177 comment
[`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226):
no decision remains genuinely undecided at the architecture level. What
remains outstanding is (a) Category I's implementation-proof work (Stage 0
merge-acceptance criteria, not a precondition to starting), (b) Category
II's tunable-constant ratifications, and (c) Gate B's out-of-scope document
corrections before Task 013 implementation specifically.
