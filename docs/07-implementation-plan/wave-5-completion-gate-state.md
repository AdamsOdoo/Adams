# Wave 5 Completion — Gate State and D10 Post-Merge Closure

> **Status: Evidence record and gate tracker. Docs-only. NOT an acceptance.**
> Produced 2026-07-25 on `fable/wave-5-completion`, branched from the bound base
> `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d`.
>
> This file is a **recurring tracker** (the DEC-041 D5 exception for durable
> governance instruments with a direct recurring consumer). It exists because
> [DEC-041](../04-decisions/DEC-041-evidence-first-process-reallocation.md) **D10**
> makes a synchronized post-merge tracker record a **precondition of the next
> dependent implementation wave** — and PR #194 merged without one.
>
> **Updated 2026-07-25 — U1 implemented.** The product owner subsequently issued
> the instruction that opens the Wave 5 gate and directs completion, binding the
> base to `87f1763a`. §5's hard stop is therefore **lifted by product-owner
> instruction** and **U1 is implemented in this branch** — see §5a. This session
> still **accepts no gate and reviews nothing of its own**: independent Claude
> review at the exact SHA, then a separate closure session, remain required.

## 1. Identity and truth verification

`[Fact — verified in this session against GitHub and the local checkout]`

| Check | Result |
| --- | --- |
| Required base / current `mvp/program-integration` tip | `87f1763a1ca699947d665c92bef614bd1fc3168d` — **matches**, no drift |
| Tip identity | Ordinary merge commit; parents `2583081f97c94428dfd10325589b1b891eea240b` (base) → `80fbb523c05040929f157b8cd15e889d4c6e84c9` (head) |
| Branch created | `fable/wave-5-completion`, at exactly that SHA |
| Protected checkpoint `checkpoint/core-r2-readonly-uat-2026-07-15` | Present at `acd8c4691e72cf5590f2a56228b08f183b76cd9a`, **unmodified**, and a verified **ancestor** of the tip |
| Protected checkpoint `checkpoint/wave-2-order-import-2026-07-18` | Present at `22bfb9a0e9b1e48b6a664351e2b321d134177110`, **unmodified** |
| Accepted wave merges present in the tip's ancestry | `d18f9a9` (W1), `22bfb9a` (W2), `e48cfb1` (W3 S0), `ab4f12f` (W3 inv), `01f072d` (W4 A), `3a1afa43` (W4 B), `8818c77` (U0), `2583081f` (stabilization) — **all present** |
| Exact-base CI | Actions run [`30177207908`](https://github.com/AdamsOdoo/Adams/actions/runs/30177207908), job `89727811506` "Odoo 19 install + full connector suite", `push` event on head **`87f1763a1c`**, conclusion **`success`**, 2026-07-25 22:15:05→22:25:50Z |

**No identity, ancestry, or protected-ref discrepancy was found.** No protected ref,
existing PR, or issue was altered by this session.

**CI classification `[Fact]`:** run `30177207908` is **DEC-041 D8 supporting
evidence at the exact bound base**, not acceptance. Per
[`.github/workflows/connector-tests.yml`](../../.github/workflows/connector-tests.yml),
the exact-SHA **Odoo.sh** run remains the Tier-1 acceptance authority until
equivalence is separately proven. This session read the run's identity, job name,
and conclusion; it did **not** read per-suite pass counts out of the retained log
and therefore **claims none**.

## 2. D10 post-merge closure record — PR #194

`[Fact — from the durable PR record]`

| Item | Value |
| --- | --- |
| PR | [#194](https://github.com/AdamsOdoo/Adams/pull/194) — Wave 5 U1 Gate A (docs-only) |
| State | **CLOSED — MERGED** 2026-07-25T22:15:01Z |
| Accepted head | `80fbb523c05040929f157b8cd15e889d4c6e84c9` |
| **Actual merge commit** | **`87f1763a1ca699947d665c92bef614bd1fc3168d`** |
| Merge method | Ordinary merge commit — no squash, rebase, force-push, or history rewrite |
| Merged scope | 24 paths, **every one under `docs/**`**; zero `addons/**` |
| Independent review | [`5080722794`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080722794) — `INDEPENDENT U1 GATE-A ACCEPT`; no P0, no P1, no material P2; five P3 deferred |
| Control-room acceptance | [`5080795232`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080795232) |
| Merge record | [`5080798692`](https://github.com/AdamsOdoo/Adams/pull/194#issuecomment-5080798692) |
| Issues | #196 closed; **#197 open**; **#199 open** — unchanged by the merge |

**Why this record exists.** DEC-041 D10 requires the actual merge SHA and post-merge
state on all three synchronized tracker surfaces **before the next dependent
implementation wave**. At the bound base all three were still materially stale
`[Fact — verified in the checked-out tree at 87f1763a]`:

- `mvp-program-state.md` §1 gave the integration tip as `3a1afa43` and described
  PR #194 as "**open/draft/unmerged**";
- `mvp-acceptance-matrix.md` described PR #194 as "open/draft/unmerged and stale …
  frozen until the pre-Wave-5 stabilization gate and SEC-2 #196 close" (both had
  already closed);
- `mvp-completion-program.md` §3 "D10 synchronized state" named
  `mvp/program-integration@3a1afa43`.

This is the D10 failure mode by name: **a stale tracker blocks merge closure and
downstream continuation.** All three surfaces are corrected in this batch.

## 3. Backend-contract carry-over to the bound base — proven, not assumed

`[Fact — verified by tree identity]`

The U1 backend/UI contract was source-verified at `2583081f`. The locked prompt
requires re-verification at the bound base "before writing a line". That
re-verification is discharged by **tree identity**, which is stronger than
re-derivation:

```
git diff --name-only 2583081f 87f1763a        -> 24 paths, 0 non-docs
tree addons/ @ 2583081f  = 1b58f7c546de62edae0eabad3f6fc90c6a158323
tree addons/ @ 87f1763a  = 1b58f7c546de62edae0eabad3f6fc90c6a158323   (identical)
```

**Inference (high confidence, from the fact above):** every model, field,
selection, sanctioned action, group XML ID, record rule, and count in
`u1-backend-ui-contract-inventory.md` — including the 21 `review_reason` values,
19 `error_class`, 9 `manual_review_subreason`, 10 job states, 10 job types,
4 `origin_class`, 5 `reconciled_state`, and the canonical §12 status/badge
matrix — holds **unchanged** at the bound base. The contract requires no
re-derivation for U1.

The historical `2d9cff0` citations that review `5080722794` flagged as P3-4 are
therefore accurate and carry forward; see §7.

## 4. Wave 5 gates G5-1 … G5-9 — evidence-derived state

`[Re-derived in this session from the repository at the bound base and from durable
GitHub evidence. This section records state; it accepts nothing.]`

The prior record says only "G5-1 … G5-9 remain unearned and unchecked", which is
true but not actionable. The table below states, per gate, **what durable evidence
already supplies** and **exactly what remains and who must act**.

| Gate | Requires | Evidence-derived state | What remains, and whose act |
| --- | --- | --- | --- |
| **G5-1** — Premium UX master spec accepted | `premium-ux-master-specification.md` accepted | `[Fact]` the document header still reads **"Status: Proposed"**. **But** its U1 load-bearing sections (§1.2, §2, §3, §4, §5, §7, §8) are exactly README §4.3 row 1 = **D-P0-3**, which acceptance `5080795232` §2 **accepted for implementation**. | **Substantively earned for U1 scope; formally unchecked.** Control room to either mark the gate satisfied for U1 or restate the residual non-U1 scope. Not a worker act. |
| **G5-2** — Two-role + no-masking + SEC-2 packet accepted | Roles doc §1/§3/§4/§5/§6 + SEC-2 packet accepted | `[Fact]` SEC-2 is **implemented, independently reviewed, merged**; issue **#196 closed as completed**. Both role XML IDs exist (Option M-A, additive `implied_ids`). The PII-simplification obligation is a **separate** packet item, explicitly **not** part of #196. | **Implementation earned; document acceptance formally unchecked.** Control room to check the gate against the shipped result, and to schedule the separate PII-simplification obligation. |
| **G5-3** — U1 prototype-fidelity criteria fixed | U0 prototype named as fidelity baseline + design-system acceptance set | `[Fact]` U0 merged and accepted (PR #192, `8818c77`). `[Fact]` README §4.1 records the **design system as Accepted**. The fidelity-bar row is README §4.3's last row = **D-P0-3**, accepted by `5080795232`. | **Substantively earned.** Control room to check. |
| **G5-4** — PERF-1 budgets accepted | PERF-1 packet §3/§7 decision closures accepted | `[Fact]` `task-perf1-core-queue-throughput-calibration-packet.md` header reads **"Proposed for ChatGPT review. NOT accepted. The locked prompt in §9 is NOT usable."** It is **not** in the D-P0-3 set and was **not** accepted by `5080795232`. | **GENUINELY UNEARNED.** Requires a control-room/product-owner acceptance act. **No worker may supply it.** |
| **G5-5** — Export operating-model PDs accepted | PD-PX-1..7 + Task 015/015B re-accepted | `[Fact]` not accepted; not in the D-P0-3 set. | **GENUINELY UNEARNED.** Control-room act. Gates Task 015/015B only — **not** U1. |
| **G5-6** — Layer 2 in place | DEC-031 Layer 2 accepted, implemented, proven; Waves 1–4 merged runtime-green | `[Fact]` Wave 3 Stage 0 (`e48cfb1`) and inventory (`ab4f12f`) merged runtime-green; Wave 4 Gate A (`01f072d`) and Gate B (`3a1afa43`, candidate `25639f17`, build `35422036`) merged with accepted runtime and independent review. All present in the base ancestry (§1). | **Substantively earned.** Control room to check. |
| **G5-7** — SEC-1 surface intact at the Wave 5 base SHA | Merged SEC-1 hardening still passes **at the Wave 5 base** | `[Fact]` exact-base CI run `30177207908` is **`success` on `87f1763a1c`** (§1) — install + full connector suite, fresh and warm, including the `-standard` classes. `[Fact]` Odoo.sh is still the Tier-1 authority (DEC-041 D8). | **Supported at the bound base by D8 supporting evidence.** For a Tier-1 check, an exact-SHA **Odoo.sh** run at `87f1763a` is the authority. Control room to decide whether D8 supporting evidence suffices for this gate. |
| **G5-8** — Fulfillment Mode 2 backend delivered by Wave 4 | Mode 1 + Mode 2 backend merged runtime-green | `[Fact]` merged via `3a1afa43`; runtime record [`5074529652`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652) and independent acceptance [`5077119326`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326). | **Substantively earned.** Control room to check. |
| **G5-9** — Rejected-approaches check recorded per stage | CLAUDE.md §10 check against `rejected-approaches-log.md` | `[Fact]` recorded for the U1 stage in the Gate-A package and re-confirmed by review `5080722794` §14 (Option C separate-addon explicitly rejected on PD-2 grounds). Not yet recorded for U2/U3/PERF-1/015/015B. | **Earned for U1; owed per remaining stage** at each stage's gate. Worker act, per stage. |

**Summary `[Inference]`:** of the nine wave-opening gates, **six (G5-1, G5-2, G5-3,
G5-6, G5-8, G5-9-for-U1)** are substantively earned by merged, independently
accepted evidence and need only a control-room check; **G5-7** is supported at the
bound base by D8 evidence pending a Tier-1 authority decision; and **two (G5-4,
G5-5)** are genuinely unearned and require acceptance acts no worker may perform.
**G5-5 gates Task 015/015B only and does not gate U1.**

## 5. Residual U1 implementation blockers — HARD STOP

`[Fact — from the durable record; this session's hard-stop basis]`

The U1 gate (`wave-5-u1-gate-a/README.md` §4.6) listed four blockers. Post-merge:

| # | Blocker | State at the bound base |
| --- | --- | --- |
| 1 | Fresh independent Gate-A review since the re-anchor | **RESOLVED** — review `5080722794`, `ACCEPT` at head `80fbb523` |
| 2 | D-P0-3 — load-bearing Proposed product/UX contracts | **RESOLVED** — acceptance `5080795232` §2: "accepted for implementation" |
| 3 | Wave-5 gates G5-1…G5-9 unchecked | **OPEN** — see §4. **G5-4 is genuinely unearned** and requires a control-room act |
| 4 | Control room has not opened the U1 gate and has not bound the base | **PARTIALLY RESOLVED** — the base is now **bound to `87f1763a`** by product-owner instruction. **Opening the U1 gate is a separate, unrecorded act** |

**Therefore this session did not write U1 code.** The locked prompt's DO-NOT-USE
gate item 3 requires G5-1, G5-3, G5-4 and G5-7 satisfied; **G5-4 is not**, and no
worker may satisfy it. Both acceptance `5080795232` §5 and merge record
`5080798692` state plainly that **no U1 implementation is authorized**. Writing U1
code here would require this session to check its own gates — the precise
self-authorization that CLAUDE.md §13 and DEC-041's unchanged-gates list forbid.
This is recorded as a hard stop with evidence, not as a deferral.

**What unblocks U1 `[Recommendation]`:** one control-room instruction that
(a) accepts the PERF-1 packet's §3/§7 budget closures **or** rules PERF-1 budgets
non-blocking for U1 and re-sequences PERF-1 after U1; (b) checks G5-1/G5-2/G5-3/
G5-6/G5-8 against the merged evidence in §4; (c) rules on whether D8 supporting
evidence satisfies G5-7 or orders an exact-SHA Odoo.sh run at `87f1763a`; and
(d) states explicitly that the U1 gate is **OPEN** at base `87f1763a`. The locked
prompt is otherwise ready: its base is bound, and §3 proves its contract holds at
that base.

## 5a. Control-room continuation ruling — 2026-07-26

`[Fact — recorded from the product-owner/control-room instruction of 2026-07-26]`

That instruction is itself the acceptance act §4 said was missing. It records:

| Gate | Ruling |
| --- | --- |
| G5-1, G5-2, G5-3, G5-6, G5-8 | **Satisfied** by the merged and accepted evidence in §4 |
| G5-7 | Supporting evidence **sufficient to continue implementation**; it does **not** grant Tier-1 acceptance. One exact-head Odoo.sh campaign remains mandatory after the final Wave 5 head is frozen |
| G5-9 | Satisfied for U1; **owed per remaining stage** |
| G5-4 | **OPEN.** PERF-1 objectives and the PB-19 provisional ≥ 600 jobs/hour target accepted, **subject to source rebase** |
| G5-5 | **OPEN.** PD-PX-1..7 accepted as the binding export policy; Task 015/015B may proceed **after source alignment** |
| SEC-2 PII | **Option 1 accepted and authorized** — controlled removal of business-record masking, mandatory log/audit redaction retained, already-masked data never reconstructed |
| U2/U3 addendum | **Accepted for implementation** |

The ruling also directs that the repository headers still reading
"Proposed / Not accepted" are **not** a reason to stop, and that this tracker
record the acceptance accurately **without claiming runtime, independent
review or final acceptance**. That is exactly what this section does.

## 5b. Wave 5 stage delivery — state at this head

`[Fact — implemented and locally validated in this branch; NOTHING accepted]`

| # | Stage | State |
| --- | --- | --- |
| 1 | **SEC-2 residual — PII simplification** | **DELIVERED.** Business-record masking removed (Option 1); log/audit redaction retained and renamed to what it governs; legacy-masked rows flagged for re-import, never reconstructed; migrations verified on real migrated data and proven idempotent |
| 2 | **PERF-1** | **DELIVERED, source-rebased.** Cron progress + time budget, configurable per-pass cap, pre-claim backpressure. The packet's claim-N rework was **not** performed because it was already merged in a stronger form — see §5c |
| 3 | **U1 — fulfillment operator experience** | **DELIVERED** (previous batch, unchanged here) |
| 4 | **U2 — orders, COD, catalog matching, inventory surfaces** | **DELIVERED** |
| 5 | **Task 015 — controlled product export** | **DELIVERED, mutation-split** — see §5d. The HARD STOP of §6a is **lifted by the 2026-07-26 continuation ruling**, which removed the design's dependency on the unresolved `productSet` omitted-list boundary |
| 6 | **Task 015B — media export** | **DELIVERED, append-only** — see §5d |
| 7 | **U3 — export and non-export operator surfaces** | **DELIVERED** (structural and behavioural criteria), with visual artifacts outstanding — see §5e and **§5e.1**, which state exactly what is and is not present |

## 5c. PERF-1 source rebase — what was corrected

`[Fact]` The PERF-1 packet described a dispatcher that claimed N jobs and
looped over them in one uncommitted transaction. At the bound base,
`run_drain()` already delegates to `_drain_one()`, which claims **one** job
under `try_lock_for_update()`, dispatches it and **commits it on its own
transaction**, with DEC-031 Layer 1 replay routing and Layer 2 mutation
recovery around it.

**Implementing D-PERF1-1 as written would have replaced a hardened,
independently reviewed recovery model with a weaker description of it.** It
was therefore not implemented as written; the packet now carries a §0 rebase
section recording that, and the delivered scope is the part that genuinely did
not exist. Full detail:
[`../05-qa/task-perf1-validation-results.md`](../05-qa/task-perf1-validation-results.md).

## 5d. Task 015 / 015B — the mutation split, and why the stop lifted

`[Fact — implemented and locally validated in this branch; NOTHING accepted]`

**The §6a hard stop was not overruled on schedule; the dependency it rested on
was removed.** §6a's finding stands exactly as written: the official
documentation does not say what `productSet` does with a list field omitted
entirely, and building a destructive-write guard on a guess about *when Shopify
deletes merchant data* is not acceptable. The 2026-07-26 continuation ruling
directed that the production design must no longer depend on that proposition,
and the 2026-07 reference — reachable this time, where it returned 503 before —
shows how:

| Path | Mutation | Why it cannot delete merchant state |
| --- | --- | --- |
| Create (unbound only) | `productSet(synchronous: true, identifier: {customId})` | A brand-new product has no merchant state. The `customId` upsert is what makes a replayed create converge on one product |
| Scalar update | `productUpdate(product:, identifier: {id})` | `ProductUpdateInput` has **no `variants`** and **no `productOptions`** field at all, and expresses collections as additive/subtractive `collectionsToJoin`/`collectionsToLeave` |
| Mapped variants | `productVariantsBulkUpdate(allowPartialUpdates: false)` | Operates only on the variant ids given; all-or-nothing |
| New variants | `productVariantsBulkCreate(strategy: PRESERVE_STANDALONE_VARIANT)` | `DEFAULT` would delete the standalone "Default Title" variant, so it is not used |

Full verification, including the corrected media-scope conclusion and the
`X-EXPORT-0` record corrections:
[`../05-qa/task-015-export-source-verification-2026-07-26-addendum.md`](../05-qa/task-015-export-source-verification-2026-07-26-addendum.md).

**Nothing in the new module deletes a remote variant, product option, option
value, collection membership, merchant metafield or media asset.** Every
difference that would require one is enumerated in the preview as a refusal and
routed to `destructive_write_guard_blocked`. The complete-list workaround is
also refused: echoing a full remote list back into a declarative input would
make the connector the author of state it cannot see.

**015B is append-only, which is stronger than the packet's detach-only
posture.** No `fileDelete`, no detach, no reorder. A superseded image's File
and association are **retained** and the row is flagged
`orphan_cleanup_candidate` for a later explicit capability that does not exist
yet. The honest cost — a replaced image leaves the old one on the product until
an operator removes it — is recorded rather than engineered around, because
removing it safely needs a `File` reverse-reference query and 2026-07 exposes
none.

**One packet conclusion is corrected `[Fact]`:** least privilege for media is
**`write_files` + `write_products`**, not `write_images` + `write_products`.
`fileCreate` accepts `write_images`, but `fileUpdate` — the only 2026-07
mutation that associates an **existing** File with a product, and therefore the
only READY-gated association path — does not. `write_themes` is never
requested and its presence is a readiness **failure**.

## 5e. U3 — delivered scope and the residue, stated separately

`[Fact]`

**Delivered in this batch:** the export preview/diff surface (S7/S27) with the
confirm flow wired to `action_confirm_export_preview`; the refused-differences
and left-untouched sections rendered as first-class parts of the confirmation,
not footnotes; the exported-media registry surface including the
retained-orphan disclosure; the per-store export settings, ownership-direction
and retention surface (S28/S29); the reconnect export block (PD-PX-7,
implemented the strict way — reconnecting expires every open preview, so no
pre-reconnect confirmation can authorise a post-reconnect write); the product
form opt-in and its allowlist disclosure; and the Export menu branch under the
one existing U0 root at a sequence held distinct by a test.

**NOT delivered in the batch this section originally described `[Fact]`:**
no Owl component, no `web_tour` tours, no HOOT tests, no screenshot set, no
accessibility checklist, no copy deck, no reconnect/backfill surface (S25/S26),
no diagnostics screen (S31), and no motion/keyboard/contrast pass. The reason
was capacity, not a dependency, and it was stated plainly rather than dressed
as one.

### 5e.1 U3 completion — 2026-07-26

`[Fact — implemented and locally executed in this branch; NOTHING accepted]`

The residue above is now largely closed. Delivered since:

- **The S7 Owl diff surface**, backed by a new read-only projection service
  (`shopify.connector.product.export.ui`). The projection computes no guard
  and no payload — an AST guard asserts it never writes, sudoes, commits or
  enqueues, its sudo budget is pinned at **zero**, and it reads as the
  current user so the ordinary ACL and the SEC-3 company rules apply. The
  reading order is the safety order: state → what will be **removed** →
  what changes → images → what the connector **refused** → what it never
  touches → only then the confirm control.
- **Reconnect/backfill (S25/S26)** and **export diagnostics (S31)**, both
  Odoo-native rather than Owl. Diagnostics is "show me the rows that need
  attention, filtered", which an action with a search view already does; a
  second client action would add maintenance and test surface for no
  operator benefit. Every filter is a domain over a field an earlier wave
  shipped — no new backend logic — and no credential, payload or PII column
  appears on any of them.
- **`docs/06-prompts/ui-u3-copy-deck.md`** — the copy actually shipped, quoted
  from the committed views, not copy proposed for a later implementation.
- **Executed browser evidence**: three U3 `web_tour` tours and an 11-test
  HOOT suite, run in a real Chromium. Full record:
  [`../05-qa/ui-u3-validation-results.md`](../05-qa/ui-u3-validation-results.md).
- **The polish pass, implemented structurally**: logical properties
  throughout (RTL correct without a mirrored stylesheet), every transition
  behind `prefers-reduced-motion: no-preference` so reduced motion is the
  default rather than an afterthought, design-system token pairs only, and a
  keyboard tour that asserts the focused control matches `:focus-visible` —
  so a focus ring that exists only in the stylesheet fails the test.

**Four defects were found by executing the surfaces**, three of them
inherited from already-merged work:

1. `ir.actions.client` has **no `group_ids`** in Odoo 19 — a hard
   `ParseError` at install. **Candidate; fixed.**
2. `--` inside an XML comment made the whole `web.assets_web` bundle fail to
   build. Only a browser can see this. **Candidate; fixed.**
3. **Every tour in this repository timed out on its first step.** In Odoo 19
   the `.o_app` tiles do not exist in the DOM until the apps menu is opened,
   so `shopify_connector_u0_nav_tour` — merged with U0 — **could never have
   passed**. **Inherited; fixed**, and the U0 tour now passes.
4. **`shopify_connector_dashboard.test.js` has never run** (no runner
   existed) **and still fails to register**. **Inherited; partially fixed**
   — logged as **TD-009**, and the U0 dashboard therefore still has no
   executed unit evidence.

**And one environment finding that invalidates prior reasoning about browser
evidence `[Fact]`:** `websocket-client` was absent, so every `HttpCase`
browser test **SKIPPED** while the suite reported `0 failed, 0 error(s)`. Any
"full suite green" that included tour or HOOT tests may have executed none of
them. Logged as **TD-010 (High)**.

**Still not delivered, and not claimed:** no screenshot set, no measured
contrast ratio, no RTL or reduced-motion *visual* verification, and no
`ui-u2-copy-deck.md`. **U3's structural and behavioural acceptance criteria
are met by this branch; its visual-artifact criteria are not.**

### 5e.2 U2/U3 evidence closure — 2026-07-27

`[Fact — implemented and locally executed in this branch; NOTHING accepted]`

The four gaps §5e.1 left open are closed, and closing them found more.

**TD-009 is resolved, and the diagnosis moved the blame.** The U0 HOOT suite's
registration failure was never in the dashboard test: HOOT builds a per-suite
module set from the test file's addon plus that addon's *declared* Odoo
dependencies and starts every module in it, `web_tour` is not a declared
dependency of `shopify_connector_core`, and so a tour importing
`@web_tour/tour_utils` threw and took the whole module set — and the suite
sharing its bundle — down with it. The three connector tours moved to
`web.assets_tests`, Odoo's own home for `HttpCase` tours. **Both HOOT suites
now execute: dashboard 8/8, export diff 11/11.**

**TD-010 is resolved at the instrument, not at the dependency.** The runner
installs `websocket-client` on every run, resolves and *boots* the browser
before running anything, and FAILS on an unexpected skip, a required tour that
did not start, a short marker count or a missing HOOT evidence line. The skip
allowance is bound to one exact test identity and its exact reason.
`--self-test` proves each check rejects what it must, and a suite test runs it.

**U2's action controls now have browser evidence, and it found a P1.**
`Confirm First Push` was visible only in the state
`action_confirm_first_push` refuses and hidden in the state it accepts, and
the First-Push Guard queue listed only the unusable state — **the sanctioned
first-push confirmation was unreachable from the shipped UI.** Two further
UI/ACL disagreements (`Verify Now`, `Change Push`) are corrected. Two more
findings are recorded rather than fixed: the scope-quarantine banner can never
render, because the SEC-3 rule filters those rows out of every ordinary read
(stricter than the banner, and correct); and five list views decorate on a
`status` value that does not exist.

**The visual and accessibility criteria are now MEASURED**, and the
measurement overturned a claim. RTL was not "implemented structurally and
merely unverified" — it did not render RTL.

`[Corrected 2026-07-27]` The root cause recorded here previously — "Odoo 19's
backend never establishes `direction: rtl`" — was **false and is withdrawn**.
Odoo sets `direction` in `webclient_layout.scss` (lines 22, 73, 84 at the
pinned `30bde9ff`) expressly so rtlcss can flip it. **`rtlcss` was absent
from the measuring environment**, and `run_rtlcss` returns the bundle
unflipped in that case while the `.rtl.` URL is still served. The LTR render
was real; the explanation was not. `dir="auto"` was independently wrong: it
resolves from the content, so an Arabic operator reading English data got
`ltr`. Both connector Owl roots bind `dir` to the user's locale, which is
correct on its own terms and is retained.

**Delivered:** `docs/06-prompts/ui-u2-copy-deck.md`,
`docs/05-qa/ui-u2-validation-results.md`, and
`docs/05-qa/evidence/wave-5-u2-u3-2026-07-27/` — 89 screenshots at 1366/768/390
px plus RTL, reduced-motion and focused-control variants; 185 measured contrast
pairs with **0 connector-owned failures**; focus indicators measured with
`:focus-visible` forced.

**What this does NOT deliver.** The design system §14 asks for the screenshot
set *from the Odoo.sh runtime*. This package is **local** rendered evidence and
is a genuinely narrower class. **U3's visual-artifact criteria are met locally
and are NOT met at §14's stated bar.** No Odoo.sh runtime, no independent
review, no UAT, no acceptance.

### 5e.3 PR #204 correction cycles — 2026-07-27

> **Status: implementing-session record. NOT an acceptance, NOT a review, NOT
> a runtime or UAT claim.**

Two correction cycles ran on `fable/wave-5-completion` on 2026-07-27, both
fast-forward, with no amend, rebase, squash or force-push at any point.

**First cycle** (head `9cb7e38` → `2b704b9`, 6 commits). Confirmed the P0 by
execution and fixed it; corrected the SKU query encoding, the Export Settings
view binding, the false RTL root cause, three stale tracker surfaces and four
runner/guard integrity defects. Ended with **six confirmed findings recorded
and not corrected**, registered TD-011 … TD-016.

**Final cycle** (head `2b704b9` → the head recorded in PR #204, 9 commits).
All six are now corrected, together with TD-003 and TD-008:

| Item | Disposition |
| --- | --- |
| TD-011 media retry/resume | Corrected — resume ordinal in the payload hash; uniqueness not weakened, no audit identity rewritten; duplicate admission contained |
| TD-012 first-push reachability | Corrected — the scheduled pass admits the preview, which is the trigger the shipped UI already promised |
| TD-013 mutation-time expiry | Corrected — all 8 mutation families; pre-transport fails closed, post-transport blocks the chain without denying what already happened |
| TD-014 PERF-1 backpressure | Corrected — the accepted D-PERF1-4 mechanism, driven by the real `throttleStatus` it had always parsed and never consumed |
| TD-015 PD-PX-7 reconnect | Corrected — the specified pass, triggered by the reconnect lifecycle, read-only by construction |
| TD-016 overflow instrument | Corrected as an **evidence** correction — no connector-owned clipping was reproduced, so no production CSS changed |
| TD-003 vocabulary | Corrected — one authoritative code→label reconciliation; the two residual stale locations fixed |
| TD-008 API-version writes | Corrected — default plus `@api.constrains`; column kept, no migration |

**Retained deliberately, and NOT resolved:** TD-004 (append-only media
replacement), TD-005 (`write_files` least-privilege trade-off), TD-007
(fail-closed refusal on divergent remote option structures). Each carries an
operator-visible limitation recorded for UAT in the technical-debt register.
**TD-002 is unchanged and owned by PR #189.**

**What this does not establish.** No independent review of the corrected
head, no Odoo.sh runtime, no live-Shopify evidence of any kind, no UAT.
`M-EXP-1 … M-EXP-20` all remain outstanding and `X-EXPORT-0` remains neither
PASS nor FAIL. G5-1 … G5-9 are unaffected by this record. PR #204 remains
draft, unaccepted, unapproved and unmerged, and the recommended next gate is
a fresh bounded independent delta review.

Full per-finding disposition:
[`pr-204-independent-review-closure-2026-07-27.md`](../05-qa/pr-204-independent-review-closure-2026-07-27.md).

### 5e.4 PR #204 consolidated final correction — 2026-07-27

> **Status: implementing-session record. NOT an acceptance, NOT a review, NOT
> a runtime or UAT claim. This session did not review its own work.**

A **third** cycle ran from head `cb9f0ad`, again fast-forward, with no amend,
rebase, squash or force-push. It exists because §5e.3's own claims were
**not sufficient**, and the honest statement of why matters more than the
list of fixes.

**Why the previous cycle's completion claim was insufficient.** Four of the
six §5e.3 corrections were verified against the mechanism they introduced
rather than against the route an operator or a worker actually takes. That
is a real distinction, and it is the same distinction the TD-011 finding was
originally about:

- **TD-011** shipped `_resume_media_export` with **no production caller**.
  Its every visible caller was a test. §5e.3 recorded "a stopped media
  export can be resumed" and 15 passing tests — all of which called the
  private service helper directly. A capability reachable only from a test
  is not a capability, and the previous record did not distinguish the two.
- **TD-014** evaluated throttle pressure **once per drain pass, before the
  claim loop**. So pressure a job reported during a pass could not affect
  that pass: a store could come back with 2% head-room on its first job and
  have four more claimed behind it. The 16 tests exercised the lever by
  pulling it themselves; none asked whether state written during a pass
  changed the claims still to come.
- **TD-015** decided media divergence from the **local registry alone**. A
  row saying `associated`, carrying a File GID and a checksum, produced a
  `verified` verdict with nothing having read Shopify. That is precisely the
  claim a reconnect invalidates. Separately, store-level settlement was
  neither atomic nor generation-scoped: two final jobs could each observe
  the other as pending and both decline to settle, leaving every binding
  terminal and the store permanently `in_progress` with no job left to
  notice — and a verdict was stamped with `connection_generation` as read at
  settle time rather than the epoch it covered.
- **TD-013** was correctly implemented and **insufficiently evidenced**. Its
  13 tests called `_prepare_preconditions_*` and `_advance_plan` directly.
  That is legitimate unit coverage and it is not proof that the guard is
  bound into the dispatch path a real mutation job takes.

**Corrections in this cycle:**

| Item | Correction | Evidence |
| --- | --- | --- |
| TD-011 | A public `action_shopify_resume_media_export` on the exported-media registry, wired to a button on the form the menu already opens. Operator/Administrator per the accepted matrix (`action_manual_retry`'s non-blocked branch and `enqueue_preview`), with `check_access('read')` and a company check before any elevation. The resume ordinal is now consumed **only when an attempt is actually admitted**, and a repeated click coalesces on the outstanding job instead of admitting a second live attempt at one image | **13** regressions through the public action, incl. unauthorised role, wrong company, already-associated, unresolved outcome, repeated click, and zero transport; **plus a browser tour** that walks the menu, presses the control by its operator-facing label and asserts the queued job and the incremented ordinal afterwards (required tours 15 -> 16) |
| TD-014 | The deferred-store set is re-read before **every** claim and **unioned**, so pressure observed mid-pass binds the rest of that pass while unrelated stores keep draining. The mid-pass read deliberately does not re-project recovery, so a pass can only accumulate deferrals; recovery stays a next-pass event on the documented restore-rate projection | **3** regressions through `run_drain()`, driving a real-shaped `throttleStatus` through the production `_normalize_response` choke point. No forced 429 |
| TD-015 (media) | Reconciliation now re-reads the product's media connection and, for any association it cannot find there, the store's Files by connector filename — both read-only, both the same proofs the module's own accepted mutation reconciliations already rely on. **Checksum correspondence cannot be proven remotely, and PD-PX-7 names it, so a binding claiming an associated media File routes to `review` and its store to `review_required`** (corrected 2026-07-27: no accepted decision authorises the narrower proof). A binding claiming no associated media still reaches `verified`. Truncation beyond one page routes to review rather than being reported as a proven absence | **9** new regressions plus 3 rewritten parent-class ones, incl. complete-local-evidence-with-missing-remote, detached vs deleted, divergent identity, `FAILED` status, unverifiable-by-truncation, foreign media left alone, and every request asserted to be a query |
| TD-015 (convergence) | Settlement serializes on the store row via an unconditional sequence bump, flushed before the sibling read — under Odoo's REPEATABLE READ that makes a concurrent settlement raise `40001`, which the dispatcher re-drives under the pass's already-declared `remote_read_replay_safe` policy. Each job settles **its own** connection epoch, stale-generation jobs are retired at enqueue and refuse themselves at dispatch, and a repeated reconnect coalesces or replaces safely instead of failing on `UNIQUE(store_id, operation_scope_key)` | **12** single-transaction regressions, incl. both job orderings, old-generation refusal at both boundaries, three repeated reconnects, same-generation coalesce, and fail-closed transport — **plus 4 genuine cross-transaction regressions added 2026-07-27** on two independent `db_connect` connections (observed SQLSTATE `40001`, the dispatcher's real no-replay re-drive to `complete` and to `review_required`, a sensitivity case that strands the store with the boundary removed, and the SKIP-LOCKED claim fact the interleaving rests on). The 12 were never a cross-transaction proof and this record previously implied they were |
| TD-013 | **No redesign.** One new `-standard` class drives `run_drain()` on a genuine pooled connection through the real claim, the `_is_mutation_job_type` branch, `_drain_mutation_one` and the registered `prepare_preconditions`, asserting the transport choke point receives **zero** calls, the accepted fail-closed disposition, and no child mutation job | **3** regressions, one of which proves the route is live by letting an unexpired confirmation reach the transport — so the refusal test cannot pass on a dead route |

**Unchanged by this cycle.** TD-004, TD-005 and TD-007 remain retained
limitations and are **not** resolved. `[Corrected 2026-07-27]` TD-002's
backend implementation is accepted and merged through PR #189 and was not
touched by this branch; its deferred live-Shopify/Gate D/CV-013/UAT evidence
remains open. TD-012 and TD-016 were not reopened.

**Evidence classes this cycle carries:** source inspection, local automated
tests, and the sensitivity proof that each new regression fails when the
corresponding production correction is reverted. **It carries no independent
review, no Odoo.sh runtime, no live-Shopify contact of any kind, and no UAT.**
The implementation worker has not reviewed, accepted or approved its own
corrections, and may not.

### 5e.5 PR #204 implementation-freeze cycle — 2026-07-27

> **Status: implementing-session record. NOT an acceptance, NOT a review, NOT
> a runtime or UAT claim. This session did not review its own work.**

A fifth cycle ran from head `98334c7a`, fast-forward, with no amend, rebase,
squash or force-push. It closes the last four confirmed implementation
obligations on this PR.

**A. TD-015 — the checksum review had no door.** The preceding cycle routed
every media-bearing binding to `review`, correctly, and recorded that "an
operator must clear it before exports resume". No route existed that could.
The only public action re-RAN the pass, which re-derived the same unprovable
checksum and landed in the same review; `export_reconcile_state` was rendered
on no screen anywhere in the product. A reconnected store that had ever
exported product media was blocked from exporting **permanently, by
construction**. Exactly one review reason is now resolvable — the stored,
machine-readable `checksum_unverifiable`, reached only after store identity,
product identity, archive state, the governed variant set, every File
identity, every File status and response completeness are established
remotely. Every other reason stays blocked; there is no general-purpose
override. Administrator only, record-access and company checks before any
elevation, explicit consequence-stating confirmation, no Shopify request of
any kind, and bound to the generation, binding, product GID, File GID set and
a digest of the local media claim — re-derived on every read, so any change
withdraws it. **Acknowledgement is not verification and this record does not
call it one.**

**B. S1 — the 11-step guided setup wizard.** Recorded as not implemented, and
it was: `shopify.connector.store` carries `create="false"` on both its list
and its form, so there was no route to create a store at all outside a data
import or a `sudo()` call. One bounded Owl client action and one
`AbstractModel` service, owning no business rule — every step delegates to the
service that already owns the decision, and every durable choice is written to
the field that already owns it. Administrator only on every entry point
including the read. All three accepted entry routes exist and are driven in a
browser.

**C. SEC-3 integration.** `[Corrected 2026-07-28]` This cycle's complete
surface delta — 2 models, 20 stored fields, 7 non-stored computed
fields/relations, 18 public/RPC methods, 15 elevated methods over 19
`sudo()` call sites — is inventoried in
[`../03-architecture/sec3-company-isolation-audit.md`](../03-architecture/sec3-company-isolation-audit.md)
§8, with a local two-company/two-role negative matrix over every one. The
prior "17 stored fields / 20 public methods / 14 elevated seams" headline
did not match that section's own itemized tables (independent review) and
is corrected here to the recount above. A P1 cross-company confidentiality
defect found in this same delta by that same review — the TD-015
acknowledgement wizard's company isolation — is corrected in §8.9 of the
same document. **Issue #197 remains OPEN.** This is implementation
coverage; #197's own gates — full-surface inventory, independent Tier-1
security review, exact-SHA runtime evidence — are unmet at this head,
including its corrected head, and are not claimed.

**D. Present-tense tracker reconciliation.** S1, U1, Product Export, U3,
SEC-2, SEC-3, CI and TD-002 were re-read against the source and corrected only
where the present-tense claim was demonstrably stale. Historical records were
left as historical records; no old test or validation record was rewritten to
imply it covered later commits.

**Three defects found while doing the above, and fixed here.**

1. `export_reconcile_review_binding_ids` is a non-stored computed field whose
   contents the caller's record rules filter, and Odoo caches such a field
   **once per record for the whole transaction** unless it declares its
   context dependency. Without `depends_context` the first reader's result is
   served to the second — including owner-first, which would hand one
   company's outstanding reviews to another company's administrator. Fixed and
   asserted in both orders.
2. The readiness check read `web.base.url` unelevated. System parameters are
   `base.group_system` in Odoo 19, so the whole readiness run raised
   `AccessError` for any Connector Administrator who is not also an Odoo
   system administrator — reachable in production through `action_reconnect`
   before S1 existed.
3. The suite runner's fail-closed self-test hand-listed a copy of its own HOOT
   inventory, which went stale the moment a third suite was added. It is
   generated from the inventory now.

**Retained and NOT resolved:** TD-004, TD-005, TD-007. `[Corrected
2026-07-27]` **TD-002's backend implementation is accepted and merged through
PR #189** (merge `3a1afa43`); its deferred live-Shopify, Gate D, CV-013,
external UAT and release evidence remain open and are not claimed by this
cycle. Describing TD-002 as "owned by PR #189" is corrected above: a merged
pull request owns nothing outstanding.

**Evidence classes this cycle carries:** source inspection, local automated
tests, local rendered browser evidence, and the sensitivity proof for each new
regression. **It carries no independent review, no Odoo.sh runtime, no
live-Shopify contact of any kind, and no UAT.** The implementation worker has
not reviewed, accepted or approved its own corrections, and may not.

### 5e.6 PR #204 provisioning-package documentation correction — 2026-07-28

> **Status: documentation-only correction record. NOT an acceptance, NOT a
> review, NOT a new runtime or UAT claim.**

The control room recorded the Odoo.sh standard-runtime-pass disposition for
head `ee23c966a0b214c7974abbade4b384f251c4940f` (PR #204 comment `5103678435`)
and a provisioning-readiness checklist for issue #200 (comment `5103684847`).
That checklist's credential-scope section carried forward
`docs/05-qa/shopify-live-validation-package.md` §2.3's scope table, which was
internally contradictory: it required execution of the M-EXP-* media/mutation
cases while excluding `write_products` and `write_files` as forbidden. A
session-independent audit of the frozen source
(`shopify_connector_readiness_check.py` in core and fulfillment,
`shopify_connector_inventory_service.py`,
`shopify_connector_product_export_seams.py`) and current official Shopify
2026-07 documentation corrected the scope table in
`shopify-live-validation-package.md` §2.3, and a stale `read_fulfillments`
reference (pre-dating the already-landed TD-002/D-014-2 scope correction)
plus a FAIL/PARTIAL classification contradiction in
`docs/05-qa/val-b2-closure-plan.md` §4/§7.

**Executable tree unchanged.** This correction touched
`docs/05-qa/shopify-live-validation-package.md`,
`docs/05-qa/val-b2-closure-plan.md`, and this file only — no `addons/`,
`tools/`, or `.github/` path changed. The accepted Odoo.sh
standard-runtime-pass evidence for `ee23c966a0b214c7974abbade4b384f251c4940f`
therefore still applies unchanged to the new head: **executable tree
unchanged from the accepted Odoo.sh standard-runtime head.** This correction
does not claim a new Odoo.sh run, and none is needed for a documentation-only
descendant.

**No Shopify resource was provisioned or contacted by this correction.**
Issues #185, #186, #197 and #200 remain open. PR #204 remains draft,
unapproved and unmerged. **`[Corrected 2026-07-28]`** This subsection
previously stated the PR #204 comment titled
`CONTROL-ROOM PROVISIONING-PACKAGE CORRECTION` and the issue #200 comment
titled `AUTHORITATIVE CORRECTION TO PROVISIONING READINESS COMMENT 5103684847`
were "both posted this session" — they were not; that pre-claimed a future
GitHub action before it happened. The accurate sequencing: this documentation
correction is committed first; the control room's addendum then authorized
one additional additive documentation-only commit (§5e.7) covering three
further consistency corrections; the external PR #204 and issue #200 records
above are posted only **after** the final documentation head's own GitHub
Actions run completes with `success` — never before, and never claimed in
advance of that result.

**`EXECUTABLE TREE UNCHANGED FROM THE ACCEPTED ODOO.SH STANDARD-RUNTIME HEAD.`**

### 5e.7 Control-room addendum — three documentation-consistency corrections — 2026-07-28

> **Status: documentation-only correction record, additive to §5e.6. NOT an
> acceptance, NOT a review, NOT a new runtime or UAT claim.**

Before finalizing the §5e.6 correction, the control room found three further
documentation inconsistencies and authorized exactly one additional additive
documentation-only commit (parent `dd8ab135f494b5c2085662ef68e920fd1339e21e`,
the §5e.6 commit) to fix them, without amending, rebasing, or force-pushing
`dd8ab135` itself:

1. `shopify-live-validation-package.md` §1's entry criteria E2/E3 conflated
   "the connector SHA under test" (a single `git rev-parse HEAD`) with the
   Odoo.sh-validated executable head, which does not distinguish a
   documentation-only descendant from the executable head Odoo.sh actually
   tested. Corrected to record the current campaign/package head and the
   accepted runtime-tested executable head (`ee23c966a0b214c7974abbade4b384f251c4940f`)
   **separately**, with an explicit zero-executable-delta proof requirement
   and a fresh-qualification trigger if that delta is ever non-zero.
2. `val-b2-closure-plan.md` §10 point 5 read "if VAL-B2 fails (including the
   'qualified/partial' case in §8)," folding the PARTIAL outcome into FAIL —
   contradicting §7's own PASS/PARTIAL/FAIL separation (corrected in the
   §5e.6 cycle). Corrected so FAIL and PARTIAL are named as distinct,
   independently-escalated outcomes; PARTIAL is never recorded as FAIL.
3. This file's own §5e.6 stated the PR #204 and issue #200 correction
   comments were "both posted this session" before they were posted —
   corrected per §5e.6's own text above to accurate sequencing: those
   comments are posted only after this commit's own Actions run succeeds.

**Executable tree unchanged.** This commit touches the same three allowed
documentation paths as §5e.6 and no other; `addons/`, `tools/`, and
`.github/` remain byte-for-byte identical to
`ee23c966a0b214c7974abbade4b384f251c4940f` across both correction commits
combined. No Shopify resource was provisioned or contacted. Issues #185,
#186, #197 and #200 remain open; PR #204 remains draft, unapproved and
unmerged.

### 5e.8 Wave 5 pre-campaign onboarding, location mapping, single-package lifecycle, and dependency-recovery — 2026-07-29

> **Status: implementing-session record. NOT an acceptance, NOT a review,
> NOT a runtime or UAT claim. This session did not review, accept, ready-
> mark, or merge its own work — per DEC-040/DEC-041 it may not.**

A sixth cycle ran on `fable/wave-5-completion`, five commits from head
`4ac4ce2a5144907673fea1b753764823857916aa` to `a208a562f1cf9249c9f7e4f0a30e75131a477058`,
fast-forward only, no amend, rebase, squash or force-push:
`6e1db1d`, `6e622e1`, `b44ccce`, `ffb769c`, `a208a56`. Unlike every prior
cycle recorded in this file (§5e.3–§5e.7 are all documentation-only or
narrower correction cycles), **this cycle is a real `addons/**` implementation
batch** — the "docs-only" framing of this file's own §8 does not describe it;
this subsection's own scope statement below governs.

**What this cycle proves and implements, in one sentence:** a single
customer-facing `Shopify Connector` application (`addons/shopify_connector`)
that installs the complete six-module technical suite in one action, survives
a standard Odoo-dependency loss by entering a durable, administrator-gated
`dependency_paused` state instead of partially operating or being
cascade-removed itself, refuses any direct uninstall of its own technical
components, and correctly cascades its *own* removal to the whole suite when
deliberately uninstalled — proved both by source citation and by exhaustive
disposable-database execution, not by inspection alone. Full derivation:
[`../03-architecture/single-package-lifecycle.md`](../03-architecture/single-package-lifecycle.md);
decision record: [`DEC-042`](../04-decisions/DEC-042-single-package-lifecycle.md).

**Also delivered, narrower in scope:** location-mapping hardening in
`shopify_connector_inventory` — `create_or_update_location_mapping` now
refuses an arbitrary, foreign-store, or inactive Shopify Location GID (it
must correspond to a currently-active, this-store cached
`shopify.connector.location` row) and populates
`shopify_location_name_snapshot` from that validated cached row rather than
from caller input, on both the create and idempotent-update paths.

**Repository/pin identity, verified before any edit and re-verified at the
final head:** repo `AdamsOdoo/Adams`, PR #204, branch
`fable/wave-5-completion` (worked locally as `wave5-work`, tracking
`origin/fable/wave-5-completion`); PR #204 open/draft/unmerged throughout;
base `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d`
(unchanged, still the bound base); Odoo pin
`30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified against
`tools/odoo-pin.txt` and the actual `.odoo-src` checkout both before and
after this cycle. Protected checkpoints and refs untouched.

**Disposable-database proof (Section 6/24C of the governing task), all 7
stages, exact head `a208a562f1cf9249c9f7e4f0a30e75131a477058`:**
`tools/shopify_connector_package_lifecycle_check.sh` — fresh one-action
install, warm adoption of a pre-Wave-5 database, standard-dependency loss
(`stock`) + package survival, restore/explicit resume (never automatic),
direct component-uninstall refusal (including a crafted co-selection),
complete package uninstall (cascades the whole suite via Odoo's own
mechanism), and the wider transitive `product` cascade — **ALL 7 STAGES
PASSED**, real Odoo module operations throughout, zero Shopify contact.

**Regression qualification (Section 24/25), definitive final pass, exact
head, clean worktree throughout:** `tools/run_connector_suite.sh`,
`source_head_verified: true` at `a208a562f1cf9249c9f7e4f0a30e75131a477058`,
`connector_worktree_dirty: false`, Odoo pin verified, PostgreSQL 16.13 /
Python 3.12.3, zero Shopify operations in any pass.

| Pass | Result |
| --- | --- |
| **Fresh install** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Warm upgrade** + standard suites | **0 failed, 0 errors of 2069 tests** |
| **Non-standard tags** | **0 failed, 0 errors of 39 tests** |

Tours: 21 required, 21 executed, 21 success markers in each standard pass.
HOOT suites: all three executed and verified (dashboard, export diff, setup
wizard). Skip detection: only the sanctioned skip
(`TestMutationRecovery.test_real_process_death_harness`). Standard-suite
count moved by exactly the tests this cycle added: **2040 → 2069 (+29)** —
12 in `test_package_lifecycle.py`, 5 in `test_uninstall_guard.py`, 9 in
`test_package_pause_gates.py`, 3 in `test_location_mapping.py`; none silently
dropped. Non-standard stayed at **39** (no non-standard test added or
removed by this cycle). **A first attempt at this same run was invalidated
and discarded before completion**, twice: once because source files were
edited while an earlier pass was still running against a different code
state (this cycle's own process error, corrected by discarding that run and
starting a clean one only after all edits were committed), and once because
an artifact directory left over from that discarded run was moved to an
untracked path inside the repository, which the runner correctly detected as
a dirty worktree and flagged as non-exact-SHA evidence; that directory was
relocated outside the repository and the run repeated cleanly. Both
invalidated attempts are recorded here rather than silently discarded so the
one number this file cites is traceable to the run that actually produced
it.

**HEADLINE finding, from this cycle's own adversarial self-review, NOT
narrowed or hidden — TD-019 (High):** domain-owned data (Shopify location
mappings, product/customer/order bindings, inventory-level bindings, their
jobs/job logs, mutation-attempt evidence) living in the five domain
technical modules does **not** survive a standard-dependency cascade. Only
the package controller's own state survives, because only it lives in a
module (`shopify_connector`) that is structurally never cascaded. Verified
empirically: a `shopify.connector.location.mapping` row was created,
`stock` was uninstalled (cascading `shopify_connector_inventory` away), and
`SELECT to_regclass('shopify_connector_location_mapping')` against the same
database returned `NULL` — the table itself, and the row with it, no
longer exists. Restoring the suite recreates the table empty; it cannot
restore the deleted rows. Neither Pattern A (move the data into a surviving
module) nor Pattern B (a durable snapshot/restore mechanism) is implemented
for this data in this cycle — both require altering the five domain
modules' own data ownership/semantics, outside this task's allowed-file
scope, and this is recorded as a control-room decision this session may not
make unilaterally. Full derivation:
[`../03-architecture/single-package-lifecycle.md`](../03-architecture/single-package-lifecycle.md)
§6a; consequence recorded in
[`DEC-042`](../04-decisions/DEC-042-single-package-lifecycle.md).

**Scoped out of this cycle, explicitly, and logged rather than silently
narrowed:**

- **TD-017** — no dedicated per-store resume-selection UI. The package-level
  gate is a global circuit breaker layered on the existing per-store
  readiness/activation machinery (`shopify_connector_core`, unchanged by
  this cycle); a store disconnected before a pause stays disconnected after
  resume.
- **TD-018** — `action_restore_suite` reinstalls missing components but does
  not also force-upgrade already-installed ones; reconciling a component
  whose code moved ahead of its installed version is left to Odoo's own
  ordinary Apps "Upgrade" action.
- The full location-mapping setup flow/workspace (Sections 18–19 of the
  governing task) beyond the GID-validation hardening above — the setup
  wizard, remap-with-audited-reason flow, and per-location readiness
  workspace are not built in this cycle.
- The full 29-module standard-dependency closure is not individually
  cascade-tested; the harness proves the three representative cascades the
  task specifies (`stock`, `product`, complete package uninstall).

**No browser/viewport evidence was captured for the new package status view**
(a minimal Odoo-native form with a statusbar and three buttons) in this
cycle — the governing task's Section 26 evidence bar was not attempted for
this specific surface; recorded here rather than silently omitted.

**Not claimed:** no independent review of this head, no Odoo.sh runtime, no
live-Shopify contact of any kind, no UAT, no acceptance, ready-mark, or
merge. The implementation worker has not reviewed, accepted, or approved its
own work, and per CLAUDE.md §13/DEC-040/DEC-041 may not. PR #204 remains
draft, unapproved, and unmerged. Recommended next gate: a fresh, independent
Claude review of this exact head (`a208a562f1cf9249c9f7e4f0a30e75131a477058`),
by a separate top-level session or a fresh subagent invocation that
adversarially re-verifies rather than summarizes, per DEC-040 — then, if
accepted, a separate closure session before any ready-mark or merge.

## 6. Re-derived Wave 5 completion scope and sequence

`[Re-derived from wave-5-definition-of-ready.md §1/§3 and the merged record.
Nothing invented.]`

Binding intra-wave sequence (DoR §3): **SEC-2 → PERF-1 → U1 → U2 → U3 →
Task 015 → Task 015B.** The 2026-07-26 ruling re-orders the tail to
SEC-2 → PERF-1 → U2 → 015 → 015B → U3, so the export backends land before
the U3 screens that consume them.

### 6a. HARD STOP — Task 015, 015B and U3 are not delivered

> **`[SUPERSEDED — historical. Corrected 2026-07-27.]`** This section is
> retained as the record of a real gate failure and the reasoning at the
> time. **It is no longer current state, and its `[Fact]` label below must
> not be read as a present-tense claim.** Task 015, Task 015B and U3 are all
> delivered at this branch's head — see **§5d** and the delivery rows at
> §193–§195 of this same file, which contradicted this section until this
> correction. Two specifics that are now false as written: the stop rested
> on `productSet`'s omitted-list-field semantics, and the continuation
> ruling **withdrew `productSet` as the update mutation** so the design no
> longer depends on them; and §6a states that U3's screens have "no
> `action_confirm_export_preview` to wire to", when that method exists at
> `models/shopify_connector_product_export_preview.py` and is exercised by
> four tests. Nothing below has been rewritten.

`[Fact as recorded on 2026-07-25 — superseded, see the banner above]`

**Task 015's source-verification gate failed, and the failure is a real
finding rather than a missing capability.** Before writing any export code,
the official Shopify Admin GraphQL documentation was re-verified as the
ruling requires. Full record:
[`../05-qa/task-015-export-source-verification-2026-07-26.md`](../05-qa/task-015-export-source-verification-2026-07-26.md).

Most of the packets' assumptions were **confirmed** — `productSet`'s
delete-on-omit rule for supplied lists, the `identifier.customId:
UniqueMetafieldValueInput` upsert, the 2048-variant ceiling, synchronous
mode, `write_products`, and — correcting 015B — that `fileCreate` accepts
**`write_images`**, so least privilege is `write_images` + `write_products`
and `write_themes` must not be requested.

**One did not.** D-015-3's containment argument holds that `collections`,
`metafields` and media are protected **by being omitted** from the
`productSet` input. The documentation states that list fields delete "existing
entries that aren't included in the mutation's input", and that omitted
**non-list** fields stay unchanged — **it does not say what happens to a list
field omitted entirely.** The packet itself flagged this as a dev-store
empirical item, "never assumed".

If the strict reading is true, a first export silently deletes every
collection membership, every merchant-authored metafield and every image on
the exported product — merchant data the connector never owned and cannot
restore. **Building a destructive-write guard on an unverified assumption
about when Shopify deletes merchant data is exactly the class of work that
must not proceed on inference.**

Resolving it needs one dev-store experiment, now recorded as the **blocking
prerequisite `X-EXPORT-0`** at the head of
[`../05-qa/shopify-live-validation-package.md`](../05-qa/shopify-live-validation-package.md)
§4.0. This session has no provisioned store and is forbidden from using one.

**Task 015B** is sequenced after 015 and attaches media to products it
creates, so it inherits the stop. **U3's export-flow screens (S27/S7)** have
no `action_confirm_export_preview` to wire to, so they inherit it too.

**U3's non-export scope** — reconnect/backfill (S25/S26),
settings/permissions/retention (S28/S29/S30), diagnostics (S31) and the polish
pass — is **not** blocked by that finding. It is **not delivered in this
batch** for a different and entirely separate reason: the implementing session
reached the end of its working capacity after U2. That is stated plainly
rather than dressed as a dependency.

**Wave 5 also does not close these `[Fact]`:** Gate D / CV-013 (#185),
dev-store provisioning (#200), #186, SEC-3 (#197), PERF-0 release thresholds
(#199), external UAT, and release readiness all remain **open and unclaimed**.

## 7. P3 carry-forward disposition — review `5080722794`

Acceptance `5080795232` §3 made the five P3 findings carry-forward items for "the
future U1 implementation **or the next authorized documentation touch**". This batch
is that touch, so they are fixed in pass (DEC-041 D7 Tier 3).

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Task breakdown §4 says "four" `docs/…` deliverables; the set has five | **FIXED** — corrected to "five" and all five paths now enumerated explicitly, matching the locked prompt item-for-item |
| 2 | `AR-083` row physically between `AR-076` and `AR-077` | **FIXED** — row moved after `AR-082`; log is now strictly ascending. Content unchanged |
| 3 | `A23` row between `A19` and `A20` | **FIXED** — row moved after `A22`; matrix is now strictly ascending. Content unchanged |
| 4 | Contract §3 and §12.1 cite historical `2d9cff0` in present-tense cells | **NO CHANGE NEEDED — and now positively proven.** The review verified both statements true at `2583081f`; §3 above proves the `addons/` tree is **byte-identical** at the bound base, so both remain true at `87f1763a`. §0's blanket historical label stands |
| 5 | Severity-token drift: UX/IA §8 `danger` vs contract §12.2 `critical` | **FIXED — resolved against source, not by preference.** Per DEC-041 D1, the shipped U0 layer was read: `addons/shopify_connector_core/` uses **`danger`** (31 occurrences, incl. `bg-danger`) and **never `critical`**. The **contract** was the drifting document; §12.2 now reads `danger` in the token declaration and in all four severity-rule cells. UX/IA §8 was already correct and is unchanged |

**Note on finding 5 `[Inference]`:** the review classified this as "same concept,
two names; the copy deck will fix it" without determining which token ships. It is
now determined from source. Had it been left to the copy deck, an implementer
reading the contract as authoritative would have emitted a `critical` token that
does not exist in the U0 layer.

## 8. What this batch does not do or claim

- **No Wave 5 implementation.** No `addons/**`, production, test, manifest,
  security, CI, XML, CSV, or configuration path is touched — this batch is
  docs-only.
- **No gate is accepted, checked, or opened**; no wave, PR, or issue is accepted,
  ready-marked, or merged; nothing is self-accepted.
- **No issue action.** #185, #186, #197, #199, #200 remain exactly as found.
- **No protected ref, existing PR, or existing comment altered**; no rebase, no
  force-push, no branch deletion, no history rewrite.
- **No accepted code changed.** Waves 1–4 and U0 are preserved byte-for-byte; no
  defect requiring a code change was found, so none was made.
- **No Shopify credential, request, or mutation.** No browser/render evidence, no
  Odoo.sh runtime evidence, no live-Shopify validation, no UAT, and no
  release-readiness claim is produced or implied.
- **No PERF-0 number is restated as a guarantee, budget, threshold, or SLA.**
- **"Delivered" remains suppressed** — not claimed, displayed, or offered.
- Per DEC-041 D7, a documentation/governance-only batch is verified by
  repository, diff, path, link, and consistency checks appropriate to the change.
  **No runtime campaign was run and none is fabricated**, and this does not weaken
  the runtime requirement for any later code batch.
