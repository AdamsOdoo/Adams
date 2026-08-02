# Shopify Connector frontend control audit — 2026-08-02

## Scope and standard

This audit covers the complete frontend declared by the six connector addons:
core, sale, product, inventory, fulfillment and product export. It treats a
control as accepted only when all of the following are true:

1. it has one understandable merchant or operator purpose;
2. its visible name describes the result, not merely the gesture;
3. it is reachable only in a role and record state the server accepts;
4. its target field, method, action, record or filtered list exists;
5. zero-result destinations explain why they are empty and what happens next;
6. destructive or consequential operations disclose the consequence first;
7. keyboard focus, accessible naming and disabled states are explicit; and
8. the rendered state never contradicts the data or another status message.

The inventory at this revision is 44 menus, 45 native actions, 70 native Odoo
buttons, 1,275 native field declarations, 41 Owl buttons and 19 custom inputs,
selects or text areas. Repeated inherited field declarations are counted because
each occurrence can carry different visibility, readonly, label or help rules.

## Information architecture

| Home | Purpose | Children |
|---|---|---|
| Overview | Store performance, freshness and connector health | Dashboard only |
| Operations | Work an operator performs | Orders; Products; Inventory; Fulfillment; Sync & Recovery; Needs Attention |
| Reporting | Read and analyse history | Analysis; Activity & Audit Trail |
| Configuration | Establish connections and rules | Connections; Sync Rules; Locations |

Configuration is deliberately nested:

- Connections: Stores, Guided Setup.
- Sync Rules: Store Settings, Export Settings, Fulfillment Settings, Tax Mappings.
- Locations: Location Mapping, Refresh Shopify Locations, Map a Shopify Location.

No first-level destination mixes configuration, reporting and daily operations.
No placeholder or actionless leaf menu is permitted.

## Corrected product contracts

| Area | Defect | Accepted contract |
|---|---|---|
| Dashboard layout | Odoo's action container clipped a long client action | The dashboard owns a full-height vertical scroll container and responsive content width |
| Typography | Undefined and duplicated font tokens invalidated declarations | Dashboard, setup and export diff share one inherited Odoo typography/token layer |
| Status truth | A freshness warning could appear with “All systems normal” | One critical projection reconciles freshness, connection state and job health; success is suppressed while any critical cause is active |
| Review action | A stale warning reused a failed-jobs domain and could open an empty page | Stale data opens the actual store sync controls; incomplete data opens the actual failure-evidence target |
| Zero metrics | Zero-value cards looked clickable but opened empty lists | Zero commercial and lifecycle counts are informative, disabled or non-interactive |
| Completed setup | A completed store resumed on checkpoint 12 with an active Activate button | Completed setup opens a completion state with Overview, Store Settings and intentional re-review actions |
| Setup progress | Twelve equal tabs were dense and difficult to scan | The twelve guarded backend checkpoints remain intact but are presented as Connect, Configure, Protect and Launch |
| Export surface | A private token set made the third custom surface visually inconsistent | Export diff consumes the shared component tokens and the same scroll/layout contract |

## Automated gates

`TestUiControlContract` is the fail-closed regression gate for the complete
installed frontend. It verifies:

- every connector view field exists on its declared model;
- every native button has an accessible name and a real object/action target;
- every Owl input has a label, every radio has a group name and every button
  handler exists in its component;
- every menu is a valid destination or a purposeful branch;
- all sibling menu sequences are unique and the four first-level homes are exact;
- every operational, reporting and configuration destination has the correct
  ancestor; and
- every native list action has purposeful empty-state guidance.

The HOOT suites add dashboard truth-state, non-actionable-zero and completed
setup coverage. Browser tours traverse the new nested navigation and execute
the existing role/state action paths. Existing server tests remain the final
authority for access, state transitions, idempotency and mutation safety.

## Review boundary

This document records implementation evidence. It is not self-acceptance and
does not replace exact-head Odoo installation, HOOT, browser-tour and visual
evidence in a reviewer-controlled runtime.
