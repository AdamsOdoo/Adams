# UI restructure wireframes — 2026-08-02

> **Implementation wireframe notes.** These low-fidelity layouts translate the
> signed [C1–C8 contract](../02-product/ui-restructure-design-contract-2026-08-02.md)
> into build targets. They supersede prior prototype navigation and the
> combined Store 360 composition where they conflict. They do not invent new
> backend evidence or claim rendered-browser validation.

## 1. Shared shell

| Vertical band | Content and behavior |
| --- | --- |
| Odoo application bar | Standard Odoo chrome and breadcrumb; no connector-owned font or decorative hero |
| Connector navigation | Four pillars only: Dashboard / Operations / Reporting / Configuration; Configuration hidden from non-Administrators |
| Page header | One H1, short purpose line, store selector where relevant, explicit page-generation timestamp, at most one primary action |
| Context/status band | Connection or source-freshness warning only when it changes interpretation; unknown and stale are named |
| Main content | Bounded aggregate regions or native lists/forms; no unbounded client fetches or client-supplied ID sets |
| Drill-down | Counts open the same ruled model/domain that produced them; technical evidence appears contextually |

At mobile width, the page header stacks in source order; the store selector and
primary action remain fully visible. RTL mirrors through logical properties,
while domains, GIDs, currencies, timestamps, and other mixed-direction tokens
receive bidi isolation.

## 2. Sales Dashboard

| Order | Region | Controls | States and contract |
| ---: | --- | --- | --- |
| 1 | Header | Store selector; period; Refresh (local aggregate read) | Store is mandatory; multi-store selection keeps currencies partitioned |
| 2 | Source disclosure | Imported-through timestamp; coverage/review warning | Page time never impersonates Shopify-source freshness |
| 3 | Commercial summary | Imported Odoo order value; Imported orders; Average imported order value; Units sold | Same-model/domain drill-downs; review/quarantine/cancel excluded |
| 4 | Awaiting data review | Separate count and per-currency value, with Review cases link | Never folded into reconciled totals or styled as successful revenue |
| 5 | Trend | One restrained chart plus accessible table | Per-currency series; empty and incomplete-period states explicit |
| 6 | Top products | Maximum five rows; Open lines | Uses the eligible goods-line population; table scroll is contained |
| 7 | Empty/error | Guidance or permission message | No fake monetary zero when access or completeness is unknown |

Desktop uses a four-cell summary followed by trend/table regions. Tablet uses a
2×2 summary. Mobile uses one column and keeps source disclosure adjacent to the
numbers it qualifies.

## 3. Connector Health

| Order | Region | Controls | States and contract |
| ---: | --- | --- | --- |
| 1 | Header | Store / All stores selector; Refresh (local aggregate read) | All stores is health-only; generated-at timestamp visible |
| 2 | Overall state | Healthy stores / stores needing attention / unknown stores | Worst state and unknown subsystems remain visible; no averaging to green |
| 3 | Work posture | Queue depth; oldest blocked age; retry scheduled; exhausted failures; ambiguous mutations | Each count opens Runs & Recovery or Needs Attention with identical scope |
| 4 | Domain matrix | Orders / Catalog / Inventory / Export / Fulfillment: last success, backlog, failure, reconciliation freshness | Missing evidence renders Unknown, never zero or healthy |
| 5 | API and mapping | Throttle headroom; observed-at; readiness/mapping gaps | Stale observations are labelled; no live-Shopify claim |
| 6 | Mode switch | Effective/requested/scan state/next action per store | Route to Configuration panel; no sales measure on this page |
| 7 | Store table/cards | One row/card per store with company and worst condition | Mobile cards expose Open action without horizontal page scrolling |

## 4. Needs Attention

| Order | Region | Controls | States and contract |
| ---: | --- | --- | --- |
| 1 | Header | Store filter; domain; owner; severity | One prioritized human-case inbox, not separate technical queues |
| 2 | Priority summary | Immediate / decision needed / verification needed | Counts equal the filtered case population |
| 3 | Case list | What happened; why it matters; store; age/freshness; owner; whether connector can recover | One primary **Review** route per case; raw trace is secondary evidence |
| 4 | Resolution route | Domain-specific order, mapping, export, inventory, or fulfillment flow | No generic "mark fixed" that bypasses the domain contract |
| 5 | Empty/error | "No cases need attention" or rule/permission-safe error | Never exposes cross-company counts or raw secret-bearing payloads |

## 5. Runs & Recovery

| Order | Region | Controls | States and contract |
| ---: | --- | --- | --- |
| 1 | Header | Store, domain, state, source, time filters | Merchant copy uses run; stable technical IDs remain available in detail |
| 2 | Posture | In progress / retry scheduled / blocked / final failure | Admission is distinct from completion |
| 3 | Runs list | Purpose, source, store, started/finished, attempt, next retry, outcome | Keyboard-accessible native list or bounded workspace |
| 4 | Recovery actions | Retry; Reconcile/Verify; Cancel | Each action discloses local/remote/background effect and eligibility before confirmation |
| 5 | Detail drawer/form | Attempts, logs, mutation evidence, connection generation, scope | Diagnostics are contextual; secrets and unsafe raw values remain redacted |

