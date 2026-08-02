# UI Restructure Design Contract — Locked Target Contracts and Independent Verification (2026-08-02)

> **Status: Control-room ruling captured and independently verified —
> AWAITING PRODUCT-OWNER STRUCTURE/DESIGN SIGN-OFF. IMPLEMENTATION IS NOT
> AUTHORIZED BY THIS DOCUMENT.** This document records, verbatim in intent,
> the 2026-08-02 control-room ruling (ChatGPT 5.6) on the connector's product
> restructure, together with this session's independent code-level
> verification of its load-bearing claims at the exact governed candidate
> head `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` (PR #204 head; also the
> base of this branch). It consolidates the **locked target contracts** that
> the ruling requires to be incorporated into the design specification before
> any UI implementation wave is authorized.
>
> **Decision framing (CLAUDE.md §8):** the ruling itself is a **control-room
> decision input**; the contracts below are **Recommendations bound by that
> ruling** until the product owner signs; the verification results in §2 are
> **Facts** (file:line evidence at the exact head); everything marked
> [Inference] is this session's reasoned interpretation.
>
> **Supersession at contract level.** Where the hierarchies and dashboard
> shapes below conflict with
> [`premium-ux-master-specification.md`](./premium-ux-master-specification.md) §2,
> [`screen-inventory-and-navigation-map.md`](./screen-inventory-and-navigation-map.md),
> [`ui-operations-360-dashboard-spec-2026-08-01.md`](./ui-operations-360-dashboard-spec-2026-08-01.md)
> (the combined Store 360 page), or the experimental branch
> `codex/wave-5-premium-ui-revamp` @ `067ba238…`, **this document's contracts
> win** once signed. Those documents are not rewritten; they remain the
> historical record.
>
> Inputs captured under §7 discipline:
> [product & restructure review](../00-source-materials/2026-08-02-product-restructure-review-capture.md) ·
> [functional correctness & data integrity audit](../00-source-materials/2026-08-02-functional-correctness-audit-capture.md) ·
> control-room ruling verbatim in Appendix A below.

---

## 1. Executive assessment (this session's independent view)

**The diagnosis is correct and the direction is right.** [Inference, from the
§2 verification] The connector's backend integrity substrate — durable jobs
with legal state transitions, store/company scoping, mutation-attempt
evidence, idempotency and CAS inventory writes, preview-first export,
first-push governance, guarded lifecycle — is genuinely strong and is the
product's differentiator. The operator-facing product built on top of it is
organized around implementation history (jobs, evidence records, per-module
menus), not operator work. That is why the product does not feel premium:
not because the engine is weak, but because the shell exposes the engine
instead of the work.

**Option D (hybrid: preserve backend contracts, refactor selected seams,
rebuild the shell) is the correct choice.** A full rewrite (Option C) would
discard the hardest-won, most defensible assets for zero operator-visible
gain. Targeted repair (Option A) would preserve a fragmented product. The
scorecard in the restructure review (D = 4.78/5) matches this session's
independent reading of the code.

**The experimental branch `067ba238…` is correctly rejected as the target
design in its present form.** Verified directly on the branch: it does move
to Overview/Operations/Reporting/Configuration (right direction), but it
keeps `Mutation Evidence` as a navigation leaf (under Needs Attention),
keeps `Sync Center` as a generic queue destination (under "Sync & Recovery"),
leaves Product/Variant Matching under Operations, and leaves the combined
Store 360 page as the single overview. Those are exactly the four
corrections the ruling names. It remains valuable as a research spike.

**The three release-blocking correctness defects are real.** All three were
reproduced from source this session (§2). They are not cosmetic: each one
produces a user-visible wrong or stuck state through the normal UI. The way
forward must sequence these repairs **before or alongside** the shell
rebuild — a beautiful shell over a stuck mode switch is still a broken
product.

---

## 2. Independent verification of the load-bearing claims

All checks read the exact head `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e`
(local checkout of this branch, which sits on that commit) and the
experimental branch head `067ba238…` fetched from origin. Claims below are
**Facts** with file:line evidence unless marked otherwise.

