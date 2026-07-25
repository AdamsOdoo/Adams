# Wave 4 Tier-1 Correction — Decision Lock (PR #189)

> **Partially superseded (2026-07-23).** The one-loop control-room ruling
> (PR #189 review comments `4766049839`/`4766053529`) accepted this
> document's Decisions A, C, D in full and authorized implementation, which
> a later session completed. **Decision B.5 (F-4's interim-only-for-this-PR
> disposition) was explicitly superseded**: the same ruling widened this
> campaign's scope to implement Decision B's **permanent** architecture
> (§B.1-B.4) directly, removing the need for the interim
> always-fails-closed `_c8_location` patch B.5 describes. Decision B's
> §B.1-B.4 target-architecture design (the core seam + inventory override
> shape) was implemented essentially as frozen here. Decision A (Theme D /
> SEC-3) remains genuinely deferred, unchanged. See
> `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` §
> "WAVE 4 CLOSURE CORRECTION CAMPAIGN" for the implementation record. The
> rest of this document (the frozen decisions themselves) is preserved
> unchanged below as the governing design record.
>
> Prior status (superseded): `PROPOSED — AWAITING CONTROL-ROOM ACCEPTANCE`
> (binding for the locked implementation prompt's purposes; not a
> ChatGPT-approved product/architecture `Decision` under CLAUDE.md §8 until
> the control room reviews this document). The implementation prompt this
> document updates remains NOT AUTHORIZED for use until the control room
> reviews this decision-lock output. No production/test/manifest/security/CI
> file was created or modified to produce this document. No Odoo.sh runtime
> was executed. No Shopify request or mutation occurred.

- **Repository:** `AdamsOdoo/Adams`
- **PR:** #189 ("Wave 4 Gate B: fulfillment and tracking backend")
- **Base:** `mvp/program-integration@dd0af5d94a7f730e738dca955971e00bb4cc9122`
- **Prior head (findings-synthesis, reviewed by this session):** `d3c157c1d4c369c1880fffc69ee6b4801ab9c05c`
- **This decision-lock's docs-only head:** recorded in the commit immediately following this document on branch `claude/wave-4-fulfillment-gate-b` — see the PR timeline / `research-handoff.md` top entry for the exact SHA.
- **Governing records:** independent Tier-1 review (PR #189 comment [`5058257403`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058257403)); findings-synthesis ruling (comment [`5058826143`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058826143)); control-room synthesis-acceptance / decision-lock ruling (comment [`5059969776`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5059969776) — the document this decision-lock directly answers); program handoff (issue #167 comment [`5059972681`](https://github.com/AdamsOdoo/Adams/issues/167#issuecomment-5059972681)).
- **Scope:** resolves the four unresolved load-bearing questions comment `5059969776` identified in the accepted 24-finding/13-theme synthesis (`wave-4-tier1-findings-ledger.md`, `wave-4-tier1-correction-synthesis.md`) so the locked correction prompt (`wave-4-tier1-correction-locked-candidate.md`) can be executed literally by a separate implementation worker. **This document does not repeat the findings synthesis and does not implement any correction.**

---

## Method

Four parallel, read-only research agents ground-truthed each open decision against (a) the exact production/test source at the current head, (b) every governing DEC named in the control-room ruling, (c) `rejected-approaches-log.md` (full read, no collision found against any of the four decisions below), and (d) current official Odoo 19 and Shopify developer documentation (full citations inline). No claim below is asserted as Fact without a file:line or an official-source citation; every architectural call is labelled a **Recommendation** (CLAUDE.md §8) frozen for the locked prompt's executability, not a ChatGPT-accepted **Decision**.

---

## Decision A — Theme D: multi-company `ir.rule` gap (`shopify.connector.job` / `.mutation.attempt`)

### A.1 Exact security risk and affected roles/actions

**Fact.** Neither `shopify.connector.job` (`addons/shopify_connector_core/models/shopify_connector_job.py`) nor `shopify.connector.mutation.attempt` (`.../shopify_connector_mutation_attempt.py`) carries a `company_id` field or any `ir.rule` (confirmed: `shopify_connector_security.xml` contains zero `ir.rule` records for either model). `shopify.connector.store` (`job.store_id`'s target) also has no `company_id` field, and `job.res_model`/`job.res_id` are a plain `Char`+`Integer` pair — not ORM-traversable, so no `domain_force` dot-path to `res.company` exists today (contrast with the fulfillment addon's own `fulfillment_binding_company_rule`/`fulfillment_inbound_evidence_company_rule`, which scope through the **bound Odoo record's** `company_id` — a pattern job/mutation_attempt structurally cannot copy, because their "bound record" is a generic, untyped res_model/res_id pair, not a typed relation).

ACL is model-level only (`ir.model.access.csv:15-18,24-27`): all four groups (`auditor`/`operator`/`reviewer`/`admin`) get `perm_read=1` on both models with **no row-level filter**; `operator`/`admin` additionally hold `perm_write`/`perm_create` on `job`. **Concrete risk:** any Odoo user in any of the four groups — in any company they belong to — can read every `shopify.connector.job` and `.mutation.attempt` row for every store/company via ordinary RPC; `operator`/`admin` can write job rows belonging to any other company's store (bounded only by the model's state-machine/protected-field guards, which check nothing about company); `action_resolve_manual_review()` (reviewer/admin) and `action_resolve_mutation_attempt()` (admin) are likewise gated only on group membership, not company. This is a genuine cross-company confidentiality/integrity gap, not a hypothetical one.

Post-SEC-2 (two-role model), the same exposure carries forward unchanged: SEC-2's own `connector-roles-and-permissions.md` §4.5 re-keys existing rule *group_ids*, it does not add a rule where none exists — confirmed by direct read of the SEC-2 packet (§5 below).

### A.2 Merge / UAT / release-candidate gate

**Recommendation (frozen).** Theme D **does not block PR #189's own merge into `mvp/program-integration`.** Rationale: the gap is confirmed pre-existing since Wave 1, shared identically by every domain (product/sale/inventory/fulfillment), and structurally unchanged in kind by PR #189 (Wave 4 adds ten more `job_type` values onto an already-company-unscoped model; it does not narrow, widen, or newly expose the access boundary). This is the same footing already established for issue #185 (CV-013) and issue #193 — both real, open, program-level gaps that are tracked separately and gate later stages rather than blocking this PR's merge.

Theme D **does block**:
- **External UAT** — no multi-company UAT scenario may execute while this gap is open (a UAT participant in one company could read another test company's job/mutation-attempt data).
- **MVP release-candidate acceptance** — the connector must not ship an RC with a confirmed, unmitigated cross-company access-control gap on two Tier-1 (security/data-integrity) models.

Theme D does **not** block SEC-2's own merge or U1 implementation; U1's contract inventory should record this as an open caveat on its job/mutation-attempt lineage display (§8, already flagged `revalidation_required` by the synthesis) rather than as a U1 implementation blocker.

### A.3 Exact implementation owner

**Recommendation (frozen).** **A new, dedicated, control-room-scoped security task/DEC** — not SEC-2, not PR #189/Wave 4. Verified by direct read of `task-sec2-two-role-and-pii-simplification-packet.md`: its allowed-files list (§G) is exactly four items (group/privilege data, ACL re-keying, the sale customer-binding masking removal, the PII-retention model/cron, store-settings, views, migrations, tests — all PII/role-migration scoped) and its forbidden list (§G) explicitly excludes **"any job/lease/dispatcher/replay/credential/inventory/fulfillment/export/Shopify-mutation code; any DEC-031 Layer 2 work."** `shopify.connector.job` is a job/dispatcher model and `shopify.connector.mutation.attempt` is DEC-031 Layer 2 evidence — both fall squarely inside SEC-2's own forbidden category. SEC-2 §A.4 names "company isolation" only as an existing protection to **preserve unweakened**, never as new work to add. Folding Theme D into SEC-2 without an explicit SEC-2 scope amendment would violate SEC-2's own locked boundaries the same way folding it into PR #189 would violate Wave 4's.

Candidate name for the control room: **"SEC-3 — `shopify.connector.job`/`.mutation.attempt` multi-company access-control hardening."** Requires its own DEC per CLAUDE.md §9, targeting `shopify_connector_core` only.

### A.4 Exact sequencing

- Relative to **PR #189**: independent — does not block PR #189's merge (§A.2).
- Relative to **SEC-2**: SEC-2 may merge before or after Theme D's fix; however, sequencing Theme D's implementation **after** SEC-2 merges is recommended so the new access-control logic is built once against the final two-role group names (`group_shopify_connector_user`/`group_shopify_connector_admin`) rather than the four legacy groups and needing rework.
- Relative to **U1**: no blocking dependency; U1's contract inventory §8 should record the open gap as a documented caveat, not a U1 implementation blocker.
- **Hard gate:** must be `Resolved` (fixed, tested, independently reviewed, merged) before external UAT begins and before MVP release-candidate acceptance (§A.2).

### A.5 Exact company-resolution architecture

**Recommendation (frozen), grounded in official Odoo 19 source** (`odoo/addons/base/models/ir_attachment.py`, `19.0` branch, `https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/ir_attachment.py` — Accessible, fetched 2026-07-23) — the exact precedent for a genuinely non-ORM-traversable polymorphic `res_model`/`res_id` reference:

Odoo core's own answer for this shape (`ir.attachment`, which has the identical `res_model` Char + `res_id` reference pattern) is **not** a stored/related `company_id` field feeding a plain `ir.rule` (the approach used elsewhere in this repo for typed relations, e.g. `account.move.line.company_id related='move_id.company_id'`, `https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_move_line.py` — Accessible). It is a **`_check_access`/`_search` ORM-method override that delegates to the access rules of the record the polymorphic reference actually points to.**

Frozen design for `shopify.connector.job`/`shopify.connector.mutation.attempt` (future SEC-3 task, not implemented by this session):

1. **Owning module:** `shopify_connector_core` only (both models live there).
2. **Mechanism:** override `shopify.connector.job._check_access(operation)` (and `_search`, mirroring `ir_attachment.py`'s pattern) so that, when `res_model`/`res_id` are both set, visibility/write access is resolved by delegating to `self.env[job.res_model].browse(job.res_id)._filtered_access(operation)` on the **referenced record** — i.e. a job about a `stock.picking` (or `fulfillment.binding`, etc.) is visible/writable exactly when that picking/binding itself would be, which already carries correct company scoping via its own `ir.rule`s (per the fulfillment addon's existing `fulfillment_binding_company_rule` pattern). `shopify.connector.mutation.attempt` delegates the identical check through its `job_id` relation (`self.job_id._check_access(operation)` or equivalent), since a mutation attempt has no independent target — it is always scoped 1:1 to its owning job.
3. **Target-less job types** (e.g. `core_readiness_check`/`core_test_connection`, TD-001) have no `res_model`/`res_id` to delegate to; these already require the connector-admin boundary (per U0's AR-077 correction) — the frozen fallback is to restrict target-less job visibility/action to `group_shopify_connector_admin` (or its SEC-2 successor) only, rather than inventing a new company field on `shopify.connector.store`.
4. **Explicitly rejected for this case:** adding a stored/related `company_id` field directly on `job`/`mutation_attempt` — there is no single ORM-traversable relation to derive it from (the referenced model varies per row), so a single related field cannot express it; this would require either a fragile per-`res_model` computed dispatch or duplicating company data, neither of which matches Odoo's own precedent for this exact shape.

---

## Decision B — Theme I / F-4: location cross-check mechanism

### B.1–B.4 Frozen mechanism

**Fact (DEC-011, verbatim, lines 285–289):** *"The exact mechanism by which `shopify_connector_fulfillment` confirms a picking's source location against the Shopify fulfillment location... — the ownership principle is clarified above... the exact confirmation mechanism is a Master Blueprint item."* **Fact (DEC-038 Q3-RULED, verbatim):** *"Fulfillment remains independent of `shopify_connector_inventory` and never reads `location.mapping`. It may own a read-only Shopify-location refresh service inside the fulfillment addon that upserts the core `shopify.connector.location` cache through sanctioned code. Missing/ambiguous location identity fails closed (`ambiguous_match` review)."*

**Fact (current code, confirmed):** `_resolve_single_location`/`_refresh_location_cache` (`shopify_connector_fulfillment_reader.py:355-418`) already implement the Q3-RULED half of this — they read/write the **core** `shopify.connector.location` cache (Shopify GID + name + active + last-synced **only**, no Odoo-location field at all) and never touch `shopify.connector.location.mapping` (inventory-owned, `odoo_location_id` ↔ Shopify GID). This closes "is the Shopify location itself resolvable/active/unambiguous" (Theme I's `F-6`, already authorized). **It does not, and structurally cannot, answer "does this Shopify location correspond to the Odoo picking's source warehouse"** — that answer only exists in inventory's `location.mapping` table, which fulfillment is forbidden to read, and which core's `shopify.connector.location` cache has no field to hold.

**Frozen owning module / seam (Recommendation):**
- `shopify_connector_core` defines a new extension-point method on the **existing** `shopify.connector.location` model fulfillment already reads: `_resolve_odoo_location(store, shopify_location_gid)`. Core's own base implementation returns `False` (no mapping concept exists in core) — a safe, fail-closed default.
- `shopify_connector_inventory` (which already depends on `shopify_connector_core` and owns `location.mapping`) **overrides** this method (`_inherit = 'shopify.connector.location'`) to look up `shopify.connector.location.mapping` for the given `(store, shopify_location_gid)` pair and return the matched `odoo_location_id`, or `False` if unmapped, ambiguous, or `push_enabled=False`.
- `shopify_connector_fulfillment` **only ever calls the core-defined method name** — exactly as it already does for `shopify.connector.location` — never imports or reads `shopify.connector.location.mapping`, and needs **no new manifest dependency** (`shopify_connector_inventory` stays absent from `shopify_connector_fulfillment/__manifest__.py`; the override loads via ordinary Odoo model inheritance if `shopify_connector_inventory` is installed in the same database).

This precedent-matches the repo's own already-cataloged "sanctioned integration points" (`final-mvp-module-and-dependency-architecture.md` §7: `_get_checks()` readiness-append seam, `_get_handlers()` dispatch seam, `job.enqueue.enqueue()`) — a core-owned extension point a sibling domain module implements, called by name, never by direct cross-domain model read. It satisfies DEC-008/DEC-038's prohibition exactly (fulfillment never depends on inventory, never reads `location.mapping`) while finally closing DEC-011's "Master Blueprint" open item. An earlier "reuse existing location-mapping data" naive remedy is correctly rejected by the synthesis (violates the forbidden-dependency rule); a **new, fulfillment-owned duplicate mapping** is also rejected here — it would create a second, divergence-prone source of truth for the same Odoo-location↔Shopify-location pairing DEC-010/DEC-011 already established as inventory's single canonical table.

- **Inputs:** `store` (recordset), `shopify_location_gid` (str). **Output:** an `odoo_location_id` (int) or `False`.
- **Behavior when absent/ambiguous:** fail closed. The caller (`_c8_location` in `shopify_connector_fulfillment_mode2.py`) must treat `False`/absence as "cannot cross-check" and route to review. **Frozen review-reason choice:** reuse the existing `location_unmapped` value (`REVIEW_REASON_SELECTION` #8, `inbound_evidence.py:30`) — its existing meaning ("the resolved Shopify location doesn't correspond to a known Odoo mapping") already fits precisely; **no new selection value is required or authorized** for F-4.

### B.5 Where the correction belongs — split disposition

**The permanent core+inventory interface (§B above) cannot be implemented inside PR #189** — it touches `shopify_connector_core` and `shopify_connector_inventory`, both outside PR #189's allowed-files list (`addons/shopify_connector_fulfillment/**` only). It requires a **separate, control-room-authorized prerequisite/follow-up task**, on the same footing as Theme D (§A.3) — tracked as its own future work item, not folded into PR #189 or SEC-2.

**However**, the control-room ruling (comment `5059969776`) states *"PR #189 cannot reach final acceptance while a required mutation-safety condition is knowingly unresolved"* — Condition 8 is a named required MVP item (DEC-038 matrix row 8). Today's code doesn't even attempt the warehouse cross-check: `_c8_location` (`shopify_connector_fulfillment_mode2.py:172-186`) resolves the Shopify location and returns success unconditionally once resolution succeeds — it silently omits Condition 8's full contract rather than failing closed.

**Frozen interim correction, authorized inside PR #189's own correction batch** (extends Theme I, entirely within `addons/shopify_connector_fulfillment/**`, no new dependency): until the permanent interface (§B) lands, `_c8_location` must **explicitly fail closed on the warehouse-cross-check dimension** — i.e. treat "no cross-check mechanism available yet" the same as "unmapped," always routing to `location_unmapped` review rather than silently proceeding. This means Mode 2 cannot auto-validate the location dimension of *any* fulfillment until the permanent interface exists — conservative, but it resolves Condition 8 (rather than leaving it silently unimplemented), satisfies the fail-closed contract DEC-038 Q3 already mandates for missing/ambiguous location identity, and is fully implementable inside PR #189's existing scope. **This interim behavior change is hereby added to PR #189's correction batch as an extension of Theme I** (see the locked-prompt update, below).

### B.6 Exact tests required

- Unit test proving `_c8_location` now always fails closed to `location_unmapped` (interim behavior) even when the Shopify location resolves successfully and is active — i.e. Condition 8 never silently passes.
- Once the permanent interface (§B) lands (future task): a core-level test proving the base `_resolve_odoo_location` returns `False`; an inventory-level test proving the override returns the correct `odoo_location_id` for a mapped, `push_enabled=True` pair and `False` for unmapped/ambiguous/`push_enabled=False` pairs; a fulfillment-level regression test proving `_c8_location` now passes for a correctly-mapped store/location and still fails closed for an unmapped one.

---

## Decision C — Theme H: review-reason contract

### C.1–C.8 Frozen value

**Fact (collision check, confirmed by repo-wide grep):** the string `external_fulfillment_observed` has **zero** matches anywhere in the repository today — no collision with any of the 20 current `REVIEW_REASON_SELECTION` values, `ORIGIN_CLASS_SELECTION`, `RECONCILED_STATE_SELECTION`, or core's `ERROR_CLASS_SELECTION`/`MANUAL_REVIEW_SUBREASON_SELECTION`/`JOB_STATE_SELECTION`. It follows the existing affirmative/descriptive naming family already used by `carrier_would_book`/`delivered_not_validated`/`cancelled_after_validation` (distinct from the fail-condition family used by the 16 Mode-2-checklist reasons).

1. **Exact code value (frozen):** `external_fulfillment_observed`.
2. **Exact operator label (frozen):** `External Fulfillment Observed` (Title Case, matching the existing convention, e.g. `remote_state_changed` → "Remote State Changed").
3. **Exact definition (frozen):** the review case opened when the connector, under Mode 1 (or Mode 2 evaluation not applicable), observes a confirmed-external Shopify fulfillment for the first time — the routine, everyday "merchant fulfilled in Shopify admin" baseline event — with zero Odoo stock modification. Distinct from `remote_state_changed` (Condition 14's narrow "a live second-read detected the fulfillment changed/vanished between observation and application" failure, evaluated only inside the Mode-2 engine) and from `mode_not_enabled` (Condition 16's "Mode 2 was attempted but is disabled/suspended" failure) — confirmed as two independently-wired, semantically distinct, already-correct values that must not be reused (reusing `mode_not_enabled`, the reviewer's own rejected alternative, would create a second collision, confirmed by direct code read: `mode2.py:39,70,295-296` wire it exclusively to Condition 16).
4. **Exact Mode-1 trigger condition (frozen):** `_route_observation` (`shopify_connector_fulfillment_inbound.py:173-179`), the final branch — reached when `origin_class != 'connector'`, `evidence.reconciled_state not in ('acknowledged', 'applied')`, and not `(mode == 'mode2' and origin_confirmed)`. Within that branch, the ternary at line 177-178 currently writes `'origin_unconfirmed' if not origin_confirmed else 'remote_state_changed'`; it must become `'origin_unconfirmed' if not origin_confirmed else 'external_fulfillment_observed'`. This is the sole production write site to change.
5. **Exact UAT mapping (frozen):** `docs/05-qa/fulfillment-mode-uat-matrix.md` UAT-FM-1.6 currently names no `review_reason` code at all (confirmed by full read); it must be annotated, non-destructively and classified `[Proposed product decision]` (per the locked-candidate prompt's existing plan), to state the exact expected value: `external_fulfillment_observed`. (Not edited by this session — outside this session's allowed-files list; the value is frozen here for the future correction session to apply.)
6. **Exact impact on the review-reason count (frozen):** current count is **20** (independently re-verified by full repo-wide grep, confirming the figure the U1 contract inventory is reported to cite). This correction does not remove `remote_state_changed` (it remains Condition 14's correct value) — it stops **misusing** it for the Mode-1 case and adds one genuinely new value. **Post-correction count: 21.**
7. **Exact PR #194 reconciliation requirement (frozen):** PR #194's contract inventory §5.4 (not accessible from this checkout — lives only on PR #194's separate head `b38e6874c45559dbf1219cfaec43f05ba5fc959a`) must be re-derived, not assumed, once this correction lands: update "20 values, exact" to 21, adding `external_fulfillment_observed` with its own badge/label mapping. This sharpens (names the exact new value for) reconciliation-checklist item 3 already present in `wave-4-tier1-correction-synthesis.md` §4.
8. **Whether existing pre-RC rows require backfill (frozen):** **No — not a blocking condition.** No live merchant data exists pre-RC/UAT (per issue #185/CV-013's gating framing, consistent across this program). A low-urgency follow-up note (already present in the synthesis) is preserved: any already-persisted `remote_state_changed` rows that were actually routine Mode-1 observations remain mislabeled unless a future data backfill relabels them — not a blocker for this correction.

---

## Decision D — Theme A: transaction-recovery architecture

### D.1 Savepoint ownership: **centralized inside `_enqueue_once`**

**Fact:** `_enqueue_once` is defined exactly once (`shopify_connector_fulfillment_admission.py:102-134`, on the shared abstract model `shopify.connector.fulfillment.service`), inherited by every file in the addon — not duplicated. All 8 production call sites (`stock_picking.py:24,49`; `shopify_connector_fulfillment_admission.py:62,78,206,232`; `shopify_connector_fulfillment_scans.py:58,211,248`; `shopify_connector_fulfillment_inbound.py:167`) resolve to this one implementation.

**Frozen (Recommendation):** the savepoint, catch, and re-verify logic is owned **centrally, inside `_enqueue_once` itself** — not duplicated at each of the 8 call sites. This is both DRY and precedent-consistent: the codebase's own best existing precedent for this exact problem shape, `shopify_connector_inventory_service.py::_try_enqueue_push_sync` (lines 934-1018), centralizes pre-check + `with self.env.cr.savepoint():` + narrow catch + re-verify in one function that all its callers share, rather than requiring each caller to know the exact constraint name/message. Caller-owned savepoints would require the 8 sites to duplicate that knowledge and risk drifting out of sync.

**Official-source confirmation** (Odoo 19.0 Coding Guidelines, `https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#avoid-catching-exceptions` — Accessible, and `odoo/sql_db.py` `Savepoint`/`BaseCursor.savepoint`, `https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/sql_db.py` — Accessible, both fetched 2026-07-23): `cr.savepoint()`'s `__exit__` never suppresses an exception — it only issues `ROLLBACK TO SAVEPOINT` (or `RELEASE SAVEPOINT` on success) and lets the exception propagate. The canonical official pattern is `try: / with self.env.cr.savepoint(): / except ...:` — the `except` wraps the **whole** `with` statement, never catches inside the block body (catching inside would attempt further SQL on an aborted (sub)transaction). `_enqueue_once`'s new body must follow this exact shape.

### D.2 Exact database exception classes handled

**Frozen:** the identical exception tuple already used by the established precedent — `_enqueue_once` must mirror `_try_enqueue_push_sync`'s `except (ValidationError, IntegrityError) as exc:` exactly (same import source already used in `shopify_connector_inventory_service.py`), not invent a new exception surface. Any exception outside this tuple propagates untouched (§D.7).

### D.3 Exact uniqueness constraint(s) treated as idempotent collision

**Frozen:** `_store_operation_scope_key_uniq` — `UNIQUE(store_id, operation_scope_key)` on `shopify.connector.job` (`shopify_connector_job.py:254-257`) — the same core constraint the inventory precedent already matches by its two named constants (friendly `models.Constraint` message + raw psycopg2 constraint name, because "Odoo only substitutes the friendly text at the HTTP boundary, not inside an inline savepoint flush"). Because `shopify_connector_fulfillment` has no dependency on `shopify_connector_inventory` (DEC-008) and must not gain one for this, **fulfillment must declare its own local copies of these two constant strings** (identical values, independently declared) rather than importing them from the inventory addon. This is flagged as a minor, non-blocking, follow-up-candidate technical-debt item (moving the two constants to `shopify_connector_job.py` in core so every domain imports one canonical copy) — not itself required for this correction and not a re-introduction of any rejected approach.

### D.4 Required re-search behavior after rollback to savepoint

**Frozen:** after the guarded block raises and is caught, `_enqueue_once` must perform a **fresh** re-search (post-rollback) for the existing non-terminal job on the same `(store_id, operation_scope_key)` pair — mirroring the precedent's independent re-verification — before treating the collision as benign.

### D.5 Behavior when the existing row is found

**Frozen:** return the found existing job (idempotent success) — the caller's actual intent ("ensure exactly one job exists for this operation") is satisfied without creating a duplicate.

### D.6 Behavior when the collision is not the expected idempotency constraint

**Frozen:** if the caught exception's message/constraint name doesn't match §D.3's constants, or the re-search (§D.4) finds nothing, **unconditionally re-raise** the original exception — never silently swallow an unexplained collision.

### D.7 Behavior for non-integrity exceptions

**Frozen:** any exception outside the §D.2 tuple must propagate untouched — `_enqueue_once` must not wrap the savepoint block in a broad `except Exception`.

### D.8 Caller-side broad `except Exception` blocks: **narrowed, not removed**

**Fact:** `stock_picking.py`'s two call sites (`_action_done()` override lines 24-36; `write()` override lines 49-67) each wrap their **entire method body** — not just the enqueue call — in a bare `except Exception: _logger.exception(...)`, silently swallowing everything including a raw `IntegrityError`.

**Frozen:** because `_enqueue_once` will now handle its own known collision internally (§D.1-D.7) and only re-raise genuinely unexpected errors, the caller-side catches no longer need to defend against the routine collision case at all. They must be **narrowed**, not removed entirely (removing them would let a genuinely unrelated admission-hook failure block the foreground picking write/validation — a separate resilience property this connector's design otherwise preserves): the bare `except Exception` must stop being the mechanism that can silently absorb an operation-scope-key collision, and any exception it does still catch must be escalated visibly (at minimum, the existing `_logger.exception` plus a durable, operator-discoverable trace — e.g. a job/log row or equivalent — not a log line alone). **Binding boundary for the implementer:** after this correction, the outer catch must never again be capable of silently absorbing a `UNIQUE(store_id, operation_scope_key)` collision, and must not swallow any exception with zero operator-visible trace. The exact mechanism (a narrower exception class vs. the same broad catch plus mandatory escalation) is left to the implementer within that boundary.

### D.9 How `stock.picking.write`/`_action_done` remain transactionally usable

**Frozen:** because the savepoint now lives inside `_enqueue_once`, scoped only around the job-creation attempt (§D.1), a caught/recovered collision rolls back only that inner savepoint. The enclosing `write()`/`_action_done()` transaction — including the picking's own already-applied field writes earlier in the same transaction — remains valid and commits normally. This directly resolves P0-A: the caller's own prior work is no longer discarded by an unrelated job-creation collision.

### D.10 How the operation-scope-key correction interacts with collision recovery

**Frozen:** independent concerns, sequenced together only for merge-conflict avoidance (both touch `shopify_connector_fulfillment_scans.py`, per the synthesis §3). The scope-key widening (job-type-prefixing the two scan job types, matching the addon's existing Q1 override pattern for the two mutation types) reduces **spurious** collisions between job types that should never have collided; the savepoint/catch mechanism (§D.1-D.9) safely handles **any** collision that still legitimately occurs (including genuine concurrent races) once that widening is in place. Neither depends on the other's internal logic.

### D.11 Exact stored-field recomputation/backfill method

**Fact:** `operation_scope_key` is a stored computed field (`shopify_connector_job.py:722-748`); an Odoo upgrade does not automatically recompute already-stored values for untouched existing rows.

**Frozen:** a companion, idempotent (safe-to-rerun) recompute step for pre-existing non-terminal rows of the two affected job types (`fulfillment_reconciliation_check`, `fulfillment_mode_switch_scan`) — search `shopify.connector.job` for those `job_type`s with `state not in TERMINAL_JOB_STATES`, force a recompute of `operation_scope_key` via the ORM's standard stored-compute-field recompute mechanism. Given no live merchant/production data exists pre-RC/UAT, today's operational blast radius is near-zero, but the mechanism and its test (a pre-fix-shaped fixture row proving the recompute step corrects it) are still required so the fix is not inert whenever real data exists by RC time.

### D.12 Sequential and concurrent tests

- **Sequential:** two back-to-back `write()` calls admitting tracking-admission on the same picking while the first job is still non-terminal — the **second** write's own picking-field change must persist (not be discarded).
- **Sequential:** a duplicate `_action_done()`-triggered picking-admission enqueue collision — `_action_done()`'s own state transition must complete normally.
- **Concurrent** (extending the existing genuine two-cursor/two-process pattern already proven by `test_fulfillment_concurrency.py`/the runtime harness): two genuinely concurrent processes both attempt `_enqueue_once` for the identical `(store_id, operation_scope_key)` — exactly one wins the `UNIQUE` constraint at the DB level; the loser recovers via §D.4-D.6 and returns the winner's job; the constraint's cross-process guarantee is unchanged (still refuses a truly concurrent duplicate row).
- **Negative:** the cron-batch call sites (`_handle_fulfillment_reconciliation_check`, `_cron_enqueue_reconciliation_checks`) must prove one store's collision does not abort the batch's processing of other stores.
- **Negative:** `action_start_mode2_switch` (admin-facing) must prove a collision returns/raises a well-classified, UI-presentable error, never a raw psycopg2 traceback.

---

## Locked-prompt normalization (applied to `wave-4-tier1-correction-locked-candidate.md` in this same commit)

- Base/expected-head language now names the exact SHAs from this document's header, distinguishing the prior findings-synthesis head from this decision-lock's own new head.
- Theme A's acceptance criterion is corrected from "all 8 call sites are savepoint-wrapped" to "the single, centrally-shared `_enqueue_once` implementation is savepoint/catch/re-verify-wrapped once, automatically covering all 8 production call sites" (§D.1), plus the caller-side narrowing requirement (§D.8).
- Theme I gains a new, explicitly authorized sub-item: the F-4 **interim** fail-closed correction to `_c8_location` (§B.5) — implementable inside PR #189's existing allowed-files. The **permanent** core+inventory interface (§B.1-B.4) remains explicitly NOT authorized for this PR, unchanged from the prior prompt, now with its exact target architecture on record for the future prerequisite task.
- Theme H's correction boundary now names the frozen exact value (`external_fulfillment_observed`) and label, removing the "exact string is a product-owner naming decision" placeholder.
- A new "Explicitly NOT authorized — Theme D" entry restates §A.3/A.5's disposition (future SEC-3 task, core-scoped) and the merge/UAT/RC gate from §A.2, so the implementing session cannot silently defer Theme D without citing this record.
- Static-checks section gains: "no re-introduction of the duplicated-constant technical debt beyond the two named strings (§D.3)"; "F-4 interim fail-closed behavior verified never to pass Condition 8 without real cross-check evidence."

---

## Documentation normalization (applied in this same commit)

- `wave-4-tier1-synthesis-handoff.md`: "Confirmed with reclassification | 4" corrected to **5** (`P1-1`, `F-5`, `P1-7`, `F-4`, `F-7`) with "Confirmed (as-is)" corrected from 20 to **19** (24 total − 5 reclassified = 19; independently re-verified line-by-line against the ledger's own 24 disposition entries in this session).
- Any "11 of 13 themes immediately correctable" wording is preserved as accurate for the *original* correction batch, with a note that Theme I now additionally carries the F-4 interim fail-closed item (§B.5) as an explicit extension, not a 12th/13th theme.
- Any statement that Theme D automatically does not block PR #189 is corrected to state the affirmative merge/UAT/RC gate from §A.2 (it does not block *merge*; it does block UAT and RC).
- Any statement that F-4 may remain unresolved at final Wave 4 acceptance is corrected: F-4 is resolved for final-acceptance purposes by the interim fail-closed behavior (§B.5); only the *permanent* interface remains open, tracked separately.
- Prior/current head references updated to name this decision-lock's exact new head alongside the prior synthesis head `d3c157c1d4c369c1880fffc69ee6b4801ab9c05c`.

---

## Final future-implementation-theme count (reconciliation)

- **Correctable inside PR #189's existing/extended correction batch:** the original 11 fully-correctable themes (A, B, C, E, F, G, H, I[`F-6`], J, K, M) **plus** Theme I's new F-4-interim fail-closed extension (§B.5) — 11 themes fully, a 12th (I) doubly.
- **Requiring separate, future, control-room-authorized work — not part of PR #189:**
  1. **Theme D** — `shopify.connector.job`/`.mutation.attempt` multi-company access-control hardening (§A; candidate "SEC-3", core-scoped DEC).
  2. **Theme L** — U0 dashboard job-type labels (unchanged from the prior synthesis; `shopify_connector_core`, forbidden for Wave 4).
  3. **F-4 permanent architecture** — the core `shopify.connector.location._resolve_odoo_location()` seam + inventory override (§B.1-B.4; touches `shopify_connector_core` and `shopify_connector_inventory`).

Three future work items, down from the prior synthesis's "2 fully + 1 partially" framing — the partial item (F-4) now has a fully-specified split disposition (interim in-PR fix + permanent future item) rather than remaining open-ended.

---

## Remaining control-room decisions

1. Accept, revise, or reject this decision-lock's four frozen dispositions (A–D above).
2. Accept the locked-prompt and documentation normalizations applied in this commit.
3. Authorize (or decline) a future implementation session to execute the now-normalized `wave-4-tier1-correction-locked-candidate.md` — **this decision-lock does not itself authorize implementation.**
4. Separately authorize the three future work items in the reconciliation table above (each needs its own control-room-scoped task/DEC).

**This document's own recommendation:** `WAVE 4 DECISION LOCK COMPLETE — READY FOR CONTROL-ROOM IMPLEMENTATION AUTHORIZATION`. No implementation occurred. No Shopify operation occurred. No `addons/**` file was touched.
