# Full canonical campaign — candidate head 7e49a51 (tools/run_connector_suite.sh)

Single run, clean committed worktree. summary.json (verbatim copy:
`connector-suite-summary.json`) records `tested_checkout_sha`:
`7e49a511c408db723e121a903cb169059017211f`, `connector_worktree_dirty: false`,
`odoo_pin_verified: true` (30bde9ff), `browser_evidence: verified`,
`shopify_operations: none`.

| Pass | Result |
| --- | --- |
| Fresh install + standard suite | **pass** — 0 failed / 0 errors of 2508; 37/36 tours |
| Warm same-version update | **pass** — 0 failed / 0 errors of 2508; zero migration scripts (asserted) |
| Genuine migration `50b770a3` (4 scripts) + second update | **pass / pass** — 0/0 of 2508 each |
| Genuine migration `0a15b176` (3 scripts) + second update | **pass / pass** — 0/0 of 2508 each |
| Non-standard tag suite | **1 failed of 62** — the P2-3 flaky RTL row only (below) |
| HOOT suites | verified — setup wizard 30, **dashboard 8**, export diff 11 |

The +11 tests over the prior 2497 are this correction's new regression methods.

## The single non-standard failure is P2-3, not a correction blocker

`TestUiVisualEvidence.test_rtl_renders_mirrored_without_overflow`:

```
AssertionError: [{'surface': 'u2-inventory-workspace', 'width': 1366,
 'doc_scroll_width': 1549, 'inner_width': 1366}] is not false :
 these surfaces overflow horizontally in RTL
```

This is the exact nondeterministic RTL instrument the independent review
recorded as **P2-3** (its §4/§14): same head, opposite outcomes across the
review's paired CI runs (136 push = pass, 137 pull_request = fail) and its own
local run (pass). The prompt directs this session to `record it under existing
P2-3 without changing it` and NOT to rerun the campaign to chase a green row.

The three conditions the prompt sets for treating it as P2-3 all hold here:
- **The same row passes in paired runs at the same head** — pass in the review's
  run 136 and its local run at `53d6a74`; pass in this program's earlier full
  campaigns; fail only intermittently.
- **No touched path owns the surface or the instrument** —
  `test_ui_visual_evidence.py` is NOT in this correction's diff (verified:
  `git diff --name-only 53d6a74 7e49a51` has no match); the failing surface
  `u2-inventory-workspace` belongs to `shopify_connector_inventory` (untouched);
  this correction changed no UI, SCSS or view file.
- **Every blocker-focused test is green** — the HOOT dashboard suite reports
  exactly 8; no projection / reconnect / catch-up / store360 / order-import test
  failed; the focused touched-class run was 0/63; and the counterfactual proves
  the blocker tests are real.

P2-3 stays recorded and untouched (the prompt forbids modifying the flaky
instrument this session). The harness exit code is non-zero solely because of
this one flaky RTL row; every deterministic pass and every blocker-focused test
is green.
