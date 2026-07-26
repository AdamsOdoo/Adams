# Wave 5 completion batch — validation results

> **Status: implementation evidence record. NOT an acceptance, NOT Odoo.sh
> runtime, NOT independently reviewed, NOT merged.** Produced 2026-07-26 on
> `fable/wave-5-completion` under the control-room continuation ruling of
> 2026-07-26.
>
> **Wave 5 is not complete.** Four of its seven stages are delivered. §6
> states exactly what is not, and why, without dressing either reason as the
> other.

---

## 1. Environment

`[Fact]`

| Item | Value |
| --- | --- |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1` (19.0), verified on every suite run |
| PostgreSQL | 16.14 |
| Python | 3.12.3 |
| Modules | `shopify_connector_core`, `_product`, `_sale`, `_inventory`, `_fulfillment` |
| Shopify | **none** — no store, credential, request, mutation or webhook at any point |
| Evidence class | **DEC-041 D8 supporting evidence. Odoo.sh remains the Tier-1 acceptance authority** |

## 2. Delivered stages

### 2.1 SEC-2 residual — PII simplification (Option 1)

`[Fact]` Business-record masking is **gone, not dormant**: the
`pii_snapshot_masked` field and compute, `action_mask_customer_pii`,
`_binding_models_with_pii`, the binding-masking loop in `run_sweep`, and the
field-level `groups=` restriction on the three snapshot fields are all
removed. Both customer-facing roles now read the raw operational snapshot.

Log/audit redaction is **retained** — job-log `payload_snapshot` and Layer-2
terminal attempt evidence — per the TA-C5 disposition that redaction is not
masking. The setting that drove both is renamed
`pii_snapshot_retention_days` → `log_redaction_retention_days`.

**Why a rename and not a retire-and-recreate `[Inference]`:** recreating would
have reset every store's configured window to `0`, which means *never redact*,
while looking like a clean install. The pre-migration renames the column so a
configured value survives.

**§E handled honestly `[Fact]`:** masking was irreversible, so rows masked
before SEC-2 are **flagged, never reconstructed**. A computed
`pii_snapshot_refresh_required` marks them; a sale post-migration logs how
many exist, counts only, no snapshot value.

**Migration evidence, on real migrated data:**

```
warm upgrade of a database carrying the pre-SEC-2 column
  column renamed              pii_snapshot_retention_days -> log_redaction_retention_days
  configured value preserved  42          (a recreate would have written 0)
  cron renamed                "Shopify Connector: Log Redaction Sweep"
  remediation audit           "1 of 2 customer bindings carry irreversibly
                               masked snapshots ... were not reconstructed"
  post-migration flag         SEC2Masked -> True, SEC2Clean -> False
  masked field present        False        mask action present  False
idempotency: all three migration scripts re-run against the migrated database
  -> columns, settings value and cron name unchanged
