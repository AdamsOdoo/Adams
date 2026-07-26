"""Controlled Odoo -> Shopify product export (Task 015), split-mutation.

Why this file does not use `productSet` to update
-------------------------------------------------

`productSet` is declarative over list fields: it "deletes existing entries
that aren't included in the mutation's input" (verbatim, 2026-07 reference,
read 2026-07-26), and the official documentation states the
leave-unchanged rule only "for all other field types". Whether a list field
omitted *entirely* is left alone is therefore not settled by the source,
and the earlier `X-EXPORT-0` experiment produced no behavioural answer.

Rather than gamble a merchant's collections, metafields and images on a
reading of two sentences, this module does not depend on the answer at all.
The 2026-07 update mutations are structurally incapable of the deletion:

* `ProductUpdateInput` has **no** `variants` field and **no**
  `productOptions` field, so `productUpdate` cannot delete a variant or an
  option however it is called. Its collection handling is the additive
  pair `collectionsToJoin`/`collectionsToLeave`, so a collection
  membership can only be removed by *naming* it — which this module never
  does.
* `productVariantsBulkUpdate` operates on the variant ids it is given,
  with `allowPartialUpdates: false` so a batch is all-or-nothing rather
  than half-applied.
* `productVariantsBulkCreate` runs with `strategy:
  PRESERVE_STANDALONE_VARIANT`, because the `DEFAULT` strategy "Deletes
  the standalone default ("Default Title") variant when it's the only
  variant on the product" — a remote deletion, and therefore not
  available to this module.

`productSet` survives in exactly one place: the **create** path, where
there is by definition no merchant state to destroy, and where its
`identifier.customId` upsert is the mechanism that makes a replayed create
converge on one product instead of two. It is reachable only after
preflight and reconciliation have established that no Shopify product is
bound to the Odoo source identity, and `_assert_no_product_set_on_existing`
enforces that at the payload boundary rather than by convention.

Nothing here deletes a remote variant, option, option value, collection
membership, metafield or media asset. Every difference that would require
one fails closed to `destructive_write_guard_blocked` and is shown to the
operator as something the connector refused to do.

The complete-list workaround is also refused: echoing a full remote list
back into a declarative input would make this module the author of state it
cannot see (a metafield it never read, a collection added a second ago),
which is the same defect wearing a different shape.
"""

import hashlib
import json
import logging
import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    INCONCLUSIVE_RECONCILIATION_CAP,
)
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from .shopify_connector_product_export_preview import PREVIEW_VALIDITY_HOURS

_logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Frozen job-contract vocabulary. Every `error_class` and
# `manual_review_subreason` below is already registered in core's
# ERROR_CLASS_SELECTION / MANUAL_REVIEW_SUBREASON_SELECTION — this module
# adds none.
# ----------------------------------------------------------------------
JOB_TYPE_PREVIEW = 'product_export_preview'
JOB_TYPE_APPLY = 'product_export_apply'
JOB_TYPE_BINDING_NAMESPACE = 'product_export_binding_namespace'
JOB_TYPE_CREATE = 'product_export_create'
JOB_TYPE_UPDATE = 'product_export_update'
JOB_TYPE_VARIANTS_UPDATE = 'product_export_variants_update'
JOB_TYPE_VARIANTS_CREATE = 'product_export_variants_create'
JOB_TYPE_MUTATION_RECONCILE = 'product_export_mutation_reconcile'

PRODUCT_MUTATION_DOMAINS = (
    JOB_TYPE_BINDING_NAMESPACE,
    JOB_TYPE_CREATE,
    JOB_TYPE_UPDATE,
    JOB_TYPE_VARIANTS_UPDATE,
    JOB_TYPE_VARIANTS_CREATE,
)

ERROR_CLASS_VALIDATION = 'shopify_user_errors_validation'
ERROR_CLASS_CONFIGURATION = 'odoo_validation_configuration'
ERROR_CLASS_DATA_SHAPE = 'data_shape_schema_mismatch'
ERROR_CLASS_TEMPORARY = 'shopify_temporary_server_network'
ERROR_CLASS_THROTTLE = 'shopify_throttling_rate_limit'
ERROR_CLASS_AUTH = 'shopify_permission_scope_auth'
ERROR_CLASS_CONCURRENCY = 'concurrency_race_conflict'
ERROR_CLASS_DESTRUCTIVE = 'destructive_write_guard_blocked'
ERROR_CLASS_DUPLICATE = 'duplicate_risk'
ERROR_CLASS_BINDING_CONFLICT = 'binding_conflict'
ERROR_CLASS_STORE_IDENTITY = 'store_identity_mismatch'
ERROR_CLASS_IDEMPOTENCY = 'idempotency_contract_violation'

SUBREASON_DESTRUCTIVE = 'destructive_write_guard_blocked'
SUBREASON_DUPLICATE = 'duplicate_risk'
SUBREASON_BINDING_CONFLICT = 'binding_conflict'
SUBREASON_STORE_IDENTITY = 'store_identity_mismatch'
SUBREASON_IDEMPOTENCY = 'idempotency_contract_violation'

# D-015-2: the ONLY product-level fields this module may ever send. The
# payload builder asserts against this set, so a future edit that adds a
# field has to add it here first and trip the allowlist test.
PRODUCT_SCALAR_ALLOWLIST = frozenset((
    'title', 'descriptionHtml', 'vendor', 'productType', 'tags', 'status',
))
# The variant-level allowlist. `inventoryQuantities` is deliberately absent
# and is additionally source-guarded: inventory quantity is Task 013's
# domain and must never ride a catalog payload.
VARIANT_FIELD_ALLOWLIST = frozenset((
    'id', 'price', 'compareAtPrice', 'barcode', 'inventoryItem',
    'optionValues',
))
# Keys that must never appear in an update-path variable tree at all. This
# is the mechanical form of "no merchant-owned list state".
FORBIDDEN_UPDATE_KEYS = frozenset((
    'collections', 'collectionsToJoin', 'collectionsToLeave', 'metafields',
    'files', 'media', 'variants', 'productOptions', 'inventoryQuantities',
    'quantityAdjustments', 'mediaId', 'mediaSrc',
))

# Shopify's documented product option ceiling (2026-07 reference).
MAX_PRODUCT_OPTIONS = 3
# D-015-4's MVP bound. Far below the documented 2048-variant ceiling, so
# synchronous `productSet` stays inside its safe envelope by construction.
MAX_EXPORT_VARIANTS = 100

# The connector-owned binding metafield. `namespace` is omitted from
# `UniqueMetafieldValueInput` on purpose: the 2026-07 reference states
# "If omitted, the app-reserved namespace will be used", which is exactly
# the namespace a connector should own and a merchant should not.
BINDING_METAFIELD_KEY = 'odoo_template_id'
BINDING_METAFIELD_TYPE = 'single_line_text_field'
BINDING_METAFIELD_OWNER = 'PRODUCT'

EXPORT_STATUS_TO_SHOPIFY = {
    'draft': 'DRAFT',
    'active': 'ACTIVE',
    'archived': 'ARCHIVED',
}


class ExportPreC2FailClosedError(Exception):
    """Domain pre-C2 fail-closed signal (the Task 013 precedent).

    Raised from `prepare_preconditions` when the fresh pre-C2 read proves
    the mutation must not be sent. It never writes and never commits: the
    disposition is applied by `_recover_pre_c2_failure` after core's own
    rollback, so no half-applied state can survive.
    """

    def __init__(self, error_class, subreason, message):
        super().__init__(message)
        self.error_class = error_class
        self.subreason = subreason
        self.message = message


def canonical_checksum(payload):
    """SHA-256 over stable JSON — used for plan-step and payload identity."""
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        ).encode('utf-8')
    ).hexdigest()


def _money(value):
    """Shopify `Money` is a decimal string; never a float in the payload."""
    return '%.2f' % (value or 0.0)


