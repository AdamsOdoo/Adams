# V2 Migration and Cutover Blueprint

> **Status:** executable migration strategy.  
> **Default:** coexistence and store-scoped cutover. No big-bang rewrite, forced reconnect or binding recreation.

## 1. Migration invariants

Every migration PR must prove all of the following:

- store IDs, canonical domains, company ownership and connection generations are unchanged;
- stable model names, tables and XML IDs remain resolvable;
- binding record IDs and all remote/Odoo uniqueness constraints remain intact;
- existing job, log, mutation, webhook and review evidence remains queryable;
- no credential value passes through a migration script, log, fixture or UI response;
- no migration performs Shopify writes;
- a warm upgrade can resume or safely quarantine pre-upgrade jobs without duplicate side effects;
- uninstall behavior of each installed addon combination remains intentional;
- downgrade means switching code paths, not reversing committed schema destructively.

Any violation stops the stage and invokes the deeper-replacement gate in `03-refactor-vs-replacement.md`.

## 2. Compatibility surface inventory

Stage 0 creates a machine-readable inventory and locks it in CI:

```text
docs/v2/evidence/
├── compatibility-baseline.json
├── database-profile.json
├── dependency-graph.json
├── performance-baseline.json
├── shopify-operation-inventory.json
└── ui-task-baseline.md
```

`compatibility-baseline.json` includes:

- addon technical names, versions and dependencies;
- model `_name`/`_table` and stored fields;
- XML IDs for menus/actions/views/groups/cron/config records;
- ACL and global record-rule IDs;
- SQL/ORM constraints and indexes;
- selection values referenced by installed rows;
- cron external IDs and call signatures;
- public model methods called across addons;
- import/dependency edges;
- uninstall hooks and historic-job sink behavior.

CI compares future branches and fails unexplained removals/renames.

## 3. Feature-control model

Add three Administrator-only, audited fields to `shopify.connector.store.settings`. They are migration controls and have removal issues from creation.

| Field | Values | Initial | Purpose |
| --- | --- | --- | --- |
| `v2_ui_mode` | `legacy`, `pilot`, `default` | `legacy` | selects V2 menus/composed surfaces while keeping technical legacy views |
| `v2_gateway_mode` | `legacy`, `compare_reads`, `v2` | `legacy` | selects Shopify gateway; compare mode never duplicates mutations |
| `v2_runtime_mode` | `legacy`, `read_only`, `subscriptions`, `inventory`, `product_export`, `fulfillment`, `all` | `legacy` | cumulative cutover ladder; each value includes the safer values to its left |

Rules:

- only Administrators can change them, through a named service method with reason;
- modes are store-scoped and checked at enqueue and execution;
- lowering a mode is always supported during coexistence;
- `compare_reads` executes the V2 read, then the legacy read or vice versa according to a deterministic sampling plan and compares normalized digests; it never shadows writes;
- a mode change increments/configures the relevant generation fence so admitted work cannot cross policies silently;
- flags have owners and expiry: removal begins after two successful connector release cycles and at least 14 calendar days at 100% V2, whichever is later.

## 4. Schema evolution protocol

All persistent changes use:

1. **Expand:** add nullable fields/tables/indexes; old code remains valid.
2. **Backfill/project:** bounded, restartable, idempotent batches with progress evidence.
3. **Dual-read:** V2 reads new representation with fallback and mismatch metrics.
4. **Dual-write where safe:** one transaction writes old and new local representations; there is never dual remote mutation.
5. **Switch:** store-scoped mode selects V2 behavior.
6. **Soak:** observe canaries and rollback ability.
7. **Contract:** remove old local code/columns only in a later release after backups and lifecycle proof.

Do not add a non-null column with a computed default to a large table in one blocking migration. Create nullable, backfill in bounded batches, validate, then add constraint in a later transaction/window.

## 5. Stage-by-stage cutover

### Stage M0 — Baseline and restore proof

Actions:

- freeze the exact supported V1 candidate and create anonymized production-shaped database copies;
- run fresh install, warm upgrade and installed-addon combination tests;
- capture row counts, largest tables/indexes, queue age, query/API cost and representative task timing;
- build golden behavior fixtures around hotspot services;
- take a database backup, restore it into an isolated environment, and run connector integrity checks;
- record the current Shopify API operation and scope inventory.

