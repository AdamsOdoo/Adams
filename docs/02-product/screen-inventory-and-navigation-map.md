# Screen Inventory and Navigation Map

> Companion to
> [`ui-ux-final-design-spec.md`](./ui-ux-final-design-spec.md) — the full
> screen inventory, menu hierarchy, navigation paths, cross-links, role
> visibility, and MVP/later split for the premium **Odoo 19 ↔ Shopify
> Connector**. Docs-only; authorizes nothing; inherits the accepted Part D
> screen inventory (S1–S14,
> [`../03-architecture/master-blueprint-ui-ux-screen-design.md`](../03-architecture/master-blueprint-ui-ux-screen-design.md)
> §1–§2, DEC-016) without adding any new top-level surface. Odoo
> action/window/menu names below are **design placeholders only** — exact
> XML IDs remain **MBQ-03 (open)**; nothing here is a committed Odoo
> identifier.

## Claim labels

Same discipline as the design spec: **[Accepted — …]** restates accepted
content; **[Decided — DEC-018/019/020]** is a post-Part-D decision;
**[Design proposal — this spec]** is new design detail subject to ChatGPT
review; **[Open item — …]** is unresolved.

---

## 1. Full screen inventory

"Placeholder ref" is a human-readable design placeholder, **not** an XML
ID. Role visibility: **A** = Admin, **O** = Operator, **R** = Reviewer,
**Au** = Auditor; "(act)" = the role can act, otherwise read-only.
Surfaces are shared and role-gated; actions are gated, never the surfaces
(**[Decided — DEC-018 MBQ-45]**).

| # | Screen | Part D key | Placeholder ref | Nature | Visibility | MVP / Later | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Shopify Connector app root + persistent health indicator | — (§2.1 chrome) | `menu: Shopify Connector` | Top-level menu | All | MVP | Accepted — Part D §2.1 |
| 2 | Dashboard / command center | S3 | `action: Dashboard` | Card home | All (quick actions: O act) | MVP | Accepted — Part A §F; DEC-012 §3 |
| 3 | Sync center / jobs list | S4 | `action: Sync Center` | Shared list | All (retry/cancel: O act) | MVP | Accepted — Part A §G; DEC-012 §4 |
| 4 | Job form (job detail) | S4 detail | `view: Job form` | Form | All (actions role-gated) | MVP | Design proposal over accepted `shopify.connector.job` |
| 5 | Job logs (list within job form) | S4 detail | `view: Job logs` | Sub-list | All | MVP | Design proposal over accepted `shopify.connector.job.log` |
| 6 | Error center / recovery + manual-review queue | S5 | `action: Error Center` | Shared recovery surface | All (resolve: R act; fix/retry: O act) | MVP | Accepted — Part A §H; DEC-012 §5 |
| 7 | Order-import touchpoints (two S5 extensions — **no dedicated screen**) | S9 | — (extends Error Center) | Extension | As S5 | MVP | Accepted — DEC-014 point C (MBQ-26) |
| 8 | Matching / duplicate-prevention center | S6 | `action: Catalog & Matching` | Interactive flow | O act; R act (customer confirmations); Au read | MVP | Accepted — DEC-006; Part D §11 |
| 9 | Product preview / diff screen | S7 | `view: Product export preview` | In-flow preview | O act | MVP | Accepted — Part B §A.16; Part D §12 |
| 10 | Customer matching / review screen | S8 | `view: Customer match review` | In-flow review | R act (confirmations); O act (routine imports); Au read | MVP | Accepted — Part B §B; Part D §13 |
| 11 | Store list | S2-adjacent | `action: Store Settings (list)` | List | A act; others read | MVP (single-store; multi-store-safe) | Design proposal over accepted `shopify.connector.store`; DEC-003 |
| 12 | Store form / store settings | S2 | `view: Store form` | Settings form | A act; others read | MVP | Accepted — Part A §B/§I; DEC-012 §2 |
| 13 | Setup wizard (11 accepted steps) | S1 | `action: Setup Wizard` | Multi-step wizard | A only | MVP | Accepted — Part A §E; DEC-012 §1 |
| 14 | Credential entry step | S1 step 3 | — (wizard step) | Wizard step | A only | MVP (posture only; internals = MBQ-04 task) | Accepted — DEC-004; MBQ-04 posture |
| 15 | Test connection / readiness step | S1 steps 5–6 | — (wizard steps; re-runnable from S2) | Wizard steps / panel | A act; results visible to all via health surfaces | MVP | Accepted — Part A §E; Decided — DEC-018 MBQ-06 |
| 16 | Location mapping screen | S10 | `action: Inventory → Location Mapping` | Config list | A act; others read | MVP | Accepted — Part C §A.2 |
| 17 | Inventory first-push guard / confirmation | S11 | `view: First-push review` | Guarded preview→confirm | O stages; confirmation per guard classification; Au read | MVP | Accepted — Part C §A.5; Decided — DEC-018 MBQ-33 |
| 18 | Inventory source-of-truth / quantity & apply settings | S12 | `view: Inventory settings (S2 tab/sub-surface)` | Settings sub-surface | A act | MVP | Accepted — Part C §A.3/§A.4; Decided — DEC-018 MBQ-34 |
| 19 | Ongoing inventory review-then-apply queue | S12 flow | `view: Inventory apply review` | Review queue | O act (apply); Au read | MVP | Decided — DEC-018 MBQ-34 |
| 20 | Fulfillment log / detail + notification config + mismatch review | S13 | — (through S4/S5 + S2 sub-surface) | Extension surfaces | O act; R act (confirmations); A act (defaults) | MVP | Accepted — Part C §B; Decided — DEC-018 MBQ-41/60 |
| 21 | Audit / history view (filtered renderings of accepted artifacts) | — | `filters: Audit views on S4/S5` | Saved filters/views | All (chiefly Au) | MVP (filters); dedicated timeline **Later** | Design proposal — this spec |
| 22 | Permissions / roles visibility page | S14 | `view: Roles & Access` | Informational | All | MVP | Accepted — Part A §J; DEC-012 §10 |
| 23 | Daily queue activity chart card | — | — | Dashboard card | — | **Later** (deferred candidate, not adopted) | DEC-016 point G |
| 24 | Sync health score / recovery assistant / audit timeline / richer onboarding checklist | — | — | Premium candidates | — | **Later** (each needs its own decision) | Design spec §Premium opportunities |

