# Wave 4 Gate A — Codex prompt review candidate

**Status:** CONTROL-ROOM RECONCILED — FINAL LOCKED GATE A PROMPT; ISSUED ONLY BY CHATGPT  
**Required base:** `mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`  
**Wave 4 control issue:** #186  
**Deferred critical validation:** #185 (`CV-013`)  

This is one complete, end-to-end Gate A prompt. It is deliberately phase-gated inside one Codex session so the worker can complete the full Definition-of-Ready package without drifting into implementation or producing shallow, contradictory outputs.

---

# GPT-5.6 SOL — WAVE 4 GATE A: FULFILLMENT DEFINITION OF READY AND LOCKED IMPLEMENTATION PACKAGE

**Codex effort:** High

## 1. Role, authority, and non-negotiable boundaries

You are GPT-5.6 Sol, the primary research, repository-audit, decision-reconciliation, and planning worker for Wave 4 Gate A.

Binding Wave 4 governance is recorded in issue #186 comment `5038326525`, which supersedes DEC-032 / issue #167 / `CLAUDE.md` only where those older records assign Claude sole control-room or sole merge authority. **ChatGPT is the strategic control room, scope governor, prompt-issuing authority, reviewer, acceptance authority, and merge-authorizing authority.** Claude is the independent reviewer and authorized runtime/governance worker when explicitly assigned; Claude may execute a merge only after explicit ChatGPT authorization. The product owner remains the ultimate business authority.

GitHub is the source of truth.

You must not:

- implement fulfillment production code;
- edit any file under `addons/**`;
- perform a Shopify mutation or use live Shopify credentials;
- start Wave 4 Gate B;
- start Wave 5;
- accept your own research, decisions, Definition of Ready, architecture, or implementation prompt;
- mark a pull request ready for review;
- merge a pull request;
- close or downgrade issue #185 (`CV-013`);
- silently broaden or reduce the accepted Wave 4 scope.

Your output is a **candidate Gate A package pending independent control-room acceptance**. Words such as “accepted,” “approved,” “final,” or “ready to implement” must not be used as self-authorization. The only permitted conclusion is either:

- `READY FOR CONTROL-ROOM GATE A REVIEW`; or
- `NOT READY — CONSOLIDATED DECISION BLOCKERS`.

## 2. Required execution environment

Run only in a genuine Codex coding workspace with:

- a real checkout of `AdamsOdoo/Adams`;
- local repository search and file-reading capability;
- local file-editing capability;
- local Git branch and commit capability;
- authenticated GitHub push and pull-request capability;
- internet access to current official Shopify and Odoo sources;
- access to the actual Odoo 19 source code used by the workspace or an authoritative Odoo 19 source checkout.

Stop immediately with one consolidated environment hard stop only when a missing capability prevents the Gate A objective.

The absence of Shopify credentials, a development store, or dedicated test fixtures is **not** a Gate A blocker because this session performs no live Shopify operation. Record issue #185 as the deferred critical live-validation obligation and continue.

## 3. Exact identity gate

Repository:

`AdamsOdoo/Adams`

Required integration branch:

`mvp/program-integration`

Required exact starting SHA:

`ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`

This is the merge commit for Task 013 / PR #182.

Before editing anything, verify and record:

1. `mvp/program-integration` resolves exactly to the required SHA;
2. PR #182 is merged and its merge commit is the required SHA;
3. issue #185 is open;
4. issue #186 is open;
5. protected references remain unchanged:
   - `checkpoint/core-r2-readonly-uat-2026-07-15`;
   - `Shopify-connector`;
   - `main`;
   - issue #165;
   - PR #150;
   - PR #151;
6. no already-authorized Wave 4 Gate A execution or implementation branch/PR exists; the prompt-review branch `control-room/wave-4-gate-a-prompt-review` and draft PR #187 are expected governance artifacts and are not competing execution work;
7. no `shopify_connector_fulfillment` addon exists at the required base;
8. the merged Layer 2, order, and inventory code expected from Waves 2 and 3 is present.

An unexpected integration SHA, protected-reference change, existing fulfillment implementation, or competing authorized Wave 4 branch is an identity hard stop. Do not rebase, merge, reset, or continue from an approximate base.

## 4. Branch, draft PR, and recovery model

After the identity gate passes, create:

`sol/wave-4-fulfillment-gate-a`

Base it directly on:

`ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`

Create the first documentation commit after Phase 1, then open an early draft PR into:

`mvp/program-integration`

Suggested PR title:

`Wave 4 Gate A: fulfillment Definition of Ready and Task 014 freeze`

