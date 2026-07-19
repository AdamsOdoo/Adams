# Official-Source Refresh — DEC-031 Layer 2 Mutation Safety (Wave 3 Gate A, 2026-07-18)

> **Capture file** per `docs/00-source-materials/README.md` rules: raw
> Tier-1 evidence (quotes/paraphrases with citation headers). Conclusions
> live in `docs/03-architecture/dec-031-layer-2-mutation-safety-design.md`
> and `docs/04-decisions/DEC-036-wave-3-layer-2-gate.md`. All Shopify sources
> accessed **2026-07-18** against the Admin GraphQL API version **2026-07**
> unless otherwise noted; all Odoo sources accessed **2026-07-18** against
> the **19.0** branch. Access status is recorded per source. Quotes are
> marked with quotation marks; everything else is close paraphrase.
>
> **Provenance note:** this capture consolidates (a) this session's own
> 27-agent research/audit workflow (code audit of
> `addons/shopify_connector_core/**`, documentation audit, and dedicated
> official-source research agents), and (b) this session's own independent
> follow-up verification via direct `WebFetch`/`WebSearch` against the exact
> pages cited below, performed specifically to corroborate the control-room
> parallel-audit ruling on PR #177 comment
> [`5012854989`](https://github.com/AdamsOdoo/Adams/pull/177#issuecomment-5012854989).
> Every fact this session characterizes as independently confirmed was
> fetched live in this session, not copied from the ruling comment's text.

---

## 1. Shopify Admin GraphQL — inventory compare-and-swap (CAS) field name

**[Fact — resolves the repository's `compareQuantity` vs `changeFromQuantity`
vs `ignoreCompareQuantity` conflict named in this session's task and in
existing docs (`dec-031-layer-2-mutation-safety-design.md` §3/§4.2,
`inventory-operating-model.md` §4.4, `wave-3-definition-of-ready.md` §3).]**

- Source: `InventoryQuantityInput` reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/input-objects/InventoryQuantityInput
  — Accessible, 2026-07-18.
  - Current fields (four): `changeFromQuantity` (Int, nullable) — quote:
    "The quantity currently expected at this location, before setting the
    new quantity."; `inventoryItemId` (ID!, required); `locationId` (ID!,
    required); `quantity` (Int!, required).
  - There is **no `compareQuantity` field and no `ignoreCompareQuantity`
    field** on this type in the 2026-07 schema. Passing
    `changeFromQuantity: null` (or omitting it) is the current mechanism for
    bypassing the CAS check — it replaces the old boolean flag.
- Source: `InventorySetQuantitiesInput` reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/input-objects/InventorySetQuantitiesInput
  — Accessible, 2026-07-18.
  - Top-level fields: `name` (quantity name(s): `available`/`on_hand`),
    `quantities` (`[InventoryQuantityInput!]!`), `reason`,
    `referenceDocumentUri`. **The CAS field lives per-entry, on
    `InventoryQuantityInput`, not at the request level** — each entry in
    `quantities[]` carries its own independent `changeFromQuantity`.
- Source: changelog, "Finalizing compare and swap redesign for
  inventorySetQuantities" (dated 2025-12-12) —
  https://shopify.dev/changelog/finalizing-compare-and-swap-redesign-for-inventory-set-quantities
  — Accessible, 2026-07-18. Makes `changeFromQuantity` **mandatory** and
  removes `compareQuantity`/`ignoreCompareQuantity` as a breaking change,
  effective API version **2026-04**.
- Source: changelog, "Compare and swap redesign for inventorySetQuantities"
  (the earlier, optional-field introduction, dated 2025-12-12) —
  https://shopify.dev/changelog/compare-and-swap-redesign-for-inventory-set-quantities
  — introduces `changeFromQuantity` as **optional**, effective API
  **2026-01**.
- Mismatch error code: `CHANGE_FROM_QUANTITY_STALE` — confirmed present on
  `InventorySetQuantitiesUserErrorCode` — https://shopify.dev/docs/api/admin-graphql/2026-07/enums/InventorySetQuantitiesUserErrorCode
  — Accessible, 2026-07-18.

