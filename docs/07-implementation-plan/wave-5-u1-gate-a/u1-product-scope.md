# Wave 5 U1 — Product Scope Contract (Fulfillment Operator Experience)

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23; **reconciled 2026-07-25** against the final
> integrated backend. Defines U1 strictly around the **merged Wave 4 backend as it
> now exists on `mvp/program-integration@2583081f`**
> (`u1-backend-ui-contract-inventory.md` §0/§0.1). **U1 implementation remains
> unauthorized.**

## 0. Numbering reconciliation (important)

The older `ui-implementation-phases-packet.md` numbers phases **U0 = prototype,
U1 = core operator surface, U2 = setup + domain (incl. fulfillment) workspaces,
U3 = resilience/export/governance**. But **PR #192 merged "U0" as the first
usable operator surface** — it absorbed that packet's "U1 core surface"
(navigation, dashboard, Sync Center, Error/Review Center, logs, mutation
evidence, safe actions). The program has therefore **re-based UI numbering**:

- **U0 (merged)** = core operator foundation.
- **U1 (this Gate A)** = **fulfillment operator experience** — which maps to the
  *fulfillment slice* of the old packet's **U2** and to wave-5 DoR §1.2 / §5.6.

**Consequence:** the packet's §6 "U1 locked prompt" is for the already-delivered
core surface and is **NOT reusable** for this U1. This Gate A ships a **fresh**
locked prompt (`u1-locked-implementation-prompt.md`). This reconciliation is
logged as **D-P1-1** in `u1-risks-and-open-questions.md`.

## 1. U1 mission

Give fulfillment operators a safe, role-aware, Odoo-native surface to **see and
drive** the accepted Wave 4 Mode 1 + Mode 2 backend — the operating-mode selector,
the mode-switch confirmation, the review workspace, fulfillment/tracking lineage,
and manual-review UX — **without owning any mutation or business logic**.

## 2. In-scope capabilities (each mapped to an exact backend surface)

| # | U1 capability | Backend surface (exact) |
|---|---|---|
| C1 | **Fulfillment mode display** | `store.settings.fulfillment_operating_mode` (`mode1`/`mode2`) |
| C2 | **Mode-change entry point** | `action_start_mode2_switch`, `action_rollback_to_mode1` (admin) |
| C3 | **Confirmation of consequences** (current mode; requested mode; STATIC operational consequences; the switch-in-progress flag; bounded, **non-authoritative informational** counts of blocked/running work and open review cases — the server reconciliation scan, NOT the wizard, decides whether review is required or switching is legal) | Composed from bounded, ACL-safe reads of `shopify.connector.job` (states/job_types), `inbound.evidence` (`reconciled_state='review'`), `fulfillment_switch_in_progress`; **displayed only** (never used for eligibility or action routing) by the confirm wizard |
| C4 | **Mode-switch progress + final status** | `fulfillment_switch_in_progress`, `fulfillment_last_mode_switch_at/uid`, the `fulfillment_mode_switch_scan` job + its log |
| C5 | **Review workspace** (store; company — now a real stored `company_id` inherited from the owning store, displayed read-only and never as a selector (SEC-3, contract §8.2); order; picking; fulfillment binding; job; mutation attempt; review reason — **21 values**; safe evidence summary; available accepted actions) | `inbound.evidence` (+ `order_binding_id`, `fulfillment_binding_id`, `store_id`, `review_reason`, safe fields) → picking via binding; job/mutation via lineage; actions per §6 |
| C6 | **Fulfillment/tracking lineage** (source trigger; job family; mutation domain; operation scope; remote resource refs; local picking; reconciliation state; audit logs) | `job.trigger_origin`, `job.job_type`, `mutation.attempt.mutation_domain`, `job.operation_scope_key`, `shopify_*_gid` fields, `binding.picking_id`, `reconciled_state`, `shopify.connector.job.log` |
| C7 | **Failure & manual-review UX** (actionable operator language; no raw traceback/payload/token/credential; clear retry/review/resolve boundaries) | `review_reason`, `review_detail` (sanitized), `job.error_class`/`manual_review_subreason`/`state`, safe mutation-attempt summary |
| C8 | **Role behavior** — customer-facing **UI visibility** gates on the two **merged** SEC-2 roles (`group_shopify_connector_user` / `group_shopify_connector_admin`, contract §8.1); the **server** enforces the four internal capability groups (auditor/operator/reviewer/admin) the two roles resolve to via implied-group closure | UI visibility: two SEC-2 roles; server authorization: four internal groups; per-action gates in §6 of the contract |
| C9 | **Accessibility & responsive behavior** | view-level (design-system tokens, keyboard/focus, RTL) |
| C10 | **Bounded queries & safe list defaults** | view search/list defaults, `limit`, sane default filters |

