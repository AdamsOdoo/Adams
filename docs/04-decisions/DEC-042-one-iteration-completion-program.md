# DEC-042 — One-Iteration Completion Program (repair-in-place, Sol builds, Claude reviews autonomously)

- **Status:** Accepted — direct product-owner directive, 2026-08-18.
- **Amends:** DEC-041 role allocation and the 2026-07-25 role-model addendum,
  for the scope of this program only. All §13 CLAUDE.md safety rules
  (no self-acceptance, durable non-suppressible review, exact-SHA runtime
  evidence, checkpoint protection) remain in force unchanged.
- **Supersedes:** nothing outside this program. `Shopify-connector` and `main`
  branch governance unchanged. Checkpoint
  `checkpoint/core-r2-readonly-uat-2026-07-15` untouched.

## 1. Decision

The product owner has directed one final, complete iteration to bring the
connector to release quality: fix the core workflows, consolidate the backend,
add real-time sync, harden the UI/UX to premium standard, then run one full
testing campaign — followed by release qualification. Rebuild-from-scratch is
**rejected**; open-ended patching is **rejected**; the accepted strategy is
**dependency-ordered repair-in-place on draft PR #206**
(`codex/ui-restructure-implementation`), continuing its existing ledger,
evidence chain, and commit conventions. No rebase, no force-push, no new
branch topology, every batch an independently revertable commit stack.

Basis for rejecting rebuild: the 2026-08-17/18 UAT defects were seam defects
(birth initialization, first-pair bootstrap, recovery routes, permissions,
one GraphQL lookup), not architectural failures; the repair loop demonstrably
converged (product and inventory verticals now proven live); and the
mutation-safety core (Layer-2 attempt protocol, CAS, fail-closed
preconditions, store-scoped isolation) is the product's differentiator and
survives intact. Evidence:
[`pr-206-coherent-repair-ledger-2026-08-17.md`](../07-implementation-plan/pr-206-coherent-repair-ledger-2026-08-17.md).

## 2. Roles (this program only)

