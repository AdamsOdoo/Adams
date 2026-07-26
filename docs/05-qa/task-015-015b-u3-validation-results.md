# Task 015 / 015B / U3 — validation results (Wave 5 completion continuation)

> **Status: local validation evidence. NOT an acceptance, NOT Odoo.sh runtime,
> NOT independent review, NOT UAT, and NOT a release-readiness claim.**
> Produced 2026-07-26 under the consolidated Wave 5 completion continuation
> ruling of the same date.
>
> **No Shopify store, credential, request, mutation or webhook exists anywhere
> in this batch.** Every test replaces the transport at the `_send` seam, so the
> real admission gate, the real Layer 2 attempt machinery and the real response
> taxonomy all execute — only the socket is absent. No latency, no response and
> no store behaviour is measured or fabricated.

## 1. What was delivered

| # | Item | State |
| --- | --- | --- |
| 1 | **API-version enforcement** (ruling §3) | **DELIVERED** |
| 2 | **Task 015 — controlled product export, split mutations** (ruling §4) | **DELIVERED** |
| 3 | **Task 015B — append-only media export** (ruling §5) | **DELIVERED** |
| 4 | **U3 — export and non-export operator surfaces** (ruling §6) | **PARTIAL** — see §6 |
| 5 | **SEC-3 extension over every new model/field/relation/action/ACL/rule** | **DELIVERED** |
| 6 | **X-EXPORT-0 record correction** (ruling §7) | **DELIVERED** |

## 2. API-version enforcement — the exact mechanism

`[Fact]` `addons/shopify_connector_core/tools/api_version.py` is the single
place the version is stated: `SHOPIFY_API_VERSION = '2026-07'`,
`API_VERSION_RESPONSE_HEADER`, and `admin_graphql_endpoint(shop_domain)` which
constructs `https://<domain>/admin/api/2026-07/graphql.json`. HTTPS and the
version are structural in that function, so no call site can address another
scheme or another version.

`[Fact]` Four enforcement points, each with a test:

| Point | Behaviour | Test |
| --- | --- | --- |
| Endpoint construction | Built from the constant; the store's recorded `api_version` is **never** used to build it | `test_endpoint_uses_the_centralized_constant` |
| Pre-send | A store whose recorded version differs raises **before** any request; nothing is sent | `test_store_version_disagreement_refuses_before_send` |
| Response mismatch | `X-Shopify-API-Version != 2026-07` → **fails closed** | `test_version_mismatch_fails_closed` |
| Missing header | No version header → **fails closed** (same uncertainty, no evidence) | `test_missing_version_header_fails_closed` |

`[Fact]` Classification is `odoo_validation_configuration` — the existing
DEC-009 "manual fix then retry" class. **No 17th error class is introduced.**
The operator-facing reason names no header, no domain and no token; the
technical detail carries only the two version strings and is passed through
`redact()`. Both are asserted:
`assertNotIn(DUMMY_TOKEN, exc.technical_detail)` and
`assertNotIn(DUMMY_TOKEN, str(exc))`.

### 2.1 A superseded behaviour, named rather than left in a diff

`[Fact]` The merged code recorded a served-version mismatch as
`version_fallforward` + `api_health_state='degraded'` **and returned the
response as a success**. Four accepted assertions encoded that:

| Accepted test | Disposition |
| --- | --- |
| `test_api_client.test_version_fallforward_no_exception` | **replaced** by `test_version_mismatch_fails_closed` |
| `test_test_connection.test_version_fallforward_warns_but_still_passes` | **replaced** by `test_version_fallforward_fails_the_probe` |
| `test_readiness_slot_closure.test_fallforward_success_still_sets_api_health_degraded` | **replaced** by `test_fallforward_now_fails_the_probe_instead_of_degrading` |
| `test_readiness_slot_closure.test_source_level_..._sudo_inventory`'s `assertIn("'api_health_state': 'degraded'")` | **inverted** to `assertNotIn`, because the fall-forward branch that wrote it is gone |

