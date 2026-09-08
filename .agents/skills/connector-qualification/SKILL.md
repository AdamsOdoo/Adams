---
name: connector-qualification
description: Triage connector failures and qualify exact-source install, migration, concurrency and live journeys with honest release evidence and economical reruns.
---

Read root AGENTS.md and handoff. docs/v2/09-test-observability-release-blueprint.md owns gates; blueprint 16 routes sequence and historical scenarios.

Identify source SHA/tree, dirty state, pinned Odoo commit, Python/PostgreSQL, build and fixture before interpreting results. Read raw logs. Separate setup cascades from assertions actually executed; hundreds of fixture failures are not hundreds of source defects.

Cheap checkpoint: `python -m unittest discover -s tools/tests -p 'test_*.py'`; add touched syntax/XML/manifest, static/dependency/change-size policy, GraphQL and packaging checks as affected. Inspect runner usage before optional flags. Evidence drift after code changes must not redefine the accepted baseline.

Native runner: tools/run_connector_suite.sh; CI wiring: .github/workflows/connector-tests.yml. Focused diagnosis cannot replace fresh/warm/migration, Lite/Full, W2-over-old-core and nonstandard campaigns. Preserve executed/skipped/failed counts and migration-script evidence. Concurrency requires independent database connections/barriers; mocks are not proof. Opt-in process-death tests skipped remain pending.

Live work is dev-only and exact-store-only. Verify identity/build, use secure credentials and bounded synthetic fixtures, and record cleanup/compensation. Server-to-server business readback precedes native UI UAT. Never repeat an uncertain write for a green screenshot.

At freeze, qualify the immutable source/package and link U1–U14, security/load/rollback/browser/human usability evidence. Preserve sequential canary minima. Changes reopen affected proof and downstream gates; docs equivalence needs an explicit record. Readiness does not grant production/public promotion authority.

Return a truthful scoped verdict: assured for the named next gate, corrections required, core gaps, or blocked by named infrastructure. Update the canonical handoff with exact first next action, not a second status ledger.