The PR must remain open, draft, unmerged, and not marked ready.

Post the PR number and exact branch head to issue #186.

Maintain one durable session checkpoint file throughout the work:

`docs/07-implementation-plan/wave-4-gate-a-handoff.md`

At every phase boundary, update it with:

- exact branch and SHA;
- phase completed;
- files created or updated;
- verified facts;
- unresolved contradictions;
- decisions still requiring control-room review;
- next phase;
- any environment limitation.

At every phase boundary, commit and push the checkpoint and all coherent phase outputs before continuing.

Continue automatically from one phase to the next. Do not stop merely to ask permission between phases.

When an unavoidable context, time, or environment limit prevents completion, stop only at a phase boundary after committing and pushing the checkpoint. Report `PARTIAL GATE A — RESUME FROM PHASE <N>` and do not claim Gate A completeness.

## 5. One-session phase plan

Complete the following phases in order. Do not skip, merge, or reorder them.

### Phase 1 — Repository resource inventory and authority map

Locate, classify, and inventory all current and historical Task 014 / fulfillment records.

### Phase 2 — Current official Shopify and Odoo research

Verify version-sensitive fulfillment behavior from official sources and actual Odoo 19 source.

### Phase 3 — Actual merged-code integration audit

Trace the real seams in the merged connector and Odoo 19 code. Do not design from documents alone.

### Phase 4 — Decision and contradiction reconciliation

Build the complete decision matrix, preserve accepted rulings, and propose dispositions or explicit escalations.

### Phase 5 — Candidate Definition of Ready, architecture, and Task 014 packet

Freeze a candidate implementation contract pending control-room acceptance.

### Phase 6 — Exact file boundary, tests, runtime, dev-store, rollback, and locked implementation prompt

Prepare the complete future implementation and validation package. Do not issue it.

### Phase 7 — Adversarial review, corrections, trackers, and final handoff

Challenge the entire package, correct it coherently, update canonical trackers, and stop.

No phase authorizes fulfillment implementation.

### Depth priority — prevent shallow completion

When context or time pressure appears, preserve depth in this order:

1. decision-critical contracts: Odoo quantity semantics, line and location identity, Mode 1/Mode 2 rules, Layer 2 mutation/reconciliation, duplicate prevention, and security;
2. verified official/code evidence and contradiction resolution;
3. exact architecture, file boundary, and tests;
4. packaging, summaries, and presentation.

Never thin or guess a decision-critical contract merely to complete every document. Use the phase-boundary partial-completion path instead.

## 6. Binding Wave 4 product scope

Wave 4 delivers the complete fulfillment and tracking **backend**.

The accepted direction is:

- Shopify FulfillmentOrder surfaces only;
- Odoo delivery and tracking state mapped to Shopify through accepted FulfillmentOrder operations;
- both fulfillment Mode 1 and Mode 2 backend are mandatory;
- per-store `fulfillment_operating_mode`;
- the existing proposed 16-condition Mode 2 engine, which Gate A must validate, reconcile, and either preserve exactly or supersede through an explicitly accepted decision;
- mode-switch state machine;
- disconnected-period reconciliation;
- COD interplay;
- complete fulfillment-state taxonomy;
- durable Layer 2 mutation ownership;
- one mutation job to at most one mutation attempt for the job lifetime;
- idempotency, retries, replacement lineage, reconciliation, duplicate prevention, logs, and manual-review routing;
- readiness scope correction from the obsolete/general fulfillment scope concept to the exact current merchant-managed FulfillmentOrder scopes supported by official Shopify evidence;
- scheduled and manual backend admission where accepted;
- complete unit, concurrency, runtime, security, lifecycle, and dev-store validation contracts.

Wave 5 owns only the fulfillment mode UI. It does not own or defer either backend mode.

Issue #185 (`CV-013`) remains a mandatory carried-forward inventory live-validation gate. Missing Shopify access must not stop this Gate A session, but Wave 4 cannot receive final control-room acceptance, enter a release candidate, or proceed to UAT while #185 remains open.

## 7. Explicitly forbidden scope

Do not authorize or implement:

- legacy Shopify Order/Fulfillment API mutation paths;
- direct Shopify mutation outside the merged Stage 0 Layer 2 substrate;
- raw HTTP or GraphQL transport that bypasses the accepted API client and mutation wrapper;
- inventory-domain changes except a narrow, demonstrated fulfillment-location integration need separately identified for control-room approval;
- Task 013B;
- product or media export;
- Shopify-side returns or reverse-fulfillment synchronization; Odoo return pickings are researched only to define the safe forward-fulfillment boundary;
- refunds;
- payouts;
- advanced accounting automation;
- webhooks;
- OAuth;
- UI;
- SEC-2;
- analytics;
- Shopify Markets;
- subscriptions;
- gift cards;
- Shopify POS;
- B2B;
- metafields;
- multi-company complexity beyond current accepted company-consistency rules;
- broad multi-store orchestration;
- unrelated refactoring;
- live Shopify validation in Gate A.

Do not treat an attractive adjacent feature as necessary Wave 4 scope without an accepted repository source.

## 8. Evidence and source discipline

Separate every statement into one of these categories:

- verified repository fact;
- verified code behavior;
- official Shopify claim;
- official Odoo claim;
- accepted prior decision;
- inference;
- recommendation;
- proposed decision;
- unresolved question;
- risk;
- required evidence.

### Shopify source rules

Use current official Shopify documentation only for Shopify API claims.

For each version-sensitive claim, record:

- official document title;
- official URL;
- access date;
- Admin API version;
- claim supported;
- implementation implication;
- uncertainty or inaccessible-source note.

Do not use blog posts, community answers, old cached text, or model memory as proof.

### Odoo source rules

Use official Odoo 19 documentation and actual Odoo 19 source code.

For each important Odoo behavior, state whether it is:

- officially documented;
- verified in Odoo 19 source;
- inferred from current connector code;
- a connector recommendation.

Do not use Odoo 17 or 18 behavior as proof of Odoo 19 behavior.

### Repository claim rules

Every material code claim must identify:

- file path;
- model/class/function/symbol;
- relevant line range or stable code reference;
- implication for fulfillment.

When a source is inaccessible, say so clearly. Do not invent the missing fact. Record the exact impact and whether it blocks a decision.

## 9. Phase 1 — Repository resource inventory and authority map

Search the repository and GitHub history for every relevant current or historical record, including:

- Task 014 packets and drafts, including `task-014-fulfillment-tracking-implementation-packet.md` and `task-014-fulfillment-tracking-implementation-packet-proposed.md`;
- the existing canonical `wave-4-definition-of-ready.md`;
- `fulfillment-operating-modes.md`;
- `shopify-fulfillment-status-model.md`;
- `fulfillment-mode-uat-matrix.md`;
- DEC-011;
- D-014-2;
- Mode 1 and Mode 2 records;
- the existing proposed 16-condition Mode 2 engine, which Gate A must validate, reconcile, and either preserve exactly or supersede through an explicitly accepted decision;
- mode-switch records;
- disconnected/reconnect reconciliation decisions;
- COD decisions and matrices;
- fulfillment-state taxonomy;
- permission and scope decisions;
- readiness decisions;
- retry, idempotency, mutation, and reconciliation decisions;
- RA-022 and RA-023;
- fulfillment research notes;
- QA matrices;
- UAT and dev-store plans;
- locked, draft, or superseded fulfillment prompts;
- `mvp-completion-program.md`;
- `mvp-program-state.md`;
- `mvp-acceptance-matrix.md`;
- `research-handoff.md`;
- `architecture-review-log.md`;
- `sync-engine-risk-register.md`;
- `rejected-approaches-log.md`;
- `quality-feedback-loop.md`;
- issue #167;
- issue #185;
- issue #186;
- relevant PR discussions and control-room rulings.

Create or update the canonical resource inventory. Default path when no canonical equivalent exists:

`docs/01-research/wave-4-fulfillment-resource-inventory.md`

For every resource, record:

- path or GitHub reference;
- title;
- date;
- status;
- authoritative, current-supporting, superseded, historical, or rejected classification;
- relevant sections;
- contradictions;
- missing citations;
- whether revision is required;
- canonical successor when superseded.

Do not create duplicate canonical documents because an existing file has an unexpected name. Record the canonical-path mapping in the inventory.

Determine the next unused decision identifier from the repository. Do not guess or reserve a duplicate DEC number.

Phase 1 is complete only when the authority map is sufficient to distinguish current contract from history.

## 10. Phase 2 — Current official Shopify and Odoo research

### Shopify fulfillment research

Verify the exact current Admin GraphQL behavior relevant to Wave 4, including:

- FulfillmentOrder queries and identifiers;
- FulfillmentOrder status and request-status semantics;
- fulfillment-order line-item identifiers and quantities;
- merchant-managed read and write scopes;
- when the write scope is conditionally required;
- the separate Shopify staff permission `fulfill_and_ship_orders` required for fulfillment creation, distinguished from API access scopes;
- the exact current mutation surfaces for creating fulfillment and updating tracking information;
- partial fulfillment behavior;
- multiple FulfillmentOrders and location behavior;
- remaining and fulfillable quantities;
- cancellation and closure behavior relevant to accepted scope;
- hold/release or scheduling behavior only where accepted Wave 4 scope requires it;
- tracking number, carrier, URL, and notification inputs;
- mutation `userErrors` and structured error evidence;
- request IDs and rate-limit evidence;
- idempotency support or absence of native idempotency;
- API version compatibility;
- deprecated or legacy fulfillment surfaces that remain forbidden, explicitly including `fulfillmentCreateV2` and `fulfillmentTrackingInfoUpdateV2` as names removed from current Admin API versions.

Do not assume exact mutation or scope names from this prompt. Verify them from current official documentation.

Create or update the canonical Shopify fulfillment source refresh. Default path when no equivalent exists:

`docs/01-research/wave-4-shopify-official-fulfillment-notes.md`

### Odoo 19 delivery and tracking research

Verify through official Odoo 19 documentation and actual source:

- `sale.order` to picking relationships;
- `stock.picking` lifecycle;
- `stock.move` and `stock.move.line` quantity semantics, explicitly verifying Odoo 19 done quantity through `stock.move.line.quantity`, rejecting obsolete `qty_done` / `quantity_done` assumptions, and distinguishing demand such as `product_uom_qty`;
- validation workflow;
- partial delivery;
- backorders;
- multiple pickings;
- cancellations;
- return pickings and reverse transfers as an Odoo forward-sync boundary only; Shopify-side return or reverse-fulfillment synchronization is outside Wave 4;
- carrier and tracking fields;
- tracking updates after validation;
- packages where materially relevant;
- warehouse, location, company, and multi-company boundaries;
- transaction boundaries;
- locking and concurrency implications;
- cron and server-action integration points;
- module install, upgrade, and uninstall behavior.

Create or update the canonical Odoo 19 fulfillment notes. Default path when no equivalent exists:

`docs/01-research/wave-4-odoo19-fulfillment-architecture-notes.md`

Phase 2 is complete only when every version-sensitive proposed fulfillment behavior is supported or explicitly unresolved.

## 11. Phase 3 — Actual merged-code integration audit

Audit the actual merged code at the required base. Use targeted symbol tracing rather than unfocused repository narration.

### Core and Stage 0 Layer 2

Inspect at minimum:

- store configuration and lifecycle;
- credential service;
- readiness checks;
- API client;
- job model;
- enqueue/admission service;
- dispatcher;
- job actions;
- mutation-attempt model;
- mutation context;
- C1/C2/NET/C3 protocol;
- business-intent and exact-request fingerprints;
- idempotency-key behavior;
- operation-scope behavior;
- connection-generation and store-identity checks;
- reconciliation;
- retry and replacement jobs;
- manual-review routing and release;
- disconnect/reconnect quiescence;
- security groups, ACLs, record rules, and protected fields;
- lifecycle and uninstall behavior;
- redaction and logging;
- source guards;
- genuine simultaneous-concurrency harnesses.

### Order domain

Inspect at minimum:

- Shopify order binding;
- sale-order creation and provenance;
- Shopify line identifiers;
- quantities and cancellations;
- COD and transaction evidence;
- fulfillment-relevant imported state;
- duplicate prevention;
- company consistency;
- delivery/picking linkage already present or absent.

### Inventory domain

Inspect at minimum:

- Shopify locations;
- location mappings;
- product and variant bindings;
- inventory-level bindings;
- store/location identity behavior;
- accepted Layer 2 mutation patterns;
- operation-scope patterns;
- reconciliation patterns;
- review-release behavior.

### Odoo stock and delivery seam

Inspect actual Odoo 19 source for the models and workflows identified in Phase 2.

Trace realistic integration seams for:

- delivery eligibility;
- picking-to-order identity;
- move/line quantity mapping;
- partial delivery and backorder;
- multiple pickings;
- tracking creation and later update;
- cancellation;
- returns boundary;
- company and warehouse consistency;
- concurrent validations or tracking changes.

Create or update the canonical current-code audit. Default path when no equivalent exists:

`docs/03-architecture/wave-4-fulfillment-current-code-audit.md`

The audit must identify:

- reusable components;
- missing seams;
- cross-module changes that appear necessary;
- cross-module changes that are unnecessary;
- architecture risks;
- unsupported assumptions in existing documents;
- exact evidence for every proposed integration point.

