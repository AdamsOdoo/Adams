# V1 known limitations

- Credentials remain write-only through the application but are stored as protected plaintext at rest. Database, backup, and hosting access must be restricted accordingly.
- Refund, return, and credit-note accounting is not automated. `REFUNDED` and `PARTIALLY_REFUNDED` orders stop in Needs Attention.
- Shopify inventory is comparison evidence only and is never imported into Odoo. Odoo available quantity is authoritative after confirmed first push.
- Product or variant deletion never deletes an Odoo product. A missing Shopify product makes its bindings stale and requires review.
- Moving an already mapped Odoo warehouse/location subtree is not automatically reconciled. Review mappings and inventory pairs after such a change.
- Reviewer remains as a compatibility capability primitive, is not a customer-facing operational role, and cannot invoke privileged cron/service RPCs.
- Store records are durable evidence. Normal lifecycle is disconnect/reconnect; removal is intentionally constrained by uninstall safety checks.
- Merchant token rotation/revocation in Shopify remains the merchant's responsibility after local disconnect or uninstall.
- V1 is bounded by the limits in `v1-supported-scope.md`; it does not claim unlimited scale.
- Final public qualification still requires exact-head CI, Odoo.sh, live backend validation, browser role UAT, and two unchanged-candidate UAT runs. A repository commit alone is not release evidence.
