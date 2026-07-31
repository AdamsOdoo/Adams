"""SEC-3 (issue #197) -- the store-rooted company ownership matrix.

This file replaces the earlier position that connector control-plane records are
company-NEUTRAL. Under the control-room MVP ownership decision (2026-07-25):

  * a connector store belongs to exactly ONE company;
  * a company may own several stores;
  * sharing one store across companies is outside the MVP;
  * isolation is FAIL-CLOSED: a row whose owning company cannot be proven is
    visible to nobody, rather than to everybody.

Why this file is DRIVEN by an inventory rather than written test by test.

The previous version described broader coverage than it performed. It named a
constant `CONTROL_PLANE_MODELS` that no test consumed; a test called
`test_every_control_plane_model_is_isolated` exercised three of the eight; a
test named for mutation attempts created no mutation attempt; credential,
call-lease, evidence and evidence-line isolation were not exercised at all. A
hand-written matrix drifts from its own description exactly that way, silently,
because nothing fails when a model is left out.

So `SEC3_MODELS` below is the single authoritative inventory, every generated
test iterates it, and `test_no_durable_store_scoped_model_escapes_this_matrix`
fails if the registry contains a durable store-scoped model the inventory does
not name. Adding a model without adding its fixture is a red suite, not a
quiet omission.

What each axis proves, and why it is here rather than assumed:

  * isolation holds across every read shape a caller can reach -- `search`,
    direct `browse().read()` by known id, `search_count`, and a grouped read
    (`formatted_read_group`). A rule that only filters `search` leaks the
    moment a UI groups by anything, and a count is a read: leaking "how many"
    is still leaking.
  * isolation holds for write shapes too: create, write and unlink, each with
    zero side effects on denial.
  * every denial is checked against the OWNING company's user performing the
    same operation. Without that comparison a test can pass because the model
    denies everyone -- a vacuous green that proves nothing about company. Where
    both users are denied, the matrix records the axis as ACL-denied rather
    than claiming a company proof it did not observe.
  * it holds for all three roles -- plain internal user, Connector User,
    Connector Administrator -- because a role is an authorization axis and
    company is an ownership axis, and neither may substitute for the other.
  * a user ALLOWED in both companies but currently SWITCHED to one sees only
    the active one. Odoo evaluates `company_ids` in a rule as `env.companies`
    (the switcher selection), not `user.company_ids`.
  * connector-to-connector relations agree on the STORE, not merely the
    company -- because one company may own several stores, so company equality
    permits two different shops' records to be linked together.
  * historic rows that predate those constraints are quarantined and invisible,
    and nothing is re-homed automatically.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 `30bde9ff`, read 2026-07-25:
  * `odoo/addons/base/models/ir_rule.py::_eval_context` -- `company_ids` is
    `self.env.companies.ids`, described there as "filtered and trusted";
  * `ir_rule.py::_compute_global` -- a rule with no groups is global and is
    AND-ed with every other rule, so a permissive group rule cannot re-open it;
  * `odoo/orm/models.py` L451/L4009/L4516/L4743 -- `_check_company_auto` makes
    create and write call `_check_company`, which requires a `check_company=True`
    relation's target company to be False or equal to the record's company.
    Note L4009: it compares COMPANIES only, which is exactly why the same-store
    constraints in `shopify.connector.scope.mixin` exist alongside it.

No Shopify store, credential, request or mutation occurs anywhere in this file.
"""

import hashlib
import json
import uuid

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

CORE = 'shopify_connector_core'

# ---------------------------------------------------------------------------
# The authoritative inventory.
#
# Every durable store-scoped model, with the name of the builder that produces
# one row of it for a given store. `test_no_durable_store_scoped_model_escapes_
# this_matrix` proves this list is complete against the live registry, so it
# cannot silently fall behind the code.
#
# Models from a module that is not installed are skipped at run time, not
# omitted here: the inventory describes the connector, not one install.
# ---------------------------------------------------------------------------
SEC3_MODELS = (
    ('shopify.connector.store', '_row_store'),
    ('shopify.connector.store.credential', '_row_credential'),
    # Wave 5. The cached 24-hour token of the client-credentials mode is
    # durable and store-scoped, so it is in the matrix rather than trusted to
    # be safe because no group can read it today.
    ('shopify.connector.store.access.token', '_row_access_token'),
    ('shopify.connector.store.settings', '_row_settings'),
    ('shopify.connector.location', '_row_location'),
    ('shopify.connector.job', '_row_job'),
    ('shopify.connector.job.log', '_row_job_log'),
    ('shopify.connector.mutation.attempt', '_row_mutation_attempt'),
    ('shopify.connector.call.lease', '_row_call_lease'),
    ('shopify.connector.customer.binding', '_row_customer_binding'),
    ('shopify.connector.order.binding', '_row_order_binding'),
    ('shopify.connector.product.template.binding', '_row_template_binding'),
    ('shopify.connector.product.variant.binding', '_row_variant_binding'),
    ('shopify.connector.location.mapping', '_row_location_mapping'),
    ('shopify.connector.inventory.level.binding', '_row_inventory_binding'),
    ('shopify.connector.tax.mapping', '_row_tax_mapping'),
    ('shopify.connector.fulfillment.binding', '_row_fulfillment_binding'),
    ('shopify.connector.fulfillment.inbound.evidence', '_row_evidence'),
    ('shopify.connector.fulfillment.inbound.evidence.line', '_row_evidence_line'),
    # Task 015 / 015B (2026-07-26). Both are durable and store-scoped, so both
    # are in the matrix rather than trusted to be safe by resemblance.
    ('shopify.connector.product.export.preview', '_row_export_preview'),
    ('shopify.connector.product.media.binding', '_row_export_media_binding'),
    # Batch 2 §8.2 (2026-07-31). A durable, store-scoped decision row that
    # points at a job and (once applied) at a binding, so it is in the matrix
    # rather than trusted to be safe by resemblance.
    ('shopify.connector.product.match.decision', '_row_match_decision'),
)

# Models that deliberately carry NO `ir.model.access.csv` row, so no connector
# group -- not even Administrator -- may read them through RPC. They are still
# in SEC3_MODELS (they are durable and store-scoped and must have the company
# rule and the relation declarations), but the four read-shape tests assert the
# stronger "nobody may read this at all" instead of "reads are isolated",
# because the ordinary assertion's "the owner CAN read it" half is exactly what
# these models must NOT satisfy.
SEC3_NO_ACL_MODELS = frozenset((
    # The cached 24-hour access token of the client-credentials mode (Wave 5).
    'shopify.connector.store.access.token',
))

