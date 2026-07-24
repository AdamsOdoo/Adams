# DEC-032: MVP Autonomous Execution Model — Claude Control Room, GPT-5.6 Sol Executor

> **Superseded in role assignment only — 2026-07-25.** Preserved for history. The macro-wave/checkpoint/GitHub/no-self-acceptance controls remain; [the role-model addendum](2026-07-25-mvp-role-model-addendum.md) and [DEC-041](DEC-041-evidence-first-process-reallocation.md) replace Claude-control-room and sole-merge-gatekeeper wording.

- **Status:** Accepted — see Status note below for the procedural basis.
- **Date:** 2026-07-15
- **Deciders:** Product owner (direct, explicit written instruction, this session — "MVP Program Bootstrap"). No separate ChatGPT review was performed before acceptance; see Status note.
- **Phase:** Program governance / operating model (not a technical architecture decision; does not itself authorize any implementation).
- **Related:** CLAUDE.md §2 (prior role model), issue #165 (CORE-R2 checkpoint), `docs/07-implementation-plan/mvp-completion-program.md`, `docs/07-implementation-plan/mvp-program-state.md`, `docs/06-prompts/gpt56-sol-master-mvp-mission.md`, `docs/06-prompts/claude-mvp-wave-review-template.md`, `GPT_SOL.md`.

## Status note (procedural basis for Accepted status)

Every prior DEC in this repository reached Accepted status through a Claude-proposes / ChatGPT-reviews cycle (CLAUDE.md §2, §8). This decision is the one deliberate exception, and that exception is recorded here rather than silently normalized:

- The product owner — the principal both CLAUDE.md and CHATGPT.md ultimately answer to — issued a single, extremely detailed, explicit instruction in this session directing exactly this operating-model change: Claude becomes the independent control room for the MVP completion program; GPT-5.6 Sol becomes the primary autonomous research/implementation worker; the checkpoint stays protected; a macro-wave process (not micro-session micro-approval) governs execution; Claude retains merge-gating authority over Sol's work.
- The product owner has standing authority to reassign roles between the AI collaborators they employ. CLAUDE.md §2's role table is itself a product-owner-authored delegation, not an independent constitutional constraint on the product owner.
- This is therefore accepted **directly by product-owner instruction**, without a separate ChatGPT review pass, because the instruction is unambiguous, self-aware of the prior model it supersedes, and internally specifies how it coexists with the rest of CLAUDE.md (see "Scope of this decision" below).
- This exception applies **only to this decision** (the MVP program operating model). It does not change §8's rule for any other future decision: every other DEC in this repository still requires ChatGPT (or another explicitly designated reviewer) acceptance before Accepted status. Sol is explicitly not authorized to self-accept architecture decisions under this precedent (see "Sol authority," below, and in `mvp-completion-program.md`).

## Context

