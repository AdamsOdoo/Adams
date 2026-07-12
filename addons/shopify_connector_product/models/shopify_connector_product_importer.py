import base64
import hashlib
import os
import tempfile
from contextlib import ExitStack
from urllib.parse import urljoin, urlsplit

import requests
from PIL import Image

from odoo import api, fields, models
from odoo.tools import float_compare, float_round

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

# Read-only GraphQL query only -- never a mutation (Task 010B remains
# import-only; see test_product_import_matching.py's source-level guard).
# D-010B-1: the extended product query with explicit variant pagination.
# `$cursor` is the in-run pagination cursor only -- it is never persisted
# (PD-5); every page requests `first: 100` explicitly (Shopify documents no
# default connection page size -- captures 2026-07-11 §9 open question 1,
# so `first` is always explicit). `pageInfo { hasNextPage endCursor }`
# drives the handler's page loop until exhaustion.
#
# `inventoryItem { id }` is requested per D-010B-1 but never stored or
# acted upon here -- Task 010B imports no inventory quantity or location
# (the inventory domain gate stays closed). It is read only so the query
# shape matches the accepted packet; no stock.* model is ever touched.
#
# `image { url }` on a variant reads the (deprecated but still available)
# ProductVariant.image field per the accepted packet D-010B-1; the current
# ProductVariant.media connection is a future migration (captures §9). This
# task uses the packet-named field for a read only.
PRODUCT_IMPORT_QUERY = """
query ConnectorProductImport($id: ID!, $cursor: String) {
  product(id: $id) {
    id
    title
    status
    descriptionHtml
    vendor
    productType
    tags
    updatedAt
    featuredImage { url }
    options {
      id
      name
      position
      optionValues {
        id
        name
      }
    }
    variants(first: 100, after: $cursor) {
      nodes {
        id
        sku
        barcode
        price
        compareAtPrice
        selectedOptions { name value }
        image { url }
        inventoryItem { id }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

# The exact four Shopify `Product.status` enum values this module's own
# `shopify_status` Selection field accepts (must stay in sync with
# `shopify_connector_product_template_binding.py`'s `shopify_status`
# field) -- any other value is a malformed/unexpected payload.
PRODUCT_STATUS_VALUES = ('active', 'archived', 'draft', 'unlisted')

# D-010B-1: explicit page size, and the defensive accumulated-variant cap.
# The platform ceiling is 2,048 variants/product for all merchants
# (changelog 2025-10-15; captures 2026-07-11 §9); a payload exceeding it is
# unreachable by the platform and signals a schema change -> routed to the
# accepted data-shape/schema-mismatch hold.
VARIANTS_PAGE_SIZE = 100
MAX_ACCUMULATED_VARIANTS = 2048

# The Shopify default single-variant option shape -- a product whose only
# option is `Title` with sole value `Default Title` is a true single-variant
# product and gets no Odoo attribute structure (D-010B-2 special case).
DEFAULT_OPTION_NAME = 'title'
DEFAULT_OPTION_VALUE = 'default title'

# D-010B-6 media download bounds. Named constants, never inlined.
MAX_IMAGE_BYTES = 20 * 1024 * 1024
IMAGE_CONNECT_TIMEOUT_SECONDS = 10
IMAGE_READ_TIMEOUT_SECONDS = 20
IMAGE_MAX_REDIRECTS = 5
IMAGE_CHUNK_BYTES = 65536
_REDIRECT_STATUS = (301, 302, 303, 307, 308)
# Each image is streamed to its own secure on-disk temporary file that is
# CLOSED immediately after download + raster validation; only the path is
# retained in the media plan, and exactly one path is reopened (and closed)
# for its Odoo write (control-room reviews `4950202231` item 5 and
# `4950339305` item 2). This keeps open file handles O(1) and aggregate
# process RAM bounded -- one 64 KiB chunk while streaming, one image while
# writing -- independent of the variant count, with no arbitrary catalog cap.
# The fixed prefix never carries a URL, token, or credential, and the path is
# never surfaced in an operator-facing error.
IMAGE_TEMPFILE_PREFIX = 'shopify_connector_img_'
# Content-type values that are image/* but not a supported raster image --
# rejected explicitly before download (SVG is script-capable markup, not a
# raster). Any content-type containing "svg" is also rejected.
_REJECTED_IMAGE_CONTENT_TYPES = ('image/svg+xml', 'image/svg')
# The raster formats Pillow may report for an accepted image; anything else
# (incl. SVG, which Pillow cannot open) is rejected after the download.
SUPPORTED_RASTER_FORMATS = frozenset({
    'PNG', 'JPEG', 'JPEG2000', 'GIF', 'WEBP', 'BMP', 'TIFF', 'ICO',
})


class ShopifyConnectorProductImporter(models.AbstractModel):
    """The read-only product and variant import and matching service.

    Task 010B completes the accepted DEC-003 product-import scope on top of
    the Task 010 slice: an ordinary Shopify catalog -- multi-option,
    multi-variant (paginated past 100), priced, with primary and variant
    images -- imports into real, complete Odoo products, idempotently and
    atomically, with safe refresh and archived/deleted-remote handling. It
    still issues only `query` operations against Shopify (never a
    `mutation`), and it still touches only this module's binding models,
    the connector lock/settings models, and the core Odoo `product.*`
    models -- never a customer, order, inventory, or fulfilment model.

    Stateless, an AbstractModel with no table and no new ACL row. The one
    seeded singleton lock row (`shopify.connector.attribute.lock`,
    D-010B-2) is the only serialization primitive: it is acquired with the
    verified Odoo 19 `try_lock_for_update()` (FOR UPDATE SKIP LOCKED)
    before any global `product.attribute` resolve/create. The lock is
    transaction-scoped: releasing the per-product savepoint does NOT release
    it -- PostgreSQL holds a `FOR UPDATE` row lock until the outer
    transaction commits or rolls back. It therefore serializes not only the
    attribute critical section but the remaining database work of the
    holding transaction (and, in a `run_drain` batch whose transaction spans
    several jobs, potentially the rest of that batch). This is a
    correctness-first design -- it guarantees two overlapping transactions
    importing the same new option create exactly one attribute (duplicate
    prevention at creation time, not a post-hoc reconciliation sweep). The
    Shopify request and any image download happen BEFORE the lock is
    acquired, never while it is held. The lock-hold duration and its
    throughput impact are an open runtime measurement obligation (Odoo.sh /
    dev-store), not a closed performance claim.

    Match-key priority is unchanged (DEC-006, RA-006): existing binding,
    then SKU (`default_code`), then barcode, then manual review -- never
    name matching, never an automatic guess. Ambiguous/blind conditions
    raise `JobHandlerError` with the accepted error classes; the
    dispatcher's unmodified `_route_failure()` routes them.

    Verified Odoo 19.0 internals used here (checked against the 19.0
    source in-session before use, D-010B-3 build-time verification):
    `product.attribute.create_variant` selection `always`/`dynamic`/
    `no_variant`, default `always`, immutable once used (a write guard in
    `product_attribute.py` raises `UserError` -- so the connector never
    changes an existing attribute's mode); `product.template.
    _create_product_variant(combination, log_warning=False)` returns the
    `product.product` for a `product.template.attribute.value` combination
    and only creates when the template has dynamic attributes and the
    combination is possible; `product.template.attribute.value.price_extra`
    (Float, "Product Price" display digits); `product.template.image_1920`
    (via `image.mixin`) and `product.product.image_variant_1920`;
    `try_lock_for_update(*, allow_referencing=False, limit=None)` returning
    the locked recordset, skipping (never blocking on) already-locked rows.
    """

    _name = 'shopify.connector.product.importer'
    _description = 'Shopify Connector Product Importer Service'

    # ------------------------------------------------------------------
    # Public entry point: paginated fetch (read-only) + apply.
    # ------------------------------------------------------------------

    @api.model
    def import_product_sync(self, store, shopify_product_gid, job=None):
        """Fetch one Shopify product (all variant pages) and import it.

        The only method here that calls the Shopify API client -- always
        with `PRODUCT_IMPORT_QUERY` (a `query`, never a `mutation`), once
        per variant page. A `ShopifyClientError` is re-raised as
        `JobHandlerError` so its accepted DEC-009 error class survives
        (D-010B-12: same job contract, same error taxonomy).

        `job`, when provided by the dispatch handler, is used only to
        append informational job-log notes (media protection,
        price-undecomposable, stale/deletion) -- never to change routing.
        """
        product_node = self._fetch_product_with_all_variant_pages(
            store, shopify_product_gid,
        )
        if product_node is None:
            # D-010B-8: the requested GID returned a null product node.
            return self._handle_absent_product(store, shopify_product_gid, job)
        payload = self._normalize_payload(product_node)
        return self._apply_import(
            store, payload, job=job, requested_gid=shopify_product_gid,
        )

    @api.model
    def _schema_error(self, shopify_gid, detail):
        return JobHandlerError(
            'data_shape_schema_mismatch',
            'Malformed Shopify product payload for %s: %s' % (shopify_gid, detail),
        )

    @api.model
    def _fetch_product_with_all_variant_pages(self, store, shopify_product_gid):
        """Loop `variants(first: 100, after: $cursor)` until exhausted.

        Returns a single raw product node dict with every variant node
        accumulated across pages, or `None` when the product node is null
        on the first page (a possible remote deletion -- handled by the
        caller, D-010B-8). Cursors live only in memory for this call (PD-5).

        Every page is strictly shape-validated (control-room reviews
        `4950202231` item 1 and `4950339305` item 1): `data`, `product`
        (unless null on page one), `variants`, and `pageInfo` must be
        mappings; `variants.nodes` must be a list of mappings; `hasNextPage`
        must be a real Boolean; and `endCursor` must be a non-empty string
        when `hasNextPage` is true. A missing, null, or wrong-type
        `pageInfo`/`hasNextPage` is a schema mismatch -- it is NEVER silently
        treated as a completed single page (which would risk truncating a
        larger product).

        Forward-progress and identity guards prevent a malformed connection
        from looping forever or importing an overlapping page:

        * the pagination cursor must strictly advance -- an `endCursor` equal
          to the cursor just used, or equal to any cursor already seen in
          this call, is rejected (so a response that repeatedly returns
          `hasNextPage=true` with the same cursor and zero nodes cannot loop
          forever);
        * every accumulated variant GID must be unique across all pages
          (a repeated GID within or across pages is a malformed connection,
          not a real 2,049th variant, and is rejected here rather than
          surfacing later as a database constraint error);
        * the returned product `id` on every non-null page must equal the
          requested product GID.

        All violations route to `data_shape_schema_mismatch`, and no product
        or binding is written (this method runs entirely before
        `_apply_import`).
        """
        cursor = None
        product_node = None
        accumulated_variants = []
        seen_cursors = set()
        seen_variant_gids = set()
        while True:
            result = self._execute_query(store, shopify_product_gid, cursor)
            if not isinstance(result, dict):
                raise self._schema_error(
                    shopify_product_gid, 'the GraphQL response was not a mapping.')
            data = result.get('data')
            if not isinstance(data, dict):
                raise self._schema_error(
                    shopify_product_gid, 'the GraphQL "data" was not a mapping.')
            page_product = data.get('product')
            if page_product is None:
                # A null product on the first page is a possible deletion;
                # a null product on a later page is malformed.
                if product_node is None and cursor is None:
                    return None
                raise self._schema_error(
                    shopify_product_gid, 'a null product node mid-pagination.')
            if not isinstance(page_product, dict):
                raise self._schema_error(
                    shopify_product_gid, 'the product node was not a mapping.')
            # Identity guard: every page must be for the requested product.
            if page_product.get('id') != shopify_product_gid:
                raise self._schema_error(
                    shopify_product_gid,
                    'a page returned product GID %r, which does not match the '
                    'requested product.' % (page_product.get('id'),))
            if product_node is None:
                product_node = page_product
            variants_connection = page_product.get('variants')
            if not isinstance(variants_connection, dict):
                raise self._schema_error(
                    shopify_product_gid, 'variants was not a mapping.')
            nodes = variants_connection.get('nodes')
            if not isinstance(nodes, list):
                raise self._schema_error(
                    shopify_product_gid, 'variants.nodes was not a list.')
            for node in nodes:
                if not isinstance(node, dict):
                    raise self._schema_error(
                        shopify_product_gid,
                        'a variants.nodes element was not a mapping.')
                node_gid = node.get('id')
                if not node_gid:
                    raise self._schema_error(
                        shopify_product_gid,
                        'a variant node is missing its Shopify variant GID.')
                if node_gid in seen_variant_gids:
                    raise self._schema_error(
                        shopify_product_gid,
                        'variant GID %r appeared more than once across the '
                        'pagination pages.' % (node_gid,))
                seen_variant_gids.add(node_gid)
            accumulated_variants.extend(nodes)
            if len(accumulated_variants) > MAX_ACCUMULATED_VARIANTS:
                raise self._schema_error(
                    shopify_product_gid,
                    'more than %d variants -- above the documented platform '
                    'ceiling; blocked as a schema-change guard rather than '
                    'imported.' % (MAX_ACCUMULATED_VARIANTS,))
            page_info = variants_connection.get('pageInfo')
            if not isinstance(page_info, dict):
                raise self._schema_error(
                    shopify_product_gid, 'variants.pageInfo was not a mapping.')
            has_next_page = page_info.get('hasNextPage')
            if not isinstance(has_next_page, bool):
                raise self._schema_error(
                    shopify_product_gid,
                    'variants.pageInfo.hasNextPage was not a Boolean.')
            if not has_next_page:
                break
            next_cursor = page_info.get('endCursor')
            if not isinstance(next_cursor, str) or not next_cursor:
                raise self._schema_error(
                    shopify_product_gid,
                    'hasNextPage is true but endCursor is missing or empty -- '
                    'cannot paginate safely.')
            # Forward-progress guard: the cursor must strictly advance and
            # never repeat, or the connection would loop forever.
            if next_cursor == cursor or next_cursor in seen_cursors:
                raise self._schema_error(
                    shopify_product_gid,
                    'pagination did not advance -- endCursor repeated a cursor '
                    'already used in this fetch.')
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        # Rewrite the accumulated variant set onto a single connection dict
        # so `_normalize_payload` consumes one product node uniformly.
        product_node['variants'] = {'nodes': accumulated_variants}
        return product_node

    @api.model
    def _execute_query(self, store, shopify_product_gid, cursor):
        """One read-only GraphQL page call, preserving the client's error
        taxonomy (D-010B-12)."""
        try:
            return self.env['shopify.connector.api.client'].execute(
                store, PRODUCT_IMPORT_QUERY,
                variables={'id': shopify_product_gid, 'cursor': cursor},
            )
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class, exc.reason, exc.technical_detail,
            ) from exc

    # ------------------------------------------------------------------
    # Normalization.
    # ------------------------------------------------------------------

    @api.model
    def _normalize_payload(self, product):
        """Raw accumulated product node -> the internal payload dict."""
        product = product or {}
        variants_connection = product.get('variants') or {}
        variant_nodes = variants_connection.get('nodes') or []
        return {
            'gid': product.get('id'),
            'title': product.get('title'),
            'status': (product.get('status') or '').lower() or None,
            'updated_at': product.get('updatedAt'),
            'image_url': (product.get('featuredImage') or {}).get('url'),
            'options': self._normalize_options(product.get('options')),
            'variants': [
                {
                    'gid': variant.get('id'),
                    'sku': variant.get('sku') or None,
                    'barcode': variant.get('barcode') or None,
                    'price': self._money_to_float(variant.get('price')),
                    'compare_at_price': self._money_to_float(
                        variant.get('compareAtPrice')
                    ),
                    'selected_options': self._normalize_selected_options(
                        variant.get('selectedOptions')
                    ),
                    'option_values': self._format_option_values(
                        variant.get('selectedOptions')
                    ),
                    'image_url': (variant.get('image') or {}).get('url'),
                }
                for variant in variant_nodes
            ],
        }

    @api.model
    def _normalize_options(self, options):
        result = []
        for option in options or []:
            result.append({
                'name': option.get('name'),
                'position': option.get('position') or 0,
                'values': [
                    value.get('name')
                    for value in (option.get('optionValues') or [])
                    if value.get('name') is not None
                ],
            })
        result.sort(key=lambda option: option['position'])
        return result

    @api.model
    def _normalize_selected_options(self, selected_options):
        return [
            {'name': option.get('name'), 'value': option.get('value')}
            for option in (selected_options or [])
        ]

    @api.model
    def _format_option_values(self, selected_options):
        if not selected_options:
            return None
        return ' / '.join(
            '%s: %s' % (option.get('name'), option.get('value'))
            for option in selected_options
        )

    @api.model
    def _money_to_float(self, value):
        """Shopify `Money` is a decimal string ("19.99"); tests may pass a
        Python number. Returns a float or `None` -- never raises on a
        malformed value (that becomes an absent price, snapshot-only)."""
        if value in (None, False, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Payload validation -- runs before any write.
    # ------------------------------------------------------------------

    @api.model
    def _validate_payload(self, payload):
        """Classified validation for a malformed Shopify product payload.

        Raises `JobHandlerError('data_shape_schema_mismatch', ...)` for a
        missing product node/GID, an unexpected product status, an
        accumulated variant set above the 2,048 platform ceiling
        (D-010B-1 defensive cap), or a variant missing its own GID.
        """
        shopify_gid = payload.get('gid')
        if not shopify_gid:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Malformed Shopify product payload: missing product '
                'node or product GID.',
            )
        status = payload.get('status')
        if status is not None and status not in PRODUCT_STATUS_VALUES:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Malformed Shopify product payload for %s: unexpected '
                'product status %r.' % (shopify_gid, status),
            )
        variants = payload.get('variants') or []
        if len(variants) > MAX_ACCUMULATED_VARIANTS:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product %s carries more than %d variants -- above '
                'the documented platform ceiling; blocked as a '
                'schema-change guard.' % (shopify_gid, MAX_ACCUMULATED_VARIANTS),
            )
        for variant in variants:
            if not variant.get('gid'):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Malformed Shopify product payload for %s: a variant '
                    'is missing its own Shopify variant GID.' % (shopify_gid,),
                )

    # ------------------------------------------------------------------
    # Store settings accessors (defaults match the field defaults so a
    # direct _apply_import() unit test with no settings row behaves like a
    # freshly configured store).
    # ------------------------------------------------------------------

    @api.model
    def _store_settings(self, store):
        return self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )

    @api.model
    def _media_enabled(self, settings):
        return settings.product_import_media_enabled if settings else True

    @api.model
    def _refresh_mode(self, settings):
        return settings.product_import_refresh_mode if settings else 'snapshot_only'

    @api.model
    def _attribute_conflict_mode(self, settings):
        return (
            settings.product_import_attribute_conflict_mode
            if settings else 'manual_review'
        )

    @api.model
    def _price_is_shopify_authoritative(self, settings):
        return bool(settings) and settings.price_source_of_truth == 'shopify_authoritative'

    # ------------------------------------------------------------------
    # D-010B-8: remote deletion (null product node for a bound GID).
    # ------------------------------------------------------------------

    @api.model
    def _handle_absent_product(self, store, shopify_product_gid, job):
        """A null Shopify product node. If the GID is already bound this is
        a remote deletion -> mark the binding stale + note; the Odoo
        product is never deleted or archived. With no binding it is a
        first-import of a nonexistent GID -> data-shape error."""
        TemplateBinding = self.env['shopify.connector.product.template.binding']
        binding = TemplateBinding.search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', shopify_product_gid),
        ], limit=1)
        if not binding:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify returned no product for %s and no binding exists '
                '-- treated as a data error, not a deletion.' % (
                    shopify_product_gid,
                ),
            )
        with self.env.cr.savepoint():
            binding.status = 'stale'
            variant_bindings = self.env[
                'shopify.connector.product.variant.binding'
            ].search([('product_template_binding_id', '=', binding.id)])
            variant_bindings.write({'status': 'stale'})
        note = (
            'Shopify product %s no longer exists remotely; its binding is '
            'marked stale for review. The Odoo product is left untouched '
            '(never deleted or archived).' % (shopify_product_gid,)
        )
        self._emit_note(job, note)
        return {
            'template_binding': binding,
            'variant_bindings': variant_bindings,
            'stale': True,
            'notes': [('remote_deleted', note)],
        }

    # ------------------------------------------------------------------
    # Matching / creation logic (pure -- no Shopify call).
    # ------------------------------------------------------------------

    @api.model
    def _apply_import(self, store, payload, job=None, requested_gid=None):
        """Map/create/bind one fully-paginated Shopify product payload.

        Validates first. Then, before any media download or database write,
        an `updatedAt` short-circuit (D-010B-7 / review `4950202231` item 2)
        returns immediately when an active binding already records this
        exact remote `updatedAt`.

        An ARCHIVED product is then routed to `_handle_archived_product`
        BEFORE any media is staged (review `4950339305` item 4): a broken
        image URL must never be able to prevent an archived product from
        being marked stale, and an archived product never triggers a master
        write or a media download.

        Otherwise images are staged over the network (D-010B-10: network out
        of the transaction) each into its own secure temporary file that is
        closed immediately, its path registered with an `ExitStack` that
        unlinks every staged path on any exit path. The entire write
        sequence -- attributes, values, lines, template, variants, prices,
        compare-at, image bytes, bindings, and the `shopify_updated_at`
        stamp -- then runs inside one `self.env.cr.savepoint()` block: any
        failure rolls back every write this call made (so a later-variant
        failure never leaves a partial product and never advances
        `shopify_updated_at`). Informational notes are emitted only after
        the savepoint commits.
        """
        self._validate_payload(payload)
        settings = self._store_settings(store)
        skipped = self._unchanged_short_circuit(store, payload)
        if skipped is not None:
            return skipped
        # D-010B-8 / review `4950339305` item 4: resolve an ARCHIVED product
        # before any media download or master write.
        if payload.get('status') == 'archived':
            return self._handle_archived_product(store, payload, job)
        notes = []
        with ExitStack() as media_stack:
            media = self._prepare_media(store, payload, settings, notes, media_stack)
            with self.env.cr.savepoint():
                result = self._apply_within_savepoint(
                    store, payload, settings, media, notes,
                )
        self._emit_notes(job, notes)
        result['notes'] = notes
        return result

    @api.model
    def _handle_archived_product(self, store, payload, job):
        """Handle an ARCHIVED Shopify product without any media download or
        Odoo master write (D-010B-8 / review `4950339305` item 4).

        A bound archived product marks its template binding and every variant
        binding stale, refreshing only the binding's own audit snapshots; the
        Odoo product, its variants, prices, attributes, values, and images
        are left byte-for-byte untouched, and `_prepare_media` is never
        called (so a broken image URL can never block the stale marking).

        A first-seen, unbound archived product does not create a bare Odoo
        product or a binding: it raises the existing `mapping_missing` class
        (a conservative, never-silent stop-then-retry -- no master data is
        invented for an archived product with no established mapping).
        """
        TemplateBinding = self.env['shopify.connector.product.template.binding']
        binding = TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', payload.get('gid')),
        ], limit=1)
        if not binding:
            raise JobHandlerError(
                'mapping_missing',
                'Shopify product %s is archived and no Odoo mapping/binding '
                'exists for it. The connector does not create Odoo master '
                'data for an archived product; import it while it is active, '
                'or map it manually.' % (payload.get('gid'),),
            )
        with self.env.cr.savepoint():
            binding.write({
                'shopify_title': payload.get('title') or False,
                'shopify_status': payload.get('status') or False,
                'shopify_primary_image_url': payload.get('image_url') or False,
                'shopify_last_imported_at': fields.Datetime.now(),
                'status': 'stale',
            })
            variant_bindings = self.env[
                'shopify.connector.product.variant.binding'
            ].search(
                [('product_template_binding_id', '=', binding.id)], order='id',
            )
            variant_bindings.write({'status': 'stale'})
        note = (
            'Shopify product %s is ARCHIVED; its binding is marked stale for '
            'review. The Odoo product is left untouched (never modified, '
            'archived, or deleted) and no image was downloaded.' % (
                payload.get('gid'),
            )
        )
        self._emit_note(job, note)
        return {
            'template_binding': binding,
            'variant_bindings': variant_bindings,
            'stale': True,
            'notes': [('remote_archived', note)],
        }

    @api.model
    def _unchanged_short_circuit(self, store, payload):
        """D-010B-7 real safe-refresh short-circuit (review `4950202231`
        item 2). When an existing, active template binding already records
        this product's exact non-empty remote `updatedAt`, return the
        binding and its variant bindings (deterministic order) immediately,
        with an explicit `unchanged` indicator and no media download and no
        product/attribute/variant/price/image/binding write. A missing or
        changed `updatedAt` returns `None`, continuing the normal path.

        This is per-import short-circuiting only; enqueue-level dedup
        (`payload_hash = updatedAt`) is an Area-6 integration obligation --
        this task has no enqueue call site and never mutates a running
        job's payload hash.
        """
        updated_at = payload.get('updated_at')
        if not updated_at:
            return None
        TemplateBinding = self.env['shopify.connector.product.template.binding']
        binding = TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', payload.get('gid')),
        ], limit=1)
        if (
            not binding
            or binding.status != 'active'
            or not binding.shopify_updated_at
            or binding.shopify_updated_at != updated_at
        ):
            return None
        variant_bindings = self.env[
            'shopify.connector.product.variant.binding'
        ].search([('product_template_binding_id', '=', binding.id)], order='id')
        return {
            'template_binding': binding,
            'variant_bindings': variant_bindings,
            'unchanged': True,
            'notes': [],
        }

    @api.model
    def _apply_within_savepoint(self, store, payload, settings, media, notes):
        """All database writes for one non-archived product (inside the
        savepoint). An ARCHIVED product never reaches here -- it is routed to
        `_handle_archived_product` before any media download (review
        `4950339305` item 4)."""
        template_binding, source, option_specs = self._resolve_template(
            store, payload, settings, notes,
        )
        variant_bindings = self._resolve_variants(
            store, payload, template_binding, source, option_specs,
            settings, media, notes,
        )
        product_by_gid = {
            binding.shopify_gid: binding.product_variant_id
            for binding in variant_bindings
        }
        self._apply_template_media(
            store, payload, template_binding, source, settings, media, notes,
        )
        self._apply_prices(
            payload, template_binding, source, settings, notes, product_by_gid,
        )
        # D-010B-7: stamp the exact remote updatedAt only after the whole
        # import has succeeded (it is the last write inside the savepoint, so
        # any earlier failure rolls it back and never advances it). A later
        # import with the same updatedAt then short-circuits.
        if payload.get('updated_at'):
            template_binding.shopify_updated_at = payload.get('updated_at')
        return {
            'template_binding': template_binding,
            'variant_bindings': variant_bindings,
        }

    # ------------------------------------------------------------------
    # Template resolution (existing binding -> SKU/barcode candidate ->
    # confident create, with attribute structure on the create path).
    # ------------------------------------------------------------------

    @api.model
    def _resolve_template(self, store, payload, settings, notes):
        """Returns `(binding, source, option_specs)`.

        `source` is one of `'existing_binding'`, `'candidate_match'`,
        `'created_singleton'`, `'created_structured'`. `option_specs` is
        the ordered list of resolved `(option_name, attribute, value_map)`
        used to build the structure on the `created_structured` path, else
        `None`.
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
            return existing, 'existing_binding', None

        variants = payload.get('variants') or []
        candidate_ids, match_key = self._find_template_candidates(store, variants)
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
            return binding, 'candidate_match', None

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

        # Confident no-match (DEC-014 point H). Build the real Odoo
        # structure when the product has real options; otherwise the clean
        # single-variant path (bare template + Odoo-generated singleton).
        # An ARCHIVED product never reaches this method (it is routed to
        # `_handle_archived_product` earlier, review `4950339305` item 4), so
        # no bare Odoo master data is created for a first-seen archived
        # product.
        if self._needs_attribute_structure(payload):
            template, option_specs = self._create_structured_template(
                payload, settings, notes,
            )
            source = 'created_structured'
        else:
            template = self.env['product.template'].create({
                'name': payload.get('title') or shopify_gid,
            })
            option_specs = None
            source = 'created_singleton'
        binding = TemplateBinding.create(dict(
            snapshot_vals,
            store_id=store.id, shopify_gid=shopify_gid,
            product_template_id=template.id,
            matched_at=fields.Datetime.now(),
        ))
        return binding, source, option_specs

    @api.model
    def _needs_attribute_structure(self, payload):
        """True when the product carries real options requiring an Odoo
        attribute structure. False for the Shopify default single-variant
        shape (sole option `Title` / `Default Title`) and for a payload
        with no options at all -- both take the clean singleton path."""
        options = payload.get('options') or []
        if not options:
            return False
        if len(options) == 1:
            option = options[0]
            name = (option.get('name') or '').strip().lower()
            values = [
                (value or '').strip().lower() for value in option.get('values') or []
            ]
            if name == DEFAULT_OPTION_NAME and values == [DEFAULT_OPTION_VALUE]:
                return False
        return True

    @api.model
    def _create_structured_template(self, payload, settings, notes):
        """Build attributes/values/lines and an empty (dynamic) template.

        Acquires the global attribute lock before any `product.attribute`
        resolve/create (D-010B-2). Returns `(template, option_specs)`;
        the template has dynamic attribute lines and, because every
        attribute used is `create_variant='dynamic'`, zero auto-generated
        variants (no phantom cartesian variants) -- variants are
        instantiated explicitly per Shopify variant in `_resolve_variants`.
        """
        conflict_mode = self._attribute_conflict_mode(settings)
        # D-010B-2 serialization: acquire the singleton lock before any
        # global attribute resolve/create. The lock is transaction-scoped --
        # releasing this product's savepoint does NOT release it; PostgreSQL
        # holds it until the outer transaction commits or rolls back, so it
        # serializes the rest of this transaction's DB work as well, not only
        # the attribute critical section (review `4950339305` item 5).
        self.env['shopify.connector.attribute.lock']._acquire_or_raise()

        option_specs = []
        line_commands = []
        for option in payload.get('options') or []:
            option_name = option.get('name')
            attribute = self._resolve_or_create_attribute(option_name, conflict_mode)
            # Build the value set from the declared optionValues plus any
            # value actually used by a variant (D-010B-2 "used value set";
            # union guarantees every sparse combination is representable).
            value_names = list(option.get('values') or [])
            for variant in payload.get('variants') or []:
                for selected in variant.get('selected_options') or []:
                    if (selected.get('name') or '').strip().lower() == (
                        option_name or ''
                    ).strip().lower():
                        if selected.get('value') is not None:
                            value_names.append(selected['value'])
            value_map = {}
            value_records = self.env['product.attribute.value']
            for value_name in value_names:
                key = (value_name or '').strip().lower()
                if key in value_map:
                    continue
                value = self._resolve_or_create_value(attribute, value_name)
                value_map[key] = value
                value_records |= value
            option_specs.append({
                'option_name': option_name,
                'attribute': attribute,
                'value_map': value_map,
            })
            line_commands.append((0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, value_records.ids)],
            }))

        template = self.env['product.template'].create({
            'name': payload.get('title') or payload.get('gid'),
            'attribute_line_ids': line_commands,
        })
        return template, option_specs

    # ------------------------------------------------------------------
    # D-010B-2: attribute / value resolve-or-create (under the lock),
    # with the existing-attribute compatibility gate.
    # ------------------------------------------------------------------

    @api.model
    def _find_attribute_ci(self, name):
        """Case-insensitive exact-name `product.attribute` lookup (active
        and archived), guarded by an exact lower() compare so an `=ilike`
        wildcard character in the name can never widen the match."""
        target = (name or '').strip().lower()
        candidates = self.env['product.attribute'].with_context(
            active_test=False,
        ).search([('name', '=ilike', name)])
        return candidates.filtered(
            lambda attribute: (attribute.name or '').strip().lower() == target
        )

    @api.model
    def _resolve_or_create_attribute(self, name, conflict_mode):
        """Resolve or create the `product.attribute` for a Shopify option.

        Reuse an existing same-name attribute only when its
        `create_variant` mode is `'dynamic'` (compatible with the sparse
        Shopify-variant strategy). An incompatible `'always'`/`'no_variant'`
        same-name attribute is never reused and never mutated: under
        `manual_review` (default) the product routes to
        `blocked_manual_review` / `binding_conflict`; under
        `connector_owned` a distinctly named `"<name> (Shopify)"` dynamic
        attribute is created and used, leaving the merchant's attribute
        untouched.
        """
        existing = self._find_attribute_ci(name)
        compatible = existing.filtered(
            lambda attribute: attribute.create_variant == 'dynamic'
        )
        if compatible:
            return compatible[0]
        if existing:
            # Same-name but incompatible mode -- never reuse, never mutate.
            if conflict_mode == 'connector_owned':
                return self._resolve_or_create_connector_attribute(name)
            raise JobHandlerError(
                'binding_conflict',
                'Shopify option %r maps to an existing Odoo attribute %r '
                'whose variant-creation mode is %r, which cannot represent '
                'a sparse Shopify variant set. Map the option to a '
                'compatible attribute or enable connector-owned attribute '
                'mode -- the import will not guess.' % (
                    name, existing[0].name, existing[0].create_variant,
                ),
            )
        return self.env['product.attribute'].create({
            'name': name,
            'create_variant': 'dynamic',
        })

    @api.model
    def _resolve_or_create_connector_attribute(self, name):
        """The connector-owned `"<name> (Shopify)"` dynamic attribute."""
        connector_name = '%s (Shopify)' % (name,)
        existing = self._find_attribute_ci(connector_name)
        compatible = existing.filtered(
            lambda attribute: attribute.create_variant == 'dynamic'
        )
        if compatible:
            return compatible[0]
        if existing:
            raise JobHandlerError(
                'binding_conflict',
                'The connector-owned attribute %r already exists with an '
                'incompatible variant-creation mode %r.' % (
                    connector_name, existing[0].create_variant,
                ),
            )
        return self.env['product.attribute'].create({
            'name': connector_name,
            'create_variant': 'dynamic',
        })

    @api.model
    def _resolve_or_create_value(self, attribute, value_name):
        """Case-insensitive resolve-or-create of a `product.attribute.value`
        under a resolved attribute (no upstream name uniqueness exists, so
        get-or-create by search is correct -- run under the global lock)."""
        target = (value_name or '').strip().lower()
        candidates = self.env['product.attribute.value'].with_context(
            active_test=False,
        ).search([
            ('attribute_id', '=', attribute.id),
            ('name', '=ilike', value_name),
        ])
        exact = candidates.filtered(
            lambda value: (value.name or '').strip().lower() == target
        )
        if exact:
            return exact[0]
        return self.env['product.attribute.value'].create({
            'name': value_name,
            'attribute_id': attribute.id,
        })

    # ------------------------------------------------------------------
    # Variant resolution.
    # ------------------------------------------------------------------

    @api.model
    def _resolve_variants(
        self, store, payload, template_binding, source, option_specs,
        settings, media, notes,
    ):
        """Resolve/create and bind every Shopify variant.

        Prefetches (D-010B-9 N+1 fix): one map of this product's existing
        variant bindings by GID, the set of already-bound variant ids for
        this store, and one batched SKU and one batched barcode candidate
        search over the whole variant identifier set -- replacing the old
        per-variant full-table exclusion scans.
        """
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        variants = payload.get('variants') or []
        template = template_binding.product_template_id

        prefetch = self._prefetch_variant_matching(store, variants)
        ptav_lookup = None
        if source == 'created_structured':
            ptav_lookup = self._build_ptav_lookup(template)

        variant_bindings = VariantBinding.browse()
        for index, variant_payload in enumerate(variants):
            binding = self._resolve_one_variant(
                store, payload, template_binding, source, option_specs,
                ptav_lookup, prefetch, variant_payload, index, len(variants),
                settings, media, notes,
            )
            variant_bindings |= binding
        return variant_bindings

    @api.model
    def _prefetch_variant_matching(self, store, variants):
        """One-shot prefetch of everything variant matching needs, so no
        per-variant full-table scan runs (D-010B-9)."""
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        variant_gids = [v['gid'] for v in variants if v.get('gid')]
        existing_bindings = VariantBinding.search([
            ('store_id', '=', store.id),
            ('shopify_gid', 'in', variant_gids),
        ]) if variant_gids else VariantBinding.browse()
        existing_by_gid = {b.shopify_gid: b for b in existing_bindings}

        bound_variant_ids = VariantBinding.search(
            [('store_id', '=', store.id)]
        ).mapped('product_variant_id').ids

        skus = sorted({v['sku'] for v in variants if v.get('sku')})
        barcodes = sorted({v['barcode'] for v in variants if v.get('barcode')})
        Product = self.env['product.product']
        sku_candidates = Product.search(
            [('default_code', 'in', skus)]
        ) if skus else Product.browse()
        barcode_candidates = Product.search(
            [('barcode', 'in', barcodes)]
        ) if barcodes else Product.browse()
        return {
            'existing_by_gid': existing_by_gid,
            'bound_variant_ids': set(bound_variant_ids),
            'sku_candidates': sku_candidates,
            'barcode_candidates': barcode_candidates,
        }

    @api.model
    def _build_ptav_lookup(self, template):
        """(attribute id, product.attribute.value id) -> template PTAV."""
        lookup = {}
        for ptav in template.attribute_line_ids.product_template_value_ids:
            lookup[(ptav.attribute_id.id, ptav.product_attribute_value_id.id)] = ptav
        return lookup

    @api.model
    def _resolve_one_variant(
        self, store, payload, template_binding, source, option_specs,
        ptav_lookup, prefetch, variant_payload, index, variant_count,
        settings, media, notes,
    ):
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        shopify_gid = variant_payload.get('gid')
        snapshot_vals = self._variant_snapshot_vals(variant_payload)

        existing = prefetch['existing_by_gid'].get(shopify_gid)
        if existing:
            existing.write(snapshot_vals)
            self._apply_variant_extras(
                existing.product_variant_id, variant_payload, existing,
                source, settings, media, notes,
            )
            return existing

        product = self._resolve_variant_product(
            payload, template_binding, source, option_specs, ptav_lookup,
            prefetch, variant_payload, index, variant_count, notes,
        )
        conflicting = VariantBinding.search([
            ('store_id', '=', store.id),
            ('product_variant_id', '=', product.id),
        ], limit=1)
        if conflicting:
            raise JobHandlerError(
                'duplicate_risk',
                'Product-variant create blocked for Shopify variant %s: '
                'the corresponding Odoo product.product is already bound '
                'to a different Shopify variant (%s) for this store.' % (
                    shopify_gid, conflicting.shopify_gid,
                ),
            )
        match_key = variant_payload.get('_match_key')
        binding = VariantBinding.create(dict(
            snapshot_vals,
            store_id=store.id, shopify_gid=shopify_gid,
            product_variant_id=product.id,
            product_template_binding_id=template_binding.id,
            match_key=match_key or False,
            matched_at=fields.Datetime.now(),
        ))
        self._apply_variant_extras(
            product, variant_payload, binding, source, settings, media, notes,
        )
        return binding

    @api.model
    def _variant_snapshot_vals(self, variant_payload):
        return {
            'shopify_option_values': variant_payload.get('option_values') or False,
            'shopify_price_snapshot': variant_payload.get('price') or 0.0,
            'shopify_compare_at_price_snapshot': (
                variant_payload.get('compare_at_price') or 0.0
            ),
            'shopify_last_imported_at': fields.Datetime.now(),
            'shopify_primary_image_url': variant_payload.get('image_url') or False,
        }

    @api.model
    def _resolve_variant_product(
        self, payload, template_binding, source, option_specs, ptav_lookup,
        prefetch, variant_payload, index, variant_count, notes,
    ):
        """Resolve the exact `product.product` a new Shopify variant binds
        to. Structured create/refresh instantiate the precise combination
        (no cartesian extras, D-010B-3); the singleton/candidate paths keep
        today's deterministic-or-conservative behaviour unchanged."""
        template = template_binding.product_template_id

        if source == 'created_structured':
            return self._instantiate_structured_variant(
                template, option_specs, ptav_lookup, variant_payload,
            )
        if source == 'existing_binding' and template.attribute_line_ids:
            return self._instantiate_refresh_variant(
                template, variant_payload,
            )

        # Singleton / candidate paths (unchanged Task 010 behaviour).
        deterministic = self._resolve_deterministic_variant(
            template_binding, source, variant_count, index,
        )
        if deterministic:
            variant_payload['_match_key'] = None
            return deterministic
        candidate_id, match_key = self._match_variant_candidate(
            template.id, prefetch, variant_payload,
        )
        if candidate_id:
            variant_payload['_match_key'] = match_key
            return self.env['product.product'].browse(candidate_id)
        raise JobHandlerError(
            'duplicate_risk',
            'Product-variant create blocked for Shopify variant %s: no '
            'existing-binding/SKU/barcode match, and no safe automatic '
            'variant creation is available under this product.template.' % (
                variant_payload.get('gid'),
            ),
        )

    @api.model
    def _instantiate_structured_variant(
        self, template, option_specs, ptav_lookup, variant_payload,
    ):
        """Map a Shopify variant's selectedOptions to the template PTAV
        combination and get-or-create exactly that `product.product` via the
        verified dynamic mechanism (`product.template._create_product_
        variant`). Never a cartesian generation, never an index-0 fallback.
        """
        specs_by_option = {
            (spec['option_name'] or '').strip().lower(): spec
            for spec in option_specs
        }
        combination = self.env['product.template.attribute.value']
        for selected in variant_payload.get('selected_options') or []:
            option_key = (selected.get('name') or '').strip().lower()
            value_key = (selected.get('value') or '').strip().lower()
            spec = specs_by_option.get(option_key)
            if not spec:
                raise JobHandlerError(
                    'binding_conflict',
                    'Shopify variant %s references option %r which is not '
                    'among the product options -- cannot map it to a Odoo '
                    'attribute.' % (variant_payload.get('gid'), selected.get('name')),
                )
            value = spec['value_map'].get(value_key)
            ptav = ptav_lookup.get((spec['attribute'].id, value.id)) if value else None
            if not ptav:
                raise JobHandlerError(
                    'binding_conflict',
                    'Shopify variant %s uses option value %r that could '
                    'not be resolved on the Odoo template.' % (
                        variant_payload.get('gid'), selected.get('value'),
                    ),
                )
            combination |= ptav
        return self._create_variant_for_combination(template, combination, variant_payload)

    @api.model
    def _instantiate_refresh_variant(self, template, variant_payload):
        """Resolve a new remote variant against a previously-imported
        structured template (existing binding refresh). Structural additions
        (new variant, additive option value) apply in both refresh modes;
        an incompatible/merchant structure routes to binding_conflict."""
        combination = self.env['product.template.attribute.value']
        for selected in variant_payload.get('selected_options') or []:
            ptav = self._resolve_or_extend_refresh_ptav(
                template, selected, variant_payload,
            )
            combination |= ptav
        return self._create_variant_for_combination(template, combination, variant_payload)

    @api.model
    def _resolve_refresh_line(self, template, option_name, variant_payload):
        """Resolve the one template attribute line a Shopify option refreshes
        into (review `4950202231` item 6).

        A `connector_owned` first import may have mapped Shopify option
        `X` to the Odoo attribute `X (Shopify)`, so refresh must resolve a
        line whose attribute name is exactly `X` OR exactly `X (Shopify)`
        (both case-insensitive). Exactly one candidate -> use it; no
        candidate -> `binding_conflict`; both a plain-`X` and an
        `X (Shopify)` line present -> `binding_conflict` (fail closed, never
        guess). The merchant's original attribute is never modified.
        """
        target = (option_name or '').strip().lower()
        connector_target = ('%s (shopify)' % (option_name or '')).strip().lower()
        lines = template.attribute_line_ids
        exact = lines.filtered(
            lambda ln: (ln.attribute_id.name or '').strip().lower() == target
        )
        connector = lines.filtered(
            lambda ln: (ln.attribute_id.name or '').strip().lower() == connector_target
        )
        candidates = exact | connector
        if not candidates:
            raise JobHandlerError(
                'binding_conflict',
                'Shopify variant %s references option %r absent from the '
                'bound Odoo template structure.' % (
                    variant_payload.get('gid'), option_name,
                ),
            )
        if len(candidates) > 1:
            raise JobHandlerError(
                'binding_conflict',
                'Shopify variant %s option %r maps to more than one template '
                'attribute line (both %r and its connector-owned variant '
                'exist) -- the connector will not guess.' % (
                    variant_payload.get('gid'), option_name, option_name,
                ),
            )
        return candidates

    @api.model
    def _resolve_or_extend_refresh_ptav(self, template, selected, variant_payload):
        """Find the template PTAV for a selectedOption, adding the value to
        the attribute line additively (under the lock) when a new remote
        value appears. Never restructures a merchant's incompatible
        attribute -- that routes to binding_conflict."""
        option_name = selected.get('name')
        value_name = selected.get('value')
        value_key = (value_name or '').strip().lower()
        line = self._resolve_refresh_line(template, option_name, variant_payload)
        ptav = line.product_template_value_ids.filtered(
            lambda p: (p.product_attribute_value_id.name or '').strip().lower() == value_key
        )[:1]
        if ptav:
            return ptav
        if line.attribute_id.create_variant != 'dynamic':
            raise JobHandlerError(
                'binding_conflict',
                'Shopify variant %s needs a new value on attribute %r whose '
                'mode is %r -- the connector will not restructure it.' % (
                    variant_payload.get('gid'), line.attribute_id.name,
                    line.attribute_id.create_variant,
                ),
            )
        # Additive value: create the value and extend the line under the
        # global attribute lock (value creation is a global-attribute write).
        self.env['shopify.connector.attribute.lock']._acquire_or_raise()
        value = self._resolve_or_create_value(line.attribute_id, value_name)
        line.write({'value_ids': [(4, value.id)]})
        # Look the new PTAV up by direct search (not the line's O2m cache,
        # which the write may not have refreshed yet in the same call).
        ptav = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', line.id),
            ('product_attribute_value_id', '=', value.id),
        ], limit=1)
        if not ptav:
            raise JobHandlerError(
                'binding_conflict',
                'Could not extend the Odoo template with option value %r '
                'for Shopify variant %s.' % (value_name, variant_payload.get('gid')),
            )
        return ptav

    @api.model
    def _create_variant_for_combination(self, template, combination, variant_payload):
        """Get-or-create the exact `product.product` for a PTAV combination
        via the verified Odoo 19 dynamic mechanism, then return it."""
        product = template._get_variant_for_combination(combination)
        if not product:
            product = template._create_product_variant(combination)
        if not product:
            raise JobHandlerError(
                'binding_conflict',
                'Odoo could not instantiate the variant for Shopify variant '
                '%s (the attribute combination is not creatable on this '
                'template).' % (variant_payload.get('gid'),),
            )
        return product

    @api.model
    def _resolve_deterministic_variant(
        self, template_binding, source, variant_count, index,
    ):
        """The one `product.product` a Shopify variant may bind to directly
        without SKU/barcode search -- unchanged Task 010 behaviour for the
        singleton paths. Only `created_singleton` at index 0, or an
        existing-binding single-variant payload whose template has exactly
        one variant, qualifies. A `candidate_match` template never takes a
        shortcut (its variant match_key must come from candidate search)."""
        ProductProduct = self.env['product.product']
        if source == 'created_singleton' and index == 0:
            return template_binding.product_template_id.product_variant_id
        if source == 'existing_binding' and variant_count == 1 and index == 0:
            template_variants = template_binding.product_template_id.product_variant_ids
            if len(template_variants) == 1:
                return template_variants
        return ProductProduct.browse()

    @api.model
    def _match_variant_candidate(self, template_id, prefetch, variant_payload):
        """SKU-then-barcode candidate match for a variant, scoped to its
        resolved template, using the prefetched candidate sets and the
        prefetched bound-id exclusion (no per-variant full-table scan,
        D-010B-9). Returns `(product_id or None, match_key or None)`."""
        bound_ids = prefetch['bound_variant_ids']
        sku = variant_payload.get('sku')
        if sku:
            matches = prefetch['sku_candidates'].filtered(
                lambda product: product.default_code == sku
                and product.product_tmpl_id.id == template_id
                and product.id not in bound_ids
            )
            if len(matches) > 1:
                raise JobHandlerError(
                    'ambiguous_match',
                    'Ambiguous product-variant SKU match for Shopify '
                    'variant %s.' % (variant_payload.get('gid'),),
                )
            if matches:
                return matches.id, 'sku_reference'
        barcode = variant_payload.get('barcode')
        if barcode:
            matches = prefetch['barcode_candidates'].filtered(
                lambda product: product.barcode == barcode
                and product.product_tmpl_id.id == template_id
                and product.id not in bound_ids
            )
            if len(matches) > 1:
                raise JobHandlerError(
                    'ambiguous_match',
                    'Ambiguous product-variant barcode match for Shopify '
                    'variant %s.' % (variant_payload.get('gid'),),
                )
            if matches:
                return matches.id, 'barcode'
        return None, None

    @api.model
    def _find_template_candidates(self, store, variants):
        """SKU-then-barcode candidate search for the template binding.

        One batched search per identifier kind over the whole variant set
        (D-010B-9), resolving candidate `product.template` records via each
        candidate `product.product`'s `product_tmpl_id`. Already-bound
        templates for this store are excluded. Match priority and the
        no-name-matching rule (RA-006) are unchanged.
        """
        ProductProduct = self.env['product.product']
        bound_template_ids = set(self.env[
            'shopify.connector.product.template.binding'
        ].search([('store_id', '=', store.id)]).mapped('product_template_id').ids)

        sku_values = sorted({v['sku'] for v in variants if v.get('sku')})
        if sku_values:
            products = ProductProduct.search([('default_code', 'in', sku_values)])
            template_ids = [
                tmpl.id for tmpl in products.mapped('product_tmpl_id')
                if tmpl.id not in bound_template_ids
            ]
            if template_ids:
                return template_ids, 'sku_reference'

        barcode_values = sorted({v['barcode'] for v in variants if v.get('barcode')})
        if barcode_values:
            products = ProductProduct.search([('barcode', 'in', barcode_values)])
            template_ids = [
                tmpl.id for tmpl in products.mapped('product_tmpl_id')
                if tmpl.id not in bound_template_ids
            ]
            if template_ids:
                return template_ids, 'barcode'

        return [], None

    # ------------------------------------------------------------------
    # D-010B-4: base price import + additive price_extra decomposition.
    # ------------------------------------------------------------------

    @api.model
    def _apply_prices(self, payload, template_binding, source, settings, notes, product_by_gid):
        """Write Odoo prices only when the store's price source of truth is
        `shopify_authoritative` and this path may write (first import, or an
        existing-binding refresh in `shopify_fields` mode). Snapshots on the
        binding keep full fidelity regardless."""
        if not self._price_is_shopify_authoritative(settings):
            return
        if not self._should_write_shopify_owned_fields(source, settings):
            return
        template = template_binding.product_template_id
        variants = payload.get('variants') or []
        priced = [v for v in variants if v.get('price') is not None]
        if not priced:
            return
        precision = self.env['decimal.precision'].precision_get('Product Price')
        base = min(v['price'] for v in priced)
        base = float_round(base, precision_digits=precision)

        if len(variants) <= 1 or not template.attribute_line_ids:
            template.list_price = base
            return

        template.list_price = base
        decomposed = self._decompose_price_extra(
            template, variants, base, precision, product_by_gid,
        )
        if not decomposed:
            notes.append((
                'price_undecomposable',
                'Shopify product %s has per-variant prices that do not fit '
                'Odoo\'s additive price_extra model exactly; the template '
                'list price is set to the minimum variant price and the '
                'exact per-variant prices are retained in the binding '
                'snapshots. No price_extra was invented.' % (payload.get('gid'),),
            ))

    @api.model
    def _decompose_price_extra(self, template, variants, base, precision, product_by_gid):
        """Attempt an exact additive decomposition of per-variant prices
        onto `product.template.attribute.value.price_extra`.

        Returns True and writes price_extra on every PTAV when, for every
        priced variant, `base + sum(price_extra of its PTAVs)` equals its
        Shopify price within Product-Price precision. Returns False (writes
        nothing) when the additive model does not fit exactly -- never
        invents an incorrect price_extra. Uses `float_compare` throughout;
        never binary-float equality. Each variant maps to its exact Odoo
        `product.product` (built during variant resolution), so a
        connector-owned renamed attribute is handled correctly.
        """
        price_by_combo = {}
        for variant in variants:
            price = variant.get('price')
            if price is None:
                continue
            product = product_by_gid.get(variant.get('gid'))
            if not product:
                return False
            combo = frozenset(product.product_template_attribute_value_ids.ids)
            price_by_combo[combo] = float_round(price, precision_digits=precision)
        if not price_by_combo:
            return False

        # Baseline = the combination of a minimum-price variant.
        base_combo = None
        for combo, price in price_by_combo.items():
            if float_compare(price, base, precision_digits=precision) == 0:
                base_combo = set(combo)
                break
        if base_combo is None:
            return False

        PTAV = self.env['product.template.attribute.value']
        all_ptavs = template.attribute_line_ids.product_template_value_ids
        baseline_by_attr = {}
        for ptav in all_ptavs:
            if ptav.id in base_combo:
                baseline_by_attr[ptav.attribute_id.id] = ptav.id

        extra_by_ptav = {}
        for ptav in all_ptavs:
            if ptav.id in base_combo:
                extra_by_ptav[ptav.id] = 0.0
                continue
            # One-axis combination: baseline everywhere except this PTAV.
            other = set(base_combo)
            other.discard(baseline_by_attr.get(ptav.attribute_id.id))
            target_combo = frozenset(other | {ptav.id})
            axis_price = price_by_combo.get(target_combo)
            if axis_price is None:
                return False
            extra_by_ptav[ptav.id] = float_round(
                axis_price - base, precision_digits=precision,
            )

        # Verify every priced variant reproduces exactly.
        for combo, price in price_by_combo.items():
            total = base + sum(extra_by_ptav.get(ptav_id, 0.0) for ptav_id in combo)
            if float_compare(total, price, precision_digits=precision) != 0:
                return False

        for ptav in all_ptavs:
            ptav.price_extra = extra_by_ptav.get(ptav.id, 0.0)
        return True

    @api.model
    def _should_write_shopify_owned_fields(self, source, settings):
        """Whether this path may (re)write Shopify-owned Odoo fields
        (prices, connector-owned images). First import always may; an
        existing-binding refresh may only in `shopify_fields` mode
        (snapshot_only never overwrites). Structural additions are handled
        separately and apply in both modes."""
        if source in ('created_singleton', 'created_structured', 'candidate_match'):
            return True
        if source == 'existing_binding':
            return self._refresh_mode(settings) == 'shopify_fields'
        return False

    # ------------------------------------------------------------------
    # D-010B-5: compare-at price + D-010B-6: variant image, per variant.
    # ------------------------------------------------------------------

    @api.model
    def _apply_variant_extras(
        self, product, variant_payload, binding, source, settings, media, notes,
    ):
        """Compare-at price (connector-owned mirror, always maintained) and
        the per-variant image (ownership-guarded, gated by refresh mode)."""
        compare_at = variant_payload.get('compare_at_price')
        product.shopify_compare_at_price = compare_at or 0.0
        if not self._media_enabled(settings):
            return
        staged_path = media.get(('variant', variant_payload.get('gid')))
        if staged_path is None:
            return
        if not self._should_write_shopify_owned_fields(source, settings):
            return
        self._apply_image(
            product, 'image_variant_1920', binding, staged_path,
            'Shopify variant %s image' % (variant_payload.get('gid'),), notes,
        )

    # ------------------------------------------------------------------
    # D-010B-6: primary product image + the shared ownership-guarded write.
    # ------------------------------------------------------------------

    @api.model
    def _apply_template_media(
        self, store, payload, template_binding, source, settings, media, notes,
    ):
        if not self._media_enabled(settings):
            return
        staged_path = media.get('template')
        if staged_path is None:
            return
        if not self._should_write_shopify_owned_fields(source, settings):
            return
        self._apply_image(
            template_binding.product_template_id, 'image_1920',
            template_binding, staged_path,
            'Shopify product %s primary image' % (payload.get('gid'),), notes,
        )

    @api.model
    def _apply_image(self, record, field_name, binding, staged_path, label, notes):
        """Write a staged connector image with the D-010B-6 ownership guard
        -- the authoritative write-time check.

        An empty Odoo image is written and its stored checksum recorded. A
        connector-written image (current stored checksum matches our record)
        is overwritten. A merchant-modified image, or a merchant image the
        connector never wrote (current stored checksum differs from -- or is
        present without -- our record), is never overwritten: a
        `merchant_image_protected` note is recorded instead.

        `staged_path` is the path to a closed temporary file. Exactly one
        such file is opened here, read fully into memory for the single Odoo
        write, and closed again (review `4950339305` item 2) -- never more
        than one staged image is held open or in memory at a time. The
        stored-value checksum is updated only after a successful write."""
        current = record[field_name]
        current_checksum = self._image_checksum(current)
        recorded = binding.shopify_image_checksum
        if current and not (recorded and current_checksum == recorded):
            self._note_protected(notes, label)
            return
        image_bytes = self._read_staged(staged_path)
        record.write({field_name: base64.b64encode(image_bytes)})
        del image_bytes
        # Read the stored (post-processing) value back so the ownership
        # checksum matches what a later refresh will compute.
        record.flush_recordset([field_name])
        record.invalidate_recordset([field_name])
        binding.shopify_image_checksum = self._image_checksum(record[field_name])

    @api.model
    def _read_staged(self, staged_path):
        """Open exactly one staged image path, read its bytes, and close it
        (a context-managed open, so the handle never outlives the read)."""
        with open(staged_path, 'rb') as handle:
            return handle.read()

    @api.model
    def _image_checksum(self, value):
        if not value:
            return False
        if isinstance(value, str):
            value = value.encode()
        return hashlib.sha256(value).hexdigest()

    @api.model
    def _note_protected(self, notes, label):
        notes.append((
            'merchant_image_protected',
            '%s was not written: the current Odoo image was set, modified, '
            'or cleared outside the connector and is protected.' % (label,),
        ))

    # ------------------------------------------------------------------
    # D-010B-6/D-010B-10: media staging (network, before the savepoint) with
    # bounded process memory and deterministic cleanup (review `4950202231`
    # items 3-6).
    # ------------------------------------------------------------------

    @api.model
    def _prepare_media(self, store, payload, settings, notes, stack):
        """Stage the primary and per-variant images over the network, before
        the transaction's write scope (D-010B-10). Returns a map
        `{'template': path|None, ('variant', gid): path|None}` whose values
        are paths to CLOSED temporary files (each path registered with
        `stack` for a deterministic unlink on every exit path) or `None` (no
        image, an unchanged connector image, or a merchant-protected image
        already noted). Only a path -- never an open handle -- is retained,
        so open file handles stay O(1) regardless of the variant count. A
        download/validation failure raises `shopify_temporary_server_network`
        (auto-retry), never a hold, and unlinks any partially staged file."""
        if not self._media_enabled(settings):
            return {}
        mode = self._refresh_mode(settings)
        media = {}
        media['template'] = self._plan_one_image(
            store, 'template', payload.get('gid'), payload.get('image_url'),
            'image_1920', mode, notes, stack,
            'Shopify product %s primary image' % (payload.get('gid'),),
        )
        for variant in payload.get('variants') or []:
            key = ('variant', variant.get('gid'))
            media[key] = self._plan_one_image(
                store, 'variant', variant.get('gid'), variant.get('image_url'),
                'image_variant_1920', mode, notes, stack,
                'Shopify variant %s image' % (variant.get('gid'),),
            )
        return media

    @api.model
    def _plan_one_image(
        self, store, kind, gid, url, field_name, mode, notes, stack, label,
    ):
        """Decide, for one image target, whether to download (return the path
        to a closed staged temp file whose unlink is registered with
        `stack`), protect (return `None` + note), or skip (return `None`).

        The skip decision compares the CURRENT Odoo image checksum against
        the recorded connector checksum (review `4950202231` item 3), so an
        unchanged URL is skipped only when the connector still owns the
        image. A merchant-modified image is protected (both modes) without
        an unnecessary download; a merchant-cleared connector image is
        preserved under `snapshot_only` and restored under `shopify_fields`.
        A target with no existing binding is downloaded (first bind); the
        write-time ownership guard in `_apply_image` still protects any
        pre-existing merchant image on that record.
        """
        if not url:
            return None
        binding = self._image_binding(store, kind, gid)
        if not binding:
            return self._stage_image(url, stack)
        record = (
            binding.product_template_id if kind == 'template'
            else binding.product_variant_id
        )
        current = record[field_name] if record else False
        current_checksum = self._image_checksum(current)
        recorded = binding.shopify_image_checksum
        url_match = binding.shopify_primary_image_url == url
        connector_owns = (
            bool(current) and bool(recorded) and current_checksum == recorded
        )
        if connector_owns:
            if url_match:
                return None
            # Changed URL, connector still owns -> refresh only in
            # shopify_fields (snapshot_only never re-writes owned fields).
            return self._stage_image(url, stack) if mode == 'shopify_fields' else None
        if current:
            # Non-empty and not connector-owned -> merchant modified or a
            # pre-existing merchant image; never overwrite (both modes).
            self._note_protected(notes, label)
            return None
        if recorded:
            # We wrote before and the Odoo image is now empty -> merchant
            # cleared it.
            if mode == 'shopify_fields':
                return self._stage_image(url, stack)
            self._note_protected(notes, label)
            return None
        # Never written and currently empty -> an empty slot to fill only
        # when this refresh writes owned fields.
        return self._stage_image(url, stack) if mode == 'shopify_fields' else None

    @api.model
    def _image_binding(self, store, kind, gid):
        model = (
            'shopify.connector.product.template.binding' if kind == 'template'
            else 'shopify.connector.product.variant.binding'
        )
        return self.env[model].search([
            ('store_id', '=', store.id), ('shopify_gid', '=', gid),
        ], limit=1)

    @api.model
    def _stage_image(self, url, stack):
        """Download one image to a CLOSED secure temporary file and register
        its unlink with `stack` so it is removed on every exit path
        (success, download failure, validation failure, DB failure, or a
        classified importer failure). Returns the path (a string), never an
        open handle -- so no staged file stays open across the transaction."""
        path = self._fetch_image(url)
        stack.callback(self._unlink_quietly, path)
        return path

    @api.model
    def _unlink_quietly(self, path):
        """Remove a staged temporary file, ignoring an already-removed path.
        Never raises (cleanup must not mask the original outcome) and never
        surfaces the path in an error."""
        try:
            os.unlink(path)
        except OSError:
            pass

    @api.model
    def _fetch_image(self, url):
        """Download one image over HTTPS into a secure temporary file, close
        it, and return its path (D-010B-6 / reviews `4950202231` items 4-6
        and `4950339305` items 2-3).

        HTTPS only; redirects followed manually and only to HTTPS; the
        response content-type must be `image/*` and never SVG; the body is
        streamed in 64 KiB chunks to a `tempfile.mkstemp` file (mode 0600,
        created with `O_EXCL`) capped at `MAX_IMAGE_BYTES`, so only one chunk
        is ever held in memory; bounded connect/read timeouts; no credential,
        token, or connector header is ever attached to the request. The bytes
        are validated as a supported raster image via Pillow before the file
        is closed.

        A `requests.exceptions.RequestException` -- whether raised by the
        initial request OR mid-stream while iterating the response body
        (`ReadTimeout`, `ConnectionError`, `ChunkedEncodingError`, ...) --
        and every other failure raises `shopify_temporary_server_network`
        (auto-retry), never exposing the body, the URL, or the temporary
        path. On any failure the HTTP response is closed and the partial
        temporary file is unlinked; on success the file is closed and the
        caller registers its path for the final unlink."""
        fd, path = tempfile.mkstemp(prefix=IMAGE_TEMPFILE_PREFIX)
        staged = os.fdopen(fd, 'w+b')
        try:
            current = url
            for _hop in range(IMAGE_MAX_REDIRECTS + 1):
                if (urlsplit(current).scheme or '').lower() != 'https':
                    raise JobHandlerError(
                        'shopify_temporary_server_network',
                        'Refusing to fetch a non-HTTPS image URL.',
                    )
                try:
                    response = requests.get(
                        current, allow_redirects=False, stream=True,
                        timeout=(
                            IMAGE_CONNECT_TIMEOUT_SECONDS, IMAGE_READ_TIMEOUT_SECONDS,
                        ),
                    )
                except requests.exceptions.RequestException:
                    raise JobHandlerError(
                        'shopify_temporary_server_network',
                        'The Shopify image could not be downloaded right now '
                        '-- this is usually temporary.',
                    )
                try:
                    if response.status_code in _REDIRECT_STATUS:
                        location = response.headers.get('Location')
                        if not location:
                            raise JobHandlerError(
                                'shopify_temporary_server_network',
                                'Image redirect without a target.',
                            )
                        current = urljoin(current, location)
                        continue
                    if response.status_code != 200:
                        raise JobHandlerError(
                            'shopify_temporary_server_network',
                            'The Shopify image download returned an '
                            'unexpected status.',
                        )
                    content_type = (
                        response.headers.get('Content-Type') or ''
                    ).split(';')[0].strip().lower()
                    if (
                        not content_type.startswith('image/')
                        or content_type in _REJECTED_IMAGE_CONTENT_TYPES
                        or 'svg' in content_type
                    ):
                        raise JobHandlerError(
                            'shopify_temporary_server_network',
                            'The image URL did not return a supported raster '
                            'image and was not imported.',
                        )
                    size = 0
                    try:
                        for chunk in response.iter_content(IMAGE_CHUNK_BYTES):
                            if not chunk:
                                continue
                            size += len(chunk)
                            if size > MAX_IMAGE_BYTES:
                                raise JobHandlerError(
                                    'shopify_temporary_server_network',
                                    'The Shopify image exceeded the maximum '
                                    'allowed size and was not imported.',
                                )
                            staged.write(chunk)
                    except requests.exceptions.RequestException:
                        # Mid-stream network failure while iterating the body
                        # (review `4950339305` item 3) -- classify it the same
                        # as an initial-request failure, never leak the body.
                        raise JobHandlerError(
                            'shopify_temporary_server_network',
                            'The Shopify image download was interrupted before '
                            'it completed -- this is usually temporary.',
                        )
                    staged.flush()
                    self._validate_raster(staged)
                    staged.close()
                    return path
                finally:
                    response.close()
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'The Shopify image exceeded the maximum number of redirects.',
            )
        except BaseException:
            # Any failure: close the handle and remove the partial file, so a
            # staged temporary never leaks. Re-raise the classified error.
            staged.close()
            self._unlink_quietly(path)
            raise

    @api.model
    def _validate_raster(self, staged):
        """Validate the staged bytes as a supported raster image via Pillow,
        never exposing the body. Malformed or non-raster bytes (including SVG
        markup with a spoofed content-type, which Pillow cannot open) raise
        `shopify_temporary_server_network`. Does not change any global
        Pillow configuration."""
        staged.seek(0)
        try:
            image = Image.open(staged)
            image_format = (image.format or '').upper()
            image.verify()
        except Exception:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'The downloaded content could not be validated as a '
                'supported raster image.',
            )
        if image_format not in SUPPORTED_RASTER_FORMATS:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'The downloaded image format is not a supported raster image.',
            )

    # ------------------------------------------------------------------
    # Informational job-log notes (via the sanctioned _system_append path).
    # ------------------------------------------------------------------

    @api.model
    def _emit_notes(self, job, notes):
        if not job or not notes:
            return
        for _code, message in notes:
            self._emit_note(job, message)

    @api.model
    def _emit_note(self, job, message):
        if not job:
            return
        self.env['shopify.connector.job.log']._system_append(job, 'note', message)


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
        preserves `super()` for every other `job_type` unchanged."""
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

        Reads only `job.store_id`/`job.shopify_target_gid` and passes `job`
        to the importer for informational notes. Any `JobHandlerError`
        propagates unchanged to `_invoke_handler()`, which routes it via
        `_route_failure()` -- no duplicate routing logic here."""
        self.env['shopify.connector.product.importer'].import_product_sync(
            job.store_id, job.shopify_target_gid, job=job,
        )
