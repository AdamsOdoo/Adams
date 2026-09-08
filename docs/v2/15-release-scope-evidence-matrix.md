# V2 release scope, reuse and journey evidence

> Historical review snapshot. The user subsequently authorized development on 8 September; current execution authority and sequence are in `16-delivery-blueprint.md` and the handoff. UI design is now parked by the user. Baseline failures below are historical evidence, not post-correction results.

Status: proposed; read with `14-rebaseline-decision.md`. Source baseline: `1c75c10288477b3a902193797360badc9d2aa06a`. Last code source: `880e70088922eb10dd44426678d578ee4ee7a73a`. Inspection: 7 September 2026 UTC / 8 September UAE.

This is the proposed release contract and evidence map, not a second current-status ledger. Changing state belongs in `13-continuous-execution-handoff.md`; attach exact evidence to the corresponding rows as work is qualified. All statuses below describe this inspected baseline.

## Reuse decisions

Paths below are relative to the repository. `addons/` prefixes are omitted in addon-family rows.

| Component | Purpose / current path | Implementation and evidence | Known weakness | Recommendation |
|---|---|---|---|---|
| Core identity, credentials, company security | `shopify_connector_core/models/`, `security/` | Existing V1 services plus V2 generation/role contracts; sampled source and CI | Broad native campaign red; settings/lifecycle coupling and limited-user access require correction | Retain identifiers, write-only secrets and authority checks; refactor only conflicting orchestration |
| P15 setup/lifecycle/settings | Core `shopify_connector_p15_*.py`, `shopify_connector_store*.py` | Substantial implementation; source and failing ORM tests inspected | Active-state contract collides with legacy fixtures/paths; current dev settings unknown | Refactor transition/admission contract and migration defaults; preserve fail-closed behavior |
| Shared transport | Core `shopify_connector_api_client_v2_runtime.py`, integration contracts | V2 transport and 48 registered GraphQL documents; policy validation green | Native transport/version-registry assertions red; commercial credential flow not live-qualified | Retain boundary; centralize version, cost and three error layers |
| Durable jobs/runs/attempts | Core `shopify_connector_v2_runtime*.py`, run/attempt models | Substantial code, dependency-free tests, independent-connection tests | Run-name sanitization blocks ORM execution; native gate red | Retain evidence model and locking adapters; remove redundant paths only with regression proof |
| P10 claim/locks/scans | Core `runtime/p10_repository_locks.py`, `shopify_connector_job_v2_claim_fence.py`; product `shopify_connector_product_scan_p10.py` | Published fixes for lock order, binding, stale handler and checkpoints inspected | Real race tests not qualified because setup fails | Retain; fix blocker and run existing database regressions |
| Recovery/attention | Core recovery commands and stale-owner sweep | Existing runtime/UI actions and tests | Translation context collision; unsupported ORM ordering; residual authorization failures | Targeted replacement of defective internals; preserve uncertainty/readback and audit semantics |
| Product/variant import | `shopify_connector_product` | Existing imports/bindings and real P10 scan implementation | Matching/refresh/UI journey not qualified on this source | Retain domain normalization and deterministic bindings; finish U3 |
| Customer/order intake | `shopify_connector_sale` | Existing customer/order/payment/totals policies and tests | Full native suite red; final integrated merchant loop not proven | Retain commercial policies; verify duplicate and ambiguous-total holds |
| Catalog export/media | `shopify_connector_product_export` | V1 export behavior, previews and V2 provider seams | P13 runtime/production journey unfinished or unqualified | Complete bounded runtime integration; preserve field ownership and media lifecycle |
| Inventory | `shopify_connector_inventory` | V1 mappings/first-push/CAS policies and V2 seams | P12 runtime integration and load/live evidence pending | Complete integration; retain authority transfer and drift safeguards |
| Fulfillment/tracking | `shopify_connector_fulfillment` | V1 operating modes, binding/notification policies and V2 seams | P14 integration and uncertainty/canary proof pending | Complete last mutation cutover; preserve location/line eligibility and no-blind-replay rule |
| Webhook foundation | `shopify_connector_webhook` | Existing receipts/signature/dedup/backstop and V2 subscription dispatch | Current end-to-end delivery/recovery proof incomplete | Retain durable receipt and raw-body verification; test delayed/missed/out-of-order parity |
| Four webhook bridges | `shopify_connector_{product,sale,inventory,fulfillment}_webhook` | Existing optional integration addons | Product bridge migration assumes export-owned column | Retain names/dependencies; repair ownership and install/uninstall combinations |
| Lite/Full packaging | `shopify_connector_lite`, `shopify_connector_full` | Full fresh install passes; Lite fails in current CI | Optional-schema install defect; release archive not qualified | Retain package distinction; fix actual combinations before packaging |
| Native/Owl UI | Core `static/src/`, manifests; `docs/09-ui-prototype/` | Legacy surfaces enabled in manifests; substantial V2/P16 source is inert | Complete journeys, responsiveness, RTL, roles and accessibility pending | Reuse native lists/forms and useful components; wire slice by slice after backend proof |
| Research, ADRs and tests | `docs/00-source-materials` through `docs/v2`; addon tests; workflows | Extensive reusable historical evidence; 448 cheap tests/48 documents green | Stale phase/status text; static checks cannot prove ORM; duplicate expensive CI triggers | Retain relevant evidence; consolidate instructions and use affected gates |
| Advanced commercial extensions | Historical roadmap / rejected alternatives | Proposals/vendor claims, not this release contract | Would expand auth, accounting and qualification cost | Defer refunds/returns automation, payouts, Markets, subscriptions, B2B, billing and speculative infrastructure |

