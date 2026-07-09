# Task 006C — Pre-Implementation Review Checklist

> QA checklist for ChatGPT's strict review pass over the Task 006C
> sync-engine skeleton implementation-scope package. Use this to
> **accept / revise / reject**
> [`../07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md),
> [`../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md)
> (draft), and
> [`../07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`](../07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md).
> Findings feed the
> [Quality Feedback Loop](./quality-feedback-loop.md) per the standard
> [PR/review checklist](./pr-review-checklist.md). **This checklist itself
> authorizes nothing** — it is a review instrument, not a decision record.

- **Audit date:** 2026-07-08.
- **Audited artifacts:**
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md`,
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`,
  `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`,
  `docs/01-research/research-handoff.md` (compact top entry).
- **Audited against:** `origin/Shopify-connector` @ `a45e0a6` (PR #128
  merge commit); the accepted `DEC-025`; the accepted Task 001–005
  substrate as it exists in the repository at this commit.

---

## 1. Docs-only check

- [ ] Only `docs/**` files were created/modified by this session; no
      `addons/**` file, Python, XML, CSV, manifest, security, migration,
      Dockerfile, or CI/workflow file was touched.
- [ ] No addon file under `addons/shopify_connector_core/` was modified —
      it was read for planning only, per `git diff --stat` review.
- [ ] Only the five expected files changed:
      `docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md`,
      `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`,
      `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`,
      `docs/05-qa/task-006c-pre-implementation-review-checklist.md`,
      `docs/01-research/research-handoff.md` — plus, only if a genuine new
      technical-debt item was discovered,
      `docs/05-qa/technical-debt-register.md`.
- [ ] Branch/PR correct: branch is a `claude/task-006c-*` session branch
      (not `main`, not plain `dev`, not `dev/Shopify-connector`); PR
      targets `Shopify-connector`; PR is **draft**, not merged.

## 2. No implementation check

- [ ] The implementation-scope document's own status reads exactly
      "Proposed / Pending ChatGPT review" — not Accepted, not any
      implementation-authorizing wording.
- [ ] The final-prompt document's own status reads exactly "Draft only /
      Not issued" — and nowhere in the document does it say Claude may
      begin implementation now.
- [ ] The gate-opening proposal's own status reads exactly "Proposed only
      / Does not open the gate."
- [ ] None of the three documents contains language that could be read as
      self-authorizing (e.g. "this document authorizes," "implementation
      may now begin," "the gate is open").
- [ ] The final-prompt draft's own placeholder fields (concurrency
      mechanism, handler-registry seam shape, merge-commit SHA,
      retry-default constants, and the enqueue/dispatch file-split note)
      are still unresolved placeholders/open notes, not silently filled
      in with an assumed answer.
- [ ] The implementation-scope document's §C allowed-files list and the
      final-prompt's Allowed files list name the exact same files —
      cross-diff the two lists item by item (including
      `docs/01-research/research-handoff.md` and
      `docs/05-qa/technical-debt-register.md`, which belong on both).

## 3. No implementation authorization unless later accepted

- [ ] The gate-opening proposal's §5 explicitly states the five
      conditions (scope accepted, final prompt accepted, gate-opening
      proposal accepted, PR merged, next session separately issued) that
      must all be true before any Task 006C code is written — and that
      none of them is satisfied by this document.
- [ ] No document claims DEC-025's existing acceptance, or PR #128's
      merge, already authorizes Task 006C implementation — both
      correctly restate that DEC-025's acceptance explicitly did not
      create or authorize Task 006C.

## 4. Scope-creep search (mirrors the session's own red-team pass 1)

- [ ] No accidental authorization language survives in any of the three
      documents (grep-level spot check: "authorized," "may begin,"
      "gate is open," "implementation starts").
- [ ] No domain-sync implementation leakage: no product/customer/order/
      inventory/fulfillment field mapping, matching rule, or Shopify
      write logic appears anywhere in the proposed allowed-files list or
      acceptance criteria.
- [ ] No UI/setup-wizard/webhook-controller/OAuth leakage: the only XML
      artifact proposed anywhere is the single `ir.cron` data record; no
      view/menu/action/wizard/controller file is proposed; no OAuth/
      token-acquisition file is proposed.
