# PR #206 — Coherent Repair and UAT Ledger

**Repository:** `AdamsOdoo/Adams`
**PR:** Draft #206
**Candidate:** `codex/ui-restructure-implementation`
**Environment:** Odoo.sh development branches/databases and the confirmed Shopify development store only
**Owner:** GPT-5.6 SOL; independent review by GPT-5.6 Luna

This is the living ledger for the dependency-ordered product, inventory, order,
fulfillment, authorization, UX, and upgrade repair. It records accepted
contracts and evidence; it does not authorize a merge or a production action.
Update it after every accepted commit, development build, and live UAT proof.

## 1. Exact baseline

| Evidence | Value |
|---|---|
| Base | `fable/wave-5-completion` at `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` |
| Candidate HEAD | `d0776edaa05122b8cc220d4868f4fbc64cd3fe07` |
| Candidate tree | `1d0ce11302e34971b6facab857c3cc8ec3e2c3c3` |
| Parent | `3af0beea3cff6672ac81f29beac90f6cb4b26a91` |
| PR delta at audit | 44 commits, 171 files, `+10,198 / -2,423` |
| Exact-head Actions | Run `31983989514`, successful |
| Odoo.sh development build | Build `36490744`, Odoo 19.0, successful; exact candidate commit |
| Audit checkout | `/tmp/adams-audit-YpEUf4`, detached exact HEAD, clean |
| Ledger worktree | `Adams-ledger`, branch `codex/pr206-ledger-contract`, exact candidate HEAD |

The PR description's old `c11f0d5` reference is stale and is not evidence.
Any live-ref, Actions, or Odoo.sh advancement must be appended as a new
evidence row, never substituted silently.

## 2. Verified development-store UAT facts

The isolated seed product currently used for UAT is:

- Title: `Shopify Seed UAT 2026-08-17 C`; SKU: `SHOPIFY-SEED-20260817-C`
- Shopify status: Draft; inventory: `7`; price: `29.95`
- Product GID: `gid://shopify/Product/8650641047737`
- Variant GID: `gid://shopify/ProductVariant/48603042840761`
- Odoo import: template `933`, variant `1382`, template binding `926`, variant binding `839`
- Observed import defect: Odoo price `1.00`, blank internal reference/SKU, Track Inventory disabled, export disabled; binding retained `29.95` snapshot
- Preview `123` was not confirmed and did not mutate Shopify. It incorrectly proposed blank vendor/SKU, `29.95 → 1.00`, and treated Shopify `Title / Default Title` as structurally different from an Odoo singleton.
- Product create evidence: job `3225`, mutation attempt `167`, final `Not Applied` (`Shopify Validation` plus `Binding Conflict`); no safe fresh-preview recovery route was exposed.
- Location mapping exists and inventory push is enabled, but no inventory-level binding exists and inventory scans/previews have no discoverable initial pair.
- Marc Demo (`res.users` `651`) is an ordinary User; current observed menu/action behavior is recorded in the security/UX seam below.
- Real order/import/delivery/FulfillmentOrder/tracking/partial/backorder/Mode 2 proof is still absent.

## 3. Architecture-to-runtime seam map

