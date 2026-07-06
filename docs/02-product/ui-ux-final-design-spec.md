# UI/UX Final Design Specification

> Implementation-ready UI/UX design specification for the premium
> **Odoo 19 ↔ Shopify Connector** — MVP and premium foundation. Prepared in
> the **UI/UX Final Design Sprint (2026-07-06)** on top of the accepted
> screen-design blueprint
> ([`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md),
> accepted via
> [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)),
> the accepted operator flows
> ([`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md) /
> [`ux-operator-flow.md`](./ux-operator-flow.md)), the accepted Master
> Blueprint Parts A–E (DEC-013/014/015/017), the post-Part-D decisions
> DEC-018/DEC-019/DEC-020, and the accepted MBQ-04 credential posture
> ([`../03-architecture/mbq-04-credential-persistence-decision-proposal.md`](../03-architecture/mbq-04-credential-persistence-decision-proposal.md),
> PR #90). Companion documents produced in the same sprint:
> [`screen-inventory-and-navigation-map.md`](./screen-inventory-and-navigation-map.md),
> [`mvp-user-flows-and-state-models.md`](./mvp-user-flows-and-state-models.md),
> [`../05-qa/ui-ux-design-review-checklist.md`](../05-qa/ui-ux-design-review-checklist.md),
> [`../07-implementation-plan/ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md).

## Scope and status

- **This document is docs-only.** It creates no code, no Odoo module, no
  view, no menu, no action, no wizard, no model, no field, no security file,
  and no credential/token/secret artifact of any kind.
- **It does not authorize implementation.** The no-code gate for
  operator-facing UI (`CLAUDE.md` §4–§5;
  [`../07-implementation-plan/limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md))
  remains fully in force: the only open implementation gate is the limited,
  **core-only, zero-UI** gate (which authorized exactly one implementation
  task, Task 001; Task 001A was a docs-only QA closure). Every operator-facing screen,
  wizard, dashboard, and view described here remains **blocked** until
  ChatGPT separately opens a UI implementation gate and each future task is
  written to the `CLAUDE.md` §9 template.
- **It translates accepted UX/architecture into implementation-ready screen
  specs.** It inherits, and never contradicts or weakens, the accepted
  behaviour in DEC-003 through DEC-020 and Master Blueprint Parts A–E. Where
  it adds design detail beyond the accepted blueprint, that detail is
  labelled **[Design proposal — this spec]** and is subject to ChatGPT
  review; it is not a decision.
- **It does not create views, code, menus, actions, wizards, models, or
  fields** — model/field/group names that appear here are either the
  **accepted planning names** from
  [`../07-implementation-plan/core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md)
  (AR-019: `shopify.connector.store`, `shopify.connector.store.settings`,
  `shopify.connector.location`, `shopify.connector.binding.mixin`,
  `shopify.connector.job`, `shopify.connector.job.log`;
  `group_shopify_connector_auditor/_operator/_reviewer/_admin`) or are
  explicitly marked as proposed directions. Exact view/menu/action XML IDs
  remain **MBQ-03 (open)**; exact user-facing copy remains **MBQ-22 (open)**
  — every quoted string in this document is **illustrative, not final**.

### Claim labels used throughout

| Label | Meaning |
| --- | --- |
| **[Accepted — DEC-0XX / Part X §Y]** | Restates an accepted decision or accepted blueprint content. Binding; never re-litigated here. |
| **[Decided — DEC-018/019/020]** | A decision made after Part D was accepted; binding. Screens in Part D that were drawn to "accommodate either resolution" are now specified against the decided outcome. |
| **[Accepted posture — MBQ-04 / PR #90]** | The accepted credential-persistence posture (Option B, posture level only). |
| **[Design proposal — this spec]** | New design-level detail this spec introduces (layout, grouping, interaction nuance, sample copy structure). Subject to ChatGPT review; not a decision; never weakens an accepted guard. |
| **[Illustrative copy — MBQ-22 open]** | Sample wording to set tone and shape. Final copy is an open item. |
| **[Open item — MBQ-nn / this spec]** | An unresolved implementation-planning detail. Recorded, never asserted. |

---

## Premium Simplicity Standard

This section defines the visual and interaction standard every connector
surface must meet. It is the single quality bar the companion review
checklist tests against. **[Design proposal — this spec]**, grounded in the
accepted Part D §19 premium acceptance checklist, the screenshot-grounded
UX benchmark ([`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md)),
and [`setup-ux-principles.md`](./setup-ux-principles.md) (recommendation-level
inputs).

### The design rule

> **Premium does not mean more screens, more colors, more charts, or more
> complexity. Premium means clarity, confidence, polish, guidance, and
> recovery.**

Every proposed screen, card, field, button, badge, and sentence in this
specification must justify itself against that rule. Anything that informs
nothing, reassures nothing, and guides no action is removed.

### How the UI should feel

Calm, competent, and quietly confident. Opening the connector should feel
like opening a well-run control room, not a server log: the operator sees
one clear answer ("everything is OK" or "3 things need you"), a small
number of well-labelled places to go, and — when something is wrong — a
plain-language explanation with a next step already attached. Nothing
flashes, nothing shouts, nothing dead-ends.

### What "premium" means in an Odoo-native backend product

