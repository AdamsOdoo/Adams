# Wave 0 Official Source Capture — Security, Roles, and Fulfillment Scopes

- **Accessed:** 2026-07-15
- **Access status:** all sources below were Accessible.
- **Purpose:** narrow refresh for the two research gaps named by the MVP completion program. This capture does not authorize addon code.

## Shopify access scopes

### Shopify API access scopes

- **Source:** Shopify, [API access scopes](https://shopify.dev/docs/api/usage/access-scopes)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Shopify lists `read_fulfillments` / `write_fulfillments` against the `FulfillmentService` resource.
- **[Fact]** Shopify separately lists `read_merchant_managed_fulfillment_orders` / `write_merchant_managed_fulfillment_orders` for `FulfillmentOrder` access, alongside assigned- and third-party-fulfillment-order scope families.
- **Implication:** `read_fulfillments` is a valid scope name, but it does not prove access to the FulfillmentOrder workflow selected by DEC-011.

### FulfillmentOrder object

- **Source:** Shopify, [FulfillmentOrder — GraphQL Admin API](https://shopify.dev/docs/api/admin-graphql/latest/objects/FulfillmentOrder)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** FulfillmentOrder results are filtered by the fulfillment-order scopes granted to the app.
- **[Fact]** The merchant-managed scope pair grants access to fulfillment orders assigned to merchant-managed locations.
- **[Fact]** Assigned-fulfillment-order scopes are intended for fulfillment-service apps; third-party scopes concern locations managed by other fulfillment services.
- **Implication:** the connector's Phase-1 order-management posture should request the merchant-managed pair, not infer access from `read_fulfillments`.

### Order-management fulfillment guide

- **Source:** Shopify, [Build fulfillment solutions](https://shopify.dev/docs/apps/build/orders-fulfillment/order-management-apps/build-fulfillment-solutions)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Shopify describes order-management apps as managing fulfillment on a merchant's behalf through FulfillmentOrder actions.
- **[Fact]** The guide requires fulfillment-order scopes and warns that, from API version 2024-10, fulfillment creation is limited to merchant-managed locations or a third-party fulfillment service owned by the app.
- **Implication:** merchant-managed fulfillment orders are the narrow MVP fit. Broad third-party orchestration remains outside the accepted MVP.

## Shopify protected customer data

- **Source:** Shopify, [Work with protected customer data](https://shopify.dev/docs/apps/launch/protected-customer-data)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Shopify's requirements include encryption at rest and in transit, purpose-limited retention, encrypted backups at the higher protection level, environment separation, staff-access limits, and access logging.
- **Implication:** DEC-028's posture ladder remains directionally aligned with current official requirements. Evidence of the chosen hosting/deployment controls is still required before real-customer PII UAT or production use; this capture does not claim that evidence already exists.

## Odoo 19 roles and access control

### Developer security reference

- **Source:** Odoo, [Security in Odoo — 19.0](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Model access rights grant CRUD operations by group.
- **[Fact]** Record rules are evaluated after access rights and are default-allow when no applicable rule restricts the operation.
- **[Fact]** A group-less ACL grants its permissions broadly, including to non-employee user classes.
- **Implication:** model ACLs alone cannot enforce sanctioned state transitions or immutable binding identity; server-side method/field guards remain necessary.

### Access-rights administration

- **Source:** Odoo, [Access rights — 19.0](https://www.odoo.com/documentation/19.0/applications/general/users/access_rights.html)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Odoo groups collect users, inherited groups, menus, views, model access rights, and record rules.
- **[Fact]** Odoo advises testing access-right changes against the intended users.
- **Implication:** the connector can use one shared role-gated surface and standard group assignment rather than inventing a second permission system.

### Restrict-data tutorial

- **Source:** Odoo, [Restrict access to data — 19.0](https://www.odoo.com/documentation/19.0/developer/tutorials/restrict_data_access.html)
- **Status/date:** Accessible, 2026-07-15.
- **[Fact]** Access rights are additive across a user's groups; if no ACL applies, access is denied.
- **[Fact]** A group-less ACL is a risky fallback because it can grant model access beyond internal users.
- **Implication:** the accepted implied-group hierarchy is compatible with Odoo's additive ACL model, but tests must verify effective permissions for each role rather than inspecting one CSV row in isolation.
