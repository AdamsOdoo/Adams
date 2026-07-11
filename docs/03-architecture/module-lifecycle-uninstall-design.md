# Module Lifecycle, Downgrade, and Uninstall Design (Lite/Full Safe Removal)

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-11 by the PR #148 revision session, implementing
> review item 9 of ChatGPT's control-room review (PR #148 comment
> `4942966937`). Companion decision record:
> [`../04-decisions/DEC-030-module-lifecycle-uninstall-proposal.md`](../04-decisions/DEC-030-module-lifecycle-uninstall-proposal.md).
> This document resolves the contradiction between the architecture
> ("uninstall fails after jobs exist") and the release plan
> ("uninstall cascade-removes jobs"), evaluates the safe options, and
> proposes the supported lifecycle. Evidence: merged core code
> (job/log FK posture re-verified 2026-07-11) and captures 2026-07-11
> §2 (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).

## 1. The contradiction being resolved (verbatim, both sides)

- Architecture §8 / packaging proposal §5 (this PR, pre-revision):
  uninstalling a domain module that has ever executed a job **fails**
  on the append-only `job_log.job_id` `ondelete='restrict'` FK
  (the `job_type` `selection_add … ondelete='cascade'` tries to
  unlink the domain's jobs; their logs block it) — "disable-only is
  the sole supported removal path once a domain has run."
- Release plan §2.3 (this PR, pre-revision): "Full-module uninstall
  path (business data survives; binding/mapping tables +
  cascade-removed domain jobs documented as lost)".

Both cannot be true; **the architecture text described the merged
mechanics correctly** (verified: `job_log.job_id` is
`ondelete='restrict'`, `shopify_connector_job_log.py` lines 19–25;
the sale module's `selection_add` carries
`ondelete={'customer_import_sync': 'cascade'}`,
`shopify_connector_customer_importer.py` line 478). The release plan
described a cascade that the database would refuse. The release plan
is corrected this session (same PR); this document then answers the
review's deeper point: **"uninstall fails after first use" is not a
completed modular-packaging design** for a product whose stated
requirement is that major capabilities can be added, disabled,
downgraded, and removed safely.

## 2. Facts the design must respect

1. **[Fact — captures §2]** Odoo uninstall deletes the module's
   database records: "Uninstalling apps also deletes their database
   records." Binding/mapping tables owned by a domain module cannot
   survive that module's physical uninstall — this is platform
   semantics, not connector design.
2. **[Fact — merged code]** Jobs and logs live in **core** (they
   survive any domain uninstall as tables); the only coupling is the
   domain-owned `job_type` selection value, whose removal triggers
   Odoo's selection-value `ondelete` policy over the rows using it.
3. **[Fact — merged code]** `job.res_model`/`res_id` are plain
   Char/Integer references (no FK), so binding-table deletion does
   not corrupt job rows; the job's `shopify_target_gid` remains the
   durable external identity.
4. **[Fact — merged design, deliberate]** `job_log` is append-only
   audit history (`ondelete='restrict'`) — deleting audit rows to
   make uninstall work would sacrifice the audit property the product
   sells.
5. Deterministic re-match exists: bindings rebuild from
   `(store, shopify_gid)`/SKU/barcode/email keys on reinstall
   (merged matching behavior); manual matches/overrides are the
   genuinely unrecoverable part unless exported first.

## 3. Options evaluated

| # | Option | Mechanics | Consequences |
| --- | --- | --- | --- |
| A | **Status quo: disable-only, uninstall fails after use** | none | Honest but fails the product requirement; uninstall attempts end in a database error the operator cannot interpret; not a completed design (the review's finding) |
| B | **Soft-degraded historical job types (core-owned)** | Core adds a permanent `job_type` value `historic_domain_job` + a Char field `original_job_type` (always populated at job creation). Domain modules change their `selection_add` `ondelete` from `'cascade'` to a callable that **reassigns** their jobs to `historic_domain_job` (original type preserved in the Char). Uninstall then removes the selection value without unlinking any job; logs untouched | Uninstall succeeds after use; complete audit/job history survives in core, queryable by `original_job_type`; degraded jobs are inert (no handler, terminal states only); small core schema addition + one-line change per domain module |
| C | **Archive/export before uninstall** | A pre-uninstall export (jobs/logs/bindings to attachment/CSV) offered as an operator step | Preserves evidence outside the DB (incl. manual matches) but does not by itself make uninstall succeed; complements B, cannot replace it |
| D | **Move persistent identity (bindings) into a stable module** | Binding tables owned by core (or a never-uninstalled `_data` module) so they survive domain uninstall | Rejected: inverts PD-1's write-risk boundary (removing the export module must provably remove its capability *and* footprint), bloats core with domain schemas (RA-013's boundary logic), and contradicts the accepted per-domain module ownership (DEC-008/AR-019); identity is deterministically re-derivable (§2.5), so the cost buys little |
| E | **Controlled migration scripts at uninstall** | `uninstall_hook` rewriting data before module removal | Odoo supports `uninstall_hook`; but hooks doing bulk data rewrites at uninstall are fragile (run inside the uninstall transaction) and duplicate what B achieves declaratively; kept only as the implementation vehicle **if** the selection-`ondelete` callable proves insufficient at build time (named fallback) |

Checked against `../05-qa/rejected-approaches-log.md`: no RA row
covers uninstall mechanics; B does not reintroduce any rejected
approach (RA-011/012/013 concern capability boundaries, preserved
here).

## 4. Proposed decision (carried by DEC-030) — Recommendation

**Option B + C, layered:**

1. **Core (small change, Task LC-1 §7):** permanent
   `historic_domain_job` job-type value; `original_job_type` Char
   (indexed, readonly, filled for every job at creation from its
   `job_type`); dispatcher refuses `historic_domain_job` (no handler
   by design — terminal rows only; non-terminal jobs of an
   uninstalled domain are cancelled by the reassignment callable with
   one audit log row each).
2. **Domain modules:** `selection_add` `ondelete` becomes the
   reassignment callable (cancel-if-non-terminal → reassign to
   `historic_domain_job`). Applies to `customer_import_sync` (merged,
   changed by LC-1), `product_import_sync` (merged, changed by LC-1),
   and every future domain job type (packets 012/013/014/015/Area-6
   inherit this rule — one-line note added to each packet's next
   revision on acceptance).
3. **Pre-uninstall export (operator step, release-plan §2.3):**
   documented procedure — export bindings/mappings (incl. manual
   matches and overrides) via standard Odoo export before uninstall;
   the uninstall confirmation copy names exactly what is lost.
4. **Supported lifecycle matrix (§5)** becomes the single
   source of truth; packaging proposal §5 and release plan §2.3 are
   revised this session to cite it.

## 5. The supported lifecycle (data-survival rules)

| Transition | Supported path | Survives | Lost (documented) |
| --- | --- | --- | --- |
| Add capability (Lite→Full, or one Full module) | install module(s) | everything | — |
| Disable capability (any) | domain flag off (operational layer — first choice, always) | everything; enqueue blocked immediately | — |
| Downgrade Full→Lite (permanent) | flags off → optional export → uninstall Full module(s) | business data (partners/products/SOs/pickings/stock — restrict FKs); **all** job/log history in core (degraded types, original preserved); store/credential/settings | domain binding & mapping tables, module settings fields, first-push/preview/confirmation records (platform semantics, §2.1); manual matches unless exported |
| Remove one Full module | same as downgrade, per module | same | same, scoped to that module |
| Reinstall after uninstall | install → deterministic re-match (binding → SKU/barcode/email keys) | re-derived bindings; history still present (degraded) | manual matches must be redone (or re-imported from the export — operator procedure) |
| Uninstall Lite modules / core | **unsupported while any domain module is installed** (dependency mechanics); core uninstall = full connector removal, subject to the same export-first guidance; job/log history is lost with core by definition | business data | all connector state (by definition) |
| Upgrade (version bump `-u`) | standard; all schema additions in this plan are additive; LC-1's `original_job_type` backfills from `job_type` at upgrade | everything | — |

Safety invariants (restated, binding): no uninstall path touches
business data (every business FK is `ondelete='restrict'`); no
lifecycle transition bypasses a safety guard; flags remain the
operational layer (DEC-029 two-layer model unchanged).

## 6. What remains an explicit product limitation

Physical uninstall **loses domain binding/mapping tables** — this is
Odoo platform semantics (§2.1), mitigated (export + deterministic
re-match), not eliminated. If ChatGPT judges even that unacceptable,
the only alternative is Option D's core-owned identity store with its
named architectural costs — DEC-030 asks for this call explicitly
rather than inheriting it silently. Commercial consequence stated
plainly: a Full→Lite downgrade is safe and reversible except for
manual-match labor, and audit history is never the price of leaving —
which is a **sellable** lifecycle story, unlike "uninstall fails".

## 7. Task LC-1 — lifecycle enablement (small core+domain task; sequenced with/after Task 013, before UAT wave 3)

**Allowed files:** core `shopify_connector_job.py`
(`historic_domain_job` selection value, `original_job_type` field +
creation fill), `shopify_connector_job_dispatch.py` (refuse-historic
guard), sale + product importer files (the `ondelete` callable
one-liners), new core `tests/test_lifecycle_uninstall.py`, validation
record, AR row, handoff. **Forbidden:** everything else.
**Tests:** original-type fill + backfill at upgrade; reassignment
callable (terminal rows preserved + retyped; non-terminal cancelled
with audit row); dispatcher refuses historic type; **the honest
uninstall test pair** — uninstall-after-use now succeeds with history
preserved (replacing the packaging proposal §6 documented-failure
check), and business data intact; reinstall re-match determinism.
**Rollback:** revert PR; `ondelete` returns to cascade (and with it
the uninstall-fails posture — documented). **Locked prompt:** drafted
at its gate (a two-file mechanical task; packet-level detail above is
complete — flagged as the one packet in this package whose prompt is
deferred to its gate act, since its diff is ~30 lines and fully
specified here).

## 8. Register impacts on acceptance

DEC-030 carries the decision; packaging proposal §5/§6 and release
plan §2.3 revised this session to cite §5's matrix; architecture §8
revised to the two-layer posture (disable-first, uninstall-supported
via LC-1); UAT scenario 23 extended (downgrade path); the
"soft-degrade is a non-MVP candidate" line in the old §8 is
superseded — LC-1 is in-plan before release.
