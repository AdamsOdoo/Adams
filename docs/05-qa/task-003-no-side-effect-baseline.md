# Task 003 — No-Side-Effect Static Baseline (VAL-D1 / VAL-D2)

## Session metadata

| Field | Value |
| --- | --- |
| Date | 2026-07-07 |
| Branch | `claude/task-003-static-validation-cszl88` |
| Session type | Docs/QA-only, static repo inspection — no live Odoo instance, no live Shopify connection |

This document is the detailed evidence backing the VAL-D1 and VAL-D2 rows in
[`task-003-static-validation-sweep.md`](./task-003-static-validation-sweep.md).
It records **static code-path evidence only** — what the code does, as
written — not a live observation of an actual run. It is not a substitute for
the live checks defined in
[`task-003-manual-validation-checklist.md`](./task-003-manual-validation-checklist.md)
§D, which remain not tested.

---

## VAL-D1 — No Shopify-side mutation (static evidence)

### The query used

`addons/shopify_connector_core/models/shopify_connector_store.py:14-18`:

```graphql
TEST_CONNECTION_QUERY = """
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
"""
```

This matches, character-for-character (aside from Python triple-quote
wrapping), the query text specified in this session's task scope. It is a
GraphQL `query` operation, not a `mutation` operation — it requests only
`shop.id`, `shop.name`, `shop.myshopifyDomain`, and
`currentAppInstallation.accessScopes.handle`, all of which are read
operations against Shopify's Admin GraphQL API.

### No mutation string exists in the client/test-connection path

A repository-wide grep for the GraphQL keyword `mutation` inside
`addons/shopify_connector_core/` returns exactly three hits, none of which is
an actual mutation operation string:

1. `models/shopify_connector_api_client.py:84` — a docstring sentence stating
   "there is no mutation-capable method, no retry loop ...".
2. `models/shopify_connector_store.py:12` — a comment: "no mutation, no
   [variables needed]".
3. `tests/test_api_client.py:253-258` — a pre-existing regression test
   (`# 18. Read-only guarantee: no mutation operation string; minimal public
   surface.`) that asserts, via
   `re.search(r'\bmutation\s*[\{\(]', source)`, that no mutation operation
   string appears in the client module's source.

There is no second GraphQL operation defined anywhere in
`shopify_connector_core` other than `TEST_CONNECTION_QUERY` above. The API
client (`shopify_connector_api_client.py`) exposes a single `execute(store,
query, variables=None)` method that sends whatever query string it is given;
Task 003's own code only ever calls it with `TEST_CONNECTION_QUERY`.

### Static conclusion

**Static read-only-query evidence: confirmed.** The only GraphQL operation
Task 003's code path can send to Shopify is the read-only
`ConnectorTestConnection` query above; no mutation string exists anywhere in
the module for it to send instead.

### What remains unproven (live evidence still required)

This is **not** a live observation. It does not confirm that Shopify's server
actually returned data without making any change, nor does it confirm zero
webhooks were registered — those require inspecting the Shopify development
store's admin (Orders, Products, Customers, Inventory, Fulfillment, Settings
→ Notifications/Webhooks) before and after a real run, which is the actual
VAL-D1 step in the checklist. That live check was not performed this session
and remains **not tested**. No Fable/browser evidence from the OAuth/Fable
attempt recorded separately in merged PR #109 (blocked before execution) was
available to, or used by, this session.

---

## VAL-D2 — No Odoo-side domain mutation (static evidence)

### The code path inspected

`action_test_connection()` —
`addons/shopify_connector_core/models/shopify_connector_store.py:86-203` —
and every helper it calls:

- `self.env['shopify.connector.job'].create(...)` / `.write(...)`
- `self.env['shopify.connector.job.log']._system_append(...)` (which itself
  calls `self.sudo().create(...)` on `shopify.connector.job.log` only)
- `self.env['shopify.connector.store.credential'].search(...)` /
  `.write({'credential_state': ...})`
- `self.env['shopify.connector.api.client'].execute(...)` (an
  `AbstractModel` with no table of its own; makes the outbound HTTP call and
  returns parsed data — writes nothing)
- `self.write(...)` on the calling `shopify.connector.store` record itself

### Models touched, exhaustively

| Model | Fields written | Allowed per this session's scope? |
| --- | --- | --- |
| `shopify.connector.store` | `last_test_connection_result`, `last_test_connection_at`, `last_test_connection_reason`, `credential_last_verified_at`, `granted_scopes`, `granted_scopes_checked_at`, `api_health_state`, `api_health_reason` | Yes |
| `shopify.connector.store.credential` | `credential_state` (only, and only on a genuine token-invalid signal) | Yes |
| `shopify.connector.job` | `error_class`, `state`, `finished_at` (plus the initial `create()` fields) | Yes |
| `shopify.connector.job.log` | append-only rows via `_system_append` | Yes |

No other model is referenced, read, or written anywhere in
`action_test_connection()` or its helpers. In particular, grepping the method
and its call graph confirms **zero** references to any product, customer,
order, inventory, stock, accounting, sale, or purchase model (e.g. no
`product.product`, `product.template`, `res.partner`, `sale.order`,
`stock.quant`, `stock.move`, `account.move`, `purchase.order`, or any other
domain model).

### Static conclusion

**Static code-path evidence: confirmed.** The four models listed above are
the complete set of models `action_test_connection()` can touch; no
domain/business model is in its reachable write set.

### What remains unproven (live evidence still required)

This is **not** a live database mutation proof. It does not confirm that an
actual run, executed against a real Odoo database, in fact left every
domain-model table unchanged (e.g. via a before/after row-count or
`write_date` diff across `product.*`, `res.partner`, `sale.*`, `stock.*`,
`account.*`, `purchase.*`). That live confirmation was not performed this
session and remains **not tested**, per VAL-D2 in
`task-003-manual-validation-checklist.md`.

---

## Explicit non-claims

- This document does not claim VAL-D1 or VAL-D2 fully passed as written in
  the checklist — only their static/source-level halves.
- This document does not claim Task 003 is complete.
- This document does not claim Task 004 is unblocked.
- No code, test, manifest, security, XML, or CSV file was created or
  modified to produce this evidence — it is inspection of the existing
  working tree only.
