# Common Failure Scenarios & Prevention

## Scenario 1: Duplicate Record Creation (Race Condition)

### Description
Scheduled sync and webhook fire simultaneously for the same Shopify product. Both processes check for an existing binding, find none, and both create a new Odoo product + binding.

### Impact
- Duplicate products in Odoo
- Broken binding integrity
- Incorrect inventory counts

### Prevention
```
1. DATABASE CONSTRAINT (primary defense):
   _sql_constraints = [
       ('unique_shopify_binding', 'UNIQUE(backend_id, shopify_id)',
        'A binding for this Shopify ID already exists on this backend.')
   ]

2. CATCH + RETRY (secondary defense):
   try:
       binding = self.env['shopify.product.binding'].create(vals)
   except IntegrityError:
       self.env.cr.rollback()
       binding = self.env['shopify.product.binding'].search([
           ('backend_id', '=', backend_id),
           ('shopify_id', '=', shopify_id),
       ], limit=1)
       # Proceed with update instead of create

3. ADVISORY LOCK (tertiary defense for critical sections):
   self.env.cr.execute(
       "SELECT pg_advisory_xact_lock(%s)",
       [hash((backend_id, shopify_id))]
   )
```

### Detection
- Testing Agent: `test_concurrent_product_create` — create binding in one thread, attempt duplicate in another
- Monitoring: Alert on IntegrityError frequency > threshold

---

## Scenario 2: Shopify API Rate Limiting (429 Errors)

### Description
Batch export sends too many requests, Shopify returns 429 (Too Many Requests). Without proper handling, the entire sync fails and partial state is left.

### Impact
- Failed sync operations
- Incomplete data in Shopify
- Wasted API quota

### Prevention
```
1. PRE-CHECK AVAILABLE BUDGET:
   Check throttleStatus.currentlyAvailable from the last response.
   If below threshold (e.g., < 100 cost units), sleep before next call.

2. LEAKY BUCKET RESPECT:
   Shopify restores 100 cost units/second.
   Max bucket: 2000 points (Plus: 4000).
   Track usage and pace requests accordingly.

3. EXPONENTIAL BACKOFF ON 429:
   delay = base_delay * (backoff_factor ** attempt)
   With jitter: delay += random.uniform(0, delay * 0.1)

4. PER-RECORD ERROR ISOLATION:
   If one product fails with 429, retry that product.
   Don't fail the entire batch.

5. BATCH SIZE TUNING:
   Start with batch_size=50.
   If 429s are frequent, reduce dynamically.
```

### Detection
- Sync log entries with `status=rate_limited`
- Alert if rate limit errors exceed 10% of batch size

---

## Scenario 3: Webhook Delivery Failure / Duplicate Delivery

### Description
Shopify retries webhook delivery if it doesn't receive 200 within 5 seconds. Processing takes too long, resulting in duplicate deliveries.

### Impact
- Duplicate processing of the same event
- Duplicate records if idempotency isn't enforced

### Prevention
```
1. RETURN 200 IMMEDIATELY:
   Webhook controller validates HMAC, enqueues job, returns 200.
   NEVER process the webhook synchronously.

2. DEDUP BY WEBHOOK ID:
   Store X-Shopify-Webhook-Id in shopify.webhook.log.
   Before processing, check if this ID was already processed.

3. IDEMPOTENT PROCESSING:
   Even without dedup, the import logic should be safe:
   - Find binding by shopify_id → update (not create)
   - Use checksums to skip no-op updates

4. WEBHOOK LOG MODEL:
   class ShopifyWebhookLog(models.Model):
       _name = 'shopify.webhook.log'
       webhook_id = fields.Char(index=True)  # X-Shopify-Webhook-Id
       topic = fields.Char()
       backend_id = fields.Many2one('shopify.backend')
       status = fields.Selection([
           ('received', 'Received'),
           ('processing', 'Processing'),
           ('done', 'Done'),
           ('error', 'Error'),
       ])
       received_at = fields.Datetime()
       processed_at = fields.Datetime()
       error_message = fields.Text()
```

