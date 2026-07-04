# Master Blueprint — Part D: UI/UX Screen Design Blueprint

> Screen-level UI/UX design blueprint for the premium **Odoo 19 ↔ Shopify
> Connector**, converting the ten accepted **DEC-012** operator flows and the
> accepted **Part A/B/C** blueprints into screen inventory, navigation /
> information architecture, Odoo-native interaction patterns, blueprint-level
> screen specs, per-screen states, a UX-copy/error-message style guide, and a
> premium UI/UX acceptance checklist. **Proposes to partially resolve
> MBQ-53** at screen-design level (MBQ-53 stays open until DEC-016 is
> accepted). Companion index: [`master-blueprint.md`](./master-blueprint.md).
> Companion decision record (this sprint):
> [`../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md).

## Status

**Proposed for ChatGPT review — NOT accepted.** Prepared as **Master
Blueprint Sprint D** on **2026-07-03**, on top of the base commit that
accepted DEC-015 (Part C). Documentation only; the no-code gate
(`CLAUDE.md` §4–§5) is in force. **This blueprint does not authorize code**,
does not create or permit any Odoo module/model/view/menu/security file, and
does not open the implementation gate. It is a **screen-design blueprint**,
not an implementation of any screen.

- **Part A** (core substrate, DEC-013), **Part B** (product/customer/order,
  DEC-014), and **Part C** (inventory/fulfillment, DEC-015) remain **Accepted
  by ChatGPT** and are treated here as binding, unmodified inputs.
- **DEC-012** (ten operator flows) remains **Accepted by ChatGPT** and is the
  behavioural spine this part gives screens to.
- **Part E** (implementation-planning bridge) remains **Not started**.
- Acceptance of this part, if it comes, is a **screen-design acceptance**; it
  still does not by itself authorize implementation (see
  `master-blueprint.md` *Criteria for when implementation may later be opened*).

## Claim labels used throughout

Every substantive statement carries exactly one label. This preserves the
`CLAUDE.md` §8 classification discipline used by Parts A/B/C:

| Label | Meaning |
| --- | --- |
| **[Accepted — DEC-0XX]** | Already accepted by ChatGPT (a decision record or an accepted blueprint part). Binding; restated here, never re-litigated. |
| **[Screen blueprint proposal]** | A screen-design proposal introduced by this sprint. **Not binding** unless/until DEC-016 is accepted. |
| **[Recommendation — open, MBQ-nn]** | A still-open decision (ChatGPT- or implementation-planning-owned) for which the accepted inputs carry a recommendation. This part **designs screens to accommodate either resolution** and does **not** decide the row. |
| **[Open question — MBQ-nn]** | An unresolved item routed to its owner; not asserted. |
| **[Inference]** | Our interpretation from cited evidence. |

**Naming / label discipline (binding, from Part A/B/C).** Every Odoo model,
field, menu, action, view, security-group, XML ID, on-screen label, and copy
string named in this document is a **proposed direction only — not a committed
Odoo identifier and not final UI copy.** Exact identifiers remain **MBQ-01**
(model names), **MBQ-02** (field names), **MBQ-03** (view/menu/action XML IDs),
**MBQ-44** (security groups / access CSVs); exact user-facing copy remains
**MBQ-22**. This part proposes **structure, layout regions, element order,
state behaviour, and interaction patterns** at **blueprint level** — it does
**not** fix Odoo view XML, widget bindings, or final wording.

## What "screen-level wireframe spec" means here (scope interpretation)

`master-blueprint.md` defines the Master Blueprint as operating at **blueprint
level — "concepts, contracts, rules, flows — not code, not schemas, not XML."**
Consistent with that, a **screen spec** in this document is a **structural
layout contract**: the screen's purpose, its users, its entry points, the
regions and content blocks it must contain, the element order, the actions it
exposes, its guard/blocked states, and its empty/loading/success/error/
manual-review states — expressed in prose and simple text layout sketches. It
is **not** a pixel mockup and **not** Odoo view XML. Pixel/interaction fidelity
and the exact XML are implementation-planning artifacts gated on **MBQ-03** and
a later, separately-authorized design pass. This interpretation is stated so
review can confirm the part stays inside the no-code gate.

---

## Relation to accepted inputs

This part is built strictly **on top of** — and must never contradict, weaken,
or re-open — the accepted records. Screen designs here **inherit** the accepted
behaviour; they add layout and interaction, never new behaviour.

| Accepted input | What this part reuses |
| --- | --- |
| [DEC-003](../04-decisions/DEC-003-mvp-scope.md) | MVP scope boundary; "controlled, not autonomous"; no auto-apply default; deferrals (order edits/refunds/returns, multi-store). |
| [DEC-004](../04-decisions/DEC-004-distribution-api-auth-strategy.md) | Credential no-read-back; honest named API-health indicator; setup-wizard shape. |
| [DEC-006](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) | Match-key priority; three matching states; binding audit fields; no name-only auto-match (RA-006). |
| [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) | Destructive-write/first-push/notification guards; price source-of-truth explicit. |
| [DEC-008](../04-decisions/DEC-008-module-boundary-strategy.md) | Module family; the single-shared-surface rule (RA-013). |
| [DEC-009](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) | 6 job sources / 10 job states / 16 error classes / 6 manual-review sub-reasons / classified retry. |
| [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md) / [DEC-011](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) | Inventory/fulfillment postures reused by the inventory & fulfillment screens. |
| [DEC-012](../04-decisions/DEC-012-ux-operator-flow-strategy.md) | The ten operator flows — the behavioural contract this part gives screens to. |
| [DEC-013](../04-decisions/DEC-013-master-blueprint-core-substrate.md) / Part A | Setup-wizard/dashboard/sync-center/error-center/settings/access substrate. |
| [DEC-014](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) / Part B | Product diff (five states), customer matching (email-only), order-import touchpoints (no dedicated screen, MBQ-26). |
| [DEC-015](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md) / Part C | Location mapping, first-push guard, apply-mode, fulfillment log/notification. |
| [`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md) | The DEC-012 flow detail (per-flow items). |
| [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md) | The 12 UX principles, UX north star, confidence loop — **recommendation-level inputs** (that doc "decides nothing"). |
| [`../02-product/product-vision.md`](../02-product/product-vision.md) | 7 non-negotiables, 7-criterion premium bar, personas — **recommendation-level inputs** (that doc "decides nothing"; predates DEC-003, reconciled against it). |

**RA guardrails (binding rejected approaches this part must never
reintroduce):** RA-006 (name-only auto-match), RA-008 (blind first inventory
push), RA-009 (hidden/default-on fulfilment notification), RA-013 (parallel
per-domain dashboards/queues), RA-014 (retry-everything), RA-015 (never-retry),
RA-016 (raw stack trace as primary error UX), RA-018 (writing `committed`),
RA-019 (SKU-only inventory writes), RA-020 (autonomous bidirectional inventory
conflict resolution), RA-022 (legacy fulfillment API), RA-023 (fulfillment
without order/FulfillmentOrder/line/quantity/location matching).

---

## §1. Screen inventory

**[Accepted — DEC-008 §K rule 2 / RA-013 / Part A §K.2].** The connector
presents **one shared, role-gated set of operator surfaces**. Domain modules
(`product`/`sale`/`inventory`/`fulfillment`) **contribute** data, categories,
job types, and settings *into* these shared surfaces; they **never** build a
parallel dashboard, sync center, error center, or manual-review queue. The
screen inventory is therefore small and shared, not per-domain.