Retry is hidden when the error taxonomy forbids it. Reconcile/Verify is favored
for ambiguous remote outcomes. Cancel states what work will remain incomplete
and requires the existing audited reason where applicable.

## 6. Stores & Onboarding

### 6.1 Stores list

| Region | Content and controls |
| --- | --- |
| Header | Company filter; Add store (Administrator; writes Odoo configuration and begins setup) |
| Store row/card | Store name/domain, company, connection, readiness, enabled domains, last verified, Continue setup/Open |
| Empty | Explain that adding a store starts configuration; no operations shortcut before readiness |

### 6.2 Onboarding frame

| Region | Content and controls |
| --- | --- |
| Header | Store identity + company; Save and close; durable "last saved" state |
| Phase rail | Connect / Choose / Map / Protect / Verify; current phase and blocked state expressed in text |
| Step body | The current durable step, why it matters, relevant fields, inline validation, consequence copy |
| Refresh status | Exact run: Queued / Running / Still running / Retry scheduled / Failed / Complete, with timestamps |
| Footer | Back; Save and close; Continue; Activate only on the final fully-ready step |

The five-phase grouping maps to all twelve durable steps in the dated UX delta
§4. Close/reopen resumes the store and step persisted by the server. Refresh
duplicate clicks reuse the active run. A failed refresh shows its recorded
reason and Retry; successful completion reloads locations and readiness before
Continue becomes eligible.

## 7. Fulfillment Settings and Mode panel

| Region | Content and controls |
| --- | --- |
| Current behavior | **Effective mode** lead value and concise consequence |
| Requested change | Requested mode, requester, requested timestamp |
| Reconciliation scan | State, exact run link, started/last observed/next retry, preserved failure reason |
| Next action | Wait; Retry; Inspect; Return to Mode 1; or Confirm switch, exactly one primary action |
| Evidence footer | Last verified timestamp and connection generation; audit route |

Confirm switch queues a Shopify reconciliation read and does not claim the mode
changed. Return to Mode 1 is reachable while switching and after failure. A
refused, missing, stale, retry-exhausted, or terminally failed scan cannot leave
an orphaned in-progress flag. Repeated confirmation coalesces onto the one
in-flight scan.

## 8. Export acknowledgement component

| Region | Content and controls |
| --- | --- |
| Status line | Queued / Sending / Accepted by Shopify / Verified in Shopify / Needs attention / Rejected |
| Evidence line | Last evidence timestamp; direct response vs readback/asynchronous-operation source |
| Next action | Wait; Verify; Review; Retry only when safe; Open remote identity where available |
| Context | Store, domain, target record, exact run and attempt route |

The ladder is used consistently in product/media export, inventory, and
fulfillment surfaces. Accepted is not Verified. Async work stays Accepted (or
Sending when the remote operation itself is in progress) until the remote
operation reaches terminal success and the policy-required verification passes.

## 9. Cross-screen state matrix

| State | Sales | Health | Attention | Runs | Onboarding / mode |
| --- | --- | --- | --- | --- | --- |
| Loading | Skeletons; preserve filters | Skeletons; preserve selector | Skeleton rows | Skeleton rows | Disable duplicate action; announce once |
| Still running | Not applicable to aggregate read | Show in-progress posture | Case may link to run | Live state with bounded refresh | Visible exact-run status and bounded backoff |
| Empty | No eligible imported orders | First-run/unknown distinguished from healthy | Affirmative all-clear | No runs for filter | Guided next step |
| Success | Reconciled, review-excluded metrics | Per-store healthy evidence | Resolved case leaves inbox | Terminal succeeded | Reload evidence/readiness before success |
| Retryable failure | Aggregate-read Retry | Retry schedule and affected subsystem | Case remains actionable | Next retry timestamp | Retry with preserved reason |
| Terminal failure | Error with safe navigation | Failed store/subsystem stays visible | Prioritized case | Reconcile/manual route | Stable Mode 1 or failed refresh + Retry |
| Unknown/stale | No fabricated zero | Explicit unknown/stale row | Unknown evidence case | Missing/dead run recoverable | Stale/missing scan recovery action |
| Permission denied | No leaked counts | Rule-safe unavailable region | No foreign cases | No unauthorized action | Configuration hidden/denied server-side |

## 10. Visible-action consequence copy

| Action | Classification displayed before execution |
| --- | --- |
| Dashboard Refresh | Reads Odoo connector evidence; does not contact Shopify |
| Refresh Shopify locations | Queues a background Shopify read for this store |
| Confirm Mode 2 | Queues a Shopify reconciliation read; effective mode remains Mode 1 until it passes |
| Retry run | Queues another attempt only when the failure class permits it |
| Reconcile / Verify | Reads Shopify to resolve an ambiguous or stale outcome before any mutation retry |
| Cancel run | Stops eligible queued work locally; states what remains incomplete; audited reason required where governed |
| Export confirm | Mutates Shopify after preview; Administrator-only no-JS route includes the same diff summary and audit line |
| Activate store | Writes Odoo configuration state; allowed only after all enabled-domain readiness gates pass |
