# Implementation-Ready Master Plan — Sequence, Gates, and What Starts After Acceptance

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-10 (AR-042 candidate); **revised 2026-07-11** by
> the PR #148 revision session per ChatGPT's control-room review
> (comment `4942966937`) — the critical path no longer begins with
> Task 012 (§2), the review calls are re-enumerated (§1), and the new
> packets (CORE-R1, 010B, 011B, 013B, 015B, SEC-1, LC-1, U0) are
> sequenced. Every implementation step remains gated by its own
> distinct ChatGPT act; **bold** marks ChatGPT acts. Packets live in
> `../07-implementation-plan/*-packet*.md`; UAT
> (`final-mvp-uat-plan.md`, 36 scenarios); release
> (`release-readiness-execution-plan.md`); budgets
> (`../03-architecture/performance-budgets.md`); design system
> (`../03-architecture/premium-ui-ux-design-system.md`); lifecycle
> (`../03-architecture/module-lifecycle-uninstall-design.md`).
> **Final-convergence revision 2026-07-11 (comment `4947866018`):** the
> critical-path sequence and gates are **unchanged**; six packets were
> refined in place — PERF-1 (official `_commit_progress` transaction
> model; `max_in_flight` deferred to the concurrency plan), 013B
> (DB-backed apply lock), 012 (tax-preserving discount lines + rate-unit
> pinning), 015B (detach-only, no automatic `fileDelete`), 010B
> (`try_lock_for_update()` attribute serialization), SEC-1/LC-1 wording.
> Closure map: audit §8.6.

## 1. Decisions ChatGPT makes when reviewing this PR (one review; carried-over calls A1–A11 + revision calls B1–B10)

**Carried over from the 2026-07-10 package (content unchanged unless
noted):**

- **A1** Accept/revise DEC-027 (branch-A pilot scope).
- **A2** Accept/revise DEC-028 — **now including the revised Rung-1
  point-2 production-entry criteria** (review item 8).
- **A3** Accept/revise DEC-029 (Lite/Full packaging — Lite definition
  revised: "no connector write-back modules", never an Odoo-stock
  statement) + ARCH PD-1/PD-2.
- **A4** Ratify ARCH PD-3..PD-6.
- **A5** Confirm the flagged Task-012 interpretations (D-012-3
  `JobPolicySkip` seam; D-012-4 hold; D-012-6 address children;
  `shopify_line_item_gid`) — **plus the 2026-07-11 revisions:
  D-012-2 component tolerance, D-012-7 no-default confirmation
  policy, D-012-9 mapping-first taxes with autocreate default False.**
- **A6** Confirm D-013-5 (third named sudo) and D-013-8 — **which now
  reads "split to the fully-planned Task 013B", not "deferred to a
  candidate".**
- **A7** Confirm D-014-2 (TD-002 fix), D-014-6, and the Task-014
  `trigger_origin` selection_add.
- **A8** Confirm D-015-7 — **now "media = fully-planned Task 015B",
  not a deferral** — plus the D-010B-5 compare-at field relocation.
- **A9** Confirm D-A6-1/D-A6-5 (Area-6 split + job-action services) —
  **D-A6-7 moved to CORE-R1 (call B1).**
- **A10** Confirm the webhook MVP-tail scoping (W1+W2 in MVP, W3–W5
  out).
- **A11** *(optional)* OP-42 wording; AR-040 status cell.

**New calls created by this revision (each Proposed, NOT accepted):**

- **B1** Accept the **Task CORE-R1 packet** (D-R1-1..5) — incl. the
  explicitly flagged `webhook_hmac` not-applicable relaxation
  (D-R1-3) and the D-R1-5 `api_health_state='normal'` write site.
- **B2** Accept the **Task 010B packet** (D-010B-1..12) — incl. the
  dynamic-variant strategy (D-010B-2/3) and the basic-media scope
  with the 010C gallery deferral (D-010B-6/6a).
- **B3** Accept the **Task 011B packet** (D-011B-1..7) — incl. the
  one `res.partner` stored-field call (D-011B-1).