| Seam | Production entry/caller and models | Identity/state/retry/scope/role contract | Automated coverage and missing live proof |
|---|---|---|---|
| **A — Product import/birth** | `shopify.connector.product.importer.import_product_sync`; `product.template`/`product.product`; template and variant bindings | Shopify source initializes SKU, price, vendor evidence, barcode/tags, option shape, and `inventoryItem.id`; birth initialization is distinct from later ownership; store-scoped identity; read-job replay only | Product tests cover payloads and binding writes, but live seed proved SKU/price/tracking gaps. Need real import → usable Odoo product and durable InventoryItem identity. |
| **B — Product update/create/recovery** | Product preview/create/update services and mutation dispatcher; product/variant bindings and mutation attempts | Canonical singleton normalization; omit absent fields; explicit managed clear only; fresh business intent/preview after definitely `Not Applied`; stale confirmation is never reusable | Preview/create tests exist; seed create `3225/167` proves recovery dead end. Need safe correction → fresh preview → fresh attempt and Shopify verification. |
| **C — Inventory identity/location/push** | `stock.move._action_done` → `_enqueue_from_stock_moves`; manual push; cron scan; location setup/mapping services; `inventory.level.binding` | Identity `(store, InventoryItem GID, Shopify Location GID)` plus variant/location uniqueness; mapping explicit; first push `pending → previewed → confirmed`; Odoo `free_qty` targets Shopify `available`; `committed` never written; CAS, operation-scope coalescing, bounded retry, reconcile-only uncertainty; Operator/Admin execution, Reviewer/Admin confirmation | Push/CAS/retry tests are extensive, but many directly create level bindings. No production caller creates the initial pair after product import/create or mapping activation. Need first-pair vertical proof and legacy repair. |
| **D — Order scan/import** | Store manual/cron order scan → `order_import_scan` → `order_import_sync`; `sale.order`, lines, order binding | Store/order GID and `updatedAt` payload identity; paginated stable read; customer/address/tax/payment and Decimal money gates; variant GID requires active product variant binding; replay is duplicate-safe; Operator/Admin entry | Scan/import tests use payload fixtures and direct bindings. Need real Shopify order → scan → import → replay, including product binding dependency and totals. |
| **E — Delivery/fulfillment/tracking** | Odoo `stock.picking._action_done` → fulfillment admission; picking write → tracking admission; `fulfillment.binding` | Delivery is source; FulfillmentOrder-based only; OPEN/IN_PROGRESS + CREATE_FULFILLMENT eligible; explicit order→FO→line/qty/location matching; each picking/backorder is one fulfillment; notification frozen; non-idempotent mutation uses reconcile-only uncertainty; Operator execution, Admin recovery | Admission/strategy tests cover gates but manufacture order/picking/binding states. Need real imported order → validated delivery → Shopify SUCCESS/GID → repeat no-op → tracking/partial/backorder/retry. |
| **F — Inbound fulfillment and Mode 1/2** | Reconciliation/reconnect scans → inbound evidence; Mode 2 evaluation/application; mode-switch actions | Connector-origin evidence applies; external fulfillment is review in Mode 1; Mode 2 requires ordered 16 checks, exact demand/location/line match, no overrun, second fresh read, and atomic local application; Admin switches/rolls back | Mode/evidence tests are mostly direct evidence/job fixtures. Need real external fulfillment observation, clean switch, exact Mode 2 application, and safe rollback. |
| **G — Authorization/isolation** | Menus/actions plus ACLs, record rules, direct RPC/server methods, company checks | No Access: no connector surface; User: read/audit + routine operations, no confirmation/review/config/credentials/mode/recovery; Administrator: User + privileged capabilities; fail closed server-side and per company/store | Existing security/UI tests cover individual rows; live ordinary-user observations showed hidden config reachable by direct action URLs and User seeing confirmation. Need full matrix through menus, URLs, RPC, actions, two companies, and upgrade. |
| **H — UX/operator recovery** | Mapping workspace, previews, confirmation, review/recheck/recovery actions | Mapping UI distinguishes no mappings, filtered mappings, healthy mappings, and attention; recovery always explains correction → fresh preview → fresh intent; no stale confirmation reuse | Product Mapping currently defaults to Needs Attention and falsely says no mappings. Need Odoo tour/live evidence for filters, first push, product recovery, and review release. |
| **I — Upgrade/qualification/evidence** | Module upgrade, exact-head Actions, Odoo.sh development build, UAT ledger | Existing rows/jobs/attempts survive; missing legacy InventoryItem identity is repaired without synthetic identity or Shopify mutation; repeated upgrade idempotent; evidence includes record IDs, GIDs, jobs, attempts, actor, before/after, cleanup | Historical Actions/build passed at baseline; no upgrade proof for this repair and no integrated live vertical proof yet. |

## 4. Accepted canonical contracts

### Product/template and variant

- Import creates a usable Odoo product from valid Shopify source data: SKU →
  `default_code`, price at birth, vendor/barcode/tags evidence, and durable
  Shopify product/variant/InventoryItem identity. Existing local values are
  not erased merely because a remote field is absent.
- Ongoing ownership is configured separately from birth initialization. Only
  owned-and-present fields are exported/updated; absent local values are
  omitted, not emitted as blank. A managed blank is distinct from an explicit
  clear intent, and list replacement is declarative only when the list is
  owned and present.
- One canonical normalization is shared by import, comparison, preview, and
  create/update payloads. Shopify `Title / Default Title` is equivalent to an
  Odoo singleton; the transport may encode Shopify's required singleton option
  without creating a false Odoo business attribute.
- Product create/set inputs must match the configured Shopify `2026-07` schema;
  variant SKU belongs in `ProductVariantSetInput.sku`, and option values must
  use the schema-valid representation.
- A definitely `Not Applied` attempt preserves its evidence but cannot be
  replayed. Recovery edits the underlying defect, generates a new preview and
  business intent, and creates fresh mutation evidence.

### Inventory/location

- Odoo is the ongoing source of truth; the default target is Shopify
  `available`. `committed` is never written. First Shopify→Odoo baseline is
  controlled/reviewed, not an autonomous bidirectional conflict resolver.