Exit gate:

- all evidence files exist and identify exact commit/database fixture hashes;
- restore produces matching store/binding/job counts and constraints;
- critical current behaviors have characterization tests;
- dependency cycles/private cross-addon imports are named;
- there is no unexplained difference between fresh and warm installation.

Rollback: no product behavior changed.

### Stage M1 — Read contracts over legacy execution

Actions:

- add the DTO/query packages and explicit UI facade methods;
- implement Overview, Attention and legacy run projections without new source-of-truth tables;
- return opaque `job:<id>` run refs;
- add query budgets and permission/count-leak tests;
- enable `v2_ui_mode=pilot` only for internal administrators.

Exit gate:

- all V2 read DTO fixtures pass;
- Overview equals source record facts for every seeded state;
- one initial RPC and no N+1 behavior at target fixture sizes;
- changing company/store cannot expose counts or IDs from another scope;
- turning the UI mode back to `legacy` is immediate and data-free.

Rollback: set `v2_ui_mode=legacy`; retain inert query code.

### Stage M2 — Shopify gateway extraction

Actions in operation-family order:

1. capability/store identity;
2. locations;
3. product/order/customer reads;
4. inventory reads;
5. fulfillment reads;
6. webhook subscription reads;
7. mutations only after read parity.

For each read family:

- place a compatibility facade at the old API-client method;
- define normalized request/result DTOs and checked-in GraphQL operation;
- run `compare_reads` on deterministic samples;
- compare normalized facts, pagination/checkpoints, errors and cost—not raw payload ordering;
- migrate call sites; then remove only that behavior from the hotspot.

Exit gate per family:

- zero unexplained semantic mismatch over 1,000 synthetic/recorded fixture cases and the complete edge-case suite;
- no API cost or latency regression above the approved baseline budget;
- served-version header and redaction tests pass;
- old facade remains switchable.

Mutation gateways are introduced but remain called by the legacy runtime until their M5–M8 cutover. There is never a shadow mutation.

Rollback: set `v2_gateway_mode=legacy`; no schema/data rollback.

### Stage M3 — Runtime schema expansion

Actions:

- add `shopify.connector.run` and `shopify.connector.job.attempt` tables;
- add nullable job linkage/lane fields and indexes concurrently/with Odoo-safe migration mechanics;
- create service-only ACL posture and global company rules;
- make new enqueue paths create a run plus jobs in one transaction while legacy jobs remain valid;
- backfill **projection rows only if required for reporting**; do not manufacture mutation evidence.

Legacy history policy:

- existing jobs remain canonical and render as `job:<id>`;
- do not create fake execution-attempt rows from logs unless the evidence unambiguously identifies an attempt;
- if a run backfill is needed, create one `legacy_projection` run per root job with request key `legacy-job:<id>`, retain original timestamps, and mark it projected;
- backfill batches are ordered by ID, capped, resumable and commit progress separately;
- counts and SHA-256 row-identity samples are checked before/after.

Exit gate:

- fresh/warm install and migration pass on small/target/stress fixtures;
- old code can run with new nullable schema;
- V2 DTO renders legacy and new refs identically at the contract level;
- kill/restart during backfill resumes without duplicates;
- mode remains `legacy` for execution.

Rollback: deploy old runtime-compatible code against expanded schema; do not drop new tables/columns.

### Stage M4 — Read-only runtime cutover

Actions:

- enable coordinator/claim/attempt execution for diagnostic, scan and reconciliation reads only;
- preserve current job states and existing drain cron external ID/call surface;
- add priority lanes/aging and attempt observations;
- canary `v2_runtime_mode=read_only` by store.

Exit gate:

- concurrency suite proves one claim and bounded stale-owner recovery;
- checkpoints never advance before committed page work;
- run/job/attempt projection is complete and redacted;
- throughput, queue age, query count, memory and Shopify cost stay within budget;
- failback to legacy drains or safely quarantines V2-owned claims without job loss.

Rollback: stop admission, wait for/resolve active claims, set mode `legacy`, resume legacy drain. Any uncertain state routes to review, never replay.

### Stage M5 — Webhook-subscription desired-state cutover

Subscription administration is first: it changes connector delivery configuration, not merchant business records, and exact desired/current state is list-readable.

Actions:

- compute a deterministic desired set from enabled topics, scopes and validated callback identity;
- manage only subscriptions proven owned by this connector/store/callback contract;
- create/delete through durable mutation intents and list-readback verification;
- preserve receiver, HMAC, delivery envelope/dedup and domain handler behavior;
- canary `v2_runtime_mode=subscriptions` by store.

Exit gate:

- repeated reconciliation converges without duplicate subscriptions;
- timeout-before/after-send and create/delete readback paths pass;
- unrecognized/external subscriptions are reported and never deleted heuristically;
- readiness explains scope/callback drift;
- test store converges from empty, correct, missing and extra-owned states.

Rollback: stop V2 subscription admission, read back outstanding intents and set mode `read_only`/`legacy`; preserve current subscriptions.

### Stage M6 — Inventory mutation cutover

Inventory is first because operation scope is naturally narrow and remote state is directly readable.

Actions:

- route preview/admission through V2 command handler;
- keep current first-push guard and bindings;
- send one bounded mutation request per proven batch contract;
- simulate all before-send/after-send failure points;
- resolve uncertainty by exact item/location readback.

Exit gate:

- zero duplicate writes across concurrency/worker-kill/network fault tests;
- no first push without mapping, current observation, fingerprint and Administrator confirmation;
- readback applied/not-applied/inconclusive paths are all proven;
- target store has at least seven continuous days or 10,000 mutation intents (whichever comes later) without a safety invariant violation.

Rollback: stop new V2 inventory admission; complete verification for in-flight mutation attempts; switch mode to `subscriptions`, `read_only` or `legacy` as evidence permits. Never undo a confirmed quantity automatically.

### Stage M7 — Product-export mutation cutover

Actions:

- route field-level diff/authority/validation through pure policy;
- bind confirmation to a canonical preview fingerprint;
- cut over by store after inventory soak;
- verify remote state by product/variant GID after uncertain responses.

Exit gate:

- protected fields never appear eligible;
- stale preview and changed authority fail closed;
- create/update idempotency, duplicate/binding risk and uncertainty tests pass;
- target store has seven continuous days or 5,000 catalog mutation intents (whichever comes later) without a safety violation.

Rollback: disable V2 export admission; verify in-flight writes; keep imported/bound records unchanged.

### Stage M8 — Fulfillment mutation cutover

This is last because duplicate fulfillment/customer notification has the highest irreversible risk.

Actions:

- route fulfillment-order selection, creation, tracking and notification through V2 handlers;
- require a registered exact readback plan for every mutation operation;
- make the effective notification value visible in preview/run evidence;
- canary individual stores only after inventory/product evidence is accepted.

Exit gate:

- duplicate creation and notification tests cover timeout before/after send, worker death and webhook/reconciliation races;
- no second mutation occurs while outcome is uncertain;
- fulfillment-order location/line eligibility tests pass;
- target store has 14 continuous days or 2,000 fulfillment mutation intents (whichever comes later) without a safety violation.

Rollback: block new V2 fulfillment admission; resolve every in-flight uncertain attempt; return future events to legacy only after operation-scope ownership is clear.

### Stage M9 — Store lifecycle and default V2 UI

Actions:

- replace setup orchestration behind stable store/setup methods;
- enable V2 Overview, Attention, Runs, setup and domain evidence surfaces for pilot roles;
- preserve technical legacy views for administrators during soak;
- set `v2_ui_mode=default` only after usability/accessibility/permission gates.

Exit gate:

- setup can be saved/resumed and cannot activate through failed/stale readiness;
- credential never returns to browser;
- task completion and error recovery meet UX acceptance measures;
- tours pass for Administrator, User/Operator, Reviewer, Auditor and no-access;
- responsive/RTL/keyboard/contrast checks pass.

Rollback: set `v2_ui_mode=legacy`; backend/runtime modes are independent.

### Stage M10 — Consolidation and contraction

Preconditions:

- 100% of supported stores on V2 for at least two connector release cycles and 14 days, whichever is longer;
- no open severity-1/2 V2 architecture defect;
- rollback drill performed within the prior release;
- migration/lifecycle matrix green;
- explicit approval recorded.

Actions:

- remove compatibility facades and migration flags one subsystem at a time;
- remove dead code only after call/dependency scans and runtime evidence;
- evaluate webhook satellite folding separately;
- drop obsolete columns/tables only in a later contract migration with backup/restore proof.

