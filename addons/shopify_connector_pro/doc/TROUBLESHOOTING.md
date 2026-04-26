# Troubleshooting Cookbook

Quick-reference for common problems and their solutions.

---

## Connection Issues

### "Connection failed: 401 Unauthorized"

**Cause:** Invalid or expired access token.

**Fix:**
1. Open your Shopify admin → Settings → Apps and sales channels → your custom app.
2. Go to **API credentials** tab.
3. Click **Reveal token once** (or reinstall the app to regenerate).
4. Copy the `shpat_…` token and paste it in Odoo backend → Access Token.
5. Click **Test Connection**.

### "Shop URL must be a valid myshopify.com domain"

**Cause:** The shop URL field contains a full URL or invalid characters.

**Fix:** Enter only `my-store.myshopify.com` — no `https://`, no trailing `/admin`, no path.

### "Connection failed: 403 Forbidden"

**Cause:** Missing API scopes on the Shopify custom app.

**Fix:**
1. Shopify admin → Settings → Apps → your app → Configuration → Admin API access scopes.
2. Ensure all required scopes are checked (see STEP_BY_STEP_GUIDE.md, Step 2).
3. Click **Save** and **Install app** again.

---

## Sync Errors

### Product sync: "PRODUCT_SET_MUTATION userErrors"

**Common sub-errors:**

| Error message | Cause | Fix |
|---|---|---|
| `Title can't be blank` | Product has no name in Odoo | Fill in the product name |
| `Handle has already been taken` | Duplicate URL slug | Edit the product handle or delete the conflicting Shopify product |
| `Option name can't be blank` | Variant attributes not set | Ensure product variants have attribute values |
| `Inventory item not found` | Stale inventory item ID | Re-export the product (reset binding, re-sync) |

### Order import: "Could not resolve customer for order #XXXX"

**Cause:** The Shopify order's customer has no email and no phone, and no existing binding.

**Fix:**
1. Open the Shopify order in Shopify admin.
2. Add a customer email.
3. Re-trigger the import (or wait for next cron run).

### Inventory push: "compareQuantity doesn't match"

**Cause:** Someone manually edited inventory in Shopify, so our `compareQuantity` is stale.

**Fix:** This auto-resolves on the next cron pass — the connector will re-read and retry. If persistent:
1. Go to the variant binding → set `last_pushed_qty` to match Shopify's current value.
2. Or wait for two cron cycles.

### "Webhook rate limit exceeded for backend X"

**Cause:** More than 200 webhooks received per minute from this store.

**Fix:** This is a safety limit. If legitimate (high-volume store):
1. Increase `WEBHOOK_RATE_LIMIT` in `controllers/webhook.py`.
2. Default: 200/min is sufficient for most stores.
3. Also check if Shopify is replaying old webhooks (retry storm).

### "HMAC verification failed"

**Cause:** Webhook secret mismatch between Odoo and Shopify.

**Fix:**
1. In Odoo, check the backend's **Webhook Secret** field.
2. It must match the secret shown in Shopify admin → Notifications → Webhooks.
3. If mismatched, update the Odoo field and click **Register Webhooks** again.

### "Webhook X moved to dead letter after 5 retries"

**Cause:** Persistent error processing a webhook event.

**Fix:**
1. Go to **Shopify → Logs → Webhook Log**.
2. Filter by **Dead Letter** state.
3. Open the record and read the `error_message`.
4. Fix the root cause (missing product, permissions, etc.).
5. Click **Retry** to re-process.

---

## Invoice Creation Failures

### "account_move_line_check_accountable_required_fields" constraint violation

**Cause:** This is the **most common invoice creation error**. It means the database rejected an invoice line because `account_id` is NULL. This happens when:

1. The **product has no income account** — neither on the product template (`property_account_income_id`) nor on its category (`property_account_income_categ_id`)
2. The **partner has no receivable account** — `property_account_receivable_id` is not set
3. **No sales journal** exists for the company

**Fix:**

1. **Set income account on the product category** (recommended — fixes all products in that category):
   - Go to **Inventory > Configuration > Product Categories**
   - Open the relevant category
   - Set **Income Account** in the Account Properties section (e.g., "Product Sales" or "200000 Revenue")

2. **Set receivable account on the partner** (usually automatic from chart of accounts):
   - Go to **Contacts** > open the customer
   - **Accounting** tab > verify **Account Receivable** is set
   - If blank, set it to your default receivable account (e.g., "121000 Account Receivable")

3. **Create a sales journal** if missing:
   - **Accounting > Configuration > Journals > New**
   - Type: Sale, Code: SHOP, Name: "Shopify Sales"

**Symptoms in logs:**
```
psycopg2.errors.CheckViolation: new row for relation "account_move_line"
violates check constraint "account_move_line_check_accountable_required_fields"
```

