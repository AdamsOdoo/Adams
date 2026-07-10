# Sync Engine — Open Questions and Risks (Task 006A)

> Open questions and risks only — no architecture decision, no
> implementation. Companion to
> [`../01-research/sync-engine-source-inventory.md`](../01-research/sync-engine-source-inventory.md),
> [`../01-research/sync-engine-source-notes.md`](../01-research/sync-engine-source-notes.md),
> and [`../01-research/sync-engine-evidence-map.md`](../01-research/sync-engine-evidence-map.md).
> Every question below either predates this session (restated here for
> completeness, per the task's mandatory-known-items requirement) or was
> surfaced fresh by this session's research — each is marked accordingly.
>
> **Revision note (2):** revision 1 updated this branch against latest
> `Shopify-connector` after PR #123 and PR #124 merged, cross-referencing
> questions 17, 18, and 30 against `docs/01-research/sync-engine-odoo-repo-source-notes.md`
> (PR #124, `R31`, the canonical Odoo/repo-substrate shard). **This
> revision** updates again after PR #126 merged, adding cross-references to
> `docs/01-research/sync-engine-queue-idempotency-source-notes.md` (PR #126,
> `R33`, the canonical queue/idempotency/retry/backoff/dead-letter reference
> shard) against questions 10, 17, and 18, plus four new questions (40–43)
> for topics `R33` surfaced that this package had not previously raised.
> **Numbering note:** existing question numbers 1–39 are preserved unchanged
> (they are cross-referenced by number from the evidence map and risk
> register) — new questions are appended as 40+ within their most relevant
> section rather than renumbering the whole document.
>
> **Status-refresh revision note (3), 2026-07-09 (AR-038 audit session —
> question text below is preserved unchanged; this note records which
> questions later merged work has since answered, each with proof):**
> **Q5 and Q29 (job-claiming/acquisition design) — answered by merged
> implementation:** the Task 006C sync-engine skeleton (PR #131, merge
> `152b155`, AR-031 Decision A, closure AR-032) implements per-row
> `try_lock_for_update()` claim/dispatch in
> `shopify_connector_job_dispatch.py`, validated live (Odoo.sh green;
> AR-032). The single-server design question is settled; the multi-server
> sufficiency question remains open as Q41/Q43 (unchanged — still requires
> live multi-server proof). **Q28 (which DEC-024 next-task candidate is
> selected) — answered by history:** ChatGPT selected the sync-engine
> gate (DEC-025/AR-030), executed through Task 006C and then Task 010
> (PR #131–#138 merge line). **Q37's product-domain instance (first-sync
> dedup thresholds) — closed by Task 010:** the accepted Task 010 final
> prompt fixed the product-domain thresholds and PR #138 merged
> runtime-green; the customer-domain instance of the same MBQ-59 residual
> is now tracked as customer-domain gate criterion 5
> (`../07-implementation-plan/customer-domain-gate-criteria-proposal.md`)
> and `../08-release-readiness/open-points-closure-register.md` OP-10.
> **Q6/Q21/Q27 (Lite/Full), Q4/Q26 (16-vs-17 `@idempotent` count),
> Q10–Q16/Q40 (Shopify behavioral unknowns), Q17/Q18/Q30–Q32/Q41/Q43
> (runtime-proof questions), Q23 (webhook PII field list), and Q36/Q38/Q39
> (domain-task-routed items) remain open, unchanged** — see the
> open-points register rows OP-23, OP-33, OP-34, OP-35, OP-36, OP-20,
> OP-05 for current routing. Blocking Question 1 (MBQ-05) and Blocking
> Question 2 (VAL-B2) remain open exactly as DEC-023/DEC-021 left them.

## Blocking questions before implementation

Questions that must be resolved (by decision, by live proof, or by explicit
routing) before a sync-engine implementation task prompt could safely be
written.

1. **[Pre-existing]** **MBQ-05 remains Partially routed / Open** — the
   scalable, many-unrelated-customer token-acquisition/distribution
   architecture is undecided. A sync engine that assumes any particular
   credential-acquisition shape (beyond the single already-accepted
   `token_variant='offline_custom_app'` seam) would be building on an
   unresolved foundation. *Source:* `master-blueprint-open-questions.md`
   MBQ-05 row (cited, not modified, this session); `DEC-023`.
2. **[Pre-existing]** **VAL-B2 remains deferred / not passed** — no live
   Shopify Admin API connection has been made or attempted by any task to
   date. Any sync-engine design assumption about live Shopify behavior beyond
   what is documented (rather than independently verified against a real
   store) carries this residual risk. *Source:* `DEC-021-val-b2-deferral-for-task-004.md`.
3. **[Pre-existing]** **TD-002 remains Open** — the `read_fulfillments`
   readiness-scope correctness concern is unresolved and depends on which
   fulfillment API model (legacy `Fulfillment` vs. `FulfillmentOrder`-based)
   the fulfillment domain ultimately adopts. A sync engine's readiness-gating
   contract must not assume this scope question is settled. *Source:*
   `technical-debt-register.md` TD-002 row (cited, not modified).
4. **[New this session]** **The 16-vs-17 `@idempotent` mutation count
   discrepancy** between existing repo research (`DEC-009`/AR-006 brief: "17
   mutations") and this session's fresh fetch (Shopify's own page, self-dated
   "last updated 2 February 2026": 16 named mutations) is unresolved. It does
   not block core-engine research (the *concept* — layered, per-mutation
   idempotency — is unaffected), but it must be re-verified before any
   domain-module code hard-codes a specific mutation list. *Source:*
   `sync-engine-source-notes.md` §"Shopify idempotency notes".
5. **[New this session]** **How the future job-drain mechanism acquires
   `shopify.connector.job` rows across concurrent `ir.cron` workers without
   racing** is undesigned. `operation_scope_key`'s unique constraint prevents
   two *conflicting* operations, but nothing in the existing schema yet
   specifies job-*claiming* semantics (e.g. a `SKIP LOCKED`-style acquisition
   analogous to `ir.cron`'s own job-row acquisition, `O7`). This is squarely
   an architecture-gate question, not resolved by this research session.
6. **[New this session]** **"Lite/Full" packaging** — no such concept exists
   anywhere in the reviewed documentation corpus, though the underlying
   domain-enablement *mechanism* (per-store flags, block-new-enqueue-when-
   disabled, never-delete-history) is already accepted and partially
   implemented. Whether "Lite/Full" is meant to map directly onto that
   existing mechanism, or implies something additional (separate installable
   module sets, licensing/pricing gates), is unresolved and should be
   clarified before any implementation assumes either shape.

## Non-blocking questions that can remain deferred

7. **[New this session]** Whether cursor-based pagination checkpointing
   should be **core-engine-owned** (a generic "resume this paginated job from
   its last cursor" primitive) or **domain-module-owned** (each import job
   manages its own cursor state) is undecided — no source in this package
   settles it either way, and it does not block earlier-stage research or
   design work.
8. **[New this session]** Exact `ir.cron`-drain-loop batch size, interval,
   and worker-thread allocation are implementation-planning items (already
   flagged as such by `DEC-005`/`ar-003-sync-orchestration-framing.md`); this
   session adds one new numeric input (the >64-savepoints-per-transaction
   ceiling, `O8`) but does not resolve the batch-size question itself.
9. **[New this session]** Whether/how a future core-engine "channel"-like
   concept (a declarative execution lane + externally-configured capacity,
   mirroring OCA `queue_job`'s pattern, `Q5`) is worth adopting is an
   open, non-blocking design idea — not evaluated to acceptance or rejection
   by this research session.
42. **[New this revision, from `R33`, minor/immaterial]** An unreconciled
    discrepancy on OCA `queue_job`'s minimum worker-count precondition: this
    package's pre-006A baseline (`R25`) cites `--workers > 0`; `R33` (PR
    #126, `OCA-4`) cites `--workers > 1`. Neither shard resolves this. Not
    blocking — `queue_job` remains reference-only (RA-004 unchanged) — but
    worth re-verifying against the live OCA README if `queue_job` is ever
    evaluated in earnest at a future architecture gate.

## Shopify API uncertainties

10. **[New this session, now corroborated by `R33`]** Cursor durability/reuse
    across a paused-and-resumed sync of unspecified length is undocumented
    by Shopify for GraphQL (`S1`, `S2`) — neither confirmed safe nor
    confirmed unsafe. `R33` (PR #126) independently reached the identical
    conclusion via its own separate research pass, and additionally found
    that the **REST** equivalent (`page_info` cursor URLs) *is* explicitly
    documented as temporary/not-for-saving — suggestive context for GraphQL,
    not proof either way.
11. **[New this session]** Whether pagination ordering is stable if the
    underlying dataset mutates between page requests is undocumented.
12. **[New this session]** Whether `partialDataUrl`/`url` populate for a
    `CANCELED` bulk operation (as opposed to `FAILED`) is undocumented — the
    official field descriptions tie both fields' population language to
    `COMPLETED`/`FAILED` states specifically, never `CANCELED` (`S12`).
13. **[New this session]** Whether repeat calls to `bulkOperationCancel` on
    an already-canceling/canceled operation are safe/idempotent is
    undocumented (`S9`).
14. **[New this session]** Whether the `bulkOperationRunQuery`/
    `bulkOperationRunMutation` **start call itself** is safe to blindly
    retry after an ambiguous (e.g. timeout) outcome is undocumented — only
    per-row mutation idempotency and post-failure *query* resubmission
    guidance exist (`S7`, `S8`).
15. **[Pre-existing, re-confirmed unresolved]** The exact per-plan GraphQL
    bucket size (`maximumAvailable`) is not published by Shopify — only
    restore rates are (`R24`, unchanged this session).
16. **[New this session]** Whether Shopify bounds a maximum time window for
    *success-path* duplicate webhook deliveries (as distinct from the
    documented 8-retries-over-4-hours *failure*-triggered retry schedule) is
    undocumented (`S14`).
40. **[New this revision, from `R33`]** A throttled Shopify **GraphQL** call
    can return **HTTP 200** with a `THROTTLED` code in the response body
    rather than a 4xx status (`R33`'s `SH-4`) — a genuinely new fact this
    package had not independently verified before this revision (see
    Mandatory Claim 12 / supplementary row 26 in the evidence map). No
    fetched source (by this package or `R33`) documents a
    `Retry-After`-equivalent signal for GraphQL `THROTTLED` responses
    specifically, leaving open exactly how a client should pace its retry
    beyond deriving a wait time from `throttleStatus`. Related: `R33`
    independently found that vendors **disagree** on how to handle a
    concurrent, still-in-flight duplicate idempotent request — the IETF
    idempotency-key draft recommends HTTP 409, Stripe's documented behavior
    is to not cache a result and tell the client to retry, and Shopify's own
    `IDEMPOTENCY_CONCURRENT_REQUEST` is a third distinct shape — so no
    single vendor's behavior should be assumed as a universal pattern if the
    sync engine ever needs to define its own answer to the same question.

## Odoo concurrency/transaction uncertainties

17. **[New this session, now a three-shard-corroborated question]** Whether
    the Task-005 disconnect-cancellation sweep (`action_disconnect()`) fully
    closes the race against a business job already transitioned to `running`
    inside an in-flight `ir.cron` batch at the exact instant of disconnect
    is **not proven by any source** in this package, in `R31` (PR #124), or
    in `R33` (PR #126) — all three independently inspected related Odoo
    concurrency/locking substrate without resolving this specific race. The
    existing gating blocks a transition *into* `running`, but does not
    itself interrupt a job already past that check. Requires live
    Odoo-runtime proof (see below), not resolved by documentation research
    alone.
18. **[New this session, now a three-shard-corroborated question]** Whether
    `lock_for_update()`/`try_lock_for_update()` (Odoo's `@api.private`
    row-locking primitives, `O9`, independently confirmed by both `R31` and
    `R33`) should be adopted by a future sync-engine's own cron-batch record
    processing is an open design question this research surfaces but does
    not answer. The underlying premise is itself a **source-backed
    inference, not a proven fact**: Odoo's RPC-layer automatic retry
    (`retrying()`, `O5`, `O6`) is source-confirmed for RPC/HTTP dispatch, but
    the `ir.cron` job-processing code reviewed did not show an equivalent
    automatic retry around each domain record-processing step (`O7`) —
    `R31` independently examined `ir.cron`'s job-*acquisition* locking
    specifically (a related but distinct layer) without settling this
    narrower question either; `R33` independently reaches the identical
    "requires an actual concurrency test... to verify the documented intent
    matches real runtime behavior" conclusion, making this a
    **three-shard-corroborated** open question. If the inference holds,
    *some* explicit mechanism (locking, or catch-and-retry, or both) would
    plausibly be needed; which one, and whether the inference is even
    correct, both remain unresolved pending runtime proof.
41. **[New this revision, from `R33`]** Whether the row-lock-only
    (`FOR NO KEY UPDATE SKIP LOCKED`) approach `ir.cron` uses is sufficient
    with **no additional cross-server coordination** when multiple Odoo
    application servers share one PostgreSQL database — `R33` names this a
    real operational pain point worth an explicit runtime test, citing a
    historical GitHub issue referencing load-balanced cron scheduling as
    circumstantial (not conclusive) evidence. Neither this package nor `R31`
    had previously surfaced this specific multi-server framing (both
    focused on single-server multi-worker concurrency). Related: `R33`
    independently researched PostgreSQL advisory locks (`pg_advisory_lock`
    and variants) as an alternative/complementary locking primitive this
    package had not examined — including a documented hazard where an
    advisory-lock call inside a `SELECT ... ORDER BY ... LIMIT` query can
    lock rows before `LIMIT` is applied, and that session-scoped advisory
    locks are not released by a transaction rollback. Whether advisory locks
    are worth considering for a future job-claiming design alongside or
    instead of `lock_for_update()`/`SKIP LOCKED` is undecided — flagged for
    the architecture gate, not resolved here.

## UX/observability uncertainties

19. **[New this session]** Whether the connector should override `ir.cron`'s
    default no-op `_notify_admin()` (log-line-only by default, `O7`) with its
    own alerting, given that the existing job/log dashboard is already the
    real operator-visible failure surface — not evaluated by this session.
20. **[Pre-existing]** Exact user-facing log copy/wording for error reasons
    and suggested fixes remains a UX/operator-flow sprint concern, unchanged
    by this session (`ar006-error-retry-idempotency-decision-brief.md` §7,
    `R10`).

## Lite/Full packaging uncertainties

21. **[New this session]** See Blocking Question 6 above — restated here
    under its own category per the task's required section structure. No
    additional sub-questions surfaced beyond the core ambiguity already
    stated.

## Security/privacy uncertainties

22. **[Pre-existing]** `access_token` is stored plain (not encrypted at
    rest), an already-accepted residual risk (AR-022/AR-024/AR-025) —
    unaffected by and out of scope for this sync-engine research, restated
    here only because a future sync-engine job handler will need to read
    this value via the existing sanctioned `_get_access_token()` path and
    must not introduce a second read path or log it.
23. **[New this session]** Whether webhook payload bodies (which may contain
    customer PII depending on topic/domain) require additional redaction
    rules beyond the existing generic `redact()` helper before being written
    into `job.log.payload_snapshot` is not evaluated by this session — the
    existing redaction pattern (`R2`) is confirmed structurally sound
    against OWASP's general guidance (`E9`), but no domain-specific PII
    field list has been reviewed (out of scope — no domain sync exists yet).

## Testing uncertainties

24. **[New this session]** Whether a future sync-engine job-drain loop test
    should use `TransactionCase` (per-method savepoint, matching the existing
    convention, `R6`, `O2`) or a heavier integration harness once concurrent
    `ir.cron` worker behavior needs exercising (which `TransactionCase`'s
    single-transaction model cannot realistically simulate) is unresolved —
    flagged for the future test-strategy design, not decided here.
25. **[Pre-existing]** The distinction between (a) no-network unit tests, (b)
    Odoo.sh live-runtime tests (already the established pattern for Tasks
    001–005, per `R18`), and (c) live-Shopify VAL-B2-style validation (still
    deferred) is confirmed as three genuinely separate tiers by this
    session's research (see evidence-map claims 15–16) — no new ambiguity
    surfaced, restated for completeness.

## Questions that require a ChatGPT decision

26. Whether/how to route the 16-vs-17 `@idempotent` mutation-count
    discrepancy (Blocking Question 4) — re-verify and correct the existing
    DEC-009/AR-006 citation, or treat as immaterial until domain
    implementation.
27. Whether "Lite/Full" packaging (Blocking Question 6) is a restatement of
    the existing domain-enablement-flag mechanism or a genuinely new product
    concept requiring its own architecture question.
28. Which of the four DEC-024 §5 "next task candidates" — sync-engine
    skeleton gate, setup/readiness UX docs gate, manual product import
    architecture gate, or VAL-B2/token validation closure gate — is selected
    next; this session's research supports (but does not select) the
    sync-engine-skeleton-gate candidate specifically, per its own scoping
    prompt.
29. Whether the future job-drain concurrent-acquisition design (Blocking
    Question 5) should reuse Odoo's `lock_for_update()`/`SKIP LOCKED`
    pattern, a variant of it, or a different mechanism entirely — an
    architecture-gate decision, not a research finding.

## Questions that require live Odoo.sh proof

> Three independently-produced research shards — this package, `R31` (PR
> #124), and `R33` (PR #126) — now converge on the same conclusion for
> questions 30 and 41: Odoo 19's cron-acquisition/locking mechanics have
> only ever been confirmed by reading source and documentation comments,
> never by an observed concurrency test.

30. **[New this session]** Whether the disconnect/in-flight-job race
    (Blocking Question 5 / Open Question 17) is a real, exploitable
    condition under actual concurrent `ir.cron` worker execution, or is
    closed in practice by transaction/savepoint timing — no static or
    source-level analysis in this package, `R31`, or `R33` resolves it.
31. **[New this session]** Real-world behavior of `_commit_progress()` /
    `CompletionStatus` interacting with a per-record-savepoint batch loop at
    scale approaching (or exceeding) the documented 64-savepoint performance
    ceiling (`O8`) — only the documentation warning is confirmed, not its
    practical throughput impact on this connector's actual record volumes.
32. **[Pre-existing pattern, reaffirmed]** Per `DEC-024`'s own "lessons
    learned" section (`R18`), this project has direct precedent (PR #121) of
    a defect (`credential.write_date` freshness-guard brittleness) that
    passed every static/adversarial review across three revisions and was
    only caught by live Odoo.sh execution. Any future sync-engine
    concurrency/locking design carries the same category of risk and should
    not be considered validated until proven live.
43. **[New this revision, from `R33`]** Whether `ir.cron`'s row-lock-only
    acquisition (Open Question 41) holds with no additional cross-server
    coordination when multiple Odoo application servers share one
    PostgreSQL database can only be settled by an actual multi-server test
    — source-reading alone cannot resolve it, per `R33`'s own explicit
    framing.

## Questions that require live Shopify proof

33. **[Pre-existing]** VAL-B2 itself (Blocking Question 2) — no live
    connection has been attempted.
34. **[New this session]** Real-world cursor-reuse-after-a-pause behavior
    (Open Question 10) and real-world duplicate-webhook timing beyond the
    documented failure-retry schedule (Open Question 16) can only be
    confirmed against a real store's actual behavior, since Shopify's own
    documentation is silent on both.
35. **[New this session]** Real-world behavior of `partialDataUrl`/`url` for
    a `CANCELED` bulk operation (Open Question 12) can only be confirmed by
    actually running and canceling a bulk operation against a live store.

## Questions that require later domain-specific tasks

36. **[Pre-existing]** **Fulfillment scope/API model cannot be finalized
    yet** — TD-002's `read_fulfillments` scope-correctness concern and the
    underlying legacy-`Fulfillment`-vs-`FulfillmentOrder` API model choice
    (DEC-011/MBQ-42/MBQ-60) remain undecided; a future fulfillment-domain
    task must resolve both before its own implementation.
37. **[Pre-existing]** **Product first-sync deduplication still requires
    domain design** — MBQ-59's exact eligibility-check/match-confidence
    thresholds (Mandatory Claim 17) are deferred to Task 010's own future
    final implementation prompt.
38. **[Pre-existing]** **Token acquisition architecture is not fully
    resolved for many unrelated customers** — MBQ-05's branch-B
    (scalable, many-unrelated-customer distribution/auth architecture)
    remains a separate, not-yet-scoped research/decision task per `DEC-023`
    §3.2.
39. **[New this session]** Whether/when Bulk Operations get adopted for
    first-sync product import (Mandatory Claim 14) is deferred to the
    product-import domain task, informed by but not decided by this
    session's mechanics research (no-partial-resume recovery model,
    per-row-only idempotency scoping).
