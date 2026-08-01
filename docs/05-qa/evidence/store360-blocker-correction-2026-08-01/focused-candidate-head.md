# Focused touched-class run — candidate head (fix applied)

Command (from .odoo-src, pinned odoo/odoo@30bde9ff, PostgreSQL 16, Python 3.12,
ODOO_BROWSER_BIN set for the HttpCase HTTP layer):

```
odoo-bin -d blocker_focus -i shopify_connector_core,shopify_connector_product,\
  shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment,\
  shopify_connector_product_export,account,stock --stop-after-init --test-enable \
  --test-tags ':TestSaleOrderProjection,:TestSaleOrderProjectionRpc,\
  :TestOrderReconnectCatchup,:TestStore360Aggregates,:TestStore360Security,\
  :TestFulfillmentReconnectCatchup,:TestOrderImportMapping'
```

Result line:

```
blocker_focus odoo.tests.result: 0 failed, 0 error(s) of 63 tests when loading database 'blocker_focus' 
```

Exit code 0. The SQL-level "duplicate key" lines in the raw log are the
deterministic-resume tests exercising the idempotency collision inside a
savepoint (caught as IntegrityError) — benign, and reflected by the 0-error total.
