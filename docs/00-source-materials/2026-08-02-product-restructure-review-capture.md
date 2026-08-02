# Source Capture — Adams Odoo↔Shopify Complete Product, UX, Architecture & Rebuild Decision Review (2026-08-02)

> **Provenance.** Received 2026-08-02 from the product owner as
> `Adams_Odoo_Shopify_Product_and_Restructure_Review.docx`, produced by the
> ChatGPT 5.6 control room as a read-only assessment of the governed candidate
> `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` (PR #204 head) and the
> experimental UI branch `codex/wave-5-premium-ui-revamp` @
> `067ba238066a33fe19c3661080613a1b73b9d809`. Captured under CLAUDE.md §7
> ("capture, don't just link") because this document is a decision input that
> otherwise exists only as a chat attachment. Converted DOCX → Markdown with a
> stdlib XML extractor (paragraphs + tables; wireframe tables flatten to
> single rows); wording unchanged. Classification per CLAUDE.md §8: the whole
> document is **control-room review input** — its verdicts are the reviewer's
> recommendations/inferences, not accepted decisions, until the product owner
> signs the structure/design decision it requests.
>
> Independent verification of its load-bearing claims against the exact head
> `49cfffbd…` is recorded in
> [`../02-product/ui-restructure-design-contract-2026-08-02.md`](../02-product/ui-restructure-design-contract-2026-08-02.md) §2.

---

ADAMS ODOO 19 ↔ SHOPIFY


# Complete Product, UX,
Architecture & Rebuild
Decision Review

Read-only assessment • Current candidate, experimental UI branch, competitors, target operating model, scorecard and migration gates

| DECISION IN ONE LINE / Approve Option D: preserve the connector’s integrity-critical backend contracts and domain modules, selectively refactor aggregation/configuration seams, and rebuild the navigation, operating workflows, dashboard, setup, recovery and reporting surfaces as one coherent product. |
|---|

| Prepared for | Mostafa — structure and design decision |
|---|---|
| Review date | 02 August 2026 |
| Repository | AdamsOdoo/Adams (private; read-only review) |
| Governed candidate | 49cfffbd5ff0eca85d2b855d9ebd2e414680af8e |
| Experimental UI head | 067ba238066a33fe19c3661080613a1b73b9d809 |

No implementation was started. No repository, pull request, branch, Odoo.sh database/build, Shopify store or external system was changed.


# 1. Executive verdict

| VERDICT / This is not a failed connector that needs a backend rewrite. It is a technically strong integration platform whose operator-facing product structure has grown around implementation domains, exception models and delivery waves. The correct move is a governed hybrid rebuild: retain proven data, job, identity, retry, reconciliation and mutation-safety contracts; rebuild the product shell and selectively refactor the read/aggregation layer that feeds it. |
|---|

| Question | Answer |
|---|---|
| Is the backend salvageable? | Yes. The source shows strong modular boundaries, store/company scoping, explicit job states, idempotency and mutation-outcome evidence, guarded lifecycle transitions, reconciliation and test infrastructure. |
| Is the current candidate product-ready? | No. PR #204 remains draft; exact-head native Odoo.sh qualification and independent correction review are still open. The current UI is structurally fragmented. |
| Is the experimental UI branch the final answer? | No. It is a useful direction and improves the top-level hierarchy, but it is self-authored, unqualified on Odoo.sh, and still carries technical naming, scattered review/recovery surfaces and an overloaded overview. |
| Recommended option | Option D — hybrid: backend contracts retained, selected service/config seams refactored, shell/IA/workflows substantially rebuilt. |
| Decision confidence | High on product/architecture direction; medium on exact screen/control completeness until exact-head runtime access and complete checkout are available. |


## Decision gates

Approve the target operating model and menu hierarchy before authorizing UI implementation.

Do not merge or declare the current candidate qualified until exact SHA 49cfffbd… is installed and passes native Odoo.sh evidence review.

Do not treat experimental head 067ba238… as accepted merely because its static inventory is extensive; require exact-head runtime, independent UX/control audit, accessibility/responsiveness review and browser evidence.

Protect the existing integrity contracts during redesign: job state transitions, idempotency keys, mutation evidence, store/company scope, reconciliation, first-push controls and preview-first export safeguards.


# 2. Preflight, scope and evidence boundary

| Evidence item | Observed result | Decision impact |
|---|---|---|
| Repository | AdamsOdoo/Adams is accessible through the connected GitHub app; default branch main. No local checkout exists in this workspace. | Static inspection is evidence-backed but cannot claim a complete filesystem inventory, local tests or worktree cleanliness. |
| PR #204 | Open, draft, mergeable; head fable/wave-5-completion at 49cfffbd…; base mvp/program-integration. | This is a governed candidate, not a production-qualified release. |
| GitHub Actions | Run 30715082576 succeeded for 49cfffbd…; Odoo 19 install and connector suite job completed successfully. | Strong CI signal, but not a substitute for native Odoo.sh qualification. |
| Native Odoo.sh | PR body explicitly says exact head 49cfffbd… was not run on Odoo.sh. A historical predecessor a1c593… has reported native evidence. The known old build URL currently returns 502. | Exact runtime review is blocked. Qualification must remain open. |
| Experimental branch | codex/wave-5-premium-ui-revamp at 067ba238… is four commits ahead of the candidate and changes 45 files across menus, dashboard/setup UI, views, styles and tests. | Useful design evidence; not accepted implementation. |
| Internal R5 reference | The requested Google Doc/export was not available in the provided materials. | Any requirement unique to that document remains a traceability gap. |
| External systems | No Odoo.sh, Shopify or external admin mutation was attempted. | Review is decision material only. |

| CONSOLIDATED EVIDENCE REQUEST / Provide read-only exact-head Odoo.sh build URLs/access for 49cfffbd… and 067ba238…, a complete authenticated checkout of AdamsOdoo/Adams, and the internal R5 document/export. Those items are sufficient to close runtime screenshots, exhaustive control enumeration and requirements traceability without changing product data. |
|---|


# 3. Existing strengths worth preserving

| Strength | Why it matters |
|---|---|
| Modular architecture | Six installed connector modules isolate core, product, sale, inventory, fulfillment and product export risk. Product export is deliberately separate from import. |
| Store/company boundary | Store is the scoping anchor; related company fields and rules support multi-company isolation. |
| Explicit lifecycle | Store states include Setup Incomplete, Connected, Reconnect Needed, Disconnecting and Disconnected, with guarded two-phase disconnect semantics. |
| Operational substrate | A durable job model supports queued/running/retry/manual-review/terminal states, explicit legal transitions, ownership and retry metadata. |
| Mutation safety | Remote mutation attempts store intent fingerprints, idempotency evidence, observed outcomes, reconciliation evidence and manual resolution disposition. |
| Recovery mechanisms | Retries, reconciliation, reconnect/backfill, resume, release and review actions are real product capabilities—not only logs. |
| Domain safety | First stock push, fulfillment review/mode change, tax/matching gates and preview-first export reduce destructive or ambiguous writes. |
| Testing discipline | The PR and branch include broad model/tour/browser/test assets. GitHub Actions passes at the governed candidate SHA. |
| Native Odoo leverage | Most operational surfaces use native actions, list/form/graph/pivot views and Owl only where a richer shell is justified. |

Architecture implication: redesign above these contracts. A full backend rewrite would discard the connector’s most expensive and differentiating work while reintroducing consistency, idempotency and migration risk.


# 4. What is structurally wrong

| Structural issue | Observed consequence |
|---|---|
| Information architecture follows implementation history | Top-level destinations mix stores, operations, configuration, error handling, analysis and logs. Operators must know internal nouns before they can act. |
| Attention work is fragmented | Error & Review Center, match decisions, tax mapping, fulfillment reviews, export diagnostics, first-push guard and mutation evidence are separate queues. |
| Configuration has multiple doors | Stores, canonical Store Settings, Export Settings, Fulfillment Settings and Setup all own or expose related choices. Canonical storage exists, but canonical experience does not. |
| Technical vocabulary leaks | Mutation Evidence, job types, retry internals, manual review subreason and generic Sync Center expose implementation concepts without translating consequence or next action. |
| Overview is overloaded | Store 360 combines sales KPIs, lifecycle exceptions, COD/payment/fulfillment snapshots, connector health, recent activity and store management. |
| Reporting is thin and misplaced | A generic Sync Operations Analysis plus logs cannot answer domain reliability, business activity, freshness and reconciliation questions cleanly. |
| Recovery is powerful but scattered | Retry, release, resolve, resume, reconnect/backfill, remap and withdrawal actions lack one governed recovery model and consistent consequence language. |
| Risky bypass is visible | “Confirm without the review screen” weakens the preview-first product-export posture; if retained at all, it belongs in restricted break-glass recovery. |
| Setup is a backend checklist | Twelve sequential steps are durable and thoughtful, but presented as equal steps rather than a short merchant journey grouped by connection, policy, mappings and readiness. |


# 5. Current navigation and workflow assessment

| Current branch | What it currently contains | Disposition |
|---|---|---|
| Dashboard | Sales, lifecycle, connector health, activity, stores | Rewrite as Overview; split detailed health and reports. |
| Orders | Orders Workspace; COD Reconciliation | Keep domain, clarify state/actions and route exceptions to unified attention. |
| Stores | Connection lifecycle and setup entry | Move to Configuration › Stores & Connections. |
| Sync Center | Cross-domain jobs, retry/release/cancel/logs | Replace generic queue-first entry with Runs & Recovery and Needs Attention. |
| Catalog & Matching | Product, variant and customer matching | Separate Products and Customers; surface unresolved cases through Needs Attention. |
| Inventory | Workspace, first-push guard, location mapping/actions | Keep daily inventory under Operations; mappings under Configuration. |
| Export | Previews, media, reconnect/backfill, settings, diagnostics | Move settings to Configuration; previews/media under Products; failures/recovery to Needs Attention. |
| Fulfillment | Review workspace, records, jobs, settings | Keep operations and review; move settings to Configuration. |
| Error & Review Center | Job review plus mutation evidence | Replace with human-oriented Needs Attention and restricted audit detail. |
| Sync Operations Analysis | Graph/pivot/list/form on jobs | Evolve into domain and reliability reports. |
| Logs | Technical evidence | Move to Reporting › Activity & Audit; admin/debug detail only. |


## Experimental IA: useful direction, not final structure

The experimental branch consolidates the product under Overview, Operations, Reporting and Configuration, nests connections/rules/locations, improves setup grouping and corrects dashboard truth handling. That direction should be retained. It remains incomplete because technical leaves (“Mutation Evidence”), generic recovery (“Reconnect and Backfill”), a mixed Product/Customer matching area, a thin Reporting branch and an overloaded store overview persist. Its own static audit counts 44 menus, 45 actions, 70 native buttons and 41 Owl buttons; those are coverage claims, not runtime usability proof.


# 6. Competitor evidence atlas and synthesis

| Competitor / evidence | Observed product/UI pattern | Classification | What Adams should learn |
|---|---|---|---|
| Emipro Odoo 19 listing + v17 docs/dashboard image | Long-running broad connector; dashboard/top navigation; operations, logs, reporting, configuration; rich business KPIs. | Current vendor listing + historical presentation evidence. Vendor claims not independently verified. | Match breadth and explicit reports, but avoid KPI-heavy dashboards that hide operational health. |
| VentorTech PRO + current Odoo 19 migration docs | Initial import/automapping, product/stock/price/order/tracking flows, job queues and error logs; operationally technical configuration. | Current vendor documentation/claims. | Preserve queue rigor but translate workers/jobs into operator outcomes. |
| Webkul Shopify app + Multichannel docs | Central home/config/products/collections/customers, mapping tables, staged feeds and sync history. Public reviews are mixed. | Current app listing/reviews + historical/current vendor guides. | Clear mapping and sync-history tables help; avoid fragmented credentials and feed jargon. |
| TeqStars Odoo 19 docs | Marketplaces hierarchy, instance configuration, listings, operations, queues/logs, automated jobs, webhooks and reports; tab-heavy setup. | Current vendor docs and some historical screenshots. | Strong breadth and domain separation; simplify dense instance configuration. |
| ecommerce_shopify Odoo 19 listing | Odoo-native connector, GraphQL/OAuth claims, scheduled/manual cadences across orders, inventory and fulfillment. | Current vendor listing; not independently run. | Make cadence/freshness explicit, but never label queue/cron behavior as real-time without measured evidence. |
| Softhealer Odoo 19 listing | Very broad instance tabs, queue dashboard, integration hub, manual/cron/webhook options. | Current vendor listing/claims. | Breadth is not structure. Resist giant tab sets and cross-module prerequisites in the primary journey. |


## Cross-market findings

Feature parity is table stakes: products, orders, stock, customers and fulfillment are widely claimed. Adams should lead on trust, evidence, guarded recovery and transparent state—not more switches.

The best competitor patterns are centralized operation launch, visible mappings, sync history, instance status and domain reports.

Common weaknesses are configuration overload, raw scheduler/queue exposure, marketing dashboards, blind mappings, email-only failure handling and recovery that depends on technical staff.

No reviewed competitor documentation clearly demonstrates Adams-level mutation-outcome evidence, first-push governance and reconciliation discipline as a coherent operator product. That is the differentiator to surface.


# 7. Future operating model

| OPERATING PROMISE / An operator should always be able to answer four questions without understanding connector internals: Is the connection safe? Is data current? What needs attention? What happens if I act? |
|---|

| Operator intent | Primary surface | System response |
|---|---|---|
| See whether the connector is safe | Overview + Connector Health | Separate connection/auth/scopes/API/scheduler/webhook/queue/throttle/freshness/reconciliation signals. |
| Run or monitor daily work | Operations by business domain | Orders, products, customers, inventory and fulfillment use business states; background work is visible but not dominant. |
| Resolve problems | Needs Attention | One prioritized inbox routes each item to a domain-aware resolution flow with consequence, evidence and rollback/recovery. |
| Understand performance | Reporting | Business volume, sync freshness, success/failure/retry, backlog, duration, reconciliation and audit are separated. |
| Change policy | Configuration | One store selector and canonical configuration model; progressive disclosure; impact preview before save. |
| Connect a store | Setup | Short grouped journey: connect → choose policies → map essentials → readiness → activate. |


# 8. Future menu hierarchy

| Level 1 | Level 2 | Level 3 / tabs | Primary persona |
|---|---|---|---|
| Overview | Store Overview | Health summary • Freshness • Needs Attention • Recent business activity • Next actions | Operator / manager |
| Operations | Needs Attention | All • Orders • Products • Customers • Inventory • Fulfillment • Connection | Operator / admin |
| Operations | Orders | All Shopify Orders • COD Reconciliation | Sales ops / finance |
| Operations | Products | Product Sync • Product Matching • Variant Matching • Export Previews • Exported Media | Catalog ops |
| Operations | Customers | Customer Matching | Sales ops |
| Operations | Inventory | Inventory Levels • First Stock Push | Warehouse ops |
| Operations | Fulfillment | Fulfillments • Reviews | Warehouse ops |
| Operations | Runs & Recovery | Current & Scheduled Runs • Failed/Blocked Runs • Reconnect & Backfill | Admin / support |
| Reporting | Sales & Orders | Volume • value • lifecycle • COD | Manager / finance |
| Reporting | Sync Reliability | Success • retry • failure • duration • backlog • throttle | Admin / support |
| Reporting | Domain Reports | Products • Inventory • Fulfillment | Domain owners |
| Reporting | Activity & Audit | User actions • state changes • evidence • redacted logs | Admin / audit |
| Configuration | Stores & Connections | Identity • credentials status • scopes • API version • lifecycle | Admin |
| Configuration | Sync Rules | Products • Orders & Customers • Inventory • Fulfillment | Admin / domain owner |
| Configuration | Mappings | Locations • Taxes • Payment gateways • durable bindings | Admin / finance |
| Configuration | Scheduling & Notifications | Cadence • freshness expectations • alerts | Admin |
| Configuration | Access & Advanced | Roles • retention • diagnostics • break-glass actions | Admin only |

Rule: no technical record name becomes a navigation label. “Mutation Evidence” is an audit detail reached from a recovery case, not a top-level destination. “Job” becomes “run” in operator-facing copy. Internal state and IDs remain available to support/admin users.


# 9. Connector Health versus Sales Operations

| Connector Health | Sales Operations |
|---|---|
| Connection identity, credential presence/verification, granted scopes, API version support | Orders imported, order value, payment/COD state, customer/product linkage |
| Scheduler/webhook heartbeat, queue progress, throttle headroom, last successful run | Product/import/export activity, stock changes, fulfillments and exceptions |
| Freshness by domain and expected cadence; stale/unknown reasons | Business outcomes and operational workload |
| Retry/failure/blocked backlog, oldest blocked age, reconciliation pending/uncertain | Domain-specific matching, configuration and validation cases |
| Health state: Healthy / Attention / Critical / Unknown | Business state: Draft / Ready / Imported / Matched / Fulfilled / etc. |

| DESIGN RULE / A store with zero sales can be perfectly healthy. A store with high sales can be critically unhealthy. Never infer connector health from transaction counts or a green connection badge alone. |
|---|


# 10. Configuration model

| Configuration area | Canonical source | Presentation rule |
|---|---|---|
| Store & connection | shopify.connector.store plus credential service status mirrors | Show identity and lifecycle; never display or re-emit secret values. |
| Domain enablement and sources of truth | shopify.connector.store.settings extended by domain modules | One page with four domain sections, impact summary and unsaved-change warning. |
| Products | Canonical store settings extension | Import/export direction, media refresh, attribute conflict, match-first behavior. |
| Orders & customers | Canonical store settings extension | Schedule/import window, confirmation, manual payment gateway policy, company/pricelist/team/fallbacks. |
| Inventory | Canonical settings + location mapping models | Cadence and source policy separate from location mappings and first-push decisions. |
| Fulfillment | Canonical settings + mode-switch wizard | Mode change is an explicit governed transition with impact preview. |
| Export | Canonical settings extension + diagnostics/reconciliation evidence | Normal policies in Sync Rules; diagnostics and checksum acknowledgement in Advanced/Recovery. |
| Retention/advanced | Core settings and evidence models | Admin only; plain-language risk and redaction behavior. |

Configuration should be a write surface with consequence-aware save. Setup should write the same canonical records and never create a parallel source of truth. Operational matching cases are not configuration even when they create durable bindings.


# 11. Reporting model

| Report | Minimum dimensions | Core measures | Not included |
|---|---|---|---|
| Sales & Orders | Store, company, date, channel status, payment/COD | Orders, value, imported/confirmed/cancelled, age | Connection health |
| Products | Store, action, product/variant, direction | Imported/exported/matched/blocked, duration | Raw mutation payloads |
| Inventory | Store, location, product, direction | Updates, verification, first-push status, stale age | Location setup controls |
| Fulfillment | Store, carrier, mode, state | Imported/exported/reviewed/blocked, notification outcome | Mode configuration |
| Sync Reliability | Store, domain, run type, trigger, error class | Success rate, retry rate, final failures, blocked backlog, p50/p95 duration, throttle deferrals | Sales KPI interpretation |
| Activity & Audit | User/system, action, state change, record, date | Configuration/lifecycle/recovery actions and evidence references | Unredacted secrets/PII |


# 12. Setup redesign

| Phase | Steps | Completion outcome |
|---|---|---|
| 1 — Connect | Store identity • credential entry • read-only connection test • scope check | Identity verified; missing scopes explained; secret never redisplayed. |
| 2 — Choose operating policy | Domains enabled • direction/source of truth • notification defaults | Policy summary written to canonical settings. |
| 3 — Map essentials | Locations • taxes/payment gates if order import enabled | Blocking mappings resolved or explicitly deferred with consequences. |
| 4 — Prepare first activity | First stock push decision • product/order readiness checks | High-risk initial actions require preview and accountable confirmation. |
| 5 — Review and activate | Readiness results • warnings • impact summary • activation | Connected and routed to Overview with next steps. |

Keep durable checkpointing and “save & exit”; compress twelve backend steps into five merchant phases.

Let users re-run setup through Configuration, but label it “Review connection setup” and preserve existing decisions.

Activation is unavailable until identity, credential, mandatory scopes and readiness checks pass; warnings distinguish blocking from advisory.

After completion, primary actions are Go to Overview, Review Settings and Resolve remaining mappings—not “start again.”


# 13. Overview / dashboard redesign

| Order | Section | Content |
|---|---|---|
| 1 | Store context | Selected store, connection state, health and last evaluated time. |
| 2 | Health strip | Connection • scopes • scheduler/webhooks • queue • freshness • reconciliation. Every status links to explanation. |
| 3 | Needs Attention | Count by severity/domain, oldest age, top three cases, “Open inbox”. |
| 4 | Freshness by domain | Orders/products/inventory/fulfillment last success versus expected cadence; Current/Delayed/Stale/Unknown. |
| 5 | Business activity | Compact daily/weekly orders, product changes, stock updates, fulfillments—no health inference. |
| 6 | Recent runs and activity | Last runs, configuration/lifecycle changes and accountable user/system source. |
| 7 | Next best action | Setup completion, reconnect, resolve blocking mapping, verify first push or review export. |


# 14. Target screen catalogue

| Screen | Purpose | Primary user | Core content |
|---|---|---|---|
| Overview | Cross-domain decision cockpit | Operator / manager | Health, freshness, attention, activity, next action |
| Connector Health | Explain readiness and degradation | Admin / support | Connection, scopes, API, scheduler/webhooks, queue, throttle, reconciliation |
| Needs Attention | Prioritized unified resolution inbox | Operator / admin | Severity, domain, impact, owner, age, recommended action |
| Attention Case | Resolve one issue safely | Domain owner / admin | Plain-language cause, affected records, evidence, consequences, resolution |
| Orders | Operate imported Shopify orders | Sales ops | Shopify/Odoo references, business/import states, refresh, exceptions |
| COD Reconciliation | Close COD mismatches | Finance | Expected/received, status, evidence, action |
| Product Sync | Monitor product import/export | Catalog ops | Direction, binding, last sync, state, issue |
| Product/Variant Matching | Create safe durable matches | Catalog ops | Candidates, confidence/evidence, preview, confirm |
| Export Preview | Approve product export intent | Catalog owner | Field/media diff, warnings, target identity, confirm/cancel |
| Inventory Levels | Monitor stock synchronization | Warehouse ops | Location/product, Odoo/Shopify values, freshness, verification |
| First Stock Push | Govern initial destructive stock write | Warehouse manager | Scope, values, consequence, confirm/verify/withdraw |
| Fulfillment | Track fulfillment exchange | Warehouse ops | Delivery/tracking/shopify state, notification, exception |
| Fulfillment Review | Resolve ambiguous/blocked fulfillment | Warehouse manager | Proposed action, evidence, destination, consequences |
| Runs & Recovery | Monitor background work and recover | Admin / support | Run, domain, trigger, progress, retry/reconcile state |
| Reports | Analyze business and reliability | Manager / admin | Domain tabs, filters, measures, exports |
| Stores & Connections | Manage store lifecycle | Admin | Identity, credential status, scopes, API, state, test/reconnect/disconnect |
| Sync Rules | Set domain policy | Admin / domain owner | Four domain sections, cadence, source, impact preview |
| Mappings | Manage durable setup mappings | Admin / finance | Locations, taxes, gateways, bindings |
| Activity & Audit | Trace accountable changes and evidence | Admin / auditor | Actor, action, before/after, record, evidence reference |


# 15. Key wireframes

Overview

One safe starting point for daily operation.

| Overview / Healthy • evaluated 10:42 / Needs attention 7 / Orders current / Inventory delayed / Last run 4m ago / Today / Orders / Products / Inventory / Fulfillment / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Open Needs Attention  •  View Health |
|---|

Design note: Health and business activity are visually distinct; every degraded signal has an explanation link.

Connector Health

Explain whether each connector subsystem is ready.

| Connector Health / Attention • inventory stale / Connection healthy / Scopes complete / Queue progressing / Reconciliation clear / Health checks / Signal / State / Last checked / Why / next action / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Re-test connection  •  Open affected runs |
|---|

Design note: No aggregate green state can hide an unknown or critical subsystem.

Needs Attention

One priority-ordered inbox across domains.

| Needs Attention / 7 open • oldest 2h / Critical 1 / High 2 / Normal 4 / Open cases / Impact / Domain / Issue / Age / Owner / Action / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Assign  •  Open case  •  Resolve selected |
|---|

Design note: Bulk actions appear only when consequences are homogeneous and server-side guards still apply.

Attention Case

Give one issue a complete, accountable resolution path.

| Attention Case / Blocked • duplicate risk / Affected 3 orders / Retry unsafe / Evidence complete / Resolution / Cause / Evidence / Recommended choice / Consequence / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Confirm match  •  Mark not applied  •  Cancel |
|---|

Design note: Technical evidence is expandable; the default view speaks in business impact and next action.

Orders

Operate Shopify order imports without queue jargon.

| Orders / Current • last success 10:38 / Imported today 42 / Needs review 3 / COD open 5 / Shopify orders / Order / Customer / Payment / Import state / Odoo order / Updated / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Refresh selected  •  Open COD  •  Open issue |
|---|

Design note: Refresh states exactly whether it reads Shopify, queues work, and can create/update records.

Product Matching

Create safe product and variant bindings.

| Product Matching / 12 unmatched / Exact SKU 7 / Multiple candidates 3 / No candidate 2 / Candidate comparison / Shopify item / Odoo candidate / Evidence / Conflict / Choice / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Match & resume  •  Create new product  •  Skip |
|---|

Design note: Selection never silently resumes destructive work; confirmation states which queued operation will continue.

Export Preview

Make outbound product mutation intent reviewable.

| Export Preview / Preview ready • 2 warnings / Fields changed 8 / Media added 4 / Variants 3 / Before / after / Field / Odoo value / Shopify value / Result / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Confirm export  •  Edit policy  •  Cancel |
|---|

Design note: Remove the normal “confirm without review” bypass; any break-glass route is admin-only and audited.

Inventory Levels

Show values, location mapping and freshness together.

| Inventory Levels / Delayed • last success 09:55 / Mapped 1,204 / Mismatch 9 / Unmapped 2 / Inventory / Product / Location / Odoo / Shopify / Freshness / State / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Verify selected  •  Open mappings  •  Open issue |
|---|

Design note: Mismatches are not automatically errors; direction/source policy determines expected value.

First Stock Push

Govern the first high-impact inventory write.

| First Stock Push / Awaiting approval / Locations 2 / Variants 1,204 / Estimated changes 118 / Impact preview / Scope / Current Shopify / Proposed Odoo / Difference / Risk / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Confirm first push  •  Withdraw  •  Export preview |
|---|

Design note: Confirmation names scope and irreversibility; verify is a separate post-write read.

Fulfillment Review

Resolve fulfillment ambiguity without duplicating shipment.

| Fulfillment Review / Blocked • notification unclear / Delivery WH/OUT/0042 / Tracking present / Shopify open / Proposed fulfillment / Destination / Tracking / Notification / Evidence / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Validate proposed fulfillment  •  Acknowledge outside Odoo  •  Cancel |
|---|

Design note: Each option states whether Shopify is mutated, whether customer notification is sent and what record becomes authoritative.

Runs & Recovery

Expose background work as understandable runs.

| Runs & Recovery / 3 active • 2 retrying / Running 3 / Retry scheduled 2 / Blocked 4 / Failed final 1 / Recent runs / Domain / Purpose / Trigger / State / Progress / Next step / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Retry eligible  •  Reconcile uncertain  •  Cancel queued |
|---|

Design note: Operator names use “run”; internal job IDs and leases remain in advanced details.

Sales & Reliability Reports

Separate business outcomes from connector behavior.

| Sales & Reliability Reports / Last 30 days / Orders 1,248 / Success 99.2% / p95 4m / Blocked 7 / Trend / breakdown / Date / Domain / Volume / Success / Retry / Duration / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Change filters  •  Export data |
|---|

Design note: A tab switch changes the semantic model; health and sales metrics are never mixed in one score.

Stores & Connections

Manage identity and lifecycle safely.

| Stores & Connections / Connected • scopes complete / Credential verified / API 2026-07 / Generation 4 / Connection details / Store / Company / Identity / State / Scopes / Last test / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Test connection  •  Reconnect  •  Disconnect |
|---|

Design note: Reconnect/disconnect previews explain quiescence, queued-work impact and required reactivation steps.

Sync Rules

Configure domains through one canonical surface.

| Sync Rules / Unsaved changes / Products enabled / Orders enabled / Inventory enabled / Fulfillment review / Domain policy / Domain / Direction/source / Cadence / Safety gate / Impact / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Primary content / record values / state explanation / Actions: Review changes  •  Save settings  •  Discard |
|---|

Design note: Save opens an impact summary when choices affect queued work, mappings or first-push readiness.


# 16. Workflow catalogue

| Workflow | Entry point | System consequence | Failure / recovery |
|---|---|---|---|
| Connect store | Configuration › Stores & Connections › Add store | Read-only identity/scope test, save canonical store/settings, readiness checks | Fix credential/domain/scope; test again; no activation on block |
| Re-run setup | Store actions › Review connection setup | Loads current canonical choices; writes only explicit changes | Save & exit preserves progress; no duplicate settings row |
| Reconnect | Connection state Reconnect Needed | Credential replacement/identity verification; connection generation advances; safe work resumes | Mismatch stays blocked and routes to Needs Attention |
| Disconnect | Store lifecycle action | Stops new business work, waits for admitted work, records completion/timeout, then disconnects | Timeout becomes critical case; no silent cancellation |
| Import products | Operations › Products › Run import | Queues read/import run; binding/matching gates determine continuation | Ambiguous items become matching cases; retry only safe failures |
| Match product | Product Matching or Needs Attention | Creates durable binding, resumes named blocked run after confirmation | Conflict remains blocked with evidence |
| Match variant | Variant Matching | Creates variant binding scoped to store/company | Duplicate/binding conflict cannot be overridden casually |
| Import media | Product sync policy/run | Reads remote media and applies configured refresh mode | Bad/unsupported media isolated; product import result remains explainable |
| Preview product export | Products › Export Previews | Dry-run builds target-specific field/media diff without mutation | Configuration or identity warnings block confirmation |
| Confirm product export | Approved preview | Queues idempotent mutation with attempt evidence | Uncertain outcome reconciles before retry |
| Resume media export | Exported Media case | Continues append-only media work from stored evidence | Missing identity/checksum becomes recovery case |
| Import orders | Operations › Orders › Run import/schedule | Reads orders in configured window; customer/product/tax/payment policies applied | Missing configuration or ambiguous binding becomes domain case |
| Refresh one order | Order record action | Reads Shopify and queues/update path for that order | UI states whether Odoo order may change; no blind duplicate |
| Approve manual-paid order | Order attention case | Applies configured manual gateway policy and continues import | Approval expires or remains blocked if evidence changes |
| Resolve tax mapping | Needs Attention › Orders | Creates tax mapping and resumes affected order run | Invalid mapping blocks; preview lists affected orders |
| Match customer | Customers › Matching | Creates durable customer binding and resumes import | Conflicts remain blocked; no merge implied unless separately approved |
| COD reconciliation | Operations › Orders › COD | Records/derives reconciliation state against Odoo payment/accounting evidence | Mismatch remains open with accountable action |
| Refresh locations | Configuration › Mappings › Locations | Reads Shopify locations; does not map automatically | Auth/scope failure becomes connection case |
| Map location | Location mapping | Creates or changes store-to-Odoo location binding | Impact preview identifies inventory runs affected |
| First stock push | Operations › Inventory › First Stock Push | Queues approved initial inventory mutations and records decisions | May withdraw before execution; uncertain writes reconcile |
| Verify inventory | Inventory action | Read-back compares expected and remote stock | Mismatch opens case; does not automatically overwrite |
| Withdraw first-push decision | First Stock Push action | Revokes pending approval where work has not executed | Executed mutations are not rolled back silently |
| Import tracking | Fulfillment Review | Reads Odoo delivery/tracking and creates proposed fulfillment path | Missing/ambiguous tracking remains blocked |
| Validate fulfillment | Fulfillment Review | Queues guarded Shopify fulfillment mutation with notification choice | Uncertain outcome reconciles before another mutation |
| Acknowledge outside Odoo | Fulfillment Review alternative | Records authoritative external completion without duplicate remote write | Requires reason/evidence and audit entry |
| Switch fulfillment mode | Configuration › Sync Rules › Fulfillment | Wizard previews queued-work and responsibility changes | Blocked until impact accepted; reversible through governed wizard |
| Retry run | Runs & Recovery or attention case | Server validates eligibility and transitions to queued | Ineligible/uncertain mutation requires reconciliation, not retry |
| Resolve mutation outcome | Attention Case › advanced evidence | Admin records Applied or Not Applied with reason/evidence | Audit is immutable; resolution drives safe continuation |
| Reconnect and backfill | Runs & Recovery | Re-establishes bindings/evidence and queues bounded backfill | Scope/date/domain preview required; partial progress remains restartable |


# 17. Control register and consequence rules

| Control | Execution | Consequence | Enablement | Feedback / recovery |
|---|---|---|---|---|
| Test connection | Immediate read | Tests identity/scopes; no mutation | Enabled with domain + unsaved credential | Shows tested identity, scope gaps and timestamp |
| Activate | Immediate governed transition | Allows business jobs after readiness | Only all blocking checks pass | Routes to Overview; warns advisory gaps |
| Reconnect | Wizard + background consequences | Replaces credential and may advance generation | Reconnect Needed / admin | Identity mismatch blocks; queued work stays gated |
| Disconnect | Wizard + background quiescence | Stops admission and waits for holders | Connected / admin | Shows timeout escalation and final state |
| Run import | Background run | Reads Shopify and creates/updates Odoo per policy | Domain enabled + connected | Shows scope, cadence and case routing |
| Refresh order | Background record run | May update/create linked Odoo records | Known Shopify order + connected | Lists affected order and policy |
| Match & resume | Immediate binding + background resume | Creates binding and resumes named run | Single valid candidate + permission | Displays conflict/duplicate guard outcome |
| Confirm export | Background remote mutation | Writes reviewed product intent to Shopify | Current valid preview + safety checks | Diff, store, identity, idempotency/recovery |
| Confirm without review | Break-glass only or remove | Remote mutation without standard review | Admin, incident reference, explicit policy | Strong warning + mandatory audit; absent in normal UI |
| Refresh locations | Immediate read/background | Reads Shopify locations only | Connected + scopes | No mappings changed automatically |
| Map/remap location | Immediate configuration write | Changes inventory routing | Admin + valid Odoo location | Impact preview and affected pending runs |
| Confirm first push | Background remote mutation | Writes initial inventory values | Approved preview + mapping completeness | Scope/count/risk; post-write verify |
| Withdraw | Immediate approval change | Cancels unexecuted first-push authorization | Pending only | Executed work unaffected |
| Verify now | Background read-back | Compares remote/current values | Connected + mapping | No automatic overwrite |
| Validate fulfillment | Background remote mutation | Creates/updates fulfillment; may notify customer | Evidence complete + mode allows | Shows notification and duplication risk |
| Acknowledge outside Odoo | Immediate resolution | Closes case without remote mutation | Reason/evidence required | Audit record and authoritative source stated |
| Switch mode | Wizard configuration transition | Changes future fulfillment responsibility | Admin; no unresolved incompatible work | Queued-work impact and rollback route |
| Retry | Immediate state transition then background | Requeues only retry-safe work | Server says eligible | Uncertain mutations route to reconcile |
| Resolve mutation | Immediate restricted resolution | Records Applied/Not Applied and unlocks safe path | Admin + evidence + reason | Immutable audit and downstream consequence |
| Save settings | Immediate canonical write | Changes domain policy/cadence/source | Validated values + permission | Impact summary for pending work/mappings/readiness |

Control standard: every visible action must disclose whether it is a read, configuration write, local business-record write, remote Shopify mutation or queued background run. Destructive/uncertain remote actions require preview, accountable confirmation, idempotency/reconciliation evidence and a documented recovery path.


# 18. Terminology and state vocabulary

| Internal/current term | Operator-facing term | Guidance |
|---|---|---|
| Job | Run | Keep “job” in technical details, logs and developer documentation. |
| Blocked — Manual Review | Needs attention | Show domain-specific cause: matching required, configuration missing, outcome uncertain, etc. |
| Mutation Evidence | Remote write evidence | Expandable within a recovery case; restricted by role. |
| Sync Center | Runs & Recovery | Purpose and next action over generic mechanics. |
| Reconnect and Backfill | Reconnect & restore history | Wizard names domains, date range, effect and partial-progress behavior. |
| Failed (Retryable) | Retry available | Explain when retry happens automatically versus requires operator action. |
| Failed (Final) | Action required | State why automatic retry stopped. |
| Setup Incomplete | Setup in progress | Show phase and next blocking step. |

| State family | Approved vocabulary |
|---|---|
| Store lifecycle | Setup in progress • Connected • Reconnect required • Disconnecting • Disconnected |
| Health | Healthy • Attention • Critical • Unknown |
| Freshness | Current • Delayed • Stale • Unknown |
| Run | Draft • Queued • Running • Retry scheduled • Needs attention • Succeeded • Failed • Skipped • Cancelled |
| Remote write outcome | Pending • Succeeded • Failed cleanly • Outcome uncertain • Resolved applied • Resolved not applied |
| Setup | Not started • In progress • Checks required • Ready to activate • Complete |


# 19. Component disposition

| Component | Decision | Rationale / scope |
|---|---|---|
| Store/company/credential models | Keep; relabel surface | Integrity boundary and secret separation are strong. Rebuild connection experience around them. |
| Job state machine and dispatcher | Keep behind new Runs/Attention UI | Preserve legal transitions, retry ownership and serialization. |
| Mutation attempt/evidence | Keep; restrict and translate | Core differentiator for safe recovery. Surface business meaning first. |
| Product/order/inventory/fulfillment domain models | Keep; refactor views | Domain logic is substantive; normalize states, actions, help and cross-links. |
| Canonical Store Settings | Keep and strengthen | Make it the only configuration write surface; remove duplicate presentation routes. |
| Setup backend checkpoints | Keep | Durable resume/re-run is valuable; rewrite phase presentation. |
| Dashboard service/Owl client | Substantial refactor | Split health, attention, freshness and business aggregates; simplify target navigation. |
| Menu/action XML | Rewrite | Implement approved hierarchy and eliminate technical top-level destinations. |
| Native list/form/search views | Refactor selectively | Preserve Odoo ergonomics while standardizing labels, filters, status, help and action placement. |
| Export bypass control | Remove from normal UI | Conflicts with preview-first safety. Optional restricted break-glass path requires policy decision. |
| Sync analysis/logs | Refactor into reports/audit | Keep data, replace generic presentation with domain/reliability semantics. |
| Shared UI tokens/SCSS | Refactor and retain | Use one responsive/accessibility token layer; no visual-fix cascade per module. |
| Tests/tours | Keep contracts; rewrite UI paths and expand | Preserve behavioral coverage; add control contract, accessibility, responsive, RTL and end-to-end evidence. |


# 20. Weighted option scorecard

| Criterion | A — Targeted repair | B — Keep backend; rebuild shell | C — Full rewrite | D — Hybrid |
|---|---|---|---|---|
| Integrity preservation (20%) | 4.5 | 4.5 | 2.5 | 4.75 |
| IA coherence (15%) | 2.0 | 5.0 | 5.0 | 5.0 |
| Operator UX (15%) | 2.0 | 5.0 | 5.0 | 5.0 |
| Preserve proven assets (15%) | 5.0 | 5.0 | 1.0 | 5.0 |
| Migration safety (10%) | 5.0 | 4.0 | 1.5 | 4.5 |
| Testability (10%) | 4.0 | 4.5 | 2.0 | 4.5 |
| Maintainability (10%) | 3.5 | 4.5 | 4.0 | 5.0 |
| Time to value (5%) | 4.5 | 3.5 | 1.0 | 3.5 |
| WEIGHTED TOTAL | 3.73 / 5 | 4.62 / 5 | 2.95 / 5 | 4.78 / 5 |

| Option | Verdict |
|---|---|
| A — Targeted repair (3.73) | Too little. It preserves risk controls but leaves the product organized around implementation history. |
| B — Keep backend; rebuild shell (4.62) | Strong. Correct for pure IA/presentation work, but under-specifies the service/config/reporting refactors needed to make the shell truthful. |
| C — Full rewrite (2.95) | Reject. Attractive on paper, but destroys hard-won integrity, migration and test assets. |
| D — Hybrid (4.78) | Recommend. Preserve contracts and data; refactor selected aggregation/configuration seams; rebuild the product experience. |


# 21. Recommendation and confidence

| RECOMMENDED DECISION / Approve Option D as the planning basis. Treat the experimental branch as a research spike, not the implementation baseline. Rebase the final product work on the governed candidate only after exact-head qualification, and deliver the redesign through small, domain-safe branches with contract tests and native Odoo.sh evidence at every checkpoint. |
|---|

| Dimension | Confidence | Reason |
|---|---|---|
| Backend preservation | High | Direct source inspection shows mature integrity contracts and modular boundaries. |
| Need for IA/workflow rebuild | High | Menus, actions, settings and attention/recovery routes are demonstrably fragmented. |
| Target top-level hierarchy | High | Matches operator intents, Odoo conventions, Shopify app design guidance and competitor lessons. |
| Exact control completeness | Medium | Static source inventory is broad; no full checkout or exact-head runtime interaction. |
| Visual/responsive/accessibility readiness | Low–medium | Experimental assets exist, but runtime and independent evidence are missing. |
| Production qualification | Low | Exact governed SHA lacks native Odoo.sh qualification and controlled Shopify UAT. |


# 22. Migration roadmap

| Phase | Scope | Exit gate |
|---|---|---|
| 0 — Evidence closure | Exact-head Odoo.sh builds; full checkout; R5 traceability; runtime screenshot/control baseline | Decision owner accepts the evidence pack; no code changes required. |
| 1 — Product contract | Approved IA, terminology, state vocabulary, screen/workflow/control register and wireframes | Mostafa signs structure/design; technical owners approve protected contracts. |
| 2 — Navigation & configuration | New menu/action hierarchy, canonical configuration, role gating, deprecation redirects | Upgrade tests, no data model regression, native Odoo.sh pass. |
| 3 — Operations & attention | Unified Needs Attention, domain workspaces, Runs & Recovery, consequence-aware controls | All existing recovery capabilities reachable; no unsafe bypass. |
| 4 — Overview & health | Split health/freshness/attention/business aggregation and new Overview | Truth-state tests including zero/unknown/stale; performance budget met. |
| 5 — Reporting & audit | Domain reports, reliability metrics, activity/audit presentation | Metric definitions and redaction verified against source records. |
| 6 — Setup and polish | Five-phase setup, responsive/mobile, keyboard/accessibility, RTL, help and empty/error states | Browser/tour evidence on exact Odoo.sh SHA. |
| 7 — Migration validation | Menu/action aliases, bookmarks, access groups, upgrade scripts if required, rollback rehearsals | Install/upgrade/uninstall, historical data and permission matrix pass. |
| 8 — Controlled UAT | Read-only checks, sandboxed writes, representative Shopify workflows and recovery drills | Signed UAT matrix; owner accepts go/no-go. |

Use one writer/branch at a time for high-risk core XML and shared UI assets; keep PRs small and independently reversible.

Do not combine backend contract change with navigation/presentation change unless the contract change is necessary and separately justified.

Every PR states protected invariants, user-visible consequences, migration/rollback, test commands, exact SHA and Odoo.sh build.


# 23. Risks, gaps and mitigations

| Risk / gap | Why it matters | Mitigation / gate |
|---|---|---|
| No exact-head runtime | Static XML/JS cannot prove action wiring, access, responsive behavior or visual truth. | Provide exact-head Odoo.sh URLs; inspect every role and key workflow; capture screenshots. |
| No complete checkout | Cannot claim exhaustive file/control/test inventory or local worktree status. | Authenticated read-only checkout; run inventory scripts and compare to static counts. |
| R5 unavailable | Potential requirements may be missing from traceability. | Provide export; map every requirement to screen/workflow/control disposition. |
| Experimental branch self-evidence | Static audits and tests written in the same branch can miss UX or wiring faults. | Independent review and native runtime evidence. |
| Menu migration/bookmarks | Renamed menus/actions can break saved links, training and access expectations. | Stable actions where possible; redirects/aliases; release notes and role testing. |
| Metric truth/performance | A richer overview can become slow or misleading. | Defined semantics, explicit unknown/stale, query budgets, caching with timestamps and p95 checks. |
| Recovery safety regression | Simplified UI could expose dangerous retry or hide uncertainty. | Server-side guards remain authoritative; control-contract tests and evidence-first recovery. |
| Configuration consolidation | Moving fields can accidentally create duplicate storage or migration logic. | Keep canonical model; change routes/views first; introduce data migration only if unavoidable. |
| Accessibility/RTL/mobile | Dense Odoo views and custom Owl components can degrade outside desktop LTR. | Keyboard/focus/contrast/zoom/RTL/mobile matrix in Phase 6. |
| Shopify API evolution | Version/scopes/limits change over time. | Keep version constant and compatibility checks explicit; review official quarterly version window before release. |


# 24. Approval checklist

| Decision item | Approval statement |
|---|---|
| Product structure | Approve Overview / Operations / Reporting / Configuration as the four top-level destinations. |
| Operating model | Approve unified Needs Attention and Runs & Recovery; domain work stays under Operations. |
| Health model | Approve separate lifecycle, health, freshness, run and business-state vocabularies. |
| Configuration | Approve one canonical settings surface and five-phase setup using the same records. |
| Safety | Approve removal of the normal export-review bypass; decide whether a restricted break-glass route exists. |
| Architecture | Approve protected backend contracts and selective aggregation/configuration refactor only. |
| Evidence | Require exact-head Odoo.sh, full checkout, R5 traceability and controlled Shopify UAT before release decision. |
| Delivery | Approve phased, small-PR implementation only after the structure/design decision. |


# 25. Confirmation: nothing was changed

| READ-ONLY COMPLETION / No GitHub branch, file, issue, pull request, review, label or comment was created or modified. No Odoo.sh build, database, module, record or configuration was changed. No Shopify store, product, inventory level, order, fulfillment, scope or credential was changed. No implementation was started. |
|---|


# Appendix A. Evidence links

• Adams repository — Private repository reviewed through connected GitHub app.

• PR #204 — Draft governed candidate and native-qualification disclosure.

• Candidate commit 49cfffbd… — Current PR head during review.

• Experimental UI commit 067ba238… — Four commits / 45 files ahead of candidate at review time.

• GitHub Actions run 30715082576 — Successful candidate CI run; not native Odoo.sh evidence.

• Odoo 19 Owl components

• Odoo 19 frontend assets

• Odoo 19 backend actions

• Odoo 19 frontend framework overview

• Shopify app design guidance

• Shopify app structure

• Shopify navigation guidance

• Shopify app home page guidance

• Shopify onboarding guidance

• Shopify API versioning

• Shopify API rate limits

• Shopify API idempotency guidance

• Emipro Odoo 19 listing

• Emipro v17 documentation

• VentorTech connector

• VentorTech Odoo 19 migration

• Webkul Shopify app listing

• Webkul connector guide

• TeqStars Odoo 19 documentation

• ecommerce_shopify Odoo 19 listing

• Softhealer Odoo 19 listing


# Appendix B. Review method and evidence classification

| Class | Meaning | How used |
|---|---|---|
| Direct repository evidence | Source, manifests, menus, views, tests, PR/commit/run metadata read from AdamsOdoo/Adams. | Architecture, current/future mapping, state/control inventory and baseline status. |
| Direct runtime evidence | Exact-head Odoo.sh/browser interaction. | Unavailable; no claims made. |
| Current official evidence | Odoo/Shopify official documentation current at review date. | Platform and design constraints. |
| Current vendor evidence | Current app listings/vendor documentation. | Feature/positioning comparison; treated as claims unless independently observed. |
| Historical presentation evidence | Older docs/screenshots showing prior UI patterns. | Design examples only; never used to claim current behavior. |
| Inference | Reasoned conclusion from two or more evidence items. | Clearly identified in verdict, risks and recommendation. |

Repository inspection was read-only through the GitHub connector. Public competitor research was read-only. The unavailable exact-head runtime and internal R5 document are explicitly carried as gaps rather than silently assumed.

PRODUCT AND RESTRUCTURE REVIEW COMPLETE — AWAITING MOSTAFA’S STRUCTURE AND DESIGN DECISION — IMPLEMENTATION NOT STARTED
