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

## 3. Complete model classification — 35 models, none unclassified

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

### 3.2 Additional business-record rules retained (7)

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
| `shopify.connector.attribute.lock` | A **single seeded row** used only as a PostgreSQL mutex anchor (`_acquire_or_raise`, `FOR UPDATE SKIP LOCKED`). It holds no business data, is never created/written/unlinked at runtime, and reveals nothing about any store or company. Locking it tells a caller nothing except that someone else is importing attributes. |

This is the only place in the connector where "company-neutral" survives
examination. Everywhere else the previous revision used it, it meant
"we did not model ownership".

### 3.4 TRANSIENT wizards (2)

| Model | Classification |
| --- | --- |
| `shopify.connector.job.cancel.wizard` | operator/admin ACL; acts on a job the user could already reach — and *reaching* a job is now company-scoped |
| `shopify.connector.mutation.resolution.wizard` | **admin-only ACL**; acts on an attempt the user could already reach, likewise company-scoped |

**Inference.** A transient wizard stores no durable cross-company data, and both
resolve their target through a model that is now company-scoped, so neither can
be used to reach a row its caller could not already read. Neither needs its own
rule; the scoping happens one level down, which is where the durable data lives.

### 3.5 ABSTRACT services and mixins (14)

`api.client`, `binding.mixin`, `customer.importer`, `fulfillment.service`,
`inventory.service`, `job.dispatch`, `job.enqueue`, `order.importer`,
`order.scan`, `pii.retention`, `product.importer`, `readiness.check`,
`stale.owner.sweep`, `ui.dashboard`.

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
