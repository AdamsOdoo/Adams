# V2 Implementation Roadmap

> **Status:** continuous five-wave execution plan.  
> **Rule:** P00–P20 are bounded traceability/work-item IDs, not 21 phases, approval requests or mandatory PRs. After implementation authorization, execute Waves 1–5 continuously on one integration branch and present one qualified candidate PR with coherent reviewable commits.  
> **Starting point:** create the implementation branch from the then-current accepted `Shopify-connector` head—not from this docs branch and not from release PR #210 unless that exact head has become the accepted baseline.

## 1. Continuous five-wave program

| Wave | Internal work items | Outcome and automatic gate |
| --- | --- | --- |
| W1 — Baseline and contracts | P00–P02 | V1 behavior/recovery evidence, dependency rules and versioned read/command contracts are reproducible; no production behavior changes |
| W2 — Shared backend foundation | P05–P10 plus the backend portion of P15 | Shopify boundary, durable runtime, security, multistore/settings/readiness, migrations, restart and measured performance are green before production UI wiring |
| W3 — Domain reliability | P11–P14 | subscriptions, inventory, product export and fulfillment use the proven runtime with domain-specific uncertainty/readback tests |
| W4 — Complete product experience | P03, P04 and the UI portion of P16 | Odoo-native shell, setup, store administration, Overview, Attention, Runs and all domain/contextual screens implement the locked contracts |
| W5 — Exact-candidate qualification and rollout | P17–P18 | U1–U14, lifecycle, security, accessibility, performance, live test-store UAT and staged deployment gates pass on one exact SHA |

P19 contraction and P20 optional packaging consolidation are post-release maintenance; they are not required to deliver V2. Within W1–W5, a green evidence gate advances automatically. An ordinary failing test is fixed and rerun; it is not a request for renewed user permission. Pause only on the stop conditions in `CLAUDE.md` and `13-continuous-execution-handoff.md`.

The work remains reviewable through coherent commits tagged with one or more P IDs. P IDs may be combined when they share the same dependency boundary and test gate; they must be split when combining them would mix a remote mutation with an uncharacterized policy/schema change.

## 2. Universal implementation-checkpoint contract

Every coherent implementation checkpoint must record:

- one-sentence user/engineering outcome;
- exact base/head SHA and dependency packet;
- allowed and forbidden file list;
- compatibility invariants affected;
- characterization test added before extraction;
- behavior, security, lifecycle and performance evidence required by the slice;
- fault/rollback statement;
- docs/evidence/traceability update and active-wave handoff state;
- no unrelated formatting or cleanup;
- a removal issue for every migration flag/facade introduced.

Dependency order is authoritative even when work is locally parallelized. Non-overlapping contract-fixture/prototype work may branch after the same stable seam, but all work is reconciled onto the integration branch and the affected gates rerun before the next wave. No work continues on a stale internal API.

## 3. Packet index

| Packet | Outcome | Remote writes | Primary risk |
| --- | --- | --- | --- |
| P00 | Reproducible V1 baseline and restore proof | none | missing characterization |
| P01 | Enforced packages, vocabularies and public contracts | none | premature behavior change |
| P02 | V2 read DTOs over legacy records | none | incorrect aggregation/tenant leak |
| P03 | V2 shell and Overview | none | Odoo-shell/contract drift |
| P04 | Attention and Run evidence experience | none | unsafe action exposure |
| P05 | Shopify compatibility facade and transport foundation | none | response/error drift |
| P06 | Core/product/sale read gateway extraction | none | pagination/checkpoint drift |
| P07 | Inventory/fulfillment/webhook read extraction | none | domain read semantics |
| P08 | Mutation gateway extraction under legacy runtime | existing legacy path only | changed write payload/normalization |
| P09 | Additive run/attempt schema and mode controls | none | upgrade/lifecycle |
| P10 | V2 coordinator for read-only work | none | concurrency/checkpoints |
| P11 | Webhook-subscription desired-state cutover | yes, scoped admin writes | lost/duplicate subscription |
| P12 | Inventory mutation V2 canary | yes, scoped | blind overwrite/duplicate |
| P13 | Product-export mutation V2 canary | yes, scoped | authority/stale preview |
| P14 | Fulfillment mutation V2 canary | yes, scoped | duplicate shipment/notification |
| P15 | Store lifecycle/settings/multistore/readiness backend | diagnostic only | credential/readiness/tenant bypass |
| P16 | Complete setup/admin/domain UX and evidence panels | uses approved commands | UI authorization/state gaps |
| P17 | Security/performance/accessibility/release closure | controlled test | qualification gaps |
| P18 | Cohort rollout and default V2 mode | controlled production cohorts | operational regression |
| P19 | Remove compatibility paths/migration flags | no new behavior | premature contraction |
| P20 | Optional webhook addon consolidation | no semantic change | install/uninstall/XML-ID breakage |

