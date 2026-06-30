# Research Sprint A Handoff

> Continuity record for **Research Sprint A — Governance, Research Workspace,
> Source Inventory, and Research Backlog.** Continuity lives in GitHub, not chat.
> The running **Sprint checkpoint log** (one note per stage) is at the bottom.

## Session summary

Research Sprint A established the GitHub-based **governance and research
foundation** for the premium Odoo 19 ↔ Shopify Connector project, so ChatGPT
can review the repo directly and direct the next sprint. Work was done in six
documentation-only stages on a clean branch off `main`: workspace setup →
governance contract & templates → learning feedback loop → research workspace
(inventory, methodology, backlog) → placeholder READMEs → finalization. **No
connector code, no Odoo module, and no forbidden files were created.** No
competitor deep dives, MVP finalization, or architecture decisions were made —
those are explicitly out of scope and gated.

## Branch and commits

**Branch:** `docs/research-sprint-a-governance-inventory` (based on `origin/main`
@ `68007a9`).

| Hash | Message |
| --- | --- |
| `2e4c276` | docs: create connector governance workspace |
| `d143086` | docs: add governance and review templates |
| `1aba406` | docs: add quality feedback loop |
| `f4f3e7d` | docs: add research inventory and backlog |
| `8aa536b` | docs: add product architecture and claude placeholders |
| _(final)_ | docs: finalize research sprint a handoff |

## Files created or updated

**Root governance**
- `CLAUDE.md` (new) — governance contract (roles, source-of-truth,
  research-first, no-code-until-approved, scoped sessions, citation rules, claim
  classification, future implementation-task requirements, allowed/forbidden
  files, do-not-repeat-rejected rule, mandatory handoff).
- `AGENTS.md` (new) — six **proposed** future agents, marked proposed only.
- `README.md` (updated) — preserved existing content; added the project
  workspace map.

