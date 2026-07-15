# Task SEC-1 — Cross-Cutting Security Hardening: Implementation-Ready Planning Packet

> **Status: Proposed for control-room review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 7 of ChatGPT's
> control-room review (PR #148 comment `4942966937`). **Sequencing
> corrected 2026-07-15 by
> [`DEC-034`](../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md)
> (Wave 1 packet reconciliation, resolving Sol's hard-stop, issue #167
> comment `4980808811`): this packet is Wave 1 Stage 4 — sequenced
> after CORE-R1, Task LC-1, and Task
> [JOB-ACTIONS](./task-job-actions-generic-core-packet.md) (which
> supplies `action_manual_retry()`/`action_cancel()`, the sanctioned
> job-action doors D-SEC1-3 names, as a generic Wave 1 prerequisite —
> not Area 6, which remains unauthorized Wave 2+ scope), and before
> UI-U1** — the UI must wire buttons to an already-hardened backend.
> The original text below assumed an Area-6 prerequisite; every place
> that assumption appears is corrected in place (§3 D-SEC1-3, §5, §7,
> §9) rather than left as historical narrative, since the underlying
> mechanics (the two methods' exact behavior) are unchanged — only
> which task supplies them. Evidence: merged code re-read 2026-07-11
> and re-verified 2026-07-15 against the live Wave 1 baseline; captures
> 2026-07-11 §8 (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).
> **Final-convergence revision 2026-07-11 per comment `4947866018`
> item 6: the `action_override_binding` contract is corrected — no
> model argument is accepted, the scalar id is resolved *only* in the
> comodel fixed by `_odoo_binding_field_name()`, and the impossible
> "valid id of the wrong model" test/claim is withdrawn (a bare integer
> cannot be classified as belonging to another model); cross-model
> safety comes from the fixed comodel plus the existence/company/
> uniqueness checks (D-SEC1-4/7).**

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
`superseded_by_job_id`, **`cancel_reason`** (added 2026-07-15, DEC-034
Wave 1 reconciliation adversarial check: `cancel_reason` is the field
Task JOB-ACTIONS's `action_cancel()` writes alongside `state` under
its own mandatory-non-empty-reason, audited, permission-gated
contract — omitting it here would leave it a plain
`perm_write=1`-ACL'd field, directly RPC/ORM-writable by any
operator/reviewer/admin with no group check, no reason validation, and
no audit row, bypassing `action_cancel()`'s own contract for exactly
the field that records *why* a job was cancelled) — is writable only
when `self.env.su` is true
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
/ Disconnect / Reconnect would raise under the new guard). **Wave 1
reconciliation addition (DEC-034):** two further sanctioned internal
protected-field writers are recognized by name — Task LC-1's
`_reassign_to_historic_job_type()` (writes `state='cancelled'` on
non-terminal jobs during historic-job conversion; lands
Wave-1-Stage-2, before this packet) and Task JOB-ACTIONS's
`action_manual_retry()`/`action_cancel()` (land Wave-1-Stage-3, before
this packet). Both already exist by the time this packet implements;
both are elevated at their existing write sites (in
`shopify_connector_job.py` for the former, `shopify_connector_job_actions.py`
for the latter — both in §5's allowlist) exactly like every other
named site above — no new mechanism, no behavior change to either
method, only the su wrapper.

**D-SEC1-3 — Sanctioned methods (the only doors).** The public
mutation surface for jobs becomes exactly: `enqueue()` (creation —
existing service; direct `create()` by non-su callers is refused for
business sources), Task JOB-ACTIONS's `action_manual_retry()` /
`action_cancel()` (extracted from the original D-A6-5 design into its
own generic Wave 1 prerequisite stage per DEC-034 — implemented
Wave-1-Stage-3, immediately before this packet; mechanics unchanged
from the original D-A6-5 text), and a new `action_resolve_manual_review()`
(reviewer/admin; `blocked_manual_review→queued` after an operator
fixes the underlying cause, one audited `manual_action` log row —
this is the "resolve" affordance the Error Center wires later; it
re-queues through the same matrix edge as manual retry). Each method:
explicit group check (`has_group`), matrix-legal transition, audit
log row with actor, then su-elevated write. No force/bypass parameter
exists anywhere (merged invariant restated).

**D-SEC1-4 — Binding identity immutability + audited override
(exact, RPC-safe contract — re-review `4945129824` item 6).** On the
binding mixin: identity fields (`store_id`, `shopify_gid`, the
per-model Odoo-record M2o, `match_key`) become su-protected exactly
like D-SEC1-2.

**Mixin seam.** The abstract mixin declares
`_odoo_binding_field_name()` returning the name of the concrete
model's Odoo-record `Many2one` field (or a falsy value when the
binding's identity is composite/derived, not a single Odoo record).
The mixin default returns `False`; every concrete binding model
declares its own (a one-line return). **Enumeration — every current
and planned binding model (corrected 2026-07-15, DEC-034: the "exists
at gate" column reflects the live Wave 1 baseline, not the
pre-reconciliation assumption that Task 012's order binding would
already exist):**

| Binding model | `_odoo_binding_field_name()` | Comodel | Exists at Wave 1 gate? |
| --- | --- | --- | --- |
| `shopify.connector.product.template.binding` | `product_template_id` | `product.template` | Yes |
| `shopify.connector.product.variant.binding` | `product_variant_id` | `product.product` | Yes |
| `shopify.connector.customer.binding` | `partner_id` | `res.partner` | Yes |
| `shopify.connector.order.binding` (Task 012, Wave 2) | `sale_order_id` | `sale.order` | **No — future, per the binding-extension contract (DEC-034)** |
| `shopify.connector.location.mapping` (Task 013, Wave 3) | `odoo_location_id` | `stock.location` | No — future |
| `shopify.connector.inventory.level.binding` (Task 013, Wave 3) | `False` (composite: variant-binding × location — re-derived deterministically, not overridable) | — | No — future |
| `shopify.connector.product.media.binding` (Task 015B, Wave 5) | `False` (identity is the remote File GID, not an Odoo record — not overridable) | — | No — future |

**Only the three models that exist at the Wave 1 baseline** (product
template/variant, customer) get the one-liner from **this task** (§5).
The nonexistent order-binding file is removed from this task's
allowlist (§5) — Task 012 does not exist at Wave 1 and must not be
started here. **Binding-extension contract (binding, DEC-034):** every
future binding model (order, location.mapping, inventory.level, media,
and any later addition) declares its own `_odoo_binding_field_name()`
seam — or explicitly relies on the mixin's fail-closed `False` default
where identity is composite/derived, per the table above — in **that
model's own implementation packet**, at the time the model is created.
The mixin default (`False`) is fail-closed: a future binding model that
forgets to declare the seam gets `UserError` on any
`action_override_binding` call, never a silent write. No future
binding may introduce its own parallel, unprotected identity-mutation
path — the su-protection on identity fields lives on the mixin
(inherited automatically by every concrete binding model, §4), so this
is structural, not a per-model opt-in.

**Public method.** `action_override_binding(new_record_id, reason)`
accepts a **scalar integer record ID** (not a recordset — RPC cannot
safely convey a generic recordset argument contract) plus a
**mandatory non-empty `reason`**. **No model argument is accepted**
(re-review `4947866018` item 6): the comodel is fixed by the binding
via `_odoo_binding_field_name()`, and the id is resolved **only** in
that declared comodel. It:
1. resolves the target model from `_odoo_binding_field_name()`; a
   falsy return raises `UserError` ("this binding's identity is not
   overridable");
2. validates `new_record_id` is a positive int and that the record
   **exists in the declared comodel** (`browse(...).exists()`) — a
   missing/non-existent, malformed, or non-int argument raises
   `UserError`, never a silent write. **There is no "wrong-model"
   check, because none is possible or needed:** the caller supplies no
   model, and a bare integer that also happens to exist in some other
   model is indistinguishable from a valid id — the id is simply
   resolved in the fixed comodel, and if it does not exist *there* it is
   rejected. Cross-model safety comes from the fixed comodel plus the
   existence/company/uniqueness checks below, not from inspecting the
   integer;
3. validates store/company consistency where the target carries a
   company (e.g. `sale.order`/`stock.location` company must match the
   binding store's company) — mismatch raises `UserError`;
4. enforces reviewer/admin permission (`has_group`) — else
   `AccessError`;
5. checks the resulting `(store_id, <odoo field>)` **still satisfies
   the model's uniqueness constraints** (no collision with another
   binding) before writing;
6. records **previous and new identity** in the audit trail
   (`override_previous_candidate` = the previous record reference,
   `override_uid`/`override_at` force-filled, one audited
   `manual_action` log row naming old→new and the reason), sets
   `status='manually_overridden'`, and re-points **only** the declared
   Odoo-record field — all in one **su** write after the checks (the
   sanctioned sudo path).

Snapshot fields stay ordinarily writable by the importer only (they
are already `readonly=True` in UI; importer writes are su per
D-SEC1-2's importer adjustment). Unlink stays denied for every group
(existing posture).

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
`write({'state': …})`, `write({'retry_count': …})`, **`write({'cancel_reason': …})`
(added 2026-07-15, DEC-034 — proves the field `action_cancel()` writes
cannot be forged/overwritten outside that sanctioned method)**, binding
`write({'shopify_gid': …})`, `write({'partner_id': …})`, job
`create()` bypassing enqueue, `unlink()` everywhere, PII field read,
masked-field read, each sanctioned method with and without the
required group, matrix-illegal transitions via sanctioned methods,
and a sudo-path regression (dispatcher/importer still function).
**`action_override_binding` negative RPC set (re-review `4947866018`
item 6):** non-int / malformed `new_record_id`; a **non-existent id
(absent from the declared comodel)** → reject (this replaces the
withdrawn "valid id of the wrong model" test — no model argument is
accepted, so a bare integer cannot be classified as belonging to a
"wrong model"; it is resolved only in the fixed comodel and rejected
iff it does not exist there); a target violating store/company
consistency; a value that would collide with another binding's
uniqueness constraint; a call on a **non-overridable** binding
(`_odoo_binding_field_name()` falsy — level/media binding);
missing/empty `reason`; and the same call by a non-reviewer group —
each expecting `UserError`/`AccessError` and **no write**; plus the
positive reviewer/admin path asserting old→new identity is recorded in
the audit trail. Expected outcome per cell stated in the test
(AccessError / ValidationError / UserError / success), mirroring the
merged ACL-matrix test pattern.

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
  (matrix constant, write-guard, `action_resolve_manual_review`, and
  the su-elevation of Task LC-1's already-existing
  `_reassign_to_historic_job_type()` write site — DEC-034)
- `addons/shopify_connector_core/models/shopify_connector_job_actions.py`
  (su-elevation of Task JOB-ACTIONS's already-existing
  `action_manual_retry()`/`action_cancel()` write sites only — DEC-034;
  no behavior change to either method)
- `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`
  (protected-field guard, `action_override_binding`, and the
  `_odoo_binding_field_name()` seam defaulting to `False`)
- the concrete-binding `_odoo_binding_field_name()` one-liners on the
  **three** models existing at this gate (corrected 2026-07-15,
  DEC-034 — the order-binding file does not exist and is removed from
  this allowlist; Task 012 declares its own seam in its own packet per
  the binding-extension contract):
  `addons/shopify_connector_product/models/shopify_connector_product_template_binding.py`
  (`return 'product_template_id'`),
  `addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py`
  (`return 'product_variant_id'`) — one line each (the customer
  binding's is added with its PII change below)
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
  `_pii_snapshot_fields()` override + the `_odoo_binding_field_name()`
  one-liner returning `partner_id`)
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

1 Task LC-1 merged runtime-green (the historic-job helper exists to
recognize as a sanctioned writer) AND Task JOB-ACTIONS merged
runtime-green (the sanctioned job-action services exist to inherit the
guard) — corrected 2026-07-15, DEC-034; replaces the original "Area 6
merged runtime-green" criterion, which named unauthorized Wave 2+
scope; 2–3 exact names ✅(§3); 4 files ✅(§5); 5 matrix +
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
DO NOT USE UNTIL CHATGPT/CONTROL-ROOM REVIEWS AND ACCEPTS THIS PLANNING
PACKAGE, EXPLICITLY OPENS THE SEC-1 GATE, VERIFIES THE CURRENT BASE
SHA, AND ISSUES THIS PROMPT. (Prerequisite: Task LC-1 AND Task
JOB-ACTIONS merged runtime-green, per DEC-034's corrected Wave 1 order
— CORE-R1 -> LC-1 -> JOB-ACTIONS -> SEC-1 -> SRR-03 closure. NOT Area
6 — Area 6 remains unauthorized Wave 2+ scope.)

Implement Task SEC-1 — cross-cutting security hardening — exactly per
docs/07-implementation-plan/task-sec1-security-hardening-packet.md
(D-SEC1-1..7 binding) and captures 2026-07-11 §8. Branch from the
verified current mvp/program-integration tip (STOP on drift). One
session; draft PR; stop.

ALLOWED FILES: exactly the §5 list — nothing else. FORBIDDEN: ACL CSV
permission rows; credential model; error registry; retry constants;
views/UI; webhooks/OAuth/CI; inventory/fulfillment/product_export
modules; adams_base; main; plain dev.

IMPLEMENT exactly: D-SEC1-1 exhaustive legal-transition matrix
enforced in write() for every caller including sudo; D-SEC1-2
protected-field su guard on the job model (named field set; every
internal elevation itemized in the validation record's sudo
inventory — INCLUDING Task LC-1's already-existing
_reassign_to_historic_job_type() and Task JOB-ACTIONS's already-existing
action_manual_retry()/action_cancel(), recognized as sanctioned
internal writers and elevated at their existing write sites, no
behavior change to either); D-SEC1-3 sanctioned doors only (enqueue,
manual retry, cancel [already implemented by Task JOB-ACTIONS —
this task elevates them, does not reimplement them], resolve-manual-
review [new] — group-checked, matrix-legal, audited, no bypass
parameter); D-SEC1-4 binding identity su-protected + the
_odoo_binding_field_name() mixin seam (each of the THREE concrete
binding models existing at this gate declares its Odoo-record field
per the enumerated table; the order/location/inventory/media bindings
do not exist yet and are NOT touched — they declare their own seam in
their own future packets per the DEC-034 binding-extension contract) +
action_override_binding(new_record_id:int, reason) — NO model argument
is accepted; resolve the comodel from the seam and the id ONLY within
that comodel; validate the target exists in the declared comodel +
store/company consistency; reject malformed / non-existent-in-comodel /
non-overridable input (there is NO wrong-model check — a bare int cannot
be classified as belonging to another model); enforce reviewer/admin,
preserve uniqueness, record old->new identity in the audit trail, write
through the sanctioned su path; the D-SEC1-7 negative RPC set proves
every rejection;
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
