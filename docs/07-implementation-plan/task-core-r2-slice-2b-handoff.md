# Task CORE-R2 — Foundation Slice 2B: Session Handoff

> **Status: documentation-only session, complete. THE CODE GATE IS NOT OPEN.**
> No code written, no implementation gate opened, no PR #150/#151/#160 modified,
> no live validation performed. **SRR-03 remains OPEN.**

**Model:** Opus 4.8. **Date:** 2026-07-14. **Architecture:** AR-047.
**Author:** Claude (execution/research/documentation). **Review/gate:** ChatGPT.

This uses the full handoff format
(`docs/06-prompts/session-handoff-template.md`) because the Slice-2B packet's open
questions and adversarial findings are load-bearing.

---

## CORE-R2 replay-safety decision package (2026-07-15 — architecture-decision session)

> **Separate follow-up session — docs-only architecture decision, not a
> Slice-2B implementation or integration-staging session.** This session did
> **not** touch `claude/core-r2-slice-2b-integration`'s Slice-2B call-site
> work, PR #150, PR #151, or PR #163. It produced a new, separate decision
> package on its own branch/PR, targeting `claude/core-r2-slice-2b-
> integration` (not `Shopify-connector`). **SRR-03 remains OPEN. Prompt E
> remains BLOCKED.**

**Why.** PR #163 (`claude/core-r2-slice-2b-runtime-correction-review` @
`655e1cd744c9a9c9d82d65a926369168e0429de0`, base `claude/core-r2-slice-2b-
integration` @ `63d10fb465a26189fa463f9c7ac580da6a931c5c`) fixed three real
scheduled-dispatch defects but, by its own PR body, could not close the
underlying gap: a transaction-scoped row lock (`try_lock_for_update`)
prevents same-worker replay only — after a genuine PostgreSQL rollback,
another worker can legitimately claim the released job row and re-invoke the
real handler, and the recovered job's bounded auto-retry class
(`concurrency_race_conflict`) schedules a further automatic replay, in both
cases with no proof a prior Shopify transport did not already occur.
Control-room review (`4700703933`) required a decided, documented production
contract before any further CORE-R2 implementation is authorized. **PR #163
remains open, draft, and unmerged; it was not modified by this session.**