- Every push requires an explicit Odoo-location ↔ Shopify-Location mapping and
  a durable InventoryItem GID. No name inference or synthetic identity.
- Initial pair creation is a production transition after product import/create,
  mapping activation, and legacy reconciliation. The pair is idempotent and
  store/company scoped.
- First push is preview-first and explicitly confirmed. Repeated push uses
  fresh Shopify CAS/read evidence, operation-scope serialization, bounded
  retry, no-op handling, and reconcile-only uncertain outcomes.
- Shopify `InventoryItem.tracked` is persisted as source evidence. Policy:
  tracked items are eligible for inventory sync; untracked items are skipped
  with evidence. For a newly created Odoo template only, `tracked=true`
  initializes the template as storable so the imported product can participate
  in stock flows; `tracked=false` does not force an Odoo product-type change.
  Existing Odoo products always retain their user-selected product type, and a
  later Shopify tracking change remains evidence rather than silently changing
  that local configuration.

### Order/line

- A Shopify variant-GID line resolves only through an active/manual product
  variant binding with matching product identity. SKU fallback is only for a
  line without a variant GID; no on-demand guessing.
- Order import is atomic, paginated, replay-safe, company/store scoped, and
  records Decimal money/tax/line snapshots and operator evidence.

### Delivery/fulfillment and modes

- Odoo validated customer delivery is the outbound source. Shopify writes use
  FulfillmentOrder semantics only, with explicit FO/line/quantity/location
  matching. No legacy fulfillment API and no guessed match.
- Notification defaults off and the decision is frozen in the job. Tracking
  update is a separate operation. Partial delivery/backorder creates separate
  picking/fulfillment events; no implicit split or multi-location automation.
- `fulfillmentCreate` and tracking update are non-idempotent mutation surfaces:
  uncertain outcomes reconcile read-only; absence is inconclusive and never a
  blind resend. Mode 1 reviews external fulfillment; Mode 2 applies only after
  the full ordered gate and atomic local re-check.

### Field ownership, snapshots, blank, and idempotency rules

- Every field is classified as connector-owned, merchant-owned, evidence-only,
  or shared. Evidence snapshots are never used as mutation retry authority.
- Absent is not blank. Explicit clear intent is recorded separately from an
  unchanged/omitted value. Remote values are preserved unless the local field
  is owned and an intentional clear/replacement is present.
- Business intent, exact request, idempotency key, mutation attempt, and
  reconciliation evidence are immutable attempt/job data. Binding snapshots
  are display/reconciliation evidence only. No stale preview/confirmation or
  old attempt is reused.

## 5. Root causes and file-level implementation/test plan

1. **Ledger/contracts/fixtures:** this file plus behavioral tests for the
   proven product-import, blank-emission, singleton, initial-pair, mapping UX,
   and role defects. No source-text-only substitute for runtime behavior.
2. **Product spine:** product importer, binding models, normalization/payload
   builders, create finalization, and fresh-preview recovery. Persist SKU,
   birth price, InventoryItem evidence and binding snapshots atomically.
3. **Inventory spine:** inventory-level finalization/reconciliation callers in
   product import/create, mapping activation, and legacy repair. Preserve
   `shopify_connector_inventory` service safeguards and add real-entry tests.
4. **Order/fulfillment vertical:** after product/inventory identity is stable,
   prove the real development-store order chain and correct only defects
   exposed by that journey.
5. **Security/upgrade/UX:** exact capability replacement, server-side checks,
   action restrictions, mapping filters/empty states, recovery guidance,
   upgrade migration, tours, exact-head CI, and Odoo.sh module upgrade.

Primary existing contracts: [`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md),
[`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md),
[`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md),
[`DEC-006`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md),
[`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md),
[`Task 012`](task-012-order-import-implementation-packet.md),
[`Task 013`](task-013-inventory-sync-implementation-packet.md),
[`Task 013B`](task-013b-initial-inventory-baseline-packet.md), and
[`Task 014`](task-014-fulfillment-tracking-implementation-packet.md).

## 6. Ongoing evidence and release gates

### Accepted implementation commits (integration branch)

