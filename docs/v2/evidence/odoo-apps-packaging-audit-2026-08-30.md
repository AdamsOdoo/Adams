# Odoo Apps release-packaging audit — 2026-08-30 remedy update

## Verdict

The packaging remedies in this slice are complete for the bounded offline
contract: the unused `graphql` manifest declaration is removed, the accepted
DEC-029 Lite/Full edition boundaries are explicit, both deterministic archive
outputs carry the complete LGPL-3 text, and CI has a candidate-only meta-install
pass.  The branch-introduced historical `shopify_connector_suite` tree has no
manifest and cannot be discovered as a third Odoo Apps application. Odoo Apps
submission is still gated on a clean release checkout, actual Odoo 19
lifecycle execution, repository registration through the Apps publisher flow,
and verified owner-provided publisher/support details. The public Apps source
does not document acceptance of a single multi-root download ZIP; the archive
shape below is therefore offline Odoo-addon evidence, not marketplace
acceptance.

This record does not claim pricing, billing, entitlement, website, support, or
live-store availability.  The exact evidence/provenance map is in
[`odoo-apps-packaging-provenance-2026-08-30.md`](odoo-apps-packaging-provenance-2026-08-30.md).
The official-source findings and direct URLs are consolidated in
[`odoo-apps-packaging-2026-08-30.md`](odoo-apps-packaging-2026-08-30.md), with
access date 2026-08-30.

## DEC-029 outputs

| Edition | Meta-addon | Direct DEC-029 modules | Explicit webhook closure | Output |
| --- | --- | --- | --- | --- |
| Lite | `shopify_connector_lite` | `shopify_connector_core`, `shopify_connector_product`, `shopify_connector_sale` | `shopify_connector_webhook`, `shopify_connector_product_webhook`, `shopify_connector_sale_webhook` | `shopify_connector_lite-19.0.1.0.0.zip` |
| Full | `shopify_connector_full` | Lite plus `shopify_connector_inventory`, `shopify_connector_fulfillment`, `shopify_connector_product_export` | Lite closure plus `shopify_connector_inventory_webhook`, `shopify_connector_fulfillment_webhook` | `shopify_connector_full-19.0.1.0.0.zip` |

The six direct modules are the accepted DEC-029 edition sets.  The webhook
foundation and satellites are an explicit installation closure required by the
current near-real-time contract; they remain independently installable
engineering addons and are not consolidated under P20.  The branch-introduced
historical `shopify_connector_suite` tree has no manifest and is not emitted by
the builder.

## Checks that pass locally

| Area | Result | Evidence |
| --- | --- | --- |
| Odoo 19 metadata | Pass, static | Edition and companion manifests are literal dictionaries with `19.0.*` versions, `LGPL-3`, `installable=True`, and `auto_install=False`. |
| DEC-029 dependency sets | Pass, static | Lite is core/product/sale; Full is Lite plus inventory/fulfillment/product_export. Each edition explicitly closes over the generic webhook foundation and the required product/order (Lite) or inventory/fulfillment (Full) satellites, with no P20 consolidation. |
| Stale Python dependency | Pass | No production `import graphql` or `from graphql` exists; `shopify_connector_core/__manifest__.py` no longer declares `external_dependencies`. The CI GraphQL schema validator dependency remains a tool-only install. |
| Manifest file references | Pass, static | Every `data`, `demo`, `images`, and asset path named by each edition module exists. |
| App presentation | Pass, static | Both descriptions disclose synthetic fixtures and the Odoo.sh/UAT boundary; neither claims OAuth or real-time guarantees and neither supplies invented publisher URLs. |
| License/provenance | Pass, deterministic | Root `LICENSE` is verbatim LGPL-3 with SHA-256 `e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118`; every archive includes it at its root. |
| Archive hygiene | Pass, deterministic | Python tests/docs/caches/credentials, nested archives, and inert P16/V2 sources are absent; declared static unit assets and test-mode browser tours are retained; symlinked addon roots/license/screenshots/sources fail closed. |
| CI migration compatibility | Pass, static wiring | Candidate meta-install verifies the full direct-plus-webhook closure in a separate pass; the migration module set is explicitly `MIGRATION_MODULES="$MODULES"`, so install/upgrade commands never require the new meta-addon paths in old refs. |

## Commands and expected evidence

```text
python tools/build_shopify_connector_bundle.py --all-editions --check
  OK: lite: <N> distribution files validated
  OK: full: <N> distribution files validated

python -m unittest \
  tools.tests.test_shopify_connector_packaging \
  tools.tests.test_shopify_connector_packaging_audit -v
  all tests OK

python -m unittest tools.tests.test_connector_suite_meta_install_contract -v
  all tests OK

bash -n tools/run_connector_suite.sh
tools/run_connector_suite.sh --self-test
  self-test: all fail-closed assertions hold
```

