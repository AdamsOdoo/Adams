# Claude Learning Rules

> **Read this file before every future session** (research, architecture, or —
> when authorised — implementation). It encodes the habits that keep the
> project from repeating mistakes. Works together with `CLAUDE.md` and the
> [Quality Feedback Loop](../05-qa/quality-feedback-loop.md).

## Mandatory pre-session checklist (check ALL before doing anything)

Before starting any session, Claude must check:

1. **Previous handoff** — `../01-research/research-handoff.md` (latest handoff +
   the Sprint checkpoint log). Continue the chain; do not restart it.
2. **Defect-pattern log** — `../05-qa/defect-pattern-log.md`. Do not reintroduce
   a logged defect; honour any escalation/pause in effect.
3. **Rejected-approaches log** — `../05-qa/rejected-approaches-log.md`. Do not
   re-propose a rejected approach unless its revisit condition is met (say so).
4. **Architecture-review log** — `../05-qa/architecture-review-log.md`. Do not
   contradict or re-litigate prior review outcomes without cause.
5. **Relevant decision records** — `../04-decisions/`. Respect accepted ADRs.
6. **Current phase** — confirm whether the no-code gate still applies
   (`CLAUDE.md` §5); do not assume implementation is authorised.
7. **Allowed and forbidden files** — confirm exactly what this session may
   create/modify and what it must not touch (`CLAUDE.md` §11 + the sprint's
   allowed-files list).

## During the session

- Stay within the scoped task; do not silently expand scope.
- Cite every external claim and **classify every claim** (fact / competitor
  claim / inference / recommendation / decision / open question — `CLAUDE.md` §8).
- Do not proceed if required evidence is missing — log it as an open question.
- Do not hide uncertainty; state confidence and surface risks.
- Never bypass authentication walls; record blocked sources.

## End of session (post-flight)

- Run the end-of-session learning review (quality-feedback-loop.md §6) and
  update any relevant `/docs/05-qa` logs.
- Update the handoff via `session-handoff-template.md`, including the Learning
  feedback loop section, and add a **"What changed in our rules?"** note if a
  new lesson emerged (and update the rule/checklist that enforces it).
- Confirm the quality gate (§7). Provide the exact next-session prompt.
- **Stop when the scoped task is complete.** Await ChatGPT review.

## Hard rules (non-negotiable)

- No coding until ChatGPT approves the implementation transition.
- Do not repeat rejected approaches unless the revisit condition is met.
- GitHub is the source of truth — deliverables are committed files, not chat.
