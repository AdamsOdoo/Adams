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
8. **Correct base branch and PR target** (see `CLAUDE.md` → Branch governance):
   - default project integration branch is `Shopify-connector`
   - never target `main` or plain `dev` unless ChatGPT explicitly approves

## During the session

- Stay within the scoped task; do not silently expand scope.
- Cite every external claim and **classify every claim** (fact / competitor
  claim / inference / recommendation / decision / open question — `CLAUDE.md` §8).
- Do not proceed if required evidence is missing — log it as an open question.
- Do not hide uncertainty; state confidence and surface risks.
- Never bypass authentication walls; record blocked sources.
- **Use high-power research mode when the task needs it** (capability, not a
  cap): large parallel-agent fan-out, broad source collection, verification
  passes, and deep synthesis are allowed and encouraged for major work — they
  must be intentional, scoped to allowed files, and documented (see the
  High-power research mode section below). Keep small patch sessions lightweight.

## High-power research mode

Claude is allowed to use strong research capabilities, parallel agents, broad
source collection, verification passes, and deep synthesis when the task
genuinely requires it. The goal is **not** to minimize tool use — it is to
produce trustworthy, state-of-the-art work. However, large fan-out must be
intentional and reviewable.

Before launching a large parallel-agent workflow, define: **why** high-power
mode is needed; **what** each agent/workstream will investigate; **which**
sources are authoritative; **what files** will be updated; the **stop
condition**; how findings will be **synthesized and verified**; and how
**unsupported claims will be prevented**.

Large fan-out is encouraged for major research sprints, competitor benchmarking,
official API verification, UX/UI benchmark research, architecture tradeoff
research, and quality/security/performance review — but it must stay within the
allowed files and current phase gate. For small patch/revision sessions, do not
launch large fan-out; use the minimum research needed.

If high-power mode is not explicitly authorized in the prompt but appears
necessary, stop and ask ChatGPT for approval or propose a small fan-out plan. If
high-power mode is explicitly authorized, proceed within scope and document the
plan/result in the handoff.

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