| # | Claim (source) | Verdict | Evidence at exact head |
| --- | --- | --- | --- |
| V-1 | F-01: onboarding location refresh admits an async job but the wizard never follows it to terminal | **CONFIRMED** | Server: `refresh_shopify_locations` admits a job and returns the momentary state (`addons/shopify_connector_core/models/shopify_connector_setup_wizard.py:1482-1498`). Client: `refreshLocations()` is a single `_call` (`addons/shopify_connector_core/static/src/js/shopify_connector_setup_wizard.js:510-515`); `_call` adopts one response (`:305-321`); no `setInterval`/poll exists anywhere in the setup client (grep: only the dashboard has a timer). The refresh badge renders whatever state the admission response carried (`:227-239`) and goes stale. |
| V-2 | F-02a: mode-switch flag is written before enqueue success is checked | **CONFIRMED** | `action_start_mode2_switch` writes `fulfillment_switch_in_progress=True` + nonce, then calls `_enqueue_once` (`addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_scans.py:405-425`). `_enqueue_once` returns an **empty recordset without raising** for a non-connected store (`addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_admission.py:187-188`) → flag set, no job exists, nothing will ever clear it. |
| V-3 | F-02b: an incomplete scan leaves the switch stuck, and the normal UI offers no recovery | **CONFIRMED** | Test contract: `test_mode_switch_scan_incomplete_pass_fails_closed` asserts `fulfillment_switch_in_progress` stays `True` after `JobHandlerError` (`addons/shopify_connector_fulfillment/tests/test_fulfillment_mode_switch.py:369-395`). UI: "Return to Mode 1" is `invisible="fulfillment_operating_mode != 'mode2'"` (`addons/shopify_connector_fulfillment/views/shopify_connector_store_settings_fulfillment_views.xml:51-57`), so in the stuck state (mode1 + in-progress) the only visible action is "Switch to Mode 2" again. Server-side `action_rollback_to_mode1` would clear the flag and is documented "always allowed" (`shopify_connector_fulfillment_scans.py:427-439`) — but the UI never shows it in mode1. |
| V-4 | F-02c: repeated confirmation can create duplicate scans | **CONFIRMED** [Inference from code] | Each `action_start_mode2_switch` call generates a fresh nonce, and the `_enqueue_once` dedup key embeds it (`mode_switch:%d:%s`, `shopify_connector_fulfillment_scans.py:414-424`) — so every re-confirm admits a distinct scan job; nothing coalesces onto the in-flight one. |
| V-5 | F-03: sales totals include orders flagged for Shopify review | **CONFIRMED** | The C1 population excludes quarantined/cancelled only (`addons/shopify_connector_sale/models/shopify_connector_ui_store360_sale.py:87-93`); `shopify_connector_review = True` orders are counted as a separate lifecycle card (`:537-538`) yet remain inside the `amount_total:sum` commercial aggregates (`:135-145`). Currency separation itself is correct (`groupby=['currency_id']`). |
| V-6 | Current menu tree follows implementation history | **CONFIRMED** | Root has ~11 top-level entries: Dashboard, Stores, Sync Center, Error & Review Center → Mutation Evidence, Sync Operations Analysis, Logs (`shopify_connector_core/views/shopify_connector_menus.xml`), plus Orders, Catalog & Matching, Inventory (with First-Push Guard, Location Mapping, Refresh/Map actions as menu items), Fulfillment (with Fulfillment Jobs, Fulfillment Settings), Export (with Export Settings, Export Diagnostics, Reconnect and Backfill) from the domain modules' menu files. Configuration, operations and diagnostics are interleaved; technical record names are navigation labels. |
| V-7 | Security foundation: two visible roles + hidden internal capability groups | **CONFIRMED** | `shopify_connector_core/security/shopify_connector_security.xml:40-77`: Auditor/Operator/Reviewer carry `privilege_id=False` (hidden capability primitives); User and Administrator carry the connector privilege (visible); Administrator ⊃ User ⊃ Operator+Reviewer → Auditor. The ruling's instruction — keep the hidden groups, do not remove them — matches the shipped structure. |
| V-8 | Store model matches the multi-store contract's foundation | **CONFIRMED** | `shop_domain` unique + readonly (`shopify_connector_core/models/shopify_connector_store.py:78,231-233`); every store requires exactly one company (`:275-289`); shop-identity verification compares Shopify's returned `myshopifyDomain` (`:772`). The UX layer (store selector everywhere, per-store isolation surfacing) is the incomplete part, as the ruling says. |
| V-9 | F-06: decision-relevant reads bypass the job-bound business-call contract | **CONFIRMED (spot-check)** | 12+ `client.execute(` read call sites in `shopify_connector_inventory/models/shopify_connector_inventory_service.py:1532,2255`, `shopify_connector_fulfillment/models/shopify_connector_fulfillment_reader.py:120`, and `shopify_connector_product_export/models/*` — the legacy read path, not a lease/generation-bound `execute_business_read`. |
| V-10 | F-08: no webhook pipeline exists | **CONFIRMED (spot-check)** | No `controllers/` directory and no `@http.route` in any `shopify_connector_*` addon. Freshness is scan/reconciliation-based; product language must say so. |
| V-11 | "Confirm without the review screen" weakens preview-first export | **CONFIRMED WITH NUANCE** | The button exists (`shopify_connector_product_export/views/shopify_connector_product_export_views.xml:124-129`) but requires `state == 'previewed'` and opens the fallback confirm **wizard** — deliberately kept as the JavaScript-unavailable route (comment `:117-123`). It skips the diff *display*, not the preview *requirement*. [Inference] The correction is therefore a **relabel/reroute** decision (make the fallback show the diff summary, restrict it, or move it to break-glass) — not the removal of an unguarded apply path, which does not exist. |

