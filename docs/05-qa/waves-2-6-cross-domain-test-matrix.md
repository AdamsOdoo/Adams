# Waves 2–6 Cross-Domain Test Matrix

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** This matrix extends the existing
> [`domain-e2e-test-matrix.md`](./domain-e2e-test-matrix.md) and
> [`data-integrity-idempotency-test-plan.md`](./data-integrity-idempotency-test-plan.md)
> to the remaining MVP program waves (2–6), consuming the new canonical
> product/architecture documents of the 2026-07-16 gap-closure mission. It
> reuses the accepted vocabulary verbatim: 7 job sources, 10 job states, the
> fixed 16 error classes (no 17th), the 6 manual-review sub-reasons, and the
> 4 retry UI cases (see the vocabulary block of
> [`domain-e2e-test-matrix.md`](./domain-e2e-test-matrix.md)). Nothing here
> re-decides any of those. Rows referencing Proposed documents inherit that
> status — a row becomes executable only when its owning packet's wave is
> authorized.

## Test-type vocabulary (used in the "Type" column)

`unit` · `ORM-security` (ACL/record-rule/field-`groups=` assertions) ·
`source-AST-guard` (static test over source, mirroring the existing
`execute_business` guard pattern) · `install-upgrade-uninstall-reinstall`
(LC-1 lifecycle family) · `migration` (migration-script execution against a
seeded fixture DB) · `concurrency-real-PG` (real PostgreSQL 40001
serialization failure + lock-timeout injection, extending the proven Wave 1
harness) · `disconnect-reconnect` · `retry` · `uncertain-outcome` ·
`idempotency` · `duplicate-prevention` · `PII` · `residue` (zero-residue
sweep) · `credentials` · `redaction` · `permissions` (two-role ACL matrix
per [`../02-product/connector-roles-and-permissions.md`](../02-product/connector-roles-and-permissions.md) §4.9) ·
`performance` (PB rows, [`../03-architecture/performance-budgets.md`](../03-architecture/performance-budgets.md)) ·
`UI-accessibility` · `UI-state-coverage` (every mapped state renders its
badge/label per fixture).

---

## 1. Wave 2 — Order import, confirmation policy, COD import layer, backfill

Sources: [`../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../02-product/sales-order-lifecycle-and-confirmation-policy.md) (§9 UAT families),
[`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md) (§8),
[`../02-product/reconnect-catchup-backfill-policy.md`](../02-product/reconnect-catchup-backfill-policy.md) (§4.3, §5),
[`../02-product/abandoned-checkout-policy.md`](../02-product/abandoned-checkout-policy.md) (§7).

