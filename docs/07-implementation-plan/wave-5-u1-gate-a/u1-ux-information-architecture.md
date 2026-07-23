# Wave 5 U1 — UX & Information Architecture

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23. Grounded in the accepted U0 design
> language + the (Proposed) gap-closure prototypes under `docs/09-ui-prototype/**`
> and the exact Wave 4 backend (`u1-backend-ui-contract-inventory.md`). **Reuses
> U0's design system and Odoo-19 idioms — introduces no new design system.**

## 1. Design-language reuse (mandatory)

U1 **must** consume, verbatim, the U0-shipped assets and idioms (source: merged
`shopify_connector_core`, `docs/02-product/ui-u0-copy-deck.md`,
`docs/09-ui-prototype/assets/prototype.css`):

- **Token layer** `static/src/scss/shopify_connector_tokens.scss` — surfaces
  `#F8FAFC/#FFFFFF`, text `#1F2937/#475467`, focus `#175CD3`, semantic
  text-on-tint pairs (success/warning/danger/info/neutral), 4–64 spacing, radius
  8px, platform font stack, light-mode only. **No new colors/fonts/libraries.**
- **Copy principles** — verbs first; no exclamation marks in errors; **never claim
  encryption**; **never render raw internal tokens** as primary copy; **no raw
  evidence** (JSON intent/fingerprints/keys) on any surface; consequence-first
  confirmations; owner-first exceptions; manual review = *a decision, not a
  failure* (distinguished by icon + owner chip + copy, never colour alone);
  friendly directive empty states; **RTL-ready via CSS logical properties**.
- **One rendering, reused** — the plain-language state map (`succeeded`→Done,
  `retry_waiting`→Waiting to retry, `failed_retryable`→Needs a fix,
  `blocked_manual_review`→Waiting on a decision, uncertain→Waiting on a decision).
  U1 reuses it; it does not re-map.
- **Odoo-19 view idioms proven at U0 runtime** — statusbar widget; `groups=` on
  buttons targeting sanctioned methods; `invisible=`/`readonly=` **expression**
  syntax (no legacy `attrs`); `create/edit/delete="false"` locked lists;
  `decoration-*` by state; **plain `<group>` group-by** (not `<group expand>`);
  `id` (not `active_id`) in stat-button contexts; `web_ribbon`; wizards as
  `TransientModel` + `target="new"`; the **server-side boundary guard before any
  side effect** (`_ensure_connector_admin_boundary` pattern) — a hidden button is
  never the security control.

## 2. Navigation & menus (extend U0's single shared surface)

Per DEC-016(A) (*single shared, role-gated surface; domain modules contribute,
never fork*), U1 **contributes** fulfillment entries; it does **not** build a
parallel app. U0's root is `shopify_connector_core.menu_shopify_connector_root`
(gated to Auditor so the whole tree hides for non-connector users), with children
Dashboard / Stores / Sync Center / Error & Review Center (→ Mutation Evidence) /
Logs.

**Two-role visibility (SEC-2, binding SEC-2-first — D-P0-2).** U1's customer-facing
menu/button **visibility** gates on the two SEC-2 roles: fulfillment review/lineage
menus are visible to **Connector User** (which resolves to auditor∪operator∪reviewer,
so the tree still hides for non-connector users), and mode-change controls are
visible only to **Connector Administrator** (the existing
`group_shopify_connector_admin`). The four internal capability groups remain the
**server-side** authorization primitives those roles resolve to. SEC-2 defines the
final `group_shopify_connector_user` XML ID; U1 must **not** treat it as existing
before SEC-2 merges runtime-green.

**U1 adds a `Fulfillment` first-level branch** (contributed by
`shopify_connector_fulfillment`, parented to the core root):

| New menu (in fulfillment addon) | Action | Screen |
|---|---|---|
| `Fulfillment` (branch under core root) | — | parent |
| ↳ `Fulfillment Review` | act_window on `inbound.evidence` | Review workspace (§4) |
| ↳ `Fulfillments` | act_window on `fulfillment.binding` | Binding/lineage list (§5) |
| ↳ `Fulfillment Jobs` | act_window on `job` filtered to the 10 fulfillment job types | Lineage/jobs (§6) |

