# Abandoned-Checkout Policy — Default Behavior, Optional Workspace, Classification

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Closes gap P-3 of
> [`mvp-remaining-gap-inventory.md`](../01-research/mvp-remaining-gap-inventory.md).
> Acceptance authority: product owner + Claude control room. No implementation
> authorized by this document.

Related documents:
[Shopify captures 2026-07-16 §5, §12](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md) ·
[`non-mvp-and-later-phases.md`](non-mvp-and-later-phases.md) (C-ADV-06) ·
[`reconnect-catchup-backfill-policy.md`](reconnect-catchup-backfill-policy.md) (P-7 sibling) ·
[`connector-roles-and-permissions.md`](connector-roles-and-permissions.md) (P-1 sibling, two-role model) ·
[Competitor refresh 2026-07-16](../00-source-materials/competitor-refresh-2026-07-16.md)

---

## 1. Default policy (binding)

**[Proposed product decision] PD-AC-1 — An abandoned Shopify cart/checkout never
automatically creates anything in Odoo.** Default connector behavior:

- **No quotation** (no `sale.order` in any state) is created from an abandoned checkout.
- **No sales-order demand** enters Odoo — nothing that MRP, procurement, or replenishment
  logic could interpret as demand.
- **No stock reservation** — abandoned carts must never hold inventory.
- **No revenue recognition or accounting artifact** of any kind.
- **Shopify remains responsible for normal recovery** (its native recovery emails /
  `abandonedCheckoutUrl` flow). The connector neither sends recovery communication nor
  mutates any checkout — abandoned-checkout access, if any, is strictly read-only.

Rationale:

- [Fact] An abandoned checkout is not a committed transaction; Shopify models it as a
  separate `AbandonedCheckout` object whose `completedAt` is null until the buyer
  completes checkout ([captures §5](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
- [Inference] Auto-created quotations would pollute demand signals (forecasting,
  reordering rules keyed on quotations), risk phantom stock reservations if a user
  confirms one, and create a duplicate-order hazard when the same checkout later
  converts into a real Shopify order imported through the normal path.
- [Inference] Most abandoned checkouts never convert; auto-creating documents for them
  produces high-volume noise in the merchant's sales pipeline with negative value.
- [Fact] Abandoned-checkout data is protected customer data (PCD, captures §5/§12) —
  minimizing what the connector copies into Odoo is the lowest-risk default.

This default is **binding in MVP** regardless of whether the optional workspace (§3)
ships: MVP simply does not read abandoned checkouts at all unless the workspace
capability is enabled.

## 2. Evidence: what the 2026-07 Shopify API provides

All facts below from the 2026-07-16 capture, §5 unless noted (sources Accessible
2026-07-16: `objects/AbandonedCheckout`, `queries/abandonedCheckouts`).

- [Fact] **`AbandonedCheckout` object exists** with `abandonedCheckoutUrl` (recovery
  URL), `completedAt` (null until the buyer completed checkout — non-null ⇒ converted
  to an order), `lineItems`, `totalPriceSet` (incl. discounts/shipping/taxes/tips),
  nullable `customer`.
- [Fact] **`abandonedCheckouts` query exists** with filters `created_at`, `updated_at`,
  `id`, `email_state` (`sent|not_sent|scheduled|suppressed`), `recovery_state`
  (`recovered|not_recovered`), `status` (`open|closed`); default sort key `ID`.
- [Fact] Required API scope: **`read_orders`** (already held for order import); Shopify
  admin-UI parity additionally involves the `manage_abandoned_checkouts` staff
  permission, which is a Shopify-staff concept, not an app scope.
- [Fact] Abandoned-checkout data is **protected customer data (PCD)** — Level-2
  obligations apply to the customer fields (name/address/email/phone): access logging,
  minimization, retention discipline (captures §12).
- [Open question] **No documented direct AbandonedCheckout→Order object reference**
  exists beyond `completedAt`/`recovery_state` (captures §5 and §13 item 4).
  [Inference] Any conversion linkage must therefore key on the resulting **Order**
  arriving through the normal order-import surface, never on the checkout itself.
- [Open question] `abandonedCheckoutsCount` availability unconfirmed; no webhook topic
  for abandoned checkouts is recorded in our captures — [Inference] polling/scan is the
  only evidenced acquisition path. Re-verify webhook topics before implementation.

## 3. Optional premium capability — Abandoned Checkouts workspace

**[Proposed product decision] PD-AC-2 — Visibility, if offered, is a separate read-only
"Abandoned Checkouts" workspace, off by default, per store.** It is an observation
surface, never an order pipeline.

### 3.1 Data model sketch [Recommendation]

- A read-only **abandoned-checkout cache model** (working name
  `shopify.abandoned.checkout.cache`), one record per Shopify `AbandonedCheckout` id,
  **scoped per store/connection** like other read domains. It is a cache, not a
  binding: it never participates in the binding/dedup framework
  ([AR-005](../03-architecture/ar-005-binding-dedup-framing.md)) and no Odoo business
  document references it structurally.
- Fields (mirroring §2 evidence): Shopify checkout id; checkout identity/number;
  customer reference (masked display, §3.2); line items (product titles/variants +
  quantities — displayed, with best-effort match to known product bindings for
  navigation only); checkout value (`totalPriceSet`, presentment + shop currency);
  created/updated timestamps; `status`, `email_state`, `recovery_state`; `completedAt`;
  deep link to the checkout in Shopify admin; and the recovery URL treated as
  sensitive (it grants cart access — Administrator-only display [Recommendation]).

### 3.2 Masked customer data (two-role model)

Consistent with the two-role direction in
[`connector-roles-and-permissions.md`](connector-roles-and-permissions.md):

- **Connector User** sees customer identity **masked by default** (e.g. partial email,
  no phone/address). Unmasking follows exactly the same permission-controlled mechanism
  defined in the roles doc — no abandoned-checkout-specific exception.
- **Connector Administrator** access follows the same doc; every unmask is subject to
  the PCD access-logging obligation ([Fact], captures §12).

### 3.3 Refresh strategy

- [Recommendation] A **scheduled read scan** using `abandonedCheckouts` with
  `updated_at` watermarking, running within the normal read-scan cadence and
  rate-limit budget of the sync engine — the same pattern as other read domains.
  **Never a mutation**: the connector never closes, completes, emails, or otherwise
  writes to a checkout.
- No webhook dependency (none evidenced, §2 open question).

### 3.4 Retention

- [Proposed product decision] PD-AC-3 — The **PII retention sweep must cover the
  abandoned-checkout cache**: records past the configured retention window are purged
  (or at minimum PII-scrubbed), and `customers/redact` / `shop/redact` handling
  ([Fact], captures §12) must include this model. A checkout cache that outlives the
  customer's redaction request is a compliance defect.

### 3.5 Conversion display

- [Recommendation] When `completedAt` is non-null (and/or `recovery_state = recovered`),
  the workspace shows **"Converted"** and attempts to display the resulting Odoo order
  **by lookup**: search existing order bindings created by the normal order-import path
  (e.g. by customer + creation-time window + value, presented as "likely linked order",
  or exact if a reliable key is later verified — §2 open question). If no binding is
  found (order outside import window/filters), show "Converted in Shopify — not
  imported" with the Shopify link.
- **The checkout is never made the binding.** Linkage is display-only, resolved from the
  order side; the imported order's binding keys on the Shopify Order id exclusively.

## 4. Audited manual quotation action

**[Proposed product decision] PD-AC-4 — A quotation may be created from an abandoned
checkout only through an explicit, audited, manual user action** in the workspace:

- **Explicit action**: a button ("Create draft quotation") with a confirmation step;
  never bulk-automatic, never scheduled.
- **Result**: a **normal Odoo quotation** (draft `sale.order`) populated from the cached
  lines/customer. It is **NOT connector-bound to any Shopify order or checkout** — the
  connector will never confirm, update, or reconcile it; it is ordinary manual Odoo data
  from that point on.
- **Provenance marker**: the quotation carries a provenance annotation (origin note /
  marker field: source checkout id + store) so it is recognizable in review and in the
  inconsistency check below. [Recommendation] Marker, not binding — it creates no sync
  relationship.
- **Audit trail**: the action is recorded via the existing lifecycle audit-job pattern
  (actor, checkout id, store, timestamp), same mechanism as other audited connector
  actions.
- **Duplicate-safety rule**: if the checkout later converts into a real Shopify order,
  that order is imported through the normal path as a **separate SO** — by design, no
  merge, no suppression. Two documents may then coexist.
  - **Operational guidance**: the manual quotation is the merchant's to cancel or
    convert manually; the imported order is always the authoritative transaction.
  - **Inconsistency warning surface**: [Recommendation] a User review case —
    *"manual quotation exists for a checkout that converted"* — raised when a cached
    checkout with a provenance-marked quotation gains a non-null `completedAt`,
    surfaced in the normal review/attention queue so the merchant resolves the
    duplicate deliberately.

## 5. Classification verdict

- [Fact — vendor claim class] The only competitor evidence for abandoned-checkout
  handling in the 2026-07-16 refresh is **Softhealer**, claiming "abandoned checkouts →
  CRM leads" ([competitor refresh, S16](../00-source-materials/competitor-refresh-2026-07-16.md));
  [`non-mvp-and-later-phases.md`](non-mvp-and-later-phases.md) already classifies this
  breadth item as **C-ADV-06, SH-only evidence**. No competitor evidence of
  checkout→quotation automation exists in our corpus, and single-vendor claims do not
  meet the bar for pulling scope into MVP.
- **[Recommendation] Verdict:**
  - **MVP (binding): the default no-quotation policy (§1)** — zero implementation cost,
    since it is the absence of a feature, but it must be stated in scope docs and UAT.
  - **Post-MVP: the Abandoned Checkouts workspace (§3) and the audited manual
    quotation action (§4).**
- Effort implications ([Inference]): the workspace is a **new read domain** — a new scan
  job type, a new per-store cache model, a workspace UI (list + detail + masking +
  review case), PCD access-logging coverage, and retention-sweep/redaction integration.
  That is meaningful scope comparable to a small domain slice, for a capability with
  single-vendor competitive evidence and no committed-transaction value.
- **Revisit condition**: pull forward to optional-MVP only if (a) the product owner
  designates it a paid differentiator for launch, or (b) ≥2 additional competitors are
  verified to ship abandoned-checkout visibility, or (c) pilot merchants explicitly
  request it during UAT. Route any revisit through the architecture-review log per
  CLAUDE.md §10.

## 6. Reconnect behavior (if the workspace is implemented)

- [Recommendation] Same pattern as other read domains in
  [`reconnect-catchup-backfill-policy.md`](reconnect-catchup-backfill-policy.md):
  watermark-based re-scan on reconnect using `updated_at >= (watermark − overlap)`,
  idempotent upsert into the cache keyed on the Shopify checkout id. Missed intervals
  cost nothing but staleness — no demand, stock, or financial effect can result, so
  abandoned checkouts are explicitly the **lowest-priority catch-up domain** and may be
  deferred behind orders/inventory/fulfillment after a reconnect.
- No backfill obligation: [Recommendation] initial/backfill window defaults to a short
  horizon (e.g. the recovery-relevant last 30 days, configurable) rather than full
  history — old abandoned checkouts are dead PII, not value.

## 7. Test / UAT hooks

MVP (default policy):

1. **UAT-AC-1**: Abandon a checkout in the dev store → verify no quotation, no
   `sale.order`, no stock move/reservation, no journal entry appears in Odoo.
2. **UAT-AC-2**: The same checkout later completes → exactly **one** Odoo order is
   created via the normal order-import path; re-running scans creates no duplicate.

Workspace (post-MVP, when built):

3. Cache scan populates identity, masked customer, lines/quantities, value, timestamps,
   `email_state`/`recovery_state`/`status`, Shopify link; Connector User sees masked
   data, unmask is permission-gated and access-logged.
4. `completedAt` transition → "Converted" shown; linked order resolved by order-side
   lookup only; checkout record is never a binding.
5. Manual quotation action → draft SO with provenance marker, not connector-bound;
   audit record has actor/checkout id/timestamp; subsequent conversion raises the
   "manual quotation exists for a converted checkout" review case, and the imported SO
   is a separate document.
6. Retention sweep and `customers/redact` purge/scrub cache rows; recovery URL hidden
   from Connector User.
7. Reconnect after downtime → watermark re-scan updates cache without duplicates.

## 8. Proposed-decision block

| ID | Decision | Class |
| --- | --- | --- |
| PD-AC-1 | Abandoned checkouts never auto-create quotations, demand, reservations, or revenue in Odoo; Shopify owns recovery. Binding in MVP. | Proposed product decision |
| PD-AC-2 | Visibility, if offered, is a separate read-only per-store workspace, off by default; classified post-MVP. | Proposed product decision |
| PD-AC-3 | The PII retention sweep and redaction handling must cover the abandoned-checkout cache. | Proposed product decision |
| PD-AC-4 | Quotation creation from a checkout only via explicit audited manual action; quotation is provenance-marked, never connector-bound; a later real order imports as a separate SO with a review-case warning. | Proposed product decision |

Acceptance: product owner + Claude control room. Upon acceptance, record as an ADR in
`docs/04-decisions/` and update [`non-mvp-and-later-phases.md`](non-mvp-and-later-phases.md)
(C-ADV-06) and [`mvp-scope.md`](mvp-scope.md) accordingly.

## 9. Open questions

1. [Open question] AbandonedCheckout→Order direct linkage beyond `completedAt` /
   `recovery_state` — is any order reference exposed in 2026-07 or later versions?
   (Captures §13 item 4.) Determines whether "likely linked order" can become exact.
2. [Open question] Does any webhook topic cover abandoned checkouts, or is polling the
   only path? Re-verify before implementation.
3. [Open question] `abandonedCheckoutsCount` availability (for workspace KPIs).
4. [Open question] Exact masking granularity for checkout customer fields — inherit
   verbatim from the roles doc or define a stricter checkout-specific profile (given
   nullable `customer` and PCD level)?
5. [Open question] Should the manual-quotation action be Administrator-only or
   available to Connector User with unmask permission? Product-owner call at
   workspace design time.
