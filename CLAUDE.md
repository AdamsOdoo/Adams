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
completed, docs/listing accurate. SCOPE DECISION (Ahmed, 2026-06-11): full
VAT-inclusive (tax-included pricing) support is IN v1 — no longer deferred.
The AUD-001 branch map in AUDIT.md is its spec; the workstream covers
AUD-001, AUD-015, AUD-016, AUD-018 plus the permanent total-check guard
(computed invoice totals vs Shopify totalPriceSet, visible degradation on
mismatch — stays in the product after full support lands). Otherwise not in
v1's definition of done: new feature development.

MILESTONES (Ahmed, 2026-06-11):
- M1 CLIENT-READY: v1 DONE as defined above, PLUS deployment-readiness for
  a specific client database (install/upgrade path verified, config
  documented, zero-knowledge onboarding guide written).
- M2 USER-VALIDATED: human test executed, findings fixed, retested.
  Client deployment happens at M2.
- M3 STORE-READY: packaging, listing, docs, demo data, submission
  requirements verified against current Odoo App Store rules. Store
  submission happens at M3.

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

## Role and authority (GOVERNANCE CHANGE — Ahmed, 2026-06-11, supersedes
## the original approval-gate model from item 3a onward)
- STANDING APPROVAL: plan, edit shipped code, and commit without per-item
  approval for all FINALIZE.md items and all findings from the remaining
  tiers, PROVIDED every change satisfies rules 1-6. The discipline rules
  are the gate. A change that cannot meet them does not ship, period.
- SELF-VERIFICATION REPLACES HUMAN REVIEW: after each item, record the
  evidence trail in FINALIZE.md (failing test ref, passing counts both
  strict profiles, full-suite counts). At each tier checkpoint, run a
  fresh adversarial review of recent diffs via fresh-context subagents
  (hunting rule violations, regressions, silent degradations) before
  proceeding.
- DECISIONS: genuine business decisions are decided here under the
  standing intent — maximize merchant-friendliness and reliability for
  real e-commerce stores; never wrong money, never silent failure; prefer
  reversible choices. Every such decision goes in docs/architecture/
  DECISIONS.md with rationale and a reversibility note. Escalate to Ahmed
  only when BOTH irreversible AND high-stakes, as a plain-language
  consequence statement.
- THREE HUMAN TOUCHPOINTS (the only ones):
  1. Odoo.sh confirmation runs — batch the commands; Ahmed relays.
     (To be eliminated once direct SSH is enabled — see STATUS.md.)
  2. Money-path changes (payments, refunds, credit notes, taxes,
     reconciliation): before committing each, Ahmed receives a 3-5
     sentence plain-language consequence statement and replies go/no-go.
     The only remaining diff-level gate.
  3. Final human user test before client deployment: a zero-knowledge
     test script executed by Ahmed or the client against a dev store.
- EFFICIENCY MANDATE: the how is owned here — subagents, tooling, harness
  improvements welcome if rules 1-6 stay intact. One item per session,
  items as large as safety allows. Periodically re-sync the local Odoo
  core checkout and re-run the suite to catch upstream drift.
- Test code remains always writable (see Testing mandate).

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
- GREEN BUILD standing rule (Ahmed, 2026-06-11): at each tier checkpoint,
  pull the latest Odoo.sh build log and confirm zero errors/warnings
  attributable to our modules — any new warning is a finding. Warnings are
  cleared by removing their cause, never by suppressing/downgrading/
  filtering log output. Part of v1 DONE (see FINALIZE.md GREEN BUILD item).

## Environment
- Repo: AdamsOdoo/Adams. Review/merge branch: `review/full-audit`. Sessions
  develop and push on their harness-mandated working branch (this session:
  `claude/admiring-bell-e9g6qp`); Ahmed merges into `review/full-audit` via
  PR at each approved checkpoint. Never push to `review/full-audit` directly.
