# Task 015 / 015B — 2026-07 source re-verification and the X-EXPORT-0 correction

> **Status: verification evidence. NOT an acceptance, NOT a runtime record, and
> NOT independent review.** Produced 2026-07-26 under the consolidated Wave 5
> completion continuation ruling of the same date, which supersedes the earlier
> decision that `X-EXPORT-0` must block implementation.
>
> This addendum is appended to
> [`task-015-export-source-verification-2026-07-26.md`](task-015-export-source-verification-2026-07-26.md).
> **Nothing in that record is rewritten.** Its §3 HARD STOP was correct on its
> own evidence and at its own time; what changed is (a) the pinned-version
> documentation became reachable, and (b) the control room ruled that the
> production design must no longer depend on the unresolved proposition. Both
> are recorded here rather than by editing history.
>
> **No Shopify store, credential, request, mutation or webhook was involved.**
> Only public documentation and the public schema were read.

## 1. Method, and the one limitation the prior record could not clear

`[Fact]` Public Shopify developer documentation was fetched over HTTPS on
2026-07-26 and read directly. **The `2026-07`-pinned URLs returned HTTP 200 on
this access.** The prior record (§1, §4) had to fall back to `latest` because
the pinned URLs returned 503, and correctly recorded that as a limitation.

**That limitation is now cleared for every statement below**: each is verified
against the **store-pinned `2026-07`** reference, not against `latest`.

| Source (all `.../admin-graphql/2026-07/...`) | Access | Status |
| --- | --- | --- |
| `mutations/productSet` | Accessible | 200 |
| `mutations/productUpdate` | Accessible | 200 |
| `mutations/productVariantsBulkUpdate` | Accessible | 200 |
| `mutations/productVariantsBulkCreate` | Accessible | 200 |
| `mutations/productCreateMedia` | Accessible | 200 |
| `mutations/fileCreate` | Accessible | 200 |
| `mutations/fileUpdate` | Accessible | 200 |
| `mutations/stagedUploadsCreate` | Accessible | 200 |
| `mutations/metafieldDefinitionCreate` | Accessible | 200 |
| `input-objects/ProductUpdateInput` | Accessible | 200 |
| `input-objects/ProductSetInput` | Accessible | 200 |
| `input-objects/ProductVariantsBulkInput` | Accessible | 200 |
| `input-objects/FileUpdateInput` | Accessible | 200 |
| `input-objects/CreateMediaInput` | Accessible | 200 |
| `input-objects/UniqueMetafieldValueInput` | Accessible | 200 |
| `input-objects/MetafieldDefinitionInput` | Accessible | 200 |
| `interfaces/File` | Accessible | 200 |
| `enums/FileStatus` | Accessible | 200 |
| `enums/ProductVariantsBulkCreateStrategy` | Accessible | 200 |
| `objects/BusinessEntity` | Accessible | 200 |
| Public Admin GraphQL schema introspection (`MetafieldCapabilityCreateInput`) | Accessible | schema tool |

**Still not done and still not claimed `[Fact]`:** no Shopify endpoint of any
store was queried, no credential exists, and **no behavioural verification of
any kind** was performed. Everything below is what Shopify *documents*.

## 2. The finding that removes the dependency

`[Fact — 2026-07 `ProductUpdateInput` reference, complete field list]`

```
ProductUpdateInput {
  category: ID
  collectionsToJoin: [ID!]
  collectionsToLeave: [ID!]
  deleteConflictingConstrainedMetafields: Boolean
  descriptionHtml: String
  giftCardTemplateSuffix: String
  handle: String
  id: ID
  metafields: [MetafieldInput!]
  productType: String
  redirectNewHandle: Boolean
  requiresSellingPlan: Boolean
  seo: SEOInput
  status: ProductStatus
  tags: [String!]
  templateSuffix: String
  title: String
  vendor: String
}
```

`[Fact]` **`ProductUpdateInput` has no `variants` field and no
`productOptions` field.** `[Fact]` Its collection handling is the additive /
subtractive pair `collectionsToJoin` / `collectionsToLeave`, not a declarative
`collections` list.

