# V2 Decision and Traceability Register

> **Status:** proposed locked defaults for architecture-gate approval.  
> **Change rule:** implementation may not silently deviate. Record a reviewed decision update with evidence, affected requirements/tests/packets and migration impact.

## 1. Decision register

| ID | Locked decision | Rationale/evidence | Implemented by |
| --- | --- | --- | --- |
| V2-D001 | Deliver V2 by staged refactor with bounded internal replacement. | Existing safety/data assets are valuable; current concentration still needs replacement. | all packets |
| V2-D002 | Remain an Odoo modular monolith; no external worker/service by default. | Accepted repository posture; simpler deployment/transactions. | P01, P10 |
| V2-D003 | Preserve addon technical names through release. | Install/upgrade/uninstall and XML-ID compatibility. | all/P20 optional |
| V2-D004 | Preserve model/table/XML IDs and record IDs unless a separate migration ADR proves necessity. | Customer data and integration compatibility. | P00, P09, P19 |
| V2-D005 | Preserve binding identity and current per-store uniqueness constraints. | Primary entity idempotency anchor. | all domain packets |
| V2-D006 | Preserve job state/error taxonomy physically; map labels in DTO/UI. | Audit and behavior compatibility. | P01–P19 |
| V2-D007 | Separate run, job, execution attempt and mutation intent. | Makes orchestration, retry and certainty explicit. | P09–P14 |
| V2-D008 | Stage 1 run refs are opaque `job:<id>`; new runtime uses `run:<id>`. | Stable UI contract without premature schema. | P02, P09 |
| V2-D009 | Attention is a provider-based read projection, not a generic table initially. | Lighter implementation; avoids another source of truth. | P02, P04 |
| V2-D010 | Presentation uses standard Odoo views by default and Owl only for composed/dense interactions. | Odoo-native UX and lower maintenance. | P03, P04, P15, P16 |
| V2-D011 | One connector app navigation: Overview, Needs Attention, Products, Orders, Inventory, Fulfillment, Runs, Settings. | Simplifies mental model; competitor review. | P03, P16 |
| V2-D012 | No separate Sync Center or Error Center in V2 mode. | They are filters over Runs/Attention. | P16 |
| V2-D013 | The live prototype governs hierarchy/tone; written contracts govern behavior/data/accessibility. | Prevents screenshot-driven safety loss. | P03–P16 |
| V2-D014 | One initial RPC per composed screen; server builds read models. | Prevents browser orchestration and N+1. | P02–P16 |
| V2-D015 | `allowed_actions` drives UI but server always reauthorizes/revalidates. | UI is not a security boundary. | P02, P04, P15, P16 |
| V2-D016 | Public RPC uses explicit versioned named methods, not arbitrary dynamic dispatch. | Smaller attack/compatibility surface. | P01–P04 |
| V2-D017 | Shopify Admin GraphQL stays pinned centrally to `2026-07`; served header must match. | Current binding control-room decision. | P05–P19 |
| V2-D018 | All business input uses GraphQL variables and checked-in named operations. | Injection safety and contract review. | P05–P08 |
| V2-D019 | Raw Shopify envelopes do not cross gateways. | Domain/runtime isolation and smaller tests. | P05–P14 |
| V2-D020 | Per-store cost governor schedules work; it never sleeps in a transaction. | Shopify cost limits and worker efficiency. | P05, P10 |
| V2-D021 | Webhook request verifies raw-body HMAC, records a payload-free dedup envelope and acknowledges before domain work. | Shopify delivery semantics and current safety. | P07/P08 preserve |
| V2-D022 | Webhooks are hints; reconciliation remains mandatory. | Duplicate/missed/out-of-order delivery. | P06–P14 |
| V2-D023 | Raw webhook bodies are never persisted; metadata retention remains 30 days. | Current privacy/lifecycle contract. | all webhook work |
| V2-D024 | Network calls occur outside broad Odoo record locks/claim transaction. | Prevents lock contention and false rollback assumptions. | P05, P10–P14 |
| V2-D025 | Database row locks/uniqueness/leases are correctness controls. | Multi-worker safety. | P09–P14 |
| V2-D026 | Priority lanes are safety verification, interactive, webhook, Odoo event, scheduled, reconciliation, with bounded aging. | Recovery urgency without starvation. | P10 |
| V2-D027 | Preserve eligible retry policy: 30-second exponential ×2, 30-minute cap, ±20% jitter, maximum 12 scheduled retries and 24-hour window; domain may be stricter. | Accepted bounded recovery behavior; no endless loops. | P10–P14 |
| V2-D028 | Any possible-after-send mutation failure enters readback; never blind replay. | Duplicate/irreversible effect risk. | P08, P11–P14 |
| V2-D029 | Direct Shopify success is `accepted`; only independent readback is `verified`. | Honest certainty semantics already present. | P02–P16 |
| V2-D030 | Inventory becomes Odoo-authoritative only after explicit mapping, current observation, preview and Administrator first-push confirmation. | Prevents blind overwrite. | P12, P16 |
| V2-D031 | Product export requires field-level authority, validation and a current preview fingerprint. | Prevents protected/stale writes. | P13, P16 |
| V2-D032 | Product/customer matching uses existing binding then accepted deterministic keys; name/fuzzy evidence never auto-binds. | Duplicate/wrong-link risk. | P06, P16 |
| V2-D033 | Shopify order commercial evidence is preserved; later observations do not silently rewrite Odoo operations. | ERP operational authority. | P06, P16 |
| V2-D034 | Fulfillment notification value is explicit in command/evidence; no hidden email behavior. | Irreversible customer communication. | P14, P16 |
| V2-D035 | Store/company/generation fences run at admission and immediately before side effects. | Tenant/lifecycle safety. | every command/runtime packet |
| V2-D036 | Credentials use a dedicated write-only command and never return to the client. | Secret boundary. | P15 |
| V2-D037 | Global company rules remain fail-closed; cross-record relations require same store. | Multiple stores may share a company. | all schema/query work |
| V2-D038 | Read models do not use `sudo()` to bypass tenant rules. | Prevent aggregate/count leakage. | P02–P16 |
| V2-D039 | Migration uses expand/backfill/dual-read/switch/soak/contract; no schema rollback during coexistence. | Online safety and recoverability. | P09, P19 |
| V2-D040 | Store-scoped UI/gateway/runtime modes are temporary and auditable. | Safe canary/failback without permanent architecture. | P03/P09–P19 |
| V2-D041 | Mutation cutover order is connector-owned webhook subscriptions, inventory, product export, fulfillment. | Increasing business irreversibility/risk with exact desired-state reads first. | P11–P14 |
| V2-D042 | Contraction waits for two successful releases and at least 14 days at all-V2, whichever is later. | Operational evidence before deletion. | P19 |
| V2-D043 | Webhook addon consolidation is optional and last, with separate ADR/lifecycle proof. | Packaging risk should not block product value. | P20 |
| V2-D044 | No cross-request cache in initial V2; optimize queries first. | Cache invalidation/tenant risk and lighter architecture. | P02–P16 |
| V2-D045 | No persistent generic attention case until assignment/snooze evidence justifies it. | Avoid speculative table/workflow. | P02, P04 |
| V2-D046 | Money is decimal string + currency in DTOs; timestamps UTC; Shopify IDs canonical GIDs. | Precision and contract consistency. | P01–P16 |
| V2-D047 | New runtime observations store digests/allowlisted metadata, not raw payloads. | Privacy, retention and smaller tables. | P05–P14 |
| V2-D048 | WCAG 2.2 AA, 375/768/1366/1440 and RTL are release gates. | Premium inclusive UX. | P03, P04, P15–P17 |
| V2-D049 | Performance budgets are hard ceilings; impossible values stop for evidence/review rather than silent relaxation. | Prevents architecture by optimism. | every relevant packet |
| V2-D050 | V2 is default-ready at P18; contraction/packaging are later and cannot delay user value. | Separates release from cleanup. | P18–P20 |
| V2-D051 | V1 release failures—unreachable onboarding, weak progress/recovery hierarchy, unproved event-to-state latency/backlog behavior and backend-heavy evidence—are explicit V2 regression contracts. | Prevents repeating costly V1 mistakes. | P00, P03–P18 |
| V2-D052 | Production UI wiring waits for a same-candidate foundation certificate covering contracts, gateway, runtime, security/isolation, migration/rollback and performance/restart. | Visual polish cannot compensate for an unstable execution base. | W1–W2 before P03/P04/P16 |
| V2-D053 | U1–U14 are mandatory end-to-end business journeys; tours alone do not satisfy them. | Proves complete operator and merchant outcomes across systems. | P16–P17 |
| V2-D054 | P00–P20 are traceability IDs inside one continuous five-wave program and one integrated candidate PR, not 21 approval phases. | Preserves reviewability without artificial waiting. | P00–P18 |
| V2-D055 | Cross-chat continuity is proactive and committed: checkpoint before context exhaustion, then verify SHA/branch/status in the receiving chat. | Keeps long execution safe and continuous. | every wave |
| V2-D056 | Near-real-time is measured event-to-visible-state latency with immediate durable admission/drain plus one-minute recovery scheduling; it is never marketed as instantaneous/exactly-once. | Responsive operation with honest distributed-system limits. | P10–P18 |
| V2-D057 | Multiple stores are first-class, independently scoped identities with no designed licensing/count cap; same company never relaxes same-store checks. | Merchant scalability and tenant safety. | P02, P09, P15–P18 |
| V2-D058 | Post-onboarding Administrator controls are grouped typed settings/lifecycle actions; safety algorithms, API version, secrets and identity fences are not configurable. | Powerful administration without bypass switches. | P15–P16 |
| V2-D059 | Refunds and payouts extend typed domain registries through additive addons; core gets no speculative generic workflow/data framework. | Future capability without present overengineering. | future addons; registry tests P01/P17 |
| V2-D060 | The V2 shell must pass Odoo action/context/asset/responsive/RTL compatibility; if custom persistent navigation requires a webclient/router fork, use the Odoo-native fallback. | Maintains Odoo compatibility and upgradeability. | P03, P16–P17 |