**Note:** This error may appear in logs even when the connector appears to work, because the connector uses savepoints to catch the failure and skip invoice creation gracefully. Check your sync logs for "Auto-invoice skipped" warnings.

### "Auto-invoice skipped: no income account for product(s)"

**Cause:** The connector proactively detected that your product(s) have no income account and skipped invoice creation to avoid the constraint violation above.

**Fix:** Same as above — set the income account on the product or product category.

### Invoice created but not posted

**Cause:** The invoice was created in `draft` state but `action_post()` failed. Common reasons:
- Missing tax configuration
- Currency mismatch
- Fiscal position mapping issue

**Fix:** Open the draft invoice, review the error in the chatter, and fix the underlying issue before posting manually.

---

## Fulfillment Issues

### Delivery validated in Odoo but not pushed to Shopify

**Checklist:**
1. Is the order's `sales_channel` set to `shopify`? (B2B orders are excluded.)
2. Does the order binding have a `shopify_id`?
3. Is the backend in `connected` state?
4. Check the sync log for errors.
5. Does the Shopify order have an open fulfillment order? (Required by Shopify 2026-01.)

### "fulfillmentCreate userErrors: Fulfillment order not found"

**Cause:** Shopify requires `fulfillmentOrderId` in 2026-01. The connector needs the fulfillment order GID.

**Fix:** Ensure the order was imported with its fulfillment order data. Re-import the order if needed.

---

## Financial Issues

### Invoice posted but Shopify order not marked as paid

**Checklist:**
1. Is **Reverse Sync: Payment** enabled on the backend?
2. Is the order's current Shopify financial status `pending` or `authorized`?
3. Is the backend connected?
4. Check the Odoo server log for `Failed to mark Shopify order`.

### Credit note posted but no Shopify refund created

**Checklist:**
1. Is **Reverse Sync: Refund** enabled on the backend?
2. Is the credit note linked to a Shopify order (via `reversed_entry_id` or sale lines)?
3. Check logs for `Failed to create Shopify refund`.

---

## Performance Issues

### Sync is slow (taking > 5 minutes for 100 records)

**Tune these settings:**
1. Increase `batch_size` (default 50, max 250).
2. Check Shopify API rate limit usage in Shopify admin → Settings → Apps → your app.
3. Ensure PostgreSQL has adequate `work_mem` and `shared_buffers`.
4. Stagger cron intervals — don't run all syncs simultaneously.

### Dashboard loads slowly

**Cause:** `_compute_bind_counts` runs grouped queries. With many backends, this can be slow.

**Fix:**
1. Ensure `backend_id` and `sync_status` are indexed (they are by default).
2. If you have > 100K bindings, consider running `VACUUM ANALYZE` on binding tables.

---

## GDPR Webhooks

### "GDPR data request received for customer X"

**What happened:** A Shopify customer requested their data. You must fulfill this manually.

**Action:**
1. Check the backend's chatter — an activity was created.
2. Use Odoo's privacy tools to export the customer's data.
3. Provide it through Shopify admin.

### "GDPR customer redact for X"

**What happened:** The connector automatically anonymized the customer's data.

**What was done:** Name → "Redacted Customer #N", email/phone/address → cleared.

**Note:** Accounting data (invoices, orders) is preserved per legal requirements.

---

## Common Shopify API Error Codes

| HTTP Status | Meaning | Action |
|---|---|---|
| 401 | Unauthorized | Check access token |
| 402 | Payment required | Store is frozen — contact shop owner |
| 403 | Forbidden | Missing API scopes |
| 404 | Not found | Resource was deleted on Shopify |
| 423 | Locked | Shop is locked — contact Shopify support |
| 429 | Throttled | Rate limit hit — connector auto-retries with backoff |
| 500 | Internal Server Error | Shopify issue — auto-retries |
| 503 | Service Unavailable | Shopify maintenance — auto-retries |

---

## Health Check Endpoint

Monitor your connector programmatically:

```
GET /shopify/health/<backend_id>
```

Returns JSON:
```json
{
  "status": "ok",
  "shop_name": "My Store",
  "last_sync": "2026-04-15 10:30:00",
  "sync_health_pct": 98,
  "counts": {
    "products": 1250,
    "customers": 3400,
    "orders": 8900,
    "errors": 12,
    "pending": 3
  },
  "webhooks": {
    "pending": 0,
    "dead_letters": 2
  }
}
```

HTTP 200 = connected, HTTP 503 = connection error.

---

## Getting More Help

1. **Odoo server log:** Filter by `shopify_connector_pro` (technical module name) to see all connector activity.
2. **Sync Log:** Shopify → Logs → Sync Log — every batch operation is logged.
3. **Webhook Log:** Shopify → Logs → Webhook Log — every incoming event with payload.
4. **Shopify API log:** Shopify admin → Settings → Apps → your app → API request logs.
