# Implementation Gate Readiness Audit — Post DEC-020

> **Accepted audit** for the premium **Odoo 19 ↔ Shopify Connector**,
> prepared after ChatGPT accepted
> [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
> (MBQ-64/MBQ-65, decision/posture level) on **2026-07-04**, and after PR
> #83 merged into `Shopify-connector` at merge commit
> `b27f842425043e6320d8e168a1208345f6fcab12`. Proposed via PR #84 and
> **accepted by ChatGPT on 2026-07-05** (see "Acceptance" below). This is
> **not** the implementation-gate-opening act itself — it is the readiness
> check that had to precede any proposal to perform that act, and its
> acceptance does not perform that act either. Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md)
> ("Criteria for when implementation may later be opened"),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (full MBQ register, reviewed row by row below),
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
> (Part E's own gate checklist and MBQ decision plan, restated and updated
> below),
> [`quality-feedback-loop.md`](./quality-feedback-loop.md) (§8, §10, §11).
> Companion review-log entry:
> [`architecture-review-log.md`](./architecture-review-log.md) (**AR-018**,
> Accepted by ChatGPT).

## Status

- **Accepted by ChatGPT on 2026-07-05.**
- **Documentation-only.**
- **Audit-only.**
- **Does not open the implementation gate.**
- **Does not authorize implementation.**
- **Does not create implementation tasks.**
- **Implementation remains blocked.**
- **Built after DEC-020 acceptance** (2026-07-04), starting point PR #83
  merge commit `b27f842425043e6320d8e168a1208345f6fcab12` into
  `Shopify-connector`; proposed via PR #84, accepted on the same PR.