Phase 3 is complete only when the later architecture can be traced to real current code.

## 12. Phase 4 — Decision and contradiction reconciliation

Create a complete decision matrix. For each item record:

- identifier;
- topic;
- prior source;
- verified facts;
- accepted ruling to preserve;
- contradiction or gap;
- proposed disposition;
- implementation implication;
- test implication;
- risk;
- whether control-room acceptance is required.

At minimum resolve or explicitly escalate:

1. source of truth for fulfillable quantity;
2. mapping between Odoo pickings/moves and Shopify FulfillmentOrders;
3. mapping between Shopify fulfillment-order line items and Odoo order/move lines;
4. partial picking and partial fulfillment;
5. multiple pickings for one order;
6. multiple Shopify FulfillmentOrders for one order;
7. multi-location fulfillment;
8. backorders;
9. cancelled Odoo pickings;
10. cancelled Shopify FulfillmentOrders;
11. returns and reverse transfers;
12. initial tracking creation;
13. later tracking update;
14. carrier-name and tracking-URL normalization;
15. missing tracking data;
16. Mode 1 admission and behavior;
17. Mode 2 admission and behavior;
18. every condition in the existing proposed 16-condition Mode 2 engine, including whether it is preserved, corrected, or escalated for acceptance;
19. mode switching with queued, running, uncertain, or review jobs;
20. disconnected-period reconciliation;
21. COD interaction;
22. non-COD interaction;
23. manual-review cases;
24. mutation job types;
25. one-job/one-attempt behavior;
26. operation-scope identity;
27. idempotency identity;
28. retry and replacement lineage;
29. uncertain-result reconciliation;
30. clean rejection;
31. store identity and connection generation;
32. company consistency;
33. permissions and protected fields;
34. logging and secret/PII minimization;
35. scheduled and manual admission;
36. replay and duplicate prevention;
37. readiness and scope checks;
38. upgrade and uninstall behavior;
39. historical deliveries and reconnect behavior;
40. dev-store resource cleanup;
41. FulfillmentOrder status and request-status eligibility for both modes, including exact treatment of OPEN, IN_PROGRESS, ON_HOLD, SCHEDULED, CLOSED, INCOMPLETE, cancelled, and other current official states.

Locate and reconcile the existing proposed 16-condition Mode 2 engine. Do not compress, expand, or paraphrase it while evaluating it. Preserve it exactly when supported; when official evidence, merged code, or accepted decisions conflict, propose explicit line-level corrections and escalate them for control-room acceptance before Gate B.

When existing accepted records conflict, preserve the history and propose one canonical current disposition. Do not silently choose.

Commercial or product questions that cannot be derived from accepted records must be escalated as a minimal control-room question set. Do not guess.

Create or update the canonical decision record using the next verified unused DEC identifier. The record remains proposed until accepted by the control room.

Phase 4 is complete only when every material contradiction has a proposed disposition or explicit blocker.

## 13. Phase 5 — Candidate Definition of Ready, architecture, and Task 014 packet

Prepare a complete candidate Wave 4 Definition of Ready and Task 014 implementation contract.

Reuse existing canonical files when present. Default paths when no equivalent exists:

- `docs/07-implementation-plan/wave-4-definition-of-ready.md`;
- `docs/07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md`.

Also inspect `task-014-fulfillment-tracking-implementation-packet-proposed.md` as historical/proposed input. Do not create a near-name replacement or a second canonical DoR/packet.

### Modular architecture contract

Define the proposed `shopify_connector_fulfillment` boundary, including:

- manifest and dependencies;
- models;
- bindings;
- fields;
- state taxonomy;
- constraints;
- services;
- handlers;
- job types;
- mutation domains;
- read-only operations;
- cron and manual backend actions;
- operation-scope keys;
- idempotency identities;
- reconciliation and lineage;
- permissions;
- ACLs;
- record rules;
- protected fields;
- error vocabulary;
- log events;
- manual-review actions;
- lifecycle and uninstall behavior;
- extension seams for later UI.

Do not permit one giant model or service file. Split by responsibility where actual complexity justifies it. Do not create unnecessary micro-modules.

### Layer 2 contract

Reuse the merged Stage 0 Layer 2 substrate. Freeze the candidate fulfillment integration for:

- domain registry values;
- job types;
- one job to at most one attempt for the job lifetime;
- C1 intent persistence;
- fresh pre-C2 read requirements as the primary duplicate-prevention control for fulfillment mutations that lack native idempotency, including verify-before-retry and adopt-if-found behavior;
- C2 side-cursor boundary;
- NET handling;
- C3 outcome persistence;
- business-intent fingerprint;
- exact-request fingerprint;
- idempotency-key derivation;
- operation-scope serialization;
- store identity and connection generation;
- outcome classification;
- reconciliation-before-retry;
- replacement-job behavior;
- manual-review routing and release;
- bounded retry behavior;
- no raw transport;
- no false success;
- no unsupported exactly-once claim.

Do not invent a parallel fulfillment mutation framework.

### Mode 1 and Mode 2 contract

For each mode define:

- purpose;
- admission event;
- source records;
- prerequisites;
- eligibility;
- exact condition matrix;
- fulfillable quantity;
- location resolution;
- tracking requirements;
- read sequence;
- mutation sequence;
- success evidence;
- clean rejection;
- uncertain outcome;
- reconciliation;
- retry;
- duplicate prevention;
- manual-review cases;
- disconnect behavior;
- reconnect behavior;
- mode-switch behavior;
- COD behavior;
- scheduled behavior;
- manual behavior;
- logs and operator evidence.

### Definition of Ready

The candidate DoR must state exact entry criteria for Gate B, including:

- accepted decision record;
- no unresolved product blocker;
- exact module boundary;
- exact file allowlist;
- exact job/mutation contract;
- exact Mode 1 and Mode 2 contracts;
- complete tests and validation plan;
- rollback plan;
- CV-013 carry-forward;
- no live Shopify mutation authorization before the later runtime gate.

Phase 5 is complete only when an implementation worker could proceed without inventing behavior, while still requiring control-room acceptance.

## 14. Phase 6 — Exact file boundary, tests, validation, rollback, and locked prompt

### Exact implementation allowlist

Freeze a candidate exact file allowlist for future Gate B.

Initial hypothesis to validate, not blindly accept:

- individually enumerated new files for `shopify_connector_fulfillment` (manifest, package initializers, models, services, security, data/cron, and tests only where the reconciled architecture proves each file necessary); do not authorize the addon through a wildcard;
- exactly `addons/shopify_connector_core/models/readiness_check.py`, symbol `REQUIRED_MVP_SCOPES`, only for the accepted scope-name correction;
- exact documentation and QA files.

List every permitted future implementation file explicitly. Do not use a broad authorization such as `addons/shopify_connector_core/**`, `addons/shopify_connector_sale/**`, or `addons/shopify_connector_inventory/**`.

Any cross-module edit must identify the exact file, symbol, demonstrated need, and regression responsibility.

List forbidden files and directories explicitly.

### Static and source-guard plan

Include checks for:

- no legacy fulfillment API surface, including name-specific guards for `fulfillmentCreateV2` and `fulfillmentTrackingInfoUpdateV2`;
- RA-023 line-identity enforcement through `lineItemsByFulfillmentOrder` or the exact current equivalent, with no order-ID-only fulfillment path;
- no raw transport;
- exact GraphQL document shapes;
- exact scopes;
- mutation-context enforcement;
- idempotency enforcement;
- operation-scope enforcement;
- protected-field enforcement;
- allowed-state and error vocabulary;
- no secret/PII logging;
- exact file-boundary enforcement.

### Unit-test plan

Include at minimum:

- Mode 1;
- all Mode 2 conditions;
- mode switching;
- COD and non-COD;
- partial delivery;
- backorder;
- multiple pickings;
- multiple FulfillmentOrders;
- location resolution;
- tracking creation;
- tracking update;
- cancellation;
- returns boundary;
- no-op;
- clean rejection;
- uncertain result;
- reconciliation;
- retry and replacement lineage;
- review release;
- duplicate prevention;
- company consistency;
- permissions;
- redaction;
- regression coverage for relevant prior defects and risk-register entries;
- explicit RA-022 and RA-023 source-guard and behavior tests;
- staff-permission/readiness tests distinct from API-scope tests.

### Genuine concurrency plan

Design independent PostgreSQL transaction/process tests for relevant races, including:

- duplicate admission;
- operation-scope serialization;
- mutation handoff;
- mode switch;
- tracking update;
- reconciliation replacement;
- review release;
- rollback injection;
- real PostgreSQL contention where feasible.

Do not represent savepoints or sequential independent connections as simultaneous concurrency.

### Odoo.sh runtime plan

Require:

- exact-head identity;
- fresh install;
- upgrade;
- focused fulfillment suite;
- complete connector regression;
- security matrix;
- lifecycle and uninstall/reinstall;
- zero residue;
- concurrency;
- failure and rollback injection;
- redaction and leak scan;
- evidence wording that distinguishes executed, static, and pending proof.

