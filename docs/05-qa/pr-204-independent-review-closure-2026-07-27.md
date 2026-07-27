# PR #204 — independent-review closure record

> **This record claims no acceptance.** It is the disposition of the final
> independent review's findings against PR #204, produced by the correction
> session, which is not an independent reviewer of its own work. The
> corrected head still requires a fresh bounded independent re-review before
> any external validation.

| Field | Value |
| --- | --- |
| Branch | `fable/wave-5-completion` |
| Starting head (reviewed SHA) | `9cb7e38a736f04d38684219092fb90c839b45e27` |
| Recovery checkpoint after the first correction cycle | `2b704b9c756a2cdce5bae87363b1656d379852b9` |
| Corrected head this record describes | see PR #204 — the final cycle added 9 commits, fast-forward from `2b704b9`, with no amend, rebase, squash or force-push |
| Bound base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor) |
| Review artifact | `Pasted text(94).txt`, SHA-256 `e071f34150c8b715e70c3df1a88e4ab0334b19b252136a598961c7cce2b30ae5` (authoritative digest per the 2026-07-27 continuation ruling; the digest named in the original correction prompt did not match any normalization of the file and was corrected by ruling) |
| Authoritative content | from the heading `PR #204 — Final Independent Review` to end of file |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1`, cloned and verified this session |
| `rtlcss` | **4.3.0**, `/opt/node22/bin/rtlcss`, execution verified (`margin-left` → `margin-right`) |
| Shopify | **none** — no store, credential, request, mutation or webhook |

## 1. Evidence classes used in this record

These are kept strictly distinct throughout and must not be conflated:

**source inspection** · **local automated-test evidence** · **local browser
evidence** · **GitHub Actions supporting evidence** · **independent review** ·
**Odoo.sh runtime evidence** · **live-Shopify evidence** · **UAT** ·
**control-room acceptance**

Everything corrected in this session carries at most **source inspection**
and **local automated-test evidence**. **No Odoo.sh runtime, no live-Shopify
contact, no UAT, and no independent review of the corrected head** is
claimed or implied anywhere below.

## 2. Category definitions

| Category | Meaning |
| --- | --- |
| **A** | Confirmed functional/security/reliability defect — corrected, with a binding regression test |
| **B** | Provisional — required a decisive diagnostic before any production change |
| **C** | Evidence or governance defect — a false record, not necessarily a broken product |
| **D** | Live-Shopify validation item — not settleable without an authorized store experiment |
| **E** | Refuted, downgraded, non-material, or out of accepted MVP scope |
| **F** | Accepted or scheduled limitation — a real constraint, retained by decision, not a defect left unfixed |

**Every finding below carries exactly one final disposition.** The
2026-07-27 correction cycle removed the one hybrid this record previously
carried (`E→ open`), which said both "refuted" and "still open" and was
therefore neither. A finding is corrected, refuted, an evidence-only
correction, a live-Shopify item, an accepted/scheduled limitation, or out of
MVP scope — one of those, and it says which.

## 3. The P0 — Category B, diagnosed, reclassified A, corrected

**Finding.** `operation_scope_key` collision: the export apply handler
enqueues its first child step while the parent is still `running`, with a
byte-identical key against a live `UNIQUE` constraint. Reviewer confidence:
**medium** — "settle it with one 10-minute experiment".

**Diagnostic method.** A dispatcher-driven experiment, not a direct handler
call: `shopify.connector.job.dispatch._dispatch_one(job)` followed by
`env.flush_all()`, so both parent and child keys are materialised at
production's own flush boundary.

**Result — the defect is real.**

```
P0DIAG parent-at-enqueue  state=queued
       key='1|shopify.connector.product.export.preview|1|gid://shopify/Product/111'
P0DIAG outcome=UniqueViolation: duplicate key value violates unique
       constraint "shopify_connector_job_store_operation_scope_key_uniq"
