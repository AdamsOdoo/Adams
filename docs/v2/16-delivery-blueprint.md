# V2 delivery blueprint — execution baseline, 8 September 2026

Development is authorized. **UI redesign is parked at the user's request until they resume it.** Neither proposal is approved. Continue backend implementation, instructions, tests and evidence. This is V2 completion through bounded repair/refactoring, not a third connector rewrite.

This dated execution overlay resolves stale instruction/sequence conflicts. Root AGENTS.md owns operating instructions, document 13 owns changing status, 14 owns the inspected rebaseline, 15 owns release scope/evidence, and existing V2 01–11 own detailed contracts. Document 17 records unapproved design proposals. Historical documents remain available; do not silently replace safety requirements with this sequence.

## Outcome and honest starting point

Deliver one installable Odoo 19 Shopify connector with complete supported merchant loops, usable management and operations surfaces, safe recovery, preserved V1 data and a qualified immutable release candidate. “Implemented” and “qualified” are separate states.

The complete checkout was refreshed at published PR #212 head `1c75c10288477b3a902193797360badc9d2aa06a`; executable source last changed at `880e70088922eb10dd44426678d578ee4ee7a73a`. P10 fixes are already published; do not recover them again. PR #210/#211 remain separate and untouched. The inspected tree has 2,286 entries / 2,060 blobs including 694 addon files and 1,301 documentation files. This is a coverage inventory, not a claim that every line of every file was audited.

Fresh local baseline: 448 dependency-free tests passed. Historical full native CI is red: fresh/warm 66 failures and 720 errors; Lite install fails; old-core W2 fails; nonstandard/concurrency assertions are partly blocked by setup. See 14 for exact run/artifact provenance. The code is **not assured for controlled UI UAT**. Re-run native gates after corrections; do not infer them from static success.

GitHub publication and native CI became available after this blueprint was drafted. The approved checkpoint is published as `30bde525`; its Lite/Full installations pass, while the broader runtime campaign still fails. Document 13 owns current source, results and access status, including the separate automatic-review restriction on publishing later local changes. The local environment lacks PostgreSQL and pinned Odoo; no current live database/build qualification is established. Preserve the gates while correcting the demonstrated failures.

## Architecture and scope decisions

- Preserve the 13 existing connector addons and their identities. Core cannot import optional domains; webhook foundation remains its existing addon. No generic repository wrappers or mandatory folder skeleton merely to match a diagram.
- Preserve distinct run, job, execution-attempt and remote-mutation-intent evidence; remove redundant orchestration only with demonstrated behavior equivalence. P10 lock ordering, handler binding, claim fencing and monotonic checkpoints remain intact.
- Native Odoo ORM/services, short transactions, bounded cron work and typed Shopify gateway/provider contracts. SQL is appropriate for owned migration/constraints/concurrency correctness; profiling is not a prerequisite for a necessary lock or schema fix.
- Shopify API pin remains 2026-07; Odoo pin remains `30bde9ff758834a4912c5ae55843d3a7dad849f1`. Move pins only in a separately explained, requalified change.
- Existing merchant-controlled app credential model, visible Administrator/User roles and internal capability groups remain. No new vendor OAuth platform or unplanned credential storage claim.
- Supported ten-store limit remains. A 20-store stress profile is an overload/rejection experiment, not permission to advertise twenty supported stores. Keep existing product/variant/order/inventory/fulfillment limits from docs/release/v1-supported-scope.md until measured change is approved.
- Refund/return/payout automation and broader commerce features remain deferred; incoming unsupported events still require safe disposition/review. Optional module consolidation and eventual schema contraction are post-release work, not prerequisites to usable delivery.

## Executable sequence and completion gates

