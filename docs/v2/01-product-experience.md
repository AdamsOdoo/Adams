# V2 Product Experience

> **Classification:** implementation-ready product contract for architecture-gate review. This refines the accepted U0 visual principles and DEC-012 operator flows; it does not silently replace them.

## 1. Product promise

V2 turns the connector from a collection of configuration and sync surfaces into an **operations workspace**. It is optimized for successful setup, exception resolution and trustworthy change—not feature-count theater.

### Experience principles

| Principle | Product consequence |
| --- | --- |
| One dominant answer | Every screen leads with status, required action, or result; secondary detail is progressive. |
| Calm by default | Healthy state is compact. Space and attention are reserved for risk and decisions. |
| Evidence before action | Risky actions show source, destination, authority, changed fields, affected records and rollback posture. |
| Recovery is a workflow | Errors name the owner, safe next action, retry eligibility and evidence—not raw stack traces. |
| Odoo-native | Familiar lists, forms, filters, chatter and access rules; custom Owl only where live composition materially improves work. |
| Honest freshness | “Last observed”, “next check” and “data through” replace vague “real-time” claims. |
| Accessible without color | Text, icon, position and focus state convey every status. |

## 2. Navigation and information architecture

The app header contains a persistent store switcher and health summary. The primary navigation is deliberately short:

| Area | Primary question | Default surface |
| --- | --- | --- |
| Overview | Is the store safe? | Selective Owl command center |
| Needs Attention | What requires a person? | Odoo list + guided resolution panel |
| Products | What is linked, missing or protected? | Odoo list/form; matching and diff as focused Owl flows |
| Orders | What arrived and is operationally blocked? | Odoo list/form with connector evidence panel |
| Inventory | What is mapped, drifting or waiting for approval? | Odoo list plus preview/consistency wizard |
| Fulfillment | What was sent, held or needs verification? | Odoo list/form + event timeline |
| Runs | What happened and why? | Odoo list/form + attempt timeline |
| Settings | Is the store correctly configured? | Odoo form + guided setup/readiness |

“Sync Center” and “Error Center” become views over **Runs** and **Needs Attention**, not separate concepts users must learn. Technical logs remain available to authorized administrators from a run.

## 3. Core journeys

### 3.1 Connect and activate a store

1. Name the connection and enter the canonical `*.myshopify.com` domain.
2. Add the credential in a write-only field; test connectivity and display scopes as pass/missing.
3. Choose enabled workflows and authority, in plain language.
4. Choose Odoo defaults: company, warehouse, sales team, fiscal position, pricelist and notification posture as applicable.
5. Map Shopify locations to Odoo locations.
6. Run readiness checks grouped as **Action required**, **Passed**, and **Not applicable**.
7. Review impact and activate.

Activation is impossible while a mandatory check fails. Re-testing does not expose the stored secret. A disconnected store retains its operational evidence according to the accepted lifecycle policy.

### 3.2 Operate daily

The Overview opens with one health band:

- **Healthy:** no active exception; show last observation and next scheduled check.
- **Attention required:** human decision is blocking work; show up to three highest-impact items.
- **Degraded:** retryable technical failure; show affected workflow and recovery progress.
- **Paused:** user or safety gate stopped admission; explain scope and resume conditions.
- **Disconnected:** connection invalid or intentionally removed; show safe recovery route.

Below it, compact workflow rows show Products, Orders, Inventory and Fulfillment with freshness, last successful result and active exception count. Recent activity is subordinate; vanity totals are excluded.

### 3.3 Resolve an exception

Each attention item must expose this contract:

| Field | Meaning |
| --- | --- |
| What happened | Human summary; no internal state token |
| Impact | Records and workflow currently held |
| Evidence | Incoming identifiers, match candidates, totals, mapping or last observation |
| Owner | Administrator, Operator, Reviewer or external dependency |
| Safe action | Fix configuration, select mapping, approve, verify remote state, retry eligible attempt, skip with reason |
| Consequence | What will happen after the action |
| Audit | Actor, timestamp, reason and linked run |

Bulk actions appear only when every selected item has the same safe transition. “Retry all” is never a generic action.

### 3.4 Launch an operation

A single operation launcher handles import, export preview, reconciliation and scoped replay. It asks for store, workflow, scope/filter and execution mode. Before confirmation it shows estimated record count, authority, risky side effects, and whether the operation is preview-only. Submission returns a run ID immediately.

### 3.5 Investigate a run