| Role | Actor | Authority |
| --- | --- | --- |
| Implementation worker | **GPT-5.6 Sol** (ChatGPT), with Sol-side subagents for mechanical work | Implements batches autonomously within each batch's scope; never accepts, ready-marks, or merges its own work. |
| Pre-push sanity gate | **GPT-5.6 Luna** (ChatGPT-side) | Cheap pre-push check per batch (compile, contract adherence, obvious defects). Advisory only — **not** acceptance. |
| Independent reviewer + prompt engineer | **Claude** (this program's Claude Code sessions) | Authors batch prompts; performs the **binding** per-batch review from the exact head SHA; posts durable verdicts to PR #206. Never implements program code. |
| Final authority | **Product owner** | Merge/promotion of PR #206 and any release act. The only mandatory human touchpoint. |

The prompting and reviewing roles may be held by the same Claude session;
implementing and reviewing may not be held by the same actor, ever.

## 3. Autonomous review loop (no product-owner relay)

1. Sol completes a batch on the PR #206 branch, updates the repair ledger,
   triggers exact-head CI and the Odoo.sh development build, and posts one PR
   comment: `READY-FOR-CLAUDE-REVIEW — Batch <N> — <exact head SHA>` with
   links/IDs for all evidence (Actions run, Odoo.sh build, ledger section,
   screenshots for UI batches, live UAT records for live batches).
2. Claude's reviewer session is subscribed to PR #206 activity and wakes on
   that comment. It reviews from the exact SHA — full diff, tests, runtime
   evidence, live evidence — and posts the complete verdict verbatim as a PR
   comment: `CLAUDE INDEPENDENT REVIEW — Batch <N> — <SHA> — ACCEPT` or
   `… — REVISE` with the full finding list. Tier scrutiny per DEC-040
   (scales up with batch size; runtime evidence never skipped for code).
3. `REVISE` → Sol responds with **one consolidated correction** on the same
   branch and re-posts the ready comment. `ACCEPT` → Sol proceeds to the next
   batch without waiting for any human.
4. Sol reads Claude's verdicts directly on GitHub via its cloud browser.
   Nobody relays messages by hand.
5. After the final batch's `ACCEPT`, Claude posts a consolidated
   release-readiness verdict; the product owner performs the merge.

Fallback: if a wake event is missed, the Claude session re-checks the PR on a
scheduled self check-in. If Sol is blocked > 1 correction cycle on a genuine
commercial judgment call, it stops and the ledger records a `HARD STOP —
PRODUCT OWNER` line instead of guessing.

## 4. Batch plan (dependency-ordered; one iteration)

| # | Batch | Tier | Content (summary — full detail in the master prompt) |
| --- | --- | --- | --- |
| B1 | **Core-vertical UAT completion** | 1 | Prove live on the dev store: real order → scan → import (customer/tax/totals, replay-safe) → delivery validation → fulfillment SUCCESS/GID → repeat no-op → tracking → partial/backorder → Mode 1 external review → Mode 2 switch/application/rollback. Fix only defects this journey exposes. |
| B2 | **Backend consolidation refactor** | 1 (behavior-preserving) | Reconcile-handler hooks in core (delete the 3 domain copies); `_reconciliation_payload_hash` seam; shared cursor-scan producer (fixes the validation drift by construction); unified `userErrors`/transport-error classification; split `inventory_service.py` and the store god-model; parameterize the 4 admission gates; decompose the 2 god-methods; prose purge (no review-thread citations, no changelog docstrings; ≤ ~12% prose). Zero behavior change; full suite green before and after. |
| B3 | **Real-time sync (webhooks)** | 1 | Following the `_product_webhook` template: `_inventory_webhook` (`inventory_levels/update`), `_sale_webhook` (`orders/create|updated|cancelled` — cancelled → review case), `_fulfillment_webhook` (`fulfillments/create|update` → mode evidence); `refunds/create` → review-case evidence only, no accounting. All read-first, HMAC-verified, replay-deduplicated; cron scan remains the correctness backstop; webhook health on the dashboard. |
| B4 | **UI/UX premium hardening** | 2 (Tier-1 security checks) | The 10 prioritized fixes from Claude's 2026-08-18 UI review (wizard fatal-state retry; inline diff-confirm errors; dashboard load generation token; `save_and_exit` error handling; busy/`aria-busy` indicators; Mapping-vs-Binding terminology; webhook views de-jargonized + help text; default-filter help sweep; frontend assets + tours for fulfillment/webhook/sale/inventory incl. the mode-switch wizard; **dark mode** via the token layer). Plus differentiated credential-error copy and a lightweight no-dependency SVG trend chart. |
| B5 | **Full complete testing + release qualification** | 1 | Full suite fresh/warm/non-standard at the exact head (Actions + Odoo.sh); complete permission matrix (5 roles × menus/URLs/RPC/actions × two companies); upgrade proof from both historical origins with legacy data; full live UAT re-run of every vertical including webhook real-time paths; performance sanity vs PERF-0; scripted human visual walkthrough light + dark with screenshots; release-readiness report. Code changes only for defects this batch exposes, each requalified. |

**Out of scope (post-release roadmap, do not scope-creep):** refund
accounting, cancellation push, customer export, collections sync, discounts,
multi-currency (stays fail-closed), gift-card accounting, draft orders, B2B,
OAuth install flow. Recorded so no batch silently expands.

## 5. Resource and effort policy (quota conservation)

> Calibrated by product-owner instruction, 2026-08-18: default the main
> thread to medium effort; reserve high/max effort for the narrow Tier-1
> escalation list below (~15% of the work).

- **Sol main thread — medium effort by default:** batch integration, UI
  code, tests, live UAT driving/verification. **Escalate to high effort
  only for the Tier-1 escalation list:** B2 consolidation items 1–4 and 6
  (core seams/admission gates), B3 webhook admission/dedup/subscription
  logic, and any change touching the Layer-2 mutation attempt protocol.
- **Sol subagents — light effort:** mechanical sweeps (prose purge,
  terminology, help text, fixture updates, SCSS token work, test
  scaffolding). Main Sol integrates and stays accountable for the result.
- **Luna — medium effort, once per batch pre-push.** Escalate Luna to
  max only for the same Tier-1 escalation list. Luna is never spent on
  mechanical/dirty work, documentation, or UI copy — defects there are
  cheap and the Claude review catches them; Luna's value concentrates
  where defects are expensive.
- **Claude review is the expensive, binding gate** — protect it by making
  REVISE cycles rare: Luna catches cheap defects first, and corrections are
  always one consolidated pass, never dribbled.
- **No re-litigation:** accepted contracts (ledger §4, DEC-006/009/010/011)
  are not re-argued; evidence is recorded once in the ledger, not
  re-summarized per message; Sol references repo docs by path instead of
  restating them.
- **Cloud browser use (Sol):** trigger/inspect Odoo.sh builds and logs, read
  Claude's PR verdicts, drive live UAT in the Odoo.sh dev database with
  screenshots, verify remote state in the Shopify dev-store admin. Browser
  evidence is always tied to the exact SHA it was captured on.

## 6. Quality bar (binding on every batch)

Solid, efficient, non-over-engineered backend following Odoo 19 and Shopify
best practices; real-time updates wherever a webhook topic exists, with scan
reconciliation as backstop; premium, accessible, dark-mode-capable,
tour-covered UI; no fabricated evidence ever; a dispatched job is never
recorded as a Shopify success without a verified remote read.

## 7. References

- Governing analysis: Claude architecture/feature/UI reviews of 2026-08-18
  (recorded in the session handoff and the master prompt).
- Master implementation prompt:
  [`../06-prompts/sol-one-iteration-master-prompt.md`](../06-prompts/sol-one-iteration-master-prompt.md)
- Live ledger: [`../07-implementation-plan/pr-206-coherent-repair-ledger-2026-08-17.md`](../07-implementation-plan/pr-206-coherent-repair-ledger-2026-08-17.md)