- Odoo.sh runtime access: NOT possible from ANY session container —
  Claude Code cloud environments sit behind an HTTP/HTTPS-only egress
  proxy, so raw TCP/SSH (port 22) is unsupported under every network
  policy including "Full" (platform constraint, confirmed against
  code.claude.com docs + empirically 2026-06-11: port 22 times out to
  all hosts, 443 to the same hosts connects). No environment setting
  fixes this; do not re-test SSH. Odoo.sh checks go through Ahmed
  (touchpoint 1). Runtime strategy is hybrid, approved by Ahmed:
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
- Local setup (re-VERIFIED 2026-06-11 from scratch; baselines reproduced
  exactly). CONTAINERS ARE EPHEMERAL: the Odoo checkout, pip deps, PG
  role and all DB profiles are LOST between sessions — rebuild at
  session start (~20 min: clone + pip + 2 installs + chart). Until an
  environment setup script exists (recommended to Ahmed), the recipe is:
  - Odoo core: `/home/user/odoo` (odoo/odoo branch 19.0, shallow clone;
    2026-06-11 tip b4c7247f — suite-equivalent to the 2026-06-10
    baseline commit 07a333c8). PostgreSQL 16 local cluster
    (`pg_ctlcluster 16 main start`), DB superuser `root`
    (`su - postgres -c "createuser -s root && createdb root"`).
  - Python dep quirks vs upstream requirements.txt (Python 3.11 here):
    `psycopg2-binary` instead of psycopg2; unpinned `rjsmin`/`vobject`
    (pinned versions fail to build); `docopt-ng` + `num2words --no-deps`;
    system `cryptography 41.0.7` kept with `urllib3==2.0.7` and
    `pyopenssl==24.1.0` (the Noble combo — Jammy's urllib3 1.26.5 is
    incompatible with cryptography ≥39); `beautifulsoup4` added; `cffi`
    added (missing in the image — without it odoo-bin dies at startup
    with ModuleNotFoundError `_cffi_backend` via OpenSSL import);
    EXCLUDE `python-ldap` and `ofxparse` (no build headers; unused by
    our dependency set — and a single failing wheel aborts the whole
    `pip install -r`).
  - Run test DBs ONE AT A TIME: `--test-tags` spawns an HTTP server even
    with `--no-http` (port collision), and two parallel suite runs can
    OOM-kill PostgreSQL (observed 2026-06-11).
  - Test command (verified):
    `python3 /home/user/odoo/odoo-bin -d <db> --addons-path=/home/user/odoo/addons,/home/user/Adams/addons -u shopify_connector_pro,shopify_simulator,shopify_connector_pro_dashboard --test-tags /shopify_connector_pro,/shopify_simulator,/shopify_connector_pro_dashboard --stop-after-init --no-http --log-level=info`
  - DB profiles (rebuilt every session; steps below):
    1. `adams_test_fresh` — fresh install, NO chart of accounts. Exposes
       env-sensitivity: 4 tests error (account.tax without tax_group_id —
       AUDIT.md ENV-1). Baseline 2026-06-10: 0 failed, 4 errors of 532.
    2. `adams_strict1` — install the 3 modules (NOTE 2026-06-11:
       `l10n_generic_coa` is NOT a module in Odoo 19 — the loader ignores
       it with "invalid module names"; the chart comes entirely from the
       next step), then apply the chart via odoo shell
       (`env['account.chart.template'].try_loading('generic_coa', env.company)`
       + `env.cr.commit()`), then run tests via `-u` (exercises the
       upgraded/existing-data path, not fresh-install-only). Baseline
       2026-06-10: 0 failed, 0 errors of 532; reproduced 2026-06-11
       after rebuild: 0 failed, 0 errors of 552.
    3. `adams_strict_vat` — clone of adams_strict1 with
       `env.company.account_price_include = 'tax_included'` (verified field,
       odoo/addons/account/models/company.py:282), EUR activated,
       base.group_multi_currency implied for internal users, AND (added
       2026-06-11 per Ahmed) an explicit EUR exchange rate
       (res.currency.rate, 1 USD = 0.92 EUR) so tax-included AND
       multi-currency conditions hold SIMULTANEOUSLY — the
       AUD-019/020/001 compound-bug surface. Build:
       `createdb -T adams_strict1 adams_strict_vat`, then odoo shell for
       the three settings + rate + `env.cr.commit()`. Baseline
       2026-06-10: 1 failed, 0 errors of 532 — caught AUD-001
       (VAT-inclusive order import totals); reproduced 2026-06-11 after
       rebuild: 2 failed, 0 errors of 552 (the known AUD-001 pair, both
       clear at 3e).
- Strict DB: its definition is not recorded anywhere; we derive it. For each
  financial bug in LEGACY_NOTES.md §1, determine what DB condition surfaced
  it (localization/chart of accounts, multi-currency, rounding settings,
  constraints, existing data vs fresh install) and configure local test DBs
  to reproduce those conditions. Derivation status: chart-presence,
  upgraded-DB, and VAT-inclusive+multi-currency conditions are reproduced by
  profiles 1–3 above; per-bug derivation for the remaining LEGACY_NOTES.md §1
  financial bugs continues during Tier 1/4, extending the profile list here.
  Known-relevant facts from Ahmed:
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
