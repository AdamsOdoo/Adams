# Upgrade and rollback runbook

## Upgrade

1. Back up the database and filestore; record the current connector addon versions and commit SHA.
2. Quiesce new connector work by disconnecting each store through the supported lifecycle. Resolve or preserve every uncertain mutation; never reinterpret it as success.
3. Deploy one immutable commit and confirm it matches the intended CI/Odoo.sh SHA.
4. Upgrade all installed connector addons together. For this V2 candidate the versions are core `19.0.1.33.0`, product `19.0.2.14.0`, sale `19.0.2.17.0`, inventory `19.0.1.13.0`, fulfillment `19.0.1.11.0`, product export `19.0.1.7.1`, webhook `19.0.1.4.0`, product webhook `19.0.0.3.0`, inventory webhook `19.0.0.5.0`, sale webhook `19.0.0.1.0`, and fulfillment webhook `19.0.0.1.1`.
5. Verify migrations completed, indexes exist, assets load, and no connector cron is failing.
6. Run the migration a second time in the qualification database to prove idempotency.
7. Reconnect one store, run readiness, complete catch-up, then expand within the supported ten-store boundary.

Core migration mapping for this candidate:

- `19.0.1.32.0` backfills the additive store activation state and creates
  the durable named-command result scope index.
- `19.0.1.33.0` preserves the later concurrent runtime migration: it links
  existing mutation-attempt rows to their already-associated runs and copies
  the stored configuration generation, then creates its scoped query index.

Run both hooks through the normal Odoo upgrade path; do not apply either SQL
snippet manually or skip `19.0.1.33.0` when upgrading from `19.0.1.32.0`.

The additive cursor migrations initialize only new scan state; they do not move existing public checkpoints, modify credentials, discard jobs, change bindings, reset setup progress, or resolve mutation attempts.

## Rollback

Code-only rollback is unsafe after a schema/version upgrade. Stop connector work, preserve the failing database for evidence, and restore the pre-upgrade database plus filestore backup together with the exact pre-upgrade source commit. Restore no credential from logs or reports. Revoke/rotate merchant credentials if exposure is suspected. Run identity/readiness checks before reconnecting.

If Shopify may have changed during the failed upgrade, reconcile from fresh remote reads before any mutation. Never replay an uncertain request.
