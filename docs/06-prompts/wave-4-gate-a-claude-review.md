# Wave 4 Gate A — Independent Claude review of the Codex prompt candidate

> **Reviewer role:** Independent prompt / architecture-governance / quality
> reviewer (Claude Code). This is a review of a **prompt**, not execution of
> Wave 4 Gate A. No fulfillment code was written, no `addons/**` file was
> changed, no Shopify operation occurred, and the candidate prompt was **not**
> edited. ChatGPT remains the reconciliation and prompt-issuing authority;
> only ChatGPT issues the final locked Codex prompt.
>
> **Claim classification (CLAUDE.md §8) is applied throughout:** `[Fact]`,
> `[Repo fact]`, `[Official fact]`, `[Inference]`, `[Recommendation]`.

---

## 1. Review identity and exact SHAs

| Item | Value | Verified |
| --- | --- | --- |
| Repository | `AdamsOdoo/Adams` | ✅ |
| Review branch | `control-room/wave-4-gate-a-prompt-review` | ✅ |
| Review-branch head (before this report) | `31fe1f2cb716ccb9d74bd43f763ad9e4041e4e55` | ✅ |
| Draft review PR | #187 — open, **draft**, unmerged, `mergeable_state: clean` | ✅ |
| PR #187 change set | single file `docs/06-prompts/wave-4-gate-a-codex-review-candidate.md` (+1022) | ✅ |
| Candidate status marker | "CONTROL-ROOM REVIEW CANDIDATE — NOT ISSUED TO CODEX" | ✅ |
| Candidate execution base | `mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc` | ✅ |
| Base provenance | `ab4f12f5` is the **merge commit of PR #182** (parents `8f5f421e` + `18ea5d72`); PR #182 merged 2026-07-21 | ✅ |
| Wave 4 control issue | #186 — open | ✅ |
| Deferred critical validation | #185 (`CV-013`) — open | ✅ |
| Binding review contract | PR #187 comment `5037625072` | ✅ |
| Review report path (this file) | `docs/06-prompts/wave-4-gate-a-claude-review.md` | — |

**Identity gate — PASS (all 9 required pre-checks confirmed):**

1. PR #187 open, draft, unmerged. ✅
2. Head exactly `31fe1f2cb716ccb9d74bd43f763ad9e4041e4e55`. ✅
3. Changes only the candidate documentation file. ✅
4. Candidate explicitly marked not issued to Codex. ✅
5. Execution base exactly `ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`. ✅
6. PR #182 merged at that integration commit. ✅
7. Issues #185 and #186 open. ✅
8. No authorized Wave 4 fulfillment implementation branch/PR exists — the only
   Wave-4 branch present is this control-room review branch; no `sol/wave-4-*`
   or fulfillment PR exists. ✅
9. No fulfillment addon at base — `addons/` = `adams_base`,
   `shopify_connector_core`, `shopify_connector_inventory`,
   `shopify_connector_product`, `shopify_connector_sale`; no
   `shopify_connector_fulfillment`. ✅