## 2. Default parameters

| Parameter | Default | Change authority |
| --- | --- | --- |
| Contract version | `1` | breaking-change review |
| Shopify API version | `2026-07` | dedicated schema revalidation checkpoint |
| Webhook envelope retention | 30 days | privacy/lifecycle ADR |
| Webhook retention batch | 2,000 rows | measured performance decision |
| Backfill batch | 2,000 rows, lower if baseline demands | migration owner with evidence |
| Retry schedule | 30-second base, ×2, 30-minute cap, ±20% jitter; stop at 12 scheduled retries or 24 hours | error-policy ADR/domain stricter override |
| Priority aging | one priority step per 15 minutes; ceiling interactive | runtime review |
| Initial mutation reconciliation inconclusive cap | preserve current cap of 3 | mutation-safety review |
| Initial Shopify idempotency validity | preserve current 23 hours where applicable | Shopify-contract review |
| Attention first page | 80 rows | UX/performance review |
| Run timeline initial page | 200 events | UX/performance review |
| Mandatory viewport tests | 375, 768, 1366, 1440 px + RTL | design-system review |
| Contraction soak | 2 releases and 14 days at all-V2, whichever later | architecture/release gate |
| Immediate drain recovery | enqueue requests bounded drain after commit; one-minute scheduled drain remains fallback | runtime/performance ADR |
| Webhook acknowledgement | p95 ≤1 second; no accepted request ≥5 seconds | performance/safety review |
| Single-record event completion | p95 ≤15 seconds, p99 ≤60 seconds excluding evidenced Shopify throttle/outage | performance/release review |
| Active/passive UI freshness | active run observes terminal state within 5 seconds; passive Overview refresh defaults to 30 seconds | UX/performance review |
| Fulfillment cutover evidence | 2,000 exact-candidate deterministic fault/load intents + 7-day canary | safety/release gate |
| Inventory cutover evidence | 10,000 exact-candidate deterministic fault/load intents + 72-hour canary | safety/release gate |
| Product-export cutover evidence | 5,000 exact-candidate deterministic fault/load intents + 72-hour canary | safety/release gate |

