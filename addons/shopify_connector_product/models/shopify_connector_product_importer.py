from odoo import api, fields, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

# Read-only GraphQL query only -- never a mutation (Task 010 is
# import-only; see shopify_connector_product_importer.py's own docstring
# and test_product_import_matching.py's source-level guard). Exact
# field list is an in-task decision (task-010-product-import-proposed.md
# names the exact query/field list "Open" for this task's own final
# prompt to fix, and the final prompt does not fix it either) -- kept
# minimal, limited to the fields this module's own snapshot schema (§7.1/
# §7.2) actually stores. Not verified against a live Shopify endpoint
# this session (VAL-B2 remains explicitly out of scope) -- shaped after
# the already-cited Shopify Product/ProductVariant fields referenced
# elsewhere in this project's accepted architecture docs
# (master-blueprint-product-customer-sale.md §A.1/§A.10/§A.14).
PRODUCT_IMPORT_QUERY = """
query ConnectorProductImport($id: ID!) {
  product(id: $id) {
    id
    title
    status
    featuredImage { url }
    variants(first: 100) {
      nodes {
        id
        sku
        barcode
        price
        compareAtPrice
        selectedOptions { name value }
        image { url }
      }
    }
  }
}
"""


class ShopifyConnectorProductImporter(models.AbstractModel):
    """The read-only product/variant import + matching service (Task 010).

    Stateless (`AbstractModel` -- no table, no new ACL row), mirroring
    `shopify_connector_readiness_check.py`'s/`shopify_connector_job_
    dispatch.py`'s own `AbstractModel` pattern. Every write path here
    creates/updates only this module's own two binding models (and, on a
    confident no-match, a new `product.template`/its Odoo-generated
    singleton `product.product`) -- never a customer/order/inventory/
    fulfillment model, and never a Shopify mutation call (only
    `shopify.connector.api.client.execute()` with a `query` operation).

    Match-key priority (DEC-006; final prompt §8, an in-task conversion
    of the already-accepted DEC-014 point H two-tier gate, not a
    re-derivation of it): existing binding -> SKU (`default_code`) ->
    barcode -> manual review. Ambiguous or blind (no identifier at all)
    conditions never create -- they raise `JobHandlerError` with
    `error_class` `ambiguous_match`/`duplicate_risk`, which the existing,
    unmodified `shopify.connector.job.dispatch._route_failure()` already
    routes to `blocked_manual_review` with the matching
    `manual_review_subreason` (both values are already-accepted members
    of `MANUAL_REVIEW_SUBREASON_SELECTION` -- no new vocabulary is added
    here).

    In-task decision (final prompt §9, "res_model/res_id targeting... the
    implementing session fixes this as its own narrow, named in-task
    decision"): a future enqueue-trigger session should target
    `res_model='shopify.connector.product.template.binding'` (the
    binding model, not the underlying `product.template`) -- the binding
    is the connector-owned identity concept a `product_import_sync` job
    is really about, and, unlike `product.template`, it is guaranteed to
    exist by the time any *second* job for the same Shopify product could
    be enqueued. Task 010 itself does not build that enqueue-trigger
    call site (multi-product enumeration is explicitly out of this job
    type's scope, final prompt §9) -- this decision is recorded here for
    that future session, not implemented by this one.

    Design decision (structural, not a schema change): an ambiguous or
    blind match never creates a binding row, even in `status='review'`,
    because both binding models' `product_template_id`/
    `product_variant_id` are `required=True` -- there is no safe,
    non-guessing Odoo record to point a "pending review" binding at
    without picking one of several plausible candidates, which DEC-006
    forbids ("no automatic name-only matching... ambiguous matches route
    to manual review, never an automatic guess"). The outcome is instead
    represented entirely at the job level (`blocked_manual_review` +
    `manual_review_subreason`), which is what every required test in
    `task-010-product-import-final-implementation-prompt.md` §10 actually
    asserts.

    Design decision (conservative scope, not a schema change): a new
    `product.product` is only ever created as the side effect of
    creating its own brand-new parent `product.template` (Odoo
    auto-generates exactly one singleton variant on `product.template.
    create()` with no attribute lines; the importer binds that
    Odoo-generated variant to the payload's first variant). Any
    additional variant in the same payload, or any variant that would
    need a fresh `product.product` under an *existing* template, is
    *not* auto-created -- Odoo variant generation for a multi-variant
    template is driven by `attribute_line_ids`, which no accepted
    document in this project specifies a mapping for (MBQ-55 §7.2.F
    defers "richer" variant/media modeling); manufacturing that mapping
    here would be inventing behaviour beyond this task's own accepted
    schema. That case instead routes to `blocked_manual_review` /
    `duplicate_risk`, the same conservative outcome as a blind create.
    """

    _name = 'shopify.connector.product.importer'
    _description = 'Shopify Connector Product Importer Service'

    # ------------------------------------------------------------------
    # Public entry point: fetch (read-only) + apply.
    # ------------------------------------------------------------------

    @api.model
    def import_product_sync(self, store, shopify_product_gid):
        """Fetch one Shopify product+variants payload and import it.

        The only method in this file that calls the Shopify API client --
        always with `PRODUCT_IMPORT_QUERY` (a `query` operation, never a
        `mutation`). `_apply_import()` below contains the actual
        matching/creation logic and takes a plain, already-normalized
        payload dict, so it can be unit-tested directly against a fake/
        stub payload with no API-client involvement at all.
        """
        result = self.env['shopify.connector.api.client'].execute(
            store, PRODUCT_IMPORT_QUERY,
            variables={'id': shopify_product_gid},
        )
        payload = self._normalize_payload(result)
        return self._apply_import(store, payload)

    @api.model
    def _normalize_payload(self, result):
        """Raw `execute()` GraphQL response -> the internal payload dict
        shape `_apply_import()` consumes."""
        data = (result or {}).get('data') or {}
        product = data.get('product') or {}
        variant_nodes = (
            (product.get('variants') or {}).get('nodes')
        ) or []
        return {
            'gid': product.get('id'),
            'title': product.get('title'),
            'status': (product.get('status') or '').lower() or None,
            'image_url': (product.get('featuredImage') or {}).get('url'),
            'variants': [
                {
                    'gid': variant.get('id'),
                    'sku': variant.get('sku') or None,
                    'barcode': variant.get('barcode') or None,
                    'price': variant.get('price'),
                    'compare_at_price': variant.get('compareAtPrice'),
                    'option_values': self._format_option_values(
                        variant.get('selectedOptions')
                    ),
                    'image_url': (variant.get('image') or {}).get('url'),
                }
                for variant in variant_nodes
            ],
        }

    @api.model
    def _format_option_values(self, selected_options):
        if not selected_options:
            return None
        return ' / '.join(
            '%s: %s' % (option.get('name'), option.get('value'))
            for option in selected_options
        )

    # ------------------------------------------------------------------
    # Matching / creation logic (pure -- no Shopify call).
    # ------------------------------------------------------------------

    @api.model
    def _apply_import(self, store, payload):
        """Map/create/bind one Shopify product+variants payload.

        Raises `JobHandlerError('ambiguous_match', ...)` or
        `JobHandlerError('duplicate_risk', ...)` -- never creates -- on
        any condition final prompt §8 does not allow an automated create
        for. Returns `{'template_binding': <record>, 'variant_bindings':
        <recordset>}` on success.
        """
        variants = payload.get('variants') or []
        template_binding, template_just_created = (
            self._resolve_template_binding(store, payload)
        )
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        variant_bindings = VariantBinding.browse()
        for index, variant_payload in enumerate(variants):
            auto_variant = False
            if template_just_created and index == 0:
                auto_variant = template_binding.product_template_id.product_variant_id
            variant_binding = self._resolve_variant_binding(
                store, template_binding, variant_payload,
                auto_variant=auto_variant,
            )
            variant_bindings |= variant_binding
        return {
            'template_binding': template_binding,
            'variant_bindings': variant_bindings,
        }

    @api.model
    def _resolve_template_binding(self, store, payload):
        """Match-key sequence for the product-template binding.

        Returns `(binding, just_created)` -- `just_created` tells the
        caller whether this template's Odoo-generated singleton variant
        is available for the payload's first variant (see this class's
        own docstring, "conservative scope" decision).
        """
        TemplateBinding = self.env['shopify.connector.product.template.binding']
        shopify_gid = payload.get('gid')
        snapshot_vals = {
            'shopify_title': payload.get('title') or False,
            'shopify_status': payload.get('status') or False,
            'shopify_primary_image_url': payload.get('image_url') or False,
            'shopify_last_imported_at': fields.Datetime.now(),
        }

        existing = TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', shopify_gid),
        ], limit=1)
        if existing:
            existing.write(snapshot_vals)
            return existing, False

        variants = payload.get('variants') or []
        candidate_ids, match_key = self._find_template_candidates(
            store, variants,
        )
        if len(candidate_ids) > 1:
            raise JobHandlerError(
                'ambiguous_match',
                'Ambiguous product-template match for Shopify product '
                '%s: %d candidate product.template record(s) found.' % (
                    shopify_gid, len(candidate_ids),
                ),
            )
        if len(candidate_ids) == 1:
            binding = TemplateBinding.create(dict(
                snapshot_vals,
                store_id=store.id, shopify_gid=shopify_gid,
                product_template_id=candidate_ids[0],
                match_key=match_key, matched_at=fields.Datetime.now(),
            ))
            return binding, False

        any_identifier_present = any(
            variant.get('sku') or variant.get('barcode')
            for variant in variants
        )
        if not any_identifier_present:
            raise JobHandlerError(
                'duplicate_risk',
                'Blind product-template create blocked for Shopify '
                'product %s: no SKU/barcode identifier present on any '
                'variant.' % (shopify_gid,),
            )

        # Confident no-match (DEC-014 point H) -- eligibility (store
        # connected, product domain enabled) is already enforced by the
        # unmodified core job-start gate before this handler ever runs.
        product_template = self.env['product.template'].create({
            'name': payload.get('title') or shopify_gid,
        })
        binding = TemplateBinding.create(dict(
            snapshot_vals,
            store_id=store.id, shopify_gid=shopify_gid,
            product_template_id=product_template.id,
            matched_at=fields.Datetime.now(),
        ))
        return binding, True

    @api.model
    def _find_template_candidates(self, store, variants):
        """SKU-then-barcode candidate search for the template binding.

        Reads Shopify SKU/barcode from the payload's variants (Shopify
        SKUs/barcodes are variant-scoped, never product-scoped -- MBQ-55
        §9) but resolves candidate `product.template` records (via each
        candidate `product.product`'s own `product_tmpl_id`) -- final
        prompt §8's own "candidate product.product/product.template"
        wording. Already-bound templates for this store are excluded --
        an identity already claimed by a different Shopify product is
        never offered as a candidate for a new one.
        """
        ProductProduct = self.env['product.product']
        bound_template_ids = self.env[
            'shopify.connector.product.template.binding'
        ].search([('store_id', '=', store.id)]).mapped('product_template_id').ids

        sku_values = sorted({
            variant['sku'] for variant in variants if variant.get('sku')
        })
        if sku_values:
            products = ProductProduct.search([
                ('default_code', 'in', sku_values),
                ('product_tmpl_id', 'not in', bound_template_ids),
            ])
            if products:
                return products.mapped('product_tmpl_id').ids, 'sku_reference'

        barcode_values = sorted({
            variant['barcode'] for variant in variants if variant.get('barcode')
        })
        if barcode_values:
            products = ProductProduct.search([
                ('barcode', 'in', barcode_values),
                ('product_tmpl_id', 'not in', bound_template_ids),
            ])
            if products:
                return products.mapped('product_tmpl_id').ids, 'barcode'

        return [], None

    @api.model
    def _resolve_variant_binding(
        self, store, template_binding, variant_payload, auto_variant=False,
    ):
        """Match-key sequence for one product-variant binding.

        `auto_variant`, when truthy, is the Odoo-generated singleton
        `product.product` created alongside a brand-new parent template
        in this same import -- a deterministic association, not a
        "match" (no candidate search is needed or run; `match_key` stays
        unset, since no key was actually checked)."""
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        shopify_gid = variant_payload.get('gid')
        snapshot_vals = {
            'shopify_option_values': variant_payload.get('option_values') or False,
            'shopify_price_snapshot': variant_payload.get('price') or 0.0,
            'shopify_compare_at_price_snapshot': (
                variant_payload.get('compare_at_price') or 0.0
            ),
            'shopify_last_imported_at': fields.Datetime.now(),
            'shopify_primary_image_url': variant_payload.get('image_url') or False,
        }

        existing = VariantBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', shopify_gid),
        ], limit=1)
        if existing:
            existing.write(snapshot_vals)
            return existing

        if auto_variant:
            return VariantBinding.create(dict(
                snapshot_vals,
                store_id=store.id, shopify_gid=shopify_gid,
                product_variant_id=auto_variant.id,
                product_template_binding_id=template_binding.id,
                matched_at=fields.Datetime.now(),
            ))

        candidate_ids, match_key = self._find_variant_candidates(
            store, template_binding.product_template_id.id, variant_payload,
        )
        if len(candidate_ids) > 1:
            raise JobHandlerError(
                'ambiguous_match',
                'Ambiguous product-variant match for Shopify variant '
                '%s: %d candidate product.product record(s) found.' % (
                    shopify_gid, len(candidate_ids),
                ),
            )
        if len(candidate_ids) == 1:
            return VariantBinding.create(dict(
                snapshot_vals,
                store_id=store.id, shopify_gid=shopify_gid,
                product_variant_id=candidate_ids[0],
                product_template_binding_id=template_binding.id,
                match_key=match_key, matched_at=fields.Datetime.now(),
            ))

        # Confident no-match, but no safe, non-guessing Odoo-side variant
        # creation is available under an existing template structure
        # (see this class's own "conservative scope" docstring decision)
        # -- routed exactly like a blind create, never an automated
        # create, whether or not an identifier was actually present.
        raise JobHandlerError(
            'duplicate_risk',
            'Product-variant create blocked for Shopify variant %s: no '
            'existing-binding/SKU/barcode match, and no safe automatic '
            'variant creation is available under an existing '
            'product.template.' % (shopify_gid,),
        )

    @api.model
    def _find_variant_candidates(self, store, template_id, variant_payload):
        """SKU-then-barcode candidate search for the variant binding.

        Scoped to `template_id` -- the already-resolved parent template
        (either matched or just created earlier in this same
        `_apply_import()` call) -- so a variant can never bind to a
        `product.product` belonging to a *different* `product.template`
        than its own declared `product_template_binding_id` points at.
        Already-bound variants for this store are excluded, mirroring
        `_find_template_candidates()`."""
        ProductProduct = self.env['product.product']
        bound_variant_ids = self.env[
            'shopify.connector.product.variant.binding'
        ].search([('store_id', '=', store.id)]).mapped('product_variant_id').ids

        sku = variant_payload.get('sku')
        if sku:
            products = ProductProduct.search([
                ('default_code', '=', sku),
                ('product_tmpl_id', '=', template_id),
                ('id', 'not in', bound_variant_ids),
            ])
            if products:
                return products.ids, 'sku_reference'

        barcode = variant_payload.get('barcode')
        if barcode:
            products = ProductProduct.search([
                ('barcode', '=', barcode),
                ('product_tmpl_id', '=', template_id),
                ('id', 'not in', bound_variant_ids),
            ])
            if products:
                return products.ids, 'barcode'

        return [], None


