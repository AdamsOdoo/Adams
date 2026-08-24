# Roles and company isolation

| Role | Intended access | Privileged cron/service RPC |
|---|---|---|
| No Access / ordinary internal user | No connector data/actions | Denied |
| Auditor | Read-only evidence appropriate to company | Denied |
| Operator/User | Day-to-day sync and recovery actions explicitly granted | Denied for job drain, PII retention, stale-owner sweep, inventory scan, and media poll |
| Reviewer | Compatibility capability only; not a customer-facing role | Denied |
| Connector Administrator | Setup, credentials through write-only actions, configuration, protected maintenance | Allowed only where intentionally guarded |
| Root cron | Scheduled internal execution | Allowed |
| Portal/public | No connector records or services | Denied |

Menu visibility is not authorization. The five privileged services named above enforce the role check server-side, so direct RPC by a lower role raises `AccessError`.

Every connector record is scoped through its owning store and related company. Stored company fields derive from the store; parent relations enforce same-store consistency. Record rules prevent a user from reading or acting on another allowed company's store, job, binding, review case, webhook, or mutation evidence. A company may own multiple stores, so same-company equality never substitutes for same-store validation.

Administrators must test both UI visibility and direct RPC after installation/upgrade. Multi-company qualification must use separate companies/stores and verify foreign identifiers cannot be fetched by ID, search, action, or linked evidence route.
