# Quality Feedback Loop & Quality Memory

> **Purpose.** Prevent repeated weak research, recurring defects, premature or
> wrong architecture, missed edge cases, and repeated Claude mistakes across
> sessions. This project **does not rely on chat memory** — every lesson,
> rejected approach, recurring issue, architectural concern, and review finding
> is saved into GitHub under `/docs/05-qa`.
>
> **Roles:** Claude runs the loop while executing; **ChatGPT** performs the
> strict review pass and approves phase transitions (see `CLAUDE.md` §2).

Supporting logs:
[`defect-pattern-log.md`](./defect-pattern-log.md) ·
[`architecture-review-log.md`](./architecture-review-log.md) ·
[`rejected-approaches-log.md`](./rejected-approaches-log.md) ·
[`technical-debt-register.md`](./technical-debt-register.md) ·
[`pr-review-checklist.md`](./pr-review-checklist.md) ·
[`../06-prompts/claude-learning-rules.md`](../06-prompts/claude-learning-rules.md)

---

## 1. The loop

```
  do work (Claude) ─▶ ChatGPT strict review ─▶ classify result + each issue
        ▲                                                    │
        │                                                    ▼
  next session reads logs + handoff  ◀──  log to /docs/05-qa, update rules/tests
```

**Every Claude session ends with a learning review** (§6) and updates the
handoff's **Learning feedback loop** section.

## 2. Review decision categories

Every review (especially every **ChatGPT review pass**) classifies the output
as exactly one of:

| Decision | Meaning | Action |
| --- | --- | --- |
| **accepted** | Meets the bar as-is. | Proceed. Log a lesson only if one emerged. |
| **accepted with minor corrections** | Usable after small fixes. | Apply fixes; log any issue types found. |
| **revise** | Material gaps; rework before use. | Rework; log issue types; re-review. |
| **reject** | Wrong/unsafe/unsupported. | Do not use; log in `rejected-approaches-log.md`. |

## 3. Issue categories (classify every issue)

1. weak research
2. missing citation
3. unsupported assumption
4. premature architecture
5. incorrect Odoo assumption
6. incorrect Shopify API assumption
7. weak modularity
8. poor UX thinking
9. missing error handling
10. missing retry/recovery logic
11. duplicate-prevention risk
12. security/permission weakness
13. performance risk
14. missing test coverage
15. regression risk
16. unclear handoff
17. token waste

## 4. Escalation thresholds (anti-repetition rule)

Track occurrences per category in
[`defect-pattern-log.md`](./defect-pattern-log.md).

- **1st occurrence:** log it, fix it, capture a concrete lesson.
- **2nd occurrence (same category):** **update the relevant checklist or prompt
  rule** (`pr-review-checklist.md`, `claude-learning-rules.md`, or a template)
  so it is caught systematically. Note it in the handoff.
- **3rd occurrence (same category):** **pause implementation** until a concrete
  prevention rule, automated test, or review gate exists that would catch the
  issue. Record the gate and set the log row to `ESCALATED`.

These counts are cumulative across all sessions — the reason they live in
GitHub, not memory.

## 5. Lessons must be concrete and reusable

- ❌ Vague: "Be careful with inventory sync."
- ✅ Concrete: "Key Shopify inventory writes on `inventory_item_id` +
  `location_id`; SKU-only writes double-decrement multi-location SKUs.
  Prevention: mapping-table uniqueness check + a multi-location regression test."

Every lesson names: the trigger, the root cause, and the specific prevention
(rule, checklist item, or test).

## 6. End-of-session learning review (mandatory)

Write the results into the handoff's **Learning feedback loop** section:

- New issues discovered (with categories).
- Repeated issue patterns (note any category at count ≥ 2 / ≥ 3 + action taken).
- Rules/checklists updated.
- New rejected approaches (→ `rejected-approaches-log.md`).
- New technical debt (→ `technical-debt-register.md`).
- Architecture concerns (→ `architecture-review-log.md`).
- Tests or review gates needed.
- Should future prompts change? Yes/No (and update them now if yes).

