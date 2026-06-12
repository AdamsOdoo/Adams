# AGENTS.md — Shopify Connector Pro Ultimate Edition Operating System

## Project Mission

Build and validate **Shopify Connector Pro Ultimate Edition**, an Odoo 19 + Shopify connector, first for the Adams database and then as a durable public third-party Odoo App Store product.

The connector must be premium/enterprise-positioned while remaining practical for small and medium merchants and Odoo partners.

## Ordered Product Pillars

1. **Reliability** — syncs must be idempotent, auditable, observable, and recoverable.
2. **Financial correctness / never wrong money** — accounting outcomes must be correct before they become posted facts.
3. **Merchant-friendly UX** — setup, errors, and recovery must be understandable to non-technical merchants.
4. **Performance** — syncs must remain responsive and bounded at realistic store scale.
5. **Completeness** — feature breadth matters after reliability, money correctness, UX, and performance are protected.

## Non-Negotiable Rules

### No Silent Failure

Failures must degrade visibly. Any sync, webhook, accounting, payout, reconciliation, fulfillment, or configuration failure must leave actionable evidence for the merchant/admin through the appropriate product surface.

### Evidence First

Before proposing or implementing a fix, cite live repository evidence: file paths, line numbers, current behavior, and the exact command or inspection that supports the finding.

### Source Verification

Verify claims against current project files and authoritative runtime/API sources. Do not rely on memory when a local file, Odoo source tree, Shopify schema/response, or documented project decision can be checked.

### Odoo / Shopify No-Guessing Rule

Do not guess model names, fields, method signatures, API payload shapes, webhook shapes, money semantics, or rate-limit behavior. Verify them from source, schema, logs, or a documented decision before using them.

### Testing and Fail-Before / Pass-After

- Bug fixes require a failing test or reproducible failure through the production connector path before the fix, then the same path passing after the fix.
- Tests must exercise production connector logic. The simulator may fake Shopify, but it must not fake connector behavior.
- Report literal test scope and counts; do not summarize with bare “green” language.
- If a goal is documentation-only, run documentation/governance verification instead of unrelated full suites unless a package/runtime reference requires more.

## Project Standing Rules

### Standing Approval

- Work proceeds under standing approval when it stays inside the active goal, follows the non-negotiable rules, and remains reversible.
- Do not use Ahmed / project owner as a relay for routine reversible implementation choices.
- Escalate only when the escalation policy requires it.

### Money-Path Consequence Statements

- Every money-path commit must include a 3–5 sentence plain-language consequence statement.
- It must explain business/accounting impact, reversibility, user-visible behavior, and verification evidence.
- Record it in `FINALIZE.md` or the active goal evidence log.
- Money-path areas include invoices, payments, credit notes, refunds, payouts, taxes, currencies, gift cards, reconciliation, and anything that can affect posted accounting documents.

### Green Build Standing Rule

- At checkpoint/merge boundaries, Odoo.sh build logs must have zero errors/warnings attributable to project modules.
- Warnings must be fixed by removing their cause.
- Do not suppress, downgrade, filter, or hide warnings just to make logs clean.
- If a warning is from Odoo core or an external dependency, classify it with evidence instead of hiding it.
- Odoo.sh verification remains a human relay touchpoint when the agent environment cannot access Odoo.sh directly.

### v1 Definition of Done

- v1 is not done until all critical and major findings are fixed or explicitly accepted, verified with evidence, and no silent failure / wrong-money risk remains in core workflows.
- Full VAT-inclusive / tax-included pricing support is in v1 scope, per Ahmed’s 2026-06-11 decision.
- The total-check guard remains permanent product behavior after VAT-inclusive support lands; see DEC-011 and DEC-012.
- `COVERAGE.md` must map shipped workflows, buttons, crons, webhooks, and negative paths to tests before v1 completion.
- User-facing docs and listing claims must match implemented and tested behavior.
- Odoo.sh install, upgrade, and build logs must be clean for project-attributable issues.

### Milestones

- M1 Client-Ready: v1 core behavior verified for the Adams pilot database, install/upgrade path known, setup/config documented, and zero-knowledge onboarding guide available.
- M2 User-Validated: human/user test executed, issues fixed or accepted, and Adams/client deployment is safe.
- M3 Store-Ready: public packaging, app-store docs, screenshots, exclusions, licensing, and submission checklist verified.

## Agent Team Roles

