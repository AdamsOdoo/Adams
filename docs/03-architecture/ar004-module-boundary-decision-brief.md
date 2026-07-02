# AR-004 Module Boundary Decision Brief

> **AR-004 + AR-006 Decision Preparation sprint.** This brief prepares a
> **proposed** decision for **AR-004** (module boundaries / addon family
> strategy) in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
> It feeds [`../04-decisions/DEC-008-module-boundary-strategy.md`](../04-decisions/DEC-008-module-boundary-strategy.md)
> (`Status: Proposed for ChatGPT review`). **This brief does not decide
> anything by itself** — AR-004 remains "Not decided" until ChatGPT accepts
> DEC-008. It decides no AR-007 (inventory) or AR-008 (fulfillment) internal
> design, creates no Odoo module, and authorizes no implementation
> (`CLAUDE.md` §4–§5).

## Claim classification used in this document

Per `CLAUDE.md` §8: `[Accepted decision]` (already accepted in DEC-003/004/
005/006/007) · `[Official fact]` (Odoo 19.0 official docs or source, cited
with URL + access date) · `[Competitor claim]` · `[Inference]` (our
reasoning from cited evidence) · `[Recommendation]` (this brief's proposed
direction — not yet a decision) · `[Open question]`.

## Purpose

Prepare a decision-ready, evidence-backed proposal for AR-004 so ChatGPT and
Fable can review whether it is acceptable, given that AR-002 (API/
distribution), AR-003 (sync orchestration), and AR-005 (binding/dedup) are
now **accepted** (`../04-decisions/DEC-004-distribution-api-auth-strategy.md`,
`DEC-005-sync-orchestration-strategy.md`,
`DEC-006-binding-dedup-identity-strategy.md`) and DEC-007 has closed the
Phase 1 scope holes that touch module design (first-inventory-push guard,
fulfilment-notification guard, financial-evidence guard). The
[`architecture-decision-framing.md`](./architecture-decision-framing.md)
map explicitly recommended deciding AR-004 **last**, after the data-flow
decisions it depends on were framed — that condition is now met.

## Inputs used (repo-local; no external fetch needed — see *External research
performed*)

- `[Accepted decision]` DEC-003 (MVP scope) — architecture-dependencies
  table names **AR-004**: "Module boundaries/names; feature-flag + config
  model," depending on essential mappings (C-MAP-03), per-store config model
  (C-MULTI-04), and multi-store-safe structure.
- `[Accepted decision]` DEC-004 (distribution/API/auth) — custom/private app,
  GraphQL-first, offline token; explicitly lists "module boundaries (AR-004)
  ... separate decisions" as blocked by that record.
- `[Accepted decision]` DEC-005 (sync orchestration) — webhook receiver +
  HMAC + dedup, internal queue/job model, `ir.cron` worker(s), manual sync,
  scheduled reconciliation, per-record isolation, retry counters, dead/
  final-failed state; explicitly defers "module boundaries (AR-004) —
  separate decision."
- `[Accepted decision]` DEC-006 (binding/dedup/identity) — dedicated,
  store-scoped connector binding model(s), domain-specific handling where
  shapes differ (product/variant, customer, order, inventory/fulfilment);
  explicitly states "AR-004 module boundaries — where the binding model(s)
  live in the connector's addon layering — not decided here."
- `[Accepted decision]` DEC-007 (Phase 1 scope clarifications) — first
  Odoo→Shopify inventory-push guard, fulfilment customer-notification
  default, conservative financial-artifact creation with a total-check
  guard; all scoped as guardrail statements, not module or schema design.
- `[Accepted decision]` [`phase1-domain-model-brief.md`](./phase1-domain-model-brief.md)
  — eight-domain concept map (store/connection, binding/identity, product,
  customer, order/sale, inventory, fulfilment, queue/log/error) that this
  brief uses as the domain inventory to assign to addons.
- `[Inference — carried, not yet decided]` [`rb14-decision-candidate-brief.md`](./rb14-decision-candidate-brief.md)
  and [`architecture-decision-framing.md`](./architecture-decision-framing.md)
  — record AR-004's dependency on AR-002/003/005 and the A-MOD-1/A-MOD-2
  anti-pattern pair.
