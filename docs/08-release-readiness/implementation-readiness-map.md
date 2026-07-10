# Implementation Readiness Map — Post-PR #140 State of Every Task and Gate

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Does not
> authorize implementation, does not open any gate.** Prepared 2026-07-09
> as part of the post-PR #140 master audit
> ([`project-readiness-master-audit.md`](./project-readiness-master-audit.md)).
> Successor-in-function to the Task-010-era
> [`../07-implementation-plan/master-implementation-readiness-checkpoint.md`](../07-implementation-plan/master-implementation-readiness-checkpoint.md)
> and the Task-011-scoped
> [`../07-implementation-plan/task-011-customer-import-gate-readiness.md`](../07-implementation-plan/task-011-customer-import-gate-readiness.md)
> (both are preserved unchanged as historical records; where their "next
> step" lines said "ChatGPT's final merge review of PR #140," that step is
> now complete — merge commit `0e138d9`).

## 1. Task-by-task map

Gate lifecycle vocabulary (established Tasks 002–010 pattern):
`unproposed → criteria/scope proposed → criteria/scope accepted →
final prompt drafted (not issued) → gate opened (explicit ChatGPT act,
one session only) → implementation PR (draft, review, merge) →
runtime-validated → closed/exhausted`.

| Task | Scope | Gate status | Implementation status | Runtime evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| 001 | Core module scaffold | Closed/exhausted (AR-021 limited core gate) | Merged (PR #88) | Live Odoo.sh validated (Task 001A, PR #89) | None — closed |
| 002 | Credential storage/masking/redaction | Closed/exhausted (AR-026) | Merged (PR #97) | Live validated (via later green suites) | None — closed |
| 003 | Read-only API client + test connection | Closed/exhausted (AR-029) | Merged (PR #101 + hotfixes #103–#106) | Live partial validation (PR #107); **VAL-B2 still BLOCKED** (deferred by DEC-021, routed by DEC-023) | VAL-B2 live evidence (OP-06) |
| 004 | Readiness-check substrate (+ TD-001 fix) | Closed/exhausted (PR #114 gate acceptance) | Merged (PR #115) | Live green 78/78 + 31/31 (`task-004-validation-results.md`) | None — closed (TD-001 Resolved) |
| 005 | Connection lifecycle actions | Closed/exhausted (DEC-022, PR #120) | Merged (PR #121, after 2 runtime-defect REVISE cycles) | Live green 123/123 (DEC-024) | None — closed |
| 006A/B/C/D | Sync-engine research → architecture gate → skeleton | 006B accepted (DEC-025); 006C gate closed/exhausted (AR-031) | 006C merged (PR #131) | Live green (AR-032; two runtime defects fixed pre-merge) | Concurrency plan (PR #134) unexecuted (OP-22) |
| **010** | Product import / variant binding | **Closed/exhausted** (criteria accepted PR #136/AR-034; gate opened PR #137/AR-035; closed when PR #138 opened as draft) | **Merged** (PR #138; closure PR #139) | **0 failed / 0 errors** (recorded as "of 220 tests"), Odoo.sh, 2026-07-09 (§K; OP-43 flags the record's per-module count arithmetic) | None for the import slice. Not operator-triggerable yet (no enqueue call site — OP-28); export/update is Task 015 |
| **011** | Customer import / matching | **Criteria accepted as criteria only** (PR #140/AR-037, comment `4928377625`); **gate CLOSED**; 7/15 criteria satisfied | Not started — `shopify_connector_sale` does not exist | n/a | Final-prompt + gate-opening-proposal session (OP-02), gate act (OP-01), then one implementation session |
| 012 | Order import | **Unproposed criteria**; order-binding naming pass never run | Not started | n/a | OP-14/OP-15/OP-16/OP-17 after Task 011 closes |
| 013 | Inventory sync | **Unproposed criteria** | Not started | n/a | OP-18/OP-19 after Task 010 (product) — sequenced after 012 per the accepted order, but structurally dependent only on product |
| 014 | Fulfillment/tracking | **Unproposed criteria**; write model already decided (DEC-011) | Not started | n/a | OP-20 (incl. exact scope set + TD-002 fix routing) after Task 012 |
| 015 | Controlled product export/update | In MVP scope (DEC-003/PR #55) but never proposed as a task | Not started | n/a | Own proposal + naming/criteria pass when sequenced (OP-21) |
| Area 6 | Manual/scheduled sync trigger call sites | Never gated | Not started | n/a | OP-28 — converts backend domains into operator-usable behavior |
| UI Groups 1–15 | Menus/dashboard/wizard/screens | UI implementation gate never opened; zero views exist | Not started | n/a | OP-26; wizard OAuth step additionally needs OP-05 + OP-06 |
| OAuth / token distribution | Setup-facing acquisition | No gate exists | Not started | n/a | MBQ-05 branch B decision first (OP-05) |
| Webhooks | Per-domain slices | Posture accepted (layered, never webhook-only); no code gate | Not started | n/a | Per-domain proposals when reached (OP-27) |
| Lite/Full packaging | Product/licensing shape | Undefined concept | Not started | n/a | Q27 framing decision, then planning task (OP-23) |

## 2. Customer-domain gate criteria — live satisfaction table

Source: [`../07-implementation-plan/customer-domain-gate-criteria-proposal.md`](../07-implementation-plan/customer-domain-gate-criteria-proposal.md)
§3 (Accepted as criteria only, comment `4928377625`). Statuses below are
restated from that document; nothing is newly satisfied by this audit.

| # | Criterion | Status | Satisfiable by |
| --- | --- | --- | --- |
| 1 | Task 010 closed and runtime-green | **Satisfied** | — |
| 2 | MBQ-55 customer-binding portion accepted | **Satisfied** | — |
| 3 | Final prompt has exact file/model/field names | Not yet | Final-prompt session |
| 4 | Exact allowed/forbidden files defined | Not yet | Final-prompt session |
| 5 | Dedup/match-confidence thresholds fixed or explicitly in-task | Not yet | Final-prompt session (OP-10) |
| 6 | No order-import scope | **Satisfied** (must remain so) | — |
| 7 | No product/inventory/fulfillment scope | **Satisfied** | — |
| 8 | No UI/wizard/webhook/OAuth scope | **Satisfied** | — |
| 9 | Exact test files confirmed | Not yet | Final-prompt session |
| 10 | Rollback plan defined | **Satisfied** (restate in prompt) | — |
| 11 | No live-Shopify dependency beyond Task 003 client | **Satisfied** | — |
| 12 | Blocker classification reconfirmed at gate time | Not yet (point-in-time act) | Gate-opening act |
| 13 | Fallback-partner field + Posture A boundary in prompt | Not yet (name/home/boundary accepted; mechanics open) | Final-prompt session (OP-11) |
| 14 | Address handling + `is_company` explicitly scoped | Not yet | Final-prompt session (OP-07/OP-08 — decision inputs ready) |
| 15 | Ambiguous-match handling incl. exact job/log candidate fields | Not yet (principle accepted) | Final-prompt session (OP-09) |

**[Inference]** Every unsatisfied criterion is resolvable by exactly one
docs-only drafting session plus the gate-opening act itself. No research,
code, or live-access blocker stands between the current state and an
openable customer-domain gate.

## 3. Cross-cutting readiness layers

| Layer | State | Evidence | Gap |
| --- | --- | --- | --- |
| Governance / decision base | Complete: DEC-003–025 accepted; AR-001–037 accepted; RA-001–024 binding | Master audit §2.3 | None |
| Core substrate | Merged, runtime-green, sufficient for Task 011 (incl. `read_customers` already in `REQUIRED_MVP_SCOPES`) | Master audit §2.2/§6 | Concurrency proof (OP-22) |
| Domain code | Product import only | Addon tree | Tasks 011–015 |
| Operator surface | **None** (zero views; no trigger call sites) | Addon tree; OP-26/OP-28 | Entire UI chain |
| Live-Shopify evidence | **None ever** (VAL-B2 BLOCKED) | OP-06 | Human-operator execution of the closure plan |
| Distribution/auth architecture | Branch A (one-store evidence) routed only | DEC-023 | Branch B decision (OP-05) |
| UAT | 0/15 scenarios executable | [`uat-readiness-gap-analysis.md`](./uat-readiness-gap-analysis.md) | See that file |
| Release | Checklist template ready; nothing executable | OP-30 | Roadmap tail |

## 4. AR-039 session addendum (2026-07-10) — Task 011 row and criteria-table delta

> Added by the AR-039 gate-readiness session. §1/§2 above are preserved
> unchanged as the 2026-07-09 baseline. Current delta, **Proposed for
> ChatGPT review** (nothing below opens a gate or authorizes a task):

- **Task 011 row delta:** the "Final-prompt + gate-opening-proposal
  session (OP-02)" step is now **done at proposal level** — the AR-039
  package drafts the final prompt (marked not usable), the gate-opening
  proposal, and the D1–D8 decision-closure brief. Remaining work is
  exclusively ChatGPT's: package acceptance + merge, the gate act
  (OP-01), then prompt issuance.
- **Criteria-table delta (§2):** criteria 3, 4, 5, 9, 13, 14, 15 move
  from "Not yet / Final-prompt session" to **"Satisfied-on-acceptance —
  drafted in
  [`../07-implementation-plan/task-011-final-implementation-prompt.md`](../07-implementation-plan/task-011-final-implementation-prompt.md),
  effective when ChatGPT accepts the AR-039 package"**; criterion 12's
  reconfirmation evidence is assembled in
  [`../07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md`](../07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md)
  §3 (the confirmation itself belongs to the gate act). Criteria 1, 2,
  6, 7, 8, 10, 11 unchanged (Satisfied).
- **§3 layer delta:** "Distribution/auth architecture" gains the
  branch B blocking analysis
  ([`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md)
  — not blocking Task 011); every other layer unchanged.

## 4.1 AR-041 session addendum (2026-07-10) — distribution/auth architecture layer

> Added by the AR-041 MBQ-05 branch B research/decision-preparation
> session. §1–§4 above are preserved unchanged. Current delta, **Proposed
> for ChatGPT review** (nothing below opens a gate or authorizes any
> task). **This addendum only patches the "Distribution/auth
> architecture" layer — it does not touch, and must not be read as
> confirming current, the Task 011 row in §1 or the "Domain code"/
> "Operator surface" rows in §3; those are addressed separately by §4.2
> below, which supersedes them after PR #145.**

- **§3 "Distribution/auth architecture" layer delta:** the branch B
  blocking analysis (§4 row) is now followed by a **complete decision
  package** —
  [`../03-architecture/mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
  (full B-1/B-2/B-3/B-4 evaluation, official evidence re-verified and
  gap-filled 2026-07-10, adversarial verification of five load-bearing
  claims) and
  [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md)
  (**Proposed, not accepted**). The layer's state moves from "Branch A
  (one-store evidence) routed only; branch B decision (OP-05) open" to
  "Branch A unchanged; a fully-evidenced branch B recommendation is
  ready for ChatGPT review — architecture decision itself still open."
- **OAuth / token distribution row (§1) delta:** unchanged in status
  ("No gate exists; Not started") — a decision package now exists to
  inform the eventual gate, but no gate is opened and no implementation
  is authorized by this addendum.
- **Lite/Full packaging row (§1) delta:** unchanged ("Undefined concept;
  Not started") — the final decision brief's §7 fit-analysis for each
  candidate is explicitly contingent on OP-23/Q27 being answered first,
  and does not itself answer it.
- **New dependency surfaced, not previously named in this map:** the
  MBQ-04 encryption-posture tension (PCD Level 2's review-enforced
  obligations vs. the accepted Task 002 plain-`Char`-plus-ACL credential
  posture) is now an explicit, named prerequisite for any future public-
  app (B-1/B-2) implementation work — see the final decision brief §4 and
  §1.1. This does not change MBQ-04's own row/status in
  [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md);
  it only records the dependency here.

## 4.2 Post-PR #145 status-refresh note (2026-07-10) — Task 011 closed/exhausted

> Added by this docs-only PR #146 status-refresh patch, per ChatGPT
> review comment
> [`4935147220`](https://github.com/AdamsOdoo/Adams/pull/146#issuecomment-4935147220).
> **§1's Task 011 row and §3's "Domain code"/"Operator surface" rows above
> are historical, pre-PR-#145 baseline text — they are left unedited
> here as the least-risky option, and are superseded by the facts in
> this note, not still current.** Nothing below opens any new gate or
> authorizes any task.

- **[Fact]** PR #145 ("Task 011: Shopify customer import and matching")
  merged into `Shopify-connector`, merge commit
  `7e83abba502c898fa413822c4d9b4866138a454a`.
- **[Fact]** Task 011 customer import/matching is now **implemented and
  merged**. The `shopify_connector_sale` addon now exists (the
  `shopify.connector.customer.binding` model; the read-only
  `shopify.connector.customer.importer` importer service; the inert
  `customer_fallback_partner_id` store-settings field, Posture A).
- **[Fact]** Runtime validation is green: **`0 failed, 0 error(s) of 268
  tests`** (operator-provided Odoo.sh install log — see the AR-040 row in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  and
  [`../05-qa/task-011-customer-import-validation-results.md`](../05-qa/task-011-customer-import-validation-results.md)
  §J).
- **[Fact]** The Task 011 customer-domain implementation gate is now
  **closed/exhausted** — it closed the moment PR #145 opened as draft
  (per the accepted gate-closure rule) and PR #145 has since merged with
  runtime-green evidence; no further customer-domain work may start
  without a distinct, future, explicit ChatGPT act.
- **Table-row supersession (§1/§3 above):** the §1 Task 011 row ("Not
  started — `shopify_connector_sale` does not exist"; "Final-prompt +
  gate-opening-proposal session (OP-02), gate act (OP-01), then one
  implementation session") and the §3 "Domain code" row ("Product import
  only") are both **superseded by the facts above** — Task 011 is no
  longer "not started," `shopify_connector_sale` exists and is merged,
  and domain code now includes the merged customer-import slice, not
  product import alone.
- **Explicit non-authorizations (unchanged by this note):** this note
  does **not** authorize Task 012, Task 013, Task 014, Task 015, UI,
  OAuth, webhooks, or Lite/Full packaging implementation of any kind, and
  does not authorize MBQ-05 branch B implementation.
- **Historical / superseded by §4.3 below (2026-07-10 correction, per
  ChatGPT review comment
  [`4936371088`](https://github.com/AdamsOdoo/Adams/pull/147#issuecomment-4936371088)
  on PR #147):** at the time this §4.2 note was added (the PR #146 merge),
  PR #146 / AR-041 was a branch-B **decision package only** —
  [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md)
  was then **Proposed for ChatGPT review, NOT accepted**, and **MBQ-05
  branch B was then undecided**. **That pre-acceptance status is
  superseded for strategic-direction purposes by §4.3 below**, which
  records that ChatGPT has since accepted DEC-026's hybrid recommendation
  as the strategic branch-B distribution/auth direction — implementation
  remains gated separately and is **not** authorized by that acceptance;
  RA-003 is **not** lifted; MBQ-04, OP-23/Q27, OP-45, and OP-46 remain
  open. **This §4.2 note remains authoritative only for the PR #145 /
  Task 011 factual closure it records above** (Task 011 merged,
  runtime-green, gate closed/exhausted) — it does not touch, edit, or
  reopen PR #145, and does not alter any Task 011 implementation record
  except to reference its already-merged, runtime-green status.

## 4.3 DEC-026 acceptance status-refresh note (2026-07-10) — distribution/auth architecture layer

> Added by this docs-only DEC-026 acceptance/status patch session, per
> ChatGPT's explicit decision to accept DEC-026's hybrid recommendation as
> the strategic branch-B distribution/auth direction. §4.1 above is
> preserved unchanged as the pre-acceptance baseline; this note is the
> current delta. **Nothing below opens a gate or authorizes any
> implementation task.**

- **[Fact]** ChatGPT has accepted
  [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md)
  (2026-07-10) as the strategic branch-B distribution/auth direction — see
  that document's "Acceptance note" and the AR-041 row in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
  §4.1's characterization ("architecture decision itself still open") is
  superseded at the **strategic-direction** level only, by this note.
- **"Distribution/auth architecture" layer state moves to:** "Branch A
  unchanged; Public distribution/Limited Visibility (candidate B-1)
  accepted as the target scalable branch-B architecture (strategic
  direction only); engineering implementation remains gated separately —
  not authorized."
- **"OAuth / token distribution" row (§1) — unchanged in status:** "No
  gate exists; Not started." An accepted strategic direction now exists,
  but no gate is opened and no implementation is authorized by this note.
- **"Lite/Full packaging" row (§1) — unchanged:** "Undefined concept; Not
  started" — OP-23/Q27 remains open and is a named prerequisite, not
  resolved here.
- **Five prerequisites remain open**, unchanged by this note: the MBQ-04
  encryption-posture decision; OP-23/Q27 (Lite/Full packaging mechanism);
  OP-46 (DEC-023 branch-A single-vs-plural pilot-customer scope
  clarification); a separate RA-003 deferral-lift act; and OP-45 (Partner
  Program Agreement fee-schedule / "Enforcement" page sourcing).
- **Explicit non-authorizations:** this note does not authorize OAuth,
  a setup wizard, App Store packaging, billing integration, compliance
  webhooks, any UI, or Task 012/013/014/015 work; does not lift RA-003;
  does not resolve MBQ-04, OP-23/Q27, OP-45, or OP-46.

## 5. Explicit non-authorizations

This map does not open any gate or authorize any implementation task. §2
restates the historical customer-domain criteria document; §4 records
AR-039 gate-readiness deltas; §4.1 records the AR-041 distribution/auth
decision-package delta; §4.2 records the post-PR #145 factual Task 011
status refresh; and §4.3 records the DEC-026 acceptance status refresh
(strategic direction accepted, implementation gated separately). Any
future task authorization or gate opening must come from its own
governing document or an explicit ChatGPT act.