| Test family | Type | Fixture refs | Pass criteria | Owning packet |
| --- | --- | --- | --- | --- |
| Financial state × policy matrix (8 states × P1/P2/P3) | unit | one order fixture per `OrderDisplayFinancialStatus` value × policy | Every §2.1 cell of the confirmation policy produces exactly the documented result (SO / Q / Wait / Skip+review / No import); confirmation, picking existence, badge asserted per cell | Task 012 (revised) |
| Manual-gateway overlay | unit | COD `PENDING` with `manualPaymentGateway=true` on/off approved list; card `PENDING` | Approved manual gateway follows the three sub-policies; unapproved manual gateway and card `PENDING` never take the manual path; discrimination is by `manualPaymentGateway` + gateway identity, never `PENDING` alone | Task 012 (revised) |
| Financial-state transitions | unit | `PENDING→PAID`, `PENDING→EXPIRED/VOIDED`, `AUTHORIZED→PAID/EXPIRED/VOIDED` (P1 and P2), `PAID→PARTIALLY_REFUNDED/REFUNDED` | Transition table of the confirmation policy §2.3 holds; wait→confirm produces exactly one SO; post-confirmation payment loss → `blocked_manual_review`, never auto-cancel | Task 012 (revised) |
| Order-binding idempotency | idempotency / duplicate-prevention | bound-order re-scan, duplicate webhook, manual re-import | Existing `(store, shopify_order_gid)` binding always takes the update path; a second SO is structurally impossible; state refresh recorded on the binding | Task 012 |
| Order edits (`orders/edited`) | unit | edited order whose refreshed totals diverge / reconcile | Evidence refresh only — never a silent SO line/price edit; divergence routes through the total-check posture; webhook path and reconciliation path converge to the identical outcome for the same change | Task 012 (revised) |
| Cancellation staging | unit | cancel before confirm / after confirm / after partial delivery / locked SO | Auto-cancel quotation; assisted review after confirm; `blocked_manual_review` after partial delivery; locked SO surface-only | Task 012 (revised) |
| Whole-order hold + total-check guard | unit / retry | one-resolvable-one-unresolvable-line order; total-mismatch order; divergent-currency order | Whole order holds (`mapping missing` → `failed_retryable`); total-check unbypassable; divergent currency blocks before SO creation independent of the total result | Task 012 |
| COD classification + ledger snapshot at import | unit | manual-gateway transaction fixtures; `PENDING`-non-COD fixture | COD identified via `manualPaymentGateway=true`/gateway identity, never `PENDING` alone; five-value ledger snapshot created at import (PD-COD-3); `totalPriceSet` captured shop+presentment | Task 012 addendum (COD import policy, §9 of the COD doc) |
| Order catch-up scan + watermark | disconnect-reconnect / idempotency | disconnected store with orders created/edited during the gap | Scan uses `updated_at:>{watermark−overlap}`; watermark advances only on clean completion; §3.4 skip logic counts new/changed/skipped/needs-review correctly | Wave 2 catch-up (PD-RB-2/4/6) |
| Watermark overlap dedup | idempotency | records inside the 30-min overlap window re-read by a second scan | Re-read records with `updatedAt ≤` binding's last-synced version are skipped; equal payload hash short-circuits (touch-only update); zero duplicate jobs enqueued for the same observed version | Wave 2 catch-up (PD-RB-5/6) |
| Backfill preview counts | unit | fixture range with known new/changed/duplicate/skipped/needs-review composition | Read-only preview computes exactly the seeded counts using §3.4 skip logic, creating no jobs and no records; enqueue happens only after explicit confirm | Wave 2 backfill wizard (PD-RB-8) |
| 60-day boundary honesty | unit | requested range >60 days, `read_all_orders` absent vs present | Absent: wizard states the limitation before scanning, shows the reachable sub-range, links the approval path, never silently truncates; present: full range scans | Wave 2 backfill wizard |
| Backfill duplicate-safe re-run + resumability | idempotency / retry | interrupted backfill; full re-run of a completed range | Re-run/resume absorbs re-reads via dedup (zero duplicate SOs); resume starts from the last completed window; generation-fenced after reconnect (fresh preview required) | Wave 2 backfill wizard |
| Abandoned checkout default policy | unit / residue | dev-store-shaped abandoned checkout fixture; same checkout later completed | No quotation, no demand, no reservation, no accounting artifact from an abandoned checkout (PD-AC-1); the converted order imports exactly once via the normal path | Task 012 / UAT-AC-1..2 |
| Order-domain concurrency | concurrency-real-PG (40001 + lock timeout) | concurrent import of the same order from two workers | One winner via `operation_scope_key`; loser recovers per the proven `_recover_after_concurrency_conflict` path; no duplicate SO, no lost update | Task 012 |
| Order import throughput | performance | RD-1 order corpus | PB-18 (≥500 orders enumerated+enqueued/min) plus the new provisional order-import SLO rows in [`performance-slo-benchmark-plan.md`](./performance-slo-benchmark-plan.md) | Task 012 + PERF-1 |

## 2. Wave 3 — Layer 2 mutation safety + inventory sync

