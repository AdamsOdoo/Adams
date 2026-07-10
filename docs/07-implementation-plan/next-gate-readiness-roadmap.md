# Next-Gate Readiness Roadmap — Customer-Domain Gate (Task 011)

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Does not open
> the customer-domain gate, does not draft or issue any implementation
> prompt, does not authorize Task 011 or any other task.** Prepared
> 2026-07-09 as part of the post-PR #140 master audit
> ([`../08-release-readiness/project-readiness-master-audit.md`](../08-release-readiness/project-readiness-master-audit.md)).
> This document specifies exactly what the **next** gate-directed session
> must produce and which decisions ChatGPT must make inside it — so that
> session can be issued with zero ambiguity. Open-point IDs (OP-xx) refer
> to [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md).

## 1. Which gate is next, and why

**The customer-domain implementation gate (Task 011 scope only).**

- Its criteria are the only domain-gate criteria in the repository that
  are **Accepted** ([`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
  §3, comment `4928377625`).
- Its naming precondition (MBQ-55 customer-binding portion) is the only
  unimplemented-domain naming pass that is **Accepted**
  ([`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)).
- Task 010, its only task-level precondition, is merged and runtime-green.
- Every other domain (order/inventory/fulfillment/export) still lacks both
  a naming pass and gate criteria — each is at least two accepted-planning
  PRs behind the customer domain.

This mirrors exactly where the product domain stood after PR #136 merged
and before PR #137 — the established two-step pattern's midpoint.

## 2. What the next session must produce (the PR #137 analogue)

One docs-only session, one draft PR into `Shopify-connector`, containing:

1. **Task 011 final implementation prompt** — file-exact, per
   [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
   (allowed files, forbidden files, acceptance criteria, exact tests,
   rollback notes, definition of done), carrying every §4 decision below,
   and marked, verbatim, at top:
   **DO NOT USE UNTIL CHATGPT REVIEWS, ACCEPTS, AND EXPLICITLY ISSUES THIS
   PROMPT.**
2. **Customer-domain gate-opening proposal** — criterion-by-criterion
   satisfaction evidence for all 15 accepted criteria, including the
   criterion-12 point-in-time reconfirmation that the OP-05/OP-06/OP-03/
   fulfillment/packaging/concurrency blockers remain non-blocking for Task
   011's narrow scope (their classification held at PR #140 time; the
   proposal must re-verify, not assume).
3. Status patches only where those two documents require them (AR log new
   row; handoff entry) — no scope rewrites.

