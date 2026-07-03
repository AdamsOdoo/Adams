# Master Blueprint — Part D: UI/UX Screen Design Blueprint

> **Proposed for ChatGPT review — not accepted.** Screen-level design
> blueprint for the operator-facing experience of the premium **Odoo 19 ↔
> Shopify Connector**, required before implementation of any operator-facing
> screen (`master-blueprint.md` "Criteria for when implementation may later
> be opened", criterion 1). Companion decision record:
> [`../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)
> (Status: **Proposed for ChatGPT review**). Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-013**, Proposed for ChatGPT review). Prepared in **Master Blueprint
> Sprint D**, starting base commit
> `b6199f78064ae4e1934bccee630a14b3d7eef438` (PR #74 "Accept Master
> Blueprint Sprint C … (DEC-015)" merged into `Shopify-connector`).

## Status

- **Proposed for ChatGPT review — decides nothing.** This document is a
  proposal. Nothing here is accepted, and acceptance of it (if it comes)
  would still not authorize implementation.
- **Documentation only.** The no-code gate (`CLAUDE.md` §4–§5) is in force.
  This part produces **no** Odoo models, views, XML, security files,
  manifests, tests, or CI. It invents **no** exact model names, field
  names, view/menu/action XML IDs, security group IDs, or access CSV rows
  (those remain **MBQ-01/02/03/44**, open).
- **This is a screen blueprint, not wireframe artwork and not code.** It
  specifies each screen's purpose, users, entry points, information,
  actions, states, and links at the level a designer/implementer needs to
  produce consistent, premium, Odoo-native screens — not pixel layouts or
  final copy strings.
- **Part E remains Not started.** This part does not begin the
  implementation-planning bridge (Part E) and produces no implementation
  tickets, sequencing, or task templates.
- **Implementation remains blocked.** See *Implementation remains blocked*
  at the end.
- **Scope of resolution:** proposes to **partially resolve MBQ-53** (see
  *MBQ-53 disposition* below and the open-questions register). All other
  register rows are **carried forward untouched**; in particular
  **MBQ-01/02/03/22/44/45** and **MBQ-33/34/41/60/61/62/63** remain open,
  and this part does **not** decide any of them.

## Method and label discipline

This blueprint converts three already-accepted layers into screens:

1. the ten operator flows of **DEC-012** (behaviour) —
   [`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md);
2. the substrate/domain contracts of Master Blueprint **Part A/B/C**
   (concepts, states, error classes, guards) — accepted via
   **DEC-013/DEC-014/DEC-015**;
3. the product-experience quality bar of
   [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md)
   (Principles P1–P12) and
   [`../02-product/product-vision.md`](../02-product/product-vision.md)
   (premium quality bar; differentiation theme 2 — a unified command center
   **and** a recovery-first error center *together*).

**Every statement is labelled** so an open item is never read as a decision
(`CLAUDE.md` §8):

- **[Accepted fact]** — restates something an accepted DEC/AR fixed, or an
  existing source-cited Odoo/Shopify platform fact. Cited to its accepted
  source; not re-decided here.
- **[Screen blueprint proposal]** — a screen-design element this Part D
  introduces (part of what ChatGPT is asked to accept). Never authorizes
  code; never fixes an exact identifier.
- **[Recommendation]** — a proposed direction on a still-open question,
  named as a recommendation, decision-owner preserved (e.g. MBQ-33/34/41).
- **[Open question — MBQ-nn]** — unresolved; carried forward; never
  asserted as decided.

**Odoo-native discipline.** Screens are described in Odoo-native vocabulary
(app/menu/action, list/form/kanban/pivot/search-filter/statusbar/wizard
dialog, settings surface, chatter/audit log, smart buttons) **as interaction
patterns**, never as committed XML IDs or view definitions. Where an *exact
Odoo or Shopify identifier* appears (e.g. `res.partner`, `sale.order`,
`sale.order.line`, `stock.picking`, `account.journal`, `carrier_tracking_ref`,
`free_qty`, `stock.quant`, `backorder_id`, `assignedLocation`,
`ir.model.access`, `Product.status`, `publishablePublish`,
`INVENTORY_LEVELS_UPDATE`), it is an **existing, source-cited platform
identifier** carried from Part A/B/C — **not** a connector-proposed name.
All **connector** model/field/menu/group names remain proposed-direction-only
(MBQ-01/02/03/44).

**What this Part D does NOT do:** it does not draw wireframe artwork; it does
not write final user-facing copy strings (exact wording is **MBQ-22**, open —
this part gives *copy guidelines and microcopy patterns* only); it does not
create implementation tickets; it includes **no** screenshots (none are
available in-repo to cite for the connector's own screens — the
`docs/00-source-materials/screenshots/**` trees are competitor-evidence
placeholders, not this product's screens); and it does not touch DEC-003
through DEC-015 or any accepted AR/RA row.

## How the accepted context is reused (not re-litigated)

| Accepted source | What it fixes | How screens use it |
| --- | --- | --- |
| DEC-003 | MVP scope; no blind create; no destructive write without preview; single-store/single-company | Bounds every screen's actions; single-store framing of navigation |
| DEC-004 | Custom-app / offline-token / GraphQL-first; credential masking | Setup wizard credential step; store settings credential/API-health |
| DEC-005 | Webhook + `ir.cron` queue + reconciliation | Dashboard freshness; sync center sources; "never webhook-only" |
| DEC-006 | Store-scoped binding; match-key priority; no name-only match | Matching center; duplicate-prevention previews; binding review |
| DEC-007 | Variant/media/price boundaries; first-push guard; notification default; financial evidence | Product/inventory/fulfillment/order screen guards |
| DEC-008 | Layered addon family; one shared substrate | One dashboard/sync/error center, never per-domain clones |
| DEC-009 | 16 error classes; classified retry; audit/log requirements | Error center; state/microcopy catalog; retry affordances |
| DEC-010 | Inventory source-of-truth, location mapping, first-push posture | Inventory screens |
| DEC-011 | FulfillmentOrder-based fulfillment; notification posture; operation idempotency | Fulfillment screens |
| DEC-012 | Ten operator flows; conceptual four-role model | The screen inventory itself |
| DEC-013 (Part A) | Substrate concepts; 6 sources / 10 states / 16 classes; operator-surface blueprints; feature flags; four-role access | Global conventions + every core screen |
| DEC-014 (Part B) | Product/customer/order flows; email-only key; no dedicated order screen; create/bind policy | Product/customer/order/matching screens |
| DEC-015 (Part C) | Inventory/fulfillment blueprints; tracking fields; location-mismatch guard | Inventory/fulfillment screens |

AR-002 through AR-012 are **Accepted**
([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md));
RA-001 through RA-023 are **binding rejected approaches**
([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)) —
checked before drafting; none is reintroduced. Notably **RA-013**
(no parallel per-domain dashboards) directly shapes the single-command-center
navigation below.

---

## 0. Screen inventory (master list)

The ten DEC-012 flows and the Part A/B/C surfaces resolve into the following
operator-facing screens. **[Screen blueprint proposal]** for the inventory
and grouping; the underlying surfaces are **[Accepted fact]** per the cited
part.

| # | Screen / surface | Owning module (DEC-008) | Primary DEC-012 flow | Accepted-surface source |
| --- | --- | --- | --- | --- |
| S1 | Connector app entry + global navigation | core | 1–10 | Part A §F/§G/§H; DEC-008 |
| S2 | Store selector / multi-store visibility (single-store MVP) | core | 2 | DEC-003; Part A §B.1 |
| S3 | Setup wizard (11 steps) | core (+domain steps) | 1 | Part A §E |
| S4 | Store settings surface (profile, credentials/API health, source-of-truth, flags, notifications, inventory/fulfillment, gateway→journal) | core (+domain tabs) | 2 | Part A §B/§I; Part B §C.10; Part C |
| S5 | Dashboard / command center | core | 3 | Part A §F |
| S6 | Sync center / job monitor (list + job detail) | core | 4 | Part A §G |
| S7 | Error center / recovery (+ manual-review queue) | core | 5 | Part A §H |
| S8 | Matching / duplicate-prevention center (product, customer, order-resolution) | core surface, domain data | 6 | Part A §C.5/§H; Part B §A.6/§A.9/§B.3/§B.9 |
| S9 | Product screens (import preview, export preview/diff, update diff) | product | 7 | Part B §A |
| S10 | Customer screens (import/matching, fallback visibility) | sale | 6/7 | Part B §B |
| S11 | Order surfaces (queue + detail via S6/S7, evidence breakdown) — **no dedicated order-import screen** | sale | 7 | Part B §C.14 |
| S12 | Inventory screens (location mapping, first-push preview, sync/reconciliation status) | inventory | 8 | Part C §A |
| S13 | Fulfillment screens (queue + detail, tracking, location review) | fulfillment | 9 | Part C §B |
| S14 | Permissions/roles visibility (conceptual, embedded across surfaces) | core | 10 | Part A §J |

**Cross-cutting layers** (not standalone screens, applied to all of the
above): §14 states & microcopy patterns; §15 cross-screen consistency; and
the *premium UI/UX acceptance checklist*.

**Single shared surface rule [Accepted fact — DEC-008 §K rule 2; RA-013]:**
there is exactly one dashboard (S5), one sync center (S6), and one error
center (S7). Domain modules *contribute data/categories* to these via the
Part A §A.5 seams; they never build parallel dashboards or a second error
center. This is a hard navigation constraint, not a preference.

---

## 1. App entry and navigation (S1, S2)

### S1 — Connector application entry + global navigation

- **Purpose:** give the operator one coherent home for the connector and a
  predictable path between setup, operations, monitoring, recovery,
  matching, mappings, and settings — the "single command center as the
  operator's home" **[Accepted fact — setup-ux P5; product-vision
  differentiation theme 2]**.
- **Primary users:** all four roles (Administrator, Operator, Reviewer,
  Auditor) **[Accepted fact — Part A §J.2: all roles view]**; affordances
  render role-conditionally (§13).
- **Entry points:** the connector's top-level Odoo application/menu.
  **[Screen blueprint proposal]** a **dedicated top-level connector app**
  (one app, not scattered menus — setup-ux P5 anti-pattern: "health in one
  menu and errors three menus away"). Exact app/menu/action **XML IDs are
  MBQ-03, open** — this proposes the IA, not the identifiers.
- **Key information shown:** primary menu regions **[Screen blueprint
  proposal]**, deliberately separating the five concerns the task names:
  1. **Operations** → Dashboard (S5), Sync center (S6).
  2. **Recovery** → Error center / manual review (S7).
  3. **Matching & mappings** → Matching center (S8), location mapping (S12),
     gateway→journal mapping (within S4).
  4. **Setup** → Setup wizard (S3), re-runnable during reconnect.
  5. **Settings** → Store settings (S4).
  A persistent **connection-health indicator** (state + API health,
  Part A §B.1/§B.3) is visible from every region — glanceable health that
  encodes cause + fix hint **[Accepted fact — setup-ux P4/P5; product-vision
  "glanceable, actionable health"]**.
- **Primary actions:** navigate to any region; open the persistent
  health/exception affordance which routes to the filtered sync/error view
  (every dashboard count is clickable, §5).
- **Blocked states:** when the store is `setup_incomplete` **[Accepted fact
  — Part A §B.1 connection state; §E.4]**, navigation still exposes Setup
  (S3) and read-only monitoring, and business-operation actions are absent
  (not merely disabled without explanation) — the operator is routed to
  "finish setup" with the exact remaining steps (§3, §14 empty/first-run).
- **Links to related screens:** all of S3–S14.
- **Accepted decision dependencies:** DEC-008 single-substrate & family
  (S1 must not fork per-domain menus for monitoring/recovery); DEC-012
  ten-flow structure; Part A §F/§G/§H surfaces.
- **Open MBQ dependencies:** MBQ-03 (exact menu/action XML IDs);
  MBQ-45 (whether one role-gated app or an admin/functional split at menu
  level — carried forward, not decided here); MBQ-54 (module
  uninstall/disable lifecycle affects which menu regions render).

### S2 — Store selector / multi-store visibility (single-store MVP)

- **Purpose:** name the store every record is scoped to, and keep the UI
  honest about which store an action affects — "surface which store/company
  this belongs to on records" **[Accepted fact — setup-ux P10; Part A §B.1
  every record carries a store reference]**.
- **Primary users:** all roles (view); Administrator connects/configures.
- **Entry points:** a store context indicator in the app header; the store
  profile in S4.
- **Key information shown:** the connected store's display name + shop domain
  (`*.myshopify.com`) and its connection state **[Accepted fact — Part A
  §B.1]**.
- **Primary actions:** (single-store MVP) view the active store; open store
  settings (S4). No store-switching action is required in Phase 1.
- **Blocked states:** none beyond `setup_incomplete`/`disconnected` display.
- **Links to related screens:** S3 (setup), S4 (store settings), S5.
- **Accepted decision dependencies:** DEC-003 (Phase 1 is single-store,
  single-company; keys are multi-store-*safe* but the UI is single-store);
  Part A §B.1 (per-store scoping via record rules, never `sudo()`).
- **Open MBQ dependencies:** **MBQ-46** (multi-company/multi-store
  permission isolation — later phase). **[Screen blueprint proposal]** the
  store selector is designed as a *concept slot* so a future multi-store
  phase can turn it into an actual selector without a redesign; Phase 1
  renders it as a single-store context label. **This does not decide
  MBQ-46.**

---

## 2. Setup wizard screens (S3)

Converts DEC-012 flow 1 and Part A §E (the accepted 11-step sequence). The
wizard is an Odoo-native guided flow **[Accepted fact — setup-ux P1: guided,
in-product, not a doc in another tab]**.

### S3 — Setup wizard

- **Purpose:** take an Administrator from "module installed" to "connected,
  ready, and safe to enable sync" without hand-editing server config or
  pasting long scope strings, proving readiness **before** first sync
  **[Accepted fact — setup-ux P1/P2; Part A §E]**.
- **Primary users:** Connector Administrator (runs the wizard) **[Accepted
  fact — Part A §J.2: Run setup wizard = Administrator only]**. Other roles
  cannot run it; they may see setup status read-only.
- **Entry points:** first install / `setup_incomplete` state; a "reconnect /
  re-run setup" action from S4; a dashboard first-run empty state (§5) that
  routes here.
- **Key information shown — the 11 accepted steps [Accepted fact — Part A
  §E.1], rendered as an Odoo wizard/stepper [Screen blueprint proposal]:**
  1. **Welcome / prerequisites** — up-front hosting disclosure (Odoo.sh/
     on-prem; **Odoo Online excluded**).
  2. **Store connection** — name + shop domain (single store).
  3. **Credential entry** — guided custom-app credential flow (not one-click
     OAuth); masked entry; plain-language explanation of the custom-app
     model.
  4. **Scope list presentation** — the wizard *presents* the minimal
     required scope list (never a free-text paste); explains scopes are
     granted Shopify-side; the wizard does not grant scopes itself.
  5. **Test connection** — a discrete, explicit action reporting pass/fail +
     reason.
  6. **Readiness checks** — pass/fail surface (candidate checks: granted
     scopes, HTTPS/`web.base.url`, webhook reachability, worker/queue
     presence, credential validity).
  7. **Sync direction choices per domain** — bounded to DEC-003's accepted
     directions; no unsupported direction offered.
  8. **Source-of-truth choices** — product first-sync strategy + price
     source-of-truth; a selection is **required, never silently defaulted**.
  9. **Notification default** — plain language, **default off, never
     pre-checked on**; enabling is an explicit opt-in.
  10. **Inventory first-push scheduling** — may *schedule* the first-push
      guard for later but **never executes a first push** and **never
      silently skips/auto-completes the guard**.
  11. **Final readiness summary** — connection status, enabled domains +
      directions, source-of-truth choices, notification default, and
      first-push-pending state, **on one screen before leaving setup**.
- **Credential input and safety [Accepted fact — Part A §B.2; DEC-004;
  setup-ux P1]:** the credential is entered masked, **never displayed again
  after save**, never logged; the UI thereafter shows only presence +
  last-validated timestamp + rotation state. Inline help explains the
  custom-app model (P3 progressive disclosure).
- **Test connection & scope/readiness checks [Accepted fact — Part A
  §E.2/§E.3/§E.6]:** run as `setup_readiness_check` jobs through the normal
  queue — visible, logged, re-runnable, read-only; results feed the dashboard
  connection-health card. `setup_readiness_check` and
  `export_preview_dry_run` are the **only** job sources allowed to run during
  setup, and they never create/update a business record.
- **First-run guidance:** each step carries inline help on jargon fields
  (P3); a persistent "what's left" indicator; the final summary (step 11) is
  the single confirm-before-leaving surface.
- **Guardrails before enabling sync [Accepted fact — Part A §E.4/§E.5;
  §I.5]:** **no business sync/write job is enqueueable-to-run for a store
  whose setup is incomplete** (the accepted DEC-012 safe-defaults rule);
  **[Recommendation — Part A §E.5]** the guard is additionally re-checked at
  execution time (defense in depth). The first-push guard cannot be silently
  skipped; the notification default cannot be pre-checked on; **no feature
  flag may bypass any of these guards (§I.5)**. These guardrails are enforced
  in the substrate — the wizard surfaces them, it does not own them.
- **Primary actions:** advance/return between steps; run Test connection; run
  Readiness checks; make required selections; **Finish** (only when required
  steps complete). "Save & exit" leaves an explicit `setup_incomplete` state.
- **Blocked states:** a failed Test connection or a failed essential
  readiness check blocks "Finish" with a named reason and a suggested fix
  (never a generic "not configured" error) **[Accepted fact — Part A §E.4]**.
- **States (see §14):** loading (checks running as visible jobs); success
  (green readiness); warning (nice-to-have check failed but essential passed —
  gated on MBQ-06); blocked (essential check failed); `setup_incomplete`
  (partial exit).
- **Links to related screens:** S4 (store settings mirror the wizard's
  choices for later editing); S5 (dashboard connection-health card consumes
  readiness results); S12 (inventory first-push preview is where step 10's
  scheduled guard is later executed).
- **Accepted decision dependencies:** DEC-004 (custom-app/credential),
  DEC-003/006/007 (directions, source-of-truth, notification default,
  first-push guard), DEC-005 (Odoo.sh/on-prem, queue presence), DEC-012 flow
  1, Part A §E.
- **Open MBQ dependencies:** **MBQ-06** (which readiness checks are essential
  vs nice-to-have — governs step 6 pass/fail gating and the warning-vs-blocked
  split); **MBQ-05** (custom-app creation surface / token-acquisition
  mechanics — governs step 3 copy detail); **MBQ-04** (credential
  storage-at-rest — no bearing on the screen, flagged so the credential step
  is not designed to imply a storage mechanism); **MBQ-10** (turnkey install
  path — step 1 prerequisites copy); **MBQ-03** (exact wizard view/action
  IDs); **MBQ-22** (exact step copy).

---

## 3. Store settings screens (S4)

Converts DEC-012 flow 2 and Part A §B/§I (the seven config-object concepts
and the feature-flag mechanism). **[Screen blueprint proposal]** a single
store settings surface with domain-segmented tabs (setup-ux P3 progressive
disclosure; WK-style tabbed IA cited as good, EM/SH toggle-density cited as
the anti-pattern).

### S4 — Store settings surface

- **Purpose:** view and (for the Administrator) edit the persisted per-store
  configuration that governs sync behaviour, after setup — one place, not
  toggle-dense scattered screens.
- **Primary users:** Administrator edits; Operator/Reviewer/Auditor view
  read-only **[Accepted fact — Part A §J.2]**.
- **Entry points:** the Settings menu region (S1); "reconnect/re-run setup"
  and "edit source-of-truth" links from setup summary and dashboard.
- **Key information shown — grouped panels [Screen blueprint proposal] over
  accepted concepts:**
  1. **Store profile** — display name, shop domain, connection state
     (`setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`),
     setup-completion markers **[Accepted fact — Part A §B.1]**.
  2. **Credentials / API health** — credential presence + last-validated +
     rotation state (**never the value**); pinned Shopify API version;
     honest, named API health state + plain-language reason (e.g. "Shopify
     is rate-limiting requests") **[Accepted fact — Part A §B.2/§B.3;
     DEC-004]**.
  3. **Source-of-truth settings** — product first-sync strategy;
     price source-of-truth; recorded inventory source-of-truth; **editing
     after first sync carries an explicit warning** (a meaningful behaviour
     change, not a cosmetic toggle) **[Accepted fact — Part A §B.6;
     DEC-012 §5]**.
  4. **Feature flags / domain enablement** — which domains
     (product/sale-order/inventory/fulfillment) are enabled, plus per-domain
     capability flags (image sync, price sync, apply-mode-once-decided,
     etc.); **installing a module never silently enables its domain**;
     disabling stops new sync but **never deletes history**; re-enabling
     **re-enters that domain's own guard** **[Accepted fact — Part A
     §I.1/§I.2/§I.4]**.
  5. **Notification defaults** — the fulfillment customer-notification
     default, **off by default, never pre-checked on**, explicit opt-in
     **[Accepted fact — Part A §B.7; DEC-007 §5; RA-009]**.
  6. **Inventory settings** — recorded inventory source-of-truth and the
     quantity-meaning explanation (see S12); apply-mode surfaced per §11.
  7. **Fulfillment settings** — notification default (shared with panel 5)
     and location-reference status (see S13).
  8. **Gateway / journal mapping placeholder** — a per-store mapping from
     Shopify's gateway/payment-method label to an Odoo `account.journal`
     reference, **classification/routing input only — triggers no journal
     entry, posting, or reconciliation** **[Accepted fact — Part B §C.10;
     DEC-014 point G, partially resolving MBQ-30]**. Rendered as a
     **placeholder/config concept**, exact schema/fields open (**MBQ-30**).