Sources: [`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md) (§13 test strategy),
[`../02-product/inventory-operating-model.md`](../02-product/inventory-operating-model.md) (§12 hooks).

| Test family | Type | Fixture refs | Pass criteria | Owning packet |
| --- | --- | --- | --- | --- |
| Layer 2 attempt-state machine | unit | attempt rows in each outcome (`pending`/`succeeded`/`failed_clean`/`uncertain`) | All outcome transitions of L2-D7 hold; `THROTTLED` classifies `failed_clean` (never `uncertain`); partial data+userErrors → `uncertain`; fingerprint normalization stable across key order and excludes volatile fields | Layer 2 packet (L2-D15 item 1) |
| Layer 2 crash-injection points | crash-injection (per L2-D15 item 3) | kill between each §11 commit-point pair: pre-C1, C1→C2, C2→NET, NET→C3, during C3, post-C3 | Each window's recovery matches the L2 §11 recovery table exactly: `transport_attempted=false` → safe requeue; `=true` → reconciliation, never re-execution | Layer 2 packet |
| Layer 2 40001 recovery branch | concurrency-real-PG (40001 + lock timeout) | serialization failure injected in a mutation job before vs after transport | Pre-transport → bounded `concurrency_race_conflict` re-run; post-transport → reconciliation routing; stale-owner finalize fails closed (attempt_id CAS) | Layer 2 packet (L2-D12) |
| Reconciliation-decision matrix | unit / uncertain-outcome | one fixture per §4.2 matrix row × {applied, not-applied, inconclusive} | Each mutation row's reconciliation read decides correctly; inconclusive after N=3 → `blocked_manual_review` sub-reason `duplicate_risk`; unregistered mutations fail closed | Layer 2 packet (L2-D8/D9) |
| Mutation-wrapper AST guard | source-AST-guard | full connector source tree | No GraphQL `mutation` call site exists outside the attempt wrapper — static test fails on any violation | Layer 2 packet (L2-D15 item 5) |
| Stale-owner sweep | unit / disconnect-reconnect | `running` job older than sweep timeout, transport true/false | Sweep routes per §2; sweep timeout ≥ quiescence timeout ordering respected; expiry never auto-finalizes | Layer 2 packet (L2-D3) |
| Inventory CAS conflicts | uncertain-outcome / retry | `compareQuantity` mismatch injected; repeated mismatch beyond 3 attempts | Read → compare → set flow; CAS mismatch → re-read + re-derive + bounded retry (3); persistent divergence → review case; `ignoreCompareQuantity` never used | Task 013 (revised) |
| Inventory idempotency-key replay | idempotency | duplicate attempt with same UUID inside the 24 h window; deliberate new attempt | Same key replays to cached response (no double write); new attempt uses a fresh key; key persisted on the attempt record before the call | Task 013 |
| Coalescing (last-value-wins) | unit / idempotency | burst of stock events on one (item, location) pair while a push job is active | Exactly one pending record per pair; new events overwrite the target; push consumes only the latest absolute `free_qty`; `operation_scope_key` blocks a concurrent second job | Task 013 (revised, §4.2) |
| Multi-location context pitfall | unit | multi-location fixture, mapped child location | `free_qty` computed with the explicit per-mapped-location context ≠ the all-locations aggregate; conflicting/overlapping mappings rejected at create | Task 013 |
| Inventory edge cases | unit | negative `free_qty`; unmapped item; inactive Shopify location; stale/archived variant binding | Clamp-to-0 + divergence warning; unmapped skipped with surfaced count; inactive location → mapping flagged + pushes suspended; stale binding → suspend + review | Task 013 |
| Baseline preview/confirm (first push) | unit / duplicate-prevention | mapped pair without/with confirmation record; drift between preview and apply | No write before the pair's own confirmation record exists; drift-abort per D-013B-4; confirmation record persists preview snapshot, operator, timestamp, source-of-truth decision | Task 013B |
| Inventory reconnect no-blind-push | disconnect-reconnect | reconnect with stale pre-disconnect pending targets | First post-reconnect action is a reconciliation read; pushes resume only with fresh `compareQuantity` bases; no pre-disconnect mutation replayed blind | Task 013 + Wave 3 catch-up |
| Inventory push throughput | performance | dev-store run per PB-20 | ≥300 level-pushes/hour sustained within throttle budget (PB-20) | Task 013 dev-store run |

## 3. Wave 4 — Fulfillment modes, status model, COD ↔ fulfillment interplay

Sources: [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md) (§9),
[`../02-product/shopify-fulfillment-status-model.md`](../02-product/shopify-fulfillment-status-model.md) (§10 fixtures),
[`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md) (§8).