def assert_no_forbidden_keys(node, path='variables'):
    """Fail closed if a merchant-owned list key appears anywhere in a tree.

    Applied to every update-path variable tree before it can reach the
    transport. A guard that only checks the top level would miss
    `variants[0].metafields`, which is exactly the shape a careless future
    edit produces.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_UPDATE_KEYS:
                raise ValidationError(
                    'Refusing to build a Shopify product update containing '
                    '%r at %s: this connector never authors merchant-owned '
                    'list state.' % (key, path)
                )
            assert_no_forbidden_keys(value, '%s.%s' % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_forbidden_keys(value, '%s[%d]' % (path, index))


class ShopifyConnectorProductExportService(models.AbstractModel):
    _name = 'shopify.connector.product.export.service'
    _description = 'Shopify Connector Product Export Service'

    # ------------------------------------------------------------------
    # Settings / gating helpers
    # ------------------------------------------------------------------

    @api.model
    def _settings(self, store):
        return self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )

    @api.model
    def _require_export_enabled(self, store):
        settings = self._settings(store)
        if not settings or not settings.product_export_domain_enabled:
            raise UserError(
                'Product export is not enabled for this Shopify store.'
            )
        return settings

    @api.model
    def _price_export_allowed(self, store):
        """D-015-2 / DEC-007: prices ride the payload only when this store
        says Odoo owns them. Any other value — including unset — omits the
        price fields entirely rather than defaulting to writing them."""
        settings = self._settings(store)
        return bool(
            settings and settings.price_source_of_truth == 'odoo_authoritative'
        )

    # ------------------------------------------------------------------
    # Desired-state construction (Odoo side)
    # ------------------------------------------------------------------

    @api.model
    def _desired_scalars(self, template):
        """The allowlisted product scalars, and nothing else."""
        status = template.shopify_export_status or 'draft'
        tags = [
            tag.strip()
            for tag in (template.shopify_export_tags or '').split(',')
            if tag.strip()
        ]
        desired = {
            'title': template.name or '',
            'descriptionHtml': template.description_sale or '',
            'vendor': template.shopify_export_vendor or '',
            'productType': template.shopify_export_product_type or '',
            'tags': tags,
            'status': EXPORT_STATUS_TO_SHOPIFY[status],
        }
        unexpected = set(desired) - PRODUCT_SCALAR_ALLOWLIST
        if unexpected:
            raise ValidationError(
                'The export payload builder produced non-allowlisted product '
                'fields: %s' % ', '.join(sorted(unexpected))
            )
        return desired

    @api.model
    def _desired_options(self, template):
        """Odoo attribute lines as Shopify product options.

        Order matters to Shopify (option position is identity for
        `optionValues`), so the Odoo line order is preserved verbatim
        rather than sorted into something prettier.
        """
        options = []
        for line in template.attribute_line_ids:
            values = [value.name for value in line.value_ids]
            if not values:
                continue
            options.append({
                'name': line.attribute_id.name,
                'values': values,
            })
        return options

    @api.model
    def _desired_variant(self, store, variant, include_price):
        """One variant's allowlisted fields.

        `inventoryItem: {sku}` rather than a top-level `sku`: SKU lives on
        InventoryItem for writes in 2026-07. `inventoryItem` carries the
        SKU and nothing else — never a tracked flag, never a quantity.
        """
        option_values = []
        for value in variant.product_template_attribute_value_ids:
            option_values.append({
                'optionName': value.attribute_id.name,
                'name': value.name,
            })
        desired = {
            'barcode': variant.barcode or '',
            'inventoryItem': {'sku': variant.default_code or ''},
        }
        if option_values:
            desired['optionValues'] = option_values
        if include_price:
            desired['price'] = _money(variant.lst_price)
            # An unset compare-at price is omitted, never sent as 0.00 —
            # 0.00 is a *value* that would clear a merchant's strike-through
            # price, and omission is the only way to say "not ours".
            if variant.shopify_compare_at_price:
                desired['compareAtPrice'] = _money(
                    variant.shopify_compare_at_price
                )
        unexpected = set(desired) - VARIANT_FIELD_ALLOWLIST
        if unexpected:
            raise ValidationError(
                'The export payload builder produced non-allowlisted variant '
                'fields: %s' % ', '.join(sorted(unexpected))
            )
        return desired

    # ------------------------------------------------------------------
    # Fresh remote read (never a cached snapshot)
    # ------------------------------------------------------------------

    @api.model
    def _read_remote_product(self, store, job, product_gid):
        """One narrow read of the bound product, for preview and for the
        apply-time changed-since-read gate.

        Merchant-owned surfaces are read for *counts only* — enough to tell
        the operator "you have 3 collections and 2 metafields and this
        export touches neither", never enough to echo them into a payload.
        """
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportRead($id: ID!) { '
            'product(id: $id) { id handle title descriptionHtml vendor '
            'productType tags status updatedAt '
            'options { id name position optionValues { id name } } '
            'variants(first: %d) { nodes { id barcode price compareAtPrice '
            'inventoryItem { id sku } '
            'selectedOptions { name value } } } '
            'collections(first: 1) { nodes { id } } '
            'metafields(first: 1) { nodes { id } } '
            'media(first: 1) { nodes { id } } } '
            'shop { myshopifyDomain } }' % (MAX_EXPORT_VARIANTS + 1,)
        )
        with client.execute_business(
            job, store, query, {'id': product_gid},
        ) as result:
            data = (result or {}).get('data')
        if not isinstance(data, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify product-read response (no data).',
            )
        store_identity = (data.get('shop') or {}).get('myshopifyDomain')
        product = data.get('product')
        if product is None:
            return {
                'store_identity': store_identity,
                'exists': False,
                'product': None,
            }
        if not isinstance(product, dict) or product.get('id') != product_gid:
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Shopify returned a different product identity than '
                'requested.',
            )
        variants = ((product.get('variants') or {}).get('nodes')) or []
        if not isinstance(variants, list):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Malformed Shopify variant collection in the product read.',
            )
        return {
            'store_identity': store_identity,
            'exists': True,
            'product': product,
            'variants': variants,
            'updated_at': product.get('updatedAt'),
            'has_collections': bool(
                ((product.get('collections') or {}).get('nodes')) or []
            ),
            'has_metafields': bool(
                ((product.get('metafields') or {}).get('nodes')) or []
            ),
            'has_media': bool(
                ((product.get('media') or {}).get('nodes')) or []
            ),
        }

    @api.model
    def _search_remote_by_custom_id(self, store, job, template_id):
        """Reconciliation-by-identifier for the create path.

        Answers the only question that makes a create replay safe: has a
        product carrying *our* binding metafield value already been created?
        This is the read that runs before any create retry, so an
        acknowledgement lost in transit converges on the existing product
        instead of a second one.
        """
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportFindByCustomId($query: String!) { '
            'products(first: 2, query: $query) { nodes { id title '
            'updatedAt } } shop { myshopifyDomain } }'
        )
        search = 'metafields.%s:%s' % (BINDING_METAFIELD_KEY, template_id)
        with client.execute_business(
            job, store, query, {'query': search},
        ) as result:
            data = (result or {}).get('data') or {}
        nodes = ((data.get('products') or {}).get('nodes')) or []
        return {
            'store_identity': (data.get('shop') or {}).get('myshopifyDomain'),
            'nodes': nodes,
        }

    @api.model
    def _search_remote_by_sku(self, store, job, skus):
        """The MBQ-59 pre-create duplicate gate. Any hit is a review case."""
        if not skus:
            return []
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportSkuGate($query: String!) { '
            'productVariants(first: 5, query: $query) { nodes { id sku '
            'product { id title } } } }'
        )
        search = ' OR '.join('sku:%s' % sku for sku in sorted(skus))
        with client.execute_business(
            job, store, query, {'query': search},
        ) as result:
            data = (result or {}).get('data') or {}
        return ((data.get('productVariants') or {}).get('nodes')) or []

    # ------------------------------------------------------------------
    # Enqueue surfaces
    # ------------------------------------------------------------------

    @api.model
    def _enqueue(
        self, store, job_type, job_source, res_model, res_id,
        shopify_target_gid=False, payload_hash=False,
    ):
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store,
            job_source,
            job_type,
            payload_hash=payload_hash or uuid.uuid4().hex,
            res_model=res_model,
            res_id=res_id,
            shopify_target_gid=shopify_target_gid,
        )

    @api.model
    def enqueue_preview(self, template, store):
        """The operator-facing entry point: request a fresh preview.

        Gated on the same two roles that may confirm, because a preview
        issues a Shopify read against the merchant's store.
        """
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Operator or Administrator may '
                'request a product-export preview.'
            )
        self._require_export_enabled(store)
        if not template.shopify_export_enabled:
            raise UserError(
                'This product is not enabled for Shopify export. Enable it '
                'on the product first.'
            )
        if template.company_id and template.company_id != store.company_id:
            raise UserError(
                'This product and this Shopify store belong to different '
                'companies.'
            )
        return self._enqueue(
            store, JOB_TYPE_PREVIEW, 'export_preview_dry_run',
            'product.template', template.id,
        )

    @api.model
    def _enqueue_apply(self, preview):
        return self._enqueue(
            preview.store_id, JOB_TYPE_APPLY, 'manual_sync',
            preview._name, preview.id,
            shopify_target_gid=preview.remote_product_gid or False,
        )

    # ------------------------------------------------------------------
    # Preview handler (read-only)
    # ------------------------------------------------------------------

    @api.model
    def _handle_product_export_preview(self, job):
        template = self.env['product.template'].browse(job.res_id).exists()
        if not template:
            raise JobHandlerError(
                ERROR_CLASS_CONFIGURATION,
                'The product to preview no longer exists.',
            )
        store = job.store_id
        settings = self._settings(store)
        if not settings or not settings.product_export_domain_enabled:
            raise JobHandlerError(
                ERROR_CLASS_CONFIGURATION,
                'Product export is not enabled for this store.',
            )
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().search([
            ('store_id', '=', store.id),
            ('product_template_id', '=', template.id),
        ], limit=1)

        include_price = self._price_export_allowed(store)
        desired_scalars = self._desired_scalars(template)
        desired_options = self._desired_options(template)
        variants = template.product_variant_ids
        blocked = []

        if len(desired_options) > MAX_PRODUCT_OPTIONS:
            blocked.append({
                'kind': 'too_many_options',
                'detail': '%d Odoo attribute lines; Shopify allows %d.' % (
                    len(desired_options), MAX_PRODUCT_OPTIONS,
                ),
            })
        if len(variants) > MAX_EXPORT_VARIANTS:
            blocked.append({
                'kind': 'too_many_variants',
                'detail': '%d variants; this connector exports at most %d '
                          'per job.' % (len(variants), MAX_EXPORT_VARIANTS),
            })

        if binding and binding.shopify_gid:
            # The read happens here, in the handler, and is passed down. Doing
            # it this way keeps `_preview_update_path` a pure function of
            # (Odoo state, remote state) — which is what makes the guard logic
            # testable without a network seam.
            read = self._read_remote_product(store, job, binding.shopify_gid)
            if read['store_identity'] != store.shop_domain:
                raise JobHandlerError(
                    ERROR_CLASS_STORE_IDENTITY,
                    'The preview read observed a different Shopify store '
                    'identity than this store.',
                )
            diff, plan_steps, path_blocked = self._preview_update_path(
                store, template, binding, desired_scalars,
                desired_options, variants, include_price, read,
            )
            export_path = 'update'
            remote_gid = binding.shopify_gid
            remote_updated_at = diff.get('remote_updated_at')
        else:
            diff, plan_steps, path_blocked = self._preview_create_path(
                job, store, template, desired_scalars, desired_options,
                variants, include_price,
            )
            export_path = 'create'
            remote_gid = False
            remote_updated_at = False
        blocked.extend(path_blocked)

        media_steps, media_diff = self.env[
            'shopify.connector.media.export.service'
        ]._preview_media(store, template, binding)
        diff['media'] = media_diff
        plan_steps.extend(media_steps)

        # A blocking hold removes every executable step: an operator must
        # never be able to confirm "the safe half" of a payload whose shape
        # this connector already refused.
        #
        # This runs AFTER the media steps are collected, and that ordering is
        # the whole point. Applied before them, the hold emptied the product
        # plan and the media planner then refilled it, so a product whose
        # option or variant shape had already been refused came back
        # `previewed` with executable steps -- confirmable, and exporting the
        # "safe half" the comment above says can never be offered. The hold
        # has to be the last word on the plan, not a step in the middle of
        # building it.
        if any(
            item['kind'] in ('too_many_options', 'too_many_variants')
            for item in blocked
        ):
            plan_steps = []
            diff['media'] = dict(
                media_diff,
                exported=False,
                reason='Media is not exported while this product\'s option '
                       'or variant shape is refused. Resolve the refusal '
                       'and run a fresh preview.',
                appends=[],
            )

        preview = self._create_preview_record(
            store, template, binding, export_path, diff, plan_steps, blocked,
            remote_gid, remote_updated_at,
        )
        self.env['shopify.connector.job.log']._system_append(
            job, 'attempt',
            'Export preview %d computed: path=%s steps=%d blocked=%d' % (
                preview.id, export_path, len(plan_steps), len(blocked),
            ),
        )
        # The job is left `running`: the dispatcher's own boundary writes the
        # succeeded transition and its log row, so a handler that wrote its
        # own would produce two.
        return preview

    @api.model
    def _create_preview_record(
        self, store, template, binding, export_path, diff, plan_steps,
        blocked, remote_gid, remote_updated_at,
    ):
        Preview = self.env['shopify.connector.product.export.preview']
        # Any earlier open preview for this template is expired rather than
        # left confirmable: two confirmable previews for one product is two
        # different truths about what is about to happen.
        superseded = Preview.sudo().search([
            ('store_id', '=', store.id),
            ('product_template_id', '=', template.id),
            ('state', 'in', ('previewed', 'confirmed')),
        ])
        for row in superseded:
            row._record_expiry('superseded_by_fresh_preview')
        now = fields.Datetime.now()
        values = {
            'store_id': store.id,
            'product_template_id': template.id,
            'product_template_binding_id': binding.id if binding else False,
            'export_path': export_path,
            # `blocked` means "this export cannot proceed as previewed", which
            # is only true when something was actually refused. A preview with
            # no steps and no refusals is simply a product that already matches
            # Shopify: it stays `previewed`, and confirmation refuses it with
            # "nothing that can be exported" rather than a red banner implying
            # a problem that does not exist.
            'state': 'blocked' if (blocked and not plan_steps) else 'previewed',
            'diff': diff,
            'apply_plan': {'steps': plan_steps, 'cursor': 0},
            'blocked_differences': {'items': blocked},
            'has_blocked_differences': bool(blocked),
            'remote_product_gid': remote_gid or False,
            'remote_updated_at': remote_updated_at or False,
            'source_write_date': Preview._source_write_date(template),
            'previewed_at': now,
            'expires_at': now + timedelta(hours=PREVIEW_VALIDITY_HOURS),
        }
        return Preview._preview_surface('_create_preview').create(values)

    # ------------------------------------------------------------------
    # Preview: update path
    # ------------------------------------------------------------------

    @api.model
    def _preview_update_path(
        self, store, template, binding, desired_scalars, desired_options,
        variants, include_price, read,
    ):
        blocked = []
        if not read['exists']:
            # PD-PX-7: a bound product that is gone remotely is a review
            # case, never a silent re-create.
            blocked.append({
                'kind': 'bound_product_missing_remotely',
                'detail': 'The bound Shopify product no longer exists. A '
                          'reviewer must decide whether to re-create or '
                          'unbind it; this connector will not guess.',
            })
            return (
                {'scalars': [], 'remote_updated_at': False,
                 'untouched': {}},
                [],
                blocked,
            )

        remote = read['product']
        scalar_changes = []
        for field_name, desired in sorted(desired_scalars.items()):
            current = remote.get(field_name)
            if field_name == 'tags':
                same = sorted(current or []) == sorted(desired)
            else:
                same = (current or '') == desired
            if not same:
                scalar_changes.append({
                    'field': field_name,
                    'from': current,
                    'to': desired,
                })

        variant_plan = self._diff_variants(
            store, binding, read['variants'], variants, include_price,
        )
        blocked.extend(variant_plan['blocked'])

        remote_options = [
            {
                'name': option.get('name'),
                'values': [
                    value.get('name')
                    for value in (option.get('optionValues') or [])
                ],
            }
            for option in sorted(
                remote.get('options') or [],
                key=lambda option: option.get('position') or 0,
            )
        ]
        # Options are never mutated on an existing product in MVP. Every
        # 2026-07 option mutation either removes values or reshapes the
        # variant matrix, and no source verification proves a
        # non-destructive path, so a divergence is disclosed and refused
        # rather than attempted.
        if self._options_diverge(remote_options, desired_options):
            blocked.append({
                'kind': 'remote_option_divergence',
                'detail': 'The Shopify option structure differs from the '
                          'Odoo attribute structure. Changing options on an '
                          'existing product cannot be proven '
                          'non-destructive, so this connector will not do '
                          'it. Resolve the option structure in Shopify.',
                'remote': remote_options,
                'odoo': desired_options,
            })

        steps = []
        if scalar_changes:
            steps.append({
                'step': JOB_TYPE_UPDATE,
                'state': 'pending',
                'fields': [change['field'] for change in scalar_changes],
            })
        # A variant write is refused while the option structure disagrees:
        # `optionValues` are positional against the remote option set, so
        # writing them against a different structure is how a variant ends
        # up describing the wrong thing.
        option_divergence = any(
            item['kind'] == 'remote_option_divergence' for item in blocked
        )
        if variant_plan['update'] and not option_divergence:
            steps.append({
                'step': JOB_TYPE_VARIANTS_UPDATE,
                'state': 'pending',
                'variant_gids': [
                    entry['id'] for entry in variant_plan['update']
                ],
            })
        if variant_plan['create'] and not option_divergence:
            steps.append({
                'step': JOB_TYPE_VARIANTS_CREATE,
                'state': 'pending',
                'variant_ids': [
                    entry['odoo_variant_id'] for entry in variant_plan['create']
                ],
            })
        elif variant_plan['create'] and option_divergence:
            blocked.append({
                'kind': 'variant_create_withheld',
                'detail': '%d new variant(s) are not created while the '
                          'option structure disagrees.' % (
                              len(variant_plan['create']),
                          ),
            })

        diff = {
            'scalars': scalar_changes,
            'variants_update': variant_plan['update'],
            'variants_create': variant_plan['create'],
            'remote_updated_at': read['updated_at'],
            'price_exported': include_price,
            # Named explicitly so "not listed" can never be misread as
            # "not affected". These are the surfaces the connector does not
            # own and structurally cannot write.
            'untouched': {
                'collections': read['has_collections'],
                'metafields': read['has_metafields'],
                'existing_media': read['has_media'],
                'note': 'Collections, merchant metafields and existing '
                        'media are never included in this export and are '
                        'left exactly as they are.',
            },
        }
        return diff, steps, blocked

    @api.model
    def _options_diverge(self, remote_options, desired_options):
        if len(remote_options) != len(desired_options):
            return True
        for remote, desired in zip(remote_options, desired_options):
            if (remote.get('name') or '') != (desired.get('name') or ''):
                return True
            # A remote option value the connector would have to remove is a
            # divergence; a remote option that is a strict superset of the
            # Odoo values is also a divergence, because closing it means
            # deleting a value.
            if sorted(remote.get('values') or []) != sorted(
                desired.get('values') or []
            ):
                return True
        return False

    @api.model
    def _diff_variants(
        self, store, binding, remote_variants, variants, include_price,
    ):
        """Map Odoo variants onto remote variants strictly through bindings.

        Identity comes from the variant binding and nowhere else. Re-deriving
        it from option values or SKU at apply time is the RA-006 name-matching
        failure mode at variant level, so it is not done here even as a
        fallback.
        """
        VariantBinding = self.env['shopify.connector.product.variant.binding']
        bindings = VariantBinding.sudo().search([
            ('store_id', '=', store.id),
            ('product_template_binding_id', '=', binding.id),
        ])
        bound_by_variant = {
            row.product_variant_id.id: row for row in bindings
        }
        remote_by_gid = {
            entry.get('id'): entry
            for entry in remote_variants
            if isinstance(entry, dict) and entry.get('id')
        }
        to_update = []
        to_create = []
        blocked = []
        mapped_gids = set()

        for variant in variants:
            row = bound_by_variant.get(variant.id)
            desired = self._desired_variant(store, variant, include_price)
            if row and row.shopify_gid and row.shopify_gid in remote_by_gid:
                mapped_gids.add(row.shopify_gid)
                current = remote_by_gid[row.shopify_gid]
                changes = self._variant_changes(current, desired, include_price)
                if changes:
                    to_update.append({
                        'id': row.shopify_gid,
                        'odoo_variant_id': variant.id,
                        'display_name': variant.display_name,
                        'changes': changes,
                    })
            elif row and row.shopify_gid:
                # The binding names a remote variant the fresh read did not
                # return. Creating a replacement would duplicate; deleting
                # the binding would erase evidence. Review it.
                blocked.append({
                    'kind': 'bound_variant_missing_remotely',
                    'detail': 'A bound Shopify variant was not returned by '
                              'the fresh read.',
                    'odoo_variant_id': variant.id,
                })
            else:
                to_create.append({
                    'odoo_variant_id': variant.id,
                    'display_name': variant.display_name,
                    'values': desired,
                })

        for gid, entry in sorted(remote_by_gid.items()):
            if gid in mapped_gids:
                continue
            # A remote variant this connector does not own. It is NOT
            # deleted, NOT counted as replaceable, and NOT silently
            # ignored: it is disclosed so the operator knows the exported
            # product will keep it.
            blocked.append({
                'kind': 'unowned_remote_variant',
                'detail': 'Shopify variant %s is not bound to any Odoo '
                          'variant. It is left exactly as it is — this '
                          'connector never deletes a remote variant.' % (
                              gid,
                          ),
                'remote_variant_gid': gid,
                'remote_sku': (entry.get('inventoryItem') or {}).get('sku'),
            })
        return {'update': to_update, 'create': to_create, 'blocked': blocked}

    @api.model
    def _variant_changes(self, current, desired, include_price):
        changes = []
        current_sku = (current.get('inventoryItem') or {}).get('sku') or ''
        desired_sku = (desired.get('inventoryItem') or {}).get('sku') or ''
        if current_sku != desired_sku:
            changes.append({'field': 'sku', 'from': current_sku,
                            'to': desired_sku})
        if (current.get('barcode') or '') != (desired.get('barcode') or ''):
            changes.append({'field': 'barcode',
                            'from': current.get('barcode'),
                            'to': desired.get('barcode')})
        if include_price:
            if _money(float(current.get('price') or 0.0)) != desired['price']:
                changes.append({'field': 'price',
                                'from': current.get('price'),
                                'to': desired['price']})
            desired_compare = desired.get('compareAtPrice')
            current_compare = current.get('compareAtPrice')
            if desired_compare is not None and (
                current_compare is None
                or _money(float(current_compare)) != desired_compare
            ):
                changes.append({'field': 'compareAtPrice',
                                'from': current_compare,
                                'to': desired_compare})
        return changes

    # ------------------------------------------------------------------
    # Preview: create path
    # ------------------------------------------------------------------

    @api.model
    def _preview_create_path(
        self, job, store, template, desired_scalars, desired_options,
        variants, include_price,
    ):
        blocked = []
        settings = self._settings(store)
        # Reconciliation before creation, not after a failure: if a product
        # already carries this template's binding metafield, the create path
        # is not available at all.
        existing = self._search_remote_by_custom_id(store, job, template.id)
        if existing['store_identity'] != store.shop_domain:
            raise JobHandlerError(
                ERROR_CLASS_STORE_IDENTITY,
                'The create-path preflight read observed a different '
                'Shopify store identity.',
            )
        if existing['nodes']:
            blocked.append({
                'kind': 'custom_id_already_bound_remotely',
                'detail': 'A Shopify product already carries this product\'s '
                          'connector binding id. It must be adopted and '
                          'bound by a reviewer before any export; this '
                          'connector will not create a second one.',
                'remote_product_gids': [
                    node.get('id') for node in existing['nodes']
                ],
            })

        skus = {
            variant.default_code
            for variant in variants
            if variant.default_code
        }
        sku_hits = self._search_remote_by_sku(store, job, skus)
        if sku_hits:
            blocked.append({
                'kind': 'duplicate_sku_on_shopify',
                'detail': 'One or more SKUs already exist on Shopify. A '
                          'reviewer must resolve the match before a create; '
                          'a blind create is how duplicate products happen.',
                'matches': [
                    {'sku': hit.get('sku'),
                     'product_gid': (hit.get('product') or {}).get('id')}
                    for hit in sku_hits
                ],
            })

        steps = []
        if not blocked:
            if not (settings and settings.product_export_binding_namespace_ready):
                steps.append({
                    'step': JOB_TYPE_BINDING_NAMESPACE,
                    'state': 'pending',
                })
            steps.append({
                'step': JOB_TYPE_CREATE,
                'state': 'pending',
                'variant_ids': variants.ids,
            })
        diff = {
            'scalars': [
                {'field': name, 'from': None, 'to': value}
                for name, value in sorted(desired_scalars.items())
            ],
            'options': desired_options,
            'variants_create': [
                {'odoo_variant_id': variant.id,
                 'display_name': variant.display_name,
                 'values': self._desired_variant(store, variant, include_price)}
                for variant in variants
            ],
            'variants_update': [],
            'remote_updated_at': False,
            'price_exported': include_price,
            'untouched': {
                'note': 'A newly created product is created DRAFT unless the '
                        'product says otherwise, and is never published as a '
                        'side effect of export.',
            },
        }
        return diff, steps, blocked

    # ------------------------------------------------------------------
    # Apply orchestrator (read-only: gates, then hands off)
    # ------------------------------------------------------------------

    @api.model
    def _handle_product_export_apply(self, job):
        """The changed-since-read gate and the destructive-write guard.

        This handler performs **no mutation**. It re-reads Shopify, refuses
        on any drift, and enqueues the first pending step of the plan the
        operator actually confirmed. Every mutation is a separate job with
        its own Layer 2 attempt.
        """
        preview = self.env[
            'shopify.connector.product.export.preview'
        ].sudo().browse(job.res_id).exists()
        if not preview:
            raise JobHandlerError(
                ERROR_CLASS_CONFIGURATION,
                'The confirmed export preview no longer exists.',
            )
        if preview.state not in ('confirmed', 'applying'):
            job._transition_blocked_manual_review(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'This export has no confirmed, unexpired preview. The '
                'destructive-write guard refused it.',
            )
            return
        if preview._is_expired():
            preview._record_expiry('expired_before_apply')
            job._transition_blocked_manual_review(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'The confirmed preview went stale before apply. A fresh '
                'preview and a fresh confirmation are required.',
            )
            return

        if preview.export_path == 'update':
            read = self._read_remote_product(
                job.store_id, job, preview.remote_product_gid,
            )
            if read['store_identity'] != job.store_id.shop_domain:
                raise JobHandlerError(
                    ERROR_CLASS_STORE_IDENTITY,
                    'The apply-time read observed a different Shopify store '
                    'identity.',
                )
            if not read['exists']:
                job._transition_blocked_manual_review(
                    ERROR_CLASS_BINDING_CONFLICT, SUBREASON_BINDING_CONFLICT,
                    'The bound Shopify product no longer exists. Nothing '
                    'was written.',
                )
                return
            if read['updated_at'] != preview.remote_updated_at:
                # D-015-6. Shopify offers no product-level compare-and-set,
                # so this read-compare-refuse sequence is the only available
                # equivalent, and it refuses rather than merges.
                preview._record_expiry('remote_changed_since_preview')
                job._transition_blocked_manual_review(
                    ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                    'The Shopify product changed after the preview was '
                    'taken. Nothing was written; re-preview and re-confirm.',
                )
                return

        next_step = self._next_pending_step(preview)
        if not next_step:
            preview._record_applied()
            return
        if preview.state == 'confirmed':
            preview._preview_surface('_record_plan_progress').write(
                {'state': 'applying'}
            )
            preview.invalidate_recordset()
        self._enqueue_step(preview, next_step)
        self.env['shopify.connector.job.log']._system_append(
            job, 'attempt',
            'Export apply admitted; step %s enqueued.' % (next_step['step'],),
        )

    @api.model
    def _next_pending_step(self, preview):
        for step in (preview.apply_plan or {}).get('steps') or []:
            if step.get('state') == 'pending':
                return step
        return None

    @api.model
    def _enqueue_step(self, preview, step):
        step_type = step['step']
        if step_type in self.env[
            'shopify.connector.media.export.service'
        ]._media_step_types():
            return self.env[
                'shopify.connector.media.export.service'
            ]._enqueue_media_step(preview, step)
        return self._enqueue(
            preview.store_id, step_type, 'manual_sync',
            preview._name, preview.id,
            shopify_target_gid=preview.remote_product_gid or False,
        )

    @api.model
    def _advance_plan(self, preview, step_type, completed=True):
        """Mark the current step done and enqueue the next one.

        Called from a mutation's `apply_consequence` on success, i.e. after
        the job is already terminal — so the plan only ever advances on a
        recorded, resolved outcome, never on optimism.
        """
        plan = dict(preview.apply_plan or {})
        steps = [dict(step) for step in plan.get('steps') or []]
        advanced = False
        for step in steps:
            if step.get('state') == 'pending' and step['step'] == step_type:
                step['state'] = 'done' if completed else 'blocked'
                advanced = True
                break
        if not advanced:
            return False
        plan['steps'] = steps
        preview._record_plan_progress(plan)
        preview.invalidate_recordset()
        if not completed:
            return False
        next_step = self._next_pending_step(preview)
        if not next_step:
            preview._record_applied()
            return True
        self._enqueue_step(preview, next_step)
        return True

    @api.model
    def _preview_for_job(self, job):
        preview = self.env[
            'shopify.connector.product.export.preview'
        ].sudo().browse(job.res_id).exists()
        if not preview:
            raise ValidationError(
                'This export mutation job has no export preview.'
            )
        return preview

    # ------------------------------------------------------------------
    # Layer 2: shared mutation plumbing
    # ------------------------------------------------------------------

    @api.model
    def _fail_closed_pre_c2(self, error_class, subreason, message):
        raise ExportPreC2FailClosedError(error_class, subreason, message)

    @api.model
    def _prepare_local_common(self, job):
        preview = self._preview_for_job(job)
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'preview_id': preview.id,
            'template_id': preview.product_template_id.id,
            'binding_id': preview.product_template_binding_id.id,
            'remote_product_gid': preview.remote_product_gid or '',
            'expected_connection_generation':
                job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    @api.model
    def _assert_confirmed_preview_pre_c2(self, local_snapshot):
        """Re-verified immediately before every mutation.

        The apply orchestrator already checked this. It is checked again
        here because between the two there is a job boundary, and a guard
        that is only evaluated once is a guard that can be raced.
        """
        preview = self.env[
            'shopify.connector.product.export.preview'
        ].sudo().browse(local_snapshot['preview_id']).exists()
        if not preview or preview.state != 'applying':
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No confirmed, in-progress export preview authorises this '
                'mutation.',
            )
        if not preview.confirmed_uid or not preview.confirmed_at:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'This export was never confirmed by a reviewer.',
            )
        return preview

    @api.model
    def _assert_no_product_set_on_existing(self, operation, local_snapshot):
        """The ruling's central structural rule, enforced at the boundary.

        `productSet` may not appear in an operation for a template that
        already has a binding with a Shopify GID. This is asserted on the
        operation string rather than trusted to the call graph, so a future
        refactor that routes an update through the create builder fails
        here instead of on a merchant's store.
        """
        if 'productSet' not in operation:
            return True
        if local_snapshot.get('remote_product_gid') or local_snapshot.get(
            'binding_id'
        ):
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'productSet is not available for a product that is already '
                'bound to Shopify. Refusing to build the request.',
            )
        return True

    @api.model
    def _mutation_request(
        self, domain, local_snapshot, operation, variables, intent,
        preconditions,
    ):
        idempotency_key = str(uuid.uuid4())
        return {
            'mutation_domain': domain,
            'operation': operation,
            'variables': variables,
            'business_intent': dict(intent),
            'remote_mutation_intent': {
                'operation_name': domain,
                'api_version': SHOPIFY_API_VERSION,
                'store_id': local_snapshot['store_id'],
                'preview_id': local_snapshot['preview_id'],
            },
            'preconditions_snapshot': dict(preconditions),
            'expected_connection_generation':
                local_snapshot['expected_connection_generation'],
            'expected_store_identity':
                local_snapshot['expected_store_identity'],
            'shopify_idempotency_key': idempotency_key,
        }

    @api.model
    def _transport(self, request, attempt_context, payload_key):
        """One guarded Layer 2 transport, shared by every export mutation."""
        store = self.env['shopify.connector.store'].browse(
            attempt_context['store_id']
        )
        client = self.env['shopify.connector.api.client']
        try:
            with client.execute_business(
                attempt_context['job_id'], store,
                request['operation'], request['variables'],
                mutation_context={
                    'job_id': attempt_context['job_id'],
                    'attempt_id': attempt_context['attempt_id'],
                    'attempt_token': attempt_context['attempt_token'],
                    'mutation_domain': attempt_context['mutation_domain'],
                },
            ) as result:
                data = (result or {}).get('data') or {}
                payload = data.get(payload_key) or {}
                return {
                    'outcome': None,
                    # The raw returned value is preserved: a missing or
                    # malformed container must never be defaulted to `[]`
                    # here, because `[]` reads as "no errors".
                    'user_errors': payload.get('userErrors'),
                    'payload': payload,
                    'evidence': {'transport': payload_key},
                }
        except Exception as exc:
            return {
                'outcome': 'uncertain',
                'error_class': self._transport_error_class(exc),
                'evidence': {'exception_class': type(exc).__name__},
            }

    @api.model
    def _transport_error_class(self, exc):
        error_class = getattr(exc, 'error_class', None)
        if error_class in (
            ERROR_CLASS_THROTTLE, ERROR_CLASS_TEMPORARY, ERROR_CLASS_AUTH,
            ERROR_CLASS_CONFIGURATION,
        ):
            return error_class
        return ERROR_CLASS_TEMPORARY

    @api.model
    def _classify_user_errors(
        self, result, success_check, message_prefix, evidence_builder=None,
    ):
        """The shared direct classifier.

        An empty `userErrors` list is never sufficient on its own: every
        domain supplies a `success_check` that has to find affirmative
        evidence in the returned payload. A malformed container is a data
        shape problem routed to reconciliation, never coerced to success.
        """
        result = result or {}
        if result.get('outcome') == 'uncertain':
            return {
                'observed_outcome': 'uncertain',
                'error_class': result.get('error_class', ERROR_CLASS_TEMPORARY),
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': '%s: transport-level uncertainty.' % message_prefix,
                'evidence': dict(result.get('evidence') or {}),
            }
        evidence = dict(result.get('evidence') or {})
        user_errors = result.get('user_errors')
        if not isinstance(user_errors, list):
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': '%s: userErrors was not a list; reconciliation '
                           'required.' % message_prefix,
                'evidence': evidence,
            }
        if user_errors:
            codes = sorted({
                str((error or {}).get('code') or 'UNKNOWN')
                for error in user_errors
                if isinstance(error, dict)
            })
            evidence['user_error_codes'] = codes
            return {
                'observed_outcome': 'failed_clean',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': False,
                'action': 'fail_final',
                'message': '%s: Shopify rejected the request (%s).' % (
                    message_prefix, ', '.join(codes),
                ),
                'evidence': evidence,
            }
        payload = result.get('payload') or {}
        verdict = success_check(payload)
        if verdict is not True:
            evidence['success_check'] = str(verdict)
            return {
                'observed_outcome': 'uncertain',
                'error_class': ERROR_CLASS_DATA_SHAPE,
                'manual_review_subreason': False,
                'action': 'reconcile',
                'message': '%s: no affirmative success evidence in the '
                           'response; reconciliation required.' % (
                               message_prefix,
                           ),
                'evidence': evidence,
            }
        if evidence_builder is not None:
            # The identities the consequence needs (a created product GID, a
            # File GID, a staged target) come from the response and are
            # carried on the evidence, so `apply_consequence` never has to
            # re-read what the mutation just told us.
            evidence.update(evidence_builder(payload) or {})
        return {
            'observed_outcome': 'succeeded',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': '%s: applied.' % message_prefix,
            'evidence': evidence,
        }

    # ------------------------------------------------------------------
    # Mutation domain: binding-metafield definition bootstrap
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_binding_namespace(self, job):
        return self._prepare_local_common(job)

    @api.model
    def _prepare_preconditions_binding_namespace(
        self, local_snapshot, owner_context,
    ):
        self._assert_confirmed_preview_pre_c2(local_snapshot)
        operation = (
            'mutation ProductExportBindingNamespace('
            '$definition: MetafieldDefinitionInput!) { '
            'metafieldDefinitionCreate(definition: $definition) { '
            'createdDefinition { id key namespace } '
            'userErrors { code field message } } }'
        )
        variables = {
            'definition': {
                'key': BINDING_METAFIELD_KEY,
                'name': 'Odoo product template id',
                'ownerType': BINDING_METAFIELD_OWNER,
                'type': BINDING_METAFIELD_TYPE,
                'description': (
                    'Connector-owned binding identity written by the Odoo '
                    'Shopify connector. Do not edit.'
                ),
                # `identifier.customId` takes a `UniqueMetafieldValueInput`,
                # which only resolves against a definition whose values are
                # unique. That is what makes this bootstrap a genuine
                # prerequisite of the create path rather than a nicety.
                'capabilities': {'uniqueValues': {'enabled': True}},
            },
        }
        return self._mutation_request(
            JOB_TYPE_BINDING_NAMESPACE, local_snapshot, operation, variables,
            {'key': BINDING_METAFIELD_KEY, 'owner': BINDING_METAFIELD_OWNER},
            {'store_id': local_snapshot['store_id']},
        )

    @api.model
    def _transport_binding_namespace(self, request, attempt_context):
        return self._transport(
            request, attempt_context, 'metafieldDefinitionCreate',
        )

    @api.model
    def _classify_direct_binding_namespace(self, result):
        def success(payload):
            created = payload.get('createdDefinition')
            if not isinstance(created, dict) or not created.get('id'):
                return 'no created definition id'
            if created.get('key') != BINDING_METAFIELD_KEY:
                return 'definition key mismatch'
            return True

        return self._classify_user_errors(
            result, success, 'Binding-metafield definition',
            lambda payload: {
                'definition_id': (
                    payload.get('createdDefinition') or {}
                ).get('id'),
            },
        )

    @api.model
    def _reconcile_binding_namespace(self, attempt):
        """A definition that already exists is the desired end state."""
        store = attempt.store_id
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportBindingDefinition($key: String!) { '
            'metafieldDefinitions(first: 1, ownerType: PRODUCT, key: $key) { '
            'nodes { id key } } shop { myshopifyDomain } }'
        )
        result = client.execute(store, query, {'key': BINDING_METAFIELD_KEY})
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self._reconcile_identity_mismatch(identity)
        nodes = ((data.get('metafieldDefinitions') or {}).get('nodes')) or []
        if nodes:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'The binding-metafield definition exists.',
                'evidence': {'definition_id': nodes[0].get('id')},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_CONFIGURATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'The binding-metafield definition does not exist; the '
                       'create path stays closed until it does.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_binding_namespace(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        preview = self._preview_for_job(job)
        if consequence['action'] != 'succeed':
            self._advance_plan(preview, JOB_TYPE_BINDING_NAMESPACE, False)
            return
        settings = self._settings(job.store_id)
        if settings:
            settings.sudo().write(
                {'product_export_binding_namespace_ready': True}
            )
        self._advance_plan(preview, JOB_TYPE_BINDING_NAMESPACE)

    # ------------------------------------------------------------------
    # Mutation domain: create (the ONLY productSet in this module)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_create(self, job):
        snapshot = self._prepare_local_common(job)
        preview = self._preview_for_job(job)
        snapshot['variant_ids'] = [
            entry['odoo_variant_id']
            for entry in (preview.diff or {}).get('variants_create') or []
        ]
        return snapshot

    @api.model
    def _prepare_preconditions_create(self, local_snapshot, owner_context):
        preview = self._assert_confirmed_preview_pre_c2(local_snapshot)
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        template = self.env['product.template'].browse(
            local_snapshot['template_id']
        ).exists()
        if not template:
            self._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'The product to create no longer exists in Odoo.',
            )
        settings = self._settings(store)
        if not settings or not settings.product_export_binding_namespace_ready:
            self._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'The connector binding-metafield definition is not '
                'established for this store; the create path stays closed.',
            )
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().search([
            ('store_id', '=', store.id),
            ('product_template_id', '=', template.id),
        ], limit=1)
        if binding and binding.shopify_gid:
            # Reconciliation-first, before the mutation rather than after a
            # failure: a binding that appeared since the preview means the
            # product exists and the create path is closed.
            self._fail_closed_pre_c2(
                ERROR_CLASS_DUPLICATE, SUBREASON_DUPLICATE,
                'This product became bound to a Shopify product after the '
                'preview was taken; a create would duplicate it.',
            )

        include_price = self._price_export_allowed(store)
        scalars = self._desired_scalars(template)
        options = self._desired_options(template)
        variants = self.env['product.product'].browse(
            local_snapshot['variant_ids']
        ).exists()
        if len(options) > MAX_PRODUCT_OPTIONS:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'This product has more Shopify options than Shopify allows.',
            )
        if len(variants) > MAX_EXPORT_VARIANTS:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'This product has more variants than one export job carries.',
            )

        product_input = dict(scalars)
        if options:
            product_input['productOptions'] = [
                {'name': option['name'],
                 'values': [{'name': value} for value in option['values']]}
                for option in options
            ]
        product_input['variants'] = [
            self._create_variant_input(store, variant, include_price, options)
            for variant in variants
        ]
        # The create shape claims exactly the connector-owned surface. No
        # `collections`, no `metafields`, no `files`: a brand-new product has
        # none, and claiming ownership of them here is what would make the
        # second export destructive.
        for merchant_owned in ('collections', 'metafields', 'files'):
            product_input.pop(merchant_owned, None)

        operation = (
            'mutation ProductExportCreate($input: ProductSetInput!, '
            '$identifier: ProductSetIdentifiers!) { '
            'productSet(input: $input, identifier: $identifier, '
            'synchronous: true) { '
            'product { id handle title status updatedAt '
            'variants(first: %d) { nodes { id barcode '
            'inventoryItem { id sku } } } } '
            'userErrors { code field message } } }' % (MAX_EXPORT_VARIANTS,)
        )
        variables = {
            'input': product_input,
            'identifier': {
                'customId': {
                    # `namespace` omitted: 2026-07 documents that the
                    # app-reserved namespace is used, which is the one a
                    # connector should own.
                    'key': BINDING_METAFIELD_KEY,
                    'value': str(template.id),
                },
            },
        }
        self._assert_no_product_set_on_existing(operation, local_snapshot)
        return self._mutation_request(
            JOB_TYPE_CREATE, local_snapshot, operation, variables,
            {'template_id': template.id,
             'variant_count': len(variants),
             'status': scalars['status']},
            {'custom_id_value': str(template.id),
             'variant_ids': variants.ids,
             'price_exported': include_price,
             'snapshot_taken_at': fields.Datetime.to_string(
                 fields.Datetime.now()
             )},
        )

    @api.model
    def _create_variant_input(self, store, variant, include_price, options):
        desired = self._desired_variant(store, variant, include_price)
        entry = {
            'barcode': desired['barcode'],
            'inventoryItem': {'sku': desired['inventoryItem']['sku']},
        }
        if options:
            entry['optionValues'] = desired.get('optionValues') or []
        if include_price:
            entry['price'] = desired['price']
            if 'compareAtPrice' in desired:
                entry['compareAtPrice'] = desired['compareAtPrice']
        return entry

    @api.model
    def _transport_create(self, request, attempt_context):
        return self._transport(request, attempt_context, 'productSet')

    @api.model
    def _classify_direct_create(self, result):
        def success(payload):
            product = payload.get('product')
            if not isinstance(product, dict) or not product.get('id'):
                return 'no created product id'
            return True

        return self._classify_user_errors(
            result, success, 'Product create',
            lambda payload: {'product': payload.get('product')},
        )

    @api.model
    def _reconcile_create(self, attempt):
        """Reconcile by the connector's own custom id, never by title.

        This is the read that makes an ambiguous create safe: found once →
        adopt and bind; found more than once → review (this connector will
        not choose between two products); not found → the attempt did not
        apply.
        """
        store = attempt.store_id
        template_id = (attempt.preconditions_snapshot or {}).get(
            'custom_id_value'
        )
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportReconcileCreate($query: String!) { '
            'products(first: 2, query: $query) { nodes { id title '
            'updatedAt variants(first: %d) { nodes { id '
            'inventoryItem { id sku } } } } } '
            'shop { myshopifyDomain } }' % (MAX_EXPORT_VARIANTS,)
        )
        search = 'metafields.%s:%s' % (BINDING_METAFIELD_KEY, template_id)
        result = client.execute(store, query, {'query': search})
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self._reconcile_identity_mismatch(identity)
        nodes = ((data.get('products') or {}).get('nodes')) or []
        if len(nodes) == 1:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'A product carrying this binding id exists; '
                           'adopting it.',
                'evidence': {'product': nodes[0]},
            }
        if len(nodes) > 1:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity,
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_DUPLICATE,
                'manual_review_subreason': SUBREASON_DUPLICATE,
                'message': 'More than one Shopify product carries this '
                           'binding id. A reviewer must resolve it.',
                'evidence': {'product_gids': [
                    node.get('id') for node in nodes
                ]},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'No product carries this binding id; the create did '
                       'not apply. A reviewer releases the retry.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_create(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        preview = self._preview_for_job(job)
        if consequence['action'] != 'succeed':
            self._advance_plan(preview, JOB_TYPE_CREATE, False)
            return
        evidence = consequence.get('evidence') or {}
        product = evidence.get('product') or {}
        product_gid = product.get('id')
        if not product_gid:
            _logger.warning(
                'Product export create succeeded for preview %d without a '
                'product GID in the evidence; no binding was written.',
                preview.id,
            )
            self._advance_plan(preview, JOB_TYPE_CREATE, False)
            return
        binding = self._bind_created_product(job.store_id, preview, product)
        preview._preview_surface('_record_created_binding').write({
            'product_template_binding_id': binding.id,
            'remote_product_gid': product_gid,
            'remote_updated_at': product.get('updatedAt') or False,
        })
        preview.invalidate_recordset()
        self._advance_plan(preview, JOB_TYPE_CREATE)

    @api.model
    def _bind_created_product(self, store, preview, product):
        """Write the bindings immediately, so the next run takes the update
        path and no second create is ever possible."""
        TemplateBinding = self.env[
            'shopify.connector.product.template.binding'
        ]
        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ]
        template = preview.product_template_id
        binding = TemplateBinding.sudo().search([
            ('store_id', '=', store.id),
            ('product_template_id', '=', template.id),
        ], limit=1)
        values = {
            'shopify_gid': product.get('id'),
            'shopify_title': product.get('title'),
            'shopify_updated_at': product.get('updatedAt'),
            'status': 'active',
            'match_key': 'existing_binding',
        }
        if binding:
            binding.sudo().write(values)
        else:
            binding = TemplateBinding.sudo().create(dict(
                values,
                store_id=store.id,
                product_template_id=template.id,
            ))
        remote_variants = (
            (product.get('variants') or {}).get('nodes')
        ) or []
        # Variant identity is matched by SKU exactly once, here, at the
        # moment the connector itself created them and therefore knows what
        # it asked for. This is not name-matching: it is reading back the
        # identity of rows this attempt authored.
        by_sku = {}
        for entry in remote_variants:
            sku = ((entry or {}).get('inventoryItem') or {}).get('sku')
            if sku:
                by_sku[sku] = entry.get('id')
        for variant in template.product_variant_ids:
            gid = by_sku.get(variant.default_code)
            if not gid:
                continue
            existing = VariantBinding.sudo().search([
                ('store_id', '=', store.id),
                ('product_variant_id', '=', variant.id),
            ], limit=1)
            variant_values = {
                'shopify_gid': gid,
                'product_template_binding_id': binding.id,
                'status': 'active',
                'match_key': 'existing_binding',
            }
            if existing:
                existing.sudo().write(variant_values)
            else:
                VariantBinding.sudo().create(dict(
                    variant_values,
                    store_id=store.id,
                    product_variant_id=variant.id,
                ))
        return binding

    # ------------------------------------------------------------------
    # Mutation domain: scalar update (productUpdate)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_update(self, job):
        return self._prepare_local_common(job)

    @api.model
    def _prepare_preconditions_update(self, local_snapshot, owner_context):
        preview = self._assert_confirmed_preview_pre_c2(local_snapshot)
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        template = self.env['product.template'].browse(
            local_snapshot['template_id']
        ).exists()
        if not template or not local_snapshot['remote_product_gid']:
            self._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'This update has no Odoo product or no bound Shopify '
                'product.',
            )
        confirmed_fields = set()
        for step in (preview.apply_plan or {}).get('steps') or []:
            if step['step'] == JOB_TYPE_UPDATE:
                confirmed_fields = set(step.get('fields') or [])
        if not confirmed_fields:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No scalar field change was confirmed for this product.',
            )
        desired = self._desired_scalars(template)
        # Only the fields the operator saw. A field that drifted after the
        # preview is not quietly added to the payload.
        product_input = {
            name: value
            for name, value in desired.items()
            if name in confirmed_fields
        }
        outside = set(product_input) - PRODUCT_SCALAR_ALLOWLIST
        if outside:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DATA_SHAPE, SUBREASON_BINDING_CONFLICT,
                'The update payload contained non-allowlisted fields.',
            )
        variables = {
            'product': product_input,
            'identifier': {'id': local_snapshot['remote_product_gid']},
        }
        # `identifier.id` is the preferred targeting form; `ProductSetInput.id`
        # still exists but is deprecated, and `productUpdate` takes its target
        # through `ProductUpdateIdentifiers` rather than inside the input.
        assert_no_forbidden_keys(variables)
        operation = (
            'mutation ProductExportUpdate('
            '$product: ProductUpdateInput!, '
            '$identifier: ProductUpdateIdentifiers!) { '
            'productUpdate(product: $product, identifier: $identifier) { '
            'product { id updatedAt title descriptionHtml vendor '
            'productType tags status } '
            'userErrors { field message } } }'
        )
        self._assert_no_product_set_on_existing(operation, local_snapshot)
        return self._mutation_request(
            JOB_TYPE_UPDATE, local_snapshot, operation, variables,
            {'product_gid': local_snapshot['remote_product_gid'],
             'fields': sorted(product_input)},
            {'product_gid': local_snapshot['remote_product_gid'],
             'expected': product_input,
             'remote_updated_at': preview.remote_updated_at,
             'snapshot_taken_at': fields.Datetime.to_string(
                 fields.Datetime.now()
             )},
        )

    @api.model
    def _transport_update(self, request, attempt_context):
        return self._transport(request, attempt_context, 'productUpdate')

    @api.model
    def _classify_direct_update(self, result):
        def success(payload):
            product = payload.get('product')
            if not isinstance(product, dict) or not product.get('id'):
                return 'no product in response'
            return True

        return self._classify_user_errors(
            result, success, 'Product update',
            lambda payload: {
                'updated_at': (payload.get('product') or {}).get('updatedAt'),
            },
        )

    @api.model
    def _reconcile_update(self, attempt):
        """Compare the remote scalars against exactly what was requested."""
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        product_gid = snapshot.get('product_gid')
        expected = snapshot.get('expected') or {}
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportReconcileUpdate($id: ID!) { '
            'product(id: $id) { id title descriptionHtml vendor productType '
            'tags status updatedAt } shop { myshopifyDomain } }'
        )
        result = client.execute(store, query, {'id': product_gid})
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self._reconcile_identity_mismatch(identity)
        product = data.get('product')
        if not isinstance(product, dict):
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_BINDING_CONFLICT,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'The bound product could not be read during '
                           'reconciliation.',
                'evidence': {},
            }
        matches = all(
            (sorted(product.get(name) or []) == sorted(value))
            if name == 'tags' else ((product.get(name) or '') == value)
            for name, value in expected.items()
        )
        if matches:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Every requested scalar matches Shopify.',
                'evidence': {'updated_at': product.get('updatedAt')},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'Shopify does not carry the requested scalar values. '
                       'A reviewer decides whether to re-preview.',
            'evidence': {'updated_at': product.get('updatedAt')},
        }

    @api.model
    def _apply_consequence_update(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        preview = self._preview_for_job(job)
        succeeded = consequence['action'] == 'succeed'
        if succeeded:
            binding = preview.product_template_binding_id
            if binding:
                updated_at = (consequence.get('evidence') or {}).get(
                    'updated_at'
                )
                if updated_at:
                    binding.sudo().write({'shopify_updated_at': updated_at})
        self._advance_plan(preview, JOB_TYPE_UPDATE, succeeded)

    # ------------------------------------------------------------------
    # Mutation domain: variant update (productVariantsBulkUpdate)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_variants_update(self, job):
        return self._prepare_local_common(job)

    @api.model
    def _prepare_preconditions_variants_update(
        self, local_snapshot, owner_context,
    ):
        preview = self._assert_confirmed_preview_pre_c2(local_snapshot)
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        include_price = self._price_export_allowed(store)
        confirmed_gids = []
        for step in (preview.apply_plan or {}).get('steps') or []:
            if step['step'] == JOB_TYPE_VARIANTS_UPDATE:
                confirmed_gids = list(step.get('variant_gids') or [])
        if not confirmed_gids:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No variant update was confirmed for this product.',
            )
        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ]
        rows = VariantBinding.sudo().search([
            ('store_id', '=', store.id),
            ('shopify_gid', 'in', confirmed_gids),
        ])
        if len(rows) != len(set(confirmed_gids)):
            self._fail_closed_pre_c2(
                ERROR_CLASS_BINDING_CONFLICT, SUBREASON_BINDING_CONFLICT,
                'A confirmed variant is no longer bound; refusing to write '
                'variants whose identity changed since the preview.',
            )
        variants_input = []
        for row in rows:
            desired = self._desired_variant(
                store, row.product_variant_id, include_price,
            )
            entry = {
                'id': row.shopify_gid,
                'barcode': desired['barcode'],
                'inventoryItem': {'sku': desired['inventoryItem']['sku']},
            }
            if include_price:
                entry['price'] = desired['price']
                if 'compareAtPrice' in desired:
                    entry['compareAtPrice'] = desired['compareAtPrice']
            # `optionValues` is deliberately NOT sent on an update: the
            # preview refuses to plan a variant update while the option
            # structure diverges, and re-asserting option values against a
            # structure this connector did not author is how a variant ends
            # up describing something else.
            variants_input.append(entry)
        variables = {
            'productId': local_snapshot['remote_product_gid'],
            'variants': variants_input,
            # All-or-nothing. A partially applied variant batch is the
            # hardest state to reason about afterwards, so it is refused at
            # the API level rather than reconciled later.
            'allowPartialUpdates': False,
        }
        # `variants` here is the mutation's own required argument, not a
        # declarative product-input list, so the forbidden-key guard is run
        # on the ENTRIES rather than the envelope.
        for entry in variants_input:
            assert_no_forbidden_keys(
                {key: value for key, value in entry.items() if key != 'id'},
                'variants[]',
            )
        operation = (
            'mutation ProductExportVariantsUpdate($productId: ID!, '
            '$variants: [ProductVariantsBulkInput!]!, '
            '$allowPartialUpdates: Boolean) { '
            'productVariantsBulkUpdate(productId: $productId, '
            'variants: $variants, '
            'allowPartialUpdates: $allowPartialUpdates) { '
            'productVariants { id barcode price compareAtPrice '
            'inventoryItem { id sku } } '
            'userErrors { code field message } } }'
        )
        self._assert_no_product_set_on_existing(operation, local_snapshot)
        return self._mutation_request(
            JOB_TYPE_VARIANTS_UPDATE, local_snapshot, operation, variables,
            {'product_gid': local_snapshot['remote_product_gid'],
             'variant_gids': sorted(confirmed_gids)},
            {'product_gid': local_snapshot['remote_product_gid'],
             'expected_variants': variants_input,
             'price_exported': include_price,
             'snapshot_taken_at': fields.Datetime.to_string(
                 fields.Datetime.now()
             )},
        )

    @api.model
    def _transport_variants_update(self, request, attempt_context):
        return self._transport(
            request, attempt_context, 'productVariantsBulkUpdate',
        )

    @api.model
    def _classify_direct_variants_update(self, result):
        def success(payload):
            variants = payload.get('productVariants')
            if not isinstance(variants, list) or not variants:
                return 'no updated variants returned'
            return True

        return self._classify_user_errors(result, success, 'Variant update')

    @api.model
    def _reconcile_variants_update(self, attempt):
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        expected = snapshot.get('expected_variants') or []
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportReconcileVariants($id: ID!) { '
            'product(id: $id) { id variants(first: %d) { nodes { id barcode '
            'price compareAtPrice inventoryItem { id sku } } } } '
            'shop { myshopifyDomain } }' % (MAX_EXPORT_VARIANTS,)
        )
        result = client.execute(store, query, {'id': snapshot.get('product_gid')})
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self._reconcile_identity_mismatch(identity)
        product = data.get('product')
        if not isinstance(product, dict):
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_BINDING_CONFLICT,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'The bound product could not be read during '
                           'variant reconciliation.',
                'evidence': {},
            }
        current = {
            entry.get('id'): entry
            for entry in ((product.get('variants') or {}).get('nodes')) or []
            if isinstance(entry, dict)
        }
        applied = True
        for entry in expected:
            observed = current.get(entry.get('id'))
            if not observed:
                applied = False
                break
            if (observed.get('barcode') or '') != (entry.get('barcode') or ''):
                applied = False
                break
            observed_sku = (observed.get('inventoryItem') or {}).get('sku') or ''
            if observed_sku != (entry.get('inventoryItem') or {}).get('sku', ''):
                applied = False
                break
            if 'price' in entry and _money(
                float(observed.get('price') or 0.0)
            ) != entry['price']:
                applied = False
                break
        if applied:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Every confirmed variant matches Shopify.',
                'evidence': {},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'Shopify does not carry the confirmed variant values.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_variants_update(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        preview = self._preview_for_job(job)
        self._advance_plan(
            preview, JOB_TYPE_VARIANTS_UPDATE,
            consequence['action'] == 'succeed',
        )

    # ------------------------------------------------------------------
    # Mutation domain: variant create (productVariantsBulkCreate)
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_variants_create(self, job):
        return self._prepare_local_common(job)

    @api.model
    def _prepare_preconditions_variants_create(
        self, local_snapshot, owner_context,
    ):
        preview = self._assert_confirmed_preview_pre_c2(local_snapshot)
        store = self.env['shopify.connector.store'].browse(
            local_snapshot['store_id']
        )
        include_price = self._price_export_allowed(store)
        confirmed_ids = []
        for step in (preview.apply_plan or {}).get('steps') or []:
            if step['step'] == JOB_TYPE_VARIANTS_CREATE:
                confirmed_ids = list(step.get('variant_ids') or [])
        if not confirmed_ids:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No variant creation was confirmed for this product.',
            )
        variants = self.env['product.product'].browse(confirmed_ids).exists()
        if len(variants) != len(set(confirmed_ids)):
            self._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'A confirmed new variant no longer exists in Odoo.',
            )
        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ]
        already = VariantBinding.sudo().search_count([
            ('store_id', '=', store.id),
            ('product_variant_id', 'in', variants.ids),
        ])
        if already:
            self._fail_closed_pre_c2(
                ERROR_CLASS_DUPLICATE, SUBREASON_DUPLICATE,
                'A confirmed new variant became bound after the preview; '
                'creating it again would duplicate it.',
            )
        options = self._desired_options(preview.product_template_id)
        variants_input = []
        for variant in variants:
            desired = self._desired_variant(store, variant, include_price)
            entry = {
                'barcode': desired['barcode'],
                'inventoryItem': {'sku': desired['inventoryItem']['sku']},
            }
            if options and desired.get('optionValues'):
                entry['optionValues'] = desired['optionValues']
            if include_price:
                entry['price'] = desired['price']
                if 'compareAtPrice' in desired:
                    entry['compareAtPrice'] = desired['compareAtPrice']
            variants_input.append(entry)
        variables = {
            'productId': local_snapshot['remote_product_gid'],
            'variants': variants_input,
            # PRESERVE_STANDALONE_VARIANT, never DEFAULT: 2026-07 documents
            # that DEFAULT "Deletes the standalone default ("Default Title")
            # variant when it's the only variant on the product". A remote
            # deletion is not available to this module, so the strategy that
            # performs one is not either.
            'strategy': 'PRESERVE_STANDALONE_VARIANT',
        }
        for entry in variants_input:
            assert_no_forbidden_keys(entry, 'variants[]')
        operation = (
            'mutation ProductExportVariantsCreate($productId: ID!, '
            '$variants: [ProductVariantsBulkInput!]!, '
            '$strategy: ProductVariantsBulkCreateStrategy) { '
            'productVariantsBulkCreate(productId: $productId, '
            'variants: $variants, strategy: $strategy) { '
            'productVariants { id barcode inventoryItem { id sku } } '
            'userErrors { code field message } } }'
        )
        self._assert_no_product_set_on_existing(operation, local_snapshot)
        return self._mutation_request(
            JOB_TYPE_VARIANTS_CREATE, local_snapshot, operation, variables,
            {'product_gid': local_snapshot['remote_product_gid'],
             'odoo_variant_ids': sorted(variants.ids)},
            {'product_gid': local_snapshot['remote_product_gid'],
             'odoo_variant_ids': sorted(variants.ids),
             'expected_skus': sorted(
                 entry['inventoryItem']['sku'] for entry in variants_input
             ),
             'snapshot_taken_at': fields.Datetime.to_string(
                 fields.Datetime.now()
             )},
        )

    @api.model
    def _transport_variants_create(self, request, attempt_context):
        return self._transport(
            request, attempt_context, 'productVariantsBulkCreate',
        )

    @api.model
    def _classify_direct_variants_create(self, result):
        def success(payload):
            variants = payload.get('productVariants')
            if not isinstance(variants, list) or not variants:
                return 'no created variants returned'
            return True

        return self._classify_user_errors(
            result, success, 'Variant create',
            lambda payload: {'variants': payload.get('productVariants')},
        )

    @api.model
    def _reconcile_variants_create(self, attempt):
        """Adopt-if-found by SKU on the variants this attempt authored."""
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        expected_skus = set(snapshot.get('expected_skus') or [])
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportReconcileVariantCreate($id: ID!) { '
            'product(id: $id) { id variants(first: %d) { nodes { id '
            'inventoryItem { id sku } } } } '
            'shop { myshopifyDomain } }' % (MAX_EXPORT_VARIANTS,)
        )
        result = client.execute(store, query, {'id': snapshot.get('product_gid')})
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self._reconcile_identity_mismatch(identity)
        product = data.get('product')
        if not isinstance(product, dict):
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_BINDING_CONFLICT,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'The bound product could not be read during '
                           'variant-create reconciliation.',
                'evidence': {},
            }
        nodes = ((product.get('variants') or {}).get('nodes')) or []
        observed = {
            ((entry or {}).get('inventoryItem') or {}).get('sku'): entry.get('id')
            for entry in nodes
        }
        found = {sku for sku in expected_skus if observed.get(sku)}
        if expected_skus and found == expected_skus:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Every confirmed new variant exists on Shopify; '
                           'adopting them.',
                'evidence': {'variants': nodes},
            }
        if found:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity,
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'Only some confirmed variants exist on Shopify. A '
                           'reviewer resolves the partial state; this '
                           'connector will not guess the rest.',
                'evidence': {'found_skus': sorted(found)},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'None of the confirmed variants exist on Shopify; the '
                       'create did not apply.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_variants_create(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        preview = self._preview_for_job(job)
        succeeded = consequence['action'] == 'succeed'
        if succeeded:
            self._bind_created_variants(
                job.store_id, preview,
                (consequence.get('evidence') or {}).get('variants') or [],
            )
        self._advance_plan(preview, JOB_TYPE_VARIANTS_CREATE, succeeded)

    @api.model
    def _bind_created_variants(self, store, preview, remote_variants):
        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ]
        binding = preview.product_template_binding_id
        if not binding:
            return
        by_sku = {}
        for entry in remote_variants:
            sku = ((entry or {}).get('inventoryItem') or {}).get('sku')
            if sku:
                by_sku[sku] = entry.get('id')
        for variant in preview.product_template_id.product_variant_ids:
            gid = by_sku.get(variant.default_code)
            if not gid:
                continue
            existing = VariantBinding.sudo().search([
                ('store_id', '=', store.id),
                ('product_variant_id', '=', variant.id),
            ], limit=1)
            if existing:
                continue
            VariantBinding.sudo().create({
                'store_id': store.id,
                'product_variant_id': variant.id,
                'product_template_binding_id': binding.id,
                'shopify_gid': gid,
                'status': 'active',
                'match_key': 'existing_binding',
            })

    # ------------------------------------------------------------------
    # Shared reconciliation helpers and the reconciliation handler
    # ------------------------------------------------------------------

    @api.model
    def _reconcile_identity_mismatch(self, observed_identity):
        return {
            'verdict': 'not_applied',
            'observed_store_identity': observed_identity or '',
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_STORE_IDENTITY,
            'manual_review_subreason': SUBREASON_STORE_IDENTITY,
            'message': 'Reconciliation observed a different Shopify store '
                       'identity than the attempt expected.',
            'evidence': {},
        }

    @api.model
    def _handle_product_export_mutation_reconcile(self, job):
        """The shared read-only reconciliation handler for every export
        mutation domain.

        Dispatches purely on `attempt.mutation_domain`, mirroring core's own
        generic reconciliation-handler shape and the Task 013 precedent. The
        exception ordering below is deliberate and matches LL-013: a failure
        *executing* the read retries through the ordinary read-safe path,
        while only a result the strategy actually returned but that fails
        schema validation blocks the original job. Conflating the two would
        let a transient read error masquerade as malformed evidence and
        block a mutation that may well have applied.
        """
        Dispatch = self.env['shopify.connector.job.dispatch']
        attempt = job.mutation_attempt_id
        if not attempt:
            job._transition_failed_final(
                'unknown_system_error',
                'The reconciliation job has no mutation-attempt link.',
            )
            return
        original = attempt.job_id
        if attempt.observed_outcome == 'pending':
            Dispatch._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE,
                'Pending attempt reached reconciliation without recovery.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Pending reconciliation attempt was refused.',
            )
            return
        if attempt.effective_disposition() != 'unresolved':
            Dispatch._complete_reconciliation_job(
                job, 'Mutation attempt was already resolved.',
            )
            return
        try:
            strategy = Dispatch._validated_mutation_strategy(
                attempt.mutation_domain
            )
        except ValidationError:
            Dispatch._block_original_job(
                original, 'no_reconciliation_strategy',
                'no_reconciliation_strategy',
                'No valid reconciliation strategy is registered.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Missing strategy was routed to the original job.',
            )
            return
        try:
            result = strategy['reconcile'](attempt)
        except JobHandlerError:
            raise
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The export reconciliation read failed transiently; retry '
                'required.',
                type(exc).__name__,
            ) from exc
        try:
            normalized = Dispatch._validate_reconciliation_result(result)
        except Exception:
            Dispatch._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE,
                'The reconciliation result was malformed; no resend '
                'occurred.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Malformed read result was routed to the original job.',
            )
            return
        if normalized['observed_store_identity'] != (
            attempt.expected_store_identity
        ):
            Dispatch._block_original_job(
                original, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Reconciliation observed a different Shopify store identity.',
            )
            Dispatch._complete_reconciliation_job(
                job, 'Store-identity mismatch was routed without a verdict.',
            )
            return
        if normalized['verdict'] == 'inconclusive':
            count = attempt._record_inconclusive_reconciliation(
                normalized['evidence']
            )
            if count >= INCONCLUSIVE_RECONCILIATION_CAP:
                Dispatch._block_original_job(
                    original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE,
                    'Reconciliation remained inconclusive at the safety cap.',
                )
                Dispatch._complete_reconciliation_job(
                    job, 'Inconclusive reconciliation reached its safety cap.',
                )
            else:
                job._transition_retry_waiting(
                    fields.Datetime.now() + timedelta(minutes=5),
                    job.retry_count + 1,
                    ERROR_CLASS_TEMPORARY,
                    normalized['message'],
                )
            return
        disposition = (
            'applied' if normalized['verdict'] == 'applied' else 'not_applied'
        )
        try:
            with self.env.cr.savepoint():
                attempt._record_reconciliation_result(
                    disposition, normalized['evidence'],
                )
                Dispatch._apply_validated_consequence(
                    original, attempt, 'reconciliation',
                    normalized['consequence'], strategy,
                    reconciliation_job=job,
                )
                Dispatch._complete_reconciliation_job(
                    job, 'Read-only export reconciliation completed.',
                )
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'Atomic reconciliation consequence failed; read retry '
                'required.',
                type(exc).__name__,
            ) from exc