- **B4** Accept the **Task 013B and 015B packets** — completing the
  accepted DEC-003 scope (recommended) instead of narrowing it; incl.
  D-013B-4/6 and D-015B-2/7 flagged calls.
- **B5** Accept the **SEC-1 packet** (D-SEC1-1..7) — incl. the
  su-guard-over-ACL-rows design choice and the matrix-binds-sudo rule.
- **B6** Accept/revise **DEC-030** (lifecycle/uninstall; ARCH PD-8;
  Task LC-1 — **now with a full locked prompt (lifecycle doc §7.1) and
  sequenced before Task 012 so every new-job-type packet adopts the
  `_reassign_to_historic_job_type` callable from day one**) — or
  choose its named Option-D alternative.
- **B7** Accept **ARCH PD-7 + the premium design system** — incl. the
  §9 dashboard-hierarchy revision of the accepted nine-card layout
  and the severable §9.5 sparkline sub-call.
- **B8** Accept **ARCH PD-9 / the performance-budget table**
  (PB-1..23) as binding-until-recalibrated.
- **B9** Accept the **revised UAT severity model** (S2-UX class) and
  the 36-scenario catalogue.
- **B10** **Authorize the U0 visual-design/prototype session** (its
  allowed files incl. `docs/09-ui-prototype/**`; PNG+md default —
  UI-U1 stays locked until the prototype is accepted in a recorded
  act).
- **B11** Accept the **Task PERF-1 packet** (core queue throughput
  calibration — the Odoo 19 `ir.cron._commit_progress()` per-job-savepoint
  transaction model, configurable per-pass-cap/cadence, lock-safety,
  Shopify backpressure; `max_in_flight`/overlap deferred to the
  topology-B concurrency plan) so PB-19 (≥ 600 jobs/hour) has a gated
  implementation owner, sequenced before performance UAT (re-review
  `4945129824` item 5; transaction model corrected per final-convergence
  `4947866018` item 1).

Accepting the PR without naming exceptions accepts A1–A10 and
B1–B9/B11 as proposed; A11 is optional; **B10 is an authorization act
that must be explicit** (it schedules work). Every locked prompt
remains unusable until its own gate act.

## 2. Critical path (revised — each step: **gate act** → one implementation session → draft PR → **merge review** → runtime-green closure)

