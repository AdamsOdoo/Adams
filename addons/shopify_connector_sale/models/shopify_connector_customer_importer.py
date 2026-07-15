import json

from odoo import api, fields, models
from odoo.tools import email_normalize

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

# Read-only GraphQL query only -- never a mutation (Task 011 is
# import-only). The exact field list fixed by final prompt §9: id,
# firstName, lastName, displayName, defaultEmailAddress.emailAddress,
# defaultPhoneNumber.phoneNumber, defaultAddress (address1/address2/
# city/zip/provinceCode/countryCodeV2), updatedAt -- nothing else. The
# deprecated email/phone/addresses fields must never appear here.
CUSTOMER_IMPORT_QUERY = """
query ConnectorCustomerImport($id: ID!) {
  customer(id: $id) {
    id
    firstName
    lastName
    displayName
    defaultEmailAddress { emailAddress }
    defaultPhoneNumber { phoneNumber }
    defaultAddress { address1 address2 city zip provinceCode countryCodeV2 }
    updatedAt
  }
}
"""


class ShopifyConnectorCustomerImporter(models.AbstractModel):
    """The read-only customer import and matching service (Task 011).

    Stateless, an AbstractModel with no table and no new ACL row,
    mirroring shopify_connector_product_importer.py's own pattern.
    Every write path here creates or updates only this module's own
    binding model, plus, on a confident no-match, a new res.partner. It
    never touches an order, product, inventory, or fulfillment model,
    and it never issues a Shopify mutation call, only
    shopify.connector.api.client.execute_business() with a query
    operation.

    Match-key priority (final prompt §8.1, D1): existing binding, then
    email, then manual review. Email is the sole automatic match key --
    phone and name are never fallback automatic keys. Ambiguous, blind
    (missing/empty/unnormalizable email), binding-conflict, and
    archived-only-match conditions never create a partner or a binding
    row -- they raise JobHandlerError with the matching error class,
    which the existing, unmodified
    shopify.connector.job.dispatch._route_failure() already routes to
    blocked_manual_review with the matching manual_review_subreason. No
    new vocabulary is added here.

    Critical recall-safety rule (D1 rule 2, control-room review comment
    4932704451): candidate discovery never uses a narrowing prefilter
    that could exclude a partner whose normalized email equals the
    incoming normalized email. Odoo partner emails may be stored in
    display-name/wrapped/mixed-case forms (e.g. "Jane Doe"
    <Jane.DOE@Example.COM>) that normalize to the same bare address.
    Task 011B (D-011B-1/D-011B-2) preserves that recall while removing
    the former O(n) full scan: candidacy is now decided by a btree-
    indexed equality search on the connector-owned stored column
    `res.partner.shopify_connector_email_normalized`, which holds exactly
    `odoo.tools.email_normalize(email, strict=False)` for each partner --
    the same normalizer, applied identically on both the stored (partner)
    side and the incoming side. The resulting candidate sets are provably
    identical to the removed full scan (the equivalence backstop in
    `test_customer_matching_scalability.py`), applied identically to the
    active-candidate search and the archived-inclusive search.

    In-task decision, per final prompt §9's own allowance: the dispatch
    handler below does not populate job.res_model/res_id after a
    successful bind, mirroring Task 010's own recorded choice
    (validation results §C.1) -- multi-customer enumeration/enqueue-
    trigger call sites are out of this job type's scope, so no code path
    in this task ever creates a job that would need that targeting. The
    binding model (shopify.connector.customer.binding, not the
    underlying res.partner) remains the fixed choice for a future
    enqueue-trigger session, for the same reason Task 010 fixed it for
    the product domain: it is the connector-owned identity concept the
    job is really about, and it is guaranteed to exist once a bind
    succeeds.
    """

    _name = 'shopify.connector.customer.importer'
    _description = 'Shopify Connector Customer Importer Service'

    # ------------------------------------------------------------------
    # Public entry point: fetch (read-only) + apply.
    # ------------------------------------------------------------------

    @api.model
    def import_customer_sync(self, store, shopify_customer_gid, job=False):
        """Fetch one Shopify customer payload and import/match it.

        The only method in this file that calls the Shopify API client.
        The single read-only Admin GraphQL customer call
        (`CUSTOMER_IMPORT_QUERY`, a `query` operation, never a
        `mutation`), the payload normalization, and the entire local
        matching/creation reconciliation all run inside **one** CORE-R2
        `execute_business()` admission lease (AR-047): the connector-owned,
        admission-gated context manager on
        `shopify.connector.api.client`. That single lease covers the
        network call (issued in `__enter__`), `_normalize_payload()`, the
        full `_apply_import()` reconciliation, and a final
        `self.env.flush_all()` that materializes the reconciliation SQL in
        the current transaction; the lease releases only when the `with`
        block exits, after reconciliation. There is **no explicit commit**
        -- the outer dispatcher/RPC transaction boundary commits naturally
        after the handler returns -- and **no legacy value-returning
        `execute()` fallback path remains**.

        `_apply_import()` below contains the actual matching/creation
        logic and takes a plain, already-normalized payload dict, so it
        can still be unit-tested directly against a fake/stub payload with
        no API-client involvement at all.

        `job`, supplied by the dispatcher path
        (`_handle_customer_import_sync()` below), is now load-bearing in
        two ways: it is the admission credential `execute_business()`
        requires (a business Shopify call is refused at admission without
        a valid job), and it is the thread through which an unresolved
        country/state code can append an informational job-log note
        (§8.3).

        A `ShopifyClientError` raised at admission (a missing/empty
        credential) or by the transport/normalization is re-raised as
        `JobHandlerError(exc.error_class, exc.reason,
        exc.technical_detail)`, preserving its DEC-009 error class through
        the dispatcher's own `_route_failure()`. A fail-closed admission
        refusal (`ShopifyQuiescedError`) is deliberately **not** caught
        here: it propagates uncaught so the CORE-R2 dispatcher can route
        it through the disconnect-quiescence (SRR-03) contract.
        """
        client = self.env['shopify.connector.api.client']
        try:
            with client.execute_business(
                job, store, CUSTOMER_IMPORT_QUERY,
                variables={'id': shopify_customer_gid},
            ) as result:
                payload = self._normalize_payload(result)
                outcome = self._apply_import(store, payload, job=job)
                # Materialize the pending reconciliation SQL in the current
                # transaction before the lease releases on context exit --
                # a flush, never a commit (the dispatcher/RPC boundary
                # commits later, after this handler returns).
                self.env.flush_all()
                return outcome
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class, exc.reason, exc.technical_detail,
            ) from exc

    @api.model
    def _normalize_payload(self, result):
        """Raw `execute_business()` GraphQL response -> the internal
        payload dict shape `_apply_import()` consumes.

        Reads only the fields `CUSTOMER_IMPORT_QUERY` requests. A
        `defaultAddress.company` value, if Shopify ever returned one,
        would simply not be read here -- this method never extracts a
        `company` key, so it can never reach `_create_partner()` (D4:
        `MailingAddress.company` is never queried/mapped/stored).
        """
        data = (result or {}).get('data') or {}
        customer = data.get('customer') or {}
        email_node = customer.get('defaultEmailAddress') or {}
        phone_node = customer.get('defaultPhoneNumber') or {}
        address_node = customer.get('defaultAddress')
        address = None
        if address_node:
            address = {
                'address1': address_node.get('address1'),
                'address2': address_node.get('address2'),
                'city': address_node.get('city'),
                'zip': address_node.get('zip'),
                'province_code': address_node.get('provinceCode'),
                'country_code': address_node.get('countryCodeV2'),
            }
        return {
            'gid': customer.get('id'),
            'first_name': customer.get('firstName'),
            'last_name': customer.get('lastName'),
            'display_name': customer.get('displayName'),
            'email': email_node.get('emailAddress') or None,
            'phone': phone_node.get('phoneNumber') or None,
            'address': address,
        }

    @api.model
    def _validate_payload(self, payload):
        """Classified, operator-readable validation for a malformed
        Shopify customer payload -- runs before any write.

        A missing customer node and a present-but-GID-less customer node
        are indistinguishable once normalized (both collapse to a falsy
        `payload['gid']`), and both are equally malformed. A null
        `defaultEmailAddress`/`defaultAddress` is NOT malformed -- both
        are tolerated per §8.1(5)/§8.3 and routed through the ordinary
        matching rules below, never through this validation.
        """
        if not payload.get('gid'):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Malformed Shopify customer payload: missing customer '
                'node or customer GID.',
            )

    # ------------------------------------------------------------------
    # Matching / creation logic (pure -- no Shopify call).
    # ------------------------------------------------------------------

    @api.model
    def _apply_import(self, store, payload, job=False):
        """Validate, then match/create/bind one Shopify customer payload
        atomically. Returns the (possibly newly created)
        `shopify.connector.customer.binding` record on success, or
        raises a classified `JobHandlerError` -- never creates a partner
        or a binding row on any of the blocked paths (§8.1).

        `job` is optional and defaults to `False` -- direct calls (as
        every test in this module makes) remain fully usable with no
        job context; it is threaded through only so the dispatcher path
        can append an informational job-log note on an unresolved
        country/state code (§8.3, see `_log_unresolved_address_code()`).
        """
        self._validate_payload(payload)
        with self.env.cr.savepoint():
            return self._resolve_customer_binding(store, payload, job=job)

    @api.model
    def _resolve_customer_binding(self, store, payload, job=False):
        """The full D1 match sequence, in order: existing binding ->
        email normalization -> exactly-one-active-candidate bind
        (guarded against a binding conflict) -> archived-match check ->
        confident-no-match create -- with ambiguous/missing-email/
        archived-match routed to blocked_manual_review at every step
        that is not a safe automatic outcome."""
        CustomerBinding = self.env['shopify.connector.customer.binding']
        shopify_gid = payload.get('gid')
        snapshot_vals = {
            'shopify_display_name': payload.get('display_name') or False,
            'shopify_email_snapshot': payload.get('email') or False,
            'shopify_phone_snapshot': payload.get('phone') or False,
            'shopify_last_imported_at': fields.Datetime.now(),
        }

        # Rule 1: existing binding always checked first.
        existing = CustomerBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', shopify_gid),
        ], limit=1)
        if existing:
            existing.write(snapshot_vals)
            return existing

        # Rule 2: normalize the incoming email. Missing/empty/
        # unnormalizable -> rule 5 (never an automated create).
        normalized_incoming = self._normalize_incoming_email(
            payload.get('email')
        )
        if not normalized_incoming:
            raise JobHandlerError(
                'duplicate_risk',
                'Blind customer create blocked for Shopify customer %s: '
                'no usable email address on the incoming payload.' % (
                    shopify_gid,
                ),
            )

        # Rule 6: more than one active candidate -> ambiguous, no row.
        active_candidates = self._find_active_candidates(normalized_incoming)
        if len(active_candidates) > 1:
            raise JobHandlerError(
                'ambiguous_match',
                'Ambiguous customer match for Shopify customer %s: %d '
                'candidate res.partner record(s) found.' % (
                    shopify_gid, len(active_candidates),
                ),
                technical_detail=self._build_candidate_payload(
                    shopify_gid, normalized_incoming, active_candidates,
                ),
            )

        # Rule 3: exactly one active candidate -> bind, unless it is
        # already bound to a different Shopify Customer in this store.
        if len(active_candidates) == 1:
            partner = active_candidates
            conflicting = CustomerBinding.search([
                ('store_id', '=', store.id), ('partner_id', '=', partner.id),
            ], limit=1)
            if conflicting:
                raise JobHandlerError(
                    'binding_conflict',
                    'Customer bind blocked for Shopify customer %s: the '
                    'matched res.partner is already bound to a '
                    'different Shopify customer (%s) for this store.' % (
                        shopify_gid, conflicting.shopify_gid,
                    ),
                )
            return CustomerBinding.create(dict(
                snapshot_vals,
                store_id=store.id, shopify_gid=shopify_gid,
                partner_id=partner.id,
                match_key='email', matched_at=fields.Datetime.now(),
            ))

        # Rule 7: zero active candidates -- check archived matches
        # before any create is even considered.
        archived_candidates = self._find_archived_candidates(
            normalized_incoming
        )
        if archived_candidates:
            raise JobHandlerError(
                'duplicate_risk',
                'Customer create blocked for Shopify customer %s: %d '
                'archived res.partner record(s) match the incoming '
                'email -- routed to manual review rather than creating '
                'a duplicate or un-archiving.' % (
                    shopify_gid, len(archived_candidates),
                ),
                technical_detail=self._build_candidate_payload(
                    shopify_gid, normalized_incoming, archived_candidates,
                ),
            )

        # Rule 4: confident no-match -- eligibility (store connected,
        # sale domain enabled) is already enforced by the unmodified
        # core job-start gate before this handler ever runs.
        partner = self._create_partner(shopify_gid, payload, job=job)
        return CustomerBinding.create(dict(
            snapshot_vals,
            store_id=store.id, shopify_gid=shopify_gid,
            partner_id=partner.id,
            match_key='email', matched_at=fields.Datetime.now(),
        ))

    @api.model
    def _normalize_incoming_email(self, raw_email):
        if not raw_email:
            return False
        return email_normalize(raw_email, strict=False) or False

    @api.model
    def _find_active_candidates(self, normalized_incoming):
        """Recall-safe active-candidate search (D1 rule 2), Task 011B
        indexed form: a btree-indexed equality search on the connector-
        owned stored column `shopify_connector_email_normalized` replaces
        the former full scan of every partner carrying an email plus a
        per-record Python `email_normalize()` compare. That column holds
        exactly `email_normalize(partner.email, strict=False)`, so this
        indexed lookup returns the identical candidate set (recall-
        equivalence proven in `test_customer_matching_scalability.py`).
        `search()` excludes archived partners by default, giving exactly
        the "active = True" candidate set rule 3/6 require."""
        Partner = self.env['res.partner']
        return Partner.search([
            ('shopify_connector_email_normalized', '=', normalized_incoming),
        ])

    @api.model
    def _find_archived_candidates(self, normalized_incoming):
        """Recall-safe archived-inclusive search (D1 rule 7), run only
        after the active-candidate count is zero -- Task 011B indexed
        form: the same btree-indexed equality on
        `shopify_connector_email_normalized`, with `active_test=False`
        plus an explicit `('active', '=', False)` so only archived
        partners are returned. Same stored normalizer, same recall as the
        active search above, and no full partner scan."""
        Partner = self.env['res.partner']
        return Partner.with_context(active_test=False).search([
            ('shopify_connector_email_normalized', '=', normalized_incoming),
            ('active', '=', False),
        ])

    @api.model
    def _build_candidate_payload(self, shopify_gid, normalized_incoming, candidates):
        """The exact §8.2 JSON shape (D2) -- capped at the first 20
        candidates by partner_id ascending; candidate_count always
        carries the true total. Minimum disambiguation set only (id,
        display name, email, active) -- no phone, no address, no order
        data."""
        ordered = candidates.sorted(key=lambda partner: partner.id)
        return json.dumps({
            'kind': 'customer_ambiguous_match_candidates',
            'shopify_customer_gid': shopify_gid,
            'incoming_email_normalized': normalized_incoming,
            'candidate_count': len(candidates),
            'candidates': [
                {
                    'partner_id': partner.id,
                    'display_name': partner.display_name,
                    'email': partner.email,
                    'active': partner.active,
                }
                for partner in ordered[:20]
            ],
        })

    # ------------------------------------------------------------------
    # Partner creation (§8.3 address mapping, §8.4 person-only).
    # ------------------------------------------------------------------

    @api.model
    def _create_partner(self, shopify_gid, payload, job=False):
        """Create a new res.partner for a confident no-match (rule 4).

        Always a person: `is_company` is never set (default `False`
        stands) -- D4. Address fields are written only here, on create,
        from `defaultAddress` only (§8.3) -- never on an existing
        matched partner, never a child partner. Country/state are
        lookup-only (never created); an unresolvable code simply leaves
        that field empty -- address resolution failures never fail the
        import and never invent records. When a code was provided but
        could not be resolved, and this call runs through the
        dispatcher's job context, an informational job-log note is
        appended (`_log_unresolved_address_code()` below) -- direct
        calls with no `job` skip the note, the field is still left
        empty either way.
        """
        vals = {
            'name': payload.get('display_name') or shopify_gid,
            'email': payload.get('email'),
        }
        address = payload.get('address')
        if address:
            vals['street'] = address.get('address1') or False
            vals['street2'] = address.get('address2') or False
            vals['city'] = address.get('city') or False
            vals['zip'] = address.get('zip') or False
            country_code = address.get('country_code')
            country = self._resolve_country(country_code)
            if country:
                vals['country_id'] = country.id
                province_code = address.get('province_code')
                state = self._resolve_state(country, province_code)
                if state:
                    vals['state_id'] = state.id
                elif province_code:
                    self._log_unresolved_address_code(
                        job, 'province_code', province_code,
                    )
            elif country_code:
                self._log_unresolved_address_code(
                    job, 'country_code', country_code,
                )
        return self.env['res.partner'].create(vals)

    @api.model
    def _resolve_country(self, country_code):
        if not country_code:
            return False
        return self.env['res.country'].search(
            [('code', '=', country_code)], limit=1,
        )

    @api.model
    def _resolve_state(self, country, province_code):
        if not province_code:
            return False
        return self.env['res.country.state'].search([
            ('country_id', '=', country.id), ('code', '=', province_code),
        ], limit=1)

    @api.model
    def _log_unresolved_address_code(self, job, kind, code):
        """Informational note for an unresolvable country/state code
        (§8.3) -- appended only when `_create_partner()` runs through
        the dispatcher's job context (`job` truthy); a direct
        `_apply_import(store, payload)` call with no job continues to
        skip it, exactly as before this note existed. Uses only the
        existing, sanctioned `job.log._system_append()` path -- no new
        field, no core edit, no server log write.

        Kept minimal and operator-safe: the human-readable `message`
        never names the specific code, the partner, or any address/
        phone value -- only that a code-based lookup was skipped. The
        bare code itself (a short country/region code, never PII, never
        a full address, never phone data) is carried in
        `technical_detail`, the field this project's own convention
        already reserves for structured/diagnostic detail.
        """
        if not job:
            return
        label = 'country' if kind == 'country_code' else 'province/state'
        self.env['shopify.connector.job.log']._system_append(
            job, 'note',
            'Customer import: an unresolvable %s code left the '
            'corresponding partner field empty; no partner field was '
            'invented and no country/state record was created.' % (
                label,
            ),
            technical_detail='%s=%s' % (kind, code),
        )


