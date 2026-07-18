# DEC-036 — Wave 3 Gate A: DEC-031 Layer 2 Acceptance Candidate

- **Status: PROPOSED FOR CONTROL-ROOM ACCEPTANCE — NOT YET ACCEPTED.**
  Claude does not accept its own decision package (see this session's
  governing task, §8). This record is a candidate for independent
  control-room review only.
- **Package status: NOT FROZEN.** Per the control-room parallel-audit ruling
  on PR #177 comment
  [`5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989)
  point 8, this package explicitly remains open: an external, independently
  tracked "Session C" code/architecture audit is stated by the control room
  to still require reconciliation against this package before any freeze.
  This session (Session A) cannot access Session C's content directly and
  makes no claim to have reconciled with it — it contributes its **own**
  independent, extremely thorough code/architecture audit (27-agent
  workflow, full read of every named core model file, all 17 test files
  surveyed, the complete Layer 1 and Layer 2 design documents read in full)
  as this session's evidence base, clearly attributed as Session A's work,
  not Session C's.
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
| D1 | Job-row durability fields | Candidate | 1, 18 |
| D2 | `mutation.attempt` core schema | Candidate | 2 |
| D3 | `store_id` denormalization + multi-company scope | Candidate, one sub-gap open | 3 |
| D4 | Attempt granularity = one business pair; batching deferred | Candidate | K, L, 33 |
| D5 | Request-fingerprint normalization | Candidate | 6 |
| D6 | Idempotency-key lifecycle | Candidate, margin value non-binding | 7, N |
| D7 | `preconditions_snapshot` allowlist | Candidate | 8, 28 |
| D8 | `remote_evidence_refs` structured JSON | Candidate | 9 |
| D9 | Outcome taxonomy stays 4-value; THROTTLED→`uncertain` | Candidate | 9, M |
| D10 | Three-layer state model (Job / Outcome / Resolution) | Candidate | 4, 5, A |
| D11 | Administrator-only resolution-override action | Candidate, naming open | 5, 25, H |
| D12 | CAS field-name correction | **RESOLVED** (source conflict), applying it is a Candidate correction | cross-cutting |
| D13 | Job-layer reconciliation-pending gate | Candidate | F, 23 |
| D14 | Reconciliation-job linkage | Candidate | 10, E |
| D15 | Reconciliation-strategy registry | Candidate, owning-model gap open | 11, O |
| D16 | Domain-registration fail-closed runtime gate | Candidate | 12 |
| D17 | Inconclusive-reconciliation cap (N=3) | Candidate, **BLOCKING sub-question** | 24 |
| D18 | Store-identity-change detection | Candidate, residual gap disclosed | 22, G |
| D19 | Transaction/commit-point protocol (C1/C2/NET/C3) | Candidate | 13 |
| D20 | C2 cursor placement + `job_id` field type | **BLOCKED** | 14 |
| D21 | Main-cursor write-isolation invariant | Candidate, needs new tests | C |
| D22 | Lock-vs-open-transaction distinction | **BLOCKED** | D |
| D23 | Crash-window C2→NET recovery | Candidate | 15, B |
| D24 | Crash-window NET→C3 recovery | Candidate, one orphaned question | 16 |
| D25 | Claimability-gate widening for 40001/lock-timeout recovery | Candidate | 17 |
| D26 | Stale-owner sweep mechanism | Candidate | 18 |
| D27 | Sweep cadence & timeout constants | Candidate, values provisional | 19 |
| D28 | Disconnect-quiescence interaction fix | **BLOCKING — control-room choice required** | 20 |
| D29 | Credential-rotation mid-attempt handling | Candidate | 21 |
| D30 | ACL for `mutation.attempt` | Candidate | 26, H |
| D31 | SEC-2 two-role-migration compatibility | Candidate, non-blocking-now | 27 |
| D32 | Retention — retain forever, no deletion | Candidate | 29 |
| D33 | Upgrade path | Candidate | 30 |
| D34 | Uninstall behavior | Candidate | 31, J |
| D35 | `mutation_domain` field ownership | **BLOCKING — control-room choice required** | I, O |
| D36 | Rollback procedure (two-phase) | Candidate | 32 |
| D37 | Repo-wide AST/source guard | **BLOCKING — effort-sizing gap** | 34 |
| D38 | Runtime/concurrency/crash-injection proof requirements | **BLOCKING** | 35 |

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
- **Recommendation:** add four additive fields to `shopify.connector.job`.
- **Accepted-candidate wording:** add `attempt_id` (Char, UUIDv4,
  regenerated per attempt — the CAS/finalize token), `owner_worker_ref`
  (Char, diagnostic, mirrors `call.lease.worker_ref` vocabulary),
  `transport_attempted` (Boolean, default False, committed before any
  network send), and `running_since` (Datetime, set once per claim at C1,
  **never aliased to `started_at`**). All four join `PROTECTED_JOB_FIELDS`,
  writable only via `env.su`.
- **Alternatives considered:** reuse `started_at` as the staleness clock
  (rejected — proven not-reset-on-retry, already load-bearing for the
  24h retry-window clock; aliasing would make every retried job appear
  instantly stale to the sweep).
- **Risk:** four new protected fields widen the sudo-write surface; must be
  covered by the existing AST guard pattern that already inventories sudo
  sites.
- **Rollback:** additive fields, droppable pre-ship; see D33/D36.
- **Exact implementation impact:** `shopify_connector_job.py` field list +
  `PROTECTED_JOB_FIELDS` + `write()` guard; one migration-free upgrade
  (D33).
- **Exact tests:** unit test asserting all four fields reject non-`su`
  writes from every role; unit test asserting `running_since` is set once
  per claim and not mutated by `started_at`'s own logic.
- **Unresolved question:** None.

### D2 — `mutation.attempt` core schema
*(Item 2)*

- **Fact:** No mutation-attempt model exists today. Odoo 19's
  `_sql_constraints` is confirmed silently inert (logs a warning, enforces
  nothing); `models.UniqueIndex` is the current mechanism.
- **Inference:** A dedicated model is required for per-attempt forensics
  beyond what job-row fields alone can carry (real mutation audit trail).
- **Recommendation:** new model `shopify.connector.mutation.attempt`.
- **Accepted-candidate wording:** fields — `job_id` (type: see D20, **BLOCKED**),
  `attempt_id` (Char UUID, required), `mutation_domain` (Selection,
  ownership: see D35, **BLOCKING**), `remote_mutation_intent` (Char/JSON,
  identifiers only), `preconditions_snapshot` (JSON, allowlisted — D7),
  `request_fingerprint` (Char SHA-256 — D5), `shopify_idempotency_key`
  (Char UUID, nullable — D6), `transport_attempted` (Boolean), `outcome`
  (Selection, 4 values — D9/D10), `remote_evidence_refs` (JSON — D8),
  `created_at`/`transport_at`/`resolved_at` (Datetime). Uniqueness on
  `(job_id, attempt_id)` via `models.UniqueIndex`.
- **Alternatives considered:** fields-on-job only, no dedicated model
  (rejected — insufficient for per-attempt forensics once multiple attempts
  per job exist across retries; weaker audit shape).
- **Risk:** new model = new ACL surface (D30) and new join cost on every
  reconciliation read.
- **Rollback:** pre-ship, drop model cleanly (D36 phase 1); post-ship,
  retained as evidence (D32/D36 phase 2).
- **Exact implementation impact:** new Python model file, new ACL rows
  (D30), new migration-free upgrade entry (D33).
- **Exact tests:** `(job_id, attempt_id)` uniqueness enforcement test
  (concurrent insert attempt); field-type/selection validation tests.
- **Unresolved question:** `job_id`'s field type is **BLOCKED** — see D20.

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
*(Items K, L, 33 — directly implements ruling point 5)*

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

### D5 — Request-fingerprint normalization
*(Item 6)*

- **Fact:** No fingerprinting mechanism exists today.
- **Inference:** A forensic identical-request detector is useful but must
  not double as the primary dedup mechanism (that role belongs to
  `operation_scope_key`, unchanged).
- **Recommendation:** SHA-256 over a canonical form.
- **Accepted-candidate wording:** `request_fingerprint` = SHA-256 over a
  canonical JSON serialization of `{mutation_name, sorted variable
  keys/values}`, with the GraphQL document normalized to parsed/re-serialized
  AST form (not raw string). `changeFromQuantity` is explicitly **excluded**
  from the hashed variables (it is a volatile fresh-read CAS value, not a
  business-intent parameter — including it would make every attempt
  fingerprint-unique by construction, defeating the field's purpose).
- **Alternatives considered:** hash the raw request string (rejected —
  whitespace/key-order noise defeats identical-request detection).
- **Risk:** low — forensic-only field, not safety-load-bearing.
- **Rollback:** field inert, droppable.
- **Exact implementation impact:** one normalization helper function, unit
  tested for stability across key order.
- **Exact tests:** fingerprint stability test (same logical request, two
  different key orders → same hash); fingerprint difference test
  (`changeFromQuantity` changes alone → same hash, since it's excluded).
- **Unresolved question:** None.

### D6 — Idempotency-key lifecycle
*(Items 7, N)*

- **Fact:** `@idempotent` is mandatory for `inventorySetQuantities`/
  `inventoryActivate` from API 2026-04; 24-hour retention (source-materials
  refresh §2); `IDEMPOTENCY_CONCURRENT_REQUEST`/`IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/
  `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` exist as user-error codes and are
  absent from the current design's outcome taxonomy.
- **Inference:** the key must be persisted before use (survives crash),
  reused verbatim only within a provably-safe local window, and never
  reused past staleness.
- **Recommendation:** `uuid.uuid4().hex`, persisted at C2, local staleness
  window with a safety margin below Shopify's 24h.
- **Accepted-candidate wording:** `shopify_idempotency_key` validated
  well-formed before interpolation into `@idempotent(key:"...")`, persisted
  at C2. Reused verbatim on retry of the *same* attempt within the local
  staleness window (clock = `mutation_attempt.transport_at`, **not**
  `created_at`); a fresh attempt (new CAS cycle) gets a fresh key and a
  fresh attempt row. `IDEMPOTENCY_CONCURRENT_REQUEST` → `outcome='uncertain'`;
  `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`/`IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED`
  → `outcome='failed_clean'` with the code recorded and logged at elevated
  severity (tracking-defect signal — these codes should never occur under
  correct key management). A mandatorily-`@idempotent` mutation's automatic
  retry (including a THROTTLED-driven retry) **must** carry the prior key
  forward verbatim within-window; past-window retries route through
  reconciliation first, never a blind fresh-key resend.
- **Alternatives considered:** always mint a fresh key per HTTP-level retry
  (rejected — defeats the purpose of `@idempotent`, which exists precisely
  to make retries safe under the *same* key).
- **Risk:** a wrongly-sized local margin could either reuse a key Shopify
  has already expired (loses idempotency protection silently) or discard a
  still-valid key too early (unnecessary reconciliation reads).
- **Rollback:** field inert, droppable pre-ship.
- **Exact implementation impact:** key-generation/validation helper;
  key-carry-forward flag `idempotency_key_carried_forward` (Boolean) on the
  attempt or job retry path.
- **Exact tests:** key reuse within window; key non-reuse past window
  (routes to reconciliation, not fresh resend); all three idempotency
  error codes correctly classified.
- **Unresolved question:** **the 23-hour local safety margin proposed here
  is this session's own Recommendation/inference, with zero source support
  for the specific number** — needs explicit control-room ratification and,
  ideally, empirical Shopify round-trip-latency validation before Stage 0
  ships with a hardcoded value.

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
- **Accepted-candidate wording:** `outcome` remains the closed 4-value
  Selection `pending`/`succeeded`/`failed_clean`/`uncertain`. `THROTTLED`
  (HTTP 429 or GraphQL-body error) is reclassified from `failed_clean` to
  **`uncertain`**, routed through reconciliation like any other ambiguous
  outcome, for every `mutation_domain`, pending an explicit Shopify
  non-execution guarantee (none found as of 2026-07-18).
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

### D10 — Three-layer state model (Job / Outcome / Resolution)
*(Items 4, 5, A)*

- **Fact:** The current design doc uses `pending`/`succeeded`/`failed_clean`/
  `uncertain` in its outcome taxonomy (§5.1) but separately describes an
  operator override producing `resolved_applied`/`resolved_not_applied`
  (§6) — two vocabularies for what reads like the same concept, never
  reconciled in the source document.
- **Inference:** these are not the same concept — one is a machine-observed
  outcome, the other is a human judgment recorded only when the machine
  path is exhausted. Conflating them into one flat enum is the actual
  defect, not either vocabulary individually.
- **Recommendation:** a strict three-layer hierarchy, the natural extension
  of a pattern this codebase already uses (`state` + orthogonal qualifier,
  e.g. `manual_review_subreason`).
- **Accepted-candidate wording:** **Layer J (Job)** —
  `shopify.connector.job.state`: unchanged 10-value machine, zero new
  states/transitions. **Layer O (Outcome)** —
  `mutation.attempt.outcome`: closed 4-value Selection (D9), machine-observed
  only; the *only* field any retry-eligibility logic may read. **Layer R
  (Resolution)** — `mutation.attempt.resolution_disposition`: new, separate,
  nullable 2-value Selection (`applied`/`not_applied`), human-asserted only
  via D11's override. Setting it atomically forces `outcome` to
  `succeeded`/`failed_clean` via the same shared helper the reconciliation-read
  path uses. `resolved_applied`/`resolved_not_applied` as free-floating
  string values are retired — they exist only as `resolution_disposition`'s
  two values. Full transition table: Part 5 below.
- **Alternatives considered:** one flat enum spanning both machine and
  human states (rejected — this is exactly the original design's own
  internal inconsistency; conflating "what happened" with "what a human
  decided happened" is the root defect).
- **Risk:** three-layer models are more complex to reason about than one
  flat enum — mitigated by the fact this codebase already uses the
  `state`+qualifier pattern elsewhere (`manual_review_subreason`), so this
  is consistent, not novel.
- **Rollback:** additive fields, droppable pre-ship; post-ship, retained
  per D32.
- **Exact implementation impact:** new `resolution_disposition`/
  `resolution_reason`/`resolution_uid`/`resolution_at` fields; a shared
  helper method used by both the reconciliation-read path and D11's
  override action.
- **Exact tests:** full state-machine unit test covering all 11 transition
  steps in Part 5; test asserting no code path reads `resolution_disposition`
  for retry-eligibility (only `outcome` may be read for that purpose).
- **Unresolved question:** the canonical field/action **names**
  (`resolution_disposition` vs. `resolution` vs. others) were proposed
  differently across this session's own review clusters — see Part 3 item 2
  — not a substantive gap, but the control room should ratify the name
  deliberately.

### D11 — Administrator-only resolution-override action
*(Items 5, 25, H.3)*

- **Fact:** `action_manual_retry` (job_actions.py) and
  `action_resolve_manual_review` (job.py) already exist, both
  Reviewer/Admin-gated, both reaching `blocked_manual_review→queued`,
  neither requiring a mandatory reason.
- **Inference:** D11 adds a **third** mechanism reaching a related job-state
  transition, which was never checked against the two pre-existing ones for
  overlap (Part 3 item 9).
- **Recommendation:** a single sanctioned action, deliberately stricter
  than the two existing mechanisms.
- **Accepted-candidate wording:** `action_resolve_mutation_attempt`,
  restricted to `group_shopify_connector_admin` only, **no Reviewer
  bypass** (matching `action_mask_customer_pii`'s precedent, not
  `action_manual_retry`'s — justified because a wrong call causes silent,
  permanent Odoo/Shopify divergence with no automatic re-check, a
  materially higher-stakes error class). Gated on `outcome=='uncertain'`
  and the job being `blocked_manual_review`/`manual_review_subreason='duplicate_risk'`;
  requires a mandatory, redaction-passed reason (`UserError` otherwise).
  One narrow `sudo()` write sets `resolution_disposition`/`resolution_reason`/
  `resolution_uid`/`resolution_at` **and** the corresponding `outcome`,
  paired atomically with the job's existing sanctioned
  `blocked_manual_review→queued` transition and exactly one `job.log` row
  (`event_type='manual_action'`). The override never edits remote Shopify
  state — any correction is a new, ordinary, fully-wrapped mutation job.
- **Alternatives considered:** reuse `action_manual_retry` or
  `action_resolve_manual_review` directly (rejected — neither requires a
  mandatory reason nor is Admin-only, both too permissive for a
  divergence-risk decision).
- **Risk:** operator error (wrong disposition) causes silent Odoo/Shopify
  divergence — mitigated by mandatory reason + audit row + Admin-only gate,
  not eliminated.
- **Rollback:** remove the action; underlying jobs remain
  `blocked_manual_review` (no data loss, just no override path).
- **Exact implementation impact:** one new server action method, ACL
  restricted to Admin group (D30), one `job.log` write.
- **Exact tests:** Reviewer-denied test; missing-reason `UserError` test;
  atomic-commit test (resolution fields + outcome + job transition + log
  row all-or-nothing).
- **Unresolved question:** the overlap between this new action and the two
  pre-existing `blocked_manual_review→queued` mechanisms is **not resolved**
  by this decision alone — carried to Part 7 as a genuine gap requiring
  control-room attention (should the two older actions be scoped to
  exclude `duplicate_risk`/mutation-attempt-linked jobs, or left as-is with
  documented precedence?).

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
  same transaction as the `outcome='uncertain'` attempt commit and
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

### D14 — Reconciliation-job linkage
*(Items 10, E)*

- **Fact:** `call.lease.job_id` is a deliberate non-FK Integer, specifically
  to avoid `FOR KEY SHARE`/`FOR NO KEY UPDATE` lock contention with
  `_claim_for_dispatch`.
- **Inference:** a reconciliation job needs to reference its target attempt
  precisely (not "most recent attempt for job_id," which is unsafe under
  retries/races), and should follow the same non-FK precedent for the same
  contention-avoidance reason.
- **Recommendation:** a new non-FK Char field on the reconciliation job.
- **Accepted-candidate wording:** a reconciliation-read job links to its
  target attempt via a new non-FK Char field `mutation_attempt_id` on
  `shopify.connector.job` (storing the target `attempt_id` UUID). **Frozen
  at creation, never lazily resolved**: the same commit that sets
  `outcome='uncertain'` (C3) creates the reconciliation job with
  `mutation_attempt_id` set to that exact `attempt_id`. The reconciliation
  handler looks up by the compound `(job_id, attempt_id)` key and fails
  closed to `blocked_manual_review` if the target row's `outcome` is no
  longer `uncertain` at dispatch time. A new `operation_scope_key`
  convention is needed for reconciliation jobs (e.g.
  `reconcile:{store}:{mutation_domain}:{attempt_id}`), since `enqueue()`
  has no idempotency/scope-key mechanism of its own for this job type.
- **Alternatives considered:** FK reference (rejected for the same
  lock-contention reason `call_lease.job_id` was made an Integer);
  "most recent attempt for job_id" lookup (rejected — unsafe under
  retries/races, the exact scenario reconciliation exists to handle).
- **Risk:** a non-FK reference relies on application-level consistency, not
  database-level referential integrity — mitigated by the fail-closed
  dispatch-time check.
- **Rollback:** additive field, droppable pre-ship.
- **Exact implementation impact:** one new Char field + one new
  `operation_scope_key` convention + one dispatch-time consistency check.
- **Exact tests:** test asserting a reconciliation job created for a
  superseded attempt_id fails closed at dispatch, not silently proceeding.
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
- **Unresolved question:** **which model hosts this method** —
  `shopify.connector.job.dispatch` by analogy with `_get_replay_policies()`,
  or a new dedicated model — is never stated in the original design
  document itself (a genuine gap in the *original* design, not introduced
  by this review) and must be settled by the control room before Stage 0
  implementation.

### D16 — Domain-registration fail-closed runtime gate
*(Item 12)*

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

### D17 — Inconclusive-reconciliation cap (N=3)
*(Item 24)*

- **Fact:** the original design's "N=3" language never distinguished
  consecutive-inconclusive-verdicts from total-retry-cycles.
- **Inference:** if the counter resets every time a new `attempt_id` is
  minted (as its natural placement on the attempt row implies), a mutation
  alternating THROTTLED-triggered retries with genuine `uncertain` outcomes
  could accumulate 3 inconclusive verdicts *per attempt row* without ever
  tripping the cap across the full retry chain — silently defeating its
  purpose.
- **Recommendation:** add the counter, explicit about what increments it,
  but leave the cross-attempt persistence question open for control-room
  decision.
- **Accepted-candidate wording:** add `inconclusive_reconciliation_count`
  (Integer, default 0, protected) to `mutation.attempt`. Incremented only
  on a literal reconciliation-read verdict of **"inconclusive"** (not
  "not-applied," a different, fully-resolving verdict). Increment happens
  under a re-acquired row lock (mirroring `_recover_after_concurrency_conflict`'s
  discipline) so two racing reconciliation jobs cannot both silently
  increment past the cap; reaching 3 transitions the job to
  `blocked_manual_review`/`duplicate_risk` in the same commit.
- **Alternatives considered:** track the count at job level instead
  (survives `attempt_id` regeneration) — this is in fact the **recommended**
  resolution direction (see unresolved question below), not fully rejected,
  but not adopted outright because it requires a product-owner safety-property
  decision, not an inference.
- **Risk:** as currently schema'd (per-attempt), the cap may functionally
  never fire for a mutation that alternates retry types — a real safety
  gap if left unresolved.
- **Rollback:** additive field, droppable pre-ship.
- **Exact implementation impact:** one Integer field + one row-locked
  increment path.
- **Exact tests:** concurrent-increment race test (two reconciliation jobs
  racing to increment, cap must not be bypassable); cap-trip test at
  exactly 3.
- **Unresolved question:** **BLOCKING, genuinely undecidable from
  precedent alone.** Whether the cap persists across `attempt_id`
  regeneration (tracked at job level, surviving retries) or resets per
  `attempt_id` (as currently schema'd) is a product-owner safety-property
  decision that materially changes the guarantee, and must be made
  explicitly before Stage 0 ships this field.

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
  of every reconciliation read.
- **Accepted-candidate wording:** reconciliation reads (D14) query
  `shop { myshopifyDomain }` alongside domain-specific selection, as the
  **first** evaluation step, before interpreting any other response data.
  Comparison reuses the existing single-field string-equality check
  verbatim. On mismatch: route directly to
  `blocked_manual_review`/`manual_review_subreason='store_identity_mismatch'`
  (new, distinct from `duplicate_risk`), bypassing the normal `uncertain`
  reconcile-then-retry flow entirely. No new check is added to
  `_admit`/ordinary mutation-send admission — cost is scoped to
  reconciliation only. **Companion fix:** `_run_connection_probe`'s
  existing domain-mismatch branch must additionally call
  `action_mark_reconnect_needed` (closing a pre-existing asymmetry with the
  auth-failure path).
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
*(Item 13)*

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
- **Accepted-candidate wording:** see Part 6 below for the complete
  protocol. Non-mutation job types (`local_only`, `remote_read_replay_safe`)
  retain the existing single-commit `_drain_one` path unchanged.
- **Alternatives considered:** keep the single-commit path for mutation
  types too (rejected — provides no crash-recoverable intermediate state,
  the entire reason Layer 2 exists).
- **Risk:** ~2 extra commits per mutation attempt (C1 already exists in the
  job-claim design; C2 and the C3 re-lock are new) — small, bounded, and
  dwarfed by the network round-trip.
- **Rollback:** scoped to mutation job types only; non-mutation types are
  unaffected and require no rollback consideration.
- **Exact implementation impact:** `_dispatch_one`/`_invoke_handler`
  branch by job-type class (mutation vs. non-mutation), each with its own
  commit-point implementation.
- **Exact tests:** see D38 for the full runtime/concurrency/crash-injection
  test requirements.
- **Unresolved question:** C2's exact cursor placement — see D20, BLOCKED.

### D20 — C2 cursor placement + `job_id` field type
*(Item 14 — BLOCKED)*

- **Fact:** two unresolved, load-bearing conflicts exist: (a) whether C2
  commits on the main cursor or a side cursor mirroring `call_lease`'s
  `_admit` pattern; (b) `mutation_attempt.job_id`'s field type, where this
  session's own review clusters reached three-way-conflicting conclusions
  (Many2one-FK-restrict for uninstall-safety per D34's precedent vs. plain
  Integer per `call_lease.job_id`'s lock-contention-avoidance precedent).
- **Inference:** the design's original justification for main-cursor C2
  rests on the now-corrected false `_commit_progress()` citation (D19) and
  does not engage with the actual isolation property the side-cursor
  alternative exists to provide. On (b), `call_lease`'s need for Integer
  stems from its *concurrent, multi-worker admission-check* access pattern;
  `job_log.job_id`'s FK+restrict is safe today because writes come from the
  single worker that already holds the job's claim lock, appending
  sequentially — a pattern C1/C2/C3 shares. This suggests FK+`ondelete='restrict'`
  is likely compatible with D25's widened claimability-gate access pattern,
  but this is a **reasoned bridging observation, not a proof**.
- **Recommendation:** do not accept either sub-question as settled; require
  D38's genuine-concurrency test to prove which access pattern
  `mutation.attempt`'s actual read/write behavior resembles before choosing
  the field type, and require a proven, tested "no non-connector-model
  write pending on the main cursor at C2 time" invariant (D21) before
  accepting main-cursor C2.
- **Accepted-candidate wording:** **Not accepted as proven safe.** Two
  candidate mechanisms remain open for C2: (a) main-cursor pre-network
  commit, contingent on D21's proven invariant; or (b) a side-cursor commit
  mirroring `call_lease`'s `_admit` pattern, which structurally eliminates
  the "unrelated business changes committed prematurely" risk rather than
  merely testing for it. `job_id`'s field type is similarly open pending
  D38's proof.
- **Alternatives considered:** both live options are stated above; no
  third alternative was found with independent support.
- **Risk:** shipping either choice unproven risks either (main cursor)
  accidentally co-committing unrelated business state at C2, or (side
  cursor, wrong field type) reproducing `call_lease`'s known lock-contention
  class under D25's widened access pattern.
- **Rollback:** N/A — this is a pre-implementation design gate, not a
  shipped feature.
- **Exact implementation impact:** Stage 0 implementation **cannot begin
  the C2 code path** until this is resolved — a hard prerequisite, carried
  into the Stage 0 packet's hard-stops.
- **Exact tests:** D38's genuine-concurrency suite must be designed to
  produce evidence for this decision, not merely validate a decision
  already made.
- **Unresolved question:** **BLOCKING.** Both the cursor-placement and
  field-type sub-questions require empirical proof (D38) or an explicit
  control-room risk-acceptance choice before Stage 0 implementation of the
  C2 code path may begin.

### D21 — Main-cursor write-isolation invariant
*(Item C — directly implements ruling point 6)*

- **Fact:** between C1 and C2, today's architecture happens to make "only
  `shopify.connector.job`/`mutation.attempt` writes occur on the main
  cursor" true, but only because of today's narrower one-job-at-a-time
  processing shape — nothing in the code enforces it as an invariant.
- **Inference:** this is currently an unstated, unproven assumption riding
  on accident, not design. Odoo 19's REPEATABLE READ isolation
  (source-materials refresh §5) makes violating this invariant
  particularly dangerous: a stray write between C1/C2 would be silently
  co-committed at C2, and under REPEATABLE READ, any code relying on
  "freshly committed" visibility after that point could observe stale
  snapshot data unless it explicitly starts a new transaction.
- **Recommendation:** state the invariant explicitly and prove it with a
  new test class.
- **Accepted-candidate wording:** between C1 and C2 inclusive, the only ORM
  writes permitted on the main cursor are to `shopify.connector.job` and
  `shopify.connector.mutation.attempt`; `preconditions_snapshot` gathering
  is read-only by contract. This is the **clean-cursor / no-unrelated-dirty-state
  invariant** the control-room ruling requires — enforced by a genuinely
  new test pattern (inspecting ORM dirty-state / `env.all.towrite`
  immediately before the C2 commit), which does not exist anywhere in the
  current 17-file test inventory and must be built, not assumed to already
  exist. Additionally, per the REPEATABLE READ consequences recorded in
  the source-materials refresh §5: any recovery/reconciliation code that
  re-reads a job or attempt row after a crash or a sibling worker's commit
  must force a fresh read via `invalidate_recordset()` + re-`browse()`/
  re-`search()`, mirroring the existing `_claim_for_dispatch` precedent,
  at every point in the C1/C2/C3 protocol that depends on cross-transaction
  visibility.
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

### D22 — Lock-vs-open-transaction distinction
*(Item D — BLOCKED, flagged by this session's own review cluster as the
single most significant unresolved item in the entire transaction-protocol
review)*

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
  unproven half.
- **Accepted-candidate wording:** **[BLOCKED — insufficient evidence, fails
  closed per this review].** No PostgreSQL row/table lock is held across
  the network call in any documented mutation admission path (proven).
  Whether a bare open (lock-free) transaction on the main cursor spans the
  network call is **not proven** for the C1–C2–NET path and must be closed
  with (a) an explicit "nothing on the main cursor between C2 and NET"
  coding rule — all data needed for the mutation body must be resolved and
  captured into plain Python values before C2, never re-derived after it —
  and (b) a genuine `pg_stat_activity`-based runtime test, before this item
  can be marked closed.
- **Alternatives considered:** assume the risk away because no lock is
  held (rejected — the operational hazard is at the connection/transaction
  level, invisible to ORM-level lock analysis).
- **Risk:** an idle-in-transaction connection holding a REPEATABLE READ
  snapshot across a 20-second network read timeout is a documented general
  PostgreSQL operational hazard (vacuum/xmin horizon impact) independent of
  correctness — a real production risk if left unaddressed at scale.
- **Rollback:** N/A — pre-implementation gate.
- **Exact implementation impact:** Stage 0's NET-window handler code must
  be written under the explicit "nothing on `self.env.cr` between C2 and
  NET" discipline from day one; this is a coding-review-enforced rule, not
  optional guidance.
- **Exact tests:** a new `pg_stat_activity`-based test class asserting no
  open transaction is observed on the connection during the simulated
  network-call window — does not exist anywhere in-repo today.
- **Unresolved question:** **BLOCKING.** No open-transaction-spans-network-call
  proof exists; required before Stage 0 acceptance (tracked in D38).

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
  currently-committed `attempt_id` matches the value the recovering
  transaction itself holds — in **addition to**, not instead of, the
  existing `queued`/due-`retry_waiting` branch. A `running` row with a
  non-matching or absent locally-held `attempt_id` remains excluded,
  exactly as today.
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
  the widened branch only matches on exact `attempt_id`, and that a
  non-matching `running` row remains correctly excluded.
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
  pattern for this class of constant. **Acceptance of any specific timeout
  value is conditioned on D28 being resolved.**
- **Alternatives considered:** derive cadence from the disconnect-quiescence
  cadence directly (rejected — no coupling requirement exists; matching by
  convention is sufficient and simpler).
- **Risk:** a timeout value accepted before D28 is resolved could be unsafe
  regardless of its numeric value — see D28.
- **Rollback:** cron interval/timeout are ordinary tunable config, not
  structural.
- **Exact implementation impact:** two named constants in the sweep cron
  implementation.
- **Exact tests:** N/A directly (measurement-driven, not test-driven);
  covered indirectly by D38's runtime proof.
- **Unresolved question:** exact numeric timeout value is an **empirical-measurement
  gap**, not a design gap — provisional 30 minutes pending Odoo.sh
  worst-case handler-duration measurement, and contingent on D28.

### D28 — Disconnect-quiescence interaction fix
*(Item 20 — BLOCKING, flagged by this session's own review cluster as the
single highest-severity gap in that cluster, confirmed by direct three-file
code reading, not inferred)*

- **Fact:** `_finalize_disconnect_timed_out()` unconditionally clears the
  store credential and deletes the lease at `DISCONNECT_QUIESCE_TIMEOUT`
  (15 minutes), with no way to distinguish a live vs. orphaned lease.
  `ShopifyQuiescedError` (the error `_admit`'s state gate raises against a
  quiesced store) has **no dedicated handling anywhere in `_invoke_handler`
  today** — it falls to the generic `unknown_system_error` safety net.
- **Inference:** the design's claim that "the sweep defers to quiescence...
  resolved by timeout ordering alone" is **not adequately supported**. An
  orphaned lease from a crashed mutation attempt is invisible to the sweep
  until t=30min (D27's provisional timeout), but credentials are cleared at
  t=15min — stranding the eventual reconciliation attempt, which then fails
  via `ShopifyQuiescedError` and is misleadingly logged as
  `unknown_system_error`, corrupting the audit trail.
- **Recommendation:** two remediations exist; the control room must choose
  explicitly.
- **Accepted-candidate wording:** **(a)** set the sweep timeout strictly
  *less than* `DISCONNECT_QUIESCE_TIMEOUT` (proposed 10 < 15 min, still
  subject to D27's "exceeds worst-case handler duration" floor); or **(b)**
  extend `_finalize_disconnect_timed_out` to check for open mutation jobs
  bound to the store and defer credential-clearing. Regardless of which,
  `ShopifyQuiescedError` **must** be wired into an explicit `except` branch
  in `_invoke_handler`, routed to a dedicated `blocked_manual_review`
  subreason distinguishing "store disconnected mid-attempt" from genuine
  outcome ambiguity — this fix is shared with D29 and is not itself in
  dispute, only (a) vs (b) is.
- **Alternatives considered:** leave the interaction as originally
  designed, relying on timeout-ordering alone (rejected — proven
  inadequate by direct code reading, not merely theorized).
- **Risk:** shipping without resolving this strands reconciliation attempts
  for any mutation crashing near the quiescence boundary — a real,
  demonstrated gap, not speculative.
- **Rollback:** N/A — pre-implementation gate.
- **Exact implementation impact:** either a timeout-constant change (a) or
  a new open-mutation-job check in `_finalize_disconnect_timed_out` (b);
  either way, one new `except ShopifyQuiescedError` branch in
  `_invoke_handler`.
- **Exact tests:** a test reproducing the exact strand scenario (crash near
  the quiescence boundary, verify the chosen remediation prevents the
  stranded-reconciliation failure mode).
- **Unresolved question:** **BLOCKING — explicit control-room choice
  required between (a) and (b)**, not inferable from precedent alone.

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

### D30 — ACL for `mutation.attempt`
*(Items 26, H.1, H.2, H.4, H.5 — directly implements ruling point 7)*

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
- **Accepted-candidate wording:** four ACL rows, one per current role
  (Auditor/Operator/Reviewer/Admin), each `perm_read=1, perm_write=0,
  perm_create=0, perm_unlink=0` — **including Admin**, no role gets
  write/create/unlink via ACL. All creation/write happens exclusively via
  `sudo()` at C2, C3, and D11's override action — a **closed sudo-site
  inventory** (exactly 3 sites) enforced by an AST test that fails the
  build on a 4th. Unlink is permanently denied to all roles including
  Admin (ties to D32's retain-forever retention).
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

### D31 — SEC-2 two-role-migration compatibility
*(Item 27)*

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
- **Risk:** if `implied_ids` inheritance does not work as assumed, SEC-2
  could ship with an accidental ACL gap for the new roles — mitigated by
  flagging this as blocking *for the SEC-2 packet specifically*, not for
  Wave 3.
- **Rollback:** N/A.
- **Exact implementation impact:** none for Wave 3; a verification task for
  the future SEC-2 implementation session.
- **Exact tests:** deferred to the SEC-2 packet's own test requirements.
- **Unresolved question:** the `implied_ids` inheritance mechanic itself is
  unverified — non-blocking now, blocking at SEC-2 time.

### D32 — Retention: retain forever, no deletion
*(Item 29)*

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
  whether retention-forever or time-bounded pruning is the right policy.
- **Recommendation:** retain indefinitely, mirroring `job`/`job.log`'s
  proven append-only posture, rather than inventing a new, unprecedented
  delete-based sweep for this specific model.
- **Accepted-candidate wording:** `mutation.attempt` rows are retained
  **indefinitely** — no cron, sweep, or manual action defined in Wave 3
  Stage 0 ever deletes a row — mirroring `job`/`job.log`'s append-only,
  `ondelete='restrict'`-anchored posture (DEC-030). If storage growth later
  requires actual deletion, that is an explicitly new, separately-decided,
  separately-tested superuser-only cron capability — out of scope for
  Stage 0.
- **Alternatives considered:** the original design's claimed 180-day sweep
  (rejected — no such mechanism exists to align with or extend; would
  require inventing an entirely new delete-based capability this
  connector's audit trail has never had, for its single highest-value
  forensic record).
- **Risk:** unbounded storage growth over time — an accepted, explicit
  trade-off favoring forensic completeness over storage efficiency for
  Stage 0; revisit if storage becomes a measured problem.
- **Rollback:** N/A — retention posture, not a droppable feature; a
  future deletion capability would be its own separately-reviewed change.
- **Exact implementation impact:** `unlink()` permanently denied to all
  roles via ACL (D30); no cron created for this model.
- **Exact tests:** test asserting no code path ever calls `.unlink()` on
  this model (AST or runtime assertion).
- **Unresolved question:** None.

### D33 — Upgrade path
*(Item 30)*

- **Fact:** none of D1's four new job fields has a computable historical
  value for pre-existing rows (unlike LC-1's `original_job_type`, which
  does).
- **Inference:** no `post-migrate.py` backfill is required — pre-Layer-2
  rows correctly resolve to their declared defaults.
- **Recommendation:** a standard additive upgrade, but with the full
  surface enumerated explicitly, not understated.
- **Accepted-candidate wording:** the four D1 job fields require **no**
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
  corrected in this session's update (done); no code change required
  beyond what LC-1's existing mechanism already provides, contingent on
  D35.
- **Exact tests:** an uninstall-simulation test asserting `mutation.attempt`
  rows survive a domain-only uninstall and are correctly retyped/queryable
  afterward.
- **Unresolved question:** **contingent on D35** — an incorrectly
  domain-owned `mutation_domain` selection field without an LC-1-style
  historic-conversion mechanism would reintroduce the exact failure DEC-030
  already fixed once; this decision is only fully safe once D35 is
  resolved.

### D35 — `mutation_domain` field ownership
*(Items I, O — BLOCKING, genuinely unresolved in either direction)*

- **Fact:** two live, precedent-supported options exist, pulling in
  opposite directions. `job_type`'s ownership rule (whichever module owns a
  mutation's handler also owns its domain-vocabulary value, via
  `selection_add`) is DEC-008-consistent, proven precedent. DEC-030's
  Option D (core carrying domain vocabulary directly) was explicitly
  rejected once already, for reasons that would recur if `mutation_domain`
  is made core-fixed.
- **Inference:** neither option is inferable from precedent alone — they
  are both legitimate readings of different, real precedents, and getting
  this wrong reproduces the same class of "documented failure discovered
  at first uninstall" DEC-030 was written to prevent.
- **Recommendation:** present both options fully, require an explicit
  control-room choice.
- **Accepted-candidate wording:** **Not resolved by this record — genuinely
  blocking.** Option (a): domain-`selection_add` (mirrors `job_type`'s
  proven ownership rule) — requires a `mutation.attempt`-scoped analogue of
  `_reassign_to_historic_job_type()` to be shipped in **core, before Stage 1**
  registers its first value, exactly mirroring LC-1's proven "ship the
  generic mechanism before the first consumer" sequencing. Option (b):
  core-fixed, non-extensible Selection enumerating the closed MVP set
  directly (consistent with the original L2-D6's "closed set... never an
  implicit inheritance" framing) — sidesteps the uninstall problem entirely
  but reintroduces exactly the "core carries domain vocabulary" pattern
  DEC-030's Option D was already explicitly rejected for.
- **Alternatives considered:** the two options above are the only two with
  real precedent support found in this session's research; no third
  alternative was identified.
- **Risk:** choosing (b) without acknowledging the DEC-030 precedent
  conflict, or choosing (a) without shipping the historic-conversion
  mechanism first, both reproduce known failure classes.
- **Rollback:** N/A — foundational schema decision, must be made before
  Stage 0 implementation of the field.
- **Exact implementation impact:** determines whether Stage 0 must ship a
  new core historic-conversion helper (option a) or not (option b) —
  materially different Stage 0 scope depending on the choice.
- **Exact tests:** whichever option is chosen, an uninstall-simulation test
  proving D34's classification holds under that specific mechanism.
- **Unresolved question:** **BLOCKING — explicit control-room decision
  required, not inferable from precedent alone.** O's attached validation
  note: whichever option is chosen, D15's registry, D30's read-only ACL,
  and this field's ownership together are the complete mechanism keeping
  core domain-agnostic; a build-time/AST guard (folded into D37) must
  assert zero literal domain-specific branching in core dispatch/job/attempt
  files.

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

### D37 — Repo-wide AST/source guard
*(Item 34 — BLOCKING for effort-sizing)*

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
- **Accepted-candidate wording:** a genuine `ast`-module parse across every
  `.py` file under `addons/shopify_connector_*/` must fail the build on any
  `ast.Call` resolving to a raw HTTP-transport call
  (`requests.get/post/request`, etc.) outside `_send()` and an explicit,
  individually justified allowlist (seeded with the existing
  `product_importer.py:1958` CDN bypass). Existing file-scoped guards are
  retained, not replaced.
- **Alternatives considered:** rely on code review alone (rejected — proven
  insufficient by the existing tolerated bypass, which presumably passed
  review once already); regex-based scanning (rejected — less reliable
  than genuine AST parsing for detecting call-site patterns robustly).
- **Risk:** none beyond normal CI-time cost of an additional static-analysis
  pass.
- **Rollback:** N/A — a test/CI addition, not a runtime feature.
- **Exact implementation impact:** one new static-analysis test module.
- **Exact tests:** the guard itself is the test; additionally, a
  negative-control test asserting the guard actually fails the build when
  a deliberately-introduced bypass is present (proves the guard isn't a
  no-op).
- **Unresolved question:** **BLOCKING for effort-sizing, not just design.**
  This session's own grounding material contains a direct, unresolved
  contradiction between two source audits over whether repo-wide
  `ast.parse`/`ast.walk` tooling **already exists**: one audit found zero
  matches repo-wide; another cited specific `ast.parse`/`ast.walk` usage
  with line numbers across 8 named test files. **This must be closed by
  direct file inspection before Stage 0 is sized** — if the tooling already
  exists, D37 is an extension task; if not, it is new infrastructure. Not
  resolved by this record.

### D38 — Runtime/concurrency/crash-injection proof requirements
*(Item 35 — BLOCKING)*

- **Fact:** the only genuine-concurrency test pattern proven anywhere
  in-repo (the `db_connect`+`registry.cursor`-monkey-patch+`threading.Thread`
  technique) is currently scoped only to `call.lease`/disconnect-quiescence
  and has never been pointed at `job.py`/`dispatch.py`'s claim logic. No
  genuine OS-process-level crash-injection pattern (real `SIGKILL` or
  equivalent, not a same-process exception) exists anywhere across all 17
  existing test files.
- **Inference:** three distinct proof layers exist and must not be
  conflated — logical/simulated unit tests prove the *design* is
  internally consistent; genuine multi-connection concurrency tests prove
  the *claim/lock/commit-point* mechanics hold under real concurrent
  access; genuine OS-level crash injection proves the *recovery tables*
  (D23/D24) hold against an actual process death, not a simulated one.
  Accepting Layer 2 as "runtime-proven" on the strength of only the first
  layer, while the foundational claim-lock mechanism itself is still only
  "REDUCED, not closed" per the risk register's own open SRR-04/SRR-09
  entries, would be evidence-inverted.
- **Recommendation:** require all three layers explicitly, with SRR-04/SRR-09
  resolved or explicitly carried forward as named residual risk.
- **Accepted-candidate wording:** three **distinct** proof layers required
  before Stage 0 is declared "runtime-proven": **(1)** logical/simulated
  unit tests over the C1/C2/NET/C3 sequence; **(2)** a genuine
  multi-connection concurrency suite (extending the proven
  `db_connect`+monkey-patch+`threading.Thread` technique to
  `job.py`/`dispatch.py`'s claim logic together with the new commit points),
  with at least one test per row of D19/D23/D24's crash-window recovery
  table; **(3)** a genuine **OS-process-level** crash-injection test (real
  `SIGKILL`/equivalent) against a real hosted-Postgres target, covering at
  minimum a kill between C2→NET and NET→C3. **If genuine OS-level crash
  injection is infeasible on the target Odoo.sh environment — a capability
  entirely unestablished by any source in this session's research — this
  is Wave-3-DoR hard-stop 6/10: stop, do not substitute simulation,
  escalate for an explicit, separately-logged product-owner risk-acceptance
  decision.**
- **Alternatives considered:** accept simulated/logical proof alone as
  sufficient for acceptance (rejected — explicitly forbidden by this
  decision's own reasoning and by Wave-3-DoR hard-stop 6/10; simulation is
  never a substitute for genuine crash injection when feasible).
- **Risk:** shipping Stage 0 without all three proof layers risks exactly
  the failure class Layer 2 exists to prevent going unverified in
  production.
- **Rollback:** N/A — an acceptance-gate requirement, not a feature.
- **Exact implementation impact:** determines the Stage 0 packet's entire
  test/runtime-plan section (see the Stage 0 packet document).
- **Exact tests:** enumerated above; see the Stage 0 packet for the full
  test-file-level breakdown.
- **Unresolved question:** **BLOCKING.** Whether genuine OS-process-level
  crash injection is feasible on the target Odoo.sh hosting environment is
  entirely unestablished by any source across this session's entire
  research — must be determined empirically before Stage 0's runtime plan
  can be finalized, per the hard-stop above.

---

## 4. Cross-cluster contradictions, gaps, and inconsistencies

(Full detail in the underlying workflow consolidation; summarized here for
the acceptance record.)

1. **`mutation_attempt.job_id` field type** — three-way conflict
   (Many2one-FK-restrict vs. plain Integer); folded into D20, **BLOCKING**.
2. **Resolution-field/action naming** — three different names proposed for
   the same settled mechanism (D10/D11); an editorial call, not a
   substantive gap — canonicalized here as `resolution_disposition` /
   `action_resolve_mutation_attempt`, flagged for deliberate control-room
   ratification.
3. **`attempt_id` regeneration-per-attempt vs. cross-retry tracking** — one
   root cause behind three separately-raised "unresolved question" markers
   (D6, D17, D14); resolving `attempt_id`'s scope (a single control-room
   decision) would close all three at once. The N=3 cap's persistence scope
   (D17) is the sharpest unresolved instance.
4. **`running_since` vs. `started_at`** — caught by only one review cluster;
   the cluster that designed the commit protocol (D19) never named the
   staleness-clock field the sweep (D26) actually depends on. Resolved at
   D1 (dedicated `running_since` field); recorded as evidence the
   underlying clusters needed a joint read before Stage 0, not just a union
   of outputs — this consolidation record **is** that joint read.
5. **Reconciliation-verdict evidence priority** (idempotency-key replay vs.
   quantity read) — raised by the transaction-protocol review, squarely
   inside the reconciliation-framework review's domain, never connected.
   Orphaned; carried to Part 5 below (D24's unresolved question).
6. **Batching (K/L vs. 33)** — the two clusters that examined it converge
   cleanly (exclude it, D4); the actual gap is between that converged
   conclusion and the Wave 3 DoR's own still-hedging text ("batching...
   where adopted"), corrected in this session's DoR update.
7. **`preconditions_snapshot` shape: fixed vs. general-allowlist framing** —
   not a true contradiction; resolved at D7 by adopting the general,
   per-domain-declared-allowlist framing with the inventory domain's
   concrete shape as one instance of it.
8. **`manual_review_subreason` new values** — four different new values
   proposed independently across three review areas
   (`no_reconciliation_strategy` D16, an unnamed "store disconnected
   mid-attempt" value D28/D29, `store_identity_mismatch` D18, plus reuse of
   existing `duplicate_risk` D17) never assembled into one consolidated
   diff before this record — this is the first place all four appear
   together; the control room should treat this list as the single source
   for that field's extension.
9. **Two pre-existing, overlapping `blocked_manual_review→queued`
   mechanisms** (`action_resolve_manual_review`, `action_manual_retry`)
   never reconciled with D11's new third mechanism — genuinely unresolved,
   carried to Part 5 below.
10. **AST-tooling-maturity contradiction** — whether repo-wide
    `ast.parse`/`ast.walk` infrastructure already exists is asserted both
    ways within this session's own grounding material; affects D37's
    effort-sizing directly; resolvable by direct inspection, not yet
    resolved.

---

## 5. Genuinely unresolved / blocking items after this consolidation

These could **not** be forced to a false resolution — each requires either
a control-room/product-owner decision not inferable from precedent, or
direct empirical/environmental verification not available from
documentation alone.

1. `mutation_attempt.job_id` field type (§4 item 1) — **BLOCKING (D20)**.
2. C2 cursor placement (main vs. side cursor) — **BLOCKING (D20)**.
3. Open-transaction-spans-network-call proof — **BLOCKING (D22)**.
4. Disconnect-quiescence/sweep-timeout interaction — **BLOCKING (D28)**,
   explicit control-room choice between remediation (a) and (b).
5. `mutation_domain` field ownership — **BLOCKING (D35)**, explicit
   control-room choice between option (a) and (b).
6. Reconciliation-strategy registry's owning model — never named in the
   original design; must be fixed before D15 can be implemented.
7. N=3 inconclusive-cap persistence scope — **BLOCKING (D17)**, product-owner
   safety-property decision.
8. Whether Shopify's THROTTLED response ever has a genuine server-side
   execution effect — factually open; the conservative `uncertain`
   classification (D9) is safe to *ship* without resolving this, but the
   fact itself remains open.
9. Two pre-existing, overlapping `blocked_manual_review→queued` mechanisms
   never reconciled with D11's new third mechanism.
10. Reconciliation-verdict evidence priority (idempotency-key-replay read
    vs. independent quantity read) — orphaned between review areas (D24).
11. Whether Shopify's `UserError` shape carries a per-entry field-path
    index sufficient for any future batching design — blocking only for
    *future* batching work, not for Stage 0/1 (D4 excludes batching
    entirely).
12. AST-tooling-maturity contradiction — resolvable by direct inspection,
    not yet resolved; blocks D37's effort-sizing.
13. Genuine OS-process-level crash-injection feasibility on the target
    Odoo.sh hosting environment — entirely unestablished; **BLOCKING (D38)**,
    invokes Wave-3-DoR hard-stop 6/10 if infeasible.
14. Literal field name for job→store linkage on `shopify.connector.job` —
    never confirmed by direct quote; blocks D3's `related=` field until
    verified against the actual field list.
15. Sweep cadence/timeout exact numeric values — empirical-measurement gap,
    not a design gap (D27).
16. Local idempotency-key safety margin (23h vs. Shopify's confirmed 24h) —
    this session's own Recommendation, zero source support for the
    specific margin value; needs explicit control-room ratification (D6).
17. `resolution_disposition`/`action_resolve_mutation_attempt` naming — not
    a substantive ambiguity, needs deliberate ratification (D10/D11).
18. **Out-of-scope document corrections** (not this session's to fix, but
    blocking before Stage 1 begins): `inventory-operating-model.md` §4.4
    and `task-013-inventory-sync-implementation-packet.md`'s CAS-heading
    text still reference `compareQuantity` as primary and must be corrected
    to `changeFromQuantity` in a session with those files in its allowed
    list, before the locked Stage 1 prompt (not this session's Stage 0
    prompt) can be issued.

---

## 6. Acceptance authority and status

Acceptance authority for every decision above: **product owner + Claude
control room**, exactly as DEC-031's Layer 2 registration already
specifies. **This record does not accept anything.** The control room's
possible dispositions, per this session's governing task: **ACCEPT**,
**ACCEPT WITH CORRECTIONS**, **REVISE**, **REJECT**.

Given the number of genuinely blocking items in §5 above (eight items
marked **BLOCKING** at the individual-decision level: D17, D20, D22, D28,
D35, D37, D38, plus the cross-cutting D12 implementation-prerequisite and
the out-of-scope document corrections), this session's own assessment —
offered as a Recommendation, not a self-acceptance — is that the package is
well-suited to **ACCEPT WITH CORRECTIONS** treatment for the *non-blocking*
majority of decisions (D1–D11, D13–D16, D18–D19, D21, D23–D27, D29–D34,
D36), with the **BLOCKING** items requiring explicit control-room decisions
before Stage 0 implementation of the affected pieces may begin. This
recommendation is not binding and is subject to the control room's own
independent judgment, including whatever Session C's code/architecture
audit surfaces that this session could not see.
