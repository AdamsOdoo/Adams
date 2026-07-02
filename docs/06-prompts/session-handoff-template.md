# Session Handoff Template

> Use this to write/refresh `../01-research/research-handoff.md` at the end of
> every session. Continuity lives in GitHub, not chat. Keep the running
> **Sprint checkpoint log** at the bottom of the handoff file (append one note
> per stage/session). Older full handoffs move to a dated archive section (see
> `../05-qa/quality-feedback-loop.md` §11, documentation maintenance rule).

---

## Compact handoff format (default)

**Use this format for most sessions.** It satisfies the mandatory handoff
requirement (`CLAUDE.md` §12) without appending another 100–200-line section.
Every field below is required; write "None" rather than leaving a field blank.
Prepend it to `research-handoff.md` as the new current-state note (do not bury
it under old handoffs) — see §11's "current-state summary + dated changelog"
principle.

```markdown
### <Session / Sprint name> — compact handoff (<date>)

- **Branch / PR:** <branch name>; PR #<n> → <target branch>, <draft/open/merged>.
- **Files changed:** <repo-relative paths, or "None">.
- **What changed / residue fixed:** <one line per substantive change>.
- **Items deferred:** <short list, or "None">.
- **Learning feedback loop:** new issues / repeated patterns / rules updated /
  rejected approaches / technical debt / architecture concerns — one line each,
  or "None" (see `../05-qa/quality-feedback-loop.md` §6).
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (if any) · technical debt
  logged (if any) · repeated-issue escalation applied (if any) — confirm
  all YES, or state what is outstanding.
- **Next recommended session:** <name + why>.
- **Stop condition:** <what boundary this session stopped at; what remains
  unauthorized (code/architecture/merge, as applicable)>.
```

A **deviation to this compact format must be explicitly authorized** (e.g. by
ChatGPT in the session prompt) when a sprint needs it for reasons other than
routine brevity; record that authorization in the compact block's own text.

## Full handoff format (major sprints only)

Use the full format below only for sprints that need the extra sections (e.g.
a first-of-its-kind sprint, a sprint ChatGPT asks to be fully documented, or a
sprint whose Assumptions/Risks/Evidence are unusually load-bearing). Do **not**
default to this for routine sessions — see the documentation maintenance rule
(`../05-qa/quality-feedback-loop.md` §11): archive old full handoffs into a
dated history section rather than requiring every future session to read
through them.

---

# <Session / Sprint name> Handoff

## Session summary

<!-- What this session set out to do and what it produced, in a few lines. -->

## Branch and commits

<!-- Branch name; list commit hashes + messages. -->

## Files created or updated

<!-- Repo-relative paths, grouped. -->

## What changed

<!-- The substantive deltas vs the prior state. -->

## Evidence and citations added

<!-- Sources registered/used with access status (Accessible/Partial/Blocked) + date. -->

## Assumptions

<!-- Anything assumed; label as assumption/inference, not fact. -->

## Open questions

<!-- Unresolved items needing follow-up or external input. -->

## Risks

<!-- What could go wrong; access risks; scope risks. -->

## Learning feedback loop

<!-- Mandatory. See ../05-qa/quality-feedback-loop.md §6. -->

- New issues discovered:
- Repeated issue patterns:
- Rules/checklists updated:
- New rejected approaches:
- New technical debt:
- Architecture concerns:
- Tests or review gates needed:
- Should future prompts change? Yes/No. If yes, how?

## What ChatGPT should review

<!-- The specific things the control room should inspect / decide. -->

## Recommended next session

<!-- Name the next scoped session and why. -->

## Stop confirmation

<!-- Confirm work stopped at the scoped boundary; no code; awaiting review. -->

---

## Quality gate confirmation (must all be YES to mark complete)

- [ ] Session handoff updated (this block).
- [ ] Quality feedback loop checked.
- [ ] New learning captured in the correct file.
- [ ] Any rejected approach logged.
- [ ] Any accepted technical debt logged.
- [ ] Any repeated issue pattern escalated into a rule, checklist, or test.

---

## Sprint checkpoint log

<!-- One short note per stage/session, most recent last. -->

- **<Stage/Session> (<date>):** <what was done; what's next>.
