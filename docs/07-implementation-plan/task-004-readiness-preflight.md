# Task 004 Readiness Preflight

> **Preparatory only. This document does not authorize coding, does not open
> any implementation gate, does not unblock Task 004, and does not mark Task
> 003 complete.** It exists so that, once Task 003 and the token-acquisition
> direction are resolved and ChatGPT is ready to consider Task 004, the
> control room has one place that summarizes exactly what is true today, what
> must become true first, and what the candidate scope looks like — without
> pre-deciding any of it. Nothing in this document may be cited as
> ChatGPT authorization for Task 004 or as evidence that Task 003 is
> complete.

## Status

**Docs-only preflight package. Prepared 2026-07-07, revised 2026-07-07**
on branch `claude/task-004-readiness-preflight-vgbkt3`, originally branched
from `Shopify-connector` at its tip after PR #109 merged (merge commit
`9d0bc11dac55b5fd6cdf338dfec2909e96364f45`). This revision updates the
package after two sessions that were in flight at the time of the original
draft have since **merged**: **PR #109** (the Fable/manual-OAuth
token-acquisition experiment, recorded as blocked before execution — no
Fable tool and no Shopify Dev Dashboard credentials were available) and
**PR #110** (the static/offline Task 003 validation sweep, recording
additional static evidence for VAL-A4/VAL-C1(server-log
half)/VAL-C3/VAL-D1/VAL-D2). Neither PR changed Task 003's overall
incomplete status or Task 004's blocked status. See §7 "History — prior
sessions, now merged" below for what changed and why this document no
longer describes them as concurrent or expected.

This document does not itself change the status of Task 003 or Task 004. It
only restates their current, already-recorded status (§1) and organizes
already-existing planning material (§3–§4) so a future gate-review session
does not have to re-derive it from scratch.

---

## 1. Current gate status

All of the following is restated from already-merged documents — nothing
here is a new finding or a new decision.