Mode display + mode-change live on the **Store form** (Stores screen), not a
separate menu (§3). Reconciliation/tracking status surface as **badges/columns**
inside the review + binding views, not new heavyweight screens (consistent with
`screen-inventory-and-navigation-map.md`: fulfillment has no dedicated heavyweight
screen; it renders through shared surfaces + a store sub-surface).

## 3. Store form additions — mode display + mode change

Extend the core store (or store-settings) form with a **Fulfillment mode** group
(admin-gated to match the model field-level `groups=` — Administrator here is the
customer-facing **Connector Administrator**, i.e. the existing
`group_shopify_connector_admin`; the review-workspace affordances in §4 are visible
to **Connector User**, server-enforced by the operator/reviewer groups):

- **Mode chip / statusbar** showing `fulfillment_operating_mode`
  (Mode 1 — Odoo-Controlled · *default* / Mode 2 — Bidirectional Exact
  Reconciliation), plus `fulfillment_switch_in_progress` ("Switching…"),
  `fulfillment_last_mode_switch_at`/`_uid` (history scalars), and the
  `fulfillment_notification_confirmed` gate.
- **Change-mode buttons** (Administrator only, `groups=…admin`) opening the
  **mode-switch confirmation wizard** (§7); buttons call the wizard, which calls
  `action_start_mode2_switch` / `action_rollback_to_mode1`.
- **Mode-2 readiness surfacing** — show the three fulfillment readiness checks
  (`fulfillment_write_scope`, `fulfillment_api_version`,
  `fulfillment_staff_permission`=NOT_PROVEN / CV-013). Never present live mutation
  as proven.

## 4. Fulfillment review workspace (the U1 centerpiece)

Realized by the prototypes as the **External fulfillment review center**
(`docs/09-ui-prototype/external-fulfillment-review/`). Backed by
`shopify.connector.fulfillment.inbound.evidence`.

- **Queue (list/search)** — columns: Case (evidence) · Shopify order
  (`shopify_order_gid` / `order_binding_id`) · **Origin chip**
  (`origin_class`: connector / external_merchant / external_app /
  external_unknown) · items summary · observed age (`last_observed_at`) ·
  **State** (`reconciled_state`: Observed / Review Case Open / Acknowledged /
  Applied / Superseded). Default search facet = review cases open. Danger band:
  "N external fulfillments are waiting on a decision — a decision queue, not a
  system failure."
- **Case detail (form)** — two columns, **evidence left / decision right**:
  - Evidence: Fulfillment GID, FO GIDs (`shopify_fulfillment_order_gids`),
    order↔sale binding, `fulfillment_status_*`/`display_status_*` badges (Layer-A
    families §8), `review_reason` badge, `review_detail` (sanitized), tracking
    (parsed from `tracking_snapshot`), `line_ids` comparison table (Shopify vs
    Odoo remaining), location-mapping check.
  - Decision (role-gated buttons → §6 sanctioned actions):
    **Import tracking** (`action_import_tracking`, Operator+),
    **Acknowledge — handled outside Odoo** (`action_acknowledge_external`,
    Operator+), **Validate proposed** (`action_validate_proposed`, Reviewer+),
    and, on the binding, **Release blocked mutation**
    (`action_release_fulfillment_review`, Reviewer+). No auto-apply on any failed
    condition; unknown origin never treated as connector-created; no stock
    reversal from the UI.
- **The one-engine truth** — the Mode-1 proposal a user confirms is exactly the
  Mode-2 16-condition evaluation output; a failed condition lands here with the
  named `review_reason` and **zero stock change**. U1 renders this; it does not
  compute it.

## 5. Fulfillment/tracking lineage & status

