"""Write-only credential projections and private credential accessors.

The credential history model keeps lifecycle/audit behavior in its legacy file.
This small inheritance closes every ordinary read/search/export projection and
exposes only narrow in-process accessors to credential services.
"""

from odoo import api, models
from odoo.exceptions import AccessError


# These values may be supplied to the closed mutation surface, but are never
# returned by ordinary ORM reads/exports.  The public model still exposes the
# fields as write-only inputs for the setup/admin service; internal callers use
# the private accessors below instead of ``read``/``search_read``.
CREDENTIAL_SECRET_FIELDS = frozenset(('access_token', 'client_secret'))


class ShopifyConnectorStoreCredentialSecurity(models.Model):
    _inherit = "shopify.connector.store.credential"

    def _assert_secret_fields_not_read(self, field_names):
        """Refuse any ORM projection that could return a raw credential.

        Field groups are useful UI/schema hygiene, but an Administrator still
        satisfies them.  This guard closes the remaining read, search-read,
        and export paths.  It intentionally applies to ``env.su`` too: trusted
        code that needs a secret uses a named private accessor, while a broad
        ``sudo().read()`` must not become a new secret extraction primitive.
        """
        if field_names is None:
            raise AccessError(
                'Raw Shopify credentials are write-only. Use the connector '
                'service or its narrow private accessor.'
            )
        self._assert_secret_projection(field_names)

    @api.model
    def _assert_secret_domain_not_used(self, domain):
        """Refuse secret predicates that would turn search into an oracle.

        A caller must not be able to learn whether a guessed token/secret is
        present merely by observing a search count or an empty/non-empty
        result.  Walk the normal prefix-domain shape recursively so this also
        covers nested ``&``/``|`` expressions and the web client's domain
        payload without attempting to interpret or log the secret value.
        """
        if not isinstance(domain, (list, tuple)):
            return
        if (
            len(domain) >= 2
            and isinstance(domain[0], str)
            and domain[0] in CREDENTIAL_SECRET_FIELDS
        ):
            raise AccessError(
                'Raw Shopify credentials cannot be used in search domains.'
            )
        for item in domain:
            self._assert_secret_domain_not_used(item)

    @api.model
    def _assert_secret_projection(self, field_names):
        """Reject secret names in grouped/web field specifications."""
        if isinstance(field_names, dict):
            field_names = field_names.items()
        if isinstance(field_names, str):
            field_names = (field_names,)
        try:
            field_names = iter(field_names)
        except TypeError:
            return
        for field_name in field_names:
            if isinstance(field_name, tuple) and len(field_name) == 2:
                # A web specification is a mapping; inspect its field name
                # and recurse into its child specification as a defensive
                # measure for nested serializers.
                self._assert_secret_projection(field_name[0])
                self._assert_secret_projection(field_name[1])
                continue
            if isinstance(field_name, dict):
                self._assert_secret_projection(field_name)
                continue
            if not isinstance(field_name, str):
                continue
            # read_group uses ``field:aggregate`` and export/web paths may
            # use a relation slash.  The credential fields are local columns;
            # only the first component can name one of them.
            base_name = field_name.split(':', 1)[0].split('/', 1)[0]
            if base_name in CREDENTIAL_SECRET_FIELDS:
                raise AccessError(
                    'Raw Shopify credentials cannot be projected or grouped.'
                )

    @api.model
    def _search(self, domain, *args, **kwargs):
        self._assert_secret_domain_not_used(domain)
        return super()._search(domain, *args, **kwargs)

    def read(self, fields=None, load='_classic_read'):
        self._assert_secret_fields_not_read(fields)
        return super().read(fields=fields, load=load)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None,
                    order=None):
        self._assert_secret_domain_not_used(domain)
        self._assert_secret_fields_not_read(fields)
        return super().search_read(
            domain=domain, fields=fields, offset=offset, limit=limit,
            order=order,
        )

    def export_data(self, fields_to_export):
        self._assert_secret_fields_not_read(fields_to_export)
        return super().export_data(fields_to_export)

    @api.model
    def read_group(self, domain, fields, groupby, *args, **kwargs):
        self._assert_secret_domain_not_used(domain)
        self._assert_secret_projection(fields)
        self._assert_secret_projection(groupby)
        return super().read_group(
            domain, fields, groupby, *args, **kwargs
        )

    def web_read(self, specification):
        # web_read normally delegates to read(), but keep the boundary here as
        # well: serializers have changed across Odoo releases and this method
        # must never become an accidental bypass of the write-only contract.
        self._assert_secret_projection(specification)
        return super().web_read(specification)

    @api.model
    def web_search_read(self, domain, specification, *args, **kwargs):
        self._assert_secret_domain_not_used(domain)
        self._assert_secret_projection(specification)
        return super().web_search_read(
            domain, specification, *args, **kwargs
        )

    @api.model
    def _get_client_secret(self, store):
        """Return one store's app secret to an internal HMAC service only.

        This is deliberately separate from ORM ``read``/``search_read`` and
        scoped to the already-resolved store, matching ``_get_access_token``.
        It never returns a value to an RPC payload, log, or exception; callers
        use it only for an in-process HMAC comparison or a boolean gate.
        """
        store.ensure_one()
        credential = self._credential_for(store)
        return credential.client_secret if credential else False
