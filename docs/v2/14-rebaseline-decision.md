# V2 rebaseline and delivery recommendation

> Historical review snapshot. The user subsequently authorized development on 8 September; current execution authority and sequence are in `16-delivery-blueprint.md` and the handoff. UI design is now parked by the user. Baseline failures below are historical evidence, not post-correction results.

Status: proposed for product-owner approval; no implementation or release acceptance.
Inspection: 7 September 2026 UTC / 8 September UAE. Planning kickoff: 8 September 2026.
Owner: Astra, directly responsible for research, implementation, testing and integration.

## Decision requested

Retain the Odoo modular monolith and existing addon/data identities. Repair the demonstrated integration defects, and replace selected internals only where a bounded change removes a proven failure or redundant responsibility. Deliver the complete supported V2 operational scope in the accompanying journey matrix. Preserve the existing safety, isolation, recovery and release gates.

Use 21 days as the engineering and qualification checkpoint, not a guaranteed release date. With the current sequential canaries, a provisional release-readiness window is **1–5 October 2026 (days 24–28)**, conditional on foundation repair, access, participant availability and actual model allowance. This is an estimate, not an accepted deadline extension. Fourteen days is not a credible complete-release commitment on the inspected evidence. Production promotion and public publication remain separate decisions.

The minimum complete product serves merchants operating Shopify with Odoo 19, initially qualified on Odoo.sh. It imports and matches catalog/customer/order data, controls product export, synchronizes Odoo-authoritative inventory, sends fulfillment/tracking safely, and gives operators coherent setup, progress, exception handling and recovery. Simple independent administration of up to ten stores remains in scope. Odoo Apps module packaging and merchant-managed Shopify credentials remain the distribution model; SaaS billing and a vendor-owned Shopify App Store installation are separate products.

## Verified state and history

| Item | Observed identity and meaning |
|---|---|
| V1 baseline | PR #210, open draft, `codex/public-release-closure`, `f77bfcc25e63615e6226dd9a9329f8f943593cb2`; accepted implementation ancestry, not public-release qualification |
| V2 blueprint | PR #211, open draft, `codex/v2-product-architecture-gate`, `3914004e27630b09b211e3d2ee92a8e6d9a0e55e` |
| V2 implementation | PR #212, open draft, `codex/v2-continuous-implementation`, `1c75c10288477b3a902193797360badc9d2aa06a` |
| Last code repair | `880e70088922eb10dd44426678d578ee4ee7a73a`, tree `8ea4e799ea87953c187dc37f25af584b84e3c977` |
| Relevant delta | Code repair to current head is one documentation/evidence commit affecting nine files. Executable equivalence was checked by the GitHub comparison. |
| Historical P10 | Previously unpublished work was recovered and published. Do not recover or recreate it again. |
| Current workspace | No existing project checkout was supplied. A read-only inspection subset was downloaded; no conclusion is made about dirty worktrees in other sessions. |

The project progressed from research/ADRs and V1 waves through release corrections to a V2 blueprint and substantial implementation. PR #212 contains 390 changed files and approximately 84,135 insertions/1,369 deletions relative to its base: enough accumulated work that wholesale replacement would incur considerable reconstruction and qualification cost. This is a scope measure, not a quality score. [PR #210](https://github.com/AdamsOdoo/Adams/pull/210), [PR #211](https://github.com/AdamsOdoo/Adams/pull/211), [PR #212](https://github.com/AdamsOdoo/Adams/pull/212), [published handoff comment](https://github.com/AdamsOdoo/Adams/pull/212#issuecomment-5480717050).

### CI verdict

