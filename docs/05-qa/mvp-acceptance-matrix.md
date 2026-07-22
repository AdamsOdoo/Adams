# MVP Acceptance Matrix

> Maps every MVP completion-program item (`../07-implementation-plan/mvp-completion-program.md` §3) to its owning module, requirement, test type, expected runtime/UAT evidence, current status, blocking issue, and release criterion. Update this file as each wave closes — it is the release-readiness source of truth for Wave 6, not a one-time snapshot.
>
> Wave 0 dispositions are recorded in `../04-decisions/DEC-033-mvp-wave-0-reconciliation.md` (Accepted 2026-07-15). Wave 1's internal packet dependency/sequencing reconciliation is recorded in `../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md` (rows 9, 16, 19, 20 below reflect it).

> Wave 1 MERGED (2026-07-16): build `34995642` (runtime-tested SHA `95db3db`)
> ran the complete corrected-head matrix green — full standard suite
> `0 failed / 0 errors / 644` — see `task-sec1-validation-results.md`. The
> final Claude control-room review (20-point independent verification with
> adversarial adjudication; two documentation-only claim-accuracy defects
> found and fixed in the reviewed head's final commit, no code/test/security
> defect) accepted PR #172 and merged it into `mvp/program-integration` via
> merge commit `d18f9a9997d7da574f629f834e2adb83b492cfc6`. SRR-03 remains
> CLOSED.
>
> Fable gap-closure MERGED (2026-07-17): PR #173 merged via merge commit
> `0fb8ccbe8ce54404a57260f82e8226ffa7e6bf73` — every Class B/C decision
> relevant to order import (PD-A/B/C/D/E, PD-COD, PD-RB) is now binding.
>
> Wave 2 gate ACCEPTED (2026-07-17): the Wave 2 Definition of Ready, the
> Task 012 packet (with its 2026-07-16 addendum), and the Area-6 order-scan
> slice are all Accepted (see `DEC-035-wave-2-open-question-dispositions.md`
> for every open question's disposition). **Wave 2 implementation and the
> runtime-correction batch are complete on draft PR #176.** The first
> exact-head runtime campaign (SHA `2e1b1eb62c1fd267bc8ac737e945bc962624e3a8`,
> Odoo.sh build `35080469`) failed and remains preserved as historical
> evidence; all eleven findings now have committed dispositions.
>
> **Corrected-head runtime campaign 3 EXECUTED — CORRECTION REQUIRED
> (2026-07-18, build `35095228`, revised control-room ruling `5010851668`):**
> the sole authorized candidate `2525447cee2d8a3371b1f4e669f61bcd50b20162`
> was runtime-validated on authenticated Odoo.sh build `35095228`
> (DB `adamsmen-sol-wave-2-order-import-35095228`, Odoo 19.0, PostgreSQL 16.14).
> The clean/full fresh install with tests enabled is **NOT green**:
> `0 failed, 3 error(s) of 728 tests`, all three in `TestOrderTotalsGuard`
> (`account_tax.tax_group_id`/`country_id` NOT-NULL). Fixture correction
> `6f32e4c` closed finding #5 in `test_order_tax_resolution.py` only and left
> the identical country-consistent-tax-fixture defect unpatched in the sibling
> `test_order_totals_guard.py` — so **finding #5 is not fully closed**.
> Genuine concurrency 3/3; residue/security/redaction clean; warm-`-u`
> `res_partner.autopost_bills` errors are base-`account` artifacts absent from
> the authoritative fresh install. Under revised ruling `5010851668`, the
> isolated baseline-upgrade (B) and uninstall/reinstall lifecycle (C)
> databases are **deferred release-readiness evidence, not Wave 2 blockers and
> not ENVIRONMENT BLOCKED**; the Wave 2 acceptance gate is the complete
> authenticated Odoo.sh clean/full matrix, which is not green. See
> `task-012-order-import-validation-results.md` → "Corrected-head runtime
> validation campaign 3 — 2026-07-18 (build `35095228`)".
> PR #176 remains draft and unmerged; Wave 2 is **not** runtime-green,
> accepted for merge, or release-ready — rows 9/13/14 reflect this current
> state.
>
> **Wave 3 Gate A ACCEPTED and MERGED (2026-07-19):** PR #177 merged into
> `mvp/program-integration` (merge commit
> `3a2043cb8d45a4b9bc7bdb3ea39b58515e706da9`). DEC-036 (the complete Layer
> 2 D1–D38 decision set) is **ACCEPTED — CONTROL-ROOM GATE A**. **Wave 3
> Gate B, draft PR [#179](https://github.com/AdamsOdoo/Adams/pull/179),
> is now ACCEPTED (2026-07-19):** Revision 1 was returned REVISE, NOT
> REJECTED (comment `5015619162`) — the same-job, two-sequential-mutation-
> attempt design was rejected in favor of three standalone job types.
> Revision 2 applied every binding correction from that comment and was
> itself returned REVISE a second time (comment `5015830229`) — Revision
> 2's same-job CAS-redispatch design still let one mutation job accumulate
> more than one attempt. Revision 3 corrected the job model so every
> mutation job makes at most one attempt for its entire lifetime, froze
> the atomic handoff contract and the `blocked_manual_review`
> review-release path, fixed the error-class vocabulary, corrected the
> `applied` reconciliation verdict, and corrected the locked prompts' role
> model. Revision 3 was **ACCEPTED IN SUBSTANCE** by comment `5016117207`,
> conditioned on one further docs-only merge-closure normalization commit
> (applied, DEC-037 §1C) and merge into `mvp/program-integration`:
> [`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) closes
> every remaining Task 013/013B contradiction and completes the corrected
> `inventorySetQuantities`/`inventoryActivate` Layer 2 mutation-domain
> matrix and job/mutation-consequence contract. **Claude did not accept
> its own package, in any revision, and did not self-accept the
> merge-closure normalization** — acceptance authority is comment
> `5016117207`, product owner + ChatGPT control room. Stage 0 (Layer 2
> core substrate) has a Sol implementation branch
> (`sol/wave-3-stage-0-layer2`) with an open draft **PR #178** (head
> `644853a68b3497c134ee648ce7399e50d30ff397`) — **not merged, not
> runtime-proven**, and remains **held** pending the post-Gate-B-merge
> integration SHA and a consolidated synchronization/correction prompt —
> rows 10/11 below reflect this factual state, not an inference of
> progress. Task 013/013B implementation remains **not authorized** until
> Stage 0 is separately merged and runtime-proven.
>

| # | MVP item | Module(s) | Requirement (accepted source) | Test type | Expected runtime/UAT evidence | Current status | Blocking issue | Release criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Store connection and lifecycle | `shopify_connector_core` | DEC-022/024 (Task 005) | Unit (`test_connection_lifecycle.py`, `test_disconnect_quiescence.py`) | Odoo.sh fresh-install + focused-class green; a store reaching `connected` end-to-end | Partially complete | CORE-R1/lifecycle backend is runtime-green on build `34986844`; Wave 5 UI remains | A store reaches `connected` via UI or documented API call, Odoo.sh-green, zero residue |
| 2 | Secure credentials | `shopify_connector_core` | Task 002 (merged); DEC-028 (Accepted) | Unit (`test_credential_access.py`, `test_credential_service.py`, `test_redaction.py`) | Redaction/leak-scan clean; DEC-028 deployment evidence before real PII | Partially complete | DEC-028 accepted and build `34986844` leak/security scan clean; deployment posture before real-customer PII remains | DEC-028 accepted; deployment posture proven before real-customer PII UAT/production; redaction evidence carried into Wave 6 |
| 3 | Test connection | `shopify_connector_core` | Task 003 | Unit (`test_test_connection.py`, `test_readiness_check.py`) | VAL-B2 live Shopify connection test | Partially complete | CORE-R1 runtime-green on build `34986844`; VAL-B2 live dev-store evidence remains Wave 6 | VAL-B2 passes against a real/dev Shopify store |
| 4 | Guided setup wizard | New UI wave (U2) | DEC-016; `docs/09-ui-prototype/setup-readiness/` | Manual UAT + wizard step tests | Odoo.sh UI walkthrough, screenshot evidence | Remaining implementation | U1 not merged; zero code | Operator completes all 11 accepted steps end-to-end in a dev-store UAT session |
| 5 | Operational dashboard | New UI wave (U1) | DEC-016; `docs/09-ui-prototype/dashboard/` | Manual UAT | Odoo.sh UI walkthrough, screenshot evidence | Remaining implementation | Area 6 not merged (Wave 2+ scope); SEC-1 merged (Wave 1, PR #172) | Dashboard reflects live store/job state in a dev-store UAT session |
| 6 | Product and variant import/export | `shopify_connector_product`; Task 015/015B export module | Task 010/010B; DEC-003; Task 015/015B | Existing import unit suite; new export/media unit + Layer 2 suite | Import Odoo.sh evidence retained; export Odoo.sh + dev-store mutation evidence required | Import complete; export remaining | DEC-033 acceptance, Layer 2, Task 015/015B implementation | Import reconfirmed in Wave 6; controlled export/update and basic media export pass Layer-2-aware runtime and dev-store UAT |
| 7 | First-sync product matching and duplicate prevention | `shopify_connector_product` | AR-045/046-adjacent, Task 010B | Unit (`test_product_duplicate_prevention.py`, `test_product_import_matching.py`) | Odoo.sh green (obtained) | Already complete at checkpoint | None | Carried into Wave 6 dev-store UAT re-confirmation only |
| 8 | Customer import and matching | `shopify_connector_sale` | Task 011/011B; AR-045 | Unit (5 files, incl. `test_customer_matching_scalability.py`) | Odoo.sh green + 100k-partner benchmark (obtained: build `34863138`) | Already complete at checkpoint | None | Carried into Wave 6 dev-store UAT re-confirmation only |
| 9 | Shopify order import into Odoo sales orders | `shopify_connector_sale` order capability | Task 012 packet (RE-ACCEPTED 2026-07-17); DEC-033 reconciliation (accepted); DEC-034 binding-extension contract (accepted); DEC-035 open-question dispositions (accepted); Area-6 order-scan slice (accepted) | 86 authored order tests across the locked 11 files, including two genuine independent-connection concurrency tests; static/source guards green | Odoo.sh clean/full install, isolated baseline-upgrade, isolated uninstall/reinstall lifecycle, focused, full-suite, concurrency, residue and security evidence **not yet obtained at the corrected head** | Corrected-head runtime campaign 3 (SHA `2525447`, build `35095228`) EXECUTED — **CORRECTION REQUIRED**: clean/full fresh install is not green (`0 failed, 3 errors of 728`, all `TestOrderTotalsGuard` `account_tax.tax_group_id`/`country_id` NOT-NULL); fixture correction `6f32e4c` closed finding #5 in `test_order_tax_resolution.py` only, leaving the same defect unpatched in `test_order_totals_guard.py`; concurrency 3/3, residue/security clean; two earlier failed campaigns (`2e1b1eb`/`35080469`, `d1af6d0`/`35088811`) preserved | PR #176 remains draft/unmerged and is not release-ready; the clean/full matrix is not green (finding #5 open in `test_order_totals_guard.py`); under revised ruling `5010851668` the isolated-upgrade (B) and isolated-lifecycle (C) databases are deferred release-readiness evidence (not Wave 2 blockers, not ENVIRONMENT BLOCKED); read-only dev-store proof honestly deferred to Wave 6 | Packet re-accepted; `remote_read_replay_safe` registered; SRR-03 closed; order binding declares and tests complete stored-field classification/protection per DEC-034/SEC-1; corrected-head Odoo.sh matrix green; dev-store UAT obtained or honestly deferred to Wave 6 |
| 10 | Basic inventory synchronization | New `shopify_connector_inventory` | Task 013/013B packet (Gate B ACCEPTED, PR #179, DEC-037); DEC-010 (accepted architecture); DEC-036 (Layer 2, ACCEPTED — CONTROL-ROOM GATE A, merged) | New unit + concurrency suite | Odoo.sh green; genuine multi-worker concurrency proof; dev-store mutation-validation plan (21 scenarios, `wave-3-dev-store-mutation-validation-plan.md`) executed | Remaining implementation | Gate B ACCEPTED (comment `5016117207`) and merged; Stage 0 (Layer 2 core substrate) not yet merged/runtime-proven — Task 013 implementation additionally requires Stage 0 | Layer 2 (Stage 0) merged and runtime-proven, providing DEC-037 §13A's correction prerequisites; packet implemented, Odoo.sh-green, dev-store UAT evidence obtained per the validation plan |
| 11 | Required bidirectional inventory behavior per accepted product rules | New `shopify_connector_inventory` | DEC-010, DEC-015 (MBQ-32/33/34 partial); DEC-037 (Gate B — one-pair-per-request binding, review-case-first drift, reconnect store-identity check) | New unit suite | Same as #10 | Remaining implementation | Gate B ACCEPTED (closes the ongoing apply-mode MBQs' remaining ambiguity — batching explicitly excluded, drift handling explicitly review-case-first); Stage 0 still required before implementation | Bidirectional behavior matches the accepted rule set (as corrected by DEC-037) with regression tests |
| 12 | Fulfillment and tracking updates from Odoo to Shopify | New `shopify_connector_fulfillment` | Task 014 (+ §9/§10 addenda); DEC-011; D-014-2; **DEC-038 (Gate A reconciliation, Proposed)**; DEC-036/DEC-031 Layer 2 (accepted) | New unit + **genuine independent-PG-transaction concurrency** suite; static source-guards (no V2/RA-022, RA-023 line-identity, no-`@idempotent`, no-`qty_done`) | Odoo.sh green; **both Mode 1 and Mode 2** dev-store FulfillmentOrder UAT; **CV-013 (#185) green** required | **Gate A CANDIDATE produced 2026-07-21; bounded correction 2026-07-22 (P0 reconcile-only; Q1–Q8 ruled; taxonomy/allowlist/pagination/vocabulary/lifecycle/staff-perm/API-version frozen); final micro-correction 2026-07-22 (post-C2 `NOT_APPLIED` never resends — APPLIED/INCONCLUSIVE only; **ten**-job taxonomy + one shared `fulfillment_mutation_reconcile` with no remote-effect-scope inheritance; no review-release job type; no Wave 4 webhook source; dedicated trigger-origin uninstall callable; DEC-038 matrix reconciled) → Gate A **ACCEPTED & MERGED** (PR #188 → `01f072dd`; issue #186 comment `5042982528`). **Gate B ISSUED** (issue #186 comment `5043052341` + PR #188 comment `5042975042` source/origin amendment) and **IMPLEMENTED 2026-07-22** by Claude Code (draft PR #189, branch `claude/wave-4-fulfillment-gate-b`, unmerged/not-ready/not-self-accepted; no live Shopify mutation): new `shopify_connector_fulfillment` addon + the one named core edit; ten frozen job types + shared reconcile; both 7-callback Layer 2 strategies (reconcile-only post-C2, APPLIED/INCONCLUSIVE only, no `@idempotent`); both Mode 1 and Mode 2 (16-condition engine + Q6); readiness/lifecycle/scans. Source guards executed → **0 violations**; the `TransactionCase` suite is `IMPLEMENTED—RUNTIME PENDING` (no Odoo runtime in Gate B → Gate C Odoo.sh); Gate D dev-store + CV-013 `NOT PROVEN`/pending. **READY FOR ONE EXHAUSTIVE CONTROL-ROOM REVIEW** (AR-073; `../05-qa/task-014-fulfillment-tracking-validation-results.md`).** | Layer 2 accepted (DEC-036, 2026-07-19) → G4-1 satisfiable; fulfillment mutations have **no native `@idempotent`** (verified 2026-07-21) → **reconcile-only** after `transport_attempted=true` (read absence = INCONCLUSIVE, no resend) + operation-scope serialization is primary dedup; the one named core edit = `shopify_connector_readiness_check.py` `REQUIRED_MVP_SCOPES` swap; **Q1–Q8 ruled/applied (DEC-038 §4)**; risk SRR-10 | FulfillmentOrder-only packet implemented (both modes; 16-condition Mode 2 engine reconciled); scope uses `read_merchant_managed_fulfillment_orders` + conditional `write_merchant_managed_fulfillment_orders` + the `fulfill_and_ship_orders` staff permission; runtime + dev-store UAT + CV-013 green |
| 13 | Scheduled synchronization | `shopify_connector_core` base crons (merged); `shopify_connector_sale` Area-6 order-scan slice (draft PR #176) | DEC-005, DEC-025; accepted Area-6 order-scan packet | Existing core dispatch tests plus authored order scan/watermark/duplicate/concurrency suites | Base cron evidence inherited; new order-scan cron and gates are static-green; first exact-head Odoo.sh campaign (build `35080469`) executed and failed on the documented eleven findings (preserved); corrected-head rerun not yet obtained | Order backend and runtime-correction batch implemented and complete; first runtime campaign failed and is preserved; corrected-head runtime pending; later domains not started | `sale_domain_enabled` and per-store `order_scheduled_sync_enabled` gate a 15-minute enqueue-only cron; no inline import and no Wave 3+ scan; not complete or release-ready until the corrected-head rerun passes | All domains scan/enqueue on schedule with operator-visible cadence |
| 14 | Manual synchronization | `shopify_connector_sale` Area-6 order backend actions (draft PR #176); Wave 5 UI remains future scope | DEC-005, DEC-025; accepted Area-6 order-scan packet | Authored store/binding role-gate, collision, preview/confirm and concurrency tests; Administrator backfill preview/confirmation tests corrected under ruling `5006941549`; non-admin denial tests preserved | Static/source guards green; first exact-head Odoo.sh campaign failed on the documented eleven findings (preserved); corrected-head runtime and later operator UI UAT pending | Backend actions implemented and corrected; corrected-head runtime pending; not complete or release-ready | Operator/Admin backend enqueue paths exist for whole-store and selected-order refresh; backfill requires Administrator preview plus exact confirmation token; no UI implemented in Wave 2; Wave 5 UI remains future work | Operator triggers a sync from the UI and observes the result |
| 15 | User-friendly job and sync logs | `shopify_connector_core` (model, merged); UI (unassigned) | DEC-009; DEC-012/016 | Unit (`test_job_log_system_append.py`); new UI test | Odoo.sh green (model, obtained); UI evidence pending | Partially complete (backend only) | No UI wave started | Operator reads logs from a screen, not just via technical developer-mode access |
| 16 | Retry and recovery controls | `shopify_connector_core` (merged); Task JOB-ACTIONS (merged, Wave 1); UI (unassigned) | DEC-009; DEC-034 (JOB-ACTIONS extraction) | Unit (`test_job_retry_scheduling.py`, `test_job_dispatch.py`, new `test_job_actions.py`); new UI test | Odoo.sh green (dispatcher/retry-scheduling backend, obtained); corrected-head Wave 1 repeat (obtained, build `34995642`); UI evidence pending | Partially complete (backend only) | JOB-ACTIONS/SEC-1 backend is runtime-green at the corrected head (build `34995642`) and merged into `mvp/program-integration` (PR #172, `d18f9a9`); no operator UI yet | Operator can retry/cancel/resolve manual-review jobs from a screen |
| 17 | Duplicate prevention and idempotency controls | All connector modules | DEC-006, DEC-009, DEC-031; Task 012 replay policy | Existing binding/replay tests; Layer 2 tests for mutation domains | Existing-domain evidence retained; mutation ownership/reconciliation evidence pending | Partially complete | SRR-03 CLOSED for read/call safety; DEC-031 Layer 2 remains undesigned for inventory/fulfillment/product export | Every domain has an explicit replay policy; every Shopify mutation domain has proven Layer 2 idempotency/reconciliation behavior |
| 18 | Mapping/configuration screens | New UI wave (U3); backend models merged | DEC-016; `screen-inventory-and-navigation-map.md` | Manual UAT | Odoo.sh UI walkthrough | Remaining implementation | No UI wave started | Operator configures location mapping / store settings from a screen |
| 19 | Basic roles and permissions | `shopify_connector_core`/`product`/`sale` | DEC-012/013; Wave 0 official-source refresh; DEC-034; ruling `4988842625` | Dedicated SEC-1 effective-permission/negative tests + UI UAT | Corrected-head Odoo.sh focused security/binding/PII classes; Roles & Access walkthrough | Partially complete | Complete 16/17/14-field four-role create/alter/clear guards and sanctioned-writer regressions are implemented and corrected-head runtime-green (build `34995642`) in `36974edc68c1985e6ccfae8f6bb5c7386f820156`, merged via PR #172 (`d18f9a9`); Wave 5 roles UI remains | Shared role hierarchy verified by tests; every connector-owned binding field explicitly classified; prohibited RPC/PII paths fail; operator can inspect/assign roles through the accepted Odoo-based UI |
| 20 | Installation, upgrade and configuration documentation | `shopify_connector_core`; `docs/**` | DEC-030 (accepted); Task LC-1; DEC-034 (confirms LC-1 lands before SEC-1) | Lifecycle tests + documentation review | Odoo.sh fresh-install/upgrade/uninstall proof | Remaining implementation | LC-1 install/uninstall/reinstall is runtime-green; final install/upgrade/configuration guide remains Wave 6 work | DEC-030 accepted; LC-1 runtime-green; install/upgrade/configuration guide validated against Wave 6 runs |
| 21 | End-to-end tests | All modules | `domain-e2e-test-matrix.md` (planning only) | Full-suite execution | First continuous (non-one-off) execution of the full suite | Partially complete (existing domains); remaining (rest) | Corrected-head exact-head repeat obtained (build `34995642`, `0/0/644`, merged via PR #172); no CI and Waves 2–5 domains remain | Full suite runs green in a single, reproducible Wave 6 session covering every implemented domain |
| 22 | Dev-store UAT evidence | All modules | VAL-B2; DEC-028 deployment gate | Live Shopify UAT | First live Shopify API call and per-domain scenarios | Remaining runtime/UAT proof | Credentials/access not provisioned; DEC-028 acceptance/deployment posture required before real PII | VAL-B2 and each domain UAT scenario executed; DEC-028 posture evidenced; no token/PII leakage |
| 23 | Release-readiness package | `docs/08-release-readiness/**` | Existing scaffolding (checklist, UAT plan, gap analysis) | Documentation review + sign-off | N/A (release artifact) | Partially complete (scaffolding only) | MVP incomplete; last addendum predates checkpoint | Every row in this matrix reaches "done"; product owner signs off using the existing checklist |

## Notes

- "Current status" values mirror `mvp-completion-program.md` §3 exactly — update both files together, never one without the other.
- Rows 6–8 and 10–12's inventory/fulfillment/order test types are "new" because no code exists yet; the exact test file names will be assigned when each wave's packet is implemented (see each packet's own §"Tests" section for the planned names). Row 9's exact test file names are now fixed (see row 9) as of the Wave 2 gate acceptance (2026-07-17) — they were the one prior omission from this note, now closed.
- This matrix is the authoritative release checklist for Wave 6 — a release is not proposed until every row reaches its stated release criterion or is explicitly, recorded-ly waived by the product owner.
