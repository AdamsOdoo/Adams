# DEC-029 — Lite/Full Packaging Model (OP-23 / Q6 / Q21 / Q27)

## Status

**Proposed for ChatGPT review. NOT accepted.** Drafted 2026-07-10 by
the MVP planning-completion session (AR-042 candidate). Full rationale,
edition contents, enforcement model, upgrade/downgrade rules, and test
strategy: [`../02-product/lite-full-packaging-final-proposal.md`](../02-product/lite-full-packaging-final-proposal.md).
Companion architecture points PD-1/PD-2 (module boundaries):
[`../03-architecture/final-mvp-module-and-dependency-architecture.md`](../03-architecture/final-mvp-module-and-dependency-architecture.md).
Nothing below is binding until ChatGPT explicitly accepts this record;
no implementation, pricing publication, billing, or distribution work
is authorized by it.

## Proposed decision (Recommendation — becomes binding only on acceptance)

1. **Q27 framing:** Lite/Full is a **two-layer model** — editions are
   **installable module sets** (commercial layer, enforced by standard
   Odoo packaging, zero license code in MVP); the merged per-store
   domain-enablement flags remain the **operational layer** and never
   encode payment status.
2. **Lite** = `shopify_connector_core` + `_product` + `_sale`:
   everything Shopify→Odoo (products, customers, orders, with the full
   reliability/observability substrate); structurally zero Shopify
   mutations.
3. **Full** = Lite + `_inventory` + `_fulfillment` +
   `_product_export`: Odoo operates the store (stock write-back,
   fulfillment/tracking, controlled catalog export).
4. **Add-ons** (Phase 2/3, names only): `_accounting`, `_refund`,
   `_payout`, `_multi_store` — each gated on its own future
   architecture pass; premium breadth (B2B/Markets/POS/gift
   cards/metafields) stays deferred per DEC-003.
5. **Downgrade/removal = disable, not uninstall** (MBQ-54 posture
   applied to editions); uninstall consequences documented, business
   data always survives.
6. **No safety guard is ever edition- or flag-bypassable** (existing
   accepted rule, restated as a packaging invariant).
7. Entitlement/license-key mechanics and any billing integration are
   **explicitly deferred** (Phase 2 commercial decisions; custom apps
   cannot use Shopify's Billing API — 2026-07-10 captures §6).

## Alternatives considered (summary; detail in the proposal §1/§3)

- **Flags-as-editions** (single codebase, everything installed, paid
  flags): rejected as MVP model — requires license-enforcement code
  (distorting the foundation), ships write code to read-only
  customers, weakest security story.
- **Per-capability micro-editions:** rejected — two editions only;
  complexity guard; revisit on demonstrated demand.
- **One edition, one price:** rejected — contradicts the standing
  product requirement (CHATGPT.md §1: "commercially packageable later,
  including Lite and Full editions").

## What becomes binding if accepted

Points 1–7; OP-23/Q6/Q21/Q27 close as Resolved-by-DEC-029;
PD-1 (`shopify_connector_product_export` module) and PD-2 (views in
owning modules) are ratified as the module-boundary consequence;
Task 013/014/015 packets' module boundaries and the release plan's
packaging/uninstall sections become the operative packaging plan.

## What remains unauthorized regardless of acceptance

All implementation (Tasks 012–015, UI, webhooks); any billing,
entitlement, license-key, App Store, or pricing-publication work; any
add-on module design.