# ----------------------------------------------------------------------
# Extension seams (final prompt §9). All three declared here only, via
# classic Odoo inheritance -- zero edits to any shopify_connector_core
# file.
# ----------------------------------------------------------------------

class ShopifyConnectorJobProductExtension(models.Model):
    """Seams 1+2: register `product_import_sync` and gate it on
    `product_domain_enabled`."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[('product_import_sync', 'Product Import Sync')],
        ondelete={'product_import_sync': 'cascade'},
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        """Maps `product_import_sync` -> `product_domain_enabled`;
        preserves `super()` for every other `job_type` unchanged (never
        removes or overrides an already-mapped value, per the base
        method's own docstring contract)."""
        if job_type == 'product_import_sync':
            return 'product_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


class ShopifyConnectorJobDispatchProductExtension(models.AbstractModel):
    """Seam 3: register the `product_import_sync` handler."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        handlers['product_import_sync'] = self._handle_product_import_sync
        return handlers

    @api.model
    def _handle_product_import_sync(self, job):
        """Import one Shopify product (+ its variants) for `job`.

        Reads only `job.store_id`/`job.shopify_target_gid` -- the
        importer's own `import_product_sync()` performs the one
        read-only Shopify call and the matching/creation logic. Any
        `JobHandlerError` it raises propagates unchanged to the
        dispatcher's own `_invoke_handler()`, which already routes it
        via `_route_failure()` -- no duplicate routing logic here.
        """
        self.env['shopify.connector.product.importer'].import_product_sync(
            job.store_id, job.shopify_target_gid,
        )
