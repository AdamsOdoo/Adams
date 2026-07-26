# Task 015 / 015B — official Shopify source verification, 2026-07-26

> **Status: verification evidence and a HARD STOP finding. No export code
> exists or is authorized by this record.** Produced on
> `fable/wave-5-completion` under the control-room continuation ruling of
> 2026-07-26, which requires: *"Re-verify every GraphQL type, field,
> mutation, scope, deprecation and return identity against official Shopify
> Admin GraphQL 2026-07 documentation before coding."*
>
> This verification was performed **before any export code was written**, and
> it is the reason none was. §3 records a finding that the export packets'
> central safety argument rests on an assumption the official documentation
> does not confirm.
>
> **No Shopify store, credential, request, mutation or webhook was involved.**
> Only public documentation was read.

## 1. Method

`[Fact]` Public Shopify developer documentation was fetched over HTTPS on
2026-07-26 and read directly. The `2026-07`-pinned URLs returned **HTTP 503**
at the time of access; the `latest` URLs returned **HTTP 200** and were used
instead. **This is itself a limitation and is recorded as one** (§4): `latest`
is not provably identical to the store-pinned `2026-07` version, so every
statement below is verified against `latest` and must be re-confirmed against
the pinned version during the provisioned-store campaign.

| Source | Access | Status |
| --- | --- | --- |
| `https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet` | Accessible | 200 |
| `https://shopify.dev/docs/api/admin-graphql/latest/input-objects/ProductSetIdentifiers` | Accessible | 200 |
| `https://shopify.dev/docs/api/admin-graphql/latest/mutations/fileCreate` | Accessible | 200 |
| `https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/productSet` | **Blocked** | 503 |

## 2. Confirmed against source

`[Fact — direct quotation from the documentation]`

### 2.1 `productSet` field semantics

> "The behavior of `productSet` depends on the type of field it's modifying:
>
> - **For list fields**: Creates new entries, updates existing entries, and
>   deletes existing entries that aren't included in the mutation's input.
>   Common examples of list fields include `collections`, `metafields`, and
>   `variants`.
>
> - **For all other field types**: Updates only the included fields. Any
>   omitted fields will remain unchanged."

This **confirms D-015-3's premise**: a supplied `variants` list deletes any
remote variant absent from it. The destructive-list guard is therefore
necessary, exactly as the packet says.

### 2.2 `productSet` modes and limits

> "By default, stores have a limit of 2048 product variants for each product."

Synchronous mode "returns the updated product in the response"; asynchronous
mode returns a `ProductSetOperation` polled via the `productOperation` query.
**Confirms D-015-4's choice** of synchronous-only for MVP and its statement
that the 2048 ceiling is unreachable by construction at ≤100 variants.

### 2.3 `identifier` — custom-ID upsert

`[Fact]` `productSet` accepts `identifier: ProductSetIdentifiers`, documented
as "identifier that will be used to lookup the resource". The input object's
members are:

```
ProductSetIdentifiers {
  customId: UniqueMetafieldValueInput
  handle: String
  id: ID
}
```

**Confirms D-015-4's `customId` upsert design** — including that `customId`
takes a `UniqueMetafieldValueInput`, which is what makes the
`metafieldDefinitionCreate` step a genuine prerequisite rather than an
optimisation.

### 2.4 Scopes

`[Fact]` `productSet` — "Requires `write_products` access scope. Also: The
user must have a permission to create products."

`[Fact]` `fileCreate` — "Requires `write_files` access scope, `write_themes`
access scope **or** `write_images` access scope. Also: Users must have create
files permissions."

**This confirms the continuation ruling's correction on 015B**: `write_images`
is sufficient for `fileCreate`, so the least-privilege pair
`write_images` + `write_products` is correct and **`write_themes` must not be
requested** — it would grant theme write access the connector has no use for.

### 2.5 `fileCreate` pipeline

`[Fact]` The documentation describes `fileCreate` as creating "file assets for
a store from external URLs or files that were previously uploaded using the
`stagedUploadsCreate` mutation", landing them on the store's **Files** page.
**Confirms 015B's `stagedUploadsCreate` → upload → `fileCreate` sequence.**