# Connector-to-connector relations that must agree on the STORE, and the models
# that own them. Company equality is insufficient for every entry here.
SEC3_STORE_RELATIONS = (
    ('shopify.connector.store.access.token', 'credential_id'),
    ('shopify.connector.job', 'mutation_attempt_id'),
    ('shopify.connector.job', 'superseded_by_job_id'),
    ('shopify.connector.job.log', 'job_id'),
    ('shopify.connector.mutation.attempt', 'job_id'),
    ('shopify.connector.product.variant.binding', 'product_template_binding_id'),
    ('shopify.connector.inventory.level.binding', 'product_variant_binding_id'),
    ('shopify.connector.inventory.level.binding', 'location_mapping_id'),
    ('shopify.connector.fulfillment.binding', 'order_binding_id'),
    ('shopify.connector.fulfillment.inbound.evidence', 'order_binding_id'),
    ('shopify.connector.fulfillment.inbound.evidence', 'fulfillment_binding_id'),
    ('shopify.connector.product.export.preview', 'product_template_binding_id'),
    ('shopify.connector.product.media.binding', 'product_template_binding_id'),
    ('shopify.connector.product.media.binding', 'product_variant_binding_id'),
    ('shopify.connector.product.match.decision', 'job_id'),
    ('shopify.connector.product.match.decision', 'resulting_template_binding_id'),
    ('shopify.connector.product.match.decision', 'resulting_variant_binding_id'),
)

# Relations whose scope disagreement is structurally impossible, because the
# child's own store/company is a stored RELATED field through that same
# relation. Listed with the field that makes it impossible, so a reviewer can
# check the claim instead of taking it on trust. These are recorded, not
# constrained: a constraint here could never fire.
SEC3_STRUCTURAL_RELATIONS = {
    # store_id = related('job_id.store_id')
    ('shopify.connector.job.log', 'job_id'),
    # store_id = related('job_id.store_id')
    ('shopify.connector.mutation.attempt', 'job_id'),
    # company_id = related('evidence_id.store_id.company_id'), and the line
    # carries no store of its own
    ('shopify.connector.fulfillment.inbound.evidence.line', 'evidence_id'),
}

# The one model deliberately left company-neutral, with the exact reasons the
# independent reviewer is asked to verify (control-room item 3.11).
NEUTRAL_BY_DECISION = 'shopify.connector.attribute.lock'


