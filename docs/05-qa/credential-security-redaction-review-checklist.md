# Credential Security and Redaction Review Checklist

> Gate checklist for reviewing any credential-, connection-,
> test-connection-, or API-client-related work (documentation now; code
> when the relevant tasks are authorized). Derived from the accepted
> MBQ-04 / AR-022 posture, DEC-004, the AR-023 UI/UX honesty rules, and
> [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md).
> A "No" on any **[Gate]** item blocks acceptance of the document or PR
> under review. Complements — does not replace —
> [`pr-review-checklist.md`](./pr-review-checklist.md) and
> [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md).

## Status

**Accepted by ChatGPT on 2026-07-06** (PR #92 acceptance patch;
[`AR-024`](./architecture-review-log.md)) **as the checklist for
future credential-, connection-, test-connection-, and
API-client-related reviews.** **Applies once the relevant implementation
gate(s) are opened** (Task 002+ reviews). **Does not authorize any
code.** Docs-only; this document itself creates no task and opens no
gate.

## A. Honest security claims

- [ ] **[Gate]** No encryption claim anywhere — code, docstrings,
      comments, copy, docs: no "encrypted", "encryption at rest",
      "bank-level", no padlock-implying-encryption iconography. Storage
      is described only as masking + access restriction (MBQ-04 posture).
- [ ] **[Gate]** No Odoo.sh/Odoo Online/on-premise encryption-coverage
      claim (hosting scope unconfirmed per AR-022) and no claim that
      `password=True`/the password widget encrypts (display masking
      only) or that `ir.config_parameter` is secure secret storage.
- [ ] **[Gate]** Residual exposure (sudo/DB/backup readability) is stated
      where storage is documented, never glossed over.

## B. No read-back / masking

- [ ] **[Gate]** No token read-back on any surface for any role,
      including Admin: no view/field/report/export renders the stored
      value; the entry widget (when UI exists) is write-only, masked,
      and never re-populated from storage.
- [ ] **[Gate]** No reveal/preview toggle; no full or partial value
      display (including "last 4" — unverified-historical Shopify
      behavior, and display-inviting regardless).
- [ ] Token *status* (present / last verified) is the only
      credential-derived content rendered, and it is honest (real
      timestamps, no implied-live freshness).

## C. Token never appears in outputs

- [ ] **[Gate]** Token never appears in Python logs at any level
      (including DEBUG), in any environment.
- [ ] **[Gate]** Token never appears in chatter (and no `mail.thread` is
      added to credential-bearing models without extending the redaction
      rule first).
- [ ] **[Gate]** Token never appears in job logs — `message`,
      `technical_detail`, `payload_snapshot` — nor in
      `credential_last_failure_reason` or any store mirror.
- [ ] **[Gate]** Token never appears in exception messages/args raised by
      the credential service, API client, test connection, readiness, or
      rollback/error-handling paths (constraint violations included).
- [ ] **[Gate]** Token never appears in request/response technical
      detail: raw request headers are never logged
      (`X-Shopify-Access-Token` is a header); response excerpts are
      redacted before persistence.

## D. Redaction utility

- [ ] **[Gate]** One shared redaction utility is used at **both**
      enforcement layers — at source (client/service outputs) and at sink
      (the job-log write choke point) — not ad-hoc per-call-site string
      handling.
- [ ] **[Gate]** Key patterns cover at least: `access_token`, `token`,
      `secret`, `password`, `authorization`, `x-shopify-access-token`,
      `api_key`, `client_secret`, `refresh_token`, `hmac`; value patterns
      cover `shpat_`/`shprt_` prefixes plus exact-match scrub of the
      stored value.
- [ ] **[Gate]** Tests prove redaction: key hits, value-pattern hits,
      exact-value scrub, nested structures, idempotence, and
      end-to-end "dummy token absent from every persisted surface"
      assertions. All test tokens are dummies; no real secret appears in
      any test, fixture, or doc.

## E. Access control and sudo

- [ ] **[Gate]** Access groups are correct: credential model ACL is
      Admin-only (no row for auditor/operator/reviewer; no unlink for
      anyone); field-level `groups=` on the secret as an independent
      second layer; tests/manual evidence prove the denial matrix.
- [ ] **[Gate]** Admin can enter/replace/clear the token;
      Operator/Reviewer/Auditor provably cannot see or touch the token
      or the credential model (not even `fields_get`).
- [ ] **[Gate]** Every `sudo()` in credential/client/lifecycle code is
      individually justified in writing, minimal in scope, never crosses
      store/record-rule boundaries (DEC-004), and never leaks the value
      outward; only the two named sanctioned elevations (the client's
      internal credential read; the core job-log system-append writer,
      per ChatGPT's write-path resolution) are permitted — any other
      `sudo()` in the diff is a review failure.

## F. Lifecycle behavior

- [ ] **[Gate]** Disconnected store keeps history: disconnect clears the
      credential value but preserves the store, credential row, settings,
      bindings, jobs, logs, audit, and mapping/error history (MBQ-08);
      nothing is unlinked.
- [ ] **[Gate]** Reconnect re-runs readiness before business sync
      resumes; reconnect is explicit and audited, never automatic.
- [ ] Credential entry/replacement/clear/verification events are audited
      (who/when/outcome) without ever recording the value.

## G. Test connection and readiness

- [ ] **[Gate]** Test connection is read-only: pure GraphQL query (no
      mutation surface exists in the shell), no webhook setup, no
      business data written on either side; runs as a
      `setup_readiness_check` job.
- [ ] **[Gate]** A failed essential readiness check can never yield
      `connected`/pass; warning-tier checks never block.
- [ ] Failure copy is business-friendly: named cause + suggested fix +
      owner; never a raw HTTP code, `extensions.code` token, or stack
      trace as primary copy (RA-016).
- [ ] **[Gate]** Technical details are expandable but redacted: raw
      status/error codes/`requestId`/cost data live only behind the
      technical-detail expand, post-redaction.
- [ ] No invented platform behavior: officially-undocumented shapes
      (THROTTLED body, invalid-token HTTP status, missing-scope shape)
      are labelled unofficial in fixtures/comments and carry empirical
      verification steps — never asserted as official.

## H. Gate and scope discipline

- [ ] **[Gate]** No UI gate opened accidentally: zero views, menus,
      actions, or wizard artifacts in any foundation task; the UI
      implementation gate remains a separate, explicit ChatGPT act.
- [ ] **[Gate]** The task under review changed only its allowed files;
      no webhook/controller/cron/domain/`adams_base` content; DEC files,
      `docs/04-decisions/README.md`, `defect-pattern-log.md`, and
      `master-blueprint-open-questions.md` untouched unless the task
      explicitly authorizes an acceptance patch.
- [ ] Each foundation task starts only after its own explicit ChatGPT
      gate act and final §9 prompt; no task consumes an unmerged
      predecessor.
