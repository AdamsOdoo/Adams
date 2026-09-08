# Astra UI redesign — proposal 01

Date: 2026-09-08. Status: **proposed, awaiting user design approval**.
Owner: Astra. This is a design checkpoint within the authorized V2 development program, not a new V3 connector or a release approval.

The user explicitly requested that Astra redesign the UI from the user's perspective, review competitor documentation, show the proposal, and obtain approval before implementation. This request supersedes the previous assumption that the old V2 prototype's visual design is already approved. Existing safety, data, permission and native-Odoo requirements remain binding. Backend diagnosis and repair can continue while the design is reviewed.

## Reviewable proposal

Open [the interactive walkthrough](./design-review/proposal-01.html). All records, times and outcomes are sample data. Actions are local simulations, with no network requests or store changes. The prototype demonstrates a proposed experience; it does not certify a backend command, readback, permission check or release gate.

The design retains Odoo navigation and dense record work, with a restrained plum accent, quiet status rows, and focused decisions. It avoids a replacement application shell, a new frontend router and a custom component framework. Production uses native Odoo lists, forms, dialogs and action navigation; Owl is limited to composed views and guided decisions. Pixel compatibility requires the existing Odoo shell spike before implementation.

| Walkthrough | User goal and complete proposed path |
| --- | --- |
| Store setup | Store selector → New store → connect → workflow authority → Odoo defaults → location → readiness → activation → separate first-stock approval |
| Daily operation | Overview → highest-impact exception → resolution → updated workflow state → run history |
| Held order | Needs Attention → compare ambiguous product candidates → reject conflicting historical binding → explicit link → revalidate whole order → Odoo order result |
| Initial stock | Inventory → explicit source/destination → old/new quantities → confirm exact scope → send → readback evidence |
| Product update | Products → owned-field diff → protected fields and preserved variants/media → confirm → readback result |
| Uncertain shipment | Fulfillment → order/location/items/tracking evidence → query Shopify → adopt exact existing fulfillment → no duplicate send |
| Investigation | Runs → business narrative and linked outcome → optional administrator diagnostics |
| Pause | Settings → consequence → confirmation → new work paused; already-sent work may still finish |

Setup values are illustrative. The six visible phases do not replace the existing durable semantic setup-step contract. The operational navigation remains Overview, Needs Attention, Products, Orders, Inventory, Fulfillment, Runs and Settings. Manage stores remains a context-level action rather than a ninth daily menu.

## Competitor evidence refreshed on 2026-09-08

These are observations of documentation, not hands-on certification or claims that a competitor lacks unmentioned features. Design implications below are Astra's inference.

| Primary vendor documentation | Observed pattern | Proposed application |
| --- | --- | --- |
| [TeqStars Odoo 19 instance setup](https://docs.teqstars.com/19.0/applications/shopify/setup/create_instance.html) | Workflow-specific settings, processing timestamps, assigned failure activities and instance confirmation | Group setup by the user's task; put authority and consequences before activation; show observation freshness and issue ownership in the work surface. |
| [Emipro queue guide, v17](https://docs.emiprotechnologies.com/shopify-odoo-connector/v17/shopify-odoo-operations/queue.html) and [Log Book](https://docs.emiprotechnologies.com/shopify-odoo-connector/v17/sales-report-and-log-book.html) | Batch queues expose per-record states and diagnostic lines; a force-done operation has irreversible processing consequences | Preserve per-record evidence but lead with the business issue and safe next step. Distinguish request accepted, execution completed and remote result confirmed. Avoid a generic force-success control. The reviewed pages are v17, not evidence of current v19 parity. |
| [Webkul connector user guide](https://webkul.com/blog/odoo-multichannel-shopify-connector/) | Incoming feeds can expose missing records and permit correction/re-evaluation; imports have dependencies | Show a held order and its missing prerequisite together, and return the user to that order after correction. Do not require learning separate queue, feed and error-center concepts. |
| [VentorTech field-mapping guide](https://ecosystem.ventor.tech/faq/e-commerce-connectors/common-questions/step-by-step-guide-for-mapping-product-fields-in-e-commerce-integration-module/) | Field mapping is explicit; the guide uses technical model/API names and developer-mode setup | Preserve explicit ownership while expressing approved fields and protected fields in the preview. Advanced mapping stays administrator work; ordinary recovery requires no debug mode. |

Competitive improvement is a hypothesis to test: faster identification of the real issue, fewer navigation steps to resolution, and correct understanding of side effects. This review does not justify adding payouts, refunds, an analytics warehouse or other deferred domains.

## Approval scope and remaining design coverage

Approval of proposal 01 accepts its visual direction and the demonstrated task structure. It does **not** waive the following design/implementation checks:

- Complete empty, loading, stale, offline, partial-success, permission-denied and interrupted-operation states, including remote verification that finds no match or multiple matches.
- Real credential onboarding/replacement, failed scopes, setup validation, resume after refresh, additional-store management, disconnect/retire and reconnect/backfill.
- Administrator and User visible roles, with existing server-enforced operator/reviewer/auditor capabilities; the prototype is an Administrator view only.
- Native record links, filtering, selection/bulk eligibility, pagination, actionable validation, keyboard/focus/announcements, mobile/tablet, dark theme and RTL.
- Current DTO/action availability, stale-preview rejection, server authorization and exact store/company isolation. A simulated action cannot be wired until its production contract and tests exist.
- Representative end-to-end UAT and the existing human usability gate. A quick prototype review is not that campaign.

We will prove one complete native Odoo slice first (held order → matching → revalidation → order result and history), review fidelity, then extend the same patterns. A new design approval is needed only for a material change to this direction or workflows, not every button or routine implementation detail.

## Review questions

1. Does the Overview make the next useful action obvious?
2. Can you understand and complete a held-order decision without technical knowledge?
3. Before approving stock/product changes, can you tell precisely what will change and where?
4. Does the navigation and visual density feel suitable for daily work inside Odoo?

Validation: JavaScript syntax and a DOM-adapter smoke check passed for eight navigation views, candidate eligibility, order/stock/shipment/product outcomes and six-phase setup progression. Source has no external requests. This verifies local state logic only. Browser inspection is pending: the remote browser rejected the local preview URL, and the local browser download timed out. Responsive layout, dark theme, keyboard/focus and accessibility are not claimed as tested. No production UI code is changed by this design checkpoint.
