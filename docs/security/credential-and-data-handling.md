# Credential and data handling

Credentials are accepted only through write-only connector actions. Normal users and RPC callers cannot read a stored token/secret back. Logs, jobs, webhook envelopes, fixtures, screenshots, reports, and Git must contain no secret.

Accepted residual: connector credentials are protected by Odoo access controls but stored as plaintext at rest. This release makes no encryption-at-rest claim. Restrict database/backup/hosting administrator access, encrypt infrastructure storage and backups, audit access, and rotate/revoke in Shopify after suspected exposure, disconnect, or uninstall.

Webhook authentication verifies HMAC over the exact raw request body before durable intake. Durable envelopes are payload-free and retain allowlisted identifiers/digests only. Duplicate, stale-generation, wrong-store, wrong-version, and unknown-topic cases fail closed.

Customer ambiguity evidence contains identifiers, counts, active flags, and a one-way email fingerprint—not customer names, addresses, phone numbers, or email text. Aged job-log payloads are redacted. Resolved Layer-2 detail is masked after 180 days; unresolved uncertainty is preserved. Webhook envelopes are deleted after 30 days in bounded batches. Low-risk terminal jobs are retained 90 days; active review and failed evidence remain.

Order business records necessarily contain the customer/address/payment evidence required by the supported import. Apply Odoo record rules, company restrictions, retention law, and backup controls to those business records; technical retention does not erase them.
