# DEC-040: MVP Program Cadence — Claude as Default Builder + Independent Reviewer, ChatGPT as Strategic Control Room, Large-Batch Waves, UI Priority

> **Superseded in default-role and tier-selection mechanics — 2026-07-25.** Preserved for history. Risk tiers, independent review, consolidated corrections, coherent batching, and runtime rigor remain. [The role-model addendum](2026-07-25-mvp-role-model-addendum.md) assigns canonical roles; [DEC-041](DEC-041-evidence-first-process-reallocation.md) makes tier selection deterministic from diff paths and semantics.

- **Status:** Accepted — see Status note below for the procedural basis.
- **Date:** 2026-07-22
- **Deciders:** Product owner (direct, explicit written instruction, this session).
- **Phase:** Program governance / operating cadence (not a technical architecture decision; does not itself authorize any specific implementation task or relax any architecture/security/runtime-evidence requirement).
- **Related:** `DEC-032-mvp-autonomous-execution-model.md`, `DEC-039-mvp-claude-implementation-worker-expansion.md` (both amended by this decision), `CLAUDE.md` §13, `docs/06-prompts/claude-mvp-wave-review-template.md`, `docs/07-implementation-plan/mvp-completion-program.md`, `docs/07-implementation-plan/mvp-program-state.md`.

## Status note (procedural basis for Accepted status)

