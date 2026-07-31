# PR #204 — Batch 2 P0 merchant reachability

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

---

# UNIFIED BATCH 2 REAL-DATA AND COMPANY-ISOLATION CORRECTION (2026-07-31)

> **This section is current and supersedes every head-SHA, test-count and
> evidence statement below it.** It is an ADDITIVE correction to Unified
> Batch 2 — not Batch 3, not a redesign, not an independent review, not an
> Odoo.sh campaign, and not an authorization to reopen Batch 1. Everything
> below this section is retained verbatim and remains accurate for the head it
> describes.
>
> **Nothing here is acceptance.** The implementing session does not review,
> accept, ready-mark or merge its own work.

## C1. The ruling, and the head it was made against

| | |
| --- | --- |
| Starting correction head (control-room verified) | `ccad8bf432868650abb80bfb2103bd8d397be549` |
| Batch 2 baseline | `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run |
| Independent review verdict | **CORRECTION REQUIRED** |
| History | **additive only** — no amend, rebase, squash, reset or force-push |

Identity gate, verified before any edit: PR #204 open, draft, unmerged, with
**no reviews at all** (therefore unapproved); head exactly `ccad8bf`; base
exactly `87f1763a`; `ccad8bf` exactly **10 ahead / 0 behind** `b0dbba2` with
`b0dbba2` as merge base; no commit after `ccad8bf` on the remote; clean
worktree; Odoo checkout verified at the pin; the `b0dbba2..ccad8bf` comparison
exactly **58 paths, 11,121 additions, 55 deletions**; and `ccad8bf` itself
touching only the three recorded documentation paths.

### The additive chain this correction adds

| Commit | What it is |
| --- | --- |
| `5a020779029781868cde0e1c7fc7853e8f5b42dd` | the whole production correction and its tests — **the final executable/test/tooling head** |
| `ad8763d2439baa93cda9f7eca84dc4fbd5b69985` | the records: this section, the handoff entry, TD-023/TD-024, the reproducer evidence README |
| `0bfeb2dca2cd45cbe8c2dcf0a6ca4edbea61d656` | the definitive seven-pass result and the retained summary |
| `24b921181d6ab12ec9e0c30a0435e5cdb2d11f82` | one COMMENT line in `shopify_connector_tax_mapping.py` naming the equivalence test correctly, plus this table |

`ad8763d` and `0bfeb2d` change **only** `docs/**`. `24b9211` touches one
executable file and changes **comment text only** — no behaviour, no signature,
no test — which is why the local seven-pass run at `5a02077` remains valid
evidence for what this branch ships, and why the exact-head CI below re-executes
the whole suite on the final head rather than being asked to take that on
trust.

**The earlier exact-head CI evidence at `ccad8bf` is not relabelled here.** It
remains valid for what it executed and is not acceptance evidence for this
correction: its fixtures did not represent the affected production data
shapes, which is precisely what the review found.

## C2. The seven mandatory corrections

### F1/F2/F3 — product and variant decision identity, and matching evidence

**Reproduced before correcting.** `safe_match_preview` is a DISPLAY scrubber
whose phone pattern is `(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)` — a leading digit,
six or more digit/separator characters, a trailing digit. `v1` ran the Shopify
Product GID, the ProductVariant GID, the remote `updatedAt` and the exact
SKU/barcode match values through it. Measured, on the shapes a real store
issues:

| Value | Stored by `v1` |
| --- | --- |
| `gid://shopify/Product/7346299043911` | `gid://shopify/Product/[redacted-phone]` |
| `gid://shopify/Product/9876543210987` | `gid://shopify/Product/[redacted-phone]` |
| `gid://shopify/ProductVariant/45123456789012` | `gid://shopify/ProductVariant/[redacted-phone]` |
| `1234567890123` (numeric SKU) | `[redacted-phone]` |
| `012-345-6789` (hyphenated numeric SKU) | `[redacted-phone]` |
| `0123456789012` (UPC-A) / `4006381333931` (EAN-13) | `[redacted-phone]` |
| `gid://shopify/Product/8201` (the OLD fixture) | **unchanged** |
| `DUP-TPL` (the OLD fixture) | **unchanged** |

The last two rows are why the suite was green: the pre-correction fixtures used
the two shapes the scrubber does not touch.

The consequences, each now covered by a named regression:

1. **A confirmed decision could never be consumed.** `_persist_decision` keyed
   on the sanitized identity; `_confirmed_for` computes its key from the RAW
   payload the importer just fetched. The two keys could not be equal, so
   confirming and resuming looped straight back to the same ambiguity.
2. **Two distinct products collapsed to one identity.** Both GIDs above
   sanitize identically, so with the same `updatedAt` they produced one
   `decision_key`. `_persist_decision`'s re-point branch would then hand
   product A's pending decision to product B's job — a reviewer deciding about
   A resuming the import of B.
3. **Supersession reached unrelated products.** `_supersede_stale_siblings`
   searched `shopify_product_gid = 'gid://shopify/Product/[redacted-phone]'`,
   which matched every product in the store whose suffix was long enough.
4. **The eligible set was empty.** `eligible_candidates()` searched
   `default_code in ['[redacted-phone]']`, which no Odoo record carries. The
   reviewer was asked to choose from nothing.

**The correction: identity, matching evidence and display evidence are three
different things.**

- `opaque_identity(value, limit)` — validates (string, non-empty, length-bounded,
  no C0/C1/DEL control characters) and returns the value **byte for byte**. No
  trim, no normalisation, no numeric-id extraction, no reconstruction. A value
  that fails returns `''` and the caller fails closed: the job still blocks and
  simply offers no decision.
- `match_value_digest(env, value)` — a **keyed, fixed-length** digest of the
  exact match value: `v2:` + HMAC-SHA256 under a domain-separated label and
  Odoo's own per-database `database.secret`. Keyed rather than bare, because a
  plain SHA-256 of a 12-digit UPC is not a redaction. The durable evidence and
  the job-log row therefore carry no merchant SKU or barcode at all, and exact
  matching is still exact.
- `safe_match_preview` survives **for the four `*_preview` display fields and
  nothing else**, and its docstring now says so.
- `eligible_candidates()` no longer searches the product table. It evaluates
  only the **bounded candidate snapshot the importer produced**, and membership
  of that snapshot is not eligibility: every candidate's LIVE identifier is
  digested and compared against the exact remote evidence, so a forged
  same-company candidate id is refused on its own data. Company agreement, the
  already-bound exclusion and (for variants) the resolved template are
  unchanged.
- `_supersede_stale_siblings` now carries `remote_updated_at <` beside the
  opaque identity leaves, so it retires the same product at an **older** remote
  identity and refuses to act where the byte order does not prove "older" —
  leaving that decision pending and unconsumable rather than guessing.
- Matching priority is unchanged (existing binding → exact SKU → exact barcode
  → manual decision), there is still no name matching (RA-006), no protected
  binding field became editable, and confirmation/resumption and
  binding-creation/consumption remain inside their existing atomic boundaries.

**Version and migration.** `MATCH_EVIDENCE_SCHEMA` is `product_match_decision.v2`,
`decision_key_for` emits a `v2:` prefix, and digests carry `v2:`. A `v1` key is
a different identity scheme and can never be consumed as this one.
`shopify_connector_product` moves **19.0.2.7.0 → 19.0.2.8.0** with migration
`19.0.2.8.0/post-migrate.py`, which:

- **supersedes** every `pending`/`confirmed` `v1` row with a stated reason —
  the transformation is not invertible, the original digits are nowhere in the
  database, and two products could produce one stored identity, so
  reinterpreting is a coin toss that can bind a catalog to the wrong master
  data. Those rows could never have been consumed anyway, so no import outcome
  changes; what changes is that an unactionable row stops looking actionable;
- leaves every `consumed` row and its binding **exactly** as they are;
- drops the obsolete `match_values` column so a display-sanitized copy cannot
  survive as a second, wrong answer to "what did Shopify send?";
- is idempotent and guarded against a missing table.

### F4 — Odoo's effective tax-inclusion posture

`account.tax.price_include_override` is an **override** and is legitimately
empty on an ordinary tax. Odoo derives the real posture in
`_compute_price_include` (`addons/account/models/account_tax.py` at pin
`30bde9ff`): the override when set, otherwise the company default
`res.company.account_price_include`, whose own default is `tax_excluded`. Four
places compared the raw override, so on a default-configured company **no
ordinary tax was eligible for an excluded Shopify tax** — the merchant was told
to create the tax and come back, and creating it did not help because the new
tax also carried no override.

One rule now, in `shopify_connector_tax_mapping.py`:

- `tax_posture_included(tax)` — the per-record predicate, reading
  `tax.price_include`;
- `eligible_sale_tax_domain(company, price_included, amount)` — the search form,
  using the searchable `('price_include', '=', ...)` leaf. Odoo 19's boolean
  domain optimisation (`odoo/orm/domains.py::_optimize_boolean_in`) rewrites
  `in [False]` to `not in [True]`, which is the one shape
  `_search_price_include` accepts, so both postures resolve in SQL to the same
  override-or-company-default disjunction.

Both are used by all four authorities: the decision wizard's candidate list,
the mapping model's `_check_mapping_safety`, the importer's non-binding
suggestions, and the importer's `_validate_resolved_tax`. The last of those was
the one that mattered most — without it a mapping created through the corrected
dialog would have been refused on the very next import, so the merchant would
have mapped the tax and the order still would not have moved.
`_analytic_unit_for_excluded` is corrected for the same reason: it decides
whether to convert an inclusive figure, and reading the override there would
have produced wrong totals for a tax the corrected dialog now admits.

`test_the_wizard_and_the_constraint_share_one_effective_rule` puts every tax in
the database to both predicates, for both postures, and requires them to agree —
so the drift F4 found cannot recur silently. Eligibility is not broadened
anywhere else: exact company, active, sale, leaf percentage, exact rate, not
base-affecting and existing mapping uniqueness are all unchanged, and no tax is
ever created.

### F5 — tax-wizard company isolation

`store_id`, `company_id` and `shopify_order_gid` were `related` fields reaching
through `job_id`. Odoo 19 gives a related field `compute_sudo=True` by default
(`odoo/orm/fields.py`: `related_sudo` → `compute_sudo`; `Field.compute_value`
calls `records.sudo()`), so the chain answered as **superuser** whatever it was
asked — and every server-side guard lived on `default_get`/`action_confirm`,
which is the intended UI route and not what an RPC `create` takes.

- The three fields are now **validated snapshots**, not related fields.
- `create()` is overridden: capability assertion, job resolved in the caller's
  own environment, the real `check_access` on job and store, the active-company
  test, evidence validation, and then every identity value **re-derived** from
  the validated job. Caller-supplied snapshots are discarded, never trusted.
  The context fallback exists because `_add_missing_default_values` runs inside
  `super().create`, so a legitimate UI save arrives with no `job_id` at all.
- `write()` refuses every identity field outright; `account_tax_id` — the one
  thing being decided — stays writable.
- Both refusal paths raise **one opaque message**, so a cross-company probe
  learns nothing: not the store id or name, not the company, not the order GID,
  not the job's existence.
- **Transient-record ownership, restated because Odoo 19 no longer provides
  it.** `TransientModel`'s docstring still claims users may only access records
  they created, but `odoo/orm/models_transient.py` at the pin carries no
  `_check_access` override at all, and the ACL grants every Connector
  Administrator full CRUD. A `create_uid` record rule is added for the tax
  dialog **and** for the product match dialog, which carries the same class of
  snapshot. `perm_create` is deliberately excluded — creation is guarded on the
  server, the rule guards the row.

Confirmation still re-reads and revalidates the durable job and evidence.

### F6 — a uniqueness collision never substitutes a different choice

`_create_mapping` used to catch the `IntegrityError`, search for whatever row
held `UNIQUE(store_id, shopify_tax_evidence_key)`, and return it as the call's
result — so `action_confirm` reported success and resumed the order under a tax
the administrator had not chosen and was never shown.

Three outcomes now, and only the first proceeds:

1. a row exists **in this transaction's snapshot** and is **proved** to be the
   same decision (store, fingerprint, fingerprint version, inclusion posture
   and Odoo tax all equal) — the ordinary sequential case where a second order
   was blocked on a fingerprint mapped moments earlier;
2. a row exists and is a **different** choice — refused, always;
3. `create` collided with a row this snapshot cannot see (Odoo cursors run
   REPEATABLE READ, so a mapping committed after this transaction started is
   refused by the index while invisible to `search`) — nothing to compare
   against, so refused, with a sentence rather than a raw `IntegrityError`.

A refusal raises before `_resume_blocked_job`, so it leaves no mapping, no
resumed job and no audit entry claiming otherwise.

### F7 — "scheduled" means the cron is really on

Both projections read the store's scheduled-sync flag alone. That flag is an
INTENTION; `_cron_enqueue_order_scans` / `_cron_enqueue_product_scans` only run
while the cron this connector installed is active, and an administrator can
disable it in Settings → Technical → Scheduled Actions. The surface then said
"Scheduled import is on" while nothing would ever be enqueued.

`shopify.connector.store._connector_scheduler_is_active(cron_xmlid)` resolves
one **module-owned external id** through `env.ref` — elevation is never used to
DISCOVER a record — and only then reads `active` on that one row under
`sudo()`, because `ir.cron` is Administrator-only by ACL and an Operator
reading their own store's page is not one. It returns `False` for an
unresolvable id, a deleted row or anything that is not an `ir.cron`: an
unprovable scheduler is indistinguishable from a disabled one. The new
elevation is registered in the core sanctioned-`sudo()` inventory with its
justification, which is why that guard failed until it was.

Both merchant-facing copies now state that scheduled import needs **both** the
store setting and the connector's scheduled action, and that turning only the
store setting on would change nothing. Manual import, its role gate and the
real cron execution route are untouched; no second scheduler exists, and no
disabled cron is silently re-enabled.

### F9 — the record-rule comment

The comment claimed the decision model does not use the scope mixin and that
its store rule carries no `sec3_scope_quarantined` leaf. Both were false about
the rule standing beside it: the model inherits `shopify.connector.scope.mixin`,
declares three connector parent relations, and the production rule does carry
the leaf. The comment is corrected to describe the rule; **the rule was not
weakened to match the comment.**

### F10 — access before lock

`action_confirm` took `SELECT ... FOR UPDATE` by primary key **before** any
access check. That is raw SQL and answers to no ACL and no record rule, so a
caller naming a foreign company's decision id took a genuine write lock on that
row — blocking its legitimate reviewer for the life of the transaction — and
only afterwards learned they were not allowed to be there.

The order is now: capability assertion → `_validated_decision` in the caller's
own environment (decision, store and job `check_access`, plus the
active-company test) → the row lock → invalidate → the full revalidation again
under the lock. The lock is not weakened: the one-winner/one-refusal
concurrent-confirmation behaviour still rests on it, and generic optimistic
locking was not substituted.

## C3. The adjudicated limitations, recorded rather than closed

**F8 — classification-guard coverage (TD-023, Low).** The canonical Store
Settings classification guard covers `shopify_connector_core`,
`shopify_connector_product`, `shopify_connector_sale` and
`shopify_connector_inventory`. `shopify_connector_fulfillment` and
`shopify_connector_product_export` also extend the settings model and have no
classification test, so a field added to either is classified by nobody.
Recorded as bounded **test-hardening** debt; **no fulfillment or
product-export production code was modified.** The coverage is now asserted
rather than described: `CLASSIFIED_MODULES` and
`UNCLASSIFIED_CONTRIBUTING_MODULES` are checked against the live registry in
both directions, so a module gaining a test, a module ceasing to contribute, or
a seventh contributing module all fail a test.

**F11 — the initial-scan ceiling (TD-024, Medium).** One product scan reads
**100** products per page and refuses beyond **200** pages, so it covers at most
**20,000** products in the window it is scanning. Above that it fails closed:
no checkpoint advance, no partial success, no silent truncation — and **no
progress either**, because the next run restarts the same window and stops in
the same place. Since the first run has no lower bound at all (§8.1.8), the
whole catalog is in the first window and the ceiling is met on the very first
scan, so **a catalog above 20,000 products cannot complete an initial import at
all.** The operator-visible refusal now states the page size, the page ceiling,
the effective ceiling, that nothing was imported, that the checkpoint has not
moved, and that retrying stops in the same place. **No new scan architecture,
queue, dispatcher or cursor store was introduced.** The fix is bounded
resumable enumeration through the existing job mechanism, recorded as debt.

**UAT PREFLIGHT REQUIREMENT.** The controlled-Shopify/UAT preflight must verify
the target store holds fewer than 20,000 products before that campaign runs; if
it does not, the control room must adjudicate the scaling work first. A search
of the repository at this head found **no fact stating the controlled-UAT
catalog size**, so this is a preflight check rather than a known blocker — and
therefore not a hard stop for this correction.

**TD-004, TD-005 and TD-007 are retained byte-for-byte.** Nothing in this
correction touches them.

## C3b. Two scope readings, named rather than assumed

Both are inside the authorized areas on the reading below, and both are called
out here explicitly so the control room can reverse either without having to
find it in a diff.

**`shopify_connector_core/models/shopify_connector_store.py` gained one
method.** `_connector_scheduler_is_active` is the cron-truth half of the
scheduled-state projections that §11 authorizes for both the order and the
product surfaces. It lives in core because `shopify.connector.store` is
defined there and BOTH modules extend it; the alternative was two copies of
one elevated read in two modules, which is a worse answer to a
security-sensitive helper than one shared, registered, justified one. It is
registered in both core sanctioned-`sudo()` inventories with its rationale —
which is why those guards failed until it was.

**`shopify_connector_sale/models/shopify_connector_order_importer.py` gained
one correction beyond the two eligibility authorities.**
`_tax_suggestions` and `_validate_resolved_tax` are tax-mapping validation and
are squarely in scope. `_analytic_unit_for_excluded` is order-total
computation, and it is corrected because it reads the same raw
`price_include_override`: it decides whether to convert an inclusive figure,
so leaving it would mean the corrected dialog admits a tax whose orders are
then priced wrongly. Correcting the eligibility rule without it would have
introduced a totals defect that did not exist before.

## C4. The tests, and what makes them load-bearing

### The reproducers run at BOTH heads, and 13 of 17 fail at the starting one

Two files -- `shopify_connector_product/tests/test_batch2_correction_at_any_head.py`
and `shopify_connector_sale/tests/test_batch2_correction_at_any_head.py` --
drive PUBLIC production routes only and import nothing the starting head does
not already have, so the same code is a genuine before/after reproducer rather
than a description of one side. The `-standard` race class
`test_tax_mapping_race.py` is head-agnostic for the same reason.

Run against a CLEAN EXTERNAL WORKTREE at the unchanged `ccad8bf`, with only
those three files and their `tests/__init__.py` registration added and the
correction branch untouched: **13 failed, 0 error(s) of 17 tests.** The same
17 at the corrected head: **0 failed, 0 error(s) of 17 tests.** Both logs are
durable under
`docs/05-qa/evidence/batch-2-real-data-correction-2026-07-31/`, stored with a
`.txt` extension because the repository's `.gitignore` excludes `*.log` — a
`.log` file there would have been silently absent from the repository while its
README claimed it was present.

Every failure names its defect rather than merely differing:

| Reproducer | What `ccad8bf` actually did |
| --- | --- |
| `test_a_confirmed_decision_on_real_data_is_actually_consumed` | `40 not found in []` — the reviewer was offered nothing to choose |
| `test_the_stored_identity_is_the_identity_shopify_sent` | `'gid://shopify/Product/[redacted-phone]' != 'gid://shopify/Product/7346299043911'` |
| `test_two_real_products_never_share_or_repoint_one_decision` | `decision(6,) == decision(6,)` — two different Shopify products share one decision row |
| `test_a_foreign_decision_is_refused_before_its_row_is_locked` | `['SELECT id FROM shopify_connector_product_match_decision WHERE id = %s FOR UPDATE'] is not false` — the refused caller locked the row first |
| `test_an_ordinary_tax_is_eligible_for_an_excluded_shopify_tax` | `54 not found in []` — no ordinary tax was offered at all |
| `test_the_whole_tax_route_completes_on_an_ordinary_tax` | `account.tax(56,) not found in account.tax()` |
| `test_an_administrator_cannot_reach_a_foreign_job_through_the_dialog` | *"a company-A administrator created a tax decision dialog for a company-B job and can read store `'Any-head foreign store'`, company `'Any-head foreign co'` and order `'gid://shopify/Order/8800770066'` from it"* |
| `test_one_administrator_cannot_read_another_open_dialog` | `True is not false` — another administrator can read this open dialog |
| `test_a_different_choice_never_replaces_the_mapping_that_won` | `UserError not raised` — the substitution was reported as success |
| `test_a_competing_choice_committed_elsewhere_refuses_and_never_resumes` | the same, across a real commit boundary on a second backend |
| `test_scheduled_product_state_is_false_while_the_cron_is_disabled` | `True is not false` — the store claims scheduled import while the cron is off |
| `test_scheduled_order_state_is_false_while_the_cron_is_disabled` | the same, for orders |
| `test_the_scan_ceiling_refusal_states_the_limit_and_consequence` | `'100' not found in 'The product scan page ceiling was exceeded.'` |

The four that pass at BOTH heads are there deliberately and say so: the
display-scrubber measurement the rest of the file rests on, the two
"manual import still works and is still role-gated" guards, and the
supersession guard whose sharper twin is the re-point test.

### The concurrency proof is a real transaction boundary, not a mock

`test_tax_mapping_race.py` (`-standard`,
tag `shopify_connector_tax_mapping_race`, registered in the runner's
`NONSTANDARD_TAGS`) commits its fixture on its own connection, commits the
competing administrator's mapping on a SECOND connection with an asserted
distinct backend PID, then asserts that this transaction's REPEATABLE READ
snapshot genuinely cannot see the winner before driving the production
`action_confirm` into the real unique index. The final state is read on a
THIRD connection, so it is the committed database rather than this
transaction's opinion of it. Statement and lock timeouts are bounded, and the
committed rows are removed with their absence asserted -- through
`addClassCleanup`, because a cleanup registered inside a test body runs while
the test transaction still holds its foreign-key share lock on the store.

Patching `Mapping.create` to raise would have proved only that the `except`
branch is reachable, and would have said nothing about the branch that
mattered: the winner refused by the index while invisible to `search`.

### Everything else the correction owes

Product identity: real Product and ProductVariant GIDs stored and keyed
exactly; two products at one `updatedAt`; numeric SKU; hyphenated numeric SKU;
an EAN-13 barcode ambiguity built the only way Odoo 19's own per-company
uniqueness permits one (two companies, which is also where company scoping
matters most); the display preview asserted still sanitized on the same record
whose identity is asserted intact; the raw identifier asserted absent from the
job logs, the durable evidence, the job record and the digest column; a forged
same-company candidate refused on its live identifier; both complete routes end
to end; a changed `updatedAt` refusing the stale decision; one confirmation
resuming one job; and the §8.2.14 generic-review refusal unchanged.

Tax: both company-default postures with the override genuinely unset; a
matching explicit override still eligible; both ways of mismatching refused by
the dialog AND by the constraint; the shared-rule equivalence proof; the whole
route through to the importer accepting the mapping on the next attempt;
direct-create, write and read isolation; a non-disclosing refusal; and the
competing-choice refusals.

Migration: `test_product_match_decision_migration.py` builds rows shaped exactly
as `v1` wrote them and asserts the retirement, the untouched consumed row and
its identical `read()`, the untouched `v2` row, idempotency, the dropped column
(including when it is present), and the missing-table guard.

Fixture hardening: the product tour, the product journey and the browser
evidence seed now carry realistic numeric GIDs and identifiers, and the sale
journey and tour taxes no longer set `price_include_override` at all. The tour
asserts BOTH treatments on one dialog in a real browser -- `sku_preview`
showing `[redacted-phone]` and `shopify_product_gid` showing
`gid://shopify/Product/7346299043911`.

Zero live Shopify contact, and zero Shopify mutation: every test patches the
transport seams, and no credential exists anywhere in the repository or this
environment.

## C5. Definitive validation

Run with `tools/run_connector_suite.sh` and **no arguments**, at
`5a020779029781868cde0e1c7fc7853e8f5b42dd` — the final executable/test/tooling
head. The two commits after it change **only** documentation and evidence: a
changed-path comparison of `5a02077..ad8763d` and of the records tail shows
**zero** executable, test or tooling delta.

| Pass | Result | Tours | Migration scripts |
| --- | --- | --- | --- |
| Fresh install + standard suite | **0 failed, 0 error(s) of 2436 tests** | 36/36 | — |
| Warm `-u` (SAME-VERSION) + standard suite | **0 failed, 0 error(s) of 2436 tests** | 36/36 | **0, asserted** |
| Genuine migration `50b770a3` → candidate + standard suite | **0 failed, 0 error(s) of 2436 tests** | 36/36 | **3** (`core 19.0.1.16.0`, `core 19.0.1.17.0`, **`product 19.0.2.8.0`**) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2436 tests** | — | **0, asserted** |
| Genuine migration `0a15b176` → candidate + standard suite | **0 failed, 0 error(s) of 2436 tests** | 36/36 | **2** (`core 19.0.1.17.0`, **`product 19.0.2.8.0`**) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2436 tests** | — | **0, asserted** |
| Complete non-standard tag suite | **0 failed, 0 error(s) of 60 tests** | — | — |

**The correction's own migration executed for real in both upgrade passes.**
`shopify_connector_product` upgraded `19.0.2.4.0 → 19.0.2.8.0` and
`shopify_connector_sale` `19.0.2.4.0 → 19.0.2.7.0` from both older trees, so
these are genuine version-to-version upgrades rather than same-version
re-updates — Odoo runs an upgrade script only when the installed version is
strictly lower, and the runner FAILS a migration pass that ran no script.

All three HOOT suites verified (`shopify connector dashboard`,
`export diff`, `setup wizard`). The single sanctioned skip per standard pass
remains `TestMutationRecovery.test_real_process_death_harness`, unchanged in
identity and reason.

### Deltas against the correction's own baseline

Measured against `153be2b`/`ccad8bf` (2373 standard / 59 non-standard / 36
tours) in this same environment:

| | Baseline | This head | Delta |
| --- | --- | --- | --- |
| Standard suite | 2373 | **2436** | **+63** |
| Non-standard suite | 59 | **60** | **+1** (the genuine-connection tax-mapping race) |
| Tours | 36 | **36** | 0 — no tour was added; the existing product tour now drives production-shaped identity and asserts both treatments on one dialog |

### Recorded facts from `summary.json`

`connector_worktree_dirty: false`; `odoo_pin_verified: true` at
`30bde9ff758834a4912c5ae55843d3a7dad849f1`; `browser_evidence: verified`;
`required_tour_tests: 36`; `hoot_suites_executed: true`;
`shopify_operations: none`.

`source_head_verified: false` **and that is stated rather than glossed**: this
local invocation was made without `SOURCE_HEAD_SHA`, which only CI sets, so the
runner recorded the checkout SHA (`tested_checkout_sha`,
`connector_sha` = `5a02077`) without a declared head to compare it against. The
exact-head CI below is the run that performs that comparison.

Environment: Python 3.12.3, PostgreSQL 16.13, Chromium 141.0.7390.37, Odoo pin
`30bde9ff` verified on every pass, clean worktree. The summary is retained at
`docs/05-qa/evidence/batch-2-real-data-correction-2026-07-31/definitive-summary.json`.

**Evidence class: local/CI-grade supporting evidence — NOT Odoo.sh exact-SHA
acceptance (DEC-041 D8), NOT live-Shopify validation, NOT UAT.**

### Exact-head CI: NOT OBTAINED, and why — stated rather than omitted

**There is no green exact-head GitHub Actions run for this correction, and none
is claimed.** Every run triggered on the correction's heads failed to start.
The observation, not an inference:

| Head | Runs | Outcome |
| --- | --- | --- |
| `ad8763d` | push ×2, pull_request | `cancelled` (superseded by the next push — ordinary concurrency-group behaviour) |
| `0bfeb2d` | push ×2, pull_request | started 09:12–09:13, superseded by the next push |
| `e8840a2` | push ×2, pull_request | **`failure` after 2–7 seconds** |
| `e8840a2`, re-run | pull_request (attempt 2), push (attempt 2) | **`failure` after 2 seconds** |

Every failed job reports `runner_id: 0`, an empty `runner_name`, an empty
`runner_group_name`, **no steps at all**, and `HTTP 404` for its logs. The
workflow's first step never executed: no runner was ever assigned. Re-running
reproduced it identically on a second attempt. The same workflow, with the same
`ubuntu-24.04` label and the same file, ran to **success** on `ccad8bf` at
04:17 the same day
([30603786322](https://github.com/AdamsOdoo/Adams/actions/runs/30603786322),
[30603788886](https://github.com/AdamsOdoo/Adams/actions/runs/30603788886)).

That is an Actions **capacity or entitlement** condition on the repository, not
a result about this code — a failing suite produces steps, logs and a red step;
this produces none of those. This session very likely contributed to it: pushing
to both `fable/wave-5-completion` and the session's designated branch triggered
**three** ~50-minute runs per commit instead of two. Pushing to the second
branch has stopped.

**What this means for the evidence.** GitHub Actions was never the acceptance
authority here — it is supporting evidence, and DEC-041 D8 reserves acceptance
for an exact-SHA Odoo.sh run that this instruction forbids. The definitive
seven-pass validation above ran to completion **locally, at the pin, on a clean
worktree**, and the before/after reproducer evidence is durable in the
repository. What is missing is an independent second execution of the same
script on a clean runner. It should be re-triggered when the repository's
Actions capacity allows, and **until it is green nobody should read this
correction as CI-confirmed.**

## C6. Gates that remain

- **Independent review of this exact corrected head.** The implementing session
  does not review, accept, ready-mark or merge its own work, and has not.
- **The unfinished independent browser/mutation review** that the previous
  cycle left open still has to be completed **after** this correction, against
  this head rather than against `ccad8bf`.
- Exact-head **Odoo.sh** qualification. Not run here; this instruction forbids
  it, and nothing below is offered in its place.
- **Controlled live-Shopify validation**, whose preflight must now also verify
  the target store is under TD-024's 20,000-product ceiling.
- **Business UAT.**
- Control-room acceptance and merge authorization.

This PR stays draft. The PR body was not edited, no comment was posted, no
review was submitted or requested, nothing was approved, ready-marked or
merged, no Shopify request of any kind was made, and no credential was used.

---

> **RETAINED IN FULL, AND STILL ACCURATE FOR ITS OWN HEAD.** Everything below
> this line describes `ccad8bf` and its predecessors and is preserved verbatim
> rather than rewritten. The correction section above supersedes its head-SHA,
> test-count and evidence statements; its description of what Batch 2 built,
> and why, is unchanged and still stands.

---

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

# Batch 2 P0 merchant reachability (as recorded at `ccad8bf`)

> **This record supersedes its own earlier text and says so explicitly.** The
> version written at `9af8b23` stated that the commits were *"local only"* and
> that *"the branch `fable/wave-5-completion` remains at `b0dbba2a`"*. Both
> were true when they were written and became stale the moment the control
> room ruled that the durability recovery is accepted as preservation of
> provisional work. They are corrected below rather than deleted: the
> historical fact that the chain was unpushed at `9af8b23` is part of this
> campaign's record, and rewriting it away would be the same kind of quiet
> revision this project exists to avoid.
>
> **Nothing here is acceptance.** Every push described below is a preservation
> checkpoint. The work remains provisional until independent review.

## 1. Heads and history

| | |
| --- | --- |
| Batch 2 starting baseline | `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e` |
| Durability-recovery head (control-room verified) | `cb4efcde13792920275f0fd8edc0c06226b94fe9` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run |
| History | **additive only** — no amend, rebase, squash, reset or force-push |

### The additive chain

| Commit | What it is |
| --- | --- |
| `9a70682` | checkpoint 1 — canonical Store Settings |
| `f5f3668` | checkpoint 1 — the guards the new surface had to answer to |
| `39e5113` | checkpoint 2 — order controls and tax decisions |
| `2c5d190` | checkpoint 3 §8.1 — product enumeration producer |
| `9af8b23` | Batch 2 records (the ones this section corrects) |
| `cb4efcd` | restore the research handoff a prepend had truncated |
| `be7cc43` | §8.2 durable match decisions, §8.3 tests, §9 journeys |
| `68410fb` | §10 browser/accessibility campaign, records, TD-021/TD-022, handoff |
| `153be2b` | the tour-instrument correction the definitive run's migration pass found — **final executable/test/tooling head** |
| *(final)* | this validation record — documentation only, zero executable/test/tooling delta against `153be2b` |

### The handoff truncation, and the fix-forward

`cb4efcd` exists because a prepend to `docs/01-research/research-handoff.md`
replaced the file instead of extending it. The correction is **additive**: the
truncated content was restored forward as a new commit rather than by amending
the commit that lost it. The net delta of that file against `b0dbba2` is
**+104 / −0**, which is the check that the restoration put back exactly what
was lost and nothing else.

### Commit signing

Unavailable in this environment: the configured signing key is empty. Unsigned
additive commits are the accepted implementation deviation for this campaign,
per the control-room ruling. **No commit was amended, rebased or recreated to
obtain a signature** — doing so would have destroyed the additive history the
same ruling protects.

## 2. What Batch 2 set out to close, and where each part stands

| § | Deliverable | State |
| --- | --- | --- |
| Checkpoint 1 | Canonical Store Settings | Implemented (`9a70682`, `f5f3668`) |
| Checkpoint 2 | Order controls and the tax decision route | Implemented (`39e5113`) |
| §8.1 | Product enumeration producer | Implemented (`2c5d190`) |
| **§8.2** | **Durable product/variant match decisions** | **Implemented (`be7cc43`)** |
| **§8.3** | **Load-bearing product matching tests** | **Implemented (`be7cc43`)** |
| **§9** | **Consolidated vertical journeys C, D-P0, I, J-P0, K-P0** | **Implemented (`be7cc43`)** |
| **§10** | **Consolidated browser/responsive/accessibility campaign** | **Implemented (final head)** |
| §15.2 | Definitive seven-pass validation | **All seven passes green at `153be2b`** (§9 below) |

Checkpoints 1, 2 and §8.1 are described in §§3–5 of the retained record below.
This section covers what the continuation added.

## 3. §8.2 — the decision an ambiguous match never recorded

### The defect

When two Odoo products carry the SKU a Shopify product claims, the importer
refuses. That is correct: silently picking one binds a store's catalog to the
wrong master data. But refusing was the whole of it.

* `ambiguous_match` is a `MANUAL_REVIEW` class, so the dispatcher routes the
  job to `blocked_manual_review` — asserted against the dispatcher's real
  taxonomy, not against the phrase "blocked work".
* Both raise sites carried a human sentence and **no structured
  `technical_detail`**, so nothing downstream could tell which product, which
  variant, or which candidates the importer had seen.
* The only offered control was the generic `action_resolve_manual_review`,
  which re-queues the identical job so the identical search finds the identical
  two candidates and stops again. A merchant could press it forever.

### Why the decision cannot be written where the ambiguity is found

Both raise sites (`_resolve_template`, `_match_variant_candidate`) run inside
`import_product_sync`'s single `self.env.cr.savepoint()` block — the block that
exists so a failure half-way through a product leaves no partial product
behind. A decision created there is discarded by the same `ROLLBACK TO
SAVEPOINT` that discards the partial writes.

That is **measured, not assumed**:
`test_a_decision_written_inside_the_importer_savepoint_would_not_survive`
patches `_resolve_template` to create a decision immediately before the raise,
drives the real drain, and asserts the row is gone — while the production seam
records its own in the same run. If that ever stops being true the seam can be
simplified; while it is true, the seam is the only correct place.

So the evidence travels out on the exception — structured, sanitized and
size-bounded on `JobHandlerError.technical_detail` — and the decision is
written by a **product-owned override of `_route_failure`**, in the same
transaction that durably records the blocked job. `super()` is called first, so
the job is transitioned before anything is linked to it and a failure to record
can never leave the job un-routed. No second queue, no second dispatcher, no
side channel.

### The invariants, and what enforces each

| §8.2 requirement | What enforces it |
| --- | --- |
| 1. linkage (store, company, job, product GID, variant GID, remote identity, level, evidence, candidates, state) | Model fields on `shopify.connector.product.match.decision`, all `readonly=True` |
| 2. no secret or unnecessary PII | `safe_match_preview` — secret patterns, then email/phone, then a length bound, on every merchant-controlled string |
| 3. company-aware candidates, bound records excluded | `eligible_candidates()`; the exclusion set is read under `sudo()` **on purpose** — elevating an exclusion can only ever remove a candidate |
| 4. priority: binding → SKU → barcode → manual | The decision is consulted only where identifier matching has already produced an ambiguity |
| 5. never match by name | Unchanged (RA-006); `MATCH_KEYS` admits only `sku_reference` and `barcode` |
| 6. Reviewer or Administrator resolve; Operator may start, not decide | `_assert_match_decision_reviewer` — the same two groups `action_manual_retry` admits from `blocked_manual_review`, so the dialog cannot offer a consequence its caller would then be refused |
| 7. same-company eligible record only | Odoo's own `_check_company` (`_check_company_auto` + `check_company=True`), which holds under `sudo()` |
| 8. no "create new" | Not added |
| 9. confirm-time revalidation | `_validated_decision` + `_validated_choice` + `_assert_no_conflicting_binding`, all re-run at confirm |
| 10. atomic decision + consequence | The decision write and the resume share one savepoint |
| 11. exact remote identity only | The decision key carries the verbatim `updatedAt`; a changed product supersedes it and raises a fresh one |
| 12. row locks and uniqueness | `SELECT … FOR UPDATE` before the state is read; `UNIQUE(store_id, decision_key)` |
| 13. resume the exact work once | `action_manual_retry` on the source job — never a fresh scan |
| 14. generic Resolve Review refuses | `action_resolve_manual_review` override, naming the route that does work |
| 15. actor, time, evidence, choice, binding, job state | `resolved_uid`, `resolved_at`, the evidence fields, `selected_*`, `resulting_*_binding_id`, `resumed_job_state` + live `job_state` |
| 16. real surfaces expose it | Match Decisions workspace + the control on the blocked job; **no binding field made generically editable** |
| 17. attribute conflicts unchanged | `product_import_attribute_conflict_mode` untouched |

### Three design choices worth reading twice

**The key is hashed and length-prefixed.** `decision_key_for` joins
`(level, product GID, variant GID, updatedAt)` with each component's length in
front of it, then hashes. Without the length prefix, `('ab', 'c')` and
`('a', 'bc')` would collide — a test asserts they do not.

**The record-rule escape hatch is load-bearing, not defensive noise.** A domain
leaf across a Many2one compiles to `field IN (SELECT …)`, and a NULL `field`
matches no `IN` subquery. The selection rule's `('selected_template_id', '=',
False)` leaf is what stops it hiding every decision that has not been decided
yet — which is every decision a reviewer needs to see. This was found by the
rule hiding exactly those rows, not by inspection.

**SEC-3 is joined rather than resembled.** The decision points at a job and at
the bindings it produces, and one company may own several stores, so it
inherits `shopify.connector.scope.mixin`, declares all three relations, and is
registered in the SEC-3 ownership matrix. The matrix's own completeness test
(`test_no_durable_store_scoped_model_escapes_this_matrix`) is what caught the
omission — a red suite rather than a quiet gap.

### ACLs

Read-only for **every** connector role — Auditor, Operator, Reviewer,
Administrator. Nothing may create, write or unlink a decision over RPC. Every
production write goes through the dispatcher seam or the revalidated confirm
path, both under `sudo()`. Asserted per role rather than assumed.

## 4. §8.3 — the tests, and what makes them load-bearing

**42 new decision tests**, plus the checkpoint-3 producer tests that already
covered §8.3's enumeration half (routes, pagination, checkpointing, gates,
fail-closed page validation, coalescing). Every end-to-end test drives the real
drain loop with the transport patched at `_send`, and asserts **that work was
admitted** — the transport ran and the job moved — before asserting what the
database holds. A test that only asserts "no binding was created" passes
brilliantly against a run in which the importer was never invoked.

### Proved against their own absence

Each central control was removed or neutered and the test that claims it was
required to fail:

| Mutation | Caught by | Result |
| --- | --- | --- |
| M1 — the `_route_failure` override removed | `test_an_ambiguous_template_persists_a_durable_decision` | **CAUGHT** |
| M2 — the remote-identity check neutered in `_confirmed_for` | `test_the_importer_consumes_only_the_matching_remote_identity` | **CAUGHT** |
| M3 — eligibility recomputation removed at confirm | `test_an_ineligible_candidate_refuses` | **CAUGHT** |
| M4 — the company filter removed from `eligible_candidates` | `test_candidates_never_include_a_foreign_company_record` | **CAUGHT** |
| M5 — the generic-resolve refusal removed | `test_generic_resolve_review_refuses_while_a_decision_is_pending` | **CAUGHT** |
| M6 — the candidate-membership check removed at consumption | `test_a_decision_selecting_a_candidate_that_vanished_is_not_consumed` | **CAUGHT** |
| M7 — the row lock and pending revalidation removed at confirm | `test_a_second_confirmation_of_the_same_decision_refuses` | **CAUGHT** |
| M8 — stale-sibling supersession removed | `test_the_importer_consumes_only_the_matching_remote_identity` | **CAUGHT** |

**8 of 8 caught, 0 missed.** Each mutation was applied to the production file,
the named test run against it, and the file restored byte-for-byte — the
worktree is clean afterwards, so none of this is in the diff. M4 is the one
worth reading twice: the company filter in `eligible_candidates` looks
redundant beside Odoo's own product record rules, and it is not — the test runs
as an administrator with *both* companies active, so the record rule lets the
foreign product through and the connector's own filter is the only thing left.

### Two fixture defects found by writing them

**A variant-ambiguity test that was exercising template matching.**
`_resolve_variant_product` reaches `_match_variant_candidate` only when the
template was resolved by *candidate match*: an `existing_binding` template with
attribute lines is routed to `_instantiate_refresh_variant` and never performs
variant candidate search at all. The first fixture built the obvious shape — a
bound template with two same-SKU variants — and produced no variant ambiguity
whatsoever, so the test failed rather than passing vacuously. The corrected
fixture makes exactly one template carry the SKU (unambiguous template match)
and gives that template two variants that both carry it.

**A shared payload dict that one job's parse corrupted for the next.** A real
transport returns a freshly parsed body every time; the importer normalises in
place. Handing every call the same dict produced a bogus
`data_shape_schema_mismatch` several tests downstream. Every fixture body is
now deep-copied per call.

**A multi-company test that was measuring its own fixture.** A product with no
company is correctly shared by every company, so a "foreign candidate" test
built on company-less products proves nothing. Both sides now carry explicit
companies.

## 5. §9 — the consolidated vertical journeys

Each journey starts from a store an operator has just configured and ends at a
database consequence a merchant could see, with every step performed by the
code the UI invokes. Where a step must fail, it is made to fail **by real
data**, never by an injected exception.

**Journey C — product import.** Configure through Store Settings → press
`Import products now` → scan job → two children → dispatcher → importer. One
product completes unambiguously and binds on `sku_reference`; the other stops
with a durable decision. The scan's checkpoint advances (the *enumeration*
finished; the blocked child is separate work with its own state, which is the
honest reading and the one the store form shows). The decision is opened from
the job, the eligible set is the two candidates and nothing else, the choice is
confirmed, the exact job resumes — **no second scan** — and the final binding
carries `match_key = manual` and the reviewer's uid. The cron route is proved
to reach the same place.

**Journey D-P0 — orders and tax.** Configure sale prerequisites and scheduling
through Store Settings → press `Import orders now` → scan → enqueue →
dispatcher → importer meets a `TaxLine` with no mapping. The job stops at
`failed_retryable` / `odoo_validation_configuration` — the state the dispatcher
really produces for that class — and **no order is created from a payload the
connector could not price**. It is mapped through an explicit same-company
choice, the exact order job resumes without a fresh scan, the order is created,
and the mapped tax is on its line. A second, different fingerprint stops again
rather than being absorbed by the first mapping.

**Journey I — administrator settings.** Reopened through the Configuration
menu's own action, not by URL. A readiness-irrelevant change does not
invalidate readiness; a domain change does; a no-op write does not; unrelated
domain settings survive both. The refusals are stated **precisely**: the one
that genuinely exists on this surface is the ACL, and the two read-only fields
are asserted as what they really are — `readonly` on the model, rendered
readonly or not rendered at all. `readonly=True` on an Odoo field is a UI
contract, not a server refusal, and claiming otherwise would have been a claim
this surface does not support.

**Journey J-P0 — multi-store/company.** Two companies, the same SKU on both
sides, one decision each. Each candidate set is its own company's and nothing
else; each administrator's `search`, `search_count` and direct `read` return
their own and only their own; an action aimed at the other company's job is
refused. Separately, two stores **in the same company** are shown not to share
decisions, so the isolation is proved to be store-scoping rather than a company
check doing the work.

**Journey K-P0 — failure/recovery.** The generic resolution refuses and names
the route that works; a blunt manual retry is permitted and provably cannot
loop (the same block, the same single decision row); stale, ineligible,
concurrent and competing decisions each refuse; a failed enumeration leaves the
checkpoint exactly where it was and admits no children.

## 6. §10 — the browser, responsive and accessibility campaign

### Tours

Seven tour tests over the six Batch 2 surfaces, registered in the runner's
fail-closed inventory (`REQUIRED_TOUR_TESTS`), whose guard test asserts that
inventory equals the set of test methods that actually call `start_tour` — so
adding a tour without listing it, or dropping one, fails a test rather than
silently shrinking browser coverage.

| Surface | Tour test | Database consequence verified in Python |
| --- | --- | --- |
| Canonical Store Settings | `TestUiB2SettingsTours.test_store_settings_tour_changes_a_setting_through_the_menu_route` | the setting is saved **and** the readiness marker moved |
| Product controls | `TestUiB2ProductTours.test_product_controls_tour_starts_a_real_scan` | exactly one `product_import_scan`, `manual_sync`, `queued` |
| Product controls, denied role | `…test_product_controls_are_absent_for_a_role_the_server_refuses` | no scan enqueued at all |
| Pending match decision | `…test_match_decision_tour_records_the_choice_and_resumes` | decision `confirmed`, actor recorded, choice was a real candidate, exact job re-queued |
| Match decision, denied role | `…test_match_decision_control_is_absent_for_an_operator` | decision still `pending`, job still blocked |
| Resolved binding | `…test_resolved_binding_tour_shows_a_human_made_match` | binding still points where the human said |
| Order controls | `TestUiB2SaleTours.test_order_controls_tour_starts_a_real_scan` | exactly one `order_import_scan` |
| Tax decision | `…test_tax_decision_tour_creates_the_mapping_and_resumes` | mapping carries the **importer's** fingerprint; exact job resumed; no fresh scan |

The fixtures are produced by production code: the pending decision comes from
the real importer meeting two same-SKU products and the real dispatcher routing
the failure; the tax block comes from the real `_resolve_taxes` raising its own
structured evidence.

**Selector discipline.** Every value assertion is anchored to the field that
owns it (`div[name='candidate_total']:contains('2')`), because a bare
`:contains('2')` is satisfied by any 2 on screen. Absence is asserted against
real attribute selectors, never `:contains()` inside `:not(:has())` —
`:contains()` is a hoot-dom extension and is not valid CSS.

**Keyboard.** Every actionable control is focused, proved to become
`document.activeElement`, proved to be in the tab order (`tabIndex >= 0`), and
activated by a dispatched `Enter` rather than a bare click. The focus
*indicator* is deliberately not asserted in the tours — in headless Chromium a
script-focused element never matches `:focus-visible` — and is measured instead
in the CDP campaign through `CSS.forcePseudoState`.

### Responsive, RTL, zoom, reduced motion

Six Batch 2 surfaces join the existing changed-surface campaign rather than
forming a second one: `CHANGED_SURFACES = BATCH1 + BATCH2`, and every matrix
that iterated Batch 1 now iterates both — **16 surfaces**, measured, with
`0 failed, 0 error(s) of 14 tests` in the visual/accessibility suite.

| Batch 2 surface | What it is |
| --- | --- |
| `b2-store-settings-canonical` | the canonical Store Settings form |
| `b2-store-form-controls` | the order **and** product controls, with the scheduled-position copy beside each |
| `b2-tax-decision-dialog` | the tax decision dialog, opened by pressing the control |
| `b2-product-match-decision-pending` | a pending decision with its evidence and candidates |
| `b2-product-match-decision-dialog` | the match decision dialog, opened by pressing the control |
| `b2-product-match-decision-resolved` | a resolved decision: actor, choice, resumed job state |

The **Match Decisions list** is captured and measured for responsive layout,
RTL, reduced motion and contrast, and is deliberately **not** in the two
matrices above: they measure a connector-owned surface region and its final
actionable control, and a bare Odoo list view has neither — the instrument
reports `no connector surface on screen` for it, exactly as it does for every
other list in the capture set. It is excluded because those matrices do not
apply to it, not because it failed them, and it is recorded that way rather
than quietly dropped.

Per changed surface the campaign covers:

* desktop / tablet / mobile, with the mobile row measured at **320 CSS px** —
  SC 1.4.10's reflow width;
* LTR and RTL, with an RTL row required to *show* it rendered right-to-left;
* real 200% zoom (the CSS viewport narrows **and** the type grows), and 200%
  zoom under `prefers-reduced-motion: reduce`;
* keyboard-only traversal to the final actionable control, driven by real
  `Input.dispatchKeyEvent` Tab presses;
* connector-owned clipping and horizontal overflow, per surface and for the
  page;
* measured contrast against WCAG 2.2 AA;
* live-region versus static-note semantics.

**One store, and that is measured rather than assumed.** The first version of
this seed created a *second* store so the order controls and the product
controls could be photographed separately. It broke four guided-setup captures
with `no offline path on the credential chooser`: the setup surface is opened
by action with no id and auto-selects a store only while there is exactly one,
so a second store replaced the credential step with a picker. Both control
groups live on the same form anyway, so one capture measures both — and the
regression is recorded here because a seed that quietly disturbs another
batch's evidence is exactly the kind of thing a campaign should not discover
after the fact.

**No production CSS changed.** No connector-owned visual defect was reproduced
on any new Batch 2 surface, so none was "fixed".

### Proved against their own absence, in the browser too

The server-side mutation table above proves the model's controls. These three
prove the *rendered* ones, by mutating the view and requiring the tour that
claims each to fail:

| Mutation | Caught by | Result |
| --- | --- | --- |
| B1 — the role gate removed from the decision control | `test_match_decision_control_is_absent_for_an_operator` | **CAUGHT** |
| B2 — the role gate removed from the catalog-import control | `test_product_controls_are_absent_for_a_role_the_server_refuses` | **CAUGHT** |
| B3 — `role="note"` removed from the dialog's consequence copy | `test_match_decision_tour_records_the_choice_and_resumes` | **CAUGHT** |

**3 of 3 caught, 0 missed**, and the view files are restored byte-for-byte.

## 7. Security and company boundaries

1. **UI visibility is never the control.** Every production action reasserts
   its role on the server: `_assert_product_sync_operator`,
   `_assert_match_decision_reviewer`, `_assert_tax_decision_administrator`,
   `_assert_canonical_settings_administrator`. Each is proved by a denied
   caller with zero side effects.
2. **Store/company scope is established before elevation.** The canonical
   settings seam resolves stores in the caller's ordinary environment and
   **refuses** — never filters — anything outside the caller's active
   companies; only then does it elevate, and only to ensure rows for that fixed
   set.
3. **Elevation is minimal and never used to discover targets.**
   `eligible_candidates()` elevates one exclusion query, which can only remove
   candidates.
4. **No foreign-company record, candidate, count or identity is disclosed.**
   Proved for `search`, `search_count` and direct `read`, per role.
5. **Existing constraints stay load-bearing.** Nothing was weakened to make a
   form save or a decision apply; the binding uniqueness constraints remain the
   final arbiter and the confirm path handles their `IntegrityError` as a
   sentence rather than a traceback.
6. **No protected payload, credential, token, secret or unnecessary PII**
   reaches RPC, DOM, evidence, logs or exception text. Asserted against the
   rendered decision record and against `safe_match_preview` directly.
7. **No generic context flag bypasses protected binding fields.** The decision
   route creates bindings through the importer's existing sanctioned writers
   and adds no editable binding field anywhere.
8. **The new durable model has explicit least-privilege ACLs** (read-only for
   every role) **and two company rules**, one fail-closed on the owning store
   and one on the selection relations.
9. **Stale and concurrent decisions fail closed** at both the confirm boundary
   and the consumption boundary.

## 8. Migrations

**None.** §8.2 adds a new model and new columns, which `_auto_init` creates;
there is no data to move, no existing row to reinterpret, and no behaviour that
changes for a database that already has data. No empty migration script was
created to satisfy a counter, and the genuine-upgrade runner was not weakened.

Module versions moved by coherent patch bumps: `core 19.0.1.18.0 →
19.0.1.19.0` (the tour asset) and `product 19.0.2.6.0 → 19.0.2.7.0` (the
decision model, wizard, views, ACLs and company rules).

## 9. Definitive validation

Run at `153be2baa6b77801f508680bc8da12646a10244f` with
`tools/run_connector_suite.sh` and no arguments. The runner verified the
checkout against the declared source head, verified the Odoo pin, and proved
the browser and `websocket-client` before executing anything — so no browser
test could skip its way to a green result.

| Pass | Result | Tours | Migration scripts |
| --- | --- | --- | --- |
| Fresh install + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | — |
| Warm `-u` (SAME-VERSION) + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **0, asserted** |
| Genuine migration `50b770a3` → candidate + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **2** (`19.0.1.16.0`, `19.0.1.17.0`) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2373 tests** | — | **0, asserted** |
| Genuine migration `0a15b176` → candidate + standard suite | **0 failed, 0 error(s) of 2373 tests** | 36/36 | **1** (`19.0.1.17.0`) |
| … second update (idempotency) | **0 failed, 0 error(s) of 2373 tests** | — | **0, asserted** |
| Complete non-standard tag suite | **0 failed, 0 error(s) of 59 tests** | — | — |

All three HOOT suites verified (`shopify connector dashboard`, `export diff`,
`setup wizard`). The single sanctioned skip per standard pass remains
`TestMutationRecovery.test_real_process_death_harness`, unchanged.

**Both migration passes were genuine version-to-version upgrades.** The
`50b770a3` tree installed at `core 19.0.1.15.0 / product 19.0.2.4.0 /
sale 19.0.2.4.0 / inventory 19.0.1.4.0` and the `0a15b176` tree at
`core 19.0.1.16.0 / inventory 19.0.1.5.0`; both were upgraded onto the
candidate's `core 19.0.1.19.0 / product 19.0.2.7.0 / sale 19.0.2.6.0 /
inventory 19.0.1.6.0`. Odoo runs an upgrade script only when the installed
version is strictly lower, so those are real upgrades rather than
same-version re-updates — and the runner fails a migration pass that ran no
script.

### Deltas against the Batch 2 baseline

Measured in this same environment against `b0dbba2` (2229 standard / 59
non-standard / 28 tours):

| | Baseline `b0dbba2` | Final `153be2b` | Delta |
| --- | --- | --- | --- |
| Standard suite | 2229 | **2373** | **+144** |
| Tours | 28 | **36** | **+8** |
| Non-standard suite | 59 | 59 | 0 |

### Recorded facts from `summary.json`

`connector_worktree_dirty: false`; `source_head_verified: true`;
`odoo_pin_verified: true` at `30bde9ff758834a4912c5ae55843d3a7dad849f1`;
`browser_evidence: verified`; `required_tour_tests: 36`;
`shopify_operations: none`.

Environment: Python 3.12.3, PostgreSQL 16.13, Chromium 141.0.7390.37,
`websocket-client` 1.9.0.

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

### The defect this validation found, and why it matters

The first definitive attempt, at `68410fb`, **failed its `50b770a3` migration
pass**: `test_tax_decision_tour_creates_the_mapping_and_resumes` asserted
`0 != 1` — no tax mapping existed. Fresh and warm had both been green.

The tour had reported **success**, and had run in three seconds.

Two weaknesses, and the second is why the first was invisible. The Many2one was
chosen by clicking "the first autocomplete suggestion", and
`.o-autocomplete--dropdown-menu li` resolves in document order across the whole
page — so which row is first depends on what the database happens to hold. On a
fresh database it was the tax the fixture created; on a migrated one it was
not, and the confirm was refused for an empty required field. And the tour could
not tell: its closing assertion was `.o_form_view .o_field_widget[name=
'account_tax_id']`, but a refused confirm leaves the **dialog** open and the
dialog contains an `account_tax_id` field too. The step meant to prove the
mapping exists was satisfied by the exact failure it was meant to rule out.

Corrected at `153be2b`: both decision routes type the record's name, click the
row containing that name, and assert the field holds it; both then assert **the
dialog is gone** before asserting anything about the result; the tax route's
final assertion moved to `shopify_tax_evidence_key`, a field the mapping form
has and the dialog does not; and the product route pins the exact candidate by
name rather than accepting either of the two.

Only the Python assertion after the tour caught this. That is the argument for
verifying the database consequence after every tour rather than trusting a green
marker — and it is the second time in this campaign that browser evidence failed
honest-looking, after 8 of 9 tour tests silently **skipped** on an unresolvable
Chromium while reporting `0 failed, 0 error(s)`.

## 10. Deferred, explicitly

**Deferred beyond Batch 2, per §17 and unchanged:** standalone customer import
and refresh; ambiguous-customer matching decisions; bulk `Prepare changed
products`; feature-derived scope narrowing; per-domain operating-mode
declarations; per-store/per-domain dashboard liveness; the consolidated
attention/recovery centre; Fulfillment Settings residuals; reconnect
discoverability; journey families F, G and H; governed tax remap (recorded as
P1 debt when checkpoint 2 declined to offer the unsafe version).

**Not added, by instruction:** a standalone customer import, an ambiguous
customer UI, a tax-remap state machine, webhooks, any Shopify mutation, a
second setup wizard, a second queue or dispatcher, direct UI-to-importer
execution, and generic global optimistic locking.

TD-004, TD-005 and TD-007 are retained byte-for-byte.

## 11. Gates that remain

Independent Claude review of the exact final head (the implementing session
does not review, accept, ready-mark or merge); exact-head Odoo.sh
qualification; controlled live-Shopify validation; business UAT; control-room
acceptance and merge authorization. PR #204 stays draft.

---

> **RETAINED, AND STILL ACCURATE FOR WHAT IT DESCRIBES.** Everything below this
> line is the record written at `9af8b23` for checkpoints 1, 2 and §8.1. Two of
> its statements are corrected above and are named here so no reader takes them
> from the archive by accident:
> 1. *"Nothing has been pushed … the four commits below are local only"* — true
>    at `9af8b23`, superseded by the durability ruling. The chain is pushed.
> 2. *"§8.2 … not implemented"*, and the §5c list of what is not done — all of
>    it is implemented above.
> Its checkpoint-1/2/§8.1 content, its field classification and its own
> mutation table are unchanged and remain the description of those commits.

---

# (retained) Batch 2 record as written at `9af8b23`

**`DRAFT — NOT ACCEPTED — NOT REVIEWED — NOT READY — NOT MERGED — NOT SELF-ACCEPTED`**

> **Scope of this record, and its limits.** The unified Batch 2 campaign
> specified three checkpoints plus consolidated journeys, a browser campaign
> and one definitive validation. This record covers what is **implemented and
> focus-validated locally**: checkpoint 1 (canonical Store Settings),
> checkpoint 2 (order controls and the tax decision route), and **§8.1 of
> checkpoint 3** (the product enumeration producer).
>
> **NOT implemented, and not claimed:** §8.2 durable product/variant match
> decisions; §9 consolidated vertical journeys; §10 the consolidated
> browser/accessibility campaign; §15.2 the definitive seven-pass validation
> at a final head. Nothing has been pushed. The branch `fable/wave-5-completion`
> remains at `b0dbba2a` and PR #204 remains draft, unreviewed and unmerged.
>
> Per §5 and §15.2 the additive chain is not pushable until the consolidated
> validation is green, so the four commits below are **local only**.

## 1. Heads

- Starting head (identity-gate verified): `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e`
- Local additive chain (unpushed):
  - `9a70682` checkpoint 1 — canonical Store Settings
  - `f5f3668` checkpoint 1 — the four guards the new surface had to answer to
  - `39e5113` checkpoint 2 — order controls and tax decisions
  - `2c5d190` checkpoint 3 §8.1 — product enumeration producer
- Base: `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, confirmed ancestor)
- Odoo pin: `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run
- History: **additive only** — no amend, rebase, squash, reset or force-push

### Identity gate

All ten items passed before any edit. Repository `AdamsOdoo/Adams`; PR #204
open, draft, unmerged, **zero reviews**; head branch `fable/wave-5-completion`;
PR head, remote branch head and local HEAD all exactly the required starting
head; base unchanged and an ancestor; clean worktree; `tools/odoo-pin.txt`
carrying the required pin; no later unreviewed commit.

One item needed care rather than acceptance at face value. `git merge-base
--is-ancestor` initially reported the base was **not** an ancestor. That was
the clone, not the branch: the working copy was shallow at 50 commits, so the
base commit was simply absent from the object store. After `git fetch
--deepen=200` the ancestry resolves. A shallow clone answering an ancestry
question with silence that reads as "no" is worth recording, because the
honest-looking action there is to stop on a false negative.

## 2. What checkpoint 1 closes

The first of the three §2 defects: **the promised per-store settings surface
did not exist**, and important core, product-import, sale and inventory
settings were not merchant-reachable after onboarding.

`Shopify Connector → Configuration → Store Settings` is that surface. It is
not a second setup wizard — it collects no consent, runs no readiness check,
drives no lifecycle transition and creates no store — and it does not compete
with the two dedicated surfaces that already own their own subjects.

The sharpest single instance: **`order_scheduled_sync_enabled` had no
production writer anywhere in the repository.** The cron
(`_cron_enqueue_order_scans`) and the enqueue producer (`_enqueue_order_scan`)
both already existed and both already selected on that field. The only thing
missing was a control a merchant could reach. That is now on the canonical
form, writing through the ordinary model path.

§7's order controls and tax decision route are §5 below; §8.1's product scan
producer is §5b. §8.2's durable match decisions are **not implemented**.

## 3. Field ownership and classification

Every module contributing a field to `shopify.connector.store.settings`
classifies **all** of them, as §6.6 requires, into exactly one of: canonical
editable, canonical read-only, owned by a named existing dedicated surface, or
internal/protected with a named justification.

**There is no expected field count anywhere in the tests.** A count is
satisfied by any set of the right size — it passes when one field is added and
another removed, and says nothing about the field that was added. The
assertion is set equality against the live registry (`Field._modules`), so
adding a field to the model in any module fails that module's test until it is
classified by name.

### Core (`shopify_connector_core`)

| Field | Classification |
| --- | --- |
| `product_domain_enabled` | canonical editable |
| `sale_domain_enabled` | canonical editable |
| `inventory_domain_enabled` | canonical editable |
| `fulfillment_domain_enabled` | canonical editable |
| `log_redaction_retention_days` | canonical editable |
| `store_id` | canonical read-only |
| `company_id` | canonical read-only |
| `product_first_sync_source` | canonical read-only |
| `notification_default_enabled` | canonical read-only |
| `price_source_of_truth` | owned by **Export Settings** |
| `setup_wizard_step_key`, `setup_wizard_step`, `setup_readiness_stale_since`, `setup_completed_at`, `setup_completed_uid`, `setup_last_rerun_at`, `setup_last_rerun_uid` | internal/protected — setup progress and the readiness marker, written only by the setup service |

`notification_default_enabled` is read-only and says on screen why: opting in
means Shopify emails customers on fulfilment, and that consent stays on the
guided Setup Wizard's notification step, which refuses to enable without an
explicit confirmation (`save_notification`). No second consent path was added.

`product_first_sync_source` is read-only; a post-onboarding direction switch
was not authorized here.

### Product (`shopify_connector_product`)

`product_import_media_enabled`, `product_import_refresh_mode`,
`product_import_attribute_conflict_mode` — all canonical editable.

Plus, **added by checkpoint 3 together with the producer that makes them
real**: `product_scheduled_sync_enabled` (canonical editable),
`product_last_import_checkpoint_at` and `product_last_import_success_at`
(canonical read-only).

**The ordering was deliberate.** Checkpoint 1 declined to render the schedule
switch while nothing in production enumerated a catalog — a control whose
producer does not exist is a control that silently does nothing, the same
false-capability failure §6.4 forbids. Its test asserted the field's absence.
Checkpoint 3 built the producer, so that test is now inverted: the schedule
must be the field the cron actually selects on.

### Sale (`shopify_connector_sale`)

Canonical editable: `order_scheduled_sync_enabled`, `order_confirmation_policy`,
`manual_gateway_policy`, `approved_manual_gateways`, `order_import_window`,
`pending_wait_expiry`, `order_import_include_test`,
`customer_fallback_partner_id`, `order_pricelist_id`, `order_sales_team_id`,
`order_payment_term_id`.
Canonical read-only: `order_company_id`, `sale_order_last_import_checkpoint_at`.

**`customer_fallback_partner_id` — the §6.4 proof.** §6.4 requires the fallback
setting to be proved consumed or else rendered unavailable. It **is** consumed:
`ShopifyConnectorOrderImporter._resolve_customer`
(`shopify_connector_order_importer.py:1164-1165`) returns it with resolution
`fallback` for an order carrying no usable customer email, and raises
`odoo_validation_configuration` when it is unset. It is therefore rendered as
the real setting it is.

The field's own docstring still described it as inert substrate — "zero
order-resolution behaviour", never read. That was true when Task 011
introduced it and stopped being true when Task 012 landed order import. The
docstring is corrected rather than trusted, because the canonical form decides
whether to present a field as supported on exactly that question, and a stale
comment is how it would have been presented wrongly. **This is the one Batch 1
file changed beyond the checkpoint's own additions, and it is named here so the
control room can reverse the reading.** A test asserts the production call site
exists, so the day it is removed the form stops claiming the capability.

### Inventory (`shopify_connector_inventory`)

`inventory_scheduled_sync_enabled` — canonical editable (the inventory
service's `run_inventory_push_scan` selects on it, so it genuinely starts and
stops scheduled scanning). `inventory_last_push_scan_at` — canonical
read-only; the service writes it, so typing into it would only make the report
wrong.

### Not duplicated

Export Settings keeps `price_source_of_truth`, `media_source_of_truth` and
`product_export_domain_enabled`. Fulfillment Settings keeps the operating mode,
`fulfillment_mode_switch_nonce`, the switching state and the notification
confirmation. Setup progress, completion/rerun stamps and
`setup_readiness_stale_since` are rendered nowhere.

## 4. Action, menu and the row-ensure seam

- Canonical list and form on `shopify.connector.store.settings`, both
  `create="false" delete="false"`, list not inline-editable.
- One `ir.actions.act_window` binding both views through `view_ids`. This is
  load-bearing rather than tidy: four surfaces now share this model, and an
  action with no view reference falls back to `default_view()`, which orders by
  `priority,name,id`. Every view sits at the default priority, so the tie
  breaks on **name** — precisely the accident that made "Export Settings"
  render the fulfillment list until it was corrected.
- `group_ids` is the Odoo 19 field on `ir.actions.act_window`, verified at the
  pinned commit (`odoo/addons/base/models/ir_actions.py:329`), not assumed.
- The Administrator-gated **Configuration** menu already existed
  (`menu_shopify_connector_configuration`); Store Settings hangs off it rather
  than creating a second branch.

### The seam, and why the order is the argument

`action_open_canonical_store_settings`:

1. reasserts the Connector Administrator role **on the server** — the menu gate
   and `group_ids` are chrome, and a direct RPC reaches the method regardless;
2. resolves stores in the **caller's ordinary environment**, where the
   fail-closed SEC-3 company rule (`[('company_id', 'in', company_ids)]`) is
   live;
3. re-checks `check_access('read')` and **refuses** if anything outside the
   caller's active companies got through;
4. only then elevates, and only to ensure rows for that fixed set.

`sudo()` does **not** keep record rules running — Odoo bypasses them under
elevation. So the property defended is not "the rules still apply"; it is that
the authorized set is fixed **before** elevation and can only shrink after.
`_ensure_canonical_settings_rows` takes a recordset and never searches for a
store, so discovery cannot happen under elevation by construction.

**A refusal, not a filter.** Step 3 raises rather than quietly dropping
records. The company rule already excluded them, so a silent `filtered()`
would be a no-op that passes every test while absorbing a widened resolution
without a sound. This was found by mutation, not by inspection: with a filter,
replacing the ordinary-environment search with a `sudo()` one broke **nothing**
— the isolation test passed either way, so it was not evidence. With the
refusal, the same mutation breaks four tests.

Row ensure is idempotent, and a concurrent opener is contained: `UNIQUE(store_id)`
is the arbiter, each create sits in its own savepoint, and losing the race is a
no-op because the winner's row is exactly the row the call wanted to exist.

## 5. Write and readiness behaviour

All saves go through the ordinary model write path, so every existing
constraint stays load-bearing — store/company agreement, order-company
agreement, import window and scope, pending expiry, pricelist/team/payment-term
company, fallback-customer company, and the unique-row guard. None was weakened
to make the form save.

The readiness-relevant-field hook is derived from
`shopify.connector.readiness.check._accepted_domain_flags()` — the same
registry the readiness checks are computed over — rather than a second tuple
beside it. The two would drift: Product Export **already** extends that
registry with `product_export_domain_enabled`, so a copied tuple would have
gone on reporting a store as freshly-checked after a merchant enabled catalog
export. It remains overridable, so a domain extends it for fields its own
checks consume.

- A meaningful change marks readiness stale through the existing
  `_mark_setup_readiness_stale()` service.
- A no-op write does not — the comparison is against the stored value, not the
  presence of a key in `vals`.
- An unrelated canonical-editable setting (`log_redaction_retention_days`) does
  not.
- The nested marker write terminates because `setup_readiness_stale_since` is
  not readiness-relevant. That is a property of the **field partition**, not a
  re-entrancy flag somebody has to keep correct — and breaking the partition
  breaks the test that claims it.

## 6. Security and company invariants (checkpoint 1 scope)

1. UI visibility is not authorization — the server role assertion is the control.
2. Store/company scope is established as the original caller, before elevation.
3. Elevation is minimal, record-scoped, and never used for target discovery.
4. No existing settings ACL or company rule was widened. Settings access is
   unchanged: Auditor/Operator/Reviewer read; Administrator read+write, no
   create, no unlink.
5. A company-less historic store — invisible under the fail-closed rule — is
   never adopted.
6. No new durable model, so no new ACL or company rule was required.
7. Zero Shopify contact and zero Shopify mutation: this checkpoint adds no
   transport code path at all.

## 7. Migrations

None. Checkpoint 1 is views, one server seam, and a `write()` override — no
schema change, so no migration script. No empty script was created to satisfy
a counter, and the genuine-upgrade runner was not weakened.

Module versions moved by coherent patch bumps for the four touched modules:
`core 19.0.1.17.0 → 19.0.1.18.0`, `product 19.0.2.4.0 → 19.0.2.5.0`,
`sale 19.0.2.4.0 → 19.0.2.5.0`, `inventory 19.0.1.5.0 → 19.0.1.6.0`.

## 8. Tests, and their load-bearing proof

31 new test methods: **20 core, 3 product, 4 sale, 4 inventory** — counted
from the test files themselves, not from `odoo.tests.stats`, whose per-module
figures include fixtures and do not sum to the selected total.

Each central claim was proved **against its own absence** by mutating the
production code and confirming the specific test that claims it fails:

| Mutation | Result |
| --- | --- |
| Server-side role assertion removed from the seam | `test_non_administrator_direct_call_is_refused` fails (1) |
| Readiness staleness call removed from `write()` | `test_a_meaningful_change_marks_readiness_stale` fails (1) |
| Every written field treated as readiness-relevant | no-op guard, unrelated-setting and **non-recursion** tests fail (3) |
| `readonly="1"` removed from a canonical read-only field | classification test fails (1) |
| `except IntegrityError` no longer catches the unique violation | concurrent-winner test errors (1) |
| Ordinary-environment store search replaced with `sudo()` | 4 tests error — **and 0 before the refusal replaced the filter** |

The last row is the one worth reading twice: it is the case where the first
version of the test proved nothing, and mutation is what said so.

## 9. Definitive validation

Recorded in `docs/05-qa/evidence/batch-2-p0-merchant-reachability-2026-07-30/`.

**Evidence class: local supporting evidence — NOT Odoo.sh exact-SHA acceptance
(DEC-041 D8), NOT live-Shopify validation, NOT UAT, NOT independent review.**

## 10. Deferred, explicitly

**Not started in this session:** checkpoint 2 in full (order manual/scheduled
controls, the tax blocked-work decision route and workspace, their tests) and
checkpoint 3 in full (product scan producer, cron, checkpointing, durable
product/variant match decisions, their tests). Also not started: the
consolidated vertical journeys (C, D-P0, I, J-P0, K-P0), the consolidated
browser/accessibility campaign, and their runner-inventory registration.

**Deferred beyond Batch 2, per §17:** standalone customer import/refresh;
ambiguous customer matching decisions; bulk `Prepare changed products`;
feature-derived scope narrowing; per-domain operating-mode declarations;
per-store/per-domain dashboard liveness; consolidated attention/recovery;
Fulfillment Settings residuals; reconnect discoverability; journey families F,
G and H; governed tax remap. TD-004, TD-005 and TD-007 are retained unchanged.

## 11. Gates that remain

Independent Claude review of this exact head (the implementing session does not
review, accept, ready-mark or merge); checkpoints 2 and 3; the consolidated
journeys and browser campaign; exact-head Odoo.sh qualification; controlled
live-Shopify validation; business UAT; control-room acceptance and merge
authorization. PR #204 stays draft.


## 5. Checkpoint 2 — order controls and tax decisions

**The controls.** `Import orders now` binds `action_sync_orders_now` on the
store form; `Refresh this order` binds `action_sync_selected` on the order
binding. Both methods pre-existed with their own server guards and neither had
a caller in any view. `groups="operator"` matches `_assert_order_sync_operator`
exactly — Administrator and User both imply Operator — and the server refuses a
denied caller regardless. The store form now states the scheduled position, the
discovery watermark and any scan in flight, so a manual button never stands
beside a silent screen that reads as "this is handled".

**The tax route.** The importer already canonicalised a Shopify `TaxLine` into
a version-stamped fingerprint, refused to guess, and raised structured evidence
with bounded candidates explicitly marked
`rate_and_inclusion_only_non_binding`. None of it was reachable: the evidence
sat in a job-log row and the only control was a generic retry that re-ran the
identical import and failed identically.

**The state is `failed_retryable`, not `blocked_manual_review`.**
`odoo_validation_configuration` is a `MANUAL_FIX_THEN_RETRY` class, so a guard
written against the phrase "blocked work" would never match what the dispatcher
produces. It also means the generic `action_resolve_manual_review` already
refuses these jobs (§7.2.13) — asserted rather than rebuilt.

Identity comes from the structured payload after exact-key schema validation,
never from the human sentence; a test rewords the message and asserts nothing
changes. The fingerprint is displayed, never typed. Candidates are recomputed
against the live database at open and again at confirm. Confirmation creates
the mapping with `UNIQUE(store_id, evidence_key)` as arbiter and resumes the
exact job via `action_manual_retry` — never a fresh scan.

**Tax Mapping workspace**: list/form/search, `create="false" delete="false"`,
and `account_tax_id` rendered **read-only** although the model permits writing
it. Changing what a Shopify tax means after it has priced imported orders needs
a preview and an audit; declining to offer the unsafe version is the honest
move. **Governed remap is recorded as P1 debt.**

**A defence that was not being tested.** Removing the candidate query's
`company_id` filter broke nothing — Odoo's own multi-company rule on
`account.tax` already hid the foreign tax from a single-company administrator.
The new test runs the query as an administrator with *both* companies active,
so the record rule lets the tax through and the filter is the only thing left.
That mutation now fails exactly one test.

21 tests. Whole sale module green at **251**.

## 5b. Checkpoint 3 §8.1 — the product enumeration producer

`product_import_sync` was registered, handled and replay-classified, and
nothing in production ever created one. Now: a registered `product_import_scan`
job type, `Import products now`, a module-owned hourly cron, per-store
checkpoint and success stamps, and children admitted through the existing
enqueue service. No second queue, dispatcher or transport.

**Verified against the configured version `2026-07`, not `latest`.**
`ProductSortKeys` carries `UPDATED_AT`; `ProductStatus` carries a fourth value,
`UNLISTED`, which the schema notes is "only visible from 2025-10 and up". A
scan written against the familiar three-value enum would meet it on this
version, so status is carried as an opaque string and a test enumerates all
four. Verification used schema introspection and official documentation only —
**zero Admin API contact, zero credential**.

- First run carries **no time lower bound** and no status clause: a
  recent-changes default silently omits every product nobody edited lately.
- Incremental runs reach one minute **behind** the checkpoint, because
  `updated_at` has second resolution and a same-second write would fall in the
  gap. Re-seeing products is free; the children collide on their idempotency
  key.
- The checkpoint advances once, after every page and child, inside the
  handler's savepoint. A scan failing on page two discards page one's children
  and leaves the checkpoint where it was.
- Child `payload_hash` is the **verbatim** remote `updatedAt`.
- Repeated cursors, non-progressing cursors, duplicate identities, malformed
  shapes and the page ceiling all fail closed and visibly.

25 tests. Whole product module green at **217**.

## 5c. What is NOT done

- **§8.2 durable product/variant match decisions** — not implemented. Ambiguous
  matching still routes to the importer's existing `blocked_manual_review`
  behaviour with no durable decision record, so generic requeue still repeats
  the same failure. This is the one §2 defect left open.
- **§9 consolidated vertical journeys** (C, D-P0, I, J-P0, K-P0) — not written.
- **§10 consolidated browser/accessibility campaign** — not run. No new tour is
  registered, so the runner's fail-closed tour inventory is unchanged.
- **§15.2 definitive seven-pass validation** — not run at a final head.
- **Nothing pushed.** Per §5/§15.2 the chain is not pushable until the
  consolidated validation is green.

An earlier seven-pass run was started after checkpoint 1 and terminated as
premature under §15.1 per the control-room ruling. Its passes 1 and 2 (fresh
and warm, 0 failed of 2260 tests, 28/28 tours) are **intermediate diagnostic
evidence only** and describe `f5f3668`, not any later head.
