# Scenario 6 (faithful) — real action_disconnect() race — timeline & outcome

Two independent Odoo transactions/connections; Worker B calls the REAL merged
`store.action_disconnect()` (no store.write substitute, no monkeypatch). Worker A
runs the real single-transaction dispatch (`_claim_for_dispatch` -> `_start_running`
-> hold -> `_invoke_handler` -> commit), holding the job row lock across the pause.

## Variant LIB (Worker B = library call, NO retrying() wrapper)
| event | UTC timestamp |
| --- | --- |
| A claim + running (holds job row lock) | 07:13:33.746 |
| B action_disconnect requested (b_start) | 07:13:34.685 |
| B BLOCKED on job row (pg: pid 4847 `Lock/transactionid`, FK KEY SHARE on shopify_connector_job) | ~07:13:34.7 |
| A checkpoint-3 probe: observed store = **connected** | 07:13:34.768 |
| A handler ran, job -> **succeeded**, A commit | 07:13:34.776 |
| B unblocks -> **SerializationFailure** ("could not serialize access due to concurrent update"), rolled back | 07:13:34.775 |

**Final committed (LIB): store = connected (disconnect ROLLED BACK), job = succeeded, 2 log rows, no cancellation, no audit job.**
Raw behavior: without the RPC retry layer, the operator's disconnect FAILS with a serialization error and must be retried by the caller.

## Variant RPC (Worker B = action_disconnect via XML-RPC -> Odoo `retrying()` layer)
| event | UTC timestamp |
| --- | --- |
| A claim + running (holds job row lock) | 07:15:23.617 |
| B action_disconnect requested via RPC (b_start) | 07:15:24.090 |
| B server backend BLOCKED on job row (pg: pid 5626 `Lock/transactionid`) | ~07:15:24.1 |
| A checkpoint-3 probe: observed store = **connected** | 07:15:24.551 |
| A handler ran, job -> **succeeded**, A commit | 07:15:24.560 |
| B unblocks -> `ERROR: could not serialize access due to concurrent update` | 07:15:24.560 |
| server: `INFO odoo.service.model: SERIALIZATION_FAILURE, 4 tries left, try again in 1.4222 sec...` (retrying() retries) | 07:15:24.560 |
| B action_disconnect completes on retry (job already terminal -> 0 cancelled) | 07:15:25.001 |
| server: HTTP 200 for POST .../action_disconnect | 07:15:26.000 |

**Final committed (RPC): store = disconnected, job = succeeded (handler ran, NOT cancelled), 2 log rows, lifecycle audit job = "Store disconnected (0 non-terminal business job(s) cancelled)."**

## What this proves (and disproves)
- The real `action_disconnect()` does NOT commit a disconnect that checkpoint-3 then fails to see. It **blocks on the in-flight job's row lock**; the handler runs to completion; the job succeeds.
- On unblock it hits a **serialization conflict**; the library path raises+rolls back, the RPC path is **automatically retried by Odoo's `retrying()` layer** and then completes, cancelling nothing (the job is already terminal).
- The live handler runs BEFORE the disconnect completes. "disconnect requested" != "disconnect committed".
- checkpoint-3 cannot skip the in-flight job (single REPEATABLE READ snapshot; same value as checkpoint-2). The plan's expected "skip" does NOT occur.
- The earlier direct-`store.write({'state':'disconnected'})` experiment (scenario-06-variantA/B/C + scenario-06b probe) is a NARROW snapshot-visibility OBSERVATION only, NOT the lifecycle result, and is not used to call any defect "runtime-confirmed".
- SRR-03 remains OPEN in all cases.
