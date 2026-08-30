# V2 UX and Visual Design Blueprint

> **Status:** implementation-ready product contract.  
> **Interactive reference:** [Shopify Connector V2 Blueprint](https://shopify-connector-v2-blueprint.mostafaessam94.chatgpt.site).  
> **Production target:** Odoo 19 backend UI. The reference site demonstrates hierarchy, states and interactions; it is not production code and must not introduce a separate SPA.

## 1. Locked design thesis

V2 is a **quiet operations control room** inside Odoo. Healthy work recedes. Risk, uncertainty and required decisions receive the space. “Premium” means that every state is legible, every action is safe, and the product feels coherent across setup, routine operation and recovery.

The visual reference and this document are jointly authoritative:

- this document governs information, behavior, accessibility, responsive rules and backend contracts;
- the interactive reference governs composition, density, hierarchy and visual tone;
- standard Odoo behavior wins where the reference site differs from native list, form, search, chatter, dialog or notification semantics;
- a production implementation may not remove required evidence to match a screenshot.

## 2. User outcomes and task hierarchy

| Rank | User question | Product response |
| --- | --- | --- |
| 1 | Is the selected store safe? | One dominant health band with freshness and a next action |
| 2 | What needs a person now? | Ranked Needs Attention queue with impact, owner and allowed transition |
| 3 | What happened? | Run narrative linked to affected Odoo and Shopify records |
| 4 | What can I do safely? | Context-aware action with authority, scope and consequence visible before confirmation |
| 5 | How much work is moving? | Subordinate activity and workflow measures, never a wall of vanity cards |

## 3. Product shell

### 3.1 Navigation

The connector owns one Odoo application root. The primary order is fixed:

1. Overview
2. Needs Attention
3. Products
4. Orders
5. Inventory
6. Fulfillment
7. Runs
8. Settings

`V2 Blueprint` exists only in the design reference and is not a production menu. Technical objects—job logs, webhook deliveries, mutation evidence and raw readiness diagnostics—live under an Administrator-only technical submenu or contextual smart buttons. There is no separate Error Center or Sync Center.

`Manage stores` is reached from the persistent store switcher, not added as a ninth daily
operations menu. It becomes visible only to users allowed to create/configure stores.

### 3.2 Persistent context

The header always shows:

- current page title;
- selected store name and connection state;
- store switcher, limited by active-company record rules;
- `New operation` when the role and current store state allow it;
- Odoo help/user controls.

Store selection is encoded in the Odoo action context and URL state where supported. It is never held only in a custom JavaScript singleton. Changing the active company revalidates or clears the selected store.

The switcher contains only permitted stores and an optional `All stores` health summary.
`All stores` is read-only aggregation; every command requires one explicit store. A user
cannot infer inaccessible store counts, names or health from the switcher or summary.

### 3.3 Surface selection

| Surface | Implementation choice | Reason |
| --- | --- | --- |
| Overview | Owl client action | Composes multiple bounded read projections and live action state |
| Manage stores | Native Odoo list/form plus guided add-store action | Multi-store administration without a second custom shell |
| Needs Attention | Odoo list/search plus Owl detail panel | Native filtering with evidence-rich resolution |
| Products, Orders | Native list/form/search | High-density record work and familiar Odoo behavior |
| Inventory | Native lists plus focused preview wizard | Mapping and guarded first-push decision |
| Fulfillment | Native list/form plus timeline component | Business record first, connector evidence second |
| Runs | Native list/form plus Owl timeline widget | Searchability plus append-only narrative |
| Settings/setup | Resumable Owl wizard backed by durable Odoo records | Multi-step validation and progressive disclosure |
| Matching/diff | Focused Owl dialog/client action | Side-by-side evidence and explicit selection |

No client-side router, global state library or direct Shopify request is permitted.

### 3.4 Odoo-shell compatibility gate

Before production component implementation, create one bounded Odoo 19 shell spike using
the pinned Odoo SHA. It must prove:

- shared connector navigation can move between Owl client actions and native list/form
  actions without a second router or webclient patch;
- the selected store/action context survives supported navigation and is revalidated on
  company change;
- the optional dark navigation emphasis, control panel, breadcrumbs, dialogs and mobile
  drawer do not conflict with Odoo Enterprise/Community assets;
- 375/768/1366/1440 and RTL work without page-level overflow;
- native keyboard, focus, notification and action-service behavior remains intact.

If pixel-identical persistent side navigation would require replacing Odoo routing or
patching the global webclient, use Odoo-native menus while preserving the blueprint's
hierarchy, tokens and information density. That adaptation is compatibility, not a visual
redesign. The standalone prototype is never embedded in an iframe or shipped as a SPA.

## 4. Visual system

### 4.1 Color tokens

Production SCSS defines semantic tokens once and maps them to Odoo variables where a native equivalent exists.

| Token | Reference value | Usage |
| --- | --- | --- |
| `--sc-ink` | `#19231f` | Primary text |
| `--sc-ink-soft` | `#34423b` | Secondary content |
| `--sc-muted` | `#69766f` | Metadata; must still meet contrast |
| `--sc-canvas` | `#f3f5f2` | Composed-surface background |
| `--sc-surface` | `#ffffff` | Panels and records |
| `--sc-surface-soft` | `#f8faf8` | Quiet rows and grouped content |
| `--sc-line` | `#dfe5e1` | Default border/divider |
| `--sc-line-strong` | `#b7c2bc` | Input and focus-adjacent boundary |
| `--sc-success` | `#287a52` | Healthy/confirmed state and primary action |
| `--sc-success-soft` | `#e8f4ed` | Success surface |
| `--sc-info` | `#71516f` | Connector evidence and neutral platform accent |
| `--sc-info-soft` | `#f1eaf0` | Connector evidence surface |
| `--sc-warning` | `#a86612` | Degraded/review warning |
| `--sc-warning-soft` | `#fcf2dc` | Warning surface |
| `--sc-danger` | `#b23c3c` | Blocked/destructive/critical state |
| `--sc-danger-soft` | `#f9eaea` | Critical surface |
| `--sc-nav` | `#17251f` | Optional connector navigation emphasis; use only if compatible with the Odoo shell |

Color is never the only status carrier. Every semantic color is paired with text and an icon or structural position. Dark mode is not a V2 release requirement; tokens must prevent hard-coded proliferation so it can be added later.

### 4.2 Type, spacing and shape

- Use Odoo’s UI font stack. Do not ship a connector-specific webfont.
- Base composed-surface text: 14 px; body line-height at least 1.45.
- Page title: 28–32 px; section title: 17–20 px; card title: 14–16 px; metadata: never below 11 px in production.
- Spacing follows an 8 px base with 4 px half-steps: `4, 8, 12, 16, 24, 32, 40`.
- Panel radius: 12–14 px; input/button radius: 8–10 px; status pills fully rounded.
- Default panel shadow is subtle and never substitutes for a border. Elevated shadows are reserved for the health hero, dialogs and active detail panels.
- Motion is 140–180 ms for hover/focus transitions. Respect `prefers-reduced-motion`; no looping decorative animation.

### 4.3 Icons and data visuals

- Use Odoo/FontAwesome icons already available in the backend bundle.
- An icon must have an accessible name when it is the only button content; decorative icons are hidden from assistive technology.
- Activity charts are subordinate and use accessible summaries. No chart is the sole source of an operational fact.
- Do not add gauges, 3-D charts, gradients for decoration, merchant stock photography or Shopify-themed illustrations.

## 5. Component contracts

| Component | Required inputs | Behavior | Prohibited behavior |
| --- | --- | --- | --- |
| Store switcher | allowed stores, selected ID, connection label | revalidates company/store scope; persists action context | leaking inaccessible stores; stale global selection |
| Health band | state, title, reason, observed time, next check, primary action | one dominant state and action; compact when healthy | calculated by browser from several calls |
| Workflow card | workflow, readiness, health, freshness, latest run, attention count | opens filtered domain/run view | decorative count-only KPI |
| Status pill | semantic state, visible label | text + icon where space permits | raw internal token or color-only state |
| Attention row | severity, summary, impact, age, owner, allowed actions | selects item; preserves list filters | generic retry action |
| Resolution panel | evidence groups, safe action, consequence, audit requirement | revalidates on submit; stale state returns a conflict | allowing a transition not returned by backend |
| Evidence panel | binding, observation, active hold, latest run, remote link | contextual and compact | cloning the whole connector record form |
| Run timeline | ordered append-only events | newest status summarized; full chronology accessible | raw stack trace as headline |
| Readiness group | check key, label, status, evidence, remediation | groups required/passed/not applicable | activation while a required check fails |
| Diff row | field, source, target, authority, validation, eligibility | protected values visibly disabled | hidden authority or batch-wide implicit override |
| Empty state | state-specific title, explanation, allowed next action | distinguishes healthy, no data, filtered, inaccessible and not configured | one generic “No records” message |
| Skeleton | stable target dimensions | `aria-busy`; no layout shift | spinner-only blank page |

## 6. Screen-by-screen blueprint

### 6.1 Overview

**Route/action:** connector root action; last permitted store or first permitted store.  
**Read contract:** `get_overview_v1(store_id)`.  
**Query budget:** one RPC; server-side aggregation; no per-card RPC.

Layout order:

1. health band with honest freshness;
2. workflow cards for Products, Orders, Inventory and Fulfillment;
3. at most three ranked attention items;
4. seven-day operation summary and recent material activity.

Primary action is resolved from backend `allowed_actions`. Healthy state uses `New operation`; blocked state uses the top safe resolution; disconnected state uses `Repair connection`. The activity summary excludes heartbeat, successful no-op and duplicate-webhook noise.

### 6.2 Needs Attention

**Route/action:** primary menu with saved filters for severity, workflow, owner role, age and action type.  
**Read contracts:** `search_attention_v1(...)`, `get_attention_detail_v1(item_ref)`.  
**Write contract:** `resolve_attention_v1(command)`.

Desktop uses list/detail composition. Tablet/mobile uses list then full-screen detail. Evidence is grouped as `Impact`, `Incoming evidence`, `Current Odoo state`, `Safety decision` and `History`. Bulk transition is rendered only when backend returns one common `action_key` for the exact selected set.

Stale resolution submissions return `state_conflict`, refresh the item and preserve typed reason text. A skipped item always requires a reason and records actor/time. Technical retry is exposed only for an error classified retryable and only after admission is rechecked.

### 6.3 Products

Native product/binding lists expose Connector State, Shopify identity, authority, last observed time and active hold. The Odoo product form gets one compact evidence panel and smart buttons for bindings/runs. Matching uses exact binding first, then accepted deterministic keys; names and fuzzy similarity are explanatory evidence only.

Product export is always `Preview → Review eligible changes → Confirm`. Rows show field-level authority and validation. The confirm command contains the preview fingerprint; a changed source or target invalidates the preview.

### 6.4 Orders

Native sales records remain primary. Lists show import/verification state, Shopify order name, verified total state and active review. The evidence panel links commercial snapshots, customer decision, latest run and Shopify admin URL when authorized.

No UI action silently recreates or rewrites an imported order. Reconnect/re-evaluate actions show preserved Odoo operational effects and Shopify evidence separately.

### 6.5 Inventory

Location mapping is explicit and one-to-one within a store. Similar names are suggestions only. The first Odoo-authoritative push cannot execute until:

1. product/inventory bindings exist;
2. location mapping is valid;
3. current Shopify quantity was observed;
4. preview fingerprint is current;
5. an Administrator confirms affected item-location pairs.

The preview table shows Odoo target, observed Shopify value, delta, mapping and exclusion reason. Later drift checks use the same evidence vocabulary.

### 6.6 Fulfillment

Fulfillment detail tells one sequence: picking event, admission, Shopify fulfillment-order selection, mutation, customer-notification decision, tracking update, readback and terminal outcome. Notification is never inferred or hidden; the effective value is visible before submit and in the run.

An interrupted response shows `Verifying Shopify` and disables resubmit. The product never labels an uncertain remote result `Failed` until verification proves the write was not applied or a human resolves it.

### 6.7 Runs

List defaults to material runs, with filters for state, workflow, trigger, store, error class and date. Run detail shows:

- request, actor/trigger and configuration generation;
- admission checks and operation-scope key;
- jobs and execution attempts;
- redacted Shopify cost/throttle/error observations;
- mutation intent and verification evidence when present;
- affected Odoo/Shopify records;
- terminal result, safe next action and audit trail.

Technical detail is collapsed and restricted to Administrator/Auditor roles as appropriate. Correlation IDs are copyable; credentials, authorization headers and PII snapshots are never rendered.

### 6.8 Settings and setup

Setup is six resumable steps:

1. Store and credential
2. Connection and scopes
3. Workflows and authority
4. Odoo defaults
5. Locations
6. Review and activate

Each step saves durable non-secret values explicitly. Credential replacement uses a separate write-only command and returns presence/verification metadata only. The final review groups readiness as `Action required`, `Passed` and `Not applicable`; activation is server-blocked if any mandatory check fails or the snapshot generation is stale.

After onboarding, Settings edits the same durable records and is grouped by progressive
disclosure rather than a giant tabbed form:

| Group | Administrator controls | Validation/behavior |
| --- | --- | --- |
| Store and connection | display name, canonical domain before first connection, owning company before protected data, replace credential, test/repair, activate/pause/disconnect/retire | token never readable; identity/company changes are blocked or migrated once bindings/evidence exist |
| Workflows | enable/disable Product Import, Product Export, Orders/Customers, Inventory and Fulfillment | enabling or changing a workflow stales readiness; dependent work stays blocked until valid |
| Automation | manual/scheduled/webhook/Odoo-event/reconciliation posture, per-workflow pause/resume and supported cadence | last success, next run and freshness visible; no control whose producer is absent |
| Product and pricing | first-sync source, price authority, imported media, refresh policy, attribute-conflict policy and export field authority | protected fields and name/fuzzy auto-binding cannot be enabled |
| Orders and customers | confirmation policy, manual-gateway policy/list, import window, pending-payment expiry, test-order inclusion and fallback partner | policies preview the resulting quotation/confirmation/review behavior |
| Odoo defaults | warehouse, matching-currency pricelist, sales team, payment term, fiscal position and required tax/payment/shipping mappings | company/currency/accounting compatibility validated before activation/import |
| Inventory and locations | explicit Shopify↔Odoo location mappings, scheduled push posture and first-push status | first push always requires current observation, preview fingerprint and Administrator confirmation |
| Fulfillment | Odoo-controlled or exact bidirectional mode, tracking and customer-notification posture | mode switch is verified; effective notification value is explicit per command/run |
| Security and evidence | permitted role posture, redacted audit/retention summary and technical evidence links | users/companies remain managed through Odoo groups/rules; no secret/PII reveal |
| Advanced rollout | temporary UI/gateway/runtime migration modes and rollback reason | Administrator-only, audited, collapsed and removed after contraction |

Not configurable in ordinary Settings: pinned API version, GraphQL documents/endpoints,
binding/idempotency/operation-scope rules, tenant/generation fences, mutation verification,
retry/pagination hard safety bounds or raw credentials. The Administrator controls product
policy, not the ability to bypass correctness.

### 6.9 Store management and multiple stores

The store-management list shows permitted store name, canonical domain, company,
connection/activation state, overall health, enabled workflows, freshness and active
attention count. Actions are `Add store`, `Resume setup`, `Open`, `Repair connection`,
`Pause`, `Disconnect` and `Retire` as returned by server authorization.

- Adding another store creates an isolated draft and starts the same six-step setup.
- Each store owns credentials, settings, generation, mappings, bindings, checkpoints,
  runs/jobs and rollout modes.
- Multiple stores may share one company; same-company does not permit cross-store child
  records or commands.
- No configuration is cloned automatically. A future explicit copy wizard may copy only
  allowlisted non-secret defaults and must run readiness independently.
- There is no designed store-count licensing cap; performance is qualified against the
  multi-store profiles in `09-test-observability-release-blueprint.md`.

## 7. Complete response-state matrix

Every composed screen implements all states below before it is considered complete.

| State | Visual response | Action |
| --- | --- | --- |
| Initial loading | shape-stable skeleton, `aria-busy=true` | none |
| Background refresh | timestamp plus quiet progress indicator | existing safe actions remain unless stale |
| Healthy empty | success icon, reason no action is needed | optional next operation |
| Unconfigured empty | setup explanation | begin/resume setup |
| Filtered empty | name active filters | clear filters |
| Permission empty | explain access boundary without record counts | request access outside product |
| Partial data | keep valid sections; mark unavailable section and freshness | retry the bounded query |
| Retryable technical failure | human summary, affected scope, next attempt | retry only if backend allows |
| Manual review | evidence, owner role, allowed transitions | explicit resolution |
| Terminal failure | reason and no-safe-action statement or remediation | no generic retry |
| Stale command | preserve input; refresh current evidence | review and resubmit |
| Offline/network loss | preserve unsent form state; do not claim submission | retry transport |
| Success | concise result and linked run | continue/open result |

## 8. Responsive and RTL rules

| Width | Rule |
| --- | --- |
| `≥ 1200 px` | full navigation; multi-column overview; attention list/detail |
| `768–1199 px` | collapsible navigation; two-column cards; detail may overlay |
| `375–767 px` | single column; drawer navigation; full-screen resolution; tables use native horizontal containment or mobile list view |
| `< 375 px` | supported without clipped actions, though not a formal screenshot baseline |

- Mandatory verification widths: 375, 768, 1366 and 1440 px.
- Logical CSS properties (`margin-inline`, `padding-inline`, `inset-inline`) are required for custom styles.
- RTL reverses spatial flow but not chronological event ordering; timeline labels remain semantically ordered.
- Primary/destructive button order follows Odoo locale conventions and must be keyboard-logical.
- No page-level horizontal overflow is allowed. Wide native tables may scroll inside their own labeled region.

## 9. Accessibility contract

- WCAG 2.2 AA is the release target for the connector-owned UI.
- Every function is keyboard-operable; focus is visible and returns to the invoking control after dialogs close.
- Dialogs trap focus, expose a title/description and do not close destructive work on accidental outside click.
- Status updates use a restrained live region; polling does not repeatedly announce unchanged content.
- Form errors are summarized, linked to fields and available as text.
- Touch targets are at least 40×40 px for connector-composed controls.
- Text contrast is at least 4.5:1; non-text indicators and focus boundaries at least 3:1.
- Tables use real headers and accessible names; interactive rows do not contain conflicting nested buttons.
- Dates expose absolute values and may add human-relative text. Numbers/currency use the user’s locale.

## 10. Copy system

Use business language first and diagnostic tokens second.

| Avoid | Use |
| --- | --- |
| `failed_retryable` | “Temporarily delayed. Next attempt in 3 minutes.” |
| `blocked_manual_review` | “A reviewer must choose the matching product.” |
| “Sync now” | “Import eligible orders” / “Preview inventory changes” |
| “Something went wrong” | “Shopify did not confirm the tracking update. No duplicate request will be sent while verification runs.” |
| “Real-time” | “Observed 2 minutes ago · next check 10:45” |
| “Retry all” | a specific, eligibility-scoped action |

Every error sentence answers: what happened, what is affected, what the connector did to remain safe, and what happens next.

## 11. Frontend package structure

Production files remain within the existing addon family:

```text
shopify_connector_core/static/src/
├── components/
│   ├── attention_detail/
│   ├── health_band/
│   ├── readiness_group/
│   ├── run_timeline/
│   └── status_pill/
├── services/
│   └── connector_rpc_service.js
├── views/
│   ├── attention_workspace/
│   ├── overview/
│   └── setup/
├── scss/
│   ├── _tokens.scss
│   ├── _utilities.scss
│   └── connector_v2.scss
└── xml/
    └── connector_v2.xml
```

Each component folder contains `.js`, `.xml` and a colocated `.test.js` when it owns behavior. Do not create one JS/XML file per trivial atom; do not recreate Odoo’s button, dropdown, pagination or notification systems.

## 12. UX definition of done

A screen is complete only when:

- its DTO and allowed actions are implemented and versioned;
- every response state in Section 7 is exercised by an automated fixture;
- keyboard, focus, screen-reader labels and reduced motion pass;
- 375/768/1366/1440 and RTL screenshots pass review;
- role tests prove hidden controls are also server-forbidden;
- the screen uses at most one initial RPC and avoids N+1 follow-ups;
- destructive or remote-write actions display authority, impact and consequence;
- user testing meets the task measures in `01-product-experience.md`;
- visual review matches the reference’s hierarchy and density without fighting Odoo conventions.

## 13. Official design references

- [Shopify app design guidance](https://shopify.dev/docs/apps/design)
- [Odoo 19 Owl components](https://www.odoo.com/documentation/19.0/developer/reference/frontend/owl_components.html)
- [Odoo 19 frontend services](https://www.odoo.com/documentation/19.0/developer/reference/frontend/services.html)

