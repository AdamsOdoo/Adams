# V1 UAT matrix

Use fresh `GPT-RC-UAT-<UTC timestamp>-<scenario>` records only in `testin-lzhbzhtc.myshopify.com`. Record Odoo IDs, Shopify GIDs, delivery/job/attempt chain, expected/actual local and remote outcome, user-visible result, cleanup, and pass/fail.

| ID | Journey | Critical proof | Roles |
|---|---|---|---|
| UAT-1 | Fresh onboarding | permanent domain, write-only credential, scopes, authorities, mapping, first preview, activation, truthful initial state | Administrator |
| UAT-2 | Resume | reload/sign-out at multiple steps; no mandatory skip; legacy progress | Administrator |
| UAT-3 | Product | import/update/match/conflict/export/variant add/delete-as-stale/recovery; no status flip/unsafe clear | Operator, Administrator, Auditor view |
| UAT-4 | Inventory | discover/map/preview/stale refusal/confirm/push/drift/uncertainty/reconcile; no wedge | Operator, Administrator |
| UAT-5 | Order | exact values, duplicate/update/composition/cancel/void/refund review; no duplicate or silent shipment | Operator, Auditor |
| UAT-6 | Fulfillment | full/partial/tracking/notify/replay/conflict/timeout/reconcile; Mode 1/2 | Operator, Administrator |
| UAT-7 | Health | setup/connected/initial/ready/degraded/reconnect; drill-down | All internal roles |
| UAT-8 | Needs Attention | mapping/match/cancellation/drift/scope/credential/uncertain/fulfillment; one clear action | Applicable role matrix |
| UAT-9 | Configuration change | impact, stale-work fence, reconciliation, resume | Administrator |
| UAT-10 | Authorization | UI visibility and direct RPC | No Access, Auditor, Operator/User, Reviewer, Administrator |
| UAT-11 | Multi-company/store | isolation, correct context, queue fairness | Administrator, Operator, Auditor |
| UAT-12 | Upgrade/rollback | prior-shape upgrade, repeat, preservation, smoke, documented restore | Administrator |

Backend gates A–G run before browser UAT. After one complete pass, freeze SHA/tree/build/module versions, reset only isolated UAT data, and rerun the complete critical matrix. Any code change invalidates affected evidence.