Per the checkpoint (issue #165) the project has:

- A validated, protected read-only foundation (store connection/lifecycle, credentials, test-connection, product import, customer import, job/log/retry substrate, DEC-031 Layer-1 replay-safety) merged and Odoo.sh-runtime-green at commit `acd8c4691e72cf5590f2a56228b08f183b76cd9a`.
- An extensive, mature, but **unaccepted** planning corpus for the remaining MVP domains (order import — Task 012; inventory — Task 013/013B; fulfillment — Task 014; operator UI — U0–U3; sync triggers — Area 6; security hardening — SEC-1; throughput — PERF-1), all explicitly gated "Proposed... NOT accepted... no code authorized."
- Zero operator-facing UI code anywhere in the repository.
- A prior working model (CLAUDE.md §2/§6: Claude executes small scoped research/documentation sessions; ChatGPT is strategy/control room and reviews every step) that, applied unmodified to the remaining MVP scope, implies dozens of further micro-approval round-trips before the MVP can be completed.

The product owner's instruction (this session) determined that completing the MVP requires a different operating model: one autonomous executor (GPT-5.6 Sol) working in bounded macro-waves, with Claude — not the product owner directly, and not the previous Claude-executes/ChatGPT-reviews loop — acting as the independent control room, scope governor, and release gatekeeper for this specific program.

## Decision

1. **Roles for the MVP completion program** (scoped to work based on `mvp/program-integration`, see "Scope" below):
   - **GPT-5.6 Sol** is the primary autonomous research and implementation worker. Sol researches, writes code/tests/docs, runs Odoo.sh validation, and opens focused PRs into `mvp/program-integration`, continuing autonomously inside an authorized macro-wave without needing per-commit approval.
   - **Claude** is the independent control room: scope governor and release gatekeeper. Claude does not write connector feature code in this role. Claude reviews each macro-wave (scope, code, architecture compliance, tests/runtime evidence, security, performance, documentation) using `docs/06-prompts/claude-mvp-wave-review-template.md` and is the only party authorized to accept/merge a wave PR into `mvp/program-integration`.
   - **The product owner** is the final authority: launches Sol, resolves hard-stops that need a commercial/product decision, and approves promotion of `mvp/program-integration` toward `main`/`Shopify-connector` when the program is complete.
   - **GitHub remains the single source of truth** (CLAUDE.md §3): every wave's scope, evidence, and acceptance decision is a file or PR/issue record in this repository, not a chat transcript.
2. **One master MVP goal, executed in controlled macro-waves** (Wave 0 through Wave 6, defined in `docs/07-implementation-plan/mvp-completion-program.md`), not one giant module, one giant commit, or one unreviewable PR. Sol is authorized to work autonomously *inside* an open wave; Sol must stop at each wave-review gate for Claude's acceptance before merging into `mvp/program-integration`.
3. **No micro-approval loop** for routine work inside an authorized wave (small commits, test corrections, doc updates) — this supersedes CLAUDE.md §6's "one clearly scoped objective per session" cadence *only* for `mvp/program-integration`-based work. CLAUDE.md §6 continues to govern any session working outside this program (e.g. on `Shopify-connector` directly).
4. **Checkpoint recovery model**: `checkpoint/core-r2-readonly-uat-2026-07-15` (commit `acd8c4691e72cf5590f2a56228b08f183b76cd9a`) remains the permanent, protected recovery point for the whole program. `mvp/program-integration` was created from that exact commit. If a wave fails unrecoverably, the recovery path is: abandon the failed working branch, branch fresh from `mvp/program-integration` (or, in the worst case, recreate `mvp/program-integration` from the checkpoint SHA), and resume only after a new control-room plan is accepted. Neither the checkpoint branch nor `Shopify-connector` nor `main` is ever reset, rewritten, or force-pushed by this program.
5. **Merge authority**: only Claude (control room) may accept and merge a macro-wave PR into `mvp/program-integration`. Sol may never merge its own wave. Promotion from `mvp/program-integration` to `Shopify-connector` or `main` requires explicit product-owner approval (mirroring the existing `Shopify-connector`→`main` promotion rule) and is out of scope for any single wave.
6. **Stop conditions**: the ten hard-stop conditions enumerated in `mvp-completion-program.md` (commercial decision needed, official-evidence conflict, destructive/irreversible migration, unresolved mutation-safety gap, credential/access needed, uncorrectable test/data-integrity failure, protected-reference drift, MVP scope change, security/credential-exposure risk, wave definition-of-done unreachable) apply to Sol at all times and are not waivable by Sol itself.

## Scope of this decision

This decision changes the operating model **only** for work on or descending from `mvp/program-integration` (the MVP completion program). It does not:

- Reopen or reassign any already-Accepted DEC (DEC-003 through DEC-031) — those remain binding technical/architecture decisions this program must still honor.
- Change branch protection or promotion rules for `checkpoint/core-r2-readonly-uat-2026-07-15`, `Shopify-connector`, or `main` (CLAUDE.md's existing branch-governance section is unchanged for those refs).
- Authorize Claude to write connector feature code, or authorize Sol to skip citation/claim-classification discipline (CLAUDE.md §7–§8 still apply to Sol's research and documentation output).
- Retroactively re-litigate any work done under the prior Claude-executes/ChatGPT-reviews model; that work (through the checkpoint) stands as-is.
- Grant Sol authority to accept architecture decisions, close risk-register rows, or mark any DEC/AR/AGENT-record Accepted — those remain Claude-control-room or product-owner acts per wave review.

## Consequences

- **Positive:** removes the multi-round micro-approval bottleneck for the remaining, already-well-designed MVP domains; gives Sol clear, bounded authority to move fast inside a wave while Claude retains a hard gate at each wave boundary; keeps the checkpoint and all shared branches protected throughout.
- **Negative / trade-offs:** Sol operates with less per-step supervision than the prior model; this raises the importance of the wave-review template's rigor (code/architecture/security/test/runtime-evidence review) and of the hard-stop list being genuinely respected. A wave that turns out to be mis-scoped costs more to unwind than a micro-session would.
- **Follow-ups:** `docs/07-implementation-plan/mvp-completion-program.md` (the program contract), `docs/07-implementation-plan/mvp-program-state.md` (live tracker), `docs/05-qa/mvp-acceptance-matrix.md` (feature/test/evidence map), `docs/06-prompts/gpt56-sol-master-mvp-mission.md` (Sol's standalone launch prompt), `docs/06-prompts/claude-mvp-wave-review-template.md` (Claude's reusable wave-review prompt), a CLAUDE.md addendum, and root `GPT_SOL.md` are created alongside this decision (same bootstrap session).

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Continue the prior Claude-executes/ChatGPT-reviews micro-session model for the remaining MVP domains | Explicitly rejected by the product owner's instruction as too slow for completing an already well-designed but unimplemented remaining scope (order/inventory/fulfillment/UI); would require dozens more micro-approval round-trips for work that is already decision-mature. | Not added to `rejected-approaches-log.md` — this is a program-management choice, not a technical architecture alternative in the RA-0NN sense, and it remains available to revert to (see Scope, above) rather than permanently foreclosed. |
| Let Sol merge its own macro-waves without a control-room gate | Rejected — violates the checkpoint-protection and no-silent-scope-expansion requirements; the product owner's instruction explicitly requires Claude wave-review + merge authorization before any wave lands. | N/A (explicitly excluded in the instruction this decision implements). |
| Build everything in one branch / one PR | Rejected — explicitly excluded by the product owner's instruction ("Do not create one giant module, one giant commit or one unreviewable PR") and inconsistent with CLAUDE.md §9's per-task allowed/forbidden-files and acceptance-criteria discipline, which the wave structure preserves at wave granularity. | N/A. |

## Evidence / references

- This session's task instruction (product-owner direct instruction, 2026-07-15) — the primary source for this decision; not an external citation, recorded verbatim in intent across this file and the program files it introduces.
- `CLAUDE.md` §2, §6, §8, §9 (prior role model, session scoping, claim classification, implementation-task requirements) — accessed 2026-07-15, in-repo.
- Issue #165 (checkpoint record) — `https://github.com/AdamsOdoo/Adams/issues/165` — accessed 2026-07-15, Accessible.
