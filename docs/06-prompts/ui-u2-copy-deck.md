# UI U2 — Copy Deck

> **Status: Evidence record of copy that is SHIPPED on this branch. Docs.
> NOT an acceptance, NOT a review, NOT a runtime or UAT claim.** Produced on
> `fable/wave-5-completion` by the implementing session. Per CLAUDE.md §13 that
> session may not review or accept its own work, and this file accepts nothing.
>
> Required by
> [`ui-implementation-phases-packet.md`](../07-implementation-plan/ui-implementation-phases-packet.md)
> §8.1 (`ALLOWED FILES: … docs/06-prompts/ui-u2-copy-deck.md`). Its absence was
> recorded as an open gap in
> [`ui-u3-validation-results.md`](../05-qa/ui-u3-validation-results.md) §5.7;
> this closes that gap.

---

## 0. What this file is, and what it is not

`[Fact]` **Every string below was read out of the shipped source at this
head, not proposed.** Each row carries the exact file and the exact wording.
If a string is not in the source, it is not in this deck.

`[Fact]` **This deck does not claim translation coverage.** The connector ships
no `.po` file and no `i18n/` directory in any U2 module — verified by
`find addons/shopify_connector_* -name '*.po' -o -name 'i18n'`, which returns
nothing. Every string here is an English source term. Odoo will expose them to
its ordinary translation machinery because they are declared in views and
Python, but **no translation exists and none is claimed.**

`[Fact]` **The five states are not all present on every surface, and this deck
says which are missing rather than inventing copy for them.** Odoo's list and
form views supply `loading` (the platform skeleton/spinner) and `success` (the
resting state after a write) as platform behaviour; the connector authors
`empty`, `warning`, `blocked` and `failure`. Where the connector authors
nothing for a state, the row says **platform** or **none**.

**Role vocabulary.** SEC-2 ships two customer-facing roles — **Connector User**
and **Connector Administrator** — implemented as `group_shopify_connector_user`
and `group_shopify_connector_admin`. `Operator`, `Reviewer` and `Auditor` are
hidden capability primitives, not roles an operator is granted directly
(`shopify_connector_core/security/shopify_connector_security.xml`). The
closure is `admin → user → {operator, reviewer} → auditor`, so **a Connector
User holds both Operator and Reviewer**, and every control below that names
Operator *or* Reviewer is available to a Connector User.

---

## 1. Navigation labels

`[Fact]`

| String | Source |
| --- | --- |
| `Orders` | `shopify_connector_sale/views/shopify_connector_sale_menus.xml:24` |
| `Orders Workspace` | `…_sale_menus.xml:30` |
| `COD Reconciliation` | `…_sale_menus.xml:36` |
| `Customer Matching` | `…_sale_menus.xml:42` |
| `Catalog & Matching` | `shopify_connector_product/views/shopify_connector_product_menus.xml:33` |
| `Product Matching` | `…_product_menus.xml:39` |
| `Variant Matching` | `…_product_menus.xml:45` |
| `Inventory` | `shopify_connector_inventory/views/shopify_connector_inventory_menus.xml:20` |
| `Inventory Workspace` | `…_inventory_menus.xml:26` |
| `First-Push Guard` | `…_inventory_menus.xml:32` |
| `Location Mapping` | `…_inventory_menus.xml:38` |

`[Fact — navigation fact found by driving the browser]` **Customer Matching is
parented to the *Catalog & Matching* branch, not to Orders**, even though the
menu is declared in the sale addon
(`shopify_connector_sale_menus.xml:41` sets
`parent="shopify_connector_product.menu_shopify_connector_catalog"`). A reader
looking for it under Orders will not find it. Recorded here because a copy deck
that implies the wrong location is a navigation defect in prose.

---

## 2. The four U2 action controls

`[Fact]` U2 ships **exactly four** operator controls that reach a server
method. Everything else on every U2 surface is read-only. The matching
surfaces (customer, product, variant) carry **no button at all**, by design —
see §5.

### 2.1 `Approve Payment` — S17 order review, and the COD workspace