```

The parent (`_enqueue_apply`) and the child (`_enqueue_step`) pass the same
`store_id`, `res_model` (`preview._name`), `res_id` (`preview.id`) and
`shopify_target_gid`; `_compute_operation_scope_key` is built from exactly
those four and excludes `job_type`. **The branch's headline deliverable
could not hand off to its first mutation step.**

Why the suite could not see it: all three apply tests call
`_handle_product_export_apply` directly and never flush, so the child was
created in a transaction where the parent's recomputed key was never
written. The reviewer's characterisation was exact.

**Correction.** The repository's own accepted pattern — the inventory
service already terminalises and `flush_recordset(['state',
'operation_scope_key'])` before creating a child, in five places, with a
comment naming this exact collision. Wrapped in a savepoint so
terminalisation and child creation cannot come apart: without it, a failed
`_enqueue_step` leaves a parent recorded `succeeded` with no step behind it,
and `succeeded -> retry_waiting` is an illegal transition, so the
dispatcher's own failure routing would raise over the top of the real error.

**Regression coverage.** `test_export_apply_handoff.py`, 5 tests, all
dispatcher-driven and all flushing. Commit `89e3101`.

## 4. Disposition of every final-review finding

Final-review inventory: **1 P0 · 11 P1 occurrences (10 distinct) · 14
material P2 · 5 evidence-only · 5 non-material P2 · 7 refuted/downgraded.**

### Corrected this session

| # | Finding | Cat | Correction | Commit | Regression test |
| --- | --- | --- | --- | --- | --- |
| P0 | `operation_scope_key` collision | B→**A** | terminalize-then-flush in a savepoint | `89e3101` | `test_export_apply_handoff.py` (5) |
| P1 | SKU duplicate gate fails open (`sku:%s` unquoted) | **A** | centralized `tools/search_syntax.py`; fails closed before transport | `14ea7a8` | `test_export_search_encoding.py` (19) |
| P1 | Export Settings renders the fulfillment list | **A** | explicit `view_ids`; empty states added | `14ea7a8` | `test_export_action_view_binding.py` (5) |
| P1 | RTL root cause false, recorded as `[Fact]` ×4 | **C** | claim withdrawn in 4 records + 2 shipped source comments | `ac6ffdf` | — (record correction) |
| P1 | U1 "RTL" screenshot byte-identical to LTR, graded PASS | **C** | check withdrawn to neither PASS nor FAIL; headline qualified | `ac6ffdf` | — (record correction) |
| P1 | Three D10 tracker surfaces contradict the head | **C** | 4 present-tense claims corrected; §6a given a superseded banner | `ac6ffdf` | — (record correction) |
| P2 | Runner skip anchoring defeatable (2 skips per line) | **A** | matched per occurrence, not per line | `5fb5062` | 2 new `--self-test` assertions |
| P2 | Subtest skips invisible to the skip check | **A** | pattern now matches `Subtest …` | `5fb5062` | `--self-test` assertion |
| P2 | 3 runner modes claim HOOT evidence they never ran | **A** | modes report `partial`; `hoot_suites_executed` emitted | `5fb5062` | `--self-test` (13 assertions pass) |
| P2 | Tour-bundle guard inspects 1 bundle of 4 | **A** | all 4 bundles; content test, not just path | `5fb5062` | guard verified non-vacuous |

### Refuted or downgraded — deliberately NOT corrected

| Finding | Cat | Basis |
| --- | --- | --- |
| Contrast: connector-owned AA failures | **E** | The final review's own correction stands: 24 connector-owned pairs, **0 failing**; 5 of the 6 disputed rows are `readonly` statusbar buttons Odoo renders `disabled` (WCAG 2.2 exempts inactive components), the 6th is Bootstrap's own `.btn-secondary` border. "0 connector-owned AA failures" is correct. No production change. |
| Scope-quarantine banner unreachable | **E** | The SEC-3 rule filters those rows out of every non-superuser read — stricter than the banner and correct. Explicitly listed as not-to-be-resurrected. |
| `_advance_plan` shares the P0's shape | **E** | Refuted by source: `_apply_validated_consequence` writes the predecessor terminal **before** calling `apply_consequence`, so the successor's key is free. Incidental rather than declared, but real. No change. |


### Live-Shopify items — Category D, unchanged

`M-EXP-1 … M-EXP-20` **all remain outstanding.** `X-EXPORT-0` remains
**neither PASS nor FAIL**. No live experiment was performed and none is
authorized by this session. The `$app:binding` namespace question
(§9.1) is **Category D**: the implementation omits `namespace` entirely and
is test-pinned to do so; whether Shopify then resolves the app-reserved
namespace, and whether changing it would strand existing remote identity
data, cannot be settled from documentation alone.

## 5. The six findings left open on 2026-07-27 — all now corrected

The 2026-07-27 correction cycle recorded six findings as confirmed but not
corrected. **All six were corrected in the 2026-07-27 final cycle.** They are
kept here with their original diagnosis, because the diagnosis is what the
correction had to answer.

| # | Finding | Cat | Disposition | Correction commit | Regression test |
| --- | --- | --- | --- | --- | --- |
| P1 | **Media retry is structurally impossible.** `_enqueue_media_step` overrides the enqueue nonce with a deterministic `'%s:%s' % (step, checksum)`, feeding `idempotency_key`, which — unlike `operation_scope_key` — is **never cleared on a terminal state**. `_ensure_media_row` reuses the row, so a legitimate resume reproduces every key component. | **A** | **Corrected.** A `resume_attempt` ordinal on the media row feeds the payload hash: re-dispatching an admitted job replays under its original identity, an authorised resume gets its own. Uniqueness is not weakened anywhere and no audit identity is rewritten. A resume is refused on an already-associated image and while the previous attempt's outcome is unresolved. Duplicate admission is contained in a savepoint so a `23505` can no longer end the drain pass. | `ad66530` | `test_media_resume.py` (15) |
| P1 | **First-push confirmation is unreachable.** `_enqueue_first_push_preview` has **zero production callers**; the only writer of `first_push_state='previewed'` is its handler. No button, cron, RPC or wizard reaches it. The shipped UI text promises a scheduled trigger that does not exist. | **A** | **Corrected.** The scheduled push scan now admits the preview for every push-enabled pair still `pending` — the trigger the UI already promised — instead of a `push_sync`, which an unconfirmed pair could only decline and which shares the pair's scope key. Role matrix and company isolation preserved; the duplicate-prevention query that could never match is fixed. | `c341280` | `test_inventory_first_push_reachability.py` (13) + a production-only U2 tour |
| P1 | **Preview expiry is never re-checked at any mutation boundary.** `_assert_confirmed_preview_pre_c2` checks `state`/`confirmed_uid`/`confirmed_at` and never calls `_is_expired()`. No mutation family re-checks. The create and update paths re-derive their payload from the **live** template while gating on an older confirmation. | **A** | **Corrected.** All 8 mutation families now reach the expiry guard, including the 3 media families that had never passed through the assertion at all. Pre-transport it fails closed with an operator-facing reason; post-transport `_advance_plan` keeps the completed step and blocks the rest, because expiry may not retroactively deny a mutation that already reached Shopify. | `02b14bc` | `test_export_mutation_expiry.py` (13) |
| P1 | **PERF-1 backpressure can never fire.** One production writer of `api_health_state`, writing `'normal'`; `'throttled'` has never been written by production code in any commit. The packet specified **throttle head-room** with linear back-off; `throttleStatus` is parsed on every response and has **zero consumers**. | **A** | **Corrected, using the accepted mechanism rather than a substitute.** The parsed `throttleStatus` becomes durable store state at the client's single response choke point and drives the existing D-PERF1-4 lever. Two thresholds give hysteresis; the documented continuous refill lets a deferred store recover with no Shopify call, which is what stops the first deferral being permanent. Absent or malformed data changes nothing. | `f1c1470` | `test_throttle_backpressure.py` (16) |
| P1 | **PD-PX-7 reconnect reconciliation does not exist.** Zero `action_reconnect` references in the export module. A manual "Expire Open Export Previews" button shipped; the spec requires an automatic pass re-reading every exported binding by GID, verifying variant GID sets and media checksums, blocking exports until it completes. | **A** | **Corrected.** The pass is triggered by the reconnect lifecycle itself (via `connection_generation`, which core bumps only on success), re-reads each bound product by GID, verifies existence, archive state, the variant GID set and connector-owned media identity, routes anything missing/archived/divergent to explicit review, and blocks exports until a terminal verdict. Read-only by construction — there is no mutation path in the handler, asserted structurally. | `091d3e7` | `test_export_reconnect_reconcile.py` (23) |
| P2 | **Overflow instrument cannot fail for connector surfaces.** It compares `documentElement.scrollWidth` against `innerWidth`, but every connector surface renders inside `.o_action_manager`, which is `overflow: hidden` at the pin. All 15 surfaces recorded exactly `1366 == 1366` and no per-surface measurement was stored. | **C** | **Corrected as an EVIDENCE correction.** The instrument now measures per surface and per width, distinguishing an ancestor that *scrolls* the overflow (reachable — §10's sanctioned treatment) from one that *hides* it (gone), and reports clipped descendants with interactive ones flagged. RTL is measured at all three widths. A probe test injects a 4000px element and requires the instrument to report it while the document total is unchanged. **No connector-owned clipping was reproduced, so no production CSS was changed** — the disposition is an evidence correction, not a product defect. | `01ddc1a` | `test_ui_visual_evidence.py` (probe + coverage guard) |
| — | **Systemic:** three governing specifications silently replaced, each in a document asserting the spec was delivered or unchanged (`$app:binding` → omitted; throttle head-room → `api_health_state`; PD-PX-7 pass → expire-previews) | **C** | **Two of the three are now genuinely implemented as specified** (throttle head-room, `f1c1470`; the PD-PX-7 pass, `091d3e7`), so the substitution no longer exists to record. The third, `$app:binding`, is a **Category D** live-Shopify item and is unchanged — see §4. | — | — |

## 5a. Findings corrected in this cycle that the review raised separately

| Finding | Cat | Disposition | Commit | Regression test |
| --- | --- | --- | --- | --- |
| Store `api_version` is writable and non-authoritative | **A** | **Corrected.** The column stays and no migration is performed; a default supplies the constant and an `@api.constrains` refuses a divergent row on create, write, `sudo()`, RPC and import alike. | `f7986b5` | `test_api_version_binding.py` (12) |
| Product-doc vocabulary diverges from the shipped selections | **C** | **Corrected as a bounded evidence/vocabulary reconciliation.** One authoritative code→label mapping covering all 21 review reasons and the role/group distinction; the two residual stale locations corrected. Not a product-document rewrite. | `b99df8d` | `test_vocabulary_reconciliation.py` (7) |

## 5b. Accepted and scheduled limitations — Category F, retained by decision

These are **not** defects left unfixed, and they are **not** resolved. They
are constraints kept deliberately, each with a limitation an operator can
meet and which therefore belongs in UAT.

| # | Limitation | Retained because | What an operator will see |
| --- | --- | --- | --- |
| TD-004 | Media replacement is append-only; no `fileDelete`, no automatic detach or orphan cleanup | Removing an association safely needs proof the `File` is not used elsewhere, and the 2026-07 `File` interface exposes no reverse-reference connection. Auto-deleting a File a merchant may have reused is a worse failure than an extra image | Replacing a product image leaves the older media association in place, so the product accumulates one entry per image version until an operator removes the old ones by hand in Shopify |
| TD-005 | Media export requires `write_files` | `fileUpdate` is the only 2026-07 mutation that associates an existing File with a product, and therefore the only path that honours D-015B-4's READY gate; it accepts `write_files` or `write_themes` and not `write_images`. `write_themes` is never requested. The READY gate was not abandoned to claim the narrower scope | Nothing directly, but the app holds write access to every file in the store rather than only product images — an accepted MVP trade-off pending release-readiness review |
| TD-007 | Divergent existing remote option structures are refused, never restructured | No 2026-07 option mutation was source-verified as non-destructive; each either removes values or reshapes the variant matrix | A merchant who renames an option or changes an option value in Shopify puts that product into a state where the connector exports nothing for it until somebody reconciles the structure by hand. The refusal is clear rather than a silent partial export, but the product is stuck |

## 5c. Separately owned — not this PR's to close

| # | Item | Owner |
| --- | --- | --- |
| TD-002 | Readiness scope-naming | **Wave 4 / PR #189.** Unchanged by this cycle and deliberately not duplicated or transplanted here merely to change its register status |

## 6. Status of this head

Every finding in the authoritative final review now carries exactly one
disposition, and every confirmed in-scope defect has been corrected with a
binding regression test. What that does **and does not** mean:

**Corrected and locally verified.** The P0, the four P1s and four P2s of the
first cycle, plus TD-011 through TD-016, TD-003 and TD-008 in the final
cycle. Each correction has regression tests that fail without it, and the
adjacent module suites pass.

**Retained by decision, not resolved.** TD-004, TD-005 and TD-007 remain open
limitations with operator-visible consequences (§5b). TD-002 is unchanged and
belongs to PR #189 (§5c). **This head does not have zero technical debt, and
this record does not claim it does.**

**Not established at this head:**

| Evidence class | State |
| --- | --- |
| Independent review of the corrected head | **Not performed** |
| Odoo.sh runtime validation at the exact head | **Not performed** |
| Live-Shopify validation — `M-EXP-1 … M-EXP-20` | **All outstanding.** `X-EXPORT-0` is neither PASS nor FAIL |
| UAT | **Not begun** |

**PR #204 remains draft, unaccepted, unapproved and unmerged.**

The recommended next gate is a **fresh bounded independent delta review** of
the corrected head, then exact-head Odoo.sh validation if that passes, then
controlled live-Shopify validation and UAT if Odoo.sh passes. Nothing in this
record is an acceptance, and the session that produced it may not perform the
review.

## 6a. Consolidated final correction — 2026-07-27

> **Not an acceptance. Not a review.** The implementation worker has not
> reviewed, accepted or approved its own corrections, and may not.

§6 above claimed every confirmed in-scope defect was corrected with a binding
regression test. **For four rows that claim was not sufficient**, and the
shortfall had a single shape worth naming: each correction was verified
against the mechanism it introduced rather than against the route a worker or
an operator actually takes. This section records what was wrong with the
claim, not only what was fixed.

| Row | The insufficiency | Correction | Regressions |
| --- | --- | --- | --- |
| **TD-011** | `_resume_media_export` had **no production caller** — every visible caller was a test. §6 recorded the capability as delivered; an operator could not reach it. All 15 tests called the private helper | Public `action_shopify_resume_media_export` on the exported-media registry, wired to a button on the form the existing menu opens. Operator/Administrator derived from the accepted matrix (`action_manual_retry`'s non-blocked branch, `enqueue_preview`), `check_access('read')` and a company check before any elevation. The ordinal is consumed only on real admission; a repeated click coalesces on the outstanding job | 16 through the public action |
| **TD-013** | Correctly implemented; **insufficiently evidenced**. All 13 tests called `_prepare_preconditions_*`/`_advance_plan` directly — unit coverage of the guard, not proof it is bound into the dispatch route | **No redesign.** One `-standard` class drives `run_drain()` on a genuine pooled connection through the real claim, `_drain_mutation_one` and the registered `prepare_preconditions`; zero calls at the transport choke point, the accepted fail-closed state, no child mutation job | 3, one of which is a live-confirmation control so the refusal cannot pass on a dead route |
| **TD-014** | Throttle pressure was evaluated **once per pass, before the claim loop**. A store reporting 2% head-room on its first job could still have four more claimed by that pass. The 16 tests pulled the lever themselves | The deferred set is re-read before every claim and **unioned**; the mid-pass read does not re-project recovery, so a pass can only accumulate deferrals and recovery stays a next-pass event | 3 through `run_drain()`, driving a real-shaped `throttleStatus` through the production response choke point. No forced 429 |
| **TD-015 (media)** | Divergence was decided from **local rows alone**. An `associated` row with a File GID and a checksum produced `verified` with nothing having read Shopify — precisely the claim a reconnect invalidates | Read-only re-read of the product's media connection, plus Files-by-connector-filename for any association absent from it. **Checksum correspondence is not claimed** — the 2026-07 `File` interface exposes no digest, and the `verified` note says so. Truncation routes to review, never to a proven absence | 9 |
| **TD-015 (convergence)** | Store settlement was neither atomic nor generation-scoped. Two final jobs could each see the other as pending and both decline, leaving every binding terminal and the store permanently `in_progress` with no job left to settle it; and the verdict was stamped with `connection_generation` as read at settle time rather than the epoch it covered | Settlement serializes on the store row via an unconditional sequence bump flushed before the sibling read — under REPEATABLE READ a concurrent settlement raises `40001` and is re-driven under the pass's declared `remote_read_replay_safe` policy. Each job settles its own epoch; stale-generation jobs are retired at enqueue and refuse themselves at dispatch; a repeated reconnect coalesces or replaces safely | 11 |

### The API limitation this cycle recorded rather than worked around

Shopify's 2026-07 `File` interface exposes `alt`, `createdAt`, `fileErrors`,
`fileStatus`, `id`, `preview` and `updatedAt` — and **no digest of the stored
bytes**. So a stored `odoo_image_checksum` **cannot be remotely
re-verified**, by this connector or any other. What reconciliation therefore
does and does not establish:

| Claim | Remotely re-verified? |
| --- | --- |
| The File exists under the GID this connector recorded | **Yes** |
| It is associated with the expected product | **Yes** — the GID appears on that product's `media` connection, the same evidence the module's accepted `_reconcile_media_associate` already relies on |
| Its `fileStatus` is not `FAILED` | **Yes** |
| A connector-owned filename identifies it | **Yes**, via `files(query: "filename:…")` |
| The uploaded bytes still match `odoo_image_checksum` | **No — not claimed anywhere.** No API surface exposes it |
| The File is used only by this product | **No** — no reverse-reference connection exists; this is the same limitation that makes the pipeline append-only (TD-004) |

A binding whose media claims cannot be established — including one on a
product with more media than a single page can carry — goes to
operator-visible `review_required`. It is never reported as `verified`, and
never as a proven absence.

### Sensitivity of the new evidence

With the five production corrections reverted, the affected suites report
**37 failed + 5 errors of 224 tests**; with them in place, **0 failed, 0
errors of 224**. Removing the TD-011 action entirely is a stronger binding
still: Odoo's own view validator refuses to install the module, because the
button names a method that must exist and must be public.

**Recorded rather than hidden:** two single-transaction convergence tests do
*not* fail under the revert. In one shared transaction each job's write is
already visible to the next, so those two cover ordering and the
terminal-set invariant; the generation and serialization tests are what prove
the concurrency mechanism.

### Unchanged by this cycle

TD-004, TD-005 and TD-007 remain retained limitations and are **not**
resolved. TD-002 remains owned by PR #189, untouched and not transplanted.
TD-012 and TD-016 were not reopened. **No independent review of this head, no
Odoo.sh runtime, no live-Shopify contact of any kind, and no UAT.** PR #204
remains draft, unaccepted, unapproved and unmerged.

## 7. What survived scrutiny

Recorded because a closure record that lists only defects misrepresents the
work: API-version discipline, the ownership boundary (no collection,
merchant metafield or media-delete reachable), `FORBIDDEN_UPDATE_KEYS`,
company rules with no NULL escape, protected-field enforcement, Owl/XML
correctness, the group hierarchy, TD-009's diagnosis against the pinned
source, and TD-010's runner genuinely failing closed on the paths it does
check — all held under deliberate attack. The 185 contrast ratios recompute
exactly, and the Actions run at `9cb7e38` genuinely exercised 14/14 tours
and both HOOT suites.