Premium here is **not** a custom-styled SaaS app grafted into Odoo. The
research base shows competitor connectors fail in two opposite directions:
exposing raw platform plumbing (Webkul's raw `ir.cron` fields) or piling on
toggle-dense configuration (Emipro's 10+ toggles per config screen;
Teqstars similarly toggle-dense) (**[Accepted evidence —
ux-ui-benchmark.md]**). Premium in an Odoo backend means:

1. **Odoo-native bones, connector-grade polish.** Standard Odoo 19 list,
   form, kanban, wizard, statusbar, smart-button, chatter, and activity
   patterns are reused everywhere they fit (Part D §3, accepted). Custom
   surfaces exist only where Part D already justifies them (readiness
   panel, command-center card grid, recovery panel, diff preview,
   class-conditional retry actions). A user who knows Odoo already knows
   how to use this connector.
2. **Fewer, better elements.** One dashboard, one sync center, one error
   center, one matching surface — shared by all domains (**[Accepted —
   RA-013 / DEC-008 §K]**). No parallel per-domain monitors, ever.
3. **Every status is a sentence, not a code.** Text label + severity/owner
   word, never colour or icon alone (**[Accepted — Part D §17 rules 8–9]**).
4. **Guidance is built in, not documented elsewhere.** Helper text under the
   field, a suggested fix inside the error, the next step inside the empty
   state.

### How to keep it clean and simple

- **One job per screen.** Each screen answers exactly one operator question
  (see the per-screen "purpose" lines below). A screen that starts
  answering two questions gets split or, more often, the second question is
  routed to the surface that already owns it.
- **Field budget.** **[Design proposal — this spec]** As a working
  discipline: a form's always-visible region should hold roughly **7 ± 2
  primary elements** (fields or field groups); everything else moves behind
  a notebook tab, an "advanced" group, or progressive disclosure. This is a
  design discipline for implementation review, not a hard validation rule.
- **Action budget.** **[Design proposal — this spec]** One primary action
  per screen state, at most two secondary actions visible; everything else
  lives in the standard Odoo action/gear menu. Destructive actions are
  never visually adjacent to the primary action (Part D §18 rule 9,
  accepted: destructive controls come last, never default focus).
- **Whitespace and grouping do the explaining.** Related fields are grouped
  with a plain-language group label; unrelated settings never share a
  group. Helper text is one sentence, under the field, in the user's
  language.

### How to avoid clutter

The named anti-patterns from the accepted research are hard "do not do"
rules for every screen (**[Accepted evidence — ux-ui-benchmark.md "UX gaps";
Part D §19.G]**): no raw `ir.cron` internals; no toggle walls without
defaults and inline help; no unexplained jargon ("Forecast vs Free-to-Use"
without a sentence of help); no raw stack traces as primary content
(RA-016); no email-only error surfaces; no "real-time" overstatement; no
vanity metrics; no irreversible action without a consequence-stating
confirmation.

### How to create smooth guided flows

Multi-step work (setup, first push, matching, recovery) always follows the
same accepted confidence loop: **stage → inspect → process → verify → log**
(**[Accepted evidence — ux-ui-benchmark.md]**; Part D §18 rule 6). Each step
ends with an explicit "verified"/"done" moment before the next step begins
(Part D §5, accepted); the flow can be left safely at any point and resumed
without restarting (Part A §E / Part D §3 wizard-resume, accepted); and the
current position, what remains, and what happens next are always visible.

### How to make errors feel recoverable

Every failure surface leads with a plain-language reason, a suggested fix,
and an owner state ("waiting on you" / "the system is retrying" /
"resolved") (**[Accepted — DEC-009; Part A §H; DEC-012 §5]**). Technical
detail exists but is one deliberate click away, behind "View technical
details". Retry is offered only where it is safe, and the screen says *why*
it will or will not retry (Part D §4.1 four retry cases, accepted). The
emotional register is factual and non-blaming: an error is a state of the
system, never an accusation, and never a dead end.

### How to make setup feel trustworthy

Trust is built by **proving, not promising**: each wizard step closes with
a verified confirmation; the Test Connection step reports a named pass/fail
with a reason; the readiness step shows a per-check pass/fail grid split
into "must pass" and "good to fix" (**[Decided — DEC-018 MBQ-06]**); and the
final summary states, in the operator's words, exactly what the connector
will and will not do now (Part D §5 confidence statement, accepted).
Credential handling is honest: the token is masked on entry, never
displayed again, and the UI **never claims encryption** — copy may describe
access restriction and masking only (**[Accepted posture — MBQ-04 / PR #90]**).

### How to make dashboards useful without becoming complex

The dashboard leads with one plain-language answer to "Is everything OK?",
then exactly the accepted nine cards — each of which either informs,
reassures, or routes to a filtered action view (**[Accepted — Part A §F.1 /
DEC-012 §3; Part D §7]**). Nothing on the dashboard is decorative. The rule
of thumb this spec adds: **[Design proposal — this spec]** the dashboard
must be useful in 10 seconds — a first-time viewer should be able to answer
"is anything wrong, and where do I click" within one screenful, without
scrolling, reading documentation, or interpreting a chart.

### How to use progressive disclosure

Three tiers, applied uniformly: (1) **default view** — safe, opinionated
defaults with one-sentence helper text; (2) **advanced groups/tabs** —
power settings (mappings, cadence, gateway→journal rows) behind a labelled
tab or "advanced" group; (3) **technical detail** — raw payloads, class
codes, and identifiers behind an explicit expand, for support and
diagnosis, never as primary content. (**[Accepted evidence —
setup-ux-principles.md Principle 3; Part D §17 rule 1]**.)

### How to make technical connector operations understandable to business users

Every internal vocabulary item has exactly one human-facing rendering,
reused verbatim on every surface (Part D §18 rule 2, accepted): job states
render as plain words ("Waiting to retry", not `retry_waiting`), error
classes render as reasons ("A product on this order isn't matched yet",
not "mapping missing"), and mechanisms are named honestly ("checked every
15 minutes", not `nextcall`). The technical token appears only inside the
technical-detail expand. Exact strings are **MBQ-22 (open)**; the rendering
rule itself is accepted (Part D §17 rules 5, 9).

---

## UX principles

Connector-specific principles, each traceable to accepted decisions. These
restate and sharpen the accepted spine for implementers; none is new
architecture.

1. **Setup simplicity.** A non-technical operator reaches a proven, safe
   connection through one guided wizard — no server-config hand-editing in
   the credential step, no pasted scope strings presented as free text, no
   documentation dependency. **[Accepted — DEC-004; DEC-012 §1; Part A §E]**
2. **Safe defaults.** Notification default off; draft-first export; review-
   then-apply for ongoing inventory writes; no domain enabled silently; no
   source-of-truth guessed. **[Accepted — DEC-007; Decided — DEC-018
   MBQ-34/MBQ-41]**
3. **No silent sync.** Nothing writes to either system without an accepted
   gate: setup completion, the pre-create gate for automated imports, or a
   blocking preview for interactive work. **[Accepted — DEC-003/DEC-006;
   DEC-014 point H (MBQ-59)]**
4. **Operator confidence.** Every operation is inspectable before, during,
   and after: stage → inspect → process → verify → log. **[Accepted — Part D
   §18 rule 6]**
5. **Explainable errors.** Reason first, fix attached, owner named,
   technical detail on demand. **[Accepted — DEC-009; RA-016]**
6. **Retry/recovery first.** Failures are recovery surfaces; retry is
   class-conditional (four UI cases), never a blanket button, never absent.
   **[Accepted — DEC-009; RA-014/RA-015]**
7. **Premium but Odoo-native.** Standard Odoo patterns everywhere they fit;
   custom surfaces only where Part D justifies them. **[Accepted — Part D §3]**
8. **Human-friendly language.** Business words, one consistent vocabulary,
   no internal tokens or API terms as primary labels. **[Accepted — Part D
   §17]**
9. **Progressive disclosure.** Defaults → advanced → technical detail; the
   default view is always safe and always enough for routine operation.
   **[Accepted evidence — setup-ux-principles.md Principle 3]**
10. **Calm error handling.** Factual, non-alarmist, non-blaming tone;
    recoverable framing; consequences stated before destructive actions.
    **[Accepted — Part D §17 rules 7, 10]**
11. **Clear next best action.** Every count, card, error, and empty state
    carries exactly one obvious next step. A number with no path to act on
    it is not acceptable. **[Accepted — DEC-012 §3 item 10; Part A §F.3]**
12. **No technical jargon where business users need to act.** Jargon may
    exist only inside the technical-detail expand and the Auditor-facing
    audit trail — never on the action path. **[Accepted — Part D §17 rule 9]**

---

## User roles and surfaces

**[Accepted — DEC-012 §10; Part A §J; Decided — DEC-018 MBQ-45]:** four
roles, mapping **1:1** to four Odoo security groups
(`group_shopify_connector_auditor/_operator/_reviewer/_admin` — accepted
planning names, AR-019), on **one shared, role-gated surface** — not a
forked admin app / operator app pair. All roles see the same dashboard,
sync center, and error center; **action affordances** are gated, not the
surfaces. Hierarchy (accepted — DEC-013): Admin ⊇ Operator + Reviewer;
Operator and Reviewer are peers; everyone ⊇ Auditor visibility.

### Connector Administrator (persona P2)

- **Sees:** everything — all surfaces, all settings, masked credential
  *status* (present / last verified — never the value).
- **Does:** runs the setup wizard; edits store settings, mappings,
  source-of-truth and notification defaults; enables/disables domains;
  disconnects/reconnects; everything an Operator and Reviewer can do.
- **Must not see:** the stored credential value after entry — no connector
  surface exposes read-back for any role, including Admin. **[Accepted —
  DEC-004; Part A §J.2; Accepted posture — MBQ-04]**
- **Elevated-permission actions:** credential entry/replacement,
  disconnect, domain enable/disable, source-of-truth changes, notification
  default changes, location mapping edits.
- **Premium UX for this role:** the wizard and settings feel expert-guided,
  not expert-demanding — consequence-stating confirmations replace fear;
  changing a live setting (e.g. source of truth) explains what will change
  in behaviour, in one sentence, before the save.

### Connector Operator (persona P1)

- **Sees:** dashboard, sync center, error center, matching center,
  previews, job/log detail; read-only view of settings.
- **Does:** triggers manual syncs and previews; retries **safe** jobs;
  runs verification reads; opens source/mapping records; performs manual
  product/variant matching.
- **Must not see / do:** cannot change settings, credentials, mappings, or
  defaults; cannot resolve confirmation-required manual-review items (that
  is the Reviewer's auditable act).
- **Elevated-permission actions:** none — anything beyond safe
  run/retry/match routes to Reviewer or Admin via the assignment
  convention (Part D §3 activities, accepted).
- **Premium UX for this role:** the Operator's whole day fits in dashboard
  → filtered list → fix → verify; a blocked item never dead-ends — the
  screen names whose action it awaits and offers to route it there.

### Connector Reviewer / Manual Review Owner

- **Sees:** the same shared surfaces; their work queue is the error
  center's manual-review view, keyed by the six accepted sub-reasons.
- **Does:** resolves `blocked_manual_review` items — approves/declines
  matches, confirms duplicate-risk creates, confirms destructive-write and
  first-push guards, confirms notification-confirmation-missing cases.
  Every resolution is recorded with who/when/what. **[Accepted — DEC-009
  audit requirements]**
- **Must not do:** change settings; run general syncs/retries (Reviewer is
  approval-focused — MBQ-47, accepted).
- **Elevated-permission actions:** resolving the six confirmation-required
  sub-reasons is the Reviewer's elevated, audited act — the one thing an
  Operator cannot do.
- **Premium UX for this role:** a reviewable item is a **decision package**:
  what the system wants to do, why it stopped, the evidence (candidates,
  diffs, totals), and two clearly-consequenced choices — never a bare
  approve/reject pair without evidence.

### Read-only Auditor (persona P3)

- **Sees:** everything — dashboard, jobs, logs, errors, bindings, audit
  trails, settings (read-only, credentials masked).
- **Does:** nothing that changes state. No trigger, retry, confirm, or
  edit affordance is rendered for this role (not merely disabled —
  **[Design proposal — this spec]** hidden, to keep the read-only surface
  visually calm).
- **Must not see / do:** the credential value (as for every role); any
  state-changing affordance.
- **Elevated-permission actions:** none — structurally read-only.
- **Premium UX for this role:** the audit story is coherent without asking
  anyone: every job shows what was attempted, written, skipped (and by
  which rule), and who confirmed what, with before/after values for
  destructive operations. **[Accepted — DEC-009]**

---

## Screen-by-screen specification

Screens are keyed to the accepted Part D inventory (S1–S14). Sub-screens
this spec details beyond Part D (store list, job form, job log detail,
audit/history view) are **[Design proposal — this spec]** renderings of
already-accepted models/surfaces — they add no new surface to the accepted
inventory. For every screen, "exact XML IDs" = **MBQ-03 (open)** and "exact
copy" = **MBQ-22 (open)**; neither is repeated in every line below.

**Shared state definitions** (Part D §4, accepted): every screen specifies
empty, loading, success, error, and manual-review states; this spec adds a
distinct **warning** state (non-blocking degradation, e.g. throttled API,
overdue sync) as a **[Design proposal — this spec]** refinement.

---

### 0. Shopify Connector main app entry

- **Purpose.** One top-level "Shopify Connector" app menu whose landing
  surface is the Dashboard (S3). **[Accepted — Part D §2.1]**
- **Premium simplicity goal.** The menu is short enough to memorise: seven
  top-level entries (Dashboard, Sync Center, Error Center, Catalog &
  Matching, Inventory, Fulfillment, Configuration). No domain adds a
  parallel top-level entry. **[Accepted — Part D §2.1; RA-013]**
- **Primary users.** All four roles (menu items role-gated per surface).
- **Entry points.** Odoo main apps menu.
- **Key elements.** The persistent connection-health indicator (store
  state + API health as one glanceable, honest, named status) visible from
  every connector region. **[Accepted — Part D §2.1]**
- **Primary action.** Navigate; the indicator itself is clickable → Store
  Settings connection band. **[Design proposal — this spec]**
- **Visual hierarchy.** Dashboard first; recovery surfaces (Sync Center,
  Error Center) next; domain work areas; Configuration last.
- **States.** Not stateful beyond the health indicator (which must carry a
  text label, never colour alone — Part D §17 rule 8).
- **Permissions.** All entries — including the Configuration branch — are
  visible to all roles with role-gated actions (edit = Admin); the one
  exception is the Setup Wizard entry, hidden for non-Admins. Roles &
  Access is read-only for everyone. (Matches the navigation map's
  visibility matrix.)
- **Must not be implemented yet.** Any menu/action XML (MBQ-03); the entire
  app shell is blocked pending the UI gate.
- **What would make it non-premium.** More than one level of nesting below
  the seven entries; per-domain dashboards; a menu entry that opens an
  unfiltered raw model list.

### 1. Dashboard / command center (S3)

Specified in full in the dedicated section below ("Dashboard / command
center design").

### 2. Store list

- **Purpose.** List the connected store record(s) (`shopify.connector.store`,
  accepted planning name) and their headline state. Phase 1 is single-store
  (**[Accepted — DEC-003]**), so this list will usually hold one row; it is
  specified so multi-store expansion does not require redesign.
  **[Design proposal — this spec]**
- **Premium simplicity goal.** With one store connected, this screen should
  feel almost invisible — most operators arrive at the store form or the
  dashboard directly; the list exists for orientation and future
  multi-store, not as a daily surface.
- **Primary users.** Admin (manage); all roles (read).
- **Entry points.** Configuration → Store Settings.
- **Key fields shown (list row).** Store name; shop domain; connection
  state (Connected / Setup incomplete / Disconnected / Reconnect needed —
  Part D §6 proposal); enabled domains (compact labels); last successful
  sync. **[Design proposal — this spec]** — five columns, no more.
- **Primary actions.** Open store form; "Connect a store" (empty state
  only, routes to the setup wizard).
- **Secondary actions.** None in the list; everything else lives on the
  form.
- **Layout.** Standard Odoo list view; no kanban needed for ≤ a handful of
  rows.
- **Validations.** None on the list itself.
- **States.** *Empty:* "No store connected yet — connect your Shopify store
  to begin" + primary button to the wizard (**[Illustrative copy — MBQ-22
  open]**). *Loading:* standard list load. *Success:* n/a (navigation
  surface). *Warning:* a row whose state is "Reconnect needed" shows the
  state word in the row. *Error:* n/a (errors live on the store form /
  error center). *Manual review:* n/a.
- **Permissions.** Create/edit gated to Admin; read for all.
- **Accepted deps / open items.** DEC-003 (single-store MVP);
  store-scoped keys stay multi-store-safe (DEC-006). Exact list columns:
  **[Open item — this spec / implementation planning]**.
- **Must not be implemented yet.** Any view/model artifact; the store model
  exists from Task 001 but exposing it in UI is blocked.
- **What would make it non-premium.** Exposing internal fields (API
  version, worker counts) as list columns; a create button that bypasses
  the wizard.

### 3. Store form / store settings (S2)

- **Purpose.** One place to see and change what the connector is doing for
  this store. **[Accepted — DEC-012 §2; Part A §B/§I]**
- **Premium simplicity goal.** An Admin can answer "what is this connector
  allowed to do right now?" from the top band without opening a single tab.
- **Primary users.** Admin (edit); Operator/Reviewer/Auditor (read).
- **Entry points.** Configuration → Store Settings; dashboard health card;
  wizard finish.
- **Key fields / regions (in order).** **[Accepted content — Part A §B/§I;
  layout is a Design proposal — this spec]:**
  1. **Connection status band** (top, full width): connection state +
     API health (named, honest) + token status (present / last verified —
     never the value) + Reconnect / Disconnect actions. Text labels
     always; colour reinforces only.
  2. **Domains group:** four enablement toggles (Products, Orders &
     Customers, Inventory, Fulfillment) with one-sentence helper text each;
     enabling re-enters that domain's own guard; disabling stops new sync
     and preserves history. **[Accepted — Part A §I.4; DEC-012 §2]**
  3. **Sync behaviour group:** source-of-truth summary (product matching;
     price authority; inventory quantity — links to S12 for detail),
     notification default (off unless explicitly opted in — **[Decided —
     DEC-018 MBQ-41]**), reconciliation cadence summary in plain language
     ("checked every N hours per domain" — **[Decided — DEC-018 MBQ-17
     posture]**).
  4. **Notebook tabs (progressive disclosure):** Locations (S10 embed or
     link), Gateway → journal mapping (classification only, never posting —
     **[Accepted — DEC-014 point G]**), API & version (pinned API version +
     deprecation warnings — **[Decided — DEC-018 MBQ-52]**), Advanced.
- **Primary actions.** Save (standard Odoo); Reconnect.
- **Secondary actions.** Re-run setup wizard; Disconnect (destructive,
  last, never default focus).
- **Visual hierarchy.** Status band → domains → behaviour → tabs. The most
  consequential state (connection) is always first.
- **Validations.** Source-of-truth changes after first sync show a
  consequence-stating confirmation ("this changes which system wins on the
  next sync") — **[Accepted — DEC-012 §2 item 5 (warning), wording MBQ-22]**.
  Disconnect confirmation states the decided retention posture: credentials
  revoked, sync stops, **bindings/jobs/logs/audit history preserved**;
  reconnect is explicit and re-runs readiness. **[Decided — DEC-018 MBQ-08]**
- **States.** *Empty:* pre-setup → the form redirects attention to the
  wizard ("Setup incomplete — N steps remain", listing them). *Loading:*
  health/token re-validation with honest progress. *Success:* explicit
  "Settings saved" confirmation. *Warning:* API health "Throttled" or
  "Reconnect recommended" band states with one-line explanations. *Error:*
  reconnect failure shows reason + fix. *Manual review:* n/a.
- **Permissions.** Edit = Admin; read = all. Credential value: no read-back
  for any role. **[Accepted — Part A §J.2]**
- **Accepted deps.** DEC-004, DEC-012 §2, Part A §B/§I, DEC-018
  (MBQ-08/17/41/45/52/54), MBQ-04 posture.
- **Open items.** Settings-form layout/composition (**MBQ-03 / future
  task-spec detail** — the settings *model* shape and its exact Phase 1
  field names are already resolved by AR-019, so no MBQ-07 residual
  exists); exact disconnect confirmation copy (**MBQ-22**); domain
  uninstall disclosure copy (**DEC-018 MBQ-54 residual**).
- **Must not be implemented yet.** All of it — settings UI is blocked; the
  credential field itself is not yet designed (MBQ-04 implementation
  planning task).
- **What would make it non-premium.** A toggle wall (settings not grouped
  by intent); exposing raw cron fields or GraphQL cost numbers; a
  disconnect button adjacent to Save; describing credential storage as
  "encrypted" (**prohibited — MBQ-04 posture**).

### 4. Setup wizard (S1)

Specified in full in the dedicated section below ("Setup wizard detailed
flow"). Summary spec:

- **Purpose.** Take a merchant from nothing to a proven, safe connection.
  **[Accepted — DEC-012 §1; Part A §E]**
- **Premium simplicity goal.** Guided, calm, trustworthy — one decision per
  step, one "verified" moment per step, never a configuration dump.
- **Primary users.** Admin only.
- **Entry points.** First install; Configuration → Setup Wizard
  (re-runnable, resumes rather than restarts — **[Accepted — Part D §3]**);
  dashboard "finish setup" nudge while `setup_incomplete`.
- **Permissions.** Admin only; other roles see the incomplete-setup state
  on the dashboard, never the wizard itself.
- **Must not be implemented yet.** All of it — wizard, credential entry,
  test connection, and readiness checks are each explicitly blocked
  (limited gate: "No setup wizard. No test connection." — AR-021).
- **What would make it non-premium.** Presenting all choices on one long
  form; silent defaults for direction/source-of-truth/notification; a
  scope list rendered as pasteable free text; fear-inducing failure copy.

### 5. Credential entry step (wizard step; also reachable from S2 for token replacement)

- **Purpose.** Capture the custom-app credential once, safely.
  **[Accepted — DEC-004; Accepted posture — MBQ-04 / PR #90]**
- **Premium simplicity goal.** The single scariest step for a merchant is
  rendered as the calmest: one masked field, one sentence of honest
  reassurance, one clearly-explained "why this way" note.
- **Key fields shown.** Store identity (shop domain, read-only from the
  prior step); one masked credential input; helper text naming where the
  operator finds the token in Shopify's admin (exact mechanics **MBQ-05,
  descoped/open**).
- **Primary action.** Save & continue (which masks permanently).
- **Secondary action.** Back.
- **Layout / visual hierarchy.** One centered content column: read-only
  store identity on top, the single masked input as the visual focus,
  helper sentence beneath, actions at the bottom. **[Design proposal —
  this spec]**
- **Validations.** Non-empty; format sanity only — real validity is proven
  by Test Connection, not by pattern-matching. **[Design proposal — this
  spec]**
- **Honesty rules (binding).** The value is masked on entry and **never
  read back on any surface, for any role**; helper copy may say the token
  is "stored with restricted access and never shown again" and **must not
  say "encrypted"**. **[Accepted — DEC-004; Accepted posture — MBQ-04]**
- **States.** *Empty:* fresh masked field with helper text. *Loading:*
  save-in-progress. *Success:* "Credential saved — next we'll test it"
  moment. *Warning:* n/a. *Error:* save failure with reason. *Manual
  review:* n/a.
- **Permissions.** Admin only.
- **Open items.** Credential model/field/access-group/redaction/rotation
  design — the dedicated MBQ-04 implementation-planning task (**not this
  spec**); token-acquisition walkthrough content (**MBQ-05**).
- **Must not be implemented yet.** Everything — no credential field,
  model, or storage of any kind exists or may be created yet.
- **What would make it non-premium.** Multiple credential fields where one
  suffices; a plaintext preview toggle; security theatre (padlock icons +
  "bank-level encryption" claims — prohibited); burying the "you'll need
  your token from Shopify admin" guidance in external docs.

### 6. Test connection / readiness step (wizard steps; re-run from S2)

- **Purpose.** Prove the connection and prove readiness — explicitly,
  before anything syncs. **[Accepted — DEC-004; Part A §E; DEC-012 §1]**
- **Premium simplicity goal.** A pass/fail moment that builds trust: the
  operator watches named checks complete, sees exactly what passed, and
  understands exactly what (if anything) still blocks them.
- **Key elements.** (1) A discrete **Test Connection** action with named
  pass/fail + reason (never a silent spinner). (2) The **readiness panel**:
  per-check rows split into two groups — **"Must pass"** (the DEC-018
  MBQ-06 essential set: credential validity/test connection, required
  scopes granted, API-version health, store identity confirmed,
  `web.base.url` reachability, webhook HMAC secret *if* webhooks enabled,
  cron/queue health, ≥1 mapped Location where inventory/fulfillment is
  enabled, intentional domain enablement) and **"Good to fix"** (all other
  checks — warn, never block). **[Decided — DEC-018 MBQ-06]**
- **Primary actions.** Run test; Run readiness checks; Continue (enabled
  only when all "Must pass" rows pass).
- **Secondary actions.** Re-run a single check; view check detail.
- **Layout.** Check rows: status word + check name + one-line result +
  (on failure) the fix hint inline. **[Design proposal — this spec]**
- **States.** *Empty:* checks not yet run — "Run checks" is the obvious
  action. *Loading:* per-row progress, honest ("Checking Shopify access…").
  *Success:* all-pass grid + "verified" confirmation. *Warning:* essential
  checks pass, some "good to fix" rows warn — continue is allowed, warnings
  carried to the dashboard. **[Design proposal — this spec]** *Error:* a
  failed essential check shows the specific reason + fix (e.g. "A required
  permission is missing: read_products — update your custom app's scopes in
  Shopify, then re-run"), never a raw HTTP code. *Manual review:* n/a.
- **Permissions.** Admin runs; results visible later to all roles via
  readiness/health surfaces.
- **Accepted deps / open items.** These runs are `setup_readiness_check`
  jobs — read-only, never business sync (**[Accepted — DEC-012 §1]**).
  Exact check thresholds and wording: implementation planning (**DEC-018
  MBQ-06 residual; MBQ-22**).
- **Must not be implemented yet.** All of it (explicitly named blocked in
  the limited gate).
- **What would make it non-premium.** A single opaque "connection failed";
  mixing must-pass and nice-to-have checks in one undifferentiated list;
  letting the operator proceed with a failed essential check.

### 7. Location mapping screen (S10)

- **Purpose.** Explicit Odoo location ↔ Shopify Location mapping — the
  precondition for any inventory write. **[Accepted — DEC-010; Part C §A.2]**
- **Premium simplicity goal.** A mapping table so unambiguous it reads like
  a sentence: *this* Odoo location publishes stock to *that* Shopify
  location.
- **Primary users.** Admin.
- **Entry points.** Inventory → Location Mapping; store form Locations tab;
  readiness check fix-link; error-center `inventory location missing`
  entries.
- **Key fields shown.** One row per mapped pair: Odoo location (internal
  types only offered — vendor/customer/virtual/transit never appear);
  Shopify Location (fetched, by name + ID); mapping status; first-push
  status for the pair (pending / confirmed — links to S11).
  **[Accepted — Part C §A.2; Part D §14.1; first-push-per-pair column
  follows Decided — DEC-018 MBQ-33]**
- **Primary actions.** Add mapping; Save.
- **Secondary actions.** Remove mapping (consequence-stating confirmation);
  Refresh Shopify locations.
- **Validations.** No name-based inference, ever; each Odoo location maps
  to exactly one Shopify Location; at least one mapping required before any
  inventory write. **[Accepted — DEC-010]**
- **States.** *Empty:* "No locations mapped yet — map at least one to
  enable inventory sync" + Add. *Loading:* fetching Shopify Locations.
  *Success:* pair saved with confirmation. *Warning:* a mapped Shopify
  Location reported disconnected (`INVENTORY_LEVELS_DISCONNECT`) surfaces
  as a named warning row, routed to the error center — never a silent
  skip. **[Accepted — Part D §14.1]** *Error:* fetch failure with reason +
  retry. *Manual review:* ambiguous candidates route to `ambiguous match`
  handling.
- **Permissions.** Edit = Admin; read = all.
- **Open items.** Cache/refresh cadence for the Location reference
  (**MBQ-43 residual**); exact list/form composition (**MBQ-03**).
- **Must not be implemented yet.** UI blocked; `shopify.connector.location`
  exists from Task 001 as a model only — no view may be added.
- **What would make it non-premium.** Free-text location entry; auto-match
  by name; hiding the first-push status (forcing operators to discover the
  guard elsewhere).

### 8. Sync center / jobs list (S4)

- **Purpose.** One job list across all domains — inspect, filter, act.
  **[Accepted — DEC-012 §4; Part A §G; RA-013]**
- **Premium simplicity goal.** An operator lands on a pre-filtered "needs
  attention" view, not a firehose; every row answers "what, why, state,
  what can I do" without opening it.
- **Primary users.** Operator; Reviewer (review items); Auditor (read).
- **Entry points.** Menu; every dashboard count (filtered).
- **Key fields shown (row).** Domain; source (the **seven** accepted values
  — the six DEC-009 sources plus `odoo_event` with its trigger-origin
  sub-classification — **[Accepted — DEC-009; Decided — DEC-019]**); state
  (10-state vocabulary, rendered as plain words, 7-value human grouping
  allowed as presentation only — **[Accepted — Part A §G.1; Part D §4.1]**);
  error class (human label); operation reference (operation type + target +
  attempt); age; related record.
- **Filters.** Domain / source / state / error class — the four accepted
  filters, using the fixed vocabularies verbatim; saved searches,
  favourites, group-by reused Odoo-natively; default filter = "needs
  attention" (`failed_retryable` + `retry_waiting` +
  `blocked_manual_review`). **[Accepted — Part A §G.1; Part D §8]**
- **Primary actions (row, state/class-conditional).** Retry when safe;
  Verify current state (shown **before** retry for ambiguous-outcome
  jobs); Open source record; Open mapping; Cancel/supersede (from
  `draft`/`queued`/`retry_waiting`). Retry renders as exactly one of the
  four accepted cases; terminal rows carry no retry control — recovery
  from `failed_final` is an explicit re-trigger (new job). **[Accepted —
  Part A §G.3/§D.3; Part D §8]**
- **Secondary actions.** Bulk retry via multi-select — applies the same
  class-conditional logic; ineligible rows reported, never forced.
  **[Accepted — Part D §8 bulk recovery]**
- **Visual hierarchy.** State word first (colour reinforces), then reason,
  then metadata.
- **States.** *Empty:* "No jobs yet — jobs appear here when syncing starts"
  (first-run) / "Nothing needs attention" (filtered view — affirmative).
  *Loading:* live `queued`→`running` progress, honest freshness. *Success:*
  done rows with completion signal + link to what changed. *Warning:*
  `retry_waiting` rows show "the system will retry — next attempt ~…" (
  constants **MBQ-16 resolved as adjustable defaults**). *Error:* failed
  rows link to the error center. *Manual review:* rows show the specific
  sub-reason and route to S5.
- **Permissions.** Retry/cancel = Operator+; resolution of review items =
  Reviewer; Auditor read-only.
- **Open items.** `odoo_event` display label (**MBQ-22**); exact list
  composition (**MBQ-03**).
- **Must not be implemented yet.** All UI; `shopify.connector.job` exists
  model-only from Task 001.
- **What would make it non-premium.** A generic retry button on every row;
  raw state tokens in the state column; an unfiltered default view; job
  internals (idempotency key schema) rendered raw.

### 9. Job form (job detail)

- **Purpose.** The single job record: what it is, what happened, what can
  happen next. **[Design proposal — this spec]** rendering of the accepted
  job/log substrate (Part A §D; `shopify.connector.job`).
- **Premium simplicity goal.** Reads top-to-bottom as a story: header
  (what + state), body (what happened), footer (what you can do).
- **Primary users.** Operator; Reviewer; Auditor.
- **Entry points.** Sync-center row; error-center entry; smart button on
  the related Odoo record (Part D §3, accepted).
- **Key fields shown.** Header: domain, operation reference, state (plain
  word), source (+ trigger origin for `odoo_event`); Body: human-readable
  reason (if failed), suggested fix, owner state, related Odoo record,
  related Shopify reference, retry-policy explanation (one line);
  Notebook: job logs (chronological), technical detail (raw
  request/response, class code, identifiers — behind the expand), audit
  trail (attempted / written / skipped-by-rule / confirmed-by,
  before/after for destructive ops). **[Accepted — Part A §H.1–§H.9]**
- **Primary actions.** The same class-conditional retry/verify set as the
  sync-center row — identical logic, one implementation. **[Accepted —
  Part A §G.3]**
- **Secondary actions.** Cancel/supersede where state allows; assign to
  Reviewer (activities convention).
- **Validations.** n/a (read + act surface).
- **States.** *Empty:* n/a. *Loading:* running job shows honest progress.
  *Success:* succeeded job leads with the completion signal + what
  changed. *Warning:* retry-waiting explanation. *Error:* reason + fix +
  owner. *Manual review:* sub-reason + Reviewer resolution panel.
- **Permissions.** As sync center.
- **Open items.** Exact form layout (**MBQ-03**); log retention policy
  (**[Open item — this spec / implementation planning]**).
- **Must not be implemented yet.** All UI.
- **What would make it non-premium.** Stack trace above the fold; chatter
  conflated with the structured audit trail (they are distinct artifacts —
  **[Accepted — Part D §3]**); a retry button whose eligibility the
  operator must guess.

### 10. Job logs (log list / log detail)

- **Purpose.** Reason-coded, per-record, human-readable log lines
  (`shopify.connector.job.log`) — the in-app source of truth for what
  happened. **[Accepted — DEC-009; Part A §D.10]**
- **Premium simplicity goal.** A non-developer can read a log line aloud
  and it makes sense.
- **Primary users.** Operator; Auditor.
- **Entry points.** Job form notebook; sync center row expand.
- **Key fields shown.** Timestamp; human reason line; severity word;
  related record link; the technical payload behind the expand.
- **Primary actions.** None (read surface); copy-reference for support.
  **[Design proposal — this spec]**
- **States.** *Empty:* "No log entries yet." *Loading:* standard. *Others:*
  the log renders other surfaces' states; it has no failure mode of its
  own beyond load errors.
- **Permissions.** Read for all roles.
- **Must not be implemented yet.** All UI.
- **What would make it non-premium.** Logs as the *primary* operator
  experience (they are the evidence layer under the error center, not the
  recovery surface itself); untranslated developer strings.

### 11. Error center / recovery + manual-review queue (S5)

- **Purpose.** Make every failure a recovery surface, never a dead end.
  **[Accepted — DEC-012 §5; Part A §H]**
- **Premium simplicity goal.** The most stressful screen in any connector
  is this product's calmest: reason → fix → action, in that order, every
  time.
- **Primary users.** Operator (fixable/retryable); Reviewer
  (confirmation-required queue); Auditor (read).
- **Entry points.** Menu; dashboard exception cards (filtered);
  sync-center rows.
- **Key elements per entry (the accepted nine).** Human-readable reason
  (primary); expandable technical detail; suggested fix; owner/action
  state; related Odoo record; related Shopify reference; retry-policy
  explanation; specific manual-review sub-reason (one of six, never
  generic); audit trail with before/after for destructive ops.
  **[Accepted — Part A §H.1–§H.9]**
- **Order-import extensions (both required).** `financial total mismatch`
  entries render the inline per-component breakdown (Shopify total vs
  computed Odoo total: lines / tax / shipping / discount); `mapping
  missing` entries link directly into the matching flow so resolve → retry
  is two clicks. **[Accepted — DEC-014 point C (MBQ-26); Part B §C.14]**
- **Currency-divergence entries.** A blocked divergent-currency order
  (presentment ≠ shop currency) appears with its captured currency evidence
  and an unsupported-scope explanation — it is **not** offered an
  auto-create path. Exact class/sub-reason mapping: **[Open item — DEC-020
  residual]**. **[Decided — DEC-020 MBQ-64]**
- **Root-cause grouping.** Entries sharing one root cause group visually
  ("14 orders waiting on 1 unmatched product"); resolution stays per-item
  rules; grouping is presentation, never bulk auto-resolution.
  **[Accepted — Part D §9]**
- **No dead end under role gates.** An Operator viewing a Reviewer-owned
  item sees whose action it awaits + a route/assign affordance
  (activities). **[Accepted — Part D §9]**
- **Primary actions.** Per entry: the suggested fix's action (e.g. "Match
  this product"), or Retry when safe, or Verify current state.
- **Secondary actions.** Assign; open records; expand technical detail.
- **Visual hierarchy.** Reason sentence → fix → owner chip → actions →
  everything else.
- **States.** *Empty:* affirmative — "No open errors. Everything that ran
  recently succeeded." *Loading:* verify-in-progress on an item. *Success:*
  item resolved with audit trail retained. *Warning:* retry-waiting
  ("system will retry") entries visually distinct from operator-owned
  ones. *Error:* the entries themselves. *Manual review:* the
  sub-reason-keyed Reviewer queue.
- **Permissions.** Resolve confirmation-required = Reviewer; fix-and-retry
  = Operator; read = all.
- **Open items.** Exact reason/fix copy per class (**MBQ-22**);
  stale-binding review detail (**MBQ-13, descoped**).
- **Must not be implemented yet.** All UI.
- **What would make it non-premium.** A raw error table sorted by
  timestamp; the same "Needs review" badge on every kind of block;
  technical detail visible by default; any dead-end entry.

### 12. Manual retry / recover flow

- **Purpose.** The act of recovering a failed/blocked item, end to end.
  **[Accepted — DEC-009 retry taxonomy; DEC-012 §4/§5]**
- **Premium simplicity goal.** The operator never has to decide whether a
  retry is safe — the system already decided, and explains itself.
- **Flow (accepted logic, rendered).** Four cases, exactly: (a) auto-retry
  in progress → no button, "next attempt ~…"; (b) safe to retry now →
  Retry button with the reason it's safe; (c) fix required first → the fix
  action is primary, Retry appears only after the fix; (d) ambiguous
  outcome → **Verify current state** is the only first action; after
  verification: "already applied" → mark resolved, "not applied" → Retry
  unlocks, inconclusive → manual review. **[Accepted — Part A §D.5; Part D
  §4.1; RA-014/RA-015]**
- **Bulk recovery.** Multi-select applies the same per-item logic;
  ineligible items are reported with reasons.
- **States.** Follow the host surface (S4/S5).
- **Audit.** Every retry/verify/resolve records who/when/outcome.
  **[Accepted — DEC-009]**
- **Must not be implemented yet.** All of it.
- **What would make it non-premium.** A "Force retry" escape hatch that
  bypasses classification (structurally prohibited — no flag bypasses a
  guard, Part A §I.5); retry buttons that silently no-op.

### 13. Matching / duplicate-prevention center (S6)

- **Purpose.** Resolve unmatched/ambiguous/duplicate-risk records with a
  preview before any create/bind. **[Accepted — DEC-006; DEC-012 §6;
  Part B §A.9/§B.9]**
- **Premium simplicity goal.** Matching feels like confirming, not
  detective work: the system presents its evidence (which key matched,
  what it found), and the operator confirms or corrects.
- **Primary users.** Operator (products/variants); Reviewer (customer
  ambiguity/duplicates).
- **Entry points.** Product/customer flows; error-center `mapping missing`
  / `ambiguous match` entries (two-click resolve → retry).
- **Key elements.** Three visually distinct states — Unmatched, Ambiguous,
  Duplicate risk — never folded into one "needs attention"; candidate list
  showing the match key that produced each candidate; binding status +
  audit fields (matched-by/at, source strategy, key used); the blocking
  preview "will create N, link M, N ambiguous" before commit.
  **[Accepted — DEC-006; Part D §11]**
- **Match-key order (fixed).** Products: binding → SKU/internal reference →
  barcode → manual. Customers: binding → email (sole automatic key) →
  manual. Name is advisory only, shown as a hint, never auto-binds.
  **[Accepted — DEC-006; DEC-014 point E (MBQ-31); RA-006]**
- **Primary actions.** Confirm match; Create (subject to domain guard);
  Send to manual review.
- **Secondary actions.** Skip with reason; open both records side-by-side.
- **States.** *Empty:* "Nothing to match — new items appear here when a
  sync can't match confidently." *Loading:* candidate search. *Success:*
  preview confirmed → bindings created, audit recorded. *Warning:*
  duplicate-risk highlighted before commit. *Error:* unresolved →
  skip/manual review. *Manual review:* ambiguous/duplicate queue for the
  Reviewer.
- **Permissions.** Product matching = Operator+; customer
  ambiguity/duplicate confirmation = Reviewer.
- **Open items.** Domain binding model names (**MBQ-55, descoped**);
  stale/recreated binding review detail (**MBQ-13, descoped**).
- **Must not be implemented yet.** All UI.
- **What would make it non-premium.** Auto-selecting the top candidate; a
  match list without the "why" (key) column; hiding the preview behind a
  setting.

### 14. Product import screen (product flow + preview/diff, S7)

- **Purpose.** Bring catalogs into agreement safely: import from Shopify,
  controlled export/update to Shopify, always via preview.
  **[Accepted — DEC-003; DEC-007 §1–§3; Part B §A]**
- **Premium simplicity goal.** The operator always sees "what will happen
  to what" before it happens — the preview is the product screen's centre
  of gravity, not an interstitial.
- **Primary users.** Operator.
- **Entry points.** Catalog & Matching menu; smart buttons on products;
  error-center links.
- **Key elements.** Import run entry (source strategy visible); the
  **five-state preview** — To create / To update (diff rendered: fields,
  images, price, variants) / To skip (reason shown, never guessed) /
  Blocked (destructive-write guard or price source-of-truth unset) /
  Draft-pending-publish; the destructive-write diff highlighting what a
  full-state write would **delete by omission**; draft-first export with
  explicit, channel-selecting publish. **[Accepted — Part B
  §A.10/§A.11/§A.16; DEC-012 §7; Part D §12]**
- **Primary actions.** Preview; Confirm (per the preview); Publish
  (explicit, channel-selecting; never automatic).
- **Secondary actions.** Skip item; send to matching; export preview
  dry-run (`export_preview_dry_run`, allowed during setup, read-only).
- **Validations.** Price export blocks until price source-of-truth is
  recorded (**[Accepted — DEC-007 §3]**); automated (webhook/scheduled/
  reconciliation) imports use the accepted pre-create gate + duplicate
  check, never a blocking human preview per record, and their
  retrospective visibility is audit-only (**[Accepted — DEC-014 point H
  (MBQ-59)]**); product webhooks are enqueue-only triggers with a
  follow-up authoritative read; `PRODUCTS_DELETE` never **directly**
  deletes/archives the bound Odoo product (**[Decided — DEC-020 MBQ-65]**;
  exact post-read handling of a confirmed deletion remains implementation
  mechanics).
- **States.** *Empty:* "No products staged — start an import or export
  preview." *Loading:* diff computing with honest progress. *Success:*
  written + binding confirmed + draft-pending-publish clearly flagged.
  *Warning:* skips present — count + reasons visible. *Error:* Shopify
  validation errors rendered plainly. *Manual review:* ambiguous items
  routed to S6.
- **Permissions.** Run/confirm = Operator; destructive-write confirmation
  = per guard rules (Reviewer where classified confirmation-required).
- **Open items.** Variant mutation strategy (**MBQ-23 residual**); media
  delete-on-omit (**MBQ-24 residual**); channel-selection UX for publish
  (**MBQ-25 residual**).
- **Must not be implemented yet.** All UI and all product domain logic
  (domain gate not open).
- **What would make it non-premium.** A diff that shows raw field names
  without human labels; burying the delete-on-omission warning; publish as
  a side effect of export.

### 15. Customer import/matching screen (S8)

- **Purpose.** Import and match customers safely; never invent or expose
  PII beyond need. **[Accepted — DEC-006; Part B §B]**
- **Premium simplicity goal.** Reviewer decisions are one-glance: the
  candidate evidence (email match, existing binding) is presented as a
  clean comparison, not a data dump.
- **Primary users.** Reviewer (ambiguity/duplicates); Operator (routine
  imports).
- **Entry points.** Catalog & Matching menu; error-center
  ambiguous/duplicate entries; partner smart buttons.
- **Layout / visual hierarchy.** Review list → one evidence card per item
  (Shopify record vs candidate side by side, match key highlighted) →
  decision actions; the evidence card is the visual centre.
  **[Design proposal — this spec]**
- **Validations.** No auto-bind on phone/name; a create routes through the
  duplicate check; fallback assignment only on genuine no-PII orders.
- **Key elements.** Match evidence (binding → email; phone/name advisory
  hints only); the clearly-flagged no-PII fallback partner (visible
  auditable marker — never indistinguishable from a real customer; used
  only when Shopify genuinely withholds PII, never for match failures).
  **[Accepted — Part B §B.3/§B.7/§B.13; DEC-014 points D/E]**
- **Primary actions.** Confirm match; Create new; Send to review.
- **States.** *Empty:* "No customers waiting for review." *Loading:*
  candidate lookup. *Success:* matched/bound with audit. *Warning:*
  fallback-partner usage surfaced. *Error:* data-shape issues →
  fix-then-retry. *Manual review:* ambiguous/duplicate → Reviewer.
- **Permissions.** Confirmation = Reviewer; imports = Operator.
- **Open items.** Fallback partner exact naming (**MBQ-29 Resolved via
  AR-020 — single flagged fallback partner per store; per-order anonymous
  identity explicitly non-MVP; only the partner naming remains task-spec
  detail**). PII-display minimization (show match evidence, not full
  profiles) is a **[Design proposal — this spec]** discipline under the
  accepted conservative protected-data posture — note MBQ-09's own open
  residual is compliance-webhook-scoped and does not govern screen
  display.
- **Must not be implemented yet.** All UI and customer domain logic.
- **What would make it non-premium.** Showing full customer PII in list
  views where the match evidence (email) suffices; a fallback partner that
  looks like a real customer.

### 16. Order import/review touchpoints (S9 — no dedicated screen)

- **Purpose.** Order-import operator work happens in the shared sync
  center and error center — **there is no dedicated order-import screen,
  and this spec does not create one.** **[Accepted — DEC-014 point C
  (MBQ-26)]**
- **Premium simplicity goal.** Order problems are rare, specific, and
  fully explained where they surface: the two accepted error-center
  extensions (financial-evidence breakdown; direct matching links) carry
  the whole flow.
- **Key elements.** Whole-order hold on unmatched product = `mapping
  missing` → fix-then-retry (never confirmation-review); total mismatch =
  `financial total mismatch` with the inline breakdown ("conservative,
  never silent" posture); three-path customer resolution; order edits/
  cancellations/refunds are evidence-refresh only — no screen ever offers
  to re-apply Shopify order edits to the Odoo sale order. **[Accepted —
  Part B §C.5/§C.8/§C.12; DEC-014 points I/J]**
- **Divergent currency.** Blocked before SO creation, routed to manual
  review / unsupported-scope handling with currency evidence captured.
  **[Decided — DEC-020 MBQ-64]**
- **Permissions.** As S4/S5.
- **Open items.** Total-check tolerance + exact Shopify total field
  (**MBQ-56, descoped**); tax-representation mechanism (**MBQ-27,
  descoped**).
- **Must not be implemented yet.** All of it.
- **What would make it non-premium.** Building the dedicated order screen
  anyway (contradicts an accepted decision); rendering the financial
  breakdown as a raw JSON blob.

### 17. Inventory sync screen (S11 first-push + S12 settings + ongoing review)

- **Purpose.** Guard the first push, make the recorded source-of-truth
  and the decided quantity definition visible, and run ongoing
  review-then-apply writes. **[Accepted — DEC-010; Part C §A; Decided —
  DEC-018 MBQ-33/34]**
- **Premium simplicity goal.** The most dangerous operation in the product
  (writing live storefront stock) feels like a careful, reviewable,
  reversible-feeling ritual — a preview the operator reads, understands,
  and signs.
- **Primary users.** Operator (staging/applying); Reviewer (guard
  confirmations); Admin (settings); Auditor (read).
- **Entry points.** Inventory → First-Push & Sync; dashboard
  first-push-pending and inventory-exception cards; wizard step 10
  scheduling; error-center inventory entries.
- **Layout / visual hierarchy.** Preview table (SKU / variant / location /
  quantity) is the dominant region; the confirm action sits **below** the
  preview, never above it; settings live in S12, not on the review
  surface. **[Design proposal — this spec]**
- **Validations.** No write without a mapped pair; no confirm without the
  preview rendered; ambiguous rows must be skipped/matched before confirm.
- **Key elements.**
  - **First-push guard (S11):** preview of SKU/variant/location/quantity
    rows to be written; explicit confirmation; recorded source-of-truth;
    skip/manual-match for ambiguous rows; fires per (store + mapped
    location pair + product/variant binding) — batched review UI is
    permitted, each unit individually recorded. Confirmation persists as a
    record (snapshot, confirmer, timestamp, scope). **[Accepted — DEC-007
    §4; Part C §A.5; Decided — DEC-018 MBQ-33; MBQ-38 partially resolved]**
  - **Quantity settings (S12):** `available` is the **sole** Phase 1
    write target; `committed` never appears anywhere as an option
    (structural exclusion); **`on_hand` is not exposed as a Phase 1 UI
    choice at all** — MBQ-35 was resolved by conservative exclusion
    (AR-020, 2026-07-05); future exposure requires explicit justification
    via the architecture-review log, so the screen contains no `on_hand`
    option and no dormant toggle for it; the Odoo quantity definition is
    likewise **decided, not chosen on screen** — Phase 1 uses `free_qty`
    semantics per mapped location (MBQ-32 residual closed via AR-020 as
    the conservative default), so S12 renders **no quantity-source choice
    UI**; it may state the definition in plain language ("we send the
    free-to-use quantity"), nothing more.
    **[Accepted — DEC-010; RA-018; Part C §A.4; Decided — MBQ-35 and the
    MBQ-32 residual resolved via AR-020]**
  - **Ongoing writes:** review-then-apply is the Phase 1 default —
    each apply shows the same preview shape as the first push; auto-apply
    does not exist in Phase 1 UI (future flag, separately decided).
    **[Decided — DEC-018 MBQ-34]**
  - **Drift/reconciliation:** "last synced / last reconciled / drift
    found" is first-class; a quantity mismatch is a distinct exception,
    never auto-resolved. **[Accepted — DEC-010; RA-020/RA-021]**
- **Primary actions.** Review & confirm first push; Review & apply
  (ongoing); Reconcile now.
- **Secondary actions.** Skip/manual-match row; open binding; open
  location mapping.
- **States.** *Empty:* "No first push pending" / "Nothing to apply."
  *Loading:* preview building with row counts. *Success:* confirmed →
  enqueued; confirmation record written and linkable. *Warning:* drift
  found — count + review link. *Error:* unmapped/ambiguous rows surfaced
  with fixes. *Manual review:* guard-blocked items until confirmed.
- **Permissions.** Confirmations = per guard classification (Reviewer for
  confirmation-required classes; Admin for settings); apply = Operator
  where safe.
- **Open items.** Quantity-**read mechanics** — how the decided `free_qty`
  semantics are read/aggregated, including the required
  expired-unreserved-divergence acceptance test if quant-based aggregation
  is used (**MBQ-32 — decided; mechanics are inventory task-spec
  detail**); confirmation-record schema (**MBQ-38 residual**); batched
  review UI composition (**[Open item — this spec / implementation
  planning]**).
- **Must not be implemented yet.** All UI and inventory domain logic.
- **What would make it non-premium.** A confirm button above the fold with
  the preview below it; quantity semantics presented as equal radio
  options; any path where "apply" happens without the preview.

### 18. Fulfillment / tracking screen (S13)

- **Purpose.** Surface fulfillment work through the shared job/log
  surfaces plus a small notification-settings sub-surface — no parallel
  fulfillment monitor. **[Accepted — Part C §B; DEC-011; RA-013]**
- **Premium simplicity goal.** A fulfillment entry reads as one matched
  sentence: *this picking* fulfilled *these lines* of *that order* at
  *this location*, tracking *X*, customer notified: *no*.
- **Primary users.** Operator (retry/verify); Reviewer (mismatch and
  notification confirmations); Admin (notification default); Auditor
  (read).
- **Entry points.** Fulfillment menu (filtered S4/S5 views); dashboard
  fulfillment-exception card; smart button on the picking/sale order;
  Store Settings notification sub-surface.
- **Layout / visual hierarchy.** The matched-unit sentence leads each
  entry; tracking and the notification decision sit directly under it;
  everything else (IDs, references) is secondary. **[Design proposal —
  this spec]**
- **Validations.** Only a validated picking triggers anything; no
  fulfillment without the full order/FulfillmentOrder/line/quantity/
  location match; notification decision fixed at enqueue.
- **Key elements.** The matched unit shown together (order /
  FulfillmentOrder / lines / quantities / location); tracking write-back
  fields (from `stock_delivery` — dependency required; absent module ⇒
  tracking write-back disabled and readiness-blocked, never silently
  degraded — **[Decided — DEC-018 MBQ-60]**); tracking-only updates
  visibly distinct from fulfillment creation; notification setting
  (requested/suppressed) recorded on every entry, default off, persisted
  per job at enqueue (**[Accepted — DEC-007 §5; DEC-011; RA-009; Decided —
  DEC-018 MBQ-41]**); location-mismatch review via the widened `ambiguous
  match` class (**[Accepted — Part C §B.8 / DEC-015 point J]**).
- **Primary actions.** Verify current state (ambiguous outcomes); Retry
  when safe; resolve location-mismatch (Reviewer).
- **Secondary actions.** Open picking / order / FulfillmentOrder
  reference.
- **States.** *Empty:* "No fulfillments yet — validated deliveries appear
  here." *Loading:* create/tracking in progress. *Success:* created +
  tracking + notification decision recorded. *Warning:* backorder-split
  pickings flagged as their own events. *Error:* unmatched picking with
  reason + fix. *Manual review:* block-if-ambiguous, location mismatch,
  notification-confirmation-missing.
- **Permissions.** Notification default change = Admin;
  confirmation-required = Reviewer; retries = Operator.
- **Open items.** FulfillmentOrder hold/lifecycle webhook handling
  (**MBQ-61, descoped**) — the screen must not pretend hold-awareness it
  doesn't have; backorder wizard copy nuance (**MBQ-40 residual**).
- **Must not be implemented yet.** All UI and fulfillment domain logic.
- **What would make it non-premium.** A separate fulfillment dashboard;
  notification state hidden in a sub-tab (it is the safety-critical fact
  and stays on the entry); unexplained "held" states.

### 19. Audit / history screen

- **Purpose.** Answer "who did what, when, and what changed" across
  connector activity — for Auditors, reviews, and support. **MVP: this is
  a filtered rendering of already-accepted artifacts** (job/log audit
  detail, binding audit fields, guard confirmation records, chatter/
  activity history) — **not a new data surface**. **[Design proposal —
  this spec]**
- **Premium simplicity goal.** An Auditor can reconstruct any incident
  without asking an engineer.
- **Primary users.** Auditor; Admin.
- **Entry points.** Sync center/error center filters; binding records;
  guard confirmation records.
- **Key elements (MVP).** Saved audit-oriented filters over S4/S5 (e.g.
  "all destructive confirmations", "all manual matches", "all notification
  decisions"); each hit shows the accepted audit fields (attempted /
  written / skipped-by-rule / confirmed-by, before/after).
  **[Accepted substrate — DEC-009; Part A §D.10/§C.4]**
- **Later (premium candidate).** A dedicated, read-only **audit timeline**
  view (one chronological stream across jobs/bindings/guards) — see
  Premium UX opportunities; **not MVP**, requires its own review.
- **States.** *Empty:* "No audit events match this filter." Others follow
  the host surfaces.
- **Permissions.** Read-only for all; exists chiefly for Auditor.
- **Must not be implemented yet.** All of it.
- **What would make it non-premium.** Inventing a separate audit store
  (duplicating the accepted substrate); mixing editable surfaces into the
  audit view.

### 20. Permissions / admin settings screen (S14)

- **Purpose.** Make the four roles and their capabilities legible —
  read-only, plain language. **[Accepted — DEC-012 §10; Part A §J;
  Decided — DEC-018 MBQ-45]**
- **Premium simplicity goal.** A manager can decide "which group does my
  colleague need?" from this page alone.
- **Primary users.** All four roles (read-only); practically consulted by
  Admins assigning access.
- **Entry points.** Configuration → Roles & Access.
- **Layout / visual hierarchy.** One capability matrix (roles × four
  plain-language capability columns), one hierarchy note beneath, one
  link for Admins — nothing else. **[Design proposal — this spec]**
- **Validations.** None (informational, read-only).
- **Key elements.** The four roles as a capability matrix in plain
  language (view / run & retry / approve reviews / configure), with
  internal state names only as parentheticals; a note that Admin implies
  Operator + Reviewer; assignment happens through standard Odoo user
  settings (groups map 1:1 — accepted planning names shown as directions).
- **Primary actions.** None (informational); link to Odoo Users & Groups
  for Admins. **[Design proposal — this spec]**
- **States.** Static informational surface; no state model beyond load.
- **Permissions.** Visible to all roles.
- **Open items.** Exact `ir.model.access` rows / record rules (**MBQ-44
  residual**).
- **Must not be implemented yet.** All of it — and no CSV/group files may
  be created.
- **What would make it non-premium.** Rendering a raw groups/ACL table;
  making this page editable (it explains; Odoo's own user admin edits).

---

## Setup wizard detailed flow

The accepted step set is the **11-step Part A §E.1 / DEC-012 §1 wizard**
(**[Accepted]**). The task brief's nine phases map onto those 11 accepted
steps as follows — this spec **groups**, but does not add, remove, or
reorder, accepted steps. Grouping is **[Design proposal — this spec]**.

| Brief phase | Accepted step(s) |
| --- | --- |
| Welcome / prerequisites | 1 |
| Store identity | 2 |
| Credential entry | 3 (+ 4 scope presentation) |
| Test connection | 5 |
| Scope/readiness check | 6 |
| Location baseline | 10 (first-push **scheduling only**) + S10 link |
| Domain feature flags | 7 (directions per domain) |
| First sync choice | 8 (source of truth) + 9 (notification default) |
| Review and activate | 11 |

Wizard-wide premium treatment **[Design proposal — this spec]**: one
decision per screen; a visible step indicator with plain step names; each
step closes on an explicit "verified"/"saved" moment (accepted confidence
loop); Back never loses entered data; exit at any point lands in the
explicit `setup_incomplete` state listing exactly which steps remain
(**[Accepted — DEC-012 §1 item 11]**).

### Step 1 — Welcome / prerequisites

- **User goal.** Understand what this flow will do and whether their
  hosting qualifies.
- **Fields/actions.** None to fill; a short "what you'll need" list (your
  Shopify admin access; ~10 minutes); the honest hosting disclosure
  (Odoo.sh/on-prem required; Odoo Online excluded) up front, not
  discovered mid-wizard. **[Accepted — DEC-005; DEC-012 §1 item 1]**
- **Helper text.** One paragraph: what the wizard sets up, what it will
  *not* do without asking (no sync until you finish; nothing writes
  without a preview).
- **Premium treatment.** Sets the emotional contract: "nothing happens
  without your say-so."
- **Validation/errors.** None.
- **Next best action.** "Start" → store identity.
- **MVP:** all. **Deferred:** none.

### Step 2 — Store identity

- **User goal.** Name the store and point at the right shop.
- **Fields/actions.** Store name (friendly label); shop domain.
- **Helper text.** Where to find the myshopify domain; single store in
  Phase 1 (multi-store later — honest note). **[Accepted — DEC-003]**
- **Premium treatment.** Two fields, one sentence each — the easiest step
  first builds momentum.
- **Validation/errors.** Domain shape sanity; identity is *confirmed* at
  readiness (store identity check — DEC-018 MBQ-06), not asserted here.
- **Next best action.** Continue → credentials.
- **MVP:** all. **Deferred:** multi-store.

### Step 3 — Credential entry

As specified in screen 5 above. **User goal:** hand over the token once,
safely. **MVP:** the accepted posture (masked entry, no read-back, no
encryption claims). **Deferred:** rotation/expiry UX (**MBQ-04
implementation-planning task**); OAuth-style connect (not the accepted
DEC-004 model).

### Step 4 — Scope presentation

- **User goal.** See which permissions the connector needs and why.
- **Fields/actions.** A read-only list of required scopes, each with a
  one-line business reason ("read_products — so we can import your
  catalog"); never a pasteable free-text scope string. **[Accepted —
  DEC-012 §1; ux-operator-flow.md §1 item 3]**
- **Helper text.** The operator grants scopes in Shopify when creating the
  custom app; the wizard verifies them at readiness (it does not grant).
- **Premium treatment.** Scopes-as-reasons converts the most jargon-heavy
  moment into a trust moment.
- **Validation/errors.** None here; verification happens in steps 5–6.
- **Next best action.** Continue → Test connection.
- **MVP:** presentation + readiness verification. **Deferred:** exact
  scope-grant walkthrough content (**MBQ-05, descoped**).

### Step 5 — Test connection

As specified in screen 6 above. **User goal:** prove the credential works
*now*. Explicit pass/fail with a reason; failure keeps the operator on the
step with a fix, never a raw HTTP code. **MVP:** all. **Deferred:** none.

### Step 6 — Readiness checks

As specified in screen 6 above (the decided essential-vs-warning split —
**[Decided — DEC-018 MBQ-06]**). **User goal:** know, before first sync,
that everything known-to-fail has been checked. **MVP:** the decided
essential set blocking; warnings carried to the dashboard. **Deferred:**
exact thresholds/copy (task-spec detail).

### Step 7 — Sync direction per domain

- **User goal.** Choose what this connector does, per domain.
- **Fields/actions.** For each domain: enable + direction choice limited
  strictly to DEC-003-supported directions (product import + controlled
  export/update; order import only; inventory import-baseline +
  Odoo→Shopify write-back; fulfillment write-back only). Unsupported
  directions are absent, not disabled. **[Accepted — DEC-003; DEC-012 §1
  item 6]**
- **Helper text.** One sentence per domain stating what will and won't
  happen.
- **Premium treatment.** Enabling a domain shows a quiet note of what
  guard still stands between enablement and the first write (e.g.
  inventory → first-push guard pending).
- **Validation/errors.** No domain enabled silently; skipping all domains
  is allowed (connect-only setup).
- **Next best action.** Continue → source of truth.
- **MVP:** all. **Deferred:** none.

### Step 8 — Source-of-truth choices

- **User goal.** Record which system wins, for matching and for price.
- **Fields/actions.** Product-matching source strategy; price authority.
  **Both required — no default is pre-selected**; the wizard requires an
  explicit selection before "ready". **[Accepted — DEC-006/DEC-007 §3;
  DEC-012 §1 item 7]**
- **Helper text.** Each option described by consequence ("Odoo is the
  price authority: price changes here overwrite Shopify prices on
  export").
- **Premium treatment.** The one genuinely strategic decision gets the
  most careful copy in the product; a "not sure?" expander explains in
  merchant language.
- **Validation/errors.** Unset choice blocks price export later (screen
  14) — stated here so the block is never a surprise.
- **Next best action.** Continue → notification default.
- **MVP:** all. **Deferred:** none.

### Step 9 — Notification default

- **User goal.** Decide whether Shopify tells customers about
  fulfillments.
- **Fields/actions.** One choice, default **off**, never pre-checked on;
  explicit opt-in with a consequence sentence ("Shopify will email your
  customers when a delivery is fulfilled"). **[Accepted — DEC-007 §5;
  RA-009; Decided — DEC-018 MBQ-41 (global/per-store granularity)]**
- **Helper text.** One sentence stating the default plainly ("Right now,
  customers will not be emailed — you can change this anytime in Store
  Settings").
- **Premium treatment.** The safest default plus the clearest consequence
  — this is where "safe by default" is most visible to a merchant.
- **Validation/errors.** None — the default is always valid; opting in
  requires the explicit consequence-stating confirmation.
- **Next best action.** Continue → first-push scheduling.
- **MVP:** global/per-store default. **Deferred:** per-order override
  (explicitly deferred by DEC-018 unless standard Odoo already exposes
  one).

### Step 10 — Inventory first-push scheduling

- **User goal.** Decide *when* to do the first-push review — without ever
  skipping it.
- **Fields/actions.** Schedule now / do it later. The wizard **only
  schedules**; the guard itself (preview + confirm + record) always runs
  in S11 at the decided granularity. It is never silently completed.
  **[Accepted — DEC-012 §1 item 9; Part D §5 step 10; Decided — DEC-018
  MBQ-33]**
- **Helper text.** One sentence: "Nothing is written to Shopify until you
  review and confirm the stock preview — this step only picks when."
- **Premium treatment.** "Later" is a first-class, guilt-free choice; the
  dashboard first-push card keeps it visible without nagging.
- **Validation/errors.** Requires inventory domain enabled; with
  inventory disabled the step states that and passes through.
- **Next best action.** Continue → review and activate.
- **MVP:** all. **Deferred:** none.

### Step 11 — Review and activate (final readiness summary)

- **User goal.** Confirm, in plain words, what the connector will now do.
- **Fields/actions.** The confidence statement: connection status; enabled
  domains + directions; source-of-truth choices; notification default;
  first-push pending or scheduled; readiness result. One primary action:
  Activate. **[Accepted — DEC-012 §1 item 10; Part D §5 confidence
  statement]**
- **Helper text.** "You can change any of this later in Store Settings."
- **Premium treatment.** The summary is written in the operator's words —
  a paragraph a merchant could read aloud to their boss — not a pass/fail
  grid alone.
- **Validation/errors.** Activation blocked while any essential readiness
  check fails; the blocking items are listed with fix links.
- **Next best action.** Activate → Dashboard (which then guides the first
  sync).
- **MVP:** all. **Deferred:** none.

---

## Dashboard / command center design

**[Accepted — Part A §F.1; DEC-012 §3; Part D §7]** with layout refinements
marked **[Design proposal — this spec]**.

### Structure (top to bottom)

1. **Lead answer band.** One plain-language sentence answering "Is
   everything OK?" — "All systems normal" or "3 items need your attention"
   — positioned above everything else. Text always; colour reinforces.
   **[Accepted — Part D §7 lead region]**
2. **The nine accepted cards** (no tenth card; no chart in MVP):
   connection health; last successful sync per domain (state, not bare
   timestamp — overdue surfaces as an exception); failed jobs by severity
   (needs review / auto-retrying / permanently failed — never one number);
   manual-review count (by sub-reason); retry-waiting count;
   first-push-pending count; inventory exceptions; fulfillment exceptions;
   duplicate/matching exceptions. **[Accepted — Part A §F.1]**
3. **Recent activity timeline + quick actions + reconciliation status**
   ("last synced / last reconciled"). Quick actions enqueue work, never
   run inline. **[Accepted — Part D §7 fused elements]**
   **Next sync:** conveyed here as the plain-language cadence statement
   ("checked every N hours per domain" — the DEC-018 MBQ-17 configurable
   posture), **not** as a new card — the accepted nine-card set is fixed,
   so a dedicated next-sync card would require its own future decision.
   **[Design proposal — this spec]**

### Card anatomy **[Design proposal — this spec]**

Every card renders: a plain-word title; the number or state; a one-line
qualifier ("2 waiting on you, 3 retrying"); and is clickable → the
filtered S4/S5 view. A zero state reads affirmatively ("0 — all clear"),
never a bare number. No card renders a raw token, a timestamp without
context, or a metric with no action.

### Dashboard rules (binding for implementation review)

- Do not overload: nine cards, one lead band, one timeline — nothing else
  in MVP. Any additional card requires a new accepted decision.
- No raw technical logs on the dashboard — the timeline shows
  human-readable activity lines, and detail lives in S4/S5.
- High-signal only: every element informs, reassures, or guides action —
  the accepted no-vanity-metrics rule. **[Accepted — DEC-012 §3 item 11]**
- **Useful in 10 seconds:** a first-time viewer answers "is anything
  wrong, where do I click" in one screenful. **[Design proposal — this
  spec]**
- Honest freshness everywhere: mechanism named (webhook / scheduled /
  manual / reconciliation), no "real-time" claims. **[Accepted — DEC-005;
  Part D §17 rule 4]**
- The deferred "Daily Queue Activity" chart idea stays deferred — a later
  premium candidate, not MVP. **[Accepted — DEC-016 point G]**

### Dashboard states

*Empty/first-run:* a guided empty state — "Connect your store to begin",
or post-setup "Your first sync hasn't run yet — start with a product
import preview" — always one concrete next action. *Loading:* counts
refresh with last-updated stamps; never a fake instant. *Success:* the
named healthy state. *Warning:* overdue-sync and API-throttled states
surface as exception cards with explanations. *Error:* failure cards route
filtered. *Manual review:* the review card routes to the Reviewer queue.

---

## Error and recovery UX

All error presentation follows the accepted nine-element error-center
contract (Part A §H) and the 16-class registry (fixed; no 17th class).
Titles below are **[Illustrative copy — MBQ-22 open]**; classes/routing are
**[Accepted]**. "Hidden by default" = inside the technical-detail expand.
Escalation path uses the accepted assignment convention (activities →
Reviewer/Admin).

For each type: **plain-language title · business explanation · recommended
action · primary action · secondary action · hidden detail · expandable
detail · audit/log behaviour · escalation.**

1. **Retryable error** (Shopify temporary/server/network — class 2).
   *Title:* "Shopify didn't respond — we'll retry automatically." *Explain:*
   a temporary hiccup on Shopify's side; nothing was lost. *Recommended:*
   nothing — the system owns it. *Primary:* none (auto-retry in progress —
   retry case (a): **no retry button**; next attempt shown). *Secondary:*
   none — a manual Retry appears only if the job later reclassifies to
   retry case (b) (e.g. after exhaustion-then-fix). *Hidden:* HTTP status,
   response body. *Expandable:* attempt history. *Audit:* each attempt
   logged with outcome. *Escalation:* auto-escalates to `failed_final` +
   error center after retry exhaustion.
2. **Manual-review block** (one of the six sub-reasons). *Title:* the
   specific sub-reason, humanised — e.g. "Two possible matches for this
   product — pick the right one." *Explain:* the system found a state only
   a person should decide. *Recommended:* review the evidence and decide.
   *Primary:* Review & resolve (Reviewer). *Secondary:* Assign to someone.
   *Hidden:* match-scoring internals. *Expandable:* candidate details.
   *Audit:* resolution recorded with who/when/choice. *Escalation:* Operator
   → Reviewer via assign; ages onto the dashboard review card.
3. **Financial mismatch** (class 13). *Title:* "This order's totals don't
   add up yet." *Explain:* Shopify's total and the computed Odoo total
   disagree; the order is held so your books stay right. *Recommended:*
   review the inline breakdown (lines / tax / shipping / discount).
   *Primary:* Review breakdown. *Secondary:* Retry after fix. *Hidden:*
   raw money payloads. *Expandable:* per-component comparison (the accepted
   inline breakdown). *Audit:* evidence captured on the order's financial
   record. *Escalation:* finance-facing — Auditor/P3 visibility;
   "conservative, never silent." **[Accepted — Part B §C.8; DEC-014 point I]**
4. **Mapping missing** (class 6 → fix-then-retry, never review-queue).
   *Title:* "A product on this order isn't matched yet." *Explain:* the
   whole order waits until its lines are matched (so nothing partial is
   created). *Recommended:* match the product. *Primary:* Match now (two
   clicks into S6). *Secondary:* Skip/retry after fix. *Hidden:* the raw
   line payload and lookup keys. *Expandable:* the unmatched line(s) and
   what was searched. *Audit:* hold + resolution logged. *Escalation:*
   volume grouping ("14 orders waiting on 1 product") surfaces systemic
   mapping gaps. **[Accepted — Part B §C.5; DEC-014 point I]**
5. **Auth failure** (class 3). *Title:* "Shopify no longer accepts this
   store's credentials." *Explain:* the token was revoked/expired; sync is
   paused; nothing else broke. *Recommended:* reconnect. *Primary:*
   Reconnect (Admin). *Secondary:* View what's paused. *Hidden:* auth
   headers/response. *Audit:* pause + reconnect + readiness re-run all
   logged. *Escalation:* Operator sees it, Admin owns it — the entry names
   that explicitly.
6. **Rate limit** (class 1). *Title:* "Shopify is asking us to slow down."
   *Explain:* normal on large catalogs; work is queued and paced; nothing
   fails. *Recommended:* nothing. *Primary:* none. *Secondary:* view queue.
   *Hidden:* cost/throttle numbers. *Audit:* throttle events logged.
   *Escalation:* persistent throttling surfaces on API health as
   "Throttled" with explanation — an honesty feature no surveyed
   competitor describes or demonstrates
   (**[Accepted evidence — gaps-opportunities O-REL-2]**).
7. **Webhook/reconciliation drift.** *Title:* "We found N differences
   during a routine check." *Explain:* Shopify events can be missed; the
   scheduled check exists exactly for this; here's what differs.
   *Recommended:* review the differences. *Primary:* Review drift list.
   *Secondary:* Reconcile again. *Hidden:* raw comparison payloads.
   *Expandable:* per-item before/after values. *Audit:* drift report
   retained. *Escalation:* repeated drift on one domain is a named warning
   on the dashboard. Never auto-applied (per-class routing applies to each
   item). **[Accepted — DEC-005; DEC-010]**
8. **Duplicate-prevention warning** (class 9, confirmation-required).
   *Title:* "Creating this might duplicate something you already have."
   *Explain:* a close existing record was found; creating anyway needs a
   person's OK. *Recommended:* compare the candidates before anything is
   created. *Primary:* Review candidates (Reviewer). *Secondary:* Confirm
   create / Match to existing. *Hidden:* similarity scoring internals.
   *Expandable:* the candidate records and the key that flagged them.
   *Audit:* decision + who/when. *Escalation:* Reviewer queue.
9. **Disconnected store.** *Title:* "This store is disconnected." *Explain:*
   credentials removed, sync stopped; **your history, matches, and logs
   are all kept** (decided retention posture). *Recommended:* reconnect
   when ready — nothing degrades while disconnected. *Primary:* Reconnect
   (re-runs readiness). *Secondary:* view retained history. *Hidden:*
   nothing technical is needed here (a deliberate state, not a fault).
   *Expandable:* the disconnect audit entry (who/when). *Audit:*
   disconnect + reconnect audited. *Escalation:* Admin-owned; the entry
   names that (Operators see the state, cannot reconnect). **[Decided —
   DEC-018 MBQ-08]**
10. **Failed test connection** (wizard). *Title:* "We couldn't reach your
    store." *Explain:* named cause (bad domain / invalid credential /
    network) + fix. *Recommended:* fix the named cause, then re-test — the
    wizard keeps everything entered. *Primary:* Fix & re-test (stay on
    step). *Secondary:* check prerequisites. *Hidden:* raw HTTP
    status/response. *Expandable:* the attempt's technical detail.
    *Audit:* attempts logged as `setup_readiness_check` jobs.
    *Escalation:* Admin-owned by construction (only Admins run the
    wizard); persistent failure points to the prerequisites step.
11. **Missing scope** (class 3 / readiness). *Title:* "A permission is
    missing: [scope]." *Explain:* what that scope is for, in business
    words; how to grant it in Shopify; re-run when done. *Recommended:*
    grant the named permission in the Shopify custom app, then re-run.
    *Primary:* Re-run check. *Secondary:* view all scopes (with their
    business reasons). *Hidden:* the raw scope-verification response.
    *Expandable:* granted-vs-required scope comparison. *Audit:* readiness
    runs logged. *Escalation:* Admin-owned (scope grants happen on the
    Shopify side); mid-operation scope loss surfaces as error type 5's
    class and pauses the affected domain.

**Cross-cutting rules.** Errors must feel recoverable, not catastrophic:
no red walls; one failure never visually condemns the whole system (the
lead band stays proportionate — "1 item needs you", not "SYNC FAILED");
technical detail is always available but never primary (RA-016); every
type above names its owner; and none of these surfaces ever invents an
error class outside the fixed 16. **[Accepted — DEC-009; Part D §17]**

---

## Copy and microcopy

All samples are **[Illustrative copy — MBQ-22 open]** — they set the tone
and shape for the later copy pass; none is final. Tone: calm,
professional, concise, non-technical, premium, action-oriented.
Credential-related copy must never claim encryption (**[Accepted posture —
MBQ-04]**).

| Moment | Sample copy |
| --- | --- |
| Connection success | "You're connected. We verified your credentials and permissions with Shopify." |
| Credential invalid | "Shopify didn't accept this credential. Check that you copied the full token from your custom app, then try again." |
| Missing scope | "One permission is missing: read_products. The connector needs it to import your catalog. Grant it in your Shopify custom app, then re-run this check." |
| Location not mapped | "This warehouse isn't linked to a Shopify location yet. Map it once, and inventory sync can start." |
| Product duplicate warning | "This looks like a product you already have ('Aria Lamp — Brass'). Link them instead of creating a copy?" |
| Order blocked for total mismatch | "Order #1042 is on hold: Shopify's total and the calculated total differ by 4.50. Review the breakdown before this order is created." |
| Retry scheduled | "We'll retry this automatically in about 5 minutes. No action needed." |
| Retry exhausted | "We tried 5 times without success, so we've stopped retrying. Review the reason below to get this moving again." |
| Reconnect required | "Shopify no longer accepts this store's saved credentials. Reconnect to resume syncing — everything else is safe and waiting." |
| Disconnect warning | "Disconnecting stops all syncing and removes the stored credentials. Your history, matches, and logs are kept. You can reconnect anytime." |
| No jobs yet | "No sync activity yet. When syncing starts, every job will be visible here." |
| No errors | "No open errors. Everything that ran recently succeeded." |
| First sync not started | "You're connected — but nothing has synced yet. A good first step: preview a product import." |
| Store healthy | "All systems normal. Last product sync 12 minutes ago (scheduled)." |
| Partial sync warning | "This run finished with 3 items skipped. Each skip has a reason — review them when you're ready." |

**Voice rules** (for the copy pass): verbs first in actions ("Review
breakdown", not "Breakdown review"); no exclamation marks in error states;
"we/you" framing; numbers stated plainly; never blame the user or Shopify;
never promise what the mechanism can't guarantee ("we'll retry" only where
auto-retry is classified).

---

## Premium UX opportunities

Realistic candidates only; each marked MVP (already inside accepted scope)
or Later (requires its own future decision/review — none is adopted by
this spec).

| Opportunity | Status | Basis |
| --- | --- | --- |
| **Guided setup progress** (step indicator, per-step verified moments, resumable wizard) | **MVP** | Accepted — Part A §E / Part D §3/§5 |
| **Smart onboarding checklist** (dashboard "finish setup" nudge + `setup_incomplete` remaining-steps list) | **MVP** (nudge + list are accepted); a richer post-setup checklist ("map locations → preview import → schedule first push") is **Later** | DEC-012 §1 item 11; Part D §5; extension **[Design proposal]** |
| **Retry recommendations** (suggested fix + retry-policy explanation per entry) | **MVP** | Accepted — Part A §H.3/§H.7 |
| **Root-cause grouping** ("N orders blocked by 1 mapping") | **MVP** | Accepted — Part D §9 |
| **Merchant-safe explanation copy** (structure now, final strings in the copy pass) | **MVP structure; Later copy** | Part D §17; MBQ-22 |
| **Queue aging indicators** (age column is MVP; visual aging emphasis/thresholds) | Age column **MVP** (DEC-012 §4 job list); aging *thresholds/emphasis* **Later** | DEC-012 §4; extension **[Design proposal]** |
| **Sync health score** (single composite score) | **Later** — new metric, not in the accepted card set; must not displace the plain-language lead answer | **[Design proposal — deferred]** |
| **Daily queue activity card** (time-series chart) | **Later** — explicitly deferred premium visualization candidate, already logged during the DEC-016 audit; supported by existing research (sh_shopify_connector benchmark) | DEC-016 point G; ux-ui-benchmark.md |
| **Recovery assistant-style panel** (the accepted recovery panel is MVP; a step-by-step "assistant" that sequences multi-item recovery is Later) | **MVP panel / Later assistant** | Part D §3 (custom recovery panel); extension **[Design proposal — deferred]** |
| **Clean audit timeline** (single chronological cross-artifact stream) | **Later** — MVP audit needs are met by filtered views over accepted artifacts (screen 19) | **[Design proposal — deferred]** |

---

## Open items and non-decisions

UI/UX details that **cannot be finalized yet**. Each is recorded, not
decided; none blocks this spec's acceptance, but each blocks (or shapes)
the named future implementation task.

1. **Exact view/menu/action XML IDs** — MBQ-03 (descoped to
   implementation planning). Everything structural in this spec is a
   direction until then.
2. **Exact user-facing copy** — MBQ-22 (descoped to a dedicated copy
   pass). Every quoted string here is illustrative.
3. **Exact access CSV rows / record rules** — MBQ-44 residual.
4. **Credential screen internals** — the MBQ-04 implementation-planning
   task (model/field/access-group/redaction/rotation/test-connection
   mechanics). This spec fixes only the operator-visible posture.
5. **Custom-app creation / token-acquisition walkthrough content** —
   MBQ-05 (descoped).
6. **Readiness-check thresholds and per-check copy** — DEC-018 MBQ-06
   residual.
7. **Quantity-read mechanics** — MBQ-32's source is **decided** (Phase 1
   uses `free_qty` semantics per mapped location, AR-020 conservative
   default; no source-choice UI); only the read/aggregation mechanics —
   including the required reconciliation acceptance test for the
   expired-unreserved divergence case — remain inventory task-spec
   detail.
8. **First-push confirmation-record schema** — MBQ-38 residual; the
   batched-review UI composition for MBQ-33's per-pair granularity is an
   open design detail for the future task.
9. **Total-check tolerance + exact Shopify total field** — MBQ-56
   (descoped); the breakdown UI shows structure, never an invented
   tolerance.
10. **Divergent-currency error-class/sub-reason mapping** — DEC-020
    residual.
11. **Domain binding model names** — MBQ-55 (descoped); binding screens
    reference the core mixin contract only.
12. **`odoo_event` human display label + trigger-origin rendering** —
    a copy question only (**MBQ-22**); DEC-019's semantics and AR-019's
    field mechanics are both resolved.
13. **FulfillmentOrder hold/lifecycle webhook UX** — MBQ-61 (descoped);
    Phase 1 screens must not simulate hold-awareness.
14. **Job/log retention policy and its settings surface** — [Open item —
    this spec / implementation planning].
15. **Field/action budget enforcement** — the 7±2 / one-primary-action
    disciplines are design guidance for review, not validation rules;
    whether any become hard checklist gates is for ChatGPT's review of
    this spec.
16. **Primary MVP persona emphasis** (P1 vs P2 lead) — open (RB-13 /
    product-vision), affects only emphasis, not structure.
17. **Later premium candidates** (activity chart, health score, audit
    timeline, recovery assistant, richer onboarding checklist) — each
    requires its own future decision; none may ship silently.

---

## No implementation authorized

This specification is a design document. It does not open any gate, does
not create or authorize any code, view, model, field, menu, wizard,
security artifact, credential mechanism, API client, webhook, controller,
or cron, and does not start Task 002. Implementation of any screen
specified here requires: the UI/UX implementation gate to be explicitly
opened by ChatGPT, and a per-task `CLAUDE.md` §9 specification naming
allowed/forbidden files, acceptance criteria, tests, and rollback — per
[`../07-implementation-plan/ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md).
