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
| incorrect Shopify API assumption (#6) | 1 | No (1st — logged + prevention rule). NB: Sprint C found a competitor (Emipro) doc citing the **stale** "19 retries/48h" figure — external confirmation the DP-001 risk is real; **not adopted as fact**. |
| token waste (#17) / unclear handoff (#16) | 1 | No (1st — high-power research mode policy added) |
| unsupported assumption (#3) / weak research (#1) | 1 | No (1st — DP-003; mitigated by the capture+verify two-pass + strict claim classification) |

---

## Log

| ID | Date | Session / PR | Defect or issue pattern | Category | Root cause | Impact | Prevention rule | Required test or review gate | Status | Related files / PRs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _DP-000_ | _YYYY-MM-DD_ | _e.g. Sprint A / PR #_ | _Concise pattern_ | _taxonomy type_ | _Underlying cause_ | _What it broke/risked_ | _Concrete, reusable rule_ | _Test or gate to add_ | _Open_ | _paths / PR links_ |
| DP-001 | 2026-06-30 | Sprint B / RB-05.1 | Commonly-cited / training-data Shopify API figures were **stale vs the current official docs** — e.g. webhook retry "19 attempts/48h" (actual: **8 retries/4h**), REST Plus bucket "80" (actual: **400**); the `/usage/rate-limits` page also moved to `/usage/limits` and is now GraphQL-only | incorrect Shopify API assumption (#6) | Shopify limits/policies are version-independent and change **without** an API-version bump; memorized/forum figures drift from the live page | Would have asserted stale numbers as Tier-1 "facts" had they been taken on trust instead of re-read and cited | For high-stakes numeric/policy facts (rate limits, retry windows, version support, scopes), **re-read the exact official page and cite it; if a number is not literally on the page, mark it Open question — never assert a remembered/forum figure** | An **independent verification pass** that re-reads the canonical pages for the highest-stakes facts (applied this sprint and to be reused in future API research) | **Mitigated** (caught pre-merge by the verification pass) | `../01-research/shopify-official-api-notes.md` (Risks), `../00-source-materials/shopify-official.md` |
| DP-002 | 2026-06-30 | Sprint B / PR #50 | Large parallel-agent fan-out was used without a persistent governance rule defining when high-power research mode is appropriate | token waste (#17) / unclear handoff | No explicit high-power research mode policy existed yet | Large tool use can be hard to review or repeat if the fan-out plan is not documented, even when the output is valuable | High-power research mode is allowed and encouraged for major research/benchmarking/architecture work, but the plan, workstreams, sources, stop condition, synthesis method, and verification method must be documented | PR review checklist checks whether high-power mode was justified, scoped, synthesized, and verified | **Mitigated** | PR #50; `../06-prompts/claude-learning-rules.md`; `pr-review-checklist.md` |
| DP-003 | 2026-06-30 | Sprint C / competitor deep dives | Competitor capability statements — **especially from a bot-blocked docs site (Teqstars 403) or a screenshot-free listing (ecommerce_shopify)** — risk being recorded as facts; "real-time" marketing also risks masking a cron/queue model | unsupported assumption (#3) / weak research (#1) | Vendor marketing is persuasive and detailed; blocked/unverifiable sources still produce quotable text; high-power fan-out can amplify volume over rigor | Would have overstated competitor capabilities (e.g. Teqstars idempotency/queue-retry, "real-time" sync) as proven facts, corrupting the matrix and downstream gaps/MVP | **Classify every line** (Fact / on-page fact / competitor claim / visible demonstrated workflow / blocked-unknown); **never elevate a competitor claim to a fact**; run an **adversarial verification pass** that re-reads the source and downgrades anything not literally supported (e.g. SH multi-company → not-found; EC "real-time" → cron; R2 Partial → Blocked) | The Sprint C **capture→verify two-pass** (one verifier per source) + the matrix's per-cell symbol (✅/🟨/⬜/🚫/🔒) + the "evidence note" column — reuse for future competitor research | **Mitigated** | `../01-research/competitor-deep-dives.md`; `../01-research/competitor-feature-matrix.md`; `../00-source-materials/competitor-source-notes.md` |

_First entries logged in Research Sprint B. DP-001 is a **prevented** issue
(caught by the verification pass before it became a shipped fact). DP-002 is
**not** a "bad" outcome and **not** a capability limit — the Sprint B fan-out
produced valuable output. It records that, at the time, **no persistent
high-power research mode policy existed** to keep large workflows intentional and
reviewable. It is **Mitigated** by the new **High-power research mode** policy in
`../../CLAUDE.md`, `../06-prompts/claude-learning-rules.md`, and
`../06-prompts/claude-session-prompts.md` (which **encourages** high-power mode
when justified, requiring only that the plan/workstreams/sources/stop-condition/
synthesis/verification be documented) plus the capability-use checks in
`pr-review-checklist.md`. Recorded so the anti-repetition counter (§4) is
meaningful for future sessions._
