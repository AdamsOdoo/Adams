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

- `ir.rule._eval_context` exposes `company_ids` — the **multi-company switcher
  selection**, not every allowed company — to a record-rule domain.
- `ir.rule` marked `global` applies to all groups; non-global rules are OR-ed
  within a group and AND-ed across groups.
- `sudo()` bypasses record rules and ACLs entirely, so system code is
  unaffected by anything in this audit.

## 2. Ownership model

**A connector store is not an Odoo company.** `shopify.connector.store` carries
no `company_id` and none is being added: one Shopify shop domain does not map
onto an Odoo legal entity, and MVP scope explicitly excludes "complex
multi-company" (`mvp-completion-program.md` §3).

Company therefore enters the connector at exactly one kind of seam: **a
connector row that points at a company-bearing Odoo record.** Those rows are
scoped to the company of the record they point at. Everything else is
`NEUTRAL` — store-scoped control-plane data that carries no company at all.

## 3. Complete model classification — 35 models, none unclassified

### 3.1 COMPANY-SCOPED — stored, reaches a company-bearing Odoo record (8)

| Model | Company path | Record rule | Status |
| --- | --- | --- | --- |
| `shopify.connector.customer.binding` | `partner_id.company_id` | `customer_binding_company_rule` | **added by this batch** |
| `shopify.connector.order.binding` | `sale_order_id.company_id` | `order_binding_company_rule` | **added by this batch** |
| `shopify.connector.product.template.binding` | `product_template_id.company_id` | `product_template_binding_company_rule` | **added by this batch** |
| `shopify.connector.product.variant.binding` | `product_variant_id.company_id` | `product_variant_binding_company_rule` | **added by this batch** |
| `shopify.connector.tax.mapping` | `account_tax_id.company_id` | `tax_mapping_company_rule` | **added by this batch** |
| `shopify.connector.location.mapping` | `odoo_location_id.company_id` | `location_mapping_company_rule` | **added by this batch** |
| `shopify.connector.inventory.level.binding` | both parents (§4.2) | `inventory_level_binding_company_rule` | **added by this batch** |
| `shopify.connector.fulfillment.inbound.evidence.line` | `sale_line_id.company_id` | `fulfillment_inbound_evidence_line_company_rule` | **added by this batch** |

### 3.2 COMPANY-SCOPED — already covered before this batch (2)

| Model | Company path | Record rule |
| --- | --- | --- |
| `shopify.connector.fulfillment.binding` | `picking_id.company_id` | `fulfillment_binding_company_rule` (Wave 4) |
| `shopify.connector.fulfillment.inbound.evidence` | `order_binding_id.sale_order_id.company_id` | `fulfillment_inbound_evidence_company_rule` (Wave 4) |

### 3.3 NEUTRAL — store-scoped control plane, no company relation (9)

Verified to have **no** `many2one` to any company-bearing non-connector model
other than actor/audit `*_uid` fields, which record *who acted* and are not an
ownership path.

| Model | Why neutral | Compensating control |
| --- | --- | --- |
| `shopify.connector.store` | the store is the scope root | admin-only write ACL |
| `shopify.connector.store.credential` | secret material, store-scoped | **admin-only ACL, no read for any other role** |
| `shopify.connector.store.settings` | store-scoped configuration | admin-only write; see §4.3 for its optional company-bearing pointers |
| `shopify.connector.location` | Shopify-side location cache | read-only for all roles |
| `shopify.connector.job` | connector control plane | role ACL matrix |
| `shopify.connector.job.log` | connector audit trail | read-only for all roles; redaction enforced |
| `shopify.connector.mutation.attempt` | Layer-2 evidence | read-only for all roles |
| `shopify.connector.call.lease` | transport lease | admin-only |
| `shopify.connector.attribute.lock` | import serialization lock | operator read-only |

**Inference.** These carry no company, so a company record rule on them would
have no ownership expression to scope by and would be security theatre. They are
protected by the role ACL matrix and, for credentials, by an admin-only ACL that
denies read to every other role.

### 3.4 TRANSIENT wizards (2)

| Model | Classification |
| --- | --- |
| `shopify.connector.job.cancel.wizard` | operator/admin ACL; acts on a job the user could already reach |
| `shopify.connector.mutation.resolution.wizard` | **admin-only ACL**; acts on an attempt the user could already reach |

**Inference.** A transient wizard stores no durable cross-company data. Both
resolve their target through a model that is itself ACL-protected, so they add
no new isolation seam. Neither needs a company rule.

### 3.5 ABSTRACT services and mixins (14)

`api.client`, `binding.mixin`, `customer.importer`, `fulfillment.service`,
`inventory.service`, `job.dispatch`, `job.enqueue`, `order.importer`,
`order.scan`, `pii.retention`, `product.importer`, `readiness.check`,
`stale.owner.sweep`, `ui.dashboard`.

**Fact.** An abstract model has no table and no rows, so it cannot hold or leak a
record. Record rules do not apply. Their isolation obligation is discharged by
the `sudo()` seam classification in §5 and by the server-side company guards in
§4.

## 4. Confirmed findings

