# DEC-039: MVP Program Role Expansion — Claude Added as Implementation Worker (alongside GPT-5.6 Sol)

> **Superseded in default-role assignment — 2026-07-25.** Preserved for history. No-self-acceptance remains; [the role-model addendum](2026-07-25-mvp-role-model-addendum.md) and [DEC-041](DEC-041-evidence-first-process-reallocation.md) replace Claude-as-standing/default-builder wording.

- **Status:** Accepted — see Status note below for the procedural basis.
- **Date:** 2026-07-22
- **Deciders:** Product owner (direct, explicit written instruction, this session — via `AskUserQuestion`, selecting "Explicitly change Claude's role now"). No separate ChatGPT review was performed before acceptance; see Status note.
- **Phase:** Program governance / operating model (not a technical architecture decision; does not itself authorize any specific implementation task).
- **Related:** `DEC-032-mvp-autonomous-execution-model.md` (the decision this amends), `CLAUDE.md` §13, `docs/07-implementation-plan/mvp-completion-program.md`, `docs/07-implementation-plan/mvp-program-state.md`, `docs/06-prompts/claude-mvp-wave-review-template.md`, `docs/06-prompts/gpt56-sol-master-mvp-mission.md`.

## Status note (procedural basis for Accepted status)

This follows the same procedural basis DEC-032 itself established and explicitly reserved: DEC-032 states "No feature coding by Claude under this addendum, **unless the product owner explicitly changes Claude's role again**" (`CLAUDE.md` §13). The product owner has now done exactly that, directly and explicitly, in this session: informed that ChatGPT (control room) sometimes authors implementation prompts intended to be relayed to a Claude session for execution, the product owner was asked to confirm whether that constitutes an intentional role change, and confirmed it does ("Explicitly change Claude's role now... Claude becomes an implementation worker for this work going forward, alongside or instead of Sol"). Per DEC-032's own precedent, this is accepted directly by product-owner instruction, without a separate ChatGPT review pass, because DEC-032 itself named this exact product-owner act as the one thing that could reopen the "no feature coding by Claude" rule.

## Context

DEC-032 (2026-07-15) established GPT-5.6 Sol as the MVP program's implementation worker and Claude as the independent control room — scope governor and release gatekeeper — explicitly barring Claude from writing connector feature code in that role. In practice, the product owner relays ChatGPT-authored task prompts between the control room and whichever worker executes them, and has indicated some upcoming implementation prompts are intended for a Claude session, not Sol. Rather than let that happen as a silent deviation from the written model, this was raised explicitly and the product owner confirmed the intended change.

## Decision

1. **Claude is now an additional authorized implementation worker for the MVP completion program, alongside GPT-5.6 Sol.** The product owner may relay a ChatGPT-authored implementation prompt to either worker. This does not retract Sol's role or authority — both are now valid execution channels.
2. **No self-review, no self-acceptance, ever — this is the binding safeguard this decision adds.** Claude may not act as both implementer and control-room gatekeeper for the same piece of work. When a Claude session implements a task/wave:
   - it produces a draft PR exactly as Sol's workflow already requires (never self-marks ready, never self-merges, never self-accepts);
   - **independent Claude review is the default routine gate** for that PR — a **separate** Claude session explicitly operating in the control-room role, or a fresh subagent invocation per DEC-040's mechanism, which must independently re-verify the work rather than defer to the implementing session's own claims. **ChatGPT review is an available strategic spot-check or escalation path, not a prerequisite for a routine gate;**
   - the implementing session and the accepting/reviewing session must never be the same session or thread.
   This mirrors, and does not weaken, the no-self-acceptance principle already enforced throughout this program's history for Sol's work (see the repeated "Claude did not accept its own package, in any revision" language across the Wave 3/4 gate records in `mvp-program-state.md`).

   **Correction (PR #191, 2026-07-22, per binding review comment `5043912321` item 1):** this item originally read "the control-room gate review for that PR must be performed by ChatGPT directly, or — only if no ChatGPT review is available for a given step — by a **separate** Claude session..." — implying ChatGPT was the default and a separate Claude session only a fallback. That conflicted with **DEC-040** (issued the same day), which makes independent Claude review the default routine gate and repositions ChatGPT as strategic control room. The bullet above is corrected to match DEC-040; this note preserves the correction's provenance rather than silently rewriting history.
3. **All other DEC-032 controls apply unchanged and in full to Claude-authored implementation work**, exactly as they already apply to Sol's: checkpoint protection, the ten hard-stop conditions, citation/claim-classification discipline (`CLAUDE.md` §7–§8), the risk-tiered review calibration and cycle-cap rules added by DEC-032's own follow-on calibration (PR #190, `claude-mvp-wave-review-template.md`), and merge authority into `mvp/program-integration` remaining outside the implementing session's own hands.
4. **Scope is identical to DEC-032's**: this applies only to work on or descending from `mvp/program-integration`. It does not change anything about `Shopify-connector` or `main` branch governance.

## Scope of this decision

This decision changes the operating model **only** for who may serve as implementation worker inside the MVP program, and only by addition (Claude alongside Sol), not by removing Sol. It does not:

- Reopen or reassign any already-Accepted DEC (DEC-003 through DEC-038) — those remain binding technical/architecture decisions this program must still honor.
- Change branch protection or promotion rules for the checkpoint, `Shopify-connector`, or `main`.
- Grant Claude (in an implementing session) any acceptance, merge, or self-review authority — DEC-032's control-room/merge-gate model stays intact; this decision's whole purpose is to keep that gate meaningful once Claude can also be the one producing the work it gates.
- Authorize Sol to skip citation/claim-classification discipline, or change any hard-stop condition.

## Consequences

- **Positive:** removes the bottleneck of needing a separate Sol-only channel for every implementation task; lets the product owner route a ChatGPT-authored prompt to whichever worker is available or best suited, without waiting on a role-model gap to be resolved ad hoc each time.
- **Negative / trade-offs:** introduces a real conflict-of-interest risk — Claude implementing and Claude gatekeeping are now performed by the same kind of agent, sometimes literally the same product. That risk is only controlled by strict session/thread separation and an explicit non-self-acceptance rule (Decision item 2); if that separation is ever blurred in practice, the safeguard this decision depends on is gone. Future sessions and the product owner should treat any case of a single session both implementing and accepting its own MVP-program work as a process violation to catch, not a convenience to allow.
- **Follow-ups:** `CLAUDE.md` §13 updated alongside this decision to reflect the expanded role and the no-self-acceptance safeguard.

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Keep Claude control-room-only; route all implementation prompts to Sol | Rejected by the product owner's explicit instruction — the practical workflow already has ChatGPT sending some implementation prompts through the product owner to Claude sessions, and leaving that undocumented would be a silent deviation from DEC-032. | Not added to `rejected-approaches-log.md` — this is a program-management choice, not a technical architecture alternative, and remains available to revert to. |
| Let a Claude implementation session also self-review and self-accept its own work, for speed | Rejected — would break the no-self-acceptance principle this project has consistently maintained for Sol's work throughout Waves 1–4, and would make the control-room gate meaningless for Claude-implemented work. | N/A (explicitly excluded by Decision item 2 above). |

## Evidence / references

- This session's conversation (2026-07-22) — the product owner's direct instruction, given via `AskUserQuestion` in response to Claude flagging the §13 conflict before proceeding with an expected implementation prompt. Not an external citation; recorded verbatim in intent here.
- `DEC-032-mvp-autonomous-execution-model.md` — the decision this amends; accessed in-repo, 2026-07-22.
- `CLAUDE.md` §13 — the addendum this decision updates; accessed in-repo, 2026-07-22.
