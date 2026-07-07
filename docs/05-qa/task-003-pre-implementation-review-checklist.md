# Task 003 Pre-Implementation Review Checklist

> Gate checklist for reviewing (A) the AR-027 decision-closure package
> itself, and (B) the future Task 003 implementation PR before merge.
> Complements — does not replace —
> [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)
> (whose §A–§H gates apply to any code touching credentials/redaction,
> including Task 003's consumption of the Task 002 `redact()` utility)
> and [`pr-review-checklist.md`](./pr-review-checklist.md). A "No" on any
> **[Gate]** item blocks acceptance.

## Status

**Accepted by ChatGPT on 2026-07-07** (PR #98 F1 revision;
[`AR-027`](./architecture-review-log.md)) — decisions 1–3 as proposed,
Decision 4 with a scope-narrowing revision (the `payload_hash` nonce
applies to `core_test_connection` job creation only; `core_readiness_check`'s
identical latent exposure is tracked as `TD-001`, out of Task 003's
scope unless separately, explicitly authorized by name — see
[`task-003-decision-closure.md`](../07-implementation-plan/task-003-decision-closure.md)
§Acceptance). **Applies to the future Task 003 implementation PR once a
separate, explicit Task 003 gate-opening act is accepted** (not performed
by this document). **Does not authorize any code.** Docs-only; this
document itself creates no task and opens no gate. (Originally proposed
2026-07-07 in this same PR.)

## A. This package (the AR-027 decision-closure PR)

- [ ] **[Gate]** No code in this PR: docs-only diff; no addon file, no
      Python/XML/CSV/manifest/test/CI file created or modified; no API
      client, no test-connection mechanism, no external network call, no
      Shopify API call of any kind.
- [ ] **[Gate]** No gate opened by this PR: AR-027 is **Accepted (with
      F1 revision)**, but a decision-closure acceptance is not a
      gate-opening act; no gate-opening document, no final Task 003
      implementation prompt is included or implied to be authorized.
- [ ] **[Gate]** Every Shopify/Odoo platform statement either cites an
      already-accepted or already-written repo document (with that
      document's own original citation and access date preserved) or is
      explicitly labelled `[Requires external validation before
      implementation]` — no new external research is claimed to have
      been performed this session, and none was (network access was
      forbidden).
- [ ] **[Gate]** The four decisions are internally consistent across all
      package documents (decision closure §Acceptance, the amendment
      note on `task-003-api-client-test-connection-proposed.md`, this
      checklist, the AR-027 row, the handoff): `core_test_connection`
      **accepted**; `SHOP_INACTIVE`/402/423/403-fraudulent **accepted**
      mapped to `shopify_permission_scope_auth` with `credential_state`-
      gating and mandatory distinct plain-language reasons; job-log
      system-append method (not ACL widening) **accepted**; per-run
      UUID4 `payload_hash` nonce **accepted for `core_test_connection`
      only** — `core_readiness_check` explicitly excluded and tracked as
      `TD-001`.
- [ ] **[Gate]** Task 002 is not re-litigated anywhere in the package
      (compute-blank; `token_variant`; scope-snapshot placement — all
      AR-025/PR #97 settled).
- [ ] **[Gate]** No error class beyond the fixed 16 is introduced or
      accepted anywhere in the package; the `shopify_user_errors_validation`
      alternative is named, reasoned about, and now logged as rejected
      (`RA-024`) — not silently dropped.
- [ ] **[Gate]** Register discipline: `architecture-review-log.md`
      touched only for (a) the new AR-027 row (status: **Accepted with
      F1 revision**) and (b) a short amendment note on AR-019's existing
      row (job_type now three values) — no rewrite of AR-019's
      substance; `master-blueprint-open-questions.md` touched only for a
      short note on MBQ-44 (status unchanged: Partially resolved); no
      other MBQ/DEC/AR row touched; DEC-003–DEC-020,
      `docs/04-decisions/README.md`, and `defect-pattern-log.md`
      untouched; `rejected-approaches-log.md` gains exactly one new
      entry (`RA-024`, the `shopify_user_errors_validation` alternative)
      and no other; `technical-debt-register.md` gains exactly one new
      entry (`TD-001`, the `core_readiness_check` follow-up) and no
      other.
- [ ] **[Gate]** The `core_readiness_check` target-less
      idempotency-collision observation (Decision 4) is recorded as
      `TD-001` and cross-referenced from the decision-closure document,
      this checklist, the AR-027 row, and the handoff — and is **not**
      silently folded into Task 003's implementation scope anywhere in
      the package.
- [ ] **[Gate]** No dummy or real credential/token value appears anywhere
      in the package (none should be needed — this package does not
      touch credential material).

## B. The future Task 003 implementation PR

- [ ] **[Gate]** Gate evidence present: AR-027 accepted **and** a
      separate, explicit Task 003 gate-opening act — the first
      authorization of any outbound Shopify Admin API call — merged into
      `Shopify-connector` before the first implementation commit; both
      referenced by SHA in the PR body.
- [ ] **[Gate]** `job_type` decision applied correctly: `core_test_connection`
      (accepted) is added as a one-line addition to the base Selection in
      `shopify_connector_job.py` (not via `selection_add`).
- [ ] **[Gate]** Error-class mapping applied correctly: `SHOP_INACTIVE`,
      HTTP 402, HTTP 423, and HTTP 403-fraudulent each map to the
      accepted class (`shopify_permission_scope_auth`) with
      a **distinct, mandatory plain-language reason per condition** — not one
      generic message reused across all four; `credential_state` is
      flipped to `invalid` only for a genuine token-invalid signal
      (401/`ACCESS_DENIED`), never for a shop-account-state condition.
- [ ] **[Gate]** Job-log write path applied correctly: a single,
      internal, documented `sudo()`-wrapped write method exists, called
      only from other core/domain service code (never a directly
      user-invokable action); **no** `security/ir.model.access.csv` or
      `shopify_connector_security.xml` change exists unless ChatGPT
      explicitly chose ACL widening instead (in which case that choice
      and its own review must be documented in the PR body).
- [ ] **[Gate]** Exactly the sanctioned `sudo()` sites exist in the
      diff: the pre-existing Task 002 credential-read accessor (untouched)
      plus exactly one new job-log system-append call site — no other
      `sudo()` anywhere in the diff.
- [ ] **[Gate]** `payload_hash` nonce applied correctly: **`core_test_connection`
      job creation only** is created with a fresh per-run UUID4 (or
      equivalent unique-per-run generator) in `payload_hash`; no secret,
      token, or credential-derived value is ever a component; **a second
      test-connection run on the same store succeeds** with no
      `store_idempotency_key_uniq` collision (proven by test, not merely
      asserted).
- [ ] **[Gate]** `core_readiness_check` is **untouched** by this PR
      unless a separate, explicit gate act named it — no silent nonce
      fix, no silent behavior change to that job type; its tracked
      follow-up remains `TD-001`.
- [ ] **[Gate]** Fixed 16-class registry respected: no 17th `error_class`
      value added to `shopify_connector_job.py`.
- [ ] **[Gate]** Dual-path error normalization proven by a fixture
      matrix (transport-injection-seam fixtures, per
      `task-003-api-client-test-connection-proposed.md` §Tests required):
      success; `ACCESS_DENIED`; `THROTTLED` (labelled unofficial);
      `MAX_COST_EXCEEDED`; `INTERNAL_SERVER_ERROR` + `requestId`; HTTP
      401/402/423/429/500; timeout; malformed JSON; version fall-forward
      — each asserting the mapped class and the plain-language reason;
      unofficial/unconfirmed shapes are labelled as such in code/tests,
      never asserted as official behavior.
- [ ] **[Gate]** Read-only guarantee proven: no emittable request body
      contains `mutation`; no Odoo business model is written; the client
      shell exposes no mutation-capable method.
- [ ] **[Gate]** Redaction proven: every exception, `job.log` field, and
      store mirror passes through the Task 002 `redact()` utility; a
      dummy-token fixture proves the token is absent from every
      persisted surface and every raised exception's `str`/`args`.
- [ ] **[Gate]** Exact allowed files respected per the final Task 003
      implementation prompt (issued in a later, separate session); exact
      forbidden files respected: no view/menu/action/wizard XML; no
      controller/webhook/cron/data file; no credential-model change; no
      `job_log`/`location`/`binding_mixin`/`store_settings` model change
      beyond what the accepted decisions above authorize; no `adams_base`;
      no domain modules; no CI; no migrations.
- [ ] **[Gate]** No pacing/backpressure policy implemented (MBQ-51
      remains untouched); the throttle signal
      (`extensions.cost.throttleStatus`) is merely surfaced, never acted
      on automatically.
- [ ] **[Gate]** Manual validation performed and recorded honestly (per
      the Task 003 proposal's own §Manual validation and this
      repository's no-runtime caveat, consistent with the Task 001A/002
      precedent): a development store, never a production shop; the
      named open behavioral questions (actual HTTP status for an invalid
      token; actual `THROTTLED` body shape if reproducible; whether
      `shop`/`currentAppInstallation` needed any scope; actual
      missing-scope error shape) are answered empirically or explicitly
      reported as not reproducible — never asserted as confirmed without
      having been observed.
- [ ] **[Gate]** Rollback is clear: single-PR revert; store mirror fields
      simply stop refreshing (harmless stale data); no migration; no
      Shopify-side artifact exists to clean up (read-only guarantee).
- [ ] Handoff updated with the learning-loop section; PR left as draft
      for ChatGPT review; no domain task started.
