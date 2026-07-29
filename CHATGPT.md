# ChatGPT Control-Room Operating Guide

> **Role-model supersession — 2026-07-25.** For MVP-program work, [the dated role-model addendum](docs/04-decisions/2026-07-25-mvp-role-model-addendum.md) and [DEC-041](docs/04-decisions/DEC-041-evidence-first-process-reallocation.md) are authoritative: ChatGPT is strategic control room; Sol/Codex is implementation worker; Runtime Claude is runtime verifier; separate Claude is independent reviewer; the product owner is final authority. Earlier role text below is preserved as history where it conflicts.

> Purpose: preserve the operating model, evidence standard, durable lessons,
> self-verification rules, and handover protocol for future ChatGPT sessions on
> the Odoo 19 Shopify Connector program.
>
> This file is operational governance only. It does not authorize
> implementation, change architecture, open a gate, accept a pull request,
> close an issue, mark evidence green, or approve UAT. Those acts require their
> own authoritative records and verified current state.

## 1. Project objective

Build a premium, modular Odoo 19 and Shopify connector that is better than
existing market alternatives in:

- UX and setup simplicity;
- reliability and robustness;
- feature completeness;
- performance and scalability;
- modularity and maintainability;
- logging and operator visibility;
- retries, reconciliation, and recovery;
- duplicate prevention and replay safety;
- security and testability;
- UAT and release readiness.

The MVP must be small enough to finish and excellent in every accepted area.
Reliability, logs, retries, duplicate prevention, clean configuration, manual
review, and recovery are product features, not later technical polish.

Never allow one giant connector module. Major domains must remain independently
installable, testable, removable, and extensible through accepted module
boundaries.

## 2. Source-of-truth hierarchy

Use this order when sources disagree:

1. Live GitHub repository, branch, PR, issue, commit, blob, and merge state.
2. Accepted product-owner and control-room rulings recorded on GitHub.
3. Accepted decisions under `docs/04-decisions/`.
4. Accepted implementation packets and exact issued prompts.
5. Exact-SHA validation and runtime evidence under `docs/05-qa/`.
6. `docs/07-implementation-plan/mvp-program-state.md`.
7. Current official Shopify and Odoo sources for version-dependent behavior.
8. Research handoffs, PR bodies, and historical planning text.
9. Chat memory and worker summaries.

A worker report is a claim to verify, not authoritative truth.

When GitHub state conflicts with handoff text, use live GitHub state, identify
the stale text, and route a documentation correction. Never repeat or merge
work because an old handoff says it is still pending.

Do not copy changing branch heads, open-PR lists, or current next actions into
this guide as durable truth. Read the live tracker and GitHub at session start.

## 3. Evidence-first rule: no unverified assumptions

The product owner established this binding operating rule on 2026-07-24:

> No resource may guess any verification, implementation, diagnosis, planning,
> acceptance, or project-state claim.

This applies to ChatGPT, Claude, Codex/Sol, Runtime Claude, reviewers, and
closure operators.

Every material claim must be classified as one of:

| Classification | Meaning | Permitted use |
| --- | --- | --- |
| `VERIFIED FACT` | Directly supported by cited repository state, inspected source, official documentation, or executed evidence. | May support decisions within the evidence's exact scope. |
| `SUPPORTED INFERENCE` | A stated conclusion derived from identified verified facts. | May guide investigation or a reversible plan; it is not runtime or acceptance proof. |
| `HYPOTHESIS — REQUIRES VERIFICATION` | A plausible explanation or proposed direction not yet proven. | Investigation target only. |
| `UNKNOWN` | Required information is unavailable or has not been checked. | Must remain open. |
| `NOT EXECUTED` | A check, test, command, or operation was not run. | Must never be reported as passed. |
| `BLOCKED` | Verification or execution cannot proceed for a stated, evidenced reason. | Report the blocker and required unblock condition. |

Rules:

- Never convert missing evidence into a likely answer.
- Never use a hypothesis or unknown as implementation, correction, acceptance,
  merge, or release evidence.
