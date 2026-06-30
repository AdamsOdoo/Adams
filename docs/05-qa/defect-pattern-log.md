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
| incorrect Shopify API assumption (#6) | 1 | No (1st — logged + prevention rule) |

---

## Log

| ID | Date | Session / PR | Defect or issue pattern | Category | Root cause | Impact | Prevention rule | Required test or review gate | Status | Related files / PRs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _DP-000_ | _YYYY-MM-DD_ | _e.g. Sprint A / PR #_ | _Concise pattern_ | _taxonomy type_ | _Underlying cause_ | _What it broke/risked_ | _Concrete, reusable rule_ | _Test or gate to add_ | _Open_ | _paths / PR links_ |
| DP-001 | 2026-06-30 | Sprint B / RB-05.1 | Commonly-cited / training-data Shopify API figures were **stale vs the current official docs** — e.g. webhook retry "19 attempts/48h" (actual: **8 retries/4h**), REST Plus bucket "80" (actual: **400**); the `/usage/rate-limits` page also moved to `/usage/limits` and is now GraphQL-only | incorrect Shopify API assumption (#6) | Shopify limits/policies are version-independent and change **without** an API-version bump; memorized/forum figures drift from the live page | Would have asserted stale numbers as Tier-1 "facts" had they been taken on trust instead of re-read and cited | For high-stakes numeric/policy facts (rate limits, retry windows, version support, scopes), **re-read the exact official page and cite it; if a number is not literally on the page, mark it Open question — never assert a remembered/forum figure** | An **independent verification pass** that re-reads the canonical pages for the highest-stakes facts (applied this sprint and to be reused in future API research) | **Mitigated** (caught pre-merge by the verification pass) | `../01-research/shopify-official-api-notes.md` (Risks), `../00-source-materials/shopify-official.md` |

_First entry logged in Research Sprint B. DP-001 is a **prevented** issue
(caught by the verification pass before it became a shipped fact), recorded so
the anti-repetition counter (§4) is meaningful for future API-research sessions._