## Implementation is not qualification

Enabled means referenced by source/module assets, not verified configuration in a running merchant database. Runtime-tested records actual evidence, including failures. “Unverified” never means absent. No component receives current release qualification from this review.

| Component | Implemented | Enabled | Runtime-tested on current code | Live-verified on current code | Release-qualified |
|---|---|---|---|---|---|
| Core identity/security | Substantial | Module paths present; deployment unknown | Exercised; suite red | Not established | No |
| P15 lifecycle/settings | Substantial | Python integrated; UI partly inert | Exercised; failures | Not established | No |
| Transport/operation registry | Substantial | Source paths present | Policy green; native failures remain | Not established | No |
| Runtime/runs/attempts | Substantial | Source present; store modes unknown | Exercised; run creation fails | Not established | No |
| P10 fixes | Present and published | Registered source paths; live mode unknown | New database tests blocked in setup | Not established | No |
| Recovery/attention | Substantial | Backend paths present | Exercised; failures | Not established | No |
| Product import | Existing domain plus P10 | Legacy manifests; live mode unknown | Current broad suite red | Not established | No |
| Customer/order import | Existing domain | Legacy module; live mode unknown | Current broad suite red | Not established | No |
| Product export/media | Existing V1; V2 incomplete | Legacy module; V2 modes unknown | Current acceptance incomplete | Not established | No |
| Inventory | Existing V1; V2 incomplete | Legacy module; V2 modes unknown | Current acceptance incomplete | Not established | No |
| Fulfillment | Existing V1; V2 incomplete | Legacy module; V2 modes unknown | Current acceptance incomplete | Not established | No |
| Webhooks and bridges | Substantial | Module-dependent | Broad suite red; Lite hook failure | Not established | No |
| Lite / Full | Present | Installable declarations | Lite fail / Full install pass | Not established | No |
| V2/P16 UI | Partial/substantial scaffolding | Unmanifested/inert | Complete production journeys not passed | Not established | No |

## Complete supported release and U1–U14

All fourteen journeys remain required. Every row needs backend business effects and browser evidence, plus appropriate blocking/recovery cases. Historical results and mocks inform development; live readback is recorded separately. The current baseline has no accepted complete U1–U14 campaign. Current status for all rows: **open, unqualified**.