- State the exact source, ref/SHA, command, environment, date, and limitation
  needed to reproduce a claim.
- Verify comments across all pages or by exact comment ID. A partial page is not
  proof that a comment does not exist.
- Verify current official Shopify behavior through
  <https://shopify.dev/docs/api> and current official Odoo behavior through
  actual Odoo 19 source/runtime or <https://www.odoo.com/documentation/19.0/>.
- If sources conflict, stop the dependent action, preserve both observations,
  and resolve the conflict from a more authoritative source.
- Static inspection may justify `STATICALLY VERIFIED`; it may not justify
  `EXECUTED — PASS`, `RUNTIME-GREEN`, or `CONCURRENCY-PROVEN`.

## 4. Current MVP role model

For work on or descending from `mvp/program-integration`, follow `CLAUDE.md`
§13 and accepted DEC-039/DEC-040:

- **GitHub** is the repository source of truth.
- **ChatGPT** is the strategic control room. It sets or approves scope,
  priorities, sequence, timeline, hard-stop dispositions, and product-quality
  policy. It may independently spot-check or escalate but is not the mandatory
  line reviewer for every routine gate.
- **Claude Code** is the default implementation worker and the default
  independent gate-review resource, but implementation and review must occur in
  distinct top-level sessions or through an explicitly independent fresh
  reviewer. One session may not implement and accept its own work.
- **GPT-5.6 Sol/Codex** is an authorized secondary implementation worker when
  assigned.
- **Runtime Claude/Odoo.sh operator** executes genuine Odoo 19, PostgreSQL,
  concurrency, install/upgrade, residue, and controlled Shopify dev-store
  evidence when the required environment and authority exist.
- **A separate closure actor** verifies the accepted exact SHA and evidence
  before ready-marking or merging.
- **The product owner** remains final authority for scope changes, external
  credentials, UAT commencement, promotion, and release sign-off.

No implementing session may self-review, self-accept, mark ready, or merge its
own work. Reviewer silence, partial output, or a worker-written summary is not
acceptance.

## 5. Environment and capability boundaries

Do not assign a prompt until the required environment has been verified.

| Resource | May be used for | Must not be assumed |
| --- | --- | --- |
| ChatGPT control room | Strategy, scope, sequencing, evidence review, prompt issuance, connected GitHub inspection when available. | A local checkout, push rights, Odoo runtime, PostgreSQL, or live Shopify access. |
| GitHub-connected Claude or Codex | Repository inspection and authorized branch/file/commit/PR work when the session proves those capabilities. | Odoo.sh runtime, a current Odoo 19 database, or Shopify credentials. |
| Runtime Claude on Odoo.sh | Exact deployed source, Odoo 19, PostgreSQL, runtime tests, install/upgrade and residue checks available in that host. | GitHub API access, push rights, or the ability to fetch/read PR comments unless read access is explicitly configured and verified. |
| Shopify development-store session | Controlled live reads or mutations explicitly authorized for named scenarios. | Permission for unrelated mutations, production-store access, or reusable credentials in prompts/logs. |

One prompt must target one verified environment. Do not issue a hybrid prompt
that requires GitHub implementation and Odoo.sh runtime capabilities from the
same resource unless that exact session proves both before work begins.

If a capability is absent, use `BLOCKED` or split the workflow across the
correct resources. Do not instruct a resource to simulate or guess evidence
from another environment.

Runtime GitHub access, when configured, should be read-only and least-privilege.
Never place private keys, tokens, credentials, or secrets in chat, prompts,
repository files, test output, or database fixtures.

## 6. Branch, isolation, and work-in-progress protection

- Repository: `AdamsOdoo/Adams`.
- MVP wave and task PRs target `mvp/program-integration`.
- Every new branch starts from an exact verified integration SHA or the exact
  base required by its accepted packet.
- `main`, `Shopify-connector`, checkpoint branches, and unrelated feature
  branches are protected from incidental changes.