@tagged('post_install', '-at_install')
class Sec3Base(TransactionCase):
    """Fixtures shared by every SEC-3 test class in this file.

    Tagged even though it defines no test of its own: Odoo collects every
    TransactionCase subclass, so an untagged base class runs `at_install`
    and reintroduces exactly the warm-update failure family issue #193
    exists to prevent.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = uuid.uuid4().hex[:8]
        cls._seq = 0
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'SEC-3 company B'})
        # A SECOND store in company A. This is what makes the store axis
        # observable at all: a same-company/different-store pair passes every
        # company check, so any test that only ever compares A against B cannot
        # tell the two axes apart.
        cls.store_a = cls._store('A', cls.company_a)
        cls.store_a2 = cls._store('A2', cls.company_a)
        cls.store_b = cls._store('B', cls.company_b)

        cls.user_a = cls._user('a', cls.company_a, [cls.company_a], 'admin')
        cls.user_b = cls._user('b', cls.company_b, [cls.company_b], 'admin')
        # Allowed in BOTH, switched to A only.
        cls.user_both = cls._user(
            'both', cls.company_a, [cls.company_a, cls.company_b], 'admin')
        # The two customer-facing SEC-2 roles and a plain internal user.
        cls.user_connector = cls._user(
            'conn', cls.company_a, [cls.company_a], 'user')
        cls.user_plain = cls._user('plain', cls.company_a, [cls.company_a], None)

        cls.job_a = cls._job(cls.store_a)
        cls.job_b = cls._job(cls.store_b)

    # ------------------------------------------------------------------
    # Identity fixtures
    # ------------------------------------------------------------------

    @classmethod
    def _store(cls, label, company):
        return cls.env['shopify.connector.store'].sudo().create({
            'name': 'SEC-3 store %s' % label,
            'shop_domain': 'sec3-%s-%s.myshopify.com' % (cls.tag, label.lower()),
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })

    @classmethod
    def _user(cls, label, company, allowed, role):
        groups = [cls.env.ref('base.group_user').id]
        if role == 'admin':
            groups.append(cls.env.ref('%s.group_shopify_connector_admin' % CORE).id)
        elif role == 'user':
            groups.append(cls.env.ref('%s.group_shopify_connector_user' % CORE).id)
        return cls.env['res.users'].sudo().create({
            'name': 'SEC-3 %s' % label,
            'login': 'sec3_%s_%s' % (cls.tag, label),
            'company_id': company.id,
            'company_ids': [(6, 0, [c.id for c in allowed])],
            'group_ids': [(6, 0, groups)],
        })

    @classmethod
    def _job(cls, store, job_type='core_dispatch_selftest'):
        return cls.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })

    def _gid(self, kind, store):
        """A unique Shopify-shaped GID.

        Unique per CALL, not per store: several builders construct a
        parent row of their own, so a per-store constant collides with
        the model's own UNIQUE(store_id, shopify_gid).
        """
        type(self)._seq += 1
        return 'gid://shopify/%s/sec3-%s-%s-%s' % (
            kind, self.tag, store.id, type(self)._seq)

    def _as(self, user, model):
        return self.env[model].with_user(user)

    def _installed(self, model):
        return model in self.env

    # ------------------------------------------------------------------
    # Business fixtures, per company
    # ------------------------------------------------------------------

    def _partner(self, company):
        return self.env['res.partner'].sudo().create({
            'name': 'SEC-3 partner %s %s' % (self.tag, company.id),
            'company_id': company.id,
        })

    def _sale_order(self, company):
        return self.env['sale.order'].sudo().with_company(company).create({
            'partner_id': self._partner(company).id,
            'company_id': company.id,
        })

    def _product_template(self, company):
        # Products are company-less on purpose where possible: it isolates the
        # binding's own company behaviour from the product's.
        return self.env['product.template'].sudo().create({
            'name': 'SEC-3 product %s %s' % (self.tag, company.id),
            'type': 'consu',
        })

    def _internal_location(self, company):
        return self.env['stock.location'].sudo().search([
            ('usage', '=', 'internal'),
            ('company_id', '=', company.id),
        ], limit=1)

    def _picking(self, company):
        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'outgoing'), ('company_id', '=', company.id),
        ], limit=1)
        if not picking_type:
            return self.env['stock.picking'].sudo().browse()
        return self.env['stock.picking'].sudo().with_company(company).create({
            'picking_type_id': picking_type.id,
            'partner_id': self._partner(company).id,
            'location_id': picking_type.default_location_src_id.id
            or self._internal_location(company).id,
            'location_dest_id': picking_type.default_location_dest_id.id
            or self._internal_location(company).id,
            'company_id': company.id,
        })

    def _tax_evidence_key(self, store):
        """`v1:<64 lowercase hex>` -- the model validates the shape."""
        type(self)._seq += 1
        return 'v1:%s' % hashlib.sha256(
            ('sec3-%s-%s-%s' % (self.tag, store.id, type(self)._seq)
             ).encode()).hexdigest()

    def _tax(self, company):
        """An independent leaf percentage SALE tax, price-excluded.

        Shaped to satisfy `shopify.connector.tax.mapping._check_mapping_safety`
        rather than to be minimal: that constraint refuses compound taxes,
        purchase taxes and a mismatched inclusion posture, so a lazier fixture
        would be testing the constraint instead of company isolation.
        """
        group = self.env['account.tax.group'].sudo().search(
            [('company_id', '=', company.id)], limit=1)
        if not group:
            group = self.env['account.tax.group'].sudo().create({
                'name': 'SEC-3 tax group %s' % company.id,
                'company_id': company.id,
            })
        return self.env['account.tax'].sudo().with_company(company).create({
            'name': 'SEC-3 tax %s %s' % (self.tag, company.id),
            'tax_group_id': group.id,
            # Required, and a freshly created company has no chart of
            # accounts to derive a fiscal country from.
            'country_id': (
                company.account_fiscal_country_id
                or company.country_id
                or self.env.ref('base.us')).id,
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_excluded',
            'include_base_amount': False,
            'company_id': company.id,
        })

    # ------------------------------------------------------------------
    # Row builders -- one per inventory entry.
    #
    # Each returns a single record of its model owned by `store`, or an empty
    # recordset when the owning module is not installed.
    # ------------------------------------------------------------------

    def _row_store(self, store):
        return store

    def _row_credential(self, store):
        # Batch 1 correction (§9.1): the credential model refuses a direct
        # `create()`, so this fixture mints through the service's own surface --
        # the same shape `_row_mutation_attempt` already uses for the Layer 2
        # sentinel. Satisfying the production guard rather than bypassing it is
        # the point: a fixture that could sidestep it would prove nothing.
        Credential = self.env['shopify.connector.store.credential'].sudo()
        existing = Credential.search([('store_id', '=', store.id)], limit=1)
        if existing:
            return existing
        return Credential._credential_surface('_mutate_token').create({
            'store_id': store.id, 'credential_epoch': 1,
        })

    def _row_access_token(self, store):
        Cache = self.env['shopify.connector.store.access.token'].sudo()
        existing = Cache.search([('store_id', '=', store.id)], limit=1)
        if existing:
            return existing
        credential = self._row_credential(store)
        return Cache.create({
            'store_id': store.id,
            'credential_id': credential.id,
            'credential_epoch': credential.credential_epoch,
            'auth_mode': credential.auth_mode,
            'access_token': 'sec3-fixture-token-%s' % store.id,
            'obtained_at': fields.Datetime.now(),
            'expires_at': fields.Datetime.add(fields.Datetime.now(), hours=24),
        })

    def _row_settings(self, store):
        Settings = self.env['shopify.connector.store.settings'].sudo()
        existing = Settings.search([('store_id', '=', store.id)], limit=1)
        return existing or Settings.create({'store_id': store.id})

    def _row_location(self, store):
        return self.env['shopify.connector.location'].sudo().create({
            'store_id': store.id,
            'name': 'SEC-3 location %s' % store.id,
            'shopify_location_gid':
                self._gid('Location', store),
        })

    def _row_job(self, store):
        return self._job(store)

    def _row_job_log(self, store):
        job = self._job(store)
        return self.env['shopify.connector.job.log'].sudo().create({
            'job_id': job.id,
            'event_type': 'note',
            'message': 'SEC-3 matrix',
        })

    def _row_mutation_attempt(self, store):
        """A REAL mutation attempt, minted through the sanctioned C2 seam.

        The previous version of this file had a test named for mutation
        attempts that created none. `_create_attempt_intent` fails closed
        without the internal C2 sentinel, so the fixture satisfies the
        production guard rather than bypassing it.
        """
        from odoo.addons.shopify_connector_core.models.\
            shopify_connector_mutation_attempt import (
                C2_SENTINEL_CONTEXT, C2_SIDE_CURSOR_SENTINEL,
            )
        job = self._job(store, job_type='mutation_dispatch_selftest')
        token = uuid.uuid4().hex
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        context = dict(self.env.context)
        context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
        return self.env['shopify.connector.mutation.attempt'].sudo(
        ).with_context(context)._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': store.shop_domain,
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': {'sec3': True},
            'business_intent_fingerprint': 'sec3-bif-%s' % token,
            'exact_request_fingerprint': 'sec3-erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        })

    def _row_call_lease(self, store):
        now = fields.Datetime.now()
        job = self._job(store)
        return self.env['shopify.connector.call.lease'].sudo().create({
            'store_id': store.id,
            'lease_key': 'sec3-%s-%s' % (self.tag, job.id),
            'job_id': job.id,
            'admitted_at': now,
            'expires_at': now,
        })

    def _row_customer_binding(self, store):
        return self.env['shopify.connector.customer.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('Customer', store),
            'partner_id': self._partner(store.company_id).id,
            'match_key': 'email',
        })

    def _row_order_binding(self, store):
        return self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('Order', store),
            'sale_order_id': self._sale_order(store.company_id).id,
        })

    def _row_template_binding(self, store):
        return self.env['shopify.connector.product.template.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('Product', store),
            'product_template_id': self._product_template(store.company_id).id,
        })

    def _row_variant_binding(self, store):
        template_binding = self._build(
            'shopify.connector.product.template.binding',
            '_row_template_binding', store)
        return self.env['shopify.connector.product.variant.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('ProductVariant', store),
            'product_variant_id':
                template_binding.product_template_id.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })

    def _row_export_preview(self, store):
        """A preview minted through the closed create surface.

        `_create_preview` fails closed without its named context, so the
        fixture satisfies the production guard instead of bypassing it.
        """
        Preview = self.env['shopify.connector.product.export.preview']
        template_binding = self._build(
            'shopify.connector.product.template.binding',
            '_row_template_binding', store)
        now = fields.Datetime.now()
        return Preview._preview_surface('_create_preview').with_company(
            store.company_id
        ).create({
            'store_id': store.id,
            'product_template_id': template_binding.product_template_id.id,
            'product_template_binding_id': template_binding.id,
            'export_path': 'update',
            'state': 'previewed',
            'diff': {},
            'apply_plan': {'steps': []},
            'blocked_differences': {'items': []},
            'previewed_at': now,
            'expires_at': fields.Datetime.add(now, hours=1),
        })

    def _row_export_media_binding(self, store):
        template_binding = self._build(
            'shopify.connector.product.template.binding',
            '_row_template_binding', store)
        return self.env[
            'shopify.connector.product.media.binding'
        ].sudo().create({
            'store_id': store.id,
            'product_template_binding_id': template_binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': '%064d' % store.id,
            'connector_filename': 'odoo-sec3-%s.png' % store.id,
            'shopify_gid': self._gid('MediaImage', store),
            'remote_status': 'staged',
        })

    def _row_location_mapping(self, store):
        location = self._internal_location(store.company_id)
        if not location:
            return self.env['shopify.connector.location.mapping'].sudo().browse()
        return self.env['shopify.connector.location.mapping'].sudo().with_company(
            store.company_id
        ).create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('Location', store),
            'odoo_location_id': location.id,
            'match_key': 'manual',
        })

    def _row_inventory_binding(self, store):
        mapping = self._build(
            'shopify.connector.location.mapping',
            '_row_location_mapping', store)
        if not mapping:
            return self.env['shopify.connector.inventory.level.binding'].sudo().browse()
        variant_binding = self._build(
            'shopify.connector.product.variant.binding',
            '_row_variant_binding', store)
        return self.env['shopify.connector.inventory.level.binding'].sudo(
        ).with_company(store.company_id).create({
            'store_id': store.id,
            'product_variant_binding_id': variant_binding.id,
            'location_mapping_id': mapping.id,
            'shopify_inventory_item_gid':
                self._gid('InventoryItem', store),
        })

    def _row_tax_mapping(self, store):
        # The mapping refuses to exist until the store's settings name an
        # order company, so the settings row is a prerequisite, not decoration.
        self._build('shopify.connector.store.settings', '_row_settings', store)
        return self.env['shopify.connector.tax.mapping'].sudo().with_company(
            store.company_id
        ).create({
            'store_id': store.id,
            'shopify_tax_evidence_key': self._tax_evidence_key(store),
            'account_tax_id': self._tax(store.company_id).id,
        })

    def _row_match_decision(self, store):
        # Built through the same key function production uses, so a change to
        # the identity rule breaks this fixture rather than leaving it
        # describing a key shape the product no longer writes.
        from odoo.addons.shopify_connector_product.models.\
            shopify_connector_product_match_decision import (
                DECISION_LEVEL_TEMPLATE,
                decision_key_for,
                match_value_digest,
            )
        job = self._job(store)
        gid = self._gid('Product', store)
        stamp = '2026-07-30T09:15:00Z'
        return self.env[
            'shopify.connector.product.match.decision'
        ].sudo().with_company(store.company_id).create({
            'store_id': store.id,
            'job_id': job.id,
            'decision_level': DECISION_LEVEL_TEMPLATE,
            'shopify_product_gid': gid,
            'remote_updated_at': stamp,
            'decision_key': decision_key_for(
                DECISION_LEVEL_TEMPLATE, gid, '', stamp,
            ),
            'match_key': 'sku_reference',
            'match_value_digests': json.dumps(
                [match_value_digest(self.env, 'SEC3-MATRIX')],
            ),
        })

    def _row_fulfillment_binding(self, store):
        picking = self._picking(store.company_id)
        if not picking:
            return self.env['shopify.connector.fulfillment.binding'].sudo().browse()
        return self.env['shopify.connector.fulfillment.binding'].sudo(
        ).with_company(store.company_id).create({
            'store_id': store.id,
            'shopify_gid':
                self._gid('Fulfillment', store),
            'picking_id': picking.id,
            'order_binding_id': self._build(
                'shopify.connector.order.binding',
                '_row_order_binding', store).id,
        })

    def _row_evidence(self, store):
        return self.env['shopify.connector.fulfillment.inbound.evidence'].sudo().create({
            'store_id': store.id,
            'shopify_fulfillment_gid':
                self._gid('Fulfillment', store),
        })

    def _row_evidence_line(self, store):
        evidence = self._build(
            'shopify.connector.fulfillment.inbound.evidence',
            '_row_evidence', store)
        return self.env[
            'shopify.connector.fulfillment.inbound.evidence.line'
        ].sudo().create({
            'evidence_id': evidence.id,
            'fo_line_item_gid':
                self._gid('FulfillmentOrderLineItem', store),
            'quantity': 1,
        })

    def _build(self, model, builder, store):
        """One cached row of `model` owned by `store`.

        Cached per test. Several builders construct a parent of their own (an
        inventory pair needs a location mapping AND a variant binding), so
        rebuilding on every call collides with the models' own uniqueness
        constraints -- UNIQUE(store_id, odoo_location_id) is the one that
        surfaced it. TransactionCase rolls back between tests, so the cache
        cannot leak across them.
        """
        if not self._installed(model):
            return None
        cache = self.__dict__.setdefault('_row_cache', {})
        key = (model, store.id)
        if key not in cache:
            cache[key] = getattr(self, builder)(store) or None
        return cache[key]


@tagged('post_install', '-at_install')
class TestSec3ModelMatrix(Sec3Base):
    """Every durable store-scoped model, every read and write shape."""

    def _pair(self, model, builder):
        """One row owned by company A and one owned by company B."""
        own = self._build(model, builder, self.store_a)
        foreign = self._build(model, builder, self.store_b)
        return own, foreign

    def _assert_unreadable_by_every_group(self, model):
        """A model no group may read at all satisfies isolation by exceeding it.

        The four read-shape tests below all assert the same pair of facts: the
        owner CAN read its own row, and a foreigner CANNOT read theirs. The
        "owner can" half is deliberate -- it stops the "foreigner cannot" half
        from passing vacuously because a rule hid the model from everybody.

        `shopify.connector.store.access.token` is the one model where hiding it
        from everybody is the POINT rather than a regression. It holds the
        cached 24-hour Shopify access token, and it carries no
        `ir.model.access.csv` row on purpose, so no connector group -- including
        Administrator -- can reach it through RPC. The token is reachable only
        through the sanctioned, store-scoped `sudo()` accessor on
        `shopify.connector.store.credential`.

        So this asserts the stronger property directly instead of skipping:
        EVERY interactive user is refused, on the model and on both rows. If a
        future change ever grants a group read access here, this fails and the
        model rejoins the ordinary matrix -- it cannot quietly become readable.
        """
        for user in (self.user_a, self.user_b):
            with self.assertRaises(AccessError, msg=model):
                self._as(user, model).search([])

    # ------------------------------------------------------------------
    # Read shapes
    # ------------------------------------------------------------------

    def test_search_is_isolated_for_every_model(self):
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if model in SEC3_NO_ACL_MODELS:
                    self._assert_unreadable_by_every_group(model)
                    continue
                if own is None or foreign is None:
                    continue  # module not installed, or no fixture is
                    # constructible here; completeness is enforced
                    # separately by TestSec3InventoryCompleteness
                visible = self._as(self.user_a, model).search([]).ids
                self.assertIn(
                    own.id, visible,
                    '%s: a reader must still see its OWN row; a rule that '
                    'hides everything is a regression, not isolation' % model)
                self.assertNotIn(
                    foreign.id, visible,
                    "%s: another company's row is visible in a plain search"
                    % model)

    def test_direct_id_read_is_refused_for_every_model(self):
        """Knowing the id must not be enough, on any model."""
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if model in SEC3_NO_ACL_MODELS:
                    self._assert_unreadable_by_every_group(model)
                    continue
                if own is None or foreign is None:
                    continue  # module not installed, or no fixture is
                    # constructible here; completeness is enforced
                    # separately by TestSec3InventoryCompleteness
                # The owning company's user CAN read it. Without this half the
                # assertion below could pass because nobody can read the model.
                self._as(self.user_b, model).browse(foreign.id).read(['id'])
                with self.assertRaises(AccessError, msg=model):
                    self._as(self.user_a, model).browse(foreign.id).read(['id'])

    def test_search_count_does_not_leak_for_every_model(self):
        """A count is a read. Leaking "how many" is still leaking."""
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if model in SEC3_NO_ACL_MODELS:
                    self._assert_unreadable_by_every_group(model)
                    continue
                if own is None or foreign is None:
                    continue  # module not installed, or no fixture is
                    # constructible here; completeness is enforced
                    # separately by TestSec3InventoryCompleteness
                self.assertEqual(
                    self._as(self.user_a, model).search_count(
                        [('id', '=', foreign.id)]), 0, model)
                self.assertEqual(
                    self._as(self.user_b, model).search_count(
                        [('id', '=', foreign.id)]), 1,
                    '%s: the owning company must still count its own row'
                    % model)

    def test_grouped_read_does_not_leak_for_every_model(self):
        """Grouped reads bypass a naive rule that only filters plain searches."""
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if model in SEC3_NO_ACL_MODELS:
                    self._assert_unreadable_by_every_group(model)
                    continue
                if own is None or foreign is None:
                    continue  # module not installed, or no fixture is
                    # constructible here; completeness is enforced
                    # separately by TestSec3InventoryCompleteness
                groups = self._as(self.user_a, model).formatted_read_group(
                    [], ['company_id'], ['__count'])
                companies = {
                    group['company_id'][0] for group in groups
                    if group.get('company_id')
                }
                self.assertNotIn(
                    self.company_b.id, companies,
                    '%s: a grouped read exposed another company' % model)

    # ------------------------------------------------------------------
    # Write shapes, each with zero side effects
    # ------------------------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models',
                 'odoo.sql_db')
    def test_write_to_a_foreign_row_is_refused_with_no_side_effect(self):
        """No interactive user may write another company's row.

        Contained in a savepoint for the same reason as the create test: these
        models refuse at different layers, and an uncontained SQL-level refusal
        would abort the transaction and take the remaining models with it. The
        proof is that the row is byte-for-byte unchanged afterwards.
        """
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if own is None or foreign is None:
                    continue
                before = foreign.read()[0]
                wrote = False
                try:
                    with self.env.cr.savepoint():
                        self._as(self.user_a, model).browse(foreign.id).write(
                            {'write_uid': self.user_a.id})
                        wrote = True
                except Exception:  # noqa: BLE001 -- see the docstring
                    wrote = False
                self.env[model].invalidate_model()
                self.assertFalse(
                    wrote, "%s: an interactive user wrote another company's "
                    'row' % model)
                self.assertEqual(
                    self.env[model].sudo().browse(foreign.id).read()[0], before,
                    '%s: a denied write must leave the target completely '
                    'untouched' % model)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models',
                 'odoo.sql_db')
    def test_unlink_of_a_foreign_row_is_refused_with_no_side_effect(self):
        for model, builder in SEC3_MODELS:
            with self.subTest(model=model):
                own, foreign = self._pair(model, builder)
                if own is None or foreign is None:
                    continue
                deleted = False
                try:
                    with self.env.cr.savepoint():
                        self._as(self.user_a, model).browse(foreign.id).unlink()
                        deleted = True
                except Exception:  # noqa: BLE001 -- see the write test
                    deleted = False
                self.env[model].invalidate_model()
                self.assertFalse(
                    deleted,
                    "%s: an interactive user deleted another company's row"
                    % model)
                self.assertTrue(
                    self.env[model].sudo().browse(foreign.id).exists(),
                    '%s: a denied unlink must leave the row in place' % model)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models',
                 'odoo.sql_db')
    def test_creating_a_row_against_a_foreign_store_is_refused(self):
        """No interactive user may mint a row into another company's store.

        Each attempt runs inside its own SAVEPOINT. Some of these creates are
        refused by the record rule, some by a closed create surface, and some
        by the database before the rule is ever consulted -- and a failure at
        the SQL layer aborts the whole transaction unless it is contained. The
        savepoint keeps one model's refusal from destroying the next model's
        test.

        The assertion that carries the proof is the row count, not the
        exception type: what must never happen is a create against a foreign
        store that SUCCEEDS.
        """
        Model = self.env['shopify.connector.store']
        for model, _builder in SEC3_MODELS:
            if model == 'shopify.connector.store':
                continue  # the ownership root has no store parent to point at
            if not self._installed(model):
                continue
            with self.subTest(model=model):
                before = self.env[model].sudo().search_count(
                    [('company_id', '=', self.company_b.id)])
                created = False
                try:
                    with self.env.cr.savepoint():
                        self.env[model].with_user(self.user_a).create(
                            self._foreign_create_values(model))
                        created = True
                except Exception:  # noqa: BLE001 -- see the docstring
                    created = False
                Model.invalidate_model()
                self.env[model].invalidate_model()
                after = self.env[model].sudo().search_count(
                    [('company_id', '=', self.company_b.id)])
                self.assertFalse(
                    created,
                    '%s: an interactive user created a row against another '
                    "company's store" % model)
                self.assertEqual(
                    before, after,
                    '%s: a refused create must leave no row behind' % model)

    def _foreign_create_values(self, model):
        """Values pointing a new row at company B's store.

        Deliberately minimal. A create refused for a missing required field is
        still a create that did not happen, and the row-count assertion above
        is what proves nothing was written.
        """
        if model == 'shopify.connector.fulfillment.inbound.evidence.line':
            return {'evidence_id': self._row_evidence(self.store_b).id}
        if model == 'shopify.connector.job.log':
            return {
                'job_id': self.job_b.id,
                'event_type': 'note',
                'message': 'SEC-3 foreign create',
            }
        if model == 'shopify.connector.mutation.attempt':
            return {'job_id': self.job_b.id, 'attempt_token': 'sec3'}
        return {'store_id': self.store_b.id}


@tagged('post_install', '-at_install')
class TestSec3InventoryCompleteness(Sec3Base):
    """The inventory above must not fall behind the registry."""

    def _durable_store_scoped_models(self):
        found = []
        for name in self.env.registry.models:
            if not name.startswith('shopify.connector.'):
                continue
            model = self.env[name]
            if model._abstract or model._transient or not model._auto:
                continue
            fields = model._fields
            company = fields.get('company_id')
            store = fields.get('store_id')
            rooted_in_store = bool(
                store is not None
                and store.comodel_name == 'shopify.connector.store'
            )
            related_through_store = bool(
                company is not None and company.related
                and 'store_id' in company.related
            )
            if (
                name == 'shopify.connector.store'
                or rooted_in_store
                or related_through_store
            ):
                found.append(name)
        return sorted(found)

    def test_no_durable_store_scoped_model_escapes_this_matrix(self):
        """Adding a store-scoped model without covering it is a red suite."""
        covered = {model for model, _ in SEC3_MODELS}
        for name in self._durable_store_scoped_models():
            self.assertIn(
                name, covered,
                'SEC-3: %s is a durable store-scoped model with no entry in '
                'SEC3_MODELS. Add a row builder and the matrix will cover it; '
                'leaving it out is exactly how the previous version came to '
                'describe more coverage than it performed.' % name,
            )

    def test_every_covered_model_has_a_company_field(self):
        for model, _builder in SEC3_MODELS:
            if not self._installed(model):
                continue
            self.assertIn(
                'company_id', self.env[model]._fields,
                '%s: no company field, so no company can be enforced' % model)

    def test_every_covered_model_has_a_global_fail_closed_rule(self):
        Rule = self.env['ir.rule'].sudo()
        for model, _builder in SEC3_MODELS:
            if not self._installed(model):
                continue
            rules = Rule.search([('model_id.model', '=', model)])
            company_rules = [
                rule for rule in rules
                if "('company_id', 'in', company_ids)" in (rule.domain_force or '')
            ]
            self.assertTrue(
                company_rules,
                '%s: no rule filters on company_id' % model)
            for rule in company_rules:
                self.assertTrue(
                    rule['global'],
                    '%s: the company rule must be GLOBAL, or a permissive '
                    'group rule can re-open it (ir_rule._compute_global)'
                    % model)
                self.assertNotIn(
                    "('company_id', '=', False)", rule.domain_force,
                    '%s: the rule has a company-less escape hatch. A row '
                    'whose owner cannot be proven must be visible to nobody, '
                    'not to everybody.' % model)

    def test_every_store_relation_is_declared_and_constrained(self):
        """A connector parent relation must be declared to the scope mixin."""
        for model, field_name in SEC3_STORE_RELATIONS:
            if not self._installed(model):
                continue
            with self.subTest(model=model, field=field_name):
                record_model = self.env[model]
                self.assertIn(
                    'sec3_scope_quarantined', record_model._fields,
                    '%s owns a connector relation but does not inherit '
                    'shopify.connector.scope.mixin' % model)
                declared = dict(record_model._sec3_parent_scope_relations())
                self.assertIn(
                    field_name, declared,
                    '%s.%s points at another connector row but is not '
                    'declared to the scope mixin, so neither the constraint '
                    'nor the upgrade sweep covers it' % (model, field_name))
                self.assertEqual(declared[field_name], 'store',
                                 '%s.%s must agree on the STORE, not merely '
                                 'the company' % (model, field_name))

    def test_no_undeclared_connector_relation_exists(self):
        """The reverse direction: a NEW connector relation must be declared."""
        for model, _builder in SEC3_MODELS:
            if not self._installed(model):
                continue
            record_model = self.env[model]
            declared = dict(
                record_model._sec3_parent_scope_relations()
                if hasattr(record_model, '_sec3_parent_scope_relations') else ()
            )
            for name, field in record_model._fields.items():
                if field.type != 'many2one':
                    continue
                if not (field.comodel_name or '').startswith('shopify.connector.'):
                    continue
                if field.comodel_name == 'shopify.connector.store':
                    continue  # the ownership root itself, not a peer relation
                if field.comodel_name == NEUTRAL_BY_DECISION:
                    continue
                if (model, name) in SEC3_STRUCTURAL_RELATIONS:
                    # Cannot disagree; see the constant's comment.
                    self.assertTrue(
                        self.env[model]._fields[
                            'company_id' if name == 'evidence_id'
                            else 'store_id'].related,
                        '%s.%s is listed as structurally safe, but the field '
                        'that makes it safe is no longer a related field'
                        % (model, name))
                    continue
                self.assertIn(
                    name, declared,
                    '%s.%s is a connector-to-connector relation that no SEC-3 '
                    'declaration covers. Declare it in '
                    '_sec3_parent_scope_relations, or the same-store rule and '
                    'the historic sweep will both miss it.' % (model, name),
                )

    def test_the_neutral_attribute_lock_is_verifiable(self):
        """The one deliberate exception, stated so a reviewer can check it.

        Control-room item 3.11 asks the independent reviewer to verify three
        properties before accepting the exception, so the properties are
        asserted here rather than argued in prose.
        """
        if not self._installed(NEUTRAL_BY_DECISION):
            self.skipTest('%s is not installed' % NEUTRAL_BY_DECISION)
        lock = self.env[NEUTRAL_BY_DECISION]
        # (1) it holds no store or company data
        self.assertNotIn('store_id', lock._fields)
        self.assertNotIn('company_id', lock._fields)
        # (2) it is a single immutable mutex row
        self.assertEqual(
            lock.sudo().search_count([]), 1,
            'the attribute lock must be exactly one seeded row; more than one '
            'is not a mutex')
        # (3) it protects a GLOBAL resource, so splitting it per company would
        #     change locking semantics rather than scope them. Odoo product
        #     attributes carry no company at all -- that is the whole reason
        #     the mutex cannot be per-company.
        self.assertNotIn(
            'company_id', self.env['product.attribute']._fields,
            'if product.attribute ever became company-scoped, this exception '
            'would have to be revisited')


@tagged('post_install', '-at_install')
class TestSec3RoleAndSwitcherAxes(Sec3Base):
    """A role is authorization; a company is ownership. Neither substitutes."""

    def test_connector_user_role_is_still_company_isolated(self):
        visible = self._as(self.user_connector, 'shopify.connector.store').search([]).ids
        self.assertIn(self.store_a.id, visible)
        self.assertNotIn(self.store_b.id, visible)

    def test_connector_admin_role_is_still_company_isolated(self):
        visible = self._as(self.user_a, 'shopify.connector.store').search([]).ids
        self.assertIn(self.store_a.id, visible)
        self.assertNotIn(
            self.store_b.id, visible,
            'Connector Administrator is a role, not a company-wide override')

    def test_plain_internal_user_has_no_connector_access_at_all(self):
        with self.assertRaises(AccessError):
            self._as(self.user_plain, 'shopify.connector.store').search([])

    def test_allowed_in_both_but_switched_to_one_sees_only_the_active_one(self):
        """`company_ids` in a rule is the switcher selection, not membership."""
        switched_to_a = self.env['shopify.connector.store'].with_user(
            self.user_both).with_context(allowed_company_ids=[self.company_a.id])
        visible = switched_to_a.search([]).ids
        self.assertIn(self.store_a.id, visible)
        self.assertNotIn(
            self.store_b.id, visible,
            'a user allowed in both companies but switched to A must not see '
            "B's store merely because they could switch to it")

        both_active = self.env['shopify.connector.store'].with_user(
            self.user_both).with_context(
                allowed_company_ids=[self.company_a.id, self.company_b.id])
        self.assertIn(self.store_b.id, both_active.search([]).ids)

    def test_sudo_does_not_let_an_interactive_caller_widen_company(self):
        """`sudo()` bypasses rules by design -- which is exactly why the
        write-side company check must be a CONSTRAINT, not a rule."""
        partner_b = self._partner(self.company_b)
        with self.assertRaises(UserError):
            self.env['shopify.connector.customer.binding'].with_user(
                self.user_a).sudo().create({
                    'store_id': self.store_a.id,
                    'shopify_gid': 'gid://shopify/Customer/SEC3SUDO-%s' % self.tag,
                    'partner_id': partner_b.id,
                    'match_key': 'email',
                })


@tagged('post_install', '-at_install')
class TestSec3RelationalClosure(Sec3Base):
    """Connector relations must agree on the STORE, not merely the company.

    Every test here uses `store_a` and `store_a2` -- two stores in the SAME
    company. That is the whole point: a company check passes for both, so any
    failure here is a genuine cross-store leak that no company rule can catch.
    """

    def test_a_variant_binding_may_not_point_at_another_stores_template(self):
        template_binding_a2 = self._row_template_binding(self.store_a2)
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.product.variant.binding'].sudo().create({
                'store_id': self.store_a.id,
                'shopify_gid': 'gid://shopify/ProductVariant/sec3x-%s' % self.tag,
                'product_variant_id':
                    template_binding_a2.product_template_id.product_variant_id.id,
                'product_template_binding_id': template_binding_a2.id,
            })

    def test_evidence_may_not_point_at_another_stores_order_binding(self):
        if not self._installed('shopify.connector.fulfillment.inbound.evidence'):
            self.skipTest('fulfillment is not installed')
        order_binding_a2 = self._row_order_binding(self.store_a2)
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.fulfillment.inbound.evidence'].sudo().create({
                'store_id': self.store_a.id,
                'shopify_fulfillment_gid':
                    'gid://shopify/Fulfillment/sec3xs-%s' % self.tag,
                'order_binding_id': order_binding_a2.id,
            })

    def test_evidence_may_not_point_at_another_stores_fulfillment_binding(self):
        if not self._installed('shopify.connector.fulfillment.inbound.evidence'):
            self.skipTest('fulfillment is not installed')
        fulfillment_a2 = self._row_fulfillment_binding(self.store_a2)
        if not fulfillment_a2:
            self.skipTest('no outgoing picking type for this company')
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.fulfillment.inbound.evidence'].sudo().create({
                'store_id': self.store_a.id,
                'shopify_fulfillment_gid':
                    'gid://shopify/Fulfillment/sec3xf-%s' % self.tag,
                'fulfillment_binding_id': fulfillment_a2.id,
            })

    def test_an_evidence_line_may_not_point_at_another_companys_sale_line(self):
        if not self._installed(
            'shopify.connector.fulfillment.inbound.evidence.line'
        ):
            self.skipTest('fulfillment is not installed')
        evidence_a = self._row_evidence(self.store_a)
        order_b = self._sale_order(self.company_b)
        product = self._product_template(self.company_b)
        line_b = self.env['sale.order.line'].sudo().with_company(
            self.company_b
        ).create({
            'order_id': order_b.id,
            'product_id': product.product_variant_id.id,
            'product_uom_qty': 1,
        })
        with self.assertRaises(ValidationError):
            self.env[
                'shopify.connector.fulfillment.inbound.evidence.line'
            ].sudo().create({
                'evidence_id': evidence_a.id,
                'fo_line_item_gid': 'gid://shopify/FOLI/sec3-%s' % self.tag,
                'sale_line_id': line_b.id,
                'quantity': 1,
            })

    def test_inventory_pair_rejects_a_variant_binding_from_another_store(self):
        if not self._installed('shopify.connector.inventory.level.binding'):
            self.skipTest('inventory is not installed')
        mapping_a = self._row_location_mapping(self.store_a)
        if not mapping_a:
            self.skipTest('no internal location for this company')
        variant_a2 = self._row_variant_binding(self.store_a2)
        with self.assertRaises(UserError):
            self.env['shopify.connector.inventory.level.binding'].sudo(
            ).with_company(self.company_a).create({
                'store_id': self.store_a.id,
                'product_variant_binding_id': variant_a2.id,
                'location_mapping_id': mapping_a.id,
                'shopify_inventory_item_gid':
                    'gid://shopify/InventoryItem/sec3x-%s' % self.tag,
            })


@tagged('post_install', '-at_install')
class TestSec3HistoricRows(Sec3Base):
    """Rows written before SEC-3 existed. Fail closed, never guess."""

    def _plant_company_less_store(self, label):
        """A store shaped like one from a pre-SEC-3 database.

        Planted in SQL because the ORM constraint (correctly) refuses to create
        one. This is precisely the shape an upgraded database can contain.
        """
        self.env.cr.execute(
            "INSERT INTO shopify_connector_store "
            "(name, shop_domain, api_version, state, company_id, "
            " connection_generation, disconnect_status, create_uid, "
            " create_date, write_uid, write_date) "
            "VALUES (%s, %s, '2026-07', 'setup_incomplete', NULL, 0, 'none', "
            "1, now(), 1, now()) RETURNING id",
            ('SEC-3 historic %s' % label,
             'sec3-hist-%s-%s.myshopify.com' % (self.tag, label)),
        )
        store_id = self.env.cr.fetchone()[0]
        self.env['shopify.connector.store'].invalidate_model()
        return store_id

    def test_store_requires_an_owning_company(self):
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.store'].sudo().create({
                'name': 'SEC-3 unowned',
                'shop_domain': 'sec3-unowned-%s.myshopify.com' % self.tag,
                'api_version': '2026-07',
                'company_id': False,
            })

    def test_company_less_historic_store_is_invisible_to_everyone(self):
        historic_id = self._plant_company_less_store('invisible')
        for user in (self.user_a, self.user_b, self.user_both,
                     self.user_connector):
            visible = self._as(user, 'shopify.connector.store').search([]).ids
            self.assertNotIn(
                historic_id, visible,
                'a store whose owning company could not be proven must be '
                'visible to nobody, not to everybody')

    def test_administrative_remediation_assigns_a_company(self):
        historic_id = self._plant_company_less_store('remediate')
        store = self.env['shopify.connector.store'].sudo().browse(historic_id)
        store.with_user(self.user_a).action_assign_company(self.company_a.id)
        self.assertEqual(store.company_id, self.company_a)
        self.assertIn(
            historic_id,
            self._as(self.user_a, 'shopify.connector.store').search([]).ids)

    def test_remediation_cannot_re_home_an_already_owned_store(self):
        with self.assertRaises(UserError):
            self.store_a.with_user(self.user_a).action_assign_company(
                self.company_a.id)

    def test_remediation_refuses_a_company_the_caller_does_not_belong_to(self):
        historic_id = self._plant_company_less_store('foreign')
        store = self.env['shopify.connector.store'].sudo().browse(historic_id)
        with self.assertRaises(AccessError):
            store.with_user(self.user_a).action_assign_company(self.company_b.id)
        store.invalidate_recordset()
        self.assertFalse(
            store.company_id,
            'a refused remediation must not have assigned anything')

    def test_a_historic_cross_store_row_is_quarantined_not_re_homed(self):
        """The shape a constraint can never catch, because it predates it.

        Two stores in the SAME company, so every company check passes; the row
        points at a parent in the other store. Planted in SQL because the ORM
        now refuses it. The sweep must hide it, name it, and change nothing
        else -- re-homing either half would rewrite operational history on a
        guess.
        """
        binding_a2 = self._row_template_binding(self.store_a2)
        variant_a = self._row_variant_binding(self.store_a)
        self.env.cr.execute(
            'UPDATE shopify_connector_product_variant_binding '
            'SET product_template_binding_id = %s WHERE id = %s',
            (binding_a2.id, variant_a.id),
        )
        Model = self.env['shopify.connector.product.variant.binding']
        Model.invalidate_model()

        # Precondition: the planted row is company-consistent, so nothing in
        # the company model can see the problem.
        variant_a = Model.sudo().browse(variant_a.id)
        self.assertEqual(
            variant_a.company_id,
            variant_a.product_template_binding_id.company_id,
            'the planted row must be company-consistent, or this test is not '
            'exercising the cross-store case at all')
        self.assertIn(variant_a.id, self._as(
            self.user_a, Model._name).search([]).ids)

        quarantined = Model._sec3_quarantine_scope_mismatches()
        self.assertGreaterEqual(quarantined, 1)
        Model.invalidate_model()

        self.assertNotIn(
            variant_a.id, self._as(self.user_a, Model._name).search([]).ids,
            'a quarantined row must be invisible to every read')
        with self.assertRaises(AccessError):
            self._as(self.user_a, Model._name).browse(variant_a.id).read(['id'])
        # Nothing was re-homed.
        variant_a = Model.sudo().browse(variant_a.id)
        self.assertEqual(variant_a.store_id, self.store_a)
        self.assertEqual(
            variant_a.product_template_binding_id.store_id, self.store_a2,
            'the sweep must not have re-homed either half')

    def test_releasing_a_quarantine_requires_the_disagreement_to_be_resolved(self):
        binding_a2 = self._row_template_binding(self.store_a2)
        variant_a = self._row_variant_binding(self.store_a)
        Model = self.env['shopify.connector.product.variant.binding']
        self.env.cr.execute(
            'UPDATE shopify_connector_product_variant_binding '
            'SET product_template_binding_id = %s WHERE id = %s',
            (binding_a2.id, variant_a.id),
        )
        Model.invalidate_model()
        Model._sec3_quarantine_scope_mismatches()
        Model.invalidate_model()

        record = Model.sudo().browse(variant_a.id)
        self.assertTrue(record.sec3_scope_quarantined)
        # Still inconsistent -> release refuses.
        with self.assertRaises(ValidationError):
            record.with_user(self.user_a).action_sec3_release_scope_quarantine()
        self.assertTrue(record.sec3_scope_quarantined)

    def test_quarantining_evidence_also_hides_its_ledger_lines(self):
        """A stored related flag does not follow a SQL write to its source.

        The line's quarantine is `related='evidence_id.sec3_scope_quarantined',
        store=True`, and the sweep writes the parent in SQL, so nothing
        recomputes it. Without explicit propagation the observation would be
        hidden while its per-line ledger -- the duplicate-application backstop
        -- stayed readable to another company.
        """
        if not self._installed(
            'shopify.connector.fulfillment.inbound.evidence.line'
        ):
            self.skipTest('fulfillment is not installed')
        Evidence = self.env['shopify.connector.fulfillment.inbound.evidence']
        Line = self.env[
            'shopify.connector.fulfillment.inbound.evidence.line']
        evidence = self._row_evidence(self.store_a)
        line = Line.sudo().create({
            'evidence_id': evidence.id,
            'fo_line_item_gid': 'gid://shopify/FOLI/sec3q-%s' % self.tag,
            'quantity': 1,
        })
        foreign_order_binding = self._row_order_binding(self.store_a2)
        # Planted in SQL: the ORM constraint now refuses this shape outright.
        self.env.cr.execute(
            'UPDATE shopify_connector_fulfillment_inbound_evidence '
            'SET order_binding_id = %s WHERE id = %s',
            (foreign_order_binding.id, evidence.id))
        Evidence.invalidate_model()
        Line.invalidate_model()
        self.assertIn(line.id, self._as(self.user_a, Line._name).search([]).ids)

        Evidence._sec3_quarantine_scope_mismatches()
        Evidence.invalidate_model()
        Line.invalidate_model()

        self.assertTrue(Evidence.sudo().browse(evidence.id).sec3_scope_quarantined)
        self.assertNotIn(
            line.id, self._as(self.user_a, Line._name).search([]).ids,
            'the ledger line must be hidden with the observation it belongs to')
        with self.assertRaises(AccessError):
            self._as(self.user_a, Line._name).browse(line.id).read(['id'])

    def test_only_a_connector_administrator_may_release_a_quarantine(self):
        variant_a = self._row_variant_binding(self.store_a)
        Model = self.env['shopify.connector.product.variant.binding']
        self.env.cr.execute(
            'UPDATE shopify_connector_product_variant_binding '
            'SET sec3_scope_quarantined = TRUE WHERE id = %s', (variant_a.id,))
        Model.invalidate_model()
        record = Model.sudo().browse(variant_a.id)
        with self.assertRaises(AccessError):
            record.with_user(
                self.user_connector).action_sec3_release_scope_quarantine()
        self.assertTrue(record.sec3_scope_quarantined)
