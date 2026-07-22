# Control-Room Calibration — Course Correction Prompt (2026-07-22)

## Purpose

On 2026-07-22 the product owner asked Claude for a read-only review (no code,
no doc edits) of whether the MVP completion program's review posture had
become disproportionate after ~3 weeks of work, given Wave 3 (inventory)
still unmerged and Wave 5 (UI) at zero code. Claude's review, grounded in the
repo's own history (git log, `docs/04-decisions`, `docs/07-implementation-plan/mvp-program-state.md`,
`docs/05-qa/defect-pattern-log.md`), found: the mutation-safety rigor is real
and has caught genuine runtime-only defects, but a large share of the
same-day gate revision cycles (e.g. Wave 3 Gate B's 3 same-day revisions,
Wave 4 Gate A's 2 same-day correction cycles) were wording/cross-reference
corrections carrying the same ceremony as substantive findings — and three
weeks in, the most user-visible piece (the operator UI) has not been started.

The prompt below is the product owner's resulting course-correction
instruction, sent directly to ChatGPT (the project's strategic control room
per DEC-032 / CLAUDE.md §13) on 2026-07-22. It is forward-looking only — it
does not reopen any accepted decision, does not touch the checkpoint, and
does not change merge/branch protections. It asks ChatGPT to self-audit its
own review record, adopt risk-tiered review depth, cap correction-cycle
churn, pull UI/performance validation forward, and update the governing
files (`mvp-completion-program.md`, `mvp-program-state.md`, the wave-review
template) accordingly. Recorded here per CLAUDE.md §3 ("if it is not in
GitHub, it does not exist for this project") so the instruction and its
rationale survive as a durable reference, independent of the ChatGPT chat
transcript it was pasted into.

**Status:** sent to ChatGPT 2026-07-22; response/follow-through not yet
recorded. Update `mvp-program-state.md` once ChatGPT's self-audit and any
resulting file changes land.

## The prompt as sent

```text
Subject: Control-room calibration — course correction for the MVP completion program, effective going forward

This is a direct product-owner instruction under DEC-032's authority. It does not reopen any accepted decision, does not touch the checkpoint, and does not ask you to relitigate past waves. It's about how you run the control room from this point forward.

Context. Three weeks into this program: Wave 0/1 are merged, orders are largely done, but inventory (Wave 3) took 3 same-day design revisions plus ~15 correction commits and still isn't merged, fulfillment (Wave 4) hasn't started implementation and is already on its 2nd same-day correction cycle at the "definition of ready" stage, and the UI (Wave 5) — the part a merchant actually sees — has zero code. Meanwhile the repo holds 200+ governance/planning documents. Some of the review rigor has caught real, load-bearing defects (runtime-only production bugs in Task 013 that static review missed, stale API facts that would've shipped as truth) — that part is working and stays. But a large share of the same-day revision cycles have been wording, cross-reference, and terminology corrections on documents, not functional or safety findings, and each one has cost a full identity-gate-plus-round-trip cycle. That ratio is slowing the program without making the connector any more airtight.

What I need from you, going forward:

1. Self-audit your own control-room record, honestly. Look at the Wave 3 and Wave 4 gate cycles specifically. For each revision/correction round you required, classify it: was it a functional, safety, data-integrity, or performance finding — or was it wording/structure/cross-reference polish? Report the actual ratio. Don't soften it and don't over-correct into blanket self-criticism either — I want an accurate read, the same way I asked Claude for one.

2. Adopt risk-tiered review depth, and write it down. Not every change deserves maximum ceremony. Define (and add to docs/06-prompts/claude-mvp-wave-review-template.md or wherever it governs) three tiers:
   - Tier 1 (full rigor, blocking): anything touching Shopify/Odoo mutation logic, concurrency, idempotency, security, credentials, or data integrity. Keep the identity gate, adversarial review, and runtime-evidence requirements exactly as they are.
   - Tier 2 (normal review, single round expected): architecture/design decisions, new domain contracts.
   - Tier 3 (light-touch, non-blocking): wording, cross-references, terminology consistency, documentation structure. These should not gate a merge or trigger a full re-verification cycle — fix in the same pass or roll into the next one.

3. Cap correction cycles and make the 3rd one a signal, not a routine. This project already has a rule that a 3rd occurrence of the same defect category triggers escalation (docs/05-qa/quality-feedback-loop.md). Apply the equivalent to gate churn: if a wave/task needs a 3rd same-day revision round, that's not "one more delta review" — it's a signal something upstream (the prompt, the packet, the definition-of-ready) was under-specified, and the fix is a reset/synthesis pass, not another incremental patch.

4. Pull UI and performance validation forward now, in parallel — don't leave them sequenced last. Wave 5 (operator UI) and PERF-1 (throughput/performance) are currently dead last in the wave order, after every backend domain is frozen. If "premium, state-of-the-art functionality, performance, and UX/UI" is the actual bar — and it is — we need to find out early whether the UI and performance characteristics hold up, not after the architecture is already locked in. Propose a concrete way to slice a first UI pass and an early performance benchmark into the next 1-2 waves rather than waiting for Wave 5/6.

5. Produce a realistic forward timeline, not an aspirational one. Based on actual per-wave velocity so far (not best-case), give me a real estimate for finishing Wave 3, then Wave 4, 5, 6. If that estimate doesn't fit a reasonable ship target, tell me now which levers you'd pull first (review depth on Tier 3 items, parallelization, scope trimming) — don't let me find out three weeks from now.

6. Update the actual governing files, not just tell me this in chat: docs/07-implementation-plan/mvp-completion-program.md (wave sequencing), docs/07-implementation-plan/mvp-program-state.md (current status), and the wave-review template with the tiered-review rule and the cycle-cap rule. If it's not in GitHub, per our own CLAUDE.md rule, it doesn't exist — that applies to this course correction too.

7. Commit to revisiting this calibration at every wave boundary going forward, not just when I ask. At each gate, briefly state which tier applied and why, so drift back into uniform maximum-rigor is visible immediately rather than three weeks later.

What does not change: mutation-safety architecture (Layer 1/2 replay-safety, CAS concurrency, the error taxonomy), runtime validation on Odoo.sh before any domain is accepted, citation/evidence discipline for facts, and the checkpoint/branch protections in DEC-032. None of that is what's slowing us down, and none of it should be relaxed.

Report back with the self-audit, the tiered-review policy, the updated files, and the realistic timeline. I want you actually driving this as the control room — including catching and correcting your own process drift — not just gatekeeping every PR at the same intensity regardless of risk.
```