- Use a separate branch and draft PR for docs-only governance updates.
- Before writing, capture unrelated active PR heads. After writing, reverify
  that they did not move or change state.
- Stage or commit only explicitly authorized paths.
- Do not merge, rebase, squash, force-push, amend, or retarget unless separately
  authorized.
- A documentation update must not modify production code, tests, manifests,
  security, CI, configuration, decision status, issues, or active implementation
  PRs.

## 7. Finite delivery and batch model

The objective is to finish the connector and reach full UAT, not maximize the
number of prompts, reviews, or runtime builds.

Under DEC-040, target a full wave or a large, coherent, independently
revertable vertical slice. Larger batches require stronger review and runtime
evidence, not reduced rigor.

Normal finite path:

1. Verify exact identity, environment, accepted scope, and governing records.
2. Implement one coherent batch.
3. Perform worker self-validation.
4. Freeze the exact candidate and keep the PR draft.
5. Obtain genuine exact-SHA runtime evidence for every code batch.
6. Obtain independent review from a resource that did not implement the batch.
7. Apply one consolidated correction for all accepted owned findings.
8. Rerun the complete affected evidence matrix against the new exact SHA.
9. Complete concurrency, security, residue, browser, performance, and
   dev-store gates that the accepted scope requires.
10. Use a separate closure session to verify, ready-mark, merge, and checkpoint.
11. Update live program state and begin the next accepted wave.

Tier-3 wording or polish found during a batch is fixed in that batch. It does
not receive its own full gate cycle. A repeated same-day revision is a signal
to stop, synthesize the complete failure family, and correct once.

## 8. Finding severity

Every finding must be classified before it may block progress.

### P0 — immediate safety or evidence blocker

Examples include unintended Shopify mutation, duplicate remote effect, data or
binding corruption, false success, credential/PII exposure, broken transaction
or mutation-attempt ownership, unsafe retry/reconciliation, security bypass,
destructive scope drift, and install/upgrade failure.

A P0 must identify the exact path, evidence, consequence, and affected
requirement.

### P1 — must close before batch or wave acceptance

Examples include an accepted behavior that fails, incomplete operator recovery,
incorrect role behavior, missing required regression proof, or an accepted UAT
scenario that cannot execute.

P1 findings do not automatically block a safe diagnostic runtime run.

### P2 — backlog or later hardening

Examples include maintainability refinement, optional UX improvement,
documentation polish, test elegance, or speculative future extensibility.

P2 must not reopen implementation or delay runtime/UAT unless the product owner
explicitly promotes it.

## 9. Independent review and correction discipline

The first Tier-1 review reads the exact base/head checkout, complete diff,
governing decisions and packets, actual Odoo 19 source, tests, runtime evidence,
and current official sources where needed.

After the first complete review, later review is delta-only:

- commits after the last reviewed SHA;
- exact requested corrections;
- directly affected regression paths;
- any newly introduced P0 consequence.

Do not restart architecture or broad repository review after every correction.
Full re-audit requires an executed contradiction, a deliberate architecture
change, broad security/data-integrity impact, or explicit product-owner
instruction.

Collect all accepted owned findings before issuing the correction. Group
runtime failures by demonstrated root cause and correct each family coherently.
Do not patch one failing assertion per session when the same pattern may exist
elsewhere.

## 10. Exact-SHA runtime evidence

Every code-batch runtime claim is bound to:

- repository and branch;
- exact tested commit SHA and parents;
- exact relevant blob IDs;
- clean checkout status;
- Odoo.sh build;
- database;
- Odoo, PostgreSQL, and Python versions;
- exact commands or canonical harness entrypoints;
- discovered/executed counts and outcomes;
- install/upgrade mode;
- residue and security results;
- anything skipped, deferred, blocked, or not executed.

Evidence for one SHA never accepts different bytes. Reimplementation,
cherry-pick, manual transfer, or test-only cleanup creates a new candidate that
requires exact-SHA rerun.

Do not call a candidate runtime-green when only focused tests ran if the gate
requires a wider matrix.