| Commit | Scope | Independent review |
|---|---|---|
| `dcc3e0e` | Living ledger, seam map, and canonical contracts | Accepted as the Phase A evidence baseline |
| `b7caaa8` | Visible role hierarchy, server-side capability enforcement, and mapping UX | Review found review-closure authority/copy and upgrade-proof gaps |
| `4ab1b7b` | Administrator-only review closure, corrected UI copy, and repeat XML-update proof | Re-reviewed: PASS |
| `52b6f4b` | Product birth normalization, ownership-aware export, singleton normalization, create/finalization/recovery contracts | Review found legacy repair, orphan-create, recovery/control exposure, structured price, and InventoryItem uniqueness gaps |
| `a54d6d3` | Product review corrections and behavioral regressions | Re-reviewed: PASS |
| `204825d` | Production first-pair bootstrap from product binding, mapping activation, scan, and legacy reconciliation | Review found that existing pairs remained eligible after a parent became stale |
| `12ef156` | Centralized active-parent/store/company eligibility at admission, dispatch, CAS, and reconciliation boundaries | Review found a post-terminalization TOCTOU that could roll back durable evidence |
| `0c1b38f` | Suppress stale-race successors without raising; preserve terminal/mutation evidence with behavioral race regressions | Review found immutable cross-store scope had been suppressed together with status races |
| `6c1d68a` | Validate store/company scope before activation identity/evidence writes; retain safe status-race suppression | Review found the analogous quantity-success evidence path unguarded |
| `0277637` | Validate store/company scope before quantity-success evidence writes with corrupt-binding regression | Inventory stack re-reviewed: PASS |

The accepted repair stack was published to the PR branch through the GitHub
Git-object API because this environment had no usable Git credential helper.
Published head `93fee1f3adae109dd7e56655365f6354f653b102` has tree
`c636a2f90b8ca889e16f6c7e9d220621daf73ca4`, an exact match to the reviewed
local integration tree. The PR remains draft and unmerged.

### First exact-head runtime qualification

- Odoo.sh development build `36522751` tested published head `93fee1f3` and
  stopped with four product-test failures and one test error among 1,112
  tests. No Shopify mutation was attempted.
- The error was environmental fixture coupling: the structured-birth test
  reused the global Odoo attribute name `Size`, which can already exist with
  `create_variant='always'`; the production importer correctly rejected that
  incompatible sparse-variant state.
- Two failures asserted the superseded rule that Odoo-authoritative or unset
  ongoing ownership also prevented birth-time price initialization. The
  accepted contract intentionally separates birth initialization from later
  refresh ownership.
- One failure was a brittle source-text assertion that every `list_price`
  assignment had to live inside `_apply_prices`; it rejected the intentional
  birth initializer without testing behavior.
- Correction commit `8fe8aab` gives the structured fixture a unique attribute,
  proves birth initialization followed by ownership-protected refreshes, and
  replaces source inspection with a runtime ownership transition test.
  `compileall` and `git diff --check` pass locally. Exact-head runtime rerun is
  required before this correction can be accepted.
- An independent Luna review passed the correction with no finding: it is
  test-only, accounts for every reported native failure/error, preserves the
  production importer, and does not mask a candidate defect.
- Odoo.sh branch rebuild `36523471` was requested while the platform mirror
  still pointed at `93fee1f3`; it repeated the already classified stale-head
  failure and is not qualification evidence for the corrected candidate.
- After the delayed branch-event queue caught up, exact-head Odoo.sh build
  `36524471` tested `c6b990f7` and exposed five additional stale qualification
  fixtures in the next module layer: one catalog journey reused the same
  InventoryItem GID for distinct variants; two protected-surface attack
  matrices omitted the newly protected birth/snapshot fields; one option
  assertion omitted canonical `position: 0`; and a source guard matched the
  word “mutation” in recovery guidance rather than executable request logic.
  The run stopped at its five-failure ceiling after 1,403 tests.
- Correction `79fff864` makes fixture InventoryItem identity unique per
  variant, exercises every new protected field through create/alter/clear
  denials, asserts the canonical option position, and preserves recovery
  guidance using remote-operation terminology. Production synchronization and
  mutation-safety behavior are unchanged. Compile, XML parse, forbidden-token,
  and diff checks pass locally. Independent Luna review: PASS, no actionable
  finding. Native rerun remains required.
- Exact-head Odoo.sh build `36525283` tested `119debd8` and reached 1,547
  tests before reporting two failures and three errors in the next layer.
  The failures were frozen elevation budgets that had not recorded two
  reviewed product-export seam elevations and one create-finalization
  elevation. The errors were stale fixtures: a Reviewer attempted the new
  Administrator-only inventory recovery, two mappings reused the same
  store/Odoo-location identity, and a replay reused an importer-mutated fake
  response instead of a fresh HTTP decode.
- Correction `6d277208` uses an Administrator for the recovery race, gives
  the second mapping a distinct real internal location, deep-copies the fake
  response for each request, and documents/locks the reviewed `sudo()` budgets
  at seams `2` and service `22`. Production authorization, uniqueness,
  pagination, and elevation behavior remain unchanged. Compile, exact sudo
  count, and diff checks pass locally. Independent Luna review: PASS; its sole
  non-blocking wording nit was corrected. Native rerun is required.