Volume-dependent values are not guessed: P00 records the target environment and hard budgets from `09-test-observability-release-blueprint.md`; failure to produce them blocks P01/P02 performance acceptance.

## 3. Rejected-approach regression checklist

The repository’s accepted RA register remains authoritative. The implementer must also answer `No` to each question below at every wave/candidate review.

| Check | Rejected pattern |
| --- | --- |
| RA-V2-01 | Does this create one giant connector addon/file/service? |
| RA-V2-02 | Does this split every minor capability into a new addon/deployable? |
| RA-V2-03 | Does it add an external worker, queue package, broker or cache by default? |
| RA-V2-04 | Does frontend code call Shopify or decide business authority/security? |
| RA-V2-05 | Does it create a second SPA/router/global browser store inside Odoo? |
| RA-V2-06 | Does it use `sudo()` or permissive record rules to fix counts/access? |
| RA-V2-07 | Does it trust hidden buttons/context flags as authorization? |
| RA-V2-08 | Does it infer bindings/mappings from names or fuzzy similarity? |
| RA-V2-09 | Does it blind-push first inventory or hide source/target authority? |
| RA-V2-10 | Does it blind-retry a possible mutation or label uncertainty as failure? |
| RA-V2-11 | Does it retry every error, never retry any error, or retry indefinitely? |
| RA-V2-12 | Does it send customer notification without explicit effective evidence? |
| RA-V2-13 | Does it expose raw stack traces, payloads, secrets or PII to users/logs? |
| RA-V2-14 | Does it persist raw webhook bodies or perform domain work before acknowledgement? |
| RA-V2-15 | Does it shadow/compare live mutations? |
| RA-V2-16 | Does it rename/drop stable models/XML IDs/data before coexistence/soak proof? |
| RA-V2-17 | Does it force store reconnect or recreate bindings? |
| RA-V2-18 | Does it combine gateway extraction with a business-policy redesign? |
| RA-V2-19 | Does it use unbounded ORM scans, offset backfills or N+1 UI calls? |
| RA-V2-20 | Does it promise “real-time” or exactly-once delivery without honest limits? |
| RA-V2-21 | Does it add a permanent flag/facade without owner/removal gate? |
| RA-V2-22 | Does it copy competitor feature breadth or dashboard density without user need? |
| RA-V2-23 | Does it remove tests/relax assertions to make a candidate green? |
| RA-V2-24 | Does it wire production UI before the shared backend foundation certificate is green? |
| RA-V2-25 | Does it turn internal work IDs into mandatory approval/PR ceremonies that add no safety evidence? |
| RA-V2-26 | Does it add speculative refund/payout tables, arbitrary JSON rules or a generic workflow engine to core? |
| RA-V2-27 | Does `All stores` or same-company aggregation permit a cross-store write, child reference or count leak? |
| RA-V2-28 | Does material execution state exist only in chat output instead of a committed checkpoint/handoff? |

