# Lite / Full Packaging — Final Proposal (OP-23 / Q6 / Q21 / Q27)

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-10 by the MVP planning-completion session (AR-042
> candidate). Companion decision record:
> [`../04-decisions/DEC-029-lite-full-packaging-proposal.md`](../04-decisions/DEC-029-lite-full-packaging-proposal.md).
> This proposal defines what "Lite" and "Full" mean for this connector,
> technically and commercially, answering Q27's framing question. It is
> grounded in what this repository is actually building (the merged
> addons + the accepted DEC-003 MVP scope), not generic edition
> patterns. **Nothing here authorizes implementation, pricing
> publication, or distribution-channel work.**

## 1. The Q27 framing answer (the core of this proposal)

Q27 asked: is "Lite/Full" a restatement of the existing per-store
domain-enablement-flag mechanism, or a genuinely new concept requiring
separate installable module sets / licensing gates?

**[Proposed decision]** Both mechanisms exist and serve different
jobs — the answer is a **two-layer model**:

- **Editions are installable module sets** (the commercial/packaging
  layer). What a customer bought = which connector modules they
  received/installed. Enforcement is standard Odoo module packaging —
  no license-validation code, no entitlement records, no runtime
  license checks in MVP.
- **The per-store domain flags remain the operational layer** (the
  four merged flags `product_domain_enabled`, `sale_domain_enabled`,
  `inventory_domain_enabled`, `fulfillment_domain_enabled`, enforced
  at job execution time, **plus the fifth flag Task 015 adds via the
  settings seam, `product_export_domain_enabled`** — exports stay
  opt-in even inside Full). They answer "is this domain switched on
  for this store right now," never "did the customer pay."

This keeps the technical foundation undistorted (CHATGPT.md §1's
requirement): no flag ever bypasses a safety guard, no giant module,
and a Full customer can still operationally disable a domain per store.

## 2. Edition contents (grounded in the accepted MVP scope)

### Lite — "reliable visibility": Shopify flows INTO Odoo

Modules: `shopify_connector_core` + `shopify_connector_product` +
`shopify_connector_sale`.

| Capability (DEC-003 ID) | In Lite |
| --- | --- |
| Store connection, credentials, test connection, readiness, lifecycle (C-CONN-01/02/04/05/06) | Yes (merged core) |
| Setup wizard, dashboard, sync/error centers, logs, retry, manual review (C-DASH-*, C-OBS-*, C-JOB-*) | Yes (core UI phases) |
| Product + variant import & matching (C-PROD-01, C-VAR-01 import side) | Yes (merged) |
| Customer import & matching (C-CUST-01/03) | Yes (merged) |
| Order import incl. total-check guard, same-currency rule, financial evidence (C-ORD-01/02/03/04, Domain 9 minimal) | Yes (Task 012) |
| Manual + scheduled sync + reconciliation (C-SYNC-04/05/06) | Yes (Area 6) |
| **Any write to Shopify** | **No — structurally absent** (no module in Lite contains a mutation) |

Lite's honest product claim: "everything that happens in your Shopify
store appears correctly, idempotently, and recoverably in Odoo — with
premium observability." Lite performs **zero** Shopify mutations; its
scope set needs no write scope. This is a real, defensible edition
boundary, not a crippled demo.

### Full — Lite + Odoo operates the store

Modules: Lite + `shopify_connector_inventory` +
`shopify_connector_fulfillment` + `shopify_connector_product_export`.

| Capability | Added by |
| --- | --- |
| Inventory write-back, location mapping, first-push guard (C-INV-01/02/03/04) | inventory (Task 013) |
| Fulfillment/tracking write-back, notification guard (C-FUL-01/03) | fulfillment (Task 014) |
| Controlled product export/update incl. preview/diff + destructive-write guard (C-PROD-02/03/05, C-VAR export side, C-PRICE-01 export) | product_export (Task 015) |

### Optional add-ons (post-MVP, Phase 2/3 — named, not designed)

`shopify_connector_accounting` (invoice/payment automation),
`_refund` (refunds/returns — carries the mandatory idempotent-refund
regression rule), `_payout` (payout reconciliation,
Shopify-Payments-gated), `_multi_store` (multi-store/multi-company
complexity). Each requires its own architecture pass + DEC before it
is anything more than a name (DEC-003 deferrals unchanged). The
taxonomy's Phase-4 premium breadth (B2B, Markets, POS, gift cards,
metafields) remains feature-flagged add-on territory on the same
pattern.

## 3. Why this split (evidence)

1. **It follows the write/read risk boundary.** Every capability that
   can damage a live storefront (stock, fulfillments, catalog writes)
   is Full-only. Lite customers cannot be harmed by a write defect —
   there is no write code installed. This is the strongest safety
   story the architecture can offer and matches the accepted
   read-only-first sequencing (Tasks 010/011 before 012–015).
2. **It matches the module DAG exactly** (architecture doc §2) — the
   edition boundary is enforced by dependencies that already exist for
   engineering reasons; zero packaging-specific code.
3. **It is commercially conventional and Odoo-native**: Odoo Apps
   store sells per-module; a Lite→Full upgrade is "install three more
   modules," data-safe and instant (§5).