- **Binding list/form** (`fulfillment.binding`): picking ⇄ Fulfillment GID,
  `order_binding_id`, tracking snapshots (parsed), `shopify_status_*`,
  `shopify_last_synced_at`, `notify_customer_sent`. Smart buttons route to the
  related **picking**, **order binding**, and **jobs** via native filtered
  actions (`id` not `active_id`).
- **Job lineage** (`job` filtered to fulfillment job types): source trigger
  (`trigger_origin`), job family (`job_type`), state (10 states), mutation domain
  (`mutation_attempt_id.mutation_domain`), operation scope (present/absent),
  remote refs (`shopify_target_gid`), `superseded_by_job_id`, and the job log
  (append-only, redacted).
- **Mutation-attempt safe summary** — show `observed_outcome`,
  `resolution_disposition`/`_source`/`_reason`, `inconclusive_reconciliation_count`,
  timestamps. **Never** the intent/fingerprint/idempotency-key fields (§9 of the
  contract). Reuse U0's Mutation Evidence list (read-only for all roles; the only
  change path is the admin `action_resolve_mutation_attempt` wizard).
- **Tracking timeline** (optional, from the prototype) — a read-only carrier
  milestone view; **a milestone never validates Odoo stock nor changes the
  reconciliation state**. In U1 this can be a form section over
  `state_snapshot`/`tracking_snapshot`, not a new Owl surface (PD-7).

## 6. Mode-switch confirmation flow (display-and-delegate consequences pattern)

A `TransientModel` wizard (**display-and-delegate only** — see the frozen boundary
in `u1-modular-architecture-recommendation.md` §3.1 and acceptance A6/A21) opened by
the admin mode buttons, mirroring the prototype's **Mode 2 consequences drawer**
(`docs/09-ui-prototype/settings-permissions/` `role="dialog"`, `aria-modal`):

- Heading names the store; body states, as **static informational** wording: the
  16-condition gate; **first failure → review case**; **history never replayed**
  (applies only to fulfillments observed after the switch); **read-only
  reconciliation scan runs first, automation only after clean completion**;
  **rollback-safe** (evidence/bindings/audit untouched); **audited who/when/from→to**.
- It MAY also show a **bounded, ACL-safe, non-authoritative informational count** of
  open external-fulfillment review cases (a bounded `search_count` of
  `inbound.evidence` where `reconciled_state='review'`), explicitly **labelled
  non-authoritative** and captioned that **the server reconciliation scan is
  authoritative**. This count never decides whether switching is legal, never
  classifies blockers, never determines "review required", never chooses the target
  mode, and never alters the server-action arguments.
- Footer: Cancel (secondary) / Enable Mode 2 (primary). On confirm the wizard
  simply **calls** `action_start_mode2_switch`; the rollback path calls
  `action_rollback_to_mode1`. The server action records/enqueues the switch, and the
  server-side reconciliation scan determines blockers and activates Mode 2 or aborts
  to Mode 1 with audit evidence — the wizard predicts nothing.
- **Progress/final status** — after start, show `fulfillment_switch_in_progress`
  ("Reconciliation scan running…"), then the mode-switch-scan job + log, resolving
  to Mode 2 (clean) or back to Mode 1 (blockers/abort). This is **not** UI-owned
  business logic — the wizard computes no mode decision, classifies no blocker, and
  performs no mutation. When an authoritative *dynamic* preflight is later desired,
  it is a **separate backend read-model task (D-P2-5)**, never wizard logic.

## 7. Failure & manual-review UX (operator language)

- **Plain-language reason first**, technical detail behind one disclosure
  ("View technical detail"); the specific `review_reason` / `error_class` /
  `manual_review_subreason` shown, never a generic "needs review". **No raw
  traceback, no raw payload, no token/credential material.**
- **Manual review ≠ failure** — danger family + hand icon + owner chip + decision
  copy; distinguished from technical failure by icon/owner/copy, not colour.
- **Verification-before-retry** — uncertain outcomes read "Verifying remote
  result… checking Shopify before any retry, never a blind resend"; retry offered
  only on server-eligible rows.
