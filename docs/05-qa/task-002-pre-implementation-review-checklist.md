# Task 002 Pre-Implementation Review Checklist

> Gate checklist for reviewing (A) the AR-025 decision/gate-preparation
> package itself, and (B) the future Task 002 implementation PR before
> merge. Complements — does not replace —
> [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)
> (whose §A–§H gates all apply to the Task 002 PR) and
> [`pr-review-checklist.md`](./pr-review-checklist.md). A "No" on any
> **[Gate]** item blocks acceptance.

## Status

**Accepted by ChatGPT on 2026-07-07** (PR #94 acceptance patch;
[`AR-025`](./architecture-review-log.md)). **Applies to the future Task
002 implementation PR once the Task 002 gate is opened** by the
separate, explicit ChatGPT gate-opening act. **Does not authorize any
code.** Docs-only; this document itself creates no task and opens no
gate. (Originally proposed 2026-07-06 as part of the AR-025 package.)

## A. This package (the AR-025 decision/gate-prep PR)

- [ ] **[Gate]** No code in this PR: docs-only diff; no addon file, no
      Python/XML/CSV/manifest/test/CI file created or modified; no
      credential/token/secret field, model, or implementation of any
      kind.
- [ ] **[Gate]** No gate opened by this PR: AR-025 is **Proposed**, the
      gate-opening document is a *proposal*, and the final prompt is
      marked **not issued, not authorized**.
- [ ] **[Gate]** No encryption claims introduced anywhere in the
      package: no "encrypted"/"encryption at rest"; no claim that
      `password=True` encrypts; no claim that `ir.config_parameter` is
      secure secret storage; no Odoo.sh/Odoo Online/on-premise
      encryption-coverage claim; residual exposure stated wherever
      storage is described.
- [ ] **[Gate]** Every Shopify/Odoo platform statement cites an
      official source (shopify.dev / help.shopify.com linked from it /
      odoo.com 19.0 docs / odoo/odoo 19.0 source) with access date and
      status, or is explicitly labelled an Open question.
- [ ] **[Gate]** The three decisions are internally consistent across
      all four package documents (decision closure, final prompt, gate
      proposal, this checklist): compute-blank **rejected** for Task
      002; `token_variant` exactly `[('offline_custom_app', …)]`; scope
      snapshot on `shopify.connector.store`.
- [ ] **[Gate]** Task 003-only decisions are *not* resolved anywhere in
      the package (job-type value; `SHOP_INACTIVE`/402/423/403 mapping;
      job-log write path; `payload_hash` nonce) — each appears only as
      explicitly deferred.
- [ ] **[Gate]** Register discipline: MBQ-04 not marked resolved;
      MBQ-05 not marked resolved; MBQ-44 status unchanged; all register
      edits are explicitly *proposed pending AR-025*; no unrelated MBQ
      row touched; DEC-003–DEC-020, `docs/04-decisions/README.md`, and
      `defect-pattern-log.md` untouched.
- [ ] **[Gate]** All credential/token examples are dummy values (e.g.
      `shpat_DUMMYDUMMYDUMMY…`); no real secret appears anywhere in the
      package.
- [ ] **[Gate]** The final prompt is implementation-ready: copy-paste
      complete (repo, branch, baseline, gate scope, hard rules,
      exhaustive allowed/forbidden files, exact model/fields/ACL/
      service/redaction contracts, enumerated tests, manual validation,
      rollback, acceptance criteria, definition of done, PR
      requirements, response format), and executable immediately after
      the gate act with zero further decisions left to the implementer.

## B. The future Task 002 implementation PR

- [ ] **[Gate]** Gate evidence present: AR-025 accepted **and** the
      separate gate-opening act merged into `Shopify-connector` before
      the first implementation commit; both referenced by SHA in the PR
      body.
- [ ] **[Gate]** Compute-blank decision applied correctly:
      `access_token` is a plain stored Char (`copy=False`, Admin
      `groups=`), **no** compute/inverse, **no** raw SQL, **no**
      hand-managed column, **no** companion stored field; the honest
      residual is stated in the model docstring.
- [ ] **[Gate]** `token_variant` decision applied correctly: exactly
      one Selection value `offline_custom_app` (default); **no**
      `client_id`/`client_secret`/token-cache/expiry/refresh field; the
      deliberate absence is documented.
- [ ] **[Gate]** Scope-snapshot decision applied correctly:
      `granted_scopes` + `granted_scopes_checked_at` on
      `shopify.connector.store` (not on the credential model), readonly,
      with **no writer** in Task 002.
- [ ] **[Gate]** Exact allowed files respected: the diff touches only
      the 13 files listed in the final prompt's Allowed files, and every
      listed change matches its stated scope (store model: six fields
      only; CSV: one appended row only; manifest: version only).
- [ ] **[Gate]** Exact forbidden files respected: no XML file of any
      kind; no security-XML change; no job/job_log/location/binding/
      settings model change; no `adams_base`; no CI/workflow/
      requirements; no migration; no doc beyond the handoff.
- [ ] **[Gate]** No UI/API/test-connection scope: zero views/menus/
      actions/wizards; zero HTTP/`requests`/`urllib`/GraphQL content;
      zero webhook/controller/cron; zero domain logic; zero `job.log`
      writes; no external network call possible from the module.
- [ ] **[Gate]** The final prompt was followed as issued
      (implementation-ready check): model/fields/ACL/service/redaction
      contracts match the prompt **exactly**; any deviation was
      pre-approved by ChatGPT in writing, not improvised.
- [ ] **[Gate]** Tests are sufficient: all 21 enumerated cases exist,
      including the 4-role denial matrix, the independent field-`groups`
      layer test, redaction idempotence/nesting/exact-scrub, the
      **token-leak sweep** (dummy token absent from every persisted
      surface except the credential column), the no-job-log assertion,
      and the single-`sudo()` guard; all tokens dummies; execution
      status (run vs. written-only per the runtime caveat) stated
      honestly in the PR body.
- [ ] **[Gate]** Exactly one `sudo()` in the diff (inside
      `_get_access_token`, with written justification); write paths run
      as the calling user; no raw SQL anywhere.
- [ ] **[Gate]** Rollback is clear: single-PR revert; drop semantics
      and re-enterability stated; no migration needed; nothing depends
      on the change.
- [ ] **[Gate]** No Task 003 scope smuggled in: no API-client shell, no
      test-connection method, no error-class mapping code, no job-type
      addition, no `payload_hash` nonce change, no job-log write path.
- [ ] **[Gate]** No encryption claims and no real token anywhere in
      code, docstrings, comments, tests, fixtures, PR body, or handoff;
      `credential-security-redaction-review-checklist.md` §A–§F gates
      re-checked and passing.
- [ ] Handoff updated with the learning-loop section; PR left as draft
      for ChatGPT review; no second task started.