| Field | Value |
| --- | --- |
| Screen | Order Review form (`view_shopify_connector_order_binding_form`), reached from **Orders Workspace** and **COD Reconciliation** — both actions use the same model and the same form |
| Control | `Approve Payment` — `shopify_connector_sale/views/shopify_connector_order_binding_views.xml:133` |
| Visible when | `manual_gateway_approval_state == 'pending'` |
| Allowed role | **Connector User** or **Connector Administrator** (view gate: Reviewer; server guard: Reviewer or Administrator) |
| Sanctioned action | `shopify.connector.order.binding::action_approve_manual_gateway_order` |
| Writes / enqueues | Writes approval provenance; enqueues **one** `order_import_sync` evidence-refresh job **and** one lifecycle audit job |
| Browser evidence | `shopify_connector_u2_order_approval_tour` / `shopify_connector_u2_order_approval_denied_tour` |

**Warning state**, shown above the control
(`…_order_binding_views.xml:146-152`):

> **Needs a decision: payment was taken outside Shopify's gateway.**
> The connector cannot verify this payment. Review the evidence below before
> approving.

**Confirmation dialog**, `Approve manually-paid order`
(`shopify_connector_sale/views/shopify_connector_sale_wizard_views.xml:15-22`):

> **You are confirming payment was received.**
> Shopify did not process this payment through a gateway, so the connector
> cannot verify it. Approving records your commercial judgement and queues a
> read-only evidence refresh — it does not create, capture or reconcile a
> payment in Odoo.

`[Inference — from the shipped method]` **Why this wording is safe and
accurate.** It claims exactly what the code does and no more: the method writes
`manual_gateway_approved_by_uid`/`_at` and enqueues a read-only refresh. It
creates no `account.payment`, reconciles nothing, and does not confirm the sale
order — so a sentence promising any of that would be false. The dialog also
declines to say the payment *is* verified, because the connector cannot verify
it; it says the operator's judgement was recorded.

**Recovery instructions (server refusals).** Every one names the condition:

| Condition | Message |
| --- | --- |
| Blank reason (dialog) | `Describe why this manually-paid order is being approved.` |
| No order selected | `Select an order binding first.` |
| Wrong role | `Only a Shopify Connector Reviewer or Administrator may approve a manual-gateway order.` |
| Wrong company | `Manual-gateway approval must run in the sale order company.` |
| Not awaiting approval | `This order is not awaiting manual-gateway approval.` |
| Order no longer draft | `Only a draft quotation can be approved.` |
| Policy changed | `This store no longer requires manual-gateway approval.` |
| Evidence changed | `The order no longer has one approved, unambiguous manual payment gateway.` |
| Reversed payment | `Cancelled or reversed payment evidence is ineligible.` |

`[Fact]` The reason field's placeholder is `Why is this order being approved?`
and its help is `Why this manually-paid order is being approved. Recorded on
the approval audit trail.`

### 2.2 `Confirm First Push` — S11 first-push guard

| Field | Value |
| --- | --- |
| Screen | Inventory Level form, reached from **First-Push Guard** |
| Control | `Confirm First Push` — `shopify_connector_inventory/views/shopify_connector_inventory_views.xml` (header) |
| Visible when | `first_push_state == 'previewed'` |
| Allowed role | **Connector User** or **Connector Administrator** |
| Sanctioned action | `shopify.connector.inventory.level.binding::action_confirm_first_push` |
| Writes / enqueues | Writes only. No job, no Shopify request |
| Browser evidence | `shopify_connector_u2_first_push_confirm_tour`, `…_pending_has_no_control_tour`, `…_denied_tour` |

`[Fact — correction made in this batch]` The control was previously shown when
`first_push_state == 'pending'`, which is the one state the server **refuses**,
and hidden in `previewed`, the one state it accepts. The two waiting states now
carry **two different sentences**, because they ask the reader for different
things:

**Waiting state 1 — nothing to decide yet** (`first_push_state == 'pending'`):

> **Waiting for a first-push preview.**
> Nothing has been pushed for this product and location yet, and the quantity
> to send has not been computed. The preview runs on the next scheduled pass;
> the confirmation control appears once it has.

**Waiting state 2 — a decision is available** (`first_push_state == 'previewed'`):

> **Waiting for a first-push confirmation.**
> Nothing has been pushed for this product and location yet. Review the
> quantities below, then confirm.

**Consequence copy on the control** (the heaviest in the module, by design —
RA-008):

> This is the FIRST stock push for this product and location. Shopify's
> quantity will be replaced by Odoo's. This cannot be undone from here.
> Confirm?