The gate itself opens only by ChatGPT's subsequent explicit act on that
PR, authorizes exactly one implementation session, and closes again when
the Task 011 implementation PR opens as draft
([`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md) §4).

## 3. Criteria left to satisfy (restated)

Criteria 3, 4, 5, 9, 13, 14, 15 are satisfied by the final prompt's own
content; criterion 12 by the gate-opening proposal's reconfirmation. Full
live table:
[`../08-release-readiness/implementation-readiness-map.md`](../08-release-readiness/implementation-readiness-map.md) §2.

## 4. The exact decisions ChatGPT must make in/for the final prompt

Assembled decision inputs (all **[Fact]** rows fetched from official
sources 2026-07-09; recommendations are this audit's, subject to review):

| # | Decision | Inputs on record | Audit recommendation |
| --- | --- | --- | --- |
| D1 | **Customer dedup/match-confidence thresholds** (criterion 5; OP-10) | Email is the sole automatic key (DEC-014 E / MBQ-31); Odoo 19 `res.partner.email` has **no uniqueness constraint** (official source: `email = fields.Char()`), so 0, 1, or N matches are all real cases | Fix the two-tier rule in the prompt: exactly-one-active-partner email match → bind; zero → create-eligible under MBQ-59 gate; >1 → `blocked_manual_review` (`ambiguous match`), no row. Declare tie-breaker refinements (archived partners, case folding) narrow in-task decisions |
| D2 | **Exact job/log field(s) for ambiguous-match candidate detail** (criterion 15; OP-09) | Principle accepted: candidate detail lives at job/log level only, never a binding row | Name the exact field(s) in the prompt (e.g. a structured payload on the existing `job.log` append path vs a dedicated job field — pick one, name it, test it) |
| D3 | **Address handling** (criterion 14; OP-07) | Shopify: `defaultAddress` (`MailingAddress`), paginated `addressesV2`; Odoo: addresses are child partners typed contact/invoice/delivery/other; `sale.order` auto-computes invoice/shipping via `address_get` — so this choice pre-shapes Task 012 behavior | First cut: import `defaultAddress` fields onto the bound partner only; no child-partner rows; full address-list sync explicitly deferred with a revisit note in the prompt |
| D4 | **Company/person classification** (criterion 14; OP-08) | Shopify `Customer` has no person/company flag; only free-text `MailingAddress.company` and B2B `companyContactProfiles` exist; Odoo `is_company` defaults False | Always import as person (`is_company=False`); never auto-classify from the address company string; B2B/company modeling stays non-MVP |
| D5 | **Fallback-partner field mechanics** (criterion 13; OP-11) | Name/home accepted: `customer_fallback_partner_id` on `shopify.connector.store.settings`; Posture A boundary accepted (inert config, zero consumption in Task 011) | Prompt fixes: field type `Many2one('res.partner')`, no default, no auto-creation, ordinary write path, boundary restated verbatim |
| D6 | **`shopify_connector_sale` manifest dependency** (OP-12) | Both options structurally safe; customer binding itself does not read product bindings | Depend on `shopify_connector_core` (+ Odoo core apps as needed) only; add the `shopify_connector_product` dependency in Task 012 when order lines actually need it — smallest-manifest principle; name it an in-task-confirmable decision |
| D7 | **Exact GraphQL query/field list + pagination** (OP-13) | On `2026-07`-era Admin API, `Customer.email`/`phone` are **deprecated** in favor of `defaultEmailAddress`/`defaultPhoneNumber`; `addressesV2` supersedes `addresses`; `read_customers` scope already in `REQUIRED_MVP_SCOPES`; cursor pagination + THROTTLED-body handling already core-client concerns (SRR-08) | Prompt pins the exact field list (prefer the non-deprecated fields, consistent with the store's pinned `api_version`) and the page-size/checkpoint posture, mirroring Task 010's precedent |
| D8 | **Test files** (criterion 9) | Proposed names already accepted as starting points: `test_customer_binding.py`, `test_customer_import_matching.py`, `test_customer_duplicate_prevention.py`, `test_customer_fallback_partner.py` | Confirm the four names; add explicit ambiguous-match and no-PII-fallback negative cases; live Odoo.sh run mandatory before merge (SRR-06 practice) |

Plus the standing prompt boundaries (restated, not new): no order logic,
no export, no UI/webhook/OAuth, no core edits, no live-Shopify dependency
beyond the Task 003 client, fake-client tests allowed, single-PR rollback.

## 5. Immediately after this gate (so nothing queues blind)

- **Parallel, recommended now:** MBQ-05 branch B research/decision task
  (OP-05, with the OP-40 protected-customer-data compliance dimension in
  scope) — ChatGPT authorization decision, independent of this gate.
- **Next domain pre-pass after Task 011 closes:** order domain — MBQ-55
  order-binding naming + order-domain gate criteria + MBQ-56/MBQ-27
  decision briefs (OP-14–OP-17), applying the ambiguous-match naming-time
  check that is now standard.
- **Runtime tracks, opportunistic:** VAL-B2 execution (OP-06) and the
  concurrency plan (OP-22) whenever their access preconditions appear.

## 6. Explicit non-authorizations

This roadmap does not open the customer-domain gate, does not draft or
issue the Task 011 final implementation prompt, does not decide D1–D8
(recommendations only), does not authorize the MBQ-05 branch B task, and
does not authorize any code. The next session it specifies must itself be
explicitly issued by ChatGPT.