**[Conflict found — recorded, not silently dropped, per this session's task
§4/§11]:** the same `InventorySetQuantitiesUserErrorCode` enum page **also
still lists** `COMPARE_QUANTITY_STALE` ("The compareQuantity value does not
match persisted value.") and `COMPARE_QUANTITY_REQUIRED` ("The
compareQuantity argument must be given to each quantity or ignored using
ignoreCompareQuantity.") as of 2026-07. This is a genuine residual naming
artifact in the **error-code enum only** — it does not reappear on the
`InventoryQuantityInput` type itself. **Resolution, per "prefer raw
versioned schema for field existence, fail closed" (this session's task
§4):** the raw input-object schema is authoritative for *field existence*;
`compareQuantity` is not a live input field in 2026-07. The error-enum
residue is logged here as a documented nuance (possibly a legacy-compat
leftover in the error taxonomy) and must **not** be read as evidence that
`compareQuantity` is still usable. Every current-facing design/product
document in this repository must use `changeFromQuantity` exclusively for
the *input field*; a footnote may retain the enum-residue observation for
completeness.

**Conclusion:** `changeFromQuantity` is the correct, current (2026-07) CAS
field name. `compareQuantity` and `ignoreCompareQuantity` are stale as
*input fields* from API 2026-04 onward and must be removed from every
current-facing occurrence in Layer 2 design text (see DEC-036 D12 for the
full correction list). **Not blocking** — this is a resolved conflict
between the project's own stale internal documents, not an unresolved
conflict between official Shopify sources (every official source examined
agrees).

---

## 2. Shopify Admin GraphQL — `@idempotent` mandatory-mutation behavior

**[Fact.]**

- Source: changelog, "Making idempotency mandatory for inventory adjustments
  and refund mutations" (published 2025-12-12) —
  https://shopify.dev/changelog/making-idempotency-mandatory-for-inventory-adjustments-and-refund-mutations
  — Accessible, 2026-07-18.
  - Mandatory from API version **2026-04**.
  - Affected mutations (17, quoted in full): `refundCreate`,
    `inventoryShipmentReceive`, `inventoryAdjustQuantities`,
    `inventoryMoveQuantities`, `inventorySetQuantities`,
    `inventorySetOnHandQuantities`, `inventoryShipmentCreateInTransit`,
    `inventoryShipmentCreate`, `inventoryTransferCreate`,
    `inventoryTransferCreateAsReadyToShip`, `inventoryTransferDuplicate`,
    `inventoryTransferSetItems`, `inventorySetScheduledChanges`,
    `inventoryActivate`, `inventoryShipmentAddItems`, `locationActivate`,
    `locationDeactivate`. **Both `inventorySetQuantities` and
    `inventoryActivate` are confirmed on this list.**
  - Quote: "Calling these mutations without an idempotency directive will
    result in an error at runtime" — i.e. enforcement is **runtime**, not
    necessarily visible as a required-argument at schema/introspection
    level (a static schema check for the directive's presence is
    insufficient; the wrapper must always supply one for these mutations).
- Source: `inventorySetQuantities` mutation reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventorySetQuantities
  — Accessible, 2026-07-18. Confirms the same 2026-01-optional /
  2026-04-mandatory timeline in-page and shows the directive syntax:
  `inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey)`
  — the idempotency key is a **GraphQL directive argument**, not an HTTP
  header.
- Source: `inventoryActivate` mutation reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryActivate
  — Accessible, 2026-07-18. Same mandatory-from-2026-04 confirmation.
  Arguments: `inventoryItemId` (ID!), `locationId` (ID!), `available`
  (Int, optional), `onHand` (Int, optional), `stockAtLegacyLocation`
  (Boolean, optional, default false). Payload: `inventoryLevel`,
  `userErrors`.

**Retention/expiry window:** **24 hours** from the original request.
Source: https://shopify.dev/docs/api/usage/implementing-idempotency —
corroborated via a targeted `WebSearch` against `shopify.dev` (2026-07-18);
quote (from search-indexed page content): "Shopify tracks idempotency keys
for 24 hours from the original request... After 24 hours, idempotency keys
expire and are no longer recognized as duplicates." **[Citation-strength
note, disclosed per this session's task §4/§11 rather than silently
upgraded to full-strength Fact]:** this session's own direct `WebFetch` of
the `idempotent-requests` guide page did **not** itself surface the numeric
figure on that specific page; the 24-hour figure is corroborated by
multiple independent `shopify.dev`-scoped search results agreeing on the
same number, which this session treats as **Accessible-corroborated** but
flags for a direct single-page re-confirmation before treating the number
as beyond challenge in a context where the exact hour count is safety-load-bearing
(see DEC-036 D6's 23-hour local safety-margin recommendation, which is
explicitly **not** itself Shopify-sourced).

