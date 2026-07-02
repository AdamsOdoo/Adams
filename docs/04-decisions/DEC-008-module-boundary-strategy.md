# DEC-008 — Module Boundary Strategy (AR-004)

> **Accepted architecture decision record.** This record resolves
> **AR-004** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md),
> prepared in the AR-004 + AR-006 Decision Preparation sprint (2026-07-02),
> after DEC-004/005/006/007 acceptance. **ChatGPT accepted this record on
> 2026-07-02** (see *Acceptance note* below). Acceptance does **not** by
> itself authorize implementation or change DEC-003/004/005/006/007.

## Acceptance note (2026-07-02)

- **Accepted by ChatGPT** after PR #64 merged into `Shopify-connector`.
- Acceptance followed Fable review: **ACCEPT WITH MINOR CHANGES**.
- Fable's fix-up was applied before merge.
- This accepts DEC-008 as the **AR-004 module-boundary strategy**.
- **This does not authorize implementation.** Implementation remains
  blocked until ChatGPT opens the implementation gate.
- **Preserved caveats (unchanged by acceptance):**
  - DEC-008 does not decide AR-007.
  - DEC-008 does not decide AR-008.
  - DEC-008 does not decide concrete Odoo schema.
  - DEC-008 does not choose between DEC-006's polymorphic binding table and
    per-domain binding table options.
  - Feature-flag / per-store capability configuration remains routed to the
    UX/operator-flow sprint and Master Blueprint / implementation planning.

## Status

**Accepted by ChatGPT.** Not implementation-authorizing.

## Acceptance date

2026-07-02.

## Date

2026-07-02 (originally proposed; accepted the same day after PR #64 merge
and Fable review).

## Scope

**AR-004 only** — Phase 1 **module/addon-family boundaries**, **dependency
direction**, and **where cross-cutting substrate (queue/job/log/binding/
transport/setup/dashboard) lives**. Does **not** design concrete Odoo
model/field/constraint schema (deferred to a domain-model/implementation
sprint), does **not** decide AR-007 (inventory internal design) or AR-008
(fulfilment internal design) beyond naming their module containers, and does
**not** create any Odoo module, manifest, or code. Assumes DEC-004's
custom-app/GraphQL premise, DEC-005's orchestration substrate, DEC-006's
binding model, and DEC-007's Phase 1 guardrails.

## Accepted context

