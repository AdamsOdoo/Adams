"""SEC-2: rename the retention setting to what it still governs.

`pii_snapshot_retention_days` drove two different things: business-record
masking of customer snapshots (removed by SEC-2, packet section D option 1)
and log/audit `payload_snapshot` redaction (retained, control-room decision
TA-C5). With masking gone the setting governs redaction only, so it is
renamed rather than retired-and-recreated -- renaming preserves each store's
configured window, which recreating would silently reset to zero (i.e. "never
redact").

Runs pre-migration so the ORM finds the column already renamed and does not
create an empty `log_redaction_retention_days` alongside it. Idempotent: a
second run finds the source column gone and does nothing.
"""


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'shopify_connector_store_settings'
           AND column_name = 'pii_snapshot_retention_days'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'shopify_connector_store_settings'
           AND column_name = 'log_redaction_retention_days'
        """
    )
    if cr.fetchone():
        # Both columns present: a partially applied run. Carry any configured
        # window across, then drop the retired column.
        cr.execute(
            """
            UPDATE shopify_connector_store_settings
               SET log_redaction_retention_days = pii_snapshot_retention_days
             WHERE COALESCE(log_redaction_retention_days, 0) = 0
               AND COALESCE(pii_snapshot_retention_days, 0) <> 0
            """
        )
        cr.execute(
            """
            ALTER TABLE shopify_connector_store_settings
              DROP COLUMN pii_snapshot_retention_days
            """
        )
        return
    cr.execute(
        """
        ALTER TABLE shopify_connector_store_settings
          RENAME COLUMN pii_snapshot_retention_days
                     TO log_redaction_retention_days
        """
    )