Any `Yes` blocks the affected checkpoint until an explicit accepted ADR supersedes the rejection.

## 4. Requirement traceability matrix

| Req | Product requirement | Screen/UX | Backend/data contract | Primary tests | Packet |
| --- | --- | --- | --- | --- | --- |
| R001 | Operator knows store safety within seconds. | Overview health band | overview DTO, health/freshness projection | U10, query/security | P02–P03 |
| R002 | Human work is ranked by impact. | Needs Attention | provider aggregation/severity/action DTO | provider/unit/U10 | P02–P04 |
| R003 | Every exception names owner, evidence, action and consequence. | resolution detail | attention detail/command | stale/role/audit/U9/U10 | P04 |
| R004 | Setup is guided, resumable and cannot activate unsafely. | six-step setup | setup DTO/commands/readiness fingerprint | U1/security/lifecycle | P15–P16 |
| R005 | Credential is write-only. | credential step | guarded service; metadata-only reads | secret/RPC tests | P15–P16 |
| R006 | Store/company isolation is fail-closed. | store switcher/all screens | record rules + service recheck | multi-company matrix | all, esp. P02/P09 |
| R007 | Matching never guesses by name. | matching flow | binding/deterministic policy | binding/match matrix | P06/P16 |
| R008 | Product writes show field authority and current diff. | product preview | authority policy/fingerprint | product export matrix | P13/P16 |
| R009 | Order commercial evidence is preserved. | order evidence panel | order DTO/binding/total policy | order matrix | P06/P16 |
| R010 | First inventory push cannot overwrite blindly. | mapping/preview | mapping/binding/preview/mutation command | inventory matrix/U6 | P12/P16 |
| R011 | Fulfillment/notification is explicit and duplicate-safe. | fulfillment timeline | mutation intent/readback/notification command | fulfillment faults/U7/U9 | P14/P16 |
| R012 | Uncertain writes are verified before retry. | run/fulfillment state | mutation certainty + verification | fault ledger | P08/P11–P14 |
| R013 | Users see a narrative, not logs. | Run detail | run/job/attempt/log DTO | timeline/role/U9/U10 | P02/P04/P09–P10 |
| R014 | Webhooks acknowledge fast, reconcile gaps and converge connector-owned subscriptions. | freshness/run/readiness evidence | HMAC/dedup/inbox/reconciler/subscription desired state | webhook/load/fault tests | preserve/P07/P10/P11 |
| R015 | Shopify cost is bounded and observable. | run technical evidence | executor/cost governor/attempt metrics | contract/performance | P05–P10 |
| R016 | Existing customer data survives V2. | unchanged identities | preserved models/constraints; additive schema | lifecycle/migration | P00/P09/P19 |
| R017 | Rollout/failback is store-scoped. | admin technical settings | three migration modes/generation | rollback/canary | P09–P18 |
| R018 | UI is premium, accessible, responsive and RTL-ready. | all composed screens | versioned DTOs/state matrix | D lane/U1–U12 | P03/P04/P16–P17 |
| R019 | Connector is lighter and easier to maintain. | simpler navigation | small cohesive packages; no duplicate sources | dependency/complexity/perf | P01–P19 |
| R020 | Release decision is evidence-based. | no direct screen | evidence bundle/SLO/halt rules | complete qualification | P17–P18 |
| R021 | V1 mistakes cannot recur silently. | setup, progress, recovery and freshness states | characterization contracts and latency/backlog evidence | V1 regression set/U1/U9/U10/U13 | P00/P17 |
| R022 | Complete merchant outcomes work across both systems. | all domain/contextual screens | cross-domain commands, bindings and evidence | U1–U14 | P16–P17 |
| R023 | Backend is strong before product UI depends on it. | contract fixtures before live wiring | foundation certificate | foundation lanes A/B/C/E/F | P00–P15 before P03/P04/P16 |
| R024 | Administrator can safely manage settings and multiple stores. | Manage stores, setup, Settings | typed settings/store administration/lifecycle contracts | U1/U2/U11/U12 | P15–P17 |
| R025 | Event-driven work is near-real-time and honestly measured. | live run progress/freshness | immediate admission/drain, priority, fallback reconciliation | latency/backlog/restart/U8–U10 | P10–P18 |
| R026 | Refunds/payouts can be added without redesigning core. | future registered domain surfaces | typed extension registries and addon ownership | synthetic extension/uninstall tests | P01/P17 + future addon |
| R027 | Long implementation continues safely across chats. | no product screen | committed checkpoint/handoff protocol | receiving-chat SHA/status verification | every wave |

