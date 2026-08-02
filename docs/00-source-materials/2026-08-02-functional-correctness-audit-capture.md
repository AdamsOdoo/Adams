# Source Capture — Adams Odoo↔Shopify Functional Correctness and Data Integrity Audit (2026-08-02)

> **Provenance.** Received 2026-08-02 from the product owner as
> `Adams_Odoo_Shopify_Functional_Correctness_and_Data_Integrity_Audit.docx`,
> produced by the ChatGPT 5.6 control room as a read-only audit of the governed
> candidate `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` (PR #204, open, draft).
> Captured under CLAUDE.md §7 ("capture, don't just link") because this
> document is a decision input that otherwise exists only as a chat
> attachment. Converted DOCX → Markdown with a stdlib XML extractor
> (paragraphs + tables); wording unchanged. Classification per CLAUDE.md §8:
> findings F-01…F-09 are **review claims** until independently verified;
> the verification results (F-01/F-02/F-03 CONFIRMED at source level, others
> spot-confirmed) are recorded in
> [`../02-product/ui-restructure-design-contract-2026-08-02.md`](../02-product/ui-restructure-design-contract-2026-08-02.md) §2.

---

ADAMS ODOO 19 ↔ SHOPIFY

Functional Correctness
and Data Integrity Audit

Exact-head source and CI assurance • Data-flow and failure-boundary review • Release gates

| DECISION IN ONE LINE / Preserve the integrity substrate; repair onboarding, mode switching, order/reporting semantics and remote verification; then require exact-head Odoo.sh and controlled Shopify acceptance before release. |
|---|

| Audit item | Pinned value |
|---|---|
| Prepared for | Mostafa — correctness and release decision |
| Audit date | 02 August 2026 |
| Repository | AdamsOdoo/Adams — read-only review |
| Governed candidate | 49cfffbd5ff0eca85d2b855d9ebd2e414680af8e |
| PR status | PR #204 — open, draft, unmerged |
| Evidence status | Exact-head CI green; exact-head Odoo.sh and Shopify UAT outstanding |

No code, branch, pull request, Odoo.sh environment, Shopify store, configuration or business data was changed.


# Audit map

| CURRENT RELEASE POSTURE / The exact head has strong deterministic CI evidence, but no remote synchronization flow is fully Proven. Three user-facing correctness defects are release blockers: onboarding refresh completion, Mode 2 transition recovery and sales metric accuracy. |
|---|

| Sections | Purpose |
|---|---|
| 1–3 | Verdict, critical findings and flow assurance |
| 4–6 | Source-of-truth, data lifecycle and technical correctness |
| 7–9 | Functional flows, multi-store isolation and dashboard contracts |
| 10–12 | Component disposition, validation campaign and release blockers |
| 13 | Final control-room decision and linked source register |

Verdict convention: Proven requires exact-head native runtime plus controlled Shopify evidence; source and CI strength alone are classified Partially Proven.


# 1. Executive decision

The connector contains a strong integrity substrate, but the exact candidate is not yet certifiable as end-to-end correct. The correct decision remains a governed hybrid rebuild:

preserve the durable job, store/company scope, binding, mutation-attempt, idempotency, reconciliation, inventory-CAS, preview and first-push controls;

refactor business-read admission, onboarding orchestration, remote-acknowledgement semantics, order lifecycle/accounting, mode switching and reporting definitions;

rebuild the operator shell and the two dashboards around validated business states;

do not merge or release until the release-blocking defects are corrected and an exact-head Odoo.sh plus controlled Shopify acceptance campaign passes.

The evidence is stronger than the PR narrative alone suggests. Exact-head GitHub Actions run 30715082576 passed fresh install, warm update, two migration origins and a browser/HOOT suite. Each main campaign reported 2,511 tests with zero failures and zero errors; the nonstandard campaign reported 62 tests with zero failures and zero errors. The artifact records no Shopify operation and one sanctioned process-death skip. This is strong local/CI proof, but not native Odoo.sh qualification or Shopify-side confirmation.


## Verdict scale

| Verdict | Meaning in this audit |
|---|---|
| Proven | Exact-head production path, native runtime and controlled Shopify result are evidenced, including failure and reconciliation cases. |
| Partially Proven | Source and exact-head CI support the design, but one or more runtime, remote, lifecycle or reachability layers remain unverified. |
| Unproven | The required behavior lacks sufficient executable evidence or an accessible end-to-end path. |
| Incorrect | A source-level defect or data-definition contradiction is reproducible from the current implementation. |

No remote synchronization flow qualifies as fully Proven because the exact head has not been qualified on Odoo.sh or against a controlled Shopify store.


## Severity scale

| Severity | Meaning in this audit |
|---|---|
| Critical | A demonstrated path to material data corruption, cross-store/company leakage, destructive remote action or unrecoverable business loss. |
| High | A release-blocking correctness or operability defect with a recoverable or technically assisted path. |
| Medium | A material assurance, consistency or product-truth gap whose current safeguards limit direct corruption risk. |
| Low | Documentation, packaging or maintainability drift without a demonstrated incorrect business result. |


# 2. Highest-priority findings

| ID | Severity | Finding | Evidence-backed consequence | Required decision |
|---|---|---|---|---|
| F-01 | High | Onboarding location refresh does not update the active wizard session to completion | The server admits and tracks a store-scoped asynchronous job, but the setup client performs one RPC and does not poll that job to terminal or automatically reload locations/readiness. A later page reload may recover the result, but the guided flow itself is incomplete. setup client | Repair before UI freeze; add genuine browser/dispatcher acceptance. |
| F-02 | High | Mode 1 → Mode 2 can remain stuck in the normal UI until technical recovery | The flag is written before enqueue success is checked; for a non-connected store, admission can return no job without raising. Unexpected terminal scan failures also have no cleanup path. Although a rollback method exists, the current wizard may not expose it while effective mode remains Mode 1. switch scan | Replace with a durable requested/effective-mode state machine and normal-UI terminal recovery. |
| F-03 | High | Sales totals can misstate post-import financial divergence | Existing-order refresh preserves the original Odoo commercial lines. The aggregate excludes cancelled/quarantined orders but not orders marked for Shopify review, so partially refunded or otherwise financially divergent reviewed orders can remain in amount_total sums. order importer sales projection | Label the metric “Imported Odoo order value” and exclude or separately disclose unresolved review cases until lifecycle adjustments are implemented. |
| F-04 | Medium | Merchant-facing export status does not distinguish evidence source consistently | Direct synchronous mutations validate transport, GraphQL errors, userErrors and returned identity; that is valid immediate outcome evidence. Independent reconciliation/readback is primarily used after uncertainty. The UI should distinguish “Shopify response confirmed” from “independently read back” where business risk requires it, and asynchronous operations must not complete before terminal success. product export | Add explicit evidence-source statuses and a risk-based verification policy. |
| F-05 | High | Existing-order lifecycle is narrower than “order synchronization” | Supported initial order creation is careful, but edited, cancelled, refunded, duty/fee/tip and divergent-currency cases are skipped or routed to review. Existing-order refresh principally updates evidence, not commercial lines/refunds. | Declare supported scope, block misleading claims, and implement or reconcile the missing lifecycle. |
| F-06 | Medium | Some decision-relevant reads bypass the job-bound business-call contract | Inventory pair/location reads, fulfillment reads and several product-export reconciliation reads use legacy execute(). This can admit stale or wasted reads across credential/generation changes; current mutation gates reduce the risk of an unsafe write. API client | Migrate these reads to a read-specific admitted contract. |
| F-07 | Medium | Customer import lacks a complete merchant-facing discovery flow | Targeted resolution is conservative and order-driven, but there is no complete standalone enumerate/scan/import workflow evidenced at the candidate. | Mark deferred or implement a store-scoped customer discovery operation. |
| F-08 | Medium | Webhook processing is not present as a production capability | The reviewed modules expose readiness language but no controller/subscription/deduplication pipeline. Current correctness therefore depends on manual/scheduled scans and reconciliation. | State scan-based freshness honestly; treat webhooks as a separate future capability with HMAC/dedup/order handling. |
| F-09 | Low | Module metadata contradicts implemented capability | Several manifest summaries still describe core/sale/fulfillment as lacking UI or business flows that the modules now contain. | Correct manifests and operator/technical documentation before release. |


# 3. Assurance matrix by flow

| Flow | Verdict | What is strong | What prevents certification | Disposition |
|---|---|---|---|---|
| Store identity, company scope, credentials and reconnect | Partially Proven | Permanent domain uniqueness, one-company ownership, connection generation, guarded lifecycle and scoped jobs | No exact-head Odoo.sh or live credential-rotation acceptance | Preserve; validate live |
| Onboarding refresh, linking, readiness and activation | Incorrect | Server admission, duplicate coalescing, cache upsert, readiness checks | Client does not track asynchronous refresh to terminal; real resume/reload journey unproven | Refactor immediately |
| Product/variant import | Partially Proven | Paginated GraphQL reads, explicit identifiers, cautious matching, stale binding instead of local deletion | No live Shopify campaign; merchant discovery/reconciliation reachability still needs acceptance | Preserve with validation |
| Customer import/matching | Partially Proven | Email-based conservative matching; no blind creation without usable identity | Existing partners are not comprehensively refreshed; full enumeration is absent | Extend selectively |
| Initial order import for supported clean cases | Partially Proven | Monetary evidence, taxes/discounts/shipping, presentment checks, explicit mappings and bounded totals validation | Remote runtime untested; numerous lifecycle shapes are intentionally excluded | Preserve supported kernel |
| Edited/refunded/cancelled order lifecycle | Unproven | Divergence is detected and can route to review | Commercial Odoo order lines/refunds are not kept equivalent to later Shopify state | Refactor or explicitly scope out |
| Product/variant export | Partially Proven | Preview, confirmation, expiry, non-destructive list handling, returned-identity checks and uncertainty recovery | No risk-based verification policy and no live Shopify result | Preserve + add verification |
| Media export | Partially Proven | Staged upload/file creation/readiness polling/attachment path | No live file/media acceptance and cleanup campaign | Preserve + validate |
| Inventory export | Partially Proven | Explicit location/item binding, first-push guard, absolute quantity CAS, idempotency directive, uncertainty reconciliation | No live concurrency/timeout campaign; business-read admission seam | Preserve; high-priority UAT |
| Fulfillment/tracking export | Partially Proven | Fulfillment-order IDs, location/quantity handling, tracking update and reconciliation paths | No wire idempotency, remote UAT, or crash-boundary acceptance | Preserve with reconciliation UAT |
| Mode 2 inbound fulfillment | Partially Proven | Extensive eligibility/review checks and conservative application | Switch orchestration is incorrect on failure; live multi-location cases unverified | Refactor switch; validate engine |
| Job retry, replay and ambiguous-mutation recovery | Partially Proven | Durable states, operation scopes, attempt evidence, reconciliation and manual resolution | One process-death test is sanctioned-skipped; no genuine distributed-worker/Odoo.sh campaign at head | Preserve; native chaos tests |
| Multi-store/multi-company isolation | Partially Proven | Store is the scope anchor; company/store constraints are pervasive | No adversarial live campaign across two companies and multiple stores | Preserve; security acceptance |
| Connector Health dashboard | Partially Proven | Derived from jobs/attempts and separates operational state from sales | Target page not yet implemented/qualified; KPI-to-record reconciliation needed | Rebuild and test |
| Sales dashboard | Incorrect | Currency separation and domain drill-down are structurally good | Lifecycle-divergent review orders can remain in totals; metric source/definition is not merchant-safe | Redefine and rebuild |
| Webhooks | Unproven | Scan/reconciliation concepts reduce dependency on event delivery | No production webhook controller/subscription/dedup pipeline evidenced | Defer transparently or implement later |


# 4. Source-of-truth matrix

| Domain/field | Intended authority | Current transfer rule | Accuracy risk | Required acceptance |
|---|---|---|---|---|
| Store identity | Shopify permanent domain and shop identity; Odoo owns company association | Unique domain; credential test and connection generation | Store replacement/reconnect must never reuse stale generation | Reconnect test with rotated credential and changed shop identity |
| Product descriptive data | Configurable, generally Shopify for import; Odoo for export when enabled | Explicit bindings and guarded refresh/export | Conflict policy is distributed across settings and operation mode | One field-level authority table shown during onboarding |
| Variant SKU/barcode | Existing Odoo identifier used for conservative match; Shopify identity bound per store | Ambiguity routes to decision; blank identifiers are not blindly created | Duplicate/mutable identifiers can strand bindings | Duplicate SKU/barcode and reassignment campaign |
| Product price | Configurable source of truth | Import/export only when configured | Currency/tax-included semantics need store-specific acceptance | Round-trip price examples by currency and tax configuration |
| Customer identity | Shopify customer ID per store; Odoo partner matched conservatively by normalized email | Order-driven resolution; no phone/name blind match | Shared email, guest checkout and changed email can produce ambiguity | Deterministic guest/shared-email cases |
| Order identity | Shopify order ID per store | Store-scoped binding and version evidence | Existing commercial state can diverge after edits/refunds | Lifecycle ledger and reconciliation rule |
| Order money | Shopify order payload for source evidence; Odoo sale order for booked operation/reporting | Initial supported orders validated; later evidence refresh does not rewrite commercial lines | Dashboard/accounting misstatement if “Shopify sales” is inferred | Define gross/net/refund/cancel, date basis and included states |
| Inventory available quantity | Odoo configured stock location | Absolute Shopify set with compare/change-from quantity and first-push protection | Concurrent remote changes, negative local quantity and stale reads | Two-worker CAS, timeout-after-accept, drift and reconciliation tests |
| Fulfillment | Mode-dependent: Odoo outbound in Mode 1; Shopify fulfillment orders drive inbound application in Mode 2 | Explicit fulfillment-order/location/line quantities | Mode transition ambiguity and duplicate creation after timeout | Partial/multi-location/crash-boundary campaign |
| Tracking | Odoo picking/carrier reference in outbound mode | Update existing remote fulfillment tracking | Remote manual edits and stale fulfillment identity | Read-before-update plus verified readback |
| Dashboard sales | Must be explicitly defined | Current implementation sums eligible imported Odoo sale orders by currency | Review/refund divergence remains included | Exact KPI-to-record reconciliation fixture |
| Connector health | Odoo job/attempt/reconciliation ledger | Counts current operational states | Stale queued jobs, retries and reconciled ambiguity must be distinguished | Every KPI drill-down equals its source domain |


# 5. Data lifecycle contract

Every synchronization must produce one traceable chain:

1. Source evidence — store, company, direction, source identity, version and immutable payload hash/snapshot.

2. Eligibility — connection generation, permission, readiness, domain enablement, authority and mapping checks.

3. Mapping — exact store-scoped product/variant/customer/location/workflow binding.

4. Transformation — field-level conversion, defaults, units, currency, tax and rounding rules.

5. Admission — one durable store-scoped job with operation scope/idempotency evidence.

6. Execution — lease owner, attempt identity, transaction boundary and request evidence.

7. Remote outcome — transport status, GraphQL top-level errors, userErrors, returned identity and throttle cost.

8. Verification — readback or asynchronous-operation completion where the risk requires it.

9. Binding — local/remote identities, remote version, local version, timestamps and generation.

10. Reconciliation — scheduled/on-demand detection and repair of missed, stale or ambiguous results.

11. Presentation — one operator state derived from the same authoritative job/attempt/binding facts.

The connector’s job and mutation-attempt substrate already covers much of admission, execution and uncertainty handling. The design gap is mainly consistent application and merchant-readable presentation.


# 6. Technical correctness findings


## Transactions and crash boundaries

Odoo and Shopify cannot share an atomic transaction. The safe pattern is therefore: durable intent, commit, pre-transport revalidation, remote call, durable observation, then reconciliation if the observation is missing or ambiguous. The candidate’s Layer-2 mutation machinery follows this pattern more carefully than typical connectors. It should be preserved.

The remaining assurance gap is executable process separation. Exact-head CI has broad transactional coverage, but the artifact records the real process-death harness as a sanctioned skip. Native Odoo.sh worker/process tests must deliberately kill execution before send, after send/before observation, and after observation/before local binding commit.


## Idempotency and duplicate prevention

The connector uses store-scoped job identity and operation scopes. Inventory also uses Shopify’s 2026-07 inventorySetQuantities contract with change-from quantity and idempotency evidence. Shopify documents absolute quantity setting as a compare-and-set operation and requires care because the app becomes responsible for the state it writes. Shopify inventory contract

Fulfillment creation has no equivalent wire-level idempotency key in the reviewed mutation call. Correctness therefore depends on local intent uniqueness plus post-timeout reconciliation against Shopify. This is acceptable only if timeout-after-accept and worker-death tests prove that duplicate remote fulfillment is not created.


## GraphQL result handling

HTTP success is not business success. The code generally checks top-level GraphQL errors, mutation userErrors and expected returned identities. Merchant-facing status must preserve the distinction:

Queued

Sending

Shopify response confirmed

Independently verified in Shopify

Ambiguous — verification required

Rejected

For synchronous productSet, Shopify returns the product; asynchronous execution returns an operation that must be checked separately. Omitted list fields can also remove existing list entries, so the current non-destructive guard is important. Shopify `productSet`


## Business reads

Business mutations are lease/generation fenced. Some inventory pair/location reads, fulfillment reads and product-export reconciliation reads still use a legacy client path that can acquire/refresh credentials without the same job-bound business-read contract. The mutation gate prevents unsafe writes after generation change, but wasted/stale reads can feed retries or decisions. Create a first-class execute_business_read(job, ...) path with connection generation, lease ownership, store/company and purpose checks.


## Webhooks and reconciliation

No production webhook pipeline was evidenced. That must not be obscured by a webhook_ready label. Shopify states that webhook delivery is not guaranteed and ordering is not guaranteed; implementations must verify HMAC, deduplicate by delivery ID and reconcile missed state. Shopify webhook behavior delivery verification

Scan-based operation can be correct if freshness targets are disclosed and reconciliation is durable. Webhooks should be an accelerator, never the sole correctness mechanism.


# 7. Functional flow specifications


## Onboarding and activation

Activation is allowed only when authentication, shop identity, scopes, enabled domains, source-of-truth rules, store-specific mappings, first-push controls, fulfillment mode and readiness checks are complete. Configuration must not leak into day-to-day Operations.

Required location-refresh acceptance:

one click admits exactly one store-scoped refresh job;

duplicate clicks coalesce onto the same in-flight job;

the browser follows that job until a terminal state;

success reloads locations and recomputes readiness;

failure exposes reason, retry and the preserved job identity;

save/reopen resumes the exact store and step;

a disconnected/reconnect-needed generation cannot silently use stale locations;

a real browser, dispatcher and worker perform the test; mocked immediate payloads do not count.


## Orders

The current importer is intentionally conservative. That is a strength, provided product language is exact. It should claim “supported order import with review gates,” not universal order mirroring.

Required lifecycle decision:

either implement local adjustment/refund/cancellation semantics and reconcile them to Shopify;

or preserve the original imported Odoo order, create explicit divergence/review records, exclude unresolved cases from “reconciled sales,” and state that Odoo commercial documents are not retroactively rewritten.

Whichever policy is chosen must define gross sales, net sales, refunds, cancellations, test orders, tips, duties, shipping, cash rounding, shop versus presentment currency, payment date versus order date and multi-currency aggregation.


## Inventory

Preserve the first-push preview/confirmation gate and absolute-quantity CAS design. Required live cases include: fresh equality, remote drift, concurrent worker, duplicate click, inactive level activation, negative local availability, timeout before acceptance, timeout after acceptance, throttling and credential generation change. Every uncertain write ends in verification, not blind retry.


## Product and media export

Preserve preview expiry, confirmation and non-destructive list-option safeguards. A successful direct response should become Accepted; selected high-impact updates become Verified after readback. Media readiness must remain a separate stage; file creation alone is not attachment success.


## Fulfillment and Mode 2

Represent mode transition with separate fields:

effective mode;

requested mode;

transition state;

transition job;

blocker/reason;

retry or rollback action;

last verified timestamp.

Setting requested Mode 2 must not change effective mode. Only a clean terminal reconciliation scan may do that. Admission failure returns to stable Mode 1. Retryable terminal failure exposes retry. Non-retryable failure returns to recoverable Mode 1 while preserving evidence. Duplicate confirmation cannot create a second scan.


# 8. Multi-store and multi-company correctness

The candidate’s basic model is sound: one permanent Shopify domain per connector store, each store owned by one Odoo company, and multiple stores allowed for a company. Correctness acceptance must prove:

all bindings and remote identities are unique within store scope, never globally by Shopify GID alone;

jobs, attempts, mappings, credentials, throttle state, connection generation and reconciliation are store-isolated;

record rules block cross-company reads and actions, not only menu access;

one exhausted or failing store does not pause another;

“All stores” health retains failing-store visibility;

monetary sales are never summed across incompatible currencies;

a user with neither connector User nor Administrator role has no connector access;

Configuration remains Administrator-only while operational actions follow the visible User role plus hidden capability guards.


# 9. Dashboard correctness contracts


## Sales Dashboard

The Sales Dashboard must be a reporting surface, not a connector-health surface. Each KPI requires a written formula, source model, included/excluded states, currency treatment, date basis and drill-down domain. The drill-down record set must recalculate to the exact displayed number.

Minimum KPIs:

reconciled orders;

gross sales by currency;

refunds/adjustments by currency;

net sales by currency;

average order value by currency;

orders awaiting data review, shown separately and excluded from reconciled totals.

Do not use “Shopify sales” for a sum of unchanged Odoo orders after Shopify lifecycle divergence. Use “Imported Odoo order value” if that is the intended metric.


## Connector Health

The Connector Health page must use job, attempt, throttle, mapping/readiness and reconciliation evidence. Minimum states:

healthy stores;

stores needing attention;

oldest queued job and queue depth by store/domain;

retries and exhausted failures;

ambiguous mutations awaiting verification;

last successful synchronization by domain/store;

API throttle headroom;

stale mappings/readiness checks;

Mode 2 transitions and blockers.

No sales KPI belongs on this page. No health total may hide a failed store. Every KPI drills into its exact source rows.


# 10. Preserve / refactor / rebuild decisions

| Component | Decision | Reason |
|---|---|---|
| Store/company identity and connection generation | Preserve | Strong scope and stale-generation defense |
| Durable job state machine and operation scopes | Preserve | Core duplicate/retry/recovery substrate |
| Mutation-attempt evidence and reconciliation | Preserve | Correct response to non-atomic remote writes |
| Product/variant/customer/order bindings | Preserve | Store-scoped identity is foundational |
| Supported initial-order financial solver | Preserve | Conservative and evidence-rich for admitted cases |
| Inventory CAS and first-push controls | Preserve | Aligned with current Shopify quantity contract |
| Product export preview/expiry/non-destructive guards | Preserve | Reduces destructive catalog mistakes |
| Fulfillment-order/location/quantity engine | Preserve conditionally | Strong model; requires live remote acceptance |
| Business read admission | Refactor | Reads need one lease/generation-bound path |
| Onboarding async orchestration | Refactor | Current client journey is functionally incomplete |
| Mode switching | Refactor substantially | Current flag/job lifecycle can remain stuck in the normal UI until technical recovery |
| Existing-order lifecycle and refund policy | Refactor or explicitly scope out | Evidence and commercial documents can diverge |
| Remote acknowledgement statuses | Refactor | Accepted and independently Verified must differ |
| Dashboard query definitions | Refactor/rebuild | Health logic is promising; sales definition is unsafe |
| Navigation, onboarding UI and dashboard shell | Rebuild | Product structure must reflect operator work |
| Webhook capability | Defer transparently or build separately | Not present; scans/reconciliation remain authoritative |


# 11. Required exact-head validation campaign


## Gate A — deterministic CI

retain fresh install, warm update and both migration origins;

retain 2,511-test identity stability or explain intentional changes;

eliminate or separately execute the process-death skip;

make module manifests and declared capability accurate;

generate requirement → production path → test → result traceability.


## Gate B — native Odoo.sh

install the exact candidate SHA on a clean database;

repeat upgrade/migration on representative predecessors;

run scheduled actions, separate workers and real browser tours;

capture module versions, Odoo core pin, database origin, logs, skips and exact SHA;

test worker termination at pre-send, post-send/pre-observation and post-observation/pre-binding boundaries.


## Gate C — controlled Shopify store

use at least two stores, two currencies and two Odoo companies;

execute genuine GraphQL requests for product/variant/media, inventory and fulfillment;

cover HTTP/GraphQL/userError, throttling, scope removal, timeouts and asynchronous completion;

manually change Shopify state and prove reconciliation;

prove remote identity/readback for every exported domain;

verify no cross-store or cross-company data leakage.


## Gate D — business reconciliation

reconcile order amounts field by field for taxes, discounts, shipping, tips, duties, cash rounding, refunds and currencies;

reconcile inventory before/after quantities at every mapped location;

reconcile fulfillment-order line quantities, location and tracking;

prove each dashboard KPI equals its drill-down records;

sign off supported/unsupported lifecycle language.


## Gate E — user acceptance

complete onboarding from blank store to ready state without technical intervention;

refresh and link locations through real asynchronous jobs;

switch Mode 1 → Mode 2, force failure, retry and roll back;

operate multiple stores without losing context;

prove export Accepted versus Verified states to a nontechnical operator;

verify responsive, RTL, access-role and accessibility behavior.


# 12. Release blockers and acceptance owners

| Blocker | Exit criterion | Suggested owner |
|---|---|---|
| Onboarding refresh defect | Browser follows exact job to terminal, reloads data, updates readiness and survives resume/retry | Core + UI |
| Mode-switch stuck state | Every admission/retry/terminal path ends in stable effective mode or explicit recoverable failure | Fulfillment |
| Sales metric ambiguity | Signed metric dictionary; refund/review policy implemented; KPI/drill-down reconciliation green | Sale + product owner |
| No exact-head native runtime | Exact SHA passes Odoo.sh install/update/migration/browser/process-boundary evidence | Release engineering |
| No Shopify-side proof | Controlled store campaign verifies product, inventory, order evidence and fulfillment outcomes | Integration QA |
| Remote acknowledgement ambiguity | Status ladder and verification policy implemented for each write domain | Core + domain owners |
| Supported lifecycle unclear | Public capability matrix distinguishes supported, review-only and deferred flows | Product + QA |


# 13. Final control-room decision

Do not authorize a full backend rewrite. Do not authorize release or merge on visual/UI evidence alone. Authorize a bounded correctness phase that:

1. repairs onboarding refresh, Mode 2 transition recovery and sales metric definitions;

2. adds consistent business-read admission and Accepted/Verified status semantics;

3. freezes a field-level source-of-truth and supported-lifecycle contract;

4. executes exact-head Odoo.sh, controlled Shopify, multi-store and business-reconciliation gates;

5. then rebuilds the approved operator shell without weakening the preserved integrity substrate.

Audit status: FUNCTIONAL CORRECTNESS AND DATA INTEGRITY AUDIT COMPLETE — RELEASE NOT CERTIFIED — CORRECTNESS REMEDIATION AND EXACT-HEAD ACCEPTANCE REQUIRED.


# Source register

1. PR #204, governed candidate and stated qualification boundary.

2. Exact-head commit.

3. Exact-head GitHub Actions run 30715082576.

4. Core store model.

5. Core API client.

6. Setup wizard client.

7. Order importer.

8. Current sales projection.

9. Fulfillment scans and mode switching.

10. Shopify inventorySetQuantities, 2026-07.

11. Shopify productSet.

12. Shopify fulfillmentCreate.

13. Shopify webhook behavior.

14. Shopify webhook delivery verification.

15. Odoo 19 testing reference.