# ----------------------------------------------------------------------
# Extension seams (final prompt §9). All three declared here only, via
# classic Odoo inheritance -- zero edits to any shopify_connector_core
# file.
# ----------------------------------------------------------------------

class ShopifyConnectorJobCustomerExtension(models.Model):
    """Seams 1+2: register `customer_import_sync` and gate it on
    `sale_domain_enabled`."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[('customer_import_sync', 'Customer Import Sync')],
        ondelete={
            'customer_import_sync': lambda recs: recs._reassign_to_historic_job_type(),
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        """Maps `customer_import_sync` -> `sale_domain_enabled`;
        preserves `super()` for every other `job_type` unchanged (never
        removes or overrides an already-mapped value, per the base
        method's own docstring contract)."""
        if job_type == 'customer_import_sync':
            return 'sale_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


class ShopifyConnectorJobDispatchCustomerExtension(models.AbstractModel):
    """Seam 3: register the `customer_import_sync` handler."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        handlers['customer_import_sync'] = self._handle_customer_import_sync
        return handlers

    @api.model
    def _get_replay_policies(self):
        """`customer_import_sync` is a Shopify *read* (`import_customer_sync`
        issues no mutation) -- replaying it has no Shopify-side effect, so
        it is declared `remote_read_replay_safe` (DEC-031 Layer 1, AR-048)."""
        policies = dict(super()._get_replay_policies())
        policies['customer_import_sync'] = REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        return policies

    @api.model
    def _handle_customer_import_sync(self, job):
        """Import one Shopify customer for `job`.

        Reads only `job.store_id`/`job.shopify_target_gid` -- the
        importer's own `import_customer_sync()` performs the one
        read-only Shopify call and the matching/creation logic. Any
        `JobHandlerError` it raises propagates unchanged to the
        dispatcher's own `_invoke_handler()`, which already routes it
        via `_route_failure()` -- no duplicate routing logic here.

        `job` itself is also passed through so an unresolved country/
        state code (§8.3) can append an informational job-log note via
        the existing sanctioned path -- the only reason this handler
        now threads `job` into the importer at all.
        """
        self.env['shopify.connector.customer.importer'].import_customer_sync(
            job.store_id, job.shopify_target_gid, job=job,
        )
