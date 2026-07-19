# DEC-037 — Wave 3 Gate B: Task 013/013B Inventory Readiness

- **Status: ACCEPTED — CONTROL-ROOM GATE B (Revision 3; accepted in
  substance, with a mandatory docs-only merge-closure normalization
  applied 2026-07-19).** Originally produced 2026-07-19 by the Gate B
  planning session (this session), based on `mvp/program-integration` @
  `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9` (PR #177 merge commit).
  Revision 1 was returned **REVISE, NOT REJECTED** (comment
  [`5015619162`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5015619162)).
  Revision 2 applied those six corrections and was itself returned
  **REVISE** a second time (comment
  [`5015830229`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5015830229)),
  which found the same-job CAS-redispatch mechanism still conflicted
  with Gate A's one-job/one-attempt rule, required an explicit atomic
  handoff contract, required the blocked-review release path to be
  frozen, required the invented error-vocabulary values withdrawn,
  corrected the `applied` reconciliation verdict, corrected the locked
  prompts' role model, and required explicit Stage 0 prerequisites.
  Revision 3 applied every one of those seven binding corrections and was
  **ACCEPTED IN SUBSTANCE** by comment
  [`5016117207`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5016117207)
  — conditioned on one further docs-only merge-closure normalization
  commit, applied here (§1C): the attempt-outcome/job-state distinction
  (`failed_clean`/`uncertain`/`applied`/`not_applied` are never job
  states), the predecessor-replacement transition (the existing terminal
  state `cancelled`, never a new state), correct existing-vs-new
  job-lineage field ownership, and the `blocked_manual_review`/
  review-release wording. **Claude did not accept its own package** in
  Revision 1, Revision 2, or Revision 3, and did not self-accept this
  normalization — acceptance authority is comment `5016117207`, product
  owner + ChatGPT control room, exactly as DEC-036.
- **Decision owner (candidate author, not acceptor):** Claude, the Gate B
  planning/contradiction-resolution/documentation worker, per this
  session's governing tasks and CLAUDE.md §13. Sol/"GPT-5.6 Sol" is the
  Task 013/013B implementation worker (not yet issued a prompt — see
  [`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md)
  and
  [`../06-prompts/sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md),
  both LOCKED, unissued). **Role model (comment `5015830229` binding
  correction 6):** ChatGPT is the strategic control room and acceptance
  authority; Claude is the planner, independent reviewer, and Odoo.sh
  runtime verifier; Sol is the implementation worker. Claude is not the
  control room, not the sole acceptance authority, and may perform a
  controlled merge only after explicit ChatGPT authorization.
- **Scope:** closes every remaining inventory-planning contradiction named
  by DEC-036 Part 0.5 ("Gate B / Task 013 corrections carried forward")
  and Part 5 item 11 ("Out-of-scope document corrections"), the
  contradictions this session found in Revision 1 by direct inspection of
  the Task 013/013B packets and the inventory operating model, the six
  binding corrections in comment `5015619162` (Revision 2), the seven
  binding corrections in comment `5015830229` (Revision 3), and — closing
  this record's acceptance — the eleven merge-closure normalization
  corrections in comment `5016117207` (§1C).
  This record does **not** reopen any DEC-036 decision (D1–D38) and does
  **not** reopen Gate A — it propagates those decisions, unchanged, into
  the inventory domain's own documents, and settles the domain-specific
  questions DEC-036 explicitly left to a Gate B session (mutation-domain
  matrix rows, job-contract vocabulary, activation sequencing).
- **Relationship to DEC-036:** DEC-036 is the generic Layer 2 substrate
  decision (Stage 0). This record is the domain-specific application of
  that substrate to the two Shopify mutations Task 013 issues
  (`inventorySetQuantities`, `inventoryActivate`) and the explicit
  non-application of Layer 2 to Task 013B. Where this record and DEC-036
  overlap, DEC-036 governs the substrate mechanism and this record governs
  the domain's use of it — they must never be read as alternatives. §13A
  (new, Revision 3) records where this domain's design now depends on a
  Stage 0 correction that has not yet landed.
- **Evidence base:** unchanged from Revision 1/2 (direct inspection of
  DEC-036 full text, the accepted Layer 2 design doc, the Wave 3 DoR, the
  Task 013/013B packets, the inventory operating model, the
  reconnect/backfill policy, the reconnect UAT matrix, the MVP acceptance
  matrix, the Stage 0 packet, the locked Stage 0 Sol prompt, the two
  narrow official-source verifications performed in Revisions 1–2, §2).
  **No new official-source fetch was performed in Revision 3** — every
  correction in comment `5015830229` is a job-model/vocabulary/role
  correction to this record's own design, not a new external fact.

---

## 1. Contradiction inventory and disposition (Pass 1, Revision 1)

Every contradiction found between the accepted DEC-036 Layer 2 substrate
and the pre-existing inventory-domain documents, with its binding
resolution. Rows C1–C7 and C9–C13 are unchanged from Revision 1. C8 was
corrected in Revision 2 (see its strikethrough below). **C14 is new in
Revision 3.**

| # | Original document / section | Conflicting document / section | Binding resolution | Corrected document | Test/implementation implication |
|---|---|---|---|---|---|
| C1 | `inventory-operating-model.md` §4.4 heading "compareQuantity CAS" and body, citing `compareQuantity`/`ignoreCompareQuantity` as the live field | DEC-036 D12 (fact: `changeFromQuantity` is the only current CAS field, 2026-04+) | `changeFromQuantity` is the sole current-facing CAS field name everywhere in this document set; the "evidence-conflict" framing is retired — Gate A's capture already resolved it as a Fact, not an open conflict | `inventory-operating-model.md` §4.4 | Static test: no `addons/shopify_connector_inventory/**` file references `compareQuantity`/`ignoreCompareQuantity` |
| C2 | `task-013-inventory-sync-implementation-packet.md`'s §"CAS via `compareQuantity`" addendum heading | DEC-036 D12; DEC-036 Part 5 item 11 | Heading and rationale corrected to `changeFromQuantity`; the 2026-07-16 "evidence conflict" framing removed (resolved, not open) | `task-013-inventory-sync-implementation-packet.md` §A.2 | Same static test as C1 |
| C3 | `inventory-operating-model.md` §4.3/§9 batching text | DEC-036 D4 (one pair per request, no `quantities[]` batching in Wave 3 MVP) | One-pair-per-request only for Wave 3 MVP; batching text rewritten as explicitly out of scope | `inventory-operating-model.md` §4.3/§9 | Static/AST test: no call site constructs a `quantities[]` array with length > 1 |
| C4 | `inventory-operating-model.md` §10 ("Partial failures") describing per-entry `userErrors` batch routing | DEC-036 D4 (no batching) | Rewritten for one-pair-per-request | `inventory-operating-model.md` §10 | Removes a batching-shaped test expectation |
| C5 | Task 013 packet D-013-1(b)/D-013-3: `last_push_idempotency_key`/`last_push_params_hash` on the binding row | DEC-036 D6 (idempotency key attempt-owned, never binding-owned) | Both fields removed from the binding schema; the key and both fingerprints live exclusively on `shopify.connector.mutation.attempt` | `task-013-inventory-sync-implementation-packet.md` D-013-1(b)/D-013-3/D-013-9 | Test: no code path reads `last_pushed_available`/`last_pushed_at` to decide idempotency-key reuse or retry eligibility |
| C6 | Task 013 packet D-013-6: unexplained Shopify-side drift "pushed over only after being logged" | DEC-036 Part 0.5 item 3 (review-case-first, no automatic overwrite) | Unexplained drift creates a review case and blocks the pending push until reviewed | `task-013-inventory-sync-implementation-packet.md` D-013-6/D-013-9; `inventory-operating-model.md` §5 | Test: induced unexplained-drift fixture asserts a review case is created and the pending push does not execute until cleared |
| C7 | Task 013 packet D-013-3: CAS-stale routes to `concurrency_race_conflict` with no explicit retry bound | Task master prompt §9.A; inventory-operating-model.md §4.4 proposed bounded retries (3) | Bounded retry count = 3 replacement jobs (Revision 3: each a **new** job, §5.4); after 3 replacements (the 4th mismatch) → `blocked_manual_review`/`binding_conflict` | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-9 | Test: 3-strikes CAS-stale fixture asserts review-case routing on the 4th mismatch, each strike a distinct job record |
| C8 | Task 013 packet D-013-3: `inventoryActivate` invoked inline inside the same handler/attempt as the `inventorySetQuantities` retry, with no explicit Layer 2 wrapper, no explicit second attempt/idempotency key | DEC-036 Hard Rule 1/D16/D37 (every Shopify mutation call site must be inside the Layer 2 wrapper); Gate A binding: one mutation job : one Shopify mutation request : one attempt row | ~~`inventoryActivate` is its own mutation domain, its own attempt, own idempotency key, own fingerprints — never combined with the `inventorySetQuantities` attempt, but both run as two sequential attempts inside the same `inventory_push_sync` job (Revision 1 §5).~~ **Superseded, Revision 2 (comment `5015619162` binding correction 1/2):** `inventory_activate` and `inventory_set_quantities` are each their **own separate mutation job type** (`job_type == mutation_domain` for each), never two attempts inside one job; `inventory_push_sync` is demoted to an orchestration/read-only job that enqueues at most one mutation job per dispatch. Full job model in §5 below | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-6/D-013-9 (rewritten, Revision 2/3); matrix rows, §4 below | Test: activation and set-quantities are asserted to be two distinct **jobs** (distinct `job_type`, distinct job IDs), each with its own single `attempt_token`/idempotency-key value — never one job executing two mutations |
| C9 | `wave-3-definition-of-ready.md` §5 item 3 flags §4.4 as needing correction "in a future Gate B session" | This session (Gate B) | Flag closed — corrected in Revision 1 | `wave-3-definition-of-ready.md` §5 | N/A — status update only |
| C10 | No document defined the exact `manual_review_subreason` values this domain adds, nor the exact pair-serialization convention | DEC-036 D18/D28/D6/D17 (generic subreasons); D14 (generic `operation_scope_key` convention) | Domain vocabulary frozen — §7; pair-serialization identity frozen — §6 (Revision 2 renames/re-derives the exact key literal per comment `5015619162` §5) | `task-013-inventory-sync-implementation-packet.md` D-013-9; locked Task 013 prompt | Test: job-contract vocabulary test enumerated in §7 |
| C11 | Task 013B packet did not explicitly state its own Layer-2-non-applicability | This session's governing task | Explicit statement added to the Task 013B packet itself | `task-013b-initial-inventory-baseline-packet.md` (§0) | N/A — documentation completeness |
| C12 | `reconnect-catchup-backfill-policy.md` §4.4 (Inventory): "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-catchup-backfill-policy.md` §4.4 | Same static test as C1 |
| C13 | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6: "pushes resume only with fresh `compareQuantity` bases" | DEC-036 D12 | `changeFromQuantity` | `reconnect-backfill-uat-matrix.md` UAT-RB-2.6 | Same static test as C1 |
| C14 | DEC-037 §4 row 1 (Revision 2): a `CHANGE_FROM_QUANTITY_STALE`/reconciliation-`not_applied` retry described as "a new job dispatch of this same job... the job is not re-created, it is redispatched" — i.e. one job accumulating multiple `mutation.attempt` rows over its lifetime | Gate A D4; control-room ruling (comment `5015830229` binding correction 1): one mutation job → one Shopify mutation request → one `mutation.attempt` row, **for that job's entire lifetime** — Revision 2's same-job redispatch design still violated this | ~~Every retry is a new job dispatch of this same job (Revision 2 §4 row 1/§5.1).~~ **Superseded, Revision 3 (comment `5015830229` binding correction 1):** every CAS-stale retry and every reconciliation `not_applied` retry creates a **new**, separate mutation job of the same domain — the old job's attempt keeps its `failed_clean`/resolved-`not_applied` outcome unchanged while the **job itself** transitions to the existing terminal state `cancelled`, and is never redispatched. The new domain-owned `cas_retry_ordinal` field, plus the existing core `superseded_by_job_id`/`cancel_reason` fields (reused, not new), track the replacement chain (§5.1, §5.4) | `task-013-inventory-sync-implementation-packet.md` D-013-3/D-013-9 (rewritten, Revision 3); DEC-037 §4 rows 1–2, §5.4, §9 | Test: a CAS-stale/`not_applied` fixture asserts a **new job record** (new job ID, new `attempt_token`, new idempotency key) is created for each replacement — never a second attempt on the same job ID |

No contradiction above disappears without the recorded resolution in its
row; every corrected document is listed in this session's governing
task's allowed-files list and was in scope to fix.

---

## 1A. Revision 2 — control-room binding corrections (Pass 3, closes review round 1)

Six binding corrections from comment `5015619162`, each with disposition
in Revision 2. None of these reopen Gate A or DEC-036; all are
corrections to this record's own Revision 1 domain-specific design.

| # | Binding correction (comment `5015619162`) | Disposition in Revision 2 |
|---|---|---|
| 1 | One mutation job means one mutation only — `inventoryActivate`/`inventorySetQuantities` must be two separate mutation jobs, not two attempts inside `inventory_push_sync` | Applied. New job model, §5. `inventory_push_sync` demoted to orchestration/read-only; `inventory_activate` and `inventory_set_quantities` are each a standalone mutation job type |
| 2 | Exact Stage 0 compatibility — mutation job types must be exactly `inventory_activate`/`inventory_set_quantities`, `job_type == mutation_domain`, `inventory_push_sync` kept outside the mutation registry | Applied. §4 (matrix), §5 (job model), §7 (job contract) |
| 3 | No message-string idempotency classification for `inventoryActivate` | Applied. §4 row 2 no longer proposes message-matching as a production classification path; removed entirely, replaced with a uniform payload-shape rule (§4 row 2, §9) |
| 4 | Safe reconciliation verdicts — freshness/ABA protection for `inventory_set_quantities` `not_applied`; explicit three-way verdict for `inventory_activate` | Applied. §4 rows 1 and 2, reconciliation-verdict cells rewritten (the `applied` cell is further corrected in Revision 3, §1B item 5) |
| 5 | Job consequences must be explicit for every direct clean failure | Applied. New §9, job/mutation-consequence contract (rewritten again in Revision 3 for the fixed vocabulary and the new-job replacement model) |
| 6 | Factual Stage 0 status — PR #178 exists, open/draft, at the stated head; correct stale "no PR" wording | Applied. New §13; every stale "no PR yet" statement in this record and the shared trackers is corrected |

---

## 1B. Revision 3 — control-room binding corrections (Pass 4, closes review round 2)

Seven binding corrections from comment `5015830229`, each with
disposition in this revision. None of these reopen Gate A or DEC-036;
all are corrections to this record's own Revision 2 domain-specific
design.

| # | Binding correction (comment `5015830229`) | Disposition in Revision 3 |
|---|---|---|
| 1 | One mutation job must own exactly one attempt for its entire lifetime — every CAS retry and every reconciliation `not_applied` retry must create a **new** same-domain job, never redispatch the same job | Applied. §1 row C14, §4 rows 1–2, §5.1, §5.4, §9 — new job-lineage fields `cas_retry_ordinal` (0→1→2→3), `superseded_by_job_id`, `cancel_reason` |
| 2 | Freeze exact atomic handoffs under a row lock on the binding — four named transactions; no new core job state; no waiting for an unrelated future scan/manual trigger after successful activation | Applied. §5.2 step 7 rewritten (atomic, immediate, same transaction as the activation job's own terminalization); new §5.4, the full atomic handoff contract (handoffs A–D) |
| 3 | Freeze the review-release path — `blocked_manual_review` is not terminal; define `action_recheck_inventory_pair(reason)` with an exact, narrow contract | Applied. New §5.5 |
| 4 | Use the existing fixed error vocabulary; remove the invented values `remote_validation_rejected`/`remote_precondition_mismatch`/`transport_ambiguous`/`clean_rejection` | Applied. §4 rows 1–2, §7, §9 — every `error_class` value in this record is now one of: `shopify_user_errors_validation`, `inventory_location_missing`, `concurrency_race_conflict`, `shopify_throttling_rate_limit`, `shopify_temporary_server_network`, `data_shape_schema_mismatch`, `idempotency_contract_violation`, `no_reconciliation_strategy`, `store_identity_mismatch` |
| 5 | Correct the `inventory_set_quantities` applied reconciliation verdict — do not require `updatedAt <= transport_at` for `applied`; use freshness only to protect `not_applied` | Applied. §4 row 1 `applied`-verdict cell — the erroneous timestamp condition is removed |
| 6 | Correct the locked-prompt role model — ChatGPT = control room/acceptance authority; Claude = planner/independent reviewer/Odoo.sh runtime verifier; Sol = implementation worker; remove wording calling Claude the control room or sole merge authority | Applied. Both locked Sol prompts corrected (ROLE sections); this record's own header/decision-owner text corrected to match |
| 7 | Record exact Stage 0 (PR #178) correction prerequisites for Task 013 issuance | Applied. New §13A |

---

## 1C. Acceptance normalization — control-room final decision (Pass 5, closes acceptance comment `5016117207`)

Comment
[`5016117207`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5016117207)
**accepted Revision 3 in substance** — the separate orchestration/
activation/set-quantities job model, one mutation job/one attempt for the
job's entire lifetime, replacement-job retries, atomic handoffs, the
fixed error vocabulary, freshness-safe reconciliation, explicit Stage 0
prerequisites, and the current role model — conditioned on eleven
docs-only merge-closure normalization corrections, applied in this pass.
None of these reopen Gate A, DEC-036, or any substantive Revision 3
design decision; all are wording/consistency corrections closing residual
contradictions the acceptance review found in this record's own text.

| # | Binding correction (comment `5016117207`) | Disposition |
|---|---|---|
| 1 | Attempt outcome is not a job state — `failed_clean`/`uncertain`/`applied`/`not_applied` must never appear as `shopify.connector.job.state` values or as "terminal job states"; existing terminal states remain `succeeded`, `failed_final`, `skipped`, `cancelled` | Applied. §5.3 handoff rule, §5.4 intro, §9 table rows corrected to attribute these values only to `mutation.attempt`'s `observed_outcome`/`resolution_disposition` |
| 2 | Replacement predecessor state is the existing terminal state `cancelled`, preserving attempt outcome/resolution; set `superseded_by_job_id`/`cancel_reason`, flush the scope key, then create the child in the same transaction | Applied. §4 rows 1–2, §5.4 handoffs C/D, §9 table |
| 3 | Successful phase handoffs (A, B) use `succeeded`; log both job IDs; never set `superseded_by_job_id`/`cancel_reason` on a successful handoff | Applied. §5.4 job-lineage-fields paragraph corrected — Revision 3's text incorrectly listed handoff B among the superseding handoffs; it is a successful completion, not a replacement, and now reads accordingly |
| 4 | `superseded_by_job_id`/`cancel_reason` are existing core fields, reused, not new domain schema; the only new domain-owned field is `cas_retry_ordinal` | Applied. §5.4, §7 job-lineage-fields text corrected throughout |
| 5 | `blocked_manual_review` remains non-terminal; removed from every terminal-state list and every automatic-handoff rule | Applied. §5.3, §5.4, §9 table, §4 rows 1–2 |
| 6 | No automatic post-review orchestration — `ITEM_NOT_STOCKED_AT_LOCATION` and ordinary clean-validation rejections stay blocked until `action_recheck_inventory_pair` releases them; no scan/manual trigger admits a new job while blocked | Applied. §4 row 1, §5.2 step 8, §9 table — the erroneous "admitted normally by scan/manual trigger" wording is removed |
| 7 | Exact review-release public owner: `shopify.connector.inventory.level.binding.action_recheck_inventory_pair(reason)`, may delegate to a private service helper | Already correct in §5.5/§7 — no change needed beyond the effective-disposition wording in item 8 |
| 8 | Effective-disposition check: `observed_outcome='failed_clean'` and `effective_disposition() == 'not_applied'`, not raw `resolution_disposition='not_applied'` | Applied. §5.5 |
| 9 | Review-release transition: `blocked_manual_review` → `cancelled`, `cancel_reason='manual_review_release'`, `superseded_by_job_id` set, scope key cleared, exactly one fresh `inventory_push_sync` job created atomically | Already correct in substance in §5.5; wording tightened to name the `cancelled` transition explicitly |
| 10 | `store_identity_mismatch` remains the accepted manual-review route Stage 0 must add/prove — not an already-existing current core error class unless Stage 0 actually adds it | Already correct — §7/§13A already state this as a Stage 0 correction prerequisite; no change needed |
| 11 | Apply consistently to DEC-037, Task 013 packet, locked Task 013 prompt, dev-store plan, acceptance matrix/DoR/program state/handoff/log wherever current-facing | Applied — see each document's own change for this pass |

---

## 2. Official-source verification performed this session

Per this session's governing tasks, the accepted Gate A capture
(`shopify-layer2-mutation-safety-refresh-2026-07-18.md`) is the default
source basis and was **not** re-fetched for facts it already establishes
(CAS field name, `@idempotent` mandatory scope/timing, THROTTLED
non-guarantee, `InventoryLevel.quantities` shape, Odoo 19 isolation
level, the CAS mismatch code `CHANGE_FROM_QUANTITY_STALE`, the two
idempotency-defect codes' message text). Three narrow gaps that capture
did not cover — each directly needed to complete a matrix cell without a
"TBD" — were verified live against `shopify.dev`, in Revisions 1–2:

1. **`inventoryActivate` default quantities** (Revision 1, 2026-07-19).
   Source: https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryactivate
   — Accessible. Quote: *"If you don't specify quantities, then
   `available` and `onHand` default to zero."* **[Fact.]**
2. **`inventoryActivate` error-reporting shape** (Revision 1, 2026-07-19).
   Source: https://shopify.dev/docs/api/admin-graphql/2026-07/objects/UserError
   — Accessible. `UserError` has exactly two fields, `field` and
   `message` — no `code` field, unlike
   `InventorySetQuantitiesUserErrorCode`. **[Fact.]**
3. **Complete `InventorySetQuantitiesUserErrorCode` enum** (Revision 2,
   2026-07-19, added because it is needed to correctly resolve binding
   correction 1's `ITEM_NOT_STOCKED_AT_LOCATION` handling and because
   Revision 1's matrix row 1 cited a partial list without capturing the
   full enum in this repository's own source materials — a citation gap
   this revision closes; no new source-materials file was created because
   this revision's allowed-files list authorizes no new file, so the full
   quote is captured directly in this decision record instead). Source:
   https://shopify.dev/docs/api/admin-graphql/2026-07/enums/InventorySetQuantitiesUserErrorCode
   — Accessible, 2026-07-19. All 17 values, in order: `CHANGE_FROM_QUANTITY_STALE`
   ("The changeFromQuantity value does not match persisted value."),
   `COMPARE_QUANTITY_REQUIRED` (legacy field, historical),
   `COMPARE_QUANTITY_STALE` (legacy field, historical),
   `IDEMPOTENCY_CONCURRENT_REQUEST` ("This request is currently in
   progress, please try again."), `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`
   ("The same idempotency key cannot be used with different operation
   parameters."), `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` ("A previous
   request with this idempotency key failed. Retry with a new idempotency
   key."), `INVALID_INVENTORY_ITEM` ("The specified inventory item could
   not be found."), `INVALID_LOCATION` ("The specified location could not
   be found."), `INVALID_NAME` ("The quantity name must be either
   'available' or 'on_hand'."), `INVALID_QUANTITY_NEGATIVE` ("The
   quantity can't be negative."), `INVALID_QUANTITY_TOO_HIGH` ("The total
   quantity can't be higher than 1,000,000,000."),
   `INVALID_QUANTITY_TOO_LOW` ("The total quantity can't be lower than
   -1,000,000,000."), `INVALID_REASON` ("The specified reason is
   invalid."), `INVALID_REFERENCE_DOCUMENT` ("The specified reference
   document is invalid."), **`ITEM_NOT_STOCKED_AT_LOCATION`** ("The
   specified inventory item is not stocked at the location."),
   `NO_DUPLICATE_INVENTORY_ITEM_ID_GROUP_ID_PAIR` ("The combination of
   inventoryItemId and locationId must be unique."),
   `NON_MUTABLE_INVENTORY_ITEM` ("The specified inventory item is not
   allowed to be adjusted via API. Example: if the inventory item is a
   parent bundle."). **[Fact.]** `ITEM_NOT_STOCKED_AT_LOCATION` exists and
   is folded into §4 row 1 and §9 per binding correction 1's exact
   handling rule (fail-closed to review/re-orchestration, never an inline
   activation trigger).

No other official-source re-verification was performed in Revisions 2 or
3 — Revision 3, like Revision 2, is a documentation-correction batch
responding to a control-room ruling, not another research round, per
this revision's governing task. Every Revision 3 correction (job-model
lifecycle, atomic handoffs, review-release action, error vocabulary,
reconciliation-verdict wording, role model, Stage 0 prerequisites) is a
correction to this record's own prior design, not a new claim about
Shopify's API surface.

---

## 3. Binding decisions propagated without reopening

The fourteen decisions from Revision 1's governing task §7 remain binding
and are propagated unchanged. Pointers to items 7 and 8 are updated to
this revision's rewritten job-model section.

| # | Decision | DEC-036 source | Applied in |
|---|---|---|---|
| 1 | CAS input field = `changeFromQuantity` | D12 | Task 013 D-013-3, §4 row 1 |
| 2 | CAS mismatch error = `CHANGE_FROM_QUANTITY_STALE` | D12 | Task 013 D-013-9, §4 row 1 |
| 3 | Idempotency: attempt-owned, request-level, persisted by Layer 2, not binding-owned | D6 | Task 013 D-013-1(b)/D-013-9 (C5) |
| 4 | Mutation granularity: one item+location pair, one request, one attempt, no batching | D4 | Task 013 D-013-6/D-013-9 (C3/C4) |
| 5 | Unexplained Shopify drift: review-case-first, no silent overwrite | Part 0.5 item 3 | Task 013 D-013-6 (C6) |
| 6 | Task 013 mutations all pass through Layer 2; no direct API-client mutation call | D16/D37, Hard Rule 1 | Task 013 D-013-9 (C8); locked Task 013 prompt |
| 7 | `inventorySetQuantities`: separate mutation-domain registration, own job type, own reconciliation strategy, mandatory Layer 2 wrapper, one attempt per job for its entire lifetime (Revision 3) | D15/D16 | §4 row 1, §5 |
| 8 | `inventoryActivate`: also a mutation, own job type, mandatory Layer 2 wrapper, own reconciliation strategy, one attempt per job for its entire lifetime (Revision 3) | D16/D37 | §4 row 2, §5 |
| 9 | Task 013B: no Layer 2, Shopify reads, guarded local Odoo writes, no mutation, separate Stage 2 | Part 0.5 item 5; Stage 0 packet §2 | §8; Task 013B packet §0 |
| 10 | Reconnect: reconciliation read before first post-reconnect push, never blind | inventory-operating-model.md §11; reconnect policy §4.4 | §12 |
| 11 | Standing direction: Odoo authoritative after onboarding, no standing Shopify→Odoo stock sync | DEC-010 (unchanged) | §11/§12 |
| 12 | Shopify quantity writes: `available` only, never `committed`, never `on_hand` | DEC-010/RA-018 (unchanged) | §11; `inventoryActivate` row never sends `onHand` as nonzero |
| 13 | Negative quantity: clamp to zero, log/review evidence, never send negative `available` | inventory-operating-model.md §7 (unchanged) | §11 |
| 14 | First push: preview, explicit confirmation, recorded actor/time/quantity, no unconfirmed mutation | Task 013 D-013-4 (unchanged); tightened by §6 | Task 013 D-013-4/D-013-9 |

---

## 4. Complete Layer 2 inventory mutation-domain matrix

Two rows — `inventory_set_quantities` and `inventory_activate` — each a
**standalone mutation job type**, per binding corrections 1 and 2
(Revision 2) and job-lifetime binding correction 1 (Revision 3). No cell
says "implementation choice," "TBD," or equivalent.

### Row 1 — `inventory_set_quantities`

| Field | Value |
|---|---|
| `job_type` | **`inventory_set_quantities`** (Revision 2 — was `inventory_push_sync` in Revision 1; corrected per binding correction 2: `job_type == mutation_domain` for every mutation job) |
| `mutation_domain` | `inventory_set_quantities` |
| Replay-policy class | `remote_effect_not_replay_safe` (every Shopify mutation is this class by construction) |
| Reconciliation-strategy registry key | `inventory_set_quantities`, registered via `_inherit`+`super()` on `shopify_connector_job_dispatch.py`'s `_get_reconciliation_strategies()` seam (DEC-036 D15) |
| Domain-enable flag | `inventory_domain_enabled` |
| Pair-serialization identity | `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}` (frozen literal, §5.3 — shared with the `inventory_push_sync` orchestration job and the `inventory_activate` job for the same pair; this is what `operation_scope_key` is set to for this job type) |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_set_quantities', inventory_item_id, location_id, target_quantity}` — excludes `changeFromQuantity` and the idempotency key (DEC-036 D5) |
| Exact-request fingerprint inputs | Normalized `inventorySetQuantities` GraphQL document + exact variables: `name: 'available'`, `reason`, `referenceDocumentUri`, one `InventoryQuantityInput` entry `{inventoryItemId, locationId, quantity, changeFromQuantity}`, plus the `@idempotent(key: ...)` directive value (DEC-036 D5) |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, target_quantity, change_from_quantity, snapshot_taken_at}` (DEC-036 D7) |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventorySetQuantities'}` |
| `remote_evidence_refs` allowlist | `{remote_gids: [...], user_errors: [{code, field}], http_status, graphql_error_codes: [...], throttle_status: {maximumAvailable, currentlyAvailable, restoreRate} \| null}` (DEC-036 D8) |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 per attempt, persisted on `mutation.attempt` at C2 (never on the binding, C5); reused verbatim only for an identical `exact_request_fingerprint` retry within `idempotency_valid_until` (24h minus a configurable local safety margin, provisional 23h) |
| Expected connection generation / store identity | Snapshotted at C2 on the attempt row (DEC-036 D18/D29); reconciliation begins with the store-identity check |
| Job-lineage field — **`cas_retry_ordinal`** (Revision 3, replaces Revision 2's `cas_mismatch_count`; closes binding correction 1) | Integer, default 0. Identifies this job's generation number in a bounded CAS-replacement chain for one pair: `0` = the original job; `1`/`2`/`3` = the first/second/third **replacement** job (a distinct job record, never the same job redispatched). Checked once, at job creation, against the ordinal of the job it replaces (`ordinal = predecessor.cas_retry_ordinal + 1`); never incremented mid-job, because a job created at a given ordinal makes **at most one** mutation attempt for its entire lifetime |
| Direct `succeeded` evidence | Response has no `userErrors` and the mutation's own returned quantity data reflects the requested `quantity` → `observed_outcome='succeeded'` |
| Direct `failed_clean` evidence — validation/binding codes | `userErrors` containing one of: `INVALID_INVENTORY_ITEM`, `INVALID_LOCATION`, `INVALID_NAME`, `INVALID_QUANTITY_TOO_HIGH`, `INVALID_QUANTITY_TOO_LOW`, `INVALID_REASON`, `INVALID_REFERENCE_DOCUMENT`, `NO_DUPLICATE_INVENTORY_ITEM_ID_GROUP_ID_PAIR`, `NON_MUTABLE_INVENTORY_ITEM` (all confirmed live on `InventorySetQuantitiesUserErrorCode`, §2 item 3) → `observed_outcome='failed_clean'`, **`error_class='shopify_user_errors_validation'`** (Revision 3 — replaces the invented `remote_validation_rejected`), `manual_review_subreason='binding_conflict'`. `INVALID_QUANTITY_NEGATIVE` is confirmed-existing but never-triggerable under this connector's clamp-before-send discipline — a defensive test asserts it is never observed. No blind automatic retry for any of these (§9) |
| Direct `failed_clean` evidence — CAS stale | `CHANGE_FROM_QUANTITY_STALE` → `observed_outcome='failed_clean'`, `error_class='concurrency_race_conflict'`. Bounded retry **permitted**, maximum **3** replacement jobs (`cas_retry_ordinal < 3` on the job that just failed). **Revision 3 correction (binding correction 1, replaces Revision 2's same-job-redispatch design entirely): every retry creates a NEW job, never a redispatch of the job that failed.** This failing job's own single attempt keeps `observed_outcome='failed_clean'` unchanged; the **job itself** transitions to the existing core job state `cancelled` (never a new state) — `superseded_by_job_id` set to the new job, `cancel_reason='cas_stale_bounded_replacement'` (§5.4 handoff C); a new `inventory_set_quantities` job is created with `cas_retry_ordinal` incremented by one, its own fresh `mutation.attempt` row, a fresh, narrow, single-purpose Shopify read of the pair's current `available`/`updatedAt` (a `remote_read_replay_safe` read performed by the new job's own dispatch handler, not a re-run of full `inventory_push_sync` orchestration — this is a CAS pre-read, not a reconnect/drift classification, and does not re-derive the target or re-run first-push/drift/reconnect gates), a fresh `changeFromQuantity`, a fresh exact-request fingerprint, and a fresh idempotency key. The new job also re-reads the binding's current coalesced `pending_target_available` (§10) rather than resending a possibly-stale target. After 3 replacements (the 4th `CHANGE_FROM_QUANTITY_STALE`, on the job at `cas_retry_ordinal=3`) → no further replacement job is created; that job instead transitions to the existing **non-terminal** `blocked_manual_review` state (`binding_conflict`), which continues to hold `operation_scope_key` until an authorized §5.5 release |
| Direct `failed_clean` evidence — `ITEM_NOT_STOCKED_AT_LOCATION` | **[Fact, §2 item 3]** Confirmed on `InventorySetQuantitiesUserErrorCode`. This is a race/contract exception, not an inline activation trigger — `inventory_push_sync`'s own prior read found (or believed it found) an existing level, but the level was not actually stocked at send time. → `observed_outcome='failed_clean'`, **`error_class='inventory_location_missing'`** (Revision 3 — replaces the invented `remote_precondition_mismatch`; the same value is also the `manual_review_subreason`), routes the job to the existing **non-terminal** `blocked_manual_review` state (`inventory_location_missing`) — which continues to hold the pair's `operation_scope_key` and blocks any new job of any of the three inventory job types for that pair until an authorized `action_recheck_inventory_pair` release (§5.5); **no scan or manual trigger admits a new orchestration job while the pair remains blocked**. This job **never** issues `inventoryActivate` inline or in any form. The pending target remains coalesced (§10) unresolved; only after that authorized release does the resulting fresh `inventory_push_sync` job re-read Shopify, correctly detect the level is genuinely absent, and — only if `first_push_state='confirmed'` — enqueue a fresh `inventory_activate` job |
| Direct `uncertain` evidence | Network timeout after send (`error_class='shopify_temporary_server_network'`); HTTP 5xx (same); `THROTTLED` (`error_class='shopify_throttling_rate_limit'`); ambiguous/partial `userErrors` (data + errors both present — does not apply cleanly to this mutation's error shape, retained for completeness; `error_class='data_shape_schema_mismatch'`); `IDEMPOTENCY_CONCURRENT_REQUEST` (`error_class='concurrency_race_conflict'`, Revision 3 — this structured code is a concurrency signal, not a generic transport-ambiguity one); worker crash between send and outcome commit (DEC-036 D9/D19/D23/D24) |
| `THROTTLED` handling | `uncertain`, `error_class='shopify_throttling_rate_limit'`, reconcile-first, never auto-classified `failed_clean` (DEC-036 D9) |
| Idempotency-error handling | `IDEMPOTENCY_CONCURRENT_REQUEST` → `uncertain`, `error_class='concurrency_race_conflict'`; `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` / `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → `error_class='idempotency_contract_violation'`, `manual_review_subreason='idempotency_contract_violation'`, `blocked_manual_review`, no automatic retry (DEC-036 D6). These are structured codes on this mutation's own error enum (§2 item 3) — no message-text matching is needed or used for this row |
| Reconciliation read | `InventoryLevel.quantities(names: ["available"])` for the exact pair, including `updatedAt` where the schema exposes it on the returned `InventoryQuantity`; **first** step is the store-identity check (DEC-036 D18) |
| `applied` verdict — **corrected, Revision 3, binding correction 5** | Current Shopify `available` equals this attempt's `target_quantity` → `resolution_disposition='applied'`; no resend. **Revision 2's additional condition — requiring `InventoryQuantity.updatedAt` not later than `transport_at` — is withdrawn**: the mutation's own successful update normally occurs *after* `transport_at`, so that condition would have made a genuinely successful attempt read as non-applied. `applied` is about the achieved business state, not attribution of which attempt produced it; freshness/`updatedAt` evidence is used **only** to protect the `not_applied` verdict below, never to gate `applied` |
| `not-applied` verdict — freshness/ABA-safe (Revision 2, binding correction 4; job-lineage mechanics corrected Revision 3) | Current Shopify `available` equals this attempt's own pre-attempt `changeFromQuantity` **and** freshness evidence does **not** show a post-transport change: i.e., `updatedAt`, where present, is **not later than** `transport_at`, and no other evidence (a differing `myshopifyDomain`, a third-party attribution signal) indicates an ABA round-trip or third-party write → `resolution_disposition='not_applied'`. **Revision 3 correction:** the **job itself** then transitions to the existing core job state `cancelled` — never redispatched, never given a new core state — with `superseded_by_job_id` set and `cancel_reason='reconciliation_not_applied_replacement'` (§5.4 handoff D); a **new** `inventory_set_quantities` job is created, which makes the next attempt through its own normal dispatch |
| Inconclusive verdict — freshness/ABA-safe (Revision 2) | Any of: (a) current `available` equals **neither** the pre- nor post-attempt value; (b) current `available` equals the pre-attempt value **but** `updatedAt` is **later** than `transport_at` (an ABA round-trip cannot be ruled out — the value could have changed away and back); (c) freshness evidence is unavailable and attribution to this attempt cannot otherwise be established. **No verdict may depend only on response absence, and a same-value read is never, by itself, treated as proof of not-applied** → `inconclusive_reconciliation_count` increments under a re-acquired row lock (DEC-036 D17); next reconciliation read scheduled |
| Manual-review subreason | `duplicate_risk` (N=3 inconclusive cap); `store_identity_mismatch`; `idempotency_contract_violation`; `binding_conflict` (`NON_MUTABLE_INVENTORY_ITEM`; persistent CAS divergence once all 3 bounded replacements are exhausted); `inventory_location_missing` (`ITEM_NOT_STOCKED_AT_LOCATION`); `no_reconciliation_strategy` (registry lookup failure, should never fire) |
| Retry eligibility | Per the effective-disposition helper (DEC-036 D10), see §9 for the full consequence table |
| First-push interaction | Never fires for a pair whose binding `first_push_state != 'confirmed'` — `destructive_write_guard_blocked`, unchanged |
| Reconnect interaction | Never admitted for a pair until that pair's post-reconnect `inventory_push_sync` reconciliation read has completed (§12) |
| Disconnect interaction | Per DEC-036 D28, unchanged |
| Rollback/disable behavior | Per DEC-036 D36, unchanged |
| Exact tests | `test_inventory_push_mechanics.py` (extended, Revision 3): CAS-stale bounded 3-replacement sequence (`cas_retry_ordinal` 0→1→2→3) is asserted to create **four distinct job records** (never a redispatch of any prior one), each with its own `attempt_token`/idempotency key, connected only by `superseded_by_job_id`; the 4th mismatch (at ordinal 3) creates no replacement and routes `blocked_manual_review`; `ITEM_NOT_STOCKED_AT_LOCATION` never triggers an inline `inventoryActivate` call in this job — asserted by a static/AST guard that this job's handler contains no `inventoryActivate` call site; `THROTTLED`→`uncertain`/`shopify_throttling_rate_limit`; both idempotency-defect codes → `idempotency_contract_violation`/`blocked_manual_review`/no-retry; reconciliation `applied` (no `updatedAt` condition)/`not_applied` (creates a new job, never redispatches)/`inconclusive` including an induced ABA fixture (value changes away and back with a later `updatedAt`) asserting `inconclusive`, never `not_applied`; store-identity-mismatch routing; first-push-confirmed gate; binding never stores a Shopify idempotency key or exact-request fingerprint; no `error_class` value outside the fixed vocabulary (§7) appears anywhere in the module |
| Exact dev-store evidence | Dev-store validation plan scenarios 1–8, 10–12, 17–19 (18 is the ABA/freshness scenario; 19 is the `ITEM_NOT_STOCKED_AT_LOCATION` race scenario; scenario 5 is corrected, Revision 3, to show a new job created per replacement) |

### Row 2 — `inventory_activate`

| Field | Value |
|---|---|
| `job_type` | **`inventory_activate`** (Revision 2 — was `inventory_push_sync` in Revision 1; corrected per binding correction 2) |
| `mutation_domain` | `inventory_activate` |
| Replay-policy class | `remote_effect_not_replay_safe` |
| Reconciliation-strategy registry key | `inventory_activate`, its own row, never folded into the set-quantities strategy |
| Domain-enable flag | `inventory_domain_enabled` |
| Pair-serialization identity | `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}` — same identity as row 1 and the orchestration job for this pair (§5.3); this job and the `inventory_set_quantities` job for the same pair are never both non-terminal at once (§5.3) |
| Business-intent fingerprint inputs | `{mutation_domain: 'inventory_activate', inventory_item_id, location_id, initial_available: 0}` |
| Exact-request fingerprint inputs | Normalized `inventoryActivate` GraphQL document + exact variables: `inventoryItemId`, `locationId`, **`available: 0`** (explicit, never omitted), `onHand` omitted (defaults to 0; never sent nonzero), `stockAtLegacyLocation: false` (explicit), plus this job's own `@idempotent(key: ...)` value, distinct from row 1's key |
| `preconditions_snapshot` allowlist | `{inventory_item_id, location_id, initial_available: 0, snapshot_taken_at}` |
| `remote_mutation_intent` allowlist | `{inventory_item_gid, location_gid, mutation_name: 'inventoryActivate'}` |
| `remote_evidence_refs` allowlist | Same D8 shape as row 1; `graphql_error_codes` empty in practice (no dedicated enum, §2 item 2) |
| Shopify idempotency-key lifecycle | Fresh UUIDv4 for this attempt, distinct from the `inventory_set_quantities` job's key; same 24h-minus-margin reuse rule |
| Expected connection generation / store identity | Snapshotted at this job's own attempt's C2, independently of any other job |
| Direct `succeeded` evidence | **[Fact, §2 item 1]** Response returns a non-null `inventoryLevel` and an empty `userErrors` array → `observed_outcome='succeeded'`. The level now exists at `available=0`/`on_hand=0` (this connector explicitly sends `available: 0` rather than relying on the omitted-argument default, so the sent value is always visible in `exact_request_fingerprint`) |
| Direct `failed_clean` evidence | **[Fact, §2 item 2]** `userErrors` is `[UserError!]!`; `UserError` has exactly `field`/`message` — no `code`. Classification is by **payload shape only**: a non-empty `userErrors` array **with a null `inventoryLevel`** → `observed_outcome='failed_clean'`, **`error_class='shopify_user_errors_validation'`** (Revision 3 — replaces the invented `clean_rejection`), `manual_review_subreason='binding_conflict'`, **never automatic retry** — this single rule covers every clean-rejection cause this mutation can report, including any idempotency-contract defect Shopify may express through this shape, without needing to distinguish the specific cause (no finer-grained routing is possible or claimed, since no structured code exists). `UserError.message` text **may be captured as redacted diagnostic evidence only** (e.g., in job logs, for human triage) and **must never be used to select an error class, a retry decision, or a manual-review subreason** — Revision 1's proposed case-insensitive message matching for idempotency-equivalent text is **withdrawn**. **No claim is made that a stable structured idempotency-defect surface exists for `inventoryActivate`** unless directly proven by a future official-source change; if Shopify later adds a dedicated error-code enum for this mutation, this row must be revisited under a further Gate decision, not silently patched |
| Direct `uncertain` evidence | Network timeout after send (`error_class='shopify_temporary_server_network'`); HTTP 5xx (same); `THROTTLED` (`error_class='shopify_throttling_rate_limit'`); **a non-empty `userErrors` array together with a non-null `inventoryLevel`** — ambiguous/partial, the payload shape itself (not message text) is the classification signal, `error_class='data_shape_schema_mismatch'` (Revision 3 — this ambiguous-partial shape is a data-shape signal, not a generic transport one); worker crash between send and outcome commit |
| `THROTTLED` handling | `uncertain`, `error_class='shopify_throttling_rate_limit'`, reconcile-first — identical policy to row 1 |
| Idempotency-error handling | Folded into the uniform clean-rejection rule above (`shopify_user_errors_validation`/`binding_conflict`); no separate handling, no message matching — there is nothing left to verify, since the uniform rule requires no cause-specific classification |
| Reconciliation read | `InventoryLevel.quantities(names: ["available", "on_hand"])` for the pair; same store-identity-first check as row 1 |
| `applied` verdict — explicit three-way (Revision 2, binding correction 4) | The level exists (non-null `InventoryLevel`) **and** `available == 0` **and** `on_hand == 0` → `resolution_disposition='applied'` |
| `not-applied` verdict — job-lineage mechanics corrected Revision 3 | The level still does not exist for the pair (query returns null/absent) → `resolution_disposition='not_applied'`. **Revision 3 correction:** the **job itself** then transitions to the existing core job state `cancelled` — never redispatched, never given a new core state — with `superseded_by_job_id` set and `cancel_reason='reconciliation_not_applied_replacement'` (§5.4 handoff D); a **new** `inventory_activate` job is created, which makes the next activation attempt through its own normal dispatch |
| Inconclusive verdict | The level exists but `available`/`on_hand` are **not both** 0 — an unexplained non-zero quantity reached the pair between this attempt and the read → `inconclusive_reconciliation_count` increments; **never auto-corrected** |
| Manual-review subreason | `duplicate_risk` (N=3 cap); `store_identity_mismatch`; `binding_conflict` (clean rejection; a nonzero level found during reconciliation) |
| Retry eligibility | Per the effective-disposition helper (DEC-036 D10), see §9 |
| First-push interaction | Enqueued **only** by a fresh `inventory_push_sync` orchestration dispatch (§5) that finds no existing Shopify level for a pair whose binding is `first_push_state='confirmed'` — **never** enqueued directly by an `inventory_set_quantities` job's own outcome: `ITEM_NOT_STOCKED_AT_LOCATION` is handled entirely within row 1 as a fail-closed review case, §4 row 1, §9 — it does not trigger this job |
| Reconnect interaction | Same admission gate as row 1 |
| Disconnect interaction | Same as row 1 |
| Rollback/disable behavior | Same as row 1 |
| Exact tests | New assertions in `test_inventory_push_mechanics.py`: activation always sends explicit `available: 0`; activation and a subsequent `inventory_set_quantities` job use two distinct job records, `job_type` values, `attempt_token`/idempotency-key values, and are connected only by the shared pair-serialization identity and a fresh, **atomic** orchestration handoff (§5.4 handoff B) — never a direct enqueue from one to the other; activation never sends `onHand` nonzero; reconciliation requires both `available`/`on_hand` zero for `applied`; a `not_applied` reconciliation creates a **new** `inventory_activate` job, never redispatches the resolved one; **no code path matches on `UserError.message` text for this mutation** (static/AST guard); a nonzero post-activation level routes to `binding_conflict`, never silently accepted; no `error_class` value outside the fixed vocabulary (§7) appears anywhere in the module |
| Exact dev-store evidence | Dev-store validation plan scenario 9 (activation, its own standalone job, Revision 2) |

No matrix cell above is "TBD" or "implementation choice."

---

## 5. Job model, orchestration flow, and pair serialization (Revision 2 — replaces Revision 1's same-job sequencing design entirely; job-lifetime and handoff mechanics corrected Revision 3)

### 5.1 Three job types (binding, comment `5015619162`; job-lifetime binding tightened, comment `5015830229`)

**A. `inventory_push_sync` — orchestration and read job only.**

- Replay policy: `remote_read_replay_safe`.
- Performs **no** Shopify mutation and creates **no** `mutation.attempt`
  row.
- Performs, per dispatch: first-push confirmation checks; reconnect
  read-first checks; the current Shopify level/`available` read; the
  Odoo `free_qty` read; the last-accepted business-state comparison;
  drift classification; target derivation; activation-required
  determination.
- Enqueues **at most one** mutation job per dispatch (either
  `inventory_activate` or `inventory_set_quantities`, never both, never
  neither-then-retry-itself-as-a-mutation).
- Kept **outside** the mutation-domain registry (no `mutation_domain`
  value, no reconciliation-strategy entry, no idempotency key) — it is a
  Layer 1 read job, exactly like the existing generic
  `remote_read_replay_safe` reconciliation reads DEC-036 already defines.

**B. `inventory_activate` — mutation job.**

- `mutation_domain = 'inventory_activate'`; `job_type == mutation_domain`.
- One job, one Shopify request, one Layer 2 attempt — **for this job's
  entire lifetime** (Revision 3, binding correction 1). One idempotency
  key.
- Full contract: §4 row 2.

**C. `inventory_set_quantities` — mutation job.**

- `mutation_domain = 'inventory_set_quantities'`; `job_type ==
  mutation_domain`.
- One job, one Shopify request, one Layer 2 attempt — **for this job's
  entire lifetime** (Revision 3, binding correction 1). **A bounded
  CAS-stale retry never redispatches this job** — it transitions this
  job to the terminal state `cancelled` and creates a **new**, separate
  `inventory_set_quantities` job carrying an incremented
  `cas_retry_ordinal` (§4 row 1, §5.4 handoff
  C). This corrects Revision 2's design, which described the bounded
  retry as "a new job dispatch of this same job" — that phrasing
  permitted one job to accumulate multiple `mutation.attempt` rows over
  its lifetime, which the control room rejected as a continuing
  violation of Gate A's one-job/one-attempt rule.
- Full contract: §4 row 1.

**No mutation job may execute two Shopify mutations, and no mutation job
may own more than one `mutation.attempt` row for its entire lifetime**
(Revision 3, binding correction 1) — this applies even to repeated
attempts of the *same* mutation kind after a bounded, transient failure
(CAS-stale, reconciliation `not_applied`): each such retry is a **new**
job, never a redispatch of the job that made the failed/unresolved
attempt. This is a domain-specific tightening of DEC-036 D9's generic
"`failed_clean` retry creates a new attempt on next dispatch" pattern —
this domain's two mutation job types apply that pattern at **job**
granularity (new job, new attempt) rather than within a single job's own
lifecycle, closing the gap Revision 2 left open. No job may combine two
conceptually distinct business mutations (activation and a quantity set)
into one execution, either — that remains a separate, independently
forbidden design (Revision 2, binding correction 1/2).

Every statement in Revision 1 saying `inventory_push_sync` is itself a
mutation job, that it contains both attempts, that both attempts occur
inside the same job, or that `current_attempt_token` is overwritten for a
second *different* mutation within one job, is withdrawn. Every statement
in Revision 2 saying a `CHANGE_FROM_QUANTITY_STALE` or reconciliation
`not_applied` outcome causes "a new job dispatch of this same job" or "the
job is not re-created, it is redispatched" — rather than creating a
genuinely new, separate job record — is withdrawn (Revision 3).

### 5.2 Orchestration flow (frozen; step 7 corrected Revision 3)

1. A trigger (odoo_event/scheduled_sync/manual_sync) or scan coalesces
   the latest Odoo target for one pair (§10).
2. It enqueues or refreshes one `inventory_push_sync` orchestration job
   for that pair (subject to §5.3's one-non-terminal-job-per-pair rule).
3. `inventory_push_sync` performs the fresh Shopify read and all gates
   (§5.1.A).
4. When the Shopify level exists and the pair is safe to push: enqueue
   one `inventory_set_quantities` mutation job.
5. When the Shopify level does not exist and first push is confirmed:
   enqueue one `inventory_activate` mutation job.
6. `inventory_activate` performs only activation, at explicit
   `available: 0` (§4 row 2).
7. **Corrected, Revision 3 (binding correction 2):** after
   `inventory_activate`'s reconciliation read confirms `applied` — **in
   the same database transaction that terminalizes `inventory_activate`
   as `succeeded`**, under the pair's row lock — a fresh
   `inventory_push_sync` job is enqueued **atomically** (§5.4 handoff
   B). This does **not** wait for an unrelated future scan or manual
   trigger — Revision 2's wording ("the normal scan/manual trigger
   admits a fresh `inventory_push_sync` orchestration job... once the
   activation job has gone terminal") is withdrawn; the handoff is part
   of the same transaction as the activation job's own terminalization,
   not a separately-admitted later event. The pending Odoo target
   remains coalesced on the binding (§10); the activation job itself
   does not issue `inventorySetQuantities` and does not enqueue it
   directly. The atomically-enqueued fresh `inventory_push_sync` job
   still performs its own full fresh Shopify read and gates (§5.1.A)
   before, per step 4, enqueueing `inventory_set_quantities` — atomicity
   guarantees the handoff, not a skipped read.
8. `ITEM_NOT_STOCKED_AT_LOCATION` received by `inventory_set_quantities`
   is not an inline activation trigger — it routes fail-closed to the
   non-terminal `blocked_manual_review` state (§4 row 1, §9), released
   only via §5.5's `action_recheck_inventory_pair`, never issuing
   `inventoryActivate` from the same job.

No direct mutation chaining is permitted — a mutation job never enqueues
another mutation job; only `inventory_push_sync` enqueues mutation jobs,
and only after its own fresh read and gates.

### 5.3 Pair serialization identity and admission (binding, comment `5015619162` §5)

- **Pair-serialization identity (frozen literal):**
  `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`.
  All three job types (`inventory_push_sync`, `inventory_activate`,
  `inventory_set_quantities`) for the same pair use this exact identity
  as their `operation_scope_key`. (Cross-reference for implementers: the
  Task 013 packet's `shopify_inventory_item_gid` and
  `location_mapping_id → shopify_gid` fields are the concrete sources for
  `inventory_item_gid`/`shopify_location_gid` in this literal.)
- **Admission rule:** only one non-terminal inventory job (of any of the
  three types) may exist for a given pair-serialization identity at a
  time. A new job for the same pair is refused admission (not silently
  duplicated, not silently dropped — refused, and any pending target
  update instead coalesces onto the binding, §10) while one is
  non-terminal. **A job in `blocked_manual_review` is not terminal for
  this purpose (§5.5) — it continues to hold the pair's
  `operation_scope_key` and continues to block new-job admission for the
  pair.**
- **Handoff rule:** the current job must reach a stopping point — the
  terminal state `succeeded`, the terminal state `cancelled` (when
  superseded by a replacement job, §5.4), or the **non-terminal**
  `blocked_manual_review` state (which continues to hold the pair's
  `operation_scope_key` until an authorized release, §5.5) — **before**
  the next phase job (an orchestration re-read after activation, a
  mutation job enqueued by an orchestration read, or a CAS/`not_applied`
  replacement job) is created. `failed_clean`/`uncertain`/`applied`/
  `not_applied` are mutation-**attempt** outcome/resolution values (DEC-036
  D9/D10) — they are never values of `shopify.connector.job.state` and
  never appear in this job-state list. Terminalization of the current job
  (or its transition to the non-terminal `blocked_manual_review` state)
  and enqueue of the next
  phase job occur **atomically**, in the same database transaction,
  under a row lock on the pair's binding record
  (`shopify.connector.inventory.level.binding`), held for the duration of
  the handoff. The exact transaction contract for each of the four named
  handoff types is §5.4.
- **Rollback guarantee:** if that transaction rolls back for any reason,
  both the current job's terminal state **and** the next phase job's
  existence roll back together — the system is left exactly as if the
  handoff had not been attempted (no orphaned child job, no job silently
  stuck non-terminal with no successor).
- **Concurrency proof required:** the Task 013 implementation must
  include a genuine independent-PostgreSQL-connection concurrency test
  (mirroring the Stage 0 pattern already proven for job claims) proving
  that two concurrent transactions attempting to create the next phase
  job for the same pair cannot both succeed — exactly one wins, the other
  observes the pair already non-terminal (or the already-created
  successor) and refuses. This is a **named, required test**, not an
  implementation choice left open (Task 013 §5, `test_inventory_push_mechanics.py`).
- **Stage 0 seam, not a Stage 0 change:** where the existing Layer 2
  substrate derives `operation_scope_key` from job identity (DEC-036
  D14), Task 013 adapts through that **existing, accepted domain
  extension seam** — it does not modify Stage 0's architecture, schema,
  or protocol. The pair-serialization identity above is this domain's own
  value for that existing generic field. §13A records the specific points
  where this domain's design still depends on a Stage 0 correction that
  has not yet landed.

### 5.4 Atomic handoff contract (new, Revision 3, closes binding correction 2)

Under a row lock on `shopify.connector.inventory.level.binding`, held for
the duration of the handoff, each of the following four handoffs occurs
in **one** database transaction. No new core job state is introduced by
any of them — each uses only the existing terminal states `succeeded` and
`cancelled`, plus, where a replacement is not created, the existing
**non-terminal** `blocked_manual_review` state (§5.5). `failed_clean` is
never a job state: it is the mutation attempt's own `observed_outcome`
(DEC-036 D9), preserved unchanged when its job transitions to
`cancelled`.

- **A. Orchestration → mutation.** `inventory_push_sync` completes its
  read and all gates (§5.1.A); terminalizes as `succeeded`, which clears
  its hold on the pair's `operation_scope_key`; exactly one mutation
  child (`inventory_activate` or `inventory_set_quantities`) is created;
  both job IDs are logged.
- **B. Activation → fresh orchestration.** When `inventory_activate`'s
  own reconciliation read confirms `applied` (§4 row 2): terminalize
  `inventory_activate` as `succeeded`, clearing its hold on
  `operation_scope_key`; enqueue a fresh `inventory_push_sync` job —
  atomically, in the same transaction, not waiting for an unrelated
  scan/manual trigger (§5.2 step 7); both job IDs logged. The child
  `inventory_push_sync` still performs its own fresh Shopify read and
  gates before creating `inventory_set_quantities`.
- **C. CAS-stale replacement.** On a `CHANGE_FROM_QUANTITY_STALE` outcome
  for an `inventory_set_quantities` job at `cas_retry_ordinal` N (N ∈
  {0, 1, 2}): the job's own single attempt keeps `observed_outcome=
  'failed_clean'` (`error_class='concurrency_race_conflict'`) unchanged;
  the **job itself** transitions to the existing core job state
  `cancelled` — **not** a new core state — with `superseded_by_job_id`
  set to the replacement job's ID and
  `cancel_reason='cas_stale_bounded_replacement'`; flush so its hold on
  `operation_scope_key` clears; a **new** `inventory_set_quantities` job
  is created, in the same transaction, with `cas_retry_ordinal = N + 1`;
  both job IDs logged. At N=3 (the 4th mismatch): no replacement job is
  created; that job instead transitions to the existing **non-terminal**
  `blocked_manual_review` state (`manual_review_subreason='binding_conflict'`),
  which continues to hold `operation_scope_key` until an authorized §5.5
  release.
- **D. Reconciliation `not_applied` replacement.** For either mutation
  domain: the old attempt's `uncertain` `observed_outcome` and its
  resolved `not_applied` `resolution_disposition` are preserved,
  immutable (DEC-036 D9/D10); the **job itself** transitions to the
  existing core job state `cancelled` — **not** a new core state — with
  `superseded_by_job_id` set and
  `cancel_reason='reconciliation_not_applied_replacement'`; flush so its
  hold on `operation_scope_key` clears; a **new** same-domain job is
  created, in the same transaction; the new job makes the next attempt
  later through its own normal dispatch; both job IDs logged.

**Job-lineage fields used by this contract:**

- `cas_retry_ordinal` (Integer, default 0; `inventory_set_quantities`
  only) — the **only new, domain-owned** job-lineage field this Gate B
  package introduces, added to `shopify.connector.job` through the
  inventory addon's own `_inherit` extension. §4 row 1.
- `superseded_by_job_id` — an **existing core** `shopify.connector.job`
  field (Many2one to the job model, nullable), reused here, not new
  domain schema. Set only when a job **transitions to `cancelled`**
  because a replacement/next-phase job was created in its place
  (handoffs C, D, and the review-release action, §5.5). **Not** set on a
  `succeeded` terminal state reached by ordinary successful phase
  completion (handoffs A and B) — those log both job IDs but set neither
  `superseded_by_job_id` nor `cancel_reason`, because nothing was
  cancelled or replaced; a plain `succeeded` job with no successor at all
  (e.g. an `inventory_set_quantities` job with nothing left to coalesce)
  also leaves it unset.
- `cancel_reason` — an **existing core** `shopify.connector.job` field
  (Char, nullable), reused here with a fixed domain vocabulary:
  `cas_stale_bounded_replacement` / `reconciliation_not_applied_replacement`
  / `manual_review_release`. Set together with `superseded_by_job_id`, on
  the same `cancelled` transition.

`cas_retry_ordinal` is the only new schema this domain adds for
job-lineage tracking, and it does not add a new value to the job model's
core state Selection. `superseded_by_job_id` and `cancel_reason` are
existing core fields — reusing them adds no new schema at all. None of
the three is read as transport-replay or idempotency authority (that
remains exclusively `mutation.attempt`, C5, unchanged).

- **Rollback guarantee:** if the handoff transaction rolls back for any
  reason, both the old job's terminal state/lineage fields **and** the
  new job's existence roll back together — no orphaned child, no job
  left non-terminal with no successor.
- **Concurrency proof required:** unchanged from §5.3 — a genuine
  independent-PostgreSQL-connection concurrency test must additionally
  prove that two concurrent transactions attempting to create a
  replacement job for the same superseded job cannot both succeed.

### 5.5 Blocked manual review is not terminal; the inventory review-release action (new, Revision 3, closes binding correction 3)

- **`blocked_manual_review` is not a terminal state for the purpose of
  pair admission.** A job in `blocked_manual_review` retains the pair's
  `operation_scope_key` (§5.3): it prevents any new job of any of the
  three inventory job types from being admitted for the same pair, and
  it prevents any automatic child job from being created from it. It
  remains blocked until an authorized review action completes.
- No automatic orchestration job, mutation job, or retry/replacement
  child may ever be created directly from a `blocked_manual_review` job.
- **`action_recheck_inventory_pair(reason)`** — the one domain action
  that releases a blocked inventory pair:
  - **Owner:** `shopify.connector.inventory.level.binding`, or the
    accepted inventory service acting on that binding.
  - **Reviewer or Administrator** group only.
  - Requires a mandatory, non-empty `reason`.
  - Acquires the pair's row lock (the same lock used by §5.4's
    handoffs).
  - Requires exactly one active `blocked_manual_review` inventory job
    for the pair.
  - Requires that job's linked attempt to have
    `observed_outcome='failed_clean'` **and**
    `effective_disposition() == 'not_applied'` — the effective-disposition
    helper (DEC-036 D10), not a requirement that the raw
    `resolution_disposition` field itself be populated; a direct
    `failed_clean` attempt normally has no separate resolution row.
  - **Allowed** only when `manual_review_subreason` is
    `inventory_location_missing`, or an explicitly enumerated safe
    `binding_conflict` clean-rejection case (an ordinary Shopify
    validation rejection, or `NON_MUTABLE_INVENTORY_ITEM`) — **never**
    an unexplained non-zero post-activation level, which remains a
    genuine data-integrity concern requiring the Stage 0
    Administrator-only manual resolution path instead.
  - **Forbidden** for: `uncertain` attempts, `duplicate_risk`,
    `idempotency_contract_violation`, any unresolved reconciliation, and
    `store_identity_mismatch` — these remain resolvable **only** through
    the existing Stage 0 mutation-attempt resolution path (DEC-036's
    Administrator-only manual resolution), never through this action.
  - **Never** modifies `observed_outcome`. **Never** writes
    `resolution_disposition`.
  - Atomically, in one transaction under the row lock: the blocked job
    transitions from `blocked_manual_review` to the existing core job
    state `cancelled` (`cancel_reason='manual_review_release'`,
    `superseded_by_job_id` set to the new job); flush so its hold on
    `operation_scope_key` clears; and exactly one fresh
    `inventory_push_sync` job is enqueued, in the same transaction.
  - Records the acting user's ID, the reason, the old job ID, and the
    new job ID. No credential or PII enters this log (this domain
    carries none).
- **The generic core job manual-retry/manual-review actions remain
  forbidden for any mutation-evidence-linked job** — restated here for
  this domain's own blocked jobs; unresolved/uncertain/duplicate-risk
  cases route through Stage 0's own resolution path, never a generic
  retry action.

---

## 6. First-push guard (tightened, Revision 2 wording update)

- Preview (`inventory_first_push_preview`) and explicit confirmation
  (`action_confirm_first_push()`, recording actor/time/preview quantity)
  are required before `inventory_push_sync` is permitted to enqueue
  **either** mutation job type for a pair (Task 013 D-013-4, unchanged in
  substance; Revision 2 corrects the mechanism — the gate is checked by
  the orchestration job at enqueue time, not "inside" a combined mutation
  job).
- First push never bypasses Layer 2 — both `inventory_activate` (if
  needed) and `inventory_set_quantities` run through the full wrapper as
  their own standalone jobs, exactly like every later push.
- Activation never creates an unreviewed nonzero stock state: it always
  requests an explicit `available: 0`, and its own reconciliation read
  (§4 row 2) must show `applied` before the atomic handoff (§5.4 handoff
  B) creates the fresh orchestration job that may go on to enqueue the
  set-quantities job.

---

## 7. Task 013 job contract — frozen (closes contradiction C10, updated Revision 3)

- **`job_type` values (six — Revision 2 adds two):**
  `inventory_push_sync` (orchestration/read-only, `remote_read_replay_safe`),
  `inventory_push_scan`, `inventory_first_push_preview`,
  `inventory_location_sync` (unchanged, existing four), plus
  **`inventory_activate`** and **`inventory_set_quantities`** (new,
  Revision 2 — each a standalone mutation job type, `job_type ==
  mutation_domain`, and each making at most one `mutation.attempt` for
  its entire lifetime, Revision 3). No new job type is added for
  reconciliation reads — those continue to use the existing generic
  `remote_read_replay_safe` job type (DEC-036 D14).
- **`job_source` values (unchanged, Task 013 D-013-6):** `odoo_event`
  (`trigger_origin='inventory_stock_change'`), `scheduled_sync`,
  `manual_sync`, `export_preview_dry_run`.
- **Error-class vocabulary (frozen, Revision 3 — closes binding
  correction 4):** `shopify_user_errors_validation` (ordinary Shopify
  validation/clean rejection, both domains), `inventory_location_missing`
  (also an `error_class` value here, not only a subreason —
  `ITEM_NOT_STOCKED_AT_LOCATION`), `concurrency_race_conflict`
  (`CHANGE_FROM_QUANTITY_STALE`; structured
  `IDEMPOTENCY_CONCURRENT_REQUEST`), `shopify_throttling_rate_limit`
  (`THROTTLED`), `shopify_temporary_server_network` (network
  timeout/HTTP 5xx), `data_shape_schema_mismatch` (malformed/partial
  response; `inventory_activate`'s ambiguous non-empty-`userErrors`-plus-
  non-null-`inventoryLevel` case), `idempotency_contract_violation`
  (structured idempotency mismatch/previous-attempt-failed). **No other
  `error_class` value is authorized without a further Gate decision.**
  The four values `remote_validation_rejected`/`remote_precondition_mismatch`/
  `transport_ambiguous`/`clean_rejection`, used in Revision 2, are
  **withdrawn** and must not appear current-facing anywhere in this
  document set.
- **Manual-review-subreason vocabulary:**
  - `inventory_location_missing` (existing — unmapped item/location;
    Revision 2 also routes `ITEM_NOT_STOCKED_AT_LOCATION` here)
  - `binding_conflict` (existing — stale/recreated Shopify identity;
    extended to also cover: `NON_MUTABLE_INVENTORY_ITEM`, persistent CAS
    divergence once the 3 bounded replacements are exhausted,
    unexplained inventory drift, and a nonzero post-activation level or
    activation clean-rejection)
  - `destructive_write_guard_blocked` (existing — unconfirmed first-push
    row)
  - `duplicate_risk` (DEC-036 D17, generic — N=3 inconclusive cap, both
    matrix rows)
  - `store_identity_mismatch` (DEC-036 D18, generic)
  - `idempotency_contract_violation` (DEC-036 D6, generic; `inventory_set_quantities`
    row only — `inventory_activate` folds any equivalent case into
    `binding_conflict`'s uniform clean-rejection rule, §4 row 2)
  - `no_reconciliation_strategy` (DEC-036 D16, generic — should never
    fire once both matrix rows are registered)
- **Job-lineage fields:** `cas_retry_ordinal` (Integer, default 0,
  `inventory_set_quantities` only) is the **only new, domain-owned**
  field this Gate B package introduces. `superseded_by_job_id`
  (Many2one, nullable) and `cancel_reason` (Char, nullable, fixed
  vocabulary — §5.4/§5.5) are **existing core** `shopify.connector.job`
  fields, reused here, not new domain schema. None of the three adds a
  new value to the job model's core state Selection.
- **Domain action (new, Revision 3):** `action_recheck_inventory_pair(reason)`
  — §5.5; Reviewer/Administrator only; the sole authorized release path
  for a `blocked_manual_review` inventory job whose attempt is
  `failed_clean`/`not_applied` with subreason `inventory_location_missing`
  or an enumerated safe `binding_conflict` case.
- **Pair-serialization identity convention:** §5.3, frozen literal
  `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`
  for all three inventory job types on a pair; reconciliation jobs use
  the existing generic convention
  `reconcile:{store}:{mutation_domain}:{attempt_token}` (DEC-036 D14).
- **Domain-enable flag:** `inventory_domain_enabled` gates all six job
  types above, plus both matrix rows' admission via the C2 registry gate.
- **Connection-generation behavior:** unchanged from the existing generic
  admission behavior; every job type snapshots
  `expected_connection_generation`/`expected_store_identity` at its own
  C1/C2, independently per job.

---

## 8. Task 013B — Layer 2 non-applicability (closes contradiction C11, unaffected in substance by Revision 2/3)

Restated bindingly, in this record and in the Task 013B packet's own §0:

- Task 013B issues **zero** Shopify mutations. It reads
  `InventoryLevel.quantities` (a `remote_read_replay_safe` Layer 1 job,
  unchanged) and performs guarded local Odoo writes.
- Because Task 013B never calls a Shopify mutation, DEC-036's mutation
  attempt model, C1/C2/NET/C3 protocol, and reconciliation contract do
  not apply to it — no `mutation.attempt` row, no `mutation_domain`
  registration, no Layer 2 wrapper call anywhere in its scope.
- Task 013B's own safety contract (row locking, final re-read under
  lock, drift/topology abort, post-write `free_qty` verification) is a
  local Odoo transaction/locking concern, unchanged by this revision.
- No Layer 2 mutation wrapper is added to Task 013B merely for symmetry
  with Task 013.
- **Exact interaction with Task 013 (unchanged, restated):** Task 013
  must be installed and its Gate B/Stage 0 dependencies accepted first; a
  baseline apply for a pair blocks any concurrent inventory job for that
  same pair (shared pair-serialization identity, §5.3, Task 013B
  D-013B-4); after a successful baseline, Odoo is the standing authority
  and the next Task 013 push for that pair begins from the accepted
  baseline state (D-013B-8, unchanged).

---

## 9. Job/mutation-consequence contract (new, Revision 2, closes binding correction 5; rewritten Revision 3 for the fixed vocabulary and the new-job replacement model, closes binding corrections 1/4/5)

For every Task 013 mutation outcome, this table specifies
`observed_outcome`, `error_class` (fixed vocabulary only, §7),
`manual_review_subreason` (where applicable), whether automatic retry is
permitted, the retry class and its counter/delay sources, whether
reconciliation is required, and the next orchestration behavior. Unknown
or malformed consequence data (anything not enumerated
below, e.g. a `mutation.attempt`-consequence payload that fails schema
validation) **must never default to automatic retry** — it routes
fail-closed to `uncertain`/`blocked_manual_review`/`no_reconciliation_strategy`
-equivalent handling. Domain code must never write job state directly
outside the accepted Layer 2 consequence interface (DEC-036's existing
C3 outcome-commit seam) — this table constrains what that interface is
told to do, it does not add a second write path. **Revision 3 correction:
every CAS-stale retry and every reconciliation `not_applied` retry now
creates a new job (see the "Next orchestration behavior" column) — it
never redispatches the job whose attempt failed/resolved.**

| Outcome | `observed_outcome` | `error_class` | `manual_review_subreason` | Auto-retry | Retry class / bound | Retry counter source | Retry-delay source | Reconciliation required | Next orchestration behavior |
|---|---|---|---|---|---|---|---|---|---|
| `inventory_set_quantities` succeeded | `succeeded` | — | — | No | — | — | — | No (evidence is direct) | Job terminal `succeeded`; binding's `last_pushed_available`/`last_pushed_at` refreshed |
| CAS stale, ordinal 0/1/2 (replacement permitted) | `failed_clean` | `concurrency_race_conflict` | — | No (not on this job) | New replacement job, bounded max 3 replacements | `cas_retry_ordinal` (job field, §4 row 1) | Existing generic bounded-retry backoff policy applied to the new job's dispatch timing (DEC-009 pattern; no new backoff mechanism) | No (fresh CAS pre-read on the new job substitutes) | This job transitions to the terminal state `cancelled` (`superseded_by_job_id` set, `cancel_reason='cas_stale_bounded_replacement'`); a **new** `inventory_set_quantities` job is created with `cas_retry_ordinal + 1` (§5.4 handoff C) |
| CAS stale, ordinal 3 (4th mismatch) | `failed_clean` | `concurrency_race_conflict` | `binding_conflict` | No | Exhausted | `cas_retry_ordinal == 3` | — | No | Job transitions to the non-terminal `blocked_manual_review` state (holds `operation_scope_key` until an authorized §5.5 release); no replacement job; pending target stays coalesced |
| Validation/binding code (`INVALID_*`, `NON_MUTABLE_INVENTORY_ITEM`, `NO_DUPLICATE_...`) | `failed_clean` | `shopify_user_errors_validation` | `binding_conflict` | No | — | — | — | No | Job transitions to the non-terminal `blocked_manual_review` state |
| `ITEM_NOT_STOCKED_AT_LOCATION` | `failed_clean` | `inventory_location_missing` | `inventory_location_missing` | No (not by this job) | — | — | — | No (this job); a fresh `inventory_push_sync` orchestration read is required | Job transitions to the non-terminal `blocked_manual_review` state, holding `operation_scope_key`; pending target stays coalesced; released **only** by an authorized `action_recheck_inventory_pair` (§5.5), which then enqueues the fresh `inventory_push_sync` job — no scan or manual trigger admits one automatically while blocked |
| `IDEMPOTENCY_CONCURRENT_REQUEST` | `uncertain` | `concurrency_race_conflict` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled; retry only after resolution |
| `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` / `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` | `uncertain` (until reconciled) | `idempotency_contract_violation` | `idempotency_contract_violation` | No | — | — | — | Yes | Job transitions to the non-terminal `blocked_manual_review` state, no automatic retry |
| `THROTTLED` (either domain) | `uncertain` | `shopify_throttling_rate_limit` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled |
| Network timeout / HTTP 5xx ambiguity (either domain) | `uncertain` | `shopify_temporary_server_network` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled |
| Malformed/partial response; `inventory_activate` ambiguous (`userErrors`+non-null `inventoryLevel`) | `uncertain` | `data_shape_schema_mismatch` | — | No (reconcile first) | — | — | — | Yes | Reconciliation read scheduled |
| `inventory_set_quantities` reconciliation → `not_applied` | (resolved) `not_applied` | — | — | No (not the same job) | New replacement job | `superseded_by_job_id` lineage | Existing generic backoff applied to the new job | Already performed | Old job transitions to the terminal state `cancelled` (`cancel_reason='reconciliation_not_applied_replacement'`); a **new** `inventory_set_quantities` job is created with a fresh attempt (§5.4 handoff D) |
| `inventory_set_quantities` reconciliation → inconclusive | (unresolved) | — | `duplicate_risk` (at N=3 cap) | No | — | `inconclusive_reconciliation_count` | — | Yes, repeat | Next reconciliation read scheduled; at cap, job transitions to the non-terminal `blocked_manual_review` state |
| `inventory_activate` succeeded | `succeeded` | — | — | No | — | — | — | No | Job transitions to the terminal state `succeeded`; triggers §5.4 handoff B (atomic fresh-orchestration enqueue) |
| `inventory_activate` clean rejection (any `userErrors`+null `inventoryLevel`) | `failed_clean` | `shopify_user_errors_validation` | `binding_conflict` | No | — | — | — | No | Job transitions to the non-terminal `blocked_manual_review` state |
| `inventory_activate` reconciliation → `not_applied` | (resolved) `not_applied` | — | — | No (not the same job) | New replacement job | `superseded_by_job_id` lineage | Existing generic backoff applied to the new job | Already performed | Old job transitions to the terminal state `cancelled` (`cancel_reason='reconciliation_not_applied_replacement'`); a **new** `inventory_activate` job is created with a fresh attempt (§5.4 handoff D) |
| `inventory_activate` reconciliation → inconclusive | (unresolved) | — | `duplicate_risk` (at N=3 cap) | No | — | `inconclusive_reconciliation_count` | — | Yes, repeat | Next reconciliation read scheduled; at cap, job transitions to the non-terminal `blocked_manual_review` state |
| `blocked_manual_review` release via `action_recheck_inventory_pair` | unchanged (the action never rewrites `observed_outcome`/disposition) | — | — | N/A (an authorized manual action, not an automatic retry) | — | — | — | No (release requires `effective_disposition() == 'not_applied'`) | Old job transitions from the non-terminal `blocked_manual_review` state to the terminal state `cancelled` (`cancel_reason='manual_review_release'`, `superseded_by_job_id` set); exactly one fresh `inventory_push_sync` job enqueued atomically (§5.5) |
| Unknown/malformed consequence data | `uncertain` (fail-closed default) | `data_shape_schema_mismatch` | `no_reconciliation_strategy` (if a registry lookup also fails) | No | — | — | — | Yes | Reconciliation/manual review scheduled; never automatic retry |

---

## 10. Coalescing (expanded, Revision 2)

- **Binding-level allowed business fields** (informational/coalescing
  only, refreshed from a reconciliation read or a `succeeded` attempt's
  evidence): `pending_target_available`, `last_pushed_available`,
  `last_pushed_at`, `last_known_shopify_available`, and the existing
  first-push state/evidence fields (`first_push_state`,
  `first_push_preview_qty`, `first_push_confirmed_at`,
  `first_push_confirmed_by_uid`).
- **These must never include:** the Shopify transport idempotency key;
  the exact-request fingerprint as replay authority; the attempt token as
  transport authority. All three live exclusively on
  `shopify.connector.mutation.attempt` (C5, unchanged).
- **While any inventory job for the pair is non-terminal** (§5.3,
  including a job in `blocked_manual_review`, §5.5): new Odoo stock
  changes update/coalesce `pending_target_available` on the binding
  (last-value-wins — a later change overwrites an earlier uncommitted
  one, it does not queue); no duplicate pair job is admitted; no second
  mutation attempt is created for the pair — a bounded CAS-stale or
  `not_applied` replacement is a **new job** for the pair, not a "second
  attempt" on the still-non-terminal one (Revision 3; the replacement job
  creation is itself part of the same atomic handoff that terminalizes
  the job it replaces, §5.4, so the pair is never briefly held by two
  non-terminal jobs at once).
- **After the active job reaches a stopping point** (the terminal state
  `succeeded`, or the non-terminal `blocked_manual_review` state being
  released via §5.5): the next
  `inventory_push_sync` orchestration dispatch reads the latest coalesced
  `pending_target_available` — a stale target (one superseded by a later
  Odoo change while the prior job ran) is never pushed; the fresh read
  always wins.

---

## 11. Inventory operating model — reconciled (summary; full text in the corrected document)

- Standing model unchanged from DEC-010: Odoo authoritative after
  onboarding; push `available` only; source is Odoo location-context
  `free_qty`; one mapped pair per request; Layer 2 wraps every Shopify
  mutation, each as its **own standalone mutation job**, making at most
  one attempt for its entire lifetime (Revision 3, §5); reverse direction
  is read/verify/review only; Task 013B is the only controlled onboarding
  exception; unexplained drift creates review evidence, never a silent
  overwrite; reconnect reads before push; no standing bidirectional sync;
  no committed/`on_hand` write; no batching; no binding-owned transport
  idempotency.
- Five distinct flows, kept explicit and never conflated: (1) standing
  Odoo→Shopify push (§4 row 1, §5 job model and orchestration flow when
  activation is needed); (2) Shopify reconciliation read (§4, both
  rows); (3) reconnect catch-up read (§12, DEC-036 D18 store-identity
  check as the first reconciliation step); (4) Task 013B one-time
  reviewed baseline (§8, no Layer 2); (5) manual divergence review
  (review cases from C6/C7/matrix `binding_conflict` routing, §9, §5.5's
  review-release action).

---

## 12. Reconnect policy — reconciled (summary; full text in the corrected document)

The inventory reconnect sequence is:

1. Store reconnect succeeds (existing eight-step sequence, unchanged).
2. Connection generation is current (existing, unchanged).
3. New push/activation admission remains blocked for every mapped pair
   until step 4 clears — enforced by `inventory_push_sync`'s own
   admission gate (§5.1.A), not by any mutation job classifying
   reconnect state itself. **No mutation job performs the reconnect
   classification itself** — this is exclusively an `inventory_push_sync`
   responsibility.
4. Read Shopify `available` (and, if the pair has no confirmed baseline,
   `on_hand`) for every mapped pair — beginning with the store-identity
   check (DEC-036 D18).
5. Read Odoo current `free_qty` for every mapped pair.
6. Read the last accepted/pushed business state (`last_pushed_available`/
   `last_pushed_at`, C5 — never retry authority, only the comparison
   baseline here).
7. Classify: expected match (resume normally); known local change
   (resume, next push carries the new value); unexplained Shopify drift
   (review case); identity mismatch (`store_identity_mismatch`, never
   retried); missing level/activation required (the fresh
   `inventory_push_sync` orchestration job enqueues `inventory_activate`
   on the **next confirmed push**, per §5.2 step 5 — not automatically
   and not from any other job).
8. Unexplained drift routes to review, never a blind push.
9. Never blind push, for any classification.
10. A new push is permitted only after the read/review gate clears for
    that specific pair, and only `inventory_push_sync` may then enqueue
    the resulting mutation job.

Behavior for the named edge cases (long disconnect, credential rotation,
store identity mismatch, pending uncertain attempt, pending
reconciliation, mapping change, product binding change, inactive Shopify
location) is unchanged from the existing accepted reconnect
policy/DEC-036 D28/D18.

---

## 13. Factual Stage 0 status (new, Revision 2, closes binding correction 6)

As of this revision (2026-07-19), directly re-verified:

- **PR #178** ("Wave 3 Stage 0: DEC-031 Layer 2 core substrate") **exists**,
  is **open**, is a **draft**, is **unmerged**, at head
  `644853a68b3497c134ee648ce7399e50d30ff397`.
- PR #178's own body states: implementation complete by its own report;
  static validation (AST parse, XML parse, line-length scan, required
  tests present/registered, cron/ACL checks, production-mutation scan,
  base-to-head file-scope check, protected-ref recheck) performed and
  passing, by its own report; Odoo is **not installed** in that session's
  execution workspace, so the genuine PostgreSQL runtime tests, the
  process-death harness, the install/upgrade test, and the full connector
  regression were **not run there** — no runtime-pass claim is made by
  that PR itself.
- This record makes **no claim** that Stage 0 is accepted, merged,
  synchronized with this Gate B package, runtime-tested, or "frozen" as a
  runtime candidate. Every prior statement in this document set saying
  Stage 0 "has no PR yet" is corrected by this section and by the
  corresponding correction in each shared tracker (`mvp-program-state.md`,
  `research-handoff.md`) — those documents are updated to point here
  rather than repeating the stale claim inline.
- This Gate B package's own content does not depend on Stage 0's
  progress in either direction — it specifies the domain-specific
  contract Stage 0's generic substrate must support once both are
  accepted and merged. **§13A (new, Revision 3) states exactly what that
  support must include** — this section states PR #178's current,
  factual state; it does not itself claim PR #178 already meets §13A.

---

## 13A. Stage 0 correction prerequisites for Task 013 issuance (new, Revision 3, closes binding correction 7)

Task 013 remains **unissuable** — regardless of this Gate B package's own
acceptance — until the corrected PR #178 provides and proves all of the
following. These are stated as **prerequisites for PR #178's correction**,
not as Stage 0 features already delivered; PR #178's current content
(§13) does not claim any of them today, and this record does not reopen
Gate A or any DEC-036 decision (D1–D38) by naming them.

1. **One mutation job / one attempt enforcement** — a mutation job's
   relationship to `mutation.attempt` must make a second attempt on the
   same job structurally impossible (a schema constraint or an enforced
   invariant), not merely a documented convention this domain happens to
   follow.
2. **A validated domain-consequence interface using only the fixed error
   vocabulary** (§7, §9 of this record) — the interface Stage 0 exposes
   for a domain to report an outcome must reject an unrecognized
   `error_class`/`manual_review_subreason` value rather than silently
   passing it through.
3. **No unconditional `failed_clean` → same-job `retry_waiting`
   transition, and no unconditional resolved-`not_applied` → same-job
   `retry_waiting` transition**, in Stage 0's generic dispatch mechanism
   — or, if such a generic transition exists for other domains, an
   explicit, enforced per-domain override point this domain's
   registration uses to opt out of it in favor of the new-job
   replacement model (§5.4).
4. **Atomic attempt-outcome, audit, and job-consequence commit** — the C3
   outcome-commit seam must support, in one transaction, both recording
   the attempt's outcome and creating a replacement/next-phase job and
   updating `superseded_by_job_id`/`cancel_reason`, under the row lock
   this record requires (§5.4).
5. **A domain callback/seam permitting this domain's atomic
   replacement-job and phase-handoff behavior** (§5.4 handoffs A–D)
   without modifying Stage 0's own architecture, schema, or protocol —
   an extension point, not a Stage 0 redesign.
6. **The accepted `store_identity_mismatch` manual-review route**
   (DEC-036 D18) — implemented and proven, not only documented.
7. **Unknown/malformed consequence data fails closed** (§9, last row) —
   proven by a test, not only asserted.
8. **Mutation-evidence-linked generic manual-retry/manual-review actions
   remain blocked** (§5.5's closing bullet) — proven by a test that the
   generic core actions refuse a job carrying `mutation.attempt`
   evidence.

---

## 14. Traceability (Pass 2 summary, updated Revision 3)

For both matrix rows, the full chain is unbroken:

**`inventorySetQuantities`:** product decision (DEC-010, unchanged) → Task
013 packet D-013-2/D-013-3/D-013-9 → §4 row 1 of this record → §5 job
model/orchestration flow/atomic handoffs (§5.4)/review-release (§5.5) →
§9 consequence contract (fixed vocabulary, new-job replacement model) →
locked Task 013 Sol prompt (Layer 2 integration section, corrected role
model) → `test_inventory_push_mechanics.py` (unit) + genuine-concurrency
tests (§5.3/§5.4, Stage 0's proven pattern, extended) → Odoo.sh evidence
(Task 013 §5, unchanged requirement) → dev-store scenarios 1–8/10–12/17–19
(plan, scenario 5 corrected Revision 3) → rollback (Task 013 §6,
unchanged single-PR revert; attempt evidence retained per DEC-036 D32).

**`inventoryActivate`:** product decision (this record, §5, job model) →
Task 013 packet D-013-3/D-013-9 → §4 row 2 of this record → §5.4 handoff
B (atomic activation-to-orchestration handoff) → §9 consequence contract
→ locked Task 013 Sol prompt (corrected role model) →
`test_inventory_push_mechanics.py` (activation assertions) → Odoo.sh
evidence (same requirement, both mutations covered) → dev-store scenario
9 (plan) → rollback (same mechanism, both matrix rows disabled together
by the domain-enable flag).

Stage 0's own correction obligations toward this domain's design are
tracked separately in §13A, not restated in this traceability chain.

---

## 15. Status

**ACCEPTED — CONTROL-ROOM GATE B (Revision 3, accepted in substance by
comment `5016117207`; docs-only merge-closure normalization applied,
§1C).** No decision in this record has been self-accepted, in Revision 1,
Revision 2, Revision 3, or this normalization pass. No DEC-036 decision is
reopened. Gate A is not reopened. No `addons/**` file was created or
modified. No Odoo/Odoo.sh run occurred. No Shopify mutation was issued,
and no new Shopify **read** was performed in this pass either — every
correction is a wording/consistency fix to this record's own
job-state/field-ownership/blocked-review text in response to comment
`5016117207`, without any new claim about Shopify's API surface. Stage 0
(PR #178) remains held at `644853a68b3497c134ee648ce7399e50d30ff397`
until the post-merge integration SHA is verified and a consolidated
synchronization/correction prompt is issued.
