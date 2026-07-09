# Final Pre-Implementation Roadmap — From PR #140 to Implementation Resumption and MVP

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Proposed
> sequencing only — not a schedule, not an authorization, and not a gate
> act of any kind.** Prepared 2026-07-09 as part of the post-PR #140
> master audit. Every step below that requires a ChatGPT act says so;
> nothing here performs one. Near-term detail for the very next gate lives
> in [`../07-implementation-plan/next-gate-readiness-roadmap.md`](../07-implementation-plan/next-gate-readiness-roadmap.md).
> Open-point IDs (OP-xx) refer to
> [`open-points-closure-register.md`](./open-points-closure-register.md).

## 1. Where the project stands (facts, one paragraph)

Research Sprints A–G, the Master Blueprint program, and DEC-003–DEC-025
are accepted. The merged, runtime-green code base is
`shopify_connector_core` (credential/API-client/readiness/lifecycle/
sync-engine substrate) plus `shopify_connector_product` (read-only product
import — Task 010; 0/220 test failures on Odoo.sh). All implementation
gates ever opened are exhausted and closed. PR #140 merged the accepted
customer-binding naming proposal and the customer-domain gate criteria
(criteria only; gate closed). Task 011 implementation is not authorized;
Tasks 012–015, UI, OAuth, webhooks, and packaging are unproposed or
unauthorized. VAL-B2 (live Shopify evidence) and the concurrency proofs
remain outstanding runtime items. MBQ-05 branch B (scalable distribution)
remains the one open architecture question on the setup-facing chain.

## 2. The critical path back to implementation (backend chain)

Each numbered step is one PR-sized unit following the established
pattern. **Bold** = ChatGPT act.

1. **ChatGPT reviews and merges this audit PR** (docs-only). Merging
   authorizes nothing.
