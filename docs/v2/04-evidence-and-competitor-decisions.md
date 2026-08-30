# Evidence and Competitor Decisions

> **Access date:** 2026-08-29. External claims are classified. Vendor documentation demonstrates vendor-presented behavior; it is not independent proof of implementation quality.

## 1. Current-product evidence

| Evidence | Status | Classification | Design consequence |
| --- | --- | --- | --- |
| Accepted DEC-008/009/010/011/012/013/014 and rejected approaches RA-001–RA-023 | Accessible in repository | Fact | Preserve accepted module, identity, retry, inventory, fulfillment and operator-flow invariants. |
| Accepted U0 prototype (`docs/09-ui-prototype`) | Accessible in repository | Fact | Preserve ranked dashboard, selective Owl, Odoo-native views, accessibility, responsive and RTL baseline. |
| Draft release PR #210 snapshot `44da1e…` inspected; live head `f77bfcc…` observed at final verification | Accessible in GitHub | Fact | Treat the inspected snapshot as evidence, not a permanently current head. Do not modify the release PR; Wave 1 re-freezes and characterizes the accepted implementation head. |
| Large core API/setup/store/credential/dispatch and setup UI files observed at release head | Accessible in GitHub | Fact | Prioritize characterization and seam extraction; file size alone is a risk signal, not proof of incorrectness. |
| Core + domain + product-export + webhook addon family at release head | Accessible in GitHub | Fact | Preserve domain family; evaluate webhook satellite consolidation only with lifecycle proof. |

## 2. V1 lessons that V2 must not repeat

The V1 closure evidence is a regression input, not a criticism to discard after redesign.
`docs/08-release-readiness/public-release-closure.md` and
`backend-responsiveness-architecture.md` identify strong safety pieces that were not yet
proven as a responsive complete product. V2 converts each lesson into a contract/test:

| V1 lesson/evidence | V2 prevention |
| --- | --- |
| Activation could enter durable verification while the browser offered no reachable completion path. | Every asynchronous command has active progress, bounded polling, manual status recovery and a tested terminal UI journey. |
| Backend/webhook admission was stronger than end-to-end visible latency proof. | Record event/admission/start/finish/readback/UI-observed timestamps and enforce the near-real-time budgets in `09`. |
| Scheduled/reconciliation backlog could outrank a newer live/manual event. | Explicit priority lanes with bounded aging, backlog load tests and queue-age alerts. |
| Passive dashboard refresh was too slow for active work. | Active run follower ≤5 seconds; idle health remains quiet and accessibility-conscious. |
| Release evidence over-weighted backend automation and under-proved complete operator journeys. | U1–U14 require backend + Odoo UI + Shopify/Odoo readback + recovery on the exact candidate. |
| Large API/store/credential/setup/dispatch/domain services concentrated unrelated responsibilities. | Characterize first, then extract transport, application, policy, runtime and projection seams while preserving public/data identity. |
| Setup/readiness choices and evidence can drift when configuration changes or steps are renumbered. | Durable semantic step keys, configuration generation/fingerprint and readiness staleness are required. |
| A wrong or stale store identity can direct work to the wrong remote boundary. | Canonical domain, exact store/company/generation checks and environment/test-store allowlists at admission and execution. |
| Activation or scheduling can be technically allowed while a downstream default/mapping guarantees failure. | Workflow-specific readiness validates currency/pricelist, company/defaults, locations, scopes and authority before activation/admission. |
| Uncertain remote writes and first pushes are too risky for generic retry or hidden defaults. | Durable mutation intent, exact readback, no blind replay, preview fingerprints and explicit notification/first-push decisions. |
| UI hiding can be mistaken for authorization. | Every public method reauthorizes role/company/store and direct-RPC tests cover forged IDs. |
| Repeating complete expensive qualification after every small edit wastes time; leaving all tests to the end misses defects late. | Cheap focused tests per change, domain gates per wave and one complete exact-SHA suite after candidate freeze. |

