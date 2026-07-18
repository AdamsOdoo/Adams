# Locked Sol Wave 3 Stage 0 Implementation Prompt — DEC-031 Layer 2 Core Substrate

> **ISSUED-NOT-EXECUTED: NO**
> **LOCKED: YES**
> **NOT USABLE UNTIL CONTROL-ROOM ACCEPTANCE**
>
> This is a draft, ready-to-copy prompt template for the Wave 3 Stage 0
> implementation session, prepared during the Wave 3 Gate A session
> (PR #177, 2026-07-18) that produced
> [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) and the
> [Stage 0 packet](../07-implementation-plan/wave-3-stage-0-layer-2-packet.md).
> **It has not been issued to any Sol session. It must not be issued until
> all of the following are true:**
>
> 1. DEC-036 is **ACCEPTED** (or **ACCEPTED WITH CORRECTIONS**, with the
>    corrections folded back into this prompt and the Stage 0 packet) by
>    the product owner + Claude control room — not by the session that
>    authored this prompt.
> 2. Every item the Stage 0 packet's §17 marks as a hard stop (job_id field
>    type + C2 cursor placement; open-transaction-vs-network-call proof;
>    disconnect-quiescence/sweep-timeout interaction; `mutation_domain`
>    field ownership; N=3 cap persistence scope; AST-tooling-maturity
>    contradiction; the three-layer runtime/concurrency/crash-injection
>    proof plan; and the two named out-of-scope document corrections) is
>    either resolved on the record or explicitly risk-accepted by the
>    control room.
> 3. The exact base SHA below is re-verified live immediately before
>    issuance.
> 4. "Session C"'s separately-tracked code/architecture audit (referenced
>    in the control-room ruling on PR #177 comment
>    [`5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989))
>    has been reconciled against this package by the control room.
>
> **Do not run this prompt in the same session that authored it. Do not run
> it now, regardless of how complete it reads — completeness of the prompt
> text is not the same as control-room acceptance of DEC-036.**

---

## Paste-ready prompt (draft — not issued)

```text
REPOSITORY: AdamsOdoo/Adams

EXACT STARTING SHA (mvp/program-integration): <EXACT_SHA_AT_ISSUANCE>
(fill this placeholder with the exact live mvp/program-integration tip at
the moment this prompt is actually handed to a Sol session — verify it live
from GitHub immediately before issuance; do not reuse any SHA recorded in
this document's own authoring session, and do not let any repository
commit occur between that verification and issuance)

WORKING BRANCH TO CREATE: sol/wave-3-stage-0-layer2

PULL REQUEST: open one early DRAFT pull request from
sol/wave-3-stage-0-layer2 into mvp/program-integration, titled
"Wave 3 Stage 0: DEC-031 Layer 2 core substrate".

ROLE: You are GPT-5.6 Sol, the primary autonomous research/implementation
worker for this MVP program (DEC-032). Claude is the control room and the
only party authorized to merge your wave PR. You do not merge your own PR.

======================================================================
MANDATORY PRE-EDIT CLAUSE (verbatim — do not paraphrase or skip)
======================================================================

"Before editing, perform a complete code, dependency, caller, test,
source-guard, migration, security and runtime-access preflight for the
entire wave. Resolve all implementation-level issues before coding. If a
genuine product decision is required, report all known blockers together in
one consolidated hard stop. Do not stop repeatedly for isolated issues that
could have been discovered during the initial audit."

Additionally, and specific to this task: before writing any code, confirm
that every DEC-036 hard-stop item (job_id field type + C2 cursor placement;
open-transaction proof requirement; disconnect-quiescence interaction
choice; mutation_domain ownership choice; N=3 cap persistence scope; AST
tooling-maturity finding) has an explicit, control-room-recorded resolution
you can cite by decision ID and date. If any is still open, stop
immediately and report it as a single consolidated hard stop — do not infer
a resolution, do not proceed on a provisional assumption for a BLOCKING
item.

======================================================================
OBJECTIVE
======================================================================

Implement Wave 3 Stage 0 exactly as specified in
docs/07-implementation-plan/wave-3-stage-0-layer-2-packet.md, itself cut
from docs/04-decisions/DEC-036-wave-3-layer-2-gate.md. This is the
durable, core-owned, domain-agnostic mutation-safety substrate: the
mutation-attempt model, the stale-owner sweep, the reconciliation-strategy
registry, and the C1/C2/NET/C3 transaction-boundary protocol.

======================================================================
NON-GOALS (verbatim from the Stage 0 packet §2 — do not exceed)
======================================================================

- No inventory-domain implementation of any kind (no
  shopify_connector_inventory addon, no location mapping, no
  inventorySetQuantities call site).
- No Shopify mutation of any kind, ever, in this wave.
- No fulfillment or product-export scaffolding.
- No UI/screen work.
- No change to the Layer 1 replay-policy registry's existing behavior
  (extended via the existing seam only, never modified).
- No change to any currently-shipped read-only handler's observable
  behavior.

======================================================================
ALLOWED FILES (exhaustive — copy verbatim from the Stage 0 packet §3;
re-verify against the then-current packet text before use, since the
packet may be revised between this prompt's authoring and its issuance)
======================================================================

addons/shopify_connector_core/models/shopify_connector_job.py (additive
fields only)
addons/shopify_connector_core/models/shopify_connector_job_dispatch.py
addons/shopify_connector_core/models/shopify_connector_mutation_attempt.py
(new)
addons/shopify_connector_core/models/shopify_connector_stale_owner_sweep.py
(new, or folded into job_dispatch.py — disclose the choice)
addons/shopify_connector_core/security/ir.model.access.csv
addons/shopify_connector_core/security/shopify_connector_security.xml (no
new group expected)
addons/shopify_connector_core/data/shopify_connector_stale_owner_sweep_cron.xml
(new)
addons/shopify_connector_core/models/__init__.py
addons/shopify_connector_core/__manifest__.py
addons/shopify_connector_core/tests/** (new test files per the packet §14
exact required set)
docs/05-qa/task-stage0-layer2-validation-results.md (new)

======================================================================
FORBIDDEN FILES
======================================================================

Everything outside the allowed list above. Specifically:
shopify_connector_product/**, shopify_connector_sale/**, adams_base/**;
any shopify_connector_inventory/** file (must not be created);
shopify_connector_api_client.py, shopify_connector_store.py,
shopify_connector_store_settings.py, shopify_connector_binding_mixin.py,
shopify_connector_job_actions.py, shopify_connector_call_lease.py,
shopify_connector_job_enqueue.py (read-only reference, not modified); any
Layer 1 replay-policy-registry behavior change; CI/workflow files;
protected references (main, Shopify-connector,
checkpoint/core-r2-readonly-uat-2026-07-15, and every prior wave
checkpoint).

======================================================================
IMPLEMENTATION SEQUENCE
======================================================================

1. Preflight (mandatory pre-edit clause above).
2. New model: shopify.connector.mutation.attempt (packet §5 schema —
   job_id field type and mutation_domain ownership must already be
   resolved per the control-room record you cited in preflight; do not
   choose them yourself).
3. Job-row additive fields (packet §5 job-row list) + PROTECTED_JOB_FIELDS.
4. ACL rows for mutation.attempt (packet §12 — four roles, all
   perm_write=0/perm_create=0/perm_unlink=0).
5. C1/C2/NET/C3 transaction protocol in job_dispatch.py, scoped to
   mutation job types only (packet §7) — respecting the Odoo 19
   REPEATABLE READ isolation fact and the "nothing on the main cursor
   between C2 and NET" discipline (packet §7, DEC-036 D21/D22).
6. Reconciliation-strategy registry (_get_reconciliation_strategies(),
   packet §8) + its runtime fail-closed gate + its combined
   completeness test with _get_replay_policies().
7. Widened _recover_after_concurrency_conflict claimability branch
   (DEC-036 D25) — additive only, existing exclusion behavior for
   non-matching running rows must remain unchanged.
8. Stale-owner sweep cron (packet §10) — respecting the
   disconnect-quiescence interaction resolution you cited in preflight.
9. Administrator-only resolution-override action (packet §9/DEC-036 D11).
10. AST/source guards (packet §19) — closed sudo-site inventory, repo-wide
    network-call-site guard, allowlist-only snapshot-construction guard,
    registry-completeness guard.
11. Full test suite (packet §19-22).
12. Validation record + this prompt's own execution log.

======================================================================
COMMIT BOUNDARIES
======================================================================

One reviewable commit per implementation-sequence step above is the
default; smaller or larger groupings are acceptable if each commit remains
independently reviewable and does not mix schema changes with test-only
changes. Do not squash the whole wave into one commit. Do not amend or
force-push.

======================================================================
TESTS (exhaustive — see Stage 0 packet §19-22 for full detail)
======================================================================

Static: closed sudo-site AST test; repo-wide network-call-site AST guard;
allowlist-construction AST guard; combined registry-completeness test;
UniqueIndex enforcement test.

Unit: full 11-step state-machine transition test; fingerprint
normalization stability; idempotency-key reuse/non-reuse; THROTTLED
classification; store-identity-mismatch routing; negative-migration test;
rollback two-mechanism test.

Genuine PostgreSQL concurrency (real independent connections, not
same-process simulation): one test per crash-window recovery-table row;
widened claimability-gate test; concurrent-increment race test for the
inconclusive-reconciliation cap; UniqueIndex under genuine concurrent
insert; main-cursor write-isolation invariant test; pg_stat_activity-based
open-transaction test.

Genuine OS-process-level crash injection (real SIGKILL or equivalent, not
a same-process exception) at every commit-point boundary listed in the
Stage 0 packet §22. If infeasible on the target Odoo.sh environment: STOP,
do not substitute simulation, report as a single consolidated hard stop
per Wave-3-DoR hard-stop 6/10 — do not silently ship with only simulated
proof.

======================================================================
RUNTIME REQUIREMENTS
======================================================================

Odoo.sh fresh install + focused-class + full regression + residue audit,
Wave 1/Wave 2 standard. Multi-worker proof specifically required: Worker B
must not execute a handler Worker A durably owns; sweep-driven
reconciliation observed on a real killed worker. Zero Shopify mutation at
any point in this wave's runtime evidence — this wave's proof is entirely
about the substrate's own crash-safety, not about any real mutation
outcome (there is no mutation domain registered yet).

======================================================================
ROLLBACK NOTES
======================================================================

Pre-ship (this wave, before merge): clean additive-schema revert, proven
by the negative-migration test. Do not claim post-ship rollback semantics
in this wave's own documentation — no mutation domain exists yet to have
"shipped" a mutation.

======================================================================
DEFINITION OF DONE
======================================================================

Stage 0 packet §18, verbatim: all non-blocking DEC-036 decisions
implemented exactly as specified; every hard-stop item resolved/risk-accepted
on the record before the corresponding code path was written (not
after); static/unit/genuine-concurrency/genuine-crash-injection tests all
green on real Odoo.sh multi-worker infrastructure; residue/leak audit
clean; validation record complete; program-state/acceptance-matrix/handoff
updated; zero inventory-domain code anywhere in the repository; zero
Shopify mutation ever issued during this wave's development or testing.

======================================================================
STOP CONDITIONS (hard stops — consolidate and report, do not proceed
past any of these)
======================================================================

1. Any DEC-036 BLOCKING item you cannot cite a control-room resolution
   for, at any point during implementation (not just preflight) — if
   implementation reveals a BLOCKING item was resolved incorrectly or
   incompletely, stop and re-report, do not patch around it.
2. Genuine OS-process-level crash injection proves infeasible on the
   target environment.
3. Any code path is found that would issue, or could be argued to issue,
   a real Shopify mutation — stop immediately, this wave must never
   mutate Shopify.
4. Any attempted change to a forbidden file.
5. Any attempted change to a protected reference.
6. Every Wave-3-DoR program-level hard stop (1-10) applies verbatim.
```

---

## Issuance checklist (for the control-room session that eventually issues this)

- [ ] DEC-036 status is ACCEPTED or ACCEPTED WITH CORRECTIONS (not
      PROPOSED).
- [ ] Every Stage 0 packet §17 hard-stop item has a cited, dated
      control-room resolution.
- [ ] "Session C" reconciliation (PR #177 comment 5012854989 point 8) is
      recorded complete.
- [ ] `<EXACT_SHA_AT_ISSUANCE>` is replaced with a live-verified
      `mvp/program-integration` tip at the moment of issuance, not any SHA
      recorded during this prompt's authoring.
- [ ] This prompt's file-list/sequence still matches the then-current
      Stage 0 packet text (re-diff before use — the packet may have been
      revised since this prompt was drafted).
- [ ] The issuing session is not the session that authored or corrected
      this prompt.
