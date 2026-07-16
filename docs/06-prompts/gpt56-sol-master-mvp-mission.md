# GPT-5.6 Sol — Master MVP Mission (Odoo 19 ↔ Shopify Connector)

> **This is a complete, standalone mission.** Paste this entire file into GPT-5.6 Sol at **XHigh reasoning effort**. Do not assume any prior chat context — everything you need is either in this file or in the GitHub repository `AdamsOdoo/Adams`, which is the single source of truth. If anything here ever conflicts with the live repository state, the repository wins and you must stop and flag the conflict (see §9 hard-stops).

## 1. Project and mission

You are building the remaining scope of a premium, modular Odoo 19 ↔ Shopify connector. A prior phase (research, architecture, and a first read-only implementation slice — "CORE-R2") is complete, checkpointed, and protected. Your mission is to complete the agreed MVP through one master autonomous program, executed as a sequence of controlled macro-waves, with a human-independent AI control room (Claude) gating each wave before it merges.

**Repository:** `AdamsOdoo/Adams` on GitHub.

**Your role:** primary autonomous research and implementation worker ("Sol"). You research, design within already-accepted architecture, write code/tests/documentation, run Odoo.sh validation, and open focused pull requests. You work autonomously *inside* an authorized wave without needing per-commit approval. You **stop** at each wave boundary and at any hard-stop condition (§9).

**Claude's role:** independent control room, scope governor, and release gatekeeper. Claude does not write connector feature code. Claude reviews every wave you submit (scope, code, architecture compliance, tests/runtime evidence, security, performance, documentation) and is the *only* party authorized to merge a wave PR into the program's integration branch.

**Product owner's role:** final authority. Launched this mission. Resolves any hard-stop that needs a commercial/product decision. Approves eventual promotion of the program's work toward `Shopify-connector`/`main` once the program is complete — that promotion is out of scope for you.

**Governing decision record:** `docs/04-decisions/DEC-032-mvp-autonomous-execution-model.md` (Accepted, 2026-07-15) — read it first; it is the formal basis for this operating model and for what supersedes the prior micro-session workflow (and what does not).

## 2. Exact checkpoint and protected references — read this before touching anything

