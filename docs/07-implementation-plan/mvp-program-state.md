# MVP Program State — Live Tracker

> **Current live tracker — calibrated 2026-07-25.** The complete pre-calibration tracker is archived at [`archive/mvp-program-state-through-2026-07-22.md`](./archive/mvp-program-state-through-2026-07-22.md). That archive preserves the full dated audit trail. This file is intentionally concise and must remain the first current-state document a worker reads.
>
> Stable scope/sequencing: [`mvp-completion-program.md`](./mvp-completion-program.md). Review policy: [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md). Acceptance evidence: [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md).
>
> **Canonical role/process governance — 2026-07-25.** [DEC-041](../04-decisions/DEC-041-evidence-first-process-reallocation.md) and the [role-model addendum](../04-decisions/2026-07-25-mvp-role-model-addendum.md) govern: ChatGPT control room; Sol/Codex implementation; Runtime Claude exact-SHA runtime; separate Claude independent review; product owner final authority. Gates are unchanged. Framework-dependent assumptions require upstream citations; pushes and runtime output require durable records; tiers are deterministic from diff paths and semantics.

## 1. Current program status

| Item | Current state |
| --- | --- |
| Program integration | **`mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` is the live tip** (D10 closure, 2026-07-25), after pre-Wave-5 stabilization PR #203 (`2583081f`) and Wave 5 U1 Gate-A docs PR #194 (merge `87f1763a`, accepted head `80fbb523`). Earlier tips `3a1afa43` (PR #189/#202) and `2583081f` are historical. Exact-base CI: Actions run [`30177207908`](https://github.com/AdamsOdoo/Adams/actions/runs/30177207908) `success` on `87f1763a` — DEC-041 D8 **supporting** evidence only; Odoo.sh remains the Tier-1 authority. Full gate state: [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md). |
| Wave 1 | Accepted, runtime-green, merged via PR #172 (`d18f9a9`); exact-head build `34986844`. |
| Wave 2 | Accepted, runtime-green, merged via PR #176 (`22bfb9a`); runtime-tested `63607dd`, build `35100725`, 728/728 and 86/86 Wave-2 methods green. |
| Wave 3 Stage 0 | Accepted, runtime-green, merged via PR #178 (`e48cfb1`); build `35145929`, 825/825. External process harness was explicitly infrastructure-deferred, not claimed executed. |
| Wave 3 inventory | Accepted, runtime-green, merged via PR #182 (`ab4f12f`); inventory 247/247, concurrent 9/9, sequential recovery 3/3. Live Shopify proof remains CV-013 issue #185. |
| U0 | Accepted, runtime-verified, merged via PR #192 (`8818c77`); exact head `a13f672`, build `35308219`, U0/Test Connection 67/67, sale 194/194, inventory 247/247. Driven browser/visual evidence remains deferred to UAT/release readiness. |
| Wave 4 Gate A | Accepted and merged via PR #188 (`01f072d`). |
| Wave 4 Gate B | [PR #189](https://github.com/AdamsOdoo/Adams/pull/189) is backend-accepted and merged at `3a1afa43f8d07a7dae1799968273fa0ab8049490`. Runtime-tested implementation candidate `25639f17`, Odoo.sh build `35422036`, [runtime record 5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652), and [independent acceptance 5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326) remain authoritative. The post-runtime head added only two accepted tracker files and no `addons/**` or test change. Live Shopify Gate D/CV-013 is deferred until the Wave-5 implementation candidate freezes; it remains open and unclaimed. |
| Wave 5 completion batch | **IMPLEMENTED, NOT ACCEPTED** — on `fable/wave-5-completion` (draft PR #204) from the bound base `87f1763a`, under the control-room continuation ruling of 2026-07-26 which opens G5-4/G5-5, accepts SEC-2 PII Option 1 and the U2/U3 addendum, and rules G5-1/2/3/6/8 satisfied. **Delivered: SEC-2 PII simplification, PERF-1 (source-rebased), U1, U2, and — `[Corrected 2026-07-27]` — Task 015, Task 015B and U3, which this row previously recorded as NOT delivered.** That statement was written before `036272a` and was never revised; it is false at the current head, which adds the `shopify_connector_product_export` module (models, Owl component, tours and HOOT suite). The §6a HARD STOP it pointed at is itself superseded — see [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md) §5d and its §6a banner. Evidence: [`../05-qa/wave-5-completion-validation-results.md`](../05-qa/wave-5-completion-validation-results.md), [`../05-qa/task-perf1-validation-results.md`](../05-qa/task-perf1-validation-results.md), [`../05-qa/task-015-export-source-verification-2026-07-26.md`](../05-qa/task-015-export-source-verification-2026-07-26.md). **Exact-head Odoo.sh runtime and independent review remain required; nothing here is self-accepted.** |
| Wave 5 export blocker | **`productSet` omitted-list-field semantics are NOT resolved by official documentation.** D-015-3's containment argument (that `collections`, `metafields` and media are protected *by being omitted*) rests on the safe reading; the docs state only that list fields delete entries "that aren't included in the mutation's input" and that omitted **non-list** fields stay unchanged. If the strict reading holds, a first export silently deletes merchant collections, metafields and images. Resolved by one dev-store experiment, now the **prerequisite case `X-EXPORT-0`** at the head of [`../05-qa/shopify-live-validation-package.md`](../05-qa/shopify-live-validation-package.md) §4.0, which remains **neither PASS nor FAIL** and non-blocking. `[Corrected 2026-07-27]` This row previously ended "**No export code exists.**" — false at the current head, and it was added as a `+` line by the same PR that adds the export module. The blocker itself is also no longer load-bearing: the continuation ruling withdrew `productSet` as the update mutation, so the design no longer depends on omitted-list-field preservation. |
| Wave 5 | U1 Gate-A [PR #194](https://github.com/AdamsOdoo/Adams/pull/194) is **CLOSED — MERGED** (2026-07-25T22:15:01Z) at accepted head `80fbb523`, merge commit **`87f1763a`**, under independent review [`5080722794`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080722794) (`INDEPENDENT U1 GATE-A ACCEPT`; no P0/P1/material P2; five P3 deferred), control-room acceptance [`5080795232`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080795232) and merge record [`5080798692`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080798692). Merged scope: 24 paths, all `docs/**`; no `addons/**`. Accepted **only as the U1 Gate-A documentation package**: **D-P0-3 is accepted for implementation**, OQ-4/OQ-5 resolved non-blocking, and unsupported “Delivered” remains **suppressed**. **G5-1…G5-9 remain unchecked; no U1 implementation is authorized, begun or claimed; the U1 implementation base was left unbound by the merge.** Per-gate evidence-derived state, the D10 closure record and the residual U1 blockers are in [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md). |
| Release dependencies | Pre-Wave-5: warm-update fixtures #193/#157, inventory residue #198, SEC-2 #196, current-backend SEC-3 #197, external multiprocessing/lifecycle proof, minimal CI/full-suite, and pre-Wave-5 PERF-0 #199 baseline. Post-Wave-5 external package: Shopify provisioning #200, Gate D/CV-013 #185/#186, Wave-5 live scenarios, UI-delta SEC-3, performance comparison, UAT and product-owner release sign-off. |
| Wave 6 / release | Not started; no UAT or release acceptance claim. |

### Wave 5 U1 Gate A — status note (2026-07-23; corrected 2026-07-23; status-layer synthesis reset 2026-07-23; **final-backend re-anchor + bounded reconciliation 2026-07-25**)

> **PRESENT STATE (2026-07-25).** PR #194 has been re-anchored onto
> `mvp/program-integration@2583081f97c94428dfd10325589b1b891eea240b` and reconciled
> against the final integrated backend. **Everything below this banner that speaks in
> the present tense about PR #189 being unmerged, SEC-2 being unmerged, the accepted
> backend being `2d9cff0`, or integration being `dd0af5d` is a HISTORICAL snapshot of
> 2026-07-23 and is superseded.** Current: Wave 4 backend **merged** (merge commit
> `3a1afa43`; accepted head `e12145ce`; runtime candidate `25639f17`); SEC-2 **merged**,
> issue #196 **closed**; current-backend SEC-3 **merged** with issue **#197 still open**
> (narrowed to future Wave-5-added surfaces + external multi-user UAT/RC); PERF-0
> baseline **merged** with issue **#199 still open** (Shopify-read reconciliation
> handlers + release thresholds; all values baseline-only, never guarantees);
> pre-Wave-5 stabilization **merged** through PR #203. The branch/SEC-2 preconditions
> (D-P0-1, D-P0-2) are therefore **satisfied**. What still blocks U1: this re-anchored
> package has **not** been independently reviewed, **D-P0-3** is unresolved, the
> Wave-5 **G5-1…G5-9** gates are unchecked, and the control room has **not** opened the
> U1 gate or bound an implementation base SHA — the locked prompt carries an unbound
> `<U1-IMPLEMENTATION-BASE-SHA>` placeholder, and `2583081f` is the docs PR's
> reconciliation anchor, **not** an implementation base. The U1 Gate-A
> architecture-review row was **renumbered AR-079 → AR-083** to resolve a duplicate the
> merge introduced. Two items were raised for the control room and deliberately **not**
> fixed: **OQ-4** (two `ir.rule` XML IDs declared twice inside
> `shopify_connector_fulfillment`) and **OQ-5** (shipped group labels `User`/
> `Administrator` vs the "Connector User"/"Connector Administrator" role concepts).
> **No U1 implementation; no acceptance, ready-marking or merge; no issue action; no
> Shopify operation; no browser/render or runtime evidence produced or claimed.**


**Wave 5 U1 (fulfillment operator experience) Gate A / Definition-of-Ready was
prepared, then corrected once per control-room comment `5056513213`
(`REVISE — one consolidated docs-only correction`)** — docs-only, on branch
`claude/wave-5-u1-gate-a`, draft PR #194 into `mvp/program-integration`, no
`addons/**` change. Package: `docs/07-implementation-plan/wave-5-u1-gate-a/**`.
Corrected rulings: **D-P0-2 resolved SEC-2-FIRST (binding)** — no parallel
four-internal-group path; U1 customer-facing UI **visibility** = the two SEC-2 roles
(Connector User, Connector Administrator), server authorization = the four internal
groups. Branch = **Option A (binding)** — U1 implementation branches from the tip
**after PR #189 (and SEC-2) merge**; U1 UI lives inside
`shopify_connector_fulfillment` (PD-2); the mode-switch wizard is
**display-and-delegate only**; the package-import allowlist is corrected (addon root
`__init__.py` imports `wizards`; `models/__init__.py` must not import the sibling
wizards package); premium-UI browser/render evidence is **required before U1
merge**. This is Gate-A planning only: **no U1 implementation is authorized**, and
U1 code remains gated on PR #189 merge, **SEC-2 merge (runtime-green)**, D-P0-3
(load-bearing Proposed product/UX contracts still need independent acceptance), and
the wave-5 gates (G5-1…G5-9 all unchecked).

**Status-layer synthesis reset (2026-07-23, control-room ruling `5058042330`;
independent review `5057796514`):** a fresh independent review of the corrected head
`36321db` returned `REVISE` on one confirmed **material P2** — UX/IA §8 mapped the
code fields `display_status_*` to A5 `FulfillmentEventStatus` (they are A7
`FulfillmentDisplayStatus`) and asserted a phantom A2 `FulfillmentOrderStatus` badge
with no backing field. The control room ruled a docs-only **synthesis reset**: the U1
status/badge contract was re-derived from the exact Wave 4 source into **one canonical
status-source & badge matrix** (`u1-backend-ui-contract-inventory.md` §12) — A7 =
`display_status_*` (display-only, never a carrier milestone); A5 only via
`delivered_inconsistency` + parsed `tracking_snapshot`; **A2 DEFERRED — no read seam,
no badge**; A4 = `fulfillment_status_*`; layers never merged; acceptance **A22**
proves per-layer correctness. The review's six Tier-3 items were normalized in the
same commit; the fulfillment/tracking-timeline/external-review prototypes were
reconciled to §12. No `addons/**` change; no Shopify operation; not
self-accepted/ready-marked/merged. `STATUS-LAYER SYNTHESIS RESET COMPLETE — AWAITING
FRESH INDEPENDENT REVIEW`.

## 2. Product-owner calibration — effective 2026-07-22

The product owner directed the control room to preserve full rigor for load-bearing risks while stopping uniform maximum-ceremony review. The governing files now implement:

- Tier 1 full rigor for mutation logic, concurrency, idempotency, security, credentials, data integrity, runtime production defects and destabilizing performance risks;
- Tier 2 normal review for architecture/design/domain contracts, with one consolidated correction iteration expected;
- Tier 3 light-touch treatment for wording, cross-references, terminology and document structure unless they change a real contract;
- a third same-day revision as a synthesis/reset signal rather than routine incremental correction;
- early UI and performance work in parallel with Wave 4;
- mandatory wave-boundary calibration.

Mutation-safety architecture, Odoo.sh runtime requirements, citation discipline and checkpoint protections are unchanged.

## 3. Control-room self-audit — Wave 3 and Wave 4 correction rounds

### Counting method

A **round** means one control-room revise/correction cycle requiring a worker response and re-review. Multiple commits inside one coherent correction batch count as one round. This avoids inflating the audit because Task 013 used many commits to preserve reviewable checkpoints.

### Round classification

| # | Wave / gate | Round | Primary classification | Honest assessment |
| ---: | --- | --- | --- | --- |
| 1 | Wave 3 Gate A | Consolidated DEC-036 correction after independent source + architecture audits | **Load-bearing** — safety/data integrity/concurrency | Resolved eight blocking Layer 2 decisions, cursor placement, network/transaction separation, disconnect interaction, fingerprints, error routing and proof environments. Full rigor was justified. |
| 2 | Wave 3 Gate A | Two clerical merge-closure conditions | **Tier 3 polish** | DoR/table/addendum wording. These should have been fixed in-pass and should not have carried an independent full identity/review cycle. |
| 3 | Wave 3 Gate B | Revision 2 | **Load-bearing** — mutation ownership/idempotency | Corrected the unsafe same-job/two-attempt design and activation sequencing. Full rigor was justified. |
| 4 | Wave 3 Gate B | Revision 3 | **Load-bearing** — job lifetime/atomic handoff/error taxonomy | Corrected repeated-attempt risk, non-atomic handoff, undefined blocked-review behavior, invented error values and inverted freshness logic. Full rigor was justified. |
| 5 | Wave 3 Gate B | Merge-closure normalization | **Mixed; Tier 2 contract semantics with Tier 3 volume** | Several terms were implementation-significant, but the round bundled eleven wording/state-taxonomy corrections after substantive acceptance. This should have been absorbed into the prior consolidated correction/acceptance pass. |
| 6 | Wave 3 Stage 0 | Runtime/diagnostic correction | **Load-bearing** — production behavior/test validity | Corrected exception shadowing, fail-closed behavior and invalid concurrency methodology. Full rigor was justified. |
| 7 | Wave 3 Task 013 | First genuine runtime correction | **Load-bearing** — P0/P1 production/data integrity | Runtime exposed operation-scope release, review-state, exception-classification and permission defects plus fixtures. One consolidated runtime correction was correct and necessary. |
| 8 | Wave 3 Task 013 | Track B guard/concurrency closure | **Load-bearing** — test integrity/concurrency proof | Corrected a false-positive source guard and added genuine simultaneous-process concurrency proof. Necessary, though it should have been planned before the first runtime acceptance claim. |
| 9 | Wave 4 prompt preparation | Dual-review prompt reconciliation | **Tier 2 design/governance** | Canonical-output, authority, source, phase and handoff controls were materially useful, but the prompt review was oversized and should have used a focused Tier 2 checklist. |
| 10 | Wave 4 Gate A | First bounded correction | **Load-bearing** — P0 retry safety + architecture | Removed unsafe uncertain-outcome resend, fixed pagination, modularity, vocabulary, lifecycle, permissions and API-version contracts. Necessary. |
| 11 | Wave 4 Gate A | Final micro-correction | **Load-bearing** — mutation safety/operation scope/lifecycle | Closed post-C2 resend authority, shared reconciliation scope and trigger lifecycle defects. Necessary, but the findings should have been discovered in round 10's complete review. |
| 12 | Wave 4 Gate A | Late source/trigger-origin finding | **Load-bearing technical finding, inefficiently handled** | The core ORM invariant was real. Requiring another documentation round was not efficient; the issue was correctly carried as a mandatory Gate B implementation/test criterion before merge acceptance. |

### Actual ratio

- **Round-level:** 9/12 load-bearing (75%), 2/12 mixed/Tier 2 (17%), 1/12 pure Tier 3 polish (8%).
- **Strict binary by dominant trigger:** 10/12 load-bearing or contract-significant (**83%**) versus 2/12 polish-dominant (**17%**).

The audit does **not** support a blanket conclusion that most revisions were trivial. Most caught real architecture, mutation-safety, runtime or test-integrity defects. The process drift was still real for two reasons:

1. Tier 3 work consumed the same ceremony as Tier 1 work.
2. Several load-bearing findings were discovered serially across delta reviews instead of together in the first exhaustive review.

The corrective action is risk-tiering plus one consolidated correction, not weaker safety review.

## 4. Current review tier and correction count

| Active work | Tier | Reason | Correction budget |
| --- | --- | --- | --- |
| Wave 4 Gate B fulfillment implementation | **Tier 1 — merged** | Shopify mutations, Layer 2, concurrency, idempotency, security, data integrity | Backend runtime/evidence accepted and merged; live Shopify Gate D/CV-013 deferred, open and unclaimed |
| U0 UI foundation | **Tier 2** with Tier 1 security/action checks | New operator information architecture on existing hardened actions; no UI-owned mutation logic | One normal independent review; Tier 3 polish fixed in-pass; Odoo.sh mandatory because this is code |
| PERF-0 baseline | **Tier 2**, escalating to Tier 1 for unsafe findings | Benchmark design/measurement; lock/network or destabilizing regression becomes blocking | One normal review; performance defect batch consolidated |
| Governance calibration | **Tier 2 — merged** | Program sequencing/review policy, no production code | One consolidated correction and one verification-only review completed through PR #191 |

## 5. Pre-Wave-5 stabilization and current boundaries — 2026-07-25

### Single active stabilization PR

Use only `sol/pre-wave-5-stabilization`, branched from `mvp/program-integration@3a1afa43f8d07a7dae1799968273fa0ab8049490`, until every inherited non-Shopify debt item is closed. Keep corrections on the same PR in controlled commits; do not start Wave 5 or create parallel hardening PRs.

Required closure workstreams:

1. correct warm-update fixture debt #193 and overlapping #157 with fresh-install and warm-update proof;
2. remove exact-ID, FK-safe inventory concurrency residue under #198 and prove repeated zero residue;
3. implement and runtime-prove SEC-2 #196;
4. complete the current-backend SEC-3 #197 model/sudo/company-isolation audit and corrections;
5. execute genuine external multiprocessing and remaining lifecycle proof in a capable disposable Odoo environment;
6. add minimal CI/reproducible continuous full-suite execution with durable exact-SHA artifacts;
7. capture the reproducible pre-Wave-5 PERF-0 #199 baseline;
8. audit and disposition TODO/FIXME, skipped/disabled tests, stale compatibility workarounds, known-failure classifications, and untracked P0/P1/material-P2 debt;
9. synchronize the three D10 tracker surfaces and obtain independent acceptance before merge.

### Stabilization implementation progress — 2026-07-25

`[Fact — implemented, NOT accepted]`. PR #203 now carries the implementation for
workstreams 1-8. **No issue is closed and nothing is accepted**: every item below
still requires exact-SHA Odoo.sh runtime evidence and independent review.

| Workstream | State |
| --- | --- |
| #193 / #157 warm-update fixtures | Implemented + locally executed. Warm `-u` went from 96 errors of 1270 tests to **0 failed, 0 errors of 1440**. Enforced by a new static phase-contract guard. |
| #198 inventory residue | Implemented + locally executed. Exact-id FK-safe teardown; repeated-cycle zero-residue proof. |
| #196 SEC-2 roles | Implemented + locally executed (20 tests). Additive Option M-A. [Issue #196](https://github.com/AdamsOdoo/Adams/issues/196) defines the SEC-2 **role layer** — two customer-facing roles over the existing internal capability groups — and that is exactly what is implemented. The earlier PR-body wording describing this as only "the role half" of #196, with a "PII-masking half" still outstanding *within #196*, was unsupported and is withdrawn: #196's own scope and definition of done contain no PII-masking obligation. The MVP PII simplification is a **separate** documented obligation in [`task-sec2-two-role-and-pii-simplification-packet.md`](task-sec2-two-role-and-pii-simplification-packet.md); it is neither claimed nor closed here, and it is not a precondition of #196. |
| #197 SEC-3 isolation | **Reworked 2026-07-25 after control-room correction.** The first pass classified 9 control-plane models as NEUTRAL, leaving stores, credentials, settings, locations, jobs, logs, attempts and leases cross-company readable — which did not satisfy #197. Now store-rooted: `store.company_id` is the single ownership root, 17 durable models inherit it, 18 fail-closed record rules, Odoo-native `_check_company` on every binding, upgrade-safe backfill with an administrative remediation path, and `order_company_id` constrained to agree with the store. 41-test matrix. Gated on external UAT/RC; U1 delta out of scope. |
| #197 SEC-3 — 2026-07-27 delta, corrected 2026-07-28 | `[Corrected 2026-07-28]` **Still open.** Draft PR #204 extends implementation coverage over its own new surface — 2 models, 20 stored fields, 7 non-stored computed fields/relations, 18 public/RPC methods, 15 elevated methods over 19 `sudo()` call sites — inventoried in [`../03-architecture/sec3-company-isolation-audit.md`](../03-architecture/sec3-company-isolation-audit.md) §8, with a local two-company/two-role negative matrix over every one. One genuine cross-company defect was found and fixed doing it: a non-stored computed field whose contents record rules filter is cached once per record for the whole transaction unless it declares `depends_context`, so the first reader's result was served to the second in either direction. A fresh independent review of that head found a SECOND genuine cross-company defect in the same delta — the TD-015 acknowledgement wizard's own `binding_id`/related display fields had no equivalent isolation at the wizard-model boundary — corrected 2026-07-28 (§8.9 of the same document), along with three arithmetic/scope corrections to this section's own headline count (the prior "17/20/14" did not match the section's own itemized tables). **Implementation coverage is not acceptance:** #197's independent Tier-1 security review and exact-SHA runtime evidence do not exist for that head, including its corrected head. |
| S1 guided setup — 2026-07-27 | `[Corrected 2026-07-27]` **IMPLEMENTED and locally qualified, NOT ACCEPTED** on draft PR #204. All 11 accepted steps in the accepted order, Administrator-only and server-enforced on every entry point, three entry routes, credential write-only, activation starts no sync. Previously recorded as not implemented, which was accurate until this cycle. No independent review, no Odoo.sh runtime, no live-Shopify, no UAT. |
| CI — 2026-07-27 | `[Corrected 2026-07-27]` **CI exists** (`.github/workflows/connector-tests.yml` over `tools/run_connector_suite.sh`: fresh install, warm `-u`, the complete non-standard tag set, pinned Odoo, source-head verification, browser preflight, fail-closed on an unexpected skip or a missing tour/HOOT marker). Earlier "no CI" statements are historical. CI remains **supporting evidence, not acceptance** — the exact-SHA Odoo.sh run is still the Tier-1 authority (DEC-041 D8). |
| TD-002 — 2026-07-27 | `[Corrected 2026-07-27]` Backend implementation **accepted and merged through PR #189** (merge `3a1afa43`, accepted head `e12145ce`, runtime candidate `25639f17`). It is no longer "owned by an open PR". Its deferred **live-Shopify validation, Gate D, CV-013 #185, external UAT and final release evidence remain open** and are claimed by nothing in Wave 5. |
| Multiprocessing / lifecycle | **Executed for the first time.** Core 3/3 and fulfillment 9/9 external-process scenarios pass with distinct OS PIDs and zero residue; three harness defects corrected. Uninstall→reinstall clean (21 tables → 0 → 21, zero metadata residue). |
| CI (DEC-041 D8) | **Corrected 2026-07-25.** The first version defaulted its tag list to empty and the workflow passed no tags, so the eight `-standard` classes were still never run continuously — D-6/D8 were reported fixed by a mechanism that excluded exactly the tests in question. The runner now executes fresh-standard, warm-standard and the complete non-standard tag set by default (skipping is opt-*out*), each into its own database with its own log and machine-readable result. Odoo is pinned to an immutable SHA in `tools/odoo-pin.txt`, verified every run, with the Actions cache keyed on the pin file. Supporting evidence only; Odoo.sh remains the Tier-1 authority, and no green Actions run exists yet. |
| #199 PERF-0 | **Corrected 2026-07-25.** The first version reported `pg_stat_statements.total_exec_time` as `lock_wait_ms_delta` (it is statement execution time, not lock wait) and its "contention" scenario was single-process and uncontended. Now: the metric is named `sql_exec_time_ms_delta` and kept as an execution-time statistic only; genuine two-connection blocking contention is measured directly with PostgreSQL's own `wait_event` plus a SKIP-LOCKED comparison; order, inventory and fulfillment scan/reconciliation workloads added over seeded datasets; residue swept across 16 tables with FK-safe teardown. Baseline-only — no threshold is asserted. |
| Repository debt | 20 findings recorded in [`pre-wave-5-debt-discovery.md`](../05-qa/pre-wave-5-debt-discovery.md) (13 original + D-14..D-20 from the control-room correction). Notably: 8 `-standard` classes never ran in any suite, and the first "fix" for that did not actually run them either. |

Runtime used: local disposable Odoo 19 pinned to
`30bde9ff758834a4912c5ae55843d3a7dad849f1` (the same commit as the first
campaign, so the numbers stay directly comparable) + PostgreSQL 16.13, Python
3.12. This is a faithful reproduction, **not** a substitute for Odoo.sh. Full
connector suite on the corrected head: **0 failed, 0 errors of 1503 tests**. No
Shopify store, credential, request or mutation was involved at any point.

**Correction-round validation, executed locally on the corrected head.**

| Campaign | Result |
| --- | --- |
| Fresh install + connector suite | 0 failed, 0 errors of 1504 |
| Warm `-u` + connector suite | 0 failed, 0 errors of 1504 |
| Non-standard `-standard` tag suite | 0 failed, 0 errors of 18 |
| Core external-process Layer-2 harness | 3/3 scenarios, distinct OS pids, zero residue |
| Fulfillment external-process harness | 9/9 scenarios, distinct OS pids, zero residue |
| Install → uninstall → residue sweep → reinstall | 21 tables → 0 (zero `ir_model_data`/`ir_model`/`ir_rule`/group residue) → 21 |
| PERF-0 | 11 scenarios, zero residue failures; contention `conclusive=true`, `wait_event_type=Lock` |
| Suite runner exit code | 0, artifact records the exact SHA and `worktree_dirty=false` |

**Correction round — 2026-07-25.** The control room reviewed the first
stabilization head (`d28633b`) and returned `REVISE ONCE BEFORE EXACT-SHA ODOO.SH
VALIDATION` with a complete finding set: the implementation record understated
the change (23 files described only the second push; the full PR is 94 changed
paths), continuous validation excluded the non-standard classes it was meant to
cover, SEC-3 classified the control-plane leak as neutral instead of closing it,
and PERF-0 mislabelled execution time as lock wait. All findings are corrected on
the same PR #203, with no rebase and no force-push.

**Second correction round — 2026-07-25 (evidence integrity).** The control room
reviewed `156a4a7` and returned three confirmed evidence-integrity gaps, all now
corrected on the same PR #203 with no rebase and no force-push:

| Gap | Correction |
| --- | --- |
| **Actions run 30153827606 was not exact-head evidence.** It succeeded (1504 fresh, 1504 warm, 18 non-standard) but its artifact recorded `connector_sha: 60ea6690…` — GitHub's synthetic PR *merge* commit, not head `156a4a74…`. Classified **EXECUTED — PASS ON SYNTHETIC PR MERGE REF; NOT EXACT-HEAD EVIDENCE**; its results are retained, not discarded, and not called failed. | The workflow checks out `github.event.pull_request.head.sha`; the runner verifies its checkout against the declared source head and **aborts** rather than publishing a mismatch; the artifact records tested checkout SHA, source head, base, event, worktree state, Odoo SHA, Python and PostgreSQL versions. |
| **PERF-0 residue claims excluded business fixtures.** Partners, product templates, generated variants, sale orders and lines were created and never captured, deleted or verified. Two further layers surfaced on the first honest teardown: 350 mutation attempts and 7 jobs per scenario created by *production* paths, and 50 `product.value` valuation rows per scenario created as a side effect. | Every row tracked by exact id; rows above a pre-run per-table watermark adopted (a watermark cannot reach a pre-existing row); FK-safe child-before-parent teardown; absence re-verified from a new transaction; a whole-database `id > watermark` sweep that no future fixture can escape; **two full passes in the same database**, second starting from the identical baseline. |
| **PERF-0 labels and contention overstated.** Three scenarios named `*_scan` performed a `search` and a `read`. The contention measurement blocked with raw SQL `FOR UPDATE`, a path the connector never takes. | Renamed `*_projection`; the real network-free cron admission paths added as separate scenarios; the **production** claim path (`_claim_for_dispatch` → `try_lock_for_update` → `FOR UPDATE SKIP LOCKED`) exercised against a held row, its **no-wait** behaviour reported as the production result; the raw blocking experiment retained and relabelled `database lock calibration`. |
| **SEC-3 tests described more coverage than they performed**, and same-**store** agreement was unenforced on five relations. | One authoritative inventory drives every test; a completeness guard fails on any uncovered durable store-scoped model or undeclared connector relation; `shopify.connector.scope.mixin` adds ORM constraints for new rows and a non-guessing quarantine for historic ones. |

**Still open after this round:** exact-SHA Odoo.sh runtime, a first exact-head
green Actions run observed on the corrected head, and independent Tier-1 review.
Issues #157, #193, #196, #197, #198 and #199 all remain open. #199 in particular
stays open because the per-record reconciliation **handlers** perform Shopify
reads and cannot be measured by any local harness; no fake transport was
introduced to manufacture a number.

### Shopify-only deferred package

The 2026-07-25 product-owner ruling defers only validation requiring a live Shopify store, credential, API request, or mutation until the Wave-5 implementation candidate is complete and frozen. Issues #185, #186, and #200 remain open. Gate D/CV-013, applicable Wave-5 live scenarios, external UAT, and release readiness are not waived or claimed.

Official Shopify documentation checks, schema/contract validation, automated tests, fail-closed behavior, security work, and all other non-live obligations continue now.

### Frozen until stabilization closes

> **SUPERSEDED 2026-07-25 (D10 closure).** Stabilization closed with PR #203
> (`2583081f`) and PR #194 has since been accepted and **merged** (`87f1763a`).
> The first bullet below is historical. Current state:
> [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md).

- ~~PR #194 remains untouched and frozen.~~ **Merged 2026-07-25 at `87f1763a`.**
- No Wave-5 implementation branch or implementation PR is authorized. **Still
  current:** the U1 gate remains closed on G5-4 (PERF-1 packet not accepted) and
  on the absence of an explicit control-room act opening the U1 gate. The
  implementation base is now **bound to `87f1763a`** by product-owner instruction.
- “Delivered” must not be exposed until a real backend seam is separately authorized, implemented, and independently proven.
- No UAT or release-readiness claim is authorized.


## 6. Realistic forward timeline

Assumptions: Odoo.sh remains accessible; a disposable Shopify development store and dedicated fixtures are available by early August; no new feature scope is added.

| Milestone | Expected window | Confidence / dependency |
| --- | --- | --- |
| Wave 3 residual live closure | 2026-07-23 to 2026-07-31 | Medium; depends on dev-store fixtures. Inventory code itself is already merged. |
| Wave 4 backend integration | Complete 2026-07-25 | PR #189 merged at `3a1afa43`; live Shopify proof remains deferred and unclaimed |
| Pre-Wave-5 stabilization | Starts from `3a1afa43`; ends only after all inherited non-Shopify debt is accepted and merged | Single active stabilization PR; no Wave-5 implementation in parallel |
| Consolidated Shopify campaign | After the Wave-5 implementation candidate is complete and frozen | Covers deferred Wave-4 Gate D/CV-013 plus applicable Wave-5 live scenarios |
| U0 first usable UI slice | 2026-07-23 to 2026-08-06 | Medium/high; read-only/hardened surfaces can run in parallel |
| PERF-0 baseline + Wave 4 comparison | 2026-07-27 to 2026-08-10 | Medium/high if benchmark environment is available |
| Wave 5 full UI/export/SEC-2/PERF-1 | 2026-08-10 to 2026-09-08 | Medium; use separate UI/export workstreams with one integration gate |
| Wave 6 full UAT/release readiness | 2026-09-07 to 2026-09-23 | Medium/low; depends on all mutation/dev-store gates |

**Realistic release-candidate range:** 2026-09-14 to 2026-09-25.

**Accelerated credible range:** 2026-09-04 to 2026-09-11, only with parallel U0/PERF work, timely Shopify access, no new scope, and no Tier 3 review loops.

## 7. Critical path and levers

Critical path:

1. close and merge every inherited non-Shopify stabilization item;
2. freeze the exact clean Wave-5 base and transfer PR #194 without unsupported Delivered exposure;
3. complete Wave-5 implementation on one active branch/PR;
4. run the consolidated Shopify campaign for deferred Wave-4 and applicable Wave-5 scenarios;
5. complete integrated UAT and release qualification.

If schedule slips, use these levers in order:

1. eliminate Tier 3 gate ceremony;
2. parallelize UI, benchmark and export work with explicit file boundaries;
3. reject new feature additions until release;
4. defer only non-critical Task 013B or UI embellishment through an explicit product-owner scope decision;
5. never relax mutation safety, security, runtime or dev-store evidence.

## 8. Next actions

> **Refreshed 2026-07-25 (D10 closure).** Items 1, 2 and 4 of the previous list are
> **done**: the stabilization PR opened, executed and merged (PR #203, `2583081f`),
> and PR #194 was accepted and merged (`87f1763a`) with “Delivered” suppressed.

1. **Control-room act — open or explicitly re-sequence the Wave 5 gates.** Per
   [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md) §4, six of
   the nine gates are substantively earned by merged, independently accepted
   evidence and need only a check; **G5-4** (PERF-1 packet) and **G5-5** (export
   PDs) are genuinely unearned and need acceptance acts no worker may perform.
   G5-5 gates Task 015/015B only, not U1.
2. **Decide the G5-7 authority question:** whether the exact-base Actions run
   `30177207908` (`success` on `87f1763a`) satisfies "SEC-1 intact at the Wave 5
   base", or an exact-SHA Odoo.sh run at `87f1763a` is required.
3. **Then, and only then, authorize U1 implementation** at the bound base
   `87f1763a`. The locked prompt is otherwise ready: its base is bound and its
   backend contract is proven to hold at that base by `addons/` tree identity with
   `2583081f`.
4. Assign an owner to the **MVP PII-simplification** obligation, which is a
   separate item from #196 and is currently tracked by no issue.
5. Keep #185/#186/#197/#199/#200 open and make no Shopify request or mutation.


## 9. Wave-boundary calibration template

At every wave boundary append a compact entry:

- tier and reason;
- initial review count and correction count;
- substantive/Tier 3 finding count;
- cycle-cap compliance;
- elapsed time vs forecast;
- UI/PERF status;
- next milestone/date/dependency;
- process adjustment, or `none` with evidence.