Within the 24h window: replay of the same key returns the cached original
response without re-executing the mutation. After the window: a replayed
key is no longer recognized as a duplicate and is treated as a new
operation — i.e. a stale key must **not** be reused past 24h as a dedup
guard; reconciliation, not blind key-reuse, governs recovery after the
window (see DEC-036 D6).

**Idempotency-specific user-error codes** (confirmed on
`InventorySetQuantitiesUserErrorCode`, 2026-07): `IDEMPOTENCY_CONCURRENT_REQUEST`
("This request is currently in progress, please try again."),
`IDEMPOTENCY_KEY_PARAMETER_MISMATCH` (key reused with different arguments),
`IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` (previous request with the same key
failed). None of these three codes appears anywhere in the current Layer 2
design doc's outcome taxonomy (§5.1) — this is a real gap, closed in
DEC-036 D6.

---

## 3. Shopify Admin GraphQL — THROTTLED execution guarantee (undocumented)

**[Fact — absence of a guarantee, not presence of one.]**

- Source: https://shopify.dev/docs/api/usage/rate-limits — Accessible,
  2026-07-18.
  - The page does **not** state whether a mutation resolver executes before
    or after the cost/throttle check, and does **not** state that a
    `THROTTLED` response guarantees no server-side mutation occurred.
  - Backoff guidance found (quote): "Your code should stop making
    additional API requests until enough time has passed to retry. The
    recommended backoff time is one second." This is stated as a
    **recommendation**, not a documented contractual minimum/guarantee —
    the existing design doc's §10 wording ("recommended minimum backoff
    1s [Fact — quote]") slightly overstates this: the number is real and
    quoted correctly, but its status is "recommended," not "guaranteed
    minimum."