| # | Surface | Nature | Owning module (surface) | Accepted basis |
| --- | --- | --- | --- | --- |
| S1 | **Setup wizard** | Dedicated multi-step wizard | `core` | DEC-012 §1; Part A §E |
| S2 | **Store settings** | Dedicated single settings surface | `core` (domain-extended) | DEC-012 §2; Part A §B/§I |
| S3 | **Dashboard / command center** | Dedicated top-level home | `core` | DEC-012 §3; Part A §F |
| S4 | **Sync center / job monitor** | Dedicated shared job list (all domains) | `core` | DEC-012 §4; Part A §G |
| S5 | **Error center / recovery + manual-review queue** | Dedicated shared recovery surface | `core` | DEC-012 §5; Part A §H |
| S6 | **Matching / duplicate-prevention center** | Cross-cutting interactive flow | `core` contract + `product`/`sale` | DEC-012 §6; Part A §C; Part B §A.9/§B.9 |
| S7 | **Product preview / diff screen** | In-flow preview (interactive/batch) | `product` (renders through core) | Part B §A.9/§A.11/§A.16 |
| S8 | **Customer matching / review screen** | In-flow review (Reviewer) | `sale` (renders through core) | Part B §B.9/§B.12 |
| S9 | **Order-import touchpoints** | **No dedicated screen** — two error-center extensions | `sale` extends S5 | Part B §C.14 (MBQ-26) |
| S10 | **Inventory location-mapping screen** | Dedicated config surface | `inventory` | Part C §A.2 |
| S11 | **Inventory first-push guard / confirmation** | Guarded preview→confirm flow | `inventory` (renders through core) | Part C §A.5 |
| S12 | **Inventory source-of-truth / quantity settings** | Settings sub-surface | `inventory` extends S2 | Part C §A.3/§A.4 |
| S13 | **Fulfillment log / detail + notification config + location-mismatch review** | Surfaces through S4/S5 + a settings sub-surface | `fulfillment` extends S2/S4/S5 | Part C §B.5/§B.6/§B.8 |
| S14 | **Permissions / roles visibility** | Conceptual access model (no CSV) | `core` | DEC-012 §10; Part A §J |

**[Screen blueprint proposal].** S6 (matching center) is treated as a
**reusable interactive surface pattern** invoked from the domain flows and the
error center, **not** necessarily a standalone top-level menu item — the
gap-check flagged that no accepted input establishes it as a dedicated screen.
Whether it also earns a top-level entry is left to the IA proposal (§2) and
tagged accordingly.

**[Recommendation — open, MBQ-45].** The **number** of operator surfaces is not
fully settled: whether S2/S3 are a **single role-gated surface** or an
**admin-vs-functional split** (two surfaces) is open. This inventory lists the
**logical** surfaces; §2 proposes a direction and flags the split as open.

---

## §2. Navigation / information architecture

### 2.1 Proposed top-level menu (blueprint level; XML IDs are MBQ-03)

**[Screen blueprint proposal].** A single top-level connector menu, role-gated
per §14, proposed as:

```
Shopify Connector
├── Dashboard                 (S3) — command center / operator home
├── Sync Center               (S4) — one job list across all domains
├── Error Center              (S5) — recovery + manual-review queue
├── Catalog & Matching        (S6/S7/S8) — matching center + product/customer review entry
├── Inventory
│   ├── Location Mapping       (S10)
│   └── First-Push & Sync      (S11/S12 entry)
├── Fulfillment               (S13 entry: log/detail + notification settings)
└── Configuration
    ├── Store Settings         (S2)
    ├── Roles & Access          (S14 — informational/visibility)
    └── Setup Wizard            (S1 — re-runnable)
```

**[Inference].** This realizes setup-ux Principle 5 ("command center over
scattered menus") and DEC-012 §3: the **Dashboard is the home**, and the other
surfaces are reachable both from the menu and from clickable dashboard counts.

### 2.2 Inter-screen routing (the "no dead end" contract)

**[Accepted — Part A §F.3/§G.3; DEC-012 §3 items 10–11].** Every dashboard
count is **clickable** and routes to the **filtered** Sync Center / Error
Center view for that category; a count with no path to act on it is not
acceptable. From any job/error row the operator can **Open source record**
(the related Odoo record) and **Open mapping** (the binding/mapping record).
**[Accepted — Part B §C.14 (MBQ-26)].** Error-center order entries for
`mapping missing` link **directly into the matching flow (S6)** so resolve +
retry is a two-click path. **[Screen blueprint proposal].** Routing is
**bidirectional**: connector→Odoo via "Open source record", and Odoo→connector
via **smart buttons** on the participating record (§3), so a record's sync
state and last error are reachable without leaving the record.

```
Dashboard (S3) ──count click──▶ Sync Center (S4, filtered) ──row──▶ Error Center (S5)
     │                                   │                              │
     └──exception card──▶ Error Center (S5, filtered)                   ├─▶ Open source record (Odoo)
                                                                        ├─▶ Open mapping (binding)
                                                                        └─▶ Matching center (S6) ─resolve→retry
```

### 2.3 Role-gated visibility

**[Accepted — Part A §J; DEC-012 §10].** All four roles see **one** dashboard/
sync-center/error-center; **action affordances** (trigger, retry, confirm,
resolve, edit settings) are role-gated, not the surfaces themselves. Read-only
Auditor sees everything, acts on nothing. See §14 for the capability matrix.

**[Recommendation — open, MBQ-45].** This IA is drawn as **one role-gated
surface with role-gated sections** (setup-ux Open Q#2, option A), which the
gap-check identifies as the more principle-consistent reading of "two audiences,
one product." The alternative (a separate admin surface vs functional-user
surface) remains open; **the menu tree above works under either resolution** —
under a split, the `Configuration` branch becomes the admin surface. This part
does **not** decide MBQ-45.

**[Open question — MBQ-06].** Which readiness checks gate "connected", and
**MBQ-03** (exact menu/action XML IDs) remain open; the tree is a proposed
structure only.

---

## §3. Odoo-native interaction patterns (reused vs custom)

**[Screen blueprint proposal].** This section is largely **original design
work** (the gap-check confirmed no accepted input maps screens to Odoo widget/
view conventions). It proposes which **standard Odoo 19 conventions** the
connector reuses, and where a **custom pattern** is justified, and why. Exact
view types/XML are **MBQ-03**; the config/data-model backing them is
**AR-004/AR-005** (undecided) — so these are **directions**, not bindings.

| Surface | Proposed Odoo-native pattern | Custom where / why |
| --- | --- | --- |
| Setup wizard (S1) | Multi-step wizard: transient **step UI** + `statusbar`, but connection/readiness/source-of-truth choices **persist** on the durable store-configuration record so re-running **resumes**, not restarts | Custom **readiness/test-connection panel** with per-check pass/fail rows (no native equivalent) |
| Store settings (S2) | Settings-style form with grouped notebook tabs; toggles as booleans with inline help | Custom **connection/health/token status band** (glanceable, read-only, no value read-back) |
| Dashboard (S3) | Kanban/card layout of clickable count cards | Custom **command-center card grid** fusing health + counts + timeline + reconciliation + quick actions |
| Sync center (S4) | List view with filters/group-by/sort; `statusbar`/`badge` for state | Custom **state/class-conditional row-action set** (retry only when the retry class permits) |
| Error center (S5) | Form/detail with an expandable "technical details" notebook page; **chatter** for discussion/assignment **plus a structured before/after audit trail** (§9 element 9) — distinct artifacts, not conflated | Custom **recovery panel** (reason + suggested fix + owner state + retry-policy explanation) |
| Matching center (S6) | List of candidates + selection; preview dialog | Custom **"will create N, link M, N ambiguous" preview** dialog before commit |
| Product diff (S7) | Form/diff dialog; `notebook` for fields/images/price/variants | Custom **destructive-write diff** highlighting delete-on-omit variants/images |
| Inventory location mapping (S10) | Editable list (one row per Odoo location → one Shopify Location) with domain-filtered Many2one | Custom **internal-only location filter**; **no** free-text/name inference |
| First-push guard (S11) | Wizard-style confirm dialog with a preview list | Custom **guard confirmation record** capture (preview snapshot + confirmer + source-of-truth + scope) |
| Fulfillment (S13) | List/detail through the shared job/log surfaces | Reuses S4/S5; **no** parallel fulfillment monitor (RA-013) |
| Everyday Odoo records (product / sale order / partner / picking) | **Odoo-native smart buttons** on the participating record → its binding, its related sync jobs, and its last error/exception count | Reverse of §2.2 "Open source record": a record's sync state is visible without leaving the record |

**Odoo-native affordances reused (blueprint level) [Screen blueprint proposal]:**

- **Smart buttons / bidirectional routing.** Operators live in the normal Odoo
  screens, not only the connector menu. Everyday records that participate in
  sync expose smart buttons to their connector artifacts (binding, related
  jobs, last error) — the reverse of §2.2's connector→Odoo "Open source
  record", making routing bidirectional. (No new model/action is committed —
  MBQ-01/03.)
- **Activities & chatter for manual-review routing.** A `blocked_manual_review`
  item is assigned/routed to the Reviewer role using the Odoo-native
  **activities** convention (with a due date) and its resolution discussion is
  recorded in **chatter**; the structured before/after evidence stays in the §9
  audit trail (a distinct artifact). This is the native answer to "how does a
  blocked item reach the right person" and removes any role-gated dead end
  (§9, §18 rule 3). Assignment is a convention to reuse, not an invented
  activity type.
