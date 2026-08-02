# Premium UX implementation delta — UI restructure (2026-08-02)

> **Status: Signed implementation contract companion.** This delta applies the
> product-owner-approved [C1–C8 contract](ui-restructure-design-contract-2026-08-02.md)
> to the earlier
> [Premium UX Master Specification](premium-ux-master-specification.md). Where
> they conflict, C1–C8 and this delta govern. The earlier document remains the
> source for compatible tokens, accessibility, density, and component rules.

## 1. Product-shell rules

- The connector has one Odoo application shell and exactly four navigation
  pillars: Dashboard, Operations, Reporting, and Configuration.
- User and Administrator are the only visible connector roles. Hidden
  Auditor, Operator, and Reviewer capability groups remain enforcement
  primitives and are never exposed as merchant roles or menu concepts.
- Configuration is Administrator-only. Day-to-day work is under Operations.
- Store is explicit on every operational result. One company may have multiple
  stores, but store/company, credential generation, readiness, mapping, mode,
  queue, and recovery evidence never cross store boundaries.
- "All stores" is supported on Connector Health. Monetary values are always
  partitioned by currency and never combined into an invented total.
- Operator copy says **run**, **Runs & Recovery**, and **Needs Attention**.
  Technical model names, mutation ledgers, and diagnostics are contextual
  drill-downs rather than primary navigation labels.

## 2. Locked navigation

| Pillar | Merchant-facing destinations | Visibility |
| --- | --- | --- |
| Dashboard | Sales Dashboard; Connector Health | User, Administrator |
| Operations | Orders; Product Imports/Exports; Inventory; Fulfillment; Runs & Recovery; Needs Attention | User, Administrator; actions remain server-side capability-gated |
| Reporting | Sales Analysis; Sync Performance; Audit Trail | User, Administrator, subject to model ACLs and record rules |
| Configuration | Stores & Onboarding; Sync Rules; Product / Variant / Customer / Location Mappings; Export Settings; Fulfillment Settings and Mode | Administrator only |

Existing XML IDs are retained when an action or menu merely moves. Any retired
ID requires an explicit reference sweep and evidence entry before removal.

## 3. Two-dashboard contract

### 3.1 Sales Dashboard

The Sales Dashboard is a reporting surface, not a connector-health surface.
It shows rule-visible Odoo orders imported from Shopify, separated by currency
and store. The headline label is **Imported Odoo order value**. Orders marked
`shopify_connector_review = True`, quarantined orders, and cancelled orders are
excluded from reconciled commercial metrics; review populations are disclosed
separately as **Awaiting data review**. Every KPI uses the same ruled model and
domain as its drill-down. Loading, empty, unavailable, stale, and permission-
denied states never render fabricated zeroes.

### 3.2 Connector Health

Connector Health contains no sales KPIs. It reports store connection and
readiness, queue depth and oldest blocked age, retries and exhausted failures,
ambiguous mutations, last successful synchronization by domain, throttle
headroom, mapping/readiness gaps, reconciliation state, and fulfillment-mode
transition state. "All stores" preserves per-store rows and worst-state detail:
a failing store or unknown subsystem cannot be hidden by a healthy aggregate.
Every timestamp names its source and unknown/stale states are explicit.

## 4. Onboarding presentation over durable state

The existing twelve durable setup steps keep their order and semantics. The UI
groups them into five merchant phases without collapsing or skipping any step.

| Phase | Durable steps | Completion meaning |
| --- | --- | --- |
| Connect | 1 Store identity/company; 2 Authentication; 3 Permanent domain and Shopify shop ID | The intended permanent store identity is authenticated and linked to one Odoo company |
| Choose | 4 Required scopes; 5 Enabled domains and directions | Permissions and operating scope are explicit |
| Map | 6 Refresh Shopify setup data; 7 Complete applicable mappings | The exact admitted refresh run reaches terminal success and all enabled-domain mappings are complete |
| Protect | 8 Source-of-truth rules; 9 First-push safeguards; 10 Fulfillment mode and notification policy | Direction, risk controls, and consequences are understood and persisted |
| Verify | 11 Final readiness checks; 12 Review and activate | Every enabled domain is ready; activation is blocked on stale refresh, incomplete mapping, missing scope, or failed check |

The refresh action discloses **Queues a background read from Shopify**. Its
client follows the admitted store-scoped run with bounded backoff. It shows a
visible still-running state, reloads locations/readiness only after success,
shows the recorded failure reason plus Retry on failure, coalesces duplicate
clicks, and resumes the correct store and durable step after close/reopen.

## 5. Fulfillment-mode transition panel

The panel presents separate facts rather than one overloaded switch:

| Field | Required presentation |
| --- | --- |
| Effective mode | The mode governing behavior now; remains Mode 1 until a clean scan commits Mode 2 |
| Requested mode | The operator's requested destination, if any |
| Scan state | Not started / Queued / Running / Retry scheduled / Failed / Stale or missing / Passed |
| Next action | Confirm, wait, retry at a stated time, inspect reason, return to Mode 1, or no action |
| Evidence | Last verified timestamp, run link, and preserved failure reason |

Confirmation discloses **Queues a Shopify reconciliation read; it does not
change the effective mode immediately**. Duplicate confirmations coalesce onto
the in-flight scan. Refused admission, terminal failure, and stale/missing runs
return to a stable, recoverable Mode 1 state. **Return to Mode 1** remains
reachable during or after a failed switch and preserves audit evidence.

## 6. Export acknowledgement component

Every exposed export domain uses one merchant-facing ladder derived from
durable mutation-attempt and reconciliation evidence:

| Status | Meaning shown to the merchant |
| --- | --- |
| Queued | Nothing has been sent yet |
| Sending | A remote mutation attempt is in progress |
| Accepted by Shopify | Shopify accepted the request and returned the expected immediate response evidence |
| Verified in Shopify | A required readback or asynchronous-operation result confirms the expected remote state |
| Needs attention | The outcome is ambiguous or verification disagrees |
| Rejected | Shopify definitively rejected the mutation |

Asynchronous operations can never reach Verified before their remote operation
has reached a successful terminal state. The component always provides the
evidence timestamp and a contextual route to the applicable run or case.

## 7. Presentation and interaction constraints

- Use the platform font stack, existing connector type scale, spacing tokens,
  8 px radius, hairline borders, and one restrained card treatment. No new
  decorative font, gradient, or card wall is introduced.
- Desktop, tablet, mobile, 200% zoom, and RTL use logical CSS properties and
  preserve the primary action, state text, timestamps, and drill-downs without
  page-level horizontal scrolling.
- Every asynchronous region defines Loading, Still running, Empty, Success,
  Retryable failure, Terminal failure, Unknown/stale, and Permission denied
  where applicable. Colour never carries state alone.
- Keyboard order follows visual order; focus is visible and unobscured; status
  updates use an appropriate live region without repeatedly announcing poll
  ticks; reduced motion removes nonessential transitions.
- Every visible action states whether it reads Shopify, writes Odoo
  configuration, writes Odoo business data, mutates Shopify, or queues a run,
  with consequence copy before remote or destructive action.

## 8. Wireframe and implementation trace

The low-fidelity target for the new and materially restructured screens is
[UI restructure wireframes — 2026-08-02](../09-ui-prototype/ui-restructure-wireframes-2026-08-02.md).
Production implementation must be validated against both that layout trace and
the stronger behavioral requirements in C1–C8; a matching layout never
substitutes for state-machine, security, or reconciliation proof.