`[Inference]` **Why this wording is safe and accurate.** It names the direction
of the overwrite (Odoo's quantity replaces Shopify's), scopes it to the exact
pair, and says plainly that this screen offers no undo — which is true: no
un-confirm action exists. It does not promise that the push happens
immediately, because confirming only lifts the guard; the push is a later
scheduled job.

**Recovery instruction:** `A first push can only be confirmed after its preview
has run.` (Reachable only through RPC now that the control is gated on
`previewed`.)

### 2.3 `Verify Now` — inventory re-check / manual-review release

| Field | Value |
| --- | --- |
| Screen | Inventory Level form, reached from **Inventory Workspace** |
| Control | `Verify Now` — `…_inventory_views.xml` (header) |
| Allowed role | **Connector User** or **Connector Administrator** (corrected in this batch from Operator, which the server refuses) |
| Sanctioned action | `shopify.connector.inventory.level.binding::action_recheck_inventory_pair` |
| Writes / enqueues | Cancels the blocked job and enqueues **exactly one** successor `inventory_push_sync` job |
| Browser evidence | `shopify_connector_u2_recheck_tour`, `…_blank_reason_tour` |

**Dialog copy**, `Verify inventory now`
(`shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml:66-70`):

> This queues a read-only verification of what Shopify currently holds for
> this pair. It changes no quantity on either side.

`[Inference]` **Why this wording is safe and accurate.** The release is
orchestration only — it cancels one job and creates a successor at ordinal 0,
and creates no mutation attempt. Saying "verification" rather than "sync" is
the accurate word: nothing is written to Shopify by this action.

**Recovery instructions:**

| Condition | Message |
| --- | --- |
| Blank reason — **client side** | Odoo marks `Reason` invalid (`required=True`) and does not call the server |
| Blank reason — server | `Describe why this pair is being re-checked.` |
| No level selected | `Select an inventory level first.` |
| Wrong role | `Only a Shopify Connector Reviewer or Administrator may release a blocked inventory pair.` |
| Pair locked | `This inventory pair is currently held by another operation; try again shortly.` |
| Job locked | `The blocked job is currently held by another operation; try again shortly.` |
| Not exactly one blocked job | `Exactly one active blocked inventory job is required for this pair (found %d).` |
| Outcome ineligible | `This blocked job's outcome is not one of the cases eligible for release via action_recheck_inventory_pair. Uncertain, duplicate-risk, idempotency-contract, unresolved-reconciliation, store-identity-mismatch, and unexplained-drift/nonzero-post-activation cases require the Stage 0 Administrator-only manual resolution path instead.` |

`[Open question — Tier 3, wording]` The ineligible-outcome message names a
method identifier (`action_recheck_inventory_pair`) and an internal route
("Stage 0 Administrator-only manual resolution path") to an operator. It is
accurate and it does name the owner of the next step, which the error contract
requires — but it reads as internal vocabulary. Logged rather than rewritten,
because changing a shipped refusal string is a behaviour change that belongs in
its own reviewed batch.

`[Fact]` Placeholder: `Why is this being re-checked?`; help: `Why this pair is
being re-checked. Recorded on the resulting verification job so the decision is
auditable later.`

### 2.4 `Change Push` — S10 location mapping

