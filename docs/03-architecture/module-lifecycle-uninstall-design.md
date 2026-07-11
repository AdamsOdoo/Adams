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
> **Final-convergence revision 2026-07-11 per comment `4947866018`
> item 6: LC-1's `non-terminal → cancelled` cancellation no longer
> references "the SEC-1 legal edge" (LC-1 is sequenced before SEC-1 and
> must not depend on code that has not landed). It uses the current
> merged sanctioned mechanism — the same state-write-to-`cancelled` +
> audit-log path the merged `action_disconnect` sweep uses (the merged
> `write()` gate blocks only transitions *to* `running`) — and is
> required to remain forward-compatible with the future SEC-1 matrix,
> which keeps `non-terminal → cancelled` legal (§7, §7.1).**

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
| F | **Core-registered job types (no domain `selection_add` at all)** | Core itself declares every domain job-type selection value, so uninstalling a domain never removes a selection value and never triggers any `ondelete` over jobs | Rejected: core would carry domain vocabulary it must not know (the DEC-008/RA-013 boundary — domain capability lives in domain modules); every future domain/add-on would require a core edit, inverting the sanctioned `selection_add` seam (ARCH §7.1); and uninstalled-domain jobs would keep a live-looking type with no handler — *worse* honesty than B's explicit `historic_domain_job` retyping |

Mapping to the review's six named candidates (comment `4942966937`
item 9), so none is silently dropped: *soft-degraded historical job
types* and *a stable generic job-type code* are *evaluated as one
combined mechanism* — **Option B** — because the former requires the
latter (the retyping target IS the stable core-owned code
`historic_domain_job`); *archive/export before uninstall* = Option C;
*persistent audit/identity state in a stable module* = Option D
(audit state already lives in core — §2.2; the option covers moving
*binding* state there); *controlled migration* = Option E; *another
Odoo-safe design* = Option F.

