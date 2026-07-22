# Claude MVP Wave Review Template

> Reusable control-room review prompt for the MVP completion program (`DEC-032`). Use this for every macro-wave PR targeting `mvp/program-integration`, before deciding accept/revise/reject and before any merge. Copy the applicable tier and checklist into the wave's review record (a PR review comment, or a dated section in `docs/07-implementation-plan/mvp-program-state.md`) — do not run it silently.
>
> **Product-owner calibration — 2026-07-22.** Review depth is risk-tiered. Mutation safety, concurrency, idempotency, security, credentials and data integrity keep full rigor. Architecture/design receives one normal review and one consolidated correction at most. Wording, cross-references, terminology and documentation structure are light-touch and non-blocking unless they alter a functional contract. This policy changes review ceremony, not the accepted mutation-safety architecture, Odoo.sh runtime requirement, citation discipline or checkpoint protections.
>
> **Builder/reviewer independence — DEC-039/DEC-040 (2026-07-22).** Claude is now a default implementation worker for this program (alongside Sol), and Claude also performs gate reviews by default (ChatGPT is the strategic control room but is no longer required to review every gate). The one rule this depends on: **the session that implemented a PR may never review or accept its own PR.** Satisfy this with either a separate top-level Claude session, or a fresh `Agent`-tool subagent given only the diff, the acceptance criteria, and this file — no memory of the implementer's own reasoning — instructed to adversarially re-verify. Batches should target a full wave, or a large independently-revertable slice of one, per iteration; review depth scales *up* with batch size, never down.

## 0. Classify the review tier before reviewing

State one tier and the reason at the start of every gate review.

| Tier | Applies to | Required depth | Merge impact |
| --- | --- | --- | --- |
| **Tier 1 — full rigor, blocking** | Shopify/Odoo mutation logic; Layer 1/2 replay safety; concurrency/CAS/locks; idempotency and duplicate prevention; security, credentials, permissions, PII/redaction; irreversible migrations; data integrity; production runtime failures; performance defects that can corrupt, block or destabilize operations | Exact identity gate; full accepted-contract and code review; adversarial review; source/official-evidence verification where behavior may have changed; genuine Odoo.sh runtime evidence; concurrency/crash/recovery proof where applicable; security/lifecycle/residue checks | Any unresolved P0/P1 blocks acceptance and merge |
| **Tier 2 — normal review, single round expected** | Architecture/design decisions; new domain contracts; module boundaries; job and state taxonomies; API-shape choices that do not yet execute a mutation; test plans; UI information architecture; performance benchmark design | Exact base/scope verification; focused architecture and contract review; evidence/citations for factual claims; implementation/testability check; one consolidated correction pass if required | Material contract gaps block; routine correction count is capped at one |
| **Tier 3 — light-touch, non-blocking** | Wording; cross-references; headings; terminology consistency; documentation structure; stale status text; formatting; PR-body/handoff polish | Verify the change does not alter a functional contract, authority, scope, acceptance criterion or evidence claim; fix in the same pass or roll into the next already-authorized batch | Must not independently block merge or trigger a full identity/runtime cycle |

### Tier-escalation rule

A Tier 3-looking item becomes Tier 2 or Tier 1 only when the wording changes or obscures a real contract: for example, confusing job state with mutation outcome, changing retry authority, misstating an API field, weakening a permission rule, or making a test/evidence claim false.

### Mixed changes

Use the highest applicable tier for the risky portion, but do not apply Tier 1 ceremony to unrelated Tier 3 edits. Record findings by tier so documentation polish cannot hold a safe implementation hostage.

## 1. Correction-cycle cap and synthesis rule

1. The first review must be comprehensive: inspect the full relevant diff, accepted decisions, actual merged seams, tests, lifecycle/security constraints, performance implications and source-of-truth documents before issuing corrections.
2. Report **all known P0, P1 and material P2 findings together** in one consolidated ruling.
3. Permit **one consolidated correction iteration maximum** for Tier 1 or Tier 2 findings discovered by that review.
4. The final review is verification-only against the agreed finding set and required regressions. Normal outcomes are `Accept` or `Reject / Reset` for a genuinely new P0, architectural impossibility or unsafe-to-test condition — not another routine P1/P2 delta cycle.
5. Tier 3 corrections are applied in the current pass or rolled into the next already-authorized documentation/implementation batch. They do not create an independent review round.
6. A third same-day revision round for the same wave/task is an **upstream-quality signal**, not routine workflow. Stop incremental patching, log the churn pattern under `docs/05-qa/quality-feedback-loop.md`, and run one synthesis/reset pass that repairs the prompt, packet or Definition of Ready before proceeding.
7. Late non-P0 findings are never ignored: record them as explicit implementation acceptance criteria, tests or tracked debt with an owner and gate. Reopen a frozen gate only for a newly demonstrated P0, security/data-integrity risk, architectural impossibility, or a contract that cannot be implemented/tested safely.

## 2. Before you start

- Confirm you are reviewing a PR targeting `mvp/program-integration` (never `Shopify-connector` or `main` — those promotions are separate, later, product-owner-approved acts).
- Read the wave definition in `docs/07-implementation-plan/mvp-completion-program.md` and the relevant task packet(s) before reading the diff.
- Read the most recent wave-boundary calibration entry in `mvp-program-state.md`.
- Declare the tier, the reason, and whether this is the initial review, the single correction verification, or a synthesis/reset triggered by churn.

## 3. Live GitHub verification

Apply the full list for Tier 1. For Tier 2, verify the exact base, PR identity, protected refs relevant to the change and changed-file scope. For Tier 3, verify the PR/file identity and that no protected or functional file changed.

