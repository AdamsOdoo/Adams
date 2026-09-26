# Implementation Task Template

> **GATED.** Do not use this template until ChatGPT explicitly approves the
> transition to implementation (see `CLAUDE.md` §5, §9). It is provided now so
> the governance chain is complete — not to invite coding.

## Acceptance preconditions (all must be true before starting)

- [ ] ChatGPT has authorised implementation of **this specific task**.
- [ ] Research is sufficient (`../01-research/`) and relevant ADR(s) exist
      (`../04-decisions/`).
- [ ] Architecture for this task is reviewed/accepted
      (`../05-qa/architecture-review-log.md`).
- [ ] The feedback-loop files were checked and are current.
- [ ] No issue type sits at its 3rd-occurrence pause without a prevention
      rule/test/gate in place.

## Required fields for every implementation task

Each implementation task **must** specify all of the following (per CLAUDE.md §9):

### 1. Objective
One scoped outcome. No scope creep.

### 2. Allowed files
The exact files/paths this task may create or modify. Keep connector work
isolated from `adams_base`/customer code and within the approved modular
connector addon-family boundaries defined by architecture/ADRs. Do not bias
implementation toward one giant connector module.

### 3. Forbidden files
What must not be touched. Restate the no-code-elsewhere rule.

### 4. Acceptance criteria
Observable, testable conditions that define success (functional + non-functional:
idempotency, error handling, retry/recovery, rate-limit behaviour, security,
performance).

### 5. Tests
The unit/integration tests that must exist and pass — including edge cases and
any previously logged defects (`../05-qa/defect-pattern-log.md`). State how
duplicate-prevention and partial-failure recovery are tested.

### 6. Rollback notes
How to safely revert (migration reversibility, feature flag, data cleanup,
order of rollback).

### 7. Definition of done
- Code + tests written; tests pass; lint/format clean.
- `../05-qa/pr-review-checklist.md` section C satisfied.
- Any shortcut logged in `../05-qa/technical-debt-register.md`.
- Modularity preserved; only allowed files changed.
- Self-review classified (accepted / minor / revise / reject); handoff updated;
  quality gate confirmed.

## Paste-ready prompt skeleton

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only.

Read first: CLAUDE.md; research-handoff.md (# Latest/Sprint handoff);
claude-learning-rules.md; the relevant ADR(s); defect-pattern-log.md,
rejected-approaches-log.md, architecture-review-log.md,
technical-debt-register.md; pr-review-checklist.md (A–C).

Task: <objective>
Allowed files: <paths>     Forbidden files: <paths / restate no-code rule>
Acceptance criteria: <list>
Tests: <unit/integration incl. edge cases + prior defects>
Rollback notes: <how to revert>
Definition of done: <per section 7 above>

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate, commit/push to the designated
branch, then STOP. Do not start the next task.
```