- DEC-003 (MVP scope): names AR-004 ("module boundaries/names; feature-flag
  + config model") as an architecture-dependent item, feeding — not
  deciding — from essential-mapping (C-MAP-03), per-store config
  (C-MULTI-04), and multi-store-safe-structure requirements.
- DEC-004 (distribution/API/auth): custom/private app, GraphQL-first,
  offline token; explicitly defers module boundaries as a separate
  decision.
- DEC-005 (sync orchestration): webhook receiver + HMAC + dedup, internal
  queue/job model, `ir.cron` worker(s), manual sync, scheduled
  reconciliation, per-record isolation, retry counters, dead/final-failed
  state — the substrate this record's `shopify_connector_core` module must
  host.
- DEC-006 (binding/dedup/identity): dedicated, store-scoped connector
  binding model(s) with domain-specific handling where shapes differ —
  explicitly left "where the binding model(s) live in the connector's
  addon layering" open, which this record now proposes.
- DEC-007 (Phase 1 scope clarifications): first-inventory-push guard,
  fulfilment customer-notification default, conservative financial-
  artifact creation with a total-check guard — Phase 1 guardrails this
  record's inventory/fulfilment/sale modules must host.

## Decision proposed

Adopt a **layered, domain-aligned connector addon family** — neither one
giant module nor a per-feature micro-module explosion — with a strict
one-directional dependency DAG and cross-cutting substrate (transport,
queue/job abstraction, binding abstraction, error-class registry, setup
wizard, dashboard) concentrated in a single domain-agnostic
`shopify_connector_core` module. Full rationale, options considered, and
evidence: [`ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md).

## Phase 1 addon family

| Addon | Owns |
| --- | --- |
| `shopify_connector_core` | Store/connection config + credentials; GraphQL transport client + rate-limit-aware pacing; webhook receiver + HMAC + `X-Shopify-Webhook-Id` dedup; queue/job **abstraction** + `ir.cron` worker(s); binding **abstraction / shared contract** (store scope, audit/status fields, uniqueness principles — schema shape not decided here, see note below); error-class registry; setup/readiness wizard; recovery-first log/error-center dashboard |
| `shopify_connector_product` | Product/variant import + controlled export/update; product/variant binding **responsibility** (schema shape open — see note below); image/media + price/compare-at handling (DEC-007); product field mapping |
| `shopify_connector_sale` | Order import; order binding **responsibility**; **customer import/matching + binding responsibility** (Phase 1 — folded in, not split); financial-evidence capture with the DEC-007 total-check guard; order-status sync |
| `shopify_connector_inventory` | Inventory quantity sync (`available`/`on_hand` only — DEC-003; never `committed`); location mapping; inventory binding **responsibility** (`inventory_item_id` + `location_id` identity shape); the first-inventory-push guard (DEC-007) |
| `shopify_connector_fulfillment` | Fulfilment/tracking write-back; fulfilment binding **responsibility**; the customer-notification guard (DEC-007) |

**Customer, dashboard, and payment-evidence are folded into a Phase 1 host
module** (`sale`, `core`, and `sale` respectively) rather than split into
their own addons — each has a documented revisit condition in the brief
(§"Customer, dashboard, and payment-evidence"). None of the three is
blocked from a later clean promotion to its own module.

**Binding schema shape is not decided by this record.** DEC-006 explicitly
left open whether bindings are implemented as one polymorphic binding table
or one table per domain — that fork is unchanged and not contradicted here.
This record places binding *responsibility*, not table *shape*, with each
module: `core` owns the binding **abstraction/shared contract** that every
binding must satisfy (store-scoping principles, audit-field shape,
uniqueness rules); each domain module owns the binding **responsibility**
for its own identity shape (product/variant, order/customer, inventory's
`inventory_item_id`+`location_id`, fulfilment). Table cells above reading
"binding responsibility" describe ownership of that domain's binding
concern, not a committed table. If the Master Blueprint later chooses a
**single polymorphic binding table**, that table likely lives in
`shopify_connector_core`, with domain-specific reference fields/handlers
contributed by each domain module. If it chooses **per-domain binding
tables**, those concrete tables likely live in the owning domain module,
extending core's shared contract. **DEC-008 does not choose between these
two shapes.**

## Later addon family

`shopify_connector_accounting`, `shopify_connector_refund`,
`shopify_connector_payout`, `shopify_connector_multi_store`,
`shopify_connector_markets`, `shopify_connector_metafield`,
`shopify_connector_pos`, `shopify_connector_b2b`,
`shopify_connector_app_store` — each maps to a capability
`../02-product/non-mvp-and-later-phases.md` already places outside MVP,
each with independent-activation value justifying a separate addon. **Exact
later-module boundaries are not finalized** — only the category and its
Phase 1 gate are proposed (see brief §2).

## Dependency rules

Strict one-directional DAG. `core` → `product`; `sale` and `inventory` are
**siblings** depending on `core` + `product`; `fulfillment` depends on
`core` + `sale`, **not** on `inventory`:

```
core
└── product
    ├── sale
    │   └── fulfillment
    └── inventory
```

- `core` depends on no other connector module.
- `product` depends only on `core`.
- `sale` and `inventory` are siblings (both depend on `core` + `product`,
  not on each other) — each independently enableable/disableable.
- `fulfillment` depends on `core` + `sale` and on Odoo's own `stock`/
  `delivery` apps directly. **`fulfillment` does not depend on
  `shopify_connector_inventory`** — the diagram's `fulfillment` branch
  under `sale` is the only place `fulfillment` appears; it is not also a
  child of `inventory`.
- No module depends "upward"; same-tier modules never depend on each other
  directly.
- No proposed module depends on `adams_base` — this record finds no
  justification for such a dependency (`CLAUDE.md` §9).

## Link-module strategy

Reserved for **optional** cross-domain glue that should not force a hard
dependency, following Odoo's own `auto_install` link-module pattern
(`sale_crm`, `estate_account` — cited with URLs in the brief). **Phase 1's
proposed dependency graph does not currently require one** — every
necessary coupling is already expressed via `depends`. A link module
becomes appropriate only if a later capability needs two independently-
optional modules to interoperate (e.g. a possible future glue module
letting `shopify_connector_fulfillment` reuse
`shopify_connector_inventory`'s location mapping) — flagged `[Open
question]`, not decided here.

## Why this is not one giant module

A single `shopify_connector` module would contradict the accepted
product-vision modularity principle and `CLAUDE.md` §9, match the named
anti-pattern A-MOD-1, and fail the accepted per-domain enable/disable
requirement (`../02-product/product-vision.md` principle 6;
`../02-product/feature-taxonomy.md` CC-6/CC-7) — a merchant could not
selectively disable fulfilment write-back without custom code. See the
brief's *Rejected or weakened alternatives* table.

## Why this is not over-fragmented

Cross-cutting substrate (queue/job, binding, transport, error taxonomy,
setup, dashboard) is deliberately concentrated in one `core` module instead
of duplicated per domain, avoiding A-MOD-2 (over-fragmentation) and
preventing inconsistent error-class taxonomies or duplicated binding-audit
logic across domains. Customer, dashboard, and payment-evidence were
evaluated for a standalone Phase 1 module and folded into a host module
specifically because no Phase 1 capability needs them independently
activatable — splitting them now would be fragmentation without
independence value, not real modularity.

## What remains open

- Exact manifest files, model/class names, field lists, and constraint DDL
  (implementation, separately gated).
- **Binding schema shape** — single polymorphic table (likely in `core`) vs
  one table per domain module — left open by DEC-006 and **not decided
  here**; this record places binding *responsibility*, not table shape,
  with each module (see the binding-schema note under *Phase 1 addon
  family* above). DEC-006 is unchanged.
- AR-007 inventory internal design (quantity fields, multi-location
  mechanism, apply-mode).
- AR-008 fulfilment internal design (FulfillmentOrder orchestration,
  multi-package/location).
- Exact later-module names/boundaries (accounting, refund, payout,
  multi-store, markets, metafield, POS, B2B, app-store).
- Whether a link module is ever actually needed for Phase 1 (no current
  case found).
- **The feature-flag / per-store capability-configuration mechanism.**
  DEC-003's AR-004 scope names both "module boundaries/names" and
  "feature-flag + config model"; this record resolves only the former. The
  concrete feature-flag/config mechanism (how a capability group is turned
  on/off per store) is **not decided or accepted by DEC-008** and is
  explicitly routed to the **UX/operator-flow sprint** (operator-facing
  enable/disable experience) and the **Master Blueprint / implementation-
  planning gate** (technical mechanism) before any code is written.
- Odoo.sh/on-prem packaging/installation convenience details.

## Risks and mitigations

1. **Risk:** folding customer/dashboard/payment-evidence into host modules
   now could make a later split harder if done carelessly. **Mitigation:**
   each fold-in is scoped with an explicit revisit condition and DEC-006
   already keeps customer/order identity as separately-shaped bindings, so
   the seam for a future split already exists in the data model, not just
   the module boundary.
2. **Risk:** concentrating queue/job/binding/transport substrate in `core`
   creates a single point of failure/complexity for the whole connector.
   **Mitigation:** this is a deliberate trade-off against duplicating that
   substrate per domain (which DEC-005/006 already require to be
   consistent — one error-class taxonomy, one audit-field shape); `core`
   stays domain-agnostic (no foreign keys to domain-specific tables),
   limiting its own complexity growth.
3. **Risk:** the sibling relationship between `sale` and `inventory` (no
   direct dependency) could tempt future contributors to duplicate binding-
   resolution logic that both need. **Mitigation:** both depend on
   `product`, which is the natural shared owner of product/variant binding
   resolution; neither needs to reimplement it.
4. **Risk:** if a genuine Phase 1 cross-domain glue need is discovered
   late (e.g. fulfilment needing inventory's location mapping), the
   "no link module needed yet" stance in this record would need revision.
   **Mitigation:** the link-module pattern is already named and cited here
   specifically so that addition is a clean, anticipated extension, not an
   architecture surprise.
5. **Risk:** later-module names in this record could be read as final.
   **Mitigation:** explicitly marked not finalized in both this record and
   the brief; any future module in that list still needs its own boundary
   review when scheduled.

## No implementation authorized

**Acceptance of this architecture decision does not by itself authorize
implementation.** This record creates no code, no Odoo module, and no file
outside `docs/03-architecture/**` and `docs/04-decisions/**`. The no-code
gate (`CLAUDE.md` §4–§5) remains in force until ChatGPT separately opens a
dedicated implementation gate per `../05-qa/quality-feedback-loop.md` §10.