Checked against `../05-qa/rejected-approaches-log.md`: no RA row
covers uninstall mechanics; B does not reintroduce any rejected
approach (RA-011/012/013 concern capability boundaries, preserved
here — and F is rejected partly *on* RA-013's boundary logic).

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
   reassignment callable `lambda recs: recs._reassign_to_historic_job_type()`
   (cancel-if-non-terminal → reassign to `historic_domain_job`).
   Applies to `customer_import_sync` (merged, changed by LC-1),
   `product_import_sync` (merged, changed by LC-1), and every future
   domain job type. **Because LC-1 is sequenced before Task 012
   (re-review `4945129824` item 7), the callable exists in core before
   any new `job_type` is registered, so packets 012/013/013B/014/015/
   015B/Area-6 adopt it from their first implementation — the one-line
   adoption note is added to each packet in this same revision, not
   deferred to acceptance, and no uncontrolled later retrofit is
   required.**
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

## 7. Task LC-1 — lifecycle enablement (small core+domain task; sequenced before Task 012 so every new-job-type packet adopts the callable from day one)

**Prerequisite:** CORE-R1 merged runtime-green. **Sequencing (revised
re-review `4945129824` item 7):** LC-1 runs **before Task 012** — the
earliest packet that registers a *new* `job_type` — so the
historic-job reassignment callable exists in core before any new
selection value is added. This removes the "uncontrolled later
retrofit" the review flagged: Tasks 012/013/013B/014/015/015B and
Area 6 register their `selection_add` `ondelete` with the callable from
their first implementation, and the two merged job types
(`customer_import_sync`/`product_import_sync`) are converted by LC-1
itself.

**Allowed files (exhaustive):** core `shopify_connector_job.py`
(permanent `historic_domain_job` selection value; `original_job_type`
Char — indexed, readonly, filled for every job at creation from
`job_type`; the public method `_reassign_to_historic_job_type(self)`),
`shopify_connector_job_dispatch.py` (refuse-`historic_domain_job`
guard — no handler), the sale + product importer files (the merged
`customer_import_sync`/`product_import_sync` `selection_add` `ondelete`
one-liners → the callable), a NEW core
`migrations/<version>/post-migrate.py` (one-time `original_job_type`
backfill — additive/idempotent), new core
`tests/test_lifecycle_uninstall.py` + its `tests/__init__.py` import,
the three manifests (version bumps), validation record, AR row,
handoff. **Forbidden:** every other file; the append-only `job_log`
posture; every business-data `ondelete='restrict'` link; any domain
edit beyond the two named importer one-liners; views/ACL/cron;
`adams_base`; CI; `main`; plain `dev`.

**Historic-job conversion mechanics.** `_reassign_to_historic_job_type(self)`
(a) **cancels any non-terminal job** with one audited
`manual_action`-grade log row each, then (b) sets
`job_type='historic_domain_job'` while `original_job_type` (populated
at creation) preserves the real type for querying. **Cancellation
mechanism (corrected per final-convergence comment `4947866018` item 6
— LC-1 must not depend on SEC-1 code sequenced later):** the
`non-terminal → cancelled` write uses the **current merged sanctioned
mechanism** — a state write to `cancelled` plus a `_system_append`
audit row, exactly the path the merged `action_disconnect` cancellation
sweep already uses (the merged `write()` gate blocks only transitions
*to* `running`, never *to* `cancelled`, so no SEC-1 matrix is required
and none exists at LC-1's landing time). LC-1 **requires forward
compatibility** with the future SEC-1 legal-transition matrix, which
keeps `non-terminal → cancelled` as a legal edge (SEC-1 D-SEC1-1) — so
when SEC-1 lands, LC-1's cancellation is already matrix-legal and
needs no change; but LC-1 does **not** call any SEC-1 method or rely on
any SEC-1 code. Terminal jobs are
only retyped — history preserved, never unlinked; logs untouched. Each
domain module's `selection_add` `ondelete` for its job type(s) is
`lambda recs: recs._reassign_to_historic_job_type()`, so uninstalling
a domain removes the selection value **without** unlinking any job or
log. The dispatcher refuses `historic_domain_job` (no handler by
design — terminal rows only).

**`original_job_type` backfill.** New jobs fill it at creation; the
post-migration script backfills pre-existing rows (`= job_type` where
null) at the `-u` upgrade that ships LC-1 — additive and idempotent,
never destructive (it is set-once, not a live compute, so retyping to
`historic_domain_job` never overwrites the preserved original).

**Tests (`test_lifecycle_uninstall.py`):** `original_job_type` filled
at creation and backfilled at upgrade; the reassignment callable
(terminal rows preserved + retyped; non-terminal cancelled with an
audit row; logs untouched); dispatcher refuses the historic type; **the
honest uninstall pair** — uninstall-after-use now **succeeds** with
history preserved (replacing the packaging proposal §6 documented-
failure check) and business data intact; **reinstall → deterministic
re-match** (binding → SKU/barcode/email keys) rebuilds bindings while
degraded history remains queryable by `original_job_type`.

**Rollback.** Revert the single PR — the `ondelete` returns to
`'cascade'` (and with it the uninstall-fails-after-use posture,
documented); the additive `original_job_type` column and the
`historic_domain_job` value may **remain inert/orphaned** (a normal
code revert does **not** drop them — no destructive schema cleanup is
assumed; any cleanup is a separately tested migration); no business or
audit data is removed.

**Definition of done.** Only the allowed files changed; all tests +
Odoo.sh green (verbatim quote, OP-43); the honest-uninstall pair green;
validation record + AR row + handoff updated; draft PR; the LC-1 gate
closes on draft-open.

### 7.1 Locked final implementation prompt (Task LC-1)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS DEC-030 AND THIS DESIGN,
EXPLICITLY OPENS THE LC-1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT. (Prerequisite: CORE-R1 merged runtime-green.)

Implement Task LC-1 — module lifecycle enablement (soft-degraded
historic job types) — exactly per
docs/03-architecture/module-lifecycle-uninstall-design.md §4–§7 and
DEC-030. Branch from the verified current Shopify-connector tip (STOP
on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_core/models/shopify_connector_job.py
    (historic_domain_job selection value; original_job_type Char —
    indexed, readonly, filled at creation from job_type;
    _reassign_to_historic_job_type(self))
  addons/shopify_connector_core/models/shopify_connector_job_dispatch.py
    (refuse historic_domain_job — no handler)
  addons/shopify_connector_sale/models/shopify_connector_customer_importer.py
    (customer_import_sync selection_add ondelete -> the callable — one line)
  addons/shopify_connector_product/models/shopify_connector_product_importer.py
    (product_import_sync selection_add ondelete -> the callable — one line)
  addons/shopify_connector_core/migrations/<version>/post-migrate.py
    (NEW — original_job_type backfill; additive, idempotent)
  addons/shopify_connector_core/tests/test_lifecycle_uninstall.py (NEW)
  addons/shopify_connector_core/tests/__init__.py (one import line)
  addons/shopify_connector_core/__manifest__.py (version bump)
  addons/shopify_connector_sale/__manifest__.py (version bump)
  addons/shopify_connector_product/__manifest__.py (version bump)
  docs/05-qa/task-lc1-validation-results.md (NEW)
  docs/05-qa/architecture-review-log.md (append one AR row)
  docs/01-research/research-handoff.md (top entry)
FORBIDDEN: every other file; the append-only job_log posture; every
business-data ondelete='restrict' link; any domain edit beyond the two
named importer one-liners; views/ACL/cron; adams_base; CI; main; plain dev.

IMPLEMENT exactly: the permanent historic_domain_job job_type value;
original_job_type Char filled for every job at creation + backfilled by
the post-migration script (= job_type where null); the dispatcher
refusing historic_domain_job (no handler); _reassign_to_historic_job_type
which cancels non-terminal jobs (one audited log row each) using the
CURRENT merged sanctioned mechanism — a state write to cancelled + a
_system_append audit row, the same path action_disconnect's cancellation
sweep already uses (the merged write() gate blocks only transitions TO
running, never TO cancelled), so LC-1 depends on NO SEC-1 code (SEC-1 is
sequenced later); require forward compatibility with the future SEC-1
matrix (which keeps non-terminal->cancelled legal) but call no SEC-1
method — then retypes terminal jobs to historic_domain_job (logs
untouched, original_job_type preserved); each named domain
selection_add ondelete set to
lambda recs: recs._reassign_to_historic_job_type(). All §7 tests incl.
the honest uninstall-after-use success pair and the reinstall re-match
determinism.

Runtime: full Odoo.sh run green before merge review (verbatim quote;
OP-43). Stop condition: open the PR as DRAFT titled "Task LC-1: module
lifecycle enablement (historic job types)", update handoff + validation
record + AR row, and stop. The LC-1 gate closes the moment the draft PR
opens. Do not start any other task under any circumstance.
```

## 8. Register impacts on acceptance

DEC-030 carries the decision; packaging proposal §5/§6 and release
plan §2.3 revised this session to cite §5's matrix; architecture §8
revised to the two-layer posture (disable-first, uninstall-supported
via LC-1); UAT scenario 23 extended (downgrade path); the
"soft-degrade is a non-MVP candidate" line in the old §8 is
superseded — LC-1 is in-plan before release.