| Test family | Type | Fixture refs | Pass criteria | Owning packet |
| --- | --- | --- | --- | --- |
| Outbound fulfillment (Mode 1 core) | unit / idempotency | eligible validated picking; backorder-split picking; tracking-only change | One fulfillment per eligible picking with explicit `lineItemsByFulfillmentOrder`; backorder split is its own event; tracking update via `fulfillmentTrackingInfoUpdate`, never a second fulfillment; `notifyCustomer` persisted at enqueue, default off (RA-009) | Task 014 (revised) |
| Partial fulfillment | unit | partial validation with backorder chain; multi-package tracking | Partial quantities fulfill exactly; each subsequent leg re-runs matching against the then-current chain; all tracking numbers captured | Task 014 (revised) |
| Uncertain outbound outcome | uncertain-outcome | timeout after `fulfillmentCreate` send | Verification read (FO remaining quantities + own-GID ledger) before any retry; adopt-if-found; inconclusive → `blocked_manual_review`; never blind retry (no `@idempotent` support — Fact, capture §6.5) | Task 014 + Layer 2 |
| Status-model state coverage | unit / UI-state-coverage | the 56 named fixtures of the status model §10 (`order_sum_*`, `fo_*`, `fo_req_*`, `fo_hold_*`, `ful_*`, `evt_*`, `dep_*`, `unknown_*`) | Raw value persisted verbatim; label/badge/severity per table row; permitted/blocked actions enforced; deprecated values normalized with legacy tooltip | Task 014 (revised) |
| Unknown Shopify states | unit | `unknown_*` fixtures (one per enum family) | All five §7 contract points: raw preserved; displayed unknown; never interpreted as success; unsafe automation halted; actionable schema warning raised | Task 014 (revised) |
| Shopify API-version change (falls-forward guard) | unit | mirrored `api_version` ≠ pinned 2026-07; fall-forward observed mid-attempt | Readiness check flags the mismatch (reconnect step 3); a version fall-forward observed mid-attempt classifies the attempt `uncertain` (L2 §10); no silent continuation on an unpinned version | Task 014 / Layer 2 / core readiness |
| External-fulfillment origin classification | unit | own-GID-ledger hit; `service.handle=manual`; service handle; event attribution; none-resolve | Evidence stack strongest-first; own-GID ledger authoritative; unresolvable → `external` (unknown origin), never assumed connector-created; class 4 (`carrier_event_only`) never touches stock | Task 014 (revised, modes §3) |
| Mode 2 exact-conditions checklist | unit | one pass fixture + 16 single-violation fixtures (one per condition) | Full pass → deterministic auto-validate; each individually violated condition stops evaluation with its named review reason and zero stock change (see [`fulfillment-mode-uat-matrix.md`](./fulfillment-mode-uat-matrix.md)) | Mode 2 packet (Wave 5 / Wave 4 stretch) |
| Deterministic picking selection + split | unit | exact-match picking; covering-with-surplus picking; two-candidate ambiguity; cross-location FO decomposition | §4.1 algorithm: exact → whole validate; surplus → deterministic split + native backorder (never the `ask` wizard); any allocation choice → `picking_ambiguous` | Mode 2 packet |
| Lots/serials | unit | tracked product with fully-reserved deterministic lots; ambiguous lot coverage | Auto-reconcile only on exact deterministic move-line lot evidence; any lot choice → `lot_serial_ambiguous` review | Mode 2 packet |
| Mode switching | unit / idempotency | switch 1→2 with unresolved externals; rollback 2→1; retried switch job; re-confirm current mode | Never replays history; pre-existing externals stay review cases; scan is read-only; switch idempotent (per-run nonce); rollback stops future auto-apply without touching evidence/bindings/audit | Mode 2 packet (modes §6) |
| Carrier-Delivered inconsistency | unit | `evt_delivered` with Odoo picking not `done` | Milestone never validates stock; high-visibility critical review case raised per status model §8 | Task 014 (revised) |
| COD three-dimension state derivation | unit | fixtures per COD §2 state, all three dimensions | Each state derives from Odoo/Shopify facts; no dimension collapses another (PD-COD-1) | Wave 4 COD interplay |
| COD ledger computation | unit | scenarios 1, 8–13, 15 quantity/event fixtures | Five values correct from move quantities + append-only events; `to_refund` return subtraction; negative raw outstanding → discrepancy | Wave 4 COD interplay |
| COD stock-restoration guard | unit | courier RTO claim; validated return picking | Stock restored only via validated return picking (PD-COD-2); courier claims never move stock; append-only collection events (corrections are compensating events) | Wave 4 COD interplay |
| Fulfillment catch-up | disconnect-reconnect | external fulfillments created while disconnected (both modes) | All gap-period externals land as review cases even in Mode 2; no blind `fulfillmentCreate` replay; FO remaining quantities re-read before any queued outbound executes | Wave 4 catch-up |

