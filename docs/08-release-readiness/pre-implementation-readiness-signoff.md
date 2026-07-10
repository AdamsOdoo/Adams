# Pre-Implementation Readiness Signoff — Task 011 Gate Package (AR-039)

> **Status: Proposed for ChatGPT review — NOT an acceptance, NOT a gate
> act.** Docs-only. Prepared 2026-07-10 by the AR-039 gate-readiness
> session, after PR #143 (AR-038 audit/planning closure) merged into
> `Shopify-connector` (merge commit `4a45f3e`, verified via GitHub
> `pull_request_read`, merged 2026-07-10T05:35:06Z). This document states
> whether the repository is now ready for ChatGPT to open the Task 011
> implementation gate **after reviewing/merging this package and
> performing its own explicit acts** — it does not perform any of those
> acts. The customer-domain gate is **closed**; Task 011 is
> **unauthorized**; no implementation prompt is issued or usable.

> **Acceptance note (2026-07-10, PR #144 control-room review, comment ID
> `4932704451` — supersedes the "Proposed" wording above, which is
> preserved as the accurate drafting-time record).** ChatGPT accepted
> this package with two required fixes, both applied in this same PR
> (D1 recall-safe candidate discovery; the merge-safety status patch —
> see the AR-039 Acceptance Note in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
> §3's blocker 1 is thereby closed; blockers 2–4 (merge, the distinct
> gate-opening act, prompt issuance) remain ChatGPT's own outstanding
> acts. **No gate is opened, no prompt is issued or usable, Task 011–015
> remain unauthorized, and MBQ-05 branch B remains undecided.**

## 1. Implementation-readiness conclusion

**[Recommendation] Ready — Option A.** After ChatGPT reviews and merges
this package, every customer-domain gate criterion is either already
satisfied or satisfied by that same acceptance, and the criterion-12
blocker reconfirmation evidence is assembled for the gate act. **No
research, documentation, decision-input, or live-access blocker stands
between the current state and an openable Task 011 gate.** What remains
is exclusively ChatGPT's own acts (§4). This is the state
[`final-pre-implementation-roadmap.md`](./final-pre-implementation-roadmap.md)
§2 step 2 targeted.

## 2. Completed items (this session, all docs-only, all subject to review)

1. **D1–D8 closed at recommendation level** —
   [`../07-implementation-plan/task-011-decision-closure-brief.md`](../07-implementation-plan/task-011-decision-closure-brief.md):
   exact dedup/match thresholds incl. normalization, archived-partner and
   binding-conflict rules (D1); exact ambiguous-candidate evidence field
   + JSON shape + PII posture (D2); defaultAddress-only, create-only
   address mapping with explicit deferrals (D3); person-only
   classification (D4); exact fallback-partner field mechanics under
   Posture A (D5); `depends: ['shopify_connector_core']` only, with the
   Odoo-`sale`-app dependency also explicitly deferred to Task 012 (D6);
   exact single-customer GraphQL query field list, seams incl. the
   existing `sale_domain_enabled` flag, pinned enumeration posture (D7);
   four exact test files with full case coverage + Odoo.sh expectations
   (D8).
2. **Task 011 final implementation prompt drafted, marked unusable** —
   [`../07-implementation-plan/task-011-final-implementation-prompt.md`](../07-implementation-plan/task-011-final-implementation-prompt.md),
   first line: *DO NOT USE UNTIL CHATGPT REVIEWS, ACCEPTS, EXPLICITLY
   OPENS THE TASK 011 GATE, AND ISSUES THIS PROMPT.* File-exact allowed/
   forbidden lists, schema, rules, tests, rollback, definition of done,
   Odoo.sh validation requirement, stop condition, report format.
3. **Customer-domain gate-opening proposal drafted** —
   [`../07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md`](../07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md):
   all 15 criteria evidenced (7 Satisfied · 7 Satisfied-on-acceptance ·
   criterion 12 as the gate-act item with its reconfirmation table
   re-verified 2026-07-10).
4. **MBQ-05 branch B decision brief** —
   [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md):
   evidence-backed **not-blocking** conclusion for Task 011; parallel
   authorization recommended; the 2026-07-10 distribution/PCD option
   space (no review-free multi-merchant route exists; candidate set
   B-1–B-4; open questions named); scoped next-task proposal.
