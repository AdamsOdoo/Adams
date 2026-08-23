# Recovery runbook

1. Identify the business object, store, Shopify/Odoo states, and exact job/attempt chain from Needs Attention.
2. Determine certainty. If transport outcome is uncertain, re-read Shopify through the provided reconciliation action. Never replay the mutation to discover what happened.
3. Correct the cause: mapping, scope, credential, ambiguous match, stale configuration, cancellation review, or remote drift.
4. Use the record's sanctioned retry/re-read action. `failed_final`, `cancelled`, `skipped`, or `blocked` downstream work is not treated as a processed webhook.
5. Verify both local and remote outcomes and that no active operation scope remains.

For cancelled, voided, expired, refunded, or partially refunded imported orders: do not ship; compare Shopify financial state with the Odoo sale order; perform the merchant's supported manual accounting/business action; then resolve the review with evidence. The connector does not automatically reverse accounting.

For stale product bindings: verify deletion remotely, preserve the Odoo product, decide whether to rematch/recreate outside the uncertain path, and never mark the stale binding synchronized without a fresh read.

For inventory drift or uncertainty: re-read the exact item/location pair, regenerate a stale first-push preview when required, and confirm only current evidence. Do not write Shopify quantity into Odoo.

For reconnect: rotate/repair the credential in Shopify if necessary, enter it through the write-only form, reconnect, reconcile subscriptions, and let generation-fenced catch-up scans complete. Old-generation work must remain refused.