**Net verification verdict:** every load-bearing claim in the control-room
ruling and the two audits that this session checked is true at the exact
head, with one nuance (V-11). The ruling can be adopted as written.

---

## 3. Locked target contracts

The eight contracts below are the binding design targets. Wireframes and the
design specification must incorporate all of them before the control room
authorizes UI implementation.

### C1 — Menu hierarchy (locked)

| Main menu | Children |
| --- | --- |
| **Dashboard** | Sales Dashboard; Connector Health |
| **Operations** | Orders; Product Imports/Exports; Inventory; Fulfillment; Runs & Recovery; Needs Attention |
| **Reporting** | Sales Analysis; Sync Performance; Audit Trail |
| **Configuration** | Stores & Onboarding; Sync Rules; Product/Variant/Customer/Location Mappings; Export Settings; Fulfillment Settings and Mode |

Rules bound to C1:

1. **Matching and mappings are Configuration, not Operations.** Unresolved
   matching *cases* surface through Needs Attention; the durable mapping
   tables live under Configuration.
2. **Store management stays under Configuration** (Stores & Onboarding), not
   as a top-level destination.
3. **No technical record name is a navigation label.** `Mutation Evidence`,
   `First-Push Guard`, `Sync Center`, `Error & Review Center`, `Fulfillment
   Jobs` disappear from navigation; mutation evidence and diagnostics become
   contextual drill-downs from Needs Attention or Runs & Recovery, visible to
   admin/support roles. Operator copy says "run", not "job".
4. **Configuration is Administrator-only.** Operations/Dashboard/Reporting
   follow the visible User role plus the hidden server-side capability
   guards (V-7).
5. Menu XML IDs should be kept stable where possible (redirect/alias
   strategy for renames) to protect bookmarks, tours, and access rules —
   the migration risk the restructure review flags.

Mapping from the current head (V-6) and from `067ba238…`: `Stores` →
Configuration › Stores & Onboarding; `Sync Center` → Operations › Runs &
Recovery; `Error & Review Center` → Operations › Needs Attention (human
cases only); `Mutation Evidence` → drill-down detail, out of navigation;
`Catalog & Matching` → split: operational import/export monitoring under
Operations › Product Imports/Exports, match/mapping tables under
Configuration › Mappings; `Location Mapping`/`Refresh`/`Map` menu items →
Configuration › Mappings; `Export Settings`, `Export Diagnostics`,
`Fulfillment Settings` → Configuration; `Sync Operations Analysis` →
Reporting › Sync Performance; `Logs` → Reporting › Audit Trail.

### C2 — Access model (locked)

