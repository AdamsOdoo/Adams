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