| # | Step | Packet / prompt | Prereqs | Why here |
| --- | --- | --- | --- | --- |
| 1 | **Task CORE-R1** readiness correction | task-core-r1 packet §8 | This PR merged | No store can reach `connected` today — everything live downstream needs this first |
| 2 | **Task 010B** product import completeness | task-010b packet §10 | CORE-R1 merged | DEC-003 product-import scope must be real before orders consume variant bindings |
| 3 | **Task 011B** customer matching scalability | task-011b packet §9 | Task 011 (fact) | Order import reuses matching at order volume; may run **in parallel with 010B** (disjoint modules) — kept as step 3 for review clarity |
| 4 | **Task LC-1** lifecycle enablement | lifecycle doc §7.1 | CORE-R1 merged | **Moved here (re-review item 7): the `_reassign_to_historic_job_type` callable + `original_job_type` must exist in core BEFORE any new `job_type` is registered, so Tasks 012/013/013B/014/015/015B/Area-6 adopt it from day one and the two merged job types are converted — no uncontrolled later retrofit** |
| 5 | **Task 012** order import | task-012 packet §15 | CORE-R1 + 010B + 011B + LC-1 merged | Revised prerequisites in-packet; adopts the LC-1 callable |
| 6 | **Task 016 / Area 6** triggers | area-6 packet §7 | 012 merged | Closes UAT blocker U-4; D-A6-7 no longer here |
| 7 | **Task SEC-1** security hardening | task-sec1 packet §9 | Area 6 merged | Hardens the substrate incl. Area-6's services **before any UI button exists** |
| 8 | **U0 visual prototype gate** | ui packet §7 prompt | B10 authorization | Design-only; **may run in parallel from acceptance onward**; must be accepted before step 9 |
| 9 | **UI Phase U1** | ui packet §6 prompt | Area 6 + SEC-1 merged; U0 accepted | Dashboard per design system §9 |
| 10 | **Task 013** inventory → **Task 013B** baseline | task-013 §8 / task-013b §9 | 010B merged (013); 013 merged (013B) | First mutation task; dev-store evidence rule active; both adopt the LC-1 callable (LC-1 already merged at step 4) |
| 11 | **Task 014** fulfillment | task-014 packet §8 | 012 merged | Carries the TD-002 fix |
| 12 | **Task 015** product export → **Task 015B** media export | task-015 §8 / task-015b §9 | 010B merged (015 consumes complete variants + compare-at field); 015 merged (015B) | Completes DEC-003 catalog scope incl. media |
| 13 | **UI U2** (wizard/readiness) | ui packet §1 (prompt post-U1) | U1 merged; VAL-B2 strongly recommended first | |
| 14 | **UI U3** (domain screens) | ui packet §1 (prompts per domain post-U1) | U1 + each domain merged | Rolling — may interleave with 10–12 |
| 15 | **W1 + W2** webhooks (MVP tail) | webhook packet §6 | Area 6 + U1 merged | W1 replaces the CORE-R1 webhook_hmac pass with the real check |
| 16 | **Task PERF-1** core queue throughput calibration | task-perf1 packet §9 | merged core dispatcher; domain tasks mergeable | **Before performance UAT (re-review item 5): calibrates the dispatcher to PB-19 (≥ 600 jobs/hour) — the accepted 5-min×20 defaults cap at ~240/h; may run ∥ the P-B concurrency plan** |
| 17 | **UAT waves 1–4** | final-mvp-uat-plan (36 scenarios) | per its §2/§6; PERF-1 merged for the performance scenarios (27/28/34) | Human reviewer sessions; numeric PB pass/fail |
| 18 | **Release execution + Go/No-Go** | release plan | UAT exit; budgets table measured; DEC-028 point-2 evidence | **The release act** |

Deviation note vs the review's expected order: identical through
step 3; **LC-1 is pulled up to step 4 (before Task 012)** so the
historic-job reassignment callable exists before any new `job_type`
is registered (re-review item 7 — no later retrofit); steps 10 and 12
group the domain tasks with their B-completions (013→013B, 015→015B);
**Task PERF-1 is inserted at step 16, before the UAT performance
scenarios** (re-review item 5); U0 is marked parallelizable because it
is design-only and gates only U1. Parallel-safe pairs are named in the
table; nothing else may overlap.

### 2.1 Proposed CORE-R2 dependency (under review — NOT an accepted reorder)

