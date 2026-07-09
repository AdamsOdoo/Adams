# Task 006D — Gate-Opening Review Checklist

> QA checklist for ChatGPT's strict review pass over the Task 006D
> sync-engine skeleton **gate-opening decision package**. Use this to
> **accept / revise / reject**
> [`../07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`](../07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md)
> (revised), the new
> [`../07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-gate.md),
> and the revised
> [`../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md).
> Findings feed the
> [Quality Feedback Loop](./quality-feedback-loop.md) per the standard
> [PR/review checklist](./pr-review-checklist.md). **This checklist itself
> authorizes nothing** — it is a review instrument, not a decision record.

- **Audit date:** 2026-07-09.
- **Audited artifacts:**
  `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`
  (revised), `docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`
  (new), `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`
  (revised), `docs/05-qa/architecture-review-log.md` (AR row, if added),
  `docs/01-research/research-handoff.md` (compact top entry).
- **Audited against:** `origin/Shopify-connector` @
  `241871b70f8151d8b796dbb4fb7bcb69cc3b2db3` (PR #129 merge commit); the
  accepted `DEC-025`; the accepted (as a planning/scope package)
  `task-006c-sync-engine-skeleton-implementation-scope.md`; the accepted
  Task 001–005 substrate as it exists in the repository at this commit.

---

## 1. Docs-only check

- [ ] Only `docs/**` files were created/modified by this session; no
      `addons/**` file, Python, XML, CSV, manifest, security, migration,
      Dockerfile, or CI/workflow file was touched.
- [ ] No addon file under `addons/shopify_connector_core/` was
      modified — it was read for decision accuracy only, per `git diff
      --stat` review.
- [ ] Only the allowed files for this session changed:
      `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`,
      `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`,
      `docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`,
      `docs/05-qa/task-006d-gate-opening-review-checklist.md`,
      `docs/05-qa/architecture-review-log.md`,
      `docs/01-research/research-handoff.md`.
- [ ] `docs/07-implementation-plan/task-006c-sync-engine-skeleton-
      implementation-scope.md` was **not** modified this session (it is
      explicitly forbidden for Task 006D).
- [ ] Branch/PR correct: branch is a `claude/task-006d-*` session branch
      (not `main`, not plain `dev`, not `dev/Shopify-connector`); PR
      targets `Shopify-connector`; PR is **draft**, not merged.

## 2. No implementation check

- [ ] No addon/Python/XML/CSV/manifest/security/migration/CI/webhook/
      controller/view/wizard/OAuth file was created or modified anywhere
      in the diff.
- [ ] No domain module directory
      (`shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment`)
      was created.
- [ ] No document in this package contains language implying
      implementation may start now (grep-level spot check: "gate is
      open," "implementation authorized," "Claude may begin," "issued,"
      "implementation starts").
- [ ] Every document states implementation starts only after ChatGPT
      accepts, this PR merges, and ChatGPT separately pastes the final
      prompt in a **new** Claude Code session — not automatically, not as
      a continuation of this session.

## 3. Final-prompt status check

- [ ] The final prompt's own status reads exactly "Final draft / Pending
      gate acceptance / Not issued" — not Draft-only-unresolved, not
      Issued, not Accepted-and-authorized.
- [ ] The final prompt's `<CONCURRENCY_MECHANISM_CHATGPT_APPROVED>`,
      `<HANDLER_REGISTRY_SHAPE_CHATGPT_APPROVED>`, and
      `<RETRY_DEFAULTS_CHATGPT_APPROVED>` placeholders are replaced with
      concrete proposed values matching the gate-opening proposal's §6
      exactly (word-for-word or in clearly equivalent restatement) — not
      silently left blank, and not silently diverging from §6.
- [ ] The final prompt's merge-commit-SHA placeholder
      (`<TASK_006D_GATE_MERGE_COMMIT_SHA>`) is still unresolved — this PR
      has not merged, so it cannot be known yet.
- [ ] The final prompt still states, explicitly, that it is not issued
      and must not be pasted/run until the gate document and the
      gate-opening proposal are both accepted, this PR merges, and
      ChatGPT separately pastes the finalized prompt in chat.
- [ ] The final prompt's allowed files, forbidden files, tests, rollback
      notes, and hard constraints are otherwise unchanged in substance
      from the accepted implementation-scope document's own §C/§D/§H/§I/
      §J.

## 4. Gate document status check

- [ ] `task-006c-sync-engine-skeleton-gate.md` exists and its own status
      reads exactly "Proposed / Pending ChatGPT review" — not Accepted,
      not "Accepted gate-opening act" (contrast the already-merged Task
      002/003 gate precedents, which do carry that latter wording only
      because they were written *after* acceptance).
- [ ] The gate document explicitly states it does not open the gate by
      existing, being drafted, or being reviewed — only by being
      accepted **and** merged.
- [ ] The gate document explicitly states implementation still requires
      a separate, later ChatGPT act (pasting the final prompt in a new
      session) even after this document merges.
- [ ] The gate document does not say implementation starts
      automatically upon its own merge.

## 5. Open choices resolved (proposed) check

- [ ] All six open choices (execution-time claim/concurrency mechanism;
      handler-registry seam shape; retry-default constants; enqueue/
      dispatch file split; cron batch-size/interval default; core
      diagnostic `job_type` name/scope) carry a **concrete proposed
      decision** in the gate-opening proposal's §6 — none is left as a
      bare, unresolved candidate.
- [ ] Every one of the six is labelled **[Recommendation]**, not
      **[Decision]** — none is asserted as ChatGPT-accepted before
      ChatGPT actually accepts this package.
- [ ] The six proposed decisions are internally consistent with DEC-025's
      own explicit non-decisions (no job-claiming mechanism selected, no
      handler-registry shape selected, no retry-count/backoff constant
      finalized) — each proposed decision is framed as *this session's
      recommendation for ChatGPT's acceptance*, not as already settled by
      DEC-025 itself.

## 6. Open-choice consistency across documents

- [ ] The gate-opening proposal §6, the final prompt's resolved
      placeholder text, the gate document's §C summary table, and this
      checklist's own §5 all name the **identical** six proposed values —
      no conflicting default anywhere (e.g. a different batch size, a
      different retry-attempt count, or a different diagnostic job_type
      name in one document versus another).
- [ ] `research-handoff.md`'s compact top entry (if it restates any of
      the six) matches the same values.

