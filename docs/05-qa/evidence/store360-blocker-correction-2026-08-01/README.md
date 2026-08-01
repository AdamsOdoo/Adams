# Evidence — Store 360 consolidated blocker correction (2026-08-01)

Session: Fable, branch `fable/wave-5-completion` (PR #204, draft). Answers the
authoritative independent review
[`#issuecomment-5152212340`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5152212340)
(REVISE — CONSOLIDATED BLOCKER). Closes P0-1, P1-1, P2-1, P2-2.

**Evidence class.** Local CI-grade supporting evidence from the correcting
container (pinned odoo/odoo `30bde9ff758834a4912c5ae55843d3a7dad849f1`,
PostgreSQL 16, Python 3.12, Chromium 141 for the browser passes). **NOT**
Odoo.sh exact-SHA acceptance (DEC-041 D8), **NOT** live-Shopify validation,
**NOT** UAT. Zero Shopify requests, credentials or mutations occurred.

## Files

| File | What it shows |
| --- | --- |
| `counterfactual-oldhead.md` | The new/changed tests run against the pre-correction production code (old head `53d6a74`): **7 failed, 4 errors of 41** — the RPC spoof succeeds, the forged context key authorises a write, and both cancelled descendants advance the freshness stamp. Proves the tests measure the defects, not fixtures. |
| `focused-candidate-head.md` | The touched classes at the candidate head (fix applied): **0 failed, 0 errors of 63** — including the HttpCase RPC boundary, both cancelled-descendant regressions, and the aggregate/security/import-mapping regressions. |
| `connector-suite-summary.json` | The single full-campaign verdict at the tested SHA (`tools/run_connector_suite.sh`): fresh, warm, both genuine migrations + idempotent second updates, and the non-standard pass (HOOT ×3, visual, concurrency, races). Verbatim harness `summary.json`. |
| `suite-result-lines.txt` | Distilled per-pass `odoo.tests.result` lines + HOOT evidence lines from the same campaign. |

## Scope reminder

P2-3 (the nondeterministic RTL evidence instrument) and the recorded P3
wording/guard items were deliberately left unchanged, except where a statement
would otherwise have become false because of this correction (the projection
write-protection wording in the handoff was corrected).