- **Task 003 (API client + test connection) is merged but its manual
  validation is incomplete.** Per
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  (PR #107; extended by a blocked continuation session recorded in **PR
  #109, merged**; extended again by a static/offline validation sweep
  recorded in **PR #110, merged**): eight checklist items passed live
  against a real Odoo 19 + Shopify development-store session (VAL-A2,
  VAL-A3, VAL-B1, VAL-B3, VAL-C2, VAL-E2, VAL-E3, VAL-F1), VAL-A1 passed
  only as an installed-module/registry-load observation (a fresh clean
  install/upgrade was not re-executed), and **VAL-B2 — the valid-token
  positive-connection test — remains BLOCKED**, with VAL-E1 blocked as a
  direct consequence. PR #110's static/offline sweep additionally
  confirmed, by static repo/source evidence (not live-environment proof):
  VAL-A4 (no XML/menu/action/wizard/controller/cron introduced), VAL-C3
  (exactly two `sudo()` call sites), VAL-D1 (the test-connection query is
  read-only, no mutation string exists), and VAL-D2 (no domain model is
  touched). VAL-C1 remains **PARTIAL** (DB/ORM leakage scan passed; the
  server-log grep half was confirmed **not testable in that session's
  environment** — no live Odoo runtime or log files were available —
  and remains not tested). VAL-B4–B7 and VAL-G1–G4 remain not tested. **Task
  003 manual validation has not been called Go or No-Go.**
- **Task 004 implementation is still not started, and remains blocked.**
  Per
  [`../04-decisions/shopify-token-acquisition-decision-brief.md`](../04-decisions/shopify-token-acquisition-decision-brief.md)
  §9 ("Can Task 004 start before this is resolved? **No.**") and every
  research-handoff entry since (PR #107, #108, #109, #110): Task 004
  implementation remains blocked pending both Task 003 completion/acceptance
  and a decided token-acquisition direction. Neither PR #109 nor PR #110
  changed this — no valid Shopify Admin API token was used or obtained by
  either, and neither claims OAuth succeeded or that VAL-B2 passed.
- **Task 004 may now proceed to gate-opening *review* only, because VAL-B2
  is formally deferred by ChatGPT.** Per
  [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
  (2026-07-07): ChatGPT has formally deferred VAL-B2 from the Task 003 →
  Task 004 gate. VAL-B2 is **not passed, not failed, and not waived** —
  this deferral changes only what the Task 003 → Task 004 *gate* requires,
  not VAL-B2's own status. See the corresponding conditional-acceptance
  update in
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  §5. **This does not unblock Task 004 implementation** — see the next
  bullet.
- **Task 004 still requires its own separate gate-opening act and final
  implementation prompt**, both explicitly accepted by ChatGPT, before any
  code is written. DEC-021 authorizes gate-opening *review* preparation
  only (this session's Phase 7 package;
  [`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md),
  [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md),
  [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
  — all draft, none authorizing code).
- **TD-001 routing remains a hard pre-start condition.** Per
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)'s
  routing note: TD-001 must be explicitly named — either as a mandatory
  first Task 004 implementation acceptance criterion, or as its own
  separate pre-Task-004 patch — before or inside the Task 004 gate. No
  Task 004 implementation may silently inherit the existing
  `core_readiness_check` collision behavior.
- **Constraint carried forward from DEC-021:** no customer-facing
  readiness pass, activation, setup wizard, or domain sync may depend on
  the unproven VAL-B2. Any Task 004 readiness-signal design must show
  unknown/not-proven when VAL-B2 evidence is absent — never an inferred
  "connected"/"pass" state.
- **VAL-B2 is pending on an unresolved token-acquisition question
  (MBQ-05).** Per the decision brief and
  [`../03-architecture/shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md):
  as of 2026-01-01, Shopify closed the "admin-created custom app, reveal a
  token in the UI" path for any newly created app. The brief recommends
  **Option C** (keep the existing offline/custom-app storage shape; attempt
  a manual OAuth authorization-code-grant exchange, outside the Odoo
  codebase, as a research-validation step) but this is a
  **[Recommendation]**, not an accepted **[Decision]**. A first attempt at
  that empirical step (recorded in PR #109) could not even start — no
  Fable-equivalent browser-automation tool and no Shopify Dev Dashboard
  credentials were available to that session. **Whether a Dev-Dashboard
  custom app can complete the standard OAuth flow is still an open
  question**, not a confirmed fact in either direction.
- **The token-acquisition direction remains pending an empirical
  result.** Nothing currently known lets anyone assert Option A, B, or C
  is correct with confidence — the decisive fact (does the manual OAuth
  exchange actually work against a Dev-Dashboard custom app?) has not been
  observed yet, in either direction.

---

## 2. What must be true before Task 004 can start

Restated from the decision brief §9 and the credential/connection/API
foundation plan's dependency chain
([`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md)),
not newly invented here. **All** of the following must hold, not just some:

1. **A valid Shopify connection must be proven, or VAL-B2 must be formally
   re-scoped by ChatGPT.** Either (a) VAL-B2 is executed and passes against
   a real Shopify development store using a token obtained through a
   decided acquisition path, or (b) ChatGPT explicitly accepts a formal
   re-scoping of VAL-B2 (e.g., deferring it with a named, documented
   condition) — silently treating VAL-B2 as "close enough" is not
   acceptable per the decision brief §8. **Partially satisfied for
   gate-opening *review* only, per
   [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)
   (2026-07-07):** ChatGPT has formally deferred VAL-B2 from this gate,
   satisfying condition (b) for the narrow purpose of allowing Task 004
   gate-opening review to proceed. **This is a deferral, not a proof of
   connection** — VAL-B2 itself is still not passed, and this condition is
   still not satisfied for Task 004 *implementation* to start, which
   requires its own separate gate-opening act per item 5 below.
2. **Task 003's validation record must be accepted by ChatGPT.** A partial
   record, however clean, is not the same as an accepted one. The
   `task-003-validation-results.md` Go/No-Go section (§5) currently reads
   "not yet determined" — that must change to an actual ChatGPT-reviewed
   recommendation before Task 004 planning proceeds.
3. **MBQ-05 / the token-acquisition direction must be accepted or explicitly
   deferred by ChatGPT.** Per the decision brief §10, ChatGPT may accept
   Option C's empirical-validation path, or may instead commit directly to
   Option A (documented limitation) or Option B (build OAuth now) without
   running the experiment — but *some* explicit choice must be recorded as
   an MBQ-05 closure note in
   [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
   or a proper `DEC-XXX`. Today MBQ-05 remains open.
4. **No critical Task 003 runtime defect may remain open.** Specifically:
   - No new defect was found in the tested paths of the 2026-07-07 live
     session (`task-003-validation-results.md` §4 — "None newly found this
     session"), but that session also did not test 12 checklist items.
   - **TD-001 remains open** — see §5 below; it is directly relevant to
     Task 004's own scope (the readiness engine consumes the same
     `core_readiness_check` job type TD-001 describes) and should be
     explicitly considered, not silently inherited, before or inside a
     future Task 004 gate act.
   - VAL-C1's server-log-grep half is still not tested — an open credential-
     redaction question that Task 004 (which will also write JSON check
     results into `job.log.payload_snapshot`) should not inherit unexamined.

None of the above are decided by this document. This section only collects,
in one place, the specific conditions already on record elsewhere.

---

## 3. What Task 004 must NOT include until unblocked

Restated from
[`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md)'s
own Task 004 scope description — not a new restriction invented here:

- **No product/customer/order/inventory sync code or modules.** Task 004 is
  a `shopify_connector_core`-only readiness-check substrate; the domain
  modules (`shopify_connector_product`, `_sale`, `_inventory`,
  `_fulfillment`) are separate, later, independently-gated work
  ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md)).
- **No OAuth implementation of any kind**, unless a future session is
  separately authorized to do so as its own named task (Option B, if
  ChatGPT ultimately selects it). Task 004's readiness engine only *reads*
  the existing test-connection/scope-snapshot state Task 003 already
  produces — it does not acquire or exchange tokens itself.
- **No UI wizard work.** Task 004's allowed files are explicitly "core
  models/tests only ... no views." The setup wizard is Task 006, gated
  separately behind its own UI-implementation-gate opening (still closed
  per AR-023) and behind MBQ-03/MBQ-05/MBQ-22.
- **No webhooks, cron, or scheduling.** The readiness engine's webhook-HMAC
  and mapped-location checks are explicitly scoped as **pending slots**
  (registered but not implemented) in the existing Task 004 planning — not
  as something this preflight session is proposing to add or remove.
- **No credential model changes beyond read-only use.** Task 004 consumes
  Task 002/003's already-accepted credential and scope-snapshot fields; it
  does not modify `shopify.connector.store.credential` or its security
  files.
- **No CI/workflow files.** Consistent with every prior task in this
  project (Task 001A's repo-wide "no runtime, no CI" precedent).

---

## 4. Likely Task 004 candidate scope — candidate only, not authorized

> **This section describes what already exists in prior, ChatGPT-legible
> planning documents. It is reproduced here for convenience, not proposed
> or invented by this session. Nothing in this section is authorized, and
> none of it should be read as this session recommending a *different*
> scope than what is already on record — the point is continuity, not
> re-design.**

The smallest, already-identified next foundation step after Task 003 is
named in
[`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md):
**Task 004 — Readiness check substrate.**

- **Candidate objective:** a readiness-check engine — a check registry
  (core-owned checks plus a domain extension seam), essential-vs-warning
  tiers per the already-accepted DEC-018/MBQ-06 split, running as
  `setup_readiness_check`-sourced jobs (job type `core_readiness_check`,
  already defined since Task 001) with per-check JSON results written to
  `job.log.payload_snapshot`, and a summary mirrored onto
  `store.last_readiness_result` / `store.last_readiness_at`.
- **Candidate allowed files (from prior planning, subject to a future §9
  task prompt's own exact list):** `shopify_connector_core` models and
  tests only — a readiness-service model/registry file; explicitly **no
  views**.
- **Candidate essential checks (already accepted at DEC-018/MBQ-06 level,
  not re-decided here):** credential validity / test-connection result,
  required scopes present, API-version health, store identity, `web.base.url`
  reachability, webhook HMAC secret presence (if webhooks are enabled),
  cron/queue health, at least one mapped Location with an enabled domain,
  and intentional domain-flag enablement. All other candidate checks warn
  only, never block — per DEC-018, already accepted.
- **Candidate acceptance shape (from prior planning):** a failed essential
  check can never yield an overall "pass"; warnings never block; every
  check returns a named reason; every check is read-only; the webhook-HMAC
  and mapped-Location checks are registered as *pending slots* only, not
  implemented, in this candidate scope.
- **What is still explicitly open even within this candidate scope:** the
  exact readiness-check copy, XML IDs, and numeric thresholds (MBQ-06's own
  stated residual) — these remain task-spec detail for whichever future
  session actually writes Task 004's binding `CLAUDE.md` §9 prompt, and are
  not decided by this preflight document either.

**Separating "candidate" from "decision":** everything in this §4 is a
**candidate**, sourced from documents ChatGPT has already seen
(`credential-connection-foundation-task-plan.md`, DEC-018,
`master-blueprint-open-questions.md` MBQ-06). This preflight package does
not ask ChatGPT to accept this scope now, and does not assume the final
scope will match it exactly — only that, absent a different direction from
ChatGPT, this is the scope a future Task 004 gate-opening act would most
naturally reference.

---

## 5. Risks if Task 004 starts too early

1. **Building the readiness engine on top of an unproven connection.**
   Task 004's essential checks are explicitly gated on "credential
   validity / test-connection result" — if VAL-B2 has never actually
   passed, the readiness engine's most important check has never been
   exercised against a real success path, only against the VAL-B1
   failure path. Shipping Task 004 before VAL-B2 passes (or is formally
   re-scoped) risks building and testing an entire tier system around a
   pass condition nobody has ever observed.
2. **TD-001 collision risk is structurally relevant, not incidental.**
   [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)'s
   TD-001 describes exactly the job type (`core_readiness_check`) Task
   004's own candidate scope is built around: a second
   `core_readiness_check` job for the same store collides on
   `store_idempotency_key_uniq` because the job type is target-less and
   carries no per-run `payload_hash` nonce (the fix already applied to
   `core_test_connection` in Task 003, by design, does not extend to
   `core_readiness_check`). If Task 004 starts before this is explicitly
   routed (folded into a future gate by name, or its own tiny follow-up
   patch, per TD-001's own "owner" column), the readiness engine may be
   built, tested once, and then silently fail on its very first re-run in
   a live environment — a defect that would look like a Task 004 bug but is
   actually an inherited, already-known Task 001 defect.
3. **VAL-C1's unfinished server-log scan is a redaction question Task 004
   would inherit.** Task 004's own candidate design writes per-check JSON
   results into `job.log.payload_snapshot` — the same field family whose
   ORM/database-visible redaction was confirmed clean, but whose Odoo
   server-log-level redaction was never checked. Starting Task 004 before
   that gap is closed risks compounding an unverified redaction surface
   rather than reusing an already-proven one.
4. **A false "connected" signal undermines the whole Dashboard/Sync Center
   design.** The accepted UX principle behind readiness (`setup-ux-principles.md`,
   "prove readiness") and Task 004's own listed risk ("dashboard false
   health," mitigated by fail-closed aggregation) both depend on the
   underlying test-connection signal being trustworthy. If Task 004 ships
   while VAL-B2 is still unobserved, the "prove readiness" promise is
   itself unproven at its foundation.
5. **Scope-creep pressure.** Task 004 sits directly upstream of Task 005
   (lifecycle actions) and Task 006 (the setup wizard). Starting Task 004
   early, under schedule pressure, risks the same "quietly widen scope"
   failure mode this project's governance model (`CLAUDE.md` §6, §9) exists
   to prevent — e.g., someone deciding mid-task to also touch lifecycle
   actions or wizard copy "while they're in there."
6. **Re-litigating MBQ-05 mid-implementation.** If Task 004 starts before
   MBQ-05 is closed, and the empirical OAuth experiment (whenever it
   eventually runs) fails, ChatGPT may need to revisit the credential
   model's `token_variant` seam or scope-snapshot assumptions Task 004's
   readiness checks are built on — forcing rework of code that would
   otherwise not need to change.

---

## 6. Session handoff

- **Branch:** `claude/task-004-readiness-preflight-vgbkt3`.
- **Original session (2026-07-07):** branched from `Shopify-connector` at
  merge commit `9d0bc11dac55b5fd6cdf338dfec2909e96364f45` (PR #109's merge
  commit). Created this file plus
  `docs/07-implementation-plan/task-004-dependency-map.md`,
  `docs/06-prompts/task-004-candidate-claude-prompts.md`, and
  `docs/05-qa/task-004-quality-gates.md`. No other file was created or
  modified; `docs/01-research/research-handoff.md`,
  `docs/05-qa/task-003-validation-results.md`, and
  `docs/04-decisions/shopify-token-acquisition-decision-brief.md` were read
  for context but not edited, to avoid colliding with the two sessions
  named in §7 that were in flight at the time (PR #109 and PR #110, both
  since merged).
- **This revision (2026-07-07, after PR #109 and PR #110 merged):** merged
  the latest `Shopify-connector` (which now includes PR #110's static/offline
  Task 003 validation sweep on top of PR #109) into this branch, then
  updated wording in this file and in `task-004-dependency-map.md` that
  described PR #109's and PR #110's work as still concurrent or expected —
  both have merged, so that wording is now stale and has been corrected to
  the past tense with their actual recorded outcomes. **No file outside the
  four allowed files was edited in this revision either** —
  `research-handoff.md`, `task-003-validation-results.md`, and
  `shopify-token-acquisition-decision-brief.md` remain untouched by this
  session, per this session's own explicit instruction to avoid churn in
  those files unless ChatGPT asks for a handoff entry.
- **What was prepared:** a Task 004 readiness preflight (this document), a
  dependency map, a set of draft-only, explicitly not-runnable candidate
  Claude prompts for Task 004's eventual sub-slices, and a generic Task 004
  quality-gate checklist — all sourced from already-existing, already-merged
  planning material, not from new research or new architecture decisions.
- **What remains blocked:** Task 003 manual validation (VAL-B2 and several
  other items — see §1) and the MBQ-05 token-acquisition direction; and, as
  a direct consequence of both, Task 004 itself. **Nothing in this session,
  nor in PR #109 or PR #110, changes any of that.**
- **No code changed:** confirmed, in both the original session and this
  revision. No file under `addons/`, no `*.py`, `*.xml`, `*.csv`, manifest,
  security, test, migration, CI, or Dockerfile was created or modified.
  Only the four Markdown files listed above.
- **Stop condition:** this revision stops once the four allowed files are
  updated, `git diff` against latest `Shopify-connector` is confirmed to
  touch only those four files, the branch is pushed, and PR #111 is
  confirmed mergeable. No further work (including any Task 004 work, any
  Task 003 work, or any edit to `research-handoff.md`) is performed in this
  session.
- **This revision (2026-07-07, after PR #111 merged, branch
  `claude/task-004-gate-opening-w3f1zg`):** after ChatGPT's control-room
  decision to defer VAL-B2 from the Task 003 → Task 004 gate
  ([`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)),
  this session updated §1's gate-status bullet and §2 item 1 above to
  record that Task 004 may now proceed to gate-opening *review* only, and
  prepared the Task 004 gate-opening package
  (`task-004-gate-opening-proposal.md`,
  `task-004-readiness-check-substrate-gate.md`,
  `task-004-final-implementation-prompt.md`,
  `../05-qa/task-004-manual-validation-checklist.md`). **Task 004
  implementation is still not started and is still not authorized by this
  session or by DEC-021.**

---

## 7. History — prior sessions, now merged

At the time this package was originally drafted, two other sessions were
in flight and this document described them as concurrent/expected. Both
have since **merged**, so that framing is now stale; this section restates
what actually happened and why the file-avoidance choices in §6 still
stand, for a different reason (avoiding unnecessary churn, not avoiding a
live conflict):

- **The Fable/manual OAuth token-acquisition experiment — merged as PR
  #109.** The experiment did not execute: no Fable-equivalent
  browser-automation tool and no Shopify Dev Dashboard credentials were
  available to that session, so it stopped before reaching the Shopify Dev
  Dashboard. PR #109 recorded this outcome in
  `docs/05-qa/task-003-validation-results.md` (§8) and
  `docs/04-decisions/shopify-token-acquisition-decision-brief.md` (§10a),
  and added its own compact handoff entry to
  `docs/01-research/research-handoff.md`. No OAuth attempt was made; VAL-B2
  is unchanged (still BLOCKED); MBQ-05 is unchanged (still open).
- **The static/offline Task 003 validation sweep — merged as PR #110.**
  This session completed static/offline evidence for the checklist items
  that do not require a valid Shopify Admin API token (VAL-A4, VAL-C3,
  VAL-D1, VAL-D2, and the VAL-C1 server-log-half finding of "not testable
  in this session's environment"). It added three new QA documents
  (`task-003-static-validation-sweep.md`,
  `task-003-no-side-effect-baseline.md`,
  `task-003-server-log-redaction-check.md`), appended a static/offline
  addendum to `task-003-validation-results.md`, and added its own compact
  handoff entry to `research-handoff.md`. No real Shopify token was used;
  VAL-B2 remains BLOCKED/not attempted; Task 003 remains incomplete.
- **Net effect on this package:** neither merge changes anything in §1–§5
  above beyond the specific static-evidence updates already folded into
  §1. Task 003 is still incomplete, Task 004 is still blocked, and MBQ-05
  is still open. This session's own file-avoidance choice (not editing
  `research-handoff.md`, `task-003-validation-results.md`, or
  `shopify-token-acquisition-decision-brief.md`) continues in this
  revision, now simply because no handoff-entry update was requested for
  this revision — not because of any remaining conflict risk with PR #109
  or PR #110, which are both already merged and closed.

See [`task-004-dependency-map.md`](./task-004-dependency-map.md) §"Conflict
map" for the corresponding, similarly-updated file-ownership table.
