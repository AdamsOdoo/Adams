# Task 010B — Product Import Completeness: Validation Results

> **Status: draft-PR validation record. Implementation session output,
> awaiting ChatGPT review.** Produced 2026-07-11 by the Task 010B
> implementation session against the OPEN gate (PR #149 comment
> `4948723366`). **Revised 2026-07-12** per control-room static reviews
> `4950202231` (§0), `4950339305` (§0b), `4951145191` (§0c), and the
> **runtime correction `4680380218`** (§0d — first Odoo.sh build RED from
> non-isolated global attribute fixtures; fixtures corrected, rerun pending).
> Odoo.sh and live/dev-store evidence are **not** part of this session (no
> Odoo runtime and no Shopify credentials are available here) and remain
> mandatory before merge acceptance (§10 below). The Odoo.sh standard-runtime
> gate is **OPEN**.

---

## 0. Revision 1 — control-room static review `4950202231` (2026-07-12)

The first control-room static review (PR stayed draft) found several
overclaimed decisions at head `1065cdf`. This revision corrects them on
the same PR (files: the importer, the template-binding model, and four
test files; docs). Corrections, each honestly scoped:

1. **Pagination now strictly shape-validated.** `_fetch_product_with_all_
   variant_pages` requires `data`/`product`/`variants`/`pageInfo` to be
   mappings, `nodes` a list, `hasNextPage` a real Boolean, and `endCursor`
   a non-empty string when `hasNextPage` is true. A missing/null/wrong-type
   `pageInfo` is **never** treated as a completed single page (that risked
   silent truncation). All violations → `data_shape_schema_mismatch`; no
   product/binding is written (validated before `_apply_import`). New tests
   cover every malformed shape.
2. **Real `updatedAt` short-circuit** (was fetched but unused). New readonly
   `shopify_updated_at` (Char) on the template binding; an active binding
   recording the exact non-empty remote `updatedAt` short-circuits the
   import **before** any media download or product/attribute/price/image/
   binding write, returning an `unchanged` indicator. The stamp is written
   **only after** a complete success (rolled back on any failure).
   Enqueue-level `payload_hash = updatedAt` is recorded as an **Area-6
   integration obligation** — this task has no enqueue call site and never
   mutates a running job's payload hash. The prior "manual duplicate-job"
   test (which only proved the core idempotency constraint) is replaced by
   real importer tests.
3. **Same-URL image ownership fixed.** The skip decision now compares the
   **current Odoo image checksum** against the recorded connector checksum
   (not URL + recorded-checksum alone). Same URL + merchant-replaced image
   → protected + note (no download); same URL + cleared image → preserved
   under `snapshot_only`, restored under `shopify_fields`. Covers both
   `image_1920` and `image_variant_1920`.
4. **SVG / spoofed bodies rejected.** `image/svg+xml`/`image/svg`/any
   `svg` content-type is rejected; downloaded bytes are validated as a
   supported raster image via Pillow (`Image.verify()` + format
   whitelist), so SVG markup or junk labelled `image/png` is rejected
   (`shopify_temporary_server_network`), never exposing the body. Global
   Pillow config is untouched.
5. **Bounded aggregate media memory.** *(Superseded by §0b.2: Revision 2
   replaces the `SpooledTemporaryFile` handles with closed-path staging for
   O(1) open handles at the 2,048-variant ceiling.)* Each image streamed
   into a `SpooledTemporaryFile` (in-memory up to 1 MB, then disk); an
   `ExitStack` closed every staged file on success, download failure,
   validation failure, DB failure, and classified failure. No dict of full
   image byte strings was retained; at most one staged image was read fully
   into memory for its Odoo write. The 20 MB cap, HTTPS/redirect
   restrictions, and the "downloads before the savepoint, DB writes inside
   it" split are kept.
6. **`connector_owned` refresh fixed.** Refresh resolves the one template
   line whose attribute name is exactly the Shopify option name OR exactly
   `"<name> (Shopify)"`; no candidate → `binding_conflict`; both present →
   `binding_conflict` (fail closed); the merchant attribute is never
   modified. New value/new variant on refresh now extends the connector
   attribute in both refresh modes.
7. **Concurrency proof strengthened to the real import path.** *(Wording
   corrected in §0b.5: the test is renamed
   `test_overlapping_transactions_serialize_to_one_global_attribute` and
   described as overlapping, not simultaneous, execution.)* The prior test
   exercised the lock + direct attribute resolver only. The strengthened
   test runs the REAL `_apply_import` for two products (same new option)
   across two genuinely independent PostgreSQL connections
   (`odoo.sql_db.db_connect`), with committed synthetic stores visible to
   both: B finishes its import first and stays uncommitted holding the
   transaction-scoped lock, A then runs and gets
   `concurrency_race_conflict`, and after B commits A retries and reuses
   B's committed attribute (exactly one attribute; both products bound;
   durable cleanup). `TransactionCase`'s `registry.cursor()` (a shared
   `TestCursor`) is **not** presented as independent concurrency.
8. **Documentation corrected** (this file, AR-046, handoff, PR body) to
   remove the prior overclaims.

---

## 0b. Revision 2 — control-room static review `4950339305` (2026-07-12)

The second control-room static review (PR stayed draft) accepted Revision 1
but found five remaining reliability blockers at head `5688ec1`. This
revision corrects them on the same PR. **Files touched:** the importer, the
attribute-lock model, and four test files (`test_product_import_matching`,
`test_product_media_import`, `test_product_refresh_and_stale`,
`test_product_attribute_import`); this doc, AR-046, handoff, PR body. Test
methods **135 → 155**. Each correction, honestly scoped:

1. **Pagination forward-progress and identity guards.**
   `_fetch_product_with_all_variant_pages` now keeps a set of seen cursors
   and rejects a repeated/non-progressing `endCursor` (equal to the current
   cursor, or already seen) → `data_shape_schema_mismatch`, so a connection
   that returns `hasNextPage=true` forever cannot loop. Every `nodes`
   element must be a mapping with a non-empty variant GID; a duplicate
   variant GID **within or across** pages is rejected here (not left to a
   later DB constraint); and every non-null page's product `id` must equal
   the requested GID. New no-write tests cover repeated/zero-node cursor,
   repeated-node cursor, cursor==current, replayed-seen cursor, non-mapping
   node, missing-GID node, duplicate GID within/across pages, product-GID
   mismatch, and a valid two-page accept. Each fake caps its call count so a
   regressed guard fails fast rather than hanging.
