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

**Proposed for ChatGPT review.** Not yet accepted. Applies to (A) this
package now, and (B) the future Task 003 implementation PR only once a
separate, explicit Task 003 gate-opening act is accepted (not performed
by this document — see
[`task-003-decision-closure.md`](../07-implementation-plan/task-003-decision-closure.md)
§Status). **Does not authorize any code.** Docs-only; this document
itself creates no task and opens no gate.

## A. This package (the AR-027 decision-closure PR)

- [ ] **[Gate]** No code in this PR: docs-only diff; no addon file, no
      Python/XML/CSV/manifest/test/CI file created or modified; no API
      client, no test-connection mechanism, no external network call, no
      Shopify API call of any kind.
- [ ] **[Gate]** No gate opened by this PR: AR-027 is **Proposed**; no
      gate-opening document, no final Task 003 implementation prompt is
      included or implied to be authorized.
- [ ] **[Gate]** Every Shopify/Odoo platform statement either cites an
      already-accepted or already-written repo document (with that
      document's own original citation and access date preserved) or is
      explicitly labelled `[Requires external validation before
      implementation]` — no new external research is claimed to have
      been performed this session, and none was (network access was
      forbidden).
- [ ] **[Gate]** The four decisions are internally consistent across all
      three package documents (decision closure, the amendment note on
      `task-003-api-client-test-connection-proposed.md`, this checklist):
      `core_test_connection` recommended; `SHOP_INACTIVE`/402/423/
      403-fraudulent recommended mapped to `shopify_permission_scope_auth`
      with `credential_state`-gating; job-log system-append method (not
      ACL widening) recommended; per-run UUID4 `payload_hash` nonce
      recommended.
- [ ] **[Gate]** Task 002 is not re-litigated anywhere in the package
      (compute-blank; `token_variant`; scope-snapshot placement — all
      AR-025/PR #97 settled).
- [ ] **[Gate]** No error class beyond the fixed 16 is introduced or
      proposed anywhere in the package; the `shopify_user_errors_validation`
      alternative is named and reasoned about, not silently dropped.
- [ ] **[Gate]** Register discipline: no edit to
      `master-blueprint-open-questions.md` or
      `architecture-review-log.md`'s existing AR-019/AR-024/AR-025/AR-026
      rows beyond adding the new AR-027 row itself in **Proposed** status;
      MBQ-44 status unchanged; no unrelated MBQ row touched;
      DEC-003–DEC-020, `docs/04-decisions/README.md`, and
      `defect-pattern-log.md` untouched; `rejected-approaches-log.md`
      untouched (the `shopify_user_errors_validation` alternative is
      logged there only upon acceptance, per the ADR template
      convention).
- [ ] **[Gate]** The newly-surfaced `core_readiness_check` target-less
      idempotency-collision observation (Decision 4) is recorded
      somewhere reviewable (this checklist, the decision-closure
      document, and the handoff) and is not silently dropped — even
      though fixing it is not itself authorized by this package.
- [ ] **[Gate]** No dummy or real credential/token value appears anywhere
      in the package (none should be needed — this package does not
      touch credential material).

## B. The future Task 003 implementation PR

- [ ] **[Gate]** Gate evidence present: AR-027 accepted **and** a
      separate, explicit Task 003 gate-opening act — the first
      authorization of any outbound Shopify Admin API call — merged into
      `Shopify-connector` before the first implementation commit; both
      referenced by SHA in the PR body.
- [ ] **[Gate]** `job_type` decision applied correctly: if
      `core_test_connection` was accepted, it is added as a one-line
      addition to the base Selection in `shopify_connector_job.py` (not
      via `selection_add`); if rejected, that file is untouched for this
      concern and `core_readiness_check` is reused.
- [ ] **[Gate]** Error-class mapping applied correctly: `SHOP_INACTIVE`,
      HTTP 402, HTTP 423, and HTTP 403-fraudulent each map to the
      accepted class (recommended: `shopify_permission_scope_auth`) with
      a **distinct plain-language reason per condition** — not one
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
- [ ] **[Gate]** `payload_hash` nonce applied correctly: every
      target-less job (`core_test_connection` and, if fixed in this PR
      or a named companion PR, `core_readiness_check`) is created with a
      fresh per-run UUID4 (or equivalent unique-per-run generator) in
      `payload_hash`; no secret, token, or credential-derived value is
      ever a component; **a second test-connection run on the same store
      succeeds** with no `store_idempotency_key_uniq` collision (proven
      by test, not merely asserted).
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
