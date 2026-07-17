# Locked Sol Wave 2 Implementation Prompt — Order Import (Task 012 + Area-6 Order-Scan Slice)

> **Status: LOCKED, corrected 2026-07-17 (same day).** This is the
> canonical, ready-to-copy prompt for the Wave 2 implementation session.
> **It is issued, not executed, by this gate session.** Do not run this
> prompt in the same session that authored it. The exact base SHA below
> must be re-verified live against `mvp/program-integration` immediately
> before use — if it has drifted, update it and re-confirm the drift is
> only further-merged `docs/**` commits (nothing under `addons/**`) before
> proceeding.
>
> **Correction pass (2026-07-17):** a post-merge control-room re-review
> (PR #174 comments `5000101837`/`5000111557`) found and fixed eight
> contradictions in this prompt's first version — a stale tax-auto-create
> test description, a missing `order_scheduled_sync_enabled` field, a
> model-registration count error, a tax-mapping ACL copied from the wrong
> pattern, a missing manual-gateway-approval backend contract, stale tip/
> metadata wording, an unsafe rollback narrative, and the `<fill in...>`
> placeholder replaced with the standard `<EXACT_SHA_AT_ISSUANCE>` marker.
> No scope, decision, or disposition changed — see DEC-035's "Correction
> addendum (2026-07-17)" for the full record. Still not executed by any
> session that has touched this file.

---

## Paste-ready prompt

```text
REPOSITORY: AdamsOdoo/Adams

EXACT STARTING SHA (mvp/program-integration): <EXACT_SHA_AT_ISSUANCE>
(fill this placeholder with the exact live mvp/program-integration tip at
the moment this prompt is actually handed to a Sol session — verify it live
from GitHub immediately before issuance; do not reuse any SHA recorded in
this document's own authoring/correction session, and do not let any
repository commit occur between that verification and issuance)

WORKING BRANCH TO CREATE: sol/wave-2-order-import

PULL REQUEST: open one early DRAFT pull request from sol/wave-2-order-import
into mvp/program-integration, titled "Wave 2: Shopify order import
(Task 012 + Area-6 order-scan slice)".

ROLE: You are GPT-5.6 Sol, the primary autonomous research/implementation
worker for this MVP program (DEC-032). Claude is the control room and the
only party authorized to merge your wave PR. You do not merge your own PR.

======================================================================
MANDATORY PRE-EDIT CLAUSE (verbatim — do not paraphrase or skip)
======================================================================

"Before editing, perform a complete code, dependency, caller, test,
source-guard, migration, security and runtime-access preflight for the
entire wave. Resolve all implementation-level issues before coding. If a
genuine product decision is required, report all known blockers together in
one consolidated hard stop. Do not stop repeatedly for isolated issues that
could have been discovered during the initial audit."

======================================================================
MANDATORY COMPLETION CLAUSE (verbatim — do not paraphrase or skip)
======================================================================

"Do not report completion after only implementing the happy path.
Completion requires affected existing callers, inherited tests, AST/source
guards, install/upgrade/uninstall behavior, runtime integration,
concurrency, residue, security and exact-head evidence to be reconciled in
the same wave."

======================================================================
1. IDENTITY VERIFICATION (perform first, live from GitHub)
======================================================================

1. mvp/program-integration is exactly the SHA above.
2. Wave 1 (PR #172) remains merged; SRR-03 remains CLOSED.
3. The Fable gap-closure mission (PR #173) remains merged.
4. This Wave 2 gate PR is merged; wave-2-definition-of-ready.md §5 reads
   "READY. Accepted."; the Task 012 and Area-6 packets both carry their
   "Control-room re-acceptance (2026-07-17)" sections.
5. Protected refs unchanged: checkpoint/core-r2-readonly-uat-2026-07-15
   (acd8c4691e72cf5590f2a56228b08f183b76cd9a), Shopify-connector
   (dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b), main
   (a5d45432a9b60f724c1aff700f4b371ea019960e).
6. No order-domain code exists yet beyond this wave's own commits (re-verify
   with git ls-tree/git grep — do not assume the gate session's finding
   still holds without re-checking).

If any condition fails, stop and report one consolidated finding. Do not
create the branch or PR until identity verification passes.

======================================================================
2. READ FIRST (in this order)
======================================================================

1. CLAUDE.md (all of it, including §13).
2. docs/07-implementation-plan/wave-2-definition-of-ready.md (accepted,
   §2.2/§2.3 are your exact allowed/forbidden files).
3. docs/07-implementation-plan/task-012-order-import-implementation-packet.md
   §0 (control-room re-acceptance) first, then the full packet.
4. docs/03-architecture/task-012-order-import-decision-closure.md (full —
   this supersedes the packet where they differ, per the packet's own
   text).
5. docs/07-implementation-plan/area-6-sync-triggers-implementation-packet.md
   §0 (control-room re-acceptance, order-scan slice only) first, then D-A6-1,
   D-A6-2, D-A6-3, D-A6-4, D-A6-6 (D-A6-5/D-A6-7 are historical — already
   implemented elsewhere).
6. docs/04-decisions/DEC-035-wave-2-open-question-dispositions.md (every
   open question's binding disposition — do not re-litigate any of them).
7. docs/04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md
   (the binding-extension contract your new binding models must satisfy).
8. docs/02-product/sales-order-lifecycle-and-confirmation-policy.md,
   cod-lifecycle-and-reconciliation.md (Wave-2 import-level rows only),
   reconnect-catchup-backfill-policy.md (order-domain subset only),
   abandoned-checkout-policy.md (PD-AC-1 negative boundary only).
9. docs/05-qa/rejected-approaches-log.md, architecture-review-log.md (at
   least AR-037, AR-042, AR-048, AR-049, AR-053, AR-054).
10. docs/06-prompts/claude-mvp-wave-review-template.md (the checklist your
    PR will be reviewed against — write your progress report to satisfy it).

======================================================================
3. ALLOWED FILES (exhaustive — copied from wave-2-definition-of-ready.md §2.2;
   that document is the source of truth if this copy and it ever diverge)
======================================================================

addons/shopify_connector_sale/models/shopify_connector_order_binding.py (NEW)
addons/shopify_connector_sale/models/shopify_connector_sale_order_line.py (NEW)
addons/shopify_connector_sale/models/shopify_connector_order_importer.py (NEW)
addons/shopify_connector_sale/models/shopify_connector_tax_mapping.py (NEW)
addons/shopify_connector_sale/models/shopify_connector_order_scan.py (NEW)
addons/shopify_connector_sale/models/shopify_connector_store_settings.py (MODIFY, additive fields only)
addons/shopify_connector_sale/models/__init__.py (MODIFY, import registration only)
addons/shopify_connector_sale/security/ir.model.access.csv (MODIFY, additive rows only)
addons/shopify_connector_sale/data/shopify_connector_sale_cron.xml (NEW)
addons/shopify_connector_sale/__manifest__.py (MODIFY: version, depends, data)
addons/shopify_connector_sale/migrations/<next-version>/post-migrate.py (NEW, only if genuinely needed — additive/idempotent only)
addons/shopify_connector_sale/tests/test_order_binding.py (NEW)
addons/shopify_connector_sale/tests/test_order_import_mapping.py (NEW)
addons/shopify_connector_sale/tests/test_order_totals_guard.py (NEW)
addons/shopify_connector_sale/tests/test_order_tax_resolution.py (NEW)
addons/shopify_connector_sale/tests/test_order_duplicate_prevention.py (NEW)
addons/shopify_connector_sale/tests/test_order_customer_resolution.py (NEW)
addons/shopify_connector_sale/tests/test_order_confirmation_policy.py (NEW)
addons/shopify_connector_sale/tests/test_order_manual_gateway_overlay.py (NEW)
addons/shopify_connector_sale/tests/test_order_watermark_backfill.py (NEW)
addons/shopify_connector_sale/tests/test_order_cod_import_readmodel.py (NEW)
addons/shopify_connector_sale/tests/test_order_scan_triggers.py (NEW)
addons/shopify_connector_sale/tests/__init__.py (MODIFY, import registration only)
docs/05-qa/task-012-order-import-validation-results.md (NEW)
docs/05-qa/task-area6-order-scan-validation-results.md (NEW)
docs/05-qa/architecture-review-log.md (MODIFY, append one AR row only)
docs/07-implementation-plan/mvp-program-state.md (MODIFY, wave-status/sprint-log only)
docs/05-qa/mvp-acceptance-matrix.md (MODIFY, row 9 [+13/14 if applicable] only)
docs/01-research/research-handoff.md (MODIFY, prepend your handoff entry only)

Two clarifications on files already in this list (corrected 2026-07-17,
post-merge control-room review — full contract: Task 012 packet §5 "Manual-
gateway approval backend contract" and §0.8; DEC-035 "Correction addendum"):
(a) shopify_connector_order_binding.py MUST also define
action_approve_manual_gateway_order(reason) and the four
manual-gateway-approval provenance fields
(manual_gateway_approval_state/manual_gateway_approved_by_uid/
manual_gateway_approved_at/manual_gateway_approved_shopify_updated_at) —
this is not a new file, it is a mandatory addition to this already-allowed
file; (b) ir.model.access.csv MUST use TWO DIFFERENT ACL patterns — the
customer-binding read/write/create pattern for
shopify.connector.order.binding, but an Administrator-create/write-only
pattern (auditor/operator/reviewer read-only, admin read/write/create, no
unlink for either model) for shopify.connector.tax.mapping, which is
configuration, not an operational binding. Do not copy the binding pattern
onto tax mapping.

Any file not in this list is forbidden by omission. In particular: no
shopify_connector_core edit of any kind (reuse sale_domain_enabled — do
not touch ACCEPTED_DOMAIN_FLAGS); no shopify_connector_product edit unless
an exact inherited regression is proven, named, and justified individually
in your progress report; no shopify_connector_customer_binding.py /
shopify_connector_customer_importer.py / shopify_connector_res_partner.py
edit (read-only reuse of the existing Task 011 match sequence only); no
inventory/fulfillment/product-export/media file; no accounting/invoice/
payment/refund/payout logic; no UI/views/menus/actions/wizards/controllers;
no webhooks/OAuth; no CI/Docker/requirements files; no adams_base file; no
DEC-031 Layer 2 model/seam of any kind; no protected branch/ref/PR/issue
(checkpoint, Shopify-connector, main, PR #150, PR #151, issue #165); no
PII-masking field/setting/action/toggle of any kind; no manual_review_subreason
selection_add (use the binding's existing status='review' value instead,
per DEC-035 item 5).

======================================================================
4. INTERNAL STAGE SEQUENCE (fixed — do not reorder)
======================================================================

1. Task 012 order-binding + order-importer foundation (models, mixin
   contract, four-query GraphQL read, financial/tax/customer/product
   resolution, execute_business-only AST guard, dispatcher/enqueue seam
   registration for order_import_sync -> sale_domain_enabled).
2. Importer tests green; dispatcher registration verified (handler resolves,
   replay policy registered as remote_read_replay_safe).
3. Area-6 order-scan job/cron/manual backend trigger (order_import_scan job
   type -> sale_domain_enabled; scan enumerates and enqueues only, never
   contains import logic itself).
4. Catch-up/backfill backend service (watermark advance/hold-back,
   Administrator preview computing new/changed/duplicate/skipped/
   needs-review counts, zero jobs/records created by preview, confirmed
   enqueue only after explicit confirmation).
5. Full combined validation (Task 012 + order-scan run together; full
   existing core/product/sale regression; Odoo.sh evidence).

The scan may not execute before its importer handler exists and is
registered.

======================================================================
5. BINDING PRODUCT DECISIONS (do not reopen — cite by ID if a caller asks why)
======================================================================

A. ORDER CONFIRMATION: order_confirmation_policy (paid_only [default] /
   paid_or_authorized / quotations_only), per store.
B. MANUAL PAYMENT GATEWAYS: manual_gateway_policy (confirm_auto / quotation
   / require_approval [default]); gateway must be on the Administrator's
   approved_manual_gateways list; discriminate via transaction evidence
   (manualPaymentGateway + gateway identity), never PENDING alone; card
   PENDING never receives manual-gateway treatment. Under require_approval,
   confirmation is a Reviewer/Administrator-only backend action,
   action_approve_manual_gateway_order(reason), on the order binding — full
   contract (permission mapping, provenance fields, atomicity, idempotency,
   refresh-before-confirm) is Task 012 packet §5's "Manual-gateway approval
   backend contract"; no UI in Wave 2.
C. PENDING PAYMENT: pending_wait_expiry default 24h, min 1h, max 7d (PD-B1);
   later PAID evidence reconciles without a duplicate order.
D. IMPORT WINDOW: order_import_window quick 7/30/60 days + custom range,
   default 30 days; ranges beyond current Shopify access blocked with an
   exact scope explanation; mandatory preview before enqueue.
E. ABANDONED CHECKOUTS: never auto-create a quotation, no stock reservation,
   no order binding (PD-AC-1) — negative test required.
F. COD: operational read model only in Wave 2 (COD flag + ledger snapshot +
   three-dimension state init at import); no automatic accounting posting;
   no orderMarkAsPaid (out of Wave 2 entirely, DEC-035 item 6).
G. RECONNECT/BACKFILL: fresh current-generation scans; watermark minus
   overlap; no blind replay of stale-generation jobs; mandatory backfill
   preview; duplicate prevention across every discovery path.
H. PII: no new PII-masking field/capability of any kind; raw PII never
   leaks into jobs, logs, audits, errors, hashes, or diagnostic evidence;
   the order binding stores no PII at all (declare _pii_snapshot_fields()
   returning an empty tuple).
I. MUTATION BOUNDARY: Wave 2 is 100% read-only toward Shopify; declares
   remote_read_replay_safe; no DEC-031 Layer 2 model or mutation wrapper;
   no exactly-once remote-effect claim anywhere in code, tests, or docs.
J. SCHEDULED SYNC: order_scheduled_sync_enabled (default False, per store)
   gates the order-scan cron alongside sale_domain_enabled; Administrator-
   only configuration is already structural via the store-settings model's
   existing ACL (no new field-level groups= needed); disabling it stops new
   scheduled scans without destroying already-enqueued or historical jobs.
K. TAX-MAPPING ACCESS: shopify.connector.tax.mapping is configuration, not
   an operational binding — Administrator create/write-only (auditor/
   operator/reviewer read-only, no unlink for any role); do not reuse the
   order-binding's read/write/create-per-role pattern here.

======================================================================
6. OPEN-QUESTION DISPOSITIONS (binding — full detail in DEC-035)
======================================================================

- Null/missing displayFinancialStatus at import -> data_shape_schema_mismatch,
  no SO, no binding, failed_final.
- Post-confirmation payment-evidence loss -> evidence-refresh only, one
  'note' log row, zero SO/line writes.
- Mixed/ambiguous transaction evidence -> import succeeds, binding
  status='review' (existing mixin value), SO created draft regardless of
  policy. Never a new selection value.
- orderMarkAsPaid/orderCreateManualPayment -> out of Wave 2 entirely.
- pending_wait_expiry -> 24h/1h/7d (PD-B1), not the addendum's stale
  "proposed 7 days" text.
- order_confirmation_policy default -> paid_only (replaces the packet's
  original no-default order_import_confirmation_policy field entirely).
- D-012-4 ambiguous-customer flow -> confirmed as written; use the
  already-merged action_manual_retry().
- Domain-enablement flag -> reuse sale_domain_enabled for both
  order_import_sync and order_import_scan; no new flag, no core edit.
- ARCH PD-5's sortKey: UPDATED_AT -> confirmed present in Shopify's current
  OrderSortKeys enum (verified live 2026-07-17; re-verify again at
  implementation time since API surfaces can change).
- COD collection-event currency policy (OQ-COD-6) -> non-blocking; DEC-020
  already routes any presentment!=shop-currency order to skipped before any
  SO/binding/COD-ledger event, so this never arises inside Wave 2's own
  scope.

======================================================================
7. ACCEPTANCE CRITERIA (Task 012 packet §8 + Area-6 §4, plus the new criteria
   this gate session added)
======================================================================

1. 8-state x 3-policy confirmation matrix produces exactly the mandated
   outcome in every cell.
2. Manual-gateway overlay behaves per policy; unapproved/card-PENDING never
   take the manual path.
3. Mixed-transaction orders import with status='review' and draft SO,
   never auto-confirmed regardless of policy.
4. Duplicate prevention: unique (store_id, shopify_gid) binding created
   atomically with the SO; every rediscovery path (scan, catch-up, manual,
   backfill) updates, never creates a second SO.
5. Six fail-closed pre-creation financial gate families, total-check ledger,
   divergent-currency skipped routing, explicit-mapping-only tax posture —
   all block before any SO exists, regardless of confirmation policy.
6. Watermark catch-up + Administrator backfill preview (zero jobs/records
   until confirmed) + 60-day/read_all_orders honesty.
7. COD read-model captured at import (flag + ledger snapshot + three
   dimensions initialized); no stock/fulfillment mechanics (Wave 4).
8. Registers remote_read_replay_safe; no Layer-2 or exactly-once claim
   anywhere.
9. Order-scan cron/manual trigger enqueue idempotently (collision-safe via
   shopify_target_gid='scan:order').
10. Order binding declares _odoo_binding_field_name() -> 'sale_order_id' and
    a complete _additional_protected_binding_fields() set (DEC-034); an
    exact protected-set test exists and passes.
11. Order binding declares _pii_snapshot_fields() -> () (empty).
12. Abandoned checkouts never enter the order pipeline (PD-AC-1 negative
    test).
13. All existing core/product/sale tests remain green — zero regression.
14. order_scheduled_sync_enabled (default False) gates the order-scan cron
    alongside sale_domain_enabled; either false, or the store not
    connected, means no enqueue; the cron never imports inline; disabling
    the flag stops new scans without destroying existing jobs.
15. shopify.connector.tax.mapping is Administrator-create/write-only;
    Auditor/Operator/Reviewer create and write are denied server-side; no
    role can unlink; a denied attempt leaves no row and no audit residue.
16. action_approve_manual_gateway_order(reason) exists, is Reviewer/
    Administrator-only, requires a non-empty reason and a draft SO, refuses
    when policy/gateway/evidence no longer qualify, never mutates Shopify,
    refreshes evidence before confirming, is idempotent, records exactly
    one audit log, and rolls back atomically if audit or enqueue fails.

======================================================================
8. TEST AND EVIDENCE MATRIX (targeted tests, full regression, and mandatory
   static/runtime evidence — every letter below is required)
======================================================================

A. STATIC / PREFLIGHT
   - Python/XML/CSV/manifest parse clean for every new/changed file.
   - Exact import-registration test: models/__init__.py registers all FIVE
     new model files (shopify_connector_order_binding,
     shopify_connector_sale_order_line, shopify_connector_order_importer,
     shopify_connector_tax_mapping, shopify_connector_order_scan) — not
     four; an omitted import must fail this static test, not surface only
     at runtime.
   - Exact selection_add + LC-1 ondelete declarations for both new job
     types (order_import_sync, order_import_scan) — same pattern as
     product_import_sync/customer_import_sync, verified by the same kind
     of AST test LC-1 already uses.
   - Dependency graph: manifest depends becomes
     ['shopify_connector_core', 'shopify_connector_product', 'sale'].
   - New source/AST guards: execute_business-only in the order importer and
     order-scan files (no execute() call reachable); no .create( call
     inside any dispatch-registration code (mirrors
     test_source_level_job_dispatch_never_calls_create); sudo-site exact
     inventory for the two new files, following the existing per-file
     exact-count AST-guard pattern.
   - No automatic account.tax creation anywhere in the importer or the tax
     mapping model (source/ORM-level negative assertion) — explicit-mapping
     resolution only, no rate fallback, no order_tax_autocreate setting of
     any kind.
   - Exact protected-set classification test for the order binding (16/17/14
     precedent — record the actual count here; must include the four
     manual-gateway-approval provenance fields).
   - No context-bypass (with_context/sudo escape) outside the sanctioned
     sites.
   - Sudo inventory: every new .sudo() call quoted and justified in the
     validation record, exactly as the product/customer importers already
     document theirs.
   - No PII in logs (order binding has no PII fields; log/redaction pass
     over every new log-emitting call site).
   - No Shopify mutation path anywhere (grep for mutation keywords in the
     new GraphQL query constants — all four must be `query`, never
     `mutation`; action_approve_manual_gateway_order enqueues a read-only
     refresh job, it does not call the Shopify API directly).

B. TASK 012 FUNCTIONAL
   - All 8 financial states x all 3 confirmation policies.
   - All manual-gateway policies; approved and unapproved gateways;
     card-PENDING; mixed transactions (status='review' path); null
     financial status (data_shape_schema_mismatch path).
   - PAID/AUTHORIZED/PENDING transitions; cancellations before and after
     confirmation; refunded/partially-refunded evidence.
   - Exact totals; currency; taxes; shipping; discounts; tips; duties; fees;
     rounding; unsupported financial shapes (each named policy-skip gate).
   - Product/customer mapping failures (mapping_missing whole-order hold);
     company boundaries.

C. DUPLICATE PREVENTION
   - Scheduled scan; reconnect scan; manual scan; backfill; repeated pages;
     overlapping watermark windows; duplicate webhook-follow-up evidence
     (even though webhook ingress is not implemented — simulate the
     re-discovery path only); concurrent discovery; one permanent binding;
     no second Odoo sale order, proven under real PostgreSQL concurrency
     where the enqueue/binding contract needs it.

D. SCAN / CATCH-UP
   - Watermark advance; watermark hold-back on partial failure; overlap;
     pagination; stale-generation refusal; backfill preview creates no
     jobs/records; confirmed backfill; resumability; 60-day/read_all_orders
     honesty; idempotent cron/manual enqueue.

E. SECURITY
   - All four existing roles (auditor/operator/reviewer/admin) under the
     order binding's ACL (customer-binding pattern); protected order-binding
     create/write/clear denial for all four roles; sanctioned importer
     positive paths; settings Administrator-only where specified; no direct
     state/provenance mutation; company consistency; ACL/source-guard
     coverage; raw PII absent from logs/audits/errors (trivially true — no
     PII fields exist, but still test-covered).
   - shopify.connector.tax.mapping four-role ACL matrix: Administrator
     create/write succeed; Auditor/Operator/Reviewer create AND write
     denied (not just create); unlink denied for all four roles; a denied
     attempt leaves no row and no audit residue; wrong-company/inactive/
     incompatible-tax mapping denied even for Administrator.
   - action_approve_manual_gateway_order full permission/atomicity matrix:
     Reviewer and Administrator succeed; Auditor and Operator denied;
     missing/empty reason rejected; wrong store policy rejected; gateway no
     longer approved rejected; non-manual-gateway or mixed evidence
     rejected; non-draft SO rejected; stale Shopify evidence forces a
     refresh rather than a stale confirm; changed evidence since approval
     routes to review, never a silent confirm; duplicate calls are
     idempotent; audit-log-creation or enqueue failure rolls back the
     approval field write atomically; direct create/write/clear of the four
     approval-provenance fields is denied for all four roles via the
     existing binding-mixin protected-field guard.

F. LIFECYCLE
   - Fresh install; prior-version upgrade; uninstall; reinstall; job-type
     selection removal (both new job types); historic conversion;
     immutable original_job_type; no orphan cron/ACL/XML ID; no residue.

G. CORE REGRESSION
   - Full core/product/sale standard suite green; LC-1; JOB-ACTIONS; SEC-1;
     CORE-R1; one combined SRR-03 smoke; real PostgreSQL concurrency where
     the order-binding/enqueue contract needs it; clean issue #157
     accommodation and restoration (apply/drop the same temporary defaults
     pattern Wave 1 used, do not invent a new one).

H. RUNTIME
   - Mandatory Odoo.sh exact-head evidence (fresh install + upgrade +
     focused-class + full regression), quoted verbatim with build ID in
     docs/05-qa/task-012-order-import-validation-results.md and
     docs/05-qa/task-area6-order-scan-validation-results.md.
   - Read-only Shopify dev-store order evidence is preferred but is NOT a
     Wave 2 merge blocker. If unavailable, defer honestly to Wave 6 with no
     false claim and no special waiver — say so plainly in your progress
     report.

No silent caps: if any of the above is bounded (top-N sample, no-retry,
partial coverage), say so explicitly in your progress report — do not let
a silent scope reduction read as full coverage.

======================================================================
9. ROLLBACK, RESIDUE, SECURITY, DEFINITION OF DONE
======================================================================

ROLLBACK (corrected 2026-07-17 — full record: DoR §2.8): a source-level Git
revert of the wave PR by itself changes no database schema — it only
removes files. Two explicit modes: (A) exact pre-production rollback via a
database backup taken immediately before the module upgrade, restored if
needed, with the code revert deployed on top; (B) forward-disable in
production — set order_scheduled_sync_enabled=False, quiesce non-terminal
jobs via the already-merged JOB-ACTIONS lifecycle paths, and leave imported
sale.order records, order bindings, and tax mappings exactly as they are.
Never uninstall shopify_connector_sale as a Wave 2 rollback action — it also
carries the merged Task 011 customer-import capability this wave does not
own. No destructive schema removal in an emergency rollback; that requires
its own separately reviewed migration. Nothing in Wave 3+ exists yet to
depend on this wave's internals beyond the merged binding contract.

RESIDUE: post-uninstall, zero orphan ir.model.data/crons/ACLs/selection
values; LC-1's _reassign_to_historic_job_type() registered on both new job
types from the start; zero PII residue (no PII fields exist on this
binding to begin with — confirm, don't assume).

SECURITY: SEC-1's protected-field contract (DEC-034) applies to the new
binding from day one; no new sudo() call outside the module-local guard's
declared inventory; no new unguarded RPC/ORM write surface.

DEFINITION OF DONE: template §7 in full (implementation-task-template.md)
+ wave-review template §1-8 all satisfied + this file's §7/§8 all satisfied
+ mvp-program-state.md and mvp-acceptance-matrix.md updated + validation
records + one new AR row + handoff entry with the learning-feedback-loop
section + draft PR opened + STOP.

======================================================================
10. HARD STOPS
======================================================================

The program's 11 standing hard-stop conditions apply verbatim (
mvp-completion-program.md). Wave-2-specific: any gate decision not Accepted
at wave-open (none currently — this gate closed them all); a Shopify
mutation appearing necessary for any acceptance criterion above (none should
be — if one seems required, stop, this wave is read-only by design); a
protected reference drifting; a security/credential-exposure risk; the
active wave failing to satisfy its own definition of done.

======================================================================
11. FINAL-REPORT FORMAT
======================================================================

Use the exact per-wave progress-report format from
gpt56-sol-master-mvp-mission.md §11:

### Wave 2 — Order import — progress report (<date>)
- Branch / PR: sol/wave-2-order-import; PR #<n> -> mvp/program-integration, <status>.
- Scope covered this report: <what's done>.
- Remaining in this wave: <what's left>.
- Runtime evidence: <Odoo.sh build, test counts, pass/fail>.
- Open questions / decisions needed: <list, or "None">.
- Hard-stop triggered? <No / Yes - which condition and why>.
- Next action: <what you're doing next, or "Awaiting control-room wave review">.

Do NOT execute this prompt in the session that authored it. Do NOT start
Wave 3+ scope, DEC-031 Layer 2, UI, webhooks, or OAuth work under any
circumstance.
```

---

## Provenance

Assembled 2026-07-17 by the Claude control room from the accepted
[Wave 2 Definition of Ready](../07-implementation-plan/wave-2-definition-of-ready.md),
the re-accepted
[Task 012 packet](../07-implementation-plan/task-012-order-import-implementation-packet.md)
(§0) and its
[decision closure](../03-architecture/task-012-order-import-decision-closure.md),
the re-accepted
[Area-6 order-scan slice](../07-implementation-plan/area-6-sync-triggers-implementation-packet.md)
(§0), and
[DEC-035](../04-decisions/DEC-035-wave-2-open-question-dispositions.md).
Not executed by the session that authored it. The exact starting SHA
placeholder must be filled in with the live `mvp/program-integration` tip
at the moment this prompt is actually issued to a Sol session — never reuse
a stale SHA from this document's own authoring session.