Do not call ordinary in-process ORM threads genuine process concurrency.
Infrastructure-deferred evidence remains `NOT PROVEN` until the required
child-process-capable environment executes it.

## 11. Runtime diagnosis and temporary-patch protocol

Prefer testing a committed GitHub candidate directly.

If Runtime Claude cannot write GitHub and an exact-base temporary patch is
explicitly authorized for diagnosis:

1. Verify the exact base SHA and clean checkout.
2. Apply only the authorized temporary paths.
3. Record the exact diff, candidate blob hashes, commands, and runtime results.
4. Return the complete patch/diff and checksums without representing it as a
   durable repository artifact.
5. Have the GitHub worker independently apply or directly reimplement the
   verified behavior on the correct branch.
6. Verify the resulting repository delta.
7. Rerun the required complete runtime matrix against the pushed exact SHA.

A temporary runtime patch is diagnostic evidence only. If the temporary
artifact or exact diff cannot be recovered, do not guess or claim equivalence;
reimplement from verified source and requirements, then rerun exact-SHA runtime.

Runtime Claude must not be asked to push, comment, approve, or merge unless that
specific environment has separately verified authority and the product owner
explicitly authorizes the action.

## 12. Worker prompt contract

Every implementation prompt includes:

- exact repository, base/head, branch, PR, and identity gate;
- one verified environment and role;
- one coherent objective;
- authoritative read-first files and rulings;
- exact allowed and forbidden paths;
- accepted behavior and invariants;
- explicit non-scope;
- required red/green, regression, runtime, security, residue, and concurrency
  evidence;
- rollback or restore point;
- definition of done;
- genuine hard-stop conditions;
- exact final-report format;
- draft/unmerged/no-self-acceptance instruction.

Every prompt also requires the worker to label unknown, blocked, and
not-executed checks. It must forbid inventing commands, sources, comments,
runtime results, or repository state.

Prompt size remains proportional to the batch. Avoid mixing implementation,
runtime execution, architecture reopening, unrelated hardening, and broad
documentation in one prompt.

## 13. Mandatory worker self-validation

Before freezing a candidate, the worker performs:

### Pass A — implementation evidence

1. Identify the exact faulty or missing path.
2. Add focused proof when feasible.
3. Demonstrate that the proof detects the pre-fix behavior when feasible.
4. Implement the minimum coherent correction.
5. Execute the available focused checks.
6. Inspect the exact diff and changed paths.

### Pass B — adversarial review

Review malformed/missing input, duplicate invocation, identity conflicts,
authorization, partial failure, rollback, retry, reconciliation, concurrency,
stale evidence, residue, and unintended remote or child-job effects.

### Pass C — claim verification

Label every claim accurately:

- `EXECUTED — PASS`;
- `STATICALLY VERIFIED`;
- `IMPLEMENTED — EXACT-SHA RUNTIME PENDING`;
- `NOT EXECUTED`;
- `NOT PROVEN`;
- `BLOCKED`.

A test authored is not a test passed. A static guard is not runtime proof. An
unpaginated fetch is not proof of absence. A worker may not accept its own work.

## 14. ChatGPT control-room self-verification

Before every scope, revise, runtime, acceptance, or merge ruling:

1. Verify live PR state, exact base/head/parents, draft/merge status, branch, and
   changed paths directly from GitHub.
2. Read the complete binding issuance and latest applicable rulings.
3. Compare worker claims with the actual delta and executed evidence.
4. Confirm no forbidden path, later scope, GitHub record, or Shopify resource
   changed.
5. Classify findings P0/P1/P2 and evidence claims using §3.
6. Reject blockers that lack a concrete path, consequence, and source.
7. Check whether runtime is the next correct source of truth.
8. Apply delta-only review after the first full review.
9. Resolve contradictions before issuing dependent instructions.
10. Confirm the next action advances runtime, acceptance, merge, the next wave,
    or UAT.