5. **Official-source refresh (OP-13/CL-5 hygiene, repeated at drafting
   time per standing practice)** — every Task 011 platform fact
   re-fetched 2026-07-10 (not assumed from the 2026-07-09 audit), with
   an adversarial verification pass over the seven load-bearing claims
   (all confirmed); excerpts captured under
   [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
   (**closing OP-44's capture routing**), and the Tier-1 Customer-object
   gap in
   [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
   closed with a dated 2026-07-10 section.
6. **Stale-docs cleanup** — OP-24 (MBQ-55 and MBQ-04 register rows
   refreshed with dated notes recording already-made acceptances/merges,
   no new decision); OP-25 (the five stale "Empty"/outdated READMEs —
   00-source-materials, 02-product, 04-decisions index note,
   07-implementation-plan, 08-release-readiness — refreshed with dated
   notes; remaining OP-25 items routed, §5); OP-42
   (`quality-feedback-loop.md` §10/§11 binding-status ambiguity flagged
   in-file, decision left to ChatGPT); OP-43 (classified below, §6).
7. **Registers/handoff updated** — new AR-039 row (Proposed);
   open-points register and implementation-readiness map addenda; new
   handoff top entry with the exact next-session prompt.

## 3. Remaining blockers for the Task 011 gate

**Only ChatGPT acts. No worker-session blocker remains.**

| # | Blocker | Class | Closed by |
| --- | --- | --- | --- |
| 1 | Review/accept this package (D1–D8 + final prompt + gate proposal) — OP-02 | G | ChatGPT review of this draft PR |
| 2 | Merge this PR into `Shopify-connector` | G | ChatGPT merge authorization (merging authorizes nothing by itself) |
| 3 | The distinct, explicit customer-domain gate-opening act, incl. the criterion-12 confirmation — OP-01 | G | ChatGPT act (gate proposal §1/§3) |
| 4 | Issue the final prompt verbatim in a new session | G | ChatGPT chat turn, after 1–3 |

## 4. Exact next ChatGPT action

1. Review this draft PR (Option A bar: nothing vague should remain — if
   anything is found vague, classify it and require revision rather than
   inferring).
2. If accepted: merge; then perform the **gate-opening act** (distinct,
   explicit, confirming the criterion-12 table as of that date).
3. Separately decide **MBQ-05 branch B parallel authorization**
   (recommended; not blocking either way).
4. Optionally give the one-line **OP-42** binding confirmation and set
   the allowed-files list for the §5 residual maintenance batch.
5. Then, as its own later act, issue
   [`../07-implementation-plan/task-011-final-implementation-prompt.md`](../07-implementation-plan/task-011-final-implementation-prompt.md)'s
   draft prompt text, verbatim, in a **new** Claude Code session.

## 5. Non-blocking open items (tracked, unaffected claims)

- **Later-MVP chain (B-class):** MBQ-55 order portion + order-domain
  criteria (OP-14/OP-15); MBQ-56/MBQ-27 (OP-16/OP-17); inventory pass +
  MBQ-32 (OP-18/OP-19); fulfillment pass + exact scope set + TD-002 fix
  routing (OP-20/OP-03); Task 015 planning (OP-21); Area 6 trigger call
  sites (OP-28); UI chain (OP-26); Lite/Full framing (OP-23); MBQ-05
  branch B decision itself (OP-05/OP-40/OP-31).
- **Remaining OP-25 maintenance residue (routed, not done here — files
  deliberately left untouched to keep this PR reviewable):** the MVP
  QA/test-strategy package's 2026-07-07-era status headers
  (`docs/05-qa/mvp-qa-test-strategy.md`, `foundation-test-matrix.md`,
  `domain-e2e-test-matrix.md`, `data-integrity-idempotency-test-plan.md`,
  `security-redaction-test-plan.md`); the release-checklist/UAT-scenarios
  freshness preambles and their unaccepted "Proposed" headers
  (`mvp-release-readiness-checklist.md`, `mvp-uat-scenarios.md`);
  DEC-021/DEC-024/DEC-025 status-wording artifacts (decision records —
  should only be touched with explicit ChatGPT authorization);
  `docs/01-research/research-backlog.md` RB-14.1 stale note. Reason per
  file: historical-preamble staleness only; none misleads about the
  current gate state now that the registers/READMEs are refreshed.
- **OP-41 minor per-task residuals** — unchanged, tracked in their own
  records (incl. the stale TD-001-era test comment, which only a future
  gated code task may touch).
- **OP-33** (`@idempotent` count discrepancy) — deferred to the first
  consuming write-domain task, unchanged.

## 6. Live-access items (cannot be closed by any docs session)

| Item | State (re-verified 2026-07-10) | Needs |
| --- | --- | --- |
| VAL-B2 (OP-06) | BLOCKED, never executed; plan accepted (DEC-023) | Human operator with Shopify Partner/Dev Dashboard access |
| Concurrency proofs SRR-03/04/09 (OP-22) | Plan merged (PR #134), never executed | Live Odoo.sh/multi-server runtime |
| UAT execution (OP-29) / release checklist (OP-30) | 0/15 scenarios executable; unchanged | Tasks 011–014 + UI + VAL-B2 + runtime |
| Blocked research sources (OP-32) | Unchanged | Owner-granted access |
| **OP-43** (Task 010 test-count arithmetic) | **Classified:** evidence-precision flag only; the accepted green outcome (0 failed/0 errors, AR-036) is not disputed and is the only thing any document relies on; the per-module figures remain unreconciled until a fresh build log exists. This package cites only the green outcome, and the final prompt bakes the quote-verbatim rule into Task 011's validation record. | Next runtime session captures verbatim summary lines |

## 7. What this session did NOT do (explicit)

Did not implement any code; did not edit any addon/code/XML/CSV/manifest/
security/migration/workflow/test/requirements/Docker/CI file; did not
open any gate; did not issue any usable prompt; did not authorize Task
011/012/013/014/015; did not decide D1–D8 (recommendations only); did
not decide MBQ-05 branch B; did not resolve VAL-B2, TD-002, MBQ-56,
MBQ-27, MBQ-32, Lite/Full, or SRR-03/04/09; did not weaken any accepted
DEC/AR/RA/MBQ record; did not touch `main` or plain `dev`; did not
merge anything.

## 8. Self-review / red-team findings (session-level)

The mandated 15-point self-review was run before the draft PR opened;
its findings and dispositions are recorded in the PR body ("Self-review /
red-team findings") and summarized in the handoff entry. Draft-changing
findings included: correcting the `sale.order` compute citation to the
two separate `address_get(['invoice'])`/`address_get(['delivery'])`
calls after the source read; adding the archived-search
`active_test=False` implementation note so D1 rule 7 is actually
implementable as written; recording the `updated_at` "whole day"
filter-description caveat as an open question instead of assuming
sub-day precision; keeping DEC status-wording artifacts out of this
PR's cleanup scope (decision records need explicit authorization);
and adding the D6 no-Odoo-`sale`-app-dependency point that the roadmap
row had not spelled out.

**Next step:** ChatGPT review of this draft PR (§4).
