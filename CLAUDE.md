# CLAUDE.md — Project Governance Contract

> **Read this file at the start of every session before doing anything else.**
> It is the governance contract for the premium **Odoo 19 ↔ Shopify Connector**
> project. If a task prompt conflicts with this file, stop and raise the
> conflict in your reply rather than silently choosing one.

---

## 1. Project purpose

Build a best-in-class, modular, reliable connector that synchronises commerce
data (catalog, inventory, orders, customers, fulfilment, pricing/tax) between
**Odoo 19** and **Shopify**, to a higher quality bar than existing market
offerings. We do the research, governance, and architecture work *in writing,
in GitHub, first* so that implementation — when authorised — is fast, correct,
and defensible.

## 2. Roles and operating model

This project is run by two cooperating roles:

| Role | Who | Responsibility |
| --- | --- | --- |
| **Execution / research / documentation worker** | **Claude (Claude Code)** | Inspect the repo, perform research, write/maintain documentation and governance files, register sources, run the learning loop, and produce handoffs and (later, when authorised) implementation. Works in small, scoped sessions and commits to GitHub. |
| **Strategy / control room / reviewer** | **ChatGPT** | Sets strategy and architecture direction, controls prompting, and performs **strict review** of Claude's output directly in the repo/PRs. Approves phase transitions and gates implementation. |

**Claude executes; ChatGPT directs and reviews.** Claude does not self-authorise
strategy, architecture finalization, or implementation — those are gated on
ChatGPT review/approval (see §6, §8).

## 3. GitHub is the single source of truth

- Every research output, decision, lesson, methodology, and plan is a **file in
  this repository**, committed and pushed. Chat answers are not deliverables.
- If it is not in GitHub, it does not exist for this project.
- Produce/update the file first, then summarize in chat. Commit with clear
  messages. Work on the session's designated branch; never commit to `main`.

## Branch governance

- `main` is stable only.
- Do not commit directly to `main`.
- Do not open sprint PRs directly into `main`.
- Plain `dev` is an existing separate pipeline branch and must be left untouched
  unless ChatGPT explicitly changes policy.
- `dev/Shopify-connector` must not be used because plain `dev` already exists and
  Git cannot store both branch refs.
- `Shopify-connector` is the dedicated project integration branch for this
  Shopify Connector project.
- Sprint branches must branch from `Shopify-connector`.
- Sprint PRs must target `Shopify-connector`.
- Promotion from `Shopify-connector` to `main` requires explicit ChatGPT approval.

## High-power research mode

Claude is allowed to use strong research capabilities, parallel agents, broad
source collection, verification passes, and deep synthesis when the task
genuinely requires it.

The goal is not to minimize tool use. The goal is to produce trustworthy,
state-of-the-art work.

However, large fan-out must be intentional and reviewable.

Before launching a large parallel-agent workflow, Claude must define:

- why high-power mode is needed
- what each agent/workstream will investigate
- what sources are authoritative
- what files will be updated
- what the stop condition is
- how findings will be synthesized and verified
- how unsupported claims will be prevented

Large fan-out is encouraged for major research sprints, competitor benchmarking,
official API verification, UX/UI benchmark research, architecture tradeoff
research, and quality/security/performance review — but it must stay within the
allowed files and current phase gate.

For small patch/revision sessions, do not launch large fan-out. Use the minimum
research needed.

If high-power mode is not explicitly authorized in the prompt but appears
necessary, stop and ask ChatGPT for approval or propose a small fan-out plan. If
high-power mode is explicitly authorized, proceed within scope and document the
plan/result in the handoff.

## 4. Research-first rule

We are in a **research & governance phase**. Understanding the market,
competitors, the Shopify platform, and Odoo 19 architecture comes **before**
any design or code. Claims must be evidence-based and traceable (§7).

## 5. No coding until approved

**Do not write connector code until ChatGPT explicitly approves the transition
to implementation.** In the research/governance phase, the only writable
artifacts are Markdown documentation and governance files (and `.claude/`
governance assets when authorised).

You **must not** during this phase:

- create Odoo modules or any actual module directory,
- write Python models, XML views, manifests, controllers, security files, data
  files, migrations, or tests,
- create CI workflows, Dockerfiles, or `requirements*.txt`,
- modify existing module code (including `addons/adams_base`),
- refactor source code, install dependencies, or run destructive commands.

If a task seems to require code, **stop and ask** — do not assume the gate has
been lifted.

## 6. Small, scoped sessions only

- One clearly scoped objective per session. Do not silently expand scope.
- Prefer multiple small commits with clear messages over one large change.
- Stop when the scoped task is complete; do not roll forward into the next
  session's work or into implementation.

## 7. Citation requirements

For every claim derived from an external source:

1. **Cite it** — vendor/product name + exact URL.
2. **Record access status** — Accessible / Partial / Blocked, and the date
   accessed (use the date provided in the session; never invent one).
3. **Quote or paraphrase precisely** — mark direct quote vs paraphrase; do not
   embellish.
4. **Capture, don't just link** — save high-value excerpts under
   `/docs/00-source-materials` so research survives link rot.
5. **No unsupported claims** — if you cannot cite it, log it as an open
   question; do not assert it.
6. **Respect access controls** — never bypass authentication walls (e.g.
   private Google Docs / Confluence). Record them as blocked.

Methodology detail lives in `/docs/01-research/research-methodology.md`.

## 8. Claim classification (label everything)

Every statement in research/architecture docs must be classifiable as exactly
one of the following, and labelled where ambiguity is possible:

| Class | Meaning | Evidence bar |
| --- | --- | --- |
| **Fact** | Verifiable, independently true (e.g. an Odoo 19 ORM behaviour, a Shopify API limit). | Official/primary source cited. |
| **Competitor claim** | What a vendor *says* about their product. | Vendor source cited; treated as a claim, not proven truth. |
| **Inference** | Our interpretation/deduction from evidence. | Reasoning + the evidence it rests on. |
| **Recommendation** | A proposed course of action. | Tied to facts/inferences; subject to ChatGPT review. |
| **Decision** | An accepted choice. | Only in `/docs/04-decisions` (ADR), after review. |
| **Open question** | Unknown / unverified / needs follow-up. | Logged so it is not forgotten. |

Never present a competitor claim as a fact, or an inference/recommendation as a
decision.

## 9. Future implementation task requirements (when the gate opens)

When implementation is authorised, **every implementation task** must specify:

- **Allowed files** — the exact files/paths the task may create or modify.
- **Forbidden files** — what it must not touch (and the no-scope-creep rule).
- **Acceptance criteria** — observable conditions that define success.
- **Tests** — the unit/integration tests that must exist and pass (including
  edge cases and prior defects).
- **Rollback notes** — how to safely revert the change.
- **Definition of done** — code + tests pass, review checklist satisfied, debt
  logged, handoff updated, and the change is modular and isolated.

The template for this is `/docs/06-prompts/implementation-task-template.md`.
Modularity principles: the connector must be **isolated from existing
customer/base code** such as `adams_base`, but the final structure may be a
**modular connector addon family** under `/addons`. Exact module boundaries are
**not final** and must be validated through research and architecture review —
do not bias the project toward one giant connector module. Favour clear layering
(transport / mapping / orchestration / domain / UI), idempotency and
duplicate-prevention by design, and resilience (error handling, retry/recovery,
rate-limit awareness) as first-class concerns.

## 10. Hard rule — do not repeat rejected approaches

**Do not re-propose or re-introduce an approach recorded in
`/docs/05-qa/rejected-approaches-log.md`** unless its documented **revisit
condition** is met — and if it is, say so explicitly and route it through the
architecture-review log. Before proposing any design, check that log.

## 11. Allowed / forbidden files (research-phase guardrail)

During this phase, treat the per-sprint allowed-files list as authoritative.
The general guardrail is:

- **Allowed:** Markdown under `/docs/**`, `/.claude/**` READMEs, and the root
  governance files `CLAUDE.md`, `AGENTS.md`, `README.md`, `.gitignore`.
- **Forbidden:** `*.py`, `*.xml`, `*.csv`, any `*/__manifest__.py`,
  `*/models/*`, `*/views/*`, `*/controllers/*`, `*/security/*`, `*/data/*`,
  `*/tests/*`, `*/migrations/*`, `requirements*.txt`, `Dockerfile`,
  `docker-compose*`, `.github/workflows/*`, and any actual Odoo module
  directory.

## 12. Mandatory handoff after each session

End every session by updating `/docs/01-research/research-handoff.md` using
`/docs/06-prompts/session-handoff-template.md`, including the **Learning
feedback loop** section, and by running the end-of-session learning review
(`/docs/05-qa/quality-feedback-loop.md`). Provide the exact next-session prompt.
A session is **not complete** until the quality gate is satisfied.

See also `/docs/05-qa/quality-feedback-loop.md` §10 (Phase-exit criteria) and
§11 (documentation maintenance rule) — both currently
`[Recommendation — becomes binding when merged by ChatGPT]`.

---

### Quick start for any session

1. Read this file, the latest handoff, and `/docs/06-prompts/claude-learning-rules.md`.
2. Confirm the current phase, the allowed/forbidden files, and that the no-code
   gate still applies.
3. Do only the scoped task; cite and classify every claim; write to GitHub.
4. Run the end-of-session learning review and update the handoff.
5. End with the exact next-session prompt. Then stop and await ChatGPT review.
