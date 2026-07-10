# Source Captures — Shopify Customer / Odoo 19 Partner Facts for Task 011 (and MBQ-05 Branch B Distribution Facts)

> **Capture file per `CLAUDE.md` §7.4 (OP-44 routing).** All excerpts
> below were fetched from **official primary sources on 2026-07-10** by
> the AR-039 gate-readiness session's research pass (parallel researcher
> agents; every load-bearing claim additionally adversarially re-verified
> — see the verification record in
> [`../08-release-readiness/pre-implementation-readiness-signoff.md`](../08-release-readiness/pre-implementation-readiness-signoff.md)).
> Direct quotes are marked as such; everything else is precise
> paraphrase; access status is recorded per source. Inferences are
> labelled. This file captures evidence only — it decides nothing and
> authorizes nothing. Consumers: 
> [`../07-implementation-plan/task-011-decision-closure-brief.md`](../07-implementation-plan/task-011-decision-closure-brief.md),
> [`../07-implementation-plan/task-011-final-implementation-prompt.md`](../07-implementation-plan/task-011-final-implementation-prompt.md),
> [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md),
> and the Customer-object section added to
> [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md).

---
<!-- TOPIC: Shopify Admin GraphQL API — MailingAddress object and customer address access (Customer.defaultAddre -->
# Source capture — Shopify Admin GraphQL: MailingAddress & customer address access

**Accessed:** 2026-07-10 · **API version documented by `/latest/` pages:** 2026-07

---

## 1. MailingAddress object

- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/MailingAddress
- **Access status:** Accessible (field descriptions extracted; deprecation-reason tooltip text for `countryCode` not extractable → that item Partial)

**Fields (type — verbatim description, direct quotes):**

| Field | Type | Description (direct quote) |
| --- | --- | --- |
| `address1` | `String` | "The first line of the address. Typically the street address or PO Box number." |
| `address2` | `String` | "The second line of the address. Typically the number of the apartment, suite, or unit." |
| `city` | `String` | "The name of the city, district, village, or town." |
| `company` | `String` | "The name of the customer's company or organization." |
| `country` | `String` | "The name of the country." |
| `countryCodeV2` | `CountryCode` | "The two-letter code for the country of the address. For example, US." |
| `firstName` | `String` | "The first name of the customer." |
| `lastName` | `String` | "The last name of the customer." |
| `name` | `String` | "The full name of the customer, based on firstName and lastName." |
| `phone` | `String` | "A unique phone number for the customer." |
| `province` | `String` | "The region of the address, such as the province, state, or district." |
| `provinceCode` | `String` | "The alphanumeric code for the region. For example, ON." |
| `zip` | `String` | "The zip or postal code of the address." |
| `formatted` | `[String!]!` | "A formatted version of the address, customized by the provided arguments." |

- **Deprecated:** `countryCode` is listed as deprecated (reason text not captured — Partial). `countryCodeV2` is the current enum-typed field.
- **[Inference]** `company` is effectively free text: it is a nullable `String` with no enum, format constraint, or validation documented. The docs do **not** literally say "free text".

## 2. Customer object — address access

- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer
- **Access status:** Accessible (Partial for the `addresses` deprecation-reason text — absent from fetched content on both `latest` (2026-07) and pinned `2025-07` pages; not asserted)

> `defaultAddress: MailingAddress` (nullable) — "The default address associated with the customer." *(direct quote)*
>
> `addressesV2: MailingAddressConnection!` — "The addresses associated with the customer." *(direct quote)*; arguments: `first`, `after`, `last`, `before`, `reverse` (reverse defaults to false — paraphrase).
>
> `addresses: [MailingAddress!]!` — listed under **Deprecated fields**; plain list, not a connection. Argument `first (Int)`: "Truncate the array result to this size." *(direct quote)*. Description extracted in one pass as "The addresses associated with the customer." **[Inference]** `addressesV2` is the replacement (from naming + deprecation); the verbatim migration-guidance string could not be verified.

## 3. Pagination plumbing

- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/connections/MailingAddressConnection — Accessible
  - `edges: [MailingAddressEdge!]!`; `nodes: [MailingAddress!]!`; `pageInfo: PageInfo!` — "An object that's used to retrieve cursor information about the current page." *(direct quote)*
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/PageInfo — Accessible
  - "Returns information about pagination in a connection, in accordance with the Relay specification." *(direct quote)*
  - `hasNextPage: Boolean!` — "Whether there are more pages to fetch following the current page." *(direct quote)*; `hasPreviousPage: Boolean!` — "Whether there are any pages prior to the current page." *(direct quote)*; `endCursor: String` — "The cursor corresponding to the last node in edges." *(direct quote)*; `startCursor: String` — "The cursor corresponding to the first node in edges." *(direct quote)*

<!-- TOPIC: Shopify Admin GraphQL API Customer object (latest stable = 2026-07): field deprecations (email/phone -->
## Source capture — Shopify Admin GraphQL `Customer` object (latest = 2026-07)

- **Source:** Shopify (shopify.dev), Admin GraphQL API reference — `Customer` object
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer (plain-text mirror: https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer.txt)
- **Accessed:** 2026-07-10 — **Status: Accessible** (rendered page + .txt mirror + HTML page source all fetched)
- **API version documented:** `api_version: 2026-07` [direct quote, page frontmatter]

### Object-level [direct quotes]
> "Requires `read_customers` access scope."
>
> Caution block: "Only use this data if it's required for your app's functionality. Shopify will restrict access to scopes for apps that don't have a legitimate use for the associated data."

### Core fields [direct quotes from field reference]
> "id — ID! — non-null — A globally-unique ID."
> "firstName — String — The customer's first name." / "lastName — String — The customer's last name."
> "displayName — String! — non-null — The full name of the customer, based on the values for first_name and last_name. If the first_name and last_name are not available, then this falls back to the customer's email address, and if that is not available, the customer's phone number."
> "note — String — A note about the customer."
> "tags — [String!]! — non-null — A comma separated list of tags that have been added to the customer."
> "verifiedEmail — Boolean! — non-null — Whether the customer has verified their email address. Defaults to `true` if the customer is created through the Shopify admin or API."
> "state — CustomerState! — non-null — The state of the customer's account with the shop. Please note that this only meaningful when Classic Customer Accounts is active." *(grammar as in source)*
> "createdAt — DateTime! — non-null — The date and time when the customer was added to the store."
> "updatedAt — DateTime! — non-null — The date and time when the customer was last updated."
> "numberOfOrders — UnsignedInt64! — non-null — The number of orders that the customer has made at the store in their lifetime."
> "amountSpent — MoneyV2! — non-null — The total amount that the customer has spent on orders in their lifetime."
> "locale — String! — non-null — The customer's locale."

### Contact fields and deprecations
> "defaultEmailAddress — CustomerEmailAddress — The customer's default email address." [direct quote]
> "defaultPhoneNumber — CustomerPhoneNumber — The customer's default phone number." [direct quote]

Deprecated fields section [direct quotes]: `email — String — Deprecated` ("The customer's email address."), `phone — String — Deprecated` ("The customer's phone number."), `addresses — [MailingAddress!]! — non-null, Deprecated` with argument `first: Int — "Truncate the array result to this size."`

Deprecation reasons [direct quotes, extracted from the schema data embedded in the HTML of the same URL — not rendered in the visible text]:
> email: "Use `defaultEmailAddress.emailAddress` instead."
> phone: "Use `defaultPhoneNumber.phoneNumber` instead."
> addresses: "Limited to 250 addresses. Use `addressesV2` for paginated access to all addresses."
> emailMarketingConsent: "Use `defaultEmailAddress.marketingState`, `defaultEmailAddress.marketingOptInLevel`, `defaultEmailAddress.marketingUpdatedAt`, and `defaultEmailAddress.sourceLocation` instead."
> smsMarketingConsent: "Use `defaultPhoneNumber.marketingState`, `defaultPhoneNumber.marketingOptInLevel`, `defaultPhoneNumber.marketingUpdatedAt`, `defaultPhoneNumber.marketingCollectedFrom`, and `defaultPhoneNumber.sourceLocation` instead."

### Addresses [direct quotes]
> "addressesV2 — MailingAddressConnection! — non-null — The addresses associated with the customer." Arguments: `after: String`, `before: String`, `first: Int`, `last: Int`, `reverse: Boolean — Default:false`.
> "defaultAddress — MailingAddress — The default address associated with the customer."

### B2B [direct quote]
> "companyContactProfiles — [CompanyContact!]! — non-null — A list of the customer's company contact profiles."

---

## Source capture — `CustomerEmailAddress` object
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/CustomerEmailAddress — Accessed 2026-07-10 — **Accessible** — `api_version: 2026-07`
> "Requires `read_customers` access scope." [direct quote]

Fields [direct quotes]: "emailAddress — String! — non-null — The customer's default email address." / "marketingState — CustomerEmailAddressMarketingState! — non-null — Whether the customer has subscribed to email marketing." / "marketingOptInLevel — CustomerMarketingOptInLevel — The marketing subscription opt-in level, as described by the M3AAWG best practices guidelines, received when the marketing consent was updated." / "marketingUnsubscribeUrl — URL! — non-null — The URL to unsubscribe a member from all mailing lists." / "marketingUpdatedAt — DateTime — The date and time at which the marketing consent was updated. No date is provided if the email address never updated its marketing consent." / "openTrackingLevel — CustomerEmailAddressOpenTrackingLevel! — non-null" / "openTrackingUrl — URL! — non-null" / "sourceLocation — Location — The location where the customer consented to receive marketing material by email." / "validFormat — Boolean! — non-null — Whether the email address is formatted correctly. Returns `true` when the email is formatted correctly. This doesn't guarantee that the email address actually exists."

---

## Source capture — `CustomerPhoneNumber` object
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/CustomerPhoneNumber — Accessed 2026-07-10 — **Accessible** — `api_version: 2026-07`
> "Requires `read_customers` access scope." / "A phone number." [direct quotes]

Fields [direct quotes]: "phoneNumber — String! — non-null — A customer's phone number." / "whatsAppMarketingConsent — CustomerWhatsAppMarketingConsent! — non-null — The WhatsApp marketing consent information for the customer's phone number. Update with the `customerWhatsAppMarketingConsentUpdate` mutation."
Deprecated fields on this object [direct quote of listing]: "marketingCollectedFrom — CustomerConsentCollectedFrom — Deprecated; marketingOptInLevel — CustomerMarketingOptInLevel — Deprecated; marketingState — CustomerSmsMarketingState! — non-null, Deprecated; marketingUpdatedAt — DateTime — Deprecated; sourceLocation — Location — Deprecated" (no replacement reasons shown on page — **open question** for SMS consent read path).

---

## Source capture — Protected customer data requirements
- **URL:** https://shopify.dev/docs/apps/launch/protected-customer-data (fetched via .txt mirror) — Accessed 2026-07-10 — **Accessible**
> "Customers (GraphQL Admin API ...) — Data that defines facts about a single customer, including name, addresses, email, and phone number." [direct quote, protected API types table]
> Level 2 = "Customer data **including** name, address, phone, or email fields" requiring: "Request access to protected customer data and fields in the Partner Dashboard", "Implement level 1 and level 2 protected customer data requirements", "Participate in data protection reviews". [direct quote]
> "you'll need to request access to the following protected customer fields individually because they directly identify customers: Name: first and last names; Address: address line 1, address line 2, geolocation, and zip codes in both billing and shipping addresses; Email; Phone" [direct quote]
> App-type availability [direct quote of table rows]: "1 — Requires review — Always available — Always available" / "2 — Requires review — Always available — Varies by plan" (columns: Public app / Custom app / Admin created custom app).

**Classification:** all statements above are **Fact (official primary source, shopify.dev)** except items explicitly flagged as open questions.

<!-- TOPIC: Shopify B2B constructs relevant to customer import: Company, CompanyContact, Customer.companyContact -->
## Source capture — Shopify B2B constructs for customer import (accessed 2026-07-10)

All pages fetched directly (WebFetch + raw `curl` of page HTML for quote verification). `/latest/` API reference URLs resolved to **API version 2026-07** (2026-10 appears on the pages only as "release candidate / Unstable").

### 1. Customer object — Admin GraphQL API 2026-07
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer
- **Access status:** Accessible (2026-07-10)
- **Direct quote (raw schema embedded in page):** `companyContactProfiles: [CompanyContact!]!`
- **Direct quote (field description):** "A list of the customer's company contact profiles."
- **Verified absence (paraphrase, from full raw schema block):** the complete `object Customer { ... }` field list contains **no** person/company boolean or type flag. Boolean fields are limited to `canDelete`, `dataSaleOptOut`, `hasTimelineComment`, `taxExempt`, `validEmailAddress`, `verifiedEmail`. The only company-related field is `companyContactProfiles`.

### 2. MailingAddress object — 2026-07
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/MailingAddress
- **Access status:** Accessible (2026-07-10)
- **Direct quote:** field `company` (type `String`) — "The name of the customer's company or organization."
- **Paraphrase:** free-text string only; docs link the type solely to the `String` scalar, with no reference to the B2B `Company` object.

### 3. Company object — 2026-07
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/Company
- **Access status:** Accessible (2026-07-10)
- **Direct quote (object description):** "A business entity that purchases from the shop as part of B2B commerce. Companies organize multiple locations and contacts who can place orders on behalf of the organization. `CompanyLocation` objects can have custom pricing through `Catalog` and `PriceList` configurations."
- **Direct quote (required access):** "Requires `read_customers` access scope or `read_companies` access scope. Also: The shop must have access to B2B. Some operations may require additional plan capabilities."
- **Paraphrase (key fields):** `contacts: CompanyContactConnection!`, `locations: CompanyLocationConnection!`, `mainContact: CompanyContact`, `name: String!`, `orders: OrderConnection!`, `draftOrders: DraftOrderConnection!`.

### 4. CompanyContact object — 2026-07
- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/objects/CompanyContact
- **Access status:** Accessible (2026-07-10)
- **Direct quote (object description):** "A person who acts on behalf of a `Company` to make B2B purchases. Company contacts are associated with `Customer` accounts and can place orders on behalf of their company. Each contact can be assigned to one or more `CompanyLocation` objects with specific roles that determine their permissions and access to catalogs, pricing, and payment terms configured for those locations."
- **Direct quotes (fields):** `customer` (`Customer!`, non-null) — "The customer associated to this contact."; `company` (`Company!`, non-null) — "The company to which the contact belongs."
- **Direct quote (required access):** identical to Company: "Requires `read_customers` access scope or `read_companies` access scope. Also: The shop must have access to B2B. Some operations may require additional plan capabilities." Write-side (from embedded mutation data, e.g. `companyContactUpdate`): "`write_customers` access scope or `write_companies` access scope. Also: The shop must have access to B2B..."

### 5. B2B app-building docs
- **URL:** https://shopify.dev/docs/apps/build/b2b
- **Access status:** Accessible (2026-07-10)
- **Direct quote (data model):** "Company — Information about the business entity that makes a B2B purchase. A company contains locations and contacts." / "CompanyContact — A person that acts on behalf of the company. A company contact is associated with a retail customer record." / "CompanyLocation — A single location or branch of the company"
- **Direct quote (Limitations):** "Your plan must support B2B capabilities to use apps with B2B features. Only dev stores, Shopify Plus Partners, and Shopify affiliates are able to access the GraphQL Admin API's B2B resources. Shopify Plus Partners need to use a sandbox organization."
- **Direct quote (orders):** "A B2B order or draft order can be associated with the company, a specific company location, or a specific company contact. However, catalogs can be assigned only to a company location."
- **Note (do not overstate):** this page does **not** contain the literal sentence "requires the Shopify Plus plan" — the Plus-only merchant-plan claim must be sourced from help.shopify.com before asserting it as fact.

<!-- TOPIC: Shopify protected customer data (PCD) requirements — levels/terminology, review requirements by app  -->
# Source capture — Shopify protected customer data (PCD)

## Source 1: shopify.dev — Work with protected customer data
- **URL:** https://shopify.dev/docs/apps/launch/protected-customer-data
- **Accessed:** 2026-07-10 — **Status: Accessible** (no redirect; page title "Work with protected customer data"). API version: not pinned on page; endpoints shown generically as `/admin/api/{api_version}/graphql.json`.

### Level table (direct quotes, table cells verbatim)
| Level | Data use | Partner actions |
| --- | --- | --- |
| 0 | "No customer data" | "No action required" |
| 1 | "Customer data **excluding** name, address, phone, and email fields" | "Request access to protected customer data in the Partner Dashboard"; "Implement level 1 protected customer data requirements" |
| 2 | "Customer data **including** name, address, phone, or email fields" | "Request access to protected customer data and fields in the Partner Dashboard"; "Implement level 1 and level 2 protected customer data requirements"; "Participate in data protection reviews" |

> [Direct quote] "Protected customer data includes any data that directly relates to a customer or prospective customer, as represented in the API types and resources. Types and resources that don't refer to a single customer, such as the product query, aren't included."

> [Direct quote — protected customer fields] "In addition to requesting access to protected customer data, you'll need to request access to the following protected customer fields individually because they directly identify customers: Name: first and last names / Address: address line 1, address line 2, geolocation, and zip codes in both billing and shipping addresses / Email / Phone"

### Access by app type (direct quotes, table cells verbatim)
| Level | Public app | Custom app | Admin created custom app |
| --- | --- | --- | --- |
| 1 | "Requires review" | "Always available" | "Always available" |
| 2 | "Requires review" | "Always available" | "Varies by plan" (links to help.shopify.com custom-apps#custom-level2-pii-app) |

> [Direct quote] "You don't need to submit a request for review for apps that are installed only on development stores."

### Requirements (headline items, direct quotes)
> [Direct quote] "If you're using only protected customer data, then you must meet the level 1 requirements. If you're using protected customer data including name, address, phone, or email fields, then you must meet all of the level 1 and 2 requirements."

**Level 1 (9):** "Process only the minimum personal data required to provide app functionality to merchants." / "Inform merchants what personal data you process and your reason for processing it." / "Limit your processing of personal data to the stated purposes." / "Where applicable, respect and apply customer consent decisions." / "Where applicable, respect and apply customer decisions to opt out of any data sharing such as a 'data sale' or similar concept under applicable laws or regulations." / "If you use personal data for automated decision-making and those decisions might have legal or significant effects, then you must allow customers to opt out." / "Make privacy and data protection agreements with your merchants." / "Apply retention periods to make sure that personal data isn't kept for longer than needed." / "Encrypt data at rest and in transit."

**Level 2 (7 additional):** "Encrypt your data backups." / "Keep test and production data separate." / "Have a data loss prevention strategy." / "Limit staff access to protected customer data." / "Require strong passwords for staff accounts." / "Keep an access log to protected customer data." / "Implement a security incident response policy."

*(Note: encryption at rest and retention limits are Level 1 obligations; Level 2 adds backup encryption, environment separation, DLP, staff-access limits, strong passwords, access logging, incident response.)*

### Effect on Customer / Order reads (direct quotes)
> "Customers (GraphQL Admin API, Customer Account API): Data that defines facts about a single customer, including name, addresses, email, and phone number."
> "Orders (GraphQL Admin API, Customer Account API): Orders, draft orders, abandoned checkouts, refunds, transactions, and other data that relate to a single customer."
> "After your app is approved to access protected customer data, API requests and webhooks that contain protected resources will return the data requested. Responses will include only approved fields, and unapproved fields will be redacted. GraphQL requests to unapproved types will return an HTTP 200 Ok response with an error message in the errors hash."
> Example error message: "This app is not approved to access the Customer object. See https://partners.shopify.com/123/apps/456/customer_data for more details."

### Data protection review (direct quote)
> "While any app might be selected, data protection reviews will likely focus on apps that have: High number of merchant installs / High volume of customer records / More protected customer fields approved / Long retention of personal data"

## Source 2: shopify.dev — About app distribution
- **URL:** https://shopify.dev/docs/apps/launch/distribution
- **Accessed:** 2026-07-10 — **Status: Accessible**

> [Direct quote, table cells] "Custom distribution — Installed on a single Shopify store, on multiple stores that belong to the same Plus organization or any transfer-disabled development stores — Approval required: No — Can't use the Billing API to charge merchants"
> [Direct quote, table cells] "Shopify admin — Installed on a single Shopify store — Custom — Authenticate in the Shopify admin — Approval required: No"

## Source 3: help.shopify.com — Custom apps (Level 2 PII plan gate)
- **URL:** https://help.shopify.com/en/manual/apps/app-types/custom-apps#custom-level2-pii-app
- **Accessed:** 2026-07-10 — **Status: Partial** (raw fetch Cloudflare-challenged; quotes extracted via rendering tool and reported verbatim — re-verify in browser before treating as Fact)

> [Direct quote per fetch tool] "To access Custom Level 2 PII apps, your store must be on the Grow plan or higher."
> [Direct quote per fetch tool] "If you sign up for or downgrade your plan to either the Basic plan or the Starter plan, then you won't have access to Custom Level 2 Personally Identifiable Information (PII) apps."

<!-- TOPIC: Shopify access scopes (read_customers/write_customers), API versioning cadence and current stable ve -->
# Source capture — Shopify access scopes, API versioning, GraphQL rate limits

**Accessed:** 2026-07-10 (all URLs fetched live via WebFetch; content extracted through an intermediate summarization model — quotes below are as extracted, with two-pass cross-checks where noted)

---

## 1. Access scopes

**URL:** https://shopify.dev/docs/api/usage/access-scopes
**Access status:** Accessible (fetched twice; consistent)

> [Direct quote — authenticated access scopes intro] "Controls access to resources in the GraphQL Admin API, Web Pixel API, and Payments Apps API. Authenticated access is intended for interacting with a store on behalf of a user."

> [Direct quote — table row, Authenticated access scopes] Scope: `read_customers`, `write_customers` — Access: "Customer, Segment, Company, CompanyLocation"

> [Direct quote — table rows, Customer Account API scopes (distinct scope family)] `customer_read_customers`, `customer_write_customers` — "Customer object"; `customer_read_companies`, `customer_write_companies` — "Company object"

Note: page references "API version 2024-10" only in relation to a `write_third_party_fulfillment_orders` change; no page-wide version indicator.

---

## 2. API versioning

**URL:** https://shopify.dev/docs/api/usage/versioning
**Access status:** Accessible (fetched three times; cadence/support quotes identical across passes; no explicit "Latest" label found)

> [Direct quote — cadence] "Shopify releases a new API version every three months at the beginning of the quarter, at 5pm UTC."

> [Direct quote — support window] "Each stable version is supported for a minimum of 12 months, with at least nine months of overlap between consecutive versions."

> [Direct quote — release-schedule table header] "| Stable version | Release date | Accessible until |"

> [Direct quote — key rows] "| 2026-04 | April 1, 2026 | April 16, 2027 15:00 UTC |" · "| 2026-07 | July 1, 2026 | July 16, 2027 15:00 UTC |" · "| 2026-10 | October 1, 2026 | October 16, 2027 15:00 UTC |" · "| 2027-01 | January 1, 2027 | January 16, 2028 15:00 UTC |"

> [Direct quote — release candidate] "Published on the same date as the stable release. For example, when `2026-04` releases on April 1, 2026, the `2026-07` release candidate also becomes available." ... "May include backwards-incompatible changes, so not recommended for production."

> [Direct quote — unsupported version behavior] "If your app targets an inaccessible version, Shopify falls forward and responds using the oldest accessible stable version."

**[Inference]** Latest released stable version as of 2026-07-10 is **2026-07** (newest table row with a past release date; 2026-10 and 2027-01 rows are future-dated). Corroborated by the GraphQL Admin API reference page using `2026-07` in its endpoint URL. The page itself labels no version "Latest".

---

## 3. Rate limits

**URL:** https://shopify.dev/docs/api/usage/limits
**Access status:** Accessible (fetched twice)

> [Direct quote — cost model] "Every field in the schema has an integer cost value assigned to it. The cost of a query is the maximum of possible fields selected."

> [Direct quote — default field costs] "Scalar: 0, Enum: 0, Object: 1, Interface: Maximum of possible selections, Union: Maximum of possible selections, Connection: Sized by `first` and `last` arguments, Mutation: 10"

> [Direct quote — plan limits] "GraphQL Admin API: Calculated query cost | Standard limit: 100 points/second | Advanced Shopify limit: 200 points/second | Shopify Plus limit: 1000 points/second | Shopify for enterprise: 2000 points/second"

> [Direct quote — single-query cap] "A single query may not exceed a cost of 1,000 points, regardless of plan limits."

> [Direct quote — extensions telemetry] "The response includes information about the cost of the request and the state of the throttle. This data is returned under the `extensions` key" — [paraphrase] with `requestedQueryCost`, `actualQueryCost`, and `throttleStatus` (`maximumAvailable`, `currentlyAvailable`, `restoreRate`).

> [Direct quote — Storefront API only, NOT Admin API] "If an API client exceeds this throttle, then a `200 Throttled` error response is returned." (checkout-level throttle section)

**Not on this page:** a THROTTLED error code for the GraphQL Admin API. "429 Too Many Requests" appears only for resource-based limits.

---

## 4. GraphQL Admin API reference (THROTTLED verification)

**URL:** https://shopify.dev/docs/api/admin-graphql
**Access status:** Partial (THROTTLED definition and 200-OK behavior extracted; a THROTTLED-specific JSON sample was not present/extractable)
**API version documented:** 2026-07 (visible in endpoint URL and code examples)

> [Direct quote — error code definition] THROTTLED: "The client has exceeded the rate limit. Similar to 429 Too Many Requests."

> [Direct quote — status code semantics] "Most importantly, the GraphQL API can return a `200 OK` response code in cases that would typically produce 4xx or 5xx errors in REST."

> [Direct quote — sibling error sample showing errors/extensions structure (code is MAX_COST_EXCEEDED, not THROTTLED)]
> ```json
> {
>   "errors": [
>     {
>       "message": "Query cost is 2003, which exceeds the single query max cost limit (1000). ...",
>       "extensions": {
>         "code": "MAX_COST_EXCEEDED",
>         "cost": 2003,
>         "maxCost": 1000,
>         "documentation": "https://shopify.dev/api/usage/limits#rate-limits"
>       }
>     }
>   ]
> }
> ```

**[Inference]** THROTTLED errors surface in the GraphQL response body's `errors[].extensions.code` (per the documented error-sample format above), with HTTP 200 rather than 429 — the THROTTLED-specific body was not directly captured.

<!-- TOPIC: Odoo 19 res.partner model source-level facts (verified against odoo/odoo branch 19.0) -->
# Source capture — Odoo 19.0 `res.partner` (base + mail), accessed 2026-07-10

## 1. `odoo/addons/base/models/res_partner.py` (branch 19.0)
- URL fetched: https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_partner.py (canonical blob: https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/res_partner.py)
- Access status: **Accessible** (HTTP 200, 1267 lines)
- All excerpts below are **direct quotes** (line numbers from the fetched file):

```python
# L184-189
class ResPartner(models.Model):
    _name = 'res.partner'
    _description = 'Contact'
    _inherit = ['format.address.mixin', 'format.vat.label.mixin', 'avatar.mixin', 'properties.base.definition.mixin']
    _order = "complete_name ASC, id DESC"
    _rec_names_search = ['complete_name', 'email', 'ref', 'vat', 'company_registry']

# L215
    parent_id: ResPartner = fields.Many2one('res.partner', string='Related Company', index=True)
# L217
    child_ids: ResPartner = fields.One2many('res.partner', 'parent_id', string='Contact', domain=[('active', '=', True)], context={'active_test': False})
# L251
    active = fields.Boolean(default=True)
# L254-260
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice'),
         ('delivery', 'Delivery'),
         ('other', 'Other'),
        ], string='Address Type',
        default='contact')
# L272
    email = fields.Char()
# L277-284
    is_company = fields.Boolean(string='Is a Company', default=False,
        help="Check if the contact is a company, otherwise it is a person")
    ...
    # company_type is only an interface field, do not use it in business logic
    company_type = fields.Selection(string='Company Type',
        selection=[('person', 'Person'), ('company', 'Company')],
        compute='_compute_company_type', inverse='_write_company_type')
# L326-329 — the ONLY SQL constraint in the file (no _sql_constraints; no unique constraint on email)
    _check_name = models.Constraint(
        "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )",
        "Contacts require a name",
    )
# L1121-1126 (docstring) and L1154-1157 (fallback) of address_get()
    def address_get(self, adr_pref=None):
        """ Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either. """
        ...
        # default to type 'contact' or the partner itself
        default = result.get('contact', self.id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
```
*(Note: docstring mentions type `'default'` but the code falls back to the `'contact'` result or the partner itself — apparent stale docstring.)*

## 2. `addons/mail/models/res_partner.py` (branch 19.0)
- URL fetched: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/mail/models/res_partner.py
- Access status: **Accessible** (HTTP 200, 344 lines). Direct quotes:

```python
# L15-16
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.activity.mixin', 'mail.thread.blacklist']
# L21 (email override adds tracking only — still no uniqueness)
    email = fields.Char(tracking=1)
# L96-105 (find_or_create override)
    def find_or_create(self, email, assert_valid_email=False):
        """ Override to use the email_normalized field. """
        ...
            partners = self.search([('email_normalized', '=', parsed_email_normalized)], limit=1)
```

## 3. `addons/mail/models/mail_thread_blacklist.py` (branch 19.0)
- URL fetched: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/mail/models/mail_thread_blacklist.py
- Access status: **Accessible** (HTTP 200, 131 lines). Direct quotes:

```python
# L29-36
    _name = 'mail.thread.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist mixin'
    _primary_email = 'email'

    email_normalized = fields.Char(
        string='Normalized Email', compute="_compute_email_normalized", compute_sudo=True, store=True,
        help="This field is used to search on email address as the primary email field can contain more than strictly an email address.")
# L50
            record.email_normalized = tools.email_normalize(record[self._primary_email], strict=False)
```

## 4. Odoo 19 ORM reference (official docs)
- URL fetched: https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- Access status: **Accessible** (HTTP 200)
- Direct quote (reserved field `active`): "toggles the global visibility of the record, if active is set to False the record is invisible in most searches and listing."

<!-- TOPIC: Shopify Admin GraphQL API QueryRoot "customers" connection — arguments, CustomerConnection shape, Cu -->
# Source capture — Shopify Admin GraphQL `customers` connection (Task 011 bulk customer import)

Access date: **2026-07-10**. All sources are official Shopify developer documentation (shopify.dev). The `latest` alias resolved to Admin API version **2026-07** on the reference pages at access time.

---

## 1. QueryRoot `customers` query reference

- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/queries/customers
- **Access status:** Accessible (fetched and downloaded raw HTML; facts extracted by direct grep of page content)
- **API version documented:** 2026-07 (page metadata `api_version: 2026-07`)

**Arguments** (complete set per page anchors: `after`, `before`, `first`, `last`, `query`, `reverse`, `sortKey` — no `savedSearchId` in this version):

> [Direct quotes]
> - `first` (Int): "The first `n` elements from the paginated list"
> - `after` (String): "The elements that come after the specified cursor"
> - `query` (String): "A filter made up of terms, connectives, modifiers, and comparators."
> - `sortKey` (CustomerSortKeys, **Default: ID**): "Sort the underlying list using a key. If your query is slow or returns an error, then try specifying a sort key that matches the field used in the search."
> - `reverse` (Boolean, **Default: false**): "Reverse the order of the underlying list."

**Return type:** `CustomerConnection!` with fields `edges` (edge → `node`), `nodes`, `pageInfo`. [Paraphrase from page HTML]

**Page's own pagination example fragment** [direct quote from page example]:

```graphql
pageInfo { hasNextPage endCursor }
```

**Page's own `updated_at` example query** [direct quote]:

```graphql
query { customers(first: 10, query: "updated_at:>2019-12-01") { edges { node { id firstName lastName updatedAt } } } }
```

**`updated_at` query filter** (type: `time`) [direct quote]:

> "The date and time, matching a whole day, when the customer's information was last updated."
> Examples: `updated_at:'2024-01-01T00:00:00Z'`, `updated_at:<now`, `updated_at:<=2024`

Other filter fields listed on the page [paraphrase]: accepts_marketing, country, customer_date, email, first_name, id, last_abandoned_order_date, last_name, order_date, orders_count, phone, state, tag, tag_not, total_spent.

---

## 2. `CustomerSortKeys` enum reference

- **URL:** https://shopify.dev/docs/api/admin-graphql/latest/enums/CustomerSortKeys
- **Access status:** Accessible (raw HTML downloaded and grepped)
- **API version documented:** 2026-07

**Valid values** [direct quote of value list]: `CREATED_AT`, `ID`, `LOCATION`, `NAME`, `RELEVANCE`, `UPDATED_AT`

> [Direct quotes of descriptions]
> - `UPDATED_AT`: "Sort by the `updated_at` value."
> - `CREATED_AT`: "Sort by the `created_at` value."
> - `ID`: "Sort by the `id` value."
> - `RELEVANCE`: "Sort by relevance to the search terms when the `query` parameter is specified on the connection. Don't use this sort key when no search query is specified."

---

## 3. Search syntax (for `query` argument ranges)

- **URL:** https://shopify.dev/docs/api/usage/search-syntax
- **Access status:** Accessible (raw HTML downloaded and grepped)

> [Direct quote] "The following comparators are supported for search queries:"
> `:` equality · `:<` less-than · `:>` greater-than · `:<=` less-than-or-equal-to · `:>=` greater-than-or-equal-to

> [Direct quote, grammar table `value` row] "Any name, or any quoted string (single or double quotes are both permitted). Date values must be a string surrounded by quotes."

Date/time example on the page [direct quote]: `created_at:>'2020-10-21T23:39:20Z'` (ISO 8601 UTC). AND is implied between space-separated terms [paraphrase]. No `updated_at`-specific example appears on this page; `updated_at` support for customers is confirmed on the customers query reference page (§1).

---

## 4. GraphQL pagination limit

- **URL:** https://shopify.dev/docs/api/usage/pagination-graphql
- **Access status:** Accessible (raw HTML downloaded and grepped)

> [Direct quote] "You can retrieve up to a maximum of 250 resources. If you need to paginate larger volumes of data, then you can perform a bulk query operation using the GraphQL Admin API."

Example on the same page combining `first: 250`, a date-range `query`, and `sortKey` [direct quote]:

```graphql
{ orders(first: 250, query: "created_at:>'2020-10-21'", sortKey: CREATED_AT) { edges { node { id } } } }
```

Note: the 250 limit is documented on this usage page, not on the `customers` query reference page (verified absent there).

---

## Not verified / caveats

- "Matching a whole day" wording in the customers `updated_at` filter description vs timestamp-precision examples — day-granularity behavior unverified (open question; test empirically before relying on fine-grained checkpoints).
- Full `PageInfo` field set (`hasPreviousPage`, `startCursor`) not fetched from its own object page; only `hasNextPage`/`endCursor` verified verbatim in the customers example.

<!-- TOPIC: Odoo 19 sale.order partner behavior (Task 012 boundary evidence) -->
# Source capture — Odoo 19 sale.order partner/address fields (Task 012)

**Accessed:** 2026-07-10 · **Branch:** odoo/odoo `19.0` · All quotes are direct quotes from raw source files fetched via HTTPS (HTTP 200).

## Source 1: `addons/sale/models/sale_order.py`

- **URL fetched:** https://raw.githubusercontent.com/odoo/odoo/19.0/addons/sale/models/sale_order.py
- **Blob equivalent:** https://github.com/odoo/odoo/blob/19.0/addons/sale/models/sale_order.py
- **Access status:** Accessible (HTTP 200, 2301 lines)

**Field definitions (direct quote, lines 64-69 and 153-166):**

```python
partner_id = fields.Many2one(
    comodel_name='res.partner',
    string="Customer",
    required=True, change_default=True, index=True,
    tracking=1,
    check_company=True)
```

```python
partner_invoice_id = fields.Many2one(
    comodel_name='res.partner',
    string="Invoice Address",
    compute='_compute_partner_invoice_id',
    store=True, readonly=False, required=True, precompute=True,
    check_company=True,
    index='btree_not_null')
partner_shipping_id = fields.Many2one(
    comodel_name='res.partner',
    string="Delivery Address",
    compute='_compute_partner_shipping_id',
    store=True, readonly=False, required=True, precompute=True,
    check_company=True,
    index='btree_not_null')
```

**Compute methods (direct quote, lines 400-408):**

```python
@api.depends('partner_id')
def _compute_partner_invoice_id(self):
    for order in self:
        order.partner_invoice_id = order.partner_id.address_get(['invoice'])['invoice'] if order.partner_id else False

@api.depends('partner_id')
def _compute_partner_shipping_id(self):
    for order in self:
        order.partner_shipping_id = order.partner_id.address_get(['delivery'])['delivery'] if order.partner_id else False
```

> Precision note [Fact]: the computes make **two separate** `address_get` calls — `address_get(['invoice'])` and `address_get(['delivery'])` — not one combined `address_get(['invoice','delivery'])` call.

**Adjacent dependency (direct quote, lines 410-414):**

```python
@api.depends('partner_shipping_id', 'partner_id', 'company_id')
def _compute_fiscal_position_id(self):
    """
    Trigger the change of fiscal position when the shipping address is modified.
    """
```

## Source 2: `odoo/addons/base/models/res_partner.py`

- **URL fetched:** https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_partner.py
- **Blob equivalent:** https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/res_partner.py
- **Access status:** Accessible (HTTP 200)

**`address_get` docstring (direct quote, lines 1121-1126):**

```python
def address_get(self, adr_pref=None):
    """ Find contacts/addresses of the right type(s) by doing a depth-first-search
    through descendants within company boundaries (stop at entities flagged ``is_company``)
    then continuing the search at the ancestors that are within the same company boundaries.
    Defaults to partners of type ``'default'`` when the exact type is not found, or to the
    provided partner itself if no type ``'default'`` is found either. """
```

**Fallback implementation (direct quote, lines 1154-1158):**

```python
# default to type 'contact' or the partner itself
default = result.get('contact', self.id or False)
for adr_type in adr_pref:
    result[adr_type] = result.get(adr_type) or default
return result
```

> [Fact] Docstring says fallback type `'default'`; the code actually falls back to the `'contact'` result or the partner itself. Code is authoritative.

## Consequence for the connector [Inference]

- Bound partner with addresses written **on its own fields, no children** → `address_get` finds no `type='invoice'`/`'delivery'` record → falls back to the partner itself → `partner_invoice_id == partner_shipping_id == partner_id`.
- Bound partner with **child partners of `type='invoice'` / `type='delivery'`** → the DFS matches them (`record.type in adr_pref`, lines 1140-1141) → sale.order uses those children as invoice/delivery addresses.
- Because both fields are `store=True, readonly=False, precompute=True` with `@api.depends('partner_id')` only, the connector may also set them **explicitly** on order create to bypass `address_get` resolution, and later partner-child edits do not recompute addresses on existing orders. (Explicit-vals-override-precompute is standard ORM behavior, not re-verified here — see open questions.)
<!-- TOPIC: Shopify app distribution methods (MBQ-05 branch B) -->
## Source capture — Shopify app distribution methods (MBQ-05 branch B)
Accessed: 2026-07-10. All quotes verbatim from the cited official Shopify page as
fetched on the access date; everything else is paraphrase. Quotes extracted via
fetch tooling — spot-check against live pages before promoting to Fact.

### 1. About app distribution — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/distribution
- Access status: Accessible (2026-07-10)
- Quote: "You can't change the distribution method after you select it, so make
  sure that you understand the different capabilities and requirements of each
  type."
- Quote (custom scope): "Installed on a single Shopify store, on multiple stores
  that belong to the same Plus organization or any transfer-disabled development
  stores"
- Quote (custom limitation): "Can't use the Billing API to charge merchants"
- Paraphrase: Comparison table covers public distribution (multiple stores,
  review required, "Must sync certain data with Shopify"), custom distribution
  (no review), and admin-created custom apps (single store; no App Bridge,
  extensions, or Billing API).

### 2. Select a distribution method — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
- Access status: Accessible (2026-07-10)
- Quote (public): "Select this method to make your app public. You can
  distribute or sell your app to many merchants through the Shopify App Store."
- Quote (custom): "Select this method if you've built a custom app that you want
  to distribute to one store or multiple stores on the same Plus organization
  using a link."
- Quote (custom flow): "After you select **Custom distribution**, enter the
  store's myshopify.com or admin.shopify.com domain" ... "Optional: To limit
  your app's installs to one store, uncheck **Allow multi-store installs for one
  Plus organization**" ... "To create the app install link, click **Generate
  link**"
- Quote: "If you create a custom app through the Shopify admin, then you can't
  change the app distribution method."

### 3. App listing visibility — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/distribution/visibility
- Access status: Accessible (2026-07-10)
- Quote: "All apps distributed through the Shopify App Store must have an app
  listing page on the Shopify App Store"
- Paraphrase: Visibility options are "fully visible" (indexed in App Store
  search, category pages, third-party search engines) and "limited visibility"
  (not indexed); both install from a Shopify App Store listing URL. "Unlisted"
  is legacy terminology for what is now limited visibility.

### 4. About the app review process — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/app-store-review/review-process
- Access status: Accessible (2026-07-10)
- Paraphrase: Every app submitted to the Shopify App Store goes through review;
  requirements apply identically to "both fully visible and limited visibility
  public apps" (quoted fragment). Statuses: Draft, Submitted, Paused/Reviewed,
  Published.
- Note: https://shopify.dev/docs/apps/launch/shopify-app-store/app-review
  returns 404 (2026-07-10) — superseded by the URL above.

### 5. Privacy law compliance (mandatory webhooks) — shopify.dev
- URL: https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance
- Access status: Accessible (2026-07-10)
- Paraphrase: Mandatory topics are customers/data_request, customers/redact,
  shop/redact.
- Quote: "Any app that you distribute through the Shopify App Store must respond
  to data subject requests"
- Quote: "The app must implement the mandatory compliance webhooks" / "The app
  must handle `POST` requests with a JSON body and `Content-Type` header set to
  `application/json`."
- Quote: "Complete the action within 30 days of receiving the request."

### 6. App Store requirements — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements
- Access status: Accessible (2026-07-10)
- Quote (1.2): "Apps that use off-platform billing cannot be distributed through
  the Shopify App store, unless you've been notified otherwise by Shopify."
- Paraphrase (1.2.1): App charges must use Shopify App Pricing or the Shopify
  Billing API; a PCI-compliant gateway is allowed for physical goods sold to
  merchants, with other app costs still charged through the Billing API.

### 7. App billing — shopify.dev
- URL: https://shopify.dev/docs/apps/launch/billing
- Access status: Accessible (2026-07-10)
- Quote: "All apps published on the Shopify App Store are required to use a
  Shopify provided billing solution."
- Paraphrase: Options are Shopify App Pricing (managed) and the Billing API;
  manual pricing remains a legacy option for cases not yet covered.

### 8. Protected customer data — shopify.dev (distribution-relevant fragments)
- URL: https://shopify.dev/docs/apps/launch/protected-customer-data
- Access status: Accessible (2026-07-10)
- Paraphrase: Level 1 = customer data excluding name, address, phone, email;
  Level 2 = customer data including those fields (each field requested
  individually).
- Quote (availability table fragments): public app Level 1 and Level 2 "Requires
  review"; custom app Level 1 and Level 2 "Always available"; admin-created
  custom app Level 2 "Varies by plan".
- Quote (dev stores): "If your app is for testing or installed only on a
  development store, you can access customer data in development after Step 5.
  You don't need to submit for review."
- Quote (obligation examples): "Encrypt data at rest and in transit"; "Encrypt
  your data backups"; "Keep test and production data separate"; "Have a data
  loss prevention strategy"; "Limit staff access to protected customer data";
  "Keep an access log to protected customer data"; "Implement a security
  incident response policy".

### 9. Custom apps — help.shopify.com
- URL: https://help.shopify.com/en/manual/apps/app-types/custom-apps
- Access status: Accessible (2026-07-10)
- Quote: "To access Custom Level 2 PII apps, your store must be on the Grow plan
  or higher."
- Quote: "If you sign up for or downgrade your plan to either the Basic plan or
  the Starter plan, then you won't have access to Custom Level 2 Personally
  Identifiable Information (PII) apps."

### 10. Unpublished app deprecation FAQ — help.shopify.com
- URL: https://help.shopify.com/en/partners/help-support/faq/unpublished-app-deprecation
- Access status: Accessible (2026-07-10)
- Quote: "An unpublished app was a type of public app that could be installed by
  one or more merchants."
- Quote: "You can set the visibility of your public app to listed or unlisted."
- Paraphrase: The unpublished (review-free, multi-merchant) app type is
  deprecated; the sanctioned successors are reviewed public apps (listed or
  unlisted/limited visibility) or custom apps.

### 11. Dev Dashboard — shopify.dev
- URL: https://shopify.dev/docs/apps/build/dev-dashboard
- Access status: Accessible (2026-07-10)
- Paraphrase: Org-wide hub for creating, configuring, and managing apps; no
  app-count limit documented.
- Related changelog: https://shopify.dev/changelog/early-access-dev-dashboard
  (entry dated 2025-05-21; Accessible 2026-07-10).

### Dead links recorded
- https://shopify.dev/docs/apps/launch/distribution/distribute-custom-app —
  Blocked (HTTP 404, 2026-07-10); content moved into
  select-distribution-method.
- https://shopify.dev/docs/apps/launch/shopify-app-store/app-review — Blocked
  (HTTP 404, 2026-07-10); content moved to app-store-review/review-process.

### Open questions the official docs do not answer (distribution)
1. Any hard/soft cap on the number of custom-distribution apps one
   partner/Dev Dashboard organization may register — no official number found.
2. Whether the Partner Program Agreement (legal terms, not dev docs) permits
   many per-client custom apps as a commercial substitute for a public app —
   not reviewed here.
3. Exact current app-review SLA/timeline — not stated on the review-process
   page.
4. Whether partner-created custom-distribution apps are affected by the
   merchant-plan gating that applies to admin-created "Custom Level 2 PII
   apps" (the PCD table says custom-app Level 2 is "Always available"; the
   Help Center plan-gate wording targets admin-created apps).
5. What "Must sync certain data with Shopify" (public-app limitation in the
   distribution table) concretely requires for a connector.
6. Whether "limited visibility" listings may be gated (e.g. install-by-
   approval) beyond mere non-indexing.