## 4. Detailed packets

### P00 — Baseline, characterization and recovery evidence

**Depends on:** architecture/product gate approval.  
**Outcome:** V1 behavior, compatibility surface, performance and database restore are reproducible.

Changes:

- generate the six evidence files listed in `08-migration-and-cutover-blueprint.md`;
- add bounded tools/tests to inventory models, fields, XML IDs, constraints, imports and Shopify operations;
- add golden fixtures around API client, store, credential, setup, dispatch and each large domain service;
- capture Tiny/CI-target baseline; schedule nightly/stress generation separately;
- prove backup/restore and fresh/warm lifecycle on an isolated database.

Allowed:

- `docs/v2/evidence/**`, `docs/v2/**` status/traceability;
- test fixtures/tests and non-production analysis tools;
- CI wiring needed to run those checks.

Forbidden:

- production addon behavior/schema/view/security changes;
- test weakening, skipped existing suite or generated merchant data.

Acceptance:

- compatibility inventory is deterministic across two clean runs;
- golden tests fail when a selected current invariant is deliberately perturbed;
- restore integrity matches row counts, sampled identities and constraints;
- exact commands/environment/SHA are recorded.

Rollback: remove analysis-only additions; no database/product change.

### P01 — Contracts and dependency skeleton

**Depends on:** P00.  
**Outcome:** target package boundaries and state/DTO contracts exist without changing execution.

Changes:

- add `application`, `domain`, `integration/shopify` and `runtime` package skeletons;
- add immutable command/result, normalized error/state and DTO dataclasses;
- add dependency rule checker and handler/attention/operation registry primitives;
- add `shopify.connector.ui.facade` and application facade with no-op/legacy-delegating explicit methods behind tests;
- document/import only stable public contracts.

Allowed:

- new core packages, minimal `__init__.py` wiring, facade AbstractModels;
- pure unit/contract tests and boundary CI.

Forbidden:

- moving existing logic, schema changes, new menus/assets, remote request changes;
- generic arbitrary command/model dispatch.

Acceptance:

- dependency checker catches reverse-import fixture;
- duplicate registry keys/unknown operations fail closed;
- all current tests pass unchanged;
- production request count/payload is identical.

Rollback: remove inert packages/facades.

### P02 — Overview, Attention and Run read models

**Depends on:** P01.  
**Outcome:** complete V2 read contracts project existing execution safely.

Changes:

- implement `get_overview_v1`, attention search/detail providers and `get_run_v1` for `job:<id>`;
- add provider adapters for manual-review jobs, mutation uncertainty, product match decisions, missing inventory mappings and readiness failures;
- add common envelope, freshness and allowed-action projection;
- add query instrumentation and budgets.

Allowed:

- core query/application packages and UI facade;
- small read-only provider modules in owning domain addons;
- tests/evidence.

Forbidden:

- persistent attention/run schema, remote calls from read DTOs, job transitions;
- `sudo()` to make aggregate counts work; raw stack traces/PII.

Acceptance:

- seeded source states map to DTO golden fixtures;
- no count/ID leakage across roles/companies/stores;
- Overview ≤20 queries/800 ms on CI-target profile; no N+1 by page size;
- allowed actions match direct server authorization tests.

Rollback: leave legacy UI calling none of the new methods.

### P03 — V2 shell and Overview

**Depends on:** P02, P10 and the backend portion of P15; executes in W4.  
**Outcome:** the production Odoo surface matches the approved visual hierarchy using the proven backend and real DTOs.

Changes:

- add V2 menu/action context, store switcher, health band, workflow cards, attention preview and activity summary;
- add shared tokens/status/loading/empty/error components;
- use the final `v2_ui_mode` contract already introduced and migration-tested by the foundation;
- retain legacy technical menus for administrators.

Allowed:

- core `static/src`, views/actions/menus and UI field/security wiring;
- Owl/HOOT/tours/SCSS/evidence.

Forbidden:

- backend execution/gateway changes, mock production data, custom router/global store;
- replacing native product/order lists.

Acceptance:

