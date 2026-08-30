# V2 Test, Observability and Release Blueprint

> **Status:** release-gate contract. Tests prove safety and operability, not only line execution.

## 1. Quality strategy

The V2 test pyramid has five mandatory proof classes:

1. pure policy and contract correctness;
2. Odoo persistence/security/lifecycle behavior;
3. concurrency and remote side-effect safety;
4. complete user journeys and visual/accessibility behavior;
5. production-shaped performance, observability and rollback.

A green unit suite cannot compensate for a missing mutation, migration or permission proof.

## 2. Test data profiles

All data is synthetic or anonymized through an approved process. No merchant credential or copied customer PII enters fixtures.

| Profile | Stores/companies | Business volume | Runtime evidence | Where used |
| --- | --- | --- | --- | --- |
| Tiny | 1 / 1 | 10 products, 10 orders, 20 inventory pairs, 5 fulfillments | 100 jobs/logs, 20 webhooks | fast unit/ORM/tour fixtures |
| CI target | 5 / 3 | 5,000 variants, 2,500 orders, 20,000 inventory pairs, 1,000 fulfillments | 50,000 jobs, 150,000 logs, 25,000 webhooks | query, migration and concurrency CI |
| Nightly target | 10 / 3 | 50,000 variants, 25,000 orders, 200,000 inventory pairs, 10,000 fulfillments | 250,000 jobs, 750,000 logs, 200,000 webhooks | performance/lifecycle nightly |
| Pre-release stress | 20 / 5 | 100,000 variants, 100,000 orders, 500,000 inventory pairs, 25,000 fulfillments | 1,000,000 jobs, 3,000,000 logs, 500,000 webhooks | release-candidate qualification |

Stage 0 records environment CPU/RAM/PostgreSQL/Odoo worker configuration with every result. Absolute timings without the environment are invalid evidence.

## 3. Required CI lanes

### Lane A — Fast static and policy

- Python syntax/import checks;
- JavaScript/Owl lint and unit tests;
- XML/CSV/manifest validation;
- dependency-boundary and cycle check;
- GraphQL operation/fixture validation;
- pure policy, state-transition, fingerprint and retry tests;
- secret/PII pattern scan on changed files and test output.

Target: under 10 minutes; required on every PR.

### Lane B — Odoo unit/integration

- current repository connector suite through `tools/run_connector_suite.sh`;
- ORM constraints, service-only writes and transitions;
- ACLs, global record rules, active-company and same-store constraints;
- command/query facade tests;
- domain import/export/inventory/fulfillment behavior;
- webhook ingestion/dispatch and readiness;
- cron/drain/stale-owner behavior.

Required on every implementation PR touching backend behavior.

### Lane C — Lifecycle

- fresh install;
- warm `-u` upgrade from the exact supported release fixture;
- migration interruption/resume;
- domain uninstall/reinstall with history;
- complete addon-family install order;
- schema/constraint/XML-ID compatibility diff.

Required for manifest, model, security, data, migration or addon-dependency changes. Full matrix runs nightly and before release.

### Lane D — Browser and accessibility

- Owl/HOOT component tests;
- HttpCase tours for core journeys and roles;
- axe-compatible automated checks or equivalent rule engine;
- keyboard/focus/reduced-motion tests;
- screenshot regression at 375, 768, 1366, 1440 and one RTL locale;
- no console errors, unhandled rejections or page-level horizontal overflow.

Required for JS/XML/SCSS/view changes; full role matrix before release.

### Lane E — Concurrency and mutation safety

- deterministic multi-worker/transaction tests;
- worker kill and stale-owner recovery;
- webhook/cron/user race;
- timeout/fault injection before DNS/connect/send, during send and after remote commit;
- exact readback applied/not-applied/inconclusive paths;
- idempotency validity-window and operation-scope contention;
- no remote duplicate assertions in the fake Shopify ledger.

Required for runtime, gateway, webhook and mutation-domain PRs.

### Lane F — Performance and soak

- target/stress profile query counts and timings;
- API requested/actual cost and pagination bounds;
- drain throughput, queue age, memory growth and lock contention;
- webhook acknowledgement under concurrent load;
- migration/backfill duration and lock observation;
- 30–60 minute steady-state synthetic soak;
- canary telemetry from the staged release.

Nightly and release-gate; a bounded microbenchmark accompanies relevant PRs.

## 4. Behavior test matrix

### 4.1 Commands and state

For every command test:

- correct role and active company;
- wrong role, inactive company, wrong store/company pair;
- current/stale generation;
- ready/not ready/paused/disconnected store;
- first submission, duplicate `command_id`, concurrent duplicate;
- valid/invalid/overlong payload and unexpected fields;
- allowed/disallowed state transition;
- resulting run/job/log/audit evidence;
- redacted public problem shape.

Every state transition table is parameterized from the production vocabulary so tests fail when values drift.

### 4.2 Bindings and matching

- remote GID existing binding always wins;
- per-store remote and Odoo uniqueness under concurrent create;
- SKU/barcode/reference deterministic candidates;
- duplicate/ambiguous key routes to review;
- names/fuzzy similarity never auto-bind;
- manual override role/reason/audit and same-company/store checks;
- deleted/stale Odoo record behavior;
- PII masking does not alter binding identity.

### 4.3 Product import/export

- pagination, overlap/checkpoint and page rollback;
- optional/missing Shopify fields;
- field-level authority combinations;
- protected field exclusion;
- preview fingerprint deterministic/stale/change detection;
- partial Shopify `userErrors` and top-level errors;
- create/update duplicate risk;
- uncertain mutation readback by canonical GID.

### 4.4 Orders/customers

- existing order/customer binding idempotency;
- guest/no-email/customer ambiguity;
- tax, discount, shipping, tip, presentment currency and total evidence;
- financial/fulfillment status refresh without silent Odoo operational rewrite;
- line-composition/total mismatch review;
- manual gateway/COD decision paths;
- reconnect/re-evaluate while preserving Odoo side effects.

### 4.5 Inventory

- exact one-to-one location mapping and cross-store rejection;
- first push blocked for missing observation/mapping/confirmation;
- preview current Shopify/Odoo/delta and fingerprint;
- rapid Odoo stock changes coalesce safely;
- item/location operation-scope contention;
- partial batch response and cost throttling;
- timeout after send, readback applied/not-applied/inconclusive;
- mapping change invalidates pending preview;
- no blind initial overwrite.

### 4.6 Fulfillment

- eligible FulfillmentOrder/location/line selection;
- full and partial picking intent where supported;
- one fulfillment per picking/binding uniqueness;
- tracking create/update and no-op;
- explicit `notifyCustomer` effective value;
- response interruption after remote commit;
- worker death before/after send;
- webhook arrives before/after readback;
- inconclusive cap routes to manual review;
- no duplicate fulfillment or duplicate notification.

### 4.7 Webhooks

- valid/invalid/missing HMAC on exact raw bytes;
- unknown/wrong shop, topic and API version;
- oversized/malformed payload after verification;
- delivery duplicate with same and conflicting digest/topic;
- event/source timestamps including nanosecond RFC 3339 input;
- minimal allowlisted identity only; no raw body persistence;
- fast acknowledgement while domain handler is slow/failing;
- duplicate/out-of-order/missed event reconciliation;
- retention cutoff and 2,000-row bounded cleanup.
- deterministic desired/current subscription diff and connector ownership;
- create/delete duplicate, timeout-before/after-send and list-readback verification;
- unrecognized/external subscriptions are never deleted by name or callback guess;
- missing scope/callback drift readiness and failback with current subscriptions intact.

## 5. Security verification

### 5.1 Automated authorization matrix

For Auditor, User/Operator, Reviewer, Administrator and no-access, verify model read/write/create/unlink, every public facade method and every button action. Explicitly test direct RPC calls even when the UI hides the action.

### 5.2 Multi-company/store probes

- one user allowed companies A/B but only A active;
- two stores in one company;
- null-company historic store;
- quarantined cross-store child row;
- forged related record from another store;
- counts/aggregates/search suggestions as well as record reads;
- company switch while a V2 screen/command is open.

### 5.3 Secret and injection probes

- token fragments in exception, log, payload, notification and browser network response;
- email/phone in manual reasons and technical details;
- GraphQL variable injection and malformed GID/domain;
- arbitrary model/method/ref injection;
- unsafe SQL/domain construction;
- overlong/recursive JSON and decompression/body size attacks;
- webhook timing comparison and replay.

Release output must contain zero high/critical findings and zero known secret/tenant leaks.

## 6. Frontend journey tests

### Journey U1 — First setup

Create draft store → save credential → test connection/scopes → configure workflows/authority/defaults → map locations → see grouped readiness → activate. Cover invalid token, missing scope, save/resume, stale generation and keyboard-only completion.

### Journey U2 — Daily operation

Open Overview → identify highest-impact issue within 10 seconds → open filtered attention item → inspect evidence/impact/consequence → resolve → follow resulting run → return to affected record.

### Journey U3 — Safe inventory first push