- Exact-head Odoo.sh build `36526292` tested published head `354d45c3` and
  reached the inventory trigger layer with only two failures. Both stale-parent
  tests correctly observed fail-closed admission and dispatch, but then
  incorrectly expected parent reactivation to create a second job while the
  original `blocked_manual_review` intent still owned the pair scope.
- Correction `8a6b5983` invalidates the TransactionCase relation cache before
  proving the repaired parent is operationally eligible, proves duplicate
  admission remains coalesced, and resolves the same blocked intent through an
  explicit Connector Administrator back to `queued`. Production inventory
  code is unchanged. Compile and diff checks pass; independent Luna review:
  PASS, with no actionable finding. Native rerun is required.
- Exact-head Odoo.sh build `36528250` tested published head `32791038` and
  stopped at its five-error ceiling after 1,762 tests (zero failures). Two
  repeated scan fixtures omitted production's per-run UUID payload identity;
  the broad cache invalidation flushed their duplicate durable idempotency
  keys. Three mapping tests still expected Operator configuration mutation
  after the accepted role contract made mapping create/update and push-enable
  changes Administrator-only.
- Correction `130db2b1` replaces the global cache flushes with targeted parent
  status invalidation, gives direct scan fixtures the same fresh payload hash
  as `run_inventory_push_scan()`, proves Operator denial leaves mapping state
  unchanged, and runs mapping configuration/validation positives as an
  explicit Connector Administrator. Production code is unchanged. Compile and
  diff checks pass; independent Luna reviews: PASS for scan identity/cache and
  PASS for the complete mapping-role call matrix. Native rerun is required.
- Exact-head Odoo.sh build `36528980` tested published head `1dcd16be` and
  passed the product, export, and inventory layers before exposing one failure
  and four errors in inventory UI, sale manifest, and fulfillment UI contract
  tests. The production boundaries were already correct: the failing fixtures
  logged an Administrator into a Connector User absence tour, froze the prior
  sale module version, and attempted to create/build the now
  Administrator-only fulfillment review-release wizard as Connector User.
- The pending native-qualification correction gives the absence tour a real
  Connector User while retaining the Administrator positive fixture, records
  sale version `19.0.2.11.0`, proves User denial at the fulfillment wizard ACL
  plus Administrator delegation to the sanctioned domain refusal, and treats
  both privileged fulfillment wizards as Administrator-only rendered views.
  Production code remains unchanged. Compile and diff checks pass; independent
  review and exact-head native rerun are required before acceptance.

| Gate/evidence | Status at ledger creation | Required closure |
|---|---|---|
| Exact candidate head/tree | Recorded above; clean exact-head worktree | Re-record if candidate advances |
| Focused automated tests | Python compile, XML parse, diff check, and suite-runner fail-closed self-tests pass locally; no local Odoo/PostgreSQL runtime is installed | Runtime product, inventory, order, fulfillment, security, UX tests pass in exact-head CI/Odoo.sh |
| Full connector suite | Not rerun | Zero failures/errors on exact candidate |
| Independent Luna review | Security, product, and inventory correction stacks passed; holistic integrated code review at `075e303` (tree `23a8491`) passed with no remaining actionable finding | Recheck only if runtime qualification requires a material code correction |
| Actions/Odoo.sh | Historical exact-head success recorded above | Re-run at final integrated HEAD and module upgrade |
| Product live proof | Seed import defect and unconfirmed preview documented | Corrected import/update/create recovery verified in Shopify dev store |
| Inventory live proof | No initial level binding; first push unreachable | Pair creation → preview → confirmation → activation/set → repeat/CAS/retry/reconcile |
| Order/fulfillment live proof | Unproved | Real prefixed order, delivery, fulfillment, tracking, partial/backorder, cancellation, Mode 1/2 |
| Permission matrix | Partial live observation only | No Access/User/Admin menus, URLs, RPC, ACL/rules, config, confirmation, recovery, companies |
| Upgrade safety | Unproved for repair | Upgrade with legacy rows/jobs/attempts, missing identity, repeat upgrade, no unintended Shopify mutation |
| Next UAT | Not ready yet | Product and inventory chain must pass before order/fulfillment UAT |

For each live record, append Odoo IDs, Shopify GIDs, job/preview/attempt IDs,
before/after values, role/company/store, verified remote outcome, retry/replay
evidence, and cleanup status. Never record a dispatched job as a successful
Shopify mutation without a verified remote read.