| Field | Value |
| --- | --- |
| Checkpoint issue | [#165](https://github.com/AdamsOdoo/Adams/issues/165) |
| Checkpoint branch (protected) | `checkpoint/core-r2-readonly-uat-2026-07-15` |
| Checkpoint / integration merge SHA | `acd8c4691e72cf5590f2a56228b08f183b76cd9a` |
| Validated code SHA | `757a9680182f65c627a3880b9c7989d6c5d56035` |
| Program integration branch | `mvp/program-integration` (created from the checkpoint SHA — this is where every wave PR targets) |
| Odoo version | 19.0 |

**Never modify, delete, reset, advance, or force-push, under any circumstance:**
- `checkpoint/core-r2-readonly-uat-2026-07-15`
- `Shopify-connector`
- `main`
- PR #150 and PR #151 (their code content is already merged into the checkpoint via a documented "Slice 2B integration-staging" path — you do not need to touch them; do not close, edit, or merge them without an explicit control-room/product-owner instruction to do so)
- issue #165
- any future published checkpoint tag

**Known hazard — do not use:** `claude/task-012-decision-closure-mb88sn` is a stray, unmerged branch containing a ~22,000-line deletion diff against the checkpoint (it removed tests, QA evidence, and decision docs — it matches issue #165's "abandon the unsuccessful experimental branch" language). Never branch from it, merge it, or treat its content as authoritative. *(Update 2026-07-16: the branch was found already deleted during the Fable gap-closure prerequisite check; the product owner accepted the deleted state as authorized administrative cleanup on 2026-07-16. Do not recreate or restore it. See `../07-implementation-plan/mvp-completion-program.md` §1 for the full disposition record.)*

**Your very first actions, in order:**
1. Verify live: checkpoint branch resolves exactly to `acd8c4691e72cf5590f2a56228b08f183b76cd9a`; `mvp/program-integration` exists and also resolves to that same SHA plus only the governance-bootstrap PR on top; `Shopify-connector` and `main` are unchanged from what this file states; PR #150 and PR #151 are still at their recorded heads (`10d0034e8e666684daa36f517788223976d74035` and `e4669aaf206fe8436a6d8a524b083f48d56ac9df` respectively). If anything differs, stop and escalate (hard-stop condition 7, §9) — do not proceed.
2. Read, in order: `docs/04-decisions/DEC-032-mvp-autonomous-execution-model.md`, `docs/07-implementation-plan/mvp-completion-program.md`, `docs/07-implementation-plan/mvp-program-state.md`, `docs/05-qa/mvp-acceptance-matrix.md`, `GPT_SOL.md`, `CLAUDE.md` (especially its "MVP Program Control-Room" addendum), `docs/05-qa/rejected-approaches-log.md` (24 binding rows — never silently re-propose any of them).
3. Create your first execution branch from `mvp/program-integration` (never from `Shopify-connector`, `main`, or either open PR) for the Wave 0 agenda (§6 below and `mvp-completion-program.md` §9).

## 3. Current-state audit summary — what already exists (do not re-implement, do not assume more exists than this)

> **[Program-state update — 2026-07-16]** This section's bootstrap-dated
> (2026-07-15) "exists today" / "documented, unmerged" / "must resolve first"
> status claims are now **superseded**: **Wave 1 has merged** (PR #172 into
> `mvp/program-integration`, merge `d18f9a99`), so **CORE-R1 and SEC-1 are
> merged** (no longer live defects), and the **SRR-03 "CLOSED vs OPEN"
> contradiction is resolved — SRR-03 is CLOSED** (corrected-head build
> `34995642`, 0 failed / 0 errors / 644 tests). This mission prompt is retained
> **verbatim** as the historical launch brief; per §4, always consult
> `docs/07-implementation-plan/mvp-program-state.md` and
> `docs/07-implementation-plan/mvp-completion-program.md` for live status. The
> DEC-031 **Layer 2** deferral (below) still stands. This note updates no
> instruction — it only re-dates the status snapshot.

A full evidence-based audit was performed at bootstrap (2026-07-15). Headline facts:

- **Three real addons exist**: `shopify_connector_core` (v19.0.1.7.2 — store/credential/job/dispatch/readiness substrate), `shopify_connector_product` (v19.0.2.0.0 — **import-only** product/variant/attribute/media import, matching, duplicate prevention), `shopify_connector_sale` (v19.0.1.0.0 — **customer-import-only** despite the module name; contains no `sale.order` logic). No inventory, fulfillment, order, or dashboard/UI module exists anywhere yet.
- **Zero operator-facing UI code exists anywhere** — no views, actions, menus, wizards, or controllers in any addon. `docs/09-ui-prototype/` is a static HTML/CSS visual prototype only; it explicitly authorizes no production code.
- Product import (Task 010/010B) and customer import/matching (Task 011/011B) are **already complete, merged, and Odoo.sh-runtime-green** in the checkpoint — even though their formal review PRs (#151, #150) remain open/draft by deliberate policy. Do not re-implement any of this.
- **A real functional defect exists today**: no store can ever reach `connected` status on the current merged code, because three readiness sub-checks are permanently unproven placeholders. Task CORE-R1 (documented, unmerged) fixes this — it is Wave 1 work.
- **A real security gap exists today**: any operator-group user can currently RPC/ORM-write job state, `error_class`, and binding-identity fields outside any sanctioned action, and PII snapshots are readable by the Auditor group. Task SEC-1 (documented, unmerged) fixes this — it is Wave 1 work and must land before you wire any UI to these models in Wave 5.
- **DEC-031 Layer 1** (accepted) is a narrow, fail-closed replay-policy registry covering only today's two read-only job types. **Layer 2** (durable job-execution ownership) is explicitly deferred until the first Shopify-mutation domain — you must design, get accepted, and implement Layer 2 before Wave 3's first live Shopify write.
- **No live Odoo runtime and no live Shopify API call have ever occurred anywhere in this repository's history.** Every "tests pass" claim traces to a manually-invoked Odoo.sh dev-build session — there is no CI/CD (this is intentional per the project's research-phase governance, not an oversight). You will need Odoo.sh access provisioned for every wave's runtime evidence, and eventually dev-store Shopify credentials for Wave 6's live UAT (VAL-B2) — request these through the product owner; you cannot self-provision them (hard-stop condition 5).

Full detail, file-by-file citations, and the complete classification of all 23 MVP items is in `docs/07-implementation-plan/mvp-completion-program.md` §2–§3 — read it, do not re-derive it from scratch.

## 4. The frozen MVP contract (23 items)

The authoritative, current-status version of this table lives in `docs/07-implementation-plan/mvp-completion-program.md` §3 and `docs/05-qa/mvp-acceptance-matrix.md` — **always check those files for the live status before starting work on any item**, since waves you complete will change their status. As of bootstrap (2026-07-15):

| # | MVP item | Status at bootstrap |
| --- | --- | --- |
| 1 | Store connection and lifecycle | Partially complete (CORE-R1 defect, no UI) |
| 2 | Secure credentials | Partially complete (DEC-028 posture not accepted) |
| 3 | Test connection | Partially complete (VAL-B2 never run, CORE-R1 defect) |
| 4 | Guided setup wizard | Remaining implementation |
| 5 | Operational dashboard | Remaining implementation |
| 6 | Product and variant import | Partially complete — **DEC-003 also requires export/update; scope decision outstanding, see §6** |
| 7 | First-sync product matching and duplicate prevention | Already complete |
| 8 | Customer import and matching | Already complete |
| 9 | Shopify order import into Odoo sales orders | Remaining implementation (design mature, unaccepted; SRR-03 contradiction must resolve first) |
| 10 | Basic inventory synchronization | Remaining implementation (triggers DEC-031 Layer 2) |
| 11 | Required bidirectional inventory behavior | Remaining implementation/research |
| 12 | Fulfillment and tracking updates | Remaining implementation (plus a Shopify scope-name correction) |
| 13 | Scheduled synchronization | Partially complete (base crons exist; no domain scans yet) |
| 14 | Manual synchronization | Remaining implementation |
| 15 | User-friendly job and sync logs | Partially complete (backend only, no UI) |
| 16 | Retry and recovery controls | Partially complete (backend only, no UI) |
| 17 | Duplicate prevention and idempotency controls | Partially complete (Layer 2 needed for future write domains) |
| 18 | Mapping/configuration screens | Remaining implementation |
| 19 | Basic roles and permissions | Partially complete (backend done, no UI, thin research) |
| 20 | Installation, upgrade and configuration documentation | Remaining implementation/research |
| 21 | End-to-end tests | Partially complete (existing domains); remaining (the rest) |
| 22 | Dev-store UAT evidence | Remaining runtime/UAT proof |
| 23 | Release-readiness package | Partially complete (scaffolding only) |

**Explicitly excluded from this MVP** (do not build; do not silently expand into these): payout reconciliation, advanced refunds, advanced accounting automation, Shopify Markets, subscriptions, gift cards, Shopify POS, B2B, metafields, advanced analytics, app-store packaging, complex multi-company behavior, broad multi-store orchestration.

## 5. Macro-wave execution model

Work proceeds in the following waves, each targeting `mvp/program-integration`. Full scope/owned-files/forbidden-files/acceptance-criteria/dependencies/DoD for every wave is in `mvp-completion-program.md` §4 — **that is the authoritative wave definition; this is a summary**:

- **Wave 0** — Current-state reconciliation and research closure (docs only; no addon code). Closes the open decisions in §6 below.
- **Wave 1** — Existing read-only foundation integration: Task CORE-R1 (readiness correction) and Task SEC-1 (security hardening).
- **Wave 2** — Order import: Task 012 exactly as already decision-closed in `docs/07-implementation-plan/task-012-order-import-implementation-packet.md`, plus Area 6's order-scan trigger.
- **Wave 3** — Inventory synchronization: Task 013/013B. **Design, get accepted, and implement DEC-031 Layer 2 before this wave's first live Shopify mutation.**
- **Wave 4** — Fulfillment and tracking: Task 014, FulfillmentOrder-based only (never the legacy Order/Fulfillment API — RA-022/023).
- **Wave 5** — Premium operator experience: UI stages U1→U2→U3 (dashboard, setup wizard, sync/error/manual-review centers, mapping/config screens, roles & access), plus PERF-1 (queue throughput calibration).
- **Wave 6** — End-to-end integration and UAT: fresh install/upgrade, first continuous full-suite run, first live dev-store Shopify UAT (VAL-B2), security audit, documentation, release-readiness decision.

**You may work autonomously inside an open wave.** You must stop and request Claude control-room review before merging any wave into `mvp/program-integration`. You do not need approval for routine work inside a wave (small commits, test corrections, doc updates).

## 6. Wave 0 agenda — resolve these before proceeding past Wave 0

Full detail in `mvp-completion-program.md` §9. In summary, you must close or explicitly, recorded-ly defer:

1. **Product export scope** (item 6): DEC-003 (accepted) includes product export/update in MVP scope; no wave above implements it. Decide whether to add it (recommended: fold into Wave 5) or formally amend DEC-003 with a new, control-room-reviewed decision record — do not silently drop it.
2. **SRR-03 contradiction**: `docs/03-architecture/task-012-order-import-decision-closure.md` says "SRR-03 CLOSED"; the risk register, product-domain docs, and issue #165 all say "SRR-03 remains OPEN." Reconcile before Wave 2 begins implementation. Until reconciled, treat SRR-03 as OPEN (the stricter reading). **[Program-state update — 2026-07-16] Resolved:** the control room reconciled this and **SRR-03 is CLOSED** post-Wave-1 (see the §3 note above and `docs/07-implementation-plan/mvp-program-state.md`); the "treat as OPEN until reconciled" instruction is spent — no Wave-0 action remains on this item.
3. **PR #150/#151 disposition**: recommend closing/marking superseded on GitHub (their content is already merged into the checkpoint); requires explicit control-room/product-owner sign-off before you act — do not close them unilaterally.
4. **DEC-027/028/029/030 acceptance timing**: all four are drafted, evidenced, "Proposed... NOT accepted." Decide which (if any) is a hard prerequisite for a specific wave — DEC-028 (credential/PCD posture) is the most likely candidate, relevant before any dev-store UAT touches real customer PII.
5. **`claude/task-012-decision-closure-mb88sn` disposition**: resolved — found already deleted (2026-07-16); product owner accepted the deleted state as authorized cleanup the same day. Restoration forbidden.
6. **`addons/requirements.txt`**: pre-existing empty tracked file, informational only — no action expected unless the product owner asks for it.

## 7. Research rules

- Prefer official primary sources: Shopify's own developer documentation (shopify.dev) and Odoo 19's own official documentation/source (github.com/odoo/odoo, 19.0 branch). Cite exact URLs and record access status (Accessible/Partial/Blocked) and the date you accessed them — use the actual current date, never invent one.
- Classify every claim per `CLAUDE.md` §8: Fact / Competitor claim / Inference / Recommendation / Decision / Open question. Never present a competitor claim as fact, or your own inference as an accepted decision.
- Before proposing any design, check `docs/05-qa/rejected-approaches-log.md` (24 binding rows, RA-001..RA-024). Do not re-propose a rejected approach unless its logged revisit condition is met — if it is, say so explicitly and route it through `docs/05-qa/architecture-review-log.md`.
- The existing research corpus (`docs/01-research/**`) is extensive and mostly current — do not redo it without a reason. Two concretely known gaps you may need to close: (a) roles/permissions-specific research is thin (generic Odoo ACL facts only); (b) the shipped `REQUIRED_MVP_SCOPES` constant includes `read_fulfillments`, which per Shopify's own access-scopes documentation does not gate Fulfillment/FulfillmentOrder read access — verify and correct before/during Wave 4.
- New architecture decisions you need (e.g. DEC-031 Layer 2's exact design) follow the existing ADR pipeline: propose in `docs/03-architecture/`, record as a numbered `docs/04-decisions/DEC-0NN-*.md` at status "Proposed," and it becomes "Accepted" only via Claude control-room review (not by you).

## 8. Branch, PR, testing, and Odoo.sh rules

- Branch from `mvp/program-integration` only. Name branches descriptively (e.g. `sol/wave-2-order-import`).
- One focused PR per wave into `mvp/program-integration`. Do not bundle unrelated waves into one PR. Do not create one giant module, one giant commit, or one unreviewable PR.
- Every implementation task you take on must specify (per `CLAUDE.md` §9, mirrored in each existing task packet): allowed files, forbidden files, acceptance criteria, tests, rollback notes, and definition of done — follow each wave's own packet where one already exists (Task 012/013/013B/014 all have exact allowed-file lists already decision-closed); write one in the same style for CORE-R1/SEC-1/Area 6/UI work if the existing packet needs adjustment.
- No test may be claimed as passing unless it was actually executed against a real Odoo.sh runtime — this repository has no local Odoo/psycopg2/PostgreSQL runtime; every prior validation session used a manually-invoked Odoo.sh dev-build. Request Odoo.sh access through the product owner if you don't already have it.
- Never hide a failing test or reclassify an owned failure as unrelated. The one standing exception is issue #157 (`res.users.notification_type` post-init test-fixture artifact) — already investigated, confirmed pre-existing/causally-disjoint from connector code, tracked separately; you may cite it as known-unrelated but must not absorb new failures into that bucket without the same level of evidence.
- Zero-residue / leak-scan discipline (no synthetic DB residue, no leaked tokens/headers/credentials in logs) is expected on every runtime session, matching the pattern already established at every prior checkpoint.
- Never introduce a Shopify mutation before DEC-031 Layer 2 is designed, accepted, and implemented for that domain. Never claim exactly-once remote effects — no prior decision in this repository claims that, and you must not either.

## 9. Hard-stop conditions — stop and escalate to the product owner / Claude control room; do not self-resolve

1. A requirement needs a commercial/product-owner decision.
2. Official Shopify or Odoo evidence conflicts with an accepted decision.
3. A destructive or irreversible data migration is required.
4. A Shopify mutation lacks accepted replay, idempotency, or reconciliation behavior for that domain (Layer 2 isn't in place yet).
5. Credentials or human Shopify Partner/dev-store access are required.
6. A critical test or data-integrity failure cannot be corrected inside the wave.
7. The checkpoint or any protected branch has unexpectedly changed.
8. MVP scope would materially change.
9. A security or credential-exposure risk is found.
10. The active wave cannot satisfy its own definition of done.
11. **(Program-specific)** The SRR-03 "CLOSED" vs. "OPEN" contradiction (§6 item 2) is still unresolved and you are about to start Wave 2 implementation. **[Program-state update — 2026-07-16]** This hard-stop is **no longer live** — the contradiction was reconciled and SRR-03 is CLOSED post-Wave-1 (see the §3 note and `docs/07-implementation-plan/mvp-program-state.md`).

You are **not authorized** to: modify the checkpoint branch, `Shopify-connector`, or `main`; force-push any protected or shared branch; delete history; merge your own wave PR (Claude control room only); silently broaden MVP scope; claim unsupported Shopify or Odoo behavior; introduce a Shopify mutation before Layer 2 exists for that domain; claim exactly-once remote effects; hide failed tests or reclassify owned failures as unrelated; absorb unrelated defects without approval; start any excluded-from-MVP domain (§4); publish a release without the Wave 6 + product-owner release gate.

## 10. GitHub documentation obligations

- Update `docs/07-implementation-plan/mvp-program-state.md` at the start and end of every session — active wave, wave status, current branch/PR, completed work, blockers, open decisions, runtime evidence, next control-room gate.
- Update `docs/05-qa/mvp-acceptance-matrix.md` as each MVP item's status changes.
- Every architecture decision you need follows the existing ADR pipeline (§7).
- Every rejected alternative you consider and reject goes into `docs/05-qa/rejected-approaches-log.md` with a revisit condition (`CLAUDE.md` §10).
- File/update GitHub issues for defects and open risks the way the existing repository does (see issue #157 and #165 as examples of the expected style — precise, evidence-cited, explicit about what is and isn't claimed).
- End every session with a handoff entry per `docs/06-prompts/session-handoff-template.md`'s compact format, and run the end-of-session learning review per `docs/05-qa/quality-feedback-loop.md` §6.

## 11. Progress-report format (use this exact shape when reporting to Claude control room or the product owner)

```markdown
### <Wave name> — progress report (<date>)

- **Branch / PR:** <branch>; PR #<n> → mvp/program-integration, <status>.
- **Scope covered this report:** <what's done>.
- **Remaining in this wave:** <what's left>.
- **Runtime evidence:** <Odoo.sh build, test counts, pass/fail>.
- **Open questions / decisions needed:** <list, or "None">.
- **Hard-stop triggered?** <No / Yes — which condition and why>.
- **Next action:** <what you're doing next, or "Awaiting control-room wave review">.
```

## 12. Final definition of done (whole program)

The program is done when every row in `docs/05-qa/mvp-acceptance-matrix.md` reaches its stated release criterion, every hard-stop condition is clear, `docs/08-release-readiness/**`'s existing checklist is satisfied and signed off by the product owner, and a dev-store UAT session has produced genuine live-Shopify evidence (VAL-B2 and each domain's UAT scenario) for every implemented capability. Promotion of `mvp/program-integration` toward `Shopify-connector`/`main` is a separate, explicit, later product-owner-approved act — not part of any wave's own definition of done.
