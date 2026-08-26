# Defect and evidence-gap register

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

Severity uses `P0` for a release-blocking integrity/architecture absence,
`P1` for important pre-release correctness/capacity work, and `P2` for
maintainability, contract or policy issues. “Evidence gap” is not a defect
claim; it means a local implementation cannot prove its live behavior.

## Proven defects/gaps

| ID | Severity | Finding and exact evidence | Impact | Required correction / acceptance |
| --- | --- | --- | --- | --- |
| AA-001 | P0/P1 | No production webhook controller, subscription lifecycle, HMAC, delivery persistence, deduplication or async event handler. Evidence: all six manifests; `readiness_check.py:_check_webhook_hmac()` lines 436–453; source guard lines 149–176. | No near-real-time inbound signal path; Gate E impossible; Shopify delivery loss/order/duplicate behavior is unhandled. | Add modular hybrid webhook/reconciliation capability and pass live Gate E against the correct shop. |
| AA-002 | P1 | Product scan caps at 20,000 records/window (`product_scan.py:68-72,224+`) with no resumable enumeration; order scan caps at 10,000 (`order_scan.py:23-24,246+`) with no bulk/resumable path. | Large merchants can remain permanently behind the failing window. | Add resumable checkpoints or Bulk Operations; test >cap recovery and capacity. |
| AA-003 | P1 | Inbound cadence is hourly product, 15-minute order/inventory and hourly fulfillment; core drain is 5 minutes. Cron XML files identify exact intervals. | Polling is not near-real-time and may exceed business freshness targets. | Webhook signals for relevant topics plus scheduled reconciliation; publish measured latency. |
| AA-004 | P1 | Setup inventory contract says “Shopify to Odoo, then Odoo to Shopify” and baseline read, while inventory manifest states no Shopify→Odoo stock write and baseline import deferred (`setup_wizard.py:231-238`; `inventory/__manifest__.py:31-47`). | Operator can believe an inbound baseline was applied when it was not. | Correct copy/ownership matrix; add an explicit baseline/import product decision and test. |
| AA-005 | P2 | Fulfillment setup says fulfillment is never read back to create Odoo deliveries, while fulfillment manifest and scans implement Mode 2 conservative inbound reconciliation. | Merchant cannot predict which inbound fulfillment observations alter evidence or review state. | Document eligible Mode 2 effects and review-only cases; add UAT scenario. |
| AA-006 | P2 | Credential model makes no encryption-at-rest claim; masked/write-only UI and redaction are present. | Deployment policy may not satisfy a stronger secret-at-rest requirement. | Decide/record encrypted secret backend or accepted compensating controls; verify logs/ACLs/direct RPC. |
| AA-007 | P2 | Stale comments say connection generation is not bumped and `execute_business` is dormant, contradicted by lifecycle methods and domain call sites (`store.py:158-165`; `api_client.py:637+`). | Future maintainers and reviewers may misunderstand the live production path. | Correct comments/docstrings; add source drift guard if useful. |
| AA-008 | P1/P2 | No Shopify Bulk Operations implementation despite realistic large-volume requirement and finite scan caps. | Catalog/order capacity and rate-limit cost may not be sustainable. | Make a documented scale decision; implement and measure bulk/resumable path or set explicit supported limits. |

## Evidence gaps (not defects by themselves)

| ID | Missing evidence | Why it matters | Closure |
| --- | --- | --- | --- |
| EG-001 | No exact-head live credential exchange and remote identity | Wrong-domain historical tests cannot validate the correct shop | Gate A with masked credentials; record returned identity/scopes/version. |
| EG-002 | No exact-head fresh Shopify reads or mutations | Local job/test success is not external business success | Gates B–D/F with remote GID/read-back ledger rows. |
| EG-003 | No exact-head live transport timeout/uncertain/crash recovery | Unit/mocked outcomes cannot prove remote ambiguity handling | Gate G with controlled live sampling and preserved attempts. |
| EG-004 | No exact-head dedicated-user/multi-company runtime matrix | ACL/source review alone cannot prove RPC/direct-URL boundaries | Gate H with role restoration evidence. |
| EG-005 | Actions run `32103926602` was in progress at last check | CI acceptance cannot be claimed while the run is unfinished | Recheck exact head and final run status. |
| EG-006 | Fresh exact-head database URL is absent from this writer’s context | Reproducibility of the environment row is incomplete | Parent adds the URL to the control-room ledger; no guessing. |

