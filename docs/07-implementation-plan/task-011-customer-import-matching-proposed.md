# Task 011 — Customer Import and Matching (Proposed)

> Planning-only future implementation task spec, part of the MVP domain
> implementation-slicing sequence
> ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> Area 2). Describes scope/boundary/approach only — MBQ-55 (exact Odoo
> field mapping) remains open.

## Status

**Proposed only. Not authorized.** Depends on: Task 002/003 foundation
gates opening and merging; the "sale domain gate" named in
[`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
Group 11 (customer import/matching is owned by `shopify_connector_sale`,
not a separate module — see below); and the dedicated MBQ-55 domain
naming/schema planning pass. This document does not authorize, start, or
imply authorization of any of the above.

## Objective

Import Shopify customers into Odoo `res.partner` records and match them
to existing partners — Shopify → Odoo only, never pushed back — using
email as the sole automatic match key, with a single, clearly-flagged
fallback partner reserved strictly for genuinely no-PII orders, so that
order import (Task 012) always has a customer-resolution outcome
(success, fallback, or held-pending-review) available to it.

## Preconditions

- Foundation Tasks 002/003 merged and gate-opened.
- The "sale domain gate" (`ui-ux-implementation-task-map.md` Group 11's
  named prerequisite) explicitly opened — customer import/matching is
  folded into `shopify_connector_sale` for Phase 1; there is **no**
  separate `shopify_connector_customer` module in the accepted design
  ([DEC-008](../04-decisions/DEC-008-module-boundary-strategy.md); Part B
  §B.1/§B.8; `ar004-module-boundary-decision-brief.md` classifies a
  future split as "Weakened/deferred, not rejected" — this task does not
  propose promoting it).
- MBQ-55 (exact Odoo partner/binding field mapping) resolved via the
  dedicated naming/schema planning pass.
- [DEC-014](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
  points D and E (fallback partner, customer match-key set) remain the
  accepted design baseline.

## Customer binding/matching approach

`shopify_connector_sale` defines its own concrete customer-binding model
(Shopify Customer ↔ Odoo `res.partner`) extending
`shopify.connector.binding.mixin` directly — not routed through
`product`, since customers have no product-domain counterpart (Part B
§B.8). Matching priority (Decision — DEC-006; DEC-012 §6.4; DEC-014 point
E / MBQ-31, "Accepted at blueprint level"): **existing binding → email
(the sole automatic match key) → manual review.** Phone and name stay
advisory/manual-only, never automatic — name is structurally excluded
everywhere (RA-006); phone was evaluated and not adopted as an automatic
key (no demonstrated additional dedup value over email). A name/email-adjacent
similarity may be shown as an advisory hint during manual match but never
auto-binds.

## Fallback partner rules

A single, deliberately-created, clearly-flagged fallback partner per
store (proposed name direction: "Shopify — No Customer Data") is used
only when Shopify genuinely withholds all customer PII for an order (a
no-PII plan/scope scenario) — never as a default for an ordinary matching
failure, which instead goes through the normal customer-import creation
path or routes to manual review if ambiguous (Part B §B.7, DEC-014 point
D — "Partially resolved"). Every order bound to the fallback partner
carries a visible, auditable marker ("no customer data available —
fallback used"). **Open — MBQ-29:** whether one shared fallback partner
per store is sufficient, or whether per-order anonymous identity is
required for order-level traceability, remains unresolved per the
product/customer/sale research; the UI/UX research separately describes
MBQ-29 as "Resolved via AR-020" with only its exact naming left open —
both characterizations are reported here without reconciliation, and this
task's own final §9 prompt must confirm the register's current state
directly rather than rely on either snapshot.

## Duplicate handling

Same two-path structure as product, applied to customers (Part B
§B.2/§B.9, MBQ-59 gate): an interactive/batch create/bind always shows a
blocking preview; an automated (webhook/scheduled/reconciliation-triggered)
import runs a pre-create duplicate check gated by the two-tier
eligibility/match-quality gate before creating/binding. No customer
export exists in Phase 1 (Decision — DEC-003, unchanged; Part B §B.4), so
duplicate handling only applies in the Shopify → Odoo direction.

## Address handling

**Open — not yet decided in the repo.** Neither DEC-014 nor the Part B
architecture document contains any section, rule, or discussion of
customer/order address handling (shipping address, billing address,
address matching, field mapping, or address-level source of truth). The
only address-adjacent mention is the one-line list of protected-PII field
examples ("name/address/email/phone," Part B §B.6), which describes
protected-data scope, not a design decision. This task's own final §9
prompt must either resolve this as a new, numbered open question or
explicitly scope address handling out of Task 011's first cut.

## Company/person handling

**Open — not yet decided in the repo.** Neither document distinguishes
company/organization partner records from individual/person partner
records for `res.partner` creation, nor discusses `is_company` semantics
or contact hierarchies. The only adjacent fact is that B2B commerce is
explicitly excluded from Phase 1 scope (Part B, "Scope and non-goals") —
which defers B2B *commerce features*, not the question of how an ordinary
Shopify customer should be classified on creation.

## API needs

**Open** — not yet confirmed at the field/query level. Direction
confirmed: reads only (Part B §B.2 — Phase 1 customer import is Shopify →
Odoo only, never pushed back); protected-customer-data access requires
Shopify approval and Level 1/2 data-protection controls for any store
handling PII (Official fact, `../01-research/shopify-official-api-notes.md`,
citing `https://shopify.dev/docs/apps/launch/protected-customer-data`) — a
store/config lacking that access must not fail order import or invent
PII. Exact GraphQL query/field list is for this task's own final §9
prompt.

## UI dependencies

Yes, for the Customer mapping screen (S8, Group 11) — Reviewer
ambiguity-resolution flow. Requires the UI implementation gate (currently
closed) plus the sale domain gate. PII-minimization on screen (match
evidence, not full profiles) is a design proposal under the accepted
conservative protected-data posture, not yet a hard implementation rule.

## Tests required

Email-only auto-match correctness; ambiguous-match manual-review routing;
fallback-partner flagging and auditability on the order/binding record;
enforcement that no customer-export path exists in Phase 1;
access-control matrix across the four existing groups; confirmation that
no PII is ever invented when Shopify withholds it. Exact fixtures for this
task's own final §9 prompt. If no Odoo runtime exists at coding time,
tests must still be written and syntax-validated per the Task 001A
precedent.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: confirm the
customer binding model lives inside `shopify_connector_sale` (not a
separate module); confirm an email match resolves automatically and a
no-match/ambiguous case routes to manual review; confirm the fallback
partner is used only for a simulated no-PII scenario and carries its
visible flag; confirm no customer record is ever pushed back to Shopify.

## Rollback

Single-PR revert; Task 012 (order import) cannot yet exist at the point
this task would first merge (per the proposed MVP domain sequence), so no
dependent domain logic is affected. Reverting drops the customer-binding
model; any already-created `res.partner` records remain as ordinary Odoo
data, simply un-bound.

## Acceptance criteria

- Only allowed files changed (per this task's own future final §9
  prompt); customer binding lives inside `shopify_connector_sale`, no
  separate customer module created.
- Email-only automatic matching enforced; phone/name never auto-bind.
- Fallback partner used only for genuine no-PII scenarios, always
  flagged.
- No customer data ever exported to Shopify.
- Zero order/inventory/fulfillment logic in the diff.

## Explicit exclusions

- **No order import** (Task 012's scope).
- **No product logic** (Task 010's scope).
- **No marketing-consent logic unless already decided** — none of the
  research notes for this sprint establish a marketing-consent decision;
  treat as out of scope unless a future §9 prompt states otherwise.
- **No advanced B2B** (Phase 1 excludes B2B commerce features entirely,
  Part B "Scope and non-goals").