**No new top-level surface is added** relative to the accepted Part D
inventory; rows 4, 5, 11, 19, and 21 are renderings/sub-views of accepted
models and surfaces, and row 7 is explicitly *not* a screen.

---

## 2. Menu hierarchy

**[Accepted — Part D §2.1]** (structure) with per-item annotations. The
`Configuration` branch remains part of the one shared, role-gated surface
(**[Decided — DEC-018 MBQ-45]** — no forked admin app).

```
Shopify Connector
├── Dashboard                  — the home; all roles
├── Sync Center                — all roles; actions role-gated
├── Error Center               — all roles; resolution Reviewer-gated
├── Catalog & Matching         — matching center + product preview + customer review entry
├── Inventory
│   ├── Location Mapping       — Admin edits; others read
│   └── First-Push & Sync      — first-push review + apply queue + drift view
├── Fulfillment                — fulfillment entries (filtered S4/S5) + notification settings link
└── Configuration              — Admin-focused branch of the same surface
    ├── Store Settings         — store list → store form
    ├── Roles & Access         — informational, all roles
    └── Setup Wizard           — re-runnable, resumes
```

### Premium simplicity notes per navigation area

- **Dashboard:** the answer, not a launcher farm. One lead sentence, nine
  cards, timeline. Nothing else.
- **Sync Center / Error Center:** the two recovery surfaces are adjacent
  in the menu because they are adjacent in the operator's mental model
  ("what ran" / "what needs me"). They must never merge into one screen
  (different jobs: monitoring vs deciding) and never fork per domain
  (RA-013).
- **Catalog & Matching:** one entry for matching + previews keeps the
  "make data agree" work in one place; the matching center is a reusable
  in-flow surface, not necessarily its own heavyweight page (**[Accepted —
  Part D §1 note on S6]**).
- **Inventory / Fulfillment:** thin branches — each exposes only its
  domain-specific config and guard surfaces; day-to-day monitoring stays
  in the shared centers. If a branch ever accumulates more than 2–3
  children, that is a design smell to review.
- **Configuration:** everything that changes behaviour lives here, with
  edits gated to Admin — an Operator works day-to-day in the six
  non-Configuration entries and touches Configuration only read-only (the
  Setup Wizard entry alone is hidden from non-Admins).

---

## 3. Odoo action/window assumptions (design placeholders only)

**[Design proposal — this spec; all identifiers = MBQ-03 open]**

