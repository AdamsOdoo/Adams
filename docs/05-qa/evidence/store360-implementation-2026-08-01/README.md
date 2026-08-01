# Evidence — Store 360 final pre-UAT implementation (2026-08-01)

Session: Fable implementation session, branch `fable/wave-5-completion`
(PR #204, draft). Control-room packet: "FINAL PRE-UAT STORE 360
IMPLEMENTATION AND PR #204 INTEGRATION".

**Evidence class.** Everything here is **local CI supporting evidence**
from the implementing container (pinned odoo/odoo
`30bde9ff758834a4912c5ae55843d3a7dad849f1`, PostgreSQL 16.13, Python
3.12.3, Chromium 141.0.7390.37, `tools/run_connector_suite.sh` with no
pass skipped). It is **NOT** Odoo.sh exact-SHA acceptance evidence
(DEC-041 D8) — the final native Odoo.sh qualification and the controlled
Shopify UAT (R-4 mandatory) remain open gates. Zero Shopify requests,
credentials, or mutations occurred in this session.

## Files

| File | What it proves |
| --- | --- |
| `connector-suite-summary.json` | The complete-suite verdict at the tested SHA: fresh, warm same-version, both genuine version-to-version migrations (the `19.0.2.9.0` sale backfill executes; second update runs zero scripts), and the non-standard pass (concurrency proofs, HOOT ×3 incl. the dashboard suite at exactly 8, visual instrument, race suites). Verbatim copy of the harness `summary.json`. |
| `suite-result-lines.txt` | The distilled per-pass `odoo.tests.result` lines and harness verdict lines from the same run. |
| `counterfactual-a1c5931.md` | The five new test suites fail against the PR base `a1c5931` (3 failed + 33 errors of 38; the projection suite cannot even import) — the capability is new, the tests are not vacuous. |
| `query-counts.md` | Warm-call SQL query counts: legacy dashboard 17; `get_store_360_data` constant 29 (auditor shape) / 48 (full-access shape) across store filter and period. |

## Tested SHA vs pushed head

The suite ran at the **last code-bearing commit**; the pushed head adds
only documentation/evidence files on top (this directory,
`research-handoff.md`). The exact SHAs, the commit chain, and the changed
path inventory are recorded in the DEC-041 D2 push-completion comment on
PR #204.
