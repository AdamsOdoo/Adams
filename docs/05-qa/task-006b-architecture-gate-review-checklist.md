# Task 006B — Architecture Gate Review Checklist

> QA checklist for ChatGPT's strict review pass over the proposed sync-engine
> architecture gate. Use this to **accept / revise / reject**
> [`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md)
> and its companion decision record
> [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md).
> Findings feed the [Quality Feedback Loop](./quality-feedback-loop.md) per
> the standard [PR/review checklist](./pr-review-checklist.md).

- **Audit date:** 2026-07-08.
- **Audited artifacts:** `docs/03-architecture/sync-engine-architecture-gate.md`,
  `docs/04-decisions/DEC-025-task-006-sync-engine-gate.md`,
  `docs/01-research/research-handoff.md` (compact top entry).
- **Audited against:** `origin/Shopify-connector` @
  `3207791412ebedbc83eceaf70592df8c8df0d97a` (PR #127 merge commit).

---

## 1. Scope and governance

- [ ] **Docs-only.** Only `docs/**` files were created/modified; no
      `addons/**` file, Python, XML, CSV, manifest, security, migration,
      Dockerfile, or CI/workflow file was touched.
- [ ] **No implementation authorized.** The gate document and DEC-025 both
      carry an explicit "No implementation authorized" section; neither
      claims or implies a coding-gate opening.
- [ ] **No implementation-scope file created.**
      `docs/07-implementation-plan/task-006-sync-engine-implementation-scope.md`
      and
      `docs/07-implementation-plan/task-006c-sync-engine-implementation-scope.md`
      do not exist and were not created by this session.
- [ ] **No Task 006C drafting.** The gate document names Task 006C only as a
      possible *future* candidate (§J), never drafts its scope.
- [ ] **Only the four allowed files changed:**
      `docs/03-architecture/sync-engine-architecture-gate.md`,
      `docs/04-decisions/DEC-025-task-006-sync-engine-gate.md`,
      `docs/05-qa/task-006b-architecture-gate-review-checklist.md`,
      `docs/01-research/research-handoff.md`.
- [ ] **Branch/PR correct.** Branch is a `claude/task-006b-*` session branch
      (not `main`, not plain `dev`, not `dev/Shopify-connector`); PR targets
      `Shopify-connector`; PR is **draft**, not merged.

## 2. DEC-025 status

- [x] **DEC-025's `Status` field reads "Accepted by ChatGPT," with
      acceptance date 2026-07-08** — the acceptance-patch update applied by
      this revision, per control-room review of PR #128 after its governance
      revisions.
- [x] **DEC-025 carries an explicit Acceptance note** stating: this accepts
      the architecture gate only; it does not authorize implementation; no
      Task 006C or implementation-scope document is created or authorized;
      every open item and runtime-validation requirement remains preserved,
      unchanged by acceptance.
- [x] DEC-025 explicitly states that acceptance of the record does not, by
      itself, authorize implementation — restated in the top blockquote,
      the Acceptance note, and the "No implementation authorized" section.

## 3. Task 006A coverage

- [ ] All five Task 006A shard documents are cited with specifics, not just
      linked: source inventory, source notes, evidence map, open-questions
      register, risk register, Odoo/repo substrate notes, queue/idempotency/
      retry/backoff notes, competitor-pattern notes, and the completeness
      audit's recommendation (Recommendation A — proceed to Task 006B
      without a Shopify-shard backfill).
- [ ] The absence of `docs/01-research/sync-engine-shopify-source-notes.md`
      is explicitly acknowledged as covered-by-synthesis (per the accepted
      PR #127 audit), not silently ignored or treated as a gap.
- [ ] No high-confidence Task 006A finding is contradicted (spot-check: the
      job/log/store/credential/readiness substrate facts; the `ir.cron`/
      savepoint/locking facts; the Shopify GraphQL throttle-body and cursor-
      durability facts).
- [ ] **The two pre-006A baseline sources —
      `docs/01-research/shopify-official-api-notes.md` and
      `docs/01-research/odoo-official-architecture-notes.md` — were directly
      read in full**, not only consulted via the Task 006A synthesis layer;
      the gate document's "Revision note" states this and confirms whether
      direct inspection required any material architecture-content change
      (it did not, per this revision — see the note for the specific facts
      checked).

## 4. Claim classification discipline

- [ ] Facts, inferences, recommendations, and open questions are labeled
      throughout, per `CLAUDE.md` §8 — no competitor claim presented as
      fact; no inference presented as a decision.
- [ ] Every "three-shard-corroborated" or "requires runtime proof" framing
      from Task 006A is preserved with that same epistemic status, not
      upgraded to a settled fact.
- [ ] No retry-count/backoff constant, mutation count, or other numeric
      value is asserted as final where the source material flags it as an
      implementation-planning default or a disputed count.

## 5. Core vs. domain responsibility separation

- [ ] The gate clearly separates core-engine responsibilities from
      product/customer/sale-order/inventory/fulfillment/future-accounting
      responsibilities (§I table), consistent with DEC-008/DEC-010/
      DEC-011/DEC-013 §C.8 — no responsibility is assigned to core that
      those decisions place with a domain module, or vice versa.
- [ ] No new domain sync logic, field mapping, or matching rule is
      introduced beyond what DEC-013/014/015/016 already state at blueprint
      level.
- [ ] No final Odoo model/field name is introduced that is not either
      already-accepted (Task 001–005 / AR-019) or explicitly marked
      candidate/architecture-level.

## 6. Preserved blockers (must all remain open/unresolved in this gate)

- [ ] **VAL-B2** — still deferred / not passed.
- [ ] **MBQ-05** — still Partially routed / Open (token acquisition for many
      unrelated customers not decided).
- [ ] **TD-002** — still Open.
- [ ] **Fulfillment API model** — still unresolved (legacy `Fulfillment` vs.
      `FulfillmentOrder`).
- [ ] **Product first-sync dedup thresholds** — still domain design, not
      decided here.
- [ ] **Lite/Full packaging** — still not finalized; treated as product
      strategy, not an architecture decision.
- [ ] **16-vs-17 `@idempotent` mutation count** — still an open, unresolved
      discrepancy.
- [ ] **OCA `queue_job` worker-count wording** (`--workers > 0` vs. `> 1`) —
      still open, still explicitly non-blocking.
- [ ] **Multi-server/Odoo.sh concurrency proof** — still explicitly required
      before implementation relies on any concurrency assumption named in
      the gate (job-claiming, disconnect race, savepoint batching).

## 7. No premature adoption

- [ ] **OCA `queue_job` is not adopted** anywhere in the gate or DEC-025;
      RA-004 is cited as unchanged and binding.
- [ ] No rejected approach from `rejected-approaches-log.md` is silently
      re-proposed without meeting its stated revisit condition (spot-check:
      RA-004, RA-013, RA-014 through RA-017).
- [ ] No job-claiming concurrency mechanism (`SKIP LOCKED` /
      `lock_for_update()` / advisory locks) is selected as final — all are
      presented as candidates with an explicit open-question status.
- [ ] No checkpoint/resume core-vs-domain ownership decision is made.

## 8. Handoff and repo hygiene

- [ ] `docs/01-research/research-handoff.md` carries a new, compact top
      entry (not a 100+ line section) covering this session, per
      `../06-prompts/session-handoff-template.md`.
- [ ] The handoff entry's Learning feedback loop fields are all present
      (new issues / repeated patterns / rules updated / rejected approaches
      / technical debt / architecture concerns — "None" where applicable).
- [x] **The corresponding `architecture-review-log.md` row exists and is
      updated** — `AR-030`'s Review decision now reads "Accepted by ChatGPT
      (2026-07-08)" and its Status reads "Accepted," mirroring DEC-025's own
      acceptance exactly.
- [x] **`AR-030`'s Follow-up action column states implementation is still
      not authorized** — future Task 006C implementation-scope drafting may
      be proposed in a separate session, but no implementation is authorized
      by `AR-030`/DEC-025 itself.
- [x] **DEC-025's `Status` and `AR-030`'s Status are consistent with each
      other** — both read "Accepted" as of this acceptance patch, applied
      together in the same revision.

## 9. Overall review decision (record the outcome)

- [x] **Overall decision recorded: accepted.** ChatGPT accepted PR #128
      (the architecture gate, DEC-025, and this checklist) on 2026-07-08,
      after the prior revisions' governance fixes (direct baseline-file
      inspection, the `AR-030` addition, and the stale-wording consistency
      fix) — this acceptance patch applies that outcome to the repository.
- [x] No issue survived to this acceptance patch requiring a new
      `/docs/05-qa` log entry — the two prior governance gaps were already
      fixed and logged in earlier revisions' handoff entries; no new issue
      is found by this patch.
- [x] **DEC-025's `Status` field is updated from "Proposed / Pending
      ChatGPT review" to "Accepted by ChatGPT," acceptance date 2026-07-08**
      — mirroring the DEC-005/DEC-009/DEC-013 acceptance pattern. **This
      acceptance does not by itself authorize implementation** — restated
      explicitly in DEC-025's Acceptance note and "No implementation
      authorized" section.
- [x] **`AR-030`'s row in `architecture-review-log.md` is moved from
      "Proposed for ChatGPT review" to "Accepted"** — applied in the same
      acceptance patch that updates DEC-025's `Status`, per DEC-025's
      "Architecture-review-log note."
- [ ] **Next recommended session:** a separately-scoped, separately-
      authorized Task 006C implementation-scope drafting session — **named
      as the recommended next step, but not started, drafted, or authorized
      by this acceptance patch.** No implementation-scope file exists;
      no code, addon, or domain work is authorized by this acceptance.