2. **O(1) media handles + bounded RAM (closed-path staging).** The prior
   design kept one open `SpooledTemporaryFile` per image until all DB writes
   finished (up to 2,049 open handles / ~2 GiB spool at the ceiling). Each
   image is now streamed in 64 KiB chunks to its **own secure `mkstemp`
   file** (mode 0600) that is **closed immediately** after download +
   raster validation; only the **path** is retained in the media plan, and
   `_apply_image` opens exactly **one** path at a time via `_read_staged`.
   Open file handles are therefore O(1) and aggregate RAM is bounded by one
   chunk during staging plus one image at write time, independent of variant
   count — with **no** arbitrary catalog cap. An `ExitStack` unlinks every
   staged path deterministically on success, download failure, validation
   failure, DB failure, and classified failure. The temp prefix carries no
   URL/token, and no path is ever surfaced in an operator-facing error.
   Downloads-before-savepoint / writes-inside-savepoint and the 20 MB cap
   are kept. New tests prove: the plan holds paths (not open handles);
   one-open-at-a-time reads; and removal of every path after success, DB
   failure, and validation failure, with no path in the error.
3. **Mid-stream network failure classification.** A
   `requests.exceptions.RequestException` raised **while iterating**
   `response.iter_content()` (`ReadTimeout`, `ConnectionError`,
   `ChunkedEncodingError`) is now caught, the response closed, the partial
   staged file unlinked, and re-raised as the sanitized
   `shopify_temporary_server_network` (auto-retry) — never leaking the body
   or path. Previously only the initial `requests.get()` was covered, so a
   mid-stream failure escaped to `unknown_system_error`. New test: an
   iterator that yields one chunk then raises `ChunkedEncodingError`.
4. **Archived path routed before any media download.** `_apply_import` now
   routes an `ARCHIVED` product to `_handle_archived_product` **before**
   `_prepare_media`, so a broken image URL can never prevent stale marking
   (the prior order staged all images first). A **bound** archived product
   marks its template + variant bindings stale, refreshes only the binding's
   own audit snapshots, and performs no media/master write. A **first-seen,
   unbound** archived product no longer silently creates a bare Odoo
   product/binding — it raises the existing `mapping_missing` class
   (conservative, never-silent). New tests prove `_prepare_media` is not
   called, a broken URL does not block stale marking, bound master values
   are unchanged, and a first-seen archived product raises `mapping_missing`
   and creates no template/variant/attribute/binding.
5. **Lock-hold + concurrency wording corrected (no code behaviour change).**
   The singleton row lock is **transaction-scoped**: releasing the
   per-product savepoint does **not** release it — PostgreSQL holds the
   `FOR UPDATE` row lock until the outer transaction commits/rolls back, so
   it serializes the remaining DB work of that transaction (and, in a
   `run_drain` batch spanning several jobs, potentially the rest of the
   batch), not merely the attribute critical section. The prior
   docstring/PR wording ("held only across the attribute critical section")
   was factually wrong and is corrected in the lock-model docstring, the
   importer comments, this doc, AR-046, the handoff, and the PR body.
   Network downloads occur **before** the lock is acquired. The concurrency
   test is renamed
   `test_overlapping_transactions_serialize_to_one_global_attribute` and its
   docstring now describes it accurately as two **independent, overlapping**
   transactions (B finishes its import first and stays uncommitted holding
   the lock; A then runs and gets `concurrency_race_conflict`; after B
   commits, A retries and reuses the committed attribute) — **not**
   simultaneous full-import execution. The lock-hold duration and throughput
   impact are recorded as a **mandatory runtime measurement obligation**
   (§10), not a closed performance claim.

---

## 0c. Revision 3 — control-room static review `4951145191` (2026-07-12)

The third static review (PR stayed draft) accepted the Revision-2 work and
found four final corrections before Odoo.sh runtime execution. **Files
touched:** the importer, `test_product_import_matching`,
`test_product_refresh_and_stale`, the authoritative packet, and the three
docs; plus a **base merge** of the current integration tip. Test methods
**155 → 161**.

- **Base updated to the current integration tip.** `Shopify-connector`
  advanced to `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f` (PR #153 merged
  its sync-engine concurrency evidence). That exact tip is merged into this
  published branch with a normal merge commit (no history rewrite); the
  merge is clean (PR #153 added only evidence files under
  `docs/05-qa/evidence/sync-engine-concurrency/` and two new `docs/05-qa`
  result/handoff files — no overlap with any Task 010B file), so **all
  PR #153 evidence is preserved unchanged** and no Task 010B code changed in
  the merge.

1. **Zero-node empty-page forward progress.** The seen-cursor guard rejected
   only a *repeating* cursor; a malformed connection returning
   `hasNextPage=true`, `nodes=[]`, and a **fresh** non-empty cursor forever
   accumulated no variants, so the 2,048 cap never fired and it could loop
   indefinitely. `_fetch_product_with_all_variant_pages` now rejects a
   continuing page (`hasNextPage=true`) whose `nodes` is empty →
   `data_shape_schema_mismatch`. A defensive `MAX_VARIANT_PAGES` backstop is
   added, and the loop is proven bounded: every continuing page must add
   ≥1 **unique** accumulated variant (zero-node rule + duplicate-GID guard),
   and the accumulated set is capped at `MAX_ACCUMULATED_VARIANTS`, so at
   most `MAX_ACCUMULATED_VARIANTS + 1` continuing pages run. Regression test
   uses fresh cursors on empty pages with a strict call-count cap so a
   regression fails rather than hangs, proving no write.
2. **Cross-page `updatedAt` torn-read guard.** Each page is a separate
   GraphQL request; the importer validated the product GID per page but did
   not check whether the product was edited mid-pagination, so it could
   splice first-page metadata onto later-page variants. It now captures the
   first page's `updatedAt` (present/absent shape and value) and requires
   every later non-null page to carry the exact same shape and value, else
   raises `data_shape_schema_mismatch` before any write. Tests: identical
   across two pages → accepted; changed on page two → blocked; first missing
   / second present → blocked; first present / second missing → blocked.
   This is an in-run torn-read guard only — **not** Area-6 enqueue
   deduplication or `payload_hash` ownership.
3. **ARCHIVED outranks the unchanged short-circuit.** `_apply_import` routed
   `_unchanged_short_circuit()` **before** the archived check, so an active
   binding whose archived payload presented the same stored `updatedAt`
   could return `unchanged` instead of going stale. The order is now
   `_validate_payload` → **archived route** → settings / unchanged
   short-circuit → media / normal import. Lifecycle status wins. Regression
   test: active bound product with a non-empty `updatedAt`, then an archived
   payload with the exact same `updatedAt` → template + variant bindings
   stale, result not `unchanged`, `_prepare_media` not called, and Odoo
   master values (a decoy price) unchanged. First-seen unbound archived
   still raises `mapping_missing` and creates nothing.
4. **Authoritative packet lock wording corrected.**
   `docs/07-implementation-plan/task-010b-product-import-completeness-packet.md`
   still described the singleton lock as released with the product savepoint
   and held only across the attribute critical section. A clearly dated
   **correction/supersession note** is added near the top (decision history
   not rewritten), and every stale statement (§D-010B-2, §10 locked prompt)
   is annotated inline as **[superseded]**: the lock is transaction-scoped,
   the savepoint release does not free it, it is held to the outer
   commit/rollback and serializes the rest of the transaction (and, in a
   `run_drain` batch, potentially the rest of the batch); network calls
   precede acquisition; correctness is accepted; lock-hold/throughput is a
   runtime measurement obligation.

