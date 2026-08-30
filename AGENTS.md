# AGENTS.md — Execution Ownership and Review Lenses

> `CLAUDE.md` is the project governance authority. This file defines how one or
> more implementation/review agents cooperate without creating an uncontrolled swarm.

## 1. Operating model

One lead implementation owner is accountable for the active coherent scope, integration
state and handoff. “Agent” below is a responsibility lens; it does not require a separate
process or model. One capable implementation model may perform every lens sequentially.

Parallel work is optional, never assumed. It is allowed only when the user or execution
environment authorizes it, files do not overlap, contracts are already stable, and one
owner will integrate and rerun the affected gates.

## 2. Required responsibility lenses

| Lens | Responsibility | Must not do |
| --- | --- | --- |
| Lead implementer | Own exact base, scope, integration, tests, evidence and rollback | delegate accountability or merge incomplete evidence |
| V1 compatibility | Trace current behavior/data and prevent recurrence of known V1 defects | preserve an error merely because it exists in V1 |
| Shopify integration | Validate GraphQL, webhooks, scopes, cost, idempotency and readback against the pinned API | invent fields or rely on vendor/competitor behavior |
| Odoo architecture | Validate ORM, transactions, security, cron, modules, views, migrations and lifecycle against pinned Odoo 19 | add non-native infrastructure without evidence |
| Domain/product | Validate authority, matching, totals, quantity, fulfillment and future extension seams | broaden current release scope silently |
| UX/accessibility | Validate complete journeys, Odoo-native composition, roles, responsive/RTL and recovery clarity | optimize screenshots at the expense of evidence or safety |
| Reliability/security | Trace concurrency, retries, uncertain mutations, tenant isolation, secrets, PII and failure injection | accept hidden buttons or `sudo()` as authorization |
| Release reviewer | Independently verify exact candidate, migration, live readback and rollback evidence | approve from the author summary alone |

Where team size permits, the final mutation-safety/security/release verdict is performed
by someone other than the author of the last material change. On a single-agent run,
perform a fresh evidence-based review pass and record that independence is logical, not
organizational.

## 3. Editing and integration rules

- One owner edits a model/contract/subsystem at a time.
- Research/review may run beside implementation only when it does not mutate overlap.
- No agent silently moves from review into unrelated implementation.
- Every result is committed to GitHub with exact files, tests and evidence.
- Conflicting recommendations are resolved against `CLAUDE.md`, accepted V2 decisions,
  official platform facts and actual repository behavior before code continues.
- The continuous program does not pause for routine internal handoffs; the lead owner
  integrates and advances when the automatic evidence gate passes.

## 4. Continuous handoff

Before a chat/session/context switch, the active owner updates
`docs/v2/13-continuous-execution-handoff.md` with:

- exact branch, base and head;
- active wave and task ID;
- completed and in-progress behavior;
- changed/uncommitted files;
- tests run and tests still required;
- external environment state without secrets;
- known defects/blockers and whether intentionally deferred to the end;
- rollback point and exact first next action.

The receiving owner verifies the head and handoff before acting, continues from the
first next action, and does not repeat completed research or implementation.

## 5. Prohibited coordination patterns

- uncontrolled agent swarms;
- overlapping edits to the same contracts/models;
- large fan-out without synthesis ownership;
- agent conclusions that exist only in chat;
- marking a gate complete from summaries without test/evidence inspection;
- restarting from an old prompt or stale branch after a handoff;
- including credentials, access tokens or customer PII in agent prompts/handoffs.

