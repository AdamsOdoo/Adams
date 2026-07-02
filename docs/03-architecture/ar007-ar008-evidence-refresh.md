# AR-007 / AR-008 Evidence Refresh — Odoo Inventory & Delivery Official-Source Check

> Small, targeted official-source check performed during the **AR-007 + AR-008
> Decision Preparation** sprint (2026-07-02), per the sprint's external-research
> rule: repo-local evidence is the default, and a targeted official check is
> allowed **only** where a decision-critical AR-007/AR-008 fact cannot be
> grounded in existing repo docs. This is **not** a broad research pass — no
> competitor/vendor/forum research was performed.

## Why this check was needed

A repo-local extraction pass over
[`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
found **zero coverage** of `stock.quant`, `stock.move`, `stock.picking`,
`stock.location`/warehouse structure, `delivery.carrier`/tracking fields, the
sale-order→delivery flow, or backorder/partial-delivery behaviour — that file
is scoped to generic Odoo framework/platform architecture (ORM, security,
`ir.cron`, external IDs), not the Inventory/Sales business-object models. The
Shopify side is well-grounded in
[`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
and required no refresh. This document records the small Odoo-side check only.
**This file does not modify `shopify-official-api-notes.md` or
`odoo-official-architecture-notes.md`** (both are forbidden files for this
sprint unless creating this refresh were impossible without editing them — it
was not).

## Scope of the check

Official Odoo 19.0 documentation pages (`odoo.com/documentation/19.0/...`)
covering: inventory quantity-report concepts (on hand / free to use /
forecasted), warehouse/location types, and third-party shipping-carrier
tracking. Access date for everything below: **2026-07-02**. Access status:
**Accessible** unless noted.

## Confirmed facts

- **[Official fact]** Odoo 19.0's **Stock report** page defines: "**On
  Hand:** current quantity of products" and "**Free to Use:** on-hand
  quantity that are not reserved for delivery or manufacturing orders, and
  are available to sell or use." It also defines **Incoming** ("items
  expected to arrive at the warehouse... based on quantities in confirmed
  purchase orders") and **Outgoing** ("items expected to leave the warehouse
  or be consumed in manufacturing orders... based on quantities in confirmed
  sales or manufacturing orders").
  Source: `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/stock.html`.
  The same page references a separate **Locations report** giving a
  "break down of on-hand quantity at multiple storage locations."
- **[Official fact]** Odoo 19.0's **Forecasted report** page defines:
  "**On Hand:** current stock physically available in the warehouse,"
  "**Incoming:** quantities expected from confirmed purchase orders or
  manufacturing orders," "**Outgoing:** quantities reserved for sales orders
  or other outgoing operations," and "**Forecasted:** projected stock levels
  based on confirmed and planned operations." It also states users "can
  reserve or unreserve products directly from the forecasted report" and that
  "confirmed SOs decrease the forecasted stock" based on scheduled delivery
  dates.
  Source: `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/forecast.html`.
- **[Official fact]** Odoo 19.0's **Inventory management** (warehouses/
  locations) page enumerates location types: **vendor, virtual, internal,
  customer, inventory loss, production, transit**.
  Source: `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management.html`.
- **[Official fact]** A dedicated **Third-party shipping carriers** page
  exists in the Odoo 19.0 official docs, covering carrier installation,
  applying a carrier to sales/delivery orders, and production-mode carrier
  behaviour.
  Source: `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/setup_configuration/third_party_shipper.html`.
  **[Open question]** the exact field name(s) used for the tracking
  reference/number on a delivery order (`stock.picking`) and how a tracking
  URL is generated were **not** confirmed verbatim from this page (the
  fetched excerpt was truncated before that section) — **must be verified
  before implementation**.
- **[Official fact]** Official Odoo 19.0 documentation confirms delivery
  processing is organised into named workflows — **One-step**, **Two-step**,
  and **Three-step receipt/delivery** — and that on sales-order confirmation
  a delivery order is generated (accessible via the order's "Delivery" smart
  button); the three-step flow explicitly separates **pick → pack → ship**.
  Sources: `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/daily_operations/delivery_three_steps.html`,
  `.../receipts_delivery_two_steps.html`, `.../receipts_delivery_one_step.html`.

## Confirmed pattern, not an official verbatim quote

- **[Inference from search-indexed secondary sources, not a verbatim official
  quote]** A "Create Backorder?" confirmation step exists in Odoo's stock
  transfer validation flow when a picking is validated with less than the
  full demanded quantity, offering "Create Backorder" (splits the remainder
  into a new picking) or "No Backorder" (closes the transfer, remainder not
  tracked further). This pattern is well-attested for **receipts** in
  official Odoo 19.0 documentation structure (three-step/two-step receipt
  pages) and by multiple secondary sources for the general `stock.picking`
  validation wizard, which is shared across receipts and deliveries in the
  `stock` module — but **no official Odoo 19.0 page was found and fetched
  during this check that states the backorder-wizard text verbatim for the
  outgoing/delivery direction specifically**.
  **[Open question] — must be verified before implementation**: the exact
  backorder-wizard behaviour and copy for **delivery orders** (as opposed to
  receipts), and whether/how a resulting backorder picking is linked back to
  the original for fulfilment-write-back purposes.

## Gaps that remain open (must be verified before implementation)

These were **not** resolved by this small check and are carried into the
AR-008 brief as explicit open questions rather than asserted as fact:

1. Exact `stock.quant` ORM field names (e.g. `quantity`, `reserved_quantity`)
   and their precise relationship to the "On Hand" / "Free to Use" /
   "Forecasted" report-level concepts above (the official pages define the
   **reporting concepts**, not the underlying model fields).
2. Exact tracking-reference/tracking-URL field name(s) on `stock.picking` or
   `delivery.carrier`.
3. Exact backorder-wizard model/field names and behaviour for delivery orders
   specifically (`stock.picking` backorder creation), and how a backorder
   picking references its originating picking.
4. Shopify webhook topic strings for inventory-level changes and fulfilment
   events (`inventory_levels/update`, `fulfillments/*`,
   `fulfillment_orders/*`) — not found in
   `../01-research/shopify-official-api-notes.md` (see the AR-007/AR-008
   briefs' own gap notes; Shopify-side, not part of this Odoo-focused check).
5. The literal enumeration of Shopify's 17 `@idempotent`-eligible mutations
   (only the count and category — "inventory/location + `refundCreate`" — are
   documented in the repo today).

## What this refresh does and does not do

- **Does:** grounds the AR-007/AR-008 briefs' Odoo-side inventory-quantity
  and delivery-workflow statements in newly-verified official Odoo 19.0
  documentation, and explicitly marks the remaining gaps as open questions
  rather than asserting them.
- **Does not:** decide any AR-007 or AR-008 architecture question, modify any
  accepted decision record, or authorize implementation. No competitor
  research was redone. No Odoo source code was read this sprint (unlike RB-14
  Part 2, which read `odoo/odoo` 19.0 source directly for `ir.cron`/
  `ir.model.data`) — the model-field-level gaps above are left open rather
  than resolved from source, consistent with the sprint's "small, targeted"
  scope.