| Journey | Release behavior | Ownership / principal dependencies | Required evidence to close |
|---|---|---|---|
| U1 First store | Secure credential entry; exact shop/version/scope checks; save/resume; defaults/mapping; truthful readiness and activation | Core/P15, credential service, settings and UI | Invalid token/shop/scope, stale configuration, no draft effects, keyboard/mobile setup; live identity/refresh proof |
| U2 Additional stores/companies | Independent settings, credentials, mapping, bindings, checkpoints and all-store overview; cap ten | Core/security, all domains | Two stores in one company plus another permitted company in native fixtures; forged IDs/RPC/count leakage denied; distinguish fake-ledger multi-store proof from single authorized live shop |
| U3 Catalog intake | Bounded product/variant/image import; exact matching; ambiguity resolution; update/deletion representation and missed-event repair | Product, P10, matching UI | Pagination/checkpoint overlap, duplicate delivery, ambiguous SKU/barcode, protected fields and resume; visible bindings/results |
| U4 Catalog publication | Link versus first publication/update; explicit field ownership; fresh preview; safe variants and required media | Product export/P13, transport, durable attempts | Stale preview rejected; remote GIDs/readback; partial userErrors; timeout-after-success; media readiness/ownership; no indiscriminate deletion |
| U5 Customer/orders | Customer/address matching; explicit currency, taxes, totals, discounts, shipping, tips and payment/default policies; duplicate prevention | Sale, product/customer bindings, defaults | Webhook/schedule overlap creates exactly one intended order; supported pending/paid/test/manual-gateway cases; cancellation/refund/composition ambiguity held without unsafe rewrites |
| U6 Inventory | Exact mappings; initial baseline/preview/Administrator approval; Odoo-authoritative reservation-aware sync; drift reconciliation | Inventory/P12, claims, attempts | Stale quantity/mapping invalidation, compare-and-set, coalescing, throttle/readback, first-push role denial and fault/load/canary gate |
| U7 Fulfillment/tracking | Accepted operating modes, full/partial pickings and backorders, eligible FulfillmentOrder/location/lines, explicit notification policy | Fulfillment/P14, sale/stock mappings, attempts | Create/tracking readback, already fulfilled/no-op, ineligible/changed lines, timeout/worker death and duplicate prevention; notifications disabled in test fixtures |
| U8 Trigger parity | Manual/scheduled/webhook/applicable Odoo-event intents share authority and execution semantics | Shared admission and domain bridges | Duplicate/delayed/missed/out-of-order events; fair dispatch; scheduled repair; one business effect across overlapping triggers |
| U9 Safe recovery | Bounded retry, cancellation, auth/scope repair and uncertain-outcome verification | Core recovery, attempts, all mutation domains | Before/after-send timeouts, worker death, restart, applied/not-applied/inconclusive readback; no replay while uncertain; reachable manual resolution |
| U10 Daily operations | Overview → Needs Attention → exact action → truthful run → affected Odoo record | Read facades, Owl/native views, counters | Action permission and real state change; loading/empty/degraded/stale/partial/manual-review states; usable impact/next action; timed refresh and task identification |
| U11 Lifecycle | Rotation, drift, workflow/store pause/resume, safe disconnect/reconnect/retire with preserved history | Core/P15, generations, subscription/runtime ownership | Queued/in-flight lifecycle races, no unsafe retargeting, no false disconnected state, no secret return and no orphan side effects |
| U12 Roles/isolation | Administrator/User UX plus Operator/Reviewer/Auditor capability and no-access tests | ACL/rules/public RPC, every facade/action | Native views, direct URLs/RPC, counters/search/suggestions, company switching and field redaction; exact authority on actual protected fields |
| U13 Lifecycle of modules/data | Fresh install; warm update; supported real migration; restart; backfill interruption; optional uninstall/reinstall; restore/rollback | All manifests/migrations, runtime and packaging | Lite/Full/optional combinations; actual executed migrations; independent cursors; owned dev backup/restore; preserve bindings, audit and remote-effect evidence |
| U14 Merchant loops | A: Shopify product/order → Odoo catalog/customer/order → stock/picking → Shopify fulfillment; B: approved Odoo catalog publication → stock sync → Shopify order → A | All accepted slices and final candidate | Both complete loops on one frozen candidate, independent remote readback, visible records/progress/recovery, two-store fixture repeat and one injected recoverable mid-loop fault |

The older 36-scenario plan must be linked into these rows by existing scenario IDs during qualification, not executed as a duplicate full campaign. No mapping was fabricated in this session.

## Boundaries and acceptance

Distribution remains an Odoo module with merchant-controlled Shopify app credentials. Client credentials must meet Shopify's actual app/store organization ownership rule. Customer-facing Administrator/User choices remain; internal capability groups and IDs survive. Odoo.sh is the first qualification environment. Do not advertise Odoo Online or untested hosting/version combinations.

Retain existing supported limits pending measured evidence: ten stores/database, 100,000 products/store, 100 variants/product, 100,000 orders in the supported window, 100,000 inventory pairs and fulfillment bindings/store. These are connector boundaries even where Shopify permits higher limits. Existing retention/readiness settings remain subject to security and load checks. The blueprint's 20-store stress profile must be labeled an overload/rejection test or explicitly revised; it does not silently expand ten-store support.

Preserve installation/data compatibility by default. Actual customer footprint is unknown because current development builds are dropped. Fresh and warm installations are always required; any narrowing of historical upgrade combinations needs an evidence-based, approved matrix. Later schema contraction is not required to erase compatibility evidence for this release.

Excluded extensions do not remove core safety behavior: refund evidence can require a hold without automatic accounting; independent stores still require company isolation; media support still requires safe ownership; unsupported currencies or product shapes must fail clearly rather than corrupt data.

Release-ready means every supported row passes its complete scenarios on the frozen candidate, required CI/native/browser/live/load/migration evidence is linked, no critical/high defect remains, moderated usability and sequential canaries pass, and setup/security/operations/rollback documentation and Odoo Apps archive match reality. Production promotion/public publication require separate final authorization.

## Evidence record to use per journey

Record: journey/scenario ID; source SHA and executable tree; Odoo/Python/PostgreSQL versions; build/database/company/shop alias; actual command or browser steps; fixture ownership and load profile; expected effects; actual local/remote readback; failures/skips; artifact links; cleanup/compensation; relevant-delta decision. Never record credentials or customer payloads. A changed candidate reopens affected checks and downstream dependencies.

Sources: [canonical U1–U14 and release contract](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/v2/09-test-observability-release-blueprint.md), [supported V1 business boundaries](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/release/v1-supported-scope.md), [V2 product experience](https://github.com/AdamsOdoo/Adams/blob/1c75c10288477b3a902193797360badc9d2aa06a/docs/v2/01-product-experience.md), [current failed full gate](https://github.com/AdamsOdoo/Adams/actions/runs/33449240525), [current policy gate](https://github.com/AdamsOdoo/Adams/actions/runs/33449240501).
