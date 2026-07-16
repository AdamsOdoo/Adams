# Screen spec — Settings, permissions & retention

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline; design artifact only — **no
> implementation is authorized**, UI-U1/U2/U3 stay CLOSED. Source:
> `settings-permissions.html` (+ `../assets/prototype.css` + a small
> screen-local `<style>` block for toggle/save-bar/toast helpers, tokens
> only). Copy is illustrative (MBQ-22). Built on the **two-role model**
> (Connector User / Connector Administrator) — itself Proposed.

## Purpose

One store-scoped settings surface where the Connector Administrator governs
capabilities, schedules, order policies, the fulfillment operating mode,
roles/access/PII visibility, and retention — and where a Connector User can
read everything without any pretend-editable control.

## Primary role

**Connector Administrator.** Every write on this surface is
Administrator-only (roles doc §1.2: configuration, scheduling, capability
enablement, order policy, fulfillment mode, access, privacy/retention).
Connector User gets the read-only variant (neutral "view only" band; values
rendered as facts, not disabled controls). Server-side gating is the
security boundary; the UI split is affordance only.

## Tab sections and data

| Tab | Content | Source |
| --- | --- | --- |
| (a) Capabilities & schedules | Per-domain enable toggles (product/customer/order import, inventory, fulfillment, product export opt-in, abandoned checkouts off-by-default) + plain-word schedule rows ("Every 15 minutes", never cron syntax) | [`mvp-capability-map.md`](../../02-product/mvp-capability-map.md) (Lite/Full domains; export opt-in even in Full); DEC-005/025 scheduling posture |
| (b) Order policies | `order_confirmation_policy` radio — paid-only (**Recommended** chip, default) / paid-or-authorized / quotations-only — with one-line consequences; approved manual-gateway table with per-gateway pending rule (COD row shows the three-value select: confirm automatically / create quotation / **require User approval**, default) | [`sales-order-lifecycle-and-confirmation-policy.md`](../../02-product/sales-order-lifecycle-and-confirmation-policy.md) §1.1, §2.2, §7 (PD-A/B/E) [Proposed] |
| (c) Fulfillment mode | Mode 1 (Odoo-controlled) selected card — default + recommended; Mode 2 card with the "exact reconciliation — 16 safety conditions" explainer, Administrator-only Enable, and the consequences drawer (never replays history; scan-gated; unresolved-case list; rollback-safe; audited) | [`fulfillment-operating-modes.md`](../../02-product/fulfillment-operating-modes.md) §1, §4, §6 [Proposed] |
| (d) Roles & access | Two role cards with capability summaries and cannot-do lines; the single-dropdown user-form mock ("Shopify Connector: [User ▾]" — one selection, options empty/User/Administrator); the per-store PII unmasking toggle (default off, Administrator-only, logged) | [`connector-roles-and-permissions.md`](../../02-product/connector-roles-and-permissions.md) §1.1/§1.2/§3/§4.3 [Proposed] |
| (e) Retention & privacy | PII retention period (illustrative 90 days), daily sweep row with last-run result, "Mask a customer now" action (audited, irreversible), and the audit note (who/when/old→new; logs append-only + redacted at write) | Roles doc §3 (PCD minimization posture); DEC-009 audit posture |

## Actions per role

| Action | Connector User | Connector Administrator |
| --- | --- | --- |
| View all five tabs | Yes (read-only facts) | Yes |
| Toggle capabilities / change schedules | No | Yes |
| Change confirmation policy / gateway list / COD rule | No | Yes (future orders only; no retro-confirm) |
| Enable/disable Mode 2 | No | Yes — always via the consequences drawer; audited |
| Assign roles / PII unmasking toggle | No | Yes (toggle default off; every change logged) |
| Retention period / manual mask | No | Yes (mask is audited and irreversible) |
| Save / discard | n/a (no edit state) | Yes via the unsaved-changes bar |

## States rendered

1. Tab (a) Administrator — toggles + schedules.
2. Tab (b) Administrator — policy radio with Recommended chip + gateway
   table with COD approval-select.
3. Tab (c) Administrator — Mode 1 selected / Mode 2 opt-in cards.
4. Tab (c) Mode 2 consequences drawer (dialog mock).
5. Tab (d) Administrator — role cards, user-form dropdown, PII toggle.
6. Tab (e) Administrator — retention & privacy.
7. **Connector User read-only variant** (tab b) — neutral view-only band;
   values as `.sc-kv` facts, deliberately not disabled controls.
8. **Unsaved-changes bar** — sticky bar naming the changed settings; Save
   primary, Discard secondary; "nothing takes effect until you save".
9. **Saved toast** — success toast with effect summary + audit pointer.

## Tokens used

Tabs: `.sc-tabs`/`.sc-tab`. Policy radio reuses the `.sc-candidate`
selected-card pattern (accent inset ring). Recommended chip =
`.sc-status--success`; Administrator-only markers = `.sc-owner` + lock icon.
Toggles/save-bar/toast are screen-local classes (`sp-*`) composed entirely
from shared tokens (`--sc-accent`, `--sc-neutral-bg`, `--sc-border-strong`,
`--sc-success-*`, spacing/radius scale); the save bar and toast are elevated
surfaces consistent with `.sc-dialog`'s single-elevation rule. Consequence
notes = `.sc-consequence` (info family).

## Accessibility

- Toggles carry `role="switch"` + `aria-checked` and a visible On/Off word;
  radios carry `role="radio"` + `aria-checked`; selects are labelled
  listbox mocks — state is never color-only (WCAG 1.4.1).
- The unsaved-changes bar and toast are `role="status"` (polite live
  regions); the Mode 2 drawer is `role="dialog"` `aria-modal="true"` with a
  labelled heading.
- Read-only variant renders facts instead of disabled controls, avoiding
  low-contrast fake-editable affordances.
- Focus-visible, reduced-motion, ≤ 900px compact shell and RTL logical
  properties are inherited from the shared stylesheet.

## Traceability

- Confirmation policies + COD/manual-gateway overlay + settings inventory
  and defaults: sales-order lifecycle doc PD-A, PD-B, PD-E; §8 UX summary
  ("one radio choice with one-line consequences"; curated gateway
  pick-list from gateways actually observed) [Proposed product decision].
- Fulfillment Mode 1 default / Mode 2 16-condition exact checklist, switch
  confirmation content (consequences, unresolved-case list, never-replay,
  scan-gated, rollback, audited): fulfillment-operating-modes doc §1/§4/§6
  [Proposed product decision].
- Two-role split, single privilege dropdown on the user form, PII
  masked-by-default with Administrator-configurable per-store unmasking
  toggle: roles doc §1/§3/§4.3 [Proposed product decision]; PCD Level 2
  minimization [Inference, roles doc §3].
- Capability set and Lite/Full + export-opt-in posture: capability map
  (DEC-029 accepted packaging).
- Plain-language schedules ("Every 15 minutes", not `nextcall`): accepted
  UX copy law (master blueprint §"Speak the user's language").
- No credential content appears on this surface; the word "encrypt" is not
  used (accepted credential posture).
