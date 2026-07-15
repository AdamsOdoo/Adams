# Claude MVP Wave Review Template

> Reusable control-room review prompt for the MVP completion program (`DEC-032`). Use this for every macro-wave PR Sol opens into `mvp/program-integration`, before deciding accept/revise/reject and before any merge. Copy this file's checklist into the wave's review record (a PR review comment, or a dated section appended to `docs/07-implementation-plan/mvp-program-state.md`) — do not just run through it silently.

## 0. Before you start

- Confirm you are reviewing a PR targeting `mvp/program-integration` (never `Shopify-connector` or `main` — those promotions are separate, later, product-owner-approved acts).
- Read the wave's own definition in `docs/07-implementation-plan/mvp-completion-program.md` §4 and the relevant task packet(s) it implements (e.g. `task-012-order-import-implementation-packet.md` for Wave 2) before reading the diff — you need the accepted allowed-files/acceptance-criteria list in hand to check against, not to infer from the diff itself.

## 1. Live GitHub verification

- [ ] `checkpoint/core-r2-readonly-uat-2026-07-15` still resolves to `acd8c4691e72cf5590f2a56228b08f183b76cd9a`.
- [ ] `Shopify-connector` and `main` are unchanged.
- [ ] PR #150 and PR #151 are unchanged (unless this wave is specifically Wave 0's PR #150/#151 disposition decision, which requires its own explicit sign-off record, not a routine wave merge).
- [ ] The PR base is `mvp/program-integration` at the expected current SHA (per `mvp-program-state.md`); if `mvp/program-integration` has drifted since the wave branched, confirm the PR was rebased/updated correctly, not silently diverged.
- [ ] The PR's stated commits match what's actually in the diff — no undisclosed commits, no force-push history rewrite.

## 2. Scope review

