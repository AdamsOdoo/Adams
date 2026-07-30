# PR #204 — Batch 2 P0 merchant reachability

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

> **Scope of this record.** The unified Batch 2 campaign specified three
> checkpoints. This record covers **checkpoint 1 only — canonical Store
> Settings** — implemented under an explicit product-owner re-scope of the
> campaign's no-partial-push rule (§5), taken during the session after the
> unified scope was assessed against what one session can implement *and*
> validate. Checkpoints 2 (order controls and tax decisions) and 3 (product
> admission and matching) are **not begun**. Nothing here claims otherwise,
> and nothing here weakens what those checkpoints must still prove.

## 1. Heads

- Starting head (identity-gate verified): `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e`
- Checkpoint 1 commit: `9a706824b9fe1089c3785e4314ed8d3d05d74d19`
- Base: `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, confirmed ancestor)
- Odoo pin: `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run
- History: **additive only** — no amend, rebase, squash, reset or force-push

### Identity gate

All ten items passed before any edit. Repository `AdamsOdoo/Adams`; PR #204
open, draft, unmerged, **zero reviews**; head branch `fable/wave-5-completion`;
PR head, remote branch head and local HEAD all exactly the required starting
head; base unchanged and an ancestor; clean worktree; `tools/odoo-pin.txt`
carrying the required pin; no later unreviewed commit.

One item needed care rather than acceptance at face value. `git merge-base
--is-ancestor` initially reported the base was **not** an ancestor. That was
the clone, not the branch: the working copy was shallow at 50 commits, so the
base commit was simply absent from the object store. After `git fetch
--deepen=200` the ancestry resolves. A shallow clone answering an ancestry
question with silence that reads as "no" is worth recording, because the
honest-looking action there is to stop on a false negative.

## 2. What checkpoint 1 closes

The first of the three §2 defects: **the promised per-store settings surface
did not exist**, and important core, product-import, sale and inventory
settings were not merchant-reachable after onboarding.

`Shopify Connector → Configuration → Store Settings` is that surface. It is
not a second setup wizard — it collects no consent, runs no readiness check,
drives no lifecycle transition and creates no store — and it does not compete
with the two dedicated surfaces that already own their own subjects.

The sharpest single instance: **`order_scheduled_sync_enabled` had no
production writer anywhere in the repository.** The cron
(`_cron_enqueue_order_scans`) and the enqueue producer (`_enqueue_order_scan`)
both already existed and both already selected on that field. The only thing
missing was a control a merchant could reach. That is now on the canonical
form, writing through the ordinary model path.

