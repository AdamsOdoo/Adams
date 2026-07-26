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

## 6. Re-derived Wave 5 completion scope and sequence

`[Re-derived from wave-5-definition-of-ready.md §1/§3 and the merged record.
Nothing invented.]`

Binding intra-wave sequence (DoR §3): **SEC-2 → PERF-1 → U1 → U2 → U3 →
Task 015 → Task 015B.** The 2026-07-26 ruling re-orders the tail to
SEC-2 → PERF-1 → U2 → 015 → 015B → U3, so the export backends land before
the U3 screens that consume them.

### 6a. HARD STOP — Task 015, 015B and U3 are not delivered

`[Fact — evidence-backed, not a scheduling deferral]`

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