- [ ] The webhook-topic-registration seam is explicitly named as
      **forbidden**, not merely deferred, with a stated reason (no
      consumer exists yet) — confirm this framing survived to the final
      draft.

## 5. Architecture consistency (mirrors red-team pass 2)

- [ ] Every proposed implementation slice in the scope document's §C/§E/
      §F maps back to a specific, cited DEC-025 responsibility or an
      already-accepted Task 001–005 substrate fact — none is invented
      without a citation.
- [ ] No rejected approach from
      [`rejected-approaches-log.md`](./rejected-approaches-log.md) is
      reintroduced (spot-check RA-004 — OCA `queue_job` remains
      reference-only, not adopted anywhere in these documents; RA-013 —
      no duplicated queue/job/log/binding abstraction is proposed).
- [ ] No final decision is made on any item DEC-025 itself left open —
      the job-claiming concurrency mechanism, the handler-registry seam
      shape (DEC-025's own third new open architecture question — whether
      the `_get_checks()` pattern literally extends to job-type dispatch),
      checkpoint/resume ownership, and the exact enqueue/dispatch file
      split are all labeled "candidate requiring ChatGPT approval," not
      asserted as decided.
- [ ] The one new `job_type` Selection value proposed for dispatcher
      self-tests (candidate `core_dispatch_selftest`) is framed as
      necessary-but-not-yet-final (name/scope open to the gate-opening
      act), not silently treated as already committed.
- [ ] The retry-scheduling constants and the cron-batch-size default are
      correctly labeled as adjustable implementation-planning defaults
      (per DEC-009's own acceptance note / SRR-01), not asserted as final,
      production-tuned values.

## 6. Preserved blockers (must all remain open/unresolved in every
## document)

- [ ] **VAL-B2** — still deferred / not passed.
- [ ] **MBQ-05** — still Partially routed / Open.
- [ ] **TD-002** — still Open.
- [ ] **Fulfillment API model** — still unresolved.
- [ ] **Product first-sync dedup thresholds** — still domain design, not
      decided.
- [ ] **Token acquisition for many unrelated customers** — still
      unresolved.
- [ ] **Lite/Full packaging** — still not finalized.
- [ ] **16-vs-17 `@idempotent` mutation-count discrepancy** — still open,
      still immaterial to this core-engine-level scope.
- [ ] **OCA `queue_job` worker-count wording discrepancy** — still open,
      still explicitly non-blocking.
- [ ] **Multi-server/Odoo.sh runtime concurrency proof** — still
      explicitly required before any future implementation may rely on a
      concurrency assumption named in the scope document.

## 7. No domain sync creep

- [ ] The forbidden-scope section (§D of the implementation-scope
      document) explicitly names product/customer/order/inventory/
      fulfillment domain logic, OAuth, UI, webhook controllers,
      accounting/refund/payout, and Lite/Full packaging as forbidden.
- [ ] No allowed-files entry in §C touches a domain-module directory or a
      domain-specific concrete binding model.

## 8. No UI/setup-wizard creep

- [ ] The only XML file proposed anywhere in the allowed-files lists is
      the single `ir.cron` data record; it carries no view, menu, or
      action.
- [ ] No wizard, controller, or client-side asset file is proposed.

## 9. No Shopify live-call creep

- [ ] Every test named in §H of the scope document and in the final
      prompt's Tests section is explicitly scoped to fake/no-op handlers,
      never the real `shopify.connector.api.client`.
- [ ] A dedicated "no live Shopify call" source-level test is named as
      mandatory in both the scope document and the final prompt.
- [ ] The acceptance criteria in the final prompt list "no live Shopify
      call anywhere in the diff" as a named, numbered acceptance
      criterion, not an implied assumption.

## 10. Tests completeness review

- [ ] §H of the scope document covers, at minimum: enqueue gating,
      enqueue idempotency, operation-scope duplicate prevention, execution
      claim guard, handler registry dispatch, missing-handler behavior,
      retryable-error retry scheduling, terminal-error routing
      (`failed_final`/`blocked_manual_review`), sanctioned-log-path
      enforcement, redaction, disconnect cancellation, execution-time
      store-state recheck, execution-time domain-enabled recheck, no-live-
      call proof, and no-domain-module-required proof.
- [ ] Every test named is specific enough to be written directly from
      this document without further design work (mirrors an existing
      named precedent test in the current suite, or a clearly stated new
      assertion).
- [ ] No test claims to prove real concurrent-worker or multi-server
      safety — every claim-guard test is explicitly scoped to code-level
      behavior under `TransactionCase`, with the runtime-proof requirement
      stated separately (§I).

## 11. Runtime validation review

- [ ] §I of the scope document lists, at minimum: cron drain runs live,
      concurrency behavior under multiple workers, disconnect during an
      active job, retry scheduling over real time, failed-job
      visibility/searchability, no token leakage in server logs, and
      savepoint/batch behavior at realistic volumes.
- [ ] None of §I's items is claimed as already passed — every item is
      phrased as a requirement for the *future* coding PR, not a result
      this docs-only session produced.
- [ ] The definition of done (§K) explicitly requires a runtime-validation
      plan to be attached to the future PR, and explicitly forbids
      marking it passed without genuine live evidence.

## 12. Rollback review

- [ ] §J of the scope document states the future PR is a single,
      self-contained, revertible unit with no destructive schema change.
- [ ] §J explicitly addresses preserving existing `job`/`job.log` data on
      rollback (no deletion, `ondelete='restrict'` unchanged).
- [ ] §J explicitly states any new field, if genuinely needed, must be
      nullable/optional — never a rename or removal of an existing
      column.

## 13. Architecture-review-log handling

- [ ] Confirm whether
      [`architecture-review-log.md`](./architecture-review-log.md) was
      modified by this session. **Expected: not modified** — this
      session's task instructions explicitly direct against modifying it
      unless the existing repo convention absolutely requires it, and
      flag the question in the final report if uncertain. Confirm the
      final report actually raises this explicitly for ChatGPT's own
      judgment (this package proposes no new AR row, since it proposes
      no new architecture decision — it is a planning/scoping package
      against an already-accepted architecture gate).

## 14. Overall review decision (record the outcome)

- [x] **Overall decision recorded: accepted as a planning/scope package
      only.** ChatGPT accepted PR #129's content (control-room review,
      GitHub review artifact/comment ID `4920363287`) on 2026-07-08 — the
      Task 006C implementation-scope document is now **Accepted by
      ChatGPT as planning/scope package** (acceptance date 2026-07-08),
      recorded via its own Acceptance note.
