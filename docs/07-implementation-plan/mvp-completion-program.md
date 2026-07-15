# MVP Completion Program — Odoo 19 ↔ Shopify Connector

> Governance: `DEC-032-mvp-autonomous-execution-model.md` (Accepted, 2026-07-15) establishes the roles and process this file operates under. `CLAUDE.md`'s "MVP Program Control-Room" addendum records the same for future sessions. Live status lives in `mvp-program-state.md`, not here — this file is the relatively stable contract; the state file is the frequently-updated tracker. Feature-by-feature test/evidence mapping lives in `../05-qa/mvp-acceptance-matrix.md`.

## 1. Checkpoint baseline

| Field | Value |
| --- | --- |
| Checkpoint issue | [#165](https://github.com/AdamsOdoo/Adams/issues/165) — CHECKPOINT — CORE-R2 Read-Only UAT Foundation — 2026-07-15 |
| Checkpoint branch (protected, immutable) | `checkpoint/core-r2-readonly-uat-2026-07-15` |
| Integration merge SHA | `acd8c4691e72cf5590f2a56228b08f183b76cd9a` |
| Validated code SHA | `757a9680182f65c627a3880b9c7989d6c5d56035` |
| Evidence commit | `3a2e95b9f4d8ddda512f5ab6f788b37f4dfaf49c` |
| Odoo.sh build | `34935129` |
| Odoo version | 19.0 |
| Annotated tag | Not published (tool limitation recorded in issue #165 §F); the checkpoint branch is the sole published immutable restore reference until someone with tag-push permission runs the command recorded there. |
| Program integration branch | `mvp/program-integration` — created from the checkpoint branch (verified to resolve to `acd8c4691e72cf5590f2a56228b08f183b76cd9a` at creation, 2026-07-15). |
| Bootstrap branch | `claude/mvp-control-room-bootstrap-39nip0` (harness-assigned working-branch name for this bootstrap session; created from `mvp/program-integration`). |

**Protected references — never modify, delete, reset, advance, or force-push, by anyone, in this program:**
`checkpoint/core-r2-readonly-uat-2026-07-15` · `Shopify-connector` (`dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b` as of 2026-07-15) · `main` · issue #165 · PR #150 · PR #151 · any future published checkpoint tag.

**Known hazard:** `claude/task-012-decision-closure-mb88sn` is a stray, unmerged branch with a ~22,000-line deletion diff against the checkpoint (removed tests, QA evidence, decision docs). It matches issue #165 §D's "abandon the unsuccessful experimental branch" language. **Do not branch from it, merge it, or treat its content as authoritative.** It does not touch any protected ref and requires no action other than avoidance; deleting it is optional cleanup requiring explicit product-owner sign-off (not decided in this bootstrap).

## 2. Repository-wide audit — method and headline findings

A 10-workstream, evidence-cited audit (addon inventory/manifests, architecture/decisions, research outputs, QA/runtime evidence, PR #150, PR #151, issue/risk register, operator UX inventory, test/CI coverage, implementation-plan/prompt history) was run against the checkpoint working tree plus live GitHub state on 2026-07-15. Every classification below traces to a specific file path, commit SHA, or GitHub API result found during that audit. Headline findings that shape the wave plan:

1. **Only three connector addons exist in code**: `shopify_connector_core` (v19.0.1.7.2), `shopify_connector_product` (v19.0.2.0.0, import-only), `shopify_connector_sale` (v19.0.1.0.0, customer-import-only despite the module name — it contains no `sale.order` logic). No `shopify_connector_inventory`, `shopify_connector_fulfillment`, `shopify_connector_order`, or dashboard/UI module exists anywhere. `addons/adams_base` is confirmed an untouched, isolated empty placeholder (good — confirms the required isolation from existing customer/base code).
2. **Zero operator-facing UI code exists anywhere** in `addons/` — no views, actions, menus, wizards, or controllers (independently grep-verified twice). `docs/09-ui-prototype/` is a self-contained static HTML/CSS visual prototype that explicitly "authorizes no production code" (its own README). Its own traceability matrix records stage U0 (visual prototype) as accepted, and U1/U2/U3 (actual implementation stages) as **CLOSED**.
3. **Product import (Task 010/010B) and customer import/matching (Task 011/011B) are functionally in the checkpoint and Odoo.sh-runtime-green**, even though GitHub PR #151 and PR #150 (their formal review PRs) remain open/draft/unmerged by deliberate stated policy. Their exact head commits are proven git ancestors of the checkpoint via a documented "Slice 2B integration-staging" merge path (`git merge-base --is-ancestor` confirmed for both). **Do not treat PR #150/#151 as "not yet available" — their code is live in the checkpoint.** Whether the GitHub PR entities themselves should be formally closed/merged is an open governance question for Wave 0 (see §5).
4. **A real, functional gap in "already accepted" scope**: `docs/07-implementation-plan/task-core-r1-readiness-correction-packet.md` documents that on the current merged code, **no store can ever reach `connected` status**, because three readiness sub-checks (`webhook_hmac`, `mapped_location`, `cron_queue_health`) are permanently `not_proven` placeholders and the aggregate readiness check is fail-closed. Task CORE-R1 (proposed, not merged) is the fix. This blocks MVP items 1 and 3 from being fully "done" even though their backend code and tests exist.
5. **A real, current security gap**: `docs/07-implementation-plan/task-sec1-security-hardening-packet.md` documents verified-fact exposures in the *already-merged* code — any operator-group user can RPC/ORM-write `shopify.connector.job.state`/`error_class` outside any sanctioned action; binding identity fields (`shopify_gid`, `store_id`, `partner_id`) are RPC-mutable with no server-side guard; PII snapshots are readable by all four connector groups including Auditor. Task SEC-1 (proposed, not merged) is the fix, and is a hard prerequisite before any operator-facing UI (Wave 5) can safely expose buttons to these models.
6. **DEC-031 Layer 1 (accepted 2026-07-15) is narrow by design**: a fail-closed replay-policy registry covering only today's read-only handlers (`product_import_sync`, `customer_import_sync` → `remote_read_replay_safe`). **Layer 2 (durable job-execution ownership) is explicitly deferred until the first Shopify-mutation domain is proposed** — this is the gate the task instruction's Phase 4 already names for Wave 3 (inventory).
7. **An unreconciled internal contradiction exists on SRR-03's status**: `docs/03-architecture/task-012-order-import-decision-closure.md` states "SRR-03 CLOSED," while `docs/05-qa/sync-engine-risk-register.md`, the product-domain validation docs, and issue #165 §C all state "SRR-03 remains OPEN" as of the same checkpoint. **This must be reconciled by the control room before Wave 2 (order import) starts** — see §5 Wave 0 and §9. Until reconciled, treat SRR-03 as OPEN (the stricter, safety-conservative reading) for gating purposes.
8. **A real scope question DEC-003 (accepted) already answers but the given wave plan does not cover**: DEC-003 defines MVP product scope as "controlled bidirectional product onboarding (import **and** export/update)." The current codebase and this program's Wave 1–6 plan (per the original task instruction) only cover product **import**. Product export (Task 015/015B) has mature-but-unaccepted design docs and zero code, and is not assigned to any wave below. **This is flagged, not silently resolved — see §3 item 6 and §9.**
9. **No live Odoo runtime and no live Shopify call have ever occurred in this repository's history.** Every "tests pass" claim traces to a manually-invoked Odoo.sh dev-build session (no CI/CD exists, consistent with the research-phase guardrail). VAL-B2 (a live Shopify Admin API connection test) has never been executed. This is the single largest gap for release readiness (MVP items 21–23) and means Sol will need Odoo.sh + eventually dev-store Shopify access provisioned for every wave's runtime evidence.
10. **Rejected-approaches log (`../05-qa/rejected-approaches-log.md`) has 24 binding rows (RA-001..RA-024)**, none re-proposable without their logged revisit condition being met. Sol must check this log before proposing any design (CLAUDE.md §10) — most relevant to the remaining waves: RA-018/019/020/021 (inventory-writing constraints), RA-022/023 (fulfillment must use FulfillmentOrder, never legacy Order/Fulfillment API), RA-014/015/016/017 (retry/error/idempotency defaults).
11. **Four `res.groups` (Auditor/Operator/Reviewer/Admin) are correctly defined once in `shopify_connector_core` and correctly referenced** across all three modules' ACLs — the roles/permissions *backend* is essentially done; what's missing is UI and a dedicated roles-specific research pass (current research on this topic is generic Odoo ACL mechanics plus one competitor-matrix row).
12. **Documentation staleness (housekeeping, non-blocking)**: `docs/05-qa/sync-engine-risk-register.md`'s SRR-03 row narrative stops at the 2026-07-13 Foundation-Slice-1 update and doesn't mention the later, merged Slice 2A/2B/DEC-031 work; `docs/03-architecture/sync-engine-architecture-gate.md`'s header still says "Proposed... not Accepted" despite the companion DEC-025 being Accepted. Recommended Wave 0 cleanup, not a functional blocker.

Full per-file evidence for every finding above lives in this bootstrap session's audit trail; the classifications in §3 and the acceptance matrix (`../05-qa/mvp-acceptance-matrix.md`) are the durable, GitHub-committed record of it (per the documentation-maintenance rule, `../05-qa/quality-feedback-loop.md` §11 — current-state summary here, not a re-paste of the full audit transcript).

## 3. Frozen MVP completion contract

Each item is classified as one of: **already complete** · **partially complete** · **implemented elsewhere, not checkpoint-integrated** · **remaining research** · **remaining implementation** · **remaining runtime/UAT proof** · **excluded from MVP**. "Owning task/packet" points to the exact repo doc/module for traceability.

| # | MVP item | Classification | Owning task/packet | Notes |
| --- | --- | --- | --- | --- |
| 1 | Store connection and lifecycle | Partially complete | `shopify_connector_core` (Task 005, DEC-022/024) | Backend (`action_activate`/`action_disconnect`/`action_reconnect`) merged, tested, Odoo.sh-green. Blocked from being fully "done": CORE-R1 defect (no store can ever reach `connected`); zero UI. |
| 2 | Secure credentials | Partially complete | `shopify_connector_core` (Task 002) | Storage/redaction/ACL merged. Production-entry security posture (encryption at rest, backups, retention) is DEC-028 — drafted, **not accepted**. |
| 3 | Test connection | Partially complete | `shopify_connector_core` (Task 003) | Backend + unit tests exist. VAL-B2 (live Shopify test) never executed. Blocked by the same CORE-R1 readiness defect as item 1. No UI. |
| 4 | Guided setup wizard | Remaining implementation | UI wave U2 (`ui-implementation-phases-packet.md`) | Zero code. Screen design accepted (DEC-016) and visually prototyped (`docs/09-ui-prototype/setup-readiness/`) — prototype explicitly authorizes no code. Gated behind U1. |
| 5 | Operational dashboard | Remaining implementation | UI wave U1 | Zero code (no dashboard model/view/action). Screen design accepted + prototyped (`docs/09-ui-prototype/dashboard/`); gated behind Area 6 + SEC-1 merge. |
| 6 | Product and variant import | Partially complete — **scope flag** | Task 010/010B (import); Task 015/015B (export, unassigned) | Import half already complete at checkpoint, runtime-green. **DEC-003 (accepted) defines product MVP scope as bidirectional import+export/update; export (Task 015/015B) has 0% code and is not assigned to any wave below.** Needs explicit product-owner/control-room decision — see §9. |
| 7 | First-sync product matching and duplicate prevention | Already complete at checkpoint | Task 010B (`shopify_connector_attribute_lock`, template/variant binding) | Runtime-green; AR-045/AR-046-adjacent. |
| 8 | Customer import and matching | Already complete at checkpoint | Task 011/011B | Indexed matching, 100k-partner benchmark, concurrency-proven, runtime-green. |
| 9 | Shopify order import into Odoo sales orders | Remaining implementation (plus a hard-stop-worthy decision-closure step) | Task 012 (`task-012-order-import-implementation-packet.md`) | Extremely mature design (10 rounds of adversarial decision closure: tax representation, total-check tolerance, 6 fail-closed pre-creation gates, DEC-020 currency routing) but **Proposed, not accepted**; zero code. Gated on the SRR-03 contradiction (finding 7, §2) being reconciled first. |
| 10 | Basic inventory synchronization | Remaining implementation | Task 013/013B | Mature proposed packets (D-013-1..8), zero code. DEC-010 architecture direction already accepted (Odoo authoritative; Shopify `available` is the Phase-1 write target; keyed on store+`inventory_item_id`+`location_id`, never SKU-only). This is the domain that triggers DEC-031 Layer 2. |
| 11 | Required bidirectional inventory behavior per accepted product rules | Remaining implementation/research | DEC-010, DEC-015 (partial: MBQ-32/33/34) | Quantity-source and first-push granularity partially resolved; ongoing bidirectional apply-mode has open MBQs. Zero code. |
| 12 | Fulfillment and tracking updates from Odoo to Shopify | Remaining implementation | Task 014 | Mature proposed packet; DEC-011 architecture accepted (FulfillmentOrder-based, validated `stock.picking` as sole trigger, RA-022/023 forbid the legacy API). Zero code. Open research item: shipped `REQUIRED_MVP_SCOPES` includes `read_fulfillments`, which per Shopify's own access-scopes docs does not gate Fulfillment/FulfillmentOrder read access — needs correction in or before this wave. |
| 13 | Scheduled synchronization | Partially complete | `shopify_connector_core` crons (merged); Area 6 (proposed, unmerged) | Two live `ir.cron` jobs run today (5-min drain, 5-min disconnect-quiesce) but only drain the existing product/customer queue — no order/inventory/fulfillment scan exists yet, and cadence is hardcoded with no operator UI. |
| 14 | Manual synchronization | Remaining implementation | Area 6 | No manual-trigger action anywhere in code; Area 6 is gated on Task 012 merging (order-scan needs the order importer) plus CORE-R1. |
| 15 | User-friendly job and sync logs | Partially complete (backend only) | `shopify_connector_job_log.py` (merged) | Append-only log model + tests exist; zero UI (no list/form view). |
| 16 | Retry and recovery controls | Partially complete (backend only) | DEC-009 (accepted); `shopify_connector_job_dispatch.py`/`job.py` (merged) | 16-class error taxonomy, job state machine, bounded retry all implemented/tested. No operator-facing retry/cancel action; `action_resolve_manual_review` is named as prospective in `ui-implementation-phases-packet.md` but does not exist yet. |
| 17 | Duplicate prevention and idempotency controls | Partially complete | DEC-031 Layer 1 (accepted, narrow); Layer 2 (deferred) | Strong for the two existing read-only domains. Any future write domain (order/inventory/fulfillment) requires Layer 2, not yet designed in detail. |
| 18 | Mapping/configuration screens | Remaining implementation | UI wave U3; backend models already exist (`shopify_connector_location.py`, `store_settings.py`, `attribute_lock.py`) | Zero config UI/views anywhere. |
| 19 | Basic roles and permissions | Partially complete | `shopify_connector_security.xml` (merged) | Four groups + ACLs correctly defined and wired across all three modules. Gaps: `shopify_connector_sale` has no dedicated groups/data file (reuses core's — a structural inconsistency, not necessarily a defect); no "Roles & Access" UI screen exists or is prototyped; roles-specific research is thin. |
| 20 | Installation, upgrade and configuration documentation | Remaining implementation/research | DEC-030 (module lifecycle/uninstall, proposed, not accepted) | No user-facing install/upgrade guide found in the audit. Needs DEC-030 acceptance plus authored documentation. |
| 21 | End-to-end tests | Partially complete for existing domains; remaining for the rest | ~404 written test methods (core/product/sale) | Historically Odoo.sh-validated in one-off dev-build sessions; never continuously re-run (no CI, no runtime in any Claude session's own sandbox). Zero coverage for order/inventory/fulfillment (no code yet). No true cross-domain E2E suite exists (`domain-e2e-test-matrix.md` is planning-only). |
| 22 | Dev-store UAT evidence | Remaining runtime/UAT proof | VAL-B2 (blocked throughout repo history) | No live Shopify API call has ever been made from any session. This is the largest concrete gap for release readiness. |
| 23 | Release-readiness package | Partially complete (scaffolding only) | `docs/08-release-readiness/**` | Extensive planning (UAT plan, checklist, readiness maps, gap analysis, signoff templates) exists; no final accepted package, because the MVP itself is incomplete. Last addendum (2026-07-11) predates the 2026-07-15 checkpoint. |

### Confirmed excluded from MVP (validated against repo evidence, unchanged from the task's default list)

Payout reconciliation · advanced refunds · advanced accounting automation · Shopify Markets · subscriptions · gift cards · Shopify POS · B2B · metafields · advanced analytics · app-store packaging · complex multi-company behavior · broad multi-store orchestration.

This list is directly supported by DEC-003 (refunds/cancellations/returns deferred; no accounting automation beyond financial-evidence capture; single-store/single-company Phase 1) and DEC-026 (public/many-unrelated-customer distribution and app-store packaging are explicitly Phase 2+, gated behind unmet prerequisites). No repo evidence found requires adding anything to this exclusion list. **Product export (item 6 above) is a partial exception**: DEC-003 already includes it in "MVP" scope in principle, even though no wave below implements it — this is the one place the given exclusion list and the accepted DEC-003 scope are in tension, and it is called out rather than silently resolved (§9).

## 4. Macro-wave execution model

Waves are as given in the program instruction, annotated with the exact repository task/packet each wave must execute, since the audit found no reason to renumber or reorder the six waves — only to make their internal dependencies explicit.

### Wave 0 — Current-state reconciliation and research closure

- **Scope:** Confirm checkpoint capability (done — this bootstrap's audit is the record). Reconcile PR #150/#151's administrative status (recommendation: close/mark superseded on GitHub since their content is already merged into the checkpoint via the Slice-2B integration-staging path — **do not act unilaterally; this needs explicit product-owner/control-room sign-off**, since PR #150/#151 are protected references for this program). Reconcile the SRR-03 "CLOSED" (Task 012 decision-closure doc) vs. "OPEN" (risk register, product-domain docs, issue #165) contradiction (finding 7, §2) — this is a blocking prerequisite for Wave 2. Decide the product-export scope question (finding 8, §2 / item 6, §3). Decide whether DEC-027/028/029/030 (all drafted, evidenced, "Proposed... NOT accepted") need acceptance before or during this program, or are explicitly deferred past it. Refresh only the research that's genuinely stale or thin: the roles/permissions-specific research gap (item 19) and the `read_fulfillments` scope-name correctness question (item 12) are the two concretely open items; the competitor bundle (~2 weeks old) is optional/low-priority. Housekeeping: update `sync-engine-risk-register.md`'s SRR-03 narrative and `sync-engine-architecture-gate.md`'s stale header (finding 12, §2). Produce the final dependency map (this file's §4 wave annotations serve as that map; Sol may refine it if evidence changes).
- **Owned paths:** `docs/**` only. No addon code.
- **Forbidden:** any `addons/**` change; any protected-reference change.
- **Acceptance criteria:** every open question in §9 has either a recorded decision (new/updated DEC or a `mvp-program-state.md` entry) or an explicit "deferred, revisit condition X" note; the dependency map is current; no addon code was touched.
- **Dependencies:** none (first wave).
- **Definition of done:** Claude control-room review confirms all Wave 0 questions are closed or explicitly deferred with a stated revisit condition, and `mvp-program-state.md` reflects "Wave 0 complete."

### Wave 1 — Existing read-only foundation integration

- **Scope:** Task CORE-R1 (readiness correction — fixes the "no store can ever reach `connected`" defect, finding 4, §2). Task SEC-1 (security hardening — closes the RPC-writable job-state/binding-identity/PII exposure, finding 5, §2; must land before Wave 5 wires any UI to these models). Confirm the Task 010B/011B completeness work is fully reflected in `mvp/program-integration` (it already is, per the audit — this wave's job is verification, not re-implementation, unless Wave 0 decides otherwise). Close any remaining setup/core UX backend gaps later waves need.
- **Owned paths:** `addons/shopify_connector_core/**` (CORE-R1, SEC-1 allowed files per their own packets); no new addon directories.
- **Forbidden:** `addons/shopify_connector_product/**`, `addons/shopify_connector_sale/**` except as CORE-R1/SEC-1's own packets explicitly allow; no UI files (UI is Wave 5); no order/inventory/fulfillment code (later waves).
- **Acceptance criteria:** a store can reach `connected` status end-to-end on Odoo.sh; the SEC-1 packet's named exposures are closed with tests; all existing core/product/sale tests remain green.
- **Test matrix / runtime evidence:** Odoo.sh fresh-install + focused-class runs for CORE-R1 and SEC-1, per their own packets' acceptance criteria; zero-residue/leak audit (matching the pattern already established for CORE-R2/010B/011B).
- **Dependencies:** Wave 0 (decisions this wave might need, e.g. any DEC-028 posture acceptance relevant to credential handling).
- **Rollback:** revert the wave PR; checkpoint/`mvp/program-integration` pre-wave state is the restore point.
- **Definition of done:** Claude control-room wave review (per `../06-prompts/claude-mvp-wave-review-template.md`) accepts and merges into `mvp/program-integration`.

### Wave 2 — Order import

- **Scope:** Task 012 exactly as decision-closed in `task-012-order-import-implementation-packet.md` (tax mapping + standard `account.tax` engine + the frozen deterministic whole-order solver K=2/M=2/C_max=25; total-check tolerance formula; six fail-closed pre-creation policy-skip gates; DEC-020 divergent-currency routing to a `skipped` state). Customer/product/binding resolution against the existing import domains. Duplicate prevention; order status handling; logs, retries, tests. Area 6's order-scan trigger (manual + scheduled) belongs here once the importer exists, since Area 6's own gate criterion requires "Task 012 merged runtime-green."
- **Owned paths:** new `addons/shopify_connector_sale/**` order-binding/importer files (per the packet's exact allowed-file list); Area 6's own allowed files once Task 012 lands.
- **Forbidden:** inventory/fulfillment code; any Shopify mutation beyond what the accepted packet specifies; product/customer domain files outside what order-resolution needs.
- **Acceptance criteria:** the packet's own acceptance criteria (§ per `task-012-order-import-implementation-packet.md`), plus: the SRR-03 contradiction (Wave 0) is resolved and this wave's own capability-prerequisite checklist (`task-012-decision-closure-handoff.md` §4) is fully satisfied before implementation starts, not just before merge.
- **Dependencies:** Wave 0 (SRR-03 reconciliation), Wave 1 (CORE-R1, SEC-1).
- **Definition of done:** Claude control-room wave review accepts and merges.

### Wave 3 — Inventory synchronization

- **Scope:** Task 013/013B exactly as decision-closed. Authoritative quantities/locations per DEC-010 (Odoo authoritative; `available` write target; keyed on store+`inventory_item_id`+`location_id`). Loop/stale-update prevention. Batching, throttling, reconciliation. **DEC-031 Layer 2 (durable job-execution ownership) must be designed, accepted, and implemented before this wave's first live Shopify mutation** — this is the domain DEC-031 itself names as the Layer-2 trigger.
- **Owned paths:** new `addons/shopify_connector_inventory/**` (per the packet's allowed-file list); `shopify_connector_core` changes only as Layer 2's own design requires.
- **Forbidden:** fulfillment code; any inventory write that bypasses Layer 2 once Layer 2 exists; writing Shopify's `committed` quantity (RA-018).
- **Acceptance criteria:** the packet's own acceptance criteria; Layer 2 runtime and concurrency proof (genuine, not simulated); reconciliation-before-retry behavior demonstrated.
- **Dependencies:** Wave 2 (order import merged — per the given wave order; also unblocks Area 6's full scan/trigger set), Layer 2 design+acceptance.
- **Definition of done:** Claude control-room wave review accepts and merges.

### Wave 4 — Fulfillment and tracking

- **Scope:** Task 014 exactly as decision-closed. Odoo delivery/fulfillment state → Shopify via FulfillmentOrder mutations only (RA-022/023 forbid the legacy Order/Fulfillment API). Partial fulfillment where included. Tracking updates. Replay/idempotency/reconciliation rules (building on Layer 2 from Wave 3). Mutation safety and operator recovery. Correct the `REQUIRED_MVP_SCOPES` `read_fulfillments` issue (finding, item 12 §3) in or before this wave.
- **Owned paths:** new `addons/shopify_connector_fulfillment/**` (per the packet's allowed-file list); `shopify_connector_core/models/shopify_connector_readiness_check.py` only for the scope-name correction.
- **Forbidden:** inventory code changes beyond what fulfillment-location resolution needs; any fulfillment mutation without a durable idempotency key (Layer 2).
- **Acceptance criteria:** the packet's own acceptance criteria; genuine replay-safety proof for fulfillment mutations.
- **Dependencies:** Wave 3 (Layer 2 must already exist and be proven).
- **Definition of done:** Claude control-room wave review accepts and merges.

### Wave 5 — Premium operator experience

- **Scope:** UI implementation stages U1→U2→U3 (core operator shell/dashboard/sync/error center; setup wizard; domain screens including mapping/config and roles & access) per `docs/09-ui-prototype/` (visual reference) and `ui-ux-implementation-task-map.md` (accepted planning guidance) — U1 itself is gated on Area 6 + SEC-1 being merged (both land earlier: SEC-1 in Wave 1, Area 6 in/after Wave 2) plus a dedicated UI-implementation-gate act. Manual sync UI, scheduled-sync configuration UI, job/sync logs UI, retry/manual-review UI (wires up the still-nonexistent `action_resolve_manual_review`). Mapping/configuration screens. Roles & permissions screen. Task PERF-1 (queue throughput calibration) belongs here too — the current 5-min/batch-20 drain cadence is mathematically under the stated throughput budget and should be recalibrated before the UI creates an expectation of near-real-time sync. Product export (Task 015/015B) lands here **only if** Wave 0 / the product owner decide it is in this program's scope (§9) — otherwise it is explicitly excluded with a recorded decision.
- **Owned paths:** views/actions/menus/wizards/controllers across all connector addons (per each accepted screen's own file list); `shopify_connector_core` job-dispatch cadence tuning for PERF-1.
- **Forbidden:** any UI wiring to a model SEC-1 hasn't hardened; any new backend business logic beyond what a screen needs to call already-accepted actions.
- **Acceptance criteria:** every screen in `screen-inventory-and-navigation-map.md`'s accepted MVP rows is implemented and wired to its already-accepted backend action; `action_resolve_manual_review` exists and is tested; PERF-1's throughput target is met and measured.
- **Dependencies:** Waves 1–4 (the backend actions and domains the UI exposes must exist first, per-screen).
- **Definition of done:** Claude control-room wave review accepts and merges.

### Wave 6 — End-to-end integration and UAT

- **Scope:** Fresh install; upgrade path (needs DEC-030 acceptance, Wave 0); full integration test suite — the first time any test in this repository is executed continuously/end-to-end rather than as a one-off dev-build session; performance checks (validates PERF-1's fix under load); dev-store UAT (VAL-B2 — the first live Shopify API call in this repository's history); security audit; residue/leak audit (continuing the pattern already established at every prior checkpoint); documentation (install/upgrade/config guides, item 20 §3); release-readiness decision using the existing `docs/08-release-readiness/**` scaffolding.
- **Owned paths:** `docs/08-release-readiness/**`, test suites across all addons, documentation.
- **Forbidden:** new feature scope of any kind — this wave proves the MVP, it does not extend it.
- **Acceptance criteria:** every item in `../05-qa/mvp-acceptance-matrix.md` reaches its stated release criterion; dev-store UAT evidence is genuine and recorded; no open hard-stop condition remains.
- **Dependencies:** Waves 1–5 complete.
- **Definition of done:** Claude control-room wave review + explicit product-owner release-readiness sign-off (this wave alone is not self-executing — see §7).

## 5. Branch strategy

- `mvp/program-integration` — the program's integration branch, created from the checkpoint SHA. All wave PRs target this branch.
- Per-wave working branches — created from `mvp/program-integration`, named descriptively (e.g. `sol/wave-1-core-r1-sec1`). Sol may create sub-branches inside a wave for its own iteration; only the wave's final PR into `mvp/program-integration` requires Claude control-room review.
- Never branch from `Shopify-connector`, `main`, PR #150, or PR #151.
- Promotion of `mvp/program-integration` toward `Shopify-connector`/`main` is a separate, later, explicitly product-owner-approved act — out of scope for every wave defined here.

## 6. Sol authority

See `../06-prompts/gpt56-sol-master-mvp-mission.md` for the complete, standalone statement Sol receives. Summary (authoritative version is the mission file, not this summary):

**Authorized:** research official Shopify/Odoo sources; inspect the full repository; create working branches from `mvp/program-integration`; create/update GitHub issues; write code/tests/docs; run Odoo.sh validation; correct defects within the active wave; open focused wave PRs into `mvp/program-integration`; update `mvp-program-state.md` and the acceptance matrix; continue autonomously inside an open wave until a wave gate or hard-stop.

**Not authorized:** modify the checkpoint branch, `Shopify-connector`, or `main`; force-push protected/shared branches; delete history; merge a wave PR (Claude control-room only); silently broaden MVP scope; claim unsupported Shopify/Odoo behavior; introduce a Shopify mutation before DEC-031 Layer 2 is designed, accepted, and implemented for that domain; claim exactly-once remote effects (DEC-031 itself makes no such claim anywhere); hide failed tests or reclassify owned failures as unrelated; absorb unrelated defects without approval; start any excluded-from-MVP domain (§3); publish a release without the Wave 6 + product-owner release gate.

## 7. Claude control-room review gates

Every macro-wave PR is reviewed with `../06-prompts/claude-mvp-wave-review-template.md` before merge into `mvp/program-integration`. Claude does not require per-commit approval inside an open wave. The Wave 6 gate additionally requires explicit product-owner sign-off before any `mvp/program-integration`→`Shopify-connector`/`main` promotion is even proposed — that promotion act is out of scope for this program's own gates.

## 8. Hard-stop conditions (apply to Sol at all times, not waivable by Sol)

1. A requirement needs a commercial/product-owner decision.
2. Official Shopify or Odoo evidence conflicts with an accepted decision.
3. A destructive or irreversible data migration is required.
4. A Shopify mutation lacks accepted replay, idempotency, or reconciliation behavior (i.e. Layer 2 isn't in place yet for that domain).
5. Credentials or human Shopify Partner/dev-store access are required.
6. A critical test or data-integrity failure cannot be corrected inside the wave.
7. The checkpoint or any protected branch has unexpectedly changed.
8. MVP scope would materially change.
9. A security or credential-exposure risk is found.
10. The active wave cannot satisfy its own definition of done.

**Program-specific stop condition (11):** the SRR-03 "CLOSED" vs. "OPEN" contradiction (§2 finding 7) is not resolved before Wave 2 begins implementation. Sol must escalate rather than pick a reading.

## 9. Open decisions requiring product-owner / control-room resolution (Wave 0 agenda)

1. **Product export (Task 015/015B) MVP scope**: DEC-003 (accepted) includes bidirectional product import+export in MVP scope; this program's given wave plan does not implement it. Decide: (a) add it as an explicit wave (recommend: fold into Wave 5 alongside other UI/completeness work, since it's decision-mature-adjacent but unaccepted), or (b) formally amend DEC-003's scope to defer it past this MVP program, with the amendment recorded as a new DEC, not a silent drop.
2. **SRR-03 status reconciliation**: is Task 012 (order import — Odoo-side write, no Shopify mutation) actually gated on SRR-03/Layer 2 closure, or does DEC-031's own trigger condition ("the first Shopify-mutation domain") mean Task 012 does not require Layer 2 and only Wave 3 (inventory, the first true Shopify-write domain) does? The two source documents disagree and neither cross-references the other's reasoning.
3. **PR #150/#151 administrative disposition**: formally close/mark superseded now that their content is proven merged into the checkpoint, or leave them open indefinitely as a deliberate policy record? (Either way, do not delete or alter their code content — they are protected references.)
4. **DEC-027/028/029/030 acceptance**: all four are drafted and evidenced but "Proposed... NOT accepted." Decide whether any is a hard prerequisite for a specific wave (DEC-028's credential/PCD posture ladder is the most plausible candidate — relevant before any wave imports real customer PII in a dev-store UAT) or can be deferred past this program.
5. **`claude/task-012-decision-closure-mb88sn` disposition**: leave untouched (default, safe) or delete as cleanup (requires explicit sign-off since branch deletion is not easily reversible in this session's tooling).
6. **`addons/requirements.txt`**: a pre-existing, empty (1-byte) tracked file. Literally matches CLAUDE.md §11's forbidden-pattern list by name, but is inert (zero pinned dependencies) and already disclosed in the repo's own QA docs. Not created or modified by this bootstrap session. Flagged for product-owner awareness; no action recommended unless the product owner wants it removed.
