# MVP Program State — Live Tracker

> This is the single live status tracker for the MVP completion program (`DEC-032`). Update this file at the start and end of every Sol session and every Claude control-room review — it is the first thing any new session should read. The relatively stable contract (scope, waves, authority) lives in `mvp-completion-program.md`; this file is the frequently-changing status. Do not duplicate the contract's content here — link to it.

## Current status

**TASK 013 (PR #182) — FIRST GENUINE ODOO.SH RUNTIME VALIDATION COMPLETED (2026-07-21).**
On Odoo.sh build `35193596` (Odoo 19.0 / PostgreSQL 16.14), the exact submitted
head `26acf2b` was run for the first time at genuine runtime (all prior cycles
were static-only — see the validation record §14/§15). Campaign A exposed
**42/237 inventory tests failing**, including the known review-release P1 and
four further runtime-only production defects (operation_scope_key never cleared
before same-scope successor insert → P0; blocked-job supersede left
`manual_review_subreason` set; coalescing caught the wrong exception; operator
`free_qty` read not sudo'd), plus ~28 never-executed-at-runtime fixture defects.
A single consolidated correction (`2bc6bdb`, `addons/shopify_connector_inventory/**`
only) brings the focused inventory suite to **0 failed / 0 errors of 238**, with
full-install, upgrade, uninstall→reinstall (zero residue), security-matrix and
(single-transaction) suites all green. **Recommendation: RUNTIME GREEN — READY
FOR CONTROL-ROOM REVIEW.** Residuals (control-room): a core mutation-source-guard
false-positive on inventory's reviewed prepare/transport split (needs a core
allowlist or a literal-relocation decision); no genuine independent-connection
concurrency test exists; unchanged core/product/sale base-suite environmental
NOT-NULL failures (out of scope). PR #182 stays **draft, unmerged, not marked
ready**; no self-acceptance; no live Shopify mutation. Full evidence:
[`../05-qa/task-013-inventory-sync-validation-results.md`](../05-qa/task-013-inventory-sync-validation-results.md)
§15.

**WAVE 3 GATE B ACCEPTED — MERGE-CLOSURE NORMALIZATION APPLIED AND MERGE AUTHORIZED (2026-07-19, PR [#179](https://github.com/AdamsOdoo/Adams/pull/179)).**
The control room reviewed Revision 3 (immediately below) at head
`565d3daefdf0c87c46ffaf7a6d52f63841b1e770` and, by PR #179 comment
[`5016117207`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5016117207),
ruled **Wave 3 Gate B ACCEPTED IN SUBSTANCE** — the separate
orchestration/activation/set-quantities job model, one mutation job/one
attempt for the job's entire lifetime, replacement-job retries, atomic
handoffs, the fixed error vocabulary, freshness-safe reconciliation,
explicit Stage 0 prerequisites, and the current role model — conditioned
on one further docs-only merge-closure normalization commit correcting
eleven residual wording issues: (1) `failed_clean`/`uncertain`/`applied`/
`not_applied` are mutation-**attempt** outcome/resolution values, never
`shopify.connector.job.state` values or "terminal job states"; (2) a
replaced predecessor job transitions to the **existing** terminal state
`cancelled`, preserving its attempt's outcome/resolution unchanged; (3)
successful phase handoffs (orchestration→mutation, activation→fresh
orchestration) use `succeeded` and never set `superseded_by_job_id`/
`cancel_reason` — Revision 3's own §5.4 text had incorrectly listed the
activation handoff among the superseding ones; (4) `superseded_by_job_id`
and `cancel_reason` are **existing core** `shopify.connector.job` fields,
reused, not new domain schema — `cas_retry_ordinal` is the **only** new,
domain-owned field; (5) `blocked_manual_review` remains non-terminal,
removed from every terminal-state list; (6) no scan/manual trigger
admits a new orchestration job while a pair is blocked — only
`action_recheck_inventory_pair` releases it; (7)/(9) the exact
review-release owner/transition wording tightened; (8) the release
action's precondition is `effective_disposition() == 'not_applied'`, not
a raw `resolution_disposition` check; (10) `store_identity_mismatch`
stays a Stage 0 correction prerequisite, not an already-existing current
error class; (11) applied consistently across DEC-037, the Task 013
packet, the locked Task 013 prompt, the dev-store plan, and this tracker.
**Identity gate independently re-verified live before any edit:** PR
#179 open/draft/unmerged at the exact expected head
`565d3daefdf0c87c46ffaf7a6d52f63841b1e770`; base unchanged; exactly the
same 15 authorized files; no addon/test/security/XML/manifest/CI file
changed; comment `5016117207` read in full; PR #178 confirmed still
open/draft/unmerged at head `644853a68b3497c134ee648ce7399e50d30ff397`;
protected refs unchanged. **Claude did not accept its own package, in
any revision, and did not self-accept this normalization** — acceptance
authority is comment `5016117207`, product owner + ChatGPT control room.
After the normalization commit, PR #179 was marked ready and merged into
`mvp/program-integration` with a normal merge commit under expected-head
protection — see the merge record immediately following this entry (or
this file's Wave-status table row 3) for the exact merge SHA. **Stage 0
(PR #178) remains held**, unmerged and not runtime-proven, pending the
post-merge integration SHA and a consolidated synchronization/correction
prompt. **Recommendation: ISSUE CONSOLIDATED STAGE 0 SYNCHRONIZATION AND
CORRECTION PROMPT.**

---

**WAVE 3 GATE B REVISION 3 — JOB-LIFETIME/ATOMIC-HANDOFF/ERROR-VOCABULARY CORRECTION APPLIED PER SECOND CONTROL-ROOM REVISE RULING (2026-07-19, PR [#179](https://github.com/AdamsOdoo/Adams/pull/179), same day as Revisions 1/2 below; superseded by the acceptance entry above).**
The control room reviewed Revision 2 (immediately below) at head
`a88d5416c46662de1b15f5490b743a553185dc0a` and returned **REVISE** a
second time (PR #179 comment
[`5015830229`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5015830229)):
Revision 2's same-job CAS/`not_applied`-redispatch design still let one
mutation job accumulate more than one `mutation.attempt` row, still
violating Gate A's one-job/one-attempt rule; the activation→orchestration
handoff was not atomic; `blocked_manual_review`'s non-terminal status and
release path were undefined; the matrix used four invented `error_class`
values; the `applied` verdict carried an inverted timestamp condition;
and the locked prompts called Claude the control room/sole merge
authority. **Identity gate independently re-verified live before any
edit:** PR #179 open/draft/unmerged at the exact expected head
`a88d5416c46662de1b15f5490b743a553185dc0a`; base unchanged; exactly the
same 15 authorized files; no addon/test/security/XML/manifest/CI file
changed; comment `5015830229` read in full; PR #178 confirmed still
open/draft/unmerged at head `644853a68b3497c134ee648ce7399e50d30ff397`;
protected refs unchanged.

This session applied one coherent documentation-only correction batch
implementing every one of the seven binding corrections in comment
`5015830229`: every CAS-stale and reconciliation-`not_applied` retry now
creates a **new**, separate job (never a same-job redispatch) — new
job-lineage fields `cas_retry_ordinal` (0→1→2→3), `superseded_by_job_id`,
`cancel_reason`; a new atomic handoff contract (DEC-037 §5.4) freezing
four named transactions under a row lock, introducing no new core job
state; `blocked_manual_review` declared explicitly non-terminal, plus a
new `action_recheck_inventory_pair(reason)` domain action (DEC-037 §5.5);
the fixed error-class vocabulary substituted for the four invented values
(`remote_validation_rejected`/`remote_precondition_mismatch`/
`transport_ambiguous`/`clean_rejection`, all withdrawn); the `applied`
verdict's erroneous `updatedAt` condition removed; both locked Sol
prompts' ROLE sections corrected (ChatGPT = control room/acceptance
authority; Claude = planner/independent reviewer/Odoo.sh runtime
verifier; Sol = implementation worker); and a new DEC-037 §13A recording
the exact Stage 0 (PR #178) correction prerequisites for Task 013
issuance. Two new dev-store scenarios (20: `blocked_manual_review`
non-automatic-child; 21: `action_recheck_inventory_pair` release) were
added, now 21 scenarios total; no new official-source fetch was
performed — every correction is to this record's own design, not a new
Shopify API claim.

**Status: DEC-037 REVISED — RESUBMITTED FOR CONTROL-ROOM GATE B
RE-REVIEW (Revision 3). Task 013 packet: GATE B ACCEPTANCE CANDIDATE
(Revision 3) — NOT IMPLEMENTATION AUTHORIZED. Task 013B packet:
unaffected in substance, role-model cross-reference corrected. Both
locked Sol prompts: LOCKED, unissued, corrected for the job-lifetime
model and the current role model. Claude did not accept its own package,
in any revision.** No `addons/**` file was created or modified. No
Odoo/Odoo.sh run occurred. No Shopify mutation was issued, and no new
Shopify read either. PR #179 remains **open, draft and unmerged**; this
session performed no merge, no ready-marking. **Recommendation: READY
FOR FINAL CONTROL-ROOM WAVE 3 GATE B REVIEW.**

---

**WAVE 3 GATE B REVISION 2 — JOB-MODEL CORRECTION APPLIED PER CONTROL-ROOM REVISE RULING, RE-REVIEW PENDING (2026-07-19, draft PR [#179](https://github.com/AdamsOdoo/Adams/pull/179), same day as Revision 1 below).**
The control room reviewed Revision 1 (immediately below) and returned
**REVISE, NOT REJECTED** (PR #179 comment
[`5015619162`](https://github.com/AdamsOdoo/Adams/pull/179#issuecomment-5015619162)):
Revision 1's same-job, two-sequential-mutation-attempt design for
`inventoryActivate`/`inventorySetQuantities` conflicted with Gate A's
binding "one mutation job : one Shopify mutation request : one attempt
row" rule. **Identity gate independently re-verified live before any
edit:** PR #179 open/draft/unmerged at the exact expected head
`74478293511b5bc2763a8998c329a752fa08ea68`; base unchanged; exactly the
same 15 authorized files; comment `5015619162` read in full; **PR #178
now exists** (open, draft, unmerged, head
`644853a68b3497c134ee648ce7399e50d30ff397` — corrects Revision 1's "no
PR yet" statement, which was accurate when written); protected refs
unchanged.

This session applied one coherent documentation-only correction batch to
[`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) and all
14 companion documents implementing every binding correction from
comment `5015619162`: **three standalone job types** —
`inventory_push_sync` demoted to orchestration/read-only (no Shopify
mutation, no `mutation.attempt` row, enqueues at most one mutation job
per dispatch), `inventory_activate` and `inventory_set_quantities` each
its own standalone mutation job (`job_type == mutation_domain`), never
two attempts inside one job; a frozen pair-serialization identity and
atomic handoff mechanics (DEC-037 §5.3); message-string idempotency
classification for `inventoryActivate` withdrawn entirely, replaced by a
uniform payload-shape clean-rejection rule; freshness/ABA-safe
reconciliation verdicts for both mutation domains; a new explicit
job/mutation-consequence contract (DEC-037 §9); two new dev-store
scenarios (18: ABA/freshness; 19: `ITEM_NOT_STOCKED_AT_LOCATION` race,
fail-closed, now 19 scenarios total); both locked Sol prompts corrected
for the three-job model. One further narrow official-source verification
was performed live (the complete 17-value `InventorySetQuantitiesUserErrorCode`
enum, confirming `ITEM_NOT_STOCKED_AT_LOCATION` exists), closing a
citation gap Revision 1 left in this repository's own source materials.

**Status: DEC-037 REVISED — RESUBMITTED FOR CONTROL-ROOM GATE B
RE-REVIEW. Task 013 packet: GATE B ACCEPTANCE CANDIDATE (Revision 2) —
NOT IMPLEMENTATION AUTHORIZED. Task 013B packet: unaffected in substance,
cross-reference corrected. Both locked Sol prompts: LOCKED, unissued,
corrected. Claude did not accept its own package.** No `addons/**` file
was created or modified. No Odoo/Odoo.sh run occurred. No Shopify
mutation was issued (one Shopify read only, for the enum verification
above). PR #179 remains **open, draft and unmerged**; this session
performed no merge, no ready-marking. **Recommendation: READY FOR
CONTROL-ROOM WAVE 3 GATE B RE-REVIEW.**

---

**WAVE 3 GATE B REVISION 1 — INVENTORY-READINESS ACCEPTANCE CANDIDATE PRODUCED, RETURNED "REVISE, NOT REJECTED" BY THE CONTROL ROOM (2026-07-19, draft PR [#179](https://github.com/AdamsOdoo/Adams/pull/179)).**
Following Gate A's merge (PR #177, merge commit
`3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`, independently verified live
against `mvp/program-integration` and against PR #177 comment
[`5015174971`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015174971)'s
"parallel-start authorization"), this Claude control-room session
produced the Wave 3 Gate B documentation-only acceptance candidate on
branch `claude/wave-3-gate-b-inventory-2m5jcl`, draft PR
[#179](https://github.com/AdamsOdoo/Adams/pull/179). **Identity gate
independently re-verified live before any edit:** PR #177 merged at the
exact required SHA; `mvp/program-integration` identical to it; branch
`claude/wave-3-gate-b-inventory-readiness` did not exist (this session's
harness-provisioned branch, based at the exact required SHA with zero
drift, is used instead — a session-naming mechanic, not a scope
deviation); no open Gate B PR existed before this one; all three binding
PR #177 comments (`5015044226`, `5015174971`, `5015231326`) read in full;
Gate A documents confirmed ACCEPTED; the Sol Stage 0 branch
(`sol/wave-3-stage-0-layer2`) exists at the same base SHA but **has no
PR and is not merged** (reported factually, not inferred); protected refs
(`main`, `Shopify-connector`, both checkpoints,
`mvp/program-integration`) all confirmed unchanged.

**Deliverable:** [`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md)
(new decision record, DEC-037 was unused — first unused sequential
number) closes every remaining Task 013/013B contradiction DEC-036 Part
0.5 carried forward to Gate B: `changeFromQuantity` CAS field name
throughout (superseding stale `compareQuantity` references in
`inventory-operating-model.md` §4.4 and the Task 013 packet's addendum
heading — DEC-036's own D12 explicitly flagged these two documents as
out-of-scope for Gate A, now closed); binding-owned idempotency
(`last_push_idempotency_key`/`last_push_params_hash`) removed from the
inventory-level-binding schema, superseded by attempt-owned Layer 2
idempotency; unexplained Shopify-side drift made explicitly
review-case-first and blocking, never auto-overwritten; one pair per
mutation request made binding MVP behavior (DEC-036 D4), not a floor
awaiting batching; a **complete** `inventorySetQuantities`/
`inventoryActivate` Layer 2 mutation-domain matrix (DEC-037 §4) with a
new activation-then-set-quantities sequencing design (§5 — two distinct
Layer 2 attempts, own idempotency keys/fingerprints, never combined);
the Task 013 job contract frozen (§7: job_type/job_source/manual-review-
subreason/`operation_scope_key`/domain-enable-flag vocabulary); Task
013B's Layer-2-non-applicability made explicit in its own packet (new
§0); a 17-scenario dev-store mutation-validation plan
(`wave-3-dev-store-mutation-validation-plan.md`); and two locked,
unissued Sol prompts
([`sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md),
[`sol-wave-3-task-013b-locked-prompt.md`](../06-prompts/sol-wave-3-task-013b-locked-prompt.md)).
Two narrow official-source verifications were performed live against
`shopify.dev` (2026-07-19, API 2026-07) beyond the accepted Gate A
capture: `inventoryActivate`'s omitted-quantity zero default, and its
`userErrors` shape (plain `UserError` — no dedicated error-code enum,
unlike `inventorySetQuantities`) — both folded into the matrix with an
explicit fail-closed default for the one genuinely open classification
question, deferred to dev-store verification (scenario 8), not silently
assumed.

**Status: DEC-037 PROPOSED FOR CONTROL-ROOM GATE B ACCEPTANCE. Task 013
packet: GATE B ACCEPTANCE CANDIDATE — NOT IMPLEMENTATION AUTHORIZED. Task
013B packet: GATE B ACCEPTANCE CANDIDATE — NOT IMPLEMENTATION
AUTHORIZED. Both locked Sol prompts: LOCKED, unissued. Claude did not
accept its own package — no self-acceptance act occurred.** No
`addons/**` file was created or modified. No Odoo/Odoo.sh run occurred.
No Shopify mutation was issued (two Shopify **reads** only, for the
narrow official-source verification above). Task 013 implementation
remains forbidden until this Gate B package is accepted and merged
**and** Stage 0 is separately merged and runtime-proven, per PR #177
comment `5015174971`'s sequencing guard; Task 013B additionally requires
Task 013 itself merged and runtime-proven. PR #179 remains **open, draft
and unmerged**; this session performed no merge, no ready-marking.
**Recommendation: READY FOR CONTROL-ROOM WAVE 3 GATE B REVIEW.**

**WAVE 3 GATE A ACCEPTED — CONTROL-ROOM ACCEPTANCE ACT COMPLETE; ACCEPTANCE/CLOSURE COMMIT AUTHORIZED FOR MERGE (2026-07-19, draft PR [#177](https://github.com/AdamsOdoo/Adams/pull/177)).**
Following the final mechanical Gate A consistency correction below (2026-07-19,
PR #177 comment
[`5014806430`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014806430)),
the control room accepted the complete Gate A package — the full DEC-036
D1–D38 decision set, the corrected DEC-031 Layer 2 design, the Stage 0
implementation packet, and the Wave 3 Gate A portion of the Definition of
Ready — by PR #177 comment
[`5015044226`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5015044226)
("Control-room final Gate A decision — ACCEPTED WITH TWO CLERICAL
MERGE-CLOSURE CONDITIONS"). **DEC-036: ACCEPTED — CONTROL-ROOM GATE A.
DEC-031 Layer 2 design: ACCEPTED through DEC-036 D1–D38. Stage 0 packet:
ACCEPTED — IMPLEMENTATION PROMPT NOT YET ISSUED. Locked Sol prompt: LOCKED,
unissued, ready for separate control-room issuance only after PR #177
merges and the new `mvp/program-integration` integration SHA is verified.
Wave 3 DoR: GATE A ACCEPTED; GATE B NOT STARTED; STAGE 0 IMPLEMENTATION NOT
YET STARTED.** Two clerical merge-closure conditions (the DoR gate-table
wording; the Stage 0 packet §4 addendum sentence) were applied in the same
acceptance/closure commit that recorded this acceptance. **No architecture
decision was reopened. No implementation authorized. No `addons/**` file
changed. No Odoo/Odoo.sh run. No Shopify request or mutation performed.**
Stage 0 implementation and Gate B may begin only after PR #177 merges into
`mvp/program-integration` and the new integration tip is independently
verified — neither has started.

**WAVE 3 GATE A CORRECTION BATCH APPLIED — DEC-036 ZERO REMAINING ARCHITECTURE BLOCKERS, NOT YET ACCEPTED — READY FOR FINAL CONTROL-ROOM GATE A REVIEW (2026-07-19, draft PR [#177](https://github.com/AdamsOdoo/Adams/pull/177)).**
Following the 2026-07-18 Gate A session below, the control room issued a
preliminary review (PR #177 comment
[`5013028262`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5013028262))
and then a final consolidated ruling reconciling an independent official-source
audit ("Session 2") and an independent adversarial architecture audit
("Session 3") — PR #177 comment
[`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445).
This session (Session A) applied every binding decision from that ruling in
one documentation-only correction batch across the same ten allowed files.
**Result: all eight items DEC-036 previously carried as explicitly
BLOCKING are now resolved** — `mutation_attempt.job_id` (Many2one-restrict)
and C2's cursor placement (dedicated side cursor); the
open-transaction-vs-network-call question (resolved by construction); the
disconnect-quiescence interaction (resolved to an awareness-based design,
not a timeout race); `mutation_domain`'s field ownership (resolved to a
registry-validated indexed `Char` — a third option the original framing
omitted); the N=3 inconclusive-cap's persistence scope (resolved
per-attempt-sufficient); the AST-tooling-maturity contradiction
(reclassified as implementation sizing, not a blocker); and the
runtime/concurrency/crash-injection proof requirement (resolved to four
proof-environment layers, correctly classified as a Stage 0
merge-acceptance criterion, not a precondition to beginning
implementation). Additional corrections: the observed-outcome/resolution
model is now genuinely orthogonal (`observed_outcome` immutable once it
leaves `pending`); the unsafe single fingerprint is split into
`business_intent_fingerprint`/`exact_request_fingerprint` (the latter
including `changeFromQuantity`); two idempotency defect codes route to
fail-closed manual review instead of auto-retry; retention is now
indefinite-for-unresolved plus configurable-masking-for-resolved; and
security installs against the current four-role model (Session 3's
proposal to install against the future two-role model is rejected), with
an explicit SEC-2 re-key obligation. Session 3's proposed single six-value
outcome enum is also rejected. **DEC-036 status: CONTROL-ROOM ACCEPTANCE
CANDIDATE — CORRECTIONS APPLIED, NOT YET ACCEPTED.** Full reconciliation
record: DEC-036 Part 0.5. **No implementation authorized. No `addons/**`
file changed. No Odoo/Odoo.sh run. No Shopify request or mutation
performed.** PR #177 remains **open, draft and unmerged**; this session
performed no merge, no ready-marking, and did not accept its own decision
package. **Wave 3 implementation remains unstarted.** Protected refs
confirmed unchanged before, during, and after this correction batch.
Recommendation: **READY FOR FINAL CONTROL-ROOM GATE A REVIEW.**

**WAVE 3 GATE A ACTIVE — DEC-031 LAYER 2 ACCEPTANCE CANDIDATE + STAGE 0 PACKET, NOT YET ACCEPTED (2026-07-18, draft PR [#177](https://github.com/AdamsOdoo/Adams/pull/177)).**
**Wave 2 is MERGED** — PR #176 merged into `mvp/program-integration` with
merge commit `22bfb9a0e9b1e48b6a664351e2b321d134177110`. **Wave 2 checkpoint
created:** `checkpoint/wave-2-order-import-2026-07-18` =
`22bfb9a0e9b1e48b6a664351e2b321d134177110`. **Current
`mvp/program-integration` integration tip at Gate A's start:**
`aa87ccc971eb9ab500911948e0e751136453cbc2` — this session (Session A)
independently verified **zero tree difference** between that tip and the
Wave 2 checkpoint; the four commits between them
(`923a84d`/`804494f`/`451598b`/`aa87ccc`) are exactly two accidental
temporary-file add/revert pairs, confirmed to leave no residue. This
session created branch `claude/wave-3-gate-dec-031-layer2-q3vwfj` from
that exact tip and opened early draft PR #177.

This session performed a 27-agent code/documentation audit, official-source
refresh, and adversarial review of the full DEC-031 Layer 2 proposed
design, producing
[`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) (a complete,
gap-free `L2-D1`–`L2-D38` decision inventory — status **PROPOSED FOR
CONTROL-ROOM ACCEPTANCE, NOT YET ACCEPTED**), a corrected
[Layer 2 design document](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
(still status Proposed), a
[Wave 3 Stage 0 implementation packet](wave-3-stage-0-layer-2-packet.md)
(status **PROPOSED — LOCKED PROMPT NOT ISSUED**), and a locked (not issued)
[Sol Stage 0 prompt](../06-prompts/sol-wave-3-stage-0-locked-prompt.md).
Mid-session, a control-room parallel-audit ruling landed on PR #177 comment
[`5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989),
correcting eight points (isolation level — Odoo 19 uses PostgreSQL
`REPEATABLE READ`, not Read Committed; the CAS field name
`changeFromQuantity`; `THROTTLED` fail-closed treatment; a one-pair-per-request
batching default; a clean-cursor invariant requirement; explicit `sudo()`-based
security guards rather than unresolved field-`groups=` behavior; and an
explicit "package not frozen" instruction pending a separately-tracked
"Session C" code/architecture audit this session cannot access). Every
point is independently re-verified (not merely accepted) against primary
sources — see
[`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md)
— and incorporated into DEC-036 and the design-doc corrections. **Eight
DEC-036 decisions remain explicitly BLOCKING** (job_id field type + C2
cursor placement; open-transaction-vs-network-call proof;
disconnect-quiescence/sweep-timeout interaction; `mutation_domain` field
ownership; N=3 inconclusive-cap persistence scope; AST-tooling-maturity
contradiction; the full three-layer runtime/concurrency/crash-injection
proof plan) — each requires an explicit control-room decision or empirical
verification not available from documentation alone. **No implementation
authorized. No `addons/**` file changed. No Odoo/Odoo.sh run. No Shopify
request or mutation performed.** PR #177 remains **open, draft and
unmerged**; this session performed no merge, no ready-marking, and did not
accept its own decision package (DEC-036/the Stage 0 packet/the locked
prompt are all explicitly not-self-accepted, per this session's own
governing rule). **Wave 3 implementation remains unstarted.** Protected
refs (`main` `a5d45432a9b60f724c1aff700f4b371ea019960e`, `Shopify-connector`
`dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`,
`checkpoint/core-r2-readonly-uat-2026-07-15` `acd8c4691e72cf5590f2a56228b08f183b76cd9a`,
`checkpoint/wave-2-order-import-2026-07-18` `22bfb9a0e9b1e48b6a664351e2b321d134177110`)
confirmed unchanged before and during this session.

**WAVE 2 EXACT-HEAD RUNTIME CAMPAIGN 4 EXECUTED — GREEN — READY FOR FRESH CLAUDE FINAL WAVE REVIEW (2026-07-18, build `35100725`, control-room authorization [`5011632937`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5011632937)).** The sole authorized runtime SHA `63607dd87a8bfc253ee60ed00e0d761ee62c8776` (correction commit mirroring the country-consistent tax + tax-group fixture from `6f32e4c` into `test_order_totals_guard.py._map_tax`; base `234c0bb`; 29 changed files; `6f32e4c` and Campaign-3 evidence `31419b7` in ancestry; no commit after the authorized SHA) was independently runtime-validated on authenticated Odoo.sh build `35100725` (DB `adamsmen-sol-wave-2-order-import-35100725`, Odoo 19.0, PostgreSQL 16.14; modules core `19.0.1.9.1` / product `19.0.2.1.2` / sale `19.0.2.0.0`, account `19.0.1.4`). **The clean/full fresh install with tests enabled is GREEN:** the build's own install-with-tests (`install.log`) recorded **`0 failed, 0 error(s) of 728 tests`** (per-module stats core 414 / product 202 / sale 232, all 0/0). **All three Campaign-3 `TestOrderTotalsGuard` errors are CLOSED** — targeted re-execution of `TestOrderTotalsGuard`+`TestOrderTaxResolution` returned `0 failed / 0 error of 19`, with `test_order_and_source_tax_fingerprints_must_reconcile` and `test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` (`included=False`/`included=True`) all green; **finding #5 is now fully closed in both `_tax()` and `_map_tax()`** (both self-assert country-consistent company/country/tax-group). The complete Wave 2 inventory (86 methods = 84 standard + 2 custom-tag concurrency) executed with no silent exclusion; genuine independent-connection concurrency (`TestOrderDiscoveryConcurrencyGenuine`) passed **3/3** (`0/0/2` each); residue (0 idle-in-tx / 0 blocked locks / 0 advisory locks / 0 orphans / 0 stray workers), credential/PII/log redaction (no token/PII/connection-string/payload leakage), ACL (12 sale rows, no unlink any role, tax-mapping admin-only create/write), and registry (23 models, 1 order-scan cron, SQL constraints present, no duplicate XML IDs) are all clean; the single build warning is a test-induced negative-path scan `UserError` (non-blocking). The warm-`-u` `res_partner.autopost_bills` NOT-NULL `setUpClass` errors (core 8 / product 2) are **base-`account` warm-rerun artifacts** (`account/models/partner.py:608`, `Selection(default='ask', required=True)`, NOT-NULL column, no DB default; zero connector references), **absent from the authoritative fresh install**, precisely attributed, and do not mask any connector defect. The isolated baseline-upgrade (B) and uninstall/reinstall lifecycle (C) databases are **deferred release-readiness evidence — NOT a Campaign-4 blocker** (single-injected-DB container); read-only Shopify dev-store evidence is deferred to Wave 6; **no Shopify mutation** was performed. Full evidence: [`../05-qa/task-012-campaign-4-exact-head-runtime-evidence.md`](../05-qa/task-012-campaign-4-exact-head-runtime-evidence.md). **Recommendation: READY FOR FRESH CLAUDE FINAL WAVE REVIEW.** The auditor changed no production or test code and made no Shopify mutation. Runtime-tested SHA `63607dd87a8bfc253ee60ed00e0d761ee62c8776`; evidence commit SHA recorded at commit time. **PR/protected-ref limitation:** no `gh`/token in this container (GitHub API `404` unauthenticated), so PR #176 draft/unmerged state and protected-ref state are asserted from local git only; the auditor performed no push to protected refs, no merge, no ready-marking. PR #176 remains **open, draft and unmerged**; the protected checkpoint `checkpoint/core-r2-readonly-uat-2026-07-15` = `acd8c469…` is unchanged; SRR-03 remains CLOSED; **Wave 3 remains unstarted.** This entry supersedes the Campaign-3 entry immediately below (retained verbatim as historical evidence, together with all earlier campaigns).

**WAVE 2 CORRECTED-HEAD RUNTIME CAMPAIGN 3 EXECUTED — CORRECTION REQUIRED (2026-07-18, build `35095228`, revised control-room ruling [`5010851668`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010851668)).** The sole authorized runtime candidate `2525447cee2d8a3371b1f4e669f61bcd50b20162` (documentation head reconciling fixture correction `6f32e4c8a2e6eac44bfb32e2cca0ea2bea3b1ea4`; base `234c0bb`; 29 changed files; no commit after the authorized SHA at campaign start) was independently runtime-validated on authenticated Odoo.sh build `35095228` (DB `adamsmen-sol-wave-2-order-import-35095228`, Odoo 19.0, PostgreSQL 16.14; modules core `19.0.1.9.1` / product `19.0.2.1.2` / sale `19.0.2.0.0`). **The clean/full fresh install with tests enabled is NOT green:** the build's own install-with-tests (`install.log`) recorded **`0 failed, 3 error(s) of 728 tests`** — all three in `TestOrderTotalsGuard` (`test_order_and_source_tax_fingerprints_must_reconcile`; `test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes` sub-cases `included=False`/`included=True`), each an `account_tax.tax_group_id`/`country_id` NOT-NULL violation raised by the test's own `_map_tax()` helper, which creates `account.tax` without an explicit country-consistent tax group. **Root cause: the accepted fixture correction `6f32e4c` fixed this exact country-consistent-tax-fixture defect in `test_order_tax_resolution.py` only (that commit touched only that one file, +47/-3) and left the identical pattern unpatched in the sibling `test_order_totals_guard.py`.** `TestOrderTaxResolution` now passes at fresh install — so **finding #5 is closed there but NOT fully closed** (OPEN in `test_order_totals_guard.py`). Genuine independent-connection concurrency (`TestOrderDiscoveryConcurrencyGenuine`, custom tag) passed **3/3** (`0/0/2` each); residue (0 idle-in-tx / 0 advisory locks / 0 orphans / 0 stray workers), security/redaction (no token/PII/connection-string leakage) and registry (1 order-scan cron, 12 sale ACL rows, no duplicate XML IDs) are clean; the warm-`-u` `res_partner.autopost_bills` NOT-NULL errors (core 8 / product 2) are base-`account` warm-rerun artifacts **absent from the authoritative fresh install** and not connector-attributable. **Under revised ruling `5010851668`, the isolated baseline-upgrade (B) and uninstall/reinstall lifecycle (C) databases are deferred release-readiness evidence — NOT Wave 2 blockers and NOT ENVIRONMENT BLOCKED**; the Wave 2 acceptance gate is the complete authenticated Odoo.sh clean/full matrix, which is not green. Full evidence: [`../05-qa/task-012-order-import-validation-results.md`](../05-qa/task-012-order-import-validation-results.md) "Corrected-head runtime validation campaign 3 — 2026-07-18 (build `35095228`)". **Recommendation: CORRECTION REQUIRED** (Sol test-fixture scope: mirror the `6f32e4c` country-consistent tax + tax-group construction into `test_order_totals_guard.py._map_tax`, and audit any other fixture creating `account.tax` without explicit `country_id`/`tax_group_id`). The auditor changed no production or test code and made no Shopify mutation. Runtime-tested SHA `2525447…`. **PR/protected-ref limitation:** no `gh`/token in this container (GitHub API `404` unauthenticated), so PR #176 draft/unmerged state and protected-ref state are asserted from local git only; the auditor performed no push to protected refs, no merge, no ready-marking. PR #176 remains **open, draft and unmerged**; SRR-03 remains CLOSED; **Wave 3 remains unstarted.** This entry supersedes the two earlier 2026-07-18 entries below (both retained verbatim as historical evidence, together with the 2026-07-17 first campaign).

**WAVE 2 TAX-FIXTURE CORRECTION COMMITTED — DOCUMENTATION RECONCILED — RUNTIME NOT AUTHORIZED PENDING B/C ENVIRONMENT VERIFICATION (2026-07-18, HISTORICAL — SUPERSEDED BY CAMPAIGN 3 ABOVE, WHICH RUNTIME-VALIDATED THE CORRECTED HEAD AND FOUND THE CORRECTION INCOMPLETE IN `test_order_totals_guard.py`).** The second corrected-head runtime campaign (SHA `d1af6d03e3c51b9fa3d12dad00fd7c7766ec8bd5`, Odoo.sh build `35088811`, database `adamsmen-sol-wave-2-order-import-35088811`, recorded in full immediately below) closed ten of the eleven original findings at runtime; the tax country fixture in `TestOrderTaxResolution._tax()` remained defective (missing a non-null, company-consistent `account.tax.country_id`). The accepted test-fixture-only correction is now committed at `6f32e4c8a2e6eac44bfb32e2cca0ea2bea3b1ea4` (control-room ruling [`5010554056`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010554056)), and this Claude control-room session completes the required documentation-only reconciliation (this file, the Task 012 validation record, and the research handoff) authorized by ruling [`5010654351`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5010654351). **No production code changed** — `shopify_connector_tax_mapping.py` and `shopify_connector_order_importer.py` remain byte-identical to evidence head `0649ff2`. **No post-correction Odoo.sh runtime pass exists.** This session performed an environment-capability audit only (no Odoo, PostgreSQL, or destructive action executed) and found no usable multi-database Odoo 19/PostgreSQL 16.14 runner available in this checkout: no reachable PostgreSQL server (port 5432 refused), no running container/Docker daemon, and no Odoo package or source present. **No SHA is currently runtime-authorized** until this documentation commit is stable and both isolated baseline-upgrade (Environment B) and isolated lifecycle (Environment C) capability are positively verified in a suitable environment; Environment A (clean/full) is known from the two preserved campaigns below and must not be spent alone again. PR #176 remains **open, draft and unmerged**; Wave 3 remains unstarted. This entry supersedes the immediately-following `CORRECTION REQUIRED` (2026-07-18) entry, which is retained verbatim below as historical evidence, together with the first (2026-07-17, build `35080469`) campaign.

**WAVE 2 CORRECTED-HEAD RUNTIME CAMPAIGN EXECUTED — CORRECTION REQUIRED (2026-07-18, HISTORICAL — SUPERSEDED BY THE TAX-FIXTURE-CORRECTION ENTRY ABOVE).** The sole authorized corrected runtime candidate `d1af6d03e3c51b9fa3d12dad00fd7c7766ec8bd5` (PR #176 head; base `234c0bb`; 29 changed files; correction commits `5897396`/`e4a75fc`/`6624028`/`3223741`/`7bd6df9`/`d1af6d0` all present) was runtime-validated on authenticated Odoo.sh build `35088811` (DB `adamsmen-sol-wave-2-order-import-35088811`, Odoo 19.0, PostgreSQL 16.14; modules core `19.0.1.9.1` / product `19.0.2.1.2` / sale `19.0.2.0.0`). **Environment A (clean/full) completed; the fresh install with tests enabled is NOT green:** `shopify_connector_sale` fails on `TestOrderTaxResolution` with `account_tax.country_id` NOT-NULL violations (build install: 5 errors, halted at cap 5; warm no-halt re-run: `0 failed / 1 error of 194`). Root cause: the `_tax` fixture adds `tax_group_id` (the prior correction) but still omits the Odoo-19-required `country_id` — **prior finding #5 is only partially closed** (test-fixture / Odoo-19-compat defect; production is unaffected — no `account.tax` auto-creation). **The other ten prior findings (#1–4, #6–11) are confirmed closed at runtime.** Concurrency `TestOrderDiscoveryConcurrencyGenuine` ×3 = green; 3 permanent unique constraints, 12 ACL rows, exactly one sale cron, no duplicate XML IDs, store-setting defaults, residue, credential/PII and network-free/no-mutation audits all clean; the core/product warm-re-run `res_partner.autopost_bills` setUpClass errors are a base-Odoo issue-#157-family environment artifact (absent at fresh install), not a Wave 2 defect. **Environments B (isolated baseline-upgrade) and C (isolated lifecycle) could not be prepared** in this single-injected-database container (AGENTS.md single-DB constraint; restricted PostgreSQL privileges) — ENVIRONMENT BLOCKED for the upgrade/lifecycle matrix. Full evidence: [`../05-qa/task-012-order-import-validation-results.md`](../05-qa/task-012-order-import-validation-results.md) "Corrected-head runtime validation campaign — 2026-07-18". **Recommendation: CORRECTION REQUIRED** (Sol adds `country_id` to the `_tax` fixture; B/C rerun in a multi-DB environment). The auditor changed no production or test code and made no Shopify mutation. PR #176 remains **open, draft and unmerged**; SRR-03 remains CLOSED; **Wave 3 remains unstarted.** This entry does not overwrite or reclassify the first (2026-07-17, build `35080469`) failed campaign, which is preserved as historical evidence.

**WAVE 2 DOCUMENTATION RECONCILIATION COMPLETE — CORRECTED-HEAD RUNTIME PENDING (2026-07-17).** The first Wave 2 exact-head runtime campaign ran against frozen candidate `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8` on authenticated Odoo.sh build `35080469` (database `adamsmen-sol-wave-2-order-import-35080469`) and returned `shopify_connector_sale` **5 failures / 6 errors** (11 unique findings); `shopify_connector_core` and `shopify_connector_product` were green. That failed result is preserved as historical evidence, not erased or reclassified, in [`../05-qa/task-012-order-import-validation-results.md`](../05-qa/task-012-order-import-validation-results.md). Binding control-room rulings [`5006941549`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5006941549), [`5007682381`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5007682381), [`5008012338`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008012338) and [`5008123769`](https://github.com/AdamsOdoo/Adams/pull/176#issuecomment-5008123769) adjudicated all eleven findings and authorized this documentation reconciliation. The accepted correction commits — `589739667e0e575ee434cd541277bfdbcc54c5e5`, `e4a75fc49af622ba908d5a9f15e7272030c2379b`, `662402849401df604f048afd78953c06a6d956a0`, and `32237410b45c37f92f80fc07d43ddd6541d6134d` (docs freeze) — are committed on `sol/wave-2-order-import`, and this Claude control-room commit completes the required documentation-only reconciliation across the tracker, Task 012 validation record, acceptance matrix and research handoff. **All eleven runtime findings now have accepted and committed dispositions; production and test corrections are complete.** Corrected-head runtime validation is **pending** — no corrected-head Odoo pass is claimed. The clean/full, isolated-upgrade and isolated-lifecycle environments remain mandatory for the next independent runtime campaign (see the required rerun matrix in PR #176's body). PR #176 remains **open, draft and unmerged**; SRR-03 remains CLOSED; **Wave 3 remains unstarted.**

**WAVE 2 EXACT-HEAD RUNTIME CAMPAIGN EXECUTED — CORRECTION REQUIRED (2026-07-17, HISTORICAL — SUPERSEDED BY THE RECONCILIATION ENTRY ABOVE).** The frozen runtime candidate `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8` was runtime-validated on authenticated Odoo.sh build `35080469` (database `adamsmen-sol-wave-2-order-import-35080469`, Odoo 19.0, PostgreSQL 16.14). Fresh install with tests enabled is green and the registry/constraints/crons/ACLs/defaults all verify. `shopify_connector_core` (0/0) and `shopify_connector_product` (0/0) are green; the two genuine independent-connection order-discovery concurrency tests pass 3/3 repetitions; residue, credential/PII and log audits are clean; no Shopify egress or mutation occurred. **`shopify_connector_sale` standard suite = 5 failed / 6 errors of 194** — 11 unique failures, classified as **8 test-harness defects** (Odoo-19 fixture incompatibilities, an over-broad inherited Wave-1 source guard, a wrong-state job fixture, and four backfill positive-path calls not made as Administrator) plus **3 production-vs-test contract questions** (address `company`→`company_name` mapping; tax-fingerprint `source=None` vs `''` collision; partial-page resumability vs transactional rollback). No confirmed production defect. Full evidence: [`../05-qa/task-012-order-import-validation-results.md`](../05-qa/task-012-order-import-validation-results.md) and [`../05-qa/task-area6-order-scan-validation-results.md`](../05-qa/task-area6-order-scan-validation-results.md). Baseline-upgrade (§4) and isolated uninstall/reinstall (§10) are environment-constrained (single injected DB, no second-DB capability) and deferred; issue #157 did not reproduce; read-only dev-store evidence deferred to Wave 6. The runtime operator changed no source or test code — correction of the failures and adjudication of the 3 contract questions is Sol-worker implementation scope under DEC-032 / CLAUDE.md §13. Failed SHA `2e1b1eb…`; corrected SHA to be recorded by the corrector after a corrected-head rerun. PR #176 remains **open, draft and unmerged**; SRR-03 remains CLOSED; Wave 3 remains unstarted. **This entry is retained verbatim for audit history — do not read it as current; see the reconciliation entry above for current status.**

**WAVE 2 PRE-RUNTIME AUDIT COMPLETE / RUNTIME CANDIDATE FROZEN (2026-07-17).** Draft PR [#176](https://github.com/AdamsOdoo/Adams/pull/176) remains open, draft and unmerged on `sol/wave-2-order-import`. Starting head `c62303611e7c5337e08d1632d0541be55df248ba` was identity-clean against merge base `234c0bb50b3f61b7681e18f0b28839dee619cdb9`. A complete contract/code/test/install/security audit corrected the permanent-binding and enqueue collision loser paths, strengthened exact negative and concurrency proof, and made connector-only Reviewer/Admin manual approval deterministic through one exact two-field linked-quotation read. All available static checks are green; 86 unique tests are authored, but no Odoo test pass or build is claimed. The exact runtime candidate is the final documentation commit of this audit and is recorded in PR #176. SRR-03 remains CLOSED; Wave 3 remains unstarted.

**WAVE 0 MERGED (2026-07-15).** PR #169 merged into `mvp/program-integration` (merge commit `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`, per the Wave 0 closure comment on issue #167). DEC-033 is Accepted with two minor corrections applied on PR #169 (Wave 1 internal sub-stage note; hard-stop 11 rewording). DEC-028/029/030 are Accepted; DEC-027 remains Proposed/Deferred. PR #150/#151 administrative closure as superseded is authorized to proceed.

**WAVE 1 MERGED (2026-07-16).** PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) merged into `mvp/program-integration` with a normal merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6` (reviewed head `d7b08e6d4a84af1a15b498068205c8ee6d510ea5`; runtime-tested SHA `95db3dba4bf295ca6c6ee94ae7fa08da1d505eb7`; runtime-evidence commit `8a3104f892fa0bdf256e17a57933a7dcbb9db0c5`). Corrected-head Odoo.sh build `34995642` ran the complete matrix green (full standard suite `0 failed / 0 errors / 644`; clean residue/security; issue #157 accommodation dropped/restored). Final Claude control-room review: 20-point independent verification against production code with adversarial adjudication on every non-clean-pass finding; two documentation-only claim-accuracy defects were found and corrected in the PR's final commit (`d7b08e6`) — no code, test, or security defect found. **Decision: ACCEPTED AND MERGED. SRR-03 remains CLOSED. Wave 2 remains unauthorized and unstarted.** The next authorized activity is the separate Wave 2 decision-acceptance / Definition-of-Ready / packet re-acceptance / exact-base preflight session (the one-time Fable remaining-gap-closure mission is now **complete** — PR #173 merged 2026-07-17, merge commit `0fb8ccb`).

**FABLE GAP-CLOSURE MERGED (2026-07-17).** PR [#173](https://github.com/AdamsOdoo/Adams/pull/173) — the one-time remaining-gap research/product/architecture/UX/QA/Waves-2–6-readiness mission — was reviewed by the Claude control room and merged into `mvp/program-integration` with a normal merge commit `0fb8ccbe8ce54404a57260f82e8226ffa7e6bf73` (reviewed head `68c159f2a46b9d0c82ab5ec19da42eca1b5eed04` = starting head `09078a8` + one docs-only reconciliation commit; 127 files, all under `docs/**`; no `addons/**` change). Decisions: **Class A confirmed; Class B (PD-B1..B7) all decided (B1 pending-expiry 24 h default; B4 mode-switch scan boundary; B5 Mode-1-outbound = Full); Class C (TA-C1..C8) decided or routed — DEC-031 Layer 2 NOT DEC-accepted (routed to a dedicated pre-Wave-3 architecture gate); Class D fail-closed classified; Class E post-MVP.** Full record: [`../04-decisions/fable-proposed-decision-pack.md`](../04-decisions/fable-proposed-decision-pack.md) §Control-room decisions (2026-07-17); [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md) AR-053; [`../01-research/research-handoff.md`](../01-research/research-handoff.md) top entry. **No implementation authorized; Wave 2 remains unauthorized and unstarted; protected refs unchanged.**

**WAVE 2 GATE ACCEPTED AND MERGED (2026-07-17).** PR [#174](https://github.com/AdamsOdoo/Adams/pull/174) — the Wave 2 decision-acceptance +
Definition-of-Ready + Task 012/Area-6 packet re-acceptance + exact-base
preflight session — was reviewed by the Claude control room and merged into
`mvp/program-integration` with a normal merge commit
`f62197b9281d6e18e4f1861d0e327738b4c3d510` (reviewed head
`637a02fdb48ca9c3f0a3463ee10335e9bfc7e25e`; base `a34c68e84aada288dad3dc22a6afe94f5ace0652`,
merge-base = base, no divergence; 9 files, all under `docs/**`; no
`addons/**` change). The Wave 2 Definition of Ready, the Task 012 packet
(with its 2026-07-16 addendum), and the Area-6 order-scan slice (order
domain only) are all **Accepted**. Every open question is closed or
non-blockingly deferred per
[`../04-decisions/DEC-035-wave-2-open-question-dispositions.md`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md).
**Wave 2 is AUTHORIZED TO START. Wave 2 implementation has NOT started** —
no branch, no code, no implementation PR exists yet. The next authorized
activity is issuing the locked Sol prompt at
[`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md)
with this SHA (or the then-current live tip, re-verified) as the starting
point. See the Sprint checkpoint log below for the full gate-closure record.

**WAVE 2 GATE CORRECTION MERGED (2026-07-17, same day).** PR
[#175](https://github.com/AdamsOdoo/Adams/pull/175) — the docs-only
correction of eight post-merge contract contradictions found in PR #174
(comments `5000101837`/`5000111557`: tax-auto-create test wording, missing
`order_scheduled_sync_enabled` field, model-registration count error, wrong
tax-mapping ACL pattern, undefined manual-gateway-approval backend
contract, stale tip/metadata test wording, unsafe rollback narrative,
unfilled issuance-SHA placeholder) — was reviewed by the Claude control
room and merged into `mvp/program-integration` with a normal merge commit
`a54e4a0699ba0426642fd753da581e3712e57177` (reviewed head
`aad19b07c884d6a4548604e5fb38acccedbe0644`; base
`751e50bfe38d1bbbcf586f87a8b256cc098525ed`, merge-base = base, no
divergence; 7 files, all under `docs/**`; no `addons/**` change). Full
record: [`DEC-035`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md)'s
"Correction addendum (2026-07-17)". **Wave 2 is (again) AUTHORIZED TO
START. Wave 2 implementation has NOT started** — no `sol/wave-2-order-import`
branch or implementation PR exists. The next authorized activity is
issuing the locked Sol prompt at
[`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md)
with the live `mvp/program-integration` tip (this merge commit, or the
then-current tip if further `docs/**` commits land first) substituted for
`<EXACT_SHA_AT_ISSUANCE>`.

Freeze/resume status: **the issue #165 implementation freeze is lifted only for work authorized by DEC-032 and the master Sol mission, on branches descending from `mvp/program-integration`.** The product owner launched Sol on 2026-07-15 by issuing the complete master mission. Wave 0 is documentation/research only; no addon code was authorized in that wave. **Wave 1 is merged** (PR #172, merge commit `d18f9a9`) — all five stages (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure) are implementation-complete and were runtime-proven at the corrected head (build `34995642`, runtime-tested SHA `95db3db`, `0 failed / 0 errors / 644`) before merge. **Wave 2's gate is now Accepted** (2026-07-17) and Wave 2 is authorized to start; it may not merge, be enabled, or receive live Shopify validation until Sol's own implementation wave passes its control-room wave review. SRR-03 itself remains **CLOSED** on its independently verified build `34986844` evidence.

## Checkpoint / integration identity

| Field | Value |
| --- | --- |
| Checkpoint SHA | `acd8c4691e72cf5590f2a56228b08f183b76cd9a` |
| Checkpoint branch | `checkpoint/core-r2-readonly-uat-2026-07-15` |
| Program integration branch | `mvp/program-integration` |
| Bootstrap governance merge SHA | `f7950e68ff4bb085deaef82563aff25bda6b8545` (PR #166 merge; checkpoint + governance bootstrap only) |
| Tracker-upkeep commit | `06600811d664f5e1fee9ee2cb86e6c81f9c8a83e` (routine tracker upkeep recording PR #166/#167; not new governance content) |
| Bootstrap branch / PR | `claude/mvp-control-room-bootstrap-39nip0` → PR [#166](https://github.com/AdamsOdoo/Adams/pull/166), merged |
| Master program issue | [#167](https://github.com/AdamsOdoo/Adams/issues/167) |

> **No SHA in this table is the live tip.** `mvp/program-integration` advances with every merge — including routine tracker-upkeep commits to this file — so any "current SHA" recorded here becomes stale the moment it is committed. Every new session must verify the live `mvp/program-integration` tip directly from GitHub before relying on it.

## Active wave

**Wave 2 CORRECTION BATCH COMPLETE; DOCUMENTATION RECONCILIATION FINALIZED, CORRECTED-HEAD RUNTIME PENDING (2026-07-17).** Sol implemented Task 012 and the accepted Area-6 order-scan slice on `sol/wave-2-order-import` in draft PR [#176](https://github.com/AdamsOdoo/Adams/pull/176). The first independent exact-head runtime campaign ran against `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8` on Odoo.sh build `35080469` and returned `shopify_connector_sale` 5 failures / 6 errors (11 unique findings); that failed result is preserved as historical evidence, not erased. Under binding control-room rulings `5006941549`, `5007682381` and `5008012338`, Sol implemented the complete correction batch across commits `589739667e0e575ee434cd541277bfdbcc54c5e5`, `e4a75fc49af622ba908d5a9f15e7272030c2379b` and `662402849401df604f048afd78953c06a6d956a0`, and this Claude control-room commit completes the required documentation-only reconciliation (this file, `../05-qa/task-012-order-import-validation-results.md`, `../05-qa/mvp-acceptance-matrix.md`, `../01-research/research-handoff.md`) authorized by ruling `5008123769`. The exact new post-reconciliation branch head becomes the sole authorized corrected runtime candidate — see PR #176's body for that exact SHA. No corrected-head Odoo.sh pass exists yet; the required clean/full, isolated-upgrade and isolated-lifecycle runtime matrix remains mandatory and unrun. The PR remains draft and is not mergeable/acceptable yet; the bounded exact-head runtime matrix is handed to an independent operator next. SRR-03 remains CLOSED from Wave 1; no Shopify mutation, DEC-031 Layer 2, or Wave 3+ implementation exists; **Wave 3 remains blocked** pending corrected-head runtime acceptance.

## Wave status

| Wave | Status | Branch/PR | Notes |
| --- | --- | --- | --- |
| 0 — Reconciliation & research closure | **Merged** | `sol/wave-0-reconciliation-research`; PR [#169](https://github.com/AdamsOdoo/Adams/pull/169) (merged, `a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`) | DEC-033 accepted with minor corrections; DEC-028/029/030 accepted; DEC-027 deferred; no addon/protected changes. |
| 1 — Read-only foundation integration (CORE-R1, LC-1, JOB-ACTIONS, SEC-1, SRR-03 closure) | **MERGED (2026-07-16)** | `sol/wave-1-readonly-foundation`; PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) (merged, `d18f9a9997d7da574f629f834e2adb83b492cfc6`) | Commit `36974edc68c1985e6ccfae8f6bb5c7386f820156` closed the complete binding mutation surface under ruling `4988842625`. Corrected-head build `34995642` (runtime-tested SHA `95db3db`) ran the complete matrix `0/0/644`; residue/security clean; #157 dropped/restored. Final Claude control-room review (20-point independent verification, adversarial adjudication) accepted and merged the reviewed head `d7b08e6`. SRR-03 CLOSED. |
| 2 — Order import (Task 012 + Area-6 order-scan slice) | **Implementation and runtime-correction batch complete; first runtime campaign failed (preserved) and is superseded by committed corrections; corrected-head runtime rerun pending (2026-07-17)** | `sol/wave-2-order-import`; draft PR [#176](https://github.com/AdamsOdoo/Adams/pull/176) | First campaign: SHA `2e1b1eb`, build `35080469`, 5 failed / 6 errors (preserved). All eleven findings dispositioned and committed (`5897396`, `e4a75fc`, `6624028`); documentation reconciliation complete. 86 tests authored, none removed/skipped/weakened; no corrected-head runtime pass claimed. Clean/full, isolated-upgrade and isolated-lifecycle proof pending/mandatory. PR stays draft/unmerged; Wave 3 remains blocked. |
| 3 — Inventory synchronization (Task 013/013B) | **Gate A ACCEPTED and MERGED (2026-07-19); Gate B ACCEPTED (comment `5016117207`) and merge-authorized, merge-closure normalization applied, merge pending/executed on PR #179 (see the Current status entry at the top of this file for the exact merge SHA once landed); Stage 0 implementation in progress on a Sol branch with an open draft PR, not merged, not runtime-proven, held pending post-merge sync** | Gate A: merged PR [#177](https://github.com/AdamsOdoo/Adams/pull/177) (docs-only). Gate B: PR [#179](https://github.com/AdamsOdoo/Adams/pull/179) (docs-only, ACCEPTED, comment `5016117207`). Stage 0: draft PR [#178](https://github.com/AdamsOdoo/Adams/pull/178) (`sol/wave-3-stage-0-layer2`, head `644853a68b3497c134ee648ce7399e50d30ff397`). | Wave-order dependency on Wave 2 **CLOSED** (Wave 2 merged, PR #176). [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) — the complete D1–D38 decision set — is **ACCEPTED — CONTROL-ROOM GATE A**, merged. [`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) — is **ACCEPTED — CONTROL-ROOM GATE B** (Revision 3, accepted by comment `5016117207`, docs-only merge-closure normalization applied, §1C): every mutation job now makes at most one attempt for its entire lifetime, an atomic handoff contract, a `blocked_manual_review` review-release action, a fixed error-class vocabulary, a corrected `applied` verdict, and a corrected locked-prompt role model; Claude did not self-accept, in any revision, and did not self-accept the merge-closure normalization. Both Task 013/013B locked Sol prompts remain unissued — not usable until Stage 0/Task 013 are separately merged and runtime-proven and a separate ChatGPT issuance names the exact SHA. Task 013 implementation additionally requires Stage 0 merged+runtime-proven and providing the DEC-037 §13A correction prerequisites; Task 013B additionally requires Task 013 merged+runtime-proven. No implementation authorized. |
| 4 — Fulfillment and tracking (Task 014) | Not started | — | Blocked on Wave 3 (Layer 2 proven). |
| 5 — Premium operator experience (UI U1–U3, PERF-1, Task 015/015B) | Not started / unauthorized | — | Proposed scope includes product export after Layer 2 (DEC-033 accepted); pending Waves 1–4. |
| 6 — E2E integration, UAT, release readiness | Not started | — | Blocked on Waves 1–5. |

## Historical Sol session log — Wave 1 runtime correction (2026-07-16, SUPERSEDED)

> **Superseded notice (added 2026-07-17, Wave 2 gate-preflight session).** This
> section is a **point-in-time log of an in-progress Wave 1 Sol session**,
> written while PR #172 was still open/draft. Every "pending" / "draft" /
> "remains OPEN" statement below was accurate only at the moment each bullet
> was written and is **superseded by the current merged status** recorded
> above in "Current status" and in the "Wave status" table: **PR #172 merged
> 2026-07-16 (merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6`); SRR-03
> is CLOSED; Wave 1 is implementation-complete and runtime-green.** This
> section is retained verbatim for audit history — do not read any statement
> below as describing current state. The authoritative current-state record
> for these same events is the dated "Sprint checkpoint log" below (see
> especially the "Wave 1 MERGED" entries).

- Re-verified the live base before branching: `mvp/program-integration` matched the product-owner-authorized tip; checkpoint `acd8c4691e72cf5590f2a56228b08f183b76cd9a`, `Shopify-connector`, and `main` remained unchanged.
- Confirmed PR #170/DEC-034 and PR #171 normalized the Wave 1 packets without introducing addon implementation.
- Created `sol/wave-1-readonly-foundation` from the verified integration tip. Opened the single early draft PR [#172](https://github.com/AdamsOdoo/Adams/pull/172) into `mvp/program-integration`; it remains draft and carries the frozen five-stage execution plan.
- Stage 1 CORE-R1: inherited accepted code/test slice re-verified; prior build evidence retained; final exact-head rerun pending.
- Stage 2 LC-1: implementation, focused tests, migration, manifests, validation record, AR-050, and handoff pushed; Python syntax checks passed; Odoo.sh install/upgrade/uninstall/reinstall proof pending.
- Product-owner ruling comment `4982429209` validated the omission and authorized the exact one-field completeness correction. D-SEC1-2/D-SEC1-7 and the LC-1 sanctioned-writer statement were amended in commit `a4a370b5378366e719c59c01b1bbd5febe0a868b`; no architecture or scope changed.
- Stage 3 JOB-ACTIONS: the additive two-action model, nine-method role/state/audit suite, version/import wiring, validation record, AR-051, and handoff are pushed; both new Python sources compile. Odoo.sh remains pending.
- Product-owner ruling comment `4982750956` validated and resolved the Stage 4 pre-edit hard-stop: binding/PII audit uses the existing lifecycle maintenance job helper with narrow protected-site sudo and original actor preservation; company validation uses caller-context records plus `env.company`, without a store field. Packet and validation record updated.
- Final exact-head runtime: build `34986844` at `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` passed targeted `0/0/2`, fresh `0/0/635`, standard `0/0/635`, and all-11-class genuine smoke `0/0/41`; residue/security clean; issue #157 defaults dropped/restored.
- Stage 5 closure: ruling `4988527547` accepts the complete evidence and authorizes SRR-03 CLOSED. Wave 1 is implementation-complete/runtime-green. PR #172 stays draft/unmerged for Claude review; Wave 2 and all excluded domains remain unstarted.
- Post-review SEC-1 correction: ruling `4988842625` authorized closing the full binding mutation surface. Commit `36974edc68c1985e6ccfae8f6bb5c7386f820156` protects the exact common and concrete identity/structure/system-state/provenance/imported-snapshot fields, adds fail-closed classification, and narrowly elevates only two legitimate product-importer writes. Static/source checks are green. Because production security code changed, build `34986844` is retained only as prior-code evidence; one complete corrected-head runtime handoff is pending. **(At the time this bullet was written) SRR-03 remains CLOSED; PR #172 remains draft/unmerged; Wave 2 remains unauthorized** — see the superseded notice above: PR #172 is now merged and this is historical.

## Prior completed work (bootstrap governance)

- Verified all protected references match the task's expected state (checkpoint SHA, issue #165, PR #163 merge target, `Shopify-connector`, `main`, PR #150/#151 heads) — no drift found.
- Created `mvp/program-integration` from the exact checkpoint SHA.
- Ran a 10-workstream evidence-based repository audit (addons/manifests, architecture/decisions, research, QA/runtime evidence, PR #150, PR #151, issues/risk register, operator UX, tests/CI, implementation-plan/prompt history).
- Produced `mvp-completion-program.md` (frozen MVP contract + macro-waves + Sol authority + hard-stops), this state file, `../05-qa/mvp-acceptance-matrix.md`, `DEC-032-mvp-autonomous-execution-model.md`, `../06-prompts/gpt56-sol-master-mvp-mission.md`, `../06-prompts/claude-mvp-wave-review-template.md`, a `CLAUDE.md` addendum, and root `GPT_SOL.md`.
- Merged the governance bootstrap via PR [#166](https://github.com/AdamsOdoo/Adams/pull/166) and opened the master program issue [#167](https://github.com/AdamsOdoo/Adams/issues/167).
- No addon code created or modified. No macro-wave opened. No live Shopify/Odoo runtime call made.

## Blockers

1. **Corrected exact-head Odoo.sh access/run** — RESOLVED (2026-07-16). Build `34995642` / DB `adamsmen-sol-wave-1-readonly-foundation-34995642` / Odoo 19.0 ran the complete corrected-head matrix at runtime-tested SHA `95db3db` (`0 failed / 0 errors / 644`), with a clean prior→corrected upgrade, clean residue/security, and the issue #157 accommodation dropped/restored. The final Claude control-room wave review completed and PR #172 merged (merge commit `d18f9a9`); this blocker is fully closed.
2. **Dev-store access provisioning** — Wave 6 and mutation-domain UAT require human-provisioned Shopify Partner/dev-store credentials; Sol cannot self-provision them (hard-stop 5).

## Open decisions (full list: `mvp-completion-program.md` §9) — resolved by Wave 0 acceptance

1. Task 015/015B retained in MVP Wave 5 after Layer 2 — Accepted (DEC-033 §1).
2. SRR-03 closure sub-gate — **CLOSED** by exact-head build `34986844` and product-owner ruling `4988527547`; closure is read/call safety only and does not claim exactly-once remote effects or DEC-031 Layer 2.
3. PR #150/#151 administrative closure as superseded — Accepted (DEC-033 §3); action to proceed once PR #169 merges.
4. DEC-027 explicitly deferred; DEC-028/029/030 Accepted with the prerequisites in DEC-033 §4 — applied to each record on this PR.
5. Hazard branch left untouched — confirmed; remains untouched.
6. Empty requirements file left untouched — confirmed; remains untouched.

## Runtime evidence log

| Date | Wave | Evidence | Odoo.sh build | Result |
| --- | --- | --- | --- | --- |
| 2026-07-15 | Checkpoint (pre-program) | `../05-qa/task-core-r2-validation-results.md` §IS2 | `34935129` | Fresh install 0/0 across core/product/sale; issue #157 artifact only known failure class. |
| 2026-07-16 | Wave 1 diagnostic (pre-correction SHA `62b2645`) | SEC-1 and CORE-R2 validation records | `34968318` | Upgrade/focused/lifecycle partial passes; transition regression in fresh/full/drain-recovery suites; residue and security scans clean; issue #157 exact artifact only; no Wave 1 pass. |
| 2026-07-16 | Wave 1 corrected production/SRR proof (SHA `d9d2dd0`) | SEC-1 and CORE-R2 validation records; ruling `4988098888` | `34985521` | Fresh 1/0/634, sole test-only AST guard failure; focused 0/0/105, product 0/0/176, sale 0/0/107, lifecycle 0/0/9; all 11 genuine classes ×3 green; clean residue/security; substantive SRR criteria satisfied, closure pending final test-only verification. |
| 2026-07-16 | Wave 1 final exact-head closure (SHA `05bb463`) | Final validation records; ruling `4988527547` | `34986844` | Targeted 0/0/2; fresh 0/0/635; standard 0/0/635; all 11 genuine classes 0/0/41; 10 real 40001 + one lock timeout; clean residue/security; #157 defaults dropped/restored; SRR-03 CLOSED. |
| 2026-07-16 | Wave 1 corrected-head runtime-green (SHA `95db3db`; build at `05acfd7`) | `../05-qa/task-sec1-validation-results.md` (build 34995642) | `34995642` | Prior→corrected upgrade clean; full standard suite 0/0/644 (module breakdown recorded as core 414 + product 202 + sale 124 does not sum to 644 — see validation doc's Test-count reconciliation note; 644 combined stands); four-role 16/17/14 create/alter/clear denial, exact-set classification, importers, audited override, PII mask/retention, LC-1, JOB-ACTIONS, and all genuine SRR-03 classes green; real 40001 + lock timeout exercised; clean residue/security; one test-only AST-guard fix; #157 dropped/restored. SRR-03 CLOSED; Wave 2 unstarted. |
| 2026-07-16 | Wave 1 MERGED | PR #172 merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6` | `34995642` (unchanged evidence; no new runtime) | Final Claude control-room review: 20-point independent verification with adversarial adjudication; two documentation-only claim-accuracy defects found and fixed in reviewed head `d7b08e6`; no code/test/security defect. PR #172 merged into `mvp/program-integration`. `Shopify-connector`, `main`, and the checkpoint branch confirmed unchanged pre- and post-merge. SRR-03 CLOSED; Wave 2 unstarted/unauthorized. |

## Next control-room gate

**Wave 2's gate is Accepted and merged (PR #174), and its docs-only
correction is also merged (PR #175, merge commit
`a54e4a0699ba0426642fd753da581e3712e57177`).** The Wave 2 Definition of
Ready, Task 012 packet (with its 2026-07-16 addendum), and Area-6
order-scan slice were reviewed and accepted by the Claude control room on
2026-07-17, and eight post-merge contract contradictions found by a
follow-up review were corrected the same day (see the Sprint checkpoint
log below). **Wave 2 is authorized to start.** The next control-room gate
is Sol's own Wave 2 implementation wave review, once a
`sol/wave-2-order-import` PR exists, using
`../06-prompts/claude-mvp-wave-review-template.md`. Until then, the next
authorized activity is issuing the locked Sol prompt at
`../06-prompts/sol-wave-2-order-import-locked-prompt.md` with the exact
live `mvp/program-integration` tip substituted for
`<EXACT_SHA_AT_ISSUANCE>`.

## Sprint checkpoint log

- **Wave 3 Gate A — final consolidated Sessions-2-and-3 correction batch
  (2026-07-19):** Resumed on the same branch/draft PR #177, head
  `c8f091149fd398096901118b44d5c2c1e6df25bc` confirmed preserved before any
  change. Read the control-room preliminary review
  ([PR #177 comment `5013028262`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5013028262))
  and the final consolidated ruling
  ([PR #177 comment `5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)),
  which reconciled an independent official-source audit ("Session 2") and
  an independent adversarial architecture audit ("Session 3"). Applied
  every binding decision in one documentation-only correction batch across
  the same ten allowed files: rewrote DEC-036's D2 (schema — `job_id`
  `Many2one`-restrict, `mutation_domain` registry-validated `Char`), D5
  (fingerprint split), D6 (idempotency fail-closed routing), D10/D11
  (orthogonal immutable-`observed_outcome`/`resolution_disposition`
  model), D14 (reconciliation linkage `Many2one`-restrict), D17 (N=3 cap
  resolved per-attempt-sufficient), D18/D29 (store-identity/connection-
  generation), D19–D22 (C1/C2/NET/C3 protocol, C2 resolved to a dedicated
  side cursor), D28 (disconnect-quiescence resolved to awareness-based
  finalization), D30/D31 (four-role ACL + SEC-2 re-key obligation), D32
  (retention resolved to indefinite-for-unresolved +
  configurable-masking-for-resolved), D35 (added and resolved a third
  `mutation_domain` ownership option — registry-validated Char), D37/D38
  (reclassified non-blocking / four proof-environment layers); added a new
  Part 0.5 explicit Session 2/3 reconciliation record; rewrote Parts 4–6
  (zero remaining architecture blockers). Corrected the Layer 2 design doc,
  the DEC-031 addendum, the Stage 0 packet (added
  `shopify_connector_api_client.py`/`shopify_connector_store.py`/
  `shopify_connector_job_actions.py` to the allowed-file list; rewrote the
  hard-stops section to three non-blocking categories), and the locked Sol
  prompt (same corrections, still locked/not issued) to match. Updated
  this file's Current status and the Wave 3 DoR §3/§5. **Result: DEC-036
  status CONTROL-ROOM ACCEPTANCE CANDIDATE — CORRECTIONS APPLIED, NOT YET
  ACCEPTED; zero remaining architecture blockers.** No new file created
  outside the existing ten-file PR set; no `addons/**`/test/security/
  XML/manifest file changed; no Odoo/Odoo.sh run; no Shopify request or
  mutation performed; PR #177 remains open, draft and unmerged; Stage 0
  not implemented; locked prompt not issued; Wave 3 implementation remains
  unstarted. Recommendation: READY FOR FINAL CONTROL-ROOM GATE A REVIEW.

- **Wave 3 Gate A — DEC-031 Layer 2 acceptance candidate + Stage 0 packet, session in progress (2026-07-18):** Verified baseline: `mvp/program-integration` tip `aa87ccc971e` exact match to the required starting base; Wave 2 merge commit `22bfb9a0e9b` confirmed in ancestry; Wave 2 checkpoint `checkpoint/wave-2-order-import-2026-07-18` = `22bfb9a0e9b`, zero tree difference from the live tip; four post-checkpoint commits confirmed as two no-op temporary-file add/revert pairs; PR #176 confirmed merged; zero open PRs; Wave 3/DEC-031 Layer 2/Wave 3 DoR all confirmed still Proposed; no Stage 0 packet existed; protected refs unchanged. Created branch `claude/wave-3-gate-dec-031-layer2-q3vwfj` (the harness-designated branch for this session) from the exact verified tip, opened early draft PR [#177](https://github.com/AdamsOdoo/Adams/pull/177). Ran a 27-agent research/audit/adversarial-review workflow: code audit of every named `shopify_connector_core` model/security/data/test file; documentation audit of DEC-031 (Layer 1 + Layer 2), DEC-030, the Wave 3 DoR, Task 013/013B, the inventory operating model, the reconnect policy, the risk register/acceptance matrix/program contract, and a targeted `research-handoff.md` sweep; four dedicated official-Shopify/Odoo-source research agents; eight thematic adversarial-review clusters covering all 35 numbered decisions + 15 lettered risks from this session's task; one consolidation pass. Mid-session, received and incorporated a binding control-room parallel-audit ruling ([PR #177 comment `5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989)) correcting the PostgreSQL isolation-level assumption (Odoo 19 = REPEATABLE READ, independently re-verified against `odoo/sql_db.py`, not merely accepted from the ruling text), the CAS field name, THROTTLED fail-closed treatment, the batching default, the clean-cursor invariant, and explicit `sudo()`-based security guards — every point cross-checked against this session's own independent research, which had already reached the same conclusions on several points before the ruling arrived. Produced: `shopify-layer2-mutation-safety-refresh-2026-07-18.md` (new); corrected `dec-031-layer-2-mutation-safety-design.md`; a new dated addendum on `DEC-031-core-r2-job-execution-replay-safety.md` (Layer 1's Accepted status untouched); `DEC-036-wave-3-layer-2-gate.md` (new, the complete `L2-D1`–`L2-D38` decision inventory); `wave-3-stage-0-layer-2-packet.md` (new); `sol-wave-3-stage-0-locked-prompt.md` (new, locked, not issued); corrections to `wave-3-definition-of-ready.md` (CAS preflight closed, batching hedge corrected, Wave 2 dependency closed); this file; and an `architecture-review-log.md` row (below). **Package status: NOT FROZEN** — an externally-tracked "Session C" code/architecture audit is stated by the control room to still require reconciliation; this session's own audit is offered as Session A's independent contribution, not a substitute. Eight DEC-036 decisions remain explicitly BLOCKING. **No implementation authorized; no `addons/**` file changed; no Odoo/Odoo.sh run; no Shopify request or mutation performed; Claude did not accept its own decision package; PR #177 remains open, draft and unmerged; Wave 3 implementation remains unstarted.**

- **Wave 2 implementation/static handoff — runtime-access hard stop (2026-07-17):** Verified exact base `234c0bb50b3f61b7681e18f0b28839dee619cdb9`, opened draft PR #176, and implemented only Task 012 plus the accepted Area-6 order-scan slice. Commits: tracker start `ec0a48a793fc7d2f53024cd89c4a539322f94aa9`; guarded importer `92cab4c532e03102473a04cb2f2b23d7f307a480`; scan/backfill `a9e1d61a6655d6b46b53057e372115c02ba0bdfd`. Static evidence: exact 20 Wave-2 Python files parse; cron XML, manifest and 12-row ACL CSV parse; four importer GraphQL operations plus one scan operation are read-only; execute-business-only, exact-sudo, LC-1 ondelete, replay-policy, complete 50-field order-binding protection, no-context-bypass and no-mutation guards pass; 86 tests authored, including independent-connection enqueue and permanent-binding races. Odoo.sh is unavailable to this Sol session, so hard-stop 5 is active. No build, DB, runtime count, fresh/upgrade/uninstall/full-suite/concurrency/residue/security pass, or live Shopify result is claimed. The draft PR remains open/unmerged and must be tested at its then-current exact head before Claude review; SRR-03 remains CLOSED; Wave 3+, Layer 2, UI, webhooks, OAuth, and every Shopify mutation remain unstarted.

- **Wave 2 gate CORRECTION MERGED (2026-07-17, same day as the gate merge):** Reviewed PR #175 (`claude/wave-2-gate-correction`) live from GitHub: open/draft/**clean**, head `aad19b0` / base `mvp/program-integration` @ `751e50b` exact (merge-base = base, no divergence), 7 files changed, all under `docs/**` (0 `addons/**`). Ran a grep-based adversarial self-review confirming: no residual "tax rate-match+creation" wording outside historical/superseded context; `order_scheduled_sync_enabled` present in the DoR, Task 012 packet, Area-6 packet, and locked prompt; no "four new model files" wording remains; the tax-mapping ACL correctly shows Administrator-create/write-only distinct from the order-binding's customer-binding pattern; `action_approve_manual_gateway_order` specified consistently across all three documents; no rollback text claims a Git revert drops schema; `<EXACT_SHA_AT_ISSUANCE>` placeholder present; no PII-masking addition; DoR §2.2's 29-file allowed list and the locked prompt's §3 29-file list re-diffed and confirmed still byte-identical (no drift introduced by the correction). No `sol/wave-2-order-import` branch existed; protected refs `acd8c46`/`dd6ecb8`/`a5d4543` confirmed unchanged. Marked the PR ready and merged with a normal merge commit **`a54e4a0699ba0426642fd753da581e3712e57177`** (no squash, no rebase) into `mvp/program-integration`. Post-merge: PR #175 closed/merged; `mvp/program-integration` tip is the merge commit; this file's Current status/Active wave/Wave status/Next-control-room-gate sections restored to "Wave 2 authorized to start." **Verdict: CORRECTED, MERGED, AND WAVE 2 RE-AUTHORIZED.** Wave 2 implementation remains unstarted; DEC-031 Layer 2 remains unaccepted; no PII-masking capability added. Master issue #167 correction-closure comment posted; PR #174 correction-closure comment posted.

- **Wave 2 gate CORRECTION started (2026-07-17, same day as the gate merge):** A post-merge control-room re-review of PR #174 (comments [`5000101837`](https://github.com/AdamsOdoo/Adams/pull/174#issuecomment-5000101837)/[`5000111557`](https://github.com/AdamsOdoo/Adams/pull/174#issuecomment-5000111557)) found eight current-contract contradictions between the merged gate documents: (1) `test_order_import_mapping.py`'s description still said "tax rate-match+creation+reuse" though D-012-9 had already removed tax auto-create from MVP; (2) `order_scheduled_sync_enabled` was required by DoR row 9/Area-6 D-A6-3 but omitted from DoR row 6's frozen settings inventory and the locked prompt; (3) DoR row 7 said "four new model files" for five listed rows; (4) DoR row 8 gave `shopify.connector.tax.mapping` the customer-binding read/write/create ACL pattern instead of an Administrator-create/write-only configuration pattern; (5) the accepted `manual_gateway_policy=require_approval` decision had no defined backend approval action/permission/provenance/audit contract anywhere; (6) test descriptions still said "tip mapping" and vague "metadata" despite nonzero-tip fail-closed and an exact data-minimization allowlist already being binding; (7) the rollback sections claimed a single Git revert "drops" tables/columns, which is not how Git or Odoo module upgrades work, and ignored that `shopify_connector_sale` also carries the merged Task 011 customer-import capability; (8) the locked prompt's exact-SHA line used an ad hoc fill-in instruction instead of the standard placeholder. All eight are corrected in this same commit across `wave-2-definition-of-ready.md`, `task-012-order-import-implementation-packet.md`, `area-6-sync-triggers-implementation-packet.md`, `DEC-035` (new "Correction addendum" section with the full before/after table), and `sol-wave-2-order-import-locked-prompt.md`; no product decision, scope boundary, or open-question disposition changed. This file's Current status/Active wave/Wave status rows record the correction as in-progress and Wave 2 implementation launch as temporarily suspended until the correction PR merges — see this same Sprint checkpoint log's post-merge tracker-upkeep entry for the merge outcome and the restored authorization state.

- **Wave 2 gate ACCEPTED AND MERGED — decision-acceptance + Definition-of-Ready + Task 012/Area-6 packet re-acceptance (2026-07-17):** Performed the exact next-session prompt from the prior handoff entry. Live identity verification first: starting SHA `a34c68e84aada288dad3dc22a6afe94f5ace0652` confirmed exact on `mvp/program-integration`; PR #172 merged via `d18f9a99` and PR #173 merged via `0fb8ccb` both confirmed ancestors via `git merge-base --is-ancestor`; SRR-03 CLOSED; Wave 1 accepted; protected refs `acd8c46`/`dd6ecb8`/`a5d4543` unchanged; zero open PRs; zero order-domain code anywhere in the repo (confirmed by direct `find`/`git ls-tree`/`git grep`). Ran a 14-agent parallel exact-codebase preflight over the complete `shopify_connector_core`/`_product`/`_sale` addon trees and the complete planning corpus (policy docs, decision pack, architecture-review log, UAT matrices, the Task 012 packet, its 3476-line decision closure, the Area-6 packet, the DoR, the tracker/templates, the research handoff), plus a live fetch of current `developer.shopify.com` Admin GraphQL documentation for the mixed-transaction/`OrderSortKeys` open questions. Reconciled the packets against real code (not just against each other) and found two genuine architecture gaps neither packet had named — no `order_domain_enabled` settings flag/extension seam (resolved by reusing `sale_domain_enabled`, exactly as `customer_import_sync` already does — zero core edit) and no AST guard yet scoping future order-domain files to `execute_business`-only (resolved by requiring Task 012/Area-6 to add their own guard) — both recorded in [`../04-decisions/DEC-035-wave-2-open-question-dispositions.md`](../04-decisions/DEC-035-wave-2-open-question-dispositions.md) as EQ-PF-1/EQ-PF-2. **Accepted** the Wave 2 Definition of Ready (every §3 gate decision; exhaustive allowed/forbidden file list frozen in §2.2/§2.3). **Re-accepted** the Task 012 packet as one canonical contract via a new §0, resolving the confirmation-policy field contradiction in favour of the addendum's `order_confirmation_policy` (default `paid_only`, replacing the original no-default posture entirely) and confirming D-012-4 as written. **Accepted** the Area-6 order-scan slice only (D-A6-1..4/6 as applied to orders); product-scan, customer-scan, and the optional core-additive readiness extension remain explicitly out of Wave 2. Closed or non-blockingly deferred every open question (OQ-A..E, OQ-COD-6, OQ-RB-1/5/6) in DEC-035, including a mixed-transaction disposition (OQ-D) that reuses the binding mixin's existing `status='review'` value rather than inventing new manual-review vocabulary, backed by a fresh official-Shopify-evidence check confirming no arbitration algorithm is published for disagreeing transactions and that `OrderTransactionStatus.UNKNOWN` is itself a documented Shopify enum member. Issued (not executed) the locked Sol Wave 2 prompt: [`../06-prompts/sol-wave-2-order-import-locked-prompt.md`](../06-prompts/sol-wave-2-order-import-locked-prompt.md). Recorded the reconciliation in one docs-only commit `637a02fdb48ca9c3f0a3463ee10335e9bfc7e25e` (`wave-2-definition-of-ready.md`; `task-012-order-import-implementation-packet.md` §0; `area-6-sync-triggers-implementation-packet.md` §0; `DEC-035` new; `sol-wave-2-order-import-locked-prompt.md` new; `mvp-acceptance-matrix.md` row 9; `architecture-review-log.md` AR-054; this file's stale "Active Sol session" section relabeled historical; `research-handoff.md` new top entry), opened as an early draft PR [#174](https://github.com/AdamsOdoo/Adams/pull/174), ran an independent adversarial review (all changes under `docs/**`; zero `addons/**`; Sol-prompt allowed-file list verified byte-identical to the DoR's; no PII-masking addition; no DEC-031 Layer 2 acceptance; no manual_review_subreason vocabulary invented), marked the PR ready, and merged with a normal merge commit **`f62197b9281d6e18e4f1861d0e327738b4c3d510`** (no squash, no rebase) into `mvp/program-integration`. Post-merge: PR #174 closed/merged; `mvp/program-integration` tip is the merge commit; checkpoint/`Shopify-connector`/`main` confirmed unchanged. **Verdict: ACCEPTED, MERGED, AND WAVE 2 AUTHORIZED TO START.** Wave 2 implementation has not started — no `sol/wave-2-order-import` branch or PR exists. DEC-031 Layer 2 remains unaccepted. Master issue #167 closure comment posted.

- **Fable gap-closure MERGED — control-room decision & merge review (2026-07-17):** Reviewed the corrected PR #173 (`fable/mvp-remaining-gap-closure`) live from GitHub: open/draft/**clean**, head `09078a8` / base `mvp/program-integration` @ `1e46c23` exact (merge-base = base, no divergence), PR #172 merged via `d18f9a99`, SRR-03 CLOSED, protected refs `acd8c46`/`dd6ecb8`/`a5d4543` unchanged, all 126 changed paths under `docs/**` (no `addons/**`/security/ACL/migration/test/manifest). Confirmed Class A (A-1..A-18); decided every Class B (PD-B1..B7) — amendments B1 (per-store `pending_wait_expiry` 24 h default, min 1 h/max 7 d, OQ-C resolved), B4 (mode-switch reconciliation-scan boundary: earlier-of watermark-overlap/unresolved-external, 30-day default lookback), B5 (Mode 1 outbound fulfillment is **Full**, not Lite); dispositioned every Class C (TA-C1..C8) — **DEC-031 Layer 2 (C1/C2) NOT DEC-accepted**, design accepted only as the authoritative proposal for a dedicated pre-Wave-3 architecture gate (verified vs all 8 hard safety properties); classified Class D fail-closed; confirmed Class E post-MVP; accepted the 28-screenshot UX evidence as the visual baseline only. Cross-document consistency clean. Recorded the decisions in one docs-only reconciliation commit `68c159f` (decision pack §Control-room decisions 2026-07-17; lifecycle §7; fulfillment-modes §6; modular-architecture §6/§9; SEC-2 §D; AR-053; gap-closure-status; research-handoff; PR body), marked PR #173 ready, and merged with a normal merge commit **`0fb8ccbe8ce54404a57260f82e8226ffa7e6bf73`** (no squash, no rebase) into `mvp/program-integration`. Post-merge: PR #173 closed/merged; integration tip is the merge commit; protected refs re-confirmed unchanged. **Verdict: ACCEPTED AND MERGED.** No implementation authorized; Wave 2 remains unauthorized/unstarted. Master issue #167 closure comment posted (`4999219626`). Next authorized activity: a separate Wave 2 decision-acceptance + Definition-of-Ready + packet re-acceptance + exact-base preflight session.
- **Wave 1 MERGED — final Claude control-room review and merge (2026-07-16):** Performed the final independent review of PR #172 at head `8a3104f892fa0bdf256e17a57933a7dcbb9db0c5`. Live identity verification: PR open/draft/unmerged/mergeable, base `mvp/program-integration` at the expected unchanged tip `64d526f`, head/base/runtime-tested/final-evidence SHAs all matched their expected values, commits `95db3dba` (test-only) and `8a3104f8` (docs-only) confirmed to touch exactly their claimed files, checkpoint/`Shopify-connector`/`main` unchanged. Ran a 20-point independent review (9 parallel dimension agents against the actual PR-head worktree, followed by adjudication of every non-clean-pass finding): CORE-R1, LC-1, JOB-ACTIONS, SEC-1 exact 16/17/14 protected-field enforcement and fail-closed classification, sanctioned importer writers and full sudo/context-bypass inventory, override atomicity/actor preservation, PII masking/retention, company-consistency, install/upgrade/uninstall/reinstall, full-suite/SRR-03/PostgreSQL-40001/residue/issue-157 evidence specificity, and all scope boundaries (no exactly-once claim, no DEC-031 Layer 2, no Wave 2+ scope) — 7 of 9 clusters PASS cleanly; one (CORE-R1/install docs) downgraded on adjudication to confirmed-but-non-blocking documentation staleness; two (JOB-ACTIONS docs' false "no sudo()" claim; the PR's unqualified "exactly two new sudo sites" claim) CONFIRMED as real documentation/claim-accuracy defects — in both cases the underlying code was independently re-verified as safe and correctly scoped; only the written record was inaccurate. Resolved the two control-room-mandated inconsistencies (644-vs-414/202/124 test-count arithmetic; stale "runtime pending" wording across `mvp-program-state.md`, `mvp-acceptance-matrix.md`, `task-lc1-validation-results.md`, `task-job-actions-validation-results.md`, `architecture-review-log.md`) plus the two review-surfaced claim-accuracy defects in one docs-only commit, `d7b08e6d4a84af1a15b498068205c8ee6d510ea5` (`docs(wave1): reconcile final runtime evidence`) — no addons/tests/manifests/security files touched. Updated the PR body to carry current evidence and the review outcome, marked the PR ready for review, and merged with a normal merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6` into `mvp/program-integration` (no squash, no rebase, no force-push). Post-merge: PR #172 closed/merged; `mvp/program-integration` tip is the merge commit; `Shopify-connector`, `main`, and the checkpoint branch confirmed unchanged. **Verdict: ACCEPTED AND MERGED.** SRR-03 remains CLOSED. Wave 2 remains unstarted/unauthorized; no Fable gap-closure work has started.

- **Wave 1 Claude control-room corrected-head runtime validation (2026-07-16):** Ran the complete corrected-head Odoo.sh matrix on build `34995642` / DB `adamsmen-sol-wave-1-readonly-foundation-34995642` / Odoo 19.0, from `05acfd72b04f072e0ed95c476ceccfa606c52d91` (clean tree; versions core `19.0.1.9.1`/product `19.0.2.1.2`/sale `19.0.1.2.1`). A genuine prior→corrected upgrade was clean (no migration/field/model/ACL/manifest error; no model/table/ACL/group/job-type/transition/replay-policy scope added). The initial exact-head run was red by exactly one failure — `test_product_importer_binding_writers_use_exact_sudo_sites` (`2 != 1`), an over-broad AST guard that conflated the sanctioned `dict(snapshot_vals, …)` create with the `existing.sudo().write(snapshot_vals)` refresh; the production importer is correct. Under this prompt's failure-handling authorization the control room applied a test-only fix (`95db3dba4bf295ca6c6ee94ae7fa08da1d505eb7`; one file; `+7`; no production/feature/version change). The definitive rerun is `0 failed / 0 errors / 644` (a session-recorded module breakdown of core 414 + product 202 + sale 124 did not sum to 644 and has been withdrawn as unreconciled — see `../05-qa/task-sec1-validation-results.md`'s Test-count reconciliation note; the combined 644 figure is unaffected and stands): four-role 16/17/14 create/alter/clear denial, exact-set classification/fail-closed, importers, audited override, PII mask/retention, LC-1, JOB-ACTIONS, and all genuine SRR-03 independent-connection classes green, with real `40001` conflicts and a real lock timeout exercised. The nine masked `setUpClass` errors were 100% the base-Odoo issue #157 `notification_type`/`color_scheme` NOT-NULL artifact; the reversible database-default accommodation cleared all nine and was then dropped, restoring both columns to their original no-default NOT-NULL state. Residue/security clean (no leaked jobs/leases/stores/credentials/logs/idle-txns/cursors/sessions/triggers/tokens/raw PII; only the seeded attribute-lock singleton and 3 by-design connector crons). One docs-only evidence commit records this. **No merge and no ready-marking performed** — the final wave review + merge decision is the next step. SRR-03 remains CLOSED; PR #172 remains draft/open/unmerged; Wave 2 remains unauthorized and unstarted.

- **Wave 1 consolidated SEC-1 binding correction (2026-07-16):** Product-owner ruling `4988842625` bound the complete current binding mutation surface. Production/test commit `36974edc68c1985e6ccfae8f6bb5c7386f820156` adds one reusable mixin extension/classification seam, protects exact template/variant/customer sets of 16/17/14 fields, refuses non-su create/alter/clear attempts for all four shared roles, preserves audited override/PII/retention/importer paths, and narrowly adds sudo only to the existing product-variant refresh and image-checksum writes. Static parsing and source guards are green; no ACL, group, model, table, job type/source, context bypass, dispatcher, replay-policy, or Wave 2 change was made. Prior build `34986844` remains valid only for prior SHA `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723`; corrected exact-head runtime is pending under one operator handoff. SRR-03 remains CLOSED; PR #172 draft/unmerged; Wave 2 unauthorized.

- **Wave 1 Claude control-room review — REVISE (2026-07-16):** Reviewed draft PR #172 (head `bee02298dec3589fb06df6f7f5f15473e615ed90`) against `claude-mvp-wave-review-template.md`. Live identity verification clean: PR open/draft/unmerged, base/head exact match, mergeable, final evidence commit exactly one commit after and docs-only relative to `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723`, addon/test content byte-identical, checkpoint/`Shopify-connector`/`main` unchanged, no drift on `mvp/program-integration`, PR's own 48-file inventory matches the actual diff exactly. Independent parallel dimension review (with adversarial verification of every finding) plus direct manual reading of the highest-stakes files: CORE-R1 integrity preserved (only SEC-1 sudo-elevation hunks touch its files); LC-1 lifecycle implementation matches DEC-030/the design doc exactly (historic sink, set-once `original_job_type`, audited non-terminal cancellation, fail-closed dispatcher, additive/idempotent migration); JOB-ACTIONS is a clean additive extension matching its packet; SRR-03/CORE-R2 closure code matches the risk register's description, DEC-031 Layer 2 not silently implemented, no new Shopify mutation call added. **SEC-1 finding (confirmed blocker):** `shopify_connector_binding_mixin.py`'s `_protected_binding_fields()` omits the binding-override audit-provenance fields, letting a Reviewer/Admin forge an audit trail via direct `write()` without calling `action_override_binding()` — verified independently twice (workflow adversarial verifier + Claude's own direct file read), both reproducing the exact same line numbers and mechanism. A second candidate finding (extra `→cancelled` transition edges) was investigated and refuted — those edges are required by LC-1's own accepted design (non-terminal jobs must remain cancellable for historic-domain conversion) and are not a spec deviation. Sudo-elevation site counts were mechanically verified against the SEC-1 validation record's claimed inventory and match exactly, file-by-file. **Decision: REVISE.** Not merged; PR left draft. Full checklist and finding detail posted as a PR #172 review. Minor, non-blocking documentation-staleness notes (task-lc1-validation-results.md citing superseded manifest versions and a stale runtime-pending line; task-job-actions-validation-results.md similarly stale) were left for Sol to sweep up in the same corrective pass rather than edited directly, since they are outside this session's documentation-only correction authority once a substantive code defect required a Sol revision round. Wave 2 remains unauthorized.

- **Wave 1 final exact-head closure (2026-07-16):** Odoo.sh 19 build `34986844`, DB `adamsmen-sol-wave-1-readonly-foundation-34986844`, exact SHA `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723`: targeted AST `0/0/2`, fresh all-module `0/0/635`, standard `0/0/635` (`352+176+107`), all 11 genuine SRR-03 classes `0/0/41`, 10 real `40001` conflicts and one lock timeout, clean residue/security, and both issue #157 defaults dropped/restored. Ruling `4988527547` authorizes SRR-03 CLOSED. Wave 1 is implementation-complete/runtime-green; PR #172 remains draft/unmerged for Claude review; Wave 2 unstarted.

- **Wave 1 build 34985521 accepted / test-only AST correction (2026-07-16):** Exact SHA `d9d2dd018470054944db064cdd553160232713cd` ran fresh `1 failed / 0 errors / 634`, with only the stale enqueue create-target AST receiver helper failing. Focused Wave 1 `0/0/105`, product `0/0/176`, sale `0/0/107`, lifecycle `0/0/9`, all 11 genuine SRR classes ×3 OS-process repetitions, residue, and security checks were green. Ruling `4988098888` accepts substantive SRR-03 criteria. Test-only commit `b42042d641ce2d02cad9559a03fcb268ceaac3bc` unwraps only the five approved wrappers and changes no production file. SRR-03 remains OPEN pending the limited final exact-head verification; Wave 2 remains unstarted.

- **Wave 1 runtime correction pushed (2026-07-16):** Build `34968318` at pre-correction SHA `62b2645f69280aadc68a56045a26bef2063c5821` found that D-SEC1-1 rejected five accepted CORE-R2 recovery outcomes after a PostgreSQL rollback returned the exact job to committed `queued`/due-`retry_waiting`. Product-owner ruling `4984719237` authorized only those edges. Commit `2b6d9d8259fada252abca19407d1df53bed9e66f` implements the narrow correction and tests both states across safe retry, exhaustion, conservative and undeclared policy, exact re-lock and no handler replay. Static guards are green; corrected runtime is not yet run; SRR-03 OPEN; Wave 2 unstarted.


- **Wave 1 Stage 4 implementation / runtime-access hard-stop (2026-07-15):** SEC-1 implementation commit `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5` applies D-SEC1-1..7 and both product-owner rulings across 32 packet-owned addon/test files. Static proof: 31 Python parses green, cron XML parses, exact sudo inventories guarded, 9 core security + 12 PII focused tests encoded. No Odoo.sh status/workflow, local Odoo runtime, authenticated build, or database is available; hard-stop 5 is active. Stage 5/SRR-03 runtime proof is unstarted; SRR-03 OPEN; Wave 2 unauthorized.

- **Wave 1 Stage 4 resumed under binding ruling (2026-07-15):** PR #172 comment `4982750956` validated the prior hard-stop and bound the existing lifecycle maintenance job as the per-action/per-store atomic audit carrier, with narrow protected-site sudo and original actor preservation. It also bound the single-company `env.company` comparison without adding `company_id` to the store. The SEC-1 packet and validation scaffold record identifiers/counts/reasons-only audit content, exact carrier counts, redaction, company-neutral behavior, refusal/no-audit cases, and rollback-on-audit-failure proof. Stage 4 resumed on the same branch and draft PR; SRR-03 remains OPEN; Wave 2 unauthorized.

- **Wave 1 hard-stop before SEC-1 implementation (2026-07-15):** After Stage 3, Sol inventoried every current SEC-1 model/writer before editing. The accepted packet requires binding overrides and PII masking/sweeps to emit audited `manual_action`/summary rows, but the only connector audit-row model requires a `shopify.connector.job` and the packet names neither an audit-job carrier/creation door nor another audit model. It also requires binding-store/company consistency although the store model has no company field. Selecting a carrier or ownership source would alter security architecture and sudo inventory, so hard-stop 10 triggered before any SEC-1 production/test edit. Stage 3 remains implemented/syntax-clean; Odoo.sh and SRR-03 remain pending; Wave 2 unauthorized.

- **Wave 1 Stage 3 JOB-ACTIONS implemented (2026-07-15):** Implemented accepted D-JA-1 as a pure additive core extension: manual retry across the four approved recovery states, cancel across the four approved non-terminal work states, exact role/reason/audit contracts, and no force/bypass or pre-SEC-1 sudo. Added a nine-method focused matrix, version/import wiring, validation record, AR-051, and compact handoff. Both new Python sources compile; exact-head Odoo.sh remains pending. Stage 4 SEC-1 is active; SRR-03 remains OPEN; Wave 2 unauthorized.

- **Wave 1 resumed under product-owner ruling (2026-07-15):** PR #172 comment `4982429209` validated the LC-1/SEC-1 completeness hard-stop and approved the narrow one-field correction. The SEC-1 packet now protects `original_job_type`, adds four-role direct-write denial coverage, and preserves the LC-1 conversion helper as a named sanctioned writer; the packet amendment is isolated in commit `a4a370b5378366e719c59c01b1bbd5febe0a868b`. Stage 3 resumed on the same branch and draft PR. SRR-03 remains OPEN; Wave 2 remains unauthorized.

- **Wave 1 hard-stop after LC-1 (2026-07-15):** CORE-R1 was found already inherited byte-for-byte from the checkpoint, re-verified without duplicate code, and recorded as Stage 1. LC-1 was implemented on PR #172 (historic job sink, original-type preservation/backfill, audited cancellation/retyping, two domain `ondelete` callables, dispatcher refusal, focused tests, version bumps); Python sources compile, Odoo.sh pending. Before JOB-ACTIONS, cross-checking the accepted SEC-1 field list exposed a security/integrity gap: LC-1's new `original_job_type` is not in D-SEC1-2's exact protected set, so implementing Stage 4 verbatim would leave that audit identity generically writable under the existing ACLs. Hard-stop 9 triggered; no Stage 3+, runtime closure, or Wave 2+ work started.

- **Wave 1 execution start (2026-07-15):** Re-verified the exact authorized integration tip and all protected references, confirmed no conflicting Wave 1 branch/PR or later-wave implementation, created `sol/wave-1-readonly-foundation`, and recorded the five-stage execution order. This is a state-only bootstrap commit; no addon/test implementation or runtime claim is included. SRR-03 remains OPEN and Wave 2 remains unauthorized.

- **Wave 1 gate normalization (2026-07-15):** Independently re-verified the live baseline before touching anything (`mvp/program-integration` = `88f2dcaaa9ec0ad01fdabec766cdcd819b859e9e`, matching PR #170's merge commit exactly; checkpoint/`Shopify-connector`/`main` unchanged at their recorded SHAs; no Wave 1 implementation branch or PR exists; SRR-03 remains OPEN; Wave 2 remains unauthorized). Read the complete current text of DEC-034, DEC-030, the CORE-R1/LC-1/JOB-ACTIONS/SEC-1 packets, this file, the completion program, and the acceptance matrix, and confirmed PR #170/DEC-034 (plus the earlier Wave 0 closure comment) intended full implementation authorization for all four Wave 1 stages, not merely sequencing. Found a real defect: DEC-034, CORE-R1, the lifecycle design doc, JOB-ACTIONS, and SEC-1 each still carried an active "Proposed"/"NOT accepted"/"DO NOT USE UNTIL..." header or locked-prompt gate line dating from before acceptance, and DEC-030 contained an internal contradiction (top-of-file note said Accepted, its own `## Status` section still said NOT accepted) — any of these would cause a fresh Sol session to read the already-accepted Wave 1 packets as unauthorized. Corrected each packet's active status header and locked-prompt gate preamble to state the gate is open (CORE-R1 Stage 1, LC-1 Stage 2, JOB-ACTIONS Stage 3, SEC-1 Stage 4, each under DEC-034/issue #167), fixed DEC-030's internal contradiction, normalized this file's and `mvp-completion-program.md`'s stale "reconciliation active"/"DEC-033 pending" wording, updated the acceptance matrix's authorization cells, and corrected `research-handoff.md`'s stale draft-PR entry. No architecture, requirement, allowed-file list, test requirement, or implementation mechanism changed; no `addons/**` or test file touched; no protected reference touched; no Wave 1 implementation began.

- **Wave 1 packet reconciliation (2026-07-15):** Sol's first Wave 1 launch hard-stopped before any branch/PR/code (issue #167 comment `4980808811`) on three packet conflicts (SEC-1's Area-6/action-doors dependency; SEC-1's nonexistent order-binding allowlist entry; LC-1-vs-SEC-1 sequencing). Claude control room independently re-verified all three against primary sources (packet text line-by-line, live `git grep`/`git ls-tree`) and confirmed each. Produced `DEC-034` (corrected Wave 1 order: CORE-R1 → LC-1 → JOB-ACTIONS → SEC-1 → SRR-03 closure), a new `task-job-actions-generic-core-packet.md` extracting D-A6-5, and corrections to the SEC-1, Area 6, lifecycle-design, DEC-030, program-contract, program-state, acceptance-matrix, and Task 012 documents. Docs-only; no addon code, protected reference, or implementation branch created. Opened as a draft PR into `mvp/program-integration`, pending control-room adversarial consistency check before merge.

- **Wave 0 acceptance (2026-07-15):** Claude control-room review accepted DEC-033 with two minor documentation corrections (Wave 1 internal sub-stage note; hard-stop 11 rewording), applied directly on PR #169. DEC-028/029/030 accepted; DEC-027 confirmed Proposed/Deferred. PR #150/#151 administrative closure as superseded authorized to proceed post-merge. Full review recorded as a PR #169 review comment and an issue #167 closure comment. Wave 1 authorized upon merge; Wave 2 remains blocked on SRR-03 closure.

- **Wave 0 submission (2026-07-15):** Docs-only PR #169 opened. DEC-033, official-source refresh, contract/matrix/risk/Task-012 alignment, and session QA/handoff were prepared. No runtime evidence or addon/protected change. Awaiting Claude control-room review; Wave 1 unauthorized.

- **Wave 0 start (2026-07-15):** Product-owner launch received; protected refs verified; `sol/wave-0-reconciliation-research` created from `mvp/program-integration`; Wave 0 docs/research work opened. No addon code authorized or changed.
- **MVP Program Bootstrap (2026-07-15):** Established the control-room governance framework (this file and its siblings). Verified checkpoint integrity, created `mvp/program-integration`, audited the full repository, froze the MVP contract, and prepared Sol's launch prompt. Implementation remains frozen pending product-owner launch. Next: product owner reviews the bootstrap PR, then launches Sol with `../06-prompts/gpt56-sol-master-mvp-mission.md` at XHigh reasoning effort.


### Wave 2 pre-runtime freeze handoff — 2026-07-17

- **Branch / PR:** `sol/wave-2-order-import`; draft PR #176 → `mvp/program-integration`, open and unmerged.
- **Scope covered:** complete Task 012 + accepted order Area-6 contract traceability, every changed production line, 86-test quality inventory, install/upgrade/migration analysis, ACL/sudo/PII review and all available non-Odoo tooling.
- **Corrections:** deterministic nested-savepoint binding-race rollback; invisible-winner enqueue collision handling; exact state/side-effect/configuration/pagination/atomicity tests; connector-role manual approval exact read seam.
- **Runtime evidence:** none. Exact-head Odoo.sh matrix is pending; no pass is claimed.
- **Hard stop:** runtime access only. Source audit found no product-decision blocker.
- **Next action:** run the single matrix in the two Wave-2 validation records against the exact PR head; do not change source first.
- **Boundary:** SRR-03 CLOSED; PR draft/unmerged; no mutation, Layer 2 or Wave 3+ work.