- one initial RPC, all response states, role/store/company switches;
- keyboard/contrast/reduced-motion and 375/768/1366/1440/RTL screenshots;
- no console error/overflow; visual review against the live blueprint;
- `legacy` mode returns immediately to current navigation.

Rollback: set UI mode `legacy`; assets remain inert.

### P04 — Needs Attention and Run experience

**Depends on:** P03 and the qualified P10 runtime.  
**Outcome:** operators can resolve evidence-backed items and investigate runs without technical logs.

Changes:

- implement list/detail attention workspace and run timeline;
- implement explicit `resolve_attention_v1`, `retry_job_v1`, `cancel_job_v1` by delegating to accepted existing services;
- add stale `state_version`, reason/consequence/audit handling;
- add contextual links to Odoo records and restricted technical details.

Allowed:

- application recovery commands, provider resolution adapters, core UI/views/tests;
- no new business transition beyond existing accepted actions.

Forbidden:

- generic retry-all, new matching/authority algorithms, mutation replay;
- arbitrary polymorphic model access from client refs.

Acceptance:

- all attention providers/actions and stale/concurrent submits tested;
- direct RPC role/scope matrix passes;
- uncertain mutation shows verification and cannot retry;
- U3/U9/U10 read/recovery journeys pass with deterministic local/fake-ledger effects.

Rollback: UI mode legacy; explicit methods remain compatible delegates.

### P05 — Shopify transport/executor compatibility facade

**Depends on:** P02.  
**Outcome:** one typed Shopify boundary exists with zero domain behavior change.

Changes:

- place a facade in front of current API-client public calls;
- extract endpoint/version/header validation, HTTPS transport, response limits, GraphQL normalization, redaction and cost observations;
- keep every old model method signature as a delegate;
- add transport/executor contract fixtures and fault injection.

Allowed:

- core integration package, API-client compatibility edits, tools/redaction and tests;

Forbidden:

- domain query documents/call-site migration, mutation behavior, store/job schema;
- user-configurable API version, business conditionals in transport.

Acceptance:

- old/new facade outputs/errors identical for golden fixtures;
- served-version mismatch fails closed;
- variables/headers/logs pass secret probes;
- existing live request count/cost unchanged.

Rollback: old API client method bodies remain recoverable behind facade mode.

### P06 — Core, product and sale read gateways

**Depends on:** P05.  
**Outcome:** store/location/product/order/customer reads return normalized DTOs; importer behavior stays compatible.

Changes in order:

- capability/store identity and locations;
- product/variant reads and pagination;
- order/customer reads, checkpoint/overlap and commercial evidence;
- call-site migration one family at a time;
- deterministic `compare_reads` sampling and mismatch evidence.

Allowed:

- core/product/sale integration gateways and narrow importer compatibility changes;
- fixtures/tests/evidence.

Forbidden:

- writes, binding/matching/total policy changes, checkpoint schema changes;
- raw Shopify dictionaries beyond gateway.

Acceptance:

- zero unexplained normalized mismatch over full fixtures + 1,000 generated cases;
- pagination/checkpoints/optional fields/error/cost parity;
- importer characterization and performance budgets pass;
- hotspot files materially shrink or their gateway responsibility does.

Rollback: per-store gateway mode `legacy`; no data migration.

### P07 — Inventory, fulfillment and webhook-subscription read gateways

**Depends on:** P06.  
**Outcome:** remaining read families cross typed gateways with parity.

Allowed:

- core/inventory/fulfillment/webhook integration read modules and narrow delegates;
- contract/fault/performance tests.

Forbidden:

- quantity/fulfillment/subscription mutations; first-push/notification policy changes;
- webhook ingestion/dedup redesign.

Acceptance:

- inventory item/location, FulfillmentOrder/fulfillment and subscription desired/current facts match legacy normalization;
- cost/pagination and missing/stale resource behavior covered;
- no read leaks raw payload/PII;
- per-family legacy switch works.

Rollback: gateway mode `legacy`.

### P08 — Mutation gateway extraction under legacy runtime

**Depends on:** P07.  
**Outcome:** checked-in mutation operations and typed results exist, but the accepted legacy admission/runtime still controls when they execute.

Changes:

- extract inventory, product export, fulfillment and subscription mutation documents/variables/results;
- define exact domain readback methods/plans;
- route existing handler calls through compatibility gateways;
- compare canonical request variables and normalized responses in fixtures; never shadow live writes.

Allowed:

- integration mutation gateways, narrow legacy call-site delegates, tests/evidence.

Forbidden:

- new retry/cutover/runtime schema, changed authority/mapping/notification values;
- multiple mutation calls for comparison.

Acceptance:

- canonical variables match legacy for all fixtures;
- success/userErrors/top-level/timeout-before/after-send classifications pass;
- every mutation spec has a readback plan;
- fake Shopify ledger proves exactly one send per admitted job.

Rollback: route facade to legacy implementation; current job/mutation evidence remains.

### P09 — Additive run/attempt schema and migration controls

**Depends on:** P08.  
**Outcome:** target runtime records and store modes install/upgrade safely without changing execution.

Changes:

- add run and execution-attempt models, security/rules/views;
- add nullable job fields and indexes;
- add all three store settings modes exactly as specified;
- add migration/backfill framework and legacy run-ref compatibility;
- update uninstall historic evidence rules.

Allowed:

- core models/security/data/views/migrations/tests/evidence;
- no cron/dispatcher behavior change.

Forbidden:

- non-null big-table rewrite, fake mutation attempts, automatic remote work;
- removing/retyping current job states or fields.

Acceptance:

- complete fresh/warm/interrupted/resumed/lifecycle matrix;
- old runtime passes unchanged on expanded schema;
- same-store/company/service-write/append-only constraints pass;
- target/stress backfill meets lock/batch budgets.

Rollback: old compatible code on expanded schema; flags `legacy`.

### P10 — V2 coordinator and read-only runtime

**Depends on:** P09.  
**Outcome:** diagnostic/import/scan/reconciliation reads use runs, attempts, safe claims and priority lanes.

Changes:

- implement admission, coordinator, claimant, executor, observations, retry policy and read-only handlers;
- keep existing drain cron external ID/call seam;
- route only registered non-mutation job types when runtime mode is `read_only`;
- project new run/attempt evidence into V2 UI.

Allowed:

- core runtime/application/model delegates and read-only domain handlers;
- concurrency/fault/performance tests.

Forbidden:

- any mutation handler, new external queue/worker, removal of legacy dispatcher;
- network call inside claim transaction.

Acceptance:

- claim/kill/stale-owner/priority-aging/dependency/cancellation tests;
- checkpoint atomicity and no duplicate page effects;
- target throughput/cost/latency within budget;
- canary read-only mode and failback drill pass.

Rollback: stop admission, settle claims, mode `legacy`.

### P11 — Webhook-subscription desired-state cutover

**Depends on:** P10.  
**Outcome:** subscription create/delete reconciliation is the first V2-admin mutation, with exact desired/current readback and no change to webhook ingestion.

Changes:

- implement a desired-state planner from enabled topics, scopes and callback identity;
- register subscription create/delete handlers and exact list/readback verification;
- route only `v2_runtime_mode=subscriptions` pilot stores;
- preserve HMAC receiver, delivery dedup, payload-free envelope and satellite handler registration.

Allowed:

- webhook application/domain/runtime adapters, bounded core registration, readiness/subscription tests and evidence.

Forbidden:

- receiver/controller/delivery schema redesign, domain synchronization changes, satellite consolidation;
- deleting an unrecognized subscription without explicit ownership evidence.

Acceptance:

- desired/current diff is deterministic and scoped to connector-owned callback/topic identity;
- duplicate create/delete, timeout after send and list-readback paths pass in the fake ledger;
- missing scopes/callback mismatch block readiness with safe remediation;
- controlled test store converges twice from clean and drifted states;
- failback leaves current subscriptions intact and reconciliation explains every difference.

Rollback: stop V2 subscription admission; read back outstanding intent; set runtime mode `read_only`/`legacy`; do not mass-delete.

### P12 — Inventory mutation V2 vertical slice

**Depends on:** P11 and qualified P10 runtime evidence.  
**Outcome:** the first merchant-data V2 mutation proves admission → intent → send → readback → operator result.

Changes:

- implement inventory command/handler/verification and UI preview integration;
- retain bindings/location/first-push models and accepted quantity service semantics;
- cut over only `v2_runtime_mode=inventory` pilot stores (cumulatively includes subscriptions);
- add fake-ledger and controlled test-store UAT.

Allowed:

- inventory application/domain/runtime adapters, bounded core registration, UI preview/tests/evidence.

Forbidden:

- product/fulfillment mutation work, binding schema rewrite, blind first push;
- bulk retry of uncertain pairs.

Acceptance:

- complete Section 4.5 test matrix and all halt conditions;
- zero duplicate writes in fault/concurrency suite;
- fingerprint/mapping/generation/Administrator gates;
- test-store end-to-end and required soak/canary evidence.

Rollback: inventory admission off; readback in-flight intents; mode `subscriptions`/`read_only`/`legacy` as evidence permits.

### P13 — Product-export mutation V2 slice

**Depends on:** accepted P12 soak.  
**Outcome:** field-authority preview and catalog writes use the V2 runtime.

Allowed:

- product-export application/domain/runtime adapters, diff UI/tests/evidence;
- bounded core registration.

Forbidden:

- product import matching redesign, fulfillment changes, unsafe automatic creation;

Acceptance:

- field authority/protection/preview-stale/duplicate/readback matrix;
- one send per intent; no shadow writes;
- controlled UAT and product-export soak gate;
- legacy switch/reconciliation drill.

Rollback: product-export admission off; verify in-flight mutations; mode `inventory` or lower.

### P14 — Fulfillment mutation V2 slice

**Depends on:** accepted P13 and all lower-risk runtime evidence.  
**Outcome:** fulfillment create/tracking/notification uses the V2 runtime with strongest uncertainty gate.

Allowed:

- fulfillment application/domain/runtime adapters, timeline integration/tests/evidence;
- bounded core registration.

Forbidden:

- hidden/default notification at dispatch, broad picking logic redesign, inventory work;

Acceptance:

- complete Section 4.6 matrix, including worker death/webhook/readback races;
- no duplicate fulfillment/notification in fake ledger or controlled UAT;
- explicit notification evidence, 2,000 exact-candidate deterministic fault/load intents and seven-day canary gate;
- independent review of mutation/readback logic.

Rollback: block admission; verify every in-flight intent before legacy ownership resumes; mode `product_export` or lower.

### P15 — Store lifecycle, settings, multistore and readiness backend

**Depends on:** P10; the backend portion completes in W2 before production UI and may be extended only through registered domain contracts in W3.  
**Outcome:** concentrated store/setup orchestration becomes explicit commands/queries and the complete Administrator/multistore contract is proven.

Changes:

- extract store lifecycle, credential and readiness services behind stable model methods;
- implement store list/administration/settings/setup DTOs and writes, resumable progress and activation fingerprint;
- enforce canonical-domain identity, one effective settings record, multiple stores per company, company/store isolation and no designed store-count cap;
- register typed per-domain workflow/settings/readiness fragments and lifecycle actions;
- preserve credential storage, scopes, generation/disconnect behavior.

Allowed:

- core application/query/store/setup/credential/readiness services, migrations and tests;
- narrow domain readiness providers.

Forbidden:

- credential schema/lifecycle claims beyond current contract, remote business mutations;
- production setup/settings UI, giant settings form or client-side activation decision.

Acceptance:

- hotspot orchestration shrinks into cohesive services;
- secret/role/generation/readiness/fresh-warm/multistore tests;
- every Administrator setting default, validation, readiness impact and lifecycle transition in `07-data-and-api-contracts.md` passes direct-service and RPC authorization tests;
- foundation performance/isolation certificate includes the 5-store and 20-store profiles.

Rollback: legacy setup/lifecycle delegates; credential/data and store identities remain intact.

### P16 — Complete domain UX and contextual evidence

**Depends on:** P03, P04 and P11–P15; executes in W4 only after the backend foundation/domain gates are green.  
**Outcome:** onboarding, store administration, Products, Orders, Inventory and Fulfillment implement the full approved V2 experience.

Changes:

- native list/search/form fields and saved filters;
- six-step setup, Manage stores, grouped Settings and lifecycle/readiness surfaces over P15 contracts;
- contextual evidence panels/smart buttons;
- matching, product diff, location/first-push and fulfillment timeline focused components;
- final operation launcher over registered operation DTO;
- remove duplicate Sync/Error navigation from V2 mode only.

Allowed:

- domain views/static tests and read-query providers; bounded core shared components.

Forbidden:

- business/runtimes changes to fit visuals, recreating native Odoo primitives;
- hidden actions not backed by returned allowed-action contract.

Acceptance:

- all UX screen/response/accessibility/role contracts;
- U1–U12 browser journeys and moderated task measures; backend/fake-ledger assertions are not replaced by tours;
- query/RPC/visual budgets and no overflow/console errors;
- legacy technical evidence remains accessible to admins.

Rollback: `v2_ui_mode=legacy` independent of backend mode.

