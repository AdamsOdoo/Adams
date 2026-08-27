# Backend responsiveness architecture

## Baseline finding

The connector has a strong durable-safety substrate, but the merged user flow
does not yet make that substrate responsive or self-completing.

## Runtime path

| Stage | Current owner | Durable evidence | Finding |
|---|---|---|---|
| HTTPS admission | `shopify_connector_webhook` controller | webhook delivery | Raw-body HMAC, topic/store checks and duplicate admission exist |
| Local webhook processing | `webhook_delivery_process` job | job + delivery | Enqueue-only domain delegation preserves the HTTP boundary |
| Domain observation | product, inventory, sale and fulfillment webhook addons | domain child job | Read-first/idempotent handlers exist for the ten active topics |
| Claim and dispatch | core dispatcher | job state/log | `FOR UPDATE SKIP LOCKED`, generation fencing, retries and per-store fairness exist |
| Wake-up | core enqueue service | `ir.cron` trigger | Every sanctioned enqueue triggers the drain; the old five-minute interval is only a lost-trigger/restart fallback |
| Reconciliation | domain and webhook crons | cursor/watermark/jobs | Correct safety net, but must not outrank live events |
| User projection | setup/dashboard Owl clients | server payload | Setup follows location refresh, but did not follow activation completion; dashboards refresh no faster than 30 seconds |

## Confirmed release defects

### A1 — Activation completion dead end

The first activation transitions the store to `connected` and admits durable
webhook reconciliation. Setup remains truthfully incomplete until Shopify
read-back proves the exact subscriptions. The review button was then disabled
by the pre-completion readiness projection, and the client had no activation
completion follower. Existing tests explicitly required a second server-side
activation after proof, but did not require a merchant-reachable browser path.

Correction contract:

- preserve the two-stage lifecycle and all server fences;
- follow only stored job/read-back evidence, never drain or call Shopify from the browser RPC;
- automatically re-enter authoritative activation only at `ready_to_complete`;
- keep Check status reachable after bounded polling;
- surface `action_required` with its exact recovery message.

### R1 — Recovery cadence too slow

Sanctioned enqueue already calls the drain cron's immediate trigger. The
five-minute interval is therefore not the primary path, but it is the recovery
bound after a lost trigger, restart or scheduler interruption. Five minutes is
incompatible with a responsive public connector. The fallback becomes one
minute on fresh installs and through an idempotent versioned migration.

### R2 — Latency is not instrumented as a release contract

Existing timestamps can calculate admission, claim, processing and completion
latency, but the release suite did not aggregate p50/p95/p99 or assert the
public targets. Exact-build live qualification must capture:

- Shopify triggered time;
- Odoo delivery creation time;
- job creation, start and finish time;
- final domain watermark/evidence time;
- first UI observation of the terminal state.

### R3 — Live-event priority remains unproved

The claim loop is fair across stores but selects oldest claimable job within a
store. A scheduled/reconciliation backlog can therefore delay a newer webhook
or manual action. Load qualification must prove the target under backlog. If it
fails, priority with bounded aging must be added without weakening row-lock,
generation, retry or mutation-reconciliation contracts.

### U1 — UI freshness remains unproved

The dashboards use a 30-second minimum refresh interval. That may be acceptable
for passive health reporting but is not acceptable as the only progress surface
after an interactive action. Active runs need a bounded faster follower; idle
dashboards may retain a slower accessibility-conscious refresh.

## Invariants to preserve

- webhook HTTP acknowledgement performs no business API work;
- every remote mutation keeps commit-before-send and uncertain-outcome reconciliation;
- generation and company fences remain authoritative;
- job and delivery uniqueness remain database-backed;
- scheduled reconciliation remains mandatory but secondary to live events;
- no UI state is treated as authorization or business truth;
- no secret enters UI state, logs, evidence or source.

## Open proof before G1 closes

- measure `_trigger()` to worker-start latency on exact Odoo.sh;
- measure each active topic through its terminal domain evidence;
- determine whether same-store backlog violates the p95 target;
- profile the slowest queries/Shopify calls and verify indexes;
- prove restart recovery and backlog drain without manual intervention;
- map active-run UI refresh separately from passive dashboard refresh.
