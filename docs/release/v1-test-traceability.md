# V1 test traceability

| Gate / finding | Automated evidence | Runtime/live evidence still required |
|---|---|---|
| A-1 order field | GraphQL schema gate; realistic multi-unit price derivation/import tests | Fresh tagged Shopify order and exact Odoo totals |
| A-2 fulfillment list | schema gate; list-shape/malformed reader tests | Live fulfillment read on API `2026-07` |
| O-2 unsafe lifecycle | cancellation/void/expiry/refund matrix; fulfillment admission/pre-C2 refusal | Remote transition visible in Needs Attention |
| PR-1 status safety | ACTIVE title-only preview; explicit ownership; migration repeat | Confirmed safe export remains published |
| PR-2/3/8 variant add | created-ID binding, identity preflight, finalization replay/adoption | Exactly one remote variant and correct binding |
| I-1/2/5 first push | pre-preview stock event, pending/previewed scan, stale refusal, no blocked scope | Fresh pair preview/confirm/re-scan |
| U-1–U-10 | navigation, setup copy, state derivation, recovery context and access tests | Four-pillar browser journeys by role |
| S-1 | direct RPC matrix for five protected methods | Same matrix in exact Odoo.sh build |
| PR-6/W-4/W-5 | terminal webhook disposition, uninstall generation, topic reinstall tests | Subscription/uninstall/reconnect scenarios |
| W-2/P-1/P-4 | >legacy product pages; order cursor restart; fulfillment/inventory bounded passes | Supported-scale timing and restart injection |
| P-2 | fair claim/drain and enqueue wakeup tests | Multi-store queue load |
| P-3/P-6 | >500 terminal jobs, attempt preservation, 2,000 webhook batch, indexes | Upgrade and retention timing |
| Supported scale | essential readiness failure above limit | Exact-head load artifacts and health UI |

Local static qualification for each commit includes `git diff --check`, Python compile/AST, manifest parse, XML parse, GraphQL document inventory/conformance when dependencies are available, and a diff secret scan. These checks do not replace Odoo runtime tests.