### 2.6 Idempotency

`[Fact]` Nothing in the `productSet` documentation marks the mutation
`@idempotent`. **Confirms the packet's premise** that create-retry safety must
come from the `customId` upsert, not from an idempotency directive.

## 3. HARD STOP — the delete-on-omit boundary is NOT resolved by source

`[Fact, then Inference]`

**D-015-3's containment argument depends on a proposition the documentation
does not state.** The packet's own wording:

> "omitted non-list fields stay unchanged; but omitted LIST fields would
> delete — verified nuance: the delete-on-omit semantics apply to entries
> within a supplied list; lists not supplied at all are not modified per the
> 'Updates only the included fields' rule for non-included fields — **this
> exact boundary is a named empirical verification item in §5's dev-store
> run, never assumed**."

Read against the quoted source in §2.1, the two documented rules do not
settle it:

- the **list-field** rule deletes "existing entries that aren't included in
  the mutation's input" — read strictly, a `collections` list that is absent
  entirely includes no entries, and every remote entry "isn't included";
- the **all-other-field-types** rule ("omitted fields will remain unchanged")
  is stated for field types *other than lists*, so it does not obviously
  rescue an omitted list.

**The documentation does not say which reading is correct.** `[Inference —
high confidence, from the two quoted rules]`

This matters because the whole of D-015-3's safety rests on the safe reading:
`collections`, `metafields` and media are protected **by being omitted**. If
the strict reading is the true one, a first export would silently delete every
collection membership, every merchant-authored metafield, and every image on
the exported product — merchant data this connector never owned and cannot
restore.

**The packet already knew this and scheduled it as a dev-store empirical
check.** That check requires a provisioned Shopify store, which this session
has none of and is expressly forbidden from using.

### 3.1 Consequence, stated plainly

**Task 015's apply path is NOT implemented, and this is why.** Export is a
mutation domain. Building a destructive-write guard on an unverified
assumption about *when Shopify deletes merchant data* is precisely the class
of work the export operating model and CLAUDE.md §8 forbid proceeding on by
inference. The correct outcome of a source-verification gate that fails is a
stop, not a best guess.

**Task 015B inherits the stop** — it is sequenced after 015 and attaches media
to products created by it.

**U3's export-flow screens (S27/S7) inherit it too** — there is no
`action_confirm_export_preview` to wire a preview/diff surface to.

### 3.2 What would clear it `[Recommendation]`

One dev-store run, on a throwaway product, recording:

1. create a product with two collections, one merchant metafield and one
   image;
2. call `productSet` with an input that omits `collections`, `metafields` and
   media entirely;
3. re-read the product and record whether the collections, metafield and
   image survived.

That single experiment resolves the boundary definitively. It belongs in
[`shopify-live-validation-package.md`](shopify-live-validation-package.md) and
is added there as a **blocking prerequisite of Task 015**, ahead of the export
cases, rather than being one case among forty.

## 4. Limitations of this verification

- **Version drift `[Fact]`.** The `2026-07`-pinned documentation URLs returned
  503; `latest` was read instead. Every statement above must be re-confirmed
  against the store's pinned version before export code is accepted.
- **Documentation, not schema introspection `[Fact]`.** No Shopify endpoint
  was queried, so no field was verified against a live schema. Deprecations
  that exist in the schema but not in prose would not be caught here.
- **No behavioural verification `[Fact]`.** Everything above is what Shopify
  *documents*. §3 exists precisely because documented behaviour ran out before
  the question that matters did.

## 5. Not done and not claimed

- No export module, model, job type, mutation strategy or view exists.
- No Shopify credential, request, mutation or webhook. No store was contacted.
- No claim that `productSet`, `fileCreate` or `stagedUploadsCreate` has been
  exercised, and no fabricated response, latency or evidence anywhere.
- PD-PX-1..7 are unchanged; this record corrects no product policy. It records
  what the official source says and where it stops.
