# DEC-034 — Wave 1 Packet Dependency Reconciliation (Security, Lifecycle, and Job-Action Ordering)

- **Status:** Proposed for control-room review. Not binding until the
  "Acceptance effect" section below is completed and the accepting
  control-room review is recorded.
- **Date:** 2026-07-15.
- **Decision owner:** Claude control room under DEC-032/CLAUDE.md §13,
  MVP Program Control-Room addendum.
- **Scope:** Wave 1 internal packet sequencing and packet-ownership
  correction only. This is **not** MVP scope expansion — no addon code
  is authorized by this record, no new capability is added to the MVP
  contract, and no wave boundary in `mvp-completion-program.md` §4
  moves.
- **Related:** DEC-030 (module lifecycle/uninstall, Accepted), DEC-033
  (Wave 0 reconciliation, Accepted), issue #167 (master program issue),
  issue #167 comment `4980808811` (Sol's Wave 1 hard-stop),
  `task-sec1-security-hardening-packet.md`,
  `area-6-sync-triggers-implementation-packet.md`,
  `module-lifecycle-uninstall-design.md`,
  `task-job-actions-generic-core-packet.md` (new, this record).

## Context

Sol was launched to open Wave 1 (CORE-R1 → SEC-1 → LC-1 → SRR-03
closure, per DEC-033's accepted recommended internal sub-stage order
and `mvp-completion-program.md` §4 as it stood before this record) and
correctly stopped before creating any branch, PR, code, or test —
per the launch instruction "if a packet conflicts with accepted
DEC-033 … or current code, stop and report the exact conflict" — and
filed the exact conflict as issue #167 comment `4980808811`.

## Exact conflict (independently re-verified against primary sources,
not accepted on Sol's summary alone)