---

## 0d. Revision 4 — control-room runtime correction `4680380218` (2026-07-12)

The first observed Odoo.sh branch build was **RED**. The control room
classified the five failures as a **test-fixture isolation problem, not a
production-policy defect**, and issued a REVISE. This session merges the
current integration tip and corrects the fixtures. **The standard-runtime
gate remains OPEN — no green result is claimed; a rerun is still pending.**

### Failed build evidence (recorded verbatim, not reconciled)

- **Build / database:** `adamsmen-claude-product-import-completeness-010b-5l-34797217`
- **Odoo:** `19.0`
- **Verbatim final result:**
  `1 failed, 4 error(s) of 329 tests when loading database
  'adamsmen-claude-product-import-completeness-010b-5l-34797217'`
- **Product suite stat line (verbatim):**
  `shopify_connector_product: 102 tests 4.04s 7407 queries`
- **Product module summary (verbatim):**
  `Module shopify_connector_product: 1 failures, 4 errors of 94 tests`
- The three totals (`329`, `102`, `94`) are **quoted verbatim and NOT
  reconciled** (standing OP-43 caution against synthesizing test totals). The
  `shopify_connector_core` and `shopify_connector_sale` per-module stat lines
  were **not supplied to this session and are not fabricated**.
- **The suite halted after the five failures**, so tests ordered after them
  (structured media-cleanup, variant-generation, pricing, refresh, and
  rollback tests) never ran. The **Task 010B standard-runtime gate is OPEN.**

### The five failures — confirmed against the real test + production source

Root cause (single class): **non-isolated global `product.attribute` fixture
names.** The Odoo test database's demo data already contains standard,
incompatible (`create_variant='always'`) attributes named `Color`, `Size`,
and `Material`. Any success-path fixture whose payload top-level `options`
named one of them resolved that pre-existing incompatible attribute through
the accepted compatibility gate.

1. `TestProductAttributeImport.test_case_insensitive_compatible_dynamic_reuse`
   — **the `1 failed`** (assertion). It created a compatible dynamic `Color`
   but asserted an **absolute** same-name count of one; the standard `Color`
   in the DB made the count ≥ 2. The production path still correctly selected
   the test-created compatible dynamic attribute; only the absolute-count
   assertion was invalid.
2. `TestProductAttributeImport.test_option_position_order_preserved` — an
   **error**. Success-path option names `Color` / `Size` hit the pre-existing
   incompatible attributes → `binding_conflict` under the default
   `manual_review` mode.
3. `TestProductAttributeImport.test_sequential_reresolve_is_idempotent` — an
   **error**. Success-path name `Material` collided with existing Odoo data.
4. `TestProductDuplicatePrevention.test_structured_reimport_is_idempotent_no_duplicates`
   — an **error**. Success-path name `Color`.
5. `TestProductMediaImport.test_only_one_staged_image_open_at_a_time` — an
   **error**. Success-path structured option `Color`.

### Production policy is UNCHANGED (no production file touched)

The accepted rule is confirmed correct and left byte-for-byte unchanged
(`_resolve_or_create_attribute`, importer §991-1028): reuse a same-name
attribute **only** when `create_variant=='dynamic'`; an incompatible
same-name attribute fails closed (`binding_conflict`) under `manual_review`
or yields a distinct `"<name> (Shopify)"` under `connector_owned`; a merchant
attribute is never mutated. The failures proved the *tests* depended on
global names, not that the *policy* was wrong. **No production behaviour was
weakened to make tests pass.**

### Correction — task-unique `SC010B `-prefixed fixtures

Every fixture whose payload top-level `options` is resolved into a
`product.attribute` (success-path **and** intentional-conflict) now uses a
task-unique `SC010B ...` name that cannot collide with standard Odoo demo
data. Value names (`Red`/`Blue`/`S`/`M`/…), snapshot-only strings,
pure-function inputs, and archived-unbound fixtures are **left unchanged**.
Intentional-conflict tests keep their genuine conflict by **explicitly
creating the incompatible attribute in-test** under the new unique name, so
the conflict no longer depends on (or is masked by) demo data.

The five known failures corrected:

- `test_case_insensitive_compatible_dynamic_reuse` → attribute
  **`SC010B Color CI`** (dynamic); imported with the differently-cased
  `sc010b color ci`. The assertion now (a) captures the same-name count
  **immediately after** creating the controlled fixture, (b) proves the
  template uses that **exact** attribute, and (c) proves the import added
  **no** same-name attribute (**delta == 0**) — never an absolute global
  count of one.
- `test_option_position_order_preserved` → **`SC010B Position Color`** /
  **`SC010B Position Size`**.
- `test_sequential_reresolve_is_idempotent` → **`SC010B Material Resolve`**.
- `test_structured_reimport_is_idempotent_no_duplicates` →
  **`SC010B Structured Color`**.
- `test_only_one_staged_image_open_at_a_time` → **`SC010B Media Color`**.

### Full seven-file fixture-collision audit (result)

All seven Task 010B standard test files were audited against the real
importer flow. A test is collision-prone **iff** its payload top-level
`options` names an attribute that reaches `_create_structured_template`
(non-archived create/refresh success path or an intentional-conflict test).
Additional collision-prone tests found and corrected beyond the five:

- **`test_product_attribute_import.py`** — `test_create_new_dynamic_attribute_and_line`
  (`Fabric`→`SC010B Attr Fabric`); `test_additive_value_reuses_existing_value_case_insensitive`
  (`Shade`→`SC010B Attr Shade`); and the intentional-conflict / connector-owned
  set made controlled+unambiguous: `test_existing_always_attribute_routes_manual_review_by_default`
  (`SC010B Conflict Always`), `test_existing_no_variant_attribute_routes_manual_review_by_default`
  (`SC010B Conflict NoVariant`), `test_connector_owned_creates_distinct_shopify_attribute`
  (`SC010B Conflict Owned`), `test_brownfield_incompatible_attribute_makes_no_phantom_variants`
  (`SC010B Conflict Brownfield`), the `_run_connector_owned_refresh` helper
  (`SC010B Refresh Owned`), and `test_refresh_fails_closed_when_both_plain_and_shopify_lines_exist`
  (`SC010B Ambiguous Color` + `SC010B Ambiguous Color (Shopify)`).
- **`test_product_duplicate_prevention.py`** —
  `test_structured_import_failure_rolls_back_new_attributes` (`Cut`→`SC010B
  Structured Cut`; absent option `Phantom`→`SC010B Phantom`).
- **`test_product_media_import.py`** —
  `test_staged_media_paths_removed_after_database_failure` (`SC010B Media
  Color`; absent option `SC010B Media Phantom`).