| Surface | Assumed Odoo mechanics (placeholder) |
| --- | --- |
| Dashboard | A client/kanban-style card view over core aggregates; counts open filtered `act_window`s on job/error views |
| Sync Center | List view on `shopify.connector.job` with saved filters/group-by; default filter "needs attention" |
| Job form | Form view with statusbar (10 accepted states, plain-word labels), notebook (logs / technical detail / audit) |
| Error Center | Filtered job/error views + form detail with recovery panel; manual-review queue = sub-reason-filtered view |
| Matching center | List + candidate selection + blocking preview dialog before commit |
| Product preview/diff | Dialog/form rendering the five accepted preview states + destructive-write diff |
| Store settings | Form with status band + grouped settings + notebook tabs; domain modules extend via the accepted settings-extension seam (Part A §A.5.4) |
| Setup wizard | Step UI + statusbar; durable choices persist on the store/settings records so re-running resumes (Part D §3, accepted) |
| Location mapping | Editable list, domain-filtered Many2one (internal locations only) |
| First-push review | Wizard-style preview list + confirm; writes the confirmation record (schema = MBQ-38 residual) |
| Roles & Access | Static informational view; groups map 1:1 to the four accepted planning group names |
| Smart buttons | Participating records (product / sale order / partner / picking) expose binding / jobs / last-error smart buttons (Part D §3, accepted) |

---

## 4. Navigation paths (primary journeys)

**[Accepted — Part D §2.2 "no dead end" contract]**, drawn end-to-end:

```
1. First run:    App root → Dashboard (empty state) → Setup Wizard (11 steps)
                 → Dashboard ("connected, first sync not started" guidance)

2. Daily check:  Dashboard lead band → (all clear? done in 10 seconds)
                 → exception card → filtered Sync/Error Center → row → fix/retry → verify → back

3. Recovery:     Error Center entry → suggested fix action
                 ├─ mapping missing → Matching center → resolve → Retry (two clicks)
                 ├─ ambiguous outcome → Verify current state → resolved / retry / review
                 └─ review item → Reviewer resolves (or route/assign via activity)

4. Order hold:   Dashboard failed-by-severity card → Error Center (financial mismatch)
                 → inline breakdown (lines/tax/shipping/discount) → fix → retry

5. Inventory:    Wizard step 10 (schedule) → Inventory → First-Push & Sync
                 → preview → confirm (per mapped pair + binding) → enqueued
                 → ongoing: review-then-apply queue → apply → verify

6. Fulfillment:  Validate picking (native Odoo) → job appears in Sync Center
                 → success (tracking + notification decision recorded)
                 or blocked → Error Center → Reviewer confirms

7. Reconnect:    Health indicator / Store Settings band → Reconnect
                 → readiness re-run → resume (history preserved — DEC-018 MBQ-08)

8. From records: Odoo product/order/partner/picking → smart button
                 → binding / jobs / last error → back to the record
```

---

## 5. Cross-links between screens

| From | To | Link | Basis |
| --- | --- | --- | --- |
| Dashboard (every count/card) | Sync/Error Center, filtered | Click-through | Accepted — Part A §F.3 |
| Sync Center row | Error Center entry; source record; mapping/binding | Row actions | Accepted — Part A §G.3 |
| Error Center `mapping missing` | Matching center (S6) | Direct resolve→retry link | Accepted — Part B §C.14 |
| Error Center `financial total mismatch` | Inline breakdown (no navigation needed) | Embedded | Accepted — Part B §C.14 |
| Error Center `inventory location missing` | Location mapping (S10) | Fix link | Accepted — Part C §A.9 |
| Readiness check failure | The fixing surface (scopes info, location mapping, settings) | Per-check fix link | Decided — DEC-018 MBQ-06; Design proposal |
| Store settings | Wizard (re-run), S10, S12, gateway→journal tab | Config links | Accepted — Part D §6 |
| Wizard finish | Dashboard | Handoff | Accepted — Part D §5 |
| First-push card (dashboard) | S11 review | Click-through | Accepted — Part A §F.1 card 6 |
| Odoo records (product/order/partner/picking) | Binding / jobs / last error | Smart buttons (bidirectional with "Open source record") | Accepted — Part D §3 |
| Any blocked item, wrong role | Assign/route to owning role | Activities convention | Accepted — Part D §9 |

---

## 6. Role visibility matrix (navigation level)

