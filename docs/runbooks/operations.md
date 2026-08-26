# Operations runbook

Use the four pillars: Dashboard, Operations, Reporting, and Configuration. Sales and Connector Health are separate views.

Store states mean:

- `Setup Incomplete`: mandatory guided choices/evidence are missing.
- `Connected — Initial Sync Pending`: authenticated but required producers have not started.
- `Initial Sync Running`: enumeration or child work is active.
- `Initial Sync Needs Attention`: a blocking initial case requires action.
- `Ready`: required scans and children completed, mappings/first push are valid, evidence is fresh, and no blocking case remains.
- `Degraded`: connected with a backlog, stale evidence, API health issue, or review condition.
- `Reconnect Required`: identity/credential/generation evidence is no longer usable.
- `Disconnected`: no business work may execute.

Needs Attention is the business recovery surface. Open the affected record and use the cause-specific action: map location, choose product match, reconnect, grant scope, review cancellation, review drift, re-read uncertain mutation, or confirm/reject a protected change. Never manually replay an uncertain transport.

Queue dispatch is woken after durable enqueue and retains the cron fallback. Work is scheduled fairly across stores and remains serialized by business-resource scope. Product/order scans resume fixed windows; inventory/fulfillment passes use 200-row keyset slices. Check health if reconciliation exceeds 60 minutes under supported load.

Retention defaults: low-risk terminal jobs 90 days, resolved Layer-2 evidence detail masked after 180 days, webhook envelopes 30 days. Failed/review jobs, active review evidence, and unresolved uncertain attempts are preserved.
