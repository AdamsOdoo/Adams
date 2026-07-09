# Task 010 — Product-Domain Implementation Gate: Opening Proposal

> **Status: Accepted by ChatGPT.** Accepted via PR #137 control-room
> review, GitHub comment ID `4926437491`. **This acceptance opens the
> product-domain implementation gate for exactly one future implementation
> session — Task 010 only — effective once this PR merges into
> `Shopify-connector`.** Prepared after PR #136 merged (MBQ-55
> product-template/product-variant portion accepted; product-domain gate
> criteria accepted, as criteria only — control-room comment ID
> `4924917266`), against `Shopify-connector` tip
> `c171d8f9b404f0b9bc066ee6fbef811086f5d0fc`. This document performs the
> distinct, explicit ChatGPT act
> [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
> §4 required before the product-domain implementation gate could open.
> **This acceptance does not authorize Task 010 code to be written now.**
> Task 010 implementation still requires, in order: (1) this PR merging
> into `Shopify-connector`; (2) ChatGPT explicitly pasting/issuing the
> referenced final implementation prompt, verbatim, into a **new** Claude
> Code session, as its own later chat turn — not performed by this
> acceptance. **The gate closes again the moment the future Task 010
> implementation PR is opened as draft** (§9) — this acceptance authorizes
> exactly that one session, not a standing mandate for further
> product-domain work, and does not authorize Task 011/012/013/014, Task
> 015, any UI, webhook, OAuth, or Lite/Full packaging work.

> **Revision note (2026-07-09, PR #137 control-room review, GitHub comment
> ID `4925370944`) — REVISE before merge.** ChatGPT's decision: this
> proposal and its referenced final prompt require revision before merge;
> not marked ready, not merged, Task 010 not authorized, product-domain
> gate not opened. Five precision gaps in the referenced final prompt were
> identified and fixed in this revision (manifest dependency; exact field
> types; explicit `_name`/`_inherit` declarations; a required
> product-domain enablement gating seam; tests proving that gating) — see
> the final prompt's own revision note for detail. §3 below is updated so
> criteria 3/4/5/9/12 are claimed satisfied only against the **revised**
> final prompt, not the original draft. This document's own status remains
> **Proposed / Under review, not accepted** — this revision does not open
> the gate and does not authorize any code.

> **Acceptance note (2026-07-09, PR #137 control-room review, GitHub
> comment ID `4926437491`) — Content accepted.** ChatGPT confirmed every
> precision gap from the prior REVISE (comment `4925370944`) fixed —
> manifest dependency, exact field types, `_name`/`_inherit` declarations,
> the product-domain enablement gating seam, and the tests covering it —
> and confirmed no addon/code/test/manifest/XML/security/migration/CI/
> domain/UI/webhook/OAuth file was changed. **Decision: content accepted;
> a final status patch (this note and §1/§9 below) is required before
> merge.** This patch does not itself merge PR #137, does not mark it
> ready, does not implement Task 010, and does not issue the final prompt
> — issuance remains ChatGPT's own separate, later chat turn, after this
> PR merges.

## 1. Status

**Accepted by ChatGPT.** Accepted via PR #137 control-room review, GitHub
comment ID `4926437491`.

- **This acceptance opens the product-domain implementation gate for
  exactly one future implementation session: Task 010 only** — effective
  once this PR merges into `Shopify-connector` (mirroring the AR-029/
  AR-031 "gate opens only once this PR merges" pattern).
- **The gate closes again the moment the future Task 010 implementation
  PR is opened as draft** (§9) — not a standing mandate for further
  product-domain work.
- **The future Task 010 implementation PR must remain draft until
  ChatGPT reviews it.**
- **This does not authorize any other product-domain task** — not Task
  011 (customer import/matching), Task 012 (order import), Task 013
  (inventory sync), Task 014 (fulfillment/tracking), Task 015 (product
  write/export, not yet even proposed at task-spec precision), any UI
  work, any webhook, any OAuth/token-acquisition work, or any Lite/Full
  packaging work.
- **This acceptance does not, by itself, authorize any Task 010 code to
  be written.** The referenced final implementation prompt
  ([`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md))
  is **Accepted final prompt / Not issued** — Claude must not use it
  until ChatGPT explicitly pastes/issues it, verbatim, into a **new**
  Claude Code session, as its own later chat turn, after this PR merges.
- Does not mark any criterion in
  [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
  §3 as satisfied beyond what §3 below already evidences — this
  acceptance confirms that evidence, it does not restate or expand it.

## 2. Purpose

Propose opening **exactly one** future implementation session — Task 010 —
mirroring the two-step decision-closure-then-gate-opening-act pattern
already used for Task 002 (AR-025→AR-026), Task 003 (AR-027/028→AR-029),
and Task 006C (AR-030→AR-031). This proposal is the gate-opening-act
candidate; ChatGPT's acceptance of it, specifically, is the "distinct,
future, explicit ChatGPT gate-opening act" that
[`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
§4 requires. Nothing in this document performs that act itself.

## 3. Gate-criteria satisfaction evidence

Evaluated against
[`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
§3's twelve criteria. Criteria 1, 2, 6, 7, 8, 10, and 11 were already
satisfied before this session (unchanged by it, restated below for
completeness). Criteria 3, 4, 5, 9, and 12 were **not yet satisfied**
before this session; this section states, for each, what this session did
and why it is now satisfied.

**Per control-room review (comment ID `4925370944`): criteria 3, 4, 5, 9,
and 12 may be claimed satisfied only once all five of the following
precision preconditions hold in the referenced final prompt — all five now
do, as of this revision:**

1. ✅ The future manifest's `depends` is exact: `['shopify_connector_core',
   'product']` (final prompt §3).
2. ✅ Every field type is exact: `fields.Text`/`fields.Float`, no "Char or
   Text"/"Monetary or Float" ambiguity, no unauthorized `Monetary`/currency
   field (final prompt §7.2).
3. ✅ Both concrete binding models explicitly declare `_name` **and**
   `_inherit` (final prompt §7.1/§7.2).
4. ✅ The product-domain enablement gating seam is exact: a
   `_domain_flag_for_job_type()` override mapping `product_import_sync` to
   the already-existing `product_domain_enabled` flag, preserving
   `super()` for every other `job_type`, declared inside the one allowed
   importer file, zero `shopify_connector_core` edits (final prompt §9).
5. ✅ Tests cover product-domain gating: cannot-start-when-disabled,
   cannot-start-when-settings-missing, can-start-when-enabled, and
   `core_dispatch_selftest` preservation (final prompt §10).

| # | Criterion | Satisfied before this session? | Satisfied by this session? | Evidence | Remaining risk |
| --- | --- | --- | --- | --- | --- |
| 1 | PR #135 merged and conclusions accepted | Yes | Unchanged | `pull_request_read` confirms PR #135 `merged: true`; AR-033 Accepted | None — a standing fact |
| 2 | MBQ-55 product-template/variant portion accepted/closed | Yes | Unchanged | PR #136 acceptance, comment ID `4924917266` | None for this portion; customer/order portions remain separately open (unaffected) |
| 3 | Final prompt has exact file/model/field names | No | **Yes** | [`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md) §3, §7 fixes exact model names (`shopify.connector.product.template.binding`, `shopify.connector.product.variant.binding`), each with an explicit `_name`/`_inherit` declaration; exact file names; the exact manifest dependency (`['shopify_connector_core', 'product']`); and the exact field list with exact Odoo field types (`fields.Text`/`fields.Float`, no ambiguous choices, no unauthorized `Monetary`), all converted from the accepted MBQ-55 proposal without re-deriving it — **precision gaps found and fixed on control-room review, comment ID `4925370944`** | Low — the prompt is drafted, not yet exercised by an implementation session; a future session could still discover a field gap during coding, per §8 below |
| 4 | Exact allowed/forbidden files defined | No | **Yes** | Final prompt §3 (allowed, exact list) and §4 (forbidden, exact list — now naming all **three** narrow `shopify_connector_core` extension seams exactly, not two, per the control-room-review fix) | Low — same as criterion 3; the implementing session must still self-audit its own diff against this exact list |
| 5 | Dedup thresholds fixed or explicitly scoped as in-task decision | No | **Yes** | Final prompt §8 fixes exact MVP thresholds (existing binding / single-candidate SKU-or-barcode / confident no-match / ambiguous / blind), explicitly grounded in the already-accepted DEC-014 point H two-tier gate — not a new architecture decision, a narrow conversion of an already-accepted policy into exact MVP numbers/conditions | Low — thresholds are conservative by design (ambiguous and blind both route to manual review, never create); a future session could still find the "single-candidate" rule too strict or too loose once exercised against real data, which is why VAL-B2 remains explicitly out of this task's scope (§6 below) |
| 6 | No export/update scope | Yes | Unchanged | `task-010-product-import-proposed.md`, ChatGPT REVISE on PR #93; restated in final prompt §4/§6 | None — standing requirement, restated not weakened |
| 7 | No customer/order/inventory/fulfillment scope | Yes | Unchanged | Same source; restated in final prompt §4/§6 | None |
| 8 | No UI/wizard/webhook/OAuth scope | Yes | Unchanged | Same source; restated in final prompt §4/§6 | None — Matching Center (S6) UI remains separately gated and out of this task's scope |
| 9 | Tests defined | No | **Yes** | Final prompt §10 confirms the four MBQ-55-proposed test file names and names the exact test cases within each, mapped to every acceptance criterion in `task-010-product-import-proposed.md` — **now including the required product-domain gating tests added on control-room review** (cannot-start-when-disabled; cannot-start-when-settings-missing; can-start-when-enabled; `core_dispatch_selftest` preservation), placed inside the existing `test_product_import_matching.py`, no new test file added | Low — test *names* are fixed; a future session could still need to add narrowly-scoped test helper code within an allowed file, which the final prompt's allowed-files list already accommodates |
| 10 | Rollback plan defined | Yes | Unchanged | `task-010-product-import-proposed.md` §Rollback; restated in final prompt §13 | None |
| 11 | Runtime/live-Shopify dependency explicitly stated as absent/controlled | Yes | Unchanged | `task-010-product-import-proposed.md`; restated in final prompt §6/§11/§12 | None |
| 12 | Open blockers listed and reconfirmed as non-blocking for Task 010 | No | **Yes** | §7 below performs the point-in-time reconfirmation this criterion requires, against `master-implementation-readiness-checkpoint.md`'s existing blocker-classification table — no new blocker discovered, no existing blocker's classification silently changed | See §7 — one item (checkpoint/resume ownership) required more than a restatement; see below |

**No criterion in 3/4/5/9/12 was found unsatisfiable by this session's own
docs-drafting act.** All five are now satisfied by the artifacts this
session produced. This proposal is therefore drafted; had any of the five
been unsatisfiable by documentation work alone, this session would have
stopped before drafting this proposal, per its own governing instructions.

## 4. Final prompt reference

[`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md) —
**Accepted final prompt / Not issued** (PR #137 control-room review,
comment ID `4926437491` — the same acceptance recorded in §1 above). Still
marked "DO NOT USE THIS PROMPT UNTIL CHATGPT ACCEPTS THE TASK 010
GATE-OPENING PROPOSAL AND EXPLICITLY ISSUES THIS PROMPT IN CHAT" at its
own top, unweakened. **This proposal's acceptance does not issue that
prompt** — issuance is ChatGPT's own separate, later chat turn, after this
PR merges.

## 5. Accepted MBQ-55 names

Per
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
(Accepted by ChatGPT, PR #136, comment ID `4924917266`, product-template/
product-variant portion only):

- **Models:** `shopify.connector.product.template.binding` (binds Shopify
  `Product` ↔ Odoo `product.template`); `shopify.connector.product.variant.binding`
  (binds Shopify `ProductVariant` ↔ Odoo `product.product`).
- **Module:** `shopify_connector_product`.
- **Model files:** `shopify_connector_product_template_binding.py`,
  `shopify_connector_product_variant_binding.py`.
- **Test files:** `test_product_template_binding.py`,
  `test_product_variant_binding.py`, `test_product_import_matching.py`,
  `test_product_duplicate_prevention.py`.
- **Security:** reuses the four existing `shopify_connector_core` groups —
  no new group.

The customer-binding and order-binding portions of MBQ-55 remain separately
open, unaddressed by this proposal.

## 6. Scope and non-scope

**Scope** (Task 010, per the final prompt §5): create
`shopify_connector_product` (depending on `shopify_connector_core` and
Odoo's own `product` module); two concrete binding models, each with an
explicit `_name`/`_inherit`, extending `shopify.connector.binding.mixin`;
a read-only importer/matching service; match-key priority existing
binding → SKU → barcode → manual review; the MBQ-59 two-tier
no-blind-create gate at the exact thresholds fixed in the final prompt
§8; one new `product_import_sync` job type registered via three seam
extensions (`selection_add`, a `_domain_flag_for_job_type()` override
gating it on the existing `product_domain_enabled` store-settings flag,
and `_get_handlers()`), all declared inside the one allowed importer file,
zero edits to `shopify_connector_core`.

**Non-scope** (final prompt §6, restated): no product export/update/write
of any kind; no `productSet`/bulk-variant mutation; no image/media sync
beyond the accepted read-only snapshot fields; no inventory quantity; no
fulfillment; no customer/order logic; no setup wizard/UI; no webhook; no
OAuth/token acquisition; no Lite/Full packaging; no live Shopify
validation; no multi-server concurrency validation.

## 7. Remaining blockers reconfirmed against Task 010's own scope

Reconfirmed, as of this proposal's date, against
`master-implementation-readiness-checkpoint.md`'s existing blocker
classification table (unchanged since PR #135/#136 — no PR touching that
table has merged since):

- **VAL-B2** (no live Shopify Admin API connection ever made) — Class D.
  **Does not block Task 010** — Task 010's own scope uses only the
  existing Task 003 API client with fake/stub tests; VAL-B2 gates live/
  production claims, not this task's backend code.
- **MBQ-05** (scalable many-unrelated-customer token-acquisition/
  distribution architecture) — Class B. **Does not block Task 010** — Task
  010 consumes an already-established store connection; it performs no
  OAuth/token-acquisition of any kind.
- **TD-002** (`read_fulfillments` readiness-scope correctness) — Class B.
  **Does not block Task 010** — unrelated to product import; depends on
  the fulfillment API model decision, a separate future domain task.
- **Fulfillment API model** (legacy `Fulfillment` vs. `FulfillmentOrder`)
  — Class B. **Does not block Task 010** — needed only for the future
  fulfillment-domain task (Task 014).
- **Lite/Full packaging** — Class B. **Does not block Task 010** — affects
  install/licensing shape, not this task's own model/logic code.
- **Multi-server concurrency proof (SRR-03/04/09)** — Class D. **Does not
  block Task 010's own diff** — Task 010 inherits the existing,
  already-merged Task 006C claim/dispatch mechanism unmodified; it neither
  worsens nor is required to resolve this pre-existing, already-tracked
  cross-cutting risk, which applies equally to every job type, not
  specifically to Task 010's.
- **Checkpoint/resume ownership (pagination-cursor ownership: core vs.
  domain)** — classified **A** in `master-implementation-readiness-checkpoint.md`
  §4 ("blocks Task 010 implementation... affects how Task 010 would
  implement multi-page product import"), with its own named resolution
  path: *"a narrow, in-task design decision inside Task 010's own final
  prompt (domain-owned cursor state)."* **This session's final prompt
  performs exactly that resolution** (final prompt §9): Task 010 is scoped
  to a single-product `product_import_sync` job type only; multi-product
  enumeration/pagination is named as a separate, narrower open point that
  the implementing session must either fix conservatively within
  `shopify_connector_product` (never a new `shopify_connector_core`
  field) or flag as its own required ChatGPT decision. This is not a
  restatement of "already non-blocking" — it is an honest record that this
  criterion was Class A and is resolved **by this session's own drafting
  act**, per the readiness checkpoint's own anticipated resolution path,
  not by a status that was already true beforehand.

**No blocker above is silently reclassified.** Six items (VAL-B2, MBQ-05,
TD-002, fulfillment API model, Lite/Full packaging, multi-server
concurrency proof) were already non-blocking for Task 010's own scope, per
the readiness checkpoint's own existing table, and remain so. One item
(checkpoint/resume ownership) required this session's own final-prompt
drafting act to move from "blocks a §9-precision prompt" to "resolved
within the final prompt, per its own already-named resolution path" — that
movement is recorded honestly here, not asserted as having already been
true.

## 8. Accepted risks and mitigations

1. **Risk:** the final prompt's exact field/model schema could still miss
   a genuine implementation-time need (e.g. a field the importer's actual
   payload-mapping code turns out to require). **Mitigation:** the final
   prompt names every field as either inherited-from-mixin, new-required,
   snapshot-only, explicitly-out-of-scope, or explicitly-deferred (per
   MBQ-55 §7) — an implementing session that finds a genuine gap must STOP
   and mark it a required ChatGPT decision (final prompt §3), not
   improvise a schema change.
2. **Risk:** the MVP dedup thresholds (final prompt §8) could prove too
   conservative (routing too much to manual review) or not conservative
   enough (a false-confident match) once exercised against real Shopify
   data. **Mitigation:** VAL-B2 remains explicitly out of Task 010's
   scope — thresholds are validated only against fake/stub payloads in
   this task; any live-data recalibration is a future, separate concern,
   not silently assumed correct here.
3. **Risk (identified on control-room review, comment ID `4925370944`,
   fixed in this revision):** the original draft registered
   `product_import_sync` via `selection_add`/`_get_handlers()` but did
   **not** wire it to the existing `_domain_flag_for_job_type()`/
   `product_domain_enabled` gate — meaning the job type would have started
   with no product-domain-enablement check at all, silently bypassing the
   same mechanism every other future domain job type is expected to use.
   **Mitigation (applied):** the final prompt §9 now requires a third seam
   extension — a `_domain_flag_for_job_type()` override mapping
   `product_import_sync` to `product_domain_enabled`, preserving `super()`
   for every other `job_type` — plus tests proving the gate actually
   blocks/allows starts correctly and that core job types are unaffected
   (final prompt §10). This is still this connector's **first** domain
   job-type registration exercising this gate in practice — some
   unforeseen interaction could still surface only at implementation or
   runtime-validation time; the final prompt continues to require zero
   edits to `shopify_connector_core` itself, and any genuine seam
   insufficiency discovered during implementation must be reported as a
   blocker, not patched into core silently.
4. **Risk:** multi-product enumeration/pagination, deliberately left out
   of this job type's scope (§7 above), could later require a core-engine
   primitive (a checkpoint/cursor field) that this proposal did not
   anticipate. **Mitigation:** the final prompt explicitly forbids adding
   such a field to `shopify_connector_core` without separate
   authorization — this is a known, named, deliberately-deferred boundary,
   not an oversight.
5. **Risk:** this gate, once opened, could be read as authorizing more
   than Task 010's own narrow scope. **Mitigation:** §9 below states the
   gate authorizes exactly one future implementation session, mirroring
   the Task 003/006C precedent, and closes again the moment that session's
   PR opens as draft.

## 9. Gate rule

- **ChatGPT has accepted this proposal** — PR #137 control-room review,
  GitHub comment ID `4926437491`. Acceptance of the criteria list
  ([`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md),
  PR #136, comment `4924917266`) was a distinct, prior act; this
  acceptance is the separate, explicit gate-opening act §4 of that
  document required — mirroring the pattern already used for AR-026 (Task
  002), AR-029 (Task 003), and AR-031 (Task 006C).
- **The product-domain implementation gate opens for exactly one future
  implementation session — Task 010 only — effective once this PR merges
  into `Shopify-connector`.** No code is authorized before that merge, and
  no code is authorized by this acceptance alone even after it — issuing
  the final prompt in a new chat turn (see §4) is still a separate,
  required, later act.
- **The gate closes again once the future Task 010 implementation PR is
  opened as draft** — mirroring AR-029's and AR-031's own closure language
  exactly. Opening the gate authorizes **exactly one** future
  implementation session — Task 010 — not a standing mandate for further
  product-domain work, and not an authorization for Task 011/012/013/014,
  Task 015, any UI, webhook, OAuth, or Lite/Full packaging work.
- **The future Task 010 implementation PR must remain draft until ChatGPT
  reviews it.** No session may mark it ready for review or merge it
  without a distinct, explicit ChatGPT review act.

---

## Evidence / references

- [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md),
  [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md) —
  both Accepted by ChatGPT, PR #136, comment ID `4924917266` — access:
  Accessible, this repository, observed 2026-07-09.
- [`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md) —
  drafted this session — access: Accessible, this repository, observed
  2026-07-09.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md)
  §4 (blocker classification table) — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`DEC-014-master-blueprint-product-customer-sale.md`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
  point H (MBQ-59 blueprint-policy acceptance) — read directly this
  session — access: Accessible, this repository, observed 2026-07-09.
- GitHub PR #135, #136 (`AdamsOdoo/Adams`) — retrieved via
  `pull_request_read` this session, confirmed `merged: true` — access:
  Accessible, 2026-07-09.
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  AR-026, AR-029, AR-031 (gate-opening-act precedent pattern) — access:
  Accessible, this repository, observed 2026-07-09.
- GitHub PR #137 comment ID `4925370944` (`AdamsOdoo/Adams`) —
  control-room REVISE decision this revision addresses — access:
  Accessible, 2026-07-09.
- `addons/shopify_connector_core/models/shopify_connector_store_settings.py` —
  read directly this revision, confirms `product_domain_enabled` already
  exists — access: Accessible, this repository, observed 2026-07-09.
- GitHub PR #137 comment ID `4926437491` (`AdamsOdoo/Adams`) —
  control-room acceptance decision this patch records — access:
  Accessible, 2026-07-09.

**Next step:** this proposal is **Accepted by ChatGPT** (comment ID
`4926437491`); the product-domain implementation gate opens for exactly
one future Task 010 implementation session once this PR merges into
`Shopify-connector`. This patch does not merge this PR. Next: ChatGPT's
final review of this status patch, then merge; after merge, ChatGPT
separately and explicitly issues the referenced final implementation
prompt in a new Claude Code session — that session's resulting PR must
remain draft until ChatGPT reviews it, and the gate closes the moment
that PR is opened as draft.
