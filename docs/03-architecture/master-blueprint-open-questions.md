# Master Blueprint — Open Questions Register

> Central register of unresolved **Master Blueprint / implementation-planning
> questions** for the premium **Odoo 19 ↔ Shopify Connector**. Created in
> Master Blueprint Sprint A; **updated by every later blueprint part**.
> Companion index: [`master-blueprint.md`](./master-blueprint.md). Companion
> Part A blueprint:
> [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md).

## Status

**Accepted as the central register through DEC-016**, latest acceptance
date **2026-07-04**. Documentation only; the no-code gate (`CLAUDE.md`
§4–§5) is in force. **Register acceptance does not resolve every
question** — each MBQ row remains open unless the row itself says
**Resolved**, **Partially resolved**, or **Accepted at blueprint(-policy)
level**; notably **MBQ-03, MBQ-04, MBQ-22, MBQ-24,
MBQ-27, MBQ-28, MBQ-32, MBQ-35, MBQ-44,
MBQ-53 (partially resolved at screen-design level only; sibling rows
above still open), MBQ-55, MBQ-56, MBQ-57, MBQ-58, MBQ-61, and
MBQ-63 remain open**. Per the **DEC-018 acceptance patch
(2026-07-04)**, **MBQ-06, MBQ-08, MBQ-17 (posture), MBQ-33, MBQ-34,
MBQ-41, MBQ-45, MBQ-52, MBQ-54, and MBQ-60 are now Resolved/Partially
resolved** (see each row; residual implementation-planning detail may
remain). Per the **DEC-019 acceptance patch (2026-07-04)**, **MBQ-62 is now
Resolved at decision/semantic-classification level** — Part A §D.2's
job-source vocabulary is extended with a seventh accepted semantic value,
`odoo_event`, plus a required trigger-origin sub-classification; exact
Odoo implementation mechanics remain implementation planning (see MBQ-62's
own row). Registering (or
accepting the register containing) a question does **not** decide it and
does **not** authorize implementation. Every row follows `CLAUDE.md`
§7/§8: unverified items are **open questions**, never asserted.
**Vocabulary note:** an unqualified **Resolved**/**Partially resolved**
label reflects a sprint whose companion decision record ChatGPT has
already **accepted**. A row from a sprint whose companion decision record
is still **Proposed for ChatGPT review** (not yet accepted) is labelled
**Proposed resolved** / **Proposed partially resolved** instead — these
rows remain **open** until that decision record is accepted; see the
Sprint C / DEC-015 acceptance note and the Sprint D / DEC-016 acceptance
note below — both DEC-015 and DEC-016 are now **accepted**, so their
rows use the unqualified **Resolved**/**Partially resolved** labels
(DEC-016's MBQ-53 label remains **partially resolved**, explicitly
qualified "at screen-design blueprint level," not a full resolution).

