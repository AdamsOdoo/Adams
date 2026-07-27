# SEC-3 — Cross-company isolation audit of the current connector backend

> **Status:** `[Inference + Decision — implemented for the current backend]`.
> Answers the audit required by [issue #197](https://github.com/AdamsOdoo/Adams/issues/197)
> for the **merged** backend surface (core, product, sale, inventory,
> fulfillment). **Date:** 2026-07-25.
> **This document does not accept SEC-3.** #197 is explicitly gated on external
> UAT / release-candidate qualification and stays open until exact-SHA runtime
> evidence and an independent Tier-1 security review exist.
> **Scope note:** the UI delta (Wave 5 U1) is *not* covered here — it does not
> exist yet. This audit covers the current backend only, which is exactly what
> the pre-Wave-5 stabilization gate asks for.

> ## Supersession notice — 2026-07-25 (control-room correction)
>
> **An earlier revision of this document classified nine connector
> control-plane models as `NEUTRAL` and asserted that a connector store
> deliberately carries no `company_id`.** Under that model, two users in
> different companies could read the same store, credential status, settings,
> locations, jobs, logs, attempts and leases. The control room ruled that this
> **does not satisfy #197**, which requires proving that no cross-company read
> is possible through *stores, settings, credentials, locations, jobs and logs,
> mutation attempts and leases, evidence and bindings, mappings, dashboards,
> wizards and direct methods*.
>
> The neutrality classification is **withdrawn**. It is preserved below only as
> §7, as a record of what was wrong and why it survived review, because that is
> the more useful artifact than a silent edit.

## 1. Method

Classification: **Fact** where it states a source-verified property, **Inference**
where it states a consequence.

The model list was taken from the **live Odoo 19 registry** of an installed
database (all five connector modules plus `account` and `stock`), not from
grepping source, so no model can be missed through a naming convention. For each
model the audit recorded: storage kind, every `many2one` to a company-bearing
non-connector model, its ACL rows, and its record rules.

Upstream ground truth (DEC-041 D1), `odoo/odoo@19.0` commit
`30bde9ff758834a4912c5ae55843d3a7dad849f1`, read 2026-07-25:

- `odoo/addons/base/models/ir_rule.py::_eval_context` exposes `company_ids` —
  `self.env.companies.ids`, the **multi-company switcher selection**, described
  in that source as "filtered and trusted" — to a record-rule domain.
- `ir_rule.py::_compute_global` — a rule with no `groups` is *global* and is
  **AND-ed** with every other rule on the model. A permissive group rule
  therefore cannot re-open what a global rule closes.
- `odoo/orm/models.py` L451 (`_check_company_auto`), L4009 (`_check_company`),
  L4516 (create) and L4743 (write) — when a model sets `_check_company_auto`,
  create and write call `_check_company`, which requires the target of every
  `check_company=True` relation to have a company of `False` or equal to the
  record's own company.
- `sudo()` bypasses record rules and ACLs entirely — which is exactly why the
  write-side company invariant is implemented as a **constraint**, not a rule
  (§4.4).

## 2. Ownership model (control-room MVP decision, 2026-07-25)

**A connector store belongs to exactly one Odoo company.**

| Rule | Consequence |
| --- | --- |
| A store belongs to exactly ONE company | `shopify.connector.store.company_id`, a `Many2one` — not a `Many2many`, so store sharing cannot arrive by accident |
| A company may own MANY stores | no uniqueness constraint on `company_id` |
| Sharing one store across companies is **outside the MVP** | never implemented implicitly; a cross-company binding is refused, not silently allowed |
| Isolation is **fail-closed** | a row whose owner cannot be proven is visible to **nobody** |
| `sudo()` does not authorize widening | the write-side invariant is an `@api.constrains`-class check, which fires under `sudo()` too |

Company enters the connector at exactly **one** place: the store. Every durable
store-scoped row derives its company from the store through a **stored related**
`company_id`, so there is one ownership decision per store and no second source
of truth that can drift.

### 2.1 Why the rules are not the usual Odoo shape

The standard Odoo multi-company rule is:

```python
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
```

which means *a NULL company is shared with everyone*. That is right for a
company-neutral price list and **wrong** for connector control-plane data: a
store, credential or job with no company is a row whose ownership we could not
prove, and the safe reading of "unknown owner" is "nobody sees it". Every rule
added here is therefore:

```python
[('company_id', 'in', company_ids)]
```

with no NULL escape.

### 2.2 Upgrade-safe disposition for historic stores

`company_id` is deliberately **not** `required=True` at the ORM level: a required
field would make the warm `-u` update of a database that already holds stores
fail outright, and Odoo would leave the column nullable anyway. Ownership is
enforced at two points an upgrade cannot bypass:

1. **create-time** — `_check_company_assigned`, an `@api.constrains`, refuses a
   store with no company (and fires under `sudo()`);
2. **read-time** — the fail-closed record rule.

Backfill happens on every install/update, and only where the answer is
**provable**:

| Evidence | Action |
| --- | --- |
| the database has exactly one company | assign it — it is the only possible owner |
| the store's `order_company_id` is already configured (`shopify_connector_sale`) | adopt it — a record of what *was*, not a guess |
| neither | **do not guess.** The store keeps a NULL company, is invisible to every interactive user, and a warning naming the exact store ids is logged |

The remediation path is `shopify.connector.store.action_assign_company`:
Administrator-gated, resolves the invisible row by explicit id under `sudo()`,
validates the target company against the caller's own `company_ids` rather than
trusting the value passed in, and **refuses to re-home a store that already has
an owner**. Fresh install, warm update, uninstall and reinstall all remain safe
because the field is additive and the backfill is idempotent.

## 3. Complete model classification — 37 models, none unclassified

> **2026-07-27 delta.** Two models were added by the TD-015 operator-resolution
> and S1 guided-setup batch. Both are classified below and both are recorded in
> §8, which states this cycle's complete surface delta. The count moved from 35
> to 37; nothing was reclassified.

### 3.1 STORE-OWNED — company derived from `store_id.company_id` (17)

Every one carries a stored related `company_id` and a fail-closed rule
`[('company_id', 'in', company_ids)]`.

| Model | Company path | Rule |
| --- | --- | --- |
| `shopify.connector.store` | **own `company_id` (the root)** | `store_company_rule` |
| `shopify.connector.store.credential` | `store_id.company_id` | `store_credential_company_rule` |
| `shopify.connector.store.settings` | `store_id.company_id` | `store_settings_company_rule` |
| `shopify.connector.location` | `store_id.company_id` | `location_company_rule` |
| `shopify.connector.job` | `store_id.company_id` | `job_company_rule` |
| `shopify.connector.job.log` | `store_id.company_id` | `job_log_company_rule` |
| `shopify.connector.mutation.attempt` | `store_id.company_id` | `mutation_attempt_company_rule` |
| `shopify.connector.call.lease` | `store_id.company_id` | `call_lease_company_rule` |
| `shopify.connector.customer.binding` | mixin `store_id.company_id` | `customer_binding_store_company_rule` |
| `shopify.connector.order.binding` | mixin `store_id.company_id` | `order_binding_store_company_rule` |
| `shopify.connector.product.template.binding` | mixin `store_id.company_id` | `product_template_binding_store_company_rule` |
| `shopify.connector.product.variant.binding` | mixin `store_id.company_id` | `product_variant_binding_store_company_rule` |
| `shopify.connector.location.mapping` | mixin `store_id.company_id` | `location_mapping_store_company_rule` |
| `shopify.connector.inventory.level.binding` | mixin `store_id.company_id` | `inventory_level_binding_store_company_rule` |
| `shopify.connector.fulfillment.binding` | mixin `store_id.company_id` | `fulfillment_binding_store_company_rule` |
| `shopify.connector.fulfillment.inbound.evidence` | `store_id.company_id` | `fulfillment_inbound_evidence_company_rule` |
| `shopify.connector.fulfillment.inbound.evidence.line` | `evidence_id.store_id.company_id` | `fulfillment_inbound_evidence_line_company_rule` |
| `shopify.connector.tax.mapping` | `store_id.company_id` | `tax_mapping_store_company_rule` |

### 3.2 Additional business-record rules retained (8)

The pre-existing rules that scope a connector row by the company of the Odoo
record it points at are **kept alongside** the store rules. Both are global, so
both must pass. They close different holes: the store rule proves ownership; the
business-record rule keeps a genuinely company-neutral product usable while
still preventing another company's product from being reached through a binding.

`product_template_binding_company_rule`, `product_variant_binding_company_rule`,
`customer_binding_company_rule`, `order_binding_company_rule`,
`tax_mapping_company_rule`, `location_mapping_company_rule`,
`inventory_level_binding_company_rule`, plus
`fulfillment_binding_picking_company_rule`.

### 3.3 GENUINELY NEUTRAL — exactly one model

| Model | Why neutrality is a proven fact here |
| --- | --- |
| `shopify.connector.attribute.lock` | A **single seeded row** used only as a PostgreSQL mutex anchor (`_acquire_or_raise`, `FOR UPDATE SKIP LOCKED`). It holds no business data, is never created/written/unlinked at runtime, and reveals nothing about any store or company. Locking it tells a caller nothing except that someone else is importing attributes. Its ACL is read-only for exactly one group and grants **no** create/write/unlink to anyone (`ir.model.access.csv`: `1,0,0,0`), so it cannot be renamed or removed either. |

**Deviation recorded deliberately.** The correction brief lists "attribute
locks" among the records that should inherit the store's company. This model is
the one place that instruction is **not** followed, and the reason is
functional rather than convenient: the lock is *global by design*. Attribute
creation is serialized across the whole database because Odoo product
attributes are themselves global; that is the invariant the lock exists to
protect. Attaching a company would mean either keeping one row (no isolation
gained, since a single row cannot be scoped to two companies at once) or
creating one row per company — which would silently **change production
locking semantics**, permitting two companies to create the same global
attribute concurrently. That is a behavioural change well outside "the smallest
coherent ownership correction", and it would reintroduce the duplicate-attribute
race the lock was built to prevent. It is therefore left neutral, with the
reasoning recorded here rather than decided silently.

This is the only place in the connector where "company-neutral" survives
examination. Everywhere else the previous revision used it, it meant
"we did not model ownership".

### 3.4 TRANSIENT wizards (5)

| Model | Classification |
| --- | --- |
| `shopify.connector.job.cancel.wizard` | operator/admin ACL; acts on a job the user could already reach — and *reaching* a job is now company-scoped |
| `shopify.connector.mutation.resolution.wizard` | **admin-only ACL**; acts on an attempt the user could already reach, likewise company-scoped |
| `shopify.connector.product.export.request.wizard` | operator/admin ACL; resolves a `product.template` and a store the caller can already read |
| `shopify.connector.product.export.confirm.wizard` | reviewer/admin ACL; resolves a preview the caller can already read |
| `shopify.connector.export.checksum.ack.wizard` (**2026-07-27**) | **admin-only ACL**; resolves a `shopify.connector.product.template.binding` the caller can already read, and delegates entirely to `action_shopify_export_acknowledge_checksum`, which re-checks the Administrator role, record access and company consistency itself |

**Inference.** A transient wizard stores no durable cross-company data, and both
resolve their target through a model that is now company-scoped, so neither can
be used to reach a row its caller could not already read. Neither needs its own
rule; the scoping happens one level down, which is where the durable data lives.

### 3.5 ABSTRACT services and mixins (14)

`api.client`, `binding.mixin`, `customer.importer`, `fulfillment.service`,
`inventory.service`, `job.dispatch`, `job.enqueue`, `order.importer`,
`order.scan`, `pii.retention`, `product.importer`, `readiness.check`,
`stale.owner.sweep`, `ui.dashboard`, `product.export.ui`,
`export.reconcile.service`, `media.export.service`,
`product.export.service`, `setup.wizard` (**2026-07-27**).

**Fact.** An abstract model has no table and no rows, so it cannot hold or leak a
record. Record rules do not apply. Their isolation obligation is discharged by
the `sudo()` seam classification in §5 and by the constraint in §4.4.

**Note on `ui.dashboard`.** The dashboard aggregates over
`shopify.connector.job` and `shopify.connector.store` as the *calling user*, not
under `sudo()`, so its aggregates are now company-scoped automatically. This is
asserted directly (`test_grouped_read_does_not_leak_another_company`) rather than
argued, because an aggregate is the classic way a scoped `search` still leaks.

## 4. Confirmed findings

### 4.1 FINDING SEC3-1 — cross-company READ leak on connector bindings (corrected)

Before the first batch, only 2 of the 10 then-company-scoped models carried a
record rule. An interactive user in company A could `search`/`read` connector
binding and mapping rows pointing at company B's partners, sale orders, products,
taxes and stock locations.

**Why it was not caught earlier (Inference).** The connector's *write* paths were
already fail-closed on company (`order_binding.py` L190-L192,
`location_mapping.py` L157, `inventory_service.py` L1954,
`inventory_level_binding.py` L155-L156, and the importer's company-scoped tax /
pricelist / product lookups). Those guards are real, and they are why four waves
of review saw company checks everywhere and concluded the surface was covered.
They simply do not constrain **reads**.

### 4.2 FINDING SEC3-2 — the inventory pair needs both parents scoped

`shopify.connector.inventory.level.binding` reaches business company through
`product_variant_binding_id` **and** `location_mapping_id`. Scoping on either
alone leaks the other half of the pair, so that rule is an AND. It now also
carries the store rule, which is the simpler and stronger of the two.

### 4.3 FINDING SEC3-3 — `order_company_id` was a second ownership selector (**corrected**)

**Superseded resolution.** The previous revision classified
`shopify.connector.store.settings` as NEUTRAL and left as an open product
question whether an administrator in company A could set `order_company_id` to
company B. The control room ruled that this contradiction may not be left open.

**Resolution.** `order_company_id` must agree with `store_id.company_id`:

- `_check_order_company_matches_store` (an `@api.constrains`) refuses any
  settings row whose order company is not the owning store's company;
- `create()` derives it from the store on every ORM path, and `default_get`
  derives it from `default_store_id` for the UI, so it is correct by
  construction rather than by the acting user's active company;
- the pre-existing guard — order company may not change once an order binding or
  tax mapping exists — is **kept**, because it protects a different thing
  (retroactive re-homing of already-imported data).

It is deliberately **not** converted into a related field: a related field's
inverse would write through and silently re-home the **store**, which is exactly
what the MVP decision forbids.

### 4.4 The write-side invariant is a constraint, not a rule

`sudo()` bypasses record rules by design, and connector system code runs under
`sudo()` constantly. A company invariant expressed only as a record rule would
therefore be absent from precisely the code paths that create data.

Every binding now opts into Odoo's native machinery — `_check_company_auto =
True` plus `check_company=True` on its business relation — so **a store may only
bind a business record of its own company, enforced on create and on write, and
under `sudo()`**. Verified directly:
`test_sudo_does_not_let_an_interactive_caller_widen_company`.

## 4.5 Relational closure — same-STORE agreement (2026-07-25 correction)

Company equality is not sufficient for a row that points at another connector
row, because **one Odoo company may own several Shopify stores**. Two stores in
one company pass every company check while being two different shops. A record
rule cannot express the requirement at all: a domain cannot compare two of a
record's own fields, so there is no `('store_id', '=', 'job_id.store_id')` to
write.

`shopify.connector.scope.mixin` closes it in two parts:

* **New and updated rows** — an `@api.constrains` per model, calling
  `_sec3_check_parent_scope()`. A constraint, not a rule, because constraints
  fire under `sudo()` and every connector write path uses `sudo()` somewhere.
* **Historic rows** — an `init()`-time sweep that sets `sec3_scope_quarantined`,
  which every fail-closed rule now excludes. It **never guesses**: re-homing the
  row to its parent's store, or the parent to the row's, are both plausible and
  both destructive. The ids are logged, the rows are hidden, nothing is moved.
  `action_sec3_release_scope_quarantine` is the Administrator-gated remediation,
  and it re-runs the check before clearing rather than trusting the caller.

### Relation-by-relation result

| Relation | Status before | Now |
| --- | --- | --- |
| `job.mutation_attempt_id` | already constrained | declared, so the historic sweep covers it too |
| `job.superseded_by_job_id` | **unconstrained** | constrained + swept. *Found by the new completeness guard, not by reading the model* |
| `job.log.job_id` | structurally closed | recorded — `store_id` is `related('job_id.store_id')`, so it cannot disagree |
| `mutation.attempt.job_id` | structurally closed | recorded — same reason |
| `product.variant.binding.product_template_binding_id` | **unconstrained** | constrained + swept |
| `inventory.level.binding.product_variant_binding_id` | already constrained | declared, swept |
| `inventory.level.binding.location_mapping_id` | already constrained | declared, swept |
| `fulfillment.binding.order_binding_id` | already constrained | declared, swept |
| `evidence.order_binding_id` | **unconstrained** | constrained + swept |
| `evidence.fulfillment_binding_id` | **unconstrained** | constrained + swept |
| `evidence.line.evidence_id` | structurally closed | recorded — `company_id` is related through this very field |
| `evidence.line.sale_line_id` | **unconstrained** | constrained on the COMPANY axis (a sale order has no store); a historic mismatch quarantines the parent evidence, so the observation and its ledger stay hidden together |
| `call.lease.job_id` | — | **not closable**: it is an `Integer`, not a `Many2one`, so there is no FK to check. Recorded as D-33 for the Wave-5 schema review |

Two things are stated plainly rather than glossed:

1. **Five relations were genuinely open** — variant→template binding,
   evidence→order binding, evidence→fulfillment binding, evidence line→sale
   line, and `job.superseded_by_job_id`. The rest were already closed, or
   closed by construction. Claiming twelve new protections would overstate what
   changed.
2. **`order.binding.fulfillment_binding_id` does not exist.** An earlier draft
   of this audit listed it. The relation runs the other way —
   `fulfillment.binding.order_binding_id` — and was already constrained.

### What the completeness guard enforces

`TestSec3InventoryCompleteness` fails when:

* a durable store-scoped model exists in the registry with no entry in the test
  inventory (so a new model cannot be added without a fixture and both a
  positive and a negative proof);
* a covered model has no `company_id`, or its company rule is not global, or the
  rule contains a `company_id = False` escape hatch;
* a connector-to-connector `Many2one` exists that no `_sec3_parent_scope_relations`
  declaration covers, and that is not on the recorded structurally-safe list;
* the field that makes a "structurally safe" relation safe stops being a
  `related` field.

## 5. `sudo()` seam classification — 177 call sites, re-audited against the store-company root

Every `sudo()` in connector production code was re-examined against the question
the control room posed: *can this seam turn a store id the caller cannot read
into data the caller can read, or attach another company's record to this store?*

| Seam family | Sites | Classification against the new root |
| --- | --- | --- |
| Job / dispatch / enqueue / log / lease writes | ~60 | **Sanctioned.** Operate on rows reached *from a store the caller already resolved*. The store resolution itself is now company-scoped, so the seam inherits the scope rather than escaping it. |
| Mutation attempt intent/outcome/reconciliation | ~20 | **Sanctioned.** Layer-2 evidence; protected-field writes are why `sudo()` is required. Company is derived from the job's store, never supplied. |
| Binding create/write | ~45 | **Sanctioned and now constraint-guarded.** `_check_company` fires under `sudo()`, so these cannot attach a foreign-company record. |
| Credential read/write | 9 | **Sanctioned and least-privilege.** Admin-only ACL, values redacted in every log path, and the row is now company-scoped as well. |
| Store lifecycle / readiness / disconnect | ~21 | **Sanctioned.** Admin-gated at the action boundary via `_ensure_connector_admin_boundary`. |
| PII retention / stale-owner sweep | 8 | **Sanctioned.** Cron context; runs as the framework superuser by design, which is a *system* actor, not an interactive caller. |
| Inventory service quant/location reads | ~14 | **Sanctioned, company-guarded** (`inventory_service.py` L1954). |
| **SEC-3 ownership seams (new)** | 2 | `_backfill_company` reads `res.company` only to decide whether ownership is **provable**, and never writes a company it guessed. `action_assign_company` resolves a deliberately-invisible historic row by explicit id, is Administrator-gated, validates the target company against the **caller's own** `company_ids` rather than trusting the argument, and refuses to re-home an owned store. |

**Fact.** No seam accepts a caller-supplied company as authority. Both new seams
are registered in the source-level sudo inventory guard
(`test_credential_service.py::test_source_level_sanctioned_sudo_sites_guard`), so
adding an unrecorded `sudo()` to core fails the suite.

**Inference.** The seams are least-privilege in the sense #197 asks for: each
runs `sudo()` to cross a *protected-field* boundary the connector owns, not a
*company* boundary.

## 6. What this batch does NOT claim

- **SEC-3 is not accepted.** #197 stays open.
- No exact-SHA Odoo.sh runtime evidence exists for these rules yet; the local run
  is recorded in the PR #203 push record and is not a substitute.
- The **UI delta** (U1) is out of scope and needs its own pass once it exists.
- Historic records: the new rules apply to existing rows immediately because they
  are evaluated at read time, but **no audit of already-leaked data is possible
  or claimed**.
- Store sharing across companies is **not** implemented, by decision, not by
  omission.

## 7. Withdrawn: the previous NEUTRAL classification

Kept deliberately, because *why a wrong classification survived* is more useful
to the next reviewer than a clean edit.

The previous revision argued: a Shopify shop domain is not an Odoo legal entity,
the MVP excludes "complex multi-company", therefore the control plane carries no
company and a rule on it "would have no ownership expression to scope by and
would be security theatre".

**Where the reasoning failed.** The premise (a shop domain is not a legal entity)
is true and irrelevant. Ownership does not require that the two concepts be the
same kind of thing — it only requires that someone *owns* the store record, and
someone always does. Having declined to model the owner, the audit then read the
absence of a company field as evidence that no company scoping was needed, which
inverted an omission into a justification. The compensating controls it cited —
role ACLs, admin-only credential access — are real, but they are an
*authorization* axis; they say what a role may do, never which company's data it
may do it to.

**Lesson recorded for the quality loop:** "there is no field to scope by" is a
statement about the schema, never about the requirement. When an isolation audit
concludes that a class of records is neutral, the burden is to show that reading
them reveals nothing about another tenant — not that the model happens to lack a
company column.


---

## 8. 2026-07-27 delta — TD-015 operator resolution and S1 guided setup

This section is the exact surface this batch introduced or changed. It is
written as an inventory rather than a narrative so a reviewer can check it
item by item, and so a later batch cannot add a surface without the diff to
this table being visible.

**Status.** This is **implementation coverage**, not acceptance. Issue #197
remains open: it requires an independent Tier-1 security review and exact-SHA
runtime evidence before external UAT or release-candidate qualification, and
neither exists for this head. Nothing below claims otherwise.

### 8.1 New models

| Model | Kind | Durable? | Company path | Isolation |
| --- | --- | --- | --- | --- |
| `shopify.connector.setup.wizard` | AbstractModel | no table | n/a | No rows to leak. Every entry point checks the Administrator role, then `check_access('read')` on the store as the CALLING user, then `store.company_id in env.companies` — in that order, before any elevation. |
| `shopify.connector.export.checksum.ack.wizard` | TransientModel | per-session only | via `binding_id` | Admin-only ACL row. Owns no business rule; the authority is the binding method it calls, which repeats all three checks. |

Neither is a durable store-scoped model, so
`test_no_durable_store_scoped_model_escapes_this_matrix` correctly does not
require a row builder for either.

### 8.2 New stored fields

| Model | Field | Kind | Company path | Notes |
| --- | --- | --- | --- | --- |
| `shopify.connector.store.settings` | `setup_wizard_step` | Integer | inherited (stored related `company_id`) | Resume point. Written only by the setup service. |
| `shopify.connector.store.settings` | `setup_completed_at` / `setup_completed_uid` | Datetime / M2o `res.users` | inherited | Who finished setup, and when. |
| `shopify.connector.store.settings` | `setup_last_rerun_at` / `setup_last_rerun_uid` | Datetime / M2o `res.users` | inherited | Who re-ran it, and when. |
| `…product.template.binding` | `export_reconcile_reason` | Selection | mixin `store_id.company_id` | The machine-readable verdict. Protected binding field. |
| `…product.template.binding` | `export_reconcile_evidence_generation` / `_product_gid` / `_file_gids` / `_claim_digest` | Integer / Char ×3 | mixin | The evidence a verdict rests on. Protected. |
| `…product.template.binding` | `export_reconcile_ack_at` / `_uid` / `_reason` / `_generation` / `_product_gid` / `_file_gids` / `_claim_digest` / `_verdict_at` | Datetime, M2o `res.users`, Selection, Integer, Char ×3, Datetime | mixin | The acknowledgement and exactly what it accepted. All protected. |

Every binding field above is registered in
`_additional_protected_binding_fields`, so a generic non-superuser
`create()`/`write()` on any of them raises `AccessError`. That is not
cosmetic: they are precisely the values `_export_reconcile_ack_is_valid`
consults, so a writable one would BE the override the design forbids.

### 8.3 New relationships

| Owner | Field | Target | Stored? | Consistency |
| --- | --- | --- | --- | --- |
| `shopify.connector.store` | `export_reconcile_review_binding_ids` | `…product.template.binding` | **no** (computed Many2many) | Creates no column and no relation table. Computed by a store-scoped, `limit`-ed search that runs as the CALLING user, so the SEC-3 binding rules filter it. `depends_context=('uid', 'company', 'allowed_company_ids')` keys the field cache per user and per company selection — without it Odoo caches a non-stored computed field once per record for the whole transaction and the first reader's result is served to the second, in either direction. |
| `shopify.connector.store.settings` | `setup_completed_uid`, `setup_last_rerun_uid` | `res.users` | yes | Not connector-to-connector, so the same-store scope mixin does not apply; `res.users` is not a store-scoped model. |
| `…product.template.binding` | `export_reconcile_ack_uid` | `res.users` | yes | Same. |

No new connector-to-connector Many2one exists, so
`test_no_undeclared_connector_relation_exists` needs no new declaration —
and would fail if one were added silently.

### 8.4 New public / RPC-callable methods

| Method | Model | Authority | Company check |
| --- | --- | --- | --- |
| `get_setup_state` | setup service | Administrator | per resolved store |
| `save_store_identity` | setup service | Administrator | creates only into `env.company`, refused unless the caller belongs to it |
| `save_credential` | setup service | Administrator | per resolved store |
| `acknowledge_scopes`, `run_test_connection`, `run_readiness` | setup service | Administrator | per resolved store |
| `save_directions`, `save_source_of_truth`, `save_notification`, `save_first_push_schedule` | setup service | Administrator | per resolved store |
| `activate`, `save_and_exit`, `restart_setup`, `action_open_setup_wizard` | setup service | Administrator | per resolved store |
| `action_shopify_rerun_setup` | `shopify.connector.store` | Administrator (inside `restart_setup`) | per resolved store |
| `action_shopify_export_acknowledge_checksum` | template binding | **Administrator only** | `check_access('read')` + `store.company_id in env.companies` |
| `action_shopify_export_open_checksum_ack_wizard` | template binding | **Administrator only** | same, before the dialog opens |
| `action_confirm` | ack wizard | delegates | delegates |

### 8.5 New client payloads and UI routes

| Surface | Route | Payload discipline |
| --- | --- | --- |
| S1 client action `shopify_connector_setup_wizard` | Dashboard empty state · Configuration → Setup Wizard · store form "Re-run Setup" | One bounded read (`get_setup_state`). Carries `credential_present` as a boolean and **never** a token, fragment or length. Store list is a `limit=20` search as the caller. |
| TD-015 review list + acknowledgement | store form → *Bindings awaiting review* → *Acknowledge* → dialog | Bounded (`limit=200`) current-user search; the dialog reads only fields on a binding the caller can already read. |

`ir.actions.client` carries no `group_ids` in Odoo 19, so the setup action
cannot be group-restricted at all — which is exactly why every server method
enforces the role itself.

### 8.6 New elevated (`sudo()`) seams

Recorded in the exact-inventory guards
(`test_credential_service.py::CORE_SUDO_SITES`,
`test_readiness_slot_closure.py`, and the per-file budget in
`test_export_source_guards.py`), which fail on an unlisted addition.

| Seam | Why elevation is necessary | Checks before it |
| --- | --- | --- |
| `setup.wizard._settings_for` ×2 | no connector group holds `create` on `store.settings` | role, record access, company |
| `setup.wizard._record_progress` | resume point is a readonly column | as above |
| `setup.wizard._last_readiness_checks` ×2 | reads one job + one log row for the already-authorised store | as above |
| `setup.wizard.save_store_identity` ×2 | no connector group holds `create` on `shopify.connector.store` | role; company taken from `env.company` and refused unless the caller belongs to it |
| `setup.wizard.save_directions` / `save_source_of_truth` / `save_notification` / `save_first_push_schedule` / `activate` / `restart_setup` | settings write ACL is Administrator-only but `create` is not, and the progress columns are readonly | role, record access, company |
| `readiness.check._web_base_url` | system parameters are `base.group_system`; readiness runs as the connector administrator | called only from the readiness registry, which its callers gate |
| `export_reconnect._export_reconcile_media_claim` | reads the binding's own media rows so a record rule cannot silently shorten the claim and make a partial digest match | role, record access, company |
| `export_reconnect._export_reconcile_clear_acknowledgement` | ack fields are protected binding fields | as above, or a pass writing a fresh verdict |
| `export_reconnect.action_shopify_export_acknowledge_checksum` | writes those protected fields | role, record access, company, eligibility |
| `export_reconnect._reassert_export_reconcile_acknowledgements` ×2 | reads the store's own outstanding reviews and re-applies the block on readonly verdict fields | reached only from the store's own export assertion |

Actor attribution survives every one of them: the audit row is written through
`store._create_lifecycle_audit_job`, whose `job.log` append runs in the
CALLING user's environment, and `export_reconcile_ack_uid` / `setup_completed_uid`
store `env.uid` rather than the superuser.

### 8.7 Install, upgrade and historic records

* Every new stored field is additive with a safe default (`0`, `False`), so a
  warm `-u` update of a database that already holds stores and bindings needs
  no migration and none is added.
* `setup_wizard_step` defaults to `1`, so an existing store reads as
  "setup not yet walked" rather than as complete — the fail-safe direction.
* An existing store's settings row is reused rather than replaced;
  `_settings_for` creates one only when none exists.
* No new stored relation exists, so the SEC-3 historic quarantine sweep has
  nothing new to scan and no existing row's scope changes.
* Uninstall behaviour is unchanged: no new model is depended on by another
  module, and the two new models own no data that outlives a session
  (transient) or a request (abstract).

### 8.8 What this delta does NOT claim

* SEC-3 is **not** accepted, and **#197 stays open**.
* No Tier-1 independent security review of this head exists.
* No exact-SHA Odoo.sh runtime evidence exists for this head.
* The local two-company/two-role negative matrix is green, and local green is
  supporting evidence, not acceptance.
