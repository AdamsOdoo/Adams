# Store 360 query-count measurement — 2026-08-01

**Method.** [Fact — measured locally on the CI container, same pinned Odoo
source `30bde9ff758834a4912c5ae55843d3a7dad849f1`, Python 3.12, PostgreSQL 16.]
An `odoo-bin shell` session against a scratch database at the candidate head
wrapped `cr.execute` with a counter (the same technique as
`shopify_connector_core/tests/test_ui_performance.py::_count_queries`), seeded
one connected store plus 50 finished jobs, flushed, warmed each RPC once, then
measured the second (warm) call. The session ended with `cr.rollback()` — the
database was left unchanged. Two caller shapes were measured:

- **Auditor-only** — connector Auditor without sale/stock access: the
  commercial, lifecycle, and dispatch providers fail closed to their honest
  `no_permission` sections (this is the same caller shape the in-suite
  performance tests use).
- **Full-access** — connector Auditor + `sales_team.group_sale_salesman_all_leads`
  + `stock.group_stock_user`: every provider runs its full aggregate path.

**Results (warm, SQL statements per RPC call).**

| Call | Queries |
| --- | --- |
| `get_dashboard_data` (legacy U0 dashboard, kept unchanged) | 17 |
| `get_store_360_data(False, '30d')` — auditor-only | 29 |
| `get_store_360_data(<store>, '30d')` — auditor-only | 29 |
| `get_store_360_data(False, '24h')` — auditor-only | 29 |
| `get_store_360_data(False, '30d')` — full access | 48 |
| `get_store_360_data(<store>, '30d')` — full access | 48 |

**Reading.** The Store 360 RPC is a constant-query aggregate: the count does
not vary with the store filter or the period, and the full-access shape adds a
fixed set of grouped reads (sale/fulfillment providers), not per-record work.
The in-suite contract tests additionally prove the count stays constant across
data volume and store count and stays ≤ the recorded bound
(`test_store360_query_count_bounded`,
`test_store360_query_count_constant_across_scale`,
`test_store360_query_count_constant_across_store_count`). [Fact — suite
results in `connector-suite-summary.json`.]