Protected references intact: `checkpoint/core-r2-readonly-uat-2026-07-15` =
`acd8c4691e72cf5590f2a56228b08f183b76cd9a` (matches CLAUDE.md §13 / issue
#165), `Shopify-connector` = `dd6ecb8f…`, `main` = `a5d45432…`. No hard stop.

---

## 2. Scope and evidence inspected

This review verified the candidate against the **actual repository at the
execution base**, not only its wording, and against **current official
Shopify/Odoo sources** where needed to judge research completeness. A
29-agent adversarial verification workflow was used (fan-out research →
dimension review → per-finding refutation pass); every P0/P1 finding below
survived an independent refutation attempt.

Evidence inspected (non-exhaustive):

- **GitHub:** PR #187 (get/files/commits/comments incl. contract `5037625072`),
  PR #182 (merged), issues #185, #186, #167; branch list; base merge parents.
- **Governance/decisions:** `CLAUDE.md` §13, `DEC-032` (roles/merge authority),
  `DEC-011` (fulfillment architecture, accepted; open items), `DEC-033`
  (readiness scope correction, accepted), DEC index (highest = **DEC-037**),
  `mvp-completion-program.md`, `mvp-program-state.md`, `mvp-acceptance-matrix.md`,
  `rejected-approaches-log.md` (RA-022/RA-023), `quality-feedback-loop.md`.
- **Fulfillment corpus (all "Proposed"):** `fulfillment-operating-modes.md`
  (16-condition Mode 2 engine), `shopify-fulfillment-status-model.md`
  (state taxonomy), `wave-4-definition-of-ready.md`,
  `task-014-fulfillment-tracking-implementation-packet.md` /
  `-proposed.md`, `fulfillment-mode-uat-matrix.md`, `ar008-…-brief.md`,
  `wave-0-roles-permissions-and-fulfillment-scope-refresh.md`.
- **Merged code (Stage 0 Layer 2 + domains):** `shopify_connector_core/models/*`
  (`job`, `job_actions`, `job_dispatch`, `job_enqueue`, `mutation_attempt`,
  `api_client`, `readiness_check`, …), `shopify_connector_sale/models/*`,
  `shopify_connector_inventory/models/*`.
- **Official sources (accessed 2026-07-21):** Shopify Admin GraphQL
  `FulfillmentOrder`, `fulfillmentCreate`, `fulfillmentTrackingInfoUpdate`,
  access-scopes, usage/limits, migrate-to-fulfillment-orders changelog; Odoo
  19.0 source `stock_move.py`, `stock_move_line.py`, `stock_picking.py`,
  `sale_stock`, `stock_delivery`, `ir_cron.py`, and 19.0 returns docs.

---

## 3. Executive verdict

> ## **REVISE** — safe to issue **after** the listed corrections.
>
> The candidate is a genuinely strong, accurate, well-controlled, **single
> complete end-to-end** Gate A prompt. It is **not** accept-as-written (four
> P1 corrections must land first) and it is **not** reject (no P0; the base,
> architecture, and control model are sound and the defects are localized
> wording/omission fixes). **P0 = 0, P1 = 4, P2 = 12.**

The candidate remains **one complete Codex session** (do not split it), its
phase controls are **sufficient** (with two P2 hardening items), it **prevents
implementation drift**, and it correctly keeps **CV-013 (#185) critical and
non-downgradable**.

---

## 4. What the candidate does well

`[Repo fact]`-grounded strengths, independently verified:

1. **Exact, correct identity gate (§3).** Base SHA, "merge commit of PR #182",
   protected-reference set, "no fulfillment addon", and "no competing
   authorized branch" all match the real checkout.
2. **Correct handling of absent Shopify credentials (§2, §18).** Missing
   creds/dev-store is explicitly *not* a Gate A blocker (no live operation this
   session), while #185/CV-013 is carried forward as a mandatory pre-UAT gate —
   no false hard stop, no silent CV-013 downgrade.
3. **Strong no-implementation / no-mutation gating.** §1 forbidden list, §5:168
   ("No phase authorizes fulfillment implementation"), §7, §14 (locked prompt
   marked NOT ISSUED), §17 pre-commit `addons/**` check, and §19 DoD all
   reinforce that no `addons/**` change and no Shopify mutation occur.
4. **Readiness-scope correction is accurately grounded.** The
   `read_fulfillments` → `read_merchant_managed_fulfillment_orders` /
   conditional `write_…` correction is a genuinely **Accepted** decision
   (`DEC-033`) and real code (`readiness_check.py:59`), and §10 correctly
   **forbids assuming scope/mutation names**, requiring official verification.
   `[Official fact]` both hardcoded scope names in issue #186 are **current and
   correct** for a merchant's own-warehouse connector.
5. **Layer 2 vocabulary is real, not invented.** Every §11/§13 term
   (C1/C2/NET/C3, business-intent & exact-request fingerprints,
   `operation_scope`, `connection_generation`, reconciliation, replacement,
   one-job/one-attempt) maps to actual merged `shopify_connector_core` code
   (`mutation_attempt.py:140` = "one attempt"). No fabricated seam.
6. **"No unsupported exactly-once claim" is explicit (§13).** `[Official fact]`
   `fulfillmentCreate` / `fulfillmentTrackingInfoUpdate` expose **no**
   `idempotencyKey` — the candidate's verify-before-retry Layer 2 contract and
   its refusal to overclaim exactly-once are the correct design.
7. **DEC numbering is not hardcoded (§12).** It instructs discovering the next
   unused identifier (correctly **DEC-038**) rather than guessing.
8. **Genuinely one complete session (§4).** Automatic phase-to-phase
   continuation, a durable per-phase checkpoint file, a usable
   `PARTIAL GATE A — RESUME FROM PHASE <N>` path, and only two honest
   conclusions (§1) so partial work cannot be presented as complete.
9. **Exact file-boundary method (§14, J).** It explicitly **forbids** broad
   `addons/shopify_connector_{core,sale,inventory}/**` wildcards and requires
   every cross-module edit to name file, symbol, demonstrated need, and
   regression responsibility.
10. **Concurrency realism (§14).** "Do not represent savepoints or sequential
    independent connections as simultaneous concurrency" — the exact lesson
    from Task 013.
11. **Complete decision matrix (§12).** 40 items map to essentially every
    decision-critical topic (fulfillable quantity, picking↔FO identity, line
    mapping, partials, multiple pickings/FOs, multi-location, backorders,
    cancellations both sides, returns, tracking create/update, mode
    admission/switching, disconnect/reconnect, COD, one-job/one-attempt,
    operation-scope, idempotency, retry/replacement lineage, reconciliation,
    clean rejection, manual review, company consistency, permissions, logging,
    scheduled/manual admission, replay/duplicate prevention, readiness,
    upgrade/uninstall, historical deliveries, dev-store cleanup).
12. **Anti-duplication and citation discipline exist (§8, §16).** The 11-way
    claim taxonomy and "Do not create a second source of truth" are present —
    the P1/P2 duplication and status findings below are about *consistency*
    with these rules, not their absence.

---

## 5. P0 findings

**None.** No instruction could authorize implementation or a Shopify mutation
prematurely; the base and protected references are correct; the architecture is
sound; no material mutation/reconciliation/security control is missing; and no
instruction risks data corruption or duplicate remote effects. The prompt is
**not unsafe to issue**; the corrections below are about correctness,
governance accuracy, and duplication — not safety.

---

## 6. P1 findings (must be corrected before Codex issuance)

> Full exact-replacement text for each is in **§14 Required corrections**.

- **P1-1 — Authority model contradicts Accepted DEC-032 without citation (§1).**
  §1 asserts *as fact* that "**ChatGPT** is the strategic control room, scope
  governor, reviewer, **acceptance authority, and merge-authorizing
  authority**." Accepted `DEC-032` (§33/§39) and issue #167 and CLAUDE.md §13
  make **Claude** the independent control room and *"the only party authorized
  to accept/merge a wave PR into `mvp/program-integration`"*; Sol never
  self-accepts or merges. The candidate is a GitHub source-of-truth artifact
  (Phase 7 writes it into canonical trackers), so an **uncited** reassignment of
  control-room/merge authority to ChatGPT is a decision-authority + canonical-doc
  conflict. It is **P1, not P0**, because Sol's own safety controls (no
  self-accept/merge) are intact. Because *this very review track is
  ChatGPT-framed*, the owner **may** be legitimately reassigning — but that
  reassignment must be **recorded and cited**, per CLAUDE.md §3/§8.

- **P1-2 — "Accepted" 16-condition Mode 2 engine overstates governance status
  (§6:180, §9:291, §12:527/551; internally inconsistent with §19:973).** The
  16-condition engine and the fulfillment-state taxonomy live **only** in
  `fulfillment-operating-modes.md` §4 and `shopify-fulfillment-status-model.md`,
  both headed **"Status: Proposed … Not accepted."** `DEC-011` (the accepted
  *architecture*) **explicitly left partial/backorder/idempotency-key linkage
  OPEN.** Product direction (`mvp-completion-program.md`, Wave 4) mandates
  *delivering* a Mode 2 backend with a 16-condition engine, but does **not**
  ratify the exact rule text. Calling it "accepted" three times (violating
  CLAUDE.md §8) can cause Sol to preserve an unaccepted rule set as settled law
  and skip the reconciliation/escalation Gate A exists to perform. The
  candidate's own §19 already says "preserved **or its conflict escalated**" —
  the fix makes §6/§9/§12 consistent with that correct framing.

- **P1-3 — Canonical-document duplication via near-miss default paths
  (§13:567–568, §14:790–792; also §9 inventory).** The named default outputs
  are near-miss forks of files that **already exist** at the base:
  `wave-4-fulfillment-definition-of-ready.md` vs existing
  **`wave-4-definition-of-ready.md`** (already the Wave 4 fulfillment DoR);
  `task-014-fulfillment-implementation-packet.md` vs existing
  **`task-014-fulfillment-tracking-implementation-packet.md`** (+ `-proposed.md`);
  `wave-4-fulfillment-validation-plan.md` vs existing
  **`fulfillment-mode-uat-matrix.md`**. A worker who looks for the literal
  default and does not find it will create a **second Wave 4 DoR / Task 014
  packet** — the exact split §16 forbids and the direct enemy of a *single
  frozen* Gate A contract. The general anti-duplication guard reduces but does
  not remove the trap while the misleading defaults remain.

- **P1-4 — Mandatory end-of-session learning review omitted from the closeout
  (§15/§16/§19).** CLAUDE.md §12 ("A session is **not complete** until the
  quality gate is satisfied") and §13 ("the handoff/quality-loop requirement §12
  … still applies **in full** to this program") make running
  `quality-feedback-loop.md` and recording its outcome in the **Learning
  feedback loop** section of `research-handoff.md` **mandatory**. The candidate
  references `quality-feedback-loop.md` only once — as a Phase-1 inventory item
  (§9) — and never as a review to **run**. §15 trackers, §16 function 15, and
  §19 DoD all omit it, so a worker could declare Gate A "done" with a binding
  governance obligation unmet.

---

## 7. P2 findings (useful; do not block issuance)

Exact text for each is in **§14**. Grouped by theme:

**Official-source precision (research verified 2026-07-21):**
- **P2-1** — §7/§14: name the **deprecated** `fulfillmentCreateV2` /
  `fulfillmentTrackingInfoUpdateV2` (V2 suffix removed Admin API **2024-10**) so
  the RA-022 source-guard is deterministic. `[Official fact]`
- **P2-2** — §10/§14: add the separate **`fulfill_and_ship_orders` staff
  permission** that `fulfillmentCreate` requires *in addition to* the write
  access scope (a distinct gate). `[Official fact]`
- **P2-3** — §10: force verification that Odoo 19 done quantity is **`quantity`**
  (there is **no** `qty_done`/`quantity_done` in 19; `product_uom_qty` = demand).
  The Shopify fulfillable-line mapping must read `quantity`. `[Official fact]`
- **P2-4** — §6/§7: state that **Shopify-side return/reverse-fulfillment sync is
  OUT of Wave 4**; Odoo return pickings are researched only as a forward
  boundary.

**Contract completeness:**
- **P2-5** — §12: add decision item 41 — **FulfillmentOrder status/eligibility
  gating** (which of OPEN/IN_PROGRESS admit a fulfillment; how ON_HOLD /
  SCHEDULED / CLOSED / INCOMPLETE are skipped/deferred/reviewed), for both modes.
- **P2-6** — §14 locked prompt: add an explicit **no-silent-boundary-expansion**
  clause + hard-stop (dimension J's failure mode must be carried into the future
  implementation prompt).
- **P2-7** — §14 allowlist: replace the `addons/shopify_connector_fulfillment/**`
  **wildcard** with an enumerated subtree (it contradicts §14's own "list every
  permitted file explicitly"), and pin the core exception to exactly
  `readiness_check.py` `REQUIRED_MVP_SCOPES`.
- **P2-8** — §13 Layer 2: spell out "fresh pre-C2 read" as the **primary
  duplicate-prevention control** (verify-before-retry / adopt-if-found), since
  the mutations have no native idempotency.
- **P2-12** — §14 unit tests: require **regression tests for prior defects**
  (`sync-engine-risk-register.md`) and explicit RA-022/RA-023 guards (CLAUDE.md
  §9 mandates "edge cases and prior defects").
- **P2-13** — §14 rollback: add rollback of the cross-module readiness-check
  scope-name correction.
- **P2-14** — §14 static-guard: encode name-specific RA-023
  (`lineItemsByFulfillmentOrder`, no order-ID-only path) and legacy/deprecated
  mutation guards.

**Execution quality / one-session robustness:**
- **P2-9** — after §5: add a **depth-priority (anti-shallow) directive** ranking
  the decision-critical contracts that must stay self-derived under the heavy
  one-session load.
- **P2-10** — §4: **commit AND push** the checkpoint at every phase boundary
  (not only on forced stop), since §17 batches phases into ~5 commits.
- **P2-11** — §9: explicitly **name** the existing canonical Wave 4 files in the
  Phase 1 inventory list.
- **P2-15** — §3 item 6 / §18: clarify that the existing
  `control-room/wave-4-gate-a-prompt-review` branch and PR #187 are **expected**
  and are not a "competing authorized" branch/PR (avoid a false identity
  hard stop).
- **P2-16** — §20 vs §19: the 28-item final report substantially restates the
  24-item DoD; compress to reduce output load.

---

## 8. Completeness assessment by review dimension (A–M)

| Dim | Area | Assessment |
| --- | --- | --- |
| **A** | Identity & environment | **Strong.** Exact base/PR/protected refs correct; absent-Shopify-creds handled correctly. Minor: false-hard-stop clarity (P2-15). |
| **B** | Authority & governance | **Defect (P1-1).** Worker safety controls intact, but the control-room/merge-authority attribution contradicts Accepted DEC-032 uncited. |
| **C** | One-session control model | **Strong.** Auto-continue, durable checkpoint, usable resume, honest-conclusion lock. Harden with P2-9, P2-10. Remains one session. |
| **D** | Repository-resource inventory | **Mostly strong; P1-3 + P2-11.** Supersession classification required and next-DEC discovered; duplication risk from near-miss default paths and generic (unnamed) inventory categories. |
| **E** | Official-source research | **Accurate & essentially complete.** Shopify/Odoo §10 lists verified current; correctly forbids hardcoding names. Add precision P2-1..P2-4. No P0/P1. |
| **F** | Actual-code audit | **Clean.** Every audit target and Layer 2 term traces to real merged code; no invented seam; order/inventory targets all exist. |
| **G** | Accepted fulfillment contracts | **Defect (P1-2).** FulfillmentOrder-only / no-legacy / readiness-scope correctly *accepted*; but the Mode 2 engine + taxonomy are mislabeled "accepted" when their source docs are "Proposed." |
| **H** | Decision reconciliation | **Near-complete.** 40-item matrix covers the checklist; add FO-status gating (P2-5). |
| **I** | Architecture & Layer 2 | **Strong.** Modular boundary, no-giant-file + no-micro-module, Stage 0 reuse, no exactly-once overclaim, one-job/one-attempt matches code. Sharpen P2-8. |
| **J** | Future file boundary | **Strong method; two gaps.** Broad wildcards forbidden and cross-module edits gated — but a `…_fulfillment/**` wildcard slips in (P2-7) and the no-silent-expansion rule is not carried into the locked prompt (P2-6). |
| **K** | Tests & evidence | **Broad & realistic** (genuine concurrency, runtime, dev-store, CV-013 before acceptance). Add regression-for-prior-defects, RA-022/RA-023 guards, staff-permission tests (P2-12, P2-14, P2-2). |
| **L** | Docs, rollback & handoff | **Defect (P1-4) + P2s.** Locked-prompt-unissued, rollback, and tracker updates present; **learning review omitted**; readiness-check rollback + duplication reuse to add (P2-13, P1-3). |
| **M** | Efficiency & execution quality | **Good; heavy.** One large session with ~15 canonical outputs; add depth-priority (P2-9) and compress §20 (P2-16). No contradictory instructions beyond the authority/status ones already logged. |

---

## 9. Efficiency and context-risk assessment

`[Inference]` The single session mandates ~15 canonical documents (§16) plus a
40-row/11-field decision matrix (§12), full Mode 1 **and** Mode 2 contracts at
~28 attributes each (§13), ~25 unit-test cases + 9 concurrency designs + runtime
+ dev-store + rollback + a **complete future locked implementation prompt**
(§14), a 27-point adversarial review (§15), six tracker updates, and a 28-item
final report (§20). This is a very large output surface for one Codex session,
and the heaviest, most decision-critical material (Layer 2 seam, Odoo↔Shopify
quantity/line/location mapping, Mode 2 conditions) is the most likely to be
thinned under context pressure.

**This is a real risk but not a reason to split the prompt.** The candidate
already mitigates well: phase-boundary `PARTIAL GATE A` stop, a durable
checkpoint file, "reference existing canonical docs" licence (§16), and
honest-conclusion lock (§1). Two cheap, one-session-preserving hardening items
remove most residual risk: **P2-9** (explicit depth-priority so the
decision-critical contracts are never thinned to cover packaging) and **P2-16**
(stop §20 from restating §19). **P2-10** (push at every phase boundary) protects
against an abrupt context loss between the ~5 grouped commits. No instruction is
impossible; no two *substantive* instructions contradict once P1-1/P1-2 are
fixed.

---

## 10. Does it remain one complete Codex session?

**Yes — confirmed, and it should stay that way.** The candidate is deliberately
phase-gated *inside one session* with automatic phase-to-phase continuation
(§4), a single durable checkpoint file, and a `RESUME FROM PHASE <N>` recovery
path. None of the recommended corrections split it; P2-9/P2-16 make the single
session more robust, not shorter. Do **not** break it into multiple Codex
sessions for length.

## 11. Are its phase controls sufficient?

**Yes, with two P2 hardening items.** The seven ordered, non-reorderable phases,
the per-phase checkpoint, the "no phase authorizes implementation" rule, and the
two-outcome conclusion lock are sufficient to prevent partial-as-complete
reporting. Add **P2-10** (durable commit+push at every phase boundary, not only
on forced stop) and **P2-9** (depth priority) to fully close the context-loss
and shallow-output gaps.

## 12. Does it prevent implementation drift?

**Yes.** No `addons/**` change (§1, §17 pre-commit check, §19), no Shopify
mutation (§2, §7, §18), locked implementation prompt **created but not issued**
(§14), and no Gate B / Wave 5 crossover (§1, §5, §7). One residual gap:
the future locked prompt should itself carry the no-silent-file-expansion rule
(**P2-6**) so drift is prevented in Gate B as well as Gate A.

## 13. Does CV-013 remain critical?

**Yes — confirmed and non-downgradable.** §1 forbids closing/downgrading #185;
§2/§6 carry it forward; §14 requires CV-013 **and** dev-store fulfillment
validation green before Wave 4 final acceptance; §18 forbids hard-stopping on
missing Shopify creds; §19 lists CV-013 carried forward as critical. No change
needed.

---

## 14. Required corrections

Format per item: **severity · candidate section · problem (exact wording or
omission) · exact change · rationale · evidence.** Line numbers are as they
appear in the candidate at head `31fe1f2c`.

### P1-1 · §1 Role, authority, and non-negotiable boundaries (candidate.md:20)

- **Problem (exact wording):** "ChatGPT is the strategic control room, scope
  governor, reviewer, acceptance authority, and merge-authorizing authority.
  Claude may later perform an independent review of your Gate A package."
- **Exact replacement (line 20):**
  > "Under the currently accepted governance (`DEC-032` §33/§39, issue #167,
  > `CLAUDE.md` §13), **Claude** is the independent control room for this
  > program — scope governor, release gatekeeper, and the only party authorized
  > to accept and merge a Wave 4 PR into `mvp/program-integration`. ChatGPT sets
  > strategy and reviews; the product owner is the final authority. **If**
  > control-room/merge authority has been reassigned to ChatGPT for this track,
  > this prompt MUST cite the specific accepted decision record (a
  > `docs/04-decisions/` DEC or an `mvp-completion-program.md` §9 control-room
  > decision) that supersedes `DEC-032` §39; absent that citation, `DEC-032`
  > governs. Regardless of who holds control-room authority, you (Sol) never
  > self-accept, never mark a PR ready, and never merge your own wave PR."
- **Also** align §14's locked-prompt marker (candidate.md:832) so it does not
  assert "CHATGPT CONTROL-ROOM ACCEPTANCE" as the sole recorded authority
  without the same citation.
- **Rationale:** CLAUDE.md §3/§8 — a governance change must be recorded in
  GitHub before it is asserted as fact in a canonical artifact; naming the wrong
  acceptance/merge authority makes decision authority ambiguous. P1 (not P0):
  worker self-accept/self-merge remain forbidden, so no unsafe merge is enabled.
- **Evidence:** `docs/04-decisions/DEC-032-mvp-autonomous-execution-model.md`
  lines 33, 39 ("only Claude (control room) may accept and merge a macro-wave
  PR …; Sol may never merge its own wave"), 50; `CLAUDE.md` §13; issue #167
  Roles table; candidate.md:20, :832.

### P1-2 · §6 Binding scope (candidate.md:174–188), §9 (candidate.md:291), §12 (candidate.md:527, 551) — remove the false "accepted" status of the Mode 2 engine

- **Problem (exact wording):** three occurrences of "the exact **accepted**
  16-condition Mode 2 engine" (candidate.md:180, :291, :551), "18. every
  **accepted** Mode 2 condition" (:527), and the §6 preface "The **accepted**
  direction is:" (:174) bundling ratified architecture with a proposed rule set.
- **Exact change (a) — §6:174–188, split into two governance tiers:**
  > "The scope below is **product-directed** for Wave 4
  > (`mvp-completion-program.md`, 'Wave 4 — Fulfillment and tracking'). Keep two
  > governance tiers strictly separate and never conflate them:
  >
  > **Accepted architecture (ratified — preserve, do not reopen):**
  > - Shopify FulfillmentOrder surfaces only (`DEC-011`, Accepted 2026-07-02;
  >   RA-022/RA-023);
  > - readiness-scope correction to the merchant-managed FulfillmentOrder scopes,
  >   conditionally requiring the write scope (`DEC-033`, Accepted).
  >
  > **Product-directed scope to DELIVER whose exact rule text is still
  > PROPOSED — Not accepted (carry verbatim, treat as a proposed contract, and
  > route for explicit control-room acceptance in Phase 4; do NOT self-label as
  > accepted):**
  > - both fulfillment Mode 1 and Mode 2 backend; per-store
  >   `fulfillment_operating_mode`;
  > - the exact 16-condition Mode 2 engine currently in
  >   `docs/02-product/fulfillment-operating-modes.md` §4 (Status: Proposed —
  >   Not accepted);
  > - the complete fulfillment-state taxonomy in
  >   `docs/02-product/shopify-fulfillment-status-model.md` (Status: Proposed);
  > - mode-switch state machine; disconnected-period reconciliation; COD
  >   interplay; durable Layer 2 mutation ownership; one job to at most one
  >   attempt; idempotency, retries, replacement lineage, reconciliation,
  >   duplicate prevention, logs, manual-review routing."

  (Delete the now-duplicated residual readiness-scope bullet at candidate.md:188,
  since it is moved into the Accepted tier.)
- **Exact change (b) — §9:291:** replace with
  > "- the exact 16-condition Mode 2 checklist as written in
  > `docs/02-product/fulfillment-operating-modes.md` §4 (Status: Proposed — Not
  > accepted); classify its exact governance status — do not assume it is
  > accepted;"
- **Exact change (c) — §12:527:** replace with
  > "18. every **proposed** Mode 2 condition (source: `fulfillment-operating-
  > modes.md` §4, Not accepted): disposition = preserve verbatim and escalate
  > for control-room acceptance;"
- **Exact change (d) — §12:551:** replace with
  > "Locate and preserve **verbatim** the exact 16-condition Mode 2 engine in
  > `docs/02-product/fulfillment-operating-modes.md` §4 (Status: Proposed — Not
  > accepted). Do not compress, expand, or paraphrase it, and do not label it
  > 'accepted'. Because its architecture parent `DEC-011` left partial/backorder/
  > idempotency OPEN, carry it as a **proposed** rule set that Phase 4 must route
  > for explicit control-room acceptance; for each condition record whether it is
  > derivable from an accepted record or must be escalated."
- **Rationale:** CLAUDE.md §8 — a proposed rule set must never be presented as an
  accepted Decision. This also makes §6/§9/§12 consistent with the candidate's
  own correct §19:973 ("preserved **or its conflict escalated**").
- **Evidence:** `docs/02-product/fulfillment-operating-modes.md:3` ("Status:
  Proposed … Not accepted"), :172 (condition 16), :371/:394 ("16-condition
  checklist"); `docs/02-product/shopify-fulfillment-status-model.md:3`;
  `DEC-011` acceptance note lines 24, 30 (partial/backorder + idempotency-key
  OPEN); `mvp-completion-program.md` Wave 4 (product-direction, no "accepted");
  candidate.md:174, :180, :291, :527, :551 vs :973.

### P1-3 · §13 (candidate.md:567–568), §14 (candidate.md:790–792) — point default paths at existing canonical files

- **Problem (exact wording):** default paths
  `docs/07-implementation-plan/wave-4-fulfillment-definition-of-ready.md` (:567),
  `docs/07-implementation-plan/task-014-fulfillment-implementation-packet.md`
  (:568), `docs/05-qa/wave-4-fulfillment-validation-plan.md` (:792) — each a
  near-miss fork of an existing canonical file.
- **Exact change — §13:567–568:**
  > "- **UPDATE the existing** `docs/07-implementation-plan/wave-4-definition-of-
  > ready.md` (the canonical Wave 4 fulfillment DoR — do NOT create
  > `wave-4-fulfillment-definition-of-ready.md`);
  > - **UPDATE the existing**
  > `docs/07-implementation-plan/task-014-fulfillment-tracking-implementation-
  > packet.md` and reconcile it against
  > `task-014-fulfillment-tracking-proposed.md` (do NOT create
  > `task-014-fulfillment-implementation-packet.md`);"
- **Exact change — §14:792:**
  > "Update/extend the existing `docs/05-qa/fulfillment-mode-uat-matrix.md` (with
  > `cod-uat-matrix.md` / `reconnect-backfill-uat-matrix.md` where relevant) as
  > the canonical validation surface; create a new validation-plan file only if
  > Phase 1 proves no existing file can host it, and record the canonical-path
  > mapping in the resource inventory."
- **Add to §16:** "Before writing any default path in §9/§10/§13/§14, first grep
  `docs/` for an existing file serving that function; a naming near-miss is still
  a duplicate."
- **Rationale:** §16 forbids a "second source of truth"; a forked Wave 4 DoR /
  Task 014 packet splits the single frozen Gate A contract across two files.
- **Evidence:** `ls docs/07-implementation-plan/` →
  `wave-4-definition-of-ready.md` (title "Wave 4 — Definition of Ready
  (Fulfillment & Tracking)", Status: Proposed),
  `task-014-fulfillment-tracking-implementation-packet.md`,
  `task-014-fulfillment-tracking-proposed.md`; `ls docs/05-qa/` →
  `fulfillment-mode-uat-matrix.md`, `cod-uat-matrix.md`,
  `reconnect-backfill-uat-matrix.md`; candidate.md:567, :568, :792.

### P1-4 · §15 (candidate.md:874–881), §16 (candidate.md:915), §19 (candidate.md:962–985) — require the mandatory learning review

- **Problem (omission):** the end-of-session learning review
  (`quality-feedback-loop.md`) and its recorded outcome in the **Learning
  feedback loop** section of `research-handoff.md` are absent from the tracker
  list, the canonical-output list, and the Definition of Done.
- **Exact additions:**
  - §15 tracker list — add: "Run the mandatory end-of-session learning review
    per `docs/05-qa/quality-feedback-loop.md` and record its outcome (lessons,
    process improvements, defects-to-prevent) in the **Learning feedback loop**
    section of `docs/01-research/research-handoff.md`."
  - §16 — add **function 16**: "end-of-session learning-loop review executed per
    `quality-feedback-loop.md`, with its outcome recorded in the research-handoff
    Learning feedback loop section."
  - §19 DoD — add condition: "the mandatory end-of-session learning review
    (`quality-feedback-loop.md`) has been run and its outcome recorded in the
    handoff."
- **Rationale:** CLAUDE.md §12 ("A session is **not complete** until the quality
  gate is satisfied") and §13 (§12 "still applies **in full** to this program").
- **Evidence:** `CLAUDE.md` §12, §13; `docs/05-qa/quality-feedback-loop.md`
  present; candidate.md:311 (only reference), :874–881, :915, :962–985.

### P2 corrections (exact text)

- **P2-1 · §7:200 / §14 static-guard:** add "the deprecated `fulfillmentCreateV2`
  and `fulfillmentTrackingInfoUpdateV2` (V2 suffix removed as of Admin API
  2024-10); use only the current `fulfillmentCreate` and
  `fulfillmentTrackingInfoUpdate`." *Evidence:* Shopify changelog
  "removing-v2-suffix-from-fulfillmentcreatev2-and-fulfillmenttrackinginfoupdatev2".
- **P2-2 · §10 (after :351) / §14 security tests:** add "the separate
  `fulfill_and_ship_orders` staff permission that `fulfillmentCreate` requires in
  addition to the `write_merchant_managed_fulfillment_orders` access scope, and
  how the connector surfaces it as a readiness/operator prerequisite." *Evidence:*
  `https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentCreate`.
- **P2-3 · §10:376:** replace with "`stock.move` / `stock.move.line` quantity
  semantics — verify in Odoo 19 source that the DONE quantity is `quantity`
  (there is no `qty_done`/`quantity_done` in 19) and that `product_uom_qty` is
  DEMAND; the Shopify fulfillable-line quantity must map from `quantity`, never
  demand or a stale `qty_done`." *Evidence:* Odoo 19.0 `stock_move.py`,
  `stock_move_line.py`.
- **P2-4 · §6 (after :190) / §7:** add "Shopify-side return / reverse-fulfillment
  mutation sync (e.g. `reverseFulfillmentOrder` / `returnCreate`) is OUT of Wave
  4 scope; Odoo return pickings (`stock.return.picking`) are researched only as a
  forward-fulfillment boundary." Annotate §12 item 11 and the §14 "returns
  boundary" test accordingly. *Evidence:* Odoo 19 `stock.return.picking` is a
  distinct concept from Shopify's return API.
- **P2-5 · §12 (add item 41):** "41. FulfillmentOrder status/eligibility gating:
  which FO `status` values (OPEN, and IN_PROGRESS for remaining quantity) admit a
  fulfillment attempt, and how ON_HOLD (`fulfillmentHolds` present), SCHEDULED
  (`fulfillAt` in the future), CLOSED, and INCOMPLETE FOs are skipped, deferred,
  or routed to manual review rather than attempted — in both Mode 1 and Mode 2;
  tie the pre-mutation live re-read (RA-023) to this gate." *Evidence:* Shopify
  `FulfillmentOrder` status enum {OPEN, SCHEDULED, ON_HOLD, IN_PROGRESS, CLOSED,
  INCOMPLETE, CANCELLED}.
- **P2-6 · §14 locked-prompt list (after :816) + hard-stops (:826):** add "an
  explicit boundary-lock rule: the implementation worker may not create, rename,
  move, or broaden any file/directory beyond the frozen exact allowlist, may not
  convert any path to a wildcard, and must hard-stop and escalate — rather than
  silently expand scope — if implementation appears to require a file outside the
  allowlist." *Evidence:* candidate.md:812–828 omits it; CLAUDE.md §9.
- **P2-7 · §14:684, :685:** replace the `addons/shopify_connector_fulfillment/**`
  wildcard with an enumerated subtree ("`__manifest__.py`, `__init__.py`,
  `models/`, `views/`, `security/`, `data/`, `tests/` as actually required — not
  an open `**`"), and pin line 685 to
  "`addons/shopify_connector_core/models/shopify_connector_readiness_check.py` —
  edit restricted to the `REQUIRED_MVP_SCOPES` constant only." *Evidence:*
  candidate.md:684 vs :688 ("List every permitted future implementation file
  explicitly"); `readiness_check.py:59`.
- **P2-8 · §13:608:** replace "fresh pre-C2 read requirements;" with "fresh
  pre-C2 read requirements: before every C2 fulfillment mutation the job re-reads
  the target FulfillmentOrder(s) and existing fulfillments/tracking and adopts an
  already-applied effect (verify-before-retry / adopt-if-found) — the primary
  duplicate-prevention control given the absence of native idempotency."
  *Evidence:* `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` expose no
  `idempotencyKey`.
- **P2-9 · after §5:168 (new subsection "Depth priority"):** "This is one session
  with a large output surface; allocate depth in this order and never thin the
  top tier to cover the lower tier. **Tier 1 (must be deep, self-derived):** the
  Layer 2 integration contract; the Odoo↔Shopify quantity/line-item/location
  mapping seams; Mode 1 and Mode 2 admission + condition contracts; idempotency,
  reconciliation, duplicate-prevention; the exact future file allowlist. **Tier 2
  (complete but MAY reference existing canonical docs by path+section per §16):**
  resource inventory, official-source refresh where an existing capture is still
  current, test enumeration, dev-store plan, rollback."
- **P2-10 · §4 (after :134):** "Commit AND push the checkpoint file (and any
  files completed) at every phase boundary before starting the next phase — not
  only on a forced stop. The §17 grouped-commit sequence is an organization
  target, not a licence to leave a completed phase unpushed."
- **P2-11 · §9 (append to the search list):** "Explicitly inventory and classify
  by name: `wave-4-definition-of-ready.md`,
  `task-014-fulfillment-tracking-implementation-packet.md`,
  `task-014-fulfillment-tracking-proposed.md`, `fulfillment-operating-modes.md`,
  `shopify-fulfillment-status-model.md`, `fulfillment-mode-uat-matrix.md`,
  `ar008-fulfillment-architecture-decision-brief.md`,
  `master-blueprint-inventory-fulfillment.md`, and the 2026-07-16
  `00-source-materials` fulfillment/COD/Odoo captures."
- **P2-12 · §14 unit-test plan:** add "regression tests for every prior known
  defect/risk in `sync-engine-risk-register.md` touching the fulfillment or
  Layer 2 path, and for each binding rejected approach (RA-022 legacy API,
  RA-023 order-ID-only fulfillment)." *Evidence:* CLAUDE.md §9 ("edge cases and
  prior defects").
- **P2-13 · §14 rollback plan:** add "rollback of the cross-module
  readiness-check scope-name correction in `readiness_check.py` (reverting
  `REQUIRED_MVP_SCOPES`) and its effect on store readiness state."
- **P2-14 · §14 static-guard:** add "RA-023 guard: every fulfillment mutation
  targets FO line items via `lineItemsByFulfillmentOrder` (fulfillmentOrderId +
  FO-line id + quantity + resolved location); a source scan proves no
  order-ID-only fulfillment path exists; plus a legacy/deprecated-mutation guard
  (no Order/Fulfillment API, no `*V2`)."
- **P2-15 · §3 item 6 (candidate.md:89) / §18 (candidate.md:948):** amend to
  "no already-authorized Wave 4 Gate A **implementation** branch/PR and no
  `shopify_connector_fulfillment` code branch exists. The existing
  `control-room/wave-4-gate-a-prompt-review` branch and PR #187 — containing only
  the Gate A review/prompt document and no addon code — are EXPECTED and are NOT
  competing authorized branches/PRs; do not hard-stop on them."
- **P2-16 · §20 (items 5–21, 24–27):** replace with "5. Confirmation that every
  §19 Definition-of-Done condition is met, with a one-line evidence pointer
  (file path or issue link) per condition; do not restate phase contents already
  committed to canonical files." Keep §20 items 1–4, 22, 23, 28.

---

## 15. Final statement

**Safe to issue after the listed corrections.** The candidate is not unsafe as
written (P0 = 0), and it is a sound, accurate, well-controlled, genuinely single
end-to-end Gate A prompt. It should not be issued *as written* because four P1
defects — the uncited authority-model contradiction (P1-1), the "accepted"
mislabel of a Proposed Mode 2 engine (P1-2), the canonical-document duplication
via near-miss default paths (P1-3), and the omitted mandatory learning review
(P1-4) — would otherwise inject an uncited governance override, freeze an
unaccepted rule set as settled, fracture the single Gate A contract, or let the
session close with a binding quality gate unmet. With P1-1..P1-4 applied (and,
recommended, the P2 precision/robustness items), the prompt is **safe for
ChatGPT to reconcile and issue to Codex as one complete session**. The candidate
prompt itself was not modified by this review, and ChatGPT alone issues the
final locked prompt.

---

### Review provenance

- Review method: repository verification at the exact base `ab4f12f5` +
  current official Shopify/Odoo source checks (accessed 2026-07-21) + a
  29-agent adversarial verification pass (0 of 20 material findings refuted).
- Reviewer: Claude Code (independent prompt/governance/quality reviewer).
- Date: 2026-07-21.
- No `addons/**` file changed; no Shopify operation performed; the candidate
  prompt was not edited; PR #187 remains draft and unmerged.
