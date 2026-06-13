# Adams Odoo Addons

## Project Purpose

This repository contains the Adams Odoo addons workspace for building and validating **Shopify Connector Pro Ultimate Edition**, an Odoo 19 + Shopify connector. The Adams database is the pilot implementation before the connector is prepared as a public third-party Odoo App Store product.

## Shopify Connector Pro Ultimate Edition Overview

Shopify Connector Pro Ultimate Edition is intended to be a reliable, financially correct, merchant-friendly Shopify connector for Odoo. The non-negotiable operating principles are:

- Never wrong money.
- Never silent failure.
- Evidence-first changes.
- Verified Odoo and Shopify behavior, not guesses.
- Wizard-first setup and merchant-readable recovery paths.

## Module Map

| Module | Purpose |
|---|---|
| `shopify_connector_pro` | Main Shopify connector addon. |
| `shopify_connector_pro_dashboard` | Dashboard/visibility companion addon. |
| `shopify_connector_pro_base` | Compatibility tombstone retained for upgrade compatibility, as confirmed in `docs/architecture/DECISIONS.md`. |
| `shopify_simulator` | Internal QA simulator only; must not be included in the public app-store package. |

## Governance and Current State

- Canonical agent operating rules: `AGENTS.md`.
- Current project state: `STATUS.md`.
- Audit evidence and findings: `AUDIT.md`.
- Evidence/backlog closure history: `FINALIZE.md`.
- Durable decisions: `docs/architecture/DECISIONS.md`.
- Environment/runtime notes: `docs/ops/ENVIRONMENT.md`.

Do not put long setup instructions in this README. Use `docs/ops/ENVIRONMENT.md` for runtime, branch, database-profile, and verification-command details.

## Documentation Tree Summary

| Path | Purpose |
|---|---|
| `docs/architecture/` | Architecture notes, decisions, and internal technical limitations. |
| `docs/archive/` | Preserved historical notes and Goal 0 manifest/audit context. |
| `docs/ops/` | Environment and runtime operating notes. |
| `docs/product/` | Product behavior, feature flags, ownership, commercial/internal product docs, and UX notes. |
| `docs/qa/` | QA plans, simulator guidance, staging plan, and reusable test patterns. |
| `docs/release/` | Packaging and app-store readiness scaffolds. |
| `addons/shopify_connector_pro/doc/` | Merchant-facing shipped addon documentation. |
| `addons/shopify_simulator/doc/` | Internal simulator documentation; not public package content. |

## Packaging Boundary

The simulator is internal QA tooling only. Public packaging rules live in `docs/release/PACKAGING_RULES.md`, including the rule that `shopify_simulator` must never be included in the public app-store package.