### 4.1 FINDING SEC3-1 — cross-company READ leak on connector bindings (corrected)

**Severity: material P2 for external UAT / RC. Not a P0/P1 for the current
single-company program state, and it blocks nothing before Wave 5.**

Before this batch, only 2 of the 10 company-scoped models carried a record rule.
An interactive user in company A could `search`/`read` connector binding and
mapping rows pointing at company B's partners, sale orders, products, taxes and
stock locations — exposing Shopify GIDs, match keys, snapshots and sync state
for another company's data.

**Why it was not caught earlier (Inference).** The connector's *write* paths are
already fail-closed on company:

- `shopify_connector_order_binding.py` L190-L192 rejects a sale order whose
  company is not `self.env.company`;
- `shopify_connector_location_mapping.py` L157 rejects a location outside
  `self.env.company`;
- `shopify_connector_inventory_service.py` L1954 makes the same check;
- `shopify_connector_inventory_level_binding.py` L155-L156 refuses a pair whose
  product and location disagree on company;
- `shopify_connector_order_importer.py` scopes taxes, pricelists and products to
  `settings.order_company_id`.

Those guards are real and remain the write-side authority. They simply do not
constrain **reads**, and record rules are the only mechanism that does.

**Correction.** Eight global record rules, one per company-scoped model, in the
module that owns the model. See §3.1.

### 4.2 FINDING SEC3-2 — the inventory pair needs both parents scoped

`shopify.connector.inventory.level.binding` has no direct company relation; it
reaches company through `product_variant_binding_id` **and**
`location_mapping_id`. Scoping on either alone would leak the other half of the
pair. The rule requires **both** to be visible.

### 4.3 FINDING SEC3-3 — `store.settings` company pointers are configuration, not ownership

`shopify.connector.store.settings` holds optional pointers at company-bearing
records (`customer_fallback_partner_id`, `order_pricelist_id`,
`order_sales_team_id`, `order_payment_term_id`) plus the explicit
`order_company_id`.

**Classified NEUTRAL, deliberately.** These are *configuration choices about
which company to import into*, not evidence of a company owning the settings
row. Scoping the settings record itself by them would hide a store's whole
configuration from an administrator whose current company differs from the
import target — a usability regression, not a security gain. The existing
`_check_company`-style constraints in `shopify_connector_store_settings.py`
L100-L128 already refuse a pricelist/team/payment-term that disagrees with
`order_company_id`, which is the invariant that actually matters.

**Open item.** Whether an administrator in company A should be able to *set*
`order_company_id` to company B is a product decision, not a defect. Recorded as
an open question, not corrected here.

### 4.4 No cross-company defect found in the `sudo()` seams

See §5. No seam was found that widens company scope on behalf of an interactive
user.

## 5. `sudo()` seam classification — 177 call sites

Every `sudo()` in connector production code was classified. None is a
cross-company escalation path, for one structural reason:

**Fact.** The connector's `sudo()` seams operate on **connector-owned,
store-scoped** rows (jobs, logs, attempts, leases, bindings) reached from a
store the caller already resolved, or on Odoo business records the caller
already holds a reference to. No seam takes a user-supplied company, and no seam
re-reads a company-bearing record with a *widened* company context.

| Seam family | Sites | Classification |
| --- | --- | --- |
| Job / dispatch / enqueue / log / lease writes | ~60 | **Sanctioned.** Connector control plane; store-scoped; no company expression exists to widen. |
| Mutation attempt intent/outcome/reconciliation | ~20 | **Sanctioned.** Layer-2 evidence; protected-field writes are exactly why `sudo()` is required. |
| Binding create/write (product, customer, order, inventory, fulfillment) | ~45 | **Sanctioned, and now read-scoped.** Writes remain guarded by the fail-closed company checks in §4.1; reads by interactive users are constrained by the new rules. |
| Credential read/write | 9 | **Sanctioned and least-privilege.** Admin-only ACL; values redacted in every log path. |
| Store lifecycle / readiness / disconnect | ~21 | **Sanctioned.** Store-scoped; admin-gated at the action boundary. |
| PII retention / stale-owner sweep | 8 | **Sanctioned.** Cron-context maintenance over store-scoped rows. |
| Inventory service quant/location reads | ~14 | **Sanctioned, company-guarded.** `inventory_service.py` L1954 fails closed when the location's company is not the current company. |

**Inference.** The seams are least-privilege in the sense #197 asks for: each
runs `sudo()` to cross a *protected-field* boundary the connector itself owns,
not to cross a *company* boundary.

## 6. What this batch does NOT claim

- **SEC-3 is not accepted.** #197 stays open.
- No exact-SHA Odoo.sh runtime evidence exists for these rules yet; the local
  run is recorded in the PR #203 push record and is not a substitute.
- The **UI delta** (U1) is out of scope and will need its own pass once it
  exists, as #197 states.
- Historic records: the new rules apply to existing rows immediately because
  they are evaluated at read time, but no audit of *already-leaked* data is
  possible or claimed.
- `order_company_id` cross-company selection (§4.3) remains an open product
  question.
