# Feature Flags

## Purpose

Track features that may be staged, hidden, or enabled by scope while protecting core reliability, financial correctness, and merchant UX.

## Core vs Advanced Feature Rule

Core merchant flows required for a correct Shopify Connector Pro Ultimate Edition v1 should not be hidden merely to avoid defining them. Advanced or optional capabilities may be staged behind feature flags when doing so preserves reliability, financial correctness, and release safety.

## Feature Flag Table Schema

| Feature | Flag name | Scope: global/backend/company/user | Default | Gated menus/views | Gated crons | Gated webhooks | Gated models | Tests required | Status |
|---|---|---|---|---|---|---|---|---|---|

No rows are populated in Goal 0.