**Research (`docs/01-research/`)**
- `resource-inventory.md`, `research-methodology.md`, `research-backlog.md`,
  `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `quality-feedback-loop.md`, `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md`, `pr-review-checklist.md`.

**Prompts/templates (`docs/06-prompts/`)**
- `claude-session-prompts.md`, `claude-learning-rules.md`,
  `implementation-task-template.md`, `pr-review-template.md`,
  `session-handoff-template.md`.

**Decisions** — `docs/04-decisions/decision-record-template.md` + `README.md`.

**Placeholder READMEs** — `docs/00-source-materials/README.md`,
`docs/02-product`, `docs/03-architecture`, `docs/07-implementation-plan`,
`docs/08-release-readiness`, and `.claude`, `.claude/skills`, `.claude/agents`.

## What changed

The repository went from a bare Odoo SH scaffold (`addons/adams_base`,
`README.md`, `.gitignore`) to a full **research/governance workspace**: a
governance contract, a learning feedback loop with four logs, a research
methodology, a registered source inventory of 8 resources, a 14-section research
backlog, and review/handoff/decision templates — all documentation. The Odoo
addon scaffold under `/addons` was left untouched.

## Evidence and citations added

Initial **access status** for the 8 sources was verified on **2026-06-30** (no
auth bypass): **Accessible** — Webkul (R1), Emipro (R3), Odoo Apps
ecommerce_shopify (R6), VentorTech website (R7), Odoo Apps sh_shopify_connector
(R8); **Partial** — VentorTech Confluence (R4, anonymous-access banner);
**Blocked** — Teqstars docs (R2, HTTP 403 bot-block, not a login wall), project
Google Doc (R5, login wall). On-page pricing recorded as facts-on-date: R6
$195.56 (OPL-1), R8 $168.81 (OPL-1), R7 EUR 499. No detailed feature claims were
asserted — only registration/triage. Full detail in `resource-inventory.md`.

## Assumptions

- The connector will be a **separate, self-contained addon**; `adams_base` is
  unrelated company/base code (inference from repo layout + README).
- "Initial value" / "Evidence strength" in the inventory are **triage
  inferences**, not vendor facts.
- The default research order in the backlog is reasonable but adjustable once
  blocked sources are resolved.

## Open questions

- R2 Teqstars: will an alternate fetch (different UA / browser / cache) work, or
  is the 16.0 doc the fallback?
- R5 Google Doc: can the owner grant view access or provide an export? What is
  its actual content?
- R6 ecommerce_shopify: is the listing Odoo S.A. official or a partner module
  (author shown as "Odoo IN Pvt Ltd")?
- R4 VentorTech Confluence: which child pages/screenshots require login?

## Risks

- **Access risk:** two blocked + one partial source could delay specific deep
  dives (RB-02.2, RB-02.6); the backlog isolates these so they don't stall the
  rest.
- **Source bias:** all 8 sources are vendor-published; technical facts must come
  from official Shopify/Odoo docs (RB-05, RB-06), not competitor claims.
- **Scope creep risk:** strong guardrails (allowed/forbidden files, no-code
  gate) are in place; future sessions must honour them.
- **Pricing/feature drift:** vendor pages change; deep dives must re-date and
  capture excerpts.

## Learning feedback loop

- **New issues discovered:** None (setup sprint; no research conclusions or code
  to review).
- **Repeated issue patterns:** None (logs initialized empty).
- **Rules/checklists updated:** Established the entire loop —
  `quality-feedback-loop.md` + four logs + `pr-review-checklist.md` +
  `claude-learning-rules.md`; wired references through `CLAUDE.md`, `AGENTS.md`,
  templates, and the methodology.
- **New rejected approaches:** None.
- **New technical debt:** None.
- **Architecture concerns:** None yet (gated). One forward-looking modularity
  constraint recorded: keep the connector an isolated addon.
- **Tests or review gates needed:** None active in research phase; the
  implementation checklist (section C) is staged for later.
- **Should future prompts change? Yes/No:** No — this sprint produced the
  reusable prompt library; future sessions should use it as-is.

## What ChatGPT should review

1. **Governance correctness** — does `CLAUDE.md` capture the intended
   Claude/ChatGPT operating model, gates, and claim-classification scheme?
2. **Learning loop sufficiency** — are the escalation thresholds (2×/3×), issue
   taxonomy, and log schemas adequate to prevent repeated mistakes?
3. **Research methodology** — is the source hierarchy, claim classification, and
   extraction method rigorous enough for trustworthy deep dives?
4. **Resource inventory** — accuracy of access triage; is the
   official-vs-partner provenance flag for R6 handled correctly?
5. **Research backlog** — are sequencing, dependencies, and acceptance criteria
   right? Anything missing before deep dives start?
6. **Proposed agents** — approve/adjust the six proposed agents (still inactive).
7. **Blocked sources** — decide the unblock path for R2 (Teqstars) and R5
   (Google Doc) before their backlog items.

## Recommended next session

**RB-01.1 — Validate and unblock sources** (resolve R2/R5 access), then begin
deep dives with **RB-02.1 — Webkul** (accessible, no blockers). Run
`RB-12` (feature taxonomy) early and `RB-05`/`RB-06` (official Shopify/Odoo
notes) in parallel. Use the prompts in `docs/06-prompts/claude-session-prompts.md`.

## Stop confirmation

Stopped at the Research Sprint A boundary as instructed: branch pushed, one
**draft** PR opened for ChatGPT review, not merged. **No** deep competitor
research, **no** architecture, **no** implementation was started. Awaiting
ChatGPT review.

## Sprint self-review

- **Scope respected:** Yes — governance/research documentation only.
- **No coding performed:** Yes — no `.py`/`.xml`/`.csv`, no module, no manifest.
- **Forbidden files untouched:** Yes — forbidden-pattern scan clean; `addons/`
  untouched (verified via `git diff --name-only origin/main`).
- **Research inventory complete:** Yes — all 8 resources registered with the
  required schema and verified access status.
- **Governance files complete:** Yes — CLAUDE.md, AGENTS.md, README, templates,
  checklist.
- **Learning loop complete:** Yes — feedback-loop doc + four logs + learning
  rules.
- **Handoff updated:** Yes — this file (all required sections + checkpoint log).
- **Ready for ChatGPT review:** Yes — draft PR opened.

---

## Sprint checkpoint log

> One short note per stage (most recent last).

- **Stage 1 — Repo inspection & safe setup (2026-06-30):** Confirmed remote
  default branch is `main` at `68007a9` (clean Odoo scaffold:
  `addons/adams_base`, `README.md`, `.gitignore`; no `docs/`, no `CLAUDE.md`).
  Created the clean branch `docs/research-sprint-a-governance-inventory` from
  `origin/main` (deliberately not from the prior research branch, so this PR
  contains exactly this governance foundation). Created the `/docs/00..08` and
  `/.claude/{skills,agents}` directory structure. No code touched. Next: Stage 2
  governance files.
- **Stage 2 — Governance files (2026-06-30):** Created `CLAUDE.md` (roles:
  Claude=execution/research/docs worker, ChatGPT=strategy/control-room/reviewer;
  GitHub source-of-truth; research-first; no-code-until-approved; small scoped
  sessions; mandatory handoff; citation rules; the fact/competitor-claim/
  inference/recommendation/decision/open-question classification; future
  implementation-task requirements incl. allowed/forbidden files, acceptance
  criteria, tests, rollback, definition of done; and the hard do-not-repeat-
  rejected-approaches rule). Created `AGENTS.md` listing six **proposed** agents
  (competitor-research, shopify-api-research, odoo-architecture-research,
  ux-benchmark, qa-review, prompt-control) — none active. Updated `README.md`
  (preserved existing title/description; added the project workspace map).
  Added `decision-record-template.md`, `pr-review-checklist.md`,
  `implementation-task-template.md`, `pr-review-template.md`, and
  `session-handoff-template.md`. Docs only; no forbidden files. Next: Stage 3
  learning feedback loop.
- **Stage 3 — Learning feedback loop (2026-06-30):** Created
  `quality-feedback-loop.md` (review-decision categories; 17-type issue
  taxonomy; 2×→update-rule / 3×→pause-implementation escalation; concrete-lesson
  rule; end-of-session review; quality + acceptance gates; routing table) and
  the four logs with the exact required columns — `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md` (all initialized empty with instructions). Created
  `claude-learning-rules.md` with the mandatory 7-item pre-session checklist
  (previous handoff, defect log, rejected log, architecture-review log, decision
  records, current phase, allowed/forbidden files). Next: Stage 4 research
  workspace + source inventory.
- **Stage 4 — Research workspace + source inventory (2026-06-30):** Created
  `00-source-materials/README.md` (capture rules; empty until deep dives).
  Created `resource-inventory.md` registering all 8 sources with the required
  schema (ID, name, URL, source type, competitor/category, initial value,
  evidence strength, current access status, what-to-extract-later, open
  questions, notes); access verified 2026-06-30 (5 Accessible, 1 Partial — R4
  VentorTech, 2 Blocked — R2 Teqstars 403/bot-block & R5 Google Doc login);
  Google Doc marked private/user-provided/access-dependent; no detailed feature
  claims asserted. Created `research-methodology.md` (source hierarchy; citation;
  competitor-evidence; claim-classification; screenshot/pricing/feature/UX/
  reliability/technical-risk extraction; deep-dive procedure; MVP/Phase2/Advanced/
  Optional/Avoid disposition rules). Created `research-backlog.md` (14 sections,
  RB-01..RB-14, each item with Objective/Inputs/Output file/Acceptance criteria/
  Dependencies/Status + sequencing). Next: Stage 5 placeholder READMEs.
- **Stage 5 — Placeholder READMEs (2026-06-30):** Created concise READMEs for
  `docs/02-product`, `docs/03-architecture`, `docs/04-decisions`,
  `docs/07-implementation-plan`, `docs/08-release-readiness`, and `.claude`,
  `.claude/skills`, `.claude/agents` — each stating purpose, what belongs, what
  does not belong yet, and current status. The `.claude/skills` and
  `.claude/agents` READMEs explicitly recommend **deferring** active skills/
  agents until the research workflow stabilizes (premature automation may encode
  weak assumptions). Next: Stage 6 final self-review, handoff, push, draft PR.
- **Stage 6 — Final self-review, handoff, push, draft PR (2026-06-30):** Added
  `claude-session-prompts.md` to complete the prompt library (whitelisted file;
  goal #7). Ran final checks: `git diff --name-only origin/main` shows only
  allowed docs/governance files; forbidden-pattern scan clean; `addons/`
  untouched. Filled all required handoff sections + the sprint self-review.
  Pushed the branch and opened one **draft** PR for ChatGPT review. Stopped.