**1. SEC-1 depends on unauthorized Wave 2 scope.**
`task-sec1-security-hardening-packet.md` header and §7 gate criterion 1
("Area 6 merged runtime-green (sanctioned services exist to inherit the
guard)") and §9's locked-prompt prerequisite both require Area 6 merged
before SEC-1 may implement, because D-SEC1-3 names
`action_manual_retry()`/`action_cancel()` — methods D-A6-5 in
`area-6-sync-triggers-implementation-packet.md` assigns to Area 6 — as
SEC-1's own sanctioned mutation doors. Area 6 (scan jobs, crons, domain
manual-sync services, order-scan) is Wave 2+ scope, explicitly gated on
Task 012 merging (`mvp-completion-program.md` §4 Wave 2, pre-this-record
text: *"Area 6's own gate criterion requires 'Task 012 merged
runtime-green'"*). Absorbing Area 6 into Wave 1 to satisfy SEC-1 would
violate Wave 1 scope; leaving SEC-1 unable to implement its own D-SEC1-3
sanctioned-methods list violates that packet's own binding decision
closure. **Independently confirmed:** `git grep` across `addons/**/*.py`
at the live baseline (`mvp/program-integration` @
`a1e83a09678537ac6db8959f5ed0c76a5bcc0d1c`) for `action_manual_retry`,
`action_cancel`, and `action_resolve_manual_review` returns zero
matches — none exists in the current tree.

**2. SEC-1 names a nonexistent Wave 2 file.** §5's allowed-files list
(lines 293–295 of the pre-reconciliation packet) names
`addons/shopify_connector_sale/models/shopify_connector_order_binding.py`
for a `_odoo_binding_field_name()` one-liner, and D-SEC1-4's enumeration
table describes the order binding as one of "the four models that exist
at the SEC-1 gate." **Independently confirmed:** `git ls-tree -r` at the
live baseline contains no `order_binding`/`order-binding` file anywhere
— Task 012 (the packet that would create it) is unstarted. Only three
binding models exist at the Wave 1 baseline: product-template binding,
product-variant binding, and customer binding.

**3. LC-1's accepted design and the Wave-0-recommended stage order
disagree on sequencing.** `module-lifecycle-uninstall-design.md`'s
2026-07-11 final-convergence revision (top-of-file note, §7 "Historic-job
conversion mechanics") explicitly states LC-1 is "sequenced before
SEC-1" and its non-terminal-job cancellation write uses "the CURRENT
merged sanctioned mechanism" specifically **because** "LC-1 must not
depend on code that has not landed" if SEC-1 lands first. DEC-030 (this
design's own accepted decision record) carries the same LC-1-before-SEC-1
assumption via its cross-reference to design-doc §7. But DEC-033's
accepted Wave 0 recommendation (issue #167 comment `4980646566`) and the
pre-reconciliation `mvp-completion-program.md` §4 Wave 1 internal
sub-stage list both order SEC-1 **before** LC-1. **Independently
confirmed as a real conflict, not merely a documentation gap:** once
Task SEC-1's D-SEC1-2 protected-field guard lands (state is one of the
named protected fields, writable only under `self.env.su`), a
non-su `write({'state': 'cancelled'})` — the exact mechanism LC-1's
`_reassign_to_historic_job_type()` uses — would raise `AccessError`. LC-1
implemented exactly as locked cannot land after SEC-1 without either
reordering the two tasks or rewriting LC-1's cancellation path to a
not-yet-designed SEC-1-sanctioned/su path (which its own design doc
explicitly refuses to depend on).

Checked against `docs/05-qa/rejected-approaches-log.md` (CLAUDE.md
§10): no RA row concerns Wave 1 internal sequencing, job-action
ownership, or the SEC-1/LC-1/Area-6 boundary — this reconciliation
revisits no rejected approach.

## Options considered

1. **Absorb all of Area 6 into Wave 1** so SEC-1's "Area 6 merged"
   prerequisite is literally satisfiable. Rejected: pulls in scan jobs,
   crons, domain manual-sync services, and order-scan (which itself
   requires Task 012, unstarted) — a large, explicit Wave-2-owned scope
   expansion, violating `mvp-completion-program.md` §4 Wave 1's
   "Forbidden" list and the product owner's explicit instruction not to
   absorb Area 6 or Task 012 wholesale.
2. **Drop SEC-1's dependency on `action_manual_retry`/`action_cancel`
   entirely** (implement D-SEC1-1/2/4/5/6/7 without D-SEC1-3's job-action
   doors). Rejected: D-SEC1-3 is a binding decision closure — the
   sanctioned-methods list is what makes the job-model write guard a
   complete mediation layer, not a partial one; silently narrowing it
   would leave `action_resolve_manual_review` (SEC-1's own new method)
   as the only sanctioned retry-adjacent door, contradicting the
   product's already-accepted retry/recovery requirements (MVP item 16).
3. **Create the Task 012 order-binding file now, minimally, just to
   satisfy SEC-1's allowlist.** Rejected: this is starting Wave 2 code
   inside Wave 1, exactly what the product owner's instruction and
   `mvp-completion-program.md` §4's wave boundaries forbid. A Wave-1-only
   packet must not require a Wave-2-only file to exist.
4. **Reorder Wave 1 to SEC-1 before LC-1 and rewrite LC-1's
   cancellation path to a hypothetical SEC-1-sanctioned method.**
   Rejected: this redesigns an already-`Accepted` decision (DEC-030) to
   fit a *recommended* (not binding-on-its-own-mechanics) sub-stage
   order, inverts the dependency the design doc explicitly built against,
   and would require designing a SEC-1 sanctioned cancellation path
   before SEC-1 itself is implemented — sequencing that cannot be
   verified runtime-green at design time.
5. **Extract D-A6-5 (`action_manual_retry`/`action_cancel`) into its own
   generic, core-owned Wave 1 prerequisite stage; keep LC-1 before SEC-1;
   scope SEC-1 to the models that exist at the Wave 1 baseline; add a
   forward-looking binding-extension contract for future binding models.**
   **Selected** (option 5) — this is the product-owner-directed
   resolution, and it is the only option that (a) does not absorb Area
   6's remaining scan/cron/domain scope, (b) does not require any Task
   012 file, (c) does not redesign DEC-030's accepted lifecycle
   mechanics, and (d) leaves every future binding model (Task 012's order
   binding, Task 013's location/inventory bindings, Task 015B's media
   binding) with an explicit, unambiguous contract for adopting SEC-1's
   protections when they are built. Supporting evidence: Area 6's own
   packet text already flagged D-A6-5 as belonging to core ("job-control
   services are generic and belong to core... an explicitly-named
   additive core exception... Flagged for ChatGPT") — this record
   resolves that flag rather than inventing a new design; and Task 012's
   own packet (§9–14 cross-references, line 1342–1343) already commits
   to declaring `_odoo_binding_field_name()` on its future order binding
   when that model is created — this record formalizes that pre-existing
   commitment as a binding contract rather than a one-off note.

## Selected solution

### Corrected Wave 1 internal stage order

```
Stage 1 — CORE-R1  (capability-aware readiness correction)
Stage 2 — LC-1     (module lifecycle / soft-degraded historic job types)
Stage 3 — JOB-ACTIONS (generic core job-control actions: action_manual_retry, action_cancel)
Stage 4 — SEC-1    (current-surface security hardening)
Stage 5 — SRR-03 closure and final runtime proof
```

This replaces the pre-reconciliation order (CORE-R1 → SEC-1 → LC-1 →
SRR-03 closure) recorded in DEC-033's acceptance note and the
pre-reconciliation `mvp-completion-program.md` §4. CORE-R1 remains
first (no dependency on any of the other three; already-established
prerequisite for every later stage's dev-store validation). SRR-03
closure remains last (unchanged position and unchanged independence
from this reordering — see "SRR-03 closure position" below).

### Transfer of generic job-control ownership

`action_manual_retry()` and `action_cancel()` (D-A6-5, verbatim
mechanics preserved) are extracted from `area-6-sync-triggers-implementation-packet.md`
into a new, independently gated Wave 1 packet:
[`task-job-actions-generic-core-packet.md`](../07-implementation-plan/task-job-actions-generic-core-packet.md)
(Task JOB-ACTIONS). It implements the two methods as a pure additive
`_inherit` extension of `shopify.connector.job`
(`shopify_connector_job_actions.py`, NEW file — no edit to
`shopify_connector_job.py` itself), using the **current** merged
write-gate mechanism (no su-elevation — none exists yet at this stage's
landing time), forward-compatible with SEC-1's already-specified
D-SEC1-1 matrix edges and D-SEC1-3 sanctioned-doors list. Area 6's
remaining scope (scan jobs, crons, domain manual-sync services, order
scan) is **not** touched or authorized by this record and remains
Wave 2+, now explicitly depending on Task JOB-ACTIONS's already-merged
services instead of re-implementing them (`area-6-sync-triggers-implementation-packet.md`
§5 revision, this record).

### SEC-1 current-surface boundary

SEC-1 (Stage 4) is rescoped to harden exactly the models and surfaces
that exist at the Wave 1 baseline:

- `shopify.connector.job` (D-SEC1-1/2/3, now naming Task JOB-ACTIONS's
  two methods as already-implemented sanctioned doors, plus the new
  `action_resolve_manual_review`);
- `shopify.connector.product.template.binding`;
- `shopify.connector.product.variant.binding`;
- `shopify.connector.customer.binding` (plus its PII snapshot fields,
  D-SEC1-5/6);
- current importers (`shopify_connector_customer_importer.py`,
  `shopify_connector_product_importer.py`) and other sanctioned internal
  core writers named in SEC-1's own §5 (dispatcher, enqueue, readiness
  check, store).

The nonexistent `shopify_connector_order_binding.py` line is removed
from SEC-1's Wave 1 allowlist (conflict 2). D-SEC1-4's enumeration table
is corrected to mark the order/location/inventory/media bindings as
**future**, not "existing at this gate."

### Future binding-extension contract (binding, applies to every future
binding model)

1. Task 012 must declare `_odoo_binding_field_name()` (returning
   `sale_order_id`) on `shopify.connector.order.binding` when that model
   is created, in Task 012's own packet/implementation — not deferred,
   not silently omitted. Task 012's own packet already commits to this
   (line 1342–1343, "SEC-1 override seam") — this contract makes that
   commitment binding rather than a one-off cross-reference.
2. Task 013 and every later binding model (`shopify.connector.location.mapping`,
   `shopify.connector.inventory.level.binding`, `shopify.connector.product.media.binding`,
   and any future binding) must declare its own `_odoo_binding_field_name()`
   seam (or explicitly inherit the mixin's `False` default where identity
   is composite/derived — SEC-1's D-SEC1-4 enumeration table already
   states which) in that model's own implementation packet, at the time
   the model is created — never as an uncontrolled later retrofit.
3. The core mixin's seam **remains fail-closed/default-`False`** where
   applicable: `_odoo_binding_field_name()` defaults to `False` on the
   abstract mixin (`action_override_binding` refuses with `UserError`
   for any binding that has not declared a truthy override), so a future
   binding model that forgets to declare the seam is inert-safe, not
   silently exploitable.
4. **No future binding may bypass SEC-1's protected-identity contract.**
   Any new binding model inheriting `shopify.connector.binding.mixin`
   inherits D-SEC1-4's identity-field su-protection automatically (the
   guard lives on the mixin, per SEC-1's own §4 "Why this is one
   cross-cutting task" rationale) — a future domain packet may not
   introduce its own parallel, unprotected identity-mutation path.

### LC-1/SEC-1 compatibility

LC-1 remains **before** SEC-1 (Stage 2, before Stage 4) — matching its
own accepted design (`module-lifecycle-uninstall-design.md` §7,
DEC-030) exactly as written, with **no change to LC-1's lifecycle
outcomes, mechanics, or locked prompt**. SEC-1's own allowed-files list
and D-SEC1-2 protected-field-write inventory are corrected (this
record; `task-sec1-security-hardening-packet.md` §5 revision) to
**explicitly recognize `_reassign_to_historic_job_type()` as a
sanctioned internal protected-field writer** once SEC-1's guards land —
the same "named elevation site" treatment SEC-1 already gives the
dispatcher/enqueue/readiness/store write sites. This closes the
forward-compatibility loop the design doc's final-convergence revision
already anticipated ("LC-1 **requires forward compatibility** with the
future SEC-1 legal-transition matrix... so when SEC-1 lands, LC-1's
cancellation is already matrix-legal and needs no change") — SEC-1 is
the side that must recognize LC-1, not the reverse, and this record
makes that recognition an explicit, itemized part of SEC-1's own §5.

### SRR-03 closure position

**Unchanged.** SRR-03 closure remains Stage 5, the final Wave 1 stage,
and remains **OPEN** until genuine runtime evidence is accepted — this
reconciliation is a sequencing/ownership correction among Stages 1–4;
it does not touch, weaken, or advance SRR-03's own closure criteria
(`sync-engine-risk-register.md` SRR-03 row,
`task-core-r2-disconnect-quiescence-packet.md`), and remains explicitly
independent of DEC-031 Layer 2 (a separate, later, Wave-3-triggered
gate — DEC-033 §2, unchanged by this record).

### Scope exclusions (restated, binding)

This record does **not** authorize: any Area 6 scan-job, cron, domain
manual-sync-service, or order-scan implementation; any Task 012
model, file, or code; any change to DEC-030's accepted lifecycle
outcomes; any weakening of the append-only `job_log` posture or any
business-data `ondelete='restrict'` link; any Wave 2+ start of any
kind. It authorizes only: the corrected Wave 1 stage order, the new
Task JOB-ACTIONS packet, and the documentation corrections to SEC-1,
Area 6 (documentation only — no Area-6 code), the lifecycle design doc,
DEC-030 (a reconciliation note only), `mvp-completion-program.md`,
`mvp-program-state.md`, `mvp-acceptance-matrix.md`, and Task 012's
packet (a cross-reference note only).

### Rollback

Revert the reconciliation PR: `mvp/program-integration` returns to its
pre-reconciliation state (the pre-reconciliation Wave 1 order, packet
text, and this record itself are all removed). No addon code, schema,
or protected reference is touched by this record in either direction —
rollback is a pure documentation revert with no data or runtime
consequence. `task-job-actions-generic-core-packet.md` (a new,
not-yet-implemented packet) is removed along with everything else.

### Consequences for Area 6 and Task 012

**Area 6:** loses ownership of `action_manual_retry`/`action_cancel`
(D-A6-5) to Task JOB-ACTIONS; retains D-A6-2 (scan jobs), D-A6-3
(crons), D-A6-4 (manual domain-sync services), D-A6-6 (progress
counters); its own future implementation depends on Task JOB-ACTIONS's
already-merged services rather than re-implementing them; remains
unauthorized, Wave 2+, gated on Task 012 merging exactly as before.

**Task 012:** unaffected in scope or gate — remains unstarted, Wave 2,
gated on Wave 1's SRR-03 closure and LC-1 runtime proof (unchanged from
DEC-033). Its packet gains one clarifying cross-reference to this
record's binding-extension contract (§9–14 cross-references section);
no change to its D-012-1..12 decisions, allowed-files list, or locked
prompt preconditions.

## Consequences

- Wave 1 now has a coherent, implementation-ready internal order with
  no forward reference to unauthorized scope.
- SEC-1's allowlist and enumeration table match the live baseline
  exactly — no phantom file, no phantom prerequisite.
- LC-1 ships exactly as already accepted (DEC-030), with SEC-1 doing
  the work of recognizing it, not the reverse.
- Every future binding model has an explicit, checkable obligation
  (§"Future binding-extension contract") instead of an implicit
  expectation.
- Wave 1's macro-wave gate (one Claude control-room review, one merge
  into `mvp/program-integration`) is unchanged — this record adds one
  more reviewable internal stage (JOB-ACTIONS), it does not change the
  wave-gate mechanics DEC-032/`mvp-completion-program.md` §7 already
  established.

## Rejected or deferred alternatives

(Restated from "Options considered" above for the standard log format.)
Absorb all of Area 6 into Wave 1 — rejected, scope violation. Drop
SEC-1's D-SEC1-3 job-action doors — rejected, weakens an accepted
decision closure. Create the Task 012 order-binding file early —
rejected, starts Wave 2 inside Wave 1. Reorder to SEC-1-before-LC-1
and redesign LC-1's cancellation path — rejected, redesigns an Accepted
decision (DEC-030) to fit a non-binding recommended order.

## Acceptance effect

**[Placeholder — completed only after independent verification and the
adversarial consistency check (Phase 7) confirm the reconciliation is
internally consistent and fully documented. Do not treat this record as
binding until this section names the accepting control-room review.]**
