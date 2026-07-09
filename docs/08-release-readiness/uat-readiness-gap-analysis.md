# UAT Readiness Gap Analysis — Scenario-by-Scenario, Post-PR #140

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only.** Prepared
> 2026-07-09 as part of the post-PR #140 master audit. This document
> re-baselines the 15 planned UAT scenarios in
> [`mvp-uat-scenarios.md`](./mvp-uat-scenarios.md) against the **current**
> merged state. (Precision note: that document merged via PR #95 after a
> recorded ChatGPT REVISE→revision cycle, but carries no in-file
> acceptance note or AR row — its standing rests on
> merge-after-control-room-review, and its own Status header still reads
> "Proposed for ChatGPT review." This analysis treats the scenario *set*
> as the planning baseline without upgrading its acceptance status.) (that document's own freshness preamble ends at the
> Task-002-era revision and is preserved unchanged as a historical
> record). **No scenario has been executed; nothing here claims a pass.**
> Open-point IDs (OP-xx) refer to
> [`open-points-closure-register.md`](./open-points-closure-register.md).

## 1. The four cross-cutting UAT blockers

Every scenario is blocked by at least one of these; most by several:

| # | Blocker | Evidence | Closes via |
| --- | --- | --- | --- |
| U-1 | **No interactive Odoo runtime available to sessions.** Test suites run green on Odoo.sh builds, but no session has interactive runtime access for scenario execution | Established environment limitation (`mvp-qa-test-strategy.md` §Runtime limitation strategy; every validation record since Task 001) | Human-operated Odoo.sh branch database session (same channel used for Tasks 003/004/005/006C/010 validation evidence) |
| U-2 | **No live Shopify connection has ever existed (VAL-B2 BLOCKED)** | [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) §Status | OP-06 — human operator executes the closure plan |
| U-3 | **Zero operator UI exists** — no view, menu, action, or wizard anywhere in the addon tree; scenarios are written for a business reviewer, which presumes an operator surface | Addon tree listing 2026-07-09; core manifest data = security + cron only | OP-26 — future UI gates (Groups 1–15) |
| U-4 | **No operator-facing trigger call sites** — merged import backend cannot be invoked by an operator ("no enqueue-trigger call site exists") | [`../07-implementation-plan/task-011-customer-import-gate-readiness.md`](../07-implementation-plan/task-011-customer-import-gate-readiness.md) §2 | OP-28 — Area 6 task |

## 2. Scenario-by-scenario status

"Backend merged" = the underlying models/services exist and are
suite-tested green; it never means the scenario is executable as written.

| # | Scenario | Backend today | Missing before executable |
| --- | --- | --- | --- |
| 1 | Connect store successfully | Merged (Tasks 002/003/005; store/credential/test-connection/lifecycle) | U-1, U-2, U-3 (credentials + readiness screens, Groups 4–5) |
| 2 | Failed credential and recovery | Merged (error classes, `reconnect_needed`, lifecycle rules — DEC-024) | U-1, U-3; U-2 only for the realistic live-failure variant (an invalid-token path was already exercised live in the PR #107 partial validation) |
| 3 | Import simple product | **Merged (Task 010)** — importer + bindings, 220-test green | U-1, U-2, U-3, U-4 |
| 4 | Import variant product | **Merged (Task 010)** — variant binding linked to template binding | U-1, U-2, U-3, U-4 |
| 5 | Import customer and match existing partner | **Not implemented** (Task 011; `shopify_connector_sale` absent) | Task 011 cycle (OP-01/OP-02), then U-1..U-4 |
| 6 | Import same-currency order | Not implemented (Task 012) | OP-14..OP-17 → Task 012 cycle, then U-1..U-4 |
| 7 | Block divergent-currency order | Not implemented (Task 012; posture decided, DEC-020) | Same as 6 |
| 8 | Prevent duplicate order import | Not implemented (Task 012; idempotency substrate exists in core) | Same as 6 |
| 9 | Sync inventory manually | Not implemented (Task 013) | OP-18/OP-19 → Task 013 cycle, then U-1..U-4 |
| 10 | Recover failed inventory sync | Not implemented (Task 013) + error-center UI | Same as 9 + Group 9 screen |
| 11 | Send fulfillment/tracking update | Not implemented (Task 014) | OP-20 → Task 014 cycle, then U-1..U-4 |
| 12 | Disconnect store and preserve history | Merged (Task 005 — disconnect cancels non-terminal jobs, preserves history) | U-1, U-3 |
| 13 | Reconnect store and re-run readiness | Merged (Tasks 004/005 — readiness re-run on reconnect) | U-1, U-2 (readiness against a live shop), U-3 |
| 14 | Operator reviews error center and retries safely | Job/log/retry substrate merged (Task 006C; DEC-009 retry taxonomy) | U-1, U-3 (error-center screen, Group 9), U-4 (something to fail meaningfully requires a domain trigger) |
| 15 | Admin verifies logs without seeing credentials | Merged (redaction + masking, suite-proven incl. ACL-matrix and redaction tests) | U-1, U-3 (log screens, Group 15) |

**Net: 0 of 15 executable today.** 7 of 15 (1, 2, 3, 4, 12, 13, 15) are
backend-complete and wait only on the cross-cutting blockers; 14 is
backend-complete except for a meaningful failure trigger; 5–11 wait on
their domain tasks first.

## 3. Staged path to UAT (consistent with the roadmap)

- **Wave 1** (after: Task 011 merged · Area 6 trigger sites · first UI
  slice Groups 1/2/4/5/9/15 · VAL-B2 passed · an interactive runtime
  session): scenarios 1, 2, 3, 4, 5, 12, 13, 14, 15.
- **Wave 2** (after Tasks 012–014 and their screens): scenarios 6, 7, 8,
  9, 10, 11.
- Evidence rule unchanged: each executed scenario records evidence per its
  own "Evidence to capture" line; a pass may only be marked by the
  reviewer executing the steps as written
  (`mvp-uat-scenarios.md` §How to use).

## 4. Gaps in the UAT planning layer itself (docs-level, non-blocking)

1. The scenarios' freshness preamble predates Tasks 002–010 merging
   (historical; superseded-in-fact by §2 above; wording refresh routed as
   OP-25).
2. No scenario yet covers the **product-import manual-review path**
   (ambiguous/blind match → `blocked_manual_review` → operator resolution)
   even though Task 010 shipped it and the release checklist's
   "manual review flows tested" item requires at least one exercised case
   per shipped domain. **[Recommendation]** add one scenario for this when
   the UAT document is next revised (routed with OP-25; not edited here —
   that file is outside this session's allowed list).
3. No scenario yet covers **ambiguous customer match** resolution — will
   be needed once Task 011 ships, matching criterion 15's posture.
   **[Recommendation]** add alongside item 2.

## 5. Explicit non-authorizations

This analysis authorizes no UAT execution, no UI work, no domain task, and
no change to the UAT scenarios file. It re-baselines status only.
