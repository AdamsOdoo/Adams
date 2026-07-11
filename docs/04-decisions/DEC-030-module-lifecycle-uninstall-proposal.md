# DEC-030 — Module Lifecycle: Safe Disable, Downgrade, and Uninstall (Review Item 9)

## Status

**Proposed for ChatGPT review. NOT accepted.** Drafted 2026-07-11 by
the PR #148 revision session. Full analysis, options table,
data-survival matrix, and the LC-1 task spec:
[`../03-architecture/module-lifecycle-uninstall-design.md`](../03-architecture/module-lifecycle-uninstall-design.md).
Nothing below is binding until ChatGPT explicitly accepts this
record; no implementation is authorized by it (Task LC-1 has its own
future gate).

## Question being decided

The architecture said uninstall fails after a domain has run (correct
against the merged FK posture); the release plan said uninstall
cascade-removes jobs (mechanically false). Beyond fixing the
contradiction: what is the **supported** lifecycle for adding,
disabling, downgrading, and removing connector capabilities, given
that (a) Odoo uninstall deletes a module's records (official 19.0
docs, captures 2026-07-11 §2), (b) job/log history is core-owned
append-only audit data, and (c) the product requirement is safe
capability removal?

## Proposed decision (Recommendation — becomes binding only on acceptance)

1. **Disable-first stands:** the per-store domain flags remain the
   first-choice removal path (everything survives; DEC-029 two-layer
   model unchanged).
2. **Uninstall becomes supported** via soft-degraded historical job
   types (design doc §4 Option B): core gains the permanent
   `historic_domain_job` type + `original_job_type` preservation
   field; domain `selection_add` `ondelete` becomes a reassignment
   callable (cancel non-terminal with audit row, retype terminal).
   Audit/job history is **never** the price of uninstalling.
3. **Pre-uninstall export** is the documented operator step covering
   the one genuinely platform-lost dataset (domain binding/mapping
   tables incl. manual matches); reinstall re-derives bindings from
   deterministic keys.
4. The **data-survival matrix** (design doc §5) is the single source
   of truth; packaging proposal §5/§6, architecture §8, and release
   plan §2.3 cite it (revised in the same PR).
5. Implementation lands as **Task LC-1** (design doc §7), sequenced
   **before Task 012** (re-review `4945129824` item 7 — so every
   new-job-type packet adopts the `_reassign_to_historic_job_type`
   callable from its first implementation, no uncontrolled later
   retrofit), with its **full locked prompt now in design doc §7.1** —
   its own gate act.
6. If ChatGPT instead judges binding-table loss on uninstall
   unacceptable, the named alternative is the rejected-here Option D
   (core-owned identity store) with its stated architectural costs —
   an explicit call, not a silent inheritance.

## Alternatives considered

Design doc §3: A status-quo (fails the product requirement — the
review's finding), C export-only (doesn't make uninstall succeed),
D core-owned bindings (inverts PD-1's write-risk boundary, bloats
core), E uninstall-hook migrations (fragile; kept as named build-time
fallback for B's mechanics).

## What becomes binding if accepted

Points 1–5; the design doc §5 matrix becomes the operative lifecycle
contract; the packaging/release/architecture revisions of this PR
become the standing text; LC-1 enters the critical path (master plan
§2). The old "uninstall fails after first use" posture and the
packaging proposal's documented-failure test are superseded.

## What remains unauthorized regardless of acceptance

Task LC-1's code (own gate); any add-on module lifecycle (own passes);
any change to the append-only log posture or business-data
`ondelete='restrict'` links (explicitly out of scope forever here).