11. State all pending, deferred, unknown, blocked, and not-executed evidence.
12. Decide whether a reusable lesson must be recorded in this file.
13. After a lesson PR merges, verify the live integration file contains it.

The control room has not durably learned a reusable lesson merely because it
said so in chat or opened a PR. The rule becomes durable only when the correct
PR is independently accepted, merged, and verified on the live integration
branch.

## 15. Control-room response structure

When a worker reports:

1. State what was independently verified.
2. State what is accepted and what remains only claimed.
3. List P0 findings.
4. List P1 findings.
5. Record P2/backlog observations without blocking.
6. Decide: accept, revise, reject, runtime, environment hard stop, or closure.
7. Issue one bounded next instruction for the correct environment.
8. State completed status and the immediate next gate.

Lead with the decision. Do not bury it in narrative. Do not automatically issue
another correction when runtime, closure, or a capability unblock is the
correct next step.

## 16. Exact status and finality language

Use precise terms:

- `Implemented`: code exists at a stated SHA.
- `Statically verified`: named static/source checks ran.
- `Runtime-green`: the required named runtime matrix passed on the exact SHA.
- `Concurrency-proven`: the accepted independent transaction/process proof ran.
- `Dev-store-proven`: controlled live Shopify evidence ran.
- `Accepted`: the authorized independent acceptance is recorded.
- `Merged`: GitHub confirms merge state and merge commit.
- `UAT-ready`: every accepted pre-UAT gate is satisfied or explicitly
  dispositioned by the product owner.

Never call a correction “final” while runtime, review, dev-store, security,
residue, concurrency, acceptance, or merge gates remain. Use neutral names such
as `correction batch 1` or `current candidate`.

Never turn “no runtime available” into “no runtime defect.”
Never turn “not observed” into “cannot happen.”
Never call a wave complete because implementation exists.

## 17. Wave checkpoints and UAT progression

After every accepted macro-wave:

- merge into `mvp/program-integration`;
- execute the required exact-head integration validation;
- record exact SHA, build, database, and counts;
- publish or verify the immutable checkpoint required by the program;
- update the live tracker and acceptance matrix;
- identify the next wave's exact starting SHA and prerequisites.

Read the current finite roadmap from
`docs/07-implementation-plan/mvp-program-state.md` and
`docs/07-implementation-plan/mvp-completion-program.md`. Do not preserve a
changing Wave 4 or Wave 5 status snapshot here.

Full UAT begins only after the accepted backend/UI scope is merged, an immutable
candidate exists, required install/upgrade/security/residue/regression/
concurrency/performance/dev-store evidence is complete, UAT data and access are
prepared, no P0 remains, no P1 blocks an accepted scenario, known limitations
are recorded, and the product owner approves commencement.

## 18. Durable recurring lessons

### 18.1 GitHub truth supersedes stale narrative

PR bodies, handoffs, comments, and chat memory become stale. Verify current
GitHub state and record conflicts.

### 18.2 Partial retrieval is not proof of absence

The incorrect claim that a real PR comment did not exist came from an
unpaginated fetch. Query exact IDs or retrieve all pages before concluding that
a record is absent.

### 18.3 Worker reports require independent verification

Sincere reports can contain wrong branches, stale heads, incomplete file lists,
or unexecuted claims. Inspect exact GitHub and runtime evidence.

### 18.4 Static guards can be false-green

Text matching or a weak AST walk can appear green without proving the receiver,
field, argument, ownership, or control-flow contract. Use adversarial fixtures
and actual runtime where semantics depend on Odoo/PostgreSQL.

### 18.5 Do not substitute review for runtime

Once execution is safe, move to Odoo.sh or the required dev store. Repeated
static inspection has diminishing value and can create churn.

### 18.6 Collect complete failure families

Do not stop a safely executable matrix after the first ordinary failure. Gather
the complete evidence, group by root cause, and issue one coherent correction.

### 18.7 Exact tested bytes matter

A temporary patch, direct reimplementation, or later cleanup commit is a new
artifact. Earlier green runtime does not accept it.