Rollback: code-level forward fix. A schema contract migration requires a separately tested restore plan and maintenance window.

## 6. Cutover cohorts

Use the smallest applicable cohort count; never fabricate percentages when only a few stores exist.

| Cohort | Membership | Minimum observation |
| --- | --- | --- |
| 0 — Test | isolated Shopify test store + disposable Odoo database | complete automated/UAT matrix |
| 1 — Internal pilot | 1 internal/noncritical real store | domain-specific soak gate |
| 2 — Controlled | next 1–3 stores, deliberately varied volume/workflow | 72 hours after last added store plus domain soak cumulative |
| 3 — Broad | 25% of eligible stores or next 5 stores, whichever is smaller | 7 days |
| 4 — Majority | 50% of eligible stores | 7 days |
| 5 — All | all eligible stores | 14 days before contraction clock starts |

A cohort does not advance on calendar alone; all gates and alert thresholds must stay green.

## 7. Automatic halt conditions

Immediately stop new V2 admission for the affected scope—and all stores if scope is uncertain—on any of:

- confirmed/suspected duplicate remote mutation;
- blind replay of an uncertain mutation;
- cross-company or cross-store data exposure/processing;
- credential/secret or unredacted PII exposure;
- binding identity/uniqueness corruption;
- store generation bypass;
- webhook HMAC/dedup bypass;
- served Shopify API-version mismatch treated as success;
- unexplained checkpoint advance after partial failure;
- one severity-1 data-integrity/security incident;
- p95 latency, queue age, error rate or API cost >20% worse than approved baseline for two consecutive 15-minute windows at comparable load.

The halt creates an audited incident/run note, freezes affected flags, preserves evidence and starts verification. It does not automatically retry or roll back remote effects.

## 8. Rollback runbook

For any subsystem:

1. identify affected stores/workflows and last safe timestamp;
2. stop new admissions through audited mode change;
3. list running/queued/uncertain work and operation-scope owners;
4. allow safe read-only jobs to finish; cancel only work not sent;
5. execute required readbacks for every possible remote mutation;
6. classify each intent applied/not-applied/review;
7. switch future work to the prior mode;
8. run reconciliation across an overlap window;
9. compare bindings/checkpoints/business records to pre-cutover evidence;
10. document cause, affected rows/remote IDs, decisions and follow-up before re-enabling.

Never restore a database over remote writes made after the backup without reconciliation; that can erase local evidence and cause duplicates.

## 9. Backfill implementation rules

- Use an Odoo migration script or explicit maintenance model with a stable progress key, not an HTTP request.
- Batch by immutable increasing ID; default batch 2,000 rows, adjustable downward after Stage 0 measurement.
- Each batch is idempotent and commits independently.
- Use `search` with indexed predicates; no offset pagination on growing tables.
- Record start/end ID, rows examined/changed/skipped, duration and digest sample.
- Do not call Shopify, send mail, trigger chatter or execute ordinary side-effecting model overrides.
- On mismatch, stop and preserve the batch; never “repair” identity heuristically.

## 10. Install/upgrade/uninstall matrix

At minimum test:

1. fresh core only;
2. core + each domain independently where dependencies permit;
3. complete addon family;
4. V1 database warm-upgraded to every migration checkpoint;
5. upgrade interrupted between batches and resumed;
6. uninstall each domain with historical jobs/bindings/evidence;
7. reinstall the domain and verify XML IDs/constraints;
8. uninstall webhook satellites before/after any approved consolidation;
9. disconnect/reconnect store before and after upgrade;
10. multi-company database with multiple stores per company and quarantined historic rows.

The core addon is not casually uninstalled in a migration test containing merchant evidence; its accepted uninstall hook/lifecycle contract governs the explicit destructive case.

## 11. Migration acceptance record

Every cutover PR includes:

- exact source/target commit and database fixture hash;
- schema/row-count/constraint diff;
- backfill progress and restart evidence;
- before/after performance and API-cost table;
- compatibility and lifecycle matrix results;
- faults injected and expected outcomes;
- canary store/workflow list without merchant secrets;
- halt/rollback rehearsal result;
- feature mode owner, current cohort and expiry/removal issue;
- signed reviewer decisions for security, data integrity, domain behavior and UX where applicable.