### Shopify dev-store validation plan

Design a safe future campaign using dedicated resources for:

- baseline reads;
- Mode 1 fulfillment;
- Mode 2 fulfillment;
- partial fulfillment where safe;
- tracking creation;
- tracking update;
- repeat/no-op;
- replay prevention;
- clean rejection or review routing where safely reproducible;
- read-after-write;
- cleanup/restoration;
- proof that no unrelated resource changed.

Wave 4 final acceptance requires both fulfillment dev-store validation and CV-013 issue #185 to execute green.

Create or update the canonical validation plan. Default path when no equivalent exists:

`docs/05-qa/fulfillment-mode-uat-matrix.md`

Use that existing canonical matrix as the validation-plan carrier. Create a different validation document only when Phase 1 proves the matrix cannot carry a required contract, records the exact gap, and designates one explicit canonical successor rather than a parallel source of truth.

### Rollback plan

Define:

- implementation rollback;
- data/schema rollback boundaries;
- job and mutation-attempt handling on rollback;
- mode-setting rollback;
- dev-store fixture cleanup;
- conditions requiring restore from the integration checkpoint;
- evidence required before retrying a failed gate.

### Locked implementation prompt

Create a complete future Codex implementation prompt at:

`docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md`

The prompt must include:

- exact accepted base placeholder;
- role and authority;
- exact allowed files and a hard stop on any silent file-boundary expansion;
- exact forbidden files;
- complete functionality;
- Mode 1 and Mode 2 contracts;
- Layer 2 contract;
- security and logging;
- tests;
- runtime evidence;
- rollback notes, including rollback of the narrow cross-module readiness-scope correction;
- definition of done;
- hard stops;
- final report;
- prohibition on self-acceptance, ready-marking, merge, live Shopify mutation, or Wave 5 work.

Mark the prompt clearly:

`LOCKED CANDIDATE — NOT ISSUED; REQUIRES CHATGPT CONTROL-ROOM ACCEPTANCE`

Do not execute or issue it.

Phase 6 is complete only when the future implementation and validation path is unambiguous and bounded.

## 15. Phase 7 — Adversarial review, coherent correction, trackers, and handoff

Perform one complete adversarial review of the full Gate A package.

Challenge at minimum:

- stale Shopify API assumptions;
- use of legacy fulfillment surfaces;
- unsupported scope names;
- missing or altered Mode 2 conditions;
- partial-delivery ambiguity;
- Odoo quantity misinterpretation;
- location mismatch;
- multiple-picking and multiple-FulfillmentOrder gaps;
- duplicate remote effects;
- false success;
- unsafe retries;
- inadequate reconciliation;
- mode-switch races;
- disconnect/reconnect races;
- COD contradictions;
- company mismatch;
- permission bypass;
- secret or PII leakage;
- uninstall residue;
- giant-module architecture;
- unnecessary cross-module changes;
- tests that do not exercise production paths;
- sequential tests mislabeled as concurrency;
- dev-store cleanup risks;
- unauthorized scope;
- CV-013 being silently downgraded;
- locked implementation prompt drifting beyond the accepted packet.

Correct every issue found in one coherent documentation batch. Do not begin implementation.

Run the mandatory end-of-session learning review defined by `quality-feedback-loop.md`. Record the result in the **Learning feedback loop** section of `docs/01-research/research-handoff.md`, including lessons, reusable controls, rejected approaches, and whether any canonical governance file requires a follow-up correction. The session is not complete until this learning review is recorded.

Update the canonical current-state records:

- `docs/07-implementation-plan/mvp-program-state.md`;
- `docs/05-qa/mvp-acceptance-matrix.md`;
- `docs/01-research/research-handoff.md`;
- `docs/05-qa/architecture-review-log.md`;
- `docs/05-qa/sync-engine-risk-register.md` when a demonstrated risk requires it;
- `docs/07-implementation-plan/wave-4-gate-a-handoff.md`.

Post a final handoff comment to issue #186 containing:

- PR number;
- exact final SHA;
- canonical output list;
- decisions preserved;
- proposed decisions;
- unresolved blockers;
- exact future implementation allowlist summary;
- CV-013 status;
- recommendation.

## 16. Documentation quality and canonical-output rules

Prefer updating canonical existing files over creating duplicates.

The final Gate A package must provide the following functions, whether through existing canonical files or the default paths named above:

1. resource inventory and authority map;
2. official Shopify fulfillment source refresh;
3. official Odoo 19 fulfillment architecture notes;
4. actual merged-code integration audit;
5. decision reconciliation record;
6. Wave 4 Definition of Ready;
7. Task 014 implementation packet;
8. modular architecture and Layer 2 contract;
9. exact allowed and forbidden file lists;
10. complete test and evidence matrix;
11. Wave 4 dev-store validation plan;
12. rollback plan;
13. locked, unissued implementation prompt;
14. live program-state and acceptance-matrix updates;
15. research, architecture-review, risk, and handoff updates;
16. completed quality-feedback-loop review recorded in the Learning feedback loop section of `research-handoff.md`.

When an existing canonical file fulfills one of these functions, update it and record that mapping in the resource inventory. Do not create a second source of truth.

All factual claims require citations or code references. All recommendations must state their basis. All proposed decisions must remain visibly proposed pending control-room acceptance.

## 17. Commit and PR discipline

Use a small coherent docs-only commit sequence, normally no more than five commits:

1. identity, inventory, and checkpoint;
2. official-source research and code audit;
3. decision reconciliation and candidate DoR/packet;
4. test, validation, rollback, and locked-prompt package;
5. adversarial corrections, trackers, and final handoff.

Use fewer commits when that is more coherent. Do not create noisy one-file commits.

Before every commit, verify:

- no file under `addons/**` changed;
- no unrelated file changed;
- no secret or credential entered the repository;
- claims match available evidence.

Push every commit to the Gate A branch. Keep the PR draft and unmerged.

## 18. Hard stops

Stop and return one consolidated blocker report when:

- exact-base identity fails;
- a protected reference changed unexpectedly;
- a competing authorized Wave 4 branch/PR exists;
- fulfillment implementation already exists unexpectedly;
- current official Shopify evidence conflicts materially with an accepted product decision;
- required Odoo 19 source is unavailable and the missing behavior is decision-critical;
- a product/commercial ruling is required and cannot be derived from accepted records;
- the proposed architecture requires a destructive or irreversible migration;
- scope would materially change;
- security or credential exposure is found;
- an exact future implementation boundary cannot be frozen without an unresolved critical decision;
- the work would require a file outside the frozen allowlist and no explicit control-room amendment exists.

Do not hard-stop for missing Shopify credentials or a development store during Gate A.

## 19. Definition of done

This session is complete only when:

- the exact identity gate is recorded;
- the Gate A branch and draft PR exist;
- the full resource inventory is complete;
- current official Shopify research is cited;
- current official Odoo 19 behavior is cited and code-verified;
- the actual merged connector is audited;
- accepted prior decisions are preserved;
- contradictions are corrected or explicitly escalated;
- Mode 1 and Mode 2 backend contracts are complete;
- the exact 16-condition Mode 2 engine is preserved or its conflict is escalated;
- the Layer 2 contract is complete;
- the exact future allowed and forbidden file lists are complete;
- test, concurrency, runtime, security, lifecycle, dev-store, and rollback contracts are complete;
- CV-013 is carried forward as critical;
- the locked implementation prompt exists but is not issued;
- the adversarial review is complete;
- the mandatory `quality-feedback-loop.md` review is complete and recorded in the Learning feedback loop section of `research-handoff.md`;
- canonical trackers and handoff are updated;
- all changes are committed and pushed;
- no `addons/**` file changed;
- no Shopify mutation occurred;
- no self-acceptance occurred;
- the PR remains draft and unmerged.

## 20. Final report

Return one concise but evidence-complete report containing:

1. identity, branch/PR, starting SHA, final SHA, changed files, and commits;
2. canonical outputs created or updated and their source-of-truth mapping;
3. official Shopify and Odoo 19 findings with citations;
4. merged-code audit findings and exact integration seams;
5. accepted decisions preserved, contradictions corrected, proposed decisions, and remaining minimal control-room questions;
6. complete Mode 1, Mode 2, proposed 16-condition reconciliation, and Layer 2 contract summaries;
7. exact future allowed and forbidden file lists;
8. test, source-guard, concurrency, runtime, security, lifecycle, dev-store, rollback, and CV-013 plans;
9. risks, mitigations, and mandatory learning-feedback-loop outcome;
10. confirmations that no `addons/**` file changed, no Shopify mutation occurred, the PR remains draft/unmerged, and the locked implementation prompt was not issued;
11. recommendation: `READY FOR CONTROL-ROOM GATE A REVIEW` or `NOT READY — CONSOLIDATED DECISION BLOCKERS`.

Then stop. Do not start implementation.