`[Inference — high confidence, directly from the field list]` Therefore
`productUpdate` **cannot** delete a variant, a product option, an option value
or a collection membership, however it is called. A collection membership can
only be removed by *naming it* in `collectionsToLeave`. Compare
`ProductSetInput`, whose 22 fields include `collections: [ID!]`,
`metafields: [MetafieldInput!]`, `productOptions: [OptionSetInput!]`,
`variants: [ProductVariantSetInput!]` and `files: [FileSetInput!]` — six list
fields governed by the delete-on-omit rule.

**This is what makes the ruling implementable.** The unresolved proposition —
what `productSet` does with a list field omitted *entirely* — stops being
load-bearing the moment the update path stops using `productSet`. The design
does not answer the question; it stops asking it.

`[Fact]` Confirmed for the rest of the split:

- `productUpdate` — "Requires `write_products` access scope"; arguments
  `identifier: ProductUpdateIdentifiers`, `media: [CreateMediaInput!]`,
  `product: ProductUpdateInput`, and a **deprecated** `input: ProductInput`;
  returns `product` + `userErrors`. Not deprecated itself.
- `productVariantsBulkUpdate` — `allowPartialUpdates: Boolean` (default
  `false`), documented as "When partial updates are allowed, valid variant
  changes may be persisted even if some of the variants updated have invalid
  data"; `productId: ID!`; `variants: [ProductVariantsBulkInput!]!`. Requires
  `write_products`.
