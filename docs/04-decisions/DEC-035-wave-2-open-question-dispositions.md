# DEC-035 — Wave 2 Open-Question Dispositions (Order Import / Area-6 Order-Scan)

- **Status:** Accepted by Claude control room, 2026-07-17.
- **Decision owner:** Claude control room under DEC-032 / CLAUDE.md §13 (MVP
  Program Control-Room addendum), exercising the same product/architecture
  decision-acceptance authority already exercised in the PR #173 control-room
  session (`fable-proposed-decision-pack.md` §Control-room decisions
  2026-07-17; AR-053) — this record follows that established precedent, not a
  new grant of authority.
- **Scope:** closes every remaining Wave 2 open question named in the Wave 2
  gate-preflight task, plus two additional questions this session's
  exact-codebase preflight discovered that no existing document had raised.
  Docs-only; authorizes no code.
- **Related:** [`wave-2-definition-of-ready.md`](../07-implementation-plan/wave-2-definition-of-ready.md),
  [`task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md),
  [`task-012-order-import-decision-closure.md`](../03-architecture/task-012-order-import-decision-closure.md),
  [`area-6-sync-triggers-implementation-packet.md`](../07-implementation-plan/area-6-sync-triggers-implementation-packet.md),
  [`sales-order-lifecycle-and-confirmation-policy.md`](../02-product/sales-order-lifecycle-and-confirmation-policy.md),
  [`cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md),
  [`reconnect-catchup-backfill-policy.md`](../02-product/reconnect-catchup-backfill-policy.md),
  DEC-034 (binding-extension contract), DEC-020 (divergent-currency routing).

## Method

Every disposition below was produced by reconciling the question's source
document against the **actual current code** in `addons/shopify_connector_core`,
`addons/shopify_connector_product`, and `addons/shopify_connector_sale` at
`mvp/program-integration` SHA `a34c68e84aada288dad3dc22a6afe94f5ace0652`, not
by restating the source document's own framing. Where a question required a
time-sensitive Shopify API fact, current official `shopify.dev` documentation
was fetched live on 2026-07-17 (cited inline; see `shopifyOfficial` findings
below) rather than answered from model knowledge.

---

## Table — every disposition