`[Inference]` Inverting an accepted assertion is a behaviour change a reviewer
must see named. The old disposition was defensible for a read-only connector
and is not defensible for a mutation domain: a `productUpdate` built against
2026-07 semantics, executed against another version's semantics and reported as
applied is precisely the failure class this wave exists to prevent.

`[Fact]` Six existing fake-transport fixtures across four modules now declare
the version header they are pretending to have been served with, because the
missing-header case is a real fail-closed path. Each keeps an explicit
`headers=` override so the version tests can still pass `{}`.

## 3. Task 015 — the mutation split, and what it structurally cannot do

`[Fact]` New module `addons/shopify_connector_product_export`, depending only on
`shopify_connector_core` and `shopify_connector_product`. Uninstalling it
removes the entire catalog-write surface (ARCH PD-1).

| Path | Mutation | Guard |
| --- | --- | --- |
| create (unbound only) | `productSet(synchronous: true, identifier: {customId})` | `_assert_no_product_set_on_existing` refuses the operation **string** whenever a binding or remote GID exists |
| scalar update | `productUpdate(product:, identifier: {id})` | only the fields the operator confirmed; `assert_no_forbidden_keys` over the whole variable tree |
| mapped variants | `productVariantsBulkUpdate(allowPartialUpdates: false)` | every variant identified by its **bound GID**; never by SKU or option values |
| new variants | `productVariantsBulkCreate(strategy: PRESERVE_STANDALONE_VARIANT)` | `DEFAULT` deletes the standalone variant, so it is unavailable |
| binding namespace | `metafieldDefinitionCreate(capabilities.uniqueValues)` | its own mutation domain, gated on a settings marker |

`[Fact]` Seven mutation domains are registered on the DEC-031 Layer 2
protocol (five product, three media — `product_export_create` counts once),
each with all seven strategy hooks, each owning at most one attempt for its
lifetime, and all sharing one read-only reconciliation job type.

### 3.1 Everything that fails closed instead of deleting

`[Fact]` Each row is a test:

| Difference | Disposition |
| --- | --- |
| A remote variant no binding names | Disclosed as `unowned_remote_variant`; **left in place**; absent from every executable list |
| A bound variant absent remotely | `bound_variant_missing_remotely` → manual review; no replacement created |
| Remote option structure differs | `remote_option_divergence` → refused; **no variant write is even planned**, because `optionValues` are positional against the remote option set |
| >3 options or >100 variants | Blocking hold; **every** executable step is removed, so the "safe half" cannot be confirmed |
| A binding appeared after the preview | `duplicate_risk` pre-C2, before any create |
| A SKU already on Shopify | `duplicate_risk`; never a blind create |
| Remote `updatedAt` changed since preview | Apply refuses; preview expires; nothing written |
| Preview older than 24h, or Odoo template/variant edited since | Expired; confirmation refused |
| Store reconnected | Every open preview expired |

`[Fact]` `collections`, `collectionsToJoin`, `collectionsToLeave`,
`metafields`, `files`, `media`, `variants`, `productOptions`,
`inventoryQuantities`, `quantityAdjustments`, `mediaId` and `mediaSrc` are in
`FORBIDDEN_UPDATE_KEYS`, checked **recursively** so
`variants[0].metafields` cannot slip through a nested edit.

`[Fact]` The complete-list workaround is refused by design and stated in the
module docstring: echoing a full remote list into a declarative input would
make the connector the author of state it cannot see.

## 4. Task 015B — append-only

`[Fact]` Pipeline: `stagedUploadsCreate` → plain HTTPS upload to the staged
target → `fileCreate` → poll `fileStatus` until `READY` →
`fileUpdate(referencesToAdd: [productId])`. Five job types, three of them
Layer 2 mutation domains.

`[Fact]` The READY gate is enforced in `prepare_preconditions`, immediately
before the request is built: a row that is not `ready`, or whose
`shopify_gid` is still the deterministic placeholder, fails closed. Tested for
`staged`, `uploaded` and `processing`.