The customer sees exactly two roles: **User** and **Administrator**.
Auditor, Operator, Reviewer remain hidden internal capability groups backing
ACLs and server-side guards — retained, never removed, never surfaced.
Assigning neither visible role yields no connector access. Configuration
(all of C1's fourth column) is Administrator-only. This matches the shipped
SEC-2 structure at the exact head (V-7); the contract forbids regressing it
during the shell rebuild.

### C3 — Multiple stores (locked)

- One Shopify **permanent domain** = one connector store (enforced today,
  V-8).
- Every store belongs to exactly **one Odoo company**; one company may
  operate **multiple stores** (enforced today, V-8).
- Credentials, connection generation, readiness, settings, mappings,
  fulfillment mode, queues, and recovery state are **isolated per store**.
- Every dashboard and operational screen carries a **store selector** and
  shows the store on every result row.
- "All stores" **health** aggregation is allowed; a failing store must stay
  visible inside any aggregate.
- **Monetary amounts are never summed across currencies** (the current
  per-currency grouping, V-5, is the pattern to keep).
- A problem or exhausted API allowance on one store must **never pause
  another store**.

### C4 — Onboarding completion contract (locked)

Onboarding configures one store completely, in this order: (1) store
identity + owning company; (2) authentication; (3) verify Shopify's returned
permanent domain and shop ID; (4) verify required scopes; (5) choose enabled
domains and directions; (6) refresh the Shopify data setup needs; (7)
complete all applicable mappings; (8) select source-of-truth rules; (9)
configure first-push safeguards; (10) configure fulfillment mode and
notifications; (11) run final readiness checks; (12) review and activate.

**Activation stays blocked** while any enabled domain has an incomplete
mapping, a stale refresh, a missing permission, or a failed readiness check.
Presentation may group these twelve steps into merchant phases (the
restructure review proposes five: Connect → Policy → Map → Prepare →
Activate), but the completion semantics above are the contract.

**Location-refresh acceptance test (binding, repairs V-1).** The refresh
journey passes only when, through the **genuine browser UI and the genuine
dispatcher** (mocked immediate payloads do not count):

- one click admits exactly one store-scoped refresh job;
- duplicate clicks coalesce onto the same in-flight job;
- the UI follows that exact job until a terminal state;
- success reloads the Shopify locations and recomputes readiness;
- failure shows a useful reason, a Retry, and preserves the job identity;
- saving a mapping immediately updates readiness;
- closing and reopening onboarding resumes the correct store and step;
- a disconnected/reconnect-needed generation cannot silently serve stale
  locations.

### C5 — Remote-write acknowledgement ladder (locked)

"Job succeeded" is never presented as proof Shopify received an export. The
merchant-facing status ladder is:

| Status | Meaning |
| --- | --- |
| Queued | Nothing sent yet |
| Sending | A mutation attempt is in progress |
| Accepted by Shopify | HTTP success, no top-level GraphQL errors, no `userErrors`, expected remote identity returned |
| Verified in Shopify | A follow-up read or asynchronous-operation result confirms the expected remote state |
| Needs attention | Transport outcome ambiguous, or verification disagrees |
| Rejected | Shopify definitively rejected the mutation |

Rules: **Accepted ≠ Verified** and the UI must distinguish them where
business risk requires (repairs F-04); asynchronous operations (e.g. async
`productSet`, which returns an operation to check separately) must not show
Verified before the operation reaches terminal success; verification depth
is a risk-based policy, not a blanket readback of every write.
Sources (cited by the control room, 2026-08-02; consistent with the
already-captured Layer 2 research in
[`../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md)):
[`productSet`](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet),
[response codes](https://shopify.dev/docs/api/usage/response-codes),
[idempotency](https://shopify.dev/docs/api/usage/implementing-idempotency).

### C6 — Fulfillment mode-switch contract (locked; repairs V-2/V-3/V-4)

Represent the transition with **separate fields**: effective mode; requested
mode; scan/transition state; transition job reference; blocker/reason; next
action; last verified timestamp. Then:

- Mode 1 → confirmation → reconciliation scan → Mode 2 **only after clean
  completion**; requesting Mode 2 never changes effective mode.
- Admission failure (including the silent non-connected refusal, V-2)
  returns the store to stable Mode 1 — the requested state must never
  outlive a failed admission.
- Retryable failure shows the next retry; terminal failure returns to a
  **recoverable** Mode 1 and preserves the failure evidence.
- **"Return to Mode 1" is reachable during and after a failed switch** —
  not only when effective mode is already Mode 2 (fixes V-3's
  `invisible` condition).
- A stale or missing scan job can never leave the store permanently
  "switching"; repeated confirmation coalesces onto the in-flight scan
  instead of admitting a duplicate (fixes V-4).

### C7 — Dashboard direction (locked)

**Sales Dashboard and Connector Health are two separate pages** — not the
combined Store 360 page currently implemented, and not tabs inside one
combined production dashboard. Contracts per page:

- **Sales Dashboard** is a reporting surface: per-currency reconciled
  orders, gross/net/refunds, AOV; orders awaiting data review are shown
  separately and **excluded from reconciled totals** (repairs V-5); the
  metric is named honestly ("Imported Odoo order value") until the order
  lifecycle work makes a "Shopify sales" claim true; every KPI's drill-down
  recalculates to the displayed number.
- **Connector Health** derives from job/attempt/throttle/mapping/
  reconciliation evidence: healthy vs attention stores, queue depth and
  oldest blocked age, retries and exhausted failures, ambiguous mutations,
  last successful sync per domain, throttle headroom, mode-switch state.
  No sales KPI on this page; no aggregate may hide a failing store or an
  unknown subsystem. A store with zero sales can be healthy; a store with
  high sales can be critical.
- Styling: restrained Odoo-native typography, consistent spacing, limited
  cards, no decorative clutter, clear timestamps, responsive at
  mobile/tablet/desktop, full RTL support.

### C8 — Preserved backend contracts (protected during the rebuild)

The rebuild must not weaken: job state machine and legal transitions;
store/company scoping and connection generation; binding identity;
mutation-attempt evidence and reconciliation; inventory CAS + first-push
governance; preview-first export (V-11's fallback route is redesigned, not
turned into an unguarded apply); guarded two-phase disconnect. Refactor
seams explicitly opened by the audits: business-read admission (V-9),
onboarding orchestration (V-1), mode-switch orchestration (V-2/3/4), order
lifecycle/refund policy and metric definitions (V-5), remote-acknowledgement
statuses (C5). Webhooks remain absent (V-10): product language states
scan-based freshness honestly; webhooks are a separate future capability.

---

## 4. Way forward (recommended sequencing)

[Recommendation — subject to control-room/product-owner approval; consistent
with the audits' bounded-correctness ruling and the restructure review's
roadmap. No implementation is started by this document.]

1. **Product-owner sign-off** on this contract set (C1–C8). This is the
   restructure review's Phase 1 exit gate ("Mostafa signs structure/design").
2. **Design-spec + wireframe update** (docs-only): update the premium UX
   master specification and produce updated wireframes for Overview split
   (Sales vs Health), Needs Attention, Runs & Recovery, Configuration
   consolidation, onboarding phases, and the mode-switch panel — each
   incorporating C1–C7 verbatim. Validate against this contract, then seek
   control-room approval to open implementation.
3. **Bounded correctness phase before/with the shell rebuild** (per the
   functional audit §13): repair onboarding refresh follow-through (V-1),
   mode-switch state machine + recovery reachability (V-2/3/4), and sales
   metric definition/exclusion (V-5); add Accepted/Verified statuses (C5)
   and the job-bound business-read seam (V-9). Each lands with the
   acceptance tests the contracts define — the refresh test through the real
   browser + dispatcher, the mode-switch stuck-state matrix, and
   KPI-to-drill-down reconciliation.
4. **Shell rebuild waves** in the DEC-040 large-batch cadence: navigation +
   configuration consolidation first (menu/action XML, redirects, role
   gating), then operations & attention surfaces, then the two dashboards,
   then reporting/audit, then setup polish — every code batch with
   independent Claude review, exact-head Odoo.sh runtime evidence, and no
   self-acceptance, per CLAUDE.md §13.
5. **Release gates unchanged and still open:** exact-head Odoo.sh
   qualification of the governed candidate, controlled Shopify store
   campaign (two stores / two currencies / two companies), business
   reconciliation, and UAT — the audit's Gates A–E. Nothing in the UI
   restructure substitutes for them.

**Branch/PR posture:** PR #204 stays draft and unmerged; `067ba238…` is a
research spike, never merged as-is; the checkpoint and program-integration
protections in CLAUDE.md §13 are untouched by this document.

---

## 5. Open items for the product owner

1. **Sign-off** on C1–C8 as the binding design contract (yes/no/amend).
2. **Export fallback route (V-11):** keep a no-JS confirm path with the diff
   summary embedded, restrict it to Administrator, or move it to break-glass
   with audit? (The audits recommend restrict-or-remove; the current button
   is a deliberate accessibility fallback — a product call, not a code
   call.)
3. **Order lifecycle policy (F-05):** implement local
   adjustment/refund/cancellation semantics, or declare the supported-kernel
   scope and exclude divergent orders from reconciled metrics (C7 assumes
   the declared-scope option until decided).
4. **R5 document:** the internal R5 reference the restructure review could
   not access remains a traceability gap — provide it or declare it
   non-binding.

---

## Appendix A — Control-room ruling of 2026-08-02 (verbatim)

> Yes—your corrections are valid, and the experimental UI branch is not
> acceptable as the final design.
>
> Competitors broadly separate configuration from operations, although their
> exact menus differ:
>
> * TeqStars uses store/instance records under Configuration and launches
>   daily work through an Operations action.
>   ([setup](https://docs.teqstars.com/19.0/applications/shopify/setup/create_instance.html),
>   [operations](https://docs.teqstars.com/19.0/applications/shopify/customer_management/customer_import.html))
> * Emipro separates its Dashboard/Perform Operation and Processes areas from
>   Configuration/Instances and locations.
>   ([operations](https://docs.emiprotechnologies.com/shopify-odoo-connector/v16/shopify-odoo-operations.html),
>   [locations](https://docs.emiprotechnologies.com/shopify-odoo-connector/v16/sale-auto-workflow-payment-gateway-and-financial-status-configurations/shopify-locations.html))
> * VentorTech uses a Quick Configuration flow before normal synchronization
>   and initial import.
>   ([configuration](https://ecosystem.ventor.tech/faq/e-commerce-connectors/common-questions/how-to-install-and-configure-ventortech-connector/))
> * Webkul and TeqStars both model multiple Shopify stores as separate
>   instances managed centrally.
>   ([Webkul](https://webkul.com/blog/shopify-odoo-connector/),
>   [TeqStars](https://docs.teqstars.com/19.0/applications/shopify/shopify_faq.html))
>
> The correct lesson is therefore "configure each store first, then operate
> it"—not blindly copying any competitor's menu.
>
> [Locked target hierarchy — as §3 C1 above, verbatim.]
>
> Important corrections to the `067ba238…` experiment: matching and mappings
> move from Operations to Configuration; store management remains under
> Configuration; sales and connector health become separate pages — not the
> combined Store 360 page currently implemented; diagnostics and mutation
> evidence become contextual drill-downs from Needs Attention or Runs &
> Recovery, not prominent merchant navigation; Configuration is
> Administrator-only.
>
> [Access model — as §3 C2 above. Multiple stores — as §3 C3. Onboarding
> completion contract and refresh acceptance test — as §3 C4. Evidence
> ladder — as §3 C5. Mode 1/Mode 2 corrected behavior — as §3 C6. Dashboard
> direction — as §3 C7.]
>
> Control-room decision: **Option D remains correct, but the experimental
> branch is rejected as the target design in its present form.** The menu,
> dashboard, onboarding, export acknowledgement and mode-switch contracts
> above must first be incorporated into the design specification and
> validated with updated wireframes. Implementation is not authorized yet,
> and no GitHub state was changed.

Access status of the competitor/Shopify links above: cited by the control
room on 2026-08-02; **not independently re-fetched in this session**
(recorded per CLAUDE.md §7.2 discipline — treat as control-room-provided
citations until a research session re-verifies them; the Shopify API claims
are additionally consistent with the repo's existing captured research, see
C5).

## Appendix B — Session evidence boundary

Read-only verification of a local checkout at
`49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` plus `git show` of
`origin/codex/wave-5-premium-ui-revamp` (`067ba238…`); PR #204 metadata via
the GitHub API (open, draft, base `mvp/program-integration@87f1763a…`). No
Odoo runtime, no Shopify call, no browser session — the runtime-dependent
claims in the audits (e.g. exact-head Odoo.sh behavior) are **not**
re-verified here and keep their Partially Proven/Unproven status. No
`addons/**` file was touched by this session; this branch adds documentation
only.