- [ ] The PR's file list matches the wave's own "owned paths" / allowed-files list in `mvp-completion-program.md` §4 (or the task packet's own allowed-files section). Flag any file outside that list.
- [ ] No file from the wave's "forbidden" list was touched.
- [ ] No other wave's scope was silently absorbed (e.g. Wave 2 PR touching inventory files).
- [ ] No excluded-from-MVP domain was touched (payout reconciliation, advanced refunds, accounting automation, Markets, subscriptions, gift cards, POS, B2B, metafields, advanced analytics, app-store packaging, complex multi-company, broad multi-store orchestration).
- [ ] If the PR proposes a new architecture decision (e.g. DEC-031 Layer 2's exact design for Wave 3), confirm it went through the ADR pipeline (`docs/03-architecture/` proposal → `docs/04-decisions/DEC-0NN-*.md` at "Proposed") rather than being silently implemented as if already accepted.
- [ ] No approach logged in `docs/05-qa/rejected-approaches-log.md` was silently reintroduced without its revisit condition being met and explicitly stated.

## 3. Code review

- [ ] Follows the module-boundary/layering architecture already accepted (DEC-008/013: transport / mapping / orchestration / domain / UI layering; no domain module bypasses `shopify_connector_core`'s job/log/binding substrate).
- [ ] No Shopify mutation is introduced without DEC-031 Layer 2 already being designed, accepted, and implemented for that domain (Wave 3 onward). Read-only handlers (import) may use Layer 1 (`remote_read_replay_safe`) as today's two import job types do.
- [ ] Idempotency/duplicate-prevention approach matches DEC-006 (binding identity) and DEC-009 (classified retry, ambiguous-outcome rule) — no blind retry of a non-idempotent write with an unknown outcome.
- [ ] No secret/credential/token is logged or exposed outside the existing redaction discipline.
- [ ] No new UI wiring to a model that Task SEC-1's hardening hasn't covered yet (relevant from Wave 5 onward).

## 4. Architecture compliance

- [ ] Consistent with every already-Accepted DEC (DEC-003 through DEC-031, plus DEC-032 itself) relevant to this wave's domain. Spot-check the specific DECs named in the wave's own section of `mvp-completion-program.md` §4.
- [ ] Any deviation from an accepted DEC is either out-of-scope-for-this-PR (flag, don't silently accept) or itself routed through a proper amendment (new DEC, control-room accepted).
- [ ] Module/model naming follows the established `shopify_connector_<domain>` / `shopify.connector.<entity>` conventions (`core-naming-schema-planning.md`).

## 5. Tests and runtime evidence

- [ ] The PR's own stated test suite exists and its file names/counts are verifiable in the diff.
- [ ] Runtime evidence is genuine: an actual Odoo.sh build ID, fresh-install result, and focused-class results are cited — not just "tests pass" with no evidence artifact. Cross-check against `docs/05-qa/mvp-acceptance-matrix.md`'s expected evidence column for this item.
- [ ] No claim of test success without an actual runtime execution (this repo has no local Odoo runtime — a claim with no Odoo.sh build citation is not acceptable evidence).
- [ ] Zero-residue / leak-scan evidence is present, matching the pattern established at every prior checkpoint.
- [ ] Issue #157 is the only test-failure class that may be waved through as "known unrelated" — any other failure must be fixed or explicitly escalated, never silently reclassified.
- [ ] For any wave introducing a Shopify mutation (Wave 3 onward): genuine concurrency/replay-safety proof exists (independent-connection races, not a single-threaded simulation), matching the rigor already established for CORE-R2's admission-lease and disconnect-quiescence proofs.

## 6. Security

- [ ] No new RPC/ORM write surface is exposed without a server-side guard (this is exactly the class of gap Task SEC-1 exists to close — confirm this wave doesn't reintroduce it elsewhere).
- [ ] Access-control changes are least-privilege and consistent with the four-role model (Auditor/Operator/Reviewer/Admin).
- [ ] Any new credential/PII-adjacent field follows the existing redaction/access pattern.

## 7. Performance

- [ ] No wave introduces a batch/cadence/lock-duration pattern PERF-1 already identified as under-budget (5-min/batch-20 drain vs. ≥600 jobs/hour target) without addressing it or explicitly deferring with a note.
- [ ] Row-lock scope doesn't extend across a network call (the specific hazard PERF-1's packet documents).

## 8. Documentation

- [ ] `docs/07-implementation-plan/mvp-program-state.md` is updated (active wave, status, branch/PR, evidence, blockers, next gate).
- [ ] `docs/05-qa/mvp-acceptance-matrix.md` rows this wave affects are updated.
- [ ] Any new/changed decision is recorded per the ADR pipeline, not left implicit in a PR description only.
- [ ] A session handoff entry exists per `docs/06-prompts/session-handoff-template.md`'s compact format, including the learning feedback loop section (`docs/05-qa/quality-feedback-loop.md` §6).

## 9. Decision

Classify as exactly one of:

- **Accept** — merges as-is into `mvp/program-integration`.
- **Accept with minor corrections** — small, named fixes applied (by Sol, in a follow-up commit on the same PR) before merge.
- **Revise** — material gaps; Sol reworks before re-review. State exactly what's missing against §1–§8 above.
- **Reject** — wrong/unsafe/unsupported; do not merge. Log the reason; if it's a rejected approach, add it to `docs/05-qa/rejected-approaches-log.md` with a revisit condition.

## 10. Merge authorization

Only record "Accept" (or "Accept with minor corrections" once applied) after every unchecked box above is either checked or explicitly, individually waived with a stated reason. Merge with a normal merge commit into `mvp/program-integration` (no squash/rebase, to preserve the same traceable-history pattern the checkpoint itself was built with). Update `mvp-program-state.md`'s wave-status table immediately after merging.

## 11. Next-wave authorization

State explicitly whether the next wave in sequence (`mvp-completion-program.md` §4) is now unblocked, still blocked (name the blocker), or whether this wave's outcome changes the wave order (e.g. a Wave 0 decision reshapes Wave 5's scope). Do not assume the next wave may start silently — record the authorization (or its absence) in `mvp-program-state.md`.
