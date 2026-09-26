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

---

## Detailed Documents

This system is defined across focused files:

| Document | Contents |
|----------|----------|
| [`AGENT_DEFINITIONS.md`](AGENT_DEFINITIONS.md) | All 7 agents: role, responsibilities, boundaries, I/O contracts |
| [`AGENT_PROMPTS.md`](AGENT_PROMPTS.md) | Ready-to-paste Claude prompts for each agent (with {{variables}}) |
| [`ORCHESTRATION.md`](ORCHESTRATION.md) | Phase workflow, validation gates, communication protocol, failure handling |

### Supporting Documents

| Document | Contents |
|----------|----------|
| [`../product/UX_DESIGN.md`](../product/UX_DESIGN.md) | Every screen, menu, button, wizard, user flow |
| [`../product/COMPETITIVE_ANALYSIS.md`](../product/COMPETITIVE_ANALYSIS.md) | 8 competitors, feature matrix (P0-P3), roadmap |
| [`../references/ODOO_V19_REFERENCE.md`](../references/ODOO_V19_REFERENCE.md) | ORM v19, manifest, security, controllers, Odoo.sh |
| [`../references/SHOPIFY_API_REFERENCE.md`](../references/SHOPIFY_API_REFERENCE.md) | GraphQL 2026-01, rate limits, webhooks, bulk ops |

### Shared Memory (Living Documents)

| Document | Updated By | Contents |
|----------|-----------|----------|
| [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md) | Architect | Data models, sync engine, layer separation |
| [`../architecture/API_MAPPING.md`](../architecture/API_MAPPING.md) | Architect | Field-level Odoo ↔ Shopify mapping tables |
| [`../architecture/DECISIONS.md`](../architecture/DECISIONS.md) | Architect | Numbered decision log with rationale |
| [`../tracking/TASKS.md`](../tracking/TASKS.md) | Orchestrator | Task tracking with status per phase |
| [`../tracking/ERRORS.md`](../tracking/ERRORS.md) | Debugging Agent | Bug log with root causes and fixes |

---

## Quick Start: How to Execute

### Step 1: Pick a vertical slice
Start with **Backend + Infrastructure** (TASK-010 through TASK-015 in TASKS.md).

### Step 2: Run the Architect
Copy the Integration Architect prompt from `AGENT_PROMPTS.md`. Fill `{{variables}}`:
- `{{architecture_doc}}` → contents of `docs/architecture/ARCHITECTURE.md`
- `{{decisions_log}}` → contents of `docs/architecture/DECISIONS.md`
- `{{competitive_analysis}}` → contents of `docs/product/COMPETITIVE_ANALYSIS.md`
- `{{task_description}}` → "Design the shopify.backend model and shopify.binding abstract model"

### Step 3: Validate output at Gate 1
Check: binding model has UNIQUE constraint? Idempotency mechanism defined? Fields have types?

### Step 4: Run developers in parallel
- Odoo Developer prompt → fill with Architect's model spec
- Shopify Agent prompt → fill with Architect's API contract

### Step 5: Review → Test → Debug → Package
Follow the phase flow in `ORCHESTRATION.md`.

### Step 6: Repeat for next slice
Products → Customers → Orders → Inventory → Fulfillment
