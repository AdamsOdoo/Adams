# Adams

Odoo SH Database for Adams.

---

## Odoo 19 ↔ Shopify Connector — research & governance workspace

This repository also hosts the design, research, governance, and (eventually)
implementation of a **premium Odoo 19 ↔ Shopify Connector**. The project is
currently in a **research & governance phase** — no connector code is being
written yet.

- **Governance contract:** [`CLAUDE.md`](./CLAUDE.md) — roles, rules, phases,
  citation/claim rules, allowed/forbidden files, and the implementation gate.
- **Proposed automation:** [`AGENTS.md`](./AGENTS.md) — future agents (not yet
  active).
- **Documentation workspace:** [`/docs`](./docs) — research, product,
  architecture, decisions, QA/quality-memory, prompts, implementation plan, and
  release readiness.

### Roles

- **Claude (Claude Code)** — GitHub execution, research, and documentation
  worker.
- **ChatGPT** — strategy, architecture, prompting, and strict review control
  room.

### Where to start

| You want to… | Go to |
| --- | --- |
| Understand the rules | [`CLAUDE.md`](./CLAUDE.md) |
| See the research plan/backlog | [`docs/01-research/research-backlog.md`](./docs/01-research/research-backlog.md) |
| See the source inventory | [`docs/01-research/resource-inventory.md`](./docs/01-research/resource-inventory.md) |
| See how research is done | [`docs/01-research/research-methodology.md`](./docs/01-research/research-methodology.md) |
| See the latest session handoff | [`docs/01-research/research-handoff.md`](./docs/01-research/research-handoff.md) |
| Understand the quality loop | [`docs/05-qa/quality-feedback-loop.md`](./docs/05-qa/quality-feedback-loop.md) |

> **Note:** The existing Odoo addon scaffold under `/addons` (e.g.
> `adams_base`) is unrelated company/base code. The connector must be **isolated
> from it**, but the final structure may be a **modular connector addon family**
> under `/addons` — exact module boundaries are not final and will be validated
> through research and architecture review. We do not bias the project toward one
> giant connector module.