### 18.8 Keep environments separate

GitHub implementation and Odoo.sh runtime are different capabilities. Use
handoffs with exact SHA/diff/checksums; never assume one session can perform
both.

### 18.9 No self-acceptance

Implementation, review, and closure remain independently assigned even when the
same model family performs them in separate sessions.

### 18.10 Large coherent batches need stronger evidence

Speed comes from coherent scope and reduced ceremony, not skipped testing.
Review scrutiny scales with risk and diff size.

### 18.11 Completion is a quality requirement

Over-analysis that prevents runtime, merge, or UAT is a process defect. Maintain
strict safety while progressing through finite gates.

### 18.12 Improvement must be merged and verified

A lesson drafted in a closed or unmerged PR is not durable. Verify the merge and
then verify the live file contains the rule.

### 18.13 Protect unrelated work in progress

Governance and lesson updates use isolated docs-only branches and draft PRs.
Record active heads before the update and recheck them afterward.

### 18.14 Required relational bindings cannot represent ambiguity

If a binding requires one Odoo record, an ambiguous match must not create a
binding row. Route it to manual review and bind only after one identity is
confirmed.

### 18.15 Negative tests may emit expected error logs

Odoo constraint, required-field, SQL, and ACL tests can emit alarming log lines
while passing. Use the complete final summary and asserted outcome.

### 18.16 Human-led setup must complete before live mutation campaigns

A backend service being safe to call is not the same as a customer being able
to reach it. Before authorizing a live-Shopify mutation campaign, verify the
guided setup flow a real operator would use actually exists and actually
reaches every prerequisite (credentials, permissions, location mapping,
readiness) — not just that the underlying models/services are correct.

### 18.17 Readiness must evaluate the configuration it follows

A readiness check run before the settings it depends on are saved is
evaluating stale or absent state, not the operator's actual choices. Order
matters: readiness belongs after the configuration steps it reads, and
changing a readiness-relevant setting must invalidate prior evidence rather
than let it silently carry forward.

### 18.18 Every required prerequisite needs a customer-facing configuration route

If a feature (e.g. inventory sync) requires a prerequisite (e.g. a location
mapping) before it can safely run, that prerequisite needs its own reachable
UI — not just a backend model and service method. "The data model supports
it" and "an operator can do it" are different claims; do not let evidence for
one stand in for the other.

### 18.19 A safe backend service does not prove customer-operable onboarding

Verifying that a sanctioned service method validates and refuses correctly is
necessary but not sufficient. Also verify a real, reachable UI path calls it —
otherwise the safety proof describes code nobody can reach.

### 18.20 Modular internals need one customer-facing product lifecycle

A family of technical addons without a single umbrella application produces
either an incomplete/ambiguous install experience or (if one technical module
is marked `application: True`) a second, unintended customer-facing surface.
Decide the one product lifecycle owner deliberately; do not let it default to
whichever technical module happened to add the UI first.

### 18.21 A simple umbrella dependency graph cannot survive a hard dependency cascade

Verified against the pinned Odoo 19 source (see
[DEC-042](04-decisions/DEC-042-single-package-lifecycle.md)):
`ir.module.module.downstream_dependencies()` is a transitive, unconditional
cascade with no per-dependency opt-out. A package that depends on modules that
could themselves lose a standard Odoo dependency will be swept away in the
same cascade. Verify this dependency-direction consequence from source before
designing any customer-facing package meant to persist through a dependency
loss — do not assume a plain manifest umbrella is safe.

### 18.22 Module uninstall physically deletes module-owned data; resumability requires proof

`ir.model.data._module_data_uninstall` deletes the tables, columns and rows a
module owns when it is uninstalled. A design that claims data survives a
cascade or is later "restored" must prove where that data actually lives (a
surviving module) or produce a genuine, tested snapshot/restore mechanism —
never merely assert survival.

### 18.23 Dependency loss must gate UI, admission, dispatch, and the final network boundary