- **Do not turn open technical questions into accepted implementation
  fields:** panels 6/7/8 present *concepts and the accepted posture*, not
  fixed field lists. Inventory apply-mode is shown per the DEC-015
  **recommendation** (review-then-apply) **without deciding MBQ-34**;
  notification granularity is global/per-store per the DEC-015
  **recommendation** **without deciding MBQ-41**; gateway→journal exact
  schema is **MBQ-30**; feature-flag exact implementation is **MBQ-07**.
- **Primary actions (Administrator):** edit each panel; enter/replace/rotate
  credential (logged reconnect/rotation, never edit-in-place of history);
  enable/disable a domain (with the accepted safe semantics); re-run setup
  wizard; run a test connection. **All other roles: read-only.**
- **Blocked / guard states:** editing source-of-truth after first sync shows
  a warning-confirm; disabling a domain with in-flight jobs shows the
  accepted job disposition (cancel-with-audit-reason or held), never silent
  drop; no settings toggle can bypass a safety guard (§I.5).
- **States (see §14):** success (saved, with audit trail entry); warning
  (post-first-sync source-of-truth change; domain disable consequences);
  `reconnect_needed`/`disconnected` banners with a route to setup.
- **Links to related screens:** S3 (setup), S5 (health card), S12 (inventory
  location mapping), S13 (fulfillment), S8 (gateway→journal feeds matching/
  evidence), S7 (a credential-invalid state links to the error center).
