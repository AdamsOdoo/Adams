# Odoo Apps packaging evidence — 2026-08-30 remedy baseline

> **Marketplace-source boundary (access date: 2026-08-30).** This record
> separates the repository's deterministic Odoo addon archives from what the
> Odoo Apps Store publicly documents about submission and acceptance. The
> public Apps upload page says **Register your Git repository**; it does not
> document an arbitrary multi-addon ZIP upload. No upload, publisher-account
> action, or Odoo Apps acceptance is claimed here. The Apps pages intermittently
> returned HTTP 429 through browser retrieval; a direct GET was available, but
> no source found below defines the missing multi-root-archive or empty-image
> behavior.

## Scope

This evidence records the deterministic DEC-029 marketplace outputs:

| Edition | Meta-addon | Direct companion modules | Required webhook closure | Archive command |
| --- | --- | --- | --- | --- |
| Lite | `shopify_connector_lite` | `shopify_connector_core`, `shopify_connector_product`, `shopify_connector_sale` | generic + product/order satellites | `python tools/build_shopify_connector_bundle.py --edition lite` |
| Full | `shopify_connector_full` | Lite plus `shopify_connector_inventory`, `shopify_connector_fulfillment`, `shopify_connector_product_export` | Lite closure + inventory/fulfillment satellites | `python tools/build_shopify_connector_bundle.py --edition full` |

Each meta-addon contains no models, controllers, views, data records, hooks,
scheduled actions, asset bundles, credentials, or Shopify behavior.  Its only
runtime effect is to declare the accepted edition modules as dependencies.

The direct modules remain the DEC-029 edition sets.  The generic webhook
foundation and domain-specific satellites are an explicit installation closure
for the near-real-time contract and remain independent modules; P20
consolidation is not performed.  The branch-introduced historical all-family
`shopify_connector_suite` tree is omitted from the candidate and has no
`__manifest__.py`, so Odoo Apps cannot discover it as a third application.

## Official requirements checked

The implementation was checked against these primary Odoo sources on
2026-08-30:

| Source | Relevant rule applied |
| --- | --- |
| [Apps upload](https://apps.odoo.com/apps/upload) | The public submission entry point says **Register your Git repository** and requires sign-in; it does not publish an arbitrary-ZIP upload contract. |
| [Apps Vendor Guidelines](https://apps.odoo.com/apps/vendor-guidelines) | The manifest's mandatory fields are `name`, `version`, `license`, and `depends`; optional fields include `summary`, `live_test_url`, `price`, `currency`, and `support`. A manifest error can unpublish all modules in the repository. |
| [Odoo Apps FAQ](https://apps.odoo.com/apps/faq) | Dependencies may be Odoo/Enterprise/Community/own/other-vendor modules; an unpublished shared base is allowed only when free. It documents icon, HTML description, cover/`images`, license, repository, and buyer ZIP guidance. |
| [Odoo 19 Module Manifests](https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html) (also [the maintained source](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/module.rst)) | `__manifest__.py` is a literal dictionary; `name` is required; `version` follows semantic-versioning guidance; dependencies load first; `application`, `installable`, `auto_install`, `license`, `data`, `demo`, and `images` are supported metadata fields. |
| [Odoo 19 Building a Module](https://www.odoo.com/documentation/19.0/developer/tutorials/backend.html) (also [the maintained source](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/tutorials/backend.rst)) | Each module is a directory within an addons/module directory, discovered through `--addons-path`, with a root `__manifest__.py` and Python `__init__.py`; this is Odoo module-tree evidence, not Apps Store ZIP acceptance. |
| [Odoo 19 Coding Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html) (also [the maintained source](https://raw.githubusercontent.com/odoo/documentation/19.0/content/contributing/development/coding_guidelines.rst)) | Module structure and static files remain inside the addon; external image URLs are not used. A meta-addon has no business code to invent. |
| [Odoo 19 Licenses](https://www.odoo.com/documentation/19.0/legal/licenses.html) | `LGPL-3` is declared, matching the existing connector family and the checked-in root license. |

The Apps pages do not show a last-updated date. The Vendor Guidelines currently
links its manifest-field reference to Odoo 18.0; no separate Odoo 19 Apps Store
vendor policy was found. The Odoo 19 backend references above are therefore
used only for addon structure and manifest semantics.

## Verified Apps Store submission contract

### Repository registration, module roots, and dependencies

- The public [Apps upload flow](https://apps.odoo.com/apps/upload) is a
  sign-in-gated **Git repository registration** flow. The [FAQ's private-repo
  guidance](https://apps.odoo.com/apps/faq) documents GitHub/GitLab/other-host
  authorization and SSH URL forms; it does not describe a free-form ZIP upload
  endpoint.
- The [Vendor Guidelines](https://apps.odoo.com/apps/vendor-guidelines) refer
  to scan errors and to “all the modules from your repository.” That is
  evidence that a registered repository can contain multiple independently
  discovered module roots. It does not define how a public download ZIP is
  assembled from those roots.
- The [Odoo 19 module tutorial](https://www.odoo.com/documentation/19.0/developer/tutorials/backend.html)
  establishes the addon-tree convention: each module is a directory in a
  module directory on `--addons-path`, with its own manifest and Python package
  initializer. The [buyer ZIP answer in the FAQ](https://apps.odoo.com/apps/faq)
  describes copying the module inside a ZIP into `addons`; the [Vendor
  Guidelines](https://apps.odoo.com/apps/vendor-guidelines) also says customers
  should not need extra procedures such as moving a folder or unzipping another
  one.
- The FAQ explicitly discusses dependencies supplied by Odoo, Enterprise,
  Community, the vendor, or another Apps vendor. It allows an unpublished
  shared base only when that base is free. Each candidate root therefore needs
  its complete declared dependency closure available to the target Odoo
  instance.

**Unresolved archive decision.** No official public source located on the
access date states that one Apps submission or one customer download ZIP may
contain multiple module roots, or that dependencies may be embedded as sibling
roots in that ZIP. The sibling-root archives built by this repository are
reproducible Odoo-addon evidence, not a verified Apps Store delivery contract;
owner/Odoo validation is required before treating them as marketplace
deliverables.

### Manifest, commercial, and publisher fields

The [Vendor Guidelines manifest section](https://apps.odoo.com/apps/vendor-guidelines)
is the authoritative Apps-specific checklist found on the access date:

| Status | Field | Verified requirement |
| --- | --- | --- |
| Mandatory | `name` | String, explicit, **no more than 25 characters** (`<=25`). |
| Mandatory | `version` | String; increment on schema/release changes and include the Odoo version with major/minor/bugfix-style numbering. |
| Mandatory | `license` | String compatible with dependencies, libraries, and derivative licenses. |
| Mandatory | `depends` | List containing all dependencies; nonexistent dependencies raise a repository-scan error. |
| Optional | `summary` | Short manifest summary. |
| Optional | `live_test_url` | Demo-instance URL where the module can be tested. No real URL is available in this evidence. |
| Optional | `price` | One-shot EUR/USD price; omitted or negative means free in the guideline. The guideline states a paid-app minimum of 9 EUR. |
| Optional | `currency` | EUR or USD; EUR is the default and another value raises a scan error. |
| Optional | `support` | Support/claims email shown to buyers; no verified address is available here. |

`publisher` is not listed as an Odoo 19 manifest field in the [Odoo 19
manifest reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html),
which instead documents `author`, `website`, and `maintainer`. The Apps
publisher/account identity and any mapping to these addon fields remain an
owner-side submission decision; no publisher value, website, support address,
or live-test URL is invented in this evidence.

### Listing presentation and screenshots

The [Apps FAQ](https://apps.odoo.com/apps/faq) and [Vendor
Guidelines](https://apps.odoo.com/apps/vendor-guidelines) document these
presentation expectations:

- use a real PNG at `static/description/icon.png` (renaming another extension
  does not make it a PNG);
- provide rich English HTML at `static/description/index.html`;
- use the manifest `images` list for module-relative cover/screenshot paths;
  FAQ examples use PNG/GIF/JPEG and describe a cover/thumbnail convention;
- provide accurate English description, thumbnail/cover, screenshots or
  previews, and purchase/download information; do not make unsupported claims
  or advertise other app stores/external platforms;
- the Vendor Guidelines scoring section lists a missing icon, missing cover
  image/thumbnail, missing manifest license, and non-HTML description as
  negative criteria.

**Lite empty-image decision.** No official source found on 2026-08-30 says
`images=[]` is a scanner failure, and no official source says an empty image
list is accepted as a complete listing. No scanner outcome can be claimed; the
empty list does not satisfy the documented presentation expectation for
screenshots and thumbnail/cover and leaves the missing-cover score criterion
unresolved. Keep Lite empty only as an explicitly disclosed evidence state;
obtain either a core/product/sale-only capture or explicit owner/Odoo
validation before calling it listing-ready. Full-only screenshots must not be
reused to imply Lite coverage.

### Documented validation sequence and limits

1. Sign in to Apps and register/authorize the repository through the public
   upload flow; do not treat a locally generated ZIP as an upload confirmation.
2. For every candidate module root, check the Odoo 19 module-tree convention,
   literal manifest, mandatory fields, declared dependency closure, version, and
   license; then resolve any Apps scan errors.
3. Supply only verified optional commercial/support/demo values and verify price
   parity if the app is paid.
4. Check the real PNG icon, HTML description, manifest `images`, English copy,
   cover/thumbnail, screenshots, previews, and accurate claims against the
   listing guidance.
5. Retain the authenticated scan/listing result and review outcome. Public
   sources do not document the authenticated buttons, a local preflight tool, a
   multi-root ZIP schema, or an acceptance SLA. The documented unpublish/sanction
   language is enforcement policy, not proof that a candidate has passed review.

## Presentation and screenshot provenance

Full's six screenshots are exact byte-for-byte copies of existing rendered
browser evidence:

| Bundle path | Source evidence path |
| --- | --- |
| `shopify_connector_full/images/dashboard_screenshot.png` | `docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/u0-dashboard-healthy-desktop-1366px.png` |
| `shopify_connector_full/images/settings_screenshot.png` | `docs/05-qa/evidence/u1-browser-2026-07-25/09-admin-settings-form.png` |
| `shopify_connector_full/images/order_review_screenshot.png` | `docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/u2-orders-workspace-empty-desktop-1366px.png` |
| `shopify_connector_full/images/inventory_screenshot.png` | `docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/u2-inventory-workspace-desktop-1366px.png` |
| `shopify_connector_full/images/fulfillment_screenshot.png` | `docs/05-qa/evidence/u1-browser-2026-07-25/04-user-fulfillments.png` |
| `shopify_connector_full/images/jobs_screenshot.png` | `docs/05-qa/evidence/u1-browser-2026-07-25/05-user-fulfillment-jobs.png` |

Lite deliberately publishes no screenshots in this candidate: the available
captures expose Full-only navigation or surfaces.  Its description does not
name or claim the unavailable domains.  Both descriptions disclose that the
repository evidence uses synthetic fixtures and is not live Shopify or
Odoo.sh/UAT acceptance evidence.

## License and reproducibility

`LICENSE` is the verbatim GNU Lesser General Public License version 3 text,
dated 29 June 2007.  The deterministic builder validates its SHA-256 as
`e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118` and places
the file at the root of every edition archive.  Full provenance is recorded in
[`odoo-apps-packaging-provenance-2026-08-30.md`](odoo-apps-packaging-provenance-2026-08-30.md).

`tools/build_shopify_connector_bundle.py` validates literal manifests,
dependency closure, PNG headers, screenshot provenance, and secret markers. It
uses sorted paths, fixed ZIP timestamps, fixed file modes, and fixed DEFLATE
settings. Python test modules, docs, caches, credentials, nested archive
suffixes, and inert P16/V2 source trees are excluded. Manifest-declared
`static/tests` unit assets are retained, as are `web.assets_tests` browser
tours; Odoo loads the latter only in test/debug mode. Symlinked addon roots,
license/screenshot inputs, and all other package sources fail closed.

## Offline validation

```bash
python tools/build_shopify_connector_bundle.py --all-editions --check
python tools/build_shopify_connector_bundle.py --all-editions --dry-run
python -m unittest \
  tools.tests.test_shopify_connector_packaging \
  tools.tests.test_shopify_connector_packaging_audit \
  tools.tests.test_connector_suite_meta_install_contract -v
bash -n tools/run_connector_suite.sh
tools/run_connector_suite.sh --self-test
```

Archive file counts and output SHA-256 values are intentionally **pending exact
frozen regeneration**.  The shared worktree is still changing, so the release
owner must rebuild both editions from one clean, frozen SHA before recording
final counts or hashes.  The current focused packaging/audit suite reports 24
tests passing (the separate CI meta-install contract adds 3); rerun both on
the frozen SHA.  Odoo
PostgreSQL install, upgrade, uninstall/reinstall, and browser execution remain
CI/Odoo.sh evidence rather than an offline claim.

## CI migration compatibility

The connector CI runner installs Lite and Full on separate disposable
candidate databases and verifies every direct and webhook-closure module
reaches `installed`.
The version-to-version migration loop uses the explicit legacy
`MIGRATION_MODULES="$MODULES"` set for both old-tree installation and candidate
upgrade.  It never asks historical refs to contain the newly introduced meta
addons.

## Remaining external submission gates

1. Freeze a clean release SHA with no unrelated modified or untracked
   production files, then rebuild both archives and rerun the lifecycle matrix.
2. Complete the Odoo Apps publisher fields using verified owner-provided
   website/support/live-test details. No URL, address, price, or publisher
   claim is invented here.
3. Confirm Odoo's acceptance of the multi-addon archive convention and retain
   the uploaded archive hashes, review result, and any requested changes.

This evidence does not claim pricing, billing, entitlement, OAuth, Shopify App
Store distribution, payouts, refunds, returns, or unlimited scale.