2. **ChatGPT issues the Task 011 final-prompt/gate-opening-proposal
   session** (the PR #137 analogue) using the handoff's next-session
   prompt. That session drafts, docs-only:
   - Task 011's file-exact final implementation prompt — carrying the
     eight decisions in the next-gate roadmap §4, marked
     **DO NOT USE UNTIL CHATGPT REVIEWS, ACCEPTS, AND EXPLICITLY ISSUES
     THIS PROMPT**;
   - the customer-domain gate-opening proposal (criterion-by-criterion
     satisfaction evidence, incl. the criterion-12 point-in-time blocker
     reconfirmation).
3. **ChatGPT performs the customer-domain gate-opening act** (accepts the
   proposal + prompt; gate opens for exactly one session and closes when
   the implementation PR opens as draft — the accepted §4 rule).
4. Task 011 implementation session (one session; creates
   `shopify_connector_sale` with the accepted
   `shopify.connector.customer.binding` model; draft PR; ChatGPT review
   cycles; live Odoo.sh validation mandatory per SRR-06 practice).
5. **ChatGPT merge review** → merge → post-merge closure docs PR
   (the PR #139 analogue), recording runtime evidence.

Steps 2–5 then repeat as a template per domain:

6. Order domain pre-pass (docs-only): MBQ-55 order-binding naming pass
   (OP-14) + order-domain gate-criteria proposal (OP-15) + decision
   briefs for MBQ-56 tolerance (OP-16) and MBQ-27 tax representation
   (OP-17). **ChatGPT accepts**, then final prompt → **gate act** →
   Task 012 implementation → closure.
7. Inventory domain pre-pass: naming + criteria (OP-18) + MBQ-32 residual
   decision (OP-19) → Task 013 cycle. (Structurally dependent only on
   product; sequenced here per the accepted domain order.)
8. Fulfillment domain pre-pass: naming + criteria + exact
   `*_fulfillment_orders` scope set, which also routes the TD-002 code
   fix (OP-20/OP-03) → Task 014 cycle.
9. Task 015 (controlled product export/update) proposal + naming/criteria
   pass → cycle (OP-21).
10. Area 6 — manual/scheduled sync trigger call sites (OP-28), making the
    backend domains operator-invokable.

## 3. Parallel tracks (non-competing with the backend chain)

- **P1 — MBQ-05 branch B research/decision task (OP-05).**
  **[Recommendation] authorize now, parallel to step 2.** Docs-only;
  non-competing (Task 011 performs no OAuth); on the critical path for the
  wizard, OAuth, packaging, and release; and the branch decision carries
  protected-customer-data Level 2 compliance consequences (OP-40) that are
  cheaper to know before customer/order implementations harden. Routed via
  RA-003's revisit condition (evaluation, not adoption).
- **P2 — VAL-B2 closure execution (OP-06).** Whenever a human operator
  with Shopify Partner/Dev Dashboard access is available — independent of
  every other track; follows
  [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md)
  exactly; redacted outcome only.
- **P3 — Concurrency validation execution (OP-22).** Whenever a live
  Odoo.sh/multi-server runtime is available; executes the merged PR #134
  plan against SRR-03/04/09.
- **P4 — Docs-maintenance micro-patch (OP-24/OP-25).** One small PR
  refreshing the MBQ-55 register row, the 04-decisions README index, the
  08-release-readiness README, and the stale freshness preambles.
  **ChatGPT** sets its allowed-files list.
- **P5 — Lite/Full packaging (OP-23).** **ChatGPT answers the Q27 framing
  question first**; the planning task then sequences naturally after (or
  with) P1's distribution outcome. Deliberately not on the backend
  critical path.

## 4. The setup-facing chain (after P1 and the backend chain)

11. UI foundation gate (task-map Group 1) → dashboard/readiness/
    credentials/settings screens (Groups 2, 4, 5, 6) — first UI slice;
    prerequisite for most UAT scenarios (OP-26).
12. Setup wizard (Group 3) — additionally requires P1 (MBQ-05 branch B)
    decided and P2 (VAL-B2) passed; wizard security constraints already
    recorded in DEC-023 §6.
13. Domain screens (Groups 7–15) alongside/after their domains.
14. Webhook slices per domain, if/when each domain task proposes its
    narrow slice under the accepted layered-sync posture (OP-27).

## 5. Validation / UAT / release tail

15. First UAT wave once §2 steps 1–5 + step 10 + step 11 land and P2
    passes: scenarios 1, 2, 3, 4, 5, 12, 13, 14, 15 become executable
    (see [`uat-readiness-gap-analysis.md`](./uat-readiness-gap-analysis.md)
    §3 for the exact mapping).
16. Second UAT wave after Tasks 012–014: scenarios 6–11.
17. Release-readiness execution: run
    [`mvp-release-readiness-checklist.md`](./mvp-release-readiness-checklist.md)
    item-by-item with evidence; requires TD-002 fixed (step 8), P3
    executed, P1 decided, packaging posture (P5) decided, and both UAT
    waves passed.

## 6. Sequence rationale and guardrails

- **Why Task 011 before order/inventory:** the accepted domain sequence
  (`mvp-domain-implementation-sequence.md`) and Task 012's own
  preconditions require customer bindings before order finalization;
  inventory is product-dependent but sequenced after orders per the
  accepted order — this roadmap preserves the accepted sequence unchanged.
- **Why the pre-pass pattern is mandatory per domain:** twice-confirmed
  lesson (product PR #136; customer PR #140 REVISE cycle) — a domain's
  gate is reliably undefined until a dedicated criteria proposal exists,
  and binding models with required Odoo-side relational fields must have
  their ambiguous-match posture fixed at naming time, not discovered
  in-task.
- **Guardrails carried forward unchanged:** one gate = one session; draft
  PRs until ChatGPT review; mandatory live Odoo.sh validation for anything
  concurrency/timing-sensitive (SRR-06); no webhook-only sync (DEC-005);
  no name-only matching (RA-006); no placeholder binding rows; no silent
  distribution/packaging assumptions in any task spec (DEC-023 §3.2).

## 7. Explicit non-authorizations

This roadmap authorizes none of its own steps. Every **bold** step is a
future ChatGPT act; every implementation step additionally requires its
own gate. No step may be started from this document alone.
