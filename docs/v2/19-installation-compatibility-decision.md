# Installation compatibility decision — proposed, not accepted

The existing W2-only gate remains required and failing. This proposal does not change its runner, origin, acceptance criteria or reported result.

## Finding

`tools/run_connector_suite.sh` installs the old W1 bundle at `7443250ae42a0c3fadba9bf0ef9991e1826b77b5`, switches every addon to current source, then installs only `shopify_connector_product_webhook`. It requires W1 to retain installed version `19.0.1.0.0` and verifies no migration ran. The original native campaign at `695aa801` recorded ten errors of eighteen tests in this lane.

Current owner modules now define additional activation, configuration, job/run/attempt and command-result schema. Replacing their Python code without upgrading their installed schema leaves an inconsistent registry. The W2 pre-init hook already bridges more than the original two W1 JSONB columns, including settings, order, inventory and export fields. Expanding it to recreate the current core runtime would duplicate owner migrations without their complete backfills, security/XML updates or version bookkeeping. Merely adding each next missing column is not an adequate repair.

The exact seven-module fixture spans these owner versions (verified from both manifests at the durable origin and current source `96f3eda8`):

| Owner addon suffix | Installed old version | Current source version |
| --- | --- | --- |
| core | 19.0.1.23.0 | 19.0.1.33.0 |
| product | 19.0.2.11.0 | 19.0.2.14.0 |
| sale | 19.0.2.11.0 | 19.0.2.17.0 |
| inventory | 19.0.1.8.0 | 19.0.1.13.0 |
| fulfillment | 19.0.1.6.0 | 19.0.1.11.0 |
| product_export | 19.0.1.2.0 | 19.0.1.7.1 |
| webhook | 19.0.1.0.0 | 19.0.1.4.0 |

This is a source/fixture inventory, not proof that any upgrade chain has passed. The proposed lane must exercise these actual owner upgrades and assert their installed versions and preserved data.

## Recommended decision

Require a normal, versioned upgrade of the installed connector owner modules before adding W2 to an old installation. Preserve existing identities, bindings, audit history and uncertain mutation records through those owner migrations. Keep the durable old origin as an upgrade fixture; do not replace it with a convenient recent baseline.

This changes the promise that W2 can install over unchanged old owner versions after all owner source has been replaced. It therefore requires the user's approval. Customer installation footprint remains unknown; lack of that information is not permission to discard compatibility or data.

| Option | Consequence | Qualification |
| --- | --- | --- |
| Owner upgrades, then W2 — recommended | One maintained current implementation; explicit supported upgrade prerequisite. | Separately named owner-upgrade/W2-install lane from the original old origin, migration/version and data-preservation evidence, repeat-update checks, clear preflight and backup/restore instructions. This is not a pass of the current W2-only lane. |
| Maintain a legacy-compatible W2 bundle | Keep compatible old owner code with a separately supported W2 implementation; ongoing packaging and security maintenance. | Test that actual split bundle against its declared owner versions, plus current bundle qualification. The present all-current-source fixture does not prove this option. |
| Rebuild current owner schema in W2 pre-init | An unversioned partial owner upgrade with duplicated migration responsibilities. | Rejected as an architectural workaround; column existence cannot establish complete owner migration correctness. |

## Work after approval of the recommendation

1. Inventory installed owner versions and their migration chains from the durable old fixture; derive the necessary upgrade list from actual installed owners, including optional packages.
2. Implement a safe installation preflight that identifies required owner upgrades without reading absent future schema or changing data. Give a precise operator recovery instruction.
3. Qualify backup, owning upgrades and W2 installation on a disposable copy. Assert module versions, migration execution, bindings/history preservation, activation intent, company isolation and uncertain-write recovery; repeat the update to prove idempotence.
4. Replace only the superseded mixed-version promise through an explicit contract/runner change, retain historical failure evidence and name the new lane honestly. Review the existing additive bridge for removal or a smaller declared compatibility range using migration evidence.
5. Document the supported package/upgrade combinations and rollback by restoration of the matching database and source, before merchant use.

No changes in this document authorize a live customer upgrade or waive native, migration, concurrency, usability or release gates. Independent backend corrections continue while the decision is pending.
