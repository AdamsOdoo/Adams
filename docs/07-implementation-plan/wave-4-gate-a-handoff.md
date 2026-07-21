# Wave 4 Gate A — Session Handoff Checkpoint

> **Purpose.** Durable phase-boundary checkpoint for the single, seven-phase
> Wave 4 Gate A Definition-of-Ready / decision-reconciliation session executed
> under the locked prompt at
> `control-room/wave-4-gate-a-prompt-review@187f04d5…` /
> `docs/06-prompts/wave-4-gate-a-codex-review-candidate.md`
> (blob `57772d04960a910bd8715050649ddc4c08cc5430`).
> **This is a candidate Gate A package pending independent control-room (ChatGPT)
> acceptance.** It authorizes no implementation. It is not accepted, approved,
> final, or ready by virtue of this worker producing it.

**Updated:** 2026-07-21 · **Worker:** Claude (Opus 4.8), acting as the
explicitly-assigned authorized governance/research worker (see §0).
**Branch:** `claude/wave-4-gate-a-review-0nbhdw` · **Base SHA:**
`ab4f12f5a6857b2f3318ffc3b3f5f371307938bc` (`mvp/program-integration`, PR #182
merge commit).

---

## 0. Role, branch, and authority reconciliation (transparent, not silent)

The locked prompt is written addressing **"GPT-5.6 Sol"** and suggests the
branch `sol/wave-4-fulfillment-gate-a`. This session is executed by **Claude**
on the designated branch **`claude/wave-4-gate-a-review-0nbhdw`**. This is a
deliberate, documented reconciliation, not a silent substitution:

1. **Authority basis.** Issue #186 comment `5038326525` (BINDING WAVE 4
   GOVERNANCE CLARIFICATION) states: *"Claude is the independent reviewer and
   authorized runtime/governance worker when explicitly assigned."* This
   session's task prompt is that explicit assignment. Gate A is a
   **documentation/governance/research** package — it writes **no** connector
   feature code — so it is squarely inside Claude's permitted role under
   CLAUDE.md §13 ("governance, audit, wave review, and release-gating only; no
   feature coding by Claude").
2. **Branch basis.** This session's own Git Development Branch Requirements
   mandate `claude/wave-4-gate-a-review-0nbhdw`; that explicit per-session
   directive overrides the generic `sol/…` name the prompt wrote for Sol. The
   `claude/…` prefix is also accurate provenance (Claude authored it).
3. **Outputs stay candidate.** No self-acceptance, no ready-marking, no merge,
   no feature code. The only permitted conclusion is
   `READY FOR CONTROL-ROOM GATE A REVIEW` **or**
   `NOT READY — CONSOLIDATED DECISION BLOCKERS`. ChatGPT remains the acceptance,
   scope, and merge authority; the product owner remains the business authority.
4. **GitHub source of truth.** The GitHub-recorded issuance (issue #186 comment
   `5038409153`) names GPT-5.6 Sol as executor. This Claude execution is
   recorded transparently here, on the draft PR, and in the #186 handoff comment
   so the control room sees exactly what was produced and by whom, and can
   accept, reroute to Sol, or reject.

If the control room intended Sol specifically and not Claude to execute, this
package is still usable as an independent-reviewer Gate A candidate; nothing
irreversible was done.

---

## 1. Phase 0 — Exact identity gate (RECORDED — PASS, no hard stop)

Verified 2026-07-21 against live GitHub + local git + Odoo 19.0 source.

| # | §3 identity item | Result | Evidence |
|---|---|---|---|
| 1 | `mvp/program-integration` = required SHA | ✅ | `git rev-parse origin/mvp/program-integration` = `ab4f12f5a6857b2f3318ffc3b3f5f371307938bc` |
| 2 | PR #182 merged, merge commit = required SHA | ✅ | PR #182 `merged=true`, `merged_at=2026-07-21`; `ab4f12f5` parents = `8f5f421e` (prior mvp tip) + `18ea5d72` (PR #182 head); subject "Merge Task 013…" |
| 3 | Issue #185 (CV-013) open | ✅ | state `open` |
| 4 | Issue #186 open | ✅ | state `open`; authorizes "one Wave 4 Gate A session; do not implement addon code" |
| 5a | Checkpoint ref unchanged | ✅ | `checkpoint/core-r2-readonly-uat-2026-07-15` → `acd8c4691e72cf5590f2a56228b08f183b76cd9a` (matches #165) |
| 5b | `Shopify-connector` present | ✅ | `refs/heads/Shopify-connector` = `dd6ecb8f…` |
| 5c | `main` present | ✅ | `refs/heads/main` = `a5d45432…` |
| 5d | Issue #165 open/unchanged | ✅ | `open`, last updated 2026-07-15; records checkpoint SHA + PR #150/#151 pre-checkpoint heads |
| 5e | PR #150 unchanged / not merged | ✅ | head `10d0034e…` (= #165 record), draft, `merged=false`. NOTE: `state=closed` since 2026-07-15 (pre-Wave-4 baseline; head SHA intact). Cross-check vs `mvp-completion-program.md` §9. |
| 5f | PR #151 unchanged / not merged | ✅ | head `e4669aaf…` (= #165 record), draft, `merged=false`; same pre-Wave-4 closed baseline. |
| 6 | No competing authorized Wave 4 exec branch/PR | ✅ | Only `control-room/wave-4-gate-a-prompt-review` (+ draft PR #187) as expected governance artifacts; `sol/wave-3-stage-0-layer2` is a Wave 3 branch; open PRs = #187 (governance) + #183 (docs-only CHATGPT.md). No Wave 4 implementation branch/PR. |
| 7 | No `shopify_connector_fulfillment` addon at base | ✅ | `addons/` at base = adams_base, shopify_connector_core, _inventory, _product, _sale (no fulfillment) |
| 8 | Waves 2/3 Layer 2 + order + inventory code present | ✅ | core has job*/mutation_attempt/api_client/readiness_check; sale has order_binding/importer/sale_order_line; inventory has inventory_service/location_mapping |

**Governance records verified:** issue #186 comment `5038326525` (authority
clarification), issue #186 comment `5038409153` (Gate A issuance), PR #187
comment `5038405915` (final adjudication). Issue #185 remains open as CV-013.

**Environment gate:** all required capabilities present. Odoo not installed
locally → using an authoritative Odoo **19.0 FINAL** source checkout
(`github.com/odoo/odoo@19.0`, `b4f0111…`; `version_info=(19,0,0,FINAL,0,'')`),
blobless-sparse-cloned for stock/sale_stock/delivery/base modules. No §18
environment hard stop. **No live Shopify credentials / dev store — expected and
NOT a Gate A blocker; recorded as CV-013 (#185).**

**Branch action taken:** designated branch reset from `187f04d5` (control-room
prompt-review commit = base + two governance docs) to the clean base
`ab4f12f5` per prompt §4 "base directly on `ab4f12f5`". No force-push needed
(origin had no copy). The two control-room docs remain intact on
`control-room/wave-4-gate-a-prompt-review` + PR #187 — no loss.

---

## 2. Binding execution constraints carried from the adjudication

From PR #187 comment `5038405915` + issue #186 comment `5038326525`:

- The **16-condition Mode 2 engine is PROPOSED / not-accepted** — Gate A must
  **reconcile** it (preserve exactly where supported by evidence; propose
  line-level corrections + escalate where official Shopify / merged code /
  accepted decisions conflict), **never treat it as settled law**.
- **Reuse canonical files** — no forks. Canonical carriers:
  `docs/07-implementation-plan/wave-4-definition-of-ready.md`,
  `docs/07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md`,
  `docs/05-qa/fulfillment-mode-uat-matrix.md`.
- **DEC-011 is Accepted** (2026-07-02) but leaves partial/backorder rules, exact
  idempotency-key schema, and the location-confirmation mechanism **OPEN**.
- **Authority model:** ChatGPT = control room / acceptance / merge; Claude =
  independent reviewer / authorized governance worker when assigned. The
  existing DoR / modes docs still cite the older DEC-032 "Claude control room"
  wording — a contradiction to reconcile.
- **Next unused decision id = DEC-038** (highest existing is DEC-037).

---

## 3. High-power research plan (CLAUDE.md high-power mode — authorized)

- **Why:** verified Shopify FulfillmentOrder GraphQL behavior + Odoo 19 source
  semantics + deep 4-addon code audit + ~20-doc classification — broad and
  parallelizable.
- **Workstreams:** WS-1 doc inventory · WS-2 Shopify official research ·
  WS-3 Odoo 19 source · WS-4 connector code audit (run as one background
  gather workflow, structured/cited returns).
- **Authoritative sources:** current shopify.dev Admin GraphQL; cloned Odoo
  19.0 source; the repo.
- **Stop condition:** every version-sensitive claim supported or explicitly
  unresolved; every doc classified; every seam traced to real code.
- **Synthesis/verification:** Claude authors the canonical docs; Phase 7 runs an
  adversarial verification pass.
- **Unsupported-claim prevention:** agents return URL+access-date (Shopify) and
  file+symbol+lines (code/Odoo); anything uncited becomes an open question.

---

## 4. Phase status

| Phase | Status |
|---|---|
| 0 — Identity gate & environment | ✅ complete (this file §1); committed `c675c83` |
| 1 — Resource inventory & authority map | ✅ complete → `docs/01-research/wave-4-fulfillment-resource-inventory.md` |
| 2 — Official Shopify & Odoo 19 research | ✅ complete → `wave-4-shopify-official-fulfillment-notes.md`, `wave-4-odoo19-fulfillment-architecture-notes.md` |
| 3 — Merged-code integration audit | ✅ complete → `docs/03-architecture/wave-4-fulfillment-current-code-audit.md` |
| 4 — Decision & contradiction reconciliation | ✅ complete → `docs/04-decisions/DEC-038-…-reconciliation.md` (Proposed) |
| 5 — Candidate DoR, architecture & Task 014 packet | ✅ complete → DoR updated; Task 014 packet §10 Gate A addendum (arch + Layer 2 + Mode 1/2 contracts) |
| 6 — File boundary, tests, validation, rollback, locked prompt | ⏳ next |
| 7 — Adversarial review, trackers, handoff, final report | ⏳ pending |

**Phase 1 key results:** next unused decision id = **DEC-038**; canonical-output
map fixed; accepted contract separated from proposed candidates and superseded
records; contradictions logged for DEC-038.

**Phase 2 key results (all cited, Admin API 2026-07 / Odoo 19.0 FINAL):**
- All **7 Layer-A Shopify enum families EXACT-MATCH** the captured status model
  (independently re-verified 2026-07-21).
- **The "17 @idempotent" count is CURRENT, not stale** (agent direct-fetch of the
  live idempotency page dated 2026-02-02) — fulfillment mutations confirmed
  **absent** from it → **verify-before-retry validated** (corrects Phase-1
  contradiction #1; to fix in DEC-038 batch).
- New refinements → DEC-038: ">1 FO per location" (not one-per-location);
  `supportedActions.CREATE_FULFILLMENT` as the authoritative eligibility gate;
  `assignedLocation.location` nullable; staff permission `fulfill_and_ship_orders`
  distinct from API scope; input-array 250 vs FO-line 512 caps; pin API `2026-07`.
- **Odoo (verified-in-source):** done-qty = `stock.move.line.quantity` (no
  `qty_done` field); hook = `_action_done` (not re-entrant `button_validate`);
  backorder via `backorder_id`; `sale_id`/`sale_line_id` in `sale_stock`, carrier
  fields in `stock_delivery` (dep set correct); **new risk:** `send_to_shipper`
  auto-books on validation when carrier `rate_and_ship`.

**Phase 3 key results (symbol-level, base `ab4f12f5`):** the Layer 2 spine is fully
reusable (10 fulfillment seams identified with exact refs); inventory is the exact
7-callback template; **`shopify_line_item_gid` is populated but read by no matcher**
(fulfillment is its first consumer); `REQUIRED_MVP_SCOPES` still has the old
`read_fulfillments` (D-014-2 swap is a Wave 4 task); **fulfillment mutations have no
`@idempotent`** (prepare_preconditions must omit it; `userErrors` carry no code →
`code_required=False`+positive-evidence branch); 8 code-grounded risks logged incl.
`action_confirm()` auto-picking coexistence and the core Location-cache shared
ownership.

**Phase 4–5 key results:** DEC-038 (Proposed) = the 41-item decision matrix
(dispositions PRESERVE/REFINE/ESCALATE) + the **16-condition Mode 2 engine
reconciled condition-by-condition (12 preserve, 4 evidence-backed refine, 0
superseded)** + the authority-model reconciliation + **7 escalated control-room
questions (Q1–Q7)**. Task 014 packet §10 addendum: corrected base (`ab4f12f5`, not
`Shopify-connector`), modular architecture contract, Layer 2 integration contract
(no-`@idempotent`; verify-before-retry primary; own operation-scope literal;
`code_required=False`+positive-evidence classifier), Mode 1 & Mode 2 contracts, and
the note that the packet's §8 old locked prompt is **superseded** by the NEW locked
prompt. DoR authority model reconciled to comment `5038326525`; program-state note
refreshed (Waves 1–3 merged, Layer 2 accepted). Phase-1 inventory contradiction #1
(the "stale 17" mis-flag) corrected.

**Next phase:** Phase 6 — exact file allowlist/forbidden lists, static/source-guard
plan, unit/concurrency/runtime/dev-store plans, rollback plan, and the NEW locked
implementation prompt (`docs/06-prompts/sol-wave-4-fulfillment-locked-prompt.md`,
marked `LOCKED CANDIDATE — NOT ISSUED`). Commit 4; continue.

**Partial-resume anchor:** if a genuine environment/context/time limit forces a
stop, stop at a phase boundary after committing+pushing this checkpoint and
report `PARTIAL GATE A — RESUME FROM PHASE <N>`. Do not represent partial work
as complete Gate A output.