| # | Question | Source | Disposition | Fail-closed behavior | Vocabulary used | Blocks Wave 2? |
|---|---|---|---|---|---|---|
| 1 | OQ-A — null `displayFinancialStatus` at initial import | lifecycle policy §10 | **Fail closed at import**, consistent with the packet's own established precedent for a different nullable financial field (nullable `totalTaxSet` → `data_shape_schema_mismatch`, closure §6.0.1, round-8). Null/missing order-level financial status → `data_shape_schema_mismatch`, no SO, no binding, `failed_final` (a blind retry cannot produce different Shopify data). | No SO/binding created; job-log records the exact Shopify order GID and the null field. | **Existing** — `data_shape_schema_mismatch` (already in `ERROR_CLASS_SELECTION`) | No |
| 2 | OQ-A — post-confirmation payment loss (evidence regresses after a SO is already confirmed) | lifecycle policy §10 | **Not an error at all.** Governed by the packet's already-decided post-import refresh rule (D-012-12): evidence-refresh only — update binding snapshots + one `event_type='note'` job-log row; **zero writes to the SO or its lines**, SO is never auto-cancelled (DEC-014 §J). Operator follow-up is an Error-Center (UI-phase) concern, not a Wave-2 mechanism. | Snapshot updates only; no state transition. | **Existing** — `event_type='note'` (already in `shopify.connector.job.log.event_type`) | No |
| 3 | OQ-B — optional early quotation for card-`PENDING` under P1/P2 | lifecycle policy §10, §2.1 | **Post-MVP.** Wave 2 does not create an early quotation for a card-`PENDING` order under P1/P2; the order simply waits per `pending_wait_expiry` (PD-B1) until PAID or expiry. | N/A — no new behavior introduced. | N/A | No |
| 4 | OQ-C — `pending_wait_expiry` duration | lifecycle policy §10 | **Already resolved** by PD-B1 (2026-07-17, PR #173): per-store default 24 h, min 1 h, max 7 d. Removed from the open-question list; not re-litigated here. | N/A | N/A | No — closed |
| 5 | OQ-D — mixed/multiple transactions on one order (e.g. part gift-card, part manual gateway; conflicting `kind`/`status`/`gateway`) | lifecycle policy §10, §9 | **Fail closed to review, using existing vocabulary only — no new selection value.** A fresh official-Shopify-evidence check (below) confirms Shopify documents no arbitration algorithm for reducing multiple disagreeing transactions to one authoritative status, and that Shopify's own schema reserves `OrderTransactionStatus.UNKNOWN` as a legitimate outcome — "cannot classify" is a state Shopify's own model anticipates, not a gap the connector must paper over. When the order's transaction evidence cannot be classified exactly (payment authority ambiguous — e.g. `paymentGatewayNames` mixes a real gateway with a manual/COD entry with no single dominant `manualPaymentGateway` signal, or transaction `status` values conflict), the importer **still creates the order binding and the SO** (the import itself did not fail — Shopify gave us real, if ambiguous, data), but: (a) the binding's own `status` field (already `active`/`stale`/`manually_overridden`/`review` on the core binding mixin) is set to **`review`** instead of `active`; (b) the SO is created in `draft` regardless of the store's configured `order_confirmation_policy` — ambiguous evidence is never auto-confirmed by any policy, matching the task's own instruction "never auto-confirm by looking only at the order-level PENDING state"; (c) one job-log note records the exact conflicting transaction evidence (kind/status/gateway per transaction, redacted per the existing PII/redaction discipline). A future Error-Center UI (Wave 5+) surfaces `status='review'` bindings for operator action — no new mechanism is required for that; the binding mixin's `action_override_binding()` (already SEC-1-protected) is already the sanctioned resolution path. | Order imports but never auto-confirms; binding flagged `review`; job still `succeeded` (import correctness ≠ confirmation trust). | **Existing** — `binding.status = 'review'` (already in the core mixin's `status` Selection) | No |
| 6 | OQ-E — `orderMarkAsPaid` / `orderCreateManualPayment` | lifecycle policy §10; COD doc §6 | **Out of Wave 2 entirely** — Wave 2 performs zero Shopify mutations of any kind. Deferred to the COD/accounting mutation gate that COD doc §6 already names ("gated as a DEC-031 Layer 2 replay-safe mutation"), itself downstream of the still-unaccepted DEC-031 Layer 2 pre-Wave-3 gate. Does not block Wave 2. | N/A | N/A | No |
| 7 | OQ-COD-6 — currency policy for collection events on presentment≠shop-currency stores | COD doc §11 | **Non-blocking for Wave 2 by construction.** DEC-020's divergent-currency routing (already decision-closed, Task 012 §10/closure §10) sends any order where `presentmentCurrencyCode != currencyCode` straight to a terminal `skipped` state **before any SO or order binding is created** — such an order never reaches the COD ledger-snapshot-at-import step at all in Wave 2. Genuine collection-*event* currency handling (beyond the read-only snapshot Wave 2 takes at import) is COD-collection-event scope, itself Wave 4/5 per the COD doc's own wave allocation (PD-COD-6). | No COD ledger event for a presentment≠shop-currency order can occur in Wave 2 — structurally impossible, not merely policy. | **Existing** — DEC-020's `skipped` routing | No |
| 8 | OQ-RB-1 — no official Shopify figure for query-visibility lag; 30-minute overlap default | reconnect policy §3.2, §11 | **Non-blocking engineering default**, unchanged: `overlap_window` stays a per-domain configurable default (30 min, tunable 15–60 min), validated empirically only when dev-store evidence becomes available — which is itself preferred-but-non-blocking for Wave 2 (§2.7). | N/A | N/A | No |
| 9 | OQ-RB-5 — whether `read_all_orders` approval is realistically obtainable for the current custom-app posture | reconnect policy §11 | **Non-blocking — already an honest-degradation design, not a build blocker.** Per PD-B2/PD-RB-8, any backfill range beyond current Shopify access is blocked with an exact scope explanation; `reconnect-backfill-uat-matrix.md` already records UAT-RB-3.3 as "not-executable" in that case with no waiver required. Wave 2 ships either way. | Range request beyond granted scope is refused with an explicit message, never silently truncated or silently granted. | N/A | No |
| 10 | OQ-RB-6 — full `OrderSortKeys` enum values; confirm `UPDATED_AT` exists | reconnect policy §11 | **Resolved — Fact, verified live today.** Fetched `https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderSortKeys` (Accessible, 2026-07-17): the enum's 14 documented values are `CREATED_AT`, `CURRENT_TOTAL_PRICE`, `CUSTOMER_NAME`, `DESTINATION`, `FINANCIAL_STATUS`, `FULFILLMENT_STATUS`, `ID`, `ORDER_NUMBER`, `PO_NUMBER`, `PROCESSED_AT`, `RELEVANCE`, `TOTAL_ITEMS_QUANTITY`, `TOTAL_PRICE`, **`UPDATED_AT`** ("Sorts by the date and time the order was last updated."). ARCH PD-5's `sortKey: UPDATED_AT` assumption is confirmed correct. | N/A | N/A | No — closed |
| 11 | Task 012 packet's own internal contradiction — `order_import_confirmation_policy` (no default, holds imports) vs. the 2026-07-16 addendum's `order_confirmation_policy` (`paid_only`/`paid_or_authorized`/`quotations_only`, default `paid_only`) | Task 012 packet §15 vs. addendum §A.2 | **Resolved.** PD-A and PD-E (§4.A of the Wave 2 gate task, binding through PR #173) are accepted as written, so the addendum's condition ("only if PD-A/PD-E are accepted as written") is satisfied. The addendum's field **replaces** the original field and posture entirely: the re-accepted packet defines exactly one store-settings field, `order_confirmation_policy` (Selection `paid_only`/`paid_or_authorized`/`quotations_only`, **default `paid_only`**). `order_import_confirmation_policy` (the original, no-default field) does not exist in the re-accepted contract — Sol must not implement both. | Unset is impossible (a default always applies); no readiness-hold state for "policy unset" is needed. | Addendum's field, packet's original field name retired | No — closed |
| 12 | D-012-4 — ambiguous-customer resolution flow ("flagged for explicit ChatGPT confirmation") | Task 012 packet §D-012-4 | **Confirmed as written.** Operator resolves the customer match (creating/correcting the customer binding via the already-existing Task 011 sanctioned path), then the job retries via the already-merged JOB-ACTIONS `action_manual_retry()` (Wave 1) and completes normally. No new mechanism required. | Job sits in `blocked_manual_review`/`ambiguous_match` until resolved; no partial SO exists in the meantime (whole-job hold, D-012-1). | Existing | No — closed |
| 13 | Task 012 packet — dangling "§18" cross-reference in the D-012-2 round-7 note | Task 012 packet | **Clarified, not a defect.** The referenced "§18" is the *decision-closure* document's own §18 ("Remaining dependencies and open questions"), which exists and is the authoritative home for that item's eventual empirical resolution — the packet's in-line reference was to the sibling document, not a stale self-reference. No packet edit required beyond this clarifying note. | N/A | N/A | No — closed |
| 14 | Decision-closure §18 remaining items (verbatim `THROTTLED` error-code string; 3-decimal-currency rounding; tip-tax-treatment documentation gap; EPD payment-term support; GraphQL cost measurement; `price_unit` candidate grid; `special_mode='total_excluded'` symmetry; cash-rounding-adjustment inclusion in `totalPriceSet`) | Task 012 decision closure §18 | **Carried forward unchanged — already fail-closed or explicitly deferred by the closure document itself** (each already routes to a named policy-skip error class or an explicit dev-store empirical-check obligation). This session does not reopen or weaken any of them; Sol must not treat their presence in §18 as newly blocking. | Each already fails closed per the closure document's own text. | Existing | No — closed |

---

## Two additional questions this session's exact-codebase preflight discovered

Neither of these appears in any Wave 2 planning document. Both were found by
reconciling the packets against the live code in `shopify_connector_core`,
`shopify_connector_product`, and `shopify_connector_sale`, and both are
resolved below rather than left as silent assumptions in the allowed-file
list or the locked Sol prompt.

### EQ-PF-1 — no `order_domain_enabled` settings flag exists, and core's domain-flag tuple has no extension seam

`shopify.connector.store.settings` currently defines exactly four domain
flags (`product_domain_enabled`, `sale_domain_enabled`,
`inventory_domain_enabled`, `fulfillment_domain_enabled`) — none is
order-specific — and `shopify.connector.readiness.check`'s
`_check_domain_flag_enablement` reads a **hardcoded core constant**
`ACCEPTED_DOMAIN_FLAGS = ('product_domain_enabled', 'sale_domain_enabled',
'inventory_domain_enabled', 'fulfillment_domain_enabled')` with no
extension seam of its own. Adding a fifth, order-specific flag without
touching this core tuple would leave a store with only that flag set
failing readiness with "No sync domain is enabled" — a real functional
break — while touching the tuple would require editing
`shopify_connector_core`, which is forbidden for Wave 2 (§2.3) and breaks
this program's established zero-core-edits precedent for domain modules.

**Disposition (Accepted):** Task 012's `order_import_sync` job type and
Area-6's `order_import_scan` job type both map `_domain_flag_for_job_type()`
→ **`'sale_domain_enabled'`** — the exact flag `customer_import_sync`
(Task 011) already reuses for the same reason. No new settings flag, no
core edit. A store enables order import/scan by having the same
`sale_domain_enabled` flag already governing customer import turned on.
(A future, separately-scoped decision may introduce a dedicated
order-domain flag and an extensible `ACCEPTED_DOMAIN_FLAGS` seam in core if
independent order/customer toggling becomes a real product requirement —
that is out of Wave 2's scope to invent.)

### EQ-PF-2 — no AST source-guard currently scopes the future order-domain files to `execute_business`-only

`execute()` (the legacy, non-admission, non-lease call path) remains live
and callable; nothing in core prevents a rushed implementation from using it
instead of `execute_business()` for an order-domain read, which would skip
CORE-R2's admission/lease/replay-policy protection entirely. Core's own
existing AST guard (`test_source_level_no_shopify_api_client_reference_in_changed_production_files`)
only scans `shopify_connector_job.py`/`shopify_connector_job_enqueue.py`/
`shopify_connector_job_dispatch.py` — it does not and cannot reach files in
`shopify_connector_sale` that do not exist yet.

**Disposition (Accepted — mandatory requirement, not a blocker):** Task 012
and Area-6's own implementation must add their own AST source-guard test
(mirroring the pattern already proven in
`test_product_import_matching.py::test_import_product_sync_only_issues_read_query_calls`
and the packet's own already-planned "Source-level guards (AST)" in §6)
asserting that `shopify_connector_order_importer.py` and
`shopify_connector_order_scan.py` call only `execute_business`, never the
generic `execute()`. Recorded in the test/evidence matrix and the locked Sol
prompt as a mandatory static guard.

---

## Sources consulted for the fresh Shopify-evidence check (OQ-D, OQ-RB-6)

All fetched live on 2026-07-17 from `developer.shopify.com` (shopify.dev):

- `OrderDisplayFinancialStatus` enum — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFinancialStatus — Accessible. 8 documented values (`AUTHORIZED`, `EXPIRED`, `PAID`, `PARTIALLY_PAID`, `PARTIALLY_REFUNDED`, `PENDING`, `REFUNDED`, `VOIDED`); no `UNKNOWN`/`NULL` member.
- `Order` object — https://shopify.dev/docs/api/admin-graphql/latest/objects/Order — Accessible. `displayFinancialStatus` nullable at the field level (no documented condition for null — [Inference, moderate confidence] pending a direct GraphQL introspection check); `transactions` field ("A list of transactions associated with the order"); `paymentGatewayNames` field, whose own worked example pairs `"Shopify Payments"` with `"Cash on Delivery (COD)"` on one order — Shopify's own docs anticipate exactly the gateway/manual mix this disposition addresses.
- `OrderTransaction` object — https://shopify.dev/docs/api/admin-graphql/latest/objects/OrderTransaction — Accessible. Confirms `manualPaymentGateway` (`Boolean!`) and `gateway` (`String`, nullable) as the current, distinct manual-payment-identity fields.
- `OrderTransactionKind` enum — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionKind — Accessible. 8 documented values (adds `EMV_AUTHORIZATION`, `SUGGESTED_REFUND`, `CHANGE` beyond the classic 5).
- `OrderTransactionStatus` enum — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionStatus — Accessible. 6 documented values including **`UNKNOWN`** ("The transaction status is unknown.") — Shopify's own schema treats "cannot classify" as a first-class outcome.
- `OrderSortKeys` enum — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderSortKeys — Accessible. `UPDATED_AT` confirmed present (item 10 above).
- No official page was found documenting an arbitration/precedence algorithm for an order carrying multiple, disagreeing transactions — an absence-of-evidence finding across a materially exhaustive search (Order/OrderTransaction/OrderPaymentStatus reference pages plus a targeted search), directly supporting the fail-closed disposition at item 5 above rather than an invented reconciliation rule.
- **Open questions logged, not resolved by this fetch** (do not block Wave 2; log for a future dev-store/introspection check per CLAUDE.md §7): exact GraphQL nullability punctuation for `Order.displayFinancialStatus` (recommend a live introspection query); exact REST `Transaction.status` enum (extraction inconclusive); exact API-version-introduction dates for `manualPaymentGateway`/`multiCapturable` (sourced only from an unverified search snippet).

## Consequences

- Wave 2's gate-decision table (`wave-2-definition-of-ready.md` §3) and open-question line are now fully closed or explicitly, non-blockingly deferred — none silently resolved in code.
- The re-accepted Task 012 packet (see the packet's own "Control-room re-acceptance (2026-07-17)" section) adopts dispositions 1, 2, 5, 11, 12, 13 above as binding.
- The re-accepted Area-6 order-scan slice and the locked Sol prompt adopt disposition 10 (ARCH PD-5 confirmed) and both preflight-discovered items (EQ-PF-1, EQ-PF-2) as binding requirements.
- No new PII field, masking capability, or PII-adjacent vocabulary was introduced by any disposition above.
- No DEC-031 Layer 2 model, mutation-attempt concept, or Shopify mutation is introduced or implied by any disposition above — every disposition operates entirely within Wave 2's read-only, `remote_read_replay_safe` boundary.

## Correction addendum (2026-07-17, same day)

A post-merge control-room re-review of the Wave 2 gate (PR #174, comments
[`5000101837`](https://github.com/AdamsOdoo/Adams/pull/174#issuecomment-5000101837)
and
[`5000111557`](https://github.com/AdamsOdoo/Adams/pull/174#issuecomment-5000111557))
found eight current-contract contradictions between the merged gate
documents (the Wave 2 Definition of Ready, the re-accepted Task 012/Area-6
packets, and the locked Sol prompt) that this addendum records and closes.
None changes a product decision, a scope boundary, or an open-question
disposition recorded in the table above — every fix below is either a
stale-wording correction or a genuine implementation-contract gap the
original gate session should have specified but did not.

| # | Contradiction found | Root cause | Disposition | Corrected in |
|---|---|---|---|---|
| C1 | DoR §2.2 row 13 and the Task 012 packet's own §6 test-file description said `test_order_import_mapping.py` covers "tax rate-match+creation+reuse" | Stale wording carried forward from an early planning draft; D-012-9 step 4 (round-6 item d6) had already **removed** tax auto-create from MVP scope well before the gate session, but the row/§6 text was never updated to match | Corrected to explicit-mapped-tax reuse only; creation/fallback/ambiguity behavior stays exclusively `test_order_tax_resolution.py`'s scope, itself explicit-mapping-only with no auto-create path anywhere | DoR row 13/15, Task 012 packet §0.8/§6, locked prompt §8.A |
| C2 | DoR row 9/Area-6 D-A6-3 required `order_scheduled_sync_enabled` to gate the order-scan cron, but DoR row 6's frozen exact settings list and the locked prompt's binding-decisions section never named it | The settings-inventory row (6) was written before D-A6-3's generic `<domain>_scheduled_sync_enabled` pattern was pinned to an exact Wave-2 field name; the two sections were never cross-checked | Added `order_scheduled_sync_enabled` (Boolean, default `False`) to the settings inventory everywhere it is exhaustively listed | DoR row 6/§2.4 criterion 9, Task 012 packet §0.1, Area-6 §0.5, locked prompt §5.J/§7 criterion 14 |
| C3 | DoR row 7 said `models/__init__.py` registers "the four new model files (rows 1–5)" — rows 1–5 name five files | Arithmetic/copy error at authoring time | Corrected to "five"; added a mandatory static import-registration test so an omission fails preflight, not runtime | DoR row 7, locked prompt §8.A |
| C4 | DoR row 8 gave `shopify.connector.tax.mapping` the same auditor/operator/reviewer/admin CRUD pattern as the ordinary customer-binding model, granting Operator create and Reviewer write | The row was drafted by copy-adapting the order-binding ACL row without re-deriving tax-mapping's own risk profile; tax mapping is configuration (it decides which `account.tax` a Shopify tax fingerprint resolves to), not an operational binding, and the accepted roles model treats configuration as Administrator-tier | Corrected to Administrator-create/write-only (auditor/operator/reviewer read-only, no unlink for any role); added the four-role negative-ACL test requirement | DoR row 8/§2.4 criterion 10, Task 012 packet §0.8/§5, locked prompt §3 clarification/§5.K/§8.E |
| C5 | The accepted `manual_gateway_policy = require_approval` product decision (binding since PR #173) had no defined backend approval action, permission mapping, provenance fields, audit behavior, or test contract anywhere in any Wave 2 document | The lifecycle-policy document accepted the *policy value* but no implementation packet ever specified the *mechanism* that policy value requires; the gap was not discovered until this post-merge re-review | Defined `action_approve_manual_gateway_order(reason)` on the already-allowed order-binding file, with a full permission/provenance/audit/atomicity/idempotency/evidence-refresh contract and four new protected provenance fields (`manual_gateway_approval_state`/`manual_gateway_approved_by_uid`/`manual_gateway_approved_at`/`manual_gateway_approved_shopify_updated_at`) | DoR row 1/§2.4 criterion 11, Task 012 packet §0.8/§5 (full contract), locked prompt §5.B/§7 criterion 16/§8.E |
| C6 | DoR row 13 and the Task 012 packet's §6 also said "tip mapping" (nonzero tips are in fact a hard fail-closed skip, never mapped) and vague "metadata" (the packet's own D-012-2/D-012-8/§4.4 data-minimization rules already name an exact allowlist) | Same stale-wording root cause as C1 — the test-description prose was never reconciled against the packet's own, already-binding financial-gate and data-minimization text | Corrected to zero-tip eligibility / nonzero-tip fail-closed (`unsupported_tip_tax_treatment`) and an exact allowlisted-fields description with mandatory negative query-shape assertions for every excluded field | DoR row 13, Task 012 packet §0.8/§6, locked prompt §8.A |
| C7 | DoR §2.8, the Task 012 packet §8, and the locked prompt §9 all described rollback as a "single-wave-PR revert" that "drops" order-binding/tax-mapping tables and settings fields | Conflated a source-level Git revert (removes files only) with a database schema change (requires a module upgrade or migration to actually run); `shopify_connector_sale` is also an existing shared module carrying the merged Task 011 customer-import capability, which an uninstall-based rollback would incorrectly remove too | Replaced with two explicit modes — (A) exact pre-production database-backup restore, (B) forward-disable in production preserving imported data — and an explicit statement that a Git revert alone touches no database; any destructive schema removal requires its own separately reviewed migration | DoR §2.8/§2.9 (full rewrite, now the authoritative rollback record for the wave), Task 012 packet §8, locked prompt §9 |
| C8 | The locked prompt's exact-starting-SHA line used an ad hoc `<fill in the exact post-gate-merge SHA…>` instruction rather than the standard placeholder convention | Authored before the issuance-SHA clarification (PR #174 comment `5000111557`) was posted | Replaced with the literal `<EXACT_SHA_AT_ISSUANCE>` placeholder plus the no-commit-between-verification-and-issuance instruction | Locked prompt, top identity line |

**Consequences of this addendum:** none of C1–C8 reopens or weakens any
disposition in the table above; none introduces a new PII field, masking
capability, DEC-031 Layer 2 seam, or Shopify mutation; the corrected
documents remain internally consistent with each other and with the actual
current code as of this addendum's own re-verification. Wave 2 implementation
remained unstarted throughout this correction pass.

## Rollback

Revert this record: every gate-decision/open-question line reverts to
"Proposed," and any packet/prompt text that cites a disposition by its item
number above becomes stale and must be reverted in the same act. No code,
schema, or protected reference is touched by this record in either
direction. Reverting the "Correction addendum" section above also reverts
DoR §2.2 rows 1/6/7/8/13/15/19, §2.4/§2.8/§2.9, the Task 012 packet's §0.8/§5/§6/§8,
the Area-6 packet's §0.5, and the locked prompt's §3/§5/§7/§8/§9 to their
pre-correction (contradictory) text — the same single commit must revert
all of them together, not a subset.