### Detection
- Webhook log shows duplicate `webhook_id` entries
- Alert on `status=error` count per hour

---

## Scenario 4: Partial Batch Failure

### Description
Batch export of 50 products: products 1-30 succeed, product 31 fails (bad data), products 32-50 are never attempted because the batch aborted.

### Impact
- 20 products never synced
- User doesn't know which products failed
- Next sync re-attempts all 50 (redundant for 1-30)

### Prevention
```
1. INDIVIDUAL ERROR ISOLATION:
   for product in batch:
       try:
           self._export_single_product(product)
       except Exception as e:
           _logger.error("Failed to export product %s: %s", product.id, e)
           self._log_sync_error(product, e)
           continue  # Don't abort the batch

2. PER-RECORD STATUS TRACKING:
   Each binding has sync_status: pending, synced, error
   On failure, mark as 'error' with error message
   Dashboard shows error count per backend

3. RETRY FAILED ONLY:
   Next sync run: also include records with sync_status='error'
   After N failures, mark as 'permanent_error' and alert user

4. PROGRESS REPORTING:
   Log batch progress: "Exported 30/50 products (2 errors)"
   Store in shopify.sync.log with per-record details
```

### Detection
- Dashboard widget showing sync_status distribution
- Alert when error_count > threshold

---

## Scenario 5: Odoo Transaction Rollback After API Call

### Description
Product exported to Shopify (API call succeeds, product created in Shopify), but the Odoo transaction rolls back due to a subsequent error. The binding is lost, but the product exists in Shopify.

### Impact
- Orphaned product in Shopify (no binding in Odoo)
- Next sync creates a duplicate in Shopify

### Prevention
```
1. API CALL PATTERN:
   Option A (preferred): Use savepoint
   with self.env.cr.savepoint():
       binding.write({'shopify_id': shopify_id, 'sync_checksum': checksum})
   # Savepoint ensures binding is committed even if outer transaction continues

   Option B: Compensating transaction
   try:
       shopify_id = self._call_shopify(mutation, variables)
       binding.write({'shopify_id': shopify_id})
   except Exception:
       if shopify_id:
           self._call_shopify(delete_mutation, {'id': shopify_id})
       raise

2. ORPHAN DETECTION (cron job):
   Periodically query Shopify for all products.
   Compare with bindings.
   Flag any Shopify products without a binding as orphans.
   Present orphans to user for resolution.

3. DEFENSIVE CREATE:
   Before creating in Shopify, check if a product with same SKU/title exists.
   If found, link to existing instead of creating new.
```

### Detection
- Orphan detection cron job
- Binding count vs Shopify product count mismatch alert

---

## Scenario 6: Shopify API Version Deprecation

### Description
Module uses Shopify API version 2024-10. Shopify deprecates this version and returns errors for all calls.

### Impact
- All sync operations fail
- No data flow between systems

### Prevention
```
1. VERSION IN CONFIG:
   shopify.backend model has api_version field (default: '2024-10')
   Admin can update without code change

2. VERSION CHECK ON CONNECTION TEST:
   test_connection() method also checks if the API version is still supported
   Warns if version is within 3 months of deprecation

3. RESPONSE MONITORING:
   Check for X-Shopify-API-Deprecated-Reason header in responses
   Log warnings when present

4. GRACEFUL DEGRADATION:
   If API returns version error, mark backend as 'api_error'
   Send notification to admin
   Don't retry until version is updated
```

### Detection
- Connection test shows version warning
- Sync log shows API version errors

---

## Scenario 7: Multi-Company Data Leakage

### Description
User in Company A accesses Shopify bindings from Company B's backend due to missing record rules.

### Impact
- Data privacy violation
- Incorrect sync operations across companies

### Prevention
```
1. COMPANY FIELD ON BACKEND:
   company_id = fields.Many2one('res.company', required=True,
       default=lambda self: self.env.company)

2. RECORD RULES:
   <record model="ir.rule" id="shopify_backend_company_rule">
       <field name="name">Shopify Backend Company Rule</field>
       <field name="model_id" ref="model_shopify_backend"/>
       <field name="domain_force">[
           ('company_id', 'in', [company_id for company_id in user.company_ids.ids])
       ]</field>
   </record>

3. BINDING INHERITS COMPANY:
   Binding models inherit company_id from their backend_id
   Record rules on bindings filter by backend.company_id

4. TESTING:
   Test with 2 companies, 2 backends, verify isolation
```

