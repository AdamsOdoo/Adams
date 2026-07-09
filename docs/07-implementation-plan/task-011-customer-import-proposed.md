# Task 011 — Customer Import and Matching (Proposed Scope Refresh)

> **Documentation-only session refresh.** This document does not replace or
> rewrite [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
> (the original Task 011 scope draft, prepared alongside the MVP domain
> implementation-slicing sequence) — that document remains the accurate,
> unedited historical record of Task 011's originally-proposed objective,
> approach, and exclusions, and this document cites it throughout rather than
> duplicating its content. This document instead records **what has changed
> since that draft was written**, confirms Task 010's closure, and states
> the current, current-session readiness posture for Task 011. **Proposed
> only. Not authorized. Does not open any implementation gate.**

## 1. Status

**Proposed only. Not authorized.** Prepared after PR #138 (Task 010
implementation) and PR #139 (Task 010 post-merge closure docs) both merged
into `Shopify-connector`, in the same session as
[`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
[`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md),
and
[`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md).

## 2. What changed since the original draft

The original [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
was written before Task 010 merged and before several open questions it
flagged were resolved. This session confirms the following updates, none of
which reopen or contradict that document's own scope/objective/approach:

1. **Task 010 is now closed and runtime-green.** PR #138 ("Task 010: Shopify
   product import and variant binding") merged into `Shopify-connector`,
   merge commit `1f478032d8581a949fa7820847e5c1ab419586b4`. Post-merge Odoo.sh
   runtime evidence: `shopify_connector_core` 187 tests,
   `shopify_connector_product` 61 tests, **0 failed, 0 error(s) of 220
   tests** (`../05-qa/task-010-product-import-validation-results.md` §K).
   PR #139 (Task 010 post-merge closure docs) subsequently merged, commit
   `297f398da96d11d1f8f9e25a9d15570a66aed80a` — this session's own branch
   sits exactly at that commit (confirmed via `git merge-base`, no drift).
   This satisfies MBQ-55's own row instruction that a domain naming/schema
   pass proceed "before the product/customer/order slice starts" for the
   **product** portion; the **customer** portion is what this session's
   companion naming proposal addresses.
2. **MBQ-29 (default-customer fallback) is now Resolved, not merely
   partially resolved.** The original draft's §"Fallback partner rules"
   flagged an unreconciled discrepancy: DEC-014 itself only "partially
   resolved" MBQ-29 (direction accepted, granularity open), while a
   separate UI/UX research note described MBQ-29 as "Resolved via AR-020,"
   and asked a future session to confirm the register's current state
   directly. This session did: reading
   [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)'s
   MBQ-29 row directly confirms the **Final MBQ closure pass** (ChatGPT via
   AR-020 / `final-mbq-closure-plan.md`, 2026-07-05) superseded DEC-014's
   partial resolution: **"one single, clearly-flagged fallback partner per
   store... is the Phase 1 answer; per-order anonymous identity is
   explicitly non-MVP."** Only the exact partner naming remains task-spec
   detail. This is a genuine narrowing of what Task 011's future final
   implementation prompt still needs to decide — see §4 below.
3. **MBQ-31 (customer match-key set) remains Resolved at blueprint level,
   unchanged** — email is the sole automatic match key; phone and name stay
   advisory/manual-only, never automatic (DEC-014 point E). No change since
   the original draft.
4. **A customer-binding naming/schema proposal now exists** (this session's
   [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)),
   proposing the exact model name `shopify.connector.customer.binding`, its
   future file/class names, and its full field set — mirroring exactly how
   `mbq-55-product-binding-naming-schema-proposal.md` closed the product
   portion before Task 010's final prompt could be drafted. **This proposal
   is not yet accepted by ChatGPT** — see §4.
5. **A customer-domain gate-criteria proposal now exists** (this session's
   [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)),
   mirroring `product-domain-gate-criteria-proposal.md`. **Not yet accepted.**
6. **No blocker named in the original draft or in
   [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md)'s
   Task-011 row has changed status:** MBQ-05 (scalable many-customer token
   acquisition), VAL-B2 (no live Shopify connection), TD-002
   (`read_fulfillments` scope-naming), the fulfillment API model decision,
   Lite/Full packaging, and the multi-server concurrency proof requirement
   (SRR-03/04/09) all remain exactly as open as before Task 010's closure —
   none is touched, resolved, or narrowed by anything in this session. See
   [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
   §5 for the full, Task-011-scoped blocker classification.
7. **Address handling and company/person (`is_company`) classification
   remain open, unchanged.** Neither the original draft nor any document
   read this session resolves either gap.

## 3. Objective, approach, and exclusions — restated by reference

**Unchanged from [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md).**
This document does not restate that document's full narrative (objective;
customer binding/matching approach; fallback partner rules beyond the §2.2
status update above; duplicate handling; API needs; UI dependencies; tests
required; manual validation; rollback; acceptance criteria; explicit
exclusions) — it remains the accurate scope record, updated only for the
model-naming precision this session's companion proposal now supplies (§4
below) and the MBQ-29 status correction (§2.2 above).

**One concrete refinement to the binding approach, informed by this
session's naming proposal:** the original draft describes "`sale` defines
its own concrete customer-binding model... extending
`shopify.connector.binding.mixin` directly" without naming it. This
document's companion,
[`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
proposes the exact name `shopify.connector.customer.binding` (§5.1 of that
document) — a proposal, not yet accepted, that a future final implementation
prompt would use once accepted.

## 4. Preconditions — current status

| Precondition (per the original draft) | Current status |
| --- | --- |
| Foundation Tasks 002/003 merged and gate-opened | **Satisfied** — unchanged, confirmed accepted foundation (`master-implementation-readiness-checkpoint.md` §2). |
| The "sale domain gate" (`ui-ux-implementation-task-map.md` Group 11's prerequisite) explicitly opened | **Not satisfied.** No document in this repository defines what would need to be true to open it, mirroring exactly the "product domain gate" gap that blocked Task 010 before `product-domain-gate-criteria-proposal.md` was drafted. This session's [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md) proposes such criteria, scoped to Task 011 (customer import) only — **proposed, not yet accepted, and does not itself open anything.** |
| MBQ-55 (exact Odoo partner/binding field mapping) resolved via the dedicated naming/schema planning pass | **Not satisfied.** This session's [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md) proposes exactly this — **proposed, not yet accepted.** |
| DEC-014 points D and E (fallback partner, customer match-key set) remain the accepted design baseline | **Satisfied**, with the §2.2 correction above (MBQ-29 is now Resolved via AR-020, superseding DEC-014's own "partially resolved" language without contradicting it — AR-020 is itself a later, ChatGPT-accepted closure of the same row DEC-014 partially resolved). |

**Net effect: Task 011 is not ready to start.** Two of its four preconditions
remain unmet, and this session proposes (but does not itself satisfy) closure
paths for both. See
[`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
for the full readiness assessment and blocker classification.

## 5. Non-authorizations

This document does not:

- Authorize Task 011, Task 012, or any other domain-sync task.
- Authorize any code, module, model, view, controller, security file,
  manifest, test, or CI file of any kind.
- Open the customer-domain gate, the Task 011 implementation gate, or any
  other implementation gate.
- Resolve MBQ-55's customer-binding portion (proposed only, by the companion
  document) or its order-binding portion (untouched, remains fully open).
- Authorize any order import, product logic, inventory sync, fulfillment
  logic, UI, webhook, or OAuth/token-acquisition work.
- Rewrite, supersede, or invalidate
  [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md) —
  that document remains the accurate historical scope record; this document
  only layers a status update on top of it.

---

## Evidence / references

- [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md) —
  the prior scope draft, cited throughout, not edited — access: Accessible,
  this repository, observed 2026-07-09.
- [`../05-qa/task-010-product-import-validation-results.md`](../05-qa/task-010-product-import-validation-results.md)
  §K — Task 010 merge/runtime-green evidence — access: Accessible, this
  repository, observed 2026-07-09.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md)
  §4 (Task-011 row) — access: Accessible, this repository, observed
  2026-07-09.
- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  MBQ-29, MBQ-31, MBQ-55 rows — access: Accessible, this repository,
  observed 2026-07-09.
- [`../04-decisions/DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
  [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md),
  [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md) —
  companion documents drafted this session — access: Accessible, this
  repository, observed 2026-07-09.
- GitHub PR #138, PR #139 (`AdamsOdoo/Adams`) — merge commits
  `1f478032d8581a949fa7820847e5c1ab419586b4` and
  `297f398da96d11d1f8f9e25a9d15570a66aed80a` respectively, per this session's
  task instructions and confirmed via `git log`/`git merge-base` against
  this session's own branch — access: Accessible, 2026-07-09.

**Next step:** ChatGPT review of this refresh alongside the naming and
gate-criteria proposals it cites. See
[`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
for the exact next-session prompt.