> **Inserted 2026-07-12 by the CORE-R2 design session** (gate comment
> PR #153 `4950413650`, docs-only). **Revised twice 2026-07-12** — per
> review `4951115877` (broaden the dependency from Shopify *mutations* to
> **any Shopify call including reads**) and per review `4951237871`
> (committed-lease quiescence; explicit `execute_business` boundary;
> base re-aligned by normal merge to
> `65e915aada32930a19a14c94d23dc9bd5e6fb517`, U0/PR #152 preserved). This
> subsection **adds a proposed dependency only** — it does **not** renumber
> or reorder the accepted §2 steps. **CORE-R2 design is under review; no
> CORE-R2 implementation gate is open.**
>
> **Cross-module note (rev 3):** making INV-2 real requires **two minimal,
> named call-site edits** in existing domain importers —
> `shopify_connector_product` (product import) and `shopify_connector_sale`
> (customer import) — to route their Shopify reads through the guarded
> `execute_business(job, …)` entry. The CORE-R2 packet's future allowlist
> names exactly those two call sites (call-site-only). This is an
> additional reason CORE-R2 must land before those handlers are
> live-validated; ChatGPT sequences the two edits vs Tasks 010B/011B at the
> CORE-R2 gate (D-CR2-E).

**Task CORE-R2 — disconnect quiescence & in-flight job contract** remediates
the **runtime-confirmed** DEF-PB-1 / SRR-03 (PR #153, accepted `4950408383`):
a concurrent real `action_disconnect()` does **not** stop an already in-flight
business handler. Design + packet:
[`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md),
[`../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`](../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md).

Proposed placement (for ChatGPT to ratify — call **D-CR2-E**):

- **CORE-R2 must be resolved (merged runtime-green) before UAT** (§2 step 17)
  and before the Go/No-Go release act (step 18). It is a UAT prerequisite.
- **The defect applies to ANY Shopify call, including reads** (the contract
  promises "no further Shopify call", not merely "no further mutation").
  Therefore CORE-R2 must be runtime-green **before merging, enabling, or
  live-validating any domain handler that can call Shopify** — this includes
  **Task 010B product-import live validation** (§2 step 2), **Task 011B
  customer-import live validation** (step 3), **Task 012 order-import live
  validation** (step 5), and **Tasks 013–015** (steps 10–12), as well as UAT.
- **Handling the already-open Task 010B and Task 011B PRs:** their
  development and review **may continue in parallel** with CORE-R2; only their
  **final integration / live enablement / live Shopify validation** waits for
  CORE-R2 to be merged runtime-green — **unless** a given handler path is
  proven to contain **no Shopify call** (in which case it is unaffected and may
  proceed). CORE-R2 is `shopify_connector_core`-only and independent of the
  domain modules, so it can be developed and merged concurrently. Its external
  validation is the **P-B concurrency track** (§3) that produced the runtime
  evidence.
- **Recommended sequencing:** run CORE-R2 **early — after CORE-R1 and in
  parallel with 010B/011B** — so it is merged and proven before any domain
  handler's live validation.
- **Sequencing constraint:** the CORE-R2 packet adds one store state
  (`disconnecting`), new store/job fields (incl. `connection_generation` /
  `expected_connection_generation`), a dedicated quiesce-controller `ir.cron`,
  and the central API-client gate; to avoid a later retrofit, land these
  **before or with Task LC-1** (§2 step 4, the historic-job-type reassignment)
  so they participate in that lifecycle from day one.

No §2 step is moved by this note; the concrete insertion point is **D-CR2-E**
at CORE-R2 gate time. Until then the CORE-R2 implementation gate is **closed**.

## 3. Parallel external tracks (independent of the chain; start any time)

Unchanged: **P-A** VAL-B2 execution (human, live store — also feeds
010B/013/015 dev-store evidence); **P-B** concurrency plan execution
(runtime — also measures PB-18/19); **P-C** docs-maintenance
micro-patch (OP-25 residue); **P-D** Phase-2+ preparation (DEC-028
Rung-2 evidence; B-1 planning under RA-003's own future lift act).
New: **P-E** the U0 visual-design session (after B10).

## 4. Deferred-with-names (not lost)

010C product media gallery import; 015C media gallery/video export;
W3/W4 webhook accelerations; add-on modules
(accounting/refund/payout/multi-store); OAuth/B-1/App Store/billing/
compliance (Phase 2+); entitlement/licensing mechanics (Phase 2
commercial); dark mode (design system). **No longer deferred:** 013B
and 015B (now steps 10/12); the readiness closure (step 1); LC-1
lifecycle enablement (now step 4, full locked prompt at lifecycle doc
§7.1); PB-19 throughput (now owned by Task PERF-1, step 16); budgets
(exist now).

## 5. The exact next implementation session after acceptance

**Task CORE-R1**, using the locked prompt at
`../07-implementation-plan/task-core-r1-readiness-correction-packet.md`
§8, issued verbatim by ChatGPT in a new session after: this PR
merges, the CORE-R1 gate act is performed, and the base SHA is
stated. (Task 012 is now step 5 — after CORE-R1, 010B, 011B, and LC-1
— not the next session; the 2026-07-10 claim is superseded.) In
parallel, at ChatGPT's discretion: the B10 U0 authorization and the
P-A/P-B external validations.
