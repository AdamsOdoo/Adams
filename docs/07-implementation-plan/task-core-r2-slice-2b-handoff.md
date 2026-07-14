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

## Session summary

**Revision 2 — correction session** driven by control-room review
**`4690659767` (REVISE)** on PR #158. Revision 1 built the Slice-2B packet
(call-site inventory, change design, integration strategy, test matrix,
multi-worker plan, SRR-03 closure). Revision 2 corrects five defects the review
identified, in the three existing packet files:

1. **Rejected the direct-merge "Option B"** (which merged PR #150/#151 into
   `Shopify-connector` *before* protecting their unguarded `execute()` call
   sites — reversing the gate) and replaced it with an **eight-step
   integration-staging strategy** (packet §7).
2. **Made RD-P structurally executable** — the pagination loop **itself owns each
   `execute_business` context**; the `_execute_query` helper that returned
   `result` is dissolved; no API result escapes its context before reconciliation
   (packet §5.1).
3. **Corrected flush semantics** — `flush_all()` materializes SQL in the main
   transaction; it does **not** commit and does **not** create cross-transaction
   durability; no explicit main-cursor commit (packet §5, §5.3; validation M15).
4. **Resolved the public-`execute()` closure** into Slice 2B as a final
   integration step (packet §6b; Prompt E, §9c), given Slice 2A / PR #160 now
   delivers `execute_lifecycle`.
5. **Rebased future Prompts P/C on the staging branch** and added **Prompt E**
   (packet §8/§9/§9c; validation plan §1.0/§1.4/§2/§3).

**This session opened no implementation gate and authorized no code.**

## Branch and commits

- **Branch:** `claude/core-r2-slice-2b-packet-l0is3j` (the governance-designated
  development branch; the brief's "preferred" `claude/core-r2-slice-2b-packet`
  differs only by the session-id suffix — see "What ChatGPT should review").
- **Base:** `Shopify-connector` @ `912801508155c6358e8f5f1a7a0aaf01ae573675`.
- **Commits:** Revision 1 = `df7118a` (three files created); Revision 2 = one
  docs-only correction commit editing the same three files. PR #158 stays
  open/draft/unmerged throughout.

## Files created or updated

The **same exact three files** (no additional file created or modified):

1. `docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`
   — state verification; product + customer call-site inventory (base and PR-head);
   change design (RD-P **loop-owned**, RD-C); **integration-staging strategy**
   (§7, 8 steps); public-`execute()` closure design (§6b); future prompts **P, C,
   and E**.
2. `docs/05-qa/task-core-r2-slice-2b-validation-plan.md`
   — regression + runtime test matrix (M1–M18 per domain); deployed
   multi-worker/multi-server plan (14 assertions, Topology C, ×3 stability), on
   the integration-staging head; SRR-03 closure checklist (C1–C10).
3. `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (this file).

## What changed (Revision 2)

New/corrected governance documentation only. No code, schema, test, manifest, CI,
or non-allowlisted doc changed. **No PR #150, #151, or #160 body or branch
touched.** No shared handoff, AR log, risk register, or rejected-approaches log
modified (explicitly out of this session's allowlist).

## Evidence and citations added

All claims cited to in-repo code (SHA-named line anchors) or the merged CORE-R2
governance docs. Access status: all sources **Accessible** on 2026-07-14 (local
working tree + `git show` at PR head SHAs + GitHub PR/issue/review metadata). No
external web source used.

Verified state this session: PR #158 open/draft @ `df7118a`, base `912801508…`,
exactly 3 files; PR #150 open/draft @ `10d0034…`; PR #151 open/draft @ `e4669aa…`;
**PR #160 (Slice 2A) open/draft @ `b3d23cb…`, no runtime-green claimed
(static-only)**; issue #157 open (separate); working tree clean. Review
`4690659767` (REVISE) read in full.

## Assumptions

- **[Fact — now confirmed]** "Slice 2A" is PR #160 (disconnect controller,
  `disconnecting` state, generation bump, direction-C, `execute_lifecycle`). PR
  #160's body states it **removes neither the public `execute()`** and claims **no
  runtime-green** (static validation only).
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
  2A/PR #160 supplies `execute_lifecycle` and migrates `action_test_connection`;
  Slice 2B removes the public `execute()` after both call sites migrate. Satisfies
  closure item C5.
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
  public surface becomes exactly `{execute_business, execute_lifecycle}`; the
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

**Corrections applied this revision:** rejected Option B; rewrote §7 as the
integration-staging strategy; rewrote RD-P for loop-owned context ownership and
withdrew the umbrella alternative; corrected all flush wording; added §6b and
Prompt E resolving the public-`execute()` closure; rebased Prompts P/C on the
staging head; added validation matrix rows M14–M18 and reframed §1.4/§2/§3 to the
integration-staging head.

## Learning feedback loop

*(Captured here per `CLAUDE.md` §12; the shared `quality-feedback-loop.md` and
`research-handoff.md` were intentionally NOT modified — see "What ChatGPT should
review".)*

- **New issues discovered:** the original packet's "Option B" reversed the CORE-R2
  gate by merging unguarded domain handlers into `Shopify-connector` before
  protecting them — a category error the review caught; corrected via the
  staging-branch strategy. A helper that enters a context manager and returns its
  `result` silently releases the lease before caller reconciliation — a real
  correctness trap now explicitly forbidden.
- **Repeated issue patterns:** (a) base-vs-PR-head anchor drift (OQ-4); (b)
  conflating a "protection is planned later" plan with "merge the unsafe code
  first" — the gate must be held at the integration branch, not deferred. Guard
  rules recommended to ChatGPT below.
- **Rules/checklists updated:** none modified this session (allowlist forbids it);
  **recommended** rules for ChatGPT: "never merge a frozen domain PR into the
  integration branch while it retains an unguarded transport call site — protect
  on a staging branch first"; and "a context-manager migration must be reviewed
  for any helper that returns the yielded value out of the `with`."
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
  escaping a context, and no main-cursor commit.
- **Should future prompts change? Yes** — done this revision: Prompt P is
  loop-owned RD-P against the PR #151 head; Prompts P/C start from the staging
  head; Prompt E added for the closure.

## What ChatGPT should review

1. **Approve the integration-staging strategy** (packet §7, 8 steps) replacing the
   rejected Option B.
2. **Confirm the loop-owned RD-P** design (packet §5.1) and the withdrawal of the
   umbrella-lease alternative.
3. **Confirm the flush semantics** (materialize-not-commit; no main-cursor commit).
4. **Approve the public-`execute()` closure** as a Slice-2B deliverable (packet
   §6b; Prompt E).
5. **Prerequisite tracking:** PR #160 (Slice 2A) must reach exact-head
   runtime-green + control-room acceptance before step 1. This packet does not and
   cannot advance PR #160.
6. **Governance deviations to bless:** (a) this session did **not** update the
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
(callsite-runtime packet incl. §5.1 loop-owned RD-P, §6b public-execute closure,
§7 integration-staging strategy; validation plan; this handoff); PR #160.

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
commit; run live Shopify validation; mark SRR-03 closed.

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
  2A) is the hard prerequisite. No code, no gate, SRR-03 OPEN. Next: PR #160
  runtime-green + merge, then the staging sequence.