- **This audit does not modify DEC-003 through DEC-020, does not modify
  `../04-decisions/README.md`, and does not change any MBQ row's
  status** — every classification below is a **reading** of the register
  as it stands, not an edit to it. Where this audit's own reading differs
  from a stale restatement elsewhere in the repo (see §2's "documentation
  currency" note), it says so explicitly rather than silently correcting
  the stale document. **This remains true after acceptance** — accepting
  this audit's findings does not itself edit the register, DEC-003
  through DEC-020, or `../04-decisions/README.md`.

## Acceptance

**ChatGPT accepted this audit on 2026-07-05.**

- **Accepted verdict:** READY ONLY FOR A VERY LIMITED
  IMPLEMENTATION-PLANNING SPRINT, NOT CODE — unchanged from §9 below.
- **Audit acceptance does not open the implementation gate.**
- **Audit acceptance does not authorize implementation.**
- **Audit acceptance does not create implementation tasks.**
- **Implementation remains blocked.**
- **No MBQ row status is changed by this acceptance.**
- **No DEC-003 through DEC-020 is changed by this acceptance.**
- **Accepted next session:** a single, documentation-only
  **naming/core-schema implementation-planning artifact** addressing
  MBQ-01 (model names), MBQ-02 (field names/types), MBQ-04 (credential
  storage decision or explicit slice-1 descope), MBQ-07 (feature-flag/
  settings schema), MBQ-16 (retry-count/backoff constants), MBQ-19
  (job/log model shape), MBQ-20 (operation-level idempotency key schema),
  MBQ-21 (serialization-guard mechanism), MBQ-44 (core access CSV/
  record-rule planning), MBQ-45's residual (group XML IDs), and MBQ-62's
  residual (`odoo_event` trigger-origin implementation mechanics) — this
  matches, without change, §6/§7's own recommendation below. **This next
  session is not code and not the gate-opening act** — it produces
  planning documentation only.
- **On Criterion 1 (§3):** ChatGPT accepts this audit's strict, conservative
  reading of Criterion 1 (blueprint parts accepted) as **non-blocking** —
  the criterion passes for the core-substrate-only scope this audit and
  the accepted next session both target, and its own UI-scoped partial-pass
  caveat does not change what actually decides readiness here. The
  **decisive** blockers remain Criterion 2 (implementation-blocking
  open questions, eleven rows unresolved), Criterion 3 (the explicit
  gate-opening act itself, not yet performed), and Criterion 4 (no
  implementation task has yet been written to the CLAUDE.md §9 template).
  Criterion 1's conservative framing is accepted as-is, not weakened, and
  is simply not where the readiness gap actually lies.

## 1. Purpose

DEC-003 through DEC-020 and Master Blueprint Parts A–E are now all
accepted. AR-002 through AR-017 are all accepted. MBQ-62 is resolved at
decision/semantic-classification level (DEC-019); MBQ-64 and MBQ-65 are
resolved at decision/posture level (DEC-020). The broad research and
architecture-decision phase this project's governance contract
(`CLAUDE.md` §4, "research-first rule") describes is, in substance,
largely complete: every domain (core, product, customer, order, inventory,
fulfillment, UI/UX) has an accepted blueprint, and the currency and
product-webhook residuals the PR #78 audit originally flagged as
untracked gaps are now decided at posture level.

Before any code is written, `master-blueprint.md`'s own "Criteria for when
implementation may later be opened" require a check that has not yet been
performed anywhere in this repository: a **row-by-row read of exactly
which open MBQs still block which piece of a first implementation slice**,
against the **current** (post-DEC-020) state of the register — not the
Part E bridge document's own MBQ decision plan table, which was written
before DEC-018/019/020 and is not re-edited row by row for every later
acceptance (its own accepted status note says exactly this). This audit is
that check. It is a **readiness audit, not the gate-opening act** — per
criterion 3 below, opening the gate is a separate, explicit ChatGPT act
this document does not perform, propose performing on its own authority,
or pre-empt.

## 2. Accepted baseline reviewed

- **DEC-003 through DEC-020** — all **Accepted by ChatGPT**. DEC-003 fixes
  MVP scope; DEC-004–006 fix API/distribution/auth, sync orchestration,
  and binding/dedup; DEC-007 closes five DEC-003 scope-hole
  clarifications; DEC-008–011 fix module boundaries,
  error/retry/idempotency, inventory, and fulfillment architecture;
  DEC-012 fixes the ten-flow operator-UX model; DEC-013–016 accept Master
  Blueprint Parts A (core substrate), B (product/customer/sale), C
  (inventory/fulfillment), D (UI/UX screen design, at screen-design
  blueprint level only); DEC-017 accepts Part E (implementation-planning
  bridge, documentation-only) plus MBQ-64/65 at fact-verification level;
  DEC-018 accepts MBQ Decision Batch 1 (ten rows: MBQ-06/08/17/33/34/41/
  45/52/54/60); DEC-019 resolves MBQ-62 at decision/semantic-classification
  level; DEC-020 resolves MBQ-64/65 at decision/posture level.
- **AR-002 through AR-017** — all **Accepted**
  ([`architecture-review-log.md`](./architecture-review-log.md)).
- **Master Blueprint Parts A–E** — all accepted, per
  [`master-blueprint.md`](../03-architecture/master-blueprint.md)'s own
  index and the DEC-013 through DEC-017 acceptance records. Part D is
  accepted **at screen-design blueprint level only** — not pixel-level
  visual design, and not itself an implementation authorization for any
  operator-facing screen.
- **Accepted module/modular posture** — per DEC-008, restated in
  `master-blueprint.md`'s "Module family overview": a layered addon family
  (`shopify_connector_core` → `product` → `sale`/`inventory` →
  `fulfillment`), substrate concentrated in `core`, strict dependency DAG,
  no module depending on a sibling out of that order. This posture is
  unweakened by DEC-018/019/020 — none of the three touched module
  boundaries.
- **Accepted no-code gate still active** — `CLAUDE.md` §5 ("No coding
  until approved") and `master-blueprint.md`'s own "Implementation remains
  blocked" section both state the no-code gate is in force; every DEC from
  DEC-013 through DEC-020 states explicitly that its own acceptance does
  not open the implementation gate. This audit changes none of that.
- **Documentation-currency note (evidence-based finding, not corrected
  here — out of this audit's allowed-files scope):**
  `master-blueprint.md`'s own Status section and "Relation to accepted
  decisions" table are stale — they read "Accepted through DEC-017" and
  "AR-002 through AR-014 are all Accepted," with no mention of DEC-018,
  DEC-019, or DEC-020. Similarly, `master-blueprint-core-substrate.md`
  §D.2 ("Job sources") still lists only the original six DEC-009 values
  (`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`,
  `setup_readiness_check`, `export_preview_dry_run`) — it has not been
  patched to reflect DEC-019's acceptance of a seventh value, `odoo_event`.
  Neither staleness changes any accepted substance (the register itself,
  `master-blueprint-open-questions.md`, correctly reflects DEC-018/019/020
  throughout, and is the authoritative source this audit reads from), but
  both are flagged here as a documentation-maintenance item
  (`quality-feedback-loop.md` §11) for a future session — **not fixed by
  this audit**, since `master-blueprint.md` and
  `master-blueprint-core-substrate.md` are outside this sprint's
  allowed-files scope.

## 3. Gate-opening criteria from master-blueprint.md

Extracted **verbatim** from `master-blueprint.md`, "Criteria for when
implementation may later be opened":

> Implementation may be considered — never self-triggered — only after
> **all** of the following, in order:
>
> 1. **ChatGPT accepts the required Master Blueprint parts** — at minimum
>    Part A (DEC-013) and the domain blueprint part(s) covering whatever
>    is to be implemented first; acceptance of Part A alone does not
>    permit domain implementation whose blueprint part is unwritten.
>    **Where the affected implementation includes any operator-facing
>    screen, view, or UI flow, the accepted UI/UX Screen Design Blueprint
>    (Part D, above) is also required** — accepted domain/substrate
>    blueprints alone do not authorize screen-level implementation.
> 2. **Implementation-blocking open questions are resolved or
>    consciously accepted** — every register row marked "Blocks
>    implementation: Yes" for the affected scope is either resolved (with
>    evidence, per `CLAUDE.md` §7) or explicitly accepted as an open risk
>    by ChatGPT in writing.
> 3. **ChatGPT explicitly opens the implementation gate** per
>    `quality-feedback-loop.md` §10 — a separate, explicit approval;
>    blueprint acceptance is necessary but not sufficient.
> 4. **Every implementation task is written to the CLAUDE.md §9
>    template** (allowed/forbidden files, acceptance criteria, tests,
>    rollback, definition of done) using
>    `implementation-task-template.md`.
> 5. **No quality-gate escalation is open** — no defect-pattern category
>    sits at its 3rd-occurrence pause without a prevention rule
>    (`quality-feedback-loop.md` §8).

| Criterion | Current evidence | Pass / Partial / Fail | Remaining blocker | Notes |
| --- | --- | --- | --- | --- |
| **1. Required Master Blueprint parts accepted** | Part A accepted (DEC-013); Part B accepted (DEC-014); Part C accepted (DEC-015); Part D accepted **at screen-design blueprint level only** (DEC-016); Part E accepted as documentation-only planning bridge (DEC-017) | **Partial** | For a **core-substrate-only** first slice (no operator-facing screen), Part A alone is the required part and is accepted — this sub-case reads as satisfied. For **any** slice that includes a screen/view/UI flow, Part D's screen-design-level acceptance is necessary but its own text states it is "not a pixel-level visual-design/final-wireframe-polish approval" — pixel-level detail is not yet accepted for any screen. | Pass only for a scope that includes zero operator-facing UI; Partial/Fail the moment any screen is in scope. |
| **2. Implementation-blocking open questions resolved or accepted** | Ten rows resolved/decided by DEC-018 (posture/policy level, mechanics residual); MBQ-62 resolved by DEC-019 (semantic-classification level, mechanics residual); MBQ-64/65 resolved by DEC-020 (posture level, mechanics residual). **Many rows marked "Blocks implementation: Yes" remain fully open** — see §4's full table: MBQ-01/02 (model/field names), MBQ-04 (credential storage), MBQ-16/19/20/21 (job/log/error/retry schema), MBQ-44/45 (access CSVs/group XML IDs residual), MBQ-51 (transport pacing), MBQ-27/56 (order-domain currency/tax), and others. | **Fail** | Every one of these rows is either fully open (MBQ-01/02/04/16/19/20/21/27/51/56/…) or resolved-at-posture-with-an-unresolved-mechanics-residual that itself is marked "Blocks implementation: Yes" (MBQ-06/08/17/33/34/41/45/52/54/60/62/64/65's own residuals). None of these residuals has been "explicitly accepted as an open risk by ChatGPT in writing" — DEC-018/019/020 each explicitly state their acceptance does **not** decide the named residual. | This is the criterion with the most concrete, itemizable remaining work — see §4. |
| **3. ChatGPT explicitly opens the implementation gate** | No DEC, AR, or handoff entry from DEC-003 through DEC-020 records this act; every one explicitly states "implementation gate remains closed" | **Fail** | The act itself has not occurred. This audit does not perform it and does not ask ChatGPT to perform it here — it only reports that criterion 3 is unmet. | Criteria 1–2 and 4–5 being satisfied would still not satisfy criterion 3 — it is a distinct, separate act. |
| **4. Every implementation task written to the CLAUDE.md §9 template** | No implementation task exists (`docs/06-prompts/implementation-task-template.md` is confirmed "complete" and "needs no redesign" by DEC-017 §11, but has never been used) | **Fail / Not yet applicable** | Vacuously unmet — there is no task to check compliance against yet. Cannot be satisfied before criteria 1–3 are, since writing a real implementation task before the gate opens would itself be premature. | The template's readiness is not in question; its **use** is what is missing. |
| **5. No quality-gate escalation open without a prevention rule** | `defect-pattern-log.md`'s occurrence counter shows **one category at 3rd-occurrence** — "unsupported assumption (#3) / weak research (#1)" (DP-003, DP-004, DP-006) — with **Status: ESCALATED**. Its own row text states an "evidence-consistency gate" was recorded as the required prevention mechanism at the time of escalation (2026-07-01), and no session since has logged a new occurrence in that category (checked via the file's own repeated "added no new defect occurrence" notes through Sprint C2/D/E/Part E/DEC-018/019/020 sessions). | **Partial** | The row's **Status field still literally reads `ESCALATED`**, not `Mitigated` or `Closed`, even though its own text names a prevention gate. `quality-feedback-loop.md` §10/§11 (phase-exit criteria, documentation-maintenance rule) are themselves still labelled `[Recommendation — becomes binding when merged by ChatGPT]` — `CLAUDE.md` itself restates this as still true. | This audit does not resolve the ambiguity by relabelling the row (out of allowed-files scope and out of this audit's authority) — it flags that ChatGPT should explicitly confirm whether the recorded evidence-consistency gate satisfies criterion 5, or whether the row needs to be re-classified `Mitigated`/`Closed` first. |