## 7. No domain sync creep

- [ ] No product/customer/order/inventory/fulfillment field mapping,
      matching rule, or Shopify write logic appears anywhere in any of
      the four documents' allowed-files lists, scope sections, or
      acceptance criteria.
- [ ] The `core_dispatch_selftest` diagnostic `job_type` is explicitly
      scoped as core/diagnostic-only, never a template for a future
      domain `job_type`, in every document that mentions it.

## 8. No UI/setup-wizard creep

- [ ] The only XML artifact proposed anywhere is the single `ir.cron`
      data record; no view/menu/action/wizard file is proposed anywhere
      in this package.

## 9. No webhook controller creep

- [ ] No webhook HTTP controller/receiver file is proposed anywhere; the
      webhook-topic-registration seam remains named as forbidden/deferred
      (not built even as a placeholder), consistent with the accepted
      implementation-scope document's §D.

## 10. No OAuth/token acquisition creep

- [ ] No OAuth or token-acquisition file, field, or mechanism is
      proposed anywhere; MBQ-05 is restated as unresolved in every
      document that touches it.

## 11. No live Shopify call creep

- [ ] Every test named in every document (gate-opening proposal §3/§8,
      gate document §H/§I, final prompt's Tests section) is explicitly
      scoped to fake/no-op handlers, never the real
      `shopify.connector.api.client`.
- [ ] A dedicated "no live Shopify call" source-level test is named as
      mandatory in the gate document's §H and the final prompt's Tests
      section.
- [ ] No document claims a live Shopify connection has been made,
      attempted, or is planned as part of this docs-only session.

## 12. Allowed-files completeness

- [ ] The gate document's §F, the final prompt's "Allowed files (exact)"
      list, and the (unmodified, forbidden-to-touch) implementation-scope
      document's §C name the same exact file set — cross-diffed item by
      item, including `docs/01-research/research-handoff.md` and
      `docs/05-qa/technical-debt-register.md`, which belong on both lists
      conditionally.
- [ ] No allowed-files entry touches a domain-module directory or a
      domain-specific concrete binding model.

## 13. Forbidden-files completeness

- [ ] The gate document's §G and the final prompt's "Forbidden files
      (exact)" list both name: any view/menu/action/wizard/controller/
      XML beyond the one cron file; any webhook receiver; any domain
      module file; any OAuth/token-acquisition file; any CI/workflow/
      Dockerfile/requirements file; any migration file; any security/ACL
      file; the seven read-only substrate files
      (`shopify_connector_store.py`,
      `shopify_connector_store_credential.py`,
      `shopify_connector_store_settings.py`,
      `shopify_connector_location.py`,
      `shopify_connector_binding_mixin.py`,
      `shopify_connector_api_client.py`, `tools/redaction.py`); `main`;
      plain `dev`; `dev/Shopify-connector`.

## 14. Tests completeness

- [ ] The gate document's §H and the final prompt's Tests section cover,
      at minimum, the same fifteen behaviors the accepted implementation-
      scope document's §H names: enqueue gating, enqueue idempotency,
      operation-scope duplicate prevention, execution claim guard,
      handler registry dispatch, missing-handler behavior, retryable-
      error retry scheduling, terminal-error routing, sanctioned-log-path
      enforcement, redaction, disconnect cancellation, execution-time
      store-state recheck, execution-time domain-enabled recheck, no-
      live-call proof, and no-domain-module-required proof.
- [ ] No test claims to prove real concurrent-worker or multi-server
      safety — every claim-guard test is explicitly scoped to code-level
      behavior under `TransactionCase`.

## 15. Runtime validation honesty

- [ ] Every document listing runtime-validation items (gate-opening
      proposal §8, gate document §I) explicitly states none of them is
      claimed as already passed by this docs-only session.
- [ ] No document claims `try_lock_for_update()` (Decision A) is proven
      safe under real concurrent workers or a multi-server deployment —
      every mention explicitly defers that claim to required, separate,
      future live Odoo.sh (and, where relevant, multi-server) proof.
- [ ] No document claims the SRR-03 disconnect/in-flight-job race is
      closed — every mention says "narrows, does not close."

## 16. Rollback completeness

- [ ] The gate document's §M and the final prompt's rollback notes both
      state: single-PR revert; no destructive schema change; existing
      `job`/`job.log` rows preserved on rollback
      (`ondelete='restrict'`); any new field, if genuinely needed, must
      be nullable/optional, never a rename or removal of an existing
      column.

## 17. Open blockers preserved

- [ ] **VAL-B2** — still deferred / not passed, in every document that
      restates it.
- [ ] **MBQ-05** — still Partially routed / Open.
- [ ] **TD-002** — still Open.
- [ ] **Fulfillment API model** — still unresolved.
- [ ] **Product first-sync dedup thresholds** — still domain design, not
      decided.
- [ ] **Token acquisition for many unrelated customers** — still
      unresolved.
- [ ] **Lite/Full packaging** — still not finalized.
- [ ] **16-vs-17 `@idempotent` mutation-count discrepancy** — still
      open, still immaterial to this core-engine-level scope.
- [ ] **OCA `queue_job` worker-count wording discrepancy** — still open,
      still explicitly non-blocking.
- [ ] **Checkpoint/resume ownership** — still undecided; no
      checkpoint/resume file, field, or model is proposed anywhere.
- [ ] **Multi-server/Odoo.sh runtime concurrency proof** — still
      explicitly required before any future implementation may rely on a
      concurrency assumption named in this package.

## 18. Architecture-review-log handling

- [ ] Confirm whether
      [`architecture-review-log.md`](./architecture-review-log.md) was
      modified by this session, and whether a new AR row was added.
      **Expected, per this repo's own convention** (confirmed this
      session by inspecting the AR-026/AR-029 "Gate-Opening Note" rows
      for the Task 002/Task 003 implementation gates): a gate-opening act
      of this kind **is** recorded as its own AR row — so a new row
      (AR-031, immediately following AR-030) should exist, with **Status:
      Proposed**, not Accepted, mirroring how AR-026/AR-029 were first
      drafted as part of their own gate-opening PRs before ChatGPT's
      acceptance.