- **Accepted decision dependencies:** Part A §B (all seven concepts), §I
  (feature flags/enable-disable), DEC-004/006/007/010/011, DEC-014 §C.10,
  DEC-015 (inventory/fulfillment posture).
- **Open MBQ dependencies:** **MBQ-07** (feature-flag exact implementation),
  **MBQ-08** (store-disconnect data-retention posture — governs the
  disconnect panel/flow), **MBQ-30** (gateway→journal schema), **MBQ-34**
  (apply-mode), **MBQ-41** (notification granularity), **MBQ-52** (API
  version pinning/upgrade policy), **MBQ-54** (module uninstall/disable
  lifecycle), **MBQ-02** (exact setting field names), **MBQ-04** (credential
  storage-at-rest).

---

## 4. Dashboard / command center (S5)

Converts DEC-012 flow 3 and Part A §F. Answers the north-star three questions:
**"Is everything OK? What failed and why? What do I do next?"** **[Accepted
fact — setup-ux north star; Part A §F.1]**.

### S5 — Dashboard / command center

- **Purpose:** the operator's home; a single glanceable + actionable summary
  of health, freshness, exceptions, and next actions — exception-first, never
  vanity metrics.
- **Primary users:** all four roles view; **action affordances render only
  for roles holding the right — visibility of a problem is never restricted
  to those who can fix it** **[Accepted fact — Part A §F.5]**.
- **Entry points:** default landing in the connector app; every "home" link.
- **Key information shown — the nine accepted cards [Accepted fact — Part A
  §F.1], as Odoo dashboard tiles/kanban [Screen blueprint proposal]:**
  1. **Connection health** (state + API health).
  2. **Last successful sync per domain** with mechanism label
     (webhook/scheduled/manual) — **never one global timestamp hiding a
     stalled domain**; honest freshness.
  3. **Failed jobs by severity meaning** — needs manual review / system will
     auto-retry / permanently failed.
  4. **Manual-review count** (`blocked_manual_review`, with sub-reason
     breakdown).
  5. **Retry-waiting count** (`retry_waiting`) — "the system has this",
     distinct from "you must act".
  6. **First-push-pending count** (inventory guard not yet completed).
  7. **Inventory exceptions** (location-missing / ambiguous / quantity
     mismatch) — contributed by the inventory module.
  8. **Fulfillment exceptions** (unmatched picking / ambiguous
     FulfillmentOrder-line / notification-confirmation-missing) — contributed
     by the fulfillment module.
  9. **Duplicate/matching exceptions across domains.**
- **Health summary / sync status / error summary / queue-job status / last
  sync timestamps / actionable next steps:** these map to cards 1, 2, 3,
  5, 2, and the exception-first design respectively.
- **Data source [Accepted fact — Part A §F.2; RA-013]:** every metric is
  computed from the job/log/error abstraction (§D) — no separate metrics
  store, **no domain-owned parallel dashboard**.
- **Actionable next steps [Accepted fact — Part A §F.3]:** the dashboard
  leads with what needs attention; **every count is clickable** and routes to
  the filtered sync-center (S6) / error-center (S7) view for that category — a
  number with no path to act on it is not acceptable. **No vanity-only
  metrics** (Part A §F.4).
- **Empty and first-run states [Screen blueprint proposal on Part A §E.4/§F]:**
  - **First-run / `setup_incomplete`:** the dashboard shows a guided
    "finish setup" state naming exactly which steps remain, routing to S3 —
    not a blank grid, not a generic "not configured" error.
  - **First-push-pending:** a distinct first-run condition (card 6) routing
    to the inventory first-push preview (S12).
  - **Healthy-empty:** when connected with zero exceptions, the dashboard
    states "everything in sync" with last-sync freshness, not an empty void.
- **Blocked states:** `disconnected`/`reconnect_needed` renders a health
  banner routing to S3/S4; credential-invalid routes to the error center.
- **Primary actions:** click any count → filtered S6/S7; role-conditional
  quick actions that **enqueue** work (never run heavy sync inline)
  **[Accepted fact — setup-ux dashboard principles; Part A §D.1]**.
- **Links to related screens:** S6, S7, S8, S12, S3, S4.
- **Accepted decision dependencies:** Part A §F, DEC-012 flow 3, DEC-005
  (freshness/mechanism labels), DEC-009 (severity meaning), DEC-006/009
  (matching exceptions).
- **Open MBQ dependencies:** **MBQ-45** (admin-vs-functional dashboard split
  — one role-gated surface or two: carried forward, not decided);
  **MBQ-17/49** (reconciliation cadence affects freshness semantics, not the
  screen); **MBQ-03** (exact action IDs).

---

## 5. Sync center / job monitor (S6)

Converts DEC-012 flow 4 and Part A §G.

### S6 — Sync center (job list) + job detail

- **Purpose:** see, filter, and safely act on every job — the operator's
  operational worklist and the audit trail of what ran.
- **Primary users:** all roles view; Operators/Administrators trigger manual
  sync, retry-when-safe, verify, cancel/supersede; Reviewers run verify on
  review items; Auditors view only **[Accepted fact — Part A §J.2]**.
- **Entry points:** navigation (S1 Operations); every clickable dashboard
  count (S5); "open job" links from error center (S7) and preview screens.
- **Key information shown [Accepted fact — Part A §G.1/§G.2]:**
  - **Filters:** domain (product/order/inventory/fulfillment); trigger/source
    (the six §D.2 sources — `webhook`, `manual_sync`, `scheduled_sync`,
    `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`);
    state (the ten §D.3 states); error class (human-readable labels, §D.4).
  - **List columns:** domain · source · state · related record · age · retry
    count · error class (where failed/blocked) · operator-safe operation
    reference.
- **Manual sync actions [Accepted fact — Part A §G.3; setup-ux sync
  principles]:** trigger manual sync / reconcile-now (role-gated); manual sync
  is always available (also the Odoo.sh-staging test path).
- **Scheduled sync visibility [Accepted fact — Part A §G.1; setup-ux P4]:**
  scheduled/`reconciliation` sources are shown honestly; freshness/mechanism
  labels avoid "real-time" overstatement; **friendly scheduling language,
  never raw `ir.cron` internals** (setup-ux config principle; anti-pattern
  A-UX-2).
- **Job list / job detail [Screen blueprint proposal on Part A §G]:** the list
  is an Odoo list/kanban with the search-filter facets above; the **job
  detail** (Odoo form) shows the job's source, state (as a statusbar over the
  ten states), related store/Shopify object/Odoo record/binding, the
  operator-safe operation reference, and the state-conditional actions.
