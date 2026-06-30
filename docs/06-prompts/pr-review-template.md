# PR Review Template

> Use this structure for every review pass (ChatGPT strict review, or Claude
> self-review) on a PR or deliverable. It pairs with
> [`../05-qa/pr-review-checklist.md`](../05-qa/pr-review-checklist.md) and feeds
> the [Quality Feedback Loop](../05-qa/quality-feedback-loop.md). Post the
> filled template as the review; log issues into the correct `/docs/05-qa` file.

---

## Review of: <PR title / deliverable> (<PR # / branch>)

- **Reviewer:** ChatGPT | Claude (self-review)
- **Date:** YYYY-MM-DD
- **Scope reviewed:** <files / sections>

## 1. Overall decision

> Choose exactly one (see quality-feedback-loop.md §2):

- [ ] **accepted**
- [ ] **accepted with minor corrections**
- [ ] **revise**
- [ ] **reject**

**Rationale:** <one short paragraph>

## 2. Scope & safety checks

- [ ] Only allowed files changed; no code/forbidden files; no Odoo module created.
- [ ] No premature architecture; no MVP/architecture finalization.
- [ ] GitHub is updated; handoff present.

## 3. Findings (classify every issue)

> Category must come from the issue taxonomy (quality-feedback-loop.md §3).

| # | Severity | Category | Finding | Evidence / location | Required fix | Log target |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | High/Med/Low | <taxonomy type> | <what's wrong> | <file:line / URL> | <fix> | defect-pattern-log / rejected / debt |

## 4. Citation & claim-classification audit

- [ ] Every external claim cited (vendor/product + URL + access + date).
- [ ] Claims correctly classified (fact / competitor claim / inference /
      recommendation / decision / open question).
- [ ] No competitor claim stated as fact; no inference stated as a decision.

## 5. Repetition / escalation check

- [ ] Any finding category now at count ≥ 2 → checklist/prompt rule updated.
- [ ] Any category at count ≥ 3 → implementation paused; gate added.

## 6. Required actions before merge / next session

1. <action> — owner — target.

## 7. Notes for the next session / handoff

<carry-forward items, open questions, recommended next session>