### P17 — Integrated hardening and exact-candidate qualification

**Depends on:** P16 and all W1–W4 gates.  
**Outcome:** one immutable candidate passes the complete security, lifecycle, performance, accessibility, recovery and UAT matrix.

Changes:

- no feature expansion;
- fix only evidence-proven release blockers in bounded commits on the integration branch, then freeze a new SHA and restart affected/downstream exact-candidate qualification;
- generate release evidence bundle and independent verdict;
- rehearse halt/rollback and database restore.

Allowed:

- tests/evidence/runbooks and narrowly proven fixes;

Forbidden:

- scope expansion, skipped/relaxed tests, candidate mutation during qualification;

Acceptance:

- the foundation certificate plus all of `09-test-observability-release-blueprint.md`, including U1–U14, on the exact SHA;
- zero S1/S2/unowned S3;
- release verdict accepted.

Rollback: candidate is not rolled out.

### P18 — Cohort rollout and default mode

**Depends on:** accepted exact candidate from P17.  
**Outcome:** V2 advances through defined cohorts with live telemetry and proven failback.

Changes:

- mode changes and release evidence only; a material defect returns to the integration branch, creates a new candidate SHA and reruns affected/downstream gates;
- cohort-by-cohort SLO/incident/rollback review;
- set `v2_ui_mode=default`, gateway/runtime modes to approved values only after all gates.

Forbidden:

- combining rollout with architecture cleanup or schema contraction.

Acceptance:

- every cohort meets minimum observation and zero halt condition;
- all eligible stores complete the streamlined cohort/domain gates in `08-migration-and-cutover-blueprint.md`; the 14-day all-V2 observation starts only the optional contraction clock;
- support/release notes and operator runbooks ready.

Rollback: per-store or global mode reversal using the migration runbook.

### P19 — Compatibility and flag contraction

**Depends on:** two successful connector release cycles and minimum 14 days at all-V2 after P18, explicit approval.  
**Outcome:** remove legacy internal paths and migration modes while retaining history/data contracts.

Changes:

- call/dependency/runtime evidence proves unused facades;
- remove one subsystem’s old path per coherent contraction checkpoint if needed;
- migrate modes to fixed V2/default and delete expired flags;
- keep stable public model/XML/data surfaces unless separately approved.

Forbidden:

- dropping binding/job/history tables, webhook packaging changes, unrelated cleanup.

Acceptance:

- complete suite/lifecycle/performance again;
- one supported path and no stale imports/config values;
- backup/restore/forward-fix plan.

### P20 — Optional webhook addon consolidation

**Depends on:** P19 and a separate ADR proving value.  
**Outcome:** domain topic registration may move into owning addons without changing ingestion, history or supported install combinations.

Changes:

- preserve/migrate XML IDs, data and historic job selection behavior;
- test every install/upgrade/uninstall/reinstall combination;
- generic HMAC/inbox/subscription core remains `shopify_connector_webhook`.

Forbidden:

- receiver/dedup/runtime semantic rewrite or one giant addon.

Acceptance:

- lifecycle matrix and database evidence show no orphan/lost history;
- addon count reduction has a measured maintenance benefit;
- if proof fails, keep satellites. P20 is not required for V2 release.

## 5. Parallelism and efficiency rules

Permitted after contracts stabilize:

- contract-fixture, static prototype and documentation work may proceed while W2 backend code is built, but production UI wiring waits for the full foundation certificate;
- independent domain gateway/handler tests may be developed against stable public ports with non-overlapping file ownership;
- long lifecycle/performance lanes run at wave gates while unaffected static/unit work continues on a separate checkpoint;
- a failing lane reruns the affected scope plus downstream dependencies instead of restarting every expensive lane after each small fix.

Not permitted:

- overlapping edits to shared runtime/store/security files by different owners;
- parallel mutation cutovers on the same store;
- runtime schema and first remote mutation in one uncharacterized checkpoint;
- gateway extraction combined with a business-authority change;
- production UI orchestration before W2/W3 backend contracts it consumes;
- packaging consolidation before post-release contraction.

## 6. Roadmap completion criteria

The implementation program is complete when one exact candidate has passed the foundation and U1–U14 qualification, P18 has made V2 the safe default through the defined cohorts, release evidence is immutable, and the continuous handoff has no unresolved blocker. P19 removes temporary complexity after soak. P20 is optional and cannot delay user value unless lifecycle evidence shows the current packaging itself is unsafe.