**Net: 0 of 5 criteria are unambiguously satisfied project-wide.** Criterion
1 is satisfied only for a scope with zero operator-facing UI (i.e. a
core-substrate-only slice); criteria 2, 3, and 4 are clearly not met;
criterion 5 is ambiguous pending an explicit ChatGPT reading of an already-
recorded prevention gate. This matches — and updates with current,
post-DEC-020 evidence — the "2 of 5 criteria satisfied" reading
`master-blueprint-implementation-planning-bridge.md` §3 gave as of DEC-017;
criterion 1's partial-pass (for a core-only scope) and criterion 5's
new ambiguity are this audit's own refinements, not a contradiction of
that earlier count.

## 4. Open MBQ blocker classification

Every row in `master-blueprint-open-questions.md` is classified below. A
row already at "Blocks implementation: No" across the board is included
for completeness and marked **Non-blocking residual / can remain open**
with a short reason. **This audit changes no row's status or wording.**

| MBQ ID | Topic | Current status | Classification | Reason | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| MBQ-01 | Odoo model names, every core concept | Open — Implementation planning owned | **Blocks first core implementation slice** | No core model (store, credential, settings, job, log, binding contract) can be created without a committed name | Write the naming pass as the first implementation-planning artifact, before any model file exists |
| MBQ-02 | Field names/types, every core concept | Open — Implementation planning owned | **Blocks first core implementation slice** | Same substrate as MBQ-01; also fixes constraint/index design | Same naming-pass artifact as MBQ-01 |
| MBQ-03 | View/menu/action XML IDs (wizard/dashboard/sync/error/settings) | Open — Implementation planning owned | **Blocks a later domain/UI implementation slice** | The safest first slice (§5) excludes all UI/wizard/dashboard; a model-only core skeleton needs no view IDs yet | Defer to the UI/wizard slice; decide only if slice 1 exposes even a minimal settings menu entry |
| MBQ-04 | Credential encryption/storage-at-rest mechanism | Open — **ChatGPT + Official-doc verification** owned | **Needs ChatGPT decision before any gate opening** | Security-sensitive; explicitly ChatGPT-owned (not Implementation-planning-owned like most core rows); a long-lived offline token stored wrong is a credential-leak risk | Either ChatGPT decides the mechanism, or the first slice explicitly descopes credential persistence (store/connection model created without writing a real token yet) |
| MBQ-05 | Custom-app creation surface / token-acquisition mechanics | Open — Implementation planning owned | **Blocks a later domain implementation slice** | Setup-wizard/connection flow; needs live external API calls, explicitly excluded from the core-only first slice | Resolve when the setup-wizard/connection slice is planned |
| MBQ-06 | Readiness-check list (essential vs nice-to-have) | Resolved (posture, DEC-018); residual = exact copy/XML IDs/thresholds | **Non-blocking residual for slice 1** | Posture decided; residual is wizard UI copy, not needed for a core-only skeleton | None needed before core slice; resolve alongside MBQ-03/22 |
| MBQ-07 | Feature-flag technical implementation (model/field shape) | Resolved at direction level (DEC-013); exact shape open | **Blocks first core implementation slice** | Feature-flag/settings foundation is explicitly named in the safest first slice (§5) | Fold into the same naming/schema pass as MBQ-01/02/19/20/21 |
| MBQ-08 | Store-disconnect data-retention mechanics | Resolved (posture, DEC-018); residual = exact field/state-machine + reconnect-matching | **Blocks a later domain implementation slice** | Disconnect/reconnect flow, not needed for a bare core model skeleton | Defer to the store-lifecycle slice |
| MBQ-09 | Compliance webhooks / protected-data obligations | Open — Official-doc verification owned; conservative posture applies meanwhile | **Blocks a later domain implementation slice** | Any compliance-relevant code; webhook/customer-data code is explicitly excluded from the core-only first slice | Verify officially before any webhook controller or customer-PII-touching code; not needed for core skeleton |
| MBQ-10 | Odoo.sh/on-prem turnkey install | Open — No blocks | **Non-blocking residual / can remain open** | Install convenience, not a design blocker | None |
| MBQ-54 | Domain-module uninstall/disable data lifecycle | Resolved (posture, DEC-018); residual = exact guard mechanism/disclosure copy | **Blocks release readiness, not initial coding** | Matters before a merchant could actually uninstall a shipped module, not before the first model file is authored | Resolve before first release, not before core-slice code |
| MBQ-11 | Per-domain concrete binding models / core contract | Resolved (DEC-013) | **Non-blocking residual / can remain open** | Fully resolved, no residual | None |
| MBQ-12 | Shopify GID permanence/non-reuse | Open — No blocks (defensive design stands) | **Non-blocking residual / can remain open** | Already handled defensively regardless of the official answer | None |
| MBQ-13 | Stale/recreated-binding review flow detail | Open — No blocks | **Non-blocking residual / can remain open** | Behavioural rules already fixed; only UI detail remains | None |
| MBQ-14 | `@idempotent` key uniqueness scope | Open — Yes (inventory/refund write code) | **Blocks a later domain implementation slice** | Inventory/refund write code specifically, not core substrate | Resolve before inventory-domain write code |
| MBQ-15 | Bulk Operation idempotency/resumability | Open — Yes, only if/when internal bulk is used | **Non-blocking residual / can remain open** | Conditional on a mechanism not yet chosen for use | Revisit only if bulk operations are adopted |
| MBQ-16 | Retry-count ceilings / backoff constants | Open — Implementation planning owned | **Blocks first core implementation slice** | Job/log/error abstraction explicitly named in Part E's own first-safe-slice recommendation (§8 of that document) | Decide constants inside the same first implementation-planning task as MBQ-19/20/21 |
| MBQ-17 | Reconciliation cadence/scope | Resolved (posture, DEC-018); residual = exact interval/batch-size constants | **Non-blocking residual for slice 1** | Core's job-source enum already includes `reconciliation` as a fixed value; the exact cadence number is only needed once a specific domain's reconciliation job is scheduled | Decide per-domain cadence when that domain's reconciliation job is built |
| MBQ-18 | Cron cadence/throughput limits | Open — Yes for constants before code; throughput validation blocks release readiness | **Blocks first core implementation slice** (constants) **and Blocks release readiness** (validation) | Constants needed to write the core queue-draining cron job; actual load validation is a separate, later concern | Decide default batch-size/interval constants inside the first task; validate throughput before release, not before code start |
| MBQ-19 | Job/log model shape (single model vs job+log split) | Open — Implementation planning owned | **Blocks first core implementation slice** | "The substrate every domain depends on; must be fixed once, early" (register's own wording) | Decide as part of the first implementation-planning task itself |
| MBQ-20 | Operation-level idempotency key schema | Open — Implementation planning owned | **Blocks first core implementation slice** | Core substrate; prevents connector-side duplicate processing across all domains | Same task as MBQ-19 |
| MBQ-21 | Serialization-guard mechanism | Open — Implementation planning owned | **Blocks first core implementation slice** | Core substrate; prevents a corrected operation dispatching while a prior ambiguous one is unresolved | Same task as MBQ-19/20 |
| MBQ-22 | User-facing copy/wording | Open — No blocks (later UI-design pass) | **Non-blocking residual / can remain open** | Structure already fixed; copy is cosmetic | None before core slice |
| MBQ-23 | Variant-write mutation strategy | Partially resolved (DEC-014, direction); exact choice open | **Blocks a later domain implementation slice** | Product export, not core | Resolve in the product-export task |
| MBQ-24 | `productSet` delete-on-omit for media | Open — Yes (image export) | **Blocks a later domain implementation slice** | Product/image export, not core | Resolve in the product-export task |
| MBQ-25 | Draft/publish channel-selection UX | Partially resolved (DEC-014, mechanism); exact UX open | **Blocks a later domain implementation slice** | Product export, not core | Resolve in the product-export task |
| MBQ-26 | Order-import operator touchpoints | Resolved at blueprint level (DEC-014) | **Non-blocking residual / can remain open** | Fully resolved, no residual | None |
| MBQ-27 | Odoo representation of Shopify-computed tax | Open — inconclusive after Sprint B's official-doc check | **Blocks a later domain implementation slice** | Order import (`sale` module), not core | Verify officially before the order-import task; recheck Odoo 19 accounting docs |
| MBQ-28 | Domain 9 draft-artifact guard | Open — Yes, if triggered; not currently triggered | **Non-blocking residual / can remain open** | Contingent, currently inactive | Re-check only if a future task triggers it |
| MBQ-29 | Default-customer fallback granularity | Partially resolved (DEC-014, direction); granularity open | **Blocks a later domain implementation slice** | Customer/order import, not core | Resolve in the customer/order-import task |
| MBQ-30 | Gateway → Odoo journal mapping schema | Open — No blocks | **Non-blocking residual / can remain open** | Config-input schema, not a design blocker | None |
| MBQ-31 | Final customer match-key set | Resolved at blueprint level (DEC-014) | **Non-blocking residual / can remain open** | Fully resolved, no residual | None |
| MBQ-32 | Free-to-Use ORM source selection (inventory) | Partially resolved (DEC-015, facts verified); source-selection open | **Blocks a later domain implementation slice** | Inventory domain, not core | Resolve in the inventory quantity-write-back task |
| MBQ-33 | First-push guard granularity | Resolved (posture, DEC-018); residual = confirmation-record schema/batched UX | **Blocks a later domain implementation slice** | Inventory domain, not core | Resolve in the inventory first-push task |
| MBQ-34 | Ongoing inventory apply-mode | Resolved (posture, DEC-018); residual = UX/copy + future flag design | **Blocks a later domain implementation slice** | Inventory domain, not core | Resolve in the inventory write-back task |
| MBQ-35 | `on_hand` UI exposure | Open — No blocks unless an `on_hand` UI is proposed | **Non-blocking residual / can remain open** | Conditional, not currently proposed | Revisit only if such a UI is proposed |
| MBQ-36 | Mutation choice per trigger type (inventory) | Partially resolved (DEC-015, direction); detail open | **Blocks a later domain implementation slice** | Inventory domain, not core | Resolve in the inventory write-back task |
| MBQ-37 | Shopify inventory webhook topic string(s) | Resolved at fact-verification level (DEC-015); residual routed to MBQ-63 | **Non-blocking residual / can remain open** | Topic-string fact resolved; remaining blocker lives at MBQ-63 | See MBQ-63 |
| MBQ-38 | First-push confirmation record schema | Partially resolved (DEC-015, concept); schema open | **Blocks a later domain implementation slice** | Inventory domain, not core | Resolve in the inventory first-push task |
| MBQ-39 | Odoo tracking-reference field source | Resolved at fact-verification level (DEC-015); residual routed to MBQ-60 | **Non-blocking residual / can remain open** | Field fact resolved; remaining blocker lives at MBQ-60 | See MBQ-60 |
| MBQ-40 | Backorder-to-picking linkage detail | Partially resolved (DEC-015); wizard UX/copy residual | **Blocks a later domain implementation slice** | Fulfillment domain, not core | Resolve in the fulfillment task |
| MBQ-41 | Notification-UI granularity | Resolved (posture, DEC-018); residual = whether Odoo already exposes a per-order toggle | **Non-blocking residual / can remain open** | Conditional; only blocks if a per-order override is later proposed | Check at implementation time; no action needed now |
| MBQ-42 | Fulfillment location-confirmation mechanism | Resolved at blueprint level (DEC-015); implementation detail open | **Blocks a later domain implementation slice** | Fulfillment domain, not core | Resolve in the fulfillment task |
| MBQ-43 | Core Location-reference cache policy | Resolved (DEC-015, precedence rule); refresh cadence/mechanism open | **Blocks a later domain implementation slice** | Fulfillment/inventory location checks, not the core skeleton itself | Resolve in the fulfillment/inventory task |
| MBQ-44 | Exact `ir.model.access` rows / security CSVs / record rules | Open — Implementation planning owned | **Blocks first core implementation slice** | `ir.model.access` is deny-by-default; even the bare core job/log/store models need access rows to be functional | Write access CSVs for core models alongside the MBQ-01/02 naming pass |
| MBQ-45 | Roles→groups mapping / surface split | Resolved (hierarchy DEC-013 + mapping/surface DEC-018); residual = exact CSVs (MBQ-44) + group XML IDs (MBQ-01/02/03) | **Blocks first core implementation slice** | Core models need the four group XML IDs to exist before their access rows can reference them | Same naming/access pass as MBQ-01/02/44 |
| MBQ-46 | Multi-company/multi-store permission isolation | Open — No blocks (later phase) | **Non-blocking residual / can remain open** | Explicitly later-phase; Phase 1 rules must merely not preclude it | None |
| MBQ-47 | Reviewer role scope | Resolved (DEC-013) | **Non-blocking residual / can remain open** | Fully resolved, no residual | None |
| MBQ-48 | Odoo.sh vs on-prem packaging | Open — No blocks | **Non-blocking residual / can remain open** | Install convenience | None |
| MBQ-49 | MVP-scale throughput validation | Open — No for code start; Yes for release readiness | **Blocks release readiness, not initial coding** | Proves the internal cron-queue suffices before release | Validate before release; does not block first slice's code |
| MBQ-50 | OCA `queue_job` optional adoption | Open — No blocks (only via a DEC-005 revisit trigger) | **Non-blocking residual / can remain open** | Not a Phase 1 default | Revisit only if a trigger fires |
| MBQ-51 | GraphQL cost/throttle-aware pacing parameters | Open — Yes (transport client) | **Blocks a later domain implementation slice** | Live transport client needs external API calls, explicitly excluded from the core-only first slice — this is the **next core-module milestone** (transport client), not slice 1 itself | Resolve when the transport-client milestone is planned |
| MBQ-52 | Shopify API-version pinning/upgrade policy | Resolved (policy, DEC-018); residual = exact upgrade mechanics | **Blocks a later domain implementation slice** | Same transport/API-version milestone as MBQ-51, not slice 1 | Resolve alongside MBQ-51 |
| MBQ-53 | Screen-level UI/UX design blueprint | Partially resolved at screen-design level (DEC-016); full closure depends on MBQ-03/22/44/45/06 | **Blocks a later domain implementation slice** | Any operator-facing screen/view/UI flow — explicitly excluded from the core-only first slice; does not block Part B/C domain-blueprint-level authoring | Resolve before any UI/screen implementation task, not before core skeleton |
| MBQ-55 | Sprint B binding model names (product/variant/customer/order) | Open — Implementation planning owned | **Blocks a later domain implementation slice** | Product/sale-domain binding models specifically, not core's own binding contract (MBQ-01/02) | Resolve in the product/sale naming pass |
| MBQ-56 | Total-check guard tolerance/comparison mechanism | Open — Implementation planning owned | **Blocks a later domain implementation slice** | Order import (`sale` module), not core | Resolve in the order-import task |
| MBQ-57 | Whole-order-hold-rule alternative | Open — No blocks | **Non-blocking residual / can remain open** | Current rule stands unless revisited | None |
| MBQ-58 | Order-identity stability nuances | Open — No blocks (defensive design stands) | **Non-blocking residual / can remain open** | Existing binding-based defense already covers the general case | None |
| MBQ-59 | Automated import create/bind eligibility/match-confidence detail | Resolved at blueprint-policy level (DEC-014); exact detail open | **Blocks a later domain implementation slice** | Product/customer/order automation, not core | Resolve in the relevant domain-automation task |
| MBQ-60 | `stock_delivery`/`delivery` module dependency | Resolved (posture, DEC-018); residual = manifest `depends` mechanics + readiness wording | **Blocks a later domain implementation slice** | Fulfillment module's own manifest, not core's | Resolve in the fulfillment task |
| MBQ-61 | FulfillmentOrder lifecycle events beyond creation | Open — No for MVP correctness-core; Yes only if hold-aware UX later required | **Non-blocking residual / can remain open** | Existing ambiguous-outcome/manual-review handling already catches a rejected call | Revisit only if a dedicated hold-aware UX is proposed |
| MBQ-62 | Odoo-side event job-source classification | Resolved (decision/semantic-classification level, DEC-019); residual = exact model/field names, Python constants, storage/Selection-field mechanics, trigger-origin field/model | **Blocks first core implementation slice** | The `odoo_event` value and its trigger-origin sub-classification live in Part A §D.2's own `job_source` field — core substrate, needed the moment the core job/log model (MBQ-19) is authored | Decide alongside MBQ-19/20/21 in the same first implementation-planning task |
| MBQ-63 | Inventory webhook payload/subscription/Phase-1-scope residual | Open — Yes, only for webhook-driven inventory import specifically | **Blocks a later domain implementation slice** | Webhook-gated inventory import, explicitly excluded from the core-only first slice (no webhooks) | Resolve only if/when webhook-driven inventory import is implemented |
| MBQ-64 | Shopify shop/presentment currency vs Odoo order currency | Resolved (decision/posture level, DEC-020); residual = exact error-class/sub-reason mapping, enforcement mechanism, MBQ-56's tolerance | **Blocks a later domain implementation slice** | Order import (`sale` module), not core | Resolve in the order-import task, with the same rigor DEC-018/019 applied to MBQ-62 |
| MBQ-65 | Product-domain webhook residuals | Resolved (decision/posture level, DEC-020); residual = exact controller/query/subscription mechanics, unconfirmed variant-truncation claim | **Blocks a later domain implementation slice** | Product-webhook-enabled path, explicitly excluded from the core-only first slice (no webhooks) | Resolve when the product-webhook controller task is planned |

## 5. First implementation slice readiness

Evaluated against the safest possible first slice — `shopify_connector_core`
substrate only, per this audit's own scoping (module skeleton;
manifest/dependencies; store/config model; job/log/error model;
feature-flag/settings foundation; **no** Shopify sync logic; **no**
product/customer/order/inventory/fulfillment logic; **no** webhooks; **no**
external API calls; credential storage included **only if** MBQ-04 is
resolved, otherwise explicitly descoped from this slice).

