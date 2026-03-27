# Adams Shopify Connector — Multi-Agent AI System (Consolidated)

> **This is the single authoritative design.** It supersedes both `docs/agents/` (original 9-agent) and `docs/ai-agents/` (codex 6-agent). Those directories will be removed.

---

## System Overview

A 7-agent AI system to build, test, and ship a production-grade Odoo v19 ↔ Shopify connector (`adams_shopify`) for sale on the Odoo Apps Store.

### Why 7 Agents (Not 6, Not 9)

| Decision | Rationale |
|----------|-----------|
| Merge Solution Architect + Technical Architect → **Integration Architect** | One person owns the full spec-to-design pipeline. Eliminates a handoff that adds overhead. |
| Keep Odoo Developer + Shopify Agent separate | They touch different file trees, different APIs, different expertise. Parallel execution. |
| Keep **Debugging Agent** (was dropped in 6-agent) | #1 customer complaint across all competitors is duplicates/sync bugs. A dedicated debug methodology prevents the most costly defects. |
| Merge Code Reviewer + Security into **Quality & Security Agent** | Security is a review concern, not a standalone phase. One agent, one gate. |
| Rename DevOps → **Release & Operations Agent** | Matches Odoo.sh deployment reality + marketplace submission. |
| Add **Product Analyst** responsibility to Architect | You asked for a design expert to scan competitive features — this lives inside the Architect's scope. |

### Agent Map

```
                         ┌──────────────────────┐
                         │    ORCHESTRATOR       │
                         │    (Controller)       │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
   ┌──────────▼──────────┐  ┌──────▼───────┐  ┌──────────▼──────────┐
   │ Integration          │  │ Quality &    │  │ Release &           │
   │ Architect            │  │ Security     │  │ Operations          │
   │ (Spec+Design+Product)│  │ Agent        │  │ Agent               │
   └──────────┬──────────┘  └──────▲───────┘  └──────────▲──────────┘
              │                     │                     │
     ┌────────┴────────┐           │                     │
     │                 │           │                     │
┌────▼─────┐    ┌──────▼─────┐    │                     │
│ Odoo     │    │ Shopify    │────┘                     │
│ Developer│    │ Integration│                          │
└────┬─────┘    └──────┬─────┘                          │
     │                 │                                │
     └────────┬────────┘                                │
              │                                         │
     ┌────────▼────────┐    ┌───────────────┐          │
     │ Testing Agent   │───►│ Debugging     │──────────┘
     └─────────────────┘    │ Agent         │
                            └───────────────┘
```

### Core Principles

1. **Contract-Driven**: Agents communicate through defined JSON I/O contracts
2. **Validation Gates**: Every output validated before the next agent consumes it
3. **Single Source of Truth**: Shared memory in `docs/` — agents read, Orchestrator writes
4. **Idempotency Everywhere**: The #1 technical principle for the connector itself AND the agent workflow
5. **Vertical Slices**: Develop by entity (products first, then customers, then orders) not by layer
6. **Fail-Forward**: Failures produce actionable reports, not silent drops

### Reference Documents (Agents MUST consult these)

| Document | Purpose | Path |
|----------|---------|------|
| Odoo v19 Reference | ORM patterns, security, controllers, Odoo.sh | `docs/references/ODOO_V19_REFERENCE.md` |
| Shopify API Reference | GraphQL queries, rate limits, webhooks | `docs/references/SHOPIFY_API_REFERENCE.md` |
| Competitive Analysis | Feature matrix, customer pain points, roadmap | `docs/product/COMPETITIVE_ANALYSIS.md` |
| Architecture | Data models, sync engine, module structure | `docs/architecture/ARCHITECTURE.md` |
| API Mapping | Field-level Odoo ↔ Shopify mapping | `docs/architecture/API_MAPPING.md` |
| Decisions Log | Numbered architectural decisions | `docs/architecture/DECISIONS.md` |
| UX Design | Every screen, button, and user flow | `docs/product/UX_DESIGN.md` |