**Conclusion (fail-closed, per the control-room ruling on PR #177 comment
5012854989 and independently corroborated by this session's own fetch):**
`THROTTLED = not executed` is **not an established official fact** for any
mutation examined. The existing design doc's §5.1/§10
`THROTTLED → failed_clean` classification is corrected to `THROTTLED →
uncertain` (reconcile-first) in DEC-036 D9, for every mutation domain,
until an explicit non-execution guarantee is found (see DEC-036 Part 7
item 8 — this remains an open, non-blocking-for-shipping but factually
open question).

---

## 4. Shopify Admin GraphQL — `InventoryLevel` reconciliation reads

**[Fact.]**

- Source: `InventoryLevel` object reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/objects/InventoryLevel
  — Accessible, 2026-07-18. Field: `quantities(names: [String!]!):
  [InventoryQuantity!]!`.
- Source: `InventoryQuantity` object reference —
  https://shopify.dev/docs/api/admin-graphql/2026-07/objects/InventoryQuantity
  — Accessible, 2026-07-18. Fields: `id` (ID!), `name` (String!), `quantity`
  (Int!), `updatedAt` (DateTime, nullable). `updatedAt` is useful for a
  reconciliation read to freshness-check the read against the attempt's own
  `transport_at` timestamp.

---

## 5. Odoo 19 — PostgreSQL transaction isolation level (REPEATABLE READ, not Read Committed)

**[Fact — corrects an error the control-room ruling on PR #177 comment
5012854989 identified in a separate parallel audit ("Session 2"). This
session independently re-verified the correction directly against source,
not merely accepted the ruling's assertion.]**

- Source: `odoo/odoo`, `odoo/sql_db.py`, `19.0` branch —
  https://github.com/odoo/odoo/blob/19.0/odoo/sql_db.py — Accessible,
  2026-07-18.
  - `Cursor.__init__` calls
    `self.connection.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)`
    (observed at approximately line 590 of the 19.0 branch file).
    `ISOLATION_LEVEL_REPEATABLE_READ` is imported from `psycopg2.extensions`
    (approximately line 30).
  - This is set for **every** Odoo cursor at creation — universal, not
    conditional on cron/request context.
  - The module's own docstring (approximately lines 540–583) explains the
    choice: PostgreSQL `REPEATABLE READ` gives snapshot-isolation semantics
    across every PostgreSQL version Odoo 19 supports (10+); Odoo implements
    its own row-locking (`FOR UPDATE`/`FOR SHARE`/`try_lock_for_update`) for
    high-contention paths rather than relying on full `SERIALIZABLE`.
- **Corroborating in-repo evidence:** `docs/05-qa/architecture-review-log.md`
  row **AR-056** (2026-07-17, pre-dating this session) already describes a
  Wave 2 correction as made "under PostgreSQL REPEATABLE READ" — i.e. this
  project's own prior sessions had already independently established
  REPEATABLE READ as the operative isolation level before this refresh;
  the "Read Committed" characterization corrected by the PR #177 ruling was
  never this repository's own working assumption in its accepted history.

**Consequences for the Layer 2 transaction-boundary design (binding on
DEC-036 Part 6 / the Stage 0 packet):**

1. A worker's later statement inside the **same** transaction does **not**
   automatically see another connection's newly committed data — the
   snapshot is fixed at the transaction's first statement, not
   re-taken per-statement (unlike PostgreSQL's default Read Committed,
   which re-takes a snapshot per statement).
2. C1/C2/C3 (see DEC-036 Part 6) must each be genuine, separate
   commit/transaction boundaries — a fresh transaction (new cursor
   statement after the prior commit) is required before any code path may
   rely on seeing another worker's or another commit-point's newly
   committed state.
3. Recovery/reconciliation logic that re-reads a job or attempt row after a
   crash or a sibling worker's commit must force a fresh read — Odoo's
   `invalidate_recordset()` + re-`browse()`/re-`search()` pattern (already
   used, per this session's code audit, in
   `shopify_connector_job.py`'s `_claim_for_dispatch`, immediately after
   lock acquisition and before re-filtering on current state) is the
   existing, proven precedent for this and must be applied identically at
   every Layer 2 recovery/reconciliation read that depends on
   cross-transaction visibility of another commit point's result.
4. This isolation level does **not** by itself change the lock-vs-open-transaction
   analysis in DEC-036 D22 (whether an open, lock-free transaction can
   still span the network call) — that risk exists independent of isolation
   level, because PostgreSQL auto-opens a new transaction on the next
   statement issued after any commit, under any isolation level.

---

## 6. Odoo 19 — cursor commit/rollback, `ir.cron`, and constraints (supplementary)

**[Fact, from this session's dedicated Odoo research agent, corroborating
the existing design's citations.]**

- `env.cr.commit()` inside a method is an established, sanctioned Odoo
  pattern for cron-style batch processing (commit-per-item durability), used
  throughout Odoo's own `ir.cron` execution path and documented as
  acceptable specifically for long-running/batch jobs where partial
  progress must survive a later failure — this is the precedent this
  repository's own `_drain_one`/`run_drain` pattern already follows (see
  DEC-036 D19's correction: the existing design doc's citation of this
  pattern as "exactly" Odoo's `_commit_progress()` API is imprecise —
  `_drain_one` uses a bare `cr.commit()`, not the `_commit_progress()`
  helper — corrected in the design doc text, not merely noted here).
- `ir.cron`'s own execution runner commits between distinct cron job
  records it processes, but does **not** itself impose a commit-per-item
  policy *within* a single cron method's body — any finer-grained
  commit boundary (such as this design's C1/C2/C3 protocol) is the
  responsibility of the method's own author, exactly as this repository's
  job-dispatch code already does.
- Odoo 19's constraint mechanism: `models.UniqueIndex` (and the broader
  `models.Constraint` declarative mechanism) is the current 19.0-recommended
  approach; legacy `_sql_constraints` dict declarations are confirmed, per
  this session's code-audit workflow, to be silently inert under 19.0 (no
  enforcement, only a startup warning) — this is **directly relevant** to
  DEC-036 D2's `(job_id, attempt_id)` uniqueness requirement on the new
  `mutation.attempt` model, which must use `models.UniqueIndex`, never
  `_sql_constraints`.

---

## 7. Odoo 19 — `selection_add`/`ondelete`, uninstall, ACL/sudo, multi-worker (supplementary)

**[Fact, from this session's dedicated Odoo research agent.]**

- `selection_add` with an `ondelete=` policy (including a callable) is the
  current, correct mechanism for a domain module to extend a core
  Selection field's vocabulary; this repository's own LC-1 design
  (`shopify_connector_job.original_job_type` conversion helper) already
  implements the callable-`ondelete` pattern and is the direct precedent
  DEC-036 D35 must reuse if `mutation_domain` is decided to be
  domain-`selection_add`-owned rather than core-fixed.
- Module uninstall in Odoo 19 drops tables/columns/data records owned by
  the uninstalling module per `ir.model.data`'s ownership records; a module
  can mark specific data as retained (surviving a *different* module's
  uninstall) only by that data being owned by a module that stays
  installed — there is no per-record "survive uninstall" flag independent
  of which module owns the underlying `ir.model.data` entry. This
  corroborates DEC-030's existing accepted design (core-owned audit tables
  survive a domain uninstall because core, not the domain module, owns
  them) and DEC-036 D34's correction of the Layer 2 design doc's internal
  self-contradiction on this point.
- ACL (`ir.model.access.csv`) rows and record rules (`ir.rule`) combine
  restrictively (an operation is permitted only if both allow it); a
  "fail-closed" ACL row is a row that grants no create/write/unlink by
  default, requiring an explicit, auditable, separate grant (or `sudo()`)
  to perform those operations — this is the pattern DEC-036 D30 adopts for
  `mutation.attempt` (four ACL rows, all `perm_write=0/perm_create=0/perm_unlink=0`,
  all mutation via `sudo()` only).
- Odoo's multi-worker (prefork/gevent) deployment model does not, by
  itself, guarantee only one worker executes a given `ir.cron` trigger at a
  time through any special cron-level mechanism beyond the same row-locking
  primitives (`try_lock_for_update`/`FOR UPDATE SKIP LOCKED`-style patterns)
  application code must use for any contended row — this directly
  corroborates why `_claim_for_dispatch`'s `try_lock_for_update()` pattern
  (and DEC-036 D26's proposed stale-owner sweep cron using the same
  primitive) is necessary rather than assumed-safe by the platform alone.

---

## 8. Field-level `groups=` vs. Python-enforced write guards (ruling point 7)

**[Fact, from this session's code-audit workflow, directly answering the
control-room ruling's instruction not to rely on unresolved `sudo()`/field-group
behavior.]**

This repository's own existing protected-field mechanism
(`shopify_connector_binding_mixin.py`'s `_protected_binding_fields()`, and
`shopify_connector_job.py`'s `PROTECTED_JOB_FIELDS` + `write()` override
requiring `env.su`) does **not** rely on a field's `groups=` attribute for
write protection — it enforces protection with an explicit Python `write()`
override that checks `self.env.su` and raises `ValidationError`/refuses the
write for any non-superuser caller attempting to touch a listed field,
regardless of which ACL group that caller belongs to. `groups=` on a field
definition affects view rendering/visibility, not ORM-level write
enforcement, and is not relied upon anywhere in the current codebase for
security. **DEC-036 D30 explicitly follows this exact existing pattern**
for `mutation.attempt` (ACL rows deny write/create/unlink to every role
including Admin; all legitimate writes go through explicit `sudo()` call
sites at C2/C3/the resolution-override action, enumerated and closed-set
via an AST test) rather than any unresolved `groups=`-based scheme — this
closes the ruling's point 7 requirement without inventing a new mechanism.

---

## Summary table — conflicts and their resolution status

| Question | Resolved? | Answer | Blocking? |
|---|---|---|---|
| CAS field name (2026-07) | Yes | `changeFromQuantity` | No — resolved |
| `@idempotent` mandatory for `inventorySetQuantities`/`inventoryActivate` | Yes | Mandatory from API 2026-04 | No — resolved |
| Idempotency-key retention window | Yes (Accessible-corroborated; single-page pin recommended) | 24 hours | No — resolved, margin value below is separately flagged |
| Local idempotency safety margin (23h) | No — no source specifies any margin | Recommendation only, not Shopify-sourced | Non-blocking; needs explicit control-room ratification |
| `THROTTLED` guarantees non-execution | No — undocumented either way | Fail closed: treat as `uncertain` | No — resolved by fail-closed policy, underlying fact still open |
| Odoo 19 isolation level | Yes | `REPEATABLE READ`, set on every cursor | No — resolved |
| Whether an open (lock-free) transaction can span the network call | No — not proven either way | Requires new coding rule + new `pg_stat_activity` test class | **Yes — blocking (DEC-036 D22)** |
| `mutation_domain` field ownership (domain-owned vs. core-fixed) | No — two legitimate precedent-supported options | Control-room choice required | **Yes — blocking (DEC-036 D35)** |

**No claim in this capture is presented as a decision.** All are [Fact] or
explicitly labeled [Inference]/[Recommendation]/[Open question] per
`CLAUDE.md` §8. Conclusions and their downstream implementation impact are
recorded in `docs/04-decisions/DEC-036-wave-3-layer-2-gate.md`, not here.
