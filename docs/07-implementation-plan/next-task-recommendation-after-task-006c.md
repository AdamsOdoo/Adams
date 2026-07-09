# Next Task Recommendation — After Task 006C Closure

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Planning only.
> Does not authorize implementation of any kind — not Task 010, not a
> setup wizard, not token-acquisition code, not a packaging change, not a
> concurrency fix.** Prepared after PR #131 (Task 006C sync-engine core
> skeleton) and PR #132 (Task 006C closure/validation-results docs) both
> merged into `Shopify-connector`, latest merge commit
> `b97df00a4dc6aa109e0485df881efac343feccdb`. This document synthesizes
> already-recorded facts, decisions, and open items from the cited files —
> it does not itself resolve, narrow, or decide any of them. Every claim
> below is either a **[Fact]** (cited, verifiable in this repository),
> a restated **[Decision]**/**[Open question]** (cited from its own
> record), or this document's own **[Recommendation]**/**[Inference]** —
> labelled per `CLAUDE.md` §8. Subject to ChatGPT review, revision, or
> rejection in whole or in part.

---

## A. Current completed state

- **[Fact]** Task 006C's sync-engine core skeleton is merged: PR #131
  ("Task 006C: sync-engine core skeleton (enqueue, dispatch, retry)"),
  merge commit `152b1553fe10c6efcbad75b4eba9cfcd2f101385`, merged into
  `Shopify-connector` 2026-07-09T08:32:33Z. Source:
  [`../05-qa/task-006c-sync-engine-skeleton-validation-results.md`](../05-qa/task-006c-sync-engine-skeleton-validation-results.md) §A–§B.
- **[Fact]** Task 006C's closure/validation-results documentation is
  merged: PR #132, merge commit
  `b97df00a4dc6aa109e0485df881efac343feccdb`, adding
  `task-006c-sync-engine-skeleton-validation-results.md`, architecture-
  review-log row **AR-032**, and a compact `research-handoff.md` entry.
  Both PRs are confirmed `merged: true` via this session's own
  `pull_request_read` calls against `AdamsOdoo/Adams`.
- **[Fact]** The core sync-engine skeleton that exists today, inside
  `shopify_connector_core`, comprises: a job-enqueue service wrapping
  `Job.create()`; an `ir.cron`-driven claim/drain dispatch loop using
  `try_lock_for_update()` per candidate row (Decision A); a
  `job_type -> handler` dict-lookup dispatch-seam registry (Decision B);
  a named, tunable retry scheduler (12 max attempts, 30s base, ×2
  multiplier, 30-minute cap, ±20% jitter, 24-hour window; Decision C);
  duplicate-running guards at creation (`operation_scope_key`) and
  execution (the claim mechanism); state-transition helpers implementing
  DEC-009's semantics; a domain-enabled execution-time gating hook
  (currently a no-op for every shipped `job_type`); and a diagnostic
  `core_dispatch_selftest` job type. Source: validation-results §B.
- **[Fact]** **No domain sync exists yet.** No product, customer, order,
  inventory, or fulfillment sync code of any kind has been written. No
  webhook controller/receiver, no OAuth/token-acquisition code, no setup
  wizard/view/menu/action/wizard file, and no new security/ACL file exist
  beyond the core skeleton's own `AbstractModel`s. Source: validation-
  results §A, §F.
- **[Fact]** Task 006C's own closure record explicitly states this is
  **"core-engine substrate only... not UAT-ready connector functionality,"**
  and that "next implementation work (any domain sync, any further core
  prerequisite, or Product MVP work) must be separately authorized by a
  distinct ChatGPT implementation prompt; this closure record does not
  itself authorize any further implementation." Source: validation-results
  §G.
- **[Fact]** Runtime-validation acceptance for PR #131 rests on a
  **user-provided Odoo.sh green-build confirmation**, not on independently
  observed CI evidence — `pull_request_read get_status`/`get_check_runs`
  for the merged head returned `pending`/empty as of the PR #132 closure
  session, and this session's own re-check (see Validation notes below)
  did not re-query CI, since PR #131/#132 are both already closed/merged.
  Source: validation-results §C.4.

---

## B. Open blockers that must remain open

None of the following are resolved, narrowed, or silently decided by
Task 006C, PR #131, PR #132, or this document. Each is restated here
exactly as its own cited source records it, per `CLAUDE.md` §10 (do not
re-propose a rejected approach) and §8 (do not present an open question as
resolved).

