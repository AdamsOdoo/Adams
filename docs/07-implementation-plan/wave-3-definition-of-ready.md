# Wave 3 — Definition of Ready (Inventory Synchronization: Layer 2 Stage 0 + Task 013/013B)

> **Status: GATE A CORRECTION COMPLETE — CONTROL-ROOM FINAL REVIEW PENDING;
> GATE B NOT STARTED; IMPLEMENTATION NOT AUTHORIZED (2026-07-19).**
> Originally proposed, Fable gap-closure mission, 2026-07-16; Gate A
> (DEC-031 Layer 2 architecture closure + Stage 0 packet preparation,
> PR #177) corrected this document's CAS-field and batching text on
> 2026-07-18, and the DEC-036 consolidated correction batch (2026-07-19)
> resolved every architecture item this document previously carried as
> BLOCKING — see §5. Docs-only. Acceptance authority: product owner +
> Claude control room. **Wave 3 remains unauthorized until this Definition
> of Ready is accepted and its gate decisions are Accepted. No
> implementation authorized by this document.**
>
> **Current program state (2026-07-19):** Wave 1 and **Wave 2 are both
> merged** (Wave 2: PR #176, merge commit `22bfb9a0e9b1e48b6a664351e2b321d134177110`)
> and **SRR-03 is CLOSED**. Wave 3's wave-order dependency on Wave 2 is
> **CLOSED**. DEC-031 Layer 2 remains Proposed, not Accepted —
> [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) is the
> normalized acceptance candidate, status **CONTROL-ROOM ACCEPTANCE
> CANDIDATE — CORRECTIONS APPLIED, NOT YET ACCEPTED**, with zero remaining
> architecture blockers after the final consolidated Sessions-2-and-3
> ruling (PR #177 comment
> [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)).
> As a Shopify-mutation wave, Wave 3 closure requires **genuine (not
> simulated) dev-store mutation evidence**. Wave 3 introduces **no
> PII-masking fields** (the MVP has no PII masking; inventory bindings
> carry no customer PII).

Instantiates the 7-field standard of
[`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)
at wave granularity for **Wave 3** of
[`mvp-completion-program.md`](mvp-completion-program.md) §4, layered with
[`../02-product/inventory-operating-model.md`](../02-product/inventory-operating-model.md)
and
[`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md).
It does not reopen the Task 013 (D-013-1..8) or Task 013B closures — see
the Task 013 packet's dated addendum of the same day.

## 1. Scope statement

Wave 3 = the program's **first Shopify-mutation domain**, in three
strictly ordered stages behind one wave gate:

- **Stage 0 — DEC-031 Layer 2 core substrate** (pre-feature core task; see
  §4). Nothing in Stage 1/2 may issue a mutation before Stage 0 is merged
  and runtime-proven.
- **Stage 1 — Task 013** — `shopify_connector_inventory`: location
  mapping, per-pair level bindings, first-push guard, Odoo→Shopify
  `available` push via `inventorySetQuantities`, triggers (stock-change
  hook, push-scan cron, manual), per
  [`task-013-inventory-sync-implementation-packet.md`](task-013-inventory-sync-implementation-packet.md)
  as revised by its 2026-07-16 addendum.
- **Stage 2 — Task 013B** — one-time reviewed Shopify→Odoo baseline
  import, per
  [`task-013b-initial-inventory-baseline-packet.md`](task-013b-initial-inventory-baseline-packet.md).

**Out of Wave 3 (hard):** fulfillment (Wave 4); product export (Wave 5);
UI screens (Wave 5 — first-push preview/confirm and divergence review ship
as backend service methods only); webhooks; standing Shopify→Odoo pull
(RA-020); any `committed`/`on_hand` write (RA-018); `inventoryAdjustQuantities`
delta semantics; the legacy `ignoreCompareQuantity`/`compareQuantity`
mechanism, which does not exist in the current (2026-04+) Shopify schema
— see the CAS field-name correction below; **and, per
[`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) D4 (2026-07-18),
multi-entry `quantities[]` batching of any kind** — Stage 1 defaults to one
`(inventory_item_id, location_id)` pair per mutation request until
partial-batch semantics are proven or every entry is independently
reconciled.

## 2. DoR checklist

### 2.1 Objective

Odoo-authoritative inventory synchronization (DEC-010): mapped-location
`free_qty` pushed as Shopify `available` with CAS + mandatory idempotency,
under the Layer 2 mutation-safety substrate, with a guarded one-time
baseline import — runtime- and concurrency-proven, dev-store-proven.

### 2.2 Allowed files

- **Stage 0 (core substrate — its own allowed files in core):**
  `addons/shopify_connector_core/models/` — the mutation-attempt model
  (`shopify.connector.mutation.attempt`, L2-D2), job-ownership/attempt
  wrapper seams and commit-point mechanics (L2-D13) in the dispatch/job
  files the accepted Layer 2 design names, the reconciliation framework
  (per-domain reconciliation-matrix registry + reconciliation-job
  contract), the sweep cron data file, core ACL rows for the attempt
  model, and core tests
  (attempt lifecycle, commit-point/crash-window matrix, sweep,
  concurrency). Exhaustive list fixed by the Stage 0 packet at Layer 2
  design acceptance — this DoR fixes the categories.
- **Stage 1:** the Task 013 §8 locked-prompt allowed list
  (`addons/shopify_connector_inventory/**` — models, ACL, cron, six test
  files; validation-results/AR/handoff docs), **plus** the addendum
  deltas: coalesced pending-target mechanics, CAS `changeFromQuantity`
  read→compare→set flow **[corrected 2026-07-18 — the field is
  `changeFromQuantity`, not `compareQuantity`, per Shopify Admin GraphQL
  API 2026-04+; see DEC-036 D12]**, divergence-review case records, and
  Layer-2 attempt-wrapper integration — all inside the inventory module
  except the wrapper calls into Stage 0's core API. **Batching
  ("multi-entry `quantities[]`") is superseded — corrected 2026-07-18 per
  DEC-036 D4: it is explicitly excluded from Stage 1, not merely "where
  adopted."** Two independent adversarial-review clusters converged on
  excluding it (no source confirms Shopify's per-entry `UserError`
  field-path shape or partial-batch atomicity); this DoR's prior hedge
  language is corrected to match, not left standing.
- **Stage 2:** the Task 013B §9 locked-prompt allowed list (baseline
  read/preview/apply service + tests within `shopify_connector_inventory`,
  its docs).

### 2.3 Forbidden files

Everything outside the three stage allowlists: all
`shopify_connector_product`/`shopify_connector_sale` files; core files
beyond Stage 0's own list and the two inheritance-only readiness seams
D-013-5 names; `adams_base`; fulfillment/export/UI/webhook/OAuth/CI files;
any Shopify→Odoo stock write outside Task 013B's guarded one-time flow;
protected references.

### 2.4 Acceptance criteria

Task 013 §6 and Task 013B criteria in full, plus:

1. **Layer 2 proven before first mutation** — attempt record persisted
   pre-network (C2 intent commit), uncertain outcomes routed to
   reconciliation (applied / not-applied decided by an
   `InventoryLevel.quantities` read) before any retry, sweep cron
   recovering every crash-window state in the L2-D13 matrix — with
   genuine (not simulated) runtime and concurrency evidence.
2. **CAS flow** — every push is read→compare→set: read the current Shopify
   quantity, send `changeFromQuantity` with the value just read, then send
   the target quantity; a `CHANGE_FROM_QUANTITY_STALE` response → re-read,
   re-derive, bounded retries (proposed 3); persistent divergence → review
   case. `compareQuantity`/`ignoreCompareQuantity` do not exist as current
   (2026-04+) input fields and must never be used — those names may appear
   elsewhere in this document only as historical explanation of what was
   removed, never as a current field.
3. **Coalescing** — last-value-wins pending target per (item, location)
   pair; queue depth bounded by pair count under backlog;
   `operation_scope_key` prevents concurrent same-pair jobs.
4. **Mandatory `@idempotent` keys** — one UUID per mutation attempt,
   persisted on the attempt record before the call; same key replayed on
   network retry within the 24h window, fresh key per deliberate new
   attempt; >24h stale attempts go through reconciliation, never key
   replay.
5. **Divergence review** — Shopify→Odoo direction is read/verify only;
   every divergence yields a review case carrying the three values
   (Shopify current / last-pushed / Odoo current); no automatic Odoo stock
   write outside 013B.
6. **First-push guard** — per-pair preview → explicit confirm (recorded
   who/when/qty) → push; unconfirmed rows refuse writes
   (`destructive_write_guard_blocked`); baseline apply (013B) holds the
   row lock per D-013B-4 and honours drift-abort.
7. Edge policies: negative `free_qty` clamped to 0 + divergence warning;
   unmapped items skipped with surfaced counts; inactive locations suspend
   with review; `committed` never written (source-guard test); reconnect
   reconciliation read precedes the first post-reconnect push (PD-RB
   inventory slice).
8. PB-20 throughput (≥300 level-pushes/hour within throttle budget)
   measured on the dev store.

### 2.5 Tests

Task 013 §5 and 013B test files, Stage 0's core test files, plus the QA
matrices: inventory-operating-model §12 test/UAT hooks (CAS mismatch,
idempotency-window, location-context regression, clamp+warn, baseline
preview/confirm, drift-abort, reconnect read-first, PB-20 run);
`../05-qa/reconnect-backfill-uat-matrix.md` inventory rows (no-blind-push
— companion deliverable that must exist before wave-open);
[`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
items 10, 11, 17. Concurrency tests must use real concurrent transactions,
not sequential simulation.

### 2.6 Runtime and dev-store evidence

Odoo.sh fresh-install + focused-class + full regression + residue audit
per the Wave 1 standard (mandatory). **Genuine dev-store mutation evidence
is required for Wave 3 closure (first mutation wave):** at minimum one
confirmed first push, one CAS round-trip with a provoked mismatch, one
uncertain-outcome reconciliation, one 013B baseline preview/apply, and the
PB-20 measurement — redacted evidence recorded. Unlike Wave 2's read-only
dev-store evidence (which is deferrable to Wave 6), mutation proof here is
**not routinely waivable**: Layer 2's "genuine, not simulated" requirement
(program §4 Wave 3) governs, and any exception is a **specific product-owner
ruling on the record**, never a routine control-room waiver.

### 2.7 Rollback

Per-stage PR revertability inside the wave; wave-PR revert drops
mapping/binding/attempt tables (attempt evidence retention on uninstall
follows DEC-030 alignment in the Layer 2 design §12); live Shopify stock
is not touched by a revert; fulfillment (Wave 4) depends on Layer 2
(Stage 0) but never on Task 013 internals, so a feature-stage rollback
does not strand Wave 4.

### 2.8 Residue audit / Definition of done / hard stops

Residue audit and DoD mirror Wave 2's §2.9/§2.10 (LC-1 `ondelete`
callables registered from the start; control-room wave review; state file
+ matrix + handoff updated). Hard stops: program 1–10 verbatim, plus:

- Any mutation path found bypassing the Stage 0 attempt wrapper → stop
  (hard-stop 4).
- CAS/idempotency shape drift between the packet (2026-07 API) and the
  live API at implementation time → stop and re-verify (hard-stop 2).
- Stage 0 runtime/concurrency proof not achievable genuinely → stop
  (hard-stop 6/10); never substitute simulation.
- Negative-`available` behaviour needed but unverified → keep clamp
  default; never ship push-negative unverified.

## 3. Gate-decision table

| Gate decision | Source | Acceptance authority |
| --- | --- | --- |
| **DEC-031 Layer 2 design Accepted** — the complete [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) D1–D38 decision set, pending final control-room acceptance | [`dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md) | Product owner + control room |
| **Layer 2 implemented + runtime-proven** (Stage 0 complete, evidence accepted) before any Stage 1/2 mutation | this DoR §4 | Control room (evidence gate) |
| Inventory-operating-model PDs 1–12 (free_qty+context source, mapping constraints, coalescing last-value-wins, CAS flow, per-attempt UUID, read/verify-only reverse direction, Layer-2 attempt contract, clamp+warn, preview-first manual, one pair per mutation request for MVP — multi-entry batching excluded, a future separately-gated optimization, reconnect read-first) | inventory-operating-model §12 | Product owner + control room |
| Location-mapping model (D-013-1 manual-only mapping, dual uniqueness, ancestor-overlap constraint, third sanctioned sudo for cache upsert) | Task 013 D-013-1/5 | Control room (sudo elevation explicitly) |
| **Task 013 packet re-accepted with its 2026-07-16 addendum**; §8 prompt gate act separate | packet + addendum | Control room gate act |
| **Task 013B packet re-accepted** (confirmed consistent with the operating model; no addendum required unless contradiction found) | 013B packet | Control room gate act |
| PD-RB inventory slice (reconciliation-read catch-up, no blind push) | reconnect policy §10/§11 | Product owner + control room |
| **CAS field-name empirical preflight — RESOLVED 2026-07-18 (Wave 3 Gate A).** `changeFromQuantity` is confirmed the correct, current (2026-07) field on `InventoryQuantityInput`; `compareQuantity`/`ignoreCompareQuantity` do not exist as input fields from API 2026-04 onward. Four independent official citations, no conflict found between official Shopify sources (the only conflict was this project's own stale internal documents, now corrected). | [`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md) §1; [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) D12 | Control room — **preflight closed, not itself a Wave 3 authorization act** |
| **DEC-031 Layer 2 acceptance candidate normalized and corrected — Gate A correction complete, 2026-07-19.** [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) is the complete `L2-D1`–`L2-D38` decision inventory, status CONTROL-ROOM ACCEPTANCE CANDIDATE — CORRECTIONS APPLIED, NOT YET ACCEPTED; **zero items remain architecture-blocking** after the final consolidated Sessions-2-and-3 ruling (PR #177 comment [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445)) — remaining items are Stage 0 merge-acceptance/implementation-proof criteria, tunable constants, or narrow verification steps (DEC-036 §5). | DEC-036; the Stage 0 packet | Product owner + control room |
| Wave 2 accepted and merged (program wave order; Area-6 full trigger set unblocked) | program §4 | Control room |

Open questions to answer or defer-fail-closed at the gate sitting:
negative-`available` verification, batch-size vs GraphQL cost,
`with_expiration` interaction, sweep cadence default, OQ-RB-3
(changed-since surface for levels).

## 4. Layer 2 as Wave 3 Stage 0 (definition)

DEC-031 names inventory as the Layer-2 trigger domain; this DoR fixes the
delivery shape: **Stage 0 is a discrete, control-room-gated core task
executed at the start of Wave 3 (or as an immediately preceding pre-wave
core task — equivalent, at the control room's scheduling discretion),
consisting of: (a) the persisted mutation-attempt record model, (b) the
reconciliation framework (attempt wrapper, per-domain reconciliation
matrix registry, uncertain-outcome resolution contract), and (c) the sweep
cron with the full crash-window recovery matrix — each with its own core
allowed-files list and its own runtime/concurrency evidence.** Stage 0
carries no inventory feature logic; Task 013 is its first consumer, Task
014/015 its later ones. No Stage 1/2 mutation code merges, is enabled, or
is live-validated before Stage 0's evidence is accepted.

## 5. Current-status conclusion

**READY once gate decisions are Accepted.** As of 2026-07-19 (Wave 3 Gate A
correction batch, PR #177), Wave 3 is **STILL NOT ready — Gate A correction
complete, control-room final review pending, Gate B not started**;
outstanding:

1. **Wave 2 is now MERGED** (PR #176, merge commit
   `22bfb9a0e9b1e48b6a664351e2b321d134177110`, into `mvp/program-integration`
   at `aa87ccc971eb9ab500911948e0e751136453cbc2`) — this dependency is
   **CLOSED**. Wave 1 remains merged and SRR-03 remains closed.
2. **DEC-031 Layer 2 design remains Proposed, not Accepted.** Gate A
   (2026-07-18) produced a complete, normalized acceptance candidate —
   [`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md), and the
   final consolidated Sessions-2-and-3 correction batch (2026-07-19, PR
   #177 comment
   [`5014689445`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5014689445))
   resolved every item DEC-036 previously carried as BLOCKING — status is
   now **CONTROL-ROOM ACCEPTANCE CANDIDATE — CORRECTIONS APPLIED, NOT YET
   ACCEPTED**. The [Wave 3 Stage 0 packet](wave-3-stage-0-layer-2-packet.md)
   is correspondingly corrected, status **PROPOSED — LOCKED PROMPT NOT
   ISSUED**. Neither DEC-036 nor the packet is yet accepted by the control
   room — this correction batch supplies the binding architecture choices,
   it does not itself constitute acceptance.
3. Inventory-operating-model PDs and the PD-RB inventory slice remain
   Proposed. **Note:** `inventory-operating-model.md` §4.4 still references
   the stale `compareQuantity` field name and requires correction in a
   future Gate B session with that file in its allowed list, before Task
   013 re-acceptance.
4. Task 013 re-acceptance, not yet performed; §8/§9 prompt gate acts not
   performed. Gate B must additionally replace all stale
   `compareQuantity`/`ignoreCompareQuantity` language with
   `changeFromQuantity`; supersede binding-owned idempotency with
   attempt-owned idempotency; adopt review-case-first handling for
   unexplained Shopify drift; confirm one pair per request for MVP; and
   confirm Task 013B does not use Layer 2 and remains a separate Stage 2
   packet — see DEC-036 Part 0.5's Gate B carry-forward list.
5. **CAS field-name empirical preflight — RESOLVED 2026-07-18** (see the
   gate-decision table above). `changeFromQuantity` is confirmed correct;
   no conflict between official Shopify sources.
6. Genuine dev-store mutation evidence must be produced for closure (first
   mutation wave); it is not routinely waivable — any exception is a
   product-owner ruling. This is not a *readiness* blocker but a *closure*
   requirement. Unaffected by Gate A.
7. This Definition of Ready itself remains Proposed, not accepted — this
   session's own corrections (items 1, 2, 3's flag, 4, 5, and the
   batching/CAS text above) do not self-accept it.
8. **Gate-A architecture status, corrected 2026-07-19:** DEC-036 carries
   **zero remaining architecture blockers** after the consolidated
   Sessions-2-and-3 ruling. What remains before Stage 0 implementation's
   *merge* (not its start) is Stage 0 packet §17's three categories:
   (I) implementation-proof requirements (the four-layer
   runtime/concurrency/crash-injection plan; the `pg_stat_activity`
   open-transaction proof; the AST-tooling-maturity inspection finding —
   none blocks *beginning* implementation); (II) tunable-constant
   ratifications (sweep timeout, idempotency-key margin, retention
   masking window); (III) one narrow implementation-time field-name
   verification. None is an architecture blocker; all are tracked in the
   Stage 0 packet §17, not duplicated here.