- **Retry / cancel / supersede concepts [Accepted fact — Part A §G.3/§G.4/
  §G.6/§D.9]:**
  - **Retry is never a single generic button.** Per job the UI distinguishes:
    auto-retry already in progress (`retry_waiting` — **no button**); safe to
    retry now; requires a fix first (no retry button until resolved); requires
    a verification read before retry (ambiguous-outcome).
  - **Verify current state** — a safe verification read against Shopify, run
    as a *visible job*, offered **before** any retry for ambiguous-outcome
    cases; its outcome either unlocks a safe retry or routes to
    `blocked_manual_review`.
  - **Cancel / supersede** — from `draft`/`queued`/`retry_waiting`; records
    who/why; supersede shows the successor operation. **Retry never bypasses a
    guard** (§I.5) and reuses the same code path as auto-retry.
- **Source classification visibility [Accepted fact — Part A §D.2] + open
  residual:** the six accepted job sources are first-class filter/column
  values. **The screen must NOT invent a seventh source label** for
  Odoo-side event-triggered jobs (an inventory push from a stock change; a
  fulfillment creation from a validated `stock.picking`) — that classification
  is **[Open question — MBQ-62]**, undecided. Until MBQ-62 is decided, such
  jobs are displayed under whichever accepted source their eventual mapping
  assigns; the screen surfaces the *accepted* source, never a fabricated one.
- **Blocked states:** jobs in `blocked_manual_review` link to the error
  center (S7); jobs blocked by a guard show the guard reason, not a bare
  retry.
- **States (see §14):** every one of the ten job states is representable;
  `retry_waiting` vs `blocked_manual_review` vs `failed_retryable` vs
  `failed_final` are visually distinct (system-owned vs operator-owned vs
  fixable vs terminal).
- **Links to related screens:** S7 (blocked/failed detail & manual review);
  S8 (open mapping/matching); S9–S13 (open source record); S5 (counts).
- **Accepted decision dependencies:** Part A §G/§D (sources/states/classes/
  retry/idempotency/serialization), DEC-005/009/011, DEC-012 flow 4.