The run detail tells a narrative:

1. request and actor/trigger;
2. admission checks and configuration generation;
3. jobs created and priority lane;
4. attempts, Shopify cost/throttle observations and redacted responses;
5. verification/readback where required;
6. terminal result and affected records.

Users navigate from any Odoo record to its connector evidence and back to the run without searching logs.

## 4. Screen contracts

| Screen | Must show | Primary action | Must not do |
| --- | --- | --- | --- |
| Overview | store state, freshness, ≤3 active exceptions, workflow health, recent activity | Resolve top issue or launch operation | nine equal metric cards; success noise |
| Needs Attention | severity, workflow, impact, age, owner, safe next action | Open resolution | collapse technical failure and human review into one color-only state |
| Store setup | progress, saved state, validation evidence, consequences | Continue / activate | imply a token can be read back; activate through failed readiness |
| Matching | incoming identity, authoritative keys, advisory evidence, candidates, existing binding conflicts | Bind/select/leave for review when genuinely ambiguous | fuzzy/name-only automatic matching |
| Product preview | source/target value, authority, protected fields, validation, affected variants | Confirm eligible changes | offer confirm while authority or validation is unresolved |
| Location mapping | Shopify location, Odoo location, conflict/unmapped evidence | Save mapping / preview first push | infer mapping from names and write immediately |
| Run detail | timeline, attempts, error classification, readback, affected objects | Context-specific recovery | show stack trace as primary explanation |
| Record panel | binding, last observed, last successful run, active hold, Shopify link | Open run / resolve | duplicate an entire technical form inside each business record |

## 5. State model

Do not overload a single `state` field. UI projections combine independent dimensions:

| Dimension | Vocabulary |
| --- | --- |
| Connection | unconfigured, testing, connected, invalid, disconnected |
| Configuration | incomplete, valid, stale |
| Activation | draft, active, paused, retired |
| Runtime health | healthy, attention_required, degraded, blocked, unknown |
| Workflow readiness | disabled, not_ready, ready, paused |
| Run execution | requested, admitted, running, waiting, succeeded, partially_succeeded, failed_retryable, blocked_manual_review, failed_terminal, cancelled |

The UI renders human labels and keeps internal tokens in diagnostics only. Freshness is always a timestamp plus an interpretation—not a green dot alone.

## 6. Role-aware experience

| Role | Can see | Can act |
| --- | --- | --- |
| Administrator | all stores, settings, credentials posture, technical evidence | connect, configure, activate/pause, destructive approvals, security-sensitive recovery |
| Operator | assigned companies/stores and operational evidence | launch safe operations, fix mappings, retry eligible failures |
| Reviewer | review queues and evidence needed for decisions | approve/reject/manual bind/skip with reason |
| Auditor | redacted history and configuration snapshots | export/read evidence only |
| No access | no connector menus, models, counters or activities | none |

Record rules and service-layer authorization both apply. Buttons are not security boundaries.

## 7. Premium visual direction

“Premium” means coherence and confidence, not decoration:

- restrained neutral canvas with semantic color used sparingly;
- clear 8-point spacing rhythm, strong typographic hierarchy and consistent density;
- one primary action per state; destructive actions visually and spatially separated;
- compact health bands, quiet secondary cards and evidence-rich detail drawers;
- readable empty states that explain what to do next;
- skeleton loading for composed surfaces; no layout shift;
- responsive shell at tablet/mobile widths, keyboard-complete flows and mirrored RTL;
- platform FontAwesome icons in production; no bespoke icon language unless a real gap is proven.

The accepted U0 prototype remains historical input. The implementation-level hierarchy, states and composition are now demonstrated in the [interactive V2 blueprint](https://shopify-connector-v2-blueprint.mostafaessam94.chatgpt.site) and specified in `05-ux-design-blueprint.md`. Production remains Odoo-native and uses the documented DTO/security contracts rather than copying the prototype as a standalone SPA.

## 8. Experience acceptance measures

- A first-time admin can connect and reach an honest readiness result without documentation.
- An operator can identify the highest-impact blocked workflow from Overview in under 10 seconds in usability testing.
- Every failed or held operation exposes owner, safe next action, impact and evidence.
- No risky mutation can be confirmed without authority and impact visible in the same flow.
- Common operational tasks require no navigation into technical models.
- All critical flows pass keyboard, focus, contrast, 375/768/1366 viewport and RTL checks.
- Screen readers receive status text and live-progress announcements without noisy polling updates.