- **Saved searches, favourites, and group-by** on the shared list surfaces
  (§8/§9), reusing the fixed §4.1 vocabularies as labels — so triage does not
  require a bespoke screen.

**Binding interaction rules (all [Accepted]):**

- **Never expose raw platform internals** (no `ir.cron` `nextcall`/model/
  scheduler fields to end users; friendly scheduling language "every N
  minutes") — setup-ux Configuration principles; vision "don't leak the
  platform"; anti-pattern A-UX-2. **[Recommendation]** basis, **[Accepted —
  Part A]** for the substrate rule.
- **Raw error/stack trace is never the primary display** (RA-016); it lives
  behind an explicit expand. **[Accepted — DEC-009]**.
- **Access is deny-by-default**; no design relies on `sudo()` to cross a
  record-rule boundary. **[Accepted — DEC-012 §10; Part A §J]**.
- **Quick actions enqueue work**; heavy sync never runs inline in the request
  (5-second webhook-ack / worker limits). **[Accepted — Part A; DEC-005]**.

---

## §4. Global screen-state model

**Every screen below is specified with all five states — no screen is designed
with only its happy path** (a Part D acceptance requirement). The connector's
job/error substrate already fixes the error and manual-review vocabulary; the
empty/loading/success states are proposed here (the gap-check flagged them as
thin in the accepted inputs).

| State | Definition (shared across screens) | Basis |
| --- | --- | --- |
| **Empty / first-run** | A guiding empty state that tells a new operator the next concrete action (never a blank grid). | **[Inference]** setup-ux Dashboard principles (C-DASH-06) — no competitor evidence, UX best-practice. |
| **Loading / in-progress** | Enqueued/`running` work shows honest progress ("queued", "running", last-updated), never a silent spinner and never a fake "real-time" claim. | **[Screen blueprint proposal]** on **[Accepted]** honest-freshness (DEC-012 §4; setup-ux Principle 4). |
| **Success / done** | An explicit completion signal (e.g. a "processed" ribbon / done count), with a link to what changed. | **[Screen blueprint proposal]** on **[Accepted]** setup-ux Principle 8 completion signal. |
| **Error** | Plain-language reason primary; technical detail behind expand; one of the fixed **16 error classes** shown as a human label; suggested fix + owner state. | **[Accepted — DEC-009; Part A §H; RA-016]**. |
| **Manual review** | Shown as one of the **6 confirmation-required sub-reasons** (never a generic "needs review"), with a resolution action gated to the Reviewer role. | **[Accepted — DEC-009; Part A §H.8; DEC-012 §5]**. |

### 4.1 Fixed vocabularies every status/monitoring screen must reuse verbatim

**[Accepted — DEC-009; Part A §D].** These are **not** re-invented by any
screen.

- **Job sources (6):** `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`. The last
  two are **read-only/preview-only** and are **not** business sync runs. A
  screen showing a job's source uses **only** these six. "Event-driven
  enqueue" is a sync-*trigger* description, **not** a job source
  (**[Open question — MBQ-62]** for the Odoo-event source classification).
- **Job states (10):** `draft`, `queued`, `running`, `succeeded`,
  `failed_final`, `skipped`, `cancelled`, `retry_waiting`, `failed_retryable`,
  `blocked_manual_review`.
- **Sync-center state filter — accepted basis is the full 10-state §D.3
  vocabulary** (Part A §G.1) **[Accepted — DEC-009; Part A §G.1]**. As a
  **[Screen blueprint proposal]**, the on-screen status filter *may* present a
  human-facing grouping (`queued`, `running`, `retry_waiting`,
  `blocked_manual_review`, `failed`, `done`, `cancelled` — where `failed`
  groups `failed_final` + `failed_retryable` and `done` = `succeeded`). This
  grouping is **presentation only** and **must still expose every accepted
  state, including `draft` and `skipped`** (as their own filter values or an
  explicit "other/system" bucket) — it never narrows the accepted 10-state
  filter. The grouping values are internal identifiers; the on-screen label
  renders as natural-language words (the raw underscored token is never shown
  to the operator; exact wording is **[Open question — MBQ-22]**).
- **Error classes (16, fixed registry, in order):** (1) Shopify throttling/
  rate-limit; (2) Shopify temporary/server/network; (3) Shopify permission/
  scope/auth; (4) Shopify userErrors/validation; (5) Odoo validation/
  configuration; (6) mapping missing; (7) ambiguous match; (8) binding
  conflict; (9) duplicate risk; (10) destructive-write guard blocked; (11)
  inventory location missing; (12) fulfillment notification confirmation
  missing; (13) financial total mismatch; (14) data shape/schema mismatch;
  (15) concurrency/race conflict; (16) unknown/system error. **No 17th class**;
  only `ambiguous match`'s applicability was widened (Part C §B.8).
- **Manual-review sub-reasons (6, the "operator confirmation required" set):**
  `ambiguous match`, `binding conflict`, `duplicate risk`, `destructive-write
  guard blocked`, `inventory location missing`, `fulfillment notification
  confirmation missing`.
- **Retry eligibility — 4 UI cases (sync center):** (a) auto-retry already in
  progress (`retry_waiting`, no button); (b) safe to retry manually now; (c)
  requires a fix first (no retry button until resolved); (d) requires a
  verification read before retry (ambiguous-outcome). Retry is **never** one
  generic button (RA-014/RA-015).

**[Open question — MBQ-22 / gap-check].** The exact **human-readable display
labels** for the 16 classes and 6 sub-reasons, and all copy, are **not fixed**
here — see §13 (copy style guide). This part fixes the **structure**, not the
strings.

---

## §5. Setup wizard (S1)

- **Purpose.** Take a merchant from nothing to a proven, safe connection
  without hand-editing server config or pasting long scope strings.
  **[Accepted — DEC-012 §1; setup-ux Principle 1/2]**.
- **Primary users.** Connector Administrator (P2). **[Accepted — DEC-012 §10]**.
- **Entry points.** First install; re-runnable from `Configuration → Setup
  Wizard`; a "finish setup" nudge on the dashboard when in `setup_incomplete`.
- **Proposed step layout (11 steps) [Accepted step set — Part A §E.1 / DEC-012
  §1; layout is a Screen blueprint proposal]:**
  1. Welcome / prerequisites (hosting disclosure: Odoo.sh/on-prem required,
     Odoo Online excluded).
  2. Store connection (store name/URL).
  3. Credential entry — **masked**; value never read back (DEC-004).
  4. Scope list presentation (present-only; verified at readiness).
  5. **Test Connection** — explicit pass/fail **with a reason**, not a silent
     spinner.
  6. **Readiness checks** — per-check pass/fail panel (candidate checks: scope
     grants, HTTPS/`web.base.url`, webhook reachability, worker/queue presence,
     credential validity).
  7. Sync direction per domain (only DEC-003-supported directions).
  8. **Source-of-truth choices — required** (product matching; price
     authority) before "ready"; neither defaults to a silent guess.
  9. Notification default — **off**, never pre-checked "on"; explicit opt-in.
  10. Inventory first-push **scheduling only** (never executes the push here).
  11. Final readiness summary.
- **Confidence-building [Screen blueprint proposal].** The wizard is where
  merchant trust is first won, so it visibly applies the confidence loop
  (setup-ux): each step closes with an explicit **"verified"** confirmation (a
  proven moment, not a silent advance), and the **final readiness summary
  (step 11) is a plain-language confidence statement** — it states, in the
  operator's words, **what the connector will and will not do now** (which
  domains sync, in which direction, notifications on/off, first-push pending) —
  not merely a pass/fail grid. Exact wording is MBQ-22.
- **Key information shown.** Per-step validity; the readiness pass/fail grid;
  what remains before "connected".
- **Primary actions.** Enter/mask credential; Test Connection; run readiness;
  choose directions/source-of-truth/notification default; schedule first-push;
  finish.
- **Blocked / guard states.** Business sync/writes stay **blocked** until setup
  is complete; `setup_readiness_check`/`export_preview_dry_run` jobs may run
  **read-only** during setup but create/update **no** business record.
- **Cross-screen links.** On finish → Dashboard (S3); first-push scheduling →
  S11; source-of-truth → S12.
- **Screen states.** *Empty:* fresh wizard at step 1. *Loading:* readiness/test
  jobs running (honest progress). *Success:* readiness all-pass → "connected".
  *Error:* a failed check shows the specific reason + fix (e.g. scope missing),
  never a raw HTTP code. *Manual review:* n/a (wizard is pre-sync).