4. **Competitive positioning:** the differentiation themes (vision §
   themes 1–3) live in Lite (correctness, observability, onboarding),
   so the entry product already demonstrates the premium bar;
   operational write-back is the paid depth. (Competitor-claim
   context, matrix-cited in the vision docs: market connectors
   generally sell all-in-one with per-feature toggles; a
   read-only-safe entry edition is a differentiator, not a copy.)

## 4. Enforcement, licensing, and distribution interaction

- **MVP enforcement = module possession.** No entitlement records, no
  license keys, no phone-home. LGPL-3 licensing of the code (merged
  manifests) permits this commercial model via distribution control
  (who receives which modules) rather than technical locks. A future
  license-key/entitlement mechanism (e.g. for Odoo Apps store
  auto-delivery) is a **Phase-2 commercial decision** — deliberately
  out of MVP so it cannot distort the foundation.
- **Distribution branches (DEC-023/DEC-026, unchanged):** branch A
  (custom distribution, ≤ the DEC-027 proposed pilot scope) delivers
  modules directly to high-touch customers — editions are a delivery
  choice per contract. The Phase-2+ B-1 public app changes the *auth*
  surface, not this packaging: the Odoo-side modules stay the product;
  Shopify billing (mandatory for App Store distribution — captures §6)
  would charge for the connection service, with edition still
  determined by installed Odoo modules. No packaging decision here
  depends on the B-1 timeline.
- **Odoo Apps packaging (if used):** three Full-only modules + three
  Lite modules publish as separate entries with dependency metadata;
  the release plan carries the packaging checklist.

## 5. Upgrade / downgrade / data-safety rules

- **Lite → Full:** install the three Full modules; no migration, no
  data change; new menus/settings appear via their own modules' views;
  first-push guard + preview/confirmation protect the first writes.
  **Known upgrade boundary (red-team-added):** sale orders imported
  and confirmed while on Lite produced no delivery pickings
  (`sale_stock` arrives with Full) — they do not gain pickings
  retroactively and are therefore not fulfillable through Task 014;
  documented in the release plan's known limitations.
- **Full → Lite (or add-on removal):** the supported path is
  **disable, not uninstall** (MBQ-54/DEC-018): switch the domain flags
  off — all history, bindings, mappings, and logs survive; enqueue of
  new domain jobs is blocked at once (merged enforcement).
  **Uninstall reality (red-team-corrected):** uninstalling a domain
  module that has ever executed a job **fails** on the append-only
  job-log `ondelete='restrict'` FK (the `selection_add` cascade tries
  to unlink the domain's jobs, and their audit logs block it) —
  uninstall works only on databases where the domain never ran.
  Disable-only is therefore the sole supported removal path once a
  domain has run; business data is never at risk on any path
  (architecture doc §8 carries the full mechanics and the future
  soft-degrade option).
- **Permissions/menus:** domain menus/screens are owned by their
  modules (PD-2), so Lite installs simply do not contain Full menus —
  no hidden-but-present surfaces; within an edition, the four merged
  security groups gate actions (roles ≠ editions; a Lite admin is
  still an admin).
- **No safety-guard interaction:** editions and flags gate *whether*
  a domain runs, never *how safely* — no guard (total-check,
  first-push, destructive-write, notification) is edition-dependent.

## 6. Test strategy for edition combinations

- Every module's suite already runs standalone-with-dependencies
  (merged pattern); Lite = core+product+sale suites green with
  inventory/fulfillment/product_export **absent** — this is exactly
  the state the repo is in today, so the Lite combination is
  continuously proven by construction until the Full modules merge.
- Each Full-module task packet (013/014/015) requires an
  install-on-populated-Lite test cycle on Odoo.sh (module installs
  cleanly on top of Lite with existing data), plus a
  **fresh-database uninstall check** (uninstall before any domain job
  has run leaves business data intact) and a documented-failure check
  (uninstall after jobs have run fails on the audit-log FK exactly as
  §5 states — asserting the disable-only posture) — carried as
  acceptance criteria in the packets.
- Release hardening (Area 8) adds the cross-edition matrix: Lite-only
  runtime; Full runtime; Full with individual domains flag-disabled;
  upgrade Lite→Full on a populated database.

## 7. What is MVP vs post-MVP in this proposal

| Item | MVP | Post-MVP |
| --- | --- | --- |
| Two editions as module sets | Yes (falls out of Tasks 012–015) | — |
| Domain flags as operational layer | Yes (merged) | — |
| Entitlement/license-key mechanism | No | Phase 2 commercial decision |
| Billing integration | No (custom apps cannot use the Billing API — captures §6) | Phase 2+ with B-1 |
| Add-on modules (accounting/refund/payout/multi-store) | No | Phase 2/3, own passes |
| Per-feature micro-editions (e.g. inventory-only) | No — two editions only, complexity guard | Revisit on demonstrated demand |

## 8. Registers touched if accepted

OP-23/Q6/Q21/Q27 → Resolved by DEC-029 (register notes); the
implementation-readiness map's "Lite/Full packaging — undefined
concept" row → "Defined by DEC-029; enforcement = module sets; no MVP
implementation work beyond the already-planned Tasks 013/014/015
module boundaries." **No new implementation task is created by this
proposal** — that is its central virtue: packaging falls out of the
architecture already being built.