**Not claimed:** §7's order controls (`Import orders now`, `Refresh this
order`, the tax decision route) and §8's product scan producer and durable
match decisions are checkpoint 2 and 3 work and are untouched.

## 3. Field ownership and classification

Every module contributing a field to `shopify.connector.store.settings`
classifies **all** of them, as §6.6 requires, into exactly one of: canonical
editable, canonical read-only, owned by a named existing dedicated surface, or
internal/protected with a named justification.

**There is no expected field count anywhere in the tests.** A count is
satisfied by any set of the right size — it passes when one field is added and
another removed, and says nothing about the field that was added. The
assertion is set equality against the live registry (`Field._modules`), so
adding a field to the model in any module fails that module's test until it is
classified by name.

### Core (`shopify_connector_core`)

| Field | Classification |
| --- | --- |
| `product_domain_enabled` | canonical editable |
| `sale_domain_enabled` | canonical editable |
| `inventory_domain_enabled` | canonical editable |
| `fulfillment_domain_enabled` | canonical editable |
| `log_redaction_retention_days` | canonical editable |
| `store_id` | canonical read-only |
| `company_id` | canonical read-only |
| `product_first_sync_source` | canonical read-only |
| `notification_default_enabled` | canonical read-only |
| `price_source_of_truth` | owned by **Export Settings** |
| `setup_wizard_step_key`, `setup_wizard_step`, `setup_readiness_stale_since`, `setup_completed_at`, `setup_completed_uid`, `setup_last_rerun_at`, `setup_last_rerun_uid` | internal/protected — setup progress and the readiness marker, written only by the setup service |

`notification_default_enabled` is read-only and says on screen why: opting in
means Shopify emails customers on fulfilment, and that consent stays on the
guided Setup Wizard's notification step, which refuses to enable without an
explicit confirmation (`save_notification`). No second consent path was added.

`product_first_sync_source` is read-only; a post-onboarding direction switch
was not authorized here.

### Product (`shopify_connector_product`)

`product_import_media_enabled`, `product_import_refresh_mode`,
`product_import_attribute_conflict_mode` — all canonical editable.

**Deliberately absent, and why.** §6.3 lists a scheduled product-import
enablement field and a product-import checkpoint/last-success observation, both
explicitly "required by checkpoint 3". Checkpoint 3 is not implemented, so
nothing in production enqueues product enumeration. Rendering a "run product
import on a schedule" toggle now would be a control that silently does nothing
— the same false-capability failure §6.4 forbids and the one this surface
exists to end. A test asserts the field does not appear without the producer,
and fails the moment one is added unwired.

### Sale (`shopify_connector_sale`)

Canonical editable: `order_scheduled_sync_enabled`, `order_confirmation_policy`,
`manual_gateway_policy`, `approved_manual_gateways`, `order_import_window`,
`pending_wait_expiry`, `order_import_include_test`,
`customer_fallback_partner_id`, `order_pricelist_id`, `order_sales_team_id`,
`order_payment_term_id`.
Canonical read-only: `order_company_id`, `sale_order_last_import_checkpoint_at`.

**`customer_fallback_partner_id` — the §6.4 proof.** §6.4 requires the fallback
setting to be proved consumed or else rendered unavailable. It **is** consumed:
`ShopifyConnectorOrderImporter._resolve_customer`
(`shopify_connector_order_importer.py:1164-1165`) returns it with resolution
`fallback` for an order carrying no usable customer email, and raises
`odoo_validation_configuration` when it is unset. It is therefore rendered as
the real setting it is.

The field's own docstring still described it as inert substrate — "zero
order-resolution behaviour", never read. That was true when Task 011
introduced it and stopped being true when Task 012 landed order import. The
docstring is corrected rather than trusted, because the canonical form decides
whether to present a field as supported on exactly that question, and a stale
comment is how it would have been presented wrongly. **This is the one Batch 1
file changed beyond the checkpoint's own additions, and it is named here so the
control room can reverse the reading.** A test asserts the production call site
exists, so the day it is removed the form stops claiming the capability.

### Inventory (`shopify_connector_inventory`)

`inventory_scheduled_sync_enabled` — canonical editable (the inventory
service's `run_inventory_push_scan` selects on it, so it genuinely starts and
stops scheduled scanning). `inventory_last_push_scan_at` — canonical
read-only; the service writes it, so typing into it would only make the report
wrong.

### Not duplicated

Export Settings keeps `price_source_of_truth`, `media_source_of_truth` and
`product_export_domain_enabled`. Fulfillment Settings keeps the operating mode,
`fulfillment_mode_switch_nonce`, the switching state and the notification
confirmation. Setup progress, completion/rerun stamps and
`setup_readiness_stale_since` are rendered nowhere.

## 4. Action, menu and the row-ensure seam

- Canonical list and form on `shopify.connector.store.settings`, both
  `create="false" delete="false"`, list not inline-editable.
- One `ir.actions.act_window` binding both views through `view_ids`. This is
  load-bearing rather than tidy: four surfaces now share this model, and an
  action with no view reference falls back to `default_view()`, which orders by
  `priority,name,id`. Every view sits at the default priority, so the tie
  breaks on **name** — precisely the accident that made "Export Settings"
  render the fulfillment list until it was corrected.
- `group_ids` is the Odoo 19 field on `ir.actions.act_window`, verified at the
  pinned commit (`odoo/addons/base/models/ir_actions.py:329`), not assumed.
- The Administrator-gated **Configuration** menu already existed
  (`menu_shopify_connector_configuration`); Store Settings hangs off it rather
  than creating a second branch.

### The seam, and why the order is the argument

`action_open_canonical_store_settings`:

1. reasserts the Connector Administrator role **on the server** — the menu gate
   and `group_ids` are chrome, and a direct RPC reaches the method regardless;
2. resolves stores in the **caller's ordinary environment**, where the
   fail-closed SEC-3 company rule (`[('company_id', 'in', company_ids)]`) is
   live;
3. re-checks `check_access('read')` and **refuses** if anything outside the
   caller's active companies got through;
4. only then elevates, and only to ensure rows for that fixed set.

`sudo()` does **not** keep record rules running — Odoo bypasses them under
elevation. So the property defended is not "the rules still apply"; it is that
the authorized set is fixed **before** elevation and can only shrink after.
`_ensure_canonical_settings_rows` takes a recordset and never searches for a
store, so discovery cannot happen under elevation by construction.

**A refusal, not a filter.** Step 3 raises rather than quietly dropping
records. The company rule already excluded them, so a silent `filtered()`
would be a no-op that passes every test while absorbing a widened resolution
without a sound. This was found by mutation, not by inspection: with a filter,
replacing the ordinary-environment search with a `sudo()` one broke **nothing**
— the isolation test passed either way, so it was not evidence. With the
refusal, the same mutation breaks four tests.

Row ensure is idempotent, and a concurrent opener is contained: `UNIQUE(store_id)`
is the arbiter, each create sits in its own savepoint, and losing the race is a
no-op because the winner's row is exactly the row the call wanted to exist.

## 5. Write and readiness behaviour

All saves go through the ordinary model write path, so every existing
constraint stays load-bearing — store/company agreement, order-company
agreement, import window and scope, pending expiry, pricelist/team/payment-term
company, fallback-customer company, and the unique-row guard. None was weakened
to make the form save.

The readiness-relevant-field hook is derived from
`shopify.connector.readiness.check._accepted_domain_flags()` — the same
registry the readiness checks are computed over — rather than a second tuple
beside it. The two would drift: Product Export **already** extends that
registry with `product_export_domain_enabled`, so a copied tuple would have
gone on reporting a store as freshly-checked after a merchant enabled catalog
export. It remains overridable, so a domain extends it for fields its own
checks consume.

- A meaningful change marks readiness stale through the existing
  `_mark_setup_readiness_stale()` service.
- A no-op write does not — the comparison is against the stored value, not the
  presence of a key in `vals`.
- An unrelated canonical-editable setting (`log_redaction_retention_days`) does
  not.
- The nested marker write terminates because `setup_readiness_stale_since` is
  not readiness-relevant. That is a property of the **field partition**, not a
  re-entrancy flag somebody has to keep correct — and breaking the partition
  breaks the test that claims it.

## 6. Security and company invariants (checkpoint 1 scope)

1. UI visibility is not authorization — the server role assertion is the control.
2. Store/company scope is established as the original caller, before elevation.
3. Elevation is minimal, record-scoped, and never used for target discovery.
4. No existing settings ACL or company rule was widened. Settings access is
   unchanged: Auditor/Operator/Reviewer read; Administrator read+write, no
   create, no unlink.
5. A company-less historic store — invisible under the fail-closed rule — is
   never adopted.
6. No new durable model, so no new ACL or company rule was required.
7. Zero Shopify contact and zero Shopify mutation: this checkpoint adds no
   transport code path at all.

## 7. Migrations

None. Checkpoint 1 is views, one server seam, and a `write()` override — no
schema change, so no migration script. No empty script was created to satisfy
a counter, and the genuine-upgrade runner was not weakened.

Module versions moved by coherent patch bumps for the four touched modules:
`core 19.0.1.17.0 → 19.0.1.18.0`, `product 19.0.2.4.0 → 19.0.2.5.0`,
`sale 19.0.2.4.0 → 19.0.2.5.0`, `inventory 19.0.1.5.0 → 19.0.1.6.0`.

## 8. Tests, and their load-bearing proof

31 new test methods: **20 core, 3 product, 4 sale, 4 inventory** — counted
from the test files themselves, not from `odoo.tests.stats`, whose per-module
figures include fixtures and do not sum to the selected total.

Each central claim was proved **against its own absence** by mutating the
production code and confirming the specific test that claims it fails:

| Mutation | Result |
| --- | --- |
| Server-side role assertion removed from the seam | `test_non_administrator_direct_call_is_refused` fails (1) |
| Readiness staleness call removed from `write()` | `test_a_meaningful_change_marks_readiness_stale` fails (1) |
| Every written field treated as readiness-relevant | no-op guard, unrelated-setting and **non-recursion** tests fail (3) |
| `readonly="1"` removed from a canonical read-only field | classification test fails (1) |
| `except IntegrityError` no longer catches the unique violation | concurrent-winner test errors (1) |
| Ordinary-environment store search replaced with `sudo()` | 4 tests error — **and 0 before the refusal replaced the filter** |

The last row is the one worth reading twice: it is the case where the first
version of the test proved nothing, and mutation is what said so.

## 9. Definitive validation

Recorded in `docs/05-qa/evidence/batch-2-p0-merchant-reachability-2026-07-30/`.

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

## 10. Deferred, explicitly

**Not started in this session:** checkpoint 2 in full (order manual/scheduled
controls, the tax blocked-work decision route and workspace, their tests) and
checkpoint 3 in full (product scan producer, cron, checkpointing, durable
product/variant match decisions, their tests). Also not started: the
consolidated vertical journeys (C, D-P0, I, J-P0, K-P0), the consolidated
browser/accessibility campaign, and their runner-inventory registration.

**Deferred beyond Batch 2, per §17:** standalone customer import/refresh;
ambiguous customer matching decisions; bulk `Prepare changed products`;
feature-derived scope narrowing; per-domain operating-mode declarations;
per-store/per-domain dashboard liveness; consolidated attention/recovery;
Fulfillment Settings residuals; reconnect discoverability; journey families F,
G and H; governed tax remap. TD-004, TD-005 and TD-007 are retained unchanged.

## 11. Gates that remain

Independent Claude review of this exact head (the implementing session does not
review, accept, ready-mark or merge); checkpoints 2 and 3; the consolidated
journeys and browser campaign; exact-head Odoo.sh qualification; controlled
live-Shopify validation; business UAT; control-room acceptance and merge
authorization. PR #204 stays draft.