| Core capability | Required decisions | Current readiness | Blocker? | Notes |
| --- | --- | --- | --- | --- |
| Module skeleton (manifest, package layout, dependency declaration) | Module-level naming (already accepted via DEC-008's family names); MBQ-01/02/07 for anything inside it | **Partial** — top-level module names (`shopify_connector_core`) are an accepted convention (DEC-008); nothing inside the module has a committed name yet | **Yes**, for anything beyond an empty shell | Cannot contain a real model until MBQ-01/02 are decided |
| Store / connection (config) model | MBQ-01/02 (names/fields), MBQ-07 (feature-flag extension shape) | Blueprint-level concept fully described (Part A §B.1); zero concrete schema | **Yes** | Decide inside the naming/schema pass |
| Credential placeholder / storage | MBQ-04 | Not decided; owner includes ChatGPT, not solely Implementation planning | **Yes, unless explicitly descoped from this slice** | Recommended: descope credential persistence from slice 1 entirely (store/connection model exists; no real token write path yet) rather than block the whole slice on MBQ-04 |
| Job/log/error model | MBQ-19 (shape), MBQ-20 (idempotency schema), MBQ-21 (serialization guard), MBQ-16 (retry constants), MBQ-62 residual (trigger-origin field), MBQ-01/02 (names) | Blueprint-level concept fully described (Part A §D — 6 fixed sources[^1], 10 states, 16 error classes); zero concrete schema | **Yes** | This is the single largest concentration of first-slice blockers — all "Implementation planning"-owned, decidable in one dedicated task |
| Feature flag / settings foundation | MBQ-07 (shape), MBQ-01/02 (names) | Direction accepted (DEC-013 §I.3); zero concrete schema | **Yes** | Same task as job/log/error |
| Security/access rows for the above (deny-by-default) | MBQ-44 (CSVs/record rules), MBQ-45 residual (group XML IDs) | Role hierarchy + 1:1 mapping accepted (DEC-013/018); zero CSVs or group XML IDs exist | **Yes** | Even a core-only skeleton needs at least the four group XML IDs and matching `ir.model.access.csv` rows for its own models to be usable at all |
| No Shopify sync logic / no product/customer/order/inventory/fulfillment logic | N/A — explicitly out of scope | N/A | N/A | By construction, none of MBQ-05/09/14/23–43/51–65 block this slice |
| No webhooks | N/A — explicitly out of scope | N/A | N/A | MBQ-09/63/65 (and the generic webhook-receiver piece of `core`) are deferred to a later `core` milestone, not slice 1 |
| No external API calls | N/A — explicitly out of scope | N/A | N/A | MBQ-05/51/52 (transport client, credential, version pinning) are deferred to the **next** `core` milestone after this slice |

[^1]: Part A §D.2 currently lists the original six DEC-009 job sources;
DEC-019's seventh value (`odoo_event`) is accepted but not yet reflected
in that blueprint section's own text — see §2's documentation-currency
note.

**Reading:** every capability inside the described first slice is blocked
by at least one open, currently-undecided item — but every one of those
items is either (a) "Implementation planning"-owned, meaning it is
designed to be decided **inside** a single dedicated naming/schema task
rather than requiring a fresh ChatGPT policy round, or (b) MBQ-04
specifically, which can be **descoped** from this slice rather than
resolved. No capability in this slice is blocked by an item whose only
path forward is "wait for a later domain sprint" — that is precisely what
makes core substrate the safest candidate first slice, consistent with
Part E §8's own reasoning. It does **not** mean the slice is ready to
code today — the naming/schema task itself does not yet exist.

## 6. What must be decided before first code

**Must resolve before any code** (ChatGPT-level acts, not internal
planning-task choices):

- **MBQ-04** — credential storage mechanism, or an explicit ChatGPT
  decision to descope it from slice 1.
- **Criterion 3** — ChatGPT's own explicit gate-opening act (a distinct
  act from accepting this audit or any blueprint part).