| Field | Value |
| --- | --- |
| Screen | Location Mapping form |
| Control | `Change Push` |
| Allowed role | **Connector User** or **Connector Administrator** (the wizard's ACL was Administrator-only and is corrected in this batch, so a Connector User is no longer refused *after* pressing a control the UI offered them) |
| Sanctioned action | `shopify.connector.location.mapping::action_set_push_enabled` |
| Writes / enqueues | Writes only |
| Browser evidence | `shopify_connector_u2_push_toggle_tour` |

**Dialog copy**, `Change inventory push` — one sentence per direction
(`…_inventory_wizard_views.xml:20-32`):

> Inventory for *(location)* will start pushing to Shopify on the next
> scheduled run.

> Inventory for *(location)* will stop pushing. Quantities already on Shopify
> are left exactly as they are.

`[Inference]` **Why this wording is safe and accurate.** The disable sentence
answers the question an operator actually has — *does turning this off remove
what is already there?* — and the answer is no, which matches the code: the
method writes a boolean and touches no quantity. The enable sentence does not
promise an immediate push, because there is none; the next scheduled run does
it.

**Recovery instructions:** `Select a location mapping first.` /
`Only a Shopify Connector Operator or Administrator may change a location
mapping's push-enable flag.`

---

## 3. Empty states

`[Fact]` Every U2 list action ships an empty state with an affirmative or
guiding first line and a second line saying what will fill it — the accepted
pattern.

| Surface | First line | Second line |
| --- | --- | --- |
| Orders Workspace | `No orders imported yet.` | `Orders appear here within minutes of your first sync.` |
| COD Reconciliation | `No cash-on-delivery orders awaiting reconciliation.` | `COD orders appear here with their commercial, fulfilment and collection states shown separately.` |
| Customer Matching | `Every customer is matched.` | `Customer bindings appear here after an order or customer import. Nothing needs your decision right now.` |
| Product Matching | `Every product is matched.` | `Product bindings appear here after a catalog import. Nothing needs your decision right now.` |
| Variant Matching | `Every variant is matched.` | `Variant bindings appear here once their product has been imported and matched.` |
| Inventory Workspace | `No pending inventory changes.` | `Inventory levels appear here once products and locations are mapped.` |
| First-Push Guard | `Nothing is waiting for a first push.` | `The first stock push for each product and location needs an explicit confirmation. Pairs waiting for one appear here.` |
| Location Mapping | `No locations mapped yet.` | `A mapping is created when a Shopify location is paired with an Odoo location. Until a pair exists, inventory for that Shopify location stays paused.` |

`[Open question — Tier 3, wording]` `Orders appear here within minutes of your
first sync.` makes a **timing promise** the connector does not control: import
latency depends on the drain cron's schedule and the store's queue depth. The
copy voice rules forbid "real-time" claims for exactly this reason, and
"within minutes" is the same claim in softer clothing. Logged rather than
rewritten in this batch.

---

## 4. Blocked and warning states

`[Fact]` The scope-quarantine banner is shipped on **six** U2 forms with
near-identical wording, tailored to what stops on each surface:

| Surface | Blocked-state copy |
| --- | --- |
| Order Review | **Excluded from synchronisation.** This binding's company no longer agrees with its store's. No job will process this order until an administrator releases it. |
| Customer Binding | **Excluded from synchronisation.** This binding's company no longer agrees with its store's. No job will process it until an administrator releases it. |
| Product Binding | **Excluded from synchronisation.** This binding's company no longer agrees with its store's. It is hidden from ordinary reads and no job will process it until an administrator releases it. |
| Variant Binding | **Excluded from synchronisation.** This binding's company no longer agrees with its store's. No job will process it until an administrator releases it. |
| Location Mapping | **Excluded from synchronisation.** This mapping's company no longer agrees with its store's. Inventory for this location is paused until an administrator releases it. |
| Inventory Level | **Excluded from synchronisation.** This level's company no longer agrees with its store's. No push or verification job will process it until an administrator releases it. |

`[Fact — P3 finding, found by driving the browser]` **This banner cannot render
for any ordinary operator.** The SEC-3 store rule is a *global* `ir.rule` whose
domain is `['&', ('company_id','in',company_ids), ('sec3_scope_quarantined','=',False)]`
(`shopify_connector_*/security/*_company_rules.xml`), so a quarantined row is
filtered out of **every non-superuser read**. The row the banner sits on is
invisible, and what an operator actually experiences is that the record is
simply not in the queue.

That is *stricter* than the banner and is the correct fail-closed posture, so
nothing was changed to make the banner appear. It is recorded as dead UI —
only the Product Binding wording ("It is hidden from ordinary reads") is
actually accurate about the mechanism. Proven by
`test_quarantined_pair_is_not_reachable_by_an_operator`.

`[Fact]` Other warning states:

| Surface | Copy |
| --- | --- |
| Order Review | **Cancelled on Shopify.** *(followed by the Shopify cancel reason)* |
| Customer Binding | **Snapshot unavailable — re-import required.** A previous retention sweep masked this customer's snapshot irreversibly. The original values cannot be recovered and are not reconstructed here. Re-import the customer from Shopify to restore them. |
| Customer Binding | **Waiting on a decision.** This customer match was not conclusive. Review the evidence below before this binding is treated as authoritative. |
| Product Binding | **Waiting on a decision.** This product match was not conclusive. Review the evidence below before this binding is treated as authoritative. |

`[Inference]` The retention-sweep sentence is the strongest wording in U2 and
correctly so: it says the loss is **irreversible**, refuses to imply the values
can be recovered locally, and names the one recovery route that exists
(re-import). It matches the field help on
`shopify_connector_customer_binding.py:70-74`.

---

## 5. The surfaces that deliberately offer nothing

`[Fact]` **Customer, product and variant matching carry no action control.**
`grep '<button'` over all three view files returns zero hits. The product view
file states the reason in its own header:

> It offers no "create as new" affordance and no export action… Offering it
> here would put a mutation one click from a list.

`shopify.connector.binding.mixin::action_override_binding` exists on the model
and is **not wired to any view**. That is the shipped boundary, pinned by
`test_customer_matching_offers_no_resolution_control` and
`test_views_open_no_mutation_path`.

`[Fact]` **COD reconciliation offers no write control.** The COD list has no
`<button>`, the COD page on the form is entirely `readonly="1"`, and the action
reuses the order-review form — so the only control reachable from COD is
`Approve Payment` (§2.1). Pinned by
`test_cod_surface_offers_no_separate_write_control`.

`[Open question — scope, not wording]` The U2 locked prompt
(`ui-implementation-phases-packet.md` §8.1) names "collection-event entry,
discrepancy review" as COD deliverables. What shipped is display-only: the
five-value ledger and three separate state badges, with no entry or resolution
affordance. This deck describes what exists; the gap is a **scope** finding for
the control room, recorded in
[`ui-u2-validation-results.md`](../05-qa/ui-u2-validation-results.md) §5, not a
missing string.

---

## 6. Fixed vocabularies rendered as text

`[Fact]` Every state is rendered as a **word**, never colour alone (design
system §1 law 3, checklist V-4). The shipped selection labels:

| Field | Labels | Source |
| --- | --- | --- |
| binding `status` | Active / Stale / Manually Overridden / Review | `shopify_connector_binding_mixin.py:76-86` |
| `manual_gateway_evidence_state` | Not Manual / Unambiguous Manual Gateway / Mixed or Ambiguous | `shopify_connector_order_binding.py:61-67` |
| `manual_gateway_approval_state` | Not Required / Pending / Approved / Superseded | `…:69-75` |
| `customer_resolution` | Existing Binding / Email Match / Created / Guest Email Match / Guest Created / Fallback / Manual | `…:42-54` |
| `cod_commercial_state` | Imported / Quotation / Confirmed / Review / Cancelled | `…:85-94` |
| `cod_fulfillment_state` | Not Dispatched | `…:95-97` |
| `cod_collection_state` | Nothing Collected / Partially Collected / Fully Collected / Discrepancy | `…:98-106` |
| `first_push_state` | Pending / Previewed / Confirmed | `shopify_connector_inventory_level_binding.py:5-9` |

`[Fact — P3 finding]` Five U2 list views carry
`decoration-muted="status == 'inactive'"`, and `'inactive'` **is not a value of
the `status` selection anywhere in the codebase**. The decoration can never
fire. Harmless, but it is not a real state and must not be described as one.
Locations: `shopify_connector_order_binding_views.xml:103`,
`shopify_connector_customer_binding_views.xml:72`,
`shopify_connector_product_binding_views.xml:83` and `:239`,
`shopify_connector_inventory_views.xml:62`.

---

## 7. Copy-voice compliance (checklist V-12)

`[Fact]`

- **No "encrypt"/"encrypted" on any U2 surface** — verified by grep over all
  four modules' `views/`.
- **No "real-time"** on any U2 surface.
- **No raw token, stack trace or bare technical identifier** on a primary
  surface, with the one exception recorded in §2.3 (the ineligible-outcome
  refusal names a method identifier).
- **No vanity metric** — every number on a U2 surface is a business quantity or
  a state count.
- **Reason + fix + owner** — every refusal in §2 names the condition and, where
  a different role is required, names that role.

---

## 8. What this deck does not claim

- **No translation coverage.** No `.po` file exists in any U2 module.
- **No Odoo.sh runtime, no independent review, no UAT, no acceptance.**
- **No live-Shopify evidence.** `M-EXP-1`..`M-EXP-20` remain outstanding.
- **No claim that the copy is final.** Three Tier-3 wording issues are logged
  above (§2.3 internal vocabulary, §3 timing promise, §6 dead decoration)
  rather than silently rewritten.
