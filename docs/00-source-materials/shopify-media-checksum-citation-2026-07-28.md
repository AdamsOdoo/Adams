# Captured Source Material — Shopify `MediaImage` byte-checksum gap

> Closes the citation gap flagged by the independent review of PR #204
> (comment [`5100097485`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5100097485),
> §6/§18): TD-015's premise that byte correspondence between an Odoo-exported
> image and the Shopify-stored File cannot be proven was asserted as a
> `[Fact]` in project documents and code comments with no captured,
> URL-cited, dated schema excerpt anywhere under this directory. This file is
> that capture. Per `../01-research/research-methodology.md` §1 this is
> **Tier-1 fact** evidence; excerpts are verbatim from the cited pages.

## Access record

| Field | Value |
| --- | --- |
| Vendor / product | Shopify — GraphQL Admin API |
| API version shown on both pages | **2026-07** |
| Access date | **2026-07-28** |
| Access status | **Accessible** |
| URL 1 | https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImage |
| URL 2 | https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImageOriginalSource |

## `MediaImage` — documented field list [Fact]

**[paraphrase, field inventory]** As captured 2026-07-28, the `MediaImage`
object documents these fields: `alt`, `createdAt`, `fileErrors`,
`fileStatus`, `id`, `image`, `mediaContentType`, `mediaErrors`,
`mediaWarnings`, `metafield` (deprecated), `metafields` (deprecated),
`mimeType`, `originalSource`, `preview`, `status`, `translations`,
`updatedAt`.
— https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImage

None of the documented fields is named or described as a checksum, digest,
hash, or any other byte-content-verification mechanism.

## `MediaImageOriginalSource` — documented field list [Fact]

**[quote]** `fileSize` — "The size of the original file in bytes."
**[quote]** `url` — "The URL of the original image, valid only for a short
period."
— https://shopify.dev/docs/api/admin-graphql/latest/objects/MediaImageOriginalSource

`fileSize` is a byte **count** (a length), not a digest of the byte
**content** — two images of equal size can have arbitrarily different
content, so this field cannot distinguish them. `url` is a temporary,
authenticated CDN link to the stored bytes, not a value computed from them.
Neither field is a checksum, digest, hash, or byte-content-verification
mechanism.

## Required factual boundary [Fact]

- `MediaImage` exposes its documented identity/status/source-related fields
  (listed above) and no others.
- `MediaImageOriginalSource` exposes `fileSize` (a length) and a temporary
  `url`, and no others.
- Neither documented field list exposes a checksum/digest field.

## Required inference boundary [Inference]

Therefore the connector cannot prove stored-byte correspondence between an
Odoo-exported image and the Shopify-stored `MediaImage` File using these
documented fields alone. This is a bounded inference from the fact above,
not itself a Shopify statement, and it does not extend beyond it:

- **Not claimed:** that Shopify has no checksum anywhere, in every API or
  internal system it operates — only that the documented `MediaImage`
  connection this connector reads exposes none.
- **Not claimed:** that downloaded URL bytes were independently compared
  against the uploaded bytes by this project.
- **Not claimed:** that cryptographic byte equality was remotely proven for
  any binding, by this project or by Shopify.
- **Not claimed:** that any live-Shopify validation occurred to produce this
  citation. This capture is documentation-only: two `shopify.dev` pages were
  fetched over HTTPS; no Shopify store, credential, request, mutation, or
  webhook of any kind was involved.

## Where this fact is used

`ACKNOWLEDGEABLE_RECONCILE_REASON = 'checksum_unverifiable'`
(`addons/shopify_connector_product_export/models/
shopify_connector_export_reconnect.py`,
`_checksum_unverifiable_divergence`) and the corresponding operator-facing
`unprovable_summary` copy in the TD-015 acknowledgement wizard
(`addons/shopify_connector_product_export/wizards/
shopify_connector_product_export_wizards.py`) rest on exactly this fact and
no more: association, product identity, archive state, the governed variant
GID set, File identity and File status are all independently re-read from
Shopify and proven; the one thing the pass cannot prove, and routes to an
explicit, auditable, revocable operator acknowledgement rather than silently
assuming, is stored-byte correspondence — because the documented API gives
it nothing to prove that with.