- **Criterion 5's ambiguity** — ChatGPT should explicitly state whether
  the recorded evidence-consistency gate satisfies "a prevention rule in
  place" for the DP-003/004/006 escalation, or whether that row needs to
  be re-classified `Mitigated`/`Closed` first.

**Must resolve before core-substrate code specifically** (naming/schema
commitments — "Implementation planning"-owned, i.e. decided inside the
task itself, but the task must exist and run before any core `.py`/model
file does):

- MBQ-01 (model names), MBQ-02 (field names/types), MBQ-07 (feature-flag
  schema), MBQ-19 (job/log shape), MBQ-20 (idempotency schema), MBQ-21
  (serialization guard), MBQ-16 (retry constants), MBQ-62's residual
  (trigger-origin field/model), MBQ-44 (access CSVs) and MBQ-45's residual
  (group XML IDs) for the core models above.

**Can resolve during the first implementation-planning task itself,
before code inside that task:**

- MBQ-18's constants sub-part (cron cadence/batch size) — needed before
  the actual cron-job code is written, but fine to decide as part of
  writing that same task.
- Any settings-screen copy tied to MBQ-06/22, **only if** the core slice
  ends up exposing even a minimal settings view — otherwise defer.

**Can remain open until later domain slices** (the large majority of the
register — see §4's full table): MBQ-03/05/08/09/14/15/17/23–43/46/48–53/
55–65 and MBQ-51/52 specifically (transport-client milestone).

## 7. Recommended next session

**Resolve the core implementation-planning blockers: MBQ-01/02/04/07/16/
19/20/21/44/45(residual)/62(residual)**, produced as a **single,
documentation-only, implementation-planning artifact** (a naming +
core-schema pass) — not code, and not itself the gate-opening act. This
is the same "naming pass" and "first safe implementation slice" Part E §4
and §8 already identified as the two cheapest, most leveraged levers
remaining, now made concrete against the full post-DEC-020 register
rather than the stale Part E table. Concretely, that session should:

1. Commit exact Odoo model and field names for every core-substrate
   concept (store/connection, settings/feature-flags, job, log, binding
   contract) — MBQ-01/02/07.
2. Commit the job/log model shape, idempotency-key schema, and
   serialization-guard mechanism — MBQ-19/20/21.
3. Commit retry-count/backoff constants and the `odoo_event` trigger-
   origin field/model shape — MBQ-16, MBQ-62's residual.
4. Commit the four group names/XML IDs and draft `ir.model.access.csv`
   rows for the core models above — MBQ-44/45's residual.
5. Explicitly address MBQ-04 — either propose a storage mechanism for
   ChatGPT's decision, or propose descoping credential persistence from
   slice 1 with an explicit rationale.

This is **not** the recommendation to start coding. It is the
prerequisite naming/schema work criterion 2 requires before a first
implementation task could even be written to the CLAUDE.md §9 template
(criterion 4), which itself precedes any explicit gate-opening act
(criterion 3).

## 8. Risks if gate opens too early

- **Unsafe credential storage** — MBQ-04 is unresolved; writing a
  long-lived offline token to the wrong field/table shape is a
  credential-leak risk DEC-004 already flagged and left open.
- **Unstable model names** — coding against unnamed models (MBQ-01/02)
  before a naming pass risks a painful rename/migration across every
  domain module once real names are chosen later.
- **Job/log schema churn** — MBQ-19/20/21 are "the substrate every domain
  depends on; must be fixed once, early" (register's own wording);
  building on top of an undecided shape before it settles risks a schema
  change rippling through every later domain module.
- **Retry/idempotency mistakes** — MBQ-16's constants and MBQ-20's key
  schema are unresolved; RA-014 (this project's own rejected
  "retry-everything automatically" approach) and RA-017 (rejected
  "binding-only, no per-operation idempotency key" approach) both exist
  precisely because getting this wrong risks double-acting on
  non-idempotent Shopify mutations.
- **Queue throughput issues** — MBQ-18's constants and MBQ-49's
  throughput validation are open; coding a cron-drain loop before either
  is decided risks building against numbers that don't hold at MVP scale.
- **Silent financial mismatch** — MBQ-56 (total-check tolerance) and
  MBQ-64's residual (exact error-class/sub-reason mapping for a blocked
  divergent-currency order) remain open; DEC-020 itself only fixed the
  *posture* (no silent SO creation for divergent currencies), not the
  exact mechanics — coding the order-import guard before that residual is
  resolved risks reintroducing the exact silent-mismatch risk DEC-020 was
  written to close.