`[Fact]` Append-only is mechanical, not a convention:
`referencesToRemove` is never sent; `fileDelete`, `productCreateMedia`,
`productDeleteMedia`, `productUpdateMedia`, `productVariantDetachMedia` and
`productReorderMedia` appear in **no GraphQL document** in the module — asserted
by an AST scan that inspects string literals matching an actual operation
signature, so the guard cannot be satisfied or defeated by prose.

`[Fact]` A superseded image's File **and its association** are retained; the
old row is flagged `orphan_cleanup_candidate`. A `FAILED` `fileStatus` routes to
manual review with nothing associated. An unchanged image is a no-op by
checksum. Media export runs only under an explicit `media_source_of_truth =
odoo`; unset **blocks** it rather than choosing.

`[Fact — scope correction]` Least privilege is **`write_files` +
`write_products`**, not `write_images` + `write_products`. `fileUpdate` — the
only 2026-07 mutation that associates an existing File with a product, and
therefore the only READY-gated path — does not accept `write_images`.
`write_themes` is never requested and its presence is a readiness **failure**.
Reasoning and sources:
[`task-015-export-source-verification-2026-07-26-addendum.md`](task-015-export-source-verification-2026-07-26-addendum.md)
§4.1.

## 5. SEC-3 and the permission boundary

`[Fact]` Both new models inherit `shopify.connector.scope.mixin`, carry a stored
related `company_id`, declare their connector-parent relations, and are swept by
`_sec3_quarantine_scope_mismatches()` on install and every update. Four global
record rules (store-company + business-record, per model) are loaded after the
ACLs. Twelve ACL rows cover the two models and the two wizards across the four
capability groups; **no row grants `unlink`** on either durable model, and both
`unlink()` methods raise.

`[Fact]` Both models are registered in core's authoritative `SEC3_MODELS`
inventory with real row builders, and their three connector relations in
`SEC3_STORE_RELATIONS` — so the whole generated SEC-3 matrix (read shapes, write
shapes, three roles, the company switcher axis, the store-vs-company axis, the
historic-quarantine axis) now covers them. Leaving them out would have been
caught by `test_no_durable_store_scoped_model_escapes_this_matrix`, and was.

`[Fact]` Every one of the 13 new job types maps to
`product_export_domain_enabled`, tested per type; a job cannot reach `running`
while the flag is off.

## 6. U3 — delivered, and the residue

`[Fact — delivered]` Export preview list/form/search with the diff, the refused
differences and the left-untouched sections as first-class parts of the record;
the review-and-confirm wizard, which requires an explicit acknowledgement and
delegates to `action_confirm_export_preview`; the preview-request wizard bound
to the product form; the exported-media registry surface including the
retained-orphan disclosure; the per-store export settings, ownership-direction
and retention surface; the reconnect export block on the store form; the
product-form opt-in with its allowlist disclosure; the Export menu branch under
the one existing U0 root.

`[Fact — NOT delivered and NOT claimed]`

- **No Owl component.** S7 is Odoo-native, not the Owl diff surface the master
  specification assigns to U3.
- **No `web_tour` tours and no HOOT tests.** The packet makes both an
  acceptance criterion for a UI phase.
- **No screenshot set, no §13 accessibility checklist, no `ui-u3-copy-deck.md`.**
- **No reconnect/backfill banner or watermark progress (S25/S26), no
  diagnostics screen (S31), no motion/keyboard/contrast polish pass.**

**U3 is therefore not complete.** The reason is capacity, not a dependency.

`[Fact]` What the UI layer cannot do is asserted structurally: an AST guard
fails if any wizard calls `create`, `write`, `unlink`, `sudo`, `commit` or
`enqueue`, and a scan fails if any view file mentions a mutation name. There is
no apply-without-preview affordance, no auto-apply toggle and no bulk-confirm
control anywhere in the view layer, because no such server path exists.

## 7. Standing guards this batch had to satisfy, and what they caught

`[Fact]` The repo's own guards rejected the first version of this work five
times, and each rejection was correct:

| Guard | What it caught | Resolution |
| --- | --- | --- |
| `test_mutation_literals_require_guarded_transport_or_selftest` | Eight mutation literals in `prepare_preconditions` methods with no allowlisted transport pair | Ten pairs registered explicitly; the shared guarded helper is **named** and separately asserted to hold `execute_business(mutation_context=...)` and no forbidden route |
| `test_accepted_split_allowlist_is_exactly_the_two_inventory_pairs` | The allowlist was frozen at two entries | Renamed to `..._is_exactly_the_declared_pairs`, all ten named; the freeze is preserved, not removed |
| `test_repo_wide_raw_transport_guard` | The staged-upload `requests.post` | Allowlisted to one file, one verb and one method, with the reason recorded: it is an object-store upload, not a Shopify GraphQL call, so there is no operation to admit |
| `test_no_attempt_direct_write_call_outside_closed_surface` | The preview model copied the `_surface(` idiom, which the guard uses as its heuristic for mutation-attempt writes | The preview accessor is renamed `_preview_surface`; **the core guard is untouched** |
| `test_no_durable_store_scoped_model_escapes_this_matrix` | Both new models missing from `SEC3_MODELS` | Registered with real row builders |

`[Inference]` Two of these are worth naming as findings rather than chores. The
mutation-literal guard is the reason this module cannot reach the network except
through `execute_business` with a Layer 2 attempt context — it refused a
plausible-looking eight-way delegation until the shared helper was named and
checked. And the SEC-3 completeness guard is the reason a new durable model
cannot be silently outside the isolation matrix; the matrix's own docstring
predicted exactly this failure mode and it fired on the first run.

## 8. Local suite results

`[Fact — EXECUTED. Environment recorded in full so the run is reproducible and
cannot be confused with Odoo.sh evidence.]`

| Item | Value |
| --- | --- |
| Odoo | `odoo/odoo@19.0` `30bde9ff758834a4912c5ae55843d3a7dad849f1` (pin verified on every run) |
| PostgreSQL | 16.13 (local disposable cluster) |
| Python | 3.12.3 |
| Installed | `shopify_connector_{core,product,sale,inventory,fulfillment,product_export}` + `account`, `stock` and closures |
| Runner | `tools/run_connector_suite.sh` (three passes, unchanged except for adding the new module to `MODULES` and `STANDARD_TAGS`) |
| Tested SHA | **recorded in §8.1 below, against the frozen head** |

**Baseline at the starting head `60a80eff` (before this batch), same
environment:** fresh install `0 failed, 0 error(s) of 1616 tests`. This
reproduces the number the PR body records for that SHA, which is what
establishes that the environment is faithful rather than merely green.

### 8.1 Results at the frozen head

*Filled in from `ci-artifacts/summary.json` at the final commit — see the PR
push record for the exact SHA and the verbatim result lines.*

| Pass | Result |
| --- | --- |
| Fresh install + standard | see summary |
| Warm `-u` update + standard | see summary |
| Non-standard tag suite | see summary |

**Evidence class: DEC-041 D8 supporting evidence, NOT Odoo.sh acceptance.**
Until equivalence is separately proven, the exact-SHA Odoo.sh run remains the
Tier-1 authority.

## 9. Not done and not claimed

- **No Odoo.sh runtime of any kind.** One exact-head Odoo.sh campaign remains
  mandatory and is the next gate.
- **No independent review.** This record is written by the implementing session
  and accepts nothing.
- **No Shopify credential, request, mutation or webhook. No store contacted.**
  No latency, no throughput and no response is measured or fabricated.
- **No behavioural verification of any export mutation.** Every one is
  source-verified against the 2026-07 reference and exercised against a
  substituted transport. Whether Shopify behaves as documented is a
  live-validation question (`M-EXP-1..20`).
- **No `X-EXPORT-0` result.** The omitted-list boundary is unresolved by
  documentation and unresolved empirically; the design no longer depends on it.
- **No browser, tour, HOOT or screenshot evidence for any U3 surface.**
- **No UAT, no release-readiness claim, no PB/PERF threshold claim.**
- **"Delivered" for U3 is explicitly qualified as partial** in §6 and in
  `wave-5-completion-gate-state.md` §5e.