- **Accepted-decision deps.** DEC-004, DEC-006, DEC-007 §3, DEC-012 §1, Part A
  §E.
- **Open-MBQ deps.** **MBQ-06** (essential vs nice-to-have readiness checks);
  **MBQ-05** (custom-app creation/token mechanics); **MBQ-04** (credential
  at-rest encryption — distinct from the accepted no-read-back UI guarantee);
  **MBQ-03** (wizard XML IDs); **MBQ-10** (`odoo.conf`/queue prerequisites).

**Explicit non-happy-path rule [Accepted — DEC-012 §1 item 11].** Exiting early
leaves an explicit **`setup_incomplete`** state that shows **exactly which
steps remain** (not a generic "not configured"); an incomplete inventory
first-push blocks **inventory** sync only, without blocking product/order sync.

---

## §6. Store settings (S2)

- **Purpose.** One place to see and change what the connector is doing for this
  store. **[Accepted — DEC-012 §2]**.
- **Primary users.** Connector Administrator (P2); read-visible to Operator/
  Auditor; edit gated to Admin.
- **Entry points.** `Configuration → Store Settings`; from dashboard health
  band; from the wizard's finish.
- **Key information & regions [Screen blueprint proposal over Accepted content
  — Part A §B/§I; DEC-012 §2]:**
  1. **Connection status band** — a single glanceable state. The named set
     `Connected / Setup incomplete / Disconnected / Reconnect needed` is a
     **[Screen blueprint proposal]** (Part A §B.1 marks the underlying
     connection-state vocabulary a blueprint proposal; DEC-012 §2 presents this
     wording as its store-settings UX). What is **[Accepted — DEC-004; DEC-012
     §2]** is that connection status is a single glanceable state conveyed by
     text — **never** a raw HTTP code and never colour alone.
  2. **API health** — an **honest, named** health indicator **[Accepted —
     DEC-004]** with a plain-language explanation when not normal. The specific
     three-state set (`Normal / Throttled / Degraded`) is a **[Screen blueprint
     proposal]**, not a fixed accepted enum.
  3. **Token status** — present / last-validated / optional rotation countdown;
     **never** the value **[Accepted — DEC-004; Part A §J.2]**.
  4. **Reconnect / re-authorise / disconnect** — first-class actions.
  5. **Domain enablement toggles** (product/sale/inventory/fulfillment). *Enabling*
     a domain **re-enters that domain's own first-sync/first-push guard**
     (no inherited prior consent); *disabling* stops new sync but **does not
     delete history/logs** **[Accepted — DEC-012 §2; Part A §I.4]**.
  6. **Source-of-truth & notification defaults** (edit surfaces; the inventory
     source-of-truth detail lives in S12).
  7. **Gateway → journal mapping** (S9 config; suggestion/classification only,
     no posting).
- **Primary actions.** Reconnect/disconnect; toggle domains; edit defaults;
  edit mappings.
- **Blocked / guard states.** A destructive setting change (e.g. disconnect)
  shows consequences and requires confirmation (safe-by-default, Principle 7).
  The disconnect confirmation **states the consequence for in-flight and queued
  jobs and for history/log/binding retention** — the exact retention/lifecycle
  posture is routed to **MBQ-08** (disconnect data-retention) and **MBQ-54**
  (domain uninstall/disable lifecycle) and is **not decided here**.
- **Cross-screen links.** To S1 (re-run wizard), S10/S12 (inventory), S9 config.
- **Screen states.** *Empty:* pre-setup → routes to wizard. *Loading:* health/
  token re-validation. *Success:* setting saved (explicit confirmation).
  *Error:* reconnect failure shows reason + fix. *Manual review:* n/a.
- **Open-MBQ deps.** **MBQ-45** (one role-gated settings surface vs admin/
  functional split); **MBQ-07** (feature-flag mechanism detail); **MBQ-08**
  (store-disconnect data-retention posture — directly shapes the disconnect
  confirmation copy/behaviour); **MBQ-54** (domain uninstall/disable lifecycle);
  **MBQ-03** (settings XML IDs).

---

## §7. Dashboard / command center (S3)

- **Purpose.** Answer, at a glance: **"Is everything OK? What failed and why?
  What do I do next?"** — the UX north star — and let the operator act without
  reading source or filing a ticket. **[Accepted — DEC-012 §3; setup-ux
  Principle 5 / north star]**.
- **Primary users.** Operator (P1) primarily; visible to all roles.
- **Entry points.** Top-level `Shopify Connector → Dashboard` (the home).
- **Primary answer — lead region [Screen blueprint proposal].** The dashboard
  **leads with a single plain-language answer** to *"Is everything OK?"* (a
  summary state such as "Healthy" or "N items need you"), positioned **above**
  the count cards, so the north-star question is answered before the operator
  counts anything. The nine cards elaborate that answer; they do not replace
  it. This is a layout/primacy proposal only (exact wording is MBQ-22; the
  admin-vs-functional split is MBQ-45).
- **Nine proposed cards [Accepted card set — Part A §F.1 / DEC-012 §3; grid
  layout is a Screen blueprint proposal]:**
  1. **Connection health** (store state + API health).
  2. **Last successful sync per domain** (with the mechanism label webhook/
     scheduled/manual), shown as a **state, not just a timestamp**: a sync that
     is **overdue/stalled** relative to its expected cadence surfaces as an
     exception ("connected but no recent activity"), not a reassuring bare time.
     The overdue threshold ties to reconciliation cadence and is **not decided
     here** (**MBQ-17**).
  3. **Failed jobs by severity** — split into *needs manual review* / *system
     will auto-retry* / *permanently failed* (never a single undifferentiated
     "errors: N").
  4. **Manual-review count** (`blocked_manual_review`, broken out by the 6
     sub-reasons).
  5. **Retry-waiting count** (`retry_waiting`).
  6. **First-push-pending count.**
  7. **Inventory exceptions** (location-missing / ambiguous-match / quantity-
     mismatch).
  8. **Fulfillment exceptions** (unmatched-picking / ambiguous FulfillmentOrder
     line / notification-confirmation-missing).
  9. **Duplicate/matching exceptions** (ambiguous-match / binding-conflict).
- **Fused elements [Accepted — setup-ux Dashboard principles].** The home fuses
  connection health + queue/failure counts + a recent-activity timeline +
  reconciliation status ("last synced / last reconciled") + quick actions.
- **Primary actions.** Quick actions that **enqueue** work (never run heavy
  sync inline); **every count is clickable** → filtered S4/S5.
- **Blocked / guard states.** No vanity-only metrics (every number maps to a
  health signal or a clickable next action).
- **Screen states.** *Empty/first-run:* a guided empty state ("connect a store
  to begin") **[Inference]**. *Loading:* counts refreshing. *Success:* an
  explicitly **named** healthy state (e.g. "All systems normal") — conveyed by
  text, never colour alone — with last-sync freshness; a zero-exception card
  reads "0 — all clear", not a bare number. *Error:* failed-by-severity card
  routes to the error center. *Manual review:* the manual-review card routes to
  the S5 queue filtered by sub-reason.
- **Accepted-decision deps.** DEC-005, DEC-009, DEC-012 §3, Part A §F.
- **Open-MBQ deps.** **MBQ-45** (admin vs functional dashboard split); **MBQ-17**
  (reconciliation cadence feeding "last reconciled"); **MBQ-03**.

---

## §8. Sync center / job monitor (S4)

- **Purpose.** One job list spanning **all** domains — inspect, filter, and act
  on any job. **[Accepted — DEC-012 §4; Part A §G; RA-013]**.
- **Primary users.** Operator (P1); Reviewer for review items; Auditor read-only.
- **Entry points.** Menu; every dashboard count.
- **Filters (4) [Accepted — Part A §G.1 / DEC-012 §4]:** domain (product/order/
  inventory/fulfillment); **trigger/source** (the 6 job sources); **state** (the
  full 10-state §D.3 vocabulary — the 7-value human grouping in §4.1 is a
  screen proposal that still exposes every state, incl. `draft`/`skipped`);
  **error class** (the 16, as human labels).
- **Triage affordances [Screen blueprint proposal, Odoo-native].** The sync
  center reuses Odoo-native **saved searches / favourites** and **group-by**
  (by domain / source / state / error class, reusing the §4.1 vocabularies as
  labels) and opens on a **sensible default filter** — a "needs attention" view
  (`failed_retryable` + `retry_waiting` + `blocked_manual_review`) — so an
  operator is never dropped into an unfiltered, all-domain firehose. Exact
  default wording is **MBQ-22**.
- **Bulk recovery [Screen blueprint proposal].** List-view **multi-select bulk
  actions** apply the *same* class-conditional retry logic (§4.1) to the
  selection: only the safe subset is retried, ineligible rows are reported (not
  forced) — so a systemic fix can be cleared at scale without weakening the
  per-job retry guard (RA-014/RA-015 preserved).
- **Row actions (5) [Accepted — Part A §G.3 / DEC-012 §4]:** *Retry when safe*;
  *Verify current state* (a safe verification read against Shopify, shown
  **before** any retry for ambiguous-outcome jobs); *Open source record*; *Open
  mapping*; *Cancel/supersede* (available from `draft`/`queued`/`retry_waiting`
  — "supersede" is a **[Screen blueprint proposal]** variant; plain "cancel" is
  **[Accepted]**).
- **Key information shown.** Per job: domain, source, state, error class (if
  any), operation reference (operation type + target + attempt), timestamps.
- **Retry as 4 conditional cases (see §4.1)** — the retry affordance is
  computed from the job's retry class, never a blanket button. A **terminal**
  state (`succeeded`, `failed_final`, `skipped`, `cancelled` — Part A §D.3)
  carries **no retry control**; recovery from `failed_final` is an explicit
  **re-trigger** (a new job), not a retry, so an operator is never left unsure
  what a terminal row's button does. **[Accepted — Part A §D.3 terminal states;
  Screen blueprint proposal]** for the affordance.