Map location → preview current/proposed values → verify Odoo authority → confirm as Administrator → observe run/result. Prove Operator cannot bypass confirmation and changed mapping/quantity invalidates preview.

### Journey U4 — Ambiguous product match

Open match evidence → compare deterministic candidates → select/bind or leave for review → provide reason when required → resume held job → verify audit.

### Journey U5 — Uncertain fulfillment

Validate picking → observe `Verifying Shopify` after interrupted response → confirm resubmit disabled → readback resolves → timeline shows accepted/verified distinction and notification value.

### Journey U6 — Permissions

Exercise menus, counts, direct URLs/RPC and actions for each role/company. No-access user sees no connector records or counter leakage.

Moderated usability acceptance:

- 5 representative participants per primary role group for pre-release validation;
- ≥90% unaided completion for setup, attention resolution and run investigation;
- median ≤10 seconds to identify the top blocked workflow from Overview;
- zero participant executes an unintended remote write in the test script;
- every repeated confusion is triaged before release, not dismissed as training.

## 7. Performance budgets

Stage 0 records exact baselines; each relevant PR commits before/after evidence. The following are hard initial ceilings unless the baseline is stricter:

| Operation | Budget |
| --- | --- |
| Overview initial read, CI target profile | p95 ≤ 800 ms server time, ≤20 SQL queries, one RPC |
| Attention search first page (80 rows) | p95 ≤ 700 ms, ≤15 SQL queries |
| Attention detail | p95 ≤ 500 ms, ≤12 SQL queries |
| Run detail (200 timeline events) | p95 ≤ 700 ms, ≤18 SQL queries |
| Setup read/save non-remote step | p95 ≤ 500 ms, ≤15 SQL queries |
| Interactive command admission | p95 < 3 s excluding asynchronous work |
| Webhook acknowledgement | p95 < 2 s, p99 < 4 s |
| Drain claim transaction | p95 ≤ 250 ms for configured batch |
| Browser largest composed view | no page-level overflow; usable interaction ≤2.5 s on test profile |

Additional gates:

- no query count growth with row count for a fixed page size;
- changed workflow API requested cost ≤ baseline +10% unless an approved capability requires more;
- p95 latency/queue age/memory ≤ baseline +10% at comparable load;
- migration lock that blocks ordinary connector writes >2 seconds requires a maintenance-window plan;
- memory has no monotonic growth across the steady-state soak beyond runtime warm-up tolerance recorded in Stage 0.

If a hard ceiling is impossible on the measured environment, the PR stops and records evidence; it does not silently relax the value.

## 8. Service-level objectives and indicators

### 8.1 Pilot SLOs

| SLI | Pilot objective |
| --- | --- |
| Webhook acknowledgement | 99.5% under 2 seconds over 7 days |
| Interactive admission | 99% under 3 seconds over 7 days |
| Scheduled read jobs | 99% reach terminal/attention within configured schedule + 15 minutes |
| Actionable outcome quality | 100% terminal/manual-review outcomes expose action or explicit no-safe-action |
| Mutation certainty | 100% possible-after-send failures enter verification; zero blind replay |
| Tenant isolation | zero cross-company/store processing or disclosure |
| Binding integrity | zero duplicate/corrupted binding identity |
| Freshness | per-workflow configured target shown honestly; 99% within target in pilot |

Volume/merchant commitments are not marketed until pilot evidence supports them.

### 8.2 Required metrics

Dimensions are bounded to store ID, workflow, operation, lane, outcome and error class; never remote GID, email or unbounded correlation ID labels.

- run/job/attempt counts and duration histograms;
- admission-to-start and end-to-end latency;
- queue depth/oldest age by lane;
- retries, manual review and terminal failure rate;
- uncertain mutations and verification time/result;
- duplicate admission and operation-scope conflicts;
- Shopify requested/actual cost, available budget and throttle delay;
- webhook acknowledgement, duplicate/conflict/ignored rate;
- reconciliation drift and repair outcomes;
- freshness by store/workflow;
- read-model server duration/query count/row count;
- stale-owner recovery and claim contention;
- migration/backfill progress.

### 8.3 Structured log fields

Every runtime observation uses:

`timestamp`, `level`, `event_code`, `correlation_id`, `run_ref`, `job_id`, `attempt_id`, `store_id`, `company_id`, `workflow`, `operation`, `outcome`, `error_class`, `safe_message`.

Never log credentials, authorization headers, raw GraphQL variables/responses, raw webhooks, unredacted manual reasons or customer identity. Remote request IDs are allowed as values, not metric labels.

## 9. Alerts and operator runbooks