```

### 2.2 PERF-1 — source-rebased

`[Fact]` The packet's central deliverable was already merged in a stronger
form; implementing it as written would have replaced a hardened recovery model
with a weaker description of it. Full record:
[`task-perf1-validation-results.md`](task-perf1-validation-results.md).

Delivered: `ir.cron._commit_progress()` progress reporting and time budget,
a configurable per-pass cap, and pre-claim backpressure on
`store.api_health_state`. The Odoo 19 `_commit_progress` signature is verified
against the pinned source **by a test that runs on every suite**, not by a
session note.

`[Fact]` Measured dispatcher overhead **≈ 5.7 ms/job**. **PB-19 is not claimed
as met** — no Shopify store exists, so the benchmark runs a *declared
synthetic* latency profile and says so in its own output.

### 2.3 U1 — fulfillment operator experience

`[Fact]` Delivered in the previous batch, unchanged here. See
[`ui-u1-validation-results.md`](ui-u1-validation-results.md).

### 2.4 U2 — orders, COD, catalog matching, inventory

`[Fact]` Odoo-native views in the modules that own the data (ARCH PD-2),
hanging off the one existing U0 root:

| Branch | Surfaces |
| --- | --- |
| Orders (seq 15) | Orders workspace (S16), order review form (S17), COD reconciliation (S18) |
| Catalog & Matching (seq 32) | Product (S6), variant, customer (S8) matching |
| Inventory (seq 33) | Workspace (S19/S12), first-push guard (S11), location mapping (S10) |

**No business logic added.** Every button reaches a sanctioned server action
an earlier wave shipped. Three take **required** arguments an Odoo object
button cannot pass, so each gets a display-and-delegate `TransientModel`
following the U1 precedent; AST guards assert those wizards never `write`,
`create`, `sudo`, `commit` or `enqueue`.

**The one model change** is a `search=` seam on the existing computed
`pii_snapshot_refresh_required`. Without it a SEC-2 remediation sweep could
only be inspected one record at a time.

**The state dimensions are never merged.** An order can be paid and unshipped,
shipped and unpaid, or cancelled after both. Shopify's payment view, Shopify's
fulfilment view, the connector's own conclusion, payment approval and
cancellation each get their own column, and the form labels whose opinion each
strip reports. A test asserts against the view architecture that no merged
state field was introduced.

## 3. Findings — three defects the work itself surfaced

`[Fact]` None of these came from reading the diff.

### 3.1 Two states the views promised that the model forbids

The location-mapping view filtered on, decorated and banner-warned about
**unmapped** locations; the orders view did the same for orders with **no Odoo
order**. `odoo_location_id` and `sale_order_id` are both **NOT NULL**, so
neither state can exist. The views were offering an operator a filter that can
never match and a warning that can never fire.

Found by a test fixture failing to create the row the view described.
Corrected against source: the filters, decorations and banners are removed.

### 3.2 A UI/server authorization disagreement

`action_set_push_enabled` admits **Operator or Administrator** (its own
guard). The premium UX master specification §2.4 lists location mapping as
**User: read, Administrator: act**. The view initially followed the
specification and hid the control from a Connector User the server would
have permitted.

**Resolved against the server, and pinned by a test.** A view that hides a
permitted capability is a defect; one that shows a denied capability is worse.
`[Recommendation]` The specification/server discrepancy is recorded for the
control room and **not** resolved by silently changing either side.

### 3.3 A menu sequence collision

Inventory was first placed at sequence 30 — the same value U0 gave Sync Center
— leaving their rendered order dependent on insertion id. Moved to 33; a test
now asserts top-level connector sequences stay distinct.

### 3.4 Two guards that did their job

Worth recording because they are the reason two silent regressions did not
ship: the **frozen sudo inventory** caught PERF-1's new
`ir.config_parameter` read, and the **phase-contract guard** caught that the
new `-standard` benchmark class was not selected by any tag in the suite
runner — so continuous validation would never have executed it.

### 3.5 A fixture that passed locally and failed on a fresh database

The U2 inventory fixture parented its stock locations to the first `view`
location it found. Without demo data that location can belong to another
company, and `_check_company` refuses the create. This is exactly what the
fresh-install checkpoint pass exists to catch, and it caught it.

## 4. Test results

`[Fact — DEC-041 D8 supporting evidence, NOT Odoo.sh acceptance]`

| Suite | Result |
| --- | --- |
| SEC-2 focused (PII least-privilege, customer binding, security hardening, credential service) | **0 failed, 0 errors of 60** |
| PERF-1 focused (throughput, dispatch, retry scheduling) | **0 failed, 0 errors of 61** |
| PERF-1 benchmark (`shopify_connector_drain_throughput`) | **0 failed, 0 errors of 1** |
| U2 focused (product, inventory, sale) | **0 failed, 0 errors of 33** |
| Full connector suite — fresh / warm / non-standard | see §4.1 |

### 4.1 Full-suite checkpoint — clean worktree, exact head

`[Fact — machine-readable summary committed at
[`evidence/wave-5-completion-2026-07-26/connector-suite-summary.json`](evidence/wave-5-completion-2026-07-26/connector-suite-summary.json);
the container is ephemeral, so the artifact is committed to a durable path per
DEC-041 D3 rather than left in gitignored `ci-artifacts/`.]`

| Pass | Result |
| --- | --- |
| Fresh install + standard suite | **0 failed, 0 errors of 1616** |
| Warm `-u` update + standard suite | **0 failed, 0 errors of 1616** |
| Non-standard tag suite (concurrency proofs, benchmarks) | **0 failed, 0 errors of 19** |

```
tested_checkout_sha       19ba225dd7378baf7e80dac4678ac52ba3b65e33
connector_worktree_dirty  false
source_head_verified      true
odoo_pin_verified         true
shopify_operations        none
```

The non-standard count rose from 18 to 19: PERF-1's throughput benchmark is
the nineteenth, and it is reachable only because the phase-contract guard
refused to let a new `-standard` class exist without a tag in the runner
(§3.4).

Every intermediate failure named in §3 was corrected **before** the next
stage, never deferred to the final runtime.

## 5. Not claimed

- **No Odoo.sh runtime.** One exact-head campaign remains mandatory.
- **No independent review, no acceptance, no ready-mark, no merge.**
- **No Shopify credential, request, mutation or webhook.** No dev-store
  latency measured; none fabricated.
- **PB-19 not claimed as met.** The benchmark's profile is declared synthetic.
- **No browser/tour/HOOT evidence for U2.** The U2 surfaces are Odoo-native
  views; the driven-browser campaign that U1 ran was **not** repeated for
  them in this batch and no U2 screenshot is presented. Stated rather than
  implied by the absence of a section.
- **No multi-worker/topology-B claim; no exactly-once claim.**

## 6. Not delivered — and the two different reasons

`[Fact]`

**Task 015 (product export) and Task 015B (media export) are blocked by an
evidence-backed source-verification failure**, not by scheduling. The official
documentation does not resolve whether a `productSet` list field omitted
*entirely* is left alone or has every remote entry deleted — and D-015-3's
whole containment argument depends on the safe reading. Full record:
[`task-015-export-source-verification-2026-07-26.md`](task-015-export-source-verification-2026-07-26.md);
the resolving experiment is the blocking case **X-EXPORT-0** now at the head
of [`shopify-live-validation-package.md`](shopify-live-validation-package.md)
§4.0.

**U3's export-flow screens inherit that stop** — there is no
`action_confirm_export_preview` to wire a preview/diff surface to.

**U3's non-export scope** — reconnect/backfill (S25/S26),
settings/permissions/retention (S28/S29/S30), diagnostics (S31) and the polish
pass — is **not** blocked by that finding. It is not delivered because the
implementing session reached the end of its working capacity after U2. That
is a different reason and is not presented as a dependency.

**Wave 5 is therefore not complete, and this batch does not claim it is.**