- **Destructive writes** — MBQ-65's residual (exact controller/query
  mechanics) and MBQ-24 (`productSet` delete-on-omit for media) are open;
  this project has already rejected the same root failure mode twice
  (RA-008 blind inventory push; RA-020 autonomous bidirectional conflict
  resolution) — coding a webhook controller or product-export path before
  these residuals are resolved risks a third instance of writing without
  a confirming read/guard.
- **Poor migration path** — with MBQ-01/02/19/20/21 undecided, any code
  written now would need a schema migration the moment those rows are
  finally decided — exactly the scenario the naming pass exists to avoid.
- **Module boundary mistakes** — MBQ-60 (fulfillment's `stock_delivery`
  dependency) and MBQ-51/52 (transport-client scope) are open; coding
  before they are decided risks a manifest `depends` list or module
  boundary that has to be reworked once resolved, echoing RA-011/RA-012
  (this project's own rejected one-giant-module and per-feature-
  micro-module anti-patterns) if boundaries are guessed rather than
  decided.

## 9. Audit verdict

**READY ONLY FOR A VERY LIMITED IMPLEMENTATION-PLANNING SPRINT, NOT
CODE.**

**Reasoning:** Criterion 1 (blueprint parts accepted) passes only for a
scope with zero operator-facing UI. Criterion 2 (implementation-blocking
questions resolved) clearly fails — §4's full sweep finds eleven rows
(MBQ-01/02/04/07/16/19/20/21/44/45/62) that block even the narrowest
possible first slice, core substrate alone, several of them (MBQ-19/20/21,
"the substrate every domain depends on") explicitly named by this
project's own prior research as needing to be "fixed once, early" before
anything else. Criterion 3 (explicit gate-opening act) has not occurred.
Criterion 4 (tasks written to template) is vacuously unmet — no task
exists. Criterion 5 (no open quality-gate escalation) is ambiguous, not a
clean pass. Zero of five criteria are unambiguously satisfied
project-wide. This is not a project that is behind — the opposite is
true: DEC-003 through DEC-020, AR-002 through AR-017, and Master Blueprint
Parts A–E represent a genuinely complete, rigorously reviewed research and
architecture phase. What remains is the **narrow, well-scoped, and now
fully itemized** naming/schema/access work §6–§7 name — not further
research, and not yet code.