| Alert | Trigger | Immediate response |
| --- | --- | --- |
| Safety invariant | any duplicate suspicion, blind replay, tenant leak, generation bypass | halt V2 admission; preserve evidence; execute verification/incident runbook |
| Uncertain mutation backlog | oldest >10 min or count above 5 per store | prioritize safety-verification lane; inspect Shopify/readback health |
| Webhook acknowledgement | p95 >2 s for 15 min | isolate ingestion transaction/DB pressure; keep domain work out of request |
| Queue age | oldest interactive >5 min or scheduled >target+15 min | inspect claims, throttle, worker/cron health |
| API budget | throttle delay or requested cost >20% baseline for two windows | lower bounded concurrency/page size; inspect operation change |
| Read-model regression | budget breach for two windows | disable V2 UI for affected stores; inspect query plan/N+1 |
| Reconciliation drift | unexplained drift above domain threshold | stop mutation expansion; compare webhooks/checkpoints/authority |
| Stale owners | any repeated stale recovery for same job | quarantine job; verify mutation certainty; inspect worker lifecycle |

Each alert links to a checked-in runbook containing query steps, allowed actions, forbidden actions, evidence to capture and closure criteria.

## 10. Coverage and mutation-quality rules

- Changed pure domain/application lines: ≥90% statement and ≥85% branch coverage.
- Security, legal state-transition, idempotency, operation-scope and mutation-certainty decision branches: 100% enumerated behavior coverage.
- Coverage cannot be raised with tests that only execute a branch without asserting state/evidence/side-effect count.
- A fake Shopify ledger records every simulated mutation and supports exactly-once assertions.
- At least one deliberate test mutation (or equivalent fault seeding) must prove critical tests fail when blind retry, missing generation check or binding uniqueness is removed.

Coverage thresholds supplement, not replace, the behavior matrix.

## 11. Release qualification

### 11.1 Candidate freeze

- exact Git SHA, Odoo pin, addon versions and Shopify API version recorded;
- no uncommitted/untracked production files;
- all required CI lanes green on the exact SHA;
- build artifacts identify the same SHA and dependency lock state;
- no release qualification modifies the candidate.

### 11.2 Environment sequence

1. local/CI synthetic qualification;
2. isolated Odoo test database + isolated Shopify test store;
3. development deployment exact-SHA verification;
4. controlled pilot cohort;
5. broad cohorts according to `08-migration-and-cutover-blueprint.md`;
6. production default only after gate approval.

No staging/production mutation is used to “see if it works” without the approved cohort and rollback plan.

### 11.3 Release evidence bundle

```text
docs/v2/evidence/releases/<candidate-sha>/
├── manifest.json
├── ci-matrix.md
├── lifecycle-matrix.md
├── contract-results.md
├── concurrency-and-faults.md
├── security-and-privacy.md
├── performance.md
├── accessibility-and-visual.md
├── uat.md
├── migration-and-rollback.md
└── verdict.md
```

`verdict.md` is written by a reviewer who did not author the last material code change where team size permits. It states release-ready, conditional or rejected and links every exception.

## 12. Severity and release policy

| Severity | Examples | Release treatment |
| --- | --- | --- |
| S1 | tenant/secret leak, data loss/corruption, duplicate irreversible mutation | freeze all expansion/release; incident and independent requalification |
| S2 | wrong authority/mapping/total, blocked recovery, install/upgrade failure | no release; fix and rerun affected + full release gates |
| S3 | degraded workflow with safe workaround, material accessibility failure | fix before default rollout; pilot exception requires explicit owner/expiry |
| S4 | cosmetic/nonblocking issue | may defer with issue, owner and date; no safety/a11y misclassification |

There are no accepted known S1/S2 defects at release. S3 exceptions cannot affect remote-write clarity, keyboard completion or role isolation.

## 13. Definition of release ready

V2 is release-ready only when:

- all compatibility/migration invariants pass on the exact release candidate;
- all required CI lanes and complete release matrix pass;
- no S1/S2 and no unowned S3 defect remains;
- performance budgets and pilot SLOs are met;
- exact UAT journeys pass on the supported environment;
- accessibility/RTL/responsive/role checks pass;
- every in-flight/uncertain mutation can be explained and resolved;
- backup, restore, halt and rollback drills are evidenced;
- feature modes, canary cohort and contraction timing are recorded;
- release notes explain behavior/migration without overstating “real-time” or exactly-once guarantees.

## 14. Official references

- [Odoo 19 testing](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html)
- [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html)
- [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- [Shopify API limits](https://shopify.dev/docs/api/usage/limits)
- [Shopify webhook guidance](https://shopify.dev/docs/apps/build/webhooks)
