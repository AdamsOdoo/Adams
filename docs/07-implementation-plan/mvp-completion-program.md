# MVP Completion Program — Odoo 19 ↔ Shopify Connector

> **Current canonical program contract — calibrated 2026-07-22.** Governance authority remains `DEC-032-mvp-autonomous-execution-model.md`, subject to the current Wave 4 authority clarification recorded on issue #186. The immutable checkpoint and all accepted mutation-safety, concurrency, security, runtime-evidence and branch-protection decisions remain unchanged.
>
> The complete pre-calibration program snapshot is archived at [`archive/mvp-completion-program-through-2026-07-22.md`](./archive/mvp-completion-program-through-2026-07-22.md). It remains historical evidence, not the live execution contract.
>
> Live status, dates, branches, blockers and wave-boundary calibration live in [`mvp-program-state.md`](./mvp-program-state.md). Feature/evidence traceability lives in [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md). Review depth and correction-cycle rules live in [`../06-prompts/claude-mvp-wave-review-template.md`](../06-prompts/claude-mvp-wave-review-template.md).

## 1. Non-negotiable program controls

The calibration changes review ceremony and sequencing efficiency. It does **not** relax:

- Layer 1/Layer 2 replay-safety and mutation ownership;
- CAS/operation-scope concurrency protection;
- one-job/one-attempt and reconciliation-before-retry contracts;
- fixed error/review vocabulary;
- server-side security, credentials and PII/redaction controls;
- genuine Odoo.sh runtime evidence before a backend domain is accepted;
- genuine dev-store proof before a Shopify-mutation domain receives final acceptance;
- citation and official-source discipline for Shopify/Odoo facts;
- the immutable checkpoint and protected-reference rules;
- no worker self-acceptance, ready-marking or merge.

## 2. Checkpoint and protected references

| Field | Value |
| --- | --- |
| Checkpoint issue | #165 — CORE-R2 Read-Only UAT Foundation |
| Immutable checkpoint branch | `checkpoint/core-r2-readonly-uat-2026-07-15` |
| Checkpoint integration SHA | `acd8c4691e72cf5590f2a56228b08f183b76cd9a` |
| Program integration branch | `mvp/program-integration` |
| Current integration SHA at calibration | `01f072dd4d83b7b39737452a686244a3a8c00332` |
| Odoo target | 19.0 |

Never modify, reset, delete, advance or force-push the checkpoint, `Shopify-connector`, `main`, issue #165, PR #150, PR #151 or any later published checkpoint/tag without a separate explicit product-owner act.

## 3. MVP scope — unchanged

The MVP still includes:

1. store connection/readiness and secure credentials;
2. test connection and guided setup;
3. operational dashboard;
4. product/variant import and controlled export/update with basic media export;
5. customer import and deterministic matching;
6. Shopify order import into Odoo sales orders;
7. inventory synchronization with duplicate prevention and reconciliation;
8. fulfillment/tracking through Shopify FulfillmentOrder surfaces;
9. scheduled and manual synchronization;
10. operator-friendly logs, retries and manual review;
11. mapping/configuration and roles/access screens;
12. install/upgrade/uninstall proof;
13. end-to-end tests, performance evidence, dev-store UAT and release readiness.

Confirmed excluded from this MVP remain: payout reconciliation; advanced refunds/accounting automation; Shopify Markets; subscriptions; gift cards; POS; B2B; metafields; advanced analytics; app-store packaging; complex multi-company; broad multi-store orchestration.

### D10 synchronized state — 2026-07-25 (post-merge closure)

