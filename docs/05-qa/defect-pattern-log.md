# Defect Pattern Log

> Records recurring defects, bugs, missed edge cases, and quality issues so we
> can detect repetition and escalate per the
> [Quality Feedback Loop](./quality-feedback-loop.md) §4 thresholds.

## How to use

1. Add one row per distinct issue **occurrence**.
2. Set **Category** from the issue taxonomy
   ([`quality-feedback-loop.md`](./quality-feedback-loop.md) §3).
3. Scan existing rows for the same **Category** before logging:
   - **2nd occurrence** → update a checklist/prompt rule; note it in
     **Prevention rule**.
   - **3rd occurrence** → **pause implementation**; add a prevention
     rule/test/review gate in **Required test or review gate**; set **Status** to
     `ESCALATED`.
4. Keep **Defect or issue pattern**, **Root cause**, and **Prevention rule**
   concrete and reusable (feedback-loop §5).
5. **Status** values: `Open`, `Mitigated`, `Closed`, `ESCALATED`.

### Occurrence counter (update as rows are added)

| Category | Count | At/over threshold? |
| --- | --- | --- |
| _none yet_ | 0 | — |

---

## Log

| ID | Date | Session / PR | Defect or issue pattern | Category | Root cause | Impact | Prevention rule | Required test or review gate | Status | Related files / PRs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _DP-000_ | _YYYY-MM-DD_ | _e.g. Sprint A / PR #_ | _Concise pattern_ | _taxonomy type_ | _Underlying cause_ | _What it broke/risked_ | _Concrete, reusable rule_ | _Test or gate to add_ | _Open_ | _paths / PR links_ |

_No defects logged yet (Research Sprint A — governance/research setup, no code).
First entries are expected during deep-dive research and, later, implementation._
