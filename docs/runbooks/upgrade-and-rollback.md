# Upgrade and rollback runbook

## Upgrade

1. Back up the database and filestore; record the current connector addon versions and commit SHA.
2. Quiesce new connector work by disconnecting each store through the supported lifecycle. Resolve or preserve every uncertain mutation; never reinterpret it as success.
3. Deploy one immutable commit and confirm it matches the intended CI/Odoo.sh SHA.
4. Upgrade all installed connector addons together. For this corrective candidate the versions are core `19.0.1.28.0`, product `19.0.2.14.0`, sale `19.0.2.15.0`, inventory `19.0.1.12.0`, fulfillment `19.0.1.10.0`, product export `19.0.1.6.0`, webhook `19.0.1.3.0`, product webhook `19.0.0.3.0`, inventory webhook `19.0.0.4.0`, sale webhook `19.0.0.1.0`, and fulfillment webhook `19.0.0.1.0`.
5. Verify migrations completed, indexes exist, assets load, and no connector cron is failing.
6. Run the migration a second time in the qualification database to prove idempotency.
7. Reconnect one store, run readiness, complete catch-up, then expand within the supported ten-store boundary.

The additive cursor migrations initialize only new scan state; they do not move existing public checkpoints, modify credentials, discard jobs, change bindings, reset setup progress, or resolve mutation attempts.

## Rollback

Code-only rollback is unsafe after a schema/version upgrade. Stop connector work, preserve the failing database for evidence, and restore the pre-upgrade database plus filestore backup together with the exact pre-upgrade source commit. Restore no credential from logs or reports. Revoke/rotate merchant credentials if exposure is suspected. Run identity/readiness checks before reconnecting.

If Shopify may have changed during the failed upgrade, reconcile from fresh remote reads before any mutation. Never replay an uncertain request.