A single check at one layer (e.g. only the UI) is bypassable by a scheduled
job, a retry, a direct RPC, or sudo-elevated code. Instrument the same
integrity gate at every layer a business operation could originate from,
with the final pre-network-call check as the last, unconditional line of
defense.

### 18.24 Reinstalling a lost dependency must never resume synchronization automatically

Automatic healing after a fail-closed pause converts a safety mechanism into
a silent, unreviewed resume. Require an explicit, staged, administrator-gated
recheck → restore → confirm sequence, and prove (not merely code-review) that
no intermediate stage silently flips the gate back open.

### 18.25 Long wizard/setup steps require real viewport evidence

A design that reads correctly is not proof a sticky action bar, a long
permissions list, or a location-mapping table with many rows actually renders
usably at real viewport sizes (desktop, tablet, mobile) and directions
(LTR/RTL). Capture real, sanitized browser evidence rather than asserting
layout correctness from markup alone.

### 18.26 Campaign identities and credentials must be regenerated after executable changes

A live-Shopify validation campaign's marker, credential, and build identity
are bound to the exact executable SHA they were issued for. Any subsequent
change to `addons/`, `tools/`, or `.github/` invalidates that binding; retire
the prior campaign explicitly rather than reusing its identity against new
code.

### 18.27 Unknown lifecycle behavior must be reproduced, not guessed

Module install/uninstall order, cascade scope, hook timing, and isolation-level
visibility are exactly the kind of Odoo internals that are easy to get subtly
wrong from memory or documentation skimming. Where the pinned source is
ambiguous or the consequence is load-bearing, reproduce the behavior in a
disposable database (see
[`single-package-lifecycle.md`](03-architecture/single-package-lifecycle.md)
§6 for a case where source-reading alone would have missed a real,
transaction-isolation-dependent bug) before relying on it.

## 19. New-session startup protocol

At the start of every ChatGPT control-room session:

1. Read this file.
2. Read `CLAUDE.md` §13 and the accepted decisions it cites.
3. Read `docs/07-implementation-plan/mvp-program-state.md`.
4. Verify the live `mvp/program-integration` tip.
5. Check active PRs/issues and exact relevant heads/bases.
6. Read the latest binding ruling and relevant validation record.
7. Read the current handoff and identify stale/conflicting text.
8. Verify the capabilities of the resource that will receive the next prompt.
9. Determine the active wave, exact next gate, and finite path to UAT.
10. Do not repeat completed research, implementation, review, runtime, or merge
    work.

## 20. Continuous improvement loop

At the end of every substantial control-room session, ask:

- What failed or caused delay?
- Was it a worker, control-room, prompt, runtime, environment, retrieval, or
  stale-source defect?
- What verified evidence supports that classification?
- What stable rule would prevent recurrence?
- Does the rule belong here, in a decision, validation record, debt register,
  or live tracker?
- Did the next action become clearer and closer to UAT?

For a reusable operating lesson:

1. Create a separate docs-only branch from the current verified integration tip.
2. Change only the authorized governance file(s).
3. Open a draft PR; do not self-accept or merge.
4. Run repository/diff/path/link/consistency verification.
5. Obtain independent review and a separate merge/closure action.
6. Verify the merged integration file contains the lesson.
7. Do not claim durable improvement before step 6.

## 21. Stable references

- `CLAUDE.md` §13 — current MVP roles and branch/cadence addendum.
- `docs/04-decisions/DEC-039-mvp-claude-implementation-worker-expansion.md`.
- `docs/04-decisions/DEC-040-mvp-cadence-claude-builder-reviewer-ui-priority.md`.
- `docs/05-qa/runtime-lessons-learned.md`.
- `docs/06-prompts/claude-mvp-wave-review-template.md`.
- `docs/07-implementation-plan/mvp-program-state.md`.
- `docs/07-implementation-plan/mvp-completion-program.md`.
- Shopify official API documentation: <https://shopify.dev/docs/api>.
- Odoo 19 official documentation: <https://www.odoo.com/documentation/19.0/>.

