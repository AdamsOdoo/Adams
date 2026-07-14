# Task CORE-R2 — Foundation Slice 2B: Session Handoff

> **Status: documentation-only session, complete. THE CODE GATE IS NOT OPEN.**
> No code written, no existing file modified, no PR modified, no gate opened, no
> live validation performed. **SRR-03 remains OPEN.**

**Model:** Opus 4.8. **Date:** 2026-07-14. **Architecture:** AR-047.
**Author:** Claude (execution/research/documentation). **Review/gate:** ChatGPT.

This uses the full handoff format
(`docs/06-prompts/session-handoff-template.md`) because it is a first-of-its-kind
Slice-2B packet whose open questions and adversarial findings are load-bearing.

---

## Session summary

Prepared the file-exact, implementation-ready **Slice 2B** packet: activate the
product and customer importers onto the merged CORE-R2 `execute_business` lease
(Slice 1, PR #156), define the exact change design, the cross-branch integration
strategy across the two frozen domain PRs (#150 customer, #151 product), the
regression + runtime test matrix, the deployed multi-worker/multi-server
validation plan, and the SRR-03 closure criteria. Verified all input state
(SHAs, PR states, working tree) against the live repo/GitHub before writing.

**This session opened no implementation gate and authorized no code.**

## Branch and commits

- **Branch:** `claude/core-r2-slice-2b-packet-l0is3j` (the governance-designated
  development branch; the session brief's "preferred" `claude/core-r2-slice-2b-packet`
  differs only by the session-id suffix — see "What ChatGPT should review").
- **Base:** `Shopify-connector` @ `912801508155c6358e8f5f1a7a0aaf01ae573675`.
- **Commit:** one docs-only commit adding the three files listed below.

## Files created or updated

Created (exactly three; **no existing file modified**):

1. `docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`
   — state verification; product + customer call-site inventory (base and PR-head);
   the required change design (RD-P product, RD-C customer); the cross-branch
   integration strategy (Option A/B/C → recommend B) with a deterministic
   sequence; the two future prompts P (product) and C (customer).
2. `docs/05-qa/task-core-r2-slice-2b-validation-plan.md`
   — the regression + runtime test matrix (M1–M13 per domain); the deployed
   multi-worker/multi-server validation plan (14 assertions, Topology C, ×3
   stability); the SRR-03 closure checklist (C1–C10).
3. `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (this file).

## What changed

New governance documentation only. No code, schema, test, manifest, CI, or
existing doc changed. No PR #150/#151 body or branch touched. No shared handoff,
AR log, risk register, or rejected-approaches log modified (explicitly out of
this session's allowlist).

## Evidence and citations added

All claims are cited to in-repo code (with SHA-named line anchors) or to the
merged CORE-R2 governance docs. Access status: all sources **Accessible** on
2026-07-14 (local working tree + `git show` at PR head SHAs + GitHub PR/issue
metadata). No external web source was needed or used. PR-head code was read via
`git show <SHA>:<path>` without checking out or modifying either branch.

Key verified state: `Shopify-connector` tip `912801508…`; PR #156 merged; PR #150
open/draft @ `10d0034…` (build 34863138, DB `…-34863138`, validated `662e980…`);
PR #151 open/draft @ `e4669aa…` (build 34828304, DB `…-34828304`, validated
`db534f8…`); issue #157 open (separate); working tree clean.

## Assumptions

- **[Assumption]** "Slice 2A" = the disconnect consumer/lifecycle half (controller,
  `disconnecting` state, generation bump, direction-C, `ShopifyQuiescedError →
  skipped` routing) — inferred from the session brief + the merged §5 "Slice 2/3"
  deferral bucket. The docs do not name 2A/2B; ChatGPT ratifies the decomposition
  (packet §0).
- **[Assumption]** The integration target for the migrations is the **PR-head**
  code of #150/#151 (not the base), because Option B branches the activation off a
  `Shopify-connector` that already contains those merged PRs. The change design
  was therefore anchored to both the base and the PR-head versions.
- **[Inference]** Media CDN downloads (`_fetch_image`) are **not** admission-gated
  business calls (tokenless GETs to image URLs), so the quiescence contract does
  not govern them; they run inside the terminal lease under RD-P but need no
  redesign.

## Open questions

- **OQ-1 — `execute_lifecycle` / public-`execute()` removal placement.** The store
  test-connection call and the removal/privatization of public `execute()` are
  coupled in the merged plan to a separate `execute_lifecycle` entry. They are
  **out of Slice 2B** (not business call sites). ChatGPT decides whether they
  belong to Slice 2A, a Slice 2C, or a dedicated task. Affects SRR-03 closure
  item C5.
- **OQ-2 — 2A-before-2B ordering (hard).** After migration,
  `execute_business.__enter__` can raise `ShopifyQuiescedError`; the current merged
  dispatcher routes it to `unknown_system_error`, not `skipped`. The
  `ShopifyQuiescedError → skipped` routing is a Slice 2A item. **Recommendation:**
  Slice 2A (or at least that routing) must land **before or with** Slice 2B, else
  an admission refusal becomes a wrong-tier safety-net retry. Drives the §7.3
  sequence.
- **OQ-3 — product lease shape: per-page (RD-P) vs umbrella.** The product
  importer paginates (N `execute()` calls); `execute_business` is single-call.
  RD-P uses per-page `execute_business` with reconciliation inside the terminal
  page's lease (backed by analysis §6 Phase C). An alternative "umbrella
  first-page lease + nested per-page contexts" keeps a lease continuously held
  across the whole fetch. **Recommendation: RD-P** (simpler, §6-backed,
  fail-closed). ChatGPT ratifies RD-P vs umbrella before Prompt P executes,
  because it shapes the pagination method.
- **OQ-4 — integration-base drift on the product spec.** The merged analysis §9.3
  product-migration spec targets the **base** single-call site (`:213`); PR #151
  replaced it with a multi-page loop. The product migration must be re-derived
  against the PR #151 head (RD-P), not applied per the stale §9.3 single-wrap.
  ChatGPT should note that §9.3 is stale for the product domain.
- **OQ-5 — `flush_all()` exactness.** RD-P/RD-C recommend `self.env.flush_all()`
  inside the context to make reconciliation durable-in-transaction before lease
  release. The implementing session confirms the exact Odoo 19 flush call and
  that it is not redundant with `_apply_import`'s own savepoint. (Recommendation,
  not a blocker.)

## Risks

- **Scope risk:** the product migration is **not** a one-line swap (multi-page
  loop + terminal-lease reconciliation). Prompt P must resist touching matching/
  pricing/media logic; the allowlist and static guards enforce call-site-only.
- **Ordering risk:** activating 2B before 2A yields wrong-tier `ShopifyQuiescedError`
  handling (OQ-2) and non-firing generation gate (dormant until 2A). Both call
  sites should be validated against the integrated 2A+2B tree.
- **Evidence-staleness risk:** any edit to PR #150/#151 invalidates their current
  exact-head evidence; Option B avoids editing them and produces one fresh
  integrated validation instead.
- **Drift risk:** cherry-picking or double-applying a shared CORE-R2 commit
  (Option C) would duplicate history; Option B eliminates it by branching from one
  moving `Shopify-connector` tip.

## Adversarial findings (self-review §10 of the brief)

Each potential defect was checked against the actual code; the design was
corrected where needed.

- **AF-1 — Lease ending before reconciliation?** No. RD-P/RD-C place
  `_apply_import` + `flush_all` **inside** the `execute_business` context (terminal
  page for products); `__exit__` releases only after the body returns. The
  inter-page gap in RD-P holds no lease but does **no reconciliation and no write**
  there (accumulation is in-memory), so nothing durable is exposed lease-free.
- **AF-2 — Missing `job` thread-through?** Checked both domains at both SHAs. At
  the PR heads, **both** handlers already pass `job` and both entry methods already
  accept it (product `import_product_sync(store, gid, job=None)` @ `e4669aa:198/2050`;
  customer @ `10d0034:96/526`). Only the base product importer lacks it (`912801:198/727`);
  since Option B targets the heads, no new parameter is needed — only passing the
  existing `job` into `execute_business`. Recorded as a fact, not a defect.
- **AF-3 — Hidden second API call?** The product importer performs media CDN
  downloads (`_fetch_image`) — but these are tokenless GETs to image URLs, not
  credentialed Admin-API business calls, so they are not "second Shopify business
  calls." They are excluded from admission gating by design and asserted
  leak-free (validation M13). The **real** multiplicity is the per-page pagination
  loop, handled explicitly by RD-P (per-page `execute_business`).
- **AF-4 — Product/customer behavior redesign?** None. RD-P/RD-C change only the
  transport/lease boundary + `job` pass-through; matching, pricing, attribute/
  variant generation, media behavior, customer resolution, duplicate prevention,
  and bindings are untouched. M11/M12 re-run all domain classes to prove it.
- **AF-5 — Double application of CORE-R2 commits?** Avoided. Option B branches the
  activation off a `Shopify-connector` that already contains Slice 1 (merged) +
  Slice 2A + both domain PRs; no CORE-R2 commit is cherry-picked onto two
  branches. Option C (cherry-pick/hybrid) is explicitly rejected for this reason.
- **AF-6 — Branch-history contamination?** Avoided. No edits to PR #150/#151
  branches (they keep their evidence intact); the activation lands in fresh
  single-domain PRs off `Shopify-connector`; the deterministic sequence branches
  every step from one moving base, never from a sibling feature branch.
- **AF-7 — Stale validated-SHA assumption?** Guarded. The packet mandates fresh
  exact-head Odoo.sh evidence on any branch that receives the migration (packet §6,
  validation §1.4); the existing `db534f8`/`662e980`/`c0d4559` evidence is treated
  as valid **only** for the un-activated PR heads, never carried onto activated code.
- **AF-8 — Test-only proof mistaken for deployed proof?** Separated. §1 (matrix)
  is unit/`TransactionCase`+independent-connection regression; §2 is the
  **deployed** multi-worker/multi-server proof (Topology C, distinct PIDs,
  `pg_stat_activity`, ×3 stability). SRR-03 closure (C4) requires the deployed
  proof, not the unit matrix.
- **AF-9 — Live Shopify claim?** None. Every test/plan fakes only the `_send`
  seam; live/dev-store read-only validation is a separate, later, explicitly-gated
  activity (C10), blocked until the deployed proof is green and SRR-03 is closed.
- **AF-10 — Token / PII logging?** Guarded. M13 asserts lease rows are secret-free
  (`store_id/lease_key/job_id(Integer)/worker_ref/admitted_at/expires_at` only),
  redaction on error paths, media bytes never logged, and the customer §8.2
  candidate `technical_detail` shape unchanged (no new PII).
- **AF-11 — Giant combined session?** Avoided. Prompts P and C are independent,
  single-domain, disjoint-file sessions with independent PRs and rollback; the
  integration analysis shows the two branches are safe to separate.
- **AF-12 — Accidental implementation authorization?** None. Every file carries
  the "CODE GATE IS NOT OPEN / SRR-03 OPEN / documentation only" banner; the two
  prompts are explicitly GATED and paste-ready for a **future** authorized session.

**Correction applied during review:** the initial framing of the product
migration as a "single structural wrap" (per the merged §9.3) was corrected to
the multi-page RD-P design after reading the PR #151 head, and the
integration-base-drift finding (OQ-4) was surfaced.

## Learning feedback loop

*(Captured here per `CLAUDE.md` §12; the shared `quality-feedback-loop.md` and
`research-handoff.md` were intentionally NOT modified — see "What ChatGPT should
review".)*

- **New issues discovered:** the merged analysis §9.3 product call-site spec is
  **stale** vs the PR #151 head (base assumed a single `execute()`; the head
  paginates). Cross-slice ordering (2A-before-2B) is a hard dependency the merged
  docs under-specify for the activation slice.
- **Repeated issue patterns:** "documentation anchors written against the base
  drift when a parallel PR rewrites the same method" — the same class of drift the
  project has seen before (base vs PR-head anchors). Guard: always anchor
  migration specs to the integration-target head, not the base.
- **Rules/checklists updated:** none modified this session (allowlist forbids it);
  **recommended** rule for ChatGPT to adopt: "a call-site migration packet must
  cite both the base and every open-PR-head version of the target method, and flag
  drift."
- **New rejected approaches:** Option C (cherry-pick/hybrid integration) —
  recommended for the rejected-approaches log with revisit condition "only if the
  two domain PRs cannot be merge-authorized before activation." (Not logged here;
  allowlist forbids editing that file.)
- **New technical debt:** none introduced (no code).
- **Architecture concerns:** the single-call `execute_business` contract does not
  natively express multi-page fetch under one lease (OQ-3); resolved for now by
  §6 Phase C per-page re-admission, but ChatGPT should ratify.
- **Tests or review gates needed:** the M1–M13 activation matrix and the §2
  deployed proof; a static guard that no business path reaches `api.client.execute(`.
- **Should future prompts change? Yes** — Prompt P must be written against the PR
  #151 head (multi-page), not the base; Prompt P/C must require Slice 2A present in
  the tree under test.

## What ChatGPT should review

1. **Ratify the Slice 1 / 2A / 2B decomposition** and the naming (packet §0).
2. **Ratify OQ-3 (RD-P per-page vs umbrella lease)** before Prompt P is authorized.
3. **Confirm OQ-2 ordering** (Slice 2A / its `ShopifyQuiescedError → skipped`
   routing lands before or with Slice 2B).
4. **Decide OQ-1** (`execute_lifecycle` + public-`execute()` removal placement).
5. **Approve Option B** integration strategy and the §7.3 sequence, or direct
   otherwise.
6. **Governance deviations to bless:** (a) this session did **not** update the
   shared `research-handoff.md` or run/record the shared `quality-feedback-loop.md`
   review, because the session allowlist is exactly the three new files and forbids
   modifying existing files — this conflicts with `CLAUDE.md` §12's shared-handoff
   rule; raised here rather than silently resolved. (b) The branch used is the
   designated `claude/core-r2-slice-2b-packet-l0is3j`, not the brief's "preferred"
   `claude/core-r2-slice-2b-packet` (suffix only). Confirm both are acceptable or
   direct a follow-up.

## Recommended next session

**Slice 2A** completion/review (the disconnect consumer/lifecycle half) — it is
the prerequisite for both Slice 2B activations and for any meaningful multi-worker
proof (OQ-2, packet §7.3 step 1). After Slice 2A merges and PR #150/#151 are
merge-authorized, run **Prompt P** and **Prompt C** (packet §8/§9) as two
independent, single-domain authorized sessions.

## Stop confirmation

Work stopped at the documentation boundary. No code was written; no existing file
was modified; no PR was modified; no implementation gate was opened; no live
Shopify validation was performed; **SRR-03 remains OPEN.** Awaiting ChatGPT
review.

---

## Exact next-session prompt (paste-ready, for after ChatGPT ratifies)

```text
You are Claude Code preparing/reviewing CORE-R2 Foundation Slice 2A (the
disconnect consumer/lifecycle half) for the Odoo 19 Shopify Connector. This is
still gated: do NOT open the Slice 2B code gate.

Read first: CLAUDE.md; docs/03-architecture/disconnect-quiescence-remediation-analysis.md
(§6, §8, §9.2, §10, §13, §14, §16, §23, §24); docs/07-implementation-plan/
task-core-r2-disconnect-quiescence-packet.md; docs/07-implementation-plan/
task-core-r2-slice-2b-callsite-runtime-packet.md and its companion validation
plan + this handoff (for the 2A↔2B dependency, OQ-1..OQ-5, and the Option-B
sequence).

Scope: confirm/prepare the Slice 2A implementation packet — disconnecting state,
two-phase action_disconnect, the store-row update-lock + connection_generation
bump, the _run_disconnect_quiesce controller + cron + POLL_DELAY, direction-C
timed_out/completed finalization + credential clear + lease cleanup, and the
dispatcher ShopifyQuiescedError -> skipped routing. Then define the merge order
(Slice 2A, then PR #151/#150, then Prompt P and Prompt C off the updated
Shopify-connector).

Confirm before any code: (a) Slice 1/2A/2B decomposition ratified; (b) RD-P
(per-page) vs umbrella lease decided; (c) 2A-before-2B ordering; (d)
execute_lifecycle/public-execute() removal placement.

End: run the learning review, update the handoff + validation record, confirm the
quality gate, commit/push to the designated branch, then STOP. Do not open the
Slice 2B code gate or run live Shopify validation.
```

---

## Quality gate confirmation

- [x] Session handoff written (this file — a dedicated Slice-2B handoff; the
      shared `research-handoff.md` was intentionally not modified per the
      allowlist, flagged for ChatGPT).
- [x] Quality feedback loop checked (captured in "Learning feedback loop" above;
      shared `quality-feedback-loop.md` not modified per the allowlist, flagged).
- [x] New learning captured (in this handoff).
- [~] Rejected approach (Option C) — recommended for the shared log; **not**
      logged there this session (allowlist forbids editing that file); flagged for
      ChatGPT.
- [x] No accepted technical debt introduced (no code).
- [x] Repeated-issue pattern (base-vs-PR-head anchor drift) escalated into a
      recommended rule for ChatGPT.

## Sprint checkpoint log

- **CORE-R2 Slice 2B packet (2026-07-14):** wrote the three Slice-2B docs
  (callsite-runtime packet, validation plan, handoff); verified all input state;
  recommended Option B integration + RD-P/RD-C designs; surfaced OQ-1..OQ-5 and
  AF-1..AF-12; opened a docs-only draft PR to `Shopify-connector`. No code, no
  gate, SRR-03 OPEN. Next: Slice 2A.