The successful policy job actually reports **448 tests passed** and **48 GraphQL documents validated** against 2026-07. Those are historical executed results on the current code, freshly inspected this session; they were not rerun locally. The full connector job provisioned pinned Odoo, PostgreSQL 16, Python 3.12 and Ubuntu 24.04 and then failed. It is not a missing-runner failure. [Policy run](https://github.com/AdamsOdoo/Adams/actions/runs/33449240501), [full run and logs](https://github.com/AdamsOdoo/Adams/actions/runs/33449240525/job/99675229959).

| Full-run lane | Recorded result |
|---|---|
| Fresh install | 66 failures, 720 errors / 2,987 tests |
| Warm update | 66 failures, 720 errors / 2,987 tests |
| Migration from `50b770a3` | 46 failures, 689 errors / 2,854 tests; 19 migration scripts ran; second update remained red |
| Migration from `0a15b176` | 46 failures, 689 errors / 2,854 tests; 18 scripts ran; second update remained red |
| Nonstandard database | 2 failures, 38 errors / 70 tests |
| Meta packages | Lite install failed; Full install passed |
| Current W2 over old W1 | 0 failures, 9 errors / 17 tests |
| Browser markers | 32 of 39 required markers detected in the main lanes; this is incomplete tour evidence |
| Process-death harness | Existing opt-in real process-death test was skipped; no process-death pass is claimed |

The downloaded artifact was verified against SHA-256 `7fd00af13df457a93c4a7085cbd94cb8e473deca5a18b76dba1a53a6f49e80d4` (artifact ID `9780360888`). Original run/artifact links remain authoritative; expiration is recorded as 30 September. Counts overlap across lanes and must not be summed into independent defects.

### Root failures versus cascades

All findings below are open. Inspection establishes the failure mechanism to the stated extent; no connector correction was made this session.

| Priority / failure family | Evidence and consequence | First correction and proof |
|---|---|---|
| P0: Lite cannot install | `shopify_connector_product_webhook/pre_init.py` writes `product_template.shopify_export_status`, owned by optional product export. Lite log reports UndefinedColumn. Full installation works. | Put migration responsibility with the owning module or guard the actual optional schema contract. Fresh Lite, Full and upgrade-order probes must pass without adding export to Lite merely to satisfy the query. |
| P0: old-core compatibility | W2-over-W1 log reports missing `shopify_connector_store.activation_state`. The prior absent-additive-table repair did not cover this new column assumption. | Verify the supported installed footprint; test real supported upgrade order and any promised mixed-version bridge. Do not delete a failing compatibility lane without an explicit scope decision. |
| P1: V2 run IDs reject themselves | Run creation generates `RUN-20260831-000001`; the shared phone-pattern sanitizer transforms it to `RUN-***`, which the run-name validator rejects. This transformation was reproduced from the checked-in regex without Odoo. Run-linked concurrency tests fail during setup. | Treat typed internal identifiers separately from human-text redaction. Keep PII tests and add an ORM create/write regression, then execute the existing independent-connection races. |
| P1: activation/legacy contract collision | P15 business-job creation requires `activation_state=active`, while legacy connected-store fixtures and paths do not establish that state. The message occurs 670 times in the fresh log. | Trace supported lifecycle/admission paths and migration defaults. Correct stale fixtures only where the intended business contract proves them stale; do not globally bypass activation. Prove active/draft/paused/retired and legacy/V2 behavior. These occurrences are not 670 proven production defects. |
| P1: recovery translation fails | `shopify_connector_recovery_commands.py` uses a local `context` object of type `_RecoveryContext`; Odoo translation stack lookup calls `.get('lang')` on it. | Use the native environment translation convention or eliminate the conflicting local name. Execute attention/recovery paths under real Odoo languages and permissions. |
| P1: stale-owner sweep ORM ordering | `shopify_connector_stale_owner_sweep.py` requests ordering through `job_id.running_since`; pinned Odoo rejects that relation property in the observed query. | Use valid bounded ordering/querying while preserving scope and cache handling. Re-run pre-send/committed-send recovery and stale-owner tests. |
| P1: remaining contracts/security/UI | Logs also expose protected lifecycle writes, limited-user facade access, settings-classification and visual-registry assertions. A command-result immutability test writes a nonexistent `message` field and fails with ValueError before its intended authorization assertion. | Triage each after common roots. Test real protected fields and direct RPC permissions; repair expectations from the contract, not from whatever makes tests green. |

Source anchors: [run model](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_core/models/shopify_connector_run.py), [run metadata](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_core/models/shopify_connector_run_metadata.py), [P15 lifecycle](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_core/models/shopify_connector_p15_lifecycle.py), [Lite hook](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_product_webhook/pre_init.py), [recovery commands](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_core/models/shopify_connector_recovery_commands.py).

P10 source inspection supports retaining globally sorted lock acquisition, the runless-V1 versus registered-V2 claim fence, stale-handler manual review, workflow/operation binding, and monotonic scan checkpoints. The regression tests use distinct database connections and backend IDs, not a shared cursor. Their existence does not establish a passing race test: current run-creation failures prevent qualification. Lessons: add a small native registry/install smoke before broad changes; group integration failures before rerunning; preserve typed metadata; explicitly test optional-module schemas; treat static counts as narrow evidence.

### Environment and access

Authenticated read-only inspection reached the existing Odoo.sh project `adamsmen` / `AdamsOdoo/Adams`, Odoo 19, Middle East. The development history shows `1c75c102` and `880e7008` as test-failed builds with a `spreadsheet_sale_management` tooltip, and both are **dropped / garbage collected**. That tooltip alone does not identify a connector root cause. No active development database was available to inspect installed modules, company identity, credentials or deployed source pin. No rebuild, install, configuration write or Shopify request occurred. [Development branch](https://www.odoo.sh/project/adamsmen/branches/codex%2Fv2-continuous-implementation).

The branch page explicitly states that commits are automatically installed, tested and deployed. Therefore these proposed files are supplied as a patch instead of pushing a planning-only commit that would trigger deployment. This is an observed deployment coupling, not a demonstrated GitHub contents-write denial. A collaborator-permission endpoint returned 403; it does not prove writes are unavailable. No workflow or Odoo.sh setting was changed to evade the boundary.

After plan approval, use the standing authorization to establish a fresh isolated development build and verify project, branch SHA, Odoo/PostgreSQL versions, database, company and exact Shopify shop `testin-lzhbzhtc.myshopify.com`. Never infer credentials or installed-customer history from a dropped build. Production and staging stay outside this work. Multi-store isolation is exercised with independent native fixtures/fake ledgers; current live authorization covers only the named shop.

## Architecture, reuse and branch strategy

| Option | Delivery cost and risk | Decision |
|---|---|---|
| Continue with targeted corrections only | Least migration churn, but may preserve redundant orchestration and contradictory lifecycle paths | Useful first repair phase, insufficient as an unquestioning long-term rule |
| Preserve contracts/data; selectively replace internals | Reuses domain knowledge and fixtures; addresses demonstrated integration seams; allows incremental qualification and rollback | **Recommended** |
| Separate implementation and controlled migration | Rebuilds identity, permissions, mutation safety, historical compatibility and UX proof; current failures do not demonstrate an irreparable substrate | Reject for this release; reconsider only if native evidence proves current boundaries cannot meet required invariants |

The actual family has **13 Shopify addons**: core, product, product_export, sale, inventory, fulfillment; shared webhook plus four domain webhook bridges; Lite and Full meta packages. `adams_base` is unrelated. Preserve addon names, model/XML IDs, bindings and audit history. Keep optional-domain ownership out of core; repair the webhook/export dependency seam before considering consolidation. Avoid speculative renaming and phase-number-driven fragmentation.

Use native models and a small set of domain services. Keep one controlled Shopify transport boundary for credentials, served API version, HTTP/GraphQL/userErrors, costs and bounded retries. Keep durable mutation intent/attempt evidence distinct from mutable job/run projections. A class called a repository is not automatically wrong; retain concrete locking/transaction adapters, but add no generic CRUD wrapper around the ORM. Adopt no new queue or third-party runtime dependency in this plan. Any later dependency needs Odoo 19 compatibility, maintenance, license and deployment review tied to a demonstrated need.

Odoo/PostgreSQL provide transactions, constraints, permissions, cron execution and persistence. Connector logic still owns remote-effect uncertainty, generation fences, claims, fairness, missed-event reconciliation and operation identity. Pinned Odoo uses repeatable-read isolation; serialization/cache handling must match real cursor boundaries. Explicit commits belong only at justified framework/owned-cursor boundaries. Odoo cron batching is useful, but cron alone is not proof of the five-second start target. Prefer bounded wakeups/drains plus scheduled recovery; measure Odoo.sh behavior before promising latency. [Pinned SQL connection source](https://github.com/odoo/odoo/blob/30bde9ff758834a4912c5ae55843d3a7dad849f1/odoo/sql_db.py), [pinned cron source](https://github.com/odoo/odoo/blob/30bde9ff758834a4912c5ae55843d3a7dad849f1/odoo/addons/base/models/ir_cron.py), [Odoo coding guidelines](https://github.com/odoo/documentation/blob/19.0/content/contributing/development/coding_guidelines.rst), [PostgreSQL locking](https://www.postgresql.org/docs/16/explicit-locking.html).

Preserve database-backed deterministic identity, server-side RPC authorization, company/store rules, admission and pre-send generation checks, explicit lock order, claims/expiry, no broad record locks across HTTP, durable intent before send, mutation-specific readback, first-push approval, safe catalog ownership and variant/media handling. A database rollback cannot undo Shopify. Public-method ACL assumptions are insufficient; direct RPC and counters must be tested. [Odoo security](https://github.com/odoo/documentation/blob/19.0/content/developer/reference/backend/security.rst).

Continue PR #212 from its freshly verified head after approval, with small coherent commits and draft status. Do not create a replacement implementation branch now. If isolation is later necessary, branch from the exact refreshed PR #212 head with recorded provenance; never reset/rebase/force-push or overwrite other work. PRs #210/#211, main, staging and unrelated modules remain preserved. Stop new admission and reconcile uncertain work before a runtime rollback; reverting source is not a database/remote rollback plan.

## Scope, authentication and UX decisions

Retain V1 commercial correctness while completing U1–U14. Preserve Odoo-authoritative inventory, both accepted fulfillment operating modes, controlled product export/media, duplicate-safe order intake, all supported triggers and independent stores. Advanced refunds/returns/accounting/payouts/Markets/metafields/subscriptions/gift cards/POS/B2B/licensing remain outside this release unless an existing accepted contract explicitly requires the narrower behavior. Refund/cancellation evidence and actionable holds remain required even without refund automation.

The current visible role selector has **Administrator and User**, with Operator/Reviewer/Auditor retained as internal capability groups and stable IDs. Recommend retaining this customer-facing simplicity while testing every capability and no-access boundary. V2 prose that lists four roles should distinguish test capabilities from selectable product roles; do not remove reviewer checks or expose new roles merely to match prose. [Security definition](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/addons/shopify_connector_core/security/shopify_connector_security.xml).

Shopify client-credentials grant requires the app and store to belong to the same organization, and tokens expire after 24 hours. Merchant-managed distribution can fit that arrangement; a developer-owned app serving unrelated merchants cannot assume the same flow. Verify merchant ownership, scopes and refresh in setup before calling commercial onboarding qualified. Retain supported legacy-token input only for credentials the platform actually provides. No OAuth/public-app build is implied. [Shopify client credentials](https://shopify.dev/docs/apps/build/authentication-authorization/client-credentials-grant?lang=node), [V1 distribution contract](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/release/v1-supported-scope.md).

Keep Admin API 2026-07 and verify the response version during live setup. GraphQL costs are scoped per app/store; bound pagination and input batches, respect actual throttle observations, and reserve bulk-operation complexity for measured volume. The official productSet page identifies itself as 2026-07/latest and warns that supplied list fields remove omitted existing entries; destructive catalog behavior requires explicit ownership and preview. Idempotency must be checked per mutation, not assumed universal. Exact inventory/fulfillment/media reference pages were not successfully retrieved this session; refresh the operation catalog against served schema before changing those integrations. [Versioning](https://shopify.dev/docs/api/usage/versioning), [limits](https://shopify.dev/docs/api/usage/limits), [productSet](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet), [idempotent requests](https://shopify.dev/docs/api/usage/idempotent-requests).

Use Overview, Needs Attention, Products, Orders, Inventory, Fulfillment, Runs and Settings. Retain native list/form navigation and use Owl for setup, progress, matching and comparisons. The inspected historical dashboard screenshot has useful status/evidence density but redundant healthy banners and older Sync Center/Error Center concepts. Reuse the evidence hierarchy, consolidate healthy states, and make issue impact and next action prominent. The live V2 design URL reached a separate sign-in gate; its interactive behavior was not reviewed. A static screenshot is not journey proof. Current V2/P16 assets are unmanifested, and the existing launcher exposes five named read/scan/reconciliation actions, not a general mutation launcher.

Vendor sources were refreshed for Webkul, Teqstars, Emipro and Ventor; the two requested Odoo Apps listings were also requested. Treat feature and performance language as vendor claims, not independent proof. Reuse established configuration/mapping previews, queue diagnostics and record navigation patterns; do not add commercial features to match a checklist or copy assets. No current price recommendation is made. [Webkul](https://webkul.com/blog/odoo-multichannel-shopify-connector/), [Teqstars 19](https://docs.teqstars.com/19.0/applications/shopify.html), [Emipro v17 reference](https://docs.emiprotechnologies.com/shopify-odoo-connector/v17/toc.html), [Ventor](https://ecosystem.ventor.tech/product/odoo-shopify-connector-pro/), [ecommerce_shopify](https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify), [sh_shopify_connector](https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector).

## Small instruction cleanup, proposed

| Files / actual conflict | Proposed resolution after approval |
|---|---|
| `CLAUDE.md`, `AGENTS.md`: obsolete phase/base guidance alongside later V2 instructions | One concise root operating contract; source hierarchy and canonical handoff pointer; current user authorization takes precedence over stale project routing |
| `CHATGPT.md`, `GPT_SOL.md`, dated role addendum: separate mandatory model roles, no self-review, and legacy branch/startup stops | Retain as historical role guidance with a short supersession pointer. Latest owner instruction assigns Astra directly and requires fresh critical self-review, without claiming independent external assurance. |
| `.claude/README.md`, `.claude/skills/README.md`, `.claude/agents/README.md` | These are placeholders/guidance, not functioning installed project skills or a required agent team. Keep a short specialist index; no swarm. No nested AGENTS files were found in the complete tree. |
| `docs/v2/README.md`, `12-lighter-model-execution-handoff.md` | Correct docs-only/locked-architecture assumptions; replace mandatory broad reruns per small step with affected-gate rules and stable-candidate qualification |
| Root SQL-after-profiling wording | Distinguish correctness SQL for locking/constraints from performance SQL that needs measurement. Keep authorization, parameterization and ORM cache obligations. |
| `docs/06-prompts/implementation-task-template.md` and old implementation indexes | Reuse the objective/base/paths/invariants/tests/rollback fields, but remove per-task user reauthorization and obsolete model handoffs within the approved plan |
| `docs/v2/08`, `09`, `11`: late UI sequencing, role terminology, 20-store stress versus ten-store support | Permit UI integration after each backend slice; align visible roles with tested capabilities; label overload/rejection tests separately from supported-volume qualification. Preserve numerical safety gates pending explicit decision. |
| `docs/v2/13-continuous-execution-handoff.md` | Replace stale publish-next/uncommitted claims with verified current head, red CI, dropped builds and the approval gate. Keep one status source. |

No global settings, skills, hooks or CI definitions were changed. The inspected workflows run on both push and pull_request; duplicate full jobs occurred for this head. Later optimize duplicate triggers/path routing only with required-check behavior preserved. Do not change deployment mechanics merely to publish these notes.

## Delivery and qualification plan

Dates assume kickoff 8 September and prompt approval/access availability. Astra owns every technical row. Delayed approval, unavailable quota or failed gates move dependent dates; elapsed calendar days do not satisfy a gate.

| Dates / day | Deliverable and dependency | Completion evidence |
|---|---|---|
| 8–9 Sep / D1–2 | Rebaseline, approve scope, prove isolated dev target and installed footprint | This package; exact source/build/database/company; supported upgrade list; secure shop identity and scopes |
| 10–13 Sep / D3–6 | Repair install, run metadata, lifecycle and recovery failure families | Small native Lite/Full registry smoke first; focused ORM/security; real independent-connection P10 tests; one coherent full CI boundary |
| 14–18 Sep / D7–11 | Complete inventory, catalog export/media and fulfillment runtime slices; assemble each production UI after its backend proof | Domain fault/readback evidence; stale preview/generation and timeout recovery; runnable U3–U9 slices; early U14 loop |
| 19–22 Sep / D12–15 | Finish U1–U14 surfaces, settings/readiness, multi-store isolation and recovery; freeze candidate when actually ready | Browser success/failure/empty/stale states; native records and live readback; role/RPC tests; release-scope ledger complete |
| 23–28 Sep / D16–21 | Stable-candidate CI/Odoo.sh lifecycle, performance, accessibility/RTL, moderated usability, defect correction and packaging | Required evidence on identified bytes; known limitations; tested backup/restore; no unresolved critical/high findings; honest remaining-canary status |
| 29 Sep–5 Oct / D22–28, conditional extension | Finish required observation windows and affected reruns; deliver release-readiness decision | All canary/volume/UX gates passed and final evidence linked; publication still requires final authorization |

**Critical-path arithmetic:** current M6 requires 10,000 deterministic inventory intents and 72 continuous hours; M7 starts after inventory soak and requires 5,000 catalog intents plus 72 hours; M8 starts after accepted inventory/catalog evidence and requires 2,000 fulfillment intents plus seven days. This adds **13 sequential observation days** after the inventory candidate is ready. If inventory begins canary at the start of 19 September, earliest completion is the start of 2 October. Earlier readiness could bring this forward; affected changes can restart it. Thus 21 days requires inventory canary readiness by roughly day 8 and timely stable downstream slices, which the red foundation does not currently support as a reliable commitment. [Cutover gates](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/v2/08-migration-and-cutover-blueprint.md).

Retain these gates in the recommendation. Do not silently overlap sequential canaries or call a release complete while they are pending. Production cohorts and the later two-release/14-day schema contraction are outside this development campaign. Real-event canaries must use authorized development fixtures; no unapproved merchant store is implied. The existing usability rule also requires five representative participants per primary role group and at least 90% unaided completion; model/browser automation cannot supply human participants. Plan those sessions early. [Qualification and usability contract](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/v2/09-test-observability-release-blueprint.md).

During implementation, use focused behavioral tests and native smoke checks; run affected domain/concurrency suites at integration boundaries; run the full campaign on a stable candidate. Preserve original red evidence. Trace the older 36 UAT scenarios into U1–U14 instead of duplicating campaigns. Fresh install, same-version update and actual version migration remain separate results. Record migrations executed, not merely an upgrade command. Prove interrupted recovery and restore without replaying remote effects.

For every live scenario record run ID, owned fixtures, before/after, expected writes, independent readback and cleanup/compensation. Disable customer notifications and payment effects. Exercise connector jobs/services; direct record writes establish fixtures only. Measure acknowledgment p95 ≤1s/no accepted request ≥5s, durable evidence ≤2s, due start ≤5s, event-to-state p95 ≤15s/p99 ≤60s and active UI refresh ≤5s. Record sample count, elapsed clock boundaries, offered load/backlog, API budget, environment and source; none of these targets is currently qualified. Do not advertise 600 jobs/hour from a stub benchmark.

### Usage discipline

Actual Astra remaining allowance/reset is not exposed by the inspected tools. Official guidance does not establish this account's quota. Ask once for remaining allowance and reset cadence before committing the schedule. Use Astra directly; no Claude prerequisite, delegated worker or background execution is claimed. [Official Astra guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra).

Provisional budget: 20 planned coherent work units plus 7 reserved units (about 26% reserve). A unit means one bounded change/integration result, not a message, token allowance or guaranteed day. Allocate planned units: intake/access 2, foundation 5, domains 6, UX integration 3, qualification/packaging 4. Reserve is for discovered defects and final review/qualification. Re-estimate after the first native correction and two domain slices; drop optional research before consuming reserve. Never trade away accepted safety gates to fit quota.

Current ledger: one rebaseline session completed; actual token/quota consumption unknown; zero new full-CI campaigns, zero native Odoo campaigns and zero Shopify effects initiated; prior CI artifacts reused. Each subsequent unit records actual observed allowance delta when available, source/evidence, time and remaining blockers in the canonical handoff. Research is delta-only after this checkpoint.

## Coverage and unresolved inputs

The recursive repository tree was inventoried (2,060 blobs; not truncated). Root instructions, role guides, project skill/agent placeholders, workflow definitions, V2 documents 01–13 and index, selected research/ADRs/rejected approaches/V1 release material, all addon manifests, P10/runtime/lifecycle/security/facade and failing test paths were inspected. Large documents were reviewed by relevant sections; this is not a line-by-line audit of all 2,060 files or all 390 PR files. The source/material, product, architecture, prompt and implementation-plan indexes were used to distinguish history from current contracts. One historical dashboard image was visually inspected; no comprehensive current UI review occurred.

The attached webarchive was read completely. The referenced `Shopify Connector Status Update.txt` was not attached and was not found by the available exact-title search; its contents were not invented. The X article body was inaccessible; no advice is attributed to it. The resource inventory identifies the private Google Doc as the `ecommerce_shopify` Get Started guide, not verified internal project requirements; its body remains inaccessible. Several Odoo web documentation pages failed, so official 19.0 documentation source and pinned Odoo code were used. Some exact Shopify mutation pages remain unrefreshed; operation-specific validation is an implementation prerequisite. These limitations do not prevent this recommendation.

Before a delivery commitment, the material unresolved inputs are: (1) actual Astra allowance/reset; (2) whether any real customer installations exist and which versions/addon combinations need supported upgrades; (3) availability of representative users for the existing usability gate. Until footprint evidence exists, preserve the current migration matrix. No reconfirmation of the named development-store permissions is required.

This first session ends at approval of the proposed scope, selective-reuse architecture and honest schedule. No production code, remote branch, deployment, acceptance status or release setting was changed.