## 10. Recommendation to ChatGPT — accepted

**Recommendation:** direct the next session to produce the
implementation-planning artifact named in §7 (naming + core-schema pass
for MBQ-01/02/04/07/16/19/20/21/44/45/62), still documentation-only, still
not a gate-opening act. Do **not** direct a coding session yet. If ChatGPT
judges criterion 5's ambiguity should be resolved first, that is a fast,
independent parallel action (confirming or re-labelling the existing
DP-003/004/006 escalation row) that does not block starting the naming/
schema work. Opening the implementation gate itself (criterion 3) should
remain a **separate, later, explicit act** — taken only once the naming/
schema pass exists and criterion 2's remaining rows are either resolved or
consciously accepted as risks in writing, per `master-blueprint.md`'s own
criteria.

**ChatGPT accepted this recommendation, as proposed, on 2026-07-05** (see
"Acceptance" above) — the next session is the documentation-only
naming/core-schema implementation-planning pass named in §7, not code and
not the gate-opening act; criterion 5's ambiguity remains open, to be
confirmed independently and does not block that next session from
starting.

---

**Change control:** further changes to this record require ChatGPT review,
mirroring the DEC-013 through DEC-020 change-control pattern. This audit
does not re-litigate DEC-003 through DEC-020, does not reopen accepted
Master Blueprint Parts A–E, and does not reintroduce any row from
`rejected-approaches-log.md`.