**What this session did.** Verified the current state (integration branch
still exactly `63d10fb`; PR #163/#150/#151 all draft/open/unmerged at their
required heads; `Shopify-connector` unchanged at `dd6ecb8`; no prior
replay-safety decision PR existed). Reset this session's designated branch
(`claude/core-r2-replay-safety-decision-3f7pjs`, which had initially pointed
at the `Shopify-connector` tip rather than the required integration SHA, and
carried no unique commits) to start exactly at `63d10fb`. Reviewed the exact
current job-dispatch mechanism (`_claim_for_dispatch`, PR #163's `_drain_one`/
`_recover_after_concurrency_conflict`, `operation_scope_key`/
`idempotency_key`), proved directly against the code that the existing
`shopify.connector.call.lease`/`execute_business` mechanism (dormant — no
production call site uses it) cannot be reused as-is (its lifecycle ends
before the job's own terminal-state commit), and independently re-verified
official Odoo 19 (`github.com/odoo/odoo`) and Shopify Admin GraphQL API
(`shopify.dev`) evidence directly (access date 2026-07-15). Produced a
12-phase architecture-decision package: semantic contract (effectively-once,
differentiated by declared operation class), a four-option durable-ownership
comparison (recommending Option A — committed `running`+`attempt_id`
ownership, extending PR #163's own accepted recovery mechanism), a
fail-closed replay-safety registry design, crash/stale-owner recovery
behavior, state/error mapping (reusing the existing `duplicate_risk`
vocabulary — no new error class needed), a nine-slice future implementation
sequence, and a self-critique against every named adversarial scenario.
**No implementation code, test, or PR #163 change was made.**

**Deliverables:**
[`../03-architecture/core-r2-job-execution-replay-safety.md`](../03-architecture/core-r2-job-execution-replay-safety.md)
(full analysis) and
[`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)
(decision record) — both **Proposed for ChatGPT review, NOT accepted**.
Architecture-review-log row **AR-048** added
([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)),
also Proposed, not accepted.

**Gate / scope status after this session.**

- PR #163 remains **draft and unmerged**; its runtime evidence is retained,
  but its implementation is **not accepted** — blocked by this replay-safety
  architecture decision, pending control-room review.
- PR #150 and PR #151 remain **open, draft, and unmerged**, untouched by this
  session.
- **No implementation gate is opened by this session.** The implementation
  sequencing in the architecture doc §9 (superseded by the scope-narrowing
  revision below — now Immediate Slice 1, Immediate Slice 2, and the
  deferred Layer 2 architecture gate) is sequencing only, not an
  authorization.
- **SRR-03 remains OPEN.** This session's package is a necessary but not
  sufficient step toward closing it — genuine multi-worker/multi-server
  runtime proof (SRR-04/SRR-09) is still separately owed, and this package's
  own ownership sweep is not yet jointly analyzed against the existing
  disconnect-quiescence controller's timeout (flagged as an open question in
  the architecture doc §10/§11, not silently assumed fine).
- `Shopify-connector` is **unchanged**.
- **Next session (after ChatGPT review):** superseded by the scope-narrowing
  revision and formal-acceptance note below — the next session, once
  separately authorized, begins with architecture doc §9 Immediate Slice 1
  (minimal replay-policy registry correction — no schema, no model, no
  cron), not Option A's schema/ownership substrate. Layer 2's schema and
  ownership substrate remain deferred, reopened by name only when a Shopify
  mutation domain is authorized for implementation.

**Scope-narrowing revision (2026-07-15, control-room review `4701015790`,
same session family — no new handoff entry).** Control-room review found
the package above disproportionate to current UAT scope: it made the full
Option-A durable-ownership protocol an immediate requirement, when every
implemented Shopify handler is read-only. The package was revised in place
(same PR #164, new head) to split into **Layer 1** — decided now, routed to
DEC-031 for acceptance: a minimal fail-closed replay-policy registry with
three declared classes (`local_only`/`remote_read_replay_safe`/
`remote_effect_not_replay_safe`), explicit declarations for the core
diagnostic/self-test handler and the current customer/product import
handlers, a fail-closed default for everything else, and PR #163's existing
recovery behavior **accepted as-is** for the current read-only scope — no
new model, field, migration, or cron proposed — and **Layer 2** — Option A
and the rest of the mutation-hardening design, retained unchanged in
substance but **deferred**, reopened by name only when inventory export,
fulfillment/tracking update, product export, refund creation, or any other
Shopify mutation is authorized for implementation. Task 012 order import is
explicitly not pre-registered by this decision. The nine-slice future
sequence is replaced with two immediate slices (registry implementation;
exact-head runtime validation) plus one deferred-roadmap paragraph. Evidence
is unchanged — only the recommendation and slicing narrowed. **PR #163
runtime evidence retained, implementation still not accepted. DEC-031/AR-048
remain Proposed/pending. SRR-03 remains OPEN. Prompt E remains BLOCKED.
`Shopify-connector` unchanged. Current UAT fast-track is read-only
product/customer/order work.** Updated files: architecture doc, DEC-031,
AR-048, this handoff, `research-handoff.md` — no production/test file
touched, PR #163 not modified, PR #164 kept draft, not merged.

**Formal acceptance (2026-07-15, control-room review `4701644819`, same
session family — no new handoff entry).** The Layer 1 / Layer 2 split above
is **accepted in substance** — no architecture redesign or additional
research required. A small docs-only editorial closure patch was applied
across the same five files: registry-completeness wording corrected to key
off `_get_handlers()`, not `JOB_STATE_SELECTION` (the unrelated job-state
vocabulary); the core handler-policy table corrected to list only
`core_dispatch_selftest` as a registered dispatcher handler (verified
against `shopify_connector_job_dispatch.py:145-161` — `core_readiness_check`,
`core_manual_maintenance`, and `core_test_connection` are job-type
vocabulary created outside the dispatcher registry, not `_get_handlers()`
entries); stale references to the superseded nine-slice plan replaced with
Immediate Slice 1 / Immediate Slice 2 / the deferred Layer 2 architecture
gate; the Layer 1 crash-recovery claim corrected from "strictly improved"
to "policy gating only" (PR #163's existing rollback/reclaim behavior is
accepted as sufficient for read-only handlers, unmodified). DEC-031 status
is now **Accepted by ChatGPT — 2026-07-15, control-room review
`4701644819`**; AR-048 status is now **Accepted**. **PR #164 is merged into
`claude/core-r2-slice-2b-integration` after this closure patch** (docs
only, same five files, no new file). PR #163 remains untouched,
draft/unmerged. PR #150 and PR #151 remain untouched, open/draft/unmerged.
`Shopify-connector` remains unchanged. **SRR-03 remains OPEN. Prompt E
remains BLOCKED. Task 012 implementation is not authorized by this
acceptance** — the next authorized step is a small, separately-authorized
implementation-gate session scoped to architecture doc §9 Immediate Slice 1
only.

---

## Runtime CORRECTION session (2026-07-15) — dispatch ownership/replay model (review `4699752673`)

> **Status: code + test + doc correction session, runtime-validated on Odoo.sh.**
> The implementation gate for the CORE-R2 dispatcher was already open (the drain
> and its tests exist and are being corrected); this session's control-room prompt
> authorised editing the allow-listed production/test/doc files. **No new module,
> no Prompt E, no merge, no gate self-authorisation. SRR-03 remains OPEN.**

**Model:** Opus 4.8 (1M). **Date:** 2026-07-15. **Author:** Claude. **Review/gate:** ChatGPT.

- **PR / base / head.** PR #163 (draft), base
  `claude/core-r2-slice-2b-integration` @ `63d10fb`, head branch
  `claude/core-r2-slice-2b-runtime-correction-review` (was `677cb67`; advanced by
  this session's single correction commit).
- **Root cause (control-room, confirmed).** The `retrying`-wrapped drain replayed
  the complete handler after a transport and re-drove/routed a job by a bare id
  after a rollback had already released its `FOR UPDATE SKIP LOCKED` claim (a
  transaction-scoped row lock, not a durable flag). See
  `../05-qa/task-core-r2-validation-results.md` §RTC-2.1.
- **Correction.** `shopify_connector_job_dispatch.py` drops `retrying`; `_drain_one`
  runs the handler once under the held claim and commits per job; a genuine
  40001/40P01/55P03 is recovered by `_recover_after_concurrency_conflict`
  (rollback → reset → reacquire the exact job under a fresh `FOR UPDATE SKIP
  LOCKED` lock → revalidate claimability under the lock → route ONCE to
  `concurrency_race_conflict`, `retry_waiting`/`failed_final`, WITHOUT replaying
  the handler). Another worker owning the job (SKIP-LOCKED empty) or having changed
  its state is a valid do-nothing outcome, never an overwrite.
- **Tests.** Updated the core disconnect `run_drain` proof to the no-replay model
  (`retry_waiting`, pgcode captured); added `TestDrainOwnershipReplayGenuine`
  (Tests A/B/C/D — genuine independent-connection races, real 40001, distinct
  PIDs); customer/product M18 tests now assert the superseded job ends `cancelled`
  (disconnect sweep of the `retry_waiting` job) with the 40001 evidenced from the
  dispatcher recovery log.
- **Files changed (allow-list only).** `models/shopify_connector_job_dispatch.py`;
  `tests/test_disconnect_quiescence.py`; `sale/tests/test_customer_matching_scalability.py`;
  `product/tests/test_product_import_matching.py`; `docs/05-qa/task-core-r2-validation-results.md`;
  `docs/05-qa/task-core-r2-customer-callsite-validation.md`;
  `docs/05-qa/task-core-r2-product-callsite-validation.md`; this file;
  `docs/07-implementation-plan/task-core-r2-customer-callsite-handoff.md`;
  `docs/07-implementation-plan/task-core-r2-product-callsite-handoff.md`.
  (`test_job_dispatch.py` needed no change and was not touched.)
- **Runtime (build 34923103).** Upgrade clean; product `0/0 of 174`; sale `0/0 of
  93`; core `0 failed, 6 error of 476` (the 6 = known `notification_type`
  `res.users` `setUpClass` artifact, RR-F/issue #157, classified separately);
  customer lifecycle `0/0 of 6` ×3; product lifecycle `0/0 of 4` ×3; ownership
  class (A/B/C/D + disconnect) `0/0 of 5` ×3; independent zero-residue audit clean.
- **Governance.** No live Shopify request; no merge; PR #163 kept draft, not marked
  ready; no new PR; `Shopify-connector`/`main`/plain `dev`/integration branch not
  advanced by this session beyond the PR head; PR #150/#151 untouched; Prompt E
  BLOCKED; SRR-03 OPEN. Full record: `../05-qa/task-core-r2-validation-results.md`
  §RTC-2.
- **Exact next-session prompt (for ChatGPT to authorise).** "Review PR #163 head
  on `claude/core-r2-slice-2b-runtime-correction-review` (ownership/replay
  correction, review `4699752673`): confirm the no-replay recovery contract, the
  reacquire-under-lock ownership guarantees, Tests A–D, and the runtime evidence in
  `task-core-r2-validation-results.md` §RTC-2; then decide whether to merge PR #163
  into the integration branch or request further changes. Do not open Prompt E."

---

## Slice 2B integration-staging setup (2026-07-14 — branch-orchestration session)

> **Separate follow-up session — branch orchestration & history integration only.**
> This session created the Slice-2B integration-staging branch and merged the two
> accepted domain PR heads into it. **No production, test, XML, manifest, security,
> or cron code was written or modified; no call-site migration was performed; the
> public generic `execute()` was not removed/privatized; no PR was opened, merged,
> or closed; no Odoo.sh or live-Shopify validation was run.** The prerequisite in
> `Recommended next session` (drive PR #160 to runtime-green, accept, and merge into
> `Shopify-connector`) has been satisfied by the control room, so this session
> begins at packet §7 step 2. **SRR-03 remains OPEN. Issue #157 remains separate.**

**Base (§7 steps 1–2).** Branch `claude/core-r2-slice-2b-integration` was created
from the exact post-PR-#160 `Shopify-connector` tip
`a3fd6cdfcb6f3654ae81a48a7f4e694994d4762b` — the merge commit of **PR #160 —
CORE-R2 Foundation Slice 2A** (control-room Slice 2A acceptance `4693862195`;
parents `1494b97d…` + Slice-2A head `843511c004…`). The branch tip was verified to
equal the required base before any merge.

**Merge of PR #151 (§7 step 3 — product / Task 010B).** The exact accepted PR #151
head `e4669aaf206fe8436a6d8a524b083f48d56ac9df` (validated code SHA
`db534f833cf3636184681801dcd7e13636e09245`; control-room acceptance `4686089797`)
was merged into staging with a **normal no-fast-forward merge commit**
`2c4d5e9a522ea414b40f9dc9967ead608679e38c` (parents = staging base `a3fd6cdf…` +
PR #151 head `e4669aaf…`). No `addons/**` conflict occurred; the merge was clean.
Every `shopify_connector_product/**` blob is byte-identical to the PR #151 head,
and the 010B validation record/packet match the PR #151 head.

**Merge of PR #150 (§7 step 3 — customer / Task 011B).** The exact accepted PR #150
head `10d0034e8e666684daa36f517788223976d74035` (validated concurrency code SHA
`662e9809c7b2443a0391f417ca2dff7daa3da29e`; control-room acceptance `4689951254`)
was merged into staging with a **normal no-fast-forward merge commit**
`4beba38b37534bca01335907d1c884d952dec5d4` (parents = post-#151 staging head
`2c4d5e9…` + PR #150 head `10d0034e…`). No `addons/**` conflict occurred. Every
`shopify_connector_sale/**` blob is byte-identical to the PR #150 head, the 011B
validation record matches the PR #150 head, and the product blobs still match the
PR #151 head.

**Documentation-only conflict resolution (§7 step 3 shared-document rule).** The
second merge conflicted **only** in the two expected shared documents; both were
resolved by **union, preserving both domain histories completely** — each resolved
file differs from the post-PR-#151 staging head by *only* PR #150's own additions
(verified: zero deletions):

- `docs/05-qa/architecture-review-log.md` — the AR-045 (Task 011B) index row was
  inserted immediately before AR-046 (Task 010B), keeping the AR table ascending
  (`AR-044 / AR-045 / AR-046 / AR-047`). **Both AR-045 and AR-046 records are
  preserved** with all their build/SHA/acceptance references; no historical note
  was deleted.
- `docs/01-research/research-handoff.md` — **both** runtime-closure session blocks
  were kept at the top in reverse-chronological order (Task 011B build `34863138`
  above Task 010B build `34828304`, both above the prior CORE-R2 Slice 1 entry).
  No acceptance ID, SHA, build ID, gate status, or chronology was lost.

**Inherited domain code unchanged.** This session made **no** call-site change and
edited no inherited product/customer/core production or test file. A static
`compileall` of the three connector addons passes (syntax only) — this is **not** a
runtime-green claim.

**Evidence status.** The historical PR #150/#151 exact-head runtime evidence
(builds 34828304 @ `db534f8`; 34863138 @ `662e980`) remains **supporting evidence
only** for the inherited domains (packet §6). **No integrated-head runtime evidence
exists yet** — the integration-staging tree has not been built or tested and is
**explicitly not runtime-green**. Integrated exact-head Odoo.sh evidence and the
deployed multi-worker proof are earned later on the staging head (validation plan
§1.4/§2), not by this session.

**Final integration-staging head and child-branch creation point.** After the two
merge commits above, **this staging-setup handoff commit becomes the final
integration-staging head**, and it is the **exact point from which both child
branches are cut** (§7 step 4). `claude/core-r2-product-callsite` and
`claude/core-r2-customer-callsite` are created from that **one identical** final
head — so both contain Slice 2A plus the complete Task 010B and Task 011B domains,
both share the same tip, neither carries an extra commit, and neither starts from a
raw PR #150/#151 head nor directly from `Shopify-connector`. The exact final-head
SHA and the two identical child tips are recorded in the session final report.

**Gate / scope status after this session.**

- PR #150 and PR #151 remain **open, draft, and unmerged**; neither was merged into
  `Shopify-connector`, and neither was closed. No code from either PR reached
  `Shopify-connector`.
- **No implementation gate beyond branch setup is opened.** Both domain importers
  still call the legacy public `execute()`; `execute_business` exists but no
  production call site enters it; the public generic `execute()` is untouched.
- **SRR-03 remains OPEN.** Issue #157 remains a separate
  `res.users.notification_type` fixture investigation, not mixed into this work.
- **Next sessions:** **Prompt P** (product call-site migration, §8) and **Prompt C**
  (customer call-site migration, §9) may run **in parallel** on the two child
  branches (disjoint file sets). **Prompt E** (public-`execute()` closure, §9c)
  **remains blocked** until **both** child branches are merged back into
  `claude/core-r2-slice-2b-integration`.

---

## Session summary

**Revision 3 — correction session** driven by control-room review **`4690831454`
(REVISE)** on PR #158, following Revision 2 (review `4690659767`). Revision 1 built
the Slice-2B packet; Revision 2 replaced the rejected direct-merge "Option B" with
the integration-staging strategy, made RD-P loop-owned, corrected flush semantics,
and resolved the public-`execute()` closure into Slice 2B. **Revision 3 corrects
three remaining architecture defects, in the same three packet files:**

1. **Lifecycle API boundary (no public `execute_lifecycle`).** The packet no longer
   assumes Slice 2A delivers a *public* API-client `execute_lifecycle`. The
   RPC-facing lifecycle surface is the **store actions** (`action_test_connection`,
   `action_reconnect`), which select a **fixed internal purpose** and call a
   **private** (underscore-prefixed) API-client lifecycle transport. The
   connector-owned public API-client business entry stays `execute_business`; no
   public generic transport and no RPC-callable arbitrary-purpose method remain.
   Prompt E inspects the **final merged** Slice-2A code and **preserves** that
   private boundary rather than inventing a public method (packet §6b, §9c;
   validation M16/M17).
2. **Admission-vs-disconnect timing (Race A / Race B).** `_admit` holds `FOR SHARE`
   only for the **short admission side transaction** and **releases it at that
   commit**; the committed **lease** (not a store-row lock) represents the holder
   across `_send`/reconciliation. A disconnect after a committed admission does
   **not** wait for the context — it bumps generation, sets `disconnecting`, and
   returns (Race B); only a disconnect racing the still-uncommitted admission
   touches the `FOR SHARE` window (Race A). M8/M18 and every "disconnect waits for
   the context" claim are rewritten (packet §5.6; validation M8/M18, §2.1).
3. **Integration-PR net scope.** The final staging→`Shopify-connector` PR carries
   the **complete net product + customer domains** plus both call-site migrations
   plus the core execute closure — because PR #150/#151 are **never** merged into
   the target base. The false "diff is only migrations/closure over a base that
   already contains the domains" wording is replaced with the true net diff and a
   merge-history/file-group/evidence review decomposition; PR #150/#151 are closed
   **superseded/subsumed, not marked individually merged** (packet §7.3;
   validation C9).

PR #160 is now referenced by **capability**, not by its moving draft head/surface.
**This session opened no implementation gate and authorized no code.**

## Branch and commits

- **Branch:** `claude/core-r2-slice-2b-packet-l0is3j` (the governance-designated
  development branch; the brief's "preferred" `claude/core-r2-slice-2b-packet`
  differs only by the session-id suffix — see "What ChatGPT should review").
- **Base:** `Shopify-connector` @ `912801508155c6358e8f5f1a7a0aaf01ae573675`.
- **Commits:** Revision 1 = `df7118a` (three files created); Revision 2 = `d255a02`
  (correction per review `4690659767`); Revision 3 = one docs-only correction commit
  per review `4690831454`, editing the same three files. PR #158 stays
  open/draft/unmerged throughout.

## Files created or updated

The **same exact three files** (no additional file created or modified):

1. `docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`
   — state verification; product + customer call-site inventory (base and PR-head);
   change design (RD-P **loop-owned**, RD-C); the **admission-vs-disconnect timing
   model (§5.6, Race A / Race B)**; **integration-staging strategy** (§7, 8 steps)
   + the **true integration-PR net scope & review decomposition (§7.3)**; the
   **private-lifecycle-boundary** public-`execute()` closure design (§6b, no public
   `execute_lifecycle`); future prompts **P, C, and E** (E capability-based).
2. `docs/05-qa/task-core-r2-slice-2b-validation-plan.md`
   — regression + runtime test matrix (M1–M18 per domain; M8/M18 = Race A/Race B;
   M16/M17 = private lifecycle boundary); deployed multi-worker/multi-server plan
   (14 assertions, Topology C, ×3 stability), on the integration-staging head;
   SRR-03 closure checklist (C1–C10).
3. `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (this file).

## What changed (Revision 3)

New/corrected governance documentation only. No code, schema, test, manifest, CI,
or non-allowlisted doc changed. **No PR #150, #151, or #160 body or branch
touched.** No shared handoff, AR log, risk register, or rejected-approaches log
modified (explicitly out of this session's allowlist). Revision 3 edited only the
three packet files, correcting the lifecycle API boundary, the admission-vs-
disconnect timing model, and the integration-PR net scope (details in the session
summary and adversarial findings AF-14…AF-16).

## Evidence and citations added

All claims cited to in-repo code (SHA-named line anchors) or the merged CORE-R2
governance docs. Access status: all sources **Accessible** on 2026-07-14 (local
working tree + `git show` at PR head SHAs + GitHub PR/issue/review metadata). No
external web source used.

Verified state this session (Revision 3): PR #158 open/draft @ `d255a02` (the
Revision-2 head), base `912801508…`, exactly 3 files; PR #150 open/draft @
`10d0034…`; PR #151 open/draft @ `e4669aa…`; **PR #160 (Slice 2A) open/draft, no
runtime-green claimed (static-only) — its head has moved (observed `415c05c…`,
distinct from the `b3d23cb…` in its own body), which is exactly why this packet now
references it by capability, not by a pinned head/surface**; issue #157 open
(separate); working tree clean. Reviews `4690659767` and `4690831454` (both REVISE)
read in full.

## Assumptions

- **[Fact — now confirmed]** "Slice 2A" is PR #160 (disconnect controller,
  `disconnecting` state, generation bump, direction-C, and a **private
  fixed-purpose lifecycle transport** behind the trusted store actions — PR #160's
  correction direction uses a private `_execute_lifecycle`, not a public method, so
  this packet references the **capability**, not the name). PR #160's body states
  it **removes neither the public `execute()`** and claims **no runtime-green**
  (static validation only).
- **[Fact — corrected]** The integration target is the dedicated **staging
  branch** `claude/core-r2-slice-2b-integration`, cut from a post-Slice-2A
  `Shopify-connector`, into which PR #151/#150 heads are merged — **not**
  `Shopify-connector` itself. The change design is anchored to both the base and
  the PR-head importer versions.
- **[Inference]** Media CDN downloads (`_fetch_image`) are **not** admission-gated
  business calls (tokenless GETs to image URLs); they run inside the terminal
  lease under RD-P and need no redesign.

## Open questions

- **[Resolved] OQ-1 — public-`execute()` closure placement.** Now **owned by
  Slice 2B** as the final integration-closure step (packet §6b; Prompt E). Slice
  2A/PR #160 supplies a **private** fixed-purpose lifecycle transport (reached
  through the store actions) and migrates `action_test_connection` onto it; Slice
  2B removes the legacy public generic `execute()` after both call sites migrate
  and **preserves** the private lifecycle boundary (no public `execute_lifecycle`
  invented). Satisfies closure item C5.
- **[Resolved] OQ-2 — 2A-before-2B ordering.** Firmed into a **hard
  prerequisite**: Slice 2A (PR #160) must be runtime-green, control-room accepted,
  and merged into `Shopify-connector` **before** the staging branch is created
  (packet §5.4, §7 step 1). No Slice 2B activation runs against a tree lacking
  Slice 2A.
- **[Resolved] OQ-3 — product lease shape.** RD-P is **loop-owned per-page,
  exactly one lease at a time**; the "umbrella lease" alternative is **withdrawn**
  (packet §5.1). The loop owns each `with`; reconciliation runs inside the terminal
  page's context.
- **OQ-4 — integration-base drift (recorded, not blocking).** The merged analysis
  §9.3 product-migration spec targets the **base** single-call site (`:213`); PR
  #151 replaced it with a multi-page loop. RD-P is re-derived against the PR #151
  head; ChatGPT should note §9.3 is stale for the product domain.
- **OQ-5 — `flush_all()` exactness (implementer confirms).** The implementing
  session confirms the exact Odoo 19 flush call and that it is not redundant with
  `_apply_import`'s savepoint. Semantics are now stated precisely
  (materialize-in-transaction, not commit).
- **External prerequisite (not this packet's to resolve):** PR #160 must earn its
  own exact-head runtime-green and control-room acceptance before step 1 of the
  staging sequence can proceed.

## Risks

- **Gate-reversal risk (the review's core finding):** merging PR #150/#151 into
  `Shopify-connector` while their handlers still call unguarded `execute()` would
  place admission-unprotected Shopify-calling code on the integration branch. The
  staging strategy (§7) structurally prevents this — the domain PRs are only ever
  merged into the staging branch, and only the protected+validated result reaches
  `Shopify-connector` via one controlled PR.
- **Scope risk:** the product migration is not a one-line swap (multi-page,
  loop-owned context). Prompt P must resist touching matching/pricing/media logic;
  the allowlist + static guards enforce call-site-only, and forbid any helper that
  returns an `execute_business` `result`.
- **Ordering risk:** activating 2B before 2A yields wrong-tier
  `ShopifyQuiescedError` handling and a non-firing generation gate. The staging
  strategy makes Slice 2A a hard, ordered prerequisite.
- **Evidence risk:** historical PR #150/#151 runtime results are supporting-only;
  presenting them as integrated-head evidence is forbidden. The staging head earns
  its own fresh exact-head evidence.

## Adversarial findings (self-review §10 of the correction brief)

Each potential defect was checked against the actual code and the corrected
design; corrections were applied.

- **AF-1 — Unsafe domain code entering `Shopify-connector` before protection?**
  Prevented. PR #150/#151 are **never** merged into `Shopify-connector` while
  unguarded; they merge only into `claude/core-r2-slice-2b-integration`; the
  protected+validated result reaches `Shopify-connector` via one integration PR
  (packet §7). This was the review's central defect and is now structurally
  impossible under the documented strategy.
- **AF-2 — API result escaping its lease?** Prevented. RD-P dissolves
  `_execute_query`; the loop owns each `with execute_business(...)`; no method
  returns a `result` to a caller that reconciles later (packet §5.1; validation
  M14). RD-C keeps `result` inside the single `with`.
- **AF-3 — Terminal reconciliation outside the lease?** No. `_normalize_payload`
  + `_apply_import` + `flush_all` + `return` all run **inside** the terminal
  page's context; `__exit__` releases only after `flush_all` (packet §5.1;
  validation M2).
- **AF-4 — Hidden second Shopify Admin call?** No. Every Admin page call is a
  `with execute_business(...)`; media (`_fetch_image`) is a tokenless CDN GET, not
  a credentialed Admin-API business call (packet §5.3; validation M13). Static
  guard: no reachable `api.client.execute(`.
- **AF-5 — Explicit main-cursor commit?** Forbidden. No `self.env.cr.commit(` in
  either importer; the commit is the natural dispatcher/RPC boundary's job
  (packet §5, §5.3; validation M15).
- **AF-6 — Flush described as commit / durable visibility?** Corrected. Every
  occurrence now states `flush_all()` **materializes SQL in the main transaction**
  and does **not** commit or make writes visible to another transaction (packet
  §5, §5.3; validation M15). The stale "durable within the handler transaction"
  wording was removed.
- **AF-7 — Public `execute()` bypass remaining?** Closed by Prompt E (§6b): the
  legacy public generic `execute()` is removed/fail-closed; the connector-owned
  public **business** entry stays `execute_business`; the lifecycle transport stays
  **private** behind the store actions (no public `execute_lifecycle`); the
  transport seam is `_`-prefixed; static guards prove zero reachable
  `api.client.execute(` and no RPC arbitrary-purpose bypass (validation M16/M17;
  closure item C5).
- **AF-8 — Sibling-branch history duplication?** Avoided. Slice 1 + Slice 2A live
  once (the base the staging branch is cut from); the domain PRs arrive via normal
  merge commits preserving history; no cherry-pick; no shared CORE-R2 commit is
  applied twice (packet §7.2).
- **AF-9 — Child branches based on different staging heads?** No. Both
  `claude/core-r2-product-callsite` and `claude/core-r2-customer-callsite` are cut
  from the **same** `claude/core-r2-slice-2b-integration` head (packet §7 step 4),
  then merged back into it (step 5).
- **AF-10 — Old PR runtime evidence presented as integrated evidence?**
  Prevented. PR #150/#151 (and PR #156) evidence is labelled **historical,
  supporting-only**; the integrated-head evidence is captured fresh on the staging
  head (packet §6; validation §1.4).
- **AF-11 — Product/customer scope mixing?** Avoided. Prompt P and Prompt C are
  disjoint-file (`shopify_connector_product/**` vs `shopify_connector_sale/**`),
  parallel-safe child branches; Prompt E is core-only and runs last.
- **AF-12 — Premature SRR-03 closure?** No. SRR-03 stays **OPEN**; closure needs
  all of C1–C10 (Slice 2A merged/green, both migrations, deployed proof ×3,
  public-`execute()` closure, ordered rollback, single integration merge, separate
  live-read authorization). This session closes nothing (validation §3).
- **AF-13 — Accidental implementation authorization?** None. Every file carries
  the "CODE GATE IS NOT OPEN / SRR-03 OPEN / documentation only" banner; Prompts
  P/C/E are explicitly GATED and paste-ready for **future** authorized sessions.

**Revision 3 findings (review `4690831454`):**

- **AF-14 — Invented public `execute_lifecycle` / RPC-callable lifecycle bypass?**
  Removed. The packet no longer assumes a public API-client `execute_lifecycle`.
  The RPC-facing lifecycle surface is the **store actions**, which select a fixed
  internal purpose and call a **private** `_`-prefixed lifecycle transport; no
  public generic transport and no caller-supplied-purpose method remain. Prompt E
  inspects the merged Slice-2A code and **preserves** the private boundary rather
  than exposing a new public method (packet §6b, §9c; validation M16/M17;
  closure C5).
- **AF-15 — Store-row lock held across the HTTP/reconciliation body / disconnect
  blocking on the context?** Corrected. `_admit` holds `FOR SHARE` only for the
  short admission side transaction and releases it at that commit; the committed
  **lease** (not a store-row lock) spans the body. A disconnect after a committed
  admission returns **without waiting** for the context (Race B); only a
  disconnect racing the uncommitted admission touches the `FOR SHARE` window
  (Race A). M8/M18 and all "disconnect waits for the context" wording were
  rewritten (packet §5.6; validation M8/M18, §2.1 assertion 3). The
  lease-through-reconciliation contract is preserved (it is the lease row, not a
  lock, that spans the body).
- **AF-16 — Fictitious integration base / domain PR marked individually merged?**
  Corrected. The final integration PR's **true net diff** carries the complete
  product + customer domains plus both call-site migrations plus the core closure
  (the base does not already contain the domain PRs); review is decomposed by
  merge-history / file-group / evidence; PR #150/#151 are closed **superseded/
  subsumed, not marked individually merged** (packet §7.3; validation C9). The
  false "diff is only migrations/closure over a base that already contains the
  domains" claim was withdrawn.

**Corrections applied this revision (Revision 3):** removed the public-
`execute_lifecycle` assumption and rewrote §6b/§9c around the private
fixed-purpose lifecycle boundary; added §5.6 (Race A / Race B) and rewrote M8/M18
+ §2.1 assertion 3; added §7.3 (true integration-PR net scope + review
decomposition) and rewrote validation C9/C5; made Prompt E capability-based and
made all PR #160 references capability-based (unpinned its moving draft head);
updated the classification table, the §11 adversarial summary (AF-1…AF-16), and
the references in all three files.

## Learning feedback loop

*(Captured here per `CLAUDE.md` §12; the shared `quality-feedback-loop.md` and
`research-handoff.md` were intentionally NOT modified — see "What ChatGPT should
review".)*

- **New issues discovered:** the original packet's "Option B" reversed the CORE-R2
  gate by merging unguarded domain handlers into `Shopify-connector` before
  protecting them — a category error the review caught; corrected via the
  staging-branch strategy. A helper that enters a context manager and returns its
  `result` silently releases the lease before caller reconciliation — a real
  correctness trap now explicitly forbidden. **Revision 3 added three more:** (a)
  assuming a *public* API-client `execute_lifecycle` when Slice 2A keeps the
  lifecycle transport **private** behind trusted store actions — a surface the
  packet must not invent; (b) describing the store-row `FOR SHARE` lock as held
  across the HTTP/reconciliation body (it is released at the short admission
  commit; the committed lease spans the body), which made "disconnect waits for
  the context" wrong — corrected to the Race A / Race B model; (c) describing the
  final integration PR's diff as "only the migrations/closure over a base that
  already contains the domains" — false, because PR #150/#151 never merge into
  `Shopify-connector`; the true net diff carries both whole domains.
- **Repeated issue patterns:** (a) base-vs-PR-head anchor drift (OQ-4); (b)
  conflating a "protection is planned later" plan with "merge the unsafe code
  first" — the gate must be held at the integration branch, not deferred. Guard
  rules recommended to ChatGPT below.
- **Rules/checklists updated:** none modified this session (allowlist forbids it);
  **recommended** rules for ChatGPT: "never merge a frozen domain PR into the
  integration branch while it retains an unguarded transport call site — protect
  on a staging branch first"; "a context-manager migration must be reviewed for
  any helper that returns the yielded value out of the `with`"; and (Revision 3)
  "depend on a prerequisite PR by **capability**, never by a moving draft head or
  method name — document a public API surface only after inspecting the *merged*
  code, and never invent a public entry the merged code keeps private"; "state
  the `FOR SHARE`/lease lock window precisely — the store-row lock is released at
  the admission commit; the committed lease, not a lock, spans the body"; "for an
  integration PR, state the **true GitHub net diff** against the actual base, and
  close subsumed PRs as superseded, never as individually merged."
- **New rejected approaches:** the **direct-merge Option B** (merge PR #150/#151
  into `Shopify-connector` before call-site protection) — recommended for the
  rejected-approaches log with revisit condition "never (gate reversal)"; and the
  **umbrella/double-lease** product design — recommended with revisit condition
  "only if a future requirement needs continuous cross-page lease coverage and the
  foundation is reopened." Not logged in the shared file (allowlist forbids it);
  flagged for ChatGPT.
- **New technical debt:** none introduced (no code).
- **Architecture concerns:** the single-call `execute_business` contract does not
  natively express multi-page fetch under one lease; resolved by §6 Phase C
  loop-owned per-page re-admission (not an umbrella lease), consistent with the
  merged analysis.
- **Tests or review gates needed:** the M1–M18 activation matrix; the §2 deployed
  proof (×3); static guards proving no reachable `api.client.execute(`, no result
  escaping a context, and no main-cursor commit; **(Revision 3)** the Race A /
  Race B disconnect-timing tests (M8/M18), the private-lifecycle-boundary guards
  (M16/M17 — no public `execute_lifecycle`, no RPC-callable arbitrary purpose,
  `_`-prefixed transport), and the §2.1 assertion that `action_disconnect` returns
  without blocking on an admitted call's context.
- **Should future prompts change? Yes** — done across revisions: Prompt P is
  loop-owned RD-P against the PR #151 head; Prompts P/C start from the staging
  head with Race A/Race B tests; Prompt E is now **capability-based** (inspect the
  merged Slice-2A code, preserve its private lifecycle boundary, add no public
  `execute_lifecycle`); all PR #160 references are capability-based.

## What ChatGPT should review

1. **Approve the integration-staging strategy** (packet §7, 8 steps) replacing the
   rejected Option B.
2. **Confirm the loop-owned RD-P** design (packet §5.1) and the withdrawal of the
   umbrella-lease alternative.
3. **Confirm the flush semantics** (materialize-not-commit; no main-cursor commit).
4. **Approve the public-`execute()` closure** as a Slice-2B deliverable, with the
   **private** lifecycle boundary preserved and **no public `execute_lifecycle`
   invented** (packet §6b; Prompt E, capability-based). *(Revision 3.)*
5. **Confirm the admission-vs-disconnect timing model** — `FOR SHARE` released at
   the admission commit; the committed lease (not a store-row lock) spans the body;
   Race A (pre-commit) vs Race B (`action_disconnect` returns without waiting)
   (packet §5.6; validation M8/M18, §2.1). *(Revision 3.)*
6. **Confirm the true integration-PR net scope** (complete both domains + both
   migrations + closure over a base that contains only Slice 2A) and the
   merge-history/file-group/evidence review decomposition, and that PR #150/#151
   are closed **superseded/subsumed, not individually merged** (packet §7.3;
   validation C9). *(Revision 3.)*
7. **Prerequisite tracking:** PR #160 (Slice 2A) must reach exact-head
   runtime-green + control-room acceptance before step 1; its head is moving
   (observed `415c05c`, distinct from its body's `b3d23cb`) — hence capability-based
   references. This packet does not and cannot advance PR #160.
8. **Governance deviations to bless:** (a) this session did **not** update the
   shared `research-handoff.md` or the shared `quality-feedback-loop.md`, because
   the allowlist is exactly the three packet files — this conflicts with
   `CLAUDE.md` §12; raised here rather than silently resolved. (b) The branch used
   is the designated `claude/core-r2-slice-2b-packet-l0is3j`, not the brief's
   "preferred" `claude/core-r2-slice-2b-packet` (suffix only).

## Recommended next session

**Slice 2A (PR #160) runtime-green + review** — obtain its exact-head Odoo.sh
validation and control-room acceptance, then merge it into `Shopify-connector`
(packet §7 step 1). Only after that: create `claude/core-r2-slice-2b-integration`,
merge PR #151/#150 heads into it, then run **Prompt P**, **Prompt C**, and
**Prompt E** as scoped authorized sessions, and the deployed multi-worker proof.

## Stop confirmation

Work stopped at the documentation boundary. No code was written; no PR #150/#151/
#160 was modified; no implementation gate was opened; no live Shopify validation
was performed; **SRR-03 remains OPEN.** Awaiting ChatGPT review.

---

## Exact next-session prompt (paste-ready, for after ChatGPT ratifies)

```text
You are Claude Code taking CORE-R2 Foundation Slice 2A (PR #160) to exact-head
runtime-green for the Odoo 19 Shopify Connector, then defining the Slice-2B
integration-staging sequence. Still gated: do NOT open the Slice 2B code gate and
do NOT merge PR #150/#151 into Shopify-connector.

Read first: CLAUDE.md; docs/03-architecture/disconnect-quiescence-remediation-analysis.md
(§6 Phase A/B/C, §8, §9.1-9.3, §10, §13, §14, §16, §23, §24); docs/07-implementation-plan/
task-core-r2-disconnect-quiescence-packet.md; the three Slice-2B packet files
(callsite-runtime packet incl. §5.1 loop-owned RD-P, §5.6 Race A/Race B timing,
§6b public-execute closure with the private lifecycle boundary, §7 integration-
staging strategy, §7.3 true integration-PR net scope; validation plan incl.
M8/M18 Race A/B and M16/M17; this handoff); the MERGED Slice-2A code (do not rely
on PR #160's draft head/surface).

Scope: (1) drive PR #160 to exact-head Odoo.sh runtime-green (full core suite +
the two migrated tests + genuine locked-first/all-locked selection), capturing
build/DB/SHA; obtain control-room acceptance; merge Slice 2A into Shopify-connector.
(2) Confirm the staging sequence: create claude/core-r2-slice-2b-integration from
the post-2A Shopify-connector tip; merge PR #151 and PR #150 HEADS into it with
normal merge commits (stop on any addons/** conflict; preserve both histories on
shared-doc conflicts); then child branches claude/core-r2-product-callsite and
claude/core-r2-customer-callsite from the same staging head for Prompt P / Prompt C;
merge them back; Prompt E closes public execute(); validate the staging head
(fresh install + full core/product/sale + M1-M18 + deployed multi-worker proof x3
+ cleanup + public-entry static audit); one controlled integration PR to
Shopify-connector; PR #150/#151 closed as subsumed only after that merge.

Do NOT: merge PR #150/#151 directly into Shopify-connector; introduce an umbrella
lease; let any execute_business result escape its context; add a main-cursor
commit; invent a public execute_lifecycle (preserve Slice 2A's private
fixed-purpose lifecycle transport behind the store actions); assume action_disconnect
blocks on an admitted call's context (it returns without waiting — Race B); depend
on PR #160's moving draft head/method names (use capability, inspect the merged
code); describe the integration PR as a diff over a base that already contains
PR #150/#151, or mark those PRs individually merged; run live Shopify validation;
mark SRR-03 closed.

End: run the learning review, update the handoff + validation record, confirm the
quality gate, commit/push to the designated branch, then STOP.
```

---

## Quality gate confirmation

- [x] Session handoff written (this file — a dedicated Slice-2B handoff; the
      shared `research-handoff.md` was intentionally not modified per the
      allowlist, flagged for ChatGPT).
- [x] Quality feedback loop checked (captured above; shared
      `quality-feedback-loop.md` not modified per the allowlist, flagged).
- [x] New learning captured (in this handoff).
- [~] Rejected approaches (direct-merge Option B; umbrella lease) — recommended
      for the shared log; **not** logged there this session (allowlist forbids
      editing that file); flagged for ChatGPT.
- [x] No accepted technical debt introduced (no code).
- [x] Repeated-issue patterns (gate-reversal; base-vs-PR-head drift;
      context-manager result escape) escalated into recommended rules for ChatGPT.

## Sprint checkpoint log

- **CORE-R2 Slice 2B packet — Revision 1 (2026-07-14):** wrote the three Slice-2B
  docs; recommended Option B + RD-P/RD-C; opened docs-only draft PR #158. No code,
  no gate, SRR-03 OPEN.
- **CORE-R2 Slice 2B packet — Revision 2 (2026-07-14):** corrected per review
  `4690659767`. Rejected Option B → integration-staging strategy (§7); loop-owned
  RD-P (§5.1); flush = materialize-not-commit (§5/M15); public-`execute()` closure
  into Slice 2B (§6b, Prompt E); Prompts P/C rebased on the staging head + Prompt E
  added; validation M14–M18 and integration-staging-head framing. PR #160 (Slice
  2A) is the hard prerequisite. No code, no gate, SRR-03 OPEN.
- **CORE-R2 Slice 2B packet — Revision 3 (2026-07-14):** corrected per review
  `4690831454`. (1) Private fixed-purpose lifecycle boundary behind the store
  actions — no public `execute_lifecycle` (§6b, §9c; M16/M17). (2) Race A / Race B
  admission-vs-disconnect timing — `FOR SHARE` released at admission commit, the
  committed lease spans the body, `action_disconnect` returns without waiting
  (§5.6; M8/M18, §2.1). (3) True integration-PR net scope + merge-history/
  file-group/evidence review decomposition; PR #150/#151 closed superseded/
  subsumed, not individually merged (§7.3; C9). Prompt E made capability-based; all
  PR #160 references made capability-based (head unpinned). No code, no gate,
  SRR-03 OPEN. Next: PR #160 runtime-green + merge, then the staging sequence.
- **CORE-R2 Slice 2B runtime CORRECTION — (2026-07-14):** one controlled
  correction session on Odoo.sh build **34912503** from staging `63d10fb`, branch
  `claude/core-r2-slice-2b-runtime-correction`. Closed the three adjudicated
  runtime findings: (1) customer disconnect-first PID proof made genuinely
  distinct by holding the disconnect connection open; (2) the customer & product
  M18 concurrent-disconnect reconciliations now retry-then-refuse through the REAL
  scheduled `run_drain` under `odoo.service.model.retrying` — the smallest
  common-layer production fix in `shopify_connector_job_dispatch.py` (never
  re-issues an ORM write in an aborted transaction; genuine 40001 → rollback →
  re-browse → refuse-before-second-transport → `failed_retryable`); (3) product
  lifecycle cron-trigger residue closed via per-test baseline ownership. Added a
  core Phase-5 `run_drain` retry proof. `notification_type` kept as an accepted
  non-blocking partial-registry artifact (unchanged). **Runtime:** fresh-install
  precedent 574/574; product 174, sale 93 green; core ×3 (6 notif-artifacts
  only); customer lifecycle ×3 and product lifecycle ×3 all `0 failed/0 error`;
  independent residue audit clean (incl. cron-trigger delta 0). Pushed via
  `odoosh-push` to the build's bound branch `claude/core-r2-slice-2b-integration`
  (a separate branch cannot be pushed from the dev container; no force-push), as
  a single clean fast-forward correction commit; **NOT promoted to
  `Shopify-connector`. No gate transition, no live Shopify request. SRR-03 OPEN.
  Prompt E BLOCKED. PR #150/#151 untouched; `Shopify-connector` unchanged.** See
  `../05-qa/task-core-r2-validation-results.md` §RTC.