- **Open MBQ dependencies:** **MBQ-62** (Odoo-event job-source
  classification), **MBQ-16** (retry ceilings/backoff — affects the "auto
  retry in progress" copy, not the screen), **MBQ-20/21** (operation-key
  schema / serialization mechanism — the operator-safe reference derives from
  MBQ-20's key, exposed only as a stable label), **MBQ-03** (exact view IDs).

---

## 6. Error center / recovery (S7)

Converts DEC-012 flow 5 and Part A §H — the recovery-first surface and the
manual-review queue. **[Accepted fact — product-vision differentiation theme
2; setup-ux P6]** this is a named differentiation pillar.

### S7 — Error center / recovery (+ manual-review queue)

- **Purpose:** turn every failure into a recovery, never a dead end — a
  reason, a suggested fix, an owner, and a safe next action; and host the
  Reviewer's manual-review approvals.
- **Primary users:** all roles view; Operators/Administrators retry-when-safe
  and verify; **Reviewers approve/resolve `blocked_manual_review`** (the
  auditable act DEC-009 requires); Auditors view only **[Accepted fact —
  Part A §J.2]**.
- **Entry points:** navigation (S1 Recovery); dashboard exception counts
  (S5 cards 3/4/7/8/9); "needs review/needs fix" links from sync center (S6)
  and from preview/matching screens.
- **Key information shown — the nine accepted required elements [Accepted
  fact — Part A §H, items 1–9]:**
  1. **Human-readable reason** as the primary display — plain language,
     **never an error code or stack trace as primary UX**.
  2. **Technical detail expandable** — raw error/response, class code, job/
     operation identifiers behind an explicit expand (secondary, never
     primary).
  3. **Suggested fix** — a concrete next step on every blocked/failed entry.
  4. **Owner/action state** — waiting on system (auto-retry) / waiting on
     operator (fix/confirm) / resolved.
  5. **Related Odoo record** — direct link.
  6. **Related Shopify record** — reference/link, shown even when the
     operation failed before a Shopify object was confirmed.
  7. **Retry-policy explanation** — a one-line *why* this entry is
     auto-retried / manual-only / needs verification.
  8. **Manual-review sub-reasons** — the *specific* sub-reason, never a
     generic "needs review": ambiguous match / binding conflict / duplicate
     risk / destructive-write guard blocked / inventory location missing /
     fulfillment notification confirmation missing.
  9. **Audit trail** — attempted / actually written / skipped-by-which-rule /
     confirmed-by-whom, with before/after values for destructive operations.
- **Error grouping by accepted Part A error classes [Accepted fact — Part A
  §H, §D.4]:** grouping/filtering by the fixed 16-class registry and by the
  manual-review sub-reason (item 8) is supported. The screen never introduces
  a 17th class or a new sub-reason vocabulary.
- **Manual-review queues [Accepted fact — Part A §D.8/§H/§J.2]:** the error
  center is the queue where Reviewer approvals happen; each
  `blocked_manual_review` item carries its specific sub-reason, related
  records, and a **named resolution action**; approving records who/when and
  **releases the job through the normal queue path, never a side channel**.
- **Retry eligibility [Accepted fact — Part A §G.4/§H, item 7]:** the same
  state/class-conditional retry rules as S6 apply; classes requiring a fix,
  confirmation, or verification never show a bare retry action.
- **Confirmation-required flows [Accepted fact — Part A §D.5.4]:** the six
  confirmation-required sub-classes are resolved through explicit confirm
  dialogs (§14 confirmation-dialog pattern) — including first-push
  confirmation (S12), notification confirmation (S13), destructive-write
  confirmation (S9), duplicate-risk/ambiguous-match/binding-conflict
  confirmation (S8).
- **No raw stack trace as primary UX [Accepted fact — Part A §H item 1/§D.11/
  §D.12; setup-ux P8]:** the human-readable reason is primary; the technical
  detail is behind an explicit expand.
- **Order-import touchpoints handled here, no dedicated screen [Accepted fact
  — Part B §C.14; DEC-014, MBQ-26]:** `financial total mismatch` entries
  render with the **inline evidence breakdown** (Shopify total vs computed
  Odoo total, per-component: lines / tax / shipping / discount), and
  `mapping missing` order entries **link directly to the matching flow (S8)** —
  a two-click resolve path. This is an extension of the *existing* error
  center, not a new surface.
- **States (see §14):** blocked/manual-review; failed-retryable; failed
  terminal; resolved; the financial-mismatch and location-mismatch warnings.
- **Links to related screens:** S6 (the job), S8 (matching/mapping), S9–S13
  (the domain record + confirmation), S5 (counts).
- **Accepted decision dependencies:** Part A §H/§D, DEC-009/012, DEC-014
  §C.14 (order touchpoints), DEC-015 (inventory/fulfillment sub-reasons now
  instantiated).
- **Open MBQ dependencies:** **MBQ-13** (exact stale/recreated-binding review
  fields/actions), **MBQ-22** (exact reason/fix copy), **MBQ-56** (total-check
  tolerance — affects the mismatch explanation), **MBQ-03** (exact view IDs).

---

## 7. Matching and duplicate-prevention screens (S8)

Converts DEC-012 flow 6 and Part A §C.5/§H + Part B §A.6/§A.9/§B.3/§B.9/§C.5/
§C.6. **[Screen blueprint proposal]** a **matching center** surface (distinct
from, but tightly linked to, the error center) for interactive/batch
create-or-bind resolution.

### S8 — Matching / duplicate-prevention center

- **Purpose:** let the operator resolve product, customer, and order-embedded
  matches safely — never a blind create, never a name-only auto-match, always
  a blocking preview before any create/bind.
- **Primary users:** Operators run interactive/batch matching sessions;
  **Reviewers resolve ambiguous/duplicate-risk items** (the manual-review
  overlap with S7); Administrators can do both; Auditors view.
- **Entry points:** navigation (S1 Matching); first-sync review; a manual
  matching session launched from a product/customer/order record; error-center
  (S7) `mapping missing`/`ambiguous match`/`duplicate risk` links; dashboard
  matching-exceptions count (S5 card 9).
- **Key information shown:**
  - **Match-key priority (structural, not configurable) [Accepted fact —
    Part A §C.5; DEC-006; RA-006]:** existing binding → SKU/internal reference
    → barcode → (customers) email → manual. **Name is advisory only, never an
    automatic key.** A name/email-adjacent similarity may be shown as an
    **advisory hint** during manual match, never used to auto-bind.
  - **Duplicate-prevention preview [Accepted fact — Part A §C.5; Part B §A.9/
    §B.9]:** an interactive/batch action **always shows a blocking preview —
    "will create N, link M, N ambiguous" — before the operator confirms.**
  - Per-candidate detail: the candidate Odoo record(s), the match key that
    fired, why a match is ambiguous (the multiple candidates), and the
    binding audit provenance.
- **Product matching [Accepted fact — Part B §A.6]:** SKU/barcode priority;
  ambiguous → manual review; duplicate-risk create → blocked pending
  confirmation.
- **Customer matching [Accepted fact — Part B §B.3/§B.13, DEC-014 MBQ-31]:**
  **email is the sole automatic match key** (beyond an existing binding);
  phone/name advisory/manual-only. The screen must not offer name/phone as an
  automatic key.
- **Order / customer resolution [Accepted fact — Part B §C.5/§C.6]:** an
  unmatched **product** on an order line holds the **whole order**
  (`mapping missing` → `failed_retryable`) with a direct link here to bind the
  product; an **ambiguous customer** holds **only the customer assignment**
  (`ambiguous match` → `blocked_manual_review`) while lines/evidence still
  capture. The screen makes this distinction explicit (product-hold vs
  customer-assignment-hold).
- **Duplicate prevention [Accepted fact — DEC-003/006]:** no blind create; the
  preview is mandatory; the four confirmation-required create/bind classes
  (ambiguous match, binding conflict, duplicate risk, destructive-write guard)
  route through confirm dialogs.
- **Manual binding review [Accepted fact — Part A §C.6/§C.4]:** a binding
  whose Shopify counterpart is deleted/recreated shows as a **review item**
  (binding conflict / duplicate risk) — never silently dropped or hijacked;
  the operator sees the binding provenance (matched-by, matched-at, source
  strategy, match key, status) and a named re-bind/override action recorded
  with who/when.
- **Create/bind policy visibility [Accepted fact — Part B §A.2/§B.2/§C.6,
  DEC-014 MBQ-59]:** the screen makes the **two distinct paths** legible:
  - **Interactive/batch** path → the mandatory **blocking, synchronous
    preview** before the operator confirms any create/bind.
  - **Automated** (webhook/scheduled/reconciliation) path → the **pre-create
    gate** is the "no blind create" mechanism; the sync-center/dashboard's
    later display is **audit visibility only, never a preview substitute**.
  The screen never presents retrospective audit visibility *as if* it were the
  automated path's preview.
- **Blocked / confirmation states:** ambiguous-match, duplicate-risk, and
  binding-conflict confirm dialogs; a create blocked pending confirmation.
- **States (see §14):** the five product preview states (to-create /
  to-update / to-skip / blocked / draft-pending-publish) where applicable;
  empty (no candidates); the ambiguous/blocked states.
- **Links to related screens:** S9 (product), S10 (customer), S11/S7 (order
  evidence), S6 (the job), S7 (manual-review overlap).
- **Accepted decision dependencies:** DEC-003/006, Part A §C, Part B §A/§B/§C,
  DEC-014 (MBQ-26/31/59).
- **Open MBQ dependencies:** **MBQ-13** (exact stale/recreated review
  fields/actions), **MBQ-31** (accepted — email-only; noted for completeness),
  **MBQ-55** (exact binding model/field names), **MBQ-59** (exact
  eligibility/match-confidence implementation detail — the *policy* is
  accepted, exact detail open), **MBQ-22** (copy).

---

## 8. Product screens (S9)

Converts DEC-012 flow 7 (product) and Part B §A.

### S9 — Product import preview / export preview / update diff

- **Purpose:** let the operator import, export, and update products/variants
  with a preview before any write and a hard guard before any destructive
  (delete-on-omit) write — the "safe by default" pillar.
- **Primary users:** Operators/Administrators run and confirm; Reviewers
  resolve destructive-write/duplicate confirmations; Auditors view.
- **Entry points:** navigation (S1 Operations, product); a product record's
  "export/update to Shopify" action; import from a sync/matching session; S6
  job detail; S7/S8 links.
- **Key information shown & flows:**
  - **Import preview [Accepted fact — Part B §A.2/§A.9]:** matching runs
    binding-first → SKU → barcode; a blocking "will create N, link M, N
    ambiguous" preview precedes any create/bind (interactive/batch); what
    travels: identity, options/variant structure, SKU/barcode, basic media,
    base/compare-at price.
  - **Export preview / diff [Accepted fact — Part B §A.3/§A.11]:** the export
    sequence is **duplicate-prevention preview → destructive-write preview/
    diff → draft-first write → binding created/confirmed after success.**
  - **Update preview / diff [Accepted fact — Part B §A.4]:** a bound product
    becomes eligible for an update job only after an **explicit operator
    action** (an ordinary Odoo write never auto-queues a Shopify update); the
    job **renders a diff — fields / images / price / variants — before
    writing**, keyed off the binding.
  - **Variant / media / price handling visibility [Accepted fact — Part B
    §A.5/§A.13/§A.14]:** the diff renders **which variants a `productSet`
    write would DELETE by omission** (the load-bearing delete-on-omit risk),
    which images would be replaced/removed, and price/compare-at changes;
    price source-of-truth must be explicit per product — **export/update
    BLOCKS rather than assumes a default when price source-of-truth is unset**.
  - **Draft-first / publish control [Accepted fact — Part B §A.10/§A.15]:** a
    first-time export creates the product with `Product.status: DRAFT` (or
    relies on `productCreate`'s unpublished-by-default behaviour) and does
    **not** call `publishablePublish` — the product exists in Shopify admin but
    is **not live** until the operator explicitly confirms channel(s); an
    update to a live product never implicitly changes its publish state.
- **The five preview/review states [Accepted requirement + Screen blueprint
  proposal — Part B §A.16]:** that every export/update run shows counts to
  create / update-with-diff / skip-with-reason *before* writing is the
  accepted requirement; the explicit **five-state enumeration** below is the
  blueprint proposal within it: **to-create / to-update (with diff) / to-skip
  (reason shown, never guessed) / blocked (destructive-write guard would
  delete/omit data, or price source-of-truth unset) / draft-pending-publish.**
- **Guard states and confirmation flows [Accepted fact — Part B §A.11;
  Part A §I.5]:** the destructive-write preview is **mandatory before any
  destructive/full-state write** and **no flag may bypass it**; confirmation
  is an explicit dialog (§14) recording who/when with before/after audit.
- **Blocked states:** destructive-write guard blocked; price source-of-truth
  unset; ambiguous/duplicate on import.
- **Links to related screens:** S8 (matching), S6 (job), S7 (guard-blocked
  entries), S4 (price/source-of-truth settings).
- **Accepted decision dependencies:** DEC-003/004/006/007, Part B §A, Part A
  §I.5.
- **Open MBQ dependencies:** **MBQ-23** (exact variant-mutation choice —
  direction accepted), **MBQ-24** (media delete-on-omit — preview covers the
  risk regardless), **MBQ-25** (exact channel-selection UX), **MBQ-55** (exact
  product/variant binding names), **MBQ-22** (copy).

---

## 9. Customer screens (S10)

Converts DEC-012 flow 7 (customer) and Part B §B.

### S10 — Customer import / matching

- **Purpose:** import and match Shopify customers to Odoo `res.partner`
  safely — email-only automatic matching, a clearly-flagged no-PII fallback,
  and manual review for ambiguity, never inventing PII.
- **Primary users:** Operators run import/matching; Reviewers resolve
  ambiguous/duplicate matches (`customer_match_review`); Administrators both;
  Auditors view.
- **Entry points:** navigation; as part of order import (most common);
  standalone customer sync/reconciliation; S8 matching center; S6/S7 links.
- **Key information shown & flows:**
  - **Customer import / matching [Accepted fact — Part B §B.2/§B.3]:**
    Shopify → Odoo only in Phase 1 (never pushes partner data back);
    matching = existing binding → email → manual review.
  - **Email-only match-key posture [Accepted fact — Part B §B.13; DEC-014
    §B.13, MBQ-31]:** **email is the sole automatic match key** beyond an
    existing binding; phone/name advisory/manual-only. The screen offers no
    automatic name/phone match.
  - **Default-customer fallback visibility [Accepted fact — Part B §B.6/§B.7,
    DEC-014 partially resolving MBQ-29]:** when Shopify genuinely withholds all
    PII (no-PII plan/scope), a single, clearly-flagged fallback partner per
    store is used — **only** for genuine no-PII orders, **never** for ordinary
    matching failure — and every such order carries a **visible, auditable
    marker "no customer data available — fallback used"**, never
    indistinguishable from a real matched customer. **Do not invent PII.**
  - **Manual review [Accepted fact — Part B §B.9/§B.11]:** an interactive/
    batch matching session always shows the blocking "will create N, link M,
    N ambiguous" preview; ambiguous email/customer-key candidates route to
    manual review; a duplicate-risk create is blocked pending confirmation.
- **Blocked / states (see §14):** ambiguous match; duplicate risk; binding
  conflict (stale/recreated Shopify customer ID); data-shape mismatch (missing
  email on a non-no-PII store = a data-quality signal, **not** a no-PII case).
  The fallback-used marker is a distinct, always-visible state.
- **Links to related screens:** S8 (matching), S11/S7 (order-embedded customer
  resolution + evidence), S6 (job), S4 (protected-data readiness).
- **Accepted decision dependencies:** DEC-003/006, Part B §B, DEC-014 (MBQ-31,
  MBQ-29 direction).
- **Open MBQ dependencies:** **MBQ-29** (one shared fallback partner vs
  per-order anonymous identity — direction accepted, granularity open),
  **MBQ-09** (protected-data obligations — affects what customer data is
  available to show), **MBQ-55** (exact customer binding names), **MBQ-02**
  (exact partner field mapping), **MBQ-22** (copy).

---

## 10. Order screens (S11)

Converts DEC-012 flow 7 (order) and Part B §C. **No dedicated order-import
screen** is authorized **[Accepted fact — Part B §C.14; DEC-014, MBQ-26]** —
order operator touchpoints live in the sync center (S6, filterable by domain)
and the error center (S7), extended with two order-specific additions.

### S11 — Order import queue + order detail (via S6/S7)

- **Purpose:** import Shopify orders idempotently to Odoo `sale.order`,
  capture financial evidence, resolve product/customer references, and guard
  totals — surfaced through the existing sync/error surfaces, not a new
  screen.
- **Primary users:** Operators monitor/act; Reviewers resolve ambiguous
  customer / duplicate-order / evidence-mismatch items; Administrators both;
  Auditors view.
- **Entry points:** the sync center filtered to the order domain (queue);
  the error center for held/mismatched orders; a `sale.order` record's linked
  job/binding; dashboard order-exception counts.
- **Key information shown & flows:**
  - **Order import queue / detail [Accepted fact — Part B §C.2/§C.14]:** the
    sync center (S6) filtered to `order` is the queue; the order detail is the
    Odoo `sale.order` form plus its linked job/binding; there is **no separate
    order-import surface**.
  - **Financial-evidence breakdown [Accepted fact — Part B §C.7/§C.9/§C.14]:**
    taxes (`taxLines`/`totalTaxSet`), shipping (`shippingLines`), discounts
    (`discountApplications`), and payment evidence (financial/payment status,
    gateway/method label, `OrderTransaction` reference) are preserved as
    **evidence only** and rendered as a per-component breakdown — inline in the
    error-center detail for a `financial total mismatch`.
  - **Total-check guard [Accepted fact — Part B §C.8; DEC-007 §6]:** before an
    order job completes, the connector reconciles summed line/tax/shipping/
    discount evidence against Shopify's reported total; a mismatch is
    `financial total mismatch` — **conservative, never silent, never
    auto-retried**, held in `failed_retryable` for explicit human review. This
    guard is **mandatory and permanent — no flag weakens it**.
  - **Product / customer resolution [Accepted fact — Part B §C.5/§C.6]:**
    unmatched product → **whole-order-hold** (`mapping missing`) with a link
    to matching (S8); ambiguous customer → **customer-assignment-hold only**
    (`ambiguous match`) while lines/evidence still capture; genuine no-PII →
    flagged fallback partner.
  - **Gateway / journal mapping visibility [Accepted fact — Part B §C.10,
    DEC-014 MBQ-30]:** the imported order's evidence record shows the
    suggested `account.journal` classification from the per-store gateway→
    journal mapping — **classification/routing input only, no posting**.
  - **Evidence-refresh-only order-edit posture [Accepted fact — Part B §C.12,
    DEC-014 point J]:** an `ORDERS_UPDATED` webhook (or reconciliation) may
    **refresh Shopify-side evidence/audit only** — it must **NOT** silently
    update the Odoo order's lines, prices, taxes, shipping, discounts,
    invoices, payments, refunds, or fulfillment state; divergence routes
    through the total-check guard / human review. The order detail surfaces
    this as "evidence refreshed" vs "Odoo order unchanged", never a silent
    rewrite.
- **Blocked / states (see §14):** financial-mismatch warning (with the inline
  evidence breakdown); whole-order-hold; customer-assignment-hold; duplicate
  order risk.
- **Links to related screens:** S6 (queue/job), S7 (mismatch/hold detail), S8
  (product/customer resolution), S10 (customer), S4 (gateway→journal mapping).
- **Accepted decision dependencies:** DEC-003/005/006/007, Part B §C, DEC-014
  (MBQ-26/30, evidence-refresh-only, total-check).
- **Open MBQ dependencies:** **MBQ-27** (Odoo tax-representation mechanism —
  evidence is shown, the mechanism is open), **MBQ-28** (draft-artifact guard —
  not triggered), **MBQ-30** (gateway→journal schema), **MBQ-56** (total-check
  tolerance), **MBQ-57** (whole-order-hold alternative — future),
  **MBQ-58** (order-identity nuances), **MBQ-22** (copy).

---

## 11. Inventory screens (S12)

Converts DEC-012 flow 8 and Part C §A (accepted via DEC-015).

### S12 — Location mapping / first-push preview / inventory sync status

- **Purpose:** map Odoo↔Shopify locations, run the guarded first inventory
  push with an explicit confirmation, and show ongoing inventory sync/
  reconciliation status and exceptions — without over/under-selling live
  stock.
- **Primary users:** Administrators configure location mapping and confirm the
  first push (or Reviewers per role); Operators monitor and act on exceptions;
  Auditors view.
- **Entry points:** navigation (S1 Matching → location mapping; Operations →
  inventory); the setup wizard's scheduled first-push step (S3 step 10);
  dashboard inventory-exception + first-push-pending counts (S5 cards 6/7);
  S6/S7 links.
- **Key information shown & flows:**
  - **Location mapping [Accepted fact — Part C §A.2; DEC-010; §K rule 6]:** an
    explicit, non-inferred Odoo-location ↔ Shopify-Location mapping, **owned
    solely by the inventory module** (fulfillment never reads this table). The
    screen shows each mapping pair and its status; **the mapping is never
    inferred silently.**
  - **First-push preview and confirmation [Accepted fact — Part C §A.5;
    DEC-007 §4; DEC-010; RA-008]:** the first inventory push is **guarded** —
    it shows a preview snapshot and requires an explicit confirmation recorded
    with the confirming operator + timestamp, the recorded source-of-truth,
    and the scope; the guard **cannot be silently skipped or auto-completed**.
  - **Quantity-source explanation [Accepted fact — Part C §A.4; DEC-010,
    partially resolving MBQ-32]:** the screen must explain *which* Odoo
    quantity is being pushed to Shopify `available` (the DEC-010 "Free to Use"
    semantic; two verified but **non-equivalent** candidate sources exist —
    `product.product.free_qty` and per-location `stock.quant.available_quantity`
    — which diverge when expired unreserved stock exists). **The screen
    surfaces the recorded source-of-truth honestly (setup-ux P3 inline help:
    "Forecast vs Free-to-Use"); it does not decide the source (MBQ-32).**
  - **Apply-mode recommendation visibility [Recommendation — Part C §A.7;
    DEC-015, NOT deciding MBQ-34]:** the ongoing (post-first-push) apply-mode
    screen affordance is designed to support **review-then-apply** (the DEC-015
    Phase-1 **recommendation**, consistent with DEC-003's "auto-apply not
    accepted as default"). **This blueprint does not decide MBQ-34** — the
    screen accommodates the recommended posture and flags apply-mode as an
    open setting.
  - **Inventory sync / reconciliation status [Accepted fact — Part C §A.8/
    §A.9; DEC-005]:** per-location sync freshness, drift/exception status, and
    reconciliation results; layered sync (webhook candidate + scheduled +
    manual + reconciliation), **never webhook-only**.
- **First-push granularity [Recommendation — Part C §A.5; DEC-015, NOT
  deciding MBQ-33]:** the guard/confirmation record is designed to attach per
  **mapped Odoo-location ↔ Shopify-Location pair** (the DEC-015
  **recommendation**, no coarser than per-store per DEC-007). **MBQ-33 remains
  open** — the screen implements the recommended granularity as a proposal,
  not a decision.
- **MBQ-32 residual visibility [Open question — MBQ-32]:** the screen shows the
  recorded source but must not present a final source-selection/aggregation
  mechanism as decided.
- **`on_hand` exposure [Open question — MBQ-35]:** the default target is
  Shopify `available`; **`on_hand` is not offered as a Phase-1 UI choice**
  without explicit justification, and `committed` is never written. The screen
  does not expose `on_hand` as a selectable target.
- **Blocked / states (see §14):** first-push-pending; location-missing
  (`inventory location missing`, a confirmation-required class); ambiguous;
  quantity-mismatch warning; guard-blocked.
- **Links to related screens:** S3 (scheduled first push), S4 (inventory
  source-of-truth/apply-mode settings), S6 (job), S7 (location-missing/
  mismatch review), S5 (counts).
- **Accepted decision dependencies:** DEC-007/010, Part C §A, DEC-015 (facts),
  Part A §I.5 (guard cannot be bypassed).
- **Open MBQ dependencies:** **MBQ-32** (quantity source — partially
  resolved), **MBQ-33** (first-push granularity — open), **MBQ-34**
  (apply-mode — open), **MBQ-35** (`on_hand` exposure — open), **MBQ-36**
  (mutation choice — direction accepted), **MBQ-38** (confirmation-record
  schema — concept accepted), **MBQ-63** (inventory-webhook payload/
  subscription/Phase-1-scope — open, governs webhook-driven import
  specifically), **MBQ-43** (Location cache policy), **MBQ-55** (inventory
  binding names), **MBQ-22** (copy).

---

## 12. Fulfillment screens (S13)

Converts DEC-012 flow 9 and Part C §B (accepted via DEC-015).

### S13 — Fulfillment queue / detail (tracking, location review, notification)

- **Purpose:** turn validated Odoo deliveries into Shopify fulfillments,
  write tracking back, honor the notification default, and route location/
  matching ambiguity to review — using FulfillmentOrder-based mutations only.
- **Primary users:** Operators monitor/act; Reviewers resolve location-
  mismatch and notification-confirmation items; Administrators both; Auditors
  view.
- **Entry points:** navigation (Operations → fulfillment); a validated
  `stock.picking`'s linked job; dashboard fulfillment-exception count (S5 card
  8); S6/S7 links.
- **Key information shown & flows:**
  - **Fulfillment queue / detail [Accepted fact — Part C §B.2/§B.3/§B.12;
    DEC-011]:** the trigger is a **validated `stock.picking`**; mutations are
    **FulfillmentOrder-based only** (legacy order-based fulfillment never
    used). The queue is the sync center filtered to `fulfillment`; the detail
    links the Odoo picking, the matched FulfillmentOrder, and the job.
  - **FulfillmentOrder matching [Accepted fact — Part C §B.4]:** order/
    FulfillmentOrder/line/quantity matched via `lineItemsByFulfillmentOrder`;
    the detail shows the matched lines/quantities.
  - **Tracking fields and tracking write-back [Accepted fact — Part C §B.5;
    DEC-015, resolving MBQ-39]:** tracking is sourced from Odoo
    `stock.picking.carrier_tracking_ref` (Char), `carrier_tracking_url`
    (computed), and `carrier_id` (Many2one to `delivery.carrier`); the screen
    shows these and the write-back status. **Whether the `stock_delivery`/
    `delivery` module is a required dependency is [Open question — MBQ-60]** —
    the screen must show a clear state if those fields are absent (no field to
    write to), not fail opaquely.
  - **Notification default visibility [Accepted fact — Part C §B.6; DEC-007
    §5/DEC-011]:** the customer-notification decision is **off by default,
    never pre-checked**, persisted per job at enqueue time (retries never
    re-read a changed default); every fulfillment entry records whether
    notification was requested/suppressed. A missing/unconfirmed decision is
    the `fulfillment notification confirmation missing` confirmation-required
    class.
  - **Location mismatch / manual review [Accepted fact — Part C §B.8; DEC-015
    point J, partially resolving MBQ-42/43]:** a live FulfillmentOrder
    `assignedLocation` read is **authoritative** for a specific operation; the
    core Shopify Location reference is used only for naming/display and
    mismatch detection (a live read always wins over the cache). A mismatch
    routes to the **`ambiguous match`** class (its applicability **widened**,
    at blueprint level only, to this deterministic scenario) → manual review.
    The screen shows the assigned-vs-expected location and the review action.
  - **Backorder linkage visibility [Accepted fact — Part C §B.7; DEC-015,
    partially resolving MBQ-40]:** sequential partial fulfillments are linked
    via Odoo `stock.picking.backorder_id`/`backorder_ids`; the detail shows
    each backorder picking as its own fulfillment event.
- **MBQ-60/61/62 residual visibility (not resolution) [Open questions]:**
  - **MBQ-60** — `stock_delivery`/`delivery` dependency: shown as a state, not
    assumed.
  - **MBQ-61** — Shopify FulfillmentOrder **lifecycle events** (holds,
    cancellation-request, merges, splits, moves, reschedules): the screen does
    **not** design a dedicated hold-aware UX; a rejected/delayed
    `fulfillmentCreate` is caught by the existing ambiguous-outcome/manual-
    review handling. **MBQ-61 remains open**, not resolved here.
  - **MBQ-62** — Odoo-event-triggered job-source classification: the screen
    shows only accepted job sources (§D.2); it invents no source label.
- **Blocked / states (see §14):** notification-confirmation-missing;
  location-mismatch warning; unmatched picking; ambiguous FulfillmentOrder/
  line; tracking-field-absent (MBQ-60) state.
- **Links to related screens:** S6 (job/queue), S7 (location/notification
  review), S4 (notification default), S5 (counts).
- **Accepted decision dependencies:** DEC-007/011, Part C §B, DEC-015 (facts +
  MBQ-42 widening), Part A §I.5, §K rule 5 (fulfillment never depends on
  inventory).
- **Open MBQ dependencies:** **MBQ-41** (notification granularity — global/
  per-store recommended, per-order override open), **MBQ-42/43** (location-
  confirmation mechanism / cache policy — partially resolved), **MBQ-60**
  (module dependency), **MBQ-61** (lifecycle events), **MBQ-62** (job-source
  classification), **MBQ-55** (fulfillment binding names), **MBQ-22** (copy).

---

## 13. Permissions and roles UX (S14)

Converts DEC-012 flow 10 and Part A §J (the conceptual four-role model).
**No exact Odoo security CSV, `ir.model.access` rows, record rules, or group
XML IDs are designed here** — those are **MBQ-44**, open. This section
specifies *what each role sees/does conceptually across the screens above*.

### S14 — Role-conditional visibility and affordances (embedded, not a standalone screen)

- **Purpose:** ensure every screen renders role-appropriate visibility and
  actions — everyone can *see* problems; only those with the right can *act*.
- **Primary users:** all four roles.
- **The four roles [Accepted fact — Part A §J.1; DEC-012 §10; DEC-013
  hierarchy]:**
  - **Connector Administrator** — configures everything; implies Operator +
    Reviewer rights.
  - **Connector Operator** — runs day-to-day sync/retry/verify/cancel; cannot
    configure.
  - **Connector Reviewer / Manual-Review Owner** — approves/resolves
    `blocked_manual_review` items; sibling of Operator (neither implies the
    other).
  - **Read-only Auditor** — views everything; implied by all (everyone who can
    act can also view).
- **What each role can see/do conceptually [Recommendation — Part A §J.2
  capability matrix, grounded in accepted DEC-012 §10 and DEC-009's who-acted
  requirement; the role hierarchy and the no-read-back credential rule are
  [Accepted fact — DEC-013]]:**
  - View dashboard / jobs / errors / bindings / audit trails — **all roles**.
  - View store settings & connection status — all roles (non-admins
    read-only).
  - Configure settings/domains/source-of-truth/notification; enter/replace/
    rotate credential; run setup wizard — **Administrator only**.
  - **See credential secret value — no role, ever** (masked status only, a
    connector-surface guarantee, DEC-013).
  - Trigger manual sync / reconcile-now; retry safe jobs; cancel/supersede —
    **Administrator + Operator**.
  - Run verify-current-state — Administrator + Operator + Reviewer (on review
    items).
  - Approve/resolve `blocked_manual_review` — **Administrator + Reviewer**.
  - Audit (who did what, before/after) — **all roles**.
- **Screen consequence [Screen blueprint proposal — consistent with Part A
  §F.5]:** on every screen, **action affordances render only for roles
  holding the corresponding right; visibility of a problem is never restricted
  to those who can fix it.** An Operator seeing a Reviewer-only manual-review
  item sees the item and its status but not the approve action; an Auditor
  sees everything read-only.
- **Odoo-native basis [Accepted fact — setup-ux P10; Part A §J.2]:**
  `ir.model.access` is deny-by-default and record rules provide per-store
  isolation (never `sudo()`); connector settings are gated to authorized
  users; "two audiences, one product" (admin surface + functional-user
  surface) gated by access rights.
- **Blocked states:** an unauthorized action is **not shown** (not shown-then-
  errored); an unauthorized navigation target is absent from that role's menu.
- **Links to related screens:** all (S14 is cross-cutting).
- **Accepted decision dependencies:** DEC-012 §10, Part A §J, DEC-013
  (hierarchy; MBQ-47 resolved).
- **Open MBQ dependencies:** **MBQ-44** (exact security groups / access CSVs /
  record rules), **MBQ-45** (roles→groups mapping + admin-vs-functional-user
  surface split — **carried forward, not decided here**), **MBQ-46**
  (multi-company/multi-store isolation — later).

---

## 14. States and microcopy patterns (cross-cutting)

**[Screen blueprint proposal]** a single shared state + microcopy vocabulary,
so every screen above draws from one catalog rather than inventing per-screen
states. Grounded in Part A §D (states/classes/log shape), setup-ux P4/P6/P7/P8,
and product-vision "honest by default". **Exact copy strings are MBQ-22,
open** — this catalog defines *patterns and intent*, not final wording.

| State | When it appears | Pattern & microcopy intent | Accepted basis |
| --- | --- | --- | --- |
| **Empty** | No records/candidates yet; healthy-empty; first-run | Guide the next action ("connect a store", "run first import", "everything in sync"), never a blank void | setup-ux dashboard principles; Part A §E.4/§F |
| **Loading / progress** | Jobs/checks running | Show it as a **visible job** with source/state; honest progress, no spinner-with-no-context | Part A §E.3/§G.5; setup-ux confidence loop |
| **Success** | Job succeeded; settings saved | Confirm *what was actually written* (never assumed), with an audit entry; completion signal | Part A §D.10; setup-ux P8 |
| **Warning** | Reversible-but-notable condition (post-first-sync source-of-truth change; nice-to-have readiness check failed; domain-disable consequences) | State the consequence + the safe path; not an error | Part A §B.6; DEC-012 §5 |
| **Blocked / manual review** | The six confirmation-required classes | Show the **specific sub-reason** (never generic "needs review"), the named resolution action, related records | Part A §D.8/§H item 8 |
| **Failed — retryable** | "Manual fix then retry" classes; total-mismatch hold | Reason + suggested fix + a retry that appears **only after** the fix; never a bare retry | Part A §D.5.3/§G.4 |
| **Failed — terminal** | `failed_final` (exhausted/manual) | Reason + audit of attempts; no misleading retry affordance | Part A §D.3/§D.5 |
| **Confirmation dialog** | Any destructive/first-push/notification/duplicate/ambiguous confirm | Explicit dialog; states consequences; records who/when; cannot bypass the guard | Part A §I.5; Part B §A.11; Part C §A.5 |
| **Destructive-write warning** | `productSet`/bulk-variant delete-on-omit; media/price destructive change | Show exactly **what would be deleted/omitted** before confirm | Part B §A.11; setup-ux P7 |
| **Notification warning** | Fulfillment notification decision pending/being enabled | "Customer will be emailed" is explicit, opt-in, never pre-checked | Part C §B.6; DEC-007 §5; RA-009 |
| **Financial mismatch warning** | `financial total mismatch` | Inline per-component breakdown (Shopify total vs computed Odoo total: lines/tax/shipping/discount); **conservative, never silent, never auto-retried** | Part B §C.8/§C.14; DEC-007 §6 |
| **Location mismatch warning** | Fulfillment `assignedLocation` ≠ expected; inventory location missing | Show assigned-vs-expected; route to review (`ambiguous match` widened / `inventory location missing`) | Part C §B.8/§A; DEC-015 |

**Microcopy guidelines [Accepted fact — setup-ux P4/P8; Part A §D.11/§D.12;
product-vision "honest by default"]:**

- **Human-readable reason is always primary; raw error/stack trace is behind an
  explicit expand, never primary.**
- **Honest freshness/latency** — label each data type's real sync mode
  (webhook/scheduled), show last-synced/last-reconciled; **no "real-time"
  overstatement**; the 24-hour idempotency window is stated, not implied
  infinite.
- **Speak the user's language, don't leak the platform** — "every 15 minutes",
  never raw `ir.cron` internals (`nextcall`, Scheduler User).
- **Every failure names a concrete next step** (a suggested fix), and the
  action set is **state-conditional** (retry / verify / skip / manual-match —
  never one generic retry button).
- **Exact wording is MBQ-22** — this section fixes intent and pattern, not the
  final strings.

---

## 15. Cross-screen consistency (cross-cutting)

**[Screen blueprint proposal]** the shared components, navigation, and journey
rules that make the screens read as one premium product rather than a set of
disconnected views.

- **Shared components / concepts [Accepted fact — DEC-008 §K rule 2; RA-013;
  Part A §A.5 seams]:** one dashboard, one sync center, one error/manual-review
  center; domain modules contribute *data/categories/steps* via the accepted
  seams, never parallel surfaces. One binding/audit concept, one job/log/error
  substrate behind every screen.
- **Navigation / breadcrumb expectations [Screen blueprint proposal]:** a
  predictable app → region → list → record → related-record path; the
  persistent connection-health indicator and store context (S1/S2) are present
  on every screen; every drill-down has a path back.
- **Status badges [Screen blueprint proposal on Part A §D.3/§D.4]:** a single
  status-badge vocabulary for the ten job states and the sixteen error classes,
  used identically on the dashboard, sync center, error center, and every
  domain screen — `retry_waiting` (system-owned) always visually distinct from
  `blocked_manual_review` (operator-owned), `failed_retryable` (fixable), and
  `failed_final` (terminal).
- **Action buttons [Accepted fact — Part A §G.3/§G.4/§H]:** a consistent
  action set (open source record, open mapping, verify, retry-when-safe,
  cancel/supersede, confirm) with the same state-conditional rules everywhere;
  the same action never means two different things on two screens.
- **Audit trail access [Accepted fact — Part A §D.10; §J.2]:** every record
  and job exposes its audit trail (attempted / actually written / skipped-by-
  rule / confirmed-by-whom, before/after for destructive ops) via a consistent
  affordance (Odoo chatter/log pattern), visible to all roles.
- **Links between related screens:** the cross-references are bidirectional —
  a dashboard count → filtered sync/error view; an error entry → its job → its
  source record → its binding/matching; a matching resolution → back to the
  held job. **No count, error, or hold is a dead end.**
- **Operator journey continuity — dashboard → error → fix → retry [Accepted
  fact — setup-ux north star; product-vision differentiation theme 2]:** the
  spine of the whole product is a continuous loop: **see** (dashboard S5) →
  **diagnose** (error center S7 with reason + sub-reason + suggested fix) →
  **fix** (matching S8 / preview S9 / settings S4 / domain screen) →
  **retry/confirm** (via the same guarded, audited action) → **verify**
  (freshness/success updates on the dashboard). Every screen must preserve this
  loop; a screen that ends the loop (an error with no next action, a count with
  no destination) fails the premium bar.

---

## Premium UI/UX acceptance checklist

**[Screen blueprint proposal]** the bar every operator-facing surface must
clear **before implementation**, derived from the product-vision **premium
quality bar** and **seven non-negotiables** and the setup-ux **12 principles**.
This checklist is proposed as the Part D acceptance gate; it does not itself
authorize implementation.

A screen is **premium-ready** only if it clears all of:

1. **Answers the three questions** — a user can answer "Is everything OK? What
   failed and why? What do I do next?" from the connector's surfaces without
   reading source or filing a ticket. *(setup-ux north star)*
2. **Correct under failure & safe** — every destructive/first-push/notification
   action has a preview or explicit confirmation; **no flag bypasses a guard**;
   the screen never enables silent data loss. *(product-vision "Safe"; Part A
   §I.5)*
3. **Recovery-first** — every failure is isolated, reason-coded, and has a
   named next action; retry is state-conditional (auto where safe, one-click
   where manual), never a bare generic button, never a dead end. *(setup-ux P6;
   Part A §G.4/§H)*
4. **Observable & honest** — status and freshness are visible and truthfully
   labelled; no "real-time" overstatement; raw platform internals never leak.
   *(setup-ux P4/P8; product-vision "Observable & honest")*
5. **No blind create / no name-only match** — every create/bind is preceded by
   a duplicate-prevention preview (interactive/batch) or the accepted
   pre-create gate (automated); name is never an automatic match key.
   *(DEC-003/006; Part B §A.9/§B.9)*
6. **Human-readable first, technical behind expand** — reasons and fixes are
   plain language; stack traces/error codes are secondary. *(Part A §D.11/§D.12;
   setup-ux P8)*
7. **Role-aware** — action affordances render only for entitled roles;
   visibility of a problem is never restricted to those who can fix it; the
   credential value is never shown to any role. *(Part A §F.5/§J.2)*
8. **Approachable then powerful** — sensible defaults with inline help on jargon
   fields; advanced power is opt-in (progressive disclosure); no toggle-dense,
   unexplained-jargon screen. *(setup-ux P3/P11; product-vision
   "Approachable then powerful")*
9. **Odoo-native & consistent** — reuses Odoo view/widget conventions and the
   shared component/status-badge/action vocabulary (§15); one dashboard/sync/
   error center, never per-domain clones. *(DEC-008; RA-013)*
10. **Every state designed** — empty / loading / success / warning / blocked-
    manual-review / failed-retryable / failed-terminal states exist for the
    screen; **no screen ships with only its happy path.** *(§14; MBQ-53 scope)*
11. **Continuity preserved** — the dashboard → error → fix → retry → verify loop
    is unbroken; every count/error/hold links to where it is resolved. *(§15)*
12. **Evidenced & governed** — the screen traces to an accepted DEC/AR flow and
    a Part A/B/C contract; it introduces no new error class, job source, guard
    bypass, or unauthorized scope, and it decides no open MBQ. *(CLAUDE.md
    §7/§8; DEC-009 fixed registries)*

---

## MBQ-53 disposition

**Proposed partially resolved** (not fully resolved; and **open** until DEC-016
is accepted — a sprint whose companion decision record is still *Proposed*
yields a *Proposed …* label that remains open, per the open-questions register
vocabulary note).

**What this Part D proposes to satisfy in MBQ-53:** the screen inventory (§0);
navigation / information architecture (§1, §15); Odoo-native interaction
patterns (throughout, §14/§15); screen-level specs — purpose, users, entry
points, information, actions, blocked states, links, decision/MBQ dependencies —
for the dashboard, setup wizard, store settings, sync center, error center,
matching center, and the product-diff / inventory-first-push / duplicate-
prevention preview screens (§2–§13); empty / loading / success / error /
manual-review states for every screen (§14, plus each screen's states line);
UX copy **guidelines** and error-message **style** (§14); and a **premium
UI/UX acceptance checklist** (above).

**What remains open (why "partially"):** exact user-facing **copy strings**
remain **MBQ-22** (this part gives guidelines/patterns, not final wording);
exact Odoo **view/menu/action XML IDs, model/field names, security groups, and
access CSVs** remain **MBQ-01/02/03/44**; pixel-level **wireframe artwork** is
out of this screen-blueprint's scope; and the **admin-vs-functional-user
surface split** remains **MBQ-45**. None of these is decided here.

**Justification for partial (not full) resolution:** the screen-design *layer*
MBQ-53 asks for is proposed complete, but MBQ-53's own text spans "UX copy
guidelines" whose exact strings are the separately-tracked open **MBQ-22**, and
implementation of any of these screens still requires the exact identifiers of
**MBQ-01/02/03/44** and a resolution of **MBQ-45**. Marking MBQ-53 anything
stronger than *proposed partially resolved* would over-claim against those live
rows and against the fact that DEC-016 is not yet accepted.

**MBQs explicitly NOT resolved by this part (carried forward, open):**
MBQ-01, MBQ-02, MBQ-03, MBQ-04, MBQ-05, MBQ-06, MBQ-07, MBQ-08, MBQ-09,
MBQ-10, MBQ-13, MBQ-16, MBQ-17, MBQ-18, MBQ-19, MBQ-20, MBQ-21, MBQ-22,
MBQ-24, MBQ-27, MBQ-28, MBQ-33, MBQ-34, MBQ-35, MBQ-41, MBQ-44, MBQ-45,
MBQ-46, MBQ-49, MBQ-51, MBQ-52, MBQ-54, MBQ-55, MBQ-56, MBQ-57, MBQ-58,
MBQ-59 (policy accepted; exact detail open), MBQ-60, MBQ-61, MBQ-62, MBQ-63,
and all remaining implementation-planning / official-doc-verification rows.
(Rows already accepted or resolved by DEC-013/014/015 — e.g. MBQ-07 direction,
MBQ-11, MBQ-23/25/26/29/30/31/36/37/38/39/40/42/43/47 — keep their prior
status; this part does not change them.)

---

## Risks and uncertainties

1. **Risk:** a screen spec being read as authorizing implementation or fixing
   an Odoo identifier. **Mitigation:** proposed-names-only discipline
   throughout; every connector model/field/menu/group name routed to
   MBQ-01/02/03/44; explicit "no code, not accepted, Part E not started"
   framing; the Status and checklist restate it.
2. **Risk:** the blueprint silently deciding an open question (esp. MBQ-33/34/
   41 inventory/fulfillment postures, or MBQ-45 surface split). **Mitigation:**
   these are shown as **[Recommendation]** with the decision owner preserved,
   and the screen is designed to *accommodate* the recommended posture without
   deciding it; each is listed in the screen's open-MBQ line and in the MBQ-53
   disposition.
3. **Risk:** inventing a state, error class, or job source not in the accepted
   registries. **Mitigation:** §14 draws only from the fixed ten states / six
   sources / sixteen classes; §S6/§S13 explicitly forbid a fabricated seventh
   source (MBQ-62 open); no 17th error class or new sub-reason is introduced.
4. **Risk:** over-claiming MBQ-53 as fully resolved. **Mitigation:** proposed
   **partially** resolved, with MBQ-22/01/02/03/44/45 and wireframe-artwork
   explicitly carved out and justified.
5. **Uncertainty:** exact readiness-check essential-vs-nice split (MBQ-06)
   shapes the wizard's warning-vs-blocked gating; exact copy (MBQ-22) shapes
   microcopy; both are open and flagged, so the screen specs are structured to
   absorb either resolution without redesign.
6. **Uncertainty:** MBQ-60 (tracking-module dependency) and MBQ-63 (inventory-
   webhook implementation-vs-candidate) affect whether the fulfillment tracking
   and inventory webhook-import screen states are ever exercised in Phase 1;
   the screens show these as honest states rather than assuming resolution.

## No implementation authorized

**This document does not authorize implementation.** It is a proposed,
documentation-level screen blueprint only. No code, Odoo module, model, view,
controller, security file, manifest, test, or CI change is created or permitted
by it, and none may be created until ChatGPT (1) accepts this Part D (and the
relevant domain/substrate blueprints), (2) resolves or consciously accepts the
implementation-blocking open questions for the affected scope, and (3)
separately opens the implementation gate per
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10 and
`CLAUDE.md` §5 — see
[`master-blueprint.md`](./master-blueprint.md) "Criteria for when
implementation may later be opened". **Part E (implementation-planning bridge)
remains Not started.**

## Review / change control

- **This document proposes Master Blueprint Part D only.** No accepted decision
  (DEC-003–DEC-015) is re-litigated; no AR/RA row is modified; checked against
  `rejected-approaches-log.md` before drafting — nothing reintroduced.
- **Related:** [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)
  (Proposed for ChatGPT review); **AR-013**
  ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md),
  Proposed for ChatGPT review); the companion index
  [`master-blueprint.md`](./master-blueprint.md); the open-questions register
  [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
  (MBQ-53 proposed partially resolved); Part A/B/C blueprints (accepted context,
  unmodified).
- **Further changes** to this record require ChatGPT review, mirroring the
  DEC-013 through DEC-015 change-control pattern.
