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
| unsupported assumption (#3) / weak research (#1) | 3 | **3rd (DP-003, DP-004, DP-006) — ESCALATED.** Per §4, at the 3rd occurrence implementation pauses until a prevention rule/review gate is in place. Implementation is **already paused by the no-code gate**; an **evidence-consistency gate** is now recorded (see the escalation note below): no capability may enter MVP/architecture as a decision until its evidence strength, conditionality, and competitor coverage have been ChatGPT-reviewed. Prior prevention rules still hold (config field ≠ demonstrated support; market promise ≠ demonstrated bidirectionality; ✅ only for a demonstrated workflow). |
| premature architecture (#4) | 2 | **2nd (DP-005, DP-006)** — at the update-rule threshold. Prevention rule (reinforced): taxonomy rows must distinguish **unconditional** platform requirements from **conditional** ones, and label improvement opportunities as inference — not demonstrated evidence or decisions. NB: an earlier Sprint A "one giant module" bias was captured in `architecture-review-log.md` AR-001, not as a DP row. |

---

## Log

| ID | Date | Session / PR | Defect or issue pattern | Category | Root cause | Impact | Prevention rule | Required test or review gate | Status | Related files / PRs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _DP-000_ | _YYYY-MM-DD_ | _e.g. Sprint A / PR #_ | _Concise pattern_ | _taxonomy type_ | _Underlying cause_ | _What it broke/risked_ | _Concrete, reusable rule_ | _Test or gate to add_ | _Open_ | _paths / PR links_ |
| DP-001 | 2026-06-30 | Sprint B / RB-05.1 | Commonly-cited / training-data Shopify API figures were **stale vs the current official docs** — e.g. webhook retry "19 attempts/48h" (actual: **8 retries/4h**), REST Plus bucket "80" (actual: **400**); the `/usage/rate-limits` page also moved to `/usage/limits` and is now GraphQL-only | incorrect Shopify API assumption (#6) | Shopify limits/policies are version-independent and change **without** an API-version bump; memorized/forum figures drift from the live page | Would have asserted stale numbers as Tier-1 "facts" had they been taken on trust instead of re-read and cited | For high-stakes numeric/policy facts (rate limits, retry windows, version support, scopes), **re-read the exact official page and cite it; if a number is not literally on the page, mark it Open question — never assert a remembered/forum figure** | An **independent verification pass** that re-reads the canonical pages for the highest-stakes facts (applied this sprint and to be reused in future API research) | **Mitigated** (caught pre-merge by the verification pass) | `../01-research/shopify-official-api-notes.md` (Risks), `../00-source-materials/shopify-official.md` |
| DP-002 | 2026-06-30 | Sprint B / PR #50 | Large parallel-agent fan-out was used without a persistent governance rule defining when high-power research mode is appropriate | token waste (#17) / unclear handoff | No explicit high-power research mode policy existed yet | Large tool use can be hard to review or repeat if the fan-out plan is not documented, even when the output is valuable | High-power research mode is allowed and encouraged for major research/benchmarking/architecture work, but the plan, workstreams, sources, stop condition, synthesis method, and verification method must be documented | PR review checklist checks whether high-power mode was justified, scoped, synthesized, and verified | **Mitigated** | PR #50; `../06-prompts/claude-learning-rules.md`; `pr-review-checklist.md` |
| DP-003 | 2026-06-30 | Sprint C / competitor deep dives | Competitor capability statements — **especially from a bot-blocked docs site (Teqstars 403) or a screenshot-free listing (ecommerce_shopify)** — risk being recorded as facts; "real-time" marketing also risks masking a cron/queue model | unsupported assumption (#3) / weak research (#1) | Vendor marketing is persuasive and detailed; blocked/unverifiable sources still produce quotable text; high-power fan-out can amplify volume over rigor | Would have overstated competitor capabilities (e.g. Teqstars idempotency/queue-retry, "real-time" sync) as proven facts, corrupting the matrix and downstream gaps/MVP | **Classify every line** (Fact / on-page fact / competitor claim / visible demonstrated workflow / blocked-unknown); **never elevate a competitor claim to a fact**; run an **adversarial verification pass** that re-reads the source and downgrades anything not literally supported (e.g. SH multi-company → not-found; EC "real-time" → cron; R2 Partial → Blocked) | The Sprint C **capture→verify two-pass** (one verifier per source) + the matrix's per-cell symbol (✅/🟨/⬜/🚫/🔒) + the "evidence note" column — reuse for future competitor research | **Mitigated** | `../01-research/competitor-deep-dives.md`; `../01-research/competitor-feature-matrix.md`; `../00-source-materials/competitor-source-notes.md` |
| DP-004 | 2026-07-01 | Sprint C / PR #51 | Evidence classification **overstated a configuration field as demonstrated multi-company support** (Webkul default Company field → ✅) and **overstated bidirectional sync as a common pattern** (all connectors) | unsupported assumption (#3) / weak research (#1) | A **visible configuration field** and a **broad market promise** were summarized too strongly during synthesis | Could bias MVP/architecture toward unsupported multi-company/bidirectional assumptions | Do **not** classify a feature as demonstrated unless a **workflow, behaviour, screenshot, or explicit vendor documentation** proves the specific capability; distinguish a **"coverage claim"** from **true bidirectionality** | **Feature-matrix review** must check whether ✅ is justified by a **demonstrated workflow**, not just a visible field or generic claim | **Mitigated** | PR #51; `../01-research/competitor-deep-dives.md`; `../01-research/competitor-feature-matrix.md`; `../01-research/common-patterns.md` |
| DP-005 | 2026-07-01 | Sprint D / RB-12 (feature taxonomy) | Normalizing the competitor matrix into a **canonical feature taxonomy** risks its *candidate / premium / advanced-later* classifications and *architecture-dependency* tags being **misread later as MVP scope or architecture decisions** | premature architecture (#4) / premature MVP | A clean, structured taxonomy reads as authoritative; classification labels can be mistaken for commitments; synthesis pressure can harden "candidate" into "must build" (a risk `CLAUDE.md` §4–§5, §8–§10 explicitly guard) | Would pre-empt the gated MVP (RB-13) and architecture (RB-14 / AR-002…AR-008) reviews and violate the no-code / research-first gate | Every capability classification must be **explicitly labelled an INPUT/candidate, not a decision**; the taxonomy must carry dedicated "MVP-candidate **inputs, not decisions**" and "Capabilities **requiring** architecture review" sections; MVP stays **RB-13-gated** and architecture stays **RB-14/AR-gated**; architecture-bearing items route to `architecture-review-log.md` (Not decided / Evidence pending), never resolved in the taxonomy | **Product/taxonomy review** must confirm no classification is phrased as a decision and that MVP/architecture remain gated (added to the review notes for ChatGPT in `feature-taxonomy.md`) | **Mitigated** (prevention built into the Sprint D deliverables) | `../02-product/feature-taxonomy.md`; `../02-product/capability-evidence-map.md`; `../02-product/product-research-handoff.md` |
| DP-006 | 2026-07-01 | Sprint D / PR #52 | Taxonomy synthesis introduced **abbreviation ambiguity** and **over-classified two capabilities**: OAuth-first (C-CONN-01) as an **unconditional** official-platform requirement, and auto-applied stock import (C-INV-04) as **demonstrated** competitor evidence (incl. Webkul marked ✅ for import stock) | unsupported assumption (#3) / weak research (#1) / premature architecture (#4) | Condensed taxonomy/evidence-map wording made **conditional** requirements and **improvement inferences** look stronger than the evidence allowed; a duplicate `SH` key (Softhealer vs Shopify official) crept into a legend | Could bias **AR-002** (distribution/auth), **AR-007** (inventory design), or MVP scoping by treating a conditional requirement / an improvement inference as demonstrated/decided | Taxonomy rows must **distinguish unconditional platform requirements from conditional ones**; **improvement opportunities must not be labelled as demonstrated competitor capabilities**; **abbreviations must be globally unique**; competitor coverage symbols must match the Sprint C matrix | **Before MVP/architecture use, capability rows must be cross-checked against the evidence map and the Sprint C matrix for symbol consistency and conditionality** (evidence-consistency gate — see escalation note) | **Mitigated** | PR #52; `../02-product/feature-taxonomy.md`; `../02-product/capability-evidence-map.md` |

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

_**Research/Product Sprint D note (2026-07-01):** **DP-005** is a **prevented**
issue — the risk that the canonical feature taxonomy's classifications could be
misread as MVP/architecture decisions was mitigated in advance by explicit
"inputs, not decisions" framing throughout the Sprint D deliverables. It is the
**1st** occurrence of category #4 (premature architecture) as a formal DP row.
DP-004's prevention rule (config field ≠ demonstrated support; market promise ≠
demonstrated bidirectionality) was **applied, not re-triggered**, during the
taxonomy synthesis — no new unsupported-assumption/weak-research occurrence._

_**ESCALATION — 3rd-occurrence gate (2026-07-01, DP-006).** With **DP-006**, the
**unsupported assumption (#3) / weak research (#1)** category reaches its **3rd
occurrence** (DP-003, DP-004, DP-006), triggering the §4 escalation threshold.
**Implementation remains paused by the existing no-code gate.** Before any
implementation starts, product/MVP and architecture prompts **must include an
evidence-consistency gate: no capability may enter MVP or architecture as a
decision unless its evidence strength, conditionality, and competitor coverage
have been reviewed by ChatGPT.** This is a **recorded review gate only — no
implementation task is set** and none is authorised (the no-code / research-first
gate, `CLAUDE.md` §4–§5, remains in force). The gate also applies DP-006's
specific checks: unconditional vs conditional platform requirements must be kept
distinct, improvement opportunities must not be labelled demonstrated evidence,
and abbreviations must be globally unique._

_**Product Sprint E note (2026-07-01): none — DP-006 gate applied, not
re-triggered.** Product Sprint E (product vision + setup/UX principles;
`../02-product/product-vision.md`, `../02-product/setup-ux-principles.md`) **added no
new defect occurrence** to any category. The **DP-006 evidence-consistency gate** was
**applied throughout**: competitor claims stayed claims (EM/VT-demonstrated evidence
weighted over SH/WK/EC/TQ), no capability entered MVP/architecture as a decision, and
**conditional platform items stayed conditional/open** — OAuth-first (public/App-Store
only), distribution model (AR-002), queue framework (AR-003), REST/GraphQL (AR-002),
multi-company (config field ≠ support, DP-004), module boundaries/names (AR-004),
payouts (Shopify-Payments-gated), and data models (AR-005). DP-003 (claim ≠ fact),
DP-004 (config field ≠ demonstrated support; market promise ≠ demonstrated
bidirectionality), and DP-005 (classification is an input, not a decision) were
**applied, not re-triggered**. Improvement opportunities (auto-apply, unified command
center, freshness indicators) were labelled **inference**, not demonstrated competitor
capability. **No counter change; no new row.** MVP stays RB-13-gated; architecture
stays RB-14 / AR-002…AR-008-gated._

_**Product Sprint F note (2026-07-01): none — DP-006 gate applied, not re-triggered.**
Product Sprint F (MVP scope proposal + non-MVP boundaries + user stories;
`../02-product/mvp-scope.md`, `../02-product/non-mvp-and-later-phases.md`,
`../02-product/user-stories.md`) **added no new defect occurrence** to any category. The
**DP-006 evidence-consistency gate** was **applied throughout** as an explicit 8-check
review in `mvp-scope.md`: no competitor claim was promoted to a fact; **weak/claim-only
evidence was kept OUT of scope** (pHash image dedup, Teqstars 403 breadth, SH/EC breadth
were not turned into MVP scope); improvement opportunities stayed **inference** (unified
command center, recovery-first error center, freshness indicators, empty states, and
**auto-apply stock C-INV-04 → routed to AR-007, not decided**); conditional platform
items stayed conditional/open (OAuth-first public/App-Store-only, distribution AR-002,
queue framework AR-003, REST/GraphQL AR-002, binding data model AR-005, error/retry
taxonomy AR-006, inventory/fulfilment AR-007/008, module boundaries AR-004); WK
multi-company stayed a config field (➖, DP-004) and WK import-stock stayed ⬜; "real-time"
was never asserted (C-SYNC-07 honesty). The MVP proposal **did not finalize architecture**
(every mechanism marked *Architecture-dependent — must be resolved in RB-14*) and **did
not turn weak evidence into scope** — the two Sprint-F-specific risks the prompt asked to
watch. DP-003/DP-004 and DP-005 (classification/scope is an input, not a decision) were
**applied, not re-triggered**. **No counter change; no new row.** MVP stays RB-13-gated
(proposed, not final); architecture stays RB-14 / AR-002…AR-008-gated._

_**Product Sprint F revision (2026-07-01, PR #54 review — consistency patch):** ChatGPT
review returned **REVISE** for a small wording consistency issue: the MVP acceptance
principles referenced the seeded **idempotent-refund / no-double-refund** regression
scenario (A-IMP-4) as if refunds were definitely in MVP, whereas refund sync is marked
**open / lean defer** (C-RET-01). The wording in `../02-product/mvp-scope.md` and
`../02-product/user-stories.md` was clarified: **the idempotent-refund / no-double-refund
regression applies only if refund handling is included in MVP; if refunds are deferred it
is carried forward as a mandatory acceptance principle for the first refund/refund-sync
sprint** (never dropped). This was a **consistency correction, not a new defect
occurrence** — **no new DP row, no counter change.** No MVP scope was finalized and no
architecture decision was made; MVP remains **proposed, not final**._

_**Product Sprint G note (2026-07-01): none — DP-006 gate applied, not re-triggered.**
Product Sprint G recorded ChatGPT's **accepted MVP scope** in
[`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md) and aligned
the product docs (`../02-product/mvp-scope.md`, `../02-product/non-mvp-and-later-phases.md`,
`../02-product/user-stories.md`) to that baseline. It **added no new defect occurrence** to
any category. The **DP-006 evidence-consistency gate** was **applied throughout**: no
competitor claim was promoted to a fact; weak/claim-only evidence stayed **out of scope**
(pHash image dedup, Teqstars 403 breadth, EC/SH breadth); the Webkul default-Company field
stayed a **config field**, not multi-company evidence (DP-004); **auto-apply stock (C-INV-04)
stayed an [Inference] routed to AR-007**, explicitly **not accepted as default MVP
behaviour** (DP-006); "real-time" was never asserted (C-SYNC-07). Critically, the sprint kept
**product-scope acceptance strictly separate from any architecture decision** — DEC-003 is a
**product-scope** record that **feeds AR-002…AR-008 but decides none** (premature-architecture
category #4 **not** triggered). DP-003/DP-004 and DP-005 (a classification/scope is an input
until ChatGPT accepts it — here it *was* accepted, via the correct gated `04-decisions`
route) were **applied, not re-triggered**. **No counter change; no new row.** Architecture
stays RB-14 / AR-002…AR-008-gated; implementation stays blocked._

_**Product Sprint G revision note (2026-07-01, PR #55 review — product-scope correction):**
ChatGPT review of PR #55 returned **REVISE**: the first Sprint G recording **over-deferred
product export** (framed the MVP as "import-first" and pushed product/customer export to
Phase 2). Corrected to **controlled bidirectional product onboarding in MVP** (controlled
product export/update with matching/binding/preview/draft-channel safety); **unrestricted
autonomous bidirectional catalog ownership** and **customer export** stay later. **This is a
product-scope correction, not an implementation defect** — no code exists — and **no
architecture decision was made** (binding/data model → AR-005; API/destructive-apply →
AR-002). **Reusable lesson (source availability can change):** the **TeqStars** docs recorded
**403-blocked in Sprint C (2026-06-30)** were **re-checked accessible on 2026-07-01**;
product export was already **market-baseline** (EM/VT/WK/SH demonstrated), so the correction
does not depend on TQ, but the episode shows that **blocked/weak-evidence sources should be
re-checked before a scope decision leans on their absence** (a refinement of DP-001's
re-read-the-source rule and DP-003's blocked-source handling). **No new DP row and no counter
change** (no broader recurring defect pattern; the existing DP-001/DP-003 rules already cover
the lesson and are reinforced here). A **full TeqStars evidence rebaseline is pending a later
research sprint.** MVP scope stays a product-scope decision; architecture stays RB-14-gated;
implementation stays blocked._

_**Research Sprint C2 note (2026-07-01): source-availability correction — no new defect
occurrence.** Sprint C2 executed the TeqStars rebaseline flagged by the Sprint G note above.
The **R2 Teqstars docs**, recorded **403-blocked in Sprint C (2026-06-30)**, were re-checked
and found **accessible** (HTTP 200 with a browser UA — a bot/UA filter, **not** a login wall;
no auth bypassed). The 31 Odoo 19.0 Shopify doc pages were read and **page-classified**
(demonstrated ✅ vs vendor claim 🟨 vs implied ➖ vs not-found ⬜) in
`../00-source-materials/competitor-source-notes.md`, `competitor-deep-dives.md`, and the
feature matrix. This is a **source-availability correction, not a defect** — the Sprint C
method (refusing to treat blocked content as fact) was **correct** and is preserved as audit
trail. The **DP-003 capture→verify discipline was applied to the new evidence**: a 17-item
adversarial verification pass **downgraded 3 proposed upgrades** (automatic-retry/backoff,
first-class cross-object reconciliation, and a metrics dashboard → **⬜ not found**), and the
Sprint C idempotency search-snippet stayed **unverified**, so **no capability was
over-upgraded** (DP-004 respected). **Reinforced standing rule (no new row, no counter
change):** *a source recorded **Blocked** that is important to a scope/architecture decision
must be re-checked before that decision is finalized — access can change (WAF/bot rules,
vendor doc releases).* This refines DP-001 (re-read the source) and DP-003 (blocked-source
handling); it is not a new recurring pattern. **DEC-003 and the accepted MVP scope are
unchanged**; architecture stays RB-14 / AR-002…AR-008-gated; implementation stays blocked._

_**RB-14 Architecture Preparation — Part 1 note (2026-07-01): no new defect pattern.** RB-14
Part 1 produced the first architecture **framing** docs (`../03-architecture/*`) + a current
official-source refresh, and **added no new defect occurrence** to any category — **no new DP
row, no counter change.** The sprint **applied, not re-triggered**, the standing prevention
rules: **DP-001 (re-read the source)** was applied to the platform facts — a scoped
official-source re-verification (2026-07-01, ~40 Tier-1 pages, verbatim quotes) that **surfaced
version-sensitive deltas** (GraphQL `latest` alias `2026-04`→`2026-07`; `@idempotent` on
inventory set/adjust **required as of 2026-04** with the 2026-01-optional detail; `productSet`
delete-on-omit is **list-fields-only**; dual offline-token model) rather than trusting the
one-day-old baseline, exactly the DP-001 discipline; **DP-003/DP-004** — competitor evidence
was kept as evidence and **not promoted to official fact** in the framing docs (official facts
and competitor demonstrations are separately labelled); **DP-005** — every candidate option and
recommended decision order is **explicitly labelled an input/`[Not decided]`, never a decision**;
**DP-006 evidence-consistency gate** — official facts, competitor evidence, inferences,
recommendations, and open questions are kept distinct, and **conditional platform requirements
stay conditional** (e.g. the GraphQL-only mandate is scoped to *new public apps*; the
custom-app scope is left an **open question**, not asserted). A few facts were **conservatively
downgraded to open questions** on re-verification (GID permanence not asserted; no general
mutation idempotency beyond `@idempotent`; `ir.model.data` `(module,name)` uniqueness
unconfirmed; `sudo()` bypass not literally on `security.rst`) — the opposite of over-claiming,
consistent with DP-001/DP-003. **No architecture decision was made; DEC-003 and MVP scope are
unchanged; implementation stays blocked** (`CLAUDE.md` §4–§5; RB-14)._

_**RB-14 Part 1 — PR #57 revision note (2026-07-01): classification/date caveats cleaned; no new
defect counter.** ChatGPT review of PR #57 returned **REVISE** for **source-classification and
evidence-date consistency** (substance accepted directionally — AR-002/003/005 framed-not-decided;
no code; no architecture decision; no implementation authorization). Cleaned, without changing
architecture scope or any decision: (1) the Shopify/Odoo official-notes "Source hierarchy and
access date" sections now distinguish the **Sprint B baseline (2026-06-30)** from the **RB-14
refresh (2026-07-01)** and record that GraphQL `latest` moved `2026-04`→`2026-07`; (2) **"Odoo
core has no async job queue"** was **downgraded from [Official fact] to [Inference from official
fact]** (docs document only `ir.cron`; `queue_job` is community, not core; verify vs 19.0 source
if load-bearing) consistently across the framing map, AR-003 framing, this log's RB-14 note, and
the handoff; (3) **secret/config storage** (`ir.config_parameter`/config-model/encrypted-field)
is no longer implied as an official recommendation — reclassified **[Open question] + [Inference]**;
(4) the **`ir.model.data` column list + `(module,name)` uniqueness** stay **[Open question]** (not
official-doc fact); (5) **custom-app compliance-webhook** wording made conservative — the
App-Store *review gate* may not apply to a custom app, but **non-App-Store privacy/data-deletion
obligations are left [Open question], not assumed absent** (removed the word "sidesteps"). This is
a **classification/consistency correction, not a new defect occurrence** — the corrections are
applications of DP-001/DP-003/DP-006 (cite/classify precisely; don't over-classify). **No new DP
row; no counter change.** DEC-003 and MVP scope unchanged; architecture stays RB-14-gated;
implementation stays blocked._
