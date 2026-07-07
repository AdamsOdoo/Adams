# Task 004 Dependency Map

> **Preparatory only. Not authorization to code, not an architecture
> decision, and not a claim that any dependency below is satisfied.** This
> document maps what already exists in accepted planning material
> ([`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md),
> [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> the token-acquisition brief) into one dependency graph, for use once
> ChatGPT is ready to review Task 004 readiness. It resolves nothing and
> unblocks nothing.

## Status

Prepared 2026-07-07, companion to
[`task-004-readiness-preflight.md`](./task-004-readiness-preflight.md).
Docs-only. Branch `claude/task-004-readiness-preflight-vgbkt3`. **Revised
2026-07-07** after **PR #109** (Fable/OAuth token-acquisition experiment,
blocked before execution) and **PR #110** (static/offline Task 003
validation sweep) both merged into `Shopify-connector` — see §7 for what
changed and why the original "sessions in flight" framing has been
corrected to the past tense.

---

## 1. Dependency graph — Task 001/002/003 → Task 004

```
Task 001  Core module scaffold (models only, no views)          — merged
        │  (defines job/job.log/store/store.credential shapes;
        │   defines core_readiness_check job_type; TD-001 origin)
        ▼
Task 002  Credential storage, masking, redaction                — merged
        │  (shopify.connector.store.credential; token_variant=
        │   'offline_custom_app'; _get_access_token; redact())
        ▼
Task 003  API client shell + test connection                    — merged,
        │  (first outbound Shopify Admin API calls, read-only;    manual
        │   action_test_connection(); core_test_connection         validation
        │   job_type; granted_scopes / _checked_at scope            INCOMPLETE
        │   snapshot on store)                                     (VAL-B2
        │                                                           blocked)
        ▼
Task 004  Readiness check substrate                    — IMPLEMENTATION
          (candidate scope: check registry, essential/warning    NOT STARTED;
           tiers per DEC-018/MBQ-06, setup_readiness_check jobs,  gate-opening
           job.log.payload_snapshot per-check results, summary    REVIEW ONLY
           mirrored to store.last_readiness_result/_at)          per DEC-021
        │
        ▼
Task 005  Connection lifecycle actions (activate/disconnect/
          reconnect, perm_create ACL decision)                   — not started
        │
        ▼   (+ UI implementation gate, still closed per AR-023,
        │    + MBQ-03/MBQ-05/MBQ-22)
        ▼
Task 006  Setup wizard UI (horizon only)                          — not started
```

Parallel, cross-cutting dependency feeding into Task 004 specifically:

```
Shopify Token-Acquisition Decision (MBQ-05)
  research (PR #108) → decision brief (PR #108, Recommendation only)
        │
        ▼
  empirical OAuth exchange experiment — attempted once (PR #109),
  BLOCKED before execution (no Fable tool, no Shopify Dev Dashboard
  credentials available to that session)
        │
        ▼
  ChatGPT accepts a direction (Option A / B / C) → MBQ-05 closes
        │
        ▼
  VAL-B2 re-attempted with a token obtained via the accepted path
        │
        ▼
  Task 003 validation Go/No-Go recorded ─────────┐
                                                  ▼
                                    Task 004 becomes reviewable
                                    (still requires its own
                                     separate ChatGPT gate act
                                     + §9 task prompt)

  ── DEC-021 deferral branch (2026-07-07) ──────────────────────
  ChatGPT defers VAL-B2 from the Task 003 → Task 004 gate
  (DEC-021) — MBQ-05 does NOT close; VAL-B2 is NOT passed
        │
        ▼
  Task 003 conditionally accepted for Task 004 gate-opening
  REVIEW purposes only (task-003-validation-results.md §5)
        │
        ▼
  Task 004 gate-opening package may be prepared and reviewed
  (task-004-gate-opening-proposal.md,
   task-004-readiness-check-substrate-gate.md,
   task-004-final-implementation-prompt.md) — still requires its
  own separate ChatGPT gate-opening act before ANY code is written;
  TD-001 routing is a hard pre-start condition; no customer-facing
  readiness/activation/wizard/domain-sync claim may depend on the
  unproven VAL-B2
```

This project's tasks never "reach forward" — each task consumes only
merged, ChatGPT-reviewed predecessors
(`credential-connection-foundation-task-plan.md`, closing line: "Credential
storage → test connection → readiness → lifecycle → wizard: each task
consumes only merged predecessors; no task reaches forward.").

---

## 2. Open blockers (as of 2026-07-07)

| # | Blocker | Current state | Tracked in |
| --- | --- | --- | --- |
| 1 | VAL-B2 (valid-token positive-connection test) | **BLOCKED, now formally DEFERRED from the Task 003 → Task 004 gate by [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md) (2026-07-07)** — no valid Shopify Admin API token was obtainable in any session to date; deferral unblocks Task 004 gate-opening *review* only, not implementation, and is not a pass | `../05-qa/task-003-validation-results.md`; `../04-decisions/DEC-021-val-b2-deferral-for-task-004.md` |
| 2 | Task 003 Go/No-Go recommendation | **Conditionally accepted for Task 004 gate-opening review only, per DEC-021** — not a full Go, not a No-Go; live valid-token connection remains unproven and Task 003 is not fully complete for customer-facing readiness | `../05-qa/task-003-validation-results.md` §5 |
| 3 | MBQ-05 (token-acquisition direction) | **Open — deferred for Task 004 only, not resolved, per DEC-021.** Option C is still a Recommendation, not accepted; empirical experiment not yet run | `../04-decisions/shopify-token-acquisition-decision-brief.md`; `master-blueprint-open-questions.md` |
| 4 | Empirical OAuth exchange experiment | **Blocked before execution twice-attempted-scope** — no Fable-equivalent tool/connector and no Shopify Dev Dashboard credentials available in the one session that attempted it | `../05-qa/task-003-validation-results.md` §8; decision brief §10a |
| 5 | VAL-C1 server-log-grep half | **Not tested** — confirmed by PR #110 (merged) as "not testable in that session's environment" (no live Odoo runtime or log files available); still not tested by any session | `../05-qa/task-003-validation-results.md` |
| 6 | VAL-A4, VAL-C3, VAL-D1, VAL-D2 | **Statically confirmed by PR #110 (merged)** — repo/source-level evidence only, not live-environment proof | `../05-qa/task-003-static-validation-sweep.md`; `../05-qa/task-003-no-side-effect-baseline.md`; `../05-qa/task-003-server-log-redaction-check.md`; results doc |
| 6a | VAL-B4–B7, VAL-E1, VAL-G1–G4 | **Not tested / blocked** — unaffected by PR #109 or PR #110 | `../05-qa/task-003-manual-validation-checklist.md`; results doc |
| 7 | TD-001 (`core_readiness_check` idempotency collision) | **Open**, unrouted beyond its register entry — no gate has yet named it explicitly | `../05-qa/technical-debt-register.md` |
| 8 | No Task 004 gate-opening act exists | **Proposal only, not yet accepted** — `task-004-gate-opening-proposal.md` and `task-004-readiness-check-substrate-gate.md` are prepared this session as proposals for ChatGPT review; the gate does **not** open until ChatGPT explicitly accepts and merges a gate-opening act, per the AR-021/AR-026/AR-028 precedent | `task-004-gate-opening-proposal.md`; `task-004-readiness-check-substrate-gate.md` |
| 9 | No Task 004 final implementation prompt exists | **Draft only, not yet accepted** — `task-004-final-implementation-prompt.md` is prepared this session, marked "DRAFT — DO NOT RUN UNTIL CHATGPT EXPLICITLY APPROVES AFTER REVIEW"; it is not issued and does not authorize any code | `task-004-final-implementation-prompt.md` |

---

## 3. Downstream risks

- **Task 005 (lifecycle actions) and Task 006 (setup wizard) both consume
  Task 004's output** (`store.last_readiness_result`/`_at`, and the
  essential/warning tier signal). Any defect or premature scope decision in
  Task 004 propagates directly into both.
- **The Dashboard/Sync Center/Error Center design** (MVP domain sequence
  Area 7) treats Task 004's readiness signal as one of nine fixed dashboard
  cards ("connection health"). An unreliable or unproven readiness signal
  undermines that card's trustworthiness across the whole operator-facing
  surface, not just Task 004 in isolation.
- **Every domain module (product/customer/order/inventory/fulfillment)**
  structurally depends on Task 004 per
  [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md)
  §"(a) Dependencies that block ALL domain work": "the readiness engine
  determines the essential/warning tiers (MBQ-06) that gate whether a store
  may run business sync at all; domain sync jobs depend on this substrate
  to be safely enqueued." A rushed or later-reworked Task 004 risks forcing
  rework across every domain module built on top of it.
- **TD-001 propagation risk** — if Task 004 is implemented without
  explicitly routing TD-001 (see §5 of the readiness preflight), the
  readiness engine inherits a collision defect on its very first re-run
  path in any live environment, which could masquerade as a "Task 004 bug"
  during a future validation session rather than being correctly
  attributed to already-known Task 001 debt.
- **MBQ-06 residual (exact copy/XML IDs/thresholds)** remains open even
  within Task 004's own candidate scope — a future Task 004 task prompt
  must fix these residuals itself; leaving them undecided risks essential
  checks with vague or inconsistent failure reasons reaching an operator.

---

## 4. Decisions required before coding (Task 004)

None of these are decided by this document. Listed so a future gate-review
session has a single checklist:

1. **MBQ-05 closure or explicit deferral** — Option A, B, or C, or an
   explicit "defer, ship Task 004 anyway with VAL-B2 formally re-scoped"
   call — recorded as an MBQ-05 closure note or a proper `DEC-XXX`.
   **Explicit deferral recorded 2026-07-07 via
   [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md)** —
   this satisfies the "explicit deferral" branch for Task 004 gate-opening
   *review* purposes only; it is **not** an MBQ-05 closure and does not
   decide Option A/B/C. MBQ-05 remains open at the product/architecture
   level (see `master-blueprint-open-questions.md`).
2. **Task 003 acceptance** — ChatGPT reviews and classifies
   `task-003-validation-results.md`'s Go/No-Go (§5) as accepted, accepted
   with conditions, or requires further live validation before Task 004 is
   considered. **Conditionally accepted 2026-07-07 for Task 004
   gate-opening review purposes only, per DEC-021** — not a full Go, not a
   No-Go, and not a claim of full completion; ChatGPT's own review of this
   PR is still the acceptance act being sought.
3. **TD-001 routing decision** — fold into a future gate by explicit name
   (e.g., the Task 004 gate itself, if ChatGPT so chooses), or schedule as
   its own separate "Task 001B" follow-up patch, per
   `technical-debt-register.md`'s own "owner" column recommendation. Task
   004 must not silently inherit or silently fix TD-001 without a named
   decision either way. **Routing requirement recorded 2026-07-07** in
   `technical-debt-register.md` and named explicitly in
   `task-004-gate-opening-proposal.md` /
   `task-004-readiness-check-substrate-gate.md` — this records that TD-001
   *must* be routed inside the Task 004 gate; it does not itself decide
   *whether* Task 004 fixes it or a separate patch does. That choice is
   still open, pending ChatGPT's review of the gate-opening package.
4. **MBQ-06 residual thresholds** — the exact readiness-check copy, XML
   IDs, and numeric thresholds must be fixed in whatever future Task 004
   task prompt is issued (already flagged as task-spec detail, not
   pre-decided here).
5. **A Task 004 gate-opening act** — following the AR-021/AR-026/AR-029
   precedent (`task-002-credential-storage-gate.md`,
   `task-003-api-client-test-connection-gate.md`): a separate, explicit,
   merged ChatGPT act naming exactly what Task 004 may touch, before any
   §9 task prompt is issued.
6. **A Task 004 §9 final implementation prompt** — allowed files, forbidden
   files, acceptance criteria, tests, rollback notes, definition of done —
   written and accepted only after the gate-opening act above.

---

## 5. Validations required before coding (Task 004)

1. **VAL-B2** — a valid Shopify development-store token must actually pass
   `action_test_connection()`, or ChatGPT must explicitly accept a formal
   re-scope of this requirement.
2. **VAL-C1's server-log-grep half** — since Task 004 writes additional
   per-check JSON into the same `job.log.payload_snapshot` family, this
   redaction gap should be closed (or explicitly, separately accepted as a
   known residual) before Task 004 adds more data into that surface.
3. **A live re-confirmation that TD-001 still reproduces exactly as
   described** (already reconfirmed once, VAL-F1, 2026-07-07) at the time
   Task 004 actually starts, in case any intervening change altered its
   behavior.
4. Any other Task 003 checklist item ChatGPT decides is a hard precondition
   at the time of review (VAL-A4, VAL-B4–B7, VAL-C3, VAL-D1–D2, VAL-G1–G4)
   — this document does not pre-judge which of these, if any, ChatGPT will
   treat as blocking versus advisory for Task 004 specifically.

---

## 6. Docs that must be reviewed before coding starts

- [`CLAUDE.md`](../../CLAUDE.md) — governance contract, still in force.
- [`../01-research/research-handoff.md`](../01-research/research-handoff.md) —
  current-state entries (PR #107, #108, #109 and whatever supersedes them).
- [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  and
  [`../05-qa/task-003-manual-validation-checklist.md`](../05-qa/task-003-manual-validation-checklist.md).
- [`../04-decisions/shopify-token-acquisition-decision-brief.md`](../04-decisions/shopify-token-acquisition-decision-brief.md)
  and
  [`../03-architecture/shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md).
- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  — MBQ-05 and MBQ-06 rows specifically.
- [`credential-connection-foundation-task-plan.md`](./credential-connection-foundation-task-plan.md)
  — Task 004's own already-documented candidate scope.
- [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md)
  — TD-001.
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  and
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) —
  standard pre-task check per `CLAUDE.md` §10.
- [`task-003-api-client-test-connection-gate.md`](./task-003-api-client-test-connection-gate.md)
  and
  [`task-002-credential-storage-gate.md`](./task-002-credential-storage-gate.md) —
  the gate-opening-act precedent Task 004 would need to follow.
- This document and
  [`task-004-readiness-preflight.md`](./task-004-readiness-preflight.md)
  themselves, once ChatGPT is ready to consider Task 004.

---

## 7. Conflict map — files future implementation sessions must not touch without explicit approval

**Revision note (2026-07-07):** the two sessions this table originally
described as "currently in flight alongside this one" have both since
**merged** — the Fable/OAuth experiment as **PR #109** and the
static/offline Task 003 validation sweep as **PR #110**. This table is
updated below to reflect that: it no longer describes their file changes
as expected/future, and it no longer treats them as a live collision risk
for this package. It still exists so that (a) this package's own file
choices are recorded accurately, and (b) any future Task 004 gate/
implementation session knows which files carry standing sensitivity
(e.g., `research-handoff.md`, the MBQ register) regardless of which
specific session last touched them.

| File | Touched by (historical) | Why it's sensitive |
| --- | --- | --- |
| `docs/05-qa/task-003-validation-results.md` | Static/offline Task 003 validation sweep (PR #110, merged) added a static/offline addendum; the Fable/OAuth experiment (PR #109, merged) added a §8 continuation entry before it | Both already landed cleanly, in sequence (PR #109 merged first, PR #110 merged on top and preserved PR #109's content unchanged, per PR #110's own test plan). **This preflight package did not touch it, in either the original session or this revision.** |
| `docs/04-decisions/shopify-token-acquisition-decision-brief.md` | Fable/OAuth experiment (PR #109, merged) — added the §10a continuation-attempt section | Already landed. **This preflight package did not touch it, in either the original session or this revision.** |
| `docs/01-research/research-handoff.md` | Both PR #109 and PR #110 (each prepended its own compact handoff entry per `CLAUDE.md` §12) | High-churn file — prepended-to by nearly every session. **This preflight package did not touch it, in either the original session or this revision**, per this session's own explicit instruction to avoid it unless ChatGPT asks for a handoff entry. |
| `docs/05-qa/task-003-manual-validation-checklist.md` | Not touched by PR #110 in the end (its wording clarification landed earlier, in PR #107) | No longer an active collision concern for this package. |
| `docs/05-qa/task-003-static-validation-sweep.md`, `task-003-no-side-effect-baseline.md`, `task-003-server-log-redaction-check.md` | New files added by PR #110 (merged) | Background evidence this package's §1/§2 now cites; not edited by this package. |
| `docs/05-qa/technical-debt-register.md` | Not touched by PR #109, PR #110, or this package | TD-001 lives here; a future TD-001 routing decision (§4 item 3 above) would edit this file — still not this preflight package's place to do so. |
| `docs/03-architecture/master-blueprint-open-questions.md` | Reserved for ChatGPT-reviewed MBQ closure notes only | MBQ-05/MBQ-06 rows should only be edited by a session ChatGPT has explicitly authorized to record a closure — not touched by PR #109, PR #110, or this package. |
| `docs/07-implementation-plan/task-004-*.md` (this package) | This session (original draft + this revision) only | A future Task 004 gate-opening session should treat these as background material to read, not necessarily to edit in place — a gate-opening act should be its own new document, following the `task-00X-*-gate.md` precedent, rather than rewriting this preflight package's status in place. |
| `docs/06-prompts/task-004-candidate-claude-prompts.md` (this package) | This session (original draft + this revision) only | Draft-only prompts; a future authorized Task 004 session should treat these as a starting point, not a binding spec — the binding spec is whatever future `task-004-final-implementation-prompt.md` ChatGPT actually accepts. |
| `docs/05-qa/task-004-quality-gates.md` (this package) | This session (original draft + this revision) only | Generic gate checklist; does not assume Task 004's final scope. |

**No file outside this list, and outside the four files this package
owns, was modified — in the original session or in this revision.**
