# Odoo ↔ Shopify AI Multi-Agent System (Optimized)

This folder contains a production-focused optimization of the existing AI multi-agent setup used to build an Odoo (v18+/v19) ↔ Shopify connector on Odoo.sh.

## Contents

- `architecture-assessment.md`: what to keep, fix, and add.
- `optimized-agent-structure.md`: balanced target agent model with explicit boundaries.
- `workflow.md`: streamlined execution flow with quality gates.
- `security-performance-checklist.md`: practical controls for ORM, GraphQL, webhooks, idempotency, and rate limits.
- `prompts/`: refined prompt templates for each agent role.

## Design Principles Used

1. Keep proven separation of concerns.
2. Remove duplicate ownership.
3. Preserve enough specialized roles for quality and safety.
4. Favor deterministic, enforceable outputs.
5. Align with real Odoo integration delivery constraints.