- **Orchestrator / Delivery Lead** — owns goal boundaries, sequencing, evidence, commits, and closure.
- **Odoo Technical Architect** — verifies Odoo models, fields, ORM flows, module packaging, and upgrade behavior.
- **Shopify Technical Architect** — verifies Shopify API contracts, webhooks, throttling, and idempotency expectations.
- **Accounting & Reconciliation Specialist** — protects invoice, credit note, payout, tax, currency, and reconciliation correctness.
- **UI/UX Product Designer** — protects wizard-first setup, merchant-readable errors, and recovery flows.
- **QA / Simulator / Test Engineer** — owns coverage mapping, simulator usage, negative paths, and fail-before/pass-after evidence.
- **Security & Privacy Reviewer** — verifies token handling, secrets, access rules, webhooks, privacy, and least privilege.
- **Adversarial Reviewer** — challenges assumptions, scans for silent failure, wrong-money risk, and scope creep.

## Goal-Loop Workflow

Every goal should move through this loop:

1. **Research** — inspect current files, decisions, tests, and authoritative sources.
2. **Confirm** — restate constraints, open questions, and evidence.
3. **Design** — propose the smallest safe plan inside the goal boundary.
4. **Implement** — make minimal changes only in the allowed scope.
5. **Test** — run the required verification and capture exact outputs.
6. **Review** — run fresh-context adversarial review before goal closure or checkpoint merge; check scope, evidence, silent failure, wrong-money risk, packaging risk, and regression risk.
7. **Document** — update the appropriate source of truth and evidence log.
8. **Close or repeat** — close if verified; otherwise repeat the loop with the next smallest correction.

## Escalation Policy

Stop and escalate instead of improvising when:

- A documentation move requires changing a manifest, script, import path, test command, module packaging file, or production path.
- A current repo document contradicts a project-owner decision and the prompt does not resolve it.
- Audit history would need to be deleted.
- Production connector logic would need to change outside the current goal.
- A total mismatch posting policy decision is required before Goal 1 verifies current guard behavior.
- A feature must be removed from v1.
- A public pricing, licensing, or app-store positioning decision is required.
- Any irreversible and high-stakes business decision is needed.

## Self-Improvement / Learning Rules

- Capture repeated mistakes as durable rules in the appropriate doc, not as one-off chat memory.
- Prefer small reusable checklists over ad hoc process notes.
- When verification exposes an environment or harness limitation, document the limitation and the safe workaround.
- Keep governance docs lean; archive historical noise instead of copying it forward.

## Durable Decision Rules

- Durable product and architecture decisions belong in `docs/architecture/DECISIONS.md`.
- Decisions should include rationale, date, owner, status, and reversibility.
- Favor reversible choices unless a non-reversible choice is explicitly approved by Ahmed / project owner.
- Preserve open decisions as open; do not resolve them by implication.

## Source-of-Truth Map

- `AGENTS.md` — canonical operating rules for agents.
- `STATUS.md` — current project state and next focus.
- `AUDIT.md` — historical audit evidence and findings.
- `FINALIZE.md` — evidence/backlog closure history.
- `docs/architecture/DECISIONS.md` — durable ADR/product decisions.
- `docs/ops/ENVIRONMENT.md` — runtime, branch, DB profile, and command notes.
- `COVERAGE.md` — coverage scaffold/map; population is a later goal.
- `docs/product/BEHAVIOR_CONTRACT.md` — behavior contract scaffold; Goal 1 fills deltas/decisions.
- `docs/qa/TEST_MATRIX.md` — QA planning scaffold.
- `docs/release/PACKAGING_RULES.md` — packaging boundaries, including simulator exclusion.

## Session Start Protocol

1. Confirm the current branch and working tree.
2. Read `AGENTS.md`, `STATUS.md`, `AUDIT.md`, `FINALIZE.md`, and any goal-specific docs.
3. Confirm the goal boundary and hard constraints.
4. Inspect only files relevant to the goal unless evidence requires more.
5. If documentation moves are planned, search references before moving.
6. Do not push or merge directly to `review/full-audit`.

## Session End Protocol

1. Review the changed file list for scope violations.
2. Run the goal-required verification commands.
3. Commit in small labeled commits.
4. Update `STATUS.md` with a short current-state handoff, normally ≤30 lines.
5. Keep `STATUS.md` focused on what changed, what is verified, what is pending, and next action.
6. Record exact verification outcomes in the final report.
7. Provide rollback instructions.
8. Recommend ready/not ready for Claude review.

## Changelog

| Date | Change |
|---|---|
| 2026-06-12 | Created Goal 0 operating-system file for future Claude/Codex sessions. |
| 2026-06-12 | Restored project-specific standing rules from pre-Goal-0 governance: standing approval, money-path consequence statements, green-build rule, v1 DONE including VAT-in-v1 scope, M1–M3 milestones, STATUS handoff, and fresh-context adversarial review. |
