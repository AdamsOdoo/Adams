# Task SEC-1 — Cross-Cutting Security Hardening: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 7 of ChatGPT's
> control-room review (PR #148 comment `4942966937`). Sequenced
> **after Area 6 (which introduces the sanctioned job-action
> services) and before UI-U1** — the UI must wire buttons to an
> already-hardened backend. Evidence: merged code re-read 2026-07-11;
> captures 2026-07-11 §8 (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).

## 1. The verified current exposure (facts, file:line)

1. **[Fact]** `ir.model.access.csv` (core) grants `perm_write=1` on
   `shopify.connector.job` to operator, reviewer, and admin (and
   `perm_create=1` to operator/admin). The job `state` field is
   `readonly=True` — but **[Fact, captures §8]** the 19.0 ORM
   reference states readonly "only has an impact on the UI. Any field
   assignation in code will work." The only server-side write guards
   are the connected-store/domain-flag gates on transitions **to
   `running`** for business-source jobs and two `@api.constrains`
   (`trigger_origin`, `manual_review_subreason`)
   (`shopify_connector_job.py` write(), lines 221–276; precision,
   red-team-corrected 2026-07-11 round 2: the domain-flag gate runs
   for **every** job — lines 243–247/265–275 — only the
   connected-store gate is business-source-scoped, lines 259–264).
   Consequence: any operator-group user can, via RPC/ORM, set e.g.
   `state='succeeded'` on a failed job, alter `retry_count`, or
   forge `error_class` — system-state mutation outside any sanctioned
   action, unaudited.
2. **[Fact]** Binding models grant reviewer `perm_write=1` and admin
   `perm_write/create=1` (product/sale ACL files) with **no**
   server-side guard on identity fields — `shopify_gid`, `store_id`,
   `partner_id`/`product_*_id`, `match_key` are RPC-mutable within
   ACL, silently re-pointing a binding with no audit trail beyond the
   generic mixin fields (which nothing forces to be filled).
3. **[Fact]** PII snapshots (`shopify_email_snapshot`,
   `shopify_phone_snapshot`, `shopify_display_name` on the customer
   binding) are readable by **every** connector group including
   auditor (ACL read=1 for all four groups); no field-level `groups=`
   exists; no record rules exist anywhere in the three modules.
4. **[Fact]** No retention/deletion mechanism exists for PII-bearing
   `payload_snapshot`/candidate-evidence content beyond log-write
   redaction.

## 2. Objective, scope, non-goals

Enforce, server-side: a legal job state-transition matrix; sanctioned
methods as the only mutation path for system-maintained records;
binding-identity immutability with an audited override workflow;
least-privilege PII snapshot visibility; and a retention/deletion/
export posture — all proven by negative RPC/ORM tests. **Non-goals:**
no new groups (the four merged groups stand); no record rules
(single-store model — re-evaluated at multi-store time, unchanged);
no credential-model changes (Task 002 posture / DEC-028 untouched);
no UI; no change to dispatcher routing logic or retry semantics; no
webhook/OAuth surface.

## 3. Decision closures (D-SEC1-1 … D-SEC1-7) — each Proposed

**D-SEC1-1 — Legal job transition matrix (server-enforced).** A
module-level constant on the job model, exhaustive:
`draft→queued`; `queued→running|cancelled`;
`running→succeeded|failed_final|skipped|retry_waiting|failed_retryable|blocked_manual_review`;
`retry_waiting→running|cancelled`;
**`draft|queued|retry_waiting→failed_retryable` (the merged
blocked-start routing — red-team-corrected 2026-07-11 round 2: the
dispatcher's `_start_running` catches the gating `ValidationError`
and routes a still-`queued`/`retry_waiting`/`draft` job to
`failed_retryable` via `odoo_validation_configuration`,
`shopify_connector_job_dispatch.py` lines 186–200, asserted green by
`test_job_dispatch.py` lines 238–286 — a matrix without these edges
would break the merged dispatcher and its suite)**;
`failed_retryable|failed_final|blocked_manual_review|skipped→queued`
(manual retry — Area 6's allowed-from set, retry_count reset);
non-terminal→`cancelled`. Everything else — including any
terminal→terminal edge and any write that *skips* a state — is
illegal. `write()` validates every `state` change against the matrix
and raises `ValidationError` on violation **regardless of caller**
(sudo included — the matrix is a correctness invariant, not a
permission).

**D-SEC1-2 — Protected system fields require system context.** On
`shopify.connector.job`, the protected set — `state`, `retry_count`,
`error_class`, `manual_review_subreason`, `payload_hash`,
`res_model`, `res_id`, `shopify_target_gid`, `job_type`, `job_source`,
`trigger_origin`, `next_retry_at`, `started_at`, `finished_at`,
`superseded_by_job_id` — is writable only when `self.env.su` is true
(the dispatcher, transitions, and sanctioned services run their
writes through an internal `sudo()` after their own explicit
permission checks). A non-su write touching any protected field
raises `AccessError` with a message naming the sanctioned action to
use. **The guard applies equally at `create()` (red-team-corrected
2026-07-11 round 2):** a non-su `create()` supplying protected fields
beyond the enqueue-door defaults is refused — otherwise the §1 abuse
channel merely moves to creation (an operator forging a
`state='succeeded'` job or a binding row at create time); the named
su-elevated creation doors are `enqueue()`, the readiness-check job
creation, and the store-lifecycle audit/test-connection job creation
(all in §5's allowlist), and the existing ACL-matrix tests that
exercise direct creates are updated accordingly (named in §6).
Rationale (flagged): context-flag guards were considered and
rejected — RPC callers control context, so a context marker is
spoofable; `env.su` is not. The dispatcher/enqueue/readiness **and
store-lifecycle** code paths are adjusted to elevate exactly at
their write sites (each elevation named in the packet's sudo
inventory — extending the release plan's §2.8 audit list;
red-team-corrected round 2: `shopify_connector_store.py` is itself a
writer of protected job fields — test-connection job mirrors, the
lifecycle audit jobs, and the disconnect cancellation sweep, lines
108–205/233–248/351–364 — and is therefore in the §5 allowlist with
those exact sites elevated; without this, Test Connection / Activate
/ Disconnect / Reconnect would raise under the new guard).

**D-SEC1-3 — Sanctioned methods (the only doors).** The public
mutation surface for jobs becomes exactly: `enqueue()` (creation —
existing service; direct `create()` by non-su callers is refused for
business sources), Area 6's `action_manual_retry()` /
`action_cancel()`, and a new `action_resolve_manual_review()`
(reviewer/admin; `blocked_manual_review→queued` after an operator
fixes the underlying cause, one audited `manual_action` log row —
this is the "resolve" affordance the Error Center wires later; it
re-queues through the same matrix edge as manual retry). Each method:
explicit group check (`has_group`), matrix-legal transition, audit
log row with actor, then su-elevated write. No force/bypass parameter
exists anywhere (merged invariant restated).

**D-SEC1-4 — Binding identity immutability + audited override.** On
the binding mixin: identity fields (`store_id`, `shopify_gid`, the
per-model Odoo-record M2o, `match_key`) become su-protected exactly
like D-SEC1-2. The sanctioned mutation is a new mixin method
`action_override_binding(new_odoo_record, reason)` — reviewer/admin
only; requires non-empty `reason`; writes the existing audit fields
(`override_uid`, `override_at`, `override_previous_candidate` — now
force-filled, not optional), sets `status='manually_overridden'`,
appends one audited log row, and re-points the record link — all in
one su write after the checks. Snapshot fields stay ordinarily
writable by the importer only (they are already `readonly=True` in
UI; importer writes are su per D-SEC1-2's importer adjustment).
Unlink stays denied for every group (existing posture).

**D-SEC1-5 — Least-privilege PII snapshots.** The customer-binding
PII fields (`shopify_email_snapshot`, `shopify_phone_snapshot`,
`shopify_display_name`) gain field-level
`groups='shopify_connector_core.group_shopify_connector_reviewer,shopify_connector_core.group_shopify_connector_admin'`
(ORM-enforced read restriction); a computed, non-stored
`pii_snapshot_masked` (e.g. `j***@e***.com`) is readable by
operator/auditor for identification without disclosure. The Task 012
order-binding packet's PII-bearing snapshots adopt the same pattern
(cross-reference added there). Candidate-evidence JSON in job logs
remains capped + redacted (merged behavior) — no change needed,
re-asserted by test.

**D-SEC1-6 — Retention / deletion / export rules.** New core
settings: `pii_snapshot_retention_days` (Integer, default 0 =
retain; documented recommendation 365) and a monthly cron
`pii_retention_sweep` that, when retention is configured, **masks**
(never deletes rows — audit history is append-only by design)
PII-bearing snapshot fields and `payload_snapshot` PII keys on
records older than the window, logging one summary row per sweep.
**Discovery seam (red-team-added 2026-07-11 round 2 — core cannot
depend on sale):** the binding mixin gains a `_pii_snapshot_fields()`
hook returning `[]`; PII-bearing binding models override it (the
customer binding returns its three snapshot field names — a
two-line override in the sale binding file, added to §5); the core
sweep iterates the registry for models inheriting the mixin and
masks the declared fields — no core→sale dependency, no hardcoded
model names.
Export/data-request support (DEC-028 Rung-2 item (d) groundwork):
a documented operator procedure (release-plan §2.5 doc set) using
standard Odoo export on the reviewer-visible fields — no new code
surface. Deletion-on-request: the same masking mechanism applied to
one named customer's records via a service method
(`action_mask_customer_pii(binding)`, admin-only, audited). This
implements the PCD "retention/deletion" practice at MVP level
without inventing encryption (DEC-028 boundary respected).

**D-SEC1-7 — Negative test matrix (the proof).** For each group
(auditor/operator/reviewer/admin) × each protected surface: direct
`write({'state': …})`, `write({'retry_count': …})`, binding
`write({'shopify_gid': …})`, `write({'partner_id': …})`, job
`create()` bypassing enqueue, `unlink()` everywhere, PII field read,
masked-field read, each sanctioned method with and without the
required group, matrix-illegal transitions via sanctioned methods,
and a sudo-path regression (dispatcher/importer still function).
Expected outcome per cell stated in the test (AccessError /
ValidationError / success), mirroring the merged ACL-matrix test
pattern.

## 4. Why this is one cross-cutting task (not per-domain)

The exposure is substrate-level (job model + binding mixin); the fix
must land once, in core, before any UI exposes buttons that would
otherwise coexist with an open RPC back door. Domain modules inherit
the hardening through the mixin with zero per-domain edits (the
product/sale binding models change only via the mixin; their ACL
rows are unchanged). This is a **core-owned task** under ARCH §7's
core-task rule, with the exhaustive allowlist below.

## 5. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_core/models/shopify_connector_job.py`
  (matrix constant, write-guard, `action_resolve_manual_review`)
- `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`
  (protected-field guard, `action_override_binding`)
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`,
  `shopify_connector_job_enqueue.py`,
  `shopify_connector_readiness_check.py`,
  `shopify_connector_store.py` (write-site su elevation only — each
  elevation itemized; the store file's sites are the test-connection
  job mirrors, lifecycle audit jobs, and disconnect sweep —
  red-team round-2 F1)
- `addons/shopify_connector_core/models/shopify_connector_store_settings.py`
  (retention field)
- `addons/shopify_connector_core/models/shopify_connector_pii_retention.py`
  (NEW — sweep + masking services)
- `addons/shopify_connector_core/data/shopify_connector_pii_retention_cron.xml`
  (NEW, noupdate=1)
- `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py`
  (field `groups=` + masked compute + the two-line
  `_pii_snapshot_fields()` override only)
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
  (snapshot/binding-write su adjustment only — its binding-create
  sites set protected identity fields)
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`
  (snapshot/binding-write su adjustment only)
- manifests (version bumps; core data entry);
  `addons/shopify_connector_core/tests/test_security_hardening.py` (NEW)
  + `addons/shopify_connector_core/tests/__init__.py` (one import line);
  `addons/shopify_connector_sale/tests/test_pii_least_privilege.py` (NEW)
  + `addons/shopify_connector_sale/tests/__init__.py` (one import line);
  existing ACL-matrix test files (named assertion updates only —
  incl. the direct-create cells that now expect refusal per
  D-SEC1-2's create-guard)
- `docs/05-qa/task-sec1-validation-results.md` (NEW); AR-log row;
  handoff top entry.

**Forbidden:** ACL permission rows themselves (no CSV change — the
guard layer, not the ACL, is the fix; flagged design choice: keeping
operator create/write ACL bits avoids breaking sanctioned service
call paths while the su-guard closes the abuse channel); credential
model; error registry; retry constants; views/UI; webhooks/OAuth/CI;
inventory/fulfillment/export modules (they inherit via mixin);
`adams_base`; `main`; plain `dev`.

## 6. Tests

`test_security_hardening.py` — the full D-SEC1-7 negative matrix +
matrix-transition property test (every illegal edge raises; every
legal edge reachable only through its sanctioned door) + sudo-path
regressions + retention sweep (masking, summary log, append-only
preserved) + `action_mask_customer_pii`.
`test_pii_least_privilege.py` — field-groups enforcement per group;
masked compute format; order-binding pattern note (activated with
Task 012). All existing suites must stay green — in particular
Task 010/011 importer suites (su adjustments must not change
behavior).

## 7. Gate criteria (15-pattern, abbreviated)

1 Area 6 merged runtime-green (sanctioned services exist to inherit
the guard); 2–3 exact names ✅(§3); 4 files ✅(§5); 5 matrix +
protected sets fixed ✅(D-SEC1-1/2); 6–8 no UI/webhook/domain-logic
scope ✅; 9 tests ✅(§6); 10 rollback ✅(single-PR revert; guards
drop, behavior returns to merged state — documented, no data change
except masked fields which are irreversible by design and only ever
masked under an explicit retention config or admin action); 11 no
live-Shopify dependency ✅; 12 gate-act reconfirmation; 13 flagged
calls explicit: su-guard over ACL-row changes (§5), matrix applying
to sudo too (D-SEC1-1), masking irreversibility (D-SEC1-6); 14 PII
visibility matrix explicit ✅(D-SEC1-5); 15 override workflow +
forced audit trail explicit ✅(D-SEC1-4).

## 8. Register impacts on acceptance

The control-room audit's RPC-mutation risk → owned and closed at
planning level by this packet; release plan §2.8 sudo inventory
extended (each D-SEC1-2 elevation named); DEC-028 Rung-1
retention/deletion practice → implemented surface (D-SEC1-6);
UI packet updated: Error Center buttons wire to
`action_manual_retry`/`action_cancel`/`action_resolve_manual_review`
only.

## 9. Locked final implementation prompt (Task SEC-1)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE SEC-1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT. (Prerequisite: Area 6 merged runtime-green.)

Implement Task SEC-1 — cross-cutting security hardening — exactly per
docs/07-implementation-plan/task-sec1-security-hardening-packet.md
(D-SEC1-1..7 binding) and captures 2026-07-11 §8. Branch from the
verified current Shopify-connector tip (STOP on drift). One session;
draft PR; stop.

ALLOWED FILES: exactly the §5 list — nothing else. FORBIDDEN: ACL CSV
permission rows; credential model; error registry; retry constants;
views/UI; webhooks/OAuth/CI; inventory/fulfillment/product_export
modules; adams_base; main; plain dev.

IMPLEMENT exactly: D-SEC1-1 exhaustive legal-transition matrix
enforced in write() for every caller including sudo; D-SEC1-2
protected-field su guard on the job model (named field set; every
internal elevation itemized in the validation record's sudo
inventory); D-SEC1-3 sanctioned doors only (enqueue, manual retry,
cancel, resolve-manual-review — group-checked, matrix-legal, audited,
no bypass parameter); D-SEC1-4 binding identity su-protected +
action_override_binding with forced audit fields and required reason;
D-SEC1-5 PII field groups= (reviewer/admin) + masked compute for
operator/auditor; D-SEC1-6 retention setting + monthly masking sweep
(mask, never delete rows) + admin-only audited
action_mask_customer_pii; D-SEC1-7 the full negative RPC/ORM matrix.
View-level readonly is NOT a security mechanism (captures 2026-07-11
§8) — every guard is server-side.

Runtime: full Odoo.sh run green before merge review (verbatim quote);
all pre-existing suites green unchanged. Stop condition: draft PR
"Task SEC-1: server-side transition, binding, and PII hardening";
gate closes on draft-open; no UI/webhook/domain work.
```
