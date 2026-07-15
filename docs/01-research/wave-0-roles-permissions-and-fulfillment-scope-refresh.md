# Wave 0 Research Refresh — Roles, Permissions, and Fulfillment Scopes

> **Status:** Wave 0 research conclusion, proposed for Claude control-room acceptance with the Wave 0 PR. External facts are captured in [the dated source capture](../00-source-materials/wave-0-official-security-scope-captures-2026-07-15.md).

## 1. Scope and method

This refresh covers only the two gaps named in `mvp-completion-program.md`: (1) roles/permissions-specific Odoo 19 evidence and (2) the correctness of `REQUIRED_MVP_SCOPES` for the FulfillmentOrder-based Wave 4 design. The existing competitor corpus was not re-run because no dated evidence showed that it was stale enough to affect either conclusion.

## 2. Roles and permissions

### Facts

1. **[Fact — Odoo official]** ACL grants are additive across all of a user's groups; record rules are evaluated after ACLs and are default-allow when no applicable rule restricts a record.
2. **[Fact — repo]** `shopify_connector_core` defines four groups once: Auditor; Operator and Reviewer each imply Auditor; Administrator implies Operator and Reviewer.
3. **[Fact — repo]** Product and sale ACLs correctly reference the core groups rather than redefining domain-local copies.
4. **[Fact — repo]** The current ACLs still grant operator/reviewer/admin write surfaces that can mutate protected job state or binding identity through RPC/ORM, and Auditor can read customer-binding PII snapshots. Task SEC-1 documents the exact exposures and negative-test plan.

### Conclusions

- **[Inference]** The current implied-group graph matches DEC-013 and DEC-018's accepted hierarchy. Reusing the core groups from domain modules is the intended shared-core pattern, not a structural inconsistency.
- **[Inference]** A dedicated `shopify_connector_sale` groups file would duplicate the connector-wide authorization substrate and conflict with the shared-core direction. No such file should be added merely for symmetry.
- **[Recommendation]** Keep the four-role model and one shared connector application surface. Wave 5's Roles & Access screen should explain effective capabilities and link administrators to standard Odoo user/group assignment; it should not invent connector-specific entitlement storage.
- **[Recommendation]** Wave 1 SEC-1 must add effective-permission tests for representative Auditor, Operator, Reviewer, and Administrator users, including implied-group behavior and negative RPC/ORM attempts. UI `readonly` flags are not a security boundary.
- **[Recommendation]** Keep the single-store MVP free of new record rules unless a record-isolation requirement appears. SEC-1's protected-field guards and least-privilege field visibility are the proportionate current control; multi-store/company record isolation requires its own later decision.

**Research-gap disposition:** roles/permissions-specific research is closed for MVP implementation. Remaining work is implementation/test/UI evidence, not further generic ACL research.

## 3. Fulfillment scopes

### Facts

1. **[Fact — repo]** `REQUIRED_MVP_SCOPES` currently includes `read_fulfillments`.
2. **[Fact — Shopify official]** `read_fulfillments` governs `FulfillmentService`; it does not grant FulfillmentOrder access.
3. **[Fact — Shopify official]** Merchant-managed FulfillmentOrder access is governed by `read_merchant_managed_fulfillment_orders` and `write_merchant_managed_fulfillment_orders`.
4. **[Fact — repo]** Task 014 D-014-2 already proposes the same narrow correction: replace the baseline read scope and require the write scope only when the fulfillment domain is enabled.

### Conclusion

- **[Recommendation]** Accept Task 014 D-014-2 unchanged:
  - replace `read_fulfillments` in the core baseline with `read_merchant_managed_fulfillment_orders`;
  - add an essential, fulfillment-domain-conditional check for `write_merchant_managed_fulfillment_orders`;
  - do not request assigned- or third-party-fulfillment-order scopes for the Phase-1 merchant-managed flow.
- **[Recommendation]** Implement and test this correction in Wave 4, in the exact core file/test allowlist already named by Task 014. No Wave 0 addon edit is permitted.

**Research-gap disposition:** TD-002's research question is closed. Its code status remains open until the Wave 4 correction and tests merge.

## 4. Decision and wave impacts

- Acceptance matrix item 19 should no longer call the lack of a sale-local groups file a gap.
- Wave 1 SEC-1 remains mandatory before operator UI and before real-customer PII exposure.
- DEC-028 should be a hard gate before real-PII dev-store UAT or production, not a blocker for synthetic Wave 1–5 tests.
- Wave 4 keeps the already-proposed merchant-managed FulfillmentOrder scope correction; no additional scope research is required unless Shopify changes the official scope model.