- [ ] If an AR row was added, confirm it is not marked Accepted by this
      session — only ChatGPT's own review can move it to Accepted.
- [ ] If the session's final report instead explains a decision **not**
      to add an AR row, confirm that explanation directly addresses the
      AR-026/AR-029 precedent rather than silently diverging from it.

## 19. Overall review decision (ChatGPT to complete)

- [ ] **Overall decision:** _______ (Accept as proposed / Accept with
      revisions / Revise / Reject)
- [ ] **If revisions are required, list them:** _______
- [ ] **Confirm before accepting:** none of VAL-B2, MBQ-05, TD-002, the
      fulfillment API model, product first-sync dedup, token
      acquisition, Lite/Full packaging, checkpoint/resume ownership, or
      the multi-server runtime concurrency proof requirement is silently
      resolved by accepting this package.
- [ ] **Confirm before accepting:** accepting this package does **not**,
      by itself, authorize implementation or open the Task 006C gate —
      the gate opens only once the gate document is merged, and
      implementation starts only once the final prompt is separately
      pasted in a new session, per `task-006c-sync-engine-skeleton-
      gate.md` §K.
- [ ] **Next recommended session (ChatGPT to confirm or override):**
      after this package merges, ChatGPT pastes
      [`task-006c-sync-engine-skeleton-final-prompt.md`](../07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md)
      verbatim (merge-commit SHA filled in) into a new Claude Code
      session as the Task 006C implementation session. **Not started,
      named as selected, or authorized by this checklist.**
