> **Current development entrypoint — odoo-harness 1.2.1, installed in this repository:** use the `odoo-dev` / `odoo-review` skills and `.odoo-harness/oh` described in the managed block at the end of this file. The adopted harness source is pinned in `.odoo-harness/lock.json` (MostafaEssamm12/Odoo `176f07317e5a6cd8cd9b769d7ebd3d99eca34bd1`). Resume from the feature's current handoff and `.odoo-harness/HANDOFF.md`. The earlier external-toolkit adapter (`.odoo-harness/connection.json`, `scripts/work-harness.py`, [former onboarding](docs/harness-onboarding.md)) is superseded and kept only for provenance and its metadata check; do not run both workflows.
>
> **This repository is public.** Never commit customer data, credentials, Enterprise source, or screenshots/logs taken from customer databases. Keep `.odoo-harness/evidence/` and other detailed evidence private (the folder is git-ignored here) and commit only sanitized summaries; this overrides the harness default of committing evidence. Only the owner deploys to `main` (production) and `staging`. The historical governance below is preserved for provenance; its research-only phase and role assignments do not override newly authorized development.

# AGENTS.md — Proposed Future Agents (not yet active)

> This file lists **proposed** automation agents for the Odoo 19 Shopify
> Connector project. **None of these agents are active.** They are documented
> here so ChatGPT (the strategy/control room) can review and shape the
> automation plan *before* any agent is built.
>
> **Do not create functioning agents now.** Premature automation can encode
> weak or unverified assumptions into the workflow. Agents will be created later,
> only after the research workflow has stabilised and ChatGPT approves.
>
> Governance authority for the project is `CLAUDE.md`. If this file and
> `CLAUDE.md` ever disagree, `CLAUDE.md` wins.

## Status legend

- **Proposed** — described here; not built; not callable.
- (Future) **Approved** — ChatGPT has approved building it.
- (Future) **Active** — implemented under `/.claude/agents/` and in use.

All agents below are **Proposed**.

## Proposed agents

| Agent | Status | Intended purpose | Intended scope / guardrails (when built) |
| --- | --- | --- | --- |
| **competitor-research-agent** | Proposed | Deep-dive one competitor connector (Webkul, Teqstars, Emipro, VentorTech, Softhealer, official ecommerce_shopify) into a cited, comparable profile. | Read-only research (web read + repo read); no write/code; must cite and classify every claim; never bypass auth. |
| **shopify-api-research-agent** | Proposed | Establish official Shopify platform facts: Admin REST/GraphQL, webhooks, scopes, versioning, rate limits, bulk ops, idempotency, app-review requirements. | Read-only; prefer official Shopify docs; always state the API version a fact applies to. |
| **odoo-architecture-research-agent** | Proposed | Identify correct Odoo 19 extension points and modularity boundaries (sale/stock/product/account/delivery, ir.cron/queue, external IDs/mapping, security). | Read-only; prefer official Odoo 19 docs; may read repo but never modify it. |
| **ux-benchmark-agent** | Proposed | Benchmark setup/onboarding and operational UX across connectors (connect flows, mapping wizards, error surfaces, screenshots). | Read-only; cite screenshot sources; separate observation from UX opinion. |
| **qa-review-agent** | Proposed | Apply the PR/review checklist and the issue taxonomy to a deliverable; surface defects, missing citations, and unsupported assumptions. | Read-only review; classifies findings; routes them to the correct `/docs/05-qa` log; does not fix code. |
| **prompt-control-agent** | Proposed | Maintain and improve the reusable prompts/templates and enforce the learning rules between sessions. | Docs-only; edits `/docs/06-prompts/**`; no code; changes reviewed by ChatGPT. |

## Why defer

- The research methodology and feature taxonomy are not yet stable; an agent
  built now would bake in assumptions we may reject.
- ChatGPT should review the proposed roles, scopes, and guardrails first.
- Each agent, when built, must be **narrow, safe, read-only (or docs-only)**,
  and must embed the citation, claim-classification, and handoff requirements
  from `CLAUDE.md`.

## Activation criteria (future)

An agent moves Proposed → Approved → Active only when:

1. The research workflow it supports is stable and documented.
2. ChatGPT approves its purpose, scope, and guardrails.
3. Its definition is added under `/.claude/agents/` with least-privilege tools
   and the project's citation/handoff rules baked in.

<!-- odoo-harness:start (managed by odoo-harness 1.2.1; change it in the harness repo, not here) -->
## Odoo development (odoo-harness 1.2.1)

This repository holds custom Odoo 19 Enterprise modules deployed on Odoo.sh. Project settings, including the production and staging branch names, are in `.odoo-harness/project.json`.

- For any Odoo work (models, views, security, reports, data, migrations, JavaScript), use the `odoo-dev` skill; for reviews, use `odoo-review`. Open a skill's reference files only when the task touches their topic.
- Odoo 19 differs from the older versions most examples show. Check an API in the real source (`.odoo-harness/oh src <pattern>`) instead of relying on memory.
- Test with `.odoo-harness/oh test [modules]`: a fresh database with demo data, like an Odoo.sh development build. **passed** means the required tests really ran and passed; **not verified** lists what didn't run; **blocked** means Enterprise code isn't available locally, so verify on an Odoo.sh development build. Report only the result the tool gave.
- Work on a feature branch. Pushing to or merging into the production or staging branch deploys it on Odoo.sh, so only the user does that. A GitHub ruleset on those branches is what enforces it (`oh doctor` says whether it does, and for which identity); in Claude Code a hook also blocks it.
- Keep existing data safe. When an installed module's data, fields or views change, bump the manifest `version` (Odoo.sh runs the update only then). When stored data must change, add a migration script and a check of the upgraded records.
- Enforce access rules on the server (access rights, record rules, multi-company checks). New user-facing text needs English and Arabic, and layouts must work right-to-left. Figures come from Odoo's standard reports whenever one provides them.
- Run tests, fix failures and re-run them without asking. Ask the user only for business decisions you can't infer from the code or data; otherwise state your assumption and continue.
- The work is done when the acceptance criteria are met, the tests pass (locally and/or on the Odoo.sh build), the result records in `.odoo-harness/evidence/` (with their logs and screenshots) are committed with the change and `oh evidence` shows them intact and current, and the feature notes are updated. End with one outcome: **completed**; **blocked** (say why); or **not verified** (say what couldn't be checked). Say whether the review was independent or a self-review.
- When resuming work, read `.odoo-harness/HANDOFF.md` first. Before stopping with work left, update it.
<!-- odoo-harness:end -->
