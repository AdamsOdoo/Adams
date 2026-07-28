# Shopify Live-Validation Package (executable)

> **Status: Executable campaign package. Docs-only — NOT an acceptance, and
> NOT authorisation to begin.** Produced 2026-07-25 on
> `fable/wave-5-completion`. Execution is gated on a provisioned disposable
> development store ([#200](https://github.com/AdamsOdoo/Adams/issues/200)) and
> an explicit control-room instruction. **No step here has been executed, and
> no result in it is claimed.**
>
> This package exists so that, the moment a store is provisioned, the campaign
> can be run by someone who was not part of building the connector, in order,
> without re-deriving anything.
>
> Residual alignment (issues are **not** modified by this package):
> Gate D / CV-013 → [#185](https://github.com/AdamsOdoo/Adams/issues/185) ·
> provisioning → [#200](https://github.com/AdamsOdoo/Adams/issues/200) ·
> external multi-user confirmation → [#197](https://github.com/AdamsOdoo/Adams/issues/197) ·
> Shopify-read performance and release thresholds → [#199](https://github.com/AdamsOdoo/Adams/issues/199).

## 1. Entry criteria — all must hold before case 1

| # | Criterion | Verified by |
| --- | --- | --- |
| E1 | A **disposable** Shopify development store exists, used by no other workload | Provisioner, recorded on #200 |
| E2 | The exact connector SHA under test is frozen and recorded | `git rev-parse HEAD` in the run record |
| E3 | Exact-SHA Odoo.sh runtime for that SHA is green | Odoo.sh build id |
| E4 | Credentials are least-privilege per §2 and are **not** production credentials | Scope dump in §2.3 |
| E5 | A named human owner is on point for the run and for revocation | Run record |
| E6 | Rollback (§8) has been read and the store's pre-run state is captured (§3.3) | Baseline snapshot file |

**If any entry criterion fails, STOP.** Do not partially run the campaign.

## 2. Provisioning and least-privilege scopes

### 2.1 Store

A Shopify **development store** (never a live merchant store), created solely
for this campaign, with no real customer data and no real payment method.

### 2.2 App / credential

A custom app on that store with an Admin API access token. The token is stored
through the connector's own credential path — never pasted into a file, a
document, a test fixture, a log, or a GitHub comment.

### 2.3 Required scopes — request exactly these, and record the granted set

**`[Corrected 2026-07-28]`** The prior version of this table was internally
contradictory: it required execution of the M-EXP-* cases (§4.0a), which
include product mutation and media upload/association, while its own scope
list omitted `write_products` and `write_files` and stated they were
forbidden. Both tiers below are re-derived directly from the frozen source at
this head, not carried over from an earlier draft.

**Core connection-readiness baseline** — the exact `REQUIRED_MVP_SCOPES`
tuple, required for every store regardless of which domain this campaign
exercises (`addons/shopify_connector_core/models/shopify_connector_readiness_check.py:53-65`):

| Scope | Why it is needed |
| --- | --- |
| `read_products` | Product/variant read |
| `read_customers` | Customer matching |
| `read_orders` | Order import and order-binding reconciliation |
| `read_inventory` | Inventory level read |
| `read_locations` | Location read |
| `read_merchant_managed_fulfillment_orders` | FulfillmentOrder read. **Not** `read_fulfillments` — that scope governs `FulfillmentService` objects, not this merchant-managed connector |

**Mutation-domain scopes** — required by the specific domains this
consolidated campaign's case list (§4) exercises, additional to the baseline
above:

| Scope | Why it is needed | Source |
| --- | --- | --- |
| `write_inventory` | M-INV-* cases (closes CV-013/#185); required by the inventory domain's own readiness seam whenever the inventory domain is enabled | `addons/shopify_connector_inventory/models/shopify_connector_inventory_service.py:430-473` |
| `write_merchant_managed_fulfillment_orders` | M-FUL-* cases (Gate D/#186); required by the fulfillment domain's own readiness seam | `addons/shopify_connector_fulfillment/models/shopify_connector_readiness_check.py:11-73` |
| `write_products` | M-EXP-* product/variant mutation cases — `productUpdate`/`productSet`/`productVariantsBulkUpdate`/`productVariantsBulkCreate` all require it | `addons/shopify_connector_product_export/models/shopify_connector_product_export_seams.py:75,84` |
| `write_files` | M-EXP-14…M-EXP-18, the media cases — `fileCreate` and the association mutation `fileUpdate` both require it. The readiness check's own gate only requires this scope conditionally (when `media_source_of_truth == 'odoo'`), but this campaign's own case list (§4.0a) includes the media cases regardless, so it is **mandatory for this campaign**, not optional | `addons/shopify_connector_product_export/models/shopify_connector_product_export_seams.py:76-86,304-306` |

**Explicitly forbidden:** `write_themes`. `fileUpdate` accepts `write_files`
**or** `write_themes` for the media-association path; this connector always
uses `write_files`, and `write_themes` is never requested — it would grant
theme write access the connector has no use for
(`shopify_connector_product_export_seams.py:82-83`).

**Not requested — verified unused by this exact implementation:**
`read_assigned_fulfillment_orders`, `write_assigned_fulfillment_orders`. The
prior version of this table listed them for the fulfillment domain. Neither
name appears anywhere in `addons/` (repository-wide search, this session) —
assigned-fulfillment-order scopes govern fulfillment-service-app assignment
functionality, a different mechanism from the merchant-managed
`FulfillmentOrder` model this connector uses exclusively. Removed because
they are not exercised anywhere in the frozen source, not because of a
platform policy change.

Verified against official Shopify documentation, API version 2026-07,
accessed 2026-07-28 (Accessible):
[Access scopes](https://shopify.dev/docs/api/usage/access-scopes) ·
[productUpdate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productUpdate) ·
[productSet](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet) ·
[productVariantsBulkUpdate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productVariantsBulkUpdate) ·
[fileUpdate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/fileUpdate) ·
[inventorySetQuantities](https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities) ·
[inventoryActivate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventoryActivate) —
each mutation's own Access Scopes section confirms the scope named above.

**No Shopify resource exists and no campaign case has executed as of this
correction.** **Record the granted scope set verbatim** in the run record; a
granted set wider than this table is itself a finding.

### 2.4 Authorization gates

- Every mutating case (M-*, R-*) requires a **named approver** recorded before
  execution. Read-only cases (D-*) do not.
- No case may run against any store other than the provisioned one. Each case
  asserts the store identity (§3.2) before acting.
- The connector's own Layer-2 substrate remains the only mutation path; no case
  calls the Shopify API by hand.

## 3. Synthetic data and identity guards

### 3.1 Fixtures — synthetic only

Products `ADAMS-UAT-P1..P5`, customers `Adams UAT Customer 1..3` with
`@example.com` addresses and no real phone numbers, orders `#ADAMS-UAT-*`. No
real person's name, address, email or phone enters the store at any point.

### 3.2 Store-identity guard

Before every case: assert the connector store record's `shop_domain` equals the
provisioned store's domain **and** the connector's recorded shop identity
matches. A mismatch is an immediate hard stop.

### 3.3 Baseline snapshot

Before case 1, record: product/variant count, inventory levels per location,
order count, fulfillment count, and the FulfillmentOrder set for each seeded
order. Cleanup (§7) is verified against this baseline.

## 4. Numbered cases

Legend — **Expected** is the observable result; **Evidence** is what must be
captured, sanitized, and attached to the run record.

### 4.0 `X-EXPORT-0` — NON-BLOCKING RESEARCH (reclassified 2026-07-26)

> **Reclassification, 2026-07-26 (control-room continuation ruling).**
> `X-EXPORT-0` **no longer gates Task 015 implementation.** It is retained as
> **non-blocking research**, because the production export design no longer
> depends on `productSet` preserving list fields that are omitted entirely.
>
> The dependency was removed rather than resolved. `productSet` is no longer
> the update mutation: an existing product is updated through `productUpdate`
> (whose input object has **no** `variants` and **no** `productOptions` field,
> and whose collection handling is the additive/subtractive
> `collectionsToJoin`/`collectionsToLeave`), `productVariantsBulkUpdate` with
> `allowPartialUpdates: false`, and `productVariantsBulkCreate` with
> `strategy: PRESERVE_STANDALONE_VARIANT`. `productSet` survives only on the
> create path, where there is by definition no merchant state to destroy.
> Full verification:
> [`task-015-export-source-verification-2026-07-26-addendum.md`](task-015-export-source-verification-2026-07-26-addendum.md)
> §2.
>
> **The earlier X-EXPORT-0 experiment produced no behavioural result.** It
> ended in an API-VERSION HARD STOP: no Shopify mutation was executed, no
> object and no residue existed, and the connector it was attempted against
> exposed a pre-`2026-07` schema without proving one exact version. It is
> neither a PASS nor a FAIL. Running it later is still worth doing — the
> answer is useful to know — but nothing waits on it.
>
> **Version discriminators, recorded so the next attempt does not repeat the
> mistake:** `grams` is **unreliable** (Shopify's changelog and the current
> reference conflict). `BusinessEntity.legalEntityId` and `GiftCard.lineItem`
> are valid positive `2026-07` markers. `ProductSetInput.id` still exists as
> **deprecated**, and `identifier.id` is the preferred targeting form.
>
> Historical framing follows unchanged. Source:
> [`task-015-export-source-verification-2026-07-26.md`](task-015-export-source-verification-2026-07-26.md)
> §3 — the official documentation does **not** resolve whether a list field
> that is omitted from a `productSet` input entirely is left alone or has all
> its remote entries deleted. Task 015's whole containment argument (that
> `collections`, `metafields` and media are protected **by being omitted**)
> depends on the answer. If the strict reading holds, a first export silently
> destroys merchant data the connector never owned.

| # | Case | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| **X-EXPORT-0** | `productSet` omitted-list-field boundary | On a throwaway synthetic product: (1) add it to two collections, set one merchant-authored metafield, attach one image; (2) record the full state; (3) call `productSet` with an input that omits `collections`, `metafields` and media **entirely** (supplying only allowlisted scalar fields); (4) re-read the product. | **Record what actually happened — both outcomes are valid results of this experiment.** If the collections, metafield and image all survive, D-015-3's containment argument holds and Task 015 may proceed. If any of them is gone, the export design must change before any code is written: omission is not protection, and every list field must be supplied explicitly and completely. | Before/after full product read (sanitized), the exact request sent, the API version string returned by the store, and a one-line verdict naming which reading is true. |

**Do not proceed past this case on either assumption** — *if the design ever
depends on it again*. A "probably fine" there would be a decision to risk
deleting a merchant's collections. As of 2026-07-26 nothing depends on it.

The prior instruction to re-confirm §2 against the store's **pinned** API
version is **discharged**: the `2026-07` documentation URLs returned HTTP 200
on 2026-07-26 and every statement was re-verified against the pinned version.
See the addendum §1.

### 4.0a Export mutation cases — `M-EXP-*` (Task 015 / 015B)

> Mutation cases. Each needs a named approver recorded before execution (§2.4),
> and each asserts the store identity before acting.

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| M-EXP-1 | Confirm a preview for an unbound product, then apply | One product created; DRAFT; **unpublished**; bindings written for template and every variant | Product GID, binding rows, status |
| M-EXP-2 | Replay the create job | **No** second product; the `customId` upsert or the reconciliation read converges on the first | Product count = 1, attempt ledger |
| M-EXP-3 | Interrupt the create transport mid-flight | Reconciliation read by `customId` only; **never** a blind resend | Attempt state, reconcile job |
| M-EXP-4 | Update a bound product's title/vendor/tags | `productUpdate` applied; **collections, merchant metafields and existing media unchanged** — verified by before/after read | Before/after full product read |
| M-EXP-5 | Add a merchant collection + metafield + image in Shopify, then run an update | All three survive the update untouched | Before/after read |
| M-EXP-6 | Update a mapped variant's price and SKU | `productVariantsBulkUpdate` applied atomically; `allowPartialUpdates` false | Variant read, request echo |
| M-EXP-7 | Add a variant in Odoo, preview, confirm, apply | `productVariantsBulkCreate` with `PRESERVE_STANDALONE_VARIANT`; **no existing variant deleted** | Variant list before/after |
| M-EXP-8 | Delete a variant in Shopify that a binding names | Blocked to manual review; **nothing written** | Job state, review case |
| M-EXP-9 | Add a variant in Shopify the connector does not own, then apply | Survives untouched; disclosed in the preview as unowned | Before/after variant list |
| M-EXP-10 | Change the option structure in Shopify, then preview | `remote_option_divergence` refused; no variant write planned | Preview record |
| M-EXP-11 | Edit the product in Shopify between preview and apply | Apply refuses; preview expires; **nothing written** | Job state, preview state |
| M-EXP-12 | Confirm, wait past the 24h expiry, then apply | Refused; fresh preview required | Preview state |
| M-EXP-13 | Set `price_source_of_truth = shopify_authoritative`, then apply | Price fields **absent** from the request | Request echo |
| M-EXP-14 | Media: append one image | `stagedUploadsCreate` → upload → `fileCreate` → poll to `READY` → `fileUpdate(referencesToAdd)`; **no association before READY** | Attempt ledger, `fileStatus` trace |
| M-EXP-15 | Media: re-run with the same image | **No** second upload (checksum no-op) | Registry row count |
| M-EXP-16 | Media: change the image and re-run | New image appended; **old File and association retained**, old row flagged `orphan_cleanup_candidate` | Product media list, registry |
| M-EXP-17 | Media: a merchant-uploaded image on the same product | Survives every connector operation | Before/after media list |
| M-EXP-18 | Media: force a `FAILED` `fileStatus` (bad file) | Manual review; **nothing associated** | Row status, job state |
| M-EXP-19 | Point the connector at a store serving another API version | Every call fails closed with the configuration class; **no mutation** | Redacted log, job state |
| M-EXP-20 | Confirm `fileUpdate(referencesToAdd:)` actually makes the File the product's media | Documented behaviour confirmed **or** the association path corrected | Product media list before/after |

**M-EXP-20 is the one 015B behaviour this batch could not verify from
documentation** and is called out rather than assumed.

### 4.1 Read / discovery (no mutation) — `D-*`

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| D-1 | Test connection with a valid credential | Succeeds; readiness reports API version and granted scopes | Redacted result, API version |
| D-2 | Test connection with a revoked credential | Fails closed with an operator-readable reason; **no** token value in any log | Redacted log excerpt |
| D-3 | Product + variant read | Seeded products import; no duplicate binding | Binding count, before/after |
| D-4 | Customer read + deterministic matching | Each customer matches once; re-run creates no duplicate | Match keys, re-run delta |
| D-5 | Order import | Seeded orders import to Odoo sale orders with correct totals/currency | Order bindings, totals |
| D-6 | Order import **replay** (same page twice) | Zero duplicate orders or lines | Count delta = 0 |
| D-7 | Inventory level read | Levels match Shopify per location | Level table |
| D-8 | FulfillmentOrder read for a seeded order | FO GIDs and line items resolve | FO GID list |
| D-9 | Pagination beyond one page | Every page consumed exactly once; no gap, no repeat | Cursor trace |
| D-10 | Unknown/future enum value present | Preserved raw, flagged `schema_warning`, never treated as success | Evidence row |

### 4.2 Inventory mutation — `M-INV-*` (closes CV-013 / #185)

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| M-INV-1 | Push a level change for one variant/location | Shopify reflects the exact quantity; one mutation attempt; one binding | Before/after level, attempt id |
| M-INV-2 | Read-after-write | Read matches the written value | Level read |
| M-INV-3 | Replay the same mutation | **No** second remote write; idempotency short-circuits | Attempt count = 1 |
| M-INV-4 | Concurrent push of the same pair from two workers | Exactly one remote write; the other yields cleanly | Attempt ledger, PIDs |
| M-INV-5 | Push while the store is disconnecting | Refused; no remote call | Job state |
| M-INV-6 | Drift introduced in Shopify, then reconcile | Review case first; no silent overwrite | Review case, no write |
| M-INV-7 | Uncertain outcome (transport interrupted mid-mutation) | **Reconcile-only**; never a blind resend | Attempt state, reconcile job |

### 4.3 Fulfillment mutation — `M-FUL-*` (Gate D)

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| M-FUL-1 | Validate an Odoo delivery → create a Shopify fulfillment | One Fulfillment created; one binding; `notifyCustomer` follows the persisted enqueue-time decision | Fulfillment GID, binding |
| M-FUL-2 | Replay the create | No second Fulfillment | Fulfillment count |
| M-FUL-3 | Backorder: one FO fulfilled by two pickings | Two Fulfillments, one binding each; no FO-GID uniqueness violation | Binding rows |
| M-FUL-4 | Tracking update on an existing fulfillment | Tracking reflected in Shopify | Tracking snapshot |
| M-FUL-5 | Tracking update replay | No duplicate remote write | Attempt count |
| M-FUL-6 | Uncertain outcome after C2 | Refused for resend; reconcile-only; the U1 release action **refuses** it | Attempt state, UI refusal |
| M-FUL-7 | Externally created fulfillment observed (Mode 1) | Review case, `external_fulfillment_observed`, **zero** Odoo stock change | Evidence row, picking state |
| M-FUL-8 | Mode 2 with all 16 conditions passing | Applied exactly once; ledger updated | Evidence, ledger |
| M-FUL-9 | Mode 2 with one condition failing (each of the 16, in turn) | Held for review; nothing applied | 16 evidence rows |
| M-FUL-10 | Carrier reports delivered, Odoo picking not validated | `delivered_inconsistency` set; **no** stock movement; U1 shows the qualified banner | Evidence row, screenshot |
| M-FUL-11 | Mode switch 1→2 with the safe scan | Scan completes before any auto-apply | Job trace |
| M-FUL-12 | Mode rollback 2→1 mid-flight | Pending evaluations cancelled to review; applied work untouched | Job states |

### 4.4 Reconnect / reconciliation — `R-*`

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| R-1 | Disconnect, change data in Shopify, reconnect | Catch-up reconciles; no duplicate | Job trace, counts |
| R-2 | Reconnect against a **different** store | Store-identity mismatch refuses fail-closed | Refusal record |
| R-3 | Reconciliation scan watermark | Second scan does not re-process settled work | Scan trace |

### 4.5 Security / privacy — `S-*`

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| S-1 | Grep every produced log/artifact for the token | Zero occurrences | Grep output |
| S-2 | Force an API error and inspect the operator message | Redacted; no token, no raw payload | Message |
| S-3 | Two-company / two-store isolation with real remote data | No cross-store or cross-company read | Matrix |
| S-4 | Connector User attempts an Administrator-only remote action by direct RPC | `AccessError`, zero remote call | Attempt ledger empty |

### 4.6 Performance (#199) — `P-*`

| # | Case | Expected | Evidence |
| --- | --- | --- | --- |
| P-1 | Per-record Shopify-read reconciliation handler, 3 runs | Recorded as a **baseline only** | Timing table |
| P-2 | Queue drain with real remote latency | Recorded as a **baseline only** | Throughput table |

**No threshold is asserted by this package.** #199 remains open, and every
number produced here is baseline-only, never a guarantee, budget or SLA.

## 5. Expected-result discipline

A case **passes** only when the observable result matches the Expected column
exactly. "No error" is not a pass. A case that cannot be executed is recorded
**NOT EXECUTED**, never inferred from a neighbouring case.

## 6. Evidence handling (DEC-041 D3)

Every result is converted to a **sanitized durable GitHub record before the
runtime environment is torn down**. Ephemeral `/tmp` files, chat-only summaries
and untransferred tool output are **not admissible**. Each record states the
exact connector SHA, the Odoo.sh build id, the store domain, the case id, the
observed result, and the evidence class. Screenshots are cropped to remove any
credential surface.

## 7. Cleanup and verification

1. Delete every synthetic order, customer, product and variant created by the
   campaign.
2. Restore inventory levels to the §3.3 baseline.
3. Re-read the store and **verify** the baseline matches; a residual row is a
   finding, not a footnote.
4. Record the residue sweep result even when it is zero.

## 8. Credential revocation and rollback

- **Revoke the access token immediately** after the final case, before the run
  record is closed. Record the revocation timestamp.
- Uninstall the custom app from the development store.
- Rollback of connector behaviour is the ordinary branch revert; no case in this
  package writes to production Odoo data.
- If the campaign is aborted mid-way: revoke first, then record which cases ran,
  then perform §7 for whatever was created.

## 9. Triage

| Severity | Definition | Action |
| --- | --- | --- |
| **P0** | Data loss, duplicate remote mutation, credential exposure, cross-company leak, or a blind resend after an uncertain outcome | **STOP the campaign.** Revoke, record, escalate to the control room immediately |
| **P1** | A domain contract violated (idempotency, reconciliation, fail-closed) without data loss | Stop that domain; continue other domains; consolidated correction |
| **P2** | Wrong or misleading operator-visible behaviour | Record; continue; fix in the consolidated correction batch |
| **P3** | Wording/cosmetic | Record; fix in pass |

Findings are consolidated into **one** correction batch per campaign (DEC-041
D6), followed by one exact-SHA rerun of the affected cases.

## 10. Exit criteria

- Every case is **executed** and recorded as pass / fail / NOT EXECUTED.
- No P0 and no P1 remains open.
- Cleanup §7 verified against baseline, with the residue sweep recorded.
- The token is revoked and the app uninstalled.
- All records are durable on GitHub, sanitized, and name the exact SHA.
- The control room, not the executing session, accepts the campaign.