- `productVariantsBulkCreate` — `strategy: ProductVariantsBulkCreateStrategy`,
  whose values are `DEFAULT` ("Deletes the standalone default ("Default
  Title") variant when it's the only variant on the product"),
  `PRESERVE_STANDALONE_VARIANT` ("Preserves the existing standalone variant
  when the product has only a single default or custom variant") and
  `REMOVE_STANDALONE_VARIANT`.
  **`DEFAULT` performs a remote deletion**, so it is not available to this
  connector; `PRESERVE_STANDALONE_VARIANT` is what the module sends.
- `ProductVariantsBulkInput` carries `id`, `price`, `compareAtPrice`,
  `barcode`, `inventoryItem`, `optionValues`, and also `inventoryQuantities`
  and `metafields` — the latter two are inside the connector's
  forbidden-key guard precisely because the input object would accept them.

## 3. `X-EXPORT-0` — the record corrected

`[Fact — corrections required by the ruling, recorded verbatim in substance]`

| # | Correction |
| --- | --- |
| 1 | `X-EXPORT-0` remains an **API-VERSION HARD STOP**. It is **not** a PASS and **not** a FAIL. |
| 2 | **No Shopify mutation was executed.** |
| 3 | **No object and no residue existed** as a result of it. |
| 4 | The Claude Shopify connector exposed a **pre-`2026-07` schema** but **did not prove one exact version**. |
| 5 | Shopify's `grams` changelog and the current reference **conflict**, so `grams` is an **unreliable version discriminator** and must not be used as one. |
| 6 | `BusinessEntity.legalEntityId` and `GiftCard.lineItem` are **valid positive `2026-07` markers**. `[Verified this session]` `BusinessEntity.legalEntityId: BigInt` — "The stable central legal entity ID associated with this business entity" — is present in the `2026-07` reference. |
| 7 | `ProductSetInput.id` **still exists as deprecated** `[Verified this session — the 2026-07 field list marks `id: ID` "(Deprecated)"]`. |
| 8 | `identifier.id` is the **preferred targeting form**. The connector's update path uses `productUpdate(identifier: {id: ...})` accordingly, and a test pins it. |
| 9 | **`X-EXPORT-0` is now non-blocking research**, because the implementation no longer depends on omitted-list preservation. |

**No empirical behaviour is fabricated anywhere in this record.** The
experiment produced no behavioural result, and none is claimed or inferred.

## 4. 015B — the media surface, and a correction to the earlier scope conclusion

`[Fact]` `fileCreate` — "Requires `write_files` access scope, `write_themes`
access scope **or** `write_images` access scope."

`[Fact]` `fileUpdate` — "Requires `write_files` access scope, `write_themes`
access scope." **`write_images` is not accepted.** `FileUpdateInput` carries
`referencesToAdd: [ID!]` — "The IDs of the references to add to the file.
Currently only accepts product IDs" — and the symmetric `referencesToRemove`.

`[Fact]` `productCreateMedia` is **deprecated**: "Use `productUpdate` or
`productSet` instead." `productUpdateMedia` is **deprecated**: "Use
`fileUpdate` instead."

`[Fact]` `CreateMediaInput` has exactly three fields — `alt`,
`mediaContentType: MediaContentType!`, `originalSource: String!`. It has **no
`id`**, so `productUpdate(media:)` creates media from a *source URL*; it
cannot attach an existing `File`.

`[Fact]` `FileStatus` = `UPLOADED` / `PROCESSING` / `READY` / `FAILED`. The
`File` interface exposes `alt`, `createdAt`, `fileErrors`, `fileStatus`, `id`,
`preview`, `updatedAt` — **and no reverse-reference connection**, confirming
the 015B header note against the pinned version.

### 4.1 The scope correction, stated plainly

`[Inference — high confidence, from the two scope facts above]` The prior
record's §2.4 concluded that least privilege for media is `write_images` +
`write_products`. **That is correct for `fileCreate` and insufficient for the
pipeline D-015B-4 requires.** The READY gate can only be honoured by creating
an independently addressable `File`, polling its `fileStatus`, and *then*
associating it — and the only 2026-07 mutation that associates an **existing**
`File` with a product is `fileUpdate`, which does not accept `write_images`.

The least-privilege set that actually satisfies the binding requirements is
therefore **`write_products` + `write_files`**, and `write_files` subsumes
`write_images` for `fileCreate`, so the set is two scopes rather than three.
**`write_themes` is never requested**, and its presence in a granted-scope
snapshot is treated as a readiness **failure**, not merely tolerated.

`[Recommendation]` If a future control-room decision prefers the narrower
`write_images`, the only way to get it is to abandon the READY gate and
associate through `productUpdate(media:)` with a staged URL — i.e. to accept
association *before* `READY`. That trade is a product decision, not an
implementation one, and it is recorded here rather than made silently.

## 5. API version — the binding ruling, and what was verified

`[Fact]` The connector now sends every Admin GraphQL request to
`/admin/api/2026-07/graphql.json`, built from a single centralized constant
(`addons/shopify_connector_core/tools/api_version.py`). The store's recorded
`api_version` is **verified against** that constant before any request and is
never used to build the endpoint.

`[Fact]` Every response's `X-Shopify-API-Version` header is inspected and must
equal `2026-07`; a mismatch **or a missing header** raises before the response
is treated as successful, classified `odoo_validation_configuration` (the
existing DEC-009 "manual fix then retry" class — no 17th error class is
introduced). Diagnostics carry only the two version strings.

**This supersedes the prior soft behaviour, and the change is not cosmetic.**
The merged code recorded a served-version mismatch as
`version_fallforward` + `api_health_state='degraded'` and **returned the
response as a success**. Two accepted tests asserted exactly that
(`test_version_fallforward_no_exception`,
`test_version_fallforward_warns_but_still_passes`). Both are **replaced** by
their inverses in this batch, and the replacement is recorded here because
inverting an accepted assertion is a behaviour change a reviewer must see
named rather than discover in a diff.

`[Inference]` The old disposition was defensible for a read-only connector and
is not defensible for a mutation domain: a `productUpdate` built against
2026-07 semantics, executed against another version's semantics, and reported
as applied is precisely the failure class this wave exists to prevent.

## 6. Not done and not claimed

- **No Shopify credential, request, mutation or webhook. No store contacted.**
- **No behavioural verification.** No claim that `productSet`, `productUpdate`,
  `productVariantsBulkUpdate`, `productVariantsBulkCreate`, `fileCreate`,
  `fileUpdate` or `stagedUploadsCreate` has ever been exercised.
- **No `X-EXPORT-0` result.** The omitted-list boundary remains unresolved by
  documentation and unresolved empirically; the design no longer depends on it.
- **No Odoo.sh runtime, no independent review, no UAT, no release readiness.**
- `fileUpdate(referencesToAdd:)`'s *effect* — that adding a product reference
  makes the File appear as that product's media — is what the field
  documentation states. **It is not behaviourally confirmed**, and it is
  recorded as the first live-validation item for 015B in
  [`shopify-live-validation-package.md`](shopify-live-validation-package.md).