- **`test_product_variant_generation.py`** — `test_sparse_two_option_set_no_cartesian_extras`,
  `test_sparse_three_option_set_exact_equality`, `test_variant_bindings_map_to_correct_products`,
  `test_reimport_is_idempotent_no_duplicate_variants`, `test_refresh_adds_new_remote_variant`
  (`SC010B VG Color/Size/Fit`); `test_later_variant_failure_rolls_back_everything`
  (`SC010B VG Color` + absent `SC010B VG Finish`); `test_one_hundred_fifty_variant_paginated_fixture`
  (`SC010B VG Paginated`); the intentional-conflict `test_structural_mismatch_routes_to_binding_conflict`
  (`SC010B VG Grade`, still created `always` in-test).
- **`test_product_price_import.py`** — the `_size_payload` helper
  (`SC010B Price Size`) and the two multi-option tests
  (`SC010B Price Color/Size`); value names `S`/`M`/`Blue` (used by
  `_ptav_extra`) unchanged.
- **`test_product_refresh_and_stale.py`** —
  `test_structural_additions_apply_in_snapshot_only_mode` and
  `test_failed_changed_import_does_not_advance_updated_at`
  (`SC010B Refresh Color`; absent `SC010B Refresh Phantom`).
- **`test_product_import_matching.py`** — the shared `_single_option_pages` /
  `_paginated_execute` pagination helpers (`Edition`→`SC010B Paged Edition`).

**Deliberately left unchanged (verified genuinely safe — do not resolve an
attribute):** `test_normalize_options_sorts_by_position` (pure-function sort
of option dicts); `test_import_product_sync_only_issues_read_query_calls`
(the `Size` name is a `shopify_option_values` **snapshot string** — the
payload carries no top-level `options`, so nothing is resolved); and
`test_first_seen_archived_creates_no_master_or_binding` (an archived, unbound
product raises `mapping_missing` **before** any attribute resolution and
asserts zero attributes are created). This was a per-fixture audit, **not** a
blind global string replacement.

### Scope, guards, and remaining gate

- **Only the seven test files were authored-edited**, plus this validation
  record, the AR log (revision note under AR-046), the research handoff, and
  the PR body. **No production file changed** (`models/**`, `__manifest__.py`,
  `data/**`, `security/**`, XML, CSV, migrations are byte-identical to the
  post-merge head). No new file added. No test tag / base class changed. The
  total test-method inventory across the seven files is unchanged
  (16/12/57/26/9/20/8 = 148). `py_compile` clean on all seven.