- **Screen states.** *Empty:* "no jobs yet" guiding text. *Loading:* live job
  progress (`queued`→`running`). *Success:* `done` rows with a completion
  signal. *Error:* `failed`/`retry_waiting` rows link to S5. *Manual review:*
  `blocked_manual_review` rows show the specific sub-reason and route to S5/S6.
- **Accepted-decision deps.** DEC-005, DEC-009, DEC-011, DEC-012 §4, Part A §G.
- **Open-MBQ deps.** **MBQ-62** (Odoo-event-triggered source label for
  inventory-push/fulfillment-create rows); **MBQ-16/18** (retry/cron constants —
  affect displayed "next attempt"); **MBQ-03**.

---

## §9. Error center / recovery + manual-review queue (S5)

- **Purpose.** Make **every failure a recovery surface, never a dead end.**
  **[Accepted — DEC-012 §5; setup-ux Principle 6; vision non-negotiable #2]**.
- **Primary users.** Operator (fixable/retryable); **Reviewer** (confirmation-
  required manual-review items); Auditor read-only.
- **Entry points.** Menu; dashboard failure/exception cards; sync-center rows.
- **Required elements per entry (9) [Accepted — Part A §H.1–§H.9 / DEC-012 §5]:**
  1. **Human-readable reason** (primary; **never** a code/stack trace as the
     default display — RA-016).
  2. **Expandable technical detail** (raw error/response + class code + job/
     operation IDs) behind an explicit expand.
  3. **Suggested fix** (a concrete next step).
  4. **Owner / action state** — *waiting on system* (auto-retry) / *waiting on
     operator* (manual fix or confirm) / *resolved*.
  5. **Related Odoo record** link.
  6. **Related Shopify record** reference (even when the op failed before a
     Shopify object existed).
  7. **Retry-policy explanation** (one line: why it will/won't auto-retry).
  8. **Specific manual-review sub-reason** (one of the 6), never generic.
  9. **Audit trail** — attempted / actually written / skipped-by-which-rule /
     who confirmed, with **before/after** values for destructive ops.
- **Manual-review queue.** The `blocked_manual_review` items form a Reviewer
  work queue keyed off the 6 sub-reasons; resolution is a **Reviewer-role**
  action (`customer_match_review` and the domain equivalents — proposed names
  only), auditable.
- **No dead end under role gates [Screen blueprint proposal].** When the viewing
  role cannot resolve an item (e.g. an Operator on a confirmation-required
  item — §16), the surface still shows a next action: it names **whose** action
  it awaits and offers to **route/assign** it to that role, using the
  Odoo-native activities/assignment convention (§3) — never a silent dead end
  (§18 rule 3). This holds under either MBQ-45 resolution.
- **Root-cause grouping & group-by [Screen blueprint proposal].** Entries
  sharing one root cause are **grouped for visibility** so the operator sees the
  cause once (e.g. "N orders blocked by 1 missing product mapping") rather than
  N identical rows; operators may also **group by** sub-reason or owner/action
  state. Resolution still follows the per-item retry/confirmation rules (§4.1);
  grouping is presentation, not bulk auto-resolution, and one bad record never
  blocks the batch.
- **Order-import extensions (S9) — required, see §10.**
- **Screen states.** *Empty:* an affirmative "no open errors" state. *Loading:*
  re-checking an item's live state (Verify). *Success:* an item moves to
  *resolved* with its audit trail. *Error:* the entry itself (this is the error
  surface). *Manual review:* the sub-reason-keyed queue.
- **Accepted-decision deps.** DEC-009, DEC-011, DEC-012 §5, Part A §H; RA-016.
- **Open-MBQ deps.** **MBQ-22** (exact reason/fix copy); **MBQ-13** (stale-
  binding review detail); **MBQ-03**.

---

## §10. Order-import touchpoints (S9) — no dedicated screen

**[Accepted — DEC-014; Part B §C.14 (MBQ-26)].** There is **no dedicated
order-import screen**, and none is authorized or required. Order-import operator
work is handled by the shared sync center (S4) and error center (S5) — **on the
condition** that S5 carries **two order-specific extensions of the existing
error-center contract** (both are **required deliverables of this blueprint**,
not new surfaces):

1. **Inline financial-evidence breakdown.** A `financial total mismatch` entry
   renders, inline in its error-center detail, the specific breakdown: **Shopify
   total vs. computed Odoo total**, per component — **lines / tax / shipping /
   discount** (computed as Σ line totals + tax evidence + shipping evidence −
   discount evidence, compared to Shopify's reported total). **[Accepted — Part
   B §C.14 item 1 / §C.8]**. Exact Shopify total field and tolerance are
   **[Open question — MBQ-56]** — the screen shows the breakdown structure, not
   an invented tolerance number.
2. **Direct matching-flow links.** A `mapping missing` entry for
   order-blocked-on-product or order-blocked-on-customer-ambiguity links
   **directly into the matching flow (S6)** so *resolve the binding → retry the
   order* is a **two-click path**. **[Accepted — Part B §C.14 item 2]**.

**Routing precision (must not be flattened) [Accepted — Part B §C.13; DEC-014
point I]:** an unmatched-product **whole-order hold** = `mapping missing` =
`failed_retryable` ("manual fix then retry") — **not** `blocked_manual_review`;
a **total mismatch** = `financial total mismatch` = its **own** "conservative,
never silent" posture (Part A §D.5.5) — **not** one of the 6 confirmation-
required sub-reasons. A screen must never label a total mismatch or an unmatched
product as a confirmation-required review. Order **edits/cancellations/refunds**
are **evidence-refresh-only** (Part B §C.12; DEC-014 point J) — a screen must
**never** offer to edit/re-apply sale-order lines/totals/fulfillment from a
Shopify order edit.

---

## §11. Matching / duplicate-prevention center (S6)

- **Purpose.** Prevent unsafe creates/duplicates and let an operator resolve
  ambiguous matches — for products/variants and customers — with a
  preview-before-commit. **[Accepted — DEC-006; DEC-012 §6; Part B §A.9/§B.9]**.
- **Primary users.** Operator (product/variant matching); **Reviewer** (customer
  ambiguous/duplicate confirmation).
- **Entry points.** From product/customer flows (S7/S8); from error-center
  `mapping missing`/`ambiguous match` entries (two-click resolve→retry).
- **Three distinct states — must stay separate [Accepted — DEC-006/DEC-009;
  DEC-012 §6 item 8]:** **Unmatched** (no candidate; offer create subject to
  the domain guard, or manual match); **Ambiguous** (>1 plausible candidate →
  manual review, **never** an automatic guess); **Duplicate risk** (a create
  would likely duplicate → blocked pending confirmation). Not folded into one
  generic "needs attention".
- **Duplicate-prevention preview [Accepted].** Before any create/bind, a
  **blocking synchronous preview** — "will create N, link M, N ambiguous" —
  for **interactive/batch** flows. Automated per-record paths use the Part A
  §A.2/§B.2 **pre-create gate** instead; retrospective sync-center/dashboard
  display of an automated job is **audit/log only — never a preview substitute**
  (do not present it as satisfying "no blind create").
- **Match-key priority [Accepted — DEC-006; RA-006].** existing binding → SKU/
  internal reference → barcode → email/customer key (customers only) → manual
  match. **Name is advisory only, never an automatic key** (a name/similarity
  hint may be shown during manual match but never auto-binds). Customer Phase 1:
  **email is the sole automatic key** beyond an existing binding (MBQ-31).
- **Key information shown.** Candidate list with the match key that produced
  each; binding status (active / stale / manually_overridden; a "review" state
  is a **[Screen blueprint proposal]**); binding audit fields (matched-by,
  matched-at, source strategy, key used).
- **Screen states.** *Empty:* "nothing to match". *Loading:* candidate search.
  *Success:* preview confirmed, bindings created (audit recorded). *Error:*
  unresolved diff → skip/manual review. *Manual review:* ambiguous/duplicate
  items queued to the Reviewer.
- **Open-MBQ deps.** **MBQ-13** (stale/recreated review detail); **MBQ-29**
  (customer fallback granularity); **MBQ-03**.

---

## §12. Product preview / diff screen (S7)

- **Purpose.** Show exactly what a product export/update will do **before** any
  write, and block destructive writes without confirmation. **[Accepted — DEC-003/
  004/007; Part B §A.9/§A.11/§A.16]**.
- **Primary users.** Operator (P1).
- **Entry points.** Manual export/update trigger (S6/product flow); a
  `product_export_preview` dry-run (maps to `export_preview_dry_run`, may run in
  setup).
- **Five preview/review states — every implementation must support [Accepted
  state set — DEC-012 §7; Part B §A.16]:**
  1. **To create** — no candidate found; will create pending guard checks.
  2. **To update** — bound; **diff rendered** (fields / images / price /
     variants).
  3. **To skip** — ambiguous/unresolved; **reason shown, never guessed**.
  4. **Blocked** — the destructive-write guard would delete/omit data without
     confirmation, **or** the price source-of-truth is unset.
  5. **Draft-pending-publish** — created/updated in Shopify but not yet
     published to any sales channel.
- **Destructive-write guard [Accepted — Part B §A.11; DEC-007 §2].** Before any
  full-state/destructive write, the diff renders which fields change, which
  images are replaced/removed, price changes, and **which variants a `productSet`
  write would DELETE by omission**. No flag/setting bypasses it (Part A §I.5).
- **Draft-first [Accepted — Part B §A.10].** A first export creates as
  draft/unpublished and does **not** auto-publish; publish is an explicit,
  channel-selecting action. (Exact draft/publish mechanism = **MBQ-25**.)
- **Primary actions.** Review diff; confirm create/bind/write; confirm the
  destructive write; confirm publish to selected channel(s).
- **Screen states.** *Empty:* nothing selected. *Loading:* diff computing.
  *Success:* write done → draft-pending-publish or published; binding confirmed.
  *Error:* Shopify userErrors surfaced plainly. *Manual review:* ambiguous items
  route to S6 / `blocked_manual_review`.
- **Open-MBQ deps.** **MBQ-23** (variant mutation strategy), **MBQ-24** (media
  delete-on-omit), **MBQ-25** (draft/publish mechanism), **MBQ-55** (binding
  model names), **MBQ-22** (copy), **MBQ-03**.

---

## §13. Customer matching / review screen (S8)

- **Purpose.** Match imported customers safely, resolve ambiguity, and never
  invent PII. **[Accepted — DEC-006/DEC-014; Part B §B]**.
- **Primary users.** **Reviewer** (`customer_match_review`); Operator for
  ordinary imports.
- **Matching [Accepted — Part B §B.3/§B.13, MBQ-31].** existing binding →
  **email** (sole automatic key) → manual review; phone/name advisory-only.
- **No-PII fallback [Accepted — Part B §B.7, partially MBQ-29].** A single,
  clearly-flagged fallback partner per store (proposed name direction only) is
  used **only** when Shopify genuinely withholds all PII — carrying a visible
  auditable marker so it is **never** indistinguishable from a real matched
  customer in any view. Never used for an ordinary matching failure.
- **Screen states.** *Empty:* nothing to review. *Loading:* candidate lookup.
  *Success:* matched/bound with audit. *Error:* data-shape issue → fix-then-retry.
  *Manual review:* ambiguous/duplicate → Reviewer confirmation.
- **Open-MBQ deps.** **MBQ-29** (fallback granularity), **MBQ-31** detail,
  **MBQ-55**, **MBQ-03**.

---

## §14. Inventory screens (S10 / S11 / S12)

### 14.1 Location-mapping screen (S10)

- **Purpose.** An explicit, non-inferred **Odoo location ↔ Shopify Location**
  mapping (each Odoo location → exactly one Shopify Location). **[Accepted —
  DEC-010; Part C §A.2]**.
- **Users.** Administrator.
- **Key rules.** Only **`internal`** Odoo location types are offered as mapping
  candidates (vendor/customer/virtual/transit never offered)
  **[Screen blueprint proposal on Accepted internal-only intent; filter
  mechanism = Open question]**; **no name-based inference**; at least one mapped
  pair required before any write; structurally multi-location-capable even for a
  single-location merchant.
- **Blocked states.** A missing mapping → **`inventory location missing`**
  (a confirmation-required sub-reason; write held, never guessed); ambiguous
  candidates → `ambiguous match`. `INVENTORY_LEVELS_DISCONNECT` for a mapped
  location routes to the same handling, not a silent skip.
- **Screen states.** *Empty:* "no locations mapped — map at least one".
  *Loading:* fetching Shopify Locations. *Success:* mapped pair saved. *Error:*
  unmapped/ambiguous surfaces to S5. *Manual review:* location-missing/ambiguous.
- **Open-MBQ deps.** **MBQ-01/02** (model/field names), **MBQ-03**.

### 14.2 Inventory first-push guard / confirmation (S11)

- **Purpose.** Guard the **first** Odoo→Shopify inventory write behind a preview
  and explicit confirmation. **[Accepted — DEC-007 §4; DEC-010; Part C §A.5]**.
- **Required elements (all mandatory, unweakened) [Accepted]:** a mapped Shopify
  location; a **preview** of SKU/variant/location quantities that will be
  written; **explicit operator confirmation** of that preview; a **recorded
  source-of-truth decision**; and the ability to **skip/manual-match** ambiguous
  items rather than guess. **No flag bypasses it** (Part A §I.5).
- **Confirmation record [Accepted concept — Part C §A.5; schema = MBQ-38].**
  Persists the preview snapshot rows, the confirming operator + timestamp, the
  source-of-truth in force, and the scope (which mapped pair(s) it covers).
- **[Recommendation — open, MBQ-33].** The guard is drawn to fire at the
  granularity of **one mapped (Odoo location ↔ Shopify Location) pair** — adding
  a new mapped pair later re-enters its own guard. This is a **recommendation,
  not decided**; the screen is designed so the guard's attach-point can be
  per-store or per-pair without redesign (a preview + confirm + record either
  way).
- **Blocked states.** An unconfirmed guard → `destructive-write guard blocked`
  (confirmation-required).
- **Screen states.** *Empty:* "no first-push pending". *Loading:* building the
  preview. *Success:* confirmed → push enqueued; confirmation record written.
  *Error:* unmapped/ambiguous items surfaced. *Manual review:* guard-blocked
  until confirmed.
- **Open-MBQ deps.** **MBQ-33** (granularity), **MBQ-38** (record schema),
  **MBQ-03**.

### 14.3 Inventory source-of-truth / quantity & apply-mode settings (S12)

- **Purpose.** Record the inventory source-of-truth and quantity semantics, and
  govern ongoing apply behaviour. **[Accepted — DEC-010; Part C §A.3/§A.4/§A.7]**.
- **Key rules [Accepted].** Default write target is Shopify **`available`**;
  **`committed` is never written** and never a selectable target (RA-018);
  **`on_hand`** is allowed but **not** an equal default.
- **[Open question — MBQ-35 / MBQ-32].** Whether `on_hand` is exposed as a Phase-1
  UI choice **at all** is undecided; **if** shown it must carry the six-state-sum
  warning (`available + committed + reserved + damaged + safety_stock +
  quality_control` — the composition cited as an official Odoo fact in **Part C
  §A.4**) and explicit justification — the screen must **not** present
  it as a settled, equally-weighted option. The underlying Odoo quantity source
  (`product.product.free_qty` vs `stock.quant.available_quantity` — verified
  **non-equivalent**) is **not** decided (MBQ-32); the settings screen exposes a
  **recorded decision**, not an invented default.
- **[Recommendation — open, MBQ-34].** Ongoing (post-first-push) writes are drawn
  as **review-then-apply** (a preview before each apply), consistent with DEC-003
  (auto-apply not accepted as default). This is a **recommendation, not decided**;
  the ongoing-writes surface is designed so the apply-mode toggle can be set to
  review-then-apply **or** auto-apply-where-safe without redesign. (This part
  does **not** adopt setup-ux anti-pattern #8's auto-apply improvement as a
  decision — it defers to the open MBQ-34.)
- **Screen states.** *Empty:* source-of-truth unset → blocks writes. *Loading:*
  n/a (settings). *Success:* decision recorded (auditable). *Error:* invalid
  combination surfaced. *Manual review:* n/a.
- **Open-MBQ deps.** **MBQ-32**, **MBQ-34**, **MBQ-35**, **MBQ-01/02**, **MBQ-03**.

---

## §15. Fulfillment screens (S13)

Fulfillment reuses the shared job/log surfaces (S4/S5) — **no** parallel
fulfillment monitor (RA-013) — plus a notification settings sub-surface and a
location-mismatch review that routes through the error center.

- **Fulfillment log / detail [Accepted — Part C §B.13; DEC-011].** Each entry
  shows the related sale order, picking, Shopify order, FulfillmentOrder/
  Fulfillment ID, tracking number/carrier, and the **notification setting
  (requested/suppressed)**; blocked/failed entries carry a human-readable reason
  and suggested next action — **no raw stack trace** as the primary UX. The
  **matched unit** is shown together (order / FulfillmentOrder / line / quantity
  / location), not as separate unlinked facts.
- **Tracking write-back [Accepted field facts — Part C §B.5; MBQ-39 resolved].**
  Sourced from Odoo `stock_delivery` fields `carrier_id` / `carrier_tracking_ref`
  / `carrier_tracking_url`; a tracking-only update is **visibly distinct** from a
  fulfillment-creation event and never creates a second fulfillment.
  **[Open question — MBQ-60]:** whether `stock_delivery`/`delivery` is a required
  dependency (and what tracking write-back does if absent) — the screen must not
  assume the fields exist.
- **Notification config [Accepted — DEC-007 §5; DEC-011; RA-009].** Default
  **off**; a global/per-store default at minimum; the decision is **persisted on
  the job at enqueue time and never re-read on retry**; every log records
  requested/suppressed. A missing required confirmation → `fulfillment
  notification confirmation missing` (confirmation-required).
  **[Recommendation — open, MBQ-41]:** a global/per-store default is drawn as
  sufficient for Phase 1 with per-order override deferred — **not decided**; the
  settings surface is designed so a per-order override can be added later without
  redesign.
- **Location-mismatch review [Accepted at blueprint level — Part C §B.8;
  MBQ-42].** A live FulfillmentOrder `assignedLocation` read is authoritative for
  the operation; the core Location reference is naming/display only. A
  deterministic location mismatch routes to the **widened `ambiguous match`
  class** (no 17th class) and blocks for confirmation — surfaced in the error
  center like any other confirmation-required item.
- **Trigger & block-if-ambiguous [Accepted — DEC-011; RA-023].** A validated
  `stock.picking` is the only trigger; a picking that cannot be cleanly matched
  to exactly one FulfillmentOrder's open line items **blocks for manual review**,
  never auto-guessed. Ambiguous-outcome calls get a **verification read before
  any retry** (RA-014).
- **Screen states.** *Empty:* "no fulfillments yet". *Loading:* fulfillment
  create/tracking in progress. *Success:* fulfillment created (+ tracking shown;
  notification requested/suppressed recorded). *Error:* Shopify userErrors /
  unmatched picking surfaced. *Manual review:* block-if-ambiguous, location
  mismatch, notification-confirmation-missing.
- **Open-MBQ deps.** **MBQ-40** (backorder wizard copy), **MBQ-41**, **MBQ-42/43**,
  **MBQ-60**, **MBQ-61** (lifecycle/hold webhooks — future hold-aware UX),
  **MBQ-62** (event-triggered source label), **MBQ-03**.

---

## §16. Permissions / roles visibility (S14)

- **Purpose.** Make the four conceptual roles and their capabilities visible;
  **conceptual only — not** Odoo security groups, `ir.model.access` rows, or
  CSVs. **[Accepted — DEC-012 §10; Part A §J]**.
- **Four roles [Accepted names — Part A §J.1] (proposed group directions only,
  MBQ-44):**

| Role (persona) | Can do | Cannot do |
| --- | --- | --- |
| **Connector Administrator** (P2) | Setup wizard; store settings; masked credential status; enable/disable domains; source-of-truth & notification defaults; mappings | — |
| **Connector Operator** (P1) | Manual syncs; dashboard/sync-center/error-center; retry **safe** jobs; open records; run previews | Change settings/credentials; resolve confirmation-required review |
| **Connector Reviewer / Manual Review Owner** | Resolve `blocked_manual_review` items (the 6 sub-reasons) | Change settings; general retry/trigger (Reviewer is approval-focused — MBQ-47 accepted) |
| **Read-only Auditor** (P3) | View everything | Trigger, retry, confirm, or change anything |

- **Reading this table [Screen blueprint proposal].** Capabilities are stated in
  plain language for a non-technical reader; internal state names (e.g.
  `blocked_manual_review`) appear only as parentheticals.
- **Hierarchy [Accepted — DEC-013], in plain terms.** Every role also has the
  Auditor's read-only visibility; the **Administrator** additionally has the
  **Operator's** and **Reviewer's** actions; **Operator** and **Reviewer** are
  peers with different action sets (an Operator runs and retries safe work; a
  Reviewer confirms/resolves manual-review items).
- **[Recommendation — open, MBQ-45].** Whether the four map **1:1** to Odoo
  groups, and whether the operator UI is one role-gated surface or an admin/
  functional split, is **not decided**. Persona **P4** (partner/integrator) is
  intentionally unmapped to a runtime role.
- **[Open question — MBQ-44].** Exact groups / `ir.model.access` / record rules
  are implementation-planning artifacts (deny-by-default; no `sudo()` across
  record-rule boundaries).

---

## §17. UX copy & error-message style guide (structure, not final copy)

**[Open question — MBQ-22].** Exact user-facing copy for every screen, error
reason, suggested fix, and confirmation dialog is **not decided here** — this is
a **style guide**, and every quoted example is **illustrative, not mandated**.
DEC-012 §5 and setup-ux/vision all explicitly defer exact wording.

**Style rules [Accepted — DEC-009; DEC-012 §5; setup-ux Principle 8; RA-016]:**

1. **Plain-language reason first.** Every error's primary line is a plain
   sentence a non-developer understands (illustrative: "Shopify rejected this
   update: the SKU no longer exists on this product"). The code/class/stack
   trace lives behind an explicit expand — **never** the default.
2. **Every error carries a suggested fix** (a concrete next step) and an
   **owner/action state** (waiting on system / operator / resolved).
3. **Name the specific manual-review sub-reason**, never a generic "needs
   review".
4. **Honest status language.** No "real-time" on a cron/queue model; name the
   mechanism (webhook/scheduled/manual) and show "last synced / last
   reconciled". Health states are named + explained when not normal.
5. **Speak the user's language.** "Every 15 minutes", not `nextcall`; never
   expose raw `ir.cron`/Odoo internals (A-UX-2).
6. **Reason codes are human** (illustrative: "SKU not found", "tax not found",
   "customer missing"), reused consistently across dashboard/sync-center/
   error-center.
7. **Confirmation copy states consequences** for destructive/irreversible
   actions (delete-on-omit variants, disconnect, publish-to-live).
8. **Status is never colour (or icon) alone.** Every status, badge, chip, or
   pill carries a **text label plus a severity/owner word** (e.g. "Failed",
   "Needs review", "Healthy") that stays unambiguous with colour removed;
   colour/icon is reinforcement only. Zero/healthy states are affirmatively
   labelled ("0 — all clear"), never a bare number or a colour-only cue.
9. **Primary label is plain, never a raw token or API term.** The human display
   label for the 10 states, 16 error classes, and 6 sub-reasons must not surface
   an internal token (`retry_waiting`) or a developer/API term ("userErrors",
   "schema mismatch") as the **primary** operator-facing word; the technical
   term may appear only in the expandable technical detail. (Exact labels are
   MBQ-22.)
10. **Voice is calm, plain, and reassuring** — professional, never jokey or
    alarmist: success states reassure, error states stay factual and
    non-blaming. (All examples in this guide are illustrative; exact copy is
    MBQ-22.)

---

## §18. Cross-screen consistency rules

**[Screen blueprint proposal, grounded in the Accepted substrate]:**

1. **One shared surface per concern** — a single dashboard, sync center, error
   center, and manual-review queue; domains contribute, never fork (RA-013).
2. **One vocabulary everywhere** — the same 6 sources / 10 states (7-value UI
   collapse) / 16 classes / 6 sub-reasons appear identically on every screen.
3. **No dead ends** — every count/exception routes to a filtered, actionable
   view; every failure has a next action.
4. **Preview before write** — every create/bind/destructive/first-push write is
   preceded by a preview + explicit confirmation; automated paths use the
   pre-create gate, and their retrospective display is audit-only.
5. **Guards are unbypassable** — no flag/setting/role removes the destructive-
   write, first-push, total-check, or notification guards.
6. **Honest by default** — status, freshness, and health are truthfully
   labelled; the confidence loop **stage → inspect → process → verify (open the
   record) → log** is available on sync surfaces.
7. **Role-gated affordances, shared visibility** — all roles see the surfaces;
   actions are gated.
8. **Never colour alone; plain labels** — status is conveyed by text + a
   severity/owner word, never colour or icon alone (§17 rule 8); primary labels
   are plain language, never raw tokens or API terms (§17 rule 9).
9. **Keyboard-friendly action order** — the primary **safe** action comes first
   in tab/action order; **destructive/irreversible** actions come last and are
   **never** the default keyboard focus; every actionable surface is operable by
   keyboard with a visible focus state.

---

## §19. Premium UI/UX acceptance checklist

**The bar an operator-facing surface must clear before it may be implemented.**
Grounded in `product-vision.md` and `setup-ux-principles.md` — both of which
"decide nothing", so every item is a **recommendation-level input** (labelled
accordingly), reconciled against the accepted DEC-003 MVP scope. This checklist
is a **[Screen blueprint proposal]**; ChatGPT sets the final bar.

**A. Correct & safe (maps to vision non-negotiables #1/#6, premium bar "Safe"):**
- [ ] No destructive/first-push/full-state write without a preview + explicit
      confirmation; delete-on-omit is shown. **[Accepted guard]**
- [ ] `committed` never writable; guards unbypassable by flag/role.
- [ ] Platform rules respected on-screen (no read-back of credentials; honest
      throttle status).

**B. Recoverable (non-negotiable #2, premium bar "Recoverable"; Principle 6):**
- [ ] Every failure shows reason + suggested fix + owner state + specific
      sub-reason; retry is class-conditional (4 cases), never blanket.
- [ ] Every failure has a next action; no dead ends; one bad record never
      blocks the batch.

**C. Observable & honest (non-negotiable #3, premium bar "Observable & honest";
Principles 4/5/8):**
- [ ] The three operator questions ("Is everything OK? What failed and why?
      What do I do next?") are answerable from the dashboard in one glance.
- [ ] Freshness/mechanism labelled honestly; "last synced / last reconciled"
      visible; no "real-time" overstatement; no vanity metrics.
- [ ] Logs are human-readable, per-record, reason-coded; raw detail behind an
      expand.

**D. Approachable then powerful (premium bar "Approachable then powerful";
Principles 1/2/3):**
- [ ] Guided setup with a pass/fail readiness check; no server-config hand-edit
      or long scope paste to reach a working connection.
- [ ] Opinionated defaults + inline help on every jargon field; advanced power
      opt-in; empty/first-run states guide the next action.

**E. Role-aware & modular (Principles 10/11; premium bar "Modular"):**
- [ ] One product, two audiences via role-gated sections (not two apps); only
      enabled domains' UI is shown.
- [ ] No raw Odoo internals leaked to end users.

**F. Evidenced & documented (non-negotiable #7, premium bar "Evidenced &
documented"; Principle 12):**
- [ ] In-product help mirrors the actual screens/jargon; honest limitation
      disclosure; a self-test/readiness surface exists for evaluation.

**G. Anti-patterns explicitly avoided (setup-ux "Anti-patterns", as negative
checks — recommendations, not §10 rejections):**
- [ ] No opaque/binary status; no raw `ir.cron` exposure; no toggle-dense
      jargon screen without defaults; no blind mappings; no email-only/reason-
      less errors; no irreversible "Force Done" without strong guards; no heavy
      work inside the webhook request.

**H. Accessible & clear (premium is not premium if it is not accessible;
maps to setup-ux Principles 8/10 and §17 rules 8–10):**
- [ ] **No status is conveyed by colour or icon alone** — every badge/chip/pill
      carries a text label + severity word, unambiguous with colour removed.
- [ ] **Primary labels are plain language**, never raw state tokens or API/dev
      terms; the technical term appears only behind the "technical detail"
      expand.
- [ ] **Every actionable surface is keyboard-operable** with a visible focus
      state; the primary safe action precedes destructive actions in order, and
      a destructive control is never the default focus.
- [ ] **Every destructive/irreversible action** has an explicit, labelled
      confirmation that states its consequences.
- [ ] **Roles and their capabilities are legible to a non-technical reader**
      (plain-language capability descriptions; internal state names only as
      parentheticals).

---

## §20. Open questions this part carries or surfaces

This part **proposes to partially resolve MBQ-53 at screen-design level**
(MBQ-53 stays open until DEC-016 is accepted) and **routes**, without deciding,
the following screen-relevant open rows to their existing owners. **It adds no new MBQ row** — the screen design consumes existing
questions rather than surfacing genuinely new ones.

| Row | Why it constrains screens | Owner / status |
| --- | --- | --- |
| **MBQ-45** | One role-gated surface vs admin/functional split; roles→groups 1:1 | Implementation planning — **open**; Part D proposes a direction, does not decide |
| **MBQ-22** | Exact copy/wording for all screens/errors | Later UI-design pass — **open** |
| **MBQ-03** | Exact view/menu/action XML IDs | Implementation planning — **open** |
| **MBQ-44** | Exact security groups / access CSVs / record rules | Implementation planning — **open** |
| **MBQ-06** | Which readiness checks gate "connected" | ChatGPT / impl-planning — **open** |
| **MBQ-33 / MBQ-34 / MBQ-41** | First-push granularity; ongoing apply-mode; per-order notification override | ChatGPT — **open recommendations**; screens accommodate either resolution |
| **MBQ-35 / MBQ-32** | `on_hand` UI exposure; Odoo quantity source | ChatGPT / impl-planning — **open** |
| **MBQ-08 / MBQ-54** | Disconnect data-retention; domain uninstall/disable lifecycle | ChatGPT — **open**; shapes settings/disconnect behaviour |
| **MBQ-25 / MBQ-23 / MBQ-24 / MBQ-55 / MBQ-56 / MBQ-13** | Product/customer/order screen detail | as registered — **open** |
| **MBQ-60 / MBQ-61 / MBQ-62 / MBQ-63** | `stock_delivery` dependency; hold webhooks; event source label; inventory webhook payload | as registered — **open** |
| Primary MVP persona (RB-13) | Which surface/persona leads | ChatGPT — **open** (vision) |

---

## §21. What this part does not decide

- Any Odoo view XML, widget binding, menu/action XML ID, model, or field
  (MBQ-01/02/03).
- Any security group, `ir.model.access` row, CSV, or record rule (MBQ-44).
- Exact user-facing copy or error strings (MBQ-22).
- The admin-vs-functional surface split or roles→groups mapping (MBQ-45).
- Any still-open recommendation (MBQ-33/34/41/35/06) — screens are designed to
  accommodate either resolution.
- Anything already deferred by DEC-003 (order edits/refunds/returns, multi-store,
  multi-package/multi-location fulfillment automation).

## §22. Implementation remains blocked

**The Master Blueprint does not authorize code.** No part of this document —
proposed or, if later accepted, accepted — creates or permits any Odoo module,
model, view, menu, controller, security file, manifest, test, CI workflow, or
dependency change. The no-code gate (`CLAUDE.md` §4–§5) remains in force.
Per `master-blueprint.md` *Criteria for when implementation may later be
opened*, implementation of any operator-facing screen additionally requires
**this Part D to be accepted by ChatGPT** — and even then, a **separate**
explicit implementation-gate approval is still required.