- **Delivered-inconsistency** — surface the `delivered_inconsistency` flag as a
  high-visibility case: "Delivered per carrier — Odoo delivery not validated";
  never auto-resolves by stock change.
- **Unknown-status** — `schema_warning` renders "Unknown status (raw value)",
  degraded health chip, never silently success.

## 8. Status badge taxonomy (one badge per layer; never merged)

From `shopify-fulfillment-status-model.md` (four-layer taxonomy) + the code fields:

- **Odoo delivery** — `stock.picking.state` (authority for real stock).
- **Order roll-up** — A1 `OrderDisplayFulfillmentStatus`.
- **FulfillmentOrder work-state** — A2 `FulfillmentOrderStatus`.
- **Fulfillment result** — A4 `FulfillmentStatus` (Mode-2 condition-2 gate) →
  code `fulfillment_status_raw`/`_normalized`/`_is_success`.
- **Carrier milestone (display only)** — A5 `FulfillmentEventStatus` →
  code `display_status_raw`/`_normalized`.
- **Connector reconciliation** — `reconciled_state`.

Severity vocabulary reuses U0 tokens: calm/neutral, info, warning, danger,
unknown. **Colour is never the only signal** (icon + label always). Severities
never downgrade by roll-up (row shows the max severity across its layers).

## 9. States, empties, responsive, accessibility, performance

- **Five states per surface** (loading skeleton `aria-busy`; loaded; empty
  (calm/directive); error/manual-review (danger + owner + decision); degraded/
  offline). Prototype also defines an 11-state gallery — treat any extension as an
  explicit `[Recommendation]`, never a silent change.
- **Bounded queries** — server-paginated Odoo-native lists (PB-9); default search
  facets that show the exception subset while "the full list stays available";
  exception regions cap at ≤3; any U1 aggregate read uses the U0 constant-query,
  capped-read `AbstractModel` shape (`search_count` + `limit`-ed read).
- **Accessibility** — word + icon (never colour alone, WCAG 1.4.1); real
  `<th scope>`; comparison tables reflow to labelled cards ≤640px; ordered
  checklists/timelines as real `<ol>`; drawers `role="dialog"` `aria-modal`,
  destructive control last in focus order, Esc cancels; `:focus-visible` 2px ring;
  `prefers-reduced-motion`; exactly one primary button per screen; confirm buttons
  name their exact effect.
- **Responsive & RTL** — CSS logical properties only (no left/right rules), so
  `dir="rtl"` mirrors with no overrides; compact shell ≤900px, phone ≤640px; no
  horizontal page scroll; optional columns hidden ≤640px keeping the primary
  answer visible.
- **Icons** — use the **platform FontAwesome set (P9)**; the prototype's inline
  SVGs are placeholders.

## 10. Copy principles specific to U1 (code→label mapping owned by the copy deck)

The U1 copy deck (`docs/06-prompts/ui-u1-copy-deck.md`, a U1-implementation
deliverable) maps every **code** value (§5 of the contract) to an operator label,
including the reconciliations in `u1-backend-ui-contract-inventory.md` §10
(`external_app`, `external_unknown`, `quantity_overrun`, `review`). Reusable copy
already written (all `[Proposed]`, MBQ-22 owns final): "Delivered per carrier —
Odoo delivery not validated"; "handled outside Odoo"; "Unknown status (raw value)";
"No surprise emails"; the review-case sentence template (which order, which
items/quantities, from which Shopify location, by whom, tracking, what Odoo would
do).

## 11. What U1 does NOT introduce

No new design system; no Owl production surface for fulfillment (PD-7 excludes it);
no chatter/mail (U0 is deliberately not mail-enabled — adding it would be a new
dependency, out of U1 scope); no new top-level app; no masked-PII/unmask UI (SEC-2
removes masking and fulfillment has no PII); no setup wizard; no dark-mode (U0 is
light-only — a theme-parity decision is deferred).
