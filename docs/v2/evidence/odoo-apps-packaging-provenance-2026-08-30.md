# Odoo Apps packaging provenance — 2026-08-30

This record accompanies the deterministic DEC-029 marketplace archives. It is
evidence for the release owner, not an Odoo Apps publisher claim. Official
source access date: **2026-08-30**. The public Apps pages intermittently
returned HTTP 429 through browser retrieval; direct GET access was available.
No upload or Odoo Apps acceptance is claimed.

## Edition source sets

| Output | Meta-addon | Direct companion modules | Required webhook closure | Archive command |
| --- | --- | --- | --- | --- |
| Lite | `shopify_connector_lite` | `shopify_connector_core`, `shopify_connector_product`, `shopify_connector_sale` | `shopify_connector_webhook`, `shopify_connector_product_webhook`, `shopify_connector_sale_webhook` | `python tools/build_shopify_connector_bundle.py --edition lite` |
| Full | `shopify_connector_full` | Lite plus `shopify_connector_inventory`, `shopify_connector_fulfillment`, `shopify_connector_product_export` | Lite closure plus `shopify_connector_inventory_webhook`, `shopify_connector_fulfillment_webhook` | `python tools/build_shopify_connector_bundle.py --edition full` |

The direct sets above are the accepted DEC-029 boundary.  The webhook
foundation and satellites are an explicit installation closure for the
near-real-time contract; each remains a separately installable engineering
addon and P20 consolidation is not performed.  The branch-introduced
historical `shopify_connector_suite` tree is omitted from the candidate and has
no `__manifest__.py`, so it is not discoverable as an Odoo application and is
not emitted by the builder.

## Official Apps Store source boundary

- [Apps upload](https://apps.odoo.com/apps/upload) publicly says **Register
  your Git repository** and requires sign-in. It does not document an arbitrary
  ZIP upload endpoint.
- [Apps Vendor Guidelines](https://apps.odoo.com/apps/vendor-guidelines) list
  mandatory `name`, `version`, `license`, and `depends` manifest fields;
  `name` must be no more than 25 characters. The optional fields listed there
  are `summary`, `live_test_url`, `price`, `currency`, and `support`, and a
  manifest error can unpublish all modules from a repository.
- [Odoo Apps FAQ](https://apps.odoo.com/apps/faq) documents dependencies from
  Odoo/Enterprise/Community/your own/another vendor, a free-only exception for
  an unpublished shared base, and icon/HTML/cover/license/repository/buyer-ZIP
  guidance.
- [Odoo 19 module documentation](https://www.odoo.com/documentation/19.0/developer/tutorials/backend.html)
  documents each module as a directory in an addons path with its own
  manifest and Python initializer.

These public sources support a multi-module registered repository and the
normal Odoo addon-tree convention. They do **not** state that one Apps
submission or customer download ZIP may contain multiple sibling module roots
or embedded dependencies. The sibling-root Lite/Full archives are therefore
reproducible Odoo evidence pending owner/Odoo validation, not a verified Apps
delivery format.

## License and attribution

- `LICENSE` is the verbatim GNU Lesser General Public License, version 3,
  dated 29 June 2007, as published by the Free Software Foundation.
- SHA-256 of the checked-in file:
  `e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118`.
- Connector manifests identify the existing code author as `Adams` and declare
  `LGPL-3`; no third-party source is vendored by the meta-addons.
- The builder places the complete `LICENSE` at the archive root and refuses a
  missing or altered copy.  Copyright ownership, contributor notices, and any
  additional dependency notices remain subject to the release owner's legal
  review.

## Screenshot provenance

Full's six screenshots are byte-for-byte copies of the browser-evidence
sources listed in `tools/build_shopify_connector_bundle.py`.  The builder
requires each source to remain under `docs/05-qa/evidence/`, to have a
provenance README containing browser/Chromium/screenshot markers, and to pass
PNG header and hash checks.  Lite intentionally has no screenshot targets in
this candidate because the available captures expose Full-only surfaces; its
manifest uses `images=[]`.  The captures use synthetic fixtures and are not
live Shopify, Odoo.sh, or UAT acceptance evidence.

## Reproducibility and exclusion boundary

`tools/build_shopify_connector_bundle.py` uses fixed ZIP timestamps, fixed
file modes, and maximum DEFLATE compression.  It excludes Python repository
tests, documentation, caches, credentials, nested archive suffixes, and the
inert P16/V2 source trees. Manifest-declared `static/tests` unit assets and
`web.assets_tests` browser tours are retained; tours are runtime/test-mode
assets and are not presented as production behavior. It rejects symlinked
addon roots, license/screenshot inputs, and all other package sources so a
package cannot read outside the checkout.

The CI runner installs each candidate meta-addon and verifies its direct-plus-
webhook closure on a disposable Odoo 19 database as a separate candidate-only
check.  Its version-to-version migration passes continue to install and
upgrade only the legacy `MODULES` set, so an older migration tree is never
required to contain the newly introduced meta addons.

## Publisher boundary

`publisher` is not a documented Odoo 19 manifest field; the [Odoo 19 manifest
reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)
documents `author`, `website`, and `maintainer` instead. The Apps-specific
`support` and `live_test_url` fields are optional in the Vendor Guidelines, but
their real values and the publisher/account identity remain unresolved. No
pricing, website, support address, live-test URL, billing, entitlement, or
publisher identity beyond the repository's existing `Adams` author value is
invented here. The release owner must complete the repository registration and
publisher fields and confirm ownership/support details before submission.

## Listing-image boundary

The [Apps FAQ](https://apps.odoo.com/apps/faq) expects a real PNG at
`static/description/icon.png`, rich HTML at `static/description/index.html`,
and manifest `images` paths for cover/screenshot material; the [Vendor
Guidelines](https://apps.odoo.com/apps/vendor-guidelines) expect accurate
English description, thumbnail/cover, screenshots or previews and score a
missing cover negatively. No official source says `images=[]` is a scanner
failure or says an empty list is accepted as a complete listing. Lite's empty
images state is therefore disclosed evidence requiring owner/Odoo validation,
not a claimed acceptance.