Same basis as DEC-032 and DEC-039: a direct, explicit product-owner instruction in this session, following the precedent DEC-032 itself established (product owner has standing authority to reassign roles between the AI collaborators they employ; `CLAUDE.md` §2's role table is a product-owner-authored delegation, not a constitutional constraint on the product owner). Accepted directly, without a separate ChatGPT review pass, because the instruction is unambiguous and specifies how it coexists with DEC-032/DEC-039 (see Scope, below).

## Context

DEC-039 (same day) authorized Claude as an implementation worker alongside Sol, with a safeguard: an implementing Claude session may never self-review or self-accept its own work. The product owner has now given four further, related instructions on how this should run day to day:

1. Claude should also be the one performing gate reviews (not rely on ChatGPT to review every wave), while ChatGPT continues as the project's control room.
2. Work should proceed in **large batches** — each iteration should cover a significant part of a wave, or a full wave, rather than the many small correction cycles that slowed Waves 3 and 4 (see the 2026-07-22 course-correction prompt, `docs/06-prompts/control-room-calibration-course-correction-2026-07-22.md`, and ChatGPT's response merged in PR #190).
3. The UI (Wave 5 / U0) should get significant, prioritized focus, not remain at zero code.
4. None of the above may come at the cost of correctness — explicit safeguards are needed so that larger, faster batches don't "blow up the whole development with errors or mistakes or bugs."

## Decision

1. **Default roles for MVP-program work, going forward:**
   - **Claude** is the default implementation worker *and* the default gate reviewer. **GPT-5.6 Sol remains an available secondary implementation worker** (DEC-039 added Claude alongside Sol, not instead of it) but is no longer assumed to be the default.
   - **ChatGPT is the strategic control room**: sets/approves scope, priority sequencing, and timeline; resolves hard-stop conditions requiring a commercial/product judgment call; is the escalation point if the independent-review mechanism (below) and the product owner disagree. ChatGPT is **not** required to perform a line-by-line review of every wave gate going forward — that operational load moves to Claude, under the mechanism below.
   - **The product owner** remains final authority on promotion (`mvp/program-integration` → `Shopify-connector`/`main`) and on any scope change, exactly as under DEC-032.

2. **Independent-review mechanism (this is how "Claude builds and reviews" stays safe).** Independent Claude review is the **default routine gate** for every wave/batch; ChatGPT review is an available strategic spot-check or escalation path, not a prerequisite for a routine gate. DEC-039's no-self-acceptance rule is unchanged and is satisfied by either:
   - a distinct top-level Claude Code session (a different conversation) reviewing the PR from scratch; or
   - within one session, a **fresh subagent invocation** (via the `Agent` tool) explicitly instructed to adversarially re-verify, not summarize or rubber-stamp.

   **Memoryless, not repository-blind.** The reviewer's initial briefing excludes the implementing session's reasoning, its defenses of its own design choices, and any selective summary intended to influence the verdict. It is not deprived of evidence: it independently reads the exact base/head repository checkout, the complete PR diff, the governing DECs and implementation packets, the acceptance criteria, the actual Odoo 19 source, automated-test output, genuine Odoo.sh runtime evidence for code batches, screenshots/browser evidence where relevant, and current official sources when a version-dependent fact needs verification. A diff-only review does not satisfy this for Tier 1 work.

   **Durable and non-suppressible review.** The complete independent-review report is posted verbatim to the PR, stating the exact reviewed SHA. The implementing session may not rewrite, selectively summarize, suppress, override, accept, ready-mark, or merge that report. A `REVISE` verdict is resolved through one consolidated correction (per the review template's cycle-cap rule). After an `ACCEPT`, a **separate top-level closure session**, or another explicitly authorized independent actor — never the implementing session — verifies the exact accepted SHA, confirms the required evidence still corresponds to that SHA, and performs the ready-marking/merge. Reviewer silence, a partial report, or a summary-only report is never acceptance.

   The implementing thread may never mark its own PR ready, accept it, or merge it on its own say-so, regardless of which mechanism is used.

3. **Batch size: target a full wave, or a large, coherent, independently-revertable vertical slice of one, per iteration.** Do not split routine work into many small correction cycles. Tier 3 (wording/polish) issues found mid-batch are fixed inline before submission — never spun into their own review cycle. This extends, not replaces, the Tier 1/2/3 depth model and the same-day cycle-cap rule already added by DEC-032's calibration (PR #190, `claude-mvp-wave-review-template.md`).

4. **UI priority.** Wave 5 (operator UI), and the U0 slice specifically, is a priority parallel track. UI iterations should also target large, usable slices per pass (e.g. a full navigable read-only operator surface in one iteration) rather than piecemeal screens, consistent with the U0/PERF-0 parallelization already approved in PR #190.

5. **Non-negotiable safeguards for large-batch delivery — the explicit answer to "don't blow up development":**
   - **Every implementation/code batch** ships with full automated test coverage for what it adds/changes, **plus genuine Odoo.sh runtime evidence** (build ID, fresh-install result, focused-class results — never a static-only claim, and proportional to the batch's risk and size), before the independent review even begins, regardless of how small the batch is. **Documentation/governance-only batches** do not require an irrelevant Odoo.sh runtime campaign — they are verified by repository/diff/path/link/consistency checks appropriate to the change, must never fabricate runtime evidence, and must never weaken this runtime requirement for a later code batch.
   - The independent review's scrutiny **scales up, not down, with batch size** — a bigger diff gets a more deliberate adversarial pass, never a lighter skim because "it's one big PR already."
   - Each batch lands as **one atomic, cleanly revertable unit.** If a batch can't be made atomically revertable, split it until it can be — this bounds the blast radius of any single bad batch regardless of how much scope it covers.
   - UI batches specifically must include a real, driven walkthrough (the app actually run and clicked through, not just code review) before being called done — UI defects are the ones a merchant sees first.
   - All previously-accepted mutation-safety architecture (Layer 1/2 replay-safety, CAS concurrency, the fixed error taxonomy), checkpoint/branch protections, and citation/claim-classification discipline (`CLAUDE.md` §7–§8) remain fully in force, unchanged by batch size or cadence. Speed comes from batching *scope*, never from skipping *evidence*.

6. **Scope**: identical to DEC-032/DEC-039 — applies only to work on or descending from `mvp/program-integration`. Does not change `Shopify-connector`/`main` branch governance.

## Consequences

- **Positive:** fewer, larger, more self-contained iterations should cut the per-gate ceremony overhead that slowed Waves 3–4 (documented in the 2026-07-22 course-correction prompt), and the UI — currently at zero code after three weeks — gets dedicated forward motion instead of remaining last in sequence.
- **Negative / trade-offs:** larger batches raise the cost of a bad batch — a defect is harder to localize inside a big diff, and the model's entire safety now rests on the independent-review mechanism actually being rigorous every single time, with genuine runtime evidence, never skipped or abbreviated "because the batch is big and review would take too long." If that discipline ever slips, this is the mechanism most likely to fail first, and it should be the first thing checked if a defect does get through.
- **Follow-ups:** `CLAUDE.md` §13 and `docs/06-prompts/claude-mvp-wave-review-template.md` updated alongside this decision to reflect the cadence and the independent-review mechanism.

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Keep ChatGPT as the required reviewer for every wave gate | Rejected by explicit product-owner instruction — the goal is to remove operational bottlenecks, and ChatGPT's role is repositioned to strategic control room rather than line-review labor. | Not added to `rejected-approaches-log.md` — a program-management choice, reversible by a future product-owner instruction. |
| Keep the existing small-increment cadence, only add the UI track | Rejected — the product owner explicitly asked for larger batches across the board, not just for UI, citing the Wave 3/4 correction-cycle overhead as the thing to fix. | N/A. |
| Allow larger batches without scaling review rigor, to move faster | Rejected — this is exactly the "blow up development with errors" failure mode the product owner asked to be guarded against; Decision item 5 exists specifically to reject this alternative. | N/A (explicitly excluded by Decision item 5). |

## Evidence / references

- This session's conversation (2026-07-22) — the product owner's direct instruction. Not an external citation; recorded verbatim in intent here.
- `DEC-032-mvp-autonomous-execution-model.md`, `DEC-039-mvp-claude-implementation-worker-expansion.md` — the decisions this amends; accessed in-repo, 2026-07-22.
- `docs/06-prompts/control-room-calibration-course-correction-2026-07-22.md` and PR #190 — the prior course-correction this decision follows on from; accessed in-repo, 2026-07-22.