| Menu entry | Admin | Operator | Reviewer | Auditor |
| --- | --- | --- | --- | --- |
| Dashboard | act | act (quick actions) | read + review card routes to their queue | read |
| Sync Center | act | act (retry/cancel safe) | read (+ their items) | read |
| Error Center | act | fix/retry | **resolve confirmation-required** | read |
| Catalog & Matching | act | act (product matching) | customer/duplicate confirmations | read |
| Inventory (both children) | act (mapping/settings) | stage/apply where safe | guard confirmations | read |
| Fulfillment | act (defaults) | retry/verify | mismatch/notification confirmations | read |
| Configuration → Store Settings | **act** | read | read | read |
| Configuration → Roles & Access | read | read | read | read |
| Configuration → Setup Wizard | **act** | — (hidden) | — (hidden) | — (hidden) |

**[Design proposal — this spec]:** the wizard is hidden (not disabled) for
non-Admins; all other surfaces stay visible to all roles with actions
gated — visibility parity is what makes the shared-surface decision
(DEC-018 MBQ-45) feel like one product.

---

## 7. MVP vs Later (navigation scope)

- **MVP:** everything in rows 1–22 of the inventory (the accepted S1–S14
  set plus this spec's renderings of accepted models). Single store;
  single company; the menu tree above complete.
- **Later:** activity chart card; sync health score; dedicated audit
  timeline; recovery assistant; richer onboarding checklist; per-order
  notification override (deferred by DEC-018); multi-store navigation
  (store switcher / per-store dashboards) — deferred with DEC-003;
  anything touching order edits/refunds/returns (deferred by DEC-003).
- Nothing in "Later" may be implemented, or navigated to, without its own
  future decision — no hidden menu stubs, no "coming soon" entries
  (**[Design proposal — this spec]**: dead menu items are an anti-premium
  pattern).

---

## 8. Dependencies / open questions affecting navigation

| Item | Effect on navigation | Status |
| --- | --- | --- |
| MBQ-03 (XML IDs) | All placeholder refs above | Open — implementation planning |
| MBQ-22 (copy) | All menu labels / on-screen names | Open — copy pass |
| MBQ-44 residual (access rows) | Enforcement of the visibility matrix | Open — implementation planning |
| MBQ-04 task (credential internals) | Credential step content | Open — dedicated planning task |
| MBQ-05 (token acquisition mechanics) | Wizard step 3/4 helper content | Descoped/open |
| MBQ-56 / MBQ-27 (total-check detail / tax mechanism) | Breakdown extension detail | Descoped/open |
| MBQ-61 (FO lifecycle webhooks) | Future fulfillment hold-aware states | Descoped/open |
| DEC-020 residual (divergent-currency class mapping) | Which error-center filter shows blocked currency orders | Open |
| Primary MVP persona (RB-13) | Emphasis (which journeys get most polish), not structure | Open |

---

## 9. Screens combined to avoid clutter

- **Order import** → no screen at all; two error-center extensions
  (accepted decision, MBQ-26).
- **Fulfillment monitoring** → the shared Sync/Error Centers (RA-013);
  only notification settings + mismatch review are fulfillment-specific.
- **Audit/history** → saved filters over the shared surfaces, not a new
  store or screen (MVP).
- **Store list + store form** → one Configuration entry; the list is a
  thin pass-through while Phase 1 is single-store.
- **Inventory settings (S12)** → a tab/sub-surface of Store Settings, not
  a separate top-level page.
- **Test connection + readiness** → one wizard surface with two moments
  (prove credential, prove readiness), re-runnable from Store Settings —
  not two scattered tools.

## 10. Screens kept separate to avoid cognitive overload

- **Sync Center vs Error Center** — monitoring ("what ran") vs recovery
  ("what needs a decision") are different mental modes; merging them
  produces the firehose every competitor suffers from.
- **Matching center vs product preview/diff** — deciding identity
  (matching) vs reviewing a write (diff) are separate decisions; folding
  them together overloads the preview.
- **First-push guard (S11) vs ongoing apply queue** — the one-time
  ceremonial confirmation and the routine review queue must feel
  different; blending them either dulls the guard or over-dramatizes
  routine applies.
- **Setup wizard vs Store Settings** — first-run guidance vs ongoing
  control; the wizard resumes/re-runs but never becomes the settings
  editor.
- **Location mapping vs quantity settings** — "where stock goes" vs "what
  number we send" are distinct decisions with distinct risk profiles.

---

## No implementation authorized

Docs-only. No menu, action, view, or navigation artifact may be created
from this document until ChatGPT opens the UI implementation gate and a
per-task §9 specification exists.
