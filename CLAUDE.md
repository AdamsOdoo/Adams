# shopify_connector_pro — Mission and Standing Rules

## Mission
Ship the best Shopify connector on the Odoo App Store. "Best" means, in order:
1. RELIABILITY — sync never silently fails; every financial operation is
   idempotent, auditable, and degrades visibly. A merchant can trust it
   with their books.
2. USER-FRIENDLINESS — a non-technical merchant can connect, configure, and
   diagnose problems alone. Every error message says what happened and what
   to do. Onboarding in minutes, not hours.
3. PERFORMANCE — smooth at real-store scale (thousands of orders/products),
   no queue pileups, no timeout-prone screens.
4. COMPLETENESS — covers what e-commerce stores actually need day-to-day.
   New features serve v1.1+, not v1. v1 ships when 1–3 are excellent and
   current functionality is defect-free.

Definition of DONE for v1: full-coverage audit completed, all critical and
major findings fixed and verified fail-before/pass-after, COVERAGE.md shows
every enumerated surface covered and green on the strict DB, UX pass
completed, docs/listing accurate. Not in v1's definition of done: new
feature development.

## Project
Odoo 19 Enterprise third-party connector for Shopify (GraphQL Admin API
2026-01), deployed on Odoo.sh, preparing for Odoo App Store publication.
Path-1 auth only: merchants paste their own Admin API token. No OAuth.
Mature codebase, built over several months. Substantial hardening already
done: payment idempotency per backend/company, savepoints on draft-posting
branches, refund credit notes with tax/shipping balancing, graceful decrypt
degradation after DB clone, status-field indexes, refund-scan pruning,
count-based reconciliation. Do not re-litigate settled design decisions;
audit for defects, not preferences.

## Role and authority
- You operate under explicit human approval gates. Ahmed approves before any
  fix is implemented in shipped connector code and before any commit of it.
- Current phase: READ-ONLY AUDIT of shipped code unless a session explicitly
  grants write access. Exception: test code is always writable (see Testing
  mandate).
- Anything touching money movement, payment idempotency, credit notes,
  refunds, or tax computation ALWAYS requires explicit approval before
  editing, in every phase.

## Non-negotiable discipline rules
1. Confirm-before-fix: every finding must cite live-source evidence
   (file path + line + actual code) before any fix is proposed. No fixes
   from memory.
2. Verify Odoo 19 field/model/method names against the actual Odoo source
   tree, never from training memory. Same for Shopify 2026-01 API shapes —
   verify against the schema or live responses.
3. Tests: report literal counts naming their scope ("14 passed in
   test_refund_credit_notes") — never bare numbers or "all green".
4. Fail-before/pass-after: any bug fix must show a failing test through the
   production code path before the fix, and the same test passing after.
   Tests must exercise the real path, not a mock that bypasses it.
5. Financial entries must degrade VISIBLY, never silently. Any branch that
   swallows an error around accounting entries is a finding.
6. Smallest possible diff per change. One backlog item per session.

## Testing mandate
- You own verification end-to-end. Goal: every workflow, every button/action,
  every cron, every webhook path, every feature — exercised by automated
  tests, including negative scenarios: API failures, rate limits, malformed
  payloads, partial syncs, duplicate webhooks, token revocation mid-sync,
  network timeouts, concurrent operations, refunds exceeding captures,
  multi-currency edge cases, and anything else you judge realistic.
- A QA simulator exists in the repo for internal use (not shipped). Read it
  first. Use it, extend it, or build better tooling — your choice. If you
  extend or replace it, document why. Test infrastructure is yours to
  design; you do NOT need approval to create or modify test code, fixtures,
  or the simulator. Approval gates apply only to shipped connector code.
- Maintain COVERAGE.md: every workflow/button/scenario mapped to the test
  that exercises it. Unmapped = untested = not done. Buttons are enumerated
  from the XML views, not from memory.
- Tests must exercise the production code path. The simulator may fake
  Shopify; it must never fake our connector's logic. Mocking our own code
  to make a test pass is a defect.
- Negative tests must assert the *handling*, not just survival: the error
  is caught, the merchant-visible message is correct and actionable, the
  record lands in the right state, and nothing financial was half-written.
- When a test finds a bug: record it in AUDIT.md with the failing test as
  evidence, then stop for approval before fixing (rules 1–6 unchanged).

## Session protocol
- Start each session by reading STATUS.md, AUDIT.md, COVERAGE.md, and
  FINALIZE.md (those that exist). Do not re-survey the whole module; read
  only files relevant to the current item.
- End each session by updating STATUS.md (max ~30 lines: what was done,
  what's next, open questions).
- Record all findings in AUDIT.md with: ID, severity (critical/major/minor),
  file:line evidence, description, proposed fix (not implemented), status
  (open/approved/fixed/wontfix).
- Use subagents for broad scans so the main context stays lean.

## Environment
- Repo: AdamsOdoo/Adams. Review/merge branch: `review/full-audit`. Sessions
  develop and push on their harness-mandated working branch (this session:
  `claude/admiring-bell-e9g6qp`); Ahmed merges into `review/full-audit` via
  PR at each approved checkpoint. Never push to `review/full-audit` directly.
- Odoo.sh runtime access: NOT possible from this container — outbound port
  22 is blocked by the environment network policy (verified 2026-06-10).
  Runtime strategy is hybrid, approved by Ahmed:
  - LOCAL: an Odoo 19 Community runtime in this container (PostgreSQL 16,
    Python 3.11, odoo/odoo branch 19.0 cloned over HTTPS) is used for
    iteration, audit verification against core source, and
    fail-before/pass-after evidence. The connector's dependencies are all
    Community modules (product, sale_management, stock, contacts, mail,
    account), so it installs on Community.
  - ODOO.SH: every Phase 2 fix stays marked "pending Odoo.sh confirmation"
    in FINALIZE.md until its tests have also passed on the Odoo.sh build.
    Ahmed runs or relays those confirmation commands.
  - Anything verifiable only against Enterprise code is flagged
    "unverified — needs build check".
- Local setup (record exact verified commands here once the build is green;
  update this section without approval as facts are learned):
  - Odoo core: `/home/user/odoo` (odoo/odoo, branch 19.0, shallow clone).
  - Test command (template, to be confirmed):
    `python3 /home/user/odoo/odoo-bin -d <db> --addons-path=/home/user/odoo/addons,/home/user/Adams/addons -i shopify_connector_pro,shopify_simulator --test-tags <tags> --stop-after-init --no-http`
- Strict DB: its definition is not recorded anywhere; we derive it. For each
  financial bug in LEGACY_NOTES.md §1, determine what DB condition surfaced
  it (localization/chart of accounts, multi-currency, rounding settings,
  constraints, existing data vs fresh install) and configure local test DBs
  to reproduce those conditions. Document the resulting "strict profile"
  here. Known-relevant facts from Ahmed:
  - A UoM rounding fix in a sibling project was silently ignored on EXISTING
    databases and needed a post_init_hook — always test against
    upgraded/existing-data DBs, not only fresh installs.
  - Include a VAT-inclusive-pricing localization among the profiles
    (VAT-inclusive behavior is a known deferred area).
  - Conditions that cannot be replicated on Community are flagged for the
    Odoo.sh confirmation pass.
- Salvaged pre-reset knowledge (bug ledger, deferred features, known
  limitations, mandatory test accounting setup) lives in LEGACY_NOTES.md.
  If any surviving file contradicts this CLAUDE.md, this file wins and the
  contradiction gets flagged to Ahmed.
