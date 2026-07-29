# PR #204 — description as it stood before the 2026-07-29 bounded onboarding batch

> **Verbatim archive. Not a new claim.** This file preserves the complete
> description of draft PR #204 (`fable/wave-5-completion` →
> `mvp/program-integration`) exactly as it stood at head
> `d6d44fa6d93ac688d6ca6f187f552586e1616461`, immediately before the bounded
> UAT-critical onboarding batch prepended its own section.
>
> **Why it exists.** The new section plus this record exceed GitHub's
> 65,536-character pull-request body limit. Rather than let any of the
> historical record fall off the end of an edit, the whole of it is kept here,
> in the repository, which CLAUDE.md §3 makes the single source of truth. The
> live PR body retains the new section, the control-room rejection and
> reversion record in full, and the two most recent superseded cycle records;
> everything else is below.
>
> **Nothing here is edited, corrected, re-dated or re-scoped.** Statements in
> it were true of the heads they describe and are superseded — not retracted —
> by the sections above them in the live body. In particular, the
> single-package dependency-recovery work described in the 2026-07-29
> pre-rejection section was **rejected and reverted**; read the reversion
> record in the PR body, not this archive, for its disposition.

---

**`DRAFT — REJECTED BATCH REVERTED — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

# CONTROL-ROOM REJECTION AND ADDITIVE REVERSION OF THE SINGLE-PACKAGE DEPENDENCY-RECOVERY EXPERIMENT

&gt; **2026-07-29. This section is current and supersedes every head-SHA, scope
&gt; and evidence statement below it. Everything below the horizontal rule is
&gt; retained verbatim as the historical record of the rejected experiment and
&gt; of the cycles that preceded it — it is not rewritten, and it must not be
&gt; read as describing the current head.**
&gt;
&gt; **Status: reversion + governance record only. NOT an acceptance, NOT a
&gt; review, NOT a ready-mark, NOT a merge, NOT a runtime, Shopify or UAT
&gt; claim, and NOT a new architecture decision.**

The control room has **REJECTED** the implementation batch from
`4ac4ce2a5144907673fea1b753764823857916aa` (exclusive) through
`69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` (inclusive). It does **not**
proceed to independent acceptance review, Odoo.sh qualification, Shopify
validation, UAT, ready-mark or merge. The rejected architecture was **not
repaired or redesigned** — it was reverted.

| Item | Value |
| --- | --- |
| **Rejected starting head** | `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` |
| **Final head** | `d6d44fa6d93ac688d6ca6f187f552586e1616461` |
| Restored executable checkpoint | `4ac4ce2a5144907673fea1b753764823857916aa` |
| Previously accepted Odoo.sh-tested executable ancestor | `ee23c966a0b214c7974abbade4b384f251c4940f` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor, 0 behind) |
| History operation | **Additive only.** Fast-forward `69562d3..d6d44fa`. No rebase, reset, amend, squash or force-push; 0 merge commits added |
| Changed paths vs `4ac4ce2a` after reversion | **1** — `docs/07-implementation-plan/wave-5-completion-gate-state.md` (the authorized governance record) |
| Executable delta vs `4ac4ce2a` and vs `ee23c966` | **ZERO** under `addons/**`, `tools/**`, `.github/**` |
| Shopify | **none** — no store, credential, request, mutation or webhook, in this cycle or any commit on this PR |

## Exact revert commits

| Commit | Role |
| --- | --- |
| [`6c6cef38d08cb7e855736164618e19c4791f7fc2`](https://github.com/AdamsOdoo/Adams/commit/6c6cef38d08cb7e855736164618e19c4791f7fc2) | Additive revert of all seven rejected commits, applied newest-first |
| [`d6d44fa6d93ac688d6ca6f187f552586e1616461`](https://github.com/AdamsOdoo/Adams/commit/d6d44fa6d93ac688d6ca6f187f552586e1616461) | Documentation-only governance record (`wave-5-completion-gate-state.md` §5e.8) |

**The seven reverted commits, full SHAs, newest-first:**

1. `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`
2. `105314d1373b0c7f6a9e414d2a5da52cef852d3d`
3. `a208a562f1cf9249c9f7e4f0a30e75131a477058`
4. `ffb769c7a8ed6f0a71390f77b8e993d229430a94`
5. `b44ccce24fae99660e10011c2670f94a270e2a2f`
6. `6e622e1ca72d8ce196d824858bff514f4142cc03`
7. `6e1db1d271fce14676ebede9db340c6ad248d7c2`

All seven remain **reachable and unmodified** in this branch&#39;s history. Nothing
at or before `4ac4ce2a` was reverted or modified. Abbreviated SHAs in the
governing instruction were resolved and range-verified before the revert:
`ffb769c` → `ffb769c7a8ed6f0a71390f77b8e993d229430a94`, `b44ccce` →
`b44ccce24fae99660e10011c2670f94a270e2a2f`, `6e622e1` →
`6e622e1ca72d8ce196d824858bff514f4142cc03`.

## Why it was rejected

1. **TD-019 is a feasibility blocker for the rejected architecture, not
   acceptable technical debt.** A standard-dependency cascade physically
   deletes domain-owned mappings, bindings, jobs, logs and mutation
   evidence.
2. That outcome **violates mandatory feasibility invariant H** and should
   have triggered the governing prompt&#39;s **Section 30 no-edit stop** before
   any file was edited.
3. The global resume implementation does not perform **per-store
   selection**, **production-path readiness**, **explicit store
   confirmation**, **interrupted-job reconciliation**, or **prevention of
   automatic queued-work resumption**.
4. The pause record and workflow **omit mandatory audit and recovery facts**.
5. **Restore does not upgrade every component.**
6. The required **setup, mapping, remap, readiness and browser-evidence
   scope was not implemented** — **Sections 15–20 and 26 were not
   delivered**.
7. Customer-facing copy claiming affected components are *&#34;paused
   automatically, not deleted&#34;* is **false**: Odoo removes the modules and
   their owned tables.

**TD-017 and TD-018 were mandatory gaps, not accepted limitations.** The
rejected batch logged them as scoped-out debt; the control room does not
accept that classification — they are the same defects named in reasons 3
and 5. TD-017, TD-018 and TD-019 were introduced by the reverted commits and
do not exist in the restored tree.

## Exact path result

```
$ git diff --name-status 4ac4ce2a5144907673fea1b753764823857916aa d6d44fa6d93ac688d6ca6f187f552586e1616461
M	docs/07-implementation-plan/wave-5-completion-gate-state.md
```

One path — the authorized governance record — and nothing else. The new
`addons/shopify_connector/**` family no longer exists (`git ls-tree
d6d44fa addons/shopify_connector` → 0 entries). All six pre-existing
connector manifests and production files match `4ac4ce2a` byte-for-byte.

## Zero executable-delta proofs

```
$ git diff --name-only 4ac4ce2a d6d44fa -- addons tools .github     # 0 paths
$ git diff --name-only ee23c966 d6d44fa -- addons tools .github     # 0 paths
```

Subtree object-hash equality — the strongest available proof, identical
across all three references:

| Path | `ee23c966` | `4ac4ce2a` | `d6d44fa` (final) |
| --- | --- | --- | --- |
| `addons/` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` | `18735157952d5a7f254e0a558ddedc0f7e6940c4` |
| `tools/` | `eede631173b4f9f006ab572b469084cffc0a05bc` | `eede631173b4f9f006ab572b469084cffc0a05bc` | `eede631173b4f9f006ab572b469084cffc0a05bc` |
| `.github/` | `f109452f4bd4caba17df7c207683308a68f69a27` | `f109452f4bd4caba17df7c207683308a68f69a27` | `f109452f4bd4caba17df7c207683308a68f69a27` |

The revert commit `6c6cef38`&#39;s **whole-repository** tree object is
`0790a57545ade4fccade035df88b3f816febc973`, identical to `4ac4ce2a`&#39;s —
i.e. the reversion restored every path in the repository, not only the
executable ones, before the governance record was added on top.

Static validation at the final head: 7 manifests parse, 49 XML files
well-formed, `compileall` clean over `addons/`, `tools/run_connector_suite.sh`
passes `bash -n`, `connector-tests.yml` parses. Worktree clean, zero
untracked files, no database or artifact residue in the tracked tree.

## Restored evidence baseline

The executable tree is byte-for-byte the tree of
`ee23c966a0b214c7974abbade4b384f251c4940f`, the previously accepted
Odoo.sh-tested executable ancestor. **No new runtime evidence is claimed by
this reversion, and none is required — no new executable tree was
produced.** The Odoo.sh standard-runtime-pass disposition recorded for
`ee23c966` ([comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435))
continues to describe the current executable tree.

The rejected batch&#39;s green local regression results (2069 / 2069 / 39) and
its green GitHub Actions runs **remain historical evidence for the rejected
subset only**. They are not evidence for the restored tree, and they never
established the mandatory requirements the batch failed. **No Odoo.sh,
Shopify, UAT or acceptance claim applies to `69562d34…` — none was ever
made, and none may be inferred.**

## Forward disposition and remaining next gate

- **Dependency-uninstall survival is deferred from the MVP** by the control
  room. No MVP work depends on it.
- **The next implementation addresses UAT-critical onboarding separately**,
  as its own bounded task. This session did not begin it.
- **Remaining next gate:** return to the control room for that bounded
  UAT-critical onboarding task. The Wave 5 gate state at this head is the
  `ee23c966` executable baseline plus documentation; the previously recorded
  next gates for that baseline (independent review of the correction delta,
  then exact-head Odoo.sh validation, then controlled live-Shopify
  validation, then UAT, then the release decision) are unchanged by this
  reversion.

## Not done in this session

**No approval · no ready-mark · no merge · no issue closed · no Shopify
contact of any kind · no credential use · no live campaign · no Odoo.sh run
· no replacement onboarding implementation begun · no architecture decision
created or accepted.** PR #204 remains **draft, open and unmerged**. Issues
#185, #186, #197 and #200 remain open.

**Execution deviation, recorded not silently reconciled.** This session&#39;s
harness designated branch `claude/revert-wave-5-lifecycle-8d62z1` while its
instruction authorised pushing **only** `fable/wave-5-completion`. The
instruction was followed — the identity invariant (local head = remote head
= PR head) is unsatisfiable on any other branch, and this PR could not
otherwise be updated. Same reasoning, same choice, as the two prior cycles
recorded further down this body.

---

&gt; **Everything below this line is the historical record of the rejected
&gt; experiment and the cycles that preceded it. It is retained verbatim and
&gt; unrewritten. Its head-SHA, scope, evidence and &#34;recommended next gate&#34;
&gt; statements are superseded by the section above.**

---

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

| Item | Value |
| --- | --- |
| Head SHA | `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor, 0 behind) |
| Commits · changed paths vs base | **82** · **361 changed paths** |
| **Wave 5 pre-campaign onboarding / single-package-lifecycle commits added after `4ac4ce2a5144907673fea1b753764823857916aa`** | **5 implementation commits** (`6e1db1d`, `6e622e1`, `b44ccce`, `ffb769c`, `a208a56`) + **2 documentation-only evidence/lessons commits** (`105314d`, `69562d3`) · **35 changed paths total** — fast-forward, no amend, rebase, squash or force-push. **The 5 implementation commits are an `addons/**` batch, not documentation-only**; the 2 trailing commits have **zero executable-tree delta** (`git diff --name-only 105314d..69562d3` touches only `CHATGPT.md`) — see the new section below |
| Correction commits added after `ef67c8035e7ee2f6cafd564fcbf2e12153a7e817` | **2 commits** · **17 changed paths** — fast-forward, no amend, rebase, squash or force-push; the five prior commits are untouched |
| Provisioning-package correction commits added after `ee23c966a0b214c7974abbade4b384f251c4940f` | **2 commits** (`dd8ab135f494b5c2085662ef68e920fd1339e21e`, `4ac4ce2a5144907673fea1b753764823857916aa`) · **3 changed paths**, identical set both times (`docs/05-qa/shopify-live-validation-package.md`, `docs/05-qa/val-b2-closure-plan.md`, `docs/07-implementation-plan/wave-5-completion-gate-state.md`) — **documentation-only**, fast-forward, no amend, rebase, squash or force-push; **zero delta** under `addons/`, `tools/`, `.github/` |
| Accepted runtime-tested executable head | `ee23c966a0b214c7974abbade4b384f251c4940f` — the Odoo.sh standard-runtime-pass disposition ([PR comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435)) applies to that SHA. **`a208a56` is a later, materially different executable head** (the new `addons/shopify_connector` package family) and is **not** independently Odoo.sh-validated; the current head `69562d3` inherits that exact same executable tree unchanged (only `CHATGPT.md` differs) — see the new section below for what evidence the executable change does have |
| Evidence class | For the executable tree at `a208a56` (unchanged through `69562d3`, this cycle): **source inspection + disposable-database module-lifecycle harness (7/7 stages, real Odoo installs/uninstalls) + local automated regression suite (2069 fresh / 2069 warm / 39 non-standard, 0 failed/0 errors, up from the 2040/2040/39 baseline)**. No Odoo.sh runtime, no independent review, no live-Shopify contact, no UAT. For the executable code at `ee23c966`: source inspection + local automated tests + local rendered browser evidence, as previously recorded |
| Shopify | **none** — no store, credential, request, mutation or webhook, in any commit on this PR |

## Wave 5 pre-campaign onboarding, location mapping, single-package lifecycle, and dependency-recovery — 2026-07-29

&gt; **Status: implementing-session record. NOT an acceptance, NOT a review, NOT a runtime or UAT claim. This session has not reviewed, accepted, ready-marked, or merged its own work — per CLAUDE.md §13/DEC-040/DEC-041 it may not.**

Five implementation commits (`6e1db1d` → `a208a56`) plus two documentation-only evidence/lessons commits (`105314d`, `69562d3`), fast-forward only from `4ac4ce2a5144907673fea1b753764823857916aa`, no amend/rebase/squash/force-push. The two trailing commits have zero executable-tree delta from `a208a56` — `69562d3` only adds two CHATGPT.md lessons about this cycle&#39;s own evidence-integrity process errors (see below) — so every evidence figure in this section, produced at exact head `a208a562f1cf9249c9f7e4f0a30e75131a477058`, applies unchanged to the current head `69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`.

**What this cycle implements, in one sentence:** a single customer-facing `Shopify Connector` application (`addons/shopify_connector`) that installs the complete six-module technical suite in one action, survives a standard Odoo-dependency loss by entering a durable, administrator-gated `dependency_paused` state (never partial operation, never auto-resume), refuses any direct uninstall of its own technical components (including a crafted co-selection), and correctly cascades its own removal to the whole suite — via Odoo&#39;s own native `downstream_dependencies()` mechanism, no custom uninstall code — when deliberately uninstalled.

**The crux design move, proven from the pinned Odoo 19 source, not assumed:** the six technical modules now depend on the new umbrella (`shopify_connector` depends only on `base`/`web`), the *reverse* of an ordinary umbrella. This is what makes package survival possible at all: `ir.module.module.downstream_dependencies()` is a transitive, unconditional cascade rooted at whatever lost its dependency, so a package that itself depended on the technical modules would be swept away the instant any one of them lost its own standard Odoo dependency. Full derivation, the manifest-graph tables, and the `post_init_hook` one-action-install proof: [`docs/03-architecture/single-package-lifecycle.md`](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/03-architecture/single-package-lifecycle.md). Decision record: [`DEC-042`](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/04-decisions/DEC-042-single-package-lifecycle.md) (status: Proposed, not self-accepted).

**Global gate instrumentation:** `shopify.connector.package.assert_healthy()` is called at every job-admission/dispatch/transport/store-lifecycle boundary already identified as load-bearing in `shopify_connector_core` (`shopify_connector_job_enqueue.py`, `shopify_connector_job_dispatch.py`, `shopify_connector_api_client.py::execute`/`execute_business`, `shopify_connector_store.py`&#39;s connection-probe/activate/reconnect paths) — proven to fire *before* any transport call is reached, not merely alongside it, via a mock that fails the test if the transport method is ever called.

**Also delivered, narrower in scope — location-mapping hardening (`shopify_connector_inventory`):** `create_or_update_location_mapping` now refuses an arbitrary, foreign-store, or inactive Shopify Location GID (it must correspond to a currently-active, this-store cached `shopify.connector.location` row) and populates `shopify_location_name_snapshot` from that validated cached row rather than from caller input, on both the create and idempotent-update paths.

### Disposable-database proof (Section 6/24C) — exact head `a208a562f1cf9249c9f7e4f0a30e75131a477058`

`tools/shopify_connector_package_lifecycle_check.sh` — a standalone harness driving real `odoo-bin`/`odoo-bin shell` module operations (never `TransactionCase`, since Odoo&#39;s own `_button_immediate_function` forbids module operations inside a test transaction). All 7 stages passed:

| # | Stage | Result |
| --- | --- | --- |
| 1 | Fresh one-action install (`-i shopify_connector` installs the whole suite + every standard app it needs) | **PASS** |
| 2 | Warm adoption of a pre-Wave-5 database (six modules under the OLD manifests, `-u`&#39;d to current code) | **PASS** |
| 3 | Standard-dependency loss (`stock`) + package survival, correctly detected as `dependency_paused` | **PASS** |
| 4 | Restore/explicit resume — three-stage, never automatic (recheck → restore → confirm) | **PASS** |
| 5 | Direct component-uninstall refusal, including a crafted co-selection with a legitimate standard app | **PASS** |
| 6 | Complete package uninstall cascades the whole suite via Odoo&#39;s own mechanism | **PASS** |
| 7 | Wider transitive cascade (`product`, bringing down `sale`/`stock`/`account`/all five domain modules) | **PASS** |

Real Odoo module operations throughout every stage; zero Shopify contact.

### Regression qualification (Section 24/25) — definitive final pass, exact head, clean worktree

`tools/run_connector_suite.sh`, `source_head_verified: true` at `a208a562f1cf9249c9f7e4f0a30e75131a477058`, `connector_worktree_dirty: false`, Odoo pin `30bde9ff758834a4912c5ae55843d3a7dad849f1` verified, PostgreSQL 16.13 / Python 3.12.3, zero Shopify operations in any pass.

| Pass | Result |
| --- | --- |
| **Fresh install** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Warm upgrade** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Non-standard tags** | **0 failed, 0 errors of 39 tests** |

Tours: 21 required, 21 executed, 21 success markers, each standard pass. HOOT suites: all three executed and verified (dashboard, export diff, setup wizard). Skip detection: only the sanctioned skip (`TestMutationRecovery.test_real_process_death_harness`). Standard-suite count moved by exactly the tests this cycle added: **2040 → 2069 (+29)** — 12 in `test_package_lifecycle.py`, 5 in `test_uninstall_guard.py`, 9 in `test_package_pause_gates.py`, 3 in `test_location_mapping.py`; none silently dropped. Non-standard stayed at **39**.

**Process error disclosed rather than hidden:** a first attempt at this run was invalidated mid-run because source files were edited while an earlier pass was still executing against a different code state — caught by this session, discarded, and re-run cleanly only after every edit was committed. A second attempt was flagged `connector_worktree_dirty: true` because a leftover artifact directory from the discarded run had been moved to an untracked path inside the repository; relocated outside the repository and the run repeated cleanly, producing the numbers above. Both mistakes are now logged as their own lessons ([CHATGPT.md §18.28](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/CHATGPT.md)). Full account: [`wave-5-completion-gate-state.md` §5e.8](https://github.com/AdamsOdoo/Adams/blob/69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe/docs/07-implementation-plan/wave-5-completion-gate-state.md).

### HEADLINE finding — TD-019 (High), from this cycle&#39;s own adversarial self-review, disclosed prominently, not narrowed

**Domain-owned data does not survive a standard-dependency cascade.** Only the package controller&#39;s own state (`shopify.connector.package`, which lives in the never-cascaded `shopify_connector` module) survives. Shopify location mappings, product/customer/order bindings, inventory-level bindings, their jobs/job logs, and mutation-attempt evidence all live in the five domain technical modules, and Odoo&#39;s own `module_uninstall()` physically drops those modules&#39; tables the moment a standard-dependency loss cascades them away.

**Verified empirically, not merely reasoned about:** a `shopify.connector.location.mapping` row was created, `stock` was uninstalled (cascading `shopify_connector_inventory` away, exactly as designed), and `SELECT to_regclass(&#39;shopify_connector_location_mapping&#39;)` against the same database returned `NULL` immediately afterward — the table itself no longer exists. Restoring the suite recreates it empty; it cannot restore the deleted rows.

**Why this was not fixed in this cycle:** the two proven-safe patterns (move the data&#39;s ownership into a surviving module, or build a durable versioned snapshot/restore mechanism) both require materially altering the five domain modules&#39; own data ownership/semantics — outside this task&#39;s allowed-file scope for those modules, and a control-room design decision this session may not make unilaterally. Logged as **TD-019 (High)** in the technical-debt register, with the full empirical proof in `single-package-lifecycle.md` §6a and the consequence recorded in DEC-042&#39;s &#34;Negative / trade-offs&#34; section.

### Scoped out of this cycle, explicitly, and logged rather than silently narrowed

- **TD-017** — no dedicated per-store resume-selection UI; the package-level gate is a global circuit breaker layered on the existing per-store readiness/activation machinery (`shopify_connector_core`, unchanged by this cycle).
- **TD-018** — `action_restore_suite` reinstalls missing components but does not also force-upgrade already-installed ones; left to Odoo&#39;s own ordinary Apps &#34;Upgrade&#34; action.
- The full location-mapping setup flow/workspace (Sections 18–19 of the governing task) beyond the GID-validation hardening above — the setup wizard, remap-with-audited-reason flow, and per-location readiness workspace are not built in this cycle.
- The full 29-module standard-dependency closure is not individually cascade-tested; the harness proves the three representative cascades the task specifies (`stock`, `product`, complete package uninstall).
- No browser/viewport evidence was captured for the new package status view (a minimal Odoo-native form with a statusbar and three buttons).

### Not claimed

**No Odoo.sh runtime · no independent review of this head · no live-Shopify contact of any kind · no UAT · no acceptance, ready-mark, or merge.** The implementation worker has not reviewed, accepted, or approved its own work, and per CLAUDE.md §13/DEC-040/DEC-041 may not. PR #204 remains draft, unapproved and unmerged.

### Recommended next gate

A fresh, independent Claude review of this exact head (`69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`) — a separate top-level session or a fresh subagent invocation that adversarially re-verifies rather than summarizes, per DEC-040 — covering in particular: the reverse-dependency architecture and its disposable-database proof, the REPEATABLE READ fix in `_commit_via_side_cursor`/`_apply_detected_state`, the uninstall-guard&#39;s crafted-co-selection refusal, the location-mapping GID-validation hardening, and above all a control-room ruling on TD-019 (accept the domain-data-loss gap as MVP behaviour, or authorize a Pattern A/B follow-up). Then, if accepted, a separate closure session before any ready-mark or merge — never this one.

---

## Provisioning-package correction — 2026-07-28 (post-runtime-disposition)

&gt; **Status: documentation-only correction record. NOT an acceptance, NOT a
&gt; review, NOT a new runtime or UAT claim, NOT provisioning or campaign
&gt; execution.**

After the control room recorded the Odoo.sh standard-runtime-pass disposition
for `ee23c966a0b214c7974abbade4b384f251c4940f`
([PR comment `5103678435`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5103678435))
and a provisioning-readiness checklist on issue #200
([comment `5103684847`](https://github.com/AdamsOdoo/Adams/issues/200#issuecomment-5103684847)),
a session-independent source audit found that checklist&#39;s credential-scope
section — carried forward from `docs/05-qa/shopify-live-validation-package.md`
§2.3 — was internally contradictory: it required execution of the M-EXP-*
product/media mutation cases while its own scope table excluded
`write_products` and `write_files` as forbidden. Two documentation-only
commits corrected this and three further consistency gaps found while
finalizing the correction:

1. **`dd8ab135f494b5c2085662ef68e920fd1339e21e`** — re-derived the
   consolidated Shopify scope set directly from the frozen source
   (`shopify_connector_readiness_check.py` in core and fulfillment,
   `shopify_connector_inventory_service.py`,
   `shopify_connector_product_export_seams.py`) and current official Shopify
   2026-07 GraphQL Admin API documentation (`productUpdate`/`productSet`/
   `productVariantsBulkUpdate` → `write_products`; `fileUpdate` → `write_files`
   or `write_themes`; `inventorySetQuantities`/`inventoryActivate` →
   `write_inventory`): the six-scope `REQUIRED_MVP_SCOPES` read baseline
   (`read_products`, `read_customers`, `read_orders`, `read_inventory`,
   `read_locations`, `read_merchant_managed_fulfillment_orders`) plus
   `write_inventory`, `write_merchant_managed_fulfillment_orders`,
   `write_products` and `write_files` — ten scopes total. `write_themes`
   stays explicitly forbidden. `read_assigned_fulfillment_orders` /
   `write_assigned_fulfillment_orders` were removed — neither name appears
   anywhere in `addons/`, and assigned-fulfillment-order scopes govern a
   different mechanism (fulfillment-service-app assignment) from the
   merchant-managed `FulfillmentOrder` model this connector uses exclusively.
   Also corrected: `val-b2-closure-plan.md` §4 still named the pre-TD-002/
   D-014-2 scope `read_fulfillments` instead of the shipped check&#39;s actual
   `read_merchant_managed_fulfillment_orders`; and §7 classified a 24-hour
   client-credentials-only outcome as an unqualified FAIL, contradicting §8&#39;s
   existing PARTIAL/QUALIFIED framing — §7 now separates PASS / PARTIAL /
   FAIL as three distinct outcomes.
2. **`4ac4ce2a5144907673fea1b753764823857916aa`** — a control-room addendum
   found three further documentation-consistency gaps and authorized this one
   additional additive commit (never amending `dd8ab135`): (a)
   `shopify-live-validation-package.md` §1&#39;s entry criteria E2/E3 conflated
   &#34;the connector SHA under test&#34; with the Odoo.sh-validated executable head
   via a single `git rev-parse HEAD` — corrected to record the current
   campaign/package head and the accepted runtime-tested executable head
   separately, with a zero-executable-delta proof requirement and a
   fresh-qualification trigger if that delta is ever non-zero; (b)
   `val-b2-closure-plan.md` §10 point 5 read &#34;if VAL-B2 fails (including the
   qualified/partial case in §8),&#34; folding PARTIAL back into FAIL — corrected
   so FAIL and PARTIAL are named as distinct, independently-escalated
   outcomes; (c) `wave-5-completion-gate-state.md` §5e.6 had pre-claimed the
   PR #204 and issue #200 correction comments as &#34;posted this session&#34; before
   they were posted — corrected to accurate sequencing.

**Zero executable-tree delta, both commits combined:**
`git diff --name-only ee23c966a0b214c7974abbade4b384f251c4940f..4ac4ce2a5144907673fea1b753764823857916aa -- addons tools .github`
is empty. Only the three documentation paths above changed, identically in
both commits. **`EXECUTABLE TREE UNCHANGED FROM THE ACCEPTED ODOO.SH
STANDARD-RUNTIME HEAD.`** GitHub Actions ran green at this final head:
run [`30359073374`](https://github.com/AdamsOdoo/Adams/actions/runs/30359073374)
(`push`) and run [`30359078999`](https://github.com/AdamsOdoo/Adams/actions/runs/30359078999)
(`pull_request`), both `completed`/`success`, head SHA
`4ac4ce2a5144907673fea1b753764823857916aa` — supporting evidence only
(DEC-041 D8), not a new Odoo.sh claim; none was made or required, since a
zero-executable-delta descendant inherits the disposition of the executable
head it descends from.

**No Shopify resource was provisioned or contacted.** Issues #185, #186,
#197 and #200 remain open. This PR remains draft, unapproved and unmerged.
Full record: PR comment `CONTROL-ROOM PROVISIONING-PACKAGE CORRECTION` and
issue #200 comment
`AUTHORITATIVE CORRECTION TO PROVISIONING READINESS COMMENT 5103684847`.

## Correction record — independent review `5100097485` (2026-07-28)

This PR&#39;s implementation-freeze head `ef67c8035e7ee2f6cafd564fcbf2e12153a7e817` received an independent review ([comment `5100097485`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5100097485), by a session with no access to this one&#39;s reasoning) that returned **B — HOLD: CORRECTION REQUIRED**: three P1 and two P2-material defects, none refuted under adversarial verification. This section is the correction of all five, by a fresh top-level session that neither produced nor reviewed that finding and has not reviewed or accepted this correction either.

**Correction commits:** `159e0a67f0bbbac20ddee97134c42253a8801f13` (production correction — all 5 findings), `ee23c966a0b214c7974abbade4b384f251c4940f` (SEC-3 inventory reconciliation + Shopify citation).

### Disposition of each finding

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | P1 | Cross-company confidentiality bypass via the TD-015 checksum wizard&#39;s unscoped ACL + default-sudo related fields | **Fixed.** `related_sudo=False` on `store_id`/`product_gid`/`reconcile_note` (protects every access path — `read()`, `search_read()`, `default_get()`, an onchange — not only the routes this wizard&#39;s own methods call); `_resolve_binding_for_ack` reached from `create()`/`write()`/`default_get()` (validated *before* `default_get()`&#39;s base implementation runs), delegating to the existing `_assert_export_reconcile_ack_authority` gate on the binding — the identical check the two production actions already enforce; a new creator-scoped `ir.rule` on the wizard model itself; foreign and nonexistent bindings collapse to one indistinguishable refusal (`check_access` can raise `AccessError` or `MissingError` for the two cases respectively — verified against the pinned Odoo 19 `fetch()` — and both are caught). |
| 2 | P1 | Connect-only setup could never activate, contradicting the accepted UX spec and the wizard&#39;s own on-screen copy | **Fixed.** `_check_domain_flag_enablement` downgraded ESSENTIAL → WARNING. Connect-only remains explicit (the step-11 review screen already shows zero domains before activation), enables no domain, schedules no job, contacts no Shopify endpoint. |
| 3 | P1 | A Catalog-export-only setup could also never activate | **Fixed.** New `_accepted_domain_flags()` extension seam, the same shape `_get_checks()` already uses; `shopify_connector_product_export` registers `product_export_domain_enabled` through it instead of a fixed core tuple. The identical fixed-constant pattern was found and fixed in the S1 step-4 scope-display list (`_governed_scope_catalog()`), which was not itself a review finding but the same root cause. |
| 4 | P2-material | A truncated remote media read could still reach the acknowledgeable `checksum_unverifiable` verdict whenever every connector-claimed File happened to land on the page that was read | **Fixed.** `_remote_media_divergence` now checks `read.get(&#39;truncated&#39;)` independently of, and before, the &#34;every claimed File found&#34; branch. |
| 5 | P2-material | Acknowledgement re-validation was capped at `EXPORT_RECONCILE_REVIEW_LIMIT` (200, a UI-sizing constant), unordered | **Fixed.** Deterministic keyset pagination (`id &gt; last_id`, `order=&#39;id asc&#39;`) over a new, separate constant `RECONCILE_REVALIDATION_BATCH_SIZE` walks every matching `review`-state binding regardless of how many batches that takes. `EXPORT_RECONCILE_REVIEW_LIMIT` is untouched and stays a presentation-only constant. |
| P3 | non-blocking | `_resolve_store`&#39;s `exists()`-before-`check_access()` let a same-role cross-company Administrator learn a foreign store id merely exists | **Fixed.** Removed the unfiltered `exists()` pre-check; `check_access` alone (catching both `AccessError` and `MissingError`) collapses foreign and nonexistent store ids to one generic refusal. |
| P3 | non-blocking | `test_the_wizard_model_is_not_readable_by_a_connector_user` only asserted `create()`, despite its name | **Fixed.** Extended to assert `read()` and `search()` refusal too, against a wizard row an Administrator legitimately created. |
| — | citation gap | The `[Fact]` claim that Shopify&#39;s GraphQL Admin API exposes no media-byte checksum lacked a captured, dated, URL-cited excerpt (CLAUDE.md §7) | **Fixed.** `docs/00-source-materials/shopify-media-checksum-citation-2026-07-28.md` — both pages fetched live 2026-07-28, API version **2026-07**, **Accessible**, exact field lists captured, fact/inference boundary stated explicitly. |

### Wizard company-isolation enforcement, exactly

`create()`, `write()` (when `binding_id` is present) and `default_get()` all resolve a caller-supplied `binding_id` through `_resolve_binding_for_ack`, which delegates to `binding._assert_export_reconcile_ack_authority()` — Administrator role, `check_access(&#39;read&#39;)`, `store.company_id in env.companies`, all before any elevation, and all reached before the wizard&#39;s related display fields could ever compute. `store_id`/`product_gid`/`reconcile_note` additionally carry `related_sudo=False` as defense in depth. A new creator-scoped `ir.rule` (`[(&#39;create_uid&#39;, &#39;=&#39;, user.id)]`) stops even a legitimately-created wizard row from being `search_read()`-visible to any other Administrator. `@api.constrains` was considered and rejected: Odoo runs constraint methods with `self` already `sudo()`&#39;d, which would have silently no-op&#39;d the whole check. A same-company positive control (`test_a_same_company_administrator_still_sees_an_authorized_wizard`) proves none of this narrows the happy path.

### Connect-only / Product-Export-only activation, exactly

Both driven through the real production route (`shopify.connector.setup.wizard.activate()`), transport stand-in fails the test if reached at all:
- `test_a_genuine_connect_only_store_can_activate` — step 7 with an empty selection through to `activate()`; asserts `state == &#39;connected&#39;`, all four core domain flags stay `False`, no job admitted.
- `test_a_product_export_only_store_can_activate_through_the_setup_wizard` — only `product_export_domain_enabled=True`; activation succeeds, no export job admitted, no unrelated domain silently enabled.

### Truncated-read fail-closed behavior, exactly

Reordered: `hasNextPage` is checked before &#34;every claimed File found,&#34; not after. Regression: `hasNextPage=True` with every claimed File GID present on the returned page now asserts `media_read_truncated` (not `checksum_unverifiable`); the binding stays unacknowledgeable and the store stays `review_required`. The pre-existing &#34;truncated + a claimed File missing&#34; test is preserved unchanged.

### Complete acknowledgement-revalidation mechanism, exactly

`_reassert_export_reconcile_acknowledgements` walks `review`-state bindings in deterministic keyset-paginated batches until a batch returns smaller than the batch size, reaching every matching row. Regression: 220 acknowledged review bindings, one stale beyond position 200 by id — reached, store re-blocked to `review_required`, all 219 siblings&#39; acknowledgements independently proven still valid; a companion 220-valid-population test proves the walk converges to `complete` (not a vacuous permanent block).

### Corrected post-correction SEC-3 inventory

Recounted from the exact source (`docs/03-architecture/sec3-company-isolation-audit.md` §8, corrections in §8.1–§8.9), not copied from the review:

| Category | Was (stale, propagated to 3 tracker docs + this body) | Now |
| --- | --- | --- |
| Models | 2 | 2 (unchanged) |
| Stored fields | 17 | **20** (arithmetic error + 2 wizard-owned fields never itemized: `binding_id`, `confirmed`) |
| Non-stored computed fields/relations | &#34;1 computed relation&#34; | **7** (the wizard&#39;s six related/computed display fields were never itemized) |
| Public/RPC methods | 20 | **18** (overcount, recounted one by one) |
| Elevated methods / `sudo()` call sites | &#34;14&#34; | **15 methods / 19 call sites** (&#34;14&#34; was `shopify_connector_core`&#39;s own count presented as the whole delta&#39;s total) |

Counting conventions, stated explicitly in §8: &#34;public/RPC methods&#34; = unique externally callable, non-underscore-prefixed production methods; &#34;elevated methods&#34; = unique production methods containing a `.sudo()` call; &#34;sudo call sites&#34; = individual syntactic `.sudo()` occurrences. The TransientModel wizard&#39;s `binding_id` — a genuine connector-to-connector Many2one — is now itemized; it is the exact scoping gap the review traced Defect #1&#39;s root cause to.

### Official Shopify documentation citations, and the bounded inference

[`MediaImage`](https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImage) and [`MediaImageOriginalSource`](https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImageOriginalSource), API version **2026-07**, accessed **2026-07-28**, **Accessible**. `MediaImageOriginalSource` exposes `fileSize` (a byte count) and a temporary `url`; neither object&#39;s documented field list exposes a checksum/digest. **[Inference]:** the connector therefore cannot prove stored-byte correspondence using those documented fields alone — not that Shopify has no checksum anywhere in any system, not that bytes were independently compared, not that live-Shopify validation occurred.

### Qualification — definitive pass, exact head, clean worktree

`tools/run_connector_suite.sh`, exact head `ee23c966a0b214c7974abbade4b384f251c4940f` verified by the runner itself (`source_head_verified: true`), exact base `87f1763a1ca699947d665c92bef614bd1fc3168d`, worktree clean (`connector_worktree_dirty: false`), Odoo pin `30bde9ff758834a4912c5ae55843d3a7dad849f1` verified, PostgreSQL 16.13 / Python 3.12.3, zero Shopify operations in any pass.

| Pass | Result |
| --- | --- |
| **Fresh install** + standard suites | **0 failed, 0 errors of 2040 tests** |
| **Warm upgrade** + standard suites | **0 failed, 0 errors of 2040 tests** |
| **Non-standard tags** | **0 failed, 0 errors of 39 tests** |

Tours: **21 required, 21 executed, 21 success markers** (verified by test-identity attribution) in each standard pass. HOOT suites: **all three executed and verified** — dashboard, export diff, setup wizard. Skip detection: only the sanctioned skip (`TestMutationRecovery.test_real_process_death_harness`); zero skips in the non-standard pass. Standard-suite count moved by exactly the tests this correction added: **2017 → 2040 (+23)** — every new Correction A/B/C/D/E regression is present and passing, none silently dropped. Non-standard stayed at **39** (no non-standard test added or removed by this correction).

**GitHub Actions, exact head, supporting evidence (DEC-041 D8 — not Odoo.sh, not acceptance):** run [`30334291201`](https://github.com/AdamsOdoo/Adams/actions/runs/30334291201) (`pull_request` event) — `completed` / `success`, head SHA `ee23c966a0b214c7974abbade4b384f251c4940f`; run [`30334288881`](https://github.com/AdamsOdoo/Adams/actions/runs/30334288881) (`push` event) — `completed` / `success`, same head.

### Not claimed

**No Odoo.sh runtime · no independent review of the corrected head · no live-Shopify contact of any kind · no UAT · no acceptance, ready-mark or merge · no release-readiness.** **Issue #197 remains open.** The independent review at `ef67c803` was a **HOLD**; this corrected head has **not yet received independent correction-delta re-review**. This PR remains **draft, unapproved and unmerged**. The five commits frozen at `ef67c803` were **not rewritten**.

**Provenance note, flagged not silently fixed:** both correction commits carry committer `noreply@anthropic.com` (the correct, repository-configured identity — no repeat of the earlier `aysaadab@gmail.com` deviation) but are unsigned, so GitHub will show them *Unverified*. No CODEOWNERS file, branch-protection config, or CLAUDE.md clause requiring signed commits exists in this repository (independently re-confirmed this session). Not corrected here: the only remedy is `--amend`, which this cycle&#39;s instruction forbids outright and which would also invalidate the exact-SHA qualification evidence above.

### Recommended next gate

**Freeze this exact corrected head for a fresh independent correction-delta and security re-review** — a separate top-level session or a fresh subagent, never this one. Then exact-head Odoo.sh validation, then controlled live-Shopify validation, then UAT, then the release decision.

---

The previous cycle made the checksum disposition fail closed — correctly, on good evidence — and wrote, in the code and in this body, that &#34;an operator must clear it before exports resume.&#34;

**No route existed that could clear it.** The only public action re-RAN the pass: it re-read the same product, re-derived the same unprovable checksum and recorded the same `review`. The binding verdict fields are protected, so no direct write could clear them. And `export_reconcile_state` was rendered on **no screen anywhere in the product** — not on the store form, not in the Export branch, nowhere.

So a reconnected store that had ever exported product media was blocked from exporting **permanently, by construction**, and the operator had nothing to click. Failing closed with no door is not a fail-closed design; it is an outage with a good explanation.

## Commits after `98334c7a`

| Commit | Item |
| --- | --- |
| `a65ed11c745c2335b467c1ad2051218fdb20d07d` | TD-015 — give the checksum review a door an operator can open |
| `81b3032be3cdd29e02b9445b9f22dc88d4dd02c0` | S1 — implement the accepted 11-step guided setup wizard |
| `c0e472f49b7710bb6294d8248cf46d3968dbd00f` | SEC-3 inventory and trackers — state what is true at this head |
| `caa5b264cdba7ea8eec676bb9ef2f8beba097fbb` | S1 — load the setup views after the menu they hang off |
| `ef67c8035e7ee2f6cafd564fcbf2e12153a7e817` | TD-015 — register the new binding fields in the product module&#39;s inventory |
| `159e0a67f0bbbac20ddee97134c42253a8801f13` | **Correction cycle** — fix all 5 findings from independent review `5100097485` |
| `ee23c966a0b214c7974abbade4b384f251c4940f` | **Correction cycle** — SEC-3 inventory reconciliation and Shopify media-checksum citation |

## Correction A — TD-015, one resolvable review and only one

Eligibility is a stored `Selection`, `export_reconcile_reason`, **not** a substring of the operator-facing note. Parsing a note would make a copy edit a security change.

`checksum_unverifiable` is reached only from the branch where the remote read has already established: the connector is bound to the expected Shopify store; the expected product exists and is not archived; every bound variant is still present; every claimed File GID was found on that product; none is `FAILED`; and the response was complete rather than truncated (independently re-verified and corrected this session — see the correction record above, Defect #4). The single remaining unknown is the byte digest, which the 2026-07 `MediaImage` / `MediaImageOriginalSource` interface does not expose at all (now cited per CLAUDE.md §7 — see the correction record above).

Every other reason — `product_missing`, `product_archived`, `variant_divergence`, `media_association_unrecorded`, `media_in_flight`, `media_local_checksum_missing`, `media_not_reread`, `media_product_reread_failed`, `media_failed_status`, `media_read_truncated`, `media_absent` — is refused. There is no general-purpose override anywhere on the route.

**Authority.** `group_shopify_connector_admin` only. Not Reviewer: under the accepted SEC-2 model `group_shopify_connector_user` implies `group_shopify_connector_reviewer`, so a Reviewer gate would have admitted every ordinary Connector User. Record access (`check_access(&#39;read&#39;)`) and company consistency (`store.company_id in env.companies`) are both checked **before** anything elevates — and, as of this correction, so is the wizard-model boundary itself (see the correction record above, Defect #1).

**Binding and invalidation.** The acknowledgement is bound to the connection generation, the binding, the remote product GID, the remote File GID set and a SHA-256 digest of the local media claim. `_export_reconcile_ack_is_valid` re-derives every one of those on each read rather than trusting a stored flag, so a later reconnect, a fresh pass, a re-pointed product, a re-uploaded File, a renamed file or a changed local checksum withdraws it automatically. The store&#39;s own export assertion re-checks outstanding acknowledgements and re-applies the block if one stopped matching — now walking every outstanding review rather than the first 200 (see the correction record above, Defect #5) — which is what makes those rules load-bearing rather than decorative.

**No Shopify contact.** Proved twice: by a transport stand-in that fails the test if it is reached at all, and by an AST guard over the route&#39;s source.

**Acknowledgement is not verification.** Byte correspondence was not cryptographically proven. The operator dialog, the audit record and the store note all say so, and the note for a `complete` reached this way names the acknowledgement count and its exact limit.

The UI route is the store&#39;s existing reconciliation surface — no second review centre, no extra menu, no parallel state machine: **Stores → the store → *Bindings awaiting review* → *Acknowledge* → the consequence dialog**. A browser tour walks exactly that and asserts the four required statements are on screen before the confirmation is possible.

## Correction B — S1, the 11-step guided setup wizard

S1 was recorded as not implemented, and it was. The pieces existed and were correct — a credential service, a readiness registry with an accepted essential/warning split, per-domain settings fields, an activation contract with a real evidence bar — and there was no route through them. `shopify.connector.store` carries `create=&#34;false&#34;` on both its list and its form, so there was no way to create a store at all outside a data import or a `sudo()` call.

One bounded Owl client action inside the normal web client, and one `AbstractModel` service behind it. It owns no business rule: every step delegates to the service that already owns the decision, and every durable choice is written to the field that already owns it. It keeps no state of its own — the only new data is the resume point and who completed or re-ran setup, on the settings row, inheriting its company and its SEC-3 rules.

| Step | What it does | Where the decision lives |
| --- | --- | --- |
| 1 Welcome | hosting disclosure up front, not mid-flow | — |
| 2 Store identity | creates/renames the store; shape validation only | identity is *confirmed* by the readiness store-identity check |
| 3 Credentials | write-only, cleared from the DOM on submit | `store.credential.action_set_token` / `action_replace_token` |
| 4 Permissions | scopes with a business reason, derived from a governed, extensible catalog (corrected this session — see above) | the wizard never claims it grants scopes |
| 5 Test connection | explicit action; pass or actionable failure shown on the step | `store.action_test_connection` |
| 6 Readiness | per-check result, tier, reason and owner | `readiness.check.run_for_store` |
| 7 What to sync | only DEC-003 directions; unsupported ones absent, not disabled | the owning settings flags |
| 8 Source of truth | both required, **neither pre-selected** | `product_first_sync_source`, `price_source_of_truth` |
| 9 Notifications | off by default; opt-in takes an explicit consequence confirmation | sets **both** halves of the RA-009 fail-closed pair |
| 10 First stock push | schedules only; the preview/confirm guard is untouched | `inventory_scheduled_sync_enabled` |
| 11 Review and activate | plain-language summary; blocked on a failing essential check | `store.action_activate` |

**Administrator only, on every entry point including the read.** `ir.actions.client` carries no `group_ids` in Odoo 19, so the action cannot be group-restricted at all — which is exactly why the enforcement lives on the methods.

**Three entry routes, all driven in a browser:** the dashboard first-run empty state, Configuration → Setup Wizard, and Re-run Setup on the store form. Re-running resets the resume point and changes not one stored choice.

Steps 5 and 6 run their check on an explicit action and stay put to show the result; a Continue that ran the probe and advanced in the same click would never show an operator either the pass or the actionable failure. Activation re-runs readiness first, because the accepted order puts readiness at 6 and the domain and ownership choices at 7–10 — the step-6 result describes a store that did not yet have any of them.

**Activation starts no synchronisation, enqueues no job and makes no Shopify request** — asserted with a transport stand-in that fails the test if it is reached, now proven for connect-only and Product-Export-only configurations too (see the correction record above, Defects #2/#3).

## Correction C — SEC-3 delta

See the corrected inventory in the correction record above; the numbers here are superseded. Issue #197 remains OPEN throughout.

## Correction D — present-tense trackers

Corrected only where the claim was demonstrably false against the source:

- **S1** read &#34;Not implemented&#34;. It was, until this cycle.
- **U3** read &#34;the rest of U3 is not implemented (TD-006)&#34;. The Owl surface, its tours, its HOOT suite, S25/S26 and S31 all exist at this head.
- **Roles/permissions** read &#34;SEC-2/SEC-3 pending&#34;. SEC-2 #196 is closed.
- **End-to-end tests** read &#34;No CI&#34;. `.github/workflows/connector-tests.yml` has existed and runs three passes against the pinned Odoo. What stays true is the part that matters: CI is supporting evidence, not acceptance.
- **TD-002** read &#34;owned by PR #189&#34; in four places. That PR is merged.
- **U1**, **Product Export** and **SEC-2** were re-read and their present-tense statements already matched the source.

Historical records were left as historical records. No old test or validation record was rewritten to imply it covered later commits.

## Three defects found while doing the above, and fixed here

1. **A cross-company field-cache leak.** The store-form review list is a non-stored computed field whose contents the caller&#39;s record rules filter, and Odoo caches such a field **once per record for the whole transaction** unless it declares its context dependency (`Environment.cache_key`). Without `depends_context` the first reader&#39;s result is served to the second — including owner-first, which would have handed one company&#39;s outstanding reviews to another company&#39;s administrator. Fixed and asserted in both orders.
2. **Readiness could not run for an ordinary Connector Administrator.** It read `web.base.url` unelevated, and system parameters are `base.group_system` in Odoo 19 — so the whole readiness run raised `AccessError` for any connector administrator who is not also an Odoo system administrator. Reachable in production through `action_reconnect`, before S1 existed.
3. **The suite runner&#39;s fail-closed self-test hand-listed a copy of its own HOOT inventory**, which went stale the moment a third suite was added. It is generated from the inventory now.

Two more were caught by the qualification itself rather than by me, which is the argument for running it. The setup views were loaded before the menu they hang off — invisible on a warm `-u` update, a hard `ParseError` on a fresh install, exactly the failure family that pass exists for (issue #193). And `shopify_connector_product` keeps its own exact-inventory guard over the template binding&#39;s protected field set; the thirteen fields TD-015 adds were classified in the export module&#39;s guard and not in that one. Both are fixed above, and each forced a full restart of the qualification.

## Retained limitations — NOT resolved

- **TD-004** — media replacement is append-only. No `fileDelete`, no automatic detach.
- **TD-005** — media export requires `write_files`, which grants write access to every file in the store. `write_themes` is never requested.
- **TD-007** — a divergent existing remote option structure is refused, never restructured.

**TD-002&#39;s backend implementation is accepted and merged through [PR #189](https://github.com/AdamsOdoo/Adams/pull/189)** (merge `3a1afa43`, accepted head `e12145ce`, runtime candidate `25639f17`). Its **deferred live-Shopify validation, Gate D, [CV-013 #185](https://github.com/AdamsOdoo/Adams/issues/185), external UAT and final release evidence remain open** and are claimed by nothing here. **This head does not have zero technical debt, and this body does not claim it does.**

## Not claimed

**No Odoo.sh runtime · no independent review of this corrected head · no live-Shopify contact of any kind · no UAT · no acceptance, ready-mark or merge · no release-readiness.**

`M-EXP-1 … M-EXP-20` **all remain outstanding**. `X-EXPORT-0` remains **neither PASS nor FAIL**. **Issue #197 remains open.**

The implementation worker has **not** reviewed, accepted or approved its own work, and may not.

## Execution deviations recorded rather than reconciled silently

**Branch (prior cycle).** That session&#39;s harness designated `claude/pr-204-freeze-cycle-8tks3v` while its instruction authorised pushing **only** `fable/wave-5-completion`. The instruction was followed and only `fable/wave-5-completion` was pushed.

**Branch (correction cycle before this one).** That session&#39;s harness designated `claude/pr-204-review-corrections-k1ue5k` while its instruction authorised pushing **only** `fable/wave-5-completion`. The same reasoning applies and the same choice was made: only `fable/wave-5-completion` was pushed — the identity invariant (local head = remote head = PR head) is unsatisfiable on any other branch.

**Committer identity — flagged, not silently fixed (prior cycle).** The five commits of the implementation-freeze cycle carry committer `aysaadab@gmail.com`, while the branch&#39;s preceding 66 commits carry `noreply@anthropic.com`. GitHub shows these five as *Unverified*. Not corrected: the only remedy is `--amend`/`rebase` plus a force-push, forbidden outright by that cycle&#39;s instruction and this one&#39;s, and rewriting would destroy the frozen head every qualification pass above and below names. **This correction cycle&#39;s own two commits do not repeat this deviation** — both carry the correct `noreply@anthropic.com` — but remain unsigned (see the correction record above).

**This is a control-room decision, not a worker one.**

## Recommended next gate (superseded by the 2026-07-29 cycle above)

Superseded by the correction record above and now by the 2026-07-29 single-package-lifecycle cycle at the top of this body: **freeze the current exact head (`69562d34ae4f37e6eb2dbd4aa2f0a91250119cfe`) for a fresh independent review** — a separate top-level session or a fresh subagent, never this one — targeting, in addition to everything the correction record above already asked for, whether the reverse-dependency package architecture and its disposable-database proof are genuinely sound, and a control-room ruling on TD-019. Then exact-head Odoo.sh validation, then controlled live-Shopify validation, then UAT, then the release decision.

---
_Generated by [Claude Code](https://claude.ai/code)_