| Packet | Work and predecessor | Concrete completion evidence |
| --- | --- | --- |
| F0 — operating baseline | Finish instructions, skills and this routing; preserve V1/V2 review and native root diagnosis | Coherent local commit; working skill links/validation; explicit unpublished status until write access works |
| F1 — install and identities | Repair Lite optional-owner schema access; canonical run name and explicit attempt number handling; then prove approved owner upgrades before W2 (document19) | Focused regressions; actual fresh Lite/Full and owner-upgrade/W2 installs; no optional-owner schema leakage; canonical immutable IDs |
| F2 — lifecycle and recovery | Repair typed-context translation collision, stale-owner ordering and actual protected-facade defects; update operational fixtures via sanctioned activation surfaces | Focused native lifecycle/recovery tests; draft/paused/retired/inactive stores still blocked; recovery result returned rather than tracebacks |
| F3 — shared backend assurance | Re-run transport, command/generation/ACL, run/job/attempt, P10 and subscription suites after setup roots clear; fix newly exposed causes | Full affected native lanes; two-connection barriers; crash/uncertain tests; install/warm/upgrade compatibility; no unresolved high safety findings |
| D1 — products and orders | Product/variant identity and import → customer/order validation → whole-order hold/resume → Odoo business record | U3/U5 backend paths, duplicate prevention, totals/currency/payment policy, supported matching and signed event convergence |
| D2 — inventory | Mapping → first observation/preview → explicit approval → quantity mutation → readback → drift recovery | U6, overlapping-trigger races, stale-preview/generation/CAS rejection; no wrong-location writes |
| D3 — catalog publication | Owned fields/variants/media → guarded diff → mutation → remote confirmation | U4, no unintended deletion or foreign-media ownership, uncertain-state recovery and no duplicate variant creation |
| D4 — fulfillment | Odoo delivery → exact Shopify order/location/items → notification decision → fulfillment → verification | U7, partial/external/uncertain outcomes; exact adoption without duplicate shipment |
| D5 — cross-cutting loops | Trigger convergence, permissions, lifecycle, fair dispatch and interrupted-work recovery across D1–D4 | U2/U8/U9/U11/U12/U13; two-store isolation; real restart/concurrency, backlog and throttle evidence |
| U — native experience | **Wait for user to resume design and approve direction.** Then shell compatibility spike and complete vertical slices over qualified backend contracts | Approved design; management plus operations; exact native actions and business-record links; responsive/RTL/keyboard; role-aware U1–U14 and human usability |
| Q — immutable candidate | Freeze source/tree/package; consolidate exact-candidate proof and independently inspect raw evidence | All supported journeys and security/migration/performance/live checks green; no critical/high defects; release notes, setup/operations/rollback docs match artifact |
| C — controlled canaries | Eligible dev/release observation cohorts after preceding gates, preserving existing sequence and rollback controls | Inventory, catalog and fulfillment observation minima below; explicit halt/rollback evidence |
| R — release decision | Present qualified artifact, evidence, residual limitations and rollback to user | Separate final production/public publication authority; no automatic promotion |

Internal packets are not approval stops. Fix ordinary failures and continue the next safe packet. UI-specific work is explicitly parked; backend DTOs, metrics definitions and journey tests can advance. If native access blocks F1, prepare bounded remaining repairs and tests, but never mark its gate complete or begin unsafe live mutations.

## The regression coverage must retain V1

The historical 36 UAT scenarios map to the existing U1–U14 campaign. This is routing, not a claim they passed. IDs 1–15 come from mvp-uat-scenarios.md; 16–36 from final-mvp-uat-plan.md under docs/08-release-readiness.

| Historical scenario IDs | Existing behavior | V2 journey ownership |
| --- | --- | --- |
| 1, 2 | Connect, failed credential and recovery | U1, U11 |
| 3, 4 | Simple/variant product import | U3 |
| 5 | Customer import and existing-partner match | U5 |
| 6, 7, 8 | Same-currency order, divergent-currency hold, duplicate prevention | U5, U8 |
| 9, 10 | Manual inventory and failure recovery | U6, U9 |
| 11 | Fulfillment and tracking | U7 |
| 12, 13 | Disconnect/history preservation, reconnect/readiness | U11 |
| 14, 15 | Safe retry and redacted diagnostics | U9, U10, U12 |
| 16, 17 | Product/customer ambiguity resolution | U3, U5, U9 |
| 18, 19 | Currency/duty hold; whole-order unmatched-line resume | U5, U3 |
| 20, 25 | First inventory push; baseline/replay audit | U6, U9 |
| 21 | Uncertain fulfillment adoption | U7, U9 |
| 22, 26 | Variant protection and media add/replace/foreign ownership | U4; current non-destructive contract supersedes old deletion options |
| 23, 36 | Lite/Full install, flags, menus and permissions | U13, U12 |
| 24 | Roles and direct authorization | U12 |
| 27, 28 | Dashboard performance/hierarchy and long operational lists | U10, management reporting |
| 29, 30, 31 | Keyboard, responsive/RTL and reduced motion | All UI journeys; U10/U12 |
| 32, 33 | Setup usability and in-screen recovery | U1, U9, U10 |
| 34 | Matching at realistic partner/review scale | U3, U5 and performance |
| 35 | Consistent visual interaction system | All UI journeys |