## 5. Screen-to-contract matrix

| Screen | Initial RPC | Detail/write RPC | Required providers/services |
| --- | --- | --- | --- |
| Overview | `get_overview_v1` | named action from returned key | store/workflow health, attention, activity |
| Needs Attention | `search_attention_v1` | `get_attention_detail_v1`, `resolve_attention_v1` | registered domain providers |
| Products | native ORM action | preview/resolve explicit methods | product bindings/match/export policy |
| Orders | native ORM action | reconnect/review explicit methods | order/customer bindings/evidence |
| Inventory | native ORM/read DTO | preview/start/resolve methods | mapping, inventory read/mutation gateway |
| Fulfillment | native ORM/read DTO | registered mutation/recovery action | fulfillment handler/readback |
| Runs | native list/read `get_run_v1` | retry/cancel/resolve methods | run/job/attempt/log/mutation evidence |
| Manage stores | `get_store_list_v1` | create/pause/resume/disconnect/retire named methods | store lifecycle, company/store rules, readiness summary |
| Settings | `get_store_settings_v1` | grouped typed settings/workflow-state methods | lifecycle, settings and domain readiness providers |
| Setup | `get_setup_v1` | save/replace/test/activate methods | lifecycle, credential, settings and readiness providers |
| Operation launcher | `get_operation_options_v1` | `start_operation_v1` | operation registry/command bus |

