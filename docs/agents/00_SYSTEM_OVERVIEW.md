# Multi-Agent AI System for Odoo ↔ Shopify Connector

## System Overview

This document defines a production-grade multi-agent AI system designed to build, test, and deploy an Odoo ↔ Shopify connector module (`adams_shopify`). The system consists of 9 specialized agents orchestrated through a Controller Agent that manages workflow, validates outputs, and enforces quality gates.

### Architecture Diagram

```
                    ┌─────────────────────────┐
                    │   ORCHESTRATOR AGENT     │
                    │   (Controller)           │
                    └────────┬────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │ Solution   │    │ Technical   │    │ DevOps /    │
    │ Architect  │───▶│ Architect   │    │ Packaging   │
    └─────┬─────┘    └──────┬──────┘    └──────▲──────┘
          │                  │                  │
          │           ┌──────▼──────┐           │
          │           │   Shared    │           │
          └──────────▶│   Memory    │◀──────────┘
                      └──────┬──────┘
                             │
               ┌─────────────┼─────────────────┐
               │             │                 │
        ┌──────▼──────┐ ┌───▼────────┐ ┌──────▼──────┐
        │ Odoo Backend│ │ Shopify    │ │ Testing     │
        │ Developer   │ │ Integration│ │ Agent       │
        └──────┬──────┘ └───┬────────┘ └──────▲──────┘
               │             │                 │
               └──────┬──────┘                 │
                      │                        │
               ┌──────▼──────┐          ┌──────┴──────┐
               │ Code        │          │ Debugging   │
               │ Reviewer    │─────────▶│ Agent       │
               └─────────────┘          └─────────────┘
```

### Core Principles

1. **Single Responsibility**: Each agent owns one domain. No overlap.
2. **Contract-Driven**: Agents communicate through defined input/output JSON contracts.
3. **Validation Gates**: Every output is validated before the next agent consumes it.
4. **Shared Memory**: A structured file system acts as the single source of truth.
5. **Idempotency First**: Every integration operation must be safely re-runnable.
6. **Fail-Forward**: Failures produce actionable error reports, not silent drops.

### Target Stack

| Component | Technology |
|-----------|-----------|
| ERP | Odoo 18+ / 19 |
| E-commerce | Shopify (GraphQL Admin API 2024-10+) |
| Webhooks | Shopify Webhooks → Odoo HTTP controllers |
| Queue | Odoo `queue.job` (OCA) or built-in cron |
| Deployment | Odoo.sh |
| Testing | `pytest`, Odoo `TransactionCase`, `HttpCase` |
| Packaging | Odoo Marketplace (apps.odoo.com) standards |

### Integration Scope (MVP)

| Entity | Direction | Method |
|--------|-----------|--------|
| Products | Odoo → Shopify, Shopify → Odoo | GraphQL + Webhooks |
| Customers | Odoo → Shopify, Shopify → Odoo | GraphQL + Webhooks |
| Orders | Shopify → Odoo | Webhooks + Polling |
| Inventory | Odoo → Shopify | GraphQL |
| Prices | Odoo → Shopify | GraphQL |
| Fulfillment | Odoo → Shopify | GraphQL |

### Idempotency Strategy

Every sync operation MUST:
- Use external ID mapping (`shopify.binding` models)
- Check for existing bindings before create
- Use `write_date` / Shopify `updated_at` for change detection
- Store sync checksums to avoid redundant writes
- Handle Shopify's rate limits with exponential backoff
- Log every sync attempt with before/after state
