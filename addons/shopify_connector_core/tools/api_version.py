"""The single place this connector states which Shopify API version it speaks.

Control-room ruling, 2026-07-26 (binding): the connector must send Admin
GraphQL requests to `/admin/api/2026-07/graphql.json`, the version must be a
**centralized, non-user-editable connector constant**, and every response's
`X-Shopify-API-Version` header must be verified to equal it — failing closed
before the response is treated as successful if it does not.

Why a constant and not a store field
------------------------------------

`shopify.connector.store.api_version` exists and is read-only on the store
form, but it is still a column an RPC caller could set. A version is not
per-store configuration: it decides which *schema* every query and mutation
in this codebase is written against. Every operation string here was verified
field-by-field against 2026-07, so a store row that said `2025-01` would not
reconfigure the connector — it would silently point verified requests at an
unverified schema. The endpoint is therefore built from this constant and the
store field is verified against it, never trusted in its place.

Why the response header is checked, and why a mismatch is fatal
---------------------------------------------------------------

Shopify serves a request made against an unsupported version on a *different*
version and reports which one in `X-Shopify-API-Version`. The previous
behaviour recorded that as `version_fallforward` and continued, which means a
mutation could be built against 2026-07 semantics, executed against another
version's semantics, and reported as success. For a read that is a data-shape
risk; for a mutation against a merchant's catalog it is unacceptable. A
mismatch — or a missing header, which is the same uncertainty without the
evidence — is now a configuration/API-compatibility block raised before any
caller sees a result.
"""

# The exact, verified Admin GraphQL version. Changing this is a deliberate
# act with a research obligation attached: every operation string in this
# repository was field-verified against it, so a bump requires re-verifying
# them and re-running the suites, never a one-line edit.
SHOPIFY_API_VERSION = '2026-07'

# The response header Shopify uses to report the version it actually served.
API_VERSION_RESPONSE_HEADER = 'X-Shopify-API-Version'


def admin_graphql_endpoint(shop_domain):
    """The one place an Admin GraphQL URL is constructed.

    HTTPS and the pinned version are structural here rather than
    caller-supplied, so no call site can accidentally address another
    version or another scheme.
    """
    return 'https://%s/admin/api/%s/graphql.json' % (
        shop_domain, SHOPIFY_API_VERSION,
    )