### Detection
- Code Reviewer checks all models for company_id field + record rules
- Testing Agent writes multi-company isolation tests

---

## Scenario 8: Stale ORM Cache

### Description
Process A writes to a binding record. Process B (running concurrently) reads the same record but gets stale cached data because Odoo ORM caches aggressively within a transaction.

### Impact
- Decisions made on stale data
- Duplicate operations or missed updates

### Prevention
```
1. INVALIDATE BEFORE CRITICAL READS:
   self.env['shopify.product.binding'].invalidate_model()
   binding = self.env['shopify.product.binding'].search([...])

2. USE browse().exists() FOR EXISTENCE CHECKS:
   # This bypasses cache
   if not binding.exists():
       ...

3. USE fresh=True FOR COMPUTED FIELDS:
   # Re-compute instead of using cache
   binding.with_context(fresh=True).sync_checksum

4. AVOID LONG-RUNNING TRANSACTIONS:
   Process records in smaller batches
   Commit between batches if using ir.cron
```

### Detection
- Debugging Agent pattern: "record appears to not exist but does in database"
- Test with concurrent writes + reads

---

## Scenario 9: Invalid/Malformed Webhook Payload

### Description
Shopify sends a webhook with an unexpected payload format (missing fields, null values where objects expected, new fields added in newer API versions).

### Impact
- KeyError / TypeError in processing
- Webhook marked as failed, not retried properly

### Prevention
```
1. DEFENSIVE PARSING:
   def _parse_product_webhook(self, payload):
       return {
           'shopify_id': payload.get('admin_graphql_api_id', ''),
           'title': payload.get('title', ''),
           'body_html': payload.get('body_html') or '',
           'variants': payload.get('variants') or [],
           'status': payload.get('status', 'draft'),
       }

2. VALIDATION BEFORE PROCESSING:
   required_fields = ['admin_graphql_api_id', 'title']
   missing = [f for f in required_fields if not payload.get(f)]
   if missing:
       _logger.warning("Webhook payload missing fields: %s", missing)
       # Still process with available data, or skip with logged reason

3. WEBHOOK PAYLOAD LOGGING:
   Store raw payload in webhook log (for debugging)
   Truncate to reasonable size (e.g., 64KB)

4. SCHEMA EVOLUTION:
   Don't fail on unknown fields (ignore them)
   Only require fields that are truly essential
```

### Detection
- Webhook log with `status=error` and parsing error messages
- Alert on webhook error rate > 5%

---

## Scenario 10: Memory Exhaustion on Large Sync

### Description
Initial sync of 10,000 products loads all records into memory, causing OOM on Odoo.sh worker.

### Impact
- Worker killed by OOM killer
- Sync never completes
- Other Odoo operations affected

### Prevention
```
1. CHUNKED PROCESSING:
   BATCH_SIZE = 50
   offset = 0
   while True:
       products = self.env['product.template'].search(
           domain, limit=BATCH_SIZE, offset=offset
       )
       if not products:
           break
       self._export_batch(products)
       offset += BATCH_SIZE
       self.env.cr.commit()  # Release memory between batches
       self.env.invalidate_all()  # Clear ORM cache

2. GENERATOR PATTERN FOR SHOPIFY READS:
   def _fetch_all_products(self):
       cursor = None
       while True:
           response = self._call_shopify(PRODUCTS_QUERY, {'after': cursor})
           products = response['data']['products']['edges']
           yield from products
           page_info = response['data']['products']['pageInfo']
           if not page_info['hasNextPage']:
               break
           cursor = page_info['endCursor']

3. MONITORING:
   Log memory usage at batch boundaries
   Alert if memory exceeds threshold
```

### Detection
- Worker process killed (exit code 137)
- Sync log shows batch N completed but batch N+1 never started