## Correction workflow

Preserve this register and the live ledger before each correction. Assign
webhook/scale implementation to a Luna Max writer in an isolated worktree;
SOL Medium must review the changed production paths independently. After a
material correction: focused tests → exact-head Actions → fresh/warm/migration
Odoo.sh qualification → independent review → resume the interrupted live gate.

## 2026-08-24 exact-head onboarding findings

These findings were reproduced against development build `36848469`, exact
HEAD `c40c0f2ebac9bfa51c05dd3ff132df79ca31f6e0`, tree
`696cd26aa31393e2a7fb14fbe9efd36db63f090b`, and only the authorized shop
`testin-lzhbzhtc.myshopify.com`. They remain release blockers until the
correction and regression evidence are qualified on a later immutable head.

| ID | Severity | Finding and exact evidence | Merchant impact | Required correction / acceptance |
| --- | --- | --- | --- | --- |
| ONB-001 | P1 | Activation job `3684` ended `Succeeded`, but only three of ten expected subscriptions were active; seven rows were `Manual review` because Shopify held the same topics on older callback endpoints. The setup banner nevertheless led with “job #3684 ended in Succeeded.” | A merchant can read transport/job completion as webhook readiness although setup remains operationally incomplete. | Report the business outcome first: active/expected count and the exact unresolved topics. Never describe the parent job as successful without the incomplete consequence beside it. Add live-shape and browser regressions. |
| ONB-002 | P1 | Wrong-callback reconciliation deliberately refuses automatic deletion, but the subscription form provides only “Reconcile store webhooks”; there is no guarded operator action to replace a stale callback. | Setup dead-ends unless the merchant leaves Odoo and manually understands Shopify webhook administration. | Add an administrator-only, read-first replacement workflow: preserve exact remote GID/digests, require explicit review, queue durable deletion, verify absence, create the expected subscription, and verify Shopify read-back. Never guess identity or delete an unverified subscription. |
| ONB-003 | P1 | Seven subscription rows were `Manual review`, while Operations → Needs Attention displayed “No one needs to act.” | The day-to-day exception inbox contradicts the setup blocker and hides required work. | Project webhook manual-review cases into the operator attention surface with store, topic, reason, owner and a supported next action. Add ACL/company and empty/non-empty UI tests. |
| ONB-004 | P2 | Activation increments the connection generation and correctly invalidates the pre-activation location read, but the wizard returns to step 12 with a stale-mapping blocker and requires a manual trip back to step 7. | A correct safety fence feels like failed activation and creates avoidable backtracking. | Automatically enqueue and follow the current-generation location refresh after activation, retain existing mappings, and return the user to readiness when the read succeeds. Test slow-worker and page-reload paths. |
| ONB-005 | P2 | The location screen continued to say “Reading your Shopify locations” while the background job had already completed, until the operator clicked “Check status.” | The wizard appears stuck even though the backend completed successfully. | Poll/follow the exact job with a bounded timeout, refresh authoritative state after completion, and expose a clear background continuation state without requiring repeated manual checks. |

### Earlier onboarding findings retained as closed regression history

| ID | Earlier finding | Current exact-head disposition / regression contract |
| --- | --- | --- |
| ONB-H01 | Shopify 2026-07 changed `WebhookSubscription.apiVersion` from a scalar-shaped assumption to an `ApiVersion` object, causing the initial bootstrap to fail. | Corrected to select and validate `apiVersion { handle displayName supported }`; exact-head CI and the three live active subscriptions prove the current parser path. Keep malformed-object rejection and `Z`/offset RFC3339 tests. |
| ONB-H02 | Re-running setup with an already stored credential could clear or race the retained credential, and the browser could advance on stale presence evidence. | Corrected with lifecycle locking, action-time presence/mode verification, and interleaving tests. Keep write-only rendering and failure-path clearing tests. |
| ONB-H03 | The location mapper displayed a seemingly suitable internal location from another company; server enforcement rejected it. | Corrected with company-scoped candidates plus server enforcement. Keep real two-company UI/RPC regressions; never weaken the server fence because the picker is filtered. |
| ONB-H04 | Fulfillment webhook topics could reach subscription mutation without the required `read_fulfillments` readiness scope. | Corrected with topic/action-scoped admission. Exact-head readiness passed with `read_fulfillments`, and both fulfillment topics are active on Shopify 2026-07. Keep unrelated-topic creation and cleanup-deletion admission tests. |