- [ ] `checkpoint/core-r2-readonly-uat-2026-07-15` still resolves to `acd8c4691e72cf5590f2a56228b08f183b76cd9a` when the review can affect a release or implementation gate.
- [ ] `Shopify-connector` and `main` are unchanged when applicable.
- [ ] PR #150 and PR #151 are unchanged unless the task explicitly owns their disposition.
- [ ] The PR base is `mvp/program-integration` at the expected SHA; drift is explicitly resolved.
- [ ] The stated commits and changed files match the live diff; no undisclosed commits or history rewrite.

## 4. Scope review

- [ ] The PR file list matches the wave/task allowed-file list.
- [ ] No forbidden path was touched.
- [ ] No other wave or excluded MVP domain was silently absorbed.
- [ ] New architecture decisions follow the ADR pipeline rather than being silently implemented.
- [ ] No rejected approach was reintroduced without its revisit condition.
- [ ] Tier 3 documentation edits are separated from functional scope and do not become merge blockers by themselves.

## 5. Code and architecture review

Mandatory for Tier 1; focused to the changed contract for Tier 2; normally not applicable to Tier 3.

- [ ] Module boundaries and transport/mapping/orchestration/domain/UI layering remain intact.
- [ ] No Shopify mutation bypasses accepted Layer 2 ownership/reconciliation.
- [ ] Idempotency and duplicate prevention match accepted binding/job/mutation contracts; no blind retry after unknown outcome.
- [ ] No secret, credential, token or PII leakage is introduced.
- [ ] No server-side write/action surface bypasses accepted permission guards.
- [ ] Accepted DECs are preserved or formally amended.
- [ ] Naming follows established addon/model conventions where naming has runtime or extension impact.

## 6. Tests and runtime evidence

- [ ] The stated test files/counts exist and cover the accepted contract.
- [ ] Evidence labels distinguish `EXECUTED—PASS`, `STATICALLY VERIFIED`, `IMPLEMENTED—RUNTIME PENDING` and `NOT PROVEN`.
- [ ] Tier 1 implementation acceptance includes genuine Odoo.sh build identity, fresh install, focused suites, required regressions, security/lifecycle/residue checks and relevant concurrency/recovery evidence.
- [ ] No success claim exists without actual execution evidence.
- [ ] Mutation-domain concurrency uses independent transactions/processes where required, not a sequential simulation presented as concurrency.
- [ ] Runtime failures are collected into one root-cause set and fixed in one consolidated batch before the targeted rerun plus regressions.

## 7. Security, lifecycle and data integrity

Mandatory for Tier 1 and any Tier 2 design that creates these obligations.

- [ ] Least privilege and server-side guards are preserved.
- [ ] Credential/PII-adjacent fields follow existing redaction/access patterns.
- [ ] `selection_add` and uninstall/reinstall behavior are explicit where new vocabulary is introduced.
- [ ] No orphan rows, active-domain residue or unsafe historic reinterpretation remains.
- [ ] Company/store identity constraints and protected fields are enforced server-side.

## 8. Performance and UX pull-forward

- [ ] Every backend wave identifies the operator surface it enables and the earliest UI slice that can validate it.
- [ ] Every mutation or queue-heavy wave records the benchmark scenario, workload, throughput/latency target and measurement evidence available at that gate.
- [ ] Row locks do not span network calls.
- [ ] Batch/cadence/scan designs are compared with the current PERF-1 target rather than deferred automatically to Wave 5/6.
- [ ] UI reviews check merchant task completion, error recovery, clarity, accessibility, responsiveness and perceived performance — not visual polish alone.

## 9. Documentation and source of truth

- [ ] `mvp-program-state.md` reflects the live state, tier used, correction count, blockers and next gate.
- [ ] `mvp-acceptance-matrix.md` is updated where evidence/status changed.
- [ ] New/changed decisions are recorded through the ADR pipeline.
- [ ] The handoff is compact and includes the learning feedback loop.
- [ ] Tier 3 issues are fixed in-pass or listed for the next authorized batch, without triggering a separate full gate.

## 10. Decision

Classify as exactly one of:

- **Accept** — meets the applicable tier and may proceed.
- **Accept with in-pass Tier 3 corrections** — non-functional polish is corrected without a new gate cycle.
- **Revise — single consolidated correction** — material Tier 1/Tier 2 gaps; list the complete finding set and acceptance proof required.
- **Reject / synthesis reset** — unsafe, unsupported, architecturally infeasible, or a third same-day revision indicates the upstream prompt/packet/DoR must be rebuilt instead of patched again.

Do not issue a second routine correction ruling after the consolidated correction. A newly demonstrated P0 or impossibility must be reported explicitly as new evidence, not disguised as another ordinary delta review.

## 11. Merge authorization

Record `Accept` only after all Tier 1/Tier 2 blockers are closed and required evidence is genuine. Tier 3 polish does not independently block merge. Merge with a normal merge commit into `mvp/program-integration` unless a separate accepted governance record says otherwise. Update `mvp-program-state.md` immediately after merge.

## 12. Wave-boundary calibration — mandatory

At every wave boundary, record:

1. tier used and why;
2. number of review rounds and correction rounds;
3. substantive vs Tier 3 findings;
4. whether the cycle cap was respected;
5. actual elapsed time vs forecast;
6. next-wave timeline and critical dependencies;
7. UI slice and performance benchmark status;
8. one process adjustment, or `none` with evidence that the process is on target.

## 13. Next-wave authorization

State whether the next wave is unblocked, blocked with a named reason, or deliberately parallelized. Do not assume strict sequencing when a read-only UI slice or benchmark harness can safely proceed in parallel, but never parallelize work that would bypass an accepted mutation, security, runtime or data-integrity gate.