> **Master Blueprint Sprint B note (2026-07-03, revised after PR #72
> ChatGPT review and again after PR #72 Fable review; superseded by the
> DEC-014 acceptance note below).** Sprint B
> ([`master-blueprint-product-customer-sale.md`](./master-blueprint-product-customer-sale.md),
> companion
> [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md))
> proposed updates to the product/customer/order rows below (MBQ-23
> through MBQ-31) and added MBQ-55 through MBQ-59 (MBQ-59 added in the
> PR #72 ChatGPT-requested revision, revised again in the PR #72
> Fable-requested revision to fix its routing description — see MBQ-59's
> own row).
>
> **DEC-014 Acceptance Patch (2026-07-03) — accepted as the register's
> update through Sprint B.** After PR #72 merged into `Shopify-connector`
> (merge commit `e27c21f328436bc734539dd9169a95d79deaadd1`), ChatGPT
> accepted [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
> on **2026-07-03**. MBQ-23, MBQ-25, MBQ-29, and MBQ-30 are now
> **partially resolved** (direction accepted, exact detail still open);
> MBQ-26 (order-import operator touchpoints), MBQ-31 (customer match-key
> set), and MBQ-59 (automated import create/bind policy) are now
> **accepted at blueprint(-policy) level** (see each row below). The
> register's accepted-through-DEC-014 status is otherwise unchanged, and
> **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53, MBQ-54, MBQ-55,
> MBQ-56, MBQ-57, and MBQ-58 remain untouched and open.**

> **Master Blueprint Sprint C note (2026-07-03, revised after PR #74
> Fable review and a same-PR consistency patch; superseded by the
> DEC-015 acceptance note below).** Sprint C
> ([`master-blueprint-inventory-fulfillment.md`](./master-blueprint-inventory-fulfillment.md),
> companion
> [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md))
> proposed updates to the inventory/fulfillment rows below (MBQ-32
> through MBQ-43) and added four new rows, MBQ-60 through MBQ-63 (MBQ-62
> and MBQ-63 added in a Fable-review revision on the same PR — see their
> own rows for what each covers and why).
>
> **DEC-015 Acceptance Patch (2026-07-03) — accepted as the register's
> update through Sprint C.** After Fable reviewed PR #74 (**REVISE** —
> findings C1/C2 plus seven minor findings, fixed on the same PR) and a
> same-PR consistency patch was applied, ChatGPT accepted
> [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
> on **2026-07-03**. MBQ-37 and MBQ-39 are now **resolved** at
> fact-verification level; MBQ-32, MBQ-36, MBQ-38, MBQ-40, MBQ-42, and
> MBQ-43 are now **partially resolved** (direction/fact accepted, exact
> residual detail still open — MBQ-32 stays partially resolved per
> Fable finding C1's correction that the two candidate quantity sources
> are verified but not equivalent; MBQ-42's partial resolution includes
> an accepted widening of `ambiguous match` to also cover a deterministic
> fulfillment-location mismatch, accepted at blueprint level only).
> **MBQ-33, MBQ-34, and MBQ-41 remain open** — each carries a
> recommendation, **not decided by this acceptance** (all three stay
> explicitly ChatGPT-decision-owner rows). **MBQ-35 remains carried
> forward, open, unchanged. MBQ-60 through MBQ-63 remain new and open**
> — none resolved by this acceptance (MBQ-62 — Odoo-event-triggered
> job-source classification, Fable finding C2 — and MBQ-63 — the
> broader inventory-webhook payload/subscription/Phase-1-scope residual
> — both added in the Fable-review revision). The register's
> accepted-through-DEC-015 status is otherwise unchanged, and
> **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53, MBQ-54, MBQ-55,
> MBQ-56, MBQ-57, and MBQ-58 remain untouched and open.**

> **Master Blueprint Sprint D note (2026-07-03, superseded by the DEC-016
> acceptance note immediately below).** Sprint D
> ([`master-blueprint-ui-ux-screen-design.md`](./master-blueprint-ui-ux-screen-design.md),
> companion
> [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md))
> proposed the UI/UX Screen Design Blueprint (Part D) and proposed updating
> only the **MBQ-53** row above. **No other MBQ row was changed, and no new
> MBQ row was added** — the screen design consumes existing open questions
> rather than surfacing new ones. Part D **proposed a direction** for, but
> did **not** decide, the screen-relevant open rows **MBQ-45**
> (admin-vs-functional surface split / roles→groups), **MBQ-06** (readiness
> split), **MBQ-33/MBQ-34/MBQ-41** (first-push granularity / apply-mode /
> per-order notification override), and **MBQ-35/MBQ-32** (`on_hand` UI
> exposure / quantity source) — its screens are designed to accommodate
> either resolution. **MBQ-03/MBQ-22/MBQ-44** (exact XML IDs / copy /
> groups) and **MBQ-60 through MBQ-63** remained open and untouched.
>
> **DEC-016 Acceptance Patch (2026-07-04) — accepted as the register's
> update through Sprint D, at screen-design blueprint level only.** After
> duplicate-PR reconciliation (PR #75 closed as superseded, not merged), a
> competitor screenshot UX benchmark traceability audit, and the Fable
> Sprint D review fixes (F1–F7) were applied on PR #77, ChatGPT accepted
> [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md)
> on **2026-07-04**. **MBQ-53 is now partially resolved by DEC-016 at
> screen-design blueprint level** — the screen-design blueprint layer
> ([`master-blueprint-ui-ux-screen-design.md`](./master-blueprint-ui-ux-screen-design.md))
> is accepted, but MBQ-53's full closure still depends on its sibling rows
> **MBQ-03** (exact XML IDs), **MBQ-22** (exact copy), **MBQ-44** (exact
> groups), **MBQ-45** (surface split), and **MBQ-06** (readiness split), all
> of which **remain open** — MBQ-53 itself therefore stays **open/partial**,
> not fully resolved. **MBQ-33, MBQ-34, MBQ-41, MBQ-35, and MBQ-32 remain
> open recommendations**, not decided by this acceptance. **MBQ-60 through
> MBQ-63 remain open.** **No new MBQ row is added.** This acceptance is a
> **screen-design blueprint** acceptance only — it is **not** a pixel-level
> visual-design/final-wireframe-polish approval, and the competitor
> screenshot audit is accepted only as sufficient traceability for
> blueprint-level acceptance (the `sh_shopify_connector` "Daily Queue
> Activity Tracking" chart idea it surfaced remains a deferred premium
> candidate, not adopted into the accepted dashboard card set). The
> register's accepted-through-DEC-016 status is otherwise unchanged, and
> **MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-54, MBQ-55, MBQ-56,
> MBQ-57, and MBQ-58 remain untouched and open.** Registering this
> acceptance decides nothing beyond the explicit points above and
> authorizes no implementation.

> **Master Blueprint Part E note (2026-07-04), superseded by the DEC-017
> Acceptance Patch immediately below.** Part E
> ([`master-blueprint-implementation-planning-bridge.md`](./master-blueprint-implementation-planning-bridge.md))
> was proposed after PR #79 merged into `Shopify-connector` (merge commit
> `77ee511036a98db36262bdbc9b4ae4371a2d85f8`, PR #80), acting on the PR #78
> Master Blueprint Integrity & Competitor Advantage Audit's recommendation
> (§6/§10) to close two currently-untracked official-doc gaps before the
> MBQ decision plan proceeds. That session added two new rows, **MBQ-64**
> and **MBQ-65** (§4 below).

> **DEC-017 Acceptance Patch (2026-07-04) — accepted as the register's
> update through Part E.** After ChatGPT reviewed PR #80, ChatGPT formally
> accepted
> [`DEC-017`](../04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md)
> on **2026-07-04**. This acceptance is **documentation-only** and accepts
> Part E **as an implementation-planning bridge** (MBQ decision plan,
> proposed implementation sequence, first-safe-slice recommendation,
> test/rollback strategy — all accepted **as planning guidance only**, not
> as decisions or authorizations). **MBQ-64 is now partially resolved by
> DEC-017 at fact-verification level** — Shopify's `MoneyBag`
> (`shopMoney`/`presentmentMoney`) order-money model and Odoo's single
> computed `sale.order.currency_id` are accepted as verified facts; **the
> design/selection mechanism (which money field is compared against
> `currency_id`, and how a mismatch is classified/guarded) remains open**,
> not decided by this acceptance. **MBQ-65's topic strings
> (`PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE`) are now resolved
> by DEC-017 at fact-verification level only**, mirroring MBQ-37's
> treatment — **the payload-shape/subscription-scope/Phase-1-
> implementation-scope residual remains open**, mirroring MBQ-63. **No
> ChatGPT-batch MBQ is decided by this acceptance** — MBQ-06, MBQ-08,
> MBQ-17 (posture), MBQ-33, MBQ-34, MBQ-41, MBQ-45 (surface split),
> MBQ-52, MBQ-54, MBQ-60, and MBQ-62 all remain exactly as open as stated
> in the DEC-013 through DEC-016 acceptance notes above. **No other MBQ
> row is modified, resolved, re-routed, or silently changed by this
> acceptance.** Per `CLAUDE.md` §10, this acceptance **does not authorize
> implementation**; DEC-003 through DEC-016 remain unchanged;
> **implementation remains blocked; the implementation gate remains
> closed.** Recommended next: the MBQ decision plan's own ChatGPT-batch
> decisions, then a separate, explicit ChatGPT implementation-gate-opening
> act.

> **DEC-018 Acceptance Patch (2026-07-04) — MBQ Decision Batch 1 accepted
> except MBQ-62.** After ChatGPT reviewed the proposed
> [`DEC-018`](../04-decisions/DEC-018-mbq-decision-batch-1.md) packet,
> **ChatGPT formally accepted DEC-018 on 2026-07-04**, adopting ten of its
> eleven in-scope rows as Decisions: **MBQ-06** (readiness-check
> essential-vs-nice-to-have split), **MBQ-08** (disconnect data-retention
> posture), **MBQ-17** (reconciliation posture only), **MBQ-33** (first-push
> guard granularity), **MBQ-34** (ongoing apply-mode default), **MBQ-41**
> (notification-UI granularity), **MBQ-45** (roles→groups mapping / surface
> split), **MBQ-52** (API-version pinning policy only), **MBQ-54**
> (uninstall/disable posture only), and **MBQ-60** (`stock_delivery`/
> `delivery` dependency). **MBQ-62 is explicitly not decided** — ChatGPT
> accepted DEC-018's recommendation to split it into its own dedicated
> follow-up decision record instead; it remains open. **MBQ-64 and MBQ-65
> are untouched**, reserved for a separate currency/webhook residual
> decision sprint. Each of the ten accepted rows still carries its own
> exact-implementation-detail residual, routed to Implementation planning —
> see each row for what remains. Per `CLAUDE.md` §10, this acceptance
> **does not authorize implementation**; DEC-003 through DEC-017 remain
> unchanged; no code, Odoo module, or implementation plan was produced;
> **implementation remains blocked; the implementation gate remains
> closed.** Recommended next: a dedicated follow-up DEC for MBQ-62, then
> the separate MBQ-64/MBQ-65 currency/webhook residual decision sprint —
> neither is implementation.

> **DEC-019 proposed (2026-07-04) — MBQ-62 decision proposal prepared for
> ChatGPT review, not accepted (history).**
> [`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md)
> proposed a dedicated answer to MBQ-62 (extending Part A §D.2's job-source
> vocabulary with a seventh value, `odoo_event`, plus a required
> trigger-origin sub-classification). **Superseded by the acceptance note
> below.**

> **DEC-019 Acceptance Patch (2026-07-04) — MBQ-62 accepted at
> decision/semantic-classification level.** ChatGPT reviewed
> [`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) and
> **formally accepted it on 2026-07-04.** **Part A §D.2's job-source
> vocabulary is now extended with a seventh accepted semantic value,
> `odoo_event`** — a job enqueued because an Odoo-side business event
> occurred (not a webhook, not operator-initiated, not a timer, not a
> reconciliation pass, not a preview run). **Every `odoo_event` job must
> conceptually carry a trigger-origin sub-classification**; for MBQ-62 the
> accepted trigger-origin concepts are **"inventory stock-change trigger"**
> and **"fulfillment picking-validation trigger."** MBQ-62's own row below
> now carries this acceptance wording. **Exact Odoo implementation
> mechanics — model names, field names, Python constants, XML IDs,
> storage/Selection-field mechanics, trigger-origin field/model
> implementation, and MBQ-16 retry-count/backoff constants — remain
> implementation planning**, not decided by this acceptance. **No other MBQ
> row is changed by this acceptance; MBQ-64 and MBQ-65 remain untouched.**
> Per `CLAUDE.md` §10, this acceptance **does not authorize
> implementation**; DEC-003 through DEC-018 remain unchanged; no code,
> Odoo module, or implementation plan was produced; **implementation
> remains blocked; the implementation gate remains closed.** Recommended
> next: the separate MBQ-64/MBQ-65 currency/webhook residual decision
> sprint — not implementation.

> **DEC-020 proposed (2026-07-04) — MBQ-64/MBQ-65 residual decision
> prepared for ChatGPT review, not accepted.**
> [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
> proposes a dedicated design/selection answer for **MBQ-64** and
> **MBQ-65**. **MBQ-64 is not resolved until ChatGPT accepts DEC-020.
> MBQ-65 is not resolved until ChatGPT accepts DEC-020.** Their own rows
> below are **unchanged by this note** — the draft register-impact wording
> lives in DEC-020 §9 and is only applied by a future acceptance patch, if
> and when ChatGPT accepts. **No other MBQ row is changed by this note.**
> Per `CLAUDE.md` §10, this note **does not authorize implementation**;
> DEC-003 through DEC-019 remain unchanged; **implementation remains
> blocked; the implementation gate remains closed.**

> **DEC-020 revised (2026-07-04) — MBQ-64 corrected after ChatGPT REVISE;
> still not accepted.** ChatGPT's first review of `DEC-020` returned
> **REVISE for MBQ-64** (the original posture — shop currency for every
> Phase 1 order, divergence caught only via the numeric total-check guard —
> was not safe enough) and found **MBQ-65 directionally acceptable**,
> unchanged. `DEC-020` §4/§5 now propose: **Phase 1 automatic order import
> is same-currency only** (`Order.presentmentCurrencyCode ==
> Order.currencyCode`); for a divergent order, the connector **never**
> silently creates a normal Odoo sale order in shop currency, regardless of
> the total-check guard's outcome — the job is blocked from automatic SO
> creation and routed to manual review / treated as an explicit
> unsupported-scope case **before** SO creation. Both `shopMoney`/
> `presentmentMoney` and `presentmentCurrencyCode` remain captured as audit
> evidence in every case; presentment-currency-denominated Odoo orders
> remain non-MVP; MBQ-56's tolerance mechanics remain open and are not the
> (sole) mechanism relied upon for catching the divergence; the exact final
> error-class/sub-reason mapping for a blocked divergent-currency order
> remains implementation planning. **MBQ-64 is still not resolved — this
> revision does not change that.** MBQ-65 (enqueue-only triggers, mandatory
> follow-up authoritative read, never a direct write) is **unchanged**. **No
> other MBQ row is changed by this note.** Per `CLAUDE.md` §10, this note
> **does not authorize implementation**; DEC-003 through DEC-019 remain
> unchanged; **implementation remains blocked; the implementation gate
> remains closed.**

> **DEC-020 Acceptance Patch (2026-07-04) — MBQ-64 and MBQ-65 resolved at
> decision/posture level.** ChatGPT reviewed the revised
> [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
> and **formally accepted it on 2026-07-04, at decision/posture level for
> both rows.** **MBQ-64's** own row now reads: Phase 1 automatic order
> import is same-currency only; a divergent order (`presentmentCurrencyCode
> != currencyCode`) is blocked from automatic SO creation and routed to
> manual review / unsupported-scope handling before SO creation,
> independent of the total-check guard's outcome; both `shopMoney`/
> `presentmentMoney` and `presentmentCurrencyCode` are captured as audit
> evidence in every case; presentment-currency Odoo orders remain non-MVP.
> **MBQ-65's** own row now reads: `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/
> `PRODUCTS_DELETE` are implemented in Phase 1 as enqueue-only triggers,
> never a direct write, each job performing a follow-up authoritative read
> before any create/update/delete, with DEC-005 reconciliation as the
> required backstop; `PRODUCTS_DELETE` never directly deletes/archives the
> bound Odoo product. **For both rows, exact implementation mechanics
> remain implementation planning** — MBQ-56's own tolerance mechanics, the
> exact error-class/sub-reason mapping and enforcement mechanism for a
> blocked MBQ-64 order, and MBQ-65's exact controller/job/query/
> subscription mechanics and the still-unconfirmed variant-count
> payload-truncation claim are **not** decided by this acceptance. **No
> other MBQ row is changed by this acceptance; MBQ-62's accepted state
> (DEC-019) is not reopened or weakened.** Per `CLAUDE.md` §10, this
> acceptance **does not authorize implementation**; DEC-003 through DEC-019
> remain unchanged; **implementation remains blocked; the implementation
> gate remains closed.** Recommended next: a gate-readiness audit against
> `master-blueprint.md`'s five gate-opening criteria before any
> implementation — not implementation itself.

> **Core Naming/Schema Planning Acceptance Patch (2026-07-05) — MBQ-01,
> MBQ-02, MBQ-07, MBQ-16, MBQ-19, MBQ-20, MBQ-21 resolved; MBQ-44 partially
> resolved; MBQ-45 and MBQ-62 residuals resolved; MBQ-04 confirmed not
> resolved, explicitly descoped for slice 1.** After the implementation gate
> readiness audit (AR-018, accepted 2026-07-05) named a single
> documentation-only naming/core-schema implementation-planning artifact as
> the next session, ChatGPT reviewed
> [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md)
> (PR #85), returned **REVISE** once, then **formally accepted the revised
> document on 2026-07-05, at implementation-planning level only** (companion
> review-log entry **AR-019**,
> [`architecture-review-log.md`](../05-qa/architecture-review-log.md)).
> **MBQ-01 and MBQ-02** are now resolved for **core model names/field-types
> only** (`shopify.connector.store`, `.store.settings`, `.location`,
> `.binding.mixin`, `.job`, `.job.log`); domain-specific binding model names
> (MBQ-55) and view/menu XML IDs (MBQ-03) remain open. **MBQ-07** is now
> resolved for the exact `shopify.connector.store.settings` model shape.
> **MBQ-16** is now resolved for retry-count/backoff constants, accepted as
> adjustable implementation-planning defaults only. **MBQ-19** is now
> resolved for the job+log split (`shopify.connector.job` +
> `shopify.connector.job.log`). **MBQ-20** is now resolved for the
> `idempotency_key` schema; **MBQ-21** is now resolved for the DB-backed,
> race-safe `operation_scope_key` serialization guard, kept explicitly
> distinct from `idempotency_key`. **MBQ-44** is now partially resolved for
> planned core `ir.model.access.csv` row shapes only — no CSV file is
> created. **MBQ-45's residual** is now resolved for the exact group XML IDs
> (`group_shopify_connector_auditor`/`_operator`/`_reviewer`/`_admin`,
> `module_category_shopify_connector`). **MBQ-62's residual** is now resolved
> for the exact `odoo_event`/`trigger_origin` field mechanics on
> `shopify.connector.job`. **MBQ-04 is confirmed NOT resolved** — explicitly,
> fully descoped from the first core-only slice (Option A): no credential
> model, credential metadata model, or secret/token field of any kind is
> accepted; real credential persistence and the credential lifecycle schema
> both remain fully open, pending official Odoo evidence and a separate
> ChatGPT decision. **No other MBQ row is changed by this acceptance.** Per
> `CLAUDE.md` §10, this acceptance **does not authorize implementation**;
> DEC-003 through DEC-020 remain unchanged; `../04-decisions/README.md`
> remains unchanged; **no implementation task is created; no code, module,
> view, controller, security file, manifest, test, or CI file is created;
> implementation remains blocked; the implementation gate remains closed.**
> Recommended next: a separate, explicit ChatGPT implementation-gate-opening
> act, and the domain-scope MBQ rows this pass does not touch — neither is
> performed by this acceptance.

## How to read

- **Decision owner:** **ChatGPT** (a control-room decision), **Implementation
  planning** (resolved when the gated implementation-planning sprint writes
  the affected task), or **Official-doc verification** (a Tier-1
  Shopify/Odoo fact that must be verified and cited before use). Combined
  owners mean both are needed.
- **Blocks implementation:** **Yes** = the affected implementation task must
  not be written/coded until this row is resolved or ChatGPT explicitly
  accepts it as an open risk. **No** = can be resolved in parallel without
  blocking the first affected code. Blocking is scoped to the affected
  domain/feature, not the whole project.
- Rows route to the sprint that should resolve them (Part B/C/D per the
  index) where applicable.

---

## 1. Core / setup / config

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-01 | Exact Odoo **model names** for every core concept (store/connection, credential posture, settings/flags, Location reference, job, log, binding contract). **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for core model names only:** `shopify.connector.store`, `shopify.connector.store.settings`, `shopify.connector.location`, `shopify.connector.binding.mixin` (abstract), `shopify.connector.job`, `shopify.connector.job.log`. No credential model is included (see MBQ-04). Domain-specific binding model names (MBQ-55) and view/menu/action XML IDs (MBQ-03) remain open. | DEC-008; Part A §B–§D; AR-019 | Implementation cannot start without committed names; blueprint names are directions only | Resolved (core model names only) — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05); domain-specific binding model names remain Implementation planning | Yes for domain-specific binding model names (MBQ-55) and view/menu XML IDs (MBQ-03) only; No for the core model names themselves, which no longer block a core-only slice |
| MBQ-02 | Exact **field names/types** for every core concept. **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for core field names/types only:** field names/types for the six core models above (§4 of that document), including constraint/index design (§12). Domain-specific field names remain open. | Part A §B–§D; phase1-domain-model-brief; AR-019 | Same as MBQ-01; also fixes constraint/index design | Resolved (core field names/types only) — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05); domain field names remain Implementation planning | Yes for domain-specific field names only; No for the core field names/types themselves, which no longer block a core-only slice |
| MBQ-03 | Exact **view/menu/action XML IDs** for wizard, dashboard, sync center, error center, settings | DEC-012; Part A §E–§H | UI code needs committed IDs; DEC-012 explicitly left these open | Implementation planning | Yes |
| MBQ-04 | Exact **credential encryption/storage-at-rest mechanism** (Odoo field-level `groups` protection alone vs additional encryption; storage location). **Reviewed by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05): not resolved — explicitly, fully descoped from the first core-only slice (Option A).** No credential model, credential metadata model, or secret/token field of any kind is accepted for slice 1. Real credential persistence and the credential lifecycle schema itself both remain fully open, blocked pending official Odoo encryption-at-rest evidence and a separate ChatGPT decision; a future MBQ-04 session may propose a credential model once that evidence exists. | DEC-004; Part A §B.2; AR-019 | A long-lived offline token is a credential-leak risk if storage is wrong; DEC-004 fixed masking/least-privilege but not the storage mechanism | ChatGPT + Official-doc verification (Odoo capability check); first-slice descope confirmed by AR-019 (2026-07-05) | Yes for any credential-touching code (setup wizard credential entry, test-connection, real token storage); No for the core-only slice itself, which explicitly descopes credential persistence |
| MBQ-05 | Exact **custom-app creation surface** (merchant Admin-created vs Partner/Dev-Dashboard custom-distribution) and its **token-acquisition mechanics** (incl. non-expiring vs 90-day-rotation variant) | DEC-004 "What remains blocked" | Determines wizard step content and reconnect/rotation flow | Implementation planning (within DEC-004's fixed offline/unattended model) | Yes (setup wizard) |
| MBQ-06 | **Readiness-check list**: which checks are essential vs nice-to-have (scopes, HTTPS/`web.base.url`, webhook reachability, worker/queue presence, credential validity). **Accepted by ChatGPT via DEC-018 (2026-07-04):** essential readiness checks are credential validity/test-connection, required scopes, API-version health, store identity, `web.base.url` reachability, webhook HMAC secret (if webhooks enabled), cron/queue health, at least one mapped Location with an enabled domain, and intentional domain-flag enablement; all other candidate checks warn, never block. | setup-ux-principles P2; DEC-012 §1; Part A §E.6; DEC-018 | Fixes the wizard's pass/fail gate and the "connected" definition | Resolved — ChatGPT via DEC-018; exact copy/XML IDs (MBQ-03/22) and thresholds remain Implementation planning | Yes for exact copy/XML IDs/thresholds only; the essential-vs-nice-to-have split itself no longer blocks |
| MBQ-07 | **Resolved at blueprint-direction level by DEC-013 acceptance (2026-07-03):** store-scoped core settings record, domain-extended (Part A §I.3) — not `ir.config_parameter`, not `res.config.settings`-as-storage, not per-domain ad hoc settings models. **Resolved for the exact technical shape by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05):** a store-scoped `shopify.connector.store.settings` model (§5 of that document), distinct from the store/connection model, extended by domain modules via classic Odoo `_inherit`; exact Phase 1 field names: `product_domain_enabled`, `sale_domain_enabled`, `inventory_domain_enabled`, `fulfillment_domain_enabled`, `product_first_sync_source`, `price_source_of_truth`, `notification_default_enabled`. No feature flag may bypass a safety guard (unchanged). | DEC-008 "What remains open"; Part A §I; DEC-013; AR-019 | DEC-008 routed the mechanism to the Master Blueprint; flags gate every domain's behaviour | Resolved (direction + exact technical shape) — ChatGPT via DEC-013 and AR-019/core-naming-schema-planning.md (2026-07-05) | No — the technical feature-flag implementation is now resolved |
| MBQ-08 | **Store-disconnect data-retention posture** — what happens to bindings, jobs, logs, audit records after disconnect. **Accepted by ChatGPT via DEC-018 (2026-07-04):** disconnect revokes/removes stored credentials and disables sync/webhook enqueue, but preserves the store record, bindings, jobs, logs, audit records, and mapping/error history; reconnect is an explicit, separately-audited operator action and re-runs readiness checks (MBQ-06) before business sync resumes. | DEC-012 (Fable, PR #68); Part A §B.1; DEC-018 | Wrong posture destroys audit history or leaks stale credentials; affects disconnect UX and re-connect matching | Resolved — ChatGPT via DEC-018; exact field/state-machine implementation (MBQ-01/02) and reconnect-matching mechanics remain Implementation planning | Yes for exact implementation mechanics only; the posture itself no longer blocks |
| MBQ-09 | Whether **custom apps must implement Shopify's compliance webhooks / are bound by Level 1/2 protected-data obligations** regardless of distribution | DEC-004 (open since RB-14 Part 2) | If yes, compliance endpoints/duties enter Phase 1 scope; DEC-004 mandates conservative handling until resolved | Official-doc verification | Yes (any compliance-relevant code); conservative posture applies meanwhile |
| MBQ-10 | Whether Odoo.sh/on-prem setup can avoid mandatory **`odoo.conf`/queue prerequisites** (turnkey install path) | DEC-005; DEC-012 §1 open questions | Affects install docs and wizard prerequisites step; not a design blocker | Implementation planning + Official-doc verification | No |
| MBQ-54 | **Domain-module uninstall / disable data lifecycle** — if domain modules extend core settings (§I) or own concrete binding tables (§C.8), uninstall/disable behaviour must not silently lose bindings, logs, flags, or audit history. **Accepted by ChatGPT via DEC-018 (2026-07-04), posture only:** Phase 1 does not support destructive domain-module uninstall as a normal merchant-facing operation; a merchant who wants to stop using a domain disables it via the accepted feature-flag mechanism (Part A §I.4, "disabling must not delete history"); a full Odoo-level uninstall is technically guarded/blocked, or — if it cannot be fully blocked — treated as an explicitly unsupported, documented, disclosed operation. | Part A §I feature-flag mechanism; Part A §C binding shape; DEC-018 | A merchant disabling or uninstalling a domain module must not silently destroy binding/audit/log history — this is the module-lifecycle counterpart to the already-accepted "disabling must not delete history" rule (DEC-012 store settings §4; Part A §I.4), extended to the harder case of a full module **uninstall** | Resolved (posture) — ChatGPT via DEC-018; exact technical guard mechanism or disclosure copy remains Implementation planning | Yes for exact guard-mechanism/disclosure detail only; No for normal MVP sync — disable-not-uninstall is now the accepted Phase 1 posture |

## 2. Binding / dedup

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-11 | **Resolved by DEC-013 acceptance (2026-07-03):** per-domain concrete binding models extending a core abstract contract, with a cross-domain enumeration/registration seam and a binding-model granularity bound (Part A §C.8); the single polymorphic table option is not chosen | DEC-006 (fork left open); DEC-008 (binding-schema note); Part A §C.8; DEC-013 | Fixes where tables live, index/constraint design, and reconciliation-scale query shape | Resolved — ChatGPT via DEC-013 | No |
| MBQ-12 | **Shopify GID permanence/non-reuse** — not asserted by Shopify | DEC-006; RB-14 Part 2 (RQ-005-1) | Already handled defensively (stale/review, no silent recreate); official assertion would simplify, not change, the design | Official-doc verification (may remain unresolved) | No (defensive design stands) |
| MBQ-13 | Exact **stale/recreated-binding review flow detail** (fields shown, resolution actions, re-bind semantics) | DEC-006; Part A §C.6 | Operator resolution of stale/hijack cases must be auditable and safe | Implementation planning | No (behavioural rules fixed; detail refinable) |
| MBQ-14 | **`@idempotent` key uniqueness scope** (per-shop / per-app / global) and any API-version-specific behaviour | RB-14 Part 2 (RQ-005-2); DEC-009/DEC-010 | Determines how persisted idempotency keys are namespaced for safe retry | Official-doc verification | Yes (inventory/refund write code) |
| MBQ-15 | **Bulk Operation idempotency/resumability semantics** (if bulk is used internally for backfills) | DEC-004 (internal-mechanism note); DEC-003 | Bulk backfills must be resumable/safe for partial failure | Official-doc verification + Implementation planning | Yes, only if/when internal bulk is used |

## 3. Job / log / error / retry

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-16 | Exact **retry-count ceilings and backoff constants** per auto-retryable class. **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for retry/backoff planning defaults:** retry ceilings and a backoff schedule by error-class family (§9 of that document), **accepted as adjustable implementation-planning defaults, not final production-tuned values.** Cron cadence/batch-size constants (MBQ-18) are tracked separately and are not resolved by this row. | DEC-009 (`[Implementation-planning default]`); AR-019 | Under-retry loses syncs; over-retry storms the rate limit | Resolved (planning defaults) — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05) | No — retry-count ceilings/backoff constants are now resolved as adjustable planning defaults |
| MBQ-17 | **Reconciliation cadence and scope** (per-object vs global; interval). **Posture accepted by ChatGPT via DEC-018 (2026-07-04):** reconciliation is per-store, per-domain — never a single global cross-domain job; cadence is configurable per store/domain with a conservative (infrequent), rate-limit/GraphQL-cost-aware default. | DEC-005 → DEC-009 "What remains open"; DEC-018 | Reconciliation is the mandatory correctness backstop; cadence trades freshness vs GraphQL cost | Resolved (posture) — ChatGPT via DEC-018; exact interval/batch-size constants remain Implementation planning | Yes for exact constants only; the per-store/per-domain posture itself no longer blocks |
| MBQ-18 | Exact **cron cadence and throughput limits** — batch sizes, drain interval, validation under `--max-cron-threads=2` and Odoo.sh best-effort cron | DEC-005; DEC-010 | The queue must provably drain at MVP scale within hosting constraints | Implementation planning (incl. MVP-scale testing) | Yes (constants before code); throughput validation blocks release readiness, not code start |
| MBQ-19 | Exact **job/log model shape** (single job model vs job+log split; payload storage). **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05):** a job+log split — `shopify.connector.job` (current state, error class, retry counters) + `shopify.connector.job.log` (append-only per-attempt/event history); error/manual-review fields live on `job`; payload/evidence snapshots live on `job.log`; `job.log.job_id` uses non-destructive `ondelete='restrict'` (not `cascade`). | phase1-domain-model-brief Domain 8; Part A §D; AR-019 | The substrate every domain depends on; must be fixed once, early | Resolved — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05) | No — the job/log model shape is now resolved |
| MBQ-20 | Exact **operation-level idempotency key schema** (field names/types for operation type, Shopify target ID, payload version/hash). **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05):** `idempotency_key` on `shopify.connector.job` — computed from `store_id` + `job_type` + `res_model`/`res_id` + `shopify_target_gid` + `payload_hash`, unique per `(store_id, idempotency_key)`; persists for the job's life; prevents duplicate connector-side processing of the same operation. Kept explicitly distinct from the serialization-guard key (`operation_scope_key`, MBQ-21). | DEC-011 (conceptual shape set); Part A §D.6; AR-019 | Prevents connector-side duplicate processing across all domains | Resolved — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05) | No — the idempotency key schema is now resolved |
| MBQ-21 | Exact **serialization-guard mechanism** for unresolved ambiguous operations (queue-level lock vs DB constraint vs job-state check). **Resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05):** a DB-backed, race-safe mechanism — `operation_scope_key` on `shopify.connector.job`, computed from `store_id`+`res_model`+`res_id`+`shopify_target_gid`, populated only while the job is non-terminal and cleared to `NULL` on reaching a terminal state, under a unique constraint on `(store_id, operation_scope_key)`. Not a query-time-only check, not a separate model, and not a queue-level lock table. | DEC-011; Part A §D.7; AR-019 | Prevents a corrected operation dispatching while a prior ambiguous one is unresolved | Resolved — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05) | No — the serialization-guard mechanism is now resolved |
| MBQ-22 | Exact **user-facing copy/wording** for error reasons, suggested fixes, wizard steps, dashboard labels | DEC-009/DEC-012 (structure fixed, copy open) | Copy quality is an operator-experience differentiator; structure already fixed | Later UI-design pass | No |