- Product context: `[Accepted decision]`
  [`../02-product/product-vision.md`](../02-product/product-vision.md)
  principle 6 ("modular & customizable... a layered addon family isolated
  from `adams_base`... we favour neither one giant module (A-MOD-1) nor
  over-fragmentation (A-MOD-2)"); `[Accepted decision]`
  [`../02-product/feature-taxonomy.md`](../02-product/feature-taxonomy.md)
  cross-cutting groups CC-6 (feature flags) and CC-7 (modularity/extension
  points); `[Accepted decision]`
  [`../02-product/non-mvp-and-later-phases.md`](../02-product/non-mvp-and-later-phases.md)
  (later-phase items and their architecture dependencies).
- `[Official fact]` Odoo 19.0 official documentation and source, cited
  individually below (`../01-research/odoo-official-architecture-notes.md`,
  access date 2026-06-30/2026-07-01).
- `[Competitor claim]`
  [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
  O-MOD-1 and [`../01-research/avoid-list.md`](../01-research/avoid-list.md)
  A-MOD-1 through A-MOD-4 (competitor-derived module anti-patterns —
  evidence, not decisions).

### External research performed

None beyond re-reading already-cited repo docs. Per the sprint's external
research rule, a fresh official-source check is only required when a
decision-critical claim cannot be grounded in existing repo docs. Every
Odoo module-mechanics fact this brief needs (manifest keys, `depends`,
`auto_install`/link modules, `_inherit` vs `_inherits`, access
rights/record rules/`sudo()`) is already Tier-1-cited in
`../01-research/odoo-official-architecture-notes.md` with URL + access
date. No `docs/03-architecture/ar004-ar006-evidence-refresh.md` file was
created.

## Official facts governing module structure (Odoo 19.0)

All `[Official fact]`, accessed 2026-06-30 unless noted, from
`../01-research/odoo-official-architecture-notes.md`:

1. A module is a directory needing at least `__manifest__.py` and
   `__init__.py`.
   (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)
2. The manifest's only required key is `name`; `depends`, `auto_install`
   (bool or list), `application`, `installable`, and `category` are the
   keys most relevant to boundary design.
   (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
3. `depends` lists modules that must load first; installing a module
   installs its dependencies first; `base` is always installed but should
   still be declared.
   (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
4. `auto_install` makes a module install automatically once its
   dependencies are present, and is Odoo's own mechanism for **"link
   modules" that integrate two otherwise-independent modules** — canonical
   example `sale_crm` (depends on `sale` + `crm`, `auto_install`); an empty
   list value always auto-installs.
   (https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
5. Odoo's own tutorial teaches this pattern explicitly: to add an optional
   cross-app feature, create a separate **link module** (`estate_account`)
   that depends on both existing modules and holds only the integration
   logic, so each app stays independently installable and the feature
   activates only when both are present.
   (https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/13_other_module.html)
6. Three model-extension mechanisms exist: classical (new model), extension/
   in-place (`_inherit` without `_name` — *"by far the most used"*), and
   delegation (`_inherits` — official docs warn *"more or less implemented,
   avoid it if you can"*).
   (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html;
   https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/12_inheritance.html)
7. Access Rights (`ir.model.access`, model-level) are additive/union across
   groups; Record Rules (`ir.rule`, row-level) are default-allow, global
   rules intersect (AND), group rules unify (OR).
   (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
8. `[Official source-code fact]` (2026-07-01, RB-14 Part 2) `sudo()`
   "simply bypasses access rights checks" and "could cause data access to
   cross the boundaries of record rules" — already load-bearing for DEC-006
   (per-store isolation must not rely on `sudo()`); the same constraint
   applies to any Phase 1 module's access-control design.
   (`github.com/odoo/odoo/blob/19.0/odoo/orm/models.py`)

`[Inference]` These facts together describe Odoo's own **preferred module
decomposition idiom**: small, independently-installable modules connected
by `depends` (hard coupling, always needed) or `auto_install` link modules
(soft coupling, only needed when both sides are present) — not one giant
module, and not model extension via fragile delegation (`_inherits`).

## Constraints this proposal must respect (restated from the sprint prompt
and accepted decisions)

- No one giant connector module `[Accepted decision — product-vision.md,
  CLAUDE.md §9]`.
- No premature over-fragmentation `[Accepted decision — product-vision.md]`.
- Every domain capability group must be enableable/disableable/removable/
  extendable safely `[Accepted decision — feature-taxonomy.md CC-6/CC-7]`.
- Phase 1 stays small but excellent — install-and-go simplicity is a DEC-003
  non-negotiable `[Accepted decision]`.
- Reliability/logs/retries/dedup/clean setup/UX are first-class, not
  bolted on `[Accepted decision — DEC-003, DEC-005, DEC-006]`.
- No dependency on `adams_base` unless explicitly justified and later
  accepted `[Accepted decision — CLAUDE.md §9]`. **This brief finds no such
  justification** — every proposed module depends only on Odoo core apps
  (`base`, `web`, `mail`, `product`, `sale`, `stock`, `delivery`, `account`
  as needed) and on other connector addons.
- Odoo.sh/on-prem are the target substrate; Odoo Online is excluded
  `[Accepted decision — DEC-005]`. This does not change module boundaries
  (a custom module cannot run on Odoo Online regardless of how it is
  split), but it does mean no boundary decision here needs to accommodate
  an Odoo-Online-only deployment shape.
- Public App Store packaging is not Phase 1 `[Accepted decision — DEC-004]`.

## Options considered

### Option 1 — One giant `shopify_connector` module

Every domain (product, sale, inventory, fulfilment), the transport/queue/
binding/log substrate, and the UI live in a single module.

**Disposition: rejected (proposed).** `[Inference]` Directly contradicts
the accepted product-vision modularity principle and `CLAUDE.md` §9;
matches the named anti-pattern **A-MOD-1** (`[Competitor claim]`
`avoid-list.md`: "poor isolation, hard maintenance, coupling risk").
Structurally, it also fails the accepted per-domain enable/disable
requirement (`../02-product/product-vision.md` principle 6;
`../02-product/feature-taxonomy.md` CC-6/CC-7) — a merchant who wants
product sync but not fulfilment write-back cannot selectively disable a
single monolithic module without custom code. See
*Rejected or weakened alternatives* below for the corresponding
rejected-approaches-log entry.

### Option 2 — Per-feature micro-module explosion

A separate installable module per fine-grained capability (e.g. a module
just for price sync, one just for image sync, one just for tax-line
capture, one per Shopify webhook topic).

**Disposition: rejected (proposed).** `[Inference]` Matches **A-MOD-2**
(over-fragmentation) — `[Competitor claim]` `avoid-list.md`: "dependency-
coupling overhead." `[Inference]` Fine-grained capabilities inside one
domain (e.g. price sync and image sync inside product export) share the
same binding record, the same job/queue substrate, and are typically
enabled/disabled together by a merchant thinking in terms of "product
sync," not "price sync" versus "image sync" — splitting them buys no real
independence and multiplies manifest/dependency bookkeeping for no
operator-visible benefit.

### Option 3 — Domain-per-Odoo-app mirroring

One connector module per **Odoo app** touched (e.g.
`shopify_connector_stock`, `shopify_connector_delivery`,
`shopify_connector_account`) rather than per **business domain**.

**Disposition: weakened, not rejected.** `[Inference]` Odoo's own `depends`
mechanism (fact 3 above) does not require this shape — a module may
`depend` on multiple Odoo apps at once. Mirroring internal Odoo app
boundaries instead of merchant-facing sync domains would scatter a single
concept like "fulfilment" (which spans `stock` + `delivery`) across
multiple connector modules with no natural home for the binding/mapping
logic that belongs to "fulfilment" as a whole. Kept as a **naming/structure
alternative**, not fully rejected, because a future domain split could
still adopt Odoo-app-aligned sub-modules via `auto_install` link modules if
a specific integration only makes sense when a specific Odoo app is present
(see *Link-module strategy* below) — but it is not the primary organizing
axis this brief recommends.

### Option 4 — Layered domain-family with link modules (recommended)

A small number of business-domain-aligned addons (core / product / sale /
inventory / fulfillment for Phase 1), each independently installable,
connected by `depends` along a strict one-directional layering, with
`auto_install` link modules reserved for optional cross-domain glue that
should not be a hard dependency.

**Disposition: recommended (proposed).** See *Recommended proposed
approach* below.

## Recommended proposed approach

### 1. Minimum Phase 1 addon family

| Addon | Owns | Depends on (connector) | Depends on (Odoo core) |
| --- | --- | --- | --- |
| `shopify_connector_core` | Store/connection config + credentials (DEC-004); GraphQL transport client + rate-limit-aware request pacing; webhook receiver controller + HMAC verification + `X-Shopify-Webhook-Id` dedup (DEC-005); the internal queue/job **abstraction** (abstract job model/mixin: source, state, retry count, error class placeholder, related-record reference — `phase1-domain-model-brief.md` Domain 8) and the `ir.cron` worker(s) that drain it; the connector binding **abstraction / shared contract** (store scope, matched-by/at, source strategy, match key, status — DEC-006; schema shape not decided here, see *Binding schema shape* below); the reason-coded error-class registry; the setup/readiness wizard; the recovery-first log/error-center dashboard | — | `base`, `web`, `mail` |
| `shopify_connector_product` | Product/variant import + controlled export/update; product & variant binding **responsibility**, extending core's binding contract (schema shape open — see *Binding schema shape* below); image/media and price/compare-at handling (DEC-007); product field-mapping configuration | `shopify_connector_core` | `product` |
| `shopify_connector_sale` | Order import; order binding **responsibility**; customer import/matching + binding **responsibility** (Phase 1 — see *Customer* below); financial-evidence capture (tax/shipping/discount lines, conservative invoice/payment creation with the DEC-007 total-check guard); order-status sync | `shopify_connector_core`, `shopify_connector_product` | `sale` |
| `shopify_connector_inventory` | Inventory quantity sync (`available`/`on_hand` only, never `committed` — accepted DEC-003 inventory scope; Tier-1 Shopify inventory facts, `../01-research/shopify-official-api-notes.md`); Shopify-location↔Odoo-location mapping; inventory binding **responsibility** (`inventory_item_id` + `location_id` identity shape, per DEC-006); the first-inventory-push guard (DEC-007) | `shopify_connector_core`, `shopify_connector_product` | `stock` |
| `shopify_connector_fulfillment` | Fulfilment/tracking write-back; fulfilment binding **responsibility**; the customer-notification visibility/control guard (DEC-007) | `shopify_connector_core`, `shopify_connector_sale` | `stock`, `delivery` |

**Binding schema shape is not decided by this brief.** DEC-006 explicitly
left open whether bindings are implemented as one polymorphic binding table
or one table per domain — that fork is unchanged and not contradicted here.
This proposal places binding *responsibility*, not table *shape*, with each
module: `core` owns the shared binding contract (store-scoping principles,
audit-field shape, uniqueness rules) every binding must satisfy; each
domain module owns the binding *responsibility* for its own identity shape.
If the Master Blueprint later chooses a **single polymorphic binding
table**, it likely lives in `shopify_connector_core` with domain-specific
reference fields/handlers contributed by each domain module; if it chooses
**per-domain binding tables**, those concrete tables likely live in the
owning domain module, extending core's shared contract. **This brief does
not choose between the two shapes.**

`[Recommendation]` **Customer, dashboard, and payment-evidence — evaluated,
not split out in Phase 1:**

- **`shopify_connector_customer`?** `[Recommendation]` Fold into
  `shopify_connector_sale` for Phase 1. `[Accepted decision]` DEC-003
  includes "customer import and matching (deduplicated; email primary,
  multi-key allowed)" as accepted Phase 1 MVP scope, alongside order import.
  `[Inference]` No Phase 1 capability in the corpus uses customer sync
  independently of order import —
  [`architecture-decision-framing.md`](./architecture-decision-framing.md)
  groups them the same way ("Import for orders, customers... and order
  status/lifecycle"), and this brief infers from that co-occurrence, not
  from a DEC-003 instruction to co-locate the two modules, that folding
  customer into `sale` for Phase 1 is the module-boundary choice. Splitting
  it now would add a manifest dependency for no independent activation
  value (A-MOD-2 risk). DEC-006 already treats customer identity as a
  separately-shaped binding (its own match-key set: email primary,
  multi-key allowed), so a future split to a standalone module — if
  customer-only use cases emerge (e.g. customer export as its own
  capability, marketing/segment sync) — is a clean promotion, not a
  redesign. **Revisit condition:** a demonstrated Phase 2+ need for
  customer sync independent of order import.
- **`shopify_connector_dashboard`?** `[Recommendation]` Fold into
  `shopify_connector_core` for Phase 1. `[Inference]` The job/log/error
  model this brief places in core (`phase1-domain-model-brief.md` Domain 8)
  is a DEC-003 non-negotiable ("recovery-first error center") and is
  meaningless without a place to view it — every install of core needs the
  dashboard, and no plausible Phase 1 deployment installs the job/queue
  substrate without wanting to see its state. Forcing a split here would be
  a mandatory-pair dependency dressed up as modularity (A-MOD-2), not real
  independence. **Revisit condition:** a demonstrated need for a
  headless/API-only deployment mode that must not carry dashboard views.
- **`shopify_connector_payment_evidence`?** `[Recommendation]` Fold into
  `shopify_connector_sale` for Phase 1. `[Inference]` DEC-003 Domain 9 is
  "minimal financial evidence only, no accounting automation" — tax/
  shipping/discount-line capture travels with the order-import job
  (`phase1-domain-model-brief.md` Domain 5) and does not need `account`-app
  depth beyond what `sale` already implies. Splitting it now would separate
  evidence capture from the order it describes for no Phase 1 benefit.
  **Revisit condition:** the later `shopify_connector_accounting` module
  (full accounting automation) is accepted — at that point payment-evidence
  logic is a natural extraction point from `sale` into `accounting`, since
  the later module's larger `account`-app surface and edition-sensitivity
  argue for keeping it out of the lean `sale` module once it exists.

### 2. Later addon family

`[Recommendation, evaluated not blindly accepted]` The sprint prompt's
candidate later-module list is **directionally sound** — every item maps to
a capability DEC-003/`non-mvp-and-later-phases.md` already places outside
MVP, and each carries real independent-activation value (a merchant may
want payouts without B2B, or Markets without POS) that justifies a separate
addon rather than folding into a Phase 1 module:

- `shopify_connector_accounting` — full invoice/payment/gateway accounting
  automation (deferred; `non-mvp-and-later-phases.md`: "must be idempotent
  (C-JOB-04) before inclusion").
- `shopify_connector_refund` — refund sync/cancellation reflection
  (deferred; "idempotent-refund / no-double-refund is a mandatory
  acceptance principle for the first refund/refund-sync sprint").
- `shopify_connector_payout` — payout import + bank reconciliation
  (`[Official fact]` Shopify-Payments-gated; optional add-on).
- `shopify_connector_multi_store` — multi-store/multi-company logic
  (`non-mvp-and-later-phases.md`: "needs AR-005 per-store binding keys
  proven at MVP; AR-004 boundaries; demonstrated record-rule isolation" —
  this brief's per-store-scoped binding abstraction in core is exactly the
  proof point that gates this later module).
- `shopify_connector_markets`, `shopify_connector_metafield`,
  `shopify_connector_pos`, `shopify_connector_b2b` — optional premium
  add-ons; `non-mvp-and-later-phases.md`: "before including: core shipped;
  feature-flag mechanism (AR-004) resolved; demonstrated demand."
- `shopify_connector_app_store` — public App Store compliance surface
  (3 mandatory compliance webhooks, Billing API, Built-for-Shopify
  performance thresholds — deferred by DEC-004).

`[Recommendation]` Plus, promotable-from-Phase-1-host modules with their
own revisit conditions (see above): a possible future
`shopify_connector_customer` and a possible future headless-mode split of
the dashboard out of `shopify_connector_core`.

`[Open question]` **Exact later-module names and manifest boundaries are
explicitly not finalized here** — only the category and its Phase 1
host/gate are proposed. Finalizing them is out of this sprint's scope and
would itself need architecture review when each capability is actually
scheduled.

### 3. Dependency direction

Strict one-directional DAG, enforced as a design rule (not a runtime
check). `core` → `product`; `sale` and `inventory` are **siblings**
depending on `core` + `product`; `fulfillment` depends on `core` + `sale`,
**not** on `inventory`:

```
core
└── product
    ├── sale
    │   └── fulfillment
    └── inventory
```

**`fulfillment` does not depend on `shopify_connector_inventory`** — it
appears only once in the diagram, under `sale`, not also under `inventory`.

- `core` depends on no other connector module — it is domain-agnostic.
- `product` depends only on `core`.
- `sale` and `inventory` are **siblings** — both depend on `core` +
  `product`, but **not on each other**. `[Inference]` Sale needs bound
  products to create order lines; inventory needs bound
  products/variants to key quantity writes; neither needs the other's
  Shopify-direction data (order import doesn't need current stock levels;
  inventory sync doesn't need order history). Keeping them siblings lets a
  merchant install inventory sync without sale sync (or vice versa) and
  satisfies the accepted per-domain enable/disable requirement
  (`../02-product/product-vision.md` principle 6;
  `../02-product/feature-taxonomy.md` CC-6/CC-7) per domain.
- `fulfillment` depends on `core` + `sale` (a fulfilment write-back is
  anchored to an order/fulfilment-order context) plus Odoo's own `stock`/
  `delivery` apps directly — **not** on `shopify_connector_inventory`.
  `[Inference]` This keeps fulfilment installable independently of the
  connector's own inventory-sync module (a merchant might want fulfilment
  tracking write-back without Shopify-direction quantity sync, or vice
  versa) and avoids a same-tier dependency that would otherwise couple two
  Phase 1 modules that do not need each other's Shopify-facing data.
- **No module ever depends "upward"** (e.g. `core` must never depend on
  `product`, `product` must never depend on `sale`). This is the
  circular-dependency-avoidance rule (see item 10 below).

### 4–9. Where things live (answering the sprint's numbered questions)

4. **Core vs domain split** — see table above. `[Recommendation]` core owns
   *domain-agnostic infrastructure* (transport, queue/job abstraction,
   binding abstraction, error-class registry, setup wizard, dashboard);
   each domain module owns its *concrete* binding tables, field mappings,
   and domain-specific job types, extending core's abstractions via
   in-place `_inherit`/subclassing (fact 6 above), never `_inherits`
   delegation.
5. **Link-module strategy** — `[Recommendation]` reserved for **optional**
   cross-domain glue that should not force a hard dependency. Phase 1's
   proposed dependency graph (item 3) does not currently require one — the
   layering already expresses every *necessary* coupling via `depends`. A
   link module becomes appropriate if a later capability only makes sense
   when **two independently-optional** modules are **both** present (e.g. a
   future glue module that lets `shopify_connector_fulfillment` reuse
   `shopify_connector_inventory`'s location-mapping table instead of asking
   for it again, if that turns out to be desirable — `[Open question]`,
   not decided here) — following the same pattern Odoo's own docs
   demonstrate with `estate_account`/`sale_crm` (fact 4–5 above): the link
   module depends on both sides and holds only the integration logic, so
   each side stays independently installable.
6. **Queue/job/log/binding abstractions** — `[Recommendation]` live in
   `shopify_connector_core` as domain-agnostic abstract models/mixins;
   concrete job types, and binding *responsibility*, live in the domain
   module that owns that concern (product binding in `product`, order/
   customer binding in `sale`, inventory binding — needing
   `inventory_item_id`+`location_id` per DEC-006 — in `inventory`,
   fulfilment binding — shape open, AR-008 — in `fulfillment`). **Whether
   each domain's binding is a concrete table in that module or a
   domain-specific slice of a single polymorphic table in `core` is the
   DEC-006 schema-shape fork this brief does not decide** (see *Binding
   schema shape* under §1). `[Inference]` Either way, this keeps DEC-006's
   "domain-specific handling where shapes differ" without duplicating the
   shared audit/status/store-scoping fields DEC-006 requires on every
   binding — those live once, in core's shared contract.
7. **Setup wizard / readiness / dashboard** — `[Recommendation]` core (see
   *Customer, dashboard, and payment-evidence* above).
8. **Shopify API client / GraphQL transport** — `[Recommendation]` core.
   `[Inference]` A single shared, authenticated, rate-limit-aware GraphQL
   client avoids duplicated auth/throttling/retry-pacing code across domain
   modules and centralizes DEC-004's GraphQL-first decision in one place
   that every domain module calls into, rather than each domain
   reimplementing request pacing.
9. **Mapping configuration** — `[Recommendation]` a lightweight, generic
   mapping-configuration **scaffold** (settings-UI pattern, no
   domain-specific fields) lives in core for a consistent operator
   experience (CC-7); **concrete field mappings are domain-specific** and
   live in the module that owns that field (product mapping in `product`,
   financial/order mapping in `sale`). `[Inference]` This mirrors item 6's
   split — shared shape in core, shared *by* every domain but *defined* by
   the domain that understands the fields.

### 10. Avoiding circular dependencies

`[Recommendation]` Enforce the strict DAG in item 3 as a hard design rule:
a module may only `depend` on modules at or below its own layer; same-tier
modules never depend on each other directly (use a link module instead, if
and when genuinely needed); core's abstract models stay domain-agnostic
(no foreign keys to domain-specific tables), so core never needs to import
domain code, which is what would create a cycle. `[Inference]` This is the
same discipline Odoo's own `auto_install` link-module pattern (fact 4–5) is
designed to preserve: two apps stay mutually independent, and only the
link module (which depends on both) knows about the pair.

### 11. Keeping AR-007/AR-008 open while proposing boundaries here

`[Recommendation]` This brief proposes only the **module boundary**
(that inventory and fulfilment are separate installable addons, their
`depends` shape, and where their binding/mapping scaffolding lives) — it
explicitly does **not** decide AR-007 (quantity-field defaults,
multi-location mechanism, apply-mode/auto-apply-vs-review) or AR-008
(FulfillmentOrder orchestration, multi-package/location design). `[Inference]`
This mirrors how DEC-006 separated "binding source of truth" (decided) from
"exact schema" (deferred) — a container-level decision does not foreclose
the internal design decided later. Nothing in this proposal requires
`shopify_connector_inventory` or `shopify_connector_fulfillment` to have any
particular field, quantity source, or write-mode; those remain fully open
for a dedicated AR-007/AR-008 sprint.

### 12. Keeping a future App Store path open without making it Phase 1

`[Recommendation]` Two cheap, non-blocking choices: (a) keep manifest
metadata (`name`, `author`, `website`, `license`, `category`) clean and
listing-ready from day one — free, and does not pull in any App-Store
obligation; (b) design core's webhook receiver as a generic, topic-dispatch
controller so that adding the 3 App-Store-mandatory compliance webhooks
later (`customers/data_request`, `customers/redact`, `shop/redact` — per
DEC-004's already-cited Shopify compliance-webhook requirement) is an
**additive** change to core (new topic handlers) rather than a
restructuring. Building the Billing API integration, the compliance
webhooks themselves, or Built-for-Shopify performance work is explicitly
**not** proposed for Phase 1 (`shopify_connector_app_store` stays a later
module, per DEC-004).

## Rejected or weakened alternatives

| Alternative | Disposition | Why |
| --- | --- | --- |
| **One giant `shopify_connector` module** (Option 1) | Rejected (proposed) | Contradicts the accepted product-vision modularity principle and `CLAUDE.md` §9; matches A-MOD-1; fails the accepted per-domain enable/disable requirement (`../02-product/product-vision.md` principle 6; `../02-product/feature-taxonomy.md` CC-6/CC-7) |
| **Per-feature micro-module explosion** (Option 2) | Rejected (proposed) | Matches A-MOD-2 (over-fragmentation); no operator-visible independent-activation value inside one domain |
| **Queue/job/log/binding abstractions duplicated per domain module** (each domain reimplements its own job/log base classes instead of sharing core's) | Rejected (proposed) | Duplicated code; inconsistent error-class taxonomy across domains; breaks the single recovery-first error-center UX (DEC-003 non-negotiable); harder to maintain a consistent audit-field shape across bindings (DEC-006) |
| **Domain-per-Odoo-app mirroring** (Option 3) | Weakened, not rejected | Not required by Odoo's own `depends` mechanism; scatters merchant-facing domains like "fulfilment" across app-aligned modules with no natural home for its binding/mapping logic; kept as a possible future link-module axis, not the primary organizing principle |
| **`shopify_connector_customer` as a mandatory separate Phase 1 module** | Weakened/deferred, not rejected | No Phase 1 capability needs customer sync independent of order import; legitimate later split once demonstrated, not a design flaw |
| **`shopify_connector_dashboard` as a mandatory separate Phase 1 module** | Weakened/deferred, not rejected | Mandatory-pair dependency with core's job/log model; fake modularity under A-MOD-2 reasoning for Phase 1 |
| **`shopify_connector_payment_evidence` as a mandatory separate Phase 1 module** | Weakened/deferred, not rejected | Financial-evidence capture travels with order import; clean extraction point once `shopify_connector_accounting` exists, not before |
| **Dependency on `adams_base`** | Not proposed; no justification found | `CLAUDE.md` §9 requires explicit justification before this is even considered; this brief finds none — every proposed module depends only on Odoo core apps and other connector addons |

## What remains open

- **Exact manifest files, model/class names, field lists, and constraint
  DDL** — none of this brief's proposal creates any code, Odoo module, or
  manifest; that is implementation, gated separately (`CLAUDE.md` §5, §9).
- **AR-007 inventory internal design** (quantity fields, multi-location
  mechanism, apply-mode) — untouched, stays a dedicated future sprint.
- **AR-008 fulfilment internal design** (FulfillmentOrder orchestration,
  multi-package/location) — untouched, stays a dedicated future sprint.
- **Exact later-module names/boundaries** (accounting, refund, payout,
  multi-store, markets, metafield, POS, B2B, app-store) — category and
  Phase 1 gate proposed; exact boundaries deferred to when each is
  scheduled.
- **Whether a link module is ever actually needed for Phase 1** — this
  brief finds no current Phase 1 case requiring one; flagged `[Open
  question]` for the domain-model/Master Blueprint sprint if a genuine
  optional-pair need emerges (e.g. fulfilment reusing inventory's location
  mapping).
- **The feature-flag / per-store capability-configuration mechanism** (how
  a capability group is enabled/disabled per store). DEC-003's AR-004 scope
  names both "module boundaries/names" and "feature-flag + config model" —
  this brief resolves only the former. The concrete mechanism is **not
  decided or proposed-accepted by this brief**; `setup-ux-principles.md`
  already flags the feature-flag model as "not decided (AR-004)," and this
  brief's boundary proposal is a necessary input to, not a resolution of,
  that mechanism. Explicitly routed to the **UX/operator-flow sprint**
  (operator-facing enable/disable experience) and the **Master Blueprint /
  implementation-planning gate** (technical mechanism) before any code is
  written.
- **Odoo.sh/on-prem installation packaging details** (e.g. whether all
  Phase 1 modules ship in one repository/app bundle for install
  convenience versus separate listings) — an implementation/deployment
  concern, not a module-boundary decision, out of scope here.

## No implementation authorized

This brief proposes an architecture direction only. It creates no Odoo
module, no Python/XML/CSV/manifest file, and no code. The no-code gate
(`CLAUDE.md` §4–§5) remains in force until ChatGPT accepts
[`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md) **and**
separately opens a dedicated implementation gate per
`../05-qa/quality-feedback-loop.md` §10.
