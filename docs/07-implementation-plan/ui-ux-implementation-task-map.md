# UI/UX Implementation Task Map

> **Future** implementation task map for the connector's operator-facing
> UI — planning only. Prepared in the UI/UX Final Design Sprint
> (2026-07-06) as the bridge from
> [`../02-product/ui-ux-final-design-spec.md`](../02-product/ui-ux-final-design-spec.md)
> to future `CLAUDE.md` §9 task specifications. **This document creates no
> task, authorizes no code, and opens no gate.** The only open gate remains
> the limited **core-only, zero-UI** gate
> ([`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md));
> every group below additionally requires (1) an explicit ChatGPT UI-gate
> opening act for its area, and (2) its own §9 task spec (allowed/forbidden
> files, acceptance criteria, tests, rollback, definition of done) written
> and reviewed **before any code**. Task ordering below is a proposed
> sequence, not a schedule; module areas repeat the accepted DEC-008 addon
> family and AR-019 naming directions — not new commitments.

## Status

**Accepted by ChatGPT on 2026-07-06** (PR #91 acceptance patch;
[`AR-023`](../05-qa/architecture-review-log.md)) as **planning guidance
only**. **Does not create any implementation task. Does not open the UI
implementation gate.** Every future task named below still requires its
own separate `CLAUDE.md` §9 task spec (allowed/forbidden files,
acceptance criteria, tests, rollback, definition of done) written and
reviewed before any code.

## Global rules for every future UI task

- **Prerequisites (all groups):** UI implementation gate opened by
  ChatGPT; MBQ-03 (XML IDs) resolved for the task's surface as task-spec
  detail; the design spec + this map + the accepted Part D checklist and
  [`../05-qa/ui-ux-design-review-checklist.md`](../05-qa/ui-ux-design-review-checklist.md)
  attached to the task as its acceptance bar.
- **Universal must-not-dos:** never modify `adams_base` or non-connector
  code; never fork a per-domain dashboard/queue (RA-013); never render an
  internal token or raw stack trace as a primary label (RA-016); never
  add a guard bypass (Part A §I.5); never claim encryption in credential
  copy (MBQ-04 posture); never widen MVP scope (DEC-003).
- **Universal acceptance criteria:** all screen states implemented
  (empty/loading/success/warning/error/manual-review as specified);
  role-gating per the visibility matrix; vocabulary rendered via the
  single shared label mapping; checklist §L (Premium Simplicity Standard)
  passes including the per-screen "clean, premium, modern, human-friendly
  without unnecessary complexity" item.
- **Universal premium requirement:** each screen ships with its guidance
  built in (helper text, empty-state next actions, suggested fixes) — a
  screen that needs external documentation to operate fails review.
- **Universally unacceptable (UX):** toggle walls; unfiltered firehose
  defaults; colour-only status; dead ends; jargon on action paths;
  overloaded forms; any silent write.

Risk levels: **Low** = read-only/informational; **Medium** = config or
staged actions; **High** = credentials, destructive writes, guards, or
money-adjacent surfaces.

---

## Group 1 — UI foundation / menu shell

- **Scope (future).** App root menu; the seven top-level entries;
  role-gated menu visibility; the persistent connection-health indicator
  chrome; the shared human-label mapping for the fixed vocabularies; the
  **S14 Roles & Access informational page** (read-only capability matrix —
  low-risk, natural to ship with the shell).
- **Prerequisite decisions.** UI gate; MBQ-03 for the shell; MBQ-22
  initial label set (at least the state/class/sub-reason display words);
  for the S14 page, the MBQ-44 residual (exact access rows) only informs
  wording — the page itself is informational.
- **Module area.** `shopify_connector_core`.
- **Risk.** Medium (chrome touches everything).
- **Dependencies.** None (first UI task); core models exist (Task 001).
- **Must not.** Add any domain menu for a domain module that isn't
  installed/enabled; expose any raw model list as a menu target; ship
  menu stubs for Later features.
- **Acceptance criteria.** Menu tree matches the accepted §2.1 structure;
  health indicator shows text-labelled state from every region; an
  Operator can act in the six non-Configuration entries and reads
  Configuration (only the Setup Wizard entry hidden), per the navigation
  map's visibility matrix; Auditor sees no action affordances; the S14
  page renders the four-role capability matrix in plain language with no
  editable element.
- **Premium simplicity requirement.** The shell disappears — navigation
  never needs explaining.
- **Unacceptable.** A deep/nested menu; a health dot without words;
  Configuration visible-but-broken for non-admins.

## Group 2 — Dashboard

- **Scope (future).** Lead answer band; the nine accepted cards; recent
  activity timeline; quick actions (enqueue only); empty/first-run
  guidance; overdue-sync exception surfacing.
- **Prerequisite decisions.** Group 1; overdue threshold source (MBQ-17
  cadence residual — task-spec detail).
- **Module area.** `core` (cards contributed via seams by domain
  modules).
- **Risk.** Medium.
- **Dependencies.** Job/log substrate (exists); filtered views (Group 8).
- **Must not.** Add a tenth card, a chart, or any metric without a
  health-signal/next-action mapping; run sync inline from a quick action;
  show raw log lines.
- **Acceptance criteria.** Ten-second usefulness test passes; every count
  clickable to the correctly-filtered view; zero states affirmative;
  freshness labelled with mechanism.
- **Premium simplicity requirement.** One screenful; the lead sentence
  answers the north-star question before any number is read.
- **Unacceptable.** Vanity metrics; a wall of equal-weight cards; any
  count that opens an unfiltered list.

## Group 3 — Setup wizard

- **Scope (future).** The 11 accepted steps as a resumable guided flow;
  step indicator; per-step verified moments; `setup_incomplete` state +
  remaining-steps surfacing; final confidence summary. (Credential entry
  and test/readiness steps integrate Groups 4–5's mechanics.)
- **Prerequisite decisions.** Groups 1, 4, 5; MBQ-05 walkthrough content
  decision; MBQ-22 wizard copy.
- **Module area.** `core`.
- **Risk.** High (first-run trust; gates everything downstream).
- **Dependencies.** Credential task (Group 4); readiness engine (Group 5);
  store settings (Group 6).
- **Must not.** Auto-complete or skip any guard; pre-select
  direction/source-of-truth/notification; offer directions outside
  DEC-003; execute the inventory first push (scheduling only).
- **Acceptance criteria.** Exit-and-resume works at every step; business
  sync provably blocked until completion; the summary states
  domains/directions/source-of-truth/notification/first-push accurately.
- **Premium simplicity requirement.** One decision per step; a merchant
  finishes in ~10 minutes feeling *safer*, not braver.
- **Unacceptable.** A one-page configuration dump; silent defaults; scope
  strings as free text; fear-toned failures.

## Group 4 — Credentials screen (entry + replacement)

- **Scope (future).** Masked credential entry (wizard step +
  settings-band replacement); token-status display (present /
  last-verified); the no-read-back guarantee across every surface.
- **Prerequisite decisions.** **The dedicated MBQ-04 implementation-
  planning task must be written and accepted first** (model, field,
  access group, redaction/no-logging, rotation/revocation,
  test-connection interaction, rollback) — this group must not start
  before it.
- **Module area.** `core`.
- **Risk.** **High** (secret handling).
- **Dependencies.** None besides its prerequisite task; blocks Groups 3/5.
- **Must not.** Persist the value anywhere unmasked in UI/logs; offer any
  read-back/reveal affordance for any role; claim encryption anywhere;
  implement rotation UX beyond what the MBQ-04 task fixes.
- **Acceptance criteria.** Value never renders after save (verified for
  all four roles); redaction rule demonstrably applied to job logs; copy
  matches the accepted posture wording constraints.
- **Premium simplicity requirement.** One field, honest reassurance, zero
  security theatre.
- **Unacceptable.** A reveal toggle; padlock-iconography implying
  encryption; multi-field credential forms without cause.

## Group 5 — Readiness / test connection

- **Scope (future).** The Test Connection action; the readiness panel
  with the decided essential-vs-warning split (DEC-018 MBQ-06); per-check
  fix links; re-run from Store Settings; readiness re-run on reconnect.
- **Prerequisite decisions.** Group 4 (needs a credential to test);
  per-check thresholds (task-spec detail).
- **Module area.** `core` (checks contributed via seams where
  domain-specific, e.g. mapped-location check).
- **Risk.** Medium.
- **Dependencies.** Group 4; external API gate (Shopify calls are
  currently blocked — this group needs the API-client gate too).
- **Must not.** Let a failed essential check reach "connected"; block on
  a warning-tier check; run any business write (jobs are
  `setup_readiness_check`, read-only).
- **Acceptance criteria.** Named pass/fail with reasons for every check;
  the two tiers visually and behaviourally distinct; warnings carried to
  the dashboard.
- **Premium simplicity requirement.** Watching the checks run builds
  trust — each row reads as proof, not diagnostics.
- **Unacceptable.** A silent spinner; one opaque "failed"; raw HTTP
  codes.

## Group 6 — Store settings

- **Scope (future).** Store list + store form: connection band; domain
  toggles with guard re-entry; sync-behaviour group; notebook tabs
  (locations link, gateway→journal, API version, advanced); disconnect/
  reconnect with the decided retention confirmation.
- **Prerequisite decisions.** Groups 1, 4, 5; settings-form composition
  (MBQ-03 / task-spec detail — the settings model shape and its Phase 1
  field names are already resolved via AR-019, no MBQ-07 residual
  exists); MBQ-54 disclosure copy.
- **Module area.** `core` + domain settings-extension seams.
- **Risk.** Medium-High (disconnect; source-of-truth changes).
- **Dependencies.** Groups 4–5.
- **Must not.** Delete history on disable/disconnect; hide
  reconnect/disconnect; expose credential value or raw cron/cost
  internals; let a settings save bypass a domain guard.
- **Acceptance criteria.** Status band answers "what is this connector
  doing" in one glance; disconnect confirmation states the decided
  retention posture verbatim in substance; enabling a domain re-enters
  its guard.
- **Premium simplicity requirement.** Grouped by intent, 7±2 visible
  elements per region, advanced behind tabs.
- **Unacceptable.** A toggle wall; disconnect adjacent to save; jargon
  labels without helper text.

## Group 7 — Locations

- **Scope (future).** The S10 mapping list (internal-only candidates,
  fetch-and-pick Shopify Locations, per-pair first-push status);
  disconnect-topic warning surfacing.
- **Prerequisite decisions.** Groups 1, 6; MBQ-43 refresh cadence
  (task-spec).
- **Module area.** `shopify_connector_inventory` (surface renders through
  core patterns; `shopify.connector.location` reference is core).
- **Risk.** Medium (precondition for high-risk writes).
- **Dependencies.** Group 6; API client gate (location fetch).
- **Must not.** Offer non-internal Odoo locations; infer by name; allow
  inventory writes with zero mappings.
- **Acceptance criteria.** Mapping reads as unambiguous sentences;
  removal confirms consequences; unmapped/ambiguous routes to the error
  center correctly classified.
- **Premium simplicity requirement.** A five-minute, one-screen job.
- **Unacceptable.** Free-text location entry; hidden first-push status.

## Group 8 — Sync center

- **Scope (future).** The shared job list; four filters over the fixed
  vocabularies; "needs attention" default; saved searches/group-by; the
  class-conditional row-action set (retry/verify/open/cancel-supersede);
  bulk recovery; job form + job logs rendering.
- **Prerequisite decisions.** Groups 1–2; MBQ-22 state/class labels,
  including the `odoo_event` display label (a copy question only —
  DEC-019 semantics and AR-019 field mechanics are both resolved).
- **Module area.** `core`.
- **Risk.** Medium-High (retry actions).
- **Dependencies.** Job substrate (exists); Group 1.
- **Must not.** Render a blanket retry; show retry on terminal rows;
  collapse the 10-state vocabulary below the accepted grouping rules;
  force ineligible rows in bulk actions.
- **Acceptance criteria.** The four retry cases render correctly per
  class/state (test matrix required); default filter lands on "needs
  attention"; operation reference legible without exposing key schema.
- **Premium simplicity requirement.** A row answers what/why/state/what-
  can-I-do without opening it.
- **Unacceptable.** An unfiltered firehose; raw tokens in the state
  column; ambiguous button semantics on terminal rows.

## Group 9 — Error center

- **Scope (future).** The nine-element entry contract; the manual-review
  queue keyed by sub-reason; root-cause grouping; route/assign
  (activities); the two order-import extensions (financial breakdown;
  matching links); divergent-currency blocked entries.
- **Prerequisite decisions.** Group 8; MBQ-22 reason/fix copy set;
  DEC-020 residual class mapping for currency blocks.
- **Module area.** `core` (+ `sale` extension seams for the order
  extensions).
- **Risk.** High (recovery correctness; Reviewer actions).
- **Dependencies.** Groups 1, 8.
- **Must not.** Present a total mismatch or unmatched product as
  confirmation-required review (per-class routing is binding — DEC-014
  point I); offer edit/re-apply of Shopify order edits; leave any
  role-gated dead end.
- **Acceptance criteria.** Every entry: reason + fix + owner + audit;
  two-click resolve→retry from `mapping missing`; breakdown renders
  per-component; Reviewer resolution recorded who/when.
- **Premium simplicity requirement.** The calmest screen in the product;
  grouped causes read as one problem, not N rows.
- **Unacceptable.** Stack traces above the fold; a generic "needs review"
  badge; dead ends.

## Group 10 — Product screens

- **Scope (future).** Matching center (product side); five-state
  preview/diff; destructive-write diff (delete-on-omission rendering);
  draft-first export + explicit channel-selecting publish; smart buttons
  on product records.
- **Prerequisite decisions.** Product domain gate; MBQ-23/24/25
  residuals fixed as task-spec detail; Groups 8–9.
- **Module area.** `shopify_connector_product` (renders through core).
- **Risk.** High (destructive catalog writes).
- **Dependencies.** Groups 8–9; API client + product domain logic gates.
- **Must not.** Auto-publish; write without the preview path; auto-match
  by name; let automated imports bypass the pre-create gate.
- **Acceptance criteria.** All five preview states reachable and tested;
  delete-on-omission visibly highlighted; publish is explicit and
  channel-selecting; skips carry reasons.
- **Premium simplicity requirement.** The diff reads like a change
  summary a merchandiser understands, not a field dump.
- **Unacceptable.** A buried destructive warning; publish as an export
  side effect.

## Group 11 — Customer / matching screens

- **Scope (future).** Customer match/review surface; email-only automatic
  matching rendering; advisory hints; flagged fallback partner; Reviewer
  confirmation flow.
- **Prerequisite decisions.** Sale domain gate; fallback partner naming
  (MBQ-29 resolved — naming is task-spec detail); the PII-display
  discipline (match evidence, not full profiles) fixed in the task spec
  under the accepted conservative protected-data posture (MBQ-09's own
  open residual is compliance-webhook-scoped, not a screen constraint).
- **Module area.** `shopify_connector_sale`.
- **Risk.** Medium-High (PII).
- **Dependencies.** Groups 8–9, 13 (order flow interplay).
- **Must not.** Auto-bind on phone/name; render full PII where match
  evidence suffices; make the fallback partner visually normal.
- **Acceptance criteria.** Ambiguity always routes to Reviewer;
  fallback usage flagged and auditable; advisory hints visibly
  non-binding.
- **Premium simplicity requirement.** A Reviewer decision takes one
  glance at one evidence card.
- **Unacceptable.** A data-dump comparison table; silent fallback usage.

## Group 12 — Order screens (touchpoint extensions only)

- **Scope (future).** The two error-center extensions (inline financial
  breakdown; direct matching links); divergent-currency block rendering;
  order smart buttons. **No dedicated order-import screen — building one
  is out of scope by decision (MBQ-26).**
- **Prerequisite decisions.** Sale domain gate; MBQ-56/MBQ-27 as
  task-spec detail (structure ships without an invented tolerance).
- **Module area.** `shopify_connector_sale` extending core S5.
- **Risk.** High (money-adjacent display correctness).
- **Dependencies.** Group 9.
- **Must not.** Create the dedicated screen; auto-apply order edits;
  display an invented tolerance; automate any invoice/payment step.
- **Acceptance criteria.** Breakdown component math matches the accepted
  evidence-sum definition; two-click resolve→retry verified; currency
  blocks show captured evidence.
- **Premium simplicity requirement.** Reads like a receipt comparison.
- **Unacceptable.** Raw money JSON; a mismatch presented as a review
  approval.

## Group 13 — Inventory screens

- **Scope (future).** First-push guard flow (per decided granularity,
  batched review permitted with per-unit recording); confirmation-record
  capture; quantity/source-of-truth settings (S12); ongoing
  review-then-apply queue; drift/reconciliation view.
- **Prerequisite decisions.** Inventory domain gate; MBQ-32 residual
  (quantity source mechanism) and MBQ-38 residual (record schema) fixed
  as task-spec detail; Groups 7–9.
- **Module area.** `shopify_connector_inventory`.
- **Risk.** **High** (live storefront stock).
- **Dependencies.** Groups 7, 8, 9.
- **Must not.** Offer `committed` anywhere; ship auto-apply; weaken the
  guard's element set (mapped location + preview + confirmation +
  recorded source-of-truth + skip/manual-match); auto-resolve drift.
- **Acceptance criteria.** Guard fires at the decided granularity with
  individually-recorded units; confirmation record persisted and
  linkable; apply queue uses the same preview shape; drift is a distinct
  exception.
- **Premium simplicity requirement.** The first push feels like a
  careful signing ceremony; the ongoing queue a two-minute routine.
- **Unacceptable.** Confirm-above-preview layouts; equal-weight quantity
  semantics; any previewless apply path.

## Group 14 — Fulfillment screens

- **Scope (future).** Fulfillment entries through S4/S5 (matched-unit
  rendering, tracking distinctness, notification requested/suppressed);
  notification default sub-surface; location-mismatch review;
  `stock_delivery` absence → readiness-blocked state.
- **Prerequisite decisions.** Fulfillment domain gate; MBQ-40 residual;
  MBQ-61 explicitly out (no hold-awareness simulated).
- **Module area.** `shopify_connector_fulfillment`.
- **Risk.** High (customer-facing side effects: notifications, double
  fulfillment).
- **Dependencies.** Groups 8–9, 13-independent (fulfillment never depends
  on inventory — Part C §C.1).
- **Must not.** Default notification on, or re-read it on retry; build a
  parallel fulfillment monitor; render an unmatched picking as
  auto-resolvable; create tracking updates as new fulfillments.
- **Acceptance criteria.** Notification decision visible on every entry;
  verification-read-before-retry enforced for ambiguous outcomes; missing
  `stock_delivery` yields the named readiness blocker.
- **Premium simplicity requirement.** Every entry reads as one matched
  sentence.
- **Unacceptable.** Surprise-notification paths; unexplained holds; a
  fulfillment dashboard fork.

## Group 15 — Audit / log screens

- **Scope (future).** Audit-oriented saved filters/views over S4/S5;
  binding audit rendering; guard-confirmation record views; log detail
  polish. (The dedicated audit timeline remains a Later premium
  candidate needing its own decision.)
- **Prerequisite decisions.** Groups 8–9; retention policy (open item)
  as task-spec detail.
- **Module area.** `core`.
- **Risk.** Low (read-only).
- **Dependencies.** Groups 8–9.
- **Must not.** Create a parallel audit data store; make audit surfaces
  editable; ship the timeline without its own accepted decision.
- **Acceptance criteria.** An Auditor can reconstruct a
  destructive-write, a manual match, and a notification decision without
  leaving the filtered views; before/after values render for destructive
  ops.
- **Premium simplicity requirement.** Audit reads as a story, not a
  table dump.
- **Unacceptable.** Jargon-only audit lines; audit data only reachable
  via developer tools.

---

## Proposed sequencing (dependency-driven, not a schedule)

1 (shell, incl. the S14 Roles & Access page) → 4 (credentials, after its
MBQ-04 planning task) → 5
(readiness) → 6 (settings) → 3 (wizard) → 2 (dashboard) + 8 (sync center)
→ 9 (error center) → 7 (locations) → then domain-gated groups as their
gates open: 10 (product), 11–12 (customer/order), 13 (inventory), 14
(fulfillment) → 15 (audit polish). Later premium candidates (chart,
health score, timeline, assistant) each require a separate decision
before entering any group.

## No implementation authorized

This map is planning documentation. It creates no task and no code
authorization; every group requires the UI gate, any named domain/API
gates, and its own reviewed `CLAUDE.md` §9 task specification before a
single file is created.