- [x] **Implementation remains unauthorized.** This acceptance patch, and
      the acceptance it records, does not authorize any code, does not
      create or modify any addon/Python/XML/CSV/security/manifest/
      migration/CI file, and does not open the Task 006C implementation
      gate.
- [x] **The final prompt remains `Draft only / Not issued`.**
      `task-006c-sync-engine-skeleton-final-prompt.md` was not modified by
      this acceptance patch — its status, and every one of its
      placeholders, are unchanged.
- [x] **The gate-opening proposal remains `Proposed only / Does not open
      the gate`.** `task-006c-sync-engine-gate-opening-proposal.md` was
      not modified by this acceptance patch — its status is unchanged,
      and it is not itself accepted by this patch.
- [x] **The execution-time claim/concurrency mechanism remains
      undecided** — still a candidate requiring ChatGPT approval in a
      future, separate gate-opening act (implementation-scope §F item 1).
- [x] **The handler-registry seam shape remains undecided** — still a
      candidate requiring ChatGPT approval in a future, separate
      gate-opening act (implementation-scope §F item 4).
- [x] **No revision was required.** This acceptance patch applies a clean
      "accepted as planning/scope package" outcome — no issue survived
      this patch requiring a further revision round.
- [x] **Next recommended session:** a future, separately-scoped,
      separately-authorized session — either (a) a Task 006C
      gate-opening-decision session, where ChatGPT's own act would fix
      the still-open candidates (concurrency mechanism, handler-registry
      shape, file split, retry defaults, cron batch size) and separately
      accept the gate-opening proposal and issue the final prompt, or
      (b) a distinct future Task 006D. **Neither is started, named as
      selected, or authorized by this checklist update** — this remains a
      control-room decision, not self-selected here. **This is not a
      coding session.**
