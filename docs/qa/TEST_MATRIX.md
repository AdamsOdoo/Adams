# Test Matrix

## Purpose

Plan test coverage by category before implementation and verification. This is a scaffold; do not infer completed coverage from this file.

## Rule

Tests must exercise the production connector path, not mock connector logic. The simulator may fake Shopify, but it must not fake our connector behavior.

## Test Categories

- Happy path
- Negative path
- Accounting
- Security
- Webhooks
- API throttling
- Concurrency
- Multi-company
- Multi-store
- UI/buttons
- Simulator
- Packaging

## Matrix Schema

| Category | Scenario | Production path exercised | Test file::method | Profile | Status | Evidence |
|---|---|---|---|---|---|---|

No rows are populated in Goal 0.