The newer release/v1-uat-matrix.md groups map similarly: 1/2→U1; 3→U3/U4; 4→U6; 5→U5; 6→U7; 7→U10/U11; 8→U9/U10; 9→U11; 10→U12; 11→U2/U12; 12→U13. U14 closes the two complete merchant loops on one candidate rather than accepting disconnected method tests.

## Qualification, timing and usage

Run cheap focused checks after coherent edits, affected native tests once their packet settles, and consolidated expensive gates at integration/freeze. Full CI already includes push/PR duplication: do not add more duplicate campaigns. Preserve strict native gates; baseline-regeneration drift or a fixture cascade is not authorization to relax them.

Existing sequential canaries remain: inventory at least 10,000 intents/72 hours; then catalog at least 5,000/72 hours; then fulfillment at least 2,000/seven days after lower layers are accepted. Minimum observation time is thirteen days after readiness, and counts/halts may extend it. The 21-day date is an engineering checkpoint, not continuous model runtime or a guaranteed delivery date. Do not claim automatic multi-day work or chat creation.

Human usability requirements remain five participants per primary role, at least 90% unaided task completion, under ten seconds to identify the highest-impact issue, and zero unintended writes. Participant availability is unresolved. This gates usability/release, not local backend repair. Architecture/security/release review must state the actual independence available.

Default routing is in AGENTS.md: Sol medium for narrow familiar tasks, high for state/ORM/concurrency implementation; Astra high for architecture and cross-domain assurance, increasing effort only when evidence warrants it. Avoid unnecessary agents, broad repeated context and maximal effort by default. Compare correctness and effort on representative packets; actual usage quota is unknown. The initial root-cause packet uses one Sol implementer plus Astra on non-overlapping installation/instructions work.

## Official guidance and how it affects implementation

Sources were refreshed during the 8 September review; refresh the owning version-specific operation again before live use. An inaccessible page is recorded as unavailable, not silently treated as read. Earlier source inventories and deep dives remain in docs/00-source-materials and docs/01-research.

| Source | Application |
| --- | --- |
| [Odoo 19 coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html) | ORM conventions, coherent methods, exception handling and framework-owned transactions; official documentation source was inspected when rendered pages failed |
| [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html) | Public method arguments are untrusted; ACL/record rules and service checks own authorization |
| [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html) | Batch/prefetch, bounded queries, measured profiling; no per-row ORM/network loops |
| [Odoo 19 scheduled actions](https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#scheduled-actions-ir-cron) | Native cron progress/batching, checked against pinned implementation |
| [Shopify webhook delivery verification](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries) and [webhooks](https://shopify.dev/docs/apps/build/webhooks) | Authenticate raw bodies, durable fast intake, asynchronous effects, deduplication and reconciliation |
| [GraphQL Admin API](https://shopify.dev/docs/api/admin-graphql/2026-07) and [API limits](https://shopify.dev/docs/api/usage/limits) | Pin operation schema, distinguish all error layers, cost-aware throttling and bounded pagination; repository operation validation is additional evidence, not live proof |
| [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) | Audit accumulated instructions, explicit autonomy/question policy, calibrated testing and bounded delegation |
| [GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6) | Evaluate representative tasks at the selected and one lower effort; stable context and efficient batching |
| [Building skills](https://learn.chatgpt.com/docs/build-skills) | Three focused repo skills with progressive loading; no generic full-stack instruction dump or personal install |
| [Long-running work](https://learn.chatgpt.com/docs/long-running-work) | Durable repository checkpoints and explicit continuation; no promise of autonomous new chats |

## Handover and significant dependencies

Keep document 13 current before context pressure, after material changes and before external blocks. Include exact local/published heads, open diffs, checks/results, environment, rollback and first next action. The receiving owner verifies rather than repeating the whole audit. Access dependency: writable GitHub connection and a native Odoo/PostgreSQL test environment; live qualification also needs an exact authorized dev build and secure shop credentials. Later decisions: resuming/approving UI design, human UAT availability and final release authority. Do all independent authorized work first.