## 6. Risk ownership

| Risk | Primary owner role | Required reviewer |
| --- | --- | --- |
| Binding/data migration | backend/data engineer | independent domain reviewer |
| Shopify operation/version/cost | integration engineer | Shopify contract reviewer |
| Runtime/concurrency/mutation certainty | backend/runtime engineer | independent safety reviewer |
| Tenant/credential/PII | security owner | independent security reviewer |
| Domain authority/mapping/totals | domain engineer | product/domain owner |
| UX/accessibility | frontend designer/engineer | accessibility + operator reviewer |
| Deployment/canary/rollback | release operator | architecture/release approver |

One person may hold several roles on a small team, but must perform and record each review lens. The author of fulfillment mutation logic should not be the sole release verdict reviewer.

## 7. External facts that must be revalidated

These are the only planned inputs that can age independently of the repository and therefore require revalidation at their packet:

| Fact | Revalidate in |
| --- | --- |
| Shopify `2026-07` schema, served-version behavior and operation fields | P05–P08 and every version bump |
| Shopify API cost/throttle behavior | P05 and release qualification |
| Shopify webhook headers/delivery/subscription guidance | any webhook change, P11 and P17 |
| Odoo 19 Owl/service/testing/security APIs at pinned Odoo SHA | P01/P03/P17 |
| Competitor UI/feature claims | only if used to change scope; not needed for implementation of locked V2 |

Implementation must use official Shopify/Odoo documentation for platform facts. Vendor/competitor documentation may inform product comparison but cannot override safety contracts.

## 8. Architecture and execution gate sign-off

One integrated gate records `approve`, `approve with named change`, or `reject` for:

1. product, complete journeys and UX contract (`01`, `05`, U1–U14 in `09`);
2. backend foundation, data/API and extension contracts (`02`, `06`, `07`);
3. migration, performance, release and rollback contract (`03`, `08`, `09`);
4. five-wave roadmap and lighter-model operating contract (`10`, `12`);
5. V1 lessons, competitor evidence and rejected patterns (`04`, this file); and
6. continuous execution/handoff protocol (`13`, `CLAUDE.md`, `AGENTS.md`).

Once that gate and implementation authorization are recorded, W1–W5 proceed as one program without packet-by-packet approval. Automatic evidence gates and the documented stop conditions remain binding; routine fixes and handoffs do not pause for confirmation.