## 3. Explicitly out of scope for U1 (forbidden)

Direct Shopify transport; direct mutation creation; any parallel mode-switch/
business logic; direct protected-field writes; invented server state/action/
selection value; webhook/OAuth/controller work; product export; the U2 setup
wizard; mappings/configuration outside fulfillment operator scope; broad redesign
of U0; any Owl production surface (PD-7 excludes fulfillment); any live Shopify
request or mutation.

## 4. Role → capability matrix (server-enforced) + UI visibility model

**UI visibility** gates on the two SEC-2 customer-facing roles (Connector User,
Connector Administrator). The columns below are the **server-enforced internal
capability groups** those two roles resolve to via SEC-2 implied-group closure
(Administrator → User → operator/reviewer → auditor). A hidden button is never the
security control; the server enforces these gates regardless of the UI.

| Capability | Auditor | Operator | Reviewer | Administrator |
|---|---|---|---|---|
| View mode, review workspace, lineage (read) | ✔ (read-only) | ✔ | ✔ | ✔ |
| `action_start_mode2_switch` / `action_rollback_to_mode1` | ✗ | ✗ | ✗ | ✔ |
| `action_import_tracking` / `action_acknowledge_external` | ✗ | ✔ | ✔ | ✔ |
| `action_validate_proposed` | ✗ | ✗ | ✔ | ✔ |
| `action_release_fulfillment_review` | ✗ | ✗ | ✔ | ✔ |

(✗ = server refuses with `AccessError` and zero side effects; the U1 button must be
hidden/disabled for that role so UI and ACL agree — wave-5 DoR hard-stop 9.) An
**ordinary internal user** (no connector group) sees no fulfillment menu and is
denied every action.

Post-SEC-2 mapping (what the two customer-facing roles resolve to): **Connector
User** ⇒ operator∪reviewer∪auditor (so a User can review, import tracking, validate
proposed, release review); **Connector Administrator** ⇒ all (adds mode switching).
U1 tests prove **both** the two-role UI visibility **and** the direct-RPC server
denial through these internal groups.

## 5. Operator mental model U1 must convey (from `fulfillment-operating-modes.md`)

- **Mode 1 (Odoo-Controlled, default):** Odoo delivery validation drives Shopify
  fulfillment; external Shopify fulfillments become **review cases** — never touch
  Odoo stock automatically.
- **Mode 2 (Bidirectional Exact Reconciliation, opt-in):** everything Mode 1 does,
  **plus** an external fulfillment may auto-validate the Odoo delivery **only** when
  the full 16-condition checklist passes; **any ambiguity falls back to Mode 1
  behavior** (review, no stock change).
- **Mode switching (admin-only, audited):** switching to Mode 2 runs a **read-only
  safe reconciliation scan**; Mode 2 activates only on a clean scan; blockers abort
  back to Mode 1. **Never replays history** — pre-existing unresolved externals
  stay review cases and are surfaced as a **bounded, non-authoritative informational
  count** at confirmation time (the server reconciliation scan is authoritative).
  **Rollback to Mode 1 always allowed**; cancels in-flight Mode 2 evaluations back to review; evidence/
  bindings/audit untouched. In-flight Layer 2 mutation jobs are **not** cancelled.
- **CV-013 caveat:** the `fulfillment_staff_permission` readiness check is
  `NOT_PROVEN`; live fulfillment mutation qualification stays blocked until
  operator-confirmed and dev-store-validated (issue #185). U1 must surface this,
  never present live mutation as proven.

## 6. Acceptance-matrix alignment

U1 delivers wave-5 DoR §5.6 ("Fulfillment Mode UI wired to the Wave 4 backend":
Administrator mode selector, mode explanation/confirmation screen,
unresolved-external-fulfillment UI, User review workspace) and contributes to
mvp-acceptance-matrix fulfillment/UI rows. U1 does **not** re-build any Mode 2
backend logic (DoR §5.6, fulfillment-operating-modes §10).