## 7. Quality gate (a session is NOT complete until all are true)

1. Handoff updated (incl. the Learning feedback loop section).
2. Quality feedback loop checked (this file + logs).
3. New learning captured in the correct file.
4. Any rejected approach logged.
5. Any accepted technical debt logged.
6. Any repeated issue pattern escalated per §4.

## 8. Implementation acceptance gate

No implementation task is accepted unless the feedback-loop files were checked
and updated where relevant, and no category sits at its 3rd-occurrence pause
without a prevention rule/test/gate in place. This is in addition to the
ChatGPT approval gate (`CLAUDE.md` §5).

## 9. Routing (where things go)

| You found… | Log it in… |
| --- | --- |
| A recurring defect / missed edge case | `defect-pattern-log.md` |
| An architecture idea under discussion (pre-decision) | `architecture-review-log.md` |
| An approach we decided NOT to use | `rejected-approaches-log.md` |
| A shortcut accepted for now | `technical-debt-register.md` |
| A finalized, accepted decision | `../04-decisions/` (ADR) |
| A new recurring rule for Claude | `../06-prompts/claude-learning-rules.md` |
| A new review check | `pr-review-checklist.md` |

## 10. Phase-exit criteria

`[Recommendation — becomes binding when this PR is merged by ChatGPT]`

**Research phase exit for Phase 1** requires all of:

1. DEC-003 accepted. *(Done — 2026-07-01.)*
2. AR-002 / AR-003 / AR-005 accepted (not just framed/narrowed).
3. Phase 1 domain-model briefs accepted.
4. A DEC-003 scope-hole amendment accepted (covering any gap DEC-003 itself or
   later review identifies).
5. A UX/operator-flow sprint accepted, or explicitly parallelized with the
   above rather than silently skipped. *(Done — 2026-07-03, via
   [`DEC-012`](../04-decisions/DEC-012-ux-operator-flow-strategy.md), after
   PR #68 merged into `Shopify-connector` and Fable's minor-change review was
   applied. This satisfies criterion 5 only — it does not by itself open the
   implementation gate; the **Master Blueprint** and a separate ChatGPT
   implementation-gate approval remain required.)*

The **implementation gate** opens only after ChatGPT approval of that exit —
Phase-1-exit criteria being met is necessary but is itself still a ChatGPT
decision, not a self-executing trigger. Once open, every implementation task
must specify (per `CLAUDE.md` §9): allowed files, forbidden files, acceptance
criteria, tests, rollback notes, and definition of done.

**Fable's review is advisory input; ChatGPT is the final decision-maker** on
every phase transition, architecture acceptance, and MVP-scope change (see
`CLAUDE.md` §2).

## 11. Documentation maintenance rule

`[Recommendation — becomes binding when this PR is merged by ChatGPT]`

To keep the repo reviewable as it grows:

- Prefer a **current-state summary + dated changelog** over restating the same
  status in many places.
- Do **not** keep appending long, repeated sections that say the same thing a
  slightly different way each sprint — a short dated note pointing at what
  changed is enough.
- A statement that is no longer current must be marked **superseded** (or
  replaced) at the point a later decision contradicts it — not left to imply
  it is still true.
- Session handoffs should stay short: current sprint summary, key decisions,
  open blockers, next recommended session. See
  `../06-prompts/session-handoff-template.md` for the compact format.
- **Archive, don't delete.** Move old detail into a clearly labelled historical
  section (or a dated archive doc) instead of forcing every future session to
  read thousands of lines to find the current state. Audit history must be
  preserved, not erased.
- Don't restate policy text (branch rules, phase gates, citation rules, etc.)
  across many docs — link to the canonical source (`CLAUDE.md`, this file)
  instead of copying it.
