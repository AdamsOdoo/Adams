====================================
Shopify Connector Pro - Troubleshooting
====================================

Connection Issues
=================

**"Connection failed" on Test Connection**

- Verify the Shop URL is exactly ``your-store.myshopify.com``
  (no ``https://``, no trailing path).
- Verify the access token starts with ``shpat_`` and has the
  required API scopes.
- Check that your Odoo server can reach ``your-store.myshopify.com``
  on port 443 (outbound HTTPS).

**"Access token should start with 'shpat_'"**

- You may have copied the API secret key instead of the access token.
  Go to your Shopify Custom App > **API credentials** and copy the
  **Admin API access token** (revealed once at install).


Webhook Issues
==============

**Webhooks not arriving**

- Your Odoo instance must be reachable over HTTPS with a valid
  (non-self-signed) certificate.
- Check that the webhook callback URL is correct:
  ``https://your-odoo.com/shopify/webhook/<backend_id>``
- Use **Check Webhook Status** button on the backend to see
  registered topics.
- Shopify retries failed deliveries for up to 48 hours.

**"HMAC verification failed" in webhook logs**

- The **Webhook Secret** on the backend must exactly match the
  secret configured in Shopify.
- If you regenerated the secret on Shopify, update it on the
  Odoo backend and re-register webhooks.

**Webhooks stuck in "pending" state**

- The ``Shopify: Process Pending Webhooks`` cron must be active
  (runs every 1 minute by default).
- Check if the cron is paused or errored in
  **Settings > Technical > Automation > Scheduled Actions**.

**Dead-letter webhooks**

- After 5 retry failures, webhooks move to "dead letter" state.
- Review the error message and payload in
  **Shopify > Webhook Logs > Dead Letter**.
- Fix the underlying issue, then retry manually.


Sync Errors
===========

**"Expected singleton" error**

- This was fixed in version 9bc6ec4.  Update your module to the
  latest version.

**Orders imported but no invoice created**

- Check that **Auto-create Invoice** is enabled on the backend.
- Verify the product has an **income account** set (product category
  > Accounting tab > Income Account).
- Check the sync log and order activities for specific error messages.

**Products not syncing**

- Verify **Sync Products** is enabled with the correct direction.
- For export: products need a ``shopify.product.binding`` record.
  Use the **Bulk Export Wizard** to create bindings.
- For import: check that the ``Shopify: Sync Products`` cron is
  active and the backend is in **Connected** state.

**Inventory quantities wrong on Shopify**

- Check the **Quantity Type** setting: ``Free Qty`` excludes reserved
  stock, ``On Hand`` includes everything.
- Verify the correct warehouse is selected on the backend.
- For multi-location, ensure **Shopify locations** are mapped to
  Odoo warehouses (Shopify > Configuration > Locations).

**Customer duplicates**

- Review the **Customer Dedup By** setting.  ``Email + Phone`` is the
  most aggressive dedup strategy.
- Existing duplicates can be merged using Odoo's standard partner
  merge wizard.

**Currency mismatch on imported orders**

- If using Shopify Markets, set **Order Currency Mode** to
  ``Customer Currency``.
- Ensure the required currencies are active in Odoo.
- Check the sync log for "Currency XXX not found" warnings.


Performance Issues
==================

**Sync running slowly**

- Increase the **Batch Size** (default 50, max 250).  Larger
  batches reduce API round-trips.
- Check the Shopify API rate limiter metrics: a high
  ``throttle_count`` means you're hitting Shopify's limits.
- Reduce the number of enabled sync entities if you don't need
  all of them.

**"API rate limit exceeded" errors**

- The connector includes an adaptive rate limiter that automatically
  backs off.  Transient 429 errors are normal and retried.
- If persistent, check if other apps are also consuming your
  Shopify API budget.

**Database growing too large**

- Webhook logs are auto-purged after 90 days (configurable).
- Sync logs accumulate but are lightweight.  Archive old logs
  periodically if needed.


Infinite Sync Loop Prevention
=============================

The connector uses the ``shopify_no_auto_export`` context flag to
prevent infinite loops.  If you see orders/invoices being duplicated:

1. Ensure you're running the latest version with loop-prevention
   patches.
2. Check that custom code overriding ``action_post``,
   ``button_validate``, or ``_action_done`` properly checks for
   ``self.env.context.get('shopify_no_auto_export')``.
3. Review the sync log for rapid repeated entries on the same record.


Reconciliation
==============

The reconciliation cron runs every 6 hours and checks for:

- **Payment mismatches**: order paid on Shopify but no posted invoice
  in Odoo.
- **Fulfillment mismatches**: order fulfilled on Shopify but delivery
  still pending in Odoo.
- **Stale bindings**: bindings stuck in error state for > 7 days.

Results are logged to the sync log and visible on the backend
dashboard (Payment Mismatches / Fulfillment Mismatches counts).


Getting Help
============

1. Check the **Sync Logs** (Shopify > Sync Logs) for detailed error
   messages.
2. Check the **Webhook Logs** for webhook-specific issues.
3. Enable Odoo debug mode and check the server log for
   ``shopify_connector_pro`` log entries.
4. Contact support at support@shopifyconnectorpro.com with:

   - Odoo version and module version
   - Backend configuration (screenshot)
   - Relevant sync log entries
   - Server log excerpt