## 4. Wave 5 — Product export, roles migration, UI

Sources: [`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md) (§14),
[`../02-product/connector-roles-and-permissions.md`](../02-product/connector-roles-and-permissions.md) (§4.9),
[`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md) (§7).

| Test family | Type | Fixture refs | Pass criteria | Owning packet |
| --- | --- | --- | --- | --- |
| Export allowlist fidelity | unit / source-AST-guard | full-field template export payload | Nothing beyond the D-015-2 allowlist appears in any `productSet` input; `collections`/`metafields` list inputs never supplied; price fields omitted unless `odoo_authoritative` | Task 015 |
| Destructive-write guard (variants) | unit / duplicate-prevention | payload omitting a bound remote variant; confirmed vs unconfirmed deletion set | Complete desired variant list always sent or job fails closed; any remote variant deletion not enumerated in the confirmed preview → `destructive_write_guard_blocked` | Task 015 |
| Changed-since-read gate | unit | remote `updatedAt` moved between preview and apply; Odoo `write_date` moved; 24 h preview expiry | Apply aborts to fresh-preview requirement on either staleness direction; no blind overwrite | Task 015 |
| Create-path upsert + duplicate gate | idempotency / duplicate-prevention | replayed create with same `customId`; pre-existing SKU collision | Replayed create converges on one product; SKU hit → `duplicate_risk` review, never blind create | Task 015 |
| Media pipeline | unit / idempotency | staged upload → `fileCreate` → READY; unchanged checksum; merchant media present | READY-gated association; checksum no-op idempotency; detach-only for proven-own media; merchant media never deleted; never imageless mid-replacement | Task 015B |
| Export uncertainty (Layer 2) | uncertain-outcome | ambiguous `productSet` outcome | Attempt record before call; reconciliation read by identifier; adopt / review / safe-retry per outcome; no blind retry path exists | Task 015 + Layer 2 |
| Export reconnect reconciliation | disconnect-reconnect | reconnect with remotely deleted / diverged / intact bound products | Exports blocked until the pass completes; deleted → review (never silent re-create); diverged → flagged for next preview | Task 015 (PD-PX-7) |
| Two-role ACL matrix | permissions / ORM-security | test users: user-only, admin-only, auditor-only, legacy operator-only, legacy reviewer-only × every connector model | Exact CRUD outcomes match roles doc §4.5 target table; server-side gates hold even with hidden groups manually assigned; credentials and unmasked PII denied to User by default | SEC-2 packet |
| Role migration idempotency | migration / idempotency | fixture DB seeded with operator/reviewer/admin/auditor users; script run twice | Identical final membership both runs; operator∪reviewer gain `group_..._user`; old memberships retained; per-user audit log lines emitted | SEC-2 packet (roles §4.7/§4.9) |
| No-privilege-escalation | permissions | migrated legacy Operator user | Gains exactly reviewer-tier acts; credentials/settings/destructive overrides still denied; implication closure exact (admin → 5 groups, user → 4) | SEC-2 packet |
| PII field-level gating | PII / ORM-security | User default; Administrator toggle granted | Masked compute for User; unmasked only via the hidden PII group; `fields_get` omission verified for non-members | SEC-2 packet |
| Lifecycle | install-upgrade-uninstall-reinstall | fresh install; upgrade with new group data; uninstall; reinstall | LC-1 family green across all new Wave 2–5 models; group/ACL data survives upgrade; uninstall leaves zero orphans; reinstall clean | LC-1 extension per wave |
| `orderMarkAsPaid` gating | unit / uncertain-outcome | fully-collected + policy on; partial collection; open discrepancy; already-`PAID` remote | Eligible only on fully-collected + Administrator policy + no discrepancy (rule L-3); Layer 2 pre-read skips if `PAID`; blocked cases produce no call | Wave 5+ COD packet |
| UI state coverage + accessibility | UI-state-coverage / UI-accessibility | dashboard/sync-center/review screens across fixture states | Every mapped badge/severity renders; one badge per concept; color never the only signal; PB-1..8 interactive budgets measured | Wave 5 UI packets |