- **Base aligned first:** the current `Shopify-connector` tip
  `ce504f42824807e215ee21df3dfd4eed9bb9a275` (PR #154, CORE-R2, AR-047) was
  merged normally (no rebase/force/squash) before the fixture edits; the only
  conflict was the shared `architecture-review-log.md`, resolved keeping both
  the AR-046 and AR-047 rows in monotonic order (AR-043, AR-044, AR-046,
  AR-047; AR-045 remains reserved for Task 011B / PR #150 and absent here);
  `research-handoff.md` auto-merged preserving both the CORE-R2 and Task 010B
  histories.
- **Runtime rerun still PENDING.** The corrected suite has **not** been run on
  Odoo.sh from this Git session (no Odoo runtime, no Odoo.sh access). No green
  result is claimed. The control room / operator must rerun the three standard
  suites at the corrected head and record the verbatim `0 failed / 0 error(s)`
  totals before the standard-runtime gate can close. Live/dev-store Shopify
  fixtures remain gated on CORE-R2 runtime-green.

---

## 1. Base verification (hard prerequisite)

- **Original required base SHA:** `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`
  (PR #149 / CORE-R1 merge). The branch was created from it.
- **Base advanced (Revision 3, review `4951145191` item 4):**
  `Shopify-connector` moved to
  `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f` after PR #153 merged. That
  exact tip is merged into this branch with a normal merge commit (clean;
  PR #153 evidence preserved — §0c).
- **Base advanced again (validation session, acceptance `4951264328`):**
  `Shopify-connector` moved to
  `65e915aada32930a19a14c94d23dc9bd5e6fb517` after PR #152 (U0 operator-UI
  visual prototype) merged. That exact tip is merged into this branch with a
  normal merge commit (`b0d8c7b…`, no rebase/force). The only content overlap
  was `docs/01-research/research-handoff.md`, resolved to preserve **both**
  the U0 entry and the Task 010B entries; all U0 artifacts under
  `docs/09-ui-prototype/**` are added by the merge unchanged. The PR diff
  relative to `65e915a` contains **only Task 010B-owned changes** (the
  `shopify_connector_product` addon + the four Task 010B docs); no U0 file,
  no Task 011B / CORE-R2 / customer / order / sale file appears as a PR
  change.
- **Base advanced again (base-sync amendment, 2026-07-12):**
  `Shopify-connector` moved to
  `cfdb05703a65f82b34a9a11364aab6fc960cca9d` via merged **PR #155** (U0
  acceptance closure). That exact tip is merged into this branch with a normal
  merge commit (no rebase/force). PR #155's U0 closure records — a new handoff
  top entry, the U0 **AR-044** row, the master-plan U0 status, and the
  `docs/09-ui-prototype/**` updates — are preserved unchanged. The **AR-044
  collision** (the Task 010B architecture-review row was also drafted as
  AR-044) was resolved per control-room item 7 by renumbering the Task 010B
  row + its four revision notes **AR-044 → AR-046**; U0 keeps AR-044 (not
  overwritten or combined). The two shared-doc conflicts were resolved by
  retaining both sides completely; **no addon or test file conflicted.** The
  PR diff versus `cfdb057` remains **Task-010B-only** (the addon + the four
  Task 010B docs) plus the AR renumber. **The current integration base is
  `cfdb05703a65f82b34a9a11364aab6fc960cca9d`; the base-sync head carries no
  code change from the `b0d8c7b` implementation head.**
- **`Shopify-connector` tip at original session start:**
  `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` — **exact match, no drift.**
- **PR #149** (CORE-R1) verified **merged** via GitHub
  (`merged_at 2026-07-11T20:50:22Z`); its merge commit is the branch tip.
- **Gate comment `4948723366`** read verbatim: *"Task 010B implementation
  gate opened by ChatGPT. Required base:
  `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`. One draft implementation PR
  only. All other task gates remain closed."*
- **Branch:** `claude/product-import-completeness-010b-5l07ci` (the
  session's designated branch, created from the verified base SHA).
- No STOP condition triggered: the packet does not conflict with the
  merged implementation, every Odoo 19 API named in the packet was
  verified against the actual 19.0 source (matches — §3), every Shopify
  2026-07 field was verified (§4), and the allowed-files list is
  structurally sufficient (§7).

## 2. Exact changed files (21, all inside the packet allowlist)

**Production/model:**
1. `addons/shopify_connector_product/models/shopify_connector_product_importer.py` (rewrite: D-010B-1..12)
2. `addons/shopify_connector_product/models/shopify_connector_product_template_binding.py` (+`shopify_image_checksum`)
3. `addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py` (+`shopify_image_checksum`)
4. `addons/shopify_connector_product/models/shopify_connector_product_product.py` (NEW — `_inherit product.product`: `shopify_compare_at_price`)
5. `addons/shopify_connector_product/models/shopify_connector_store_settings.py` (NEW — `_inherit`: the 3 §4 settings)
6. `addons/shopify_connector_product/models/shopify_connector_attribute_lock.py` (NEW — singleton lock model)
7. `addons/shopify_connector_product/models/__init__.py` (import lines)

**Data/security/manifest:**
8. `addons/shopify_connector_product/data/shopify_connector_attribute_lock.xml` (NEW — one `noupdate=1` lock row)
9. `addons/shopify_connector_product/security/ir.model.access.csv` (one row for the lock model only)
10. `addons/shopify_connector_product/__manifest__.py` (data entry + version bump `19.0.1.0.0`→`19.0.2.0.0`)

**Tests:**
11. `addons/shopify_connector_product/tests/test_product_import_matching.py` (pagination updates)
12. `addons/shopify_connector_product/tests/test_product_duplicate_prevention.py` (structured atomicity/idempotency)
13. `addons/shopify_connector_product/tests/test_product_attribute_import.py` (NEW)
14. `addons/shopify_connector_product/tests/test_product_variant_generation.py` (NEW)
15. `addons/shopify_connector_product/tests/test_product_price_import.py` (NEW)
16. `addons/shopify_connector_product/tests/test_product_media_import.py` (NEW)
17. `addons/shopify_connector_product/tests/test_product_refresh_and_stale.py` (NEW)
18. `addons/shopify_connector_product/tests/__init__.py` (import lines)

**Documentation:**
19. `docs/05-qa/task-010b-validation-results.md` (this file, NEW)
20. `docs/05-qa/architecture-review-log.md` (one AR row appended)
21. `docs/01-research/research-handoff.md` (one top entry added)

**No forbidden file changed:** no `shopify_connector_core` or
`shopify_connector_sale` file; no `adams_base`; no inventory/stock model;
no Shopify mutation; no cron/migration/CI/UI/webhook/OAuth file; `main`
and plain `dev` untouched.

## 3. Odoo 19.0 internal-API verification (actual source, not memory)

All facts below were read from the **actual Odoo 19.0 source** this
session (raw `odoo/odoo@19.0` files) and match the packet's assumptions.

| API | Verified fact | Source |
| --- | --- | --- |
| `product.attribute.create_variant` | Selection `[('always','Instantly'),('dynamic','Dynamically'),('no_variant','Never')]`, default `'always'`. `write()` **raises `UserError`** if `create_variant` changes while `number_related_products` is set — mode is immutable once used. | `addons/product/models/product_attribute.py` |
| `product.template._create_product_variant` | `def _create_product_variant(self, combination, log_warning=False)`; arg is a `product.template.attribute.value` recordset; returns the `product.product`; *"possible to create only if the template has dynamic attributes and the combination itself is possible"*; reactivates an archived variant. | `addons/product/models/product_template.py` |
| dynamic variant generation | `_create_variant_ids()` with dynamic attributes **skips** cartesian auto-generation; variants are made on-demand via `_create_product_variant`. Also `_get_variant_for_combination(combination)` resolves an existing variant. | `addons/product/models/product_template.py` |
| `product.template.attribute.line` | create() calls `_update_product_template_attribute_values()` and triggers `_create_variant_ids()`; `value_ids` (m2m `product.attribute.value`) generates `product_template_value_ids` (the PTAV set). | `addons/product/models/product_template_attribute_line.py` |
| `product.template.attribute.value.price_extra` | `fields.Float(string="Extra Price", default=0.0, min_display_digits='Product Price', ...)`; uniqueness `unique(attribute_line_id, product_attribute_value_id)`. | `addons/product/models/product_template_attribute_value.py` |
| `product.attribute.value` | `name` (Char, required, translate), `attribute_id` (required, cascade); **no** name/attribute SQL uniqueness → get-or-create by search is correct. `_order='attribute_id, sequence, id'`. | `addons/product/models/product_attribute_value.py` |
| `product.template.image_1920` | `product.template` `_inherit` includes `image.mixin` → `image_1920`. | `addons/product/models/product_template.py` |
| `product.product.image_variant_1920` | `image_variant_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)`. | `addons/product/models/product_product.py` |
| `BaseModel.try_lock_for_update` | `def try_lock_for_update(self, *, allow_referencing=False, limit=None) -> Self`: issues `SELECT ... FOR UPDATE SKIP LOCKED` (deliberately **not** NOWAIT); *"Skip locked records and browse the records that could be locked"*; returns the recordset of rows it could lock (**empty if already locked** by another transaction); lock held to transaction end. `lock_for_update()` raises `LockError` if not all rows lock. | `odoo/orm/models.py` |
| Product-Price precision | `decimal.precision` "Product Price" defaults to **2** digits; `res.currency` carries per-currency `rounding`/`decimal_places`. | `addons/product/data/product_data.xml`; captures §6 |

**Lock-design consequence (key finding):** `try_lock_for_update()` is
**non-blocking (SKIP LOCKED)**. This *supports the accepted D-010B-2
design as written*: the packet requires "never proceed with unprotected
creation when the lock is unavailable", which is only meaningful for a
non-blocking primitive. The importer acquires the singleton lock, and if
the recordset comes back empty (another transaction holds it) it raises
`concurrency_race_conflict` (an auto-retry class), so the import backs off
and, on a later attempt, acquires the lock, re-resolves, and reuses the
first transaction's committed attribute. No architecture change was
needed; no STOP was triggered.

## 4. Shopify Admin GraphQL 2026-07 verification

From the accepted captures (`../00-source-materials/odoo19-shopify-
official-captures-2026-07-11.md` §9/§11) and the official references they
cite:

- `Product.options { id name position optionValues { id name } }`, ≤3
  options; variant pagination via `variants(first: N, after: $cursor)` +
  `pageInfo { hasNextPage endCursor }`; **no documented default page
  size** → `first` is always explicit; a single product at the root can
  return up to 2,048 variants; the **2,048 variants/product** ceiling is
  GA for all merchants (changelog 2025-10-15).
- `ProductVariant.compareAtPrice`: *"The compare-at price of the variant
  in the default shop currency."*, type `Money`. `Money` is a decimal
  string ("19.99"); zero-decimal display currencies exist (formatting,
  not API-precision).
- Product deletion surfaces as a **null product node**; archival as
  `Product.status = ARCHIVED`.
- **Deprecation noted (honest):** `ProductVariant.image` is **Deprecated**
  in favour of `ProductVariant.media`; the accepted packet D-010B-1
  nevertheless names `image { url }` for a read, so this task uses the
  packet-named field and records the deprecation. A future task may
  migrate the variant-image read to `media`. `inventoryItem { id }` is
  requested per D-010B-1 but **never stored or acted on** (no inventory
  model is touched).

## 5. Implementation summary (D-010B-1 … D-010B-12)

- **D-010B-1 (query + pagination):** `PRODUCT_IMPORT_QUERY` extended to
  `id title status descriptionHtml vendor productType tags updatedAt
  featuredImage{url} options{id name position optionValues{id name}}` and
  `variants(first:100, after:$cursor){ nodes{ id sku barcode price
  compareAtPrice selectedOptions{name value} image{url} inventoryItem{id}
  } pageInfo{hasNextPage endCursor} }`. `import_product_sync` loops pages
  (cursor in-run only) until `hasNextPage` is false; `first` always
  explicit; accumulated cap 2,048 → `data_shape_schema_mismatch`;
  malformed pageInfo / missing endCursor with `hasNextPage` →
  `data_shape_schema_mismatch`. **Forward-progress + identity guards
  (§0b.1, §0c.1-2):** seen-cursor set rejects a repeated/non-progressing
  cursor; a continuing page with **zero nodes** is rejected (no forward
  progress); duplicate variant GIDs within/across pages and a product `id`
  mismatch are rejected; the first page's `updatedAt` (present/absent shape
  and value) must be carried unchanged on every later page (cross-page
  torn-read guard); a defensive `MAX_VARIANT_PAGES` backstop bounds the
  loop, which the zero-node rule + duplicate-GID guard + 2,048 cap already
  make finite. Never a mutation; client error taxonomy preserved.
- **D-010B-2 (attributes/values/lines + compatibility gate + lock):** for
  each option in position order, `product.attribute` resolved
  case-insensitively; reused **only** when `create_variant=='dynamic'`;
  incompatible `always`/`no_variant` same-name attribute → per
  `product_import_attribute_conflict_mode` (default `manual_review` →
  `binding_conflict`; `connector_owned` → distinct `"<name> (Shopify)"`
  dynamic attribute). Existing modes never changed. Values get-or-created
  under the resolved attribute; one line per option; `Title`/`Default
  Title` → no structure. Global serialization via
  `shopify.connector.attribute.lock._acquire_or_raise()`
  (`try_lock_for_update()`) before any global attribute resolve/create;
  unavailable lock → `concurrency_race_conflict`; a **real full-import
  two-connection test** (§0.7) proves exactly one attribute is created and
  the second import reuses it. Refresh resolves the exact Shopify-name or
  exact `"<name> (Shopify)"` line and fails closed if both exist (§0.6).
- **D-010B-3 (sparse variants):** every used attribute is dynamic; each
  Shopify variant's `selectedOptions` maps to the template PTAV
  combination and `product.template._create_product_variant` instantiates
  exactly that variant. Odoo variants ≡ Shopify variants; no cartesian
  phantoms; no index-0 fallback for multi-variant; structural mismatch on
  a merchant product → `binding_conflict`.
- **D-010B-4 (base price):** written only when
  `price_source_of_truth=='shopify_authoritative'` and the path may write
  (first import, or `shopify_fields` refresh). Single variant →
  `list_price=price`; multi → `list_price=min`; per-value deltas
  decomposed onto `price_extra` **only when the additive model fits
  exactly** (verified with `float_compare` at Product-Price precision),
  else `list_price=min` + one `price_undecomposable` note, snapshots keep
  fidelity. No binary-float equality.
- **D-010B-5 (compare-at):** `shopify_compare_at_price` on
  `product.product`, connector-maintained, populated during import,
  shop-currency semantics documented; no export; binding snapshots
  unchanged.
- **D-010B-6 (images):** primary product + per-variant only; HTTPS-only,
  redirects followed manually and only to HTTPS, content-type `image/*`
  and **never SVG**, 20 MB streamed cap, bounded timeouts, **no
  credential/token on the media request**; downloaded bytes **validated as
  a supported raster image via Pillow** (SVG markup / junk labelled
  `image/png` rejected, never exposing the body); writes
  `image_1920`/`image_variant_1920`; **checksum ownership compares the
  current Odoo image checksum against the recorded connector checksum**
  (§0.3) so a same-URL merchant edit/clear is protected, not silently
  skipped; each image streams into its **own secure `mkstemp` file, closed
  immediately** — only the path is retained, exactly one path is opened at a
  time for the write, and an `ExitStack` unlinks every path on all exit
  paths (O(1) open handles, bounded RAM — §0b.2, superseding the Revision-1
  `SpooledTemporaryFile` design); a mid-stream `iter_content` network error
  is classified `shopify_temporary_server_network` (§0b.3); per-store
  `product_import_media_enabled` (default True). Any fetch/validation
  failure → `shopify_temporary_server_network`, never a hold, and the
  partial staged file is unlinked (no body/path in the error).
- **D-010B-7 (safe refresh):** `product_import_refresh_mode`
  (`snapshot_only` default | `shopify_fields`). snapshot_only never
  overwrites merchant-editable Odoo fields; shopify_fields re-applies the
  Shopify-owned set (SoT price, connector images). Structural additions
  (new variants, additive values) apply in **both** modes. A real
  `updatedAt` short-circuit (§0.2) skips an unchanged product before any
  media/DB write via the new readonly `shopify_updated_at` binding field
  (stamped only after a complete success). Enqueue-level `payload_hash =
  updatedAt` is an **Area-6 obligation**, not implemented here (this task
  has no enqueue call site; a running job's payload hash is never
  mutated).
- **D-010B-8 (archived/deleted):** null product for a bound GID →
  binding+variant bindings `stale` + note, Odoo master untouched. `ARCHIVED`
  is routed **before the unchanged short-circuit and before any media
  download** (§0b.4, §0c.3): lifecycle status outranks the refresh
  optimization, so an active binding whose archived payload presents the
  same stored `updatedAt` still goes stale (never returned `unchanged`). A
  **bound** product → binding+variant bindings `stale` + audit-snapshot
  refresh, no media/master write (a broken image URL cannot block stale
  marking); a **first-seen, unbound** archived product creates **no** bare
  Odoo product/binding and raises the existing `mapping_missing` class. Null
  product with no binding → `data_shape_schema_mismatch`.
- **D-010B-9 (duplicate prevention + N+1):** match priority unchanged
  (binding→SKU→barcode→manual; no name matching). Per-variant full-table
  scans replaced by one prefetched binding map + batched SKU/barcode
  candidate searches per product. Both uniqueness constraints intact; no
  bypass flag.
- **D-010B-10 (atomicity):** one `self.env.cr.savepoint()` per product
  covers all writes; Shopify reads and image downloads run before the
  savepoint. A later-variant failure leaves no partial structure
  (including no orphan attribute).
- **D-010B-11 (performance):** N+1 removed; page-at-a-time processing;
  budgets not measured here (no runtime — §10).
- **D-010B-12 (job contract):** same job type `product_import_sync`, same
  handler/domain-flag/target, same error taxonomy, same retry behaviour.
  No new job type/flag/error class; no mutation.

## 6. Commands executed and local/static results

- `git fetch` state verified; branch at base SHA; working tree clean at start.
- `python3 -m compileall -q addons/shopify_connector_product/` → **clean**
  (all production and test files compile).
- Per-file `python3 -m py_compile` on every changed Python file → clean.
- XML well-formedness check on `data/shopify_connector_attribute_lock.xml`
  → well-formed.
- Source-guard greps (see §7).
- **No Odoo runtime is available in this environment** (`import odoo` →
  `ModuleNotFoundError`, same as the CORE-R1 session), so the test suite
  was **not executed here**; Odoo.sh execution is the runtime gate (§10).

## 7. Test inventory (static method counts, not Odoo test counts)

| File | `def test_*` methods |
| --- | --- |
| test_product_template_binding.py (unchanged) | 7 |
| test_product_variant_binding.py (unchanged) | 6 |
| test_product_import_matching.py | 57 |
| test_product_duplicate_prevention.py | 12 |
| test_product_attribute_import.py | 16 |
| test_product_variant_generation.py | 8 |
| test_product_price_import.py | 9 |
| test_product_media_import.py | 26 |
| test_product_refresh_and_stale.py | 20 |
| **Total** | **161** (155 at `8e3076e`; 135 at `5688ec1`; 110 at `1065cdf`; 61 at CORE-R1) |

Coverage maps to every §21 named case plus reviews `4950202231` (items 1-8),
`4950339305` (items 1-5), and `4951145191` (items 1-3): pagination (250
across pages, 2,048 cap, malformed pageInfo, missing endCursor, no mutation;
**forward-progress and identity** — repeated/zero-node cursor,
**zero-node fresh-cursor loop**, cursor==current, replayed-seen cursor,
duplicate variant GID within/across pages, non-mapping node, missing-GID
node, product-GID mismatch, **cross-page updatedAt: identical accepted /
changed / first-missing-second-present / first-present-second-missing
blocked**, valid two-page accept);
attributes (ci dynamic reuse, new dynamic, Default-Title, position,
additive values, existing-`always`→manual-review, existing-`no_variant`→
manual-review, connector_owned `"Color (Shopify)"` + refresh both modes +
fail-closed, merchant unchanged, no phantom, brownfield, **overlapping
transactions → one attribute**); variants (sparse 2- and 3-option, exact
equality, no cartesian, deterministic re-import, structural mismatch →
binding_conflict, later-variant rollback); price (SoT both ways, unset,
single list_price, min, exact `price_extra`, undecomposable note, decimal
precision); images (primary, variant, unchanged skip, same-URL merchant
edit/clear ownership on template+variant, changed-URL protect, switch off,
HTTPS-only, redirect-to-non-HTTPS rejection, wrong content-type, **SVG
reject**, **invalid-bytes-labelled-png reject**, oversized,
timeout/network, **mid-stream `iter_content` failure**, no secret, no body
in error; **staging** — plan holds closed paths not open handles,
one-open-at-a-time read, path removal after success/DB-failure/validation-
failure, no path in error); refresh/stale (snapshot_only, shopify_fields,
structural adds in both, real updatedAt short-circuit + stamp-after-success
+ no-advance-on-failure + empty-never-short-circuits; **archived routed
before media AND before the unchanged short-circuit** — bound→stale with no
`_prepare_media`, broken-URL cannot block stale, bound master unchanged,
**archived-outranks-unchanged (identical stored updatedAt still goes
stale)**, first-seen unbound→`mapping_missing` creating nothing;
deleted-bound→stale, deleted-unbound→data-error, no Odoo deletion,
source-level declared-write guard).

## 8. Source-level guards, sudo inventory, network behaviour

- **Query-only / no mutation:** `PRODUCT_IMPORT_QUERY` starts with `query`
  and contains no `mutation` (grep + test asserted).
- **No bypass flags:** none of `bypass`/`force_create`/`skip_gate`/
  `skip_duplicate`/`ignore_duplicate`/`allow_blind` appear (test asserted).
- **No customer/order/inventory/fulfilment models:** no `sale.order`,
  `res.partner`, `stock.*`, `account.*`, `delivery.carrier` in the model
  files (grep + test asserted).
- **Savepoint:** `self.env.cr.savepoint()` present (test asserted).
- **`list_price` write locality:** every `list_price` assignment lives
  inside `_apply_prices` (source-level test asserted).
- **Sudo inventory:** **zero new `sudo()` sites** in any
  `shopify_connector_product` file (grep clean). Job-log notes are emitted
  through the sanctioned core `job.log._system_append()` path (which
  itself holds the one authorized job-log sudo) — no new elevated context.
- **Media request carries no secret:** `_fetch_image` attaches no headers
  and no auth; the importer file contains neither `X-Shopify-Access-Token`
  nor `_get_access_token` (test asserted). HTTPS-only, redirect-HTTPS-only,
  content-type `image/*`, 20 MB streamed cap, bounded timeouts.

## 9. Performance evidence

Not measured in this session (no Odoo runtime, no dev store). The N+1
per-variant full-table scans are removed by construction (one prefetch +
batched candidate searches per product). The p95 budgets (100-variant
≤10 s excl. images; ≤60 s incl. images) and the 2,048-variant timing probe
are dev-store measurements deferred to the runtime validation session
(§10). No optimization weakened duplicate protection, merchant-edit
protection, or atomicity.

## 10. Mandatory runtime/live evidence still outstanding (honest)

**Runtime-correction note (2026-07-12, review `4680380218`).** The first
observed Odoo.sh build (`…-34797217`, Odoo 19.0) was **RED** —
`1 failed, 4 error(s) of 329 tests` — and the suite halted after five
failures caused by **non-isolated global product-attribute fixture names**
(§0d records the verbatim evidence, the five failures, the root cause, the
unchanged production policy, the exact tests corrected, and the full
seven-file audit). The fixtures are corrected in this session; **the Odoo.sh
rerun is still pending and no green result is claimed.** Head references
below (`b0d8c7b`) predate the CORE-R2 base merge (`ce504f`) and the fixture
correction; the rerun must target the corrected head.

**Validation session note (2026-07-12, acceptance `4951264328`).** The
control-room review accepted the four Revision-3 corrections and authorized
the **base-alignment + Odoo.sh runtime validation** session. In this session:

- **Base alignment: DONE.** `Shopify-connector` (`65e915a`, PR #152) was
  merged into the branch with a normal merge commit (`b0d8c7b`, no
  rebase/force); the sole `research-handoff.md` conflict was resolved
  preserving both the U0 and Task 010B entries; all U0 artifacts are added
  unchanged; the PR diff vs `65e915a` is Task-010B-only (verified). Validated
  head = `b0d8c7be43e7d7e32d2344355b96cf0dd246f636`.
- **Odoo.sh three-suite run: NOT executed or observed in this session, and
  therefore NOT recorded as evidence.** This Git execution environment has
  **no Odoo runtime** (`import odoo` → `ModuleNotFoundError`; no
  `odoo`/`odoo-bin` on PATH), **no Odoo.sh access** (no Odoo.sh CLI, no
  credentials/env), and the PR head carries **no CI check-run or commit
  status** (`get_check_runs` total 0; combined status has zero contexts; the
  repo has no `.github/workflows`). No Odoo.sh build output was provided to
  this session to record. Per project governance (no faked evidence), the
  verbatim three-suite summary is **left blank and outstanding** rather than
  fabricated. The Odoo.sh run must be executed/observed on the Odoo.sh
  platform (by the control room / project owner) at head `b0d8c7b`, and its
  verbatim `0 failed / 0 error(s)` totals + build identity recorded here.

Not obtained this session and **required before merge acceptance**:

- **Odoo.sh:** full three-suite run (`shopify_connector_core`,
  `shopify_connector_product`, `shopify_connector_sale`) with exact
  verbatim totals, **0 failed / 0 error** — **at head `b0d8c7b`** (see the
  validation-session note above: not executable/observable from this Git
  session).
- **Live/dev-store (read-only):** three-option sparse product; a >100-
  variant product; the one 2,048-variant timing probe; product + variant
  images with refresh + merchant-image-protection; an archived product; a
  deleted bound product; an incompatible same-name Odoo attribute.
- **Lock-hold / throughput measurement (review `4950339305` item 5):**
  because the singleton attribute lock is transaction-scoped (held to outer
  commit, §0b.5), measure on Odoo.sh / dev-store the lock-hold duration, a
  competing import's retry/back-off behaviour, a structured product import
  inside a multi-job `run_drain` transaction, and the DB-phase timing at 100
  and 2,048 variants. Throughput is **not** claimed proven here.

**Runtime sequence (review `4951145191`):** (1) run the Odoo.sh full suites
and quote the exact result; (2) the **live/dev-store Shopify fixtures are
NOT yet authorized** — **CORE-R2 must be runtime-green before any live
validation of a domain handler that calls Shopify**; (3) keep PR #151 draft
and unmerged until the Odoo.sh evidence and the later authorized live-fixture
evidence are reviewed.

These are **not faked and not waived**. The PR is kept **draft**; a later
validation-only session (or an explicit ChatGPT waiver recorded at gate
time) closes them.

**Concurrency/lock accuracy note (honest, review `4950339305` item 5):** the
lock is transaction-scoped — releasing the per-product savepoint does not
release it; PostgreSQL holds the `FOR UPDATE` row lock until the outer
transaction commits/rolls back, so it can serialize the rest of that
transaction's DB work (and, in a `run_drain` batch spanning several jobs,
the remainder of that batch), not merely the attribute critical section.
Network downloads happen before the lock is acquired. The test
`test_overlapping_transactions_serialize_to_one_global_attribute` opens a
genuinely independent PostgreSQL connection with
`odoo.sql_db.db_connect(...).cursor()` — **not** `self.registry.cursor()`,
which in a `TransactionCase` returns a `TestCursor` on the same underlying
connection (one PG session, no real `FOR UPDATE SKIP LOCKED` contention). It
is deliberately **overlapping, not simultaneous**: transaction B finishes
its import first and stays uncommitted holding the lock, then transaction A
runs and receives `concurrency_race_conflict`; after B commits, A retries
and reuses the committed attribute (exactly one attribute; both bound;
durable cleanup via a third independent connection). `TransactionCase`
cannot exercise true multi-worker/multi-server execution; that named caveat
stands and is the subject of the dev-store validation.

## 11. Rollback

Rollback is the single-PR revert. It removes the new import behaviour but
does **not** drop the additive columns
(`shopify_image_checksum` ×2, `shopify_compare_at_price`) or the lock
table/row, and does **not** delete imported products, attributes, values,
images, or bindings — those remain as ordinary Odoo master data. Any
optional schema cleanup is a separately tested migration, never part of
the revert. No destructive migration is part of this task.

## 12. Definition-of-done checklist

- [x] Original base SHA verified (`f9c3c5f…`); PR #149 merged; gate
      `4948723366` read. **Base advanced to `fcbbb0b…` (PR #153) and merged
      into this branch, clean, PR #153 evidence preserved (§0c).**
- [x] Only allowed files changed (no forbidden file); Revision 3 touched the
      importer, two test files, the packet, and three docs (+ the base merge).
- [x] D-010B-1 … D-010B-12 implemented.
- [x] Odoo 19 internals verified against actual 19.0 source before use.
- [x] Shopify 2026-07 fields verified (variant-`image` deprecation noted).
- [x] All required tests exist (161 methods; every §21 case + reviews
      `4950202231` items 1-8, `4950339305` items 1-5, `4951145191` items 1-3).
- [x] All locally executable checks pass (compileall, py_compile, XML,
      source guards).
- [x] No Shopify mutation; no phantom Odoo variants; import atomic;
      merchant images protected; price writes respect SoT; archived/deleted
      never delete Odoo master data; a first-seen archived product creates
      no Odoo master data (`mapping_missing`).
- [x] Pagination cannot loop forever (zero-node forward-progress + seen-cursor
      + defensive page ceiling) or import an overlapping/torn page
      (variant/product identity + cross-page `updatedAt` guards).
- [x] Lifecycle status outranks the unchanged short-circuit (archived routed
      before `_unchanged_short_circuit` and media).
- [x] Media staging uses O(1) open handles / bounded RAM with deterministic
      unlink on every exit path; mid-stream network errors are classified.
- [x] Attribute-lock behaviour unchanged; its transaction-scope wording
      corrected everywhere including the **authoritative packet** (dated
      supersession note, stale statements annotated); the overlapping-
      transaction test is named and described accurately (not "simultaneous").
- [x] Validation record (this file) + AR row + handoff entry.
- [x] Draft PR opened into `Shopify-connector`; session stops after.
- [x] Base aligned to the current integration tip `65e915a` (PR #152) via a
      normal merge commit `b0d8c7b` (no rebase/force); handoff conflict
      resolved preserving both sides; PR diff Task-010B-only (§1, §10 note).
- [x] **Base re-aligned to the current integration tip `ce504f` (PR #154,
      CORE-R2, AR-047) via a normal merge; AR-046/AR-047 rows both preserved
      in monotonic order; CORE-R2 + Task 010B handoff histories preserved
      (§0d).**
- [x] **Runtime fixture correction applied (§0d): the five failing fixtures
      and every other collision-prone success/conflict fixture across the
      seven test files renamed to task-unique `SC010B ` names; production
      files byte-identical; test-method inventory unchanged (148); `py_compile`
      clean.**
- [ ] **Odoo.sh green (verbatim) at the corrected head** — **still OPEN**; the
      first build (`…-34797217`) was RED and the corrected suite has **not**
      been rerun from this Git session (no Odoo runtime / Odoo.sh access) —
      §0d + §10 runtime-correction note.
- [ ] **Live/dev-store evidence** — outstanding; **live Shopify fixtures gated
      on CORE-R2 runtime-green** (§10).

All other task gates (011B, LC-1, 012, Area 6, SEC-1, inventory,
fulfillment, product export, UI/Owl, webhooks, OAuth, PERF-1) stayed
**closed**; no other task was started or prepared.