## 4. Product / customer / order (routed to Sprint B)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-23 | Exact **variant-write mutation strategy** (`productSet` vs `productVariantsBulkCreate`/`productVariantsBulkUpdate` vs combination). **Partially resolved by DEC-014 acceptance (2026-07-03):** direction accepted — prefer `productVariantsBulkCreate`/`productVariantsBulkUpdate` for variant-only updates after first export, `productSet` for first-time combined export/full resync (`master-blueprint-product-customer-sale.md` §A.5.2, citing verified `productSet`/`productVariantsBulkCreate`/`productVariantsBulkUpdate` official docs, accessed 2026-07-03). Exact implementation choice remains open. | DEC-007 §1; DEC-014 | Different mutations have different delete-on-omit/partial-failure semantics | Official-doc verification + Implementation planning (direction accepted; detail remains) | Yes (product export) |
| MBQ-24 | Whether **`productSet` delete-on-omit applies to product/variant media** identically to variants/collections/metafields. **Carried forward, open (Sprint B checked, not resolved):** official `productSet` docs (accessed 2026-07-03) name `collections`/`metafields`/`variants` as list-field examples but do not name or exclude media — still unconfirmed either way. Safety posture (preview guard) applies regardless (`master-blueprint-product-customer-sale.md` §A.13). | DEC-007 §2 | Determines whether image export needs the same full-state-diff guard | Official-doc verification (Sprint B) | Yes (image export) |
| MBQ-25 | Exact **Shopify draft/publish mechanism** to key draft-first export off. **Partially resolved by DEC-014 acceptance (2026-07-03):** mechanism accepted — `Product.status` enum (`active`/`archived`/`draft`/`unlisted`) + `productCreate`'s unpublished-by-default behaviour + explicit `publishablePublish` mutation (`master-blueprint-product-customer-sale.md` §A.10, accessed 2026-07-03). Exact channel-selection UX remains open. | DEC-012 §7; DEC-014 | Draft-first export safety depends on the concrete status/channel mechanism | Official-doc verification + Implementation planning (direction accepted; detail remains) | Yes (product export) |
| MBQ-26 | **Order-import operator touchpoints** — fully covered by the error center/manual-review flow, or a dedicated order-import flow needed. **Accepted at blueprint level by DEC-014 (2026-07-03):** the existing error-center/sync-center surfaces (Part A §G/§H), extended with an inline financial-evidence breakdown and direct matching-flow links, are accepted as sufficient — **no dedicated order-import screen is authorized or required** (`master-blueprint-product-customer-sale.md` §C.14). This was ChatGPT's direct decision as MBQ-26's named decision owner. | DEC-012 (Fable, PR #68); DEC-007 §6; DEC-014 | Determines whether Sprint B adds an operator surface beyond the core error center | Resolved at blueprint level — ChatGPT via DEC-014 | No |
| MBQ-27 | Exact **mechanism for representing Shopify-computed tax** on an Odoo sale order without Odoo's tax engine recomputing/overriding, keeping totals reconcilable. **Carried forward, open (Sprint B checked, inconclusive):** an official-doc check of Odoo 19 accounting/taxes documentation (accessed 2026-07-03) confirmed a "Tax Included" price mode exists but did not resolve the manual/externally-supplied tax-amount mechanism (`master-blueprint-product-customer-sale.md` §C.17). Mechanism remains unverified. | DEC-007 §6; domain brief Domain 5 | Totals-reconcilability is a correctness requirement; mechanism unverified | Official-doc verification + Implementation planning (Sprint B) | Yes (order import) |
| MBQ-28 | **Domain 9 draft-artifact guard** — whether any draft invoice/payment artifact is absolutely required for a valid Odoo order flow. **Not triggered by Sprint B** (`master-blueprint-product-customer-sale.md` §C.11/§C.17). | DEC-003 (guard); DEC-007 §6 | If triggered, returns to ChatGPT before implementation; no silent invoice/payment creation | ChatGPT (if triggered by Sprint B/implementation planning) | Yes, if triggered |
| MBQ-29 | **Default-customer fallback** behaviour for no-PII Shopify plans. **Partially resolved by DEC-014 acceptance (2026-07-03):** direction accepted — a single, clearly-flagged fallback partner per store, used only for genuine no-PII orders, never for ordinary matching failures (`master-blueprint-product-customer-sale.md` §B.7). Whether one shared fallback partner per store is sufficient, or per-order anonymous identity is needed, remains open. | domain brief Domain 4; DEC-014 | Order import must not fail or invent PII when customer data is unavailable | Implementation planning (direction accepted; granularity remains) | Yes (customer/order import) |
| MBQ-30 | **Gateway → Odoo journal mapping** configuration surface (classification/routing input only). **Partially resolved by DEC-014 acceptance (2026-07-03):** concept accepted — a per-store gateway-label → `account.journal` mapping, classification/routing input only, contributed via the core settings-extension seam (`master-blueprint-product-customer-sale.md` §C.10). Exact schema/fields remain open. | DEC-003 Domain 9; domain brief Domain 5; DEC-014 | Config input for evidence routing; no accounting automation implied | Implementation planning (concept accepted; schema remains) | No |
| MBQ-31 | Final **customer match-key set** (email-only vs multi-key) beyond the accepted binding→email→manual order. **Accepted at blueprint level by DEC-014 (2026-07-03):** **email is the sole automatic customer match key** (beyond existing binding); phone/name stay advisory/manual-only (`master-blueprint-product-customer-sale.md` §B.13). This was ChatGPT's direct decision as MBQ-31's named decision owner. | DEC-006; domain brief Domain 4; DEC-014 | Wrong keys create duplicate partners; accepted priority stands, exact set refinable | Resolved at blueprint level — ChatGPT via DEC-014 | No |
| MBQ-55 | Exact **Odoo model/field names** for the four Sprint B-defined binding models: product-template binding, product-variant binding, customer binding, order binding | Sprint B (`master-blueprint-product-customer-sale.md` §A.1/§B.1/§C.1) | Domain-specific extension of MBQ-01/02 to the Sprint B binding models — implementation cannot start without committed names | Implementation planning | Yes |
| MBQ-56 | Exact **total-check guard tolerance/comparison mechanism** — the exact Shopify total field(s) used, currency-rounding tolerance, and which evidence components are summed | Sprint B (`master-blueprint-product-customer-sale.md` §C.8) | The total-check guard is mandatory and permanent; its exact comparison logic is not yet fixed | Implementation planning | Yes (order import) |
| MBQ-57 | Whether the **whole-order-hold rule** for an unmatched product line (§C.5) should ever have an alternative (e.g. partial-line placeholder) for a future phase | Sprint B (`master-blueprint-product-customer-sale.md` §C.5) | Recorded for future reconsideration; the current guard-consistent rule is not weakened by leaving this open | ChatGPT (future, only if revisited) | No (current rule stands unless revisited) |
| MBQ-58 | **Shopify order-identity stability nuances** beyond general GID-non-permanence (e.g. test-mode orders, draft orders later converted) | Sprint B (`master-blueprint-product-customer-sale.md` §C.3) | The existing binding-based defensive design (Part A §C.6) already covers the general case; this refines it, not a blocker | Official-doc verification | No (defensive design already stands) |
| MBQ-59 | Exact **automated (webhook/scheduled/reconciliation) import create/bind policy and preview semantics** — whether/how an automated product/customer create satisfies the accepted "no blind create" rule. **Added in PR #72 revision; revised again in the Fable-review revision; accepted at blueprint-policy level by DEC-014 (2026-07-03):** a pre-create duplicate check plus a two-tier gate — eligibility conditions (setup complete, domain enabled, source strategy permits creation) routed via Part A's accepted enqueue/cancel mechanisms (§E.5/§I.3/§I.4, never `blocked_manual_review`), and match-quality conditions (confident match or confident no-match-creation candidate; no ambiguous-match/binding-conflict/duplicate-risk/destructive-write-guard condition) routed via Part A's accepted confirmation-required `blocked_manual_review` classes (§D.5.4/§D.8) when failed — fully logged (§D.10/§C.4); retrospective sync-center/dashboard visibility is audit only, never a preview substitute (`master-blueprint-product-customer-sale.md` §A.2/§A.9/§B.2/§B.9/§C.6). Replaces this document's withdrawn earlier reading that retrospective visibility satisfied the preview requirement, and the earlier reading that every gate failure collapsed into `blocked_manual_review`. **The policy is accepted; exact eligibility-check/match-confidence implementation detail remains open for implementation planning.** | Sprint B revision (§A.2/§B.2); DEC-014; tension between DEC-003/DEC-006 "no blind create" and DEC-005 layered automation, resolved via the accepted Part A/DEC-013 per-class routing | Prevents weakening the accepted no-blind-create rule while still allowing webhook/scheduled import to operate without a synchronous per-record human click for every confident, unambiguous create, without misusing Part A's accepted state/class vocabulary | Resolved at blueprint-policy level — ChatGPT via DEC-014; exact implementation detail remains Implementation planning | Yes (exact eligibility-check/match-confidence implementation detail; policy itself no longer blocks) |
| MBQ-64 | **Resolved at decision/posture level by DEC-020 acceptance (2026-07-04)** (originally added by the Part E pre-implementation research patch, PR #78 audit cross-check addendum; accepted at fact-verification level only by DEC-017). Exact **currency-comparison mechanism** for the total-check guard and the price source-of-truth mechanism. **Accepted as verified fact (DEC-017):** Shopify order-money fields are `MoneyBag`-typed (`shopMoney` + `presentmentMoney`, both non-null on every order-total field), while an Odoo `sale.order` carries exactly **one** computed `currency_id` (pricelist currency, else company currency). **Accepted by ChatGPT via DEC-020 (2026-07-04), at decision/posture level:** [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md) decides that **Phase 1 automatic order import is same-currency only** — for orders where `Order.presentmentCurrencyCode == Order.currencyCode`, Odoo `sale.order.currency_id` is driven by the connector's normal configured pricelist/company currency, aligned to Shopify shop currency. For orders where `Order.presentmentCurrencyCode != Order.currencyCode`, the connector **must not** silently create/import a normal Odoo sales order in shop currency, regardless of the total-check guard's outcome — the job is **blocked from automatic sale-order creation** and routed to manual review / treated as an explicit unsupported-scope case, **before** SO creation. Both `shopMoney` and `presentmentMoney` amounts, plus `Order.presentmentCurrencyCode`, are captured as audit/reconciliation evidence in every case. Presentment-currency-denominated Odoo orders (Shopify Markets/multi-currency order-currency driver) remain explicitly **non-MVP** unless and until a later, explicit scope expansion designs currency/pricelist provisioning. **MBQ-56's total-check tolerance/comparison mechanics remain their own open residual**, unchanged and not relied upon as the (sole) mechanism for catching a currency-model divergence. **The exact final error-class/sub-reason mapping for a blocked divergent-currency order — and the exact enforcement mechanism (manual-review queue vs. unsupported-scope classification) — remain implementation planning**, not decided by this acceptance. | PR #78 audit §6 cross-check addendum ("Shopify multi-currency/presentment-currency order model"; "Odoo multi-currency/pricelist ORM behavior"); DEC-017 (fact-verification acceptance); DEC-020 (decision/posture-level acceptance); complements **MBQ-56** (total-check guard tolerance/comparison mechanism, `master-blueprint-product-customer-sale.md` §C.8, still open) and **DEC-007 §3** (price source-of-truth, which excludes "any currency-/market-specific pricing strategy" from Phase 1 scope, consistent with DEC-020's non-MVP framing) | The total-check guard (§C.8, "mandatory and permanent") and price source-of-truth mechanism both implicitly assumed single-currency comparison; DEC-020 resolves this by scoping automatic import to same-currency orders and blocking divergent orders before SO creation, independent of whether the total-check guard would otherwise pass, so a back-converted shop-currency total can never be silently treated as sufficient evidence a divergent order is safe to import | Resolved (decision/posture level) — ChatGPT via DEC-020; exact error-class/sub-reason mapping, exact enforcement mechanism, MBQ-56's tolerance value, and exact Odoo field/model names for presentment evidence (MBQ-01/02) remain Implementation planning | Yes for exact error-class/sub-reason mapping, enforcement mechanism, and MBQ-56's own tolerance mechanism only; No for the decision posture itself (same-currency-only automatic import; divergent-order block independent of the total-check guard), which no longer blocks |
| MBQ-65 | **Resolved at decision/posture level by DEC-020 acceptance (2026-07-04)** (originally added by the Part E pre-implementation research patch, PR #78 audit cross-check addendum; topic strings accepted at fact-verification level only by DEC-017). Exact **Shopify product-domain webhook topic strings** for webhook-driven product create/update/delete triggers, and whether/how webhook-driven product import is implemented in Phase 1. **Accepted as verified fact (DEC-017):** `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, and `PRODUCTS_DELETE` confirmed against the official `WebhookSubscriptionTopic` enum — the direct product-domain analog of **MBQ-37**'s inventory-topic resolution. **Accepted by ChatGPT via DEC-020 (2026-07-04), at decision/posture level:** [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md) decides that `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/`PRODUCTS_DELETE` **are implemented in Phase 1 as enqueue-only triggers** — never a direct write — each enqueued job performing a **follow-up authoritative read** before any create/update/delete is applied to Odoo, with the existing DEC-005 layered-sync reconciliation pass as the required backstop regardless of webhook health. A `PRODUCTS_DELETE` webhook **never directly deletes/archives** the bound Odoo product; ambiguous or unconfirmable cases route to manual review via existing error-class vocabulary, none invented. **The exact subscription mechanism, controller shape, follow-up-read query shape, job-source classification, and handling of the still-unconfirmed variant-count payload-truncation claim all remain implementation planning**, not decided by this acceptance. | PR #78 audit §6 cross-check addendum ("Shopify product-domain webhook topic strings"); `master-blueprint-product-customer-sale.md` §A.2 (topic strings previously flagged "not verified/cited this sprint"); DEC-017 (fact-verification acceptance); DEC-020 (decision/posture-level acceptance) | Webhook-driven product import cannot be built on an unverified topic string; DEC-020 resolves the implementation-scope question by adopting an enqueue-only, never-direct-write posture with a mandatory follow-up authoritative read, so a stale, out-of-order, or incomplete webhook payload (delivery/ordering not guaranteed, per Shopify's own documentation) can never drive a silent product write; the accepted layered sync (scheduled/manual/reconciliation) stands as the required backstop regardless, mirroring the accepted inventory posture (MBQ-37/MBQ-63) | Resolved (decision/posture level) — ChatGPT via DEC-020; exact controller/job/query/subscription implementation mechanics, and the still-unconfirmed variant-count payload-truncation claim, remain Implementation planning | Yes for exact controller/job/query/subscription implementation mechanics only; No for the decision posture itself (enqueue-only, never-direct-write, mandatory follow-up read), which no longer blocks — mirroring MBQ-37's resolved-topic-string treatment |

## 5. Inventory (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-32 | Exact **Odoo ORM source/field/formula behind "Free to Use"** (and whether a configurable Forecast/On-Hand/Free-to-Use default is offered). **Partially resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** two candidate sources cited against official Odoo 19.0 source (`master-blueprint-inventory-fulfillment.md` §A.4, accessed 2026-07-03) — `product.product.free_qty` (compute `product.uom_id.round(qty_available − reserved_quantity − expired_unreserved_qty)`, UoM-rounded) and per-location `stock.quant.available_quantity` (`quantity − reserved_quantity`, no UoM-rounding shown). **Fable finding C1 (corrected):** these two sources are verified but **not equivalent** — they diverge whenever expired unreserved stock exists, since only `free_qty` nets that term out; the source choice is substantive, not cosmetic, and this acceptance does not choose a final implementation source. Whether the connector reads `free_qty` via location context, aggregates `stock.quant.available_quantity` directly (and if so, how it would also net out expired-unreserved stock to match `free_qty`'s semantics), or uses a third reconciling mechanism, and whether a configurable default is offered, remain implementation planning. This row stays **open** for that residual. | DEC-010 (semantic concept decided; source unverified) | Pushing the wrong Odoo quantity to Shopify `available` over/under-sells live stock | Official-doc verification (Odoo 19 source) — **Partially resolved by DEC-015 acceptance** | Yes for the residual source-selection/aggregation-mechanism/configurable-default detail; the two candidate sources' field/formula facts are accepted as verified |
| MBQ-33 | Exact **granularity of "first"** for the first-push guard (per-store / per-binding / per-variant-location), no coarser than per-store. **Accepted by ChatGPT via DEC-018 (2026-07-04),** adopting DEC-015's carried recommendation in full: the guard fires no coarser than per (store + mapped Odoo-Location ↔ Shopify-Location pair) + product/variant binding (`master-blueprint-inventory-fulfillment.md` §A.5); a batched review UI is permitted only if each pair's confirmation is individually recorded. | DEC-007 §4; DEC-010; DEC-018 | Fixes where the guard/confirmation record attaches | Resolved — ChatGPT via DEC-018; exact confirmation-record schema (MBQ-38) and batched-review UI/UX remain Implementation planning | Yes for exact schema/UI detail only; the granularity itself no longer blocks |
| MBQ-34 | **Ongoing apply-mode** — auto-apply vs review-then-apply for post-first-push writes (C-INV-04). **Accepted by ChatGPT via DEC-018 (2026-07-04),** adopting DEC-015's carried recommendation in full: review-then-apply is the Phase 1 default for all ongoing (post-first-push) inventory writes, consistent with DEC-003's "auto-apply not accepted as default" (`master-blueprint-inventory-fulfillment.md` §A.7/§G); auto-apply is not offered as a Phase 1 default and may only be introduced later behind an explicit, separately-decided feature flag. | DEC-003; DEC-010; DEC-018 | Auto-apply was explicitly not accepted as default MVP behaviour; must be decided, not assumed | Resolved — ChatGPT via DEC-018; exact review-queue UX/copy and any future auto-apply feature-flag design remain Implementation planning | Yes for exact UX/copy detail only; the apply-mode default itself no longer blocks |
| MBQ-35 | Whether **`on_hand` is ever exposed as a Phase 1 UI choice** at all (requires explicit justification; `available` is the default; `committed` never). **Carried forward, open, unchanged — Sprint C introduces no new evidence** on this row (`master-blueprint-inventory-fulfillment.md` §A.4/§A.12). | DEC-010; DEC-012 §8 | Prevents mis-mapping a multi-state sum; structural exclusions already stand | ChatGPT (Sprint C) | No (default path is fixed; exposure decision needed only before any `on_hand` UI) |
| MBQ-36 | Exact **mutation choice per trigger type** (`inventorySetQuantities` preferred default vs `inventoryAdjustQuantities` for deltas). **Partially resolved by DEC-015 acceptance (2026-07-03):** direction accepted — `inventorySetQuantities` (compare-and-set) as the default for all trigger types; `inventoryAdjustQuantities` a candidate for narrower single-delta event-driven pushes only (`master-blueprint-inventory-fulfillment.md` §A.13/§G). Exact per-trigger choice, batching, and error handling remain open for implementation planning. | DEC-010 | Compare-and-set vs delta semantics differ under concurrency | Implementation planning — direction accepted by DEC-015; exact per-trigger/batching/error-handling detail remains | Yes |
| MBQ-37 | **Shopify inventory webhook topic string(s)** — unverified in repo docs. **Resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** `INVENTORY_LEVELS_UPDATE` (plus `INVENTORY_LEVELS_CONNECT`/`INVENTORY_LEVELS_DISCONNECT`), confirmed against the official Shopify `WebhookSubscriptionTopic` enum (`master-blueprint-inventory-fulfillment.md` §A.9, accessed 2026-07-03). The underlying fact is accepted as verified; this row is resolved at fact-verification level. | DEC-010; ar007-ar008-evidence-refresh | Webhook-driven import can't be built on an unverified topic; layered sync stands regardless | Official-doc verification — **Resolved by DEC-015 acceptance** | No for the topic-string fact itself; the broader payload-shape/subscription-mechanics/Phase-1-implementation-scope residual still blocks webhook-driven inventory import specifically — see MBQ-63 |
| MBQ-38 | Exact **first-push confirmation record schema** (what is persisted: preview snapshot, confirmer, source-of-truth, scope). **Partially resolved by DEC-015 acceptance (2026-07-03):** blueprint-level concept accepted — extends the Part A guard/audit record shape with a preview snapshot, confirming operator + timestamp, recorded source-of-truth, and scope (`master-blueprint-inventory-fulfillment.md` §A.5). Exact field names/schema remain open for implementation planning. | DEC-010 | The guard's audit/idempotency anchor (DEC-009 layer) | Implementation planning — concept accepted by DEC-015; exact schema/field names remain open | Yes |

## 6. Fulfillment (routed to Sprint C)

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-39 | Exact **Odoo tracking-reference field source** (carrier/tracking fields on `stock.picking`/delivery). **Resolved by DEC-015 acceptance (2026-07-03), official-doc verification:** `stock.picking.carrier_tracking_ref` (Char), `carrier_tracking_url` (computed Char, via `carrier_id.get_tracking_link(picking)`), and `carrier_id` (Many2one to `delivery.carrier`), all defined in Odoo 19.0's `stock_delivery` module, cited against official Odoo source (`master-blueprint-inventory-fulfillment.md` §B.5, accessed 2026-07-03). **Surfaces new open question MBQ-60**, which remains open (whether `stock_delivery`/`delivery` is a required Odoo dependency). This row is resolved at fact-verification level. | DEC-011; ar007-ar008-evidence-refresh | Tracking write-back needs a verified source field | Official-doc verification (Odoo 19) — **Resolved by DEC-015 acceptance** | No for the tracking-field fact itself; see MBQ-60, which remains open, for the module-dependency question |
| MBQ-40 | Exact **backorder-to-picking linkage** fields/rules for sequential partial fulfillments. **Partially resolved by DEC-015 acceptance (2026-07-03):** `stock.picking.backorder_id` (Many2one, "Back Order of") and reverse `backorder_ids` (One2many) cited against official Odoo 19.0 source (`master-blueprint-inventory-fulfillment.md` §B.7, accessed 2026-07-03). The delivery-specific backorder-wizard UX/copy nuance flagged by `ar007-ar008-evidence-refresh.md` was not independently re-verified this sprint and remains open. | DEC-011 | Each backorder picking is its own fulfillment event; linkage must be exact | Official-doc verification + Implementation planning — finding accepted by DEC-015 | Yes, for the residual wizard-UX/copy detail |
| MBQ-41 | Exact **notification-UI granularity** (global/per-store minimum decided; per-order override open). **Accepted by ChatGPT via DEC-018 (2026-07-04),** adopting DEC-015's carried recommendation in full: a global/per-store notification-default setting (default off) is sufficient for Phase 1 MVP (`master-blueprint-inventory-fulfillment.md` §B.6); no per-order override ships in Phase 1 unless standard Odoo's own delivery flow already exposes one without added connector UI — per-order override is explicitly deferred, not rejected. | DEC-007 §5; DEC-011; DEC-018 | Operator control surface for the notification guard | Resolved — ChatGPT via DEC-018; whether standard Odoo already exposes a per-order toggle is an implementation-time check | Yes only if a per-order override beyond the per-store default is later proposed; the Phase 1 default itself no longer blocks |
| MBQ-42 | Exact **fulfillment location-confirmation mechanism** (core Shopify Location reference vs live FulfillmentOrder `assignedLocation` read, or both; live read treated as authoritative unless proven otherwise). **Partially resolved by DEC-015 acceptance (2026-07-03):** mechanism accepted — a live `assignedLocation` read is authoritative for a specific operation; the core Location reference is used only for naming/display and mismatch-detection, never as an override authority; a mismatch routes to the existing `ambiguous match` class, **its applicability widened to also cover this deterministic scenario, accepted at blueprint level only** (`master-blueprint-inventory-fulfillment.md` §B.8). Exact implementation-level detail (e.g. sub-reason tagging) remains open for implementation planning. | DEC-010/DEC-011 | Prevents fulfilling from a mismatched location without depending on inventory's mapping | Resolved at blueprint level — ChatGPT via DEC-015; exact implementation detail remains Implementation planning | Yes (exact implementation-level detail; mechanism itself no longer blocks) |
| MBQ-43 | **Core Location reference cache policy** — stale-cache handling, refresh cadence, precedence vs live reads. **Partially resolved by DEC-015 acceptance (2026-07-03):** precedence rule accepted — a live read always wins over the cache for a specific operation, cache refreshed on setup-readiness checks and the shared reconciliation cadence (`master-blueprint-inventory-fulfillment.md` §B.8). Exact refresh cadence/mechanism remains open for implementation planning. | DEC-010/DEC-011; Part A §B.4 | A stale cache must never override live Shopify state for a specific operation | Implementation planning — rule accepted by DEC-015; exact refresh cadence/mechanism remains open | Yes (fulfillment/inventory location checks) |
| MBQ-60 | Whether `shopify_connector_fulfillment` requires the Odoo **`stock_delivery`** (or `delivery`) module as a dependency for the `carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id` fields identified this sprint (§B.5), and what tracking write-back does if a merchant's database does not have that module installed. **Accepted by ChatGPT via DEC-018 (2026-07-04):** `shopify_connector_fulfillment` requires Odoo's `stock_delivery` (or the lighter `delivery`) module for tracking write-back; if a merchant's database lacks that module, tracking write-back is disabled and reported as a named, specific readiness/health blocker (MBQ-06), never a silent no-op or a degraded partial write. | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.5), newly surfaced by this sprint's official-doc verification — not previously discussed by DEC-008's module family or DEC-011; DEC-018 | These fields live in an installable Odoo module distinct from core `stock`; if not installed, tracking write-back has no field to write to, and DEC-008's module family did not previously name any standard Odoo module dependency beyond core/base | Resolved — ChatGPT via DEC-018; manifest `depends` mechanics and exact readiness-check wording remain Implementation planning | Yes for exact manifest/readiness wording only; the dependency posture itself no longer blocks |
| MBQ-61 | Whether/how the connector must react to Shopify-side **FulfillmentOrder lifecycle events beyond simple creation** — holds (`FULFILLMENT_ORDERS_PLACED_ON_HOLD`/`HOLD_RELEASED`), cancellation-request lifecycle, merges, splits, moves, reschedules — newly confirmed as real Shopify webhook topics this sprint (§B.11) but not discussed by DEC-011 at all | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.11), newly surfaced by this sprint's official-doc verification of the full `WebhookSubscriptionTopic` enum | A FulfillmentOrder placed on hold by Shopify could silently reject or delay an Odoo-triggered `fulfillmentCreate` call if the connector has no visibility into hold state before attempting fulfillment; DEC-011 did not consider these lifecycle events at all | ChatGPT (whether/how to react) + Implementation planning | No for MVP correctness-core fulfillment creation (the existing ambiguous-outcome/manual-review handling already catches a rejected call); Yes if a dedicated hold-aware UX is later required |
| MBQ-62 | **New, Fable finding C2.** Exact **Part A §D.2 job-source classification for Odoo-side event-triggered jobs** — specifically (a) an inventory push enqueued by a relevant Odoo stock change (§A.7), and (b) a fulfillment creation triggered by a validated `stock.picking` (§B.3/§B.12). DEC-010 accepted the Odoo-side event trigger as a **sync-trigger layer**, not as an addition to Part A §D.2's fixed job-source enum (`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`); this sprint's own first draft silently listed `event-driven enqueue` as if it were one of those six values, which Fable flagged as unauthorized vocabulary extension. **DEC-018 note (2026-07-04):** DEC-018 reviewed this row against all six fixed job-source values, found none a defensible fit, and recommended splitting it into its own dedicated follow-up decision record rather than forcing a same-batch answer — ChatGPT accepted that recommendation. **This row remains open and undecided**; no mapping or vocabulary extension is adopted by DEC-018. **Accepted by ChatGPT via DEC-019 (2026-07-04), at decision/semantic-classification level:** [`DEC-019`](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md) extends Part A §D.2's job-source vocabulary with a seventh accepted semantic value, `odoo_event` — a job enqueued because an Odoo-side business event occurred (not a webhook, not manual sync, not scheduled sync, not reconciliation, not setup readiness, not export preview dry run). Every `odoo_event` job must conceptually carry a trigger-origin sub-classification; the accepted trigger-origin concepts for this row are **"inventory stock-change trigger"** and **"fulfillment picking-validation trigger."** An inventory push enqueued by a relevant Odoo stock change is classified as `job_source = odoo_event`, trigger-origin = "inventory stock-change trigger"; a fulfillment creation triggered by a validated `stock.picking` is classified as `job_source = odoo_event`, trigger-origin = "fulfillment picking-validation trigger." **Exact Odoo implementation mechanics — model names, field names, Python constant names, XML IDs, storage/Selection-field mechanics, trigger-origin field/model implementation, and MBQ-16 retry-count/backoff constants — remain implementation planning**, not decided by this acceptance. **Residual resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for the exact implementation mechanics:** `job_source` Selection value `odoo_event` and `trigger_origin` Selection field on `shopify.connector.job`, with values `inventory_stock_change`/`fulfillment_picking_validation`, extensible via `selection_add`; `trigger_origin` is required only when `job_source = odoo_event` (validation-rule concept, §7 of that document). The semantic classification itself remains DEC-019, unchanged — this acceptance fixes only the field/model mechanics; MBQ-16's own retry-count/backoff constants are resolved separately by MBQ-16's own row. | Sprint C (`master-blueprint-inventory-fulfillment.md` §A.7/§A.13/§B.12/§C item 7), Fable review of PR #74 — not previously decided by DEC-010, DEC-011, or Part A (DEC-013); reviewed, not decided, by DEC-018; resolved at decision/semantic-classification level by DEC-019; exact mechanics resolved by AR-019 | Every job must record a Part A job source for dashboard/sync-center display and retry-policy lookup (Part A §D.2/§F/§G); an undecided or silently-invented source value would leave these two genuinely common triggers (an Odoo stock change; a picking validation) without a defined, accepted classification | Resolved (decision/semantic-classification level + exact implementation mechanics) — ChatGPT via DEC-019 and AR-019/core-naming-schema-planning.md (2026-07-05) | No — both the semantic classification and the exact implementation mechanics are now resolved |
| MBQ-63 | **New, Fable minor finding 4.** Exact **Shopify inventory webhook payload shape and subscription mechanics** for `INVENTORY_LEVELS_UPDATE`/`INVENTORY_LEVELS_CONNECT`/`INVENTORY_LEVELS_DISCONNECT` (payload fields, required subscription scopes beyond `read_inventory`, delivery/registration mechanics), and **whether webhook-driven inventory import is implemented in Phase 1 at all** or left purely as a drift-detection candidate (§A.7/§A.9 already treat it as "candidate... never the sole mechanism," but do not decide implementation-vs-candidate-only status) | Sprint C (`master-blueprint-inventory-fulfillment.md` §A.7/§A.9), Fable review of PR #74 — MBQ-37 verified only the topic **string**, not the payload/subscription/implementation-scope residual | Building a webhook-driven import path on an unverified payload shape or unconfirmed subscription mechanics risks silent breakage; whether Phase 1 implements it at all changes what implementation planning must design for this trigger | Implementation planning, with official-doc verification | Yes, only for webhook-driven inventory import specifically; No for the layered scheduled/manual/event-driven/reconciliation inventory-sync mechanisms, which do not depend on this row |

## 7. Permissions / security

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-44 | Exact **Odoo security groups, `ir.model.access` rows, access CSVs, and record rules** for the four roles. **Partially resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for planned core access-CSV row shapes only:** which of the four groups get read/write/create/unlink per core model (§10 of that document) — **no actual `ir.model.access.csv` file is created**, and record-rule details beyond Phase 1 store-scoping remain deferred (MBQ-46). Exact group XML IDs are resolved by MBQ-45's residual. | DEC-012 §10; Part A §J; AR-019 | `ir.model.access` is deny-by-default; nothing works without these — but they are code artifacts, gated | Partially resolved (planned CSV row shapes only) — ChatGPT via AR-019/core-naming-schema-planning.md (2026-07-05); actual CSV file creation remains Implementation planning, gated on the implementation gate | Yes for the actual CSV file/record rules (still a code artifact, gated); No for the planned row shapes themselves, which are now resolved at planning level |
| MBQ-45 | **Partially resolved by DEC-013 acceptance (2026-07-03):** the proposed role hierarchy is accepted (Admin ⊃ Operator/Reviewer ⊃ Auditor). **Partially resolved by DEC-018 acceptance (2026-07-04):** the roles→groups mapping and surface-split residual are now also resolved — the four accepted roles map **1:1** to four Odoo security groups in Phase 1 (no finer-grained composition); the connector uses **one shared, role-gated application surface**, not a forked admin-app/functional-app pair. **Residual resolved by ChatGPT via PR #85 / AR-019 / [`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md) (2026-07-05), for exact group XML IDs:** `group_shopify_connector_auditor`, `group_shopify_connector_operator`, `group_shopify_connector_reviewer`, `group_shopify_connector_admin`, and `module_category_shopify_connector` (§10 of that document). The role hierarchy and roles→groups mapping/surface-split themselves are unchanged, already resolved by DEC-013/DEC-018 — this acceptance adds only the missing identifiers. | DEC-012 §10; setup-ux-principles P10; Part A §J.1/§F.5; DEC-013; DEC-018; AR-019 | Fixes group design before CSVs are written | Resolved (hierarchy + mapping/surface split + group XML IDs) — ChatGPT via DEC-013, DEC-018, and AR-019/core-naming-schema-planning.md (2026-07-05); exact `ir.model.access.csv` rows (MBQ-44) remain Implementation planning, gated | Yes for the actual CSV file/record rules (MBQ-44) only; No for the group design and XML IDs themselves, which no longer block |
| MBQ-46 | **Multi-company / multi-store permission isolation** beyond the single-store MVP's record-rule scoping | setup-ux-principles; DEC-003 | Later-phase concern; Phase 1 keys/rules must merely not preclude it | ChatGPT (later phase) | No |
| MBQ-47 | **Resolved by DEC-013 acceptance (2026-07-03):** Reviewer remains approval/manual-review focused — not a general retry/trigger role | Part A §J.2; DEC-013 | Keeps manual-review approval a distinct, auditable act | Resolved — ChatGPT via DEC-013 | No |

## 8. Deployment / operations

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-48 | **Odoo.sh vs on-prem packaging/installation** convenience details | DEC-005/DEC-008 | Install experience; not a design blocker | Implementation planning | No |
| MBQ-49 | **MVP-scale throughput validation** under `--max-cron-threads=2` (realistic catalog/order volumes) | DEC-005 | Proves the internal cron-queue suffices before release; triggers the `queue_job` revisit if not | Implementation planning (testing) | No for code start; **Yes for release readiness** |
| MBQ-50 | **OCA `queue_job` optional-accelerator adoption** — only via DEC-005's revisit triggers | DEC-005; RA-004 | Kept ready-to-adopt-later; not a Phase 1 default | ChatGPT (only if a revisit trigger fires) | No |
| MBQ-51 | Exact **GraphQL cost/throttle-aware pacing parameters** (cost budgeting, backpressure thresholds feeding the health state) | DEC-004; Part A §B.3 | Rate-limit awareness is DEC-003-mandatory; parameters unfixed | Implementation planning | Yes (transport client) |
| MBQ-52 | **Shopify API-version pinning/upgrade policy** (which version pinned per store; upgrade cadence; deprecation watch). **Accepted by ChatGPT via DEC-018 (2026-07-04), policy only:** one stable Shopify GraphQL Admin API version is pinned per connector release; the active pinned version is stored per store/config (Part A §B.3); API-version health/deprecation warnings are surfaced on the existing API-health surface; a planned, periodic (e.g. quarterly) review/upgrade window is committed to — never "latest" tracked live in production. | DEC-004; Part A §B.3; DEC-018 | Version drift silently changes mutation semantics (e.g. `@idempotent` requirements are version-dated) | Resolved (policy) — ChatGPT via DEC-018; exact upgrade-execution mechanics and deprecation-warning copy/thresholds remain Implementation planning | Yes for exact upgrade mechanics only; the pinning/review-cadence policy itself no longer blocks |

## 9. UI/UX design

| ID | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-53 | **Screen-level UI/UX design blueprint** — screen inventory, navigation/information architecture, Odoo-native interaction patterns, screen-level wireframe specs (dashboard, setup wizard, store settings, sync center, error center, matching center, preview/review screens), empty/loading/success/error/manual-review states per screen, UX copy guidelines, error-message style, and a premium UI/UX acceptance checklist. **Partially resolved by DEC-016 at screen-design blueprint level (Master Blueprint Sprint D, accepted by ChatGPT 2026-07-04) — stays OPEN/partial, not fully resolved:** the screen-design blueprint layer is now accepted ([`master-blueprint-ui-ux-screen-design.md`](./master-blueprint-ui-ux-screen-design.md), companion [`DEC-016`](../04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md), Status: Accepted by ChatGPT — at screen-design blueprint level only, not a pixel-level visual-design/final-wireframe-polish approval), but MBQ-53's full closure additionally depends on its still-open sibling rows — **MBQ-03** (exact view/menu/action XML IDs), **MBQ-22** (exact copy/wording), **MBQ-44** (exact security groups/CSVs), **MBQ-45** (admin-vs-functional surface split), **MBQ-06** (readiness essential-vs-nice-to-have split) — which Part D **accommodates but does not decide**; and the still-open screen-relevant recommendations MBQ-33/34/41/35/32 are likewise accommodated, not decided. See the Sprint D / DEC-016 acceptance note above. | DEC-012 (promised a later UI-design pass; "exact copy/wording... a later UI-design pass" — `ux-operator-flow.md` §5, DEC-012 "What remains open"); standing user/ChatGPT rule that premium UI/UX is a product pillar; Master Blueprint Sprint A review | The ten accepted operator flows (DEC-012) fix *behaviour*, not *screens* — premium UI/UX is a named differentiation pillar (`../02-product/product-vision.md`) and is not achieved by behavioural rules alone; without screen-level design, wireframes/specs, Odoo-native interaction rules, and explicit screen states, implementation would have to invent screen design ad hoc, risking an inconsistent or non-premium operator experience | ChatGPT + a later **UI/UX Screen Design Blueprint sprint** (Master Blueprint Part D, see `master-blueprint.md`) | Yes, for implementation of any operator-facing screen/view/UI flow; No for Part B/C domain-blueprint authoring (concept/contract level, not screen design) |

---

## Maintenance rule

Every later blueprint part (B/C/D/E) must: (1) resolve or re-route its
assigned rows, marking resolved rows **Resolved (date, by, where)** rather
than deleting them; (2) add newly discovered questions here with the next
free ID; (3) never let a "Blocks implementation: Yes" row be silently
dropped — per `../05-qa/quality-feedback-loop.md` §11 and `CLAUDE.md` §7.