## 5. Wave 6 — Cross-cutting release families

| Test family | Type | Fixture refs | Pass criteria | Owning packet |
| --- | --- | --- | --- | --- |
| Full-suite continuous execution | all unit suites | complete corpus | One reproducible session, `0 failed / 0 errors`, covering every implemented domain (acceptance-matrix row 21) | Wave 6 |
| Redaction / credential leak scan | redaction / credentials | full log corpus after all UAT runs | No token, secret, or PII in any log/job record; `_system_append` redaction holds across the new domains | Wave 6 (per [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)) |
| Residue sweeps | residue | disconnect, uninstall, backfill abort, mode switch abort | Zero orphan records/crons/attachments after each abort/teardown path | Wave 6 |
| PII surface matrix execution | PII / permissions | per [`security-pii-matrix-waves-2-6.md`](./security-pii-matrix-waves-2-6.md) | Every surface row's required tests pass | Wave 6 |
| Performance/SLO benchmark run | performance | per [`performance-slo-benchmark-plan.md`](./performance-slo-benchmark-plan.md) | Every PB row measured or explicitly waived; provisional rows calibrated by PERF-1 | PERF-1 + Wave 6 |
| Dev-store UAT execution | UAT | [`cod-uat-matrix.md`](./cod-uat-matrix.md), [`fulfillment-mode-uat-matrix.md`](./fulfillment-mode-uat-matrix.md), [`reconnect-backfill-uat-matrix.md`](./reconnect-backfill-uat-matrix.md) | All UAT cases pass on the dev store (acceptance-matrix row 22; VAL-B2 first) | Wave 6 |

---

[Inference] Coverage check against the mission brief: partial fulfillment
(§3), COD (§1/§3/§4), cancellation (§1), backorders (§1/§3), lots/serials
(§3), multi-location (§2/§3), unknown Shopify states (§3), API-version
falls-forward guard (§3), order edits (§1), CAS conflicts (§2), coalescing
(§2), watermark overlap dedup (§1), backfill preview counts (§1), Layer 2
attempt-state machine + crash-injection (§2), mode switching (§3),
external-fulfillment origin classification (§3), role migration idempotency
(§4) — all present. [Open question] Exact test file names are assigned by
each wave's implementation packet, not here (consistent with the acceptance
matrix's note on "new" test types).
