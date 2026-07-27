# Wave 5 U1 — driven browser evidence, 2026-07-25

Durable copy of the U1 browser/render evidence, committed here because
`ci-artifacts/` is gitignored and the machine that produced it is ephemeral
(DEC-041 **D3**: runtime output must become a durable record before the runtime
environment is torn down).

| Item | Value |
| --- | --- |
| Branch / head | `fable/wave-5-completion` @ `5e50aa1` (evidence run), reported in [`../../ui-u1-validation-results.md`](../../ui-u1-validation-results.md) |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` |
| Odoo | 19.0 at the pinned commit `30bde9ff758834a4912c5ae55843d3a7dad849f1` |
| PostgreSQL / Python | 16.13 / 3.12.3 |
| Browser | Chromium 141.0.7390.37 (Playwright) |
| Result | **34 checks, 0 failed, 13 screenshots** |
| `[Corrected 2026-07-27]` | The **RTL check is withdrawn**. `12-admin-review-rtl.png` is byte-identical to `11-admin-review-workspace.png` (`sha256 fdb4ea74…`), so it is a second LTR capture, not an RTL render, and it was graded PASS. 33 checks stand; 12 of 13 screenshots are distinct. The harness that produced this set is **committed nowhere in this repository**, so none of it can be re-run or audited. |
| Shopify | **none** — no credential, request, mutation or webhook |

## Files

- `u1-browser-evidence.json` — every check, its pass/fail state and its detail.
- `connector-suite-summary.json` — the machine-readable suite summary written by
  `tools/run_connector_suite.sh`: tested checkout SHA, declared source head,
  worktree cleanliness, Odoo pin verification, and the per-pass results.
- `NN-*.png` — the screenshot set. Contents are described in
  [`../../ui-u1-validation-results.md`](../../ui-u1-validation-results.md) §3.1.

## Sanitisation

The database contains **synthetic fixtures only** — `Adams Demo Store`,
`Ada Lovelace`, `Analytical Engine`, `gid://shopify/...` placeholder GIDs. No
real customer data, no Shopify credential, and no access token exists anywhere
in this environment, so no screenshot can contain one. The deliberate
second-company fixture is named "Second Company (must not leak)" precisely so
that its absence from every screenshot is checkable by eye as well as by
assertion.

**Evidence class:** DEC-041 D8 supporting evidence. **Not** Odoo.sh, and not
wave acceptance.