| Blocker | Status | Source |
| --- | --- | --- |
| **Multi-server/concurrent-worker concurrency proof** | Not proven. `try_lock_for_update()` is proven only at the code level via a stubbed test; SRR-03 (disconnect/in-flight-job race), SRR-04 (cron job-acquisition concurrency under real load), and SRR-09 (multi-server/load-balanced coordination) each explicitly require live Odoo.sh / multi-server runtime proof, not source-reading. | [`sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md) SRR-03/04/09; [`task-006c-sync-engine-skeleton-validation-results.md`](../05-qa/task-006c-sync-engine-skeleton-validation-results.md) §F |
| **VAL-B2** | BLOCKED, not passed, not failed. No live Shopify Admin API connection has ever been made or attempted. A staged closure plan exists but requires a human operator with real Shopify Partner/Dev Dashboard access, which no session to date has had. | [`val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) §Status, §1; [`DEC-021-val-b2-deferral-for-task-004.md`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md) |
| **MBQ-05** | Partially routed / open. Branch A (one-store/VAL-B2-evidence use of Custom Distribution) accepted in limited scope only. Branch B (scalable, many-unrelated-customer distribution/auth architecture) remains a separate, unevaluated, gated research/decision task. | [`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) §3.2, §8 |
| **TD-002** | Open. `REQUIRED_MVP_SCOPES` includes `read_fulfillments`, which official Shopify docs indicate governs only the `FulfillmentService` resource, not `Fulfillment`/`FulfillmentOrder` read access. Fix routed to the future fulfillment-domain task or its own small correction task — not fixed by Task 006C. | [`technical-debt-register.md`](../05-qa/technical-debt-register.md) TD-002 row |
| **Fulfillment API model** | Undecided — legacy `Fulfillment` vs. `FulfillmentOrder`-based flow (DEC-011/MBQ-42/MBQ-60). TD-002's correct scope depends on this choice. | [`technical-debt-register.md`](../05-qa/technical-debt-register.md) TD-002; [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q36 |
| **Product first-sync dedup thresholds** | Deferred to Task 010's own future final implementation prompt. MBQ-59's two-tier eligibility/match-confidence gate is accepted at blueprint-policy level; exact thresholds are not fixed. | [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) "Duplicate prevention approach"; [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q37 |
| **Token acquisition for many unrelated customers** | Not fully resolved — same underlying question as MBQ-05 branch B. Public distribution (App Store review, compliance webhooks, Billing API), or another officially-supported scalable route, "must be separately evaluated and accepted by ChatGPT before any implementation work assumes a specific multi-customer distribution mechanism." | [`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md) §3.2 branch B |
| **Lite/Full packaging** | Not finalized. No such concept exists anywhere in the reviewed documentation corpus as its own decided architecture; whether it maps onto the already-accepted per-store domain-enablement-flag mechanism or implies something additional (separate installable module sets, licensing/pricing gates) is unresolved. | [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Blocking Question 6, Q21, Q27; [`DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md) "Explicit non-decisions" |
| **Checkpoint/resume ownership** | Undesigned. Whether cursor-based pagination checkpointing is core-engine-owned or domain-module-owned is undecided. | [`sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md) Q7; [`DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md) "Open questions" |
| **Multi-server concurrency proof (job-claiming mechanism selection)** | No job-claiming concurrency mechanism (`SKIP LOCKED` vs. `lock_for_update()` vs. advisory locks vs. a combination) is finally selected beyond Task 006C's own stubbed-tested implementation choice; DEC-025 names this explicitly as not decided. | [`DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md) "Explicit non-decisions" |

This document adds no new blocker and closes none of the above.

---

## C. Candidate next tasks

Five candidates, compared on: what work is actually docs-only-executable
right now (no live Shopify/Odoo.sh access required), what it depends on,
and its risk profile.

| Candidate | What it would produce | Blocked on external access? | Depends on | Risk if deferred | Risk if started now |
| --- | --- | --- | --- | --- | --- |
| **1. Core operational validation / runtime-proof follow-up** | A concurrency-validation *plan* document (mirroring `val-b2-closure-plan.md`'s pattern) specifying exact preconditions, multi-server test topology, and pass/fail evidence criteria for SRR-03/SRR-04/SRR-09 against the just-merged `_claim_for_dispatch()`/`try_lock_for_update()` mechanism. The live test itself still requires a human operator with multi-server Odoo.sh access — not executable from this session. | Plan: no. Execution: yes. | Task 006C merged (done). | Every future domain job (product, order, inventory, fulfillment) will run through this exact unproven claim mechanism — a defect found later is far more expensive to isolate and fix once dozens of job handlers depend on it. | Low — docs-only, no code. |
| **2. Setup/configuration UX planning** | Further planning-only refinement of the setup wizard's screens/flow, building on `setup-ux-principles.md` and `ui-ux-implementation-task-map.md`. | No (planning), but the UI implementation gate is still closed, and the wizard's actual mechanics depend on the still-open MBQ-05 branch B / token-acquisition architecture — planning ahead of that risks having to redo the flow once distribution architecture is decided. | UI implementation gate (closed); MBQ-05 branch B (open) for the OAuth-connect step specifically. | Wizard planning is not urgent — no UI gate is open yet, so no wizard code is at risk of being written on a stale plan. | Medium — could produce planning detail that has to be revised once MBQ-05 branch B is decided (the OAuth-connect screen's shape depends directly on which distribution architecture is chosen). |
| **3. Product MVP Task 010 preparation** | Resolving MBQ-55 (exact model/field names for product-template/variant binding) and tightening `task-010-product-import-proposed.md` toward `CLAUDE.md` §9 precision. | No (planning), but Task 010 itself cannot start regardless — it is also blocked on the not-yet-defined "product domain gate" (`ui-ux-implementation-task-map.md` Group 10), whose own triggering conditions are not specified in any research note. | MBQ-55 naming/schema pass; product domain gate (undefined trigger); Task 002–005 (already merged) and Task 006 (merged, this closure). | Low on its own, but see §E — the closer this planning gets to §9 precision, the stronger the pull to start implementation before the harder cross-cutting questions (packaging, distribution, concurrency) are settled. | Medium — see §E. |
| **4. Token acquisition / auth-distribution planning** | A dedicated research/decision task addressing MBQ-05 branch B: whether Public distribution (App Store review, compliance webhooks, Billing API per `shopify-token-acquisition-research.md` §9) or another officially-supported route is the right many-unrelated-customer mechanism — explicitly named in DEC-023 §3.2 as "a distinct, not-yet-scoped research/decision task." | No — pure research against official Shopify documentation, same shape as the work that already produced DEC-023. | DEC-023 (existing baseline, extends it); does not depend on VAL-B2 or live access. | This question has been "not yet scoped" across multiple sessions (DEC-023, DEC-025 both restate it as open) while more planning/implementation accumulates on top of an unresolved distribution assumption. | Low — docs-only, no code; directly informs Lite/Full packaging (candidate 5) since both hinge on the same distribution-mechanism question. |
| **5. Lite/Full packaging planning** | A research/decision document defining whether "Lite/Full" maps onto the existing per-store domain-enablement-flag mechanism or is a separate product-packaging concept (separate installable module sets, licensing/pricing gates), per Blocking Question 6 in `sync-engine-open-questions.md`. | No — largely a repo-internal product-strategy question, though it may also need to reference the same Shopify distribution-method documentation as candidate 4. | Overlaps heavily with candidate 4 (MBQ-05 branch B) — the "who can install this and how" question and the "what do they install" question are closely coupled. | Continues to leave every future task spec (Task 010 onward) unable to state whether it must account for a "Lite" subset — a gap the mvp-domain-implementation-sequence.md sequencing document already flags as unresolved. | Low — docs-only, no code. |

---

## D. Recommended next task

**Recommended: Candidate 1 — Core operational validation / runtime-proof
follow-up, scoped narrowly to drafting a multi-server/concurrent-worker
concurrency *validation plan* for the Task 006C job-claim mechanism.**

**This is a [Recommendation], not a decision — subject to ChatGPT review,
revision, or rejection.** It does not authorize implementation, does not
authorize the live concurrency test itself, and does not write a final
`CLAUDE.md` §9 implementation prompt. If accepted, the concrete next
Claude session (§F below) would be limited to *drafting the plan document
itself* (mirroring how `val-b2-closure-plan.md` was drafted before any
execution) — the actual live multi-server test remains a distinct,
separately-authorized, execution-only session requiring real Odoo.sh
infrastructure this environment does not have.

**Justification:**

1. **It is the highest-severity unresolved risk sitting directly on code
   that already merged**, not on a hypothetical future domain module.
   `_claim_for_dispatch()`/`try_lock_for_update()` is live in
   `Shopify-connector` today; every future domain job (product, customer,
   order, inventory, fulfillment) will execute through this exact
   mechanism. SRR-03, SRR-04, and SRR-09 all independently conclude the
   underlying concurrency assumption is a **source-backed inference, not
   a proven fact**, and all three explicitly require live runtime proof —
   not further reading — to resolve (`sync-engine-risk-register.md`).
2. **This project has direct, already-recorded precedent for exactly this
   failure mode.** SRR-06 and `DEC-024` §4's "lessons learned" both cite
   PR #121's `credential.write_date` freshness-guard defect as a
   concurrency/timing-dependent bug that "passed every static and
   adversarial review across three revisions and was only caught by live
   Odoo.sh execution." DEC-025's own acceptance note restates: "no
   concurrency claim is treated as proven, and live Odoo.sh/multi-server
   runtime proof is still required before any implementation relies on
   one." Choosing to build further (domain sync, or even setup UX that
   assumes reliable job dispatch) before this proof exists repeats a
   pattern this project has already been burned by once and explicitly
   flagged against repeating.
3. **It is fully docs-only-executable right now**, unlike VAL-B2/MBQ-05
   branch A (which require a human operator with real Shopify Partner
   account access this environment does not have). A concurrency
   validation *plan* — preconditions, exact multi-server test topology,
   what to observe, pass/fail evidence criteria — can be drafted the same
   way `val-b2-closure-plan.md` was drafted before any execution, without
   touching code.
4. **Deferring it costs more the longer domain-sync planning/
   implementation accumulates on top of it.** A defect discovered after
   Task 010–014 are all built against this claim mechanism is far more
   expensive to isolate than one discovered now, while only the core
   skeleton depends on it.

**Close second / parallel candidate:** Candidate 4 (token acquisition /
auth-distribution planning, MBQ-05 branch B) is also fully docs-only-
executable now and has been "not yet scoped" across multiple sessions
(DEC-023 §3.2, DEC-025 "Explicit non-decisions"). It does not compete for
the same evidence/access constraints as Candidate 1 and could reasonably
run as a separate, parallel planning track if ChatGPT prefers to
prioritize it first, or alongside Candidate 1. This document does not
rank it below Candidate 1 on merit — only on the basis that Candidate 1
sits on already-merged, already-load-bearing code with a project-specific
precedent of exactly this kind of defect slipping past static review.

**Not recommended as the immediate next task:** Candidate 3 (Product MVP
Task 010 preparation) — see §E for why starting to firm up product-domain
task-spec precision now, ahead of Candidates 1 and 4, carries avoidable
rework risk. Candidate 2 (setup/config UX planning) is not recommended
next either, for the same reason: its OAuth-connect screen's shape
depends directly on the still-open MBQ-05 branch B decision.

---

## E. Risks of choosing product implementation too early

If Product MVP domain-sync implementation (Task 010 or any other domain
area) were authorized to start before the blockers in §B are addressed,
the following concrete failure modes could result. This section is
**[Inference]**, reasoned from the cited evidence, not a proven prediction.

- **Building domain sync on an unproven concurrency mechanism compounds
  the blast radius of a later-discovered defect.** Every domain job type
  (product import, order import, inventory push, fulfillment write-back)
  would be dispatched through the same `_claim_for_dispatch()`/
  `try_lock_for_update()` mechanism SRR-03/SRR-04/SRR-09 flag as unproven
  under real concurrent-worker or multi-server execution. If a live test
  later reveals the claim mechanism does not safely prevent double-
  processing under real load, every domain module built on top of it
  would need re-validation, and in the worst case, the domain
  binding/idempotency layer itself might need rework to compensate —
  precisely the "defect discovered only after significant implementation
  effort" scenario SRR-06 already warns against.
- **Product/customer/order sync assumes an auth/distribution shape that
  is not yet decided.** MBQ-05 branch B (many-unrelated-customer
  distribution) and Lite/Full packaging remain open. If domain-sync code,
  its tests, or its setup/readiness assumptions implicitly bake in an
  auth model (e.g., assuming any customer can simply paste a token, or
  assuming a single vendor-owned app installs across all customers) that
  is later found incompatible with whichever distribution architecture
  ChatGPT eventually accepts, that code would need to be revisited or
  reworked — not because the domain logic itself was wrong, but because
  it was built on an assumption the project had explicitly not yet
  settled.
- **VAL-B2 still has never passed.** No live Shopify Admin API connection
  has ever been made. Domain sync code that has only ever been exercised
  against fakes/stubs (as Task 006C's own tests were, per the fake-
  handler-signature defect found during its real-runtime validation) risks
  the same category of defect Task 006C itself already encountered once —
  a signature/behavior mismatch between test doubles and real Shopify
  response shapes that only surfaces once a genuine API call is made.
  Building more sync logic before even one live connection has succeeded
  multiplies the surface area that first live test would need to validate
  at once.
- **The fulfillment API model and TD-002 are both open, and Product
  Task 010 sits upstream of order, inventory, and fulfillment in the
  accepted sequencing** (`mvp-domain-implementation-sequence.md`).
  Starting product-domain work does not itself require the fulfillment
  question to be answered, but treating "Task 010 prep" as the unblocked
  next step risks creating momentum toward the domain sequence overall
  before the harder downstream questions (fulfillment API model, product
  first-sync dedup thresholds) have anywhere near the same rigor applied
  to them that Task 006C's own concurrency questions still lack.
- **Repeating a scope-creep pattern this project's own governance exists
  to prevent.** `CLAUDE.md` §5 requires an explicit ChatGPT gate-opening
  act and a separate final task prompt before any domain code is written;
  §6 requires small, scoped sessions. A session that starts "preparing"
  Task 010 in earnest (resolving MBQ-55, tightening acceptance criteria)
  without also confirming the cross-cutting prerequisites are being
  actively worked risks exactly the kind of quiet forward-rolling this
  project's own quick-start checklist warns against.

None of this asserts product implementation *will* fail if started early
— only that the cited open items are the specific, evidence-backed
mechanisms by which starting early could force rework, and that this
project has direct precedent (PR #121, SRR-06) for exactly the
concurrency-defect variant of this risk.

---

## F. Proposed next Claude session

**Recommended next-session objective — docs-only:**

> Draft `docs/07-implementation-plan/sync-engine-concurrency-validation-plan.md`
> (or an equivalent `docs/05-qa/` location, mirroring
> `val-b2-closure-plan.md`'s structure): exact preconditions (a multi-
> server/multi-worker Odoo.sh topology sharing one PostgreSQL database, or
> the closest available equivalent); the exact scenario(s) to exercise
> (concurrent `ir.cron` drain workers claiming overlapping
> `shopify.connector.job` rows; a store disconnect racing an in-flight
> business job, per SRR-03); what to observe and record as pass/fail
> evidence for SRR-03, SRR-04, and SRR-09; and what this plan explicitly
> does **not** claim to prove (e.g., it does not resolve MBQ-05, Lite/Full
> packaging, or any domain-sync question). This session does not execute
> the test itself — no live Odoo.sh/multi-server access exists in this
> environment — and does not authorize any code, module, or implementation
> change. It should end with its own mandatory handoff entry per
> `CLAUDE.md` §12, and should explicitly note Candidate 4 (token
> acquisition / auth-distribution planning, MBQ-05 branch B) as an
> available parallel docs-only track ChatGPT may choose to authorize
> instead of, or alongside, this one.

This is the only next-session objective this document proposes. It is
**implementation-gate-only** in the narrow sense that it prepares the
evidence plan a future execution session would need — it is not itself an
implementation task, authorizes no code, and does not open any gate.

---

## Explicit non-authorizations

This document does not:

- Authorize Task 010, any other domain-sync task, a setup wizard, OAuth/
  token-acquisition code, or any Lite/Full packaging implementation.
- Resolve VAL-B2, MBQ-05, TD-002, the fulfillment API model, product
  first-sync dedup thresholds, Lite/Full packaging, checkpoint/resume
  ownership, or the multi-server concurrency proof requirement — every one
  remains exactly as open as its own cited source states.
- Open any implementation gate. The only open gate remains the limited
  core-only, zero-UI gate (`limited-core-implementation-gate.md`), whose
  scope Task 006C's own already-merged skeleton already exhausted for the
  core sync-engine; no further gate is opened by this document.
- Create, modify, or imply authorization for any addon/code, test,
  manifest, XML/security/ACL, migration, CI/workflow, domain module, UI/
  view/menu/action/wizard/controller, webhook, or OAuth file.

---

## Evidence / references

- [`../01-research/research-handoff.md`](../01-research/research-handoff.md) — top entries, Task 006C closure.
- [`task-006c-sync-engine-skeleton-validation-results.md`](../05-qa/task-006c-sync-engine-skeleton-validation-results.md) — access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md) — AR-032 and prior rows — access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md), [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md), [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md) — access: Accessible, this repository, observed 2026-07-09.
- [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md), [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md), [`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md) — access: Accessible, this repository, observed 2026-07-09.
- [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md), [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md), [`final-mbq-closure-plan.md`](./final-mbq-closure-plan.md), [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md), [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md) — access: Accessible, this repository, observed 2026-07-09.
- [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md), [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10, [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) RA-003 — access: Accessible, this repository, observed 2026-07-09.
- GitHub PR #131, #132 (`AdamsOdoo/Adams`) — retrieved via `pull_request_read` this session, 2026-07-09; both confirmed `merged: true`.

**Next step:** ChatGPT review.