The builder also supports one output at a time with `--edition lite` or
`--edition full`; `--all-editions` writes both default archives to a sibling
`<repo>-dist/` directory outside the checkout.

Final archive file counts and output SHA-256 values remain **pending exact
frozen regeneration**.  Do not promote a worktree-local count or hash to
release evidence until the clean candidate SHA is frozen.
The full Odoo/PostgreSQL install and browser lanes are CI/Odoo.sh evidence and
were not represented as a local pass by this static slice.

## Remaining release blockers

| ID / severity | Finding | Required disposition |
| --- | --- | --- |
| PKG-03 / S2 | The shared worktree contains unrelated modified and untracked production files, so its current `HEAD` is not an exact candidate identity. | Freeze one clean release SHA, build both archives from that checkout, and rerun the required Odoo 19 fresh/warm/migration/uninstall lanes. |
| PKG-04 / S3 | No reviewed browser capture is limited to the Lite closure; Lite therefore has no listing screenshots and its manifest deliberately uses `images=[]`. Odoo Apps guidance expects screenshots/thumbnail metadata and scores a missing cover image negatively, but does not publicly document an empty-list scanner failure. | Keep Lite image-free until a core/product/sale/webhook-only capture is reviewed, or obtain explicit owner/Odoo validation that the listing is acceptable. Never reuse Full-only screens. |
| PKG-05 / S3 | No verified Adams website, support address, live-test URL, or Apps publisher identity is available in the repository. `publisher` is not a documented Odoo 19 manifest field; Apps-specific `support` and `live_test_url` are optional guideline fields. | Complete the repository registration and Apps publisher fields from verified owner-provided values. Add manifest `website`/`live_test_url` only when real values are supplied; do not invent publisher or `support` metadata. |
| PKG-06 / S2 until runtime evidence | Static dependency closure passes, but this slice cannot prove a clean Odoo 19 install, upgrade, uninstall/reinstall, repository scan, multi-root ZIP acceptance, or marketplace archive acceptance. | Run the CI candidate-only Lite/Full meta-install pass and the release lifecycle matrix on the frozen SHA; register the repository only with owner authorization; retain scan, review, logs, and database/version evidence. |
| PKG-07 / S2 until Odoo confirmation | The public Apps upload page documents Git repository registration, not an arbitrary ZIP endpoint. Odoo supports multiple module roots in an addons tree and the Vendor Guidelines refer to all modules in a repository, but no public source defines a single Apps submission/download ZIP containing sibling roots or embedded dependencies. | Ask the owner to exercise the authenticated Apps flow and, if needed, obtain Odoo confirmation before treating the sibling-root Lite/Full archives as marketplace deliverables. |

Legal provenance is now present in the archives.  The release owner still
needs to confirm any additional copyright/contributor notices required by the
final distribution and review the archive convention with Odoo Apps.

## Exact files changed in this remedy slice

- `LICENSE`
- `addons/shopify_connector_core/__manifest__.py` (remove stale `graphql` dependency)
- `addons/shopify_connector_suite/` branch-introduced historical tree (manifest and addon entry removed; no Odoo app candidate)
- `addons/shopify_connector_lite/__init__.py`
- `addons/shopify_connector_lite/__manifest__.py`
- `addons/shopify_connector_lite/README.md`
- `addons/shopify_connector_lite/static/description/index.html`
- `addons/shopify_connector_lite/static/description/icon.png`
- `addons/shopify_connector_full/__init__.py`
- `addons/shopify_connector_full/__manifest__.py`
- `addons/shopify_connector_full/README.md`
- `addons/shopify_connector_full/static/description/index.html`
- `addons/shopify_connector_full/images/*.png`
- `addons/shopify_connector_full/static/description/icon.png`
- `tools/build_shopify_connector_bundle.py`
- `tools/run_connector_suite.sh`
- `.github/workflows/connector-tests.yml`
- `tools/tests/test_shopify_connector_packaging.py`
- `tools/tests/test_shopify_connector_packaging_audit.py`
- `tools/tests/test_connector_suite_meta_install_contract.py`
- `docs/v2/evidence/odoo-apps-packaging-2026-08-30.md`
- `docs/v2/evidence/odoo-apps-packaging-audit-2026-08-30.md`
- `docs/v2/evidence/odoo-apps-packaging-provenance-2026-08-30.md`

No runtime/domain implementation files were changed.  No commit or push was
performed.