Every Wave 1 characterization test maps at least one lesson to the exact current V1
behavior. Preserved behavior is intentional; known defects become failing regression tests
before their correction.

## 3. Official platform evidence

| Source | Access | Classification | V2 use |
| --- | --- | --- | --- |
| [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks) | Accessible — 2026-08-29 | Official fact | Design for duplicate/missed/out-of-order delivery and reconciliation; acknowledge quickly. |
| [Shopify API limits](https://shopify.dev/docs/api/usage/limits) | Accessible — 2026-08-29 | Official fact | Cost-aware per-store governor, bounded requests and observable throttle delay. |
| [Shopify idempotent requests](https://shopify.dev/docs/api/usage/idempotent-requests) | Accessible — 2026-08-30 | Official fact/guidance | Use supported idempotency keys within their contract while retaining durable local intent and readback for ambiguous outcomes. |
| [Shopify app design](https://shopify.dev/docs/apps/design) | Accessible — 2026-08-29 | Official guidance | Clear hierarchy, familiar patterns, accessible feedback and safe actions. |
| [Odoo 19 Owl components](https://www.odoo.com/documentation/19.0/developer/reference/frontend/owl_components.html) | Accessible — 2026-08-29 | Official fact/guidance | Use Owl within Odoo’s component system for interaction-dense surfaces. |
| [Odoo 19 services](https://www.odoo.com/documentation/19.0/developer/reference/frontend/services.html) | Accessible — 2026-08-29 | Official fact/guidance | Keep client side effects in services and use explicit dependencies. |
| [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html) | Accessible — 2026-08-29 | Official guidance | Batch operations, avoid N+1 and profile before structural replacement. |
| [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html) | Accessible — 2026-08-29 | Official guidance | ACLs, record rules, safe ORM usage and explicit authorization. |
| [Odoo 19 testing](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html) | Accessible — 2026-08-29 | Official guidance | Layered Python, tour and integration tests. |
| [Odoo 19 scheduled actions](https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#scheduled-actions-ir-cron) | Accessible — 2026-08-30 | Official guidance | Keep cron batches bounded/short, report progress and use wake-up plus recovery scheduling rather than a monolithic cron transaction. |
| [Odoo 19 multi-company guidance](https://www.odoo.com/documentation/19.0/developer/howtos/company.html) | Accessible — 2026-08-30 | Official guidance | Company-dependent consistency and record rules are designed/tested deliberately. |
| [Odoo 19 coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html) | Accessible — 2026-08-30 | Official guidance | Follow addon layout, naming, extensibility, commits and test conventions. |

## 4. Competitor review

| Competitor | Screen/feature evidence | Learn | Avoid |
| --- | --- | --- | --- |
| [VentorTech Shopify Connector](https://ecosystem.ventor.tech/product/odoo-shopify-connector-pro/) and [release notes](https://ecosystem.ventor.tech/release-notes/odoo-shopify-connector-pro/) | Accessible — 2026-08-29. Vendor docs/screens show guided configuration, queues, per-order automation, consistency checks, contextual recovery and link-vs-publish separation. **Competitor claim.** | Make recovery, queue evidence, consistency and safe linking first-class; show scope readiness clearly. | Copying Odoo-native visuals without simplifying information architecture. |
| [VentorTech queue priority](https://ecosystem.ventor.tech/faq/e-commerce-connectors/common-questions/how-the-connector-prioritizes-background-jobs/) | Accessible — 2026-08-29. Vendor describes priority behavior. **Competitor claim.** | Explicit lanes and human-readable priority rationale. | Depending on an external queue package as the default; RA-004 remains binding. |
| [Teqstars Odoo 19 connector](https://docs.teqstars.com/19.0/applications/shopify.html), [instance setup](https://docs.teqstars.com/19.0/applications/shopify/setup/create_instance.html) | Accessible — 2026-08-29. Vendor docs show broad tabbed configuration, operation wizards, logs/queues, schedulers, metafields, returns, payouts, markets/catalogs. **Competitor claim.** | Central operation launcher, strong coverage map and discoverable scheduling. | A giant settings form, feature-first navigation and unsafe auto-create defaults. |
| [Emipro documentation](https://docs.emiprotechnologies.com/shopify-odoo-connector/v17/toc.html) and [video tutorials](https://www.youtube.com/playlist?list=PLZGehiXauylZAowR8580_18UZUyWRjynd) | Accessible — 2026-08-29. Vendor docs/videos show dashboards, a Perform Operation wizard, workflow/payment configuration and reporting. **Competitor claim.** | Guided operation execution and commercial-workflow visibility. | Fragmenting setup across many unrelated pages or prioritizing reporting over actionability. |
| [Webkul guide](https://webkul.com/blog/odoo-multichannel-shopify-connector/) | Accessible — 2026-08-29. Vendor material shows feeds, mappings, sync history and multichannel dashboards. **Competitor claim.** | Staging/feeds can help inspection and re-evaluation when presented as evidence. | Busy multichannel abstraction in a Shopify-focused product; duplicate technical concepts in navigation. |

### Screen/function decisions observed

- **VentorTech:** guided configuration, scope readiness, Odoo business-record context,
  background jobs, step-level automation, retry/skip and consistency tooling. Decision:
  put recovery beside the affected record and distinguish link, first publish and update.
- **Teqstars:** marketplace hub, dense instance tabs, shared Operations wizard, scheduled
  action controls, metafield cards and returns/payout surfaces. Decision: preserve one
  operation vocabulary and future breadth seams, but reveal settings progressively.
- **Emipro:** dual commercial dashboard, central Perform Operation, reports/logs and
  separate workflow/payment/location/scheduler configuration. Decision: keep one launcher
  and useful commercial evidence, but make synchronization health and configuration order
  clearer than charts.
- **Webkul:** channel cards, feeds, mapping lists, sync history, filters and re-evaluation.
  Decision: provide an understandable Needs Attention/evidence projection instead of
  forcing every user to learn a second feed-record system.

The interactive V2 blueprint must be traceable to these decisions; it must not copy a
competitor screen merely because it looks familiar.

## 5. Explicit product decisions from the review

| Observation | Proposed decision | Classification |
| --- | --- | --- |
| Mature connectors make operations and queues visible. | Provide one launcher and one run narrative, not domain-specific operation wizards and logs. | Recommendation |
| Recovery is a competitive differentiator. | Make Needs Attention a primary navigation area with contextual safe transitions. | Recommendation |
| Breadth creates configuration density. | Use staged setup, progressive disclosure and domain readiness; avoid a single mega-form. | Recommendation |
| Competitor dashboards often emphasize counts. | Rank health and exceptions above volume; remove vanity cards. | Recommendation |
| Feeds/staging aid review but can add mental models. | Use projections and evidence panels; add a persistent feed model only where a domain requires editable staging. | Recommendation |
| “Real-time” is commonly marketed. | Build and measure near-real-time event paths, display honest observation timestamps and reconciliation state, and avoid an unqualified real-time promise. | Recommendation |
| Visual polish varies widely. | Differentiate through hierarchy, copy, accessibility, response states and safe action design—not decorative novelty. | Recommendation |

## 6. Research limitations

- Vendor screenshots and tutorials show selected states and may lag current releases.
- Public material does not establish internal reliability, test coverage, security or performance.
- No competitor production tenant or destructive operation was exercised.
- Public screen/function coverage is sufficient to lock the current product design, but a
  licensed hands-on benchmark would still be required for an independently verified claim
  that our response time or recovery is superior in production.
- Feature presence is not evidence that the feature belongs in this product’s initial V2 scope.

Accordingly, competitor evidence informs interaction patterns and product questions; official platform sources and repository behavior govern technical decisions.
