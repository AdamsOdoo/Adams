# Task 011 — Customer-Domain Gate-Opening Proposal

> **Status: Proposed for ChatGPT review — NOT accepted. The
> customer-domain gate is CLOSED and remains closed until ChatGPT's own
> distinct, explicit gate-opening act.** Docs-only. Prepared 2026-07-10
> by the AR-039 gate-readiness session — the exact analogue of the
> accepted Task 010 gate-opening proposal
> ([`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md),
> AR-035/PR #137 pattern) for the customer domain. This document audits
> all 15 accepted gate criteria
> ([`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
> §3, **Accepted as criteria only**, comment `4928377625`) and presents
> the evidence that every previously-unsatisfied criterion is now
> satisfied **or becomes satisfied by ChatGPT's acceptance of this same
> package** — it does not itself open the gate, satisfy criteria by
> fiat, or authorize any code.

> **Acceptance note (2026-07-10, PR #144 control-room review, comment ID
> `4932704451` — supersedes the "NOT accepted" wording above, which is
> preserved as the accurate drafting-time record).** ChatGPT accepted
> this package with two required fixes, both applied in this same PR
> (see the AR-039 Acceptance Note in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
> With that acceptance, criteria 3/4/5/9/13/14/15's
> "Satisfied-on-acceptance" status in §2 takes effect once PR #144
> merges. **The customer-domain gate itself remains CLOSED** — the
> acceptance comment explicitly does not perform the gate-opening act
> ("Do not open the gate"); criterion 12's point-in-time confirmation
> and the distinct, explicit gate-opening act remain outstanding
> ChatGPT acts (§1/§3). Task 011 remains unauthorized; the final prompt
> remains not issued.

## 1. What this proposal asks ChatGPT to do (and not do)

If ChatGPT, on review, (a) accepts
[`task-011-final-implementation-prompt.md`](./task-011-final-implementation-prompt.md)
(fixing its content as binding — still not issued) with the D1–D8
recommendations in
[`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md),
(b) confirms the §2 criterion table below, including the criterion-12
point-in-time blocker reconfirmation, and (c) **performs the distinct,
explicit customer-domain gate-opening act** — then the gate opens for
**exactly one** future Task 011 implementation session and closes again
the moment that session's PR opens as draft (the accepted §4 rule).

This document performs none of those acts. Accepting this proposal
without the explicit gate-opening act does **not** open the gate.
Opening the gate does **not** issue the prompt — issuance is a further,
separate ChatGPT chat turn in a new session (final prompt, "How this
document will be used," conditions 1–6).

## 2. Criterion-by-criterion table (all 15)

Statuses: **Satisfied** (evidence already merged/on record) ·
**Satisfied-on-acceptance** (the drafted content in this package
satisfies it; becomes effective when ChatGPT accepts this package) ·
**Gate-act item** (a point-in-time confirmation belonging to the
gate-opening act itself).

| # | Criterion (abbrev.) | Status | Evidence | Owner / exact ChatGPT action needed |
| --- | --- | --- | --- | --- |
| 1 | Task 010 closed and runtime-green | **Satisfied** | PR #138 merged (merge commit `1f47803`); post-merge Odoo.sh build green — **0 failed, 0 error(s)** (recorded basis of AR-036's acceptance; the record's per-module count arithmetic is flagged as OP-43 and is not relied on here — only the green outcome is); PR #139 closure docs merged (`297f398`); product gate closed/exhausted | None — already satisfied |
| 2 | MBQ-55 customer-binding portion accepted | **Satisfied** | [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md) Accepted (comment `4928377625`, PR #140 merged `0e138d9`), incl. corrected ambiguous-match posture + Posture A boundary | None — already satisfied |
| 3 | Final prompt has exact file/model/field names | **Satisfied-on-acceptance** | Final prompt §3 (13 exact addon files + 3 exact docs files), §7 (exact model `shopify.connector.customer.binding`, class names, every field with exact type), §9 (exact job type, seams, query field list) | ChatGPT accepts the final prompt |
| 4 | Exact allowed and forbidden files defined | **Satisfied-on-acceptance** | Final prompt §3 (exhaustive allowed list) and §4 (explicit forbidden list incl. zero core/product edits, no UI/webhook/OAuth/CI/migration, `adams_base` untouched, "any file not named in §3") | ChatGPT accepts the final prompt |
| 5 | Dedup/match-confidence thresholds fixed or explicitly in-task | **Satisfied-on-acceptance** | Final prompt §8.1 fixes the full threshold set as named in-task decisions (existing-binding → normalized-email exact-one → create-eligible zero-match → ambiguous/blind/archived routing, no-bypass rule) per D1 ([`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md) D1, official Odoo 19 source evidence re-verified 2026-07-10) | ChatGPT accepts D1 via the final prompt |
| 6 | No order-import scope | **Satisfied** (and preserved) | Standing exclusion in both Task 011 scope docs; final prompt §4/§6 restate it verbatim, incl. zero `sale.order` references and zero `customer_fallback_partner_id` consumption | None — confirm unchanged on review |
| 7 | No product/inventory/fulfillment scope | **Satisfied** (and preserved) | Same sources; final prompt §4/§6 | None — confirm unchanged on review |
| 8 | No UI/wizard/webhook/OAuth scope | **Satisfied** (and preserved) | Same sources; final prompt §4/§6; additionally: no distribution/auth assumption may be baked in (MBQ-05 brief §2) | None — confirm unchanged on review |
| 9 | Exact test files confirmed | **Satisfied-on-acceptance** | Final prompt §10 confirms the four accepted file names and enumerates every required positive/negative/guard case per D8 | ChatGPT accepts D8 via the final prompt |
| 10 | Rollback plan defined | **Satisfied** (restated precisely) | Accepted rollback posture restated in final prompt §13 (single-PR revert; no dependent module; unbound `res.partner` data preserved) | None — confirm restatement on review |
| 11 | No live-Shopify dependency beyond Task 003 client | **Satisfied** (and preserved) | Final prompt §6/§9: fake/stub tests only; reads only through the existing unmodified client; VAL-B2 untouched | None — confirm unchanged on review |
| 12 | Open blockers reconfirmed non-blocking at gate time | **Gate-act item — reconfirmation evidence assembled below (§3)** | §3 re-verifies each blocker against current GitHub/register/official-source state, 2026-07-10 | **ChatGPT confirms §3 as part of the gate-opening act itself** (point-in-time, per the accepted criterion text) |
| 13 | Fallback-partner field + Posture A boundary in prompt | **Satisfied-on-acceptance** | Final prompt §7.2 fixes exact type (`Many2one('res.partner')`, `ondelete='restrict'`), no default, no auto-creation, ordinary write path, and restates the Posture A boundary verbatim; §10 requires the outcome-equivalence proof (D5) | ChatGPT accepts D5 via the final prompt |
| 14 | Address handling + `is_company` explicitly scoped | **Satisfied-on-acceptance** | Final prompt §8.3 (defaultAddress-only, create-only writes, lookup-only country/state, explicit deferrals) and §8.4 (person-only, company string unmapped, B2B non-MVP) per D3/D4, official-source facts re-verified 2026-07-10 | ChatGPT accepts D3/D4 via the final prompt |
| 15 | Ambiguous-match handling incl. exact job/log candidate fields | **Satisfied-on-acceptance** | Final prompt §8.1(6) (no binding row, `blocked_manual_review`/`ambiguous_match`, manual-confirm-then-bind) + §8.2 (exact field: existing `job.log.technical_detail`; exact JSON shape; PII posture; tests) per D2 | ChatGPT accepts D2 via the final prompt |

**Summary:** 7 criteria already Satisfied; 7 become satisfied by
accepting this package's drafted content; criterion 12 is the
point-in-time confirmation belonging to the gate act itself, with its
evidence fully assembled in §3. **No criterion requires research, code,
or live access beyond this package.**

## 3. Criterion-12 reconfirmation evidence (point-in-time, re-verified 2026-07-10)

The accepted classification
([`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
§5) held at PR #140 time; this section **re-verifies** (not assumes) each
named blocker as still non-blocking for Task 011's narrow backend scope:

| Blocker | Re-verified state (2026-07-10) | Still non-blocking for Task 011? |
| --- | --- | --- |
| MBQ-05 (branch B distribution/auth) | Register row unchanged (Partially routed / Open); dedicated blocking analysis in [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md) §2/§6: Task 011 performs no OAuth/distribution-dependent step; PCD access under the current custom-distribution evidence path is "Always available" (official page re-fetched 2026-07-10) | **Yes** |
| VAL-B2 (live Shopify connection) | Still BLOCKED, never executed ([`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md)); Task 011 is fake-client-only (criterion 11) | **Yes** |
| TD-002 (`read_fulfillments` scope naming) | Still Open (register re-read 2026-07-10); unrelated to customer import; Task 011 touches no readiness-check code | **Yes** |
| Fulfillment scope-set / API-model residual | Write model decided (DEC-011); residual scope-set choice routed to OP-20 — fulfillment domain only | **Yes** |
| Lite/Full packaging | Open at framing level (Q27); affects packaging, not customer-import models/logic | **Yes** |
| Multi-server concurrency proofs (SRR-03/04/09) | Plan merged (PR #134), still unexecuted; Task 011 inherits the unmodified Task 006C mechanism and adds no concurrency claim (final prompt hard constraint) | **Yes** — named cross-cutting risk, not a Task 011 precondition |
| MBQ-55 order-binding portion | Still fully open; blocks Task 012 only | **Yes** |
| Address/`is_company`/thresholds/job-log fields/manifest/query (the former A-class rows OP-07–OP-13) | All resolved at recommendation level by this package (D1–D8); they block only the *acceptance* of this package, not the gate once accepted | **Yes**, contingent on this package's acceptance |

No new blocker was found by this session's re-verification (repo sweep +
official-source refresh). **ChatGPT's gate-opening act should state that
it confirms this table as of the date of the act.**

## 4. What opening the gate authorizes (and does not)

- Authorizes **exactly one** future Task 011 implementation session,
  executing the accepted final prompt **only after ChatGPT separately
  issues it verbatim** in a new session (conditions 3–5 of the final
  prompt's usage list).
- The gate **closes again** the moment the Task 011 implementation PR
  opens as draft; that PR remains draft until ChatGPT's own review
  (accepted §4 rule, restated unchanged).
- Does **not** authorize Task 012 (order import) or any other task, any
  UI/webhook/OAuth work, any enumeration/trigger work (Area 6), or any
  MBQ-05 work — each needs its own future act.

## 5. Explicit non-authorizations

This proposal does not open the customer-domain gate (ChatGPT's distinct
act does); does not issue or render usable the final prompt; does not
decide D1–D8 (ChatGPT's acceptance does); does not resolve VAL-B2,
MBQ-05, MBQ-55's order portion, TD-002, MBQ-56, MBQ-27, MBQ-32, Lite/Full
packaging, or SRR-03/04/09; does not weaken any accepted DEC/AR/RA/MBQ
record; and does not start, schedule, or imply any implementation.

## Evidence / references

- [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
  §3/§4 (the accepted criteria and gate-closure rule) — Accessible, this
  repository, 2026-07-10.
- [`task-011-final-implementation-prompt.md`](./task-011-final-implementation-prompt.md),
  [`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md)
  — companion documents, this package — Accessible, 2026-07-10.
- [`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)
  (accepted structural precedent, AR-035) — Accessible, 2026-07-10.
- [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
  §5 (the blocker classification §3 re-verifies) — Accessible,
  2026-07-10.
- [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md)
  (OP rows cited per blocker) — Accessible, 2026-07-10.
- [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md)
  — companion blocking analysis — Accessible, 2026-07-10.
- GitHub `pull_request_read` (PR #143 merged 2026-07-10T05:35:06Z) and
  `git rev-parse` (tip `4a45f3e` at drafting time) — 2026-07-10.

**Next step:** ChatGPT reviews this package (draft PR). If accepted:
accept the final prompt (D1–D8 become fixed prompt content), confirm §3,
and — as a distinct, explicit act — open the customer-domain gate for
exactly one Task 011 implementation session. Then, later and separately,
issue the final prompt verbatim in a new session. None of those acts is
performed by this document.