- **`mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` is the live tip.** It is the ordinary merge commit of Wave 5 U1 Gate-A [PR #194](https://github.com/AdamsOdoo/Adams/pull/194) (accepted head `80fbb523`) onto pre-Wave-5 stabilization [PR #203](https://github.com/AdamsOdoo/Adams/pull/203) (`2583081f`). Earlier tips `3a1afa43` (PR #202 + PR #189) and `2583081f` are historical.
- PR #194 merged docs-only — 24 paths, every one under `docs/**`, zero `addons/**` — under independent review [`5080722794`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080722794), acceptance [`5080795232`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080795232) and merge record [`5080798692`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080798692).
- Wave-4 runtime evidence remains tied to implementation candidate `25639f17be14b30a52a8453f0813aa0b764de310`, Odoo.sh build `35422036`; the later reconciliations changed trackers and docs only, and no `addons/**` or test path. The `addons/` tree is byte-identical at `2583081f` and `87f1763a`.
- Inherited non-Shopify stabilization debt closed through PR #203; SEC-2 #196 is closed. **Issues #197 (SEC-3) and #199 (PERF-0 thresholds) remain open.**
- **Wave 5 implementation has not started and is not authorized.** U1 Gate-A planning is accepted and merged, but G5-1…G5-9 remain unchecked — G5-4 (PERF-1 packet) and G5-5 (export PDs) are genuinely unearned. Per-gate evidence-derived state and the residual U1 blockers: [`wave-5-completion-gate-state.md`](./wave-5-completion-gate-state.md).
- Live Shopify Gate D/CV-013 and provisioning issues #185/#186/#200 are deferred until the Wave-5 implementation candidate is complete and frozen. They remain open and unclaimed; no external UAT or release-readiness claim exists.

## 4. Risk-tiered review model

Every gate declares its tier and reason.

- **Tier 1 — full rigor, blocking:** mutation logic, replay safety, concurrency, idempotency, security, credentials, data integrity, runtime production defects and destabilizing performance risks.
- **Tier 2 — normal review, one consolidated correction expected:** architecture/design decisions, new domain contracts, module boundaries, UI information architecture and benchmark design.
- **Tier 3 — light-touch, non-blocking:** wording, cross-references, terminology, stale status and document structure, unless the wording changes a real functional/safety contract.

The first review must report the complete known finding set. One consolidated correction iteration is the normal maximum. A third same-day revision is a synthesis/reset signal, not another incremental patch. Tier 3 issues are fixed in-pass or carried into the next already-authorized batch; they do not independently gate a merge.

The binding detailed checklist is `claude-mvp-wave-review-template.md`.

## 5. Execution model — backend spine plus early UI/performance tracks

The program no longer waits until all backend domains are frozen before validating operator UX and throughput.

### Track A — backend and mutation spine

This remains dependency-controlled:

- Wave 1: read-only foundation — complete.
- Wave 2: order import — complete.
- Wave 3: inventory + Layer 2 — implementation merged; live Shopify validation `CV-013` remains critical and must close before release-candidate/UAT acceptance.
- Wave 4: fulfillment/tracking backend — current implementation wave.
- Wave 5: remaining premium operator experience, product export and SEC-2.
- Wave 6: full integration, UAT and release readiness.

### Track U — UI pulled forward

A read-only/operator-control UI slice may run in parallel with Wave 4 because it consumes already-hardened core/order/inventory surfaces and does not bypass a mutation/security gate.

#### U0 — UI foundation and merchant operations slice

Start during Wave 4 Gate B. Scope:

- connector navigation, actions and menu structure;
- store/readiness summary;
- operational dashboard shell with real read-only metrics;
- job queue, error, retry and manual-review list/form views;
- safe existing actions only;
- responsive layout, accessibility baseline and perceived-performance instrumentation;
- no new backend business logic and no fulfillment-mode controls until the Wave 4 fields/actions exist.

Acceptance purpose: validate merchant task flow, information hierarchy, error recovery and actual Odoo rendering early enough to influence remaining backend seams.

#### U1 — fulfillment operator slice

Begin after the Wave 4 models/actions stabilize on the implementation branch:

- fulfillment mode selector and confirmation;
- review workspace;
- fulfillment/tracking status and lineage views;
- only accepted backend actions; no UI-owned mutation logic.

#### Wave 5 completion UI

Complete setup wizard, mappings/configuration, roles/access, SEC-2, product export UI and remaining U2/U3 screens after their backend actions are available.

### Track P — performance pulled forward

#### PERF-0 baseline during Wave 4

Create and run a repeatable benchmark against the current integration baseline and again against the Wave 4 candidate:

- queue admission/drain throughput;
- Layer 2 C1/C2/C3 overhead excluding Shopify network latency;
- order/inventory scan throughput;
- reconciliation pagination and memory behavior;
- lock duration/contention;
- p50/p95/p99 job latency;
- query counts and major hot paths.

Use deterministic datasets and record hardware/build/database identity. The baseline does not replace PERF-1; it makes later regressions visible.

#### PERF-1 acceptance

Wave 5 owns tuning/operator cadence controls and the accepted throughput target. Wave 6 repeats the benchmark as release evidence. A material regression or unsafe lock/network pattern is Tier 1 and blocking; ordinary tuning is Tier 2.

## 6. Wave contracts from calibration onward

### Wave 3 — inventory closure

**Current state:** Task 013 and the Layer 2 inventory foundation are merged. `CV-013` live Shopify inventory mutation validation remains open and critical. Task 013B remains separately gated by its accepted packet and product priority.

**Close when:** required live development-store inventory scenarios execute safely, baseline is restored, evidence is committed, and no P0/P1 remains. Missing store access is an external schedule dependency, not permission to mark the validation complete.

### Wave 4 — fulfillment and tracking backend

**Scope:** Task 014; FulfillmentOrder-only architecture; both Mode 1 and Mode 2 backend; exact 16-condition Mode 2 engine; mode switching; disconnected-period reconciliation; COD interplay; tracking create/update; complete state taxonomy; Layer 2 mutation strategies and shared reconciliation.

**Required:** no post-C2 resend from read absence; cursor-complete reads; accepted source/origin pairs; lifecycle/security/redaction; genuine concurrency; Odoo.sh runtime; safe dev-store campaign. `CV-013` must also close before Wave 4 final acceptance/RC entry.

**Parallel work:** U0 and PERF-0 may proceed within their explicit read-only/benchmark boundaries.

### Wave 5 — premium operator experience, export and hardening

**Scope:** finish U0/U1/U2/U3; guided setup; dashboard; mappings/configuration; job/error/retry/review controls; roles/access; fulfillment Mode UI; SEC-2; controlled product/media export; PERF-1 tuning and cadence controls.

**Boundary:** UI calls accepted server actions; it does not create parallel business logic. Product export remains its own Layer-2-aware module/task packet and dev-store gate.

### Wave 6 — end-to-end integration and UAT

**Scope:** fresh install; upgrade/uninstall/reinstall; continuous full connector suite; security and residue/leak audit; PERF-1 release rerun; Shopify dev-store UAT; configuration/install documentation; release-readiness package.

No feature expansion belongs in Wave 6.

## 7. Realistic forward timeline — calibrated 2026-07-22

These are planning ranges based on observed Wave 1–4 velocity, runtime correction cost and the current scope. They assume Odoo.sh access remains available and a disposable Shopify development store is provisioned no later than the Wave 4 runtime window.

| Deliverable | Working-time estimate | Calendar planning window | Parallelization |
| --- | ---: | --- | --- |
| Wave 3 residual live closure (`CV-013`; Task 013B only if kept on immediate critical path) | 3–6 working days once store fixtures exist | 2026-07-23 to 2026-07-31 | Can overlap Wave 4 implementation |
| Wave 4 Gate B implementation + exhaustive pre-runtime audit | 8–12 working days | 2026-07-23 to 2026-08-07 | U0 + PERF-0 start in parallel |
| Wave 4 Odoo.sh runtime, one consolidated correction, rerun and dev-store validation | 5–8 working days | 2026-08-06 to 2026-08-18 | U0/U1 continue |
| U0 UI foundation + first operator slice | 6–9 working days | 2026-07-24 to 2026-08-06 | Parallel to Wave 4 |
| PERF-0 baseline and Wave 4 candidate comparison | 3–5 working days | 2026-07-27 to 2026-08-10 | Parallel to Wave 4 |
| Wave 5 remaining UI/export/SEC-2/PERF-1 | 15–22 working days | 2026-08-10 to 2026-09-08 | UI and export may use separate branches with one integration gate |
| Wave 6 full UAT/release readiness | 7–12 working days | 2026-09-07 to 2026-09-23 | Starts only when required mutation/dev-store gates are green |

**Realistic release-candidate range:** **2026-09-14 to 2026-09-25**.

**Accelerated but credible range:** **2026-09-04 to 2026-09-11**, only if UI/PERF run in parallel, Shopify fixtures are available on time, Tier 3 ceremony is removed, and product export/UI scope is kept to the accepted MVP without new screens or features.

If dev-store access is not ready by early August, the release date becomes externally blocked even if code is complete.

## 8. Levers if the target slips

Use in this order:

1. remove Tier 3 gate ceremony and consolidate documentation updates;
2. parallelize U0/PERF-0 and later UI/export work where file boundaries permit;
3. freeze new feature ideas and protect the accepted MVP boundary;
4. move non-critical Task 013B or lower-priority UI embellishments behind release only through an explicit product-owner scope decision;
5. never trade away mutation safety, security, runtime proof or dev-store evidence.

## 9. Branch and worker model

- Every implementation/governance branch starts from the exact current `mvp/program-integration` SHA.
- Wave PRs target `mvp/program-integration` and remain draft until control-room acceptance.
- GitHub is the source of truth.
- ChatGPT is the strategic control room and acceptance/merge-authorizing authority under the current program-track clarification; Claude/Codex are execution or independent-review workers only when assigned.
- Workers may not self-accept, mark ready or merge.

## 10. Hard stops — unchanged

Stop and escalate for:

1. a required product/commercial decision;
2. official Shopify/Odoo evidence materially conflicting with an accepted decision;
3. destructive or irreversible migration;
4. a Shopify mutation without accepted ownership/idempotency/reconciliation;
5. critical credentials/security exposure;
6. an uncorrectable data-integrity/runtime failure;
7. protected-reference drift;
8. material MVP scope change;
9. inability to satisfy the active wave definition of done safely.

Missing later dev-store/Odoo.sh evidence does not authorize a false pass; it remains explicitly pending.

## 11. Wave-boundary calibration

At every wave boundary the control room records in `mvp-program-state.md`:

- review tier and why;
- initial review and correction count;
- substantive vs Tier 3 findings;
- elapsed time vs forecast;
- UI/PERF parallel-track status;
- next-wave forecast and dependencies;
- process adjustment or evidence that none is needed.
