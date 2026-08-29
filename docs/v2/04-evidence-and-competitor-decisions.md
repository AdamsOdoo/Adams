# Evidence and Competitor Decisions

> **Access date:** 2026-08-29. External claims are classified. Vendor documentation demonstrates vendor-presented behavior; it is not independent proof of implementation quality.

## 1. Current-product evidence

| Evidence | Status | Classification | Design consequence |
| --- | --- | --- | --- |
| Accepted DEC-008/009/010/011/012/013/014 and rejected approaches RA-001–RA-023 | Accessible in repository | Fact | Preserve accepted module, identity, retry, inventory, fulfillment and operator-flow invariants. |
| Accepted U0 prototype (`docs/09-ui-prototype`) | Accessible in repository | Fact | Preserve ranked dashboard, selective Owl, Odoo-native views, accessibility, responsive and RTL baseline. |
| Current draft release PR #210, head `44da1e…` | Accessible in GitHub | Fact | Treat current code as migration source; do not modify the release PR. |
| Large core API/setup/store/credential/dispatch and setup UI files observed at release head | Accessible in GitHub | Fact | Prioritize characterization and seam extraction; file size alone is a risk signal, not proof of incorrectness. |
| Core + domain + product-export + webhook addon family at release head | Accessible in GitHub | Fact | Preserve domain family; evaluate webhook satellite consolidation only with lifecycle proof. |

## 2. Official platform evidence

| Source | Access | Classification | V2 use |
| --- | --- | --- | --- |
| [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks) | Accessible — 2026-08-29 | Official fact | Design for duplicate/missed/out-of-order delivery and reconciliation; acknowledge quickly. |
| [Shopify API limits](https://shopify.dev/docs/api/usage/limits) | Accessible — 2026-08-29 | Official fact | Cost-aware per-store governor, bounded requests and observable throttle delay. |
| [Shopify app design](https://shopify.dev/docs/apps/design) | Accessible — 2026-08-29 | Official guidance | Clear hierarchy, familiar patterns, accessible feedback and safe actions. |
| [Odoo 19 Owl components](https://www.odoo.com/documentation/19.0/developer/reference/frontend/owl_components.html) | Accessible — 2026-08-29 | Official fact/guidance | Use Owl within Odoo’s component system for interaction-dense surfaces. |
| [Odoo 19 services](https://www.odoo.com/documentation/19.0/developer/reference/frontend/services.html) | Accessible — 2026-08-29 | Official fact/guidance | Keep client side effects in services and use explicit dependencies. |
| [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html) | Accessible — 2026-08-29 | Official guidance | Batch operations, avoid N+1 and profile before structural replacement. |
| [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html) | Accessible — 2026-08-29 | Official guidance | ACLs, record rules, safe ORM usage and explicit authorization. |
| [Odoo 19 testing](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html) | Accessible — 2026-08-29 | Official guidance | Layered Python, tour and integration tests. |

## 3. Competitor review

| Competitor | Screen/feature evidence | Learn | Avoid |
| --- | --- | --- | --- |
| [VentorTech Shopify Connector](https://ecosystem.ventor.tech/product/odoo-shopify-connector-pro/) and [release notes](https://ecosystem.ventor.tech/release-notes/odoo-shopify-connector-pro/) | Accessible — 2026-08-29. Vendor docs/screens show guided configuration, queues, per-order automation, consistency checks, contextual recovery and link-vs-publish separation. **Competitor claim.** | Make recovery, queue evidence, consistency and safe linking first-class; show scope readiness clearly. | Copying Odoo-native visuals without simplifying information architecture. |
| [VentorTech queue priority](https://ecosystem.ventor.tech/faq/e-commerce-connectors/common-questions/how-the-connector-prioritizes-background-jobs/) | Accessible — 2026-08-29. Vendor describes priority behavior. **Competitor claim.** | Explicit lanes and human-readable priority rationale. | Depending on an external queue package as the default; RA-004 remains binding. |
| [Teqstars Odoo 19 connector](https://docs.teqstars.com/19.0/applications/shopify.html), [instance setup](https://docs.teqstars.com/19.0/applications/shopify/setup/create_instance.html) | Accessible — 2026-08-29. Vendor docs show broad tabbed configuration, operation wizards, logs/queues, schedulers, metafields, returns, payouts, markets/catalogs. **Competitor claim.** | Central operation launcher, strong coverage map and discoverable scheduling. | A giant settings form, feature-first navigation and unsafe auto-create defaults. |
| [Emipro documentation](https://docs.emiprotechnologies.com/shopify-odoo-connector/v17/toc.html) and [video tutorials](https://www.youtube.com/playlist?list=PLZGehiXauylZAowR8580_18UZUyWRjynd) | Accessible — 2026-08-29. Vendor docs/videos show dashboards, a Perform Operation wizard, workflow/payment configuration and reporting. **Competitor claim.** | Guided operation execution and commercial-workflow visibility. | Fragmenting setup across many unrelated pages or prioritizing reporting over actionability. |
| [Webkul guide](https://webkul.com/blog/odoo-multichannel-shopify-connector/) | Accessible — 2026-08-29. Vendor material shows feeds, mappings, sync history and multichannel dashboards. **Competitor claim.** | Staging/feeds can help inspection and re-evaluation when presented as evidence. | Busy multichannel abstraction in a Shopify-focused product; duplicate technical concepts in navigation. |

## 4. Explicit product decisions proposed from the review

| Observation | Proposed decision | Classification |
| --- | --- | --- |
| Mature connectors make operations and queues visible. | Provide one launcher and one run narrative, not domain-specific operation wizards and logs. | Recommendation |
| Recovery is a competitive differentiator. | Make Needs Attention a primary navigation area with contextual safe transitions. | Recommendation |
| Breadth creates configuration density. | Use staged setup, progressive disclosure and domain readiness; avoid a single mega-form. | Recommendation |
| Competitor dashboards often emphasize counts. | Rank health and exceptions above volume; remove vanity cards. | Recommendation |
| Feeds/staging aid review but can add mental models. | Use projections and evidence panels; add a persistent feed model only where a domain requires editable staging. | Recommendation |
| “Real-time” is commonly marketed. | Display honest observation timestamps and reconciliation state; do not promise real-time. | Recommendation |
| Visual polish varies widely. | Differentiate through hierarchy, copy, accessibility, response states and safe action design—not decorative novelty. | Recommendation |

## 5. Research limitations

- Vendor screenshots and tutorials show selected states and may lag current releases.
- Public material does not establish internal reliability, test coverage, security or performance.
- No competitor production tenant or destructive operation was exercised.
- Feature presence is not evidence that the feature belongs in this product’s initial V2 scope.

Accordingly, competitor evidence informs interaction patterns and product questions; official platform sources and repository behavior govern technical decisions.
